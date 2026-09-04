from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import json
import time

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7B-10
# Controlled Front-Aware PI-RNN Refinement
#
# PURPOSE
# -------
# Execute the controlled E0-E6 refinement matrix defined by V15-SG7B-9 while
# preserving the accepted SG7B-6D physics/data implementation as the authority.
#
# This script deliberately imports the accepted SG7B-6D source module instead
# of reimplementing its finite-volume operator, fractional-flow law, dataset
# loader, target generation, or held-out evaluator.
#
# IMPORTANT
# ---------
# - The frozen SG7B-7R model is NEVER overwritten.
# - Every trainable experiment starts independently from the same frozen model.
# - E0 is an immutable control and is never trained.
# - SG7B-10 may NOMINATE a candidate only.
# - Final replacement authority remains V15-SG7B-11 independent validation.
# - Canonical SG7B-6H/7R activity-scaled physics gates are not redefined here;
#   they remain mandatory and are explicitly reserved for SG7B-11.
# =============================================================================


# =============================================================================
# ROOT / AUTHORITATIVE SOURCES
# =============================================================================

ROOT = Path(__file__).resolve().parent

BASE_SOURCE_FILE = (
    ROOT
    / "PAD_Stream_V15SG7B6D_Advective_Flux_Refinement.py"
)

FROZEN_MODEL_FILE = (
    ROOT
    / "output"
    / "V15_SG7B7R"
    / "V15SG7B_FROZEN_Model.keras"
)

SG7B9_CONTRACT_FILE = (
    ROOT
    / "output"
    / "V15_SG7B9"
    / "V15SG7B9_Front_Aware_Refinement_Contract.json"
)

SG7B9_EXPERIMENT_FILE = (
    ROOT
    / "output"
    / "V15_SG7B9"
    / "V15SG7B9_SG7B10_Experiment_Matrix.csv"
)

DEFAULT_DEPLOYMENT_WORKSPACE = (
    ROOT.parent
    / f"{ROOT.name}_SG5C_seed_11x11"
)

DEPLOYMENT_SG6_RELATIVE = (
    Path("output")
    / "V15_SG6"
    / "STREAMLINE_TRANSPORT_COORDINATES.npz"
)

DEPLOYMENT_SG7C_RELATIVE = (
    Path("output")
    / "V15_SG7C"
    / "SG7C_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B10"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

EXPERIMENT_DIR = (
    OUTPUT_DIR
    / "experiments"
)

EXPERIMENT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# OUTPUT FILES
# =============================================================================

CANDIDATE_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B10_Candidate_Model.keras"
)

CANDIDATE_MANIFEST_FILE = (
    OUTPUT_DIR
    / "V15SG7B10_Candidate_Manifest.json"
)

EXPERIMENT_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7B10_Experiment_Metrics.csv"
)

EPOCH_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7B10_Epoch_Metrics.csv"
)

PRECHECK_FILE = (
    OUTPUT_DIR
    / "V15SG7B10_Front_Contract_Precheck.json"
)

TEST_RESULTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B10_Candidate_Test_Results.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B10_Summary.json"
)


# =============================================================================
# FROZEN IDENTITY
# =============================================================================

EXPECTED_FROZEN_SHA256 = (
    "9242af83e9aae6dc91ce215f78bf2a6d"
    "539972632d5e5ce759ea1fc83f3c11be"
)


# =============================================================================
# FRONT CONTRACT
# =============================================================================

FRONT_THRESHOLD = 0.210
FRONT_LOW = 0.210
CROSSING_LOW = 0.200
FRONT_HIGH = 0.300
FRONT_ANCHOR_HIGH = 0.320

# Differentiable classification temperature.
CROSSING_TEMPERATURE = 0.010

# Numerical slope / classification tolerances.
MONOTONIC_TOL = 1.0e-5
EPS = 1.0e-8

# SG7B-9 design targets.
MIN_100D_CROSSINGS = 744
LEGACY_MAX_GLOBAL_THRESHOLD_GAP = 2.913121e-02
MAX_100D_PROFILE_L1 = 4.500330e-03
MAX_LOCAL_MONOTONIC_VIOLATION = 0.020

# Important semantic correction:
# SG7B-8's reported mean threshold gap was averaged over all streamlines,
# including profiles where SG7A itself has no S=0.21 front. Driving those
# profiles toward the threshold would be nonphysical. SG7B-10 therefore uses
# the same 75% reduction requirement, but conditions the operational gap metric
# on the subset of profiles where SG7A actually contains a front. The original
# global quantity is still reported as a legacy diagnostic and is not relaxed;
# it is simply not used to create artificial fronts in no-front profiles.
FRONT_CONDITIONED_GAP_REDUCTION = 0.75


# =============================================================================
# PRESERVATION GATES RETAINED FROM SG7B-7R
# =============================================================================

MAX_TEST_L1 = 0.020
MAX_TEST_L2 = 0.030
MAX_MASS_RELATIVE_MAE = 0.030
MAX_INJECTOR_L1 = 0.015
MAX_FRONT_L1 = 0.030
MAX_EARLY_L1 = 0.020
MAX_LATE_L1 = 0.025

MAX_CANONICAL_MEAN = 0.500
MAX_CANONICAL_P90 = 1.000
MAX_CANONICAL_FRAC_GT1 = 0.10

# Canonical gates are intentionally PENDING in SG7B-10 and must be recomputed
# independently by SG7B-11 before any replacement decision.


# =============================================================================
# TRAINING CONTRACT FROM SG7B-9
# =============================================================================

MAXIMUM_EPOCHS = 160
EARLY_STOPPING_PATIENCE = 30
LR_REDUCTION_PATIENCE = 12
INITIAL_LEARNING_RATE = 2.5e-6
MINIMUM_LEARNING_RATE = 2.5e-7
GRADIENT_CLIP_NORM = 5.0

EVAL_EVERY = 5
BATCH_SIZE = 32

EARLY_TIME_WEIGHT = 4.0
MIDDLE_TIME_WEIGHT = 2.0
LATE_TIME_WEIGHT = 1.0

# Keep the accepted SG7B-6D source losses as preservation regularizers.
LAMBDA_DATA = 1.00
LAMBDA_FV = 0.20
LAMBDA_FACE_FLUX = 1.00
LAMBDA_ADV_DIV = 1.50
LAMBDA_MASS = 0.40
LAMBDA_INJECTOR = 0.30
LAMBDA_LATE = 0.30


# =============================================================================
# REPRODUCIBILITY
# =============================================================================

SEED = 1510710
np.random.seed(SEED)
tf.random.set_seed(SEED)


# =============================================================================
# GENERIC HELPERS
# =============================================================================


def compute_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Missing file for SHA-256:\n{path}")

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV:\n{path}")
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row.keys():
            if key not in keys:
                keys.append(key)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def find_npz_key(database, aliases, description):
    for key in aliases:
        if key in database:
            return key
    raise KeyError(
        f"Could not identify {description}.\n"
        f"Accepted aliases: {aliases}\n"
        f"Available keys: {list(database.keys())}"
    )


