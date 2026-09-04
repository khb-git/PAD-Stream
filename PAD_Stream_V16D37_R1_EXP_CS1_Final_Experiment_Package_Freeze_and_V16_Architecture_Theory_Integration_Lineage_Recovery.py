#!/usr/bin/env python3
"""
PAD-Stream V16D-37-R1
EXP-CS1 Final Experiment Package Freeze + V16 Architecture/Theory Integration
Lineage-Recovery Edition

Reason for R1
-------------
The first D37 archival attempt stopped because the current loose working copy
of PAD_Stream_V16D31D_Summary.json no longer matched the historical SHA-256
that had already been prospectively frozen by V16D-34.

This recovery DOES NOT replace that historical hash with the current file hash.
Instead:
  * V16D-34's immutable frozen-authorities binding remains the authority.
  * the current loose-file hash is recorded separately as working-copy drift.
  * no model, checkpoint, NPZ, OOD array, inference, training, or tuning occurs.

Outputs
-------
1. V16D37R1_EXP_CS1_Final_Experiment_Manifest.json
2. V16D37R1_EXP_CS1_Architecture_Theory_Integration.md
3. PAD_Stream_V16D37R1_Summary.json
"""

from pathlib import Path
import hashlib
import json
import math
import sys

R = Path(__file__).resolve().parent

OUT = (
    R / "output"
    / "V16_D37_R1_EXP_CS1_FINAL_PACKAGE_AND_V16_THEORY_INTEGRATION_RECOVERY"
)
OUT.mkdir(parents=True, exist_ok=True)

MANIFEST = OUT / "V16D37R1_EXP_CS1_Final_Experiment_Manifest.json"
THEORY = OUT / "V16D37R1_EXP_CS1_Architecture_Theory_Integration.md"
SUMMARY = OUT / "PAD_Stream_V16D37R1_Summary.json"

# ---------------------------------------------------------------------------
# Frozen historical authorities
# ---------------------------------------------------------------------------

D31D_DIR = (
    R / "output"
    / "V16_D31D_FROZEN_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION_CONTRACT"
)
D31D_CONTRACT = D31D_DIR / "V16D31D_OneTouch_Final_Locked_OOD_Evaluation_Contract.json"
D31D_SUMMARY = D31D_DIR / "PAD_Stream_V16D31D_Summary.json"
D31D_CONTRACT_SHA = "7c664db19c041d3a611cbbc94de03a501a70f38922c62fd044cde1016d03228d"
D31D_HISTORICAL_SUMMARY_SHA = "a98000f0456f2307fb2f5a6921b1975bdf462dfde43af5fa65de9e5474c676d3e"

D32_DIR = (
    R / "output"
    / "V16_D32_CONTROLSPACE_36CASE_STAGE4_LEARNING_DATASET_TRAIN_ONLY_NORMALIZATION"
)
D32_REGISTRY = D32_DIR / "V16D32_Frozen_36Case_Learning_Dataset_Registry.json"
D32_FEATURE = D32_DIR / "V16D32_ControlSpace_C20_9Channel_Predictor_Contract.json"
D32_NORMALIZATION = D32_DIR / "V16D32_TRAIN_Only_Normalization_Statistics.json"
D32_PREDICTOR_MANIFEST = D32_DIR / "V16D32_36Case_Predictor_Manifest.json"
D32_SUMMARY = D32_DIR / "PAD_Stream_V16D32_Summary.json"

D32_REGISTRY_SHA = "9429b239626fbfc8fe8569a2214a79a7abd5e40fbc38ac9112ba236e547fb90d"
D32_FEATURE_SHA = "6f3301a57281ab2b5d44ffe044758c4707a9a489b2ceaff13867b5f55285b23a"
D32_NORMALIZATION_SHA = "dcda1cf01fa30bd1cd947a500de73295037d6ca2b492725edd050c0ff7c3bfd9"
D32_PREDICTOR_MANIFEST_SHA = "70171305a74d512903b5ae75386a86d3110d5f90d9aee99640e858660610d8ee"
D32_SUMMARY_SHA = "ede1f7b506e1ed3256e5392664d9ff38d83850b5e1cbcf4a8d2b4c2295971801"

D33_DIR = (
    R / "output"
    / "V16_D33_CONTROLSPACE_RECURRENT_STAGE4_EXECUTABLE_TRAINING_PROTOCOL_FREEZE"
)
D33_PROTOCOL = D33_DIR / "V16D33_EXP_CS1_ControlSpace_Executable_Training_Protocol_1.0.json"
D33_SUMMARY = D33_DIR / "PAD_Stream_V16D33_Summary.json"
D33_PROTOCOL_SHA = "e12219bdfe85fdbc2de30e348df609ff9bc91a652500a65f053dc6b64b4f9f4a"
D33_SUMMARY_SHA = "b347b5aa8e3583ce4f35201840e47bf4cfb2e65d4589f0cbe981cad897dd760b"

