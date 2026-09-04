from __future__ import annotations

from pathlib import Path
import argparse
import csv
import json
import hashlib
import time

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7C-R3F4
# Controlled Front-Local Residual Basis Calibration
#
# TRAINING MILESTONE — BOUNDED DEPLOYMENT CALIBRATOR ONLY
#
# SG7B-11 REMAINS FROZEN.
# NO PI-RNN WEIGHTS ARE CHANGED.
# NO PI-RNN ARCHITECTURE CHANGE.
# NO SG6 STREAMLINE GEOMETRY CHANGE.
# NO FEATURE / TARGET CONVENTION CHANGE.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
# NO PRESERVATION GATE RELAXATION.
#
# CORE R3F3 CONTRACT
# ------------------
#
#   deltaS_local =
#       alpha(features)
#       * (S_canonical - S_frozen)
#       * G(xi - xi_front)
#
# with 0 <= alpha <= 1.
#
# R3F4 therefore learns only bounded residual FRACTIONS.
# It does NOT learn an unconstrained additive saturation correction.
#
# The front-local basis directly inherits:
#
#   * correction sign from the validated canonical residual,
#   * bounded amplitude from alpha <= 1,
#   * compact support from G,
#   * explicit crossing / width / gradient safeguards.
#
# FULL PERSISTENCE IS MANDATORY.
# =============================================================================


ROOT = Path(__file__).resolve().parent

R3F3_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F3"
    / "PAD_Stream_V15SG7CR3F3_Summary.json"
)

R3F3_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F3"
    / "V15SG7CR3F3_Front_Local_Residual_Basis_Contract.json"
)

R3C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3C"
    / "V15SG7CR3C_Feature_Target_Audit.npz"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3F4"
EXPERIMENT_DIR = OUTPUT_DIR / "experiments"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

EPOCH_METRICS_FILE = OUTPUT_DIR / "V15SG7CR3F4_Epoch_Metrics.csv"
FINAL_METRICS_FILE = OUTPUT_DIR / "V15SG7CR3F4_Final_Experiment_Metrics.csv"
FINAL_GATES_FILE = OUTPUT_DIR / "V15SG7CR3F4_Final_Gate_Matrix.csv"
BEST_CHECKPOINT_FILE = OUTPUT_DIR / "V15SG7CR3F4_Best_Checkpoint_By_Experiment.csv"
CANDIDATE_MANIFEST_FILE = OUTPUT_DIR / "V15SG7CR3F4_Candidate_Manifest.json"
CANDIDATE_DB_FILE = OUTPUT_DIR / "V15SG7CR3F4_Candidate_Streamline_Deployment.npz"
SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG7CR3F4_Summary.json"


# =============================================================================
# FIXED AUTHORITATIVE LIMITS
# =============================================================================

SEED = 15441
np.random.seed(SEED)
tf.random.set_seed(SEED)

FRONT_THRESHOLD = 0.210
FRONT_SHELL_LOW = 0.205
FRONT_SHELL_HIGH = 0.300

MIN_RECOVERED_FRONTS = 744
MAX_CONDITIONED_GAP = 5.33123727917913484e-04
MAX_PROFILE_L1 = 4.50032942291447424e-03
MIN_FRONT_ERROR_REDUCTION = 0.50

MAX_MEAN_FRONT_XI_SHIFT = 2.0e-03
MAX_P90_FRONT_XI_SHIFT = 5.0e-03

MIN_SIGN_AGREEMENT = 0.95
MAX_OVERSHOOT = 0.05
MAX_SHORT_TOF_CAL_MAE = 1.5e-03
MAX_GLOBAL_CORRECTION = 0.10
MAX_CALIBRATION_TV_RATIO = 0.20

MAX_BIAS_500_1000 = 2.5e-03
MAX_BIAS_1000_2000 = 4.5e-03
MAX_BIAS_GT2000 = 5.0e-03

SIGMA_NARROW = 0.015
SIGMA_MEDIUM = 0.030
COSINE_HALF_WIDTH = 0.030

MAX_EPOCHS = 220
BATCH_SIZE = 8192
INITIAL_LR = 1.0e-3
MIN_LR = 1.0e-5
EVAL_EVERY = 5
EARLY_STOP_PATIENCE = 50


# =============================================================================
# IO
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_csv(path: Path, rows):
    if not rows:
        return

    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
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


# =============================================================================
# FRONT GEOMETRY
# =============================================================================

def first_crossing(profile, xi, threshold):
    y = np.asarray(profile, dtype=float) - threshold

    idx = np.where(y[:-1] * y[1:] < 0.0)[0]

    if idx.size == 0:
        exact = np.where(np.isclose(y, 0.0, atol=1e-10))[0]
        if exact.size:
            return float(xi[int(exact[0])]), True
        return np.nan, False

    j = int(idx[0])

    denom = y[j + 1] - y[j]

    if abs(denom) <= 1e-14:
        return float(0.5 * (xi[j] + xi[j + 1])), True

    frac = float(np.clip(-y[j] / denom, 0.0, 1.0))

    return float(
        xi[j] + frac * (xi[j + 1] - xi[j])
    ), True


