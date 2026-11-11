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

M = "POSTV16-P-CAD-A1"
NAME = "Empirical 5-Day Hold-Error Envelope + Targeted Early-Probe Design Freeze"
PASS = "POSTV16PCADA1_EMPIRICAL_5DAY_ENVELOPE_AND_TARGETED_EARLY_PROBE_DESIGN_FREEZE_PASS_NO_EXPENSIVE_EXECUTION"
BLOCK = "POSTV16PCADA1_TECHNICAL_OR_AUTHORITY_BLOCK_NO_PHYSICS_MUTATION"

BRANCH = "postv16-av4-pivot"
PARENT = "da688945054f6c909e199b5444dd51252b45e058"  # P-CAD-A0
A0_RUNNER = "PAD_Stream_POSTV16_P_CAD_A0_Exact_Pressure_Evolution_and_FlowEpoch_Hold_Screening.py"
A0_RUNNER_BLOB = "ce56b4742e941e89444ca463e7bc583a506a6389"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

A0_TOKEN = "POSTV16_P_CAD_A0"
A0_REL = BASE_AV4 / (A0_TOKEN + "_Exact_Pressure_Evolution_and_FlowEpoch_Hold_Screening")
A0_SUMMARY = f"PAD_Stream_{A0_TOKEN}_Summary.json"
A0_DECISION = f"{A0_TOKEN}_Decision_Contract.json"
A0_HOLD_SUMMARY = f"{A0_TOKEN}_Hold_Duration_Summary.csv"
A0_HOLD_PAIRWISE = f"{A0_TOKEN}_Hold_Duration_Pairwise.csv"
A0_EARLY_PRIORITY = f"{A0_TOKEN}_Early_Probe_Priority.csv"
A0_MANIFEST = f"{A0_TOKEN}_Artifact_Manifest.csv"
A0_STATUS = "POSTV16PCADA0_EXACT_PRESSURE_EVOLUTION_AND_FLOWEPOCH_HOLD_SCREENING_PASS_NO_PHYSICS_MUTATION"
A0_CLASS = "P_CAD_A0_AV5_EARLY_PRESSURE_SCREENING_NOT_FORMALLY_CONTIGUOUS_WITH_AV4_DAY365_TRAJECTORY_LATE_HOLD_SCREENING_COMPLETE_TARGETED_EARLY_PROBE_DESIGN_REQUIRED"

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
EXPECTED_TOP3 = [(60, 100), (100, 150), (30, 60)]

