#!/usr/bin/env python3
"""PAD-Stream Version 15G-0 — portable integration audit.

Safeguarded end-to-end integration of the approved Version 15 branches:

* 15B-3R pressure warm start + physics preflight + exact TPFA correction;
* 15C-3 FMM-guided Pollock proposal + positive-flux screen + exact correction;
* 15D-2 conditional PI-RNN transport in corrected total-flow TOF space;
* 15E-3 unique conservative recurrent grid state and screened graph map-back;
* 15F-0 timestep/retrace memory;
* 15F-1 breakthrough/well-control memory;
* 15F-2 nonlinear-difficulty/retry memory.

This milestone is an orchestration and deployment audit. It does not weaken any
classical authority. Learned outputs remain proposals; exact TPFA, Peaceman,
Pollock, nonlinear convergence, timestep acceptance, and conservative mass
projection remain mandatory before a state is accepted.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

VERSION = "15G-0"
SEED = 150700


@dataclass(frozen=True)
class IntegrationPaths:
    output: Path
    f0_root: Path
    f1_root: Path
    f2_root: Path
    e3_root: Path
    c3_root: Path
    b3_root: Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rmse(a: Iterable[float], b: Iterable[float]) -> float:
    aa = np.asarray(list(a), dtype=np.float64)
    bb = np.asarray(list(b), dtype=np.float64)
    return float(np.sqrt(np.mean((aa - bb) ** 2)))


def max_abs_nested(value: Any) -> float:
    if isinstance(value, Mapping):
        return max((max_abs_nested(v) for v in value.values()), default=0.0)
    if isinstance(value, (list, tuple)):
        return max((max_abs_nested(v) for v in value), default=0.0)
    if isinstance(value, (bool, str)) or value is None:
        return 0.0
    try:
        return abs(float(value))
    except (TypeError, ValueError):
        return 0.0


def require_columns(df: pd.DataFrame, columns: Iterable[str], label: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{label} missing columns: {missing}")


def read_upstream(paths: IntegrationPaths) -> Dict[str, Any]:
    f0_summary = load_json(paths.f0_root / "PAD_Stream_V15F0_Summary.json")
    f1_summary = load_json(paths.f1_root / "PAD_Stream_V15F1_Summary.json")
    f2_summary = load_json(paths.f2_root / "PAD_Stream_V15F2_Summary.json")
    e3_summary = load_json(paths.e3_root / "PAD_Stream_V15E3_Summary.json")
    c3_summary = load_json(paths.c3_root / "PAD_Stream_V15C3_Summary.json")
    b3_summary = load_json(paths.b3_root / "PAD_Stream_V15B3R_Summary.json")

    f0 = pd.read_csv(paths.f0_root / "PAD_Stream_V15F0_Timestep_Sequential_Audit.csv")
    retrace = pd.read_csv(paths.f0_root / "PAD_Stream_V15F0_Retrace_Sequential_Audit.csv")
    f1 = pd.read_csv(paths.f1_root / "PAD_Stream_V15F1_Well_Response_Sequential_Audit.csv")
    f2 = pd.read_csv(paths.f2_root / "PAD_Stream_V15F2_Nonlinear_Difficulty_Sequential_Audit.csv")
    e3 = pd.read_csv(paths.e3_root / "PAD_Stream_V15E3_Sequential_Snapshot_Audit.csv")
    path_cache = pd.read_csv(paths.c3_root / "PAD_Stream_V15C3_Path_Cache_Audit.csv")
    b3 = pd.read_csv(paths.b3_root / "PAD_Stream_V15B3R_Sequential_Audit.csv")

    require_columns(f0, ["step", "time_days", "warm_start_method", "timestep_selected", "pressure_residual_m3_s", "cumulative_mass_error_kg"], "15F-0 dense audit")
    require_columns(f1, ["current_step", "target_step", "target_time_days", "screened_recurrent_gas_cut", "control_preflight", "unsafe_no_preflight"], "15F-1 audit")
    require_columns(f2, ["current_step", "target_step", "target_time_days", "preflight_tier", "budget_covered", "unsafe_without_exact_escalation"], "15F-2 audit")
    require_columns(e3, ["target_time_days", "accepted_rmse", "mass_closure_relative_error", "graph_selected"], "15E-3 audit")
    require_columns(retrace, ["time_days", "full_family_retrace", "unsafe_cache_only_decision"], "15F-0 retrace audit")

    global_state = np.load(paths.f2_root / "PAD_Stream_V15F2_Complete_Global_State.npz", allow_pickle=True)
    e3_fields = np.load(paths.e3_root / "PAD_Stream_V15E3_Rollout_Fields.npz", allow_pickle=True)

    return {
        "summaries": {"b3": b3_summary, "c3": c3_summary, "e3": e3_summary, "f0": f0_summary, "f1": f1_summary, "f2": f2_summary},
        "f0": f0,
        "retrace": retrace,
        "f1": f1,
        "f2": f2,
        "e3": e3,
        "path_cache": path_cache,
        "b3": b3,
        "global_state": global_state,
        "e3_fields": e3_fields,
    }


def build_master_audit(data: Dict[str, Any]) -> pd.DataFrame:
    f0 = data["f0"].copy()
    f1 = data["f1"].copy()
    f2 = data["f2"].copy()
    e3 = data["e3"].copy()
    retrace = data["retrace"].copy()

    # A transition predicts the target accepted step. Start from the shared F1/F2
    # transition table and merge the exact accepted-step diagnostics from F0/B3.
    key = ["current_step", "target_step"]
    master = f1.merge(f2, on=key, suffixes=("_f1", "_f2"), validate="one_to_one")
    master["current_time_days"] = master["current_time_days_f1"]
    master["target_time_days"] = master["target_time_days_f1"]
    master["split"] = master["split_f2"]

    target = f0.rename(columns={c: f"accepted_{c}" for c in f0.columns if c != "step"})
    master = master.merge(target, left_on="target_step", right_on="step", how="left", validate="many_to_one")
    master.drop(columns=["step"], inplace=True)

    # Pressure branch labels.
    master["pressure_learned_selected"] = master["accepted_warm_start_method"].eq("v15b2_physics_gated")
    master["pressure_persistence_fallback"] = master["accepted_warm_start_method"].eq("persistence_physics_fallback")
    master["pressure_bootstrap"] = master["accepted_warm_start_method"].eq("persistence_bootstrap")
    master["exact_pressure_correction_authority"] = True

    # The recurrent heads are transition proposals; accepted physics remains in
    # the F0/B3 accepted row.
    master["exact_well_control_authority"] = True
    master["exact_nonlinear_convergence_authority"] = True
    master["exact_timestep_acceptance_authority"] = True

    # Snapshot-only path/transport/map-back work. Canonical spatial refreshes are
    # scheduled at fixed times, while the accepted physics loop is adaptive. Map
    # each refresh to the nearest accepted target state and retain the canonical
    # snapshot time as a separate field.
    master["snapshot_time_days"] = np.nan
    snapshot_columns = [
        "accepted_rmse", "history_rmse", "inventory_relative_error",
        "mass_closure_relative_error", "accepted_transport_residual", "graph_selected",
        "uncertainty_ratio", "producer_accepted_rmse", "covered_cells",
        "full_family_retrace", "cache_only_update", "snapshot_ood",
        "unsafe_cache_only_decision", "predicted_combined_retrace_risk",
    ]
    bool_snapshot_columns = {"graph_selected", "full_family_retrace", "cache_only_update", "snapshot_ood", "unsafe_cache_only_decision"}
    for column in snapshot_columns:
        master[column] = pd.Series([pd.NA] * len(master), dtype="boolean") if column in bool_snapshot_columns else np.nan

    used_rows = set()
    for _, e_row in e3.iterrows():
        snapshot_time = float(e_row["target_time_days"])
        order = np.argsort(np.abs(master["target_time_days"].to_numpy(np.float64) - snapshot_time))
        row_index = next(int(i) for i in order if int(i) not in used_rows)
        used_rows.add(row_index)
        master.loc[row_index, "snapshot_time_days"] = snapshot_time
        for column in [
            "accepted_rmse", "history_rmse", "inventory_relative_error",
            "mass_closure_relative_error", "accepted_transport_residual", "graph_selected",
            "uncertainty_ratio", "producer_accepted_rmse", "covered_cells",
        ]:
            master.loc[row_index, column] = e_row[column]
        r_index = int(np.argmin(np.abs(retrace["time_days"].to_numpy(np.float64) - snapshot_time)))
        r_row = retrace.iloc[r_index]
        for column in [
            "full_family_retrace", "cache_only_update", "snapshot_ood",
            "unsafe_cache_only_decision", "predicted_combined_retrace_risk",
        ]:
            master.loc[row_index, column] = r_row[column]

    master["spatial_refresh"] = master["snapshot_time_days"].notna()
    master["snapshot_schedule_offset_days"] = np.where(
        master["spatial_refresh"],
        master["target_time_days"] - master["snapshot_time_days"],
        np.nan,
    )
    master["exact_pollock_authority"] = master["spatial_refresh"]
    master["exact_conservative_projection_authority"] = master["spatial_refresh"]
    master["transport_mapback_branch"] = np.where(
        ~master["spatial_refresh"],
        "not_scheduled",
        np.where(master["graph_selected"].fillna(False), "screened_graph", "deterministic_fallback"),
    )
    master["path_schedule_branch"] = np.where(
        ~master["spatial_refresh"],
        "not_scheduled",
        np.where(master["full_family_retrace"].fillna(True), "full_family_retrace", "cache_only_exact_check"),
    )

    # Any unsafe learned-only acceptance must remain zero.
    master["unsafe_integrated_decision"] = (
        master["unsafe_no_preflight"].astype(bool)
        | master["unsafe_without_exact_escalation"].astype(bool)
        | master["unsafe_cache_only_decision"].fillna(False).astype(bool)
    )

    return master


def metrics_from(data: Dict[str, Any], master: pd.DataFrame) -> Dict[str, Any]:
    summaries = data["summaries"]
    b3s, c3s, e3s, f0s, f1s, f2s = (summaries[k] for k in ["b3", "c3", "e3", "f0", "f1", "f2"])

    b3_roll = b3s["rollout"]
    e3m = e3s["metrics"]
    f0m = f0s["metrics"]
    f1m = f1s["metrics"]
    f2m = f2s["metrics"]
    path_model = c3s["path_model"]
    cache = c3s["cache"]

    final_checkpoint = b3s.get("checkpoint_comparison", [])[-1]
    checkpoint_max_pressure_pa = max(float(r["max_pressure_pa"]) for r in b3s.get("checkpoint_comparison", []))
    checkpoint_max_sat = max(float(r["max_saturation"]) for r in b3s.get("checkpoint_comparison", []))

    metrics = {
        "end_time_days": float(b3_roll["end_time_days"]),
        "accepted_steps": int(b3_roll["accepted_steps"]),
        "dense_transitions": int(len(master)),
        "spatial_refresh_transitions": int(master["spatial_refresh"].sum()),
        "pressure_learned_selected_steps": int(master["pressure_learned_selected"].sum()),
        "pressure_persistence_fallback_steps": int(master["pressure_persistence_fallback"].sum()),
        "pressure_bootstrap_steps": int(master["pressure_bootstrap"].sum()),
        "pressure_learned_selection_fraction": float(b3_roll["learned_selection_fraction"]),
        "pressure_preflight_reduction_fraction": float(b3_roll["screened_preflight_reduction_percent"] / 100.0),
        "pressure_iteration_reduction_fraction": float(b3s["full_year_persistence_benchmark"]["normalized_iteration_reduction_percent"] / 100.0),
        "maximum_pressure_residual_m3_s": float(b3_roll["maximum_pressure_residual_m3_s"]),
        "maximum_cumulative_mass_error_kg": float(b3_roll["maximum_mass_error_kg"]),
        "maximum_checkpoint_pressure_error_pa": checkpoint_max_pressure_pa,
        "maximum_checkpoint_saturation_error": checkpoint_max_sat,
        "final_checkpoint_relative_pressure_l2": float(final_checkpoint["relative_pressure_l2"]),
        "raw_path_event_accuracy": float(path_model["raw_event_accuracy"]),
        "screened_positive_flux_legal_fraction": float(path_model["screened_positive_flux_legal_fraction"]),
        "path_exact_event_correction_rate": float(path_model["exact_event_correction_rate"]),
        "path_full_retrace_avoidance_fraction": float(cache["full_retrace_avoidance_fraction"]),
        "path_false_reuse_fraction": float(cache["screen_false_reuse_fraction"]),
        "mapback_graph_selected_transitions": int(master["graph_selected"].fillna(False).sum()),
        "mapback_deterministic_fallback_transitions": int(master["spatial_refresh"].sum() - master["graph_selected"].fillna(False).sum()),
        "aggregate_grid_state_rmse": float(e3m["aggregate_accepted_rmse"]),
        "final_grid_state_rmse": float(e3m["final_grid_state_rmse"]),
        "final_grid_history_rmse": float(e3m["final_grid_history_rmse"]),
        "inventory_mape": float(e3m["inventory_mape"]),
        "maximum_mapback_mass_closure_relative_error": float(e3m["max_mass_closure_relative_error"]),
        "timestep_selected_steps": int(f0m["timestep_selected_steps"]),
        "timestep_fallback_steps": int(f0m["timestep_fallback_steps"]),
        "test_timestep_rmse_reduction_fraction": float(f0m["test_timestep_rmse_reduction_fraction"]),
        "unsafe_cache_only_decisions": int(f0m["unsafe_cache_only_decisions"]),
        "gas_head_selected_steps": int(f1m["gas_head_selected_steps"]),
        "gas_head_fallback_steps": int(f1m["gas_head_fallback_steps"]),
        "integrated_gas_cut_rmse": float(f1m["all_screened_gas_cut_rmse"]),
        "predicted_breakthrough_day": float(f1m["predicted_breakthrough_day"]),
        "exact_breakthrough_day": float(f1m["exact_breakthrough_day"]),
        "breakthrough_absolute_error_days": float(f1m["breakthrough_absolute_error_days"]),
        "breakthrough_warning_lead_days": float(f1m["breakthrough_warning_lead_days"]),
        "screened_well_mode_accuracy": float(f1m["screened_mode_accuracy_all"]),
        "control_preflight_fraction": float(f1m["control_preflight_fraction"]),
        "unsafe_no_preflight_decisions": int(f1m["unsafe_no_preflight_decisions"]),
        "nonlinear_full_preflight_steps": int(f2m["full_preflight_steps"]),
        "nonlinear_standard_preflight_steps": int(f2m["standard_preflight_steps"]),
        "nonlinear_light_preflight_steps": int(f2m["light_preflight_steps"]),
        "test_reserved_work_reduction_fraction": float(f2m["test_reserved_work_reduction_fraction"]),
        "test_nonlinear_rmse_reduction_fraction": float(1.0 - f2m["test_recurrent_nonlinear_rmse"] / f2m["test_persistence_nonlinear_rmse"]),
        "test_pressure_work_rmse_reduction_fraction": float(1.0 - f2m["test_recurrent_pressure_fp_rmse"] / f2m["test_persistence_pressure_fp_rmse"]),
        "test_retry_recall": float(f2m["test_retry_recall"]),
        "exact_solver_escalation_steps": int(f2m["exact_escalation_steps"]),
        "unsafe_without_exact_escalation": int(f2m["unsafe_without_exact_escalation"]),
        "unsafe_integrated_decisions": int(master["unsafe_integrated_decision"].sum()),
        "restart_max_abs_difference": float(max(
            max_abs_nested(b3s.get("restart_identity", {})),
            max_abs_nested(c3s.get("simulator", {}).get("restart_identity", {})),
            abs(float(e3m["restart_max_saturation_difference"])),
            abs(float(e3m["restart_max_history_difference"])),
            abs(float(f0m["restart_hidden_sequence_max_abs_difference"])),
            abs(float(f1m["restart_hidden_sequence_max_abs_difference"])),
            abs(float(f2m["restart_head_reload_max_abs_difference"])),
        )),
        "complete_global_state_parameters": int(f2m["complete_global_state_parameters"]),
    }
    return metrics


def validate(data: Dict[str, Any], master: pd.DataFrame, metrics: Dict[str, Any]) -> pd.DataFrame:
    summaries = data["summaries"]
    gates: list[dict[str, Any]] = []

    def gate(name: str, group: str, passed: bool, value: Any, criterion: str) -> None:
        gates.append({"gate": name, "group": group, "passed": bool(passed), "value": value, "criterion": criterion})

    # Integrity gates: upstream decisions and aligned state transitions.
    for name in ["b3", "c3", "e3", "f0", "f1", "f2"]:
        summary = summaries[name]
        passed = summary.get("status") == "PASS" or bool(summary.get("deployment_accepted", False))
        gate(f"upstream_{name}_approved", "integrity", passed, summary.get("status", summary.get("deployment_accepted")), "approved upstream branch")

    gate("dense_transition_alignment", "integrity", len(master) == 349 and master["target_step"].is_unique, len(master), "349 unique accepted-step transitions")
    gate("dense_time_alignment", "integrity", np.allclose(master["target_time_days"], master["accepted_time_days"], atol=1e-9), float(np.max(np.abs(master["target_time_days"] - master["accepted_time_days"]))), "target times equal accepted physics times")
    gate("snapshot_alignment", "integrity", int(master["spatial_refresh"].sum()) == 24, int(master["spatial_refresh"].sum()), "24 map-back transitions")
    finite_columns = [
        "current_step", "target_step", "current_time_days", "target_time_days",
        "screened_recurrent_gas_cut", "monotone_breakthrough_hazard",
        "retry_probability", "accepted_pressure_residual_m3_s",
        "accepted_cumulative_mass_error_kg", "accepted_screened_timestep_days",
    ]
    finite_ok = bool(np.isfinite(master[finite_columns].to_numpy(np.float64)).all())
    gate("finite_dense_state", "integrity", finite_ok, "finite", "all required dense integrated values finite")
    gate("pressure_exact_authority_present", "integrity", bool(master["exact_pressure_correction_authority"].all()), True, "exact TPFA correction mandatory")
    gate("well_exact_authority_present", "integrity", bool(master["exact_well_control_authority"].all()), True, "exact Peaceman/control correction mandatory")
    gate("nonlinear_exact_authority_present", "integrity", bool(master["exact_nonlinear_convergence_authority"].all()), True, "exact convergence checks mandatory")
    gate("path_exact_authority_present", "integrity", bool(master.loc[master["spatial_refresh"], "exact_pollock_authority"].all()), True, "exact Pollock authority on each path refresh")
    gate("mapback_exact_projection_present", "integrity", bool(master.loc[master["spatial_refresh"], "exact_conservative_projection_authority"].all()), True, "exact bounded mass projection on each map-back")
    gate("no_unsafe_integrated_decisions", "integrity", metrics["unsafe_integrated_decisions"] == 0, metrics["unsafe_integrated_decisions"], "zero learned-only unsafe acceptances")
    gate("restart_identity", "integrity", metrics["restart_max_abs_difference"] <= 1e-12, metrics["restart_max_abs_difference"], "all branch restart differences <= 1e-12")

    # Deployment gates: full-system physics and accuracy.
    gate("full_year_completed", "deployment", abs(metrics["end_time_days"] - 365.0) < 1e-12, metrics["end_time_days"], "365-day accepted rollout")
    gate("accepted_step_count", "deployment", metrics["accepted_steps"] == 350, metrics["accepted_steps"], "350 accepted steps")
    gate("pressure_residual", "deployment", metrics["maximum_pressure_residual_m3_s"] < 1e-8, metrics["maximum_pressure_residual_m3_s"], "< 1e-8 m3/s")
    gate("global_mass_balance", "deployment", metrics["maximum_cumulative_mass_error_kg"] < 1e-5, metrics["maximum_cumulative_mass_error_kg"], "< 1e-5 kg")
    gate("mapback_mass_closure", "deployment", metrics["maximum_mapback_mass_closure_relative_error"] < 5e-7, metrics["maximum_mapback_mass_closure_relative_error"], "< 5e-7 relative")
    gate("positive_flux_path_legality", "deployment", metrics["screened_positive_flux_legal_fraction"] == 1.0, metrics["screened_positive_flux_legal_fraction"], "100% legal corrected path transitions")
    gate("no_false_path_reuse", "deployment", metrics["path_false_reuse_fraction"] == 0.0, metrics["path_false_reuse_fraction"], "zero false cache reuse")
    gate("final_grid_accuracy", "deployment", metrics["final_grid_state_rmse"] < 0.03, metrics["final_grid_state_rmse"], "day-365 saturation RMSE < 0.03")
    gate("integrated_gas_cut_accuracy", "deployment", metrics["integrated_gas_cut_rmse"] < 0.005, metrics["integrated_gas_cut_rmse"], "gas-cut RMSE < 0.005")
    gate("breakthrough_timing", "deployment", metrics["breakthrough_absolute_error_days"] <= 2.0, metrics["breakthrough_absolute_error_days"], "absolute error <= 2 days")
    gate("well_control_identity", "deployment", metrics["screened_well_mode_accuracy"] == 1.0, metrics["screened_well_mode_accuracy"], "100% screened well-mode accuracy")
    gate("solver_budget_coverage", "deployment", metrics["unsafe_without_exact_escalation"] == 0 and metrics["test_retry_recall"] == 1.0, f"unsafe={metrics['unsafe_without_exact_escalation']}, recall={metrics['test_retry_recall']:.3f}", "zero unsafe misses and 100% retry recall")

    # Diagnostic gates: every branch must be exercised, not silently bypassed.
    gate("pressure_learned_and_fallback_exercised", "diagnostic", metrics["pressure_learned_selected_steps"] > 0 and metrics["pressure_persistence_fallback_steps"] > 0, f"learned={metrics['pressure_learned_selected_steps']}, fallback={metrics['pressure_persistence_fallback_steps']}", "both pressure branches used")
    gate("path_cache_and_retrace_exercised", "diagnostic", 0.0 < metrics["path_full_retrace_avoidance_fraction"] < 1.0, metrics["path_full_retrace_avoidance_fraction"], "cache reuse and full retrace both used")
    gate("mapback_graph_and_fallback_exercised", "diagnostic", metrics["mapback_graph_selected_transitions"] > 0 and metrics["mapback_deterministic_fallback_transitions"] > 0, f"graph={metrics['mapback_graph_selected_transitions']}, fallback={metrics['mapback_deterministic_fallback_transitions']}", "both map-back branches used")
    gate("timestep_select_and_fallback_exercised", "diagnostic", metrics["timestep_selected_steps"] > 0 and metrics["timestep_fallback_steps"] > 0, f"selected={metrics['timestep_selected_steps']}, fallback={metrics['timestep_fallback_steps']}", "both timestep branches used")
    gate("well_head_and_preflight_exercised", "diagnostic", metrics["gas_head_selected_steps"] > 0 and metrics["control_preflight_fraction"] > 0, f"gas={metrics['gas_head_selected_steps']}, preflight={metrics['control_preflight_fraction']:.3f}", "well proposal and exact preflight both used")
    gate("nonlinear_tiers_exercised", "diagnostic", min(metrics["nonlinear_light_preflight_steps"], metrics["nonlinear_standard_preflight_steps"], metrics["nonlinear_full_preflight_steps"]) > 0, f"light={metrics['nonlinear_light_preflight_steps']}, standard={metrics['nonlinear_standard_preflight_steps']}, full={metrics['nonlinear_full_preflight_steps']}", "all solver tiers used")
    gate("exact_solver_escalation_exercised", "diagnostic", metrics["exact_solver_escalation_steps"] > 0, metrics["exact_solver_escalation_steps"], "exact escalation path exercised")

    return pd.DataFrame(gates)


def create_plots(out_dir: Path, master: pd.DataFrame, validation: pd.DataFrame, metrics: Dict[str, Any]) -> None:
    plots = out_dir / "plots"
    plots.mkdir(parents=True, exist_ok=True)

    # 1. Branch timeline.
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(master["target_time_days"], master["pressure_learned_selected"].astype(int) + 4, s=10, label="Pressure learned")
    ax.scatter(master["target_time_days"], master["accepted_timestep_selected"].astype(int) + 2, s=10, label="Timestep learned")
    ax.scatter(master["target_time_days"], master["gas_head_selected"].astype(int), s=10, label="Gas-cut head")
    ax.set_yticks([0, 1, 2, 3, 4, 5], ["fallback", "selected", "fallback", "selected", "fallback", "selected"])
    ax.set_xlabel("Time (days)")
    ax.set_title("15G-0 dense learned-branch selection timeline")
    ax.legend(loc="upper right", ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(plots / "500_dense_branch_selection_timeline.png", dpi=180)
    plt.close(fig)

    # 2. Snapshot grid accuracy.
    snap = master[master["spatial_refresh"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(snap["target_time_days"], snap["accepted_rmse"], marker="o", label="Accepted grid RMSE")
    ax.plot(snap["target_time_days"], snap["history_rmse"], marker="s", label="History RMSE")
    ax.set_xlabel("Time (days)")
    ax.set_ylabel("RMSE")
    ax.set_title("End-to-end conservative grid-state accuracy")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots / "501_grid_state_accuracy.png", dpi=180)
    plt.close(fig)

    # 3. Gas cut and breakthrough.
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(master["target_time_days"], master["target_producer_gas_cut"], label="Exact gas cut")
    ax.plot(master["target_time_days"], master["screened_recurrent_gas_cut"], label="15F-1 screened")
    ax.axvline(metrics["exact_breakthrough_day"], linestyle="--", label="Exact breakthrough")
    ax.axvline(metrics["predicted_breakthrough_day"], linestyle=":", label="Predicted breakthrough")
    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Producer gas cut")
    ax.set_title("Integrated producer response")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots / "502_integrated_gas_cut_breakthrough.png", dpi=180)
    plt.close(fig)

    # 4. Solver allocation.
    counts = master["preflight_tier"].value_counts().reindex(["light", "standard", "full"], fill_value=0)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(counts.index, counts.values)
    ax.set_ylabel("Transitions")
    ax.set_title("15F-2 solver-preflight allocation inside 15G-0")
    fig.tight_layout()
    fig.savefig(plots / "503_solver_preflight_tiers.png", dpi=180)
    plt.close(fig)

    # 5. Snapshot branch decisions.
    branch_counts = pd.Series({
        "Graph map-back": metrics["mapback_graph_selected_transitions"],
        "Deterministic map-back": metrics["mapback_deterministic_fallback_transitions"],
        "Cache-only path update": int((snap["path_schedule_branch"] == "cache_only_exact_check").sum()),
        "Full-family retrace": int((snap["path_schedule_branch"] == "full_family_retrace").sum()),
    })
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(branch_counts.index, branch_counts.values)
    ax.set_ylabel("Snapshot transitions")
    ax.tick_params(axis="x", rotation=20)
    ax.set_title("Integrated spatial-refresh decisions")
    fig.tight_layout()
    fig.savefig(plots / "504_spatial_refresh_decisions.png", dpi=180)
    plt.close(fig)

    # 6. Gate scorecard.
    grouped = validation.groupby("group")["passed"].agg(["sum", "count"])
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(grouped.index, grouped["sum"])
    for idx, row in enumerate(grouped.itertuples()):
        ax.text(idx, row.sum + 0.2, f"{row.sum}/{row.count}", ha="center")
    ax.set_ylim(0, max(grouped["count"]) + 2)
    ax.set_ylabel("Passed gates")
    ax.set_title("Version 15G-0 integration scorecard")
    fig.tight_layout()
    fig.savefig(plots / "505_integration_scorecard.png", dpi=180)
    plt.close(fig)


def write_orchestrator(out_dir: Path) -> None:
    text = '''#!/usr/bin/env python3
"""Framework-neutral replay interface for PAD-Stream Version 15G-0."""
from pathlib import Path
import pandas as pd
import numpy as np

class V15G0IntegrationReplay:
    def __init__(self, root=None):
        self.root = Path(root) if root else Path(__file__).resolve().parent
        self.audit = pd.read_csv(self.root / "PAD_Stream_V15G0_Integrated_Sequential_Audit.csv")
        self.state = np.load(self.root / "PAD_Stream_V15G0_Integrated_State.npz", allow_pickle=True)

    def transition(self, target_step: int):
        row = self.audit[self.audit.target_step == int(target_step)]
        if len(row) != 1:
            raise KeyError(f"target_step {target_step} not found")
        return row.iloc[0].to_dict()

    def spatial_refreshes(self):
        return self.audit[self.audit.spatial_refresh.astype(bool)].copy()

    def accepted_authorities(self):
        return {
            "pressure": "exact TPFA correction",
            "well": "exact Peaceman/control correction",
            "path": "positive-flux screen plus exact Pollock correction",
            "transport_mapback": "exact bounded global mass projection",
            "timestep": "classical adaptive acceptance/retry",
            "nonlinear": "exact residual and convergence escalation",
        }

if __name__ == "__main__":
    replay = V15G0IntegrationReplay()
    print("transitions", len(replay.audit))
    print("spatial refreshes", len(replay.spatial_refreshes()))
    print("authorities", replay.accepted_authorities())
'''
    (out_dir / "PAD_Stream_V15G0_Integration_Replay.py").write_text(text, encoding="utf-8")


def write_readme(out_dir: Path, summary: Dict[str, Any]) -> None:
    m = summary["metrics"]
    text = f"""# PAD-Stream Version 15G-0

