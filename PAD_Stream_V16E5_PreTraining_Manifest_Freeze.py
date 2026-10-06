#!/usr/bin/env python3
"""PAD-Stream V16E-5: prospective pre-training manifest freeze.

This milestone performs NO neural-network training and creates NO checkpoint.
It binds the accepted V16E-4-R1 deterministic teacher dataset and freezes the
prospective Hybrid10/Hybrid12 training recipe before any learned-model execution.
The internal-test and OOD partitions remain unavailable for model selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np

MILESTONE = "V16E-5"
REVISION = "R0_PRETRAINING_MANIFEST_FREEZE"
STATUS = (
    "V16E5_PRETRAINING_MANIFEST_FROZEN_"
    "HYBRID10_CONTROLLED_TRAINING_AUTHORIZED_"
    "HYBRID12_RECIPE_FROZEN_EXECUTION_DEFERRED_"
    "INTERNAL_TEST_AND_OOD_REMAIN_SEALED"
)
NEXT = "V16E-6A — Prospective Hybrid10 Controlled Training and Validation"

E4_REL = Path("datasets/hybrid_dp/V16E4_R1_DETERMINISTIC_TEACHER_DATASET")
E5_REL = Path("provenance/hybrid_dp/V16E5_PRETRAINING_MANIFEST_FREEZE")

E4 = {
    "manifest": (
        "V16E4_R1_Dataset_Manifest.json",
        "ec8c50720074f1ebe07be259073e44f5a82e03a45ca1cdc9385402fe280602a7",
    ),
    "audit": (
        "V16E4_R1_Numerical_Audit.json",
        "ca0a6320e773dfee9a405ef23b509101a3862446f541fdf2b17133861b73c16b",
    ),
    "summary": (
        "PAD_Stream_V16E4_R1_Summary.json",
        "85544f6b160025fb534fb9c047a16d05d9bb0bf55a461eb163f5ae924cdedbaf",
    ),
    "handoff": (
        "V16E4_R1_Handoff.md",
        "8e6d14221135cd00e5d4a31d775a02d23709bfa2296757204360ced79bd71790",
    ),
}

E4_RUNNER = (
    "PAD_Stream_V16E4_R1_Deterministic_Hybrid_BL_DP_Teacher_Dataset_Generation_and_Audit.py",
    "9f9fce49d1cad38f83dac046759c4d9cd64115fff19ee916079ed4c8a59120a3",
)
R2_ADAPTER = (
    "PAD_Stream_V16E3_R2_Repaired_BL_Teacher.py",
    "640a853fd0775c5efaf2922976d5c3843fa69ce9e5165245daffefdb3d4eac2a",
)

FEATURES10 = ["no", "nw", "swc", "sor", "mu_w", "mu_o", "phi", "tD", "xD_star", "Sw_star"]
FEATURES12 = FEATURES10[:7] + ["krw_max", "kro_max"] + FEATURES10[7:]

PROHIBITIONS = [
    "NO NEURAL-NETWORK TRAINING.",
    "NO CHECKPOINT CREATION.",
    "NO HISTORICAL HYBRID CHECKPOINT CLAIM.",
    "NO INTERNAL-TEST MODEL SELECTION.",
    "NO OOD REOPENING.",
    "NO SGSim MODIFICATION.",
    "NO POLLOCK/TOF RECOMPUTATION.",
    "NO B4 RETRAINING.",
    "NO DATASET, SPLIT, TEACHER OR TOLERANCE CHANGE.",
    "NO HYPERPARAMETER SEARCH IN V16E-6A.",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False, ensure_ascii=False) + "\n").encode("utf-8")


class FreezeError(RuntimeError):
    pass


class Gates:
    def __init__(self):
        self.items = {}

    def check(self, name, condition, detail=""):
        ok = bool(condition)
        self.items[name] = {"passed": ok, "detail": detail}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)
        if not ok:
            raise FreezeError(name + (": " + detail if detail else ""))


def read_json(path: Path):
    def reject(value):
        raise FreezeError("Nonfinite JSON literal: " + value)
    return json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=reject)


def bind(gates: Gates, label: str, path: Path, expected: str):
    gates.check(label + "_exists", path.is_file(), str(path))
    actual = sha(path)
    gates.check(label + "_SHA_exact", actual == expected,
                "" if actual == expected else f"expected {expected}; actual {actual}")


def expected_param_count(param_dim: int) -> int:
    # RepeatVector and range map have no trainable parameters.
    # LSTM params = 4*u*(input_dim + u + 1).
    u = 64
    first_input = 1 + param_dim
    lstm1 = 4 * u * (first_input + u + 1)
    lstm2 = 4 * u * (u + u + 1)
    dense = u + 1
    return lstm1 + lstm2 + dense


def verify_inventory(gates: Gates, root: Path, manifest: dict):
    artifacts = manifest.get("artifacts")
    gates.check("E4_manifest_artifact_inventory_present", isinstance(artifacts, dict) and bool(artifacts))
    checked = 0
    for rel, meta in sorted(artifacts.items()):
        p = root / rel
        gates.check(f"artifact_{checked:02d}_exists", p.is_file(), rel)
        expected = meta.get("sha256")
        gates.check(f"artifact_{checked:02d}_SHA_exact", sha(p) == expected, rel)
        if "bytes" in meta:
            gates.check(f"artifact_{checked:02d}_size_exact", p.stat().st_size == meta["bytes"], rel)
        checked += 1
    return checked


def inspect_dataset(gates: Gates, root: Path):
    schema = read_json(root / "V16E4_R1_Dataset_Schema.json")
    cases = read_json(root / "V16E4_R1_Case_Manifest.json")

    gates.check("schema_model_inputs_exact", schema.get("model_inputs_only") == ["xi.npy", "conditioning.npy"])
    gates.check("schema_primary_target_exact", schema.get("primary_target") == "Sw_fan_teacher.npy")
    gates.check("schema_normalization_none", schema.get("normalization") == "none; raw conditioning as frozen; no fitted statistics")
    gates.check("schema_teacher_R2_exact", schema.get("teacher") == "V16E3_R2_STABLE_COREY_ANALYTIC_WELGE_FAN_V1")
    gates.check("schema_teacher_SHA_exact", schema.get("teacher_sha256") == R2_ADAPTER[1])
    gates.check("schema_Hybrid10_features_exact", schema.get("conditioning_feature_order", {}).get("Hybrid10") == FEATURES10)
    gates.check("schema_Hybrid12_features_exact", schema.get("conditioning_feature_order", {}).get("Hybrid12") == FEATURES12)

    gates.check("case_manifest_1000_families", len(cases) == 1000)
    partition_counts = {"train": 0, "validation": 0, "internal_test": 0}
    ids = set()
    for row in cases:
        ids.add(row["family_id"])
        partition_counts[row["partition"]] += 1
    gates.check("case_manifest_unique_family_ids", len(ids) == 1000)
    gates.check("case_manifest_split_700_150_150", partition_counts == {"train": 700, "validation": 150, "internal_test": 150})

    xi = np.load(root / "xi.npy", allow_pickle=False, mmap_mode="r")
    pc = np.load(root / "partition_codes.npy", allow_pickle=False, mmap_mode="r")
    fids = np.load(root / "family_ids.npy", allow_pickle=False, mmap_mode="r")
    gates.check("xi_shape_201", xi.shape == (201,))
    gates.check("xi_exact_grid", np.array_equal(np.asarray(xi), np.arange(201, dtype=np.float64) / 200.0))
    gates.check("partition_codes_shape_1000", pc.shape == (1000,))
    gates.check("partition_codes_counts_exact", [int(np.sum(pc == i)) for i in (0, 1, 2)] == [700, 150, 150])
    gates.check("family_ids_shape_1000", fids.shape == (1000,))

    shapes = {}
    for label, dim in [("Hybrid10", 10), ("Hybrid12", 12)]:
        cond = np.load(root / label / "conditioning.npy", allow_pickle=False, mmap_mode="r")
        target = np.load(root / label / "Sw_fan_teacher.npy", allow_pickle=False, mmap_mode="r")
        states = np.load(root / label / "transport_states.npy", allow_pickle=False, mmap_mode="r")
        gates.check(label + "_conditioning_shape_exact", cond.shape == (1000, 2, 8, 20, dim))
        gates.check(label + "_target_shape_exact", target.shape == (1000, 8, 20, 201))
        gates.check(label + "_transport_states_shape_exact", states.shape == (1000, 2, 8, 20, 5))
        gates.check(label + "_conditioning_float32", cond.dtype == np.float32)
        gates.check(label + "_target_float32", target.dtype == np.float32)
        shapes[label] = {"conditioning": list(cond.shape), "target": list(target.shape), "transport_states": list(states.shape)}

    return schema, partition_counts, shapes


def build_manifest(dataset_manifest_sha: str, audit_sha: str, summary_sha: str, handoff_sha: str,
                   partition_counts: dict, shapes: dict):
    common_training = {
        "framework": {
            "name": "TensorFlow",
            "version": "2.20.0",
            "api": "tf.keras",
            "float_policy": "float32",
            "mixed_precision": False,
            "jit_compile": False,
            "deterministic_ops_required": True,
        },
        "data": {
            "dataset_manifest_sha256": dataset_manifest_sha,
            "numerical_audit_sha256": audit_sha,
            "summary_sha256": summary_sha,
            "handoff_sha256": handoff_sha,
            "partitions": partition_counts,
            "train_profiles_per_experiment": 700 * 2 * 8 * 20,
            "validation_profiles_per_experiment": 150 * 2 * 8 * 20,
            "internal_test_profiles_per_experiment": 150 * 2 * 8 * 20,
            "allocation_modes_retained": ["kh", "kh_mob"],
            "normalization": "none; raw frozen conditioning; no statistics fitted",
            "shuffle_unit": "complete neural profile; equal descendant count per family preserves family balance",
            "shuffle_each_epoch": True,
            "shuffle_seed": 16051,
            "internal_test_loader_allowed_during_training": False,
        },
        "architecture": {
            "sequence_nodes": 201,
            "xi_input_dim": 1,
            "conditioning": "repeat parameter vector at all xi nodes then concatenate with xi",
            "lstm_layers": 2,
            "hidden_units": 64,
            "return_sequences": True,
            "activation": "tanh",
            "recurrent_activation": "sigmoid",
            "dropout": 0.0,
            "recurrent_dropout": 0.0,
            "head": "TimeDistributed(Dense(1))",
            "bounded_output": "swc + (1 - swc - sor) * sigmoid(z)",
            "kernel_initializer": "GlorotUniform",
            "recurrent_initializer": "Orthogonal",
            "bias_initializer": "Zeros",
        },
        "loss": {
            "structure": "lambda_data*L_Sw + lambda_bc*L_BC + lambda_front*L_front + lambda_phys*L_phys + lambda_mono*L_mono",
            "weights": {"lambda_data": 1.0, "lambda_bc": 5.0, "lambda_front": 2.0, "lambda_phys": 0.01, "lambda_mono": 0.1},
            "L_Sw": "mean squared saturation error over all 201 nodes; then batch mean",
            "L_BC": "MSE at xi=0 versus 1-sor",
            "L_front": "MSE at xi=1 versus supplied Sw_star",
            "L_phys": "interior-node MSE of analytic Corey fprime(Sw_hat) - xi*xD_star/tD using the frozen R2 stable Corey semantics",
            "L_mono": "mean square of relu(Sw_hat[j+1]-Sw_hat[j])",
            "physics_scope": "classical incompressible positive pre-breakthrough self-similar BL fan only",
        },
        "optimizer": {
            "name": "Adam",
            "learning_rate": 0.001,
            "beta_1": 0.9,
            "beta_2": 0.999,
            "epsilon": 1e-7,
            "amsgrad": False,
            "clipnorm": 1.0,
        },
        "schedule": {
            "type": "ReduceLROnPlateau",
            "monitor": "val_L_Sw",
            "mode": "min",
            "factor": 0.5,
            "patience_epochs": 8,
            "min_delta": 1e-6,
            "min_learning_rate": 1e-5,
        },
        "training": {
            "batch_size_profiles": 256,
            "max_epochs": 250,
            "global_seed": 1605,
            "python_seed": 1605,
            "numpy_seed": 1605,
            "tensorflow_seed": 1605,
            "hyperparameter_search": False,
            "test_informed_tuning": False,
        },
        "early_stopping": {
            "monitor": "val_L_Sw",
            "mode": "min",
            "patience_epochs": 20,
            "min_delta": 1e-6,
            "restore_best_weights": True,
        },
        "checkpoint_selection": {
            "criterion": "minimum validation L_Sw among finite epochs",
            "tie_breaker": "lower validation total objective, then earlier epoch",
            "internal_test_in_selection": False,
            "accepted_checkpoint_count_per_run": 1,
            "checkpoint_format": "Keras weights .weights.h5 plus JSON identity/config manifest",
            "historical_checkpoint_claim_permitted": False,
        },
        "validation_acceptance": {
            "Sw_RMSE_max": 0.020,
            "Sw_MAE_max": 0.0125,
            "profile_RMSE_p95_max": 0.030,
            "BC_RMSE_max": 0.015,
            "front_RMSE_max": 0.015,
            "physics_characteristic_RMSE_max": 0.030,
            "monotonic_violation_fraction_max": 0.005,
            "nonfinite_predictions_allowed": 0,
            "policy": "all gates must pass on validation before checkpoint can be frozen for later internal-test evaluation",
        },
        "sealed_evaluation": {
            "internal_test": "remains sealed during training, early stopping and checkpoint selection",
            "internal_test_evaluation": "one final evaluation only after validation-accepted checkpoint identity is frozen",
            "OOD": "existing V16 OOD contract remains unopened",
        },
    }

    experiments = {
        "Hybrid10": {
            "experiment_id": "V16E-HYBRID10-CLASSICAL-FAN-PROSPECTIVE-001",
            "training_run_id": "V16E6A-HYBRID10-R1",
            "param_dim": 10,
            "feature_order": FEATURES10,
            "expected_trainable_parameters": expected_param_count(10),
            "dataset_shapes": shapes["Hybrid10"],
            "execution_authorized_after_E5": True,
        },
        "Hybrid12": {
            "experiment_id": "V16E-HYBRID12-CLASSICAL-FAN-PROSPECTIVE-001",
            "training_run_id": "V16E6B-HYBRID12-R1",
            "param_dim": 12,
            "feature_order": FEATURES12,
            "expected_trainable_parameters": expected_param_count(12),
            "dataset_shapes": shapes["Hybrid12"],
            "execution_authorized_after_E5": False,
            "execution_requires": "successful V16E-6A Hybrid10 training/validation handoff; recipe itself is frozen here",
        },
    }

    return {
        "schema_version": 1,
        "milestone": MILESTONE,
        "revision": REVISION,
        "status": STATUS,
        "purpose": "freeze all numerical training choices before any prospective Hybrid model is trained",
        "parent": {
            "E4_R1_dataset_manifest_sha256": dataset_manifest_sha,
            "E4_R1_numerical_audit_sha256": audit_sha,
            "E4_R1_summary_sha256": summary_sha,
            "E4_R1_handoff_sha256": handoff_sha,
            "R2_adapter_sha256": R2_ADAPTER[1],
        },
        "common_training_protocol": common_training,
        "experiments": experiments,
        "authorization": {
            "training_performed_here": False,
            "checkpoint_created_here": False,
            "Hybrid10_controlled_training_authorized_after_success": True,
            "Hybrid12_execution_authorized_after_success": False,
            "internal_test_evaluation_authorized_now": False,
            "OOD_reopening_authorized": False,
            "SGSim_modification_authorized": False,
            "Pollock_TOF_recomputation_authorized": False,
            "B4_retraining_authorized": False,
        },
        "prohibitions": PROHIBITIONS,
        "next_milestone": NEXT,
    }


def validate_manifest(gates: Gates, m: dict):
    c = m["common_training_protocol"]
    gates.check("E5_no_training_performed_here", m["authorization"]["training_performed_here"] is False)
    gates.check("E5_no_checkpoint_created_here", m["authorization"]["checkpoint_created_here"] is False)
    gates.check("Hybrid10_training_authorized_after_success", m["authorization"]["Hybrid10_controlled_training_authorized_after_success"] is True)
    gates.check("Hybrid12_execution_deferred", m["authorization"]["Hybrid12_execution_authorized_after_success"] is False)
    gates.check("internal_test_still_sealed", m["authorization"]["internal_test_evaluation_authorized_now"] is False)
    gates.check("OOD_still_closed", m["authorization"]["OOD_reopening_authorized"] is False)
    gates.check("no_normalization_fitted", c["data"]["normalization"].startswith("none"))
    gates.check("fixed_loss_weights", c["loss"]["weights"] == {"lambda_data": 1.0, "lambda_bc": 5.0, "lambda_front": 2.0, "lambda_phys": 0.01, "lambda_mono": 0.1})
    gates.check("optimizer_fixed", c["optimizer"]["name"] == "Adam" and c["optimizer"]["learning_rate"] == 0.001)
    gates.check("batch_size_fixed", c["training"]["batch_size_profiles"] == 256)
    gates.check("max_epochs_fixed", c["training"]["max_epochs"] == 250)
    gates.check("single_deterministic_seed_fixed", c["training"]["global_seed"] == 1605)
    gates.check("hyperparameter_search_disabled", c["training"]["hyperparameter_search"] is False)
    gates.check("checkpoint_selection_validation_only", c["checkpoint_selection"]["internal_test_in_selection"] is False)
    gates.check("Hybrid10_param_count_exact", m["experiments"]["Hybrid10"]["expected_trainable_parameters"] == 52545)
    gates.check("Hybrid12_param_count_exact", m["experiments"]["Hybrid12"]["expected_trainable_parameters"] == 53057)
    gates.check("features10_frozen", m["experiments"]["Hybrid10"]["feature_order"] == FEATURES10)
    gates.check("features12_frozen", m["experiments"]["Hybrid12"]["feature_order"] == FEATURES12)


def commit_outputs(out: Path, payloads: dict[str, bytes]):
    if out.exists():
        if not out.is_dir() or set(p.name for p in out.iterdir()) != set(payloads):
            raise FreezeError("Existing E5 output differs; use a new output directory. Nothing overwritten.")
        if not all((out / name).read_bytes() == data for name, data in payloads.items()):
            raise FreezeError("Existing E5 output bytes differ; use a new output directory. Nothing overwritten.")
        print("Existing identical V16E-5 freeze reused.", flush=True)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".v16e5-", dir=out.parent))
    try:
        for name, data in payloads.items():
            p = staging / name
            with p.open("xb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        staging.rename(out)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def run(project: Path, drive: Path, dataset: Path, out: Path):
    print("=" * 118 + "\nPAD-Stream V16E-5\nPre-Training Manifest Freeze\n" + "=" * 118, flush=True)
    print("\n".join(PROHIBITIONS), flush=True)
    gates = Gates()

    print("\nV16E-4-R1 ACCEPTED DATASET AUTHORITY", flush=True)
    for label, (name, expected) in E4.items():
        bind(gates, "E4_R1_" + label, dataset / name, expected)
    bind(gates, "E4_R1_runner", project / E4_RUNNER[0], E4_RUNNER[1])
    bind(gates, "R2_adapter", project / R2_ADAPTER[0], R2_ADAPTER[1])

    manifest = read_json(dataset / E4["manifest"][0])
    audit = read_json(dataset / E4["audit"][0])
    summary = read_json(dataset / E4["summary"][0])

    gates.check("E4_R1_summary_milestone_exact", summary.get("milestone") == "V16E-4-R1")
    gates.check("E4_R1_accepted_dataset_true", summary.get("accepted_dataset_created") is True)
    gates.check("E4_R1_full_profile_certified_true", summary.get("full_profile_population_certified") is True)
    gates.check("E4_R1_two_pass_determinism_true", summary.get("repeat_generation_byte_identical") is True)
    gates.check("E4_R1_training_was_closed", summary.get("training_authorized") is False)
    gates.check("E4_R1_checkpoint_creation_was_closed", summary.get("checkpoint_creation_authorized") is False)
    gates.check("E4_R1_summary_manifest_link", summary.get("dataset_manifest_sha256") == E4["manifest"][1])
    gates.check("E4_R1_summary_audit_link", summary.get("numerical_audit_sha256") == E4["audit"][1])
    gates.check("E4_R1_audit_full_population", audit.get("full_profile_population_certified_here") is True)
    gates.check("E4_R1_audit_16016_exact", audit.get("audited_layer_parameter_sets") == 16016)
    gates.check("E4_R1_manifest_training_false", manifest.get("neural_training_authorized") is False)
    gates.check("E4_R1_manifest_R2_adapter_link", manifest.get("R2_adapter", {}).get("sha256") == R2_ADAPTER[1])

    print("\nE4-R1 ARTIFACT INVENTORY", flush=True)
    artifact_count = verify_inventory(gates, dataset, manifest)
    gates.check("E4_R1_artifact_inventory_nontrivial", artifact_count >= 10, f"{artifact_count} artifacts")

    print("\nDATASET SHAPE / SPLIT / SCHEMA CONTRACT", flush=True)
    _, partition_counts, shapes = inspect_dataset(gates, dataset)

    training_manifest = build_manifest(
        E4["manifest"][1], E4["audit"][1], E4["summary"][1], E4["handoff"][1],
        partition_counts, shapes,
    )

    print("\nPRE-TRAINING CONTRACT", flush=True)
    validate_manifest(gates, training_manifest)

    manifest_bytes = encoded(training_manifest)
    results = {
        "milestone": MILESTONE,
        "revision": REVISION,
        "status": STATUS,
        "pretraining_manifest_sha256": digest(manifest_bytes),
        "runner_sha256": sha(Path(__file__)),
        "E4_R1_dataset_manifest_sha256": E4["manifest"][1],
        "E4_R1_numerical_audit_sha256": E4["audit"][1],
        "acceptance_gates": gates.items,
        "all_gates_passed": all(v["passed"] for v in gates.items.values()),
        "training_performed_here": False,
        "checkpoint_created_here": False,
        "Hybrid10_controlled_training_authorized": True,
        "Hybrid12_recipe_frozen_execution_deferred": True,
        "internal_test_remains_sealed": True,
        "OOD_remains_closed": True,
        "next_milestone": NEXT,
    }
    results_bytes = encoded(results)
    summary5 = {
        "milestone": MILESTONE,
        "revision": REVISION,
        "status": STATUS,
        "pretraining_manifest_sha256": digest(manifest_bytes),
        "results_sha256": digest(results_bytes),
        "pretraining_protocol_frozen": True,
        "dataset_changed_here": False,
        "model_created_here": False,
        "training_performed_here": False,
        "checkpoint_created_here": False,
        "Hybrid10_training_authorized_after_success": True,
        "Hybrid12_execution_deferred": True,
        "internal_test_evaluation_authorized": False,
        "next_milestone": NEXT,
    }
    summary_bytes = encoded(summary5)
    handoff = f'''# PAD-Stream V16E-5 — Pre-Training Manifest Freeze\n\nThe accepted V16E-4-R1 dataset, its complete artifact inventory, the full numerical\naudit and the frozen R2 teacher adapter were verified exactly. No dataset bytes were\nchanged. No neural model was instantiated, trained or checkpointed.\n\nThe prospective training recipe is now frozen before execution: TensorFlow 2.20.0,\nfloat32, deterministic seed 1605, the source-bound two-layer 64-unit LSTM family,\nfixed loss weights, Adam optimizer, batch size, learning-rate schedule, early stopping,\nvalidation-only checkpoint selection and validation acceptance gates. No hyperparameter\nsearch is authorized in V16E-6A.\n\nHybrid10 is authorized for the first controlled training/validation run only. The\nHybrid12 recipe is frozen here but its execution is deferred until the V16E-6A handoff.\nThe internal-test partition remains sealed and cannot select a checkpoint. Existing\nOOD work remains unopened. No historical Hybrid checkpoint claim is permitted.\n\nPre-training manifest SHA: {digest(manifest_bytes)}\nResults SHA: {digest(results_bytes)}\nSummary SHA: {digest(summary_bytes)}\nE4-R1 dataset manifest SHA: {E4['manifest'][1]}\nR2 adapter SHA: {R2_ADAPTER[1]}\n\nNEXT: {NEXT}\n'''.encode("utf-8")

    payloads = {
        "V16E5_PreTraining_Manifest.json": manifest_bytes,
        "V16E5_PreTraining_Manifest_Freeze_Results.json": results_bytes,
        "PAD_Stream_V16E5_Summary.json": summary_bytes,
        "V16E5_Handoff.md": handoff,
    }
    commit_outputs(out, payloads)

    print("\n" + "=" * 118 + "\nV16E-5 RESULT: PASS\n" + "=" * 118, flush=True)
    print(f"{'E4-R1 accepted dataset bound':48}: YES", flush=True)
    print(f"{'Training recipe prospectively frozen':48}: YES", flush=True)
    print(f"{'Training / checkpoint performed here':48}: NO / NO", flush=True)
    print(f"{'Hybrid10 controlled training authorized':48}: YES", flush=True)
    print(f"{'Hybrid12 execution authorized now':48}: NO (recipe frozen)", flush=True)
    print(f"{'Internal test / OOD opened':48}: NO / NO", flush=True)
    for name, data in payloads.items():
        print(f"{name} SHA: {digest(data)}", flush=True)
    print("Output:", out, flush=True)
    print("NEXT:", NEXT, flush=True)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--dataset-dir", type=Path)
    p.add_argument("--output-dir", type=Path)
    args = p.parse_args(argv)
    try:
        project = args.project_root.resolve()
        drive = args.drive_root.resolve()
        dataset = (args.dataset_dir or drive / E4_REL).resolve()
        out = (args.output_dir or drive / E5_REL).resolve()
        return run(project, drive, dataset, out)
    except (FreezeError, OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        print("\n[FAIL] V16E-5 did not close:", exc, file=sys.stderr, flush=True)
        print("No training authorization was published by this invocation.", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
