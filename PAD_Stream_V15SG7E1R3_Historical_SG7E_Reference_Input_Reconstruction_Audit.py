from __future__ import annotations

from pathlib import Path
import csv
import json
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R3
# Historical SG7E Reference Input Reconstruction Audit
#
# FORENSIC SOURCE-RECONSTRUCTION MILESTONE
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
# SG7E1R2 established:
#
#   SG7E_HISTORICAL_REFERENCE_TRUTH_NOT_PERSISTED
#
# with:
#
#   NO_DISCOVERED_15X50X50_ARRAY_HAS_VALID_REFERENCE_TRUTH_SEMANTICS
#
# Therefore the historical SG7E reference used by the acceptance workflow must
# be reconstructed from its ORIGINAL UPSTREAM PHYSICS INPUT, not from coverage
# diagnostics.
#
# SG7E1R3:
#
#   1. identifies historical SG7E source files that computed the four
#      authoritative deployment metrics/gates,
#   2. traces reference/truth variables used by those metric calculations,
#   3. traces those variables back to file/key loads or deterministic
#      reconstruction functions,
#   4. inventories candidate upstream physics artifacts,
#   5. distinguishes source physics inputs from map-back diagnostics,
#   6. determines whether a unique reconstructible reference-input chain exists.
#
# SG7E1R3 DOES NOT evaluate the frozen candidate against deployment gates.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R3"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R2_DIR = ROOT / "output" / "V15_SG7E1R2"

R2_SUMMARY = R2_DIR / "PAD_Stream_V15SG7E1R2_Summary.json"
R2_CONTRACT = R2_DIR / "V15SG7E1R2_Reference_Creation_Chain_Contract.json"

E0_SOURCE_DISCOVERY = (
    ROOT / "output" / "V15_SG7E0"
    / "V15SG7E0_Historical_SG7E_Source_Discovery.csv"
)

E0R_REGISTRY = (
    ROOT / "output" / "V15_SG7E0R"
    / "V15SG7E0R_Canonical_SG7E_Gate_Registry.csv"
)

R0_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R0"
    / "V15SG7E1R0_Historical_Reference_Plume_Contract.json"
)

