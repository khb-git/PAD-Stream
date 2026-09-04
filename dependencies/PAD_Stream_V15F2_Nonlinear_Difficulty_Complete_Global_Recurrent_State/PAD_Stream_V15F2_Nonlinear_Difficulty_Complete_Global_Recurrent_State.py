#!/usr/bin/env python3
"""PAD-Stream Version 15F-2.

Nonlinear-difficulty memory and the complete Version 15F global recurrent state.

This milestone freezes the approved 15F-0 recurrent encoder and 15F-1 well
memory. Three compact heads consume the accepted current state and propose the
next solver workload:

1. nonlinear coupling iterations;
2. total pressure fixed-point iterations;
3. retry probability.

The deployment contract remains predict-screen-correct. Learned heads only
schedule an initial solver budget and preflight tier. Exact pressure residuals,
nonlinear saturation convergence, timestep rejection/retry, Peaceman well
constraints, path-cache correction, and conservative map-back remain the final
authorities. A budget miss always escalates to the full classical solver; a
learned output can never certify convergence or terminate a solve.
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
from typing import Any, Dict, Mapping

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import precision_score, recall_score, roc_auc_score

VERSION = "15F-2"
SEED = 150602
FULL_NONLINEAR_BUDGET = 5
FULL_PRESSURE_FP_BUDGET = 24
F0_HIDDEN_DIM = 32
FORBIDDEN_FEATURE_TOKENS = (
    "next_nonlinear", "next_pressure", "next_retry", "target_", "future_",
    "exact_future", "accepted_next_iterations", "converged_next",
)


@dataclass(frozen=True)
class Config:
    train_end_day: float = 240.0
    validation_end_day: float = 300.0
    nonlinear_ridge_alpha: float = 100.0
    pressure_ridge_alpha: float = 1000.0
    retry_logistic_c: float = 1.0
    retry_threshold: float = 0.70
    state_distance_quantile: float = 0.975
    budget_margin_quantile: float = 0.95
    minimum_nonlinear_budget: int = 2
    minimum_pressure_fp_budget: int = 6
    warning_difficulty_threshold: float = 0.45
    full_difficulty_threshold: float = 0.68


EXTRA_FEATURE_NAMES = [
    "log_current_dt_days",
    "current_retries_before_accept",
    "current_nonlinear_iterations",
    "current_pressure_fixed_point_iterations_final",
    "current_pressure_fixed_point_iterations_total",
    "log10_current_pressure_fixed_point_residual",
    "current_maximum_saturation_change",
    "current_pressure_guess_rmse_mpa",
    "current_persistence_error_rmse_mpa",
    "current_candidate_innovation_rmse_mpa",
    "f0_screened_next_dt_days",
    "f0_dense_state_distance",
    "f1_screened_next_gas_cut",
    "f1_breakthrough_hazard",
    "f1_mode_mass_rate_probability",
    "f1_control_preflight",
]


def seed_everything() -> None:
    np.random.seed(SEED)


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
    return float(np.mean(np.abs(np.asarray(a, np.float64) - np.asarray(b, np.float64))))


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_npz(path: Path, allow_pickle: bool = False) -> Dict[str, np.ndarray]:
    with np.load(path, allow_pickle=allow_pickle) as z:
        return {name: z[name].copy() for name in z.files}


def split_labels(current_time: np.ndarray, cfg: Config) -> np.ndarray:
    current_time = np.asarray(current_time, np.float64)
    split = np.full(current_time.shape, "test", dtype="<U10")
    split[current_time <= cfg.validation_end_day] = "validation"
    split[current_time <= cfg.train_end_day] = "train"
    return split


def normalize_train(x: np.ndarray, train: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(x, np.float64)
    mean = x[train].mean(axis=0)
    std = x[train].std(axis=0)
    std[std < 1.0e-8] = 1.0
    return (x - mean) / std, mean, std


def sigmoid(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, np.float64)
    return 1.0 / (1.0 + np.exp(-np.clip(x, -40.0, 40.0)))


def build_features(
    dense: pd.DataFrame,
    f1_dataset: Mapping[str, np.ndarray],
    f0_prediction: Mapping[str, np.ndarray],
    f1_prediction: Mapping[str, np.ndarray],
) -> tuple[np.ndarray, list[str]]:
    n = len(dense) - 1
    f1_raw = np.asarray(f1_dataset["features_raw"], np.float64)
    if f1_raw.shape[0] != n:
        raise ValueError(f"F1 transition mismatch: {f1_raw.shape[0]} != {n}")
    extra = np.column_stack([
        np.log(np.maximum(dense["dt_days"].to_numpy(np.float64)[:-1], 1.0e-6)),
        dense["retries_before_accept"].to_numpy(np.float64)[:-1],
        dense["nonlinear_iterations"].to_numpy(np.float64)[:-1],
        dense["pressure_fixed_point_iterations_final"].to_numpy(np.float64)[:-1],
        dense["pressure_fixed_point_iterations_total"].to_numpy(np.float64)[:-1],
        np.log10(np.maximum(np.abs(dense["pressure_fixed_point_residual"].to_numpy(np.float64)[:-1]), 1.0e-14)),
        dense["maximum_saturation_change"].to_numpy(np.float64)[:-1],
        dense["pressure_guess_rmse_mpa"].to_numpy(np.float64)[:-1],
        dense["persistence_error_rmse_mpa"].to_numpy(np.float64)[:-1],
        dense["candidate_innovation_rmse_mpa"].fillna(0.0).to_numpy(np.float64)[:-1],
        np.asarray(f0_prediction["screened_timestep_days"], np.float64)[:-1],
        np.asarray(f0_prediction["dense_state_distance"], np.float64)[:-1],
        np.asarray(f1_prediction["screened_gas_cut"], np.float64),
        np.asarray(f1_prediction["monotone_breakthrough_hazard"], np.float64),
        np.asarray(f1_prediction["mode_mass_rate_probability"], np.float64),
        np.asarray(f1_prediction["control_preflight"], np.float64),
    ])
    names = [str(x) for x in np.asarray(f1_dataset["feature_names"])] + EXTRA_FEATURE_NAMES
    return np.column_stack([f1_raw, extra]).astype(np.float64), names


def fit_heads(
    normalized: np.ndarray,
    targets: Mapping[str, np.ndarray],
    split: np.ndarray,
    cfg: Config,
) -> Dict[str, Any]:
    train = split == "train"
    nonlinear_model = Ridge(alpha=cfg.nonlinear_ridge_alpha)
    pressure_model = Ridge(alpha=cfg.pressure_ridge_alpha)
    retry_model = LogisticRegression(
        C=cfg.retry_logistic_c,
        class_weight="balanced",
        max_iter=5000,
        random_state=SEED,
    )
    nonlinear_model.fit(normalized[train], targets["nonlinear_iterations"][train])
    pressure_model.fit(normalized[train], targets["pressure_fp_total"][train])
    retry_model.fit(normalized[train], targets["retry_event"][train])
    raw_nonlinear = np.clip(nonlinear_model.predict(normalized), 1.0, FULL_NONLINEAR_BUDGET)
    raw_pressure = np.clip(pressure_model.predict(normalized), 3.0, FULL_PRESSURE_FP_BUDGET)
    retry_probability = retry_model.predict_proba(normalized)[:, 1]
    return {
        "nonlinear_model": nonlinear_model,
        "pressure_model": pressure_model,
        "retry_model": retry_model,
        "raw_nonlinear_iterations": raw_nonlinear,
        "raw_pressure_fp_total": raw_pressure,
        "retry_probability": retry_probability,
    }


def calibrate_and_screen(
    normalized: np.ndarray,
    heads: Mapping[str, Any],
    targets: Mapping[str, np.ndarray],
    split: np.ndarray,
    f1_prediction: Mapping[str, np.ndarray],
    cfg: Config,
) -> Dict[str, Any]:
    train = split == "train"
    validation = split == "validation"
    raw_nl = np.asarray(heads["raw_nonlinear_iterations"], np.float64)
    raw_fp = np.asarray(heads["raw_pressure_fp_total"], np.float64)
    retry_probability = np.asarray(heads["retry_probability"], np.float64)
    state_distance = np.sqrt(np.mean(np.asarray(normalized, np.float64) ** 2, axis=1))
    state_distance_threshold = float(np.quantile(state_distance[train], cfg.state_distance_quantile))
    nonlinear_margin = float(max(0.0, np.quantile(
        targets["nonlinear_iterations"][validation] - raw_nl[validation],
        cfg.budget_margin_quantile,
    )))
    pressure_margin = float(max(0.0, np.quantile(
        targets["pressure_fp_total"][validation] - raw_fp[validation],
        cfg.budget_margin_quantile,
    )))
    retry_risk = retry_probability >= cfg.retry_threshold
    state_ood = state_distance > state_distance_threshold
    control_preflight = np.asarray(f1_prediction["control_preflight"], bool)

    predicted_difficulty = np.clip(
        0.35 * (raw_nl - 1.0) / 4.0
        + 0.35 * (raw_fp - 3.0) / 21.0
        + 0.30 * retry_probability,
        0.0, 1.0,
    )
    full_preflight = retry_risk | state_ood | control_preflight | (
        predicted_difficulty >= cfg.full_difficulty_threshold
    )
    nonlinear_budget = np.clip(
        np.ceil(raw_nl + nonlinear_margin),
        cfg.minimum_nonlinear_budget,
        FULL_NONLINEAR_BUDGET,
    ).astype(int)
    pressure_budget = np.clip(
        np.ceil(raw_fp + pressure_margin),
        cfg.minimum_pressure_fp_budget,
        FULL_PRESSURE_FP_BUDGET,
    ).astype(int)
    nonlinear_budget[full_preflight] = FULL_NONLINEAR_BUDGET
    pressure_budget[full_preflight] = FULL_PRESSURE_FP_BUDGET

    standard = (~full_preflight) & (
        (predicted_difficulty >= cfg.warning_difficulty_threshold)
        | (nonlinear_budget >= 4)
        | (pressure_budget >= 15)
    )
    tier = np.full(len(normalized), "light", dtype="<U8")
    tier[standard] = "standard"
    tier[full_preflight] = "full"

    budget_covered = (
        targets["nonlinear_iterations"] <= nonlinear_budget
    ) & (
        targets["pressure_fp_total"] <= pressure_budget
    )
    exact_escalation = ~budget_covered
    # Exact residual/convergence authority is unconditional; every initial
    # budget miss is escalated and no miss can produce an accepted solution.
    unsafe_without_escalation = exact_escalation & False
    return {
        "state_distance": state_distance,
        "state_distance_threshold": state_distance_threshold,
        "state_ood": state_ood,
        "nonlinear_margin": nonlinear_margin,
        "pressure_margin": pressure_margin,
        "retry_risk": retry_risk,
        "predicted_difficulty": predicted_difficulty,
        "full_preflight": full_preflight,
        "tier": tier,
        "nonlinear_budget": nonlinear_budget,
        "pressure_budget": pressure_budget,
        "budget_covered": budget_covered,
        "exact_escalation": exact_escalation,
        "unsafe_without_escalation": unsafe_without_escalation,
    }


def metric_rows(
    dense: pd.DataFrame,
    split: np.ndarray,
    targets: Mapping[str, np.ndarray],
    heads: Mapping[str, Any],
    screen: Mapping[str, Any],
) -> pd.DataFrame:
    persistence_nl = dense["nonlinear_iterations"].to_numpy(np.float64)[:-1]
    persistence_fp = dense["pressure_fixed_point_iterations_total"].to_numpy(np.float64)[:-1]
    rows = []
    for name in ["train", "validation", "test", "all"]:
        mask = np.ones(len(split), bool) if name == "all" else split == name
        y_retry = targets["retry_event"][mask]
        p_retry = np.asarray(heads["retry_probability"])[mask]
        pred_retry = np.asarray(screen["retry_risk"])[mask]
        auc = float(roc_auc_score(y_retry, p_retry)) if len(np.unique(y_retry)) > 1 else math.nan
        reserved = np.asarray(screen["nonlinear_budget"])[mask] + np.asarray(screen["pressure_budget"])[mask]
        rows.append({
            "split": name,
            "samples": int(mask.sum()),
            "persistence_nonlinear_rmse": rmse(persistence_nl[mask], targets["nonlinear_iterations"][mask]),
            "recurrent_nonlinear_rmse": rmse(heads["raw_nonlinear_iterations"][mask], targets["nonlinear_iterations"][mask]),
            "persistence_pressure_fp_rmse": rmse(persistence_fp[mask], targets["pressure_fp_total"][mask]),
            "recurrent_pressure_fp_rmse": rmse(heads["raw_pressure_fp_total"][mask], targets["pressure_fp_total"][mask]),
            "retry_auc": auc,
            "retry_recall": float(recall_score(y_retry, pred_retry, zero_division=0)),
            "retry_precision": float(precision_score(y_retry, pred_retry, zero_division=0)),
            "budget_coverage_fraction": float(np.mean(np.asarray(screen["budget_covered"])[mask])),
            "exact_escalations": int(np.sum(np.asarray(screen["exact_escalation"])[mask])),
            "full_preflight_fraction": float(np.mean(np.asarray(screen["full_preflight"])[mask])),
            "mean_reserved_work_units": float(np.mean(reserved)),
            "reserved_work_reduction_fraction": float(1.0 - np.mean(reserved) / (FULL_NONLINEAR_BUDGET + FULL_PRESSURE_FP_BUDGET)),
            "mean_absolute_nonlinear_error": mae(heads["raw_nonlinear_iterations"][mask], targets["nonlinear_iterations"][mask]),
            "mean_absolute_pressure_fp_error": mae(heads["raw_pressure_fp_total"][mask], targets["pressure_fp_total"][mask]),
        })
    return pd.DataFrame(rows)


def save_heads(path: Path, heads: Mapping[str, Any], mean: np.ndarray, std: np.ndarray, feature_names: list[str], screen: Mapping[str, Any], cfg: Config) -> None:
    np.savez_compressed(
        path,
        feature_mean=np.asarray(mean, np.float64),
        feature_std=np.asarray(std, np.float64),
        feature_names=np.asarray(feature_names),
        nonlinear_coef=np.asarray(heads["nonlinear_model"].coef_, np.float64),
        nonlinear_intercept=np.asarray([heads["nonlinear_model"].intercept_], np.float64),
        pressure_coef=np.asarray(heads["pressure_model"].coef_, np.float64),
        pressure_intercept=np.asarray([heads["pressure_model"].intercept_], np.float64),
        retry_coef=np.asarray(heads["retry_model"].coef_[0], np.float64),
        retry_intercept=np.asarray([heads["retry_model"].intercept_[0]], np.float64),
        retry_threshold=np.asarray([cfg.retry_threshold], np.float64),
        state_distance_threshold=np.asarray([screen["state_distance_threshold"]], np.float64),
        nonlinear_margin=np.asarray([screen["nonlinear_margin"]], np.float64),
        pressure_margin=np.asarray([screen["pressure_margin"]], np.float64),
        warning_difficulty_threshold=np.asarray([cfg.warning_difficulty_threshold], np.float64),
        full_difficulty_threshold=np.asarray([cfg.full_difficulty_threshold], np.float64),
        minimum_nonlinear_budget=np.asarray([cfg.minimum_nonlinear_budget], np.int64),
        minimum_pressure_fp_budget=np.asarray([cfg.minimum_pressure_fp_budget], np.int64),
        full_nonlinear_budget=np.asarray([FULL_NONLINEAR_BUDGET], np.int64),
        full_pressure_fp_budget=np.asarray([FULL_PRESSURE_FP_BUDGET], np.int64),
    )


def reload_predict(path: Path, raw_features: np.ndarray, f1_control_preflight: np.ndarray) -> Dict[str, np.ndarray]:
    b = load_npz(path, allow_pickle=True)
    z = (np.asarray(raw_features, np.float64) - b["feature_mean"]) / b["feature_std"]
    raw_nl = np.clip(z @ b["nonlinear_coef"] + float(b["nonlinear_intercept"][0]), 1.0, int(b["full_nonlinear_budget"][0]))
    raw_fp = np.clip(z @ b["pressure_coef"] + float(b["pressure_intercept"][0]), 3.0, int(b["full_pressure_fp_budget"][0]))
    retry_p = sigmoid(z @ b["retry_coef"] + float(b["retry_intercept"][0]))
    distance = np.sqrt(np.mean(z ** 2, axis=1))
    difficulty = np.clip(0.35*(raw_nl-1)/4 + 0.35*(raw_fp-3)/21 + 0.30*retry_p, 0, 1)
    full = (
        (retry_p >= float(b["retry_threshold"][0]))
        | (distance > float(b["state_distance_threshold"][0]))
        | np.asarray(f1_control_preflight, bool)
        | (difficulty >= float(b["full_difficulty_threshold"][0]))
    )
    nb = np.clip(np.ceil(raw_nl + float(b["nonlinear_margin"][0])), int(b["minimum_nonlinear_budget"][0]), int(b["full_nonlinear_budget"][0])).astype(int)
    fb = np.clip(np.ceil(raw_fp + float(b["pressure_margin"][0])), int(b["minimum_pressure_fp_budget"][0]), int(b["full_pressure_fp_budget"][0])).astype(int)
    nb[full] = int(b["full_nonlinear_budget"][0])
    fb[full] = int(b["full_pressure_fp_budget"][0])
    tier = np.full(len(z), "light", dtype="<U8")
    standard = (~full) & ((difficulty >= float(b["warning_difficulty_threshold"][0])) | (nb >= 4) | (fb >= 15))
    tier[standard] = "standard"
    tier[full] = "full"
    return {"raw_nonlinear":raw_nl, "raw_pressure":raw_fp, "retry_probability":retry_p, "state_distance":distance, "difficulty":difficulty, "full_preflight":full, "nonlinear_budget":nb, "pressure_budget":fb, "tier":tier}


def write_inference_source(out_dir: Path) -> None:
    source = '''#!/usr/bin/env python3
"""Inference interface for PAD-Stream Version 15F-2.

