#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, io, json, subprocess
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV5-A3"
NAME = "Teacher Dataset / Split / Pressure-Seed Model / Objective Design Freeze"

PASS = (
    "POSTV16AV5A3_TEACHER_DATASET_SPLIT_PRESSURE_SEED_MODEL_OBJECTIVE_"
    "DESIGN_FREEZE_PASS_NO_TEACHER_GENERATION_NO_TRAINING"
)
BLOCK = "POSTV16AV5A3_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "9cfd1c05a1ed276a3b674edfaa3485e8f4cddfc9"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
BASE_AV5 = Path("post_v16") / RID / "POSTV16_AV5_Learned_Acceleration"

AV4_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"
GRID = [15, 50, 50]
CANONICAL_DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]

# A2-R1 benchmark authority.
A2R1_TOKEN = "POSTV16_AV5_A2_R1"
A2R1_REL = BASE_AV5 / (
    A2R1_TOKEN + "_AcceptedPressureSystem_ExactCorrection_WarmStart_Benchmark"
)
A2R1_SUMMARY = "PAD_Stream_" + A2R1_TOKEN + "_Summary.json"
A2R1_DECISION = A2R1_TOKEN + "_Decision_Contract.json"
A2R1_MANIFEST = A2R1_TOKEN + "_Artifact_Manifest.csv"
A2R1_STATUS = (
    "POSTV16AV5A2R1_ACCEPTED_PRESSURE_SYSTEM_EXACT_CORRECTION_"
    "WARM_START_BENCHMARK_PASS_NO_ML_NO_STATE_MUTATION"
)
A2R1_CLASS = (
    "ACCEPTED_DAY365_AND_DAY375_PRESSURE_SYSTEMS_SUPPORT_EXACT_"
    "WARM_START_CORRECTION_AND_SEED_ACCELERATION_OPPORTUNITY_"
    "AV5_A3_DESIGN_MAY_PROCEED"
)
A2R1_RUNNER = "PAD_Stream_POSTV16_AV5_A2_R1_AcceptedPressureSystem_ExactCorrection_WarmStart_Benchmark.py"
A2R1_RUNNER_BLOB = "d7009cc9b80b6d553c6d68d3ffcaf4ef22b74a67"

# AV3 split/design source.
AV3A1 = "PAD_Stream_POSTV16_AV3_A1_Corey_Relperm_Parameter_Field_Model_and_Split_Registry_Freeze.py"
AV3A1_BLOB = "fb3b77b89ab3d1b12a09f967a476c4ecfcda0e33"

# 36-state physical-state library.
A6E = "PAD_Stream_POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution.py"
A6E_BLOB = "e3dcb0aa9354c399904f7f0e830b6a1fddd78987"
A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_SUMMARY = "PAD_Stream_POSTV16_AV3_A6_E_Summary.json"
A6E_MANIFEST = "POSTV16_AV3_A6_E_Artifact_Manifest.csv"
A6E_STATUS = (
    "AV3A6E_FROZEN_EPOCH92_CHECKPOINT_LOCAL_PORE_VOLUME_R7D_TERMINAL_HALO_"
    "INTEGRATION_ALL_4_REALIZATIONS_ALL_9_TIMES_PASS"
)

# Pressure system sources.
R3 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3_BLOB = "740c6da03e73906646bf0153633187e749449f31"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    A2R1_RUNNER: A2R1_RUNNER_BLOB,
    AV3A1: AV3A1_BLOB,
    A6E: A6E_BLOB,
    R3: R3_BLOB,
    SG3: SG3_BLOB,
    PERM: PERM_BLOB,
}

REALIZATION_REGISTRY = [
    {"id": "AV3CR0001", "partition": "TRAIN", "paired_porosity": "AV2PHI0001"},
    {"id": "AV3CR0002", "partition": "TRAIN", "paired_porosity": "AV2PHI0002"},
    {"id": "AV3CR0003", "partition": "VALIDATION", "paired_porosity": "AV2PHI0003"},
    {"id": "AV3CR0004", "partition": "LOCKED_OOD_TEST", "paired_porosity": "AV2PHI0004"},
]

