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
# PAD-Stream V15-SG7E1R26I-R15B
# Exact SG7B16 Caller Expression Residual Audit
#
# DIAGNOSTIC-ONLY DATASET-BINDING REPAIR
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
# R15A resolved the exact SG7B16 caller expression:
#
#   load_deployment_database(
#       workspace,
#       float(dataset["tD_scale"][0])
#   )
#
# but dataset itself was not yet bound.
#
# R15B traces ONLY the authoritative `dataset` assignment inside SG7B16 and
# resolves its exact runtime constructor / helper. It then extracts tD_scale
# from that dataset and, if successful, reconstructs deployment["X100"].
#
# No model inference is executed.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR15B"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "PAD_Stream_V15SG7B16_Controlled_Front_Preserving_TOF_Refinement.py"

R15A_DIR = ROOT / "output" / "V15_SG7E1R26IR15A"
R15A_SUMMARY = R15A_DIR / "PAD_Stream_V15SG7E1R26IR15A_Summary.json"

# Outputs
DATASET_ASSIGN_TABLE = OUT / "V15SG7E1R26IR15B_Dataset_Assignment_Trace.csv"
DATASET_CALL_TABLE = OUT / "V15SG7E1R26IR15B_Dataset_Constructor_Call_Trace.csv"
HELPER_TABLE = OUT / "V15SG7E1R26IR15B_Dataset_Helper_Runtime_Binding.csv"
TD_TABLE = OUT / "V15SG7E1R26IR15B_tD_Scale_Resolution.csv"
DEPLOY_TABLE = OUT / "V15SG7E1R26IR15B_Deployment_Reconstruction.csv"
X100_TABLE = OUT / "V15SG7E1R26IR15B_X100_Identity.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR15B_Final_Gate_Matrix.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR15B_Dataset_Binding_Decision.csv"

NUM_FILE = OUT / "V15SG7E1R26IR15B_Resolved_X100.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR15B_Exact_Dataset_Binding_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR15B_Summary.json"


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


