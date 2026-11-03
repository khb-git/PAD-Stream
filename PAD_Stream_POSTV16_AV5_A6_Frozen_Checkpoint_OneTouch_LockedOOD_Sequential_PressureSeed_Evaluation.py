#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


M = "POSTV16-AV5-A6"
NAME = "Frozen Checkpoint One-Touch Locked-OOD Sequential Pressure-Seed Evaluation"
PASS = (
    "POSTV16AV5A6_FROZEN_CHECKPOINT_ONE_TOUCH_LOCKED_OOD_SEQUENTIAL_PRESSURE_SEED_"
    "EVALUATION_PASS_NO_RETRAIN_NO_RESELECT_NO_RETUNE"
)
BLOCK = "POSTV16AV5A6_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "38f1b94a1893f324cfb306d8e9aab2fa5dd666d8"
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
PRESSURE_GATE = 1.0e-8
PRESSURE_EQUIV_GATE = 1.0e-8
EXPECTED_PARAMETER_COUNT = 337793
OOD_REALIZATION_INDEX = 3
OOD_REALIZATION_ID = "AV3CR0004"

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
A5R1_TOKEN = "POSTV16_AV5_A5_R1"
A5R1_REL = BASE_AV5 / (
    A5R1_TOKEN
    + "_SG3_Blob_Authority_Repair_Controlled_Training_and_Validation_ExactCorrection_Checkpoint_Selection"
)
A5R1_SUMMARY = f"PAD_Stream_{A5R1_TOKEN}_Summary.json"
A5R1_CHECKPOINT = f"{A5R1_TOKEN}_Best_Validation_Model.keras"
A5R1_HANDOFF = f"{A5R1_TOKEN}_A6_Handoff_Contract.json"
A5R1_DECISION = f"{A5R1_TOKEN}_Decision_Contract.json"
A5R1_MANIFEST = f"{A5R1_TOKEN}_Artifact_Manifest.csv"
A5R1_STATUS = (
    "POSTV16AV5A5R1_SG3_BLOB_AUTHORITY_REPAIR_FROZEN_PRESSURE_SEED_MODEL_CONTROLLED_TRAINING_"
    "VALIDATION_EXACT_CORRECTION_CHECKPOINT_SELECTION_PASS_LOCKED_OOD_UNOPENED"
)

A4_TOKEN = "POSTV16_AV5_A4"
A4_REL = BASE_AV5 / (
    A4_TOKEN
    + "_Exact_Pressure_Teacher_Dataset_TRAIN_Only_Normalization_and_Locked_OOD_Predictor_Materialization"
)
A4_SUMMARY = f"PAD_Stream_{A4_TOKEN}_Summary.json"
A4_OOD_SCAFFOLD = f"{A4_TOKEN}_LockedOOD_6Channel_Predictor_Scaffold.npz"
A4_NORMALIZATION = f"{A4_TOKEN}_TRAIN_Only_Normalization.npz"
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
A6E_OOD_STATE = "POSTV16_AV3_A6_E_AV3CR0004_Integrated_State.npz"

OUT_TOKEN = "POSTV16_AV5_A6"
OUT_REL = BASE_AV5 / (
    OUT_TOKEN + "_Frozen_Checkpoint_OneTouch_LockedOOD_Sequential_PressureSeed_Evaluation"
)
BLOCK_REL = BASE_AV5 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
STATE_AUDIT = f"{OUT_TOKEN}_LockedOOD_Sequential_State_Audit.csv"
OUTCOME = f"{OUT_TOKEN}_LockedOOD_Outcome_Contract.json"
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
        for key in row:
            if key not in fields:
                fields.append(key)
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