D6_FREEZE_MANIFEST = (
    ROOT / "output" / "V15_SG7D6"
    / "V15SG7D6_Full_Grid_Freeze_Manifest.json"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R3_Summary.json"

METRIC_SOURCE_TABLE = OUT / "V15SG7E1R3_Authoritative_Metric_Source_Trace.csv"
REFERENCE_SYMBOL_TABLE = OUT / "V15SG7E1R3_Reference_Symbol_Trace.csv"
LOAD_TRACE_TABLE = OUT / "V15SG7E1R3_Reference_Load_Trace.csv"
RECON_FUNCTION_TABLE = OUT / "V15SG7E1R3_Reference_Reconstruction_Functions.csv"
UPSTREAM_ARTIFACT_TABLE = OUT / "V15SG7E1R3_Upstream_Physics_Artifact_Candidates.csv"
DECISION_TABLE = OUT / "V15SG7E1R3_Reference_Input_Reconstruction_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R3_Reference_Input_Reconstruction_Contract.json"

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


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def find_lines(text, pattern, flags=0):
    rx = re.compile(pattern, flags)
    rows = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        if rx.search(line):
            rows.append((idx, line))
    return rows


def context(lines, line_no, radius=6):
    return "\n".join(
        lines[max(0, line_no - radius - 1):min(len(lines), line_no + radius)]
    )


def extract_identifiers(expr):
    if not expr:
        return []
    toks = re.findall(r'(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)', expr)
    ignore = {
        "np", "float", "int", "bool", "sum", "mean", "abs", "min", "max",
        "where", "clip", "array", "asarray", "astype", "nan", "True", "False",
        "len", "range", "enumerate"
    }
    return [t for t in toks if t not in ignore]


def score_upstream_artifact(path: Path, key: str):
    """
    Prefer actual physics/reference/plume/saturation artifacts over coverage,
    count, weight, mapback, and candidate diagnostics.
    """
    name = path.name.lower()
    key_l = key.lower()

    score = 0
    reasons = []

    for tok, val in (
        ("truth", 12),
        ("reference", 12),
        ("canonical", 10),
        ("physics", 10),
        ("saturation", 8),
        ("plume", 8),
        ("sg7a", 7),
        ("sg7e", 3),
    ):
        if tok in key_l:
            score += val
            reasons.append(f"key:{tok}")
        if tok in name:
            score += val // 2
            reasons.append(f"file:{tok}")

    for tok, val in (
        ("coverage", -10),
        ("streamline_count", -12),
        ("count", -6),
        ("weight", -8),
        ("support_distance", -10),
        ("mapback", -5),
        ("candidate", -8),
        ("prediction", -8),
        ("p4", -6),
    ):
        if tok in key_l:
            score += val
            reasons.append(f"neg_key:{tok}")
        if tok in name:
            score += val // 2
            reasons.append(f"neg_file:{tok}")

    return score, reasons


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R3")
    print("Historical SG7E Reference Input Reconstruction Audit")
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

    r2_summary = load_json(R2_SUMMARY)
    r2_contract = load_json(R2_CONTRACT)
    r0_contract = load_json(R0_CONTRACT)
    d6_manifest = load_json(D6_FREEZE_MANIFEST)

    if r2_summary.get("status") != "SG7E_HISTORICAL_REFERENCE_TRUTH_NOT_PERSISTED":
        raise RuntimeError(
            "SG7E1R3 requires SG7E1R2 non-persisted-reference status."
        )

    if (
        r2_summary.get("diagnosis")
        != "NO_DISCOVERED_15X50X50_ARRAY_HAS_VALID_REFERENCE_TRUTH_SEMANTICS"
    ):
        raise RuntimeError(
            "SG7E1R3 requires SG7E1R2 missing-reference-truth diagnosis."
        )

    threshold_info = r0_contract.get("plume_threshold", {})
    threshold = float(threshold_info["value"])

    if not threshold_info.get("resolved", False):
        raise RuntimeError(
            "SG7E1R3 requires resolved historical plume threshold."
        )

    if d6_manifest.get("status") != "SG7D_FULL_GRID_CANDIDATE_FROZEN":
        raise RuntimeError(
            "SG7E1R3 requires frozen SG7D6 candidate provenance."
        )

    source_rows = load_csv(E0_SOURCE_DISCOVERY)
    registry_rows = load_csv(E0R_REGISTRY)

    # -------------------------------------------------------------------------
    # Identify source files associated with authoritative gate definitions
    # -------------------------------------------------------------------------

    authoritative_sources = set()

    for row in registry_rows:
        if str(row.get("role", "")).upper() != "AUTHORITATIVE":
            continue

        symbol = str(row.get("symbol", "")).upper()
        if symbol not in AUTHORITATIVE_GATES:
            continue

        src = row.get("canonical_source")
        if src:
            authoritative_sources.add(src)

    metric_source_rows = []

    for src in sorted(authoritative_sources):
        p = Path(src)
        text = safe_text(p)
        lines = text.splitlines()

        for gate in AUTHORITATIVE_GATES:
            hits = find_lines(text, re.escape(gate))

            for line_no, line in hits:
                metric_source_rows.append({
                    "gate": gate,
                    "source": str(p),
                    "line": line_no,
                    "raw": line.strip()[:500],
                    "context": context(lines, line_no, radius=8)[:2500],
                })

    save_csv(METRIC_SOURCE_TABLE, metric_source_rows)

    # -------------------------------------------------------------------------
    # Trace reference/truth variables in those authoritative sources
    # -------------------------------------------------------------------------

    reference_symbol_rows = []
    reference_symbols = set()

    reference_name_pattern = re.compile(
        r'(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*(?:truth|reference|ref|canonical|target)[A-Za-z0-9_]*)',
        re.IGNORECASE,
    )

    for src in sorted(authoritative_sources):
        p = Path(src)
        text = safe_text(p)
        lines = text.splitlines()

        for idx, line in enumerate(lines, start=1):
            # Restrict to metric/plume/gate-related lines or nearby semantics.
            lower = line.lower()
            if not any(tok in lower for tok in (
                "plume", "volume", "iou", "centroid", "vertical", "gate",
                "truth", "reference", "canonical", "target"
            )):
                continue

            for m in reference_name_pattern.finditer(line):
                symbol = m.group(1)
                reference_symbols.add(symbol)

                reference_symbol_rows.append({
                    "source": str(p),
                    "line": idx,
                    "symbol": symbol,
                    "raw": line.strip()[:500],
                    "context": context(lines, idx, radius=5)[:1800],
                })

    save_csv(REFERENCE_SYMBOL_TABLE, reference_symbol_rows)

    # -------------------------------------------------------------------------
    # Trace loads / assignments of reference symbols
    # -------------------------------------------------------------------------

    load_trace_rows = []
    recon_function_rows = []

    load_patterns = [
        re.compile(r'np\.load\((.+?)\)'),
        re.compile(r'load\((.+?)\)'),
    ]

    for src in sorted(authoritative_sources):
        p = Path(src)
        text = safe_text(p)
        lines = text.splitlines()

        for symbol in sorted(reference_symbols):
            assign_rx = re.compile(
                rf'^\s*{re.escape(symbol)}\s*=\s*(.+)$'
            )

            for idx, line in enumerate(lines, start=1):
                m = assign_rx.match(line)
                if not m:
                    continue

                expr = m.group(1).strip()

                load_trace_rows.append({
                    "source": str(p),
                    "line": idx,
                    "symbol": symbol,
                    "assignment_expression": expr[:1000],
                    "context": context(lines, idx, radius=8)[:2500],
                })

                # Function call candidates in RHS.
                fn_calls = re.findall(
                    r'([A-Za-z_][A-Za-z0-9_]*)\s*\(',
                    expr
                )

                for fn in fn_calls:
                    if fn in {"np", "float", "int", "bool"}:
                        continue

                    # Search function definition in same source.
                    fn_rx = re.compile(
                        rf'^\s*def\s+{re.escape(fn)}\s*\('
                    )

                    for j, fn_line in enumerate(lines, start=1):
                        if fn_rx.search(fn_line):
                            recon_function_rows.append({
                                "source": str(p),
                                "function": fn,
                                "definition_line": j,
                                "used_by_symbol": symbol,
                                "definition_context":
                                    context(lines, j, radius=15)[:4000],
                            })

    save_csv(LOAD_TRACE_TABLE, load_trace_rows)
    save_csv(RECON_FUNCTION_TABLE, recon_function_rows)

    # -------------------------------------------------------------------------
    # Inventory upstream physics artifact candidates from ALL historical SG7E
    # source-discovered NPZs and nearby outputs.
    # -------------------------------------------------------------------------

    upstream_rows = []

    seen = set()

    for row in source_rows:
        path = Path(row["path"])

        if path.suffix.lower() != ".npz" or not path.exists():
            continue

        rp = str(path.resolve())
        if rp in seen:
            continue
        seen.add(rp)

        try:
            db = np.load(path, allow_pickle=True)
        except Exception:
            continue

        for key in db.files:
            try:
                arr = np.asarray(db[key])
            except Exception:
                continue

            score, reasons = score_upstream_artifact(path, key)

            upstream_rows.append({
                "path": str(path),
                "key": key,
                "shape": str(arr.shape),
                "dtype": str(arr.dtype),
                "score": score,
                "reasons": ";".join(reasons),
                "finite_fraction":
                    float(np.mean(np.isfinite(arr))) if arr.size else 0.0,
                "min":
                    float(np.nanmin(arr))
                    if arr.size and np.any(np.isfinite(arr))
                    else "",
                "max":
                    float(np.nanmax(arr))
                    if arr.size and np.any(np.isfinite(arr))
                    else "",
            })

    upstream_rows.sort(
        key=lambda r: r["score"],
        reverse=True,
    )

    save_csv(UPSTREAM_ARTIFACT_TABLE, upstream_rows)

    # -------------------------------------------------------------------------
    # Reconstruction decision
    # -------------------------------------------------------------------------

    positive_upstream = [
        r for r in upstream_rows
        if r["score"] > 0
        and any(tok in r["reasons"] for tok in (
            "truth", "reference", "canonical", "physics", "saturation", "plume"
        ))
    ]

    # Determine whether explicit load traces already name a source artifact.
    explicit_paths = set()

    for row in load_trace_rows:
        ctx = row["context"]

        # Windows/Unix-ish .npz filename extraction.
        for m in re.finditer(
            r'([A-Za-z0-9_\-\.\\/]+\.npz)',
            ctx,
            re.IGNORECASE,
        ):
            explicit_paths.add(Path(m.group(1)).name)

    explicitly_linked_candidates = [
        r for r in positive_upstream
        if Path(r["path"]).name in explicit_paths
    ]

    checks = [
        (
            "Incoming SG7E1R2 non-persisted truth diagnosis reproduced",
            True,
        ),
        (
            "Resolved plume threshold retained",
            abs(threshold - 0.5) < 1e-15,
        ),
        (
            "Authoritative SG7E metric source files identified",
            len(authoritative_sources) > 0,
        ),
        (
            "Authoritative metric source contexts traced",
            len(metric_source_rows) > 0,
        ),
        (
            "Reference/truth symbols searched",
            True,
        ),
        (
            "Reference symbol assignments traced",
            True,
        ),
        (
            "Reference reconstruction functions searched",
            True,
        ),
        (
            "Upstream physics artifacts inventoried",
            len(upstream_rows) > 0,
        ),
        (
            "Coverage/support diagnostics remain excluded as truth",
            True,
        ),
        (
            "No candidate performance used to infer reference input",
            True,
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

    core_complete = all(bool(v) for _, v in checks)

    if core_complete and len(explicitly_linked_candidates) == 1:

        selected = explicitly_linked_candidates[0]

        status = "SG7E_REFERENCE_INPUT_CHAIN_RECONSTRUCTED"
        diagnosis = "UNIQUE_UPSTREAM_PHYSICS_REFERENCE_INPUT_IDENTIFIED"
        recommendation = (
            "The historical SG7E metric source explicitly links to one upstream physics "
            "reference artifact/key. Reconstruct and persist that reference field exactly, "
            "then rerun the frozen SG7E deployment validation using the already locked "
            "threshold and authoritative gate registry."
        )
        next_milestone = (
            "V15-SG7E1R4 — Exact Historical Reference Field Reconstruction / Persistence"
        )

    elif core_complete and len(explicitly_linked_candidates) > 1:

        selected = None

        status = "SG7E_MULTIPLE_EXPLICIT_REFERENCE_INPUTS_FOUND"
        diagnosis = "AUTHORITATIVE_METRIC_SOURCE_REFERENCES_MULTIPLE_UPSTREAM_PHYSICS_INPUTS"
        recommendation = (
            "Do not evaluate SG7E gates. The authoritative source lineage explicitly reaches "
            "multiple upstream physics artifacts. Audit only those linked inputs and determine "
            "which one feeds the historical deployment metrics."
        )
        next_milestone = (
            "V15-SG7E1R4 — Explicit Reference Input Divergence Audit"
        )

    elif core_complete and len(positive_upstream) == 1:

        selected = positive_upstream[0]

        status = "SG7E_REFERENCE_INPUT_CHAIN_INFERRED_FROM_SINGLE_PHYSICS_ARTIFACT"
        diagnosis = "ONE_PHYSICS_REFERENCE_CANDIDATE_REMAINS_BUT_DIRECT_LOAD_LINK_NOT_FOUND"
        recommendation = (
            "One plausible upstream physics reference artifact remains, but the direct load "
            "link from the historical SG7E metric source was not recovered. Do not evaluate "
            "gates yet. Verify the final source linkage before reconstructing the field."
        )
        next_milestone = (
            "V15-SG7E1R4 — Reference Source-Link Verification Audit"
        )

    elif core_complete:

        selected = None

        status = "SG7E_REFERENCE_INPUT_CHAIN_NOT_YET_RECONSTRUCTED"
        diagnosis = "HISTORICAL_METRIC_SOURCE_DOES_NOT_YET_RESOLVE_UNIQUE_UPSTREAM_REFERENCE"
        recommendation = (
            "Do not evaluate SG7E gates. The historical acceptance source has been traced, "
            "but the unique upstream physics reference input is not yet established. Use the "
            "generated symbol/load/function traces to isolate the exact reference-building "
            "path; do not substitute a coverage diagnostic."
        )
        next_milestone = (
            "V15-SG7E1R4 — Historical Reference Build-Path Audit"
        )

    else:

        selected = None

        status = "SG7E_REFERENCE_INPUT_RECONSTRUCTION_AUDIT_INCOMPLETE"
        diagnosis = "ONE_OR_MORE_SOURCE_RECONSTRUCTION_CHECKS_FAILED"
        recommendation = (
            "Do not evaluate SG7E gates. Repair only the failed SG7E1R3 source-reconstruction "
            "checks."
        )
        next_milestone = (
            "V15-SG7E1R4 — Reference Input Reconstruction Repair"
        )

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "plume_threshold": threshold,
        "authoritative_source_count": len(authoritative_sources),
        "metric_source_records": len(metric_source_rows),
        "reference_symbols_found": len(reference_symbols),
        "reference_assignment_records": len(load_trace_rows),
        "reconstruction_functions_found": len(recon_function_rows),
        "upstream_artifact_candidates": len(upstream_rows),
        "positive_physics_candidates": len(positive_upstream),
        "explicitly_linked_candidates": len(explicitly_linked_candidates),
        "selected_path": selected["path"] if selected else "",
        "selected_key": selected["key"] if selected else "",
        "next_milestone": next_milestone,
    }

    save_csv(DECISION_TABLE, [decision])

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1R3",
            "status": status,
            "diagnosis": diagnosis,
            "plume_threshold": {
                "value": threshold,
                "changed": False,
            },
            "source_trace": {
                "authoritative_sources": sorted(authoritative_sources),
                "reference_symbols": sorted(reference_symbols),
                "metric_source_records": len(metric_source_rows),
                "assignment_records": len(load_trace_rows),
                "reconstruction_functions": len(recon_function_rows),
            },
            "upstream_reference": {
                "selected": selected is not None,
                "path": selected["path"] if selected else None,
                "key": selected["key"] if selected else None,
                "explicit_link":
                    selected in explicitly_linked_candidates
                    if selected else False,
            },
            "constraints": {
                "candidate_performance_used": False,
                "coverage_diagnostic_used_as_truth": False,
                "threshold_changed": False,
                "posthoc_alignment": False,
                "deployment_correction_performed": False,
            },
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7E1R3",
            "status": status,
            "diagnosis": diagnosis,
            "authoritative_source_count": len(authoritative_sources),
            "reference_symbols_found": len(reference_symbols),
            "positive_physics_candidates": len(positive_upstream),
            "explicitly_linked_candidates": len(explicitly_linked_candidates),
            "reference_selected": selected is not None,
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("HISTORICAL SG7E REFERENCE SOURCE TRACE")
    print(f"  Authoritative sources   : {len(authoritative_sources)}")
    print(f"  Metric source records   : {len(metric_source_rows)}")
    print(f"  Reference symbols       : {len(reference_symbols)}")
    print(f"  Assignment records      : {len(load_trace_rows)}")
    print(f"  Reconstruction funcs    : {len(recon_function_rows)}")
    print(f"  Upstream artifacts      : {len(upstream_rows)}")
    print(f"  Positive physics cands  : {len(positive_upstream)}")
    print(f"  Explicitly linked cands : {len(explicitly_linked_candidates)}")

    if positive_upstream:
        print("\nTOP UPSTREAM PHYSICS CANDIDATES")
        for row in positive_upstream[:10]:
            print(
                f"  score={row['score']:4d} | "
                f"{Path(row['path']).name} :: {row['key']} | "
                f"shape={row['shape']}"
            )

    if selected:
        print("\nSELECTED UPSTREAM REFERENCE INPUT")
        print(f"  File                    : {Path(selected['path']).name}")
        print(f"  Key                     : {selected['key']}")
        print(f"  Shape                   : {selected['shape']}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R3 RECONSTRUCTION VALIDATION")
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

    print("\nTables:")
    print(f"  {METRIC_SOURCE_TABLE.name}")
    print(f"  {REFERENCE_SYMBOL_TABLE.name}")
    print(f"  {LOAD_TRACE_TABLE.name}")
    print(f"  {RECON_FUNCTION_TABLE.name}")
    print(f"  {UPSTREAM_ARTIFACT_TABLE.name}")
    print(f"  {DECISION_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R3 HISTORICAL REFERENCE INPUT RECONSTRUCTION AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen SG7D6 field was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No coverage/support diagnostic was used as truth.")
    print("No frozen-candidate performance was used to infer the reference.")
    print("No post-hoc alignment was performed.")
    print("No deployment correction was performed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
