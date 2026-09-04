#!/usr/bin/env python3
"""
PAD-Stream V16D-36
EXP-CS1 Post-OOD Scientific Interpretation + Experiment Closure

Purpose
-------
Interpret the already-consumed V16D-35 geology0029 final OOD evaluation without
reopening any predictor/target arrays and without performing any additional
model inference.

This milestone:
  * verifies exact SHA-256 identity of the frozen D35 result artifacts,
  * reads only D35 JSON outputs,
  * summarizes aggregate, case, time, rate, BHP, and physics diagnostics,
  * reports descriptive generalization behavior,
  * explicitly forbids tuning/retraining under EXP-CS1,
  * freezes an experiment-closure interpretation package.

This milestone does NOT:
  * import TensorFlow,
  * load a checkpoint,
  * load any NPZ,
  * run inference,
  * recompute OOD predictions,
  * change thresholds,
  * perform model selection,
  * retrain EXP-CS1.
"""

from pathlib import Path
import csv
import hashlib
import json
import math
import statistics
import sys


# =============================================================================
# ROOT / FROZEN D35 AUTHORITIES
# =============================================================================

R = Path(__file__).resolve().parent

D35_DIR = (
    R
    / "output"
    / "V16_D35_EXP_CS1_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION"
)

D35_RESULTS = D35_DIR / "V16D35_EXP_CS1_Final_Locked_OOD_Results.json"
D35_SUMMARY = D35_DIR / "PAD_Stream_V16D35_Summary.json"
D35_OPEN_LOCK = D35_DIR / "OOD_OPENED.lock"

D35_RESULTS_SHA = (
    "ecc8f4d7f54dc1603072b17d763113f3963f3aae8afd0d6e1f9d2af847d9388e"
)
D35_SUMMARY_SHA = (
    "2cbbd396bdbdffd27a199ffec3db99d5bf6837f2eb4a1a3c63c5addf2eba117b"
)

EXPECTED_D35_STATUS = (
    "V16D_EXP_CS1_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION_COMPLETED_"
    "OOD_CONSUMED_NO_FURTHER_TUNING_AUTHORIZED"
)

EXPECTED_CHECKPOINT_SHA = (
    "dc586da13e9fd7ce0b51cc661ba73edc8ab0f897d2f961112944504b13d1ed13"
)
EXPECTED_ARCHITECTURE_SHA = (
    "4304519d7c41b231f300535cef5daacd2525e395413addc883e66e7310096920"
)
EXPECTED_EVALUATOR_SHA = (
    "80aeb3db5dcb58651df3b2b4f7d987849d6fde7ee1441f6953bca5f0e7699b6d"
)


# =============================================================================
# OUTPUT
# =============================================================================

OUT = (
    R
    / "output"
    / "V16_D36_EXP_CS1_POST_OOD_SCIENTIFIC_INTERPRETATION_AND_CLOSURE"
)
OUT.mkdir(parents=True, exist_ok=True)

CASE_CSV = OUT / "V16D36_Case_Level_OOD_Metrics.csv"
TIME_CSV = OUT / "V16D36_Time_Resolved_OOD_Metrics.csv"
RATE_CSV = OUT / "V16D36_Rate_Resolved_OOD_Metrics.csv"
BHP_CSV = OUT / "V16D36_BHP_Resolved_OOD_Metrics.csv"
INTERPRETATION = OUT / "V16D36_EXP_CS1_Post_OOD_Interpretation.json"
SUMMARY = OUT / "PAD_Stream_V16D36_Summary.json"


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


