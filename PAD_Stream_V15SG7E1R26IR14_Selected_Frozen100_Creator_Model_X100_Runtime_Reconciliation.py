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
# PAD-Stream V15-SG7E1R26I-R14
# Selected Frozen100 Creator Model / X100 Runtime Reconciliation
#
# CONTROLLED CREATOR-REPLAY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA RECALIBRATION.
# NO CROSSING-GUARD CHANGE.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO ALTERNATIVE CREATOR WILL BE SEARCHED.
#
# PURPOSE
# -------
# R26I-R13 resolved the historical frozen100 creator lineage to:
#
#   PAD_Stream_V15SG7B16_Controlled_Front_Preserving_TOF_Refinement.py
#
# R26I-R14 now resolves ONLY that creator's:
#
#   1. frozen_model artifact,
#   2. deployment workspace / X100 constructor,
#   3. exact 100-day frozen_model.predict path,
#
# and compares the replayed 100-day creator output against persisted frozen100.
#
# No numerical fitting, model substitution, or source broadening is permitted.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR14"
OUT.mkdir(parents=True, exist_ok=True)

CREATOR_SOURCE = ROOT / "PAD_Stream_V15SG7B16_Controlled_Front_Preserving_TOF_Refinement.py"

R13_DIR = ROOT / "output" / "V15_SG7E1R26IR13"
R13_SUMMARY = R13_DIR / "PAD_Stream_V15SG7E1R26IR13_Summary.json"

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

R25R_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R25R"
    / "V15SG7E1R25R_Repaired_100d_Replay_Contract.json"
)

# Outputs
SOURCE_TABLE = OUT / "V15SG7E1R26IR14_Selected_Creator_Identity.csv"
MODEL_TRACE_TABLE = OUT / "V15SG7E1R26IR14_Frozen_Model_Load_Trace.csv"
MODEL_ID_TABLE = OUT / "V15SG7E1R26IR14_Frozen_Model_Identity.csv"
DEPLOY_TABLE = OUT / "V15SG7E1R26IR14_Deployment_Object_Construction.csv"
X100_TABLE = OUT / "V15SG7E1R26IR14_X100_Identity.csv"
RUNTIME_TABLE = OUT / "V15SG7E1R26IR14_Creator_100d_Runtime.csv"
CLOSURE_TABLE = OUT / "V15SG7E1R26IR14_Frozen100_Closure.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR14_Final_Reconciliation_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR14_Reconciliation_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R26IR14_Creator_100d_Runtime_Reconciliation.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR14_Selected_Creator_Runtime_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR14_Summary.json"


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


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


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def safe_text(path: Path):
    return path.read_text(encoding="utf-8", errors="ignore")


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


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


