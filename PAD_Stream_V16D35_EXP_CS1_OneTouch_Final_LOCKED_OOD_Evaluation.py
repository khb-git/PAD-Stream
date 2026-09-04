#!/usr/bin/env python3
"""
PAD-Stream V16D-35
EXP-CS1 One-Touch Final LOCKED-OOD Evaluation — EXECUTION

THIS SCRIPT CONSUMES THE FINAL LOCKED-OOD EVALUATION.

It may be executed only after V16D-34 has frozen:
  * D32 learning-dataset / feature / normalization authorities,
  * EXP-CS1 architecture SHA,
  * EXP-CS1 validation-selected checkpoint SHA,
  * validation-selection metrics,
  * this exact evaluator source SHA,
  * the 9 geology0029 normalized predictor + target artifact hashes.

One-touch rule
--------------
1. Refuse if OOD_OPENED.lock already exists.
2. Require a new/empty final-evaluation output directory.
3. Complete every hash/semantic preflight before opening any OOD array.
4. Build/load the one frozen EXP-CS1 model/checkpoint.
5. Atomically create OOD_OPENED.lock immediately before the first OOD array
   load/evaluation.
6. Evaluate all 9 frozen cases with no exclusions or adaptation.
7. Report the preregistered metrics even if results are poor.
8. Never retrain, tune, change checkpoint, or repeat this evaluation.
"""

from pathlib import Path
import hashlib
import json
import math
import os
import re
import sys
import time

import numpy as np


# =============================================================================
# ROOT / FROZEN D34 BINDING
# =============================================================================

R = Path(__file__).resolve().parent

D34_DIR = (
    R
    / "output"
    / "V16_D34_EXP_CS1_FINAL_ONE_TOUCH_OOD_EVALUATOR_BINDING_CONTRACT"
)

D34_CONTRACT = (
    D34_DIR
    / "V16D34_EXP_CS1_Final_OneTouch_OOD_Evaluator_Binding_Contract.json"
)
D34_SUMMARY = D34_DIR / "PAD_Stream_V16D34_Summary.json"


# =============================================================================
# FINAL ONE-TOUCH OUTPUT
# =============================================================================

OUT = (
    R
    / "output"
    / "V16_D35_EXP_CS1_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION"
)

OPEN_LOCK = OUT / "OOD_OPENED.lock"
RESULT_JSON = OUT / "V16D35_EXP_CS1_Final_Locked_OOD_Results.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16D35_Summary.json"


# =============================================================================
# FROZEN SHAPES / MODEL
# =============================================================================

N_TIMES = 9
N_STREAMLINES = 1078
N_NODES = 201
N_CHANNELS = 9

X_SHAPE = (9, 1078, 201, 9)
Y_SHAPE = (9, 1078, 201)

TARGET_DAYS = [30, 60, 100, 150, 250, 365, 500, 750, 1000]
RATES_TPD = [350, 500, 650]
BHP_PSI = [1800, 2000, 2200]

SWC = 0.2
ONE_MINUS_SOR = 0.8
INJECTION_BOUNDARY_SW = 0.8

TEMPORAL_NEGATIVE_THRESHOLD = -1.0e-8
SPATIAL_POSITIVE_THRESHOLD = +1.0e-8

PREDICTION_BATCH_SIZE = 64


# =============================================================================
# HELPERS
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def resolve_path(value: str) -> Path:
    p = Path(value)
    if not p.is_absolute():
        p = R / p
    return p


def require_file(path: Path, label: str):
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"{label} missing: {path}")
    if path.stat().st_size <= 0:
        raise RuntimeError(f"{label} empty: {path}")


def atomic_create_lock(path: Path, payload: dict):
    """
    Exclusive lock creation. If the file already exists, evaluation is consumed.
    """
    data = json.dumps(payload, indent=2).encode("utf-8")
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def blank_error_accum():
    return {
        "n": 0,
        "sum_sq": 0.0,
        "sum_abs": 0.0,
        "sum_signed": 0.0,
        "max_abs": 0.0,
        "pred_min": math.inf,
        "pred_max": -math.inf,
    }


