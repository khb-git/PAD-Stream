from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7D5
# Independent Full-Grid Completion Validation
#
# INDEPENDENT VALIDATION MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D1 SUPPORTED CELL CHANGED.
# NO SG7D4 FULL-GRID ARRAY CHANGED.
# NO INTERPOLATION.
# NO NEAREST-NEIGHBOR FILL.
# NO SG7E THRESHOLD CHANGED.
# NO FULL-GRID CANDIDATE FROZEN BY SG7D5.
#
# PURPOSE
# -------
# SG7D4 produced a complete 15 x 50 x 50 saturation field using:
#
#   supported cells   -> exact SG7D1 mapped values
#   unsupported cells -> frozen transport background saturation
#
# SG7D5 independently reconstructs that full-grid candidate from authoritative
# upstream sources and validates:
#
#   1. SG7D4 artifact identity / provenance,
#   2. exact support-mask reproduction,
#   3. exact supported-cell preservation,
#   4. exact unsupported background completion,
#   5. full-grid closure against SG7D4 candidate,
#   6. saturation bounds,
#   7. no unsupported plume creation,
#   8. plume topology preservation,
#   9. conservative SG7D1 evidence preservation,
#  10. readiness for formal SG7D freeze before SG7E.
#
# SG7D5 does NOT freeze the candidate.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7D5"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

SG7D4_DIR = ROOT / "output" / "V15_SG7D4"

SG7D4_SUMMARY = (
    SG7D4_DIR / "PAD_Stream_V15SG7D4_Summary.json"
)

SG7D4_CONTRACT = (
    SG7D4_DIR / "V15SG7D4_Background_Completion_Contract.json"
)

SG7D4_MANIFEST = (
    SG7D4_DIR / "V15SG7D4_Full_Grid_Candidate_Manifest.json"
)