def crossing_arrays(field, xi, threshold):
    pos = np.full(field.shape[0], np.nan, dtype=float)
    ok = np.zeros(field.shape[0], dtype=bool)

    for i in range(field.shape[0]):
        pos[i], ok[i] = first_crossing(
            field[i],
            xi,
            threshold,
        )

    return pos, ok


def front_position_database(target, xi):
    nt, ns, _ = target.shape

    pos = np.full((nt, ns), np.nan, dtype=float)
    ok = np.zeros((nt, ns), dtype=bool)

    for it in range(nt):
        p, m = crossing_arrays(
            target[it],
            xi,
            FRONT_THRESHOLD,
        )

        pos[it] = p
        ok[it] = m

    return pos, ok


# =============================================================================
# BASIS FUNCTIONS
# =============================================================================

def gaussian(distance, sigma):
    return np.exp(
        -0.5 * (distance / sigma) ** 2
    )


def raised_cosine(distance, half_width):
    out = np.zeros_like(distance, dtype=float)

    mask = np.abs(distance) <= half_width

    out[mask] = 0.5 * (
        1.0
        +
        np.cos(
            np.pi
            * distance[mask]
            / half_width
        )
    )

    return out


def make_basis_fields(target, xi):
    """
    Construct canonical-front-local basis fields for all deployment times.

    Profiles without a canonical front receive zero basis support.
    """
    nt, ns, nx = target.shape

    front_pos, front_ok = front_position_database(
        target,
        xi,
    )

    distance = np.zeros(
        (nt, ns, nx),
        dtype=float,
    )

    for it in range(nt):
        distance[it] = (
            xi[None, :]
            -
            front_pos[it, :, None]
        )

    # Invalid profiles are zeroed after basis evaluation.
    g1 = gaussian(
        distance,
        SIGMA_NARROW,
    )

    g2 = gaussian(
        distance,
        SIGMA_MEDIUM,
    )

    g3 = raised_cosine(
        distance,
        COSINE_HALF_WIDTH,
    )

    valid3 = front_ok[:, :, None]

    g1 = np.where(valid3, g1, 0.0)
    g2 = np.where(valid3, g2, 0.0)
    g3 = np.where(valid3, g3, 0.0)

    return {
        "front_pos": front_pos,
        "front_ok": front_ok,
        "g1": g1.astype(np.float32),
        "g2": g2.astype(np.float32),
        "g3": g3.astype(np.float32),
    }


# =============================================================================
# AMPLITUDE MODEL
# =============================================================================

def make_profile_features(normalized_tD, tau_end_days):
    """
    Learn profile-level alpha, not node-level alpha.

    This is deliberate: alpha is constant along a given streamline profile
    at a given physical time, and only the front-local basis varies with xi.
    That prevents arbitrary node-by-node geometry manipulation.
    """
    logtau = np.log10(
        np.maximum(
            tau_end_days,
            1.0,
        )
    )

    logtau = (
        logtau - np.mean(logtau)
    ) / max(np.std(logtau), 1e-12)

    nt, ns = normalized_tD.shape

    logtau2 = np.broadcast_to(
        logtau[None, :],
        (nt, ns),
    )

    features = np.stack(
        [
            normalized_tD,
            logtau2,
        ],
        axis=-1,
    )

    return features.astype(np.float32)


def build_alpha_model(experiment):
    """
    Models contain no Lambda layers, avoiding the checkpoint-deserialization
    issue encountered in R3F2A.
    """
    inp = tf.keras.Input(
        shape=(2,),
        name="profile_features",
    )

    x = tf.keras.layers.Dense(
        12,
        activation="tanh",
    )(inp)

    x = tf.keras.layers.Dense(
        12,
        activation="tanh",
    )(x)

    if experiment in {"B1", "B2", "B3"}:
        out = tf.keras.layers.Dense(
            1,
            activation="sigmoid",
            name="alpha",
        )(x)

    elif experiment in {"B4", "B5"}:
        # Three-way softmax:
        #   w1, w2 = two basis amplitudes,
        #   w0 = unused residual fraction.
        #
        # Thus w1+w2 <= 1 automatically.
        out = tf.keras.layers.Dense(
            3,
            activation="softmax",
            name="basis_weights",
        )(x)

    else:
        raise ValueError(
            f"Unknown trainable experiment: {experiment}"
        )

    return tf.keras.Model(
        inp,
        out,
        name=f"R3F4_{experiment}",
    )


# =============================================================================
# CALIBRATED FIELD CONSTRUCTION
# =============================================================================

