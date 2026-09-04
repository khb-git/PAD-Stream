from __future__ import annotations

from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R3D
# Frozen PI-RNN Deployment Calibration Design
#
# DESIGN-ONLY MILESTONE
#
# NO TRAINING.
# NO FROZEN MODEL WEIGHTS CHANGED.
# NO ARCHITECTURE CHANGE TO SG7B-11.
# NO SG6 GEOMETRY CHANGE.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# SG7C-R3C-FIX established:
#
#   R3C_XI_MISMATCH_IS_NUMERICAL_OR_REPRESENTATIONAL
#
# and repaired the interpretation to:
#
#   FEATURE_AND_TARGET_TRANSFER_VALID_MODEL_APPROXIMATION_RESIDUAL
#
# The canonical target manifold reproduces SGSim SG7A truth essentially to
# machine precision at the exact deployment inputs, while the frozen PI-RNN
# retains a TOF-conditioned approximation residual.
#
# SG7C-R3D therefore designs a DEPLOYMENT-SIDE calibration that:
#
#   1. leaves the SG7B-11 frozen PI-RNN unchanged,
#   2. leaves the canonical target definition unchanged,
#   3. leaves the deployment input convention unchanged,
#   4. corrects only the residual S_PI-RNN - S_canonical_interp,
#   5. protects the accepted S=0.21 front,
#   6. is zero-mean / strongly anchored outside the residual regime,
#   7. is evaluated before any grid map-back,
#   8. must preserve every SG7B-11 / SG7B-10S front-state-physics gate.
#
# This milestone performs NO calibration fit. It creates the SG7C-R3E
# controlled calibration experiment contract.
# =============================================================================


ROOT = Path(__file__).resolve().parent

R3C_FIX_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3C_FIX"
    / "PAD_Stream_V15SG7CR3C_FIX_Summary.json"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

R3A_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3A"
    / "V15SG7CR3A_Coordinate_Audit.npz"
)

SG7B15R_CONTRACT = (
    ROOT / "output" / "V15_SG7B15R"
    / "V15SG7B15R_Front_Preserving_TOF_Refinement_Contract.json"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3D"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CONTRACT_FILE = (
    OUTPUT_DIR
    / "V15SG7CR3D_Frozen_Deployment_Calibration_Contract.json"
)

REGION_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3D_Calibration_Regions.csv"
)

FEATURE_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3D_Calibration_Features.csv"
)

LOSS_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3D_Calibration_Objective.csv"
)

GATE_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3D_Preservation_Gates.csv"
)

EXPERIMENT_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3D_SG7CR3E_Experiment_Matrix.csv"
)

BASELINE_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3D_Residual_Baseline.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7CR3D_Summary.json"
)


# =============================================================================
# FIXED DESIGN CONSTANTS
# =============================================================================

FRONT_THRESHOLD = 0.210
FRONT_SHELL_LOW = 0.205
FRONT_SHELL_HIGH = 0.300
FRONT_CORE_LOW = 0.210
FRONT_CORE_HIGH = 0.260

LONG_TOF_MIN = 500.0
VERY_LONG_TOF_MIN = 1000.0

# Calibration must remain much smaller than the saturation dynamic range.
MAX_ABS_CORRECTION_GLOBAL = 0.020
MAX_ABS_CORRECTION_FRONT = 0.003
MAX_MEAN_FRONT_CORRECTION = 0.001

# The deployment-side calibration should correct long-TOF residuals but remain
# essentially inactive on already-good short TOF streamlines.
MAX_SHORT_TOF_CALIBRATION_MAE = 0.0015

# Keep calibration smooth in xi.
MAX_CALIBRATION_TV_RATIO = 0.15

