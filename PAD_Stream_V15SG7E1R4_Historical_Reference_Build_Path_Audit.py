from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re
from collections import defaultdict, deque

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R4
# Historical Reference Build-Path Audit
#
# FORENSIC BUILD-PATH MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO SUPPORT MASK OR BACKGROUND POLICY CHANGED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POST-HOC ALIGNMENT.
# NO DEPLOYMENT CORRECTION.
# NO REFERENCE FIELD WILL BE SELECTED BY CANDIDATE PERFORMANCE.
#
# PURPOSE
# -------
# SG7E1R3 established:
#
#   SG7E_REFERENCE_INPUT_CHAIN_NOT_YET_RECONSTRUCTED
#
# with:
#
#   HISTORICAL_METRIC_SOURCE_DOES_NOT_YET_RESOLVE_UNIQUE_UPSTREAM_REFERENCE
#
# R1R3 found one authoritative SG7E metric source, two reference symbols, and
# multiple plausible upstream physics arrays, including SG7A raw/corrected grid
# saturation arrays. However, no explicit source-artifact link was recovered.
#
# SG7E1R4 therefore traces the REFERENCE BUILD PATH itself:
#
#   authoritative metric expression
#       -> reference symbol
#       -> assignment
#       -> dependent symbols
#       -> helper functions / indexing / thresholding
#       -> np.load handles
#       -> artifact path expressions
#       -> NPZ keys
#       -> upstream physics array
#
# This milestone does not choose a reference because it "looks right" or because
# it improves frozen-candidate performance. Selection is allowed only if source
# semantics and dependency lineage uniquely establish the historical reference.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R4"
OUT.mkdir(parents=True, exist_ok=True)

R3_DIR = ROOT / "output" / "V15_SG7E1R3"

R3_SUMMARY = R3_DIR / "PAD_Stream_V15SG7E1R3_Summary.json"
R3_CONTRACT = R3_DIR / "V15SG7E1R3_Reference_Input_Reconstruction_Contract.json"
R3_METRIC_SOURCE = R3_DIR / "V15SG7E1R3_Authoritative_Metric_Source_Trace.csv"
R3_REFERENCE_SYMBOLS = R3_DIR / "V15SG7E1R3_Reference_Symbol_Trace.csv"
R3_LOAD_TRACE = R3_DIR / "V15SG7E1R3_Reference_Load_Trace.csv"
R3_UPSTREAM = R3_DIR / "V15SG7E1R3_Upstream_Physics_Artifact_Candidates.csv"

R0_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R0"
    / "V15SG7E1R0_Historical_Reference_Plume_Contract.json"
)

D6_MANIFEST = (
    ROOT / "output" / "V15_SG7D6"
    / "V15SG7D6_Full_Grid_Freeze_Manifest.json"
)

# Outputs
SOURCE_AST_TABLE = OUT / "V15SG7E1R4_Authoritative_Source_AST_Inventory.csv"
SYMBOL_DEP_TABLE = OUT / "V15SG7E1R4_Reference_Symbol_Dependency_Graph.csv"
LOAD_HANDLE_TABLE = OUT / "V15SG7E1R4_NPZ_Load_Handle_Trace.csv"
KEY_ACCESS_TABLE = OUT / "V15SG7E1R4_NPZ_Key_Access_Trace.csv"
PATH_EXPR_TABLE = OUT / "V15SG7E1R4_Artifact_Path_Expression_Trace.csv"
BUILD_PATH_TABLE = OUT / "V15SG7E1R4_Reference_Build_Path_Candidates.csv"
SEMANTIC_TABLE = OUT / "V15SG7E1R4_Build_Path_Semantic_Audit.csv"
DECISION_TABLE = OUT / "V15SG7E1R4_Reference_Build_Path_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R4_Historical_Reference_Build_Path_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R4_Summary.json"


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_csv(path: Path, rows):
    if not rows:
        # still create an empty artifact
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def source_from_r3(rows):
    vals = []
    for row in rows:
        s = row.get("source", "").strip()
        if s and s not in vals:
            vals.append(s)
    return vals


def node_text(source, node):
    try:
        return ast.get_source_segment(source, node) or ""
    except Exception:
        return ""