def reconstruct_delta(
    experiment,
    model,
    profile_features,
    residual,
    basis,
):
    nt, ns, nx = residual.shape

    raw = model.predict(
        profile_features.reshape(-1, 2),
        batch_size=8192,
        verbose=0,
    )

    if experiment == "B1":
        alpha = raw[:, 0].reshape(nt, ns)
        coefficient = alpha[:, :, None] * basis["g1"]

    elif experiment == "B2":
        alpha = raw[:, 0].reshape(nt, ns)
        coefficient = alpha[:, :, None] * basis["g2"]

    elif experiment == "B3":
        alpha = raw[:, 0].reshape(nt, ns)
        coefficient = alpha[:, :, None] * basis["g3"]

    elif experiment in {"B4", "B5"}:
        weights = raw.reshape(nt, ns, 3)

        w1 = weights[:, :, 0]
        w2 = weights[:, :, 1]

        coefficient = (
            w1[:, :, None] * basis["g1"]
            +
            w2[:, :, None] * basis["g2"]
        )

    else:
        raise ValueError(experiment)

    coefficient = np.clip(
        coefficient,
        0.0,
        1.0,
    )

    delta = coefficient * residual

    return (
        delta.astype(float),
        coefficient.astype(float),
    )


# =============================================================================
# VALIDATION METRICS
# =============================================================================

def evaluate(
    calibrated,
    frozen,
    target,
    truth,
    tau_end_days,
    xi,
    times_days,
):
    idx100 = int(
        np.argmin(
            np.abs(times_days - 100.0)
        )
    )

    pred100 = calibrated[idx100]
    frozen100 = frozen[idx100]
    target100 = target[idx100]
    truth100 = truth[idx100]

    shell = (
        (truth100 >= FRONT_SHELL_LOW)
        &
        (truth100 <= FRONT_SHELL_HIGH)
    )

    frozen_shell_l1 = float(
        np.mean(
            np.abs(
                frozen100[shell]
                -
                truth100[shell]
            )
        )
    )

    calibrated_shell_l1 = float(
        np.mean(
            np.abs(
                pred100[shell]
                -
                truth100[shell]
            )
        )
    )

    front_error_reduction = float(
        1.0
        -
        calibrated_shell_l1
        /
        max(frozen_shell_l1, 1e-15)
    )

    pred_pos, pred_ok = crossing_arrays(
        pred100,
        xi,
        FRONT_THRESHOLD,
    )

    truth_pos, truth_ok = crossing_arrays(
        truth100,
        xi,
        FRONT_THRESHOLD,
    )

    frozen_pos, frozen_ok = crossing_arrays(
        frozen100,
        xi,
        FRONT_THRESHOLD,
    )

    recovered = int(
        np.sum(
            pred_ok & truth_ok
        )
    )

    gaps = np.min(
        np.abs(
            pred100
            -
            FRONT_THRESHOLD
        ),
        axis=1,
    )

    conditioned_gap = (
        float(
            np.mean(
                gaps[truth_ok]
            )
        )
        if np.any(truth_ok)
        else np.inf
    )

    profile_l1_100d = float(
        np.mean(
            np.abs(
                pred100
                -
                truth100
            )
        )
    )

    common = (
        pred_ok
        &
        frozen_ok
        &
        truth_ok
    )

    if np.any(common):
        shifts = np.abs(
            pred_pos[common]
            -
            frozen_pos[common]
        )

        mean_shift = float(
            np.mean(shifts)
        )

        p90_shift = float(
            np.percentile(
                shifts,
                90,
            )
        )

    else:
        mean_shift = np.inf
        p90_shift = np.inf

    delta = calibrated - frozen
    required = target - frozen

    applied_shell = delta[idx100][shell]
    required_shell = required[idx100][shell]

    sign_agreement = float(
        np.mean(
            applied_shell
            *
            required_shell
            >=
            -1e-12
        )
    )

    overshoot_fraction = float(
        np.mean(
            np.abs(applied_shell)
            >
            (
                np.abs(required_shell)
                +
                1e-6
            )
        )
    )

    short = tau_end_days < 500.0

    short_cal_mae = float(
        np.mean(
            np.abs(
                delta[:, short, :]
            )
        )
    )

    max_correction = float(
        np.max(
            np.abs(delta)
        )
    )

    tv_delta = float(
        np.mean(
            np.sum(
                np.abs(
                    np.diff(
                        delta,
                        axis=2,
                    )
                ),
                axis=2,
            )
        )
    )

    tv_frozen = float(
        np.mean(
            np.sum(
                np.abs(
                    np.diff(
                        frozen,
                        axis=2,
                    )
                ),
                axis=2,
            )
        )
    )

    tv_ratio = (
        tv_delta
        /
        max(tv_frozen, 1e-12)
    )

    err = calibrated - truth

    def band_bias(lo, hi):
        mask = (
            (tau_end_days >= lo)
            &
            (tau_end_days < hi)
        )

        if not np.any(mask):
            return np.nan

        return float(
            np.mean(
                err[:, mask, :]
            )
        )

    b500 = band_bias(
        500.0,
        1000.0,
    )

    b1000 = band_bias(
        1000.0,
        2000.0,
    )

    b2000 = band_bias(
        2000.0,
        np.inf,
    )

    global_l1 = float(
        np.mean(
            np.abs(err)
        )
    )

    global_l2 = float(
        np.sqrt(
            np.mean(
                err ** 2
            )
        )
    )

    gates = {
        "front_error_reduction":
            front_error_reduction
            >=
            MIN_FRONT_ERROR_REDUCTION,

        "recovered_fronts":
            recovered
            >=
            MIN_RECOVERED_FRONTS,

        "conditioned_front_gap":
            conditioned_gap
            <=
            MAX_CONDITIONED_GAP,

        "100d_profile_L1":
            profile_l1_100d
            <=
            MAX_PROFILE_L1,

        "mean_frozen_front_xi_shift":
            mean_shift
            <=
            MAX_MEAN_FRONT_XI_SHIFT,

        "P90_frozen_front_xi_shift":
            p90_shift
            <=
            MAX_P90_FRONT_XI_SHIFT,

        "front_sign_agreement":
            sign_agreement
            >=
            MIN_SIGN_AGREEMENT,

        "front_overshoot_fraction":
            overshoot_fraction
            <=
            MAX_OVERSHOOT,

        "short_TOF_calibration_MAE":
            short_cal_mae
            <=
            MAX_SHORT_TOF_CAL_MAE,

        "global_abs_correction":
            max_correction
            <=
            MAX_GLOBAL_CORRECTION,

        "calibration_TV_ratio":
            tv_ratio
            <=
            MAX_CALIBRATION_TV_RATIO,

        "bias_500_1000":
            abs(b500)
            <=
            MAX_BIAS_500_1000,

        "bias_1000_2000":
            abs(b1000)
            <=
            MAX_BIAS_1000_2000,

        "bias_gt2000":
            abs(b2000)
            <=
            MAX_BIAS_GT2000,
    }

    return {
        "global_L1": global_l1,
        "global_L2": global_l2,
        "front_error_reduction_fraction": front_error_reduction,
        "frozen_front_shell_L1": frozen_shell_l1,
        "calibrated_front_shell_L1": calibrated_shell_l1,
        "recovered_fronts": recovered,
        "truth_fronts": int(np.sum(truth_ok)),
        "conditioned_gap": conditioned_gap,
        "profile_L1_100d": profile_l1_100d,
        "mean_frozen_front_xi_shift": mean_shift,
        "P90_frozen_front_xi_shift": p90_shift,
        "front_sign_agreement": sign_agreement,
        "front_overshoot_fraction": overshoot_fraction,
        "short_TOF_calibration_MAE": short_cal_mae,
        "global_abs_correction_MAX": max_correction,
        "calibration_TV_ratio": tv_ratio,
        "bias_500_1000": b500,
        "bias_1000_2000": b1000,
        "bias_gt2000": b2000,
        "complete_pass": bool(
            all(
                gates.values()
            )
        ),
        "gates": gates,
    }


