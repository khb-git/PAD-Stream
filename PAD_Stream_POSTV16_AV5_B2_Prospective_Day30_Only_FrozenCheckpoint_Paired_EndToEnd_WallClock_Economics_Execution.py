#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np


M = "POSTV16-AV5-B2"
NAME = "Prospective Day30-Only Frozen-Checkpoint Dispatch + Paired End-to-End Wall-Clock Economics Execution"
PASS = (
    "POSTV16AV5B2_PROSPECTIVE_DAY30_ONLY_FROZEN_CHECKPOINT_PAIRED_END_TO_END_"
    "WALLCLOCK_ECONOMICS_EXECUTION_PASS_NO_TRAINING_NO_OOD_REUSE"
)
BLOCK = "POSTV16AV5B2_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "0d8ca28b2b229b071a80bc018c819396c4601c31"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
BASE_AV5 = Path("post_v16") / RID / "POSTV16_AV5_Learned_Acceleration"

AV4_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"
CHECKPOINT_SHA = "4cb41080b1d92780af21c9fae6e830a681d69315940656f1938db97c75dc52ef"
GRID = (15, 50, 50)
CANONICAL_DAYS = np.asarray(
    [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0],
    dtype=np.float64,
)
VALIDATION_REALIZATION = "AV3CR0003"
VALIDATION_REALIZATION_INDEX = 2
LOCKED_OOD_REALIZATION = "AV3CR0004"

TIMING_PAIRS = 11
WARMUP_PAIRS = 2
REQUIRED_FASTER_PAIRS = 9
PRESSURE_GATE = 1.0e-8
PRESSURE_EQUIV_GATE = 1.0e-8
EXPECTED_PARAMETER_COUNT = 337793

INPUT_CHANNELS = [
    "log10_permeability_md",
    "log10_total_mobility",
    "previous_pressure_normalized",
    "injector_source_map",
    "producer_bhp_map",
    "normalized_depth_z",
]

# -------------------------------------------------------------------------------------------------
# Exact repository authorities.
# -------------------------------------------------------------------------------------------------
B1 = "PAD_Stream_POSTV16_AV5_B1_Day30_ColdStart_Dispatch_WallClock_Economics_Prospective_Design_Freeze.py"
B1_BLOB = "15bc37231d32283fbcd1053619f4a833f349f40e"
A7 = "PAD_Stream_POSTV16_AV5_A7_Scientific_Outcome_Interpretation_and_Production_Decision_Freeze.py"
A7_BLOB = "3e39af491ed0c3f04c40958eb79571f43d4d6eb7"
A5R1 = (
    "PAD_Stream_POSTV16_AV5_A5_R1_SG3_Blob_Authority_Repair_Controlled_Training_and_"
    "Validation_ExactCorrection_Checkpoint_Selection.py"
)
A5R1_BLOB = "dd1bfd2d8a854d218fc220949bc8ca63d92c650b"
A4 = (
    "PAD_Stream_POSTV16_AV5_A4_Exact_Pressure_Teacher_Dataset_Generation_"
    "TRAIN_Only_Normalization_and_Locked_OOD_Predictor_Materialization.py"
)
A4_BLOB = "b4a12d9949953ec8aa3d99e1ea1d8bac90d4eaf7"
A2R1 = "PAD_Stream_POSTV16_AV5_A2_R1_AcceptedPressureSystem_ExactCorrection_WarmStart_Benchmark.py"
A2R1_BLOB = "d7009cc9b80b6d553c6d68d3ffcaf4ef22b74a67"
A6E = "PAD_Stream_POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution.py"
A6E_BLOB = "e3dcb0aa9354c399904f7f0e830b6a1fddd78987"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
R3 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3_BLOB = "740c6da03e73906646bf0153633187e749449f31"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    B1: B1_BLOB,
    A7: A7_BLOB,
    A5R1: A5R1_BLOB,
    A4: A4_BLOB,
    A2R1: A2R1_BLOB,
    A6E: A6E_BLOB,
    A2E: A2E_BLOB,
    R3: R3_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    PERM: PERM_BLOB,
}

# -------------------------------------------------------------------------------------------------
# Frozen Drive authorities.
# -------------------------------------------------------------------------------------------------
B1_TOKEN = "POSTV16_AV5_B1"
B1_REL = BASE_AV5 / (B1_TOKEN + "_Day30_ColdStart_Dispatch_WallClock_Economics_Prospective_Design_Freeze")
B1_SUMMARY = f"PAD_Stream_{B1_TOKEN}_Summary.json"
B1_DESIGN = f"{B1_TOKEN}_Day30_ColdStart_Dispatch_Design_Contract.json"
B1_TIMING = f"{B1_TOKEN}_EndToEnd_WallClock_Protocol.json"
B1_LEAKAGE = f"{B1_TOKEN}_Prospective_Leakage_and_Selection_Firewall.json"
B1_HANDOFF = f"{B1_TOKEN}_B2_Handoff_Contract.json"
B1_DECISION = f"{B1_TOKEN}_Decision_Contract.json"
B1_MANIFEST = f"{B1_TOKEN}_Artifact_Manifest.csv"
B1_STATUS = (
    "POSTV16AV5B1_DAY30_COLDSTART_DISPATCH_WALLCLOCK_ECONOMICS_PROSPECTIVE_"
    "ADMISSION_GATED_DESIGN_FREEZE_PASS_NO_MODEL_EXECUTION"
)
B1_CLASSIFICATION = (
    "AV5_DAY30_ONLY_FROZEN_CHECKPOINT_DISPATCH_AND_PAIRED_END_TO_END_WALLCLOCK_"
    "ECONOMICS_PROTOCOL_FROZEN_B2_EXECUTION_AUTHORIZED_NO_TRAINING_NO_OOD_REUSE"
)

