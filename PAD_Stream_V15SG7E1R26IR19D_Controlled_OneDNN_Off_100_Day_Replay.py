from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import os
import subprocess
import sys
import textwrap

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR19D"
OUT.mkdir(parents=True, exist_ok=True)

R19C_DIR = ROOT / "output" / "V15_SG7E1R26IR19C"
R19C_SUMMARY = R19C_DIR / "PAD_Stream_V15SG7E1R26IR19C_Summary.json"
R19C_VARIANCE = R19C_DIR / "V15SG7E1R26IR19C_Admissible_Runtime_Variance_Matrix.csv"

R16_DIR = ROOT / "output" / "V15_SG7E1R26IR16"
R16_CONTRACT = R16_DIR / "V15SG7E1R26IR16_SG7B16_Frozen100_Runtime_Contract.json"
R16_NUM = R16_DIR / "V15SG7E1R26IR16_SG7B16_Frozen100_Runtime_Control.npz"

R15C_NUM = ROOT / "output" / "V15_SG7E1R26IR15C" / "V15SG7E1R26IR15C_Resolved_SG7B16_X100.npz"

ENV_TABLE = OUT / "V15SG7E1R26IR19D_Child_Runtime_Environment.csv"
RUNTIME_TABLE = OUT / "V15SG7E1R26IR19D_OneDNN_Off_Runtime_Output.csv"
COMPARE_TABLE = OUT / "V15SG7E1R26IR19D_Baseline_vs_OneDNN_Off_Comparison.csv"
CLOSURE_TABLE = OUT / "V15SG7E1R26IR19D_Frozen100_Closure.csv"
ULP_TABLE = OUT / "V15SG7E1R26IR19D_ULP_Summary.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR19D_Final_Replay_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR19D_OneDNN_Off_Decision.csv"

NUM_FILE = OUT / "V15SG7E1R26IR19D_OneDNN_Off_100d_Replay.npz"
CHILD_SCRIPT = OUT / "_R19D_child_onednn_off.py"
CHILD_JSON = OUT / "_R19D_child_runtime.json"
CHILD_NPZ = OUT / "_R19D_child_output.npz"

CONTRACT_FILE = OUT / "V15SG7E1R26IR19D_OneDNN_Off_Replay_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR19D_Summary.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def error_metrics(a, b):
    a64 = np.asarray(a, dtype=np.float64)
    b64 = np.asarray(b, dtype=np.float64)
    d = a64 - b64
    return {
        "L1": float(np.mean(np.abs(d))),
        "L2": float(np.sqrt(np.mean(d * d))),
        "Linf": float(np.max(np.abs(d))),
    }


def ordered_int_float32(arr):
    a = np.asarray(arr, dtype=np.float32)
    u = a.view(np.uint32)
    sign = (u >> 31).astype(np.uint32)
    ordered = np.where(sign == 0, u | np.uint32(0x80000000), ~u)
    return ordered.astype(np.int64)


def ulp_distance(a, b):
    return np.abs(ordered_int_float32(a) - ordered_int_float32(b))


def write_child(model_path: Path):
    child = """
from pathlib import Path
import os, json, hashlib
import numpy as np
import tensorflow as tf

MODEL = Path(MODEL_PATH)
X100_FILE = Path(X100_PATH)
OUT_NPZ = Path(OUT_NPZ_PATH)
OUT_JSON = Path(OUT_JSON_PATH)

def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()

xdb = np.load(X100_FILE, allow_pickle=True)
x100 = np.asarray(xdb["X100"], dtype=np.float32)
xdb.close()

model = tf.keras.models.load_model(MODEL, compile=False)
raw = np.asarray(model.predict(x100, batch_size=1024, verbose=0))
creator100 = np.asarray(raw[:, :, 0], dtype=np.float32)

np.savez_compressed(OUT_NPZ, raw=raw, creator100=creator100)

meta = {
    "TF_ENABLE_ONEDNN_OPTS": os.environ.get("TF_ENABLE_ONEDNN_OPTS", ""),
    "TF_DETERMINISTIC_OPS": os.environ.get("TF_DETERMINISTIC_OPS", ""),
    "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", ""),
    "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS", ""),
    "tensorflow_version": tf.__version__,
    "keras_version": getattr(tf.keras, "__version__", ""),
    "x100_shape": list(x100.shape),
    "raw_shape": list(raw.shape),
    "creator100_shape": list(creator100.shape),
    "creator100_min": float(np.min(creator100)),
    "creator100_max": float(np.max(creator100)),
    "creator100_sha256": sha256_array(creator100),
}
OUT_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")
"""
    child = child.replace("MODEL_PATH", repr(str(model_path)))
    child = child.replace("X100_PATH", repr(str(R15C_NUM)))
    child = child.replace("OUT_NPZ_PATH", repr(str(CHILD_NPZ)))
    child = child.replace("OUT_JSON_PATH", repr(str(CHILD_JSON)))
    CHILD_SCRIPT.write_text(textwrap.dedent(child), encoding="utf-8")


