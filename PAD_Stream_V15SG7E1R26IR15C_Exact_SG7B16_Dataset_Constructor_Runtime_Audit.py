from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import importlib.util
import json
import sys

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R15C
# Exact SG7B16 Dataset Constructor Runtime Audit
#
# DIAGNOSTIC-ONLY BASE/DATASET BINDING REPAIR
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
# R15B resolved the exact SG7B16 dataset constructor:
#
#     dataset = base.load_dataset()
#
# but `base` is a local runtime object and therefore was not available in the
# imported module globals.
#
# R15C traces ONLY the source-defined local assignment that creates `base`,
# executes that exact constructor, then evaluates:
#
#     base.load_dataset()
#     float(dataset["tD_scale"][0])
#     load_deployment_database(workspace, tD_scale)
#
# and validates deployment["X100"].
#
# No model inference is executed.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR15C"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "PAD_Stream_V15SG7B16_Controlled_Front_Preserving_TOF_Refinement.py"

R15B_DIR = ROOT / "output" / "V15_SG7E1R26IR15B"
R15B_SUMMARY = R15B_DIR / "PAD_Stream_V15SG7E1R26IR15B_Summary.json"

BASE_ASSIGN_TABLE = OUT / "V15SG7E1R26IR15C_Base_Assignment_Trace.csv"
BASE_RUNTIME_TABLE = OUT / "V15SG7E1R26IR15C_Base_Runtime_Binding.csv"
DATASET_TABLE = OUT / "V15SG7E1R26IR15C_Dataset_Runtime_Binding.csv"
TD_TABLE = OUT / "V15SG7E1R26IR15C_tD_Scale_Runtime_Binding.csv"
DEPLOY_TABLE = OUT / "V15SG7E1R26IR15C_Deployment_Runtime_Binding.csv"
X100_TABLE = OUT / "V15SG7E1R26IR15C_X100_Runtime_Identity.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR15C_Final_Gate_Matrix.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR15C_Dataset_Constructor_Decision.csv"

NUM_FILE = OUT / "V15SG7E1R26IR15C_Resolved_SG7B16_X100.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR15C_Dataset_Constructor_Runtime_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR15C_Summary.json"


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


def symbol_assignments(tree, text, symbol):
    rows = []
    nodes = []
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
                nodes.append(node.value)
    order = sorted(range(len(rows)), key=lambda i: int(rows[i]["line"]))
    return [rows[i] for i in order], [nodes[i] for i in order]


def safe_eval_expr(expr: str, module, local_env=None):
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
    if local_env:
        env.update(local_env)

    return eval(compile(parsed, "<R15C-eval>", "eval"), env, {})