A7_TOKEN = "POSTV16_AV5_A7"
A7_REL = BASE_AV5 / (A7_TOKEN + "_Scientific_Outcome_Interpretation_and_Production_Decision_Freeze")
A7_SUMMARY = f"PAD_Stream_{A7_TOKEN}_Summary.json"
A7_MANIFEST = f"{A7_TOKEN}_Artifact_Manifest.csv"

A5R1_TOKEN = "POSTV16_AV5_A5_R1"
A5R1_REL = BASE_AV5 / (
    A5R1_TOKEN
    + "_SG3_Blob_Authority_Repair_Controlled_Training_and_Validation_ExactCorrection_Checkpoint_Selection"
)
A5R1_SUMMARY = f"PAD_Stream_{A5R1_TOKEN}_Summary.json"
A5R1_CHECKPOINT = f"{A5R1_TOKEN}_Best_Validation_Model.keras"
A5R1_MANIFEST = f"{A5R1_TOKEN}_Artifact_Manifest.csv"

A4_TOKEN = "POSTV16_AV5_A4"
A4_REL = BASE_AV5 / (
    A4_TOKEN
    + "_Exact_Pressure_Teacher_Dataset_TRAIN_Only_Normalization_and_Locked_OOD_Predictor_Materialization"
)
A4_SUMMARY = f"PAD_Stream_{A4_TOKEN}_Summary.json"
A4_TRAINVAL = f"{A4_TOKEN}_TrainValidation_6Channel_PressureTeacher_Dataset.npz"
A4_NORMALIZATION = f"{A4_TOKEN}_TRAIN_Only_Normalization.npz"
A4_MANIFEST = f"{A4_TOKEN}_Artifact_Manifest.csv"

A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_SUMMARY = "PAD_Stream_POSTV16_AV3_A6_E_Summary.json"
A6E_MANIFEST = "POSTV16_AV3_A6_E_Artifact_Manifest.csv"
A6E_STATUS = (
    "AV3A6E_FROZEN_EPOCH92_CHECKPOINT_LOCAL_PORE_VOLUME_R7D_TERMINAL_HALO_"
    "INTEGRATION_ALL_4_REALIZATIONS_ALL_9_TIMES_PASS"
)
A6E_VAL_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"

OUT_TOKEN = "POSTV16_AV5_B2"
OUT_REL = BASE_AV5 / (
    OUT_TOKEN + "_Prospective_Day30_Only_FrozenCheckpoint_Paired_EndToEnd_WallClock_Economics_Execution"
)
BLOCK_REL = BASE_AV5 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
PAIR_AUDIT = f"{OUT_TOKEN}_Paired_WallClock_Audit.csv"
CORRECTNESS_AUDIT = f"{OUT_TOKEN}_Validation_Correctness_Audit.csv"
OUTCOME = f"{OUT_TOKEN}_WallClock_Economics_Outcome_Contract.json"
B3_HANDOFF = f"{OUT_TOKEN}_B3_Handoff_Contract.json"
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


def normalize(a: np.ndarray, mean: float, std: float) -> np.ndarray:
    return ((np.asarray(a, dtype=np.float64) - mean) / std).astype(np.float32)


def one_sided_sign_test_tail(faster_pairs: int, n: int) -> float:
    return float(sum(math.comb(n, k) for k in range(faster_pairs, n + 1)) / (2 ** n))


