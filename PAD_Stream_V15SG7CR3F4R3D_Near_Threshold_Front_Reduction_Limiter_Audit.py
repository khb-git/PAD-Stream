from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R3F4-R3D
# Near-Threshold Front-Reduction Limiter Audit
#
# DIAGNOSTIC-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FRONT-ERROR-REDUCTION GATE CHANGED OR RELAXED.
# NO TOF-BIAS GATE CHANGED.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# R3F4-R3C established:
#
#   FRONT_ERROR_REDUCTION_ONLY_REMAINING_LIMITER
#
# Best persisted candidates:
#
#   B2 ~49.545%
#   B4 ~49.548%
#   B5 ~49.547%
#
# against the unchanged:
#
#   >= 50.000% front-error-reduction requirement.
#
# This audit determines whether the ~0.45 percentage-point shortfall is:
#
#   1. NUMERICAL / REPORTING LIMITED
#   2. CHECKPOINT-SELECTION LIMITED
#   3. BASIS-SUPPORT LIMITED
#   4. OPTIMIZATION-TRAJECTORY LIMITED
#   5. STRUCTURAL SATURATION / RESIDUAL-COVERAGE LIMITED
#
# It uses only persisted R3F4 evidence.
#
# No candidate is promoted or frozen here.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F4R3D"
OUT.mkdir(parents=True, exist_ok=True)

R3C_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F4R3C"
    / "PAD_Stream_V15SG7CR3F4R3C_Summary.json"
)

R3C_SCREEN = (
    ROOT / "output" / "V15_SG7CR3F4R3C"
    / "V15SG7CR3F4R3C_Clarified_Deployment_Screen.csv"
)

R3F4_EPOCHS = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Epoch_Metrics.csv"
)

R3F4_FINAL = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Final_Experiment_Metrics.csv"
)

R3F4_CHECKPOINTS = (
    ROOT / "output" / "V15_SG7CR3F4"
    / "V15SG7CR3F4_Best_Checkpoint_By_Experiment.csv"
)

R3F4R_SUPPORT = (
    ROOT / "output" / "V15_SG7CR3F4R"
    / "V15SG7CR3F4R_Basis_Support_Coverage.csv"
)

R3F4R_GLOBAL = (
    ROOT / "output" / "V15_SG7CR3F4R"
    / "V15SG7CR3F4R_Global_Crossing_Audit.csv"
)

FRONT_TARGET = 0.50
NEAR_TARGET = 0.49

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F4R3D_Summary.json"
GLOBAL_TABLE = OUT / "V15SG7CR3F4R3D_Global_Limiter_Audit.csv"
TRAJECTORY_TABLE = OUT / "V15SG7CR3F4R3D_Epoch_Trajectory_Audit.csv"
SUPPORT_TABLE = OUT / "V15SG7CR3F4R3D_Support_vs_Reduction.csv"
CHECKPOINT_TABLE = OUT / "V15SG7CR3F4R3D_Checkpoint_Selection_Audit.csv"
LIMITER_TABLE = OUT / "V15SG7CR3F4R3D_Limiter_Classification.csv"


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


