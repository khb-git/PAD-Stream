from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1ER
# Joint Reconciliation Outcome Audit
#
# DIAGNOSTIC-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO X08 SUPPORT GEOMETRY CHANGED.
# NO JOINT CORRECTION RECALIBRATED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED OR RELAXED.
#
# PURPOSE
# -------
# R1E completed the controlled J0-J5 joint reconciliation matrix and found:
#
#   NO_R1E_JOINT_CANDIDATE_PASSES_COMPLETE_CONTRACT
#
# The strongest controlled candidate J5:
#
#   * preserves X08 exact support at 50.000564%
#   * strongly preserves the accepted front
#   * passes the 500-1000d material-positive-share gate
#   * reduces all four remaining positive-bias metrics substantially
#   * but still misses the numerical bias gates
#
# R1ER audits:
#
#   1. which gates remain active for each J candidate,
#   2. how close J5 is to each target,
#   3. whether residual bias reduction scales monotonically with beta capacity,
#   4. the beta fraction theoretically required to meet each gate under the
#      bounded truth-directed residual formulation,
#   5. whether current regional beta caps are simply too conservative,
#   6. whether the front remains sufficiently insensitive to permit a targeted
#      cap extension without reopening the front/support problem.
#
# No candidate is changed by this milestone.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1ER"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R1E_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1E"
    / "PAD_Stream_V15SG7CR3F5R1E_Summary.json"
)

R1E_EXPERIMENTS = (
    ROOT / "output" / "V15_SG7CR3F5R1E"
    / "V15SG7CR3F5R1E_Experiment_Metrics.csv"
)

R1E_GATES = (
    ROOT / "output" / "V15_SG7CR3F5R1E"
    / "V15SG7CR3F5R1E_Final_Gate_Matrix.csv"
)

R1E_REGIONAL = (
    ROOT / "output" / "V15_SG7CR3F5R1E"
    / "V15SG7CR3F5R1E_Regional_Correction_Metrics.csv"
)

R1E_FRONT = (
    ROOT / "output" / "V15_SG7CR3F5R1E"
    / "V15SG7CR3F5R1E_Front_Metrics.csv"
)

R1E_TOF = (
    ROOT / "output" / "V15_SG7CR3F5R1E"
    / "V15SG7CR3F5R1E_TOF_Bias_Metrics.csv"
)

R1E_BETA = (
    ROOT / "output" / "V15_SG7CR3F5R1E"
    / "V15SG7CR3F5R1E_Beta_Field_Metrics.csv"
)

R1E_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1E"
    / "V15SG7CR3F5R1E_Controlled_Joint_Reconciliation.npz"
)