def load_base_module():
    if not BASE_SOURCE_FILE.exists():
        raise FileNotFoundError(
            "SG7B-10 must be placed beside the accepted SG7B-6D source.\n"
            f"Missing:\n{BASE_SOURCE_FILE}"
        )

    spec = importlib.util.spec_from_file_location(
        "pad_stream_sg7b6d_authority",
        BASE_SOURCE_FILE,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not construct SG7B-6D import specification.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bool_from_csv(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


# =============================================================================
# EXPERIMENT CONTRACT
# =============================================================================


def load_experiment_matrix(selected: set[str] | None = None):
    rows = load_csv(SG7B9_EXPERIMENT_FILE)
    output = []

    for row in rows:
        experiment = str(row["experiment"]).strip()
        training = bool_from_csv(row["training"])

        item = {
            "experiment": experiment,
            "description": str(row["description"]),
            "front_zone_weight": float(row["front_zone_weight"]),
            "crossing_weight": float(row["crossing_weight"]),
            "front_shape_weight": float(row["front_shape_weight"]),
            "gradient_weight": float(row["gradient_weight"]),
            "anchor_weight": float(row["anchor_weight"]),
            "learning_rate": float(row["learning_rate"]),
            "maximum_epochs": int(float(row["maximum_epochs"])),
            "training": training,
            "role": str(row["role"]),
        }

        if selected is None or experiment in selected or experiment == "E0":
            output.append(item)

    if not any(row["experiment"] == "E0" for row in output):
        raise RuntimeError("Experiment matrix must contain E0 frozen control.")

    return output


# =============================================================================
# DEPLOYMENT DATABASE
# =============================================================================


def load_deployment_database(workspace: Path, tD_scale: float):
    sg6_path = workspace / DEPLOYMENT_SG6_RELATIVE
    sg7c_path = workspace / DEPLOYMENT_SG7C_RELATIVE

    if not sg6_path.exists():
        raise FileNotFoundError(f"Missing SG6 deployment geometry:\n{sg6_path}")
    if not sg7c_path.exists():
        raise FileNotFoundError(f"Missing SG7C deployment database:\n{sg7c_path}")

    sg6 = np.load(sg6_path, allow_pickle=True)
    sg7c = np.load(sg7c_path, allow_pickle=True)

    xi_key = find_npz_key(sg6, ["xi", "transport_xi"], "SG6 xi")
    tau_end_key = find_npz_key(
        sg6,
        ["tau_end_s", "terminal_tau_s", "terminal_tof_s"],
        "SG6 terminal TOF",
    )
    weights_key = find_npz_key(
        sg6,
        ["weights_m3_s", "weights", "flow_weights_m3_s"],
        "SG6 streamline weights",
    )

    time_key = find_npz_key(
        sg7c,
        ["times_days", "physical_times_days", "deployment_times_days"],
        "SG7C deployment times",
    )
    truth_key = find_npz_key(
        sg7c,
        ["SG7A_saturation", "truth_saturation", "reference_saturation", "S_truth"],
        "SG7C SG7A truth",
    )
    frozen_pred_key = find_npz_key(
        sg7c,
        ["PI_RNN_saturation", "pirnn_saturation", "predicted_saturation", "S_pirnn"],
        "SG7C frozen PI-RNN prediction",
    )

    xi = np.asarray(sg6[xi_key], dtype=np.float32)
    tau_end_s = np.asarray(sg6[tau_end_key], dtype=np.float64)
    weights = np.asarray(sg6[weights_key], dtype=np.float64)
    times_days = np.asarray(sg7c[time_key], dtype=np.float64)
    truth_all = np.asarray(sg7c[truth_key], dtype=np.float32)
    frozen_pred_all = np.asarray(sg7c[frozen_pred_key], dtype=np.float32)

    idx100 = int(np.argmin(np.abs(times_days - 100.0)))
    if not np.isclose(times_days[idx100], 100.0):
        raise RuntimeError("SG7C database does not contain the required 100-day snapshot.")

    truth100 = truth_all[idx100]
    stored_frozen100 = frozen_pred_all[idx100]

    terminal_days = tau_end_s / 86400.0
    tD_100 = 100.0 / terminal_days
    normalized_tD = tD_100 / float(tD_scale)

    if np.any(normalized_tD < -1.0e-8) or np.any(normalized_tD > 1.0 + 1.0e-6):
        raise RuntimeError(
            "100-day deployment produces normalized tD outside the frozen training domain."
        )

    n_streamlines = len(tau_end_s)
    n_nodes = len(xi)

    X100 = np.zeros((n_streamlines, n_nodes, 2), dtype=np.float32)
    X100[:, :, 0] = xi[None, :]
    X100[:, :, 1] = normalized_tD[:, None].astype(np.float32)

    if truth100.shape != (n_streamlines, n_nodes):
        raise RuntimeError(
            f"Unexpected SG7C truth shape {truth100.shape}; "
            f"expected {(n_streamlines, n_nodes)}."
        )

    return {
        "X100": X100,
        "truth100": truth100,
        "stored_frozen100": stored_frozen100,
        "weights": weights,
        "tau_end_s": tau_end_s,
        "xi": xi,
        "tD_100": tD_100,
        "times_days": times_days,
        "workspace": str(workspace),
    }


# =============================================================================
# FRONT METRICS
# =============================================================================


def profile_has_crossing_np(S: np.ndarray, threshold: float = FRONT_THRESHOLD):
    shifted = np.asarray(S, dtype=np.float64) - threshold
    return np.any(shifted[:, :-1] * shifted[:, 1:] < 0.0, axis=1)


def front_metrics_np(prediction: np.ndarray, truth: np.ndarray):
    prediction = np.asarray(prediction, dtype=np.float64)
    truth = np.asarray(truth, dtype=np.float64)

    truth_has_front = profile_has_crossing_np(truth)
    pred_has_front = profile_has_crossing_np(prediction)

    truth_front_count = int(np.sum(truth_has_front))
    pred_front_count_total = int(np.sum(pred_has_front))
    recovered_front_count = int(np.sum(truth_has_front & pred_has_front))

    per_profile_gap = np.min(
        np.abs(prediction - FRONT_THRESHOLD),
        axis=1,
    )

    global_gap_mean = float(np.mean(per_profile_gap))
    global_gap_p90 = float(np.percentile(per_profile_gap, 90))

    if np.any(truth_has_front):
        conditioned_gap = per_profile_gap[truth_has_front]
        conditioned_gap_mean = float(np.mean(conditioned_gap))
        conditioned_gap_p90 = float(np.percentile(conditioned_gap, 90))
        conditioned_profile_l1 = float(
            np.mean(np.abs(prediction[truth_has_front] - truth[truth_has_front]))
        )
    else:
        conditioned_gap_mean = np.nan
        conditioned_gap_p90 = np.nan
        conditioned_profile_l1 = np.nan

    profile_l1 = np.mean(np.abs(prediction - truth), axis=1)
    profile_l1_mean = float(np.mean(profile_l1))

    # Front-local monotonicity. Saturation should not increase substantially
    # along xi in the displacement-front band.
    truth_left = truth[:, :-1]
    truth_right = truth[:, 1:]
    local_mask = (
        (np.minimum(truth_left, truth_right) <= FRONT_HIGH)
        & (np.maximum(truth_left, truth_right) >= CROSSING_LOW)
    )

    dS = prediction[:, 1:] - prediction[:, :-1]
    if np.any(local_mask):
        monotonic_violation = float(np.mean(dS[local_mask] > MONOTONIC_TOL))
    else:
        monotonic_violation = 0.0

    front_zone_mask = (truth >= FRONT_LOW) & (truth <= FRONT_HIGH)
    if np.any(front_zone_mask):
        front_zone_l1 = float(np.mean(np.abs(prediction - truth)[front_zone_mask]))
    else:
        front_zone_l1 = 0.0

    return {
        "truth_front_count": truth_front_count,
        "pred_front_count_total": pred_front_count_total,
        "recovered_front_count": recovered_front_count,
        "global_threshold_gap_mean": global_gap_mean,
        "global_threshold_gap_p90": global_gap_p90,
        "conditioned_threshold_gap_mean": conditioned_gap_mean,
        "conditioned_threshold_gap_p90": conditioned_gap_p90,
        "profile_L1_mean": profile_l1_mean,
        "conditioned_profile_L1": conditioned_profile_l1,
        "front_zone_L1": front_zone_l1,
        "local_monotonic_violation": monotonic_violation,
    }


# =============================================================================
# HELD-OUT PRESERVATION METRICS NOT EXPLICITLY RETURNED BY SG7B-6D
# =============================================================================


def additional_preservation_metrics(X, truth, prediction):
    X = np.asarray(X, dtype=np.float64)
    truth = np.asarray(truth, dtype=np.float64)
    prediction = np.asarray(prediction, dtype=np.float64)

    error = np.abs(prediction - truth)
    t_norm = X[:, 0, 1]

    early_mask = t_norm <= (1.0 / 3.0)
    late_mask = t_norm >= (2.0 / 3.0)

    early_l1 = float(np.mean(error[early_mask])) if np.any(early_mask) else 0.0
    late_l1 = float(np.mean(error[late_mask])) if np.any(late_mask) else 0.0

    front_mask = (truth >= FRONT_LOW) & (truth <= FRONT_HIGH)
    front_l1 = float(np.mean(error[front_mask])) if np.any(front_mask) else 0.0

    local_left = truth[:, :-1]
    local_right = truth[:, 1:]
    local_mask = (
        (np.minimum(local_left, local_right) <= FRONT_HIGH)
        & (np.maximum(local_left, local_right) >= CROSSING_LOW)
    )
    dS = prediction[:, 1:] - prediction[:, :-1]
    local_monotonic = (
        float(np.mean(dS[local_mask] > MONOTONIC_TOL))
        if np.any(local_mask)
        else 0.0
    )

    return {
        "early_L1": early_l1,
        "late_L1_recomputed": late_l1,
        "front_L1": front_l1,
        "local_monotonic_violation": local_monotonic,
    }


# =============================================================================
# DIFFERENTIABLE FRONT LOSSES
# =============================================================================


def time_emphasis_tf(X):
    t = X[:, 0, 1]
    return tf.where(
        t <= (1.0 / 3.0),
        tf.cast(EARLY_TIME_WEIGHT, tf.float32),
        tf.where(
            t <= (2.0 / 3.0),
            tf.cast(MIDDLE_TIME_WEIGHT, tf.float32),
            tf.cast(LATE_TIME_WEIGHT, tf.float32),
        ),
    )


def safe_masked_mean(values, mask):
    values = tf.cast(values, tf.float32)
    mask = tf.cast(mask, tf.float32)
    return tf.reduce_sum(values * mask) / (tf.reduce_sum(mask) + EPS)


def front_zone_state_loss_tf(X, Y_true, Y_pred):
    truth = Y_true[:, :, 0]
    pred = Y_pred[:, :, 0]

    mask = tf.cast(
        (truth >= FRONT_LOW) & (truth <= FRONT_HIGH),
        tf.float32,
    )
    time_weight = time_emphasis_tf(X)[:, None]

    return safe_masked_mean(
        tf.square(pred - truth) * time_weight,
        mask,
    )


def threshold_crossing_loss_tf(X, Y_true, Y_pred):
    truth = Y_true[:, :, 0]
    pred = Y_pred[:, :, 0]

    # Include the initial-state side of the front as well as the swept side.
    # This allows the model to learn a genuine threshold crossing instead of
    # merely approaching 0.21 from above.
    local_mask = tf.cast(
        (truth >= CROSSING_LOW - 1.0e-6) & (truth <= FRONT_HIGH),
        tf.float32,
    )

    target_high = tf.cast(truth > FRONT_THRESHOLD, tf.float32)
    logits = (pred - FRONT_THRESHOLD) / CROSSING_TEMPERATURE

    bce = tf.nn.sigmoid_cross_entropy_with_logits(
        labels=target_high,
        logits=logits,
    )

    time_weight = time_emphasis_tf(X)[:, None]
    return safe_masked_mean(bce * time_weight, local_mask)


def front_shape_loss_tf(X, Y_true, Y_pred):
    truth = Y_true[:, :, 0]
    pred = Y_pred[:, :, 0]

    dtruth = truth[:, 1:] - truth[:, :-1]
    dpred = pred[:, 1:] - pred[:, :-1]

    local_mask = tf.cast(
        (tf.minimum(truth[:, :-1], truth[:, 1:]) <= FRONT_HIGH)
        & (tf.maximum(truth[:, :-1], truth[:, 1:]) >= CROSSING_LOW),
        tf.float32,
    )

    # Normalize by local truth gradient energy to avoid domination by one shock.
    scale = tf.reduce_mean(tf.square(dtruth)) + EPS
    time_weight = time_emphasis_tf(X)[:, None]

    return safe_masked_mean(
        tf.square(dpred - dtruth) * time_weight / scale,
        local_mask,
    )


def gradient_regularizer_tf(X, Y_true, Y_pred):
    truth = Y_true[:, :, 0]
    pred = Y_pred[:, :, 0]

    dpred = pred[:, 1:] - pred[:, :-1]

    local_mask = tf.cast(
        (tf.minimum(truth[:, :-1], truth[:, 1:]) <= FRONT_HIGH)
        & (tf.maximum(truth[:, :-1], truth[:, 1:]) >= CROSSING_LOW),
        tf.float32,
    )

    # Positive dS/dxi is a local monotonicity violation for the current
    # injector-to-producer orientation.
    violation = tf.nn.relu(dpred - MONOTONIC_TOL)
    time_weight = time_emphasis_tf(X)[:, None]

    return safe_masked_mean(tf.square(violation) * time_weight, local_mask)


def frozen_anchor_loss_tf(Y_true, Y_pred, frozen_anchor):
    truth = Y_true[:, :, 0]
    pred = Y_pred[:, :, 0]
    anchor = frozen_anchor[:, :, 0]

    # Anchor only the already-correct swept interior. Do not anchor the low
    # saturation tail, because that is precisely where threshold avoidance was
    # diagnosed and must be allowed to move.
    mask = tf.cast(truth > FRONT_ANCHOR_HIGH, tf.float32)
    return safe_masked_mean(tf.square(pred - anchor), mask)


# =============================================================================
# TRAINING STEP
# =============================================================================


def make_train_step(base, config):
    front_weight = tf.constant(config["front_zone_weight"], dtype=tf.float32)
    crossing_weight = tf.constant(config["crossing_weight"], dtype=tf.float32)
    shape_weight = tf.constant(config["front_shape_weight"], dtype=tf.float32)
    grad_weight = tf.constant(config["gradient_weight"], dtype=tf.float32)
    anchor_weight = tf.constant(config["anchor_weight"], dtype=tf.float32)

    @tf.function
    def train_step(
        model,
        optimizer,
        X,
        Y,
        target_face,
        target_div,
        frozen_anchor,
        tD_scale,
        dxi,
    ):
        with tf.GradientTape() as tape:
            Y_pred = model(X, training=True)
            S_pred = Y_pred[:, :, 0]

            L_data = base.data_loss(Y, Y_pred)

            _, relative, _, _ = base.finite_volume_residual(
                model,
                X,
                tD_scale,
                training=True,
            )
            L_fv = tf.reduce_mean(tf.square(relative))

            predicted_face, predicted_div = base.predicted_advective_flux(S_pred)
            L_face = base.normalized_face_flux_loss(predicted_face, target_face)
            L_div = base.normalized_divergence_loss(predicted_div, target_div)

            L_mass = base.mass_loss(Y, Y_pred, dxi)
            L_injector = base.injector_loss(Y, Y_pred)
            L_late = base.late_time_loss(X, Y, Y_pred)

            L_front = front_zone_state_loss_tf(X, Y, Y_pred)
            L_cross = threshold_crossing_loss_tf(X, Y, Y_pred)
            L_shape = front_shape_loss_tf(X, Y, Y_pred)
            L_grad = gradient_regularizer_tf(X, Y, Y_pred)
            L_anchor = frozen_anchor_loss_tf(Y, Y_pred, frozen_anchor)

            total = (
                LAMBDA_DATA * L_data
                + LAMBDA_FV * L_fv
                + LAMBDA_FACE_FLUX * L_face
                + LAMBDA_ADV_DIV * L_div
                + LAMBDA_MASS * L_mass
                + LAMBDA_INJECTOR * L_injector
                + LAMBDA_LATE * L_late
                + front_weight * L_front
                + crossing_weight * L_cross
                + shape_weight * L_shape
                + grad_weight * L_grad
                + anchor_weight * L_anchor
            )

        gradients = tape.gradient(total, model.trainable_variables)
        gradients, _ = tf.clip_by_global_norm(gradients, GRADIENT_CLIP_NORM)
        optimizer.apply_gradients(zip(gradients, model.trainable_variables))

        return (
            total,
            L_data,
            L_fv,
            L_face,
            L_div,
            L_mass,
            L_injector,
            L_late,
            L_front,
            L_cross,
            L_shape,
            L_grad,
            L_anchor,
        )

    return train_step


# =============================================================================
# TF DATASET
# =============================================================================


def make_tf_dataset(X, Y, face, div, anchor, seed):
    ds = tf.data.Dataset.from_tensor_slices(
        (
            X.astype(np.float32),
            Y.astype(np.float32),
            face.astype(np.float32),
            div.astype(np.float32),
            anchor.astype(np.float32),
        )
    )

    ds = ds.shuffle(
        buffer_size=len(X),
        seed=seed,
        reshuffle_each_iteration=True,
    )
    ds = ds.batch(BATCH_SIZE)
    ds = ds.prefetch(tf.data.AUTOTUNE)
    return ds


# =============================================================================
# CANDIDATE SCREEN
# =============================================================================


def evaluate_candidate(
    base,
    model,
    dataset,
    targets,
    deployment,
    conditioned_gap_target,
):
    xi = np.asarray(dataset["xi"], dtype=float)
    tD_scale = float(dataset["tD_scale"][0])

    test = base.evaluate_split(
        model,
        dataset["X_test"],
        dataset["Y_test"],
        targets["face_test"],
        targets["div_test"],
        xi,
        tD_scale,
    )

    test_extra = additional_preservation_metrics(
        dataset["X_test"],
        test["truth"],
        test["prediction"],
    )

    deployment_prediction = model.predict(
        deployment["X100"],
        batch_size=BATCH_SIZE,
        verbose=0,
    )[:, :, 0]

    front = front_metrics_np(
        deployment_prediction,
        deployment["truth100"],
    )

    gates = {
        "finite": bool(np.all(np.isfinite(deployment_prediction))),
        "bounds": bool(
            np.min(deployment_prediction) >= base.S_INITIAL - 1.0e-7
            and np.max(deployment_prediction) <= base.S_INJECTED + 1.0e-7
        ),
        "held_out_L1": bool(test["L1"] < MAX_TEST_L1),
        "held_out_L2": bool(test["L2"] < MAX_TEST_L2),
        "mass": bool(test["mass_relative_MAE"] < MAX_MASS_RELATIVE_MAE),
        "injector": bool(test["injector_L1"] < MAX_INJECTOR_L1),
        "front_L1": bool(test_extra["front_L1"] < MAX_FRONT_L1),
        "early_L1": bool(test_extra["early_L1"] < MAX_EARLY_L1),
        "late_L1": bool(test_extra["late_L1_recomputed"] < MAX_LATE_L1),
        "front_crossings": bool(front["recovered_front_count"] >= MIN_100D_CROSSINGS),
        "conditioned_gap": bool(
            front["conditioned_threshold_gap_mean"] <= conditioned_gap_target
        ),
        "profile_100d_L1": bool(front["profile_L1_mean"] <= MAX_100D_PROFILE_L1),
        "local_monotonic": bool(
            front["local_monotonic_violation"] <= MAX_LOCAL_MONOTONIC_VIOLATION
        ),
    }

    # SG7B-10 is a nomination stage. Canonical activity-scaled physics is
    # intentionally not duplicated from SG7B-6H/7R here.
    local_screen_pass = all(gates.values())

    return {
        "test": test,
        "test_extra": test_extra,
        "deployment_prediction": deployment_prediction,
        "front": front,
        "gates": gates,
        "local_screen_pass": bool(local_screen_pass),
        "canonical_physics_status": "PENDING_SG7B11_INDEPENDENT_VALIDATION",
    }


# =============================================================================
# CHECKPOINT SCORE
# =============================================================================


def candidate_score(screen, baseline_front, conditioned_gap_target):
    front = screen["front"]
    test = screen["test"]
    extra = screen["test_extra"]

    crossing_deficit = max(
        0.0,
        MIN_100D_CROSSINGS - front["recovered_front_count"],
    ) / max(MIN_100D_CROSSINGS, 1)

    gap_term = (
        front["conditioned_threshold_gap_mean"]
        / max(conditioned_gap_target, 1.0e-8)
    )

    profile_term = front["profile_L1_mean"] / MAX_100D_PROFILE_L1
    test_term = test["L1"] / MAX_TEST_L1
    mass_term = test["mass_relative_MAE"] / MAX_MASS_RELATIVE_MAE
    monotonic_term = (
        front["local_monotonic_violation"]
        / max(MAX_LOCAL_MONOTONIC_VIOLATION, 1.0e-8)
    )

    # Reward actual recovery relative to E0 while keeping preservation terms
    # explicit. Lower is better.
    improvement_reward = (
        front["recovered_front_count"]
        / max(baseline_front["truth_front_count"], 1)
    )

    return float(
        3.0 * crossing_deficit
        + 2.0 * gap_term
        + 2.0 * profile_term
        + 1.0 * test_term
        + 0.5 * mass_term
        + 0.5 * monotonic_term
        - 0.5 * improvement_reward
        + 0.25 * (extra["front_L1"] / MAX_FRONT_L1)
    )


# =============================================================================
# SINGLE EXPERIMENT TRAINING
# =============================================================================


def train_experiment(
    base,
    config,
    dataset,
    targets,
    frozen_anchor,
    deployment,
    baseline_front,
    conditioned_gap_target,
):
    experiment = config["experiment"]
    exp_dir = EXPERIMENT_DIR / experiment
    exp_dir.mkdir(parents=True, exist_ok=True)

    best_weights = exp_dir / f"V15SG7B10_{experiment}_Best.weights.h5"
    best_model_file = exp_dir / f"V15SG7B10_{experiment}_Best_Model.keras"
    final_model_file = exp_dir / f"V15SG7B10_{experiment}_Final_Model.keras"
    history_file = exp_dir / f"V15SG7B10_{experiment}_History.npz"

    experiment_seed = SEED + int(experiment[1:]) * 101
    np.random.seed(experiment_seed)
    tf.random.set_seed(experiment_seed)

    # Fresh load for every experiment. This is the core independence contract.
    model = tf.keras.models.load_model(FROZEN_MODEL_FILE)

    xi = np.asarray(dataset["xi"], dtype=float)
    dxi = tf.constant(float(xi[1] - xi[0]), dtype=tf.float32)
    tD_scale = float(dataset["tD_scale"][0])
    tD_scale_tf = tf.constant(tD_scale, dtype=tf.float32)

    train_ds = make_tf_dataset(
        dataset["X_train"],
        dataset["Y_train"],
        targets["face_train"],
        targets["div_train"],
        frozen_anchor["train"],
        experiment_seed,
    )

    optimizer = tf.keras.optimizers.Adam(
        learning_rate=float(config["learning_rate"]),
    )

    train_step = make_train_step(base, config)

    history = {
        "epoch": [],
        "learning_rate": [],
        "train_total": [],
        "train_data": [],
        "train_FV": [],
        "train_face": [],
        "train_div": [],
        "train_mass": [],
        "train_injector": [],
        "train_late": [],
        "train_front": [],
        "train_cross": [],
        "train_shape": [],
        "train_grad": [],
        "train_anchor": [],
        "val_L1": [],
        "val_L2": [],
        "val_mass": [],
        "deploy_recovered_fronts": [],
        "deploy_conditioned_gap": [],
        "deploy_global_gap": [],
        "deploy_profile_L1": [],
        "deploy_monotonic": [],
        "score": [],
    }

    best_score = np.inf
    best_epoch = -1
    patience_counter = 0
    lr_plateau_counter = 0
    current_lr = float(config["learning_rate"])

    start = time.perf_counter()

    max_epochs = int(config["maximum_epochs"] or MAXIMUM_EPOCHS)

    for epoch in range(max_epochs):
        batch_metrics = []

        for Xb, Yb, Fb, Db, Ab in train_ds:
            values = train_step(
                model,
                optimizer,
                Xb,
                Yb,
                Fb,
                Db,
                Ab,
                tD_scale_tf,
                dxi,
            )
            batch_metrics.append([float(value.numpy()) for value in values])

        train_mean = np.mean(batch_metrics, axis=0)

        do_eval = (epoch == 0) or ((epoch + 1) % EVAL_EVERY == 0)
        if not do_eval:
            continue

        val = base.evaluate_split(
            model,
            dataset["X_val"],
            dataset["Y_val"],
            targets["face_val"],
            targets["div_val"],
            xi,
            tD_scale,
        )

        deploy_pred = model.predict(
            deployment["X100"],
            batch_size=BATCH_SIZE,
            verbose=0,
        )[:, :, 0]
        deploy_front = front_metrics_np(deploy_pred, deployment["truth100"])

        quick_screen = {
            "front": deploy_front,
            "test": {
                "L1": val["L1"],
                "mass_relative_MAE": val["mass_relative_MAE"],
            },
            "test_extra": {
                "front_L1": min(MAX_FRONT_L1, deploy_front["front_zone_L1"]),
            },
        }
        score = candidate_score(
            quick_screen,
            baseline_front,
            conditioned_gap_target,
        )

        history["epoch"].append(epoch + 1)
        history["learning_rate"].append(current_lr)

        train_keys = [
            "train_total",
            "train_data",
            "train_FV",
            "train_face",
            "train_div",
            "train_mass",
            "train_injector",
            "train_late",
            "train_front",
            "train_cross",
            "train_shape",
            "train_grad",
            "train_anchor",
        ]
        for key, value in zip(train_keys, train_mean):
            history[key].append(float(value))

        history["val_L1"].append(val["L1"])
        history["val_L2"].append(val["L2"])
        history["val_mass"].append(val["mass_relative_MAE"])
        history["deploy_recovered_fronts"].append(deploy_front["recovered_front_count"])
        history["deploy_conditioned_gap"].append(
            deploy_front["conditioned_threshold_gap_mean"]
        )
        history["deploy_global_gap"].append(deploy_front["global_threshold_gap_mean"])
        history["deploy_profile_L1"].append(deploy_front["profile_L1_mean"])
        history["deploy_monotonic"].append(deploy_front["local_monotonic_violation"])
        history["score"].append(score)

        eligible = (
            np.isfinite(score)
            and val["L1"] < MAX_TEST_L1
            and val["L2"] < MAX_TEST_L2
            and val["mass_relative_MAE"] < MAX_MASS_RELATIVE_MAE
            and val["injector_L1"] < MAX_INJECTOR_L1
        )

        if eligible and score < best_score - 1.0e-6:
            best_score = score
            best_epoch = epoch + 1
            patience_counter = 0
            lr_plateau_counter = 0
            model.save_weights(best_weights)
        else:
            patience_counter += EVAL_EVERY
            lr_plateau_counter += EVAL_EVERY

        if lr_plateau_counter >= LR_REDUCTION_PATIENCE:
            new_lr = max(current_lr * 0.5, MINIMUM_LEARNING_RATE)
            if new_lr < current_lr:
                current_lr = new_lr
                optimizer.learning_rate.assign(current_lr)
            lr_plateau_counter = 0

        if (
            epoch == 0
            or (epoch + 1) % 10 == 0
            or deploy_front["recovered_front_count"] >= MIN_100D_CROSSINGS
        ):
            print(
                f"  {experiment} | epoch {epoch + 1:4d}/{max_epochs} | "
                f"lr={current_lr:.2e} | "
                f"valL1={val['L1']:.3e} | "
                f"fronts={deploy_front['recovered_front_count']:4d}/"
                f"{deploy_front['truth_front_count']:4d} | "
                f"gap={deploy_front['conditioned_threshold_gap_mean']:.3e} | "
                f"L1@100d={deploy_front['profile_L1_mean']:.3e} | "
                f"mono={100.0*deploy_front['local_monotonic_violation']:.2f}% | "
                f"score={score:.3f}"
            )

        # Do not stop merely because the front gate is reached. Require a small
        # confirmation period so that the state does not immediately regress.
        comfortable = (
            deploy_front["recovered_front_count"] >= MIN_100D_CROSSINGS
            and deploy_front["conditioned_threshold_gap_mean"] <= conditioned_gap_target
            and deploy_front["profile_L1_mean"] <= MAX_100D_PROFILE_L1
            and deploy_front["local_monotonic_violation"] <= MAX_LOCAL_MONOTONIC_VIOLATION
            and val["L1"] < 0.010
            and val["mass_relative_MAE"] < 0.010
        )
        if comfortable and epoch >= 30:
            print(f"\n  {experiment}: front-aware comfortable target reached.")
            break

        if patience_counter >= EARLY_STOPPING_PATIENCE:
            print(
                f"\n  {experiment}: early stopping at epoch {epoch + 1}; "
                f"best epoch = {best_epoch}."
            )
            break

    runtime = time.perf_counter() - start

    for key, value in history.items():
        history[key] = np.asarray(value)
    np.savez_compressed(history_file, **history)

    model.save(final_model_file)

    if not best_weights.exists():
        raise RuntimeError(f"{experiment} produced no eligible checkpoint.")

    model.load_weights(best_weights)
    model.save(best_model_file)

    final_screen = evaluate_candidate(
        base,
        model,
        dataset,
        targets,
        deployment,
        conditioned_gap_target,
    )

    return {
        "experiment": experiment,
        "config": config,
        "runtime_seconds": float(runtime),
        "best_epoch": int(best_epoch),
        "best_score": float(best_score),
        "best_model_file": str(best_model_file),
        "final_model_file": str(final_model_file),
        "history_file": str(history_file),
        "screen": final_screen,
        "history": history,
    }


# =============================================================================
# E0 CONTROL
# =============================================================================


def evaluate_control(base, dataset, targets, deployment, conditioned_gap_target):
    model = tf.keras.models.load_model(FROZEN_MODEL_FILE)
    screen = evaluate_candidate(
        base,
        model,
        dataset,
        targets,
        deployment,
        conditioned_gap_target,
    )
    return model, screen


# =============================================================================
# RESULT ROWS
# =============================================================================


def result_row(experiment, description, config, screen, runtime_seconds=0.0, best_epoch=0, score=np.nan):
    test = screen["test"]
    extra = screen["test_extra"]
    front = screen["front"]

    return {
        "experiment": experiment,
        "description": description,
        "front_zone_weight": config.get("front_zone_weight", 0.0),
        "crossing_weight": config.get("crossing_weight", 0.0),
        "front_shape_weight": config.get("front_shape_weight", 0.0),
        "gradient_weight": config.get("gradient_weight", 0.0),
        "anchor_weight": config.get("anchor_weight", 0.0),
        "runtime_seconds": runtime_seconds,
        "best_epoch": best_epoch,
        "score": score,
        "held_out_L1": test["L1"],
        "held_out_L2": test["L2"],
        "mass_relative_MAE": test["mass_relative_MAE"],
        "injector_L1": test["injector_L1"],
        "late_L1": extra["late_L1_recomputed"],
        "early_L1": extra["early_L1"],
        "front_L1": extra["front_L1"],
        "100d_truth_fronts": front["truth_front_count"],
        "100d_total_pred_fronts": front["pred_front_count_total"],
        "100d_recovered_fronts": front["recovered_front_count"],
        "100d_global_gap": front["global_threshold_gap_mean"],
        "100d_conditioned_gap": front["conditioned_threshold_gap_mean"],
        "100d_profile_L1": front["profile_L1_mean"],
        "100d_front_zone_L1": front["front_zone_L1"],
        "100d_monotonic_violation": front["local_monotonic_violation"],
        "local_screen_pass": screen["local_screen_pass"],
        "canonical_physics_status": screen["canonical_physics_status"],
    }


# =============================================================================
# PLOTS
# =============================================================================


def plot_experiment_summary(rows):
    labels = [row["experiment"] for row in rows]
    crossings = [row["100d_recovered_fronts"] for row in rows]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(labels, crossings)
    ax.axhline(MIN_100D_CROSSINGS, linestyle="--", label="SG7B-9 crossing target")
    ax.set_xlabel("Experiment")
    ax.set_ylabel("Recovered SG7A fronts at 100 days")
    ax.set_title("PAD-Stream V15-SG7B-10\nFront Recovery by Experiment")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "V15SG7B10_Front_Recovery.png", dpi=300)
    plt.close(fig)

    gaps = [row["100d_conditioned_gap"] for row in rows]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(labels, gaps)
    ax.set_xlabel("Experiment")
    ax.set_ylabel("Mean min |S - 0.21| on SG7A-front profiles")
    ax.set_title("PAD-Stream V15-SG7B-10\nFront-Conditioned Threshold Gap")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "V15SG7B10_Front_Conditioned_Gap.png", dpi=300)
    plt.close(fig)

    state = [row["held_out_L1"] for row in rows]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(labels, state)
    ax.axhline(MAX_TEST_L1, linestyle="--", label="SG7B-7R L1 gate")
    ax.set_xlabel("Experiment")
    ax.set_ylabel("Held-out L1")
    ax.set_title("PAD-Stream V15-SG7B-10\nState Preservation")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "V15SG7B10_State_Preservation.png", dpi=300)
    plt.close(fig)


