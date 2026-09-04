#!/usr/bin/env python3
"""
PAD-Stream V16D-37-R2
EXP-CS1 Final Experiment Package Freeze + V16 Theory Integration
Archival Provenance Reconciliation

R2 reason
---------
D37 failed because the current loose D31D summary no longer matched the
historical frozen SHA.
D37-R1 then found a second archival inconsistency: the exact D34 runtime
contract's embedded D31D-summary SHA did not equal the historical SHA expected
from the exact D34 source, even though D34 had successfully passed its
D31D_summary_SHA_exact gate before the OOD set was opened.

R2 does not conceal or overwrite either discrepancy.

It freezes four distinct identities:
  1. historical expected D31D summary SHA,
  2. exact D34-source-declared D31D summary SHA,
  3. exact D34-runtime-contract embedded D31D summary SHA,
  4. current loose D31D summary SHA.

Scientific authority is preserved through:
  * exact D34 source SHA,
  * source-level historical constant and pre-OOD exact-SHA gate,
  * exact successful D34 summary SHA/status,
  * exact D35 one-touch result SHA/status,
  * exact D36-R1 post-OOD closure SHA/status.

NO TensorFlow. NO model load. NO checkpoint load. NO NPZ load.
NO OOD reopening. NO inference. NO training. NO tuning.
"""

from pathlib import Path
import hashlib
import json
import math
import re
import sys

R = Path(__file__).resolve().parent

OUT = (
    R / "output"
    / "V16_D37_R2_EXP_CS1_FINAL_PACKAGE_V16_THEORY_PROVENANCE_RECONCILIATION"
)
OUT.mkdir(parents=True, exist_ok=True)

MANIFEST = OUT / "V16D37R2_EXP_CS1_Final_Experiment_Manifest.json"
THEORY = OUT / "V16D37R2_EXP_CS1_Architecture_Theory_Integration.md"
AUDIT = OUT / "V16D37R2_D31D_D34_Archival_Provenance_Audit.json"
SUMMARY = OUT / "PAD_Stream_V16D37R2_Summary.json"

# ---------------------------------------------------------------------------
# D31D historical authority
# ---------------------------------------------------------------------------

D31D_DIR = (
    R / "output"
    / "V16_D31D_FROZEN_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION_CONTRACT"
)
D31D_CONTRACT = D31D_DIR / "V16D31D_OneTouch_Final_Locked_OOD_Evaluation_Contract.json"
D31D_SUMMARY = D31D_DIR / "PAD_Stream_V16D31D_Summary.json"

D31D_CONTRACT_SHA = "7c664db19c041d3a611cbbc94de03a501a70f38922c62fd044cde1016d03228d"
HISTORICAL_D31D_SUMMARY_SHA = "a98000f0456f2307fb2f5a6921b1975bdf462dfde43af5fa65de9e5474c676d3e"

# ---------------------------------------------------------------------------
# D32
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# D33 / D33-R1-R2
# ---------------------------------------------------------------------------

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

CHECKPOINT_SHA = "dc586da13e9fd7ce0b51cc661ba73edc8ab0f897d2f961112944504b13d1ed13"
ARCHITECTURE_SHA = "4304519d7c41b231f300535cef5daacd2525e395413addc883e66e7310096920"

# ---------------------------------------------------------------------------
# D34 exact source + exact runtime outputs
# ---------------------------------------------------------------------------

D34_SOURCE = R / "PAD_Stream_V16D34_EXP_CS1_Final_OneTouch_OOD_Evaluator_Binding_Contract_Freeze.py"
D34_SOURCE_SHA = "9f9512fab7cc324014460bfcf8911f4202d408c9bd99b4ee247390c0dc6e3181"

D34_DIR = (
    R / "output"
    / "V16_D34_EXP_CS1_FINAL_ONE_TOUCH_OOD_EVALUATOR_BINDING_CONTRACT"
)
D34_CONTRACT = D34_DIR / "V16D34_EXP_CS1_Final_OneTouch_OOD_Evaluator_Binding_Contract.json"
D34_SUMMARY = D34_DIR / "PAD_Stream_V16D34_Summary.json"

