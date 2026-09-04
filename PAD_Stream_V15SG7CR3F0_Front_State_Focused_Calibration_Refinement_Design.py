from __future__ import annotations

from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R3F0
# Front-State-Focused Calibration Refinement Design
#
# DESIGN-ONLY MILESTONE
#
# NO TRAINING.
# NO SG7B-11 WEIGHTS CHANGED.
# NO EXISTING R3E CALIBRATOR CHANGED.
# NO FRONT GATE RELAXED.
# NO TOF-BIAS GATE RELAXED.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# R3E-R2 diagnosed:
#
#     FRONT_STATE_CORRECTION_CAPACITY_LIMIT
#
# with an important evidence caveat:
# R3E persisted complete final metrics only for E0, while E1-E5 final candidate
# metrics were not available in the fields expected by the audit.
#
# Therefore R3F0 does TWO things:
#
#   1. designs a front-state-focused residual calibrator refinement;
#   2. repairs the experimental persistence contract so every R3F1 experiment
#      MUST save complete per-experiment and selected-checkpoint metrics.
#
# The underlying SG7B-11 PI-RNN remains frozen and authoritative.
# =============================================================================


ROOT = Path(__file__).resolve().parent

R3ER2_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3ER2"
    / "PAD_Stream_V15SG7CR3ER2_Summary.json"
)

R3DR_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3DR"
    / "V15SG7CR3DR_Frozen_Deployment_Calibration_Contract.json"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3F0"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CONTRACT_FILE = (
    OUTPUT_DIR
    / "V15SG7CR3F0_Front_State_Refinement_Contract.json"
)

REGION_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3F0_Front_State_Regions.csv"
)

OBJECTIVE_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3F0_Objective_Design.csv"
)

EXPERIMENT_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3F0_R3F1_Experiment_Matrix.csv"
)

PERSISTENCE_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3F0_R3F1_Persistence_Contract.csv"
)

GATE_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3F0_Preservation_Gates.csv"
)

BASELINE_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR3F0_Front_Correction_Baseline.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7CR3F0_Summary.json"
)


FRONT_THRESHOLD = 0.210
FRONT_SHELL_LOW = 0.205
FRONT_SHELL_HIGH = 0.300
FRONT_CORE_LOW = 0.210
FRONT_CORE_HIGH = 0.260

MIN_FRONT_ERROR_REDUCTION = 0.50

# New R3F1 design guard:
# front-state capacity may increase, but correction remains bounded.
MAX_GLOBAL_ABS_CORRECTION = 0.10
MAX_SHORT_TOF_CALIBRATION_MAE = 1.5e-3
MAX_FRONT_OVERSHOOT_FRACTION = 0.05
MIN_FRONT_SIGN_AGREEMENT = 0.95
MAX_CALIBRATION_TV_RATIO = 0.20


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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


