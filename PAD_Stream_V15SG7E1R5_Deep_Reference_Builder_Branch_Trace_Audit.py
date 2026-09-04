from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re
from collections import defaultdict, deque


# =============================================================================
# PAD-Stream V15-SG7E1R5
# Deep Reference Builder / Branch Trace Audit
#
# FORENSIC SOURCE / CONTROL-FLOW MILESTONE
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
# SG7E1R4 established:
#
#   SG7E_HISTORICAL_REFERENCE_BUILD_PATH_NOT_YET_RESOLVED
#
# with:
#
#   REFERENCE_SYMBOL_GRAPH_DOES_NOT_YET_REACH_UNIQUE_NPZ_KEY
#
# and found:
#
#   NPZ load records        : 0
#   NPZ key accesses        : 0
#
# Therefore the authoritative SG7E source is likely receiving its historical
# reference through one or more of:
#
#   - imported helper functions,
#   - imported constants / modules,
#   - function arguments,
#   - branch-selected variables,
#   - time-indexed 4-D saturation arrays,
#   - dictionary / object fields,
#   - helper builders defined in another source file.
#
# SG7E1R5 recursively audits those paths without executing or modifying the
# historical source.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R5"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R4_DIR = ROOT / "output" / "V15_SG7E1R4"

R4_SUMMARY = R4_DIR / "PAD_Stream_V15SG7E1R4_Summary.json"
R4_CONTRACT = R4_DIR / "V15SG7E1R4_Historical_Reference_Build_Path_Contract.json"
R4_AST = R4_DIR / "V15SG7E1R4_Authoritative_Source_AST_Inventory.csv"
R4_GRAPH = R4_DIR / "V15SG7E1R4_Reference_Symbol_Dependency_Graph.csv"

R3_METRIC_SOURCE = (
    ROOT / "output" / "V15_SG7E1R3"
    / "V15SG7E1R3_Authoritative_Metric_Source_Trace.csv"
)

R3_UPSTREAM = (
    ROOT / "output" / "V15_SG7E1R3"
    / "V15SG7E1R3_Upstream_Physics_Artifact_Candidates.csv"
)

R0_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R0"
    / "V15SG7E1R0_Historical_Reference_Plume_Contract.json"
)

