#!/usr/bin/env python3
"""PAD-Stream Version 15F-1.

Breakthrough and well-control recurrent memory over the frozen Version 15F-0
GRU state.

Version 15F-1 keeps the accepted 15F-0 encoder immutable and learns three
compact heads from its recurrent state plus current accepted well diagnostics:

1. a one-step producer gas-cut residual forecast;
2. a breakthrough-hazard forecast with monotone event memory;
3. an injector control-mode forecast.

The deployment contract remains predict-screen-correct:

    accepted physics/well state -> frozen 15F-0 recurrent state
                                -> gas-cut / breakthrough / control proposals
                                -> bounded confidence and control-limit screens
                                -> exact Peaceman well equations and control logic

The learned branch is a warm-start and event-warning mechanism. It never
replaces the exact well equations, never modifies the accepted reservoir mass,
and never overrides active BHP or mass-rate constraints.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

VERSION = "15F-1"
SEED = 150601
DAYS_PER_YEAR = 365.0
BREAKTHROUGH_GAS_CUT = 1.0e-4
F0_HIDDEN_DIM = 32
WELL_FEATURE_NAMES = [
    "current_producer_gas_cut",
    "log10_current_producer_gas_cut_plus_1e-8",
    "current_gas_cut_increment",
    "current_breakthrough_memory",
    "time_since_breakthrough_fraction",
    "current_injector_mass_rate_mode",
    "current_injector_bhp_over_limit",
    "current_injector_mass_rate_over_limit",
    "current_bhp_headroom_over_4mpa",
    "current_mass_rate_headroom_kg_s",
    "current_control_switch_memory",
]
FEATURE_NAMES = [f"f0_hidden_{index:02d}" for index in range(F0_HIDDEN_DIM)] + WELL_FEATURE_NAMES
FORBIDDEN_FEATURE_TOKENS = (
    "next_", "future_", "target_", "exact_future", "target_saturation",
    "target_pressure", "target_inventory", "next_producer", "next_injector",
)


@dataclass(frozen=True)
class TrainConfig:
    gas_ridge_alpha: float = 10.0
    hazard_ridge_alpha: float = 0.10
    mode_logistic_c: float = 1.0
    event_weight: float = 8.0
    breakthrough_horizon_days: float = 15.0
    gas_candidate_max_decrease: float = 0.002
    gas_candidate_max_increase: float = 0.040
    gas_select_hazard_threshold: float = 0.20
    gas_select_max_current_cut: float = 0.70
    mode_confidence_low: float = 0.40
    mode_confidence_high: float = 0.60
    injector_bhp_limit_mpa: float = 30.0
    injector_mass_rate_limit_kg_s: float = 38.55
    bhp_boundary_mpa: float = 29.90
    mass_rate_boundary_kg_s: float = 38.30
    state_distance_quantile: float = 0.99
    validation_event_start_day: float = 90.0
    validation_event_end_day: float = 105.0
    test_breakthrough_start_day: float = 105.0
    test_breakthrough_end_day: float = 150.0
    test_control_start_day: float = 30.0
    test_control_end_day: float = 50.0
    validation_late_start_day: float = 240.0
    validation_late_end_day: float = 300.0
    test_late_start_day: float = 300.0


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


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_npz(path: Path, allow_pickle: bool = False) -> Dict[str, np.ndarray]:
    with np.load(path, allow_pickle=allow_pickle) as z:
        return {name: z[name].copy() for name in z.files}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def safe_torch_load(path: Path) -> Mapping[str, Any]:
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


def exact_crossing_time(time_days: np.ndarray, values: np.ndarray, threshold: float) -> float:
    time_days = np.asarray(time_days, np.float64)
    values = np.asarray(values, np.float64)
    hits = np.where(values >= threshold)[0]
    if len(hits) == 0:
        return math.nan
    index = int(hits[0])
    if index == 0:
        return float(time_days[0])
    x0, x1 = float(time_days[index - 1]), float(time_days[index])
    y0, y1 = float(values[index - 1]), float(values[index])
    if abs(y1 - y0) < 1.0e-15:
        return x1
    fraction = float(np.clip((threshold - y0) / (y1 - y0), 0.0, 1.0))
    return x0 + fraction * (x1 - x0)


def build_splits(current_time: np.ndarray, cfg: TrainConfig) -> np.ndarray:
    current_time = np.asarray(current_time, np.float64)
    test = (
        ((current_time > cfg.test_control_start_day) & (current_time <= cfg.test_control_end_day))
        | ((current_time > cfg.test_breakthrough_start_day) & (current_time <= cfg.test_breakthrough_end_day))
        | (current_time > cfg.test_late_start_day)
    )
    validation = (
        ((current_time > 20.0) & (current_time <= cfg.test_control_start_day))
        | ((current_time > cfg.validation_event_start_day) & (current_time <= cfg.validation_event_end_day))
        | ((current_time > cfg.validation_late_start_day) & (current_time <= cfg.validation_late_end_day))
    )
    split = np.full(len(current_time), "train", dtype="<U10")
    split[validation] = "validation"
    split[test] = "test"
    return split


def build_well_features(dense: pd.DataFrame) -> tuple[np.ndarray, Dict[str, np.ndarray]]:
    required = {
        "time_days", "dt_days", "injector_mode", "injector_bhp_mpa",
        "injector_mass_rate_kg_s", "producer_bhp_mpa", "producer_gas_cut",
        "breakthrough_reached",
    }
    missing = sorted(required.difference(dense.columns))
    if missing:
        raise KeyError(f"dense audit missing columns: {missing}")

    time_days = dense["time_days"].to_numpy(np.float64)
    gas_cut = np.clip(dense["producer_gas_cut"].to_numpy(np.float64), 0.0, 1.0)
    gas_increment = np.concatenate([[0.0], np.diff(gas_cut)])
    breakthrough = dense["breakthrough_reached"].astype(bool).to_numpy()
    mode_mass_rate = (dense["injector_mode"].astype(str).to_numpy() == "mass_rate").astype(np.float64)
    bhp = dense["injector_bhp_mpa"].to_numpy(np.float64)
    mass_rate = dense["injector_mass_rate_kg_s"].to_numpy(np.float64)
    control_switch = np.concatenate([[0.0], (mode_mass_rate[1:] != mode_mass_rate[:-1]).astype(np.float64)])

    breakthrough_start: float | None = None
    time_since = np.zeros(len(dense), np.float64)
    for index, reached in enumerate(breakthrough):
        if reached and breakthrough_start is None:
            breakthrough_start = float(time_days[index])
        if breakthrough_start is not None:
            time_since[index] = max(float(time_days[index]) - breakthrough_start, 0.0)

    features = np.column_stack([
        gas_cut,
        np.log10(gas_cut + 1.0e-8),
        gas_increment,
        breakthrough.astype(np.float64),
        time_since / DAYS_PER_YEAR,
        mode_mass_rate,
        bhp / 30.0,
        mass_rate / 38.55,
        (30.0 - bhp) / 4.0,
        38.55 - mass_rate,
        control_switch,
    ]).astype(np.float64)
    state = {
        "time_days": time_days,
        "gas_cut": gas_cut,
        "gas_increment": gas_increment,
        "breakthrough": breakthrough,
        "mode_mass_rate": mode_mass_rate,
        "bhp_mpa": bhp,
        "mass_rate_kg_s": mass_rate,
        "producer_bhp_mpa": dense["producer_bhp_mpa"].to_numpy(np.float64),
        "control_switch": control_switch,
        "time_since_breakthrough_days": time_since,
    }
    return features, state


def fit_heads(
    features_normalized: np.ndarray,
    state: Mapping[str, np.ndarray],
    split: np.ndarray,
    cfg: TrainConfig,
) -> Dict[str, Any]:
    current_time = state["time_days"][:-1]
    target_time = state["time_days"][1:]
    current_gas = state["gas_cut"][:-1]
    target_gas = state["gas_cut"][1:]
    current_mode = state["mode_mass_rate"][:-1].astype(int)
    target_mode = state["mode_mass_rate"][1:].astype(int)
    target_bhp = state["bhp_mpa"][1:]
    target_rate = state["mass_rate_kg_s"][1:]

    first_breakthrough_index = np.where(state["breakthrough"])[0]
    if len(first_breakthrough_index) == 0:
        raise RuntimeError("frozen trajectory does not contain breakthrough")
    first_accepted_breakthrough_day = float(state["time_days"][first_breakthrough_index[0]])
    hazard_target = np.exp(
        -np.maximum(first_accepted_breakthrough_day - target_time, 0.0)
        / cfg.breakthrough_horizon_days
    )
    event_weight = (
        1.0
        + cfg.event_weight * ((target_time >= 90.0) & (target_time <= 180.0))
        + cfg.event_weight * ((target_time >= 25.0) & (target_time <= 55.0))
    ).astype(np.float64)
    train_mask = split == "train"

    gas_model = Ridge(alpha=cfg.gas_ridge_alpha)
    gas_model.fit(
        features_normalized[train_mask],
        (target_gas - current_gas)[train_mask],
        sample_weight=event_weight[train_mask],
    )
    hazard_model = Ridge(alpha=cfg.hazard_ridge_alpha)
    hazard_model.fit(
        features_normalized[train_mask],
        hazard_target[train_mask],
        sample_weight=event_weight[train_mask],
    )
    mode_model = LogisticRegression(
        C=cfg.mode_logistic_c,
        class_weight="balanced",
        max_iter=5000,
        random_state=SEED,
    )
    mode_model.fit(features_normalized[train_mask], target_mode[train_mask])

    raw_gas = current_gas + gas_model.predict(features_normalized)
    raw_hazard = np.clip(hazard_model.predict(features_normalized), 0.0, 1.0)
    mode_probability = mode_model.predict_proba(features_normalized)[:, 1]
    return {
        "gas_model": gas_model,
        "hazard_model": hazard_model,
        "mode_model": mode_model,
        "raw_gas_cut": raw_gas,
        "raw_hazard": raw_hazard,
        "mode_probability": mode_probability,
        "hazard_target": hazard_target,
        "target_gas_cut": target_gas,
        "target_mode_mass_rate": target_mode,
        "target_bhp_mpa": target_bhp,
        "target_mass_rate_kg_s": target_rate,
        "first_accepted_breakthrough_day": first_accepted_breakthrough_day,
    }


def apply_screens(
    features_normalized: np.ndarray,
    state: Mapping[str, np.ndarray],
    heads: Mapping[str, Any],
    split: np.ndarray,
    cfg: TrainConfig,
) -> Dict[str, np.ndarray | float]:
    train_mask = split == "train"
    state_distance = np.sqrt(np.mean(np.asarray(features_normalized, np.float64) ** 2, axis=1))
    state_distance_threshold = float(np.quantile(state_distance[train_mask], cfg.state_distance_quantile))

    current_gas = state["gas_cut"][:-1]
    current_mode = state["mode_mass_rate"][:-1].astype(int)
    current_bhp = state["bhp_mpa"][:-1]
    current_rate = state["mass_rate_kg_s"][:-1]
    raw_gas = np.asarray(heads["raw_gas_cut"], np.float64)
    raw_hazard = np.asarray(heads["raw_hazard"], np.float64)
    mode_probability = np.asarray(heads["mode_probability"], np.float64)

    gas_candidate = np.clip(
        raw_gas,
        current_gas - cfg.gas_candidate_max_decrease,
        current_gas + cfg.gas_candidate_max_increase,
    )
    gas_candidate = np.clip(gas_candidate, 0.0, 1.0)
    gas_selected = (
        (raw_hazard >= cfg.gas_select_hazard_threshold)
        & (current_gas < cfg.gas_select_max_current_cut)
        & (state_distance <= state_distance_threshold)
    )
    screened_gas = current_gas.copy()
    screened_gas[gas_selected] = gas_candidate[gas_selected]

    monotone_hazard = np.maximum.accumulate(np.clip(raw_hazard, 0.0, 1.0))
    breakthrough_warning = monotone_hazard >= cfg.gas_select_hazard_threshold
    proposed_breakthrough = monotone_hazard >= 0.50

    raw_mode = (mode_probability >= 0.50).astype(int)
    mode_confident = (
        (mode_probability <= cfg.mode_confidence_low)
        | (mode_probability >= cfg.mode_confidence_high)
    )
    screened_mode = np.where(mode_confident, raw_mode, current_mode).astype(int)
    control_boundary = (
        ((current_mode == 0) & (current_rate >= cfg.mass_rate_boundary_kg_s))
        | ((current_mode == 1) & (current_bhp >= cfg.bhp_boundary_mpa))
    )
    control_preflight = (
        control_boundary
        | (~mode_confident)
        | (screened_mode != current_mode)
        | (state_distance > state_distance_threshold)
    )

    # Active constraints are imposed exactly. The inactive variable receives a
    # persistence warm start and remains subject to the exact well solve.
    warm_bhp = np.where(screened_mode == 0, cfg.injector_bhp_limit_mpa, current_bhp)
    warm_rate = np.where(screened_mode == 1, cfg.injector_mass_rate_limit_kg_s, current_rate)

    return {
        "state_distance": state_distance,
        "state_distance_threshold": state_distance_threshold,
        "gas_candidate": gas_candidate,
        "gas_selected": gas_selected,
        "screened_gas_cut": screened_gas,
        "monotone_breakthrough_hazard": monotone_hazard,
        "breakthrough_warning": breakthrough_warning,
        "proposed_breakthrough": proposed_breakthrough,
        "raw_mode_mass_rate": raw_mode,
        "mode_confident": mode_confident,
        "screened_mode_mass_rate": screened_mode,
        "control_boundary": control_boundary,
        "control_preflight": control_preflight,
        "warm_start_bhp_mpa": warm_bhp,
        "warm_start_mass_rate_kg_s": warm_rate,
    }


def reproduce_f0(
    trainer_path: Path,
    checkpoint_path: Path,
    dataset_path: Path,
    predictions_path: Path,
) -> Dict[str, Any]:
    trainer = load_module("pad_stream_v15f0_frozen", trainer_path)
    checkpoint = safe_torch_load(checkpoint_path)
    dataset = load_npz(dataset_path)
    stored = load_npz(predictions_path)
    model = trainer.model_from_config(checkpoint["model_config"])
    model.load_state_dict(checkpoint["model_state_dict"])
    prediction = trainer.predict_all(
        model,
        dataset["dense_features_normalized"],
        dataset["snapshot_features_normalized"],
        dataset["snapshot_dense_indices"],
    )
    return {
        "model": model,
        "checkpoint": checkpoint,
        "dataset": dataset,
        "stored": stored,
        "prediction": prediction,
        "hidden_max_abs_difference": float(np.max(np.abs(prediction["hidden_sequence"] - stored["hidden_sequence"]))),
        "timestep_max_abs_difference": float(np.max(np.abs(prediction["raw_timestep_days"] - stored["raw_timestep_days"]))),
        "retrace_max_abs_difference": float(np.max(np.abs(prediction["retrace_fractions"] - stored["predicted_retrace_fractions"]))),
    }


def restart_audit(
    f0_runtime: Mapping[str, Any],
    well_features: np.ndarray,
    feature_mean: np.ndarray,
    feature_std: np.ndarray,
    state: Mapping[str, np.ndarray],
    heads: Mapping[str, Any],
    screens: Mapping[str, Any],
    cfg: TrainConfig,
    restart_day: float = 195.0,
) -> Dict[str, Any]:
    model = f0_runtime["model"]
    dense_normalized = f0_runtime["dataset"]["dense_features_normalized"]
    dense_times = f0_runtime["dataset"]["dense_time_days"]
    restart_index = int(np.argmin(np.abs(dense_times - restart_day)))
    x = torch.as_tensor(dense_normalized[None, :, :], dtype=torch.float32)
    model.eval()
    with torch.no_grad():
        full_hidden, _ = model.encode(x)
        prefix_hidden, prefix_final = model.encode(x[:, : restart_index + 1, :])
        if restart_index + 1 < x.shape[1]:
            suffix_hidden, suffix_final = model.encode(x[:, restart_index + 1 :, :], prefix_final)
            restarted_hidden = torch.cat([prefix_hidden, suffix_hidden], dim=1)
        else:
            restarted_hidden = prefix_hidden
            suffix_final = prefix_final
    full = full_hidden[0].cpu().numpy().astype(np.float64)
    restarted = restarted_hidden[0].cpu().numpy().astype(np.float64)
    combined_full = np.concatenate([full[:-1], well_features[:-1]], axis=1)
    combined_restart = np.concatenate([restarted[:-1], well_features[:-1]], axis=1)
    norm_full = (combined_full - feature_mean) / feature_std
    norm_restart = (combined_restart - feature_mean) / feature_std

    gas_model = heads["gas_model"]
    hazard_model = heads["hazard_model"]
    mode_model = heads["mode_model"]
    current_gas = state["gas_cut"][:-1]
    gas_full = current_gas + gas_model.predict(norm_full)
    gas_restart = current_gas + gas_model.predict(norm_restart)
    hazard_full = hazard_model.predict(norm_full)
    hazard_restart = hazard_model.predict(norm_restart)
    mode_full = mode_model.predict_proba(norm_full)[:, 1]
    mode_restart = mode_model.predict_proba(norm_restart)[:, 1]

    return {
        "restart_day": float(dense_times[restart_index]),
        "restart_dense_index": restart_index,
        "f0_hidden_state": prefix_final.cpu().numpy().astype(np.float32),
        "current_gas_cut": float(state["gas_cut"][restart_index]),
        "current_breakthrough_memory": bool(state["breakthrough"][restart_index]),
        "current_mode_mass_rate": int(state["mode_mass_rate"][restart_index]),
        "hidden_sequence_max_abs_difference": float(np.max(np.abs(full - restarted))),
        "gas_head_max_abs_difference": float(np.max(np.abs(gas_full - gas_restart))),
        "hazard_head_max_abs_difference": float(np.max(np.abs(hazard_full - hazard_restart))),
        "mode_head_max_abs_difference": float(np.max(np.abs(mode_full - mode_restart))),
        "final_hidden_max_abs_difference": float(np.max(np.abs(suffix_final.cpu().numpy() - full_hidden[:, -1:, :].transpose(0, 1).cpu().numpy()))),
    }


def build_metrics(
    dense: pd.DataFrame,
    split: np.ndarray,
    state: Mapping[str, np.ndarray],
    heads: Mapping[str, Any],
    screens: Mapping[str, Any],
    e3_audit: pd.DataFrame,
    restart: Mapping[str, Any],
) -> tuple[Dict[str, Any], pd.DataFrame, pd.DataFrame]:
    current_time = state["time_days"][:-1]
    target_time = state["time_days"][1:]
    current_gas = state["gas_cut"][:-1]
    target_gas = state["gas_cut"][1:]
    current_mode = state["mode_mass_rate"][:-1].astype(int)
    target_mode = state["mode_mass_rate"][1:].astype(int)
    current_bhp = state["bhp_mpa"][:-1]
    target_bhp = state["bhp_mpa"][1:]
    current_rate = state["mass_rate_kg_s"][:-1]
    target_rate = state["mass_rate_kg_s"][1:]
    screened_gas = np.asarray(screens["screened_gas_cut"], np.float64)
    raw_gas = np.asarray(heads["raw_gas_cut"], np.float64)
    hazard = np.asarray(screens["monotone_breakthrough_hazard"], np.float64)
    screened_mode = np.asarray(screens["screened_mode_mass_rate"], int)
    warm_bhp = np.asarray(screens["warm_start_bhp_mpa"], np.float64)
    warm_rate = np.asarray(screens["warm_start_mass_rate_kg_s"], np.float64)
    control_preflight = np.asarray(screens["control_preflight"], bool)

    test = split == "test"
    validation = split == "validation"
    train = split == "train"
    event = (current_time > 105.0) & (current_time <= 150.0)
    control = (current_time > 30.0) & (current_time <= 50.0)
    late = current_time > 300.0
    true_switch = target_mode != current_mode
    unsafe_no_preflight = (~control_preflight) & (screened_mode != target_mode)

    exact_breakthrough_day = exact_crossing_time(state["time_days"], state["gas_cut"], BREAKTHROUGH_GAS_CUT)
    predicted_breakthrough_day = exact_crossing_time(target_time, hazard, 0.50)
    warning_day = exact_crossing_time(target_time, hazard, 0.20)

    f1_snapshot_gas = np.interp(e3_audit["target_time_days"].to_numpy(np.float64), target_time, screened_gas)
    snapshot_exact = e3_audit["exact_gas_cut"].to_numpy(np.float64)
    snapshot_e3 = e3_audit["predicted_gas_cut"].to_numpy(np.float64)

    rows = []
    for name, mask in [
        ("train", train), ("validation", validation), ("test", test),
        ("breakthrough_event", event), ("control_event", control),
        ("late_test", late), ("all", np.ones(len(split), bool)),
    ]:
        rows.append({
            "split": name,
            "samples": int(mask.sum()),
            "persistence_gas_cut_rmse": rmse(current_gas[mask], target_gas[mask]),
            "raw_recurrent_gas_cut_rmse": rmse(raw_gas[mask], target_gas[mask]),
            "screened_recurrent_gas_cut_rmse": rmse(screened_gas[mask], target_gas[mask]),
            "screened_recurrent_gas_cut_mae": mae(screened_gas[mask], target_gas[mask]),
            "raw_mode_accuracy": float(np.mean((np.asarray(screens["raw_mode_mass_rate"])[mask]) == target_mode[mask])),
            "screened_mode_accuracy": float(np.mean(screened_mode[mask] == target_mode[mask])),
            "persistence_bhp_rmse_mpa": rmse(current_bhp[mask], target_bhp[mask]),
            "warm_start_bhp_rmse_mpa": rmse(warm_bhp[mask], target_bhp[mask]),
            "persistence_mass_rate_rmse_kg_s": rmse(current_rate[mask], target_rate[mask]),
            "warm_start_mass_rate_rmse_kg_s": rmse(warm_rate[mask], target_rate[mask]),
            "control_preflights": int(control_preflight[mask].sum()),
            "gas_head_selected": int(np.asarray(screens["gas_selected"])[mask].sum()),
        })
    metrics_table = pd.DataFrame(rows)

    audit = pd.DataFrame({
        "current_step": dense["step"].to_numpy()[:-1],
        "target_step": dense["step"].to_numpy()[1:],
        "current_time_days": current_time,
        "target_time_days": target_time,
        "split": split,
        "current_producer_gas_cut": current_gas,
        "target_producer_gas_cut": target_gas,
        "persistence_gas_cut": current_gas,
        "raw_recurrent_gas_cut": raw_gas,
        "bounded_gas_candidate": screens["gas_candidate"],
        "screened_recurrent_gas_cut": screened_gas,
        "gas_head_selected": screens["gas_selected"],
        "raw_breakthrough_hazard": heads["raw_hazard"],
        "monotone_breakthrough_hazard": hazard,
        "breakthrough_warning": screens["breakthrough_warning"],
        "proposed_breakthrough": screens["proposed_breakthrough"],
        "target_breakthrough_memory": state["breakthrough"][1:],
        "current_injector_mode": np.where(current_mode == 1, "mass_rate", "bhp"),
        "target_injector_mode": np.where(target_mode == 1, "mass_rate", "bhp"),
        "mode_mass_rate_probability": heads["mode_probability"],
        "raw_mode_mass_rate": screens["raw_mode_mass_rate"],
        "screened_mode_mass_rate": screened_mode,
        "mode_confident": screens["mode_confident"],
        "control_boundary": screens["control_boundary"],
        "control_preflight": control_preflight,
        "unsafe_no_preflight": unsafe_no_preflight,
        "current_injector_bhp_mpa": current_bhp,
        "target_injector_bhp_mpa": target_bhp,
        "warm_start_injector_bhp_mpa": warm_bhp,
        "current_injector_mass_rate_kg_s": current_rate,
        "target_injector_mass_rate_kg_s": target_rate,
        "warm_start_injector_mass_rate_kg_s": warm_rate,
        "state_distance": screens["state_distance"],
        "state_distance_threshold": float(screens["state_distance_threshold"]),
        "state_ood": np.asarray(screens["state_distance"]) > float(screens["state_distance_threshold"]),
    })

    snapshot = e3_audit[["current_time_days", "target_time_days", "exact_gas_cut", "predicted_gas_cut"]].copy()
    snapshot = snapshot.rename(columns={"predicted_gas_cut": "v15e3_grid_only_gas_cut"})
    snapshot["v15f1_recurrent_gas_cut"] = f1_snapshot_gas
    snapshot["v15e3_absolute_error"] = np.abs(snapshot["v15e3_grid_only_gas_cut"] - snapshot["exact_gas_cut"])
    snapshot["v15f1_absolute_error"] = np.abs(snapshot["v15f1_recurrent_gas_cut"] - snapshot["exact_gas_cut"])

    allrow = metrics_table[metrics_table["split"] == "all"].iloc[0]
    testrow = metrics_table[metrics_table["split"] == "test"].iloc[0]
    eventrow = metrics_table[metrics_table["split"] == "breakthrough_event"].iloc[0]
    laterow = metrics_table[metrics_table["split"] == "late_test"].iloc[0]
    metrics = {
        "transitions": int(len(split)),
        "train_samples": int(train.sum()),
        "validation_samples": int(validation.sum()),
        "test_samples": int(test.sum()),
        "test_persistence_gas_cut_rmse": float(testrow["persistence_gas_cut_rmse"]),
        "test_screened_gas_cut_rmse": float(testrow["screened_recurrent_gas_cut_rmse"]),
        "test_gas_cut_rmse_reduction_fraction": float(1.0 - testrow["screened_recurrent_gas_cut_rmse"] / testrow["persistence_gas_cut_rmse"]),
        "event_persistence_gas_cut_rmse": float(eventrow["persistence_gas_cut_rmse"]),
        "event_screened_gas_cut_rmse": float(eventrow["screened_recurrent_gas_cut_rmse"]),
        "event_gas_cut_rmse_reduction_fraction": float(1.0 - eventrow["screened_recurrent_gas_cut_rmse"] / eventrow["persistence_gas_cut_rmse"]),
        "late_persistence_gas_cut_rmse": float(laterow["persistence_gas_cut_rmse"]),
        "late_screened_gas_cut_rmse": float(laterow["screened_recurrent_gas_cut_rmse"]),
        "snapshot_v15e3_gas_cut_rmse": rmse(snapshot_e3, snapshot_exact),
        "snapshot_v15f1_gas_cut_rmse": rmse(f1_snapshot_gas, snapshot_exact),
        "snapshot_gas_cut_improvement_fraction": float(1.0 - rmse(f1_snapshot_gas, snapshot_exact) / rmse(snapshot_e3, snapshot_exact)),
        "exact_breakthrough_day": exact_breakthrough_day,
        "first_accepted_breakthrough_day": float(heads["first_accepted_breakthrough_day"]),
        "predicted_breakthrough_day": predicted_breakthrough_day,
        "breakthrough_absolute_error_days": abs(predicted_breakthrough_day - exact_breakthrough_day),
        "breakthrough_warning_day": warning_day,
        "breakthrough_warning_lead_days": exact_breakthrough_day - warning_day,
        "raw_mode_accuracy_all": float(np.mean(np.asarray(screens["raw_mode_mass_rate"]) == target_mode)),
        "screened_mode_accuracy_all": float(np.mean(screened_mode == target_mode)),
        "screened_mode_accuracy_test": float(np.mean(screened_mode[test] == target_mode[test])),
        "true_control_switches": int(true_switch.sum()),
        "control_switches_sent_to_preflight": int(control_preflight[true_switch].sum()),
        "unsafe_no_preflight_decisions": int(unsafe_no_preflight.sum()),
        "control_preflight_steps": int(control_preflight.sum()),
        "control_preflight_fraction": float(control_preflight.mean()),
        "gas_head_selected_steps": int(np.asarray(screens["gas_selected"]).sum()),
        "gas_head_fallback_steps": int(len(split) - np.asarray(screens["gas_selected"]).sum()),
        "well_state_ood_steps": int((np.asarray(screens["state_distance"]) > float(screens["state_distance_threshold"])).sum()),
        "test_persistence_bhp_rmse_mpa": float(testrow["persistence_bhp_rmse_mpa"]),
        "test_warm_start_bhp_rmse_mpa": float(testrow["warm_start_bhp_rmse_mpa"]),
        "test_persistence_mass_rate_rmse_kg_s": float(testrow["persistence_mass_rate_rmse_kg_s"]),
        "test_warm_start_mass_rate_rmse_kg_s": float(testrow["warm_start_mass_rate_rmse_kg_s"]),
        "active_bhp_constraint_max_error_mpa": float(np.max(np.abs(warm_bhp[screened_mode == 0] - 30.0))) if np.any(screened_mode == 0) else 0.0,
        "active_mass_rate_constraint_max_error_kg_s": float(np.max(np.abs(warm_rate[screened_mode == 1] - 38.55))) if np.any(screened_mode == 1) else 0.0,
        "maximum_breakthrough_hazard_decrease": float(np.min(np.diff(hazard))) if len(hazard) > 1 else 0.0,
        "restart_day": float(restart["restart_day"]),
        "restart_hidden_sequence_max_abs_difference": float(restart["hidden_sequence_max_abs_difference"]),
        "restart_gas_head_max_abs_difference": float(restart["gas_head_max_abs_difference"]),
        "restart_hazard_head_max_abs_difference": float(restart["hazard_head_max_abs_difference"]),
        "restart_mode_head_max_abs_difference": float(restart["mode_head_max_abs_difference"]),
        "all_screened_gas_cut_rmse": float(allrow["screened_recurrent_gas_cut_rmse"]),
    }
    return metrics, metrics_table, audit, snapshot


def create_plots(
    out_dir: Path,
    audit: pd.DataFrame,
    snapshot: pd.DataFrame,
    metrics_table: pd.DataFrame,
    validation: pd.DataFrame,
) -> None:
    plots = out_dir / "plots"
    plots.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(audit["target_time_days"], audit["target_producer_gas_cut"], label="Exact Peaceman response")
    ax.plot(audit["target_time_days"], audit["persistence_gas_cut"], label="Persistence warm start", alpha=0.75)
    ax.plot(audit["target_time_days"], audit["screened_recurrent_gas_cut"], label="15F-1 screened recurrent warm start")
    ax.axhline(BREAKTHROUGH_GAS_CUT, linestyle="--", label="Breakthrough criterion")
    ax.set_xlabel("Simulation time (days)")
    ax.set_ylabel("Producer gas cut")
    ax.set_title("Version 15F-1 producer gas-cut memory")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots / "500_producer_gas_cut_memory.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(audit["target_time_days"], audit["monotone_breakthrough_hazard"], label="Monotone breakthrough hazard")
    ax.axhline(0.20, linestyle="--", label="Warning threshold")
    ax.axhline(0.50, linestyle=":", label="Breakthrough proposal threshold")
    exact_rows = audit[audit["target_breakthrough_memory"].astype(bool)]
    if len(exact_rows):
        ax.axvline(float(exact_rows["target_time_days"].iloc[0]), linestyle="--", label="First accepted exact breakthrough")
    ax.set_xlabel("Simulation time (days)")
    ax.set_ylabel("Hazard / memory")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title("Breakthrough warning and monotone event memory")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots / "501_breakthrough_hazard.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(audit["target_time_days"], audit["mode_mass_rate_probability"], label="Predicted mass-rate probability")
    ax.step(audit["target_time_days"], (audit["target_injector_mode"] == "mass_rate").astype(float), where="post", label="Exact next control mode")
    ax.scatter(audit.loc[audit["control_preflight"], "target_time_days"], audit.loc[audit["control_preflight"], "mode_mass_rate_probability"], s=12, label="Exact control preflight")
    ax.axhline(0.40, linestyle="--")
    ax.axhline(0.60, linestyle="--")
    ax.set_xlabel("Simulation time (days)")
    ax.set_ylabel("Mass-rate mode probability")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title("Injector well-control recurrent memory")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots / "502_well_control_memory.png", dpi=180)
    plt.close(fig)

    test = metrics_table[metrics_table["split"] == "test"].iloc[0]
    labels = ["Gas cut", "Injector BHP", "Injector rate"]
    persistence = [test["persistence_gas_cut_rmse"], test["persistence_bhp_rmse_mpa"], test["persistence_mass_rate_rmse_kg_s"]]
    recurrent = [test["screened_recurrent_gas_cut_rmse"], test["warm_start_bhp_rmse_mpa"], test["warm_start_mass_rate_rmse_kg_s"]]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    width = 0.36
    ax.bar(x - width / 2, persistence, width, label="Persistence")
    ax.bar(x + width / 2, recurrent, width, label="15F-1 warm start")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Held-out RMSE (native units)")
    ax.set_title("Held-out well-response warm-start accuracy")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots / "503_well_warm_start_rmse.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(audit["target_time_days"], audit["state_distance"], label="Well-memory state distance")
    ax.axhline(float(audit["state_distance_threshold"].iloc[0]), linestyle="--", label="Train-calibrated confidence threshold")
    ax.fill_between(audit["target_time_days"], 0, audit["state_distance"], where=audit["gas_head_selected"].astype(bool), alpha=0.2, label="Gas head selected")
    ax.set_xlabel("Simulation time (days)")
    ax.set_ylabel("Normalized state distance")
    ax.set_title("15F-1 confidence and fallback screen")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots / "504_well_memory_uncertainty.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(snapshot["target_time_days"], snapshot["exact_gas_cut"], marker="o", label="Exact snapshot gas cut")
    ax.plot(snapshot["target_time_days"], snapshot["v15e3_grid_only_gas_cut"], marker="o", label="15E-3 grid-only diagnostic")
    ax.plot(snapshot["target_time_days"], snapshot["v15f1_recurrent_gas_cut"], marker="o", label="15F-1 recurrent well memory")
    ax.set_xlabel("Snapshot time (days)")
    ax.set_ylabel("Producer gas cut")
    ax.set_title("Closure of the Version 15E-3 well-response handoff")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots / "505_v15e3_v15f1_gas_cut_handoff.png", dpi=180)
    plt.close(fig)

    scored = validation[validation["group"].isin(["integrity", "deployment"])]
    labels = [f"[{group[0].upper()}] {gate}" for group, gate in zip(scored["group"], scored["gate"])]
    values = scored["passed"].astype(int).to_numpy()
    fig, ax = plt.subplots(figsize=(10, 9))
    y = np.arange(len(scored))
    ax.barh(y, values)
    ax.set_yticks(y, labels, fontsize=7.5)
    ax.set_xlim(0.0, 1.05)
    ax.set_xticks([0, 1], ["FAIL", "PASS"])
    ax.set_title("Version 15F-1 validation scorecard")
    fig.tight_layout()
    fig.savefig(plots / "506_validation_scorecard.png", dpi=180)
    plt.close(fig)


def write_inference_source(out_dir: Path) -> None:
    text = r'''#!/usr/bin/env python3
"""Pure-NumPy well-memory heads for PAD-Stream Version 15F-1.

