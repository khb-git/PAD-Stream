from __future__ import annotations

from pathlib import Path
import argparse
import csv
import importlib.util
import json

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output" / "V15_SG7B10R"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SG7B10_SOURCE = ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"
DEFAULT_WORKSPACE = ROOT.parent / f"{ROOT.name}_SG5C_seed_11x11"
FROZEN_MODEL_FILE = ROOT / "output" / "V15_SG7B7R" / "V15SG7B_FROZEN_Model.keras"
E2_MODEL_FILE = ROOT / "output" / "V15_SG7B10" / "experiments" / "E2" / "V15SG7B10_E2_Best_Model.keras"
SG7B10_SUMMARY = ROOT / "output" / "V15_SG7B10" / "PAD_Stream_V15SG7B10_Summary.json"
SG7B10_METRICS = ROOT / "output" / "V15_SG7B10" / "V15SG7B10_Experiment_Metrics.csv"

SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG7B10R_Summary.json"
GLOBAL_TABLE = OUTPUT_DIR / "V15SG7B10R_Monotonicity_Global.csv"
TOLERANCE_TABLE = OUTPUT_DIR / "V15SG7B10R_Tolerance_Sensitivity.csv"
AMPLITUDE_TABLE = OUTPUT_DIR / "V15SG7B10R_Violation_Amplitude.csv"
PROFILE_TABLE = OUTPUT_DIR / "V15SG7B10R_Profile_Monotonicity.csv"
DATABASE_FILE = OUTPUT_DIR / "V15SG7B10R_Monotonicity_Audit.npz"

REFERENCE_GATE = 0.020
TOLERANCE_SWEEP = np.asarray(
    [0.0, 1e-6, 1e-5, 5e-5, 1e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2],
    dtype=np.float64,
)

AMPLITUDE_BINS = [
    ("0_to_1e-5", 0.0, 1e-5),
    ("1e-5_to_1e-4", 1e-5, 1e-4),
    ("1e-4_to_5e-4", 1e-4, 5e-4),
    ("5e-4_to_1e-3", 5e-4, 1e-3),
    ("1e-3_to_5e-3", 1e-3, 5e-3),
    ("5e-3_to_1e-2", 5e-3, 1e-2),
    ("gt_1e-2", 1e-2, None),
]

def load_module(path: Path, name: str):
    if not path.exists():
        raise FileNotFoundError(f"Missing source module:\n{path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import source module:\n{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV:\n{path}")
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

def save_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

def build_front_pair_mask(truth, front_high, crossing_low):
    left = truth[:, :-1]
    right = truth[:, 1:]
    return ((np.minimum(left, right) <= float(front_high))
            & (np.maximum(left, right) >= float(crossing_low)))

def monotonic_diagnostics(prediction, local_mask, tol):
    prediction = np.asarray(prediction, dtype=np.float64)
    dS = prediction[:, 1:] - prediction[:, :-1]
    values = dS[local_mask]
    positive = values[values > float(tol)]
    if values.size == 0:
        return dict(
            eligible_pairs=0, violation_pairs=0, violation_fraction=0.0,
            positive_dS_mean=0.0, positive_dS_median=0.0,
            positive_dS_p90=0.0, positive_dS_p95=0.0,
            positive_dS_p99=0.0, positive_dS_max=0.0,
            signed_dS_mean=0.0, abs_dS_mean=0.0
        )
    return {
        "eligible_pairs": int(values.size),
        "violation_pairs": int(positive.size),
        "violation_fraction": float(positive.size / values.size),
        "positive_dS_mean": float(np.mean(positive)) if positive.size else 0.0,
        "positive_dS_median": float(np.median(positive)) if positive.size else 0.0,
        "positive_dS_p90": float(np.percentile(positive, 90)) if positive.size else 0.0,
        "positive_dS_p95": float(np.percentile(positive, 95)) if positive.size else 0.0,
        "positive_dS_p99": float(np.percentile(positive, 99)) if positive.size else 0.0,
        "positive_dS_max": float(np.max(positive)) if positive.size else 0.0,
        "signed_dS_mean": float(np.mean(values)),
        "abs_dS_mean": float(np.mean(np.abs(values))),
    }