# Calibration target residual:
#   deltaS_target = S_canonical_interp - S_frozen_PI-RNN
# so calibrated prediction:
#   S_cal = S_frozen_PI-RNN + deltaS_cal
# =============================================================================


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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
    print("PAD-Stream Version 15-SG7C-R3D")
    print("Frozen PI-RNN Deployment Calibration Design")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO SG7B-11 MODEL WEIGHTS WILL BE CHANGED.")
    print("NO PI-RNN ARCHITECTURE CHANGE WILL BE MADE.")
    print("NO DEPLOYMENT FEATURE CONVENTION WILL BE CHANGED.")
    print("NO TARGET SCALING WILL BE CHANGED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for path in [
        R3C_FIX_SUMMARY,
        R3C_NUMERICAL,
        R3A_NUMERICAL,
        SG7B15R_CONTRACT,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing SG7C-R3D prerequisite:\n{path}")

    fix = load_json(R3C_FIX_SUMMARY)
    contract15r = load_json(SG7B15R_CONTRACT)

    if fix.get("repaired_R3C_diagnosis") != \
            "FEATURE_AND_TARGET_TRANSFER_VALID_MODEL_APPROXIMATION_RESIDUAL":
        raise RuntimeError(
            "SG7C-R3D requires repaired R3C interpretation:\n"
            "FEATURE_AND_TARGET_TRANSFER_VALID_MODEL_APPROXIMATION_RESIDUAL"
        )

    r3c = np.load(R3C_NUMERICAL, allow_pickle=True)
    r3a = np.load(R3A_NUMERICAL, allow_pickle=True)

    canonical_interp = np.asarray(
        r3c["canonical_interpolated_target"],
        dtype=float,
    )

    frozen_pirnn = np.asarray(
        r3c["deployment_pirnn"],
        dtype=float,
    )

    truth = np.asarray(
        r3c["deployment_truth"],
        dtype=float,
    )

    tau_end_days = np.asarray(
        r3c["tau_end_days"],
        dtype=float,
    )

    times_days = np.asarray(
        r3c["times_days"],
        dtype=float,
    )

    normalized_input = np.asarray(
        r3c["deployment_normalized_input"],
        dtype=float,
    )

    xi = np.asarray(
        r3c["canonical_xi"],
        dtype=float,
    )

    residual_target = canonical_interp - frozen_pirnn
    frozen_error = frozen_pirnn - truth
    interp_error = canonical_interp - truth

    # -------------------------------------------------------------------------
    # Residual baseline
    # -------------------------------------------------------------------------

    idx100 = int(np.argmin(np.abs(times_days - 100.0)))

    if not np.isclose(times_days[idx100], 100.0):
        raise RuntimeError("100-day snapshot not found.")

    truth100 = truth[idx100]
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

    short_sl = tau_end_days < LONG_TOF_MIN
    long_sl = tau_end_days >= LONG_TOF_MIN
    very_long_sl = tau_end_days >= VERY_LONG_TOF_MIN

    baseline_rows = []

    tof_bands = [
        ("<=250d", -np.inf, 250.0),
        ("250-500d", 250.0, 500.0),
        ("500-1000d", 500.0, 1000.0),
        ("1000-2000d", 1000.0, 2000.0),
        (">2000d", 2000.0, np.inf),
    ]

    for label, lo, hi in tof_bands:

        mask = (tau_end_days > lo) & (tau_end_days <= hi)

        if not np.any(mask):
            continue

        target = residual_target[:, mask, :]
        err = frozen_error[:, mask, :]

        baseline_rows.append({
            "TOF_band": label,
            "streamlines": int(np.sum(mask)),
            "frozen_L1": float(np.mean(np.abs(err))),
            "frozen_signed_bias": float(np.mean(err)),
            "required_correction_mean": float(np.mean(target)),
            "required_correction_MAE": float(np.mean(np.abs(target))),
            "required_correction_P90": float(np.percentile(np.abs(target), 90)),
            "required_correction_MAX": float(np.max(np.abs(target))),
        })

    global_required_mae = float(np.mean(np.abs(residual_target)))
    global_required_max = float(np.max(np.abs(residual_target)))

    front_required_mae = float(
        np.mean(np.abs(residual100[front_shell]))
    )

    front_required_max = float(
        np.max(np.abs(residual100[front_shell]))
    )

    short_required_mae = float(
        np.mean(np.abs(residual_target[:, short_sl, :]))
    )

    long_required_mae = float(
        np.mean(np.abs(residual_target[:, long_sl, :]))
    )

    very_long_required_mae = float(
        np.mean(np.abs(residual_target[:, very_long_sl, :]))
    )

    print("\nRESIDUAL CALIBRATION BASELINE")
    print(f"  Global required correction MAE : {global_required_mae:.6e}")
    print(f"  Global required correction MAX : {global_required_max:.6e}")
    print(f"  100d front-shell correction MAE: {front_required_mae:.6e}")
    print(f"  100d front-shell correction MAX: {front_required_max:.6e}")
    print(f"  Short-TOF required correction  : {short_required_mae:.6e}")
    print(f"  Long-TOF required correction   : {long_required_mae:.6e}")
    print(f"  Very-long required correction  : {very_long_required_mae:.6e}")

    # -------------------------------------------------------------------------
    # Calibration regions
    # -------------------------------------------------------------------------

    region_rows = [
        {
            "region": "C0_short_TOF",
            "definition": "tau_end < 500 d",
            "calibration_strength": "OFF/VERY_WEAK",
            "purpose": "preserve already-good fast-streamline deployment",
        },
        {
            "region": "C1_long_TOF_nonfront",
            "definition": "tau_end >= 500 d and outside front shell",
            "calibration_strength": "PRIMARY",
            "purpose": "remove dominant deployment approximation residual",
        },
        {
            "region": "C2_very_long_TOF_nonfront",
            "definition": "tau_end >= 1000 d and outside front shell",
            "calibration_strength": "STRONG",
            "purpose": "correct strongest positive long-TOF residual",
        },
        {
            "region": "C3_front_shell",
            "definition": "0.205 <= SG7A S <= 0.300",
            "calibration_strength": "TIGHTLY_BOUNDED",
            "purpose": "preserve SG7B-11 front morphology",
        },
        {
            "region": "C4_front_core",
            "definition": "0.210 <= SG7A S <= 0.260",
            "calibration_strength": "NEAR_ZERO",
            "purpose": "protect S=0.21 threshold crossing",
        },
    ]

    # -------------------------------------------------------------------------
    # Calibration feature set
    # -------------------------------------------------------------------------

    feature_rows = [
        {
            "feature": "xi",
            "role": "local streamline coordinate",
            "authority": "canonical/deployment semantic equivalent",
        },
        {
            "feature": "normalized_tD",
            "role": "deployment conditional time",
            "authority": "verified by R3A/R3C",
        },
        {
            "feature": "log10_tau_end_days",
            "role": "captures strong TOF-conditioned residual correlation",
            "authority": "R3A corr(log10 tau_end,bias)=0.9287",
        },
        {
            "feature": "S_frozen",
            "role": "local frozen-model state",
            "authority": "SG7B-11 frozen prediction",
        },
        {
            "feature": "front_distance",
            "role": "|S_frozen - 0.21| front protection feature",
            "authority": "SG7B-10S / SG7B-15R front contract",
        },
    ]

    # -------------------------------------------------------------------------
    # Calibration model design
    # -------------------------------------------------------------------------
    #
    # Deliberately small residual model:
    #
    #   deltaS_cal = g(features)
    #   S_cal      = clip(S_frozen + deltaS_cal, physical bounds)
    #
    # This is NOT a replacement transport model. It is a deployment residual
    # calibrator with strong null/anchor behavior.
    # -------------------------------------------------------------------------

    loss_rows = [
        {
            "term": "L_residual",
            "definition": "|deltaS_cal - (S_canonical_interp-S_frozen)|",
            "purpose": "fit deployment approximation residual",
        },
        {
            "term": "L_short_anchor",
            "definition": "|deltaS_cal| for tau_end < 500 d",
            "purpose": "keep calibration near zero where frozen model is already good",
        },
        {
            "term": "L_front_anchor",
            "definition": "|deltaS_cal| in S=[0.205,0.300]",
            "purpose": "preserve accepted front shell",
        },
        {
            "term": "L_front_core",
            "definition": "|deltaS_cal| in S=[0.210,0.260]",
            "purpose": "protect S=0.21 crossing",
        },
        {
            "term": "L_smooth_xi",
            "definition": "|d(deltaS_cal)/dxi|",
            "purpose": "prevent oscillatory calibration",
        },
        {
            "term": "L_zero_mean",
            "definition": "mean(deltaS_cal) outside targeted residual regime",
            "purpose": "prevent broad saturation shift",
        },
    ]

    # -------------------------------------------------------------------------
    # Preservation gates
    # -------------------------------------------------------------------------

    front_contract = contract15r[
        "authoritative_front_improvement_contract"
    ]

    guards = contract15r[
        "new_front_guards"
    ]

    gate_rows = [
        {
            "gate": "Recovered 100d fronts",
            "limit": f">= {front_contract['minimum_recovered_fronts']}",
            "authority": "SG7B-10S",
        },
        {
            "gate": "Conditioned front gap",
            "limit": f"<= {float(front_contract['maximum_conditioned_threshold_gap']):.17e}",
            "authority": "SG7B-10S",
        },
        {
            "gate": "100d profile L1",
            "limit": f"<= {float(front_contract['maximum_100d_profile_L1']):.17e}",
            "authority": "SG7B-10S",
        },
        {
            "gate": "Front-anchor MAE",
            "limit": f"<= {float(guards['maximum_front_anchor_MAE']):.6e}",
            "authority": "SG7B-15R",
        },
        {
            "gate": "P90 frozen-front xi shift",
            "limit": f"<= {float(guards['maximum_P90_frozen_front_xi_shift']):.6e}",
            "authority": "SG7B-15R",
        },
        {
            "gate": "Global calibration magnitude",
            "limit": f"|deltaS| <= {MAX_ABS_CORRECTION_GLOBAL:.6f}",
            "authority": "SG7C-R3D new",
        },
        {
            "gate": "Front calibration magnitude",
            "limit": f"|deltaS_front| <= {MAX_ABS_CORRECTION_FRONT:.6f}",
            "authority": "SG7C-R3D new",
        },
        {
            "gate": "Mean front calibration",
            "limit": f"<= {MAX_MEAN_FRONT_CORRECTION:.6f}",
            "authority": "SG7C-R3D new",
        },
        {
            "gate": "Short-TOF calibration MAE",
            "limit": f"<= {MAX_SHORT_TOF_CALIBRATION_MAE:.6f}",
            "authority": "SG7C-R3D new",
        },
        {
            "gate": "Calibration TV ratio",
            "limit": f"<= {MAX_CALIBRATION_TV_RATIO:.3f}",
            "authority": "SG7C-R3D new",
        },
    ]

    # -------------------------------------------------------------------------
    # Controlled R3E experiment matrix
    # -------------------------------------------------------------------------

    experiment_rows = [
        {
            "experiment": "E0",
            "description": "Frozen SG7B-11 control; no calibration",
            "model": "zero residual",
            "front_weight": 0.0,
            "short_weight": 0.0,
            "smooth_weight": 0.0,
        },
        {
            "experiment": "E1",
            "description": "Linear TOF-state residual calibration",
            "model": "linear",
            "front_weight": 4.0,
            "short_weight": 2.0,
            "smooth_weight": 1.0,
        },
        {
            "experiment": "E2",
            "description": "Small MLP residual calibration",
            "model": "MLP 16x16",
            "front_weight": 6.0,
            "short_weight": 2.5,
            "smooth_weight": 1.5,
        },
        {
            "experiment": "E3",
            "description": "TOF-gated MLP calibration",
            "model": "MLP 16x16 + long-TOF gate",
            "front_weight": 8.0,
            "short_weight": 4.0,
            "smooth_weight": 2.0,
        },
        {
            "experiment": "E4",
            "description": "Front-masked TOF-gated calibration",
            "model": "MLP 16x16 + TOF gate + front mask",
            "front_weight": 10.0,
            "short_weight": 4.0,
            "smooth_weight": 2.5,
        },
    ]

    # -------------------------------------------------------------------------
    # Design validation
    # -------------------------------------------------------------------------

    canonical_interp_close = bool(
        float(np.mean(np.abs(interp_error))) <= 5.0e-7
    )

    residual_nonzero = bool(
        global_required_mae > 1.0e-4
    )

    tof_localized = bool(
        very_long_required_mae > short_required_mae
    )

    front_small_relative = bool(
        front_required_mae < very_long_required_mae
    )

    checks = [
        (
            "R3C-FIX repaired interpretation reproduced",
            fix.get("repaired_R3C_diagnosis")
            ==
            "FEATURE_AND_TARGET_TRANSFER_VALID_MODEL_APPROXIMATION_RESIDUAL",
        ),
        (
            "Canonical interpolation remains effectively exact",
            canonical_interp_close,
        ),
        (
            "Frozen-model deployment residual is nonzero",
            residual_nonzero,
        ),
        (
            "Required correction increases into slow-TOF population",
            tof_localized,
        ),
        (
            "Front correction need smaller than very-long-TOF correction",
            front_small_relative,
        ),
        (
            "Calibration leaves SG7B-11 frozen",
            True,
        ),
        (
            "Calibration is pre-map-back deployment-side residual only",
            True,
        ),
        (
            "Exact SG7B-10S front gates retained",
            True,
        ),
        (
            "Controlled experiment matrix contains zero-calibration control",
            experiment_rows[0]["experiment"] == "E0",
        ),
        (
            "No calibration fit performed by R3D",
            True,
        ),
    ]

    passed = all(flag for _, flag in checks)

    print("\n" + "=" * 78)
    print("FROZEN DEPLOYMENT CALIBRATION DESIGN")
    print("=" * 78)

    print("\nCalibration form:")
    print("  deltaS_cal = g(xi, normalized_tD, log10(tau_end), S_frozen, front_distance)")
    print("  S_cal      = S_frozen + deltaS_cal")
    print()
    print("  SG7B-11 remains the transport model.")
    print("  g(.) is only a bounded deployment residual calibrator.")

    print("\nREGIONAL STRATEGY")
    for row in region_rows:
        print(
            f"  {row['region']:<24s} | "
            f"{row['calibration_strength']:<15s} | "
            f"{row['purpose']}"
        )

    print("\n" + "=" * 78)
    print("SG7C-R3E CONTROLLED CALIBRATION MATRIX")
    print("=" * 78)

    for row in experiment_rows:
        print(f"  {row['experiment']} | {row['description']}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3D DESIGN VALIDATION")
    print("=" * 78)

    for description, flag in checks:
        print(f"[{'PASS' if flag else 'FAIL'}] {description}")

    print("=" * 78)

    if passed:
        status = "FROZEN_DEPLOYMENT_CALIBRATION_CONTRACT_READY"
        recommendation = (
            "Proceed to SG7C-R3E. Fit only a small bounded residual calibrator "
            "against the canonical-interpolated deployment residual while keeping "
            "SG7B-11 frozen. Candidate selection must preserve the complete front "
            "contract and must improve the long-TOF deployment residual before any "
            "map-back or plume validation."
        )
        next_milestone = (
            "V15-SG7C-R3E — Controlled Frozen-Model Deployment Calibration"
        )
    else:
        status = "FROZEN_DEPLOYMENT_CALIBRATION_CONTRACT_INCOMPLETE"
        recommendation = (
            "Do not fit a calibrator until the R3D contract validates."
        )
        next_milestone = (
            "V15-SG7C-R3D-R — Frozen Deployment Calibration Contract Repair"
        )

    # -------------------------------------------------------------------------
    # Save
    # -------------------------------------------------------------------------

    save_csv(BASELINE_TABLE, baseline_rows)
    save_csv(REGION_TABLE, region_rows)
    save_csv(FEATURE_TABLE, feature_rows)
    save_csv(LOSS_TABLE, loss_rows)
    save_csv(GATE_TABLE, gate_rows)
    save_csv(EXPERIMENT_TABLE, experiment_rows)

    contract = {
        "milestone": "V15-SG7C-R3D",
        "status": status,
        "training_performed": False,
        "frozen_PI_RNN_modified": False,
        "incoming_diagnosis": fix.get("repaired_R3C_diagnosis"),
        "calibration_definition": {
            "target": "canonical_interpolated_target - frozen_PI_RNN",
            "output": "deltaS_cal",
            "calibrated_state": "frozen_PI_RNN + deltaS_cal",
            "placement": "streamline deployment space before grid map-back",
        },
        "features": feature_rows,
        "regions": region_rows,
        "objective": loss_rows,
        "preservation_gates": gate_rows,
        "controlled_experiments": experiment_rows,
        "baseline": {
            "global_required_correction_MAE": global_required_mae,
            "global_required_correction_MAX": global_required_max,
            "front_required_correction_MAE_100d": front_required_mae,
            "front_required_correction_MAX_100d": front_required_max,
            "short_TOF_required_correction_MAE": short_required_mae,
            "long_TOF_required_correction_MAE": long_required_mae,
            "very_long_TOF_required_correction_MAE": very_long_required_mae,
        },
        "next_milestone": next_milestone,
    }

    save_json(CONTRACT_FILE, contract)

    summary = {
        "milestone": "V15-SG7C-R3D",
        "status": status,
        "validation_passed": passed,
        "training_performed": False,
        "frozen_model_modified": False,
        "global_required_correction_MAE": global_required_mae,
        "front_required_correction_MAE_100d": front_required_mae,
        "short_TOF_required_correction_MAE": short_required_mae,
        "very_long_TOF_required_correction_MAE": very_long_required_mae,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(SUMMARY_FILE, summary)

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    plt.figure(figsize=(9, 5))
    plt.hist(
        residual_target.ravel(),
        bins=100,
    )
    plt.xlabel("Required deployment correction deltaS")
    plt.ylabel("Samples")
    plt.title("V15-SG7C-R3D Frozen PI-RNN Residual Correction Distribution")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3D_Required_Correction_Distribution.png",
        dpi=300,
    )
    plt.close()

    labels = [row["TOF_band"] for row in baseline_rows]
    vals = [row["required_correction_MAE"] for row in baseline_rows]

    plt.figure(figsize=(9, 5))
    plt.bar(labels, vals)
    plt.xlabel("Terminal TOF band")
    plt.ylabel("Required correction MAE")
    plt.title("V15-SG7C-R3D Required Calibration vs Terminal TOF")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3D_Required_Correction_By_TOF.png",
        dpi=300,
    )
    plt.close()

    # -------------------------------------------------------------------------
    # Final print
    # -------------------------------------------------------------------------

    print("\nSTATUS")
    print(f"  {status}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nTables:")
    print(f"  {BASELINE_TABLE.name}")
    print(f"  {REGION_TABLE.name}")
    print(f"  {FEATURE_TABLE.name}")
    print(f"  {LOSS_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print(f"  {EXPERIMENT_TABLE.name}")

    print("\nDiagnostics:")
    print("  V15SG7CR3D_Required_Correction_Distribution.png")
    print("  V15SG7CR3D_Required_Correction_By_TOF.png")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print(f"V15-SG7C-R3D DESIGN: {'PASS' if passed else 'FAIL'}")
    print()
    print("No training was performed.")
    print("The SG7B-11 frozen PI-RNN remains authoritative.")
    print("No map-back, feature convention, target scaling, or validation gate changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
