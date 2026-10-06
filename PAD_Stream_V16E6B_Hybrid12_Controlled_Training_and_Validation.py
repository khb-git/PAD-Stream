#!/usr/bin/env python3
"""PAD-Stream V16E-6B: prospective Hybrid12 controlled training and validation.

This is the second prospective Hybrid training milestone. V16E-5 froze the
Hybrid12 recipe but deferred execution until the Hybrid10 predecessor passed.
It binds V16E-6A-T, V16E-6A, V16E-5 and V16E-4-R1 before training, and trains
only Hybrid12 under the frozen recipe, selects one checkpoint from VALIDATION
only, and evaluates the frozen validation acceptance gates. The internal-test
partition and all OOD assets remain sealed.

No hyperparameter search or automatic repair is permitted. If validation fails,
no accepted checkpoint is published; a new prospective protocol is required
before any retraining with changed settings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import time

import numpy as np

MILESTONE = "V16E-6B"
REVISION = "R1_HYBRID12_CONTROLLED_TRAINING_VALIDATION"
SUCCESS = "V16E6B_HYBRID12_CONTROLLED_TRAINING_VALIDATION_ACCEPTED_CHECKPOINT_FROZEN_INTERNAL_TEST_STILL_SEALED"
BLOCKED = "V16E6B_HYBRID12_CONTROLLED_TRAINING_VALIDATION_BLOCKED_NO_ACCEPTED_CHECKPOINT_PUBLISHED"
NEXT_PASS = "V16E-6B-T — Hybrid12 Sealed Internal-Test Evaluation; one final evaluation, no model selection"
NEXT_FAIL = "V16E-5-R1 — prospective pre-training protocol revision required before any Hybrid12 retraining"

E5_REL = Path("provenance/hybrid_dp/V16E5_PRETRAINING_MANIFEST_FREEZE")
DATA_REL = Path("datasets/hybrid_dp/V16E4_R1_DETERMINISTIC_TEACHER_DATASET")
OUT_REL = Path("models/hybrid_dp/V16E6B_HYBRID12_CONTROLLED_R1")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E6B_BLOCKED_TRAINING")

E5 = {
    "manifest": ("V16E5_PreTraining_Manifest.json", "c197dae32d01a1f083f7ad414e601eac1f44d7405b6087c7c7db8a6c28c5c808"),
    "results": ("V16E5_PreTraining_Manifest_Freeze_Results.json", "3f605784f41f4cec2637887d4678d217a651b2f5b5fff0f1b9f659857dde4d84"),
    "summary": ("PAD_Stream_V16E5_Summary.json", "9736d303c5388f5cca87616583a6b5e692738fdd1e912b372c372c889abfdebd"),
    "handoff": ("V16E5_Handoff.md", "caf53b0dccf696c604e248688a30d81dac1a100afd8ff5eefbe601c8bb44e44a"),
}
E5_RUNNER = ("PAD_Stream_V16E5_PreTraining_Manifest_Freeze.py", "38849300cb611511575fc0dc4c023758a3d61462d31c0aa82fe863989e54f56e")
E4 = {
    "manifest": ("V16E4_R1_Dataset_Manifest.json", "ec8c50720074f1ebe07be259073e44f5a82e03a45ca1cdc9385402fe280602a7"),
    "audit": ("V16E4_R1_Numerical_Audit.json", "ca0a6320e773dfee9a405ef23b509101a3862446f541fdf2b17133861b73c16b"),
    "summary": ("PAD_Stream_V16E4_R1_Summary.json", "85544f6b160025fb534fb9c047a16d05d9bb0bf55a461eb163f5ae924cdedbaf"),
    "handoff": ("V16E4_R1_Handoff.md", "8e6d14221135cd00e5d4a31d775a02d23709bfa2296757204360ced79bd71790"),
}
R2_ADAPTER_SHA = "640a853fd0775c5efaf2922976d5c3843fa69ce9e5165245daffefdb3d4eac2a"
E6A_REL = Path("models/hybrid_dp/V16E6A_HYBRID10_CONTROLLED_R1")
E6AT_REL = Path("evaluations/hybrid_dp/V16E6AT_HYBRID10_SEALED_INTERNAL_TEST_R1")
E6AT_LOCK_REL = Path("provenance/hybrid_dp/V16E6AT_INTERNAL_TEST_OPEN_LOCK")
E6A_RUNNER = (
    "PAD_Stream_V16E6A_Hybrid10_Controlled_Training_and_Validation.py",
    "c48a1d8f185bb4576af7e255a5cf190fc47d2fa5360f526e2254d831254994ad",
)
E6A = {
    "checkpoint": ("V16E6A_Hybrid10_Accepted.weights.h5", "0b7be119dfc14c08bd8f7bb3c84c64b8d425e0176cddebf952687a49c05402a9"),
    "validation": ("V16E6A_Validation_Metrics.json", "235c41ed2e6bbf63a242cf5a8d6386802e752705dafee9705e8d09453a9589f0"),
    "summary": ("PAD_Stream_V16E6A_Summary.json", "3a737b4c8a15e30fcc5a2acf9a94a6e7af5f26a3158c99f6207e78986c0a60ea"),
    "handoff": ("V16E6A_Handoff.md", "c3ba1b3ffb4439d616f9420542e9bfc1f42b4e47467d324f075d924f78467586"),
}
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
    "NO HYPERPARAMETER SEARCH.",
    "NO INTERNAL-TEST LOADING OR MODEL SELECTION FOR HYBRID12.",
    "NO HYBRID10 INTERNAL-TEST RE-EVALUATION OR RESULT-INFORMED TRAINING CHANGE.",
    "NO OOD REOPENING.",
    "NO SECOND HYBRID10 TRAINING OR CHECKPOINT CHANGE.",
    "NO DATASET, SPLIT, TEACHER, TOLERANCE OR LOSS-WEIGHT CHANGE.",
    "NO TEST-INFORMED EARLY STOPPING OR CHECKPOINT SELECTION.",
    "NO HISTORICAL HYBRID CHECKPOINT CLAIM.",
    "NO SGSim MODIFICATION.",
    "NO POLLOCK/TOF RECOMPUTATION.",
    "NO B4 RETRAINING.",
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
        if out.is_dir() and tree_hashes(stage) == tree_hashes(out):
            print("Existing identical output reused.", flush=True)
            return
        raise GateError("Existing output differs; nothing overwritten. Use a new revision directory.")
    out.parent.mkdir(parents=True, exist_ok=True)
    sibling = Path(tempfile.mkdtemp(prefix=".v16e6a-publish-", dir=out.parent))
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
    e5_dir = drive / E5_REL
    data_dir = drive / DATA_REL

    print("\nV16E-5 PRE-TRAINING AUTHORITY", flush=True)
    for label, (name, expected) in E5.items():
        bind(gates, "E5_" + label, e5_dir / name, expected)
    bind(gates, "E5_runner", project / E5_RUNNER[0], E5_RUNNER[1])

    manifest = read_json(e5_dir / E5["manifest"][0])
    results = read_json(e5_dir / E5["results"][0])
    summary = read_json(e5_dir / E5["summary"][0])

    gates.check("E5_milestone_exact", manifest.get("milestone") == "V16E-5")
    gates.check("E5_pretraining_protocol_frozen", summary.get("pretraining_protocol_frozen") is True)
    gates.check("E5_Hybrid12_recipe_frozen_execution_deferred",
                manifest.get("experiments", {}).get("Hybrid12", {}).get("execution_authorized_after_E5") is False)
    gates.check("E5_Hybrid12_dependency_exact", manifest["experiments"]["Hybrid12"].get("execution_requires") ==
                "successful V16E-6A Hybrid10 training/validation handoff; recipe itself is frozen here")
    gates.check("E5_Hybrid10_predecessor_authorized", results.get("Hybrid10_controlled_training_authorized") is True)
    gates.check("E5_internal_test_sealed", manifest.get("common_training_protocol", {}).get("sealed_evaluation", {}).get("internal_test", "").startswith("remains sealed"))
    gates.check("E5_OOD_closed", "unopened" in manifest.get("common_training_protocol", {}).get("sealed_evaluation", {}).get("OOD", ""))

    c = manifest["common_training_protocol"]
    exp = manifest["experiments"]["Hybrid12"]
    gates.check("framework_exact", c["framework"] == {
        "name": "TensorFlow", "version": "2.20.0", "api": "tf.keras", "float_policy": "float32",
        "mixed_precision": False, "jit_compile": False, "deterministic_ops_required": True,
    })
    gates.check("Hybrid12_run_id_exact", exp["training_run_id"] == "V16E6B-HYBRID12-R1")
    gates.check("Hybrid12_feature_order_exact", exp["feature_order"] == FEATURES12)
    gates.check("Hybrid12_param_dim_exact", exp["param_dim"] == 12)
    gates.check("Hybrid12_parameter_count_exact", exp["expected_trainable_parameters"] == 53057)
    gates.check("loss_weights_exact", c["loss"]["weights"] == {
        "lambda_data": 1.0, "lambda_bc": 5.0, "lambda_front": 2.0, "lambda_phys": 0.01, "lambda_mono": 0.1,
    })
    gates.check("optimizer_exact", c["optimizer"] == {
        "name": "Adam", "learning_rate": 0.001, "beta_1": 0.9, "beta_2": 0.999,
        "epsilon": 1e-7, "amsgrad": False, "clipnorm": 1.0,
    })
    gates.check("training_exact", c["training"] == {
        "batch_size_profiles": 256, "max_epochs": 250, "global_seed": 1605,
        "python_seed": 1605, "numpy_seed": 1605, "tensorflow_seed": 1605,
        "hyperparameter_search": False, "test_informed_tuning": False,
    })
    gates.check("normalization_none", c["data"]["normalization"] == "none; raw frozen conditioning; no statistics fitted")
    gates.check("internal_test_loader_forbidden", c["data"]["internal_test_loader_allowed_during_training"] is False)

    print("\nV16E-4-R1 ACCEPTED DATASET AUTHORITY", flush=True)
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

    return manifest, data_dir


def verify_hybrid10_predecessor(project: Path, drive: Path, gates: Gates):
    """Verify frozen Hybrid10 completion without using its held-out metrics for selection."""
    print("\nV16E-6A / V16E-6A-T PREDECESSOR AUTHORITY", flush=True)
    bind(gates, "E6A_runner", project / E6A_RUNNER[0], E6A_RUNNER[1])
    bind(gates, "E6AT_runner", project / E6AT_RUNNER[0], E6AT_RUNNER[1])
    for label, (name, expected) in E6A.items():
        bind(gates, "E6A_" + label, drive / E6A_REL / name, expected)
    for label, (name, expected) in E6AT.items():
        bind(gates, "E6AT_" + label, drive / E6AT_REL / name, expected)
    accepted = read_json(drive / E6A_REL / E6A["summary"][0])
    results = read_json(drive / E6AT_REL / E6AT["results"][0])
    final = read_json(drive / E6AT_REL / E6AT["summary"][0])
    gates.check("E6A_completed_validation_accepted",
                accepted.get("milestone") == "V16E-6A" and
                accepted.get("validation_all_gates_passed") is True and
                accepted.get("accepted_checkpoint_published") is True)
    gates.check("E6A_Hybrid12_dependency_claim", accepted.get("Hybrid12_training_authorized_by_E5_dependency") is True)
    gates.check("E6A_identity_unchanged", accepted.get("checkpoint_sha256") == E6A["checkpoint"][1])
    gates.check("E6AT_internal_test_frozen_once",
                results.get("milestone") == "V16E-6A-T" and
                results.get("evaluation_completed") is True and
                results.get("internal_test_evaluation_count_under_run_id") == 1 and
                final.get("internal_test_evaluation_count") == 1)
    gates.check("E6AT_no_test_informed_tuning",
                final.get("model_selection_performed") is False and
                final.get("checkpoint_changed") is False and
                final.get("OOD_evaluated") is False and
                results.get("model_selection_performed") is False and
                results.get("checkpoint_replaced") is False and
                results.get("training_performed") is False and
                results.get("test_acceptance_thresholds_claimed") is False and
                results.get("OOD_opened") is False)
    gates.check("E6AT_next_Hybrid12_authority",
                final.get("Hybrid12_training_authorized_next") is True and
                final.get("checkpoint_sha256") == E6A["checkpoint"][1] and
                results.get("E6A_checkpoint_sha256") == E6A["checkpoint"][1] and
                results.get("E5_manifest_sha256") == E5["manifest"][1] and
                results.get("E4_dataset_manifest_sha256") == E4["manifest"][1])
    lock = drive / E6AT_LOCK_REL / "V16E6AT_Internal_Test_Open_Lock.json"
    gates.check("E6AT_open_lock_exists", lock.is_file(), str(lock))
    gates.check("E6AT_lock_result_link", sha(lock) == results.get("internal_test_open_lock_sha256"))
    # Never open E6A-T test metrics or Hybrid12 partition code 2 in this function.


def load_partition_arrays(data_dir: Path, partition_code: int, gates: Gates):
    if partition_code not in (0, 1):
        raise GateError("Internal-test loading is forbidden in V16E-6B")
    codes = np.load(data_dir / "partition_codes.npy", allow_pickle=False)
    gates.check("partition_codes_shape_exact", codes.shape == (1000,))
    gates.check("partition_counts_exact", {i: int(np.sum(codes == i)) for i in (0, 1, 2)} == {0: 700, 1: 150, 2: 150})
    family_idx = np.flatnonzero(codes == partition_code)
    expected_families = 700 if partition_code == 0 else 150
    gates.check(("train" if partition_code == 0 else "validation") + "_family_count_exact", family_idx.size == expected_families)

    cond_mm = np.load(data_dir / "Hybrid12" / "conditioning.npy", mmap_mode="r", allow_pickle=False)
    target_mm = np.load(data_dir / "Hybrid12" / "Sw_fan_teacher.npy", mmap_mode="r", allow_pickle=False)
    if cond_mm.shape != (1000, 2, 8, 20, 12) or cond_mm.dtype != np.float32:
        raise GateError("Hybrid12 conditioning contract changed")
    if target_mm.shape != (1000, 8, 20, 201) or target_mm.dtype != np.float32:
        raise GateError("Hybrid12 target contract changed")

    # Only TRAIN/VALIDATION family pages are copied. Partition code 2 is never indexed.
    cond = np.asarray(cond_mm[family_idx], dtype=np.float32).reshape(-1, 12)
    base_target = np.asarray(target_mm[family_idx], dtype=np.float32)
    target = np.repeat(base_target[:, None, :, :, :], 2, axis=1).reshape(-1, 201)
    del cond_mm, target_mm, base_target

    expected_profiles = expected_families * 2 * 8 * 20
    gates.check(("train" if partition_code == 0 else "validation") + "_profile_count_exact",
                cond.shape == (expected_profiles, 12) and target.shape == (expected_profiles, 201))
    gates.check(("train" if partition_code == 0 else "validation") + "_finite", np.all(np.isfinite(cond)) and np.all(np.isfinite(target)))
    return cond, target


def prepare_tensorflow(manifest):
    # Determinism environment must be established before TensorFlow import.
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


def build_model_and_trainer(tf, manifest):
    c = manifest["common_training_protocol"]
    weights = c["loss"]["weights"]

    class Hybrid12Trainer(tf.keras.Model):
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
            self.track_objective = tf.keras.metrics.Mean(name="objective")
            self.track_sw = tf.keras.metrics.Mean(name="L_Sw")
            self.track_bc = tf.keras.metrics.Mean(name="L_BC")
            self.track_front = tf.keras.metrics.Mean(name="L_front")
            self.track_phys = tf.keras.metrics.Mean(name="L_phys")
            self.track_mono = tf.keras.metrics.Mean(name="L_mono")

        @property
        def metrics(self):
            return [self.track_objective, self.track_sw, self.track_bc, self.track_front, self.track_phys, self.track_mono]

        def call(self, inputs, training=False):
            xi, p = inputs
            pexp = self.repeat(p)
            x = self.concat([xi, pexp])
            x = self.lstm1(x, training=training)
            x = self.lstm2(x, training=training)
            z = self.head(x, training=training)
            swc = pexp[:, :, 2:3]
            sor = pexp[:, :, 3:4]
            span = 1.0 - swc - sor
            return swc + span * tf.math.sigmoid(z)

        def components(self, xi, p, y, pred):
            y = tf.cast(y, tf.float32)
            no = p[:, 0:1, None]
            nw = p[:, 1:2, None]
            swc = p[:, 2:3, None]
            sor = p[:, 3:4, None]
            mu_w = p[:, 4:5, None]
            mu_o = p[:, 5:6, None]
            krw_max = p[:, 7:8, None]
            kro_max = p[:, 8:9, None]
            tD = p[:, 9:10, None]
            xstar = p[:, 10:11, None]
            swstar = p[:, 11]
            span = 1.0 - swc - sor

            L_Sw = tf.reduce_mean(tf.square(pred - y))
            L_BC = tf.reduce_mean(tf.square(pred[:, 0, 0] - (1.0 - p[:, 3])))
            L_front = tf.reduce_mean(tf.square(pred[:, -1, 0] - swstar))

            s = tf.clip_by_value((pred - swc) / span, 0.0, 1.0)
            Aw = krw_max / mu_w
            Ao = kro_max / mu_o
            lw = Aw * tf.pow(s, nw)
            lo = Ao * tf.pow(1.0 - s, no)
            dlw = Aw * nw * tf.pow(s, nw - 1.0)
            dlo = -Ao * no * tf.pow(1.0 - s, no - 1.0)
            total = lw + lo
            dfds = (dlw * total - lw * (dlw + dlo)) / tf.maximum(tf.square(total), tf.constant(1e-24, tf.float32))
            fprime = dfds / span
            rhs = xi * (xstar / tD)
            L_phys = tf.reduce_mean(tf.square(fprime[:, 1:-1, :] - rhs[:, 1:-1, :]))
            increments = pred[:, 1:, :] - pred[:, :-1, :]
            L_mono = tf.reduce_mean(tf.square(tf.nn.relu(increments)))

            total_loss = (weights["lambda_data"] * L_Sw + weights["lambda_bc"] * L_BC +
                          weights["lambda_front"] * L_front + weights["lambda_phys"] * L_phys +
                          weights["lambda_mono"] * L_mono)
            return total_loss, L_Sw, L_BC, L_front, L_phys, L_mono

        def train_step(self, data):
            (xi, p), y = data
            with tf.GradientTape() as tape:
                pred = self([xi, p], training=True)
                vals = self.components(xi, p, y, pred)
            grads = tape.gradient(vals[0], self.trainable_variables)
            self.optimizer.apply_gradients(zip(grads, self.trainable_variables))
            for tracker, value in zip(self.metrics, vals):
                tracker.update_state(value)
            return {m.name: m.result() for m in self.metrics}

        def test_step(self, data):
            (xi, p), y = data
            pred = self([xi, p], training=False)
            vals = self.components(xi, p, y, pred)
            for tracker, value in zip(self.metrics, vals):
                tracker.update_state(value)
            return {m.name: m.result() for m in self.metrics}

    model = Hybrid12Trainer()
    opt_cfg = c["optimizer"]
    optimizer = tf.keras.optimizers.Adam(
        learning_rate=opt_cfg["learning_rate"], beta_1=opt_cfg["beta_1"], beta_2=opt_cfg["beta_2"],
        epsilon=opt_cfg["epsilon"], amsgrad=opt_cfg["amsgrad"], clipnorm=opt_cfg["clipnorm"])
    model.compile(optimizer=optimizer, run_eagerly=False, jit_compile=False)
    xi_dummy = tf.zeros((1, 201, 1), dtype=tf.float32)
    p_dummy = tf.zeros((1, 12), dtype=tf.float32)
    p_dummy = tf.tensor_scatter_nd_update(p_dummy, [[0,2],[0,3],[0,4],[0,5],[0,7],[0,8],[0,9]], [0.2,0.2,0.5,1.0,0.8,0.8,0.1])
    _ = model([xi_dummy, p_dummy], training=False)
    return model


def make_datasets(tf, train_cond, train_target, val_cond, val_target, xi, manifest):
    c = manifest["common_training_protocol"]
    batch = c["training"]["batch_size_profiles"]
    xi_tensor = tf.constant(xi[:, None].astype(np.float32))

    def attach_xi(p, y):
        return ((xi_tensor, p), tf.expand_dims(y, axis=-1))

    options = tf.data.Options()
    options.experimental_deterministic = True

    train = tf.data.Dataset.from_tensor_slices((train_cond, train_target))
    train = train.shuffle(train_cond.shape[0], seed=c["data"]["shuffle_seed"], reshuffle_each_iteration=True)
    train = train.map(attach_xi, num_parallel_calls=tf.data.AUTOTUNE, deterministic=True)
    train = train.batch(batch, drop_remainder=False).prefetch(tf.data.AUTOTUNE).with_options(options)

    val = tf.data.Dataset.from_tensor_slices((val_cond, val_target))
    val = val.map(attach_xi, num_parallel_calls=tf.data.AUTOTUNE, deterministic=True)
    val = val.batch(batch, drop_remainder=False).prefetch(tf.data.AUTOTUNE).with_options(options)
    return train, val


def make_callbacks(tf, manifest, best_path: Path, history_rows: list):
    c = manifest["common_training_protocol"]

    class FrozenSelector(tf.keras.callbacks.Callback):
        def __init__(self):
            super().__init__()
            self.best_tuple = None
            self.best_epoch = None
            self.best_logs = None

        def on_epoch_end(self, epoch, logs=None):
            logs = dict(logs or {})
            sw = float(logs.get("val_L_Sw", math.inf))
            obj = float(logs.get("val_objective", math.inf))
            if not (math.isfinite(sw) and math.isfinite(obj)):
                return
            key = (sw, obj, int(epoch))
            if self.best_tuple is None or key < self.best_tuple:
                self.best_tuple = key
                self.best_epoch = int(epoch) + 1
                self.best_logs = {k: float(v) for k, v in logs.items() if isinstance(v, (int, float, np.floating))}
                self.model.save_weights(best_path)

    class HistoryRecorder(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            row = {"epoch": int(epoch) + 1}
            for k, v in (logs or {}).items():
                try:
                    row[k] = float(v)
                except (TypeError, ValueError):
                    pass
            try:
                row["learning_rate"] = float(tf.keras.backend.get_value(self.model.optimizer.learning_rate))
            except Exception:
                pass
            history_rows.append(row)

    selector = FrozenSelector()
    schedule = c["schedule"]
    reducer = tf.keras.callbacks.ReduceLROnPlateau(
        monitor=schedule["monitor"], mode=schedule["mode"], factor=schedule["factor"],
        patience=schedule["patience_epochs"], min_delta=schedule["min_delta"],
        min_lr=schedule["min_learning_rate"], verbose=1)
    es = c["early_stopping"]
    stopper = tf.keras.callbacks.EarlyStopping(
        monitor=es["monitor"], mode=es["mode"], patience=es["patience_epochs"],
        min_delta=es["min_delta"], restore_best_weights=es["restore_best_weights"], verbose=1)
    recorder = HistoryRecorder()
    return [selector, reducer, stopper, recorder], selector


def numpy_fprime(sw, p):
    no = p[:, 0:1]
    nw = p[:, 1:2]
    swc = p[:, 2:3]
    sor = p[:, 3:4]
    mu_w = p[:, 4:5]
    mu_o = p[:, 5:6]
    krw_max = p[:, 7:8]
    kro_max = p[:, 8:9]
    span = 1.0 - swc - sor
    s = np.clip((sw - swc) / span, 0.0, 1.0)
    Aw = krw_max / mu_w
    Ao = kro_max / mu_o
    lw = Aw * np.power(s, nw)
    lo = Ao * np.power(1.0 - s, no)
    dlw = Aw * nw * np.power(s, nw - 1.0)
    dlo = -Ao * no * np.power(1.0 - s, no - 1.0)
    total = lw + lo
    return ((dlw * total - lw * (dlw + dlo)) / np.maximum(np.square(total), 1e-24)) / span


def validation_metrics(model, val_cond, val_target, xi, batch_size, acceptance):
    sums = {"sq": 0.0, "abs": 0.0, "bc_sq": 0.0, "front_sq": 0.0, "phys_sq": 0.0}
    counts = {"nodes": 0, "profiles": 0, "phys": 0, "mono": 0, "increments": 0, "nonfinite": 0}
    profile_rmse = []
    xi2 = xi[None, :]

    for start in range(0, val_cond.shape[0], batch_size):
        stop = min(start + batch_size, val_cond.shape[0])
        p = val_cond[start:stop]
        y = val_target[start:stop]
        xi_batch = np.broadcast_to(xi[None, :, None].astype(np.float32), (p.shape[0], 201, 1))
        pred = model([xi_batch, p], training=False).numpy()[:, :, 0].astype(np.float64)
        counts["nonfinite"] += int(np.size(pred) - np.count_nonzero(np.isfinite(pred)))
        if not np.all(np.isfinite(pred)):
            pred = np.nan_to_num(pred, nan=1e30, posinf=1e30, neginf=-1e30)
        y64 = y.astype(np.float64)
        diff = pred - y64
        sums["sq"] += float(np.sum(diff * diff))
        sums["abs"] += float(np.sum(np.abs(diff)))
        counts["nodes"] += int(diff.size)
        pr = np.sqrt(np.mean(diff * diff, axis=1))
        profile_rmse.append(pr)
        sums["bc_sq"] += float(np.sum(np.square(pred[:, 0] - (1.0 - p[:, 3]))))
        sums["front_sq"] += float(np.sum(np.square(pred[:, -1] - p[:, 11])))
        counts["profiles"] += int(p.shape[0])

        fp = numpy_fprime(pred, p.astype(np.float64))
        rhs = xi2 * (p[:, 10:11].astype(np.float64) / p[:, 9:10].astype(np.float64))
        r = fp[:, 1:-1] - rhs[:, 1:-1]
        sums["phys_sq"] += float(np.sum(r * r))
        counts["phys"] += int(r.size)
        inc = np.diff(pred, axis=1)
        counts["mono"] += int(np.count_nonzero(inc > 0.0))
        counts["increments"] += int(inc.size)

    profile_rmse = np.concatenate(profile_rmse)
    metrics = {
        "Sw_RMSE": math.sqrt(sums["sq"] / counts["nodes"]),
        "Sw_MAE": sums["abs"] / counts["nodes"],
        "profile_RMSE_p95": float(np.percentile(profile_rmse, 95.0)),
        "BC_RMSE": math.sqrt(sums["bc_sq"] / counts["profiles"]),
        "front_RMSE": math.sqrt(sums["front_sq"] / counts["profiles"]),
        "physics_characteristic_RMSE": math.sqrt(sums["phys_sq"] / counts["phys"]),
        "monotonic_violation_fraction": counts["mono"] / counts["increments"],
        "nonfinite_predictions": counts["nonfinite"],
        "validation_profiles": counts["profiles"],
    }
    gates = {
        "Sw_RMSE_max": metrics["Sw_RMSE"] <= acceptance["Sw_RMSE_max"],
        "Sw_MAE_max": metrics["Sw_MAE"] <= acceptance["Sw_MAE_max"],
        "profile_RMSE_p95_max": metrics["profile_RMSE_p95"] <= acceptance["profile_RMSE_p95_max"],
        "BC_RMSE_max": metrics["BC_RMSE"] <= acceptance["BC_RMSE_max"],
        "front_RMSE_max": metrics["front_RMSE"] <= acceptance["front_RMSE_max"],
        "physics_characteristic_RMSE_max": metrics["physics_characteristic_RMSE"] <= acceptance["physics_characteristic_RMSE_max"],
        "monotonic_violation_fraction_max": metrics["monotonic_violation_fraction"] <= acceptance["monotonic_violation_fraction_max"],
        "nonfinite_predictions_allowed": metrics["nonfinite_predictions"] <= acceptance["nonfinite_predictions_allowed"],
    }
    return metrics, gates


def runtime_info(tf):
    gpus = tf.config.list_physical_devices("GPU")
    return {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "tensorflow": tf.__version__,
        "physical_GPUs": [getattr(x, "name", str(x)) for x in gpus],
        "TF_DETERMINISTIC_OPS": os.environ.get("TF_DETERMINISTIC_OPS"),
        "float_policy": tf.keras.mixed_precision.global_policy().name,
    }


def blocked_output(drive: Path, parent_manifest, history_rows, val_metrics, val_gates, candidate_sha, selector, runinfo):
    report = {
        "milestone": MILESTONE, "revision": REVISION, "status": BLOCKED,
        "training_run_id": "V16E6B-HYBRID12-R1", "pretraining_manifest_sha256": E5["manifest"][1],
        "dataset_manifest_sha256": E4["manifest"][1], "training_performed": True,
        "accepted_checkpoint_published": False, "candidate_checkpoint_sha256": candidate_sha,
        "selected_epoch": selector.best_epoch, "selected_epoch_logs": selector.best_logs,
        "validation_metrics": val_metrics, "validation_gates": val_gates,
        "internal_test_loaded": False, "OOD_opened": False, "hyperparameter_search_performed": False,
        "runtime": runinfo, "history": history_rows, "next_milestone": NEXT_FAIL,
    }
    data = encoded(report)
    report_sha = digest(data)
    target = drive / BLOCKED_REL / report_sha[:16]
    with tempfile.TemporaryDirectory(prefix="v16e6a-blocked-") as tmp:
        stage = Path(tmp)
        (stage / "V16E6B_Blocked_Training_Validation_Report.json").write_bytes(data)
        summary = {
            "milestone": MILESTONE, "status": BLOCKED, "report_sha256": report_sha,
            "accepted_checkpoint_published": False, "training_performed": True,
            "internal_test_loaded": False, "next_milestone": NEXT_FAIL,
        }
        (stage / "PAD_Stream_V16E6B_Blocked_Summary.json").write_bytes(encoded(summary))
        handoff = f"""# PAD-Stream V16E-6B — BLOCKED Hybrid12 training/validation\n\nThe exact V16E-5 recipe was executed without hyperparameter search. TRAIN and\nVALIDATION only were loaded; INTERNAL TEST and OOD remained sealed. The selected\nvalidation checkpoint did not satisfy every frozen V16E-5 acceptance gate, so no\naccepted checkpoint was published. The candidate SHA is evidence only and is not\na deployable or historical checkpoint identity. Any changed training settings\nrequire a new prospective pre-training protocol before retraining.\n\nReport SHA: {report_sha}\nCandidate checkpoint SHA: {candidate_sha}\nNEXT: {NEXT_FAIL}\n"""
        (stage / "V16E6B_Blocked_Handoff.md").write_text(handoff, encoding="utf-8")
        publish_tree(stage, target)
    print("\n" + "=" * 118 + "\nV16E-6B RESULT: BLOCKED\n" + "=" * 118, flush=True)
    print("Training performed                         : YES", flush=True)
    print("Accepted checkpoint published             : NO", flush=True)
    print("Internal test / OOD opened                : NO / NO", flush=True)
    print("Blocked report:", target, flush=True)
    print("NEXT:", NEXT_FAIL, flush=True)
    return 2


