from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib
import shutil
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7D6
# Full-Grid Candidate Freeze / Provenance Manifest
#
# FORMAL SG7D FREEZE MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D1 MAP-BACK ARRAY CHANGED.
# NO SG7D4 FULL-GRID ARRAY CHANGED.
# NO INTERPOLATION.
# NO NEAREST-NEIGHBOR FILL.
# NO SG7E THRESHOLD CHANGED.
#
# PURPOSE
# -------
# SG7D5 established:
#
#   FULL_GRID_CANDIDATE_FREEZE_READY
#
# and:
#
#   P4_FULL_GRID_INDEPENDENT_VALIDATION_PASSES_COMPLETE_CONTRACT
#
# SG7D6 formally freezes the validated 15x50x50 full-grid candidate by:
#
#   1. verifying SG7D5 freeze-readiness,
#   2. verifying all SG7D5 independent gates pass,
#   3. verifying the SG7D4 full-grid artifact identity,
#   4. verifying SG7D1 conservative map-back provenance,
#   5. verifying R1F3 frozen L2 provenance,
#   6. copying the validated SG7D4 artifact byte-for-byte,
#   7. verifying source/frozen SHA-256 identity,
#   8. recording the complete SG7C -> SG7D provenance chain,
#   9. writing the frozen SG7D deployment contract for SG7E.
#
# SG7D6 does not modify or regenerate the numerical field.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7D6"
OUT.mkdir(parents=True, exist_ok=True)

FROZEN_DIR = OUT / "frozen_full_grid"
FROZEN_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

SG7D5_DIR = ROOT / "output" / "V15_SG7D5"
SG7D4_DIR = ROOT / "output" / "V15_SG7D4"
SG7D1_DIR = ROOT / "output" / "V15_SG7D1"

SG7D5_SUMMARY = SG7D5_DIR / "PAD_Stream_V15SG7D5_Summary.json"
SG7D5_READINESS = SG7D5_DIR / "V15SG7D5_Freeze_Readiness_Manifest.json"
SG7D5_CONTRACT = SG7D5_DIR / "V15SG7D5_Independent_Full_Grid_Validation_Contract.json"
SG7D5_GATES = SG7D5_DIR / "V15SG7D5_Final_Gate_Matrix.csv"

SG7D4_NUMERICAL = SG7D4_DIR / "V15SG7D4_Completed_Full_Grid.npz"
SG7D4_CONTRACT = SG7D4_DIR / "V15SG7D4_Background_Completion_Contract.json"
SG7D4_MANIFEST = SG7D4_DIR / "V15SG7D4_Full_Grid_Candidate_Manifest.json"

SG7D1_NUMERICAL = SG7D1_DIR / "V15SG7D1_Conservative_MapBack.npz"
SG7D1_CONTRACT = SG7D1_DIR / "V15SG7D1_Conservative_MapBack_Contract.json"

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3"
    / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

R1F3_FREEZE_MANIFEST = (
    ROOT / "output" / "V15_SG7CR3F5R1F3"
    / "V15SG7CR3F5R1F3_Freeze_Manifest.json"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7D6_Summary.json"

HASH_TABLE = OUT / "V15SG7D6_Artifact_Hashes.csv"
PROVENANCE_TABLE = OUT / "V15SG7D6_Provenance_Chain.csv"
GATE_TABLE = OUT / "V15SG7D6_Frozen_Gate_Record.csv"
IDENTITY_TABLE = OUT / "V15SG7D6_Frozen_Full_Grid_Identity.csv"

FREEZE_MANIFEST = OUT / "V15SG7D6_Full_Grid_Freeze_Manifest.json"
DEPLOYMENT_CONTRACT = OUT / "V15SG7D6_Frozen_Grid_Deployment_Contract.json"

FROZEN_GRID = (
    FROZEN_DIR
    / "V15SG7D6_P4_Frozen_Full_Grid_Deployment_Candidate.npz"
)

EXPECTED_SHAPE = (15, 50, 50)

# =============================================================================
# Helpers
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


def sha256(path: Path, chunk_size=1024 * 1024):
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)

    return h.hexdigest()


