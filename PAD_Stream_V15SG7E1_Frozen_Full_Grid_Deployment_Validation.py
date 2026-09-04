from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib
import re
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1
# Frozen Full-Grid Deployment Validation
#
# FINAL DEPLOYMENT SCREEN — NO CORRECTION
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO SUPPORT MASK OR BACKGROUND POLICY CHANGED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POST-HOC ALIGNMENT.
# NO DEPLOYMENT CORRECTION.
#
# PURPOSE
# -------
# SG7E0R established the canonical historical SG7E authority registry:
#
#   PRIMARY_VOLUME_GATE
#   FOOTPRINT_IOU_GATE
#   CENTROID_GATE_CELLS
#   VERTICAL_EXTENT_GATE_LAYERS
#
# SG7E1 evaluates the frozen SG7D6 P4 full-grid candidate against ONLY those
# authoritative deployment gates.
#
# SG7E1:
#   1. verifies frozen input identity,
#   2. loads canonical gate thresholds from SG7E0R,
#   3. reconstructs historical reference plume data from persisted SG7E sources,
#   4. computes the four authoritative deployment metrics,
#   5. applies the recovered operators/limits exactly,
#   6. records diagnostic quantities separately,
#   7. makes a PASS/FAIL deployment decision without changing anything.
#
# If the historical reference plume cannot be uniquely reconstructed, SG7E1
# blocks safely rather than inventing a reference.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

SG7E0R_DIR = ROOT / "output" / "V15_SG7E0R"

SG7E0R_SUMMARY = (
    SG7E0R_DIR / "PAD_Stream_V15SG7E0R_Summary.json"
)

SG7E0R_CONTRACT = (
    SG7E0R_DIR / "V15SG7E0R_Reconciled_SG7E_Gate_Authority_Contract.json"
)

SG7E0R_REGISTRY = (
    SG7E0R_DIR / "V15SG7E0R_Canonical_SG7E_Gate_Registry.csv"
)

SG7E0_SOURCES = (
    ROOT / "output" / "V15_SG7E0"
    / "V15SG7E0_Historical_SG7E_Source_Discovery.csv"
)

SG7D6_FREEZE_MANIFEST = (
    ROOT / "output" / "V15_SG7D6"
    / "V15SG7D6_Full_Grid_Freeze_Manifest.json"
)

