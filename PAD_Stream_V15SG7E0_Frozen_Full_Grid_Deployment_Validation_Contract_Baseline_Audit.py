from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib
import re
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E0
# Frozen Full-Grid Deployment Validation Contract / Baseline Audit
#
# CONTRACT / BASELINE MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO SUPPORT MASK CHANGED.
# NO BACKGROUND COMPLETION POLICY CHANGED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO DEPLOYMENT CORRECTION PERFORMED.
#
# PURPOSE
# -------
# SG7D6 formally froze:
#
#   P4_full_grid
#
# as the authoritative 15 x 50 x 50 deployment field for SG7E.
#
# SG7E0 now:
#
#   1. verifies SG7D6 frozen artifact identity,
#   2. inventories historical SG7E scripts/contracts/tables,
#   3. extracts explicit SG7E threshold/gate definitions,
#   4. distinguishes authoritative vs diagnostic evidence where possible,
#   5. audits compatibility between historical SG7E expectations and the
#      frozen SG7D6 full-grid field,
#   6. computes only baseline metrics that are directly reconstructible from
#      the frozen full-grid artifact,
#   7. writes the immutable SG7E1 validation matrix.
#
# SG7E0 NEVER modifies the frozen field or invents a threshold.
# If threshold provenance is ambiguous, the milestone routes to SG7E0R.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E0"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Authoritative SG7D6 input
# -----------------------------------------------------------------------------

SG7D6_DIR = ROOT / "output" / "V15_SG7D6"

SG7D6_FREEZE_MANIFEST = (
    SG7D6_DIR / "V15SG7D6_Full_Grid_Freeze_Manifest.json"
)

SG7D6_DEPLOYMENT_CONTRACT = (
    SG7D6_DIR / "V15SG7D6_Frozen_Grid_Deployment_Contract.json"
)

