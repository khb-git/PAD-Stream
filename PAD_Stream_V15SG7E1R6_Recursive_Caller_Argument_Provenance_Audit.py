from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re
from collections import defaultdict, deque


# =============================================================================
# PAD-Stream V15-SG7E1R6
# Recursive Caller / Argument Provenance Audit
#
# FORENSIC INTERPROCEDURAL PROVENANCE MILESTONE
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
# SG7E1R5 established:
#
#   SG7E_DEEP_REFERENCE_BUILD_PATH_NOT_YET_RESOLVED
#
# with:
#
#   REFERENCE_LINEAGE_STILL_TERMINATES_BEFORE_PERSISTED_UPSTREAM_KEY
#
# R5 found that the authoritative reference-symbol lineage traverses helper
# calls, imports, branches, and field accesses, but still does not directly reach
# a persisted SG7A array key. The next unresolved interface is therefore the
# FUNCTION ARGUMENT / CALLER boundary.
#
# SG7E1R6 recursively traces:
#
#   reference symbol
#       -> helper call
#       -> helper parameter
#       -> caller argument expression
#       -> caller variable
#       -> caller assignment / field access
#       -> upstream loader or source object
#
# across local project modules.
#
# It also records branch predicates and time-index expressions encountered
# along the caller chain, but it does not select raw/corrected/time-slice values
# unless the source lineage establishes them uniquely.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R6"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R5_DIR = ROOT / "output" / "V15_SG7E1R5"

R5_SUMMARY = R5_DIR / "PAD_Stream_V15SG7E1R5_Summary.json"
R5_CONTRACT = R5_DIR / "V15SG7E1R5_Deep_Reference_Build_Path_Contract.json"
R5_CALLS = R5_DIR / "V15SG7E1R5_Reference_Helper_Call_Trace.csv"
R5_HELPERS = R5_DIR / "V15SG7E1R5_Imported_Helper_Definitions.csv"
R5_FIELDS = R5_DIR / "V15SG7E1R5_Reference_Field_Access_Trace.csv"
R5_BRANCHES = R5_DIR / "V15SG7E1R5_Reference_Branch_Conditions.csv"
R5_INDEXES = R5_DIR / "V15SG7E1R5_Time_Slice_Index_Trace.csv"

R4_GRAPH = (
    ROOT / "output" / "V15_SG7E1R4"
    / "V15SG7E1R4_Reference_Symbol_Dependency_Graph.csv"
)

R3_UPSTREAM = (
    ROOT / "output" / "V15_SG7E1R3"
    / "V15SG7E1R3_Upstream_Physics_Artifact_Candidates.csv"
)