def update_error_accum(acc, pred, truth):
    p = np.asarray(pred, dtype=np.float64)
    y = np.asarray(truth, dtype=np.float64)

    if p.shape != y.shape:
        raise RuntimeError(f"prediction/target shape mismatch: {p.shape} vs {y.shape}")

    if not np.isfinite(p).all() or not np.isfinite(y).all():
        raise RuntimeError("nonfinite prediction/target block")

    d = p - y
    ad = np.abs(d)

    acc["n"] += int(d.size)
    acc["sum_sq"] += float(np.square(d).sum(dtype=np.float64))
    acc["sum_abs"] += float(ad.sum(dtype=np.float64))
    acc["sum_signed"] += float(d.sum(dtype=np.float64))
    acc["max_abs"] = max(acc["max_abs"], float(ad.max()))
    acc["pred_min"] = min(acc["pred_min"], float(p.min()))
    acc["pred_max"] = max(acc["pred_max"], float(p.max()))


def finalize_error_accum(acc):
    n = int(acc["n"])
    if n <= 0:
        raise RuntimeError("cannot finalize zero-length error accumulator")
    mse = acc["sum_sq"] / n
    return {
        "values": n,
        "MSE": mse,
        "RMSE": math.sqrt(mse),
        "MAE": acc["sum_abs"] / n,
        "mean_signed_error": acc["sum_signed"] / n,
        "max_abs_error": acc["max_abs"],
        "prediction_min": acc["pred_min"],
        "prediction_max": acc["pred_max"],
    }


def load_x(path: Path):
    with np.load(path, allow_pickle=False) as z:
        if "X" not in z.files:
            raise RuntimeError(f"normalized predictor key X absent in {path}")
        a = np.asarray(z["X"])
    if a.shape != X_SHAPE:
        raise RuntimeError(f"X shape mismatch {a.shape} in {path}")
    a = np.asarray(a, dtype=np.float32)
    if not np.isfinite(a).all():
        raise RuntimeError(f"nonfinite X in {path}")
    return a


def load_y(path: Path):
    with np.load(path, allow_pickle=False) as z:
        if "Y_transport" not in z.files:
            raise RuntimeError(f"Y_transport key absent in {path}; keys={list(z.files)}")
        a = np.asarray(z["Y_transport"])
    if a.shape != Y_SHAPE:
        raise RuntimeError(f"Y shape mismatch {a.shape} in {path}")
    a = np.asarray(a, dtype=np.float32)
    if not np.isfinite(a).all():
        raise RuntimeError(f"nonfinite Y in {path}")
    return a