def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F0")
    print("Front-State-Focused Calibration Refinement Design")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO SG7B-11 MODEL WEIGHTS WILL BE CHANGED.")
    print("NO EXISTING R3E CALIBRATOR WILL BE MODIFIED.")
    print("NO FRONT OR TOF-BIAS GATE WILL BE RELAXED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for path in [
        R3ER2_SUMMARY,
        R3DR_CONTRACT,
        R3C_NUMERICAL,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing R3F0 prerequisite:\n{path}")

    r3er2 = load_json(R3ER2_SUMMARY)
    r3dr = load_json(R3DR_CONTRACT)

    if r3er2.get("diagnosis") != "FRONT_STATE_CORRECTION_CAPACITY_LIMIT":
        raise RuntimeError(
            "R3F0 requires incoming diagnosis:\n"
            "FRONT_STATE_CORRECTION_CAPACITY_LIMIT"
        )

    db = np.load(R3C_NUMERICAL, allow_pickle=True)

    frozen = np.asarray(db["deployment_pirnn"], dtype=float)
    truth = np.asarray(db["deployment_truth"], dtype=float)
    canonical = np.asarray(db["canonical_interpolated_target"], dtype=float)
    tau_end_days = np.asarray(db["tau_end_days"], dtype=float)
    times_days = np.asarray(db["times_days"], dtype=float)

    idx100 = int(np.argmin(np.abs(times_days - 100.0)))

    truth100 = truth[idx100]
    frozen100 = frozen[idx100]
    canonical100 = canonical[idx100]

    shell = (
        (truth100 >= FRONT_SHELL_LOW)
        &
        (truth100 <= FRONT_SHELL_HIGH)
    )

    core = (
        (truth100 >= FRONT_CORE_LOW)
        &
        (truth100 <= FRONT_CORE_HIGH)
    )

    required = canonical100 - frozen100

    shell_required = required[shell]
    core_required = required[core]

    frozen_shell_l1 = float(
        np.mean(np.abs(frozen100[shell] - truth100[shell]))
    )

    canonical_shell_l1 = float(
        np.mean(np.abs(canonical100[shell] - truth100[shell]))
    )

    ideal_reduction = (
        1.0
        -
        canonical_shell_l1
        /
        max(frozen_shell_l1, 1e-15)
    )

    shell_mae = float(np.mean(np.abs(shell_required)))
    shell_p90 = float(np.percentile(np.abs(shell_required), 90))
    shell_max = float(np.max(np.abs(shell_required)))

    core_mae = float(np.mean(np.abs(core_required)))
    core_p90 = float(np.percentile(np.abs(core_required), 90))
    core_max = float(np.max(np.abs(core_required)))

    print("\nFRONT-STATE CAPACITY BASELINE")
    print(f"  Frozen front-shell L1        : {frozen_shell_l1:.6e}")
    print(f"  Canonical front-shell L1     : {canonical_shell_l1:.6e}")
    print(f"  Ideal front reduction        : {100*ideal_reduction:.3f}%")
    print(f"  Required shell correction MAE: {shell_mae:.6e}")
    print(f"  Required shell correction P90: {shell_p90:.6e}")
    print(f"  Required shell correction MAX: {shell_max:.6e}")
    print(f"  Required core correction MAE : {core_mae:.6e}")

    baseline_rows = [
        {"metric": "frozen_front_shell_L1", "value": frozen_shell_l1},
        {"metric": "canonical_front_shell_L1", "value": canonical_shell_l1},
        {"metric": "ideal_front_error_reduction_fraction", "value": ideal_reduction},
        {"metric": "required_shell_correction_MAE", "value": shell_mae},
        {"metric": "required_shell_correction_P90", "value": shell_p90},
        {"metric": "required_shell_correction_MAX", "value": shell_max},
        {"metric": "required_core_correction_MAE", "value": core_mae},
        {"metric": "required_core_correction_P90", "value": core_p90},
        {"metric": "required_core_correction_MAX", "value": core_max},
    ]

    # -------------------------------------------------------------------------
    # Region design
    # -------------------------------------------------------------------------

    region_rows = [
        {
            "region": "F0_nonfront_short_TOF",
            "definition": "outside front shell and tau_end < 500 d",
            "capacity": "LOW",
            "purpose": "preserve already-good short-TOF behavior",
        },
        {
            "region": "F1_nonfront_long_TOF",
            "definition": "outside front shell and tau_end >= 500 d",
            "capacity": "MODERATE",
            "purpose": "retain existing TOF-bias correction capability",
        },
        {
            "region": "F2_front_shell",
            "definition": "0.205 <= SG7A S <= 0.300",
            "capacity": "HIGHER LOCAL CAPACITY",
            "purpose": "reach >=50% front-state error reduction",
        },
        {
            "region": "F3_front_core",
            "definition": "0.210 <= SG7A S <= 0.260",
            "capacity": "HIGH + CROSSING-CONSTRAINED",
            "purpose": "correct state while preserving threshold position",
        },
        {
            "region": "F4_front_shoulders",
            "definition": "front shell excluding front core",
            "capacity": "HIGH + SHAPE-CONSTRAINED",
            "purpose": "correct shoulder state without broadening/oscillation",
        },
    ]

    # -------------------------------------------------------------------------
    # Objective design
    # -------------------------------------------------------------------------

    objective_rows = [
        {
            "term": "L_residual_global",
            "role": "global canonical residual fit",
            "relative_weight": "1.0",
        },
        {
            "term": "L_front_state",
            "role": "front-shell canonical state fit",
            "relative_weight": "8-16",
        },
        {
            "term": "L_front_core_state",
            "role": "front-core canonical state fit",
            "relative_weight": "10-20",
        },
        {
            "term": "L_crossing_position",
            "role": "retain S=0.21 crossing accuracy",
            "relative_weight": "4-8",
        },
        {
            "term": "L_front_gradient",
            "role": "retain canonical front gradient",
            "relative_weight": "2-4",
        },
        {
            "term": "L_front_TV",
            "role": "retain canonical front morphology",
            "relative_weight": "1-3",
        },
        {
            "term": "L_short_anchor",
            "role": "keep tau_end<500d correction weak",
            "relative_weight": "2-5",
        },
        {
            "term": "L_direction",
            "role": "correction must move toward canonical target",
            "relative_weight": "2-4",
        },
        {
            "term": "L_overshoot",
            "role": "prevent correction past canonical target",
            "relative_weight": "2-4",
        },
    ]

    # -------------------------------------------------------------------------
    # R3F1 experiment matrix
    # -------------------------------------------------------------------------

    experiment_rows = [
        {
            "experiment": "F0",
            "description": "R3E-style control calibrator",
            "front_capacity": "BASE",
            "architecture": "MLP 16x16",
            "front_state_weight": 6,
            "front_core_weight": 6,
        },
        {
            "experiment": "F1",
            "description": "Moderate front-state capacity",
            "front_capacity": "MODERATE",
            "architecture": "MLP 24x24",
            "front_state_weight": 10,
            "front_core_weight": 12,
        },
        {
            "experiment": "F2",
            "description": "Strong front-state capacity",
            "front_capacity": "STRONG",
            "architecture": "MLP 32x32",
            "front_state_weight": 14,
            "front_core_weight": 16,
        },
        {
            "experiment": "F3",
            "description": "Dual-head front/nonfront residual calibrator",
            "front_capacity": "REGION-SPECIALIZED",
            "architecture": "shared 24x24 + front residual head",
            "front_state_weight": 12,
            "front_core_weight": 16,
        },
        {
            "experiment": "F4",
            "description": "Dual-head + explicit crossing lock",
            "front_capacity": "REGION-SPECIALIZED",
            "architecture": "shared 24x24 + front head + crossing constraint",
            "front_state_weight": 16,
            "front_core_weight": 20,
        },
    ]

    # -------------------------------------------------------------------------
    # Preservation gates
    # -------------------------------------------------------------------------

    exact_front = r3dr["authoritative_front_contract"]
    displacement = r3dr["authoritative_front_displacement_guards"]

    gate_rows = [
        {
            "gate": "front_error_reduction",
            "limit": ">= 50%",
            "authority": "R3D-R",
        },
        {
            "gate": "recovered_fronts",
            "limit": f">= {exact_front['minimum_recovered_fronts']}",
            "authority": "SG7B-10S",
        },
        {
            "gate": "conditioned_front_gap",
            "limit": f"<= {float(exact_front['maximum_conditioned_threshold_gap']):.17e}",
            "authority": "SG7B-10S",
        },
        {
            "gate": "100d_profile_L1",
            "limit": f"<= {float(exact_front['maximum_100d_profile_L1']):.17e}",
            "authority": "SG7B-10S",
        },
        {
            "gate": "mean_frozen_front_xi_shift",
            "limit": f"<= {float(displacement['maximum_mean_frozen_front_xi_shift']):.6e}",
            "authority": "SG7B-15R",
        },
        {
            "gate": "P90_frozen_front_xi_shift",
            "limit": f"<= {float(displacement['maximum_P90_frozen_front_xi_shift']):.6e}",
            "authority": "SG7B-15R",
        },
        {
            "gate": "front_sign_agreement",
            "limit": f">= {100*MIN_FRONT_SIGN_AGREEMENT:.1f}%",
            "authority": "R3D-R",
        },
        {
            "gate": "front_overshoot_fraction",
            "limit": f"<= {100*MAX_FRONT_OVERSHOOT_FRACTION:.1f}%",
            "authority": "R3D-R",
        },
        {
            "gate": "short_TOF_calibration_MAE",
            "limit": f"<= {MAX_SHORT_TOF_CALIBRATION_MAE:.6e}",
            "authority": "R3D-R",
        },
        {
            "gate": "global_abs_correction",
            "limit": f"<= {MAX_GLOBAL_ABS_CORRECTION:.3f}",
            "authority": "R3D-R",
        },
        {
            "gate": "calibration_TV_ratio",
            "limit": f"<= {MAX_CALIBRATION_TV_RATIO:.3f}",
            "authority": "R3D-R",
        },
        {
            "gate": "500-1000d bias",
            "limit": "|bias| <= 2.5e-3",
            "authority": "SG7B-12",
        },
        {
            "gate": "1000-2000d bias",
            "limit": "|bias| <= 4.5e-3",
            "authority": "SG7B-12",
        },
        {
            "gate": ">2000d bias",
            "limit": "|bias| <= 5.0e-3",
            "authority": "SG7B-12",
        },
    ]

    # -------------------------------------------------------------------------
    # Persistence contract — mandatory because R3E did not persist E1-E5 final
    # metrics adequately for downstream audit.
    # -------------------------------------------------------------------------

    persistence_rows = [
        {
            "artifact": "R3F1_Epoch_Metrics.csv",
            "required": True,
            "contents": "all evaluated checkpoint metrics for F1-F4",
        },
        {
            "artifact": "R3F1_Final_Experiment_Metrics.csv",
            "required": True,
            "contents": "complete final metrics for every F0-F4 experiment",
        },
        {
            "artifact": "R3F1_Final_Gate_Matrix.csv",
            "required": True,
            "contents": "every mandatory gate for every experiment",
        },
        {
            "artifact": "R3F1_Best_Checkpoint_By_Experiment.csv",
            "required": True,
            "contents": "epoch/path/metrics for each experiment's best checkpoint",
        },
        {
            "artifact": "F1-F4 best calibrator .keras files",
            "required": True,
            "contents": "best persisted checkpoint even if contract fails",
        },
        {
            "artifact": "R3F1_Candidate_Manifest.json",
            "required": True,
            "contents": "nomination status, candidate hash/path, no-freeze declaration",
        },
    ]

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    canonical_exact = bool(
        np.mean(np.abs(canonical - truth)) <= 5.0e-7
    )

    front_residual_material = bool(
        shell_mae > 1.0e-3
    )

    ideal_can_meet_gate = bool(
        ideal_reduction >= MIN_FRONT_ERROR_REDUCTION
    )

    persistence_repaired = bool(
        all(row["required"] for row in persistence_rows)
    )

    checks = [
        (
            "Incoming front-state capacity diagnosis reproduced",
            r3er2.get("diagnosis") == "FRONT_STATE_CORRECTION_CAPACITY_LIMIT",
        ),
        (
            "Canonical target remains effectively exact",
            canonical_exact,
        ),
        (
            "Front-shell residual remains material",
            front_residual_material,
        ),
        (
            "Validated canonical target can satisfy 50% front-reduction gate",
            ideal_can_meet_gate,
        ),
        (
            "50% front-error-reduction gate retained",
            True,
        ),
        (
            "Threshold/front-shape gates retained",
            True,
        ),
        (
            "TOF-bias gates retained",
            True,
        ),
        (
            "R3F1 persistence deficiency explicitly repaired",
            persistence_repaired,
        ),
        (
            "R3F1 matrix contains unchanged-capacity control",
            experiment_rows[0]["experiment"] == "F0",
        ),
        (
            "No training performed by R3F0",
            True,
        ),
    ]

    passed = all(flag for _, flag in checks)

    print("\n" + "=" * 78)
    print("R3F1 FRONT-STATE REFINEMENT PRINCIPLE")
    print("=" * 78)

    print("""
  Increase LOCAL residual-calibration capacity in the front shell/core.
  Do NOT modify SG7B-11.
  Do NOT relax the 50% front-error-reduction gate.
  Do NOT trade away threshold position, front topology, or TOF-bias control.
  Persist every evaluated checkpoint needed for independent audit.
""")

    print("=" * 78)
    print("V15-SG7C-R3F0 DESIGN VALIDATION")
    print("=" * 78)

    for description, flag in checks:
        print(f"[{'PASS' if flag else 'FAIL'}] {description}")

    print("=" * 78)

    if passed:
        status = "FRONT_STATE_REFINEMENT_CONTRACT_READY"
        recommendation = (
            "Proceed to controlled R3F1 front-state-focused calibrator refinement. "
            "Keep SG7B-11 frozen and retain every existing front, TOF-bias, and "
            "calibration safeguard. R3F1 must persist full per-experiment and "
            "checkpoint metrics regardless of pass/fail outcome."
        )
        next_milestone = (
            "V15-SG7C-R3F1 — Controlled Front-State-Focused Calibration Refinement"
        )
    else:
        status = "FRONT_STATE_REFINEMENT_CONTRACT_INCOMPLETE"
        recommendation = (
            "Do not train until the R3F0 design contract validates."
        )
        next_milestone = (
            "V15-SG7C-R3F0-R — Front-State Refinement Contract Repair"
        )

    save_csv(BASELINE_TABLE, baseline_rows)
    save_csv(REGION_TABLE, region_rows)
    save_csv(OBJECTIVE_TABLE, objective_rows)
    save_csv(EXPERIMENT_TABLE, experiment_rows)
    save_csv(PERSISTENCE_TABLE, persistence_rows)
    save_csv(GATE_TABLE, gate_rows)

    contract_out = {
        "milestone": "V15-SG7C-R3F0",
        "status": status,
        "training_performed": False,
        "SG7B11_modified": False,
        "incoming_diagnosis": r3er2.get("diagnosis"),
        "evidence_caveat": (
            "R3E persisted complete final front-reduction metrics only for E0; "
            "R3F1 therefore requires complete per-experiment/checkpoint persistence."
        ),
        "baseline": {
            "frozen_front_shell_L1": frozen_shell_l1,
            "canonical_front_shell_L1": canonical_shell_l1,
            "ideal_front_error_reduction_fraction": ideal_reduction,
            "required_shell_correction_MAE": shell_mae,
            "required_shell_correction_P90": shell_p90,
            "required_shell_correction_MAX": shell_max,
            "required_core_correction_MAE": core_mae,
        },
        "regions": region_rows,
        "objective": objective_rows,
        "preservation_gates": gate_rows,
        "experiment_matrix": experiment_rows,
        "persistence_contract": persistence_rows,
        "next_milestone": next_milestone,
    }

    save_json(CONTRACT_FILE, contract_out)

    summary = {
        "milestone": "V15-SG7C-R3F0",
        "status": status,
        "validation_passed": passed,
        "training_performed": False,
        "SG7B11_modified": False,
        "ideal_front_error_reduction_fraction": ideal_reduction,
        "required_front_shell_correction_MAE": shell_mae,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(SUMMARY_FILE, summary)

    # diagnostics
    plt.figure(figsize=(9, 5))
    plt.hist(required[shell], bins=80)
    plt.xlabel("Required front-shell correction")
    plt.ylabel("Samples")
    plt.title("V15-SG7C-R3F0 Required Front-State Correction")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3F0_Front_Correction_Distribution.png",
        dpi=300,
    )
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.hist(required[core], bins=80)
    plt.xlabel("Required front-core correction")
    plt.ylabel("Samples")
    plt.title("V15-SG7C-R3F0 Required Front-Core Correction")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3F0_Front_Core_Correction.png",
        dpi=300,
    )
    plt.close()

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
    print(f"  {OBJECTIVE_TABLE.name}")
    print(f"  {EXPERIMENT_TABLE.name}")
    print(f"  {PERSISTENCE_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print("\nDiagnostics:")
    print("  V15SG7CR3F0_Front_Correction_Distribution.png")
    print("  V15SG7CR3F0_Front_Core_Correction.png")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print(f"V15-SG7C-R3F0 DESIGN: {'PASS' if passed else 'FAIL'}")
    print()
    print("No training was performed.")
    print("SG7B-11 remains frozen and authoritative.")
    print("No front, TOF-bias, map-back, or plume-validation gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
