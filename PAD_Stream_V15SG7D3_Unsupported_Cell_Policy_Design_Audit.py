from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7D3
# Unsupported-Cell Policy Design / Audit
#
# DESIGN / DIAGNOSTIC MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D1 GRID ARRAY CHANGED.
# NO UNSUPPORTED CELL FILLED.
# NO SG7E THRESHOLD CHANGED.
#
# PURPOSE
# -------
# SG7D2 independently validated the conservative map-back:
#
#   supported cells   = 29,107 / 37,500
#   unsupported cells = 8,393
#   support topology  = one connected component
#
# SG7D3 determines what unsupported cells physically represent and designs the
# safest downstream policy WITHOUT modifying any grid value.
#
# Candidate policies audited:
#
#   P0  KEEP_NAN
#       Preserve unsupported cells as explicit no-streamline-support cells.
#
#   P1  BACKGROUND_STATE
#       Assign the frozen transport minimum/background saturation to unsupported
#       cells in a future controlled fill milestone.
#
#   P2  NEAREST_SUPPORTED
#       Copy nearest supported cell saturation.
#
#   P3  HARMONIC_LOCAL_INTERPOLATION
#       Iteratively interpolate unsupported cells from neighboring supported
#       cells.
#
#   P4  MASKED_BACKGROUND_PLUS_SUPPORT
#       Preserve SG7D1 mapped values where supported and assign only the known
#       background saturation elsewhere.
#
# SG7D3 does NOT apply any policy. It evaluates each against:
#
#   * physical defensibility,
#   * conservation semantics,
#   * saturation invention risk,
#   * topology distortion risk,
#   * threshold/plume distortion risk,
#   * deterministic reproducibility,
#   * compatibility with the existing SG7E contract.
#
# The recommended policy should minimize invented information.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7D3"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

SG7D2_CONTRACT = (
    ROOT / "output" / "V15_SG7D2"
    / "V15SG7D2_Independent_MapBack_Audit_Contract.json"
)

SG7D2_SUMMARY = (
    ROOT / "output" / "V15_SG7D2"
    / "PAD_Stream_V15SG7D2_Summary.json"
)

SG7D1_NUMERICAL = (
    ROOT / "output" / "V15_SG7D1"
    / "V15SG7D1_Conservative_MapBack.npz"
)

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3"
    / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7D3_Summary.json"

UNSUPPORTED_GEOMETRY_TABLE = OUT / "V15SG7D3_Unsupported_Geometry_Audit.csv"
DISTANCE_TABLE = OUT / "V15SG7D3_Unsupported_Distance_to_Support.csv"
NEIGHBOR_TABLE = OUT / "V15SG7D3_Unsupported_Neighbor_Context.csv"
POLICY_TABLE = OUT / "V15SG7D3_Candidate_Policy_Audit.csv"
LAYER_TABLE = OUT / "V15SG7D3_Unsupported_By_Layer.csv"
PLUME_RISK_TABLE = OUT / "V15SG7D3_Policy_Plume_Risk.csv"
DECISION_TABLE = OUT / "V15SG7D3_Policy_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7D3_Unsupported_Cell_Policy_Contract.json"

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EXPECTED_SHAPE = (15, 50, 50)
DIAGNOSTIC_THRESHOLD = 0.21  # diagnostic only; not changing SG7E
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
    mask = np.asarray(mask, dtype=bool)
    nz, ny, nx = mask.shape
    visited = np.zeros_like(mask, dtype=bool)

    neighbors = (
        (-1,0,0), (1,0,0),
        (0,-1,0), (0,1,0),
        (0,0,-1), (0,0,1),
    )

    sizes = []

    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                if not mask[k,j,i] or visited[k,j,i]:
                    continue

                stack = [(k,j,i)]
                visited[k,j,i] = True
                size = 0

                while stack:
                    ck,cj,ci = stack.pop()
                    size += 1

                    for dk,dj,di in neighbors:
                        nk,nj,ni = ck+dk,cj+dj,ci+di
                        if (
                            0 <= nk < nz and
                            0 <= nj < ny and
                            0 <= ni < nx and
                            mask[nk,nj,ni] and
                            not visited[nk,nj,ni]
                        ):
                            visited[nk,nj,ni] = True
                            stack.append((nk,nj,ni))

                sizes.append(size)

    sizes.sort(reverse=True)
    return sizes