def truth_orientation_diagnostics(truth, local_mask, tol):
    dS = np.asarray(truth, dtype=np.float64)[:, 1:] - np.asarray(truth, dtype=np.float64)[:, :-1]
    values = dS[local_mask]
    if values.size == 0:
        return dict(
            positive_fraction=0.0, negative_fraction=0.0,
            near_zero_fraction=0.0, signed_dS_mean=0.0, median_dS=0.0
        )
    positive = values > tol
    negative = values < -tol
    near_zero = ~(positive | negative)
    return {
        "positive_fraction": float(np.mean(positive)),
        "negative_fraction": float(np.mean(negative)),
        "near_zero_fraction": float(np.mean(near_zero)),
        "signed_dS_mean": float(np.mean(values)),
        "median_dS": float(np.median(values)),
    }

def profile_level_metrics(prediction, truth, local_mask, tol):
    dS = np.asarray(prediction, dtype=np.float64)[:, 1:] - np.asarray(prediction, dtype=np.float64)[:, :-1]
    eligible = np.sum(local_mask, axis=1)
    violations = np.sum(local_mask & (dS > tol), axis=1)
    frac = np.zeros(len(prediction), dtype=np.float64)
    valid = eligible > 0
    frac[valid] = violations[valid] / eligible[valid]
    l1 = np.mean(np.abs(np.asarray(prediction) - np.asarray(truth)), axis=1)
    return eligible, violations, frac, l1

def amplitude_rows(name, prediction, local_mask, tol):
    dS = np.asarray(prediction, dtype=np.float64)[:, 1:] - np.asarray(prediction, dtype=np.float64)[:, :-1]
    positive = dS[local_mask]
    positive = positive[positive > tol]
    total = max(int(positive.size), 1)
    rows = []
    for label, low, high in AMPLITUDE_BINS:
        if high is None:
            count = int(np.sum(positive > low))
        else:
            count = int(np.sum((positive > low) & (positive <= high)))
        rows.append({
            "field": name,
            "amplitude_bin": label,
            "lower_exclusive": float(low),
            "upper_inclusive": "" if high is None else float(high),
            "count": count,
            "fraction_of_violations": float(count / total) if positive.size else 0.0,
        })
    return rows