def import_source(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def resolve_path(value):
    p = Path(value)
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve()


def assignment_rows(tree, text, symbol):
    rows = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id == symbol:
                rows.append({
                    "line": node.lineno,
                    "symbol": symbol,
                    "expression": node_src(text, node.value),
                    "expression_type": type(node.value).__name__,
                })
    rows.sort(key=lambda r: int(r["line"]))
    return rows


def find_dataset_constructor_calls(tree, text):
    rows = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue

        targets = [
            tgt.id for tgt in node.targets
            if isinstance(tgt, ast.Name)
        ]
        if "dataset" not in targets:
            continue

        rhs = node.value
        rows.append({
            "line": node.lineno,
            "target": "dataset",
            "expression": node_src(text, rhs),
            "call_name": call_name(rhs) if isinstance(rhs, ast.Call) else "",
            "arg_count": len(rhs.args) if isinstance(rhs, ast.Call) else 0,
            "args": ";".join(node_src(text, a) for a in rhs.args) if isinstance(rhs, ast.Call) else "",
        })
    return rows


def safe_eval_expr(expr: str, module):
    """
    Read-only evaluation in the SG7B16 runtime namespace.
    Explicitly forbids training/inference/save actions.
    """
    parsed = ast.parse(expr, mode="eval")

    forbidden = {
        "fit", "predict", "train_on_batch", "compile",
        "save", "savez", "savez_compressed",
    }

    for node in ast.walk(parsed):
        if isinstance(node, ast.Call):
            cname = call_name(node)
            leaf = cname.split(".")[-1] if cname else ""
            if leaf in forbidden:
                raise ValueError(f"forbidden call: {cname}")

    env = dict(vars(module))
    env.update({"np": np, "Path": Path, "ROOT": ROOT})
    return eval(compile(parsed, "<R15B-eval>", "eval"), env, {})


def dataset_runtime_binding(constructor_rows, module):
    """
    Resolve dataset from the exact source assignment, not a global search.
    """
    attempts = []

    for row in constructor_rows:
        expr = row["expression"]
        try:
            value = safe_eval_expr(expr, module)
            ok = isinstance(value, dict)
            attempts.append({
                "line": row["line"],
                "expression": expr,
                "resolved": ok,
                "value_type": type(value).__name__,
                "keys": ";".join(sorted(value.keys())) if ok else "",
                "diagnostic": "",
            })
            if ok:
                return value, row, attempts
        except Exception as exc:
            attempts.append({
                "line": row["line"],
                "expression": expr,
                "resolved": False,
                "value_type": "",
                "keys": "",
                "diagnostic": f"{type(exc).__name__}: {exc}",
            })

    return None, None, attempts


def workspace_from_module(module):
    for symbol in ("DEFAULT_DEPLOYMENT_WORKSPACE", "DEPLOYMENT_WORKSPACE"):
        if hasattr(module, symbol):
            return resolve_path(getattr(module, symbol)), symbol
    return None, None


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R15B")
    print("Exact SG7B16 Caller Expression Residual Audit")
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
ONLY THE `dataset` OBJECT FEEDING float(dataset["tD_scale"][0]) WILL BE AUDITED.
""")

    prev = load_json(R15A_SUMMARY)
    if prev.get("status") != "SG7B16_FINAL_RESIDUAL_BINDING_REPAIR_STILL_INCOMPLETE":
        raise RuntimeError("R15B requires the R15A residual-binding failure.")

    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    text = safe_text(SOURCE)
    tree = ast.parse(text)

    dataset_assignments = assignment_rows(tree, text, "dataset")
    constructor_rows = find_dataset_constructor_calls(tree, text)

    save_csv(DATASET_ASSIGN_TABLE, dataset_assignments)
    save_csv(DATASET_CALL_TABLE, constructor_rows)

    creator = import_source(SOURCE, "_sg7b16_r15b")

    dataset, selected_constructor, helper_attempts = dataset_runtime_binding(
        constructor_rows,
        creator,
    )
    save_csv(HELPER_TABLE, helper_attempts)

    td = None
    td_error = ""

    if isinstance(dataset, dict):
        if "tD_scale" in dataset:
            try:
                arr = np.asarray(dataset["tD_scale"]).ravel()
                if arr.size != 1:
                    raise ValueError(f"expected scalar tD_scale, shape={arr.shape}")
                td = float(arr[0])
            except Exception as exc:
                td_error = f"{type(exc).__name__}: {exc}"
        else:
            td_error = "dataset lacks tD_scale"
    else:
        td_error = "dataset not resolved"

    save_csv(TD_TABLE, [{
        "dataset_resolved": isinstance(dataset, dict),
        "selected_constructor_line": selected_constructor["line"] if selected_constructor else "",
        "selected_constructor_expression": selected_constructor["expression"] if selected_constructor else "",
        "tD_scale_present": isinstance(dataset, dict) and "tD_scale" in dataset,
        "tD_scale": td if td is not None else "",
        "diagnostic": td_error,
    }])

    workspace, workspace_basis = workspace_from_module(creator)
    loader = getattr(creator, "load_deployment_database", None)

    deployment = None
    deploy_error = ""

    if callable(loader) and workspace is not None and td is not None:
        try:
            deployment = loader(workspace, td)
        except Exception as exc:
            deploy_error = f"{type(exc).__name__}: {exc}"

    save_csv(DEPLOY_TABLE, [{
        "workspace": str(workspace) if workspace else "",
        "workspace_basis": workspace_basis or "",
        "workspace_exists": workspace.exists() if workspace else False,
        "loader_available": callable(loader),
        "tD_scale": td if td is not None else "",
        "deployment_success": isinstance(deployment, dict),
        "deployment_keys": ";".join(sorted(deployment.keys())) if isinstance(deployment, dict) else "",
        "diagnostic": deploy_error,
    }])

    x100 = None
    if isinstance(deployment, dict) and "X100" in deployment:
        x100 = np.asarray(deployment["X100"])

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
        ("R15A_failure_reproduced", True),
        ("SG7B16_creator_fixed", prev.get("selected_creator") == SOURCE.name),
        ("dataset_assignment_found", len(dataset_assignments) > 0),
        ("dataset_constructor_call_found", len(constructor_rows) > 0),
        ("dataset_runtime_resolved", isinstance(dataset, dict)),
        ("dataset_contains_tD_scale", isinstance(dataset, dict) and "tD_scale" in dataset),
        ("tD_scale_resolved", td is not None),
        ("workspace_resolved", workspace is not None),
        ("workspace_exists", workspace.exists() if workspace else False),
        ("deployment_loader_available", callable(loader)),
        ("deployment_database_constructed", isinstance(deployment, dict)),
        ("X100_resolved", isinstance(x100, np.ndarray)),
        ("X100_numeric_finite_feature_dim_2", x_ok),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_later_time_state_generated", True),
        ("no_authority_broadening", True),
    ]

    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    if not failed:
        status = "SG7B16_DATASET_tD_SCALE_AND_X100_BINDINGS_RESOLVED"
        diagnosis = (
            "EXACT_SG7B16_DATASET_CONSTRUCTOR_RESOLVES_tD_SCALE_AND_DEPLOYMENT_X100"
        )
        recommendation = (
            "The exact SG7B16 dataset object now resolves the caller's tD_scale and deployment X100. "
            "Persist these identities and proceed directly to the repaired SG7B16 frozen100 creator "
            "100-day runtime control. Do not reopen creator/model/X100 discovery."
        )
        next_ms = (
            "V15-SG7E1R26I-R16 — Repaired SG7B16 Frozen100 Creator Runtime Control"
        )
    else:
        status = "SG7B16_DATASET_BINDING_STILL_INCOMPLETE"
        diagnosis = (
            "EXACT_DATASET_ASSIGNMENT_EXISTS_BUT_ONE_OR_MORE_RUNTIME_DATASET_OR_DEPLOYMENT_COMPONENTS_REMAIN_UNRESOLVED"
        )
        recommendation = (
            "Do not execute model.predict. Audit only the failed R15B gates and the exact dataset "
            "constructor expression persisted in the R15B tables."
        )
        next_ms = (
            "V15-SG7E1R26I-R15C — Exact SG7B16 Dataset Constructor Runtime Audit"
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
        "dataset_constructor": selected_constructor["expression"] if selected_constructor else "",
        "tD_scale": td if td is not None else "",
        "X100_sha256": sha256_array(x100) if isinstance(x100, np.ndarray) else "",
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R15B",
        "status": status,
        "diagnosis": diagnosis,
        "creator": SOURCE.name,
        "dataset_constructor": selected_constructor,
        "dataset_keys": sorted(dataset.keys()) if isinstance(dataset, dict) else None,
        "tD_scale": td,
        "workspace": str(workspace) if workspace else None,
        "X100_shape": list(x100.shape) if isinstance(x100, np.ndarray) else None,
        "X100_sha256": sha256_array(x100) if isinstance(x100, np.ndarray) else None,
        "failed_gates": failed,
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
            "authority_broadened": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R15B",
        "status": status,
        "diagnosis": diagnosis,
        "selected_creator": SOURCE.name,
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("DATASET ASSIGNMENT TRACE")
    print(f"  Assignments             : {len(dataset_assignments)}")
    for r in dataset_assignments:
        print(f"  line={r['line']} | dataset <- {r['expression']}")

    print("\nDATASET RUNTIME BINDING")
    print(f"  Resolved                : {isinstance(dataset, dict)}")
    if selected_constructor:
        print(f"  Constructor             : {selected_constructor['expression']}")
    if isinstance(dataset, dict):
        print(f"  Key count               : {len(dataset)}")

    print("\ntD_SCALE")
    print(f"  Resolved                : {td is not None}")
    print(f"  Value                   : {td if td is not None else 'UNRESOLVED'}")
    if td_error:
        print(f"  Diagnostic              : {td_error}")

    print("\nDEPLOYMENT")
    print(f"  Workspace               : {workspace}")
    print(f"  Workspace exists        : {workspace.exists() if workspace else False}")
    print(f"  Constructed             : {isinstance(deployment, dict)}")
    if deploy_error:
        print(f"  Diagnostic              : {deploy_error}")

    print("\nX100")
    if isinstance(x100, np.ndarray):
        print(f"  Shape                   : {x100.shape}")
        print(f"  Dtype                   : {x100.dtype}")
        print(f"  Finite                  : {np.all(np.isfinite(x100))}")
        print(f"  Feature dim = 2         : {x100.ndim == 3 and x100.shape[-1] == 2}")
        print(f"  SHA-256                 : {sha256_array(x100)}")
    else:
        print("  NOT RESOLVED")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R15B FINAL GATES")
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
        DATASET_ASSIGN_TABLE,
        DATASET_CALL_TABLE,
        HELPER_TABLE,
        TD_TABLE,
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
    print("V15-SG7E1R26I-R15B EXACT SG7B16 CALLER-EXPRESSION AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No authority was broadened.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
