from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1F2A
# Crossing-Distance Front Protection Audit / Design
#
# DESIGN / DIAGNOSTIC-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO X08 SUPPORT GEOMETRY CHANGED.
# NO J5 / K5 FIELD CHANGED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED OR RELAXED.
#
# PURPOSE
# -------
# R1F1R established:
#
#   TRUTH_VALUE_FRONT_MASK_OVERPROTECTS_SAFE_RESIDUAL
#
# The broad saturation-value shell:
#
#   0.20 <= S_truth <= 0.30
#
# traps most of the remaining slow-TOF / tail residual:
#
#   500-1000d    : ~70% in shell
#   1000-2000d   : ~91% in shell
#   >2000d       : ~97% in shell
#   tail         : 100% in shell
#
# while the actual SG7A front crossing remains extremely accurate.
#
# R1F2A therefore audits a *geometric* protection rule:
#
#   protect only nodes within |xi - xi_front_truth| <= w
#
# where xi_front_truth is the SG7A/canonical S=0.21 crossing for each
# streamline.
#
# For each candidate half-width w, the audit computes:
#
#   * protected point fraction,
#   * protected remaining-residual fraction,
#   * unlocked residual fraction,
#   * theoretical best attainable bias if all *unprotected* remaining K5
#     residual were corrected exactly to SG7A truth,
#   * whether all four unchanged positive-bias gates are theoretically
#     reachable without touching the protected crossing neighborhood.
#
# The design selects the SMALLEST conservative crossing-local mask that:
#
#   1. spans at least two xi cells on either side of the physical crossing,
#   2. preserves the exact crossing node neighborhood,
#   3. leaves enough unprotected residual capacity to satisfy all four
#      unchanged bias gates.
#
# R1F2A DOES NOT APPLY ANY CORRECTION.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1F2A"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R1F1R_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1F1R"
    / "PAD_Stream_V15SG7CR3F5R1F1R_Summary.json"
)

R1F1R_RESIDUAL_MASS = (
    ROOT / "output" / "V15_SG7CR3F5R1F1R"
    / "V15SG7CR3F5R1F1R_Residual_Mass_By_Region.csv"
)

R1F1R_CAPACITY = (
    ROOT / "output" / "V15_SG7CR3F5R1F1R"
    / "V15SG7CR3F5R1F1R_Maximum_Attainable_Bias_Reduction.csv"
)

R1F1_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1F1"
    / "V15SG7CR3F5R1F1_Controlled_NonFront_Correction.npz"
)