def import_creator():
    name = "_pad_stream_sg7b16_r26ir14"
    spec = importlib.util.spec_from_file_location(name, CREATOR_SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not create SG7B16 import specification.")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def assignment_map(tree, text):
    amap = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    amap[tgt.id] = {
                        "line": node.lineno,
                        "rhs": node_src(text, node.value),
                        "rhs_node": node.value,
                    }
    return amap


def find_frozen_model_loads(tree, text):
    rows = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if not call_name(node.value).endswith("load_model"):
            continue

        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "frozen_model" not in targets:
            continue

        rows.append({
            "line": node.lineno,
            "target": "frozen_model",
            "path_expression": node_src(text, node.value.args[0]) if node.value.args else "",
            "full_expression": node_src(text, node.value),
        })
    return rows


def find_frozen100_predict(tree, text):
    rows = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "frozen100" not in targets:
            continue
        rhs = node_src(text, node.value)
        if "frozen_model.predict" in rhs:
            rows.append({
                "line": node.lineno,
                "expression": rhs,
            })
    return rows


def resolve_runtime_path(value):
    if value is None:
        return None
    p = Path(value)
    if not p.is_absolute():
        p = (ROOT / p)
    return p.resolve()


def model_path_from_module(mod, load_rows):
    """
    Resolve the exact SG7B16 frozen-model path from runtime module globals.
    Preference is source-semantic:
      - direct symbol used by load_model
      - no model scanning
    """
    if not load_rows:
        return None, None

    expr = load_rows[0]["path_expression"].strip()

    if expr.isidentifier() and hasattr(mod, expr):
        value = getattr(mod, expr)
        return resolve_runtime_path(value), expr

    # Common source symbols.
    for symbol in (
        "FROZEN_MODEL_FILE",
        "FROZEN_MODEL_PATH",
        "BASE_MODEL_FILE",
        "BASE_MODEL_PATH",
        "MODEL_FILE",
    ):
        if hasattr(mod, symbol) and symbol in expr:
            return resolve_runtime_path(getattr(mod, symbol)), symbol

    return None, None


def find_deployment_loader(mod):
    candidates = [
        "load_deployment_database",
        "load_deployment",
        "build_deployment_database",
        "build_deployment",
    ]
    found = [name for name in candidates if hasattr(mod, name) and callable(getattr(mod, name))]
    return found


def infer_tD_scale(mod):
    """
    Resolve tD_scale only from source/module semantics. No fabricated value.
    """
    if hasattr(mod, "tD_scale"):
        try:
            return float(getattr(mod, "tD_scale")), "module.tD_scale"
        except Exception:
            pass

    # Try authoritative/base dataset loader if exposed.
    for loader_name in ("load_base_module",):
        if hasattr(mod, loader_name) and callable(getattr(mod, loader_name)):
            base = getattr(mod, loader_name)()
            if hasattr(base, "load_dataset") and callable(base.load_dataset):
                ds = base.load_dataset()
                if isinstance(ds, dict) and "tD_scale" in ds:
                    arr = np.asarray(ds["tD_scale"]).ravel()
                    if arr.size:
                        return float(arr[0]), "base.load_dataset()['tD_scale'][0]"
    return None, None


def infer_workspace(mod):
    for symbol in (
        "DEFAULT_DEPLOYMENT_WORKSPACE",
        "DEPLOYMENT_WORKSPACE",
        "DEFAULT_WORKSPACE",
    ):
        if hasattr(mod, symbol):
            p = resolve_runtime_path(getattr(mod, symbol))
            if p is not None:
                return p, symbol
    return None, None


def error_metrics(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.shape != b.shape:
        return None
    d = a - b
    return {
        "L1": float(np.mean(np.abs(d))),
        "L2": float(np.sqrt(np.mean(d * d))),
        "Linf": float(np.max(np.abs(d))),
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R14")
    print("Selected Frozen100 Creator Model / X100 Runtime Reconciliation")
    print("=" * 78)

    print("""
CONTROLLED 100-DAY CREATOR REPLAY WILL BE ATTEMPTED.
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO ALTERNATIVE FROZEN100 CREATOR WILL BE SEARCHED.
""")

    prev = load_json(R13_SUMMARY)
    if prev.get("status") != "FROZEN100_DIRECT_CREATOR_LINEAGE_RESOLVED":
        raise RuntimeError("R26I-R14 requires resolved R13 frozen100 creator lineage.")

    selected_creator = prev.get("selected_creator")
    if selected_creator != CREATOR_SOURCE.name:
        raise RuntimeError(
            f"R13 selected {selected_creator}; R14 is fixed to {CREATOR_SOURCE.name}."
        )

    if not CREATOR_SOURCE.exists():
        raise FileNotFoundError(CREATOR_SOURCE)

    text = safe_text(CREATOR_SOURCE)
    tree = ast.parse(text)
    amap = assignment_map(tree, text)

    load_rows = find_frozen_model_loads(tree, text)
    predict_rows = find_frozen100_predict(tree, text)

    save_csv(SOURCE_TABLE, [{
        "creator_source": CREATOR_SOURCE.name,
        "creator_path": str(CREATOR_SOURCE),
        "creator_sha256": sha256_file(CREATOR_SOURCE),
        "frozen_model_load_records": len(load_rows),
        "frozen100_predict_records": len(predict_rows),
    }])

    save_csv(MODEL_TRACE_TABLE, load_rows)

    creator = import_creator()

    model_path, model_symbol = model_path_from_module(creator, load_rows)
    model_exists = bool(model_path and model_path.exists())
    model_sha = sha256_file(model_path) if model_exists else None

    save_csv(MODEL_ID_TABLE, [{
        "resolved": model_path is not None,
        "resolution_symbol": model_symbol or "",
        "model_path": str(model_path) if model_path else "",
        "exists": model_exists,
        "sha256": model_sha or "",
    }])

    workspace, workspace_symbol = infer_workspace(creator)
    tD_scale, td_basis = infer_tD_scale(creator)
    loader_names = find_deployment_loader(creator)

    deployment = None
    deployment_error = ""
    deployment_loader_used = ""

    # We only call an exact creator helper if all required arguments are
    # source-resolved. No fabricated values.
    for loader_name in loader_names:
        fn = getattr(creator, loader_name)
        try:
            if workspace is not None and tD_scale is not None:
                deployment = fn(workspace, tD_scale)
                deployment_loader_used = loader_name
                break
            elif workspace is not None:
                deployment = fn(workspace)
                deployment_loader_used = loader_name
                break
        except TypeError:
            continue
        except Exception as exc:
            deployment_error = f"{type(exc).__name__}: {exc}"

    save_csv(DEPLOY_TABLE, [{
        "workspace_resolved": workspace is not None,
        "workspace_symbol": workspace_symbol or "",
        "workspace": str(workspace) if workspace else "",
        "workspace_exists": workspace.exists() if workspace else False,
        "tD_scale_resolved": tD_scale is not None,
        "tD_scale": tD_scale if tD_scale is not None else "",
        "tD_scale_basis": td_basis or "",
        "deployment_loader_candidates": ";".join(loader_names),
        "deployment_loader_used": deployment_loader_used,
        "deployment_success": isinstance(deployment, dict),
        "deployment_error": deployment_error,
    }])

    x100 = None
    if isinstance(deployment, dict) and "X100" in deployment:
        x100 = np.asarray(deployment["X100"])

    save_csv(X100_TABLE, [{
        "X100_resolved": isinstance(x100, np.ndarray),
        "shape": str(x100.shape) if isinstance(x100, np.ndarray) else "",
        "dtype": str(x100.dtype) if isinstance(x100, np.ndarray) else "",
        "finite": bool(np.all(np.isfinite(x100))) if isinstance(x100, np.ndarray) else False,
        "sha256": sha256_array(x100) if isinstance(x100, np.ndarray) else "",
    }])

    # -------------------------------------------------------------------------
    # Controlled creator runtime
    # -------------------------------------------------------------------------

    runtime100 = None
    runtime_error = ""

    if model_exists and isinstance(x100, np.ndarray):
        try:
            import tensorflow as tf
            frozen_model = tf.keras.models.load_model(model_path, compile=False)
            out = np.asarray(
                frozen_model.predict(
                    x100,
                    batch_size=getattr(creator, "BATCH_SIZE", 1024),
                    verbose=0,
                )
            )
            if out.ndim == 3 and out.shape[-1] >= 1:
                runtime100 = np.asarray(out[:, :, 0])
            else:
                runtime100 = np.asarray(out)
        except Exception as exc:
            runtime_error = f"{type(exc).__name__}: {exc}"

    save_csv(RUNTIME_TABLE, [{
        "runtime_executed": runtime100 is not None,
        "shape": str(runtime100.shape) if runtime100 is not None else "",
        "dtype": str(runtime100.dtype) if runtime100 is not None else "",
        "finite": bool(np.all(np.isfinite(runtime100))) if runtime100 is not None else False,
        "min": float(np.min(runtime100)) if runtime100 is not None else "",
        "max": float(np.max(runtime100)) if runtime100 is not None else "",
        "sha256": sha256_array(runtime100) if runtime100 is not None else "",
        "runtime_error": runtime_error,
    }])

    # Persisted frozen100
    fdb = np.load(R1F3_FROZEN, allow_pickle=True)
    if "frozen100" not in fdb.files:
        fdb.close()
        raise RuntimeError("R1F3 frozen package lacks frozen100.")
    frozen100 = np.asarray(fdb["frozen100"])
    fdb.close()

    r25r = load_json(R25R_CONTRACT)
    envelope = float(
        r25r.get("contract_repair", {}).get(
            "precision_envelope",
            1.192093e-07,
        )
    )

    metrics = error_metrics(runtime100, frozen100) if runtime100 is not None else None
    closure_pass = bool(metrics and metrics["Linf"] <= envelope)

    save_csv(CLOSURE_TABLE, [{
        "runtime_available": runtime100 is not None,
        "runtime_sha256": sha256_array(runtime100) if runtime100 is not None else "",
        "frozen100_sha256": sha256_array(frozen100),
        "runtime_shape": str(runtime100.shape) if runtime100 is not None else "",
        "frozen100_shape": str(frozen100.shape),
        "shape_match": bool(runtime100 is not None and runtime100.shape == frozen100.shape),
        "L1": metrics["L1"] if metrics else "",
        "L2": metrics["L2"] if metrics else "",
        "Linf": metrics["Linf"] if metrics else "",
        "precision_envelope": envelope,
        "precision_pass": closure_pass,
    }])

    gates = [
        ("R13_selected_creator_is_SG7B16", selected_creator == CREATOR_SOURCE.name),
        ("creator_source_exists", CREATOR_SOURCE.exists()),
        ("frozen_model_load_path_resolved", model_path is not None),
        ("frozen_model_artifact_exists", model_exists),
        ("deployment_workspace_resolved", workspace is not None),
        ("deployment_workspace_exists", workspace.exists() if workspace else False),
        ("tD_scale_resolved", tD_scale is not None),
        ("deployment_X100_resolved", isinstance(x100, np.ndarray)),
        ("deployment_X100_finite", bool(np.all(np.isfinite(x100))) if isinstance(x100, np.ndarray) else False),
        ("creator_100d_runtime_executed", runtime100 is not None),
        ("creator_100d_runtime_finite", bool(np.all(np.isfinite(runtime100))) if runtime100 is not None else False),
        ("creator_100d_closes_to_frozen100", closure_pass),
        ("no_250_500_1000d_state_generated", True),
        ("no_training_performed", True),
        ("no_model_parameter_changed", True),
        ("no_threshold_changed", True),
        ("no_alternative_creator_searched", True),
    ]

    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])
    failed = [g for g, p in gates if not p]

    if not failed:
        status = "SG7B16_FROZEN100_CREATOR_RUNTIME_RECONCILED"
        diagnosis = (
            "SELECTED_SG7B16_CREATOR_MODEL_AND_X100_REPRODUCE_PERSISTED_FROZEN100"
        )
        recommendation = (
            "The selected SG7B16 frozen100 creator is fully reconciled: its exact model artifact, "
            "deployment/X100 construction, and 100-day runtime reproduce persisted frozen100 within "
            "the unchanged precision envelope. Proceed to reconstruct the downstream frozen100 -> "
            "K5_100 -> L2_independent_100 correction chain before generating later times."
        )
        next_milestone = (
            "V15-SG7E1R26J — 100-Day Downstream Correction-Chain Runtime Replay"
        )
    else:
        status = "SG7B16_FROZEN100_CREATOR_RUNTIME_RECONCILIATION_INCOMPLETE"
        diagnosis = (
            "SELECTED_CREATOR_LINEAGE_IS_FIXED_BUT_ONE_OR_MORE_MODEL_DEPLOYMENT_OR_CLOSURE_BINDINGS_FAIL"
        )
        recommendation = (
            "Do not generate later-time states. Audit only the failed R14 gates in the selected "
            "SG7B16 creator lineage. Do not reopen SG7B13, model discovery, or X100 discovery."
        )
        next_milestone = (
            "V15-SG7E1R26I-R15 — Selected SG7B16 Creator Residual Binding Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "selected_creator": selected_creator,
        "model_path": str(model_path) if model_path else "",
        "model_sha256": model_sha or "",
        "X100_sha256": sha256_array(x100) if isinstance(x100, np.ndarray) else "",
        "runtime_sha256": sha256_array(runtime100) if runtime100 is not None else "",
        "frozen100_sha256": sha256_array(frozen100),
        "Linf": metrics["Linf"] if metrics else "",
        "precision_envelope": envelope,
        "closure_pass": closure_pass,
        "failed_gates": ";".join(failed),
        "next_milestone": next_milestone,
    }])

    if runtime100 is not None and isinstance(x100, np.ndarray):
        np.savez_compressed(
            NUMERICAL_FILE,
            X100=x100,
            creator_runtime100=runtime100,
            frozen100=frozen100,
            precision_envelope=np.asarray([envelope], dtype=np.float64),
        )

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R14",
        "status": status,
        "diagnosis": diagnosis,
        "selected_creator": selected_creator,
        "creator_source": str(CREATOR_SOURCE),
        "model": {
            "path": str(model_path) if model_path else None,
            "sha256": model_sha,
            "resolution_symbol": model_symbol,
        },
        "deployment": {
            "workspace": str(workspace) if workspace else None,
            "workspace_symbol": workspace_symbol,
            "tD_scale": tD_scale,
            "tD_scale_basis": td_basis,
            "loader": deployment_loader_used or None,
            "X100_shape": list(x100.shape) if isinstance(x100, np.ndarray) else None,
            "X100_sha256": sha256_array(x100) if isinstance(x100, np.ndarray) else None,
        },
        "runtime100": {
            "executed": runtime100 is not None,
            "shape": list(runtime100.shape) if runtime100 is not None else None,
            "sha256": sha256_array(runtime100) if runtime100 is not None else None,
            "closure": metrics,
            "precision_envelope": envelope,
            "passed": closure_pass,
        },
        "failed_gates": failed,
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "threshold_changed": False,
            "alternative_creator_searched": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R14",
        "status": status,
        "diagnosis": diagnosis,
        "selected_creator": selected_creator,
        "closure_pass": closure_pass,
        "failed_gates": failed,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    print("SELECTED FROZEN100 CREATOR")
    print(f"  Source                  : {CREATOR_SOURCE.name}")
    print(f"  Source SHA-256          : {sha256_file(CREATOR_SOURCE)}")

    print("\nFROZEN MODEL")
    print(f"  Load records            : {len(load_rows)}")
    print(f"  Model path              : {model_path}")
    print(f"  Model exists            : {model_exists}")
    if model_sha:
        print(f"  Model SHA-256           : {model_sha}")

    print("\nDEPLOYMENT CONTRACT")
    print(f"  Workspace               : {workspace}")
    print(f"  Workspace exists        : {workspace.exists() if workspace else False}")
    print(f"  tD_scale                : {tD_scale}")
    print(f"  Loader                  : {deployment_loader_used or 'UNRESOLVED'}")

    print("\nX100")
    if isinstance(x100, np.ndarray):
        print(f"  Shape                   : {x100.shape}")
        print(f"  Dtype                   : {x100.dtype}")
        print(f"  SHA-256                 : {sha256_array(x100)}")
    else:
        print("  NOT RESOLVED")

    print("\nCREATOR 100-DAY RUNTIME")
    if runtime100 is not None:
        print(f"  Shape                   : {runtime100.shape}")
        print(f"  Range                   : {np.min(runtime100):.6f} -> {np.max(runtime100):.6f}")
        print(f"  SHA-256                 : {sha256_array(runtime100)}")
    else:
        print(f"  NOT EXECUTED            : {runtime_error}")

    print("\nFROZEN100 CLOSURE")
    if metrics:
        print(f"  L1                      : {metrics['L1']:.6e}")
        print(f"  L2                      : {metrics['L2']:.6e}")
        print(f"  Linf                    : {metrics['Linf']:.6e}")
    print(f"  Precision envelope      : {envelope:.6e}")
    print(f"  Closure pass            : {closure_pass}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R14 FINAL RECONCILIATION GATES")
    print("=" * 78)
    for gate, passed in gates:
        print(f"[{'PASS' if passed else 'FAIL'}] {gate}")
    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    if failed:
        print("\nFAILED GATES")
        for gate in failed:
            print(f"  {gate}")
    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\nTables:")
    for p in (
        SOURCE_TABLE,
        MODEL_TRACE_TABLE,
        MODEL_ID_TABLE,
        DEPLOY_TABLE,
        X100_TABLE,
        RUNTIME_TABLE,
        CLOSURE_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    if runtime100 is not None and isinstance(x100, np.ndarray):
        print("\nNumerical:")
        print(f"  {NUMERICAL_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R14 SELECTED FROZEN100 CREATOR RECONCILIATION: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No alternative creator was searched.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
