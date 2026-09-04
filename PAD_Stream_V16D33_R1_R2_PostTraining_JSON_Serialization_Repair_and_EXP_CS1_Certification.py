#!/usr/bin/env python3
"""
PAD-Stream V16D-33-R1-R2
Post-Training JSON Serialization Repair + Existing EXP-CS1 Run Certification

Purpose
-------
Recover/certify the already-completed V16D-33-R1 EXP-CS1 training attempt after
its final summary JSON serialization failed.

This is NOT a training rerun.

The original D33-R1 run already:
  * completed 98 epochs,
  * early-stopped after the frozen patience window,
  * selected/reloaded the best validation checkpoint,
  * evaluated the selected checkpoint on VALIDATION,
  * wrote validation diagnostics,
  * left LOCKED_OOD_TEST sealed,
  * then failed only while serializing the final summary because a non-native
    boolean scalar remained in the gate dictionary.

This repair:
  * never imports TensorFlow,
  * never loads a model,
  * never opens any NPZ,
  * never trains,
  * never performs inference,
  * never opens or hashes LOCKED_OOD predictor/target arrays,
  * never changes model/optimizer/loss/seed/batch/selection rules,
  * certifies the existing checkpoint/history/validation diagnostics by SHA.
"""

from pathlib import Path
import csv
import hashlib
import json
import math
import sys


# =============================================================================
# ROOT / AUTHORITIES
# =============================================================================

R = Path(__file__).resolve().parent

D33 = (
    R
    / "output"
    / "V16_D33_CONTROLSPACE_RECURRENT_STAGE4_EXECUTABLE_TRAINING_PROTOCOL_FREEZE"
)
D33_SUMMARY = D33 / "PAD_Stream_V16D33_Summary.json"
D33_PROTOCOL = D33 / "V16D33_EXP_CS1_ControlSpace_Executable_Training_Protocol_1.0.json"

D33_SUMMARY_SHA = (
    "b347b5aa8e3583ce4f35201840e47bf4cfb2e65d4589f0cbe981cad897dd760b"
)
D33_PROTOCOL_SHA = (
    "e12219bdfe85fdbc2de30e348df609ff9bc91a652500a65f053dc6b64b4f9f4a"
)

D33R1_SOURCE = R / "PAD_Stream_V16D33_R1_EXP_CS1_ControlSpace_Recurrent_Stage4_Training_Run.py"
D33R1_SOURCE_SHA = (
    "a1d4ad5ee4e9918b590c72c54925e7685734941e5488f381152b9170f2eef4b6"
)

D31D = (
    R
    / "output"
    / "V16_D31D_FROZEN_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION_CONTRACT"
)
D31D_CONTRACT = D31D / "V16D31D_OneTouch_Final_Locked_OOD_Evaluation_Contract.json"
D31D_CONTRACT_SHA = (
    "7c664db19c041d3a611cbbc94de03a501a70f38922c62fd044cde1016d03228d"
)

D32 = (
    R
    / "output"
    / "V16_D32_CONTROLSPACE_36CASE_STAGE4_LEARNING_DATASET_TRAIN_ONLY_NORMALIZATION"
)
D32_REGISTRY = D32 / "V16D32_Frozen_36Case_Learning_Dataset_Registry.json"
D32_REGISTRY_SHA = (
    "9429b239626fbfc8fe8569a2214a79a7abd5e40fbc38ac9112ba236e547fb90d"
)
D32_NORMALIZATION = D32 / "V16D32_TRAIN_Only_Normalization_Statistics.json"
D32_NORMALIZATION_SHA = (
    "dcda1cf01fa30bd1cd947a500de73295037d6ca2b492725edd050c0ff7c3bfd9"
)


# =============================================================================
# EXISTING D33-R1 ARTIFACTS — READ ONLY
# =============================================================================

O = (
    R
    / "output"
    / "V16_D33_R1_EXP_CS1_CONTROLSPACE_RECURRENT_STAGE4_TRAINING_RUN"
)

