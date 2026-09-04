from __future__ import annotations

from pathlib import Path
import argparse
import csv
import json
import math
import shutil
import time

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7C-R3E
# Controlled Frozen-Model Deployment Calibration
#
# TRAINING MILESTONE — CALIBRATOR ONLY
#
# SG7B-11 REMAINS FROZEN.
# NO PI-RNN WEIGHTS ARE CHANGED.
# NO PI-RNN ARCHITECTURE CHANGE.
# NO SG6 GEOMETRY CHANGE.
# NO DEPLOYMENT FEATURE CONVENTION CHANGE.
# NO TARGET SCALING CHANGE.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# R3D-R established a valid calibration contract after proving that:
#
#   * canonical target interpolation reproduces SG7A deployment truth,
#   * the frozen PI-RNN retains a material deployment approximation residual,
#   * the front residual is physically meaningful and points directly toward
#     the canonical / SG7A target,
#   * front preservation must therefore be judged by OUTCOME rather than by
#     forcing deltaS_front ~ 0.
#
# R3E fits small deployment-only residual calibrators:
#
#     deltaS_cal = g(xi, normalized_tD, log10(tau_end), S_frozen,
#                    |S_frozen - 0.21|)
#
#     S_cal = S_frozen + deltaS_cal
#
# Candidate selection requires:
#
#   * exact SG7B-10S front recovery / threshold-gap / 100d profile-L1 gates,
#   * SG7B-15R frozen-front displacement guards,
#   * residual directionality and overshoot guards,
#   * short-TOF calibration safeguard,
#   * calibration magnitude / smoothness safeguards,
#   * long-TOF residual improvement.
#
# R3E may NOMINATE a calibrator. It does NOT declare a new frozen authority.
# =============================================================================


ROOT = Path(__file__).resolve().parent

R3DR_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3DR"
    / "PAD_Stream_V15SG7CR3DR_Summary.json"
)

R3DR_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3DR"
    / "V15SG7CR3DR_Frozen_Deployment_Calibration_Contract.json"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3E"
EXPERIMENT_DIR = OUTPUT_DIR / "experiments"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

METRICS_FILE = OUTPUT_DIR / "V15SG7CR3E_Experiment_Metrics.csv"
GATES_FILE = OUTPUT_DIR / "V15SG7CR3E_Final_Gate_Matrix.csv"
EPOCH_FILE = OUTPUT_DIR / "V15SG7CR3E_Epoch_Metrics.csv"
CALIBRATED_DB_FILE = OUTPUT_DIR / "V15SG7CR3E_Calibrated_Streamline_Deployment.npz"
CANDIDATE_MODEL_FILE = OUTPUT_DIR / "V15SG7CR3E_Candidate_Calibrator.keras"
CANDIDATE_MANIFEST_FILE = OUTPUT_DIR / "V15SG7CR3E_Candidate_Manifest.json"
SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG7CR3E_Summary.json"


SEED = 15370
np.random.seed(SEED)
tf.random.set_seed(SEED)

FRONT_THRESHOLD = 0.210
FRONT_SHELL_LOW = 0.205
FRONT_SHELL_HIGH = 0.300
FRONT_CORE_LOW = 0.210
FRONT_CORE_HIGH = 0.260

LONG_TOF_MIN = 500.0
VERY_LONG_TOF_MIN = 1000.0

MAX_GLOBAL_ABS_CORRECTION = 0.10
MAX_SHORT_TOF_CAL_MAE = 0.0015
MAX_CALIBRATION_TV_RATIO = 0.20

MIN_FRONT_ERROR_REDUCTION = 0.50
MAX_FRONT_OVERSHOOT_FRACTION = 0.05
MIN_FRONT_CORRECTION_SIGN_AGREEMENT = 0.95

MAX_EPOCHS = 180
BATCH_SIZE = 4096
INITIAL_LR = 2.0e-3
MIN_LR = 2.0e-5
EVAL_EVERY = 5
EARLY_STOP_PATIENCE = 35


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def save_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def threshold_crossing_positions(field, xi, threshold):
    field = np.asarray(field, dtype=float)
    xi = np.asarray(xi, dtype=float)

    positions = np.full(field.shape[0], np.nan, dtype=float)
    resolved = np.zeros(field.shape[0], dtype=bool)

    for i in range(field.shape[0]):
        y = field[i] - threshold
        crossing = np.where(y[:-1] * y[1:] < 0.0)[0]

        if crossing.size == 0:
            continue

        j = int(crossing[0])

        y0 = y[j]
        y1 = y[j + 1]
        denom = y1 - y0

        if abs(denom) <= 1e-14:
            x = 0.5 * (xi[j] + xi[j + 1])
        else:
            f = float(np.clip(-y0 / denom, 0.0, 1.0))
            x = xi[j] + f * (xi[j + 1] - xi[j])

        positions[i] = x
        resolved[i] = True

    return positions, resolved