def main():
    parser = argparse.ArgumentParser(
        description="PAD-Stream V15-SG7B-10R monotonicity/outcome audit."
    )
    parser.add_argument("--workspace", type=str, default=str(DEFAULT_WORKSPACE))
    args = parser.parse_args()

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7B-10R")
    print("Front-Aware Refinement Outcome / Monotonicity Audit")
    print("=" * 78)
    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO MODEL PARAMETERS WILL BE CHANGED.")
    print("NO MONOTONICITY GATE WILL BE CHANGED.")
    print("NO CANDIDATE WILL BE PROMOTED.")
    print("NO SG7B-7R FREEZE GATE WILL BE RELAXED.")

    for path in [SG7B10_SOURCE, FROZEN_MODEL_FILE, E2_MODEL_FILE, SG7B10_SUMMARY, SG7B10_METRICS]:
        if not path.exists():
            raise FileNotFoundError(f"Missing SG7B-10R prerequisite:\n{path}")

    sg10_summary = load_json(SG7B10_SUMMARY)
    if sg10_summary.get("milestone") != "V15-SG7B-10":
        raise RuntimeError("Unexpected SG7B-10 summary identity.")

    metrics_rows = load_csv(SG7B10_METRICS)
    e2_row = next((r for r in metrics_rows if r.get("experiment") == "E2"), None)
    if e2_row is None:
        raise RuntimeError("SG7B-10 experiment table does not contain E2.")

    sg10 = load_module(SG7B10_SOURCE, "pad_stream_sg7b10_source")
    base = sg10.load_base_module()
    dataset = base.load_dataset()
    tD_scale = float(dataset["tD_scale"][0])
    workspace = Path(args.workspace).resolve()
    deployment = sg10.load_deployment_database(workspace, tD_scale)

    print("\nSOURCE CONTRACT")
    print(f"  SG7B-10 source          : {SG7B10_SOURCE.name}")
    print(f"  Frozen model            : {FROZEN_MODEL_FILE.name}")
    print(f"  E2 best model           : {E2_MODEL_FILE.name}")
    print(f"  Deployment streamlines  : {len(deployment['X100']):,}")
    print(f"  Sequence nodes          : {len(deployment['xi'])}")
    print(f"  SG7B-10 monotonic tol   : {float(sg10.MONOTONIC_TOL):.1e}")
    print(f"  SG7B-9 reference gate   : {100.0 * REFERENCE_GATE:.3f}%")

    frozen_model = sg10.tf.keras.models.load_model(FROZEN_MODEL_FILE)
    e2_model = sg10.tf.keras.models.load_model(E2_MODEL_FILE)

    frozen = frozen_model.predict(deployment["X100"], batch_size=sg10.BATCH_SIZE, verbose=0)[:, :, 0]
    e2 = e2_model.predict(deployment["X100"], batch_size=sg10.BATCH_SIZE, verbose=0)[:, :, 0]
    truth = np.asarray(deployment["truth100"], dtype=np.float64)

    frozen_identity_linf = float(
        np.max(np.abs(frozen - np.asarray(deployment["stored_frozen100"], dtype=float)))
    )
    if frozen_identity_linf > 2.0e-6:
        raise RuntimeError(
            "Frozen prediction does not reproduce accepted SG7C deployment.\n"
            f"Linf = {frozen_identity_linf:.6e}"
        )

    local_mask = build_front_pair_mask(truth, sg10.FRONT_HIGH, sg10.CROSSING_LOW)
    tol = float(sg10.MONOTONIC_TOL)

    truth_diag = monotonic_diagnostics(truth, local_mask, tol)
    e0_diag = monotonic_diagnostics(frozen, local_mask, tol)
    e2_diag = monotonic_diagnostics(e2, local_mask, tol)
    truth_orientation = truth_orientation_diagnostics(truth, local_mask, tol)

    truth_front = sg10.front_metrics_np(truth, truth)
    e0_front = sg10.front_metrics_np(frozen, truth)
    e2_front = sg10.front_metrics_np(e2, truth)

    print("\n" + "=" * 78)
    print("EXACT SG7B-10 MONOTONICITY METRIC")
    print("=" * 78)
    for label, diag in [("SG7A truth", truth_diag), ("E0 frozen", e0_diag), ("E2 best", e2_diag)]:
        print(f"\n{label}")
        print(f"  Eligible front pairs    : {diag['eligible_pairs']:,}")
        print(f"  Positive-dS violations  : {diag['violation_pairs']:,}")
        print(f"  Violation fraction      : {100.0 * diag['violation_fraction']:.3f}%")
        print(f"  Positive dS median      : {diag['positive_dS_median']:.6e}")
        print(f"  Positive dS P90         : {diag['positive_dS_p90']:.6e}")
        print(f"  Positive dS P99         : {diag['positive_dS_p99']:.6e}")
        print(f"  Positive dS max         : {diag['positive_dS_max']:.6e}")

    print("\nSG7A FRONT-PAIR ORIENTATION")
    print(f"  Positive dS fraction    : {100.0 * truth_orientation['positive_fraction']:.3f}%")
    print(f"  Negative dS fraction    : {100.0 * truth_orientation['negative_fraction']:.3f}%")
    print(f"  Near-zero fraction      : {100.0 * truth_orientation['near_zero_fraction']:.3f}%")
    print(f"  Signed dS mean          : {truth_orientation['signed_dS_mean']:.6e}")

    tolerance_rows = []
    for current_tol in TOLERANCE_SWEEP:
        for label, field in [("SG7A", truth), ("E0", frozen), ("E2", e2)]:
            diag = monotonic_diagnostics(field, local_mask, current_tol)
            tolerance_rows.append({
                "tolerance": float(current_tol),
                "field": label,
                "violation_fraction": diag["violation_fraction"],
                "violation_pairs": diag["violation_pairs"],
                "eligible_pairs": diag["eligible_pairs"],
            })

    truth_elig, truth_vio, truth_frac, truth_l1 = profile_level_metrics(truth, truth, local_mask, tol)
    e0_elig, e0_vio, e0_frac, e0_l1 = profile_level_metrics(frozen, truth, local_mask, tol)
    e2_elig, e2_vio, e2_frac, e2_l1 = profile_level_metrics(e2, truth, local_mask, tol)

    truth_cross = sg10.profile_has_crossing_np(truth)
    e0_cross = sg10.profile_has_crossing_np(frozen)
    e2_cross = sg10.profile_has_crossing_np(e2)

    profile_rows = []
    for i in range(len(truth)):
        profile_rows.append({
            "profile_index": i,
            "eligible_front_pairs": int(truth_elig[i]),
            "truth_violation_fraction": float(truth_frac[i]),
            "E0_violation_fraction": float(e0_frac[i]),
            "E2_violation_fraction": float(e2_frac[i]),
            "E0_profile_L1": float(e0_l1[i]),
            "E2_profile_L1": float(e2_l1[i]),
            "truth_has_front": bool(truth_cross[i]),
            "E0_has_front": bool(e0_cross[i]),
            "E2_has_front": bool(e2_cross[i]),
        })

    amplitude = []
    amplitude.extend(amplitude_rows("SG7A", truth, local_mask, tol))
    amplitude.extend(amplitude_rows("E0", frozen, local_mask, tol))
    amplitude.extend(amplitude_rows("E2", e2, local_mask, tol))

    conditioned_gap_target = (
        (1.0 - float(sg10.FRONT_CONDITIONED_GAP_REDUCTION))
        * e0_front["conditioned_threshold_gap_mean"]
    )

    e2_front_success = bool(e2_front["recovered_front_count"] >= sg10.MIN_100D_CROSSINGS)
    e2_gap_success = bool(e2_front["conditioned_threshold_gap_mean"] <= conditioned_gap_target)
    e2_profile_success = bool(e2_front["profile_L1_mean"] <= sg10.MAX_100D_PROFILE_L1)

    truth_itself_exceeds_gate = bool(truth_diag["violation_fraction"] > REFERENCE_GATE)
    e0_exceeds_gate = bool(e0_diag["violation_fraction"] > REFERENCE_GATE)
    e2_increment_over_e0 = e2_diag["violation_fraction"] - e0_diag["violation_fraction"]
    e2_materially_worse_than_e0 = bool(e2_increment_over_e0 > 0.02)

    e2_tiny_fraction = float(sum(
        row["fraction_of_violations"]
        for row in amplitude
        if row["field"] == "E2"
        and row["amplitude_bin"] in {"0_to_1e-5", "1e-5_to_1e-4", "1e-4_to_5e-4"}
    ))

    if truth_itself_exceeds_gate:
        diagnosis = "MONOTONICITY_METRIC_INCOMPATIBLE_WITH_SG7A_REFERENCE"
        recommendation = (
            "The exact SG7B-10 metric classifies more than 2% of authoritative "
            "SG7A front-pair samples as violations. Do not use the 2% absolute "
            "gate for candidate rejection until the metric is reformulated "
            "against SG7A-relative behavior."
        )
        next_milestone = "V15-SG7B-10S — SG7A-Relative Front-Shape Preservation Contract"
    elif e0_exceeds_gate and not e2_materially_worse_than_e0:
        diagnosis = "PREEXISTING_MONOTONICITY_METRIC_FLOOR"
        recommendation = (
            "The frozen accepted SG7B baseline already violates the new 2% "
            "safeguard, while E2 does not materially worsen that behavior. "
            "Define a baseline-relative / SG7A-relative front-shape preservation "
            "criterion before judging E2."
        )
        next_milestone = "V15-SG7B-10S — SG7A-Relative Front-Shape Preservation Contract"
    elif e2_materially_worse_than_e0:
        diagnosis = "E2_INDUCED_FRONT_OSCILLATION"
        recommendation = (
            "E2 recovers the front but materially increases local monotonic "
            "violations relative to the frozen model. Proceed to controlled "
            "shape/gradient-regularized candidates E4-E6."
        )
        next_milestone = "V15-SG7B-10B — Shape-Regularized Front-Aware Refinement"
    elif e2_tiny_fraction >= 0.80:
        diagnosis = "MONOTONICITY_VIOLATIONS_DOMINATED_BY_SMALL_AMPLITUDE"
        recommendation = (
            "Most counted E2 violations are extremely small increments. "
            "Reformulate the safeguard using physically scaled amplitude and "
            "SG7A-relative shape behavior before additional training."
        )
        next_milestone = "V15-SG7B-10S — SG7A-Relative Front-Shape Preservation Contract"
    else:
        diagnosis = "MIXED_MONOTONICITY_MECHANISM"
        recommendation = (
            "The monotonicity failure contains mixed baseline, truth, and "
            "candidate effects. Retain E2 only as a diagnostic candidate and "
            "perform a more localized shape audit before additional training."
        )
        next_milestone = "V15-SG7B-10R2 — Local Front-Shape Mechanism Audit"

    global_rows = []
    for label, diag, front in [("SG7A", truth_diag, truth_front), ("E0", e0_diag, e0_front), ("E2", e2_diag, e2_front)]:
        global_rows.append({
            "field": label,
            "eligible_pairs": diag["eligible_pairs"],
            "violation_pairs": diag["violation_pairs"],
            "violation_fraction": diag["violation_fraction"],
            "positive_dS_median": diag["positive_dS_median"],
            "positive_dS_p90": diag["positive_dS_p90"],
            "positive_dS_p99": diag["positive_dS_p99"],
            "positive_dS_max": diag["positive_dS_max"],
            "recovered_fronts": front["recovered_front_count"],
            "conditioned_gap": front["conditioned_threshold_gap_mean"],
            "profile_L1": front["profile_L1_mean"],
        })

    save_csv(GLOBAL_TABLE, global_rows)
    save_csv(TOLERANCE_TABLE, tolerance_rows)
    save_csv(AMPLITUDE_TABLE, amplitude)
    save_csv(PROFILE_TABLE, profile_rows)

    labels = ["SG7A", "E0", "E2"]
    fractions = [truth_diag["violation_fraction"], e0_diag["violation_fraction"], e2_diag["violation_fraction"]]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.bar(labels, [100.0 * v for v in fractions])
    ax.axhline(100.0 * REFERENCE_GATE, linestyle="--", label="SG7B-9 2% reference")
    ax.set_ylabel("Local monotonic violation [%]")
    ax.set_title("PAD-Stream V15-SG7B-10R\nExact Monotonicity Metric")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "V15SG7B10R_Monotonicity_Comparison.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 6))
    for label in ["SG7A", "E0", "E2"]:
        rows = [r for r in tolerance_rows if r["field"] == label]
        ax.plot([r["tolerance"] for r in rows],
                [100.0 * r["violation_fraction"] for r in rows],
                marker="o", label=label)
    ax.set_xscale("symlog", linthresh=1e-6)
    ax.set_xlabel("Positive dS tolerance")
    ax.set_ylabel("Violation fraction [%]")
    ax.set_title("PAD-Stream V15-SG7B-10R\nMonotonicity Tolerance Sensitivity")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "V15SG7B10R_Tolerance_Sensitivity.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.hist(e0_frac, bins=40, alpha=0.55, label="E0")
    ax.hist(e2_frac, bins=40, alpha=0.55, label="E2")
    ax.set_xlabel("Per-profile front-pair violation fraction")
    ax.set_ylabel("Profiles")
    ax.set_title("PAD-Stream V15-SG7B-10R\nPer-Profile Monotonicity")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "V15SG7B10R_Profile_Violation_Distribution.png", dpi=300)
    plt.close(fig)

    np.savez_compressed(
        DATABASE_FILE,
        truth100=truth.astype(np.float32),
        E0_frozen100=frozen.astype(np.float32),
        E2_best100=e2.astype(np.float32),
        local_mask=local_mask,
        tolerance_sweep=TOLERANCE_SWEEP,
        xi=np.asarray(deployment["xi"], dtype=np.float32),
    )

    checks = [
        ("SG7B-10 outcome requires audit", str(sg10_summary.get("next_milestone", "")).startswith("V15-SG7B-10R")),
        ("Frozen deployment identity reproduced", frozen_identity_linf <= 2.0e-6),
        ("E2 best checkpoint loaded", E2_MODEL_FILE.exists()),
        ("SG7A / E0 / E2 fields finite", bool(np.all(np.isfinite(truth)) and np.all(np.isfinite(frozen)) and np.all(np.isfinite(e2)))),
        ("Front-local mask contains samples", bool(np.any(local_mask))),
        ("E2 front recovery target met", e2_front_success),
        ("E2 conditioned-gap target met", e2_gap_success),
        ("E2 100-day profile-L1 target met", e2_profile_success),
        ("Monotonicity mechanism classified", diagnosis in {
            "MONOTONICITY_METRIC_INCOMPATIBLE_WITH_SG7A_REFERENCE",
            "PREEXISTING_MONOTONICITY_METRIC_FLOOR",
            "E2_INDUCED_FRONT_OSCILLATION",
            "MONOTONICITY_VIOLATIONS_DOMINATED_BY_SMALL_AMPLITUDE",
            "MIXED_MONOTONICITY_MECHANISM",
        }),
    ]
    passed = all(status for _, status in checks)

    print("\n" + "=" * 78)
    print("V15-SG7B-10R DIAGNOSTIC VALIDATION")
    print("=" * 78)
    for description, status in checks:
        print(f"[{'PASS' if status else 'FAIL'}] {description}")
    print("=" * 78)

    print("\nOUTCOME COMPARISON")
    print(f"  SG7A violation           : {100.0 * truth_diag['violation_fraction']:.3f}%")
    print(f"  E0 violation             : {100.0 * e0_diag['violation_fraction']:.3f}%")
    print(f"  E2 violation             : {100.0 * e2_diag['violation_fraction']:.3f}%")
    print(f"  E2 - E0 change           : {100.0 * e2_increment_over_e0:+.3f} percentage points")
    print(f"  E2 tiny-amplitude share  : {100.0 * e2_tiny_fraction:.3f}%")
    print(f"  E2 recovered fronts      : {e2_front['recovered_front_count']:,} / {e2_front['truth_front_count']:,}")
    print(f"  E2 conditioned gap       : {e2_front['conditioned_threshold_gap_mean']:.6e}")
    print(f"  E2 100d profile L1       : {e2_front['profile_L1_mean']:.6e}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    summary = {
        "milestone": "V15-SG7B-10R",
        "description": "Front-aware refinement outcome / monotonicity audit",
        "training_performed": False,
        "model_parameters_changed": False,
        "freeze_gate_changed": False,
        "candidate_promoted": False,
        "deployment_workspace": str(workspace),
        "frozen_identity_linf": frozen_identity_linf,
        "SG7A": global_rows[0],
        "E0": global_rows[1],
        "E2": global_rows[2],
        "truth_orientation": truth_orientation,
        "E2_minus_E0_violation_fraction": e2_increment_over_e0,
        "E2_tiny_amplitude_violation_share": e2_tiny_fraction,
        "diagnosis": diagnosis,
        "recommendation": recommendation,
        "audit_passed": bool(passed),
        "next_milestone": next_milestone,
    }
    with SUMMARY_FILE.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")
    print("\nTables:")
    print(f"  {GLOBAL_TABLE.name}")
    print(f"  {TOLERANCE_TABLE.name}")
    print(f"  {AMPLITUDE_TABLE.name}")
    print(f"  {PROFILE_TABLE.name}")
    print("\nDatabase:")
    print(f"  {DATABASE_FILE.name}")
    print("\nDiagnostics:")
    print("  V15SG7B10R_Monotonicity_Comparison.png")
    print("  V15SG7B10R_Tolerance_Sensitivity.png")
    print("  V15SG7B10R_Profile_Violation_Distribution.png")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    if passed:
        print("V15-SG7B-10R AUDIT: PASS")
        print()
        print("No gate has been changed.")
        print("No candidate has been promoted.")
        print()
        print(f"Diagnosis:\n  {diagnosis}")
        print()
        print(f"Next milestone:\n  {next_milestone}")
    else:
        print("V15-SG7B-10R AUDIT: INCOMPLETE")
        print()
        print("Do not resume training or candidate promotion until the audit is consistent.")
    print("=" * 78)

if __name__ == "__main__":
    main()
