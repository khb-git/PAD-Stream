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


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR15"
OUT.mkdir(parents=True, exist_ok=True)

CREATOR_SOURCE = ROOT / "PAD_Stream_V15SG7B16_Controlled_Front_Preserving_TOF_Refinement.py"
R14_DIR = ROOT / "output" / "V15_SG7E1R26IR14"
R14_SUMMARY = R14_DIR / "PAD_Stream_V15SG7E1R26IR14_Summary.json"

TABLE_BIND = OUT / "V15SG7E1R26IR15_Residual_Binding_Audit.csv"
TABLE_DATASET = OUT / "V15SG7E1R26IR15_Dataset_tD_Scale_Resolution.csv"
TABLE_DEPLOY = OUT / "V15SG7E1R26IR15_Deployment_Helper_Runtime_Audit.csv"
TABLE_X100 = OUT / "V15SG7E1R26IR15_X100_Runtime_Identity.csv"
TABLE_GATES = OUT / "V15SG7E1R26IR15_Final_Residual_Binding_Gates.csv"
TABLE_DECISION = OUT / "V15SG7E1R26IR15_Residual_Binding_Decision.csv"
NUM = OUT / "V15SG7E1R26IR15_Resolved_X100.npz"
CONTRACT = OUT / "V15SG7E1R26IR15_Residual_Binding_Contract.json"
SUMMARY = OUT / "PAD_Stream_V15SG7E1R26IR15_Summary.json"


def save_csv(path, rows):
    rows = list(rows)
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