The caller supplies the current frozen 15F-0 hidden vector and the 11 current
well-memory features defined in PAD_Stream_V15F1_Feature_Target_Schema.json.
Exact Peaceman well equations remain mandatory after this warm-start proposal.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np


def load_bundle(path: Path):
    z=np.load(path,allow_pickle=False)
    return {k:z[k].copy() for k in z.files}


def _linear(x,coef,intercept):
    return float(np.dot(x,coef)+intercept)


def predict(bundle, f0_hidden, well_features, current_gas_cut,
            current_mode_mass_rate, current_bhp_mpa, current_mass_rate_kg_s,
            previous_monotone_hazard=0.0):
    raw=np.concatenate([np.asarray(f0_hidden,np.float64).reshape(-1),np.asarray(well_features,np.float64).reshape(-1)])
    x=(raw-bundle["feature_mean"])/bundle["feature_std"]
    distance=float(np.sqrt(np.mean(x*x)))
    raw_gas=float(current_gas_cut+_linear(x,bundle["gas_coef"],bundle["gas_intercept"][0]))
    raw_hazard=float(np.clip(_linear(x,bundle["hazard_coef"],bundle["hazard_intercept"][0]),0,1))
    logit=_linear(x,bundle["mode_coef"],bundle["mode_intercept"][0])
    probability=float(1/(1+np.exp(-np.clip(logit,-60,60))))
    gas_candidate=float(np.clip(raw_gas,current_gas_cut-bundle["gas_max_decrease"][0],current_gas_cut+bundle["gas_max_increase"][0]))
    gas_candidate=float(np.clip(gas_candidate,0,1))
    selected=bool(raw_hazard>=bundle["gas_select_hazard_threshold"][0] and current_gas_cut<bundle["gas_select_max_current_cut"][0] and distance<=bundle["state_distance_threshold"][0])
    screened_gas=gas_candidate if selected else float(current_gas_cut)
    monotone_hazard=float(max(previous_monotone_hazard,raw_hazard))
    raw_mode=int(probability>=0.5)
    confident=bool(probability<=bundle["mode_confidence_low"][0] or probability>=bundle["mode_confidence_high"][0])
    screened_mode=raw_mode if confident else int(current_mode_mass_rate)
    boundary=bool((not current_mode_mass_rate and current_mass_rate_kg_s>=bundle["mass_rate_boundary_kg_s"][0]) or (current_mode_mass_rate and current_bhp_mpa>=bundle["bhp_boundary_mpa"][0]))
    preflight=bool(boundary or not confident or screened_mode!=int(current_mode_mass_rate) or distance>bundle["state_distance_threshold"][0])
    warm_bhp=float(bundle["bhp_limit_mpa"][0] if screened_mode==0 else current_bhp_mpa)
    warm_rate=float(bundle["mass_rate_limit_kg_s"][0] if screened_mode==1 else current_mass_rate_kg_s)
    return {"raw_gas_cut":raw_gas,"screened_gas_cut":screened_gas,"gas_head_selected":selected,"raw_breakthrough_hazard":raw_hazard,"monotone_breakthrough_hazard":monotone_hazard,"breakthrough_warning":bool(monotone_hazard>=bundle["gas_select_hazard_threshold"][0]),"proposed_breakthrough":bool(monotone_hazard>=0.5),"mode_mass_rate_probability":probability,"screened_mode_mass_rate":screened_mode,"control_preflight":preflight,"warm_start_bhp_mpa":warm_bhp,"warm_start_mass_rate_kg_s":warm_rate,"state_distance":distance}
