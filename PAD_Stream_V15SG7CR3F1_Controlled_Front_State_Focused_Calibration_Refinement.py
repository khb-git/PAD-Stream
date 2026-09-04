from __future__ import annotations

from pathlib import Path
import argparse
import csv
import json
import time
import hashlib

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7C-R3F1
# Controlled Front-State-Focused Calibration Refinement
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
# IMPORTANT PERSISTENCE CONTRACT
# ------------------------------
# Unlike R3E, this milestone MUST persist:
#
#   * epoch metrics for every evaluated checkpoint,
#   * final metrics for every experiment,
#   * full gate matrix for every experiment,
#   * best-checkpoint metadata for every experiment,
#   * best calibrator file for every trainable experiment,
#   * candidate nomination manifest.
#
# Even failed experiments must be persisted for downstream independent audit.
# =============================================================================


ROOT = Path(__file__).resolve().parent

R3F0_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F0"
    / "PAD_Stream_V15SG7CR3F0_Summary.json"
)

R3F0_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F0"
    / "V15SG7CR3F0_Front_State_Refinement_Contract.json"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3F1"
EXPERIMENT_DIR = OUTPUT_DIR / "experiments"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

EPOCH_METRICS_FILE = OUTPUT_DIR / "V15SG7CR3F1_Epoch_Metrics.csv"
FINAL_METRICS_FILE = OUTPUT_DIR / "V15SG7CR3F1_Final_Experiment_Metrics.csv"
FINAL_GATES_FILE = OUTPUT_DIR / "V15SG7CR3F1_Final_Gate_Matrix.csv"
BEST_CHECKPOINT_FILE = OUTPUT_DIR / "V15SG7CR3F1_Best_Checkpoint_By_Experiment.csv"
CANDIDATE_MANIFEST_FILE = OUTPUT_DIR / "V15SG7CR3F1_Candidate_Manifest.json"
CANDIDATE_DB_FILE = OUTPUT_DIR / "V15SG7CR3F1_Candidate_Streamline_Deployment.npz"
SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG7CR3F1_Summary.json"

SEED = 15371
np.random.seed(SEED)
tf.random.set_seed(SEED)

FRONT_THRESHOLD = 0.210
FRONT_SHELL_LOW = 0.205
FRONT_SHELL_HIGH = 0.300
FRONT_CORE_LOW = 0.210
FRONT_CORE_HIGH = 0.260

LONG_TOF_MIN = 500.0

MAX_EPOCHS = 220
BATCH_SIZE = 4096
INITIAL_LR = 1.5e-3
MIN_LR = 1.0e-5
EVAL_EVERY = 5
EARLY_STOP_PATIENCE = 45


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def save_csv(path: Path, rows):
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


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def crossing_positions(field, xi, threshold):
    field = np.asarray(field, dtype=float)
    xi = np.asarray(xi, dtype=float)

    pos = np.full(field.shape[0], np.nan, dtype=float)
    ok = np.zeros(field.shape[0], dtype=bool)

    for i in range(field.shape[0]):
        y = field[i] - threshold
        idx = np.where(y[:-1] * y[1:] < 0.0)[0]

        if idx.size == 0:
            # Exact-threshold node fallback.
            exact = np.where(np.isclose(y, 0.0, atol=1e-10))[0]
            if exact.size:
                pos[i] = xi[int(exact[0])]
                ok[i] = True
            continue

        j = int(idx[0])
        denom = y[j + 1] - y[j]

        if abs(denom) <= 1e-14:
            pos[i] = 0.5 * (xi[j] + xi[j + 1])
        else:
            frac = float(np.clip(-y[j] / denom, 0.0, 1.0))
            pos[i] = xi[j] + frac * (xi[j + 1] - xi[j])

        ok[i] = True

    return pos, ok


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
    logtau = (logtau - np.mean(logtau)) / max(np.std(logtau), 1e-12)

    logtau3 = np.broadcast_to(
        logtau[None, :, None],
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
    )

    return features.astype(np.float32)