INPUT_CHANNELS = [
    "log10_permeability_md",
    "log10_total_mobility",
    "previous_pressure_normalized",
    "injector_source_map",
    "producer_bhp_map",
    "normalized_depth_z",
]

DILATION_SCHEDULE = [1, 2, 4, 8, 4, 2]
FEATURE_WIDTH = 32
RESIDUAL_BLOCKS = len(DILATION_SCHEDULE)

OUT_TOKEN = "POSTV16_AV5_A3"
OUT_REL = BASE_AV5 / (
    OUT_TOKEN + "_TeacherDataset_Split_PressureSeed_Model_Objective_Design_Freeze"
)
BLOCK_REL = BASE_AV5 / (OUT_TOKEN + "_BLOCKED")


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
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
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> dict[str, str]:
    result = {}
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


def selftest():
    parts = [r["partition"] for r in REALIZATION_REGISTRY]
    assert parts.count("TRAIN") == 2
    assert parts.count("VALIDATION") == 1
    assert parts.count("LOCKED_OOD_TEST") == 1
    assert len(CANONICAL_DAYS) == 9
    assert len(INPUT_CHANNELS) == 6
    assert RESIDUAL_BLOCKS == 6
    assert DILATION_SCHEDULE == [1, 2, 4, 8, 4, 2]
    print("POSTV16 AV5-A3 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None):
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
        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_exact", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "A2R1_benchmark_authority"
        a2d = drive / A2R1_REL
        a2m = manifest(a2d, A2R1_MANIFEST)
        a2s = js(a2d / A2R1_SUMMARY)
        a2c = js(a2d / A2R1_DECISION)
        gate("A2R1_status_exact", a2s.get("status") == A2R1_STATUS, a2s.get("status"))
        gate("A2R1_class_exact", a2s.get("classification") == A2R1_CLASS, a2s.get("classification"))
        gate("A2R1_exact_correction_feasible",
             a2s.get("exact_correction_feasible_on_all_accepted_systems") is True)
        gate("A2R1_learned_seed_opportunity",
             a2s.get("learned_seed_opportunity_demonstrated") is True)
        gate("A2R1_A3_authorized", a2c.get("AV5_A3_authorized") is True)
        gate("A2R1_A3_execution_authorized", a2c.get("AV5_A3_execution_authorized") is True)
        gate("A2R1_AV4_state_binding_exact",
             a2c.get("AV5_A3_must_bind_AV4_state_SHA") == AV4_STATE_SHA)
        gate("A2R1_training_still_locked", a2c.get("AV5_model_training_authorized") is False)
        gate("A2R1_direct_fallback_required",
             a2c.get("direct_spsolve_reference_and_fallback_required") is True)
        gate("A2R1_exact_FV_correction_required", a2c.get("exact_FV_correction_required") is True)
        gate("A2R1_manifest_nonempty", len(a2m) > 0)

        stage = "A6E_36_state_library_authority"
        a6d = drive / A6E_REL
        a6m = manifest(a6d, A6E_MANIFEST)
        a6s = js(a6d / A6E_SUMMARY)
        gate("A6E_status_exact", a6s.get("status") == A6E_STATUS, a6s.get("status"))
        gate("A6E_36_states_exact", int(a6s.get("integrated_states")) == 36)
        expected_state_files = [
            f"POSTV16_AV3_A6_E_{r['id']}_Integrated_State.npz"
            for r in REALIZATION_REGISTRY
        ]
        gate("A6E_all_four_state_files_manifested",
             all(name in a6m for name in expected_state_files), expected_state_files)

        for reg, name in zip(REALIZATION_REGISTRY, expected_state_files):
            p = a6d / name
            gate(f"{reg['id']}_state_present", p.is_file(), str(p))
            with np.load(p, allow_pickle=False) as z:
                required = {
                    "paired_porosity", "nw", "no", "krw_max", "kro_max",
                    "grid_saturation", "grid_component_mass_kg", "target_days",
                }
                gate(f"{reg['id']}_required_arrays", required.issubset(set(z.files)), sorted(z.files))
                gate(f"{reg['id']}_grid_saturation_shape",
                     np.asarray(z["grid_saturation"]).shape == (9, 15, 50, 50),
                     np.asarray(z["grid_saturation"]).shape)
                gate(f"{reg['id']}_target_days_exact",
                     np.array_equal(np.asarray(z["target_days"], dtype=float), np.asarray(CANONICAL_DAYS)))

        stage = "pressure_equation_feature_audit"
        r3_text = (root / R3).read_text(encoding="utf-8")
        sg3_text = (root / SG3).read_text(encoding="utf-8")
        gate("pressure_system_uses_total_mobility",
             "lambda_total" in r3_text and "assemble_updated_pressure_system" in r3_text)
        gate("pressure_system_uses_permeability",
             "k_cell_md" in r3_text and "peaceman_well_index_si" in r3_text)
        gate("pressure_system_has_fixed_injector_source",
             "Q_INJ_PERF_M3_S" in r3_text and "INJECTOR_I" in sg3_text)
        gate("pressure_system_has_producer_BHP",
             "PRODUCER_BHP_PA" in r3_text and "PRODUCERS" in sg3_text)
        gate("pressure_system_includes_gravity_depth",
             "RHO_BRINE_KG_M3" in r3_text and "cell_center_z_m" in r3_text)

        stage = "dataset_split_freeze"
        train_ids = [r["id"] for r in REALIZATION_REGISTRY if r["partition"] == "TRAIN"]
        val_ids = [r["id"] for r in REALIZATION_REGISTRY if r["partition"] == "VALIDATION"]
        ood_ids = [r["id"] for r in REALIZATION_REGISTRY if r["partition"] == "LOCKED_OOD_TEST"]
        gate("split_exact_2train_1val_1lockedOOD",
             train_ids == ["AV3CR0001", "AV3CR0002"]
             and val_ids == ["AV3CR0003"]
             and ood_ids == ["AV3CR0004"])
        gate("train_state_count_18", len(train_ids) * len(CANONICAL_DAYS) == 18)
        gate("validation_state_count_9", len(val_ids) * len(CANONICAL_DAYS) == 9)
        gate("locked_OOD_state_count_9", len(ood_ids) * len(CANONICAL_DAYS) == 9)

        stage = "model_and_objective_freeze"
        dataset_contract = {
            "source_state_library": "POSTV16_AV3_A6_E 36-state integrated library",
            "sample_unit": "one complete 15x50x50 pressure system; no random cell or patch split",
            "partitions": {
                "TRAIN": {
                    "realizations": train_ids,
                    "states": 18,
                    "teacher_pressure_generation": "authorized in A4",
                },
                "VALIDATION": {
                    "realizations": val_ids,
                    "states": 9,
                    "teacher_pressure_generation": "authorized in A4",
                },
                "LOCKED_OOD_TEST": {
                    "realizations": ood_ids,
                    "states": 9,
                    "teacher_pressure_generation": (
                        "forbidden in A4; predictor inputs may be materialized, but exact OOD pressure "
                        "targets remain sealed until after checkpoint freeze"
                    ),
                },
            },
            "canonical_days": CANONICAL_DAYS,
            "teacher_system": (
                "for each frozen grid-saturation snapshot, compute exact total mobility, assemble the "
                "unchanged AV4 finite-volume A,b, and solve exact p_star with direct spsolve"
            ),
            "temporal_seed": {
                "day30": (
                    "exact background-state pressure solve for the same realization using the frozen "
                    "well controls and constitutive fields"
                ),
                "days_after_30": "previous canonical exact teacher pressure from the same realization",
                "training_target": "delta_p_true = p_star - p_previous",
            },
            "normalization": {
                "fit_on": "TRAIN only",
                "input_scalars": [
                    "log10_permeability_md mean/std",
                    "log10_total_mobility mean/std",
                    "previous_pressure_psi mean/std",
                ],
                "target": (
                    "delta pressure is centered/scaled using TRAIN-only mean and standard deviation; "
                    "numeric statistics are computed once in A4 and frozen before any validation/OOD use"
                ),
                "never_refit_on_validation_or_OOD": True,
            },
            "leakage_firewalls": [
                "no random voxel/cell split",
                "no state from AV3CR0003 in training",
                "no AV3CR0004 target pressure generation before checkpoint freeze",
                "no normalization statistics from validation or OOD",
                "no hyperparameter selection from OOD",
            ],
        }

        model_contract = {
            "model_role": "non-authoritative pressure-correction seed predictor",
            "input_shape": [15, 50, 50, len(INPUT_CHANNELS)],
            "input_channels": INPUT_CHANNELS,
            "output_shape": [15, 50, 50, 1],
            "output": "normalized delta_p_pred",
            "pressure_seed": "p_hat = p_previous + inverse_normalize(delta_p_pred)",
            "architecture": {
                "family": "3D residual dilated convolutional network",
                "feature_width": FEATURE_WIDTH,
                "stem": "Conv3D(32, kernel=3, dilation=1, padding='same') + GELU",
                "residual_blocks": RESIDUAL_BLOCKS,
                "dilation_schedule": DILATION_SCHEDULE,
                "block": (
                    "Conv3D(32,3,dilation=d,same,bias=False) -> LayerNorm(channel) -> GELU -> "
                    "Conv3D(32,3,dilation=d,same,bias=False) -> LayerNorm(channel) -> residual add -> GELU"
                ),
                "head": "Conv3D(1, kernel=1, padding='same', activation='linear')",
                "pooling": False,
                "upsampling": False,
                "reason": (
                    "full-grid receptive field through dilation while preserving exact cell alignment "
                    "needed for finite-volume residual correction"
                ),
            },
            "parameter_budget": {
                "maximum_trainable_parameters": 500000,
                "reason": "small 18-volume TRAIN population requires a deliberately compact model",
            },
        }

        objective_contract = {
            "training_objective": {
                "primary": "Huber loss on TRAIN-normalized delta pressure",
                "huber_delta": 1.0,
                "auxiliary": "none in first controlled training",
                "reason": (
                    "exact finite-volume correction, not the neural loss, enforces physics; avoid "
                    "introducing an uncalibrated differentiable A,b residual weight before baseline training"
                ),
            },
            "optimizer": {
                "name": "Adam",
                "initial_learning_rate": 1.0e-3,
                "batch_size_full_volumes": 1,
                "maximum_epochs": 300,
                "early_stopping_patience": 30,
                "early_stopping_min_delta": 1.0e-6,
                "reduce_lr_factor": 0.5,
                "reduce_lr_patience": 10,
                "minimum_learning_rate": 1.0e-6,
                "random_seed": 260501,
            },
            "checkpoint_selection": {
                "primary": "minimum VALIDATION median exact-correction Krylov iteration count",
                "secondary": "minimum VALIDATION mean exact-correction Krylov iteration count",
                "tertiary": "minimum VALIDATION normalized delta-pressure Huber loss",
                "wall_clock_not_used_for_checkpoint_selection": True,
                "reason": "iteration count is deterministic; wall time is hardware/noise dependent",
            },
        }

        runtime_contract = {
            "proposal": "learned p_hat from frozen model",
            "exact_initial_residual": "r_hat = b - A*p_hat",
            "temporal_initial_residual": "r_prev = b - A*p_previous",
            "seed_admission_rule": (
                "use learned seed only when ||r_hat||_2 < ||r_prev||_2; otherwise use p_previous"
            ),
            "correction": "solve A*delta_p = b - A*p_selected with frozen exact Krylov policy",
            "corrected_pressure": "p_corrected = p_selected + delta_p",
            "science_acceptance": "unchanged AV4 ||A*p_corrected-b||/||b|| < 1e-8 plus downstream gates",
            "fallback": (
                "if iterative correction fails/stagnates or violates any gate, use direct spsolve(A,b)"
            ),
            "learned_pressure_never_authoritative": True,
            "direct_spsolve_reference_and_fallback_preserved": True,
            "AV4_Darcy_Pollock_TOF_transport_semantics_unchanged": True,
        }

        stage = "publication"
        out.mkdir(parents=True, exist_ok=False)

        classification = (
            "AV5_PRESSURE_SEED_TEACHER_SPLIT_COMPACT_3D_RESIDUAL_DILATED_MODEL_"
            "AND_EXACT_RESIDUAL_ADMISSION_PROTOCOL_FROZEN_A4_DATASET_GENERATION_AUTHORIZED"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "AV4_authoritative_state_sha256": AV4_STATE_SHA,
            "A2R1_benchmark_bound": True,
            "A6E_36_state_library_bound": True,
            "train_realizations": train_ids,
            "validation_realizations": val_ids,
            "locked_OOD_realizations": ood_ids,
            "train_states": 18,
            "validation_states": 9,
            "locked_OOD_states": 9,
            "input_channel_count": len(INPUT_CHANNELS),
            "model_family": model_contract["architecture"]["family"],
            "target": "delta_p_true = p_star - p_previous",
            "learned_seed_exact_residual_admission_required": True,
            "exact_FV_correction_required": True,
            "direct_spsolve_fallback_required": True,
            "teacher_generation_executed": False,
            "model_training_executed": False,
            "learned_inference_executed": False,
            "AV4_state_mutated": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        design = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "teacher_dataset_and_split": dataset_contract,
            "pressure_seed_model": model_contract,
            "training_objective_and_selection": objective_contract,
            "runtime_exact_correction_and_fallback": runtime_contract,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "AV5_A4_authorized": True,
            "AV5_A4_name": "Exact Pressure-Teacher Dataset Generation + TRAIN-Only Normalization + Locked-OOD Predictor Materialization",
            "AV5_A4_execution_authorized": True,
            "AV5_A4_must_bind_AV4_state_SHA": AV4_STATE_SHA,
            "AV5_A4_must_preserve_split_registry": True,
            "AV5_A4_must_not_generate_locked_OOD_pressure_targets": True,
            "AV5_A4_must_fit_normalization_on_TRAIN_only": True,
            "AV5_A4_must_generate_exact_spsolve_teacher_pressures": True,
            "AV5_A4_must_not_train_model": True,
            "AV5_model_training_authorized": False,
            "AV5_learned_inference_authorized": False,
            "AV5_production_execution_authorized": False,
            "exact_FV_correction_required": True,
            "direct_spsolve_reference_and_fallback_required": True,
            "AV4_conservation_gates_unchanged": True,
            "AV4_state_mutation_authorized": False,
            "P3_authorized": False,
        }

        split_rows = []
        for r in REALIZATION_REGISTRY:
            split_rows.append({
                "realization_id": r["id"],
                "paired_porosity": r["paired_porosity"],
                "partition": r["partition"],
                "canonical_state_count": 9,
                "teacher_target_policy": (
                    "GENERATE_IN_A4"
                    if r["partition"] != "LOCKED_OOD_TEST"
                    else "SEALED_UNTIL_POST_CHECKPOINT_ONE_TOUCH_OOD"
                ),
            })

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Teacher_Dataset_and_Leakage_Firewall.json").write_bytes(jb(dataset_contract))
        (out / f"{OUT_TOKEN}_Pressure_Seed_Model_Contract.json").write_bytes(jb(model_contract))
        (out / f"{OUT_TOKEN}_Objective_Checkpoint_Selection_Contract.json").write_bytes(jb(objective_contract))
        (out / f"{OUT_TOKEN}_Exact_Correction_Runtime_Contract.json").write_bytes(jb(runtime_contract))
        (out / f"{OUT_TOKEN}_Realization_Split_Registry.csv").write_bytes(csvb(split_rows))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        man = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                man.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(man))

        print("=" * 200)
        print(M, "PASS")
        print("Classification                         :", classification)
        print("TRAIN realizations                     :", train_ids, "18 states")
        print("VALIDATION realization                 :", val_ids, "9 states")
        print("LOCKED OOD realization                 :", ood_ids, "9 states")
        print("Input channels                         :", INPUT_CHANNELS)
        print("Model                                  : 3D residual dilated CNN")
        print("Dilation schedule                      :", DILATION_SCHEDULE)
        print("Target                                 : delta_p = p_star - p_previous")
        print("Learned residual admission gate        : required")
        print("Exact FV correction                    : required")
        print("Direct spsolve fallback                : required")
        print("AV5-A4 dataset generation authorized   : True")
        print("Model training authorized              : False")
        print("P3 authorized                          : False")
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
                "teacher_generation_executed": False,
                "model_training_executed": False,
                "learned_inference_executed": False,
                "AV4_state_mutation_executed": False,
                "physical_time_advance_executed": False,
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
    a = ap.parse_args()
    if a.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root, a.drive_root))