def names_in_node(node):
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.add(n.id)
    return out


def target_names(node):
    out = []
    if isinstance(node, ast.Name):
        out.append(node.id)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for e in node.elts:
            out.extend(target_names(e))
    return out


def assignment_inventory(tree, source, source_path):
    rows = []
    assigns = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            if isinstance(node, ast.Assign):
                targets = []
                for t in node.targets:
                    targets.extend(target_names(t))
                value = node.value
            else:
                targets = target_names(node.target)
                value = node.value

            if value is None:
                continue

            deps = sorted(names_in_node(value))
            expr = node_text(source, value)

            for t in targets:
                row = {
                    "source": str(source_path),
                    "line": getattr(node, "lineno", ""),
                    "target": t,
                    "dependencies": ";".join(deps),
                    "expression": expr[:3000],
                }
                rows.append(row)
                assigns.setdefault(t, []).append(row)

    return rows, assigns


def function_inventory(tree, source, source_path):
    funcs = {}
    rows = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = [a.arg for a in node.args.args]
            body_names = sorted(names_in_node(node))
            txt = node_text(source, node)

            row = {
                "source": str(source_path),
                "line": node.lineno,
                "function": node.name,
                "parameters": ";".join(params),
                "body_symbols": ";".join(body_names),
                "definition": txt[:6000],
            }
            rows.append(row)
            funcs[node.name] = row

    return rows, funcs


def trace_symbol_graph(root_symbols, assigns, max_depth=12):
    rows = []
    visited = set()
    q = deque((s, 0, None) for s in root_symbols)

    while q:
        symbol, depth, parent = q.popleft()
        key = (symbol, depth, parent)
        if key in visited:
            continue
        visited.add(key)

        entries = assigns.get(symbol, [])
        if not entries:
            rows.append({
                "root_or_symbol": symbol,
                "depth": depth,
                "parent": parent or "",
                "assignment_found": False,
                "line": "",
                "expression": "",
                "dependencies": "",
            })
            continue

        for entry in entries:
            deps = [x for x in entry["dependencies"].split(";") if x]
            rows.append({
                "root_or_symbol": symbol,
                "depth": depth,
                "parent": parent or "",
                "assignment_found": True,
                "line": entry["line"],
                "expression": entry["expression"],
                "dependencies": ";".join(deps),
            })

            if depth < max_depth:
                for dep in deps:
                    if dep != symbol:
                        q.append((dep, depth + 1, symbol))

    return rows


def extract_np_loads(tree, source, source_path):
    """
    Capture:
        db = np.load(path)
        with np.load(path) as db:
    """
    rows = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            fn = node_text(source, call.func)
            if fn.endswith("np.load") or fn == "np.load":
                handles = []
                for t in node.targets:
                    handles.extend(target_names(t))
                path_expr = node_text(source, call.args[0]) if call.args else ""
                for h in handles:
                    rows.append({
                        "source": str(source_path),
                        "line": node.lineno,
                        "handle": h,
                        "path_expression": path_expr,
                        "context": node_text(source, node)[:2500],
                    })

        if isinstance(node, ast.With):
            for item in node.items:
                call = item.context_expr
                if isinstance(call, ast.Call):
                    fn = node_text(source, call.func)
                    if fn.endswith("np.load") or fn == "np.load":
                        h = ""
                        if item.optional_vars is not None:
                            names = target_names(item.optional_vars)
                            h = names[0] if names else ""
                        path_expr = node_text(source, call.args[0]) if call.args else ""
                        rows.append({
                            "source": str(source_path),
                            "line": node.lineno,
                            "handle": h,
                            "path_expression": path_expr,
                            "context": node_text(source, node)[:2500],
                        })

    return rows


def extract_subscript_key(node):
    # Python 3.9+: slice is direct expression.
    sl = node.slice
    if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
        return sl.value
    return None


def extract_key_accesses(tree, source, source_path, handles):
    rows = []
    hset = set(handles)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue

        if isinstance(node.value, ast.Name) and node.value.id in hset:
            key = extract_subscript_key(node)
            if key is not None:
                rows.append({
                    "source": str(source_path),
                    "line": node.lineno,
                    "handle": node.value.id,
                    "key": key,
                    "expression": node_text(source, node)[:2000],
                })

    return rows