def main():
    print("\\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R19D")
    print("Controlled oneDNN-Off 100-Day Replay")
    print("=" * 78)

    print("""
CONTROLLED 100-DAY MODEL INFERENCE WILL BE PERFORMED IN A CHILD PROCESS.
TF_ENABLE_ONEDNN_OPTS=0 WILL BE SET BEFORE TENSORFLOW IMPORT.
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
THE R16 PRECISION ENVELOPE WILL REMAIN UNCHANGED.
NO OTHER RUNTIME VARIANCE CASE WILL BE EXECUTED.
""")

    r19c = load_json(R19C_SUMMARY)
    if r19c.get("status") != "CONTROLLED_RUNTIME_VARIANCE_EXPERIMENT_DESIGN_READY":
        raise RuntimeError("R19D requires successful R19C.")

    variance = load_csv(R19C_VARIANCE)
    c1 = next((r for r in variance if r.get("case_id") == "C1"), None)
    if not c1 or str(c1.get("authorized", "")).lower() not in {"true", "1", "yes"}:
        raise RuntimeError("Authorized C1 case not found.")

    r16 = load_json(R16_CONTRACT)
    model_path = Path(r16["model"]["path"])
    model_sha = r16["model"]["sha256"]
    x100_sha = r16["X100"]["sha256"]
    precision_envelope = float(r16["closure"]["precision_envelope"])

    db = np.load(R16_NUM, allow_pickle=True)
    baseline100 = np.asarray(db["creator100"], dtype=np.float32)
    frozen100 = np.asarray(db["frozen100"], dtype=np.float32)
    db.close()

    baseline_hash = sha256_array(baseline100)
    frozen_hash = sha256_array(frozen100)

    write_child(model_path)

    env = os.environ.copy()
    env["TF_ENABLE_ONEDNN_OPTS"] = "0"

    completed = subprocess.run(
        [sys.executable, str(CHILD_SCRIPT)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            "Child replay failed.\\nSTDOUT:\\n" + completed.stdout +
            "\\nSTDERR:\\n" + completed.stderr
        )

    child_meta = load_json(CHILD_JSON)
    odb = np.load(CHILD_NPZ, allow_pickle=True)
    raw = np.asarray(odb["raw"])
    onednn_off100 = np.asarray(odb["creator100"], dtype=np.float32)
    odb.close()

    onednn_hash = sha256_array(onednn_off100)

    save_csv(ENV_TABLE, [{
        "TF_ENABLE_ONEDNN_OPTS": child_meta.get("TF_ENABLE_ONEDNN_OPTS", ""),
        "TF_DETERMINISTIC_OPS": child_meta.get("TF_DETERMINISTIC_OPS", ""),
        "OMP_NUM_THREADS": child_meta.get("OMP_NUM_THREADS", ""),
        "MKL_NUM_THREADS": child_meta.get("MKL_NUM_THREADS", ""),
        "tensorflow_version": child_meta.get("tensorflow_version", ""),
        "keras_version": child_meta.get("keras_version", ""),
        "child_returncode": completed.returncode,
    }])

    save_csv(RUNTIME_TABLE, [{
        "raw_shape": str(raw.shape),
        "creator100_shape": str(onednn_off100.shape),
        "creator100_dtype": str(onednn_off100.dtype),
        "creator100_finite": bool(np.all(np.isfinite(onednn_off100))),
        "creator100_min": float(np.min(onednn_off100)),
        "creator100_max": float(np.max(onednn_off100)),
        "creator100_sha256": onednn_hash,
    }])

    m_base = error_metrics(onednn_off100, baseline100)
    m_frozen = error_metrics(onednn_off100, frozen100)

    exact_baseline = bool(np.array_equal(onednn_off100, baseline100))
    exact_frozen = bool(np.array_equal(onednn_off100, frozen100))
    precision_pass = bool(m_frozen["Linf"] <= precision_envelope)

    absdiff = np.abs(onednn_off100.astype(np.float64) - frozen100.astype(np.float64))
    count_above = int(np.count_nonzero(absdiff > precision_envelope))

    ulp = ulp_distance(onednn_off100, frozen100)
    max_ulp = int(np.max(ulp))

    baseline_abs = np.abs(baseline100.astype(np.float64) - frozen100.astype(np.float64))
    fp_mask = baseline_abs > precision_envelope
    fp_count = int(np.count_nonzero(fp_mask))
    fp_frozen = int(np.count_nonzero(onednn_off100[fp_mask] == frozen100[fp_mask]))
    fp_base = int(np.count_nonzero(onednn_off100[fp_mask] == baseline100[fp_mask]))

    save_csv(COMPARE_TABLE, [
        {"comparison": "C1_vs_C0", **m_base, "exact": exact_baseline},
        {"comparison": "C1_vs_frozen100", **m_frozen, "exact": exact_frozen},
    ])

    save_csv(CLOSURE_TABLE, [{
        "precision_envelope": precision_envelope,
        "L1_to_frozen100": m_frozen["L1"],
        "L2_to_frozen100": m_frozen["L2"],
        "Linf_to_frozen100": m_frozen["Linf"],
        "count_above_envelope": count_above,
        "precision_pass": precision_pass,
        "exact_frozen100": exact_frozen,
        "fingerprint_cells": fp_count,
        "fingerprint_exact_frozen": fp_frozen,
        "fingerprint_exact_baseline": fp_base,
    }])

    save_csv(ULP_TABLE, [{
        "max_ulp_to_frozen100": max_ulp,
        "mean_ulp_to_frozen100": float(np.mean(ulp)),
        "p99_ulp_to_frozen100": float(np.percentile(ulp, 99)),
        "p999_ulp_to_frozen100": float(np.percentile(ulp, 99.9)),
    }])

    if exact_frozen:
        status = "ONEDNN_OFF_EXACTLY_REPRODUCES_HISTORICAL_FROZEN100"
        diagnosis = "ONEDNN_RUNTIME_ORDERING_IS_SUFFICIENT_TO_EXPLAIN_HISTORICAL_FROZEN100_IDENTITY"
        recommendation = (
            "Freeze this runtime-provenance result and proceed to downstream 100-day correction-chain replay."
        )
        next_ms = "V15-SG7E1R26J — 100-Day Downstream Correction-Chain Runtime Replay"
    elif precision_pass:
        status = "ONEDNN_OFF_RESTORES_FROZEN_PRECISION_CONTRACT_CLOSURE"
        diagnosis = "ONEDNN_OFF_RESTORES_UNCHANGED_R16_PRECISION_CLOSURE_WITHOUT_BITWISE_IDENTITY"
        recommendation = (
            "Do not widen tolerance. Revalidate C1 against the frozen precision-equivalence contract."
        )
        next_ms = "V15-SG7E1R26I-R19E — oneDNN-Off Precision-Equivalence Revalidation"
    else:
        status = "ONEDNN_OFF_DOES_NOT_EXPLAIN_HISTORICAL_FROZEN100"
        diagnosis = "AUTHORIZED_ONEDNN_VARIANCE_DOES_NOT_RESTORE_FROZEN100_CLOSURE"
        recommendation = (
            "Stop runtime-variance testing. Do not try arbitrary TensorFlow versions or thread changes. "
            "Record historical runtime as partially unrecoverable and resolve deployment authority accordingly."
        )
        next_ms = "V15-SG7E1R26I-R19E — Historical Runtime Reproducibility Limitation / Authority Decision Audit"

    gates = [
        ("R19C_design_status_reproduced", True),
        ("C1_authorized", True),
        ("TF_ENABLE_ONEDNN_OPTS_zero_in_child", child_meta.get("TF_ENABLE_ONEDNN_OPTS") == "0"),
        ("child_runtime_executed", completed.returncode == 0),
        ("model_output_shape_2662x201x1", raw.shape == (2662, 201, 1)),
        ("creator100_shape_2662x201", onednn_off100.shape == (2662, 201)),
        ("creator100_finite", bool(np.all(np.isfinite(onednn_off100)))),
        ("historical_90_cell_fingerprint_retained", fp_count == 90),
        ("precision_envelope_unchanged", True),
        ("no_alternative_tensorflow_version_tested", True),
        ("no_thread_contract_change", True),
        ("no_training_performed", True),
        ("no_model_parameter_changed", True),
        ("no_later_time_state_generated", True),
    ]
    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "baseline_sha256": baseline_hash,
        "onednn_off_sha256": onednn_hash,
        "frozen100_sha256": frozen_hash,
        "exact_baseline_match": exact_baseline,
        "exact_frozen_match": exact_frozen,
        "precision_frozen_pass": precision_pass,
        "Linf_to_baseline": m_base["Linf"],
        "Linf_to_frozen": m_frozen["Linf"],
        "count_above_envelope": count_above,
        "max_ulp_to_frozen": max_ulp,
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    np.savez_compressed(
        NUM_FILE,
        baseline100=baseline100,
        onednn_off100=onednn_off100,
        frozen100=frozen100,
        raw=raw,
        precision_envelope=np.asarray([precision_envelope], dtype=np.float64),
        fingerprint_mask=fp_mask.astype(np.uint8),
        ulp_to_frozen=ulp.astype(np.int64),
    )

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R19D",
        "status": status,
        "diagnosis": diagnosis,
        "runtime_case": {
            "case_id": "C1",
            "TF_ENABLE_ONEDNN_OPTS": "0",
            "tensorflow_version": child_meta.get("tensorflow_version", ""),
            "keras_version": child_meta.get("keras_version", ""),
        },
        "fixed_model": {"path": str(model_path), "sha256": model_sha},
        "fixed_X100_sha256": x100_sha,
        "hashes": {
            "baseline_creator100": baseline_hash,
            "onednn_off_creator100": onednn_hash,
            "historical_frozen100": frozen_hash,
        },
        "closure": {
            "to_baseline": m_base,
            "to_frozen100": m_frozen,
            "precision_envelope": precision_envelope,
            "precision_pass": precision_pass,
            "exact_frozen_hash_match": exact_frozen,
            "count_above_envelope": count_above,
            "max_ulp_to_frozen100": max_ulp,
        },
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R19D",
        "status": status,
        "diagnosis": diagnosis,
        "exact_frozen_match": exact_frozen,
        "precision_frozen_pass": precision_pass,
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("CONTROLLED RUNTIME CASE")
    print("  Case                    : C1")
    print(f"  TF_ENABLE_ONEDNN_OPTS   : {child_meta.get('TF_ENABLE_ONEDNN_OPTS', '')}")
    print(f"  TensorFlow              : {child_meta.get('tensorflow_version', '')}")
    print(f"  Keras                   : {child_meta.get('keras_version', '')}")

    print("\\n100-DAY OUTPUT IDENTITY")
    print(f"  Baseline SHA-256        : {baseline_hash}")
    print(f"  oneDNN-off SHA-256      : {onednn_hash}")
    print(f"  Frozen100 SHA-256       : {frozen_hash}")

    print("\\nC1 VS CURRENT BASELINE")
    print(f"  L1                      : {m_base['L1']:.6e}")
    print(f"  L2                      : {m_base['L2']:.6e}")
    print(f"  Linf                    : {m_base['Linf']:.6e}")
    print(f"  Exact                   : {exact_baseline}")

    print("\\nC1 VS HISTORICAL FROZEN100")
    print(f"  L1                      : {m_frozen['L1']:.6e}")
    print(f"  L2                      : {m_frozen['L2']:.6e}")
    print(f"  Linf                    : {m_frozen['Linf']:.6e}")
    print(f"  Precision envelope      : {precision_envelope:.6e}")
    print(f"  Count above envelope    : {count_above}")
    print(f"  Exact frozen100         : {exact_frozen}")
    print(f"  Precision pass          : {precision_pass}")
    print(f"  Max ULP                 : {max_ulp}")

    print("\\n90-CELL HISTORICAL FINGERPRINT")
    print(f"  Fingerprint cells       : {fp_count}")
    print(f"  Exact frozen values     : {fp_frozen}")
    print(f"  Exact baseline values   : {fp_base}")

    print("\\n" + "=" * 78)
    print("V15-SG7E1R26I-R19D FINAL REPLAY GATES")
    print("=" * 78)
    for g, p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")
    print("=" * 78)

    print("\\nSTATUS")
    print(f"  {status}")
    print("\\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\\nNEXT MILESTONE")
    print(f"  {next_ms}")
    print("\\nOUTPUTS")
    print(f"  Directory:\\n    {OUT}")
    print("\\nNumerical:")
    print(f"  {NUM_FILE.name}")
    print("\\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\\nSummary:")
    print(f"  {SUMMARY_FILE.name}")
    print("\\n" + "=" * 78)
    print("V15-SG7E1R26I-R19D CONTROLLED oneDNN-OFF 100-DAY REPLAY: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
