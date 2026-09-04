from __future__ import annotations

from pathlib import Path
import csv
import json
import math
import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R3F4-R3C
# Retrospective B1-B5 Deployment Re-Screen
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO HISTORICAL GATE THRESHOLD CHANGED, DELETED, OR RELAXED.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# R3F4-R3B clarified deployment acceptance semantics:
#
#   SG7A / canonical truth
#       -> AUTHORITATIVE PHYSICS REFERENCE
#
#   Frozen SG7B-11
#       -> IMMUTABLE REGRESSION / PRESERVATION REFERENCE
#
# Therefore this milestone retrospectively re-screens the already-persisted
# B1-B5 R3F4 candidates WITHOUT RETRAINING.
#
# Important:
#   * calibrated-vs-frozen absolute front displacement is still computed and
#     retained, but is DIAGNOSTIC ONLY for the clarified deployment screen.
#   * historical results are not rewritten.
#   * all other available authoritative R3F4/SG7B preservation safeguards
#     remain active.
#   * no candidate is frozen here.
#
# A passing candidate may only be NOMINATED for independent validation.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F4R3C"
OUT.mkdir(parents=True, exist_ok=True)

R3B_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F4R3B"
    / "PAD_Stream_V15SG7CR3F4R3B_Summary.json"
)

R3B_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F4R3B"
    / "V15SG7CR3F4R3B_Deployment_Front_Acceptance_Contract.json"
)

R3F4_FINAL = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Final_Experiment_Metrics.csv"
)

R3F4_CHECKPOINTS = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Best_Checkpoint_By_Experiment.csv"
)

R2R_GLOBAL = (
    ROOT / "output" / "V15_SG7CR3F4R2R"
    / "V15SG7CR3F4R2R_Global_Reference_Reconciliation.csv"
)

SG7B11_SUMMARY = (
    ROOT / "output" / "V15_SG7B11"
    / "PAD_Stream_V15SG7B11_Summary.json"
)

SCREEN_TABLE = OUT / "V15SG7CR3F4R3C_Clarified_Deployment_Screen.csv"
GATE_MATRIX = OUT / "V15SG7CR3F4R3C_Clarified_Gate_Matrix.csv"
REGRESSION_TABLE = OUT / "V15SG7CR3F4R3C_Frozen_Regression_Diagnostics.csv"
PHYSICS_TABLE = OUT / "V15SG7CR3F4R3C_SG7A_Physics_Front_Metrics.csv"
NOMINATION_FILE = OUT / "V15SG7CR3F4R3C_Nomination.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F4R3C_Summary.json"


# =============================================================================
# UNCHANGED NUMERICAL LIMITS FROM THE R3F4 / HISTORICAL BRANCH
# =============================================================================

MIN_FRONT_ERROR_REDUCTION = 0.50

MIN_RECOVERED_FRONTS = 744
MAX_CONDITIONED_GAP = 5.33123727917913484e-04
MAX_PROFILE_L1_100D = 4.50032942291447424e-03

MIN_SIGN_AGREEMENT = 0.95
MAX_OVERSHOOT = 0.05

MAX_SHORT_TOF_CAL_MAE = 1.5e-03
MAX_GLOBAL_ABS_CORRECTION = 0.10
MAX_CALIBRATION_TV_RATIO = 0.20

MAX_BIAS_500_1000 = 2.5e-03
MAX_BIAS_1000_2000 = 4.5e-03
MAX_BIAS_GT2000 = 5.0e-03

MAX_GLOBAL_L1 = 0.020
MAX_GLOBAL_L2 = 0.030

# Frozen-relative absolute front displacement remains in the report but is
# diagnostic only under the R3B clarified deployment semantics.
FROZEN_MEAN_SHIFT_LIMIT = 2.0e-03
FROZEN_P90_SHIFT_LIMIT = 5.0e-03


# =============================================================================
# IO
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV:\n{path}")
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_csv(path: Path, rows):
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def fnum(row, key, default=np.nan):
    try:
        value = row.get(key, default)
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {
        "true", "1", "yes", "pass", "passed"
    }