def run(project: Path, drive: Path, out: Path):
    print("=" * 118 + "\nPAD-Stream V16E-6B\nProspective Hybrid12 Controlled Training and Validation\n" + "=" * 118, flush=True)
    print("\n".join(PROHIBITIONS), flush=True)
    if out.exists():
        raise GateError("This training-run output already exists; refusing to retrain under the frozen run ID")
    gates = Gates()
    manifest, data_dir = verify_authority(project, drive, gates)
    verify_hybrid10_predecessor(project, drive, gates)

    print("\nTRAIN / VALIDATION DATA FIREWALL", flush=True)
    train_cond, train_target = load_partition_arrays(data_dir, 0, gates)
    val_cond, val_target = load_partition_arrays(data_dir, 1, gates)
    xi = np.load(data_dir / "xi.npy", allow_pickle=False)
    gates.check("xi_exact", xi.shape == (201,) and np.array_equal(xi, np.arange(201, dtype=np.float64) / 200.0))
    gates.check("internal_test_not_loaded", True, "partition code 2 was never indexed")

    print("\nFROZEN TENSORFLOW RUNTIME / MODEL", flush=True)
    tf = prepare_tensorflow(manifest)
    gates.check("TensorFlow_2_20_exact", tf.__version__ == "2.20.0", tf.__version__)
    model = build_model_and_trainer(tf, manifest)
    trainable_count = int(sum(np.prod(v.shape) for v in model.trainable_variables))
    gates.check("trainable_parameter_count_exact", trainable_count == 53057, str(trainable_count))

    train_ds, val_ds = make_datasets(tf, train_cond, train_target, val_cond, val_target, xi, manifest)
    # tf.data has converted TRAIN arrays to tensors; release the large host copies.
    del train_cond, train_target
    import gc
    gc.collect()
    c = manifest["common_training_protocol"]
    history_rows = []

    with tempfile.TemporaryDirectory(prefix="v16e6a-training-") as tmp:
        tmp = Path(tmp)
        best_path = tmp / "V16E6B_Hybrid12_Selected.weights.h5"
        callbacks, selector = make_callbacks(tf, manifest, best_path, history_rows)

        print("\nCONTROLLED HYBRID12 TRAINING", flush=True)
        started = time.time()
        model.fit(
            train_ds, validation_data=val_ds, epochs=c["training"]["max_epochs"],
            callbacks=callbacks, verbose=2,
        )
        elapsed = time.time() - started
        gates.check("validation_selected_checkpoint_exists", best_path.is_file())
        gates.check("validation_selected_epoch_recorded", selector.best_epoch is not None)
        candidate_sha = sha(best_path)
        model.load_weights(best_path)

        print("\nFROZEN VALIDATION ACCEPTANCE", flush=True)
        val_metrics, val_gates = validation_metrics(
            model, val_cond, val_target, xi, c["training"]["batch_size_profiles"], c["validation_acceptance"])
        for name, passed in val_gates.items():
            detail = ""
            if name == "Sw_RMSE_max": detail = f"{val_metrics['Sw_RMSE']:.8g} <= {c['validation_acceptance']['Sw_RMSE_max']}"
            elif name == "Sw_MAE_max": detail = f"{val_metrics['Sw_MAE']:.8g} <= {c['validation_acceptance']['Sw_MAE_max']}"
            elif name == "profile_RMSE_p95_max": detail = f"{val_metrics['profile_RMSE_p95']:.8g} <= {c['validation_acceptance']['profile_RMSE_p95_max']}"
            elif name == "BC_RMSE_max": detail = f"{val_metrics['BC_RMSE']:.8g} <= {c['validation_acceptance']['BC_RMSE_max']}"
            elif name == "front_RMSE_max": detail = f"{val_metrics['front_RMSE']:.8g} <= {c['validation_acceptance']['front_RMSE_max']}"
            elif name == "physics_characteristic_RMSE_max": detail = f"{val_metrics['physics_characteristic_RMSE']:.8g} <= {c['validation_acceptance']['physics_characteristic_RMSE_max']}"
            elif name == "monotonic_violation_fraction_max": detail = f"{val_metrics['monotonic_violation_fraction']:.8g} <= {c['validation_acceptance']['monotonic_violation_fraction_max']}"
            elif name == "nonfinite_predictions_allowed": detail = f"{val_metrics['nonfinite_predictions']} <= 0"
            print(f"[{'PASS' if passed else 'FAIL'}] validation_{name}: {detail}", flush=True)

        runinfo = runtime_info(tf)
        runinfo["training_elapsed_seconds"] = elapsed
        all_validation_pass = all(val_gates.values())
        if not all_validation_pass:
            return blocked_output(drive, manifest, history_rows, val_metrics, val_gates,
                                  candidate_sha, selector, runinfo)

        print("\nPUBLISH ACCEPTED HYBRID12 CHECKPOINT", flush=True)
        with tempfile.TemporaryDirectory(prefix="v16e6a-accepted-") as stage_tmp:
            stage = Path(stage_tmp)
            weights_name = "V16E6B_Hybrid12_Accepted.weights.h5"
            shutil.copyfile(best_path, stage / weights_name)
            accepted_sha = sha(stage / weights_name)
            if accepted_sha != candidate_sha:
                raise GateError("Accepted checkpoint copy SHA differs from validation-selected candidate")
            history_payload = {
                "milestone": MILESTONE, "training_run_id": "V16E6B-HYBRID12-R1",
                "selected_epoch": selector.best_epoch, "selected_epoch_logs": selector.best_logs,
                "epochs_executed": len(history_rows), "history": history_rows,
                "selection_rule": c["checkpoint_selection"],
            }
            (stage / "V16E6B_Training_History.json").write_bytes(encoded(history_payload))
            validation_payload = {
                "milestone": MILESTONE, "partition": "validation", "profiles": int(val_cond.shape[0]),
                "metrics": val_metrics, "frozen_acceptance": c["validation_acceptance"],
                "gates": val_gates, "all_gates_passed": True,
                "internal_test_loaded": False, "OOD_opened": False,
            }
            (stage / "V16E6B_Validation_Metrics.json").write_bytes(encoded(validation_payload))
            model_cfg = {
                "experiment_id": manifest["experiments"]["Hybrid12"]["experiment_id"],
                "training_run_id": "V16E6B-HYBRID12-R1", "feature_order": FEATURES12,
                "architecture": c["architecture"], "framework": c["framework"], "optimizer": c["optimizer"],
                "loss": c["loss"], "training": c["training"], "schedule": c["schedule"],
                "early_stopping": c["early_stopping"], "trainable_parameters": trainable_count,
            }
            (stage / "V16E6B_Hybrid12_Model_Config.json").write_bytes(encoded(model_cfg))
            identity = {
                "milestone": MILESTONE, "revision": REVISION, "status": SUCCESS,
                "experiment_id": manifest["experiments"]["Hybrid12"]["experiment_id"],
                "training_run_id": "V16E6B-HYBRID12-R1", "checkpoint_filename": weights_name,
                "checkpoint_sha256": accepted_sha, "pretraining_manifest_sha256": E5["manifest"][1],
                "dataset_manifest_sha256": E4["manifest"][1], "R2_adapter_sha256": R2_ADAPTER_SHA,
                "selected_epoch": selector.best_epoch, "selected_epoch_logs": selector.best_logs,
                "validation_metrics": val_metrics, "validation_all_gates_passed": True,
                "internal_test_evaluated": False, "OOD_evaluated": False,
                "E6AT_parent_results_sha256": E6AT["results"][1],
                "E6A_parent_checkpoint_sha256": E6A["checkpoint"][1],
                "historical_checkpoint_claimed": False, "runtime": runinfo,
            }
            (stage / "V16E6B_Checkpoint_Identity.json").write_bytes(encoded(identity))
            summary = {
                "milestone": MILESTONE, "revision": REVISION, "status": SUCCESS,
                "training_performed": True, "accepted_checkpoint_published": True,
                "checkpoint_sha256": accepted_sha, "validation_all_gates_passed": True,
                "internal_test_evaluated": False, "OOD_evaluated": False,
                "E6AT_parent_results_sha256": E6AT["results"][1],
                "Hybrid10_checkpoint_unchanged": True,
                "next_milestone": NEXT_PASS,
            }
            (stage / "PAD_Stream_V16E6B_Summary.json").write_bytes(encoded(summary))
            handoff = f"""# PAD-Stream V16E-6B — Hybrid12 controlled training/validation PASS\n\nThe exact V16E-5 pre-training manifest was executed with no hyperparameter search.\nOnly TRAIN and VALIDATION families were loaded. One checkpoint was selected using\nVALIDATION only and passed every frozen V16E-5 validation acceptance gate. INTERNAL\nTEST and OOD remain sealed. This is a new V16E prospective checkpoint, not recovery\nof any historical Hybrid model.\n\nCheckpoint SHA: {accepted_sha}\nSelected epoch: {selector.best_epoch}\nValidation metrics SHA: {sha(stage / 'V16E6B_Validation_Metrics.json')}\nCheckpoint identity SHA: {sha(stage / 'V16E6B_Checkpoint_Identity.json')}\n\nNEXT: {NEXT_PASS}\n"""
            (stage / "V16E6B_Handoff.md").write_text(handoff, encoding="utf-8")
            publish_tree(stage, out)

    print("\n" + "=" * 118 + "\nV16E-6B RESULT: PASS\n" + "=" * 118, flush=True)
    print(f"{'Controlled Hybrid12 training performed':48}: YES", flush=True)
    print(f"{'Validation acceptance gates passed':48}: YES", flush=True)
    print(f"{'Accepted checkpoint published':48}: YES", flush=True)
    print(f"{'Internal test / OOD opened':48}: NO / NO", flush=True)
    print("Output:", out, flush=True)
    print("Checkpoint SHA:", sha(out / "V16E6B_Hybrid12_Accepted.weights.h5"), flush=True)
    print("Validation metrics SHA:", sha(out / "V16E6B_Validation_Metrics.json"), flush=True)
    print("Summary SHA:", sha(out / "PAD_Stream_V16E6B_Summary.json"), flush=True)
    print("Handoff SHA:", sha(out / "V16E6B_Handoff.md"), flush=True)
    print("NEXT:", NEXT_PASS, flush=True)
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
        print("\n[FAIL] V16E-6B did not close:", exc, file=sys.stderr, flush=True)
        print("No accepted checkpoint or internal-test authority was published by this invocation.", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