def plot_candidate_profiles(deployment, candidate_prediction, frozen_prediction):
    truth = deployment["truth100"]
    xi = deployment["xi"]
    truth_has_front = profile_has_crossing_np(truth)
    indices = np.where(truth_has_front)[0]
    if len(indices) == 0:
        return

    positions = np.linspace(0, len(indices) - 1, min(6, len(indices)), dtype=int)
    selected = indices[positions]

    fig, ax = plt.subplots(figsize=(10, 7))
    for idx in selected:
        ax.plot(xi, truth[idx], linewidth=1.8, label=f"SG7A #{idx}")
        ax.plot(xi, frozen_prediction[idx], linestyle=":", linewidth=1.2)
        ax.plot(xi, candidate_prediction[idx], linestyle="--", linewidth=1.4)

    ax.axhline(FRONT_THRESHOLD, linestyle="--", label="S=0.21")
    ax.set_xlabel(r"TOF coordinate $\xi$")
    ax.set_ylabel("Saturation")
    ax.set_title(
        "PAD-Stream V15-SG7B-10\n"
        "100-Day SG7A / Frozen / Candidate Front Profiles"
    )
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "V15SG7B10_Candidate_Profiles_100d.png", dpi=300)
    plt.close(fig)


# =============================================================================
# MAIN
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="PAD-Stream V15-SG7B-10 controlled front-aware refinement."
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default=str(DEFAULT_DEPLOYMENT_WORKSPACE),
        help="11x11 SG5C deployment workspace used by SG7B-8/SG7D diagnostics.",
    )
    parser.add_argument(
        "--experiments",
        type=str,
        default="E1,E2,E3,E4,E5,E6",
        help="Comma-separated trainable experiments. E0 is always evaluated.",
    )
    args = parser.parse_args()

    selected = {
        value.strip()
        for value in args.experiments.split(",")
        if value.strip()
    }

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7B-10")
    print("Controlled Front-Aware PI-RNN Refinement")
    print("=" * 78)

    print("\nTRAINING WILL BE PERFORMED FOR SELECTED E1-E6 EXPERIMENTS.")
    print("THE FROZEN SG7B-7R MODEL WILL NOT BE MODIFIED.")
    print("EACH EXPERIMENT STARTS FROM THE SAME VERIFIED FROZEN CHECKPOINT.")
    print("NO ARCHITECTURE CHANGE WILL BE MADE.")
    print("NO SG7B-7R FREEZE GATE WILL BE RELAXED.")
    print("NO SG7E THRESHOLD WILL BE CHANGED.")
    print("NO CANDIDATE WILL BE DECLARED FROZEN BY SG7B-10.")

    # -------------------------------------------------------------------------
    # Preconditions
    # -------------------------------------------------------------------------
    if not SG7B9_CONTRACT_FILE.exists():
        raise FileNotFoundError(
            "SG7B-9 refinement contract is required before SG7B-10.\n"
            f"Missing:\n{SG7B9_CONTRACT_FILE}"
        )

    contract = load_json(SG7B9_CONTRACT_FILE)
    if contract.get("milestone") != "V15-SG7B-9":
        raise RuntimeError("Unexpected SG7B-9 contract identity.")

    actual_hash = compute_sha256(FROZEN_MODEL_FILE)
    if actual_hash != EXPECTED_FROZEN_SHA256:
        raise RuntimeError(
            "Frozen SG7B model identity mismatch.\n"
            f"Expected: {EXPECTED_FROZEN_SHA256}\n"
            f"Actual  : {actual_hash}"
        )

    print("\nFROZEN SOURCE")
    print(f"  Model                   : {FROZEN_MODEL_FILE.name}")
    print(f"  SHA-256                 : {actual_hash}")
    print("  Identity                : PASS")

    base = load_base_module()

    # -------------------------------------------------------------------------
    # Load authoritative data/physics from SG7B-6D implementation.
    # -------------------------------------------------------------------------
    dataset = base.load_dataset()
    sg7a = base.load_sg7a()
    targets = base.build_advective_targets(dataset, sg7a)

    tD_scale = float(dataset["tD_scale"][0])
    deployment_workspace = Path(args.workspace).resolve()
    deployment = load_deployment_database(deployment_workspace, tD_scale)

    print("\nAUTHORITATIVE SOURCE IMPLEMENTATION")
    print(f"  SG7B-6D source          : {BASE_SOURCE_FILE.name}")
    print(f"  Training profiles       : {len(dataset['X_train']):,}")
    print(f"  Validation profiles     : {len(dataset['X_val']):,}")
    print(f"  Test profiles           : {len(dataset['X_test']):,}")
    print(f"  Sequence nodes          : {len(dataset['xi'])}")
    print(f"  Deployment streamlines  : {len(deployment['X100']):,}")

    # -------------------------------------------------------------------------
    # Frozen anchors and E0 deployment identity.
    # -------------------------------------------------------------------------
    frozen_model = tf.keras.models.load_model(FROZEN_MODEL_FILE)

    frozen_anchor = {
        split: frozen_model.predict(
            dataset[f"X_{split}"].astype(np.float32),
            batch_size=BATCH_SIZE,
            verbose=0,
        ).astype(np.float32)
        for split in ["train", "val", "test"]
    }

    fresh_frozen_100 = frozen_model.predict(
        deployment["X100"],
        batch_size=BATCH_SIZE,
        verbose=0,
    )[:, :, 0]

    deployment_identity_linf = float(
        np.max(np.abs(fresh_frozen_100 - deployment["stored_frozen100"]))
    )

    if deployment_identity_linf > 2.0e-6:
        raise RuntimeError(
            "Fresh frozen-model deployment does not reproduce the accepted "
            "SG7C 100-day prediction within tolerance.\n"
            f"Linf = {deployment_identity_linf:.6e}"
        )

    baseline_front = front_metrics_np(
        fresh_frozen_100,
        deployment["truth100"],
    )

    conditioned_gap_target = (
        (1.0 - FRONT_CONDITIONED_GAP_REDUCTION)
        * baseline_front["conditioned_threshold_gap_mean"]
    )

    print("\n" + "=" * 78)
    print("FRONT CONTRACT PRECHECK")
    print("=" * 78)
    print(f"SG7A 100d front profiles  : {baseline_front['truth_front_count']:,}")
    print(f"Frozen recovered fronts   : {baseline_front['recovered_front_count']:,}")
    print(f"Frozen global gap         : {baseline_front['global_threshold_gap_mean']:.6e}")
    print(
        "Frozen front-conditioned gap: "
        f"{baseline_front['conditioned_threshold_gap_mean']:.6e}"
    )
    print(f"Legacy SG7B-9 global target: {LEGACY_MAX_GLOBAL_THRESHOLD_GAP:.6e}")
    print(f"Operational conditioned target: {conditioned_gap_target:.6e}")
    print(f"Fresh/stored SG7C Linf    : {deployment_identity_linf:.6e}")
    print("\nNOTE:")
    print(
        "  The operational gap is conditioned on SG7A-front-bearing profiles."
    )
    print(
        "  The original all-profile SG7B-8 gap remains a diagnostic because "
        "no-front profiles should not be forced toward S=0.21."
    )

    precheck = {
        "milestone": "V15-SG7B-10",
        "frozen_sha256": actual_hash,
        "deployment_workspace": str(deployment_workspace),
        "deployment_identity_linf": deployment_identity_linf,
        "baseline_front_metrics": baseline_front,
        "legacy_global_gap_target": LEGACY_MAX_GLOBAL_THRESHOLD_GAP,
        "front_conditioned_gap_target": conditioned_gap_target,
        "semantic_note": (
            "Operational threshold-gap gate is conditioned on SG7A-front-bearing "
            "profiles to avoid creating artificial threshold crossings in "
            "physically no-front profiles."
        ),
    }
    with PRECHECK_FILE.open("w", encoding="utf-8") as handle:
        json.dump(precheck, handle, indent=2)

    # -------------------------------------------------------------------------
    # E0 frozen control.
    # -------------------------------------------------------------------------
    control_model, control_screen = evaluate_control(
        base,
        dataset,
        targets,
        deployment,
        conditioned_gap_target,
    )

    experiment_matrix = load_experiment_matrix(selected)
    control_config = next(row for row in experiment_matrix if row["experiment"] == "E0")

    rows = [
        result_row(
            "E0",
            control_config["description"],
            control_config,
            control_screen,
            runtime_seconds=0.0,
            best_epoch=0,
            score=np.nan,
        )
    ]
    epoch_rows = []
    trained_results = []

    print("\n" + "=" * 78)
    print("E0 FROZEN CONTROL")
    print("=" * 78)
    print(f"Held-out L1             : {control_screen['test']['L1']:.6e}")
    print(f"Held-out L2             : {control_screen['test']['L2']:.6e}")
    print(f"Mass relative MAE       : {control_screen['test']['mass_relative_MAE']:.6e}")
    print(f"100d recovered fronts   : {control_screen['front']['recovered_front_count']:,}")
    print(
        "100d conditioned gap  : "
        f"{control_screen['front']['conditioned_threshold_gap_mean']:.6e}"
    )
    print(f"100d profile L1         : {control_screen['front']['profile_L1_mean']:.6e}")

    # -------------------------------------------------------------------------
    # E1-E6.
    # -------------------------------------------------------------------------
    for config in experiment_matrix:
        if not config["training"]:
            continue

        experiment = config["experiment"]
        print("\n" + "=" * 78)
        print(f"{experiment} — {config['description']}")
        print("=" * 78)
        print(f"front-zone weight       : {config['front_zone_weight']}")
        print(f"crossing weight         : {config['crossing_weight']}")
        print(f"shape weight            : {config['front_shape_weight']}")
        print(f"gradient weight         : {config['gradient_weight']}")
        print(f"anchor weight           : {config['anchor_weight']}")

        result = train_experiment(
            base,
            config,
            dataset,
            targets,
            frozen_anchor,
            deployment,
            baseline_front,
            conditioned_gap_target,
        )
        trained_results.append(result)

        screen = result["screen"]
        row = result_row(
            experiment,
            config["description"],
            config,
            screen,
            runtime_seconds=result["runtime_seconds"],
            best_epoch=result["best_epoch"],
            score=result["best_score"],
        )
        rows.append(row)

        history = result["history"]
        for i in range(len(history["epoch"])):
            epoch_rows.append(
                {
                    "experiment": experiment,
                    **{
                        key: (
                            float(history[key][i])
                            if key != "epoch"
                            else int(history[key][i])
                        )
                        for key in history.keys()
                    },
                }
            )

        print("\nBEST-CHECKPOINT SCREEN")
        print(f"  Held-out L1             : {screen['test']['L1']:.6e}")
        print(f"  Held-out L2             : {screen['test']['L2']:.6e}")
        print(f"  Mass relative MAE       : {screen['test']['mass_relative_MAE']:.6e}")
        print(f"  Early L1                : {screen['test_extra']['early_L1']:.6e}")
        print(f"  Front L1                : {screen['test_extra']['front_L1']:.6e}")
        print(f"  Late L1                 : {screen['test_extra']['late_L1_recomputed']:.6e}")
        print(f"  100d recovered fronts   : {screen['front']['recovered_front_count']:,}")
        print(
            "  100d conditioned gap    : "
            f"{screen['front']['conditioned_threshold_gap_mean']:.6e}"
        )
        print(f"  100d global gap         : {screen['front']['global_threshold_gap_mean']:.6e}")
        print(f"  100d profile L1         : {screen['front']['profile_L1_mean']:.6e}")
        print(
            "  Local monotonic violation: "
            f"{100.0 * screen['front']['local_monotonic_violation']:.3f}%"
        )
        print(f"  Local screen            : {'PASS' if screen['local_screen_pass'] else 'FAIL'}")
        print("  Canonical physics       : PENDING SG7B-11")

    # -------------------------------------------------------------------------
    # Candidate selection.
    # -------------------------------------------------------------------------
    passing = [result for result in trained_results if result["screen"]["local_screen_pass"]]

    candidate = None
    if passing:
        candidate = min(passing, key=lambda item: item["best_score"])
        source = Path(candidate["best_model_file"])
        candidate_model = tf.keras.models.load_model(source)
        candidate_model.save(CANDIDATE_MODEL_FILE)

        candidate_hash = compute_sha256(CANDIDATE_MODEL_FILE)
        candidate_screen = candidate["screen"]

        np.savez_compressed(
            TEST_RESULTS_FILE,
            xi=np.asarray(dataset["xi"]),
            tD_test=np.asarray(dataset["tD_test"]),
            truth=candidate_screen["test"]["truth"],
            prediction=candidate_screen["test"]["prediction"],
            error=candidate_screen["test"]["error"],
            deployment_truth_100d=deployment["truth100"],
            deployment_frozen_100d=fresh_frozen_100,
            deployment_candidate_100d=candidate_screen["deployment_prediction"],
        )

        manifest = {
            "milestone": "V15-SG7B-10",
            "status": "CANDIDATE_NOMINATED_PENDING_SG7B11",
            "experiment": candidate["experiment"],
            "description": candidate["config"]["description"],
            "candidate_model": CANDIDATE_MODEL_FILE.name,
            "candidate_sha256": candidate_hash,
            "frozen_parent_model": FROZEN_MODEL_FILE.name,
            "frozen_parent_sha256": actual_hash,
            "architecture_changed": False,
            "frozen_model_replaced": False,
            "front_screen_passed": True,
            "canonical_physics_status": "PENDING_SG7B11_INDEPENDENT_VALIDATION",
            "next_milestone": "V15-SG7B-11 — Independent Front-Aware Candidate Validation",
        }
        with CANDIDATE_MANIFEST_FILE.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)

        plot_candidate_profiles(
            deployment,
            candidate_screen["deployment_prediction"],
            fresh_frozen_100,
        )
    else:
        candidate_hash = None

    # -------------------------------------------------------------------------
    # Outputs / summary.
    # -------------------------------------------------------------------------
    save_csv(EXPERIMENT_METRICS_FILE, rows)
    save_csv(EPOCH_METRICS_FILE, epoch_rows)
    plot_experiment_summary(rows)

    print("\n" + "=" * 78)
    print("V15-SG7B-10 CONTROLLED REFINEMENT SUMMARY")
    print("=" * 78)

    for row in rows:
        print(
            f"{row['experiment']:>2s} | "
            f"fronts={int(row['100d_recovered_fronts']):4d} | "
            f"gap={float(row['100d_conditioned_gap']):.3e} | "
            f"100dL1={float(row['100d_profile_L1']):.3e} | "
            f"testL1={float(row['held_out_L1']):.3e} | "
            f"screen={'PASS' if bool(row['local_screen_pass']) else 'FAIL'}"
        )

    if candidate is not None:
        print("\nCANDIDATE NOMINATED")
        print(f"  Experiment              : {candidate['experiment']}")
        print(f"  Model                   : {CANDIDATE_MODEL_FILE.name}")
        print(f"  SHA-256                 : {candidate_hash}")
        print("  Frozen SG7B replaced    : NO")
        print("  Canonical physics       : PENDING SG7B-11")
        status = "CANDIDATE_NOMINATED_PENDING_SG7B11"
        next_milestone = "V15-SG7B-11 — Independent Front-Aware Candidate Validation"
    else:
        print("\nNO SG7B-10 CANDIDATE PASSED THE LOCAL FRONT/PRESERVATION SCREEN.")
        print("The frozen SG7B model remains authoritative.")
        status = "NO_CANDIDATE_PASSED_LOCAL_SCREEN"
        next_milestone = "V15-SG7B-10R — Front-Aware Refinement Outcome Audit"

    summary = {
        "milestone": "V15-SG7B-10",
        "description": "Controlled front-aware PI-RNN refinement",
        "source_implementation": BASE_SOURCE_FILE.name,
        "frozen_source_model": FROZEN_MODEL_FILE.name,
        "frozen_source_sha256": actual_hash,
        "frozen_model_modified": False,
        "architecture_changed": False,
        "deployment_workspace": str(deployment_workspace),
        "deployment_identity_linf": deployment_identity_linf,
        "front_contract": {
            "minimum_recovered_100d_fronts": MIN_100D_CROSSINGS,
            "legacy_global_gap_target": LEGACY_MAX_GLOBAL_THRESHOLD_GAP,
            "front_conditioned_baseline_gap": baseline_front[
                "conditioned_threshold_gap_mean"
            ],
            "front_conditioned_gap_target": conditioned_gap_target,
            "maximum_100d_profile_L1": MAX_100D_PROFILE_L1,
            "maximum_local_monotonic_violation": MAX_LOCAL_MONOTONIC_VIOLATION,
        },
        "canonical_physics_contract": {
            "mean_max": MAX_CANONICAL_MEAN,
            "P90_max": MAX_CANONICAL_P90,
            "fraction_gt1_max": MAX_CANONICAL_FRAC_GT1,
            "status": "PENDING_SG7B11_INDEPENDENT_VALIDATION",
        },
        "experiments_run": [row["experiment"] for row in rows],
        "candidate_experiment": candidate["experiment"] if candidate else None,
        "candidate_model": CANDIDATE_MODEL_FILE.name if candidate else None,
        "candidate_sha256": candidate_hash,
        "status": status,
        "next_milestone": next_milestone,
    }

    with SUMMARY_FILE.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")
    print("\nTables:")
    print(f"  {EXPERIMENT_METRICS_FILE.name}")
    print(f"  {EPOCH_METRICS_FILE.name}")
    print("\nPrecheck:")
    print(f"  {PRECHECK_FILE.name}")
    print("\nDiagnostics:")
    print("  V15SG7B10_Front_Recovery.png")
    print("  V15SG7B10_Front_Conditioned_Gap.png")
    print("  V15SG7B10_State_Preservation.png")
    if candidate is not None:
        print("  V15SG7B10_Candidate_Profiles_100d.png")
        print("\nCandidate:")
        print(f"  {CANDIDATE_MODEL_FILE.name}")
        print(f"  {CANDIDATE_MANIFEST_FILE.name}")
        print(f"  {TEST_RESULTS_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    if candidate is not None:
        print("V15-SG7B-10 CONTROLLED REFINEMENT: CANDIDATE NOMINATED")
        print("\nSTATUS:")
        print("FRONT-AWARE CANDIDATE EXISTS — NOT YET FROZEN")
        print("\nNext milestone:")
        print("V15-SG7B-11 — Independent Front-Aware Candidate Validation")
    else:
        print("V15-SG7B-10 CONTROLLED REFINEMENT: NO CANDIDATE PASSED")
        print("\nThe original frozen SG7B remains authoritative.")
        print("\nNext milestone:")
        print("V15-SG7B-10R — Front-Aware Refinement Outcome Audit")
    print("=" * 78)


if __name__ == "__main__":
    main()
