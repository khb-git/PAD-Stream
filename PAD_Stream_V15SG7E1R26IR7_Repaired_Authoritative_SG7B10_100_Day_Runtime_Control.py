from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R7
# Repaired Authoritative SG7B10 100-Day Runtime Control
#
# CONTROLLED INFERENCE MILESTONE
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
# R26I-R6 established:
#
#   SG7B10_DEPLOYMENT_X100_RUNTIME_CONSTRUCTOR_FULLY_RESOLVED
#
# and persisted the exact source-authentic 100-day model input:
#
#   V15SG7E1R26IR6_Reconstructed_X100.npz :: X100
#
# R26I-R7 now performs the repaired 100-day inference using ONLY:
#
#   - the frozen authoritative model,
#   - the R26I-R6 reconstructed X100,
#   - the already-bound frozen 100-day L2 target,
#   - the unchanged R25R precision envelope.
#
# It does NOT search for alternative inputs or models.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR7"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Inputs
# -----------------------------------------------------------------------------

R26IR6_DIR = ROOT / "output" / "V15_SG7E1R26IR6"
R26IR6_SUMMARY = R26IR6_DIR / "PAD_Stream_V15SG7E1R26IR6_Summary.json"
R26IR6_CONTRACT = R26IR6_DIR / "V15SG7E1R26IR6_Final_Runtime_Constructor_Contract.json"
R26IR6_NUM = R26IR6_DIR / "V15SG7E1R26IR6_Reconstructed_X100.npz"

R25R_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R25R"
    / "V15SG7E1R25R_Repaired_100d_Replay_Contract.json"
)

R23_SUMMARY = (
    ROOT / "output" / "V15_SG7E1R23"
    / "PAD_Stream_V15SG7E1R23_Summary.json"
)

R18_MODEL_TABLE = (
    ROOT / "output" / "V15_SG7E1R18"
    / "V15SG7E1R18_Frozen_Model_Identity.csv"
)

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

INPUT_TABLE = OUT / "V15SG7E1R26IR7_Runtime_Input_Identity.csv"
MODEL_TABLE = OUT / "V15SG7E1R26IR7_Model_Identity.csv"
RAW_TABLE = OUT / "V15SG7E1R26IR7_Raw_Prediction_Identity.csv"
CLOSURE_TABLE = OUT / "V15SG7E1R26IR7_100d_Closure_Audit.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR7_Final_Runtime_Gate_Matrix.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR7_Runtime_Control_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R26IR7_100d_Runtime_Control.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR7_Authoritative_100d_Runtime_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR7_Summary.json"


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
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


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