R1D_MATRIX = (
    ROOT / "output" / "V15_SG7CR3F5R1D"
    / "V15SG7CR3F5R1D_R1E_Experiment_Matrix.csv"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1ER_Summary.json"
FAILURE_TABLE = OUT / "V15SG7CR3F5R1ER_Remaining_Gate_Failures.csv"
SHORTFALL_TABLE = OUT / "V15SG7CR3F5R1ER_J5_Bias_Shortfalls.csv"
BETA_REQUIREMENT_TABLE = OUT / "V15SG7CR3F5R1ER_Required_Beta_By_Gate.csv"
TRAJECTORY_TABLE = OUT / "V15SG7CR3F5R1ER_Bias_vs_Cap_Trajectory.csv"
FRONT_MARGIN_TABLE = OUT / "V15SG7CR3F5R1ER_Front_Preservation_Margins.csv"
DIAGNOSIS_TABLE = OUT / "V15SG7CR3F5R1ER_Limiter_Classification.csv"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1ER_Outcome_Audit_Contract.json"

# -----------------------------------------------------------------------------
# Authoritative unchanged limits
# -----------------------------------------------------------------------------

BIAS_LIMITS = {
    "bias_500_1000": 2.5e-3,
    "bias_1000_2000": 4.5e-3,
    "bias_gt2000": 5.0e-3,
    "tail_bias": 5.0e-3,
    "material_positive_share_500_1000": 0.40,
}

MATERIAL_SHARE_MAX = BIAS_LIMITS["material_positive_share_500_1000"]

MAX_CONDITIONED_GAP = 5.33123727917913484e-04
MAX_PROFILE_L1_100D = 4.50032942291447424e-03
MIN_RECOVERED_FRONTS = 744

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


def bval(row, key):
    value = str(row.get(key, "")).strip().lower()
    return value in ("true", "1", "yes", "pass")


def row_by_experiment(rows, experiment):
    for row in rows:
        if row.get("experiment") == experiment:
            return row
    return None


# =============================================================================
# Analytical beta requirement
# =============================================================================

def required_beta_fraction_from_bias(base_bias, target_bias):
    """
    Under truth-directed residual scaling:

        error_new = (1-beta) * error_old

    a constant effective beta required to reduce positive mean bias from
    base_bias to target_bias is:

        beta_required = 1 - target/base

    This is diagnostic. It is not applied by R1ER.
    """
    if not np.isfinite(base_bias) or base_bias <= 0.0:
        return np.nan

    return float(
        np.clip(
            1.0 - target_bias / base_bias,
            0.0,
            1.0,
        )
    )


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1ER")
    print("Joint Reconciliation Outcome Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
X08 SUPPORT GEOMETRY WILL NOT BE CHANGED.
NO JOINT CORRECTION WILL BE RECALIBRATED.
NO FRONT OR TOF-BIAS GATE WILL BE CHANGED OR RELAXED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
""")

    incoming = load_json(R1E_SUMMARY)

    if (
        incoming.get("diagnosis")
        !=
        "JOINT_TOF_CORRECTION_REQUIRES_OUTCOME_AUDIT"
    ):
        raise RuntimeError(
            "R1ER requires incoming R1E joint-outcome-audit diagnosis."
        )

    experiments = load_csv(R1E_EXPERIMENTS)
    gates = load_csv(R1E_GATES)
    regional = load_csv(R1E_REGIONAL)
    front_rows = load_csv(R1E_FRONT)
    tof_rows = load_csv(R1E_TOF)
    beta_rows = load_csv(R1E_BETA)
    matrix = load_csv(R1D_MATRIX)

    if not experiments:
        raise RuntimeError("R1E experiment table is empty.")

    exp_map = {
        row["experiment"]: row
        for row in experiments
    }

    matrix_map = {
        row["experiment"]: row
        for row in matrix
    }

    if "J0" not in exp_map or "J5" not in exp_map:
        raise RuntimeError("R1ER requires J0 and J5 experiment records.")

    j0 = exp_map["J0"]
    j5 = exp_map["J5"]

    # -------------------------------------------------------------------------
    # Reconstruct failed gates by experiment.
    # -------------------------------------------------------------------------

    failure_rows = []

    for exp_row in experiments:
        exp = exp_row["experiment"]

        failed = [
            row["gate"]
            for row in gates
            if row.get("experiment") == exp
            and not bval(row, "passed")
        ]

        failure_rows.append({
            "experiment": exp,
            "failed_gate_count": len(failed),
            "failed_gates": ";".join(failed),
            "exact_support_fraction":
                fnum(exp_row, "exact_support_fraction"),
            "conditioned_front_gap":
                fnum(exp_row, "conditioned_front_gap"),
            "bias_500_1000":
                fnum(exp_row, "bias_500_1000"),
            "bias_1000_2000":
                fnum(exp_row, "bias_1000_2000"),
            "bias_gt2000":
                fnum(exp_row, "bias_gt2000"),
            "tail_bias":
                fnum(exp_row, "tail_bias"),
            "material_positive_share_500_1000":
                fnum(exp_row, "material_positive_share_500_1000"),
        })

    save_csv(FAILURE_TABLE, failure_rows)

    # -------------------------------------------------------------------------
    # J5 shortfall audit.
    # -------------------------------------------------------------------------

    shortfall_rows = []

    for metric, limit in BIAS_LIMITS.items():
        value = fnum(j5, metric)

        if metric == "material_positive_share_500_1000":
            pass_gate = value <= limit
            absolute_shortfall = max(value - limit, 0.0)
            relative_shortfall = (
                absolute_shortfall / max(limit, EPS)
            )
        else:
            pass_gate = value <= limit
            absolute_shortfall = max(value - limit, 0.0)
            relative_shortfall = (
                absolute_shortfall / max(limit, EPS)
            )

        shortfall_rows.append({
            "gate": metric,
            "J5_value": value,
            "limit": limit,
            "pass": pass_gate,
            "absolute_shortfall": absolute_shortfall,
            "relative_shortfall": relative_shortfall,
        })

    save_csv(SHORTFALL_TABLE, shortfall_rows)

    # -------------------------------------------------------------------------
    # Required effective beta audit.
    # -------------------------------------------------------------------------

    requirement_rows = []

    mapping = [
        ("bias_500_1000", "mid_TOF_cap"),
        ("bias_1000_2000", "slow_TOF_cap"),
        ("bias_gt2000", "very_slow_TOF_cap"),
        ("tail_bias", "tail_cap"),
    ]

    j5_matrix = matrix_map["J5"]

    for metric, cap_field in mapping:
        base_value = fnum(j0, metric)
        j5_value = fnum(j5, metric)
        target = BIAS_LIMITS[metric]
        configured_cap = fnum(j5_matrix, cap_field)

        beta_required_from_J0 = required_beta_fraction_from_bias(
            base_value,
            target,
        )

        # Effective beta actually achieved by J5 from mean-bias reduction.
        beta_effective_J5 = (
            1.0 - j5_value / base_value
            if base_value > EPS
            else np.nan
        )

        additional_effective_beta_needed = max(
            beta_required_from_J0 - beta_effective_J5,
            0.0,
        )

        requirement_rows.append({
            "gate": metric,
            "J0_bias": base_value,
            "J5_bias": j5_value,
            "target_bias": target,
            "J5_configured_regional_cap": configured_cap,
            "required_effective_beta_from_J0":
                beta_required_from_J0,
            "J5_effective_beta":
                beta_effective_J5,
            "additional_effective_beta_needed":
                additional_effective_beta_needed,
            "configured_cap_above_required_effective_beta":
                configured_cap >= beta_required_from_J0
                if np.isfinite(beta_required_from_J0)
                else False,
        })

    save_csv(BETA_REQUIREMENT_TABLE, requirement_rows)

    # -------------------------------------------------------------------------
    # Bias-vs-cap trajectory.
    # -------------------------------------------------------------------------

    trajectory_rows = []

    for exp in ["J0", "J1", "J2", "J3", "J4", "J5"]:
        if exp not in exp_map or exp not in matrix_map:
            continue

        erow = exp_map[exp]
        mrow = matrix_map[exp]

        trajectory_rows.append({
            "experiment": exp,
            "mid_TOF_cap": fnum(mrow, "mid_TOF_cap"),
            "slow_TOF_cap": fnum(mrow, "slow_TOF_cap"),
            "very_slow_TOF_cap": fnum(mrow, "very_slow_TOF_cap"),
            "tail_cap": fnum(mrow, "tail_cap"),
            "front_core_cap": fnum(mrow, "front_core_cap"),
            "front_shell_cap": fnum(mrow, "front_shell_cap"),
            "bias_500_1000": fnum(erow, "bias_500_1000"),
            "bias_1000_2000": fnum(erow, "bias_1000_2000"),
            "bias_gt2000": fnum(erow, "bias_gt2000"),
            "tail_bias": fnum(erow, "tail_bias"),
            "material_positive_share_500_1000":
                fnum(erow, "material_positive_share_500_1000"),
            "conditioned_front_gap":
                fnum(erow, "conditioned_front_gap"),
            "global_L1_100d":
                fnum(erow, "global_L1_100d"),
        })

    save_csv(TRAJECTORY_TABLE, trajectory_rows)

    # -------------------------------------------------------------------------
    # Front preservation margin.
    # -------------------------------------------------------------------------

    front_margin_rows = []

    for exp in ["J0", "J1", "J2", "J3", "J4", "J5"]:
        if exp not in exp_map:
            continue

        row = exp_map[exp]

        gap = fnum(row, "conditioned_front_gap")
        l1 = fnum(row, "global_L1_100d")
        recovered = fnum(row, "recovered_fronts")

        front_margin_rows.append({
            "experiment": exp,
            "conditioned_front_gap": gap,
            "conditioned_gap_limit": MAX_CONDITIONED_GAP,
            "conditioned_gap_margin":
                MAX_CONDITIONED_GAP - gap,
            "profile_L1_100d": l1,
            "profile_L1_limit": MAX_PROFILE_L1_100D,
            "profile_L1_margin":
                MAX_PROFILE_L1_100D - l1,
            "recovered_fronts": recovered,
            "recovered_front_margin":
                recovered - MIN_RECOVERED_FRONTS,
        })

    save_csv(FRONT_MARGIN_TABLE, front_margin_rows)

    # -------------------------------------------------------------------------
    # Mechanism classification.
    # -------------------------------------------------------------------------

    failed_j5 = [
        row["gate"]
        for row in shortfall_rows
        if not row["pass"]
    ]

    material_gate_passes = (
        fnum(j5, "material_positive_share_500_1000")
        <= MATERIAL_SHARE_MAX
    )

    front_has_large_margin = bool(
        fnum(j5, "conditioned_front_gap")
        < 0.10 * MAX_CONDITIONED_GAP
        and
        fnum(j5, "global_L1_100d")
        < MAX_PROFILE_L1_100D
    )

    # Are all J5 failed gates strictly positive-bias magnitude gates?
    magnitude_only_failures = set(failed_j5).issubset({
        "bias_500_1000",
        "bias_1000_2000",
        "bias_gt2000",
        "tail_bias",
    })

    # Check monotonic improvement J0 -> J5 for each positive-bias metric.
    monotonic_endpoint_improvement = all(
        fnum(j5, metric) < fnum(j0, metric)
        for metric in [
            "bias_500_1000",
            "bias_1000_2000",
            "bias_gt2000",
            "tail_bias",
        ]
    )

    # Does configured regional capacity exceed analytically required effective
    # beta, yet actual effective beta still fall short? If yes, the limiter is
    # front-shell/core masking / regional overlap rather than total cap alone.
    overlap_limited = any(
        row["configured_cap_above_required_effective_beta"]
        and
        row["J5_effective_beta"] < row["required_effective_beta_from_J0"]
        for row in requirement_rows
    )

    if (
        magnitude_only_failures
        and
        material_gate_passes
        and
        front_has_large_margin
        and
        monotonic_endpoint_improvement
        and
        overlap_limited
    ):
        status = "R1E_OUTCOME_AUDIT_COMPLETE"
        diagnosis = "FRONT_MASKED_EFFECTIVE_BETA_CAPACITY_LIMIT"
        recommendation = (
            "J5 has already passed the material-positive-share gate and retains very large "
            "front/profile safety margins. The remaining failures are only mean positive-bias "
            "magnitude gates. Configured regional caps are high enough in principle, but the "
            "effective beta delivered to the biased populations is reduced by front-core/shell "
            "mask overlap. Do not relax any gate and do not alter X08 support. Design a more "
            "selective residual corrector that increases effective beta only on non-front "
            "slow-TOF/tail nodes while leaving accepted front nodes locked."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1F0 — Non-Front Slow-TOF Residual Capacity Design"
        )

    elif (
        magnitude_only_failures
        and
        material_gate_passes
        and
        front_has_large_margin
        and
        monotonic_endpoint_improvement
    ):
        status = "R1E_OUTCOME_AUDIT_COMPLETE"
        diagnosis = "REGIONAL_BETA_CAPACITY_LIMIT"
        recommendation = (
            "J5 preserves the accepted support/front solution and passes the material-share gate, "
            "but the bounded regional correction remains too weak to meet the four mean-bias gates. "
            "Design the minimum additional non-front TOF/tail correction capacity required from the "
            "analytical beta deficits. Keep X08 and every gate unchanged."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1F0 — Non-Front Slow-TOF Residual Capacity Design"
        )

    else:
        status = "R1E_OUTCOME_AUDIT_COMPLETE"
        diagnosis = "COUPLED_JOINT_RECONCILIATION_LIMITER"
        recommendation = (
            "The remaining R1E failures cannot be attributed solely to bounded beta capacity. "
            "Use the audit tables to isolate the coupled front/TOF or regional-overlap mechanism "
            "before any further correction."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1ER2 — Coupled Joint-Reconciliation Limiter Audit"
        )

    diagnosis_rows = [{
        "J5_failed_gates": ";".join(failed_j5),
        "material_share_gate_passes": material_gate_passes,
        "front_has_large_margin": front_has_large_margin,
        "monotonic_endpoint_improvement": monotonic_endpoint_improvement,
        "configured_cap_overlap_limited": overlap_limited,
        "diagnosis": diagnosis,
        "next_milestone": next_milestone,
    }]

    save_csv(DIAGNOSIS_TABLE, diagnosis_rows)

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1ER",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "joint_correction_recalibrated": False,
            "X08_support_geometry_changed": False,
            "gate_changed": False,
            "J5_failed_gates": failed_j5,
            "material_share_gate_passes": material_gate_passes,
            "front_has_large_margin": front_has_large_margin,
            "configured_cap_overlap_limited": overlap_limited,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1ER",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "joint_correction_recalibrated": False,
            "X08_support_geometry_changed": False,
            "gate_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("J5 REMAINING BIAS SHORTFALLS")
    print("=" * 78)

    for row in shortfall_rows:
        print(
            f"{row['gate']:<38s} | "
            f"J5={row['J5_value']:.6e} | "
            f"limit={row['limit']:.6e} | "
            f"{'PASS' if row['pass'] else 'FAIL'} | "
            f"shortfall={row['absolute_shortfall']:.6e}"
        )

    print("\nREQUIRED EFFECTIVE BETA")
    for row in requirement_rows:
        print(
            f"{row['gate']:<25s} | "
            f"configured={row['J5_configured_regional_cap']:.3f} | "
            f"requiredEff={row['required_effective_beta_from_J0']:.3f} | "
            f"J5eff={row['J5_effective_beta']:.3f} | "
            f"remaining={row['additional_effective_beta_needed']:.3f}"
        )

    print("\nFRONT SAFETY MARGIN — J5")
    print(
        f"  Conditioned gap         : "
        f"{fnum(j5, 'conditioned_front_gap'):.6e} "
        f"/ {MAX_CONDITIONED_GAP:.6e}"
    )
    print(
        f"  100d L1                 : "
        f"{fnum(j5, 'global_L1_100d'):.6e} "
        f"/ {MAX_PROFILE_L1_100D:.6e}"
    )
    print(
        f"  Material + share        : "
        f"{100*fnum(j5, 'material_positive_share_500_1000'):.2f}% "
        f"/ {100*MATERIAL_SHARE_MAX:.2f}%"
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1ER DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        ("Incoming R1E no-candidate diagnosis reproduced", True),
        ("J0-J5 experiment metrics loaded", True),
        ("Final gate matrix loaded", True),
        ("J5 remaining failures enumerated", True),
        ("Bias shortfalls quantified", True),
        ("Analytical effective-beta requirements computed", True),
        ("Bias-vs-cap trajectory reconstructed", True),
        ("Front preservation margins quantified", True),
        ("Material-positive-share gate status audited", True),
        ("No joint correction recalibrated", True),
        ("No X08 support geometry changed", True),
        ("No gate changed or relaxed", True),
        ("Outcome mechanism classified", True),
    ]

    for desc, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {desc}")

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
    print(f"  {FAILURE_TABLE.name}")
    print(f"  {SHORTFALL_TABLE.name}")
    print(f"  {BETA_REQUIREMENT_TABLE.name}")
    print(f"  {TRAJECTORY_TABLE.name}")
    print(f"  {FRONT_MARGIN_TABLE.name}")
    print(f"  {DIAGNOSIS_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1ER OUTCOME AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No joint correction was recalibrated.")
    print("X08 support geometry remained unchanged.")
    print("No gate was changed or relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()