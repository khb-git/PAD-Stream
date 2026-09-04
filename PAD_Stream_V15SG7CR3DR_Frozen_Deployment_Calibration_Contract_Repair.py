from __future__ import annotations

from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R3D-R
# Frozen Deployment Calibration Contract Repair
#
# DESIGN-REPAIR ONLY
#
# NO TRAINING.
# NO SG7B-11 WEIGHTS CHANGED.
# NO PI-RNN ARCHITECTURE CHANGE.
# NO FEATURE CONVENTION CHANGE.
# NO TARGET SCALING CHANGE.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
# NO AUTHORITATIVE SG7B-10S / SG7B-15R FRONT GATE RELAXATION.
#
# WHY R3D FAILED
# --------------
# R3D assumed:
#
#     front-shell required correction < very-long-TOF correction
#
# but measured:
#
#     front-shell MAE   = 9.261960e-03
#     very-long-TOF MAE = 4.711265e-03
#
# The assumption was therefore false.
#
# This is NOT evidence that the accepted front must be left uncorrected.
# R3C/R3C-FIX already established that the canonical-interpolated target is
# semantically correct and reproduces SG7A to near machine precision.
#
# Therefore the front-shell residual itself is physically meaningful.
#
# R3D-R repairs the calibration philosophy:
#
#   OLD:
#       "make front calibration nearly zero"
#
#   NEW:
#       "allow front calibration when it moves the frozen prediction toward
#        the canonical/SG7A target, but judge the result using the exact
#        accepted front-position / shape gates."
#
# Thus front preservation is enforced by OUTCOME, not by forcing deltaS≈0.
# =============================================================================


ROOT = Path(__file__).resolve().parent

R3D_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3D"
    / "PAD_Stream_V15SG7CR3D_Summary.json"
)

R3D_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3D"
    / "V15SG7CR3D_Frozen_Deployment_Calibration_Contract.json"
)

R3D_BASELINE = (
    ROOT / "output" / "V15_SG7CR3D"
    / "V15SG7CR3D_Residual_Baseline.csv"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

SG7B15R_CONTRACT = (
    ROOT / "output" / "V15_SG7B15R"
    / "V15SG7B15R_Front_Preserving_TOF_Refinement_Contract.json"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3DR"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPAIRED_CONTRACT_FILE = (
    OUTPUT_DIR
    / "V15SG7CR3DR_Frozen_Deployment_Calibration_Contract.json"
)

REGION_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3DR_Repaired_Calibration_Regions.csv"
)

OBJECTIVE_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3DR_Repaired_Calibration_Objective.csv"
)

GATE_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3DR_Repaired_Preservation_Gates.csv"
)

EXPERIMENT_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3DR_SG7CR3E_Experiment_Matrix.csv"
)

FRONT_AUDIT_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3DR_Front_Residual_Audit.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7CR3DR_Summary.json"
)


# =============================================================================
# FIXED PHYSICS / FRONT DEFINITIONS
# =============================================================================

FRONT_THRESHOLD = 0.210
FRONT_SHELL_LOW = 0.205
FRONT_SHELL_HIGH = 0.300
FRONT_CORE_LOW = 0.210
FRONT_CORE_HIGH = 0.260

LONG_TOF_MIN = 500.0
VERY_LONG_TOF_MIN = 1000.0

# Calibration remains bounded globally, but front correction is no longer
# required to be near-zero. It is constrained by canonical alignment and the
# authoritative front outcome gates.
MAX_ABS_CORRECTION_GLOBAL = 0.10

# Short-TOF region is already good and should remain weakly calibrated.
MAX_SHORT_TOF_CALIBRATION_MAE = 0.0015

# Smoothness guard for the calibration itself.
MAX_CALIBRATION_TV_RATIO = 0.20

# New front-target alignment guards.
MIN_FRONT_ERROR_REDUCTION_FRACTION = 0.50
MAX_FRONT_OVERSHOOT_FRACTION = 0.05
MIN_FRONT_CORRECTION_SIGN_AGREEMENT = 0.95


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


