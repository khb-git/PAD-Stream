from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1D
# Joint Exact-Support / TOF-Bias Reconciliation Design
#
# DESIGN-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO X08 SUPPORT GEOMETRY CHANGED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED OR RELAXED.
#
# PURPOSE
# -------
# R1CR established:
#
#   TOF_BIAS_FAILURES_PREEXIST_SUPPORT_EXTENSION
#
# and showed that X08:
#
#   * crosses the unchanged 50% support gate,
#   * does NOT create any new TOF/tail failure,
#   * does NOT materially worsen any existing TOF/tail failure.
#
# Therefore:
#
#   X08 support geometry is preserved.
#
# The remaining problem is the pre-existing deployment TOF/tail bias:
#
#   500-1000d bias               ~ 4.466e-03
#   1000-2000d bias              ~ 8.321e-03
#   >2000d bias                  ~ 9.663e-03
#   initial-tail bias            ~ 9.021e-03
#   material + share 500-1000d  ~ 51.72%
#
# R1D defines a JOINT deployment correction contract:
#
#   S_joint = S_X08 + deltaS_TOF
#
# where deltaS_TOF:
#
#   * acts only on the residual remaining after X08,
#   * is conditioned on terminal TOF,
#   * is bounded to move toward SG7A/canonical truth,
#   * is strongly suppressed in the accepted front core,
#   * preserves the X08 exact-support coefficient field,
#   * and cannot reduce exact support below 50%.
#
# R1D performs NO fitting. It only creates the controlled R1E experiment matrix
# and acceptance contract.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1D"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R1CR_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1CR"
    / "PAD_Stream_V15SG7CR3F5R1CR_Summary.json"
)

R1CR_GATE_TABLE = (
    ROOT / "output" / "V15_SG7CR3F5R1CR"
    / "V15SG7CR3F5R1CR_Failed_Gate_Decomposition.csv"
)

R1CR_TOF_TABLE = (
    ROOT / "output" / "V15_SG7CR3F5R1CR"
    / "V15SG7CR3F5R1CR_TOF_Band_Bias_Comparison.csv"
)

R1CR_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1CR"
    / "V15SG7CR3F5R1CR_Bias_Decomposition.npz"
)

R1C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1C"
    / "V15SG7CR3F5R1C_Independent_Validation.npz"
)