def workspace_from_module(module):
    for symbol in ("DEFAULT_DEPLOYMENT_WORKSPACE", "DEPLOYMENT_WORKSPACE"):
        if hasattr(module, symbol):
            return resolve_path(getattr(module, symbol)), symbol
    return None, None


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R15C")
    print("Exact SG7B16 Dataset Constructor Runtime Audit")
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
ONLY THE LOCAL `base` OBJECT FEEDING dataset = base.load_dataset() WILL BE AUDITED.
""")

    prev = load_json(R15B_SUMMARY)
    if prev.get("status") != "SG7B16_DATASET_BINDING_STILL_INCOMPLETE":
        raise RuntimeError("R15C requires the R15B dataset-binding failure.")

    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    text = safe_text(SOURCE)
    tree = ast.parse(text)

    base_rows, base_nodes = symbol_assignments(tree, text, "base")
    dataset_rows, _ = symbol_assignments(tree, text, "dataset")

    save_csv(BASE_ASSIGN_TABLE, base_rows)

    creator = import_source(SOURCE, "_sg7b16_r15c")

    base = None
    selected_base = None
    base_attempts = []

    for row in base_rows:
        expr = row["expression"]
        try:
            obj = safe_eval_expr(expr, creator)
            ok = obj is not None
            has_load_dataset = bool(
                ok and hasattr(obj, "load_dataset") and callable(getattr(obj, "load_dataset"))
            )
            base_attempts.append({
                "line": row["line"],
                "expression": expr,
                "resolved": ok,
                "type": type(obj).__name__ if ok else "",
                "module_file": str(getattr(obj, "__file__", "")) if ok else "",
                "has_load_dataset": has_load_dataset,
                "diagnostic": "",
            })
            if has_load_dataset:
                base = obj
                selected_base = row
                break
        except Exception as exc:
            base_attempts.append({
                "line": row["line"],
                "expression": expr,
                "resolved": False,
                "type": "",
                "module_file": "",
                "has_load_dataset": False,
                "diagnostic": f"{type(exc).__name__}: {exc}",
            })

    save_csv(BASE_RUNTIME_TABLE, base_attempts)

    dataset = None
    dataset_error = ""

    if base is not None:
        try:
            dataset = base.load_dataset()
        except Exception as exc:
            dataset_error = f"{type(exc).__name__}: {exc}"

    dataset_ok = isinstance(dataset, dict)

    save_csv(DATASET_TABLE, [{
        "base_resolved": base is not None,
        "base_assignment": selected_base["expression"] if selected_base else "",
        "base_file": str(getattr(base, "__file__", "")) if base is not None else "",
        "dataset_resolved": dataset_ok,
        "dataset_type": type(dataset).__name__ if dataset is not None else "",
        "dataset_keys": ";".join(sorted(dataset.keys())) if dataset_ok else "",
        "diagnostic": dataset_error,
    }])

    td = None
    td_error = ""

    if dataset_ok and "tD_scale" in dataset:
        try:
            arr = np.asarray(dataset["tD_scale"]).ravel()
            if arr.size < 1:
                raise ValueError("tD_scale array is empty")
            td = float(arr[0])
        except Exception as exc:
            td_error = f"{type(exc).__name__}: {exc}"
    elif dataset_ok:
        td_error = "dataset lacks tD_scale"
    else:
        td_error = "dataset unresolved"

    save_csv(TD_TABLE, [{
        "dataset_resolved": dataset_ok,
        "tD_scale_present": dataset_ok and "tD_scale" in dataset,
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
        ("R15B_failure_reproduced", True),
        ("SG7B16_creator_fixed", prev.get("selected_creator") == SOURCE.name),
        ("base_assignment_found", len(base_rows) > 0),
        ("base_runtime_resolved", base is not None),
        ("base_load_dataset_available", bool(base and hasattr(base, "load_dataset"))),
        ("dataset_runtime_resolved", dataset_ok),
        ("dataset_contains_tD_scale", dataset_ok and "tD_scale" in dataset),
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
        status = "SG7B16_BASE_DATASET_tD_SCALE_AND_X100_RUNTIME_BINDINGS_RESOLVED"
        diagnosis = (
            "EXACT_LOCAL_BASE_CONSTRUCTOR_CLOSES_DATASET_tD_SCALE_AND_DEPLOYMENT_X100_LINEAGE"
        )
        recommendation = (
            "The exact SG7B16 local base object now resolves dataset, tD_scale, and deployment X100. "
            "Persist these identities and proceed directly to the repaired SG7B16 frozen100 creator "
            "100-day runtime control. Do not reopen creator/model/X100 discovery."
        )
        next_ms = (
            "V15-SG7E1R26I-R16 — Repaired SG7B16 Frozen100 Creator Runtime Control"
        )
    else:
        status = "SG7B16_BASE_DATASET_RUNTIME_BINDING_STILL_INCOMPLETE"
        diagnosis = (
            "ONE_OR_MORE_SOURCE_DEFINED_BASE_DATASET_OR_DEPLOYMENT_COMPONENTS_REMAIN_UNRESOLVED"
        )
        recommendation = (
            "Do not execute model.predict. Audit only the failed R15C gates and the exact local "
            "`base` assignment persisted in the R15C tables."
        )
        next_ms = (
            "V15-SG7E1R26I-R15D — Final SG7B16 Base Constructor Residual Audit"
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
        "base_assignment": selected_base["expression"] if selected_base else "",
        "base_file": str(getattr(base, "__file__", "")) if base is not None else "",
        "tD_scale": td if td is not None else "",
        "X100_sha256": sha256_array(x100) if isinstance(x100, np.ndarray) else "",
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R15C",
        "status": status,
        "diagnosis": diagnosis,
        "creator": SOURCE.name,
        "base_assignment": selected_base,
        "base_file": str(getattr(base, "__file__", "")) if base is not None else None,
        "dataset_keys": sorted(dataset.keys()) if dataset_ok else None,
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
        "milestone": "V15-SG7E1R26I-R15C",
        "status": status,
        "diagnosis": diagnosis,
        "selected_creator": SOURCE.name,
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("BASE ASSIGNMENT TRACE")
    print(f"  Assignments             : {len(base_rows)}")
    for r in base_rows:
        print(f"  line={r['line']} | base <- {r['expression']}")

    print("\nBASE RUNTIME BINDING")
    print(f"  Resolved                : {base is not None}")
    if selected_base:
        print(f"  Constructor             : {selected_base['expression']}")
    if base is not None:
        print(f"  Base file               : {getattr(base, '__file__', 'N/A')}")
        print(f"  load_dataset available  : {hasattr(base, 'load_dataset')}")

    print("\nDATASET")
    print(f"  Resolved                : {dataset_ok}")
    if dataset_ok:
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
    print("V15-SG7E1R26I-R15C FINAL GATES")
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
        BASE_ASSIGN_TABLE,
        BASE_RUNTIME_TABLE,
        DATASET_TABLE,
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
    print("V15-SG7E1R26I-R15C EXACT SG7B16 DATASET-CONSTRUCTOR AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No authority was broadened.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