def parse_control(case_id: str):
    m = re.fullmatch(
        r"V16D_Foundation_Case_0029_R(350|500|650)_B(1800|2000|2200)",
        case_id,
    )
    if not m:
        raise RuntimeError(f"unexpected locked-OOD case id: {case_id}")
    return int(m.group(1)), int(m.group(2))


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16D-35")
    print("EXP-CS1 ONE-TOUCH FINAL LOCKED-OOD EVALUATION")
    print("=" * 78)
    print(
        "\nWARNING: successful creation of OOD_OPENED.lock permanently consumes "
        "the final geology0029 evaluation.\n"
    )

    # -------------------------------------------------------------------------
    # 1. Output directory must be new/empty; rerun after opening prohibited
    # -------------------------------------------------------------------------

    if OUT.exists():
        if OPEN_LOCK.exists():
            raise RuntimeError(
                "ONE-TOUCH EVALUATION ALREADY CONSUMED: OOD_OPENED.lock exists."
            )
        existing = list(OUT.iterdir())
        if existing:
            raise RuntimeError(
                "Final-evaluation output directory already exists and is not empty. "
                "D31D requires a new/empty directory before opening."
            )
    else:
        OUT.mkdir(parents=True, exist_ok=False)

    # -------------------------------------------------------------------------
    # 2. Read D34 binding; verify this exact source is the frozen evaluator
    # -------------------------------------------------------------------------

    require_file(D34_CONTRACT, "D34 binding contract")
    require_file(D34_SUMMARY, "D34 summary")

    binding = read_json(D34_CONTRACT)
    d34_summary = read_json(D34_SUMMARY)

    expected_status = (
        "V16D_EXP_CS1_FINAL_ONE_TOUCH_OOD_EVALUATOR_BINDING_FROZEN_"
        "OOD_REMAINS_SEALED_FINAL_EVALUATION_EXECUTION_AUTHORIZED"
    )

    if binding.get("status") != expected_status:
        raise RuntimeError("D34 binding contract status does not authorize D35.")

    if d34_summary.get("status") != expected_status:
        raise RuntimeError("D34 summary status does not authorize D35.")

    this_source = Path(__file__).resolve()
    this_sha = sha256(this_source)

    frozen_eval = binding["final_evaluator_source"]
    if this_sha != frozen_eval["sha256"]:
        raise RuntimeError(
            "This D35 source SHA does not match the evaluator frozen by D34."
        )

    # -------------------------------------------------------------------------
    # 3. All frozen authority hashes before any OOD np.load
    # -------------------------------------------------------------------------

    authorities = binding["frozen_authorities"]

    for label, record in authorities.items():
        if not isinstance(record, dict) or "path" not in record or "sha256" not in record:
            continue
        p = resolve_path(record["path"])
        require_file(p, label)
        actual = sha256(p)
        if actual != record["sha256"]:
            raise RuntimeError(
                f"Frozen authority SHA mismatch for {label}: {actual} != {record['sha256']}"
            )

    selected = binding["selected_model"]

    architecture_path = resolve_path(selected["architecture_path"])
    checkpoint_path = resolve_path(selected["checkpoint_path"])

    require_file(architecture_path, "selected architecture")
    require_file(checkpoint_path, "selected checkpoint")

    if sha256(architecture_path) != selected["architecture_sha256"]:
        raise RuntimeError("selected architecture SHA mismatch")

    if sha256(checkpoint_path) != selected["checkpoint_sha256"]:
        raise RuntimeError("selected checkpoint SHA mismatch")

    # -------------------------------------------------------------------------
    # 4. Exact 9-case OOD inventory hashes — raw-byte checks only
    # -------------------------------------------------------------------------

    inventory = binding["locked_OOD_inventory"]
    cases = inventory["cases"]

    if len(cases) != 9:
        raise RuntimeError("D34 locked-OOD inventory must contain exactly 9 cases.")

    expected_ids = [
        f"V16D_Foundation_Case_0029_R{r}_B{b}"
        for r in RATES_TPD
        for b in BHP_PSI
    ]

    if [x["case_id"] for x in cases] != expected_ids:
        raise RuntimeError("D34 locked-OOD case order/identity mismatch.")

    for rec in cases:
        xp = resolve_path(rec["X_normalized_path"])
        yp = resolve_path(rec["Y_stage4_path"])

        require_file(xp, f"{rec['case_id']} X")
        require_file(yp, f"{rec['case_id']} Y")

        if sha256(xp) != rec["X_normalized_sha256"]:
            raise RuntimeError(f"{rec['case_id']}: frozen X SHA mismatch")

        if sha256(yp) != rec["Y_stage4_sha256"]:
            raise RuntimeError(f"{rec['case_id']}: frozen Y SHA mismatch")

    print("PRE-OPEN HASH PREFLIGHT: PASS")
    print("  architecture/checkpoint/normalization/feature/data authorities: exact")
    print("  all 9 OOD normalized X artifact hashes: exact")
    print("  all 9 OOD Stage-4 Y artifact hashes: exact")
    print("  no OOD array loaded yet")

    # -------------------------------------------------------------------------
    # 5. Build/load the exact one frozen model BEFORE OOD opening
    # -------------------------------------------------------------------------

    import tensorflow as tf

    seed = int(binding["selected_model"]["seed"])
    tf.keras.utils.set_random_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:
        pass

    inp = tf.keras.Input(shape=(N_NODES, N_CHANNELS), name="C20_predictors")
    x = tf.keras.layers.LSTM(
        64, return_sequences=True, name="lstm_1"
    )(inp)
    x = tf.keras.layers.LSTM(
        64, return_sequences=True, name="lstm_2"
    )(x)
    raw = tf.keras.layers.TimeDistributed(
        tf.keras.layers.Dense(1, activation="sigmoid"),
        name="td_sigmoid",
    )(x)
    out = tf.keras.layers.Rescaling(
        scale=0.6,
        offset=0.2,
        name="bounded_Sw_0p2_0p8",
    )(raw)
    model = tf.keras.Model(inp, out, name="V16D_EXP_CS1")

    _ = model(
        tf.zeros((1, N_NODES, N_CHANNELS), dtype=tf.float32),
        training=False,
    )
    model.load_weights(checkpoint_path)

    print("MODEL/CHECKPOINT LOAD: PASS")
    print("  checkpoint:", selected["checkpoint_sha256"])
    print("  OOD arrays remain unopened")

    # -------------------------------------------------------------------------
    # 6. Atomically consume the one-touch evaluation
    # -------------------------------------------------------------------------

    atomic_create_lock(
        OPEN_LOCK,
        {
            "milestone": "V16D-35",
            "experiment": "EXP-CS1",
            "meaning": (
                "Final geology0029 locked-OOD evaluation consumed. "
                "This experiment may never be rerun or tuned against OOD."
            ),
            "D34_contract_sha256": sha256(D34_CONTRACT),
            "evaluator_source_sha256": this_sha,
            "checkpoint_sha256": selected["checkpoint_sha256"],
            "created_unix_time": time.time(),
        },
    )

    print("\nOOD_OPENED.lock CREATED")
    print("  The one-touch evaluation is now permanently consumed.")

    # -------------------------------------------------------------------------
    # 7. Preregistered metric accumulators
    # -------------------------------------------------------------------------

    aggregate = blank_error_accum()
    time_acc = [blank_error_accum() for _ in TARGET_DAYS]
    rate_acc = {r: blank_error_accum() for r in RATES_TPD}
    bhp_acc = {b: blank_error_accum() for b in BHP_PSI}

    case_results = []

    below_count = 0
    above_count = 0
    pred_count = 0
    max_lower_violation = 0.0
    max_upper_violation = 0.0

    injector_abs_sum = 0.0
    injector_count = 0

    temporal_negative_count = 0
    temporal_diff_count = 0

    spatial_positive_count = 0
    spatial_diff_count = 0

    # -------------------------------------------------------------------------
    # 8. Exactly all 9 locked-OOD cases, no exclusions
    # -------------------------------------------------------------------------

    for idx, rec in enumerate(cases, 1):
        cid = rec["case_id"]
        rate, bhp = parse_control(cid)

        xp = resolve_path(rec["X_normalized_path"])
        yp = resolve_path(rec["Y_stage4_path"])

        # First OOD arrays are loaded only after OOD_OPENED.lock.
        X = load_x(xp)
        Y = load_y(yp)

        Xseq = X.reshape(-1, N_NODES, N_CHANNELS)
        pred = model.predict(
            Xseq,
            batch_size=PREDICTION_BATCH_SIZE,
            verbose=0,
        )
        pred = np.asarray(pred, dtype=np.float32).reshape(Y_SHAPE)

        if not np.isfinite(pred).all():
            raise RuntimeError(f"{cid}: nonfinite predictions")

        case_acc = blank_error_accum()
        update_error_accum(case_acc, pred, Y)
        update_error_accum(aggregate, pred, Y)
        update_error_accum(rate_acc[rate], pred, Y)
        update_error_accum(bhp_acc[bhp], pred, Y)

        for ti in range(N_TIMES):
            update_error_accum(time_acc[ti], pred[ti], Y[ti])

        # Prediction physics diagnostics — semantics frozen by D34.
        p64 = np.asarray(pred, dtype=np.float64)

        below = p64 < SWC
        above = p64 > ONE_MINUS_SOR
        below_count += int(below.sum())
        above_count += int(above.sum())
        pred_count += int(p64.size)

        max_lower_violation = max(
            max_lower_violation,
            max(0.0, SWC - float(p64.min())),
        )
        max_upper_violation = max(
            max_upper_violation,
            max(0.0, float(p64.max()) - ONE_MINUS_SOR),
        )

        injector_err = np.abs(p64[:, :, 0] - INJECTION_BOUNDARY_SW)
        injector_abs_sum += float(injector_err.sum(dtype=np.float64))
        injector_count += int(injector_err.size)

        temporal_diff = np.diff(p64, axis=0)
        temporal_negative_count += int(
            (temporal_diff < TEMPORAL_NEGATIVE_THRESHOLD).sum()
        )
        temporal_diff_count += int(temporal_diff.size)

        spatial_diff = np.diff(p64, axis=2)
        spatial_positive_count += int(
            (spatial_diff > SPATIAL_POSITIVE_THRESHOLD).sum()
        )
        spatial_diff_count += int(spatial_diff.size)

        cr = finalize_error_accum(case_acc)
        cr.update(
            {
                "case_id": cid,
                "geology": "0029",
                "injection_rate_tpd": rate,
                "producer_bhp_psi": bhp,
            }
        )
        case_results.append(cr)

        print(
            f"[{idx:02d}/09] {cid} "
            f"RMSE={cr['RMSE']:.8e} MAE={cr['MAE']:.8e}"
        )

    # -------------------------------------------------------------------------
    # 9. Freeze all preregistered outputs
    # -------------------------------------------------------------------------

    agg = finalize_error_accum(aggregate)

    time_results = []
    for day, acc in zip(TARGET_DAYS, time_acc):
        r = finalize_error_accum(acc)
        time_results.append(
            {
                "time_days": day,
                "MSE": r["MSE"],
                "RMSE": r["RMSE"],
                "MAE": r["MAE"],
                "max_abs_error": r["max_abs_error"],
                "values": r["values"],
            }
        )

    by_rate = {}
    for rate, acc in rate_acc.items():
        r = finalize_error_accum(acc)
        by_rate[str(rate)] = {
            "RMSE": r["RMSE"],
            "MAE": r["MAE"],
            "values": r["values"],
        }

    by_bhp = {}
    for bhp, acc in bhp_acc.items():
        r = finalize_error_accum(acc)
        by_bhp[str(bhp)] = {
            "RMSE": r["RMSE"],
            "MAE": r["MAE"],
            "values": r["values"],
        }

    physics = {
        "Swc": SWC,
        "one_minus_Sor": ONE_MINUS_SOR,
        "fraction_predictions_below_Swc": below_count / pred_count,
        "fraction_predictions_above_one_minus_Sor": above_count / pred_count,
        "maximum_lower_bound_violation": max_lower_violation,
        "maximum_upper_bound_violation": max_upper_violation,
        "injector_node_boundary_Sw": INJECTION_BOUNDARY_SW,
        "injector_node_mean_absolute_error": injector_abs_sum / injector_count,
        "temporal_negative_threshold": TEMPORAL_NEGATIVE_THRESHOLD,
        "temporal_negative_fraction": (
            temporal_negative_count / temporal_diff_count
        ),
        "spatial_positive_threshold": SPATIAL_POSITIVE_THRESHOLD,
        "spatial_positive_fraction": (
            spatial_positive_count / spatial_diff_count
        ),
        "prediction_values": pred_count,
        "temporal_differences": temporal_diff_count,
        "spatial_differences": spatial_diff_count,
    }

    frozen_val = binding["frozen_validation_metrics"]
    val_rmse = float(frozen_val["RMSE"])
    val_mae = float(frozen_val["MAE"])

    if not (val_rmse > 0.0 and val_mae > 0.0):
        raise RuntimeError("frozen validation denominators must be positive")

    gaps = {
        "OOD_RMSE_over_frozen_validation_RMSE": agg["RMSE"] / val_rmse,
        "OOD_MAE_over_frozen_validation_MAE": agg["MAE"] / val_mae,
        "frozen_validation_RMSE": val_rmse,
        "frozen_validation_MAE": val_mae,
    }

    result = {
        "milestone": "V16D-35",
        "experiment": "EXP-CS1",
        "evaluation_role": "ONE_TOUCH_FINAL_LOCKED_OOD_TEST",
        "LOCKED_OOD": {
            "partition": "LOCKED_OOD_TEST",
            "geology": "0029",
            "cases_evaluated": 9,
            "case_ids": [x["case_id"] for x in cases],
            "target_days": TARGET_DAYS,
            "opening_lock": str(OPEN_LOCK.relative_to(R)),
            "opening_lock_sha256": sha256(OPEN_LOCK),
        },
        "selected_model": {
            "architecture_sha256": selected["architecture_sha256"],
            "checkpoint_sha256": selected["checkpoint_sha256"],
            "evaluator_source_sha256": this_sha,
        },
        "aggregate": agg,
        "case_level": case_results,
        "time_resolved": time_results,
        "control_resolved": {
            "by_injection_rate_tpd": by_rate,
            "by_producer_bhp_psi": by_bhp,
        },
        "prediction_physics_diagnostics": physics,
        "validation_generalization_gap": gaps,
        "precision": "float64 error accumulation",
        "result_policy": {
            "all_9_cases_included": True,
            "all_9_times_included": True,
            "all_1078_streamlines_per_case_included": True,
            "all_201_nodes_included": True,
            "no_deduplication": True,
            "no_adaptation": True,
            "no_threshold_fitting": True,
            "poor_results_reported_without_suppression": True,
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
            "OOD_informed_model_selection": "PROHIBITED",
            "new_learning_requires_new_independent_locked_test": True,
        },
    }

    RESULT_JSON.write_text(json.dumps(result, indent=2))

    status = (
        "V16D_EXP_CS1_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION_COMPLETED_"
        "OOD_CONSUMED_NO_FURTHER_TUNING_AUTHORIZED"
    )

    summary = {
        "milestone": "V16D-35",
        "experiment": "EXP-CS1",
        "status": status,
        "OOD_opened": True,
        "OOD_evaluated": True,
        "OOD_consumed": True,
        "cases_evaluated": 9,
        "aggregate_MSE": agg["MSE"],
        "aggregate_RMSE": agg["RMSE"],
        "aggregate_MAE": agg["MAE"],
        "validation_gap_RMSE_ratio":
            gaps["OOD_RMSE_over_frozen_validation_RMSE"],
        "validation_gap_MAE_ratio":
            gaps["OOD_MAE_over_frozen_validation_MAE"],
        "results_sha256": sha256(RESULT_JSON),
        "opening_lock_sha256": sha256(OPEN_LOCK),
        "checkpoint_sha256": selected["checkpoint_sha256"],
        "evaluator_source_sha256": this_sha,
        "next_milestone": (
            "V16D-36 — Post-OOD scientific interpretation and structural/"
            "front/time/control diagnostics using the same frozen results only; "
            "no retraining or tuning under EXP-CS1"
        ),
    }

    SUMMARY_JSON.write_text(json.dumps(summary, indent=2))

    print("\n" + "=" * 78)
    print("ONE-TOUCH FINAL OOD RESULT")
    print("=" * 78)
    print("  OOD MSE  : %.12e" % agg["MSE"])
    print("  OOD RMSE : %.12e" % agg["RMSE"])
    print("  OOD MAE  : %.12e" % agg["MAE"])
    print(
        "  RMSE gap : %.6f x validation"
        % gaps["OOD_RMSE_over_frozen_validation_RMSE"]
    )
    print(
        "  MAE gap  : %.6f x validation"
        % gaps["OOD_MAE_over_frozen_validation_MAE"]
    )
    print("\nSTATUS")
    print(" ", status)
    print("\nOOD STATUS")
    print("  OPENED / EVALUATED / CONSUMED — rerun prohibited.")
    print("\nResults SHA-256:", sha256(RESULT_JSON))
    print("Summary SHA-256:", sha256(SUMMARY_JSON))


if __name__ == "__main__":
    main()
