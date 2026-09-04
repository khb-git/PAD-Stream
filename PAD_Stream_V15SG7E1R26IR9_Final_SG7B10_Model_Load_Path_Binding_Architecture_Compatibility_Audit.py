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
# PAD-Stream V15-SG7E1R26I-R9
# Final SG7B10 Model Load-Path Binding / Architecture Compatibility Audit
#
# DIAGNOSTIC-ONLY MODEL-BINDING MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO X100 WILL BE CHANGED.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
#
# PURPOSE
# -------
# R26I-R8 established:
#
#   evaluate_candidate(..., model, ...)
#       -> model.predict(deployment["X100"], ...)
#
# and found two authoritative loads:
#
#   model = tf.keras.models.load_model(FROZEN_MODEL_FILE)
#
# but artifact identity remained ambiguous because FROZEN_MODEL_FILE itself
# was not resolved.
#
# R26I-R9 resolves ONLY that source-defined symbol, verifies the exact file and
# SHA-256, loads the model with compile=False for architecture inspection only,
# and checks compatibility against the already-frozen X100 contract:
#
#   X100 shape = (2662, 201, 2)
#
# No inference is executed.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR9"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"

R26IR8_SUMMARY = (
    ROOT / "output" / "V15_SG7E1R26IR8"
    / "PAD_Stream_V15SG7E1R26IR8_Summary.json"
)

R26IR6_NUM = (
    ROOT / "output" / "V15_SG7E1R26IR6"
    / "V15SG7E1R26IR6_Reconstructed_X100.npz"
)

# Outputs
SYMBOL_TABLE = OUT / "V15SG7E1R26IR9_FROZEN_MODEL_FILE_Symbol_Trace.csv"
LOAD_TABLE = OUT / "V15SG7E1R26IR9_Authoritative_Load_Model_Trace.csv"
IDENTITY_TABLE = OUT / "V15SG7E1R26IR9_Resolved_Model_Identity.csv"
ARCH_TABLE = OUT / "V15SG7E1R26IR9_Model_Architecture_Contract.csv"
COMPAT_TABLE = OUT / "V15SG7E1R26IR9_X100_Model_Compatibility.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR9_Model_Load_Path_Binding_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26IR9_Final_Model_Load_Path_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR9_Summary.json"


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


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def import_source_module():
    name = "_pad_stream_sg7b10_r26ir9"
    spec = importlib.util.spec_from_file_location(name, SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not create SG7B10 import specification.")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def source_symbol_trace(tree, text, symbol):
    rows = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == symbol:
                    rows.append({
                        "line": node.lineno,
                        "symbol": symbol,
                        "expression": node_src(text, node.value),
                        "expression_type": type(node.value).__name__,
                    })

        elif isinstance(node, ast.AnnAssign):
            tgt = node.target
            if isinstance(tgt, ast.Name) and tgt.id == symbol:
                rows.append({
                    "line": node.lineno,
                    "symbol": symbol,
                    "expression": node_src(text, node.value) if node.value else "",
                    "expression_type": type(node.value).__name__ if node.value else "",
                })

    return rows


def load_model_trace(tree, text):
    rows = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call):
            continue

        cname = call_name(node.value)
        if not cname.endswith("load_model"):
            continue

        targets = [
            t.id for t in node.targets
            if isinstance(t, ast.Name)
        ]

        rows.append({
            "line": node.lineno,
            "target": ";".join(targets),
            "call": cname,
            "path_expression": node_src(text, node.value.args[0]) if node.value.args else "",
            "full_expression": node_src(text, node.value),
        })

    return rows


def normalize_shapes(shape_obj):
    if isinstance(shape_obj, list):
        seq = shape_obj
    else:
        seq = [shape_obj]

    out = []
    for shape in seq:
        if shape is None:
            out.append(None)
            continue
        out.append(tuple(None if d is None else int(d) for d in shape))
    return out