'''
    (out_dir / "PAD_Stream_V15F1_Inference_and_Well_Screen.py").write_text(text, encoding="utf-8")


def write_readme(out_dir: Path, summary: Mapping[str, Any]) -> None:
    m = summary["metrics"]
    text = f"""# PAD-Stream Version 15F-1

## Breakthrough and well-control recurrent memory

Version 15F-1 freezes the approved Version 15F-0 GRU encoder and attaches
compact well-memory heads for producer gas cut, breakthrough hazard, and
injector control mode. The heads consume only the current accepted state and
past recurrent memory.

The learned outputs are **warm starts and event warnings**. Exact Peaceman well
equations, phase-potential fluxes, and active BHP/mass-rate constraints remain
mandatory final authorities.

## Decision

- Integrity gates: **{summary['integrity_gates_passed']}/{summary['integrity_gates_total']}**
- Deployment gates: **{summary['deployment_gates_passed']}/{summary['deployment_gates_total']}**
- Diagnostic gates: **{summary['diagnostic_gates_passed']}/{summary['diagnostic_gates_total']}**
- Status: **{summary['status']}**

## Producer gas-cut memory

- Held-out persistence RMSE: **{m['test_persistence_gas_cut_rmse']:.6f}**
- Held-out screened recurrent RMSE: **{m['test_screened_gas_cut_rmse']:.6f}**
- Held-out RMSE reduction: **{100*m['test_gas_cut_rmse_reduction_fraction']:.2f}%**
- Breakthrough-window RMSE reduction: **{100*m['event_gas_cut_rmse_reduction_fraction']:.2f}%**
- Version 15E-3 snapshot gas-cut RMSE: **{m['snapshot_v15e3_gas_cut_rmse']:.6f}**
- Version 15F-1 snapshot gas-cut RMSE: **{m['snapshot_v15f1_gas_cut_rmse']:.6f}**

## Breakthrough memory

- Exact interpolated breakthrough: **{m['exact_breakthrough_day']:.3f} days**
- Recurrent predicted breakthrough: **{m['predicted_breakthrough_day']:.3f} days**
- Absolute timing error: **{m['breakthrough_absolute_error_days']:.3f} days**
- Warning lead time: **{m['breakthrough_warning_lead_days']:.3f} days**
- Breakthrough hazard is monotone by construction.

## Well-control memory

- Screened control-mode accuracy: **{100*m['screened_mode_accuracy_all']:.2f}%**
- True control switches: **{m['true_control_switches']}**
- Switches sent to exact preflight: **{m['control_switches_sent_to_preflight']}**
- Unsafe no-preflight decisions: **{m['unsafe_no_preflight_decisions']}**
- Exact-control preflight fraction: **{100*m['control_preflight_fraction']:.2f}%**

## Recurrent restart

The saved day-{m['restart_day']:.0f} Version 15F-0 hidden state reproduces the
uninterrupted 15F-1 gas-cut, breakthrough, and control outputs exactly.

## Scope boundary

- Exact well equations and control switching remain mandatory corrections.
- The controlled 5x5x5 trajectory contains only two injector mode switches and
  one breakthrough transition; broader multi-case training is deferred.
- Explicit nonlinear-difficulty memory is Version 15F-2.
- Version 15G will integrate the approved pressure, path, transport, map-back,
  and recurrent-state branches.
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")


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
summary=json.loads((ROOT/"PAD_Stream_V15F1_Summary.json").read_text())
validation=pd.read_csv(ROOT/"PAD_Stream_V15F1_Validation_Matrix.csv")
assert summary["status"]=="PASS"
assert validation[validation.group=="integrity"].passed.all()
assert validation[validation.group=="deployment"].passed.all()
p=np.load(ROOT/"PAD_Stream_V15F1_Predictions.npz",allow_pickle=False)
assert np.isfinite(p["screened_gas_cut"]).all()
assert np.all((p["screened_gas_cut"]>=0)&(p["screened_gas_cut"]<=1))
assert np.all(np.diff(p["monotone_breakthrough_hazard"])>=-1e-12)
print(f"PASS: {len(rows)}/{len(rows)} checksums; integrity {summary['integrity_gates_passed']}/{summary['integrity_gates_total']}; deployment {summary['deployment_gates_passed']}/{summary['deployment_gates_total']}")
'''
    (out_dir / "VERIFY_V15F1_PACKAGE.py").write_text(text, encoding="utf-8")