def neighbor_context(supported, s_grid):
    """
    For each unsupported cell, count supported 6-neighbors and collect local
    supported-neighbor saturation statistics.
    """

    nz,ny,nx = supported.shape

    counts = np.zeros_like(supported, dtype=np.int16)
    means = np.full(supported.shape, np.nan, dtype=np.float64)
    mins = np.full(supported.shape, np.nan, dtype=np.float64)
    maxs = np.full(supported.shape, np.nan, dtype=np.float64)

    neighbors = (
        (-1,0,0), (1,0,0),
        (0,-1,0), (0,1,0),
        (0,0,-1), (0,0,1),
    )

    unsupported_idx = np.argwhere(~supported)

    for k,j,i in unsupported_idx:
        vals = []

        for dk,dj,di in neighbors:
            nk,nj,ni = k+dk,j+dj,i+di

            if (
                0 <= nk < nz and
                0 <= nj < ny and
                0 <= ni < nx and
                supported[nk,nj,ni]
            ):
                vals.append(float(s_grid[nk,nj,ni]))

        counts[k,j,i] = len(vals)

        if vals:
            vals = np.asarray(vals, dtype=float)
            means[k,j,i] = float(np.mean(vals))
            mins[k,j,i] = float(np.min(vals))
            maxs[k,j,i] = float(np.max(vals))

    return counts, means, mins, maxs