OUT_TOKEN = "POSTV16_P_CAD_A1"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_Empirical_5Day_Envelope_and_Targeted_Early_Probe_Design_Freeze")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
ENVELOPE = f"{OUT_TOKEN}_Hold_Envelope_Assessment.csv"
PROBES = f"{OUT_TOKEN}_Targeted_Early_Probe_Design.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

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
    rows = csv_rows(directory / filename)
    if not rows:
        raise GateError("A0_manifest_empty")
    out: dict[str, str] = {}
    for row in rows:
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"A0_manifest_missing:{p.name}")
        actual = sha256(p)
        if actual != row["sha256"]:
            raise GateError(f"A0_manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"A0_manifest_bytes:{p.name}")
        out[p.name] = actual
    return out

def finite_float(row: dict[str, str], key: str) -> float:
    v = float(row[key])
    if not math.isfinite(v):
        raise GateError(f"nonfinite:{key}:{v}")
    return v

def inflation(value: float, baseline: float) -> float:
    if baseline == 0.0:
        return 1.0 if value == 0.0 else float("inf")
    return value / baseline

def empirical_envelope(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], int | None, int | None]:
    by_hold = {int(float(r["hold_days"])): r for r in rows}
    if sorted(by_hold) != HOLD_DAYS:
        raise GateError(f"hold_days:{sorted(by_hold)}")
    base = by_hold[5]
    out: list[dict[str, Any]] = []
    strict_longest = None
    typical_longest = None
    for h in HOLD_DAYS:
        r = by_hold[h]
        item: dict[str, Any] = {"hold_days": h, "pair_count": int(float(r["pair_count"]))}
        strict = True
        typical = True
        worst_max_infl = 1.0
        worst_mean_infl = 1.0
        worst_max_metric = ""
        worst_mean_metric = ""
        for metric in PRIMARY_METRICS + SUPPLEMENTAL_METRICS:
            bmax = finite_float(base, metric + "_max")
            bmean = finite_float(base, metric + "_mean")
            vmax = finite_float(r, metric + "_max")
            vmean = finite_float(r, metric + "_mean")
            rimax = inflation(vmax, bmax)
            rimean = inflation(vmean, bmax)  # typical compared to observed 5-day worst case
            item[metric + "_max_vs_5day_max"] = rimax
            item[metric + "_mean_vs_5day_max"] = rimean
            if metric in PRIMARY_METRICS:
                if vmax > bmax * (1.0 + 1e-12) + 1e-15:
                    strict = False
                if vmean > bmax * (1.0 + 1e-12) + 1e-15:
                    typical = False
                if rimax > worst_max_infl:
                    worst_max_infl, worst_max_metric = rimax, metric
                if rimean > worst_mean_infl:
                    worst_mean_infl, worst_mean_metric = rimean, metric
        item["strict_all_primary_max_within_observed_5day_max_envelope"] = strict
        item["typical_all_primary_mean_within_observed_5day_max_envelope"] = typical
        item["worst_primary_max_inflation_vs_5day_max"] = worst_max_infl
        item["worst_primary_max_inflation_metric"] = worst_max_metric
        item["worst_primary_mean_inflation_vs_5day_max"] = worst_mean_infl
        item["worst_primary_mean_inflation_metric"] = worst_mean_metric
        out.append(item)
        if strict:
            strict_longest = h
        if typical:
            typical_longest = h
    return out, strict_longest, typical_longest

def make_probe_design(priority: list[dict[str, str]]) -> list[dict[str, Any]]:
    ordered = sorted(priority, key=lambda r: int(float(r["priority_rank_by_relative_L2_rate"])))
    top3 = [(int(float(r["start_day"])), int(float(r["end_day"]))) for r in ordered[:3]]
    if top3 != EXPECTED_TOP3:
        raise GateError(f"unexpected_top3:{top3}")
    rows: list[dict[str, Any]] = []
    for rank, (a, b) in enumerate(top3, start=1):
        midpoint = 0.5 * (a + b)
        probe_end = int(5 * round(midpoint / 5))
        probe_end = max(a + 5, min(probe_end, b))
        probe_start = probe_end - 5
        rows.append({
            "priority_rank": rank,
            "screening_window_start_day": a,
            "screening_window_end_day": b,
            "screening_window_days": b - a,
            "first_targeted_probe_start_day": probe_start,
            "first_targeted_probe_end_day": probe_end,
            "probe_duration_days": 5,
            "selection_rule": "single centered 5-day probe inside ranked coarse window",
            "formal_AV4_restart_state_currently_available": False,
            "current_expensive_probe_execution_authorized": False,
            "planned_execution_context": "future GPU BL+Hybrid-DP early reference trajectory with exact pressure/flow diagnostics",
            "adaptive_expansion_rule": (
                "Only add adjacent 5-day probes inside this coarse window if the first targeted probe "
                "exceeds the empirically observed late-time 5-day flow-epoch change envelope in one or more primary metrics."
            ),
        })
    return rows

def plot_inflation(rows: list[dict[str, Any]], key: str, title: str, output: Path) -> None:
    x = np.asarray([r["hold_days"] for r in rows], dtype=np.float64)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for metric in PRIMARY_METRICS:
        y = np.asarray([float(r[metric + key]) for r in rows], dtype=np.float64)
        finite = np.isfinite(y)
        if np.any(finite):
            ax.plot(x[finite], y[finite], marker="o", label=metric)
    ax.axhline(1.0, linewidth=1.0, linestyle="--", label="Observed 5-day max envelope")
    ax.set_xlabel("Held flow-epoch duration (days)")
    ax.set_ylabel("Inflation relative to observed 5-day maximum")
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)