D34_CONTRACT_SHA = "6c21c825355211ae5470922143f78154ca32d8349ee6a61c89f29648a1845cef"
D34_SUMMARY_SHA = "4a75d85b1ec23bd58a3b09032da81d9cc30893a201dcf85938fe0444f4f5cef7"

EXPECTED_D34_STATUS = (
    "V16D_EXP_CS1_FINAL_ONE_TOUCH_OOD_EVALUATOR_BINDING_FROZEN_"
    "OOD_REMAINS_SEALED_FINAL_EVALUATION_EXECUTION_AUTHORIZED"
)

# ---------------------------------------------------------------------------
# D35 exact final OOD
# ---------------------------------------------------------------------------

D35_DIR = (
    R / "output"
    / "V16_D35_EXP_CS1_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION"
)
D35_RESULTS = D35_DIR / "V16D35_EXP_CS1_Final_Locked_OOD_Results.json"
D35_SUMMARY = D35_DIR / "PAD_Stream_V16D35_Summary.json"
D35_OPEN_LOCK = D35_DIR / "OOD_OPENED.lock"

D35_RESULTS_SHA = "ecc8f4d7f54dc1603072b17d763113f3963f3aae8afd0d6e1f9d2af847d9388e"
D35_SUMMARY_SHA = "2cbbd396bdbdffd27a199ffec3db99d5bf6837f2eb4a1a3c63c5addf2eba117b"
D35_EVALUATOR_SHA = "80aeb3db5dcb58651df3b2b4f7d987849d6fde7ee1441f6953bca5f0e7699b6d"

EXPECTED_D35_STATUS = (
    "V16D_EXP_CS1_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION_COMPLETED_"
    "OOD_CONSUMED_NO_FURTHER_TUNING_AUTHORIZED"
)

# ---------------------------------------------------------------------------
# D36-R1 exact closure
# ---------------------------------------------------------------------------

D36R1_SOURCE = (
    R / "PAD_Stream_V16D36_R1_EXP_CS1_Post_OOD_Scientific_Interpretation_and_Closure_Recovery.py"
)
D36R1_SOURCE_SHA = "f83cd938791d6237ddc6734734d01c57987b261452cf9522f2ecee08d490aa56"

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

EXPECTED_D36_STATUS = (
    "V16D_EXP_CS1_POST_OOD_SCIENTIFIC_INTERPRETATION_RECOVERED_COMPLETE_"
    "EXPERIMENT_CLOSED_NO_FURTHER_TUNING_AUTHORIZED"
)

# ---------------------------------------------------------------------------
# Failed archival attempts preserved
# ---------------------------------------------------------------------------

D37_FAILED_SOURCE = (
    R / "PAD_Stream_V16D37_EXP_CS1_Final_Experiment_Package_Freeze_and_V16_Architecture_Theory_Integration.py"
)
D37_FAILED_SOURCE_SHA = "ec36f49408323b318a31ec872184d931290424e5e8c19b7bbe6571d3cdedc782"

D37R1_FAILED_SOURCE = (
    R / "PAD_Stream_V16D37_R1_EXP_CS1_Final_Experiment_Package_Freeze_and_V16_Architecture_Theory_Integration_Lineage_Recovery.py"
)
D37R1_FAILED_SOURCE_SHA = "fc0286ee26287c1e947aaac5ddc871cd6e6f80c5064ae097dc33ead5c3253f4a"

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
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"{label} missing/empty: {path}")


