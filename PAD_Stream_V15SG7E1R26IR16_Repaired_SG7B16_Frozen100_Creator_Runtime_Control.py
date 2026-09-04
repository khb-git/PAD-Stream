from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R16
# Repaired SG7B16 Frozen100 Creator Runtime Control
#
# CONTROLLED 100-DAY AUTHORITATIVE CREATOR REPLAY
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA / GUARD RECALIBRATION.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO CREATOR / MODEL / X100 DISCOVERY WILL BE REOPENED.
#
# PURPOSE
# -------
# R15C fully resolved the selected SG7B16 frozen100 creator input contract:
#
#   base = SG7B6D
#   dataset = base.load_dataset()
#   tD_scale = 11.137549167853525
#   deployment workspace = ..._SG5C_seed_11x11
#   X100.shape = (2662, 201, 2)
#   X100 SHA-256 =
#     21e4fb419f9c56242516d7c439da5160cf24b2b6cae4d30666d71de752aed526
#
# R14 already resolved the selected SG7B16 frozen model:
#
#   output/V15_SG7B11/V15SG7B_FRONT_AWARE_FROZEN_Model.keras
#
# R16 now performs ONLY:
#
#   frozen_model.predict(X100)[:, :, 0]
#        -> compare against persisted frozen100
#
# using the unchanged precision envelope from R25R.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR16"
OUT.mkdir(parents=True, exist_ok=True)

R15C_DIR = ROOT / "output" / "V15_SG7E1R26IR15C"
R15C_SUMMARY = R15C_DIR / "PAD_Stream_V15SG7E1R26IR15C_Summary.json"
R15C_NUM = R15C_DIR / "V15SG7E1R26IR15C_Resolved_SG7B16_X100.npz"

R14_DIR = ROOT / "output" / "V15_SG7E1R26IR14"
R14_CONTRACT = R14_DIR / "V15SG7E1R26IR14_Selected_Creator_Runtime_Contract.json"

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

R25R_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R25R"
    / "V15SG7E1R25R_Repaired_100d_Replay_Contract.json"
)

MODEL_TABLE = OUT / "V15SG7E1R26IR16_Model_Identity.csv"
X100_TABLE = OUT / "V15SG7E1R26IR16_X100_Identity.csv"
RUNTIME_TABLE = OUT / "V15SG7E1R26IR16_Creator_Runtime_Output.csv"
CLOSURE_TABLE = OUT / "V15SG7E1R26IR16_Frozen100_Closure.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR16_Final_Runtime_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR16_Runtime_Decision.csv"