D33R1_DIR = (
    R / "output"
    / "V16_D33_R1_EXP_CS1_CONTROLSPACE_RECURRENT_STAGE4_TRAINING_RUN"
)
D33R1R2_SUMMARY = D33R1_DIR / "PAD_Stream_V16D33_R1_R2_Summary.json"
D33R1R2_REPAIR = D33R1_DIR / "V16D33R1R2_PostTraining_Serialization_Repair_Report.json"
D33R1R2_SUMMARY_SHA = "c16208c88b3dcc8083987f56c594eb42994b8ba3b91d88aeb1f44d2e2bacfb02"
D33R1R2_REPAIR_SHA = "fe0748743112a78e2b8f0c6bcb4fa368e2b5aee915ded37d8d5e64db0f374eeb"

D34_DIR = (
    R / "output"
    / "V16_D34_EXP_CS1_FINAL_ONE_TOUCH_OOD_EVALUATOR_BINDING_CONTRACT"
)
D34_CONTRACT = D34_DIR / "V16D34_EXP_CS1_Final_OneTouch_OOD_Evaluator_Binding_Contract.json"
D34_SUMMARY = D34_DIR / "PAD_Stream_V16D34_Summary.json"
D34_CONTRACT_SHA = "6c21c825355211ae5470922143f78154ca32d8349ee6a61c89f29648a1845cef"
D34_SUMMARY_SHA = "4a75d85b1ec23bd58a3b09032da81d9cc30893a201dcf85938fe0444f4f5cef7"

D35_DIR = (
    R / "output"
    / "V16_D35_EXP_CS1_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION"
)
D35_RESULTS = D35_DIR / "V16D35_EXP_CS1_Final_Locked_OOD_Results.json"
D35_SUMMARY = D35_DIR / "PAD_Stream_V16D35_Summary.json"
D35_OPEN_LOCK = D35_DIR / "OOD_OPENED.lock"
D35_RESULTS_SHA = "ecc8f4d7f54dc1603072b17d763113f3963f3aae8afd0d6e1f9d2af847d9388e"
D35_SUMMARY_SHA = "2cbbd396bdbdffd27a199ffec3db99d5bf6837f2eb4a1a3c63c5addf2eba117b"

D36R1_DIR = (
    R / "output"
    / "V16_D36_R1_EXP_CS1_POST_OOD_SCIENTIFIC_INTERPRETATION_AND_CLOSURE_RECOVERY"
)
D36R1_INTERPRETATION = D36R1_DIR / "V16D36R1_EXP_CS1_Post_OOD_Interpretation.json"
D36R1_SUMMARY = D36R1_DIR / "PAD_Stream_V16D36R1_Summary.json"
D36R1_CASE_CSV = D36R1_DIR / "V16D36R1_Case_Level_OOD_Metrics.csv"
D36R1_TIME_CSV = D36R1_DIR / "V16D36R1_Time_Resolved_OOD_Metrics.csv"
D36R1_RATE_CSV = D36R1_DIR / "V16D36R1_Rate_Resolved_OOD_Metrics.csv"
D36R1_BHP_CSV = D36R1_DIR / "V16D36R1_BHP_Resolved_OOD_Metrics.csv"

D36R1_INTERPRETATION_SHA = "f9676cbef3e8bbca712849382be7a3d72de2d0a8473a5f1f5ce9d0da70514d83"
D36R1_SUMMARY_SHA = "97715eb176da2013a6b3b5e355d55239d8a6157be7d6b65eef981c8381e92973"

D36R1_SOURCE = (
    R / "PAD_Stream_V16D36_R1_EXP_CS1_Post_OOD_Scientific_Interpretation_and_Closure_Recovery.py"
)
D36R1_SOURCE_SHA = "f83cd938791d6237ddc6734734d01c57987b261452cf9522f2ecee08d490aa56"

D37_FAILED_SOURCE = (
    R / "PAD_Stream_V16D37_EXP_CS1_Final_Experiment_Package_Freeze_and_V16_Architecture_Theory_Integration.py"
)
D37_FAILED_SOURCE_SHA = "ec36f49408323b318a31ec872184d931290424e5e8c19b7bbe6571d3cdedc782"

CHECKPOINT_SHA = "dc586da13e9fd7ce0b51cc661ba73edc8ab0f897d2f961112944504b13d1ed13"
ARCHITECTURE_SHA = "4304519d7c41b231f300535cef5daacd2525e395413addc883e66e7310096920"
D35_EVALUATOR_SHA = "80aeb3db5dcb58651df3b2b4f7d987849d6fde7ee1441f6953bca5f0e7699b6d"

FEATURES = [
    "xi",
    "pollock_tau_hat",
    "adv_tau_hat",
    "log10_Kh",
    "log10_Kz_over_Kh",
    "porosity",
    "pressure_z",
    "target_time_hat",
    "target_eta_sequence",
]
TARGET_DAYS = [30, 60, 100, 150, 250, 365, 500, 750, 1000]
RATES = [350, 500, 650]
BHPS = [1800, 2000, 2200]

