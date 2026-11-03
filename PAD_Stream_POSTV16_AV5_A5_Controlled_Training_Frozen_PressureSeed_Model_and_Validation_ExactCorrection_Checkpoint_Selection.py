#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


M = "POSTV16-AV5-A5"
NAME = (
    "Controlled Training of Frozen A3 Pressure-Seed Model + "
    "Validation Exact-Correction Checkpoint Selection"
)

PASS = (
    "POSTV16AV5A5_FROZEN_PRESSURE_SEED_MODEL_CONTROLLED_TRAINING_"
    "VALIDATION_EXACT_CORRECTION_CHECKPOINT_SELECTION_PASS_LOCKED_OOD_UNOPENED"
)
BLOCK = "POSTV16AV5A5_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "2535347fdeff0ee5217076ee84f980fe23c9f239"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
BASE_AV5 = Path("post_v16") / RID / "POSTV16_AV5_Learned_Acceleration"
AV4_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"

GRID = (15, 50, 50)
CANONICAL_DAYS = np.asarray(
    [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0],
    dtype=np.float64,
)
INPUT_CHANNELS = [
    "log10_permeability_md",
    "log10_total_mobility",
    "previous_pressure_normalized",
    "injector_source_map",
    "producer_bhp_map",
    "normalized_depth_z",
]

FEATURE_WIDTH = 32
DILATION_SCHEDULE = [1, 2, 4, 8, 4, 2]
MAX_TRAINABLE_PARAMETERS = 500000
RANDOM_SEED = 260501
INITIAL_LR = 1.0e-3
BATCH_SIZE = 1
MAX_EPOCHS = 300
EARLY_STOPPING_PATIENCE = 30
EARLY_STOPPING_MIN_DELTA = 1.0e-6
REDUCE_LR_FACTOR = 0.5
REDUCE_LR_PATIENCE = 10
MIN_LR = 1.0e-6
HUBER_DELTA = 1.0
PRESSURE_GATE = 1.0e-8
FAILURE_ITERATION_PENALTY = 20001

# -------------------------------------------------------------------------------------------------
# Repository source authorities.
# -------------------------------------------------------------------------------------------------
A4_RUNNER = (
    "PAD_Stream_POSTV16_AV5_A4_Exact_Pressure_Teacher_Dataset_Generation_"
    "TRAIN_Only_Normalization_and_Locked_OOD_Predictor_Materialization.py"
)
A4_RUNNER_BLOB = "b4a12d9949953ec8aa3d99e1ea1d8bac90d4eaf7"
A3_RUNNER = "PAD_Stream_POSTV16_AV5_A3_TeacherDataset_Split_PressureSeed_Model_Objective_Design_Freeze.py"
A3_RUNNER_BLOB = "2232bced72acffdf3afbb0673ae11a12edc94e44"
A2R1_RUNNER = "PAD_Stream_POSTV16_AV5_A2_R1_AcceptedPressureSystem_ExactCorrection_WarmStart_Benchmark.py"
A2R1_RUNNER_BLOB = "d7009cc9b80b6d553c6d68d3ffcaf4ef22b74a67"
A6E_RUNNER = "PAD_Stream_POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution.py"
A6E_RUNNER_BLOB = "e3dcb0aa9354c399904f7f0e830b6a1fddd78987"
A2E_RUNNER = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_RUNNER_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
R3 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3_BLOB = "740c6da03e73906646bf0153633187e749449f31"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e949171541e4918c3"
PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    A4_RUNNER: A4_RUNNER_BLOB,
    A3_RUNNER: A3_RUNNER_BLOB,
    A2R1_RUNNER: A2R1_RUNNER_BLOB,
    A6E_RUNNER: A6E_RUNNER_BLOB,
    A2E_RUNNER: A2E_RUNNER_BLOB,
    R3: R3_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    PERM: PERM_BLOB,
}

# -------------------------------------------------------------------------------------------------
# A3 / A4 / A6E Drive authorities.
# -------------------------------------------------------------------------------------------------
A3_TOKEN = "POSTV16_AV5_A3"
A3_REL = BASE_AV5 / (
    A3_TOKEN + "_TeacherDataset_Split_PressureSeed_Model_Objective_Design_Freeze"
)
A3_SUMMARY = f"PAD_Stream_{A3_TOKEN}_Summary.json"
A3_MODEL = f"{A3_TOKEN}_Pressure_Seed_Model_Contract.json"
A3_OBJECTIVE = f"{A3_TOKEN}_Objective_Checkpoint_Selection_Contract.json"
A3_DECISION = f"{A3_TOKEN}_Decision_Contract.json"
A3_MANIFEST = f"{A3_TOKEN}_Artifact_Manifest.csv"
A3_STATUS = (
    "POSTV16AV5A3_TEACHER_DATASET_SPLIT_PRESSURE_SEED_MODEL_OBJECTIVE_"
    "DESIGN_FREEZE_PASS_NO_TEACHER_GENERATION_NO_TRAINING"
)

A4_TOKEN = "POSTV16_AV5_A4"
A4_REL = BASE_AV5 / (
    A4_TOKEN
    + "_Exact_Pressure_Teacher_Dataset_TRAIN_Only_Normalization_and_Locked_OOD_Predictor_Materialization"
)
A4_SUMMARY = f"PAD_Stream_{A4_TOKEN}_Summary.json"
A4_TRAINVAL = f"{A4_TOKEN}_TrainValidation_6Channel_PressureTeacher_Dataset.npz"
A4_NORMALIZATION = f"{A4_TOKEN}_TRAIN_Only_Normalization.npz"
A4_OOD_SCAFFOLD = f"{A4_TOKEN}_LockedOOD_6Channel_Predictor_Scaffold.npz"
A4_HANDOFF = f"{A4_TOKEN}_A5_Handoff_Contract.json"
A4_DECISION = f"{A4_TOKEN}_Decision_Contract.json"
A4_MANIFEST = f"{A4_TOKEN}_Artifact_Manifest.csv"
A4_STATUS = (
    "POSTV16AV5A4_EXACT_PRESSURE_TEACHER_DATASET_TRAIN_ONLY_NORMALIZATION_"
    "AND_LEAKAGE_SAFE_LOCKED_OOD_PREDICTOR_MATERIALIZATION_PASS_NO_TRAINING"
)

