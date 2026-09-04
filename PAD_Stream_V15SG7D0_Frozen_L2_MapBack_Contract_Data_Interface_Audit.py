from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7D0
# Frozen L2 Map-Back Contract / Data-Interface Audit
#
# DIAGNOSTIC / CONTRACT MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO STREAMLINE GEOMETRY CHANGED.
# NO MAP-BACK PERFORMED.
# NO SG7E THRESHOLD CHANGED.
#
# PURPOSE
# -------
# SG7C is formally frozen:
#
#   frozen candidate = L2
#
# SG7D0 establishes the exact data contract between:
#
#   frozen streamline-space transport
#
# and:
#
#   the 3-D SGSim Cartesian grid.
#
# The audit must establish, without performing deposition:
#
#   1. frozen L2 candidate identity and hash,
#   2. streamline count and common xi-node count,
#   3. SG6 transport-coordinate geometry,
#   4. streamline terminal TOF,
#   5. streamline weights / flux weights,
#   6. streamline xyz coordinates,
#   7. target SGSim grid dimensions,
#   8. target cell indexing convention,
#   9. whether sufficient information exists for a conservative map-back,
#  10. the exact conservation contract for SG7D1.
#
# SG7D0 DOES NOT MAP SATURATION BACK TO THE GRID.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7D0"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Frozen SG7C source
# -----------------------------------------------------------------------------

R1F3_DIR = ROOT / "output" / "V15_SG7CR3F5R1F3"

FREEZE_MANIFEST = (
    R1F3_DIR
    / "V15SG7CR3F5R1F3_Freeze_Manifest.json"
)

FROZEN_CONTRACT = (
    R1F3_DIR
    / "V15SG7CR3F5R1F3_Frozen_Deployment_Contract.json"
)