def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_array(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def import_module_from(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def resolve_path(v):
    p = Path(v)
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve()


def find_base_module(creator):
    # SG7B16 historically inherits its data contract from an earlier SG7B module.
    # Use only explicit runtime helper/module provenance exposed by SG7B16.
    rows = []
    for name, obj in vars(creator).items():
        if inspect.ismodule(obj):
            file = getattr(obj, "__file__", None)
            if file and "PAD_Stream_V15SG7B" in Path(file).name:
                rows.append((name, obj, Path(file)))
    # Prefer modules exposing load_dataset because tD_scale is a dataset scalar.
    for name, obj, file in rows:
        if hasattr(obj, "load_dataset") and callable(obj.load_dataset):
            return name, obj, file, rows

    # If SG7B16 exposes a load_base_module helper, execute that exact helper.
    if hasattr(creator, "load_base_module") and callable(creator.load_base_module):
        obj = creator.load_base_module()
        file = Path(getattr(obj, "__file__", "")) if getattr(obj, "__file__", None) else None
        return "load_base_module()", obj, file, rows

    return None, None, None, rows


def dataset_tD_scale(base):
    if base is None or not hasattr(base, "load_dataset"):
        return None, None, "base module/load_dataset unavailable"
    try:
        ds = base.load_dataset()
    except Exception as exc:
        return None, None, f"{type(exc).__name__}: {exc}"

    if not isinstance(ds, dict):
        return None, None, "load_dataset did not return dict"

    if "tD_scale" not in ds:
        return None, ds, "dataset lacks tD_scale"

    arr = np.asarray(ds["tD_scale"]).ravel()
    if arr.size == 0:
        return None, ds, "tD_scale empty"

    try:
        value = float(arr[0])
    except Exception as exc:
        return None, ds, f"{type(exc).__name__}: {exc}"
    return value, ds, ""


def deployment_workspace(creator):
    for sym in ("DEFAULT_DEPLOYMENT_WORKSPACE", "DEPLOYMENT_WORKSPACE"):
        if hasattr(creator, sym):
            return resolve_path(getattr(creator, sym)), sym
    return None, None


def deployment_loader(creator):
    for name in ("load_deployment_database", "load_deployment"):
        if hasattr(creator, name) and callable(getattr(creator, name)):
            return name, getattr(creator, name)
    return None, None


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R15")
    print("Selected SG7B16 Creator Residual Binding Audit")
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
ONLY R14'S tD_scale / deployment / X100 BINDING FAILURES WILL BE AUDITED.
""")

    r14 = load_json(R14_SUMMARY)
    if r14.get("selected_creator") != CREATOR_SOURCE.name:
        raise RuntimeError("R15 requires R14 to remain fixed to SG7B16.")

    creator = import_module_from(CREATOR_SOURCE, "_sg7b16_r15")

    workspace, workspace_sym = deployment_workspace(creator)
    base_name, base, base_file, module_rows = find_base_module(creator)
    td, dataset, td_error = dataset_tD_scale(base)
    loader_name, loader = deployment_loader(creator)

    print("AUTHORITATIVE CREATOR")
    print(f"  Source                  : {CREATOR_SOURCE.name}")

    print("\nBASE DATASET AUTHORITY")
    print(f"  Base module             : {base_name or 'UNRESOLVED'}")
    print(f"  Base file               : {base_file or 'UNRESOLVED'}")
    print(f"  load_dataset available  : {bool(base and hasattr(base, 'load_dataset'))}")

    print("\nRESIDUAL CALLER BINDINGS")
    print(f"  deployment_workspace    : {workspace}")
    print(f"  workspace exists        : {workspace.exists() if workspace else False}")
    print(f"  tD_scale                : {td if td is not None else 'UNRESOLVED'}")
    if td_error:
        print(f"  tD_scale diagnostic     : {td_error}")
    print(f"  deployment loader       : {loader_name or 'UNRESOLVED'}")

    deploy = None
    deploy_error = ""
    if loader is not None and workspace is not None and td is not None:
        try:
            deploy = loader(workspace, td)
        except Exception as exc:
            deploy_error = f"{type(exc).__name__}: {exc}"

    x100 = None
    if isinstance(deploy, dict) and "X100" in deploy:
        x100 = np.asarray(deploy["X100"])

    print("\nDEPLOYMENT DATABASE")
    print(f"  Helper success          : {isinstance(deploy, dict)}")
    if deploy_error:
        print(f"  Diagnostic              : {deploy_error}")

    print("\nFINAL X100")
    if isinstance(x100, np.ndarray):
        print(f"  Shape                   : {x100.shape}")
        print(f"  Dtype                   : {x100.dtype}")
        print(f"  Numeric                 : {np.issubdtype(x100.dtype, np.number)}")
        print(f"  Finite                  : {np.all(np.isfinite(x100))}")
        print(f"  Feature dim = 2         : {x100.ndim == 3 and x100.shape[-1] == 2}")
        print(f"  SHA-256                 : {sha256_array(x100)}")
    else:
        print("  NOT RESOLVED")

    save_csv(TABLE_BIND, [
        {"binding": "workspace", "resolved": workspace is not None,
         "basis": workspace_sym or "", "value": str(workspace) if workspace else ""},
        {"binding": "tD_scale", "resolved": td is not None,
         "basis": "authoritative_base.load_dataset()['tD_scale'][0]" if td is not None else "",
         "value": td if td is not None else "", "diagnostic": td_error},
        {"binding": "deployment_loader", "resolved": loader is not None,
         "basis": loader_name or "", "value": loader_name or ""},
    ])

    save_csv(TABLE_DATASET, [{
        "base_module": base_name or "",
        "base_file": str(base_file) if base_file else "",
        "dataset_loaded": isinstance(dataset, dict),
        "tD_scale_resolved": td is not None,
        "tD_scale": td if td is not None else "",
        "diagnostic": td_error,
    }])

    save_csv(TABLE_DEPLOY, [{
        "workspace": str(workspace) if workspace else "",
        "workspace_exists": workspace.exists() if workspace else False,
        "loader": loader_name or "",
        "helper_success": isinstance(deploy, dict),
        "keys": ";".join(sorted(deploy.keys())) if isinstance(deploy, dict) else "",
        "diagnostic": deploy_error,
    }])

    x_ok = bool(
        isinstance(x100, np.ndarray)
        and np.issubdtype(x100.dtype, np.number)
        and np.all(np.isfinite(x100))
        and x100.ndim == 3
        and x100.shape[-1] == 2
    )
    save_csv(TABLE_X100, [{
        "resolved": isinstance(x100, np.ndarray),
        "shape": str(x100.shape) if isinstance(x100, np.ndarray) else "",
        "dtype": str(x100.dtype) if isinstance(x100, np.ndarray) else "",
        "finite": bool(np.all(np.isfinite(x100))) if isinstance(x100, np.ndarray) else False,
        "feature_dim_2": bool(x100.ndim == 3 and x100.shape[-1] == 2) if isinstance(x100, np.ndarray) else False,
        "sha256": sha256_array(x100) if isinstance(x100, np.ndarray) else "",
    }])

    gates = [
        ("R14_creator_fixed_to_SG7B16", r14.get("selected_creator") == CREATOR_SOURCE.name),
        ("deployment_workspace_resolved", workspace is not None),
        ("deployment_workspace_exists", workspace.exists() if workspace else False),
        ("authoritative_base_module_resolved", base is not None),
        ("base_load_dataset_available", bool(base and hasattr(base, "load_dataset"))),
        ("tD_scale_resolved_from_base_dataset", td is not None),
        ("deployment_loader_resolved", loader is not None),
        ("deployment_database_constructed", isinstance(deploy, dict)),
        ("X100_resolved", isinstance(x100, np.ndarray)),
        ("X100_numeric_finite_feature_dim_2", x_ok),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_later_time_state_generated", True),
        ("no_creator_search_reopened", True),
    ]
    failed = [g for g, p in gates if not p]
    save_csv(TABLE_GATES, [{"gate": g, "passed": p} for g, p in gates])

    if not failed:
        status = "SG7B16_CREATOR_RESIDUAL_BINDINGS_RESOLVED"
        diagnosis = "AUTHORITATIVE_BASE_DATASET_CLOSES_tD_SCALE_AND_DEPLOYMENT_X100_CONTRACT"
        recommendation = (
            "Persist the resolved SG7B16 X100 contract and rerun only the selected SG7B16 "
            "100-day creator model inference against persisted frozen100. Do not reopen model, "
            "creator, workspace, or X100 discovery."
        )
        next_ms = "V15-SG7E1R26I-R16 — Repaired SG7B16 Frozen100 Creator Runtime Control"
    else:
        status = "SG7B16_CREATOR_RESIDUAL_BINDINGS_STILL_INCOMPLETE"
        diagnosis = "ONE_OR_MORE_SOURCE_AUTHENTIC_BASE_DATASET_OR_DEPLOYMENT_BINDINGS_REMAIN_UNRESOLVED"
        recommendation = (
            "Do not execute model.predict. Audit only the failed R15 binding gates. "
            "Do not broaden creator/model/X100 authority."
        )
        next_ms = "V15-SG7E1R26I-R15A — Final SG7B16 Residual Binding Repair"

    if isinstance(x100, np.ndarray):
        np.savez_compressed(
            NUM,
            X100=x100,
            tD_scale=np.asarray([td], dtype=np.float64),
        )

    save_csv(TABLE_DECISION, [{
        "status": status,
        "diagnosis": diagnosis,
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT, {
        "milestone": "V15-SG7E1R26I-R15",
        "status": status,
        "diagnosis": diagnosis,
        "creator": CREATOR_SOURCE.name,
        "workspace": str(workspace) if workspace else None,
        "base_module": base_name,
        "base_file": str(base_file) if base_file else None,
        "tD_scale": td,
        "deployment_loader": loader_name,
        "X100_shape": list(x100.shape) if isinstance(x100, np.ndarray) else None,
        "X100_sha256": sha256_array(x100) if isinstance(x100, np.ndarray) else None,
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })
    save_json(SUMMARY, {
        "milestone": "V15-SG7E1R26I-R15",
        "status": status,
        "diagnosis": diagnosis,
        "selected_creator": CREATOR_SOURCE.name,
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R15 RESIDUAL-BINDING VALIDATION")
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
    for p in (TABLE_BIND, TABLE_DATASET, TABLE_DEPLOY, TABLE_X100, TABLE_GATES, TABLE_DECISION):
        print(f"  {p.name}")
    if isinstance(x100, np.ndarray):
        print("\nNumerical:")
        print(f"  {NUM.name}")
    print("\nContract:")
    print(f"  {CONTRACT.name}")
    print("\nSummary:")
    print(f"  {SUMMARY.name}")
    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R15 SELECTED SG7B16 CREATOR RESIDUAL BINDING AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No alternative creator was searched.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