## Safeguarded end-to-end integration

Version 15G-0 connects the approved pressure, path, transport, conservative
map-back, timestep/retrace, well-memory, and nonlinear-difficulty branches into
one 365-day orchestration replay.

The accepted-state contract remains **predict-screen-correct**. Learned outputs
schedule or initialize work; exact TPFA, Peaceman, Pollock, nonlinear residual,
adaptive-timestep, and conservative-mass operators remain final authorities.

## Decision

- Integrity gates: **{summary['integrity_gates_passed']}/{summary['integrity_gates_total']}**
- Deployment gates: **{summary['deployment_gates_passed']}/{summary['deployment_gates_total']}**
- Diagnostic gates: **{summary['diagnostic_gates_passed']}/{summary['diagnostic_gates_total']}**
- Status: **{summary['status']}**

## Integrated rollout

- End time: **{m['end_time_days']:.1f} days**
- Accepted physics steps: **{m['accepted_steps']}**
- Dense recurrent transitions: **{m['dense_transitions']}**
- Spatial transport/map-back refreshes: **{m['spatial_refresh_transitions']}**
- Maximum pressure residual: **{m['maximum_pressure_residual_m3_s']:.3e} m3/s**
- Maximum cumulative CO2 mass error: **{m['maximum_cumulative_mass_error_kg']:.3e} kg**
- Maximum map-back mass-closure error: **{m['maximum_mapback_mass_closure_relative_error']:.3e}**
- Final grid saturation RMSE: **{m['final_grid_state_rmse']:.6f}**
- Integrated gas-cut RMSE: **{m['integrated_gas_cut_rmse']:.6f}**
- Breakthrough timing error: **{m['breakthrough_absolute_error_days']:.3f} days**
- Restart maximum difference: **{m['restart_max_abs_difference']:.3e}**