def front_metrics(prediction100, truth100, frozen100, xi):
    pred_pos, pred_ok = threshold_crossing_positions(
        prediction100, xi, FRONT_THRESHOLD
    )
    truth_pos, truth_ok = threshold_crossing_positions(
        truth100, xi, FRONT_THRESHOLD
    )
    frozen_pos, frozen_ok = threshold_crossing_positions(
        frozen100, xi, FRONT_THRESHOLD
    )

    recovered = int(np.sum(pred_ok & truth_ok))
    truth_fronts = int(np.sum(truth_ok))

    gaps = np.min(np.abs(prediction100 - FRONT_THRESHOLD), axis=1)
    conditioned_gap = float(np.mean(gaps[truth_ok])) if np.any(truth_ok) else np.nan

    profile_l1 = float(np.mean(np.abs(prediction100 - truth100)))

    common = pred_ok & frozen_ok & truth_ok

    if np.any(common):
        shift = np.abs(pred_pos[common] - frozen_pos[common])
        mean_shift = float(np.mean(shift))
        p90_shift = float(np.percentile(shift, 90))
    else:
        mean_shift = np.inf
        p90_shift = np.inf

    return {
        "truth_fronts": truth_fronts,
        "recovered_fronts": recovered,
        "conditioned_gap": conditioned_gap,
        "profile_L1_100d": profile_l1,
        "mean_frozen_front_xi_shift": mean_shift,
        "P90_frozen_front_xi_shift": p90_shift,
    }


def calibration_safeguards(
    calibrated,
    frozen,
    target,
    truth,
    tau_end_days,
    xi,
    idx100,
):
    delta = calibrated - frozen
    err_before = frozen - truth
    err_after = calibrated - truth

    truth100 = truth[idx100]
    delta100 = delta[idx100]
    err_before100 = err_before[idx100]
    err_after100 = err_after[idx100]

    shell = (
        (truth100 >= FRONT_SHELL_LOW)
        &
        (truth100 <= FRONT_SHELL_HIGH)
    )

    short = tau_end_days < LONG_TOF_MIN

    front_before = float(np.mean(np.abs(err_before100[shell])))
    front_after = float(np.mean(np.abs(err_after100[shell])))

    front_reduction = (
        1.0 - front_after / max(front_before, 1e-15)
    )

    required = target[idx100][shell] - frozen[idx100][shell]
    applied = delta100[shell]

    # Sign agreement relative to required residual direction.
    sign_agreement = float(
        np.mean(
            applied * required >= -1e-12
        )
    )

    # Overshoot: applied correction magnitude exceeds ideal required correction
    # while remaining in same sign direction.
    overshoot = (
        np.abs(applied) > (np.abs(required) + 1e-6)
    )
    overshoot_fraction = float(np.mean(overshoot))

    short_cal_mae = float(
        np.mean(
            np.abs(
                delta[:, short, :]
            )
        )
    )

    global_max = float(np.max(np.abs(delta)))

    # Calibration TV / frozen-state TV ratio.
    d_delta = np.diff(delta, axis=2)
    d_frozen = np.diff(frozen, axis=2)

    tv_delta = float(np.mean(np.sum(np.abs(d_delta), axis=2)))
    tv_frozen = float(np.mean(np.sum(np.abs(d_frozen), axis=2)))

    tv_ratio = tv_delta / max(tv_frozen, 1e-12)

    return {
        "front_error_before": front_before,
        "front_error_after": front_after,
        "front_error_reduction_fraction": front_reduction,
        "front_sign_agreement": sign_agreement,
        "front_overshoot_fraction": overshoot_fraction,
        "short_TOF_calibration_MAE": short_cal_mae,
        "global_abs_correction_MAX": global_max,
        "calibration_TV_ratio": tv_ratio,
    }


def bias_by_tof(calibrated, truth, tau_end_days):
    err = calibrated - truth

    bands = [
        ("500_1000", 500.0, 1000.0),
        ("1000_2000", 1000.0, 2000.0),
        ("gt2000", 2000.0, np.inf),
    ]

    out = {}

    for label, lo, hi in bands:
        sl = (tau_end_days >= lo) & (tau_end_days < hi)
        if not np.any(sl):
            out[f"bias_{label}"] = np.nan
            out[f"L1_{label}"] = np.nan
            continue

        vals = err[:, sl, :]
        out[f"bias_{label}"] = float(np.mean(vals))
        out[f"L1_{label}"] = float(np.mean(np.abs(vals)))

    return out