def build_model(config):
    inp = tf.keras.Input(shape=(5,), name="features")

    arch = config["architecture"]

    if arch == "mlp16":
        x = tf.keras.layers.Dense(16, activation="tanh")(inp)
        x = tf.keras.layers.Dense(16, activation="tanh")(x)
        raw = tf.keras.layers.Dense(
            1,
            activation=None,
            kernel_initializer="zeros",
            bias_initializer="zeros",
        )(x)

    elif arch == "mlp24":
        x = tf.keras.layers.Dense(24, activation="tanh")(inp)
        x = tf.keras.layers.Dense(24, activation="tanh")(x)
        raw = tf.keras.layers.Dense(
            1,
            activation=None,
            kernel_initializer="zeros",
            bias_initializer="zeros",
        )(x)

    elif arch == "mlp32":
        x = tf.keras.layers.Dense(32, activation="tanh")(inp)
        x = tf.keras.layers.Dense(32, activation="tanh")(x)
        raw = tf.keras.layers.Dense(
            1,
            activation=None,
            kernel_initializer="zeros",
            bias_initializer="zeros",
        )(x)

    elif arch == "dual24":
        shared = tf.keras.layers.Dense(24, activation="tanh")(inp)
        shared = tf.keras.layers.Dense(24, activation="tanh")(shared)

        global_head = tf.keras.layers.Dense(
            1,
            activation=None,
            kernel_initializer="zeros",
            bias_initializer="zeros",
            name="global_head",
        )(shared)

        front_head = tf.keras.layers.Dense(16, activation="tanh")(shared)
        front_head = tf.keras.layers.Dense(
            1,
            activation=None,
            kernel_initializer="zeros",
            bias_initializer="zeros",
            name="front_head",
        )(front_head)

        # Smooth front gating from front_distance feature.
        front_distance = inp[:, 4:5]
        gate = tf.keras.layers.Lambda(
            lambda z: tf.exp(-tf.square(z / 0.06)),
            name="front_gate",
        )(front_distance)

        raw = global_head + gate * front_head

    else:
        raise ValueError(f"Unknown architecture: {arch}")

    out = tf.keras.layers.Lambda(
        lambda z: 0.10 * tf.tanh(z / 0.10),
        name="bounded_deltaS",
    )(raw)

    return tf.keras.Model(inp, out, name=config["experiment"])


def experiment_configs():
    return [
        {
            "experiment": "F0",
            "description": "R3E-style capacity control",
            "architecture": "mlp16",
            "front_weight": 6.0,
            "core_weight": 6.0,
            "short_weight": 3.0,
            "direction_weight": 1.5,
        },
        {
            "experiment": "F1",
            "description": "Moderate front-state capacity",
            "architecture": "mlp24",
            "front_weight": 10.0,
            "core_weight": 12.0,
            "short_weight": 3.0,
            "direction_weight": 2.0,
        },
        {
            "experiment": "F2",
            "description": "Strong front-state capacity",
            "architecture": "mlp32",
            "front_weight": 14.0,
            "core_weight": 16.0,
            "short_weight": 3.5,
            "direction_weight": 2.5,
        },
        {
            "experiment": "F3",
            "description": "Dual-head front/nonfront residual calibrator",
            "architecture": "dual24",
            "front_weight": 12.0,
            "core_weight": 16.0,
            "short_weight": 3.5,
            "direction_weight": 2.0,
        },
        {
            "experiment": "F4",
            "description": "Dual-head strongest front-state specialization",
            "architecture": "dual24",
            "front_weight": 16.0,
            "core_weight": 20.0,
            "short_weight": 4.0,
            "direction_weight": 3.0,
        },
    ]


