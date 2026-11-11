#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

M = "POSTV16-P-CAD-A2"
NAME = "Hold-Envelope Failure-Driver Attribution + GPU BL/Hybrid-DP Targeted-Probe Protocol Freeze"
PASS = "POSTV16PCADA2_HOLD_ENVELOPE_FAILURE_DRIVER_AND_GPU_TARGETED_PROBE_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"
BLOCK = "POSTV16PCADA2_TECHNICAL_OR_AUTHORITY_BLOCK_NO_PHYSICS_EXECUTION"

BRANCH = "postv16-av4-pivot"
PARENT = "ed772c57ddca46b4c9157d179ff69328f6311014"  # P-CAD-A1
A1_RUNNER = "PAD_Stream_POSTV16_P_CAD_A1_Empirical_5Day_Envelope_and_Targeted_Early_Probe_Design_Freeze.py"
A1_RUNNER_BLOB = "908d959260102c82de503adb9727e2faa790f49b"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

A1_TOKEN = "POSTV16_P_CAD_A1"
A1_REL = BASE_AV4 / (A1_TOKEN + "_Empirical_5Day_Envelope_and_Targeted_Early_Probe_Design_Freeze")
A1_SUMMARY = f"PAD_Stream_{A1_TOKEN}_Summary.json"
A1_DECISION = f"{A1_TOKEN}_Decision_Contract.json"
A1_ENVELOPE = f"{A1_TOKEN}_Hold_Envelope_Assessment.csv"
A1_PROBES = f"{A1_TOKEN}_Targeted_Early_Probe_Design.csv"
A1_MANIFEST = f"{A1_TOKEN}_Artifact_Manifest.csv"
A1_STATUS = "POSTV16PCADA1_EMPIRICAL_5DAY_ENVELOPE_AND_TARGETED_EARLY_PROBE_DESIGN_FREEZE_PASS_NO_EXPENSIVE_EXECUTION"

HOLD_DAYS = [5, 10, 15, 20, 25, 30, 35, 40]
PRIMARY_METRICS = [
    "pressure_relative_L2",
    "flux_relative_L2",
    "tau_end_relative_L2",
    "streamline_weight_relative_L2",
    "producer_connectivity_mismatch_fraction",
    "path_RMS_displacement_ft",
]
SUPPLEMENTAL_METRICS = [
    "pressure_rmse_psi",
    "pressure_max_abs_psi",
    "path_p95_displacement_ft",
]

OUT_TOKEN = "POSTV16_P_CAD_A2"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_HoldEnvelope_FailureDriver_and_GPU_TargetedProbe_Protocol_Freeze")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
METRIC_LIMITS = f"{OUT_TOKEN}_Metric_Specific_Hold_Limits.csv"
FAILURE_MATRIX = f"{OUT_TOKEN}_Failure_Driver_Matrix.csv"
GPU_PROTOCOL = f"{OUT_TOKEN}_GPU_Targeted_Probe_Protocol.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

EPS = 1.0e-12  # numerical comparison tolerance only; not a scientific cadence tolerance

class GateError(RuntimeError):
    pass

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def verify_manifest(directory: Path, filename: str) -> dict[str, str]:
    p = directory / filename
    if not p.is_file():
        raise GateError(f"manifest_missing:{p}")
    rows = csv_rows(p)
    if not rows:
        raise GateError(f"manifest_empty:{p}")
    out: dict[str, str] = {}
    for row in rows:
        q = directory / row["file"]
        if not q.is_file():
            raise GateError(f"manifest_artifact_missing:{q.name}")
        actual = sha256(q)
        if actual != row["sha256"]:
            raise GateError(f"manifest_sha:{q.name}")
        if q.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{q.name}")
        out[q.name] = actual
    return out

def as_bool(v: str) -> bool:
    return str(v).strip().lower() == "true"

def as_float(v: str) -> float:
    x = float(v)
    if not math.isfinite(x):
        raise GateError(f"nonfinite_value:{v}")
    return x

