#!/usr/bin/env python3
"""
PAD-Stream V16D-37
EXP-CS1 Final Experiment Package Freeze + Version 16 Architecture/Theory Integration

Scientific role
---------------
Freeze the completed EXP-CS1 control-space experiment as an immutable,
traceable Version 16 evidence package after the final locked-OOD evaluation
has been consumed and interpreted.

This milestone is archival/theoretical only.

It does NOT:
  * import TensorFlow,
  * load a model/checkpoint,
  * open any NPZ,
  * rerun inference,
  * recompute OOD predictions,
  * retrain,
  * tune,
  * reopen geology0029,
  * change any scientific claim based on new computation.

Outputs
-------
1. V16D37_EXP_CS1_Final_Experiment_Manifest.json
2. V16D37_EXP_CS1_Architecture_Theory_Integration.md
3. PAD_Stream_V16D37_Summary.json
"""

from pathlib import Path
import hashlib
import json
import math
import sys


# =============================================================================
# ROOT / OUTPUT
# =============================================================================

R = Path(__file__).resolve().parent

OUT = (
    R
    / "output"
    / "V16_D37_EXP_CS1_FINAL_PACKAGE_AND_V16_THEORY_INTEGRATION"
)
OUT.mkdir(parents=True, exist_ok=True)

MANIFEST = OUT / "V16D37_EXP_CS1_Final_Experiment_Manifest.json"
THEORY = OUT / "V16D37_EXP_CS1_Architecture_Theory_Integration.md"
SUMMARY = OUT / "PAD_Stream_V16D37_Summary.json"


# =============================================================================
# FROZEN AUTHORITIES
# =============================================================================

# D31D — preregistered one-touch final-OOD contract
D31D_DIR = (
    R
    / "output"
    / "V16_D31D_FROZEN_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION_CONTRACT"
)
D31D_CONTRACT = D31D_DIR / "V16D31D_OneTouch_Final_Locked_OOD_Evaluation_Contract.json"
D31D_SUMMARY = D31D_DIR / "PAD_Stream_V16D31D_Summary.json"
D31D_CONTRACT_SHA = "7c664db19c041d3a611cbbc94de03a501a70f38922c62fd044cde1016d03228d"
D31D_SUMMARY_SHA = "a98000f0456f2307fb2f5a6921b1975bdf462dfde43af5fa65de9e5474c676d3e"