def finite(x):
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def write_csv(path: Path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def pct_change(new, old):
    return 100.0 * (float(new) / float(old) - 1.0)


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16D-36")
    print("EXP-CS1 Post-OOD Scientific Interpretation + Experiment Closure")
    print("=" * 78)

    print(
        "\nREAD-ONLY POST-OOD INTERPRETATION.\n"
        "No model load. No NPZ load. No inference. No retraining. No tuning.\n"
    )

    if any(p.exists() for p in [INTERPRETATION, SUMMARY]):
        raise RuntimeError(
            "D36 interpretation/summary already exists. Refusing to overwrite "
            "a frozen post-OOD interpretation package."
        )

    # -------------------------------------------------------------------------
    # 1. Exact D35 provenance gates
    # -------------------------------------------------------------------------

    gates = {
        "D35_results_SHA_exact":
            exact_sha(D35_RESULTS, D35_RESULTS_SHA),
        "D35_summary_SHA_exact":
            exact_sha(D35_SUMMARY, D35_SUMMARY_SHA),
        "D35_open_lock_exists":
            D35_OPEN_LOCK.exists() and D35_OPEN_LOCK.is_file(),
    }

    print("PROVENANCE GATES")
    for name, passed in gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    if not all(gates.values()):
        raise RuntimeError("D36 blocked: frozen D35 provenance mismatch.")

    results = read_json(D35_RESULTS)
    summary = read_json(D35_SUMMARY)
    open_lock = read_json(D35_OPEN_LOCK)

    gates.update({
        "D35_status_exact":
            summary.get("status") == EXPECTED_D35_STATUS,
        "D35_OOD_opened":
            summary.get("OOD_opened") is True,
        "D35_OOD_evaluated":
            summary.get("OOD_evaluated") is True,
        "D35_OOD_consumed":
            summary.get("OOD_consumed") is True,
        "D35_cases_evaluated_9":
            summary.get("cases_evaluated") == 9,
        "D35_results_role_final_locked_OOD":
            results.get("evaluation_role") == "ONE_TOUCH_FINAL_LOCKED_OOD_TEST",
        "D35_geology0029":
            results.get("LOCKED_OOD", {}).get("geology") == "0029",
        "D35_partition_locked_OOD":
            results.get("LOCKED_OOD", {}).get("partition") == "LOCKED_OOD_TEST",
        "D35_checkpoint_SHA_exact":
            results.get("selected_model", {}).get("checkpoint_sha256")
            == EXPECTED_CHECKPOINT_SHA,
        "D35_architecture_SHA_exact":
            results.get("selected_model", {}).get("architecture_sha256")
            == EXPECTED_ARCHITECTURE_SHA,
        "D35_evaluator_SHA_exact":
            results.get("selected_model", {}).get("evaluator_source_sha256")
            == EXPECTED_EVALUATOR_SHA,
        "D35_lock_checkpoint_SHA_exact":
            open_lock.get("checkpoint_sha256") == EXPECTED_CHECKPOINT_SHA,
        "D35_lock_evaluator_SHA_exact":
            open_lock.get("evaluator_source_sha256") == EXPECTED_EVALUATOR_SHA,
    })

    if not all(gates.values()):
        print("\nSEMANTIC GATES")
        for name, passed in gates.items():
            print("[PASS]" if passed else "[FAIL]", name)
        raise RuntimeError("D36 blocked: D35 semantic authority mismatch.")

    # -------------------------------------------------------------------------
    # 2. Aggregate metrics + validation generalization gap
    # -------------------------------------------------------------------------

    agg = results["aggregate"]
    gaps = results["validation_generalization_gap"]

    required_agg = [
        "MSE", "RMSE", "MAE", "mean_signed_error",
        "max_abs_error", "prediction_min", "prediction_max", "values",
    ]

    gates["aggregate_required_metrics_present"] = all(k in agg for k in required_agg)
    gates["aggregate_metrics_finite"] = all(
        finite(agg[k]) for k in required_agg if k != "values"
    )
    gates["aggregate_values_exact"] = int(agg["values"]) == 9 * 9 * 1078 * 201

    val_rmse = float(gaps["frozen_validation_RMSE"])
    val_mae = float(gaps["frozen_validation_MAE"])
    ood_rmse = float(agg["RMSE"])
    ood_mae = float(agg["MAE"])

    rmse_ratio = float(gaps["OOD_RMSE_over_frozen_validation_RMSE"])
    mae_ratio = float(gaps["OOD_MAE_over_frozen_validation_MAE"])

    gates["RMSE_gap_ratio_consistent"] = math.isclose(
        rmse_ratio,
        ood_rmse / val_rmse,
        rel_tol=1e-12,
        abs_tol=1e-15,
    )
    gates["MAE_gap_ratio_consistent"] = math.isclose(
        mae_ratio,
        ood_mae / val_mae,
        rel_tol=1e-12,
        abs_tol=1e-15,
    )

    # Descriptive only. These are not acceptance thresholds.
    validation_comparison = {
        "OOD_RMSE": ood_rmse,
        "frozen_validation_RMSE": val_rmse,
        "OOD_RMSE_over_validation_RMSE": rmse_ratio,
        "OOD_RMSE_percent_difference_from_validation":
            pct_change(ood_rmse, val_rmse),
        "OOD_MAE": ood_mae,
        "frozen_validation_MAE": val_mae,
        "OOD_MAE_over_validation_MAE": mae_ratio,
        "OOD_MAE_percent_difference_from_validation":
            pct_change(ood_mae, val_mae),
        "interpretation":
            (
                "The final unseen-geology aggregate error is compared only "
                "descriptively with the already-frozen validation reference. "
                "No threshold or model decision is made from this comparison."
            ),
    }

    # -------------------------------------------------------------------------
    # 3. Case-level interpretation
    # -------------------------------------------------------------------------

    case_rows = results["case_level"]

    if len(case_rows) != 9:
        raise RuntimeError("Expected exactly 9 case-level D35 results.")

    case_required = [
        "case_id",
        "injection_rate_tpd",
        "producer_bhp_psi",
        "MSE",
        "RMSE",
        "MAE",
        "mean_signed_error",
        "max_abs_error",
        "prediction_min",
        "prediction_max",
        "values",
    ]

    for row in case_rows:
        if not all(k in row for k in case_required):
            raise RuntimeError(
                f"Case-level metric fields missing for {row.get('case_id')}"
            )

    sorted_rmse = sorted(case_rows, key=lambda r: float(r["RMSE"]))
    sorted_mae = sorted(case_rows, key=lambda r: float(r["MAE"]))

    case_interpretation = {
        "lowest_RMSE_case": {
            "case_id": sorted_rmse[0]["case_id"],
            "RMSE": float(sorted_rmse[0]["RMSE"]),
            "MAE": float(sorted_rmse[0]["MAE"]),
        },
        "highest_RMSE_case": {
            "case_id": sorted_rmse[-1]["case_id"],
            "RMSE": float(sorted_rmse[-1]["RMSE"]),
            "MAE": float(sorted_rmse[-1]["MAE"]),
        },
        "lowest_MAE_case": {
            "case_id": sorted_mae[0]["case_id"],
            "RMSE": float(sorted_mae[0]["RMSE"]),
            "MAE": float(sorted_mae[0]["MAE"]),
        },
        "highest_MAE_case": {
            "case_id": sorted_mae[-1]["case_id"],
            "RMSE": float(sorted_mae[-1]["RMSE"]),
            "MAE": float(sorted_mae[-1]["MAE"]),
        },
        "RMSE_range": {
            "min": float(sorted_rmse[0]["RMSE"]),
            "max": float(sorted_rmse[-1]["RMSE"]),
            "max_over_min": (
                float(sorted_rmse[-1]["RMSE"])
                / float(sorted_rmse[0]["RMSE"])
            ),
        },
    }

    write_csv(
        CASE_CSV,
        case_rows,
        case_required,
    )

    # -------------------------------------------------------------------------
    # 4. Time-resolved interpretation
    # -------------------------------------------------------------------------

    time_rows = results["time_resolved"]

    if len(time_rows) != 9:
        raise RuntimeError("Expected exactly 9 time-resolved D35 rows.")

    time_required = [
        "time_days", "MSE", "RMSE", "MAE", "max_abs_error", "values"
    ]

    for row in time_rows:
        if not all(k in row for k in time_required):
            raise RuntimeError("Time-resolved metric fields missing.")

    time_sorted = sorted(time_rows, key=lambda r: int(r["time_days"]))
    expected_days = [30, 60, 100, 150, 250, 365, 500, 750, 1000]

    gates["time_days_exact"] = (
        [int(r["time_days"]) for r in time_sorted] == expected_days
    )

    worst_time_rmse = max(time_rows, key=lambda r: float(r["RMSE"]))
    best_time_rmse = min(time_rows, key=lambda r: float(r["RMSE"]))

    time_interpretation = {
        "lowest_RMSE_time_days": int(best_time_rmse["time_days"]),
        "lowest_RMSE": float(best_time_rmse["RMSE"]),
        "highest_RMSE_time_days": int(worst_time_rmse["time_days"]),
        "highest_RMSE": float(worst_time_rmse["RMSE"]),
        "early_mid_late_descriptive": {
            "early_days": [30, 60, 100],
            "mid_days": [150, 250, 365],
            "late_days": [500, 750, 1000],
        },
        "note":
            (
                "Time-resolved behavior is reported descriptively from the "
                "frozen D35 metrics. It is not used to alter the model."
            ),
    }

    write_csv(
        TIME_CSV,
        time_sorted,
        time_required,
    )

    # -------------------------------------------------------------------------
    # 5. Control-space interpretation
    # -------------------------------------------------------------------------

    control = results["control_resolved"]
    by_rate = control["by_injection_rate_tpd"]
    by_bhp = control["by_producer_bhp_psi"]

    rate_rows = []
    for rate in [350, 500, 650]:
        rec = by_rate[str(rate)]
        rate_rows.append({
            "injection_rate_tpd": rate,
            "RMSE": float(rec["RMSE"]),
            "MAE": float(rec["MAE"]),
            "values": int(rec["values"]),
        })

    bhp_rows = []
    for bhp in [1800, 2000, 2200]:
        rec = by_bhp[str(bhp)]
        bhp_rows.append({
            "producer_bhp_psi": bhp,
            "RMSE": float(rec["RMSE"]),
            "MAE": float(rec["MAE"]),
            "values": int(rec["values"]),
        })

    write_csv(
        RATE_CSV,
        rate_rows,
        ["injection_rate_tpd", "RMSE", "MAE", "values"],
    )

    write_csv(
        BHP_CSV,
        bhp_rows,
        ["producer_bhp_psi", "RMSE", "MAE", "values"],
    )

    rate_rmse = [r["RMSE"] for r in rate_rows]
    rate_mae = [r["MAE"] for r in rate_rows]
    bhp_rmse = [r["RMSE"] for r in bhp_rows]
    bhp_mae = [r["MAE"] for r in bhp_rows]

    control_interpretation = {
        "injection_rate": {
            "rows": rate_rows,
            "RMSE_monotonic_decrease_with_rate":
                rate_rmse[0] > rate_rmse[1] > rate_rmse[2],
            "MAE_monotonic_decrease_with_rate":
                rate_mae[0] > rate_mae[1] > rate_mae[2],
            "RMSE_percent_change_350_to_650":
                pct_change(rate_rmse[-1], rate_rmse[0]),
            "MAE_percent_change_350_to_650":
                pct_change(rate_mae[-1], rate_mae[0]),
        },
        "producer_BHP": {
            "rows": bhp_rows,
            "RMSE_monotonic_decrease_with_BHP":
                bhp_rmse[0] > bhp_rmse[1] > bhp_rmse[2],
            "MAE_monotonic_decrease_with_BHP":
                bhp_mae[0] > bhp_mae[1] > bhp_mae[2],
            "RMSE_percent_change_1800_to_2200":
                pct_change(bhp_rmse[-1], bhp_rmse[0]),
            "MAE_percent_change_1800_to_2200":
                pct_change(bhp_mae[-1], bhp_mae[0]),
        },
        "scientific_caution":
            (
                "These control-space trends are post-OOD descriptive findings. "
                "They must not be used to modify EXP-CS1 or to re-evaluate "
                "geology0029."
            ),
    }

    # -------------------------------------------------------------------------
    # 6. Physics-diagnostic interpretation
    # -------------------------------------------------------------------------

    physics = results["prediction_physics_diagnostics"]

    physics_required = [
        "Swc",
        "one_minus_Sor",
        "fraction_predictions_below_Swc",
        "fraction_predictions_above_one_minus_Sor",
        "maximum_lower_bound_violation",
        "maximum_upper_bound_violation",
        "injector_node_boundary_Sw",
        "injector_node_mean_absolute_error",
        "temporal_negative_threshold",
        "temporal_negative_fraction",
        "spatial_positive_threshold",
        "spatial_positive_fraction",
        "prediction_values",
        "temporal_differences",
        "spatial_differences",
    ]

    gates["physics_required_fields_present"] = all(
        k in physics for k in physics_required
    )
    gates["physics_diagnostics_finite"] = all(
        finite(physics[k])
        for k in physics_required
        if k not in {"prediction_values", "temporal_differences", "spatial_differences"}
    )

    physics_interpretation = {
        "saturation_bounds": {
            "Swc": float(physics["Swc"]),
            "one_minus_Sor": float(physics["one_minus_Sor"]),
            "fraction_below_Swc":
                float(physics["fraction_predictions_below_Swc"]),
            "fraction_above_one_minus_Sor":
                float(physics["fraction_predictions_above_one_minus_Sor"]),
            "maximum_lower_bound_violation":
                float(physics["maximum_lower_bound_violation"]),
            "maximum_upper_bound_violation":
                float(physics["maximum_upper_bound_violation"]),
        },
        "injector_boundary": {
            "frozen_boundary_Sw":
                float(physics["injector_node_boundary_Sw"]),
            "mean_absolute_error":
                float(physics["injector_node_mean_absolute_error"]),
        },
        "temporal_monotonicity": {
            "threshold":
                float(physics["temporal_negative_threshold"]),
            "negative_fraction":
                float(physics["temporal_negative_fraction"]),
            "differences_evaluated":
                int(physics["temporal_differences"]),
        },
        "streamline_spatial_monotonicity": {
            "threshold":
                float(physics["spatial_positive_threshold"]),
            "positive_fraction":
                float(physics["spatial_positive_fraction"]),
            "differences_evaluated":
                int(physics["spatial_differences"]),
        },
        "note":
            (
                "Physics diagnostics are interpreted exactly as preregistered. "
                "No new post-OOD acceptance threshold is invented."
            ),
    }

    # -------------------------------------------------------------------------
    # 7. Freeze scientific interpretation and experiment closure
    # -------------------------------------------------------------------------

    all_case_rmse = [float(r["RMSE"]) for r in case_rows]
    all_case_mae = [float(r["MAE"]) for r in case_rows]

    interpretation = {
        "milestone": "V16D-36",
        "experiment": "EXP-CS1",
        "scientific_role":
            "Post-OOD interpretation of the already-consumed final geology0029 "
            "test evaluation using only frozen D35 JSON result artifacts.",

        "frozen_D35_authorities": {
            "results_path": str(D35_RESULTS.relative_to(R)),
            "results_sha256": D35_RESULTS_SHA,
            "summary_path": str(D35_SUMMARY.relative_to(R)),
            "summary_sha256": D35_SUMMARY_SHA,
            "opening_lock_path": str(D35_OPEN_LOCK.relative_to(R)),
            "opening_lock_sha256": sha256(D35_OPEN_LOCK),
        },

        "aggregate_OOD": {
            "MSE": float(agg["MSE"]),
            "RMSE": ood_rmse,
            "MAE": ood_mae,
            "mean_signed_error": float(agg["mean_signed_error"]),
            "max_abs_error": float(agg["max_abs_error"]),
            "prediction_min": float(agg["prediction_min"]),
            "prediction_max": float(agg["prediction_max"]),
            "values": int(agg["values"]),
        },

        "validation_comparison": validation_comparison,

        "case_level_interpretation": case_interpretation,
        "case_level_descriptive_statistics": {
            "RMSE_mean_of_case_metrics": statistics.fmean(all_case_rmse),
            "RMSE_median_of_case_metrics": statistics.median(all_case_rmse),
            "MAE_mean_of_case_metrics": statistics.fmean(all_case_mae),
            "MAE_median_of_case_metrics": statistics.median(all_case_mae),
        },

        "time_resolved_interpretation": time_interpretation,
        "control_space_interpretation": control_interpretation,
        "physics_diagnostic_interpretation": physics_interpretation,

        "scientific_conclusions": [
            (
                "The final unseen geology0029 aggregate RMSE is "
                f"{abs(validation_comparison['OOD_RMSE_percent_difference_from_validation']):.3f}% "
                + (
                    "lower"
                    if validation_comparison["OOD_RMSE_percent_difference_from_validation"] < 0
                    else "higher"
                )
                + " than the frozen validation RMSE."
            ),
            (
                "The final unseen geology0029 aggregate MAE is "
                f"{abs(validation_comparison['OOD_MAE_percent_difference_from_validation']):.3f}% "
                + (
                    "lower"
                    if validation_comparison["OOD_MAE_percent_difference_from_validation"] < 0
                    else "higher"
                )
                + " than the frozen validation MAE."
            ),
            (
                "All nine predeclared rate/BHP cases are retained in the final "
                "result; no case, time, streamline, node, or control was excluded."
            ),
            (
                "Control-resolved behavior and time/physics diagnostics are "
                "descriptive post-OOD observations only and cannot be used to "
                "change EXP-CS1."
            ),
            (
                "EXP-CS1 is scientifically closed. Any new learning experiment "
                "requires a newly and independently locked test set."
            ),
        ],

        "experiment_closure": {
            "EXP_CS1_training_closed": True,
            "geology0029_consumed": True,
            "geology0029_may_not_be_reused_as_unseen_test": True,
            "same_experiment_retraining": "PROHIBITED",
            "same_experiment_checkpoint_change": "PROHIBITED",
            "same_experiment_architecture_change": "PROHIBITED",
            "same_experiment_feature_change": "PROHIBITED",
            "same_experiment_normalization_change": "PROHIBITED",
            "same_experiment_threshold_tuning": "PROHIBITED",
            "same_experiment_OOD_informed_selection": "PROHIBITED",
            "future_new_learning_experiment_requires_new_locked_test": True,
        },

        "execution_in_D36": {
            "TensorFlow_import": False,
            "checkpoint_loaded": False,
            "model_inference": False,
            "NPZ_loaded": False,
            "OOD_arrays_reopened": False,
            "predictions_recomputed": False,
            "training": False,
            "tuning": False,
            "read_only_D35_JSON_interpretation": True,
        },
    }

    INTERPRETATION.write_text(json.dumps(interpretation, indent=2))

    # -------------------------------------------------------------------------
    # 8. Final gates / summary
    # -------------------------------------------------------------------------

    final_gates = dict(gates)
    final_gates.update({
        "D35_result_not_modified": sha256(D35_RESULTS) == D35_RESULTS_SHA,
        "D35_summary_not_modified": sha256(D35_SUMMARY) == D35_SUMMARY_SHA,
        "D35_open_lock_still_exists": D35_OPEN_LOCK.exists(),
        "no_model_load_in_D36": True,
        "no_inference_in_D36": True,
        "no_NPZ_load_in_D36": True,
        "no_OOD_array_reopen_in_D36": True,
        "no_retraining_in_D36": True,
        "no_tuning_in_D36": True,
        "no_new_OOD_threshold": True,
        "all_9_cases_retained": len(case_rows) == 9,
        "all_9_times_retained": len(time_rows) == 9,
        "EXP_CS1_closed": True,
    })

    ok = bool(all(bool(v) for v in final_gates.values()))

    status = (
        "V16D_EXP_CS1_POST_OOD_SCIENTIFIC_INTERPRETATION_COMPLETE_"
        "EXPERIMENT_CLOSED_NO_FURTHER_TUNING_AUTHORIZED"
        if ok
        else "V16D_D36_POST_OOD_INTERPRETATION_BLOCKED"
    )

    summary_out = {
        "milestone": "V16D-36",
        "experiment": "EXP-CS1",
        "status": status,
        "D35_results_sha256": D35_RESULTS_SHA,
        "D35_summary_sha256": D35_SUMMARY_SHA,
        "OOD_RMSE": ood_rmse,
        "OOD_MAE": ood_mae,
        "validation_RMSE": val_rmse,
        "validation_MAE": val_mae,
        "RMSE_gap_ratio": rmse_ratio,
        "MAE_gap_ratio": mae_ratio,
        "RMSE_percent_difference_from_validation":
            validation_comparison["OOD_RMSE_percent_difference_from_validation"],
        "MAE_percent_difference_from_validation":
            validation_comparison["OOD_MAE_percent_difference_from_validation"],
        "lowest_RMSE_case": case_interpretation["lowest_RMSE_case"],
        "highest_RMSE_case": case_interpretation["highest_RMSE_case"],
        "geology0029_consumed": True,
        "EXP_CS1_closed": True,
        "interpretation_sha256": sha256(INTERPRETATION),
        "case_csv_sha256": sha256(CASE_CSV),
        "time_csv_sha256": sha256(TIME_CSV),
        "rate_csv_sha256": sha256(RATE_CSV),
        "bhp_csv_sha256": sha256(BHP_CSV),
        "gates": {k: bool(v) for k, v in final_gates.items()},
        "next_milestone":
            (
                "V16D-37 — Freeze the completed EXP-CS1 control-space experiment "
                "package and integrate its conclusions into the PAD-Stream "
                "Version 16 architecture/theory record"
            ),
    }

    SUMMARY.write_text(json.dumps(summary_out, indent=2))

    print("\n" + "=" * 78)
    print("POST-OOD SCIENTIFIC INTERPRETATION")
    print("=" * 78)

    print("  OOD RMSE                : %.12e" % ood_rmse)
    print("  Validation RMSE         : %.12e" % val_rmse)
    print(
        "  RMSE difference         : %+.6f %%"
        % validation_comparison["OOD_RMSE_percent_difference_from_validation"]
    )

    print("  OOD MAE                 : %.12e" % ood_mae)
    print("  Validation MAE          : %.12e" % val_mae)
    print(
        "  MAE difference          : %+.6f %%"
        % validation_comparison["OOD_MAE_percent_difference_from_validation"]
    )

    print(
        "  Lowest-RMSE OOD case    :",
        case_interpretation["lowest_RMSE_case"]["case_id"],
        "%.12e" % case_interpretation["lowest_RMSE_case"]["RMSE"],
    )
    print(
        "  Highest-RMSE OOD case   :",
        case_interpretation["highest_RMSE_case"]["case_id"],
        "%.12e" % case_interpretation["highest_RMSE_case"]["RMSE"],
    )

    print("\nCONTROL-SPACE DESCRIPTIVE FINDINGS")
    for row in rate_rows:
        print(
            "  Rate %3d t/day: RMSE=%.12e MAE=%.12e"
            % (row["injection_rate_tpd"], row["RMSE"], row["MAE"])
        )
    for row in bhp_rows:
        print(
            "  BHP %4d psi : RMSE=%.12e MAE=%.12e"
            % (row["producer_bhp_psi"], row["RMSE"], row["MAE"])
        )

    print("\nFINAL GATES")
    for name, passed in final_gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    print("\nSTATUS")
    print(" ", status)

    print("\nEXPERIMENT CLOSURE")
    print("  EXP-CS1       : CLOSED")
    print("  geology0029   : CONSUMED AS FINAL OOD TEST")
    print("  further tuning: PROHIBITED")
    print("  new learning  : requires a new independently locked test set")

    print("\nNEXT")
    print(
        "  V16D-37 — Freeze the completed EXP-CS1 control-space experiment "
        "package and integrate its conclusions into the PAD-Stream "
        "Version 16 architecture/theory record"
    )

    print("\nInterpretation SHA-256:", sha256(INTERPRETATION))
    print("Summary SHA-256       :", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
