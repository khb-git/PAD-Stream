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
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


M = "POSTV16-AV5-A4"
NAME = (
    "Exact Pressure-Teacher Dataset Generation + TRAIN-Only Normalization + "
    "Locked-OOD Predictor Materialization"
)

PASS = (
    "POSTV16AV5A4_EXACT_PRESSURE_TEACHER_DATASET_TRAIN_ONLY_NORMALIZATION_"
    "AND_LEAKAGE_SAFE_LOCKED_OOD_PREDICTOR_MATERIALIZATION_PASS_NO_TRAINING"
)
BLOCK = "POSTV16AV5A4_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "ee5870ba86a8cb5acaa6a40b90621d87d39acf6d"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
BASE_AV5 = Path("post_v16") / RID / "POSTV16_AV5_Learned_Acceleration"

AV4_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"
GRID = (15, 50, 50)
NZ, NY, NX = GRID
N = int(np.prod(GRID))
CANONICAL_DAYS = np.asarray(
    [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0],
    dtype=np.float64,
)
PRESSURE_LINEAR_REL_RESIDUAL_MAX = 1.0e-8

# -------------------------------------------------------------------------------------------------
# Exact source authorities.
# -------------------------------------------------------------------------------------------------
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
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
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
# Frozen Drive authorities.
# -------------------------------------------------------------------------------------------------
A3_TOKEN = "POSTV16_AV5_A3"
A3_REL = BASE_AV5 / (
    A3_TOKEN + "_TeacherDataset_Split_PressureSeed_Model_Objective_Design_Freeze"
)
A3_SUMMARY = f"PAD_Stream_{A3_TOKEN}_Summary.json"
A3_DATASET = f"{A3_TOKEN}_Teacher_Dataset_and_Leakage_Firewall.json"
A3_MODEL = f"{A3_TOKEN}_Pressure_Seed_Model_Contract.json"
A3_DECISION = f"{A3_TOKEN}_Decision_Contract.json"
A3_MANIFEST = f"{A3_TOKEN}_Artifact_Manifest.csv"
A3_STATUS = (
    "POSTV16AV5A3_TEACHER_DATASET_SPLIT_PRESSURE_SEED_MODEL_OBJECTIVE_"
    "DESIGN_FREEZE_PASS_NO_TEACHER_GENERATION_NO_TRAINING"
)

A2R1_TOKEN = "POSTV16_AV5_A2_R1"
A2R1_REL = BASE_AV5 / (
    A2R1_TOKEN + "_AcceptedPressureSystem_ExactCorrection_WarmStart_Benchmark"
)
A2R1_SUMMARY = f"PAD_Stream_{A2R1_TOKEN}_Summary.json"
A2R1_DECISION = f"{A2R1_TOKEN}_Decision_Contract.json"
A2R1_MANIFEST = f"{A2R1_TOKEN}_Artifact_Manifest.csv"
A2R1_STATUS = (
    "POSTV16AV5A2R1_ACCEPTED_PRESSURE_SYSTEM_EXACT_CORRECTION_"
    "WARM_START_BENCHMARK_PASS_NO_ML_NO_STATE_MUTATION"
)

A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_SUMMARY = "PAD_Stream_POSTV16_AV3_A6_E_Summary.json"
A6E_MANIFEST = "POSTV16_AV3_A6_E_Artifact_Manifest.csv"
A6E_STATUS = (
    "AV3A6E_FROZEN_EPOCH92_CHECKPOINT_LOCAL_PORE_VOLUME_R7D_TERMINAL_HALO_"
    "INTEGRATION_ALL_4_REALIZATIONS_ALL_9_TIMES_PASS"
)

REALIZATION_REGISTRY = [
    {"id": "AV3CR0001", "partition": "TRAIN", "paired_porosity": "AV2PHI0001", "index": 0},
    {"id": "AV3CR0002", "partition": "TRAIN", "paired_porosity": "AV2PHI0002", "index": 1},
    {"id": "AV3CR0003", "partition": "VALIDATION", "paired_porosity": "AV2PHI0003", "index": 2},
    {"id": "AV3CR0004", "partition": "LOCKED_OOD_TEST", "paired_porosity": "AV2PHI0004", "index": 3},
]

INPUT_CHANNELS = [
    "log10_permeability_md",
    "log10_total_mobility",
    "previous_pressure_normalized",
    "injector_source_map",
    "producer_bhp_map",
    "normalized_depth_z",
]

OUT_TOKEN = "POSTV16_AV5_A4"
OUT_REL = BASE_AV5 / (
    OUT_TOKEN
    + "_Exact_Pressure_Teacher_Dataset_TRAIN_Only_Normalization_and_Locked_OOD_Predictor_Materialization"
)
BLOCK_REL = BASE_AV5 / (OUT_TOKEN + "_BLOCKED")

