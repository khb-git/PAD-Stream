#!/usr/bin/env python3
"""
PAD-Stream V16D-31D
Frozen One-Touch Final LOCKED-OOD Evaluation Contract

This milestone DOES NOT evaluate the locked OOD set.

It freezes, before model training/selection on the new 36-case control-space
experiment:
  * the exact sealed geology0029 OOD identity,
  * the exact 9 control cases and 9 target times,
  * the one-touch opening semantics,
  * the required model/checkpoint freeze prerequisites,
  * the allowed final metrics,
  * the no-retraining / no-selection-after-opening firewall.

The future final evaluator may execute only after a single model architecture,
normalization authority, and validation-selected checkpoint have been frozen by
SHA-256 without any LOCKED_OOD_TEST use.
"""

from pathlib import Path
import hashlib
import json
import sys

R = Path(__file__).resolve().parent
O = R / "output" / "V16_D31D_FROZEN_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION_CONTRACT"
O.mkdir(parents=True, exist_ok=True)

D31 = R / "output" / "V16_D31_PARTITIONAWARE_RESTARTABLE_36CASE_STAGE4_TRANSPORT_EXECUTION_CONTRACT" / "PAD_Stream_V16D31_Summary.json"

D31A_DIR = R / "output" / "V16_D31A_RESTARTABLE_TRAIN_18CASE_STAGE4_TRANSPORT"
D31A_SUMMARY = D31A_DIR / "PAD_Stream_V16D31A_Summary.json"
D31A_MANIFEST = D31A_DIR / "V16D31A_TRAIN_18Case_Manifest.json"

D31B_DIR = R / "output" / "V16_D31B_R1_RESTARTABLE_VALIDATION_9CASE_STAGE4_TRANSPORT"
D31B_SUMMARY = D31B_DIR / "PAD_Stream_V16D31B_R1_Summary.json"
D31B_MANIFEST = D31B_DIR / "V16D31B_R1_VALIDATION_9Case_Manifest.json"

D31C_DIR = R / "output" / "V16_D31C_LOCKED_OOD_STAGE4_TRANSPORT_GENERATION_CONTRACT"
D31C_CONTRACT = D31C_DIR / "V16D31C_Locked_OOD_Transport_Generation_Contract.json"
D31C_SUMMARY = D31C_DIR / "PAD_Stream_V16D31C_Summary.json"

D31CR1_DIR = R / "output" / "V16_D31C_R1_RESTARTABLE_LOCKED_OOD_9CASE_STAGE4_TRANSPORT"
D31CR1_CASES = D31CR1_DIR / "cases"
D31CR1_MANIFEST = D31CR1_DIR / "V16D31C_R1_LOCKED_OOD_9Case_Manifest.json"
D31CR1_SUMMARY = D31CR1_DIR / "PAD_Stream_V16D31C_R1_Summary.json"

EXPECTED_SHA = {
    "D31_summary": "107e2c5cedf9ac9fcebfea27d3290c84be9c0d0ae46f5cd6c0dce37fa0b5e33d",
    "D31A_summary": "ccc6dbb748c8ffd465b5c0e7c40291b4a04a91957a554a68360957ffb8a5edc4",
    "D31A_manifest": "b59d62bb839477b4158774c845b680b32a21543e9762645e95513f092992545b",
    "D31B_summary": "87fe0042da478221f51210461d523e0d9c564996cd88756c99016b6ae57a7ba9",
    "D31B_manifest": "39adcee9baf710a3e9910a88b999a82aaf237d4601c995a387b040798e0fe163",
    "D31C_contract": "f08b7258dc645a6f866683200a0ff35cc7917a373fe27caec525152c65c2e153",
    "D31C_summary": "2d4afc02fd0bd8213e195d5a00a6cbf1151fa3d5e6a83578520a99ba96c69b3e",
    "D31CR1_manifest": "6e4fac63b6dcd8dad4e1675cd2d856811ffcf9231dadc50104349471da9df9a6",
    "D31CR1_summary": "91d83cc1588d8ec54d1a3903128c9dbbcc4aedb7f82c554e590143372f855092",
}

RATES_TPD = [350, 500, 650]
PRODUCER_BHP_PSI = [1800, 2000, 2200]
TARGET_DAYS = [30, 60, 100, 150, 250, 365, 500, 750, 1000]
EXPECTED_OOD_CASE_IDS = [
    f"V16D_Foundation_Case_0029_R{rate}_B{bhp}"
    for rate in RATES_TPD
    for bhp in PRODUCER_BHP_PSI
]
EXPECTED_Y_SHAPE = [9, 1078, 201]
EXPECTED_X_SHAPE = [9, 1078, 201, 9]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def exact_sha(path: Path, expected: str) -> bool:
    return path.exists() and sha256(path) == expected


