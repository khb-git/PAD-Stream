#!/usr/bin/env python3
"""
PAD-Stream V16D-34
EXP-CS1 Final One-Touch LOCKED-OOD Evaluator Binding Contract Freeze

CONTRACT ONLY — NO OOD ARRAY LOAD / NO MODEL INFERENCE.

This milestone closes every remaining precondition in the preregistered V16D-31D
one-touch final evaluation protocol.

It binds, by exact SHA-256:
  * D32 learning-dataset registry,
  * D32 C20 9-channel feature contract,
  * D32 TRAIN-only normalization statistics,
  * D33 executable training protocol,
  * D33-R1-R2 repaired/certified training summary,
  * selected EXP-CS1 architecture,
  * selected EXP-CS1 checkpoint,
  * frozen validation diagnostics/metrics,
  * the exact future V16D-35 evaluator source,
  * all 9 geology0029 normalized-X artifact hashes,
  * all 9 geology0029 Stage-4 Y artifact hashes.

It also freezes the exact operational semantics of the preregistered prediction
physics diagnostics before OOD results exist.

V16D-34 does NOT:
  * import TensorFlow,
  * load a model,
  * load any X/Y NPZ,
  * run inference,
  * compute OOD statistics,
  * create OOD_OPENED.lock,
  * open the final OOD evaluation.
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
    / "V16_D34_EXP_CS1_FINAL_ONE_TOUCH_OOD_EVALUATOR_BINDING_CONTRACT"
)
OUT.mkdir(parents=True, exist_ok=True)

CONTRACT = (
    OUT
    / "V16D34_EXP_CS1_Final_OneTouch_OOD_Evaluator_Binding_Contract.json"
)
SUMMARY = OUT / "PAD_Stream_V16D34_Summary.json"


# =============================================================================
# D31D PREREGISTERED FINAL-EVALUATION AUTHORITY
# =============================================================================

D31D_DIR = (
    R
    / "output"
    / "V16_D31D_FROZEN_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION_CONTRACT"
)
D31D_CONTRACT = D31D_DIR / "V16D31D_OneTouch_Final_Locked_OOD_Evaluation_Contract.json"
D31D_SUMMARY = D31D_DIR / "PAD_Stream_V16D31D_Summary.json"

D31D_CONTRACT_SHA = (
    "7c664db19c041d3a611cbbc94de03a501a70f38922c62fd044cde1016d03228d"
)
D31D_SUMMARY_SHA = (
    "a98000f0456f2307fb2f5a6921b1975bdf462dfde43af5fa65de9e5474c676d3"
)


# =============================================================================
# D32 DATASET / FEATURE / NORMALIZATION AUTHORITIES
# =============================================================================

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

D32_REGISTRY_SHA = (
    "9429b239626fbfc8fe8569a2214a79a7abd5e40fbc38ac9112ba236e547fb90d"
)
D32_FEATURE_SHA = (
    "6f3301a57281ab2b5d44ffe044758c4707a9a489b2ceaff13867b5f55285b23a"
)
D32_NORMALIZATION_SHA = (
    "dcda1cf01fa30bd1cd947a500de73295037d6ca2b492725edd050c0ff7c3bfd9"
)
D32_PREDICTOR_MANIFEST_SHA = (
    "70171305a74d512903b5ae75386a86d3110d5f90d9aee99640e858660610d8ee"
)
D32_SUMMARY_SHA = (
    "ede1f7b506e1ed3256e5392664d9ff38d83850b5e1cbcf4a8d2b4c2295971801"
)


# =============================================================================
# D33 TRAINING PROTOCOL AUTHORITY
# =============================================================================

D33_DIR = (
    R
    / "output"
    / "V16_D33_CONTROLSPACE_RECURRENT_STAGE4_EXECUTABLE_TRAINING_PROTOCOL_FREEZE"
)

D33_PROTOCOL = D33_DIR / "V16D33_EXP_CS1_ControlSpace_Executable_Training_Protocol_1.0.json"
D33_SUMMARY = D33_DIR / "PAD_Stream_V16D33_Summary.json"

D33_PROTOCOL_SHA = (
    "e12219bdfe85fdbc2de30e348df609ff9bc91a652500a65f053dc6b64b4f9f4a"
)
D33_SUMMARY_SHA = (
    "b347b5aa8e3583ce4f35201840e47bf4cfb2e65d4589f0cbe981cad897dd760b"
)


# =============================================================================
# CERTIFIED EXISTING D33-R1-R2 TRAINING RESULT
# =============================================================================

D33R1_DIR = (
    R
    / "output"
    / "V16_D33_R1_EXP_CS1_CONTROLSPACE_RECURRENT_STAGE4_TRAINING_RUN"
)

D33R1R2_SUMMARY = D33R1_DIR / "PAD_Stream_V16D33_R1_R2_Summary.json"
D33R1R2_REPAIR = D33R1_DIR / "V16D33R1R2_PostTraining_Serialization_Repair_Report.json"

D33R1R2_SUMMARY_SHA = (
    "c16208c88b3dcc8083987f56c594eb42994b8ba3b91d88aeb1f44d2e2bacfb02"
)
D33R1R2_REPAIR_SHA = (
    "fe0748743112a78e2b8f0c6bcb4fa368e2b5aee915ded37d8d5e64db0f374eeb"
)

EXPECTED_CHECKPOINT_SHA = (
    "dc586da13e9fd7ce0b51cc661ba73edc8ab0f897d2f961112944504b13d1ed13"
)
EXPECTED_ARCHITECTURE_SHA = (
    "4304519d7c41b231f300535cef5daacd2525e395413addc883e66e7310096920"
)

EXPECTED_BEST_EPOCH = 73
EXPECTED_VALIDATION_MSE = 1.898255084950e-05
EXPECTED_VALIDATION_RMSE = 4.356896928951e-03
EXPECTED_VALIDATION_MAE = 1.755229556989e-03


# =============================================================================
# FUTURE EVALUATOR SOURCE TO FREEZE NOW
# =============================================================================

D35_SOURCE = R / "PAD_Stream_V16D35_EXP_CS1_OneTouch_Final_LOCKED_OOD_Evaluation.py"
D35_SOURCE_SHA = "80aeb3db5dcb58651df3b2b4f7d987849d6fde7ee1441f6953bca5f0e7699b6d"

D35_OUT = (
    R
    / "output"
    / "V16_D35_EXP_CS1_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION"
)
D35_OPEN_LOCK = D35_OUT / "OOD_OPENED.lock"


# =============================================================================
# FIXED OOD IDENTITY
# =============================================================================

RATES = [350, 500, 650]
BHPS = [1800, 2000, 2200]
TARGET_DAYS = [30, 60, 100, 150, 250, 365, 500, 750, 1000]

EXPECTED_CASE_IDS = [
    f"V16D_Foundation_Case_0029_R{rate}_B{bhp}"
    for rate in RATES
    for bhp in BHPS
]

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


def resolve_path(value: str) -> Path:
    p = Path(value)
    if not p.is_absolute():
        p = R / p
    return p


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16D-34")
    print("EXP-CS1 Final One-Touch LOCKED-OOD Evaluator Binding Contract Freeze")
    print("=" * 78)

    print(
        "\nCONTRACT ONLY — no TensorFlow import, no model load, no NPZ load, "
        "no OOD statistics, no OOD_OPENED.lock.\n"
    )

    if CONTRACT.exists() or SUMMARY.exists():
        raise RuntimeError(
            "D34 contract/summary already exists. Refusing to overwrite a frozen "
            "final-evaluation binding."
        )

    # -------------------------------------------------------------------------
    # 1. Exact authority SHA gates
    # -------------------------------------------------------------------------

    gates = {
        "D31D_contract_SHA_exact":
            exact_sha(D31D_CONTRACT, D31D_CONTRACT_SHA),
        "D31D_summary_SHA_exact":
            exact_sha(D31D_SUMMARY, D31D_SUMMARY_SHA),

        "D32_registry_SHA_exact":
            exact_sha(D32_REGISTRY, D32_REGISTRY_SHA),
        "D32_feature_contract_SHA_exact":
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
        "D33R1R2_repair_report_SHA_exact":
            exact_sha(D33R1R2_REPAIR, D33R1R2_REPAIR_SHA),

        "D35_future_evaluator_source_SHA_exact":
            exact_sha(D35_SOURCE, D35_SOURCE_SHA),

        "D35_OOD_OPENED_lock_absent":
            not D35_OPEN_LOCK.exists(),
    }

    print("AUTHORITY GATES")
    for name, passed in gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    if not all(gates.values()):
        raise RuntimeError("D34 blocked: exact frozen-authority gate failed.")

    # -------------------------------------------------------------------------
    # 2. Semantic authority checks
    # -------------------------------------------------------------------------

    d31d = read_json(D31D_CONTRACT)
    d31d_summary = read_json(D31D_SUMMARY)
    registry = read_json(D32_REGISTRY)
    feature = read_json(D32_FEATURE)
    stats = read_json(D32_NORMALIZATION)
    train_summary = read_json(D33R1R2_SUMMARY)

    gates.update({
        "D31D_one_touch_frozen":
            d31d_summary.get("one_touch_protocol_frozen") is True,
        "D31D_OOD_not_opened":
            d31d_summary.get("OOD_opened") is False,
        "D31D_OOD_not_evaluated":
            d31d_summary.get("OOD_evaluated") is False,

        "D32_generalization_unit_complete_case":
            registry.get("generalization_unit") == "COMPLETE_FOUNDATION_CASE",
        "D32_exact_18_9_9":
            registry.get("split_counts") == {
                "TRAIN": 18,
                "VALIDATION": 9,
                "LOCKED_OOD_TEST": 9,
            },
        "D32_feature_order_exact":
            feature.get("feature_order") == FEATURES,
        "D32_predictor_shape_exact":
            feature.get("shape_per_case") == [9, 1078, 201, 9],
        "D32_normalization_TRAIN_only":
            stats.get("fit_partition") == "TRAIN_ONLY",

        "training_status_certified":
            train_summary.get("status")
            == "V16D_EXP_CS1_CONTROLSPACE_RECURRENT_STAGE4_EXISTING_TRAINING_RUN_"
               "CERTIFIED_POSTSERIALIZATION_REPAIR_BEST_VALIDATION_CHECKPOINT_"
               "FROZEN_OOD_REMAINS_SEALED_FINAL_ONE_TOUCH_EVALUATOR_BINDING_"
               "CONTRACT_AUTHORIZED",
        "training_rerun_false":
            train_summary.get("training_rerun") is False,
        "best_epoch_exact_73":
            train_summary.get("best_epoch") == EXPECTED_BEST_EPOCH,
        "checkpoint_SHA_exact":
            train_summary.get("selected_model", {}).get("checkpoint_sha256")
            == EXPECTED_CHECKPOINT_SHA,
        "architecture_SHA_exact":
            train_summary.get("selected_model", {}).get("architecture_sha256")
            == EXPECTED_ARCHITECTURE_SHA,
        "training_OOD_not_evaluated":
            train_summary.get("LOCKED_OOD", {}).get("evaluated") is False,
    })

    frozen_val = train_summary.get("frozen_validation_metrics", {})

    gates.update({
        "frozen_validation_MSE_exact":
            math.isclose(
                float(frozen_val.get("MSE", math.nan)),
                EXPECTED_VALIDATION_MSE,
                rel_tol=0.0,
                abs_tol=5e-16,
            ),
        "frozen_validation_RMSE_exact":
            math.isclose(
                float(frozen_val.get("RMSE", math.nan)),
                EXPECTED_VALIDATION_RMSE,
                rel_tol=0.0,
                abs_tol=5e-15,
            ),
        "frozen_validation_MAE_exact":
            math.isclose(
                float(frozen_val.get("MAE", math.nan)),
                EXPECTED_VALIDATION_MAE,
                rel_tol=0.0,
                abs_tol=5e-15,
            ),
    })

    # Exact selected artifact files from certified R2 summary.
    architecture_path = resolve_path(
        train_summary["selected_model"]["architecture_path"]
    )
    checkpoint_path = resolve_path(
        train_summary["selected_model"]["checkpoint_path"]
    )
    validation_diag_path = resolve_path(
        frozen_val["diagnostics_path"]
    )

    gates.update({
        "selected_architecture_file_SHA_exact":
            exact_sha(architecture_path, EXPECTED_ARCHITECTURE_SHA),
        "selected_checkpoint_file_SHA_exact":
            exact_sha(checkpoint_path, EXPECTED_CHECKPOINT_SHA),
        "validation_diagnostics_SHA_matches_certified_summary":
            exact_sha(
                validation_diag_path,
                frozen_val["diagnostics_sha256"],
            ),
    })

    if not all(gates.values()):
        print("\nSEMANTIC GATES")
        for name, passed in gates.items():
            print("[PASS]" if passed else "[FAIL]", name)
        raise RuntimeError("D34 blocked: selected-model/validation semantic gate failed.")

    # -------------------------------------------------------------------------
    # 3. Bind exact OOD X/Y inventory with raw-byte SHA only — no np.load
    # -------------------------------------------------------------------------

    ood_entries = [
        x for x in registry.get("cases", [])
        if x.get("partition") == "LOCKED_OOD_TEST"
    ]

    by_id = {x["case_id"]: x for x in ood_entries}

    d31d_y_inventory = {
        x["case_id"]: x
        for x in d31d.get("sealed_OOD_artifact_inventory", [])
    }

    inventory = []

    print("\nLOCKED-OOD RAW-BYTE HASH PREFLIGHT")
    print("  Hashing files does not open X/Y arrays.")

    for i, cid in enumerate(EXPECTED_CASE_IDS, 1):
        if cid not in by_id:
            raise RuntimeError(f"D32 OOD registry missing {cid}")
        if cid not in d31d_y_inventory:
            raise RuntimeError(f"D31D sealed target inventory missing {cid}")

        e = by_id[cid]
        d31_rec = d31d_y_inventory[cid]

        xp = resolve_path(e["X_normalized"]["path"])
        yp = resolve_path(e["Y_stage4"]["path"])

        if not xp.exists() or not yp.exists():
            raise RuntimeError(f"{cid} X/Y artifact missing")

        x_sha = sha256(xp)
        y_sha = sha256(yp)

        if x_sha != e["X_normalized"]["sha256"]:
            raise RuntimeError(f"{cid} normalized-X SHA mismatch")

        if y_sha != e["Y_stage4"]["sha256"]:
            raise RuntimeError(f"{cid} D32 target SHA mismatch")

        if y_sha != d31_rec["artifact_sha256"]:
            raise RuntimeError(
                f"{cid} target SHA mismatch between D32 and D31D authorities"
            )

        if e["X_normalized"]["shape"] != [9, 1078, 201, 9]:
            raise RuntimeError(f"{cid} X shape authority mismatch")

        if e["Y_stage4"]["shape_authority"] != [9, 1078, 201]:
            raise RuntimeError(f"{cid} Y shape authority mismatch")

        inventory.append({
            "case_id": cid,
            "geology": "0029",
            "injection_rate_tpd": int(e["injection_rate_tpd"]),
            "producer_bhp_psi": int(e["producer_bhp_psi"]),
            "X_normalized_path": str(xp.relative_to(R)),
            "X_normalized_sha256": x_sha,
            "X_shape": [9, 1078, 201, 9],
            "Y_stage4_path": str(yp.relative_to(R)),
            "Y_stage4_sha256": y_sha,
            "Y_shape": [9, 1078, 201],
            "hash_verified_without_np_load": True,
        })

        print(f"[{i:02d}/09] {cid} X/Y SHA PASS")

    gates.update({
        "exact_9_OOD_inventory_cases": len(inventory) == 9,
        "OOD_case_order_exact": [x["case_id"] for x in inventory] == EXPECTED_CASE_IDS,
        "all_OOD_X_SHA_verified_without_np_load": True,
        "all_OOD_Y_SHA_verified_without_np_load": True,
        "no_OOD_X_np_load_in_D34": True,
        "no_OOD_Y_np_load_in_D34": True,
    })

    # -------------------------------------------------------------------------
    # 4. Freeze implementation semantics of preregistered diagnostics
    # -------------------------------------------------------------------------

    metric_semantics = {
        "primary_aggregate": {
            "MSE": "mean((prediction-target)^2) over all 9x9x1078x201 values",
            "RMSE": "sqrt(primary aggregate MSE)",
            "MAE": "mean(abs(prediction-target)) over all 9x9x1078x201 values",
            "accumulation_dtype": "float64",
        },
        "secondary_aggregate": [
            "mean_signed_error",
            "max_abs_error",
            "prediction_min",
            "prediction_max",
        ],
        "case_level": [
            "MSE",
            "RMSE",
            "MAE",
            "mean_signed_error",
            "max_abs_error",
            "prediction_min",
            "prediction_max",
        ],
        "time_resolved": {
            "times_days": TARGET_DAYS,
            "metrics": ["MSE", "RMSE", "MAE", "max_abs_error"],
            "aggregation":
                "all 9 OOD control cases x 1078 streamlines x 201 nodes at each time",
        },
        "control_resolved": {
            "by_injection_rate_tpd": RATES,
            "by_producer_bhp_psi": BHPS,
            "metrics": ["RMSE", "MAE"],
            "no_control_weighting_or_exclusion": True,
        },
        "physics_diagnostics": {
            "Swc": 0.2,
            "one_minus_Sor": 0.8,
            "fraction_below_Swc":
                "count(prediction < 0.2) / all prediction values",
            "fraction_above_one_minus_Sor":
                "count(prediction > 0.8) / all prediction values",
            "maximum_lower_bound_violation":
                "max(0, 0.2 - global_prediction_min)",
            "maximum_upper_bound_violation":
                "max(0, global_prediction_max - 0.8)",
            "injector_node": {
                "node_index": 0,
                "frozen_injection_boundary_Sw": 0.8,
                "metric":
                    "mean absolute(prediction[:,:,node0] - 0.8) over all cases/times/streamlines",
            },
            "temporal_negative_fraction": {
                "difference_axis": "target-time axis within each case",
                "threshold": -1e-8,
                "metric":
                    "count(diff_time(prediction) < -1e-8) / all adjacent-time prediction differences",
            },
            "spatial_positive_fraction": {
                "difference_axis": "Pollock-node axis within each case/time/streamline",
                "threshold": +1e-8,
                "metric":
                    "count(diff_node(prediction) > +1e-8) / all adjacent-node prediction differences",
            },
        },
        "validation_generalization_gap": {
            "RMSE_ratio": "OOD_RMSE / frozen_validation_RMSE",
            "MAE_ratio": "OOD_MAE / frozen_validation_MAE",
            "frozen_validation_RMSE": float(frozen_val["RMSE"]),
            "frozen_validation_MAE": float(frozen_val["MAE"]),
        },
        "claim_policy": {
            "no_OOD_derived_pass_fail_threshold": True,
            "report_even_if_poor": True,
            "no_result_suppression": True,
        },
    }

    # -------------------------------------------------------------------------
    # 5. Freeze final D35 evaluator + complete D31D future binding
    # -------------------------------------------------------------------------

    status = (
        "V16D_EXP_CS1_FINAL_ONE_TOUCH_OOD_EVALUATOR_BINDING_FROZEN_"
        "OOD_REMAINS_SEALED_FINAL_EVALUATION_EXECUTION_AUTHORIZED"
    )

    binding = {
        "milestone": "V16D-34",
        "contract_id":
            "V16D_EXP_CS1_FINAL_ONE_TOUCH_OOD_EVALUATOR_BINDING_1.0",
        "status": status,

        "scientific_role":
            "Complete the previously preregistered D31D future-required binding "
            "after validation-only model/checkpoint selection and before any "
            "locked-OOD array is opened.",

        "frozen_authorities": {
            "D31D_contract": {
                "path": str(D31D_CONTRACT.relative_to(R)),
                "sha256": D31D_CONTRACT_SHA,
            },
            "D31D_summary": {
                "path": str(D31D_SUMMARY.relative_to(R)),
                "sha256": D31D_SUMMARY_SHA,
            },
            "D32_dataset_registry": {
                "path": str(D32_REGISTRY.relative_to(R)),
                "sha256": D32_REGISTRY_SHA,
            },
            "D32_feature_contract": {
                "path": str(D32_FEATURE.relative_to(R)),
                "sha256": D32_FEATURE_SHA,
            },
            "D32_normalization": {
                "path": str(D32_NORMALIZATION.relative_to(R)),
                "sha256": D32_NORMALIZATION_SHA,
            },
            "D32_predictor_manifest": {
                "path": str(D32_PREDICTOR_MANIFEST.relative_to(R)),
                "sha256": D32_PREDICTOR_MANIFEST_SHA,
            },
            "D33_training_protocol": {
                "path": str(D33_PROTOCOL.relative_to(R)),
                "sha256": D33_PROTOCOL_SHA,
            },
            "D33R1R2_certified_training_summary": {
                "path": str(D33R1R2_SUMMARY.relative_to(R)),
                "sha256": D33R1R2_SUMMARY_SHA,
            },
            "D33R1R2_serialization_repair_report": {
                "path": str(D33R1R2_REPAIR.relative_to(R)),
                "sha256": D33R1R2_REPAIR_SHA,
            },
            "validation_diagnostics": {
                "path": str(validation_diag_path.relative_to(R)),
                "sha256": frozen_val["diagnostics_sha256"],
            },
        },

        "selected_model": {
            "experiment": "EXP-CS1",
            "seed": 161501,
            "architecture":
                "LSTM64 -> LSTM64 -> TD Dense sigmoid -> Rescaling[0.2,0.8]",
            "architecture_path": str(architecture_path.relative_to(R)),
            "architecture_sha256": EXPECTED_ARCHITECTURE_SHA,
            "checkpoint_path": str(checkpoint_path.relative_to(R)),
            "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA,
            "selection_partition": "VALIDATION",
            "selection_authority": "minimum raw VALIDATION MSE",
            "best_epoch": EXPECTED_BEST_EPOCH,
            "single_model_only": True,
            "single_checkpoint_only": True,
        },

        "predictor_interface": {
            "feature_order": FEATURES,
            "shape_per_case": [9, 1078, 201, 9],
            "normalization_fit": "TRAIN_ONLY",
            "validation_normalization": "TRANSFORM_ONLY",
            "locked_OOD_normalization": "TRANSFORM_ONLY",
            "Pollock": "AUTHORITATIVE_KINEMATICS",
            "ADV": "AUXILIARY",
            "FMM": "NOT_PREDICTOR",
            "M_face": "PHYSICS_SIDECAR_NOT_PREDICTOR",
            "direct_rate_channel": False,
            "direct_BHP_channel": False,
        },

        "frozen_validation_metrics": {
            "MSE": float(frozen_val["MSE"]),
            "RMSE": float(frozen_val["RMSE"]),
            "MAE": float(frozen_val["MAE"]),
            "mean_signed_error": float(frozen_val["mean_signed_error"]),
            "prediction_min": float(frozen_val["prediction_min"]),
            "prediction_max": float(frozen_val["prediction_max"]),
            "values_evaluated": int(frozen_val["values_evaluated"]),
            "diagnostics_sha256": frozen_val["diagnostics_sha256"],
        },

        "locked_OOD_inventory": {
            "partition": "LOCKED_OOD_TEST",
            "geology": "0029",
            "rates_tpd": RATES,
            "producer_bhp_psi": BHPS,
            "target_days": TARGET_DAYS,
            "count": 9,
            "cases": inventory,
            "arrays_opened_in_D34": False,
            "statistics_computed_in_D34": False,
        },

        "metric_semantics": metric_semantics,

        "final_evaluator_source": {
            "path": str(D35_SOURCE.relative_to(R)),
            "sha256": D35_SOURCE_SHA,
            "prediction_batch_size": 64,
            "source_frozen_before_OOD_opening": True,
            "executed_in_D34": False,
        },

        "one_touch_execution": {
            "future_milestone": "V16D-35",
            "future_output_directory":
                str(D35_OUT.relative_to(R)),
            "opening_marker":
                str(D35_OPEN_LOCK.relative_to(R)),
            "opening_marker_must_be_absent_at_D34": True,
            "opening_rule":
                "V16D-35 atomically creates OOD_OPENED.lock immediately before "
                "the first locked-OOD array load/evaluation.",
            "rerun_after_open": "PROHIBITED",
            "failure_after_open_consumes_evaluation": True,
            "output_directory_new_empty_before_open": True,
            "exactly_one_checkpoint": EXPECTED_CHECKPOINT_SHA,
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
            "new_learning_requires_new_independent_locked_test": True,
        },

        "execution_in_D34": {
            "TensorFlow_import": False,
            "model_load": False,
            "model_inference": False,
            "OOD_X_np_load": False,
            "OOD_Y_np_load": False,
            "OOD_statistics": False,
            "OOD_OPENED_lock_created": False,
            "contract_freeze_only": True,
        },
    }

    CONTRACT.write_text(json.dumps(binding, indent=2))

    # -------------------------------------------------------------------------
    # 6. Final gates
    # -------------------------------------------------------------------------

    final_gates = dict(gates)
    final_gates.update({
        "all_D31D_future_required_bindings_now_frozen": True,
        "single_model_only": True,
        "single_checkpoint_only": True,
        "architecture_SHA_frozen": True,
        "checkpoint_SHA_frozen": True,
        "dataset_registry_SHA_frozen": True,
        "feature_contract_SHA_frozen": True,
        "TRAIN_only_normalization_SHA_frozen": True,
        "validation_selection_summary_SHA_frozen": True,
        "validation_metrics_frozen": True,
        "final_evaluator_source_SHA_frozen": True,
        "exact_9_OOD_X_hashes_frozen": True,
        "exact_9_OOD_Y_hashes_frozen": True,
        "OOD_OPENED_lock_still_absent": not D35_OPEN_LOCK.exists(),
        "no_model_training_in_D34": True,
        "no_model_inference_in_D34": True,
        "no_OOD_array_open_in_D34": True,
        "no_OOD_metrics_in_D34": True,
        "no_OOD_tuning": True,
        "no_threshold_tuning": True,
        "poor_OOD_result_reporting_required": True,
        "contract_only": True,
    })

    ok = bool(all(bool(v) for v in final_gates.values()))

    if not ok:
        raise RuntimeError("D34 final binding gate failed; OOD remains sealed.")

    summary = {
        "milestone": "V16D-34",
        "experiment": "EXP-CS1",
        "status": status,
        "contract_sha256": sha256(CONTRACT),
        "selected_checkpoint_sha256": EXPECTED_CHECKPOINT_SHA,
        "selected_architecture_sha256": EXPECTED_ARCHITECTURE_SHA,
        "frozen_validation_MSE": float(frozen_val["MSE"]),
        "frozen_validation_RMSE": float(frozen_val["RMSE"]),
        "frozen_validation_MAE": float(frozen_val["MAE"]),
        "final_evaluator_source_sha256": D35_SOURCE_SHA,
        "locked_OOD_geology": "0029",
        "locked_OOD_cases": 9,
        "OOD_opened": False,
        "OOD_evaluated": False,
        "OOD_OPENED_lock_exists": D35_OPEN_LOCK.exists(),
        "gates": {k: bool(v) for k, v in final_gates.items()},
        "next_milestone":
            "V16D-35 — Execute the exact frozen EXP-CS1 one-touch final "
            "LOCKED-OOD evaluation on geology0029",
    }

    SUMMARY.write_text(json.dumps(summary, indent=2))

    print("\nFROZEN MODEL")
    print("  best epoch          :", EXPECTED_BEST_EPOCH)
    print("  validation MSE      : %.12e" % float(frozen_val["MSE"]))
    print("  validation RMSE     : %.12e" % float(frozen_val["RMSE"]))
    print("  validation MAE      : %.12e" % float(frozen_val["MAE"]))
    print("  checkpoint SHA-256  :", EXPECTED_CHECKPOINT_SHA)
    print("  architecture SHA-256:", EXPECTED_ARCHITECTURE_SHA)

    print("\nFROZEN FINAL EVALUATOR")
    print("  source:", D35_SOURCE.name)
    print("  SHA-256:", D35_SOURCE_SHA)

    print("\nFINAL GATES")
    for name, passed in final_gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    print("\nSTATUS")
    print(" ", status)

    print("\nLOCKED-OOD STATUS")
    print(
        "  SEALED — all 9 X/Y files were raw-byte hash verified, "
        "but no OOD array was opened or evaluated."
    )

    print("\nNEXT")
    print(
        "  V16D-35 — Execute the exact frozen EXP-CS1 one-touch final "
        "LOCKED-OOD evaluation on geology0029"
    )

    print("\nContract SHA-256:", sha256(CONTRACT))
    print("Summary SHA-256 :", sha256(SUMMARY))


if __name__ == "__main__":
    main()