def make_features(xi, normalized_tD, tau_end_days, frozen):
    nt, ns, nx = frozen.shape

    xi3 = np.broadcast_to(
        xi[None, None, :],
        (nt, ns, nx),
    )

    tnorm3 = np.broadcast_to(
        normalized_tD[:, :, None],
        (nt, ns, nx),
    )

    logtau = np.log10(np.maximum(tau_end_days, 1.0))
    logtau_norm = (
        logtau - np.mean(logtau)
    ) / max(np.std(logtau), 1e-12)

    logtau3 = np.broadcast_to(
        logtau_norm[None, :, None],
        (nt, ns, nx),
    )

    front_distance = np.abs(
        frozen - FRONT_THRESHOLD
    )

    features = np.stack(
        [
            xi3,
            tnorm3,
            logtau3,
            frozen,
            front_distance,
        ],
        axis=-1,
    ).astype(np.float32)

    return features


def build_calibrator(kind: str):
    inputs = tf.keras.Input(shape=(5,), name="calibration_features")

    if kind == "linear":
        x = tf.keras.layers.Dense(
            1,
            activation=None,
            kernel_initializer="zeros",
            bias_initializer="zeros",
        )(inputs)

    elif kind == "mlp16":
        x = tf.keras.layers.Dense(16, activation="tanh")(inputs)
        x = tf.keras.layers.Dense(16, activation="tanh")(x)
        x = tf.keras.layers.Dense(
            1,
            activation=None,
            kernel_initializer="zeros",
            bias_initializer="zeros",
        )(x)

    elif kind == "mlp8":
        x = tf.keras.layers.Dense(8, activation="tanh")(inputs)
        x = tf.keras.layers.Dense(8, activation="tanh")(x)
        x = tf.keras.layers.Dense(
            1,
            activation=None,
            kernel_initializer="zeros",
            bias_initializer="zeros",
        )(x)

    else:
        raise ValueError(f"Unknown calibrator kind: {kind}")

    # Bound raw correction smoothly to +/- 0.10.
    outputs = tf.keras.layers.Lambda(
        lambda z: 0.10 * tf.tanh(z / 0.10),
        name="bounded_deltaS",
    )(x)

    return tf.keras.Model(inputs, outputs, name=f"R3E_{kind}_calibrator")


def experiment_configs():
    return [
        {
            "experiment": "E0",
            "description": "Frozen SG7B-11 control",
            "kind": None,
            "tof_gate": False,
            "front_weight": 0.0,
            "cross_weight": 0.0,
            "shape_weight": 0.0,
            "short_weight": 0.0,
            "smooth_weight": 0.0,
            "direction_weight": 0.0,
        },
        {
            "experiment": "E1",
            "description": "Linear canonical-residual calibration",
            "kind": "linear",
            "tof_gate": False,
            "front_weight": 2.0,
            "cross_weight": 1.0,
            "shape_weight": 0.5,
            "short_weight": 1.0,
            "smooth_weight": 0.25,
            "direction_weight": 0.5,
        },
        {
            "experiment": "E2",
            "description": "Small canonical-residual MLP",
            "kind": "mlp16",
            "tof_gate": False,
            "front_weight": 3.0,
            "cross_weight": 2.0,
            "shape_weight": 1.0,
            "short_weight": 1.5,
            "smooth_weight": 0.5,
            "direction_weight": 1.0,
        },
        {
            "experiment": "E3",
            "description": "TOF-gated canonical-residual MLP",
            "kind": "mlp16",
            "tof_gate": True,
            "front_weight": 4.0,
            "cross_weight": 2.0,
            "shape_weight": 1.0,
            "short_weight": 2.5,
            "smooth_weight": 0.75,
            "direction_weight": 1.0,
        },
        {
            "experiment": "E4",
            "description": "Front-aware TOF-gated residual MLP",
            "kind": "mlp16",
            "tof_gate": True,
            "front_weight": 6.0,
            "cross_weight": 4.0,
            "shape_weight": 2.0,
            "short_weight": 3.0,
            "smooth_weight": 1.0,
            "direction_weight": 1.5,
        },
        {
            "experiment": "E5",
            "description": "Conservative front-aware residual calibration",
            "kind": "mlp8",
            "tof_gate": True,
            "front_weight": 8.0,
            "cross_weight": 5.0,
            "shape_weight": 2.5,
            "short_weight": 4.0,
            "smooth_weight": 1.5,
            "direction_weight": 2.0,
        },
    ]