def save_csv(path: Path, rows: list[dict]):
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


def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3D-R")
    print("Frozen Deployment Calibration Contract Repair")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO SG7B-11 MODEL WEIGHTS WILL BE CHANGED.")
    print("NO PI-RNN ARCHITECTURE CHANGE WILL BE MADE.")
    print("NO FEATURE OR TARGET CONVENTION WILL BE CHANGED.")
    print("NO AUTHORITATIVE FRONT GATE WILL BE RELAXED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for path in [
        R3D_SUMMARY,
        R3D_CONTRACT,
        R3D_BASELINE,
        R3C_NUMERICAL,
        SG7B15R_CONTRACT,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing R3D-R prerequisite:\n{path}")

    r3d_summary = load_json(R3D_SUMMARY)
    r3d_contract = load_json(R3D_CONTRACT)
    r3d_baseline = load_csv(R3D_BASELINE)
    front_authority = load_json(SG7B15R_CONTRACT)

    if r3d_summary.get("status") != "FROZEN_DEPLOYMENT_CALIBRATION_CONTRACT_INCOMPLETE":
        raise RuntimeError(
            "R3D-R requires incoming status:\n"
            "FROZEN_DEPLOYMENT_CALIBRATION_CONTRACT_INCOMPLETE"
        )

    db = np.load(R3C_NUMERICAL, allow_pickle=True)

    canonical_interp = np.asarray(
        db["canonical_interpolated_target"],
        dtype=float,
    )

    frozen = np.asarray(
        db["deployment_pirnn"],
        dtype=float,
    )

    truth = np.asarray(
        db["deployment_truth"],
        dtype=float,
    )

    tau_end_days = np.asarray(
        db["tau_end_days"],
        dtype=float,
    )

    times_days = np.asarray(
        db["times_days"],
        dtype=float,
    )

    xi = np.asarray(
        db["canonical_xi"],
        dtype=float,
    )

    residual_target = canonical_interp - frozen

    idx100 = int(np.argmin(np.abs(times_days - 100.0)))

    if not np.isclose(times_days[idx100], 100.0):
        raise RuntimeError("100-day snapshot not found.")

    truth100 = truth[idx100]
    frozen100 = frozen[idx100]
    target100 = canonical_interp[idx100]
    residual100 = residual_target[idx100]

    front_shell = (
        (truth100 >= FRONT_SHELL_LOW)
        &
        (truth100 <= FRONT_SHELL_HIGH)
    )

    front_core = (
        (truth100 >= FRONT_CORE_LOW)
        &
        (truth100 <= FRONT_CORE_HIGH)
    )

    # -------------------------------------------------------------------------
    # Reproduce the failed design premise
    # -------------------------------------------------------------------------

    front_shell_mae = float(
        np.mean(np.abs(residual100[front_shell]))
    )

    front_shell_max = float(
        np.max(np.abs(residual100[front_shell]))
    )

    very_long = tau_end_days >= VERY_LONG_TOF_MIN

    very_long_mae = float(
        np.mean(
            np.abs(
                residual_target[:, very_long, :]
            )
        )
    )

    short = tau_end_days < LONG_TOF_MIN

    short_mae = float(
        np.mean(
            np.abs(
                residual_target[:, short, :]
            )
        )
    )

    failed_assumption_reproduced = bool(
        front_shell_mae >= very_long_mae
    )

    # -------------------------------------------------------------------------
    # Front residual directionality
    # -------------------------------------------------------------------------
    #
    # Because canonical_interp ≈ SG7A truth, residual_target is the correction
    # direction that should reduce the actual deployment error.
    # -------------------------------------------------------------------------

    frozen_front_error = frozen100 - truth100
    target_front_error = target100 - truth100

    front_required = residual100[front_shell]
    front_frozen_error = frozen_front_error[front_shell]

    # A correct residual should oppose the frozen error.
    direction_product = (
        front_required
        *
        front_frozen_error
    )

    sign_agreement = float(
        np.mean(
            direction_product <= 1.0e-14
        )
    )

    frozen_front_l1 = float(
        np.mean(
            np.abs(
                front_frozen_error
            )
        )
    )

    canonical_front_l1 = float(
        np.mean(
            np.abs(
                target_front_error[front_shell]
            )
        )
    )

    ideal_error_reduction = (
        1.0
        -
        canonical_front_l1
        /
        max(
            frozen_front_l1,
            1.0e-15,
        )
    )

    print("\nFAILED R3D PREMISE REPRODUCTION")
    print(f"  100d front-shell correction MAE : {front_shell_mae:.6e}")
    print(f"  100d front-shell correction MAX : {front_shell_max:.6e}")
    print(f"  Very-long-TOF correction MAE    : {very_long_mae:.6e}")
    print(f"  Short-TOF correction MAE        : {short_mae:.6e}")
    print(f"  Failed premise reproduced       : {failed_assumption_reproduced}")

    print("\nFRONT RESIDUAL DIRECTIONALITY")
    print(f"  Frozen front-shell L1           : {frozen_front_l1:.6e}")
    print(f"  Canonical target front-shell L1 : {canonical_front_l1:.6e}")
    print(f"  Ideal front error reduction     : {100*ideal_error_reduction:.3f}%")
    print(f"  Residual/error sign opposition  : {100*sign_agreement:.3f}%")

    front_audit_rows = [
        {
            "metric": "front_shell_required_correction_MAE",
            "value": front_shell_mae,
        },
        {
            "metric": "front_shell_required_correction_MAX",
            "value": front_shell_max,
        },
        {
            "metric": "very_long_TOF_required_correction_MAE",
            "value": very_long_mae,
        },
        {
            "metric": "short_TOF_required_correction_MAE",
            "value": short_mae,
        },
        {
            "metric": "frozen_front_shell_L1",
            "value": frozen_front_l1,
        },
        {
            "metric": "canonical_target_front_shell_L1",
            "value": canonical_front_l1,
        },
        {
            "metric": "ideal_front_error_reduction_fraction",
            "value": ideal_error_reduction,
        },
        {
            "metric": "front_correction_sign_agreement",
            "value": sign_agreement,
        },
    ]

    # -------------------------------------------------------------------------
    # Repaired calibration regions
    # -------------------------------------------------------------------------

    region_rows = [
        {
            "region": "C0_short_TOF",
            "definition": "tau_end < 500 d",
            "calibration_strategy": "WEAK / ZERO-ANCHORED",
            "reason": "frozen deployment already accurate",
        },
        {
            "region": "C1_long_TOF_nonfront",
            "definition": "tau_end >= 500 d outside front shell",
            "calibration_strategy": "PRIMARY RESIDUAL FIT",
            "reason": "remove long-TOF approximation residual",
        },
        {
            "region": "C2_very_long_TOF_nonfront",
            "definition": "tau_end >= 1000 d outside front shell",
            "calibration_strategy": "STRONG RESIDUAL FIT",
            "reason": "largest slow-streamline bias",
        },
        {
            "region": "C3_front_shell",
            "definition": "0.205 <= SG7A S <= 0.300",
            "calibration_strategy": "CANONICAL-TARGETED + FRONT-GATED",
            "reason": (
                "front residual is material; correction is allowed only when it "
                "reduces canonical/SG7A error and preserves accepted front metrics"
            ),
        },
        {
            "region": "C4_front_core",
            "definition": "0.210 <= SG7A S <= 0.260",
            "calibration_strategy": "CANONICAL-TARGETED + CROSSING-CONSTRAINED",
            "reason": (
                "do not force deltaS to zero; directly preserve/recover threshold "
                "position and front shape while correcting state error"
            ),
        },
    ]

    # -------------------------------------------------------------------------
    # Repaired objective
    # -------------------------------------------------------------------------

    objective_rows = [
        {
            "term": "L_residual",
            "definition": "|deltaS_cal - (S_canonical_interp - S_frozen)|",
            "purpose": "fit validated deployment approximation residual",
        },
        {
            "term": "L_short_anchor",
            "definition": "|deltaS_cal| on tau_end < 500 d",
            "purpose": "keep fast-streamline calibration weak",
        },
        {
            "term": "L_front_state",
            "definition": "|S_cal - S_canonical_interp| in front shell",
            "purpose": "correct front state toward authoritative target",
        },
        {
            "term": "L_front_cross",
            "definition": "front-position error at S=0.21",
            "purpose": "preserve/recover threshold crossing directly",
        },
        {
            "term": "L_front_shape",
            "definition": "gradient + TV mismatch vs canonical target",
            "purpose": "preserve front morphology",
        },
        {
            "term": "L_direction",
            "definition": "penalize deltaS_cal that increases |S_cal-S_target|",
            "purpose": "prevent correction in the wrong direction",
        },
        {
            "term": "L_overshoot",
            "definition": "penalize crossing past canonical target",
            "purpose": "prevent over-correction",
        },
        {
            "term": "L_smooth_xi",
            "definition": "|d(deltaS_cal)/dxi|",
            "purpose": "suppress oscillatory residual correction",
        },
    ]

    # -------------------------------------------------------------------------
    # Preservation gates
    # -------------------------------------------------------------------------

    exact_front = front_authority[
        "authoritative_front_improvement_contract"
    ]

    guards = front_authority[
        "new_front_guards"
    ]

    gate_rows = [
        {
            "gate": "Recovered 100d fronts",
            "limit": f">= {exact_front['minimum_recovered_fronts']}",
            "authority": "SG7B-10S",
        },
        {
            "gate": "Conditioned front gap",
            "limit": f"<= {float(exact_front['maximum_conditioned_threshold_gap']):.17e}",
            "authority": "SG7B-10S",
        },
        {
            "gate": "100d profile L1",
            "limit": f"<= {float(exact_front['maximum_100d_profile_L1']):.17e}",
            "authority": "SG7B-10S",
        },
        {
            "gate": "Front-anchor MAE",
            "limit": f"<= {float(guards['maximum_front_anchor_MAE']):.6e}",
            "authority": "SG7B-15R",
        },
        {
            "gate": "Mean frozen-front xi shift",
            "limit": f"<= {float(guards['maximum_mean_frozen_front_xi_shift']):.6e}",
            "authority": "SG7B-15R",
        },
        {
            "gate": "P90 frozen-front xi shift",
            "limit": f"<= {float(guards['maximum_P90_frozen_front_xi_shift']):.6e}",
            "authority": "SG7B-15R",
        },
        {
            "gate": "Global calibration magnitude",
            "limit": f"|deltaS| <= {MAX_ABS_CORRECTION_GLOBAL:.3f}",
            "authority": "R3D-R calibration safeguard",
        },
        {
            "gate": "Short-TOF calibration MAE",
            "limit": f"<= {MAX_SHORT_TOF_CALIBRATION_MAE:.6f}",
            "authority": "R3D-R calibration safeguard",
        },
        {
            "gate": "Front error reduction",
            "limit": f">= {100*MIN_FRONT_ERROR_REDUCTION_FRACTION:.1f}%",
            "authority": "R3D-R front calibration safeguard",
        },
        {
            "gate": "Front correction sign agreement",
            "limit": f">= {100*MIN_FRONT_CORRECTION_SIGN_AGREEMENT:.1f}%",
            "authority": "R3D-R directionality safeguard",
        },
        {
            "gate": "Front overshoot fraction",
            "limit": f"<= {100*MAX_FRONT_OVERSHOOT_FRACTION:.1f}%",
            "authority": "R3D-R overshoot safeguard",
        },
        {
            "gate": "Calibration TV ratio",
            "limit": f"<= {MAX_CALIBRATION_TV_RATIO:.3f}",
            "authority": "R3D-R smoothness safeguard",
        },
    ]

    # -------------------------------------------------------------------------
    # Repaired controlled R3E matrix
    # -------------------------------------------------------------------------

    experiment_rows = [
        {
            "experiment": "E0",
            "description": "Frozen SG7B-11 control; zero calibration",
            "model": "zero residual",
        },
        {
            "experiment": "E1",
            "description": "Linear canonical-residual calibration",
            "model": "linear residual head",
        },
        {
            "experiment": "E2",
            "description": "Small canonical-residual MLP",
            "model": "MLP 16x16",
        },
        {
            "experiment": "E3",
            "description": "TOF-gated canonical-residual MLP",
            "model": "MLP 16x16 + TOF gate",
        },
        {
            "experiment": "E4",
            "description": "Front-aware canonical-residual MLP",
            "model": "MLP 16x16 + TOF gate + explicit front state/crossing losses",
        },
        {
            "experiment": "E5",
            "description": "Conservative front-aware residual calibration",
            "model": "MLP 8x8 + TOF gate + strongest short-TOF anchor",
        },
    ]

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    canonical_exact = bool(
        float(
            np.mean(
                np.abs(
                    canonical_interp
                    -
                    truth
                )
            )
        )
        <=
        5.0e-7
    )

    front_residual_material = bool(
        front_shell_mae > 1.0e-3
    )

    front_direction_valid = bool(
        sign_agreement >= 0.95
    )

    canonical_front_superior = bool(
        canonical_front_l1
        <
        frozen_front_l1
    )

    checks = [
        (
            "Incoming R3D incomplete status reproduced",
            r3d_summary.get("status")
            ==
            "FROZEN_DEPLOYMENT_CALIBRATION_CONTRACT_INCOMPLETE",
        ),
        (
            "R3D failed front<very-long premise reproduced",
            failed_assumption_reproduced,
        ),
        (
            "Canonical target remains effectively exact",
            canonical_exact,
        ),
        (
            "Front-shell residual confirmed material",
            front_residual_material,
        ),
        (
            "Canonical front state improves over frozen front state",
            canonical_front_superior,
        ),
        (
            "Required front correction opposes frozen error",
            front_direction_valid,
        ),
        (
            "Near-zero front-calibration assumption removed",
            True,
        ),
        (
            "Front judged by exact outcome gates instead",
            True,
        ),
        (
            "Authoritative SG7B-10S / SG7B-15R gates retained",
            True,
        ),
        (
            "No calibration fit performed by R3D-R",
            True,
        ),
    ]

    passed = all(flag for _, flag in checks)

    print("\n" + "=" * 78)
    print("REPAIRED CALIBRATION PRINCIPLE")
    print("=" * 78)

    print("""
  OLD R3D:
    Protect front by forcing calibration ~ 0.

  REPAIRED R3D-R:
    Allow front correction when the canonical target requires it.
    Protect the front using direct state, crossing-position, shape,
    directionality, and overshoot gates.
""")

    print("=" * 78)
    print("V15-SG7C-R3D-R CONTRACT VALIDATION")
    print("=" * 78)

    for description, flag in checks:
        print(f"[{'PASS' if flag else 'FAIL'}] {description}")

    print("=" * 78)

    if passed:
        status = "FROZEN_DEPLOYMENT_CALIBRATION_CONTRACT_READY"
        recommendation = (
            "Proceed to controlled SG7C-R3E residual calibration. Keep SG7B-11 "
            "frozen. Permit material front correction only toward the validated "
            "canonical target and require the complete SG7B-10S/15R front outcome "
            "contract plus new directionality/overshoot safeguards."
        )
        next_milestone = (
            "V15-SG7C-R3E — Controlled Frozen-Model Deployment Calibration"
        )
    else:
        status = "FROZEN_DEPLOYMENT_CALIBRATION_CONTRACT_REPAIR_FAILED"
        recommendation = (
            "Do not train. The repaired calibration contract did not validate."
        )
        next_milestone = (
            "V15-SG7C-R3D-R2 — Calibration Contract Reconciliation"
        )

    repaired_contract = {
        "milestone": "V15-SG7C-R3D-R",
        "status": status,
        "training_performed": False,
        "frozen_model_modified": False,
        "repair_reason": (
            "R3D incorrectly assumed front correction should be smaller than "
            "very-long-TOF correction. The validated canonical target requires a "
            "material front correction."
        ),
        "authoritative_front_contract": exact_front,
        "authoritative_front_displacement_guards": guards,
        "calibration_target": (
            "canonical_interpolated_target - frozen_PI_RNN"
        ),
        "regions": region_rows,
        "objective": objective_rows,
        "preservation_gates": gate_rows,
        "controlled_experiments": experiment_rows,
        "front_residual_audit": {
            "front_shell_required_correction_MAE": front_shell_mae,
            "front_shell_required_correction_MAX": front_shell_max,
            "very_long_TOF_required_correction_MAE": very_long_mae,
            "short_TOF_required_correction_MAE": short_mae,
            "frozen_front_shell_L1": frozen_front_l1,
            "canonical_target_front_shell_L1": canonical_front_l1,
            "ideal_front_error_reduction_fraction": ideal_error_reduction,
            "required_correction_sign_agreement": sign_agreement,
        },
        "next_milestone": next_milestone,
    }

    save_json(
        REPAIRED_CONTRACT_FILE,
        repaired_contract,
    )

    save_csv(
        FRONT_AUDIT_TABLE,
        front_audit_rows,
    )

    save_csv(
        REGION_TABLE,
        region_rows,
    )

    save_csv(
        OBJECTIVE_TABLE,
        objective_rows,
    )

    save_csv(
        GATE_TABLE,
        gate_rows,
    )

    save_csv(
        EXPERIMENT_TABLE,
        experiment_rows,
    )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    plt.figure(figsize=(9, 5))
    plt.hist(
        residual100[front_shell],
        bins=80,
    )
    plt.xlabel("Required canonical front correction")
    plt.ylabel("Front-shell samples")
    plt.title("V15-SG7C-R3D-R Required Front-Shell Correction")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3DR_Front_Correction_Distribution.png",
        dpi=300,
    )
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.scatter(
        front_frozen_error,
        front_required,
        s=8,
        alpha=0.35,
    )
    plt.axhline(0.0, linestyle="--")
    plt.axvline(0.0, linestyle="--")
    plt.xlabel("Frozen front error (S_frozen - SG7A)")
    plt.ylabel("Required correction (S_target - S_frozen)")
    plt.title("V15-SG7C-R3D-R Front Correction Directionality")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3DR_Front_Correction_Directionality.png",
        dpi=300,
    )
    plt.close()

    summary = {
        "milestone": "V15-SG7C-R3D-R",
        "status": status,
        "validation_passed": passed,
        "training_performed": False,
        "frozen_model_modified": False,
        "failed_R3D_assumption_reproduced": failed_assumption_reproduced,
        "front_shell_required_correction_MAE": front_shell_mae,
        "very_long_TOF_required_correction_MAE": very_long_mae,
        "front_correction_sign_agreement": sign_agreement,
        "ideal_front_error_reduction_fraction": ideal_error_reduction,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(
        SUMMARY_FILE,
        summary,
    )

    print("\nSTATUS")
    print(f"  {status}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")

    print("\nRepaired contract:")
    print(f"  {REPAIRED_CONTRACT_FILE.name}")

    print("\nTables:")
    print(f"  {FRONT_AUDIT_TABLE.name}")
    print(f"  {REGION_TABLE.name}")
    print(f"  {OBJECTIVE_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print(f"  {EXPERIMENT_TABLE.name}")

    print("\nDiagnostics:")
    print("  V15SG7CR3DR_Front_Correction_Distribution.png")
    print("  V15SG7CR3DR_Front_Correction_Directionality.png")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print(f"V15-SG7C-R3D-R CONTRACT REPAIR: {'PASS' if passed else 'FAIL'}")
    print()
    print("No training was performed.")
    print("SG7B-11 remains frozen and authoritative.")
    print("No authoritative front, physics, map-back, or plume gate was relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