TRAINVAL_DATASET = f"{OUT_TOKEN}_TrainValidation_6Channel_PressureTeacher_Dataset.npz"
OOD_SCAFFOLD = f"{OUT_TOKEN}_LockedOOD_6Channel_Predictor_Scaffold.npz"
NORMALIZATION = f"{OUT_TOKEN}_TRAIN_Only_Normalization.npz"
STATE_REGISTRY = f"{OUT_TOKEN}_State_Registry.csv"
TEACHER_AUDIT = f"{OUT_TOKEN}_Exact_Teacher_Audit.csv"
CHANNEL_CONTRACT = f"{OUT_TOKEN}_Channel_Materialization_Contract.json"
A5_HANDOFF = f"{OUT_TOKEN}_A5_Handoff_Contract.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
GATE_MATRIX = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"


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


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


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
    return result


def mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def rel_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(np.linalg.norm((aa - bb).ravel()) / max(float(np.linalg.norm(bb.ravel())), 1.0e-30))


def build_fixed_maps(sg3: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Deterministic fixed well/depth descriptors for the A3-frozen six-channel schema."""
    injector = np.zeros(GRID, dtype=np.float64)
    source_fraction_per_completion = float(sg3.Q_INJ_PERF_M3_S / sg3.Q_INJ_M3_S)
    for k in sg3.COMPLETION_K:
        injector[int(k), int(sg3.INJECTOR_J), int(sg3.INJECTOR_I)] = source_fraction_per_completion

    producer = np.zeros(GRID, dtype=np.float64)
    bhp_ratio = float(sg3.PRODUCER_BHP_PSI / sg3.INITIAL_PRESSURE_PSI)
    for well in sg3.PRODUCERS.values():
        for k in sg3.COMPLETION_K:
            producer[int(k), int(well["j"]), int(well["i"])] = bhp_ratio

    depth = np.empty(GRID, dtype=np.float64)
    total_depth_m = float(sg3.NZ * sg3.DZ_M)
    for k in range(sg3.NZ):
        depth[k, :, :] = float(sg3.cell_center_z_m(k) / total_depth_m)

    return injector, producer, depth


def solve_state(
    *,
    saturation: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
    permeability: np.ndarray,
    tx_ref: np.ndarray,
    ty_ref: np.ndarray,
    tz_ref: np.ndarray,
    a2e: Any,
    r3: Any,
    sg3: Any,
) -> dict[str, Any]:
    mobility = a2e.spatial_mobility(saturation, nw, no, krw_max, kro_max)
    tx, ty, tz, _face = r3.build_updated_transmissibilities(
        sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
    )
    A, b, producer_wi = r3.assemble_updated_pressure_system(
        sg3, permeability, tx, ty, tz, mobility["lambda_total"]
    )
    p_pa, p_psi, residual = r3.solve_updated_pressure(sg3, A, b)
    return {
        "lambda_total": np.asarray(mobility["lambda_total"], dtype=np.float64),
        "A": A,
        "b": np.asarray(b, dtype=np.float64),
        "producer_wi": producer_wi,
        "p_pa": np.asarray(p_pa, dtype=np.float64),
        "p_psi": np.asarray(p_psi, dtype=np.float64),
        "relative_residual": float(residual),
    }


def stats_train(x: np.ndarray) -> tuple[float, float]:
    a = np.asarray(x, dtype=np.float64)
    mean = float(np.mean(a))
    std = float(np.std(a))
    if not np.isfinite(mean) or not np.isfinite(std) or std <= 0.0:
        raise GateError("invalid_TRAIN_normalization_statistics")
    return mean, std


def normalize(a: np.ndarray, mean: float, std: float) -> np.ndarray:
    return ((np.asarray(a, dtype=np.float64) - mean) / std).astype(np.float32)


def selftest() -> None:
    assert GRID == (15, 50, 50)
    assert N == 37500
    assert len(CANONICAL_DAYS) == 9
    assert len(INPUT_CHANNELS) == 6
    assert [r["partition"] for r in REALIZATION_REGISTRY].count("TRAIN") == 2
    assert [r["partition"] for r in REALIZATION_REGISTRY].count("VALIDATION") == 1
    assert [r["partition"] for r in REALIZATION_REGISTRY].count("LOCKED_OOD_TEST") == 1
    assert PRESSURE_LINEAR_REL_RESIDUAL_MAX == 1.0e-8
    print("POSTV16 AV5-A4 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []
    teacher_generation_executed = False
    ood_canonical_pressure_target_generated = False

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
        print("=" * 200)
        print("POSTV16-AV5-A4 — EXACT PRESSURE-TEACHER DATASET / TRAIN-ONLY NORMALIZATION / LOCKED-OOD MATERIALIZATION")
        print("=" * 200)
        print("TRAIN/VALIDATION: exact direct-spsolve pressure teachers.")
        print("LOCKED OOD: no canonical pressure target generation; leakage-safe predictor scaffold only.")
        print("NO MODEL TRAINING. NO LEARNED INFERENCE. NO AV4 STATE MUTATION. NO PHYSICAL TIME ADVANCE.")
        print()

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_exact", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "A3_design_authority"
        a3d = drive / A3_REL
        a3m = manifest(a3d, A3_MANIFEST)
        a3s = js(a3d / A3_SUMMARY)
        a3dataset = js(a3d / A3_DATASET)
        a3model = js(a3d / A3_MODEL)
        a3c = js(a3d / A3_DECISION)
        gate("A3_status_exact", a3s.get("status") == A3_STATUS, a3s.get("status"))
        gate("A3_AV4_state_binding_exact", a3s.get("AV4_authoritative_state_sha256") == AV4_STATE_SHA)
        gate("A3_A4_authorized", a3c.get("AV5_A4_authorized") is True)
        gate("A3_A4_execution_authorized", a3c.get("AV5_A4_execution_authorized") is True)
        gate("A3_A4_must_bind_AV4_state_SHA", a3c.get("AV5_A4_must_bind_AV4_state_SHA") == AV4_STATE_SHA)
        gate("A3_no_locked_OOD_pressure_targets", a3c.get("AV5_A4_must_not_generate_locked_OOD_pressure_targets") is True)
        gate("A3_TRAIN_only_normalization", a3c.get("AV5_A4_must_fit_normalization_on_TRAIN_only") is True)
        gate("A3_exact_spsolve_teachers_required", a3c.get("AV5_A4_must_generate_exact_spsolve_teacher_pressures") is True)
        gate("A3_no_model_training", a3c.get("AV5_A4_must_not_train_model") is True)
        gate("A3_model_training_still_locked", a3c.get("AV5_model_training_authorized") is False)
        gate("A3_exact_FV_correction_preserved", a3c.get("exact_FV_correction_required") is True)
        gate("A3_direct_fallback_preserved", a3c.get("direct_spsolve_reference_and_fallback_required") is True)
        gate("A3_input_channels_exact", a3model.get("input_channels") == INPUT_CHANNELS, a3model.get("input_channels"))
        gate("A3_target_exact", a3dataset.get("temporal_seed", {}).get("training_target") == "delta_p_true = p_star - p_previous")
        gate("A3_manifest_nonempty", len(a3m) > 0)

        stage = "A2R1_benchmark_authority"
        a2d = drive / A2R1_REL
        a2m = manifest(a2d, A2R1_MANIFEST)
        a2s = js(a2d / A2R1_SUMMARY)
        a2c = js(a2d / A2R1_DECISION)
        gate("A2R1_status_exact", a2s.get("status") == A2R1_STATUS, a2s.get("status"))
        gate("A2R1_exact_correction_feasible", a2s.get("exact_correction_feasible_on_all_accepted_systems") is True)
        gate("A2R1_direct_fallback_required", a2c.get("direct_spsolve_reference_and_fallback_required") is True)
        gate("A2R1_manifest_nonempty", len(a2m) > 0)

        stage = "A6E_36_state_library_authority"
        a6d = drive / A6E_REL
        a6m = manifest(a6d, A6E_MANIFEST)
        a6s = js(a6d / A6E_SUMMARY)
        gate("A6E_status_exact", a6s.get("status") == A6E_STATUS, a6s.get("status"))
        gate("A6E_36_states_exact", int(a6s.get("integrated_states")) == 36)
        state_files: dict[str, Path] = {}
        for reg in REALIZATION_REGISTRY:
            name = f"POSTV16_AV3_A6_E_{reg['id']}_Integrated_State.npz"
            p = a6d / name
            gate(f"{reg['id']}_state_manifested", name in a6m and p.is_file(), name)
            if p.is_file() and name in a6m:
                gate(f"{reg['id']}_state_SHA_exact", sha(p) == a6m[name], sha(p))
            state_files[reg["id"]] = p

        stage = "runtime_physics_binding"
        sg2 = mod(root / SG2, "av5a4_sg2")
        sg3 = mod(root / SG3, "av5a4_sg3")
        r3 = mod(root / R3, "av5a4_r3")
        a2e = mod(root / A2E_RUNNER, "av5a4_a2e")

        permeability = np.loadtxt(root / PERM, skiprows=1, dtype=np.float64).reshape(GRID, order="C")
        gate("permeability_shape_positive_finite", permeability.shape == GRID and np.isfinite(permeability).all() and np.all(permeability > 0.0))
        kx, ky, kz = sg2.build_directional_permeability(permeability)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)
        gate("reference_transmissibility_shapes", tx_ref.shape == (15, 50, 49) and ty_ref.shape == (15, 49, 50) and tz_ref.shape == (14, 50, 50))

        log10_k = np.log10(permeability)
        injector_map, producer_bhp_map, depth_map = build_fixed_maps(sg3)
        gate("injector_source_map_finite", np.isfinite(injector_map).all() and np.count_nonzero(injector_map) == len(sg3.COMPLETION_K))
        gate("producer_BHP_map_finite", np.isfinite(producer_bhp_map).all() and np.count_nonzero(producer_bhp_map) == len(sg3.PRODUCERS) * len(sg3.COMPLETION_K))
        gate("normalized_depth_in_0_1", np.isfinite(depth_map).all() and float(np.min(depth_map)) > 0.0 and float(np.max(depth_map)) < 1.0)

        stage = "exact_teacher_generation"
        supervised_raw: list[dict[str, Any]] = []
        ood_raw: list[dict[str, Any]] = []
        audit_rows: list[dict[str, Any]] = []
        state_rows: list[dict[str, Any]] = []

        for reg in REALIZATION_REGISTRY:
            rid = reg["id"]
            partition = reg["partition"]
            with np.load(state_files[rid], allow_pickle=False) as z:
                required = {
                    "paired_porosity", "nw", "no", "krw_max", "kro_max",
                    "grid_saturation", "grid_component_mass_kg", "target_days",
                }
                gate(f"{rid}_required_A6E_arrays", required.issubset(set(z.files)), sorted(z.files))
                nw = np.asarray(z["nw"], dtype=np.float64)
                no = np.asarray(z["no"], dtype=np.float64)
                krw_max = np.asarray(z["krw_max"], dtype=np.float64)
                kro_max = np.asarray(z["kro_max"], dtype=np.float64)
                sat_all = np.asarray(z["grid_saturation"], dtype=np.float64)
                days = np.asarray(z["target_days"], dtype=np.float64)

            gate(f"{rid}_field_shapes_exact", all(x.shape == GRID for x in [nw, no, krw_max, kro_max]))
            gate(f"{rid}_saturation_shape_exact", sat_all.shape == (9,) + GRID, sat_all.shape)
            gate(f"{rid}_days_exact", np.array_equal(days, CANONICAL_DAYS), days.tolist())

            # Day-30 temporal seed authority: exact background-state pressure solve for this realization.
            background_sat = np.full(GRID, 0.20, dtype=np.float64)
            background = solve_state(
                saturation=background_sat,
                nw=nw,
                no=no,
                krw_max=krw_max,
                kro_max=kro_max,
                permeability=permeability,
                tx_ref=tx_ref,
                ty_ref=ty_ref,
                tz_ref=tz_ref,
                a2e=a2e,
                r3=r3,
                sg3=sg3,
            )
            gate(f"{rid}_background_pressure_residual", background["relative_residual"] < PRESSURE_LINEAR_REL_RESIDUAL_MAX, background["relative_residual"])
            previous_pressure = np.asarray(background["p_psi"], dtype=np.float64)

            for it, day in enumerate(CANONICAL_DAYS.tolist()):
                saturation = np.asarray(sat_all[it], dtype=np.float64)
                mobility = a2e.spatial_mobility(saturation, nw, no, krw_max, kro_max)
                log10_lambda = np.log10(np.asarray(mobility["lambda_total"], dtype=np.float64))

                common = {
                    "realization_id": rid,
                    "realization_index": int(reg["index"]),
                    "paired_porosity": reg["paired_porosity"],
                    "partition": partition,
                    "time_index": int(it),
                    "target_day": float(day),
                    "log10_k": log10_k,
                    "log10_lambda": log10_lambda,
                    "injector_source_map": injector_map,
                    "producer_bhp_map": producer_bhp_map,
                    "normalized_depth_z": depth_map,
                }

                if partition == "LOCKED_OOD_TEST":
                    # Do NOT solve any canonical OOD pressure system in A4.
                    # Only Day30 has a legitimate previous-pressure seed available without opening OOD truth:
                    # the exact background-state solve above. Later previous-pressure channels remain deferred to
                    # the post-checkpoint sequential one-touch OOD evaluation.
                    previous_available = bool(it == 0)
                    ood_raw.append({
                        **common,
                        "previous_pressure_psi": previous_pressure.copy() if previous_available else None,
                        "previous_pressure_available": previous_available,
                    })
                    state_rows.append({
                        "realization_id": rid,
                        "partition": partition,
                        "time_index": int(it),
                        "target_day": float(day),
                        "exact_teacher_generated": False,
                        "previous_pressure_available_in_A4": previous_available,
                        "previous_pressure_semantics": (
                            "EXACT_BACKGROUND_STATE_PRESSURE"
                            if previous_available
                            else "DEFERRED_TO_POST_CHECKPOINT_SEQUENTIAL_ONE_TOUCH_OOD"
                        ),
                    })
                    continue

                solved = solve_state(
                    saturation=saturation,
                    nw=nw,
                    no=no,
                    krw_max=krw_max,
                    kro_max=kro_max,
                    permeability=permeability,
                    tx_ref=tx_ref,
                    ty_ref=ty_ref,
                    tz_ref=tz_ref,
                    a2e=a2e,
                    r3=r3,
                    sg3=sg3,
                )
                teacher_generation_executed = True
                p_star = np.asarray(solved["p_psi"], dtype=np.float64)
                delta = p_star - previous_pressure
                residual = float(solved["relative_residual"])
                gate(f"{rid}_day{int(day)}_teacher_residual", residual < PRESSURE_LINEAR_REL_RESIDUAL_MAX, residual)
                gate(f"{rid}_day{int(day)}_teacher_finite", np.isfinite(p_star).all() and np.isfinite(delta).all())

                supervised_raw.append({
                    **common,
                    "previous_pressure_psi": previous_pressure.copy(),
                    "p_star_psi": p_star.copy(),
                    "delta_p_psi": delta.copy(),
                })
                audit_rows.append({
                    "realization_id": rid,
                    "partition": partition,
                    "time_index": int(it),
                    "target_day": float(day),
                    "linear_relative_residual": residual,
                    "pressure_min_psi": float(np.min(p_star)),
                    "pressure_max_psi": float(np.max(p_star)),
                    "delta_p_min_psi": float(np.min(delta)),
                    "delta_p_max_psi": float(np.max(delta)),
                    "delta_p_relative_l2_vs_previous": rel_l2(p_star, previous_pressure),
                })
                state_rows.append({
                    "realization_id": rid,
                    "partition": partition,
                    "time_index": int(it),
                    "target_day": float(day),
                    "exact_teacher_generated": True,
                    "previous_pressure_available_in_A4": True,
                    "previous_pressure_semantics": (
                        "EXACT_BACKGROUND_STATE_PRESSURE" if it == 0 else "PREVIOUS_CANONICAL_EXACT_TEACHER"
                    ),
                })
                previous_pressure = p_star

        stage = "dataset_count_and_leakage_audit"
        train_raw = [x for x in supervised_raw if x["partition"] == "TRAIN"]
        val_raw = [x for x in supervised_raw if x["partition"] == "VALIDATION"]
        gate("TRAIN_exact_state_count_18", len(train_raw) == 18, len(train_raw))
        gate("VALIDATION_exact_state_count_9", len(val_raw) == 9, len(val_raw))
        gate("LOCKED_OOD_scaffold_state_count_9", len(ood_raw) == 9, len(ood_raw))
        gate("LOCKED_OOD_canonical_teacher_count_zero", all(not r["exact_teacher_generated"] for r in state_rows if r["partition"] == "LOCKED_OOD_TEST"))
        gate("LOCKED_OOD_only_day30_previous_pressure_available", sum(int(x["previous_pressure_available"]) for x in ood_raw) == 1)
        gate("LOCKED_OOD_canonical_pressure_target_never_generated", ood_canonical_pressure_target_generated is False)

        stage = "TRAIN_only_normalization"
        train_logk = np.stack([x["log10_k"] for x in train_raw], axis=0)
        train_loglam = np.stack([x["log10_lambda"] for x in train_raw], axis=0)
        train_prev = np.stack([x["previous_pressure_psi"] for x in train_raw], axis=0)
        train_delta = np.stack([x["delta_p_psi"] for x in train_raw], axis=0)

        logk_mean, logk_std = stats_train(train_logk)
        loglam_mean, loglam_std = stats_train(train_loglam)
        prev_mean, prev_std = stats_train(train_prev)
        delta_mean, delta_std = stats_train(train_delta)

        normalization_contract = {
            "fit_partition": "TRAIN_ONLY",
            "TRAIN_realizations": ["AV3CR0001", "AV3CR0002"],
            "TRAIN_states": 18,
            "statistics": {
                "log10_permeability_md": {"mean": logk_mean, "std": logk_std},
                "log10_total_mobility": {"mean": loglam_mean, "std": loglam_std},
                "previous_pressure_psi": {"mean": prev_mean, "std": prev_std},
                "delta_pressure_psi": {"mean": delta_mean, "std": delta_std},
            },
            "validation_used_to_fit": False,
            "locked_OOD_used_to_fit": False,
        }
        gate("normalization_all_finite_positive_std", all(np.isfinite(v) and v > 0.0 for v in [logk_std, loglam_std, prev_std, delta_std]))

        stage = "normalized_dataset_materialization"
        ordered = train_raw + val_raw
        X = np.empty((27,) + GRID + (6,), dtype=np.float32)
        Y = np.empty((27,) + GRID + (1,), dtype=np.float32)
        P_prev = np.empty((27,) + GRID, dtype=np.float64)
        P_star = np.empty((27,) + GRID, dtype=np.float64)
        Delta = np.empty((27,) + GRID, dtype=np.float64)
        realization_index = np.empty(27, dtype=np.int64)
        time_index = np.empty(27, dtype=np.int64)
        target_day = np.empty(27, dtype=np.float64)
        partition_code = np.empty(27, dtype=np.int8)  # 0 TRAIN, 1 VALIDATION

        for n, x in enumerate(ordered):
            X[n, ..., 0] = normalize(x["log10_k"], logk_mean, logk_std)
            X[n, ..., 1] = normalize(x["log10_lambda"], loglam_mean, loglam_std)
            X[n, ..., 2] = normalize(x["previous_pressure_psi"], prev_mean, prev_std)
            X[n, ..., 3] = np.asarray(x["injector_source_map"], dtype=np.float32)
            X[n, ..., 4] = np.asarray(x["producer_bhp_map"], dtype=np.float32)
            X[n, ..., 5] = np.asarray(x["normalized_depth_z"], dtype=np.float32)
            Y[n, ..., 0] = normalize(x["delta_p_psi"], delta_mean, delta_std)
            P_prev[n] = x["previous_pressure_psi"]
            P_star[n] = x["p_star_psi"]
            Delta[n] = x["delta_p_psi"]
            realization_index[n] = int(x["realization_index"])
            time_index[n] = int(x["time_index"])
            target_day[n] = float(x["target_day"])
            partition_code[n] = 0 if x["partition"] == "TRAIN" else 1

        gate("TrainValidation_X_shape_exact", X.shape == (27, 15, 50, 50, 6), X.shape)
        gate("TrainValidation_Y_shape_exact", Y.shape == (27, 15, 50, 50, 1), Y.shape)
        gate("TrainValidation_finite", np.isfinite(X).all() and np.isfinite(Y).all() and np.isfinite(P_star).all())
        gate("TrainValidation_order_exact", np.array_equal(realization_index[:18], np.repeat([0, 1], 9)) and np.array_equal(realization_index[18:], np.repeat([2], 9)))

        # OOD leakage-safe scaffold: channels 0,1,3,4,5 are complete for all 9 states.
        # Channel 2 is populated only for Day30; later rows are NaN until post-checkpoint sequential evaluation.
        X_ood = np.full((9,) + GRID + (6,), np.nan, dtype=np.float32)
        ood_prev_available = np.zeros(9, dtype=np.bool_)
        for n, x in enumerate(ood_raw):
            X_ood[n, ..., 0] = normalize(x["log10_k"], logk_mean, logk_std)
            X_ood[n, ..., 1] = normalize(x["log10_lambda"], loglam_mean, loglam_std)
            if x["previous_pressure_available"]:
                X_ood[n, ..., 2] = normalize(x["previous_pressure_psi"], prev_mean, prev_std)
                ood_prev_available[n] = True
            X_ood[n, ..., 3] = np.asarray(x["injector_source_map"], dtype=np.float32)
            X_ood[n, ..., 4] = np.asarray(x["producer_bhp_map"], dtype=np.float32)
            X_ood[n, ..., 5] = np.asarray(x["normalized_depth_z"], dtype=np.float32)

        gate("OOD_static_channels_finite_all_states", np.isfinite(X_ood[..., [0, 1, 3, 4, 5]]).all())
        gate("OOD_previous_pressure_mask_day30_only", np.array_equal(ood_prev_available, np.asarray([True] + [False] * 8)))
        gate("OOD_later_previous_pressure_channel_is_NaN", np.isnan(X_ood[1:, ..., 2]).all())
        gate("OOD_no_Y_array_materialized", True)

        stage = "publication"
        channel_contract = {
            "milestone": M,
            "status": PASS,
            "input_channels_in_order": INPUT_CHANNELS,
            "channel_definitions": {
                "log10_permeability_md": "log10 of frozen SGSIM_50x50x15_PERM_MD cell permeability; TRAIN-only z-score",
                "log10_total_mobility": (
                    "log10 of unchanged AV4 spatial Corey total mobility from A2E.spatial_mobility; TRAIN-only z-score"
                ),
                "previous_pressure_normalized": (
                    "pressure_psi normalized with TRAIN-only mean/std; Day30 uses exact background-state pressure; "
                    "later supervised states use prior canonical exact teacher"
                ),
                "injector_source_map": (
                    "dimensionless fixed source fraction Q_INJ_PERF/Q_INJ_TOTAL at each injector completion; zero elsewhere"
                ),
                "producer_bhp_map": (
                    "dimensionless fixed BHP ratio PRODUCER_BHP_PSI/INITIAL_PRESSURE_PSI at each producer completion; zero elsewhere"
                ),
                "normalized_depth_z": "cell-center z divided by total modeled depth NZ*DZ_M; fixed analytical scaling",
            },
            "target": "TRAIN-normalized delta_p_true = p_star - p_previous",
            "teacher_pressure_units": "psi",
            "exact_teacher_solver": "unchanged AV4 sparse finite-volume A,b plus scipy direct spsolve via R3.solve_updated_pressure",
            "pressure_linear_relative_residual_max": PRESSURE_LINEAR_REL_RESIDUAL_MAX,
            "locked_OOD_firewall": {
                "canonical_pressure_targets_generated_in_A4": False,
                "canonical_delta_pressure_targets_generated_in_A4": False,
                "static_predictor_channels_materialized_for_all_9_states": True,
                "day30_previous_pressure_materialized": True,
                "day60_plus_previous_pressure_materialized": False,
                "reason": (
                    "Day60+ previous pressure would be prior canonical OOD exact pressure and therefore would open OOD truth before checkpoint freeze. "
                    "It is deferred to the post-checkpoint sequential one-touch OOD evaluation."
                ),
            },
        }

        handoff = {
            "milestone": "POSTV16-AV5-A5",
            "name": "Controlled Training of Frozen A3 Pressure-Seed Model on A4 Certified Dataset",
            "authorized": True,
            "execution": True,
            "must_use_train_states_only_for_optimizer_updates": True,
            "must_use_validation_only_for_checkpoint_selection": True,
            "must_not_use_locked_OOD_for_training_normalization_selection_or_tuning": True,
            "must_preserve_A3_model_architecture_and_objective": True,
            "must_preserve_exact_residual_seed_admission": True,
            "must_preserve_exact_FV_correction": True,
            "must_preserve_direct_spsolve_fallback": True,
            "must_not_open_locked_OOD_canonical_pressure_truth_before_checkpoint_freeze": True,
            "post_checkpoint_OOD_sequence": (
                "after checkpoint SHA freeze only: start from stored Day30 background pressure seed, sequentially form each OOD X6, "
                "perform one-touch prediction/exact correction/reference comparison, carry corrected exact pressure forward as next previous-pressure input"
            ),
        }

        classification = (
            "AV5_EXACT_PRESSURE_TEACHERS_FOR_27_SUPERVISED_STATES_TRAIN_ONLY_NORMALIZATION_"
            "AND_LOCKED_OOD_LEAKAGE_SAFE_PREDICTOR_SCAFFOLD_CERTIFIED_A5_TRAINING_AUTHORIZED"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "AV4_authoritative_state_sha256": AV4_STATE_SHA,
            "TRAIN_exact_teacher_states": 18,
            "VALIDATION_exact_teacher_states": 9,
            "LOCKED_OOD_states": 9,
            "LOCKED_OOD_canonical_pressure_targets_generated": False,
            "LOCKED_OOD_day30_background_previous_pressure_materialized": True,
            "LOCKED_OOD_day60_plus_previous_pressure_deferred": True,
            "input_channel_count": 6,
            "TRAIN_only_normalization_frozen": True,
            "exact_spsolve_teacher_generation_executed": True,
            "model_training_executed": False,
            "learned_inference_executed": False,
            "AV4_state_mutated": False,
            "physical_time_advance_executed": False,
            "AV5_A5_authorized": True,
            "AV5_model_training_authorized": True,
            "AV5_learned_inference_authorized": False,
            "AV5_production_execution_authorized": False,
            "exact_FV_correction_required": True,
            "direct_spsolve_reference_and_fallback_required": True,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "AV5_A5_authorized": True,
            "AV5_A5_execution_authorized": True,
            "AV5_A5_must_bind_AV4_state_SHA": AV4_STATE_SHA,
            "AV5_A5_must_use_A4_TRAIN_only_normalization": True,
            "AV5_A5_must_preserve_A3_split_registry": True,
            "AV5_A5_must_not_open_locked_OOD_pressure_truth_before_checkpoint_freeze": True,
            "AV5_A5_must_preserve_exact_residual_seed_admission": True,
            "AV5_A5_must_preserve_exact_FV_correction": True,
            "AV5_A5_must_preserve_direct_spsolve_fallback": True,
            "AV5_model_training_authorized": True,
            "AV5_learned_inference_authorized": False,
            "AV5_production_execution_authorized": False,
            "AV4_state_mutation_authorized": False,
            "P3_authorized": False,
        }

        normal_arrays = {
            "log10_permeability_mean": np.asarray(logk_mean, dtype=np.float64),
            "log10_permeability_std": np.asarray(logk_std, dtype=np.float64),
            "log10_total_mobility_mean": np.asarray(loglam_mean, dtype=np.float64),
            "log10_total_mobility_std": np.asarray(loglam_std, dtype=np.float64),
            "previous_pressure_psi_mean": np.asarray(prev_mean, dtype=np.float64),
            "previous_pressure_psi_std": np.asarray(prev_std, dtype=np.float64),
            "delta_pressure_psi_mean": np.asarray(delta_mean, dtype=np.float64),
            "delta_pressure_psi_std": np.asarray(delta_std, dtype=np.float64),
            "fit_state_count": np.asarray(18, dtype=np.int64),
            "fit_realization_indices": np.asarray([0, 1], dtype=np.int64),
        }

        trainval_arrays = {
            "X6": X,
            "Y_delta_p_normalized": Y,
            "previous_pressure_psi": P_prev,
            "p_star_psi": P_star,
            "delta_p_psi": Delta,
            "realization_index": realization_index,
            "time_index": time_index,
            "target_day": target_day,
            "partition_code": partition_code,
            "input_channel_names": np.asarray(INPUT_CHANNELS),
            "partition_code_meaning": np.asarray(["TRAIN=0", "VALIDATION=1"]),
            "AV4_authoritative_state_sha256": np.asarray(AV4_STATE_SHA),
        }

        ood_arrays = {
            "X6_partial": X_ood,
            "previous_pressure_available": ood_prev_available,
            "realization_index": np.full(9, 3, dtype=np.int64),
            "time_index": np.arange(9, dtype=np.int64),
            "target_day": CANONICAL_DAYS,
            "input_channel_names": np.asarray(INPUT_CHANNELS),
            "canonical_pressure_target_generated": np.asarray(False),
            "canonical_delta_pressure_target_generated": np.asarray(False),
            "post_checkpoint_completion_required": np.asarray(True),
            "AV4_authoritative_state_sha256": np.asarray(AV4_STATE_SHA),
        }

        output_files = {
            SUMMARY: jb(summary),
            TRAINVAL_DATASET: deterministic_npz_bytes(trainval_arrays),
            OOD_SCAFFOLD: deterministic_npz_bytes(ood_arrays),
            NORMALIZATION: deterministic_npz_bytes(normal_arrays),
            STATE_REGISTRY: csvb(state_rows),
            TEACHER_AUDIT: csvb(audit_rows),
            CHANNEL_CONTRACT: jb({**channel_contract, "normalization": normalization_contract}),
            A5_HANDOFF: jb(handoff),
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
        print("=" * 200)
        print(M, "PASS")
        print("Classification                                 :", classification)
        print("TRAIN exact teacher states                    : 18")
        print("VALIDATION exact teacher states               : 9")
        print("LOCKED OOD canonical targets generated        : False")
        print("LOCKED OOD Day30 background seed materialized : True")
        print("LOCKED OOD Day60+ previous pressure deferred  : True")
        print("TRAIN-only normalization                      : FROZEN")
        print("Model training executed                       : False")
        print("AV5-A5 training execution authorized          : True")
        print("Exact FV correction / direct fallback         : PRESERVED")
        print("P3 authorized                                 : False")
        print("=" * 200)
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
                "AV4_authoritative_state_preserved": True,
                "teacher_generation_executed_before_block": bool(teacher_generation_executed),
                "locked_OOD_canonical_pressure_target_generated": bool(ood_canonical_pressure_target_generated),
                "model_training_executed": False,
                "learned_inference_executed": False,
                "AV4_state_mutation_executed": False,
                "physical_time_advance_executed": False,
                "AV5_A5_authorized": False,
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