def evaluate(
    calibrated,
    frozen,
    target,
    truth,
    tau_end_days,
    xi,
    times_days,
    contract,
):
    idx100 = int(np.argmin(np.abs(times_days - 100.0)))

    pred100 = calibrated[idx100]
    frozen100 = frozen[idx100]
    truth100 = truth[idx100]
    target100 = target[idx100]

    shell = (
        (truth100 >= FRONT_SHELL_LOW)
        &
        (truth100 <= FRONT_SHELL_HIGH)
    )

    frozen_shell_l1 = float(
        np.mean(np.abs(frozen100[shell] - truth100[shell]))
    )

    calibrated_shell_l1 = float(
        np.mean(np.abs(pred100[shell] - truth100[shell]))
    )

    front_error_reduction = (
        1.0
        -
        calibrated_shell_l1
        /
        max(frozen_shell_l1, 1e-15)
    )

    pred_pos, pred_ok = crossing_positions(pred100, xi, FRONT_THRESHOLD)
    truth_pos, truth_ok = crossing_positions(truth100, xi, FRONT_THRESHOLD)
    frozen_pos, frozen_ok = crossing_positions(frozen100, xi, FRONT_THRESHOLD)

    recovered = int(np.sum(pred_ok & truth_ok))
    truth_fronts = int(np.sum(truth_ok))

    gaps = np.min(np.abs(pred100 - FRONT_THRESHOLD), axis=1)
    conditioned_gap = float(np.mean(gaps[truth_ok])) if np.any(truth_ok) else np.inf

    profile_l1_100d = float(np.mean(np.abs(pred100 - truth100)))

    common = pred_ok & frozen_ok & truth_ok

    if np.any(common):
        shifts = np.abs(pred_pos[common] - frozen_pos[common])
        mean_shift = float(np.mean(shifts))
        p90_shift = float(np.percentile(shifts, 90))
    else:
        mean_shift = np.inf
        p90_shift = np.inf

    delta = calibrated - frozen
    required = target - frozen

    applied_shell = delta[idx100][shell]
    required_shell = required[idx100][shell]

    sign_agreement = float(
        np.mean(applied_shell * required_shell >= -1e-12)
    )

    overshoot = np.abs(applied_shell) > (
        np.abs(required_shell) + 1e-6
    )

    overshoot_fraction = float(np.mean(overshoot))

    short = tau_end_days < LONG_TOF_MIN

    short_cal_mae = float(
        np.mean(np.abs(delta[:, short, :]))
    )

    global_abs_corr = float(
        np.max(np.abs(delta))
    )

    tv_delta = float(
        np.mean(
            np.sum(
                np.abs(np.diff(delta, axis=2)),
                axis=2,
            )
        )
    )

    tv_frozen = float(
        np.mean(
            np.sum(
                np.abs(np.diff(frozen, axis=2)),
                axis=2,
            )
        )
    )

    tv_ratio = tv_delta / max(tv_frozen, 1e-12)

    err = calibrated - truth

    def band_bias(lo, hi):
        mask = (
            (tau_end_days >= lo)
            &
            (tau_end_days < hi)
        )
        vals = err[:, mask, :]
        return float(np.mean(vals)) if np.any(mask) else np.nan

    b500 = band_bias(500.0, 1000.0)
    b1000 = band_bias(1000.0, 2000.0)
    b2000 = band_bias(2000.0, np.inf)

    global_l1 = float(np.mean(np.abs(err)))
    global_l2 = float(np.sqrt(np.mean(err**2)))

    exact_front = contract["preservation_gates"]

    # Pull numeric gates by known contract semantics.
    auth = load_json(R3F0_CONTRACT)
    authoritative_front = auth["preservation_gates"]

    # Fixed limits retained from previous milestones.
    min_fronts = 744
    max_gap = 5.33123727917913484e-04
    max_profile_l1 = 4.50032942291447424e-03
    max_mean_shift = 2.0e-03
    max_p90_shift = 5.0e-03

    gates = {
        "front_error_reduction": front_error_reduction >= 0.50,
        "recovered_fronts": recovered >= min_fronts,
        "conditioned_front_gap": conditioned_gap <= max_gap,
        "100d_profile_L1": profile_l1_100d <= max_profile_l1,
        "mean_frozen_front_xi_shift": mean_shift <= max_mean_shift,
        "P90_frozen_front_xi_shift": p90_shift <= max_p90_shift,
        "front_sign_agreement": sign_agreement >= 0.95,
        "front_overshoot_fraction": overshoot_fraction <= 0.05,
        "short_TOF_calibration_MAE": short_cal_mae <= 1.5e-3,
        "global_abs_correction": global_abs_corr <= 0.10,
        "calibration_TV_ratio": tv_ratio <= 0.20,
        "bias_500_1000": abs(b500) <= 2.5e-3,
        "bias_1000_2000": abs(b1000) <= 4.5e-3,
        "bias_gt2000": abs(b2000) <= 5.0e-3,
    }

    return {
        "global_L1": global_l1,
        "global_L2": global_l2,
        "front_error_reduction_fraction": front_error_reduction,
        "frozen_front_shell_L1": frozen_shell_l1,
        "calibrated_front_shell_L1": calibrated_shell_l1,
        "recovered_fronts": recovered,
        "truth_fronts": truth_fronts,
        "conditioned_gap": conditioned_gap,
        "profile_L1_100d": profile_l1_100d,
        "mean_frozen_front_xi_shift": mean_shift,
        "P90_frozen_front_xi_shift": p90_shift,
        "front_sign_agreement": sign_agreement,
        "front_overshoot_fraction": overshoot_fraction,
        "short_TOF_calibration_MAE": short_cal_mae,
        "global_abs_correction_MAX": global_abs_corr,
        "calibration_TV_ratio": tv_ratio,
        "bias_500_1000": b500,
        "bias_1000_2000": b1000,
        "bias_gt2000": b2000,
        "gates": gates,
        "complete_pass": bool(all(gates.values())),
    }


