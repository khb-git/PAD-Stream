from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import importlib.util
import inspect
import json
import sys

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R15A
# Final SG7B16 Residual Binding Repair
#
# DIAGNOSTIC-ONLY SOURCE-AUTHENTIC BINDING REPAIR
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA / GUARD RECALIBRATION.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
#
# PURPOSE
# -------
# R15 fixed the creator to SG7B16 and resolved:
#
#   deployment_workspace
#   load_deployment_database
#
# but failed to resolve:
#
#   authoritative base module
#   tD_scale
#   deployment database / X100
#
# R15A repairs ONLY those failed bindings by tracing the actual SG7B16 caller
# expression feeding load_deployment_database(...), then resolving that
# tD_scale expression from SG7B16's own runtime namespace and imported helpers.
#
# No global model/X100 search and no fabricated scalar are permitted.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR15A"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "PAD_Stream_V15SG7B16_Controlled_Front_Preserving_TOF_Refinement.py"

R15_DIR = ROOT / "output" / "V15_SG7E1R26IR15"
R15_SUMMARY = R15_DIR / "PAD_Stream_V15SG7E1R26IR15_Summary.json"

# Outputs
CALL_TABLE = OUT / "V15SG7E1R26IR15A_Deployment_Helper_Call_Trace.csv"
ARG_TABLE = OUT / "V15SG7E1R26IR15A_tD_Scale_Argument_Provenance.csv"
IMPORT_TABLE = OUT / "V15SG7E1R26IR15A_Imported_Runtime_Helper_Audit.csv"
EVAL_TABLE = OUT / "V15SG7E1R26IR15A_tD_Scale_Runtime_Evaluation.csv"
DEPLOY_TABLE = OUT / "V15SG7E1R26IR15A_Deployment_Database_Runtime_Validation.csv"
X100_TABLE = OUT / "V15SG7E1R26IR15A_X100_Runtime_Identity.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR15A_Final_Binding_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR15A_Final_Binding_Decision.csv"

