from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R10
# Bound SG7B10 100-Day Runtime Control
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
# R26I-R9 resolved the exact SG7B10 runtime model:
#
#   output/V15_SG7B7R/V15SG7B_FROZEN_Model.keras
#
# with architecture:
#
#   input  : (None, 201, 2)
#   output : (None, 201, 1)
#
# and confirmed compatibility with:
#
#   X100.shape = (2662, 201, 2)
#
# The raw SG7B10 frozen-model output is treated as the frozen/pre-correction
# 100-day state. K5_100 and L2_independent_100 are audited diagnostically only.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR10"
OUT.mkdir(parents=True, exist_ok=True)

R9_DIR = ROOT / "output" / "V15_SG7E1R26IR9"
R9_SUMMARY = R9_DIR / "PAD_Stream_V15SG7E1R26IR9_Summary.json"
R9_CONTRACT = R9_DIR / "V15SG7E1R26IR9_Final_Model_Load_Path_Contract.json"

R6_DIR = ROOT / "output" / "V15_SG7E1R26IR6"
R6_SUMMARY = R6_DIR / "PAD_Stream_V15SG7E1R26IR6_Summary.json"
R6_NUM = R6_DIR / "V15SG7E1R26IR6_Reconstructed_X100.npz"

R23_DIR = ROOT / "output" / "V15_SG7E1R23"
R23_ROLE_TABLE = R23_DIR / "V15SG7E1R23_State_Key_Role_Mapping.csv"

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

R25R_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R25R"
    / "V15SG7E1R25R_Repaired_100d_Replay_Contract.json"
)

MODEL_TABLE = OUT / "V15SG7E1R26IR10_Model_Identity.csv"
INPUT_TABLE = OUT / "V15SG7E1R26IR10_X100_Identity.csv"
ROLE_TABLE = OUT / "V15SG7E1R26IR10_100d_State_Role_Contract.csv"
RAW_TABLE = OUT / "V15SG7E1R26IR10_Raw_Runtime_Prediction.csv"
CLOSURE_TABLE = OUT / "V15SG7E1R26IR10_100d_State_Closure_Audit.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR10_Final_Runtime_Gate_Matrix.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR10_Runtime_Control_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R26IR10_100d_Runtime_Control.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR10_Bound_100d_Runtime_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR10_Summary.json"


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