def selftest() -> None:
    assert GRID == (15, 50, 50)
    assert len(CANONICAL_DAYS) == 9
    assert len(INPUT_CHANNELS) == 6
    assert OOD_REALIZATION_INDEX == 3
    assert PRESSURE_GATE == 1.0e-8
    assert PRESSURE_EQUIV_GATE == 1.0e-8
    assert len(CHECKPOINT_SHA) == 64
    assert len(SG3_BLOB) == 40
    print("POSTV16 AV5-A6 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    import tensorflow as tf
    from scipy.sparse.linalg import spsolve

    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []
    states_completed = 0
    model_inference_count = 0
    direct_reference_count = 0
    checkpoint_loaded = False
    locked_ood_pressure_truth_opened = False

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
        print("=" * 210)
        print("POSTV16-AV5-A6 — FROZEN CHECKPOINT ONE-TOUCH LOCKED-OOD SEQUENTIAL PRESSURE-SEED EVALUATION")
        print("=" * 210)
        print("LOCKED OOD: AV3CR0004 only; 9 canonical states, sequentially, exactly one model inference per state.")
        print("NO RETRAINING / RESELECTION / RETUNING / NORMALIZATION REFIT.")
        print("Learned seed admitted only when exact residual is lower than temporal seed residual.")
        print("Exact FV Krylov correction remains authoritative; direct spsolve remains fallback/reference.")
        print("Accepted corrected pressure is carried forward as the next temporal pressure input.")
        print("NO AV4 STATE MUTATION. NO PHYSICAL TIME ADVANCE. NO PRODUCTION EXECUTION. P3 REMAINS LOCKED.")
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

        stage = "A5R1_checkpoint_and_handoff_authority"
        a5d = drive / A5R1_REL
        a5m = manifest(a5d, A5R1_MANIFEST)
        a5s = js(a5d / A5R1_SUMMARY)
        a5h = js(a5d / A5R1_HANDOFF)
        a5c = js(a5d / A5R1_DECISION)
        checkpoint = a5d / A5R1_CHECKPOINT

        gate("A5R1_status_exact", a5s.get("status") == A5R1_STATUS, a5s.get("status"))
        gate("A5R1_AV4_state_SHA_exact", a5s.get("AV4_authoritative_state_sha256") == AV4_STATE_SHA)
        gate("A5R1_original_A5_BLOCK_preserved", a5c.get("original_A5_BLOCK_preserved") is True)
        gate("A5R1_SG3_repair_only", a5c.get("SG3_blob_authority_repair_only") is True)
        gate("A5R1_checkpoint_frozen", a5c.get("checkpoint_frozen") is True)
        gate("A5R1_checkpoint_SHA_exact", a5c.get("checkpoint_sha256") == CHECKPOINT_SHA and a5h.get("must_bind_checkpoint_sha256") == CHECKPOINT_SHA)
        gate("A5R1_checkpoint_selected_without_OOD", a5c.get("checkpoint_selected_without_locked_OOD") is True)
        gate("A5R1_A6_authorized", a5c.get("AV5_A6_authorized") is True and a5h.get("authorized") is True)
        gate("A5R1_A6_execution_authorized", a5c.get("AV5_A6_execution_authorized") is True and a5h.get("execution") is True)
        gate("A5R1_A6_one_touch_authorized", a5c.get("AV5_A6_locked_OOD_one_touch_authorized") is True)
        gate("A5R1_A6_TRAIN_normalization_required", a5c.get("AV5_A6_must_use_A4_TRAIN_only_normalization") is True)
        gate("A5R1_A6_no_retrain_reselect_retune", a5c.get("AV5_A6_must_not_retrain_reselect_or_retune") is True)
        gate("A5R1_exact_residual_admission_required", a5c.get("AV5_A6_must_preserve_exact_residual_seed_admission") is True)
        gate("A5R1_exact_FV_correction_required", a5c.get("AV5_A6_must_preserve_exact_FV_correction") is True)
        gate("A5R1_direct_fallback_required", a5c.get("AV5_A6_must_preserve_direct_spsolve_fallback") is True)
        gate("A5R1_model_training_locked", a5c.get("AV5_model_training_authorized") is False)
        gate("A5R1_checkpoint_reselection_locked", a5c.get("AV5_checkpoint_reselection_authorized") is False)
        gate("A5R1_checkpoint_manifested", A5R1_CHECKPOINT in a5m and checkpoint.is_file())
        gate("A5R1_checkpoint_file_SHA_exact", checkpoint.is_file() and sha(checkpoint) == CHECKPOINT_SHA, sha(checkpoint) if checkpoint.is_file() else "missing")

        stage = "A4_normalization_and_OOD_scaffold_authority"
        a4d = drive / A4_REL
        a4m = manifest(a4d, A4_MANIFEST)
        a4s = js(a4d / A4_SUMMARY)
        gate("A4_status_exact", a4s.get("status") == A4_STATUS, a4s.get("status"))
        gate("A4_locked_OOD_targets_were_not_generated", a4s.get("LOCKED_OOD_canonical_pressure_targets_generated") is False)
        gate("A4_TRAIN_only_normalization_frozen", a4s.get("TRAIN_only_normalization_frozen") is True)
        gate("A4_OOD_scaffold_manifested", A4_OOD_SCAFFOLD in a4m and (a4d / A4_OOD_SCAFFOLD).is_file())
        gate("A4_normalization_manifested", A4_NORMALIZATION in a4m and (a4d / A4_NORMALIZATION).is_file())

        with np.load(a4d / A4_NORMALIZATION, allow_pickle=False) as z:
            loglam_mean = float(np.asarray(z["log10_total_mobility_mean"]).reshape(()))
            loglam_std = float(np.asarray(z["log10_total_mobility_std"]).reshape(()))
            prev_mean = float(np.asarray(z["previous_pressure_psi_mean"]).reshape(()))
            prev_std = float(np.asarray(z["previous_pressure_psi_std"]).reshape(()))
            delta_mean = float(np.asarray(z["delta_pressure_psi_mean"]).reshape(()))
            delta_std = float(np.asarray(z["delta_pressure_psi_std"]).reshape(()))
            fit_state_count = int(np.asarray(z["fit_state_count"]).reshape(()))
            fit_realization_indices = np.asarray(z["fit_realization_indices"], dtype=np.int64)

        gate("A4_normalization_TRAIN_only_exact", fit_state_count == 18 and np.array_equal(fit_realization_indices, np.asarray([0, 1], dtype=np.int64)))
        gate("A4_normalization_stats_valid", all(np.isfinite(x) for x in [loglam_mean, loglam_std, prev_mean, prev_std, delta_mean, delta_std]) and all(x > 0.0 for x in [loglam_std, prev_std, delta_std]))

        with np.load(a4d / A4_OOD_SCAFFOLD, allow_pickle=False) as z:
            X_partial = np.asarray(z["X6_partial"], dtype=np.float32)
            prev_available = np.asarray(z["previous_pressure_available"], dtype=np.bool_)
            realization_index = np.asarray(z["realization_index"], dtype=np.int64)
            time_index = np.asarray(z["time_index"], dtype=np.int64)
            target_day = np.asarray(z["target_day"], dtype=np.float64)
            channel_names = [str(x) for x in np.asarray(z["input_channel_names"]).tolist()]
            pressure_target_generated = bool(np.asarray(z["canonical_pressure_target_generated"]).reshape(()))
            delta_target_generated = bool(np.asarray(z["canonical_delta_pressure_target_generated"]).reshape(()))
            post_checkpoint_completion_required = bool(np.asarray(z["post_checkpoint_completion_required"]).reshape(()))
            scaffold_av4_sha = str(np.asarray(z["AV4_authoritative_state_sha256"]).reshape(-1)[0])

        gate("A4_OOD_scaffold_shape_exact", X_partial.shape == (9, 15, 50, 50, 6), X_partial.shape)
        gate("A4_OOD_channel_order_exact", channel_names == INPUT_CHANNELS, channel_names)
        gate("A4_OOD_registry_exact", np.array_equal(realization_index, np.full(9, OOD_REALIZATION_INDEX)) and np.array_equal(time_index, np.arange(9)) and np.array_equal(target_day, CANONICAL_DAYS))
        gate("A4_OOD_target_firewall_exact", pressure_target_generated is False and delta_target_generated is False)
        gate("A4_OOD_post_checkpoint_completion_required", post_checkpoint_completion_required is True)
        gate("A4_OOD_AV4_SHA_exact", scaffold_av4_sha == AV4_STATE_SHA)
        gate("A4_OOD_day30_previous_available_only", np.array_equal(prev_available, np.asarray([True] + [False] * 8)))
        gate("A4_OOD_static_channels_finite", np.isfinite(X_partial[..., [0, 1, 3, 4, 5]]).all())
        gate("A4_OOD_later_previous_channels_sealed", np.isnan(X_partial[1:, ..., 2]).all())

        stage = "A6E_locked_OOD_physical_state_authority"
        a6d = drive / A6E_REL
        a6m = manifest(a6d, A6E_MANIFEST)
        a6s = js(a6d / A6E_SUMMARY)
        ood_state = a6d / A6E_OOD_STATE
        gate("A6E_status_exact", a6s.get("status") == A6E_STATUS, a6s.get("status"))
        gate("A6E_OOD_state_manifested", A6E_OOD_STATE in a6m and ood_state.is_file())
        with np.load(ood_state, allow_pickle=False) as z:
            nw = np.asarray(z["nw"], dtype=np.float64)
            no = np.asarray(z["no"], dtype=np.float64)
            krw_max = np.asarray(z["krw_max"], dtype=np.float64)
            kro_max = np.asarray(z["kro_max"], dtype=np.float64)
            sat_all = np.asarray(z["grid_saturation"], dtype=np.float64)
            days_exact = np.asarray(z["target_days"], dtype=np.float64)
        gate("A6E_OOD_field_shapes_exact", all(a.shape == GRID for a in [nw, no, krw_max, kro_max]))
        gate("A6E_OOD_saturation_shape_exact", sat_all.shape == (9,) + GRID, sat_all.shape)
        gate("A6E_OOD_days_exact", np.array_equal(days_exact, CANONICAL_DAYS))

        stage = "runtime_physics_and_checkpoint_binding"
        sg2 = mod(root / SG2, "av5a6_sg2")
        sg3 = mod(root / SG3, "av5a6_sg3")
        r3 = mod(root / R3, "av5a6_r3")
        a2e = mod(root / A2E, "av5a6_a2e")
        a2r1 = mod(root / A2R1, "av5a6_a2r1")

        permeability = np.loadtxt(root / PERM, skiprows=1, dtype=np.float64).reshape(GRID, order="C")
        gate("permeability_valid", permeability.shape == GRID and np.isfinite(permeability).all() and np.all(permeability > 0.0))
        kx, ky, kz = sg2.build_directional_permeability(permeability)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)

        model = tf.keras.models.load_model(checkpoint, compile=False)
        checkpoint_loaded = True
        gate("checkpoint_model_parameter_count_exact", int(model.count_params()) == EXPECTED_PARAMETER_COUNT, int(model.count_params()))
        gate("checkpoint_model_input_shape_exact", tuple(model.input_shape[1:]) == GRID + (6,), model.input_shape)
        gate("checkpoint_model_output_shape_exact", tuple(model.output_shape[1:]) == GRID + (1,), model.output_shape)

        background_sat = np.full(GRID, 0.20, dtype=np.float64)
        background_mobility = a2e.spatial_mobility(background_sat, nw, no, krw_max, kro_max)
        bg_tx, bg_ty, bg_tz, _ = r3.build_updated_transmissibilities(
            sg3, tx_ref, ty_ref, tz_ref, background_mobility["lambda_total"]
        )
        bg_A, bg_b, _ = r3.assemble_updated_pressure_system(
            sg3, permeability, bg_tx, bg_ty, bg_tz, background_mobility["lambda_total"]
        )
        background_pa = np.asarray(spsolve(bg_A, bg_b), dtype=np.float64)
        background_rel = float(a2r1.lin_residual(bg_A, background_pa, bg_b))
        background_psi = (background_pa * float(sg3.PA_TO_PSI)).reshape(GRID, order="C")
        gate("OOD_background_seed_exact_residual", background_rel < PRESSURE_GATE, background_rel)
        bg_norm = normalize(background_psi, prev_mean, prev_std)
        gate("A4_day30_stored_previous_channel_reproduced", np.allclose(bg_norm, X_partial[0, ..., 2], rtol=0.0, atol=2.0e-6), float(np.max(np.abs(bg_norm - X_partial[0, ..., 2]))))

        stage = "one_touch_sequential_locked_OOD_evaluation"
        rows: list[dict[str, Any]] = []
        previous_pressure_psi = background_psi.copy()
        selected_iters: list[int] = []
        temporal_iters: list[int] = []
        selected_fallbacks = 0
        temporal_fallbacks = 0
        learned_admitted = 0
        learned_improved_iterations = 0
        failure_penalty = int(a2r1.MAX_KRYLOV_ITERATIONS) + 1

        for it, day in enumerate(CANONICAL_DAYS.tolist()):
            saturation = np.asarray(sat_all[it], dtype=np.float64)
            mobility = a2e.spatial_mobility(saturation, nw, no, krw_max, kro_max)
            reconstructed_loglam_norm = normalize(np.log10(np.asarray(mobility["lambda_total"], dtype=np.float64)), loglam_mean, loglam_std)
            gate(f"day{int(day)}_A4_mobility_channel_reproduced", np.allclose(reconstructed_loglam_norm, X_partial[it, ..., 1], rtol=0.0, atol=2.0e-6), float(np.max(np.abs(reconstructed_loglam_norm - X_partial[it, ..., 1]))))

            X_state = np.asarray(X_partial[it], dtype=np.float32).copy()
            if it == 0:
                # Use the A4-materialized Day30 channel byte-for-byte; the reconstructed exact
                # background pressure above is used as the physical temporal seed.
                X_state[..., 2] = X_partial[0, ..., 2]
            else:
                X_state[..., 2] = normalize(previous_pressure_psi, prev_mean, prev_std)
            gate(f"day{int(day)}_completed_X6_finite", np.isfinite(X_state).all())
            if it == 0:
                gate("day30_completed_previous_channel_matches_A4_scaffold", np.array_equal(X_state[..., 2], X_partial[0, ..., 2]))

            tx, ty, tz, _ = r3.build_updated_transmissibilities(
                sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
            )
            A, b, _ = r3.assemble_updated_pressure_system(
                sg3, permeability, tx, ty, tz, mobility["lambda_total"]
            )
            audit = a2r1.matrix_audit(A)
            method = "cg" if audit["structural_SPD_candidate"] else "gmres"

            # Exactly one learned inference for this OOD state.
            pred_norm = np.asarray(model(X_state[None, ...], training=False).numpy(), dtype=np.float64)[0, ..., 0]
            model_inference_count += 1
            gate(f"day{int(day)}_single_prediction_finite", np.isfinite(pred_norm).all())
            delta_pred_psi = pred_norm * delta_std + delta_mean
            p_hat_psi = previous_pressure_psi + delta_pred_psi
            p_hat_pa = p_hat_psi.reshape(-1, order="C") * float(sg3.PSI_TO_PA)
            p_prev_pa = previous_pressure_psi.reshape(-1, order="C") * float(sg3.PSI_TO_PA)

            r_hat = np.asarray(b - A @ p_hat_pa, dtype=np.float64)
            r_prev = np.asarray(b - A @ p_prev_pa, dtype=np.float64)
            hat_norm = float(np.linalg.norm(r_hat))
            prev_norm = float(np.linalg.norm(r_prev))
            admitted = bool(hat_norm < prev_norm)
            if admitted:
                learned_admitted += 1
            selected_seed = p_hat_pa if admitted else p_prev_pa
            selected_label = "LEARNED" if admitted else "TEMPORAL"

            selected_corr = a2r1.correction_solve(A, b, selected_seed, method)
            if bool(selected_corr["success"]):
                selected_iter = int(selected_corr["iterations"])
                corrected_pa = np.asarray(selected_corr["pressure_pa"], dtype=np.float64)
                selected_final_rel = float(selected_corr["final_relative_residual"])
                selected_fallback = False
            else:
                selected_iter = failure_penalty
                corrected_pa = np.asarray(spsolve(A, b), dtype=np.float64)
                selected_final_rel = float(a2r1.lin_residual(A, corrected_pa, b))
                selected_fallback = True
                selected_fallbacks += 1

            # Temporal baseline uses the same exact system. Reuse selected solve if learned seed was rejected.
            if not admitted:
                temporal_iter = selected_iter
                temporal_final_rel = selected_final_rel
                temporal_fallback = selected_fallback
                if temporal_fallback:
                    temporal_fallbacks += 1
            else:
                temporal_corr = a2r1.correction_solve(A, b, p_prev_pa, method)
                if bool(temporal_corr["success"]):
                    temporal_iter = int(temporal_corr["iterations"])
                    temporal_final_rel = float(temporal_corr["final_relative_residual"])
                    temporal_fallback = False
                else:
                    temporal_iter = failure_penalty
                    temporal_direct = np.asarray(spsolve(A, b), dtype=np.float64)
                    temporal_final_rel = float(a2r1.lin_residual(A, temporal_direct, b))
                    temporal_fallback = True
                    temporal_fallbacks += 1

            # OOD pressure reference is opened only after frozen inference / admission / correction for this state.
            direct_pa = np.asarray(spsolve(A, b), dtype=np.float64)
            direct_reference_count += 1
            locked_ood_pressure_truth_opened = True
            direct_rel = float(a2r1.lin_residual(A, direct_pa, b))
            direct_psi = (direct_pa * float(sg3.PA_TO_PSI)).reshape(GRID, order="C")
            corrected_psi = (corrected_pa * float(sg3.PA_TO_PSI)).reshape(GRID, order="C")
            pressure_equiv = rel_l2(corrected_pa, direct_pa)

            gate(f"day{int(day)}_selected_correction_final_residual", selected_final_rel < PRESSURE_GATE, selected_final_rel)
            gate(f"day{int(day)}_temporal_baseline_final_residual", temporal_final_rel < PRESSURE_GATE, temporal_final_rel)
            gate(f"day{int(day)}_direct_reference_final_residual", direct_rel < PRESSURE_GATE, direct_rel)
            gate(f"day{int(day)}_corrected_pressure_equivalence_to_direct", pressure_equiv <= PRESSURE_EQUIV_GATE, pressure_equiv)

            if selected_iter < temporal_iter:
                learned_improved_iterations += 1

            selected_iters.append(selected_iter)
            temporal_iters.append(temporal_iter)
            states_completed += 1
            rows.append({
                "realization_id": OOD_REALIZATION_ID,
                "time_index": int(it),
                "target_day": float(day),
                "method": method,
                "model_inference_count_for_state": 1,
                "learned_seed_admitted": admitted,
                "selected_seed": selected_label,
                "learned_initial_residual_l2": hat_norm,
                "temporal_initial_residual_l2": prev_norm,
                "learned_to_temporal_initial_residual_ratio": hat_norm / max(prev_norm, 1.0e-30),
                "selected_correction_iterations": int(selected_iter),
                "temporal_baseline_correction_iterations": int(temporal_iter),
                "iteration_delta_selected_minus_temporal": int(selected_iter - temporal_iter),
                "selected_direct_fallback_used": selected_fallback,
                "temporal_direct_fallback_used": temporal_fallback,
                "selected_final_relative_residual": selected_final_rel,
                "temporal_final_relative_residual": temporal_final_rel,
                "direct_reference_relative_residual": direct_rel,
                "corrected_pressure_relative_L2_vs_direct": pressure_equiv,
                "learned_seed_pressure_relative_L2_vs_direct": rel_l2(p_hat_pa, direct_pa),
                "temporal_seed_pressure_relative_L2_vs_direct": rel_l2(p_prev_pa, direct_pa),
                "direct_reference_opened_after_inference_and_correction": True,
                "accepted_corrected_pressure_carried_forward": True,
            })

            # Sequential protocol: carry the accepted corrected pressure, not the direct reference, forward.
            previous_pressure_psi = corrected_psi

        stage = "global_one_touch_outcome"
        gate("all_9_locked_OOD_states_completed", states_completed == 9, states_completed)
        gate("exactly_9_model_inferences", model_inference_count == 9, model_inference_count)
        gate("exactly_9_direct_references_opened", direct_reference_count == 9, direct_reference_count)
        gate("locked_OOD_pressure_truth_opened_only_in_authorized_A6", locked_ood_pressure_truth_opened is True)
        gate("no_retraining", True)
        gate("no_checkpoint_reselection", True)
        gate("no_retuning", True)
        gate("no_normalization_refit", True)
        gate("AV4_state_mutation_not_executed", True)
        gate("physical_time_advance_not_executed", True)
        gate("production_execution_not_executed", True)

        selected_arr = np.asarray(selected_iters, dtype=np.float64)
        temporal_arr = np.asarray(temporal_iters, dtype=np.float64)
        selected_median = float(np.median(selected_arr))
        selected_mean = float(np.mean(selected_arr))
        temporal_median = float(np.median(temporal_arr))
        temporal_mean = float(np.mean(temporal_arr))
        acceleration_observed = bool(selected_median < temporal_median or selected_mean < temporal_mean)
        all_pressure_equivalent = all(float(r["corrected_pressure_relative_L2_vs_direct"]) <= PRESSURE_EQUIV_GATE for r in rows)
        gate("all_corrected_pressures_exact_equivalent", all_pressure_equivalent)

        if acceleration_observed:
            classification = (
                "AV5_FROZEN_PRESSURE_SEED_ONE_TOUCH_LOCKED_OOD_EXACT_CORRECTION_PASS_"
                "OOD_ACCELERATION_OBSERVED_NO_ADAPTATION"
            )
        else:
            classification = (
                "AV5_FROZEN_PRESSURE_SEED_ONE_TOUCH_LOCKED_OOD_EXACT_CORRECTION_PASS_"
                "NO_OOD_ACCELERATION_OBSERVED_NO_ADAPTATION"
            )

        outcome = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "locked_OOD_realization": OOD_REALIZATION_ID,
            "locked_OOD_states": 9,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "checkpoint_parameter_count": EXPECTED_PARAMETER_COUNT,
            "model_inference_count": model_inference_count,
            "direct_reference_count": direct_reference_count,
            "learned_seed_admitted_states": learned_admitted,
            "states_with_selected_iteration_improvement": learned_improved_iterations,
            "selected_correction_median_iterations": selected_median,
            "selected_correction_mean_iterations": selected_mean,
            "temporal_baseline_median_iterations": temporal_median,
            "temporal_baseline_mean_iterations": temporal_mean,
            "selected_minus_temporal_median_iterations": selected_median - temporal_median,
            "selected_minus_temporal_mean_iterations": selected_mean - temporal_mean,
            "selected_direct_fallback_states": selected_fallbacks,
            "temporal_direct_fallback_states": temporal_fallbacks,
            "OOD_acceleration_observed": acceleration_observed,
            "no_speedup_threshold_was_frozen": True,
            "all_corrected_pressures_exact_equivalent_to_direct": all_pressure_equivalent,
            "one_touch_no_adaptation": True,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "AV4_authoritative_state_sha256": AV4_STATE_SHA,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "checkpoint_loaded": checkpoint_loaded,
            "locked_OOD_realization": OOD_REALIZATION_ID,
            "locked_OOD_states_completed": states_completed,
            "model_inference_count": model_inference_count,
            "learned_seed_admitted_states": learned_admitted,
            "selected_correction_median_iterations": selected_median,
            "selected_correction_mean_iterations": selected_mean,
            "temporal_baseline_median_iterations": temporal_median,
            "temporal_baseline_mean_iterations": temporal_mean,
            "selected_direct_fallback_states": selected_fallbacks,
            "temporal_direct_fallback_states": temporal_fallbacks,
            "OOD_acceleration_observed": acceleration_observed,
            "locked_OOD_pressure_truth_opened": True,
            "locked_OOD_pressure_truth_opened_only_after_checkpoint_freeze": True,
            "model_training_executed": False,
            "checkpoint_reselection_executed": False,
            "retuning_executed": False,
            "normalization_refit_executed": False,
            "AV4_state_mutated": False,
            "physical_time_advance_executed": False,
            "AV5_production_execution_authorized": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "checkpoint_remains_frozen": True,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "locked_OOD_one_touch_completed": True,
            "locked_OOD_one_touch_no_adaptation": True,
            "OOD_acceleration_observed": acceleration_observed,
            "exact_FV_correction_preserved": True,
            "direct_spsolve_reference_and_fallback_preserved": True,
            "AV5_model_training_authorized": False,
            "AV5_checkpoint_reselection_authorized": False,
            "AV5_retuning_authorized": False,
            "AV5_production_execution_authorized": False,
            "AV4_state_mutation_authorized": False,
            "P3_authorized": False,
            "next_execution_authorized": False,
            "next_step": "interpret and freeze AV5 scientific outcome before any production/P3 authorization decision",
        }

        output_files = {
            SUMMARY: jb(summary),
            STATE_AUDIT: csvb(rows),
            OUTCOME: jb(outcome),
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
        print("=" * 210)
        print(M, "PASS")
        print("Classification                                      :", classification)
        print("Checkpoint SHA256                                   :", CHECKPOINT_SHA)
        print("LOCKED OOD states / model inferences                :", states_completed, "/", model_inference_count)
        print("Learned seed admitted states                        :", learned_admitted, "/ 9")
        print("Selected correction median / mean iterations        :", selected_median, "/", selected_mean)
        print("Temporal baseline median / mean iterations          :", temporal_median, "/", temporal_mean)
        print("Selected direct fallback states                     :", selected_fallbacks)
        print("OOD acceleration observed                           :", acceleration_observed)
        print("LOCKED OOD truth opened after checkpoint freeze     : True")
        print("Retrain / reselect / retune                         : False / False / False")
        print("Production execution / P3 authorized                : False / False")
        print("=" * 210)
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
                "states_completed": int(states_completed),
                "model_inference_count": int(model_inference_count),
                "direct_reference_count": int(direct_reference_count),
                "locked_OOD_pressure_truth_opened": bool(locked_ood_pressure_truth_opened),
                "model_training_executed": False,
                "checkpoint_reselection_executed": False,
                "retuning_executed": False,
                "normalization_refit_executed": False,
                "AV4_state_mutation_executed": False,
                "physical_time_advance_executed": False,
                "AV5_production_execution_authorized": False,
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
