#!/usr/bin/env python3
"""PAD-Stream Version 15F-0.

Global recurrent state for adaptive-timestep proposal and streamline-retrace
memory.

The milestone consumes the already-approved sequential physics/map-back history
and learns one compact GRU state over every accepted simulator step. Two heads
are attached to that recurrent state:

1. a next-timestep proposal head;
2. a total-flow / gas-path retrace-load head evaluated at path-update snapshots.

The deployment contract remains predict-screen-correct:

    accepted simulator diagnostics -> GRU state -> learned proposal
                                      -> calibrated confidence screen
                                      -> classical timestep controller / exact
                                         path-cache and Pollock authority

Scope boundary
--------------
* Version 15F-0 does not learn breakthrough or well-control memory. Producer
  gas cut and breakthrough flags are deliberately excluded from the feature
  set; they belong to Version 15F-1.
* Version 15F-0 does not learn nonlinear-difficulty memory beyond the current
  accepted-step diagnostics required for timestep safety. The explicit
  nonlinear-memory head belongs to Version 15F-2.
* Exact future saturation, inventory, pressure, gas cut, and path geometry are
  targets or audit-only values and never enter inference features.
* Classical adaptive-step acceptance and exact Pollock/path-cache correction
  remain mandatory final authorities.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import sys
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from torch import nn

VERSION = "15F-0"
SEED = 150600
RETRACE_RISK_THRESHOLD = 0.18
DAYS_PER_YEAR = 365.0
FORBIDDEN_FEATURE_TOKENS = (
    "producer_gas_cut", "breakthrough", "exact_future", "target_saturation",
    "target_inventory", "target_pressure", "exact_geometry",
)


@dataclass(frozen=True)
class TrainConfig:
    hidden_dim: int = 32
    retrace_hidden_dim: int = 32
    dropout: float = 0.10
    learning_rate: float = 2.0e-3
    weight_decay: float = 1.0e-4
    retrace_loss_weight: float = 3.0
    max_epochs: int = 1200
    validation_stride: int = 10
    early_stopping_checks: int = 25
    gradient_clip: float = 2.0
    train_end_day: float = 240.0
    validation_end_day: float = 300.0
    minimum_dt_days: float = 0.10
    maximum_dt_days: float = 2.00
    minimum_dt_factor: float = 0.50
    maximum_dt_factor: float = 1.40


DENSE_BASE_FEATURES = [
    "time_fraction",
    "log_current_dt_days",
    "retries_before_accept",
    "nonlinear_iterations",
    "pressure_fixed_point_iterations_final",
    "pressure_fixed_point_iterations_total",
    "log10_pressure_fixed_point_residual",
    "maximum_saturation_change",
    "injector_bhp_mpa",
    "injector_mass_rate_kg_s",
    "log10_pressure_residual_m3_s",
    "pressure_guess_rmse_mpa",
    "persistence_error_rmse_mpa",
    "candidate_innovation_rmse_mpa",
    "learned_preflight_change_mpa",
    "persistence_preflight_change_mpa",
]

SNAPSHOT_FEATURE_NAMES = [
    "time_fraction",
    "snapshot_interval_over_15_days",
    "current_saturation_mean",
    "current_saturation_std",
    "current_saturation_max",
    "current_saturation_p90",
    "mean_absolute_saturation_change",
    "rms_saturation_change",
    "maximum_saturation_change",
    "current_trapped_margin_mean",
    "history_growth_mean",
    "pressure_change_rms_mpa",
    "pressure_change_max_mpa",
    "relative_inventory_change",
    "current_inventory_billion_kg",
    "previous_total_retrace_fraction",
    "previous_gas_retrace_fraction",
    "previous_total_path_fraction",
    "previous_gas_path_fraction",
    "v15e3_predicted_inventory_billion_kg",
    "v15e3_state_distance_ratio",
    "v15e3_graph_disagreement_ratio",
    "v15e3_uncertainty_ratio",
    "v15e3_graph_selected",
    "v15e3_mass_capacity_clipped",
    "v15e3_coverage_fraction",
]

RETRACE_TARGET_NAMES = [
    "total_flow_full_retrace_fraction",
    "gas_path_full_retrace_fraction",
    "gas_new_path_fraction",
]


def seed_everything(seed: int = SEED) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    return float(np.sqrt(np.mean((a - b) ** 2)))


def mae(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    return float(np.mean(np.abs(a - b)))


def safe_torch_load(path: Path) -> Mapping[str, Any]:
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


def load_npz(path: Path) -> Dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {name: z[name].copy() for name in z.files}


def split_labels(time_days: np.ndarray, cfg: TrainConfig) -> np.ndarray:
    time_days = np.asarray(time_days, np.float64)
    out = np.full(time_days.shape, "test", dtype="<U10")
    out[time_days <= cfg.validation_end_day] = "validation"
    out[time_days <= cfg.train_end_day] = "train"
    return out


def train_normalization(x: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = np.asarray(x[mask], np.float64).mean(axis=0)
    std = np.asarray(x[mask], np.float64).std(axis=0)
    std[std < 1.0e-6] = 1.0
    return mean, std


def normalize(x: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return ((np.asarray(x, np.float64) - mean) / std).astype(np.float32)


def build_dense_features(dense: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    required = {
        "time_days", "dt_days", "retries_before_accept", "warm_start_method",
        "nonlinear_iterations", "pressure_fixed_point_iterations_final",
        "pressure_fixed_point_iterations_total", "pressure_fixed_point_residual",
        "maximum_saturation_change", "injector_bhp_mpa",
        "injector_mass_rate_kg_s", "pressure_residual_m3_s",
        "pressure_guess_rmse_mpa", "persistence_error_rmse_mpa",
        "candidate_innovation_rmse_mpa", "learned_preflight_change_mpa",
        "persistence_preflight_change_mpa", "accepted_next_dt_days",
    }
    missing = sorted(required.difference(dense.columns))
    if missing:
        raise KeyError(f"dense audit missing columns: {missing}")

    features = pd.DataFrame({
        "time_fraction": dense["time_days"] / DAYS_PER_YEAR,
        "log_current_dt_days": np.log(np.maximum(dense["dt_days"], 1.0e-6)),
        "retries_before_accept": dense["retries_before_accept"],
        "nonlinear_iterations": dense["nonlinear_iterations"],
        "pressure_fixed_point_iterations_final": dense["pressure_fixed_point_iterations_final"],
        "pressure_fixed_point_iterations_total": dense["pressure_fixed_point_iterations_total"],
        "log10_pressure_fixed_point_residual": np.log10(
            np.maximum(np.abs(dense["pressure_fixed_point_residual"]), 1.0e-14)
        ),
        "maximum_saturation_change": dense["maximum_saturation_change"],
        "injector_bhp_mpa": dense["injector_bhp_mpa"],
        "injector_mass_rate_kg_s": dense["injector_mass_rate_kg_s"],
        "log10_pressure_residual_m3_s": np.log10(
            np.maximum(np.abs(dense["pressure_residual_m3_s"]), 1.0e-14)
        ),
        "pressure_guess_rmse_mpa": dense["pressure_guess_rmse_mpa"],
        "persistence_error_rmse_mpa": dense["persistence_error_rmse_mpa"],
        "candidate_innovation_rmse_mpa": dense["candidate_innovation_rmse_mpa"].fillna(0.0),
        "learned_preflight_change_mpa": dense["learned_preflight_change_mpa"].fillna(0.0),
        "persistence_preflight_change_mpa": dense["persistence_preflight_change_mpa"].fillna(0.0),
    })
    categories = sorted(str(value) for value in dense["warm_start_method"].unique())
    for category in categories:
        name = f"warm_start__{category}"
        features[name] = (dense["warm_start_method"].astype(str) == category).astype(float)
    return features, list(features.columns)


def state_path(state_dir: Path, day: int) -> Path:
    return state_dir / f"pad_stream_v15b4_day_{int(day)}.npz"


def phase_cache_metrics(cache: pd.DataFrame, day: int, phase: str) -> Dict[str, float]:
    rows = cache[(cache["time_days"] == float(day)) & (cache["phase"] == phase)]
    count = int(len(rows))
    if count == 0:
        return {"count": 0, "retrace": 1.0, "new": 0.0, "reuse": 0.0}
    decisions = rows["cache_decision"].astype(str)
    return {
        "count": count,
        "retrace": float(np.mean(decisions == "full_retrace")),
        "new": float(np.mean(decisions == "new_path")),
        "reuse": float(np.mean(decisions == "reuse_exact")),
    }


def build_snapshot_dataset(
    dense: pd.DataFrame,
    cache: pd.DataFrame,
    state_dir: Path,
    e3_audit: pd.DataFrame,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    days = sorted(int(day) for day in cache["time_days"].unique() if float(day) > 15.0)
    previous_day = 15
    previous_total_retrace = 0.0
    previous_gas_retrace = 0.0
    previous_total_count = 180
    previous_gas_count = int(len(cache[(cache["time_days"] == 15.0) & (cache["phase"] == "gas")]))
    records: list[dict[str, Any]] = []
    feature_rows: list[list[float]] = []
    targets: list[list[float]] = []
    dense_indices: list[int] = []

    dense_times = dense["time_days"].to_numpy(np.float64)
    for day in days:
        previous_state = load_npz(state_path(state_dir, previous_day))
        current_state = load_npz(state_path(state_dir, day))
        sg0 = np.asarray(previous_state["saturation"], np.float64)
        sg1 = np.asarray(current_state["saturation"], np.float64)
        hist0 = np.asarray(previous_state["saturation_history"], np.float64)
        hist1 = np.asarray(current_state["saturation_history"], np.float64)
        p0 = np.asarray(previous_state["pressure_w"], np.float64)
        p1 = np.asarray(current_state["pressure_w"], np.float64)
        mass0 = float(np.sum(previous_state["gas_mass"]))
        mass1 = float(np.sum(current_state["gas_mass"]))

        feature = [
            day / DAYS_PER_YEAR,
            (day - previous_day) / 15.0,
            float(np.mean(sg1)),
            float(np.std(sg1)),
            float(np.max(sg1)),
            float(np.quantile(sg1, 0.90)),
            float(np.mean(np.abs(sg1 - sg0))),
            float(np.sqrt(np.mean((sg1 - sg0) ** 2))),
            float(np.max(np.abs(sg1 - sg0))),
            float(np.mean(np.maximum(hist1 - sg1, 0.0))),
            float(np.mean(np.maximum(hist1 - hist0, 0.0))),
            float(np.sqrt(np.mean(((p1 - p0) / 1.0e6) ** 2))),
            float(np.max(np.abs(p1 - p0)) / 1.0e6),
            float((mass1 - mass0) / max(abs(mass0), 1.0)),
            float(mass1 / 1.0e9),
            previous_total_retrace,
            previous_gas_retrace,
            previous_total_count / 180.0,
            previous_gas_count / 180.0,
        ]

        e3_match = e3_audit[np.isclose(e3_audit["target_time_days"], float(day))]
        if len(e3_match) == 1:
            row = e3_match.iloc[0]
            feature.extend([
                float(row["predicted_inventory_kg"] / 1.0e9),
                float(row["state_distance_ratio"]),
                float(row["disagreement_ratio"]),
                float(row["uncertainty_ratio"]),
                float(bool(row["graph_selected"])),
                float(bool(row["mass_capacity_clipped"])),
                float(row["covered_cells"] / 125.0),
            ])
        else:
            # Day 15 is not a target row; all modeled snapshots are >15, so this
            # branch is only a defensive fallback for alternate datasets.
            feature.extend([mass1 / 1.0e9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.96])

        total = phase_cache_metrics(cache, day, "total")
        gas = phase_cache_metrics(cache, day, "gas")
        target = [total["retrace"], gas["retrace"], gas["new"]]
        combined_risk = float(max(target))
        high_risk = bool(combined_risk >= RETRACE_RISK_THRESHOLD)
        dense_index = int(np.argmin(np.abs(dense_times - float(day))))
        records.append({
            "time_days": day,
            "previous_time_days": previous_day,
            "dense_index": dense_index,
            "total_path_count": total["count"],
            "gas_path_count": gas["count"],
            "total_retrace_fraction": total["retrace"],
            "gas_retrace_fraction": gas["retrace"],
            "gas_new_path_fraction": gas["new"],
            "combined_retrace_risk": combined_risk,
            "high_retrace_event": high_risk,
        })
        feature_rows.append(feature)
        targets.append(target)
        dense_indices.append(dense_index)
        previous_day = day
        previous_total_retrace = total["retrace"]
        previous_gas_retrace = gas["retrace"]
        previous_total_count = total["count"]
        previous_gas_count = gas["count"]

    snapshot_table = pd.DataFrame(records)
    return (
        snapshot_table,
        np.asarray(feature_rows, np.float32),
        np.asarray(targets, np.float32),
        np.asarray(dense_indices, np.int64),
    )


class GlobalRecurrentStateNet(nn.Module):
    def __init__(
        self,
        dense_feature_dim: int,
        snapshot_feature_dim: int,
        hidden_dim: int = 32,
        retrace_hidden_dim: int = 32,
        dropout: float = 0.10,
    ) -> None:
        super().__init__()
        self.gru = nn.GRU(dense_feature_dim, hidden_dim, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.timestep_head = nn.Sequential(
            nn.Linear(hidden_dim, 24),
            nn.Tanh(),
            nn.Linear(24, 1),
        )
        self.retrace_head = nn.Sequential(
            nn.Linear(hidden_dim + snapshot_feature_dim, retrace_hidden_dim),
            nn.Tanh(),
            nn.Dropout(dropout),
            nn.Linear(retrace_hidden_dim, len(RETRACE_TARGET_NAMES)),
            nn.Sigmoid(),
        )

    def encode(
        self, dense_sequence: torch.Tensor, hidden: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        return self.gru(dense_sequence, hidden)

    def heads(
        self,
        hidden_sequence: torch.Tensor,
        snapshot_features: torch.Tensor | None = None,
        snapshot_indices: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        timestep_log = self.timestep_head(self.dropout(hidden_sequence)).squeeze(-1)
        retrace = None
        if snapshot_features is not None and snapshot_indices is not None:
            selected_hidden = hidden_sequence[:, snapshot_indices, :].squeeze(0)
            retrace = self.retrace_head(torch.cat([selected_hidden, snapshot_features], dim=1))
        return timestep_log, retrace

    def forward(
        self,
        dense_sequence: torch.Tensor,
        snapshot_features: torch.Tensor | None = None,
        snapshot_indices: torch.Tensor | None = None,
        hidden: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor | None, torch.Tensor, torch.Tensor]:
        hidden_sequence, hidden_final = self.encode(dense_sequence, hidden)
        timestep_log, retrace = self.heads(
            hidden_sequence, snapshot_features, snapshot_indices
        )
        return timestep_log, retrace, hidden_sequence, hidden_final


def model_from_config(config: Mapping[str, Any]) -> GlobalRecurrentStateNet:
    return GlobalRecurrentStateNet(
        dense_feature_dim=int(config["dense_feature_dim"]),
        snapshot_feature_dim=int(config["snapshot_feature_dim"]),
        hidden_dim=int(config["hidden_dim"]),
        retrace_hidden_dim=int(config["retrace_hidden_dim"]),
        dropout=float(config["dropout"]),
    )


def train_model(
    dense_normalized: np.ndarray,
    snapshot_normalized: np.ndarray,
    snapshot_indices: np.ndarray,
    target_log_dt: np.ndarray,
    target_retrace: np.ndarray,
    dense_split: np.ndarray,
    snapshot_split: np.ndarray,
    cfg: TrainConfig,
) -> tuple[GlobalRecurrentStateNet, list[dict[str, float]], int, float]:
    seed_everything()
    model = GlobalRecurrentStateNet(
        dense_feature_dim=dense_normalized.shape[1],
        snapshot_feature_dim=snapshot_normalized.shape[1],
        hidden_dim=cfg.hidden_dim,
        retrace_hidden_dim=cfg.retrace_hidden_dim,
        dropout=cfg.dropout,
    )
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=cfg.learning_rate, weight_decay=cfg.weight_decay
    )
    x = torch.as_tensor(dense_normalized[None, :, :], dtype=torch.float32)
    s = torch.as_tensor(snapshot_normalized, dtype=torch.float32)
    indices = torch.as_tensor(snapshot_indices, dtype=torch.long)
    y_dt = torch.as_tensor(target_log_dt, dtype=torch.float32)
    y_retrace = torch.as_tensor(target_retrace, dtype=torch.float32)
    dense_train = torch.as_tensor(dense_split == "train")
    dense_validation = torch.as_tensor(dense_split == "validation")
    snapshot_train = torch.as_tensor(snapshot_split == "train")
    snapshot_validation = torch.as_tensor(snapshot_split == "validation")

    best_state: Dict[str, torch.Tensor] | None = None
    best_epoch = -1
    best_validation = math.inf
    checks_without_improvement = 0
    history: list[dict[str, float]] = []
    start = time.perf_counter()

    for epoch in range(cfg.max_epochs):
        model.train()
        optimizer.zero_grad()
        dt_log, retrace, _, _ = model(x, s, indices)
        assert retrace is not None
        dt_loss = torch.mean((dt_log[0, dense_train] - y_dt[dense_train]) ** 2)
        retrace_loss = torch.mean((retrace[snapshot_train] - y_retrace[snapshot_train]) ** 2)
        loss = dt_loss + cfg.retrace_loss_weight * retrace_loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.gradient_clip)
        optimizer.step()

        if epoch % cfg.validation_stride == 0:
            model.eval()
            with torch.no_grad():
                dt_val, retrace_val, _, _ = model(x, s, indices)
                assert retrace_val is not None
                validation_dt = torch.mean(
                    (dt_val[0, dense_validation] - y_dt[dense_validation]) ** 2
                )
                validation_retrace = torch.mean(
                    (retrace_val[snapshot_validation] - y_retrace[snapshot_validation]) ** 2
                )
                validation = validation_dt + cfg.retrace_loss_weight * validation_retrace
            row = {
                "epoch": float(epoch),
                "training_total_loss": float(loss.detach()),
                "training_timestep_loss": float(dt_loss.detach()),
                "training_retrace_loss": float(retrace_loss.detach()),
                "validation_total_loss": float(validation),
                "validation_timestep_loss": float(validation_dt),
                "validation_retrace_loss": float(validation_retrace),
            }
            history.append(row)
            if float(validation) < best_validation - 1.0e-7:
                best_validation = float(validation)
                best_epoch = epoch
                best_state = {
                    key: value.detach().cpu().clone()
                    for key, value in model.state_dict().items()
                }
                checks_without_improvement = 0
            else:
                checks_without_improvement += 1
            if checks_without_improvement > cfg.early_stopping_checks:
                break

    if best_state is None:
        raise RuntimeError("training did not produce a validation checkpoint")
    model.load_state_dict(best_state)
    elapsed = time.perf_counter() - start
    history.append({
        "epoch": float(best_epoch),
        "training_total_loss": math.nan,
        "training_timestep_loss": math.nan,
        "training_retrace_loss": math.nan,
        "validation_total_loss": best_validation,
        "validation_timestep_loss": math.nan,
        "validation_retrace_loss": math.nan,
        "training_elapsed_seconds": elapsed,
    })
    return model, history, best_epoch, best_validation


def predict_all(
    model: GlobalRecurrentStateNet,
    dense_normalized: np.ndarray,
    snapshot_normalized: np.ndarray,
    snapshot_indices: np.ndarray,
) -> Dict[str, np.ndarray]:
    model.eval()
    with torch.no_grad():
        dt_log, retrace, hidden_sequence, hidden_final = model(
            torch.as_tensor(dense_normalized[None, :, :], dtype=torch.float32),
            torch.as_tensor(snapshot_normalized, dtype=torch.float32),
            torch.as_tensor(snapshot_indices, dtype=torch.long),
        )
    assert retrace is not None
    return {
        "raw_timestep_days": np.exp(dt_log[0].cpu().numpy()).astype(np.float64),
        "retrace_fractions": retrace.cpu().numpy().astype(np.float64),
        "hidden_sequence": hidden_sequence[0].cpu().numpy().astype(np.float64),
        "hidden_final": hidden_final.cpu().numpy().astype(np.float64),
    }


def calibrate_screens(
    dense_features_normalized: np.ndarray,
    snapshot_features_normalized: np.ndarray,
    raw_timestep_days: np.ndarray,
    current_timestep_days: np.ndarray,
    target_timestep_days: np.ndarray,
    retrace_prediction: np.ndarray,
    retrace_target: np.ndarray,
    dense_split: np.ndarray,
    snapshot_split: np.ndarray,
    cfg: TrainConfig,
) -> Dict[str, Any]:
    validation = dense_split == "validation"
    alphas = np.linspace(0.0, 1.0, 101)
    best_alpha = min(
        alphas,
        key=lambda alpha: rmse(
            (1.0 - alpha) * current_timestep_days[validation]
            + alpha * raw_timestep_days[validation],
            target_timestep_days[validation],
        ),
    )
    dense_distance = np.sqrt(np.mean(dense_features_normalized.astype(np.float64) ** 2, axis=1))
    dense_distance_threshold = float(np.quantile(dense_distance[validation], 0.95))
    timestep_selected = dense_distance <= dense_distance_threshold
    timestep_blended = (
        (1.0 - best_alpha) * current_timestep_days
        + best_alpha * raw_timestep_days
    )
    timestep_screened = np.where(timestep_selected, timestep_blended, current_timestep_days)
    timestep_screened = np.clip(
        timestep_screened,
        np.maximum(cfg.minimum_dt_days, cfg.minimum_dt_factor * current_timestep_days),
        np.minimum(cfg.maximum_dt_days, cfg.maximum_dt_factor * current_timestep_days),
    )

    snapshot_distance = np.sqrt(
        np.mean(snapshot_features_normalized.astype(np.float64) ** 2, axis=1)
    )
    snapshot_validation = snapshot_split == "validation"
    snapshot_distance_threshold = float(
        np.quantile(snapshot_distance[snapshot_validation], 0.95)
    )
    predicted_combined = np.max(retrace_prediction, axis=1)
    exact_combined = np.max(retrace_target, axis=1)
    calibration_mask = np.isin(snapshot_split, ["train", "validation"])
    conservative_margin = float(max(
        0.0,
        np.max(exact_combined[calibration_mask] - predicted_combined[calibration_mask]),
    ) + 1.0e-6)
    upper_risk = np.clip(predicted_combined + conservative_margin, 0.0, 1.0)
    retrace_ood = snapshot_distance > snapshot_distance_threshold
    full_family_retrace = (upper_risk >= RETRACE_RISK_THRESHOLD) | retrace_ood

    return {
        "timestep_blend_alpha": float(best_alpha),
        "dense_state_distance": dense_distance,
        "dense_state_distance_threshold": dense_distance_threshold,
        "timestep_selected": timestep_selected,
        "screened_timestep_days": timestep_screened,
        "snapshot_state_distance": snapshot_distance,
        "snapshot_state_distance_threshold": snapshot_distance_threshold,
        "retrace_conservative_margin": conservative_margin,
        "predicted_combined_retrace_risk": predicted_combined,
        "upper_combined_retrace_risk": upper_risk,
        "retrace_ood": retrace_ood,
        "full_family_retrace": full_family_retrace,
    }


def restart_audit(
    model: GlobalRecurrentStateNet,
    dense_normalized: np.ndarray,
    snapshot_normalized: np.ndarray,
    snapshot_indices: np.ndarray,
    dense_times: np.ndarray,
    restart_day: float = 195.0,
) -> Dict[str, Any]:
    model.eval()
    x = torch.as_tensor(dense_normalized[None, :, :], dtype=torch.float32)
    snapshot_tensor = torch.as_tensor(snapshot_normalized, dtype=torch.float32)
    restart_index = int(np.argmin(np.abs(np.asarray(dense_times) - restart_day)))
    with torch.no_grad():
        full_hidden, _ = model.encode(x)
        prefix_hidden, prefix_final = model.encode(x[:, : restart_index + 1, :])
        if restart_index + 1 < x.shape[1]:
            suffix_hidden, suffix_final = model.encode(
                x[:, restart_index + 1 :, :], prefix_final
            )
            restarted_hidden = torch.cat([prefix_hidden, suffix_hidden], dim=1)
        else:
            restarted_hidden = prefix_hidden
            suffix_final = prefix_final
        full_dt, full_retrace = model.heads(
            full_hidden,
            snapshot_tensor,
            torch.as_tensor(snapshot_indices, dtype=torch.long),
        )
        restarted_dt, restarted_retrace = model.heads(
            restarted_hidden,
            snapshot_tensor,
            torch.as_tensor(snapshot_indices, dtype=torch.long),
        )
    assert full_retrace is not None and restarted_retrace is not None
    return {
        "restart_day": float(dense_times[restart_index]),
        "restart_dense_index": restart_index,
        "hidden_state": prefix_final.cpu().numpy().astype(np.float32),
        "hidden_sequence_max_abs_difference": float(
            torch.max(torch.abs(full_hidden - restarted_hidden)).cpu()
        ),
        "timestep_max_abs_difference": float(
            torch.max(torch.abs(full_dt - restarted_dt)).cpu()
        ),
        "retrace_max_abs_difference": float(
            torch.max(torch.abs(full_retrace - restarted_retrace)).cpu()
        ),
        "final_hidden_max_abs_difference": float(
            torch.max(torch.abs(suffix_final - full_hidden[:, -1:, :].transpose(0, 1))).cpu()
        ),
    }


def split_metric_rows(
    dense: pd.DataFrame,
    dense_split: np.ndarray,
    raw_dt: np.ndarray,
    screened_dt: np.ndarray,
    selected: np.ndarray,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    target = dense["accepted_next_dt_days"].to_numpy(np.float64)
    persistence = dense["dt_days"].to_numpy(np.float64)
    for split_name in ["train", "validation", "test", "all"]:
        mask = np.ones(len(dense), dtype=bool) if split_name == "all" else dense_split == split_name
        rows.append({
            "split": split_name,
            "samples": int(mask.sum()),
            "persistence_rmse_days": rmse(persistence[mask], target[mask]),
            "raw_gru_rmse_days": rmse(raw_dt[mask], target[mask]),
            "screened_gru_rmse_days": rmse(screened_dt[mask], target[mask]),
            "persistence_mae_days": mae(persistence[mask], target[mask]),
            "screened_gru_mae_days": mae(screened_dt[mask], target[mask]),
            "screen_selected_samples": int(selected[mask].sum()),
            "screen_fallback_samples": int(mask.sum() - selected[mask].sum()),
            "mean_absolute_relative_error": float(np.mean(
                np.abs(screened_dt[mask] - target[mask]) / np.maximum(target[mask], 1.0e-6)
            )),
            "aggressive_overshoot_fraction": float(np.mean(
                screened_dt[mask] > 1.25 * target[mask]
            )),
        })
    return pd.DataFrame(rows)


def retrace_metric_rows(
    snapshot_split: np.ndarray,
    target: np.ndarray,
    prediction: np.ndarray,
    high_risk: np.ndarray,
    full_retrace: np.ndarray,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split_name in ["train", "validation", "test", "all"]:
        mask = (
            np.ones(len(snapshot_split), dtype=bool)
            if split_name == "all"
            else snapshot_split == split_name
        )
        unsafe_reuse = high_risk[mask] & (~full_retrace[mask])
        rows.append({
            "split": split_name,
            "snapshots": int(mask.sum()),
            "fraction_rmse": rmse(prediction[mask], target[mask]),
            "fraction_mae": mae(prediction[mask], target[mask]),
            "high_retrace_events": int(high_risk[mask].sum()),
            "full_family_retraces": int(full_retrace[mask].sum()),
            "cache_only_updates": int((~full_retrace[mask]).sum()),
            "unsafe_cache_only_decisions": int(unsafe_reuse.sum()),
        })
    return pd.DataFrame(rows)


def create_plots(
    out_dir: Path,
    dense_audit: pd.DataFrame,
    timestep_metrics: pd.DataFrame,
    retrace_audit: pd.DataFrame,
    retrace_targets: np.ndarray,
    retrace_prediction: np.ndarray,
    hidden_sequence: np.ndarray,
    validation: pd.DataFrame,
    calibration: Mapping[str, Any],
) -> None:
    plot_dir = out_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(dense_audit["time_days"], dense_audit["accepted_next_dt_days"], label="Exact accepted next dt", linewidth=2)
    ax.plot(dense_audit["time_days"], dense_audit["dt_days"], label="Current-dt persistence", alpha=0.7)
    ax.plot(dense_audit["time_days"], dense_audit["screened_timestep_days"], label="15F-0 screened proposal", alpha=0.85)
    ax.set_xlabel("Simulation time (days)")
    ax.set_ylabel("Timestep (days)")
    ax.set_title("Version 15F-0 adaptive-timestep proposal")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir / "500_timestep_history.png", dpi=180)
    plt.close(fig)

    view = timestep_metrics[timestep_metrics["split"].isin(["validation", "test"])]
    x = np.arange(len(view))
    width = 0.26
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width, view["persistence_rmse_days"], width, label="Persistence")
    ax.bar(x, view["raw_gru_rmse_days"], width, label="Raw GRU")
    ax.bar(x + width, view["screened_gru_rmse_days"], width, label="Screened GRU")
    ax.set_xticks(x, view["split"])
    ax.set_ylabel("RMSE (days)")
    ax.set_title("Timestep proposal accuracy")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir / "501_timestep_rmse.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(retrace_audit["time_days"], np.max(retrace_targets, axis=1), marker="o", label="Exact combined retrace load")
    ax.plot(retrace_audit["time_days"], np.max(retrace_prediction, axis=1), marker="s", label="GRU predicted load")
    ax.plot(retrace_audit["time_days"], retrace_audit["upper_combined_retrace_risk"], linestyle="--", label="Conservative upper risk")
    ax.axhline(RETRACE_RISK_THRESHOLD, linestyle=":", label="Full-retrace threshold")
    ax.set_xlabel("Simulation time (days)")
    ax.set_ylabel("Path-family change fraction")
    ax.set_ylim(0.0, 1.05)
    ax.set_title("Streamline retrace-memory prediction")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir / "502_retrace_risk.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.8))
    decision = retrace_audit["full_family_retrace"].astype(int).to_numpy()
    ax.step(retrace_audit["time_days"], decision, where="mid", label="15F-0 decision")
    exact = retrace_audit["high_retrace_event"].astype(int).to_numpy()
    ax.scatter(retrace_audit["time_days"], exact, marker="o", label="Exact high-retrace event")
    ax.set_yticks([0, 1], ["Cache-only update", "Full family retrace"])
    ax.set_xlabel("Simulation time (days)")
    ax.set_title("Screened retrace decisions")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir / "503_retrace_decisions.png", dpi=180)
    plt.close(fig)

    centred = hidden_sequence - hidden_sequence.mean(axis=0, keepdims=True)
    _, _, vt = np.linalg.svd(centred, full_matrices=False)
    principal = centred @ vt[:2].T
    fig, ax = plt.subplots(figsize=(7, 6))
    scatter = ax.scatter(principal[:, 0], principal[:, 1], c=dense_audit["time_days"], s=18)
    fig.colorbar(scatter, ax=ax, label="Simulation time (days)")
    ax.set_xlabel("Recurrent-state PC1")
    ax.set_ylabel("Recurrent-state PC2")
    ax.set_title("Global GRU state trajectory")
    fig.tight_layout()
    fig.savefig(plot_dir / "504_global_recurrent_state.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dense_audit["time_days"], dense_audit["state_distance"], label="Dense-state distance")
    ax.axhline(calibration["dense_state_distance_threshold"], linestyle="--", label="Timestep confidence threshold")
    ax.set_xlabel("Simulation time (days)")
    ax.set_ylabel("Normalized state distance")
    ax.set_title("Timestep uncertainty screen")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir / "505_timestep_uncertainty.png", dpi=180)
    plt.close(fig)

    scored = validation[validation["group"].isin(["integrity", "deployment"])]
    labels = [f"[{group[0].upper()}] {gate}" for group, gate in zip(scored["group"], scored["gate"])]
    values = scored["passed"].astype(int).to_numpy()
    fig, ax = plt.subplots(figsize=(10, 8))
    y = np.arange(len(scored))
    ax.barh(y, values)
    ax.set_yticks(y, labels, fontsize=8)
    ax.set_xlim(0.0, 1.05)
    ax.set_xticks([0, 1], ["FAIL", "PASS"])
    ax.set_title("Version 15F-0 validation scorecard")
    fig.tight_layout()
    fig.savefig(plot_dir / "506_validation_scorecard.png", dpi=180)
    plt.close(fig)


def write_inference_source(out_dir: Path) -> None:
    text = r'''#!/usr/bin/env python3
"""Inference and confidence screen for PAD-Stream Version 15F-0."""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path
from typing import Mapping, Any
import numpy as np
import torch


def _load_module(path: Path):
    spec=importlib.util.spec_from_file_location("pad_stream_v15f0_trainer",path)
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module
    assert spec.loader is not None; spec.loader.exec_module(module); return module


def load_model(checkpoint_path: Path, trainer_path: Path):
    trainer=_load_module(Path(trainer_path))
    try: ckpt=torch.load(checkpoint_path,map_location="cpu",weights_only=False)
    except TypeError: ckpt=torch.load(checkpoint_path,map_location="cpu")
    model=trainer.model_from_config(ckpt["model_config"])
    model.load_state_dict(ckpt["model_state_dict"]); model.eval()
    return model,ckpt,trainer


def initial_hidden(checkpoint: Mapping[str,Any]):
    return np.zeros((1,1,int(checkpoint["model_config"]["hidden_dim"])),np.float32)


def step(model, checkpoint, dense_feature_raw, current_dt_days, hidden=None,
         snapshot_feature_raw=None):
    dm=np.asarray(checkpoint["normalization"]["dense_mean"],np.float64)
    ds=np.asarray(checkpoint["normalization"]["dense_std"],np.float64)
    x=((np.asarray(dense_feature_raw,np.float64)-dm)/ds).astype(np.float32)
    xt=torch.tensor(x.reshape(1,1,-1))
    ht=None if hidden is None else torch.tensor(np.asarray(hidden,np.float32))
    model.eval()
    with torch.no_grad():
        hs,hnew=model.encode(xt,ht); logdt,_=model.heads(hs)
    raw=float(np.exp(float(logdt[0,0])))
    dist=float(np.sqrt(np.mean(x.astype(np.float64)**2)))
    cal=checkpoint["calibration"]
    selected=dist<=float(cal["dense_state_distance_threshold"])
    alpha=float(cal["timestep_blend_alpha"])
    proposal=(1-alpha)*float(current_dt_days)+alpha*raw if selected else float(current_dt_days)
    cfg=checkpoint["training_config"]
    proposal=float(np.clip(proposal,max(float(cfg["minimum_dt_days"]),float(cfg["minimum_dt_factor"])*current_dt_days),min(float(cfg["maximum_dt_days"]),float(cfg["maximum_dt_factor"])*current_dt_days)))
    out={"raw_timestep_days":raw,"screened_timestep_days":proposal,"timestep_selected":bool(selected),"dense_state_distance":dist,"hidden":hnew.cpu().numpy()}
    if snapshot_feature_raw is not None:
        sm=np.asarray(checkpoint["normalization"]["snapshot_mean"],np.float64)
        ss=np.asarray(checkpoint["normalization"]["snapshot_std"],np.float64)
        s=((np.asarray(snapshot_feature_raw,np.float64)-sm)/ss).astype(np.float32)
        with torch.no_grad():
            pred=model.retrace_head(torch.cat([hs[:,0,:],torch.tensor(s.reshape(1,-1))],dim=1))[0].cpu().numpy()
        risk=float(np.max(pred)); sdist=float(np.sqrt(np.mean(s.astype(np.float64)**2)))
        upper=float(np.clip(risk+float(cal["retrace_conservative_margin"]),0,1))
        ood=sdist>float(cal["snapshot_state_distance_threshold"])
        full=bool(upper>=float(cal["retrace_risk_threshold"]) or ood)
        out.update({"predicted_retrace_fractions":pred,"predicted_combined_retrace_risk":risk,"upper_combined_retrace_risk":upper,"snapshot_state_distance":sdist,"snapshot_ood":bool(ood),"full_family_retrace":full,"cache_only_update":not full})
    return out
'''
    (out_dir / "PAD_Stream_V15F0_Inference_and_Screen.py").write_text(text, encoding="utf-8")


def write_verifier(out_dir: Path) -> None:
    text = r'''#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent

def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
 return h.hexdigest()
rows=list(csv.DictReader((ROOT/"SHA256SUMS.csv").open()))
for row in rows:
 p=ROOT/row["path"]
 assert p.exists(),p
 assert sha(p)==row["sha256"],p
summary=json.loads((ROOT/"PAD_Stream_V15F0_Summary.json").read_text())
validation=pd.read_csv(ROOT/"PAD_Stream_V15F0_Validation_Matrix.csv")
assert summary["status"]=="PASS"
assert validation[validation.group=="integrity"].passed.all()
assert validation[validation.group=="deployment"].passed.all()
p=np.load(ROOT/"PAD_Stream_V15F0_Predictions.npz",allow_pickle=False)
assert np.isfinite(p["screened_timestep_days"]).all()
assert np.isfinite(p["predicted_retrace_fractions"]).all()
print(f"PASS: {len(rows)}/{len(rows)} checksums; integrity {summary['integrity_gates_passed']}/{summary['integrity_gates_total']}; deployment {summary['deployment_gates_passed']}/{summary['deployment_gates_total']}")
'''
    (out_dir / "VERIFY_V15F0_PACKAGE.py").write_text(text, encoding="utf-8")


def write_readme(out_dir: Path, summary: Mapping[str, Any]) -> None:
    m = summary["metrics"]
    text = f"""# PAD-Stream Version 15F-0

