from __future__ import annotations

from pathlib import Path
import ast
import csv
import json
import re


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R1
# Missing X100 Component Binding / Deployment-Object Constructor Audit
#
# DIAGNOSTIC-ONLY PROVENANCE MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA RECALIBRATION.
# NO CROSSING-GUARD CHANGE.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
#
# PURPOSE
# -------
# R26I-R established:
#
#   SG7B10_DEPLOYMENT_X100_CONSTRUCTION_CONTRACT_STILL_INCOMPLETE
#
# with:
#
#   deployment["X100"] subscript assignments   = 0
#   deployment dictionary X100 entries         = 0
#
# Therefore X100 is not constructed directly in the authoritative SG7B10
# source body. The `deployment` object itself must be created or returned by
# an upstream helper / imported constructor / loader.
#
# R26I-R1 traces:
#
#   assignment of `deployment`
#       -> constructor/helper call
#       -> helper function definition
#       -> returned dictionary/object
#       -> exact X100 construction expression
#       -> upstream source/module lineage
#
# This milestone does not search for an alternative evaluator. SG7B10 remains
# authoritative. It only follows the data-construction branch feeding SG7B10.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR1"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"

R26IR2_DIR = ROOT / "output" / "V15_SG7E1R26IR2"
R26IR2_SUMMARY = R26IR2_DIR / "PAD_Stream_V15SG7E1R26IR2_Summary.json"

# Outputs
DEPLOYMENT_ASSIGN = OUT / "V15SG7E1R26IR1_Deployment_Assignment_Trace.csv"
CALLER_TABLE = OUT / "V15SG7E1R26IR1_Deployment_Constructor_Call_Trace.csv"
IMPORT_TABLE = OUT / "V15SG7E1R26IR1_Imported_Helper_Lineage.csv"
HELPER_TABLE = OUT / "V15SG7E1R26IR1_Helper_Definition_Trace.csv"
RETURN_TABLE = OUT / "V15SG7E1R26IR1_Helper_Return_Object_Trace.csv"
X100_TABLE = OUT / "V15SG7E1R26IR1_X100_Constructor_Expression.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR1_Deployment_Constructor_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26IR1_Deployment_Object_Constructor_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR1_Summary.json"


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def save_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def safe_text(path: Path):
    return path.read_text(encoding="utf-8", errors="ignore")


def node_src(text, node):
    try:
        return ast.get_source_segment(text, node) or ""
    except Exception:
        return ""


def call_name(node):
    if not isinstance(node, ast.Call):
        return ""
    cur = node.func
    parts = []
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def import_alias_map(tree):
    """
    Maps local imported symbols / module aliases to their import origins.
    """
    aliases = {}

    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                local = a.asname or a.name.split(".")[-1]
                aliases[local] = {
                    "kind": "module",
                    "module": a.name,
                    "symbol": "",
                }

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for a in node.names:
                local = a.asname or a.name
                aliases[local] = {
                    "kind": "symbol",
                    "module": module,
                    "symbol": a.name,
                }

    return aliases


def resolve_module_path(module_name: str):
    """
    Resolve a local project module to a .py file without broadening evaluator
    authority. Only project-local modules are considered.
    """
    candidates = []

    if module_name:
        rel = Path(*module_name.split(".")).with_suffix(".py")
        candidates.append(ROOT / rel)
        candidates.append(ROOT / rel.name)

    for p in candidates:
        if p.exists():
            return p.resolve()

    return None


def local_function_map(tree):
    return {
        n.name: n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef)
    }


def find_deployment_assignments(tree, text):
    rows = []
    calls = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue

        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id == "deployment":
                rhs = node.value
                cname = call_name(rhs) if isinstance(rhs, ast.Call) else ""

                rows.append({
                    "line": node.lineno,
                    "rhs": node_src(text, rhs),
                    "rhs_type": type(rhs).__name__,
                    "call_name": cname,
                })

                if isinstance(rhs, ast.Call):
                    calls.append({
                        "line": node.lineno,
                        "call_name": cname,
                        "expression": node_src(text, rhs),
                        "arg_symbols": ";".join(sorted({
                            n.id for n in ast.walk(rhs)
                            if isinstance(n, ast.Name)
                        })),
                    })

    return rows, calls