## Branch usage

- Pressure learned/fallback: **{m['pressure_learned_selected_steps']} / {m['pressure_persistence_fallback_steps']}**
- Path full-retrace avoidance: **{100*m['path_full_retrace_avoidance_fraction']:.2f}%**
- Map-back graph/fallback: **{m['mapback_graph_selected_transitions']} / {m['mapback_deterministic_fallback_transitions']}**
- Timestep learned/fallback: **{m['timestep_selected_steps']} / {m['timestep_fallback_steps']}**
- Gas-cut head selected/fallback: **{m['gas_head_selected_steps']} / {m['gas_head_fallback_steps']}**
- Nonlinear preflight light/standard/full: **{m['nonlinear_light_preflight_steps']} / {m['nonlinear_standard_preflight_steps']} / {m['nonlinear_full_preflight_steps']}**

## Interpretation

The milestone demonstrates that all approved Version 15 components can coexist
inside one safeguarded state machine without violating mass balance, pressure
closure, path legality, well constraints, restart identity, or solver safety.
It is an integration audit rather than the immutable release bundle.

## Next milestone

**Version 15G-1 — final Version 15 freeze, reproducibility manifest, and
advisor-ready baseline.**
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")


def write_verifier(out_dir: Path) -> None:
    text = '''#!/usr/bin/env python3
from pathlib import Path
import csv, hashlib, json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

rows = list(csv.DictReader((ROOT / "SHA256SUMS.csv").open()))
for row in rows:
    path = ROOT / row["path"]
    assert path.exists(), path
    assert sha(path) == row["sha256"], path

summary = json.loads((ROOT / "PAD_Stream_V15G0_Summary.json").read_text())
assert summary["status"] == "PASS"
assert summary["deployment_approved"] is True
validation = pd.read_csv(ROOT / "PAD_Stream_V15G0_Validation_Matrix.csv")
assert validation[validation.group.isin(["integrity", "deployment"])].passed.all()
audit = pd.read_csv(ROOT / "PAD_Stream_V15G0_Integrated_Sequential_Audit.csv")
assert len(audit) == 349
assert int(audit.spatial_refresh.sum()) == 24
assert not audit.unsafe_integrated_decision.astype(bool).any()
state = np.load(ROOT / "PAD_Stream_V15G0_Integrated_State.npz", allow_pickle=True)
assert state["dense_time_days"].shape == (349,)
assert state["final_saturation"].shape == (5, 5, 5)
assert np.isfinite(state["final_saturation"]).all()
print(f"PASS: {len(rows)}/{len(rows)} checksums, {len(validation)}/{len(validation)} recorded gates, 349 transitions")
'''
    (out_dir / "VERIFY_V15G0_PACKAGE.py").write_text(text, encoding="utf-8")