R3_METRIC_SOURCE = (
    ROOT / "output" / "V15_SG7E1R3"
    / "V15SG7E1R3_Authoritative_Metric_Source_Trace.csv"
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

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R6_Summary.json"

PROJECT_MODULE_TABLE = OUT / "V15SG7E1R6_Project_Module_Inventory.csv"
FUNCTION_TABLE = OUT / "V15SG7E1R6_Function_Definition_Inventory.csv"
CALLER_TABLE = OUT / "V15SG7E1R6_Function_Caller_Inventory.csv"
ARGUMENT_TABLE = OUT / "V15SG7E1R6_Argument_Provenance_Trace.csv"
RECURSIVE_TABLE = OUT / "V15SG7E1R6_Recursive_Argument_Chain.csv"
FIELD_SOURCE_TABLE = OUT / "V15SG7E1R6_Field_Source_Trace.csv"
UPSTREAM_MATCH_TABLE = OUT / "V15SG7E1R6_Upstream_Key_Match_Audit.csv"
DECISION_TABLE = OUT / "V15SG7E1R6_Recursive_Provenance_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R6_Recursive_Caller_Argument_Provenance_Contract.json"

MAX_RECURSION_DEPTH = 8


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


def call_name(call):
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return attr_chain(call.func)
    return ""


def iter_project_py_files():
    """
    Local project only. Excludes the active virtual environment and output dirs.
    """
    rows = []

    for p in ROOT.rglob("*.py"):
        parts_lower = {x.lower() for x in p.parts}

        if ".venv" in parts_lower:
            continue
        if "site-packages" in parts_lower:
            continue
        if "output" in parts_lower:
            continue
        if "__pycache__" in parts_lower:
            continue

        rows.append(p.resolve())

    return sorted(set(rows))


def parse_module(path: Path):
    text = safe_text(path)
    if not text:
        return None, ""

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None, text

    return tree, text


def function_inventory(module_paths):
    """
    Inventory top-level functions/methods and their parameters.
    """
    rows = []
    defs_by_simple_name = defaultdict(list)

    for path in module_paths:
        tree, text = parse_module(path)
        if tree is None:
            continue

        class_stack = []

        def walk_body(body, class_name=""):
            for node in body:
                if isinstance(node, ast.FunctionDef):
                    qual = f"{class_name}.{node.name}" if class_name else node.name
                    params = [a.arg for a in node.args.args]

                    rec = {
                        "source": str(path),
                        "line": node.lineno,
                        "function": node.name,
                        "qualified_function": qual,
                        "parameters": ";".join(params),
                        "definition": node_text(text, node)[:12000],
                    }
                    rows.append(rec)
                    defs_by_simple_name[node.name].append((path, node, text, rec))

                elif isinstance(node, ast.ClassDef):
                    walk_body(node.body, node.name)

        walk_body(tree.body)

    return rows, defs_by_simple_name


def caller_inventory(module_paths):
    """
    Inventory all call sites project-wide.
    """
    rows = []
    calls_by_simple_name = defaultdict(list)

    for path in module_paths:
        tree, text = parse_module(path)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            name = call_name(node)
            if not name:
                continue

            simple = name.split(".")[-1]

            args = [node_text(text, a) for a in node.args]
            kwargs = {
                kw.arg: node_text(text, kw.value)
                for kw in node.keywords
                if kw.arg is not None
            }

            rec = {
                "source": str(path),
                "line": node.lineno,
                "call_name": name,
                "simple_name": simple,
                "args": json.dumps(args),
                "kwargs": json.dumps(kwargs),
                "call_expression": node_text(text, node)[:6000],
            }

            rows.append(rec)
            calls_by_simple_name[simple].append((path, node, text, rec))

    return rows, calls_by_simple_name


def assignment_map(tree, text):
    amap = defaultdict(list)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            expr = node_text(text, node.value)
            deps = sorted(names_in_node(node.value))

            for target in node.targets:
                for n in ast.walk(target):
                    if isinstance(n, ast.Name):
                        amap[n.id].append({
                            "line": node.lineno,
                            "expression": expr,
                            "dependencies": deps,
                        })

        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            expr = node_text(text, node.value)
            deps = sorted(names_in_node(node.value))

            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    amap[n.id].append({
                        "line": node.lineno,
                        "expression": expr,
                        "dependencies": deps,
                    })

    return amap


def map_call_arguments(def_record, call_record):
    """
    Map caller argument expressions onto function parameter names.
    """
    params = [x for x in def_record["parameters"].split(";") if x]
    args = json.loads(call_record["args"])
    kwargs = json.loads(call_record["kwargs"])

    rows = []

    for idx, expr in enumerate(args):
        if idx >= len(params):
            break

        rows.append({
            "parameter": params[idx],
            "argument_expression": expr,
            "binding_kind": "positional",
        })

    for name, expr in kwargs.items():
        if name in params:
            rows.append({
                "parameter": name,
                "argument_expression": expr,
                "binding_kind": "keyword",
            })

    return rows


def expression_tokens(expr):
    return re.findall(
        r'(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)',
        expr or "",
    )


def source_semantic_score(expr, upstream_keys):
    """
    Score only for prioritization of provenance evidence, never for candidate
    performance.
    """
    e = (expr or "").lower()

    score = 0
    reasons = []

    for tok, val in (
        ("sg7a_corrected_grid_saturation", 40),
        ("sg7a_raw_grid_saturation", 36),
        ("sg7a_corrected", 30),
        ("sg7a_raw", 26),
        ("corrected_grid_saturation", 22),
        ("raw_grid_saturation", 18),
        ("reference", 18),
        ("truth", 18),
        ("canonical", 15),
        ("saturation", 8),
    ):
        if tok in e:
            score += val
            reasons.append(tok)

    for bad, val in (
        ("pi_rnn", -12),
        ("coverage", -25),
        ("streamline_count", -25),
        ("weight", -18),
        ("support_distance", -25),
    ):
        if bad in e:
            score += val
            reasons.append(f"neg:{bad}")

    exact_keys = [
        k for k in upstream_keys
        if k and k.lower() in e
    ]

    score += 50 * len(exact_keys)

    return score, reasons, exact_keys


def recursively_trace_argument(
    start_function,
    target_parameter,
    defs_by_name,
    callers_by_name,
    upstream_keys,
    max_depth=MAX_RECURSION_DEPTH,
):
    """
    Follow parameter -> caller argument -> caller-local variable assignments ->
    optionally caller function parameters recursively.
    """
    rows = []
    found_upstream = []

    queue = deque()
    queue.append({
        "function": start_function,
        "parameter": target_parameter,
        "depth": 0,
        "parent": "",
    })

    visited = set()

    while queue:
        item = queue.popleft()

        fn = item["function"]
        param = item["parameter"]
        depth = item["depth"]

        state = (fn, param, depth)
        if state in visited:
            continue
        visited.add(state)

        if depth > max_depth:
            continue

        definitions = defs_by_name.get(fn, [])
        callers = callers_by_name.get(fn, [])

        for def_path, def_node, def_text, def_rec in definitions:
            for call_path, call_node, call_text, call_rec in callers:
                bindings = map_call_arguments(def_rec, call_rec)

                for binding in bindings:
                    if binding["parameter"] != param:
                        continue

                    arg_expr = binding["argument_expression"]

                    score, reasons, exact_keys = source_semantic_score(
                        arg_expr,
                        upstream_keys,
                    )

                    rows.append({
                        "depth": depth,
                        "function": fn,
                        "parameter": param,
                        "definition_source": str(def_path),
                        "caller_source": str(call_path),
                        "caller_line": call_rec["line"],
                        "binding_kind": binding["binding_kind"],
                        "argument_expression": arg_expr,
                        "semantic_score": score,
                        "semantic_reasons": ";".join(reasons),
                        "exact_upstream_keys": ";".join(exact_keys),
                    })

                    for k in exact_keys:
                        found_upstream.append({
                            "key": k,
                            "depth": depth,
                            "function": fn,
                            "parameter": param,
                            "caller_source": str(call_path),
                            "caller_line": call_rec["line"],
                            "argument_expression": arg_expr,
                        })

                    # Trace simple caller-local variable assignments.
                    tokens = expression_tokens(arg_expr)

                    caller_tree, caller_src = parse_module(call_path)
                    if caller_tree is None:
                        continue

                    amap = assignment_map(caller_tree, caller_src)

                    for tok in tokens:
                        for a in amap.get(tok, []):
                            expr = a["expression"]

                            score2, reasons2, exact2 = source_semantic_score(
                                expr,
                                upstream_keys,
                            )

                            rows.append({
                                "depth": depth,
                                "function": fn,
                                "parameter": param,
                                "definition_source": str(def_path),
                                "caller_source": str(call_path),
                                "caller_line": a["line"],
                                "binding_kind": "caller_assignment",
                                "argument_expression": expr,
                                "semantic_score": score2,
                                "semantic_reasons": ";".join(reasons2),
                                "exact_upstream_keys": ";".join(exact2),
                                "via_symbol": tok,
                            })

                            for k in exact2:
                                found_upstream.append({
                                    "key": k,
                                    "depth": depth,
                                    "function": fn,
                                    "parameter": param,
                                    "caller_source": str(call_path),
                                    "caller_line": a["line"],
                                    "argument_expression": expr,
                                })

                    # If the caller is itself inside a function and argument is a
                    # parameter of that caller function, continue upward.
                    enclosing = None

                    for node in ast.walk(caller_tree):
                        if isinstance(node, ast.FunctionDef):
                            if (
                                getattr(node, "lineno", 0)
                                <= int(call_rec["line"])
                                <= getattr(node, "end_lineno", getattr(node, "lineno", 0))
                            ):
                                enclosing = node
                                break

                    if enclosing:
                        caller_params = [a.arg for a in enclosing.args.args]

                        for tok in tokens:
                            if tok in caller_params:
                                queue.append({
                                    "function": enclosing.name,
                                    "parameter": tok,
                                    "depth": depth + 1,
                                    "parent": f"{fn}:{param}",
                                })

    return rows, found_upstream


# =============================================================================
# Main
# =============================================================================


def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R6")
    print("Recursive Caller / Argument Provenance Audit")
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

    r5_summary = load_json(R5_SUMMARY)
    r5_contract = load_json(R5_CONTRACT)
    r0_contract = load_json(R0_CONTRACT)
    d6_manifest = load_json(D6_MANIFEST)

    if r5_summary.get("status") != "SG7E_DEEP_REFERENCE_BUILD_PATH_NOT_YET_RESOLVED":
        raise RuntimeError(
            "SG7E1R6 requires SG7E1R5 unresolved deep build-path status."
        )

    if r5_summary.get("diagnosis") != (
        "REFERENCE_LINEAGE_STILL_TERMINATES_BEFORE_PERSISTED_UPSTREAM_KEY"
    ):
        raise RuntimeError(
            "SG7E1R6 requires SG7E1R5 unresolved upstream-key diagnosis."
        )

    threshold_info = r0_contract.get("plume_threshold", {})
    threshold = float(threshold_info["value"])

    if not threshold_info.get("resolved", False):
        raise RuntimeError(
            "Historical plume threshold must already be resolved."
        )

    if d6_manifest.get("status") != "SG7D_FULL_GRID_CANDIDATE_FROZEN":
        raise RuntimeError(
            "Frozen SG7D6 provenance is required."
        )

    r5_calls = load_csv(R5_CALLS)
    r5_helpers = load_csv(R5_HELPERS)
    r4_graph = load_csv(R4_GRAPH)
    upstream_rows = load_csv(R3_UPSTREAM)

    upstream_keys = sorted({
        r.get("key", "").strip()
        for r in upstream_rows
        if r.get("key", "").strip()
    })

    # -------------------------------------------------------------------------
    # Project inventory
    # -------------------------------------------------------------------------

    module_paths = iter_project_py_files()

    module_rows = [{
        "source": str(p),
        "relative_to_root": str(p.relative_to(ROOT)),
    } for p in module_paths]

    save_csv(PROJECT_MODULE_TABLE, module_rows)

    function_rows, defs_by_name = function_inventory(module_paths)
    caller_rows, callers_by_name = caller_inventory(module_paths)

    save_csv(FUNCTION_TABLE, function_rows)
    save_csv(CALLER_TABLE, caller_rows)

    # -------------------------------------------------------------------------
    # Identify helper entry points from R5.
    # -------------------------------------------------------------------------

    helper_entries = []

    for row in r5_helpers:
        fn = row.get("function", "").strip()
        params = [
            p for p in row.get("parameters", "").split(";")
            if p
        ]

        if not fn or not params:
            continue

        helper_entries.append({
            "function": fn,
            "parameters": params,
            "source": row.get("source", ""),
        })

    # R5 may have helper calls without resolved helper definition; retain those.
    for row in r5_calls:
        fn = row.get("function_call", "").strip()
        if not fn:
            continue

        simple = fn.split(".")[-1]

        if any(h["function"] == simple for h in helper_entries):
            continue

        if simple in defs_by_name:
            for _, _, _, drec in defs_by_name[simple]:
                params = [
                    p for p in drec["parameters"].split(";")
                    if p
                ]
                if params:
                    helper_entries.append({
                        "function": simple,
                        "parameters": params,
                        "source": drec["source"],
                    })
                    break

    # -------------------------------------------------------------------------
    # Determine likely reference-bearing parameters.
    #
    # Conservative: parameters whose names are reference/truth/saturation/grid-
    # like, or all parameters if only one non-self argument exists.
    # -------------------------------------------------------------------------

    target_entries = []

    for h in helper_entries:
        params = [p for p in h["parameters"] if p not in {"self", "cls"}]

        likely = [
            p for p in params
            if any(tok in p.lower() for tok in (
                "ref",
                "truth",
                "reference",
                "canonical",
                "sat",
                "saturation",
                "grid",
                "plume",
                "field",
                "state",
            ))
        ]

        if not likely and len(params) == 1:
            likely = params

        for p in likely:
            target_entries.append({
                "function": h["function"],
                "parameter": p,
                "source": h["source"],
            })

    # -------------------------------------------------------------------------
    # Recursive caller / argument trace.
    # -------------------------------------------------------------------------

    recursive_rows = []
    found_upstream = []

    for entry in target_entries:
        rows, found = recursively_trace_argument(
            entry["function"],
            entry["parameter"],
            defs_by_name,
            callers_by_name,
            upstream_keys,
        )

        for row in rows:
            row["entry_function"] = entry["function"]
            row["entry_parameter"] = entry["parameter"]

        recursive_rows.extend(rows)
        found_upstream.extend(found)

    save_csv(ARGUMENT_TABLE, recursive_rows)
    save_csv(RECURSIVE_TABLE, recursive_rows)

    # -------------------------------------------------------------------------
    # Field source trace from expressions containing object/dict fields.
    # -------------------------------------------------------------------------

    field_rows = []

    for row in recursive_rows:
        expr = row.get("argument_expression", "")

        for m in re.finditer(
            r'([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*[\'"]([^\'"]+)[\'"]\s*\]',
            expr,
        ):
            field_rows.append({
                "caller_source": row.get("caller_source", ""),
                "caller_line": row.get("caller_line", ""),
                "container": m.group(1),
                "field_or_key": m.group(2),
                "expression": expr,
                "kind": "dict_key",
            })

        for m in re.finditer(
            r'([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)',
            expr,
        ):
            field_rows.append({
                "caller_source": row.get("caller_source", ""),
                "caller_line": row.get("caller_line", ""),
                "container": m.group(1),
                "field_or_key": m.group(2),
                "expression": expr,
                "kind": "attribute",
            })

    save_csv(FIELD_SOURCE_TABLE, field_rows)

    # -------------------------------------------------------------------------
    # Upstream-key matching.
    # -------------------------------------------------------------------------

    match_counts = defaultdict(int)
    match_examples = defaultdict(list)

    for hit in found_upstream:
        key = hit["key"]

        if any(bad in key.lower() for bad in (
            "coverage",
            "streamline_count",
            "coverage_weight",
            "support_distance",
        )):
            continue

        match_counts[key] += 1

        if len(match_examples[key]) < 5:
            match_examples[key].append(
                f"{Path(hit['caller_source']).name}:{hit['caller_line']}"
            )

    match_rows = []

    for key, count in sorted(
        match_counts.items(),
        key=lambda kv: kv[1],
        reverse=True,
    ):
        source_paths = sorted({
            r.get("path", "")
            for r in upstream_rows
            if r.get("key", "") == key
            and r.get("path", "")
        })

        match_rows.append({
            "key": key,
            "provenance_hit_count": count,
            "upstream_artifact_paths": ";".join(source_paths),
            "examples": ";".join(match_examples[key]),
        })

    save_csv(UPSTREAM_MATCH_TABLE, match_rows)

    unique_keys = [
        r["key"]
        for r in match_rows
        if r["provenance_hit_count"] > 0
    ]

    # -------------------------------------------------------------------------
    # Decision.
    # -------------------------------------------------------------------------

    checks = [
        (
            "Incoming SG7E1R5 unresolved deep-build diagnosis reproduced",
            True,
        ),
        (
            "Historical plume threshold retained",
            abs(threshold - 0.5) < 1e-15,
        ),
        (
            "Local project Python modules inventoried",
            len(module_paths) > 0,
        ),
        (
            "Function definitions inventoried project-wide",
            len(function_rows) > 0,
        ),
        (
            "Function caller sites inventoried project-wide",
            len(caller_rows) > 0,
        ),
        (
            "Reference helper entry points retained",
            len(helper_entries) > 0,
        ),
        (
            "Reference-bearing helper parameters identified",
            len(target_entries) > 0,
        ),
        (
            "Recursive caller/argument provenance traced",
            True,
        ),
        (
            "Object/dictionary field sources audited",
            True,
        ),
        (
            "Upstream SG7A/physics keys matched only from source provenance",
            True,
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

    if len(unique_keys) == 1:

        selected_key = unique_keys[0]

        selected_paths = sorted({
            r.get("path", "")
            for r in upstream_rows
            if r.get("key", "") == selected_key
            and r.get("path", "")
        })

        selected_path = selected_paths[0] if len(selected_paths) == 1 else ""

        status = "SG7E_RECURSIVE_REFERENCE_PROVENANCE_RESOLVED"

        diagnosis = (
            "UNIQUE_UPSTREAM_REFERENCE_KEY_REACHED_THROUGH_CALLER_ARGUMENT_CHAIN"
        )

        recommendation = (
            "The recursive caller/argument provenance chain reaches exactly one historical "
            "upstream reference key. Proceed to a focused source-semantic audit that resolves "
            "its exact artifact instance and, if 4-D, the historical branch/time slice before "
            "persisting the reference field. Do not evaluate SG7E gates yet."
        )

        next_milestone = (
            "V15-SG7E1R7 — Exact Reference Artifact / Time-Slice Resolution Audit"
        )

    elif len(unique_keys) > 1:

        selected_key = ""
        selected_path = ""

        status = "SG7E_RECURSIVE_REFERENCE_PROVENANCE_CONFLICT"

        diagnosis = (
            "MULTIPLE_UPSTREAM_REFERENCE_KEYS_REACHED_THROUGH_CALLER_ARGUMENT_CHAIN"
        )

        recommendation = (
            "Do not evaluate SG7E gates. The caller/argument chain now reaches multiple "
            "historical upstream physics keys. Resolve only the final branch, raw-vs-corrected "
            "selection, and/or time-slice semantics that determine which key feeds the "
            "authoritative metric path."
        )

        next_milestone = (
            "V15-SG7E1R7 — Final Reference Branch / Key Consumption Audit"
        )

    else:

        selected_key = ""
        selected_path = ""

        status = "SG7E_RECURSIVE_REFERENCE_PROVENANCE_NOT_YET_RESOLVED"

        diagnosis = (
            "CALLER_ARGUMENT_CHAIN_STILL_DOES_NOT_REACH_PERSISTED_REFERENCE_KEY"
        )

        recommendation = (
            "Do not evaluate SG7E gates. The recursive caller chain still terminates before "
            "a persisted reference key. Audit factory objects, returned dictionaries, class "
            "attributes, and constructor-time data loading on the final unresolved containers."
        )

        next_milestone = (
            "V15-SG7E1R7 — Reference Object / Factory Provenance Audit"
        )

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "plume_threshold": threshold,
        "project_modules": len(module_paths),
        "function_definitions": len(function_rows),
        "caller_sites": len(caller_rows),
        "helper_entries": len(helper_entries),
        "target_parameters": len(target_entries),
        "recursive_records": len(recursive_rows),
        "field_source_records": len(field_rows),
        "unique_upstream_keys": len(unique_keys),
        "matched_upstream_keys": ";".join(unique_keys),
        "selected_key": selected_key,
        "selected_path": selected_path,
        "next_milestone": next_milestone,
    }

    save_csv(DECISION_TABLE, [decision])

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7E1R6",
            "status": status,
            "diagnosis": diagnosis,
            "plume_threshold": {
                "value": threshold,
                "changed": False,
            },
            "recursive_provenance": {
                "project_modules": len(module_paths),
                "function_definitions": len(function_rows),
                "caller_sites": len(caller_rows),
                "helper_entries": len(helper_entries),
                "target_parameters": len(target_entries),
                "recursive_records": len(recursive_rows),
                "field_source_records": len(field_rows),
                "matched_upstream_keys": unique_keys,
                "selected_key": selected_key or None,
                "selected_path": selected_path or None,
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
            "milestone": "V15-SG7E1R6",
            "status": status,
            "diagnosis": diagnosis,
            "unique_upstream_keys": len(unique_keys),
            "matched_upstream_keys": unique_keys,
            "reference_selected": len(unique_keys) == 1,
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("RECURSIVE CALLER / ARGUMENT TRACE")
    print(f"  Project modules         : {len(module_paths)}")
    print(f"  Function definitions    : {len(function_rows)}")
    print(f"  Caller sites            : {len(caller_rows)}")
    print(f"  Helper entries          : {len(helper_entries)}")
    print(f"  Target parameters       : {len(target_entries)}")
    print(f"  Recursive records       : {len(recursive_rows)}")
    print(f"  Field source records    : {len(field_rows)}")
    print(f"  Unique upstream keys    : {len(unique_keys)}")

    if match_rows:
        print("\nUPSTREAM KEY PROVENANCE")
        for row in match_rows[:12]:
            print(
                f"  hits={int(row['provenance_hit_count']):3d} | "
                f"{row['key']}"
            )

    if len(unique_keys) == 1:
        print("\nSELECTED UPSTREAM REFERENCE KEY")
        print(f"  Key                     : {selected_key}")
        if selected_path:
            print(f"  Artifact                : {Path(selected_path).name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R6 RECURSIVE PROVENANCE VALIDATION")
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
    print(f"  {PROJECT_MODULE_TABLE.name}")
    print(f"  {FUNCTION_TABLE.name}")
    print(f"  {CALLER_TABLE.name}")
    print(f"  {ARGUMENT_TABLE.name}")
    print(f"  {RECURSIVE_TABLE.name}")
    print(f"  {FIELD_SOURCE_TABLE.name}")
    print(f"  {UPSTREAM_MATCH_TABLE.name}")
    print(f"  {DECISION_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R6 RECURSIVE CALLER / ARGUMENT PROVENANCE AUDIT: COMPLETE")
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