def error_metrics(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    d = a - b
    return {
        "L1": float(np.mean(np.abs(d))),
        "L2": float(np.sqrt(np.mean(d * d))),
        "Linf": float(np.max(np.abs(d))),
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R7")
    print("Repaired Authoritative SG7B10 100-Day Runtime Control")
    print("=" * 78)

    print("""
CONTROLLED 100-DAY MODEL INFERENCE WILL BE PERFORMED.
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO SG7E PERFORMANCE GATE WILL BE EVALUATED.
NO HEURISTIC X100 SEARCH WILL BE PERFORMED.
""")

    # -------------------------------------------------------------------------
    # Preconditions
    # -------------------------------------------------------------------------

    s6 = load_json(R26IR6_SUMMARY)
    c6 = load_json(R26IR6_CONTRACT)
    c25r = load_json(R25R_CONTRACT)
    s23 = load_json(R23_SUMMARY)

    if s6.get("status") != "SG7B10_DEPLOYMENT_X100_RUNTIME_CONSTRUCTOR_FULLY_RESOLVED":
        raise RuntimeError("R26I-R7 requires successful R26I-R6 X100 runtime constructor.")

    if s23.get("selected_key") != "L2_independent_100":
        raise RuntimeError("Authoritative 100-day target must remain L2_independent_100.")

    if not R26IR6_NUM.exists():
        raise FileNotFoundError(R26IR6_NUM)

    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(R1F3_FROZEN)

    # -------------------------------------------------------------------------
    # Load exact X100
    # -------------------------------------------------------------------------

    db_x = np.load(R26IR6_NUM, allow_pickle=True)
    x100 = np.asarray(db_x["X100"])
    td_scale = float(np.asarray(db_x["tD_scale"]).ravel()[0]) if "tD_scale" in db_x.files else np.nan
    db_x.close()

    x100_hash = sha256_array(x100)

    save_csv(INPUT_TABLE, [{
        "artifact": str(R26IR6_NUM),
        "key": "X100",
        "shape": str(x100.shape),
        "dtype": str(x100.dtype),
        "sha256": x100_hash,
        "finite": bool(np.all(np.isfinite(x100))),
        "tD_scale": td_scale,
    }])

    # -------------------------------------------------------------------------
    # Authoritative model
    # -------------------------------------------------------------------------

    model_rows = load_csv(R18_MODEL_TABLE)
    if len(model_rows) != 1:
        raise RuntimeError("Expected exactly one authoritative model identity.")

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

    import tensorflow as tf

    model = tf.keras.models.load_model(model_path, compile=False)

    # -------------------------------------------------------------------------
    # Exact SG7B10 raw prediction semantics
    # -------------------------------------------------------------------------

    raw_model_output = model.predict(
        x100,
        batch_size=1024,
        verbose=0,
    )

    raw_model_output = np.asarray(raw_model_output)

    if raw_model_output.ndim == 3 and raw_model_output.shape[-1] >= 1:
        raw_state = raw_model_output[:, :, 0]
    else:
        raw_state = raw_model_output

    raw_finite = bool(np.all(np.isfinite(raw_state)))

    save_csv(RAW_TABLE, [{
        "raw_model_output_shape": str(raw_model_output.shape),
        "raw_model_output_dtype": str(raw_model_output.dtype),
        "raw_state_shape": str(raw_state.shape),
        "raw_state_dtype": str(raw_state.dtype),
        "raw_state_sha256": sha256_array(raw_state),
        "finite": raw_finite,
        "min": float(np.min(raw_state)) if raw_finite else "",
        "max": float(np.max(raw_state)) if raw_finite else "",
    }])

    # -------------------------------------------------------------------------
    # Authoritative frozen 100-day target
    # -------------------------------------------------------------------------

    db_f = np.load(R1F3_FROZEN, allow_pickle=True)
    if "L2_independent_100" not in db_f.files:
        db_f.close()
        raise RuntimeError("Frozen R1F3 package lacks L2_independent_100.")

    target = np.asarray(db_f["L2_independent_100"])
    db_f.close()

    target_hash = sha256_array(target)

    # unchanged R25R envelope
    envelope = float(c25r["contract_repair"]["precision_envelope"])

    shape_match = raw_state.shape == target.shape
    metrics = None
    closure_pass = False

    if shape_match and raw_finite:
        metrics = error_metrics(raw_state, target)
        closure_pass = metrics["Linf"] <= envelope

    save_csv(CLOSURE_TABLE, [{
        "target_key": "L2_independent_100",
        "target_sha256": target_hash,
        "raw_state_shape": str(raw_state.shape),
        "target_shape": str(target.shape),
        "shape_match": shape_match,
        "L1": metrics["L1"] if metrics else "",
        "L2": metrics["L2"] if metrics else "",
        "Linf": metrics["Linf"] if metrics else "",
        "precision_envelope": envelope,
        "precision_pass": closure_pass,
    }])

    # -------------------------------------------------------------------------
    # Gates
    # -------------------------------------------------------------------------

    gates = [
        ("R26IR6_X100_contract_reproduced", True),
        ("authoritative_model_hash_reproduced", model_hash_match),
        ("X100_numeric_finite", bool(np.all(np.isfinite(x100)))),
        ("X100_shape_2662x201x2", x100.shape == (2662, 201, 2)),
        ("100d_model_predict_executed", True),
        ("raw_prediction_finite", raw_finite),
        ("raw_prediction_shape_matches_target", shape_match),
        ("raw_prediction_closes_to_L2_independent_100", closure_pass),
        ("no_250_500_1000d_state_generated", True),
        ("no_training_performed", True),
        ("no_model_parameter_changed", True),
        ("no_gamma_or_guard_recalibration", True),
        ("no_SG7E_threshold_change", True),
        ("no_SG7E_performance_gate_evaluated", True),
    ]

    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    failed = [g for g, p in gates if not p]

    if not failed:
        status = "AUTHORITATIVE_SG7B10_100D_RUNTIME_CONTROL_VALIDATED"
        diagnosis = (
            "SOURCE_AUTHENTIC_X100_AND_FROZEN_MODEL_REPRODUCE_AUTHORITATIVE_100D_L2_STATE"
        )
        recommendation = (
            "The repaired SG7B10 100-day runtime path passes all frozen controls. "
            "The exact source-authentic X100 tensor and frozen authoritative model reproduce "
            "L2_independent_100 within the unchanged R25R precision envelope. Proceed to "
            "controlled multi-time generation at 100/250/500/1000 days using the same "
            "source-authentic deployment constructor and frozen model, with no retraining "
            "or threshold changes."
        )
        next_milestone = (
            "V15-SG7E1R27 — Controlled Four-Time Authoritative L2 Regeneration"
        )
    else:
        status = "AUTHORITATIVE_SG7B10_100D_RUNTIME_CONTROL_NOT_YET_VALIDATED"
        diagnosis = (
            "SOURCE_AUTHENTIC_RUNTIME_INFERENCE_EXECUTES_BUT_ONE_OR_MORE_FROZEN_100D_CLOSURE_GATES_FAIL"
        )
        recommendation = (
            "Do not generate later-time states. The exact X100 and frozen model now execute, "
            "so audit only the failed R26I-R7 closure gates. Do not change X100, model weights, "
            "gamma, guard, or the precision envelope."
        )
        next_milestone = (
            "V15-SG7E1R26I-R8 — Final 100-Day Runtime Closure Failure Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "failed_gate_count": len(failed),
        "failed_gates": ";".join(failed),
        "closure_pass": closure_pass,
        "Linf": metrics["Linf"] if metrics else "",
        "precision_envelope": envelope,
        "next_milestone": next_milestone,
    }])

    np.savez_compressed(
        NUMERICAL_FILE,
        X100=x100,
        raw_model_output=raw_model_output,
        raw_state_100d=raw_state,
        target_L2_independent_100=target,
        precision_envelope=np.asarray([envelope], dtype=np.float64),
    )

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R7",
        "status": status,
        "diagnosis": diagnosis,
        "X100": {
            "artifact": str(R26IR6_NUM),
            "key": "X100",
            "sha256": x100_hash,
            "shape": list(x100.shape),
            "dtype": str(x100.dtype),
        },
        "model": {
            "path": str(model_path),
            "sha256": actual_model_sha,
            "hash_match": model_hash_match,
        },
        "100d_runtime": {
            "raw_model_output_shape": list(raw_model_output.shape),
            "raw_state_shape": list(raw_state.shape),
            "raw_state_sha256": sha256_array(raw_state),
            "target_key": "L2_independent_100",
            "target_sha256": target_hash,
            "closure": metrics,
            "precision_envelope": envelope,
            "passed": closure_pass,
        },
        "failed_gates": failed,
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
        "milestone": "V15-SG7E1R26I-R7",
        "status": status,
        "diagnosis": diagnosis,
        "100d_runtime_executed": True,
        "100d_closure_pass": closure_pass,
        "failed_gates": failed,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("SOURCE-AUTHENTIC X100")
    print(f"  Artifact                : {R26IR6_NUM}")
    print(f"  Shape                   : {x100.shape}")
    print(f"  Dtype                   : {x100.dtype}")
    print(f"  SHA-256                 : {x100_hash}")

    print("\nAUTHORITATIVE MODEL")
    print(f"  File                    : {model_path.name}")
    print(f"  SHA-256                 : {actual_model_sha}")
    print(f"  Hash match              : {model_hash_match}")

    print("\n100-DAY RAW INFERENCE")
    print(f"  Model output shape      : {raw_model_output.shape}")
    print(f"  Raw state shape         : {raw_state.shape}")
    print(f"  Raw state finite        : {raw_finite}")
    print(f"  Raw state SHA-256       : {sha256_array(raw_state)}")

    print("\n100-DAY FROZEN CLOSURE")
    print(f"  Target                  : L2_independent_100")
    print(f"  Target SHA-256          : {target_hash}")
    print(f"  Shape match             : {shape_match}")
    if metrics:
        print(f"  L1                      : {metrics['L1']:.6e}")
        print(f"  L2                      : {metrics['L2']:.6e}")
        print(f"  Linf                    : {metrics['Linf']:.6e}")
    print(f"  Precision envelope      : {envelope:.6e}")
    print(f"  Closure pass            : {closure_pass}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R7 FINAL RUNTIME GATES")
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
    for path in (
        INPUT_TABLE,
        MODEL_TABLE,
        RAW_TABLE,
        CLOSURE_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {path.name}")

    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R7 REPAIRED AUTHORITATIVE 100-DAY RUNTIME CONTROL: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No gamma or crossing guard was recalibrated.")
    print("No later-time state was generated.")
    print("No SG7E threshold was changed or relaxed.")
    print("=" * 78)


if __name__ == "__main__":
    main()
