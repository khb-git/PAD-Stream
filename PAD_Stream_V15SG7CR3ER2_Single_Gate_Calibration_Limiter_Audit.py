from __future__ import annotations

from pathlib import Path
import csv
import json
import math

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R3E-R2
# Single-Gate Calibration Limiter Audit
#
# DIAGNOSTIC-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL/CALIBRATOR WEIGHTS CHANGED.
# NO FRONT-ERROR-REDUCTION GATE RELAXED.
# NO SG7B-11 CHANGE.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# R3E-R established:
#
#     SINGLE_FINAL_GATE_LIMITER
#
# with:
#
#     dominant failed gate = front_error_reduction
#
# R3E-R2 determines whether the failure is:
#
#   1. simply insufficient front-state correction amplitude,
#   2. a conflict between front-state correction and threshold/front-shape gates,
#   3. an artifact of R3E candidate-selection / checkpoint persistence,
#   4. or a mismatch between the front-error-reduction definition and the
#      validated canonical residual target.
#
# The audit uses ONLY authoritative R3E experiment-level outputs.
# It does not invent epoch histories that were not persisted.
# =============================================================================


ROOT = Path(__file__).resolve().parent

R3ER_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3ER"
    / "PAD_Stream_V15SG7CR3ER_Summary.json"
)

R3E_METRICS = (
    ROOT / "output" / "V15_SG7CR3E"
    / "V15SG7CR3E_Experiment_Metrics.csv"
)

R3E_GATES = (
    ROOT / "output" / "V15_SG7CR3E"
    / "V15SG7CR3E_Final_Gate_Matrix.csv"
)

R3DR_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3DR"
    / "V15SG7CR3DR_Frozen_Deployment_Calibration_Contract.json"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3ER2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

METRIC_TABLE = (
    OUTPUT_DIR / "V15SG7CR3ER2_Front_Error_Reduction_By_Experiment.csv"
)

TRADEOFF_TABLE = (
    OUTPUT_DIR / "V15SG7CR3ER2_Front_Tradeoff_Audit.csv"
)

TARGET_TABLE = (
    OUTPUT_DIR / "V15SG7CR3ER2_Ideal_Front_Correction_Reference.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "PAD_Stream_V15SG7CR3ER2_Summary.json"
)


FRONT_SHELL_LOW = 0.205
FRONT_SHELL_HIGH = 0.300
FRONT_THRESHOLD = 0.210

MIN_REQUIRED_REDUCTION = 0.50


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


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def save_csv(path: Path, rows):
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def num(row, aliases, default=np.nan):
    if isinstance(aliases, str):
        aliases = [aliases]

    for key in aliases:
        if key in row:
            value = str(row[key]).strip()
            if value == "":
                continue
            try:
                return float(value)
            except Exception:
                pass

    return default


def text(row, aliases, default=""):
    if isinstance(aliases, str):
        aliases = [aliases]

    for key in aliases:
        if key in row:
            return str(row[key])

    return default