def compatible_with_x100(model_shape, xshape):
    """
    Keras input_shape includes batch dimension.
    X100 is the actual array supplied to predict.
    """
    if model_shape is None:
        return False

    if len(model_shape) != len(xshape):
        return False

    for expected, actual in zip(model_shape, xshape):
        if expected is None:
            continue
        if int(expected) != int(actual):
            return False

    return True


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R9")
    print("Final SG7B10 Model Load-Path Binding / Architecture Compatibility Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO X100 WILL BE CHANGED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
ONLY FROZEN_MODEL_FILE AND THE BOUND SG7B10 MODEL ARCHITECTURE WILL BE AUDITED.
""")

    prev = load_json(R26IR8_SUMMARY)
    if prev.get("status") != "SG7B10_DEPLOYMENT_PREDICT_MODEL_OBJECT_STILL_AMBIGUOUS":
        raise RuntimeError("R26I-R9 requires unresolved R26I-R8 model-object status.")

    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    if not R26IR6_NUM.exists():
        raise FileNotFoundError(R26IR6_NUM)

    text = safe_text(SOURCE)
    tree = ast.parse(text)

    # -------------------------------------------------------------------------
    # 1. Source-level symbol trace
    # -------------------------------------------------------------------------

    symbol_rows = source_symbol_trace(tree, text, "FROZEN_MODEL_FILE")
    save_csv(SYMBOL_TABLE, symbol_rows)

    load_rows = load_model_trace(tree, text)
    relevant_loads = [
        r for r in load_rows
        if "FROZEN_MODEL_FILE" in r["path_expression"]
    ]
    save_csv(LOAD_TABLE, relevant_loads)

    # -------------------------------------------------------------------------
    # 2. Runtime-resolve FROZEN_MODEL_FILE from imported SG7B10 globals
    # -------------------------------------------------------------------------

    sg7b10 = import_source_module()

    resolved_value = getattr(sg7b10, "FROZEN_MODEL_FILE", None)
    model_path = Path(resolved_value).resolve() if resolved_value is not None else None

    model_exists = bool(model_path and model_path.exists())
    model_sha = sha256_file(model_path) if model_exists else None

    save_csv(IDENTITY_TABLE, [{
        "symbol": "FROZEN_MODEL_FILE",
        "resolved": resolved_value is not None,
        "runtime_value": str(resolved_value) if resolved_value is not None else "",
        "resolved_path": str(model_path) if model_path is not None else "",
        "exists": model_exists,
        "sha256": model_sha or "",
        "filename": model_path.name if model_path is not None else "",
    }])

    # -------------------------------------------------------------------------
    # 3. Load exact X100 contract
    # -------------------------------------------------------------------------

    db = np.load(R26IR6_NUM, allow_pickle=True)
    x100 = np.asarray(db["X100"])
    db.close()

    xshape = tuple(int(d) for d in x100.shape)

    # -------------------------------------------------------------------------
    # 4. Architecture inspection only
    # -------------------------------------------------------------------------

    arch_rows = []
    compat_rows = []
    architecture_ready = False
    input_shapes = []
    output_shapes = []
    model_name = ""
    load_error = ""

    if model_exists:
        try:
            import tensorflow as tf
            model = tf.keras.models.load_model(model_path, compile=False)

            model_name = str(getattr(model, "name", ""))
            input_shapes = normalize_shapes(model.input_shape)
            output_shapes = normalize_shapes(model.output_shape)

            arch_rows.append({
                "model_name": model_name,
                "model_path": str(model_path),
                "input_shape": repr(model.input_shape),
                "output_shape": repr(model.output_shape),
                "input_count": len(input_shapes),
                "output_count": len(output_shapes),
                "parameter_count": int(model.count_params()),
            })

            for i, shape in enumerate(input_shapes):
                compatible = compatible_with_x100(shape, xshape)
                compat_rows.append({
                    "input_index": i,
                    "model_input_shape": repr(shape),
                    "X100_shape": repr(xshape),
                    "compatible": compatible,
                })

            architecture_ready = any(r["compatible"] for r in compat_rows)

        except Exception as exc:
            load_error = f"{type(exc).__name__}: {exc}"

    if not arch_rows:
        arch_rows.append({
            "model_name": "",
            "model_path": str(model_path) if model_path is not None else "",
            "input_shape": "",
            "output_shape": "",
            "input_count": "",
            "output_count": "",
            "parameter_count": "",
            "load_error": load_error,
        })

    if not compat_rows:
        compat_rows.append({
            "input_index": "",
            "model_input_shape": "",
            "X100_shape": repr(xshape),
            "compatible": False,
            "load_error": load_error,
        })

    save_csv(ARCH_TABLE, arch_rows)
    save_csv(COMPAT_TABLE, compat_rows)

    # -------------------------------------------------------------------------
    # 5. Decision
    # -------------------------------------------------------------------------

    if model_exists and architecture_ready:
        status = "SG7B10_FROZEN_MODEL_PATH_AND_X100_ARCHITECTURE_COMPATIBLE"
        diagnosis = (
            "FROZEN_MODEL_FILE_RESOLVES_TO_MODEL_WHOSE_INPUT_CONTRACT_ACCEPTS_SOURCE_AUTHENTIC_X100"
        )
        recommendation = (
            "The exact SG7B10 FROZEN_MODEL_FILE is resolved and its architecture is compatible "
            "with the frozen source-authentic X100 tensor. Proceed to a controlled 100-day "
            "runtime inference using only this model path and X100 artifact."
        )
        next_milestone = (
            "V15-SG7E1R26I-R10 — Bound SG7B10 100-Day Runtime Control"
        )

    elif model_exists:
        status = "SG7B10_FROZEN_MODEL_PATH_RESOLVED_ARCHITECTURE_INCOMPATIBLE_WITH_X100"
        diagnosis = (
            "FROZEN_MODEL_FILE_IS_EXACTLY_RESOLVED_BUT_ITS_MODEL_INPUT_SHAPE_CONTRADICTS_DEPLOYMENT_X100"
        )
        recommendation = (
            "Do not call model.predict and do not reshape X100. The exact SG7B10 frozen model path "
            "is now known, but its architecture does not accept the source-authentic deployment "
            "tensor. Audit the SG7B10 deployment prediction reshape/vectorization semantics and "
            "model-call preprocessing immediately surrounding model.predict()."
        )
        next_milestone = (
            "V15-SG7E1R26I-R10 — SG7B10 Predict-Time Reshape / Vectorization Contract Audit"
        )

    else:
        status = "SG7B10_FROZEN_MODEL_FILE_RUNTIME_PATH_NOT_RESOLVED"
        diagnosis = (
            "SOURCE_SYMBOL_EXISTS_BUT_RUNTIME_FROZEN_MODEL_ARTIFACT_PATH_DOES_NOT_RESOLVE"
        )
        recommendation = (
            "Do not call model.predict. Audit only FROZEN_MODEL_FILE path construction and its "
            "parent constants in SG7B10. Do not select a substitute model."
        )
        next_milestone = (
            "V15-SG7E1R26I-R10 — FROZEN_MODEL_FILE Parent-Path Resolution Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "source_symbol_records": len(symbol_rows),
        "authoritative_load_records": len(relevant_loads),
        "model_path_resolved": model_path is not None,
        "model_exists": model_exists,
        "model_path": str(model_path) if model_path is not None else "",
        "model_sha256": model_sha or "",
        "model_name": model_name,
        "model_input_shapes": repr(input_shapes),
        "model_output_shapes": repr(output_shapes),
        "X100_shape": repr(xshape),
        "architecture_compatible": architecture_ready,
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R9",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_source": str(SOURCE),
        "FROZEN_MODEL_FILE": {
            "source_records": symbol_rows,
            "resolved_value": str(resolved_value) if resolved_value is not None else None,
            "resolved_path": str(model_path) if model_path is not None else None,
            "exists": model_exists,
            "sha256": model_sha,
        },
        "architecture": {
            "model_name": model_name,
            "input_shapes": [list(s) if s is not None else None for s in input_shapes],
            "output_shapes": [list(s) if s is not None else None for s in output_shapes],
            "X100_shape": list(xshape),
            "compatible": architecture_ready,
        },
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "model_predict_executed": False,
            "X100_changed": False,
            "threshold_changed": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R9",
        "status": status,
        "diagnosis": diagnosis,
        "resolved_model_path": str(model_path) if model_path is not None else None,
        "resolved_model_sha256": model_sha,
        "architecture_compatible": architecture_ready,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("FROZEN_MODEL_FILE SOURCE TRACE")
    print(f"  Source assignments      : {len(symbol_rows)}")
    for r in symbol_rows:
        print(f"  line={r['line']} | FROZEN_MODEL_FILE <- {r['expression']}")

    print("\nAUTHORITATIVE LOAD_MODEL CALLS")
    print(f"  Records                 : {len(relevant_loads)}")
    for r in relevant_loads:
        print(f"  line={r['line']} | {r['target']} <- {r['full_expression']}")

    print("\nRESOLVED MODEL IDENTITY")
    print(f"  Runtime value           : {resolved_value}")
    print(f"  Resolved path           : {model_path}")
    print(f"  Exists                  : {model_exists}")
    if model_sha:
        print(f"  SHA-256                 : {model_sha}")

    print("\nARCHITECTURE")
    if model_exists and not load_error:
        print(f"  Model name              : {model_name}")
        print(f"  Input shape(s)          : {input_shapes}")
        print(f"  Output shape(s)         : {output_shapes}")
        print(f"  X100 shape              : {xshape}")
        print(f"  Compatible              : {architecture_ready}")
    else:
        print(f"  Load failure            : {load_error}")

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
        SYMBOL_TABLE,
        LOAD_TABLE,
        IDENTITY_TABLE,
        ARCH_TABLE,
        COMPAT_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R9 FINAL MODEL LOAD-PATH / ARCHITECTURE AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No X100 tensor was changed.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