def inspect_function_for_return_contract(path: Path, function_name: str):
    """
    Inspect a specific helper for return dictionaries/objects and X100 creation.
    """
    text = safe_text(path)
    tree = ast.parse(text)

    target = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            target = node
            break

    if target is None:
        return [], [], []

    helper_rows = [{
        "source": str(path),
        "function": function_name,
        "line": target.lineno,
        "parameters": ";".join(a.arg for a in target.args.args),
    }]

    return_rows = []
    x100_rows = []

    # Trace assignments inside helper, including dictionary/subscript writes.
    for node in ast.walk(target):
        if isinstance(node, ast.Assign):
            rhs = node.value

            # Direct subscript assignments obj["X100"] = ...
            for tgt in node.targets:
                if isinstance(tgt, ast.Subscript):
                    base = tgt.value.id if isinstance(tgt.value, ast.Name) else ""
                    key = ""
                    if isinstance(tgt.slice, ast.Constant) and isinstance(tgt.slice.value, str):
                        key = tgt.slice.value

                    if key == "X100":
                        x100_rows.append({
                            "source": str(path),
                            "function": function_name,
                            "line": node.lineno,
                            "construction_kind": "SUBSCRIPT_ASSIGNMENT",
                            "container": base,
                            "expression": node_src(text, rhs),
                            "symbols": ";".join(sorted({
                                n.id for n in ast.walk(rhs)
                                if isinstance(n, ast.Name)
                            })),
                        })

            # Dict literal assignments containing X100.
            if isinstance(rhs, ast.Dict):
                for k_node, v_node in zip(rhs.keys, rhs.values):
                    if (
                        isinstance(k_node, ast.Constant)
                        and k_node.value == "X100"
                    ):
                        target_names = []
                        for tgt in node.targets:
                            if isinstance(tgt, ast.Name):
                                target_names.append(tgt.id)

                        x100_rows.append({
                            "source": str(path),
                            "function": function_name,
                            "line": node.lineno,
                            "construction_kind": "DICT_LITERAL_ASSIGNMENT",
                            "container": ";".join(target_names),
                            "expression": node_src(text, v_node),
                            "symbols": ";".join(sorted({
                                n.id for n in ast.walk(v_node)
                                if isinstance(n, ast.Name)
                            })),
                        })

        if isinstance(node, ast.Return):
            expr = node.value
            rec = {
                "source": str(path),
                "function": function_name,
                "line": node.lineno,
                "return_expression": node_src(text, expr),
                "return_type": type(expr).__name__ if expr is not None else "None",
            }

            if isinstance(expr, ast.Dict):
                keys = []
                for k in expr.keys:
                    if isinstance(k, ast.Constant):
                        keys.append(str(k.value))
                rec["dict_keys"] = ";".join(keys)

                for k_node, v_node in zip(expr.keys, expr.values):
                    if (
                        isinstance(k_node, ast.Constant)
                        and k_node.value == "X100"
                    ):
                        x100_rows.append({
                            "source": str(path),
                            "function": function_name,
                            "line": node.lineno,
                            "construction_kind": "RETURN_DICT",
                            "container": "<return>",
                            "expression": node_src(text, v_node),
                            "symbols": ";".join(sorted({
                                n.id for n in ast.walk(v_node)
                                if isinstance(n, ast.Name)
                            })),
                        })

            return_rows.append(rec)

    return helper_rows, return_rows, x100_rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R1")
    print("Missing X100 Component Binding / Deployment-Object Constructor Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
SG7B10 REMAINS THE AUTHORITATIVE EVALUATOR SOURCE.
""")

    s_prev = load_json(R26IR2_SUMMARY)
    if s_prev.get("status") != "SG7B10_DEPLOYMENT_X100_CONSTRUCTION_CONTRACT_STILL_INCOMPLETE":
        raise RuntimeError("R26I-R1 requires unresolved R26I-R X100 construction status.")

    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    text = safe_text(SOURCE)
    tree = ast.parse(text)

    aliases = import_alias_map(tree)
    local_funcs = local_function_map(tree)

    assign_rows, call_rows = find_deployment_assignments(tree, text)

    save_csv(DEPLOYMENT_ASSIGN, assign_rows)
    save_csv(CALLER_TABLE, call_rows)

    # -------------------------------------------------------------------------
    # Resolve each deployment constructor call.
    # -------------------------------------------------------------------------

    import_rows = []
    helper_rows = []
    return_rows = []
    x100_rows = []

    resolved_constructor_records = []

    for call in call_rows:
        cname = call["call_name"]
        if not cname:
            continue

        parts = cname.split(".")
        base = parts[0]
        fn = parts[-1]

        # 1. Local function
        if fn in local_funcs and len(parts) == 1:
            h, r, x = inspect_function_for_return_contract(SOURCE, fn)
            helper_rows.extend(h)
            return_rows.extend(r)
            x100_rows.extend(x)

            import_rows.append({
                "deployment_call": cname,
                "resolution_kind": "LOCAL_FUNCTION",
                "module": SOURCE.stem,
                "symbol": fn,
                "resolved_source": str(SOURCE),
            })

            resolved_constructor_records.append((SOURCE, fn))

        # 2. Imported symbol function
        elif base in aliases and aliases[base]["kind"] == "symbol":
            info = aliases[base]
            mod_path = resolve_module_path(info["module"])

            import_rows.append({
                "deployment_call": cname,
                "resolution_kind": "IMPORTED_SYMBOL",
                "module": info["module"],
                "symbol": info["symbol"],
                "resolved_source": str(mod_path) if mod_path else "",
            })

            if mod_path:
                h, r, x = inspect_function_for_return_contract(
                    mod_path, info["symbol"]
                )
                helper_rows.extend(h)
                return_rows.extend(r)
                x100_rows.extend(x)
                resolved_constructor_records.append((mod_path, info["symbol"]))

        # 3. Module alias function
        elif base in aliases and aliases[base]["kind"] == "module":
            info = aliases[base]
            mod_path = resolve_module_path(info["module"])

            import_rows.append({
                "deployment_call": cname,
                "resolution_kind": "IMPORTED_MODULE_FUNCTION",
                "module": info["module"],
                "symbol": fn,
                "resolved_source": str(mod_path) if mod_path else "",
            })

            if mod_path:
                h, r, x = inspect_function_for_return_contract(mod_path, fn)
                helper_rows.extend(h)
                return_rows.extend(r)
                x100_rows.extend(x)
                resolved_constructor_records.append((mod_path, fn))

        else:
            import_rows.append({
                "deployment_call": cname,
                "resolution_kind": "UNRESOLVED_CALLER",
                "module": "",
                "symbol": fn,
                "resolved_source": "",
            })

    save_csv(IMPORT_TABLE, import_rows)
    save_csv(HELPER_TABLE, helper_rows)
    save_csv(RETURN_TABLE, return_rows)
    save_csv(X100_TABLE, x100_rows)

    # -------------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------------

    unique_x100_exprs = {}
    for row in x100_rows:
        expr = row["expression"].strip()
        if expr:
            unique_x100_exprs.setdefault(expr, row)

    constructor_resolved = len(resolved_constructor_records) > 0
    x100_resolved = len(unique_x100_exprs) == 1

    if constructor_resolved and x100_resolved:
        selected = next(iter(unique_x100_exprs.values()))

        status = "SG7B10_DEPLOYMENT_X100_CONSTRUCTOR_EXPRESSION_RESOLVED"
        diagnosis = (
            "DEPLOYMENT_OBJECT_HELPER_LINEAGE_IDENTIFIES_ONE_X100_CONSTRUCTION_EXPRESSION"
        )
        recommendation = (
            "The missing X100 branch is resolved: SG7B10 receives deployment from an upstream "
            "constructor/helper, and that helper defines one exact X100 construction expression. "
            "Proceed to bind only the symbols in this expression to persisted numeric arrays and "
            "reconstruct the model input tensor. Do not search for alternative evaluators or "
            "ready-made X100 arrays."
        )
        next_milestone = (
            "V15-SG7E1R26I-R2 — Exact X100 Component Array Binding / Reconstruction"
        )

    elif constructor_resolved:
        selected = None

        status = "SG7B10_DEPLOYMENT_CONSTRUCTOR_RESOLVED_X100_EXPRESSION_AMBIGUOUS"
        diagnosis = (
            "DEPLOYMENT_HELPER_RESOLVED_BUT_MULTIPLE_OR_NO_X100_EXPRESSIONS_REMAIN"
        )
        recommendation = (
            "Do not call model.predict. Audit only the resolved deployment constructor helper's "
            "return branches and X100 key creation path. Do not broaden the evaluator/source search."
        )
        next_milestone = (
            "V15-SG7E1R26I-R2 — Deployment Helper X100 Branch Audit"
        )

    else:
        selected = None

        status = "SG7B10_DEPLOYMENT_CONSTRUCTOR_NOT_YET_RESOLVED"
        diagnosis = (
            "DEPLOYMENT_VARIABLE_CALLER_OR_IMPORTED_HELPER_LINEAGE_REMAINS_UNBOUND"
        )
        recommendation = (
            "Do not call model.predict. Audit only the deployment assignment call(s) listed by "
            "R26I-R1 and resolve their imported/local definition lineage. SG7B10 remains authoritative."
        )
        next_milestone = (
            "V15-SG7E1R26I-R2 — Deployment Constructor Import/Caller Resolution Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "deployment_assignment_count": len(assign_rows),
        "deployment_constructor_call_count": len(call_rows),
        "resolved_constructor_count": len(resolved_constructor_records),
        "helper_definition_records": len(helper_rows),
        "return_records": len(return_rows),
        "X100_expression_records": len(x100_rows),
        "unique_X100_expression_count": len(unique_x100_exprs),
        "selected_X100_expression": selected["expression"] if selected else "",
        "selected_X100_source": selected["source"] if selected else "",
        "selected_X100_function": selected["function"] if selected else "",
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R1",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_evaluator": str(SOURCE),
        "deployment_constructor": {
            "assignment_count": len(assign_rows),
            "call_count": len(call_rows),
            "resolved_constructor_count": len(resolved_constructor_records),
            "resolved_constructors": [
                {"source": str(p), "function": fn}
                for p, fn in resolved_constructor_records
            ],
        },
        "X100_constructor": {
            "expression_records": len(x100_rows),
            "unique_expression_count": len(unique_x100_exprs),
            "resolved": x100_resolved,
            "expression": selected["expression"] if selected else None,
            "source": selected["source"] if selected else None,
            "function": selected["function"] if selected else None,
            "symbols": selected["symbols"].split(";") if selected and selected["symbols"] else [],
        },
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "gamma_changed": False,
            "guard_changed": False,
            "threshold_changed": False,
            "model_predict_executed": False,
            "alternative_evaluator_search_performed": False,
            "fabricated_feature_used": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R1",
        "status": status,
        "diagnosis": diagnosis,
        "deployment_constructor_resolved": constructor_resolved,
        "X100_expression_resolved": x100_resolved,
        "selected_X100_expression": selected["expression"] if selected else None,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("DEPLOYMENT VARIABLE TRACE")
    print(f"  Assignments             : {len(assign_rows)}")
    print(f"  Constructor calls       : {len(call_rows)}")
    for row in call_rows:
        print(
            f"  line={row['line']} | {row['call_name']} | "
            f"{row['expression'][:180]}"
        )

    print("\nCONSTRUCTOR RESOLUTION")
    print(f"  Resolved constructors   : {len(resolved_constructor_records)}")
    for path, fn in resolved_constructor_records:
        print(f"  {path.name} :: {fn}")

    print("\nX100 CONSTRUCTION EXPRESSIONS")
    print(f"  Records                 : {len(x100_rows)}")
    print(f"  Unique expressions      : {len(unique_x100_exprs)}")
    for row in x100_rows:
        print(
            f"  {Path(row['source']).name} :: {row['function']} "
            f"| {row['construction_kind']} | {row['expression'][:220]}"
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

    print("\nTables:")
    for p in (
        DEPLOYMENT_ASSIGN,
        CALLER_TABLE,
        IMPORT_TABLE,
        HELPER_TABLE,
        RETURN_TABLE,
        X100_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R1 DEPLOYMENT-OBJECT CONSTRUCTOR AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No alternative evaluator was searched.")
    print("No fabricated feature was used.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