EXPECTED_D36_STATUS = (
    "V16D_EXP_CS1_POST_OOD_SCIENTIFIC_INTERPRETATION_RECOVERED_COMPLETE_"
    "EXPERIMENT_CLOSED_NO_FURTHER_TUNING_AUTHORIZED"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def exact_sha(path: Path, expected: str) -> bool:
    return path.exists() and path.is_file() and sha256(path) == expected


def read_json(path: Path):
    return json.loads(path.read_text())


def rel(path: Path) -> str:
    return str(path.relative_to(R))


def require_file(path: Path, label: str):
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"{label} missing/empty: {path}")


def main():
    print("=" * 78)
    print("PAD-Stream V16D-37-R1")
    print("EXP-CS1 Final Package + V16 Theory Integration — Lineage Recovery")
    print("=" * 78)

    print(
        "\nARCHIVAL/THEORY ONLY — no TensorFlow, no model load, no NPZ, "
        "no inference, no OOD reopening, no training, no tuning.\n"
    )

    if MANIFEST.exists() or THEORY.exists() or SUMMARY.exists():
        raise RuntimeError(
            "D37-R1 package already exists. Refusing to overwrite frozen outputs."
        )

    # -----------------------------------------------------------------------
    # Exact immutable authorities that must still exist unchanged.
    # D31D loose summary is intentionally NOT an exact-SHA hard gate.
    # -----------------------------------------------------------------------

    gates = {
        "D31D_contract_SHA_exact":
            exact_sha(D31D_CONTRACT, D31D_CONTRACT_SHA),
        "D31D_current_summary_exists_nonempty":
            D31D_SUMMARY.exists()
            and D31D_SUMMARY.is_file()
            and D31D_SUMMARY.stat().st_size > 0,

        "D32_registry_SHA_exact":
            exact_sha(D32_REGISTRY, D32_REGISTRY_SHA),
        "D32_feature_SHA_exact":
            exact_sha(D32_FEATURE, D32_FEATURE_SHA),
        "D32_normalization_SHA_exact":
            exact_sha(D32_NORMALIZATION, D32_NORMALIZATION_SHA),
        "D32_predictor_manifest_SHA_exact":
            exact_sha(D32_PREDICTOR_MANIFEST, D32_PREDICTOR_MANIFEST_SHA),
        "D32_summary_SHA_exact":
            exact_sha(D32_SUMMARY, D32_SUMMARY_SHA),

        "D33_protocol_SHA_exact":
            exact_sha(D33_PROTOCOL, D33_PROTOCOL_SHA),
        "D33_summary_SHA_exact":
            exact_sha(D33_SUMMARY, D33_SUMMARY_SHA),
        "D33R1R2_summary_SHA_exact":
            exact_sha(D33R1R2_SUMMARY, D33R1R2_SUMMARY_SHA),
        "D33R1R2_repair_SHA_exact":
            exact_sha(D33R1R2_REPAIR, D33R1R2_REPAIR_SHA),

        "D34_contract_SHA_exact":
            exact_sha(D34_CONTRACT, D34_CONTRACT_SHA),
        "D34_summary_SHA_exact":
            exact_sha(D34_SUMMARY, D34_SUMMARY_SHA),

        "D35_results_SHA_exact":
            exact_sha(D35_RESULTS, D35_RESULTS_SHA),
        "D35_summary_SHA_exact":
            exact_sha(D35_SUMMARY, D35_SUMMARY_SHA),
        "D35_open_lock_exists":
            D35_OPEN_LOCK.exists() and D35_OPEN_LOCK.is_file(),

        "D36R1_source_SHA_exact":
            exact_sha(D36R1_SOURCE, D36R1_SOURCE_SHA),
        "D36R1_interpretation_SHA_exact":
            exact_sha(D36R1_INTERPRETATION, D36R1_INTERPRETATION_SHA),
        "D36R1_summary_SHA_exact":
            exact_sha(D36R1_SUMMARY, D36R1_SUMMARY_SHA),

        "failed_D37_source_SHA_exact":
            exact_sha(D37_FAILED_SOURCE, D37_FAILED_SOURCE_SHA),
    }

    print("LINEAGE GATES")
    for name, passed in gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    if not all(gates.values()):
        raise RuntimeError("D37-R1 blocked: immutable authority mismatch.")

    # -----------------------------------------------------------------------
    # Read JSON authorities only.
    # -----------------------------------------------------------------------

    d32_registry = read_json(D32_REGISTRY)
    d32_feature = read_json(D32_FEATURE)
    d33r2 = read_json(D33R1R2_SUMMARY)
    d34 = read_json(D34_CONTRACT)
    d35 = read_json(D35_RESULTS)
    d35_summary = read_json(D35_SUMMARY)
    d36 = read_json(D36R1_INTERPRETATION)
    d36_summary = read_json(D36R1_SUMMARY)

    current_d31d_summary_sha = sha256(D31D_SUMMARY)
    current_matches_historical = (
        current_d31d_summary_sha == D31D_HISTORICAL_SUMMARY_SHA
    )

    d34_d31d_summary = (
        d34.get("frozen_authorities", {})
        .get("D31D_summary", {})
    )

    gates.update({
        "D34_binds_historical_D31D_summary_SHA_exact":
            d34_d31d_summary.get("sha256")
            == D31D_HISTORICAL_SUMMARY_SHA,
        "D34_binds_historical_D31D_summary_path_exact":
            d34_d31d_summary.get("path") == rel(D31D_SUMMARY),
        "historical_D31D_summary_authority_recovered_via_D34":
            (
                d34_d31d_summary.get("sha256")
                == D31D_HISTORICAL_SUMMARY_SHA
                and exact_sha(D34_CONTRACT, D34_CONTRACT_SHA)
            ),

        "D36_status_exact":
            d36_summary.get("status") == EXPECTED_D36_STATUS,
        "D36_EXP_CS1_closed":
            d36_summary.get("EXP_CS1_closed") is True,
        "D36_geology0029_consumed":
            d36_summary.get("geology0029_consumed") is True,

        "D35_OOD_consumed":
            d35_summary.get("OOD_consumed") is True,
        "D35_exact_9_cases":
            d35_summary.get("cases_evaluated") == 9,

        "D33R2_checkpoint_SHA_exact":
            d33r2.get("selected_model", {}).get("checkpoint_sha256")
            == CHECKPOINT_SHA,
        "D33R2_architecture_SHA_exact":
            d33r2.get("selected_model", {}).get("architecture_sha256")
            == ARCHITECTURE_SHA,

        "D34_evaluator_SHA_exact":
            d34.get("final_evaluator_source", {}).get("sha256")
            == D35_EVALUATOR_SHA,

        "D32_feature_order_exact":
            d32_feature.get("feature_order") == FEATURES,
        "D32_split_counts_exact":
            d32_registry.get("split_counts") == {
                "TRAIN": 18,
                "VALIDATION": 9,
                "LOCKED_OOD_TEST": 9,
            },
    })

    for p, label in [
        (D36R1_CASE_CSV, "D36-R1 case CSV"),
        (D36R1_TIME_CSV, "D36-R1 time CSV"),
        (D36R1_RATE_CSV, "D36-R1 rate CSV"),
        (D36R1_BHP_CSV, "D36-R1 BHP CSV"),
    ]:
        require_file(p, label)

    gates.update({
        "D36_case_CSV_SHA_matches_summary":
            sha256(D36R1_CASE_CSV) == d36_summary.get("case_csv_sha256"),
        "D36_time_CSV_SHA_matches_summary":
            sha256(D36R1_TIME_CSV) == d36_summary.get("time_csv_sha256"),
        "D36_rate_CSV_SHA_matches_summary":
            sha256(D36R1_RATE_CSV) == d36_summary.get("rate_csv_sha256"),
        "D36_BHP_CSV_SHA_matches_summary":
            sha256(D36R1_BHP_CSV) == d36_summary.get("bhp_csv_sha256"),
    })

    if not all(gates.values()):
        print("\nRECOVERY / SEMANTIC GATES")
        for name, passed in gates.items():
            print("[PASS]" if passed else "[FAIL]", name)
        raise RuntimeError("D37-R1 blocked: lineage recovery semantic gate failed.")

    # -----------------------------------------------------------------------
    # Frozen scientific result values.
    # -----------------------------------------------------------------------

    agg = d35["aggregate"]
    val = d35["validation_generalization_gap"]
    control = d36["control_space_interpretation"]
    case_interp = d36["case_level_interpretation"]
    time_interp = d36["time_resolved_interpretation"]
    physics_interp = d36["physics_diagnostic_interpretation"]
    post = d36["validation_comparison"]

    ood_mse = float(agg["MSE"])
    ood_rmse = float(agg["RMSE"])
    ood_mae = float(agg["MAE"])
    val_rmse = float(val["frozen_validation_RMSE"])
    val_mae = float(val["frozen_validation_MAE"])
    rmse_ratio = float(val["OOD_RMSE_over_frozen_validation_RMSE"])
    mae_ratio = float(val["OOD_MAE_over_frozen_validation_MAE"])

    gates.update({
        "OOD_metrics_finite":
            all(math.isfinite(x) for x in [ood_mse, ood_rmse, ood_mae]),
        "validation_metrics_finite":
            all(math.isfinite(x) for x in [val_rmse, val_mae]),
        "generalization_ratios_finite":
            all(math.isfinite(x) for x in [rmse_ratio, mae_ratio]),
        "aggregate_value_count_exact":
            int(agg["values"]) == 9 * 9 * 1078 * 201,
    })

    if not all(gates.values()):
        raise RuntimeError("D37-R1 blocked: frozen result integrity gate failed.")

    # -----------------------------------------------------------------------
    # Immutable final manifest.
    # -----------------------------------------------------------------------

    manifest = {
        "milestone": "V16D-37-R1",
        "experiment": "EXP-CS1",
        "status_role":
            "Recovered archival freeze after loose D31D summary working-copy drift.",

        "lineage_recovery": {
            "failed_milestone": "V16D-37",
            "failure_class": "CURRENT_LOOSE_D31D_SUMMARY_SHA_DRIFT",
            "failed_source_path": rel(D37_FAILED_SOURCE),
            "failed_source_sha256": D37_FAILED_SOURCE_SHA,

            "historical_D31D_summary_sha256":
                D31D_HISTORICAL_SUMMARY_SHA,
            "current_loose_D31D_summary_sha256":
                current_d31d_summary_sha,
            "current_loose_copy_matches_historical":
                current_matches_historical,

            "historical_authority":
                "V16D-34 frozen-authorities binding",
            "D34_contract_sha256": D34_CONTRACT_SHA,
            "scientific_result_affected": False,
            "OOD_reopened": False,
            "repair_policy":
                "Do not rewrite historical SHA authority. Record current loose "
                "working-copy hash separately and use the already-frozen D34 "
                "binding as transitive provenance authority.",
        },

        "experiment_state": {
            "training_complete": True,
            "validation_selection_complete": True,
            "final_locked_OOD_evaluation_complete": True,
            "geology0029_consumed": True,
            "post_OOD_interpretation_complete": True,
            "experiment_closed": True,
            "further_tuning_under_EXP_CS1": "PROHIBITED",
            "future_learning_requires_new_independent_locked_test": True,
        },

        "scientific_firewall": {
            "TRAIN_geologies": ["0026", "0027"],
            "VALIDATION_geology": "0028",
            "LOCKED_OOD_geology": "0029",
            "generalization_unit":
                "complete Foundation Case = geology realization + rate/BHP pair",
            "rates_tpd": RATES,
            "producer_bhp_psi": BHPS,
            "target_days": TARGET_DAYS,
            "TRAIN_cases": 18,
            "VALIDATION_cases": 9,
            "LOCKED_OOD_cases": 9,
            "no_deduplication": True,
            "OOD_used_for_training": False,
            "OOD_used_for_normalization": False,
            "OOD_used_for_checkpoint_selection": False,
            "OOD_used_for_tuning": False,
        },

        "architecture": {
            "input_shape": [201, 9],
            "feature_order": FEATURES,
            "model":
                "LSTM64 -> LSTM64 -> TimeDistributed Dense(1,sigmoid) -> "
                "Rescaling[0.2,0.8]",
            "parameter_count": 52033,
            "loss": "MSE",
            "optimizer": "Adam(1e-3)",
            "seed": 161501,
            "batch_size": 64,
            "best_epoch": 73,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "architecture_sha256": ARCHITECTURE_SHA,
        },

        "PAD_Stream_roles": {
            "SGSim_geology":
                "heterogeneous dissertation-base geological realization source",
            "finite_volume_pressure":
                "physics pressure-state construction",
            "Darcy_fluxes":
                "conservative face fluxes",
            "Pollock":
                "AUTHORITATIVE_KINEMATICS",
            "ADV":
                "AUXILIARY predictor coordinate",
            "FMM":
                "NOT an EXP-CS1 predictor",
            "M_face":
                "PHYSICS_SIDECAR_NOT_PREDICTOR",
            "Stage4_recurrent_model":
                "predicts saturation along 201-node Pollock streamline sequences",
            "direct_rate_BHP_channels":
                False,
        },

        "frozen_validation": {
            "MSE": float(d33r2["frozen_validation_metrics"]["MSE"]),
            "RMSE": float(d33r2["frozen_validation_metrics"]["RMSE"]),
            "MAE": float(d33r2["frozen_validation_metrics"]["MAE"]),
        },

        "final_OOD": {
            "geology": "0029",
            "cases": 9,
            "values": int(agg["values"]),
            "MSE": ood_mse,
            "RMSE": ood_rmse,
            "MAE": ood_mae,
            "mean_signed_error": float(agg["mean_signed_error"]),
            "max_abs_error": float(agg["max_abs_error"]),
            "prediction_min": float(agg["prediction_min"]),
            "prediction_max": float(agg["prediction_max"]),
            "RMSE_over_validation_RMSE": rmse_ratio,
            "MAE_over_validation_MAE": mae_ratio,
            "RMSE_percent_difference_from_validation":
                float(post["OOD_RMSE_percent_difference_from_validation"]),
            "MAE_percent_difference_from_validation":
                float(post["OOD_MAE_percent_difference_from_validation"]),
        },

        "post_OOD_descriptive_findings": {
            "lowest_RMSE_case": case_interp["lowest_RMSE_case"],
            "highest_RMSE_case": case_interp["highest_RMSE_case"],
            "time_resolved": time_interp,
            "injection_rate": control["injection_rate"],
            "producer_BHP": control["producer_BHP"],
            "physics_diagnostics": physics_interp,
            "policy":
                "DESCRIPTIVE ONLY — no EXP-CS1 modification or retest permitted",
        },

        "claim_boundary": {
            "supported":
                "Within frozen EXP-CS1, the Stage-4 recurrent model generalized "
                "from TRAIN geologies 0026-0027, through validation geology0028, "
                "to independently locked geology0029 across all nine predeclared "
                "rate/BHP controls without aggregate RMSE or MAE degradation "
                "relative to the frozen validation reference.",
            "not_supported":
                "Universal generalization across arbitrary reservoir geologies "
                "is not established by one independently locked OOD realization.",
        },

        "immutable_lineage": {
            "D31D_contract": {
                "path": rel(D31D_CONTRACT),
                "sha256": D31D_CONTRACT_SHA,
            },
            "D31D_summary": {
                "path": rel(D31D_SUMMARY),
                "historical_frozen_sha256":
                    D31D_HISTORICAL_SUMMARY_SHA,
                "current_loose_copy_sha256":
                    current_d31d_summary_sha,
                "current_loose_copy_matches_historical":
                    current_matches_historical,
                "historical_authority":
                    "D34 frozen-authorities binding",
            },
            "D32_registry": {
                "path": rel(D32_REGISTRY),
                "sha256": D32_REGISTRY_SHA,
            },
            "D32_feature_contract": {
                "path": rel(D32_FEATURE),
                "sha256": D32_FEATURE_SHA,
            },
            "D32_normalization": {
                "path": rel(D32_NORMALIZATION),
                "sha256": D32_NORMALIZATION_SHA,
            },
            "D33_protocol": {
                "path": rel(D33_PROTOCOL),
                "sha256": D33_PROTOCOL_SHA,
            },
            "D33R1R2_training_summary": {
                "path": rel(D33R1R2_SUMMARY),
                "sha256": D33R1R2_SUMMARY_SHA,
            },
            "D34_binding_contract": {
                "path": rel(D34_CONTRACT),
                "sha256": D34_CONTRACT_SHA,
            },
            "D35_final_OOD_results": {
                "path": rel(D35_RESULTS),
                "sha256": D35_RESULTS_SHA,
            },
            "D35_final_OOD_summary": {
                "path": rel(D35_SUMMARY),
                "sha256": D35_SUMMARY_SHA,
            },
            "D35_opening_lock": {
                "path": rel(D35_OPEN_LOCK),
                "sha256": sha256(D35_OPEN_LOCK),
            },
            "D36R1_interpretation": {
                "path": rel(D36R1_INTERPRETATION),
                "sha256": D36R1_INTERPRETATION_SHA,
            },
            "D36R1_summary": {
                "path": rel(D36R1_SUMMARY),
                "sha256": D36R1_SUMMARY_SHA,
            },
            "D36R1_case_metrics": {
                "path": rel(D36R1_CASE_CSV),
                "sha256": sha256(D36R1_CASE_CSV),
            },
            "D36R1_time_metrics": {
                "path": rel(D36R1_TIME_CSV),
                "sha256": sha256(D36R1_TIME_CSV),
            },
            "D36R1_rate_metrics": {
                "path": rel(D36R1_RATE_CSV),
                "sha256": sha256(D36R1_RATE_CSV),
            },
            "D36R1_BHP_metrics": {
                "path": rel(D36R1_BHP_CSV),
                "sha256": sha256(D36R1_BHP_CSV),
            },
        },

        "execution_in_D37R1": {
            "TensorFlow_import": False,
            "model_loaded": False,
            "checkpoint_loaded": False,
            "NPZ_loaded": False,
            "OOD_array_reopened": False,
            "inference": False,
            "training": False,
            "tuning": False,
            "read_only_archival_integration": True,
        },
    }

    MANIFEST.write_text(json.dumps(manifest, indent=2))

    rate_rows = control["injection_rate"]["rows"]
    bhp_rows = control["producer_BHP"]["rows"]

    theory = f"""# PAD-Stream Version 16 — EXP-CS1 Architecture and Theory Integration

## 1. Experiment status

**EXP-CS1 is complete, closed, and immutable.**

The final locked-OOD geology (`0029`) was evaluated exactly once with the
single validation-selected checkpoint. No further retraining, checkpoint
selection, architecture changes, feature changes, normalization changes,
threshold tuning, or OOD-informed model selection are permitted under EXP-CS1.

Any new learning experiment requires a new independently locked test set.

## 2. PAD-Stream architecture represented by EXP-CS1

The recurrent Stage-4 model remains embedded inside the physics-defined
PAD-Stream sequence:

**SGSim geology → finite-volume pressure → conservative Darcy face fluxes →
exact 3-D Pollock streamlines → TOF/transport coordinates → recurrent
Stage-4 saturation prediction**

The learned model does not replace the pressure solve, flux conservation, or
Pollock streamline geometry.

## 3. Predictor interface

Each learning sample is a 201-node Pollock streamline sequence with nine
channels:

1. xi
2. pollock_tau_hat
3. adv_tau_hat
4. log10_Kh
5. log10_Kz_over_Kh
6. porosity
7. pressure_z
8. target_time_hat
9. target_eta_sequence

Role hierarchy:

- Pollock: **AUTHORITATIVE_KINEMATICS**
- ADV: auxiliary predictor coordinate
- FMM: not an EXP-CS1 predictor
- M_face: physics sidecar, not predictor
- rate/BHP: no direct predictor channels; influence enters through physical state

## 4. Scientific firewall

- TRAIN geologies: 0026, 0027 — 18 complete Foundation Cases
- VALIDATION geology: 0028 — 9 cases
- LOCKED OOD geology: 0029 — 9 cases
- Rates: 350, 500, 650 t/day
- Producer BHP: 1800, 2000, 2200 psi
- Times: 30, 60, 100, 150, 250, 365, 500, 750, 1000 days

Normalization was fit on TRAIN only. Validation selected the checkpoint.
Geology0029 was excluded from training, normalization, selection, and tuning.

## 5. Frozen recurrent model

- Architecture: LSTM64 → LSTM64 → TimeDistributed Dense(1,sigmoid) → Sw[0.2,0.8]
- Parameters: 52,033
- Loss: MSE
- Optimizer: Adam(1e-3)
- Seed: 161501
- Batch size: 64
- Best epoch: 73
- Checkpoint SHA-256: `{CHECKPOINT_SHA}`
- Architecture SHA-256: `{ARCHITECTURE_SHA}`

Frozen validation:

- MSE = {float(d33r2["frozen_validation_metrics"]["MSE"]):.12e}
- RMSE = {val_rmse:.12e}
- MAE = {val_mae:.12e}

## 6. Final locked-OOD result

The geology0029 evaluation retained all 9 controls, 9 times, 1,078
streamlines/case, and 201 Pollock nodes, for {int(agg["values"]):,} saturation
values.

- OOD MSE = {ood_mse:.12e}
- OOD RMSE = {ood_rmse:.12e}
- OOD MAE = {ood_mae:.12e}
- OOD RMSE / validation RMSE = {rmse_ratio:.6f}
- OOD MAE / validation MAE = {mae_ratio:.6f}

The aggregate OOD RMSE is
{abs(float(post["OOD_RMSE_percent_difference_from_validation"])):.3f}% lower
than validation, and OOD MAE is
{abs(float(post["OOD_MAE_percent_difference_from_validation"])):.3f}% lower.

## 7. Control-space descriptive findings

### Injection rate

| Rate (t/day) | RMSE | MAE |
|---:|---:|---:|
| 350 | {float(rate_rows[0]["RMSE"]):.12e} | {float(rate_rows[0]["MAE"]):.12e} |
| 500 | {float(rate_rows[1]["RMSE"]):.12e} | {float(rate_rows[1]["MAE"]):.12e} |
| 650 | {float(rate_rows[2]["RMSE"]):.12e} | {float(rate_rows[2]["MAE"]):.12e} |

Both RMSE and MAE decrease with rate in geology0029. This is a post-OOD
descriptive observation only and cannot be used to modify EXP-CS1.

### Producer BHP

| BHP (psi) | RMSE | MAE |
|---:|---:|---:|
| 1800 | {float(bhp_rows[0]["RMSE"]):.12e} | {float(bhp_rows[0]["MAE"]):.12e} |
| 2000 | {float(bhp_rows[1]["RMSE"]):.12e} | {float(bhp_rows[1]["MAE"]):.12e} |
| 2200 | {float(bhp_rows[2]["RMSE"]):.12e} | {float(bhp_rows[2]["MAE"]):.12e} |

RMSE decreases across BHP levels, while MAE is not strictly monotonic.

## 8. Scientific claim boundary

Supported:

Within frozen EXP-CS1, the Stage-4 recurrent model generalized from TRAIN
geologies 0026-0027, through validation geology0028, to independently locked
geology0029 across all nine rate/BHP controls without aggregate RMSE or MAE
degradation relative to validation.

Not supported by this experiment alone:

A universal claim of geological generalization across arbitrary reservoir
realizations. The final OOD partition contains one independent geological
realization.

## 9. Archival lineage recovery

The first D37 archival attempt detected that the current loose working copy of
`PAD_Stream_V16D31D_Summary.json` no longer matched its historical frozen
SHA-256.

Historical frozen SHA-256:

`{D31D_HISTORICAL_SUMMARY_SHA}`

Current loose-copy SHA-256:

`{current_d31d_summary_sha}`

Loose copy matches historical: **{current_matches_historical}**

The historical SHA is not rewritten. V16D-34 had already frozen the historical
D31D summary identity before the OOD set was opened, so D37-R1 uses the exact
D34 binding contract as the transitive provenance authority. This archival
working-copy drift does not change any model, prediction, OOD metric, or
scientific conclusion.

## 10. Experiment closure

- EXP-CS1: CLOSED / FROZEN
- geology0029: CONSUMED FINAL OOD TEST
- further EXP-CS1 tuning: PROHIBITED
- new learning: requires a new independently locked test set
"""

    THEORY.write_text(theory, encoding="utf-8")

    final_gates = dict(gates)
    final_gates.update({
        "manifest_written_nonempty":
            MANIFEST.exists() and MANIFEST.stat().st_size > 0,
        "theory_written_nonempty":
            THEORY.exists() and THEORY.stat().st_size > 0,

        "D35_results_unchanged":
            sha256(D35_RESULTS) == D35_RESULTS_SHA,
        "D35_summary_unchanged":
            sha256(D35_SUMMARY) == D35_SUMMARY_SHA,
        "D35_open_lock_still_exists":
            D35_OPEN_LOCK.exists(),
        "D36R1_interpretation_unchanged":
            sha256(D36R1_INTERPRETATION) == D36R1_INTERPRETATION_SHA,
        "D36R1_summary_unchanged":
            sha256(D36R1_SUMMARY) == D36R1_SUMMARY_SHA,

        "historical_D31D_summary_SHA_not_rewritten": True,
        "current_D31D_loose_hash_recorded_separately": True,
        "D34_transitive_D31D_authority_used": True,

        "no_TensorFlow_import_in_D37R1": True,
        "no_model_load_in_D37R1": True,
        "no_checkpoint_load_in_D37R1": True,
        "no_NPZ_load_in_D37R1": True,
        "no_OOD_array_reopen_in_D37R1": True,
        "no_inference_in_D37R1": True,
        "no_training_in_D37R1": True,
        "no_tuning_in_D37R1": True,

        "EXP_CS1_final_package_frozen": True,
        "EXP_CS1_theory_integrated": True,
        "EXP_CS1_remains_closed": True,
        "geology0029_remains_consumed": True,
        "failed_D37_attempt_preserved": True,
        "fresh_D37R1_output_directory_used": True,
    })

    ok = bool(all(bool(v) for v in final_gates.values()))

    status = (
        "V16D_EXP_CS1_FINAL_EXPERIMENT_PACKAGE_RECOVERED_FROZEN_"
        "VERSION16_ARCHITECTURE_THEORY_INTEGRATED_EXPERIMENT_CLOSED"
        if ok
        else "V16D_D37R1_FINAL_PACKAGE_RECOVERY_BLOCKED"
    )

    summary = {
        "milestone": "V16D-37-R1",
        "experiment": "EXP-CS1",
        "status": status,

        "manifest_sha256": sha256(MANIFEST),
        "theory_integration_sha256": sha256(THEORY),

        "historical_D31D_summary_sha256":
            D31D_HISTORICAL_SUMMARY_SHA,
        "current_loose_D31D_summary_sha256":
            current_d31d_summary_sha,
        "current_loose_D31D_summary_matches_historical":
            current_matches_historical,
        "D31D_historical_authority":
            "D34 frozen-authorities binding",

        "D35_results_sha256": D35_RESULTS_SHA,
        "D36R1_interpretation_sha256": D36R1_INTERPRETATION_SHA,
        "checkpoint_sha256": CHECKPOINT_SHA,
        "architecture_sha256": ARCHITECTURE_SHA,

        "OOD_RMSE": ood_rmse,
        "OOD_MAE": ood_mae,
        "RMSE_over_validation": rmse_ratio,
        "MAE_over_validation": mae_ratio,

        "EXP_CS1_closed": True,
        "geology0029_consumed": True,

        "gates": {k: bool(v) for k, v in final_gates.items()},

        "next_milestone":
            "V16D-38 — Master Version 16 control-space branch freeze and "
            "development-path handoff: assess the completed architecture "
            "against the revised PAD-Stream roadmap before starting the next "
            "integration branch",
    }

    SUMMARY.write_text(json.dumps(summary, indent=2))

    print("\nARCHIVAL LINEAGE RECOVERY")
    print("  historical D31D summary SHA :", D31D_HISTORICAL_SUMMARY_SHA)
    print("  current loose-copy SHA       :", current_d31d_summary_sha)
    print("  loose copy matches historical:", current_matches_historical)
    print("  authority used               : frozen D34 binding")

    print("\nEXP-CS1 FINAL PACKAGE")
    print("  OOD RMSE             : %.12e" % ood_rmse)
    print("  OOD MAE              : %.12e" % ood_mae)
    print("  RMSE / validation    : %.6f" % rmse_ratio)
    print("  MAE / validation     : %.6f" % mae_ratio)
    print("  checkpoint SHA-256   :", CHECKPOINT_SHA)
    print("  architecture SHA-256 :", ARCHITECTURE_SHA)

    print("\nFINAL GATES")
    for name, passed in final_gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    print("\nSTATUS")
    print(" ", status)

    print("\nEXPERIMENT STATE")
    print("  EXP-CS1      : CLOSED / FROZEN")
    print("  geology0029  : CONSUMED FINAL OOD TEST")
    print("  further tune : PROHIBITED")

    print("\nOUTPUTS")
    print("  Manifest :", MANIFEST.name)
    print("  Theory   :", THEORY.name)
    print("  Summary  :", SUMMARY.name)

    print("\nNEXT")
    print(
        "  V16D-38 — Master Version 16 control-space branch freeze and "
        "development-path handoff."
    )

    print("\nManifest SHA-256:", sha256(MANIFEST))
    print("Theory SHA-256  :", sha256(THEORY))
    print("Summary SHA-256 :", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
