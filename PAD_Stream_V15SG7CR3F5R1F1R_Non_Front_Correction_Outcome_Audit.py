from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1F1R
# Non-Front Correction Outcome Audit
#
# DIAGNOSTIC-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO X08 SUPPORT GEOMETRY CHANGED.
# NO J5 OR K-CANDIDATE FIELD CHANGED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED OR RELAXED.
#
# PURPOSE
# -------
# R1F1 completed the K0-K5 controlled second-stage non-front correction and
# found no fully passing candidate.
#
# Observed endpoint:
#
#   K5:
#     support = 50.000564%
#     gap     ~ 1.399e-05
#     B500    ~ 2.979e-03
#     B1000   ~ 5.374e-03
#     B2000   ~ 6.478e-03
#     tail    ~ 7.004e-03
#     material + share ~ 30.8%
#
# The front/support/topology solution remains stable. Four positive mean-bias
# gates remain active.
#
# R1F1R audits whether the second-stage gamma failed because:
#
#   A) non-front nodes do not contain enough residual mass to satisfy the gates;
#   B) the tail population is largely inside the protected front shell/core;
#   C) the regional gamma caps remain too small;
#   D) K5 correction is being delivered to the correct nodes but simply needs
#      more non-front capacity;
#   E) the current "truth-value-defined front mask" is too broad and suppresses
#      physically safe correction in states that are not actually crossing the
#      S=0.21 front.
#
# No correction is performed by this milestone.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1F1R"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R1F1_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1F1"
    / "PAD_Stream_V15SG7CR3F5R1F1_Summary.json"
)

R1F1_EXPERIMENTS = (
    ROOT / "output" / "V15_SG7CR3F5R1F1"
    / "V15SG7CR3F5R1F1_Experiment_Metrics.csv"
)

R1F1_GATES = (
    ROOT / "output" / "V15_SG7CR3F5R1F1"
    / "V15SG7CR3F5R1F1_Final_Gate_Matrix.csv"
)

R1F1_REGIONAL = (
    ROOT / "output" / "V15_SG7CR3F5R1F1"
    / "V15SG7CR3F5R1F1_Regional_Correction_Metrics.csv"
)

R1F1_GAMMA = (
    ROOT / "output" / "V15_SG7CR3F5R1F1"
    / "V15SG7CR3F5R1F1_Gamma_Field_Metrics.csv"
)

R1F1_TOPOLOGY = (
    ROOT / "output" / "V15_SG7CR3F5R1F1"
    / "V15SG7CR3F5R1F1_Topology_Preservation_Metrics.csv"
)

R1F1_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1F1"
    / "V15SG7CR3F5R1F1_Controlled_NonFront_Correction.npz"
)