def candidate_score(metrics):
    """
    Score is only for ranking persisted checkpoints.
    It never replaces the mandatory pass/fail contract.
    """
    return float(
        metrics["global_L1"]
        +
        3.0
        *
        max(
            0.0,
            0.50
            -
            metrics[
                "front_error_reduction_fraction"
            ],
        )
        +
        2.0
        *
        metrics["conditioned_gap"]
        +
        0.5
        *
        metrics["profile_L1_100d"]
        +
        0.25
        *
        abs(
            metrics[
                "bias_500_1000"
            ]
        )
        +
        0.25
        *
        abs(
            metrics[
                "bias_1000_2000"
            ]
        )
        +
        0.25
        *
        abs(
            metrics[
                "bias_gt2000"
            ]
        )
    )


# =============================================================================
# TRAINING
# =============================================================================

def experiment_configs():
    return [
        {
            "experiment": "B1",
            "description": "Narrow Gaussian residual fraction",
            "basis": "g1",
            "front_weight": 12.0,
            "crossing_weight": 2.0,
        },
        {
            "experiment": "B2",
            "description": "Medium Gaussian residual fraction",
            "basis": "g2",
            "front_weight": 12.0,
            "crossing_weight": 2.0,
        },
        {
            "experiment": "B3",
            "description": "Raised-cosine residual fraction",
            "basis": "g3",
            "front_weight": 12.0,
            "crossing_weight": 2.0,
        },
        {
            "experiment": "B4",
            "description": "Two-scale front-local residual basis",
            "basis": "g1+g2",
            "front_weight": 14.0,
            "crossing_weight": 3.0,
        },
        {
            "experiment": "B5",
            "description": "Crossing-constrained two-scale basis",
            "basis": "g1+g2",
            "front_weight": 16.0,
            "crossing_weight": 8.0,
        },
    ]