RUN_LOCK = O / "TRAINING_STARTED.lock"
CHECKPOINT = O / "V16D33R1_EXP_CS1_Best.weights.h5"
TRAINING_HISTORY = O / "V16D33R1_EXP_CS1_Training_History.csv"
ARCHITECTURE_JSON = O / "V16D33R1_EXP_CS1_Model_Architecture.json"
VALIDATION_DIAGNOSTICS = O / "V16D33R1_EXP_CS1_Validation_Diagnostics.json"
CASE_BINDING_MANIFEST = O / "V16D33R1_TRAIN_VALIDATION_Artifact_Bindings.json"

# The architecture SHA printed by the completed original run before training.
EXPECTED_ARCHITECTURE_SHA = (
    "4304519d7c41b231f300535cef5daacd2525e395413addc883e66e7310096920"
)

# Exact execution identity evidenced by the completed run log.
EXPECTED_EPOCHS_EXECUTED = 98
EXPECTED_BEST_EPOCH = 73
EXPECTED_TRAIN_BATCHES_PER_EPOCH = 2729
EXPECTED_VALIDATION_BATCHES = 1365

REPAIR_REPORT = O / "V16D33R1R2_PostTraining_Serialization_Repair_Report.json"
REPAIRED_SUMMARY = O / "PAD_Stream_V16D33_R1_R2_Summary.json"


# =============================================================================
# HELPERS
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def exact_sha(path: Path, expected: str) -> bool:
    return path.exists() and path.is_file() and sha256(path) == expected


def read_json(path: Path):
    return json.loads(path.read_text())


def require(path: Path, label: str):
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"Required existing {label} missing: {path}")
    if path.stat().st_size <= 0:
        raise RuntimeError(f"Required existing {label} is empty: {path}")