def score(metrics):
    return float(
        metrics["global_L1"]
        + 2.0 * max(0.0, 0.50 - metrics["front_error_reduction_fraction"])
        + 2.0 * metrics["conditioned_gap"]
        + 0.5 * metrics["profile_L1_100d"]
        + 0.25 * abs(metrics["bias_500_1000"])
        + 0.25 * abs(metrics["bias_1000_2000"])
        + 0.25 * abs(metrics["bias_gt2000"])
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
    contract,
):
    exp = config["experiment"]
    exp_dir = EXPERIMENT_DIR / exp
    exp_dir.mkdir(parents=True, exist_ok=True)

    model = build_model(config)

    X = features.reshape(-1, 5).astype(np.float32)
    y = residual_target.reshape(-1, 1).astype(np.float32)

    nt, ns, nx = frozen.shape

    truth_flat = truth.reshape(-1)
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

    sample_weight = (
        1.0
        + config["front_weight"] * shell
        + config["core_weight"] * core
    ).astype(np.float32)

    ds = tf.data.Dataset.from_tensor_slices(
        (
            X,
            y,
            sample_weight[:, None],
            shell[:, None],
            core[:, None],
            short[:, None],
        )
    ).shuffle(
        min(len(X), 500000),
        seed=SEED + int(exp[1:]),
        reshuffle_each_iteration=True,
    ).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

    optimizer = tf.keras.optimizers.Adam(INITIAL_LR)

    @tf.function
    def train_step(xb, yb, wb, shellb, coreb, shortb):

        with tf.GradientTape() as tape:

            pred = model(xb, training=True)

            residual_loss = tf.reduce_sum(
                wb * tf.abs(pred - yb)
            ) / (
                tf.reduce_sum(wb) + 1e-8
            )

            shell_loss = tf.reduce_sum(
                shellb * tf.abs(pred - yb)
            ) / (
                tf.reduce_sum(shellb) + 1e-8
            )

            core_loss = tf.reduce_sum(
                coreb * tf.abs(pred - yb)
            ) / (
                tf.reduce_sum(coreb) + 1e-8
            )

            short_anchor = tf.reduce_sum(
                shortb * tf.abs(pred)
            ) / (
                tf.reduce_sum(shortb) + 1e-8
            )

            direction_penalty = tf.reduce_mean(
                tf.nn.relu(
                    -(pred * yb)
                )
            )

            total = (
                residual_loss
                + config["front_weight"] * shell_loss
                + config["core_weight"] * core_loss
                + config["short_weight"] * short_anchor
                + config["direction_weight"] * direction_penalty
            )

        grads = tape.gradient(
            total,
            model.trainable_variables,
        )

        grads, _ = tf.clip_by_global_norm(
            grads,
            5.0,
        )

        optimizer.apply_gradients(
            zip(grads, model.trainable_variables)
        )

        return total

    epoch_rows = []

    best_score = np.inf
    best_epoch = None
    best_weights = None
    best_metrics = None

    best_any_score = np.inf
    best_any_epoch = None
    best_any_weights = None
    best_any_metrics = None

    patience = 0
    lr = INITIAL_LR

    start = time.perf_counter()

    for epoch in range(1, MAX_EPOCHS + 1):

        for batch in ds:
            train_step(*batch)

        if (
            epoch == 1
            or
            epoch % EVAL_EVERY == 0
        ):

            delta = model.predict(
                X,
                batch_size=8192,
                verbose=0,
            ).reshape(frozen.shape)

            calibrated = frozen + delta

            metrics = evaluate(
                calibrated,
                frozen,
                target,
                truth,
                tau_end_days,
                xi,
                times_days,
                contract,
            )

            sc = score(metrics)

            row = {
                "experiment": exp,
                "epoch": epoch,
                "score": sc,
                **{
                    k: v
                    for k, v in metrics.items()
                    if k not in {"gates", "complete_pass"}
                },
                "complete_pass": metrics["complete_pass"],
                "failed_gates": ";".join(
                    [
                        gate
                        for gate, passed
                        in metrics["gates"].items()
                        if not passed
                    ]
                ),
            }

            epoch_rows.append(row)

            print(
                f"  {exp} epoch={epoch:3d} | "
                f"L1={metrics['global_L1']:.3e} | "
                f"frontRed={100*metrics['front_error_reduction_fraction']:.1f}% | "
                f"fronts={metrics['recovered_fronts']:4d} | "
                f"gap={metrics['conditioned_gap']:.3e} | "
                f"short={metrics['short_TOF_calibration_MAE']:.3e} | "
                f"B500={metrics['bias_500_1000']:.3e} | "
                f"{'PASS' if metrics['complete_pass'] else 'FAIL'}"
            )

            # Always persist best-any checkpoint for audit.
            if sc < best_any_score:
                best_any_score = sc
                best_any_epoch = epoch
                best_any_weights = model.get_weights()
                best_any_metrics = metrics

            # Separately track passing checkpoint.
            if metrics["complete_pass"] and sc < best_score:
                best_score = sc
                best_epoch = epoch
                best_weights = model.get_weights()
                best_metrics = metrics
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

    # Persist best-any checkpoint regardless of pass/fail.
    if best_any_weights is None:
        raise RuntimeError(
            f"{exp}: no evaluable checkpoint was produced."
        )

    model.set_weights(best_any_weights)

    best_any_path = (
        exp_dir
        / f"V15SG7CR3F1_{exp}_Best_Any_Calibrator.keras"
    )

    model.save(best_any_path)

    # Also persist best passing model if available.
    passing_path = None

    if best_weights is not None:
        model.set_weights(best_weights)

        passing_path = (
            exp_dir
            / f"V15SG7CR3F1_{exp}_Best_Passing_Calibrator.keras"
        )

        model.save(passing_path)

    # Restore best-any for downstream experiment summary.
    model.set_weights(best_any_weights)

    delta_any = model.predict(
        X,
        batch_size=8192,
        verbose=0,
    ).reshape(frozen.shape)

    calibrated_any = frozen + delta_any

    return {
        "experiment": exp,
        "description": config["description"],
        "best_any_epoch": best_any_epoch,
        "best_any_score": best_any_score,
        "best_any_metrics": best_any_metrics,
        "best_any_path": str(best_any_path),
        "best_any_sha256": sha256_file(best_any_path),
        "best_passing_epoch": best_epoch,
        "best_passing_score": best_score if best_epoch is not None else None,
        "best_passing_metrics": best_metrics,
        "best_passing_path": str(passing_path) if passing_path else None,
        "best_passing_sha256": sha256_file(passing_path) if passing_path else None,
        "epoch_rows": epoch_rows,
        "runtime_seconds": runtime,
        "calibrated_any": calibrated_any,
        "delta_any": delta_any,
    }