A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_SUMMARY = "PAD_Stream_POSTV16_AV3_A6_E_Summary.json"
A6E_MANIFEST = "POSTV16_AV3_A6_E_Artifact_Manifest.csv"
A6E_STATUS = (
    "AV3A6E_FROZEN_EPOCH92_CHECKPOINT_LOCAL_PORE_VOLUME_R7D_TERMINAL_HALO_"
    "INTEGRATION_ALL_4_REALIZATIONS_ALL_9_TIMES_PASS"
)
A6E_VAL_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"

OUT_TOKEN = "POSTV16_AV5_A5"
OUT_REL = BASE_AV5 / (
    OUT_TOKEN + "_Controlled_Training_and_Validation_ExactCorrection_Checkpoint_Selection"
)
BLOCK_REL = BASE_AV5 / (OUT_TOKEN + "_BLOCKED")

SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
CHECKPOINT = f"{OUT_TOKEN}_Best_Validation_Model.keras"
MODEL_CONTRACT = f"{OUT_TOKEN}_Frozen_Model_Architecture_and_Training_Contract.json"
EPOCH_AUDIT = f"{OUT_TOKEN}_Epochwise_Training_and_Validation_Selection_Audit.csv"
BASELINE_AUDIT = f"{OUT_TOKEN}_Validation_Temporal_Seed_Baseline_Audit.csv"
BEST_AUDIT = f"{OUT_TOKEN}_Best_Checkpoint_Validation_ExactCorrection_Audit.csv"
SELECTION = f"{OUT_TOKEN}_Best_Checkpoint_Selection.json"
A6_HANDOFF = f"{OUT_TOKEN}_A6_Handoff_Contract.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
GATE_MATRIX = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csvb(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        result[p.name] = row["sha256"]
    if not result:
        raise GateError(f"manifest_empty:{filename}")
    return result


def mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


def rel_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(np.linalg.norm((aa - bb).ravel()) / max(float(np.linalg.norm(bb.ravel())), 1.0e-30))


def set_determinism(tf: Any) -> None:
    os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")
    os.environ.setdefault("TF_CUDNN_DETERMINISTIC", "1")
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    tf.keras.utils.set_random_seed(RANDOM_SEED)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:
        pass


def build_model(tf: Any):
    layers = tf.keras.layers
    x_in = tf.keras.Input(shape=GRID + (6,), name="X6")
    x = layers.Conv3D(
        FEATURE_WIDTH, 3, padding="same", dilation_rate=1, activation=None, use_bias=True, name="stem_conv"
    )(x_in)
    x = layers.Activation(tf.nn.gelu, name="stem_gelu")(x)

    for block_index, d in enumerate(DILATION_SCHEDULE, start=1):
        residual = x
        y = layers.Conv3D(
            FEATURE_WIDTH, 3, padding="same", dilation_rate=d, use_bias=False,
            name=f"res{block_index}_conv1_d{d}",
        )(x)
        y = layers.LayerNormalization(axis=-1, epsilon=1.0e-5, name=f"res{block_index}_ln1")(y)
        y = layers.Activation(tf.nn.gelu, name=f"res{block_index}_gelu1")(y)
        y = layers.Conv3D(
            FEATURE_WIDTH, 3, padding="same", dilation_rate=d, use_bias=False,
            name=f"res{block_index}_conv2_d{d}",
        )(y)
        y = layers.LayerNormalization(axis=-1, epsilon=1.0e-5, name=f"res{block_index}_ln2")(y)
        x = layers.Add(name=f"res{block_index}_add")([residual, y])
        x = layers.Activation(tf.nn.gelu, name=f"res{block_index}_gelu2")(x)

    out = layers.Conv3D(1, 1, padding="same", activation="linear", name="delta_p_normalized")(x)
    return tf.keras.Model(x_in, out, name="AV5_A3_Frozen_3D_Residual_Dilated_PressureSeed")


def score_better(candidate: tuple[float, float, float], best: tuple[float, float, float] | None) -> bool:
    if best is None:
        return True
    cm, cmean, ch = candidate
    bm, bmean, bh = best
    if cm < bm:
        return True
    if cm > bm:
        return False
    if cmean < bmean:
        return True
    if cmean > bmean:
        return False
    return ch < (bh - EARLY_STOPPING_MIN_DELTA)


def selftest() -> None:
    assert GRID == (15, 50, 50)
    assert len(INPUT_CHANNELS) == 6
    assert DILATION_SCHEDULE == [1, 2, 4, 8, 4, 2]
    assert FEATURE_WIDTH == 32
    assert MAX_TRAINABLE_PARAMETERS == 500000
    assert RANDOM_SEED == 260501
    assert BATCH_SIZE == 1
    assert MAX_EPOCHS == 300
    assert EARLY_STOPPING_PATIENCE == 30
    assert REDUCE_LR_PATIENCE == 10
    assert HUBER_DELTA == 1.0
    assert score_better((1.0, 2.0, 10.0), (2.0, 1.0, 1.0))
    assert not score_better((2.0, 1.0, 1.0), (1.0, 2.0, 10.0))
    print("POSTV16 AV5-A5 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    import tensorflow as tf
    from scipy.sparse.linalg import spsolve

    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []
    training_started = False
    validation_inference_executed = False
    locked_ood_opened = False

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    try:
        print("=" * 206)
        print("POSTV16-AV5-A5 — FROZEN PRESSURE-SEED MODEL CONTROLLED TRAINING / VALIDATION EXACT-CORRECTION CHECKPOINT SELECTION")
        print("=" * 206)
        print("TRAIN optimizer updates: AV3CR0001/0002 only (18 full volumes).")
        print("VALIDATION checkpoint selection: AV3CR0003 only (9 full volumes).")
        print("LOCKED OOD AV3CR0004: not loaded, not inferred, not scored, not tuned.")
        print("Checkpoint hierarchy: validation median Krylov iterations -> mean iterations -> Huber loss.")
        print("Learned seed admission: exact residual improvement only; exact FV correction + direct fallback preserved.")
        print("NO AV4 STATE MUTATION. NO PHYSICAL TIME ADVANCE. NO PRODUCTION EXECUTION.")
        print()

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        branch = gt(root, "branch", "--show-current")
        parent = gt(root, "rev-parse", "HEAD^")
        clean = gt(root, "status", "--porcelain")
        gate("branch_exact", branch == BRANCH, branch)
        gate("parent_exact", parent == PARENT, parent)
        gate("repository_clean", clean == "", clean)
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "A3_contract_authority"
        a3d = drive / A3_REL
        a3m = manifest(a3d, A3_MANIFEST)
        a3s = js(a3d / A3_SUMMARY)
        a3model = js(a3d / A3_MODEL)
        a3obj = js(a3d / A3_OBJECTIVE)
        a3c = js(a3d / A3_DECISION)
        gate("A3_status_exact", a3s.get("status") == A3_STATUS, a3s.get("status"))
        gate("A3_AV4_state_SHA_exact", a3s.get("AV4_authoritative_state_sha256") == AV4_STATE_SHA)
        gate("A3_model_family_exact", a3model.get("architecture", {}).get("family") == "3D residual dilated convolutional network")
        gate("A3_feature_width_exact", int(a3model.get("architecture", {}).get("feature_width")) == FEATURE_WIDTH)
        gate("A3_dilation_schedule_exact", a3model.get("architecture", {}).get("dilation_schedule") == DILATION_SCHEDULE)
        gate("A3_input_channels_exact", a3model.get("input_channels") == INPUT_CHANNELS)
        gate("A3_parameter_budget_exact", int(a3model.get("parameter_budget", {}).get("maximum_trainable_parameters")) == MAX_TRAINABLE_PARAMETERS)
        opt = a3obj.get("optimizer", {})
        gate("A3_optimizer_Adam", opt.get("name") == "Adam")
        gate("A3_initial_lr_exact", float(opt.get("initial_learning_rate")) == INITIAL_LR)
        gate("A3_batch_size_exact", int(opt.get("batch_size_full_volumes")) == BATCH_SIZE)
        gate("A3_max_epochs_exact", int(opt.get("maximum_epochs")) == MAX_EPOCHS)
        gate("A3_early_stopping_patience_exact", int(opt.get("early_stopping_patience")) == EARLY_STOPPING_PATIENCE)
        gate("A3_early_stopping_min_delta_exact", float(opt.get("early_stopping_min_delta")) == EARLY_STOPPING_MIN_DELTA)
        gate("A3_reduce_lr_factor_exact", float(opt.get("reduce_lr_factor")) == REDUCE_LR_FACTOR)
        gate("A3_reduce_lr_patience_exact", int(opt.get("reduce_lr_patience")) == REDUCE_LR_PATIENCE)
        gate("A3_minimum_lr_exact", float(opt.get("minimum_learning_rate")) == MIN_LR)
        gate("A3_random_seed_exact", int(opt.get("random_seed")) == RANDOM_SEED)
        train_obj = a3obj.get("training_objective", {})
        gate("A3_Huber_primary_exact", train_obj.get("primary") == "Huber loss on TRAIN-normalized delta pressure")
        gate("A3_Huber_delta_exact", float(train_obj.get("huber_delta")) == HUBER_DELTA)
        sel = a3obj.get("checkpoint_selection", {})
        gate("A3_checkpoint_primary_exact", sel.get("primary") == "minimum VALIDATION median exact-correction Krylov iteration count")
        gate("A3_checkpoint_secondary_exact", sel.get("secondary") == "minimum VALIDATION mean exact-correction Krylov iteration count")
        gate("A3_checkpoint_tertiary_exact", sel.get("tertiary") == "minimum VALIDATION normalized delta-pressure Huber loss")
        gate("A3_manifest_nonempty", len(a3m) > 0)

        stage = "A4_dataset_authority"
        a4d = drive / A4_REL
        a4m = manifest(a4d, A4_MANIFEST)
        a4s = js(a4d / A4_SUMMARY)
        a4h = js(a4d / A4_HANDOFF)
        a4c = js(a4d / A4_DECISION)
        gate("A4_status_exact", a4s.get("status") == A4_STATUS, a4s.get("status"))
        gate("A4_AV4_state_SHA_exact", a4s.get("AV4_authoritative_state_sha256") == AV4_STATE_SHA)
        gate("A4_18_TRAIN_exact", int(a4s.get("TRAIN_exact_teacher_states")) == 18)
        gate("A4_9_VALIDATION_exact", int(a4s.get("VALIDATION_exact_teacher_states")) == 9)
        gate("A4_locked_OOD_targets_zero", a4s.get("LOCKED_OOD_canonical_pressure_targets_generated") is False)
        gate("A4_TRAIN_only_normalization_frozen", a4s.get("TRAIN_only_normalization_frozen") is True)
        gate("A4_A5_authorized", a4c.get("AV5_A5_authorized") is True and a4h.get("authorized") is True)
        gate("A4_A5_execution_authorized", a4c.get("AV5_A5_execution_authorized") is True and a4h.get("execution") is True)
        gate("A4_A5_bind_AV4_state_SHA", a4c.get("AV5_A5_must_bind_AV4_state_SHA") == AV4_STATE_SHA)
        gate("A4_A5_TRAIN_only_optimizer_updates", a4h.get("must_use_train_states_only_for_optimizer_updates") is True)
        gate("A4_A5_validation_only_checkpoint_selection", a4h.get("must_use_validation_only_for_checkpoint_selection") is True)
        gate("A4_A5_locked_OOD_firewall", a4c.get("AV5_A5_must_not_open_locked_OOD_pressure_truth_before_checkpoint_freeze") is True)
        gate("A4_A5_exact_residual_admission", a4c.get("AV5_A5_must_preserve_exact_residual_seed_admission") is True)
        gate("A4_A5_exact_FV_correction", a4c.get("AV5_A5_must_preserve_exact_FV_correction") is True)
        gate("A4_A5_direct_fallback", a4c.get("AV5_A5_must_preserve_direct_spsolve_fallback") is True)
        gate("A4_trainval_manifested", A4_TRAINVAL in a4m and (a4d / A4_TRAINVAL).is_file())
        gate("A4_normalization_manifested", A4_NORMALIZATION in a4m and (a4d / A4_NORMALIZATION).is_file())
        gate("A4_OOD_scaffold_manifested_but_not_opened", A4_OOD_SCAFFOLD in a4m and (a4d / A4_OOD_SCAFFOLD).is_file())

        # Intentionally never np.load() A4_OOD_SCAFFOLD in this milestone.
        locked_ood_opened = False

        with np.load(a4d / A4_TRAINVAL, allow_pickle=False) as z:
            X6 = np.asarray(z["X6"], dtype=np.float32)
            Y = np.asarray(z["Y_delta_p_normalized"], dtype=np.float32)
            p_prev_psi = np.asarray(z["previous_pressure_psi"], dtype=np.float64)
            p_star_psi = np.asarray(z["p_star_psi"], dtype=np.float64)
            realization_index = np.asarray(z["realization_index"], dtype=np.int64)
            time_index = np.asarray(z["time_index"], dtype=np.int64)
            target_day = np.asarray(z["target_day"], dtype=np.float64)
            partition_code = np.asarray(z["partition_code"], dtype=np.int8)
            channel_names = [str(x) for x in np.asarray(z["input_channel_names"]).tolist()]
            stored_av4_sha = str(np.asarray(z["AV4_authoritative_state_sha256"]).reshape(-1)[0])

        with np.load(a4d / A4_NORMALIZATION, allow_pickle=False) as z:
            delta_mean = float(np.asarray(z["delta_pressure_psi_mean"]).reshape(()))
            delta_std = float(np.asarray(z["delta_pressure_psi_std"]).reshape(()))
            fit_state_count = int(np.asarray(z["fit_state_count"]).reshape(()))
            fit_realization_indices = np.asarray(z["fit_realization_indices"], dtype=np.int64)

        gate("A4_X6_shape_exact", X6.shape == (27, 15, 50, 50, 6), X6.shape)
        gate("A4_Y_shape_exact", Y.shape == (27, 15, 50, 50, 1), Y.shape)
        gate("A4_dataset_finite", np.isfinite(X6).all() and np.isfinite(Y).all())
        gate("A4_channel_order_exact", channel_names == INPUT_CHANNELS, channel_names)
        gate("A4_dataset_AV4_SHA_exact", stored_av4_sha == AV4_STATE_SHA, stored_av4_sha)
        gate("A4_partition_counts_exact", int(np.sum(partition_code == 0)) == 18 and int(np.sum(partition_code == 1)) == 9)
        gate("A4_split_realization_exact", np.array_equal(np.unique(realization_index[partition_code == 0]), np.asarray([0, 1])) and np.array_equal(np.unique(realization_index[partition_code == 1]), np.asarray([2])))
        gate("A4_validation_days_exact", np.array_equal(target_day[partition_code == 1], CANONICAL_DAYS), target_day[partition_code == 1].tolist())
        gate("A4_TRAIN_normalization_fit_count_exact", fit_state_count == 18)
        gate("A4_TRAIN_normalization_realizations_exact", np.array_equal(fit_realization_indices, np.asarray([0, 1])))
        gate("A4_delta_normalization_finite_positive", np.isfinite(delta_mean) and np.isfinite(delta_std) and delta_std > 0.0, [delta_mean, delta_std])

        train_mask = partition_code == 0
        val_mask = partition_code == 1
        X_train, Y_train = X6[train_mask], Y[train_mask]
        X_val, Y_val = X6[val_mask], Y[val_mask]
        Pprev_val = p_prev_psi[val_mask]
        Pstar_val = p_star_psi[val_mask]
        val_time_index = time_index[val_mask]
        val_days = target_day[val_mask]

        stage = "validation_exact_pressure_system_binding"
        a6d = drive / A6E_REL
        a6m = manifest(a6d, A6E_MANIFEST)
        a6s = js(a6d / A6E_SUMMARY)
        gate("A6E_status_exact", a6s.get("status") == A6E_STATUS, a6s.get("status"))
        gate("A6E_validation_state_manifested", A6E_VAL_STATE in a6m and (a6d / A6E_VAL_STATE).is_file())
        with np.load(a6d / A6E_VAL_STATE, allow_pickle=False) as z:
            nw = np.asarray(z["nw"], dtype=np.float64)
            no = np.asarray(z["no"], dtype=np.float64)
            krw_max = np.asarray(z["krw_max"], dtype=np.float64)
            kro_max = np.asarray(z["kro_max"], dtype=np.float64)
            sat_all = np.asarray(z["grid_saturation"], dtype=np.float64)
            days_exact = np.asarray(z["target_days"], dtype=np.float64)

        gate("A6E_validation_days_exact", np.array_equal(days_exact, CANONICAL_DAYS))
        gate("A6E_validation_saturation_shape_exact", sat_all.shape == (9,) + GRID, sat_all.shape)

        sg2 = mod(root / SG2, "av5a5_sg2")
        sg3 = mod(root / SG3, "av5a5_sg3")
        r3 = mod(root / R3, "av5a5_r3")
        a2e = mod(root / A2E_RUNNER, "av5a5_a2e")
        a2r1 = mod(root / A2R1_RUNNER, "av5a5_a2r1")
        gate("A2R1_failure_iteration_penalty_exact", FAILURE_ITERATION_PENALTY == int(a2r1.MAX_KRYLOV_ITERATIONS) + 1, [FAILURE_ITERATION_PENALTY, int(a2r1.MAX_KRYLOV_ITERATIONS)])

        permeability = np.loadtxt(root / PERM, skiprows=1, dtype=np.float64).reshape(GRID, order="C")
        kx, ky, kz = sg2.build_directional_permeability(permeability)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)

        systems: list[dict[str, Any]] = []
        for it, day in enumerate(CANONICAL_DAYS.tolist()):
            mobility = a2e.spatial_mobility(sat_all[it], nw, no, krw_max, kro_max)
            tx, ty, tz, _ = r3.build_updated_transmissibilities(
                sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
            )
            A, b, _producer_wi = r3.assemble_updated_pressure_system(
                sg3, permeability, tx, ty, tz, mobility["lambda_total"]
            )
            audit = a2r1.matrix_audit(A)
            method = "cg" if audit["structural_SPD_candidate"] else "gmres"
            q = int(np.flatnonzero(val_time_index == it)[0])
            star_pa = Pstar_val[q].reshape(-1, order="C") * float(sg3.PSI_TO_PA)
            star_res = a2r1.lin_residual(A, star_pa, b)
            gate(f"validation_day{int(day)}_A4_teacher_reproduces_exact_system", star_res < PRESSURE_GATE, star_res)
            systems.append({
                "time_index": it,
                "day": float(day),
                "A": A,
                "b": np.asarray(b, dtype=np.float64),
                "method": method,
                "p_prev_pa": Pprev_val[q].reshape(-1, order="C") * float(sg3.PSI_TO_PA),
                "p_star_pa": star_pa,
            })

        def evaluate_predictions(pred_norm: np.ndarray, epoch: int | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
            nonlocal validation_inference_executed
            validation_inference_executed = True
            pred = np.asarray(pred_norm, dtype=np.float64)[..., 0]
            delta_pred_psi = pred * delta_std + delta_mean
            rows: list[dict[str, Any]] = []
            iterations_for_score: list[int] = []
            admitted_count = 0
            fallback_count = 0
            correction_success_count = 0

            for q, system in enumerate(systems):
                A = system["A"]
                b = system["b"]
                p_prev_pa = system["p_prev_pa"]
                p_star_pa = system["p_star_pa"]
                p_hat_psi = Pprev_val[q] + delta_pred_psi[q]
                p_hat_pa = p_hat_psi.reshape(-1, order="C") * float(sg3.PSI_TO_PA)

                r_hat = np.asarray(b - A @ p_hat_pa, dtype=np.float64)
                r_prev = np.asarray(b - A @ p_prev_pa, dtype=np.float64)
                hat_norm = float(np.linalg.norm(r_hat))
                prev_norm = float(np.linalg.norm(r_prev))
                admitted = bool(hat_norm < prev_norm)
                if admitted:
                    admitted_count += 1
                selected = p_hat_pa if admitted else p_prev_pa
                selected_label = "LEARNED" if admitted else "TEMPORAL"

                corr = a2r1.correction_solve(A, b, selected, system["method"])
                success = bool(corr["success"])
                if success:
                    correction_success_count += 1
                    iters = int(corr["iterations"])
                    corrected_pa = np.asarray(corr["pressure_pa"], dtype=np.float64)
                    final_rel = float(corr["final_relative_residual"])
                    fallback = False
                else:
                    fallback_count += 1
                    iters = FAILURE_ITERATION_PENALTY
                    corrected_pa = np.asarray(spsolve(A, b), dtype=np.float64)
                    final_rel = float(a2r1.lin_residual(A, corrected_pa, b))
                    fallback = True

                iterations_for_score.append(iters)
                rows.append({
                    "epoch": "" if epoch is None else int(epoch),
                    "time_index": int(system["time_index"]),
                    "target_day": float(system["day"]),
                    "method": system["method"],
                    "learned_seed_admitted": admitted,
                    "selected_seed": selected_label,
                    "learned_initial_residual_l2": hat_norm,
                    "temporal_initial_residual_l2": prev_norm,
                    "learned_to_temporal_residual_ratio": hat_norm / max(prev_norm, 1.0e-30),
                    "correction_success": success,
                    "correction_iterations_for_selection": iters,
                    "direct_spsolve_fallback_used": fallback,
                    "final_relative_residual": final_rel,
                    "corrected_pressure_relative_L2_vs_teacher": rel_l2(corrected_pa, p_star_pa),
                    "learned_seed_pressure_relative_L2_vs_teacher": rel_l2(p_hat_pa, p_star_pa),
                    "temporal_seed_pressure_relative_L2_vs_teacher": rel_l2(p_prev_pa, p_star_pa),
                })

            arr = np.asarray(iterations_for_score, dtype=np.float64)
            metrics = {
                "validation_median_exact_correction_iterations": float(np.median(arr)),
                "validation_mean_exact_correction_iterations": float(np.mean(arr)),
                "validation_max_exact_correction_iterations": int(np.max(arr)),
                "validation_learned_seed_admitted_states": int(admitted_count),
                "validation_correction_success_states": int(correction_success_count),
                "validation_direct_fallback_states": int(fallback_count),
            }
            return metrics, rows

        stage = "temporal_seed_baseline"
        baseline_rows: list[dict[str, Any]] = []
        baseline_iters: list[int] = []
        baseline_fallbacks = 0
        for system in systems:
            corr = a2r1.correction_solve(system["A"], system["b"], system["p_prev_pa"], system["method"])
            if corr["success"]:
                iters = int(corr["iterations"])
                final_rel = float(corr["final_relative_residual"])
                fallback = False
            else:
                iters = FAILURE_ITERATION_PENALTY
                p_direct = np.asarray(spsolve(system["A"], system["b"]), dtype=np.float64)
                final_rel = float(a2r1.lin_residual(system["A"], p_direct, system["b"]))
                fallback = True
                baseline_fallbacks += 1
            baseline_iters.append(iters)
            baseline_rows.append({
                "time_index": int(system["time_index"]),
                "target_day": float(system["day"]),
                "method": system["method"],
                "temporal_seed_correction_success": not fallback,
                "temporal_seed_correction_iterations": iters,
                "direct_spsolve_fallback_used": fallback,
                "final_relative_residual": final_rel,
            })
        baseline_median = float(np.median(np.asarray(baseline_iters, dtype=np.float64)))
        baseline_mean = float(np.mean(np.asarray(baseline_iters, dtype=np.float64)))
        gate("temporal_seed_baseline_all_final_residuals_pass", all(float(r["final_relative_residual"]) < PRESSURE_GATE for r in baseline_rows))

        stage = "model_construction"
        set_determinism(tf)
        model = build_model(tf)
        parameter_count = int(model.count_params())
        trainable_count = int(sum(int(np.prod(v.shape)) for v in model.trainable_weights))
        gate("model_parameter_count_exact_337793", parameter_count == 337793, parameter_count)
        gate("model_parameter_count_under_budget", parameter_count <= MAX_TRAINABLE_PARAMETERS, parameter_count)
        gate("model_trainable_parameter_count_under_budget", trainable_count <= MAX_TRAINABLE_PARAMETERS, trainable_count)
        gate("model_input_shape_exact", tuple(model.input_shape[1:]) == GRID + (6,), model.input_shape)
        gate("model_output_shape_exact", tuple(model.output_shape[1:]) == GRID + (1,), model.output_shape)

        optimizer = tf.keras.optimizers.Adam(learning_rate=INITIAL_LR)
        loss_fn = tf.keras.losses.Huber(delta=HUBER_DELTA)
        model.compile(optimizer=optimizer, loss=loss_fn)

        epoch_rows: list[dict[str, Any]] = []
        best_score: tuple[float, float, float] | None = None
        best_epoch: int | None = None
        best_weights: list[np.ndarray] | None = None
        best_metrics: dict[str, Any] | None = None
        best_state_rows: list[dict[str, Any]] | None = None
        bad_epochs = 0

        class ExactCorrectionSelectionCallback(tf.keras.callbacks.Callback):
            def on_epoch_end(self, epoch, logs=None):
                nonlocal best_score, best_epoch, best_weights, best_metrics, best_state_rows, bad_epochs
                logs = logs or {}
                pred = self.model(X_val, training=False).numpy()
                metrics, rows = evaluate_predictions(pred, epoch=epoch + 1)
                val_huber = float(logs.get("val_loss", np.nan))
                train_huber = float(logs.get("loss", np.nan))
                if not np.isfinite(val_huber) or not np.isfinite(train_huber):
                    raise GateError("nonfinite_training_or_validation_loss")
                score = (
                    float(metrics["validation_median_exact_correction_iterations"]),
                    float(metrics["validation_mean_exact_correction_iterations"]),
                    val_huber,
                )
                improved = score_better(score, best_score)
                if improved:
                    best_score = score
                    best_epoch = int(epoch + 1)
                    best_weights = [np.asarray(w).copy() for w in self.model.get_weights()]
                    best_metrics = dict(metrics)
                    best_state_rows = [dict(r) for r in rows]
                    bad_epochs = 0
                else:
                    bad_epochs += 1

                lr = float(tf.keras.backend.get_value(self.model.optimizer.learning_rate))
                epoch_rows.append({
                    "epoch": int(epoch + 1),
                    "train_normalized_Huber": train_huber,
                    "validation_normalized_Huber": val_huber,
                    "validation_median_exact_correction_iterations": metrics["validation_median_exact_correction_iterations"],
                    "validation_mean_exact_correction_iterations": metrics["validation_mean_exact_correction_iterations"],
                    "validation_max_exact_correction_iterations": metrics["validation_max_exact_correction_iterations"],
                    "validation_learned_seed_admitted_states": metrics["validation_learned_seed_admitted_states"],
                    "validation_correction_success_states": metrics["validation_correction_success_states"],
                    "validation_direct_fallback_states": metrics["validation_direct_fallback_states"],
                    "learning_rate": lr,
                    "selected_as_best_checkpoint": improved,
                    "checkpoint_selection_rank": "median_iterations>mean_iterations>Huber",
                    "epochs_since_checkpoint_improvement": int(bad_epochs),
                })
                print(
                    f"A5 epoch {epoch + 1:03d}: loss={train_huber:.8g} val={val_huber:.8g} "
                    f"median_iter={score[0]:.3f} mean_iter={score[1]:.3f} "
                    f"admitted={metrics['validation_learned_seed_admitted_states']}/9 "
                    f"fallback={metrics['validation_direct_fallback_states']} best={improved}"
                )
                if bad_epochs >= EARLY_STOPPING_PATIENCE:
                    print(f"A5 lexicographic early stop after {bad_epochs} epochs without checkpoint improvement.")
                    self.model.stop_training = True

        reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=REDUCE_LR_FACTOR,
            patience=REDUCE_LR_PATIENCE,
            min_lr=MIN_LR,
            mode="min",
            verbose=1,
        )

        stage = "controlled_training"
        training_started = True
        history = model.fit(
            X_train,
            Y_train,
            validation_data=(X_val, Y_val),
            batch_size=BATCH_SIZE,
            epochs=MAX_EPOCHS,
            shuffle=True,
            verbose=2,
            callbacks=[ExactCorrectionSelectionCallback(), reduce_lr],
        )
        epochs_completed = int(len(history.history.get("loss", [])))
        gate("training_completed_at_least_one_epoch", epochs_completed >= 1, epochs_completed)
        gate("best_checkpoint_selected", best_epoch is not None and best_weights is not None and best_metrics is not None and best_state_rows is not None, best_epoch)
        gate("best_epoch_within_completed_range", 1 <= int(best_epoch) <= epochs_completed, [best_epoch, epochs_completed])
        gate("epoch_audit_complete", len(epoch_rows) == epochs_completed, len(epoch_rows))

        stage = "best_checkpoint_freeze_and_reproduction"
        model.set_weights(best_weights)
        best_pred = model(X_val, training=False).numpy()
        final_metrics, final_rows = evaluate_predictions(best_pred, epoch=best_epoch)
        selected_epoch_row = next(r for r in epoch_rows if int(r["epoch"]) == int(best_epoch))
        gate(
            "best_checkpoint_metrics_reproduce_selection",
            abs(float(final_metrics["validation_median_exact_correction_iterations"]) - float(selected_epoch_row["validation_median_exact_correction_iterations"])) <= 1.0e-12
            and abs(float(final_metrics["validation_mean_exact_correction_iterations"]) - float(selected_epoch_row["validation_mean_exact_correction_iterations"])) <= 1.0e-12,
        )
        gate("best_checkpoint_all_corrected_final_residuals_pass", all(float(r["final_relative_residual"]) < PRESSURE_GATE for r in final_rows))
        gate("best_checkpoint_outputs_finite", np.isfinite(best_pred).all())
        gate("locked_OOD_never_opened", locked_ood_opened is False)
        gate("locked_OOD_inference_not_executed", True)
        gate("AV4_state_mutation_not_executed", True)
        gate("physical_time_advance_not_executed", True)

        with tempfile.TemporaryDirectory(prefix="av5a5_") as td:
            checkpoint_temp = Path(td) / CHECKPOINT
            model.save(checkpoint_temp)
            checkpoint_bytes = checkpoint_temp.read_bytes()

        checkpoint_sha = hashlib.sha256(checkpoint_bytes).hexdigest()
        gate("checkpoint_bytes_nonempty", len(checkpoint_bytes) > 0, len(checkpoint_bytes))

        stage = "publication"
        model_contract = {
            "milestone": M,
            "status": PASS,
            "source_design": "POSTV16-AV5-A3",
            "architecture": {
                "family": "3D residual dilated convolutional network",
                "input_shape": [15, 50, 50, 6],
                "input_channels": INPUT_CHANNELS,
                "feature_width": FEATURE_WIDTH,
                "dilation_schedule": DILATION_SCHEDULE,
                "residual_blocks": len(DILATION_SCHEDULE),
                "stem": "Conv3D(32,3,dilation=1,same)+GELU",
                "block": "Conv3D(no bias)->LayerNorm->GELU->Conv3D(no bias)->LayerNorm->residual add->GELU",
                "head": "Conv3D(1,1,same,linear)",
                "pooling": False,
                "upsampling": False,
                "parameter_count": parameter_count,
                "trainable_parameter_count": trainable_count,
                "maximum_trainable_parameters": MAX_TRAINABLE_PARAMETERS,
            },
            "training": {
                "TRAIN_realizations": ["AV3CR0001", "AV3CR0002"],
                "TRAIN_states": 18,
                "VALIDATION_realizations": ["AV3CR0003"],
                "VALIDATION_states": 9,
                "LOCKED_OOD_realizations": ["AV3CR0004"],
                "LOCKED_OOD_used": False,
                "optimizer": "Adam",
                "initial_learning_rate": INITIAL_LR,
                "batch_size_full_volumes": BATCH_SIZE,
                "maximum_epochs": MAX_EPOCHS,
                "epochs_completed": epochs_completed,
                "early_stopping_patience": EARLY_STOPPING_PATIENCE,
                "early_stopping_min_delta": EARLY_STOPPING_MIN_DELTA,
                "reduce_lr_factor": REDUCE_LR_FACTOR,
                "reduce_lr_patience": REDUCE_LR_PATIENCE,
                "minimum_learning_rate": MIN_LR,
                "random_seed": RANDOM_SEED,
                "loss": "Huber on TRAIN-normalized delta pressure",
                "huber_delta": HUBER_DELTA,
            },
            "checkpoint_selection": {
                "primary": "minimum VALIDATION median exact-correction Krylov iteration count",
                "secondary": "minimum VALIDATION mean exact-correction Krylov iteration count",
                "tertiary": "minimum VALIDATION normalized delta-pressure Huber loss",
                "learned_seed_admission": "||b-A*p_hat||_2 < ||b-A*p_previous||_2",
                "exact_correction": "A*delta=b-A*p_selected",
                "direct_spsolve_fallback": True,
                "failed_iterative_correction_selection_penalty_iterations": FAILURE_ITERATION_PENALTY,
                "wall_clock_used_for_selection": False,
            },
        }

        selection = {
            "milestone": M,
            "status": PASS,
            "best_epoch": int(best_epoch),
            "checkpoint_sha256": checkpoint_sha,
            "checkpoint_file": CHECKPOINT,
            "selection_tuple": {
                "validation_median_exact_correction_iterations": float(selected_epoch_row["validation_median_exact_correction_iterations"]),
                "validation_mean_exact_correction_iterations": float(selected_epoch_row["validation_mean_exact_correction_iterations"]),
                "validation_normalized_Huber": float(selected_epoch_row["validation_normalized_Huber"]),
            },
            "validation_learned_seed_admitted_states": int(final_metrics["validation_learned_seed_admitted_states"]),
            "validation_direct_fallback_states": int(final_metrics["validation_direct_fallback_states"]),
            "temporal_seed_baseline_median_iterations": baseline_median,
            "temporal_seed_baseline_mean_iterations": baseline_mean,
            "temporal_seed_baseline_fallback_states": baseline_fallbacks,
            "no_speedup_threshold_was_frozen": True,
            "checkpoint_selected_without_locked_OOD": True,
        }

        handoff = {
            "milestone": "POSTV16-AV5-A6",
            "name": "Frozen Checkpoint One-Touch Locked-OOD Sequential Pressure-Seed Evaluation",
            "authorized": True,
            "execution": True,
            "must_bind_checkpoint_sha256": checkpoint_sha,
            "must_use_A4_TRAIN_only_normalization": True,
            "must_not_retrain_reselect_or_retune": True,
            "locked_OOD_realization": "AV3CR0004",
            "locked_OOD_states": 9,
            "sequential_protocol": (
                "start Day30 from A4 stored exact background-state previous pressure; materialize Day30 X6; "
                "predict pressure seed; apply exact residual admission; perform exact FV correction with direct spsolve fallback/reference; "
                "only after checkpoint freeze open the exact Day30 OOD pressure reference for one-touch evaluation; "
                "carry the accepted exact corrected pressure forward as the previous-pressure input for Day60 and repeat sequentially through Day1000"
            ),
            "must_preserve_exact_residual_seed_admission": True,
            "must_preserve_exact_FV_correction": True,
            "must_preserve_direct_spsolve_fallback": True,
            "model_training_authorized": False,
            "checkpoint_reselection_authorized": False,
            "production_execution_authorized": False,
            "AV4_state_mutation_authorized": False,
            "P3_authorized": False,
        }

        classification = (
            "AV5_FROZEN_A3_PRESSURE_SEED_MODEL_TRAINED_ON_18_TRAIN_STATES_"
            "CHECKPOINT_SELECTED_ON_9_VALIDATION_STATES_BY_EXACT_CORRECTION_ITERATIONS_"
            "LOCKED_OOD_UNOPENED_A6_ONE_TOUCH_AUTHORIZED"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "AV4_authoritative_state_sha256": AV4_STATE_SHA,
            "TRAIN_states": 18,
            "VALIDATION_states": 9,
            "LOCKED_OOD_states": 9,
            "epochs_completed": epochs_completed,
            "best_epoch": int(best_epoch),
            "checkpoint_sha256": checkpoint_sha,
            "model_parameter_count": parameter_count,
            "validation_median_exact_correction_iterations": float(final_metrics["validation_median_exact_correction_iterations"]),
            "validation_mean_exact_correction_iterations": float(final_metrics["validation_mean_exact_correction_iterations"]),
            "validation_learned_seed_admitted_states": int(final_metrics["validation_learned_seed_admitted_states"]),
            "validation_direct_fallback_states": int(final_metrics["validation_direct_fallback_states"]),
            "temporal_seed_baseline_median_iterations": baseline_median,
            "temporal_seed_baseline_mean_iterations": baseline_mean,
            "model_training_executed": True,
            "validation_inference_executed": bool(validation_inference_executed),
            "locked_OOD_pressure_truth_opened": False,
            "locked_OOD_inference_executed": False,
            "AV4_state_mutated": False,
            "physical_time_advance_executed": False,
            "AV5_A6_authorized": True,
            "AV5_production_execution_authorized": False,
            "exact_FV_correction_required": True,
            "direct_spsolve_reference_and_fallback_required": True,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "checkpoint_frozen": True,
            "checkpoint_sha256": checkpoint_sha,
            "checkpoint_selected_without_locked_OOD": True,
            "AV5_A6_authorized": True,
            "AV5_A6_execution_authorized": True,
            "AV5_A6_must_bind_checkpoint_SHA": checkpoint_sha,
            "AV5_A6_must_use_A4_TRAIN_only_normalization": True,
            "AV5_A6_must_not_retrain_reselect_or_retune": True,
            "AV5_A6_locked_OOD_one_touch_authorized": True,
            "AV5_A6_must_preserve_exact_residual_seed_admission": True,
            "AV5_A6_must_preserve_exact_FV_correction": True,
            "AV5_A6_must_preserve_direct_spsolve_fallback": True,
            "AV5_model_training_authorized": False,
            "AV5_checkpoint_reselection_authorized": False,
            "AV5_production_execution_authorized": False,
            "AV4_state_mutation_authorized": False,
            "P3_authorized": False,
        }

        output_files = {
            SUMMARY: jb(summary),
            CHECKPOINT: checkpoint_bytes,
            MODEL_CONTRACT: jb(model_contract),
            EPOCH_AUDIT: csvb(epoch_rows),
            BASELINE_AUDIT: csvb(baseline_rows),
            BEST_AUDIT: csvb(final_rows),
            SELECTION: jb(selection),
            A6_HANDOFF: jb(handoff),
            DECISION: jb(decision),
            GATE_MATRIX: csvb(gates),
        }
        immutable_publish(out, output_files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                manifest_rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        immutable_publish(out, {MANIFEST: csvb(manifest_rows)})

        print()
        print("=" * 206)
        print(M, "PASS")
        print("Classification                                      :", classification)
        print("Epochs completed                                    :", epochs_completed)
        print("Best epoch                                          :", best_epoch)
        print("Checkpoint SHA256                                   :", checkpoint_sha)
        print("Model parameters                                    :", parameter_count)
        print("VALIDATION median exact-correction iterations       :", final_metrics["validation_median_exact_correction_iterations"])
        print("VALIDATION mean exact-correction iterations         :", final_metrics["validation_mean_exact_correction_iterations"])
        print("VALIDATION learned seed admitted states             :", final_metrics["validation_learned_seed_admitted_states"], "/ 9")
        print("VALIDATION direct fallback states                   :", final_metrics["validation_direct_fallback_states"])
        print("Temporal baseline median / mean iterations          :", baseline_median, "/", baseline_mean)
        print("LOCKED OOD truth opened / inference                 : False / False")
        print("AV5-A6 one-touch locked-OOD evaluation authorized   : True")
        print("Production execution / P3 authorized                : False / False")
        print("=" * 206)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "training_started": bool(training_started),
                "validation_inference_executed": bool(validation_inference_executed),
                "locked_OOD_opened": bool(locked_ood_opened),
                "locked_OOD_inference_executed": False,
                "AV4_state_mutation_executed": False,
                "physical_time_advance_executed": False,
                "AV5_A6_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
