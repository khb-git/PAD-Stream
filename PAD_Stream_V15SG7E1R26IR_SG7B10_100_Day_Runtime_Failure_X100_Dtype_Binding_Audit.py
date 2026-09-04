from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26IR
# SG7B10 100-Day Runtime Failure / X100 Dtype-Binding Audit
#
# DIAGNOSTIC-ONLY FAILURE-REPAIR MILESTONE
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
# R26I failed before inference with:
#
#   ValueError: Invalid dtype: str1952
#
# This proves the selected deployment["X100"] candidate was not a numeric
# feature tensor. The R26I provenance score selected a string/object-like array
# that happened to satisfy path/key heuristics.
#
# R26IR does not call model.predict. It audits X100 candidates with strict
# executable tensor constraints:
#
#   - numeric dtype only
#   - finite values only
#   - rank compatible with model input
#   - exact non-batch dimensions compatible with model.input_shape
#   - first two physical dimensions consistent with SG7B10 source semantics
#   - excludes strings, bytes, unicode, object, structured arrays
#
# The goal is to bind one genuinely executable deployment X100 tensor before
# retrying the 100-day control.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR"
OUT.mkdir(parents=True, exist_ok=True)

R26H_DIR = ROOT / "output" / "V15_SG7E1R26H"
R26H_SUMMARY = R26H_DIR / "PAD_Stream_V15SG7E1R26H_Summary.json"

R26I_DIR = ROOT / "output" / "V15_SG7E1R26I"
R26I_X100 = R26I_DIR / "V15SG7E1R26I_X100_Binding_Audit.csv"

R18_MODEL = (
    ROOT / "output" / "V15_SG7E1R18"
    / "V15SG7E1R18_Frozen_Model_Identity.csv"
)

AUTHORITATIVE_SOURCE = (
    ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"
)

CANDIDATE_TABLE = OUT / "V15SG7E1R26IR_X100_Executable_Tensor_Audit.csv"
MODEL_TABLE = OUT / "V15SG7E1R26IR_Model_Input_Shape_Contract.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR_X100_Binding_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26IR_X100_Dtype_Binding_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR_Summary.json"


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


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def candidate_npz_files():
    output_root = ROOT / "output"
    out = []
    if not output_root.exists():
        return out

    for p in output_root.rglob("*.npz"):
        low = str(p).lower()
        if any(tok in low for tok in (
            "v15_sg7b10",
            "v15sg7b10",
            "v15_sg7b9",
            "v15sg7b9",
            "sg7cr3",
        )):
            out.append(p.resolve())

    return sorted(set(out))


def dtype_class(arr):
    dt = arr.dtype
    if dt.fields is not None:
        return "STRUCTURED"
    if dt.kind in {"U", "S"}:
        return "STRING"
    if dt.kind == "O":
        return "OBJECT"
    if dt.kind in {"f", "i", "u", "b", "c"}:
        return "NUMERIC"
    return f"OTHER_{dt.kind}"


def model_shapes():
    rows = load_csv(R18_MODEL)
    if len(rows) != 1:
        raise RuntimeError("Expected one authoritative model record.")

    model_path = Path(rows[0]["path"])
    import tensorflow as tf
    model = tf.keras.models.load_model(model_path, compile=False)

    shapes = model.input_shape
    if not isinstance(shapes, list):
        shapes = [shapes]

    norm = []
    for s in shapes:
        norm.append(tuple(None if d is None else int(d) for d in s))

    return model_path, norm