def metric_limits(envelope_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = sorted(envelope_rows, key=lambda r: int(float(r["hold_days"])))
    if [int(float(r["hold_days"])) for r in rows] != HOLD_DAYS:
        raise GateError("hold_days_not_exact")

    limits: list[dict[str, Any]] = []
    matrix: list[dict[str, Any]] = []
    for metric in PRIMARY_METRICS + SUPPLEMENTAL_METRICS:
        strict_longest = None
        typical_longest = None
        first_strict_fail = None
        first_typical_fail = None
        strict_fail_ratio = None
        typical_fail_ratio = None
        for r in rows:
            h = int(float(r["hold_days"]))
            max_ratio = as_float(r[metric + "_max_vs_5day_max"])
            mean_ratio = as_float(r[metric + "_mean_vs_5day_max"])
            strict_pass = max_ratio <= 1.0 + EPS
            typical_pass = mean_ratio <= 1.0 + EPS
            matrix.append({
                "metric": metric,
                "hold_days": h,
                "max_change_ratio_vs_observed_5day_max": max_ratio,
                "mean_change_ratio_vs_observed_5day_max": mean_ratio,
                "strict_metric_pass": strict_pass,
                "typical_metric_pass": typical_pass,
            })
            if strict_pass:
                strict_longest = h
            elif first_strict_fail is None:
                first_strict_fail = h
                strict_fail_ratio = max_ratio
            if typical_pass:
                typical_longest = h
            elif first_typical_fail is None:
                first_typical_fail = h
                typical_fail_ratio = mean_ratio

        limits.append({
            "metric": metric,
            "metric_role": "PRIMARY" if metric in PRIMARY_METRICS else "SUPPLEMENTAL",
            "strict_longest_hold_days_with_metric_max_within_observed_5day_max": strict_longest,
            "first_strict_failure_hold_days": first_strict_fail,
            "first_strict_failure_ratio_vs_5day_max": strict_fail_ratio,
            "typical_longest_hold_days_with_metric_mean_within_observed_5day_max": typical_longest,
            "first_typical_failure_hold_days": first_typical_fail,
            "first_typical_failure_ratio_vs_5day_max": typical_fail_ratio,
        })
    return limits, matrix

def build_gpu_protocol(probe_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    ordered = sorted(probe_rows, key=lambda r: int(float(r["priority_rank"])))
    if len(ordered) != 3:
        raise GateError(f"probe_count:{len(ordered)}")
    out: list[dict[str, Any]] = []
    for r in ordered:
        rank = int(float(r["priority_rank"]))
        ws = int(float(r["screening_window_start_day"]))
        we = int(float(r["screening_window_end_day"]))
        ps = int(float(r["first_targeted_probe_start_day"]))
        pe = int(float(r["first_targeted_probe_end_day"]))
        prev_pair = [ps - 5, ps]
        next_pair = [pe, pe + 5]
        if prev_pair[0] < ws:
            prev_pair = None
        if next_pair[1] > we:
            next_pair = None
        out.append({
            "priority_rank": rank,
            "screening_window_start_day": ws,
            "screening_window_end_day": we,
            "stage_1_probe_start_day": ps,
            "stage_1_probe_end_day": pe,
            "stage_1_duration_days": 5,
            "required_reference_outputs": (
                "exact pressure; exact conservative Darcy Qx/Qy/Qz; exact Pollock paths; "
                "terminal TOF; streamline volumetric weights; producer labels; transported saturation"
            ),
            "comparison_reference": "authoritative late-time observed 5-day maximum-change envelope from Day365-Day405",
            "stage_1_pass_rule": "all PRIMARY metric changes <= corresponding observed late-time 5-day maximum",
            "stage_1_exceedance_rule": "one or more PRIMARY metrics exceed corresponding observed late-time 5-day maximum",
            "adjacent_probe_before_if_exceeded": "" if prev_pair is None else f"{prev_pair[0]}-{prev_pair[1]}",
            "adjacent_probe_after_if_exceeded": "" if next_pair is None else f"{next_pair[0]}-{next_pair[1]}",
            "adaptive_expansion_rule": (
                "If Stage-1 exceeds the empirical 5-day envelope, execute only the available immediate adjacent 5-day "
                "probe pair(s) inside the same coarse window. Do not sweep the entire window."
            ),
            "future_execution_engine": "GPU BL + Hybrid Dykstra-Parsons reference trajectory",
            "learned_pressure_seed_allowed_for_reference_truth": False,
            "exact_FV_pressure_required": True,
            "exact_Darcy_Pollock_TOF_required": True,
            "current_execution_authorized": False,
        })
    return out

def plot_metric_limits(matrix: list[dict[str, Any]], output: Path, mode: str) -> None:
    suffix = "max_change_ratio_vs_observed_5day_max" if mode == "strict" else "mean_change_ratio_vs_observed_5day_max"
    fig, ax = plt.subplots(figsize=(10, 6))
    for metric in PRIMARY_METRICS:
        rr = [r for r in matrix if r["metric"] == metric]
        x = np.asarray([r["hold_days"] for r in rr], dtype=float)
        y = np.asarray([r[suffix] for r in rr], dtype=float)
        ax.plot(x, y, marker="o", label=metric)
    ax.axhline(1.0, linestyle="--", linewidth=1.2, label="Observed 5-day max envelope")
    ax.set_xlabel("Held flow-epoch duration (days)")
    ax.set_ylabel("Change ratio relative to observed 5-day maximum")
    ax.set_title(
        "Primary metric worst-case inflation vs hold duration"
        if mode == "strict"
        else "Primary metric mean inflation vs hold duration"
    )
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)

def selftest() -> None:
    rows = []
    for h in HOLD_DAYS:
        row = {"hold_days": str(h)}
        for m in PRIMARY_METRICS + SUPPLEMENTAL_METRICS:
            row[m + "_max_vs_5day_max"] = str(h / 5.0)
            row[m + "_mean_vs_5day_max"] = str(h / 10.0)
        rows.append(row)
    limits, matrix = metric_limits(rows)
    assert len(limits) == len(PRIMARY_METRICS) + len(SUPPLEMENTAL_METRICS)
    assert len(matrix) == len(HOLD_DAYS) * (len(PRIMARY_METRICS) + len(SUPPLEMENTAL_METRICS))
    assert limits[0]["strict_longest_hold_days_with_metric_max_within_observed_5day_max"] == 5
    assert limits[0]["typical_longest_hold_days_with_metric_mean_within_observed_5day_max"] == 10
    probes = [
        {"priority_rank":"1","screening_window_start_day":"60","screening_window_end_day":"100","first_targeted_probe_start_day":"75","first_targeted_probe_end_day":"80"},
        {"priority_rank":"2","screening_window_start_day":"100","screening_window_end_day":"150","first_targeted_probe_start_day":"120","first_targeted_probe_end_day":"125"},
        {"priority_rank":"3","screening_window_start_day":"30","screening_window_end_day":"60","first_targeted_probe_start_day":"40","first_targeted_probe_end_day":"45"},
    ]
    p = build_gpu_protocol(probes)
    assert p[0]["adjacent_probe_before_if_exceeded"] == "70-75"
    assert p[0]["adjacent_probe_after_if_exceeded"] == "80-85"
    print("POSTV16 P-CAD-A2 structural/protocol self-test: PASS")

def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    a1 = drive / A1_REL
    out = drive / OUT_REL
    staging = drive / STAGE_REL
    blocked = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({"stage": stage, "gate": name, "pass": ok, "detail": "" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"), flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("=" * 180)
        print("POSTV16-P-CAD-A2 — HOLD-ENVELOPE FAILURE-DRIVER ATTRIBUTION + GPU TARGETED-PROBE PROTOCOL FREEZE")
        print("READ-ONLY DESIGN/INTERPRETATION. NO PRESSURE SOLVE. NO FLOW RECOMPUTATION. NO TRANSPORT EXECUTION.")
        print("=" * 180)

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_P_CAD_A1_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        rp = root / A1_RUNNER
        gate("A1_runner_present", rp.is_file())
        gate("A1_runner_blob_exact", gt(root, "hash-object", str(rp)) == A1_RUNNER_BLOB,
             gt(root, "hash-object", str(rp)) if rp.is_file() else "missing")

        stage = "A1_formal_authority"
        gate("A1_output_exists", a1.is_dir(), str(a1))
        for fn in [A1_SUMMARY, A1_DECISION, A1_ENVELOPE, A1_PROBES, A1_MANIFEST]:
            gate(f"A1_artifact_present:{fn}", (a1 / fn).is_file())
        verify_manifest(a1, A1_MANIFEST)
        s = js(a1 / A1_SUMMARY)
        d = js(a1 / A1_DECISION)
        gate("A1_status_exact", s.get("status") == A1_STATUS, s.get("status"))
        gate("A1_strict_longest_exact_5", s.get("strict_longest_hold_with_all_primary_maxima_within_5day_max_envelope_days") == 5)
        gate("A1_typical_longest_exact_15", s.get("typical_longest_hold_with_all_primary_means_within_5day_max_envelope_days") == 15)
        gate("A1_no_production_cadence", s.get("production_pressure_refresh_cadence_selected") is False)
        gate("A1_no_expensive_current_probes", s.get("expensive_current_recurrent_probe_execution_authorized") is False)
        gate("A1_A2_protocol_design_authorized", d.get("P_CAD_A2_GPU_targeted_probe_protocol_design_authorized") is True)
        gate("A1_expensive_A2_execution_locked", d.get("P_CAD_A2_expensive_early_probe_execution_authorized") is False)
        gate("A1_bruteforce_locked", d.get("brute_force_Day30_to_Day365_five_day_sweep_authorized") is False)
        gate("A1_Day405_to410_still_authorized", d.get("Day405_to_Day410_transport_remains_authorized_from_R7R10") is True)
        gate("A1_P4_locked", d.get("P4_authorized") is False)

        stage = "failure_driver_attribution"
        envelope = csv_rows(a1 / A1_ENVELOPE)
        limits, matrix = metric_limits(envelope)
        primary_limits = [r for r in limits if r["metric_role"] == "PRIMARY"]
        strict_first_fail_holds = [r["first_strict_failure_hold_days"] for r in primary_limits if r["first_strict_failure_hold_days"] is not None]
        typical_first_fail_holds = [r["first_typical_failure_hold_days"] for r in primary_limits if r["first_typical_failure_hold_days"] is not None]
        overall_first_strict_failure = min(strict_first_fail_holds) if strict_first_fail_holds else None
        overall_first_typical_failure = min(typical_first_fail_holds) if typical_first_fail_holds else None
        gate("overall_first_strict_failure_is_10", overall_first_strict_failure == 10, overall_first_strict_failure)
        gate("overall_first_typical_failure_is_20", overall_first_typical_failure == 20, overall_first_typical_failure)

        strict_drivers_at_10 = sorted([
            r["metric"] for r in matrix
            if r["hold_days"] == 10 and r["metric"] in PRIMARY_METRICS and not r["strict_metric_pass"]
        ])
        typical_drivers_at_20 = sorted([
            r["metric"] for r in matrix
            if r["hold_days"] == 20 and r["metric"] in PRIMARY_METRICS and not r["typical_metric_pass"]
        ])
        gate("strict_failure_driver_present_at_10", len(strict_drivers_at_10) >= 1, strict_drivers_at_10)
        gate("typical_failure_driver_present_at_20", len(typical_drivers_at_20) >= 1, typical_drivers_at_20)

        stage = "GPU_probe_protocol"
        probes = build_gpu_protocol(csv_rows(a1 / A1_PROBES))
        gate("three_GPU_probe_protocol_rows", len(probes) == 3)
        gate("all_future_exact_FV_required", all(p["exact_FV_pressure_required"] is True for p in probes))
        gate("learned_seed_not_reference_truth", all(p["learned_pressure_seed_allowed_for_reference_truth"] is False for p in probes))
        gate("current_execution_locked", all(p["current_execution_authorized"] is False for p in probes))

        stage = "publication"
        gate("output_does_not_preexist", not out.exists(), str(out))
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=False)

        write_csv(staging / METRIC_LIMITS, limits)
        write_csv(staging / FAILURE_MATRIX, matrix)
        write_csv(staging / GPU_PROTOCOL, probes)
        plot_metric_limits(matrix, staging / f"{OUT_TOKEN}_Strict_PrimaryMetric_Inflation.png", "strict")
        plot_metric_limits(matrix, staging / f"{OUT_TOKEN}_Typical_PrimaryMetric_Inflation.png", "typical")

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "repository_parent_P_CAD_A1_commit": PARENT,
            "source_A1_status": A1_STATUS,
            "source_A1_summary_sha256": sha256(a1 / A1_SUMMARY),
            "empirical_reference": "authoritative Day365-Day405 observed five-day maximum-change envelope",
            "late_time_strict_longest_hold_days": 5,
            "late_time_typical_longest_hold_days": 15,
            "late_time_first_strict_failure_hold_days": overall_first_strict_failure,
            "late_time_first_typical_failure_hold_days": overall_first_typical_failure,
            "strict_failure_drivers_at_10_days": strict_drivers_at_10,
            "typical_failure_drivers_at_20_days": typical_drivers_at_20,
            "metric_specific_hold_limits_table": METRIC_LIMITS,
            "failure_driver_matrix": FAILURE_MATRIX,
            "future_GPU_targeted_probe_protocol": GPU_PROTOCOL,
            "future_GPU_targeted_probe_pairs": [[75,80],[120,125],[40,45]],
            "future_GPU_adaptive_expansion_is_local_only": True,
            "future_GPU_reference_truth_requires_exact_FV_pressure": True,
            "future_GPU_reference_truth_requires_exact_Darcy_Pollock_TOF": True,
            "learned_pressure_seed_can_define_reference_truth": False,
            "production_pressure_refresh_cadence_selected": False,
            "late_time_evidence_bracket_not_production_cadence": [5, 15],
            "brute_force_Day30_to_Day365_five_day_sweep_authorized": False,
            "expensive_current_recurrent_early_probe_execution_authorized": False,
            "GPU_BL_HybridDP_probe_execution_authorized_now": False,
            "new_pressure_solves_executed": False,
            "Darcy_recomputation_executed": False,
            "Pollock_retracing_executed": False,
            "TOF_recomputation_executed": False,
            "transport_execution_executed": False,
            "authoritative_physics_state_mutated": False,
            "Day405_to_Day410_transport_executed": False,
            "Day405_to_Day410_transport_remains_authorized": True,
            "P4_authorized": False,
            "recommended_next_action": (
                "Use the A2 failure-driver attribution to determine which physical observable controls cadence. "
                "Preserve the ranked early target pairs for execution only when the GPU BL+Hybrid-DP early reference "
                "trajectory is available. Resume AV4 Day405-to-Day410 only if additional late-time trajectory coverage "
                "is desired; do not use that expensive segment as a substitute for the targeted early cadence probes."
            ),
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "production_pressure_refresh_cadence_selected": False,
            "late_time_evidence_bracket_days": [5, 15],
            "P_CAD_A3_GPU_targeted_probe_execution_authorized": False,
            "P_CAD_A3_GPU_targeted_probe_execution_protocol_frozen": True,
            "brute_force_Day30_to_Day365_five_day_sweep_authorized": False,
            "expensive_current_recurrent_early_probe_execution_authorized": False,
            "Day405_to_Day410_transport_remains_authorized_from_R7R10": True,
            "Day405_to_Day410_transport_executed": False,
            "P4_authorized": False,
            "recommended_next_action": summary["recommended_next_action"],
        }

        (staging / SUMMARY).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (staging / DECISION).write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        manifest_rows = []
        for p in sorted(staging.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                manifest_rows.append({"file": p.name, "sha256": sha256(p), "bytes": p.stat().st_size})
        write_csv(staging / MANIFEST, manifest_rows)
        staging.rename(out)

        print("=" * 180)
        print(M, "PASS")
        print("Late-time strict longest hold (days)      :", 5)
        print("Late-time typical longest hold (days)     :", 15)
        print("First strict failure hold (days)          :", overall_first_strict_failure)
        print("Strict failure drivers at 10 days         :", strict_drivers_at_10)
        print("First typical failure hold (days)         :", overall_first_typical_failure)
        print("Typical failure drivers at 20 days        :", typical_drivers_at_20)
        print("Future GPU targeted pairs                 :", [[75,80],[120,125],[40,45]])
        print("GPU probe execution authorized now        : False")
        print("Production cadence selected               : False")
        print("Day405->Day410 remains authorized         : True")
        print("P4 authorized                             : False")
        print("Output directory                          :", out)
        print("=" * 180)
        return 0

    except Exception as exc:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        blocked.mkdir(parents=True, exist_ok=True)
        (blocked / f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone": M,
            "status": BLOCK,
            "failed_stage": stage,
            "exception": repr(exc),
            "transport_execution_executed": False,
            "authoritative_physics_state_mutated": False,
            "P4_authorized": False,
            "gates_completed": gates,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