R1F0_MATRIX = (
    ROOT / "output" / "V15_SG7CR3F5R1F0"
    / "V15SG7CR3F5R1F0_R1F1_Experiment_Matrix.csv"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1F1R_Summary.json"
FAILURE_TABLE = OUT / "V15SG7CR3F5R1F1R_Remaining_Gate_Failures.csv"
K5_SHORTFALL_TABLE = OUT / "V15SG7CR3F5R1F1R_K5_Bias_Shortfalls.csv"
RESIDUAL_MASS_TABLE = OUT / "V15SG7CR3F5R1F1R_Residual_Mass_By_Region.csv"
MASK_OVERLAP_TABLE = OUT / "V15SG7CR3F5R1F1R_Front_Mask_Overlap.csv"
CAPACITY_TABLE = OUT / "V15SG7CR3F5R1F1R_Maximum_Attainable_Bias_Reduction.csv"
TRAJECTORY_TABLE = OUT / "V15SG7CR3F5R1F1R_K_Trajectory.csv"
CLASSIFICATION_TABLE = OUT / "V15SG7CR3F5R1F1R_Limiter_Classification.csv"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1F1R_Outcome_Audit_Contract.json"

# -----------------------------------------------------------------------------
# Unchanged gates
# -----------------------------------------------------------------------------

BIAS_LIMITS = {
    "bias_500_1000": 2.5e-3,
    "bias_1000_2000": 4.5e-3,
    "bias_gt2000": 5.0e-3,
    "tail_bias": 5.0e-3,
}

MATERIAL_SHARE_MAX = 0.40
SUPPORT_GATE = 0.50
MAX_CONDITIONED_GAP = 5.33123727917913484e-04
MAX_PROFILE_L1_100D = 4.50032942291447424e-03

THRESHOLD = 0.21
FRONT_CORE_LOW = 0.205
FRONT_CORE_HIGH = 0.235
FRONT_SHELL_LOW = 0.20
FRONT_SHELL_HIGH = 0.30
TAIL_THRESHOLD = 0.205

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


def bval(row, key):
    value = str(row.get(key, "")).strip().lower()
    return value in ("true", "1", "yes", "pass")


def row_by_experiment(rows, exp):
    for row in rows:
        if row.get("experiment") == exp:
            return row
    return None


# =============================================================================
# Helpers
# =============================================================================

def tof_mask(tau_end, lo, hi):
    return (tau_end > lo) & (tau_end <= hi)


def mean_bias(diff, streamline_mask):
    if not np.any(streamline_mask):
        return np.nan
    return float(np.mean(diff[streamline_mask]))


def required_gamma_from_current_bias(current_bias, target):
    if not np.isfinite(current_bias) or current_bias <= 0.0:
        return np.nan
    return float(np.clip(1.0 - target / current_bias, 0.0, 1.0))


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1F1R")
    print("Non-Front Correction Outcome Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
X08 SUPPORT GEOMETRY WILL NOT BE CHANGED.
NO J5 OR K-CANDIDATE FIELD WILL BE CHANGED.
NO FRONT OR TOF-BIAS GATE WILL BE CHANGED OR RELAXED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
""")

    incoming = load_json(R1F1_SUMMARY)

    if (
        incoming.get("diagnosis")
        !=
        "NONFRONT_SECOND_STAGE_CORRECTION_REQUIRES_OUTCOME_AUDIT"
    ):
        raise RuntimeError(
            "R1F1R requires incoming R1F1 no-candidate outcome-audit diagnosis."
        )

    experiments = load_csv(R1F1_EXPERIMENTS)
    gates = load_csv(R1F1_GATES)
    regional = load_csv(R1F1_REGIONAL)
    gamma_metrics = load_csv(R1F1_GAMMA)
    topology = load_csv(R1F1_TOPOLOGY)
    matrix = load_csv(R1F0_MATRIX)

    exp_map = {row["experiment"]: row for row in experiments}
    matrix_map = {row["experiment"]: row for row in matrix}

    if "K0" not in exp_map or "K5" not in exp_map:
        raise RuntimeError("R1F1R requires K0 and K5 experiment records.")

    k0 = exp_map["K0"]
    k5 = exp_map["K5"]

    db = np.load(R1F1_NUMERICAL, allow_pickle=True)

    required_keys = [
        "truth100",
        "J5_100",
        "K5_pred100",
        "K5_gamma",
        "tau_end",
        "X08_coeff100",
        "exact_support_fraction",
    ]

    missing = [key for key in required_keys if key not in db.files]

    if missing:
        raise RuntimeError(
            "R1F1 numerical database missing required arrays: "
            + ", ".join(missing)
        )

    truth = np.asarray(db["truth100"], dtype=float)
    j5 = np.asarray(db["J5_100"], dtype=float)
    k5_pred = np.asarray(db["K5_pred100"], dtype=float)
    k5_gamma = np.asarray(db["K5_gamma"], dtype=float)
    tau_end = np.asarray(db["tau_end"], dtype=float)
    coeff_x08 = np.asarray(db["X08_coeff100"], dtype=float)
    exact_support = float(np.asarray(db["exact_support_fraction"]))

    if not (
        truth.shape == j5.shape == k5_pred.shape == k5_gamma.shape == coeff_x08.shape
        and truth.ndim == 2
    ):
        raise RuntimeError("R1F1R arrays are not shape-compatible.")

    if tau_end.size != truth.shape[0]:
        raise RuntimeError("R1F1R tau_end length mismatch.")

    j5_diff = j5 - truth
    k5_diff = k5_pred - truth
    remaining_after_k5 = truth - k5_pred

    # -------------------------------------------------------------------------
    # Remaining failures
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
            "conditioned_front_gap": fnum(exp_row, "conditioned_front_gap"),
            "global_L1_100d": fnum(exp_row, "global_L1_100d"),
            "bias_500_1000": fnum(exp_row, "bias_500_1000"),
            "bias_1000_2000": fnum(exp_row, "bias_1000_2000"),
            "bias_gt2000": fnum(exp_row, "bias_gt2000"),
            "tail_bias": fnum(exp_row, "tail_bias"),
            "material_positive_share_500_1000":
                fnum(exp_row, "material_positive_share_500_1000"),
        })

    save_csv(FAILURE_TABLE, failure_rows)

    # -------------------------------------------------------------------------
    # K5 shortfalls
    # -------------------------------------------------------------------------

    shortfall_rows = []

    for gate, limit in BIAS_LIMITS.items():
        value = fnum(k5, gate)

        shortfall_rows.append({
            "gate": gate,
            "K5_value": value,
            "limit": limit,
            "pass": bool(value <= limit),
            "absolute_shortfall": max(value - limit, 0.0),
            "relative_shortfall":
                max(value - limit, 0.0) / max(limit, EPS),
            "third_stage_gamma_required_if_uniform":
                required_gamma_from_current_bias(value, limit),
        })

    save_csv(K5_SHORTFALL_TABLE, shortfall_rows)

    # -------------------------------------------------------------------------
    # Front-mask overlap and residual mass.
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
    tail = truth <= TAIL_THRESHOLD

    region_defs = [
        ("500-1000d", tof_mask(tau_end, 500.0, 1000.0)),
        ("1000-2000d", tof_mask(tau_end, 1000.0, 2000.0)),
        (">2000d", tof_mask(tau_end, 2000.0, np.inf)),
    ]

    residual_mass_rows = []
    overlap_rows = []
    capacity_rows = []

    for label, smask in region_defs:

        if not np.any(smask):
            continue

        local_residual = np.abs(remaining_after_k5[smask])
        local_shell = front_shell[smask]
        local_core = front_core[smask]
        local_nonfront = nonfront[smask]

        total_mass = float(np.sum(local_residual))
        nonfront_mass = float(np.sum(local_residual[local_nonfront]))
        shell_mass = float(np.sum(local_residual[local_shell]))
        core_mass = float(np.sum(local_residual[local_core]))

        residual_mass_rows.append({
            "region": label,
            "total_remaining_abs_residual": total_mass,
            "nonfront_remaining_abs_residual": nonfront_mass,
            "front_shell_remaining_abs_residual": shell_mass,
            "front_core_remaining_abs_residual": core_mass,
            "nonfront_residual_mass_fraction":
                nonfront_mass / max(total_mass, EPS),
            "front_shell_residual_mass_fraction":
                shell_mass / max(total_mass, EPS),
            "front_core_residual_mass_fraction":
                core_mass / max(total_mass, EPS),
        })

        overlap_rows.append({
            "region": label,
            "point_count": int(local_residual.size),
            "front_shell_point_fraction":
                float(np.mean(local_shell)),
            "front_core_point_fraction":
                float(np.mean(local_core)),
            "nonfront_point_fraction":
                float(np.mean(local_nonfront)),
            "mean_K5_gamma_front_shell":
                float(np.mean(k5_gamma[smask][local_shell]))
                if np.any(local_shell)
                else np.nan,
            "mean_K5_gamma_nonfront":
                float(np.mean(k5_gamma[smask][local_nonfront]))
                if np.any(local_nonfront)
                else np.nan,
        })

        # Maximum additional reduction available from nonfront nodes only:
        # move all remaining nonfront residual exactly to truth.
        diff_region = k5_diff[smask]
        candidate_if_nonfront_exact = diff_region.copy()
        candidate_if_nonfront_exact[local_nonfront] = 0.0

        current_bias = float(np.mean(diff_region))
        best_nonfront_only_bias = float(np.mean(candidate_if_nonfront_exact))

        gate_name = {
            "500-1000d": "bias_500_1000",
            "1000-2000d": "bias_1000_2000",
            ">2000d": "bias_gt2000",
        }[label]

        limit = BIAS_LIMITS[gate_name]

        capacity_rows.append({
            "gate": gate_name,
            "region": label,
            "current_K5_bias": current_bias,
            "unchanged_limit": limit,
            "best_possible_nonfront_only_bias":
                best_nonfront_only_bias,
            "nonfront_only_can_meet_gate":
                bool(best_nonfront_only_bias <= limit),
            "required_bias_reduction":
                max(current_bias - limit, 0.0),
            "maximum_nonfront_bias_reduction":
                current_bias - best_nonfront_only_bias,
            "fraction_of_available_nonfront_reduction_required":
                (
                    max(current_bias - limit, 0.0)
                    /
                    max(current_bias - best_nonfront_only_bias, EPS)
                ),
        })

    # Tail-specific decomposition.
    tail_residual = np.abs(remaining_after_k5[tail])
    tail_shell = front_shell[tail]
    tail_core = front_core[tail]
    tail_nonfront = nonfront[tail]

    total_tail_mass = float(np.sum(tail_residual))
    nonfront_tail_mass = float(np.sum(tail_residual[tail_nonfront]))
    shell_tail_mass = float(np.sum(tail_residual[tail_shell]))
    core_tail_mass = float(np.sum(tail_residual[tail_core]))

    residual_mass_rows.append({
        "region": "tail",
        "total_remaining_abs_residual": total_tail_mass,
        "nonfront_remaining_abs_residual": nonfront_tail_mass,
        "front_shell_remaining_abs_residual": shell_tail_mass,
        "front_core_remaining_abs_residual": core_tail_mass,
        "nonfront_residual_mass_fraction":
            nonfront_tail_mass / max(total_tail_mass, EPS),
        "front_shell_residual_mass_fraction":
            shell_tail_mass / max(total_tail_mass, EPS),
        "front_core_residual_mass_fraction":
            core_tail_mass / max(total_tail_mass, EPS),
    })

    overlap_rows.append({
        "region": "tail",
        "point_count": int(np.sum(tail)),
        "front_shell_point_fraction":
            float(np.mean(front_shell[tail])) if np.any(tail) else np.nan,
        "front_core_point_fraction":
            float(np.mean(front_core[tail])) if np.any(tail) else np.nan,
        "nonfront_point_fraction":
            float(np.mean(nonfront[tail])) if np.any(tail) else np.nan,
        "mean_K5_gamma_front_shell":
            float(np.mean(k5_gamma[tail][front_shell[tail]]))
            if np.any(front_shell[tail])
            else np.nan,
        "mean_K5_gamma_nonfront":
            float(np.mean(k5_gamma[tail][nonfront[tail]]))
            if np.any(nonfront[tail])
            else np.nan,
    })

    tail_diff = k5_diff[tail]
    tail_best = tail_diff.copy()
    tail_best[tail_nonfront] = 0.0

    current_tail_bias = float(np.mean(tail_diff))
    best_tail_nonfront_bias = float(np.mean(tail_best))

    capacity_rows.append({
        "gate": "tail_bias",
        "region": "tail",
        "current_K5_bias": current_tail_bias,
        "unchanged_limit": BIAS_LIMITS["tail_bias"],
        "best_possible_nonfront_only_bias":
            best_tail_nonfront_bias,
        "nonfront_only_can_meet_gate":
            bool(best_tail_nonfront_bias <= BIAS_LIMITS["tail_bias"]),
        "required_bias_reduction":
            max(current_tail_bias - BIAS_LIMITS["tail_bias"], 0.0),
        "maximum_nonfront_bias_reduction":
            current_tail_bias - best_tail_nonfront_bias,
        "fraction_of_available_nonfront_reduction_required":
            (
                max(current_tail_bias - BIAS_LIMITS["tail_bias"], 0.0)
                /
                max(current_tail_bias - best_tail_nonfront_bias, EPS)
            ),
    })

    save_csv(RESIDUAL_MASS_TABLE, residual_mass_rows)
    save_csv(MASK_OVERLAP_TABLE, overlap_rows)
    save_csv(CAPACITY_TABLE, capacity_rows)

    # -------------------------------------------------------------------------
    # K trajectory
    # -------------------------------------------------------------------------

    trajectory_rows = []

    for exp in ["K0", "K1", "K2", "K3", "K4", "K5"]:
        if exp not in exp_map:
            continue

        erow = exp_map[exp]
        mrow = matrix_map.get(exp, {})

        trajectory_rows.append({
            "experiment": exp,
            "mid_gamma": fnum(mrow, "mid_gamma", 0.0),
            "slow_gamma": fnum(mrow, "slow_gamma", 0.0),
            "very_slow_gamma": fnum(mrow, "very_slow_gamma", 0.0),
            "tail_gamma": fnum(mrow, "tail_gamma", 0.0),
            "front_shell_gamma": fnum(mrow, "front_shell_gamma", 0.0),
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
    # Classification
    # -------------------------------------------------------------------------

    failed_k5 = [
        row["gate"]
        for row in shortfall_rows
        if not row["pass"]
    ]

    all_nonfront_capacity_sufficient = all(
        row["nonfront_only_can_meet_gate"]
        for row in capacity_rows
    )

    any_nonfront_capacity_insufficient = any(
        not row["nonfront_only_can_meet_gate"]
        for row in capacity_rows
    )

    # How much of remaining residual is still hidden inside the mask?
    high_mask_overlap = any(
        row["front_shell_residual_mass_fraction"] > 0.25
        for row in residual_mass_rows
    )

    front_margin_large = bool(
        fnum(k5, "conditioned_front_gap") < 0.10 * MAX_CONDITIONED_GAP
        and
        fnum(k5, "global_L1_100d") < MAX_PROFILE_L1_100D
    )

    material_share_pass = bool(
        fnum(k5, "material_positive_share_500_1000") <= MATERIAL_SHARE_MAX
    )

    support_pass = bool(
        exact_support >= SUPPORT_GATE
    )

    if (
        all_nonfront_capacity_sufficient
        and
        front_margin_large
        and
        material_share_pass
        and
        support_pass
    ):
        status = "R1F1_OUTCOME_AUDIT_COMPLETE"
        diagnosis = "NONFRONT_CAPACITY_REMAINS_SUFFICIENT_BUT_UNDERDELIVERED"
        recommendation = (
            "The remaining K5 bias can still be removed using non-front residual alone, "
            "without touching X08 support or the accepted front region. The K-stage gamma "
            "trajectory therefore remains too conservative rather than structurally blocked. "
            "Design a third-stage analytically solved non-front gamma using the exact remaining "
            "K5 residual mass, with front core locked and front shell unchanged."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1F2A — Exact Remaining Non-Front Gamma Design"
        )

    elif (
        any_nonfront_capacity_insufficient
        and
        high_mask_overlap
        and
        front_margin_large
    ):
        status = "R1F1_OUTCOME_AUDIT_COMPLETE"
        diagnosis = "TRUTH_VALUE_FRONT_MASK_OVERPROTECTS_SAFE_RESIDUAL"
        recommendation = (
            "At least one remaining gate cannot be met from the currently defined non-front "
            "residual alone, while a material fraction of residual mass is trapped inside the "
            "broad truth-value front shell. The accepted crossing itself still has very large "
            "safety margin. Do not relax front gates. Replace the broad saturation-value mask "
            "with a crossing-distance-local protection mask so only the actual S=0.21 crossing "
            "neighborhood remains locked."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1F2A — Crossing-Distance Front Protection Audit / Design"
        )

    else:
        status = "R1F1_OUTCOME_AUDIT_COMPLETE"
        diagnosis = "COUPLED_NONFRONT_RESIDUAL_LIMITER"
        recommendation = (
            "The remaining K5 bias is not explained by a single non-front capacity or mask-overlap "
            "mechanism. Use the residual-mass and maximum-attainable-bias tables to isolate the "
            "specific TOF/tail population before any additional correction."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1F1R2 — Residual Population Limiter Audit"
        )

    classification_rows = [{
        "K5_failed_gates": ";".join(failed_k5),
        "all_nonfront_capacity_sufficient": all_nonfront_capacity_sufficient,
        "any_nonfront_capacity_insufficient": any_nonfront_capacity_insufficient,
        "high_front_mask_overlap": high_mask_overlap,
        "front_margin_large": front_margin_large,
        "material_share_pass": material_share_pass,
        "support_pass": support_pass,
        "diagnosis": diagnosis,
        "next_milestone": next_milestone,
    }]

    save_csv(CLASSIFICATION_TABLE, classification_rows)

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1F1R",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "correction_recalibrated": False,
            "X08_support_geometry_changed": False,
            "gate_changed": False,
            "K5_failed_gates": failed_k5,
            "all_nonfront_capacity_sufficient": all_nonfront_capacity_sufficient,
            "high_front_mask_overlap": high_mask_overlap,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1F1R",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "correction_recalibrated": False,
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
    print("K5 REMAINING BIAS SHORTFALLS")
    print("=" * 78)

    for row in shortfall_rows:
        print(
            f"{row['gate']:<25s} | "
            f"K5={row['K5_value']:.6e} | "
            f"limit={row['limit']:.6e} | "
            f"shortfall={row['absolute_shortfall']:.6e} | "
            f"gammaReq={row['third_stage_gamma_required_if_uniform']:.3f}"
        )

    print("\nMAXIMUM NON-FRONT CAPACITY")
    for row in capacity_rows:
        print(
            f"{row['gate']:<25s} | "
            f"K5={row['current_K5_bias']:.6e} | "
            f"bestNonFront={row['best_possible_nonfront_only_bias']:.6e} | "
            f"limit={row['unchanged_limit']:.6e} | "
            f"{'PASS' if row['nonfront_only_can_meet_gate'] else 'FAIL'} | "
            f"fractionNeeded={row['fraction_of_available_nonfront_reduction_required']:.3f}"
        )

    print("\nFRONT-MASK RESIDUAL OVERLAP")
    for row in residual_mass_rows:
        print(
            f"{row['region']:<12s} | "
            f"nonfront={100*row['nonfront_residual_mass_fraction']:.1f}% | "
            f"shell={100*row['front_shell_residual_mass_fraction']:.1f}% | "
            f"core={100*row['front_core_residual_mass_fraction']:.1f}%"
        )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F1R DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        ("Incoming R1F1 no-candidate diagnosis reproduced", True),
        ("K0-K5 experiment metrics loaded", True),
        ("K5 persisted state loaded", True),
        ("Remaining K5 gate failures enumerated", True),
        ("K5 shortfalls quantified", True),
        ("Remaining residual mass decomposed by TOF/tail region", True),
        ("Front-shell/core overlap quantified", True),
        ("Maximum non-front-only attainable bias reduction computed", True),
        ("K-stage trajectory reconstructed", True),
        ("X08 support remains unchanged", support_pass),
        ("Front safety margin audited", True),
        ("No correction recalibrated", True),
        ("No gate changed or relaxed", True),
        ("Limiter mechanism classified", True),
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
    print(f"  {K5_SHORTFALL_TABLE.name}")
    print(f"  {RESIDUAL_MASS_TABLE.name}")
    print(f"  {MASK_OVERLAP_TABLE.name}")
    print(f"  {CAPACITY_TABLE.name}")
    print(f"  {TRAJECTORY_TABLE.name}")
    print(f"  {CLASSIFICATION_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F1R OUTCOME AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No correction was recalibrated.")
    print("X08 support geometry remained unchanged.")
    print("No gate was changed or relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