FROZEN_CANDIDATE = (
    R1F3_DIR
    / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

# -----------------------------------------------------------------------------
# SG6 / streamline geometry discovery
# -----------------------------------------------------------------------------

SG6_HINTS = [
    "V15_SG6",
    "V15_SG7A",
    "V15_SG7C",
]

EXPECTED_GRID = (15, 50, 50)
EXPECTED_STREAMLINES = None          # discovered from frozen candidate
EXPECTED_XI_NODES = 201

# Expected SGSim Cartesian geometry from the frozen SG model.
DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7D0_Summary.json"
FROZEN_IDENTITY_TABLE = OUT / "V15SG7D0_Frozen_L2_Identity.csv"
ARRAY_INVENTORY_TABLE = OUT / "V15SG7D0_Array_Interface_Inventory.csv"
GEOMETRY_TABLE = OUT / "V15SG7D0_Streamline_Geometry_Interface.csv"
GRID_TABLE = OUT / "V15SG7D0_Target_Grid_Contract.csv"
WEIGHT_TABLE = OUT / "V15SG7D0_Streamline_Weight_Audit.csv"
INDEX_TABLE = OUT / "V15SG7D0_Grid_Indexing_Contract.csv"
MAPBACK_REQUIREMENTS = OUT / "V15SG7D0_Conservative_MapBack_Requirements.csv"
SOURCE_DISCOVERY_TABLE = OUT / "V15SG7D0_Source_Discovery.csv"

CONTRACT_FILE = OUT / "V15SG7D0_Frozen_L2_MapBack_Interface_Contract.json"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


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
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def inventory_npz(path: Path, source_label: str):
    rows = []

    db = np.load(path, allow_pickle=True)

    for key in db.files:
        arr = np.asarray(db[key])

        row = {
            "source": source_label,
            "file": str(path),
            "key": key,
            "dtype": str(arr.dtype),
            "shape": "x".join(map(str, arr.shape)),
            "ndim": arr.ndim,
            "size": arr.size,
        }

        if np.issubdtype(arr.dtype, np.number) and arr.size > 0:
            finite = np.isfinite(arr)

            if np.any(finite):
                vals = arr[finite].astype(np.float64)

                row.update({
                    "finite_fraction": float(np.mean(finite)),
                    "min": float(np.min(vals)),
                    "max": float(np.max(vals)),
                    "mean": float(np.mean(vals)),
                })

        rows.append(row)

    return rows


def discover_npz_candidates():
    """
    Discover likely SG6 / streamline geometry NPZ files.

    We deliberately search by semantic filename patterns rather than assuming
    one historical serialization name.
    """

    candidates = []

    search_roots = [
        ROOT / "output",
        ROOT,
    ]

    seen = set()

    tokens = (
        "SG6",
        "TOF",
        "Transport",
        "Streamline",
        "Pollock",
        "Coordinate",
    )

    for search_root in search_roots:
        if not search_root.exists():
            continue

        for path in search_root.rglob("*.npz"):
            resolved = path.resolve()

            if resolved in seen:
                continue

            seen.add(resolved)

            name = path.name.lower()

            score = sum(
                1
                for token in tokens
                if token.lower() in name
            )

            # Directory names also contribute.
            parent_text = str(path.parent).lower()

            score += sum(
                1
                for token in tokens
                if token.lower() in parent_text
            )

            if score > 0:
                candidates.append(
                    {
                        "path": path,
                        "score": score,
                    }
                )

    candidates.sort(
        key=lambda item: (
            -item["score"],
            len(str(item["path"])),
        )
    )

    return candidates


def classify_array(key: str, arr: np.ndarray):
    """
    Semantic array classification for map-back interface discovery.
    """

    k = key.lower()

    if arr.ndim == 3 and arr.shape[-1] == 3:
        if any(t in k for t in ("xyz", "coord", "position", "streamline")):
            return "streamline_xyz"

    if arr.ndim == 2:
        if any(t in k for t in ("tof", "tau")):
            return "tof_matrix"

        if any(t in k for t in ("weight", "flux")):
            return "weight_matrix"

    if arr.ndim == 1:
        if any(t in k for t in ("weight", "flux")):
            return "streamline_weights"

        if any(t in k for t in ("tau_end", "terminal", "tof_end")):
            return "terminal_tof"

        if key.lower() == "xi":
            return "xi"

    return "other"


def search_geometry_arrays(candidate_paths, frozen_nstream, frozen_nxi):
    """
    Search likely NPZ files for geometry arrays compatible with the frozen
    streamline transport tensor.
    """

    discovered = {
        "streamline_xyz": None,
        "tof_matrix": None,
        "streamline_weights": None,
        "terminal_tof": None,
        "xi": None,
    }

    evidence = []

    for item in candidate_paths:
        path = item["path"]

        try:
            db = np.load(path, allow_pickle=True)
        except Exception as exc:
            evidence.append({
                "file": str(path),
                "score": item["score"],
                "loaded": False,
                "reason": repr(exc),
            })
            continue

        file_has_match = False

        for key in db.files:
            arr = np.asarray(db[key])
            cls = classify_array(key, arr)

            compatible = False

            if cls == "streamline_xyz":
                compatible = (
                    arr.ndim == 3
                    and
                    arr.shape[0] == frozen_nstream
                    and
                    arr.shape[1] == frozen_nxi
                    and
                    arr.shape[2] == 3
                )

            elif cls == "tof_matrix":
                compatible = (
                    arr.ndim == 2
                    and
                    arr.shape[0] == frozen_nstream
                    and
                    arr.shape[1] == frozen_nxi
                )

            elif cls == "streamline_weights":
                compatible = (
                    arr.ndim == 1
                    and
                    arr.size == frozen_nstream
                )

            elif cls == "terminal_tof":
                compatible = (
                    arr.ndim == 1
                    and
                    arr.size == frozen_nstream
                )

            elif cls == "xi":
                compatible = (
                    arr.ndim == 1
                    and
                    arr.size == frozen_nxi
                )

            if compatible and discovered.get(cls) is None:
                discovered[cls] = {
                    "file": path,
                    "key": key,
                    "array": arr,
                }
                file_has_match = True

        evidence.append({
            "file": str(path),
            "score": item["score"],
            "loaded": True,
            "compatible_interface_array_found": file_has_match,
            "keys": ";".join(db.files),
        })

        # Stop early once the essential geometry is found.
        if (
            discovered["streamline_xyz"] is not None
            and
            discovered["tof_matrix"] is not None
            and
            discovered["streamline_weights"] is not None
        ):
            break

    return discovered, evidence


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7D0")
    print("Frozen L2 Map-Back Contract / Data-Interface Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO STREAMLINE GEOMETRY WILL BE CHANGED.
NO MAP-BACK WILL BE PERFORMED.
NO SG7E THRESHOLD WILL BE CHANGED.
""")

    # -------------------------------------------------------------------------
    # Frozen SG7C identity
    # -------------------------------------------------------------------------

    freeze_manifest = load_json(FREEZE_MANIFEST)
    frozen_contract = load_json(FROZEN_CONTRACT)

    if freeze_manifest.get("status") != "SG7C_CROSSING_LOCAL_CANDIDATE_FROZEN":
        raise RuntimeError(
            "SG7D0 requires the formally frozen SG7C L2 candidate."
        )

    if freeze_manifest.get("candidate") != "L2":
        raise RuntimeError(
            "SG7D0 expects the frozen SG7C candidate identity L2."
        )

    if not FROZEN_CANDIDATE.exists():
        raise FileNotFoundError(
            f"Missing frozen SG7C candidate:\n{FROZEN_CANDIDATE}"
        )

    source_sha = sha256(FROZEN_CANDIDATE)

    expected_sha = freeze_manifest.get(
        "frozen_numerical_sha256"
    )

    hash_match = (
        expected_sha is not None
        and
        source_sha == expected_sha
    )

    if not hash_match:
        raise RuntimeError(
            "Frozen L2 SHA-256 does not match the R1F3 freeze manifest."
        )

    frozen = np.load(
        FROZEN_CANDIDATE,
        allow_pickle=True,
    )

    required_frozen_keys = [
        "xi",
        "tau_end",
        "L2_independent_100",
        "L2_gamma_independent",
        "X08_coeff100",
        "exact_support_fraction",
        "truth_front_xi",
        "guard_mask",
    ]

    missing_frozen = [
        key
        for key in required_frozen_keys
        if key not in frozen.files
    ]

    if missing_frozen:
        raise RuntimeError(
            "Frozen L2 artifact is missing required deployment arrays: "
            + ", ".join(missing_frozen)
        )

    xi = np.asarray(
        frozen["xi"],
        dtype=np.float64,
    )

    tau_end = np.asarray(
        frozen["tau_end"],
        dtype=np.float64,
    )

    l2_state = np.asarray(
        frozen["L2_independent_100"],
        dtype=np.float64,
    )

    nstream, nxi = l2_state.shape

    frozen_identity_rows = [{
        "candidate": "L2",
        "frozen_file": str(FROZEN_CANDIDATE),
        "sha256": source_sha,
        "hash_matches_freeze_manifest": hash_match,
        "streamline_count": nstream,
        "xi_nodes": nxi,
        "exact_support_fraction":
            float(np.asarray(frozen["exact_support_fraction"])),
        "state_min": float(np.min(l2_state)),
        "state_max": float(np.max(l2_state)),
        "crossing_guard_half_width":
            freeze_manifest.get("selected_guard_half_width"),
    }]

    save_csv(
        FROZEN_IDENTITY_TABLE,
        frozen_identity_rows,
    )

    # -------------------------------------------------------------------------
    # Inventory frozen candidate
    # -------------------------------------------------------------------------

    inventory_rows = inventory_npz(
        FROZEN_CANDIDATE,
        "frozen_L2",
    )

    # -------------------------------------------------------------------------
    # Discover SG6 / streamline geometry
    # -------------------------------------------------------------------------

    candidate_paths = discover_npz_candidates()

    geometry_sources, discovery_rows = search_geometry_arrays(
        candidate_paths,
        nstream,
        nxi,
    )

    save_csv(
        SOURCE_DISCOVERY_TABLE,
        discovery_rows,
    )

    for cls, rec in geometry_sources.items():
        if rec is not None:
            inventory_rows.extend(
                inventory_npz(
                    rec["file"],
                    f"geometry_source:{cls}",
                )
            )

    save_csv(
        ARRAY_INVENTORY_TABLE,
        inventory_rows,
    )

    xyz_rec = geometry_sources["streamline_xyz"]
    tof_rec = geometry_sources["tof_matrix"]
    weight_rec = geometry_sources["streamline_weights"]
    terminal_rec = geometry_sources["terminal_tof"]
    xi_rec = geometry_sources["xi"]

    # -------------------------------------------------------------------------
    # Geometry compatibility audit
    # -------------------------------------------------------------------------

    geometry_rows = []

    geometry_rows.append({
        "interface": "frozen_transport_state",
        "available": True,
        "shape": f"{nstream}x{nxi}",
        "source": str(FROZEN_CANDIDATE),
        "key": "L2_independent_100",
    })

    geometry_rows.append({
        "interface": "streamline_xyz",
        "available": xyz_rec is not None,
        "shape":
            (
                "x".join(map(str, xyz_rec["array"].shape))
                if xyz_rec is not None
                else ""
            ),
        "source":
            str(xyz_rec["file"])
            if xyz_rec is not None
            else "",
        "key":
            xyz_rec["key"]
            if xyz_rec is not None
            else "",
    })

    geometry_rows.append({
        "interface": "tof_matrix",
        "available": tof_rec is not None,
        "shape":
            (
                "x".join(map(str, tof_rec["array"].shape))
                if tof_rec is not None
                else ""
            ),
        "source":
            str(tof_rec["file"])
            if tof_rec is not None
            else "",
        "key":
            tof_rec["key"]
            if tof_rec is not None
            else "",
    })

    geometry_rows.append({
        "interface": "streamline_weights",
        "available": weight_rec is not None,
        "shape":
            (
                "x".join(map(str, weight_rec["array"].shape))
                if weight_rec is not None
                else ""
            ),
        "source":
            str(weight_rec["file"])
            if weight_rec is not None
            else "",
        "key":
            weight_rec["key"]
            if weight_rec is not None
            else "",
    })

    geometry_rows.append({
        "interface": "terminal_tof",
        "available":
            terminal_rec is not None
            or
            tau_end.size == nstream,
        "shape":
            (
                "x".join(map(str, terminal_rec["array"].shape))
                if terminal_rec is not None
                else str(tau_end.shape)
            ),
        "source":
            (
                str(terminal_rec["file"])
                if terminal_rec is not None
                else str(FROZEN_CANDIDATE)
            ),
        "key":
            (
                terminal_rec["key"]
                if terminal_rec is not None
                else "tau_end"
            ),
    })

    save_csv(
        GEOMETRY_TABLE,
        geometry_rows,
    )

    # -------------------------------------------------------------------------
    # Streamline weight audit
    # -------------------------------------------------------------------------

    weight_rows = []

    if weight_rec is not None:

        weights = np.asarray(
            weight_rec["array"],
            dtype=np.float64,
        )

        finite = np.all(np.isfinite(weights))
        positive = np.all(weights > 0.0)
        weight_sum = float(np.sum(weights))
        normalized = weights / max(weight_sum, 1e-30)

        weight_rows.append({
            "available": True,
            "source": str(weight_rec["file"]),
            "key": weight_rec["key"],
            "count": weights.size,
            "all_finite": finite,
            "all_positive": positive,
            "sum": weight_sum,
            "normalized_sum": float(np.sum(normalized)),
            "min": float(np.min(weights)),
            "max": float(np.max(weights)),
            "mean": float(np.mean(weights)),
        })

    else:

        weight_rows.append({
            "available": False,
            "source": "",
            "key": "",
            "count": 0,
            "all_finite": False,
            "all_positive": False,
            "sum": np.nan,
            "normalized_sum": np.nan,
            "min": np.nan,
            "max": np.nan,
            "mean": np.nan,
        })

    save_csv(
        WEIGHT_TABLE,
        weight_rows,
    )

    # -------------------------------------------------------------------------
    # Target grid contract
    # -------------------------------------------------------------------------

    nz, ny, nx = EXPECTED_GRID
    ncells = nx * ny * nz

    grid_rows = [{
        "NZ": nz,
        "NY": ny,
        "NX": nx,
        "logical_cells": ncells,
        "dx_ft": DX_FT,
        "dy_ft": DY_FT,
        "dz_ft": DZ_FT,
        "x_extent_ft": nx * DX_FT,
        "y_extent_ft": ny * DY_FT,
        "z_extent_ft": nz * DZ_FT,
        "array_order": "(k, j, i) = (z, y, x)",
        "expected_numpy_shape": f"({nz}, {ny}, {nx})",
    }]

    save_csv(
        GRID_TABLE,
        grid_rows,
    )

    index_rows = [
        {
            "axis": "x",
            "numpy_index": "i",
            "range": f"0..{nx-1}",
            "physical_coordinate_contract":
                "cell center x = (i + 0.5) * dx",
        },
        {
            "axis": "y",
            "numpy_index": "j",
            "range": f"0..{ny-1}",
            "physical_coordinate_contract":
                "cell center y = (j + 0.5) * dy",
        },
        {
            "axis": "z",
            "numpy_index": "k",
            "range": f"0..{nz-1}",
            "physical_coordinate_contract":
                "cell center z = (k + 0.5) * dz relative to model origin",
        },
        {
            "axis": "flattened",
            "numpy_index": "linear",
            "range": f"0..{ncells-1}",
            "physical_coordinate_contract":
                "linear = (k * NY + j) * NX + i",
        },
    ]

    save_csv(
        INDEX_TABLE,
        index_rows,
    )

    # -------------------------------------------------------------------------
    # Conservative map-back requirements
    # -------------------------------------------------------------------------

    requirement_rows = [
        {
            "requirement": "Frozen transport immutability",
            "definition":
                "SG7D1 must read L2 directly from the R1F3 frozen artifact.",
            "acceptance":
                "Source SHA-256 must match R1F3 manifest.",
        },
        {
            "requirement": "Geometric deposition basis",
            "definition":
                "Each streamline xi sample must be associated with its 3-D xyz location.",
            "acceptance":
                f"xyz shape must equal ({nstream}, {nxi}, 3).",
        },
        {
            "requirement": "Streamline weighting",
            "definition":
                "Deposited saturation contribution must retain the frozen streamline flux/volume weight.",
            "acceptance":
                f"One positive finite weight per streamline ({nstream}).",
        },
        {
            "requirement": "Grid-index consistency",
            "definition":
                "Every deposited xyz point must map to exactly one valid SGSim logical cell or be explicitly boundary-clipped.",
            "acceptance":
                f"Indices must remain within shape {EXPECTED_GRID}.",
        },
        {
            "requirement": "Conservative weighted averaging",
            "definition":
                "For each grid cell, saturation is weighted by deposited streamline support, not simple unweighted streamline count.",
            "acceptance":
                "cell numerator = sum(w * S * deposition_measure); denominator = sum(w * deposition_measure).",
        },
        {
            "requirement": "No unsupported-cell invention",
            "definition":
                "Cells receiving zero streamline support must not be assigned arbitrary plume saturation.",
            "acceptance":
                "Unsupported cells retain explicit fallback status and are handled by a separately audited rule.",
        },
        {
            "requirement": "Mass / support closure",
            "definition":
                "Total deposited weighted support before and after grid accumulation must close numerically.",
            "acceptance":
                "relative support closure target <= 1e-10 for float64 accumulation.",
        },
        {
            "requirement": "Saturation bounds",
            "definition":
                "Mapped cell saturation must remain within the frozen transport state bounds.",
            "acceptance":
                f"{float(np.min(l2_state)):.12e} <= S_grid <= {float(np.max(l2_state)):.12e}.",
        },
        {
            "requirement": "Deterministic mapping",
            "definition":
                "Repeated SG7D1 runs with identical frozen inputs must reproduce identical map-back arrays.",
            "acceptance":
                "Frozen map-back output hash reproducible.",
        },
    ]

    save_csv(
        MAPBACK_REQUIREMENTS,
        requirement_rows,
    )

    # -------------------------------------------------------------------------
    # Interface readiness classification
    # -------------------------------------------------------------------------

    checks = []

    checks.append((
        "Frozen R1F3 L2 candidate loaded",
        True,
    ))

    checks.append((
        "Frozen candidate SHA-256 reproduced",
        hash_match,
    ))

    checks.append((
        "Frozen L2 transport field is 2-D streamline/xi",
        l2_state.ndim == 2,
    ))

    checks.append((
        "Frozen xi node count consistent",
        xi.size == nxi,
    ))

    checks.append((
        "Frozen terminal TOF count consistent",
        tau_end.size == nstream,
    ))

    checks.append((
        "Expected 201-node common xi grid retained",
        nxi == EXPECTED_XI_NODES,
    ))

    checks.append((
        "3-D streamline xyz interface discovered",
        xyz_rec is not None,
    ))

    checks.append((
        "TOF matrix interface discovered",
        tof_rec is not None,
    ))

    checks.append((
        "Positive finite streamline-weight interface discovered",
        (
            weight_rec is not None
            and
            np.all(np.isfinite(np.asarray(weight_rec["array"], dtype=float)))
            and
            np.all(np.asarray(weight_rec["array"], dtype=float) > 0.0)
        ),
    ))

    checks.append((
        "Target SGSim grid contract established",
        EXPECTED_GRID == (15, 50, 50),
    ))

    checks.append((
        "Grid indexing convention established",
        True,
    ))

    checks.append((
        "Conservative map-back requirements established",
        len(requirement_rows) > 0,
    ))

    checks.append((
        "No map-back performed by SG7D0",
        True,
    ))

    complete = all(
        bool(passed)
        for _, passed
        in checks
    )

    if complete:

        status = "FROZEN_L2_MAPBACK_INTERFACE_CONTRACT_READY"

        diagnosis = "SG7D1_CONSERVATIVE_MAPBACK_INPUTS_AVAILABLE"

        recommendation = (
            "The frozen L2 transport state, SG6 streamline geometry, TOF coordinates, "
            "streamline weights, and 15x50x50 SGSim grid contract are jointly available. "
            "Proceed to SG7D1 conservative streamline-to-grid accumulation. Keep the "
            "R1F3 artifact immutable and do not introduce an unweighted averaging rule."
        )

        next_milestone = (
            "V15-SG7D1 — Conservative Frozen-L2 Streamline-to-Grid Map-Back"
        )

    else:

        status = "FROZEN_L2_MAPBACK_INTERFACE_INCOMPLETE"

        failed = [
            desc
            for desc, passed in checks
            if not passed
        ]

        diagnosis = "ONE_OR_MORE_REQUIRED_MAPBACK_INTERFACES_NOT_RECOVERED"

        recommendation = (
            "Do not perform map-back yet. Recover or serialize the missing SG6 streamline "
            "geometry / TOF / weight interface identified by SG7D0. Do not infer missing "
            "weights or geometry and do not modify the frozen L2 state."
        )

        next_milestone = (
            "V15-SG7D0R — Map-Back Interface Recovery"
        )

    # -------------------------------------------------------------------------
    # Contract
    # -------------------------------------------------------------------------

    contract = {
        "milestone": "V15-SG7D0",
        "status": status,
        "diagnosis": diagnosis,

        "frozen_candidate": {
            "candidate": "L2",
            "file": str(FROZEN_CANDIDATE),
            "sha256": source_sha,
            "streamline_count": nstream,
            "xi_nodes": nxi,
        },

        "streamline_geometry": {
            "xyz_available": xyz_rec is not None,
            "xyz_source":
                str(xyz_rec["file"])
                if xyz_rec is not None
                else None,
            "xyz_key":
                xyz_rec["key"]
                if xyz_rec is not None
                else None,

            "tof_matrix_available": tof_rec is not None,
            "tof_matrix_source":
                str(tof_rec["file"])
                if tof_rec is not None
                else None,
            "tof_matrix_key":
                tof_rec["key"]
                if tof_rec is not None
                else None,

            "weights_available": weight_rec is not None,
            "weights_source":
                str(weight_rec["file"])
                if weight_rec is not None
                else None,
            "weights_key":
                weight_rec["key"]
                if weight_rec is not None
                else None,
        },

        "target_grid": {
            "shape": list(EXPECTED_GRID),
            "array_order": ["k", "j", "i"],
            "cell_dimensions_ft": [
                DX_FT,
                DY_FT,
                DZ_FT,
            ],
        },

        "mapback_performed": False,
        "frozen_candidate_changed": False,
        "streamline_geometry_changed": False,
        "SG7E_threshold_changed": False,

        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(
        CONTRACT_FILE,
        contract,
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7D0",
            "status": status,
            "diagnosis": diagnosis,
            "frozen_candidate": "L2",
            "frozen_candidate_sha256": source_sha,
            "streamline_count": nstream,
            "xi_nodes": nxi,
            "target_grid": list(EXPECTED_GRID),
            "mapback_performed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("FROZEN SG7C SOURCE")
    print(f"  Candidate               : L2")
    print(f"  Streamlines             : {nstream}")
    print(f"  xi nodes                : {nxi}")
    print(f"  State shape             : {l2_state.shape}")
    print(f"  SHA-256                 : {source_sha}")
    print(f"  Hash verified           : {hash_match}")

    print("\nDISCOVERED MAP-BACK INTERFACES")
    print(
        f"  Streamline xyz          : "
        f"{'FOUND' if xyz_rec is not None else 'NOT FOUND'}"
    )
    print(
        f"  TOF matrix              : "
        f"{'FOUND' if tof_rec is not None else 'NOT FOUND'}"
    )
    print(
        f"  Streamline weights      : "
        f"{'FOUND' if weight_rec is not None else 'NOT FOUND'}"
    )
    print(
        f"  Terminal TOF            : "
        f"{'FOUND' if terminal_rec is not None else 'FROZEN tau_end USED'}"
    )

    if xyz_rec is not None:
        print(
            f"  xyz source              : "
            f"{xyz_rec['file'].name} :: {xyz_rec['key']}"
        )

    if tof_rec is not None:
        print(
            f"  TOF source              : "
            f"{tof_rec['file'].name} :: {tof_rec['key']}"
        )

    if weight_rec is not None:
        print(
            f"  weight source           : "
            f"{weight_rec['file'].name} :: {weight_rec['key']}"
        )

    print("\nTARGET GRID")
    print(f"  Shape                   : {EXPECTED_GRID}")
    print(f"  Cells                   : {ncells:,}")
    print(
        f"  Cell size               : "
        f"{DX_FT:.1f} x {DY_FT:.1f} x {DZ_FT:.1f} ft"
    )
    print(
        f"  Physical extent         : "
        f"{nx*DX_FT:.1f} x {ny*DY_FT:.1f} x {nz*DZ_FT:.1f} ft"
    )

    print("\n" + "=" * 78)
    print("V15-SG7D0 INTERFACE VALIDATION")
    print("=" * 78)

    for desc, passed in checks:
        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{desc}"
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
    print(f"  {FROZEN_IDENTITY_TABLE.name}")
    print(f"  {ARRAY_INVENTORY_TABLE.name}")
    print(f"  {GEOMETRY_TABLE.name}")
    print(f"  {GRID_TABLE.name}")
    print(f"  {WEIGHT_TABLE.name}")
    print(f"  {INDEX_TABLE.name}")
    print(f"  {MAPBACK_REQUIREMENTS.name}")
    print(f"  {SOURCE_DISCOVERY_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7D0 MAP-BACK INTERFACE AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen L2 array was changed.")
    print("No streamline geometry was changed.")
    print("No map-back was performed.")
    print("No SG7E threshold was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