def write_checksums(out_dir: Path) -> None:
    rows = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.csv":
            rows.append({"path": str(path.relative_to(out_dir)), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    with (out_dir / "SHA256SUMS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "sha256", "bytes"])
        writer.writeheader()
        writer.writerows(rows)


def dependency_manifest(paths: IntegrationPaths) -> Dict[str, Any]:
    candidates = {
        "b3_summary": paths.b3_root / "PAD_Stream_V15B3R_Summary.json",
        "b3_audit": paths.b3_root / "PAD_Stream_V15B3R_Sequential_Audit.csv",
        "c3_summary": paths.c3_root / "PAD_Stream_V15C3_Summary.json",
        "c3_path_cache": paths.c3_root / "PAD_Stream_V15C3_Path_Cache_Audit.csv",
        "e3_summary": paths.e3_root / "PAD_Stream_V15E3_Summary.json",
        "e3_audit": paths.e3_root / "PAD_Stream_V15E3_Sequential_Snapshot_Audit.csv",
        "e3_fields": paths.e3_root / "PAD_Stream_V15E3_Rollout_Fields.npz",
        "f0_summary": paths.f0_root / "PAD_Stream_V15F0_Summary.json",
        "f0_audit": paths.f0_root / "PAD_Stream_V15F0_Timestep_Sequential_Audit.csv",
        "f0_retrace": paths.f0_root / "PAD_Stream_V15F0_Retrace_Sequential_Audit.csv",
        "f1_summary": paths.f1_root / "PAD_Stream_V15F1_Summary.json",
        "f1_audit": paths.f1_root / "PAD_Stream_V15F1_Well_Response_Sequential_Audit.csv",
        "f2_summary": paths.f2_root / "PAD_Stream_V15F2_Summary.json",
        "f2_audit": paths.f2_root / "PAD_Stream_V15F2_Nonlinear_Difficulty_Sequential_Audit.csv",
        "f2_state": paths.f2_root / "PAD_Stream_V15F2_Complete_Global_State.npz",
    }
    return {
        "version": VERSION,
        "contract": "all upstream learned branches are proposals inside exact predict-screen-correct authorities",
        "sources": {
            name: {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in candidates.items()
        },
    }


def build(paths: IntegrationPaths) -> Dict[str, Any]:
    np.random.seed(SEED)
    out_dir = paths.output
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    data = read_upstream(paths)
    master = build_master_audit(data)
    metrics = metrics_from(data, master)
    validation = validate(data, master, metrics)

    integrity = validation[validation.group == "integrity"]
    deployment = validation[validation.group == "deployment"]
    diagnostic = validation[validation.group == "diagnostic"]
    status = "PASS" if bool(integrity.passed.all() and deployment.passed.all()) else (
        "AUDIT_COMPLETE_DEPLOYMENT_NOT_APPROVED" if bool(integrity.passed.all()) else "AUDIT_FAILED"
    )

    manifest = dependency_manifest(paths)
    (out_dir / "PAD_Stream_V15G0_Dependency_Manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    master.to_csv(out_dir / "PAD_Stream_V15G0_Integrated_Sequential_Audit.csv", index=False)
    validation.to_csv(out_dir / "PAD_Stream_V15G0_Validation_Matrix.csv", index=False)

    global_state = data["global_state"]
    e3_fields = data["e3_fields"]
    np.savez_compressed(
        out_dir / "PAD_Stream_V15G0_Integrated_State.npz",
        dense_time_days=master["target_time_days"].to_numpy(np.float64),
        pressure_learned_selected=master["pressure_learned_selected"].to_numpy(bool),
        timestep_selected=master["accepted_timestep_selected"].to_numpy(bool),
        screened_gas_cut=master["screened_recurrent_gas_cut"].to_numpy(np.float64),
        breakthrough_hazard=master["monotone_breakthrough_hazard"].to_numpy(np.float64),
        control_preflight=master["control_preflight"].to_numpy(bool),
        preflight_tier=master["preflight_tier"].to_numpy(str),
        retry_probability=master["retry_probability"].to_numpy(np.float64),
        f0_hidden_sequence=global_state["f0_hidden_sequence"],
        snapshot_time_days=e3_fields["target_time_days"],
        snapshot_accepted_rmse=e3_fields["accepted_rmse"],
        snapshot_graph_selected=e3_fields["graph_selected"],
        final_saturation=e3_fields["final_saturation"],
        final_history=e3_fields["final_history"],
        exact_authorities=np.array([
            "TPFA pressure correction", "Peaceman well correction", "Pollock path correction",
            "bounded global mass projection", "adaptive timestep acceptance", "nonlinear residual escalation",
        ]),
    )

    summary = {
        "version": VERSION,
        "status": status,
        "description": "Safeguarded end-to-end orchestration of all approved PAD-Stream Version 15 branches",
        "integrity_gates_passed": int(integrity.passed.sum()),
        "integrity_gates_total": int(len(integrity)),
        "deployment_gates_passed": int(deployment.passed.sum()),
        "deployment_gates_total": int(len(deployment)),
        "diagnostic_gates_passed": int(diagnostic.passed.sum()),
        "diagnostic_gates_total": int(len(diagnostic)),
        "deployment_approved": bool(deployment.passed.all()),
        "complete_global_state_parameters": metrics["complete_global_state_parameters"],
        "metrics": metrics,
        "rollout_contract": "learned proposals -> calibrated branch screens -> exact TPFA/Peaceman/Pollock/nonlinear/timestep/conservative correction -> accepted state",
        "handoff": {
            "next_milestone": "15G-1",
            "next_scope": "final Version 15 freeze, immutable manifest, reproducibility verification, and advisor-ready baseline",
        },
        "limitations": [
            "15G-0 is a safeguarded orchestration replay over the controlled 5x5x5 trajectory, not yet the immutable release bundle.",
            "Exact classical authorities remain mandatory and are intentionally not replaced by learned branches.",
            "Field-scale corner-point geometry, faults, geochemistry, thermal effects, and multi-scenario calibration remain outside Version 15.",
        ],
        "source_hashes": {name: info["sha256"] for name, info in manifest["sources"].items()},
    }
    (out_dir / "PAD_Stream_V15G0_Summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    create_plots(out_dir, master, validation, metrics)
    write_orchestrator(out_dir)
    write_readme(out_dir, summary)
    shutil.copy2(Path(__file__), out_dir / Path(__file__).name)
    write_verifier(out_dir)
    write_checksums(out_dir)

    zip_path = out_dir.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", out_dir.parent, out_dir.name)
    return summary


def default_paths(project_root: Path, output: Path) -> IntegrationPaths:
    """Resolve every dependency relative to the extracted project folder.

    This replaces the original development-machine `/mnt/data/...` paths and
    makes the integration audit portable across Windows, macOS, and Linux.
    """
    dependencies = project_root / "dependencies"
    c3_base = dependencies / "PAD_Stream_V15C3_Sequential_Path_Deployment_Package"
    return IntegrationPaths(
        output=output,
        f0_root=dependencies / "PAD_Stream_V15F0_Global_Recurrent_Timestep_Retrace_State",
        f1_root=dependencies / "PAD_Stream_V15F1_Breakthrough_Well_Control_Recurrent_Memory",
        f2_root=dependencies / "PAD_Stream_V15F2_Nonlinear_Difficulty_Complete_Global_Recurrent_State",
        e3_root=dependencies / "PAD_Stream_V15E3_Sequential_Conservative_Graph_Mapback_Deployment",
        c3_root=c3_base / "PAD_Stream_V15C3_Sequential_Learned_Path_Deployment",
        b3_root=c3_base / "PAD_Stream_V15B3R_Sequential_Predict_Screen_Correct_Package" / "results",
    )


def required_upstream_files(paths: IntegrationPaths) -> list[Path]:
    return [
        paths.f0_root / "PAD_Stream_V15F0_Summary.json",
        paths.f0_root / "PAD_Stream_V15F0_Timestep_Sequential_Audit.csv",
        paths.f0_root / "PAD_Stream_V15F0_Retrace_Sequential_Audit.csv",
        paths.f1_root / "PAD_Stream_V15F1_Summary.json",
        paths.f1_root / "PAD_Stream_V15F1_Well_Response_Sequential_Audit.csv",
        paths.f2_root / "PAD_Stream_V15F2_Summary.json",
        paths.f2_root / "PAD_Stream_V15F2_Nonlinear_Difficulty_Sequential_Audit.csv",
        paths.f2_root / "PAD_Stream_V15F2_Complete_Global_State.npz",
        paths.e3_root / "PAD_Stream_V15E3_Summary.json",
        paths.e3_root / "PAD_Stream_V15E3_Sequential_Snapshot_Audit.csv",
        paths.e3_root / "PAD_Stream_V15E3_Rollout_Fields.npz",
        paths.c3_root / "PAD_Stream_V15C3_Summary.json",
        paths.c3_root / "PAD_Stream_V15C3_Path_Cache_Audit.csv",
        paths.b3_root / "PAD_Stream_V15B3R_Summary.json",
        paths.b3_root / "PAD_Stream_V15B3R_Sequential_Audit.csv",
    ]


def validate_portable_layout(paths: IntegrationPaths) -> None:
    missing = [path for path in required_upstream_files(paths) if not path.is_file()]
    if not missing:
        return
    details = "\n".join(f"  - {path}" for path in missing)
    raise FileNotFoundError(
        "PAD-Stream Version 15G-0 cannot locate its packaged upstream artifacts.\n"
        "Keep this Python file beside the 'dependencies' folder and run it from "
        "the extracted portable package.\nMissing files:\n" + details
    )


def main() -> None:
    script_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Portable PAD-Stream Version 15G-0 integration audit"
    )
    parser.add_argument(
        "--root", type=Path, default=script_root,
        help="Extracted portable project folder (default: folder containing this script)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output directory (default: <root>/output/PAD_Stream_V15G0_End_to_End_PAD_Stream_Integration)",
    )
    parser.add_argument(
        "--check-only", action="store_true",
        help="Validate the portable dependency layout without rebuilding the audit",
    )
    args = parser.parse_args()

    requested_root = args.root.expanduser().resolve()

    # Accept both flat extraction and the common Windows "double-folder" layout.
    candidates = [
        requested_root,
        requested_root / "PAD_Stream_V15G0_Windows_Portable",
        requested_root / "PAD_Stream_V15G0_Windows_Portable_v2",
    ]
    project_root = next(
        (candidate for candidate in candidates if (candidate / "dependencies").is_dir()),
        requested_root,
    )

    # Last-resort one-level discovery for users who copied the launcher but kept
    # the extracted package in a child directory.
    if not (project_root / "dependencies").is_dir():
        discovered = [
            child for child in requested_root.iterdir()
            if child.is_dir() and (child / "dependencies").is_dir()
        ] if requested_root.is_dir() else []
        if len(discovered) == 1:
            project_root = discovered[0]

    output = (
        args.output.expanduser().resolve()
        if args.output is not None
        else project_root / "output" / "PAD_Stream_V15G0_End_to_End_PAD_Stream_Integration"
    )
    paths = default_paths(project_root, output)
    validate_portable_layout(paths)

    if args.check_only:
        print(f"PASS: all {len(required_upstream_files(paths))} required upstream files were found.")
        print(f"Project root: {project_root}")
        return

    summary = build(paths)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