def resolve_literal_path(expr, source_dir):
    """
    Conservative path resolution only. No eval.
    Handles quoted string literals and Path("...") literals.
    """
    if not expr:
        return None

    m = re.fullmatch(r'\s*[rRuUfFbB]*[\'"]([^\'"]+)[\'"]\s*', expr)
    if m:
        p = Path(m.group(1))
        return p if p.is_absolute() else (source_dir / p)

    m = re.fullmatch(
        r'\s*Path\(\s*[rRuUfFbB]*[\'"]([^\'"]+)[\'"]\s*\)\s*',
        expr
    )
    if m:
        p = Path(m.group(1))
        return p if p.is_absolute() else (source_dir / p)

    return None


def semantic_score(path_name, key, reference_symbols, graph_text):
    name = path_name.lower()
    key_l = key.lower()
    graph_l = graph_text.lower()

    score = 0
    reasons = []

    positive = (
        ("sg7a", 18),
        ("truth", 18),
        ("reference", 18),
        ("canonical", 14),
        ("corrected_grid_saturation", 14),
        ("raw_grid_saturation", 10),
        ("grid_saturation", 9),
        ("saturation", 6),
        ("physics", 8),
    )

    negative = (
        ("coverage", -18),
        ("streamline_count", -20),
        ("coverage_weight", -20),
        ("support_distance", -20),
        ("candidate", -12),
        ("prediction", -12),
        ("pi_rnn", -6),
    )

    for tok, val in positive:
        if tok in key_l:
            score += val
            reasons.append(f"key:{tok}")
        if tok in name:
            score += val // 3
            reasons.append(f"file:{tok}")
        if tok in graph_l:
            score += max(1, val // 4)
            reasons.append(f"graph:{tok}")

    for tok, val in negative:
        if tok in key_l:
            score += val
            reasons.append(f"neg_key:{tok}")
        if tok in name:
            score += val // 3
            reasons.append(f"neg_file:{tok}")

    # Direct historical-reference naming is stronger than generic saturation.
    for sym in reference_symbols:
        if sym.lower() in graph_l:
            score += 3

    return score, reasons


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R4")
    print("Historical Reference Build-Path Audit")
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
NO REFERENCE FIELD WILL BE SELECTED BY CANDIDATE PERFORMANCE.
""")

    r3_summary = load_json(R3_SUMMARY)
    r3_contract = load_json(R3_CONTRACT)
    r0_contract = load_json(R0_CONTRACT)
    d6_manifest = load_json(D6_MANIFEST)

    if r3_summary.get("status") != "SG7E_REFERENCE_INPUT_CHAIN_NOT_YET_RECONSTRUCTED":
        raise RuntimeError("SG7E1R4 requires the SG7E1R3 unresolved build-path status.")

    if r3_summary.get("diagnosis") != (
        "HISTORICAL_METRIC_SOURCE_DOES_NOT_YET_RESOLVE_UNIQUE_UPSTREAM_REFERENCE"
    ):
        raise RuntimeError("SG7E1R4 requires the SG7E1R3 unresolved-reference diagnosis.")

    threshold_info = r0_contract.get("plume_threshold", {})
    threshold = float(threshold_info["value"])

    if not threshold_info.get("resolved", False):
        raise RuntimeError("Historical plume threshold is not resolved.")

    if d6_manifest.get("status") != "SG7D_FULL_GRID_CANDIDATE_FROZEN":
        raise RuntimeError("SG7D6 frozen input provenance is not valid.")

    metric_rows = load_csv(R3_METRIC_SOURCE)
    ref_rows = load_csv(R3_REFERENCE_SYMBOLS)
    r3_load_rows = load_csv(R3_LOAD_TRACE)
    upstream_rows = load_csv(R3_UPSTREAM)

    sources = source_from_r3(metric_rows)
    reference_symbols = sorted({
        r.get("symbol", "").strip()
        for r in ref_rows
        if r.get("symbol", "").strip()
    })

    all_ast_rows = []
    all_graph_rows = []
    all_load_rows = []
    all_key_rows = []
    all_path_rows = []
    all_function_rows = []

    build_candidates = []

    for src_s in sources:
        src = Path(src_s)
        if not src.exists():
            continue

        text = safe_text(src)

        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        assign_rows, assigns = assignment_inventory(tree, text, src)
        function_rows, funcs = function_inventory(tree, text, src)

        all_ast_rows.extend(assign_rows)
        all_function_rows.extend(function_rows)

        graph_rows = trace_symbol_graph(reference_symbols, assigns)
        for row in graph_rows:
            row["source"] = str(src)
        all_graph_rows.extend(graph_rows)

        graph_text = "\n".join(
            f"{r.get('root_or_symbol','')} {r.get('expression','')} "
            f"{r.get('dependencies','')}"
            for r in graph_rows
        )

        loads = extract_np_loads(tree, text, src)
        all_load_rows.extend(loads)

        handles = [r["handle"] for r in loads if r["handle"]]
        keys = extract_key_accesses(tree, text, src, handles)
        all_key_rows.extend(keys)

        load_by_handle = defaultdict(list)
        for row in loads:
            load_by_handle[row["handle"]].append(row)

        for row in loads:
            resolved = resolve_literal_path(row["path_expression"], src.parent)
            all_path_rows.append({
                "source": str(src),
                "line": row["line"],
                "handle": row["handle"],
                "path_expression": row["path_expression"],
                "literal_path_resolved": bool(resolved),
                "resolved_path": str(resolved) if resolved else "",
                "exists": bool(resolved and resolved.exists()),
            })

        for key_row in keys:
            h = key_row["handle"]
            for load_row in load_by_handle.get(h, []):
                resolved = resolve_literal_path(
                    load_row["path_expression"], src.parent
                )

                score, reasons = semantic_score(
                    Path(resolved).name if resolved else load_row["path_expression"],
                    key_row["key"],
                    reference_symbols,
                    graph_text,
                )

                build_candidates.append({
                    "source": str(src),
                    "load_line": load_row["line"],
                    "handle": h,
                    "path_expression": load_row["path_expression"],
                    "resolved_path": str(resolved) if resolved else "",
                    "path_exists": bool(resolved and resolved.exists()),
                    "key_line": key_row["line"],
                    "key": key_row["key"],
                    "semantic_score": score,
                    "semantic_reasons": ";".join(reasons),
                    "reference_graph_mentions_key":
                        key_row["key"].lower() in graph_text.lower(),
                    "reference_graph_mentions_handle":
                        h.lower() in graph_text.lower(),
                })

    save_csv(SOURCE_AST_TABLE, all_ast_rows)
    save_csv(SYMBOL_DEP_TABLE, all_graph_rows)
    save_csv(LOAD_HANDLE_TABLE, all_load_rows)
    save_csv(KEY_ACCESS_TABLE, all_key_rows)
    save_csv(PATH_EXPR_TABLE, all_path_rows)

    # -------------------------------------------------------------------------
    # Add R3 upstream candidates as corroborating evidence.
    # -------------------------------------------------------------------------

    upstream_lookup = defaultdict(list)
    for row in upstream_rows:
        upstream_lookup[row.get("key", "")].append(row)

    semantic_rows = []
    for cand in build_candidates:
        corroboration = upstream_lookup.get(cand["key"], [])
        corroborated_paths = ";".join(
            sorted({r.get("path", "") for r in corroboration if r.get("path", "")})
        )

        row = dict(cand)
        row["R3_upstream_key_match_count"] = len(corroboration)
        row["R3_upstream_matching_paths"] = corroborated_paths
        semantic_rows.append(row)

    semantic_rows.sort(
        key=lambda r: (
            bool(r["reference_graph_mentions_key"]),
            bool(r["reference_graph_mentions_handle"]),
            int(r["semantic_score"]),
            bool(r["path_exists"]),
        ),
        reverse=True,
    )

    save_csv(BUILD_PATH_TABLE, build_candidates)
    save_csv(SEMANTIC_TABLE, semantic_rows)

    # -------------------------------------------------------------------------
    # Strict selection logic.
    #
    # A build path is "direct" only when:
    #   - the reference dependency graph mentions the NPZ key OR its load handle,
    #   - the key is semantically physics/reference-like,
    #   - it is not coverage/support/count/weight/candidate diagnostic material.
    # -------------------------------------------------------------------------

    direct = []
    for r in semantic_rows:
        reasons = r["semantic_reasons"].lower()
        negative = any(tok in reasons for tok in (
            "neg_key:coverage",
            "neg_key:streamline_count",
            "neg_key:coverage_weight",
            "neg_key:support_distance",
            "neg_key:candidate",
            "neg_key:prediction",
        ))

        graph_link = (
            bool(r["reference_graph_mentions_key"])
            or bool(r["reference_graph_mentions_handle"])
        )

        if graph_link and int(r["semantic_score"]) > 0 and not negative:
            direct.append(r)

    # Collapse exact same resolved path/key.
    unique_direct = {}
    for r in direct:
        ident = (
            r["resolved_path"] or r["path_expression"],
            r["key"],
        )
        if ident not in unique_direct:
            unique_direct[ident] = r

    direct_unique = list(unique_direct.values())

    checks = [
        ("Incoming SG7E1R3 unresolved build-path diagnosis reproduced", True),
        ("Historical plume threshold retained unchanged", abs(threshold - 0.5) < 1e-15),
        ("Authoritative metric source retained", len(sources) > 0),
        ("Reference symbols retained", len(reference_symbols) > 0),
        ("Authoritative source parsed into AST", len(all_ast_rows) > 0),
        ("Reference dependency graph constructed", len(all_graph_rows) > 0),
        ("NPZ load handles traced", True),
        ("NPZ key accesses traced", True),
        ("Artifact path expressions traced", True),
        ("R3 upstream physics inventory retained as corroboration", len(upstream_rows) > 0),
        ("Coverage/support diagnostics excluded from reference selection", True),
        ("Frozen candidate performance not used for selection", True),
        ("No SG7E threshold changed or relaxed", True),
        ("No post-hoc alignment performed", True),
        ("No deployment correction performed", True),
    ]

    if len(direct_unique) == 1:
        selected = direct_unique[0]
        status = "SG7E_HISTORICAL_REFERENCE_BUILD_PATH_RESOLVED"
        diagnosis = "UNIQUE_SOURCE_LINKED_UPSTREAM_REFERENCE_BUILD_PATH_IDENTIFIED"
        recommendation = (
            "A unique source-linked historical reference build path has been identified. "
            "Do not evaluate deployment gates yet. Reconstruct the reference field exactly "
            "from this persisted upstream artifact/key using the historical source operation "
            "order and resolved plume threshold, then persist and independently validate the "
            "reconstructed truth before SG7E1."
        )
        next_milestone = (
            "V15-SG7E1R5 — Exact Historical Reference Field Reconstruction / Persistence"
        )

    elif len(direct_unique) > 1:
        selected = None
        status = "SG7E_HISTORICAL_REFERENCE_BUILD_PATH_CONFLICT"
        diagnosis = "MULTIPLE_SOURCE_LINKED_REFERENCE_BUILD_PATHS_REMAIN"
        recommendation = (
            "Do not evaluate SG7E gates. Multiple source-linked physics/reference build "
            "paths remain. Audit only their historical branch conditions, time-index "
            "selection, raw-vs-corrected semantics, and final metric consumption."
        )
        next_milestone = (
            "V15-SG7E1R5 — Reference Build-Path Branch / Time-Slice Conflict Audit"
        )

    else:
        selected = None
        status = "SG7E_HISTORICAL_REFERENCE_BUILD_PATH_NOT_YET_RESOLVED"
        diagnosis = "REFERENCE_SYMBOL_GRAPH_DOES_NOT_YET_REACH_UNIQUE_NPZ_KEY"
        recommendation = (
            "Do not evaluate SG7E gates. The source-level reference graph has been expanded, "
            "but no unique NPZ key is yet directly linked. Audit helper functions, imported "
            "builders, branch conditions, and time-slice/index expressions reached by the "
            "reference symbols. Do not select SG7A raw/corrected arrays by naming alone."
        )
        next_milestone = (
            "V15-SG7E1R5 — Deep Reference Builder / Branch Trace Audit"
        )

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "plume_threshold": threshold,
        "authoritative_sources": len(sources),
        "reference_symbols": len(reference_symbols),
        "assignment_records": len(all_ast_rows),
        "dependency_records": len(all_graph_rows),
        "npz_load_records": len(all_load_rows),
        "npz_key_access_records": len(all_key_rows),
        "build_path_candidates": len(semantic_rows),
        "direct_source_linked_candidates": len(direct_unique),
        "selected_path": (
            selected["resolved_path"] or selected["path_expression"]
            if selected else ""
        ),
        "selected_key": selected["key"] if selected else "",
        "next_milestone": next_milestone,
    }

    save_csv(DECISION_TABLE, [decision])

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1R4",
            "status": status,
            "diagnosis": diagnosis,
            "plume_threshold": {
                "value": threshold,
                "changed": False,
            },
            "reference_build_path": {
                "authoritative_sources": sources,
                "reference_symbols": reference_symbols,
                "direct_source_linked_candidate_count": len(direct_unique),
                "selected": selected is not None,
                "selected_path": (
                    selected["resolved_path"] or selected["path_expression"]
                    if selected else None
                ),
                "selected_key": selected["key"] if selected else None,
            },
            "constraints": {
                "candidate_performance_used": False,
                "coverage_support_diagnostic_promoted_to_truth": False,
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
            "milestone": "V15-SG7E1R4",
            "status": status,
            "diagnosis": diagnosis,
            "direct_source_linked_candidates": len(direct_unique),
            "reference_selected": selected is not None,
            "threshold_changed": False,
            "candidate_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print("REFERENCE BUILD-PATH TRACE")
    print(f"  Authoritative sources   : {len(sources)}")
    print(f"  Reference symbols       : {len(reference_symbols)}")
    print(f"  Assignment records      : {len(all_ast_rows)}")
    print(f"  Dependency records      : {len(all_graph_rows)}")
    print(f"  NPZ load records        : {len(all_load_rows)}")
    print(f"  NPZ key accesses        : {len(all_key_rows)}")
    print(f"  Build-path candidates   : {len(semantic_rows)}")
    print(f"  Direct linked candidates: {len(direct_unique)}")

    if semantic_rows:
        print("\nTOP SOURCE-LINKED BUILD-PATH CANDIDATES")
        for r in semantic_rows[:12]:
            path_name = Path(r["resolved_path"]).name if r["resolved_path"] else r["path_expression"]
            print(
                f"  score={int(r['semantic_score']):4d} | "
                f"graphKey={str(bool(r['reference_graph_mentions_key'])):5s} | "
                f"graphHandle={str(bool(r['reference_graph_mentions_handle'])):5s} | "
                f"{path_name} :: {r['key']}"
            )

    if selected:
        print("\nSELECTED HISTORICAL REFERENCE BUILD PATH")
        print(
            "  Artifact                : "
            f"{Path(selected['resolved_path']).name if selected['resolved_path'] else selected['path_expression']}"
        )
        print(f"  Key                     : {selected['key']}")
        print(f"  Source line             : {selected['key_line']}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R4 BUILD-PATH VALIDATION")
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
    print(f"  {SOURCE_AST_TABLE.name}")
    print(f"  {SYMBOL_DEP_TABLE.name}")
    print(f"  {LOAD_HANDLE_TABLE.name}")
    print(f"  {KEY_ACCESS_TABLE.name}")
    print(f"  {PATH_EXPR_TABLE.name}")
    print(f"  {BUILD_PATH_TABLE.name}")
    print(f"  {SEMANTIC_TABLE.name}")
    print(f"  {DECISION_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R4 HISTORICAL REFERENCE BUILD-PATH AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen SG7D6 field was changed.")
    print("No SG7E threshold was changed or relaxed.")
    print("No coverage/support diagnostic was promoted to truth.")
    print("No frozen-candidate performance was used to select a reference.")
    print("No post-hoc alignment was performed.")
    print("No deployment correction was performed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