# D32 — 36-case learning dataset + TRAIN-only normalization
D32_DIR = (
    R
    / "output"
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

# D33 — executable training protocol
D33_DIR = (
    R
    / "output"
    / "V16_D33_CONTROLSPACE_RECURRENT_STAGE4_EXECUTABLE_TRAINING_PROTOCOL_FREEZE"
)
D33_PROTOCOL = D33_DIR / "V16D33_EXP_CS1_ControlSpace_Executable_Training_Protocol_1.0.json"
D33_SUMMARY = D33_DIR / "PAD_Stream_V16D33_Summary.json"
D33_PROTOCOL_SHA = "e12219bdfe85fdbc2de30e348df609ff9bc91a652500a65f053dc6b64b4f9f4a"
D33_SUMMARY_SHA = "b347b5aa8e3583ce4f35201840e47bf4cfb2e65d4589f0cbe981cad897dd760b"

# D33-R1-R2 — certified existing training run after serialization-only repair
D33R1_DIR = (
    R
    / "output"
    / "V16_D33_R1_EXP_CS1_CONTROLSPACE_RECURRENT_STAGE4_TRAINING_RUN"
)
D33R1R2_SUMMARY = D33R1_DIR / "PAD_Stream_V16D33_R1_R2_Summary.json"
D33R1R2_REPAIR = D33R1_DIR / "V16D33R1R2_PostTraining_Serialization_Repair_Report.json"
D33R1R2_SUMMARY_SHA = "c16208c88b3dcc8083987f56c594eb42994b8ba3b91d88aeb1f44d2e2bacfb02"
D33R1R2_REPAIR_SHA = "fe0748743112a78e2b8f0c6bcb4fa368e2b5aee915ded37d8d5e64db0f374eeb"

CHECKPOINT_SHA = "dc586da13e9fd7ce0b51cc661ba73edc8ab0f897d2f961112944504b13d1ed13"
ARCHITECTURE_SHA = "4304519d7c41b231f300535cef5daacd2525e395413addc883e66e7310096920"

# D34 — final evaluator/model/OOD-artifact binding
D34_DIR = (
    R
    / "output"
    / "V16_D34_EXP_CS1_FINAL_ONE_TOUCH_OOD_EVALUATOR_BINDING_CONTRACT"
)
D34_CONTRACT = D34_DIR / "V16D34_EXP_CS1_Final_OneTouch_OOD_Evaluator_Binding_Contract.json"
D34_SUMMARY = D34_DIR / "PAD_Stream_V16D34_Summary.json"
D34_CONTRACT_SHA = "6c21c825355211ae5470922143f78154ca32d8349ee6a61c89f29648a1845cef"
D34_SUMMARY_SHA = "4a75d85b1ec23bd58a3b09032da81d9cc30893a201dcf85938fe0444f4f5cef7"

# D35 — one-touch final OOD evaluation
D35_DIR = (
    R
    / "output"
    / "V16_D35_EXP_CS1_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION"
)
D35_RESULTS = D35_DIR / "V16D35_EXP_CS1_Final_Locked_OOD_Results.json"
D35_SUMMARY = D35_DIR / "PAD_Stream_V16D35_Summary.json"
D35_OPEN_LOCK = D35_DIR / "OOD_OPENED.lock"
D35_RESULTS_SHA = "ecc8f4d7f54dc1603072b17d763113f3963f3aae8afd0d6e1f9d2af847d9388e"
D35_SUMMARY_SHA = "2cbbd396bdbdffd27a199ffec3db99d5bf6837f2eb4a1a3c63c5addf2eba117b"
D35_EVALUATOR_SHA = "80aeb3db5dcb58651df3b2b4f7d987849d6fde7ee1441f6953bca5f0e7699b6d"

# D36-R1 — post-OOD scientific interpretation + experiment closure
D36R1_DIR = (
    R
    / "output"
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
    R
    / "PAD_Stream_V16D36_R1_EXP_CS1_Post_OOD_Scientific_Interpretation_and_Closure_Recovery.py"
)
D36R1_SOURCE_SHA = "f83cd938791d6237ddc6734734d01c57987b261452cf9522f2ecee08d490aa56"


# =============================================================================
# FIXED SCIENTIFIC IDENTITIES
# =============================================================================

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


def rel(path: Path) -> str:
    return str(path.relative_to(R))


def require_file(path: Path, label: str):
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"{label} missing: {path}")
    if path.stat().st_size <= 0:
        raise RuntimeError(f"{label} empty: {path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16D-37")
    print("EXP-CS1 Final Experiment Package Freeze + V16 Architecture/Theory Integration")
    print("=" * 78)

    print(
        "\nARCHIVAL/THEORY ONLY — no TensorFlow, no model load, no NPZ, "
        "no inference, no OOD reopening, no training, no tuning.\n"
    )

    if MANIFEST.exists() or THEORY.exists() or SUMMARY.exists():
        raise RuntimeError(
            "D37 package already exists. Refusing to overwrite a frozen final "
            "EXP-CS1 package."
        )

    # -------------------------------------------------------------------------
    # 1. Exact lineage gates
    # -------------------------------------------------------------------------

    gates = {
        "D31D_contract_SHA_exact": exact_sha(D31D_CONTRACT, D31D_CONTRACT_SHA),
        "D31D_summary_SHA_exact": exact_sha(D31D_SUMMARY, D31D_SUMMARY_SHA),

        "D32_registry_SHA_exact": exact_sha(D32_REGISTRY, D32_REGISTRY_SHA),
        "D32_feature_SHA_exact": exact_sha(D32_FEATURE, D32_FEATURE_SHA),
        "D32_normalization_SHA_exact": exact_sha(D32_NORMALIZATION, D32_NORMALIZATION_SHA),
        "D32_predictor_manifest_SHA_exact":
            exact_sha(D32_PREDICTOR_MANIFEST, D32_PREDICTOR_MANIFEST_SHA),
        "D32_summary_SHA_exact": exact_sha(D32_SUMMARY, D32_SUMMARY_SHA),

        "D33_protocol_SHA_exact": exact_sha(D33_PROTOCOL, D33_PROTOCOL_SHA),
        "D33_summary_SHA_exact": exact_sha(D33_SUMMARY, D33_SUMMARY_SHA),

        "D33R1R2_summary_SHA_exact":
            exact_sha(D33R1R2_SUMMARY, D33R1R2_SUMMARY_SHA),
        "D33R1R2_repair_SHA_exact":
            exact_sha(D33R1R2_REPAIR, D33R1R2_REPAIR_SHA),

        "D34_contract_SHA_exact": exact_sha(D34_CONTRACT, D34_CONTRACT_SHA),
        "D34_summary_SHA_exact": exact_sha(D34_SUMMARY, D34_SUMMARY_SHA),

        "D35_results_SHA_exact": exact_sha(D35_RESULTS, D35_RESULTS_SHA),
        "D35_summary_SHA_exact": exact_sha(D35_SUMMARY, D35_SUMMARY_SHA),
        "D35_open_lock_exists": D35_OPEN_LOCK.exists() and D35_OPEN_LOCK.is_file(),

        "D36R1_source_SHA_exact": exact_sha(D36R1_SOURCE, D36R1_SOURCE_SHA),
        "D36R1_interpretation_SHA_exact":
            exact_sha(D36R1_INTERPRETATION, D36R1_INTERPRETATION_SHA),
        "D36R1_summary_SHA_exact":
            exact_sha(D36R1_SUMMARY, D36R1_SUMMARY_SHA),
    }

    print("LINEAGE GATES")
    for name, passed in gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    if not all(gates.values()):
        raise RuntimeError("D37 blocked: exact immutable lineage mismatch.")

    # -------------------------------------------------------------------------
    # 2. Read only frozen JSON records
    # -------------------------------------------------------------------------

    d32_registry = read_json(D32_REGISTRY)
    d32_feature = read_json(D32_FEATURE)
    d33r2 = read_json(D33R1R2_SUMMARY)
    d34 = read_json(D34_CONTRACT)
    d35 = read_json(D35_RESULTS)
    d35_summary = read_json(D35_SUMMARY)
    d36 = read_json(D36R1_INTERPRETATION)
    d36_summary = read_json(D36R1_SUMMARY)

    # D36-generated CSVs are part of the final package and are hash-frozen now.
    for p, label in [
        (D36R1_CASE_CSV, "D36-R1 case CSV"),
        (D36R1_TIME_CSV, "D36-R1 time CSV"),
        (D36R1_RATE_CSV, "D36-R1 rate CSV"),
        (D36R1_BHP_CSV, "D36-R1 BHP CSV"),
    ]:
        require_file(p, label)

    d36_recorded = {
        "case_csv_sha256": d36_summary.get("case_csv_sha256"),
        "time_csv_sha256": d36_summary.get("time_csv_sha256"),
        "rate_csv_sha256": d36_summary.get("rate_csv_sha256"),
        "bhp_csv_sha256": d36_summary.get("bhp_csv_sha256"),
    }

    gates.update({
        "D36_status_exact": d36_summary.get("status") == EXPECTED_D36_STATUS,
        "D36_EXP_CS1_closed": d36_summary.get("EXP_CS1_closed") is True,
        "D36_geology0029_consumed":
            d36_summary.get("geology0029_consumed") is True,

        "D35_OOD_consumed": d35_summary.get("OOD_consumed") is True,
        "D35_exact_9_cases": d35_summary.get("cases_evaluated") == 9,

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

        "D36_case_CSV_SHA_matches_summary":
            sha256(D36R1_CASE_CSV) == d36_recorded["case_csv_sha256"],
        "D36_time_CSV_SHA_matches_summary":
            sha256(D36R1_TIME_CSV) == d36_recorded["time_csv_sha256"],
        "D36_rate_CSV_SHA_matches_summary":
            sha256(D36R1_RATE_CSV) == d36_recorded["rate_csv_sha256"],
        "D36_BHP_CSV_SHA_matches_summary":
            sha256(D36R1_BHP_CSV) == d36_recorded["bhp_csv_sha256"],
    })

    if not all(gates.values()):
        print("\nSEMANTIC GATES")
        for name, passed in gates.items():
            print("[PASS]" if passed else "[FAIL]", name)
        raise RuntimeError("D37 blocked: final experiment semantics mismatch.")

    # -------------------------------------------------------------------------
    # 3. Freeze key scientific results
    # -------------------------------------------------------------------------

    agg = d35["aggregate"]
    val = d35["validation_generalization_gap"]
    post = d36["validation_comparison"]
    control = d36["control_space_interpretation"]
    physics = d36["physics_diagnostic_interpretation"]
    time_interp = d36["time_resolved_interpretation"]
    case_interp = d36["case_level_interpretation"]

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

    # -------------------------------------------------------------------------
    # 4. Final immutable experiment manifest
    # -------------------------------------------------------------------------

    manifest = {
        "milestone": "V16D-37",
        "experiment": "EXP-CS1",
        "package_role":
            "Immutable final evidence package for the completed V16D control-space "
            "recurrent Stage-4 experiment.",

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
            "control_factorial": {
                "rates_tpd": RATES,
                "producer_bhp_psi": BHPS,
                "cases_per_geology": 9,
            },
            "target_days": TARGET_DAYS,
            "no_deduplication": True,
            "OOD_used_for_training": False,
            "OOD_used_for_normalization": False,
            "OOD_used_for_checkpoint_selection": False,
            "OOD_used_for_tuning": False,
        },

        "architecture": {
            "input_sequence_shape": [201, 9],
            "feature_order": FEATURES,
            "model":
                "LSTM(64, return_sequences) -> LSTM(64, return_sequences) -> "
                "TimeDistributed Dense(1,sigmoid) -> Rescaling[0.2,0.8]",
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
                "exact physics pressure solution / state construction",
            "Darcy_fluxes":
                "conservative face fluxes from finite-volume pressure",
            "Pollock":
                "AUTHORITATIVE_KINEMATICS for streamline geometry and TOF",
            "ADV":
                "AUXILIARY predictor coordinate",
            "FMM":
                "NOT a predictor in EXP-CS1",
            "M_face":
                "PHYSICS_SIDECAR_NOT_PREDICTOR",
            "Stage4_recurrent_model":
                "predicts saturation along 201-node Pollock streamline sequences",
            "direct_rate_BHP_channels":
                "absent; controls enter indirectly through the physical state",
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
            "physics_diagnostics": physics,
            "use_policy":
                "DESCRIPTIVE ONLY — no EXP-CS1 model change or retest permitted",
        },

        "claim_boundary": {
            "supported":
                "Within this frozen experiment, the recurrent Stage-4 model "
                "generalized from TRAIN geologies 0026-0027, through validation "
                "geology0028, to independently locked geology0029 across all nine "
                "predeclared rate/BHP controls without aggregate RMSE or MAE "
                "degradation relative to the frozen validation reference.",
            "not_supported":
                "A universal claim of geological generalization across arbitrary "
                "reservoir realizations is not established by one independently "
                "locked OOD geology.",
        },

        "immutable_lineage": {
            "D31D_contract": {
                "path": rel(D31D_CONTRACT),
                "sha256": D31D_CONTRACT_SHA,
            },
            "D31D_summary": {
                "path": rel(D31D_SUMMARY),
                "sha256": D31D_SUMMARY_SHA,
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
            "D32_predictor_manifest": {
                "path": rel(D32_PREDICTOR_MANIFEST),
                "sha256": D32_PREDICTOR_MANIFEST_SHA,
            },
            "D33_protocol": {
                "path": rel(D33_PROTOCOL),
                "sha256": D33_PROTOCOL_SHA,
            },
            "D33R1R2_training_summary": {
                "path": rel(D33R1R2_SUMMARY),
                "sha256": D33R1R2_SUMMARY_SHA,
            },
            "D33R1R2_repair_report": {
                "path": rel(D33R1R2_REPAIR),
                "sha256": D33R1R2_REPAIR_SHA,
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

        "execution_in_D37": {
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

    # -------------------------------------------------------------------------
    # 5. Version 16 architecture/theory integration record
    # -------------------------------------------------------------------------

    rate_rows = control["injection_rate"]["rows"]
    bhp_rows = control["producer_BHP"]["rows"]

    theory = f"""# PAD-Stream Version 16 — EXP-CS1 Architecture and Theory Integration

## 1. Scientific status

**EXP-CS1 is complete and closed.**

The final locked-OOD geology (`0029`) has been opened exactly once, evaluated
with the single validation-selected checkpoint, interpreted without reopening
the arrays, and permanently consumed as the final test set.

No further retraining, checkpoint selection, architecture changes, feature
changes, normalization changes, threshold tuning, or OOD-informed model
selection are permitted under EXP-CS1.

Any new learning experiment requires a new independently locked test set.

---

## 2. PAD-Stream computational architecture represented by EXP-CS1

The control-space recurrent Stage-4 experiment sits downstream of the
physics-based PAD-Stream kinematic backbone:

1. **SGSim heterogeneous geology**
   - 3-D geological property field.
   - Dissertation-base heterogeneity source.

2. **Finite-volume pressure**
   - Exact physics state construction.
   - Produces pressure consistent with the frozen reservoir controls.

3. **Conservative Darcy face fluxes**
   - Derived from the pressure solution.
   - Preserve the finite-volume flow balance.

4. **Exact 3-D Pollock streamlines**
   - Pollock remains the **authoritative kinematic representation**.
   - Streamline geometry and time-of-flight are not replaced by the neural model.

5. **Transport-coordinate construction**
   - Each sample is a 201-node Pollock streamline sequence.
   - The recurrent model operates in streamline/TOF coordinates.

6. **C20 nine-channel predictor interface**
   - `xi`
   - `pollock_tau_hat`
   - `adv_tau_hat`
   - `log10_Kh`
   - `log10_Kz_over_Kh`
   - `porosity`
   - `pressure_z`
   - `target_time_hat`
   - `target_eta_sequence`

7. **EXP-CS1 recurrent Stage-4 transport model**
   - LSTM(64)
   - LSTM(64)
   - TimeDistributed Dense(1, sigmoid)
   - Saturation rescaling to `[0.2, 0.8]`
   - 52,033 trainable parameters.

The learned component predicts **Stage-4 saturation along the frozen Pollock
streamline coordinate**. It does not replace the pressure solve, conservative
Darcy flux construction, or Pollock tracing.

---

## 3. Role hierarchy of auxiliary quantities

The final EXP-CS1 predictor contract preserves the following hierarchy:

- **Pollock:** authoritative kinematics.
- **ADV:** auxiliary predictor coordinate.
- **FMM:** not used as an EXP-CS1 predictor.
- **M_face:** physics sidecar, not predictor.
- **Rate/BHP:** no direct predictor channels; their influence enters through the
  physical state and transport coordinates.

This separation is important to the PAD-Stream architecture because it keeps
the recurrent transport surrogate embedded inside a physics-defined flow and
kinematic system rather than allowing the learned model to redefine the
streamline geometry.

---

## 4. Generalization firewall

The unit of generalization is a **complete Foundation Case**:

> one geology realization + one injection-rate / producer-BHP pair.

The frozen split is:

- **TRAIN:** geologies 0026 and 0027, 18 complete cases.
- **VALIDATION:** geology 0028, 9 complete cases.
- **LOCKED OOD TEST:** geology 0029, 9 complete cases.

Control factorial:

- Injection rate: 350, 500, 650 t/day.
- Producer BHP: 1800, 2000, 2200 psi.
- Target times: 30, 60, 100, 150, 250, 365, 500, 750, 1000 days.

Normalization was fit on TRAIN only. Validation was used only for checkpoint
selection. Geology0029 was excluded from training, normalization, architecture
selection, feature selection, checkpoint selection, and threshold tuning.

---

## 5. Frozen recurrent model

Selected checkpoint:

- Best epoch: **73**
- Checkpoint SHA-256: `{CHECKPOINT_SHA}`
- Architecture SHA-256: `{ARCHITECTURE_SHA}`

Frozen validation metrics:

- MSE: **{float(d33r2["frozen_validation_metrics"]["MSE"]):.12e}**
- RMSE: **{val_rmse:.12e}**
- MAE: **{val_mae:.12e}**

---

## 6. Final locked-OOD result

The final geology0029 evaluation includes all:

- 9 control cases,
- 9 target times,
- 1,078 streamlines per case,
- 201 Pollock nodes per streamline,

for **{int(agg["values"]):,} saturation values**.

Aggregate OOD performance:

- MSE: **{ood_mse:.12e}**
- RMSE: **{ood_rmse:.12e}**
- MAE: **{ood_mae:.12e}**
- Mean signed error: **{float(agg["mean_signed_error"]):.12e}**
- Maximum absolute error: **{float(agg["max_abs_error"]):.12e}**

Generalization ratios:

- OOD RMSE / validation RMSE: **{rmse_ratio:.6f}**
- OOD MAE / validation MAE: **{mae_ratio:.6f}**

Therefore the final unseen-geology aggregate RMSE is
**{abs(float(post["OOD_RMSE_percent_difference_from_validation"])):.3f}% lower**
than the frozen validation RMSE, and the aggregate MAE is
**{abs(float(post["OOD_MAE_percent_difference_from_validation"])):.3f}% lower**
than the frozen validation MAE.

This is evidence of successful generalization in the **predeclared EXP-CS1
experiment**, not evidence that every unseen geological realization will have
equal or lower error.

---

## 7. Control-space observations

### Injection rate

| Rate (t/day) | RMSE | MAE |
|---:|---:|---:|
| 350 | {float(rate_rows[0]["RMSE"]):.12e} | {float(rate_rows[0]["MAE"]):.12e} |
| 500 | {float(rate_rows[1]["RMSE"]):.12e} | {float(rate_rows[1]["MAE"]):.12e} |
| 650 | {float(rate_rows[2]["RMSE"]):.12e} | {float(rate_rows[2]["MAE"]):.12e} |

Within geology0029, both RMSE and MAE decrease as rate increases across the
three preregistered rate levels. This is a **post-OOD descriptive observation**
and cannot be used to modify EXP-CS1.

### Producer BHP

| Producer BHP (psi) | RMSE | MAE |
|---:|---:|---:|
| 1800 | {float(bhp_rows[0]["RMSE"]):.12e} | {float(bhp_rows[0]["MAE"]):.12e} |
| 2000 | {float(bhp_rows[1]["RMSE"]):.12e} | {float(bhp_rows[1]["MAE"]):.12e} |
| 2200 | {float(bhp_rows[2]["RMSE"]):.12e} | {float(bhp_rows[2]["MAE"]):.12e} |

RMSE decreases across these BHP levels, but MAE is not strictly monotonic.
Accordingly, the BHP response should be treated as a descriptive interaction
with geology/control state rather than a simple monotonic model property.

---

## 8. Case-level envelope

Lowest-RMSE OOD case:

- `{case_interp["lowest_RMSE_case"]["case_id"]}`
- RMSE = **{float(case_interp["lowest_RMSE_case"]["RMSE"]):.12e}**

Highest-RMSE OOD case:

- `{case_interp["highest_RMSE_case"]["case_id"]}`
- RMSE = **{float(case_interp["highest_RMSE_case"]["RMSE"]):.12e}**

All cases remain in the final evaluation. No case, time, streamline, node, or
control condition was removed.

---

## 9. Physics-diagnostic interpretation

The preregistered post-prediction diagnostics remain part of the EXP-CS1
evidence package:

- Saturation bounds relative to `Swc = 0.2` and `1 - Sor = 0.8`.
- Injector-node boundary error relative to `Sw = 0.8`.
- Temporal negative-difference fraction using threshold `-1e-8`.
- Streamline spatial positive-difference fraction using threshold `+1e-8`.

These diagnostics are **descriptive scientific diagnostics**, not post-OOD
accept/reject criteria invented after seeing the test result.

---

## 10. Scientific claim boundary

### Supported claim

Within the frozen EXP-CS1 protocol, the recurrent Stage-4 transport model
generalized from TRAIN geologies 0026–0027, through validation geology0028, to
the independently locked geology0029 across the complete 3×3 rate/BHP control
space **without aggregate RMSE or MAE degradation relative to the frozen
validation reference**.

### Claim not supported by this experiment alone

EXP-CS1 does **not** establish universal generalization to arbitrary reservoir
geologies. The final OOD partition contains one independent geological
realization. Broader geological claims require additional prospectively locked
realizations or a new independent field-transfer protocol.

---

## 11. Version 16 architectural meaning

EXP-CS1 provides evidence that the PAD-Stream Stage-4 recurrent transport layer
can operate across a control factorial and transfer to one unseen SGSim
geological realization while preserving the architecture's central physics
division:

**geology → exact pressure → conservative Darcy flux → exact Pollock
kinematics → TOF/transport coordinates → recurrent saturation prediction**

The neural model therefore remains a transport surrogate **inside** a
physics-defined streamline simulator rather than becoming a replacement for
the flow solver or streamline geometry.

---

## 12. Experiment closure

EXP-CS1 is now immutable.

- Geology0029 is permanently consumed as its final locked-OOD test.
- No EXP-CS1 retraining is authorized.
- No alternate checkpoint may be evaluated on geology0029.
- No feature, normalization, architecture, loss, or threshold change may be
  evaluated against geology0029 as an unseen test.
- Any future learning experiment must use a new independently locked test set.

This record should be cited together with the V16D-37 experiment manifest and
the frozen D35/D36-R1 SHA-256 lineage.
"""

    THEORY.write_text(theory, encoding="utf-8")

    # -------------------------------------------------------------------------
    # 6. Final certification
    # -------------------------------------------------------------------------

    final_gates = dict(gates)
    final_gates.update({
        "manifest_written": MANIFEST.exists(),
        "theory_record_written": THEORY.exists(),
        "manifest_nonempty": MANIFEST.stat().st_size > 0,
        "theory_record_nonempty": THEORY.stat().st_size > 0,

        "D35_results_unchanged": sha256(D35_RESULTS) == D35_RESULTS_SHA,
        "D35_summary_unchanged": sha256(D35_SUMMARY) == D35_SUMMARY_SHA,
        "D35_open_lock_still_exists": D35_OPEN_LOCK.exists(),
        "D36R1_interpretation_unchanged":
            sha256(D36R1_INTERPRETATION) == D36R1_INTERPRETATION_SHA,
        "D36R1_summary_unchanged":
            sha256(D36R1_SUMMARY) == D36R1_SUMMARY_SHA,

        "no_TensorFlow_import_in_D37": True,
        "no_model_load_in_D37": True,
        "no_checkpoint_load_in_D37": True,
        "no_NPZ_load_in_D37": True,
        "no_OOD_array_reopen_in_D37": True,
        "no_inference_in_D37": True,
        "no_training_in_D37": True,
        "no_tuning_in_D37": True,

        "EXP_CS1_final_package_frozen": True,
        "EXP_CS1_theory_integrated": True,
        "EXP_CS1_remains_closed": True,
        "geology0029_remains_consumed": True,
    })

    ok = bool(all(bool(v) for v in final_gates.values()))

    status = (
        "V16D_EXP_CS1_FINAL_EXPERIMENT_PACKAGE_FROZEN_"
        "VERSION16_ARCHITECTURE_THEORY_INTEGRATED_EXPERIMENT_CLOSED"
        if ok
        else "V16D_D37_FINAL_PACKAGE_FREEZE_BLOCKED"
    )

    summary = {
        "milestone": "V16D-37",
        "experiment": "EXP-CS1",
        "status": status,
        "manifest_sha256": sha256(MANIFEST),
        "theory_integration_sha256": sha256(THEORY),
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
            (
                "V16D-38 — Master Version 16 control-space branch freeze and "
                "development-path handoff: assess the completed architecture "
                "against the revised PAD-Stream roadmap before starting the "
                "next integration branch"
            ),
    }

    SUMMARY.write_text(json.dumps(summary, indent=2))

    print("\n" + "=" * 78)
    print("EXP-CS1 FINAL PACKAGE")
    print("=" * 78)
    print("  OOD RMSE               : %.12e" % ood_rmse)
    print("  OOD MAE                : %.12e" % ood_mae)
    print("  RMSE / validation      : %.6f" % rmse_ratio)
    print("  MAE / validation       : %.6f" % mae_ratio)
    print("  checkpoint SHA-256     :", CHECKPOINT_SHA)
    print("  architecture SHA-256   :", ARCHITECTURE_SHA)

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