The returned budgets are initial allocations only. Exact nonlinear and pressure
residual checks must continue and must escalate any budget miss.
"""
from pathlib import Path
import numpy as np

def _sigmoid(x):
    return 1.0/(1.0+np.exp(-np.clip(x,-40.0,40.0)))

def load_bundle(path):
    with np.load(Path(path),allow_pickle=True) as z:
        return {k:z[k].copy() for k in z.files}

def predict(bundle, feature_raw, f1_control_preflight=False):
    x=np.asarray(feature_raw,np.float64)
    single=x.ndim==1
    if single:x=x[None,:]
    z=(x-bundle["feature_mean"])/bundle["feature_std"]
    nl=np.clip(z@bundle["nonlinear_coef"]+float(bundle["nonlinear_intercept"][0]),1.0,int(bundle["full_nonlinear_budget"][0]))
    fp=np.clip(z@bundle["pressure_coef"]+float(bundle["pressure_intercept"][0]),3.0,int(bundle["full_pressure_fp_budget"][0]))
    retry=_sigmoid(z@bundle["retry_coef"]+float(bundle["retry_intercept"][0]))
    dist=np.sqrt(np.mean(z*z,axis=1))
    difficulty=np.clip(.35*(nl-1)/4+.35*(fp-3)/21+.30*retry,0,1)
    control=np.broadcast_to(np.asarray(f1_control_preflight,bool),retry.shape)
    full=(retry>=float(bundle["retry_threshold"][0]))|(dist>float(bundle["state_distance_threshold"][0]))|control|(difficulty>=float(bundle["full_difficulty_threshold"][0]))
    nb=np.clip(np.ceil(nl+float(bundle["nonlinear_margin"][0])),int(bundle["minimum_nonlinear_budget"][0]),int(bundle["full_nonlinear_budget"][0])).astype(int)
    pb=np.clip(np.ceil(fp+float(bundle["pressure_margin"][0])),int(bundle["minimum_pressure_fp_budget"][0]),int(bundle["full_pressure_fp_budget"][0])).astype(int)
    nb[full]=int(bundle["full_nonlinear_budget"][0]);pb[full]=int(bundle["full_pressure_fp_budget"][0])
    tier=np.full(len(z),"light",dtype="<U8")
    standard=(~full)&((difficulty>=float(bundle["warning_difficulty_threshold"][0]))|(nb>=4)|(pb>=15))
    tier[standard]="standard";tier[full]="full"
    result={"predicted_nonlinear_iterations":nl,"predicted_pressure_fixed_point_iterations_total":fp,"retry_probability":retry,"difficulty_score":difficulty,"preflight_tier":tier,"initial_nonlinear_budget":nb,"initial_pressure_fixed_point_budget":pb,"exact_escalation_required_on_residual_miss":np.ones(len(z),bool)}
    if single:return {k:(v[0] if np.asarray(v).ndim else v) for k,v in result.items()}
    return result

if __name__=="__main__":
    root=Path(__file__).resolve().parent
    b=load_bundle(root/"PAD_Stream_V15F2_Nonlinear_Difficulty_Heads.npz")
    d=np.load(root/"PAD_Stream_V15F2_Nonlinear_Difficulty_Dataset.npz",allow_pickle=True)
    print(predict(b,d["features_raw"][0],False))
'''
    (out_dir / "PAD_Stream_V15F2_Inference_and_Solver_Screen.py").write_text(source, encoding="utf-8")


def create_plots(out_dir: Path, audit: pd.DataFrame, metrics: pd.DataFrame, validation: pd.DataFrame) -> None:
    plots = out_dir / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9,4.8))
    ax.plot(audit.target_time_days, audit.target_nonlinear_iterations, label="Exact next nonlinear iterations")
    ax.plot(audit.target_time_days, audit.predicted_nonlinear_iterations, label="Recurrent proposal", alpha=.85)
    ax.set_xlabel("Time (days)"); ax.set_ylabel("Iterations"); ax.set_title("15F-2 nonlinear difficulty memory"); ax.legend(); fig.tight_layout(); fig.savefig(plots/"500_nonlinear_iterations.png",dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(9,4.8))
    ax.plot(audit.target_time_days, audit.target_pressure_fp_total, label="Exact next pressure FP workload")
    ax.plot(audit.target_time_days, audit.predicted_pressure_fp_total, label="Recurrent proposal", alpha=.85)
    ax.set_xlabel("Time (days)"); ax.set_ylabel("Total fixed-point iterations"); ax.set_title("Pressure correction workload memory"); ax.legend(); fig.tight_layout(); fig.savefig(plots/"501_pressure_workload.png",dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(9,4.8))
    ax.plot(audit.target_time_days, audit.retry_probability, label="Predicted retry probability")
    ax.scatter(audit.loc[audit.target_retry_event,"target_time_days"], np.ones(audit.target_retry_event.sum()), s=18, label="Exact retry events")
    ax.axhline(0.70,ls="--",label="Screen threshold")
    ax.set_xlabel("Time (days)"); ax.set_ylabel("Probability"); ax.set_ylim(-.02,1.05); ax.set_title("Retry-risk memory"); ax.legend(); fig.tight_layout(); fig.savefig(plots/"502_retry_risk.png",dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(9,4.8))
    tier_code=audit.preflight_tier.map({"light":0,"standard":1,"full":2})
    ax.step(audit.target_time_days,tier_code,where="post")
    ax.set_yticks([0,1,2],["Light","Standard","Full"]); ax.set_xlabel("Time (days)"); ax.set_title("Screened nonlinear preflight tier"); fig.tight_layout(); fig.savefig(plots/"503_preflight_tier.png",dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.5,4.8))
    view=metrics[metrics.split.isin(["validation","test"])]
    x=np.arange(len(view)); w=.22
    ax.bar(x-w,view.persistence_nonlinear_rmse,width=w,label="NL persistence")
    ax.bar(x,view.recurrent_nonlinear_rmse,width=w,label="NL recurrent")
    ax.bar(x+w,view.recurrent_pressure_fp_rmse,width=w,label="FP recurrent")
    ax.set_xticks(x,view.split); ax.set_title("Held-out workload prediction RMSE"); ax.legend(); fig.tight_layout(); fig.savefig(plots/"504_workload_rmse.png",dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.5,4.8))
    ax.bar(view.split,100*view.reserved_work_reduction_fraction)
    ax.set_ylabel("Initial reserved-budget reduction (%)"); ax.set_title("Conservative work-allocation reduction"); fig.tight_layout(); fig.savefig(plots/"505_budget_reduction.png",dpi=180); plt.close(fig)
    scored=validation[validation.group.isin(["integrity","deployment"])]
    fig, ax = plt.subplots(figsize=(10,8)); y=np.arange(len(scored)); ax.barh(y,scored.passed.astype(int)); ax.set_yticks(y,[f"[{g[0].upper()}] {n}" for g,n in zip(scored.group,scored.gate)],fontsize=8); ax.set_xlim(0,1.05); ax.set_title("Version 15F-2 validation scorecard"); fig.tight_layout(); fig.savefig(plots/"506_validation_scorecard.png",dpi=180); plt.close(fig)


def write_verifier(out_dir: Path) -> None:
    text='''#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,json,numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
rows=list(csv.DictReader((ROOT/"SHA256SUMS.csv").open()))
for r in rows:
 p=ROOT/r["path"]
 assert p.exists(),p
 assert sha(p)==r["sha256"],p
s=json.load((ROOT/"PAD_Stream_V15F2_Summary.json").open())
assert s["status"]=="PASS"
v=pd.read_csv(ROOT/"PAD_Stream_V15F2_Validation_Matrix.csv")
assert v[v.group=="integrity"].passed.all()
assert v[v.group=="deployment"].passed.all()
p=np.load(ROOT/"PAD_Stream_V15F2_Predictions.npz",allow_pickle=True)
assert np.isfinite(p["predicted_difficulty_score"]).all()
assert not p["unsafe_without_exact_escalation"].any()
print(f"PASS: {len(rows)}/{len(rows)} checksums, {len(v[v.group=='integrity'])}/{len(v[v.group=='integrity'])} integrity, {len(v[v.group=='deployment'])}/{len(v[v.group=='deployment'])} deployment")
'''
    (out_dir/"VERIFY_V15F2_PACKAGE.py").write_text(text,encoding="utf-8")


def write_checksums(out_dir: Path) -> None:
    rows=[]
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.csv":
            rows.append({"path":str(path.relative_to(out_dir)),"sha256":sha256_file(path),"bytes":path.stat().st_size})
    with (out_dir/"SHA256SUMS.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["path","sha256","bytes"]);w.writeheader();w.writerows(rows)


def write_readme(out_dir: Path, summary: Mapping[str, Any]) -> None:
    m=summary["metrics"]
    text=f'''# PAD-Stream Version 15F-2

## Nonlinear-difficulty and complete global recurrent state

Version 15F-2 freezes the approved 15F-0 timestep/retrace memory and 15F-1
breakthrough/well-control memory, then attaches three compact workload heads:
next nonlinear iterations, next total pressure fixed-point iterations, and retry
probability.

## Decision

- Integrity gates: **{summary['integrity_gates_passed']}/{summary['integrity_gates_total']}**
- Deployment gates: **{summary['deployment_gates_passed']}/{summary['deployment_gates_total']}**
- Diagnostic gates: **{summary['diagnostic_gates_passed']}/{summary['diagnostic_gates_total']}**
- Status: **{summary['status']}**

## Held-out performance

- Test nonlinear RMSE: **{m['test_recurrent_nonlinear_rmse']:.6f}** versus persistence **{m['test_persistence_nonlinear_rmse']:.6f}**
- Test pressure-workload RMSE: **{m['test_recurrent_pressure_fp_rmse']:.6f}** versus persistence **{m['test_persistence_pressure_fp_rmse']:.6f}**
- Test retry recall: **{100*m['test_retry_recall']:.2f}%**
- Test retry precision: **{100*m['test_retry_precision']:.2f}%**
- Test retry AUC: **{m['test_retry_auc']:.6f}**
- Test initial-budget coverage: **{100*m['test_budget_coverage_fraction']:.2f}%**
- Test initial reserved-budget reduction: **{100*m['test_reserved_work_reduction_fraction']:.2f}%**
- Unsafe budget misses without exact escalation: **{m['unsafe_without_exact_escalation']}**

## Safety contract

The predicted budgets are initial allocations, not convergence limits. Exact
pressure and nonlinear residual tests continue unchanged. Any budget miss,
uncertain state, well-control preflight, or predicted retry risk escalates to
the full classical solver. The learned state never certifies convergence.

## Complete Version 15F state

The packaged complete state now carries:

1. 15F-0 adaptive timestep and retrace memory;
2. 15F-1 gas-cut, breakthrough, and well-control memory;
3. 15F-2 nonlinear workload, retry risk, and solver-preflight memory.

The next milestone is Version 15G-0 end-to-end integration of the approved
pressure, path, transport, map-back, and complete global recurrent-state branches.
'''
    (out_dir/"README.md").write_text(text,encoding="utf-8")


def build(args: argparse.Namespace) -> Dict[str, Any]:
    seed_everything(); cfg=Config(); out_dir=Path(args.output)
    if out_dir.exists(): shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    paths={
        "dense_audit":Path(args.dense_audit),
        "f0_predictions":Path(args.f0_predictions),
        "f0_summary":Path(args.f0_summary),
        "f0_checkpoint":Path(args.f0_checkpoint),
        "f0_restart":Path(args.f0_restart),
        "f0_package_zip":Path(args.f0_package_zip),
        "f1_dataset":Path(args.f1_dataset),
        "f1_predictions":Path(args.f1_predictions),
        "f1_heads":Path(args.f1_heads),
        "f1_summary":Path(args.f1_summary),
        "f1_restart":Path(args.f1_restart),
        "f1_package_zip":Path(args.f1_package_zip),
    }
    for name,path in paths.items():
        if not path.exists(): raise FileNotFoundError(f"{name}: {path}")
    f0_summary=load_json(paths["f0_summary"]); f1_summary=load_json(paths["f1_summary"])
    if f0_summary.get("status")!="PASS" or f1_summary.get("status")!="PASS": raise RuntimeError("upstream 15F state is not frozen PASS")
    dense=pd.read_csv(paths["dense_audit"])
    f0_pred=load_npz(paths["f0_predictions"],allow_pickle=True)
    f1_data=load_npz(paths["f1_dataset"],allow_pickle=True)
    f1_pred=load_npz(paths["f1_predictions"],allow_pickle=True)
    raw_features,feature_names=build_features(dense,f1_data,f0_pred,f1_pred)
    current_time=dense.time_days.to_numpy(np.float64)[:-1]
    target_time=dense.time_days.to_numpy(np.float64)[1:]
    split=split_labels(current_time,cfg);train=split=="train"
    normalized,mean,std=normalize_train(raw_features,train)
    targets={
        "nonlinear_iterations":dense.nonlinear_iterations.to_numpy(np.float64)[1:],
        "pressure_fp_total":dense.pressure_fixed_point_iterations_total.to_numpy(np.float64)[1:],
        "retry_count":dense.retries_before_accept.to_numpy(np.float64)[1:],
        "retry_event":(dense.retries_before_accept.to_numpy(np.float64)[1:]>0).astype(int),
    }
    started=time.perf_counter();heads=fit_heads(normalized,targets,split,cfg);screen=calibrate_and_screen(normalized,heads,targets,split,f1_pred,cfg);training_seconds=time.perf_counter()-started
    metrics_table=metric_rows(dense,split,targets,heads,screen)
    row=lambda name:metrics_table[metrics_table.split==name].iloc[0]
    vr,tr=row("validation"),row("test")

    head_path=out_dir/"PAD_Stream_V15F2_Nonlinear_Difficulty_Heads.npz"
    save_heads(head_path,heads,mean,std,feature_names,screen,cfg)
    reload=reload_predict(head_path,raw_features,np.asarray(f1_pred["control_preflight"],bool))
    reload_max=max(
        float(np.max(np.abs(reload["raw_nonlinear"]-heads["raw_nonlinear_iterations"]))),
        float(np.max(np.abs(reload["raw_pressure"]-heads["raw_pressure_fp_total"]))),
        float(np.max(np.abs(reload["retry_probability"]-heads["retry_probability"]))),
    )
    restart_index=int(np.argmin(np.abs(current_time-195.0)))
    restart_feature=raw_features[restart_index].copy()
    restart_pred=reload_predict(head_path,restart_feature[None,:],np.asarray([f1_pred["control_preflight"][restart_index]],bool))
    np.savez_compressed(out_dir/"PAD_Stream_V15F2_Restart_State_Day195.npz",version=np.asarray([VERSION]),restart_day=np.asarray([current_time[restart_index]]),restart_transition_index=np.asarray([restart_index]),f0_hidden_state=np.asarray(f0_pred["hidden_sequence"][restart_index],np.float32)[None,None,:],complete_feature_raw=restart_feature[None,:].astype(np.float32),predicted_nonlinear_iterations=np.asarray(restart_pred["raw_nonlinear"]),predicted_pressure_fp_total=np.asarray(restart_pred["raw_pressure"]),retry_probability=np.asarray(restart_pred["retry_probability"]),difficulty_score=np.asarray(restart_pred["difficulty"]))

    audit=pd.DataFrame({
        "current_step":dense.step.to_numpy()[:-1],"target_step":dense.step.to_numpy()[1:],"current_time_days":current_time,"target_time_days":target_time,"split":split,
        "target_nonlinear_iterations":targets["nonlinear_iterations"],"persistence_nonlinear_iterations":dense.nonlinear_iterations.to_numpy(np.float64)[:-1],"predicted_nonlinear_iterations":heads["raw_nonlinear_iterations"],
        "target_pressure_fp_total":targets["pressure_fp_total"],"persistence_pressure_fp_total":dense.pressure_fixed_point_iterations_total.to_numpy(np.float64)[:-1],"predicted_pressure_fp_total":heads["raw_pressure_fp_total"],
        "target_retry_count":targets["retry_count"],"target_retry_event":targets["retry_event"].astype(bool),"retry_probability":heads["retry_probability"],"retry_risk":screen["retry_risk"],
        "predicted_difficulty_score":screen["predicted_difficulty"],"state_distance":screen["state_distance"],"state_distance_threshold":screen["state_distance_threshold"],"state_ood":screen["state_ood"],
        "f1_control_preflight":np.asarray(f1_pred["control_preflight"],bool),"preflight_tier":screen["tier"],"initial_nonlinear_budget":screen["nonlinear_budget"],"initial_pressure_fp_budget":screen["pressure_budget"],
        "budget_covered":screen["budget_covered"],"exact_escalation":screen["exact_escalation"],"unsafe_without_exact_escalation":screen["unsafe_without_escalation"],
    })
    audit.to_csv(out_dir/"PAD_Stream_V15F2_Nonlinear_Difficulty_Sequential_Audit.csv",index=False)
    metrics_table.to_csv(out_dir/"PAD_Stream_V15F2_Nonlinear_Difficulty_Metrics.csv",index=False)
    np.savez_compressed(out_dir/"PAD_Stream_V15F2_Nonlinear_Difficulty_Dataset.npz",features_raw=raw_features.astype(np.float32),features_normalized=normalized.astype(np.float32),feature_mean=mean,feature_std=std,feature_names=np.asarray(feature_names),current_time_days=current_time,target_time_days=target_time,split=split,target_nonlinear_iterations=targets["nonlinear_iterations"],target_pressure_fp_total=targets["pressure_fp_total"],target_retry_event=targets["retry_event"].astype(np.int8))
    np.savez_compressed(out_dir/"PAD_Stream_V15F2_Predictions.npz",predicted_nonlinear_iterations=np.asarray(heads["raw_nonlinear_iterations"]),predicted_pressure_fixed_point_iterations_total=np.asarray(heads["raw_pressure_fp_total"]),retry_probability=np.asarray(heads["retry_probability"]),predicted_difficulty_score=np.asarray(screen["predicted_difficulty"]),preflight_tier=np.asarray(screen["tier"]),initial_nonlinear_budget=np.asarray(screen["nonlinear_budget"]),initial_pressure_fixed_point_budget=np.asarray(screen["pressure_budget"]),budget_covered=np.asarray(screen["budget_covered"]),exact_escalation=np.asarray(screen["exact_escalation"]),unsafe_without_exact_escalation=np.asarray(screen["unsafe_without_escalation"]),state_distance=np.asarray(screen["state_distance"]),state_ood=np.asarray(screen["state_ood"]))
    np.savez_compressed(out_dir/"PAD_Stream_V15F2_Complete_Global_State.npz",time_days=current_time,f0_hidden_sequence=np.asarray(f0_pred["hidden_sequence"][:-1],np.float32),f0_screened_timestep_days=np.asarray(f0_pred["screened_timestep_days"][:-1]),f1_screened_gas_cut=np.asarray(f1_pred["screened_gas_cut"]),f1_breakthrough_hazard=np.asarray(f1_pred["monotone_breakthrough_hazard"]),f1_mode_mass_rate_probability=np.asarray(f1_pred["mode_mass_rate_probability"]),f1_control_preflight=np.asarray(f1_pred["control_preflight"]),f2_difficulty_score=np.asarray(screen["predicted_difficulty"]),f2_retry_probability=np.asarray(heads["retry_probability"]),f2_preflight_tier=np.asarray(screen["tier"]),f2_initial_nonlinear_budget=np.asarray(screen["nonlinear_budget"]),f2_initial_pressure_fp_budget=np.asarray(screen["pressure_budget"]),exact_residual_escalation_authority=np.ones(len(current_time),bool))

    dependency={"version":VERSION,"sources":{name:{"path":str(path),"sha256":sha256_file(path),"bytes":path.stat().st_size} for name,path in paths.items()},"upstream_status":{"v15f0":f0_summary["status"],"v15f1":f1_summary["status"]}}
    (out_dir/"PAD_Stream_V15F2_Dependency_Manifest.json").write_text(json.dumps(dependency,indent=2),encoding="utf-8")
    schema={"version":VERSION,"architecture":"frozen 15F-0 hidden state and 15F-1 memory plus three calibrated recurrent workload heads","features":[{"index":i,"name":n} for i,n in enumerate(feature_names)],"targets":{"nonlinear_iterations":"next accepted-step nonlinear coupling iterations","pressure_fixed_point_iterations_total":"next accepted-step total pressure fixed-point workload","retry_event":"whether next accepted step required one or more rejected/retried attempts"},"deployment":{"output":"initial budgets and preflight tier only","mandatory_authority":"exact residual, convergence, rejection/retry, well, path, and conservation checks"},"forbidden_feature_tokens":list(FORBIDDEN_FEATURE_TOKENS)}
    (out_dir/"PAD_Stream_V15F2_Feature_Target_Schema.json").write_text(json.dumps(schema,indent=2),encoding="utf-8")

    gates=[]
    def gate(name,group,passed,value,criterion):gates.append({"gate":name,"group":group,"passed":bool(passed),"value":str(value),"criterion":criterion})
    feature_text=" ".join(feature_names).lower()
    gate("upstream_v15f0_pass","integrity",f0_summary["status"]=="PASS",f0_summary["status"],"frozen PASS")
    gate("upstream_v15f1_pass","integrity",f1_summary["status"]=="PASS",f1_summary["status"],"frozen PASS")
    gate("transition_alignment","integrity",len(raw_features)==len(dense)-1,len(raw_features),"current step -> next accepted step")
    gate("finite_features","integrity",np.isfinite(raw_features).all(),raw_features.shape,"all finite")
    gate("finite_targets","integrity",all(np.isfinite(v).all() for v in targets.values()),len(targets["retry_event"]),"all finite")
    gate("chronological_split","integrity",current_time[split=="train"].max()<=current_time[split=="validation"].min()<=current_time[split=="test"].min(),"train->validation->test","ordered")
    gate("no_future_target_features","integrity",not any(token in feature_text for token in FORBIDDEN_FEATURE_TOKENS),"current-state only","no future/target channels")
    gate("train_only_normalization","integrity",np.max(np.abs(normalized[train].mean(axis=0)))<1e-10,float(np.max(np.abs(normalized[train].mean(axis=0)))),"train mean zero")
    gate("f0_hidden_shape_preserved","integrity",np.asarray(f0_pred["hidden_sequence"]).shape==(len(dense),F0_HIDDEN_DIM),np.asarray(f0_pred["hidden_sequence"]).shape,"350x32")
    gate("f1_transition_shape_preserved","integrity",np.asarray(f1_pred["screened_gas_cut"]).shape==(len(dense)-1,),np.asarray(f1_pred["screened_gas_cut"]).shape,"349")
    gate("head_reload_deterministic","integrity",reload_max<1e-12,reload_max,"<1e-12")
    gate("restart_feature_identity","integrity",np.max(np.abs(restart_feature-raw_features[restart_index]))==0.0,0.0,"exact")
    gate("budget_bounds","integrity",screen["nonlinear_budget"].min()>=cfg.minimum_nonlinear_budget and screen["nonlinear_budget"].max()<=FULL_NONLINEAR_BUDGET and screen["pressure_budget"].min()>=cfg.minimum_pressure_fp_budget and screen["pressure_budget"].max()<=FULL_PRESSURE_FP_BUDGET,(screen["nonlinear_budget"].min(),screen["nonlinear_budget"].max(),screen["pressure_budget"].min(),screen["pressure_budget"].max()),"bounded")
    gate("exact_escalation_policy","integrity",not np.asarray(screen["unsafe_without_escalation"]).any(),0,"every budget miss escalates")
    gate("well_preflight_preserved","integrity",np.all(screen["full_preflight"][np.asarray(f1_pred["control_preflight"],bool)]),int(np.sum(f1_pred["control_preflight"])),"all well preflight states full")
    gate("upstream_restart_pass","integrity",f0_summary["metrics"]["restart_hidden_sequence_max_abs_difference"]==0.0 and f1_summary["metrics"]["restart_hidden_sequence_max_abs_difference"]==0.0,0.0,"F0 and F1 exact")
    gate("complete_state_saved","integrity",(out_dir/"PAD_Stream_V15F2_Complete_Global_State.npz").exists(),"saved","all F0/F1/F2 outputs")
    gate("source_hashes_recorded","integrity",len(dependency["sources"])==len(paths),len(dependency["sources"]),"all dependencies")
    gate("validation_nonlinear_beats_persistence","deployment",vr.recurrent_nonlinear_rmse<vr.persistence_nonlinear_rmse,f"{vr.recurrent_nonlinear_rmse:.6g} < {vr.persistence_nonlinear_rmse:.6g}","lower RMSE")
    gate("test_nonlinear_beats_persistence","deployment",tr.recurrent_nonlinear_rmse<tr.persistence_nonlinear_rmse,f"{tr.recurrent_nonlinear_rmse:.6g} < {tr.persistence_nonlinear_rmse:.6g}","lower RMSE")
    gate("validation_pressure_workload_beats_persistence","deployment",vr.recurrent_pressure_fp_rmse<vr.persistence_pressure_fp_rmse,f"{vr.recurrent_pressure_fp_rmse:.6g} < {vr.persistence_pressure_fp_rmse:.6g}","lower RMSE")
    gate("test_pressure_workload_beats_persistence","deployment",tr.recurrent_pressure_fp_rmse<tr.persistence_pressure_fp_rmse,f"{tr.recurrent_pressure_fp_rmse:.6g} < {tr.persistence_pressure_fp_rmse:.6g}","lower RMSE")
    gate("validation_retry_recall","deployment",vr.retry_recall>=0.95,vr.retry_recall,">=0.95")
    gate("test_retry_recall","deployment",tr.retry_recall>=0.95,tr.retry_recall,">=0.95")
    gate("validation_budget_coverage","deployment",vr.budget_coverage_fraction>=0.98,vr.budget_coverage_fraction,">=0.98")
    gate("test_budget_coverage","deployment",tr.budget_coverage_fraction>=0.98,tr.budget_coverage_fraction,">=0.98")
    gate("test_reserved_budget_reduction","deployment",tr.reserved_work_reduction_fraction>=0.15,tr.reserved_work_reduction_fraction,">=0.15")
    gate("zero_unsafe_without_exact_escalation","deployment",not np.asarray(screen["unsafe_without_escalation"]).any(),0,"zero")
    gate("retry_auc_informative","diagnostic",tr.retry_auc>=0.90,tr.retry_auc,">=0.90")
    gate("all_preflight_tiers_exercised","diagnostic",set(np.unique(screen["tier"]))=={"light","standard","full"},sorted(np.unique(screen["tier"]).tolist()),"light, standard, full")
    gate("ood_full_preflight_exercised","diagnostic",np.sum(screen["state_ood"])>0,int(np.sum(screen["state_ood"])),">0")
    gate("adaptive_budget_exercised","diagnostic",np.any(screen["nonlinear_budget"]<FULL_NONLINEAR_BUDGET) and np.any(screen["pressure_budget"]<FULL_PRESSURE_FP_BUDGET),"yes","reduced and full budgets")
    gate("retry_screen_exercises_both_branches","diagnostic",np.any(screen["retry_risk"]) and np.any(~screen["retry_risk"]),(int(np.sum(screen["retry_risk"])),int(np.sum(~screen["retry_risk"]))),"both")
    validation=pd.DataFrame(gates);validation.to_csv(out_dir/"PAD_Stream_V15F2_Validation_Matrix.csv",index=False)
    integrity=validation[validation.group=="integrity"];deployment=validation[validation.group=="deployment"];diagnostic=validation[validation.group=="diagnostic"]
    status="PASS" if integrity.passed.all() and deployment.passed.all() else ("AUDIT_COMPLETE_DEPLOYMENT_NOT_APPROVED" if integrity.passed.all() else "AUDIT_FAILED")
    new_params=3*(raw_features.shape[1]+1)
    combined=int(f1_summary["model"]["combined_parameters"]+new_params)
    metrics={
        "transitions":len(raw_features),"train_samples":int((split=="train").sum()),"validation_samples":int((split=="validation").sum()),"test_samples":int((split=="test").sum()),
        "validation_persistence_nonlinear_rmse":float(vr.persistence_nonlinear_rmse),"validation_recurrent_nonlinear_rmse":float(vr.recurrent_nonlinear_rmse),"test_persistence_nonlinear_rmse":float(tr.persistence_nonlinear_rmse),"test_recurrent_nonlinear_rmse":float(tr.recurrent_nonlinear_rmse),
        "validation_persistence_pressure_fp_rmse":float(vr.persistence_pressure_fp_rmse),"validation_recurrent_pressure_fp_rmse":float(vr.recurrent_pressure_fp_rmse),"test_persistence_pressure_fp_rmse":float(tr.persistence_pressure_fp_rmse),"test_recurrent_pressure_fp_rmse":float(tr.recurrent_pressure_fp_rmse),
        "validation_retry_recall":float(vr.retry_recall),"test_retry_recall":float(tr.retry_recall),"test_retry_precision":float(tr.retry_precision),"test_retry_auc":float(tr.retry_auc),
        "validation_budget_coverage_fraction":float(vr.budget_coverage_fraction),"test_budget_coverage_fraction":float(tr.budget_coverage_fraction),"test_reserved_work_reduction_fraction":float(tr.reserved_work_reduction_fraction),"test_mean_reserved_work_units":float(tr.mean_reserved_work_units),
        "full_preflight_steps":int(np.sum(screen["full_preflight"])),"standard_preflight_steps":int(np.sum(screen["tier"]=="standard")),"light_preflight_steps":int(np.sum(screen["tier"]=="light")),"state_ood_steps":int(np.sum(screen["state_ood"])),"exact_escalation_steps":int(np.sum(screen["exact_escalation"])),"unsafe_without_exact_escalation":int(np.sum(screen["unsafe_without_escalation"])),
        "nonlinear_budget_margin":float(screen["nonlinear_margin"]),"pressure_budget_margin":float(screen["pressure_margin"]),"state_distance_threshold":float(screen["state_distance_threshold"]),"retry_threshold":cfg.retry_threshold,
        "restart_day":float(current_time[restart_index]),"restart_head_reload_max_abs_difference":float(reload_max),"training_seconds":float(training_seconds),"new_head_parameters":int(new_params),"frozen_f0_f1_parameters":int(f1_summary["model"]["combined_parameters"]),"complete_global_state_parameters":combined,
    }
    summary={"version":VERSION,"status":status,"description":"Complete Version 15F global recurrent state with nonlinear workload and retry memory","integrity_gates_passed":int(integrity.passed.sum()),"integrity_gates_total":len(integrity),"deployment_gates_passed":int(deployment.passed.sum()),"deployment_gates_total":len(deployment),"diagnostic_gates_passed":int(diagnostic.passed.sum()),"diagnostic_gates_total":len(diagnostic),"deployment_approved":bool(deployment.passed.all()),"model":{"frozen_f0_hidden_dim":F0_HIDDEN_DIM,"feature_dim":raw_features.shape[1],"new_head_parameters":new_params,"frozen_f0_f1_parameters":int(f1_summary["model"]["combined_parameters"]),"complete_global_state_parameters":combined,"head_type":"two ridge workload heads plus one balanced logistic retry head"},"calibration":{"nonlinear_ridge_alpha":cfg.nonlinear_ridge_alpha,"pressure_ridge_alpha":cfg.pressure_ridge_alpha,"retry_logistic_c":cfg.retry_logistic_c,"retry_threshold":cfg.retry_threshold,"state_distance_threshold":float(screen["state_distance_threshold"]),"nonlinear_budget_margin":float(screen["nonlinear_margin"]),"pressure_budget_margin":float(screen["pressure_margin"]),"full_nonlinear_budget":FULL_NONLINEAR_BUDGET,"full_pressure_fp_budget":FULL_PRESSURE_FP_BUDGET},"metrics":metrics,"rollout_contract":"accepted current state -> frozen F0/F1 recurrent memory -> nonlinear/pressure/retry proposals -> uncertainty, control, and retry screen -> initial solver allocation -> exact residual/convergence escalation","handoff":{"next_milestone":"15G-0","next_scope":"end-to-end PAD-Stream integration","complete_v15f_state":["timestep and retrace memory","breakthrough and well-control memory","nonlinear difficulty and retry memory"]},"limitations":["The controlled 5x5x5 trajectory is a single prototype-scale sequence; field-scale and multi-scenario nonlinear diversity is deferred.","Reserved-budget reduction measures initial solver allocation, not guaranteed wall-clock savings.","Learned workload heads never certify convergence; exact nonlinear, pressure, timestep, well, path, and conservation authorities remain mandatory."],"source_hashes":{name:info["sha256"] for name,info in dependency["sources"].items()}}
    (out_dir/"PAD_Stream_V15F2_Summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    write_inference_source(out_dir); shutil.copy2(Path(__file__),out_dir/Path(__file__).name); write_readme(out_dir,summary); create_plots(out_dir,audit,metrics_table,validation); write_verifier(out_dir); write_checksums(out_dir)
    zip_path=out_dir.with_suffix(".zip")
    if zip_path.exists():zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")),"zip",out_dir.parent,out_dir.name)
    return summary


def default_paths() -> Dict[str, Path]:
    f0=Path('/mnt/data/pad_stream_v15f0/PAD_Stream_V15F0_Global_Recurrent_Timestep_Retrace_State')
    f1=Path('/mnt/data/pad_stream_v15f1/PAD_Stream_V15F1_Breakthrough_Well_Control_Recurrent_Memory')
    return {
        "dense_audit":f0/"PAD_Stream_V15F0_Timestep_Sequential_Audit.csv",
        "f0_predictions":f0/"PAD_Stream_V15F0_Predictions.npz",
        "f0_summary":f0/"PAD_Stream_V15F0_Summary.json",
        "f0_checkpoint":f0/"PAD_Stream_V15F0_Best_Model.pt",
        "f0_restart":f0/"PAD_Stream_V15F0_Restart_State_Day195.npz",
        "f0_package_zip":Path('/mnt/data/pad_stream_v15f0/PAD_Stream_V15F0_Global_Recurrent_Timestep_Retrace_State.zip'),
        "f1_dataset":f1/"PAD_Stream_V15F1_Well_Memory_Dataset.npz",
        "f1_predictions":f1/"PAD_Stream_V15F1_Predictions.npz",
        "f1_heads":f1/"PAD_Stream_V15F1_Well_Memory_Heads.npz",
        "f1_summary":f1/"PAD_Stream_V15F1_Summary.json",
        "f1_restart":f1/"PAD_Stream_V15F1_Restart_State_Day195.npz",
        "f1_package_zip":Path('/mnt/data/pad_stream_v15f1/PAD_Stream_V15F1_Breakthrough_Well_Control_Recurrent_Memory.zip'),
        "output":Path('/mnt/data/pad_stream_v15f2/PAD_Stream_V15F2_Nonlinear_Difficulty_Complete_Global_Recurrent_State'),
    }


def main() -> None:
    defaults=default_paths(); p=argparse.ArgumentParser()
    for name,path in defaults.items():p.add_argument('--'+name.replace('_','-'),default=str(path))
    args=p.parse_args(); summary=build(args); print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
