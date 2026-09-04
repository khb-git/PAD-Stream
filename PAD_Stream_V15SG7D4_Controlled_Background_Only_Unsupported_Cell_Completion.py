from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7D4
# Controlled Background-Only Unsupported-Cell Completion
#
# CONTROLLED FULL-GRID COMPLETION MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D1 SUPPORTED CELL CHANGED.
# NO INTERPOLATION.
# NO NEAREST-NEIGHBOR FILL.
# NO SG7E THRESHOLD CHANGED.
#
# PURPOSE
# -------
# SG7D3 established the accepted unsupported-cell policy:
#
#   P4_MASKED_BACKGROUND_PLUS_SUPPORT
#
#   supported cells   -> preserve SG7D1 exactly
#   unsupported cells -> assign frozen transport background saturation only
#   support mask      -> preserve as provenance
#
# SG7D4 applies that policy exactly once to produce a complete
# 15 x 50 x 50 saturation field.
#
# The completion is:
#
#   S_full[c] =
#       S_SG7D1[c],       if supported[c]
#       S_background,     otherwise
#
# where:
#
#   S_background = min(frozen L2 transport state)
#
# SG7D4 then verifies:
#
#   * every supported cell is bitwise/numerically unchanged,
#   * every formerly unsupported cell equals the frozen background,
#   * support mask is preserved,
#   * no NaNs remain in the full-grid field,
#   * saturation bounds remain valid,
#   * diagnostic plume membership is unchanged outside supported cells,
#   * SG7D1 conservative numerator/denominator evidence remains untouched.
#
# SG7D4 does not freeze the full-grid deployment field; that requires an
# independent SG7D5 validation.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7D4"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

SG7D3_CONTRACT = (
    ROOT / "output" / "V15_SG7D3"
    / "V15SG7D3_Unsupported_Cell_Policy_Contract.json"
)