def evaluate_candidate(
    calibrated,
    frozen,
    target,
    truth,
    tau_end_days,
    xi,
    times_days,
    exact_front,
    displacement_guards,
):
    idx100 = int(np.argmin(np.abs(times_days - 100.0)))

    front = front_metrics(
        calibrated[idx100],
        truth[idx100],
        frozen[idx100],
        xi,
    )

    safeguard = calibration_safeguards(
        calibrated,
        frozen,
        target,
        truth,
        tau_end_days,
        xi,
        idx100,
    )

    tof = bias_by_tof(
        calibrated,
        truth,
        tau_end_days,
    )

    global_l1 = float(
        np.mean(
            np.abs(
                calibrated - truth
            )
        )
    )

    global_l2 = float(
        np.sqrt(
            np.mean(
                (calibrated - truth) ** 2
            )
        )
    )

    gates = {
        "recovered_fronts": (
            front["recovered_fronts"]
            >= int(exact_front["minimum_recovered_fronts"])
        ),
        "conditioned_gap": (
            front["conditioned_gap"]
            <= float(exact_front["maximum_conditioned_threshold_gap"])
        ),
        "profile_L1_100d": (
            front["profile_L1_100d"]
            <= float(exact_front["maximum_100d_profile_L1"])
        ),
        "mean_front_xi_shift": (
            front["mean_frozen_front_xi_shift"]
            <= float(displacement_guards["maximum_mean_frozen_front_xi_shift"])
        ),
        "P90_front_xi_shift": (
            front["P90_frozen_front_xi_shift"]
            <= float(displacement_guards["maximum_P90_frozen_front_xi_shift"])
        ),
        "front_error_reduction": (
            safeguard["front_error_reduction_fraction"]
            >= MIN_FRONT_ERROR_REDUCTION
        ),
        "front_sign_agreement": (
            safeguard["front_sign_agreement"]
            >= MIN_FRONT_CORRECTION_SIGN_AGREEMENT
        ),
        "front_overshoot": (
            safeguard["front_overshoot_fraction"]
            <= MAX_FRONT_OVERSHOOT_FRACTION
        ),
        "short_TOF_calibration": (
            safeguard["short_TOF_calibration_MAE"]
            <= MAX_SHORT_TOF_CAL_MAE
        ),
        "global_correction_bound": (
            safeguard["global_abs_correction_MAX"]
            <= MAX_GLOBAL_ABS_CORRECTION
        ),
        "calibration_TV": (
            safeguard["calibration_TV_ratio"]
            <= MAX_CALIBRATION_TV_RATIO
        ),
        "bias_500_1000": (
            abs(tof["bias_500_1000"])
            <= 2.5e-3
        ),
        "bias_1000_2000": (
            abs(tof["bias_1000_2000"])
            <= 4.5e-3
        ),
        "bias_gt2000": (
            abs(tof["bias_gt2000"])
            <= 5.0e-3
        ),
    }

    complete_pass = bool(all(gates.values()))

    return {
        "front": front,
        "safeguard": safeguard,
        "tof": tof,
        "global_L1": global_l1,
        "global_L2": global_l2,
        "gates": gates,
        "complete_pass": complete_pass,
    }


def score_candidate(metrics):
    f = metrics["front"]
    s = metrics["safeguard"]
    t = metrics["tof"]

    return float(
        metrics["global_L1"]
        + 2.0 * f["conditioned_gap"]
        + 0.5 * f["profile_L1_100d"]
        + 0.5 * abs(t["bias_500_1000"])
        + 0.25 * abs(t["bias_1000_2000"])
        + 0.25 * abs(t["bias_gt2000"])
        + 0.25 * s["short_TOF_calibration_MAE"]
        + 0.10 * s["calibration_TV_ratio"]
    )