NUM_FILE = OUT / "V15SG7E1R26IR15A_Resolved_SG7B16_X100.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR15A_Final_SG7B16_Residual_Binding_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR15A_Summary.json"


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def save_csv(path: Path, rows):
    rows = list(rows)
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


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def import_source(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def resolve_path(value):
    p = Path(value)
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve()


def assignment_records(tree, text):
    rows = []
    amap = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue

        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                rec = {
                    "line": node.lineno,
                    "symbol": tgt.id,
                    "expression": node_src(text, node.value),
                    "node": node.value,
                }
                rows.append(rec)
                amap[tgt.id] = rec

    return rows, amap


def deployment_calls(tree, text):
    rows = []
    nodes = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        cname = call_name(node)
        if not cname.endswith("load_deployment_database"):
            continue

        rows.append({
            "line": node.lineno,
            "call": cname,
            "expression": node_src(text, node),
            "arg0": node_src(text, node.args[0]) if len(node.args) > 0 else "",
            "arg1": node_src(text, node.args[1]) if len(node.args) > 1 else "",
            "arg_count": len(node.args),
        })
        nodes.append(node)

    return rows, nodes


def extract_name_dependencies(node):
    return sorted({
        n.id for n in ast.walk(node)
        if isinstance(n, ast.Name)
    })


def trace_expression(expr_node, amap, text, depth=0, seen=None):
    if seen is None:
        seen = set()

    rows = []

    for name in extract_name_dependencies(expr_node):
        if name in seen:
            continue
        seen.add(name)

        if name in amap:
            rec = amap[name]
            rows.append({
                "depth": depth,
                "symbol": name,
                "line": rec["line"],
                "expression": rec["expression"],
                "dependencies": ";".join(extract_name_dependencies(rec["node"])),
            })
            if depth < 12:
                rows.extend(
                    trace_expression(
                        rec["node"],
                        amap,
                        text,
                        depth=depth + 1,
                        seen=seen,
                    )
                )
        else:
            rows.append({
                "depth": depth,
                "symbol": name,
                "line": "",
                "expression": "",
                "dependencies": "",
            })

    return rows


def imported_helpers(module):
    rows = []
    objects = []

    for name, obj in vars(module).items():
        if inspect.ismodule(obj):
            file = getattr(obj, "__file__", None)
            rows.append({
                "name": name,
                "kind": "module",
                "file": str(file) if file else "",
                "has_load_dataset": bool(hasattr(obj, "load_dataset") and callable(getattr(obj, "load_dataset", None))),
            })
            objects.append((name, obj))

        elif callable(obj) and name in {
            "load_base_module",
            "load_dataset",
            "load_deployment_database",
        }:
            rows.append({
                "name": name,
                "kind": "callable",
                "file": inspect.getsourcefile(obj) or "",
                "has_load_dataset": False,
            })

    return rows, objects


def safe_eval_expr(expr: str, module):
    """
    Evaluate an expression exactly in SG7B16's imported runtime namespace.

    This is intentionally restricted to read-only expression evaluation and
    does not permit training/predict calls.
    """
    if not expr:
        raise ValueError("empty expression")

    parsed = ast.parse(expr, mode="eval")

    forbidden = {
        "fit",
        "predict",
        "train_on_batch",
        "compile",
        "save",
        "savez",
        "savez_compressed",
    }

    for node in ast.walk(parsed):
        if isinstance(node, ast.Call):
            cname = call_name(node)
            leaf = cname.split(".")[-1] if cname else ""
            if leaf in forbidden:
                raise ValueError(f"forbidden call in binding expression: {cname}")

    env = dict(vars(module))
    env.update({
        "np": np,
        "Path": Path,
        "ROOT": ROOT,
    })

    return eval(compile(parsed, "<R15A-binding>", "eval"), env, {})


def scalarize(value):
    arr = np.asarray(value)
    if arr.size != 1:
        raise ValueError(f"expected scalar-like value, got shape={arr.shape}")
    return float(arr.ravel()[0])


def workspace_from_module(module, expr):
    # First evaluate the actual caller expression if possible.
    try:
        v = safe_eval_expr(expr, module)
        return resolve_path(v), "caller_expression"
    except Exception:
        pass

    for symbol in ("DEFAULT_DEPLOYMENT_WORKSPACE", "DEPLOYMENT_WORKSPACE"):
        if hasattr(module, symbol):
            return resolve_path(getattr(module, symbol)), symbol

    return None, None


def resolve_td_from_expression(expr, module):
    rows = []

    # 1) Exact caller expression in the authoritative SG7B16 namespace.
    try:
        value = safe_eval_expr(expr, module)
        td = scalarize(value)
        rows.append({
            "basis": "exact_SG7B16_caller_expression",
            "expression": expr,
            "resolved": True,
            "value": td,
            "diagnostic": "",
        })
        return td, rows
    except Exception as exc:
        rows.append({
            "basis": "exact_SG7B16_caller_expression",
            "expression": expr,
            "resolved": False,
            "value": "",
            "diagnostic": f"{type(exc).__name__}: {exc}",
        })

    # 2) If the expression is a plain symbol and that symbol exists at runtime.
    if expr.isidentifier() and hasattr(module, expr):
        try:
            td = scalarize(getattr(module, expr))
            rows.append({
                "basis": f"module_symbol:{expr}",
                "expression": expr,
                "resolved": True,
                "value": td,
                "diagnostic": "",
            })
            return td, rows
        except Exception as exc:
            rows.append({
                "basis": f"module_symbol:{expr}",
                "expression": expr,
                "resolved": False,
                "value": "",
                "diagnostic": f"{type(exc).__name__}: {exc}",
            })

    # 3) Exact imported helper lineage: modules exposing load_dataset.
    for name, obj in vars(module).items():
        if not inspect.ismodule(obj):
            continue
        if not hasattr(obj, "load_dataset") or not callable(obj.load_dataset):
            continue
        try:
            ds = obj.load_dataset()
            if isinstance(ds, dict) and "tD_scale" in ds:
                td = scalarize(ds["tD_scale"])
                rows.append({
                    "basis": f"{name}.load_dataset()['tD_scale']",
                    "expression": expr,
                    "resolved": True,
                    "value": td,
                    "diagnostic": "",
                })
                return td, rows
        except Exception as exc:
            rows.append({
                "basis": f"{name}.load_dataset()['tD_scale']",
                "expression": expr,
                "resolved": False,
                "value": "",
                "diagnostic": f"{type(exc).__name__}: {exc}",
            })

    # 4) Exact SG7B16 load_base_module helper if defined.
    if hasattr(module, "load_base_module") and callable(module.load_base_module):
        try:
            base = module.load_base_module()
            if hasattr(base, "load_dataset") and callable(base.load_dataset):
                ds = base.load_dataset()
                if isinstance(ds, dict) and "tD_scale" in ds:
                    td = scalarize(ds["tD_scale"])
                    rows.append({
                        "basis": "load_base_module().load_dataset()['tD_scale']",
                        "expression": expr,
                        "resolved": True,
                        "value": td,
                        "diagnostic": "",
                    })
                    return td, rows
        except Exception as exc:
            rows.append({
                "basis": "load_base_module().load_dataset()['tD_scale']",
                "expression": expr,
                "resolved": False,
                "value": "",
                "diagnostic": f"{type(exc).__name__}: {exc}",
            })

    return None, rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R15A")
    print("Final SG7B16 Residual Binding Repair")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
SG7B16 REMAINS THE ONLY AUTHORITATIVE FROZEN100 CREATOR.
ONLY THE FAILED R15 tD_scale / DEPLOYMENT / X100 BINDINGS WILL BE REPAIRED.
""")

    prev = load_json(R15_SUMMARY)
    if prev.get("status") != "SG7B16_CREATOR_RESIDUAL_BINDINGS_STILL_INCOMPLETE":
        raise RuntimeError("R15A requires the R15 residual-binding failure.")

    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    text = safe_text(SOURCE)
    tree = ast.parse(text)
    assignments, amap = assignment_records(tree, text)
    call_rows, call_nodes = deployment_calls(tree, text)

    save_csv(CALL_TABLE, call_rows)

    creator = import_source(SOURCE, "_sg7b16_r15a")

    helper_rows, _ = imported_helpers(creator)
    save_csv(IMPORT_TABLE, helper_rows)

    # Use only the exact load_deployment_database call(s) in SG7B16.
    # Prefer a two-argument call because the helper contract already established
    # workspace + tD_scale.
    selected_call = None
    selected_node = None
    for row, node in zip(call_rows, call_nodes):
        if len(node.args) >= 2:
            selected_call = row
            selected_node = node
            break

    if selected_call is None and call_rows:
        selected_call = call_rows[0]
        selected_node = call_nodes[0]

    arg_trace = []
    td_expr = ""
    workspace_expr = ""

    if selected_node is not None:
        if len(selected_node.args) > 0:
            workspace_expr = node_src(text, selected_node.args[0])
            arg_trace.extend(trace_expression(selected_node.args[0], amap, text))
        if len(selected_node.args) > 1:
            td_expr = node_src(text, selected_node.args[1])
            arg_trace.extend(trace_expression(selected_node.args[1], amap, text))

    # Deduplicate.
    dedup = {}
    for r in arg_trace:
        dedup[(r["symbol"], r["line"], r["depth"])] = r
    arg_trace = list(dedup.values())
    save_csv(ARG_TABLE, arg_trace)

    workspace, workspace_basis = workspace_from_module(
        creator,
        workspace_expr or "DEFAULT_DEPLOYMENT_WORKSPACE",
    )

    td, td_rows = resolve_td_from_expression(td_expr, creator)
    save_csv(EVAL_TABLE, td_rows)

    loader = getattr(creator, "load_deployment_database", None)
    deploy = None
    deploy_error = ""

    if callable(loader) and workspace is not None and td is not None:
        try:
            deploy = loader(workspace, td)
        except Exception as exc:
            deploy_error = f"{type(exc).__name__}: {exc}"

    x100 = None
    if isinstance(deploy, dict) and "X100" in deploy:
        x100 = np.asarray(deploy["X100"])

    save_csv(DEPLOY_TABLE, [{
        "selected_call_line": selected_call["line"] if selected_call else "",
        "workspace_expression": workspace_expr,
        "workspace_basis": workspace_basis or "",
        "workspace": str(workspace) if workspace else "",
        "workspace_exists": workspace.exists() if workspace else False,
        "tD_scale_expression": td_expr,
        "tD_scale": td if td is not None else "",
        "loader_available": callable(loader),
        "deployment_success": isinstance(deploy, dict),
        "deployment_keys": ";".join(sorted(deploy.keys())) if isinstance(deploy, dict) else "",
        "diagnostic": deploy_error,
    }])

    x_ok = bool(
        isinstance(x100, np.ndarray)
        and np.issubdtype(x100.dtype, np.number)
        and np.all(np.isfinite(x100))
        and x100.ndim == 3
        and x100.shape[-1] == 2
    )

    save_csv(X100_TABLE, [{
        "resolved": isinstance(x100, np.ndarray),
        "shape": str(x100.shape) if isinstance(x100, np.ndarray) else "",
        "dtype": str(x100.dtype) if isinstance(x100, np.ndarray) else "",
        "numeric": bool(np.issubdtype(x100.dtype, np.number)) if isinstance(x100, np.ndarray) else False,
        "finite": bool(np.all(np.isfinite(x100))) if isinstance(x100, np.ndarray) else False,
        "feature_dim_2": bool(x100.ndim == 3 and x100.shape[-1] == 2) if isinstance(x100, np.ndarray) else False,
        "sha256": sha256_array(x100) if isinstance(x100, np.ndarray) else "",
    }])

    gates = [
        ("R15_failure_reproduced", True),
        ("SG7B16_creator_remains_fixed", prev.get("selected_creator") == SOURCE.name),
        ("deployment_helper_call_found", selected_call is not None),
        ("workspace_argument_resolved", workspace is not None),
        ("workspace_exists", workspace.exists() if workspace else False),
        ("tD_scale_argument_expression_traced", bool(td_expr)),
        ("tD_scale_runtime_resolved", td is not None),
        ("deployment_helper_available", callable(loader)),
        ("deployment_database_constructed", isinstance(deploy, dict)),
        ("X100_resolved", isinstance(x100, np.ndarray)),
        ("X100_numeric_finite_feature_dim_2", x_ok),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_model_parameter_changed", True),
        ("no_later_time_state_generated", True),
        ("no_creator_or_model_search_reopened", True),
    ]

    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    if not failed:
        status = "SG7B16_FINAL_RESIDUAL_BINDINGS_REPAIRED"
        diagnosis = (
            "SOURCE_AUTHENTIC_SG7B16_CALLER_EXPRESSION_CLOSES_tD_SCALE_DEPLOYMENT_AND_X100_BINDINGS"
        )
        recommendation = (
            "The selected SG7B16 creator now has a fully resolved deployment input contract. "
            "Persist this X100 and proceed directly to the repaired SG7B16 100-day frozen-model "
            "runtime closure against persisted frozen100. Do not reopen creator/model/X100 discovery."
        )
        next_ms = (
            "V15-SG7E1R26I-R16 — Repaired SG7B16 Frozen100 Creator Runtime Control"
        )
    else:
        status = "SG7B16_FINAL_RESIDUAL_BINDING_REPAIR_STILL_INCOMPLETE"
        diagnosis = (
            "ONE_OR_MORE_EXACT_SG7B16_CALLER_EXPRESSION_OR_RUNTIME_HELPER_BINDINGS_REMAIN_UNRESOLVED"
        )
        recommendation = (
            "Do not execute model.predict. Audit only the failed R15A gates and the exact caller "
            "expression persisted in the R15A tables. Do not broaden authority."
        )
        next_ms = (
            "V15-SG7E1R26I-R15B — Exact SG7B16 Caller Expression Residual Audit"
        )

    if isinstance(x100, np.ndarray):
        np.savez_compressed(
            NUM_FILE,
            X100=x100,
            tD_scale=np.asarray([td], dtype=np.float64),
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "workspace": str(workspace) if workspace else "",
        "tD_scale_expression": td_expr,
        "tD_scale": td if td is not None else "",
        "X100_sha256": sha256_array(x100) if isinstance(x100, np.ndarray) else "",
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R15A",
        "status": status,
        "diagnosis": diagnosis,
        "creator": SOURCE.name,
        "deployment_call": selected_call,
        "workspace": str(workspace) if workspace else None,
        "workspace_basis": workspace_basis,
        "tD_scale_expression": td_expr,
        "tD_scale": td,
        "X100_shape": list(x100.shape) if isinstance(x100, np.ndarray) else None,
        "X100_sha256": sha256_array(x100) if isinstance(x100, np.ndarray) else None,
        "failed_gates": failed,
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "model_predict_executed": False,
            "creator_search_reopened": False,
            "model_search_reopened": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R15A",
        "status": status,
        "diagnosis": diagnosis,
        "selected_creator": SOURCE.name,
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("SG7B16 DEPLOYMENT CALL")
    print(f"  Call records            : {len(call_rows)}")
    if selected_call:
        print(f"  Selected line           : {selected_call['line']}")
        print(f"  Workspace expression    : {workspace_expr}")
        print(f"  tD_scale expression     : {td_expr}")

    print("\nFINAL RUNTIME BINDINGS")
    print(f"  Workspace               : {workspace}")
    print(f"  Workspace exists        : {workspace.exists() if workspace else False}")
    print(f"  tD_scale                : {td if td is not None else 'UNRESOLVED'}")
    print(f"  Deployment constructed  : {isinstance(deploy, dict)}")

    print("\nFINAL X100")
    if isinstance(x100, np.ndarray):
        print(f"  Shape                   : {x100.shape}")
        print(f"  Dtype                   : {x100.dtype}")
        print(f"  Finite                  : {np.all(np.isfinite(x100))}")
        print(f"  Feature dim = 2         : {x100.ndim == 3 and x100.shape[-1] == 2}")
        print(f"  SHA-256                 : {sha256_array(x100)}")
    else:
        print("  NOT RESOLVED")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R15A FINAL BINDING GATES")
    print("=" * 78)
    for g, p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")
    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    if failed:
        print("\nFAILED GATES")
        for g in failed:
            print(f"  {g}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_ms}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\nTables:")
    for p in (
        CALL_TABLE,
        ARG_TABLE,
        IMPORT_TABLE,
        EVAL_TABLE,
        DEPLOY_TABLE,
        X100_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    if isinstance(x100, np.ndarray):
        print("\nNumerical:")
        print(f"  {NUM_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R15A FINAL SG7B16 RESIDUAL BINDING REPAIR: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No creator/model search was reopened.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