def selftest() -> None:
    synthetic = []
    for h in HOLD_DAYS:
        r = {"hold_days": h, "pair_count": 9 - h // 5}
        scale = h / 5.0
        for metric in PRIMARY_METRICS + SUPPLEMENTAL_METRICS:
            r[metric + "_mean"] = 0.5 * scale
            r[metric + "_max"] = 1.0 * scale
        synthetic.append({k: str(v) for k, v in r.items()})
    out, strict, typical = empirical_envelope(synthetic)
    assert len(out) == 8 and strict == 5 and typical == 10
    priority = [
        {"start_day":"60","end_day":"100","priority_rank_by_relative_L2_rate":"1"},
        {"start_day":"100","end_day":"150","priority_rank_by_relative_L2_rate":"2"},
        {"start_day":"30","end_day":"60","priority_rank_by_relative_L2_rate":"3"},
    ]
    probes = make_probe_design(priority)
    assert [(p["first_targeted_probe_start_day"], p["first_targeted_probe_end_day"]) for p in probes] == [(75,80),(120,125),(40,45)]
    print("POSTV16 P-CAD-A1 structural/decision self-test: PASS")

def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    a0 = drive / A0_REL
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
        print("=" * 170)
        print("POSTV16-P-CAD-A1 — EMPIRICAL 5-DAY ENVELOPE + TARGETED EARLY-PROBE DESIGN FREEZE")
        print("READ-ONLY DECISION/DESIGN ONLY. NO NEW PRESSURE SOLVE. NO DARCY/POLLOCK/TOF RECOMPUTATION. NO TRANSPORT EXECUTION.")
        print("=" * 170)

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_P_CAD_A0_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        runner_path = root / A0_RUNNER
        gate("A0_runner_present", runner_path.is_file(), str(runner_path))
        gate("A0_runner_blob_exact", gt(root, "hash-object", str(runner_path)) == A0_RUNNER_BLOB,
             gt(root, "hash-object", str(runner_path)) if runner_path.is_file() else "missing")

        stage = "A0_formal_authority"
        gate("A0_output_exists", a0.is_dir(), str(a0))
        for fn in [A0_SUMMARY, A0_DECISION, A0_HOLD_SUMMARY, A0_HOLD_PAIRWISE, A0_EARLY_PRIORITY, A0_MANIFEST]:
            gate(f"A0_artifact_present:{fn}", (a0 / fn).is_file())
        manifest = verify_manifest(a0, A0_MANIFEST)
        s = js(a0 / A0_SUMMARY)
        d = js(a0 / A0_DECISION)
        gate("A0_status_exact", s.get("status") == A0_STATUS, s.get("status"))
        gate("A0_classification_exact", s.get("classification") == A0_CLASS, s.get("classification"))
        gate("A0_formal_splice_false", s.get("formal_Day30_to_Day405_pressure_splice_authorized") is False)
        gate("A0_cadence_not_selected", s.get("production_pressure_refresh_cadence_selected") is False)
        gate("A0_tolerance_not_defined", s.get("cadence_error_tolerance_defined") is False)
        gate("A0_A1_design_authorized", d.get("P_CAD_A1_targeted_early_probe_design_authorized") is True)
        gate("A0_expensive_probe_execution_locked", d.get("P_CAD_A1_expensive_probe_execution_authorized") is False)
        gate("A0_bruteforce_locked", d.get("brute_force_Day30_to_Day365_five_day_sweep_authorized") is False)
        gate("A0_Day405_to410_still_authorized", d.get("Day405_to_Day410_transport_remains_authorized_from_R7R10") is True)
        gate("A0_P4_locked", d.get("P4_authorized") is False)

        stage = "empirical_5day_envelope"
        hold_rows = csv_rows(a0 / A0_HOLD_SUMMARY)
        assessment, strict_longest, typical_longest = empirical_envelope(hold_rows)
        gate("eight_hold_durations_assessed", len(assessment) == 8)
        gate("five_day_strict_baseline_pass", assessment[0]["strict_all_primary_max_within_observed_5day_max_envelope"] is True)

        stage = "targeted_early_probe_design"
        priority = csv_rows(a0 / A0_EARLY_PRIORITY)
        probes = make_probe_design(priority)
        gate("three_probe_windows_frozen", len(probes) == 3)
        gate("no_current_restart_claim", all(p["formal_AV4_restart_state_currently_available"] is False for p in probes))
        gate("no_expensive_execution_authority", all(p["current_expensive_probe_execution_authorized"] is False for p in probes))

        stage = "publication"
        gate("output_does_not_preexist", not out.exists(), str(out))
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=False)
        write_csv(staging / ENVELOPE, assessment)
        write_csv(staging / PROBES, probes)
        plot_inflation(assessment, "_max_vs_5day_max",
                       "Worst-case hold-error inflation relative to observed 5-day envelope",
                       staging / f"{OUT_TOKEN}_WorstCase_Error_Inflation_vs_Hold.png")
        plot_inflation(assessment, "_mean_vs_5day_max",
                       "Typical hold-error inflation relative to observed 5-day worst-case envelope",
                       staging / f"{OUT_TOKEN}_Typical_Error_Inflation_vs_Hold.png")

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "repository_parent_P_CAD_A0_commit": PARENT,
            "source_A0_status": A0_STATUS,
            "source_A0_classification": A0_CLASS,
            "source_A0_summary_sha256": sha256(a0 / A0_SUMMARY),
            "source_A0_hold_summary_sha256": sha256(a0 / A0_HOLD_SUMMARY),
            "formal_Day30_to_Day405_pressure_splice_authorized": False,
            "empirical_reference_envelope": "maximum observed change over authoritative Day365-to-Day405 5-day pairs",
            "primary_metrics": PRIMARY_METRICS,
            "strict_longest_hold_with_all_primary_maxima_within_5day_max_envelope_days": strict_longest,
            "typical_longest_hold_with_all_primary_means_within_5day_max_envelope_days": typical_longest,
            "targeted_early_probe_windows_ranked": [
                {"rank": p["priority_rank"], "window": [p["screening_window_start_day"], p["screening_window_end_day"]],
                 "first_centered_5day_probe": [p["first_targeted_probe_start_day"], p["first_targeted_probe_end_day"]]}
                for p in probes
            ],
            "early_probe_restart_states_currently_available": False,
            "expensive_current_recurrent_probe_execution_authorized": False,
            "future_targeted_probe_execution_context": "GPU BL+Hybrid-DP early reference trajectory with exact pressure/flow diagnostics",
            "production_pressure_refresh_cadence_selected": False,
            "absolute_numeric_cadence_tolerance_invented": False,
            "brute_force_Day30_to_Day365_five_day_sweep_authorized": False,
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
                "Use the A1 empirical envelope to identify which late-time hold durations are scientifically plausible. "
                "Do not execute the ranked early probes with the current expensive recurrent transport. Preserve the three "
                "ranked probe windows as targets for the future GPU BL+Hybrid-DP early reference trajectory, where exact "
                "pressure/flow diagnostics can be sampled at the frozen 5-day probe pairs with far lower compute cost."
            ),
        }
        decision = {
            "milestone": M,
            "status": PASS,
            "production_pressure_refresh_cadence_selected": False,
            "P_CAD_A2_expensive_early_probe_execution_authorized": False,
            "P_CAD_A2_GPU_targeted_probe_protocol_design_authorized": True,
            "brute_force_Day30_to_Day365_five_day_sweep_authorized": False,
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

        print("=" * 170)
        print(M, "PASS")
        print("Strict longest hold within observed 5-day max envelope :", strict_longest)
        print("Typical longest hold within observed 5-day max envelope:", typical_longest)
        print("Ranked early probe targets                              :",
              [(p["first_targeted_probe_start_day"], p["first_targeted_probe_end_day"]) for p in probes])
        print("Expensive early probes executed                         : False")
        print("Production cadence selected                             : False")
        print("Day405->Day410 remains authorized                       : True")
        print("P4 authorized                                           : False")
        print("Output directory                                        :", out)
        print("=" * 170)
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