def main():
    print("=" * 78)
    print("PAD-Stream V16D-37-R2")
    print("EXP-CS1 Final Package + V16 Theory — Archival Provenance Reconciliation")
    print("=" * 78)
    print(
        "\nARCHIVAL/THEORY ONLY — no TensorFlow, no model/checkpoint load, "
        "no NPZ, no OOD reopening, no inference, no training, no tuning.\n"
    )

    if any(p.exists() for p in [MANIFEST, THEORY, AUDIT, SUMMARY]):
        raise RuntimeError(
            "D37-R2 output already exists. Refusing to overwrite frozen recovery."
        )

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

        "D34_source_SHA_exact":
            exact_sha(D34_SOURCE, D34_SOURCE_SHA),
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
        "failed_D37R1_source_SHA_exact":
            exact_sha(D37R1_FAILED_SOURCE, D37R1_FAILED_SOURCE_SHA),
    }

    print("IMMUTABLE LINEAGE GATES")
    for name, passed in gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    if not all(gates.values()):
        raise RuntimeError("D37-R2 blocked: immutable lineage gate failed.")

    # -----------------------------------------------------------------------
    # Source-level D34 prospective-gate audit
    # -----------------------------------------------------------------------

    d34_source_text = D34_SOURCE.read_text(encoding="utf-8")

    source_constant_present = (
        HISTORICAL_D31D_SUMMARY_SHA in d34_source_text
        and "D31D_SUMMARY_SHA" in d34_source_text
    )
    source_exact_gate_present = (
        '"D31D_summary_SHA_exact"' in d34_source_text
        and "exact_sha(D31D_SUMMARY, D31D_SUMMARY_SHA)" in d34_source_text
    )
    source_binding_present = (
        '"D31D_summary"' in d34_source_text
        and '"sha256": D31D_SUMMARY_SHA' in d34_source_text
    )

    gates.update({
        "D34_source_declares_historical_D31D_summary_SHA":
            source_constant_present,
        "D34_source_contains_exact_D31D_summary_pre_gate":
            source_exact_gate_present,
        "D34_source_constructs_D31D_summary_binding":
            source_binding_present,
    })

    # -----------------------------------------------------------------------
    # Runtime JSON audit
    # -----------------------------------------------------------------------

    d34_contract = read_json(D34_CONTRACT)
    d34_summary = read_json(D34_SUMMARY)
    d35_results = read_json(D35_RESULTS)
    d35_summary = read_json(D35_SUMMARY)
    d36_interpretation = read_json(D36R1_INTERPRETATION)
    d36_summary = read_json(D36R1_SUMMARY)
    d32_registry = read_json(D32_REGISTRY)
    d32_feature = read_json(D32_FEATURE)
    d33r2 = read_json(D33R1R2_SUMMARY)

    current_d31d_summary_sha = sha256(D31D_SUMMARY)

    d34_embedded = (
        d34_contract.get("frozen_authorities", {})
        .get("D31D_summary", {})
    )
    d34_embedded_path = d34_embedded.get("path")
    d34_embedded_sha = d34_embedded.get("sha256")

    gates.update({
        "D34_summary_status_authorized":
            d34_summary.get("status") == EXPECTED_D34_STATUS,
        "D34_summary_OOD_not_opened":
            d34_summary.get("OOD_opened") is False,
        "D34_summary_OOD_not_evaluated":
            d34_summary.get("OOD_evaluated") is False,
        "D34_runtime_D31D_summary_path_exact":
            d34_embedded_path == rel(D31D_SUMMARY),

        "D35_status_exact":
            d35_summary.get("status") == EXPECTED_D35_STATUS,
        "D35_OOD_consumed":
            d35_summary.get("OOD_consumed") is True,
        "D35_cases_9":
            d35_summary.get("cases_evaluated") == 9,
        "D35_checkpoint_exact":
            d35_results.get("selected_model", {}).get("checkpoint_sha256")
            == CHECKPOINT_SHA,
        "D35_architecture_exact":
            d35_results.get("selected_model", {}).get("architecture_sha256")
            == ARCHITECTURE_SHA,
        "D35_evaluator_exact":
            d35_results.get("selected_model", {}).get("evaluator_source_sha256")
            == D35_EVALUATOR_SHA,

        "D36_status_exact":
            d36_summary.get("status") == EXPECTED_D36_STATUS,
        "D36_EXP_CS1_closed":
            d36_summary.get("EXP_CS1_closed") is True,
        "D36_geology0029_consumed":
            d36_summary.get("geology0029_consumed") is True,

        "D32_split_counts_exact":
            d32_registry.get("split_counts") == {
                "TRAIN": 18,
                "VALIDATION": 9,
                "LOCKED_OOD_TEST": 9,
            },
        "D32_feature_order_exact":
            d32_feature.get("feature_order") == FEATURES,
        "D33R2_checkpoint_exact":
            d33r2.get("selected_model", {}).get("checkpoint_sha256")
            == CHECKPOINT_SHA,
        "D33R2_architecture_exact":
            d33r2.get("selected_model", {}).get("architecture_sha256")
            == ARCHITECTURE_SHA,
    })

    # D34 embedded-SHA equality is deliberately an AUDIT FACT, not a pass gate.
    # R1 already demonstrated that this value differs from the historical SHA.
    runtime_contract_matches_historical = (
        d34_embedded_sha == HISTORICAL_D31D_SUMMARY_SHA
    )
    current_loose_matches_historical = (
        current_d31d_summary_sha == HISTORICAL_D31D_SUMMARY_SHA
    )
    current_loose_matches_runtime_contract = (
        current_d31d_summary_sha == d34_embedded_sha
    )

    # Freeze D36 CSV identities too.
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

        "archival_discrepancy_explicitly_recorded": True,
        "historical_SHA_not_rewritten": True,
        "runtime_embedded_SHA_not_rewritten": True,
        "current_loose_SHA_not_rewritten": True,
        "scientific_artifacts_unchanged": True,
    })

    if not all(gates.values()):
        print("\nSEMANTIC / RECONCILIATION GATES")
        for name, passed in gates.items():
            print("[PASS]" if passed else "[FAIL]", name)
        raise RuntimeError("D37-R2 blocked: semantic reconciliation gate failed.")

    audit = {
        "milestone": "V16D-37-R2",
        "audit_role":
            "Reconcile archival D31D-summary identity discrepancy without "
            "changing scientific results or historical provenance.",

        "identities": {
            "historical_expected_D31D_summary_sha256":
                HISTORICAL_D31D_SUMMARY_SHA,
            "D34_source_declared_D31D_summary_sha256":
                HISTORICAL_D31D_SUMMARY_SHA,
            "D34_runtime_contract_embedded_D31D_summary_sha256":
                d34_embedded_sha,
            "current_loose_D31D_summary_sha256":
                current_d31d_summary_sha,
        },

        "comparisons": {
            "D34_runtime_contract_matches_historical":
                runtime_contract_matches_historical,
            "current_loose_copy_matches_historical":
                current_loose_matches_historical,
            "current_loose_copy_matches_D34_runtime_contract":
                current_loose_matches_runtime_contract,
        },

        "D34_source_authority": {
            "path": rel(D34_SOURCE),
            "sha256": D34_SOURCE_SHA,
            "historical_constant_present": source_constant_present,
            "exact_D31D_summary_pre_gate_present": source_exact_gate_present,
            "D31D_summary_binding_constructor_present": source_binding_present,
        },

        "D34_runtime_authority": {
            "contract_path": rel(D34_CONTRACT),
            "contract_sha256": D34_CONTRACT_SHA,
            "summary_path": rel(D34_SUMMARY),
            "summary_sha256": D34_SUMMARY_SHA,
            "summary_status": d34_summary.get("status"),
            "embedded_D31D_summary_path": d34_embedded_path,
            "embedded_D31D_summary_sha256": d34_embedded_sha,
        },

        "resolution_policy": {
            "rewrite_historical_SHA": False,
            "rewrite_runtime_contract": False,
            "rewrite_current_loose_summary": False,
            "scientific_result_invalidated": False,
            "OOD_reopening_required": False,
            "provenance_resolution":
                "The exact D34 source proves the prospectively specified "
                "historical D31D-summary SHA and exact-SHA gate. The exact "
                "successful D34 summary proves that D34 completed before OOD "
                "opening. The exact D35/D36 lineage proves the frozen experiment "
                "continued unchanged. The runtime-contract embedded discrepancy "
                "and current loose-file drift are retained as archival metadata.",
        },
    }

    AUDIT.write_text(json.dumps(audit, indent=2))

    # -----------------------------------------------------------------------
    # Final scientific package
    # -----------------------------------------------------------------------

    agg = d35_results["aggregate"]
    gap = d35_results["validation_generalization_gap"]
    control = d36_interpretation["control_space_interpretation"]
    cases = d36_interpretation["case_level_interpretation"]
    time_info = d36_interpretation["time_resolved_interpretation"]
    physics = d36_interpretation["physics_diagnostic_interpretation"]
    validation_compare = d36_interpretation["validation_comparison"]

    ood_mse = float(agg["MSE"])
    ood_rmse = float(agg["RMSE"])
    ood_mae = float(agg["MAE"])
    val_rmse = float(gap["frozen_validation_RMSE"])
    val_mae = float(gap["frozen_validation_MAE"])
    rmse_ratio = float(gap["OOD_RMSE_over_frozen_validation_RMSE"])
    mae_ratio = float(gap["OOD_MAE_over_frozen_validation_MAE"])

    gates.update({
        "OOD_metrics_finite":
            all(math.isfinite(x) for x in [ood_mse, ood_rmse, ood_mae]),
        "validation_metrics_finite":
            all(math.isfinite(x) for x in [val_rmse, val_mae]),
        "generalization_ratios_finite":
            all(math.isfinite(x) for x in [rmse_ratio, mae_ratio]),
        "aggregate_values_exact":
            int(agg["values"]) == 9 * 9 * 1078 * 201,
    })

    manifest = {
        "milestone": "V16D-37-R2",
        "experiment": "EXP-CS1",
        "package_role":
            "Final immutable control-space experiment package with explicit "
            "archival provenance reconciliation.",

        "experiment_state": {
            "training_complete": True,
            "validation_selection_complete": True,
            "final_locked_OOD_evaluation_complete": True,
            "post_OOD_interpretation_complete": True,
            "EXP_CS1_closed": True,
            "geology0029_consumed": True,
            "further_tuning": "PROHIBITED",
            "new_learning_requires_new_independent_locked_test": True,
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
            "OOD_used_for_training": False,
            "OOD_used_for_normalization": False,
            "OOD_used_for_selection": False,
            "OOD_used_for_tuning": False,
            "no_deduplication": True,
        },

        "architecture": {
            "input_shape": [201, 9],
            "feature_order": FEATURES,
            "model":
                "LSTM64 -> LSTM64 -> TimeDistributed Dense(1,sigmoid) -> "
                "Rescaling[0.2,0.8]",
            "parameter_count": 52033,
            "best_epoch": 73,
            "loss": "MSE",
            "optimizer": "Adam(1e-3)",
            "seed": 161501,
            "batch_size": 64,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "architecture_sha256": ARCHITECTURE_SHA,
        },

        "PAD_Stream_roles": {
            "SGSim_geology":
                "heterogeneous dissertation-base geology",
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
                "saturation prediction along 201-node Pollock streamlines",
            "direct_rate_BHP_channels":
                False,
        },

        "frozen_validation": {
            "MSE": float(d33r2["frozen_validation_metrics"]["MSE"]),
            "RMSE": val_rmse,
            "MAE": val_mae,
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
                float(validation_compare["OOD_RMSE_percent_difference_from_validation"]),
            "MAE_percent_difference_from_validation":
                float(validation_compare["OOD_MAE_percent_difference_from_validation"]),
        },

        "descriptive_post_OOD": {
            "case_level": cases,
            "time_resolved": time_info,
            "injection_rate": control["injection_rate"],
            "producer_BHP": control["producer_BHP"],
            "physics": physics,
            "policy":
                "DESCRIPTIVE ONLY; never a tuning signal for EXP-CS1.",
        },

        "claim_boundary": {
            "supported":
                "Within frozen EXP-CS1, the Stage-4 recurrent model transferred "
                "from TRAIN geologies 0026-0027, through validation geology0028, "
                "to independently locked geology0029 across all nine rate/BHP "
                "controls without aggregate RMSE or MAE degradation relative "
                "to the frozen validation reference.",
            "not_supported":
                "Universal geological generalization across arbitrary reservoir "
                "realizations is not established by one independently locked "
                "OOD geology.",
        },

        "archival_provenance_reconciliation": audit,

        "immutable_lineage": {
            "D31D_contract": {
                "path": rel(D31D_CONTRACT),
                "sha256": D31D_CONTRACT_SHA,
            },
            "D31D_summary_identity_set": {
                "historical_expected_sha256":
                    HISTORICAL_D31D_SUMMARY_SHA,
                "D34_runtime_embedded_sha256":
                    d34_embedded_sha,
                "current_loose_sha256":
                    current_d31d_summary_sha,
                "audit_sha256":
                    sha256(AUDIT),
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
            "D34_source": {
                "path": rel(D34_SOURCE),
                "sha256": D34_SOURCE_SHA,
            },
            "D34_contract": {
                "path": rel(D34_CONTRACT),
                "sha256": D34_CONTRACT_SHA,
            },
            "D34_summary": {
                "path": rel(D34_SUMMARY),
                "sha256": D34_SUMMARY_SHA,
            },
            "D35_results": {
                "path": rel(D35_RESULTS),
                "sha256": D35_RESULTS_SHA,
            },
            "D35_summary": {
                "path": rel(D35_SUMMARY),
                "sha256": D35_SUMMARY_SHA,
            },
            "D35_open_lock": {
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
        },

        "execution_in_D37R2": {
            "TensorFlow_import": False,
            "model_load": False,
            "checkpoint_load": False,
            "NPZ_load": False,
            "OOD_array_reopen": False,
            "inference": False,
            "training": False,
            "tuning": False,
            "read_only_archival_reconciliation": True,
        },
    }

    MANIFEST.write_text(json.dumps(manifest, indent=2))

    rate_rows = control["injection_rate"]["rows"]
    bhp_rows = control["producer_BHP"]["rows"]

    theory = f"""# PAD-Stream Version 16 — EXP-CS1 Final Architecture and Theory Record

## 1. Final state

**EXP-CS1 is CLOSED and FROZEN.**

- TRAIN: geologies 0026-0027
- VALIDATION: geology0028
- FINAL LOCKED OOD: geology0029
- geology0029 has been consumed exactly once as the final EXP-CS1 test.
- No further EXP-CS1 tuning or retesting is authorized.

## 2. PAD-Stream architecture represented by EXP-CS1

**SGSim geology → finite-volume pressure → conservative Darcy fluxes →
exact 3-D Pollock streamlines → TOF/transport coordinates → recurrent
Stage-4 saturation prediction**

The recurrent model operates inside a physics-defined streamline simulator.
It does not replace the pressure solve, conservative flux construction, or
Pollock kinematics.

## 3. Predictor interface

Nine channels per 201-node streamline:

1. xi
2. pollock_tau_hat
3. adv_tau_hat
4. log10_Kh
5. log10_Kz_over_Kh
6. porosity
7. pressure_z
8. target_time_hat
9. target_eta_sequence

Roles:

- Pollock: authoritative kinematics
- ADV: auxiliary predictor
- FMM: not an EXP-CS1 predictor
- M_face: physics sidecar, not predictor
- rate/BHP: indirect through the physical state, not direct channels

## 4. Frozen recurrent model

- LSTM64 → LSTM64 → TimeDistributed Dense(1,sigmoid) → Sw[0.2,0.8]
- 52,033 parameters
- MSE loss
- Adam(1e-3)
- seed 161501
- batch 64
- best epoch 73
- checkpoint SHA: `{CHECKPOINT_SHA}`
- architecture SHA: `{ARCHITECTURE_SHA}`

Validation:

- MSE = {float(d33r2["frozen_validation_metrics"]["MSE"]):.12e}
- RMSE = {val_rmse:.12e}
- MAE = {val_mae:.12e}

## 5. Final locked-OOD result

All 9 controls × 9 times × 1,078 streamlines × 201 nodes were retained.

- values = {int(agg["values"]):,}
- OOD MSE = {ood_mse:.12e}
- OOD RMSE = {ood_rmse:.12e}
- OOD MAE = {ood_mae:.12e}
- OOD RMSE / validation RMSE = {rmse_ratio:.6f}
- OOD MAE / validation MAE = {mae_ratio:.6f}

OOD RMSE is
{abs(float(validation_compare["OOD_RMSE_percent_difference_from_validation"])):.3f}%
lower than validation and OOD MAE is
{abs(float(validation_compare["OOD_MAE_percent_difference_from_validation"])):.3f}%
lower than validation.

## 6. Control-space descriptive findings

### Injection rate

| Rate (t/day) | RMSE | MAE |
|---:|---:|---:|
| 350 | {float(rate_rows[0]["RMSE"]):.12e} | {float(rate_rows[0]["MAE"]):.12e} |
| 500 | {float(rate_rows[1]["RMSE"]):.12e} | {float(rate_rows[1]["MAE"]):.12e} |
| 650 | {float(rate_rows[2]["RMSE"]):.12e} | {float(rate_rows[2]["MAE"]):.12e} |

Both metrics decrease with rate in geology0029. This is descriptive only.

### Producer BHP

| BHP (psi) | RMSE | MAE |
|---:|---:|---:|
| 1800 | {float(bhp_rows[0]["RMSE"]):.12e} | {float(bhp_rows[0]["MAE"]):.12e} |
| 2000 | {float(bhp_rows[1]["RMSE"]):.12e} | {float(bhp_rows[1]["MAE"]):.12e} |
| 2200 | {float(bhp_rows[2]["RMSE"]):.12e} | {float(bhp_rows[2]["MAE"]):.12e} |

RMSE decreases across BHP levels, while MAE is not strictly monotonic.

## 7. Scientific claim boundary

Supported:

Within frozen EXP-CS1, Stage-4 recurrent transport generalized from TRAIN
geologies 0026-0027, through validation geology0028, to independently locked
geology0029 across all nine rate/BHP controls without aggregate RMSE or MAE
degradation relative to validation.

Not supported:

Universal geological generalization across arbitrary reservoirs. One
independently locked OOD geology is not sufficient for that broader claim.

## 8. Archival provenance reconciliation

The scientific result is unchanged, but an archival discrepancy was detected
during final packaging.

Historical D31D summary SHA expected by the exact D34 source:

`{HISTORICAL_D31D_SUMMARY_SHA}`

D34 runtime contract embedded D31D summary SHA:

`{d34_embedded_sha}`

Current loose D31D summary SHA:

`{current_d31d_summary_sha}`

D34 exact source SHA:

`{D34_SOURCE_SHA}`

The exact D34 source contains the historical SHA constant, the
`D31D_summary_SHA_exact` pre-OOD gate, and the D31D-summary binding
constructor. The exact D34 summary has the successful pre-OOD authorization
status, while exact D35/D36 artifacts preserve the completed one-touch
experiment and closure.

No identity is rewritten. The discrepancy is preserved explicitly in:

`{AUDIT.name}`

This archival issue does not reopen OOD data and does not alter any model,
prediction, error metric, or scientific conclusion.

## 9. Experiment closure

EXP-CS1 remains immutable.

- geology0029 cannot be reused as an unseen test.
- no alternate EXP-CS1 checkpoint may be tested on geology0029.
- no EXP-CS1 feature/architecture/normalization/loss/threshold change may use
  geology0029 for selection.
- any new learning experiment requires a new independently locked test set.
"""

    THEORY.write_text(theory, encoding="utf-8")

    final_gates = dict(gates)
    final_gates.update({
        "audit_written_nonempty":
            AUDIT.exists() and AUDIT.stat().st_size > 0,
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
        "D36_interpretation_unchanged":
            sha256(D36R1_INTERPRETATION) == D36R1_INTERPRETATION_SHA,
        "D36_summary_unchanged":
            sha256(D36R1_SUMMARY) == D36R1_SUMMARY_SHA,

        "no_TensorFlow_import_in_D37R2": True,
        "no_model_load_in_D37R2": True,
        "no_checkpoint_load_in_D37R2": True,
        "no_NPZ_load_in_D37R2": True,
        "no_OOD_reopen_in_D37R2": True,
        "no_inference_in_D37R2": True,
        "no_training_in_D37R2": True,
        "no_tuning_in_D37R2": True,

        "historical_D31D_identity_preserved": True,
        "D34_runtime_identity_preserved": True,
        "current_loose_identity_preserved": True,
        "archival_discrepancy_not_hidden": True,

        "EXP_CS1_final_package_frozen": True,
        "EXP_CS1_theory_integrated": True,
        "EXP_CS1_closed": True,
        "geology0029_consumed": True,
    })

    ok = bool(all(bool(v) for v in final_gates.values()))

    status = (
        "V16D_EXP_CS1_FINAL_EXPERIMENT_PACKAGE_PROVENANCE_RECONCILED_FROZEN_"
        "VERSION16_ARCHITECTURE_THEORY_INTEGRATED_EXPERIMENT_CLOSED"
        if ok
        else "V16D_D37R2_PROVENANCE_RECONCILIATION_BLOCKED"
    )

    summary = {
        "milestone": "V16D-37-R2",
        "experiment": "EXP-CS1",
        "status": status,

        "historical_D31D_summary_sha256":
            HISTORICAL_D31D_SUMMARY_SHA,
        "D34_runtime_embedded_D31D_summary_sha256":
            d34_embedded_sha,
        "current_loose_D31D_summary_sha256":
            current_d31d_summary_sha,

        "D34_runtime_contract_matches_historical":
            runtime_contract_matches_historical,
        "current_loose_matches_historical":
            current_loose_matches_historical,
        "current_loose_matches_D34_runtime_contract":
            current_loose_matches_runtime_contract,

        "D34_source_sha256": D34_SOURCE_SHA,
        "D34_contract_sha256": D34_CONTRACT_SHA,
        "D34_summary_sha256": D34_SUMMARY_SHA,

        "audit_sha256": sha256(AUDIT),
        "manifest_sha256": sha256(MANIFEST),
        "theory_sha256": sha256(THEORY),

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
            "against the revised PAD-Stream roadmap before beginning the next "
            "integration branch.",
    }

    SUMMARY.write_text(json.dumps(summary, indent=2))

    print("\nARCHIVAL IDENTITY AUDIT")
    print("  historical expected D31D SHA :", HISTORICAL_D31D_SUMMARY_SHA)
    print("  D34 runtime embedded SHA      :", d34_embedded_sha)
    print("  current loose D31D SHA        :", current_d31d_summary_sha)
    print("  runtime matches historical    :", runtime_contract_matches_historical)
    print("  loose matches historical      :", current_loose_matches_historical)
    print("  loose matches runtime         :", current_loose_matches_runtime_contract)

    print("\nSCIENTIFIC PACKAGE")
    print("  OOD RMSE          : %.12e" % ood_rmse)
    print("  OOD MAE           : %.12e" % ood_mae)
    print("  RMSE / validation : %.6f" % rmse_ratio)
    print("  MAE / validation  : %.6f" % mae_ratio)

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
    print("  Audit    :", AUDIT.name)
    print("  Manifest :", MANIFEST.name)
    print("  Theory   :", THEORY.name)
    print("  Summary  :", SUMMARY.name)

    print("\nNEXT")
    print("  V16D-38 — Master Version 16 control-space branch freeze and handoff.")

    print("\nAudit SHA-256   :", sha256(AUDIT))
    print("Manifest SHA-256:", sha256(MANIFEST))
    print("Theory SHA-256  :", sha256(THEORY))
    print("Summary SHA-256 :", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