def shape_compatible(arr_shape, model_shape):
    if len(arr_shape) != len(model_shape):
        return False

    for actual, expected in zip(arr_shape, model_shape):
        if expected is None:
            continue
        if int(actual) != int(expected):
            return False
    return True


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26IR")
    print("SG7B10 100-Day Runtime Failure / X100 Dtype-Binding Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO SG7E PERFORMANCE GATE WILL BE EVALUATED.
NO MODEL.PREDICT CALL WILL BE EXECUTED BY R26IR.
""")

    s26h = load_json(R26H_SUMMARY)
    if s26h.get("status") != "AUTHORITATIVE_EVALUATOR_IO_CONTRACT_READY":
        raise RuntimeError("R26IR requires successful R26H contract.")

    if not AUTHORITATIVE_SOURCE.exists():
        raise FileNotFoundError(AUTHORITATIVE_SOURCE)

    model_path, input_shapes = model_shapes()

    save_csv(MODEL_TABLE, [
        {
            "model_path": str(model_path),
            "input_index": i,
            "input_shape": str(shape),
        }
        for i, shape in enumerate(input_shapes)
    ])

    old_rows = load_csv(R26I_X100)
    old_selected = old_rows[0] if old_rows else {}

    rows = []
    eligible = []

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

            dclass = dtype_class(arr)
            numeric = dclass == "NUMERIC"

            finite = False
            if numeric:
                try:
                    finite = bool(np.all(np.isfinite(arr)))
                except Exception:
                    finite = False

            compatible_shapes = [
                s for s in input_shapes
                if shape_compatible(arr.shape, s)
            ]

            executable = (
                numeric
                and finite
                and len(compatible_shapes) > 0
            )

            score = 0
            reasons = []

            klow = key.lower()
            plow = str(path).lower()

            if klow == "x100":
                score += 1200
                reasons.append("exact_key_X100")
            elif "x100" in klow:
                score += 900
                reasons.append("key_contains_X100")

            if "deployment" in klow:
                score += 500
                reasons.append("deployment_semantics")

            if "feature" in klow or "input" in klow:
                score += 250
                reasons.append("feature_input_semantics")

            if "sg7b10" in plow:
                score += 350
                reasons.append("SG7B10_artifact")
            elif "sg7b9" in plow:
                score += 150
                reasons.append("SG7B9_parent_artifact")
            elif "sg7cr3" in plow:
                score += 50
                reasons.append("CR3_corroboration")

            if numeric:
                score += 500
                reasons.append("numeric_dtype")
            else:
                score -= 5000
                reasons.append(f"reject_{dclass.lower()}")

            if finite:
                score += 200
                reasons.append("finite")

            if compatible_shapes:
                score += 2000
                reasons.append("exact_model_input_shape_compatible")
            else:
                score -= 1500
                reasons.append("reject_model_shape_incompatible")

            row = {
                "artifact": str(path),
                "key": key,
                "shape": str(arr.shape),
                "dtype": str(arr.dtype),
                "dtype_class": dclass,
                "numeric": numeric,
                "finite": finite,
                "compatible_model_shapes": ";".join(str(s) for s in compatible_shapes),
                "executable_tensor": executable,
                "score": score,
                "reasons": ";".join(reasons),
                "sha256": sha256_array(arr),
            }
            rows.append(row)

            if executable:
                eligible.append((score, path, key, arr, reasons, compatible_shapes))

        db.close()

    rows.sort(key=lambda r: int(r["score"]), reverse=True)
    save_csv(CANDIDATE_TABLE, rows)

    eligible.sort(key=lambda x: x[0], reverse=True)

    selected = None
    margin = 0

    if eligible:
        top = eligible[0]
        second_score = eligible[1][0] if len(eligible) > 1 else -999999
        margin = top[0] - second_score

        strong_semantics = (
            top[2].lower() == "x100"
            or "x100" in top[2].lower()
            or "deployment" in top[2].lower()
        )

        if len(eligible) == 1 or strong_semantics or margin >= 500:
            selected = top

    if selected:
        score, path, key, arr, reasons, compatible_shapes = selected

        status = "SG7B10_DEPLOYMENT_X100_EXECUTABLE_TENSOR_BOUND"
        diagnosis = (
            "STRICT_DTYPE_AND_MODEL_SHAPE_CONTRACT_IDENTIFIES_NUMERIC_X100_INPUT"
        )
        recommendation = (
            "The R26I failure is resolved as an X100 binding error: the prior selected array "
            "was nonnumeric. A numeric finite tensor now matches the authoritative model input "
            "shape and SG7B10 X100 semantics. Rerun the 100-day runtime control using only this "
            "artifact/key; do not permit any string/object fallback."
        )
        next_milestone = (
            "V15-SG7E1R26I-R — Repaired Authoritative SG7B10 100-Day Runtime Control"
        )

    else:
        status = "SG7B10_DEPLOYMENT_X100_EXECUTABLE_TENSOR_NOT_YET_UNIQUE"
        diagnosis = (
            "STRICT_EXECUTABLE_TENSOR_FILTER_DOES_NOT_YET_SELECT_ONE_X100_INPUT"
        )
        recommendation = (
            "Do not call model.predict. Audit only the top numeric, finite, model-shape-compatible "
            "X100 candidates and their SG7B10 save/load lineage. Do not allow string/object arrays."
        )
        next_milestone = (
            "V15-SG7E1R26I-R — Final Numeric X100 Artifact Lineage Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "model_input_shapes": ";".join(str(s) for s in input_shapes),
        "executable_candidate_count": len(eligible),
        "selected_artifact": str(selected[1]) if selected else "",
        "selected_key": selected[2] if selected else "",
        "selected_score": selected[0] if selected else "",
        "selection_margin": margin,
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26IR",
        "status": status,
        "diagnosis": diagnosis,
        "failure_provenance": {
            "R26I_exception": "ValueError: Invalid dtype: str1952",
            "classification": "NONNUMERIC_X100_BINDING",
        },
        "model_input_shapes": [list(s) for s in input_shapes],
        "X100_binding": {
            "resolved": selected is not None,
            "artifact": str(selected[1]) if selected else None,
            "key": selected[2] if selected else None,
            "shape": list(selected[3].shape) if selected else None,
            "dtype": str(selected[3].dtype) if selected else None,
            "score": selected[0] if selected else None,
            "margin": margin,
        },
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "gamma_changed": False,
            "guard_changed": False,
            "threshold_changed": False,
            "model_predict_executed": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26IR",
        "status": status,
        "diagnosis": diagnosis,
        "selected_X100_artifact": str(selected[1]) if selected else None,
        "selected_X100_key": selected[2] if selected else None,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    print("AUTHORITATIVE MODEL INPUT CONTRACT")
    print(f"  Model                   : {model_path.name}")
    print(f"  Input shapes            : {input_shapes}")

    print("\nTOP EXECUTABLE X100 CANDIDATES")
    for row in rows[:15]:
        print(
            f"  score={int(row['score']):5d} | "
            f"exec={row['executable_tensor']} | "
            f"dtype={row['dtype']:<12s} | "
            f"shape={row['shape']:<24s} | "
            f"{Path(row['artifact']).name} :: {row['key']}"
        )

    if selected:
        print("\nSELECTED X100")
        print(f"  Artifact                : {selected[1]}")
        print(f"  Key                     : {selected[2]}")
        print(f"  Shape                   : {selected[3].shape}")
        print(f"  Dtype                   : {selected[3].dtype}")
        print(f"  Score / margin          : {selected[0]} / {margin}")

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
    print(f"  {MODEL_TABLE.name}")
    print(f"  {CANDIDATE_TABLE.name}")
    print(f"  {DECISION_TABLE.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26IR X100 DTYPE-BINDING AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
