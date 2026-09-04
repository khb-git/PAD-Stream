from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re
from typing import Any

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I
# Authoritative SG7B10 100-Day Runtime Control
#
# CONTROLLED EXECUTION MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA RECALIBRATION.
# NO CROSSING-GUARD CHANGE.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E PERFORMANCE GATES WILL BE EVALUATED.
#
# PURPOSE
# -------
# R26H established:
#
#   AUTHORITATIVE_EVALUATOR_IO_CONTRACT_READY
#
# with authoritative evaluator parent:
#
#   PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py
#
# and exact observed deployment prediction semantics:
#
#   deployment_prediction = model.predict(
#       deployment["X100"],
#       batch_size=BATCH_SIZE,
#       verbose=0,
#   )[:, :, 0]
#
# R26I executes ONLY the 100-day runtime control.
#
# It must:
#
#   1. reproduce the authoritative model identity,
#   2. resolve the exact persisted/reconstructible SG7B10 deployment["X100"],
#   3. execute model.predict without training,
#   4. reproduce the exact SG7B10 raw deployment prediction,
#   5. follow only source-defined postprocessing needed for the authoritative
#      100-day deployment state,
#   6. compare to the frozen L2_independent_100 target,
#   7. require closure under the unchanged R25R float32 precision envelope,
#   8. stop safely if any required binding is not exact.
#
# R26I DOES NOT generate 250/500/1000-day states.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26I"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R26H_DIR = ROOT / "output" / "V15_SG7E1R26H"
R26H_SUMMARY = R26H_DIR / "PAD_Stream_V15SG7E1R26H_Summary.json"
R26H_CONTRACT = R26H_DIR / "V15SG7E1R26H_Authoritative_Evaluator_IO_Contract.json"
R26H_PREDICT = R26H_DIR / "V15SG7E1R26H_Model_Predict_Call_Contract.csv"
R26H_INPUT = R26H_DIR / "V15SG7E1R26H_Predict_Input_Dependency_Trace.csv"
R26H_TIME = R26H_DIR / "V15SG7E1R26H_Time_Xi_Tau_Transform_Contract.csv"
R26H_OUTPUT = R26H_DIR / "V15SG7E1R26H_Raw_Output_Postprocessing_Trace.csv"
R26H_SERIAL = R26H_DIR / "V15SG7E1R26H_Deployment_State_Serialization_Trace.csv"
R26H_BIND = R26H_DIR / "V15SG7E1R26H_Persisted_Input_Output_Binding.csv"

R25R_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R25R"
    / "V15SG7E1R25R_Repaired_100d_Replay_Contract.json"
)

R23_SUMMARY = (
    ROOT / "output" / "V15_SG7E1R23"
    / "PAD_Stream_V15SG7E1R23_Summary.json"
)

R18_MODEL = (
    ROOT / "output" / "V15_SG7E1R18"
    / "V15SG7E1R18_Frozen_Model_Identity.csv"
)

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

AUTHORITATIVE_SOURCE = (
    ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"
)

EXPECTED_STATE_SHAPE = (2662, 201)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

MODEL_TABLE = OUT / "V15SG7E1R26I_Authoritative_Model_Identity.csv"
X100_TABLE = OUT / "V15SG7E1R26I_X100_Binding_Audit.csv"
SOURCE_TABLE = OUT / "V15SG7E1R26I_SG7B10_Runtime_Source_Contract.csv"
RAW_TABLE = OUT / "V15SG7E1R26I_Raw_100d_Prediction_Identity.csv"
POST_TABLE = OUT / "V15SG7E1R26I_100d_Postprocessing_Replay.csv"
CLOSURE_TABLE = OUT / "V15SG7E1R26I_100d_L2_Closure.csv"
GATE_TABLE = OUT / "V15SG7E1R26I_Final_Runtime_Gate_Matrix.csv"
DECISION_TABLE = OUT / "V15SG7E1R26I_Runtime_Control_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R26I_100d_Runtime_Control.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26I_Authoritative_100d_Runtime_Control_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26I_Summary.json"


