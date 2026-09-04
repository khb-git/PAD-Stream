from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7D2
# Independent Map-Back Conservation / Support Audit
#
# DIAGNOSTIC-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D1 GRID ARRAY CHANGED.
# NO UNSUPPORTED-CELL FILLING.
# NO SG7E THRESHOLD CHANGED.
#
# PURPOSE
# -------
# SG7D1 completed a conservative segment-weighted map-back:
#
#   frozen L2 streamline transport
#       ->
#   15 x 50 x 50 SGSim saturation grid
#
# with:
#
#   supported cells        = 29,107 / 37,500
#   support fraction       = 77.62%
#   weighted-length closure ~ 1e-14
#   weighted-S*length closure ~ 1e-14
#
# SG7D2 independently audits:
#
#   1. SG7D1 artifact identity and hashes,
#   2. numerator / denominator / saturation closure,
#   3. supported-mask consistency,
#   4. cellwise finite/bounds consistency,
#   5. independent recomputation of global conservation,
#   6. support distribution by layer,
#   7. support connectivity/topology,
#   8. plume-support morphology,
#   9. unsupported-cell distribution,
#  10. readiness for an unsupported-cell policy milestone.
#
# SG7D2 does not fill or modify unsupported cells.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7D2"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

SG7D1_DIR = ROOT / "output" / "V15_SG7D1"

SG7D1_CONTRACT = (
    SG7D1_DIR / "V15SG7D1_Conservative_MapBack_Contract.json"
)

SG7D1_SUMMARY = (
    SG7D1_DIR / "PAD_Stream_V15SG7D1_Summary.json"
)

SG7D1_NUMERICAL = (
    SG7D1_DIR / "V15SG7D1_Conservative_MapBack.npz"
)

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3"
    / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7D2_Summary.json"

HASH_TABLE = OUT / "V15SG7D2_Artifact_Identity_Audit.csv"
CLOSURE_TABLE = OUT / "V15SG7D2_Independent_Closure_Audit.csv"
MASK_TABLE = OUT / "V15SG7D2_Support_Mask_Consistency.csv"
LAYER_TABLE = OUT / "V15SG7D2_Support_By_Layer.csv"
TOPOLOGY_TABLE = OUT / "V15SG7D2_Support_Topology.csv"
PLUME_TABLE = OUT / "V15SG7D2_Plume_Support_Morphology.csv"
UNSUPPORTED_TABLE = OUT / "V15SG7D2_Unsupported_Cell_Distribution.csv"
BOUNDS_TABLE = OUT / "V15SG7D2_Grid_Bounds_Audit.csv"
DECISION_TABLE = OUT / "V15SG7D2_Readiness_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7D2_Independent_MapBack_Audit_Contract.json"

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EXPECTED_SHAPE = (15, 50, 50)
SAT_THRESHOLD_DIAGNOSTIC = 0.21  # diagnostic only; SG7E threshold is unchanged

SUPPORT_CLOSURE_LIMIT = 1e-8
SAT_MEASURE_CLOSURE_LIMIT = 1e-8

EPS = 1e-15


# =============================================================================
# Helpers
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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