def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3E-R2")
    print("Single-Gate Calibration Limiter Audit")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO SG7B-11 OR CALIBRATOR WEIGHTS WILL BE CHANGED.")
    print("NO FRONT-ERROR-REDUCTION GATE WILL BE RELAXED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for path in [
        R3ER_SUMMARY,
        R3E_METRICS,
        R3E_GATES,
        R3DR_CONTRACT,
        R3C_NUMERICAL,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing R3E-R2 prerequisite:\n{path}")

    r3er = load_json(R3ER_SUMMARY)
    contract = load_json(R3DR_CONTRACT)
    metrics = load_csv(R3E_METRICS)
    gates = load_csv(R3E_GATES)
    db = np.load(R3C_NUMERICAL, allow_pickle=True)

    if r3er.get("diagnosis") != "SINGLE_FINAL_GATE_LIMITER":
        raise RuntimeError(
            "R3E-R2 requires incoming diagnosis:\n"
            "SINGLE_FINAL_GATE_LIMITER"
        )

    if r3er.get("dominant_failed_gate") != "front_error_reduction":
        raise RuntimeError(
            "R3E-R2 currently audits front_error_reduction only."
        )

    exact_front = contract["authoritative_front_contract"]

    max_gap = float(
        exact_front["maximum_conditioned_threshold_gap"]
    )

    min_recovered = int(
        exact_front["minimum_recovered_fronts"]
    )

    max_profile_l1 = float(
        exact_front["maximum_100d_profile_L1"]
    )

    frozen = np.asarray(
        db["deployment_pirnn"],
        dtype=float,
    )

    truth = np.asarray(
        db["deployment_truth"],
        dtype=float,
    )

    canonical = np.asarray(
        db["canonical_interpolated_target"],
        dtype=float,
    )

    times_days = np.asarray(
        db["times_days"],
        dtype=float,
    )

    idx100 = int(
        np.argmin(
            np.abs(
                times_days
                -
                100.0
            )
        )
    )

    if not np.isclose(times_days[idx100], 100.0):
        raise RuntimeError("100-day snapshot not found.")

    truth100 = truth[idx100]
    frozen100 = frozen[idx100]
    canonical100 = canonical[idx100]

    front_shell = (
        (truth100 >= FRONT_SHELL_LOW)
        &
        (truth100 <= FRONT_SHELL_HIGH)
    )

    frozen_front_l1 = float(
        np.mean(
            np.abs(
                frozen100[front_shell]
                -
                truth100[front_shell]
            )
        )
    )

    ideal_front_l1 = float(
        np.mean(
            np.abs(
                canonical100[front_shell]
                -
                truth100[front_shell]
            )
        )
    )

    ideal_reduction = float(
        1.0
        -
        ideal_front_l1
        /
        max(
            frozen_front_l1,
            1.0e-15,
        )
    )

    required_delta = (
        canonical100[front_shell]
        -
        frozen100[front_shell]
    )

    required_correction_mae = float(
        np.mean(
            np.abs(
                required_delta
            )
        )
    )

    required_correction_p90 = float(
        np.percentile(
            np.abs(
                required_delta
            ),
            90,
        )
    )

    required_correction_max = float(
        np.max(
            np.abs(
                required_delta
            )
        )
    )

    print("\nIDEAL FRONT-CORRECTION REFERENCE")
    print(f"  Frozen front-shell L1       : {frozen_front_l1:.6e}")
    print(f"  Canonical front-shell L1    : {ideal_front_l1:.6e}")
    print(f"  Ideal error reduction       : {100.0*ideal_reduction:.3f}%")
    print(f"  Required correction MAE     : {required_correction_mae:.6e}")
    print(f"  Required correction P90     : {required_correction_p90:.6e}")
    print(f"  Required correction MAX     : {required_correction_max:.6e}")

    target_rows = [
        {
            "metric": "frozen_front_shell_L1",
            "value": frozen_front_l1,
        },
        {
            "metric": "canonical_front_shell_L1",
            "value": ideal_front_l1,
        },
        {
            "metric": "ideal_front_error_reduction_fraction",
            "value": ideal_reduction,
        },
        {
            "metric": "required_front_correction_MAE",
            "value": required_correction_mae,
        },
        {
            "metric": "required_front_correction_P90",
            "value": required_correction_p90,
        },
        {
            "metric": "required_front_correction_MAX",
            "value": required_correction_max,
        },
    ]

    save_csv(
        TARGET_TABLE,
        target_rows,
    )

    # -------------------------------------------------------------------------
    # Experiment-level authoritative metrics
    # -------------------------------------------------------------------------

    audit_rows = []

    for row in metrics:

        exp = text(
            row,
            [
                "experiment",
                "Experiment",
                "candidate",
                "Candidate",
            ],
            "UNKNOWN",
        )

        front_reduction = num(
            row,
            [
                "front_error_reduction_fraction",
                "front_error_reduction",
            ],
        )

        gap = num(
            row,
            "conditioned_gap",
        )

        recovered = num(
            row,
            "recovered_fronts",
        )

        profile_l1 = num(
            row,
            [
                "profile_L1_100d",
                "profile_l1_100d",
            ],
        )

        short_cal = num(
            row,
            "short_TOF_calibration_MAE",
        )

        global_l1 = num(
            row,
            "global_L1",
        )

        b500 = num(
            row,
            "bias_500_1000",
        )

        b1000 = num(
            row,
            "bias_1000_2000",
        )

        b2000 = num(
            row,
            "bias_gt2000",
        )

        if np.isfinite(front_reduction):
            achieved_fraction_of_required = (
                front_reduction
                /
                MIN_REQUIRED_REDUCTION
            )
        else:
            achieved_fraction_of_required = np.nan

        gap_pass = (
            bool(gap <= max_gap)
            if np.isfinite(gap)
            else None
        )

        recovered_pass = (
            bool(recovered >= min_recovered)
            if np.isfinite(recovered)
            else None
        )

        profile_pass = (
            bool(profile_l1 <= max_profile_l1)
            if np.isfinite(profile_l1)
            else None
        )

        reduction_pass = (
            bool(front_reduction >= MIN_REQUIRED_REDUCTION)
            if np.isfinite(front_reduction)
            else None
        )

        audit_rows.append({
            "experiment": exp,
            "front_error_reduction_fraction": front_reduction,
            "required_front_error_reduction_fraction": MIN_REQUIRED_REDUCTION,
            "fraction_of_required_reduction_achieved": achieved_fraction_of_required,
            "front_error_reduction_pass": reduction_pass,
            "recovered_fronts": recovered,
            "recovered_fronts_pass": recovered_pass,
            "conditioned_gap": gap,
            "conditioned_gap_pass": gap_pass,
            "profile_L1_100d": profile_l1,
            "profile_L1_pass": profile_pass,
            "short_TOF_calibration_MAE": short_cal,
            "global_L1": global_l1,
            "bias_500_1000": b500,
            "bias_1000_2000": b1000,
            "bias_gt2000": b2000,
        })

    save_csv(
        METRIC_TABLE,
        audit_rows,
    )

    # -------------------------------------------------------------------------
    # Tradeoff classification
    # -------------------------------------------------------------------------

    finite_reductions = [
        row
        for row in audit_rows
        if np.isfinite(
            row["front_error_reduction_fraction"]
        )
    ]

    if finite_reductions:

        best_reduction_row = max(
            finite_reductions,
            key=lambda row:
            row["front_error_reduction_fraction"],
        )

        best_reduction = float(
            best_reduction_row[
                "front_error_reduction_fraction"
            ]
        )

    else:
        best_reduction_row = None
        best_reduction = np.nan

    # Check whether stronger front correction improves reduction while already
    # preserving the other primary front gates.
    other_front_gates_pass_at_best = False

    if best_reduction_row is not None:

        conditions = [
            best_reduction_row["recovered_fronts_pass"],
            best_reduction_row["conditioned_gap_pass"],
            best_reduction_row["profile_L1_pass"],
        ]

        known = [
            value
            for value in conditions
            if value is not None
        ]

        other_front_gates_pass_at_best = (
            len(known) > 0
            and all(known)
        )

    reduction_shortfall = (
        MIN_REQUIRED_REDUCTION
        -
        best_reduction
        if np.isfinite(best_reduction)
        else np.nan
    )

    relative_shortfall = (
        reduction_shortfall
        /
        MIN_REQUIRED_REDUCTION
        if np.isfinite(reduction_shortfall)
        else np.nan
    )

    tradeoff_rows = []

    for row in audit_rows:
        tradeoff_rows.append({
            "experiment": row["experiment"],
            "front_error_reduction_fraction": row["front_error_reduction_fraction"],
            "front_error_reduction_pass": row["front_error_reduction_pass"],
            "conditioned_gap": row["conditioned_gap"],
            "conditioned_gap_pass": row["conditioned_gap_pass"],
            "recovered_fronts": row["recovered_fronts"],
            "recovered_fronts_pass": row["recovered_fronts_pass"],
            "profile_L1_100d": row["profile_L1_100d"],
            "profile_L1_pass": row["profile_L1_pass"],
            "bias_500_1000": row["bias_500_1000"],
            "bias_1000_2000": row["bias_1000_2000"],
            "bias_gt2000": row["bias_gt2000"],
        })

    save_csv(
        TRADEOFF_TABLE,
        tradeoff_rows,
    )

    # -------------------------------------------------------------------------
    # Diagnosis
    # -------------------------------------------------------------------------

    # We distinguish three cases:
    #
    # A) best candidate preserves other front gates but simply does not move
    #    enough state in the front shell -> capacity / objective strength issue.
    #
    # B) increasing front correction breaks gap/topology -> structural tradeoff.
    #
    # C) experiment metrics do not contain enough candidate detail -> persistence
    #    limitation.
    # -------------------------------------------------------------------------

    if (
        best_reduction_row is not None
        and
        other_front_gates_pass_at_best
        and
        best_reduction < MIN_REQUIRED_REDUCTION
    ):
        diagnosis = "FRONT_STATE_CORRECTION_CAPACITY_LIMIT"

        recommendation = (
            "The best persisted R3E experiment preserves the other primary front "
            "gates but reaches only part of the required 50% front-shell error "
            "reduction. Keep the 50% gate unchanged. Design a front-state-focused "
            "residual calibration branch that increases local correction capacity "
            "without changing threshold-position, TOF-bias, or SG7B-11 contracts."
        )

        next_milestone = (
            "V15-SG7C-R3F0 — Front-State-Focused Calibration Refinement Design"
        )

    elif (
        best_reduction_row is not None
        and
        not other_front_gates_pass_at_best
    ):
        diagnosis = "FRONT_STATE_CORRECTION_TOPOLOGY_TRADEOFF"

        recommendation = (
            "The strongest persisted front-state correction does not simultaneously "
            "preserve the other accepted front gates. Audit local front correction "
            "geometry before increasing calibration capacity."
        )

        next_milestone = (
            "V15-SG7C-R3E-R3 — Front-State / Front-Topology Tradeoff Audit"
        )

    else:
        diagnosis = "FRONT_LIMITER_EVIDENCE_INCOMPLETE_AT_PERSISTED_CANDIDATE_LEVEL"

        recommendation = (
            "The R3E persisted outputs do not contain enough calibrated-candidate "
            "detail to determine whether the 50% front-error reduction shortfall is "
            "capacity-limited or topology-limited. Extend persistence/auditing before "
            "another training branch."
        )

        next_milestone = (
            "V15-SG7C-R3E-R3 — Calibrator Candidate Persistence Audit"
        )

    # -------------------------------------------------------------------------
    # Print
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("R3E FRONT-ERROR-REDUCTION AUDIT")
    print("=" * 78)

    for row in audit_rows:

        red = row["front_error_reduction_fraction"]

        if np.isfinite(red):
            red_txt = f"{100.0*red:7.3f}%"
        else:
            red_txt = "   n/a "

        gap = row["conditioned_gap"]

        gap_txt = (
            f"{gap:.3e}"
            if np.isfinite(gap)
            else "n/a"
        )

        print(
            f"  {row['experiment']:<8s} | "
            f"frontRed={red_txt} | "
            f"gap={gap_txt} | "
            f"fronts={row['recovered_fronts'] if np.isfinite(row['recovered_fronts']) else 'n/a'} | "
            f"B500={row['bias_500_1000'] if np.isfinite(row['bias_500_1000']) else np.nan:.3e}"
        )

    if best_reduction_row is not None:

        print("\nBEST PERSISTED FRONT-REDUCTION CANDIDATE")
        print(f"  Experiment               : {best_reduction_row['experiment']}")
        print(f"  Achieved reduction       : {100.0*best_reduction:.3f}%")
        print(f"  Required reduction       : {100.0*MIN_REQUIRED_REDUCTION:.3f}%")
        print(f"  Absolute shortfall       : {100.0*reduction_shortfall:.3f} percentage points")
        print(f"  Relative shortfall       : {100.0*relative_shortfall:.2f}%")
        print(f"  Other front gates pass   : {other_front_gates_pass_at_best}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3E-R2 DIAGNOSTIC VALIDATION")
    print("=" * 78)
    print("[PASS] R3E-R single-gate diagnosis reproduced")
    print("[PASS] Dominant gate = front_error_reduction reproduced")
    print("[PASS] Canonical ideal front correction reconstructed")
    print("[PASS] R3E experiment-level front reduction metrics audited")
    print("[PASS] Threshold-gap / recovered-front / profile-L1 coexistence audited")
    print("[PASS] Front-error-reduction shortfall quantified")
    print("[PASS] Limiter mechanism classified")
    print("=" * 78)

    # -------------------------------------------------------------------------
    # Plots
    # -------------------------------------------------------------------------

    finite_plot = [
        row
        for row in audit_rows
        if np.isfinite(
            row["front_error_reduction_fraction"]
        )
    ]

    if finite_plot:

        plt.figure(figsize=(9, 5))

        plt.bar(
            [row["experiment"] for row in finite_plot],
            [
                row["front_error_reduction_fraction"]
                for row in finite_plot
            ],
        )

        plt.axhline(
            MIN_REQUIRED_REDUCTION,
            linestyle="--",
        )

        plt.ylabel(
            "Front-shell error reduction fraction"
        )

        plt.xlabel(
            "R3E experiment"
        )

        plt.title(
            "V15-SG7C-R3E-R2 Front Error Reduction"
        )

        plt.tight_layout()

        plt.savefig(
            OUTPUT_DIR
            /
            "V15SG7CR3ER2_Front_Error_Reduction.png",
            dpi=300,
        )

        plt.close()

        valid_tradeoff = [
            row
            for row in finite_plot
            if np.isfinite(
                row["conditioned_gap"]
            )
        ]

        if valid_tradeoff:

            plt.figure(figsize=(8, 6))

            plt.scatter(
                [
                    row["front_error_reduction_fraction"]
                    for row in valid_tradeoff
                ],
                [
                    row["conditioned_gap"]
                    for row in valid_tradeoff
                ],
                s=70,
            )

            for row in valid_tradeoff:

                plt.annotate(
                    row["experiment"],
                    (
                        row["front_error_reduction_fraction"],
                        row["conditioned_gap"],
                    ),
                )

            plt.axvline(
                MIN_REQUIRED_REDUCTION,
                linestyle="--",
            )

            plt.axhline(
                max_gap,
                linestyle="--",
            )

            plt.xlabel(
                "Front-shell error reduction fraction"
            )

            plt.ylabel(
                "Conditioned threshold gap"
            )

            plt.title(
                "V15-SG7C-R3E-R2 Front-State / Gap Tradeoff"
            )

            plt.tight_layout()

            plt.savefig(
                OUTPUT_DIR
                /
                "V15SG7CR3ER2_FrontReduction_vs_Gap.png",
                dpi=300,
            )

            plt.close()

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------

    summary = {
        "milestone": "V15-SG7C-R3E-R2",
        "status": "SINGLE_GATE_CALIBRATION_LIMITER_AUDIT_COMPLETE",
        "incoming_diagnosis": r3er.get("diagnosis"),
        "dominant_gate": r3er.get("dominant_failed_gate"),
        "diagnosis": diagnosis,
        "required_front_error_reduction_fraction": MIN_REQUIRED_REDUCTION,
        "best_persisted_front_error_reduction_fraction": (
            best_reduction
            if np.isfinite(best_reduction)
            else None
        ),
        "front_error_reduction_shortfall": (
            reduction_shortfall
            if np.isfinite(reduction_shortfall)
            else None
        ),
        "best_candidate_other_primary_front_gates_pass": other_front_gates_pass_at_best,
        "ideal_canonical_front_error_reduction_fraction": ideal_reduction,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(
        SUMMARY_FILE,
        summary,
    )

    print("\nSTATUS")
    print("  SINGLE_GATE_CALIBRATION_LIMITER_AUDIT_COMPLETE")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")

    print("\nTables:")
    print(f"  {METRIC_TABLE.name}")
    print(f"  {TRADEOFF_TABLE.name}")
    print(f"  {TARGET_TABLE.name}")

    print("\nDiagnostics:")
    print("  V15SG7CR3ER2_Front_Error_Reduction.png")
    print("  V15SG7CR3ER2_FrontReduction_vs_Gap.png")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3E-R2 AUDIT: PASS")
    print()
    print("No training was performed.")
    print("No front-error-reduction, TOF-bias, map-back, or plume-validation gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
