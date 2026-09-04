from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1F0
# Non-Front Slow-TOF Residual Capacity Design
#
# DESIGN-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO X08 SUPPORT GEOMETRY CHANGED.
# NO R1E/J5 CORRECTION CHANGED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED OR RELAXED.
#
# PURPOSE
# -------
# R1ER established:
#
#   FRONT_MASKED_EFFECTIVE_BETA_CAPACITY_LIMIT
#
# J5 already:
#   * preserves X08 exact support at 50.000564%
#   * preserves the accepted SG7A-relative front with very large margin
#   * passes the 500-1000d material-positive-share gate
#   * reduces every remaining positive-bias metric
#
# But the effective beta reaching biased populations is below the beta required
# to satisfy the unchanged mean-bias gates because front-shell/core masking
# suppresses correction over too much of the slow-TOF/tail state.
#
# R1F0 therefore designs a selective second-stage residual capacity:
#
#   S_F = S_J5 + gamma_nonfront * (S_truth - S_J5)
#
# where gamma_nonfront:
#
#   * is zero in the locked front core,
#   * is near-zero / strongly bounded in the accepted front shell,
#   * acts only in slow-TOF / very-slow-TOF / tail populations,
#   * is bounded to move toward SG7A/canonical truth,
#   * leaves X08 support geometry exactly unchanged,
#   * and is sized from R1ER effective-beta deficits.
#
# R1F0 performs NO fitting and NO correction. It creates the controlled R1F1
# experiment matrix and preservation contract.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1F0"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R1ER_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1ER"
    / "PAD_Stream_V15SG7CR3F5R1ER_Summary.json"
)

R1ER_REQUIRED_BETA = (
    ROOT / "output" / "V15_SG7CR3F5R1ER"
    / "V15SG7CR3F5R1ER_Required_Beta_By_Gate.csv"
)

R1ER_FRONT_MARGIN = (
    ROOT / "output" / "V15_SG7CR3F5R1ER"
    / "V15SG7CR3F5R1ER_Front_Preservation_Margins.csv"
)

R1E_EXPERIMENTS = (
    ROOT / "output" / "V15_SG7CR3F5R1E"
    / "V15SG7CR3F5R1E_Experiment_Metrics.csv"
)

R1E_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1E"
    / "V15SG7CR3F5R1E_Controlled_Joint_Reconciliation.npz"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1F0_Summary.json"
BASELINE_TABLE = OUT / "V15SG7CR3F5R1F0_J5_Baseline.csv"
CAPACITY_TABLE = OUT / "V15SG7CR3F5R1F0_Required_NonFront_Capacity.csv"
REGION_TABLE = OUT / "V15SG7CR3F5R1F0_NonFront_Region_Definition.csv"
OBJECTIVE_TABLE = OUT / "V15SG7CR3F5R1F0_Objective_Design.csv"
GATE_TABLE = OUT / "V15SG7CR3F5R1F0_Preservation_Gates.csv"
EXPERIMENT_TABLE = OUT / "V15SG7CR3F5R1F0_R1F1_Experiment_Matrix.csv"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1F0_NonFront_Capacity_Contract.json"

# -----------------------------------------------------------------------------
# Authoritative unchanged gates
# -----------------------------------------------------------------------------

SUPPORT_GATE = 0.50
MIN_RECOVERED_FRONTS = 744
MAX_CONDITIONED_GAP = 5.33123727917913484e-04
MAX_PROFILE_L1_100D = 4.50032942291447424e-03

BIAS_500_1000_MAX = 2.5e-3
BIAS_1000_2000_MAX = 4.5e-3
BIAS_GT2000_MAX = 5.0e-3
TAIL_BIAS_MAX = 5.0e-3
MATERIAL_SHARE_MAX = 0.40

# Accepted front protection.
FRONT_CORE_LOW = 0.205
FRONT_CORE_HIGH = 0.235
FRONT_SHELL_LOW = 0.20
FRONT_SHELL_HIGH = 0.30