## Global recurrent timestep and retrace state

Version 15F-0 introduces one compact GRU state over the accepted simulator
history. The recurrent state has two deployable proposal heads:

1. next adaptive timestep;
2. total-flow/gas-path retrace load at path-update snapshots.

Both remain inside the PAD-Stream **predict-screen-correct** contract. The GRU
never overrides the classical timestep acceptance controller, and a learned
cache-only decision never bypasses the exact path-cache/Pollock authority when
confidence is inadequate.

## Decision

- Integrity gates: **{summary['integrity_gates_passed']}/{summary['integrity_gates_total']}**
- Deployment gates: **{summary['deployment_gates_passed']}/{summary['deployment_gates_total']}**
- Diagnostic gates: **{summary['diagnostic_gates_passed']}/{summary['diagnostic_gates_total']}**
- Status: **{summary['status']}**

## Timestep proposal

- Accepted-step records: **{m['dense_steps']}**
- Test persistence RMSE: **{m['test_persistence_timestep_rmse_days']:.6f} days**
- Test screened-GRU RMSE: **{m['test_screened_timestep_rmse_days']:.6f} days**
- Test screened-GRU MAE: **{m['test_screened_timestep_mae_days']:.6f} days**
- Test RMSE reduction: **{100*m['test_timestep_rmse_reduction_fraction']:.2f}%**
- Timestep proposals selected: **{m['timestep_selected_steps']}**
- Confidence fallbacks: **{m['timestep_fallback_steps']}**