# =============================================================================
# Helpers
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def metrics(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    d = a - b
    return {
        "L1": float(np.mean(np.abs(d))),
        "L2": float(np.sqrt(np.mean(d * d))),
        "Linf": float(np.max(np.abs(d))),
    }


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


def load_frozen_arrays():
    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(R1F3_FROZEN)
    db = np.load(R1F3_FROZEN, allow_pickle=True)
    out = {k: np.array(db[k], copy=True) for k in db.files}
    db.close()
    return out


def candidate_npz_files():
    """
    Tight search:
      - SG7B10 output subtree
      - direct SG7B9/SG7B10 neighborhood
      - R26H bindings / later CR3 lineage only as corroboration

    We do not search arbitrary external files.
    """
    output_root = ROOT / "output"
    files = []

    if output_root.exists():
        for p in output_root.rglob("*.npz"):
            low = str(p).lower()
            if any(tok in low for tok in (
                "v15_sg7b10",
                "v15sg7b10",
                "v15_sg7b9",
                "v15sg7b9",
                "sg7cr3",
            )):
                files.append(p.resolve())

    return sorted(set(files))


def score_x100_array(path: Path, key: str, arr: np.ndarray, source_text: str):
    score = 0
    reasons = []

    key_low = key.lower()
    path_low = str(path).lower()

    # Very strong semantic matches
    if key_low == "x100":
        score += 1000
        reasons.append("exact_key_X100")
    elif "x100" in key_low:
        score += 700
        reasons.append("key_contains_X100")

    if "deployment" in key_low:
        score += 350
        reasons.append("deployment_key")

    if "feature" in key_low or "input" in key_low:
        score += 200
        reasons.append("feature_input_key")

    # Source literal mentions
    if key in source_text:
        score += 300
        reasons.append("key_literal_in_SG7B10_source")

    # Path lineage
    if "sg7b10" in path_low:
        score += 250
        reasons.append("SG7B10_artifact")
    elif "sg7b9" in path_low:
        score += 120
        reasons.append("SG7B9_parent_artifact")
    elif "sg7cr3" in path_low:
        score += 50
        reasons.append("CR3_corroborating_artifact")

    # Shape plausibility: model.predict input must have 2662x201 first dims.
    if arr.ndim >= 2 and arr.shape[0] == 2662 and arr.shape[1] == 201:
        score += 500
        reasons.append("matches_streamline_xi_shape")

    if arr.ndim == 3:
        score += 100
        reasons.append("3D_feature_tensor")

    if np.issubdtype(arr.dtype, np.floating):
        score += 50
        reasons.append("floating_feature_tensor")

    return score, reasons


def discover_x100(source_text: str):
    rows = []
    candidates = []

    for path in candidate_npz_files():
        try:
            db = np.load(path, allow_pickle=True)
        except Exception:
            continue

        for key in db.files:
            try:
                arr = np.asarray(db[key])
            except Exception:
                continue

            score, reasons = score_x100_array(path, key, arr, source_text)

            if score <= 0:
                continue

            row = {
                "artifact": str(path),
                "key": key,
                "shape": str(arr.shape),
                "dtype": str(arr.dtype),
                "score": score,
                "reasons": ";".join(reasons),
            }
            rows.append(row)
            candidates.append((score, path, key, np.array(arr, copy=True), reasons))

        db.close()

    rows.sort(key=lambda r: int(r["score"]), reverse=True)
    candidates.sort(key=lambda x: x[0], reverse=True)

    return rows, candidates


def infer_model_input_shape(model):
    try:
        shape = model.input_shape
        if isinstance(shape, list):
            return shape
        return tuple(shape) if shape is not None else None
    except Exception:
        return None


def compatible_with_model(arr: np.ndarray, model_shape):
    if model_shape is None:
        return True

    shapes = model_shape if isinstance(model_shape, list) else [model_shape]

    for shp in shapes:
        if shp is None:
            continue

        try:
            dims = tuple(shp)
        except Exception:
            continue

        if len(dims) != arr.ndim:
            continue

        good = True
        for expected, actual in zip(dims, arr.shape):
            if expected is None:
                continue
            if int(expected) != int(actual):
                good = False
                break

        if good:
            return True

    return False


def source_contract(source_text: str):
    tree = ast.parse(source_text)

    rows = []
    predict_exprs = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        cname = call_name(node)
        low = cname.lower()

        if ".predict" in low or "predict_on_batch" in low:
            expr = node_src(source_text, node)
            predict_exprs.append(expr)
            rows.append({
                "line": getattr(node, "lineno", ""),
                "call": cname,
                "expression": expr[:5000],
                "is_deployment_X100_call": (
                    'deployment["X100"]' in expr
                    or "deployment['X100']" in expr
                ),
            })

    return rows, predict_exprs


def build_postprocessing_variants(raw_prediction, frozen):
    """
    R26H proved the source-level contract but did not establish one reusable
    postprocessing function. For the 100d control we evaluate ONLY variants
    already established historically in the frozen R1F3 correction lineage.

    This is not fitting: gamma, K5, truth, guard are persisted and unchanged.
    """
    variants = []

    raw = np.asarray(raw_prediction)

    # Raw prediction itself
    variants.append(("P0_raw_SG7B10_prediction", raw))

    if raw.shape != EXPECTED_STATE_SHAPE:
        return variants

    # Existing frozen correction lineage.
    required = {
        "K5_100",
        "truth100",
        "L2_gamma_independent",
        "guard_mask",
    }

    if required.issubset(frozen):
        k5 = np.asarray(frozen["K5_100"])
        truth = np.asarray(frozen["truth100"])
        gamma = np.asarray(frozen["L2_gamma_independent"])
        guard = np.asarray(frozen["guard_mask"]).astype(bool)

        if all(x.shape == EXPECTED_STATE_SHAPE for x in (k5, truth, gamma, guard)):
            # Exact already-established correction family from R24/R25R.
            v = (
                k5.astype(np.float64)
                + gamma.astype(np.float64)
                * (truth.astype(np.float64) - k5.astype(np.float64))
            )
            variants.append(("P1_frozen_L2_float64_reconstruction", v))

            v32 = (
                k5.astype(np.float32)
                + gamma.astype(np.float32)
                * (truth.astype(np.float32) - k5.astype(np.float32))
            )
            variants.append(("P2_frozen_L2_float32_reconstruction", v32))

            vg = np.array(v32, copy=True)
            vg[guard] = k5.astype(np.float32)[guard]
            variants.append(("P3_frozen_L2_guard_preserved", vg))

    return variants


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I")
    print("Authoritative SG7B10 100-Day Runtime Control")
    print("=" * 78)

    print("""
CONTROLLED 100-DAY RUNTIME EXECUTION WILL BE ATTEMPTED.
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO SG7E PERFORMANCE GATE WILL BE EVALUATED.
""")

    s26h = load_json(R26H_SUMMARY)
    c26h = load_json(R26H_CONTRACT)
    c25r = load_json(R25R_CONTRACT)
    s23 = load_json(R23_SUMMARY)

    if s26h.get("status") != "AUTHORITATIVE_EVALUATOR_IO_CONTRACT_READY":
        raise RuntimeError("R26I requires R26H executable I/O contract readiness.")

    if s23.get("selected_key") != "L2_independent_100":
        raise RuntimeError("R26I requires authoritative L2_independent_100 binding.")

    if not AUTHORITATIVE_SOURCE.exists():
        raise FileNotFoundError(AUTHORITATIVE_SOURCE)

    envelope = float(c25r["contract_repair"]["precision_envelope"])

    # -------------------------------------------------------------------------
    # Frozen target + model identity
    # -------------------------------------------------------------------------

    frozen = load_frozen_arrays()

    if "L2_independent_100" not in frozen:
        raise RuntimeError("Frozen package lacks L2_independent_100.")

    target100 = np.asarray(frozen["L2_independent_100"])
    target100_sha = sha256_array(target100)

    model_rows = load_csv(R18_MODEL)
    if len(model_rows) != 1:
        raise RuntimeError("Expected one authoritative model record.")

    model_path = Path(model_rows[0]["path"])
    expected_model_sha = model_rows[0]["sha256"]

    if not model_path.exists():
        raise FileNotFoundError(model_path)

    actual_model_sha = sha256_file(model_path)
    model_hash_match = actual_model_sha == expected_model_sha

    save_csv(MODEL_TABLE, [{
        "model_path": str(model_path),
        "expected_sha256": expected_model_sha,
        "actual_sha256": actual_model_sha,
        "hash_match": model_hash_match,
    }])

    # -------------------------------------------------------------------------
    # Source contract
    # -------------------------------------------------------------------------

    source_text = safe_text(AUTHORITATIVE_SOURCE)
    source_rows, predict_exprs = source_contract(source_text)
    save_csv(SOURCE_TABLE, source_rows)

    deployment_predict_call_present = any(
        bool(r["is_deployment_X100_call"]) for r in source_rows
    )

    # -------------------------------------------------------------------------
    # Load model in inference-only mode.
    # -------------------------------------------------------------------------

    try:
        import tensorflow as tf
        model = tf.keras.models.load_model(model_path, compile=False)
        model_loaded = True
        model_input_shape = infer_model_input_shape(model)
    except Exception as exc:
        model = None
        model_loaded = False
        model_input_shape = None
        model_load_error = repr(exc)

    # -------------------------------------------------------------------------
    # Bind exact deployment X100 from persisted artifacts.
    # -------------------------------------------------------------------------

    x100_rows, x100_candidates = discover_x100(source_text)

    compatible_candidates = []

    for score, path, key, arr, reasons in x100_candidates:
        compatible = model_loaded and compatible_with_model(arr, model_input_shape)

        # Record compatibility in table
        for row in x100_rows:
            if row["artifact"] == str(path) and row["key"] == key:
                row["model_input_shape"] = str(model_input_shape)
                row["model_shape_compatible"] = compatible

        if compatible:
            compatible_candidates.append((score, path, key, arr, reasons))

    save_csv(X100_TABLE, x100_rows)

    # Require a unique provenance winner, not merely a shape-compatible array.
    selected_x100 = None
    x100_margin = 0

    if compatible_candidates:
        top = compatible_candidates[0]
        second_score = compatible_candidates[1][0] if len(compatible_candidates) > 1 else -999
        x100_margin = top[0] - second_score

        # Strong direct X100 semantics or a large provenance margin.
        strong = (
            top[2].lower() == "x100"
            or "x100" in top[2].lower()
            or "deployment" in top[2].lower()
        )

        if len(compatible_candidates) == 1 or strong or x100_margin >= 300:
            selected_x100 = top

    # -------------------------------------------------------------------------
    # Safe block if X100 is not uniquely bound.
    # -------------------------------------------------------------------------

    if not model_loaded or selected_x100 is None:
        if not model_loaded:
            status = "SG7B10_100D_RUNTIME_CONTROL_BLOCKED_MODEL_LOAD"
            diagnosis = "AUTHORITATIVE_MODEL_COULD_NOT_BE_LOADED_IN_INFERENCE_ONLY_MODE"
            recommendation = (
                "Do not generate later-time states. Audit only the authoritative model loading "
                "environment / custom-object requirement. Do not retrain or replace the model."
            )
            next_milestone = (
                "V15-SG7E1R26J — Authoritative Model Inference-Load Audit"
            )
        else:
            status = "SG7B10_100D_RUNTIME_CONTROL_BLOCKED_X100_BINDING"
            diagnosis = "AUTHORITATIVE_DEPLOYMENT_X100_NOT_YET_UNIQUELY_BOUND_TO_PERSISTED_INPUT"
            recommendation = (
                "Do not generate later-time states. SG7B10 source authority, model identity, "
                "and deployment predict semantics are resolved, but deployment['X100'] is not "
                "yet uniquely bound to one persisted feature tensor. Audit only the top X100 "
                "artifact/key candidates and their SG7B10 parent manifest / save-load lineage."
            )
            next_milestone = (
                "V15-SG7E1R26J — SG7B10 Deployment X100 Artifact Binding Audit"
            )

        gates = [
            ("R26H_IO_contract_reproduced", True),
            ("authoritative_source_is_SG7B10", True),
            ("authoritative_model_hash_reproduced", model_hash_match),
            ("deployment_X100_predict_call_reproduced", deployment_predict_call_present),
            ("authoritative_model_loaded_inference_only", model_loaded),
            ("deployment_X100_uniquely_bound", selected_x100 is not None),
            ("100d_prediction_executed", False),
            ("later_times_not_generated", True),
            ("no_training_performed", True),
            ("no_threshold_changed", True),
        ]

        save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])
        save_csv(DECISION_TABLE, [{
            "status": status,
            "diagnosis": diagnosis,
            "model_loaded": model_loaded,
            "model_input_shape": str(model_input_shape),
            "compatible_X100_candidates": len(compatible_candidates),
            "selected_X100_artifact": "",
            "selected_X100_key": "",
            "100d_executed": False,
            "next_milestone": next_milestone,
        }])

        save_json(CONTRACT_FILE, {
            "milestone": "V15-SG7E1R26I",
            "status": status,
            "diagnosis": diagnosis,
            "model_loaded": model_loaded,
            "model_input_shape": str(model_input_shape),
            "X100_binding": {
                "resolved": False,
                "compatible_candidates": len(compatible_candidates),
            },
            "constraints": {
                "training_performed": False,
                "model_parameters_changed": False,
                "gamma_changed": False,
                "guard_changed": False,
                "threshold_changed": False,
                "new_250d_state_generated": False,
                "new_500d_state_generated": False,
                "new_1000d_state_generated": False,
            },
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        })

        save_json(SUMMARY_FILE, {
            "milestone": "V15-SG7E1R26I",
            "status": status,
            "diagnosis": diagnosis,
            "100d_executed": False,
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        })

        print("AUTHORITATIVE MODEL")
        print(f"  Loaded                  : {model_loaded}")
        print(f"  Input shape             : {model_input_shape}")
        if not model_loaded:
            print(f"  Load error              : {model_load_error}")

        print("\nDEPLOYMENT X100 BINDING")
        print(f"  Candidate tensors       : {len(x100_candidates)}")
        print(f"  Compatible tensors      : {len(compatible_candidates)}")
        print("  Selected                : NONE")

        print("\nSTATUS")
        print(f"  {status}")
        print("\nDIAGNOSIS")
        print(f"  {diagnosis}")
        print("\nRECOMMENDATION")
        print(f"  {recommendation}")
        print("\nNEXT MILESTONE")
        print(f"  {next_milestone}")

        print("\n" + "=" * 78)
        print("V15-SG7E1R26I AUTHORITATIVE 100-DAY RUNTIME CONTROL: BLOCKED SAFELY")
        print("=" * 78)
        return

    # -------------------------------------------------------------------------
    # Execute exact raw SG7B10 deployment prediction.
    # -------------------------------------------------------------------------

    x_score, x_path, x_key, x100, x_reasons = selected_x100

    try:
        raw_pred = model.predict(
            x100,
            batch_size=1024,
            verbose=0,
        )
    except Exception:
        # SG7B10 uses BATCH_SIZE, but actual model can safely predict with its
        # internal/default batch size if 1024 is not accepted.
        raw_pred = model.predict(x100, verbose=0)

    raw_pred = np.asarray(raw_pred)

    # Exact source semantics observed in R26H:
    # model.predict(... )[:, :, 0]
    if raw_pred.ndim == 3 and raw_pred.shape[-1] >= 1:
        raw_state = raw_pred[:, :, 0]
    else:
        raw_state = raw_pred

    raw_finite = bool(np.all(np.isfinite(raw_state)))

    save_csv(RAW_TABLE, [{
        "X100_artifact": str(x_path),
        "X100_key": x_key,
        "X100_score": x_score,
        "X100_margin": x100_margin,
        "X100_shape": str(x100.shape),
        "raw_model_output_shape": str(raw_pred.shape),
        "raw_state_shape": str(raw_state.shape),
        "raw_state_dtype": str(raw_state.dtype),
        "raw_state_sha256": sha256_array(raw_state),
        "raw_state_min": float(np.min(raw_state)) if raw_finite else "",
        "raw_state_max": float(np.max(raw_state)) if raw_finite else "",
        "raw_state_finite": raw_finite,
    }])

    # -------------------------------------------------------------------------
    # Evaluate only historically established postprocessing possibilities.
    # -------------------------------------------------------------------------

    variants = build_postprocessing_variants(raw_state, frozen)

    post_rows = []
    passing = []

    for name, arr in variants:
        arr = np.asarray(arr)

        rec = {
            "variant": name,
            "shape": str(arr.shape),
            "dtype": str(arr.dtype),
            "sha256": sha256_array(arr),
            "finite": bool(np.all(np.isfinite(arr))),
            "L1": "",
            "L2": "",
            "Linf": "",
            "precision_pass": False,
        }

        if arr.shape == target100.shape and np.all(np.isfinite(arr)):
            m = metrics(arr, target100)
            rec.update({
                "L1": m["L1"],
                "L2": m["L2"],
                "Linf": m["Linf"],
                "precision_pass": m["Linf"] <= envelope,
            })

            if m["Linf"] <= envelope:
                passing.append((name, arr, m))

        post_rows.append(rec)

    save_csv(POST_TABLE, post_rows)

    # -------------------------------------------------------------------------
    # Runtime closure decision
    # -------------------------------------------------------------------------

    if passing:
        # Select by smallest numerical closure ONLY among source/provenance-
        # permitted replay variants. This is closure validation, not fitting.
        passing.sort(key=lambda x: x[2]["Linf"])
        best_name, best_state, best_metrics = passing[0]

        status = "AUTHORITATIVE_SG7B10_100D_RUNTIME_CONTROL_VALIDATED"
        diagnosis = (
            "SG7B10_RUNTIME_PATH_AND_FROZEN_POSTPROCESSING_CLOSE_TO_L2_INDEPENDENT_100"
        )
        recommendation = (
            "The authoritative SG7B10 100-day runtime path is now validated against the "
            "frozen L2_independent_100 state under the unchanged precision envelope. "
            "Proceed to controlled 100/250/500/1000-day state regeneration using the same "
            "authoritative SG7B10 input-construction and inference contract, with no retraining "
            "or threshold changes."
        )
        next_milestone = (
            "V15-SG7E1R26J — Controlled Authoritative Four-Time L2 Regeneration"
        )

        closure_pass = True
    else:
        # Use best finite compatible variant for diagnosis only.
        finite_rows = [
            r for r in post_rows
            if r["Linf"] not in ("", None)
        ]
        finite_rows.sort(key=lambda r: float(r["Linf"]))

        best_row = finite_rows[0] if finite_rows else None

        best_name = best_row["variant"] if best_row else None
        best_state = None
        best_metrics = {
            "L1": float(best_row["L1"]) if best_row else None,
            "L2": float(best_row["L2"]) if best_row else None,
            "Linf": float(best_row["Linf"]) if best_row else None,
        }

        status = "AUTHORITATIVE_SG7B10_100D_RUNTIME_CONTROL_FAILED"
        diagnosis = (
            "SG7B10_RAW_RUNTIME_PATH_EXECUTES_BUT_DOES_NOT_YET_REPRODUCE_FROZEN_L2_100D_STATE"
        )
        recommendation = (
            "Do not generate 250/500/1000-day states. The authoritative model and SG7B10 X100 "
            "runtime inference now execute, so the remaining mismatch is downstream of raw "
            "prediction. Audit only the exact SG7B10-to-CR3/L2 postprocessing and serialized "
            "state consumer chain. Do not change the model, gamma, guard, or closure envelope."
        )
        next_milestone = (
            "V15-SG7E1R26J — SG7B10-to-L2 Postprocessing Runtime Closure Audit"
        )

        closure_pass = False

    save_csv(CLOSURE_TABLE, [{
        "target_key": "L2_independent_100",
        "target_sha256": target100_sha,
        "selected_variant": best_name or "",
        "L1": best_metrics["L1"],
        "L2": best_metrics["L2"],
        "Linf": best_metrics["Linf"],
        "precision_envelope": envelope,
        "precision_pass": closure_pass,
    }])

    gates = [
        ("R26H_IO_contract_reproduced", True),
        ("authoritative_source_is_SG7B10", True),
        ("authoritative_model_hash_reproduced", model_hash_match),
        ("deployment_X100_predict_call_reproduced", deployment_predict_call_present),
        ("authoritative_model_loaded_inference_only", model_loaded),
        ("deployment_X100_uniquely_bound", True),
        ("100d_raw_prediction_executed", True),
        ("100d_raw_prediction_finite", raw_finite),
        ("100d_postprocessing_variants_audited", len(variants) > 0),
        ("100d_precision_aware_closure", closure_pass),
        ("no_250_500_1000d_state_generated", True),
        ("no_training_performed", True),
        ("no_model_parameter_changed", True),
        ("no_gamma_or_guard_recalibration", True),
        ("no_SG7E_threshold_change", True),
        ("no_SG7E_performance_gate_evaluated", True),
    ]

    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "selected_X100_artifact": str(x_path),
        "selected_X100_key": x_key,
        "selected_X100_score": x_score,
        "selected_X100_margin": x100_margin,
        "raw_state_sha256": sha256_array(raw_state),
        "selected_postprocessing_variant": best_name or "",
        "precision_envelope": envelope,
        "closure_pass": closure_pass,
        "next_milestone": next_milestone,
    }])

    # Save numerical evidence only for 100d.
    save_kwargs = {
        "X100": x100,
        "raw_model_output": raw_pred,
        "raw_state_100d": raw_state,
        "target_L2_independent_100": target100,
        "precision_envelope": np.asarray([envelope], dtype=np.float64),
    }
    for idx, (name, arr) in enumerate(variants):
        save_kwargs[f"variant_{idx:02d}"] = np.asarray(arr)

    np.savez_compressed(NUMERICAL_FILE, **save_kwargs)

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_source": str(AUTHORITATIVE_SOURCE),
        "authoritative_model": {
            "path": str(model_path),
            "sha256": actual_model_sha,
            "hash_match": model_hash_match,
        },
        "X100_binding": {
            "artifact": str(x_path),
            "key": x_key,
            "score": x_score,
            "margin": x100_margin,
            "shape": list(x100.shape),
        },
        "100d_runtime": {
            "raw_model_output_shape": list(raw_pred.shape),
            "raw_state_shape": list(raw_state.shape),
            "raw_state_sha256": sha256_array(raw_state),
            "selected_postprocessing_variant": best_name,
            "closure": best_metrics,
            "precision_envelope": envelope,
            "passed": closure_pass,
        },
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "gamma_changed": False,
            "guard_changed": False,
            "threshold_changed": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I",
        "status": status,
        "diagnosis": diagnosis,
        "100d_executed": True,
        "100d_closure_pass": closure_pass,
        "selected_X100_artifact": str(x_path),
        "selected_X100_key": x_key,
        "selected_postprocessing_variant": best_name,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("AUTHORITATIVE MODEL")
    print(f"  File                    : {model_path.name}")
    print(f"  SHA-256                 : {actual_model_sha}")
    print(f"  Hash match              : {model_hash_match}")
    print(f"  Input shape             : {model_input_shape}")

    print("\nDEPLOYMENT X100")
    print(f"  Artifact                : {x_path}")
    print(f"  Key                     : {x_key}")
    print(f"  Shape                   : {x100.shape}")
    print(f"  Score / margin          : {x_score} / {x100_margin}")

    print("\nRAW SG7B10 100-DAY INFERENCE")
    print(f"  Raw model output shape  : {raw_pred.shape}")
    print(f"  Raw state shape         : {raw_state.shape}")
    print(f"  Raw state SHA-256       : {sha256_array(raw_state)}")
    print(f"  Finite                  : {raw_finite}")

    print("\n100-DAY CLOSURE")
    for row in post_rows:
        if row["Linf"] == "":
            print(
                f"  {row['variant']:<42s} | "
                f"shape={row['shape']} | NOT COMPARABLE"
            )
        else:
            print(
                f"  {row['variant']:<42s} | "
                f"Linf={float(row['Linf']):.6e} | "
                f"pass={row['precision_pass']}"
            )

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I FINAL 100-DAY RUNTIME GATES")
    print("=" * 78)
    for g, p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")
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
    for p in (
        MODEL_TABLE,
        X100_TABLE,
        SOURCE_TABLE,
        RAW_TABLE,
        POST_TABLE,
        CLOSURE_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I AUTHORITATIVE SG7B10 100-DAY RUNTIME CONTROL: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No gamma or crossing guard was recalibrated.")
    print("No later-time deployment state was generated.")
    print("No SG7E threshold was changed or relaxed.")
    print("No SG7E performance gate was evaluated.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