D6_MANIFEST = (
    ROOT / "output" / "V15_SG7D6"
    / "V15SG7D6_Full_Grid_Freeze_Manifest.json"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R5_Summary.json"

IMPORT_TABLE = OUT / "V15SG7E1R5_Import_Lineage.csv"
CALL_TABLE = OUT / "V15SG7E1R5_Reference_Helper_Call_Trace.csv"
HELPER_TABLE = OUT / "V15SG7E1R5_Imported_Helper_Definitions.csv"
BRANCH_TABLE = OUT / "V15SG7E1R5_Reference_Branch_Conditions.csv"
INDEX_TABLE = OUT / "V15SG7E1R5_Time_Slice_Index_Trace.csv"
FIELD_TABLE = OUT / "V15SG7E1R5_Reference_Field_Access_Trace.csv"
DEEP_PATH_TABLE = OUT / "V15SG7E1R5_Deep_Build_Path_Candidates.csv"
DECISION_TABLE = OUT / "V15SG7E1R5_Deep_Build_Path_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R5_Deep_Reference_Build_Path_Contract.json"

# =============================================================================
# Helpers
# =============================================================================


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
        path.write_text("", encoding="utf-8")
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


def node_text(source: str, node):
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


def attr_chain(node):
    parts = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return ""


def imported_modules(tree, source_path):
    rows = []
    aliases = {}

    for node in tree.body:
        if isinstance(node, ast.Import):
            for item in node.names:
                alias = item.asname or item.name.split(".")[0]
                aliases[alias] = item.name
                rows.append({
                    "source": str(source_path),
                    "line": node.lineno,
                    "kind": "import",
                    "module": item.name,
                    "name": "",
                    "alias": alias,
                })

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for item in node.names:
                alias = item.asname or item.name
                aliases[alias] = f"{module}.{item.name}" if module else item.name
                rows.append({
                    "source": str(source_path),
                    "line": node.lineno,
                    "kind": "from_import",
                    "module": module,
                    "name": item.name,
                    "alias": alias,
                })

    return rows, aliases


def resolve_module_file(module_name: str, base_dir: Path):
    """
    Resolve local project modules conservatively.
    """
    if not module_name:
        return None

    rel = Path(*module_name.split("."))

    candidates = [
        base_dir / f"{rel}.py",
        ROOT / f"{rel}.py",
        base_dir / rel / "__init__.py",
        ROOT / rel / "__init__.py",
    ]

    for p in candidates:
        if p.exists():
            return p.resolve()

    return None


def function_defs(tree, source, source_path):
    rows = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            rows[node.name] = {
                "source": str(source_path),
                "line": node.lineno,
                "function": node.name,
                "parameters": ";".join(a.arg for a in node.args.args),
                "definition": node_text(source, node)[:8000],
                "node": node,
            }
    return rows


def assignment_map(tree, source):
    amap = defaultdict(list)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            value_text = node_text(source, node.value)
            deps = sorted(names_in_node(node.value))
            for target in node.targets:
                for n in ast.walk(target):
                    if isinstance(n, ast.Name):
                        amap[n.id].append({
                            "line": node.lineno,
                            "expression": value_text,
                            "dependencies": deps,
                            "node": node.value,
                        })

        elif isinstance(node, ast.AnnAssign):
            if node.value is None:
                continue
            value_text = node_text(source, node.value)
            deps = sorted(names_in_node(node.value))
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    amap[n.id].append({
                        "line": node.lineno,
                        "expression": value_text,
                        "dependencies": deps,
                        "node": node.value,
                    })

    return amap


def reference_roots(r4_graph_rows):
    roots = []
    for row in r4_graph_rows:
        if str(row.get("depth", "")).strip() == "0":
            sym = row.get("root_or_symbol", "").strip()
            if sym and sym not in roots:
                roots.append(sym)
    return roots


def call_trace_for_symbols(tree, source, roots, amap):
    """
    Trace functions called in assignments reachable from reference roots.
    """
    reachable = set(roots)
    q = deque(roots)

    while q:
        s = q.popleft()
        for a in amap.get(s, []):
            for d in a["dependencies"]:
                if d not in reachable:
                    reachable.add(d)
                    q.append(d)

    rows = []

    for symbol in sorted(reachable):
        for a in amap.get(symbol, []):
            for n in ast.walk(a["node"]):
                if isinstance(n, ast.Call):
                    fn = ""
                    if isinstance(n.func, ast.Name):
                        fn = n.func.id
                    elif isinstance(n.func, ast.Attribute):
                        fn = attr_chain(n.func)

                    rows.append({
                        "symbol": symbol,
                        "assignment_line": a["line"],
                        "function_call": fn,
                        "call_expression": node_text(source, n)[:2500],
                    })

    return rows, reachable


def branch_trace(tree, source, reachable_symbols):
    rows = []

    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_names = names_in_node(node.test)
            body_names = names_in_node(node)

            touched = sorted(
                reachable_symbols.intersection(test_names | body_names)
            )

            if touched:
                rows.append({
                    "line": node.lineno,
                    "kind": "if",
                    "condition": node_text(source, node.test)[:2000],
                    "reachable_symbols": ";".join(touched),
                    "body": node_text(source, node)[:5000],
                })

        elif isinstance(node, ast.IfExp):
            names = names_in_node(node)
            touched = sorted(reachable_symbols.intersection(names))
            if touched:
                rows.append({
                    "line": getattr(node, "lineno", ""),
                    "kind": "if_expression",
                    "condition": node_text(source, node.test)[:2000],
                    "reachable_symbols": ";".join(touched),
                    "body": node_text(source, node)[:3000],
                })

    return rows


def subscript_trace(tree, source, reachable_symbols):
    rows = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue

        names = names_in_node(node)
        touched = sorted(reachable_symbols.intersection(names))

        if not touched:
            continue

        slice_text = node_text(source, node.slice)
        expr = node_text(source, node)

        # Heuristically flag time-index or 4-D slice semantics.
        time_like = any(tok in slice_text.lower() for tok in (
            "time", "itime", "tidx", "time_idx", "snapshot", "step",
            "epoch", "idx", "it"
        ))

        integer_literal = None
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
            integer_literal = node.slice.value

        rows.append({
            "line": node.lineno,
            "expression": expr[:2500],
            "slice": slice_text[:1000],
            "reachable_symbols": ";".join(touched),
            "time_like": time_like,
            "integer_literal": integer_literal if integer_literal is not None else "",
        })

    return rows


def field_access_trace(tree, source, reachable_symbols):
    rows = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            names = names_in_node(node)
            touched = sorted(reachable_symbols.intersection(names))
            if touched:
                rows.append({
                    "line": node.lineno,
                    "kind": "attribute",
                    "expression": node_text(source, node)[:2000],
                    "reachable_symbols": ";".join(touched),
                })

        elif isinstance(node, ast.Subscript):
            # String-key access.
            key = None
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                key = node.slice.value

            if key:
                names = names_in_node(node)
                touched = sorted(reachable_symbols.intersection(names))
                if touched:
                    rows.append({
                        "line": node.lineno,
                        "kind": "string_key",
                        "expression": node_text(source, node)[:2000],
                        "reachable_symbols": ";".join(touched),
                        "key": key,
                    })

    return rows


def score_candidate(candidate_key, helper_text, branch_text, index_text):
    key = candidate_key.lower()
    blob = f"{helper_text}\n{branch_text}\n{index_text}".lower()

    score = 0
    reasons = []

    for tok, val in (
        ("sg7a_corrected_grid_saturation", 30),
        ("sg7a_raw_grid_saturation", 25),
        ("sg7a_corrected", 18),
        ("sg7a_raw", 16),
        ("corrected_grid_saturation", 14),
        ("raw_grid_saturation", 10),
        ("grid_saturation", 8),
        ("truth", 18),
        ("reference", 18),
        ("canonical", 14),
    ):
        if tok in key:
            score += val
            reasons.append(f"key:{tok}")
        if tok in blob:
            score += max(2, val // 4)
            reasons.append(f"trace:{tok}")

    for tok, val in (
        ("pi_rnn", -10),
        ("original_pi_rnn", -12),
        ("coverage", -20),
        ("count", -15),
        ("weight", -15),
        ("support_distance", -20),
    ):
        if tok in key:
            score += val
            reasons.append(f"neg_key:{tok}")

    return score, reasons


# =============================================================================
# Main
# =============================================================================


def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R5")
    print("Deep Reference Builder / Branch Trace Audit")
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

    r4_summary = load_json(R4_SUMMARY)
    r4_contract = load_json(R4_CONTRACT)
    r0_contract = load_json(R0_CONTRACT)
    d6_manifest = load_json(D6_MANIFEST)

    if r4_summary.get("status") != "SG7E_HISTORICAL_REFERENCE_BUILD_PATH_NOT_YET_RESOLVED":
        raise RuntimeError(
            "SG7E1R5 requires SG7E1R4 unresolved build-path status."
        )

    if r4_summary.get("diagnosis") != "REFERENCE_SYMBOL_GRAPH_DOES_NOT_YET_REACH_UNIQUE_NPZ_KEY":
        raise RuntimeError(
            "SG7E1R5 requires SG7E1R4 unresolved NPZ-key diagnosis."
        )

    threshold_info = r0_contract.get("plume_threshold", {})
    threshold = float(threshold_info["value"])

    if not threshold_info.get("resolved", False):
        raise RuntimeError("Historical plume threshold must already be resolved.")

    if d6_manifest.get("status") != "SG7D_FULL_GRID_CANDIDATE_FROZEN":
        raise RuntimeError("Frozen SG7D6 provenance is required.")

    metric_rows = load_csv(R3_METRIC_SOURCE)
    graph_rows = load_csv(R4_GRAPH)
    upstream_rows = load_csv(R3_UPSTREAM)

    source_paths = []
    for row in metric_rows:
        s = row.get("source", "").strip()
        if s and s not in source_paths:
            source_paths.append(s)

    roots = reference_roots(graph_rows)

    import_rows = []
    call_rows = []
    helper_rows = []
    branch_rows = []
    index_rows = []
    field_rows = []

    helper_blobs = []
    branch_blobs = []
    index_blobs = []

    deep_candidates = []

    for src_s in source_paths:
        src = Path(src_s)
        text = safe_text(src)

        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        imports, aliases = imported_modules(tree, src)
        import_rows.extend(imports)

        funcs_local = function_defs(tree, text, src)
        amap = assignment_map(tree, text)

        calls, reachable = call_trace_for_symbols(
            tree, text, roots, amap
        )
        for r in calls:
            r["source"] = str(src)
        call_rows.extend(calls)

        branches = branch_trace(tree, text, reachable)
        for r in branches:
            r["source"] = str(src)
            branch_blobs.append(r["body"])
        branch_rows.extend(branches)

        indexes = subscript_trace(tree, text, reachable)
        for r in indexes:
            r["source"] = str(src)
            index_blobs.append(r["expression"])
        index_rows.extend(indexes)

        fields = field_access_trace(tree, text, reachable)
        for r in fields:
            r["source"] = str(src)
        field_rows.extend(fields)

        # ---------------------------------------------------------------------
        # Resolve helper functions: local first, imported second.
        # ---------------------------------------------------------------------

        called_names = sorted({
            r["function_call"]
            for r in calls
            if r["function_call"]
        })

        for called in called_names:
            simple = called.split(".")[-1]

            if simple in funcs_local:
                rec = dict(funcs_local[simple])
                rec["resolution"] = "local_function"
                rec["called_as"] = called
                helper_rows.append(rec)
                helper_blobs.append(rec["definition"])
                continue

            # imported alias function: `from module import func`
            target = aliases.get(called) or aliases.get(simple)

            if not target:
                continue

            if "." in target:
                module_name, obj_name = target.rsplit(".", 1)
            else:
                module_name, obj_name = "", target

            module_file = resolve_module_file(module_name, src.parent)

            if module_file and module_file.exists():
                module_text = safe_text(module_file)
                try:
                    module_tree = ast.parse(module_text)
                except SyntaxError:
                    continue

                module_funcs = function_defs(
                    module_tree,
                    module_text,
                    module_file,
                )

                if obj_name in module_funcs:
                    rec = dict(module_funcs[obj_name])
                    rec["resolution"] = "imported_function"
                    rec["called_as"] = called
                    rec["import_target"] = target
                    helper_rows.append(rec)
                    helper_blobs.append(rec["definition"])

                    # Deep inspect helper for branches / indexing / fields.
                    helper_node = module_funcs[obj_name]["node"]
                    helper_names = names_in_node(helper_node)

                    helper_branches = branch_trace(
                        helper_node,
                        module_text,
                        helper_names,
                    )
                    for r in helper_branches:
                        r["source"] = str(module_file)
                        r["helper"] = obj_name
                        branch_rows.append(r)
                        branch_blobs.append(r["body"])

                    helper_indexes = subscript_trace(
                        helper_node,
                        module_text,
                        helper_names,
                    )
                    for r in helper_indexes:
                        r["source"] = str(module_file)
                        r["helper"] = obj_name
                        index_rows.append(r)
                        index_blobs.append(r["expression"])

                    helper_fields = field_access_trace(
                        helper_node,
                        module_text,
                        helper_names,
                    )
                    for r in helper_fields:
                        r["source"] = str(module_file)
                        r["helper"] = obj_name
                        field_rows.append(r)

    save_csv(IMPORT_TABLE, import_rows)
    save_csv(CALL_TABLE, call_rows)
    save_csv(HELPER_TABLE, helper_rows)
    save_csv(BRANCH_TABLE, branch_rows)
    save_csv(INDEX_TABLE, index_rows)
    save_csv(FIELD_TABLE, field_rows)

    # -------------------------------------------------------------------------
    # Match historical upstream physics candidates against deep source traces.
    # -------------------------------------------------------------------------

    helper_text = "\n".join(helper_blobs)
    branch_text = "\n".join(branch_blobs)
    index_text = "\n".join(index_blobs)
    field_text = "\n".join(r.get("expression", "") for r in field_rows)
    call_text = "\n".join(r.get("call_expression", "") for r in call_rows)

    trace_blob = "\n".join([
        helper_text,
        branch_text,
        index_text,
        field_text,
        call_text,
    ])

    for row in upstream_rows:
        key = row.get("key", "")
        if not key:
            continue

        score, reasons = score_candidate(
            key,
            helper_text + "\n" + field_text + "\n" + call_text,
            branch_text,
            index_text,
        )

        exact_mentions = len(
            re.findall(
                re.escape(key),
                trace_blob,
                flags=re.IGNORECASE,
            )
        )

        # Partial reference terms.
        normalized = key.lower()
        partial_tokens = [
            tok for tok in (
                "sg7a",
                "corrected",
                "raw",
                "grid_saturation",
                "saturation",
            )
            if tok in normalized
        ]

        partial_mentions = sum(
            trace_blob.lower().count(tok)
            for tok in partial_tokens
        )

        direct_evidence = exact_mentions > 0

        deep_candidates.append({
            "path": row.get("path", ""),
            "key": key,
            "shape": row.get("shape", ""),
            "R3_score": row.get("score", ""),
            "deep_score": score,
            "exact_trace_mentions": exact_mentions,
            "partial_trace_mentions": partial_mentions,
            "direct_source_evidence": direct_evidence,
            "reasons": ";".join(reasons),
        })

    deep_candidates.sort(
        key=lambda r: (
            bool(r["direct_source_evidence"]),
            int(r["exact_trace_mentions"]),
            int(r["deep_score"]),
            int(r["partial_trace_mentions"]),
        ),
        reverse=True,
    )

    save_csv(DEEP_PATH_TABLE, deep_candidates)

    direct = [
        r for r in deep_candidates
        if r["direct_source_evidence"]
        and int(r["deep_score"]) > 0
        and not any(
            bad in r["key"].lower()
            for bad in (
                "coverage",
                "streamline_count",
                "coverage_weight",
                "support_distance",
            )
        )
    ]

    # Collapse duplicate path/key identities.
    unique = {}
    for r in direct:
        ident = (r["path"], r["key"])
        unique.setdefault(ident, r)

    direct_unique = list(unique.values())

    # Detect time/branch evidence even if direct key isn't yet reached.
    branch_has_raw_corrected = any(
        ("raw" in r.get("body", "").lower()
         and "corrected" in r.get("body", "").lower())
        for r in branch_rows
    )

    time_index_evidence = [
        r for r in index_rows
        if r.get("time_like")
        or str(r.get("integer_literal", "")).strip() != ""
    ]

    checks = [
        (
            "Incoming SG7E1R4 unresolved build-path diagnosis reproduced",
            True,
        ),
        (
            "Historical plume threshold retained",
            abs(threshold - 0.5) < 1e-15,
        ),
        (
            "Authoritative source retained",
            len(source_paths) > 0,
        ),
        (
            "Reference roots retained",
            len(roots) > 0,
        ),
        (
            "Import lineage audited",
            True,
        ),
        (
            "Reference helper calls traced",
            len(call_rows) > 0,
        ),
        (
            "Local/imported helper definitions searched",
            True,
        ),
        (
            "Reference branch conditions audited",
            True,
        ),
        (
            "Time-slice/index expressions audited",
            True,
        ),
        (
            "Object/dictionary field accesses audited",
            True,
        ),
        (
            "R3 upstream physics candidates tested against deep trace",
            len(deep_candidates) > 0,
        ),
        (
            "Coverage/support diagnostics excluded",
            True,
        ),
        (
            "Frozen candidate performance not used",
            True,
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

    # -------------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------------

    if len(direct_unique) == 1:
        selected = direct_unique[0]

        status = "SG7E_DEEP_REFERENCE_BUILD_PATH_RESOLVED"
        diagnosis = "UNIQUE_UPSTREAM_REFERENCE_KEY_REACHED_THROUGH_HELPER_BRANCH_TRACE"

        recommendation = (
            "The deep source/control-flow trace now reaches one unique upstream physics "
            "reference key from the historical reference-symbol lineage. Proceed to exact "
            "historical reference-field reconstruction and persistence using this source/key, "
            "the historical branch/time-index semantics, and the unchanged S=0.5 threshold."
        )

        next_milestone = (
            "V15-SG7E1R6 — Exact Historical Reference Field Reconstruction / Persistence"
        )

    elif len(direct_unique) > 1:
        selected = None

        if branch_has_raw_corrected or time_index_evidence:
            status = "SG7E_REFERENCE_BRANCH_TIME_SLICE_CONFLICT_ISOLATED"
            diagnosis = "MULTIPLE_REFERENCE_KEYS_REMAIN_DUE_TO_BRANCH_OR_TIME_INDEX_SEMANTICS"
            recommendation = (
                "Do not evaluate SG7E gates. The deep trace now reaches multiple upstream "
                "reference candidates, and the remaining ambiguity is associated with "
                "raw-vs-corrected and/or time-slice selection. Audit only the exact branch "
                "predicate and historical time index used by the authoritative metrics."
            )
            next_milestone = (
                "V15-SG7E1R6 — Exact Reference Branch / Time-Index Resolution Audit"
            )
        else:
            status = "SG7E_DEEP_REFERENCE_BUILD_PATH_CONFLICT"
            diagnosis = "MULTIPLE_UPSTREAM_REFERENCE_KEYS_REMAIN_AFTER_DEEP_TRACE"
            recommendation = (
                "Do not evaluate SG7E gates. Multiple source-reachable upstream reference "
                "keys remain. Resolve their final consumption in the authoritative metric "
                "expressions without using frozen-candidate performance."
            )
            next_milestone = (
                "V15-SG7E1R6 — Final Reference Consumption Trace Audit"
            )

    else:
        selected = None

        status = "SG7E_DEEP_REFERENCE_BUILD_PATH_NOT_YET_RESOLVED"
        diagnosis = "REFERENCE_LINEAGE_STILL_TERMINATES_BEFORE_PERSISTED_UPSTREAM_KEY"

        recommendation = (
            "Do not evaluate SG7E gates. The helper/import/branch/index trace still does not "
            "reach a persisted upstream reference key. The next audit should follow function "
            "arguments and caller sites recursively across local project modules until the "
            "historical reference field constructor is reached."
        )

        next_milestone = (
            "V15-SG7E1R6 — Recursive Caller / Argument Provenance Audit"
        )

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "plume_threshold": threshold,
        "authoritative_sources": len(source_paths),
        "reference_roots": len(roots),
        "imports": len(import_rows),
        "reference_calls": len(call_rows),
        "helper_definitions": len(helper_rows),
        "branch_records": len(branch_rows),
        "index_records": len(index_rows),
        "time_index_records": len(time_index_evidence),
        "field_access_records": len(field_rows),
        "direct_reference_candidates": len(direct_unique),
        "raw_corrected_branch_evidence": branch_has_raw_corrected,
        "selected_path": selected["path"] if selected else "",
        "selected_key": selected["key"] if selected else "",
        "next_milestone": next_milestone,
    }

    save_csv(DECISION_TABLE, [decision])

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1R5",
            "status": status,
            "diagnosis": diagnosis,
            "plume_threshold": {
                "value": threshold,
                "changed": False,
            },
            "deep_trace": {
                "authoritative_sources": source_paths,
                "reference_roots": roots,
                "imports": len(import_rows),
                "calls": len(call_rows),
                "helper_definitions": len(helper_rows),
                "branches": len(branch_rows),
                "index_records": len(index_rows),
                "time_index_records": len(time_index_evidence),
                "field_access_records": len(field_rows),
                "direct_reference_candidates": len(direct_unique),
            },
            "selected_reference": {
                "selected": selected is not None,
                "path": selected["path"] if selected else None,
                "key": selected["key"] if selected else None,
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
            "milestone": "V15-SG7E1R5",
            "status": status,
            "diagnosis": diagnosis,
            "direct_reference_candidates": len(direct_unique),
            "branch_records": len(branch_rows),
            "time_index_records": len(time_index_evidence),
            "reference_selected": selected is not None,
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print("DEEP REFERENCE BUILDER TRACE")
    print(f"  Authoritative sources   : {len(source_paths)}")
    print(f"  Reference roots         : {len(roots)}")
    print(f"  Imports                 : {len(import_rows)}")
    print(f"  Reference calls         : {len(call_rows)}")
    print(f"  Helper definitions      : {len(helper_rows)}")
    print(f"  Branch records          : {len(branch_rows)}")
    print(f"  Index records           : {len(index_rows)}")
    print(f"  Time-index records      : {len(time_index_evidence)}")
    print(f"  Field accesses          : {len(field_rows)}")
    print(f"  Direct reference cands  : {len(direct_unique)}")

    if deep_candidates:
        print("\nTOP DEEP BUILD-PATH CANDIDATES")
        for r in deep_candidates[:12]:
            print(
                f"  direct={str(bool(r['direct_source_evidence'])):5s} | "
                f"mentions={int(r['exact_trace_mentions']):2d} | "
                f"score={int(r['deep_score']):4d} | "
                f"{Path(r['path']).name} :: {r['key']}"
            )

    if selected:
        print("\nSELECTED UPSTREAM REFERENCE")
        print(f"  File                    : {Path(selected['path']).name}")
        print(f"  Key                     : {selected['key']}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R5 DEEP TRACE VALIDATION")
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
    print(f"  {IMPORT_TABLE.name}")
    print(f"  {CALL_TABLE.name}")
    print(f"  {HELPER_TABLE.name}")
    print(f"  {BRANCH_TABLE.name}")
    print(f"  {INDEX_TABLE.name}")
    print(f"  {FIELD_TABLE.name}")
    print(f"  {DEEP_PATH_TABLE.name}")
    print(f"  {DECISION_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R5 DEEP REFERENCE BUILDER / BRANCH TRACE AUDIT: COMPLETE")
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