SG7D6_FROZEN_GRID = (
    ROOT / "output" / "V15_SG7D6"
    / "frozen_full_grid"
    / "V15SG7D6_P4_Frozen_Full_Grid_Deployment_Candidate.npz"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1_Summary.json"

INPUT_TABLE = OUT / "V15SG7E1_Frozen_Input_Identity.csv"
GATE_TABLE = OUT / "V15SG7E1_Authoritative_Gate_Registry.csv"
REFERENCE_DISCOVERY = OUT / "V15SG7E1_Reference_Plume_Discovery.csv"
REFERENCE_TABLE = OUT / "V15SG7E1_Reference_Plume_Identity.csv"
METRIC_TABLE = OUT / "V15SG7E1_Authoritative_Deployment_Metrics.csv"
DIAGNOSTIC_TABLE = OUT / "V15SG7E1_Deployment_Diagnostics.csv"
FINAL_GATE_TABLE = OUT / "V15SG7E1_Final_Gate_Matrix.csv"

NUMERICAL_FILE = OUT / "V15SG7E1_Deployment_Validation.npz"
MANIFEST_FILE = OUT / "V15SG7E1_Deployment_Validation_Manifest.json"
CONTRACT_FILE = OUT / "V15SG7E1_Deployment_Validation_Contract.json"

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EXPECTED_SHAPE = (15, 50, 50)

AUTHORITATIVE_GATES = (
    "PRIMARY_VOLUME_GATE",
    "FOOTPRINT_IOU_GATE",
    "CENTROID_GATE_CELLS",
    "VERTICAL_EXTENT_GATE_LAYERS",
)


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
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def sha256(path: Path, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def parse_float(value):
    try:
        return float(value)
    except Exception:
        return None


def evaluate_gate(value, operator, limit):
    if operator == "<=":
        return bool(value <= limit)
    if operator == "<":
        return bool(value < limit)
    if operator == ">=":
        return bool(value >= limit)
    if operator == ">":
        return bool(value > limit)
    raise ValueError(f"Unsupported gate operator: {operator!r}")


def infer_gate_semantics(gate_name, operator, limit):
    """
    Translate historical gate symbol into metric semantics.
    """
    if gate_name == "PRIMARY_VOLUME_GATE":
        return {
            "metric": "primary_volume_relative_error",
            "operator": operator,
            "limit": limit,
        }
    if gate_name == "FOOTPRINT_IOU_GATE":
        return {
            "metric": "footprint_IoU",
            "operator": operator,
            "limit": limit,
        }
    if gate_name == "CENTROID_GATE_CELLS":
        return {
            "metric": "centroid_distance_cells",
            "operator": operator,
            "limit": limit,
        }
    if gate_name == "VERTICAL_EXTENT_GATE_LAYERS":
        return {
            "metric": "vertical_extent_error_layers",
            "operator": operator,
            "limit": limit,
        }
    raise KeyError(gate_name)


def load_authoritative_registry():
    rows = load_csv(SG7E0R_REGISTRY)

    selected = {}

    for row in rows:
        symbol = str(row.get("symbol", "")).strip().upper()

        if symbol not in AUTHORITATIVE_GATES:
            continue

        if str(row.get("role", "")).strip().upper() != "AUTHORITATIVE":
            continue

        op = str(row.get("operator", "")).strip()
        limit = parse_float(row.get("canonical_numeric_limit"))

        if not op or limit is None:
            raise RuntimeError(
                f"Authoritative gate {symbol} lacks resolved operator/limit."
            )

        selected[symbol] = {
            "symbol": symbol,
            "operator": op,
            "limit": limit,
            "source": row.get("canonical_source"),
            "resolution": row.get("resolution"),
        }

    missing = [g for g in AUTHORITATIVE_GATES if g not in selected]

    if missing:
        raise RuntimeError(
            "Canonical SG7E registry is missing authoritative gates: "
            + ", ".join(missing)
        )

    return selected


def discover_reference_candidates(source_rows):
    """
    Search persisted SG7E numerical files for candidate reference/truth plume
    arrays. Strongly prefer 15x50x50 arrays with names suggesting reference,
    truth, target, canonical, physics, baseline, or plume.
    """

    candidates = []

    positive_tokens = (
        "truth",
        "reference",
        "ref",
        "target",
        "canonical",
        "physics",
        "benchmark",
        "plume",
    )

    negative_tokens = (
        "pred",
        "candidate",
        "model",
        "mapped",
        "full_grid",
        "p4",
    )

    seen_files = set()

    for row in source_rows:
        path = Path(row["path"])

        if path.suffix.lower() != ".npz":
            continue

        rp = str(path.resolve())

        if rp in seen_files:
            continue

        seen_files.add(rp)

        try:
            db = np.load(path, allow_pickle=True)
        except Exception:
            continue

        for key in db.files:
            try:
                arr = np.asarray(db[key])
            except Exception:
                continue

            if arr.shape != EXPECTED_SHAPE:
                continue

            name = key.lower()
            file_text = path.name.lower()

            score = 0
            reasons = []

            for tok in positive_tokens:
                if tok in name:
                    score += 5
                    reasons.append(f"key:{tok}")
                if tok in file_text:
                    score += 2
                    reasons.append(f"file:{tok}")

            for tok in negative_tokens:
                if tok in name:
                    score -= 4
                    reasons.append(f"neg_key:{tok}")
                if tok in file_text:
                    score -= 1
                    reasons.append(f"neg_file:{tok}")

            # Historical SG7E numerical outputs get a base bonus.
            score += 2
            reasons.append("historical_SG7E_npz")

            finite_fraction = float(np.mean(np.isfinite(arr)))
            range_min = float(np.nanmin(arr)) if np.any(np.isfinite(arr)) else np.nan
            range_max = float(np.nanmax(arr)) if np.any(np.isfinite(arr)) else np.nan

            candidates.append({
                "path": str(path),
                "key": key,
                "shape": str(arr.shape),
                "dtype": str(arr.dtype),
                "score": score,
                "reasons": ";".join(reasons),
                "finite_fraction": finite_fraction,
                "min": range_min,
                "max": range_max,
            })

    candidates.sort(
        key=lambda r: (r["score"], r["finite_fraction"]),
        reverse=True,
    )

    return candidates


def select_reference_candidate(candidates):
    """
    Require a positive provenance score and a clear score lead.
    """
    if not candidates:
        return None, "NO_REFERENCE_CANDIDATE_FOUND"

    top = candidates[0]

    if top["score"] <= 0:
        return None, "NO_POSITIVE_REFERENCE_PROVENANCE"

    if len(candidates) >= 2:
        second = candidates[1]

        if (
            second["score"] > 0
            and
            top["score"] - second["score"] < 3
            and
            (
                top["path"] != second["path"]
                or
                top["key"] != second["key"]
            )
        ):
            return None, "AMBIGUOUS_REFERENCE_CANDIDATES"

    return top, "UNIQUE_REFERENCE_SELECTED"


def reconstruct_plume_threshold_from_history():
    """
    Search historical SG7E source for explicit plume threshold semantics.
    This threshold is used to derive binary plume masks for SG7E metrics.

    Preference:
      explicit PLUME...THRESHOLD assignments in SG7E source.
    """

    source_rows = load_csv(SG7E0_SOURCES)

    pattern = re.compile(
        r'(?P<name>[A-Z][A-Z0-9_]*(?:PLUME|SAT)[A-Z0-9_]*THRESHOLD[A-Z0-9_]*)'
        r'\s*=\s*(?P<value>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)'
    )

    hits = []

    for row in source_rows:
        path = Path(row["path"])

        if path.suffix.lower() != ".py":
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            for m in pattern.finditer(line):
                hits.append({
                    "name": m.group("name"),
                    "value": float(m.group("value")),
                    "source": str(path),
                    "line": line_no,
                    "raw": line.strip(),
                })

    # Prefer exact/common values repeated across sources.
    if not hits:
        return None, []

    counts = {}
    for h in hits:
        counts.setdefault(h["value"], 0)
        counts[h["value"]] += 1

    ranked_values = sorted(
        counts.items(),
        key=lambda kv: kv[1],
        reverse=True,
    )

    best_value, best_count = ranked_values[0]

    if len(ranked_values) > 1 and ranked_values[1][1] == best_count:
        return None, hits

    return best_value, hits


def binary_plume(arr, threshold):
    return np.isfinite(arr) & (arr >= threshold)


def primary_volume_relative_error(pred_mask, ref_mask):
    pred = int(np.sum(pred_mask))
    ref = int(np.sum(ref_mask))
    return abs(pred - ref) / max(ref, 1)


def footprint_iou(pred_mask, ref_mask):
    # Collapse vertically: any plume in a column.
    pred2 = np.any(pred_mask, axis=0)
    ref2 = np.any(ref_mask, axis=0)

    inter = int(np.sum(pred2 & ref2))
    union = int(np.sum(pred2 | ref2))

    if union == 0:
        return 1.0

    return inter / union


def centroid_cells(mask):
    idx = np.argwhere(mask)

    if idx.size == 0:
        return np.asarray([np.nan, np.nan, np.nan], dtype=float)

    # Return [k, j, i] centroid in logical cell coordinates.
    return np.mean(idx, axis=0)


def centroid_distance_cells(pred_mask, ref_mask):
    a = centroid_cells(pred_mask)
    b = centroid_cells(ref_mask)

    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        return np.inf

    return float(np.linalg.norm(a - b))


def vertical_extent_layers(mask):
    idx = np.argwhere(mask)

    if idx.size == 0:
        return 0

    kmin = int(np.min(idx[:, 0]))
    kmax = int(np.max(idx[:, 0]))

    return kmax - kmin + 1


def vertical_extent_error_layers(pred_mask, ref_mask):
    return abs(
        vertical_extent_layers(pred_mask)
        -
        vertical_extent_layers(ref_mask)
    )


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1")
    print("Frozen Full-Grid Deployment Validation")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D6 FULL-GRID ARRAY WILL BE CHANGED.
NO SUPPORT MASK OR BACKGROUND POLICY WILL BE CHANGED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO POST-HOC ALIGNMENT WILL BE PERFORMED.
NO DEPLOYMENT CORRECTION WILL BE PERFORMED.
""")

    e0r_summary = load_json(SG7E0R_SUMMARY)
    e0r_contract = load_json(SG7E0R_CONTRACT)
    freeze_manifest = load_json(SG7D6_FREEZE_MANIFEST)

    if (
        e0r_summary.get("status")
        != "SG7E_GATE_AUTHORITY_RECONCILED"
    ):
        raise RuntimeError(
            "SG7E1 requires successful SG7E0R gate-authority reconciliation."
        )

    if (
        e0r_summary.get("diagnosis")
        != "CANONICAL_HISTORICAL_SG7E_GATE_REGISTRY_ESTABLISHED"
    ):
        raise RuntimeError(
            "SG7E1 requires the canonical SG7E gate-registry diagnosis."
        )

    if (
        freeze_manifest.get("status")
        != "SG7D_FULL_GRID_CANDIDATE_FROZEN"
    ):
        raise RuntimeError(
            "SG7E1 requires the formally frozen SG7D6 full-grid candidate."
        )

    frozen_sha = sha256(SG7D6_FROZEN_GRID)

    if frozen_sha != freeze_manifest["frozen_full_grid_sha256"]:
        raise RuntimeError(
            "Frozen SG7D6 candidate hash does not match freeze manifest."
        )

    db = np.load(SG7D6_FROZEN_GRID, allow_pickle=True)

    full_grid = np.asarray(
        db["saturation_grid_full"],
        dtype=np.float64,
    )

    supported_mask = np.asarray(
        db["supported_mask"],
        dtype=np.uint8,
    ).astype(bool)

    background = float(
        np.asarray(
            db["background_saturation"]
        )
    )

    if full_grid.shape != EXPECTED_SHAPE:
        raise RuntimeError(
            f"Unexpected SG7D6 shape {full_grid.shape}."
        )

    registry = load_authoritative_registry()

    # -------------------------------------------------------------------------
    # Persist authoritative gate registry
    # -------------------------------------------------------------------------

    gate_rows = []

    for gate_name in AUTHORITATIVE_GATES:
        rec = registry[gate_name]
        semantics = infer_gate_semantics(
            gate_name,
            rec["operator"],
            rec["limit"],
        )

        gate_rows.append({
            "gate": gate_name,
            "metric": semantics["metric"],
            "operator": rec["operator"],
            "limit": rec["limit"],
            "canonical_source": rec["source"],
            "resolution": rec["resolution"],
        })

    save_csv(GATE_TABLE, gate_rows)

    # -------------------------------------------------------------------------
    # Frozen input identity
    # -------------------------------------------------------------------------

    save_csv(
        INPUT_TABLE,
        [{
            "candidate": "P4_full_grid",
            "file": str(SG7D6_FROZEN_GRID),
            "sha256": frozen_sha,
            "grid_shape": str(full_grid.shape),
            "supported_cells": int(np.sum(supported_mask)),
            "unsupported_cells": int(np.sum(~supported_mask)),
            "background_saturation": background,
            "grid_min": float(np.min(full_grid)),
            "grid_max": float(np.max(full_grid)),
            "all_finite": bool(np.all(np.isfinite(full_grid))),
        }],
    )

    # -------------------------------------------------------------------------
    # Historical plume-threshold provenance
    # -------------------------------------------------------------------------

    plume_threshold, threshold_hits = (
        reconstruct_plume_threshold_from_history()
    )

    # -------------------------------------------------------------------------
    # Historical reference plume discovery
    # -------------------------------------------------------------------------

    source_rows = load_csv(SG7E0_SOURCES)

    reference_candidates = discover_reference_candidates(
        source_rows
    )

    save_csv(
        REFERENCE_DISCOVERY,
        reference_candidates,
    )

    reference_choice, reference_status = (
        select_reference_candidate(
            reference_candidates
        )
    )

    reference_ready = (
        reference_choice is not None
        and
        plume_threshold is not None
    )

    if not reference_ready:

        # Safe block: do not invent a reference or plume threshold.
        reference_identity_rows = [{
            "status": reference_status,
            "plume_threshold_resolved": plume_threshold is not None,
            "plume_threshold":
                plume_threshold if plume_threshold is not None else "",
            "selected_reference_path": "",
            "selected_reference_key": "",
        }]

        save_csv(
            REFERENCE_TABLE,
            reference_identity_rows,
        )

        checks = [
            ("SG7E0R authoritative registry reproduced", True),
            ("Frozen SG7D6 hash reproduced", True),
            ("All four authoritative gates loaded", len(registry) == 4),
            ("Historical plume threshold uniquely recovered", plume_threshold is not None),
            ("Historical reference plume uniquely recovered", reference_choice is not None),
            ("No SG7E threshold changed or relaxed", True),
            ("No deployment correction performed", True),
        ]

        status = "SG7E1_REFERENCE_CONTRACT_BLOCKED"

        diagnosis = "HISTORICAL_REFERENCE_PLUME_OR_THRESHOLD_NOT_UNIQUELY_RECOVERED"

        recommendation = (
            "Do not evaluate deployment gates yet. The authoritative SG7E gate registry is "
            "resolved, but the historical reference plume and/or plume-threshold definition "
            "is not uniquely reconstructible from persisted evidence. Audit only reference "
            "provenance; do not create a new truth field or threshold."
        )

        next_milestone = (
            "V15-SG7E1R0 — Historical SG7E Reference Plume Provenance Audit"
        )

        save_csv(
            FINAL_GATE_TABLE,
            [{
                "gate": "REFERENCE_CONTRACT",
                "passed": False,
                "reason": diagnosis,
            }],
        )

        save_json(
            CONTRACT_FILE,
            {
                "milestone": "V15-SG7E1",
                "status": status,
                "diagnosis": diagnosis,
                "frozen_candidate_sha256": frozen_sha,
                "authoritative_gates": list(AUTHORITATIVE_GATES),
                "reference_status": reference_status,
                "plume_threshold_resolved": plume_threshold is not None,
                "thresholds_changed": False,
                "deployment_correction_performed": False,
                "recommendation": recommendation,
                "next_milestone": next_milestone,
            },
        )

        save_json(
            SUMMARY_FILE,
            {
                "milestone": "V15-SG7E1",
                "status": status,
                "diagnosis": diagnosis,
                "authoritative_gates_loaded": 4,
                "reference_status": reference_status,
                "plume_threshold_resolved": plume_threshold is not None,
                "candidate_changed": False,
                "thresholds_changed": False,
                "recommendation": recommendation,
                "next_milestone": next_milestone,
            },
        )

        print("REFERENCE CONTRACT")
        print(f"  Reference status        : {reference_status}")
        print(
            f"  Plume threshold resolved: "
            f"{plume_threshold is not None}"
        )

        print("\n" + "=" * 78)
        print("V15-SG7E1 VALIDATION ENTRY CHECK")
        print("=" * 78)

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
        print("\n" + "=" * 78)
        print("V15-SG7E1 DEPLOYMENT VALIDATION: BLOCKED SAFELY")
        print("=" * 78)
        return

    # -------------------------------------------------------------------------
    # Load selected historical reference
    # -------------------------------------------------------------------------

    ref_path = Path(reference_choice["path"])
    ref_key = reference_choice["key"]

    ref_db = np.load(ref_path, allow_pickle=True)
    reference_grid = np.asarray(
        ref_db[ref_key],
        dtype=np.float64,
    )

    if reference_grid.shape != EXPECTED_SHAPE:
        raise RuntimeError(
            "Selected reference plume does not match 15x50x50 grid."
        )

    pred_mask = binary_plume(
        full_grid,
        plume_threshold,
    )

    ref_mask = binary_plume(
        reference_grid,
        plume_threshold,
    )

    # -------------------------------------------------------------------------
    # Authoritative metrics
    # -------------------------------------------------------------------------

    metrics = {
        "primary_volume_relative_error":
            primary_volume_relative_error(
                pred_mask,
                ref_mask,
            ),

        "footprint_IoU":
            footprint_iou(
                pred_mask,
                ref_mask,
            ),

        "centroid_distance_cells":
            centroid_distance_cells(
                pred_mask,
                ref_mask,
            ),

        "vertical_extent_error_layers":
            float(
                vertical_extent_error_layers(
                    pred_mask,
                    ref_mask,
                )
            ),
    }

    metric_rows = []

    final_gate_rows = []

    all_authoritative_pass = True

    for gate_name in AUTHORITATIVE_GATES:
        rec = registry[gate_name]
        sem = infer_gate_semantics(
            gate_name,
            rec["operator"],
            rec["limit"],
        )

        value = metrics[sem["metric"]]
        passed = evaluate_gate(
            value,
            sem["operator"],
            sem["limit"],
        )

        all_authoritative_pass = (
            all_authoritative_pass
            and
            passed
        )

        metric_rows.append({
            "gate": gate_name,
            "metric": sem["metric"],
            "value": value,
            "operator": sem["operator"],
            "limit": sem["limit"],
            "passed": passed,
            "canonical_source": rec["source"],
        })

        final_gate_rows.append({
            "gate": gate_name,
            "metric": sem["metric"],
            "value": value,
            "operator": sem["operator"],
            "limit": sem["limit"],
            "passed": passed,
            "role": "AUTHORITATIVE",
        })

    save_csv(
        METRIC_TABLE,
        metric_rows,
    )

    save_csv(
        FINAL_GATE_TABLE,
        final_gate_rows,
    )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    pred_centroid = centroid_cells(pred_mask)
    ref_centroid = centroid_cells(ref_mask)

    diagnostic_rows = [{
        "plume_threshold":
            plume_threshold,

        "predicted_plume_cells":
            int(np.sum(pred_mask)),

        "reference_plume_cells":
            int(np.sum(ref_mask)),

        "predicted_footprint_cells":
            int(np.sum(np.any(pred_mask, axis=0))),

        "reference_footprint_cells":
            int(np.sum(np.any(ref_mask, axis=0))),

        "predicted_vertical_extent_layers":
            vertical_extent_layers(pred_mask),

        "reference_vertical_extent_layers":
            vertical_extent_layers(ref_mask),

        "predicted_centroid_k":
            float(pred_centroid[0]),

        "predicted_centroid_j":
            float(pred_centroid[1]),

        "predicted_centroid_i":
            float(pred_centroid[2]),

        "reference_centroid_k":
            float(ref_centroid[0]),

        "reference_centroid_j":
            float(ref_centroid[1]),

        "reference_centroid_i":
            float(ref_centroid[2]),

        "unsupported_background_plume_cells":
            int(np.sum(
                pred_mask & (~supported_mask)
            )),
    }]

    save_csv(
        DIAGNOSTIC_TABLE,
        diagnostic_rows,
    )

    # -------------------------------------------------------------------------
    # Reference identity
    # -------------------------------------------------------------------------

    save_csv(
        REFERENCE_TABLE,
        [{
            "status": reference_status,
            "selected_reference_path": str(ref_path),
            "selected_reference_key": ref_key,
            "reference_file_sha256": sha256(ref_path),
            "reference_shape": str(reference_grid.shape),
            "reference_min": float(np.nanmin(reference_grid)),
            "reference_max": float(np.nanmax(reference_grid)),
            "plume_threshold": plume_threshold,
            "reference_score": reference_choice["score"],
            "reference_reasons": reference_choice["reasons"],
        }],
    )

    # -------------------------------------------------------------------------
    # Persist validation package
    # -------------------------------------------------------------------------

    np.savez_compressed(
        NUMERICAL_FILE,

        frozen_candidate_grid=
            full_grid.astype(np.float32),

        reference_grid=
            reference_grid.astype(np.float32),

        predicted_plume_mask=
            pred_mask.astype(np.uint8),

        reference_plume_mask=
            ref_mask.astype(np.uint8),

        supported_mask=
            supported_mask.astype(np.uint8),

        plume_threshold=
            np.asarray(
                plume_threshold,
                dtype=np.float64,
            ),

        frozen_candidate_sha256=
            np.asarray(
                frozen_sha
            ),

        reference_file_sha256=
            np.asarray(
                sha256(ref_path)
            ),
    )

    # -------------------------------------------------------------------------
    # Final validation checks
    # -------------------------------------------------------------------------

    checks = [
        (
            "SG7E0R authoritative registry reproduced",
            True,
        ),
        (
            "Frozen SG7D6 candidate SHA-256 reproduced",
            frozen_sha
            ==
            freeze_manifest["frozen_full_grid_sha256"],
        ),
        (
            "All four authoritative SG7E gates loaded",
            len(registry) == 4,
        ),
        (
            "Historical plume threshold uniquely recovered",
            plume_threshold is not None,
        ),
        (
            "Historical reference plume uniquely recovered",
            reference_choice is not None,
        ),
        (
            "Reference plume shape matches frozen grid",
            reference_grid.shape == EXPECTED_SHAPE,
        ),
        (
            "PRIMARY_VOLUME_GATE evaluated",
            any(r["gate"] == "PRIMARY_VOLUME_GATE" for r in final_gate_rows),
        ),
        (
            "FOOTPRINT_IOU_GATE evaluated",
            any(r["gate"] == "FOOTPRINT_IOU_GATE" for r in final_gate_rows),
        ),
        (
            "CENTROID_GATE_CELLS evaluated",
            any(r["gate"] == "CENTROID_GATE_CELLS" for r in final_gate_rows),
        ),
        (
            "VERTICAL_EXTENT_GATE_LAYERS evaluated",
            any(r["gate"] == "VERTICAL_EXTENT_GATE_LAYERS" for r in final_gate_rows),
        ),
        (
            "No SG7E threshold changed or relaxed",
            True,
        ),
        (
            "No post-hoc alignment performed",
            True,
        ),
        (
            "No deployment correction performed",
            True,
        ),
    ]

    entry_complete = all(bool(p) for _, p in checks)

    if entry_complete and all_authoritative_pass:

        status = "FROZEN_FULL_GRID_DEPLOYMENT_VALIDATION_PASS"

        diagnosis = "P4_FROZEN_GRID_PASSES_ALL_AUTHORITATIVE_SG7E_GATES"

        recommendation = (
            "The frozen SG7D6 P4 field passes all four authoritative historical SG7E "
            "deployment gates without correction or threshold changes. Do not declare final "
            "deployment freeze yet. Independently reproduce the SG7E1 reference identity, "
            "metrics, and pass/fail matrix before final SG7E acceptance."
        )

        next_milestone = (
            "V15-SG7E2 — Independent Frozen Deployment Validation Reproduction"
        )

    elif entry_complete:

        failed = [
            row["gate"]
            for row in final_gate_rows
            if not row["passed"]
        ]

        status = "FROZEN_FULL_GRID_DEPLOYMENT_VALIDATION_FAIL"

        diagnosis = "P4_FROZEN_GRID_FAILS_ONE_OR_MORE_AUTHORITATIVE_SG7E_GATES"

        recommendation = (
            "Do not modify the frozen field or any SG7E threshold. Audit only the failed "
            "authoritative deployment gate(s) and their historical metric definitions before "
            "considering any further development."
        )

        next_milestone = (
            "V15-SG7E1R — Authoritative Deployment Gate Failure Audit"
        )

    else:

        failed = []

        status = "SG7E1_DEPLOYMENT_VALIDATION_INCOMPLETE"

        diagnosis = "ONE_OR_MORE_SG7E1_VALIDATION_ENTRY_CHECKS_FAILED"

        recommendation = (
            "Do not modify the frozen candidate. Repair only the failed SG7E1 reference or "
            "metric reconstruction checks."
        )

        next_milestone = (
            "V15-SG7E1R — Deployment Validation Reconstruction Repair"
        )

    # -------------------------------------------------------------------------
    # Manifest / contract / summary
    # -------------------------------------------------------------------------

    save_json(
        MANIFEST_FILE,
        {
            "milestone": "V15-SG7E1",
            "status": status,
            "diagnosis": diagnosis,
            "candidate": "P4_full_grid",
            "candidate_sha256": frozen_sha,
            "candidate_changed": False,
            "reference_path": str(ref_path),
            "reference_key": ref_key,
            "reference_sha256": sha256(ref_path),
            "plume_threshold": plume_threshold,
            "authoritative_gates": list(AUTHORITATIVE_GATES),
            "all_authoritative_pass": all_authoritative_pass,
            "failed_authoritative_gates": failed,
            "thresholds_changed": False,
            "posthoc_alignment": False,
            "deployment_correction_performed": False,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1",
            "status": status,
            "diagnosis": diagnosis,
            "candidate": "P4_full_grid",
            "candidate_sha256": frozen_sha,
            "reference": {
                "path": str(ref_path),
                "key": ref_key,
                "sha256": sha256(ref_path),
                "plume_threshold": plume_threshold,
            },
            "authoritative_metrics": metrics,
            "authoritative_gate_results": final_gate_rows,
            "candidate_changed": False,
            "thresholds_changed": False,
            "posthoc_alignment": False,
            "deployment_correction_performed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7E1",
            "status": status,
            "diagnosis": diagnosis,
            "candidate": "P4_full_grid",
            "all_authoritative_pass": all_authoritative_pass,
            "failed_authoritative_gates": failed,
            "primary_volume_relative_error":
                metrics["primary_volume_relative_error"],
            "footprint_IoU":
                metrics["footprint_IoU"],
            "centroid_distance_cells":
                metrics["centroid_distance_cells"],
            "vertical_extent_error_layers":
                metrics["vertical_extent_error_layers"],
            "candidate_changed": False,
            "thresholds_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("AUTHORITATIVE SG7E CONTRACT")
    for row in gate_rows:
        print(
            f"  {row['gate']:30s} | "
            f"{row['operator']} {row['limit']:.6g}"
        )

    print("\nREFERENCE PLUME")
    print(f"  File                    : {ref_path.name}")
    print(f"  Key                     : {ref_key}")
    print(f"  SHA-256                 : {sha256(ref_path)}")
    print(f"  Plume threshold         : {plume_threshold:.6g}")

    print("\nAUTHORITATIVE DEPLOYMENT METRICS")
    for row in metric_rows:
        print(
            f"  {row['gate']:30s} | "
            f"value={row['value']:.6e} | "
            f"{row['operator']} {row['limit']:.6e} | "
            f"{'PASS' if row['passed'] else 'FAIL'}"
        )

    print("\n" + "=" * 78)
    print("V15-SG7E1 FINAL AUTHORITATIVE GATES")
    print("=" * 78)

    for row in final_gate_rows:
        print(
            f"[{'PASS' if row['passed'] else 'FAIL'}] "
            f"{row['gate']}"
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
    print(f"  {INPUT_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print(f"  {REFERENCE_DISCOVERY.name}")
    print(f"  {REFERENCE_TABLE.name}")
    print(f"  {METRIC_TABLE.name}")
    print(f"  {DIAGNOSTIC_TABLE.name}")
    print(f"  {FINAL_GATE_TABLE.name}")

    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")

    print("\nManifest:")
    print(f"  {MANIFEST_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1 FROZEN FULL-GRID DEPLOYMENT VALIDATION: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen candidate value was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No post-hoc alignment was performed.")
    print("No deployment correction was performed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