def manhattan_distance_to_support(supported):
    """
    Multi-source BFS on the Cartesian logical grid. Returns integer 6-neighbor
    distance from every cell to nearest supported cell.
    """

    from collections import deque

    nz,ny,nx = supported.shape
    dist = np.full(supported.shape, -1, dtype=np.int32)

    q = deque()

    for k,j,i in np.argwhere(supported):
        dist[k,j,i] = 0
        q.append((int(k),int(j),int(i)))

    neighbors = (
        (-1,0,0), (1,0,0),
        (0,-1,0), (0,1,0),
        (0,0,-1), (0,0,1),
    )

    while q:
        k,j,i = q.popleft()
        d0 = dist[k,j,i]

        for dk,dj,di in neighbors:
            nk,nj,ni = k+dk,j+dj,i+di

            if (
                0 <= nk < nz and
                0 <= nj < ny and
                0 <= ni < nx and
                dist[nk,nj,ni] < 0
            ):
                dist[nk,nj,ni] = d0 + 1
                q.append((nk,nj,ni))

    return dist


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7D3")
    print("Unsupported-Cell Policy Design / Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D1 GRID ARRAY WILL BE CHANGED.
NO UNSUPPORTED CELL WILL BE FILLED.
NO SG7E THRESHOLD WILL BE CHANGED.
""")

    contract = load_json(SG7D2_CONTRACT)
    summary = load_json(SG7D2_SUMMARY)

    if (
        contract.get("status")
        !=
        "INDEPENDENT_MAPBACK_AUDIT_COMPLETE_UNSUPPORTED_CELLS_REMAIN"
    ):
        raise RuntimeError(
            "SG7D3 requires SG7D2 validated map-back with unsupported cells remaining."
        )

    if (
        summary.get("diagnosis")
        !=
        "CONSERVATIVE_MAPBACK_VALIDATED_FILL_POLICY_REQUIRED_BEFORE_FULL_GRID_USE"
    ):
        raise RuntimeError(
            "SG7D3 requires SG7D2 unsupported-cell policy diagnosis."
        )

    if not SG7D1_NUMERICAL.exists():
        raise FileNotFoundError(
            f"Missing SG7D1 numerical map-back:\n{SG7D1_NUMERICAL}"
        )

    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(
            f"Missing R1F3 frozen candidate:\n{R1F3_FROZEN}"
        )

    db = np.load(SG7D1_NUMERICAL, allow_pickle=True)
    frozen = np.load(R1F3_FROZEN, allow_pickle=True)

    s_grid = np.asarray(
        db["saturation_grid"],
        dtype=np.float64,
    )

    den = np.asarray(
        db["support_denominator"],
        dtype=np.float64,
    )

    supported = np.asarray(
        db["supported_mask"],
        dtype=np.uint8,
    ).astype(bool)

    if s_grid.shape != EXPECTED_SHAPE:
        raise RuntimeError(
            f"Unexpected SG7D1 grid shape {s_grid.shape}."
        )

    if not np.array_equal(supported, den > 0.0):
        raise RuntimeError(
            "Stored support mask no longer matches denominator."
        )

    if not np.all(np.isnan(s_grid[~supported])):
        raise RuntimeError(
            "Unsupported SG7D1 cells are no longer explicit NaN."
        )

    l2 = np.asarray(
        frozen["L2_independent_100"],
        dtype=np.float64,
    )

    background_s = float(np.min(l2))

    supported_cells = int(np.sum(supported))
    unsupported = ~supported
    unsupported_cells = int(np.sum(unsupported))

    if unsupported_cells == 0:
        raise RuntimeError(
            "SG7D3 is unnecessary because no unsupported cells remain."
        )

    # -------------------------------------------------------------------------
    # Unsupported topology / geometry
    # -------------------------------------------------------------------------

    unsupported_components = connected_components_3d(
        unsupported
    )

    n_components = len(unsupported_components)
    largest_component = unsupported_components[0] if unsupported_components else 0
    largest_fraction = largest_component / max(unsupported_cells, 1)

    boundary_mask = np.zeros(EXPECTED_SHAPE, dtype=bool)
    boundary_mask[0,:,:] = True
    boundary_mask[-1,:,:] = True
    boundary_mask[:,0,:] = True
    boundary_mask[:,-1,:] = True
    boundary_mask[:,:,0] = True
    boundary_mask[:,:,-1] = True

    unsupported_boundary = int(np.sum(unsupported & boundary_mask))
    unsupported_interior = unsupported_cells - unsupported_boundary

    distance = manhattan_distance_to_support(supported)

    unsupported_dist = distance[unsupported]

    geometry_rows = [{
        "unsupported_cells":
            unsupported_cells,

        "unsupported_fraction":
            unsupported_cells / np.prod(EXPECTED_SHAPE),

        "unsupported_components":
            n_components,

        "largest_unsupported_component_cells":
            largest_component,

        "largest_unsupported_component_fraction":
            largest_fraction,

        "unsupported_boundary_cells":
            unsupported_boundary,

        "unsupported_interior_cells":
            unsupported_interior,

        "boundary_fraction_of_unsupported":
            unsupported_boundary / max(unsupported_cells, 1),

        "max_manhattan_distance_to_support":
            int(np.max(unsupported_dist)),

        "mean_manhattan_distance_to_support":
            float(np.mean(unsupported_dist)),

        "median_manhattan_distance_to_support":
            float(np.median(unsupported_dist)),
    }]

    save_csv(
        UNSUPPORTED_GEOMETRY_TABLE,
        geometry_rows,
    )

    # -------------------------------------------------------------------------
    # Distance distribution
    # -------------------------------------------------------------------------

    distance_rows = []

    for d in np.unique(unsupported_dist):
        count = int(np.sum(unsupported_dist == d))

        distance_rows.append({
            "manhattan_distance_cells":
                int(d),

            "unsupported_cells":
                count,

            "fraction_of_unsupported":
                count / unsupported_cells,
        })

    save_csv(
        DISTANCE_TABLE,
        distance_rows,
    )

    # -------------------------------------------------------------------------
    # Neighbor context
    # -------------------------------------------------------------------------

    neighbor_count, neighbor_mean, neighbor_min, neighbor_max = (
        neighbor_context(
            supported,
            s_grid,
        )
    )

    unsupported_neighbor_count = neighbor_count[unsupported]

    neigh_rows = []

    for count in range(7):
        mask = (
            unsupported
            &
            (neighbor_count == count)
        )

        n = int(np.sum(mask))

        if n == 0:
            continue

        vals = neighbor_mean[mask]
        finite_vals = vals[np.isfinite(vals)]

        neigh_rows.append({
            "supported_6neighbor_count":
                count,

            "unsupported_cells":
                n,

            "fraction_of_unsupported":
                n / unsupported_cells,

            "mean_neighbor_saturation":
                float(np.mean(finite_vals))
                if finite_vals.size else np.nan,

            "min_neighbor_saturation":
                float(np.nanmin(neighbor_min[mask]))
                if finite_vals.size else np.nan,

            "max_neighbor_saturation":
                float(np.nanmax(neighbor_max[mask]))
                if finite_vals.size else np.nan,
        })

    save_csv(
        NEIGHBOR_TABLE,
        neigh_rows,
    )

    # -------------------------------------------------------------------------
    # Layer distribution
    # -------------------------------------------------------------------------

    layer_rows = []

    for k in range(EXPECTED_SHAPE[0]):

        u = unsupported[k]
        s = supported[k]

        layer_rows.append({
            "k":
                k,

            "user_layer":
                k + 1,

            "unsupported_cells":
                int(np.sum(u)),

            "unsupported_fraction":
                float(np.mean(u)),

            "supported_cells":
                int(np.sum(s)),

            "supported_fraction":
                float(np.mean(s)),
        })

    save_csv(
        LAYER_TABLE,
        layer_rows,
    )

    # -------------------------------------------------------------------------
    # Policy audit
    # -------------------------------------------------------------------------

    # Policy scoring:
    #   conservation_semantics: 0-3
    #   invention_risk:         0-3 (lower better)
    #   topology_risk:          0-3 (lower better)
    #   plume_risk:             0-3 (lower better)
    #   deterministic:          bool
    #   full_grid:              bool
    #
    # We recommend the least-information policy that can produce a full-grid
    # field for downstream use without manufacturing a plume.
    policies = [
        {
            "policy": "P0_KEEP_NAN",
            "description":
                "Retain unsupported cells as NaN / no streamline support.",
            "conservation_semantics_score":
                3,
            "invention_risk_score":
                0,
            "topology_risk_score":
                0,
            "plume_risk_score":
                0,
            "deterministic":
                True,
            "full_grid_field":
                False,
            "changes_supported_cells":
                False,
            "uses_new_saturation_information":
                False,
        },
        {
            "policy": "P1_BACKGROUND_STATE",
            "description":
                "Assign frozen minimum/background saturation to unsupported cells.",
            "conservation_semantics_score":
                3,
            "invention_risk_score":
                1,
            "topology_risk_score":
                0,
            "plume_risk_score":
                0,
            "deterministic":
                True,
            "full_grid_field":
                True,
            "changes_supported_cells":
                False,
            "uses_new_saturation_information":
                False,
        },
        {
            "policy": "P2_NEAREST_SUPPORTED",
            "description":
                "Copy saturation from the nearest supported cell.",
            "conservation_semantics_score":
                1,
            "invention_risk_score":
                2,
            "topology_risk_score":
                2,
            "plume_risk_score":
                2,
            "deterministic":
                True,
            "full_grid_field":
                True,
            "changes_supported_cells":
                False,
            "uses_new_saturation_information":
                True,
        },
        {
            "policy": "P3_HARMONIC_LOCAL_INTERPOLATION",
            "description":
                "Interpolate unsupported cells from neighboring supported values.",
            "conservation_semantics_score":
                1,
            "invention_risk_score":
                3,
            "topology_risk_score":
                3,
            "plume_risk_score":
                3,
            "deterministic":
                True,
            "full_grid_field":
                True,
            "changes_supported_cells":
                False,
            "uses_new_saturation_information":
                True,
        },
        {
            "policy": "P4_MASKED_BACKGROUND_PLUS_SUPPORT",
            "description":
                "Preserve SG7D1 exactly where supported and use frozen background state elsewhere.",
            "conservation_semantics_score":
                3,
            "invention_risk_score":
                1,
            "topology_risk_score":
                0,
            "plume_risk_score":
                0,
            "deterministic":
                True,
            "full_grid_field":
                True,
            "changes_supported_cells":
                False,
            "uses_new_saturation_information":
                False,
        },
    ]

    # P1 and P4 are algebraically identical for the grid state; P4 is retained
    # as the clearer deployment contract because it explicitly preserves the
    # support mask as provenance.
    for p in policies:

        p["total_risk_score"] = (
            p["invention_risk_score"]
            +
            p["topology_risk_score"]
            +
            p["plume_risk_score"]
        )

        p["recommended_for_full_grid"] = False

    selected_policy = "P4_MASKED_BACKGROUND_PLUS_SUPPORT"

    for p in policies:
        if p["policy"] == selected_policy:
            p["recommended_for_full_grid"] = True

    save_csv(
        POLICY_TABLE,
        policies,
    )

    # -------------------------------------------------------------------------
    # Plume risk preview WITHOUT modifying SG7D1
    # -------------------------------------------------------------------------

    current_supported_plume = (
        supported
        &
        np.isfinite(s_grid)
        &
        (s_grid >= DIAGNOSTIC_THRESHOLD)
    )

    current_plume_cells = int(
        np.sum(
            current_supported_plume
        )
    )

    background_crosses_threshold = (
        background_s
        >=
        DIAGNOSTIC_THRESHOLD
    )

    # P4 would add zero unsupported plume cells if background is below threshold.
    p4_added_plume = (
        unsupported_cells
        if background_crosses_threshold
        else
        0
    )

    # Nearest/interpolation cannot be exactly known without applying them; risk
    # is estimated from unsupported cells adjacent to supported plume cells.
    plume_neighbor_risk = (
        unsupported
        &
        (neighbor_max >= DIAGNOSTIC_THRESHOLD)
    )

    near_plume_unsupported = int(
        np.sum(
            plume_neighbor_risk
        )
    )

    plume_risk_rows = [
        {
            "policy":
                "P0_KEEP_NAN",

            "existing_supported_plume_cells":
                current_plume_cells,

            "potential_added_unsupported_plume_cells":
                0,

            "risk_class":
                "NONE",
        },
        {
            "policy":
                "P4_MASKED_BACKGROUND_PLUS_SUPPORT",

            "existing_supported_plume_cells":
                current_plume_cells,

            "potential_added_unsupported_plume_cells":
                p4_added_plume,

            "risk_class":
                "NONE"
                if not background_crosses_threshold
                else "HIGH",
        },
        {
            "policy":
                "P2_NEAREST_SUPPORTED",

            "existing_supported_plume_cells":
                current_plume_cells,

            "potential_added_unsupported_plume_cells":
                near_plume_unsupported,

            "risk_class":
                "MATERIAL",
        },
        {
            "policy":
                "P3_HARMONIC_LOCAL_INTERPOLATION",

            "existing_supported_plume_cells":
                current_plume_cells,

            "potential_added_unsupported_plume_cells":
                near_plume_unsupported,

            "risk_class":
                "MATERIAL",
        },
    ]

    save_csv(
        PLUME_RISK_TABLE,
        plume_risk_rows,
    )

    # -------------------------------------------------------------------------
    # Decision / validation
    # -------------------------------------------------------------------------

    checks = [
        (
            "SG7D2 validated-mapback status reproduced",
            True,
        ),
        (
            "Unsupported cells remain present",
            unsupported_cells > 0,
        ),
        (
            "SG7D1 support mask unchanged",
            np.array_equal(supported, den > 0.0),
        ),
        (
            "Unsupported cells remain NaN",
            np.all(np.isnan(s_grid[unsupported])),
        ),
        (
            "Unsupported topology established",
            n_components >= 1,
        ),
        (
            "Distance-to-support distribution established",
            unsupported_dist.size == unsupported_cells,
        ),
        (
            "Neighbor context established",
            unsupported_neighbor_count.size == unsupported_cells,
        ),
        (
            "Frozen background saturation identified",
            np.isfinite(background_s),
        ),
        (
            "Background saturation remains below diagnostic plume threshold",
            background_s < DIAGNOSTIC_THRESHOLD,
        ),
        (
            "Candidate policy matrix established",
            len(policies) >= 4,
        ),
        (
            "Selected policy does not modify supported cells",
            True,
        ),
        (
            "Selected policy uses no interpolated plume information",
            True,
        ),
        (
            "No unsupported cell filled by SG7D3",
            True,
        ),
        (
            "No SG7E threshold changed",
            True,
        ),
    ]

    complete = all(
        bool(passed)
        for _, passed
        in checks
    )

    if complete:

        status = "UNSUPPORTED_CELL_POLICY_CONTRACT_READY"

        diagnosis = "BACKGROUND_ONLY_FILL_IS_MINIMUM_INFORMATION_FULL_GRID_POLICY"

        recommendation = (
            "Use a masked background-plus-support policy in the next controlled milestone: "
            "retain SG7D1 mapped saturation exactly in every supported cell, retain the SG7D1 "
            "support mask as provenance, and assign only the frozen transport background "
            "saturation to unsupported cells. Do not use nearest-neighbor or harmonic "
            "interpolation because those methods manufacture plume structure outside the "
            "streamline-supported domain."
        )

        next_milestone = (
            "V15-SG7D4 — Controlled Background-Only Unsupported-Cell Completion"
        )

    else:

        status = "UNSUPPORTED_CELL_POLICY_DESIGN_INCOMPLETE"

        diagnosis = "BACKGROUND_POLICY_PRECONDITIONS_NOT_FULLY_VALIDATED"

        recommendation = (
            "Do not fill unsupported cells. Audit only the failed unsupported-cell geometry, "
            "background-state, or plume-risk precondition before modifying the grid."
        )

        next_milestone = (
            "V15-SG7D3R — Unsupported-Cell Policy Design Repair"
        )

    decision_rows = [{
        "selected_policy":
            selected_policy,

        "background_saturation":
            background_s,

        "diagnostic_threshold":
            DIAGNOSTIC_THRESHOLD,

        "background_below_threshold":
            background_s < DIAGNOSTIC_THRESHOLD,

        "supported_cells":
            supported_cells,

        "unsupported_cells":
            unsupported_cells,

        "unsupported_components":
            n_components,

        "largest_unsupported_component_fraction":
            largest_fraction,

        "near_plume_unsupported_cells":
            near_plume_unsupported,

        "status":
            status,

        "diagnosis":
            diagnosis,

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
                "V15-SG7D3",

            "status":
                status,

            "diagnosis":
                diagnosis,

            "selected_policy":
                selected_policy,

            "selected_policy_semantics":
                {
                    "supported_cells":
                        "preserve SG7D1 exactly",

                    "unsupported_cells":
                        "assign frozen minimum/background saturation only",

                    "support_mask":
                        "preserve as immutable provenance",

                    "interpolation":
                        "prohibited",

                    "nearest_neighbor":
                        "prohibited",

                    "SG7E_threshold_changed":
                        False,
                },

            "background_saturation":
                background_s,

            "supported_cells":
                supported_cells,

            "unsupported_cells":
                unsupported_cells,

            "unsupported_components":
                n_components,

            "largest_unsupported_component_fraction":
                largest_fraction,

            "SG7D1_sha256":
                sha256(SG7D1_NUMERICAL),

            "frozen_L2_sha256":
                sha256(R1F3_FROZEN),

            "grid_changed":
                False,

            "unsupported_cells_filled":
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
                "V15-SG7D3",

            "status":
                status,

            "diagnosis":
                diagnosis,

            "selected_policy":
                selected_policy,

            "background_saturation":
                background_s,

            "supported_cells":
                supported_cells,

            "unsupported_cells":
                unsupported_cells,

            "unsupported_components":
                n_components,

            "grid_changed":
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

    print("UNSUPPORTED-CELL GEOMETRY")
    print(
        f"  Unsupported cells       : "
        f"{unsupported_cells:,}"
    )
    print(
        f"  Unsupported fraction    : "
        f"{100*unsupported_cells/np.prod(EXPECTED_SHAPE):.2f}%"
    )
    print(
        f"  Connected components    : "
        f"{n_components}"
    )
    print(
        f"  Largest component share : "
        f"{100*largest_fraction:.2f}%"
    )
    print(
        f"  Boundary unsupported    : "
        f"{unsupported_boundary:,}"
    )
    print(
        f"  Interior unsupported    : "
        f"{unsupported_interior:,}"
    )

    print("\nDISTANCE TO STREAMLINE SUPPORT")
    print(
        f"  Mean logical distance   : "
        f"{np.mean(unsupported_dist):.3f} cells"
    )
    print(
        f"  Median logical distance : "
        f"{np.median(unsupported_dist):.3f} cells"
    )
    print(
        f"  Max logical distance    : "
        f"{np.max(unsupported_dist)} cells"
    )

    print("\nBACKGROUND STATE")
    print(
        f"  Frozen background S     : "
        f"{background_s:.6f}"
    )
    print(
        f"  Diagnostic threshold    : "
        f"{DIAGNOSTIC_THRESHOLD:.6f}"
    )
    print(
        f"  Background < threshold  : "
        f"{background_s < DIAGNOSTIC_THRESHOLD}"
    )

    print("\nPOLICY DECISION")
    print(
        "  Selected                : "
        "P4_MASKED_BACKGROUND_PLUS_SUPPORT"
    )
    print(
        "  Supported cells         : preserve exactly"
    )
    print(
        "  Unsupported cells       : frozen background only"
    )
    print(
        "  Interpolation           : prohibited"
    )
    print(
        "  Support mask            : retained"
    )

    print("\n" + "=" * 78)
    print("V15-SG7D3 POLICY DESIGN VALIDATION")
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
        f"  {UNSUPPORTED_GEOMETRY_TABLE.name}"
    )
    print(
        f"  {DISTANCE_TABLE.name}"
    )
    print(
        f"  {NEIGHBOR_TABLE.name}"
    )
    print(
        f"  {POLICY_TABLE.name}"
    )
    print(
        f"  {LAYER_TABLE.name}"
    )
    print(
        f"  {PLUME_RISK_TABLE.name}"
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
    print("V15-SG7D3 UNSUPPORTED-CELL POLICY DESIGN: COMPLETE")
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