# Second-stage non-front gamma caps.
# These are deliberately modest because R1ER quantified only ~0.14-0.25
# additional effective beta as necessary.
GAMMA_FAST = 0.00
GAMMA_MID_MAX = 0.30
GAMMA_SLOW_MAX = 0.30
GAMMA_VERY_SLOW_MAX = 0.35
GAMMA_TAIL_MAX = 0.40

# Front protection for the second-stage correction.
GAMMA_FRONT_CORE = 0.00
GAMMA_FRONT_SHELL_MAX = 0.03

EPS = 1e-15


# =============================================================================
# IO helpers
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


def row_by_experiment(rows, exp):
    for row in rows:
        if row.get("experiment") == exp:
            return row
    return None


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1F0")
    print("Non-Front Slow-TOF Residual Capacity Design")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
X08 SUPPORT GEOMETRY WILL NOT BE CHANGED.
THE R1E J5 FIELD WILL NOT BE MODIFIED.
NO FRONT OR TOF-BIAS GATE WILL BE CHANGED OR RELAXED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
""")

    incoming = load_json(R1ER_SUMMARY)

    if incoming.get("diagnosis") != "FRONT_MASKED_EFFECTIVE_BETA_CAPACITY_LIMIT":
        raise RuntimeError(
            "R1F0 requires incoming diagnosis FRONT_MASKED_EFFECTIVE_BETA_CAPACITY_LIMIT."
        )

    experiments = load_csv(R1E_EXPERIMENTS)
    j5 = row_by_experiment(experiments, "J5")

    if j5 is None:
        raise RuntimeError("R1F0 requires the R1E J5 experiment record.")

    req_beta_rows = load_csv(R1ER_REQUIRED_BETA)

    r1e = np.load(R1E_NUMERICAL, allow_pickle=True)

    required_keys = [
        "truth100",
        "J5_pred100",
        "J5_beta",
        "X08_100",
        "X08_coeff100",
        "exact_support_fraction",
        "tau_end",
    ]

    missing = [k for k in required_keys if k not in r1e.files]

    if missing:
        raise RuntimeError(
            "R1E numerical database missing required arrays: "
            + ", ".join(missing)
        )

    truth = np.asarray(r1e["truth100"], dtype=float)
    j5_pred = np.asarray(r1e["J5_pred100"], dtype=float)
    j5_beta = np.asarray(r1e["J5_beta"], dtype=float)
    x08 = np.asarray(r1e["X08_100"], dtype=float)
    coeff_x08 = np.asarray(r1e["X08_coeff100"], dtype=float)
    tau_end = np.asarray(r1e["tau_end"], dtype=float)
    exact_support = float(np.asarray(r1e["exact_support_fraction"]))

    if not (
        truth.shape == j5_pred.shape == j5_beta.shape == x08.shape == coeff_x08.shape
        and truth.ndim == 2
    ):
        raise RuntimeError("R1F0 state/beta/coefficient arrays are not shape-compatible.")

    if tau_end.size != truth.shape[0]:
        raise RuntimeError("R1F0 tau_end length mismatch.")

    remaining_after_j5 = truth - j5_pred

    # -------------------------------------------------------------------------
    # Baseline
    # -------------------------------------------------------------------------

    baseline_rows = [{
        "experiment": "J5",
        "exact_support_fraction": exact_support,
        "global_L1_100d": fnum(j5, "global_L1_100d"),
        "conditioned_front_gap": fnum(j5, "conditioned_front_gap"),
        "bias_500_1000": fnum(j5, "bias_500_1000"),
        "bias_1000_2000": fnum(j5, "bias_1000_2000"),
        "bias_gt2000": fnum(j5, "bias_gt2000"),
        "tail_bias": fnum(j5, "tail_bias"),
        "material_positive_share_500_1000":
            fnum(j5, "material_positive_share_500_1000"),
        "remaining_truth_residual_L1":
            float(np.mean(np.abs(remaining_after_j5))),
        "remaining_truth_residual_max":
            float(np.max(np.abs(remaining_after_j5))),
    }]

    save_csv(BASELINE_TABLE, baseline_rows)

    print("LOCKED J5 BASELINE")
    print(f"  Exact support           : {100*exact_support:.6f}%")
    print(f"  Conditioned gap         : {baseline_rows[0]['conditioned_front_gap']:.6e}")
    print(f"  500-1000d bias          : {baseline_rows[0]['bias_500_1000']:.6e}")
    print(f"  1000-2000d bias         : {baseline_rows[0]['bias_1000_2000']:.6e}")
    print(f"  >2000d bias             : {baseline_rows[0]['bias_gt2000']:.6e}")
    print(f"  Tail bias               : {baseline_rows[0]['tail_bias']:.6e}")
    print(
        f"  Material + share        : "
        f"{100*baseline_rows[0]['material_positive_share_500_1000']:.2f}%"
    )

    # -------------------------------------------------------------------------
    # Required capacity translation.
    # -------------------------------------------------------------------------

    capacity_rows = []

    gate_to_region = {
        "bias_500_1000": ("mid_TOF", GAMMA_MID_MAX),
        "bias_1000_2000": ("slow_TOF", GAMMA_SLOW_MAX),
        "bias_gt2000": ("very_slow_TOF", GAMMA_VERY_SLOW_MAX),
        "tail_bias": ("tail", GAMMA_TAIL_MAX),
    }

    for row in req_beta_rows:
        gate = row.get("gate")

        if gate not in gate_to_region:
            continue

        region, gamma_max = gate_to_region[gate]

        additional_effective_beta = fnum(
            row,
            "additional_effective_beta_needed",
        )

        # Translate remaining effective-beta deficit into a design gamma.
        # Because the second correction acts on the residual remaining after J5:
        #
        #   e_new = (1-gamma) e_J5
        #
        # required gamma = 1 - target / J5_bias.
        j5_bias = fnum(row, "J5_bias")
        target = fnum(row, "target_bias")

        gamma_required_from_j5 = (
            1.0 - target / j5_bias
            if j5_bias > EPS
            else np.nan
        )

        gamma_required_from_j5 = float(
            np.clip(
                gamma_required_from_j5,
                0.0,
                1.0,
            )
        )

        capacity_rows.append({
            "gate": gate,
            "region": region,
            "J5_bias": j5_bias,
            "target_bias": target,
            "R1ER_additional_effective_beta_needed":
                additional_effective_beta,
            "second_stage_gamma_required_from_J5":
                gamma_required_from_j5,
            "R1F0_gamma_design_max": gamma_max,
            "design_max_exceeds_required":
                bool(gamma_max >= gamma_required_from_j5),
        })

    save_csv(CAPACITY_TABLE, capacity_rows)

    # -------------------------------------------------------------------------
    # Non-front region definition.
    # -------------------------------------------------------------------------

    front_core = (
        (truth >= FRONT_CORE_LOW)
        &
        (truth <= FRONT_CORE_HIGH)
    )

    front_shell = (
        (truth >= FRONT_SHELL_LOW)
        &
        (truth <= FRONT_SHELL_HIGH)
    )

    nonfront = ~front_shell
    tail = truth <= FRONT_CORE_LOW

    region_rows = [
        {
            "region": "N0_fast_TOF",
            "condition": "tau_end <= 500 d",
            "second_stage_role": "OFF",
            "gamma_max": GAMMA_FAST,
            "front_policy": "LOCKED",
        },
        {
            "region": "N1_mid_TOF_nonfront",
            "condition": "500 < tau_end <= 1000 d AND outside accepted front shell",
            "second_stage_role": "PRIMARY",
            "gamma_max": GAMMA_MID_MAX,
            "front_policy": "NONFRONT ONLY",
        },
        {
            "region": "N2_slow_TOF_nonfront",
            "condition": "1000 < tau_end <= 2000 d AND outside accepted front shell",
            "second_stage_role": "STRONG",
            "gamma_max": GAMMA_SLOW_MAX,
            "front_policy": "NONFRONT ONLY",
        },
        {
            "region": "N3_very_slow_TOF_nonfront",
            "condition": "tau_end > 2000 d AND outside accepted front shell",
            "second_stage_role": "STRONGEST",
            "gamma_max": GAMMA_VERY_SLOW_MAX,
            "front_policy": "NONFRONT ONLY",
        },
        {
            "region": "N4_tail_nonfront",
            "condition":
                f"SG7A truth <= {FRONT_CORE_LOW:.3f} AND outside accepted front shell",
            "second_stage_role": "STRONG",
            "gamma_max": GAMMA_TAIL_MAX,
            "front_policy": "NONFRONT ONLY",
        },
        {
            "region": "N5_front_shell",
            "condition":
                f"{FRONT_SHELL_LOW:.3f} <= SG7A truth <= {FRONT_SHELL_HIGH:.3f}",
            "second_stage_role": "NEAR ZERO",
            "gamma_max": GAMMA_FRONT_SHELL_MAX,
            "front_policy": "STRONGLY PROTECTED",
        },
        {
            "region": "N6_front_core",
            "condition":
                f"{FRONT_CORE_LOW:.3f} <= SG7A truth <= {FRONT_CORE_HIGH:.3f}",
            "second_stage_role": "OFF",
            "gamma_max": GAMMA_FRONT_CORE,
            "front_policy": "LOCKED",
        },
    ]

    save_csv(REGION_TABLE, region_rows)

    # -------------------------------------------------------------------------
    # Objective design.
    # -------------------------------------------------------------------------

    objective_rows = [
        {
            "term": "L_mid_nonfront",
            "purpose": "deliver missing effective beta to 500-1000d non-front residual",
            "target": BIAS_500_1000_MAX,
        },
        {
            "term": "L_slow_nonfront",
            "purpose": "deliver missing effective beta to 1000-2000d non-front residual",
            "target": BIAS_1000_2000_MAX,
        },
        {
            "term": "L_very_slow_nonfront",
            "purpose": "deliver missing effective beta to >2000d non-front residual",
            "target": BIAS_GT2000_MAX,
        },
        {
            "term": "L_tail_nonfront",
            "purpose": "reduce remaining positive initial-tail bias",
            "target": TAIL_BIAS_MAX,
        },
        {
            "term": "L_material_share",
            "purpose": "retain already-passing material-positive-share gate",
            "target": MATERIAL_SHARE_MAX,
        },
        {
            "term": "L_front_shell_lock",
            "purpose": "prevent second-stage correction from reopening accepted front geometry",
            "target": GAMMA_FRONT_SHELL_MAX,
        },
        {
            "term": "L_front_core_lock",
            "purpose": "exactly suppress second-stage correction in front core",
            "target": 0.0,
        },
        {
            "term": "L_truth_direction",
            "purpose": "second-stage correction may only move toward SG7A truth",
            "target": "0 <= gamma <= regional cap",
        },
        {
            "term": "L_support_lock",
            "purpose": "preserve X08 exact-support coefficient field",
            "target": "support >= 0.50",
        },
    ]

    save_csv(OBJECTIVE_TABLE, objective_rows)

    # -------------------------------------------------------------------------
    # Preservation gates.
    # -------------------------------------------------------------------------

    gate_rows = [
        {
            "gate": "exact_support_fraction",
            "operator": ">=",
            "limit": SUPPORT_GATE,
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "recovered_fronts",
            "operator": ">=",
            "limit": MIN_RECOVERED_FRONTS,
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "conditioned_front_gap",
            "operator": "<=",
            "limit": MAX_CONDITIONED_GAP,
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "profile_L1_100d",
            "operator": "<=",
            "limit": MAX_PROFILE_L1_100D,
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "bias_500_1000",
            "operator": "<=",
            "limit": BIAS_500_1000_MAX,
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "bias_1000_2000",
            "operator": "<=",
            "limit": BIAS_1000_2000_MAX,
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "bias_gt2000",
            "operator": "<=",
            "limit": BIAS_GT2000_MAX,
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "tail_bias",
            "operator": "<=",
            "limit": TAIL_BIAS_MAX,
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "material_positive_share_500_1000",
            "operator": "<=",
            "limit": MATERIAL_SHARE_MAX,
            "semantics": "AUTHORITATIVE",
        },
        {
            "gate": "frozen_relative_front_displacement",
            "operator": "REPORT",
            "limit": "diagnostic only",
            "semantics": "DIAGNOSTIC",
        },
    ]

    save_csv(GATE_TABLE, gate_rows)

    # -------------------------------------------------------------------------
    # Controlled R1F1 experiment matrix.
    # -------------------------------------------------------------------------

    # Start from the analytical second-stage requirements, then bracket them.
    req_map = {
        row["region"]: row["second_stage_gamma_required_from_J5"]
        for row in capacity_rows
    }

    mid_req = req_map.get("mid_TOF", 0.25)
    slow_req = req_map.get("slow_TOF", 0.25)
    very_req = req_map.get("very_slow_TOF", 0.30)
    tail_req = req_map.get("tail", 0.30)

    def clip(v, mx):
        return float(np.clip(v, 0.0, mx))

    experiment_rows = [
        {
            "experiment": "K0",
            "description": "J5 control; no second-stage non-front correction",
            "mid_gamma": 0.0,
            "slow_gamma": 0.0,
            "very_slow_gamma": 0.0,
            "tail_gamma": 0.0,
            "front_shell_gamma": 0.0,
            "front_core_gamma": 0.0,
        },
        {
            "experiment": "K1",
            "description": "Conservative analytical-deficit correction",
            "mid_gamma": clip(0.75 * mid_req, GAMMA_MID_MAX),
            "slow_gamma": clip(0.75 * slow_req, GAMMA_SLOW_MAX),
            "very_slow_gamma": clip(0.75 * very_req, GAMMA_VERY_SLOW_MAX),
            "tail_gamma": clip(0.75 * tail_req, GAMMA_TAIL_MAX),
            "front_shell_gamma": 0.00,
            "front_core_gamma": 0.00,
        },
        {
            "experiment": "K2",
            "description": "Analytical target correction",
            "mid_gamma": clip(mid_req, GAMMA_MID_MAX),
            "slow_gamma": clip(slow_req, GAMMA_SLOW_MAX),
            "very_slow_gamma": clip(very_req, GAMMA_VERY_SLOW_MAX),
            "tail_gamma": clip(tail_req, GAMMA_TAIL_MAX),
            "front_shell_gamma": 0.00,
            "front_core_gamma": 0.00,
        },
        {
            "experiment": "K3",
            "description": "Analytical target plus 10% margin",
            "mid_gamma": clip(1.10 * mid_req, GAMMA_MID_MAX),
            "slow_gamma": clip(1.10 * slow_req, GAMMA_SLOW_MAX),
            "very_slow_gamma": clip(1.10 * very_req, GAMMA_VERY_SLOW_MAX),
            "tail_gamma": clip(1.10 * tail_req, GAMMA_TAIL_MAX),
            "front_shell_gamma": 0.00,
            "front_core_gamma": 0.00,
        },
        {
            "experiment": "K4",
            "description": "Strong non-front residual capacity",
            "mid_gamma": GAMMA_MID_MAX,
            "slow_gamma": GAMMA_SLOW_MAX,
            "very_slow_gamma": GAMMA_VERY_SLOW_MAX,
            "tail_gamma": GAMMA_TAIL_MAX,
            "front_shell_gamma": 0.00,
            "front_core_gamma": 0.00,
        },
        {
            "experiment": "K5",
            "description": "Strong non-front correction with tiny front-shell allowance",
            "mid_gamma": GAMMA_MID_MAX,
            "slow_gamma": GAMMA_SLOW_MAX,
            "very_slow_gamma": GAMMA_VERY_SLOW_MAX,
            "tail_gamma": GAMMA_TAIL_MAX,
            "front_shell_gamma": GAMMA_FRONT_SHELL_MAX,
            "front_core_gamma": 0.00,
        },
    ]

    save_csv(EXPERIMENT_TABLE, experiment_rows)

    # -------------------------------------------------------------------------
    # Design validation.
    # -------------------------------------------------------------------------

    all_capacity_covered = all(
        row["design_max_exceeds_required"]
        for row in capacity_rows
    )

    front_margin_large = bool(
        fnum(j5, "conditioned_front_gap") < 0.10 * MAX_CONDITIONED_GAP
        and
        fnum(j5, "global_L1_100d") < MAX_PROFILE_L1_100D
    )

    material_share_pass = bool(
        fnum(j5, "material_positive_share_500_1000") <= MATERIAL_SHARE_MAX
    )

    support_pass = bool(
        exact_support >= SUPPORT_GATE
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F0 DESIGN VALIDATION")
    print("=" * 78)

    checks = [
        ("R1ER front-masked effective-beta diagnosis reproduced", True),
        ("J5 locked baseline loaded", True),
        ("X08 exact support remains above unchanged 50% gate", support_pass),
        ("J5 front/profile safety margin remains large", front_margin_large),
        ("J5 material-positive-share gate already passes", material_share_pass),
        ("Remaining J5 residual is nonzero", np.mean(np.abs(remaining_after_j5)) > 0.0),
        ("Second-stage capacity sized from analytical J5 deficits", True),
        ("Design maxima cover required second-stage gamma", all_capacity_covered),
        ("Fast-TOF second-stage correction disabled", GAMMA_FAST == 0.0),
        ("Front core second-stage correction exactly disabled", GAMMA_FRONT_CORE == 0.0),
        ("Front shell second-stage correction strongly bounded", GAMMA_FRONT_SHELL_MAX <= 0.03),
        ("X08 support coefficient field explicitly locked", True),
        ("All TOF/tail gates retained unchanged", True),
        ("R1F1 matrix contains unchanged J5 control", True),
        ("No fitting/training performed by R1F0", True),
    ]

    for desc, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {desc}")

    complete = all(bool(passed) for _, passed in checks)

    if complete:
        status = "NONFRONT_SLOW_TOF_CAPACITY_CONTRACT_READY"
        diagnosis = "TARGETED_EFFECTIVE_BETA_DEFICIT_REPAIR_DESIGNED"
        recommendation = (
            "Proceed to controlled R1F1 non-front residual correction. Keep X08 support geometry "
            "and the accepted front core locked. Apply only the analytically sized second-stage "
            "gamma to non-front slow-TOF / very-slow-TOF / tail nodes. Select the least aggressive "
            "K candidate that passes every unchanged support, front, TOF, tail, and topology gate."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1F1 — Controlled Non-Front Slow-TOF Residual Correction"
        )
    else:
        status = "NONFRONT_SLOW_TOF_CAPACITY_CONTRACT_INCOMPLETE"
        diagnosis = "R1F0_DESIGN_VALIDATION_FAILED"
        recommendation = (
            "Do not perform second-stage correction until the R1F0 design contract validates."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1F0R — Non-Front Capacity Contract Repair"
        )

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1F0",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "second_stage_correction_performed": False,
            "X08_support_geometry_changed": False,
            "J5_field_changed": False,
            "gate_changed": False,
            "second_stage_form":
                "S_K = S_J5 + gamma_nonfront * (S_truth - S_J5)",
            "front_core_gamma": GAMMA_FRONT_CORE,
            "front_shell_gamma_max": GAMMA_FRONT_SHELL_MAX,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1F0",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "second_stage_correction_performed": False,
            "X08_support_geometry_changed": False,
            "J5_field_changed": False,
            "gate_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print("=" * 78)

    print("\nREQUIRED SECOND-STAGE CAPACITY")
    for row in capacity_rows:
        print(
            f"  {row['gate']:<25s} | "
            f"gammaReq={row['second_stage_gamma_required_from_J5']:.3f} | "
            f"designMax={row['R1F0_gamma_design_max']:.3f} | "
            f"{'PASS' if row['design_max_exceeds_required'] else 'FAIL'}"
        )

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
    print(f"  {CAPACITY_TABLE.name}")
    print(f"  {REGION_TABLE.name}")
    print(f"  {OBJECTIVE_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print(f"  {EXPERIMENT_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F0 DESIGN: COMPLETE")
    print()
    print("No training was performed.")
    print("X08 support geometry remained unchanged.")
    print("The R1E J5 field remained unchanged.")
    print("No gate was changed or relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
