#!/usr/bin/env python3
"""PAD-Stream V16E-6B-T: Hybrid12 sealed internal-test evaluation.

This milestone opens the frozen INTERNAL TEST partition exactly once, only after
binding the validation-accepted V16E-6B checkpoint. No training, checkpoint
selection, hyperparameter tuning, threshold tuning, or OOD evaluation is
permitted. Test metrics are frozen as evidence. V16E-5 did not define separate
internal-test acceptance thresholds, so validation limits are shown only as
non-authoritative reference comparisons and cannot trigger model selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import sys
import tempfile

import numpy as np

MILESTONE = "V16E-6B-T"
REVISION = "R1_HYBRID12_SEALED_INTERNAL_TEST"
STATUS = "V16E6BT_HYBRID12_INTERNAL_TEST_EVALUATED_ONCE_METRICS_FROZEN_NO_MODEL_SELECTION"
NEXT = "V16E-7 — Hybrid10/Hybrid12 Evidence Synthesis and Deployment-Role Freeze; no test-informed model selection"

E6B_REL = Path("models/hybrid_dp/V16E6B_HYBRID12_CONTROLLED_R1")
E5_REL = Path("provenance/hybrid_dp/V16E5_PRETRAINING_MANIFEST_FREEZE")
DATA_REL = Path("datasets/hybrid_dp/V16E4_R1_DETERMINISTIC_TEACHER_DATASET")
OUT_REL = Path("evaluations/hybrid_dp/V16E6BT_HYBRID12_SEALED_INTERNAL_TEST_R1")
LOCK_REL = Path("provenance/hybrid_dp/V16E6BT_INTERNAL_TEST_OPEN_LOCK")

E6B_RUNNER = (
    "PAD_Stream_V16E6B_Hybrid12_Controlled_Training_and_Validation.py",
    "79cffcf527d20a8f036f561a5a5372f9858f47f91eb08dd34dc0069d6229dcf0",
)
E6B = {
    "checkpoint": ("V16E6B_Hybrid12_Accepted.weights.h5", "1321008f1127ae48fa3d230b89759337779a9db83819ae8a73719ed3dfec12d8"),
    "validation": ("V16E6B_Validation_Metrics.json", "3739954f7d6ee0157660f17b080379cacdb998f75f5cb1bca5f1df3141e87a59"),
    "summary": ("PAD_Stream_V16E6B_Summary.json", "ecb0cca6ff9b5c1a7c9131e92897ad80008a552e27ee1f456341683935b2ee4f"),
    "handoff": ("V16E6B_Handoff.md", "2bbfcb6549ac225410ad94501cf823943e405599a634f4ba7713f406349b5c12"),
}
E5 = {
    "manifest": ("V16E5_PreTraining_Manifest.json", "c197dae32d01a1f083f7ad414e601eac1f44d7405b6087c7c7db8a6c28c5c808"),
    "results": ("V16E5_PreTraining_Manifest_Freeze_Results.json", "3f605784f41f4cec2637887d4678d217a651b2f5b5fff0f1b9f659857dde4d84"),
    "summary": ("PAD_Stream_V16E5_Summary.json", "9736d303c5388f5cca87616583a6b5e692738fdd1e912b372c372c889abfdebd"),
    "handoff": ("V16E5_Handoff.md", "caf53b0dccf696c604e248688a30d81dac1a100afd8ff5eefbe601c8bb44e44a"),
}
E4 = {
    "manifest": ("V16E4_R1_Dataset_Manifest.json", "ec8c50720074f1ebe07be259073e44f5a82e03a45ca1cdc9385402fe280602a7"),
    "audit": ("V16E4_R1_Numerical_Audit.json", "ca0a6320e773dfee9a405ef23b509101a3862446f541fdf2b17133861b73c16b"),
    "summary": ("PAD_Stream_V16E4_R1_Summary.json", "85544f6b160025fb534fb9c047a16d05d9bb0bf55a461eb163f5ae924cdedbaf"),
    "handoff": ("V16E4_R1_Handoff.md", "8e6d14221135cd00e5d4a31d775a02d23709bfa2296757204360ced79bd71790"),
}
R2_ADAPTER_SHA = "640a853fd0775c5efaf2922976d5c3843fa69ce9e5165245daffefdb3d4eac2a"
E6AT_REL = Path("evaluations/hybrid_dp/V16E6AT_HYBRID10_SEALED_INTERNAL_TEST_R1")
E6AT_RUNNER = (
    "PAD_Stream_V16E6AT_Hybrid10_Sealed_Internal_Test_Evaluation.py",
    "6cad3a01c5c05ce7488956cfe358294eef41af5ffa79876d08d19312f39b660f",
)
E6AT = {
    "metrics": ("V16E6AT_Hybrid10_Internal_Test_Metrics.json", "35c48d2e2e01c8c4efc2d1594970c929f1d87cfd93066f242dd306ad863fe218"),
    "results": ("V16E6AT_Sealed_Internal_Test_Evaluation_Results.json", "0343911f35329309ae88a0431de38f1b448b940559b5582d1ed57064d3cc2e7f"),
    "summary": ("PAD_Stream_V16E6AT_Summary.json", "c1f72fbce37fa5e7b5346c9cf36a55452ba454ccd0580fb8469b85bba4e516db"),
    "handoff": ("V16E6AT_Handoff.md", "384c93e2d431501d4b20351b2c6069b70d59acf91822dc3a29ad3c6522ba56d3"),
}
FEATURES12 = ["no", "nw", "swc", "sor", "mu_w", "mu_o", "phi", "krw_max", "kro_max", "tD", "xD_star", "Sw_star"]

PROHIBITIONS = [
    "NO TRAINING OR GRADIENT UPDATE.",
    "NO CHECKPOINT SELECTION OR REPLACEMENT.",
    "NO HYPERPARAMETER OR THRESHOLD TUNING.",
    "NO VALIDATION-OR-TEST-INFORMED MODEL CHANGE.",
    "NO OOD REOPENING.",
    "NO HYBRID12 TRAINING OR RETRAINING IN THIS MILESTONE.",
    "NO DATASET, SPLIT, TEACHER, TOLERANCE OR LOSS-WEIGHT CHANGE.",
    "NO SECOND INTERNAL-TEST EVALUATION UNDER THIS RUN ID.",
    "NO HISTORICAL HYBRID CHECKPOINT CLAIM.",
    "NO SGSim MODIFICATION, POLLOCK/TOF RECOMPUTATION, OR B4 RETRAINING.",
]


class GateError(RuntimeError):
    pass


class Gates:
    def __init__(self):
        self.items = {}

    def check(self, name, condition, detail=""):
        ok = bool(condition)
        self.items[name] = {"passed": ok, "detail": detail}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)
        if not ok:
            raise GateError(name + ((": " + detail) if detail else ""))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False, ensure_ascii=False) + "\n").encode("utf-8")


def read_json(path: Path):
    def reject(value):
        raise GateError("Nonfinite JSON literal: " + value)
    return json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=reject)


def bind(gates: Gates, label: str, path: Path, expected: str):
    gates.check(label + "_exists", path.is_file(), str(path))
    actual = sha(path)
    gates.check(label + "_SHA_exact", actual == expected,
                "" if actual == expected else f"expected {expected}; actual {actual}")


def tree_hashes(root: Path):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def publish_tree(stage: Path, out: Path):
    if out.exists():
        raise GateError("Sealed internal-test output already exists; re-evaluation is forbidden.")
    out.parent.mkdir(parents=True, exist_ok=True)
    sibling = Path(tempfile.mkdtemp(prefix=".v16e6at-publish-", dir=out.parent))
    try:
        for src in sorted(stage.rglob("*")):
            if src.is_file():
                dst = sibling / src.relative_to(stage)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
        if tree_hashes(stage) != tree_hashes(sibling):
            raise GateError("Publication byte verification failed")
        sibling.rename(out)
    finally:
        if sibling.exists():
            shutil.rmtree(sibling)


def verify_authority(project: Path, drive: Path, gates: Gates):
    e6b_dir = drive / E6B_REL
    e5_dir = drive / E5_REL
    data_dir = drive / DATA_REL

    print("\nV16E-6B ACCEPTED CHECKPOINT AUTHORITY", flush=True)
    bind(gates, "E6B_runner", project / E6B_RUNNER[0], E6B_RUNNER[1])
    for label, (name, expected) in E6B.items():
        bind(gates, "E6B_" + label, e6b_dir / name, expected)

    summary = read_json(e6b_dir / E6B["summary"][0])
    validation = read_json(e6b_dir / E6B["validation"][0])
    handoff_text = (e6b_dir / E6B["handoff"][0]).read_text(encoding="utf-8")
    gates.check("E6B_milestone_exact", summary.get("milestone") == "V16E-6B")
    gates.check("E6B_training_performed_true", summary.get("training_performed") is True)
    gates.check("E6B_checkpoint_published_true", summary.get("accepted_checkpoint_published") is True)
    gates.check("E6B_validation_passed_true", summary.get("validation_all_gates_passed") is True)
    gates.check("E6B_internal_test_not_evaluated", summary.get("internal_test_evaluated") is False)
    gates.check("E6B_OOD_not_evaluated", summary.get("OOD_evaluated") is False)
    gates.check("E6B_Hybrid10_checkpoint_unchanged", summary.get("Hybrid10_checkpoint_unchanged") is True)
    gates.check("E6B_summary_checkpoint_link", summary.get("checkpoint_sha256") == E6B["checkpoint"][1])
    gates.check("E6B_validation_partition_exact", validation.get("partition") == "validation")
    gates.check("E6B_validation_profiles_exact", validation.get("profiles") == 48000)
    gates.check("E6B_validation_all_gates_passed", validation.get("all_gates_passed") is True)
    gates.check("E6B_validation_internal_test_false", validation.get("internal_test_loaded") is False)

    match = re.search(r"Checkpoint identity SHA:\s*([0-9a-f]{64})", handoff_text)
    gates.check("E6B_handoff_identity_SHA_present", match is not None)
    identity_expected = match.group(1)
    identity_path = e6b_dir / "V16E6B_Checkpoint_Identity.json"
    bind(gates, "E6B_checkpoint_identity", identity_path, identity_expected)
    identity = read_json(identity_path)
    gates.check("E6B_identity_checkpoint_link", identity.get("checkpoint_sha256") == E6B["checkpoint"][1])
    gates.check("E6B_identity_validation_passed", identity.get("validation_all_gates_passed") is True)
    gates.check("E6B_identity_internal_test_false", identity.get("internal_test_evaluated") is False)
    gates.check("E6B_identity_historical_claim_false", identity.get("historical_checkpoint_claimed") is False)

    selected_match = re.search(r"Selected epoch:\s*(\d+)", handoff_text)
    gates.check("E6B_handoff_selected_epoch_present", selected_match is not None)
    selected_epoch = int(selected_match.group(1))
    gates.check("E6B_identity_selected_epoch_link", identity.get("selected_epoch") == selected_epoch)

    print("\nV16E-6A-T COMPLETED HYBRID10 TEST AUTHORITY", flush=True)
    e6at_dir = drive / E6AT_REL
    bind(gates, "E6AT_runner", project / E6AT_RUNNER[0], E6AT_RUNNER[1])
    for label, (name, expected) in E6AT.items():
        bind(gates, "E6AT_" + label, e6at_dir / name, expected)
    e6at_results = read_json(e6at_dir / E6AT["results"][0])
    e6at_summary = read_json(e6at_dir / E6AT["summary"][0])
    gates.check("E6AT_evaluation_completed", e6at_results.get("evaluation_completed") is True)
    gates.check("E6AT_one_time_evaluation", e6at_results.get("internal_test_evaluation_count_under_run_id") == 1)
    gates.check("E6AT_no_model_selection", e6at_results.get("model_selection_performed") is False)
    gates.check("E6AT_no_retraining", e6at_results.get("training_performed") is False)
    gates.check("E6AT_OOD_closed", e6at_results.get("OOD_opened") is False)
    gates.check("E6AT_summary_one_time", e6at_summary.get("internal_test_evaluation_count") == 1)
    gates.check("E6B_identity_parent_E6AT_link", identity.get("E6AT_parent_results_sha256") == E6AT["results"][1])

    print("\nV16E-5 SEALED-EVALUATION AUTHORITY", flush=True)
    for label, (name, expected) in E5.items():
        bind(gates, "E5_" + label, e5_dir / name, expected)
    manifest = read_json(e5_dir / E5["manifest"][0])
    c = manifest["common_training_protocol"]
    gates.check("E5_internal_test_one_final_evaluation",
                c["sealed_evaluation"]["internal_test_evaluation"] ==
                "one final evaluation only after validation-accepted checkpoint identity is frozen")
    gates.check("E5_internal_test_not_in_selection", c["checkpoint_selection"]["internal_test_in_selection"] is False)
    gates.check("E5_Hybrid12_features_exact", manifest["experiments"]["Hybrid12"]["feature_order"] == FEATURES12)
    gates.check("E5_TensorFlow_2_20_exact", c["framework"]["version"] == "2.20.0")

    print("\nV16E-4-R1 DATASET AUTHORITY", flush=True)
    for label, (name, expected) in E4.items():
        bind(gates, "E4_R1_" + label, data_dir / name, expected)
    e4_manifest = read_json(data_dir / E4["manifest"][0])
    inventory = e4_manifest.get("artifacts", {})
    gates.check("E4_artifact_inventory_present", isinstance(inventory, dict) and len(inventory) == 22)
    for i, (rel, meta) in enumerate(sorted(inventory.items())):
        p = data_dir / rel
        gates.check(f"artifact_{i:02d}_exists", p.is_file(), rel)
        gates.check(f"artifact_{i:02d}_SHA_exact", sha(p) == meta.get("sha256"), rel)
        gates.check(f"artifact_{i:02d}_size_exact", p.stat().st_size == meta.get("bytes"), rel)
    gates.check("E4_R1_R2_adapter_link", e4_manifest.get("R2_adapter", {}).get("sha256") == R2_ADAPTER_SHA)

    return manifest, validation, identity, data_dir, e6b_dir


def prepare_tensorflow(manifest):
    os.environ["TF_DETERMINISTIC_OPS"] = "1"
    os.environ["TF_CUDNN_DETERMINISTIC"] = "1"
    import tensorflow as tf

    expected = manifest["common_training_protocol"]["framework"]["version"]
    if tf.__version__ != expected:
        raise GateError(f"TensorFlow version mismatch: expected {expected}, actual {tf.__version__}")
    if tf.keras.mixed_precision.global_policy().name != "float32":
        tf.keras.mixed_precision.set_global_policy("float32")
    tf.config.experimental.enable_op_determinism()
    random.seed(1605)
    np.random.seed(1605)
    tf.keras.utils.set_random_seed(1605)
    return tf


def build_inference_model(tf):
    class Hybrid12Inference(tf.keras.Model):
        def __init__(self):
            super().__init__(name="V16E6B_Hybrid12")
            self.repeat = tf.keras.layers.RepeatVector(201, name="repeat_conditioning")
            self.concat = tf.keras.layers.Concatenate(axis=-1, name="concat_xi_conditioning")
            self.lstm1 = tf.keras.layers.LSTM(
                64, return_sequences=True, activation="tanh", recurrent_activation="sigmoid",
                dropout=0.0, recurrent_dropout=0.0,
                kernel_initializer=tf.keras.initializers.GlorotUniform(),
                recurrent_initializer=tf.keras.initializers.Orthogonal(),
                bias_initializer=tf.keras.initializers.Zeros(), name="lstm_1")
            self.lstm2 = tf.keras.layers.LSTM(
                64, return_sequences=True, activation="tanh", recurrent_activation="sigmoid",
                dropout=0.0, recurrent_dropout=0.0,
                kernel_initializer=tf.keras.initializers.GlorotUniform(),
                recurrent_initializer=tf.keras.initializers.Orthogonal(),
                bias_initializer=tf.keras.initializers.Zeros(), name="lstm_2")
            self.head = tf.keras.layers.TimeDistributed(
                tf.keras.layers.Dense(1, kernel_initializer=tf.keras.initializers.GlorotUniform(),
                                      bias_initializer=tf.keras.initializers.Zeros()), name="td_dense")

        def call(self, inputs, training=False):
            xi, p = inputs
            pexp = self.repeat(p)
            x = self.concat([xi, pexp])
            x = self.lstm1(x, training=False)
            x = self.lstm2(x, training=False)
            z = self.head(x, training=False)
            swc = pexp[:, :, 2:3]
            sor = pexp[:, :, 3:4]
            span = 1.0 - swc - sor
            return swc + span * tf.math.sigmoid(z)

    model = Hybrid12Inference()
    xi_dummy = tf.zeros((1, 201, 1), dtype=tf.float32)
    p_dummy = tf.zeros((1, 12), dtype=tf.float32)
    p_dummy = tf.tensor_scatter_nd_update(p_dummy, [[0,2],[0,3],[0,4],[0,5],[0,7],[0,8],[0,9]], [0.2,0.2,0.5,1.0,0.8,0.8,0.1])
    _ = model([xi_dummy, p_dummy], training=False)
    return model


def open_internal_test_once(data_dir: Path, drive: Path, out: Path, project: Path, gates: Gates):
    lock_dir = drive / LOCK_REL
    lock_file = lock_dir / "V16E6BT_Internal_Test_Open_Lock.json"

    if out.exists():
        raise GateError("V16E-6B-T output already exists. The sealed test has already been evaluated; rerun forbidden.")
    if lock_file.exists():
        raise GateError("Internal-test open lock already exists without accepted output. Automatic re-opening is forbidden; review provenance first.")

    codes = np.load(data_dir / "partition_codes.npy", allow_pickle=False)
    gates.check("partition_codes_shape_exact", codes.shape == (1000,))
    gates.check("partition_counts_exact", {i: int(np.sum(codes == i)) for i in (0,1,2)} == {0:700, 1:150, 2:150})

    # Create persistent single-use lock immediately before partition code 2 is indexed.
    lock_dir.mkdir(parents=True, exist_ok=False)
    lock_payload = {
        "milestone": MILESTONE,
        "evaluation_run_id": "V16E6BT-HYBRID12-R1",
        "checkpoint_sha256": E6B["checkpoint"][1],
        "E6B_summary_sha256": E6B["summary"][1],
        "runner_sha256": sha(Path(__file__)),
        "meaning": "partition code 2 may be indexed exactly once under this frozen run identity; lock is permanent evidence",
    }
    lock_file.write_bytes(encoded(lock_payload))
    gates.check("internal_test_open_lock_created", lock_file.is_file(), str(lock_file))

    family_idx = np.flatnonzero(codes == 2)
    gates.check("internal_test_family_count_exact", family_idx.size == 150)

    cond_mm = np.load(data_dir / "Hybrid12" / "conditioning.npy", mmap_mode="r", allow_pickle=False)
    target_mm = np.load(data_dir / "Hybrid12" / "Sw_fan_teacher.npy", mmap_mode="r", allow_pickle=False)
    if cond_mm.shape != (1000, 2, 8, 20, 12) or cond_mm.dtype != np.float32:
        raise GateError("Hybrid12 conditioning contract changed")
    if target_mm.shape != (1000, 8, 20, 201) or target_mm.dtype != np.float32:
        raise GateError("Hybrid12 target contract changed")

    # This is the single intentional sealed-partition access.
    cond = np.asarray(cond_mm[family_idx], dtype=np.float32).reshape(-1, 12)
    base_target = np.asarray(target_mm[family_idx], dtype=np.float32)
    target = np.repeat(base_target[:, None, :, :, :], 2, axis=1).reshape(-1, 201)
    del cond_mm, target_mm, base_target

    family_ids_all = np.load(data_dir / "family_ids.npy", allow_pickle=False)
    family_ids = [str(x) for x in family_ids_all[family_idx].tolist()]
    gates.check("internal_test_family_ids_exact_count", len(family_ids) == 150 and len(set(family_ids)) == 150)
    gates.check("internal_test_profile_count_exact", cond.shape == (48000,12) and target.shape == (48000,201))
    gates.check("internal_test_inputs_finite", np.all(np.isfinite(cond)) and np.all(np.isfinite(target)))
    print("[PASS] sealed_internal_test_opened_once: partition code 2 indexed only after permanent lock creation", flush=True)
    return cond, target, family_ids, lock_file


def numpy_fprime(sw, p):
    no = p[:, 0:1]
    nw = p[:, 1:2]
    swc = p[:, 2:3]
    sor = p[:, 3:4]
    mu_w = p[:, 4:5]
    mu_o = p[:, 5:6]
    span = 1.0 - swc - sor
    s = np.clip((sw - swc) / span, 0.0, 1.0)
    Aw = p[:, 7:8] / mu_w
    Ao = p[:, 8:9] / mu_o
    lw = Aw * np.power(s, nw)
    lo = Ao * np.power(1.0 - s, no)
    dlw = Aw * nw * np.power(s, nw - 1.0)
    dlo = -Ao * no * np.power(1.0 - s, no - 1.0)
    total = lw + lo
    return ((dlw * total - lw * (dlw + dlo)) / np.maximum(np.square(total), 1e-24)) / span


def evaluate_metrics(model, cond, target, xi, batch_size):
    sums = {"sq":0.0, "abs":0.0, "bc_sq":0.0, "front_sq":0.0, "phys_sq":0.0}
    counts = {"nodes":0, "profiles":0, "phys":0, "mono":0, "increments":0, "nonfinite":0}
    profile_rmse_parts = []
    profile_mae_parts = []
    xi2 = xi[None, :]

    for start in range(0, cond.shape[0], batch_size):
        stop = min(start + batch_size, cond.shape[0])
        p = cond[start:stop]
        y = target[start:stop]
        xi_batch = np.broadcast_to(xi[None,:,None].astype(np.float32), (p.shape[0],201,1))
        pred = model([xi_batch, p], training=False).numpy()[:,:,0].astype(np.float64)
        counts["nonfinite"] += int(np.size(pred) - np.count_nonzero(np.isfinite(pred)))
        if not np.all(np.isfinite(pred)):
            pred = np.nan_to_num(pred, nan=1e30, posinf=1e30, neginf=-1e30)
        y64 = y.astype(np.float64)
        diff = pred - y64
        sums["sq"] += float(np.sum(diff*diff))
        sums["abs"] += float(np.sum(np.abs(diff)))
        counts["nodes"] += int(diff.size)
        profile_rmse_parts.append(np.sqrt(np.mean(diff*diff, axis=1)))
        profile_mae_parts.append(np.mean(np.abs(diff), axis=1))
        sums["bc_sq"] += float(np.sum(np.square(pred[:,0] - (1.0 - p[:,3]))))
        sums["front_sq"] += float(np.sum(np.square(pred[:,-1] - p[:,11])))
        counts["profiles"] += int(p.shape[0])

        fp = numpy_fprime(pred, p.astype(np.float64))
        rhs = xi2 * (p[:,10:11].astype(np.float64) / p[:,9:10].astype(np.float64))
        r = fp[:,1:-1] - rhs[:,1:-1]
        sums["phys_sq"] += float(np.sum(r*r))
        counts["phys"] += int(r.size)
        inc = np.diff(pred, axis=1)
        counts["mono"] += int(np.count_nonzero(inc > 0.0))
        counts["increments"] += int(inc.size)

    profile_rmse = np.concatenate(profile_rmse_parts)
    profile_mae = np.concatenate(profile_mae_parts)
    metrics = {
        "Sw_RMSE": math.sqrt(sums["sq"] / counts["nodes"]),
        "Sw_MAE": sums["abs"] / counts["nodes"],
        "profile_RMSE_p50": float(np.percentile(profile_rmse, 50.0)),
        "profile_RMSE_p95": float(np.percentile(profile_rmse, 95.0)),
        "profile_RMSE_p99": float(np.percentile(profile_rmse, 99.0)),
        "profile_RMSE_max": float(np.max(profile_rmse)),
        "BC_RMSE": math.sqrt(sums["bc_sq"] / counts["profiles"]),
        "front_RMSE": math.sqrt(sums["front_sq"] / counts["profiles"]),
        "physics_characteristic_RMSE": math.sqrt(sums["phys_sq"] / counts["phys"]),
        "monotonic_violation_fraction": counts["mono"] / counts["increments"],
        "nonfinite_predictions": counts["nonfinite"],
        "test_profiles": counts["profiles"],
    }
    return metrics, profile_rmse, profile_mae


def ratio_or_none(a, b):
    if b is None or b == 0:
        return None
    return a / b


def run(project: Path, drive: Path, out: Path):
    print("="*118 + "\nPAD-Stream V16E-6B-T\nHybrid12 Sealed Internal-Test Evaluation\n" + "="*118, flush=True)
    print("\n".join(PROHIBITIONS), flush=True)
    gates = Gates()
    manifest, validation_payload, identity, data_dir, e6b_dir = verify_authority(project, drive, gates)

    print("\nFROZEN INFERENCE RUNTIME / CHECKPOINT", flush=True)
    tf = prepare_tensorflow(manifest)
    gates.check("TensorFlow_2_20_exact", tf.__version__ == "2.20.0", tf.__version__)
    model = build_inference_model(tf)
    trainable_count = int(sum(np.prod(v.shape) for v in model.trainable_variables))
    gates.check("trainable_parameter_count_exact", trainable_count == 53057, str(trainable_count))
    checkpoint = e6b_dir / E6B["checkpoint"][0]
    model.load_weights(checkpoint)
    gates.check("accepted_checkpoint_loaded_exact", sha(checkpoint) == E6B["checkpoint"][1])

    xi = np.load(data_dir / "xi.npy", allow_pickle=False)
    gates.check("xi_exact", xi.shape == (201,) and np.array_equal(xi, np.arange(201,dtype=np.float64)/200.0))

    print("\nOPEN SEALED INTERNAL TEST — SINGLE USE", flush=True)
    test_cond, test_target, family_ids, lock_file = open_internal_test_once(data_dir, drive, out, project, gates)

    print("\nFINAL HYBRID12 INTERNAL-TEST EVALUATION", flush=True)
    batch_size = manifest["common_training_protocol"]["training"]["batch_size_profiles"]
    test_metrics, profile_rmse, profile_mae = evaluate_metrics(model, test_cond, test_target, xi, batch_size)
    gates.check("test_profile_count_exact", test_metrics["test_profiles"] == 48000)
    print("Internal-test metrics (descriptive; no model selection):", flush=True)
    for key, value in test_metrics.items():
        print(f"  {key}: {value}", flush=True)

    # 320 profiles per physical family: 2 allocation modes * 8 layers * 20 clocks.
    family_profile_rmse = profile_rmse.reshape(150, 320)
    family_profile_mae = profile_mae.reshape(150, 320)
    family_rows = []
    for i, fid in enumerate(family_ids):
        family_rows.append({
            "family_id": fid,
            "mean_profile_RMSE": float(np.mean(family_profile_rmse[i])),
            "p95_profile_RMSE": float(np.percentile(family_profile_rmse[i],95.0)),
            "max_profile_RMSE": float(np.max(family_profile_rmse[i])),
            "mean_profile_MAE": float(np.mean(family_profile_mae[i])),
        })

    validation_metrics = validation_payload["metrics"]
    comparison = {}
    for key in ["Sw_RMSE","Sw_MAE","profile_RMSE_p95","BC_RMSE","front_RMSE",
                "physics_characteristic_RMSE","monotonic_violation_fraction","nonfinite_predictions"]:
        tv = test_metrics[key]
        vv = validation_metrics.get(key)
        comparison[key] = {
            "validation": vv,
            "internal_test": tv,
            "test_minus_validation": None if vv is None else tv - vv,
            "test_to_validation_ratio": ratio_or_none(tv, vv),
        }

    reference_limits = manifest["common_training_protocol"]["validation_acceptance"]
    reference_comparison = {
        "non_authoritative_reference_only": True,
        "reason": "V16E-5 froze these limits for validation acceptance, not as post-hoc internal-test acceptance gates",
        "comparisons": {
            "Sw_RMSE_max": test_metrics["Sw_RMSE"] <= reference_limits["Sw_RMSE_max"],
            "Sw_MAE_max": test_metrics["Sw_MAE"] <= reference_limits["Sw_MAE_max"],
            "profile_RMSE_p95_max": test_metrics["profile_RMSE_p95"] <= reference_limits["profile_RMSE_p95_max"],
            "BC_RMSE_max": test_metrics["BC_RMSE"] <= reference_limits["BC_RMSE_max"],
            "front_RMSE_max": test_metrics["front_RMSE"] <= reference_limits["front_RMSE_max"],
            "physics_characteristic_RMSE_max": test_metrics["physics_characteristic_RMSE"] <= reference_limits["physics_characteristic_RMSE_max"],
            "monotonic_violation_fraction_max": test_metrics["monotonic_violation_fraction"] <= reference_limits["monotonic_violation_fraction_max"],
            "nonfinite_predictions_allowed": test_metrics["nonfinite_predictions"] <= reference_limits["nonfinite_predictions_allowed"],
        },
    }

    del test_cond, test_target, profile_rmse, profile_mae

    print("\nFREEZE SEALED TEST EVIDENCE", flush=True)
    with tempfile.TemporaryDirectory(prefix="v16e6bt-output-") as tmp:
        stage = Path(tmp)
        metrics_payload = {
            "milestone": MILESTONE,
            "revision": REVISION,
            "evaluation_run_id": "V16E6BT-HYBRID12-R1",
            "partition": "internal_test",
            "families": 150,
            "profiles": 48000,
            "checkpoint_sha256": E6B["checkpoint"][1],
            "metrics": test_metrics,
            "validation_comparison": comparison,
            "validation_limit_reference": reference_comparison,
            "model_selection_performed": False,
            "checkpoint_changed": False,
            "retraining_performed": False,
            "OOD_opened": False,
        }
        (stage / "V16E6BT_Hybrid12_Internal_Test_Metrics.json").write_bytes(encoded(metrics_payload))
        (stage / "V16E6BT_Hybrid12_Family_Metrics.json").write_bytes(encoded({
            "milestone": MILESTONE, "families": 150, "profiles_per_family": 320,
            "rows": family_rows,
        }))
        results = {
            "milestone": MILESTONE,
            "revision": REVISION,
            "status": STATUS,
            "runner_sha256": sha(Path(__file__)),
            "E6B_checkpoint_sha256": E6B["checkpoint"][1],
            "E6B_validation_metrics_sha256": E6B["validation"][1],
            "E6B_summary_sha256": E6B["summary"][1],
            "E5_manifest_sha256": E5["manifest"][1],
            "E4_dataset_manifest_sha256": E4["manifest"][1],
            "internal_test_open_lock_sha256": sha(lock_file),
            "internal_test_evaluation_count_under_run_id": 1,
            "evaluation_completed": True,
            "test_metrics": test_metrics,
            "test_acceptance_thresholds_claimed": False,
            "model_selection_performed": False,
            "checkpoint_replaced": False,
            "training_performed": False,
            "hyperparameter_tuning_performed": False,
            "OOD_opened": False,
            "Hybrid10_and_Hybrid12_evidence_complete_next": True,
            "next_milestone": NEXT,
            "acceptance_gates": gates.items,
        }
        (stage / "V16E6BT_Sealed_Internal_Test_Evaluation_Results.json").write_bytes(encoded(results))
        summary = {
            "milestone": MILESTONE,
            "revision": REVISION,
            "status": STATUS,
            "checkpoint_sha256": E6B["checkpoint"][1],
            "internal_test_evaluated": True,
            "internal_test_evaluation_count": 1,
            "test_metrics_frozen": True,
            "test_acceptance_thresholds_claimed": False,
            "model_selection_performed": False,
            "checkpoint_changed": False,
            "training_performed": False,
            "OOD_evaluated": False,
            "Hybrid10_and_Hybrid12_evidence_complete_next": True,
            "next_milestone": NEXT,
        }
        (stage / "PAD_Stream_V16E6BT_Summary.json").write_bytes(encoded(summary))
        handoff = f"""# PAD-Stream V16E-6B-T — Hybrid12 sealed internal-test evaluation\n\nThe exact validation-accepted V16E-6B Hybrid12 checkpoint was evaluated once on\nthe previously sealed 150-family INTERNAL TEST partition (48,000 profiles). No\ntraining, checkpoint selection, replacement, hyperparameter tuning, or OOD access\noccurred. A permanent open-lock was written immediately before partition code 2\nwas indexed, preventing automatic repeat evaluation under this run identity.\n\nV16E-5 did not freeze separate internal-test acceptance thresholds. Therefore the\ntest metrics are descriptive final generalization evidence. The frozen validation\nlimits are reported only as reference comparisons and are not used to select or\nmodify the model. Any response to the test result must occur prospectively in a\nnew milestone; this checkpoint identity is unchanged.\n\nCheckpoint SHA: {E6B['checkpoint'][1]}\nInternal-test metrics SHA: {sha(stage / 'V16E6BT_Hybrid12_Internal_Test_Metrics.json')}\nResults SHA: {sha(stage / 'V16E6BT_Sealed_Internal_Test_Evaluation_Results.json')}\n\nNEXT: {NEXT}\n"""
        (stage / "V16E6BT_Handoff.md").write_text(handoff, encoding="utf-8")
        publish_tree(stage, out)

    print("\n" + "="*118 + "\nV16E-6B-T RESULT: PASS\n" + "="*118, flush=True)
    print(f"{'Accepted Hybrid12 checkpoint unchanged':48}: YES", flush=True)
    print(f"{'Internal-test families / profiles evaluated':48}: 150 / 48000", flush=True)
    print(f"{'Internal-test evaluation count':48}: 1", flush=True)
    print(f"{'Model selection / retraining performed':48}: NO / NO", flush=True)
    print(f"{'Separate test acceptance thresholds claimed':48}: NO", flush=True)
    print(f"{'OOD opened':48}: NO", flush=True)
    print("Output:", out, flush=True)
    print("Internal-test metrics SHA:", sha(out / "V16E6BT_Hybrid12_Internal_Test_Metrics.json"), flush=True)
    print("Results SHA:", sha(out / "V16E6BT_Sealed_Internal_Test_Evaluation_Results.json"), flush=True)
    print("Summary SHA:", sha(out / "PAD_Stream_V16E6BT_Summary.json"), flush=True)
    print("Handoff SHA:", sha(out / "V16E6BT_Handoff.md"), flush=True)
    print("NEXT:", NEXT, flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        return run(args.project_root.resolve(), args.drive_root.resolve(),
                   (args.output_dir or args.drive_root / OUT_REL).resolve())
    except (GateError, OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        print("\n[FAIL] V16E-6B-T did not close:", exc, file=sys.stderr, flush=True)
        print("No second Hybrid12 internal-test evaluation, training, or checkpoint change is authorized by this failure.", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