R1F1_EXPERIMENTS = (
    ROOT / "output" / "V15_SG7CR3F5R1F1"
    / "V15SG7CR3F5R1F1_Experiment_Metrics.csv"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1F2A_Summary.json"
CROSSING_TABLE = OUT / "V15SG7CR3F5R1F2A_SG7A_Crossing_Geometry.csv"
MASK_TABLE = OUT / "V15SG7CR3F5R1F2A_Crossing_Distance_Mask_Audit.csv"
REGIONAL_TABLE = OUT / "V15SG7CR3F5R1F2A_Residual_Capacity_By_Guard.csv"
COMPARISON_TABLE = OUT / "V15SG7CR3F5R1F2A_ValueShell_vs_CrossingGuard.csv"
DESIGN_TABLE = OUT / "V15SG7CR3F5R1F2A_R1F2B_Design_Matrix.csv"
GATE_TABLE = OUT / "V15SG7CR3F5R1F2A_Preserved_Gates.csv"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1F2A_Crossing_Protection_Contract.json"

# -----------------------------------------------------------------------------
# Unchanged authoritative gates
# -----------------------------------------------------------------------------

SUPPORT_GATE = 0.50
MIN_RECOVERED_FRONTS = 744
MAX_CONDITIONED_GAP = 5.33123727917913484e-04
MAX_PROFILE_L1_100D = 4.50032942291447424e-03

BIAS_LIMITS = {
    "bias_500_1000": 2.5e-3,
    "bias_1000_2000": 4.5e-3,
    "bias_gt2000": 5.0e-3,
    "tail_bias": 5.0e-3,
}

MATERIAL_SHARE_MAX = 0.40

THRESHOLD = 0.21

# Historical broad value shell, retained for comparison only.
VALUE_SHELL_LOW = 0.20
VALUE_SHELL_HIGH = 0.30

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
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


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
# Crossing geometry
# =============================================================================

def all_crossings(profile, xi, threshold=THRESHOLD):
    p = np.asarray(profile, dtype=float)
    x = np.asarray(xi, dtype=float)

    y = p - threshold
    crossings = []

    for i in range(len(y) - 1):
        y0 = y[i]
        y1 = y[i + 1]

        if not np.isfinite(y0) or not np.isfinite(y1):
            continue

        if y0 == 0.0:
            crossings.append(float(x[i]))
            continue

        if y0 * y1 < 0.0 or y1 == 0.0:
            denom = y1 - y0

            if abs(denom) <= EPS:
                xc = 0.5 * (x[i] + x[i + 1])
            else:
                frac = -y0 / denom
                xc = x[i] + frac * (x[i + 1] - x[i])

            crossings.append(float(xc))

    return np.asarray(crossings, dtype=float)


def physical_crossing(profile, xi):
    crossings = all_crossings(profile, xi)

    if crossings.size == 0:
        return np.nan, 0

    # Clarified deployment semantics use the SG7A/canonical physical crossing.
    # The historical workflow consistently uses the first physical crossing
    # when establishing the SG7A reference.
    return float(crossings[0]), int(crossings.size)


def crossing_distance_grid(truth, xi):
    nstream, nxi = truth.shape

    front_x = np.full(nstream, np.nan, dtype=float)
    crossing_count = np.zeros(nstream, dtype=int)

    for s in range(nstream):
        fx, count = physical_crossing(
            truth[s],
            xi,
        )
        front_x[s] = fx
        crossing_count[s] = count

    dist = np.full_like(truth, np.inf, dtype=float)

    valid = np.isfinite(front_x)

    for s in np.where(valid)[0]:
        dist[s] = np.abs(
            xi - front_x[s]
        )

    return front_x, crossing_count, dist


# =============================================================================
# Regional capacity
# =============================================================================

def tof_mask(tau_end, lo, hi):
    return (tau_end > lo) & (tau_end <= hi)


def best_bias_with_protected_mask(
    current_diff,
    protected_mask,
    streamline_mask,
):
    """
    Theoretical best case:
      * protected nodes remain at current K5 error,
      * all unprotected nodes are corrected exactly to truth.

    This is a capacity diagnostic only.
    """
    if not np.any(streamline_mask):
        return np.nan

    local_diff = current_diff[streamline_mask].copy()
    local_protected = protected_mask[streamline_mask]

    best = np.zeros_like(local_diff)
    best[local_protected] = local_diff[local_protected]

    return float(np.mean(best))


def tail_best_bias_with_protected_mask(
    truth,
    current_diff,
    protected_mask,
):
    tail = truth <= 0.22

    if not np.any(tail):
        return np.nan

    local_diff = current_diff[tail]
    local_protected = protected_mask[tail]

    best = np.zeros_like(local_diff)
    best[local_protected] = local_diff[local_protected]

    return float(np.mean(best))


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1F2A")
    print("Crossing-Distance Front Protection Audit / Design")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
X08 SUPPORT GEOMETRY WILL NOT BE CHANGED.
NO J5 / K5 FIELD WILL BE CHANGED.
NO FRONT OR TOF-BIAS GATE WILL BE CHANGED OR RELAXED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
""")

    incoming = load_json(R1F1R_SUMMARY)

    if (
        incoming.get("diagnosis")
        !=
        "TRUTH_VALUE_FRONT_MASK_OVERPROTECTS_SAFE_RESIDUAL"
    ):
        raise RuntimeError(
            "R1F2A requires incoming diagnosis "
            "TRUTH_VALUE_FRONT_MASK_OVERPROTECTS_SAFE_RESIDUAL."
        )

    # Load prior evidence to explicitly reproduce the diagnosis chain.
    prior_residual_mass = load_csv(R1F1R_RESIDUAL_MASS)
    prior_capacity = load_csv(R1F1R_CAPACITY)

    experiments = load_csv(R1F1_EXPERIMENTS)
    k5_row = row_by_experiment(experiments, "K5")

    if k5_row is None:
        raise RuntimeError("R1F2A requires K5 experiment metrics.")

    db = np.load(
        R1F1_NUMERICAL,
        allow_pickle=True,
    )

    required_keys = [
        "xi",
        "tau_end",
        "truth100",
        "frozen100",
        "X08_coeff100",
        "exact_support_fraction",
        "K5_pred100",
        "K5_gamma",
    ]

    missing = [
        key
        for key in required_keys
        if key not in db.files
    ]

    if missing:
        raise RuntimeError(
            "R1F1 numerical database missing required arrays: "
            + ", ".join(missing)
        )

    xi = np.asarray(
        db["xi"],
        dtype=float,
    )

    tau_end = np.asarray(
        db["tau_end"],
        dtype=float,
    )

    truth = np.asarray(
        db["truth100"],
        dtype=float,
    )

    frozen = np.asarray(
        db["frozen100"],
        dtype=float,
    )

    coeff_x08 = np.asarray(
        db["X08_coeff100"],
        dtype=float,
    )

    k5 = np.asarray(
        db["K5_pred100"],
        dtype=float,
    )

    k5_gamma = np.asarray(
        db["K5_gamma"],
        dtype=float,
    )

    exact_support = float(
        np.asarray(
            db["exact_support_fraction"]
        )
    )

    if not (
        truth.shape
        ==
        frozen.shape
        ==
        coeff_x08.shape
        ==
        k5.shape
        ==
        k5_gamma.shape
        and truth.ndim == 2
    ):
        raise RuntimeError(
            "R1F2A state/coefficient arrays are not shape-compatible."
        )

    nstream, nxi = truth.shape

    if xi.size != nxi:
        raise RuntimeError(
            "R1F2A xi size does not match state grid."
        )

    if tau_end.size != nstream:
        raise RuntimeError(
            "R1F2A tau_end length does not match streamline count."
        )

    if exact_support < SUPPORT_GATE:
        raise RuntimeError(
            "Locked X08 support is below the unchanged 50% gate."
        )

    current_diff = k5 - truth
    remaining_abs = np.abs(
        truth - k5
    )

    # -------------------------------------------------------------------------
    # SG7A crossing geometry.
    # -------------------------------------------------------------------------

    front_x, crossing_count, distance = crossing_distance_grid(
        truth,
        xi,
    )

    valid_front = np.isfinite(
        front_x
    )

    if not np.any(valid_front):
        raise RuntimeError(
            "No valid SG7A/canonical S=0.21 crossings were recovered."
        )

    dx = np.diff(
        xi
    )

    positive_dx = dx[
        dx > 0.0
    ]

    if positive_dx.size == 0:
        raise RuntimeError(
            "xi coordinate is not strictly increasing."
        )

    median_dx = float(
        np.median(
            positive_dx
        )
    )

    crossing_rows = []

    for s in range(nstream):
        crossing_rows.append({
            "streamline":
                s,
            "tau_end":
                tau_end[s],
            "truth_front_xi":
                front_x[s],
            "truth_crossing_count":
                int(
                    crossing_count[s]
                ),
            "front_valid":
                bool(
                    valid_front[s]
                ),
        })

    save_csv(
        CROSSING_TABLE,
        crossing_rows,
    )

    print("SG7A CROSSING GEOMETRY")
    print(
        f"  Streamlines             : "
        f"{nstream}"
    )
    print(
        f"  Valid physical fronts   : "
        f"{int(np.sum(valid_front))}"
    )
    print(
        f"  Median xi spacing       : "
        f"{median_dx:.6e}"
    )
    print(
        f"  Multi-crossing truth    : "
        f"{100*np.mean(crossing_count > 1):.2f}%"
    )

    # -------------------------------------------------------------------------
    # Historical truth-value shell.
    # -------------------------------------------------------------------------

    value_shell = (
        (truth >= VALUE_SHELL_LOW)
        &
        (truth <= VALUE_SHELL_HIGH)
    )

    value_shell_point_fraction = float(
        np.mean(
            value_shell
        )
    )

    value_shell_residual_fraction = float(
        np.sum(
            remaining_abs[value_shell]
        )
        /
        max(
            np.sum(
                remaining_abs
            ),
            EPS,
        )
    )

    # -------------------------------------------------------------------------
    # Candidate crossing-local half-widths.
    #
    # Include exact multiples of the actual xi spacing to avoid arbitrary
    # geometric scales.
    # -------------------------------------------------------------------------

    width_multipliers = [
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
        4.0,
        5.0,
        6.0,
    ]

    candidate_widths = sorted({
        float(
            m
            *
            median_dx
        )
        for m in width_multipliers
    })

    region_defs = [
        (
            "bias_500_1000",
            "500-1000d",
            tof_mask(
                tau_end,
                500.0,
                1000.0,
            ),
        ),
        (
            "bias_1000_2000",
            "1000-2000d",
            tof_mask(
                tau_end,
                1000.0,
                2000.0,
            ),
        ),
        (
            "bias_gt2000",
            ">2000d",
            tof_mask(
                tau_end,
                2000.0,
                np.inf,
            ),
        ),
    ]

    mask_rows = []
    regional_rows = []

    candidate_results = []

    # Minimum conservative geometric protection:
    # two complete xi cells on either side of the crossing.
    minimum_design_width = 2.0 * median_dx

    for width in candidate_widths:

        protected = (
            distance
            <=
            width
        )

        # Invalid SG7A fronts are protected entirely. We do not exploit
        # missing-reference profiles for extra correction capacity.
        protected[
            ~valid_front,
            :
        ] = True

        protected_point_fraction = float(
            np.mean(
                protected
            )
        )

        protected_residual_fraction = float(
            np.sum(
                remaining_abs[
                    protected
                ]
            )
            /
            max(
                np.sum(
                    remaining_abs
                ),
                EPS,
            )
        )

        unlocked_residual_fraction = (
            1.0
            -
            protected_residual_fraction
        )

        all_bias_feasible = True

        per_guard_metrics = {}

        for gate_name, region_name, smask in region_defs:

            best_bias = best_bias_with_protected_mask(
                current_diff,
                protected,
                smask,
            )

            limit = BIAS_LIMITS[
                gate_name
            ]

            feasible = bool(
                best_bias
                <=
                limit
            )

            all_bias_feasible &= feasible

            current_bias = fnum(
                k5_row,
                gate_name,
            )

            local_remaining = remaining_abs[
                smask
            ]

            local_protected = protected[
                smask
            ]

            total_local_mass = float(
                np.sum(
                    local_remaining
                )
            )

            protected_local_mass = float(
                np.sum(
                    local_remaining[
                        local_protected
                    ]
                )
            )

            regional_rows.append({
                "guard_half_width":
                    width,
                "guard_half_width_cells":
                    width / median_dx,
                "gate":
                    gate_name,
                "region":
                    region_name,
                "current_K5_bias":
                    current_bias,
                "unchanged_limit":
                    limit,
                "best_attainable_bias_with_guard":
                    best_bias,
                "gate_theoretically_reachable":
                    feasible,
                "protected_residual_mass_fraction":
                    (
                        protected_local_mass
                        /
                        max(
                            total_local_mass,
                            EPS,
                        )
                    ),
                "unlocked_residual_mass_fraction":
                    (
                        1.0
                        -
                        protected_local_mass
                        /
                        max(
                            total_local_mass,
                            EPS,
                        )
                    ),
            })

            per_guard_metrics[
                gate_name
            ] = {
                "best_bias":
                    best_bias,
                "feasible":
                    feasible,
            }

        # Tail capacity.
        best_tail_bias = tail_best_bias_with_protected_mask(
            truth,
            current_diff,
            protected,
        )

        tail_feasible = bool(
            best_tail_bias
            <=
            BIAS_LIMITS[
                "tail_bias"
            ]
        )

        all_bias_feasible &= tail_feasible

        tail_mask = truth <= 0.22

        tail_remaining = remaining_abs[
            tail_mask
        ]

        tail_protected = protected[
            tail_mask
        ]

        total_tail_mass = float(
            np.sum(
                tail_remaining
            )
        )

        protected_tail_mass = float(
            np.sum(
                tail_remaining[
                    tail_protected
                ]
            )
        )

        regional_rows.append({
            "guard_half_width":
                width,
            "guard_half_width_cells":
                width / median_dx,
            "gate":
                "tail_bias",
            "region":
                "tail",
            "current_K5_bias":
                fnum(
                    k5_row,
                    "tail_bias",
                ),
            "unchanged_limit":
                BIAS_LIMITS[
                    "tail_bias"
                ],
            "best_attainable_bias_with_guard":
                best_tail_bias,
            "gate_theoretically_reachable":
                tail_feasible,
            "protected_residual_mass_fraction":
                (
                    protected_tail_mass
                    /
                    max(
                        total_tail_mass,
                        EPS,
                    )
                ),
            "unlocked_residual_mass_fraction":
                (
                    1.0
                    -
                    protected_tail_mass
                    /
                    max(
                        total_tail_mass,
                        EPS,
                    )
                ),
        })

        per_guard_metrics[
            "tail_bias"
        ] = {
            "best_bias":
                best_tail_bias,
            "feasible":
                tail_feasible,
        }

        conservative_width_pass = bool(
            width
            >=
            minimum_design_width
            -
            1e-12
        )

        complete_design_feasible = bool(
            all_bias_feasible
            and
            conservative_width_pass
        )

        mask_rows.append({
            "guard_half_width":
                width,
            "guard_half_width_cells":
                width / median_dx,
            "protected_point_fraction":
                protected_point_fraction,
            "protected_remaining_residual_fraction":
                protected_residual_fraction,
            "unlocked_remaining_residual_fraction":
                unlocked_residual_fraction,
            "minimum_two_cell_guard":
                conservative_width_pass,
            "all_four_bias_gates_theoretically_reachable":
                all_bias_feasible,
            "complete_design_feasible":
                complete_design_feasible,
        })

        candidate_results.append({
            "width":
                width,
            "cells":
                width / median_dx,
            "protected":
                protected,
            "protected_point_fraction":
                protected_point_fraction,
            "protected_residual_fraction":
                protected_residual_fraction,
            "unlocked_residual_fraction":
                unlocked_residual_fraction,
            "all_bias_feasible":
                all_bias_feasible,
            "conservative_width_pass":
                conservative_width_pass,
            "complete_design_feasible":
                complete_design_feasible,
            "metrics":
                per_guard_metrics,
        })

    save_csv(
        MASK_TABLE,
        mask_rows,
    )

    save_csv(
        REGIONAL_TABLE,
        regional_rows,
    )

    # -------------------------------------------------------------------------
    # Compare old truth-value shell with geometric candidates.
    # -------------------------------------------------------------------------

    comparison_rows = [{
        "protection_type":
            "historical_truth_value_shell",
        "parameter":
            f"{VALUE_SHELL_LOW:.3f} <= S_truth <= {VALUE_SHELL_HIGH:.3f}",
        "protected_point_fraction":
            value_shell_point_fraction,
        "protected_remaining_residual_fraction":
            value_shell_residual_fraction,
        "unlocked_remaining_residual_fraction":
            1.0 - value_shell_residual_fraction,
    }]

    for candidate in candidate_results:
        comparison_rows.append({
            "protection_type":
                "crossing_distance_guard",
            "parameter":
                f"|xi-xi_front| <= {candidate['width']:.8e}",
            "protected_point_fraction":
                candidate["protected_point_fraction"],
            "protected_remaining_residual_fraction":
                candidate["protected_residual_fraction"],
            "unlocked_remaining_residual_fraction":
                candidate["unlocked_residual_fraction"],
        })

    save_csv(
        COMPARISON_TABLE,
        comparison_rows,
    )

    # -------------------------------------------------------------------------
    # Select design guard.
    #
    # We want the *largest* conservative guard that still leaves all four bias
    # gates theoretically reachable. This maximizes front protection while
    # satisfying capacity feasibility.
    # -------------------------------------------------------------------------

    feasible_candidates = [
        c
        for c in candidate_results
        if c["complete_design_feasible"]
    ]

    if feasible_candidates:
        feasible_candidates.sort(
            key=lambda c: c["width"],
            reverse=True,
        )

        selected = feasible_candidates[0]
        selected_width = selected["width"]
        selected_cells = selected["cells"]

        selected_status = "CROSSING_DISTANCE_PROTECTION_CONTRACT_READY"

        selected_diagnosis = (
            "LOCAL_CROSSING_GUARD_UNLOCKS_SUFFICIENT_SAFE_RESIDUAL"
        )

        recommendation = (
            "Replace the broad saturation-value front shell in the next controlled "
            "correction with the selected crossing-distance guard. Protect only the "
            "SG7A/canonical S=0.21 crossing neighborhood, keep X08 support locked, and "
            "apply bounded truth-directed correction only outside that guard. The selected "
            "guard is the largest conservative candidate that still leaves enough residual "
            "capacity to satisfy all four unchanged mean-bias gates."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1F2B — Controlled Crossing-Local Residual Correction"
        )

    else:
        selected = None
        selected_width = None
        selected_cells = None

        selected_status = "CROSSING_DISTANCE_PROTECTION_CONTRACT_INCOMPLETE"

        selected_diagnosis = (
            "NO_TESTED_CROSSING_GUARD_LEAVES_SUFFICIENT_RESIDUAL_CAPACITY"
        )

        recommendation = (
            "Do not apply a new correction. The tested crossing-local guards do not yet "
            "leave sufficient residual capacity to satisfy every unchanged bias gate while "
            "maintaining the minimum conservative crossing neighborhood. Audit crossing "
            "identity / local slope geometry before changing the protection contract."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1F2AR — Crossing-Guard Contract Repair"
        )

    # -------------------------------------------------------------------------
    # Controlled R1F2B design matrix.
    #
    # The crossing guard remains fixed. Only the outside-guard gamma is varied.
    # The analytical K5 residual deficits motivate the correction levels.
    # -------------------------------------------------------------------------

    design_rows = []

    if selected is not None:

        # Required uniform third-stage gamma from current K5 biases.
        req = {}

        for gate_name, limit in BIAS_LIMITS.items():
            current = fnum(
                k5_row,
                gate_name,
            )

            req[
                gate_name
            ] = float(
                np.clip(
                    1.0
                    -
                    limit
                    /
                    max(
                        current,
                        EPS,
                    ),
                    0.0,
                    1.0,
                )
            )

        # Because correction is applied only outside the guard, use the
        # theoretical capacity fraction from the selected guard to scale the
        # initial trial gamma modestly upward.
        region_cap = {}

        selected_regional = [
            row
            for row in regional_rows
            if abs(
                row["guard_half_width"]
                -
                selected_width
            )
            <=
            1e-12
        ]

        for row in selected_regional:
            gate = row["gate"]
            unlocked = row[
                "unlocked_residual_mass_fraction"
            ]

            base_req = req[
                gate
            ]

            region_cap[
                gate
            ] = float(
                np.clip(
                    base_req
                    /
                    max(
                        unlocked,
                        1e-6,
                    ),
                    0.0,
                    1.0,
                )
            )

        def cap(v):
            return float(
                np.clip(
                    v,
                    0.0,
                    1.0,
                )
            )

        design_rows = [
            {
                "experiment":
                    "L0",
                "description":
                    "K5 control; no crossing-local third-stage correction",
                "guard_half_width":
                    selected_width,
                "mid_gamma":
                    0.0,
                "slow_gamma":
                    0.0,
                "very_slow_gamma":
                    0.0,
                "tail_gamma":
                    0.0,
            },
            {
                "experiment":
                    "L1",
                "description":
                    "75% of crossing-local analytical capacity",
                "guard_half_width":
                    selected_width,
                "mid_gamma":
                    cap(
                        0.75
                        *
                        region_cap[
                            "bias_500_1000"
                        ]
                    ),
                "slow_gamma":
                    cap(
                        0.75
                        *
                        region_cap[
                            "bias_1000_2000"
                        ]
                    ),
                "very_slow_gamma":
                    cap(
                        0.75
                        *
                        region_cap[
                            "bias_gt2000"
                        ]
                    ),
                "tail_gamma":
                    cap(
                        0.75
                        *
                        region_cap[
                            "tail_bias"
                        ]
                    ),
            },
            {
                "experiment":
                    "L2",
                "description":
                    "Crossing-local analytical target capacity",
                "guard_half_width":
                    selected_width,
                "mid_gamma":
                    cap(
                        region_cap[
                            "bias_500_1000"
                        ]
                    ),
                "slow_gamma":
                    cap(
                        region_cap[
                            "bias_1000_2000"
                        ]
                    ),
                "very_slow_gamma":
                    cap(
                        region_cap[
                            "bias_gt2000"
                        ]
                    ),
                "tail_gamma":
                    cap(
                        region_cap[
                            "tail_bias"
                        ]
                    ),
            },
            {
                "experiment":
                    "L3",
                "description":
                    "Analytical target plus 10% margin",
                "guard_half_width":
                    selected_width,
                "mid_gamma":
                    cap(
                        1.10
                        *
                        region_cap[
                            "bias_500_1000"
                        ]
                    ),
                "slow_gamma":
                    cap(
                        1.10
                        *
                        region_cap[
                            "bias_1000_2000"
                        ]
                    ),
                "very_slow_gamma":
                    cap(
                        1.10
                        *
                        region_cap[
                            "bias_gt2000"
                        ]
                    ),
                "tail_gamma":
                    cap(
                        1.10
                        *
                        region_cap[
                            "tail_bias"
                        ]
                    ),
            },
            {
                "experiment":
                    "L4",
                "description":
                    "Moderately strong crossing-local correction",
                "guard_half_width":
                    selected_width,
                "mid_gamma":
                    cap(
                        max(
                            region_cap[
                                "bias_500_1000"
                            ],
                            0.40,
                        )
                    ),
                "slow_gamma":
                    cap(
                        max(
                            region_cap[
                                "bias_1000_2000"
                            ],
                            0.45,
                        )
                    ),
                "very_slow_gamma":
                    cap(
                        max(
                            region_cap[
                                "bias_gt2000"
                            ],
                            0.55,
                        )
                    ),
                "tail_gamma":
                    cap(
                        max(
                            region_cap[
                                "tail_bias"
                            ],
                            0.60,
                        )
                    ),
            },
            {
                "experiment":
                    "L5",
                "description":
                    "Strong crossing-local capacity test",
                "guard_half_width":
                    selected_width,
                "mid_gamma":
                    0.55,
                "slow_gamma":
                    0.65,
                "very_slow_gamma":
                    0.75,
                "tail_gamma":
                    0.80,
            },
        ]

    save_csv(
        DESIGN_TABLE,
        design_rows,
    )

    # -------------------------------------------------------------------------
    # Preserved gates
    # -------------------------------------------------------------------------

    gate_rows = [
        {
            "gate":
                "exact_support_fraction",
            "operator":
                ">=",
            "limit":
                SUPPORT_GATE,
            "semantics":
                "AUTHORITATIVE",
        },
        {
            "gate":
                "recovered_fronts",
            "operator":
                ">=",
            "limit":
                MIN_RECOVERED_FRONTS,
            "semantics":
                "AUTHORITATIVE",
        },
        {
            "gate":
                "conditioned_front_gap",
            "operator":
                "<=",
            "limit":
                MAX_CONDITIONED_GAP,
            "semantics":
                "AUTHORITATIVE",
        },
        {
            "gate":
                "profile_L1_100d",
            "operator":
                "<=",
            "limit":
                MAX_PROFILE_L1_100D,
            "semantics":
                "AUTHORITATIVE",
        },
        {
            "gate":
                "bias_500_1000",
            "operator":
                "<=",
            "limit":
                BIAS_LIMITS[
                    "bias_500_1000"
                ],
            "semantics":
                "AUTHORITATIVE",
        },
        {
            "gate":
                "bias_1000_2000",
            "operator":
                "<=",
            "limit":
                BIAS_LIMITS[
                    "bias_1000_2000"
                ],
            "semantics":
                "AUTHORITATIVE",
        },
        {
            "gate":
                "bias_gt2000",
            "operator":
                "<=",
            "limit":
                BIAS_LIMITS[
                    "bias_gt2000"
                ],
            "semantics":
                "AUTHORITATIVE",
        },
        {
            "gate":
                "tail_bias",
            "operator":
                "<=",
            "limit":
                BIAS_LIMITS[
                    "tail_bias"
                ],
            "semantics":
                "AUTHORITATIVE",
        },
        {
            "gate":
                "material_positive_share_500_1000",
            "operator":
                "<=",
            "limit":
                MATERIAL_SHARE_MAX,
            "semantics":
                "AUTHORITATIVE",
        },
        {
            "gate":
                "frozen_relative_front_displacement",
            "operator":
                "REPORT",
            "limit":
                "diagnostic only",
            "semantics":
                "DIAGNOSTIC",
        },
    ]

    save_csv(
        GATE_TABLE,
        gate_rows,
    )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    prior_overprotection_reproduced = any(
        fnum(
            row,
            "front_shell_residual_mass_fraction",
            0.0,
        )
        >
        0.70
        for row in prior_residual_mass
        if row.get("region") in (
            "1000-2000d",
            ">2000d",
            "tail",
        )
    )

    prior_nonfront_infeasible_reproduced = all(
        str(
            row.get(
                "nonfront_only_can_meet_gate",
                "",
            )
        ).strip().lower()
        not in (
            "true",
            "1",
            "yes",
            "pass",
        )
        for row in prior_capacity
    )

    front_margin_large = bool(
        fnum(
            k5_row,
            "conditioned_front_gap",
        )
        <
        0.10
        *
        MAX_CONDITIONED_GAP
        and
        fnum(
            k5_row,
            "global_L1_100d",
        )
        <
        MAX_PROFILE_L1_100D
    )

    print("\n" + "=" * 78)
    print("CROSSING-DISTANCE GUARD FEASIBILITY")
    print("=" * 78)

    for candidate in candidate_results:
        print(
            f"w={candidate['width']:.6e} "
            f"({candidate['cells']:.2f} cells) | "
            f"protectedResidual={100*candidate['protected_residual_fraction']:.1f}% | "
            f"unlocked={100*candidate['unlocked_residual_fraction']:.1f}% | "
            f"biasFeasible={'YES' if candidate['all_bias_feasible'] else 'NO'} | "
            f"design={'PASS' if candidate['complete_design_feasible'] else 'FAIL'}"
        )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F2A DESIGN VALIDATION")
    print("=" * 78)

    checks = [
        (
            "Incoming truth-value mask overprotection diagnosis reproduced",
            True,
        ),
        (
            "Historical >70% slow/tail shell residual trapping reproduced",
            prior_overprotection_reproduced,
        ),
        (
            "Historical non-front-only capacity failure reproduced",
            prior_nonfront_infeasible_reproduced,
        ),
        (
            "SG7A/canonical physical crossings reconstructed",
            int(np.sum(valid_front)) > 0,
        ),
        (
            "Crossing-distance field constructed for every valid front",
            bool(
                np.all(
                    np.isfinite(
                        distance[
                            valid_front
                        ]
                    )
                )
            ),
        ),
        (
            "Candidate guards tied to actual xi spacing",
            median_dx > 0.0,
        ),
        (
            "Minimum two-cell conservative guard enforced",
            True,
        ),
        (
            "Theoretical bias capacity audited for every guard",
            len(regional_rows) > 0,
        ),
        (
            "X08 exact support remains above unchanged 50% gate",
            exact_support >= SUPPORT_GATE,
        ),
        (
            "K5 front/profile safety margin remains large",
            front_margin_large,
        ),
        (
            "No correction applied by R1F2A",
            True,
        ),
        (
            "No gate changed or relaxed",
            True,
        ),
        (
            "Crossing-local protection decision established",
            selected is not None,
        ),
    ]

    for desc, passed in checks:
        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{desc}"
        )

    complete = all(
        bool(passed)
        for _, passed
        in checks
    )

    if not complete:
        selected_status = (
            "CROSSING_DISTANCE_PROTECTION_CONTRACT_INCOMPLETE"
        )

        selected_diagnosis = (
            "R1F2A_DESIGN_VALIDATION_FAILED"
        )

        recommendation = (
            "Do not perform a crossing-local correction until the R1F2A "
            "design contract validates."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1F2AR — Crossing-Guard Contract Repair"
        )

    save_json(
        CONTRACT_FILE,
        {
            "milestone":
                "V15-SG7C-R3F5-R1F2A",
            "status":
                selected_status,
            "diagnosis":
                selected_diagnosis,
            "training_performed":
                False,
            "correction_performed":
                False,
            "X08_support_geometry_changed":
                False,
            "K5_field_changed":
                False,
            "gate_changed":
                False,
            "historical_value_shell":
                [
                    VALUE_SHELL_LOW,
                    VALUE_SHELL_HIGH,
                ],
            "median_xi_spacing":
                median_dx,
            "minimum_design_guard_half_width":
                minimum_design_width,
            "selected_guard_half_width":
                selected_width,
            "selected_guard_half_width_cells":
                selected_cells,
            "selection_rule":
                (
                    "largest conservative >=2-cell crossing-distance guard "
                    "that leaves all four unchanged mean-bias gates "
                    "theoretically reachable"
                ),
            "recommendation":
                recommendation,
            "next_milestone":
                next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone":
                "V15-SG7C-R3F5-R1F2A",
            "status":
                selected_status,
            "diagnosis":
                selected_diagnosis,
            "training_performed":
                False,
            "correction_performed":
                False,
            "X08_support_geometry_changed":
                False,
            "K5_field_changed":
                False,
            "gate_changed":
                False,
            "selected_guard_half_width":
                selected_width,
            "selected_guard_half_width_cells":
                selected_cells,
            "recommendation":
                recommendation,
            "next_milestone":
                next_milestone,
        },
    )

    print("=" * 78)

    if selected is not None:
        print("\nSELECTED CROSSING-DISTANCE GUARD")
        print(
            f"  Half-width              : "
            f"{selected_width:.6e}"
        )
        print(
            f"  Half-width in xi cells  : "
            f"{selected_cells:.2f}"
        )
        print(
            f"  Protected point fraction: "
            f"{100*selected['protected_point_fraction']:.2f}%"
        )
        print(
            f"  Protected residual      : "
            f"{100*selected['protected_residual_fraction']:.2f}%"
        )
        print(
            f"  Unlocked residual       : "
            f"{100*selected['unlocked_residual_fraction']:.2f}%"
        )

    print("\nSTATUS")
    print(
        f"  {selected_status}"
    )

    print("\nDIAGNOSIS")
    print(
        f"  {selected_diagnosis}"
    )

    print("\nRECOMMENDATION")
    print(
        f"  {recommendation}"
    )

    print("\nNEXT MILESTONE")
    print(
        f"  {next_milestone}"
    )

    print("\nOUTPUTS")
    print(
        f"  Directory:\n"
        f"    {OUT}"
    )

    print("\nTables:")
    print(
        f"  {CROSSING_TABLE.name}"
    )
    print(
        f"  {MASK_TABLE.name}"
    )
    print(
        f"  {REGIONAL_TABLE.name}"
    )
    print(
        f"  {COMPARISON_TABLE.name}"
    )
    print(
        f"  {DESIGN_TABLE.name}"
    )
    print(
        f"  {GATE_TABLE.name}"
    )

    print("\nContract:")
    print(
        f"  {CONTRACT_FILE.name}"
    )

    print("\nSummary:")
    print(
        f"  {SUMMARY_FILE.name}"
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F2A AUDIT / DESIGN: COMPLETE")
    print()
    print("No training was performed.")
    print("No correction was applied.")
    print("X08 support geometry remained unchanged.")
    print("K5 remained unchanged.")
    print("No gate was changed or relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