def case_artifact_path(case_id: str) -> Path:
    return D31CR1_CASES / f"{case_id}_Stage4_Transport.npz"


def main():
    print("=" * 78)
    print("PAD-Stream V16D-31D")
    print("Frozen One-Touch Final LOCKED-OOD Evaluation Contract")
    print("=" * 78)

    gates = {
        "D31_summary_SHA_exact": exact_sha(D31, EXPECTED_SHA["D31_summary"]),
        "D31A_summary_SHA_exact": exact_sha(D31A_SUMMARY, EXPECTED_SHA["D31A_summary"]),
        "D31A_manifest_SHA_exact": exact_sha(D31A_MANIFEST, EXPECTED_SHA["D31A_manifest"]),
        "D31B_summary_SHA_exact": exact_sha(D31B_SUMMARY, EXPECTED_SHA["D31B_summary"]),
        "D31B_manifest_SHA_exact": exact_sha(D31B_MANIFEST, EXPECTED_SHA["D31B_manifest"]),
        "D31C_contract_SHA_exact": exact_sha(D31C_CONTRACT, EXPECTED_SHA["D31C_contract"]),
        "D31C_summary_SHA_exact": exact_sha(D31C_SUMMARY, EXPECTED_SHA["D31C_summary"]),
        "D31CR1_manifest_SHA_exact": exact_sha(D31CR1_MANIFEST, EXPECTED_SHA["D31CR1_manifest"]),
        "D31CR1_summary_SHA_exact": exact_sha(D31CR1_SUMMARY, EXPECTED_SHA["D31CR1_summary"]),
    }

    if not all(gates.values()):
        print("\nPRE-GATES")
        for name, passed in gates.items():
            print("[PASS]" if passed else "[FAIL]", name)
        raise RuntimeError("D31D blocked: exact upstream SHA lineage mismatch.")

    ood_summary = read_json(D31CR1_SUMMARY)
    ood_manifest = read_json(D31CR1_MANIFEST)

    gates.update({
        "D31CR1_status_authorizes_contract": (
            ood_summary.get("status")
            == "V16D_LOCKED_OOD_9CASE_STAGE4_TRANSPORT_GENERATED_CERTIFIED_RESTARTABLE_SEALED_FINAL_OOD_EVALUATION_CONTRACT_AUTHORIZED"
        ),
        "D31CR1_certified_cases_9": ood_summary.get("certified_cases") == 9,
        "D31CR1_partition_locked_OOD": ood_summary.get("partition") == "LOCKED_OOD_TEST",
        "D31CR1_geology0029": ood_summary.get("geology") == "0029",
        "D31CR1_manifest_hash_record_matches": ood_summary.get("manifest_sha256") == EXPECTED_SHA["D31CR1_manifest"],
        "D31CR1_generation_sealed": ood_summary.get("OOD_generation_sealed") is True,
        "D31CR1_no_training_use": ood_summary.get("OOD_targets_not_used_for_training") is True,
        "D31CR1_no_tuning_use": ood_summary.get("OOD_targets_not_used_for_tuning") is True,
        "D31CR1_no_normalization_use": ood_summary.get("OOD_targets_not_used_for_normalization") is True,
        "D31CR1_no_selection_use": ood_summary.get("OOD_targets_not_used_for_selection") is True,
    })

    manifest_cases = ood_manifest.get("cases", [])
    manifest_ids = [record.get("case_id") for record in manifest_cases]

    gates.update({
        "manifest_status_CERTIFIED_SEALED": ood_manifest.get("status") == "CERTIFIED_SEALED",
        "manifest_partition_LOCKED_OOD_TEST": ood_manifest.get("partition") == "LOCKED_OOD_TEST",
        "manifest_geology0029": ood_manifest.get("geology") == "0029",
        "manifest_count_9": ood_manifest.get("count") == 9 and len(manifest_cases) == 9,
        "manifest_rates_exact": ood_manifest.get("rates_tpd") == RATES_TPD,
        "manifest_BHP_exact": ood_manifest.get("producer_bhp_psi") == PRODUCER_BHP_PSI,
        "manifest_target_days_exact": ood_manifest.get("target_days") == TARGET_DAYS,
        "manifest_Y_shape_exact": ood_manifest.get("Y_shape_each") == EXPECTED_Y_SHAPE,
        "manifest_case_ids_exact": manifest_ids == EXPECTED_OOD_CASE_IDS,
        "manifest_sealed_true": ood_manifest.get("sealed") is True,
        "manifest_not_opened_for_model_evaluation": ood_manifest.get("OOD_targets_not_opened_for_model_evaluation") is True,
        "manifest_future_opening_rule": (
            ood_manifest.get("future_opening_requires")
            == "separately frozen one-touch final OOD evaluation contract"
        ),
    })

    case_hashes_ok = True
    case_status_ok = True
    case_partition_ok = True
    artifact_inventory = []
    by_id = {record["case_id"]: record for record in manifest_cases if "case_id" in record}

    for case_id in EXPECTED_OOD_CASE_IDS:
        record = by_id.get(case_id)
        if record is None:
            case_hashes_ok = case_status_ok = case_partition_ok = False
            continue

        artifact = case_artifact_path(case_id)
        actual_sha = sha256(artifact) if artifact.exists() else None
        expected_sha = record.get("artifact_sha256")
        hash_ok = artifact.exists() and expected_sha is not None and actual_sha == expected_sha
        status_ok = record.get("status") == "CERTIFIED"
        partition_ok = record.get("partition") == "LOCKED_OOD_TEST"

        case_hashes_ok = case_hashes_ok and hash_ok
        case_status_ok = case_status_ok and status_ok
        case_partition_ok = case_partition_ok and partition_ok

        artifact_inventory.append({
            "case_id": case_id,
            "artifact_path": str(artifact.relative_to(R)),
            "artifact_sha256": expected_sha,
            "hash_verified_without_np_load": bool(hash_ok),
            "target_array_opened_in_D31D": False,
        })

    gates.update({
        "all_9_case_artifact_SHA_exact": case_hashes_ok,
        "all_9_case_status_CERTIFIED": case_status_ok,
        "all_9_case_partition_locked_OOD": case_partition_ok,
        "no_OOD_np_load_in_D31D": True,
        "no_OOD_target_statistics_in_D31D": True,
    })

    evaluation_contract = {
        "contract_id": "V16D_CONTROLSPACE_LOCKED_OOD_ONE_TOUCH_FINAL_EVALUATION_1.0",
        "milestone": "V16D-31D",
        "scientific_role": "Pre-registered final evaluation protocol for the unseen geology0029 control-space LOCKED_OOD_TEST partition.",
        "generalization_unit": "complete Foundation Case = one geology realization + one rate/BHP control pair",
        "locked_OOD_identity": {
            "partition": "LOCKED_OOD_TEST",
            "geology": "0029",
            "case_ids": EXPECTED_OOD_CASE_IDS,
            "rates_tpd": RATES_TPD,
            "producer_bhp_psi": PRODUCER_BHP_PSI,
            "target_days": TARGET_DAYS,
            "target_shape_each": EXPECTED_Y_SHAPE,
            "expected_predictor_shape_each": EXPECTED_X_SHAPE,
            "sealed_manifest_sha256": EXPECTED_SHA["D31CR1_manifest"],
            "sealed_summary_sha256": EXPECTED_SHA["D31CR1_summary"],
        },
        "preconditions_before_any_OOD_target_array_may_be_opened": {
            "single_model_only": True,
            "architecture_must_be_frozen_by_SHA256": True,
            "checkpoint_must_be_frozen_by_SHA256": True,
            "predictor_feature_order_must_be_frozen": True,
            "TRAIN_only_normalization_authority_must_be_frozen_by_SHA256": True,
            "normalization_fit_may_use": ["TRAIN"],
            "normalization_transform_only": ["VALIDATION", "LOCKED_OOD_TEST"],
            "checkpoint_selection_may_use": ["VALIDATION"],
            "checkpoint_selection_may_not_use": ["LOCKED_OOD_TEST"],
            "model_selection_complete_before_opening": True,
            "validation_metrics_frozen_before_opening": True,
            "final_evaluator_source_must_be_frozen_by_SHA256_before_execution": True,
            "all_9_OOD_artifact_hashes_must_match_this_contract": True,
        },
        "one_touch_semantics": {
            "preflight_before_opening": "All model/checkpoint/normalization/predictor/OOD artifact hashes must pass before any OOD target np.load.",
            "opening_marker": "Immediately before loading the first OOD Y_transport array, the future evaluator must atomically create OOD_OPENED.lock.",
            "rerun_rule": "If OOD_OPENED.lock exists, the final evaluator must refuse to run again under this experiment.",
            "failure_after_opening": "A failure after OOD_OPENED.lock consumes the one-touch evaluation; it may be audited but not repeated or tuned against.",
            "output_directory_rule": "The future final-evaluation output directory must be new and empty before the opening marker is created.",
            "one_checkpoint": "Exactly one frozen validation-selected checkpoint is evaluated.",
            "no_candidate_comparison": "No architecture/checkpoint/candidate ranking is permitted on OOD.",
        },
        "prediction_semantics": {
            "input_unit": "one streamline sequence of 201 Pollock nodes",
            "prediction_target": "Stage-4 saturation Sw",
            "prediction_shape_per_case": EXPECTED_Y_SHAPE,
            "Pollock_role": "AUTHORITATIVE_KINEMATICS",
            "M_face_role": "PHYSICS_SIDECAR_NOT_PREDICTOR",
            "FMM_ADV_role": "AUXILIARY_PREDICTORS_ONLY_IF_ALREADY_FROZEN_IN_FEATURE_ORDER",
            "no_OOD_adaptation": True,
        },
        "predeclared_final_metrics": {
            "primary_aggregate": [
                "MSE = mean((P-Y)^2) over all 9 cases, 9 times, 1078 streamlines, 201 nodes",
                "RMSE = sqrt(MSE)",
                "MAE = mean(abs(P-Y))",
            ],
            "secondary_aggregate": [
                "mean_signed_error = mean(P-Y)",
                "max_abs_error = max(abs(P-Y))",
                "prediction_min",
                "prediction_max",
            ],
            "case_level": [
                "MSE", "RMSE", "MAE", "mean_signed_error", "max_abs_error",
                "prediction_min", "prediction_max",
            ],
            "time_resolved": {
                "times_days": TARGET_DAYS,
                "metrics": ["MSE", "RMSE", "MAE", "max_abs_error"],
                "aggregation": "all 9 OOD control cases x 1078 streamlines x 201 nodes at each predeclared time",
            },
            "control_resolved": {
                "by_injection_rate_tpd": RATES_TPD,
                "by_producer_bhp_psi": PRODUCER_BHP_PSI,
                "metrics": ["RMSE", "MAE"],
                "purpose": "predeclared descriptive control-space generalization audit; never used for model selection or retraining",
            },
            "prediction_physics_diagnostics": [
                "fraction predictions below frozen Swc",
                "fraction predictions above frozen 1-Sor",
                "maximum lower-bound violation",
                "maximum upper-bound violation",
                "injector-node absolute error versus frozen injection boundary",
                "temporal_negative_fraction using threshold -1e-8",
                "spatial_positive_fraction using threshold +1e-8",
            ],
            "validation_generalization_gap": [
                "OOD_RMSE / frozen_validation_RMSE",
                "OOD_MAE / frozen_validation_MAE",
            ],
            "metric_precision": "accumulate error sums in float64 even if model prediction tensors are float32",
            "missing_or_nonfinite_policy": "Any missing, shape-mismatched, or nonfinite prediction/target blocks make the one-touch evaluation INVALID; no adaptive repair or re-evaluation is permitted after opening.",
        },
        "claim_policy": {
            "OOD_is_final_test_not_tuning_signal": True,
            "no_new_OOD_threshold_invention": True,
            "no_pass_fail_threshold_fitted_to_OOD": True,
            "validation_derived_claim_threshold_if_any": "must be frozen before OOD opening in the model/checkpoint freeze",
            "report_results_even_if_poor": True,
            "no_result_suppression": True,
            "no_case_exclusion": True,
            "no_time_exclusion": True,
            "no_streamline_exclusion": True,
            "no_node_exclusion": True,
            "no_control_exclusion": True,
            "no_deduplication": True,
        },
        "post_opening_firewall": {
            "retraining_same_experiment": "PROHIBITED",
            "checkpoint_change": "PROHIBITED",
            "architecture_change": "PROHIBITED",
            "feature_change": "PROHIBITED",
            "normalization_change": "PROHIBITED",
            "loss_change": "PROHIBITED",
            "hyperparameter_change": "PROHIBITED",
            "threshold_tuning": "PROHIBITED",
            "case_reweighting": "PROHIBITED",
            "control_reweighting": "PROHIBITED",
            "OOD_informed_model_selection": "PROHIBITED",
            "allowed_after_opening": "scientific interpretation and explicitly labeled post-OOD diagnostics using the same frozen predictions/checkpoint; any new learning experiment requires a new independently locked test set",
        },
        "execution_in_D31D": {
            "model_training": False,
            "model_inference": False,
            "validation_evaluation": False,
            "OOD_target_np_load": False,
            "OOD_model_evaluation": False,
            "OOD_statistics": False,
            "contract_freeze_only": True,
        },
        "future_required_binding": {
            "note": "D31D intentionally does not invent or bind a checkpoint that does not yet exist for the new control-space learning experiment.",
            "must_be_bound_before_one_touch": [
                "training dataset registry SHA-256",
                "predictor feature-order contract SHA-256",
                "TRAIN-only normalization statistics SHA-256",
                "model architecture SHA-256",
                "selected checkpoint SHA-256",
                "validation-selection summary SHA-256",
                "final evaluator source SHA-256",
            ],
        },
    }

    gates.update({
        "one_touch_rule_frozen": True,
        "OOD_open_marker_required": True,
        "rerun_after_open_prohibited": True,
        "single_checkpoint_only": True,
        "validation_selection_only": True,
        "TRAIN_only_normalization": True,
        "OOD_transform_only": True,
        "metrics_predeclared_before_model_training": True,
        "case_level_metrics_predeclared": True,
        "time_resolved_metrics_predeclared": True,
        "control_resolved_metrics_predeclared": True,
        "physics_diagnostics_predeclared": True,
        "no_OOD_threshold_fitting": True,
        "no_OOD_model_selection": True,
        "no_OOD_retraining": True,
        "no_deduplication": True,
        "no_case_time_streamline_node_exclusion": True,
        "poor_results_must_be_reported": True,
        "no_model_training_in_D31D": True,
        "no_model_inference_in_D31D": True,
        "no_OOD_evaluation_in_D31D": True,
        "contract_only": True,
    })

    ok = bool(all(gates.values()))
    status = (
        "V16D_CONTROLSPACE_LOCKED_OOD_ONE_TOUCH_FINAL_EVALUATION_CONTRACT_FROZEN_OOD_REMAINS_SEALED_LEARNING_DATASET_ASSEMBLY_AUTHORIZED"
        if ok else "V16D_D31D_ONE_TOUCH_OOD_EVALUATION_CONTRACT_BLOCKED"
    )
    next_milestone = (
        "V16D-32 — Control-space 36-case Stage-4 learning dataset assembly + TRAIN-only normalization contract"
        if ok else "Repair D31D provenance/firewall gate; keep OOD sealed."
    )

    report = {
        "milestone": "V16D-31D",
        "status": status,
        "upstream_sha256": EXPECTED_SHA,
        "sealed_OOD_artifact_inventory": artifact_inventory,
        "evaluation_contract": evaluation_contract,
        "gates": gates,
        "next_milestone": next_milestone,
    }

    contract_path = O / "V16D31D_OneTouch_Final_Locked_OOD_Evaluation_Contract.json"
    contract_path.write_text(json.dumps(report, indent=2))

    summary_path = O / "PAD_Stream_V16D31D_Summary.json"
    summary_path.write_text(json.dumps({
        "milestone": "V16D-31D",
        "status": status,
        "contract_sha256": sha256(contract_path),
        "sealed_OOD_manifest_sha256": EXPECTED_SHA["D31CR1_manifest"],
        "sealed_OOD_summary_sha256": EXPECTED_SHA["D31CR1_summary"],
        "OOD_opened": False,
        "OOD_evaluated": False,
        "model_trained": False,
        "model_inference": False,
        "one_touch_protocol_frozen": bool(ok),
        "next_milestone": next_milestone,
    }, indent=2))

    print("\nGATES")
    for name, passed in gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    print("\nSTATUS\n ", status)
    print("\nLOCKED-OOD STATUS")
    print("  SEALED — no Y_transport array opened; no model evaluation performed.")
    print("\nONE-TOUCH RULE")
    print("  The future evaluator may open geology0029 exactly once, only after")
    print("  architecture/checkpoint/normalization/validation selection are frozen.")
    print("  OOD_OPENED.lock will permanently consume that final evaluation.")
    print("\nNEXT\n ", next_milestone)
    print("\nContract SHA-256:", sha256(contract_path))
    print("Summary SHA-256 :", sha256(summary_path))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