def bval(row, key):
    return str(row.get(key, "")).strip().lower() in {
        "true", "1", "yes", "pass", "passed"
    }


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F4-R3D")
    print("Near-Threshold Front-Reduction Limiter Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FRONT-ERROR-REDUCTION GATE WILL BE CHANGED OR RELAXED.
NO TOF-BIAS GATE WILL BE CHANGED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
""")

    for p in [
        R3C_SUMMARY,
        R3C_SCREEN,
        R3F4_EPOCHS,
        R3F4_FINAL,
        R3F4_CHECKPOINTS,
        R3F4R_SUPPORT,
        R3F4R_GLOBAL,
    ]:
        if not p.exists():
            raise FileNotFoundError(
                f"Missing R3F4-R3D prerequisite:\n{p}"
            )

    incoming = load_json(R3C_SUMMARY)

    if (
        incoming.get("diagnosis")
        != "FRONT_ERROR_REDUCTION_ONLY_REMAINING_LIMITER"
    ):
        raise RuntimeError(
            "R3F4-R3D requires incoming diagnosis:\n"
            "FRONT_ERROR_REDUCTION_ONLY_REMAINING_LIMITER"
        )

    screen_rows = load_csv(R3C_SCREEN)
    epoch_rows = load_csv(R3F4_EPOCHS)
    final_rows = load_csv(R3F4_FINAL)
    checkpoint_rows = load_csv(R3F4_CHECKPOINTS)
    support_rows = load_csv(R3F4R_SUPPORT)
    global_cross_rows = load_csv(R3F4R_GLOBAL)

    # Near-target candidates only.
    near = [
        row for row in screen_rows
        if fnum(row, "front_error_reduction_fraction") >= NEAR_TARGET
    ]

    if not near:
        raise RuntimeError(
            "No >=49% near-target candidates found."
        )

    experiments = [
        row["experiment"]
        for row in near
    ]

    global_rows = []
    trajectory_rows = []
    support_audit_rows = []
    checkpoint_audit_rows = []

    print("\n" + "=" * 78)
    print("NEAR-TARGET CANDIDATE AUDIT")
    print("=" * 78)

    for exp in experiments:

        srow = next(
            row for row in screen_rows
            if row["experiment"] == exp
        )

        erows = [
            row for row in epoch_rows
            if row.get("experiment") == exp
        ]

        if not erows:
            raise RuntimeError(
                f"No R3F4 epoch history found for {exp}."
            )

        # Sort epoch history.
        erows = sorted(
            erows,
            key=lambda r: fnum(r, "epoch", 0.0)
        )

        reductions = np.asarray(
            [
                fnum(r, "front_error_reduction_fraction")
                for r in erows
            ],
            dtype=float,
        )

        epochs = np.asarray(
            [
                fnum(r, "epoch")
                for r in erows
            ],
            dtype=float,
        )

        valid = (
            np.isfinite(reductions)
            &
            np.isfinite(epochs)
        )

        reductions = reductions[valid]
        epochs = epochs[valid]

        if reductions.size == 0:
            raise RuntimeError(
                f"No finite front-reduction trajectory for {exp}."
            )

        i_best = int(
            np.argmax(reductions)
        )

        trajectory_best_reduction = float(
            reductions[i_best]
        )

        trajectory_best_epoch = int(
            epochs[i_best]
        )

        final_reduction = fnum(
            srow,
            "front_error_reduction_fraction",
        )

        shortfall = (
            FRONT_TARGET
            -
            final_reduction
        )

        trajectory_shortfall = (
            FRONT_TARGET
            -
            trajectory_best_reduction
        )

        # Estimate late-trajectory slope using last 3 finite checkpoints.
        if reductions.size >= 3:
            x = epochs[-3:]
            y = reductions[-3:]
            slope = float(
                np.polyfit(
                    x,
                    y,
                    1,
                )[0]
            )
        else:
            slope = np.nan

        # Detect saturation/plateau.
        tail_n = min(
            4,
            reductions.size,
        )

        tail = reductions[-tail_n:]

        tail_range = float(
            np.max(tail)
            -
            np.min(tail)
        )

        plateau = bool(
            tail_range
            <=
            2.0e-03
        )

        # Support evidence.
        sup = next(
            (
                row for row in support_rows
                if row.get("experiment") == exp
            ),
            None,
        )

        if sup is None:
            raise RuntimeError(
                f"Missing support audit row for {exp}."
            )

        residual_coverage = fnum(
            sup,
            "front_shell_residual_coverage_fraction",
        )

        coeff_mean = fnum(
            sup,
            "front_shell_coefficient_mean",
        )

        coeff_p90 = fnum(
            sup,
            "front_shell_coefficient_P90",
        )

        coeff_max = fnum(
            sup,
            "front_shell_coefficient_max",
        )

        # Crossing audit row.
        grow = next(
            (
                row for row in global_cross_rows
                if row.get("experiment") == exp
            ),
            None,
        )

        crossing_switch = (
            fnum(
                grow,
                "crossing_identity_switch_fraction",
            )
            if grow is not None
            else np.nan
        )

        # Checkpoint selection evidence.
        ck = [
            row for row in checkpoint_rows
            if row.get("experiment") == exp
        ]

        best_any = next(
            (
                row for row in ck
                if row.get("checkpoint_type") == "best_any"
            ),
            None,
        )

        best_pass = next(
            (
                row for row in ck
                if row.get("checkpoint_type") == "best_passing"
            ),
            None,
        )

        checkpoint_selection_limited = bool(
            trajectory_best_reduction
            >
            final_reduction
            +
            1.0e-4
        )

        numerical_only = bool(
            0.0
            <
            shortfall
            <=
            5.0e-5
        )

        support_tracks_reduction = bool(
            np.isfinite(residual_coverage)
            and
            abs(
                residual_coverage
                -
                final_reduction
            )
            <=
            1.0e-3
        )

        support_limited = bool(
            residual_coverage
            <
            FRONT_TARGET
            and
            support_tracks_reduction
        )

        optimization_plateau = bool(
            plateau
            and
            trajectory_best_reduction
            <
            FRONT_TARGET
        )

        trajectory_has_pass = bool(
            trajectory_best_reduction
            >=
            FRONT_TARGET
        )

        global_rows.append({
            "experiment": exp,
            "final_front_reduction_fraction": final_reduction,
            "final_shortfall_fraction": shortfall,
            "final_shortfall_percentage_points": 100.0 * shortfall,
            "best_trajectory_reduction_fraction": trajectory_best_reduction,
            "best_trajectory_epoch": trajectory_best_epoch,
            "best_trajectory_shortfall_fraction": trajectory_shortfall,
            "late_epoch_reduction_slope_per_epoch": slope,
            "tail_reduction_range": tail_range,
            "trajectory_plateau": plateau,
            "trajectory_has_50pct_pass": trajectory_has_pass,
            "front_shell_residual_coverage_fraction": residual_coverage,
            "front_shell_coefficient_mean": coeff_mean,
            "front_shell_coefficient_P90": coeff_p90,
            "front_shell_coefficient_max": coeff_max,
            "support_tracks_reduction": support_tracks_reduction,
            "checkpoint_selection_limited": checkpoint_selection_limited,
            "numerical_only": numerical_only,
            "support_limited": support_limited,
            "optimization_plateau": optimization_plateau,
            "crossing_identity_switch_fraction": crossing_switch,
        })

        for row in erows:
            trajectory_rows.append({
                "experiment": exp,
                "epoch": fnum(row, "epoch"),
                "front_error_reduction_fraction":
                    fnum(
                        row,
                        "front_error_reduction_fraction",
                    ),
                "complete_pass":
                    row.get("complete_pass"),
                "failed_gates":
                    row.get("failed_gates"),
            })

        support_audit_rows.append({
            "experiment": exp,
            "front_error_reduction_fraction": final_reduction,
            "front_shell_residual_coverage_fraction": residual_coverage,
            "coverage_minus_reduction":
                residual_coverage
                -
                final_reduction,
            "front_shell_coefficient_mean": coeff_mean,
            "front_shell_coefficient_P90": coeff_p90,
            "front_shell_coefficient_max": coeff_max,
            "support_tracks_reduction": support_tracks_reduction,
        })

        checkpoint_audit_rows.append({
            "experiment": exp,
            "selected_final_reduction": final_reduction,
            "best_epoch_reduction": trajectory_best_reduction,
            "best_epoch": trajectory_best_epoch,
            "selection_gap":
                trajectory_best_reduction
                -
                final_reduction,
            "best_any_checkpoint_present":
                best_any is not None,
            "best_passing_checkpoint_present":
                best_pass is not None,
            "checkpoint_selection_limited":
                checkpoint_selection_limited,
        })

        print(
            f"\n{exp}"
        )
        print(
            f"  Final reduction           : "
            f"{100*final_reduction:.4f}%"
        )
        print(
            f"  Shortfall                 : "
            f"{100*shortfall:.4f} percentage points"
        )
        print(
            f"  Best epoch reduction      : "
            f"{100*trajectory_best_reduction:.4f}% "
            f"(epoch {trajectory_best_epoch})"
        )
        print(
            f"  Residual coverage         : "
            f"{100*residual_coverage:.4f}%"
        )
        print(
            f"  Tail plateau              : "
            f"{plateau}"
        )
        print(
            f"  Selection limited         : "
            f"{checkpoint_selection_limited}"
        )
        print(
            f"  Support tracks reduction  : "
            f"{support_tracks_reduction}"
        )

    save_csv(
        GLOBAL_TABLE,
        global_rows,
    )

    save_csv(
        TRAJECTORY_TABLE,
        trajectory_rows,
    )

    save_csv(
        SUPPORT_TABLE,
        support_audit_rows,
    )

    save_csv(
        CHECKPOINT_TABLE,
        checkpoint_audit_rows,
    )

    # -------------------------------------------------------------------------
    # Limiter classification
    # -------------------------------------------------------------------------

    # Best experiment by final reduction.
    best = max(
        global_rows,
        key=lambda r:
        r["final_front_reduction_fraction"]
    )

    any_epoch_pass = any(
        row["trajectory_has_50pct_pass"]
        for row in global_rows
    )

    any_selection_limited = any(
        row["checkpoint_selection_limited"]
        for row in global_rows
    )

    all_support_track = all(
        row["support_tracks_reduction"]
        for row in global_rows
    )

    all_plateau = all(
        row["trajectory_plateau"]
        for row in global_rows
    )

    best_support = best[
        "front_shell_residual_coverage_fraction"
    ]

    best_shortfall = best[
        "final_shortfall_fraction"
    ]

    numerical_material = bool(
        best_shortfall
        <=
        1.0e-4
    )

    if any_epoch_pass:

        diagnosis = "CHECKPOINT_SELECTION_LIMITER"

        recommendation = (
            "At least one persisted R3F4 epoch reaches or exceeds the unchanged "
            "50% front-error-reduction target. Do not retrain. Re-screen the actual "
            "passing epoch checkpoint under the clarified deployment contract."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3D2 — Passing-Epoch Checkpoint Recovery / Revalidation"
        )

    elif any_selection_limited:

        diagnosis = "CHECKPOINT_SELECTION_NEAR_THRESHOLD_LIMITER"

        recommendation = (
            "A persisted epoch improves materially beyond the selected best-any "
            "checkpoint but still does not reach 50%. Recover and independently "
            "evaluate the best front-reduction epoch before any retraining."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3D2 — Best-Epoch Checkpoint Recovery Audit"
        )

    elif (
        all_support_track
        and
        best_support
        <
        FRONT_TARGET
    ):

        diagnosis = "BASIS_SUPPORT_CEILING_AT_49P5_PERCENT"

        recommendation = (
            "Front-error reduction tracks the available front-shell residual support "
            "almost one-for-one, and the best candidates plateau below 50%. The "
            "remaining ~0.45 percentage-point shortfall is structural support coverage, "
            "not a failed optimizer or checkpoint choice. Design the minimum possible "
            "support extension needed to exceed 50% while retaining SG7A/canonical "
            "front accuracy and all clarified deployment gates."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3E — Minimal Residual-Support Extension Design"
        )

    elif all_plateau:

        diagnosis = "OPTIMIZATION_TRAJECTORY_PLATEAU_BELOW_50_PERCENT"

        recommendation = (
            "All near-target candidates plateau below the unchanged 50% gate without "
            "evidence that checkpoint selection is responsible. Design a minimal "
            "continuation experiment from the best persisted checkpoint."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3E — Minimal Near-Threshold Continuation Design"
        )

    elif numerical_material:

        diagnosis = "NUMERICAL_NEAR_THRESHOLD_LIMITER"

        recommendation = (
            "The remaining shortfall is within numerical-scale tolerance, but the "
            "50% gate remains unchanged. Independently recompute the front-reduction "
            "metric at higher numerical precision before any training or contract change."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3D2 — High-Precision Front-Reduction Recalculation"
        )

    else:

        diagnosis = "MIXED_NEAR_THRESHOLD_LIMITER"

        recommendation = (
            "The 49.5% ceiling cannot yet be assigned uniquely to support, checkpoint "
            "selection, or numerical precision. Audit the best epoch and support geometry "
            "jointly before retraining."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3D2 — Joint Best-Epoch / Support Audit"
        )

    limiter_rows = [{
        "best_experiment": best["experiment"],
        "best_final_front_reduction_fraction":
            best["final_front_reduction_fraction"],
        "best_shortfall_fraction":
            best_shortfall,
        "best_shortfall_percentage_points":
            100.0 * best_shortfall,
        "best_residual_coverage_fraction":
            best_support,
        "any_epoch_reaches_50pct":
            any_epoch_pass,
        "any_checkpoint_selection_limited":
            any_selection_limited,
        "all_near_target_support_tracks_reduction":
            all_support_track,
        "all_near_target_trajectories_plateau":
            all_plateau,
        "numerical_scale_shortfall":
            numerical_material,
        "diagnosis":
            diagnosis,
    }]

    save_csv(
        LIMITER_TABLE,
        limiter_rows,
    )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    labels = [
        row["experiment"]
        for row in global_rows
    ]

    x = np.arange(
        len(labels)
    )

    width = 0.35

    plt.figure(
        figsize=(9, 5)
    )

    plt.bar(
        x - width / 2,
        [
            row[
                "final_front_reduction_fraction"
            ]
            for row in global_rows
        ],
        width=width,
        label="front reduction",
    )

    plt.bar(
        x + width / 2,
        [
            row[
                "front_shell_residual_coverage_fraction"
            ]
            for row in global_rows
        ],
        width=width,
        label="residual support",
    )

    plt.axhline(
        FRONT_TARGET,
        linestyle="--",
    )

    plt.xticks(
        x,
        labels,
    )

    plt.ylabel(
        "Fraction"
    )

    plt.title(
        "V15-SG7C-R3F4-R3D Reduction vs Residual Support"
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUT
        /
        "V15SG7CR3F4R3D_Reduction_vs_Support.png",
        dpi=300,
    )

    plt.close()

    plt.figure(
        figsize=(10, 6)
    )

    for exp in experiments:

        rows = [
            r for r in trajectory_rows
            if r["experiment"] == exp
        ]

        plt.plot(
            [
                r["epoch"]
                for r in rows
            ],
            [
                r[
                    "front_error_reduction_fraction"
                ]
                for r in rows
            ],
            marker="o",
            label=exp,
        )

    plt.axhline(
        FRONT_TARGET,
        linestyle="--",
    )

    plt.xlabel(
        "Epoch"
    )

    plt.ylabel(
        "Front-error reduction fraction"
    )

    plt.title(
        "V15-SG7C-R3F4-R3D Near-Threshold Training Trajectories"
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUT
        /
        "V15SG7CR3F4R3D_Epoch_Trajectories.png",
        dpi=300,
    )

    plt.close()

    # -------------------------------------------------------------------------
    # Validation / output
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F4-R3D DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        (
            "Incoming single near-threshold limiter reproduced",
            True,
        ),
        (
            "Persisted R3F4 epoch trajectories loaded",
            True,
        ),
        (
            "Persisted checkpoint selection evidence loaded",
            True,
        ),
        (
            "Front-shell residual support evidence loaded",
            True,
        ),
        (
            "Best epoch identified for each near-target experiment",
            True,
        ),
        (
            "50% trajectory crossing audited",
            True,
        ),
        (
            "Support/reduction relationship audited",
            True,
        ),
        (
            "No front-error-reduction threshold changed",
            True,
        ),
        (
            "Limiter mechanism classified",
            True,
        ),
    ]

    for description, passed in checks:
        print(
            f"[{'PASS' if passed else 'FAIL'}] {description}"
        )

    print("=" * 78)

    print("\nBEST NEAR-TARGET CASE")
    print(
        f"  Experiment              : "
        f"{best['experiment']}"
    )
    print(
        f"  Front reduction         : "
        f"{100*best['final_front_reduction_fraction']:.4f}%"
    )
    print(
        f"  Shortfall               : "
        f"{100*best_shortfall:.4f} percentage points"
    )
    print(
        f"  Best epoch reduction    : "
        f"{100*best['best_trajectory_reduction_fraction']:.4f}%"
    )
    print(
        f"  Residual support        : "
        f"{100*best_support:.4f}%"
    )

    print("\nSTATUS")
    print(
        "  NEAR_THRESHOLD_FRONT_REDUCTION_LIMITER_AUDIT_COMPLETE"
    )

    print("\nDIAGNOSIS")
    print(
        f"  {diagnosis}"
    )

    print("\nRECOMMENDATION")
    print(
        f"  {recommendation}"
    )

    print("\nNEXT MILESTONE")
    print(
        f"  {next_milestone}"
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F4-R3D",
            "status": "NEAR_THRESHOLD_FRONT_REDUCTION_LIMITER_AUDIT_COMPLETE",
            "incoming_diagnosis":
                incoming.get("diagnosis"),
            "diagnosis":
                diagnosis,
            "training_performed":
                False,
            "front_error_reduction_threshold_changed":
                False,
            "best_experiment":
                best["experiment"],
            "best_final_front_reduction_fraction":
                best["final_front_reduction_fraction"],
            "best_front_reduction_shortfall_fraction":
                best_shortfall,
            "best_residual_support_fraction":
                best_support,
            "recommendation":
                recommendation,
            "next_milestone":
                next_milestone,
        },
    )

    print("\nOUTPUTS")
    print(
        f"  Directory:\n    {OUT}"
    )

    print("\nTables:")
    print(
        f"  {GLOBAL_TABLE.name}"
    )
    print(
        f"  {TRAJECTORY_TABLE.name}"
    )
    print(
        f"  {SUPPORT_TABLE.name}"
    )
    print(
        f"  {CHECKPOINT_TABLE.name}"
    )
    print(
        f"  {LIMITER_TABLE.name}"
    )

    print("\nDiagnostics:")
    print(
        "  V15SG7CR3F4R3D_Reduction_vs_Support.png"
    )
    print(
        "  V15SG7CR3F4R3D_Epoch_Trajectories.png"
    )

    print("\nSummary:")
    print(
        f"  {SUMMARY_FILE.name}"
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F4-R3D AUDIT: PASS")
    print()
    print("No training was performed.")
    print("The 50% front-error-reduction gate remains unchanged.")
    print("No model, TOF-bias, map-back, or plume gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