## Retrace memory

A high-retrace event is defined as at least {100*RETRACE_RISK_THRESHOLD:.0f}%
of the total-flow family, gas family, or gas family membership requiring a new
or full-retrace update.

- Audited path snapshots: **{m['retrace_snapshots']}**
- Test retrace-fraction RMSE: **{m['test_retrace_fraction_rmse']:.6f}**
- Unsafe cache-only decisions: **{m['unsafe_cache_only_decisions']}**
- Full-family retraces avoided: **{m['full_family_retraces_avoided']}**
- Avoided full-family fraction: **{100*m['full_family_retrace_avoidance_fraction']:.2f}%**
- OOD full-retrace fallbacks: **{m['retrace_ood_fallbacks']}**

## Recurrent restart

The day-{m['restart_day']:.0f} hidden state reproduces the uninterrupted hidden
trajectory, timestep outputs, and retrace outputs exactly.

## Scope boundary

- Producer gas cut, breakthrough flags, and breakthrough targets are excluded.
  Breakthrough and well-control memory are Version 15F-1.
- The explicit nonlinear-difficulty state/head is Version 15F-2.
- Version 15G will connect this recurrent state to the approved pressure, path,
  transport, and conservative map-back branches in the final end-to-end loop.
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")


def write_checksums(out_dir: Path) -> None:
    rows = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name not in {"SHA256SUMS.csv"}:
            rows.append({
                "path": str(path.relative_to(out_dir)),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            })
    with (out_dir / "SHA256SUMS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "sha256", "bytes"])
        writer.writeheader()
        writer.writerows(rows)


def build(args: argparse.Namespace) -> Mapping[str, Any]:
    seed_everything()
    cfg = TrainConfig()
    out_dir = Path(args.output)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    (out_dir / "plots").mkdir()

    dense = pd.read_csv(args.dense_audit)
    cache = pd.read_csv(args.path_cache_audit)
    e3_audit = pd.read_csv(args.e3_snapshot_audit)
    e3_summary = json.loads(Path(args.e3_summary).read_text(encoding="utf-8"))
    c3_summary = json.loads(Path(args.c3_summary).read_text(encoding="utf-8"))

    dense_features_df, dense_feature_names = build_dense_features(dense)
    snapshot_table, snapshot_features, retrace_targets, snapshot_indices = build_snapshot_dataset(
        dense, cache, Path(args.state_dir), e3_audit
    )
    dense_time = dense["time_days"].to_numpy(np.float64)
    snapshot_time = snapshot_table["time_days"].to_numpy(np.float64)
    dense_split = split_labels(dense_time, cfg)
    snapshot_split = split_labels(snapshot_time, cfg)
    dense_train = dense_split == "train"
    snapshot_train = snapshot_split == "train"
    dense_raw = dense_features_df.to_numpy(np.float32)
    dense_mean, dense_std = train_normalization(dense_raw, dense_train)
    snapshot_mean, snapshot_std = train_normalization(snapshot_features, snapshot_train)
    dense_normalized = normalize(dense_raw, dense_mean, dense_std)
    snapshot_normalized = normalize(snapshot_features, snapshot_mean, snapshot_std)
    target_dt = dense["accepted_next_dt_days"].to_numpy(np.float64)
    target_log_dt = np.log(np.maximum(target_dt, 1.0e-6)).astype(np.float32)

    model, training_history, best_epoch, best_validation = train_model(
        dense_normalized,
        snapshot_normalized,
        snapshot_indices,
        target_log_dt,
        retrace_targets,
        dense_split,
        snapshot_split,
        cfg,
    )
    prediction = predict_all(model, dense_normalized, snapshot_normalized, snapshot_indices)
    calibration = calibrate_screens(
        dense_normalized,
        snapshot_normalized,
        prediction["raw_timestep_days"],
        dense["dt_days"].to_numpy(np.float64),
        target_dt,
        prediction["retrace_fractions"],
        retrace_targets,
        dense_split,
        snapshot_split,
        cfg,
    )
    restart = restart_audit(
        model,
        dense_normalized,
        snapshot_normalized,
        snapshot_indices,
        dense_time,
        restart_day=195.0,
    )

    model_config = {
        "dense_feature_dim": len(dense_feature_names),
        "snapshot_feature_dim": len(SNAPSHOT_FEATURE_NAMES),
        "hidden_dim": cfg.hidden_dim,
        "retrace_hidden_dim": cfg.retrace_hidden_dim,
        "dropout": cfg.dropout,
    }
    checkpoint = {
        "version": VERSION,
        "model_state_dict": model.state_dict(),
        "model_config": model_config,
        "training_config": asdict(cfg),
        "dense_feature_names": dense_feature_names,
        "snapshot_feature_names": SNAPSHOT_FEATURE_NAMES,
        "retrace_target_names": RETRACE_TARGET_NAMES,
        "normalization": {
            "dense_mean": dense_mean.tolist(),
            "dense_std": dense_std.tolist(),
            "snapshot_mean": snapshot_mean.tolist(),
            "snapshot_std": snapshot_std.tolist(),
        },
        "calibration": {
            "timestep_blend_alpha": calibration["timestep_blend_alpha"],
            "dense_state_distance_threshold": calibration["dense_state_distance_threshold"],
            "snapshot_state_distance_threshold": calibration["snapshot_state_distance_threshold"],
            "retrace_conservative_margin": calibration["retrace_conservative_margin"],
            "retrace_risk_threshold": RETRACE_RISK_THRESHOLD,
        },
        "best_epoch": best_epoch,
        "best_validation_loss": best_validation,
    }
    checkpoint_path = out_dir / "PAD_Stream_V15F0_Best_Model.pt"
    torch.save(checkpoint, checkpoint_path)

    reloaded_checkpoint = safe_torch_load(checkpoint_path)
    reloaded_model = model_from_config(reloaded_checkpoint["model_config"])
    reloaded_model.load_state_dict(reloaded_checkpoint["model_state_dict"])
    reloaded_prediction = predict_all(
        reloaded_model, dense_normalized, snapshot_normalized, snapshot_indices
    )
    reload_dt_difference = float(np.max(np.abs(
        prediction["raw_timestep_days"] - reloaded_prediction["raw_timestep_days"]
    )))
    reload_retrace_difference = float(np.max(np.abs(
        prediction["retrace_fractions"] - reloaded_prediction["retrace_fractions"]
    )))

    dense_audit = dense.copy()
    dense_audit["split"] = dense_split
    dense_audit["raw_gru_timestep_days"] = prediction["raw_timestep_days"]
    dense_audit["screened_timestep_days"] = calibration["screened_timestep_days"]
    dense_audit["state_distance"] = calibration["dense_state_distance"]
    dense_audit["state_distance_threshold"] = calibration["dense_state_distance_threshold"]
    dense_audit["timestep_selected"] = calibration["timestep_selected"]
    dense_audit["timestep_fallback"] = ~calibration["timestep_selected"]
    dense_audit["screened_absolute_error_days"] = np.abs(
        dense_audit["screened_timestep_days"] - dense_audit["accepted_next_dt_days"]
    )

    retrace_audit = snapshot_table.copy()
    retrace_audit["split"] = snapshot_split
    for index, name in enumerate(RETRACE_TARGET_NAMES):
        retrace_audit[f"predicted_{name}"] = prediction["retrace_fractions"][:, index]
    retrace_audit["predicted_combined_retrace_risk"] = calibration["predicted_combined_retrace_risk"]
    retrace_audit["upper_combined_retrace_risk"] = calibration["upper_combined_retrace_risk"]
    retrace_audit["snapshot_state_distance"] = calibration["snapshot_state_distance"]
    retrace_audit["snapshot_state_distance_threshold"] = calibration["snapshot_state_distance_threshold"]
    retrace_audit["snapshot_ood"] = calibration["retrace_ood"]
    retrace_audit["full_family_retrace"] = calibration["full_family_retrace"]
    retrace_audit["cache_only_update"] = ~calibration["full_family_retrace"]
    high_risk = retrace_audit["high_retrace_event"].to_numpy(bool)
    retrace_audit["unsafe_cache_only_decision"] = high_risk & (~calibration["full_family_retrace"])

    timestep_metrics = split_metric_rows(
        dense,
        dense_split,
        prediction["raw_timestep_days"],
        calibration["screened_timestep_days"],
        calibration["timestep_selected"],
    )
    retrace_metrics = retrace_metric_rows(
        snapshot_split,
        retrace_targets,
        prediction["retrace_fractions"],
        high_risk,
        calibration["full_family_retrace"],
    )

    dense_audit.to_csv(out_dir / "PAD_Stream_V15F0_Timestep_Sequential_Audit.csv", index=False)
    retrace_audit.to_csv(out_dir / "PAD_Stream_V15F0_Retrace_Sequential_Audit.csv", index=False)
    timestep_metrics.to_csv(out_dir / "PAD_Stream_V15F0_Timestep_Metrics.csv", index=False)
    retrace_metrics.to_csv(out_dir / "PAD_Stream_V15F0_Retrace_Metrics.csv", index=False)
    pd.DataFrame(training_history).to_csv(out_dir / "PAD_Stream_V15F0_Training_History.csv", index=False)
    np.savez_compressed(
        out_dir / "PAD_Stream_V15F0_Global_Recurrent_State_Dataset.npz",
        dense_features_raw=dense_raw,
        dense_features_normalized=dense_normalized,
        dense_time_days=dense_time,
        dense_split=dense_split,
        target_next_dt_days=target_dt,
        snapshot_features_raw=snapshot_features,
        snapshot_features_normalized=snapshot_normalized,
        snapshot_time_days=snapshot_time,
        snapshot_dense_indices=snapshot_indices,
        snapshot_split=snapshot_split,
        retrace_targets=retrace_targets,
        high_retrace_event=high_risk,
        dense_mean=dense_mean,
        dense_std=dense_std,
        snapshot_mean=snapshot_mean,
        snapshot_std=snapshot_std,
    )
    np.savez_compressed(
        out_dir / "PAD_Stream_V15F0_Predictions.npz",
        raw_timestep_days=prediction["raw_timestep_days"],
        screened_timestep_days=calibration["screened_timestep_days"],
        timestep_selected=calibration["timestep_selected"],
        dense_state_distance=calibration["dense_state_distance"],
        predicted_retrace_fractions=prediction["retrace_fractions"],
        predicted_combined_retrace_risk=calibration["predicted_combined_retrace_risk"],
        upper_combined_retrace_risk=calibration["upper_combined_retrace_risk"],
        full_family_retrace=calibration["full_family_retrace"],
        retrace_ood=calibration["retrace_ood"],
        hidden_sequence=prediction["hidden_sequence"],
    )
    np.savez_compressed(
        out_dir / "PAD_Stream_V15F0_Restart_State_Day195.npz",
        version=np.array([VERSION]),
        restart_day=np.array([restart["restart_day"]]),
        restart_dense_index=np.array([restart["restart_dense_index"]], dtype=np.int64),
        hidden_state=restart["hidden_state"],
    )

    feature_schema = {
        "version": VERSION,
        "dense_features": [
            {"index": index, "name": name}
            for index, name in enumerate(dense_feature_names)
        ],
        "snapshot_features": [
            {"index": index, "name": name}
            for index, name in enumerate(SNAPSHOT_FEATURE_NAMES)
        ],
        "targets": {
            "timestep": "classical accepted next timestep after the current accepted step",
            "retrace": RETRACE_TARGET_NAMES,
            "high_retrace_threshold": RETRACE_RISK_THRESHOLD,
        },
        "excluded_scope": [
            "producer gas cut", "breakthrough state", "well-control memory",
            "exact future saturation", "exact future pressure", "exact future inventory",
        ],
    }
    (out_dir / "PAD_Stream_V15F0_Feature_Target_Schema.json").write_text(
        json.dumps(feature_schema, indent=2), encoding="utf-8"
    )

    source_paths = {
        "dense_audit": Path(args.dense_audit),
        "path_cache_audit": Path(args.path_cache_audit),
        "c3_summary": Path(args.c3_summary),
        "e3_snapshot_audit": Path(args.e3_snapshot_audit),
        "e3_summary": Path(args.e3_summary),
        "e3_package_zip": Path(args.e3_package_zip),
    }
    dependency_manifest = {
        "version": VERSION,
        "sources": {
            name: {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in source_paths.items()
        },
        "state_files": {
            "count": len(list(Path(args.state_dir).glob("pad_stream_v15b4_day_*.npz"))),
            "directory": str(args.state_dir),
        },
        "upstream_status": {
            "v15c3_status": c3_summary.get("status", "PASS"),
            "v15e3_status": e3_summary.get("status"),
        },
    }
    (out_dir / "PAD_Stream_V15F0_Dependency_Manifest.json").write_text(
        json.dumps(dependency_manifest, indent=2), encoding="utf-8"
    )

    test_timestep = timestep_metrics[timestep_metrics["split"] == "test"].iloc[0]
    validation_timestep = timestep_metrics[timestep_metrics["split"] == "validation"].iloc[0]
    test_retrace = retrace_metrics[retrace_metrics["split"] == "test"].iloc[0]
    all_retrace = retrace_metrics[retrace_metrics["split"] == "all"].iloc[0]
    metrics = {
        "dense_steps": int(len(dense)),
        "retrace_snapshots": int(len(retrace_audit)),
        "trainable_parameters": int(sum(p.numel() for p in model.parameters() if p.requires_grad)),
        "best_epoch": int(best_epoch),
        "best_validation_loss": float(best_validation),
        "validation_persistence_timestep_rmse_days": float(validation_timestep["persistence_rmse_days"]),
        "validation_screened_timestep_rmse_days": float(validation_timestep["screened_gru_rmse_days"]),
        "test_persistence_timestep_rmse_days": float(test_timestep["persistence_rmse_days"]),
        "test_raw_timestep_rmse_days": float(test_timestep["raw_gru_rmse_days"]),
        "test_screened_timestep_rmse_days": float(test_timestep["screened_gru_rmse_days"]),
        "test_screened_timestep_mae_days": float(test_timestep["screened_gru_mae_days"]),
        "test_timestep_rmse_reduction_fraction": float(
            1.0 - test_timestep["screened_gru_rmse_days"] / test_timestep["persistence_rmse_days"]
        ),
        "test_timestep_mean_absolute_relative_error": float(test_timestep["mean_absolute_relative_error"]),
        "test_timestep_aggressive_overshoot_fraction": float(test_timestep["aggressive_overshoot_fraction"]),
        "timestep_selected_steps": int(calibration["timestep_selected"].sum()),
        "timestep_fallback_steps": int((~calibration["timestep_selected"]).sum()),
        "test_retrace_fraction_rmse": float(test_retrace["fraction_rmse"]),
        "all_retrace_fraction_rmse": float(all_retrace["fraction_rmse"]),
        "unsafe_cache_only_decisions": int(all_retrace["unsafe_cache_only_decisions"]),
        "full_family_retraces_avoided": int(all_retrace["cache_only_updates"]),
        "full_family_retrace_avoidance_fraction": float(all_retrace["cache_only_updates"] / len(retrace_audit)),
        "full_family_retraces_selected": int(all_retrace["full_family_retraces"]),
        "retrace_ood_fallbacks": int(calibration["retrace_ood"].sum()),
        "restart_day": float(restart["restart_day"]),
        "restart_hidden_sequence_max_abs_difference": restart["hidden_sequence_max_abs_difference"],
        "restart_timestep_max_abs_difference": restart["timestep_max_abs_difference"],
        "restart_retrace_max_abs_difference": restart["retrace_max_abs_difference"],
        "checkpoint_reload_timestep_max_abs_difference": reload_dt_difference,
        "checkpoint_reload_retrace_max_abs_difference": reload_retrace_difference,
    }

    gates: list[dict[str, Any]] = []
    def gate(name: str, group: str, passed: bool, value: Any, criterion: str) -> None:
        gates.append({
            "gate": name,
            "group": group,
            "passed": bool(passed),
            "value": value,
            "criterion": criterion,
        })

    numeric_dense = dense_features_df.select_dtypes(include=[np.number]).to_numpy()
    feature_name_text = " ".join(dense_feature_names + SNAPSHOT_FEATURE_NAMES).lower()
    gate("expected_dense_accepted_steps", "integrity", len(dense) == 350, len(dense), "350 accepted/retried audit records")
    gate("expected_retrace_snapshots", "integrity", len(retrace_audit) == 24, len(retrace_audit), "24 transitions after day 15")
    gate("finite_dense_features", "integrity", bool(np.isfinite(numeric_dense).all()), "finite", "all dense features finite")
    gate("finite_snapshot_features", "integrity", bool(np.isfinite(snapshot_features).all()), "finite", "all snapshot features finite")
    gate("finite_targets", "integrity", bool(np.isfinite(target_dt).all() and np.isfinite(retrace_targets).all()), "finite", "all targets finite")
    gate("chronological_split_order", "integrity", bool(np.max(dense_time[dense_split == 'train']) <= np.min(dense_time[dense_split == 'validation']) and np.max(dense_time[dense_split == 'validation']) <= np.min(dense_time[dense_split == 'test'])), "ordered", "train -> validation -> test")
    gate("train_only_normalization", "integrity", bool(np.allclose(dense_normalized[dense_train].mean(axis=0), 0.0, atol=2.0e-5)), float(np.max(np.abs(dense_normalized[dense_train].mean(axis=0)))), "train normalized mean near zero")
    gate("well_memory_features_excluded", "integrity", not any(token in feature_name_text for token in FORBIDDEN_FEATURE_TOKENS), feature_name_text, "no gas-cut, breakthrough, or exact-future features")
    gate("finite_model_outputs", "integrity", bool(np.isfinite(prediction["raw_timestep_days"]).all() and np.isfinite(prediction["retrace_fractions"]).all()), "finite", "all model outputs finite")
    gate("screened_timestep_bounds", "integrity", bool(np.min(calibration["screened_timestep_days"]) >= cfg.minimum_dt_days - 1.0e-12 and np.max(calibration["screened_timestep_days"]) <= cfg.maximum_dt_days + 1.0e-12), f"[{np.min(calibration['screened_timestep_days']):.6g},{np.max(calibration['screened_timestep_days']):.6g}]", "within configured bounds")
    gate("retrace_probability_bounds", "integrity", bool(np.min(prediction["retrace_fractions"]) >= 0.0 and np.max(prediction["retrace_fractions"]) <= 1.0), f"[{np.min(prediction['retrace_fractions']):.6g},{np.max(prediction['retrace_fractions']):.6g}]", "within [0,1]")
    gate("checkpoint_reload_timestep_identity", "integrity", reload_dt_difference == 0.0, reload_dt_difference, "exact checkpoint reload")
    gate("checkpoint_reload_retrace_identity", "integrity", reload_retrace_difference == 0.0, reload_retrace_difference, "exact checkpoint reload")
    gate("restart_hidden_state_identity", "integrity", restart["hidden_sequence_max_abs_difference"] == 0.0, restart["hidden_sequence_max_abs_difference"], "day-195 hidden restart exact")
    gate("restart_output_identity", "integrity", restart["timestep_max_abs_difference"] == 0.0 and restart["retrace_max_abs_difference"] == 0.0, f"dt={restart['timestep_max_abs_difference']}, retrace={restart['retrace_max_abs_difference']}", "restart outputs exact")
    gate("v15e3_upstream_pass", "integrity", e3_summary.get("status") == "PASS", e3_summary.get("status"), "15E-3 approved recurrent grid state")
    gate("v15c3_upstream_pass", "integrity", int(c3_summary.get("validation_passed", c3_summary.get("mandatory_gates_passed", 24))) == int(c3_summary.get("validation_total", c3_summary.get("mandatory_gates_total", 24))), c3_summary.get("status", "PASS"), "15C-3 corrected path/cache baseline")

    gate("validation_timestep_beats_persistence", "deployment", metrics["validation_screened_timestep_rmse_days"] < metrics["validation_persistence_timestep_rmse_days"], f"{metrics['validation_screened_timestep_rmse_days']:.6g} < {metrics['validation_persistence_timestep_rmse_days']:.6g}", "screened GRU validation RMSE below persistence")
    gate("test_timestep_beats_persistence", "deployment", metrics["test_screened_timestep_rmse_days"] < metrics["test_persistence_timestep_rmse_days"], f"{metrics['test_screened_timestep_rmse_days']:.6g} < {metrics['test_persistence_timestep_rmse_days']:.6g}", "screened GRU test RMSE below persistence")
    gate("test_timestep_mae_below_0p15_days", "deployment", metrics["test_screened_timestep_mae_days"] < 0.15, metrics["test_screened_timestep_mae_days"], "<0.15 day test MAE")
    gate("test_timestep_rmse_reduction_above_25pct", "deployment", metrics["test_timestep_rmse_reduction_fraction"] > 0.25, metrics["test_timestep_rmse_reduction_fraction"], ">25% versus persistence")
    gate("timestep_screen_exercises_learned", "deployment", metrics["timestep_selected_steps"] > 0, metrics["timestep_selected_steps"], ">0 selected proposals")
    gate("timestep_screen_exercises_fallback", "deployment", metrics["timestep_fallback_steps"] > 0, metrics["timestep_fallback_steps"], ">0 confidence fallbacks")
    gate("test_retrace_fraction_rmse_below_0p08", "deployment", metrics["test_retrace_fraction_rmse"] < 0.08, metrics["test_retrace_fraction_rmse"], "<0.08 held-out fraction RMSE")
    gate("zero_unsafe_cache_only_decisions", "deployment", metrics["unsafe_cache_only_decisions"] == 0, metrics["unsafe_cache_only_decisions"], "zero false reuse/high-retrace misses")
    gate("full_family_retraces_avoided", "deployment", metrics["full_family_retraces_avoided"] >= 5, metrics["full_family_retraces_avoided"], ">=5 cache-only snapshot updates")
    late_high = retrace_audit[(retrace_audit["split"] == "test") & retrace_audit["high_retrace_event"]]
    gate("late_ood_high_retrace_fallback", "deployment", bool(late_high["full_family_retrace"].all()), int(late_high["full_family_retrace"].sum()), "all held-out high-retrace events use full retrace")

    gate("raw_timestep_head_beats_persistence_test", "diagnostic", metrics["test_raw_timestep_rmse_days"] < metrics["test_persistence_timestep_rmse_days"], f"{metrics['test_raw_timestep_rmse_days']:.6g}", "raw learned signal is informative")
    gate("retrace_screen_exercises_full_family", "diagnostic", metrics["full_family_retraces_selected"] > 0, metrics["full_family_retraces_selected"], ">0 full-family decisions")
    gate("retrace_screen_exercises_cache_only", "diagnostic", metrics["full_family_retraces_avoided"] > 0, metrics["full_family_retraces_avoided"], ">0 cache-only decisions")
    gate("retrace_ood_fallback_exercised", "diagnostic", metrics["retrace_ood_fallbacks"] > 0, metrics["retrace_ood_fallbacks"], ">0 OOD full-retrace fallbacks")

    validation = pd.DataFrame(gates)
    validation.to_csv(out_dir / "PAD_Stream_V15F0_Validation_Matrix.csv", index=False)
    integrity = validation[validation["group"] == "integrity"]
    deployment = validation[validation["group"] == "deployment"]
    diagnostic = validation[validation["group"] == "diagnostic"]
    status = "PASS" if bool(integrity["passed"].all() and deployment["passed"].all()) else (
        "AUDIT_COMPLETE_DEPLOYMENT_NOT_APPROVED"
        if bool(integrity["passed"].all()) else "AUDIT_FAILED"
    )

    summary = {
        "version": VERSION,
        "status": status,
        "description": "Global GRU state with screened adaptive-timestep and streamline-retrace proposals",
        "integrity_gates_passed": int(integrity["passed"].sum()),
        "integrity_gates_total": int(len(integrity)),
        "deployment_gates_passed": int(deployment["passed"].sum()),
        "deployment_gates_total": int(len(deployment)),
        "diagnostic_gates_passed": int(diagnostic["passed"].sum()),
        "diagnostic_gates_total": int(len(diagnostic)),
        "deployment_approved": bool(deployment["passed"].all()),
        "model": model_config | {"trainable_parameters": metrics["trainable_parameters"]},
        "calibration": checkpoint["calibration"],
        "metrics": metrics,
        "rollout_contract": "accepted-step diagnostics -> GRU state -> timestep/retrace proposal -> uncertainty screen -> classical timestep controller and exact path-cache/Pollock authority",
        "handoff": {
            "next_milestone": "15F-1",
            "next_scope": "breakthrough and well-control recurrent memory",
            "preserved_15e3_diagnostics": ["producer gas cut", "breakthrough timing"],
        },
        "limitations": [
            "The single controlled 365-day trajectory is a prototype-scale recurrent dataset; field-scale diversity is deferred.",
            "The learned timestep is a proposal only; the classical adaptive acceptance/retry controller remains mandatory.",
            "The learned retrace output schedules cache-only versus full-family work; exact per-path cache and Pollock correction remain mandatory.",
            "Breakthrough and well-control memory are excluded and deferred to Version 15F-1.",
            "Explicit nonlinear-difficulty memory is deferred to Version 15F-2.",
        ],
        "source_hashes": {name: info["sha256"] for name, info in dependency_manifest["sources"].items()},
    }
    (out_dir / "PAD_Stream_V15F0_Summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    create_plots(
        out_dir,
        dense_audit,
        timestep_metrics,
        retrace_audit,
        retrace_targets,
        prediction["retrace_fractions"],
        prediction["hidden_sequence"],
        validation,
        calibration,
    )
    write_inference_source(out_dir)
    shutil.copy2(Path(__file__), out_dir / Path(__file__).name)
    write_readme(out_dir, summary)
    write_verifier(out_dir)
    write_checksums(out_dir)

    zip_path = out_dir.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", out_dir.parent, out_dir.name)
    return summary


def default_paths(root: Path) -> Dict[str, Path]:
    c3_root = root / "deps/c3/PAD_Stream_V15C3_Sequential_Path_Deployment_Package/PAD_Stream_V15C3_Sequential_Learned_Path_Deployment"
    b3_results = root / "deps/c3/PAD_Stream_V15C3_Sequential_Path_Deployment_Package/PAD_Stream_V15B3R_Sequential_Predict_Screen_Correct_Package/results"
    e3_root = root / "PAD_Stream_V15E3_Sequential_Conservative_Graph_Mapback_Deployment"
    return {
        "dense_audit": b3_results / "PAD_Stream_V15B3R_Sequential_Audit.csv",
        "path_cache_audit": c3_root / "PAD_Stream_V15C3_Path_Cache_Audit.csv",
        "state_dir": c3_root / "sequential_states",
        "c3_summary": c3_root / "PAD_Stream_V15C3_Summary.json",
        "e3_snapshot_audit": e3_root / "PAD_Stream_V15E3_Sequential_Snapshot_Audit.csv",
        "e3_summary": e3_root / "PAD_Stream_V15E3_Summary.json",
        "e3_package_zip": root / "PAD_Stream_V15E3_Sequential_Conservative_Graph_Mapback_Deployment.zip",
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent / "pad_stream_v15e3"
    defaults = default_paths(root)
    parser = argparse.ArgumentParser()
    parser.add_argument("--dense-audit", type=Path, default=defaults["dense_audit"])
    parser.add_argument("--path-cache-audit", type=Path, default=defaults["path_cache_audit"])
    parser.add_argument("--state-dir", type=Path, default=defaults["state_dir"])
    parser.add_argument("--c3-summary", type=Path, default=defaults["c3_summary"])
    parser.add_argument("--e3-snapshot-audit", type=Path, default=defaults["e3_snapshot_audit"])
    parser.add_argument("--e3-summary", type=Path, default=defaults["e3_summary"])
    parser.add_argument("--e3-package-zip", type=Path, default=defaults["e3_package_zip"])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "PAD_Stream_V15F0_Global_Recurrent_Timestep_Retrace_State",
    )
    args = parser.parse_args()
    for path in [
        args.dense_audit, args.path_cache_audit, args.c3_summary,
        args.e3_snapshot_audit, args.e3_summary, args.e3_package_zip,
    ]:
        if not Path(path).exists():
            raise FileNotFoundError(path)
    summary = build(args)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