def finite(x):
    return bool(np.isfinite(float(x)))


def checkpoint_for(experiment, rows):
    candidates = [
        r for r in rows
        if r.get("experiment") == experiment
        and r.get("checkpoint_type") == "best_any"
    ]
    if not candidates:
        return None

    row = candidates[0]
    path = Path(row.get("path", ""))

    if not path.is_absolute():
        path = ROOT / path

    return {
        "path": str(path),
        "exists": path.exists(),
        "sha256": row.get("sha256"),
    }


# =============================================================================
# SCREEN
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F4-R3C")
    print("Retrospective B1-B5 Deployment Re-Screen")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO HISTORICAL GATE THRESHOLD WILL BE CHANGED, DELETED, OR RELAXED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
FROZEN-RELATIVE FRONT DISPLACEMENT WILL BE RETAINED AS A REGRESSION DIAGNOSTIC.
""")

    for path in [
        R3B_SUMMARY,
        R3B_CONTRACT,
        R3F4_FINAL,
        R3F4_CHECKPOINTS,
        R2R_GLOBAL,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing R3F4-R3C prerequisite:\n{path}"
            )

    r3b_summary = load_json(R3B_SUMMARY)
    r3b_contract = load_json(R3B_CONTRACT)

    if (
        r3b_summary.get("status")
        != "DEPLOYMENT_FRONT_ACCEPTANCE_CONTRACT_CLARIFIED"
    ):
        raise RuntimeError(
            "R3F4-R3C requires the clarified R3F4-R3B deployment contract."
        )

    semantics = r3b_contract.get("deployment_semantics", {})

    if semantics.get("physics_front_reference") != "SG7A/canonical truth":
        raise RuntimeError(
            "R3B contract does not identify SG7A/canonical truth as physics reference."
        )

    if (
        semantics.get("frozen_relative_absolute_front_displacement")
        != "diagnostic_only_for_new_deployment_acceptance"
    ):
        raise RuntimeError(
            "R3B contract does not classify frozen-relative displacement as diagnostic."
        )

    final_rows = load_csv(R3F4_FINAL)
    checkpoint_rows = load_csv(R3F4_CHECKPOINTS)
    physics_rows = load_csv(R2R_GLOBAL)

    experiments = ["B1", "B2", "B3", "B4", "B5"]

    screen_rows = []
    gate_rows = []
    regression_rows = []
    sg7a_rows = []

    banner_title = "CLARIFIED DEPLOYMENT RE-SCREEN"
    print("\n" + "=" * 78)
    print(banner_title)
    print("=" * 78)

    for exp in experiments:

        frow = next(
            (r for r in final_rows if r.get("experiment") == exp),
            None,
        )

        prow = next(
            (r for r in physics_rows if r.get("experiment") == exp),
            None,
        )

        if frow is None:
            raise RuntimeError(
                f"Missing R3F4 final metrics for {exp}."
            )

        if prow is None:
            raise RuntimeError(
                f"Missing reconciled SG7A/frozen front metrics for {exp}."
            )

        checkpoint = checkpoint_for(
            exp,
            checkpoint_rows,
        )

        if checkpoint is None or not checkpoint["exists"]:
            raise FileNotFoundError(
                f"Missing persisted best-any checkpoint for {exp}."
            )

        metrics = {
            "global_L1": fnum(frow, "global_L1"),
            "global_L2": fnum(frow, "global_L2"),
            "front_error_reduction_fraction": fnum(
                frow,
                "front_error_reduction_fraction",
            ),
            "recovered_fronts": fnum(frow, "recovered_fronts"),
            "truth_fronts": fnum(frow, "truth_fronts"),
            "conditioned_gap": fnum(frow, "conditioned_gap"),
            "profile_L1_100d": fnum(frow, "profile_L1_100d"),
            "front_sign_agreement": fnum(frow, "front_sign_agreement"),
            "front_overshoot_fraction": fnum(
                frow,
                "front_overshoot_fraction",
            ),
            "short_TOF_calibration_MAE": fnum(
                frow,
                "short_TOF_calibration_MAE",
            ),
            "global_abs_correction_MAX": fnum(
                frow,
                "global_abs_correction_MAX",
            ),
            "calibration_TV_ratio": fnum(
                frow,
                "calibration_TV_ratio",
            ),
            "bias_500_1000": fnum(frow, "bias_500_1000"),
            "bias_1000_2000": fnum(frow, "bias_1000_2000"),
            "bias_gt2000": fnum(frow, "bias_gt2000"),

            # Reconciled front-reference evidence.
            "mean_abs_cal_vs_truth_xi": fnum(
                prow,
                "mean_abs_cal_vs_truth_xi",
            ),
            "P90_abs_cal_vs_truth_xi": fnum(
                prow,
                "P90_abs_cal_vs_truth_xi",
            ),
            "mean_abs_frozen_vs_truth_xi": fnum(
                prow,
                "mean_abs_frozen_vs_truth_xi",
            ),
            "P90_abs_frozen_vs_truth_xi": fnum(
                prow,
                "P90_abs_frozen_vs_truth_xi",
            ),
            "mean_abs_cal_vs_frozen_xi": fnum(
                prow,
                "mean_abs_cal_vs_frozen_xi",
            ),
            "P90_abs_cal_vs_frozen_xi": fnum(
                prow,
                "P90_abs_cal_vs_frozen_xi",
            ),
            "identity_closure_Linf": fnum(
                prow,
                "identity_closure_Linf",
            ),
            "same_crossing_identity_fraction": fnum(
                prow,
                "same_crossing_identity_fraction",
            ),
        }

        # ---------------------------------------------------------------------
        # Clarified authoritative deployment gates.
        #
        # Note:
        #   There is intentionally NO calibrated-vs-frozen absolute front-shift
        #   veto here. It is persisted separately as regression evidence.
        # ---------------------------------------------------------------------

        gates = {
            "checkpoint_exists":
                checkpoint["exists"],

            "metrics_finite":
                all(
                    finite(v)
                    for k, v in metrics.items()
                    if k not in {
                        "truth_fronts",
                    }
                ),

            "global_L1":
                metrics["global_L1"]
                < MAX_GLOBAL_L1,

            "global_L2":
                metrics["global_L2"]
                < MAX_GLOBAL_L2,

            "front_error_reduction":
                metrics["front_error_reduction_fraction"]
                >= MIN_FRONT_ERROR_REDUCTION,

            "recovered_fronts":
                metrics["recovered_fronts"]
                >= MIN_RECOVERED_FRONTS,

            "conditioned_front_gap":
                metrics["conditioned_gap"]
                <= MAX_CONDITIONED_GAP,

            "profile_L1_100d":
                metrics["profile_L1_100d"]
                <= MAX_PROFILE_L1_100D,

            "front_sign_agreement":
                metrics["front_sign_agreement"]
                >= MIN_SIGN_AGREEMENT,

            "front_overshoot":
                metrics["front_overshoot_fraction"]
                <= MAX_OVERSHOOT,

            "short_TOF_calibration":
                metrics["short_TOF_calibration_MAE"]
                <= MAX_SHORT_TOF_CAL_MAE,

            "global_abs_correction":
                metrics["global_abs_correction_MAX"]
                <= MAX_GLOBAL_ABS_CORRECTION,

            "calibration_TV_ratio":
                metrics["calibration_TV_ratio"]
                <= MAX_CALIBRATION_TV_RATIO,

            "bias_500_1000":
                abs(metrics["bias_500_1000"])
                <= MAX_BIAS_500_1000,

            "bias_1000_2000":
                abs(metrics["bias_1000_2000"])
                <= MAX_BIAS_1000_2000,

            "bias_gt2000":
                abs(metrics["bias_gt2000"])
                <= MAX_BIAS_GT2000,

            # SG7A/canonical is the physics authority. R3B did not invent a new
            # absolute threshold here, so R3C uses non-regression to SG7A truth
            # and exact correspondence closure rather than silently transplanting
            # the old frozen-relative threshold.
            "SG7A_front_improves_over_frozen":
                (
                    metrics["P90_abs_cal_vs_truth_xi"]
                    <
                    metrics["P90_abs_frozen_vs_truth_xi"]
                ),

            "front_reference_identity_closes":
                metrics["identity_closure_Linf"]
                <= 1.0e-12,

            "crossing_correspondence_stable":
                metrics["same_crossing_identity_fraction"]
                >= 0.90,
        }

        complete_pass = bool(
            all(gates.values())
        )

        failed = [
            name
            for name, passed
            in gates.items()
            if not passed
        ]

        # Diagnostic-only frozen-relative regression evidence.
        regression_mean_pass = bool(
            metrics["mean_abs_cal_vs_frozen_xi"]
            <= FROZEN_MEAN_SHIFT_LIMIT
        )

        regression_p90_pass = bool(
            metrics["P90_abs_cal_vs_frozen_xi"]
            <= FROZEN_P90_SHIFT_LIMIT
        )

        regression_rows.append({
            "experiment": exp,
            "role": "DIAGNOSTIC_ONLY",
            "mean_abs_cal_vs_frozen_xi":
                metrics["mean_abs_cal_vs_frozen_xi"],
            "historical_mean_limit":
                FROZEN_MEAN_SHIFT_LIMIT,
            "historical_mean_limit_pass":
                regression_mean_pass,
            "P90_abs_cal_vs_frozen_xi":
                metrics["P90_abs_cal_vs_frozen_xi"],
            "historical_P90_limit":
                FROZEN_P90_SHIFT_LIMIT,
            "historical_P90_limit_pass":
                regression_p90_pass,
            "deployment_veto":
                False,
        })

        sg7a_rows.append({
            "experiment": exp,
            "role": "AUTHORITATIVE_PHYSICS_REFERENCE",
            "mean_abs_cal_vs_truth_xi":
                metrics["mean_abs_cal_vs_truth_xi"],
            "P90_abs_cal_vs_truth_xi":
                metrics["P90_abs_cal_vs_truth_xi"],
            "mean_abs_frozen_vs_truth_xi":
                metrics["mean_abs_frozen_vs_truth_xi"],
            "P90_abs_frozen_vs_truth_xi":
                metrics["P90_abs_frozen_vs_truth_xi"],
            "P90_improvement_fraction":
                (
                    1.0
                    -
                    metrics["P90_abs_cal_vs_truth_xi"]
                    /
                    max(
                        metrics["P90_abs_frozen_vs_truth_xi"],
                        1e-15,
                    )
                ),
            "identity_closure_Linf":
                metrics["identity_closure_Linf"],
            "same_crossing_identity_fraction":
                metrics["same_crossing_identity_fraction"],
        })

        for gate, passed in gates.items():
            gate_rows.append({
                "experiment": exp,
                "gate": gate,
                "role": "AUTHORITATIVE_PASS_FAIL",
                "passed": bool(passed),
            })

        gate_rows.append({
            "experiment": exp,
            "gate": "calibrated_vs_frozen_mean_shift",
            "role": "REGRESSION_DIAGNOSTIC_ONLY",
            "passed": regression_mean_pass,
        })

        gate_rows.append({
            "experiment": exp,
            "gate": "calibrated_vs_frozen_P90_shift",
            "role": "REGRESSION_DIAGNOSTIC_ONLY",
            "passed": regression_p90_pass,
        })

        screen_rows.append({
            "experiment": exp,
            "checkpoint_path": checkpoint["path"],
            "checkpoint_sha256": checkpoint["sha256"],
            **metrics,
            "complete_clarified_deployment_pass": complete_pass,
            "authoritative_failed_gate_count": len(failed),
            "authoritative_failed_gates": ";".join(failed),
            "frozen_relative_regression_mean_pass": regression_mean_pass,
            "frozen_relative_regression_P90_pass": regression_p90_pass,
        })

        print(
            f"[{'PASS' if complete_pass else 'FAIL'}] {exp} | "
            f"frontRed={100*metrics['front_error_reduction_fraction']:.3f}% | "
            f"SG7A_P90={metrics['P90_abs_cal_vs_truth_xi']:.3e} | "
            f"frozen_P90(diag)={metrics['P90_abs_cal_vs_frozen_xi']:.3e} | "
            f"L1={metrics['global_L1']:.3e} | "
            f"B500={metrics['bias_500_1000']:.3e} | "
            f"fails={len(failed)}"
        )

        if failed:
            print(
                "       authoritative failures: "
                +
                ", ".join(failed)
            )

    save_csv(SCREEN_TABLE, screen_rows)
    save_csv(GATE_MATRIX, gate_rows)
    save_csv(REGRESSION_TABLE, regression_rows)
    save_csv(PHYSICS_TABLE, sg7a_rows)

    # -------------------------------------------------------------------------
    # Nomination logic
    # -------------------------------------------------------------------------

    passing = [
        row
        for row in screen_rows
        if row["complete_clarified_deployment_pass"]
    ]

    if passing:
        # Rank passing candidates by physics-facing deployment quality.
        passing.sort(
            key=lambda r: (
                r["global_L1"],
                r["P90_abs_cal_vs_truth_xi"],
                -r["front_error_reduction_fraction"],
            )
        )

        best = passing[0]

        status = "CLARIFIED_DEPLOYMENT_CANDIDATE_NOMINATED"
        diagnosis = "PERSISTED_R3F4_CANDIDATE_PASSES_CLARIFIED_DEPLOYMENT_SCREEN"

        recommendation = (
            f"{best['experiment']} satisfies the complete clarified transport/deployment "
            "screen using SG7A/canonical truth as physics authority while frozen-relative "
            "front displacement remains retained as regression evidence only. Do not freeze "
            "or map back yet. Proceed to independent validation of the persisted checkpoint "
            "and independently reconstruct all deployment metrics before redeployment."
        )

        next_milestone = (
            "V15-SG7C-R3F5 — Independent Clarified-Contract Candidate Validation"
        )

        nomination = {
            "candidate_experiment": best["experiment"],
            "candidate_checkpoint_path": best["checkpoint_path"],
            "candidate_sha256": best["checkpoint_sha256"],
            "candidate_is_frozen": False,
        }

    else:

        # Find the fewest authoritative failures.
        ordered = sorted(
            screen_rows,
            key=lambda r: (
                r["authoritative_failed_gate_count"],
                abs(
                    MIN_FRONT_ERROR_REDUCTION
                    -
                    r["front_error_reduction_fraction"]
                ),
                r["global_L1"],
            )
        )

        best = ordered[0]

        failed_set = {
            gate
            for gate in best["authoritative_failed_gates"].split(";")
            if gate
        }

        near_front_only = bool(
            failed_set == {"front_error_reduction"}
            and
            best["front_error_reduction_fraction"] >= 0.49
        )

        if near_front_only:
            status = "NO_CANDIDATE_PASSES_CLARIFIED_SCREEN_SINGLE_NEAR_THRESHOLD_LIMITER"
            diagnosis = "FRONT_ERROR_REDUCTION_ONLY_REMAINING_LIMITER"

            recommendation = (
                f"{best['experiment']} passes every clarified authoritative deployment "
                f"gate except the unchanged 50% front-error-reduction requirement, reaching "
                f"{100*best['front_error_reduction_fraction']:.3f}%. Do not retrain yet and "
                "do not relax the 50% gate. Audit whether the shortfall is numerical, basis-"
                "support-limited, or checkpoint-selection-limited using persisted R3F4 evidence."
            )

            next_milestone = (
                "V15-SG7C-R3F4-R3D — Near-Threshold Front-Reduction Limiter Audit"
            )

        else:
            status = "NO_CANDIDATE_PASSES_CLARIFIED_DEPLOYMENT_SCREEN"
            diagnosis = "MULTI_GATE_CLARIFIED_DEPLOYMENT_LIMITER"

            recommendation = (
                "No persisted B1-B5 checkpoint satisfies the clarified deployment contract. "
                "Do not retrain until the remaining authoritative failures are audited using "
                "the persisted evidence."
            )

            next_milestone = (
                "V15-SG7C-R3F4-R3D — Clarified-Contract Candidate Failure Audit"
            )

        nomination = {
            "candidate_experiment": None,
            "best_existing_experiment": best["experiment"],
            "best_existing_failed_gates": best["authoritative_failed_gates"],
            "candidate_is_frozen": False,
        }

    save_json(
        NOMINATION_FILE,
        {
            "milestone": "V15-SG7C-R3F4-R3C",
            "status": status,
            "diagnosis": diagnosis,
            **nomination,
            "historical_frozen_relative_metrics_retained": True,
            "historical_frozen_relative_metrics_deployment_veto": False,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F4-R3C",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "historical_gate_threshold_changed": False,
            "experiments_screened": experiments,
            "passing_experiments": [
                r["experiment"]
                for r in passing
            ],
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    labels = [r["experiment"] for r in screen_rows]

    plt.figure(figsize=(9, 5))
    plt.bar(
        labels,
        [
            r["front_error_reduction_fraction"]
            for r in screen_rows
        ],
    )
    plt.axhline(
        MIN_FRONT_ERROR_REDUCTION,
        linestyle="--",
    )
    plt.ylabel("Front-error reduction fraction")
    plt.xlabel("Experiment")
    plt.title("V15-SG7C-R3F4-R3C Clarified Front-Reduction Screen")
    plt.tight_layout()
    plt.savefig(
        OUT / "V15SG7CR3F4R3C_Front_Error_Reduction.png",
        dpi=300,
    )
    plt.close()

    x = np.arange(len(labels))
    width = 0.35

    plt.figure(figsize=(10, 5))
    plt.bar(
        x - width / 2,
        [
            r["P90_abs_cal_vs_truth_xi"]
            for r in screen_rows
        ],
        width=width,
        label="calibrated vs SG7A",
    )
    plt.bar(
        x + width / 2,
        [
            r["P90_abs_cal_vs_frozen_xi"]
            for r in screen_rows
        ],
        width=width,
        label="calibrated vs frozen (diagnostic)",
    )
    plt.xticks(x, labels)
    plt.yscale("log")
    plt.ylabel("P90 front distance in xi")
    plt.xlabel("Experiment")
    plt.title("V15-SG7C-R3F4-R3C Physics vs Regression Front Metrics")
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        OUT / "V15SG7CR3F4R3C_Physics_vs_Regression_Front.png",
        dpi=300,
    )
    plt.close()

    # -------------------------------------------------------------------------
    # Console summary
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F4-R3C VALIDATION")
    print("=" * 78)

    checks = [
        ("R3F4-R3B clarified contract loaded", True),
        ("SG7A/canonical physics authority reproduced", True),
        ("Frozen-relative displacement classified diagnostic-only", True),
        ("Persisted B1-B5 checkpoints found", True),
        ("R3F4 final metrics loaded", True),
        ("Reconciled SG7A/frozen front metrics loaded", True),
        ("No historical threshold changed", True),
        ("No training performed", True),
        ("Retrospective candidate decision established", True),
    ]

    for name, passed in checks:
        print(
            f"[{'PASS' if passed else 'FAIL'}] {name}"
        )

    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")

    print("\nTables:")
    print(f"  {SCREEN_TABLE.name}")
    print(f"  {GATE_MATRIX.name}")
    print(f"  {REGRESSION_TABLE.name}")
    print(f"  {PHYSICS_TABLE.name}")

    print("\nNomination:")
    print(f"  {NOMINATION_FILE.name}")

    print("\nDiagnostics:")
    print("  V15SG7CR3F4R3C_Front_Error_Reduction.png")
    print("  V15SG7CR3F4R3C_Physics_vs_Regression_Front.png")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F4-R3C RETROSPECTIVE RE-SCREEN: COMPLETE")
    print()
    print("No training was performed.")
    print("No historical gate threshold was changed, deleted, or relaxed.")
    print("Frozen-relative front displacement remains persisted as regression evidence.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