def sha256(path: Path, chunk_size=1024 * 1024):
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def connected_components_3d(mask):
    """
    6-neighbor connected-component count and sizes.
    Pure NumPy/Python implementation to avoid extra dependencies.
    """

    mask = np.asarray(mask, dtype=bool)

    visited = np.zeros(mask.shape, dtype=bool)

    nz, ny, nx = mask.shape

    component_sizes = []

    neighbors = (
        (-1, 0, 0),
        (1, 0, 0),
        (0, -1, 0),
        (0, 1, 0),
        (0, 0, -1),
        (0, 0, 1),
    )

    for k in range(nz):
        for j in range(ny):
            for i in range(nx):

                if not mask[k, j, i]:
                    continue

                if visited[k, j, i]:
                    continue

                stack = [(k, j, i)]
                visited[k, j, i] = True
                size = 0

                while stack:

                    ck, cj, ci = stack.pop()
                    size += 1

                    for dk, dj, di in neighbors:

                        nk = ck + dk
                        nj = cj + dj
                        ni = ci + di

                        if (
                            0 <= nk < nz
                            and
                            0 <= nj < ny
                            and
                            0 <= ni < nx
                            and
                            mask[nk, nj, ni]
                            and
                            not visited[nk, nj, ni]
                        ):

                            visited[nk, nj, ni] = True
                            stack.append((nk, nj, ni))

                component_sizes.append(size)

    component_sizes.sort(reverse=True)

    return component_sizes


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7D2")
    print("Independent Map-Back Conservation / Support Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D1 GRID ARRAY WILL BE CHANGED.
NO UNSUPPORTED CELL WILL BE FILLED.
NO SG7E THRESHOLD WILL BE CHANGED.
""")

    contract = load_json(SG7D1_CONTRACT)
    summary = load_json(SG7D1_SUMMARY)

    if (
        contract.get("status")
        !=
        "CONSERVATIVE_FROZEN_L2_MAPBACK_COMPLETE"
    ):
        raise RuntimeError(
            "SG7D2 requires successful SG7D1 conservative map-back."
        )

    if (
        summary.get("diagnosis")
        !=
        "SEGMENT_WEIGHTED_MAPBACK_CLOSES_AND_PRESERVES_BOUNDS"
    ):
        raise RuntimeError(
            "SG7D2 requires the SG7D1 closure/bounds diagnosis."
        )

    if not SG7D1_NUMERICAL.exists():
        raise FileNotFoundError(
            f"Missing SG7D1 numerical map-back:\n{SG7D1_NUMERICAL}"
        )

    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(
            f"Missing frozen L2 candidate:\n{R1F3_FROZEN}"
        )

    sg7d1_sha = sha256(SG7D1_NUMERICAL)
    frozen_sha = sha256(R1F3_FROZEN)

    expected_frozen_sha = contract["frozen_candidate"]["sha256"]

    if frozen_sha != expected_frozen_sha:
        raise RuntimeError(
            "Frozen L2 SHA-256 does not match SG7D1 contract."
        )

    db = np.load(
        SG7D1_NUMERICAL,
        allow_pickle=True,
    )

    required = [
        "saturation_grid",
        "support_denominator",
        "support_numerator",
        "supported_mask",
        "segment_piece_count",
        "streamline_visit_count",
        "grid_shape",
        "cell_size_m",
        "domain_size_m",
        "total_input_weighted_length",
        "total_deposited_weighted_length",
        "total_input_weighted_sat_length",
        "total_deposited_weighted_sat_length",
    ]

    missing = [
        key
        for key in required
        if key not in db.files
    ]

    if missing:
        raise RuntimeError(
            "SG7D1 numerical package is incomplete: "
            + ", ".join(missing)
        )

    s_grid = np.asarray(
        db["saturation_grid"],
        dtype=np.float64,
    )

    den = np.asarray(
        db["support_denominator"],
        dtype=np.float64,
    )

    num = np.asarray(
        db["support_numerator"],
        dtype=np.float64,
    )

    supported_stored = np.asarray(
        db["supported_mask"],
        dtype=np.uint8,
    ).astype(bool)

    pieces = np.asarray(
        db["segment_piece_count"],
        dtype=np.int64,
    )

    visits = np.asarray(
        db["streamline_visit_count"],
        dtype=np.int64,
    )

    grid_shape = tuple(
        int(v)
        for v in np.asarray(db["grid_shape"]).tolist()
    )

    if grid_shape != EXPECTED_SHAPE:
        raise RuntimeError(
            f"Unexpected SG7D1 grid shape {grid_shape}; expected {EXPECTED_SHAPE}."
        )

    if not (
        s_grid.shape
        ==
        den.shape
        ==
        num.shape
        ==
        supported_stored.shape
        ==
        pieces.shape
        ==
        visits.shape
        ==
        EXPECTED_SHAPE
    ):
        raise RuntimeError(
            "SG7D1 arrays do not share the expected 15x50x50 shape."
        )

    # -------------------------------------------------------------------------
    # Independent numerator/denominator closure
    # -------------------------------------------------------------------------

    supported_rebuilt = den > 0.0

    mask_exact = bool(
        np.array_equal(
            supported_rebuilt,
            supported_stored,
        )
    )

    reconstructed_s = np.full(
        EXPECTED_SHAPE,
        np.nan,
        dtype=np.float64,
    )

    reconstructed_s[supported_rebuilt] = (
        num[supported_rebuilt]
        /
        den[supported_rebuilt]
    )

    supported_delta = (
        reconstructed_s[supported_rebuilt]
        -
        s_grid[supported_rebuilt]
    )

    state_l1 = float(
        np.mean(
            np.abs(
                supported_delta
            )
        )
    ) if np.any(supported_rebuilt) else np.nan

    state_linf = float(
        np.max(
            np.abs(
                supported_delta
            )
        )
    ) if np.any(supported_rebuilt) else np.nan

    unsupported_nan_exact = bool(
        np.all(
            np.isnan(
                s_grid[
                    ~supported_rebuilt
                ]
            )
        )
    )

    # -------------------------------------------------------------------------
    # Global conservation from persisted source totals
    # -------------------------------------------------------------------------

    input_support = float(
        np.asarray(
            db["total_input_weighted_length"]
        )
    )

    deposited_support = float(
        np.asarray(
            db["total_deposited_weighted_length"]
        )
    )

    input_sat_measure = float(
        np.asarray(
            db["total_input_weighted_sat_length"]
        )
    )

    deposited_sat_measure = float(
        np.asarray(
            db["total_deposited_weighted_sat_length"]
        )
    )

    denominator_sum = float(
        np.sum(
            den
        )
    )

    numerator_sum = float(
        np.sum(
            num
        )
    )

    support_rel_source = abs(
        deposited_support
        -
        input_support
    ) / max(abs(input_support), EPS)

    support_rel_grid = abs(
        denominator_sum
        -
        input_support
    ) / max(abs(input_support), EPS)

    sat_rel_source = abs(
        deposited_sat_measure
        -
        input_sat_measure
    ) / max(abs(input_sat_measure), EPS)

    sat_rel_grid = abs(
        numerator_sum
        -
        input_sat_measure
    ) / max(abs(input_sat_measure), EPS)

    closure_rows = [{
        "input_weighted_length":
            input_support,

        "persisted_deposited_weighted_length":
            deposited_support,

        "independent_denominator_sum":
            denominator_sum,

        "persisted_support_rel_error":
            support_rel_source,

        "independent_grid_support_rel_error":
            support_rel_grid,

        "input_weighted_sat_length":
            input_sat_measure,

        "persisted_deposited_weighted_sat_length":
            deposited_sat_measure,

        "independent_numerator_sum":
            numerator_sum,

        "persisted_sat_measure_rel_error":
            sat_rel_source,

        "independent_grid_sat_measure_rel_error":
            sat_rel_grid,
    }]

    save_csv(
        CLOSURE_TABLE,
        closure_rows,
    )

    # -------------------------------------------------------------------------
    # Support mask consistency
    # -------------------------------------------------------------------------

    supported_cells = int(
        np.sum(
            supported_rebuilt
        )
    )

    unsupported_cells = int(
        np.size(
            supported_rebuilt
        )
        -
        supported_cells
    )

    support_fraction = float(
        np.mean(
            supported_rebuilt
        )
    )

    mask_rows = [{
        "stored_supported_cells":
            int(
                np.sum(
                    supported_stored
                )
            ),

        "rebuilt_supported_cells":
            supported_cells,

        "unsupported_cells":
            unsupported_cells,

        "support_fraction":
            support_fraction,

        "mask_exact_match":
            mask_exact,

        "unsupported_cells_all_nan":
            unsupported_nan_exact,

        "state_reconstruction_L1":
            state_l1,

        "state_reconstruction_Linf":
            state_linf,
    }]

    save_csv(
        MASK_TABLE,
        mask_rows,
    )

    # -------------------------------------------------------------------------
    # Bounds
    # -------------------------------------------------------------------------

    frozen = np.load(
        R1F3_FROZEN,
        allow_pickle=True,
    )

    l2 = np.asarray(
        frozen["L2_independent_100"],
        dtype=np.float64,
    )

    l2_min = float(
        np.min(
            l2
        )
    )

    l2_max = float(
        np.max(
            l2
        )
    )

    mapped_min = float(
        np.nanmin(
            s_grid
        )
    )

    mapped_max = float(
        np.nanmax(
            s_grid
        )
    )

    bounds_rows = [{
        "frozen_L2_min":
            l2_min,

        "frozen_L2_max":
            l2_max,

        "mapped_grid_min":
            mapped_min,

        "mapped_grid_max":
            mapped_max,

        "lower_bound_pass":
            mapped_min >= l2_min - 1e-7,

        "upper_bound_pass":
            mapped_max <= l2_max + 1e-7,
    }]

    save_csv(
        BOUNDS_TABLE,
        bounds_rows,
    )

    # -------------------------------------------------------------------------
    # Support by layer
    # -------------------------------------------------------------------------

    layer_rows = []

    for k in range(EXPECTED_SHAPE[0]):

        smask = supported_rebuilt[k]
        n_support = int(np.sum(smask))
        n_total = smask.size

        den_k = den[k]
        visits_k = visits[k]

        layer_rows.append({
            "k":
                k,

            "user_layer":
                k + 1,

            "supported_cells":
                n_support,

            "total_cells":
                n_total,

            "support_fraction":
                n_support / n_total,

            "denominator_sum":
                float(
                    np.sum(
                        den_k
                    )
                ),

            "mean_denominator_supported":
                float(
                    np.mean(
                        den_k[smask]
                    )
                )
                if n_support
                else np.nan,

            "mean_streamline_visits_supported":
                float(
                    np.mean(
                        visits_k[smask]
                    )
                )
                if n_support
                else np.nan,

            "mapped_saturation_mean_supported":
                float(
                    np.mean(
                        s_grid[k][smask]
                    )
                )
                if n_support
                else np.nan,

            "mapped_saturation_min_supported":
                float(
                    np.min(
                        s_grid[k][smask]
                    )
                )
                if n_support
                else np.nan,

            "mapped_saturation_max_supported":
                float(
                    np.max(
                        s_grid[k][smask]
                    )
                )
                if n_support
                else np.nan,
        })

    save_csv(
        LAYER_TABLE,
        layer_rows,
    )

    # -------------------------------------------------------------------------
    # Support topology
    # -------------------------------------------------------------------------

    component_sizes = connected_components_3d(
        supported_rebuilt
    )

    support_component_count = len(
        component_sizes
    )

    largest_support_component = (
        component_sizes[0]
        if component_sizes
        else 0
    )

    largest_support_fraction = (
        largest_support_component
        /
        max(
            supported_cells,
            1,
        )
    )

    topology_rows = [{
        "support_component_count":
            support_component_count,

        "largest_component_cells":
            largest_support_component,

        "largest_component_fraction_of_supported":
            largest_support_fraction,

        "second_component_cells":
            component_sizes[1]
            if len(component_sizes) > 1
            else 0,

        "third_component_cells":
            component_sizes[2]
            if len(component_sizes) > 2
            else 0,
    }]

    save_csv(
        TOPOLOGY_TABLE,
        topology_rows,
    )

    # -------------------------------------------------------------------------
    # Diagnostic plume support morphology
    # -------------------------------------------------------------------------

    plume_mask = (
        supported_rebuilt
        &
        np.isfinite(
            s_grid
        )
        &
        (
            s_grid
            >=
            SAT_THRESHOLD_DIAGNOSTIC
        )
    )

    plume_cells = int(
        np.sum(
            plume_mask
        )
    )

    plume_component_sizes = connected_components_3d(
        plume_mask
    )

    plume_component_count = len(
        plume_component_sizes
    )

    largest_plume_component = (
        plume_component_sizes[0]
        if plume_component_sizes
        else 0
    )

    plume_rows = [{
        "diagnostic_threshold":
            SAT_THRESHOLD_DIAGNOSTIC,

        "threshold_semantics":
            "DIAGNOSTIC_ONLY_NO_SG7E_CHANGE",

        "plume_cells_supported_only":
            plume_cells,

        "plume_fraction_of_supported":
            plume_cells
            /
            max(
                supported_cells,
                1,
            ),

        "plume_component_count":
            plume_component_count,

        "largest_plume_component_cells":
            largest_plume_component,

        "largest_plume_component_fraction":
            largest_plume_component
            /
            max(
                plume_cells,
                1,
            ),
    }]

    save_csv(
        PLUME_TABLE,
        plume_rows,
    )

    # -------------------------------------------------------------------------
    # Unsupported-cell distribution
    # -------------------------------------------------------------------------

    unsupported_rows = []

    for k in range(EXPECTED_SHAPE[0]):

        unsupported_layer = (
            ~supported_rebuilt[k]
        )

        unsupported_rows.append({
            "k":
                k,

            "user_layer":
                k + 1,

            "unsupported_cells":
                int(
                    np.sum(
                        unsupported_layer
                    )
                ),

            "unsupported_fraction":
                float(
                    np.mean(
                        unsupported_layer
                    )
                ),

            "supported_cells":
                int(
                    np.sum(
                        supported_rebuilt[k]
                    )
                ),
        })

    save_csv(
        UNSUPPORTED_TABLE,
        unsupported_rows,
    )

    # -------------------------------------------------------------------------
    # Artifact hashes
    # -------------------------------------------------------------------------

    hash_rows = [
        {
            "artifact":
                "SG7D1 numerical map-back",
            "path":
                str(
                    SG7D1_NUMERICAL
                ),
            "sha256":
                sg7d1_sha,
        },
        {
            "artifact":
                "R1F3 frozen L2",
            "path":
                str(
                    R1F3_FROZEN
                ),
            "sha256":
                frozen_sha,
        },
    ]

    save_csv(
        HASH_TABLE,
        hash_rows,
    )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    checks = [
        (
            "SG7D1 success status reproduced",
            True,
        ),
        (
            "Frozen L2 SHA-256 reproduced",
            frozen_sha == expected_frozen_sha,
        ),
        (
            "SG7D1 grid shape reproduced",
            grid_shape == EXPECTED_SHAPE,
        ),
        (
            "Stored support mask exactly reproduced from denominator",
            mask_exact,
        ),
        (
            "Unsupported cells remain NaN",
            unsupported_nan_exact,
        ),
        (
            "Saturation grid reconstructed from numerator/denominator",
            state_linf <= 1e-6,
        ),
        (
            "Independent denominator support closure <= 1e-8",
            support_rel_grid <= SUPPORT_CLOSURE_LIMIT,
        ),
        (
            "Independent numerator saturation-measure closure <= 1e-8",
            sat_rel_grid <= SAT_MEASURE_CLOSURE_LIMIT,
        ),
        (
            "Mapped saturation lower bound preserved",
            bounds_rows[0]["lower_bound_pass"],
        ),
        (
            "Mapped saturation upper bound preserved",
            bounds_rows[0]["upper_bound_pass"],
        ),
        (
            "Support topology established",
            support_component_count >= 1,
        ),
        (
            "Layerwise support distribution established",
            len(layer_rows) == EXPECTED_SHAPE[0],
        ),
        (
            "Unsupported-cell distribution established",
            len(unsupported_rows) == EXPECTED_SHAPE[0],
        ),
        (
            "No unsupported cell filled",
            True,
        ),
        (
            "No SG7E threshold changed",
            True,
        ),
    ]

    complete = all(
        bool(
            passed
        )
        for _, passed
        in checks
    )

    # Determine whether unsupported-cell policy is needed.
    unsupported_policy_needed = (
        unsupported_cells > 0
    )

    if complete:

        if unsupported_policy_needed:

            status = "INDEPENDENT_MAPBACK_AUDIT_COMPLETE_UNSUPPORTED_CELLS_REMAIN"

            diagnosis = "CONSERVATIVE_MAPBACK_VALIDATED_FILL_POLICY_REQUIRED_BEFORE_FULL_GRID_USE"

            recommendation = (
                "SG7D1 independently closes, the numerator/denominator relation is exact "
                "within numerical precision, bounds are preserved, and support topology is "
                "well-defined. Because unsupported cells remain, do not threshold or publish "
                "a full-grid plume yet. Design and audit an explicit unsupported-cell policy "
                "that preserves conservation and does not invent saturation."
            )

            next_milestone = (
                "V15-SG7D3 — Unsupported-Cell Policy Design / Audit"
            )

        else:

            status = "INDEPENDENT_MAPBACK_AUDIT_COMPLETE_FULL_GRID_SUPPORTED"

            diagnosis = "CONSERVATIVE_MAPBACK_VALIDATED_NO_FILL_POLICY_REQUIRED"

            recommendation = (
                "The conservative map-back independently validates and supports every grid "
                "cell. Proceed directly to SG7E deployment validation."
            )

            next_milestone = (
                "V15-SG7E — Frozen Grid Deployment Validation"
            )

    else:

        status = "INDEPENDENT_MAPBACK_AUDIT_FAILED"

        diagnosis = "ONE_OR_MORE_MAPBACK_CONSERVATION_OR_SUPPORT_CHECKS_FAILED"

        recommendation = (
            "Do not modify or fill the SG7D1 grid. Audit only the failed conservation, "
            "mask, bounds, or topology checks before any downstream processing."
        )

        next_milestone = (
            "V15-SG7D2R — Independent Map-Back Audit Failure Resolution"
        )

    decision_rows = [{
        "status":
            status,

        "diagnosis":
            diagnosis,

        "supported_cells":
            supported_cells,

        "unsupported_cells":
            unsupported_cells,

        "support_fraction":
            support_fraction,

        "support_component_count":
            support_component_count,

        "largest_support_component_fraction":
            largest_support_fraction,

        "plume_component_count_diagnostic":
            plume_component_count,

        "independent_support_closure_rel":
            support_rel_grid,

        "independent_sat_measure_closure_rel":
            sat_rel_grid,

        "unsupported_policy_needed":
            unsupported_policy_needed,

        "next_milestone":
            next_milestone,
    }]

    save_csv(
        DECISION_TABLE,
        decision_rows,
    )

    # -------------------------------------------------------------------------
    # Contract / summary
    # -------------------------------------------------------------------------

    save_json(
        CONTRACT_FILE,
        {
            "milestone":
                "V15-SG7D2",

            "status":
                status,

            "diagnosis":
                diagnosis,

            "SG7D1_numerical_sha256":
                sg7d1_sha,

            "frozen_L2_sha256":
                frozen_sha,

            "grid_shape":
                list(
                    EXPECTED_SHAPE
                ),

            "supported_cells":
                supported_cells,

            "unsupported_cells":
                unsupported_cells,

            "support_fraction":
                support_fraction,

            "independent_support_closure_rel":
                support_rel_grid,

            "independent_sat_measure_closure_rel":
                sat_rel_grid,

            "support_component_count":
                support_component_count,

            "largest_support_component_fraction":
                largest_support_fraction,

            "unsupported_cell_policy":
                "none_applied",

            "SG7E_threshold_changed":
                False,

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
                "V15-SG7D2",

            "status":
                status,

            "diagnosis":
                diagnosis,

            "supported_cells":
                supported_cells,

            "unsupported_cells":
                unsupported_cells,

            "support_fraction":
                support_fraction,

            "support_component_count":
                support_component_count,

            "largest_support_component_fraction":
                largest_support_fraction,

            "plume_component_count_diagnostic":
                plume_component_count,

            "mapback_grid_changed":
                False,

            "unsupported_cells_filled":
                False,

            "SG7E_threshold_changed":
                False,

            "recommendation":
                recommendation,

            "next_milestone":
                next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("INDEPENDENT CLOSURE")
    print(
        f"  Grid denominator rel err : "
        f"{support_rel_grid:.6e}"
    )
    print(
        f"  Grid numerator rel err   : "
        f"{sat_rel_grid:.6e}"
    )
    print(
        f"  Grid state closure Linf  : "
        f"{state_linf:.6e}"
    )

    print("\nSUPPORT")
    print(
        f"  Supported cells          : "
        f"{supported_cells:,} / {np.prod(EXPECTED_SHAPE):,}"
    )
    print(
        f"  Support fraction         : "
        f"{100*support_fraction:.2f}%"
    )
    print(
        f"  Unsupported cells        : "
        f"{unsupported_cells:,}"
    )

    print("\nSUPPORT TOPOLOGY")
    print(
        f"  Connected components     : "
        f"{support_component_count}"
    )
    print(
        f"  Largest component        : "
        f"{largest_support_component:,} cells"
    )
    print(
        f"  Largest component share  : "
        f"{100*largest_support_fraction:.2f}%"
    )

    print("\nDIAGNOSTIC PLUME MORPHOLOGY")
    print(
        f"  Threshold                : "
        f"{SAT_THRESHOLD_DIAGNOSTIC:.3f} [diagnostic only]"
    )
    print(
        f"  Plume cells              : "
        f"{plume_cells:,}"
    )
    print(
        f"  Plume components         : "
        f"{plume_component_count}"
    )
    print(
        f"  Largest plume component  : "
        f"{largest_plume_component:,}"
    )

    print("\n" + "=" * 78)
    print("V15-SG7D2 INDEPENDENT VALIDATION")
    print("=" * 78)

    for desc, passed in checks:
        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{desc}"
        )

    print("=" * 78)

    print("\nSTATUS")
    print(
        f"  {status}"
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

    print("\nOUTPUTS")
    print(
        f"  Directory:\n"
        f"    {OUT}"
    )

    print("\nTables:")
    print(
        f"  {HASH_TABLE.name}"
    )
    print(
        f"  {CLOSURE_TABLE.name}"
    )
    print(
        f"  {MASK_TABLE.name}"
    )
    print(
        f"  {LAYER_TABLE.name}"
    )
    print(
        f"  {TOPOLOGY_TABLE.name}"
    )
    print(
        f"  {PLUME_TABLE.name}"
    )
    print(
        f"  {UNSUPPORTED_TABLE.name}"
    )
    print(
        f"  {BOUNDS_TABLE.name}"
    )
    print(
        f"  {DECISION_TABLE.name}"
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
    print("V15-SG7D2 INDEPENDENT MAP-BACK AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen L2 array was changed.")
    print("No SG7D1 grid array was changed.")
    print("No unsupported cell was filled.")
    print("No SG7E threshold was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