def main():

    parser = argparse.ArgumentParser(
        description="PAD-Stream V15-SG7C-R3F1 controlled front-state-focused calibrator refinement."
    )

    parser.add_argument(
        "--experiments",
        type=str,
        default="F0,F1,F2,F3,F4",
        help="Comma-separated experiments to run.",
    )

    args = parser.parse_args()

    selected = {
        item.strip()
        for item in args.experiments.split(",")
        if item.strip()
    }

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F1")
    print("Controlled Front-State-Focused Calibration Refinement")
    print("=" * 78)

    print("\nCALIBRATOR TRAINING WILL BE PERFORMED.")
    print("SG7B-11 PI-RNN WEIGHTS WILL NOT BE CHANGED.")
    print("NO FRONT OR TOF-BIAS GATE WILL BE RELAXED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")
    print("ALL EXPERIMENT CHECKPOINT METRICS WILL BE PERSISTED.")

    for path in [
        R3F0_SUMMARY,
        R3F0_CONTRACT,
        R3C_NUMERICAL,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing R3F1 prerequisite:\n{path}"
            )

    r3f0_summary = load_json(R3F0_SUMMARY)
    r3f0_contract = load_json(R3F0_CONTRACT)

    if r3f0_summary.get("status") != "FRONT_STATE_REFINEMENT_CONTRACT_READY":
        raise RuntimeError(
            "R3F1 requires R3F0 ready contract status."
        )

    db = np.load(
        R3C_NUMERICAL,
        allow_pickle=True,
    )

    frozen = np.asarray(
        db["deployment_pirnn"],
        dtype=float,
    )

    truth = np.asarray(
        db["deployment_truth"],
        dtype=float,
    )

    target = np.asarray(
        db["canonical_interpolated_target"],
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

    normalized_tD = np.asarray(
        db["deployment_normalized_input"],
        dtype=float,
    )

    xi = np.asarray(
        db["canonical_xi"],
        dtype=float,
    )

    residual_target = target - frozen

    features = make_features(
        xi,
        normalized_tD,
        tau_end_days,
        frozen,
    )

    configs = [
        c
        for c in experiment_configs()
        if c["experiment"] in selected
    ]

    all_epoch_rows = []
    final_rows = []
    gate_rows = []
    checkpoint_rows = []
    results = []

    print("\n" + "=" * 78)
    print("R3F1 CONTROLLED EXPERIMENTS")
    print("=" * 78)

    for config in configs:

        exp = config["experiment"]

        print(
            f"\n{exp} — {config['description']}"
        )

        result = train_experiment(
            config,
            features,
            residual_target,
            frozen,
            target,
            truth,
            tau_end_days,
            xi,
            times_days,
            r3f0_contract,
        )

        results.append(result)
        all_epoch_rows.extend(
            result["epoch_rows"]
        )

        m = result["best_any_metrics"]

        final_rows.append({
            "experiment": exp,
            "description": result["description"],
            "runtime_seconds": result["runtime_seconds"],
            "best_any_epoch": result["best_any_epoch"],
            "best_any_score": result["best_any_score"],
            "best_any_complete_pass": m["complete_pass"],
            **{
                k: v
                for k, v in m.items()
                if k not in {"gates", "complete_pass"}
            },
            "best_passing_epoch": (
                result["best_passing_epoch"]
                if result["best_passing_epoch"] is not None
                else ""
            ),
            "best_passing_score": (
                result["best_passing_score"]
                if result["best_passing_score"] is not None
                else ""
            ),
        })

        for gate, passed in m["gates"].items():
            gate_rows.append({
                "experiment": exp,
                "checkpoint_type": "best_any",
                "gate": gate,
                "passed": bool(passed),
            })

        checkpoint_rows.append({
            "experiment": exp,
            "checkpoint_type": "best_any",
            "epoch": result["best_any_epoch"],
            "path": result["best_any_path"],
            "sha256": result["best_any_sha256"],
            "complete_pass": bool(m["complete_pass"]),
        })

        if result["best_passing_epoch"] is not None:

            mp = result["best_passing_metrics"]

            for gate, passed in mp["gates"].items():
                gate_rows.append({
                    "experiment": exp,
                    "checkpoint_type": "best_passing",
                    "gate": gate,
                    "passed": bool(passed),
                })

            checkpoint_rows.append({
                "experiment": exp,
                "checkpoint_type": "best_passing",
                "epoch": result["best_passing_epoch"],
                "path": result["best_passing_path"],
                "sha256": result["best_passing_sha256"],
                "complete_pass": True,
            })

    save_csv(
        EPOCH_METRICS_FILE,
        all_epoch_rows,
    )

    save_csv(
        FINAL_METRICS_FILE,
        final_rows,
    )

    save_csv(
        FINAL_GATES_FILE,
        gate_rows,
    )

    save_csv(
        BEST_CHECKPOINT_FILE,
        checkpoint_rows,
    )

    # -------------------------------------------------------------------------
    # Nomination
    # -------------------------------------------------------------------------

    passing = [
        result
        for result in results
        if result["best_passing_epoch"] is not None
    ]

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F1 FINAL SCREEN")
    print("=" * 78)

    for row in final_rows:
        print(
            f"[{'PASS' if row['best_any_complete_pass'] else 'FAIL'}] "
            f"{row['experiment']} | "
            f"frontRed={100*row['front_error_reduction_fraction']:.1f}% | "
            f"fronts={int(row['recovered_fronts'])} | "
            f"gap={row['conditioned_gap']:.3e} | "
            f"L1={row['global_L1']:.3e} | "
            f"B500={row['bias_500_1000']:.3e}"
        )

    print("=" * 78)

    candidate = None

    if passing:

        passing.sort(
            key=lambda result:
            result["best_passing_score"]
        )

        candidate = passing[0]

        status = "FRONT_STATE_FOCUSED_CALIBRATOR_NOMINATED"

        recommendation = (
            "A front-state-focused deployment calibrator satisfies the complete "
            "R3F0 preservation contract while SG7B-11 remains frozen. Proceed to "
            "independent validation before any final redeployment or map-back."
        )

        next_milestone = (
            "V15-SG7C-R3F2 — Independent Front-State Calibrator Validation"
        )

        # Save candidate deployment based on passing model.
        candidate_model = tf.keras.models.load_model(
            candidate["best_passing_path"],
            compile=False,
        )

        X = features.reshape(-1, 5)

        delta = candidate_model.predict(
            X,
            batch_size=8192,
            verbose=0,
        ).reshape(frozen.shape)

        calibrated = frozen + delta

        np.savez_compressed(
            CANDIDATE_DB_FILE,
            times_days=times_days,
            xi=xi,
            tau_end_days=tau_end_days,
            normalized_tD=normalized_tD,
            frozen_PI_RNN_saturation=frozen,
            canonical_target=target,
            SG7A_truth=truth,
            calibrated_PI_RNN_saturation=calibrated,
            calibration_deltaS=delta,
        )

        manifest = {
            "milestone": "V15-SG7C-R3F1",
            "status": status,
            "candidate_experiment": candidate["experiment"],
            "candidate_epoch": candidate["best_passing_epoch"],
            "candidate_model_path": candidate["best_passing_path"],
            "candidate_sha256": candidate["best_passing_sha256"],
            "candidate_is_frozen": False,
            "SG7B11_modified": False,
            "next_milestone": next_milestone,
        }

    else:

        status = "NO_R3F1_CALIBRATOR_PASSES_COMPLETE_CONTRACT"

        recommendation = (
            "No front-state-focused calibrator satisfies the complete contract. "
            "Use the now-complete checkpoint persistence to diagnose the exact "
            "remaining limiter without repeating the R3E evidence gap."
        )

        next_milestone = (
            "V15-SG7C-R3F1-R — Front-State Refinement Outcome Audit"
        )

        manifest = {
            "milestone": "V15-SG7C-R3F1",
            "status": status,
            "candidate_experiment": None,
            "candidate_is_frozen": False,
            "SG7B11_modified": False,
            "next_milestone": next_milestone,
        }

    save_json(
        CANDIDATE_MANIFEST_FILE,
        manifest,
    )

    summary = {
        "milestone": "V15-SG7C-R3F1",
        "status": status,
        "training_performed": True,
        "SG7B11_modified": False,
        "experiments_run": [
            result["experiment"]
            for result in results
        ],
        "candidate_nominated": candidate is not None,
        "candidate_experiment": (
            candidate["experiment"]
            if candidate is not None
            else None
        ),
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(
        SUMMARY_FILE,
        summary,
    )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    if final_rows:

        labels = [
            row["experiment"]
            for row in final_rows
        ]

        plt.figure(figsize=(9, 5))
        plt.bar(
            labels,
            [
                row["front_error_reduction_fraction"]
                for row in final_rows
            ],
        )
        plt.axhline(
            0.50,
            linestyle="--",
        )
        plt.ylabel(
            "Front-shell error reduction fraction"
        )
        plt.xlabel(
            "Experiment"
        )
        plt.title(
            "V15-SG7C-R3F1 Front-State Error Reduction"
        )
        plt.tight_layout()
        plt.savefig(
            OUTPUT_DIR / "V15SG7CR3F1_Front_Error_Reduction.png",
            dpi=300,
        )
        plt.close()

        plt.figure(figsize=(9, 5))
        plt.bar(
            labels,
            [
                row["conditioned_gap"]
                for row in final_rows
            ],
        )
        plt.axhline(
            5.33123727917913484e-04,
            linestyle="--",
        )
        plt.ylabel(
            "Conditioned front gap"
        )
        plt.xlabel(
            "Experiment"
        )
        plt.title(
            "V15-SG7C-R3F1 Front-Gap Preservation"
        )
        plt.tight_layout()
        plt.savefig(
            OUTPUT_DIR / "V15SG7CR3F1_Front_Gap.png",
            dpi=300,
        )
        plt.close()

    print("\nSTATUS")
    print(f"  {status}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")

    print("\nTables:")
    print(f"  {EPOCH_METRICS_FILE.name}")
    print(f"  {FINAL_METRICS_FILE.name}")
    print(f"  {FINAL_GATES_FILE.name}")
    print(f"  {BEST_CHECKPOINT_FILE.name}")

    print("\nManifest:")
    print(f"  {CANDIDATE_MANIFEST_FILE.name}")

    if candidate is not None:
        print("\nCandidate deployment:")
        print(f"  {CANDIDATE_DB_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F1 CONTROLLED REFINEMENT: COMPLETE")
    print()
    print("SG7B-11 remains frozen and authoritative.")
    print("All evaluated experiment/checkpoint metrics were persisted.")
    print("No front, TOF-bias, map-back, or plume-validation gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