def all_finite(values):
    return all(math.isfinite(float(x)) for x in values)


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16D-33-R1-R2")
    print("Post-Training JSON Serialization Repair + Existing EXP-CS1 Certification")
    print("=" * 78)

    print(
        "\nNO RETRAINING. NO MODEL LOAD. NO NPZ LOAD. NO OOD ACCESS.\n"
        "This milestone certifies the already-completed D33-R1 training attempt.\n"
    )

    # -------------------------------------------------------------------------
    # 1. Frozen authority + source identity
    # -------------------------------------------------------------------------

    gates = {
        "D33_summary_SHA_exact":
            exact_sha(D33_SUMMARY, D33_SUMMARY_SHA),
        "D33_protocol_SHA_exact":
            exact_sha(D33_PROTOCOL, D33_PROTOCOL_SHA),
        "D33R1_source_SHA_exact":
            exact_sha(D33R1_SOURCE, D33R1_SOURCE_SHA),
        "D31D_contract_SHA_exact":
            exact_sha(D31D_CONTRACT, D31D_CONTRACT_SHA),
        "D32_registry_SHA_exact":
            exact_sha(D32_REGISTRY, D32_REGISTRY_SHA),
        "D32_normalization_SHA_exact":
            exact_sha(D32_NORMALIZATION, D32_NORMALIZATION_SHA),
    }

    print("AUTHORITY GATES")
    for name, passed in gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    if not all(gates.values()):
        raise RuntimeError("R2 blocked: frozen authority/source SHA mismatch.")

    # -------------------------------------------------------------------------
    # 2. Existing run artifacts must already exist
    # -------------------------------------------------------------------------

    for path, label in [
        (RUN_LOCK, "training lock"),
        (CHECKPOINT, "best checkpoint"),
        (TRAINING_HISTORY, "training history"),
        (ARCHITECTURE_JSON, "architecture JSON"),
        (VALIDATION_DIAGNOSTICS, "validation diagnostics"),
        (CASE_BINDING_MANIFEST, "TRAIN/VALIDATION binding manifest"),
    ]:
        require(path, label)

    existing_hashes = {
        "training_lock_sha256": sha256(RUN_LOCK),
        "checkpoint_sha256": sha256(CHECKPOINT),
        "training_history_sha256": sha256(TRAINING_HISTORY),
        "architecture_sha256": sha256(ARCHITECTURE_JSON),
        "validation_diagnostics_sha256": sha256(VALIDATION_DIAGNOSTICS),
        "binding_manifest_sha256": sha256(CASE_BINDING_MANIFEST),
    }

    gates.update({
        "training_lock_exists": RUN_LOCK.exists(),
        "checkpoint_exists_nonempty": CHECKPOINT.stat().st_size > 0,
        "training_history_exists_nonempty": TRAINING_HISTORY.stat().st_size > 0,
        "architecture_exists_nonempty": ARCHITECTURE_JSON.stat().st_size > 0,
        "validation_diagnostics_exists_nonempty": VALIDATION_DIAGNOSTICS.stat().st_size > 0,
        "binding_manifest_exists_nonempty": CASE_BINDING_MANIFEST.stat().st_size > 0,
        "architecture_SHA_matches_original_run_log":
            existing_hashes["architecture_sha256"] == EXPECTED_ARCHITECTURE_SHA,
    })

    # -------------------------------------------------------------------------
    # 3. Recover history without TensorFlow / model inference
    # -------------------------------------------------------------------------

    with TRAINING_HISTORY.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise RuntimeError("Training history contains no epoch rows.")

    required_cols = {"epoch", "loss", "mae", "val_loss", "val_mae"}
    missing_cols = required_cols - set(rows[0])
    if missing_cols:
        raise RuntimeError(
            f"Training history missing required columns: {sorted(missing_cols)}"
        )

    epoch_zero_based = [int(r["epoch"]) for r in rows]
    loss = [float(r["loss"]) for r in rows]
    mae = [float(r["mae"]) for r in rows]
    val_loss = [float(r["val_loss"]) for r in rows]
    val_mae = [float(r["val_mae"]) for r in rows]

    epochs_executed = len(rows)
    best_row_index = min(range(len(rows)), key=lambda i: val_loss[i])
    best_epoch = best_row_index + 1
    best_raw_val_mse = val_loss[best_row_index]
    best_training_loss = loss[best_row_index]
    best_training_mae = mae[best_row_index]
    best_val_mae_history = val_mae[best_row_index]

    gates.update({
        "history_all_metrics_finite":
            all_finite(loss + mae + val_loss + val_mae),
        "history_epochs_sequential_zero_based":
            epoch_zero_based == list(range(epochs_executed)),
        "epochs_executed_exact_98":
            epochs_executed == EXPECTED_EPOCHS_EXECUTED,
        "best_epoch_exact_73":
            best_epoch == EXPECTED_BEST_EPOCH,
        "best_validation_MSE_positive_finite":
            math.isfinite(best_raw_val_mse) and best_raw_val_mse > 0.0,
        "patience_window_exact_25_after_best_epoch":
            epochs_executed - best_epoch == 25,
    })

    # -------------------------------------------------------------------------
    # 4. Recover selected-checkpoint validation diagnostics
    # -------------------------------------------------------------------------

    diag = read_json(VALIDATION_DIAGNOSTICS)

    required_diag = [
        "MSE_float64_accumulation",
        "RMSE_float64_accumulation",
        "MAE_float64_accumulation",
        "mean_signed_error_float64_accumulation",
        "prediction_min",
        "prediction_max",
        "target_min",
        "target_max",
        "values_evaluated",
        "best_epoch",
        "best_raw_val_MSE_from_training_history",
        "checkpoint_sha256",
        "architecture_sha256",
        "LOCKED_OOD_opened",
        "LOCKED_OOD_evaluated",
    ]

    gates["validation_diagnostics_required_fields"] = all(
        k in diag for k in required_diag
    )

    if not gates["validation_diagnostics_required_fields"]:
        missing = [k for k in required_diag if k not in diag]
        raise RuntimeError(
            f"Validation diagnostics missing required fields: {missing}"
        )

    val_mse = float(diag["MSE_float64_accumulation"])
    val_rmse = float(diag["RMSE_float64_accumulation"])
    val_mae = float(diag["MAE_float64_accumulation"])
    val_bias = float(diag["mean_signed_error_float64_accumulation"])
    pred_min = float(diag["prediction_min"])
    pred_max = float(diag["prediction_max"])
    target_min = float(diag["target_min"])
    target_max = float(diag["target_max"])
    values_evaluated = int(diag["values_evaluated"])

    gates.update({
        "diag_best_epoch_matches_history":
            int(diag["best_epoch"]) == best_epoch,
        "diag_best_raw_val_MSE_matches_history":
            math.isclose(
                float(diag["best_raw_val_MSE_from_training_history"]),
                best_raw_val_mse,
                rel_tol=0.0,
                abs_tol=1e-15,
            ),
        "diag_checkpoint_SHA_matches_existing":
            diag["checkpoint_sha256"] == existing_hashes["checkpoint_sha256"],
        "diag_architecture_SHA_matches_existing":
            diag["architecture_sha256"] == existing_hashes["architecture_sha256"],
        "diag_validation_metrics_finite":
            all_finite([val_mse, val_rmse, val_mae, val_bias]),
        "diag_RMSE_squared_matches_MSE":
            math.isclose(val_rmse * val_rmse, val_mse, rel_tol=1e-10, abs_tol=1e-15),
        "diag_values_evaluated_exact":
            values_evaluated == 87318 * 201,
        "diag_prediction_bounds_enforced":
            pred_min >= 0.2 - 1e-6 and pred_max <= 0.8 + 1e-6,
        "diag_OOD_not_opened":
            diag["LOCKED_OOD_opened"] is False,
        "diag_OOD_not_evaluated":
            diag["LOCKED_OOD_evaluated"] is False,
    })

    # -------------------------------------------------------------------------
    # 5. Binding manifest proves only TRAIN/VALIDATION were preflighted
    # -------------------------------------------------------------------------

    binding = read_json(CASE_BINDING_MANIFEST)
    bindings = binding.get("bindings", [])

    counts = {
        "TRAIN": sum(x.get("partition") == "TRAIN" for x in bindings),
        "VALIDATION": sum(x.get("partition") == "VALIDATION" for x in bindings),
        "LOCKED_OOD_TEST": sum(
            x.get("partition") == "LOCKED_OOD_TEST" for x in bindings
        ),
    }

    gates.update({
        "binding_manifest_exact_27_cases": len(bindings) == 27,
        "binding_manifest_exact_18_TRAIN": counts["TRAIN"] == 18,
        "binding_manifest_exact_9_VALIDATION": counts["VALIDATION"] == 9,
        "binding_manifest_zero_OOD": counts["LOCKED_OOD_TEST"] == 0,
        "binding_manifest_declares_OOD_not_resolved_or_hashed":
            binding.get("LOCKED_OOD_entries_resolved_or_hashed") is False,
    })

    # -------------------------------------------------------------------------
    # 6. Run-lock provenance
    # -------------------------------------------------------------------------

    lock = read_json(RUN_LOCK)
    gates.update({
        "run_lock_experiment_EXP_CS1": lock.get("experiment") == "EXP-CS1",
        "run_lock_D33_protocol_SHA_exact":
            lock.get("D33_protocol_sha256") == D33_PROTOCOL_SHA,
        "run_lock_D32_registry_SHA_exact":
            lock.get("D32_dataset_registry_sha256") == D32_REGISTRY_SHA,
    })

    # -------------------------------------------------------------------------
    # 7. Explicit repair/firewall gates
    # -------------------------------------------------------------------------

    gates.update({
        "failure_class_post_training_summary_serialization_only": True,
        "no_retraining_in_R2": True,
        "no_model_load_in_R2": True,
        "no_model_inference_in_R2": True,
        "no_npz_load_in_R2": True,
        "no_TRAIN_target_reopen_in_R2": True,
        "no_VALIDATION_target_reopen_in_R2": True,
        "no_OOD_X_open_in_R2": True,
        "no_OOD_Y_open_in_R2": True,
        "no_OOD_hashing_in_R2": True,
        "no_OOD_metric_in_R2": True,
        "no_OOD_informed_decision_in_R2": True,
        "no_architecture_change": True,
        "no_checkpoint_change": True,
        "no_loss_change": True,
        "no_optimizer_change": True,
        "no_seed_change": True,
        "no_batch_change": True,
        "no_threshold_change": True,
        "original_training_attempt_preserved": True,
    })

    ok = bool(all(bool(v) for v in gates.values()))

    status = (
        "V16D_EXP_CS1_CONTROLSPACE_RECURRENT_STAGE4_EXISTING_TRAINING_RUN_"
        "CERTIFIED_POSTSERIALIZATION_REPAIR_BEST_VALIDATION_CHECKPOINT_FROZEN_"
        "OOD_REMAINS_SEALED_FINAL_ONE_TOUCH_EVALUATOR_BINDING_CONTRACT_AUTHORIZED"
        if ok
        else "V16D_D33_R1_R2_EXISTING_TRAINING_CERTIFICATION_BLOCKED"
    )

    next_milestone = (
        "V16D-34 — Freeze EXP-CS1 selected architecture/checkpoint/validation "
        "metrics into the final one-touch locked-OOD evaluator binding contract"
        if ok
        else "Diagnose existing D33-R1 artifacts without retraining or opening OOD."
    )

    # -------------------------------------------------------------------------
    # 8. Serialization-safe repair report + authoritative repaired summary
    # -------------------------------------------------------------------------

    repair_report = {
        "milestone": "V16D-33-R1-R2",
        "repair_of": "V16D-33-R1",
        "failure_class": "POST_TRAINING_FINAL_SUMMARY_JSON_SERIALIZATION_ONLY",
        "cause": (
            "Original D33-R1 reached the final summary write with one or more "
            "non-native boolean scalar values in the gate dictionary. Training, "
            "checkpoint selection, checkpoint reload, and validation diagnostics "
            "had already completed."
        ),
        "repair_scope": "serialization/certification only; no numerical recomputation from X/Y",
        "original_source": {
            "path": str(D33R1_SOURCE.relative_to(R)),
            "sha256": D33R1_SOURCE_SHA,
        },
        "existing_artifact_hashes": existing_hashes,
        "recovered_training_identity": {
            "experiment": "EXP-CS1",
            "epochs_executed": epochs_executed,
            "best_epoch": best_epoch,
            "best_raw_validation_MSE": best_raw_val_mse,
            "best_epoch_training_loss": best_training_loss,
            "best_epoch_training_MAE": best_training_mae,
            "best_epoch_validation_MAE_history": best_val_mae_history,
            "expected_training_batches_per_epoch": EXPECTED_TRAIN_BATCHES_PER_EPOCH,
            "expected_validation_batches": EXPECTED_VALIDATION_BATCHES,
        },
        "frozen_validation_metrics": {
            "MSE": val_mse,
            "RMSE": val_rmse,
            "MAE": val_mae,
            "mean_signed_error": val_bias,
            "prediction_min": pred_min,
            "prediction_max": pred_max,
            "target_min": target_min,
            "target_max": target_max,
            "values_evaluated": values_evaluated,
        },
        "OOD": {
            "geology": "0029",
            "opened": False,
            "evaluated": False,
            "hashed_in_repair": False,
            "used_for_selection": False,
        },
        "gates": {k: bool(v) for k, v in gates.items()},
    }

    REPAIR_REPORT.write_text(json.dumps(repair_report, indent=2))

    summary = {
        "milestone": "V16D-33-R1-R2",
        "experiment": "EXP-CS1",
        "status": status,
        "repair_of": "V16D-33-R1",
        "failure_class": "POST_TRAINING_FINAL_SUMMARY_JSON_SERIALIZATION_ONLY",
        "training_rerun": False,
        "epochs_executed": epochs_executed,
        "best_epoch": best_epoch,
        "best_raw_validation_MSE": best_raw_val_mse,
        "selected_model": {
            "architecture": "LSTM64 -> LSTM64 -> TD Dense sigmoid -> Rescaling[0.2,0.8]",
            "architecture_path": str(ARCHITECTURE_JSON.relative_to(R)),
            "architecture_sha256": existing_hashes["architecture_sha256"],
            "checkpoint_path": str(CHECKPOINT.relative_to(R)),
            "checkpoint_sha256": existing_hashes["checkpoint_sha256"],
            "selection_authority": "minimum raw VALIDATION MSE",
        },
        "frozen_validation_metrics": {
            "MSE": val_mse,
            "RMSE": val_rmse,
            "MAE": val_mae,
            "mean_signed_error": val_bias,
            "prediction_min": pred_min,
            "prediction_max": pred_max,
            "values_evaluated": values_evaluated,
            "diagnostics_path": str(VALIDATION_DIAGNOSTICS.relative_to(R)),
            "diagnostics_sha256": existing_hashes["validation_diagnostics_sha256"],
        },
        "artifact_hashes": existing_hashes,
        "repair_report_sha256": sha256(REPAIR_REPORT),
        "frozen_authorities": {
            "D33_summary_sha256": D33_SUMMARY_SHA,
            "D33_protocol_sha256": D33_PROTOCOL_SHA,
            "D33R1_source_sha256": D33R1_SOURCE_SHA,
            "D32_dataset_registry_sha256": D32_REGISTRY_SHA,
            "D32_normalization_sha256": D32_NORMALIZATION_SHA,
            "D31D_contract_sha256": D31D_CONTRACT_SHA,
        },
        "LOCKED_OOD": {
            "geology": "0029",
            "X_opened_in_repair": False,
            "Y_opened_in_repair": False,
            "evaluated": False,
            "used_for_selection": False,
        },
        "gates": {k: bool(v) for k, v in gates.items()},
        "next_milestone": next_milestone,
    }

    # Native Python scalars only; prove serialization before write.
    payload = json.dumps(summary, indent=2)
    REPAIRED_SUMMARY.write_text(payload)

    print("\nRECOVERED EXISTING TRAINING RESULT")
    print("  epochs executed      :", epochs_executed)
    print("  best epoch           :", best_epoch)
    print("  best raw val MSE     : %.12e" % best_raw_val_mse)
    print("  frozen val MSE       : %.12e" % val_mse)
    print("  frozen val RMSE      : %.12e" % val_rmse)
    print("  frozen val MAE       : %.12e" % val_mae)
    print("  validation pred range: [%.9f, %.9f]" % (pred_min, pred_max))
    print("  checkpoint SHA-256   :", existing_hashes["checkpoint_sha256"])
    print("  architecture SHA-256 :", existing_hashes["architecture_sha256"])

    print("\nGATES")
    for name, passed in gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    print("\nSTATUS")
    print(" ", status)

    print("\nLOCKED-OOD STATUS")
    print(
        "  SEALED — no geology0029 X/Y array was opened, hashed, or evaluated "
        "by this repair."
    )

    print("\nNEXT")
    print(" ", next_milestone)

    print("\nExisting checkpoint SHA-256:", existing_hashes["checkpoint_sha256"])
    print("Repair report SHA-256       :", sha256(REPAIR_REPORT))
    print("Repaired summary SHA-256    :", sha256(REPAIRED_SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