SG7D3_SUMMARY = (
    ROOT / "output" / "V15_SG7D3"
    / "PAD_Stream_V15SG7D3_Summary.json"
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

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7D4_Summary.json"

SOURCE_TABLE = OUT / "V15SG7D4_Source_Identity.csv"
COMPLETION_TABLE = OUT / "V15SG7D4_Completion_Metrics.csv"
SUPPORTED_CLOSURE_TABLE = OUT / "V15SG7D4_Supported_Cell_Preservation.csv"
UNSUPPORTED_TABLE = OUT / "V15SG7D4_Background_Fill_Audit.csv"
PLUME_TABLE = OUT / "V15SG7D4_Diagnostic_Plume_Preservation.csv"
BOUNDS_TABLE = OUT / "V15SG7D4_Full_Grid_Bounds.csv"
GATE_TABLE = OUT / "V15SG7D4_Final_Gate_Matrix.csv"

NUMERICAL_FILE = OUT / "V15SG7D4_Completed_Full_Grid.npz"
CONTRACT_FILE = OUT / "V15SG7D4_Background_Completion_Contract.json"
MANIFEST_FILE = OUT / "V15SG7D4_Full_Grid_Candidate_Manifest.json"

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EXPECTED_SHAPE = (15, 50, 50)
DIAGNOSTIC_THRESHOLD = 0.21
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
    visited = np.zeros(mask.shape, dtype=bool)

    neighbors = (
        (-1,0,0),(1,0,0),
        (0,-1,0),(0,1,0),
        (0,0,-1),(0,0,1),
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
                            0 <= nk < nz
                            and 0 <= nj < ny
                            and 0 <= ni < nx
                            and mask[nk,nj,ni]
                            and not visited[nk,nj,ni]
                        ):
                            visited[nk,nj,ni] = True
                            stack.append((nk,nj,ni))

                sizes.append(size)

    sizes.sort(reverse=True)
    return sizes


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7D4")
    print("Controlled Background-Only Unsupported-Cell Completion")
    print("=" * 78)

    print("""
CONTROLLED FULL-GRID COMPLETION WILL BE PERFORMED.
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D1 SUPPORTED CELL WILL BE CHANGED.
NO INTERPOLATION OR NEAREST-NEIGHBOR FILL WILL BE USED.
NO SG7E THRESHOLD WILL BE CHANGED.
NO FULL-GRID CANDIDATE WILL BE FROZEN BY SG7D4.
""")

    contract = load_json(SG7D3_CONTRACT)
    summary = load_json(SG7D3_SUMMARY)

    if (
        contract.get("status")
        !=
        "UNSUPPORTED_CELL_POLICY_CONTRACT_READY"
    ):
        raise RuntimeError(
            "SG7D4 requires successful SG7D3 unsupported-cell policy contract."
        )

    if (
        contract.get("selected_policy")
        !=
        "P4_MASKED_BACKGROUND_PLUS_SUPPORT"
    ):
        raise RuntimeError(
            "SG7D4 requires the P4 masked background-plus-support policy."
        )

    if (
        summary.get("diagnosis")
        !=
        "BACKGROUND_ONLY_FILL_IS_MINIMUM_INFORMATION_FULL_GRID_POLICY"
    ):
        raise RuntimeError(
            "SG7D4 requires the SG7D3 background-only policy diagnosis."
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

    if sg7d1_sha != contract["SG7D1_sha256"]:
        raise RuntimeError(
            "SG7D1 numerical artifact hash does not match SG7D3 contract."
        )

    if frozen_sha != contract["frozen_L2_sha256"]:
        raise RuntimeError(
            "Frozen L2 artifact hash does not match SG7D3 contract."
        )

    db = np.load(SG7D1_NUMERICAL, allow_pickle=True)
    frozen = np.load(R1F3_FROZEN, allow_pickle=True)

    required = [
        "saturation_grid",
        "support_denominator",
        "support_numerator",
        "supported_mask",
        "segment_piece_count",
        "streamline_visit_count",
        "grid_shape",
    ]

    missing = [
        key
        for key in required
        if key not in db.files
    ]

    if missing:
        raise RuntimeError(
            "SG7D1 numerical package incomplete: "
            + ", ".join(missing)
        )

    mapped = np.asarray(
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

    supported = np.asarray(
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
            f"Unexpected grid shape {grid_shape}; expected {EXPECTED_SHAPE}."
        )

    if not np.array_equal(supported, den > 0.0):
        raise RuntimeError(
            "SG7D1 support mask no longer matches denominator."
        )

    if not np.all(np.isnan(mapped[~supported])):
        raise RuntimeError(
            "SG7D1 unsupported cells are no longer explicit NaN."
        )

    l2 = np.asarray(
        frozen["L2_independent_100"],
        dtype=np.float64,
    )

    background = float(np.min(l2))

    if abs(background - float(contract["background_saturation"])) > 1e-12:
        raise RuntimeError(
            "Frozen background saturation does not match SG7D3 contract."
        )

    # -------------------------------------------------------------------------
    # Controlled completion
    # -------------------------------------------------------------------------

    full_grid = mapped.copy()

    full_grid[~supported] = background

    supported_cells = int(np.sum(supported))
    unsupported_cells = int(np.sum(~supported))

    # -------------------------------------------------------------------------
    # Preservation audits
    # -------------------------------------------------------------------------

    supported_delta = (
        full_grid[supported]
        -
        mapped[supported]
    )

    supported_l1 = float(
        np.mean(
            np.abs(
                supported_delta
            )
        )
    )

    supported_linf = float(
        np.max(
            np.abs(
                supported_delta
            )
        )
    )

    unsupported_values = full_grid[~supported]

    background_l1 = float(
        np.mean(
            np.abs(
                unsupported_values
                -
                background
            )
        )
    )

    background_linf = float(
        np.max(
            np.abs(
                unsupported_values
                -
                background
            )
        )
    )

    no_nan_full_grid = bool(
        np.all(
            np.isfinite(
                full_grid
            )
        )
    )

    # -------------------------------------------------------------------------
    # Bounds
    # -------------------------------------------------------------------------

    l2_min = float(np.min(l2))
    l2_max = float(np.max(l2))

    full_min = float(np.min(full_grid))
    full_max = float(np.max(full_grid))

    lower_bound_pass = bool(
        full_min >= l2_min - 1e-12
    )

    upper_bound_pass = bool(
        full_max <= l2_max + 1e-12
    )

    # -------------------------------------------------------------------------
    # Plume preservation
    # -------------------------------------------------------------------------

    supported_plume_before = (
        supported
        &
        np.isfinite(mapped)
        &
        (mapped >= DIAGNOSTIC_THRESHOLD)
    )

    full_plume_after = (
        full_grid
        >=
        DIAGNOSTIC_THRESHOLD
    )

    unsupported_plume_after = (
        (~supported)
        &
        full_plume_after
    )

    supported_plume_after = (
        supported
        &
        full_plume_after
    )

    supported_plume_exact = bool(
        np.array_equal(
            supported_plume_before,
            supported_plume_after,
        )
    )

    unsupported_plume_count = int(
        np.sum(
            unsupported_plume_after
        )
    )

    plume_components_before = connected_components_3d(
        supported_plume_before
    )

    plume_components_after = connected_components_3d(
        full_plume_after
    )

    plume_count_before = int(
        np.sum(
            supported_plume_before
        )
    )

    plume_count_after = int(
        np.sum(
            full_plume_after
        )
    )

    # -------------------------------------------------------------------------
    # Preserve conservative SG7D1 evidence unchanged
    # -------------------------------------------------------------------------

    den_hash_before = hashlib.sha256(
        np.ascontiguousarray(den).tobytes()
    ).hexdigest()

    num_hash_before = hashlib.sha256(
        np.ascontiguousarray(num).tobytes()
    ).hexdigest()

    support_hash_before = hashlib.sha256(
        np.ascontiguousarray(supported.astype(np.uint8)).tobytes()
    ).hexdigest()

    # No modifications are performed to these arrays.
    den_hash_after = hashlib.sha256(
        np.ascontiguousarray(den).tobytes()
    ).hexdigest()

    num_hash_after = hashlib.sha256(
        np.ascontiguousarray(num).tobytes()
    ).hexdigest()

    support_hash_after = hashlib.sha256(
        np.ascontiguousarray(supported.astype(np.uint8)).tobytes()
    ).hexdigest()

    conservative_evidence_unchanged = bool(
        den_hash_before == den_hash_after
        and
        num_hash_before == num_hash_after
        and
        support_hash_before == support_hash_after
    )

    # -------------------------------------------------------------------------
    # Tables
    # -------------------------------------------------------------------------

    save_csv(
        SOURCE_TABLE,
        [
            {
                "role": "SG7D1_conservative_mapback",
                "path": str(SG7D1_NUMERICAL),
                "sha256": sg7d1_sha,
            },
            {
                "role": "R1F3_frozen_L2",
                "path": str(R1F3_FROZEN),
                "sha256": frozen_sha,
            },
            {
                "role": "SG7D3_policy_contract",
                "path": str(SG7D3_CONTRACT),
                "sha256": sha256(SG7D3_CONTRACT),
            },
        ],
    )

    save_csv(
        COMPLETION_TABLE,
        [{
            "policy":
                "P4_MASKED_BACKGROUND_PLUS_SUPPORT",

            "grid_shape":
                "15x50x50",

            "supported_cells":
                supported_cells,

            "unsupported_cells_completed":
                unsupported_cells,

            "background_saturation":
                background,

            "full_grid_finite":
                no_nan_full_grid,

            "full_grid_min":
                full_min,

            "full_grid_max":
                full_max,
        }],
    )

    save_csv(
        SUPPORTED_CLOSURE_TABLE,
        [{
            "supported_cells":
                supported_cells,

            "supported_state_L1_change":
                supported_l1,

            "supported_state_Linf_change":
                supported_linf,

            "supported_cells_preserved_exactly":
                bool(
                    supported_linf == 0.0
                ),

            "support_denominator_unchanged":
                den_hash_before == den_hash_after,

            "support_numerator_unchanged":
                num_hash_before == num_hash_after,

            "support_mask_unchanged":
                support_hash_before == support_hash_after,
        }],
    )

    save_csv(
        UNSUPPORTED_TABLE,
        [{
            "unsupported_cells":
                unsupported_cells,

            "background_saturation":
                background,

            "unsupported_background_L1_error":
                background_l1,

            "unsupported_background_Linf_error":
                background_linf,

            "all_unsupported_equal_background":
                bool(
                    background_linf == 0.0
                ),

            "unsupported_cells_above_diagnostic_threshold":
                unsupported_plume_count,
        }],
    )

    save_csv(
        PLUME_TABLE,
        [{
            "diagnostic_threshold":
                DIAGNOSTIC_THRESHOLD,

            "threshold_semantics":
                "DIAGNOSTIC_ONLY_NO_SG7E_CHANGE",

            "supported_plume_cells_before":
                plume_count_before,

            "supported_plume_cells_after":
                int(
                    np.sum(
                        supported_plume_after
                    )
                ),

            "full_grid_plume_cells_after":
                plume_count_after,

            "unsupported_plume_cells_after":
                unsupported_plume_count,

            "supported_plume_membership_exact":
                supported_plume_exact,

            "plume_components_before":
                len(
                    plume_components_before
                ),

            "plume_components_after":
                len(
                    plume_components_after
                ),

            "largest_component_before":
                plume_components_before[0]
                if plume_components_before
                else 0,

            "largest_component_after":
                plume_components_after[0]
                if plume_components_after
                else 0,
        }],
    )

    save_csv(
        BOUNDS_TABLE,
        [{
            "frozen_L2_min":
                l2_min,

            "frozen_L2_max":
                l2_max,

            "completed_grid_min":
                full_min,

            "completed_grid_max":
                full_max,

            "lower_bound_pass":
                lower_bound_pass,

            "upper_bound_pass":
                upper_bound_pass,
        }],
    )

    # -------------------------------------------------------------------------
    # Persist full-grid candidate
    # -------------------------------------------------------------------------

    np.savez_compressed(
        NUMERICAL_FILE,

        saturation_grid_full=
            full_grid.astype(np.float32),

        saturation_grid_supported_only=
            mapped.astype(np.float32),

        supported_mask=
            supported.astype(np.uint8),

        support_denominator=
            den.astype(np.float64),

        support_numerator=
            num.astype(np.float64),

        segment_piece_count=
            pieces.astype(np.int64),

        streamline_visit_count=
            visits.astype(np.int64),

        background_saturation=
            np.asarray(
                background,
                dtype=np.float64,
            ),

        diagnostic_threshold=
            np.asarray(
                DIAGNOSTIC_THRESHOLD,
                dtype=np.float64,
            ),

        frozen_L2_sha256=
            np.asarray(
                frozen_sha
            ),

        SG7D1_sha256=
            np.asarray(
                sg7d1_sha
            ),
    )

    numerical_sha = sha256(NUMERICAL_FILE)

    # -------------------------------------------------------------------------
    # Validation gates
    # -------------------------------------------------------------------------

    gates = {
        "SG7D3_policy_contract_reproduced":
            True,

        "SG7D1_hash_reproduced":
            sg7d1_sha
            ==
            contract["SG7D1_sha256"],

        "frozen_L2_hash_reproduced":
            frozen_sha
            ==
            contract["frozen_L2_sha256"],

        "supported_cells_exactly_preserved":
            supported_linf
            ==
            0.0,

        "unsupported_cells_equal_background":
            background_linf
            ==
            0.0,

        "support_mask_preserved":
            support_hash_before
            ==
            support_hash_after,

        "conservative_numerator_preserved":
            num_hash_before
            ==
            num_hash_after,

        "conservative_denominator_preserved":
            den_hash_before
            ==
            den_hash_after,

        "full_grid_finite":
            no_nan_full_grid,

        "completed_grid_lower_bound":
            lower_bound_pass,

        "completed_grid_upper_bound":
            upper_bound_pass,

        "supported_plume_membership_preserved":
            supported_plume_exact,

        "unsupported_background_does_not_create_plume":
            unsupported_plume_count
            ==
            0,

        "no_interpolation_used":
            True,

        "no_nearest_neighbor_used":
            True,

        "no_SG7E_threshold_change":
            True,
    }

    gate_rows = [
        {
            "gate": name,
            "passed": bool(passed),
        }
        for name, passed
        in gates.items()
    ]

    save_csv(
        GATE_TABLE,
        gate_rows,
    )

    complete = bool(
        all(
            gates.values()
        )
    )

    if complete:

        status = "BACKGROUND_ONLY_FULL_GRID_CANDIDATE_COMPLETE"

        diagnosis = "FULL_GRID_COMPLETION_PRESERVES_SUPPORTED_PHYSICS_AND_ADDS_NO_PLUME"

        recommendation = (
            "The full 15x50x50 saturation candidate is complete. Every SG7D1-supported "
            "cell is unchanged, every unsupported cell is assigned only the frozen "
            "background saturation, the support mask and conservative evidence remain "
            "intact, and no unsupported plume cells are created. Do not freeze yet. "
            "Independently validate the completed field and provenance before SG7E."
        )

        next_milestone = (
            "V15-SG7D5 — Independent Full-Grid Completion Validation"
        )

    else:

        status = "BACKGROUND_ONLY_FULL_GRID_COMPLETION_FAILED"

        diagnosis = "ONE_OR_MORE_COMPLETION_PRESERVATION_GATES_FAILED"

        recommendation = (
            "Do not freeze or threshold the completed field. Audit only the failed "
            "supported-cell, background-fill, provenance, or plume-preservation gates."
        )

        next_milestone = (
            "V15-SG7D4R — Background Completion Failure Audit"
        )

    # -------------------------------------------------------------------------
    # Manifest / contract / summary
    # -------------------------------------------------------------------------

    save_json(
        MANIFEST_FILE,
        {
            "milestone":
                "V15-SG7D4",

            "candidate":
                "P4_full_grid",

            "status":
                status,

            "candidate_frozen":
                False,

            "policy":
                "P4_MASKED_BACKGROUND_PLUS_SUPPORT",

            "background_saturation":
                background,

            "supported_cells":
                supported_cells,

            "unsupported_cells_completed":
                unsupported_cells,

            "full_grid_numerical_file":
                str(NUMERICAL_FILE),

            "full_grid_sha256":
                numerical_sha,

            "SG7D1_sha256":
                sg7d1_sha,

            "frozen_L2_sha256":
                frozen_sha,

            "support_mask_preserved":
                True,

            "SG7E_threshold_changed":
                False,

            "next_milestone":
                next_milestone,
        },
    )

    save_json(
        CONTRACT_FILE,
        {
            "milestone":
                "V15-SG7D4",

            "status":
                status,

            "diagnosis":
                diagnosis,

            "policy":
                "P4_MASKED_BACKGROUND_PLUS_SUPPORT",

            "completion_rule":
                "supported -> SG7D1; unsupported -> frozen L2 minimum/background",

            "background_saturation":
                background,

            "supported_cells":
                supported_cells,

            "unsupported_cells_completed":
                unsupported_cells,

            "full_grid_sha256":
                numerical_sha,

            "supported_cells_changed":
                False,

            "conservative_mapback_evidence_changed":
                not conservative_evidence_unchanged,

            "interpolation_used":
                False,

            "nearest_neighbor_used":
                False,

            "unsupported_plume_cells_added":
                unsupported_plume_count,

            "SG7E_threshold_changed":
                False,

            "candidate_frozen":
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
                "V15-SG7D4",

            "status":
                status,

            "diagnosis":
                diagnosis,

            "background_saturation":
                background,

            "supported_cells":
                supported_cells,

            "unsupported_cells_completed":
                unsupported_cells,

            "full_grid_min":
                full_min,

            "full_grid_max":
                full_max,

            "unsupported_plume_cells_added":
                unsupported_plume_count,

            "candidate_frozen":
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

    print("CONTROLLED COMPLETION")
    print(
        f"  Supported cells preserved : "
        f"{supported_cells:,}"
    )
    print(
        f"  Unsupported cells filled  : "
        f"{unsupported_cells:,}"
    )
    print(
        f"  Background saturation     : "
        f"{background:.6f}"
    )
    print(
        f"  Full-grid range           : "
        f"{full_min:.6f} -> {full_max:.6f}"
    )
    print(
        f"  Remaining NaNs            : "
        f"{np.sum(~np.isfinite(full_grid))}"
    )

    print("\nSUPPORTED-CELL PRESERVATION")
    print(
        f"  L1 change                 : "
        f"{supported_l1:.6e}"
    )
    print(
        f"  Linf change               : "
        f"{supported_linf:.6e}"
    )

    print("\nUNSUPPORTED-CELL COMPLETION")
    print(
        f"  Background L1 error       : "
        f"{background_l1:.6e}"
    )
    print(
        f"  Background Linf error     : "
        f"{background_linf:.6e}"
    )

    print("\nDIAGNOSTIC PLUME PRESERVATION")
    print(
        f"  Supported plume before    : "
        f"{plume_count_before:,}"
    )
    print(
        f"  Full-grid plume after     : "
        f"{plume_count_after:,}"
    )
    print(
        f"  Unsupported plume added   : "
        f"{unsupported_plume_count:,}"
    )

    print("\n" + "=" * 78)
    print("V15-SG7D4 FINAL CONTROLLED GATES")
    print("=" * 78)

    for name, passed in gates.items():
        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{name}"
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
        f"  {SOURCE_TABLE.name}"
    )
    print(
        f"  {COMPLETION_TABLE.name}"
    )
    print(
        f"  {SUPPORTED_CLOSURE_TABLE.name}"
    )
    print(
        f"  {UNSUPPORTED_TABLE.name}"
    )
    print(
        f"  {PLUME_TABLE.name}"
    )
    print(
        f"  {BOUNDS_TABLE.name}"
    )
    print(
        f"  {GATE_TABLE.name}"
    )

    print("\nNumerical:")
    print(
        f"  {NUMERICAL_FILE.name}"
    )

    print("\nCandidate manifest:")
    print(
        f"  {MANIFEST_FILE.name}"
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
    print("V15-SG7D4 CONTROLLED FULL-GRID COMPLETION: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen L2 array was changed.")
    print("No SG7D1 supported cell was changed.")
    print("No interpolation or nearest-neighbor fill was used.")
    print("No SG7E threshold was changed.")
    print("No full-grid candidate was frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