def train_experiment(
    config,
    features,
    residual_target,
    frozen,
    target,
    truth,
    tau_end_days,
    xi,
    times_days,
    exact_front,
    displacement_guards,
):
    exp = config["experiment"]

    exp_dir = EXPERIMENT_DIR / exp
    exp_dir.mkdir(parents=True, exist_ok=True)

    model = build_calibrator(config["kind"])

    X = features.reshape(-1, 5)
    y = residual_target.reshape(-1, 1).astype(np.float32)

    # Masks
    nt, ns, nx = frozen.shape

    truth_flat = truth.reshape(-1)
    frozen_flat = frozen.reshape(-1)

    tau3 = np.broadcast_to(
        tau_end_days[None, :, None],
        (nt, ns, nx),
    ).reshape(-1)

    shell = (
        (truth_flat >= FRONT_SHELL_LOW)
        &
        (truth_flat <= FRONT_SHELL_HIGH)
    ).astype(np.float32)

    core = (
        (truth_flat >= FRONT_CORE_LOW)
        &
        (truth_flat <= FRONT_CORE_HIGH)
    ).astype(np.float32)

    short = (
        tau3 < LONG_TOF_MIN
    ).astype(np.float32)

    long_mask = (
        tau3 >= LONG_TOF_MIN
    ).astype(np.float32)

    if config["tof_gate"]:
        # Smoothly reduce residual loss on short TOF while keeping target learning
        # active everywhere.
        tof_weight = 0.25 + 0.75 * long_mask
    else:
        tof_weight = np.ones_like(long_mask)

    sample_weight = (
        tof_weight
        + config["front_weight"] * shell
        + 0.5 * config["front_weight"] * core
    ).astype(np.float32)

    ds = tf.data.Dataset.from_tensor_slices(
        (
            X.astype(np.float32),
            y,
            sample_weight[:, None],
            short[:, None],
            shell[:, None],
        )
    ).shuffle(
        min(len(X), 500000),
        seed=SEED + int(exp[1:]),
        reshuffle_each_iteration=True,
    ).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

    optimizer = tf.keras.optimizers.Adam(INITIAL_LR)

    @tf.function
    def step(xb, yb, wb, shortb, shellb):
        with tf.GradientTape() as tape:
            pred = model(xb, training=True)

            residual_loss = tf.reduce_sum(
                wb * tf.abs(pred - yb)
            ) / (tf.reduce_sum(wb) + 1e-8)

            short_anchor = tf.reduce_sum(
                shortb * tf.abs(pred)
            ) / (tf.reduce_sum(shortb) + 1e-8)

            # Shell target is canonical residual, not zero.
            shell_state = tf.reduce_sum(
                shellb * tf.abs(pred - yb)
            ) / (tf.reduce_sum(shellb) + 1e-8)

            # Penalize wrong-direction correction.
            direction_penalty = tf.reduce_mean(
                tf.nn.relu(
                    -(pred * yb)
                )
            )

            total = (
                residual_loss
                + config["short_weight"] * short_anchor
                + config["front_weight"] * shell_state
                + config["direction_weight"] * direction_penalty
            )

        grads = tape.gradient(total, model.trainable_variables)
        grads, _ = tf.clip_by_global_norm(grads, 5.0)
        optimizer.apply_gradients(zip(grads, model.trainable_variables))

        return total

    history = []
    best_score = np.inf
    best_weights = None
    best_epoch = -1
    patience = 0
    lr = INITIAL_LR

    start = time.perf_counter()

    for epoch in range(1, MAX_EPOCHS + 1):
        for batch in ds:
            step(*batch)

        if epoch == 1 or epoch % EVAL_EVERY == 0:
            delta = model.predict(
                X,
                batch_size=8192,
                verbose=0,
            ).reshape(frozen.shape)

            # Mild post-model spatial smoothing is NOT applied; all safeguards
            # are evaluated on raw calibrator output.
            calibrated = frozen + delta

            metrics = evaluate_candidate(
                calibrated,
                frozen,
                target,
                truth,
                tau_end_days,
                xi,
                times_days,
                exact_front,
                displacement_guards,
            )

            sc = score_candidate(metrics)

            history.append({
                "experiment": exp,
                "epoch": epoch,
                "score": sc,
                "global_L1": metrics["global_L1"],
                "conditioned_gap": metrics["front"]["conditioned_gap"],
                "profile_L1_100d": metrics["front"]["profile_L1_100d"],
                "recovered_fronts": metrics["front"]["recovered_fronts"],
                "front_error_reduction": metrics["safeguard"]["front_error_reduction_fraction"],
                "front_sign_agreement": metrics["safeguard"]["front_sign_agreement"],
                "front_overshoot_fraction": metrics["safeguard"]["front_overshoot_fraction"],
                "short_TOF_calibration_MAE": metrics["safeguard"]["short_TOF_calibration_MAE"],
                "calibration_TV_ratio": metrics["safeguard"]["calibration_TV_ratio"],
                "bias_500_1000": metrics["tof"]["bias_500_1000"],
                "bias_1000_2000": metrics["tof"]["bias_1000_2000"],
                "bias_gt2000": metrics["tof"]["bias_gt2000"],
                "complete_pass": metrics["complete_pass"],
            })

            print(
                f"  {exp} | epoch={epoch:3d} | "
                f"L1={metrics['global_L1']:.3e} | "
                f"fronts={metrics['front']['recovered_fronts']:4d}/"
                f"{metrics['front']['truth_fronts']:4d} | "
                f"gap={metrics['front']['conditioned_gap']:.3e} | "
                f"frontRed={100*metrics['safeguard']['front_error_reduction_fraction']:.1f}% | "
                f"shortCal={metrics['safeguard']['short_TOF_calibration_MAE']:.3e} | "
                f"B500={metrics['tof']['bias_500_1000']:.3e} | "
                f"B1000={metrics['tof']['bias_1000_2000']:.3e} | "
                f"B2000={metrics['tof']['bias_gt2000']:.3e} | "
                f"{'PASS' if metrics['complete_pass'] else 'FAIL'}"
            )

            if metrics["complete_pass"] and sc < best_score:
                best_score = sc
                best_epoch = epoch
                best_weights = model.get_weights()
                patience = 0
            else:
                patience += EVAL_EVERY

            if metrics["complete_pass"] and epoch >= 20:
                break

            if patience >= EARLY_STOP_PATIENCE:
                break

            if patience > 0 and patience % 15 == 0:
                lr = max(lr * 0.5, MIN_LR)
                optimizer.learning_rate.assign(lr)

    runtime = time.perf_counter() - start

    if best_weights is None:
        return {
            "experiment": exp,
            "description": config["description"],
            "model": model,
            "best_epoch": -1,
            "best_score": np.inf,
            "metrics": None,
            "calibrated": None,
            "delta": None,
            "history": history,
            "runtime_seconds": runtime,
            "complete_pass": False,
        }

    model.set_weights(best_weights)

    delta = model.predict(
        X,
        batch_size=8192,
        verbose=0,
    ).reshape(frozen.shape)

    calibrated = frozen + delta

    metrics = evaluate_candidate(
        calibrated,
        frozen,
        target,
        truth,
        tau_end_days,
        xi,
        times_days,
        exact_front,
        displacement_guards,
    )

    model.save(
        exp_dir / f"V15SG7CR3E_{exp}_Best_Calibrator.keras"
    )

    return {
        "experiment": exp,
        "description": config["description"],
        "model": model,
        "best_epoch": best_epoch,
        "best_score": best_score,
        "metrics": metrics,
        "calibrated": calibrated,
        "delta": delta,
        "history": history,
        "runtime_seconds": runtime,
        "complete_pass": metrics["complete_pass"],
    }