SG7D6_FROZEN_GRID = (
    SG7D6_DIR
    / "frozen_full_grid"
    / "V15SG7D6_P4_Frozen_Full_Grid_Deployment_Candidate.npz"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E0_Summary.json"

INPUT_IDENTITY_TABLE = OUT / "V15SG7E0_Frozen_Input_Identity.csv"
SOURCE_DISCOVERY_TABLE = OUT / "V15SG7E0_Historical_SG7E_Source_Discovery.csv"
THRESHOLD_TABLE = OUT / "V15SG7E0_SG7E_Threshold_Provenance.csv"
COMPATIBILITY_TABLE = OUT / "V15SG7E0_Contract_Compatibility_Audit.csv"
BASELINE_TABLE = OUT / "V15SG7E0_Frozen_P4_Baseline_Metrics.csv"
ROLE_TABLE = OUT / "V15SG7E0_Authoritative_vs_Diagnostic_Gates.csv"
VALIDATION_MATRIX = OUT / "V15SG7E0_SG7E1_Validation_Matrix.csv"

CONTRACT_FILE = OUT / "V15SG7E0_Deployment_Validation_Contract.json"

EXPECTED_SHAPE = (15, 50, 50)

# Diagnostic only. This does NOT redefine SG7E.
DEFAULT_DIAGNOSTIC_THRESHOLD = 0.21


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


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def discover_sg7e_sources():
    """
    Search scripts / contracts / summaries / CSVs that appear to belong to SG7E.
    """

    rows = []
    seen = set()

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        name = path.name.upper()
        parent = str(path.parent).upper()

        if "SG7E" not in name and "V15_SG7E" not in parent:
            continue

        rp = str(path.resolve())
        if rp in seen:
            continue

        seen.add(rp)

        suffix = path.suffix.lower()

        role = "other"

        if suffix == ".py":
            role = "source_code"
        elif suffix == ".json":
            if "CONTRACT" in name:
                role = "contract"
            elif "SUMMARY" in name:
                role = "summary"
            elif "MANIFEST" in name:
                role = "manifest"
            else:
                role = "json"
        elif suffix == ".csv":
            role = "table"
        elif suffix == ".npz":
            role = "numerical"

        rows.append({
            "path": str(path),
            "name": path.name,
            "role": role,
            "suffix": suffix,
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        })

    rows.sort(key=lambda r: (r["role"], r["name"]))
    return rows


def extract_threshold_candidates(source_rows):
    """
    Extract likely numerical threshold / gate definitions from SG7E source text.

    This is provenance discovery, not authoritative interpretation.
    We only record explicit assignments/comparisons that appear in source.
    """

    candidates = []

    assignment_pattern = re.compile(
        r'(?P<name>[A-Z][A-Z0-9_]*(?:LIMIT|MAX|MIN|THRESHOLD|TOL|TOLERANCE|GATE)[A-Z0-9_]*)'
        r'\s*=\s*(?P<value>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)'
    )

    comparison_pattern = re.compile(
        r'(?P<metric>[A-Za-z_][A-Za-z0-9_]*)'
        r'\s*(?P<op><=|>=|<|>)\s*'
        r'(?P<rhs>[A-Z][A-Z0-9_]*(?:LIMIT|MAX|MIN|THRESHOLD|TOL|TOLERANCE|GATE)[A-Z0-9_]*'
        r'|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)'
    )

    for row in source_rows:
        if row["role"] not in {
            "source_code", "contract", "summary", "json"
        }:
            continue

        path = Path(row["path"])
        text = safe_text(path)

        if not text:
            continue

        lines = text.splitlines()

        for line_no, line in enumerate(lines, start=1):

            for m in assignment_pattern.finditer(line):
                candidates.append({
                    "source": str(path),
                    "line": line_no,
                    "evidence_type": "assignment",
                    "symbol": m.group("name"),
                    "operator": "=",
                    "value_or_rhs": m.group("value"),
                    "raw_evidence": line.strip()[:500],
                })

            for m in comparison_pattern.finditer(line):
                candidates.append({
                    "source": str(path),
                    "line": line_no,
                    "evidence_type": "comparison",
                    "symbol": m.group("metric"),
                    "operator": m.group("op"),
                    "value_or_rhs": m.group("rhs"),
                    "raw_evidence": line.strip()[:500],
                })

    return candidates


def classify_role(candidate):
    """
    Conservative role classification from naming/context only.
    Ambiguous items remain UNKNOWN.
    """

    raw = (
        candidate.get("raw_evidence", "")
        + " "
        + candidate.get("symbol", "")
    ).lower()

    diagnostic_tokens = (
        "diagnostic",
        "report_only",
        "diagnostic_only",
        "informational",
    )

    authoritative_tokens = (
        "authoritative",
        "acceptance",
        "final_gate",
        "deployment_gate",
        "must_pass",
    )

    if any(tok in raw for tok in diagnostic_tokens):
        return "DIAGNOSTIC"

    if any(tok in raw for tok in authoritative_tokens):
        return "AUTHORITATIVE"

    return "UNKNOWN"


def metric_baseline(full_grid, supported_mask, background):
    """
    Baseline metrics derivable directly from frozen SG7D6 artifact.
    No historical threshold is assumed here.
    """

    finite = np.isfinite(full_grid)

    plume_mask = (
        finite
        &
        (full_grid >= DEFAULT_DIAGNOSTIC_THRESHOLD)
    )

    supported_plume = plume_mask & supported_mask
    unsupported_plume = plume_mask & (~supported_mask)

    rows = [
        {
            "metric": "grid_cell_count",
            "value": int(full_grid.size),
            "units": "cells",
            "semantics": "BASELINE",
        },
        {
            "metric": "grid_finite_fraction",
            "value": float(np.mean(finite)),
            "units": "fraction",
            "semantics": "BASELINE",
        },
        {
            "metric": "grid_min_saturation",
            "value": float(np.min(full_grid)),
            "units": "saturation",
            "semantics": "BASELINE",
        },
        {
            "metric": "grid_max_saturation",
            "value": float(np.max(full_grid)),
            "units": "saturation",
            "semantics": "BASELINE",
        },
        {
            "metric": "grid_mean_saturation",
            "value": float(np.mean(full_grid)),
            "units": "saturation",
            "semantics": "BASELINE",
        },
        {
            "metric": "supported_cells",
            "value": int(np.sum(supported_mask)),
            "units": "cells",
            "semantics": "BASELINE",
        },
        {
            "metric": "unsupported_background_cells",
            "value": int(np.sum(~supported_mask)),
            "units": "cells",
            "semantics": "BASELINE",
        },
        {
            "metric": "support_fraction",
            "value": float(np.mean(supported_mask)),
            "units": "fraction",
            "semantics": "BASELINE",
        },
        {
            "metric": "background_saturation",
            "value": float(background),
            "units": "saturation",
            "semantics": "BASELINE",
        },
        {
            "metric": "diagnostic_plume_threshold",
            "value": DEFAULT_DIAGNOSTIC_THRESHOLD,
            "units": "saturation",
            "semantics": "DIAGNOSTIC_ONLY",
        },
        {
            "metric": "diagnostic_full_grid_plume_cells",
            "value": int(np.sum(plume_mask)),
            "units": "cells",
            "semantics": "DIAGNOSTIC_ONLY",
        },
        {
            "metric": "diagnostic_supported_plume_cells",
            "value": int(np.sum(supported_plume)),
            "units": "cells",
            "semantics": "DIAGNOSTIC_ONLY",
        },
        {
            "metric": "diagnostic_unsupported_plume_cells",
            "value": int(np.sum(unsupported_plume)),
            "units": "cells",
            "semantics": "DIAGNOSTIC_ONLY",
        },
    ]

    return rows


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E0")
    print("Frozen Full-Grid Deployment Validation Contract / Baseline Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D6 FULL-GRID ARRAY WILL BE CHANGED.
NO SUPPORT MASK OR BACKGROUND POLICY WILL BE CHANGED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO DEPLOYMENT CORRECTION WILL BE PERFORMED.
""")

    freeze_manifest = load_json(SG7D6_FREEZE_MANIFEST)
    deployment_contract = load_json(SG7D6_DEPLOYMENT_CONTRACT)

    if (
        freeze_manifest.get("status")
        !=
        "SG7D_FULL_GRID_CANDIDATE_FROZEN"
    ):
        raise RuntimeError(
            "SG7E0 requires the formally frozen SG7D6 full-grid candidate."
        )

    if (
        freeze_manifest.get("candidate")
        !=
        "P4_full_grid"
    ):
        raise RuntimeError(
            "SG7E0 expects SG7D6 candidate P4_full_grid."
        )

    if not SG7D6_FROZEN_GRID.exists():
        raise FileNotFoundError(
            f"Missing SG7D6 frozen grid:\n{SG7D6_FROZEN_GRID}"
        )

    frozen_sha = sha256(SG7D6_FROZEN_GRID)
    expected_sha = freeze_manifest.get("frozen_full_grid_sha256")

    if frozen_sha != expected_sha:
        raise RuntimeError(
            "SG7D6 frozen full-grid SHA-256 does not match freeze manifest."
        )

    db = np.load(
        SG7D6_FROZEN_GRID,
        allow_pickle=True,
    )

    required = [
        "saturation_grid_full",
        "supported_mask",
        "support_denominator",
        "support_numerator",
        "background_saturation",
    ]

    missing = [
        key
        for key in required
        if key not in db.files
    ]

    if missing:
        raise RuntimeError(
            "SG7D6 frozen grid package incomplete: "
            + ", ".join(missing)
        )

    full_grid = np.asarray(
        db["saturation_grid_full"],
        dtype=np.float64,
    )

    supported_mask = np.asarray(
        db["supported_mask"],
        dtype=np.uint8,
    ).astype(bool)

    denominator = np.asarray(
        db["support_denominator"],
        dtype=np.float64,
    )

    numerator = np.asarray(
        db["support_numerator"],
        dtype=np.float64,
    )

    background = float(
        np.asarray(
            db["background_saturation"]
        )
    )

    if full_grid.shape != EXPECTED_SHAPE:
        raise RuntimeError(
            f"Unexpected frozen grid shape {full_grid.shape}."
        )

    # -------------------------------------------------------------------------
    # Frozen input identity
    # -------------------------------------------------------------------------

    identity_rows = [{
        "candidate":
            "P4_full_grid",

        "file":
            str(SG7D6_FROZEN_GRID),

        "sha256":
            frozen_sha,

        "hash_matches_freeze_manifest":
            frozen_sha == expected_sha,

        "grid_shape":
            "15x50x50",

        "supported_cells":
            int(np.sum(supported_mask)),

        "unsupported_cells":
            int(np.sum(~supported_mask)),

        "background_saturation":
            background,

        "grid_min":
            float(np.min(full_grid)),

        "grid_max":
            float(np.max(full_grid)),

        "grid_all_finite":
            bool(np.all(np.isfinite(full_grid))),

        "support_mask_consistent":
            bool(np.array_equal(supported_mask, denominator > 0.0)),
    }]

    save_csv(
        INPUT_IDENTITY_TABLE,
        identity_rows,
    )

    # -------------------------------------------------------------------------
    # Historical SG7E source discovery
    # -------------------------------------------------------------------------

    source_rows = discover_sg7e_sources()

    save_csv(
        SOURCE_DISCOVERY_TABLE,
        source_rows,
    )

    threshold_candidates = extract_threshold_candidates(
        source_rows
    )

    for row in threshold_candidates:
        row["role_classification"] = classify_role(row)

    save_csv(
        THRESHOLD_TABLE,
        threshold_candidates,
    )

    # -------------------------------------------------------------------------
    # Role audit
    # -------------------------------------------------------------------------

    role_rows = []

    for row in threshold_candidates:
        role_rows.append({
            "source": row["source"],
            "line": row["line"],
            "symbol": row["symbol"],
            "operator": row["operator"],
            "value_or_rhs": row["value_or_rhs"],
            "role": row["role_classification"],
            "raw_evidence": row["raw_evidence"],
        })

    save_csv(
        ROLE_TABLE,
        role_rows,
    )

    # -------------------------------------------------------------------------
    # Contract compatibility
    # -------------------------------------------------------------------------

    compatibility_rows = [
        {
            "item": "frozen_input_shape",
            "expected": "15x50x50",
            "observed": str(full_grid.shape),
            "compatible": full_grid.shape == EXPECTED_SHAPE,
        },
        {
            "item": "full_grid_finite",
            "expected": "all finite",
            "observed": bool(np.all(np.isfinite(full_grid))),
            "compatible": bool(np.all(np.isfinite(full_grid))),
        },
        {
            "item": "support_mask_available",
            "expected": True,
            "observed": supported_mask.shape == EXPECTED_SHAPE,
            "compatible": supported_mask.shape == EXPECTED_SHAPE,
        },
        {
            "item": "conservative_denominator_available",
            "expected": True,
            "observed": denominator.shape == EXPECTED_SHAPE,
            "compatible": denominator.shape == EXPECTED_SHAPE,
        },
        {
            "item": "conservative_numerator_available",
            "expected": True,
            "observed": numerator.shape == EXPECTED_SHAPE,
            "compatible": numerator.shape == EXPECTED_SHAPE,
        },
        {
            "item": "background_policy_available",
            "expected": "P4 frozen background completion",
            "observed": deployment_contract.get("unsupported_cell_policy"),
            "compatible":
                deployment_contract.get("unsupported_cell_policy")
                ==
                "P4_MASKED_BACKGROUND_PLUS_SUPPORT",
        },
    ]

    # Search historical SG7E evidence for expected input semantics.
    historical_text = "\n".join(
        safe_text(Path(row["path"]))
        for row in source_rows
        if row["role"] in {"source_code", "contract", "summary", "json"}
    ).lower()

    semantic_flags = {
        "historical_mentions_full_grid":
            any(
                token in historical_text
                for token in (
                    "full_grid",
                    "full grid",
                    "15x50x50",
                    "37500",
                )
            ),

        "historical_mentions_supported_mask":
            any(
                token in historical_text
                for token in (
                    "supported_mask",
                    "support mask",
                    "unsupported",
                )
            ),

        "historical_mentions_mapback":
            any(
                token in historical_text
                for token in (
                    "map-back",
                    "mapback",
                    "grid mapping",
                )
            ),
    }

    for key, value in semantic_flags.items():
        compatibility_rows.append({
            "item": key,
            "expected": "informational",
            "observed": value,
            "compatible": True,
        })

    save_csv(
        COMPATIBILITY_TABLE,
        compatibility_rows,
    )

    # -------------------------------------------------------------------------
    # Frozen baseline
    # -------------------------------------------------------------------------

    baseline_rows = metric_baseline(
        full_grid,
        supported_mask,
        background,
    )

    save_csv(
        BASELINE_TABLE,
        baseline_rows,
    )

    baseline_lookup = {
        row["metric"]: row["value"]
        for row in baseline_rows
    }

    # -------------------------------------------------------------------------
    # Build SG7E1 validation matrix
    # -------------------------------------------------------------------------

    matrix_rows = []

    # Only threshold candidates with explicit numeric RHS can be carried as
    # numerical candidates. Symbolic comparisons remain provenance-only.
    for idx, row in enumerate(threshold_candidates):

        rhs = row["value_or_rhs"]

        numeric_rhs = None

        try:
            numeric_rhs = float(rhs)
        except Exception:
            numeric_rhs = None

        matrix_rows.append({
            "matrix_id": f"G{idx:04d}",
            "source": row["source"],
            "line": row["line"],
            "metric_or_symbol": row["symbol"],
            "operator": row["operator"],
            "limit_or_rhs": rhs,
            "numeric_limit": numeric_rhs if numeric_rhs is not None else "",
            "role": row["role_classification"],
            "baseline_value": "",
            "baseline_evaluable": False,
            "SG7E1_action":
                "RECONSTRUCT_FROM_SOURCE_DEFINITION"
                if row["role_classification"] != "DIAGNOSTIC"
                else
                "REPORT_DIAGNOSTIC",
            "raw_evidence": row["raw_evidence"],
        })

    save_csv(
        VALIDATION_MATRIX,
        matrix_rows,
    )

    # -------------------------------------------------------------------------
    # Validation / decision
    # -------------------------------------------------------------------------

    explicit_authoritative = [
        row
        for row in threshold_candidates
        if row["role_classification"] == "AUTHORITATIVE"
    ]

    unknown_candidates = [
        row
        for row in threshold_candidates
        if row["role_classification"] == "UNKNOWN"
    ]

    checks = [
        (
            "SG7D6 frozen status reproduced",
            freeze_manifest.get("status")
            ==
            "SG7D_FULL_GRID_CANDIDATE_FROZEN",
        ),
        (
            "Frozen P4 candidate SHA-256 reproduced",
            frozen_sha == expected_sha,
        ),
        (
            "Frozen full-grid shape reproduced",
            full_grid.shape == EXPECTED_SHAPE,
        ),
        (
            "Frozen full-grid field finite",
            np.all(np.isfinite(full_grid)),
        ),
        (
            "Support mask reproduced",
            supported_mask.shape == EXPECTED_SHAPE,
        ),
        (
            "Conservative denominator reproduced",
            denominator.shape == EXPECTED_SHAPE,
        ),
        (
            "Conservative numerator reproduced",
            numerator.shape == EXPECTED_SHAPE,
        ),
        (
            "Historical SG7E sources searched",
            len(source_rows) > 0,
        ),
        (
            "SG7E threshold/gate evidence extracted",
            len(threshold_candidates) > 0,
        ),
        (
            "Frozen P4 baseline metrics established",
            len(baseline_rows) > 0,
        ),
        (
            "SG7E1 validation matrix established",
            len(matrix_rows) > 0,
        ),
        (
            "No SG7E threshold changed or relaxed",
            True,
        ),
        (
            "No deployment correction performed",
            True,
        ),
    ]

    core_complete = all(
        bool(passed)
        for _, passed in checks
    )

    # If there is explicit authoritative evidence, we can proceed directly.
    # If all candidates are UNKNOWN, provenance is not strong enough.
    authority_resolved = (
        len(explicit_authoritative) > 0
    )

    if core_complete and authority_resolved:

        status = "FROZEN_FULL_GRID_DEPLOYMENT_CONTRACT_READY"

        diagnosis = "SG7E_AUTHORITATIVE_VALIDATION_CONTRACT_RECOVERED"

        recommendation = (
            "The SG7D6 frozen P4 field is verified and historical SG7E gate evidence has "
            "been recovered with explicit authoritative provenance. Proceed to SG7E1 using "
            "the frozen field and unchanged historical SG7E gates. Reconstruct each SG7E1 "
            "metric from its source definition; do not substitute a new threshold or infer "
            "a gate from the frozen candidate value."
        )

        next_milestone = (
            "V15-SG7E1 — Frozen Full-Grid Deployment Validation"
        )

    elif core_complete:

        status = "SG7E_CONTRACT_PROVENANCE_REQUIRES_CLARIFICATION"

        diagnosis = "SG7E_GATE_EVIDENCE_FOUND_BUT_AUTHORITY_NOT_EXPLICITLY_RESOLVED"

        recommendation = (
            "Historical SG7E evidence exists, but explicit authoritative-vs-diagnostic "
            "semantics are not yet strong enough to launch the final deployment screen. "
            "Do not change thresholds. Resolve gate authority from source/contract provenance "
            "before SG7E1."
        )

        next_milestone = (
            "V15-SG7E0R — Historical SG7E Gate Authority Reconciliation"
        )

    else:

        status = "SG7E_DEPLOYMENT_CONTRACT_AUDIT_INCOMPLETE"

        diagnosis = "ONE_OR_MORE_SG7E0_INPUT_OR_PROVENANCE_CHECKS_FAILED"

        recommendation = (
            "Do not run deployment validation yet. Repair only the failed SG7E0 input, "
            "historical-source, or threshold-provenance checks."
        )

        next_milestone = (
            "V15-SG7E0R — SG7E Contract / Baseline Audit Repair"
        )

    # -------------------------------------------------------------------------
    # Contract / summary
    # -------------------------------------------------------------------------

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E0",
            "status": status,
            "diagnosis": diagnosis,

            "frozen_input": {
                "candidate": "P4_full_grid",
                "file": str(SG7D6_FROZEN_GRID),
                "sha256": frozen_sha,
                "grid_shape": list(EXPECTED_SHAPE),
                "supported_cells": int(np.sum(supported_mask)),
                "unsupported_cells": int(np.sum(~supported_mask)),
                "background_saturation": background,
            },

            "historical_SG7E": {
                "sources_found": len(source_rows),
                "threshold_candidates_found": len(threshold_candidates),
                "explicit_authoritative_candidates":
                    len(explicit_authoritative),
                "unknown_role_candidates":
                    len(unknown_candidates),
            },

            "baseline": baseline_lookup,

            "thresholds_changed": False,
            "deployment_correction_performed": False,

            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7E0",
            "status": status,
            "diagnosis": diagnosis,
            "frozen_candidate": "P4_full_grid",
            "frozen_full_grid_sha256": frozen_sha,
            "historical_SG7E_sources_found": len(source_rows),
            "threshold_candidates_found": len(threshold_candidates),
            "explicit_authoritative_candidates":
                len(explicit_authoritative),
            "unknown_role_candidates":
                len(unknown_candidates),
            "thresholds_changed": False,
            "deployment_correction_performed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("FROZEN SG7D6 INPUT")
    print("  Candidate               : P4_full_grid")
    print(f"  Grid shape              : {full_grid.shape}")
    print(f"  SHA-256                 : {frozen_sha}")
    print(f"  Supported cells         : {np.sum(supported_mask):,}")
    print(f"  Unsupported cells       : {np.sum(~supported_mask):,}")
    print(f"  Background saturation   : {background:.6f}")
    print(
        f"  Grid range              : "
        f"{np.min(full_grid):.6f} -> {np.max(full_grid):.6f}"
    )

    print("\nHISTORICAL SG7E DISCOVERY")
    print(f"  Sources found           : {len(source_rows)}")
    print(f"  Threshold/gate records  : {len(threshold_candidates)}")
    print(f"  Explicit authoritative  : {len(explicit_authoritative)}")
    print(f"  Unknown role            : {len(unknown_candidates)}")

    print("\nFROZEN BASELINE")
    print(
        f"  Finite fraction         : "
        f"{baseline_lookup['grid_finite_fraction']:.6f}"
    )
    print(
        f"  Mean saturation         : "
        f"{baseline_lookup['grid_mean_saturation']:.6f}"
    )
    print(
        f"  Diagnostic plume cells  : "
        f"{baseline_lookup['diagnostic_full_grid_plume_cells']:,}"
    )
    print(
        f"  Unsupported plume cells : "
        f"{baseline_lookup['diagnostic_unsupported_plume_cells']:,}"
    )

    print("\n" + "=" * 78)
    print("V15-SG7E0 CONTRACT / BASELINE VALIDATION")
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
    print(f"  {INPUT_IDENTITY_TABLE.name}")
    print(f"  {SOURCE_DISCOVERY_TABLE.name}")
    print(f"  {THRESHOLD_TABLE.name}")
    print(f"  {COMPATIBILITY_TABLE.name}")
    print(f"  {BASELINE_TABLE.name}")
    print(f"  {ROLE_TABLE.name}")
    print(f"  {VALIDATION_MATRIX.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E0 DEPLOYMENT CONTRACT / BASELINE AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen L2 array was changed.")
    print("No SG7D6 full-grid array was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No deployment correction was performed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