def train_experiment(
    config,
    profile_features,
    residual,
    frozen,
    target,
    truth,
    basis,
    tau_end_days,
    xi,
    times_days,
):
    exp = config["experiment"]

    exp_dir = EXPERIMENT_DIR / exp
    exp_dir.mkdir(parents=True, exist_ok=True)

    model = build_alpha_model(
        exp
    )

    nt, ns, nx = residual.shape

    X = profile_features.reshape(
        -1,
        2,
    ).astype(np.float32)

    residual_flat = residual.reshape(
        nt * ns,
        nx,
    ).astype(np.float32)

    truth_flat = truth.reshape(
        nt * ns,
        nx,
    ).astype(np.float32)

    frozen_flat = frozen.reshape(
        nt * ns,
        nx,
    ).astype(np.float32)

    if exp == "B1":
        g1 = basis["g1"].reshape(
            nt * ns,
            nx,
        )

        basis_a = g1
        basis_b = np.zeros_like(
            g1
        )

    elif exp == "B2":
        g2 = basis["g2"].reshape(
            nt * ns,
            nx,
        )

        basis_a = g2
        basis_b = np.zeros_like(
            g2
        )

    elif exp == "B3":
        g3 = basis["g3"].reshape(
            nt * ns,
            nx,
        )

        basis_a = g3
        basis_b = np.zeros_like(
            g3
        )

    else:
        basis_a = basis["g1"].reshape(
            nt * ns,
            nx,
        )

        basis_b = basis["g2"].reshape(
            nt * ns,
            nx,
        )

    basis_a = basis_a.astype(
        np.float32
    )

    basis_b = basis_b.astype(
        np.float32
    )

    front_mask = (
        (truth_flat >= FRONT_SHELL_LOW)
        &
        (truth_flat <= FRONT_SHELL_HIGH)
    ).astype(np.float32)

    # Profile-level short-TOF anchor.
    tau2 = np.broadcast_to(
        tau_end_days[None, :],
        (nt, ns),
    ).reshape(-1)

    short_profile = (
        tau2 < 500.0
    ).astype(np.float32)

    ds = tf.data.Dataset.from_tensor_slices(
        (
            X,
            residual_flat,
            basis_a,
            basis_b,
            front_mask,
            short_profile,
        )
    ).shuffle(
        min(
            nt * ns,
            20000,
        ),
        seed=SEED + int(exp[1:]),
        reshuffle_each_iteration=True,
    ).batch(
        512
    ).prefetch(
        tf.data.AUTOTUNE
    )

    optimizer = tf.keras.optimizers.Adam(
        INITIAL_LR
    )

    @tf.function
    def train_step(
        xb,
        rb,
        ga,
        gb,
        frontb,
        shortb,
    ):

        with tf.GradientTape() as tape:

            weights = model(
                xb,
                training=True,
            )

            if exp in {"B1", "B2", "B3"}:
                alpha = weights[:, 0:1]

                coeff = (
                    alpha
                    *
                    ga
                )

            else:
                w1 = weights[:, 0:1]
                w2 = weights[:, 1:2]

                coeff = (
                    w1 * ga
                    +
                    w2 * gb
                )

                coeff = tf.clip_by_value(
                    coeff,
                    0.0,
                    1.0,
                )

            pred_delta = (
                coeff
                *
                rb
            )

            residual_loss = tf.reduce_mean(
                tf.abs(
                    pred_delta
                    -
                    rb
                )
            )

            front_loss = (
                tf.reduce_sum(
                    frontb
                    *
                    tf.abs(
                        pred_delta
                        -
                        rb
                    )
                )
                /
                (
                    tf.reduce_sum(
                        frontb
                    )
                    +
                    1e-8
                )
            )

            # Penalize correction amplitude on short-TOF profiles.
            mean_abs_delta_profile = tf.reduce_mean(
                tf.abs(
                    pred_delta
                ),
                axis=1,
            )

            short_anchor = (
                tf.reduce_sum(
                    shortb
                    *
                    mean_abs_delta_profile
                )
                /
                (
                    tf.reduce_sum(
                        shortb
                    )
                    +
                    1e-8
                )
            )

            # Crossing-core moment surrogate:
            # minimize signed correction first moment in front support.
            #
            # Since sign/amplitude are already bounded, this discourages a
            # one-sided correction that translates the whole threshold front.
            moment = tf.reduce_mean(
                tf.abs(
                    tf.reduce_sum(
                        pred_delta
                        *
                        frontb,
                        axis=1,
                    )
                )
            )

            total = (
                residual_loss
                +
                config["front_weight"]
                *
                front_loss
                +
                2.5
                *
                short_anchor
                +
                config["crossing_weight"]
                *
                moment
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
            zip(
                grads,
                model.trainable_variables,
            )
        )

        return total

    epoch_rows = []

    best_any = None
    best_any_score = np.inf
    best_any_weights = None

    best_pass = None
    best_pass_score = np.inf
    best_pass_weights = None

    patience = 0

    start_time = time.perf_counter()

    for epoch in range(
        1,
        MAX_EPOCHS + 1,
    ):

        for batch in ds:
            train_step(
                *batch
            )

        if (
            epoch == 1
            or
            epoch % EVAL_EVERY == 0
        ):

            delta, coefficient = reconstruct_delta(
                exp,
                model,
                profile_features,
                residual,
                basis,
            )

            calibrated = (
                frozen
                +
                delta
            )

            metrics = evaluate(
                calibrated,
                frozen,
                target,
                truth,
                tau_end_days,
                xi,
                times_days,
            )

            sc = candidate_score(
                metrics
            )

            failed_gates = [
                gate
                for gate, passed
                in metrics["gates"].items()
                if not passed
            ]

            epoch_rows.append({
                "experiment": exp,
                "epoch": epoch,
                "score": sc,
                **{
                    key: value
                    for key, value
                    in metrics.items()
                    if key not in {
                        "gates",
                        "complete_pass",
                    }
                },
                "coefficient_mean": float(
                    np.mean(
                        coefficient
                    )
                ),
                "coefficient_P90": float(
                    np.percentile(
                        coefficient,
                        90,
                    )
                ),
                "coefficient_max": float(
                    np.max(
                        coefficient
                    )
                ),
                "complete_pass": metrics["complete_pass"],
                "failed_gates": ";".join(
                    failed_gates
                ),
            })

            print(
                f"  {exp} epoch={epoch:3d} | "
                f"L1={metrics['global_L1']:.3e} | "
                f"frontRed={100*metrics['front_error_reduction_fraction']:.1f}% | "
                f"fronts={metrics['recovered_fronts']:4d} | "
                f"gap={metrics['conditioned_gap']:.3e} | "
                f"shift90={metrics['P90_frozen_front_xi_shift']:.3e} | "
                f"sign={100*metrics['front_sign_agreement']:.1f}% | "
                f"over={100*metrics['front_overshoot_fraction']:.1f}% | "
                f"{'PASS' if metrics['complete_pass'] else 'FAIL'}"
            )

            if sc < best_any_score:
                best_any_score = sc
                best_any = metrics
                best_any_weights = model.get_weights()
                patience = 0
            else:
                patience += EVAL_EVERY

            if (
                metrics["complete_pass"]
                and
                sc < best_pass_score
            ):
                best_pass_score = sc
                best_pass = metrics
                best_pass_weights = model.get_weights()

            if (
                metrics["complete_pass"]
                and
                epoch >= 20
            ):
                break

            if patience >= EARLY_STOP_PATIENCE:
                break

            if (
                patience > 0
                and
                patience % 20 == 0
            ):
                new_lr = max(
                    float(
                        tf.keras.backend.get_value(
                            optimizer.learning_rate
                        )
                    )
                    *
                    0.5,
                    MIN_LR,
                )

                optimizer.learning_rate.assign(
                    new_lr
                )

    runtime = (
        time.perf_counter()
        -
        start_time
    )

    if best_any_weights is None:
        raise RuntimeError(
            f"{exp}: no evaluated checkpoint."
        )

    model.set_weights(
        best_any_weights
    )

    best_any_path = (
        exp_dir
        /
        f"V15SG7CR3F4_{exp}_Best_Any_Alpha_Model.keras"
    )

    model.save(
        best_any_path
    )

    # Candidate deployment based on best-any.
    delta_any, coefficient_any = reconstruct_delta(
        exp,
        model,
        profile_features,
        residual,
        basis,
    )

    calibrated_any = (
        frozen
        +
        delta_any
    )

    best_pass_path = None

    if best_pass_weights is not None:
        model.set_weights(
            best_pass_weights
        )

        best_pass_path = (
            exp_dir
            /
            f"V15SG7CR3F4_{exp}_Best_Passing_Alpha_Model.keras"
        )

        model.save(
            best_pass_path
        )

    return {
        "experiment": exp,
        "description": config["description"],
        "runtime_seconds": runtime,
        "epoch_rows": epoch_rows,
        "best_any_metrics": best_any,
        "best_any_score": best_any_score,
        "best_any_path": str(best_any_path),
        "best_any_sha256": sha256_file(
            best_any_path
        ),
        "best_any_calibrated": calibrated_any,
        "best_any_delta": delta_any,
        "best_any_coefficient": coefficient_any,
        "best_pass_metrics": best_pass,
        "best_pass_score": (
            best_pass_score
            if best_pass is not None
            else None
        ),
        "best_pass_path": (
            str(best_pass_path)
            if best_pass_path is not None
            else None
        ),
        "best_pass_sha256": (
            sha256_file(
                best_pass_path
            )
            if best_pass_path is not None
            else None
        ),
    }


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "PAD-Stream V15-SG7C-R3F4 controlled front-local residual basis calibration."
        )
    )

    parser.add_argument(
        "--experiments",
        type=str,
        default="B1,B2,B3,B4,B5",
        help="Comma-separated trainable experiments.",
    )

    args = parser.parse_args()

    selected = {
        item.strip()
        for item
        in args.experiments.split(",")
        if item.strip()
    }

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F4")
    print("Controlled Front-Local Residual Basis Calibration")
    print("=" * 78)

    print("\nBOUNDED CALIBRATOR TRAINING WILL BE PERFORMED.")
    print("SG7B-11 PI-RNN WEIGHTS WILL NOT BE CHANGED.")
    print("NO UNCONSTRAINED ADDITIVE CORRECTION WILL BE TRAINED.")
    print("NO FRONT OR TOF-BIAS GATE WILL BE RELAXED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")
    print("ALL CHECKPOINT METRICS WILL BE PERSISTED.")

    for path in [
        R3F3_SUMMARY,
        R3F3_CONTRACT,
        R3C_NUMERICAL,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing R3F4 prerequisite:\n{path}"
            )

    r3f3_summary = load_json(
        R3F3_SUMMARY
    )

    r3f3_contract = load_json(
        R3F3_CONTRACT
    )

    if (
        r3f3_summary.get("status")
        !=
        "FRONT_LOCAL_RESIDUAL_BASIS_CONTRACT_READY"
    ):
        raise RuntimeError(
            "R3F4 requires R3F3 ready contract status."
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

    residual = (
        target
        -
        frozen
    )

    basis = make_basis_fields(
        target,
        xi,
    )

    profile_features = make_profile_features(
        normalized_tD,
        tau_end_days,
    )

    # -------------------------------------------------------------------------
    # B0 frozen control
    # -------------------------------------------------------------------------

    control_metrics = evaluate(
        frozen,
        frozen,
        target,
        truth,
        tau_end_days,
        xi,
        times_days,
    )

    print("\nFROZEN B0 CONTROL")
    print(f"  Front reduction         : {100*control_metrics['front_error_reduction_fraction']:.2f}%")
    print(f"  Recovered fronts        : {control_metrics['recovered_fronts']} / {control_metrics['truth_fronts']}")
    print(f"  Conditioned gap         : {control_metrics['conditioned_gap']:.3e}")
    print(f"  Global L1               : {control_metrics['global_L1']:.3e}")

    configs = [
        cfg
        for cfg in experiment_configs()
        if cfg["experiment"] in selected
    ]

    all_epoch_rows = []

    final_rows = [
        {
            "experiment": "B0",
            "description": "Frozen SG7B-11 control",
            "runtime_seconds": 0.0,
            **{
                k: v
                for k, v
                in control_metrics.items()
                if k not in {
                    "gates",
                    "complete_pass",
                }
            },
            "complete_pass": control_metrics["complete_pass"],
            "failed_gates": ";".join(
                [
                    gate
                    for gate, passed
                    in control_metrics["gates"].items()
                    if not passed
                ]
            ),
        }
    ]

    gate_rows = []

    for gate, passed in control_metrics["gates"].items():
        gate_rows.append({
            "experiment": "B0",
            "checkpoint_type": "control",
            "gate": gate,
            "passed": bool(passed),
        })

    checkpoint_rows = []
    results = []

    print("\n" + "=" * 78)
    print("R3F4 CONTROLLED EXPERIMENTS")
    print("=" * 78)

    for config in configs:

        print(
            f"\n{config['experiment']} — {config['description']}"
        )

        result = train_experiment(
            config,
            profile_features,
            residual,
            frozen,
            target,
            truth,
            basis,
            tau_end_days,
            xi,
            times_days,
        )

        results.append(
            result
        )

        all_epoch_rows.extend(
            result["epoch_rows"]
        )

        m = result["best_any_metrics"]

        failed = [
            gate
            for gate, passed
            in m["gates"].items()
            if not passed
        ]

        final_rows.append({
            "experiment": result["experiment"],
            "description": result["description"],
            "runtime_seconds": result["runtime_seconds"],
            **{
                k: v
                for k, v
                in m.items()
                if k not in {
                    "gates",
                    "complete_pass",
                }
            },
            "complete_pass": m["complete_pass"],
            "failed_gates": ";".join(
                failed
            ),
        })

        for gate, passed in m["gates"].items():
            gate_rows.append({
                "experiment": result["experiment"],
                "checkpoint_type": "best_any",
                "gate": gate,
                "passed": bool(passed),
            })

        checkpoint_rows.append({
            "experiment": result["experiment"],
            "checkpoint_type": "best_any",
            "path": result["best_any_path"],
            "sha256": result["best_any_sha256"],
            "complete_pass": bool(m["complete_pass"]),
        })

        if result["best_pass_metrics"] is not None:

            mp = result["best_pass_metrics"]

            for gate, passed in mp["gates"].items():
                gate_rows.append({
                    "experiment": result["experiment"],
                    "checkpoint_type": "best_passing",
                    "gate": gate,
                    "passed": bool(passed),
                })

            checkpoint_rows.append({
                "experiment": result["experiment"],
                "checkpoint_type": "best_passing",
                "path": result["best_pass_path"],
                "sha256": result["best_pass_sha256"],
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
    # Final screen / nomination
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F4 FINAL SCREEN")
    print("=" * 78)

    for row in final_rows:

        print(
            f"[{'PASS' if row['complete_pass'] else 'FAIL'}] "
            f"{row['experiment']} | "
            f"frontRed={100*row['front_error_reduction_fraction']:.1f}% | "
            f"fronts={int(row['recovered_fronts'])} | "
            f"gap={row['conditioned_gap']:.3e} | "
            f"shift90={row['P90_frozen_front_xi_shift']:.3e} | "
            f"sign={100*row['front_sign_agreement']:.1f}% | "
            f"over={100*row['front_overshoot_fraction']:.1f}% | "
            f"L1={row['global_L1']:.3e}"
        )

    print("=" * 78)

    passing = [
        result
        for result in results
        if result["best_pass_metrics"] is not None
    ]

    if passing:

        passing.sort(
            key=lambda result:
            result["best_pass_score"]
        )

        candidate = passing[0]

        candidate_model_path = Path(
            candidate["best_pass_path"]
        )

        candidate_model = tf.keras.models.load_model(
            candidate_model_path,
            compile=False,
        )

        delta, coefficient = reconstruct_delta(
            candidate["experiment"],
            candidate_model,
            profile_features,
            residual,
            basis,
        )

        calibrated = (
            frozen
            +
            delta
        )

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
            calibration_coefficient=coefficient,
        )

        status = "FRONT_LOCAL_BASIS_CALIBRATOR_NOMINATED"

        recommendation = (
            "A bounded front-local residual-basis calibrator satisfies the complete "
            "R3F3 preservation contract while SG7B-11 remains frozen. Proceed to "
            "independent validation before final streamline redeployment or map-back."
        )

        next_milestone = (
            "V15-SG7C-R3F5 — Independent Front-Local Calibrator Validation"
        )

        manifest = {
            "milestone": "V15-SG7C-R3F4",
            "status": status,
            "candidate_experiment": candidate["experiment"],
            "candidate_model_path": candidate["best_pass_path"],
            "candidate_sha256": candidate["best_pass_sha256"],
            "candidate_is_frozen": False,
            "SG7B11_modified": False,
            "next_milestone": next_milestone,
        }

    else:

        candidate = None

        status = "NO_R3F4_BASIS_CALIBRATOR_PASSES_COMPLETE_CONTRACT"

        recommendation = (
            "No bounded front-local basis calibrator satisfies the complete contract. "
            "Use the persisted R3F4 trajectories to determine whether the remaining "
            "limiter is support width, crossing displacement, or insufficient residual "
            "coverage before changing the basis family."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R — Front-Local Basis Outcome Audit"
        )

        manifest = {
            "milestone": "V15-SG7C-R3F4",
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
        "milestone": "V15-SG7C-R3F4",
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
        MIN_FRONT_ERROR_REDUCTION,
        linestyle="--",
    )

    plt.ylabel(
        "Front-shell error reduction fraction"
    )

    plt.xlabel(
        "Experiment"
    )

    plt.title(
        "V15-SG7C-R3F4 Front Error Reduction"
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F4_Front_Error_Reduction.png",
        dpi=300,
    )

    plt.close()

    plt.figure(figsize=(9, 5))

    x = np.arange(
        len(final_rows)
    )

    width = 0.35

    plt.bar(
        x - width / 2,
        [
            row["front_sign_agreement"]
            for row in final_rows
        ],
        width=width,
        label="sign agreement",
    )

    plt.bar(
        x + width / 2,
        [
            row["front_overshoot_fraction"]
            for row in final_rows
        ],
        width=width,
        label="overshoot",
    )

    plt.xticks(
        x,
        labels,
    )

    plt.ylabel(
        "Fraction"
    )

    plt.title(
        "V15-SG7C-R3F4 Directionality / Overshoot"
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        /
        "V15SG7CR3F4_Directionality_Overshoot.png",
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
    print("V15-SG7C-R3F4 CONTROLLED CALIBRATION: COMPLETE")
    print()
    print("SG7B-11 remains frozen and authoritative.")
    print("Only bounded front-local residual fractions were trained.")
    print("No front, TOF-bias, map-back, or plume-validation gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