def bool_from_csv(value):
    return str(value).strip().lower() in {
        "true", "1", "yes", "pass"
    }


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7D6")
    print("Full-Grid Candidate Freeze / Provenance Manifest")
    print("=" * 78)

    print("""
FORMAL SG7D FULL-GRID FREEZE WILL BE PERFORMED.
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D1 MAP-BACK ARRAY WILL BE CHANGED.
NO SG7D4 FULL-GRID ARRAY WILL BE CHANGED.
NO INTERPOLATION OR NEAREST-NEIGHBOR FILL WILL BE USED.
NO SG7E THRESHOLD WILL BE CHANGED.
THE FREEZE WILL COPY AND HASH THE ALREADY VALIDATED SG7D4 CANDIDATE ONLY.
""")

    # -------------------------------------------------------------------------
    # Load contracts / manifests
    # -------------------------------------------------------------------------

    d5_summary = load_json(SG7D5_SUMMARY)
    d5_ready = load_json(SG7D5_READINESS)
    d5_contract = load_json(SG7D5_CONTRACT)

    d4_contract = load_json(SG7D4_CONTRACT)
    d4_manifest = load_json(SG7D4_MANIFEST)

    d1_contract = load_json(SG7D1_CONTRACT)
    r1f3_manifest = load_json(R1F3_FREEZE_MANIFEST)

    d5_gate_rows = load_csv(SG7D5_GATES)

    # -------------------------------------------------------------------------
    # Freeze-entry validation
    # -------------------------------------------------------------------------

    checks = []

    checks.append((
        "SG7D5 freeze-ready status reproduced",
        d5_summary.get("status") == "FULL_GRID_CANDIDATE_FREEZE_READY",
    ))

    checks.append((
        "SG7D5 diagnosis reproduced",
        d5_summary.get("diagnosis")
        == "P4_FULL_GRID_INDEPENDENT_VALIDATION_PASSES_COMPLETE_CONTRACT",
    ))

    checks.append((
        "SG7D5 freeze-ready flag = true",
        bool(d5_ready.get("freeze_ready", False)),
    ))

    checks.append((
        "Candidate identity = P4_full_grid",
        d5_ready.get("candidate") == "P4_full_grid",
    ))

    checks.append((
        "Candidate not previously frozen",
        not bool(d5_ready.get("candidate_frozen", False)),
    ))

    checks.append((
        "SG7D4 policy identity preserved",
        d4_contract.get("policy") == "P4_MASKED_BACKGROUND_PLUS_SUPPORT",
    ))

    checks.append((
        "R1F3 L2 remains formally frozen",
        r1f3_manifest.get("status") == "SG7C_CROSSING_LOCAL_CANDIDATE_FROZEN",
    ))

    authoritative_gate_failures = []

    for row in d5_gate_rows:
        if not bool_from_csv(row.get("passed")):
            authoritative_gate_failures.append(row.get("gate"))

    checks.append((
        "Every SG7D5 independent gate passes",
        len(authoritative_gate_failures) == 0,
    ))

    # -------------------------------------------------------------------------
    # Artifact identity checks
    # -------------------------------------------------------------------------

    required_paths = [
        SG7D4_NUMERICAL,
        SG7D1_NUMERICAL,
        R1F3_FROZEN,
    ]

    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(f"Missing prerequisite:\n{path}")

    d4_sha = sha256(SG7D4_NUMERICAL)
    d1_sha = sha256(SG7D1_NUMERICAL)
    l2_sha = sha256(R1F3_FROZEN)

    checks.append((
        "SG7D4 candidate SHA-256 reproduced",
        d4_sha == d5_ready["full_grid_sha256"],
    ))

    checks.append((
        "SG7D1 SHA-256 reproduced",
        d1_sha == d5_ready["SG7D1_sha256"],
    ))

    checks.append((
        "Frozen L2 SHA-256 reproduced",
        l2_sha == d5_ready["frozen_L2_sha256"],
    ))

    # -------------------------------------------------------------------------
    # Numerical candidate validation before copy
    # -------------------------------------------------------------------------

    d4 = np.load(SG7D4_NUMERICAL, allow_pickle=True)

    required_arrays = [
        "saturation_grid_full",
        "saturation_grid_supported_only",
        "supported_mask",
        "support_denominator",
        "support_numerator",
        "segment_piece_count",
        "streamline_visit_count",
        "background_saturation",
    ]

    missing = [
        key
        for key in required_arrays
        if key not in d4.files
    ]

    checks.append((
        "SG7D4 freeze package contains complete arrays",
        len(missing) == 0,
    ))

    if missing:
        raise RuntimeError(
            "Cannot freeze incomplete SG7D4 candidate arrays: "
            + ", ".join(missing)
        )

    full_grid = np.asarray(
        d4["saturation_grid_full"],
        dtype=np.float64,
    )

    supported_mask = np.asarray(
        d4["supported_mask"],
        dtype=np.uint8,
    ).astype(bool)

    support_denominator = np.asarray(
        d4["support_denominator"],
        dtype=np.float64,
    )

    support_numerator = np.asarray(
        d4["support_numerator"],
        dtype=np.float64,
    )

    background = float(
        np.asarray(
            d4["background_saturation"]
        )
    )

    checks.append((
        "Full-grid shape = 15x50x50",
        full_grid.shape == EXPECTED_SHAPE,
    ))

    checks.append((
        "Full-grid field finite",
        np.all(np.isfinite(full_grid)),
    ))

    checks.append((
        "Support mask shape preserved",
        supported_mask.shape == EXPECTED_SHAPE,
    ))

    checks.append((
        "Conservative denominator shape preserved",
        support_denominator.shape == EXPECTED_SHAPE,
    ))

    checks.append((
        "Conservative numerator shape preserved",
        support_numerator.shape == EXPECTED_SHAPE,
    ))

    # -------------------------------------------------------------------------
    # Byte-for-byte freeze copy
    # -------------------------------------------------------------------------

    source_sha = d4_sha

    shutil.copy2(
        SG7D4_NUMERICAL,
        FROZEN_GRID,
    )

    frozen_sha = sha256(FROZEN_GRID)

    checks.append((
        "Frozen full-grid SHA-256 matches validated source",
        frozen_sha == source_sha,
    ))

    complete = all(bool(passed) for _, passed in checks)

    # -------------------------------------------------------------------------
    # Hash provenance
    # -------------------------------------------------------------------------

    provenance_artifacts = [
        ("SG7D5 summary", SG7D5_SUMMARY),
        ("SG7D5 freeze readiness", SG7D5_READINESS),
        ("SG7D5 independent contract", SG7D5_CONTRACT),
        ("SG7D5 final gates", SG7D5_GATES),
        ("SG7D4 full-grid candidate", SG7D4_NUMERICAL),
        ("SG7D4 completion contract", SG7D4_CONTRACT),
        ("SG7D4 candidate manifest", SG7D4_MANIFEST),
        ("SG7D1 conservative map-back", SG7D1_NUMERICAL),
        ("SG7D1 map-back contract", SG7D1_CONTRACT),
        ("R1F3 frozen L2", R1F3_FROZEN),
        ("R1F3 freeze manifest", R1F3_FREEZE_MANIFEST),
        ("SG7D6 frozen full-grid candidate", FROZEN_GRID),
    ]

    hash_rows = []

    for role, path in provenance_artifacts:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing provenance artifact:\n{path}"
            )

        hash_rows.append({
            "role": role,
            "path": str(path),
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        })

    save_csv(HASH_TABLE, hash_rows)

    # -------------------------------------------------------------------------
    # Frozen gate record
    # -------------------------------------------------------------------------

    frozen_gate_rows = []

    for row in d5_gate_rows:
        frozen_gate_rows.append({
            "candidate": "P4_full_grid",
            "gate": row.get("gate"),
            "passed": row.get("passed"),
            "source_milestone": "V15-SG7D5",
            "frozen_by": "V15-SG7D6",
        })

    save_csv(GATE_TABLE, frozen_gate_rows)

    # -------------------------------------------------------------------------
    # Identity record
    # -------------------------------------------------------------------------

    supported_cells = int(np.sum(supported_mask))
    unsupported_cells = int(np.size(supported_mask) - supported_cells)

    identity_rows = [{
        "candidate": "P4_full_grid",
        "freeze_milestone": "V15-SG7D6",
        "source_validation_milestone": "V15-SG7D5",
        "frozen_file": str(FROZEN_GRID),
        "frozen_sha256": frozen_sha,
        "grid_shape": "15x50x50",
        "supported_cells": supported_cells,
        "unsupported_cells": unsupported_cells,
        "background_saturation": background,
        "grid_min": float(np.min(full_grid)),
        "grid_max": float(np.max(full_grid)),
        "support_mask_preserved": True,
        "conservative_denominator_preserved": True,
        "conservative_numerator_preserved": True,
        "SG7D1_sha256": d1_sha,
        "frozen_L2_sha256": l2_sha,
    }]

    save_csv(IDENTITY_TABLE, identity_rows)

    # -------------------------------------------------------------------------
    # Provenance chain
    # -------------------------------------------------------------------------

    provenance_rows = [
        {
            "order": 1,
            "milestone": "V15-SG7C-R3F5-R1F3",
            "role": "Frozen streamline-space transport",
            "decision": "L2 frozen as authoritative SG7C deployment candidate",
        },
        {
            "order": 2,
            "milestone": "V15-SG7D0",
            "role": "Map-back interface contract",
            "decision": "Frozen L2, xyz, TOF, weights, and 15x50x50 grid interface validated",
        },
        {
            "order": 3,
            "milestone": "V15-SG7D1",
            "role": "Conservative streamline-to-grid map-back",
            "decision": "Flow-weighted segment/cell deposition closes at machine precision",
        },
        {
            "order": 4,
            "milestone": "V15-SG7D2",
            "role": "Independent map-back audit",
            "decision": "29,107 supported cells validated; 8,393 unsupported cells retained",
        },
        {
            "order": 5,
            "milestone": "V15-SG7D3",
            "role": "Unsupported-cell policy design",
            "decision": "P4 masked background-plus-support selected",
        },
        {
            "order": 6,
            "milestone": "V15-SG7D4",
            "role": "Controlled full-grid completion",
            "decision": "Unsupported cells assigned frozen background; no supported cell changed",
        },
        {
            "order": 7,
            "milestone": "V15-SG7D5",
            "role": "Independent full-grid validation",
            "decision": "P4 full-grid candidate passes complete contract",
        },
        {
            "order": 8,
            "milestone": "V15-SG7D6",
            "role": "Formal SG7D freeze",
            "decision": "P4 full-grid candidate frozen for SG7E deployment validation",
        },
    ]

    save_csv(PROVENANCE_TABLE, provenance_rows)

    # -------------------------------------------------------------------------
    # Final decision
    # -------------------------------------------------------------------------

    if complete:

        status = "SG7D_FULL_GRID_CANDIDATE_FROZEN"

        diagnosis = "P4_FULL_GRID_FROZEN_AS_AUTHORITATIVE_SG7E_INPUT"

        recommendation = (
            "The validated 15x50x50 P4 full-grid saturation field is now formally frozen "
            "with byte-for-byte SHA-256 provenance. Treat the SG7D6 frozen artifact, support "
            "mask, conservative map-back evidence, and frozen background rule as immutable. "
            "Proceed to SG7E deployment validation without modifying the grid, support mask, "
            "background completion, frozen L2 transport, or SG7E thresholds."
        )

        next_milestone = (
            "V15-SG7E0 — Frozen Full-Grid Deployment Validation Contract / Baseline Audit"
        )

    else:

        status = "SG7D_FULL_GRID_FREEZE_BLOCKED"

        diagnosis = "FULL_GRID_FREEZE_PROVENANCE_VALIDATION_FAILED"

        recommendation = (
            "Do not freeze or deploy the SG7D4 field. Repair only the failed provenance or "
            "freeze-entry checks; do not alter the numerical field or any acceptance gate."
        )

        next_milestone = (
            "V15-SG7D6R — Full-Grid Freeze Provenance Repair"
        )

    # -------------------------------------------------------------------------
    # Freeze manifest
    # -------------------------------------------------------------------------

    save_json(
        FREEZE_MANIFEST,
        {
            "milestone": "V15-SG7D6",
            "status": status,
            "diagnosis": diagnosis,
            "candidate": "P4_full_grid",
            "candidate_frozen": complete,
            "frozen_full_grid_file": str(FROZEN_GRID),
            "frozen_full_grid_sha256": frozen_sha,
            "source_full_grid_sha256": source_sha,
            "SG7D1_sha256": d1_sha,
            "frozen_L2_sha256": l2_sha,
            "grid_shape": list(EXPECTED_SHAPE),
            "supported_cells": supported_cells,
            "unsupported_cells": unsupported_cells,
            "background_saturation": background,
            "all_SG7D5_gates_pass":
                len(authoritative_gate_failures) == 0,
            "gate_failures": authoritative_gate_failures,
            "numerical_field_changed": False,
            "support_mask_changed": False,
            "conservative_evidence_changed": False,
            "SG7E_threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Deployment contract
    # -------------------------------------------------------------------------

    save_json(
        DEPLOYMENT_CONTRACT,
        {
            "contract_name":
                "PAD-Stream V15-SG7D Frozen Full-Grid Deployment Contract",

            "freeze_milestone":
                "V15-SG7D6",

            "candidate":
                "P4_full_grid",

            "status":
                status,

            "authoritative_artifact":
                str(FROZEN_GRID),

            "authoritative_sha256":
                frozen_sha,

            "grid_shape":
                list(EXPECTED_SHAPE),

            "transport_source":
                "R1F3 frozen L2",

            "mapback_source":
                "SG7D1 conservative segment-weighted map-back",

            "unsupported_cell_policy":
                "P4_MASKED_BACKGROUND_PLUS_SUPPORT",

            "background_saturation":
                background,

            "support_provenance":
                {
                    "supported_cells": supported_cells,
                    "unsupported_cells": unsupported_cells,
                    "support_mask_preserved": True,
                    "support_denominator_preserved": True,
                    "support_numerator_preserved": True,
                },

            "invariants":
                {
                    "frozen_L2_immutable": True,
                    "SG7D1_supported_cells_immutable": True,
                    "support_mask_immutable": True,
                    "support_denominator_immutable": True,
                    "support_numerator_immutable": True,
                    "background_completion_rule_immutable": True,
                    "interpolation_prohibited": True,
                    "nearest_neighbor_prohibited": True,
                    "SG7E_thresholds_immutable": True,
                },

            "downstream_use":
                "Authoritative full-grid saturation input for SG7E deployment validation.",

            "next_milestone":
                next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7D6",
            "status": status,
            "diagnosis": diagnosis,
            "candidate": "P4_full_grid",
            "candidate_frozen": complete,
            "frozen_full_grid_sha256": frozen_sha,
            "grid_shape": list(EXPECTED_SHAPE),
            "supported_cells": supported_cells,
            "unsupported_cells": unsupported_cells,
            "background_saturation": background,
            "numerical_field_changed": False,
            "SG7E_threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("V15-SG7D6 FREEZE VALIDATION")
    print("=" * 78)

    for desc, passed in checks:
        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{desc}"
        )

    print("=" * 78)

    print("\nFROZEN FULL-GRID CANDIDATE")
    print("  Candidate               : P4_full_grid")
    print(f"  Grid shape              : {EXPECTED_SHAPE}")
    print(f"  Supported cells         : {supported_cells:,}")
    print(f"  Unsupported cells       : {unsupported_cells:,}")
    print(f"  Background saturation   : {background:.6f}")
    print(f"  Frozen artifact         : {FROZEN_GRID.name}")
    print(f"  SHA-256                 : {frozen_sha}")
    print(
        f"  Source/frozen hash match: "
        f"{source_sha == frozen_sha}"
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

    print("\nFrozen candidate:")
    print(f"  {FROZEN_GRID}")

    print("\nTables:")
    print(f"  {HASH_TABLE.name}")
    print(f"  {PROVENANCE_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print(f"  {IDENTITY_TABLE.name}")

    print("\nFreeze manifest:")
    print(f"  {FREEZE_MANIFEST.name}")

    print("\nFrozen deployment contract:")
    print(f"  {DEPLOYMENT_CONTRACT.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)

    if complete:
        print("V15-SG7D6 FORMAL FULL-GRID FREEZE: PASS")
        print()
        print("P4_full_grid is now frozen as the authoritative SG7D deployment field.")
        print("No training was performed.")
        print("No numerical field was changed.")
        print("No support provenance was changed.")
        print("No SG7E threshold was changed.")
        print()
        print("Next milestone:")
        print(next_milestone)
    else:
        print("V15-SG7D6 FORMAL FULL-GRID FREEZE: BLOCKED")
        print()
        print("No candidate was frozen.")
        print("No numerical field was changed.")
        print("No SG7E threshold was changed.")
        print()
        print("Next milestone:")
        print(next_milestone)

    print("=" * 78)


if __name__ == "__main__":
    main()