def main():

    parser = argparse.ArgumentParser(
        description="PAD-Stream V15-SG7C-R3E controlled frozen-model deployment calibration."
    )

    parser.add_argument(
        "--experiments",
        type=str,
        default="E1,E2,E3,E4,E5",
        help="Comma-separated trainable experiments.",
    )

    args = parser.parse_args()

    selected = {
        item.strip()
        for item in args.experiments.split(",")
        if item.strip()
    }

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3E")
    print("Controlled Frozen-Model Deployment Calibration")
    print("=" * 78)

    print("\nCALIBRATOR TRAINING WILL BE PERFORMED FOR SELECTED E1-E5.")
    print("SG7B-11 PI-RNN WEIGHTS WILL NOT BE CHANGED.")
    print("NO PI-RNN ARCHITECTURE CHANGE WILL BE MADE.")
    print("NO FEATURE, TARGET, MAP-BACK, OR SG7E GATE WILL BE CHANGED.")
    print("NO CALIBRATOR WILL BE DECLARED FROZEN BY R3E.")

    for path in [
        R3DR_SUMMARY,
        R3DR_CONTRACT,
        R3C_NUMERICAL,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing R3E prerequisite:\n{path}")

    summary_dr = load_json(R3DR_SUMMARY)
    contract = load_json(R3DR_CONTRACT)

    if summary_dr.get("status") != "FROZEN_DEPLOYMENT_CALIBRATION_CONTRACT_READY":
        raise RuntimeError(
            "R3E requires R3D-R ready contract status."
        )

    db = np.load(R3C_NUMERICAL, allow_pickle=True)

    canonical_interp = np.asarray(
        db["canonical_interpolated_target"],
        dtype=float,
    )

    frozen = np.asarray(
        db["deployment_pirnn"],
        dtype=float,
    )

    truth = np.asarray(
        db["deployment_truth"],
        dtype=float,
    )

    tau_end_days = np.asarray(
        db["tau_end_days"],
        dtype=float,
    )

    times_days = np.asarray(
        db["times_days"],
        dtype=float,
    )

    normalized_input = np.asarray(
        db["deployment_normalized_input"],
        dtype=float,
    )

    xi = np.asarray(
        db["canonical_xi"],
        dtype=float,
    )

    residual_target = canonical_interp - frozen

    exact_front = contract["authoritative_front_contract"]
    displacement_guards = contract["authoritative_front_displacement_guards"]

    features = make_features(
        xi,
        normalized_input,
        tau_end_days,
        frozen,
    )

    # E0 control
    e0_metrics = evaluate_candidate(
        frozen,
        frozen,
        canonical_interp,
        truth,
        tau_end_days,
        xi,
        times_days,
        exact_front,
        displacement_guards,
    )

    results = [{
        "experiment": "E0",
        "description": "Frozen SG7B-11 control",
        "best_epoch": 0,
        "best_score": score_candidate(e0_metrics),
        "metrics": e0_metrics,
        "calibrated": frozen,
        "delta": np.zeros_like(frozen),
        "history": [],
        "runtime_seconds": 0.0,
        "complete_pass": e0_metrics["complete_pass"],
        "model": None,
    }]

    print("\n" + "=" * 78)
    print("CONTROLLED CALIBRATION EXPERIMENTS")
    print("=" * 78)

    configs = experiment_configs()

    for config in configs:
        exp = config["experiment"]

        if exp == "E0":
            continue

        if exp not in selected:
            continue

        print(f"\n{exp} — {config['description']}")

        result = train_experiment(
            config,
            features,
            residual_target,
            frozen,
            canonical_interp,
            truth,
            tau_end_days,
            xi,
            times_days,
            exact_front,
            displacement_guards,
        )

        results.append(result)

    # -------------------------------------------------------------------------
    # Tables
    # -------------------------------------------------------------------------

    metric_rows = []
    gate_rows = []
    epoch_rows = []

    for result in results:
        exp = result["experiment"]
        metrics = result["metrics"]

        if metrics is None:
            metric_rows.append({
                "experiment": exp,
                "description": result["description"],
                "best_epoch": -1,
                "complete_pass": False,
                "failure": "NO_PASSING_CHECKPOINT",
            })
            continue

        metric_rows.append({
            "experiment": exp,
            "description": result["description"],
            "best_epoch": result["best_epoch"],
            "best_score": result["best_score"],
            "runtime_seconds": result["runtime_seconds"],
            "complete_pass": result["complete_pass"],
            "global_L1": metrics["global_L1"],
            "global_L2": metrics["global_L2"],
            "recovered_fronts": metrics["front"]["recovered_fronts"],
            "conditioned_gap": metrics["front"]["conditioned_gap"],
            "profile_L1_100d": metrics["front"]["profile_L1_100d"],
            "mean_frozen_front_xi_shift": metrics["front"]["mean_frozen_front_xi_shift"],
            "P90_frozen_front_xi_shift": metrics["front"]["P90_frozen_front_xi_shift"],
            "front_error_reduction_fraction": metrics["safeguard"]["front_error_reduction_fraction"],
            "front_sign_agreement": metrics["safeguard"]["front_sign_agreement"],
            "front_overshoot_fraction": metrics["safeguard"]["front_overshoot_fraction"],
            "short_TOF_calibration_MAE": metrics["safeguard"]["short_TOF_calibration_MAE"],
            "global_abs_correction_MAX": metrics["safeguard"]["global_abs_correction_MAX"],
            "calibration_TV_ratio": metrics["safeguard"]["calibration_TV_ratio"],
            "bias_500_1000": metrics["tof"]["bias_500_1000"],
            "bias_1000_2000": metrics["tof"]["bias_1000_2000"],
            "bias_gt2000": metrics["tof"]["bias_gt2000"],
        })

        for gate, passed in metrics["gates"].items():
            gate_rows.append({
                "experiment": exp,
                "gate": gate,
                "passed": bool(passed),
            })

        for row in result["history"]:
            epoch_rows.append(row)

    save_csv(METRICS_FILE, metric_rows)
    save_csv(GATES_FILE, gate_rows)
    save_csv(EPOCH_FILE, epoch_rows)

    # -------------------------------------------------------------------------
    # Candidate selection
    # -------------------------------------------------------------------------

    passing = [
        result
        for result in results
        if result["experiment"] != "E0"
        and result["complete_pass"]
    ]

    print("\n" + "=" * 78)
    print("V15-SG7C-R3E FINAL CALIBRATION SCREEN")
    print("=" * 78)

    for result in results:
        if result["metrics"] is None:
            print(
                f"[FAIL] {result['experiment']} | no passing checkpoint"
            )
            continue

        m = result["metrics"]

        print(
            f"[{'PASS' if result['complete_pass'] else 'FAIL'}] "
            f"{result['experiment']} | "
            f"L1={m['global_L1']:.3e} | "
            f"fronts={m['front']['recovered_fronts']} | "
            f"gap={m['front']['conditioned_gap']:.3e} | "
            f"frontRed={100*m['safeguard']['front_error_reduction_fraction']:.1f}% | "
            f"shortCal={m['safeguard']['short_TOF_calibration_MAE']:.3e} | "
            f"B500={m['tof']['bias_500_1000']:.3e} | "
            f"B1000={m['tof']['bias_1000_2000']:.3e} | "
            f"B2000={m['tof']['bias_gt2000']:.3e}"
        )

    print("=" * 78)

    if passing:
        passing.sort(key=lambda item: item["best_score"])
        winner = passing[0]

        exp = winner["experiment"]
        source_model = (
            EXPERIMENT_DIR / exp
            / f"V15SG7CR3E_{exp}_Best_Calibrator.keras"
        )

        shutil.copy2(
            source_model,
            CANDIDATE_MODEL_FILE,
        )

        np.savez_compressed(
            CALIBRATED_DB_FILE,
            times_days=times_days,
            xi=xi,
            tau_end_days=tau_end_days,
            normalized_input=normalized_input,
            frozen_PI_RNN_saturation=frozen,
            canonical_interpolated_target=canonical_interp,
            SG7A_truth=truth,
            calibrated_PI_RNN_saturation=winner["calibrated"],
            calibration_deltaS=winner["delta"],
        )

        manifest = {
            "milestone": "V15-SG7C-R3E",
            "status": "FROZEN_MODEL_DEPLOYMENT_CALIBRATOR_NOMINATED",
            "experiment": exp,
            "candidate_model": str(CANDIDATE_MODEL_FILE),
            "SG7B11_modified": False,
            "candidate_is_frozen": False,
            "complete_R3E_contract_pass": True,
        }

        save_json(
            CANDIDATE_MANIFEST_FILE,
            manifest,
        )

        status = "FROZEN_MODEL_DEPLOYMENT_CALIBRATOR_NOMINATED"

        recommendation = (
            "A deployment-only residual calibrator satisfies the complete R3D-R "
            "front, directionality, overshoot, short-TOF, smoothness, and TOF-bias "
            "contract while SG7B-11 remains frozen. Do not map back yet. Proceed "
            "to an independent calibration validation before redeployment."
        )

        next_milestone = (
            "V15-SG7C-R3F — Independent Frozen-Model Calibration Validation"
        )

    else:
        winner = None

        status = "NO_R3E_CALIBRATOR_PASSES_COMPLETE_CONTRACT"

        recommendation = (
            "No controlled calibration experiment satisfies the complete contract. "
            "Do not relax the front or deployment safeguards. Audit the calibration "
            "failure modes before redesign."
        )

        next_milestone = (
            "V15-SG7C-R3E-R — Calibration Outcome / Gate-Failure Audit"
        )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    plot_rows = [
        row
        for row in metric_rows
        if "global_L1" in row
    ]

    if plot_rows:
        labels = [row["experiment"] for row in plot_rows]

        plt.figure(figsize=(9, 5))
        plt.bar(
            labels,
            [row["global_L1"] for row in plot_rows],
        )
        plt.ylabel("Global streamline L1")
        plt.xlabel("Experiment")
        plt.title("V15-SG7C-R3E Calibrated Streamline Accuracy")
        plt.tight_layout()
        plt.savefig(
            OUTPUT_DIR / "V15SG7CR3E_Global_L1.png",
            dpi=300,
        )
        plt.close()

        plt.figure(figsize=(9, 5))
        plt.bar(
            labels,
            [row["conditioned_gap"] for row in plot_rows],
        )
        plt.axhline(
            float(exact_front["maximum_conditioned_threshold_gap"]),
            linestyle="--",
        )
        plt.ylabel("Conditioned front gap")
        plt.xlabel("Experiment")
        plt.title("V15-SG7C-R3E Front-Gap Preservation")
        plt.tight_layout()
        plt.savefig(
            OUTPUT_DIR / "V15SG7CR3E_Front_Gap.png",
            dpi=300,
        )
        plt.close()

        plt.figure(figsize=(9, 5))
        plt.bar(
            labels,
            [row["bias_gt2000"] for row in plot_rows],
        )
        plt.axhline(5.0e-3, linestyle="--")
        plt.ylabel(">2000 d signed bias")
        plt.xlabel("Experiment")
        plt.title("V15-SG7C-R3E Very-Long-TOF Bias")
        plt.tight_layout()
        plt.savefig(
            OUTPUT_DIR / "V15SG7CR3E_VeryLong_TOF_Bias.png",
            dpi=300,
        )
        plt.close()

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------

    summary = {
        "milestone": "V15-SG7C-R3E",
        "status": status,
        "SG7B11_modified": False,
        "candidate_nominated": winner is not None,
        "candidate_experiment": (
            winner["experiment"] if winner is not None else None
        ),
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(
        SUMMARY_FILE,
        summary,
    )

    print("\nSTATUS")
    print(f"  {status}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")

    print("\nTables:")
    print(f"  {METRICS_FILE.name}")
    print(f"  {GATES_FILE.name}")
    print(f"  {EPOCH_FILE.name}")

    if winner is not None:
        print("\nCandidate:")
        print(f"  {CANDIDATE_MODEL_FILE.name}")
        print(f"  {CALIBRATED_DB_FILE.name}")
        print(f"  {CANDIDATE_MANIFEST_FILE.name}")

    print("\nDiagnostics:")
    print("  V15SG7CR3E_Global_L1.png")
    print("  V15SG7CR3E_Front_Gap.png")
    print("  V15SG7CR3E_VeryLong_TOF_Bias.png")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3E CONTROLLED CALIBRATION: COMPLETE")
    print()
    print("SG7B-11 remains frozen and authoritative.")
    print("No map-back, feature, target, or plume-validation gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