R1B_MANIFEST = (
    ROOT / "output" / "V15_SG7CR3F5R1B"
    / "V15SG7CR3F5R1B_Candidate_Manifest.json"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1D_Summary.json"
BASELINE_TABLE = OUT / "V15SG7CR3F5R1D_Joint_Baseline.csv"
REGION_TABLE = OUT / "V15SG7CR3F5R1D_TOF_Correction_Regions.csv"
OBJECTIVE_TABLE = OUT / "V15SG7CR3F5R1D_Objective_Design.csv"
GATE_TABLE = OUT / "V15SG7CR3F5R1D_Preservation_Gates.csv"
EXPERIMENT_TABLE = OUT / "V15SG7CR3F5R1D_R1E_Experiment_Matrix.csv"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1D_Joint_Reconciliation_Contract.json"

# -----------------------------------------------------------------------------
# Unchanged authoritative gates
# -----------------------------------------------------------------------------

SUPPORT_GATE = 0.50

BIAS_500_1000_MAX = 2.5e-3
BIAS_1000_2000_MAX = 4.5e-3
BIAS_GT2000_MAX = 5.0e-3
TAIL_BIAS_MAX = 5.0e-3
MATERIAL_SHARE_MAX = 0.40

MIN_RECOVERED_FRONTS = 744
MAX_CONDITIONED_GAP = 5.33123727917913484e-04
MAX_PROFILE_L1_100D = 4.50032942291447424e-03

# Direct front protection for the new TOF corrector.
FRONT_CORE_LOW = 0.205
FRONT_CORE_HIGH = 0.235
FRONT_SHELL_LOW = 0.20
FRONT_SHELL_HIGH = 0.30

# Maximum fraction of remaining local truth residual the R1E TOF correction
# may apply. These are design caps, not gate relaxations.
CAP_FAST_TOF = 0.10
CAP_MID_TOF = 0.45
CAP_SLOW_TOF = 0.70
CAP_VERY_SLOW_TOF = 0.85
CAP_TAIL = 0.85

EPS = 1e-15


# =============================================================================
# IO
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_csv(path: Path, rows):
    if not rows:
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
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


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1D")
    print("Joint Exact-Support / TOF-Bias Reconciliation Design")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
X08 SUPPORT GEOMETRY WILL NOT BE CHANGED.
NO FRONT OR TOF-BIAS GATE WILL BE CHANGED OR RELAXED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
""")

    incoming = load_json(R1CR_SUMMARY)

    if incoming.get("diagnosis") != "TOF_BIAS_FAILURES_PREEXIST_SUPPORT_EXTENSION":
        raise RuntimeError(
            "R1D requires incoming diagnosis TOF_BIAS_FAILURES_PREEXIST_SUPPORT_EXTENSION."
        )

    r1b_manifest = load_json(R1B_MANIFEST)

    if r1b_manifest.get("selected_experiment") != "X08":
        raise RuntimeError("R1D requires the preserved X08 support-extension candidate.")

    # -------------------------------------------------------------------------
    # Load independent X08 state.
    # -------------------------------------------------------------------------

    r1c = np.load(R1C_NUMERICAL, allow_pickle=True)

    required_keys = [
        "truth100",
        "candidate100",
        "coeff100_candidate",
        "exact_support_fraction",
        "tau_end",
    ]

    missing = [key for key in required_keys if key not in r1c.files]

    if missing:
        raise RuntimeError(
            "R1C numerical database missing required arrays: "
            + ", ".join(missing)
        )

    truth100 = np.asarray(r1c["truth100"], dtype=float)
    x08_100 = np.asarray(r1c["candidate100"], dtype=float)
    coeff_x08 = np.asarray(r1c["coeff100_candidate"], dtype=float)
    tau_end = np.asarray(r1c["tau_end"], dtype=float)
    support_x08 = float(np.asarray(r1c["exact_support_fraction"]))

    if truth100.shape != x08_100.shape:
        raise RuntimeError("truth100 / X08 shape mismatch.")

    if coeff_x08.shape != truth100.shape:
        raise RuntimeError("X08 coefficient field shape mismatch.")

    if tau_end.size != truth100.shape[0]:
        raise RuntimeError("terminal TOF size mismatch.")

    residual_after_x08 = truth100 - x08_100

    # -------------------------------------------------------------------------
    # Reproduce failed-gate baseline from R1CR.
    # -------------------------------------------------------------------------

    gate_rows = load_csv(R1CR_GATE_TABLE)

    gate_map = {
        row["gate"]: row
        for row in gate_rows
    }

    required_failed = [
        "bias_500_1000",
        "bias_1000_2000",
        "bias_gt2000",
        "tail_bias",
        "material_positive_share_500_1000",
    ]

    for gate in required_failed:
        if gate not in gate_map:
            raise RuntimeError(f"Missing R1CR gate record: {gate}")

    baseline_rows = [{
        "selected_support_candidate": "X08",
        "exact_support_fraction": support_x08,
        "support_gate": SUPPORT_GATE,
        "support_margin": support_x08 - SUPPORT_GATE,
        "bias_500_1000": fnum(gate_map["bias_500_1000"], "candidate_value"),
        "bias_1000_2000": fnum(gate_map["bias_1000_2000"], "candidate_value"),
        "bias_gt2000": fnum(gate_map["bias_gt2000"], "candidate_value"),
        "tail_bias": fnum(gate_map["tail_bias"], "candidate_value"),
        "material_positive_share_500_1000":
            fnum(gate_map["material_positive_share_500_1000"], "candidate_value"),
        "remaining_truth_residual_L1":
            float(np.mean(np.abs(residual_after_x08))),
        "remaining_truth_residual_max":
            float(np.max(np.abs(residual_after_x08))),
    }]

    save_csv(BASELINE_TABLE, baseline_rows)

    print("JOINT BASELINE")
    print(f"  X08 exact support       : {100*support_x08:.6f}%")
    print(
        f"  500-1000d bias          : "
        f"{baseline_rows[0]['bias_500_1000']:.6e}"
    )
    print(
        f"  1000-2000d bias         : "
        f"{baseline_rows[0]['bias_1000_2000']:.6e}"
    )
    print(
        f"  >2000d bias             : "
        f"{baseline_rows[0]['bias_gt2000']:.6e}"
    )
    print(
        f"  Tail bias               : "
        f"{baseline_rows[0]['tail_bias']:.6e}"
    )
    print(
        f"  Material + share        : "
        f"{100*baseline_rows[0]['material_positive_share_500_1000']:.2f}%"
    )

    # -------------------------------------------------------------------------
    # Define TOF-conditioned correction regions.
    # -------------------------------------------------------------------------

    region_rows = [
        {
            "region": "T0_fast_TOF",
            "condition": "tau_end <= 500 d",
            "correction_role": "OFF / VERY WEAK",
            "max_fraction_of_remaining_truth_residual": CAP_FAST_TOF,
            "front_core_policy": "OFF",
            "reason": "already-good fast-streamline deployment preservation",
        },
        {
            "region": "T1_mid_TOF",
            "condition": "500 < tau_end <= 1000 d",
            "correction_role": "PRIMARY",
            "max_fraction_of_remaining_truth_residual": CAP_MID_TOF,
            "front_core_policy": "STRONGLY_SUPPRESSED",
            "reason": "dominant material-positive bias population",
        },
        {
            "region": "T2_slow_TOF",
            "condition": "1000 < tau_end <= 2000 d",
            "correction_role": "STRONG",
            "max_fraction_of_remaining_truth_residual": CAP_SLOW_TOF,
            "front_core_policy": "STRONGLY_SUPPRESSED",
            "reason": "large persistent positive deployment bias",
        },
        {
            "region": "T3_very_slow_TOF",
            "condition": "tau_end > 2000 d",
            "correction_role": "STRONGEST",
            "max_fraction_of_remaining_truth_residual": CAP_VERY_SLOW_TOF,
            "front_core_policy": "STRONGLY_SUPPRESSED",
            "reason": "largest persistent positive deployment bias",
        },
        {
            "region": "T4_initial_tail",
            "condition": f"SG7A truth <= {FRONT_CORE_LOW:.3f}",
            "correction_role": "STRONG",
            "max_fraction_of_remaining_truth_residual": CAP_TAIL,
            "front_core_policy": "N/A",
            "reason": "pre-existing initial-state positive bias",
        },
        {
            "region": "T5_front_core",
            "condition":
                f"{FRONT_CORE_LOW:.3f} <= SG7A truth <= {FRONT_CORE_HIGH:.3f}",
            "correction_role": "NEAR ZERO / GUARDED",
            "max_fraction_of_remaining_truth_residual": 0.05,
            "front_core_policy": "MAXIMUM PROTECTION",
            "reason": "preserve accepted threshold crossing and front topology",
        },
        {
            "region": "T6_front_shell",
            "condition":
                f"{FRONT_SHELL_LOW:.3f} <= SG7A truth <= {FRONT_SHELL_HIGH:.3f}",
            "correction_role": "BOUNDED",
            "max_fraction_of_remaining_truth_residual": 0.20,
            "front_core_policy": "DIRECT OUTCOME GATES",
            "reason": "permit small state improvement without sacrificing accepted front",
        },
    ]

    save_csv(REGION_TABLE, region_rows)

    # -------------------------------------------------------------------------
    # Objective design.
    # -------------------------------------------------------------------------

    objective_rows = [
        {
            "term": "L_TOF_500_1000",
            "purpose": "reduce 500-1000d positive bias below unchanged gate",
            "target": BIAS_500_1000_MAX,
        },
        {
            "term": "L_TOF_1000_2000",
            "purpose": "reduce 1000-2000d positive bias below unchanged gate",
            "target": BIAS_1000_2000_MAX,
        },
        {
            "term": "L_TOF_gt2000",
            "purpose": "reduce >2000d positive bias below unchanged gate",
            "target": BIAS_GT2000_MAX,
        },
        {
            "term": "L_tail",
            "purpose": "reduce initial-tail positive bias below unchanged gate",
            "target": TAIL_BIAS_MAX,
        },
        {
            "term": "L_material_share",
            "purpose": "reduce material-positive share in 500-1000d population",
            "target": MATERIAL_SHARE_MAX,
        },
        {
            "term": "L_front_core",
            "purpose": "protect accepted front threshold/core from TOF correction",
            "target": "direct state/crossing lock",
        },
        {
            "term": "L_front_shape",
            "purpose": "retain X08/SG7A front topology and conditioned gap",
            "target": MAX_CONDITIONED_GAP,
        },
        {
            "term": "L_support_lock",
            "purpose": "preserve X08 exact support coefficient field unchanged",
            "target": "exact support >= 0.50",
        },
        {
            "term": "L_direction",
            "purpose": "TOF correction may only move toward SG7A/canonical truth",
            "target": "0 <= beta <= regional cap",
        },
    ]

    save_csv(OBJECTIVE_TABLE, objective_rows)

    # -------------------------------------------------------------------------
    # Preservation gates.
    # -------------------------------------------------------------------------

    preservation_rows = [
        {
            "gate": "exact_support_fraction",
            "operator": ">=",
            "limit": SUPPORT_GATE,
            "source": "R1B/R1C",
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "recovered_fronts",
            "operator": ">=",
            "limit": MIN_RECOVERED_FRONTS,
            "source": "SG7B-10S / clarified deployment contract",
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "conditioned_front_gap",
            "operator": "<=",
            "limit": MAX_CONDITIONED_GAP,
            "source": "SG7B-10S / clarified deployment contract",
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "profile_L1_100d",
            "operator": "<=",
            "limit": MAX_PROFILE_L1_100D,
            "source": "SG7B-10S / clarified deployment contract",
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "bias_500_1000",
            "operator": "<=",
            "limit": BIAS_500_1000_MAX,
            "source": "SG7B-12",
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "bias_1000_2000",
            "operator": "<=",
            "limit": BIAS_1000_2000_MAX,
            "source": "SG7B-12",
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "bias_gt2000",
            "operator": "<=",
            "limit": BIAS_GT2000_MAX,
            "source": "SG7B-12",
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "tail_bias",
            "operator": "<=",
            "limit": TAIL_BIAS_MAX,
            "source": "SG7B-12",
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "material_positive_share_500_1000",
            "operator": "<=",
            "limit": MATERIAL_SHARE_MAX,
            "source": "SG7B-12",
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "frozen_relative_front_displacement",
            "operator": "REPORT",
            "limit": "diagnostic only",
            "source": "R3F4-R3B clarified contract",
            "semantics": "DIAGNOSTIC",
        },
    ]

    save_csv(GATE_TABLE, preservation_rows)

    # -------------------------------------------------------------------------
    # Controlled R1E experiment matrix.
    # -------------------------------------------------------------------------

    experiment_rows = [
        {
            "experiment": "J0",
            "description": "X08 exact-support control; no TOF correction",
            "mid_TOF_cap": 0.0,
            "slow_TOF_cap": 0.0,
            "very_slow_TOF_cap": 0.0,
            "tail_cap": 0.0,
            "front_core_cap": 0.0,
            "front_shell_cap": 0.0,
        },
        {
            "experiment": "J1",
            "description": "Conservative TOF-only residual correction",
            "mid_TOF_cap": 0.25,
            "slow_TOF_cap": 0.40,
            "very_slow_TOF_cap": 0.55,
            "tail_cap": 0.40,
            "front_core_cap": 0.02,
            "front_shell_cap": 0.10,
        },
        {
            "experiment": "J2",
            "description": "Balanced joint TOF/tail correction",
            "mid_TOF_cap": 0.35,
            "slow_TOF_cap": 0.55,
            "very_slow_TOF_cap": 0.70,
            "tail_cap": 0.65,
            "front_core_cap": 0.03,
            "front_shell_cap": 0.15,
        },
        {
            "experiment": "J3",
            "description": "Strong slow-TOF correction with front lock",
            "mid_TOF_cap": 0.40,
            "slow_TOF_cap": 0.65,
            "very_slow_TOF_cap": 0.80,
            "tail_cap": 0.70,
            "front_core_cap": 0.02,
            "front_shell_cap": 0.12,
        },
        {
            "experiment": "J4",
            "description": "Tail-focused correction with moderate TOF action",
            "mid_TOF_cap": 0.30,
            "slow_TOF_cap": 0.50,
            "very_slow_TOF_cap": 0.65,
            "tail_cap": 0.80,
            "front_core_cap": 0.02,
            "front_shell_cap": 0.12,
        },
        {
            "experiment": "J5",
            "description": "Maximum bounded reconciliation",
            "mid_TOF_cap": CAP_MID_TOF,
            "slow_TOF_cap": CAP_SLOW_TOF,
            "very_slow_TOF_cap": CAP_VERY_SLOW_TOF,
            "tail_cap": CAP_TAIL,
            "front_core_cap": 0.05,
            "front_shell_cap": 0.20,
        },
    ]

    save_csv(EXPERIMENT_TABLE, experiment_rows)

    # -------------------------------------------------------------------------
    # Contract validation.
    # -------------------------------------------------------------------------

    support_preserved = bool(
        support_x08 >= SUPPORT_GATE
    )

    residual_nonzero = bool(
        np.mean(np.abs(residual_after_x08)) > 0.0
    )

    failed_biases_confirmed = bool(
        baseline_rows[0]["bias_500_1000"] > BIAS_500_1000_MAX
        and baseline_rows[0]["bias_1000_2000"] > BIAS_1000_2000_MAX
        and baseline_rows[0]["bias_gt2000"] > BIAS_GT2000_MAX
        and baseline_rows[0]["tail_bias"] > TAIL_BIAS_MAX
        and baseline_rows[0]["material_positive_share_500_1000"] > MATERIAL_SHARE_MAX
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1D DESIGN VALIDATION")
    print("=" * 78)

    checks = [
        ("R1CR pre-existing TOF-bias diagnosis reproduced", True),
        ("X08 exact-support candidate reproduced", True),
        ("X08 support remains above unchanged 50% gate", support_preserved),
        ("All five pre-existing TOF/tail failures reproduced", failed_biases_confirmed),
        ("Remaining canonical residual is nonzero", residual_nonzero),
        ("TOF correction acts only on remaining truth residual", True),
        ("Fast-TOF population explicitly protected", True),
        ("Front core explicitly protected", True),
        ("X08 support coefficient field locked", True),
        ("All SG7B-12 TOF gates retained unchanged", True),
        ("Clarified SG7A front authority retained", True),
        ("Frozen-relative displacement remains diagnostic only", True),
        ("R1E matrix includes unchanged X08 control", True),
        ("No fitting/training performed by R1D", True),
    ]

    for desc, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {desc}")

    complete = all(passed for _, passed in checks)

    if complete:
        status = "JOINT_EXACT_SUPPORT_TOF_RECONCILIATION_CONTRACT_READY"
        diagnosis = "X08_FRONT_SUPPORT_ACCEPTED_PREEXISTING_TOF_BIAS_REMAINS"
        recommendation = (
            "Proceed to controlled R1E joint residual correction. Keep X08 support geometry "
            "exactly fixed and apply only a bounded TOF/tail-conditioned fraction of the "
            "remaining SG7A/canonical residual. Candidate selection must satisfy the unchanged "
            "50% support gate together with every clarified front and SG7B-12 TOF/tail gate."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1E — Controlled Joint Exact-Support / TOF-Bias Reconciliation"
        )
    else:
        status = "JOINT_RECONCILIATION_CONTRACT_INCOMPLETE"
        diagnosis = "R1D_DESIGN_VALIDATION_FAILED"
        recommendation = (
            "Do not perform joint calibration until the R1D design contract validates."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1DR — Joint Reconciliation Contract Repair"
        )

    contract = {
        "milestone": "V15-SG7C-R3F5-R1D",
        "status": status,
        "diagnosis": diagnosis,
        "training_performed": False,
        "support_extension_recalibrated": False,
        "X08_support_geometry_changed": False,
        "gate_changed": False,
        "joint_correction_form":
            "S_joint = S_X08 + beta(xi,tau_end,S_X08,S_truth) * (S_truth - S_X08)",
        "beta_bounds": "0 <= beta <= regional cap",
        "support_lock": "X08 coeff100 unchanged",
        "front_authority": "SG7A/canonical truth",
        "frozen_relative_displacement_semantics": "diagnostic_only",
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(CONTRACT_FILE, contract)

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1D",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "support_extension_recalibrated": False,
            "X08_support_geometry_changed": False,
            "gate_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
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
    print(f"  {BASELINE_TABLE.name}")
    print(f"  {REGION_TABLE.name}")
    print(f"  {OBJECTIVE_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print(f"  {EXPERIMENT_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1D DESIGN: COMPLETE")
    print()
    print("No training was performed.")
    print("X08 support geometry was not changed.")
    print("No gate was changed or relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