def role_from_r23(rows, key, fallback):
    for row in rows:
        joined = " ".join(str(v) for v in row.values())
        if key in joined:
            for col in ("stage_role", "role", "semantic_role", "state_role"):
                if col in row and row[col]:
                    return row[col]
            return fallback
    return fallback


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R10")
    print("Bound SG7B10 100-Day Runtime Control")
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
NO MODEL OR X100 SEARCH WILL BE PERFORMED.
""")

    r9 = load_json(R9_SUMMARY)
    r9c = load_json(R9_CONTRACT)
    r6 = load_json(R6_SUMMARY)

    if r9.get("status") != "SG7B10_FROZEN_MODEL_PATH_AND_X100_ARCHITECTURE_COMPATIBLE":
        raise RuntimeError("R26I-R10 requires successful R26I-R9 architecture compatibility.")

    if r6.get("status") != "SG7B10_DEPLOYMENT_X100_RUNTIME_CONSTRUCTOR_FULLY_RESOLVED":
        raise RuntimeError("R26I-R10 requires successful R26I-R6 X100 constructor.")

    model_path_str = (
        r9.get("resolved_model_path")
        or r9c.get("FROZEN_MODEL_FILE", {}).get("resolved_path")
    )
    if not model_path_str:
        raise RuntimeError("R9 did not persist the resolved SG7B10 model path.")

    model_path = Path(model_path_str)
    if not model_path.exists():
        raise FileNotFoundError(model_path)

    expected_model_sha = (
        r9.get("resolved_model_sha256")
        or r9c.get("FROZEN_MODEL_FILE", {}).get("sha256")
    )
    actual_model_sha = sha256_file(model_path)
    model_hash_match = bool(expected_model_sha and actual_model_sha == expected_model_sha)

    xdb = np.load(R6_NUM, allow_pickle=True)
    x100 = np.asarray(xdb["X100"])
    tD_scale = (
        float(np.asarray(xdb["tD_scale"]).ravel()[0])
        if "tD_scale" in xdb.files else np.nan
    )
    xdb.close()

    x100_hash = sha256_array(x100)

    save_csv(MODEL_TABLE, [{
        "model_path": str(model_path),
        "expected_sha256": expected_model_sha or "",
        "actual_sha256": actual_model_sha,
        "hash_match": model_hash_match,
    }])

    save_csv(INPUT_TABLE, [{
        "artifact": str(R6_NUM),
        "key": "X100",
        "shape": str(x100.shape),
        "dtype": str(x100.dtype),
        "sha256": x100_hash,
        "finite": bool(np.all(np.isfinite(x100))),
        "tD_scale": tD_scale,
    }])

    r23_roles = load_csv(R23_ROLE_TABLE)
    roles = {
        "frozen100": role_from_r23(
            r23_roles, "frozen100", "FROZEN_BASELINE_OR_PRECORRECTION_STATE"
        ),
        "K5_100": role_from_r23(
            r23_roles, "K5_100", "K5_PRE_L2_INPUT_STATE"
        ),
        "L2_independent_100": role_from_r23(
            r23_roles, "L2_independent_100", "L2_INDEPENDENTLY_VALIDATED_STATE"
        ),
    }

    primary_key = "frozen100"

    save_csv(ROLE_TABLE, [{
        "key": key,
        "semantic_role": role,
        "runtime_closure_authority": (
            "AUTHORITATIVE_RAW_TARGET" if key == primary_key else "DIAGNOSTIC_ONLY"
        ),
    } for key, role in roles.items()])

    fdb = np.load(R1F3_FROZEN, allow_pickle=True)
    required_keys = ["frozen100", "K5_100", "L2_independent_100"]
    missing = [k for k in required_keys if k not in fdb.files]
    if missing:
        fdb.close()
        raise RuntimeError(f"Frozen R1F3 package missing state keys: {missing}")

    states = {k: np.asarray(fdb[k]) for k in required_keys}
    fdb.close()

    import tensorflow as tf
    model = tf.keras.models.load_model(model_path, compile=False)

    runtime_output = np.asarray(
        model.predict(x100, batch_size=1024, verbose=0)
    )

    if runtime_output.ndim != 3 or runtime_output.shape[-1] < 1:
        raise RuntimeError(
            f"Unexpected SG7B10 model output shape: {runtime_output.shape}"
        )

    raw100 = np.asarray(runtime_output[:, :, 0])

    save_csv(RAW_TABLE, [{
        "runtime_output_shape": str(runtime_output.shape),
        "runtime_output_dtype": str(runtime_output.dtype),
        "raw100_shape": str(raw100.shape),
        "raw100_dtype": str(raw100.dtype),
        "raw100_sha256": sha256_array(raw100),
        "finite": bool(np.all(np.isfinite(raw100))),
        "min": float(np.min(raw100)),
        "max": float(np.max(raw100)),
    }])

    r25r = load_json(R25R_CONTRACT)
    envelope = float(
        r25r.get("contract_repair", {}).get("precision_envelope", 1.192093e-07)
    )

    closure_rows = []
    closure = {}

    for key in required_keys:
        metrics = error_metrics(raw100, states[key])
        same_shape = raw100.shape == states[key].shape

        row = {
            "runtime_state": "SG7B10_raw100",
            "reference_key": key,
            "semantic_role": roles[key],
            "authority": (
                "AUTHORITATIVE_RAW_TARGET" if key == primary_key else "DIAGNOSTIC_ONLY"
            ),
            "shape_match": same_shape,
            "runtime_shape": str(raw100.shape),
            "reference_shape": str(states[key].shape),
            "reference_sha256": sha256_array(states[key]),
            "L1": metrics["L1"] if metrics else "",
            "L2": metrics["L2"] if metrics else "",
            "Linf": metrics["Linf"] if metrics else "",
            "precision_envelope": envelope,
            "precision_pass": bool(metrics and metrics["Linf"] <= envelope),
        }
        closure_rows.append(row)
        closure[key] = row

    save_csv(CLOSURE_TABLE, closure_rows)

    primary_pass = bool(closure[primary_key]["precision_pass"])
    raw_finite = bool(np.all(np.isfinite(raw100)))
    output_shape_ok = raw100.shape == states[primary_key].shape

    gates = [
        ("R9_model_path_contract_reproduced", True),
        ("R9_model_sha256_reproduced", model_hash_match),
        ("R6_X100_contract_reproduced", x100.shape == (2662, 201, 2)),
        ("X100_finite", bool(np.all(np.isfinite(x100)))),
        ("SG7B10_model_predict_executed", True),
        ("runtime_output_shape_2662x201x1", runtime_output.shape == (2662, 201, 1)),
        ("raw100_finite", raw_finite),
        ("raw100_shape_matches_frozen100", output_shape_ok),
        ("raw100_closes_to_frozen100_under_unchanged_precision_envelope", primary_pass),
        ("K5_and_L2_used_diagnostic_only", True),
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
        status = "SG7B10_BOUND_100D_RAW_RUNTIME_CONTROL_VALIDATED"
        diagnosis = (
            "CORRECT_MODEL_AND_SOURCE_AUTHENTIC_X100_REPRODUCE_FROZEN100_WITHIN_UNCHANGED_PRECISION_ENVELOPE"
        )
        recommendation = (
            "The correctly bound SG7B10 frozen model and source-authentic X100 reproduce the "
            "historical frozen100 pre-correction state at 100 days within the unchanged precision "
            "envelope. Proceed to the downstream frozen100 -> K5_100 -> L2_independent_100 "
            "correction-chain runtime replay before generating later-time states."
        )
        next_milestone = (
            "V15-SG7E1R26J — 100-Day Downstream Correction-Chain Runtime Replay"
        )
    else:
        status = "SG7B10_BOUND_100D_RAW_RUNTIME_CONTROL_EXECUTED_CLOSURE_FAILED"
        diagnosis = (
            "CORRECT_MODEL_AND_X100_EXECUTE_BUT_RAW100_DOES_NOT_REPRODUCE_FROZEN100_UNDER_FROZEN_PRECISION_CONTRACT"
        )
        recommendation = (
            "Do not generate later-time states. The correct SG7B10 model and X100 now execute. "
            "Audit only the historical raw-prediction serialization/postprocessing path between "
            "model.predict(... )[:,:,0] and frozen100. Do not change model weights, X100, gamma, "
            "guard, or the precision envelope."
        )
        next_milestone = (
            "V15-SG7E1R26I-R11 — SG7B10 Raw100 Serialization / Postprocessing Closure Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "failed_gate_count": len(failed),
        "failed_gates": ";".join(failed),
        "primary_runtime_target": primary_key,
        "primary_target_role": roles[primary_key],
        "primary_Linf": closure[primary_key]["Linf"],
        "precision_envelope": envelope,
        "primary_precision_pass": primary_pass,
        "next_milestone": next_milestone,
    }])

    np.savez_compressed(
        NUMERICAL_FILE,
        X100=x100,
        runtime_model_output=runtime_output,
        raw100=raw100,
        frozen100=states["frozen100"],
        K5_100=states["K5_100"],
        L2_independent_100=states["L2_independent_100"],
        precision_envelope=np.asarray([envelope], dtype=np.float64),
    )

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R10",
        "status": status,
        "diagnosis": diagnosis,
        "model": {
            "path": str(model_path),
            "sha256": actual_model_sha,
            "hash_match": model_hash_match,
        },
        "X100": {
            "artifact": str(R6_NUM),
            "key": "X100",
            "shape": list(x100.shape),
            "dtype": str(x100.dtype),
            "sha256": x100_hash,
        },
        "100d_state_roles": roles,
        "authoritative_raw_runtime_target": primary_key,
        "closure": closure,
        "precision_envelope": envelope,
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
        "milestone": "V15-SG7E1R26I-R10",
        "status": status,
        "diagnosis": diagnosis,
        "runtime_executed": True,
        "primary_target": primary_key,
        "primary_closure_pass": primary_pass,
        "failed_gates": failed,
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    print("BOUND SG7B10 MODEL")
    print(f"  File                    : {model_path}")
    print(f"  SHA-256                 : {actual_model_sha}")
    print(f"  Hash match              : {model_hash_match}")

    print("\nSOURCE-AUTHENTIC X100")
    print(f"  Shape                   : {x100.shape}")
    print(f"  Dtype                   : {x100.dtype}")
    print(f"  SHA-256                 : {x100_hash}")

    print("\n100-DAY RUNTIME")
    print(f"  Model output shape      : {runtime_output.shape}")
    print(f"  Raw100 shape            : {raw100.shape}")
    print(f"  Raw100 range            : {np.min(raw100):.6f} -> {np.max(raw100):.6f}")
    print(f"  Raw100 SHA-256          : {sha256_array(raw100)}")

    print("\n100-DAY STATE CLOSURE")
    for row in closure_rows:
        print(
            f"  {row['reference_key']:<20s} | "
            f"role={row['semantic_role']:<36s} | "
            f"Linf={float(row['Linf']):.6e} | "
            f"pass={row['precision_pass']}"
        )

    print(f"\nAUTHORITATIVE RAW TARGET : {primary_key}")
    print(f"PRECISION ENVELOPE       : {envelope:.6e}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R10 FINAL RUNTIME GATES")
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
        MODEL_TABLE,
        INPUT_TABLE,
        ROLE_TABLE,
        RAW_TABLE,
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
    print("V15-SG7E1R26I-R10 BOUND SG7B10 100-DAY RUNTIME CONTROL: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No gamma or crossing guard was recalibrated.")
    print("No later-time state was generated.")
    print("No SG7E threshold was changed or relaxed.")
    print("=" * 78)


if __name__ == "__main__":
    main()