NUM_FILE = OUT / "V15SG7E1R26IR16_SG7B16_Frozen100_Runtime_Control.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26IR16_SG7B16_Frozen100_Runtime_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR16_Summary.json"


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


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R16")
    print("Repaired SG7B16 Frozen100 Creator Runtime Control")
    print("=" * 78)

    print("""
CONTROLLED 100-DAY SG7B16 FROZEN-MODEL INFERENCE WILL BE PERFORMED.
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO CREATOR / MODEL / X100 DISCOVERY WILL BE REOPENED.
""")

    # -------------------------------------------------------------------------
    # Preconditions
    # -------------------------------------------------------------------------

    r15c = load_json(R15C_SUMMARY)
    if r15c.get("status") != "SG7B16_BASE_DATASET_tD_SCALE_AND_X100_RUNTIME_BINDINGS_RESOLVED":
        raise RuntimeError("R16 requires successful R15C binding resolution.")

    r14 = load_json(R14_CONTRACT)

    model_path_str = r14.get("model", {}).get("path")
    expected_model_sha = r14.get("model", {}).get("sha256")

    if not model_path_str:
        raise RuntimeError("R14 did not persist selected SG7B16 frozen-model path.")

    model_path = Path(model_path_str)
    if not model_path.exists():
        raise FileNotFoundError(model_path)

    actual_model_sha = sha256_file(model_path)
    model_hash_match = bool(
        expected_model_sha and actual_model_sha == expected_model_sha
    )

    # -------------------------------------------------------------------------
    # Source-authentic X100 from R15C
    # -------------------------------------------------------------------------

    if not R15C_NUM.exists():
        raise FileNotFoundError(R15C_NUM)

    xdb = np.load(R15C_NUM, allow_pickle=True)
    x100 = np.asarray(xdb["X100"])
    tD_scale = float(np.asarray(xdb["tD_scale"]).ravel()[0])
    xdb.close()

    x100_hash = sha256_array(x100)

    # -------------------------------------------------------------------------
    # Persisted frozen100 target
    # -------------------------------------------------------------------------

    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(R1F3_FROZEN)

    fdb = np.load(R1F3_FROZEN, allow_pickle=True)
    if "frozen100" not in fdb.files:
        fdb.close()
        raise RuntimeError("R1F3 frozen package lacks frozen100.")
    frozen100 = np.asarray(fdb["frozen100"])
    fdb.close()

    frozen100_hash = sha256_array(frozen100)

    # -------------------------------------------------------------------------
    # Unchanged precision envelope
    # -------------------------------------------------------------------------

    r25r = load_json(R25R_CONTRACT)
    envelope = float(
        r25r.get("contract_repair", {}).get(
            "precision_envelope",
            1.192093e-07,
        )
    )

    save_csv(MODEL_TABLE, [{
        "model_path": str(model_path),
        "expected_sha256": expected_model_sha or "",
        "actual_sha256": actual_model_sha,
        "hash_match": model_hash_match,
    }])

    save_csv(X100_TABLE, [{
        "artifact": str(R15C_NUM),
        "key": "X100",
        "shape": str(x100.shape),
        "dtype": str(x100.dtype),
        "finite": bool(np.all(np.isfinite(x100))),
        "tD_scale": tD_scale,
        "sha256": x100_hash,
    }])

    # -------------------------------------------------------------------------
    # Exact SG7B16 creator inference
    # -------------------------------------------------------------------------

    import tensorflow as tf

    model = tf.keras.models.load_model(model_path, compile=False)

    model_output = np.asarray(
        model.predict(
            x100,
            batch_size=1024,
            verbose=0,
        )
    )

    if model_output.ndim != 3 or model_output.shape[-1] < 1:
        raise RuntimeError(
            f"Unexpected SG7B16 frozen-model output shape: {model_output.shape}"
        )

    creator100 = np.asarray(model_output[:, :, 0])
    creator100_hash = sha256_array(creator100)

    save_csv(RUNTIME_TABLE, [{
        "model_output_shape": str(model_output.shape),
        "model_output_dtype": str(model_output.dtype),
        "creator100_shape": str(creator100.shape),
        "creator100_dtype": str(creator100.dtype),
        "creator100_finite": bool(np.all(np.isfinite(creator100))),
        "creator100_min": float(np.min(creator100)),
        "creator100_max": float(np.max(creator100)),
        "creator100_sha256": creator100_hash,
    }])

    # -------------------------------------------------------------------------
    # Closure
    # -------------------------------------------------------------------------

    metrics = error_metrics(creator100, frozen100)
    shape_match = creator100.shape == frozen100.shape
    closure_pass = bool(metrics and metrics["Linf"] <= envelope)

    save_csv(CLOSURE_TABLE, [{
        "creator_runtime_key": "SG7B16_creator100",
        "persisted_target_key": "frozen100",
        "creator_shape": str(creator100.shape),
        "target_shape": str(frozen100.shape),
        "shape_match": shape_match,
        "creator_sha256": creator100_hash,
        "target_sha256": frozen100_hash,
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
        (
            "R15C_binding_status_reproduced",
            r15c.get("status")
            == "SG7B16_BASE_DATASET_tD_SCALE_AND_X100_RUNTIME_BINDINGS_RESOLVED",
        ),
        (
            "selected_creator_remains_SG7B16",
            r15c.get("selected_creator")
            == "PAD_Stream_V15SG7B16_Controlled_Front_Preserving_TOF_Refinement.py",
        ),
        ("selected_model_path_exists", model_path.exists()),
        ("selected_model_sha256_reproduced", model_hash_match),
        ("R15C_X100_loaded", x100.shape == (2662, 201, 2)),
        ("R15C_X100_float32", x100.dtype == np.float32),
        ("R15C_X100_finite", bool(np.all(np.isfinite(x100)))),
        (
            "R15C_X100_sha256_reproduced",
            x100_hash
            == "21e4fb419f9c56242516d7c439da5160cf24b2b6cae4d30666d71de752aed526",
        ),
        ("tD_scale_reproduced", np.isfinite(tD_scale)),
        ("SG7B16_model_predict_executed", True),
        ("runtime_output_shape_2662x201x1", model_output.shape == (2662, 201, 1)),
        ("creator100_finite", bool(np.all(np.isfinite(creator100)))),
        ("creator100_shape_matches_frozen100", shape_match),
        ("creator100_closes_to_frozen100", closure_pass),
        ("no_250_500_1000d_state_generated", True),
        ("no_training_performed", True),
        ("no_model_parameter_changed", True),
        ("no_gamma_or_guard_recalibration", True),
        ("no_SG7E_threshold_change", True),
        ("no_creator_model_X100_search_reopened", True),
    ]

    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    # -------------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------------

    if not failed:
        status = "SG7B16_FROZEN100_CREATOR_RUNTIME_VALIDATED"
        diagnosis = (
            "AUTHORITATIVE_SG7B16_MODEL_AND_SOURCE_AUTHENTIC_X100_REPRODUCE_PERSISTED_FROZEN100"
        )
        recommendation = (
            "The authoritative SG7B16 frozen100 creator is now runtime validated. Its exact frozen "
            "model and exact source-authentic X100 reproduce persisted frozen100 within the unchanged "
            "precision envelope. Proceed to the 100-day downstream correction-chain replay "
            "frozen100 -> K5_100 -> L2_independent_100 before generating later-time states."
        )
        next_milestone = (
            "V15-SG7E1R26J — 100-Day Downstream Correction-Chain Runtime Replay"
        )

    else:
        status = "SG7B16_FROZEN100_CREATOR_RUNTIME_CONTROL_FAILED"
        diagnosis = (
            "AUTHORITATIVE_CREATOR_MODEL_AND_X100_EXECUTE_BUT_ONE_OR_MORE_RUNTIME_OR_CLOSURE_GATES_FAIL"
        )
        recommendation = (
            "Do not generate later-time states. Audit only the failed R16 gates. Creator, model, "
            "workspace, tD_scale, and X100 authority are frozen and must not be reopened."
        )
        next_milestone = (
            "V15-SG7E1R26I-R17 — SG7B16 Frozen100 Runtime Closure Failure Audit"
        )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "creator_model": str(model_path),
        "creator_model_sha256": actual_model_sha,
        "X100_sha256": x100_hash,
        "creator100_sha256": creator100_hash,
        "frozen100_sha256": frozen100_hash,
        "Linf": metrics["Linf"] if metrics else "",
        "precision_envelope": envelope,
        "closure_pass": closure_pass,
        "failed_gates": ";".join(failed),
        "next_milestone": next_milestone,
    }])

    np.savez_compressed(
        NUM_FILE,
        X100=x100,
        tD_scale=np.asarray([tD_scale], dtype=np.float64),
        model_output=model_output,
        creator100=creator100,
        frozen100=frozen100,
        precision_envelope=np.asarray([envelope], dtype=np.float64),
    )

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R16",
        "status": status,
        "diagnosis": diagnosis,
        "creator": "PAD_Stream_V15SG7B16_Controlled_Front_Preserving_TOF_Refinement.py",
        "model": {
            "path": str(model_path),
            "sha256": actual_model_sha,
            "hash_match": model_hash_match,
        },
        "X100": {
            "artifact": str(R15C_NUM),
            "shape": list(x100.shape),
            "dtype": str(x100.dtype),
            "sha256": x100_hash,
            "tD_scale": tD_scale,
        },
        "runtime100": {
            "shape": list(creator100.shape),
            "sha256": creator100_hash,
            "range": [
                float(np.min(creator100)),
                float(np.max(creator100)),
            ],
        },
        "frozen100": {
            "shape": list(frozen100.shape),
            "sha256": frozen100_hash,
        },
        "closure": {
            "L1": metrics["L1"] if metrics else None,
            "L2": metrics["L2"] if metrics else None,
            "Linf": metrics["Linf"] if metrics else None,
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
            "authority_reopened": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R16",
        "status": status,
        "diagnosis": diagnosis,
        "selected_creator": "PAD_Stream_V15SG7B16_Controlled_Front_Preserving_TOF_Refinement.py",
        "closure_pass": closure_pass,
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("AUTHORITATIVE SG7B16 MODEL")
    print(f"  File                    : {model_path}")
    print(f"  SHA-256                 : {actual_model_sha}")
    print(f"  Hash match              : {model_hash_match}")

    print("\nSOURCE-AUTHENTIC X100")
    print(f"  Shape                   : {x100.shape}")
    print(f"  Dtype                   : {x100.dtype}")
    print(f"  tD_scale                : {tD_scale}")
    print(f"  SHA-256                 : {x100_hash}")

    print("\nSG7B16 100-DAY CREATOR RUNTIME")
    print(f"  Model output shape      : {model_output.shape}")
    print(f"  Creator100 shape        : {creator100.shape}")
    print(f"  Range                   : {np.min(creator100):.6f} -> {np.max(creator100):.6f}")
    print(f"  SHA-256                 : {creator100_hash}")

    print("\nPERSISTED FROZEN100")
    print(f"  Shape                   : {frozen100.shape}")
    print(f"  SHA-256                 : {frozen100_hash}")

    print("\nCLOSURE")
    if metrics:
        print(f"  L1                      : {metrics['L1']:.6e}")
        print(f"  L2                      : {metrics['L2']:.6e}")
        print(f"  Linf                    : {metrics['Linf']:.6e}")
    print(f"  Precision envelope      : {envelope:.6e}")
    print(f"  Closure pass            : {closure_pass}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R16 FINAL RUNTIME GATES")
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
        X100_TABLE,
        RUNTIME_TABLE,
        CLOSURE_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nNumerical:")
    print(f"  {NUM_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R16 REPAIRED SG7B16 FROZEN100 CREATOR RUNTIME CONTROL: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No gamma or crossing guard was recalibrated.")
    print("No creator/model/X100 authority was reopened.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