def selftest() -> None:
    assert GRID == (15, 50, 50)
    assert len(CANONICAL_DAYS) == 9
    assert VALIDATION_REALIZATION == "AV3CR0003"
    assert TIMING_PAIRS == 11
    assert WARMUP_PAIRS == 2
    assert REQUIRED_FASTER_PAIRS == 9
    assert one_sided_sign_test_tail(9, 11) < 0.05
    assert len(CHECKPOINT_SHA) == 64
    assert len(SG3_BLOB) == 40
    print("POSTV16 AV5-B2 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    import tensorflow as tf
    from scipy.sparse.linalg import spsolve

    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    model_inference_count = 0
    measured_candidate_trajectories = 0
    measured_baseline_trajectories = 0
    warmup_candidate_trajectories = 0
    warmup_baseline_trajectories = 0
    checkpoint_loaded = False
    locked_ood_loaded = False

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
        print("=" * 214)
        print("POSTV16-AV5-B2 — PROSPECTIVE DAY30-ONLY FROZEN-CHECKPOINT PAIRED END-TO-END WALL-CLOCK ECONOMICS EXECUTION")
        print("=" * 214)
        print("VALIDATION ONLY: AV3CR0003. LOCKED OOD AV3CR0004 IS NOT LOADED OR SCORED.")
        print("CANDIDATE: Day30 frozen learned inference + exact residual admission; Day60+ temporal-only.")
        print("BASELINE : temporal-seed exact correction at all 9 canonical states.")
        print("2 warm-up pairs, then exactly 11 measured pairs with alternating execution order.")
        print("NO TRAINING / NEW CHECKPOINT / RESELECTION / RETUNING / NORMALIZATION REFIT.")
        print("NO PRODUCTION OR P3 AUTHORIZATION FROM B2.")
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

        stage = "B1_design_and_handoff_authority"
        b1d = drive / B1_REL
        b1m = manifest(b1d, B1_MANIFEST)
        b1s = js(b1d / B1_SUMMARY)
        b1design = js(b1d / B1_DESIGN)
        b1timing = js(b1d / B1_TIMING)
        b1leak = js(b1d / B1_LEAKAGE)
        b1h = js(b1d / B1_HANDOFF)
        b1c = js(b1d / B1_DECISION)

        gate("B1_manifest_nonempty", len(b1m) > 0)
        gate("B1_status_exact", b1s.get("status") == B1_STATUS, b1s.get("status"))
        gate("B1_classification_exact", b1s.get("classification") == B1_CLASSIFICATION, b1s.get("classification"))
        gate("B1_AV4_state_SHA_exact", b1s.get("AV4_authoritative_state_sha256") == AV4_STATE_SHA)
        gate("B1_checkpoint_SHA_exact", b1s.get("checkpoint_sha256") == CHECKPOINT_SHA)
        gate("B1_Day30_dispatch_frozen", b1s.get("Day30_only_dispatch_frozen") is True)
        gate("B1_Day60plus_bypass_frozen", b1s.get("Day60_plus_model_inference_bypassed") is True)
        gate("B1_11_timing_pairs_exact", int(b1s.get("paired_timing_repeats")) == TIMING_PAIRS)
        gate("B1_2_warmup_pairs_exact", int(b1s.get("warmup_pairs")) == WARMUP_PAIRS)
        gate("B1_9_of_11_requirement_exact", int(b1s.get("required_candidate_faster_pairs")) == REQUIRED_FASTER_PAIRS)
        gate("B1_validation_realization_exact", b1s.get("B2_validation_realization") == VALIDATION_REALIZATION)
        gate("B1_B2_authorized", b1c.get("B2_authorized") is True and b1h.get("authorized") is True)
        gate("B1_B2_execution_authorized", b1c.get("B2_execution_authorized") is True and b1h.get("execution") is True)
        gate("B1_A7_commit_binding_exact", b1h.get("must_bind_A7_commit") == "4976b8a3e7e6c982dadf027768087102a5e5f148")
        gate("B1_checkpoint_binding_exact", b1h.get("must_bind_checkpoint_sha256") == CHECKPOINT_SHA)
        gate("B1_validation_only_exact", b1h.get("must_use_validation_realization") == VALIDATION_REALIZATION)
        gate("B1_no_OOD_selection", b1h.get("must_not_load_or_score_locked_OOD_for_selection") is True)
        gate("B1_no_training", b1h.get("must_not_train_model") is True)
        gate("B1_no_new_checkpoint", b1h.get("must_not_create_new_checkpoint") is True)
        gate("B1_no_reselect_retune", b1h.get("must_not_reselect_or_retune_checkpoint") is True)
        gate("B1_no_normalization_refit", b1h.get("must_not_refit_normalization") is True)
        gate("B1_exactly_11_pairs", b1h.get("must_execute_exactly_11_paired_timing_repeats") is True)
        gate("B1_exactly_2_warmups", b1h.get("must_execute_2_warmup_pairs") is True)
        gate("B1_alternate_order", b1h.get("must_alternate_pair_order") is True)
        gate("B1_exact_residual_admission", b1h.get("must_preserve_exact_residual_admission") is True)
        gate("B1_exact_FV_correction", b1h.get("must_preserve_exact_FV_correction") is True)
        gate("B1_direct_fallback_reference", b1h.get("must_preserve_direct_spsolve_fallback_and_reference") is True)
        gate("B1_no_production_or_P3", b1h.get("must_not_authorize_production_or_P3") is True)

        gate(
            "B1_dispatch_rule_exact",
            b1design.get("pre_inference_dispatch_gate", {}).get("rule")
            == "invoke frozen learned pressure-seed model iff target_day == 30.0; otherwise bypass learned inference",
        )
        gate(
            "B1_admission_rule_exact",
            b1design.get("Day30_post_inference_admission", {}).get("rule")
            == "admit learned seed iff ||b-A*p_hat||_2 < ||b-A*p_temporal||_2",
        )
        gate("B1_Day60plus_policy_exact", b1design.get("Day60_plus_policy") == "TEMPORAL_SEED_ONLY_NO_MODEL_INFERENCE")
        gate("B1_timing_timer_exact", b1timing.get("timer") == "time.perf_counter")
        gate("B1_timing_alternation_exact", b1timing.get("ordering") == "alternate candidate-first and baseline-first across paired repeats")
        gate("B1_candidate_inference_sync_exact", b1timing.get("model_inference_synchronization") == "materialize TensorFlow prediction to NumPy inside timed region")
        gate("B1_OOD_role_motivation_only", b1leak.get("A6_locked_OOD_role") == "RETROSPECTIVE_MOTIVATION_ONLY")
        gate("B1_OOD_not_wallclock_acceptance", b1leak.get("A6_locked_OOD_may_be_used_for_B2_wallclock_acceptance") is False)

        stage = "frozen_checkpoint_and_validation_data_authority"
        a5d = drive / A5R1_REL
        a5m = manifest(a5d, A5R1_MANIFEST)
        a5s = js(a5d / A5R1_SUMMARY)
        checkpoint = a5d / A5R1_CHECKPOINT
        gate("A5R1_manifest_nonempty", len(a5m) > 0)
        gate("A5R1_checkpoint_manifested", A5R1_CHECKPOINT in a5m and checkpoint.is_file())
        gate("A5R1_checkpoint_file_SHA_exact", checkpoint.is_file() and sha(checkpoint) == CHECKPOINT_SHA, sha(checkpoint) if checkpoint.is_file() else "missing")
        gate("A5R1_checkpoint_summary_SHA_exact", a5s.get("checkpoint_sha256") == CHECKPOINT_SHA)

        a4d = drive / A4_REL
        a4m = manifest(a4d, A4_MANIFEST)
        a4s = js(a4d / A4_SUMMARY)
        gate("A4_manifest_nonempty", len(a4m) > 0)
        gate("A4_trainval_manifested", A4_TRAINVAL in a4m and (a4d / A4_TRAINVAL).is_file())
        gate("A4_normalization_manifested", A4_NORMALIZATION in a4m and (a4d / A4_NORMALIZATION).is_file())
        gate("A4_locked_OOD_targets_zero", a4s.get("LOCKED_OOD_canonical_pressure_targets_generated") is False)
        gate("A4_TRAIN_only_normalization_frozen", a4s.get("TRAIN_only_normalization_frozen") is True)

        with np.load(a4d / A4_TRAINVAL, allow_pickle=False) as z:
            X6 = np.asarray(z["X6"], dtype=np.float32)
            Pprev = np.asarray(z["previous_pressure_psi"], dtype=np.float64)
            realization_index = np.asarray(z["realization_index"], dtype=np.int64)
            time_index = np.asarray(z["time_index"], dtype=np.int64)
            target_day = np.asarray(z["target_day"], dtype=np.float64)
            partition_code = np.asarray(z["partition_code"], dtype=np.int8)
            channel_names = [str(x) for x in np.asarray(z["input_channel_names"]).tolist()]
            stored_av4_sha = str(np.asarray(z["AV4_authoritative_state_sha256"]).reshape(-1)[0])

        with np.load(a4d / A4_NORMALIZATION, allow_pickle=False) as z:
            prev_mean = float(np.asarray(z["previous_pressure_psi_mean"]).reshape(()))
            prev_std = float(np.asarray(z["previous_pressure_psi_std"]).reshape(()))
            delta_mean = float(np.asarray(z["delta_pressure_psi_mean"]).reshape(()))
            delta_std = float(np.asarray(z["delta_pressure_psi_std"]).reshape(()))
            fit_state_count = int(np.asarray(z["fit_state_count"]).reshape(()))
            fit_realization_indices = np.asarray(z["fit_realization_indices"], dtype=np.int64)

        gate("A4_dataset_shapes_exact", X6.shape == (27, 15, 50, 50, 6) and Pprev.shape == (27, 15, 50, 50))
        gate("A4_channel_order_exact", channel_names == INPUT_CHANNELS, channel_names)
        gate("A4_dataset_AV4_SHA_exact", stored_av4_sha == AV4_STATE_SHA)
        gate("A4_TRAIN_normalization_exact", fit_state_count == 18 and np.array_equal(fit_realization_indices, np.asarray([0, 1])))
        gate("A4_delta_normalization_valid", np.isfinite(delta_mean) and np.isfinite(delta_std) and delta_std > 0.0)
        gate("A4_previous_normalization_valid", np.isfinite(prev_mean) and np.isfinite(prev_std) and prev_std > 0.0)

        val_mask = (
            (partition_code == 1)
            & (realization_index == VALIDATION_REALIZATION_INDEX)
        )
        gate("A4_validation_state_count_9", int(np.sum(val_mask)) == 9, int(np.sum(val_mask)))
        val_indices = np.flatnonzero(val_mask)
        order = np.argsort(time_index[val_indices])
        val_indices = val_indices[order]
        gate("A4_validation_days_exact", np.array_equal(target_day[val_indices], CANONICAL_DAYS), target_day[val_indices].tolist())
        day30_idx = int(val_indices[0])
        X_day30 = np.asarray(X6[day30_idx], dtype=np.float32).copy()
        A4_background_psi = np.asarray(Pprev[day30_idx], dtype=np.float64)

        # The locked-OOD scaffold/output is intentionally never opened in B2.
        locked_ood_loaded = False

        stage = "validation_physical_state_and_system_binding"
        a6d = drive / A6E_REL
        a6m = manifest(a6d, A6E_MANIFEST)
        a6s = js(a6d / A6E_SUMMARY)
        val_state = a6d / A6E_VAL_STATE
        gate("A6E_status_exact", a6s.get("status") == A6E_STATUS, a6s.get("status"))
        gate("A6E_validation_state_manifested", A6E_VAL_STATE in a6m and val_state.is_file())

        with np.load(val_state, allow_pickle=False) as z:
            nw = np.asarray(z["nw"], dtype=np.float64)
            no = np.asarray(z["no"], dtype=np.float64)
            krw_max = np.asarray(z["krw_max"], dtype=np.float64)
            kro_max = np.asarray(z["kro_max"], dtype=np.float64)
            sat_all = np.asarray(z["grid_saturation"], dtype=np.float64)
            days_exact = np.asarray(z["target_days"], dtype=np.float64)

        gate("A6E_validation_field_shapes_exact", all(a.shape == GRID for a in [nw, no, krw_max, kro_max]))
        gate("A6E_validation_saturation_shape_exact", sat_all.shape == (9,) + GRID, sat_all.shape)
        gate("A6E_validation_days_exact", np.array_equal(days_exact, CANONICAL_DAYS))

        sg2 = mod(root / SG2, "av5b2_sg2")
        sg3 = mod(root / SG3, "av5b2_sg3")
        r3 = mod(root / R3, "av5b2_r3")
        a2e = mod(root / A2E, "av5b2_a2e")
        a2r1 = mod(root / A2R1, "av5b2_a2r1")

        permeability = np.loadtxt(root / PERM, skiprows=1, dtype=np.float64).reshape(GRID, order="C")
        gate("permeability_valid", permeability.shape == GRID and np.isfinite(permeability).all() and np.all(permeability > 0.0))
        kx, ky, kz = sg2.build_directional_permeability(permeability)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)

        background_sat = np.full(GRID, 0.20, dtype=np.float64)
        bg_mob = a2e.spatial_mobility(background_sat, nw, no, krw_max, kro_max)
        bg_tx, bg_ty, bg_tz, _ = r3.build_updated_transmissibilities(
            sg3, tx_ref, ty_ref, tz_ref, bg_mob["lambda_total"]
        )
        bg_A, bg_b, _ = r3.assemble_updated_pressure_system(
            sg3, permeability, bg_tx, bg_ty, bg_tz, bg_mob["lambda_total"]
        )
        from scipy.sparse.linalg import spsolve
        background_pa = np.asarray(spsolve(bg_A, bg_b), dtype=np.float64)
        background_rel = float(a2r1.lin_residual(bg_A, background_pa, bg_b))
        background_psi = (background_pa * float(sg3.PA_TO_PSI)).reshape(GRID, order="C")
        gate("validation_background_exact_residual", background_rel < PRESSURE_GATE, background_rel)
        gate("validation_background_matches_A4_previous_pressure", rel_l2(background_psi, A4_background_psi) <= 1.0e-10, rel_l2(background_psi, A4_background_psi))
        reconstructed_prev_norm = normalize(background_psi, prev_mean, prev_std)
        gate(
            "validation_Day30_previous_channel_matches_A4",
            np.allclose(reconstructed_prev_norm, X_day30[..., 2], rtol=0.0, atol=2.0e-6),
            float(np.max(np.abs(reconstructed_prev_norm - X_day30[..., 2]))),
        )

        systems: list[dict[str, Any]] = []
        for it, day in enumerate(CANONICAL_DAYS.tolist()):
            mob = a2e.spatial_mobility(sat_all[it], nw, no, krw_max, kro_max)
            tx, ty, tz, _ = r3.build_updated_transmissibilities(
                sg3, tx_ref, ty_ref, tz_ref, mob["lambda_total"]
            )
            A, b, _ = r3.assemble_updated_pressure_system(
                sg3, permeability, tx, ty, tz, mob["lambda_total"]
            )
            audit = a2r1.matrix_audit(A)
            method = "cg" if audit["structural_SPD_candidate"] else "gmres"
            systems.append({
                "time_index": int(it),
                "day": float(day),
                "A": A,
                "b": np.asarray(b, dtype=np.float64),
                "method": method,
            })
        gate("nine_validation_systems_bound", len(systems) == 9)

        stage = "frozen_checkpoint_load"
        model = tf.keras.models.load_model(checkpoint, compile=False)
        checkpoint_loaded = True
        gate("checkpoint_parameter_count_exact", int(model.count_params()) == EXPECTED_PARAMETER_COUNT, int(model.count_params()))
        gate("checkpoint_input_shape_exact", tuple(model.input_shape[1:]) == GRID + (6,), model.input_shape)
        gate("checkpoint_output_shape_exact", tuple(model.output_shape[1:]) == GRID + (1,), model.output_shape)
        gpu_devices = tf.config.list_physical_devices("GPU")
        device_description = gpu_devices[0].name if gpu_devices else "NO_GPU"

        failure_penalty = int(a2r1.MAX_KRYLOV_ITERATIONS) + 1

        def exact_correction(A, b, seed_pa, method):
            corr = a2r1.correction_solve(A, b, seed_pa, method)
            if bool(corr["success"]):
                return {
                    "pressure_pa": np.asarray(corr["pressure_pa"], dtype=np.float64),
                    "iterations": int(corr["iterations"]),
                    "fallback": False,
                    "final_relative_residual": float(corr["final_relative_residual"]),
                }
            direct = np.asarray(spsolve(A, b), dtype=np.float64)
            return {
                "pressure_pa": direct,
                "iterations": failure_penalty,
                "fallback": True,
                "final_relative_residual": float(a2r1.lin_residual(A, direct, b)),
            }

        def run_candidate() -> tuple[float, list[dict[str, Any]]]:
            nonlocal model_inference_count
            previous_psi = background_psi.copy()
            rows: list[dict[str, Any]] = []
            t0 = time.perf_counter()
            for it, system in enumerate(systems):
                A = system["A"]
                b = system["b"]
                p_prev_pa = previous_psi.reshape(-1, order="C") * float(sg3.PSI_TO_PA)
                admitted = False
                selected_label = "TEMPORAL"
                learned_residual_l2 = float("nan")
                temporal_residual_l2 = float(np.linalg.norm(np.asarray(b - A @ p_prev_pa, dtype=np.float64)))
                if it == 0:
                    pred_norm = np.asarray(model(X_day30[None, ...], training=False).numpy(), dtype=np.float64)[0, ..., 0]
                    model_inference_count += 1
                    if not np.isfinite(pred_norm).all():
                        raise GateError("candidate_Day30_prediction_nonfinite")
                    delta_pred_psi = pred_norm * delta_std + delta_mean
                    p_hat_psi = previous_psi + delta_pred_psi
                    p_hat_pa = p_hat_psi.reshape(-1, order="C") * float(sg3.PSI_TO_PA)
                    learned_residual_l2 = float(np.linalg.norm(np.asarray(b - A @ p_hat_pa, dtype=np.float64)))
                    admitted = bool(learned_residual_l2 < temporal_residual_l2)
                    selected_seed = p_hat_pa if admitted else p_prev_pa
                    selected_label = "LEARNED" if admitted else "TEMPORAL"
                else:
                    selected_seed = p_prev_pa

                corr = exact_correction(A, b, selected_seed, system["method"])
                previous_psi = (corr["pressure_pa"] * float(sg3.PA_TO_PSI)).reshape(GRID, order="C")
                rows.append({
                    "time_index": int(system["time_index"]),
                    "target_day": float(system["day"]),
                    "selected_seed": selected_label,
                    "learned_seed_admitted": admitted,
                    "learned_initial_residual_l2": learned_residual_l2,
                    "temporal_initial_residual_l2": temporal_residual_l2,
                    "correction_iterations": int(corr["iterations"]),
                    "direct_fallback_used": bool(corr["fallback"]),
                    "final_relative_residual": float(corr["final_relative_residual"]),
                    "pressure_pa": corr["pressure_pa"],
                })
            elapsed = time.perf_counter() - t0
            return float(elapsed), rows

        def run_baseline() -> tuple[float, list[dict[str, Any]]]:
            previous_psi = background_psi.copy()
            rows: list[dict[str, Any]] = []
            t0 = time.perf_counter()
            for system in systems:
                A = system["A"]
                b = system["b"]
                p_prev_pa = previous_psi.reshape(-1, order="C") * float(sg3.PSI_TO_PA)
                temporal_residual_l2 = float(np.linalg.norm(np.asarray(b - A @ p_prev_pa, dtype=np.float64)))
                corr = exact_correction(A, b, p_prev_pa, system["method"])
                previous_psi = (corr["pressure_pa"] * float(sg3.PA_TO_PSI)).reshape(GRID, order="C")
                rows.append({
                    "time_index": int(system["time_index"]),
                    "target_day": float(system["day"]),
                    "selected_seed": "TEMPORAL",
                    "learned_seed_admitted": False,
                    "temporal_initial_residual_l2": temporal_residual_l2,
                    "correction_iterations": int(corr["iterations"]),
                    "direct_fallback_used": bool(corr["fallback"]),
                    "final_relative_residual": float(corr["final_relative_residual"]),
                    "pressure_pa": corr["pressure_pa"],
                })
            elapsed = time.perf_counter() - t0
            return float(elapsed), rows

        stage = "warmup_and_correctness"
        warmup_records = []
        correctness_rows: list[dict[str, Any]] = []
        first_candidate_rows = None
        first_baseline_rows = None

        for wp in range(1, WARMUP_PAIRS + 1):
            candidate_first = bool(wp % 2 == 1)
            if candidate_first:
                ctime, crows = run_candidate()
                warmup_candidate_trajectories += 1
                btime, brows = run_baseline()
                warmup_baseline_trajectories += 1
            else:
                btime, brows = run_baseline()
                warmup_baseline_trajectories += 1
                ctime, crows = run_candidate()
                warmup_candidate_trajectories += 1
            warmup_records.append({
                "warmup_pair": wp,
                "order": "CANDIDATE_FIRST" if candidate_first else "BASELINE_FIRST",
                "candidate_seconds": ctime,
                "baseline_seconds": btime,
            })
            if wp == 1:
                first_candidate_rows = crows
                first_baseline_rows = brows

        gate("exactly_2_candidate_warmup_trajectories", warmup_candidate_trajectories == WARMUP_PAIRS, warmup_candidate_trajectories)
        gate("exactly_2_baseline_warmup_trajectories", warmup_baseline_trajectories == WARMUP_PAIRS, warmup_baseline_trajectories)
        gate("warmup_pair_order_alternated", [r["order"] for r in warmup_records] == ["CANDIDATE_FIRST", "BASELINE_FIRST"])

        if first_candidate_rows is None or first_baseline_rows is None:
            raise GateError("missing_warmup_correctness_rows")

        candidate_day30_admitted = bool(first_candidate_rows[0]["learned_seed_admitted"])
        candidate_day30_seed = str(first_candidate_rows[0]["selected_seed"])
        candidate_fallbacks_correctness = 0
        baseline_fallbacks_correctness = 0

        for it, system in enumerate(systems):
            direct_pa = np.asarray(spsolve(system["A"], system["b"]), dtype=np.float64)
            direct_rel = float(a2r1.lin_residual(system["A"], direct_pa, system["b"]))
            crow = first_candidate_rows[it]
            brow = first_baseline_rows[it]
            c_equiv = rel_l2(crow["pressure_pa"], direct_pa)
            b_equiv = rel_l2(brow["pressure_pa"], direct_pa)
            gate(f"correctness_day{int(system['day'])}_direct_residual", direct_rel < PRESSURE_GATE, direct_rel)
            gate(f"correctness_day{int(system['day'])}_candidate_final_residual", float(crow["final_relative_residual"]) < PRESSURE_GATE, crow["final_relative_residual"])
            gate(f"correctness_day{int(system['day'])}_baseline_final_residual", float(brow["final_relative_residual"]) < PRESSURE_GATE, brow["final_relative_residual"])
            gate(f"correctness_day{int(system['day'])}_candidate_equivalent_to_direct", c_equiv <= PRESSURE_EQUIV_GATE, c_equiv)
            gate(f"correctness_day{int(system['day'])}_baseline_equivalent_to_direct", b_equiv <= PRESSURE_EQUIV_GATE, b_equiv)
            candidate_fallbacks_correctness += int(bool(crow["direct_fallback_used"]))
            baseline_fallbacks_correctness += int(bool(brow["direct_fallback_used"]))
            correctness_rows.append({
                "time_index": int(it),
                "target_day": float(system["day"]),
                "method": system["method"],
                "candidate_selected_seed": crow["selected_seed"],
                "candidate_learned_seed_admitted": bool(crow["learned_seed_admitted"]),
                "candidate_correction_iterations": int(crow["correction_iterations"]),
                "baseline_correction_iterations": int(brow["correction_iterations"]),
                "candidate_direct_fallback_used": bool(crow["direct_fallback_used"]),
                "baseline_direct_fallback_used": bool(brow["direct_fallback_used"]),
                "candidate_final_relative_residual": float(crow["final_relative_residual"]),
                "baseline_final_relative_residual": float(brow["final_relative_residual"]),
                "direct_reference_relative_residual": direct_rel,
                "candidate_pressure_relative_L2_vs_direct": c_equiv,
                "baseline_pressure_relative_L2_vs_direct": b_equiv,
            })

        gate("correctness_candidate_Day60plus_no_model_dispatch", all(r["selected_seed"] == "TEMPORAL" for r in correctness_rows[1:]))
        gate("locked_OOD_never_loaded", locked_ood_loaded is False)

        stage = "paired_measured_wallclock_execution"
        pair_rows: list[dict[str, Any]] = []
        candidate_times = []
        baseline_times = []

        for pair in range(1, TIMING_PAIRS + 1):
            candidate_first = bool(pair % 2 == 1)
            if candidate_first:
                ctime, _ = run_candidate()
                measured_candidate_trajectories += 1
                btime, _ = run_baseline()
                measured_baseline_trajectories += 1
            else:
                btime, _ = run_baseline()
                measured_baseline_trajectories += 1
                ctime, _ = run_candidate()
                measured_candidate_trajectories += 1

            candidate_times.append(ctime)
            baseline_times.append(btime)
            pair_rows.append({
                "pair": int(pair),
                "order": "CANDIDATE_FIRST" if candidate_first else "BASELINE_FIRST",
                "candidate_seconds": float(ctime),
                "baseline_seconds": float(btime),
                "candidate_minus_baseline_seconds": float(ctime - btime),
                "candidate_to_baseline_ratio": float(ctime / max(btime, 1.0e-30)),
                "candidate_faster": bool(ctime < btime),
            })
            print(
                f"B2 pair {pair:02d}: order={'C-FIRST' if candidate_first else 'B-FIRST'} "
                f"candidate={ctime:.6f}s baseline={btime:.6f}s "
                f"delta={ctime-btime:+.6f}s faster={ctime < btime}"
            )

        gate("exactly_11_candidate_measured_trajectories", measured_candidate_trajectories == TIMING_PAIRS, measured_candidate_trajectories)
        gate("exactly_11_baseline_measured_trajectories", measured_baseline_trajectories == TIMING_PAIRS, measured_baseline_trajectories)
        expected_orders = ["CANDIDATE_FIRST" if p % 2 == 1 else "BASELINE_FIRST" for p in range(1, TIMING_PAIRS + 1)]
        gate("measured_pair_order_alternated", [r["order"] for r in pair_rows] == expected_orders)

        stage = "economics_interpretation"
        candidate_arr = np.asarray(candidate_times, dtype=np.float64)
        baseline_arr = np.asarray(baseline_times, dtype=np.float64)
        candidate_median = float(np.median(candidate_arr))
        baseline_median = float(np.median(baseline_arr))
        candidate_mean = float(np.mean(candidate_arr))
        baseline_mean = float(np.mean(baseline_arr))
        faster_pairs = int(np.sum(candidate_arr < baseline_arr))
        ties = int(np.sum(candidate_arr == baseline_arr))
        median_criterion = bool(candidate_median < baseline_median)
        pair_criterion = bool(faster_pairs >= REQUIRED_FASTER_PAIRS)
        economically_qualified = bool(median_criterion and pair_criterion)
        sign_test_p = one_sided_sign_test_tail(faster_pairs, TIMING_PAIRS)

        if economically_qualified:
            classification = (
                "AV5_DAY30_ONLY_FROZEN_CHECKPOINT_VALIDATION_END_TO_END_WALLCLOCK_"
                "ECONOMICS_QUALIFIED_B3_INTERPRETATION_FREEZE_AUTHORIZED_NO_OOD_REUSE"
            )
        else:
            classification = (
                "AV5_DAY30_ONLY_FROZEN_CHECKPOINT_VALIDATION_END_TO_END_WALLCLOCK_"
                "ECONOMICS_NOT_QUALIFIED_B3_INTERPRETATION_FREEZE_AUTHORIZED_NO_OOD_REUSE"
            )

        outcome = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "validation_realization": VALIDATION_REALIZATION,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "device_description": device_description,
            "warmup_pairs": WARMUP_PAIRS,
            "measured_pairs": TIMING_PAIRS,
            "candidate_dispatch": "Day30 learned inference + exact residual admission; Day60+ temporal-only",
            "baseline_dispatch": "temporal-only all 9 states",
            "candidate_Day30_learned_seed_admitted_in_correctness_warmup": candidate_day30_admitted,
            "candidate_Day30_selected_seed_in_correctness_warmup": candidate_day30_seed,
            "candidate_correctness_direct_fallback_states": candidate_fallbacks_correctness,
            "baseline_correctness_direct_fallback_states": baseline_fallbacks_correctness,
            "candidate_median_seconds": candidate_median,
            "baseline_median_seconds": baseline_median,
            "candidate_mean_seconds": candidate_mean,
            "baseline_mean_seconds": baseline_mean,
            "median_candidate_minus_baseline_seconds": candidate_median - baseline_median,
            "median_candidate_to_baseline_ratio": candidate_median / max(baseline_median, 1.0e-30),
            "median_fractional_speedup": (baseline_median - candidate_median) / max(baseline_median, 1.0e-30),
            "candidate_faster_pairs": faster_pairs,
            "ties": ties,
            "required_candidate_faster_pairs": REQUIRED_FASTER_PAIRS,
            "one_sided_exact_sign_test_tail_probability": sign_test_p,
            "criterion_1_candidate_median_lower": median_criterion,
            "criterion_2_candidate_faster_at_least_9_of_11": pair_criterion,
            "economic_qualification_both_required": economically_qualified,
            "locked_OOD_loaded_or_scored": False,
            "no_training_no_reselection_no_retuning": True,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "AV4_authoritative_state_sha256": AV4_STATE_SHA,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "validation_realization": VALIDATION_REALIZATION,
            "paired_timing_repeats_completed": TIMING_PAIRS,
            "warmup_pairs_completed": WARMUP_PAIRS,
            "candidate_Day30_learned_seed_admitted": candidate_day30_admitted,
            "candidate_median_seconds": candidate_median,
            "baseline_median_seconds": baseline_median,
            "candidate_mean_seconds": candidate_mean,
            "baseline_mean_seconds": baseline_mean,
            "candidate_faster_pairs": faster_pairs,
            "required_candidate_faster_pairs": REQUIRED_FASTER_PAIRS,
            "one_sided_exact_sign_test_tail_probability": sign_test_p,
            "wallclock_economic_qualification_pass": economically_qualified,
            "model_inference_count_total": model_inference_count,
            "measured_candidate_trajectories": measured_candidate_trajectories,
            "measured_baseline_trajectories": measured_baseline_trajectories,
            "locked_OOD_loaded_or_scored": False,
            "model_training_executed": False,
            "new_checkpoint_created": False,
            "checkpoint_reselection_executed": False,
            "retuning_executed": False,
            "normalization_refit_executed": False,
            "AV5_production_execution_authorized": False,
            "P3_authorized": False,
            "AV4_state_mutated": False,
            "physical_time_advance_executed": False,
            "B3_interpretation_freeze_authorized": True,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "wallclock_economic_qualification_pass": economically_qualified,
            "criterion_1_candidate_median_lower": median_criterion,
            "criterion_2_candidate_faster_at_least_9_of_11": pair_criterion,
            "candidate_faster_pairs": faster_pairs,
            "checkpoint_remains_frozen": True,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "locked_OOD_reused_for_selection": False,
            "AV5_model_training_authorized": False,
            "AV5_checkpoint_reselection_authorized": False,
            "AV5_retuning_authorized": False,
            "AV5_production_execution_authorized": False,
            "P3_authorized": False,
            "B3_authorized": True,
            "B3_execution_authorized": True,
            "B3_name": "Validation Wall-Clock Economics Outcome Interpretation + AV5 Learned-Acceleration Closure Decision Freeze",
            "B3_must_not_execute_model": True,
            "B3_must_not_reuse_locked_OOD_for_selection": True,
            "AV4_state_mutation_authorized": False,
            "physical_time_advance_authorized": False,
        }

        handoff = {
            "milestone": "POSTV16-AV5-B3",
            "name": "Validation Wall-Clock Economics Outcome Interpretation + AV5 Learned-Acceleration Closure Decision Freeze",
            "authorized": True,
            "execution": True,
            "must_bind_B2_classification": classification,
            "must_bind_checkpoint_sha256": CHECKPOINT_SHA,
            "must_preserve_B2_economic_outcome": economically_qualified,
            "must_not_execute_model": True,
            "must_not_train_reselect_or_retune": True,
            "must_not_reuse_locked_OOD_for_selection": True,
            "must_not_mutate_AV4_state": True,
            "must_not_advance_physical_time": True,
            "must_not_automatically_authorize_production_or_P3": True,
        }

        output_files = {
            SUMMARY: jb(summary),
            PAIR_AUDIT: csvb(pair_rows),
            CORRECTNESS_AUDIT: csvb(correctness_rows),
            OUTCOME: jb(outcome),
            B3_HANDOFF: jb(handoff),
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
        print("=" * 214)
        print(M, "PASS")
        print("Classification                                      :", classification)
        print("Validation realization                              :", VALIDATION_REALIZATION)
        print("Device                                               :", device_description)
        print("Day30 learned seed admitted in correctness warmup    :", candidate_day30_admitted)
        print("Candidate median / mean seconds                      :", candidate_median, "/", candidate_mean)
        print("Baseline median / mean seconds                       :", baseline_median, "/", baseline_mean)
        print("Candidate faster measured pairs                      :", faster_pairs, "/", TIMING_PAIRS)
        print("One-sided exact sign-test tail p                     :", sign_test_p)
        print("Median-lower criterion                               :", median_criterion)
        print("9-of-11 criterion                                    :", pair_criterion)
        print("Wall-clock economic qualification                    :", economically_qualified)
        print("LOCKED OOD loaded/scored                             : False")
        print("Training / reselect / retune                         : False / False / False")
        print("Production / P3 authorized                           : False / False")
        print("B3 interpretation freeze authorized                  : True")
        print("=" * 214)
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
                "checkpoint_loaded": bool(checkpoint_loaded),
                "model_inference_count": int(model_inference_count),
                "warmup_candidate_trajectories": int(warmup_candidate_trajectories),
                "warmup_baseline_trajectories": int(warmup_baseline_trajectories),
                "measured_candidate_trajectories": int(measured_candidate_trajectories),
                "measured_baseline_trajectories": int(measured_baseline_trajectories),
                "locked_OOD_loaded_or_scored": bool(locked_ood_loaded),
                "model_training_executed": False,
                "new_checkpoint_created": False,
                "checkpoint_reselection_executed": False,
                "retuning_executed": False,
                "normalization_refit_executed": False,
                "AV5_production_execution_authorized": False,
                "P3_authorized": False,
                "AV4_state_mutation_executed": False,
                "physical_time_advance_executed": False,
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