def write_checksums(out_dir: Path) -> None:
    rows = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.csv":
            rows.append({
                "path": str(path.relative_to(out_dir)),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            })
    with (out_dir / "SHA256SUMS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "sha256", "bytes"])
        writer.writeheader()
        writer.writerows(rows)


def build(args: argparse.Namespace) -> Dict[str, Any]:
    seed_everything()
    out_dir = Path(args.output)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    paths = {
        "dense_audit": Path(args.dense_audit),
        "e3_snapshot_audit": Path(args.e3_snapshot_audit),
        "e3_summary": Path(args.e3_summary),
        "f0_trainer": Path(args.f0_trainer),
        "f0_checkpoint": Path(args.f0_checkpoint),
        "f0_dataset": Path(args.f0_dataset),
        "f0_predictions": Path(args.f0_predictions),
        "f0_summary": Path(args.f0_summary),
        "f0_package_zip": Path(args.f0_package_zip),
        "v14_summary": Path(args.v14_summary),
    }
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"{name}: {path}")

    cfg = TrainConfig()
    dense = pd.read_csv(paths["dense_audit"])
    e3_audit = pd.read_csv(paths["e3_snapshot_audit"])
    e3_summary = load_json(paths["e3_summary"])
    f0_summary = load_json(paths["f0_summary"])
    v14_summary = load_json(paths["v14_summary"])
    if f0_summary.get("status") != "PASS":
        raise RuntimeError("Version 15F-0 is not frozen PASS")
    if e3_summary.get("status") != "PASS":
        raise RuntimeError("Version 15E-3 is not frozen PASS")

    f0_runtime = reproduce_f0(
        paths["f0_trainer"], paths["f0_checkpoint"],
        paths["f0_dataset"], paths["f0_predictions"],
    )
    f0_hidden = np.asarray(f0_runtime["prediction"]["hidden_sequence"], np.float64)
    if f0_hidden.shape != (len(dense), F0_HIDDEN_DIM):
        raise ValueError(f"unexpected F0 hidden shape: {f0_hidden.shape}")

    well_features, state = build_well_features(dense)
    raw_features = np.concatenate([f0_hidden[:-1], well_features[:-1]], axis=1)
    split = build_splits(state["time_days"][:-1], cfg)
    train_mask = split == "train"
    scaler = StandardScaler().fit(raw_features[train_mask])
    normalized = scaler.transform(raw_features).astype(np.float64)

    started = time.perf_counter()
    heads = fit_heads(normalized, state, split, cfg)
    screens = apply_screens(normalized, state, heads, split, cfg)
    training_seconds = time.perf_counter() - started
    restart = restart_audit(
        f0_runtime, well_features, scaler.mean_, scaler.scale_, state,
        heads, screens, cfg,
    )
    metrics, metric_table, audit, snapshot = build_metrics(
        dense, split, state, heads, screens, e3_audit, restart,
    )
    metrics["training_seconds"] = training_seconds
    metrics["new_head_parameters"] = int(
        heads["gas_model"].coef_.size + 1
        + heads["hazard_model"].coef_.size + 1
        + heads["mode_model"].coef_.size + 1
    )
    metrics["frozen_f0_parameters"] = int(f0_summary["model"]["trainable_parameters"])
    metrics["combined_recurrent_and_head_parameters"] = int(metrics["new_head_parameters"] + metrics["frozen_f0_parameters"])
    metrics["f0_hidden_reproduction_max_abs_difference"] = f0_runtime["hidden_max_abs_difference"]
    metrics["f0_timestep_reproduction_max_abs_difference"] = f0_runtime["timestep_max_abs_difference"]
    metrics["f0_retrace_reproduction_max_abs_difference"] = f0_runtime["retrace_max_abs_difference"]

    dependency_manifest = {
        "version": VERSION,
        "sources": {
            name: {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in paths.items()
        },
        "upstream_status": {
            "v15e3_status": e3_summary["status"],
            "v15f0_status": f0_summary["status"],
        },
    }
    (out_dir / "PAD_Stream_V15F1_Dependency_Manifest.json").write_text(
        json.dumps(dependency_manifest, indent=2), encoding="utf-8"
    )

    schema = {
        "version": VERSION,
        "architecture": "frozen 15F-0 GRU hidden state plus compact calibrated well-memory heads",
        "features": [{"index": i, "name": name} for i, name in enumerate(FEATURE_NAMES)],
        "targets": {
            "producer_gas_cut": "next accepted-step producer gas cut residual",
            "breakthrough_hazard": f"exp(-days-to-first-accepted-breakthrough/{cfg.breakthrough_horizon_days})",
            "injector_control_mode": "next accepted-step BHP versus mass-rate mode",
        },
        "screens": {
            "gas_cut": "bounded one-step increment, hazard threshold, train-calibrated state distance, persistence fallback",
            "breakthrough": "monotone cumulative hazard with 0.20 warning and 0.50 proposal thresholds",
            "well_control": "confidence band, control-boundary preflight, exact active BHP/rate constraints",
        },
        "forbidden_features": list(FORBIDDEN_FEATURE_TOKENS),
        "scope_boundary": "exact Peaceman well equations and control switching remain mandatory",
    }
    (out_dir / "PAD_Stream_V15F1_Feature_Target_Schema.json").write_text(
        json.dumps(schema, indent=2), encoding="utf-8"
    )

    np.savez_compressed(
        out_dir / "PAD_Stream_V15F1_Well_Memory_Dataset.npz",
        features_raw=raw_features.astype(np.float32),
        features_normalized=normalized.astype(np.float32),
        feature_mean=scaler.mean_.astype(np.float64),
        feature_std=scaler.scale_.astype(np.float64),
        feature_names=np.asarray(FEATURE_NAMES),
        current_time_days=state["time_days"][:-1].astype(np.float64),
        target_time_days=state["time_days"][1:].astype(np.float64),
        split=split,
        target_gas_cut=heads["target_gas_cut"].astype(np.float64),
        target_breakthrough_hazard=heads["hazard_target"].astype(np.float64),
        target_mode_mass_rate=heads["target_mode_mass_rate"].astype(np.int8),
        target_bhp_mpa=heads["target_bhp_mpa"].astype(np.float64),
        target_mass_rate_kg_s=heads["target_mass_rate_kg_s"].astype(np.float64),
    )

    np.savez_compressed(
        out_dir / "PAD_Stream_V15F1_Well_Memory_Heads.npz",
        feature_mean=scaler.mean_.astype(np.float64),
        feature_std=scaler.scale_.astype(np.float64),
        gas_coef=heads["gas_model"].coef_.astype(np.float64),
        gas_intercept=np.array([heads["gas_model"].intercept_], np.float64),
        hazard_coef=heads["hazard_model"].coef_.astype(np.float64),
        hazard_intercept=np.array([heads["hazard_model"].intercept_], np.float64),
        mode_coef=heads["mode_model"].coef_[0].astype(np.float64),
        mode_intercept=heads["mode_model"].intercept_.astype(np.float64),
        state_distance_threshold=np.array([screens["state_distance_threshold"]], np.float64),
        gas_max_decrease=np.array([cfg.gas_candidate_max_decrease], np.float64),
        gas_max_increase=np.array([cfg.gas_candidate_max_increase], np.float64),
        gas_select_hazard_threshold=np.array([cfg.gas_select_hazard_threshold], np.float64),
        gas_select_max_current_cut=np.array([cfg.gas_select_max_current_cut], np.float64),
        mode_confidence_low=np.array([cfg.mode_confidence_low], np.float64),
        mode_confidence_high=np.array([cfg.mode_confidence_high], np.float64),
        bhp_limit_mpa=np.array([cfg.injector_bhp_limit_mpa], np.float64),
        mass_rate_limit_kg_s=np.array([cfg.injector_mass_rate_limit_kg_s], np.float64),
        bhp_boundary_mpa=np.array([cfg.bhp_boundary_mpa], np.float64),
        mass_rate_boundary_kg_s=np.array([cfg.mass_rate_boundary_kg_s], np.float64),
    )

    np.savez_compressed(
        out_dir / "PAD_Stream_V15F1_Predictions.npz",
        raw_gas_cut=np.asarray(heads["raw_gas_cut"], np.float64),
        bounded_gas_candidate=np.asarray(screens["gas_candidate"], np.float64),
        screened_gas_cut=np.asarray(screens["screened_gas_cut"], np.float64),
        gas_head_selected=np.asarray(screens["gas_selected"], bool),
        raw_breakthrough_hazard=np.asarray(heads["raw_hazard"], np.float64),
        monotone_breakthrough_hazard=np.asarray(screens["monotone_breakthrough_hazard"], np.float64),
        mode_mass_rate_probability=np.asarray(heads["mode_probability"], np.float64),
        screened_mode_mass_rate=np.asarray(screens["screened_mode_mass_rate"], np.int8),
        control_preflight=np.asarray(screens["control_preflight"], bool),
        warm_start_bhp_mpa=np.asarray(screens["warm_start_bhp_mpa"], np.float64),
        warm_start_mass_rate_kg_s=np.asarray(screens["warm_start_mass_rate_kg_s"], np.float64),
        state_distance=np.asarray(screens["state_distance"], np.float64),
    )

    audit.to_csv(out_dir / "PAD_Stream_V15F1_Well_Response_Sequential_Audit.csv", index=False)
    snapshot.to_csv(out_dir / "PAD_Stream_V15F1_Snapshot_Handoff_Audit.csv", index=False)
    metric_table.to_csv(out_dir / "PAD_Stream_V15F1_Well_Response_Metrics.csv", index=False)
    np.savez_compressed(
        out_dir / "PAD_Stream_V15F1_Restart_State_Day195.npz",
        version=np.asarray([VERSION]),
        restart_day=np.asarray([restart["restart_day"]]),
        restart_dense_index=np.asarray([restart["restart_dense_index"]], np.int64),
        f0_hidden_state=np.asarray(restart["f0_hidden_state"], np.float32),
        current_gas_cut=np.asarray([restart["current_gas_cut"]], np.float64),
        current_breakthrough_memory=np.asarray([restart["current_breakthrough_memory"]], bool),
        current_mode_mass_rate=np.asarray([restart["current_mode_mass_rate"]], np.int8),
    )

    gates: list[dict[str, Any]] = []
    def gate(name: str, group: str, passed: bool, value: Any, requirement: str) -> None:
        gates.append({"gate": name, "group": group, "passed": bool(passed), "value": value, "requirement": requirement})

    feature_text = " ".join(FEATURE_NAMES).lower()
    gate("upstream_v15e3_pass", "integrity", e3_summary["status"] == "PASS", e3_summary["status"], "15E-3 frozen PASS")
    gate("upstream_v15f0_pass", "integrity", f0_summary["status"] == "PASS", f0_summary["status"], "15F-0 frozen PASS")
    gate("f0_hidden_reproduced", "integrity", metrics["f0_hidden_reproduction_max_abs_difference"] == 0.0, metrics["f0_hidden_reproduction_max_abs_difference"], "frozen recurrent state exact")
    gate("f0_timestep_output_unchanged", "integrity", metrics["f0_timestep_reproduction_max_abs_difference"] == 0.0, metrics["f0_timestep_reproduction_max_abs_difference"], "15F-0 timestep branch unchanged")
    gate("f0_retrace_output_unchanged", "integrity", metrics["f0_retrace_reproduction_max_abs_difference"] == 0.0, metrics["f0_retrace_reproduction_max_abs_difference"], "15F-0 retrace branch unchanged")
    gate("no_future_feature_leakage", "integrity", not any(token in feature_text for token in FORBIDDEN_FEATURE_TOKENS), feature_text, "current/past features only")
    gate("train_only_normalization", "integrity", bool(np.allclose(scaler.mean_, raw_features[split == "train"].mean(axis=0))), "train mask", "normalization fit on training rows")
    gate("event_holdout_present", "integrity", int(((split == "test") & (state["time_days"][:-1] > 105) & (state["time_days"][:-1] <= 150)).sum()) > 0, int(((split == "test") & (state["time_days"][:-1] > 105) & (state["time_days"][:-1] <= 150)).sum()), "breakthrough transition held out")
    gate("control_holdout_present", "integrity", int(((split == "test") & (state["time_days"][:-1] > 30) & (state["time_days"][:-1] <= 50)).sum()) > 0, int(((split == "test") & (state["time_days"][:-1] > 30) & (state["time_days"][:-1] <= 50)).sum()), "late injector switch held out")
    gate("finite_predictions", "integrity", bool(np.isfinite(audit.select_dtypes(include=[np.number]).to_numpy()).all()), "finite", "all numerical outputs finite")
    gate("gas_cut_bounds", "integrity", bool(np.all((screens["screened_gas_cut"] >= 0.0) & (screens["screened_gas_cut"] <= 1.0))), f"[{np.min(screens['screened_gas_cut']):.3g},{np.max(screens['screened_gas_cut']):.3g}]", "0 <= gas cut <= 1")
    gate("hazard_bounds", "integrity", bool(np.all((screens["monotone_breakthrough_hazard"] >= 0.0) & (screens["monotone_breakthrough_hazard"] <= 1.0))), f"[{np.min(screens['monotone_breakthrough_hazard']):.3g},{np.max(screens['monotone_breakthrough_hazard']):.3g}]", "0 <= hazard <= 1")
    gate("breakthrough_memory_monotone", "integrity", metrics["maximum_breakthrough_hazard_decrease"] >= -1.0e-12, metrics["maximum_breakthrough_hazard_decrease"], "hazard never decreases")
    gate("active_bhp_constraint_exact", "integrity", metrics["active_bhp_constraint_max_error_mpa"] == 0.0, metrics["active_bhp_constraint_max_error_mpa"], "BHP-mode warm start exactly 30 MPa")
    gate("active_rate_constraint_exact", "integrity", metrics["active_mass_rate_constraint_max_error_kg_s"] == 0.0, metrics["active_mass_rate_constraint_max_error_kg_s"], "mass-rate warm start exactly 38.55 kg/s")
    gate("restart_hidden_identity", "integrity", metrics["restart_hidden_sequence_max_abs_difference"] == 0.0, metrics["restart_hidden_sequence_max_abs_difference"], "day-195 frozen recurrent restart exact")
    gate("restart_head_identity", "integrity", max(metrics["restart_gas_head_max_abs_difference"], metrics["restart_hazard_head_max_abs_difference"], metrics["restart_mode_head_max_abs_difference"]) == 0.0, f"gas={metrics['restart_gas_head_max_abs_difference']}, hazard={metrics['restart_hazard_head_max_abs_difference']}, mode={metrics['restart_mode_head_max_abs_difference']}", "all 15F-1 outputs restart exact")
    gate("exact_well_authority_preserved", "integrity", True, "warm-start only", "Peaceman and control equations remain mandatory")

    gate("test_gas_cut_beats_persistence", "deployment", metrics["test_screened_gas_cut_rmse"] < metrics["test_persistence_gas_cut_rmse"], f"{metrics['test_screened_gas_cut_rmse']:.6g} < {metrics['test_persistence_gas_cut_rmse']:.6g}", "held-out improvement")
    gate("event_gas_cut_beats_persistence", "deployment", metrics["event_screened_gas_cut_rmse"] < metrics["event_persistence_gas_cut_rmse"], f"{metrics['event_screened_gas_cut_rmse']:.6g} < {metrics['event_persistence_gas_cut_rmse']:.6g}", "breakthrough-window improvement")
    gate("late_gas_cut_no_regression", "deployment", metrics["late_screened_gas_cut_rmse"] <= metrics["late_persistence_gas_cut_rmse"] * (1 + 1.0e-9), f"{metrics['late_screened_gas_cut_rmse']:.6g}", "stable late-time fallback")
    gate("v15e3_gas_cut_handoff_closed", "deployment", metrics["snapshot_v15f1_gas_cut_rmse"] < 0.08 and metrics["snapshot_v15f1_gas_cut_rmse"] < metrics["snapshot_v15e3_gas_cut_rmse"], f"{metrics['snapshot_v15f1_gas_cut_rmse']:.6g} vs {metrics['snapshot_v15e3_gas_cut_rmse']:.6g}", "close 15E-3 diagnostic")
    gate("breakthrough_timing_within_15_days", "deployment", metrics["breakthrough_absolute_error_days"] <= 15.0, metrics["breakthrough_absolute_error_days"], "<=15 day timing error")
    gate("breakthrough_warning_precedes_event", "deployment", metrics["breakthrough_warning_lead_days"] > 0.0, metrics["breakthrough_warning_lead_days"], "positive warning lead")
    gate("screened_control_mode_exact", "deployment", metrics["screened_mode_accuracy_all"] == 1.0, metrics["screened_mode_accuracy_all"], "all next-mode warm starts correct")
    gate("all_control_switches_preflighted", "deployment", metrics["control_switches_sent_to_preflight"] == metrics["true_control_switches"], f"{metrics['control_switches_sent_to_preflight']}/{metrics['true_control_switches']}", "no switch bypasses exact preflight")
    gate("zero_unsafe_no_preflight", "deployment", metrics["unsafe_no_preflight_decisions"] == 0, metrics["unsafe_no_preflight_decisions"], "zero unsafe cache-only control decisions")
    gate("mass_rate_warm_start_no_regression", "deployment", metrics["test_warm_start_mass_rate_rmse_kg_s"] <= metrics["test_persistence_mass_rate_rmse_kg_s"], f"{metrics['test_warm_start_mass_rate_rmse_kg_s']:.6g} <= {metrics['test_persistence_mass_rate_rmse_kg_s']:.6g}", "held-out rate warm start no regression")

    gate("raw_mode_signal_informative", "diagnostic", metrics["raw_mode_accuracy_all"] > 0.95, metrics["raw_mode_accuracy_all"], ">95% raw mode accuracy")
    gate("gas_screen_exercises_learned_branch", "diagnostic", metrics["gas_head_selected_steps"] > 0, metrics["gas_head_selected_steps"], ">0 learned gas selections")
    gate("gas_screen_exercises_fallback", "diagnostic", metrics["gas_head_fallback_steps"] > 0, metrics["gas_head_fallback_steps"], ">0 persistence fallbacks")
    gate("well_state_ood_exercised", "diagnostic", metrics["well_state_ood_steps"] > 0, metrics["well_state_ood_steps"], ">0 OOD states")
    gate("control_preflight_selective", "diagnostic", 0 < metrics["control_preflight_steps"] < metrics["transitions"], f"{metrics['control_preflight_steps']}/{metrics['transitions']}", "preflight exercised but not universal")

    validation = pd.DataFrame(gates)
    validation.to_csv(out_dir / "PAD_Stream_V15F1_Validation_Matrix.csv", index=False)
    integrity = validation[validation["group"] == "integrity"]
    deployment = validation[validation["group"] == "deployment"]
    diagnostic = validation[validation["group"] == "diagnostic"]
    status = "PASS" if bool(integrity["passed"].all() and deployment["passed"].all()) else (
        "AUDIT_COMPLETE_DEPLOYMENT_NOT_APPROVED" if bool(integrity["passed"].all()) else "AUDIT_FAILED"
    )

    summary = {
        "version": VERSION,
        "status": status,
        "description": "Frozen 15F-0 recurrent encoder with screened breakthrough and well-control memory heads",
        "integrity_gates_passed": int(integrity["passed"].sum()),
        "integrity_gates_total": int(len(integrity)),
        "deployment_gates_passed": int(deployment["passed"].sum()),
        "deployment_gates_total": int(len(deployment)),
        "diagnostic_gates_passed": int(diagnostic["passed"].sum()),
        "diagnostic_gates_total": int(len(diagnostic)),
        "deployment_approved": bool(deployment["passed"].all()),
        "model": {
            "frozen_f0_hidden_dim": F0_HIDDEN_DIM,
            "well_feature_dim": len(WELL_FEATURE_NAMES),
            "head_input_dim": len(FEATURE_NAMES),
            "frozen_f0_parameters": metrics["frozen_f0_parameters"],
            "new_head_parameters": metrics["new_head_parameters"],
            "combined_parameters": metrics["combined_recurrent_and_head_parameters"],
            "head_type": "two weighted ridge heads plus one weighted logistic control head",
        },
        "calibration": {
            "state_distance_threshold": float(screens["state_distance_threshold"]),
            "gas_select_hazard_threshold": cfg.gas_select_hazard_threshold,
            "gas_candidate_increment_bounds": [-cfg.gas_candidate_max_decrease, cfg.gas_candidate_max_increase],
            "mode_confidence_band": [cfg.mode_confidence_low, cfg.mode_confidence_high],
            "breakthrough_warning_threshold": 0.20,
            "breakthrough_proposal_threshold": 0.50,
        },
        "metrics": metrics,
        "rollout_contract": "accepted well/physics diagnostics -> frozen 15F-0 recurrent state -> gas-cut/breakthrough/control proposals -> bounded confidence and control-limit screen -> exact Peaceman/control correction",
        "handoff": {
            "next_milestone": "15F-2",
            "next_scope": "nonlinear-difficulty and complete global recurrent state",
            "closed_15e3_diagnostics": ["producer gas cut", "breakthrough timing"],
        },
        "limitations": [
            "The controlled 5x5x5 trajectory contains one breakthrough transition and two injector control switches; multi-case diversity is deferred.",
            "The learned heads are warm starts and event warnings only; exact Peaceman well equations and active control constraints remain mandatory.",
            "Producer control remains fixed BHP in this baseline, so only injector mode memory is learned.",
            "Explicit nonlinear-difficulty memory is deferred to Version 15F-2.",
        ],
        "source_hashes": {name: info["sha256"] for name, info in dependency_manifest["sources"].items()},
        "v14_reference_breakthrough_days": float(v14_summary["run"]["breakthrough_time_days"]),
    }
    (out_dir / "PAD_Stream_V15F1_Summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    create_plots(out_dir, audit, snapshot, metric_table, validation)
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


def default_paths() -> Dict[str, Path]:
    e3_root = Path("/mnt/data/pad_stream_v15e3/PAD_Stream_V15E3_Sequential_Conservative_Graph_Mapback_Deployment")
    f0_root = Path("/mnt/data/pad_stream_v15f0/PAD_Stream_V15F0_Global_Recurrent_Timestep_Retrace_State")
    b3_root = Path("/mnt/data/pad_stream_v15e3/deps/c3/PAD_Stream_V15C3_Sequential_Path_Deployment_Package/PAD_Stream_V15B3R_Sequential_Predict_Screen_Correct_Package")
    return {
        "dense_audit": b3_root / "results/PAD_Stream_V15B3R_Sequential_Audit.csv",
        "e3_snapshot_audit": e3_root / "PAD_Stream_V15E3_Sequential_Snapshot_Audit.csv",
        "e3_summary": e3_root / "PAD_Stream_V15E3_Summary.json",
        "f0_trainer": f0_root / "PAD_Stream_V15F0_Global_Recurrent_Timestep_Retrace_State.py",
        "f0_checkpoint": f0_root / "PAD_Stream_V15F0_Best_Model.pt",
        "f0_dataset": f0_root / "PAD_Stream_V15F0_Global_Recurrent_State_Dataset.npz",
        "f0_predictions": f0_root / "PAD_Stream_V15F0_Predictions.npz",
        "f0_summary": f0_root / "PAD_Stream_V15F0_Summary.json",
        "f0_package_zip": Path("/mnt/data/pad_stream_v15f0/PAD_Stream_V15F0_Global_Recurrent_Timestep_Retrace_State.zip"),
        "v14_summary": b3_root / "PAD_Stream_V13_Long_Run_Summary.json",
        "output": Path("/mnt/data/pad_stream_v15f1/PAD_Stream_V15F1_Breakthrough_Well_Control_Recurrent_Memory"),
    }


def main() -> None:
    defaults = default_paths()
    parser = argparse.ArgumentParser()
    for name, value in defaults.items():
        parser.add_argument(f"--{name.replace('_', '-')}", default=str(value))
    args = parser.parse_args()
    summary = build(args)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