SG7D4_NUMERICAL = (
    SG7D4_DIR / "V15SG7D4_Completed_Full_Grid.npz"
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

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7D5_Summary.json"

HASH_TABLE = OUT / "V15SG7D5_Artifact_Identity_Audit.csv"
RECON_TABLE = OUT / "V15SG7D5_Independent_Reconstruction_Closure.csv"
SUPPORTED_TABLE = OUT / "V15SG7D5_Supported_Cell_Validation.csv"
UNSUPPORTED_TABLE = OUT / "V15SG7D5_Unsupported_Background_Validation.csv"
BOUNDS_TABLE = OUT / "V15SG7D5_Full_Grid_Bounds_Audit.csv"
PLUME_TABLE = OUT / "V15SG7D5_Plume_Topology_Validation.csv"
CONSERVATION_TABLE = OUT / "V15SG7D5_Conservative_Evidence_Audit.csv"
GATE_TABLE = OUT / "V15SG7D5_Final_Gate_Matrix.csv"

NUMERICAL_FILE = OUT / "V15SG7D5_Independent_Full_Grid_Validation.npz"
FREEZE_READINESS = OUT / "V15SG7D5_Freeze_Readiness_Manifest.json"
CONTRACT_FILE = OUT / "V15SG7D5_Independent_Full_Grid_Validation_Contract.json"

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EXPECTED_SHAPE = (15, 50, 50)
DIAGNOSTIC_THRESHOLD = 0.21

# SG7D4 stored saturation arrays as float32; independent reconstruction uses
# float64 upstream values and is compared with a dtype-aware envelope.
FLOAT32_STATE_ENVELOPE = 1.5e-7

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


def array_sha256(arr):
    return hashlib.sha256(
        np.ascontiguousarray(arr).tobytes()
    ).hexdigest()


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
    print("PAD-Stream Version 15-SG7D5")
    print("Independent Full-Grid Completion Validation")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D1 SUPPORTED CELL WILL BE CHANGED.
NO SG7D4 FULL-GRID ARRAY WILL BE CHANGED.
NO INTERPOLATION OR NEAREST-NEIGHBOR FILL WILL BE USED.
NO SG7E THRESHOLD WILL BE CHANGED.
NO FULL-GRID CANDIDATE WILL BE FROZEN BY SG7D5.
""")

    summary = load_json(SG7D4_SUMMARY)
    contract = load_json(SG7D4_CONTRACT)
    manifest = load_json(SG7D4_MANIFEST)

    if (
        summary.get("status")
        !=
        "BACKGROUND_ONLY_FULL_GRID_CANDIDATE_COMPLETE"
    ):
        raise RuntimeError(
            "SG7D5 requires successful SG7D4 full-grid completion."
        )

    if (
        summary.get("diagnosis")
        !=
        "FULL_GRID_COMPLETION_PRESERVES_SUPPORTED_PHYSICS_AND_ADDS_NO_PLUME"
    ):
        raise RuntimeError(
            "SG7D5 requires the SG7D4 preservation diagnosis."
        )

    if (
        contract.get("policy")
        !=
        "P4_MASKED_BACKGROUND_PLUS_SUPPORT"
    ):
        raise RuntimeError(
            "SG7D5 requires the P4 background-only completion policy."
        )

    if manifest.get("candidate") != "P4_full_grid":
        raise RuntimeError(
            "SG7D5 expects SG7D4 candidate identity P4_full_grid."
        )

    for path in (
        SG7D4_NUMERICAL,
        SG7D1_NUMERICAL,
        R1F3_FROZEN,
    ):
        if not path.exists():
            raise FileNotFoundError(f"Missing prerequisite:\n{path}")

    sg7d4_sha = sha256(SG7D4_NUMERICAL)
    sg7d1_sha = sha256(SG7D1_NUMERICAL)
    frozen_sha = sha256(R1F3_FROZEN)

    if sg7d4_sha != manifest["full_grid_sha256"]:
        raise RuntimeError(
            "SG7D4 numerical artifact hash does not match SG7D4 manifest."
        )

    if sg7d1_sha != manifest["SG7D1_sha256"]:
        raise RuntimeError(
            "SG7D1 numerical artifact hash does not match SG7D4 manifest."
        )

    if frozen_sha != manifest["frozen_L2_sha256"]:
        raise RuntimeError(
            "Frozen L2 hash does not match SG7D4 manifest."
        )

    d4 = np.load(SG7D4_NUMERICAL, allow_pickle=True)
    d1 = np.load(SG7D1_NUMERICAL, allow_pickle=True)
    frozen = np.load(R1F3_FROZEN, allow_pickle=True)

    required_d4 = [
        "saturation_grid_full",
        "saturation_grid_supported_only",
        "supported_mask",
        "support_denominator",
        "support_numerator",
        "background_saturation",
    ]

    missing = [k for k in required_d4 if k not in d4.files]

    if missing:
        raise RuntimeError(
            "SG7D4 numerical package incomplete: "
            + ", ".join(missing)
        )

    full_persisted = np.asarray(
        d4["saturation_grid_full"],
        dtype=np.float64,
    )

    supported_only_persisted = np.asarray(
        d4["saturation_grid_supported_only"],
        dtype=np.float64,
    )

    support_mask_d4 = np.asarray(
        d4["supported_mask"],
        dtype=np.uint8,
    ).astype(bool)

    den_d4 = np.asarray(
        d4["support_denominator"],
        dtype=np.float64,
    )

    num_d4 = np.asarray(
        d4["support_numerator"],
        dtype=np.float64,
    )

    background_d4 = float(
        np.asarray(
            d4["background_saturation"]
        )
    )

    mapped_d1 = np.asarray(
        d1["saturation_grid"],
        dtype=np.float64,
    )

    support_mask_d1 = np.asarray(
        d1["supported_mask"],
        dtype=np.uint8,
    ).astype(bool)

    den_d1 = np.asarray(
        d1["support_denominator"],
        dtype=np.float64,
    )

    num_d1 = np.asarray(
        d1["support_numerator"],
        dtype=np.float64,
    )

    l2 = np.asarray(
        frozen["L2_independent_100"],
        dtype=np.float64,
    )

    background_frozen = float(np.min(l2))

    if full_persisted.shape != EXPECTED_SHAPE:
        raise RuntimeError(
            f"Unexpected completed grid shape {full_persisted.shape}."
        )

    if not (
        mapped_d1.shape
        ==
        support_mask_d1.shape
        ==
        den_d1.shape
        ==
        num_d1.shape
        ==
        EXPECTED_SHAPE
    ):
        raise RuntimeError(
            "SG7D1 authoritative arrays are not shape-compatible."
        )

    # -------------------------------------------------------------------------
    # Independent reconstruction from authoritative sources
    # -------------------------------------------------------------------------

    reconstructed = mapped_d1.copy()

    reconstructed[
        ~support_mask_d1
    ] = background_frozen

    reconstruction_delta = (
        reconstructed
        -
        full_persisted
    )

    reconstruction_l1 = float(
        np.mean(
            np.abs(
                reconstruction_delta
            )
        )
    )

    reconstruction_linf = float(
        np.max(
            np.abs(
                reconstruction_delta
            )
        )
    )

    # Compare after float32 persistence too.
    reconstructed32 = reconstructed.astype(np.float32)
    full32 = full_persisted.astype(np.float32)

    reconstruction32_exact = bool(
        np.array_equal(
            reconstructed32,
            full32,
        )
    )

    # -------------------------------------------------------------------------
    # Supported-cell validation
    # -------------------------------------------------------------------------

    supported_delta = (
        reconstructed[
            support_mask_d1
        ]
        -
        mapped_d1[
            support_mask_d1
        ]
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

    persisted_supported_delta = (
        full_persisted[
            support_mask_d1
        ]
        -
        mapped_d1[
            support_mask_d1
        ]
    )

    persisted_supported_linf = float(
        np.max(
            np.abs(
                persisted_supported_delta
            )
        )
    )

    # -------------------------------------------------------------------------
    # Unsupported-cell validation
    # -------------------------------------------------------------------------

    unsupported = ~support_mask_d1

    unsupported_reconstructed = reconstructed[unsupported]
    unsupported_persisted = full_persisted[unsupported]

    unsupported_recon_linf = float(
        np.max(
            np.abs(
                unsupported_reconstructed
                -
                background_frozen
            )
        )
    )

    unsupported_persisted_linf = float(
        np.max(
            np.abs(
                unsupported_persisted
                -
                background_frozen
            )
        )
    )

    # -------------------------------------------------------------------------
    # Mask / conservative evidence identity
    # -------------------------------------------------------------------------

    support_mask_match = bool(
        np.array_equal(
            support_mask_d4,
            support_mask_d1,
        )
    )

    denominator_match = bool(
        array_sha256(den_d4)
        ==
        array_sha256(den_d1)
    )

    numerator_match = bool(
        array_sha256(num_d4)
        ==
        array_sha256(num_d1)
    )

    # -------------------------------------------------------------------------
    # Bounds
    # -------------------------------------------------------------------------

    l2_min = float(np.min(l2))
    l2_max = float(np.max(l2))

    full_min = float(np.min(full_persisted))
    full_max = float(np.max(full_persisted))

    lower_bound_pass = bool(
        full_min >= l2_min - FLOAT32_STATE_ENVELOPE
    )

    upper_bound_pass = bool(
        full_max <= l2_max + FLOAT32_STATE_ENVELOPE
    )

    all_finite = bool(
        np.all(
            np.isfinite(
                full_persisted
            )
        )
    )

    # -------------------------------------------------------------------------
    # Plume / topology validation
    # -------------------------------------------------------------------------

    supported_plume_reference = (
        support_mask_d1
        &
        np.isfinite(mapped_d1)
        &
        (
            mapped_d1
            >=
            DIAGNOSTIC_THRESHOLD
        )
    )

    completed_plume = (
        full_persisted
        >=
        DIAGNOSTIC_THRESHOLD
    )

    unsupported_plume = (
        unsupported
        &
        completed_plume
    )

    supported_plume_completed = (
        support_mask_d1
        &
        completed_plume
    )

    supported_plume_exact = bool(
        np.array_equal(
            supported_plume_reference,
            supported_plume_completed,
        )
    )

    unsupported_plume_cells = int(
        np.sum(
            unsupported_plume
        )
    )

    ref_components = connected_components_3d(
        supported_plume_reference
    )

    full_components = connected_components_3d(
        completed_plume
    )

    topology_preserved = bool(
        len(ref_components) == len(full_components)
        and
        ref_components == full_components
    )

    # -------------------------------------------------------------------------
    # Tables
    # -------------------------------------------------------------------------

    save_csv(
        HASH_TABLE,
        [
            {
                "artifact": "SG7D4 full-grid candidate",
                "path": str(SG7D4_NUMERICAL),
                "sha256": sg7d4_sha,
                "manifest_match":
                    sg7d4_sha == manifest["full_grid_sha256"],
            },
            {
                "artifact": "SG7D1 conservative map-back",
                "path": str(SG7D1_NUMERICAL),
                "sha256": sg7d1_sha,
                "manifest_match":
                    sg7d1_sha == manifest["SG7D1_sha256"],
            },
            {
                "artifact": "R1F3 frozen L2",
                "path": str(R1F3_FROZEN),
                "sha256": frozen_sha,
                "manifest_match":
                    frozen_sha == manifest["frozen_L2_sha256"],
            },
        ],
    )

    save_csv(
        RECON_TABLE,
        [{
            "full_grid_reconstruction_L1":
                reconstruction_l1,

            "full_grid_reconstruction_Linf":
                reconstruction_linf,

            "float32_reconstruction_exact":
                reconstruction32_exact,

            "precision_envelope":
                FLOAT32_STATE_ENVELOPE,

            "precision_aware_closure_pass":
                reconstruction_linf
                <=
                FLOAT32_STATE_ENVELOPE,
        }],
    )

    save_csv(
        SUPPORTED_TABLE,
        [{
            "supported_cells":
                int(np.sum(support_mask_d1)),

            "independent_supported_L1_change":
                supported_l1,

            "independent_supported_Linf_change":
                supported_linf,

            "persisted_supported_vs_SG7D1_Linf":
                persisted_supported_linf,

            "supported_cells_preserved":
                persisted_supported_linf
                <=
                FLOAT32_STATE_ENVELOPE,
        }],
    )

    save_csv(
        UNSUPPORTED_TABLE,
        [{
            "unsupported_cells":
                int(np.sum(unsupported)),

            "frozen_background":
                background_frozen,

            "SG7D4_background":
                background_d4,

            "background_scalar_error":
                abs(
                    background_d4
                    -
                    background_frozen
                ),

            "independent_unsupported_background_Linf":
                unsupported_recon_linf,

            "persisted_unsupported_background_Linf":
                unsupported_persisted_linf,

            "unsupported_background_pass":
                unsupported_persisted_linf
                <=
                FLOAT32_STATE_ENVELOPE,
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

            "all_finite":
                all_finite,

            "lower_bound_pass":
                lower_bound_pass,

            "upper_bound_pass":
                upper_bound_pass,
        }],
    )

    save_csv(
        PLUME_TABLE,
        [{
            "diagnostic_threshold":
                DIAGNOSTIC_THRESHOLD,

            "threshold_semantics":
                "DIAGNOSTIC_ONLY_NO_SG7E_CHANGE",

            "supported_plume_reference_cells":
                int(
                    np.sum(
                        supported_plume_reference
                    )
                ),

            "completed_plume_cells":
                int(
                    np.sum(
                        completed_plume
                    )
                ),

            "unsupported_plume_cells":
                unsupported_plume_cells,

            "supported_plume_membership_exact":
                supported_plume_exact,

            "reference_component_count":
                len(
                    ref_components
                ),

            "completed_component_count":
                len(
                    full_components
                ),

            "reference_component_sizes":
                ";".join(
                    map(
                        str,
                        ref_components[:10]
                    )
                ),

            "completed_component_sizes":
                ";".join(
                    map(
                        str,
                        full_components[:10]
                    )
                ),

            "topology_preserved":
                topology_preserved,
        }],
    )

    save_csv(
        CONSERVATION_TABLE,
        [{
            "support_mask_sha_match":
                support_mask_match,

            "denominator_sha_match":
                denominator_match,

            "numerator_sha_match":
                numerator_match,

            "SG7D1_conservative_evidence_preserved":
                bool(
                    support_mask_match
                    and
                    denominator_match
                    and
                    numerator_match
                ),
        }],
    )

    # -------------------------------------------------------------------------
    # Validation gates
    # -------------------------------------------------------------------------

    gates = {
        "SG7D4_success_status_reproduced":
            True,

        "SG7D4_candidate_hash_reproduced":
            sg7d4_sha
            ==
            manifest["full_grid_sha256"],

        "SG7D1_hash_reproduced":
            sg7d1_sha
            ==
            manifest["SG7D1_sha256"],

        "frozen_L2_hash_reproduced":
            frozen_sha
            ==
            manifest["frozen_L2_sha256"],

        "support_mask_reproduced":
            support_mask_match,

        "full_grid_precision_aware_reconstruction_closure":
            reconstruction_linf
            <=
            FLOAT32_STATE_ENVELOPE,

        "full_grid_float32_reconstruction_exact":
            reconstruction32_exact,

        "supported_cells_preserved":
            persisted_supported_linf
            <=
            FLOAT32_STATE_ENVELOPE,

        "unsupported_cells_equal_frozen_background":
            unsupported_persisted_linf
            <=
            FLOAT32_STATE_ENVELOPE,

        "background_scalar_reproduced":
            abs(
                background_d4
                -
                background_frozen
            )
            <=
            1e-12,

        "conservative_support_mask_preserved":
            support_mask_match,

        "conservative_denominator_preserved":
            denominator_match,

        "conservative_numerator_preserved":
            numerator_match,

        "full_grid_all_finite":
            all_finite,

        "full_grid_lower_bound":
            lower_bound_pass,

        "full_grid_upper_bound":
            upper_bound_pass,

        "supported_plume_membership_preserved":
            supported_plume_exact,

        "unsupported_background_adds_no_plume":
            unsupported_plume_cells
            ==
            0,

        "plume_topology_preserved":
            topology_preserved,

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

    # -------------------------------------------------------------------------
    # Persist independent reconstruction evidence
    # -------------------------------------------------------------------------

    np.savez_compressed(
        NUMERICAL_FILE,

        reconstructed_full_grid=
            reconstructed.astype(np.float32),

        persisted_full_grid=
            full_persisted.astype(np.float32),

        supported_mask=
            support_mask_d1.astype(np.uint8),

        frozen_background=
            np.asarray(
                background_frozen,
                dtype=np.float64,
            ),

        diagnostic_threshold=
            np.asarray(
                DIAGNOSTIC_THRESHOLD,
                dtype=np.float64,
            ),

        SG7D4_sha256=
            np.asarray(
                sg7d4_sha
            ),

        SG7D1_sha256=
            np.asarray(
                sg7d1_sha
            ),

        frozen_L2_sha256=
            np.asarray(
                frozen_sha
            ),
    )

    # -------------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------------

    if complete:

        status = "FULL_GRID_CANDIDATE_FREEZE_READY"

        diagnosis = "P4_FULL_GRID_INDEPENDENT_VALIDATION_PASSES_COMPLETE_CONTRACT"

        recommendation = (
            "The completed 15x50x50 field independently reconstructs from SG7D1 plus the "
            "frozen background rule, preserves every supported cell and conservative map-back "
            "artifact, creates no unsupported plume cells, and preserves plume topology. "
            "Proceed to formal SG7D freeze/provenance. Do not alter the field or SG7E threshold."
        )

        next_milestone = (
            "V15-SG7D6 — Full-Grid Candidate Freeze / Provenance Manifest"
        )

    else:

        status = "FULL_GRID_CANDIDATE_INDEPENDENT_VALIDATION_FAILED"

        diagnosis = "P4_FULL_GRID_FAILS_ONE_OR_MORE_INDEPENDENT_GATES"

        recommendation = (
            "Do not freeze the SG7D4 field. Audit only the remaining independent closure, "
            "supported-cell, background, conservative-evidence, or plume-topology failure."
        )

        next_milestone = (
            "V15-SG7D5R — Independent Full-Grid Validation Failure Audit"
        )

    save_json(
        FREEZE_READINESS,
        {
            "milestone":
                "V15-SG7D5",

            "candidate":
                "P4_full_grid",

            "status":
                status,

            "freeze_ready":
                complete,

            "candidate_frozen":
                False,

            "full_grid_sha256":
                sg7d4_sha,

            "SG7D1_sha256":
                sg7d1_sha,

            "frozen_L2_sha256":
                frozen_sha,

            "background_saturation":
                background_frozen,

            "supported_cells":
                int(
                    np.sum(
                        support_mask_d1
                    )
                ),

            "unsupported_cells":
                int(
                    np.sum(
                        unsupported
                    )
                ),

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
                "V15-SG7D5",

            "status":
                status,

            "diagnosis":
                diagnosis,

            "candidate":
                "P4_full_grid",

            "candidate_frozen":
                False,

            "independent_reconstruction_rule":
                "SG7D1 supported cells + frozen L2 minimum/background on unsupported cells",

            "precision_envelope":
                FLOAT32_STATE_ENVELOPE,

            "full_grid_reconstruction_Linf":
                reconstruction_linf,

            "float32_reconstruction_exact":
                reconstruction32_exact,

            "supported_cells_preserved":
                persisted_supported_linf
                <=
                FLOAT32_STATE_ENVELOPE,

            "unsupported_background_preserved":
                unsupported_persisted_linf
                <=
                FLOAT32_STATE_ENVELOPE,

            "conservative_evidence_preserved":
                bool(
                    support_mask_match
                    and
                    denominator_match
                    and
                    numerator_match
                ),

            "unsupported_plume_cells":
                unsupported_plume_cells,

            "plume_topology_preserved":
                topology_preserved,

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
                "V15-SG7D5",

            "status":
                status,

            "diagnosis":
                diagnosis,

            "candidate":
                "P4_full_grid",

            "freeze_ready":
                complete,

            "candidate_frozen":
                False,

            "full_grid_reconstruction_Linf":
                reconstruction_linf,

            "supported_cells":
                int(
                    np.sum(
                        support_mask_d1
                    )
                ),

            "unsupported_cells":
                int(
                    np.sum(
                        unsupported
                    )
                ),

            "unsupported_plume_cells":
                unsupported_plume_cells,

            "plume_topology_preserved":
                topology_preserved,

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

    print("INDEPENDENT FULL-GRID RECONSTRUCTION")
    print(
        f"  Reconstruction L1       : "
        f"{reconstruction_l1:.6e}"
    )
    print(
        f"  Reconstruction Linf     : "
        f"{reconstruction_linf:.6e}"
    )
    print(
        f"  Precision envelope      : "
        f"{FLOAT32_STATE_ENVELOPE:.6e}"
    )
    print(
        f"  Float32 exact match     : "
        f"{reconstruction32_exact}"
    )

    print("\nSUPPORTED-CELL VALIDATION")
    print(
        f"  Supported cells         : "
        f"{np.sum(support_mask_d1):,}"
    )
    print(
        f"  Persisted vs SG7D1 Linf : "
        f"{persisted_supported_linf:.6e}"
    )

    print("\nUNSUPPORTED-CELL VALIDATION")
    print(
        f"  Unsupported cells       : "
        f"{np.sum(unsupported):,}"
    )
    print(
        f"  Frozen background       : "
        f"{background_frozen:.6f}"
    )
    print(
        f"  Persisted background err: "
        f"{unsupported_persisted_linf:.6e}"
    )

    print("\nPLUME / TOPOLOGY VALIDATION")
    print(
        f"  Supported plume cells   : "
        f"{np.sum(supported_plume_reference):,}"
    )
    print(
        f"  Completed plume cells   : "
        f"{np.sum(completed_plume):,}"
    )
    print(
        f"  Unsupported plume cells : "
        f"{unsupported_plume_cells:,}"
    )
    print(
        f"  Ref components          : "
        f"{len(ref_components)}"
    )
    print(
        f"  Completed components    : "
        f"{len(full_components)}"
    )
    print(
        f"  Topology preserved      : "
        f"{topology_preserved}"
    )

    print("\n" + "=" * 78)
    print("V15-SG7D5 FINAL INDEPENDENT GATES")
    print("=" * 78)

    for name, passed in gates.items():
        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{name}"
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
    print(f"  {HASH_TABLE.name}")
    print(f"  {RECON_TABLE.name}")
    print(f"  {SUPPORTED_TABLE.name}")
    print(f"  {UNSUPPORTED_TABLE.name}")
    print(f"  {BOUNDS_TABLE.name}")
    print(f"  {PLUME_TABLE.name}")
    print(f"  {CONSERVATION_TABLE.name}")
    print(f"  {GATE_TABLE.name}")

    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")

    print("\nFreeze-readiness manifest:")
    print(f"  {FREEZE_READINESS.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7D5 INDEPENDENT FULL-GRID VALIDATION: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen L2 array was changed.")
    print("No SG7D1 supported cell was changed.")
    print("No SG7D4 full-grid array was changed.")
    print("No interpolation or nearest-neighbor fill was used.")
    print("No SG7E threshold was changed.")
    print("No full-grid candidate was frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
