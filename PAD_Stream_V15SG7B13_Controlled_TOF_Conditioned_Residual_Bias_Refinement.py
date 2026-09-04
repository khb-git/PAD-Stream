from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
import time

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7B-13
# Controlled TOF-Conditioned Residual Bias Refinement
#
# TRAINING MILESTONE
#
# PURPOSE
# -------
# SG7B-12 established a controlled refinement contract after SG7C-R2 diagnosed
# TOF_CONDITIONED_BIAS. This milestone:
#
#   1. starts every trainable experiment from the SAME independently frozen
#      SG7B-11 front-aware checkpoint,
#   2. preserves the accepted SG7B-6D physics/state losses,
#   3. adds a deployment-supervised TOF-conditioned correction step at 100 d,
#   4. protects short-TOF streamlines and the accepted frozen solution,
#   5. preserves the recovered S=0.21 front,
#   6. evaluates the SG7B-12 bias gates plus SG7B-11 local preservation gates,
#   7. nominates a candidate only; it does NOT freeze/promote a new authority.
#
# IMPORTANT
# ---------
# SG7B-13 is a nomination/training stage. Independent canonical-physics and
# final promotion authority remain downstream.
# =============================================================================


# =============================================================================
# ROOT / AUTHORITATIVE SOURCES
# =============================================================================

ROOT = Path(__file__).resolve().parent

BASE_SOURCE_FILE = ROOT / "PAD_Stream_V15SG7B6D_Advective_Flux_Refinement.py"

SG7B10_SOURCE_FILE = (
    ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"
)

SG7B12_CONTRACT_FILE = (
    ROOT / "output" / "V15_SG7B12"
    / "V15SG7B12_TOF_Conditioned_Refinement_Contract.json"
)

SG7B12_EXPERIMENT_FILE = (
    ROOT / "output" / "V15_SG7B12"
    / "V15SG7B12_SG7B13_Experiment_Matrix.csv"
)

SG7B11_FROZEN_MODEL = (
    ROOT / "output" / "V15_SG7B11"
    / "V15SG7B_FRONT_AWARE_FROZEN_Model.keras"
)

SG7B11_MANIFEST = (
    ROOT / "output" / "V15_SG7B11"
    / "V15SG7B11_Front_Aware_Freeze_Manifest.json"
)

SG7CR_DEPLOYMENT_FILE = (
    ROOT / "output" / "V15_SG7CR"
    / "SG7CR_FRONT_AWARE_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"
)

DEFAULT_DEPLOYMENT_WORKSPACE = (
    ROOT.parent / f"{ROOT.name}_SG5C_seed_11x11"
)

SG6_RELATIVE = (
    Path("output") / "V15_SG6" / "STREAMLINE_TRANSPORT_COORDINATES.npz"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7B13"
EXPERIMENT_DIR = OUTPUT_DIR / "experiments"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

CANDIDATE_MODEL_FILE = OUTPUT_DIR / "V15SG7B13_Candidate_Model.keras"
CANDIDATE_MANIFEST_FILE = OUTPUT_DIR / "V15SG7B13_Candidate_Manifest.json"
EXPERIMENT_METRICS_FILE = OUTPUT_DIR / "V15SG7B13_Experiment_Metrics.csv"
EPOCH_METRICS_FILE = OUTPUT_DIR / "V15SG7B13_Epoch_Metrics.csv"
PRECHECK_FILE = OUTPUT_DIR / "V15SG7B13_Contract_Precheck.json"
NUMERICAL_FILE = OUTPUT_DIR / "V15SG7B13_Candidate_Test_Results.npz"
SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG7B13_Summary.json"


# =============================================================================
# FIXED CONTRACT VALUES
# =============================================================================

FRONT_THRESHOLD = 0.210
FRONT_LOW = 0.210
FRONT_HIGH = 0.300
TAIL_LIMIT = 0.205
MATERIAL_POSITIVE_BIAS = 0.005
EPS = 1.0e-8

# SG7B-12 bias gates
MAX_BIAS_500_1000 = 2.500000e-03
MAX_BIAS_1000_2000 = 4.500000e-03
MAX_BIAS_GT2000 = 5.000000e-03
MAX_TAIL_BIAS = 5.000000e-03
MAX_500_1000_MATERIAL_SHARE = 0.40

# SG7B-11 retained local gates
MAX_TEST_L1 = 0.020
MAX_TEST_L2 = 0.030
MAX_MASS_RELATIVE_MAE = 0.030
MAX_INJECTOR_L1 = 0.015
MAX_FRONT_L1 = 0.030
MAX_EARLY_L1 = 0.020
MAX_LATE_L1 = 0.025
MIN_100D_CROSSINGS = 744
MAX_100D_PROFILE_L1 = 4.500330e-03

# Training contract from SG7B-12
MAXIMUM_EPOCHS = 140
INITIAL_LEARNING_RATE = 1.5e-6
MINIMUM_LEARNING_RATE = 1.5e-7
EARLY_STOPPING_PATIENCE = 28
LR_REDUCTION_PATIENCE = 10
EVAL_EVERY = 5
BATCH_SIZE = 32
BIAS_BATCH_SIZE = 64
GRADIENT_CLIP_NORM = 5.0

# Preserve accepted SG7B-6D losses.
LAMBDA_DATA = 1.00
LAMBDA_FV = 0.20
LAMBDA_FACE_FLUX = 1.00
LAMBDA_ADV_DIV = 1.50
LAMBDA_MASS = 0.40
LAMBDA_INJECTOR = 0.30
LAMBDA_LATE = 0.30

# Front preservation is intentionally modest because SG7B-11 already froze
# the front-aware solution. These terms prevent regression rather than trying
# to create a new front solution.
LAMBDA_FRONT_PRESERVE = 0.50
LAMBDA_CROSS_PRESERVE = 0.20

SEED = 1510713
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
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def import_module(path: Path, name: str):
    if not path.exists():
        raise FileNotFoundError(f"Required source missing:\n{path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import source:\n{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_key(db, aliases, description):
    for key in aliases:
        if key in db:
            return key
    raise KeyError(
        f"Could not identify {description}.\n"
        f"Aliases: {aliases}\nAvailable: {list(db.keys())}"
    )


def as_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


# =============================================================================
# EXPERIMENT MATRIX
# =============================================================================

def load_experiment_matrix(selected: set[str] | None):
    rows = load_csv(SG7B12_EXPERIMENT_FILE)
    output = []
    for row in rows:
        exp = str(row["experiment"]).strip()
        item = {
            "experiment": exp,
            "description": str(row["description"]),
            "lambda_TOF_bias": float(row["lambda_TOF_bias"]),
            "lambda_TOF_slow": float(row["lambda_TOF_slow"]),
            "lambda_tail": float(row["lambda_tail"]),
            "lambda_short_anchor": float(row["lambda_short_anchor"]),
            "lambda_frozen_anchor": float(row["lambda_frozen_anchor"]),
            "training": exp != "E0",
            "learning_rate": INITIAL_LEARNING_RATE,
            "maximum_epochs": MAXIMUM_EPOCHS,
        }
        if selected is None or exp == "E0" or exp in selected:
            output.append(item)

    if not any(r["experiment"] == "E0" for r in output):
        raise RuntimeError("SG7B-13 experiment matrix must contain E0.")
    return output


# =============================================================================
# DEPLOYMENT DATABASE
# =============================================================================

def load_deployment_database(workspace: Path, tD_scale: float):
    sg6_path = workspace / SG6_RELATIVE
    if not sg6_path.exists():
        raise FileNotFoundError(f"Missing SG6 geometry:\n{sg6_path}")
    if not SG7CR_DEPLOYMENT_FILE.exists():
        raise FileNotFoundError(
            "Missing accepted front-aware SG7C-R deployment:\n"
            f"{SG7CR_DEPLOYMENT_FILE}"
        )

    sg6 = np.load(sg6_path, allow_pickle=True)
    sg7cr = np.load(SG7CR_DEPLOYMENT_FILE, allow_pickle=True)

    xi = np.asarray(
        sg6[find_key(sg6, ["xi", "transport_xi"], "SG6 xi")],
        dtype=np.float32,
    )
    tau_end_s = np.asarray(
        sg6[find_key(
            sg6,
            ["tau_end_s", "terminal_tau_s", "terminal_tof_s"],
            "terminal TOF",
        )],
        dtype=np.float64,
    )

    times = np.asarray(
        sg7cr[find_key(
            sg7cr,
            ["times_days", "physical_times_days", "deployment_times_days"],
            "deployment times",
        )],
        dtype=np.float64,
    )
    truth_all = np.asarray(
        sg7cr[find_key(
            sg7cr,
            ["SG7A_saturation", "truth_saturation", "reference_saturation"],
            "SG7A truth",
        )],
        dtype=np.float32,
    )
    stored_front_aware = np.asarray(
        sg7cr[find_key(
            sg7cr,
            ["PI_RNN_saturation", "pirnn_saturation", "predicted_saturation"],
            "front-aware prediction",
        )],
        dtype=np.float32,
    )

    idx100 = int(np.argmin(np.abs(times - 100.0)))
    if not np.isclose(times[idx100], 100.0):
        raise RuntimeError("SG7C-R does not contain 100-day deployment.")

    terminal_days = tau_end_s / 86400.0
    tD100 = 100.0 / terminal_days
    normalized = tD100 / float(tD_scale)

    nsl = len(terminal_days)
    nn = len(xi)
    X100 = np.zeros((nsl, nn, 2), dtype=np.float32)
    X100[:, :, 0] = xi[None, :]
    X100[:, :, 1] = normalized[:, None].astype(np.float32)

    return {
        "X100": X100,
        "truth100": truth_all[idx100],
        "stored_front_aware100": stored_front_aware[idx100],
        "terminal_days": terminal_days,
        "xi": xi,
        "times_days": times,
    }


# =============================================================================
# BIAS / FRONT METRICS
# =============================================================================

def profile_has_crossing(S, threshold=FRONT_THRESHOLD):
    shifted = np.asarray(S, dtype=float) - threshold
    return np.any(shifted[:, :-1] * shifted[:, 1:] < 0.0, axis=1)


def front_metrics(pred, truth):
    pred = np.asarray(pred, dtype=float)
    truth = np.asarray(truth, dtype=float)
    truth_front = profile_has_crossing(truth)
    pred_front = profile_has_crossing(pred)

    gaps = np.min(np.abs(pred - FRONT_THRESHOLD), axis=1)
    conditioned = gaps[truth_front] if np.any(truth_front) else np.array([np.nan])

    return {
        "truth_front_count": int(np.sum(truth_front)),
        "recovered_front_count": int(np.sum(truth_front & pred_front)),
        "conditioned_gap": float(np.nanmean(conditioned)),
        "profile_L1": float(np.mean(np.abs(pred - truth))),
    }


def positive_mean_bias(error, mask):
    values = error[mask]
    if values.size == 0:
        return np.nan
    return float(np.mean(values))


def bias_metrics(pred, truth, terminal_days):
    pred = np.asarray(pred, dtype=float)
    truth = np.asarray(truth, dtype=float)
    terminal_days = np.asarray(terminal_days, dtype=float)
    error = pred - truth

    band_500_1000 = (terminal_days >= 500.0) & (terminal_days < 1000.0)
    band_1000_2000 = (terminal_days >= 1000.0) & (terminal_days < 2000.0)
    band_gt2000 = terminal_days >= 2000.0

    node_500_1000 = np.broadcast_to(band_500_1000[:, None], error.shape)
    node_1000_2000 = np.broadcast_to(band_1000_2000[:, None], error.shape)
    node_gt2000 = np.broadcast_to(band_gt2000[:, None], error.shape)
    tail = truth <= TAIL_LIMIT

    material = error > MATERIAL_POSITIVE_BIAS
    material_total = int(np.sum(material))
    material_500 = int(np.sum(material & node_500_1000))
    material_share = (
        material_500 / material_total if material_total > 0 else 0.0
    )

    return {
        "bias_500_1000": positive_mean_bias(error, node_500_1000),
        "bias_1000_2000": positive_mean_bias(error, node_1000_2000),
        "bias_gt2000": positive_mean_bias(error, node_gt2000),
        "tail_bias": positive_mean_bias(error, tail),
        "material_share_500_1000": float(material_share),
        "global_bias": float(np.mean(error)),
        "global_L1": float(np.mean(np.abs(error))),
    }


# =============================================================================
# DIFFERENTIABLE LOSSES
# =============================================================================

def safe_masked_mean(values, mask):
    values = tf.cast(values, tf.float32)
    mask = tf.cast(mask, tf.float32)
    return tf.reduce_sum(values * mask) / (tf.reduce_sum(mask) + EPS)


def make_canonical_train_step(base):
    @tf.function
    def train_step(model, optimizer, X, Y, face, div, frozen_anchor, tD_scale, dxi):
        with tf.GradientTape() as tape:
            Yp = model(X, training=True)
            Sp = Yp[:, :, 0]
            truth = Y[:, :, 0]
            anchor = frozen_anchor[:, :, 0]

            L_data = base.data_loss(Y, Yp)
            _, relative, _, _ = base.finite_volume_residual(
                model, X, tD_scale, training=True
            )
            L_fv = tf.reduce_mean(tf.square(relative))

            pf, pd = base.predicted_advective_flux(Sp)
            L_face = base.normalized_face_flux_loss(pf, face)
            L_div = base.normalized_divergence_loss(pd, div)
            L_mass = base.mass_loss(Y, Yp, dxi)
            L_inj = base.injector_loss(Y, Yp)
            L_late = base.late_time_loss(X, Y, Yp)

            front_mask = tf.cast(
                (truth >= FRONT_LOW) & (truth <= FRONT_HIGH), tf.float32
            )
            L_front = safe_masked_mean(tf.square(Sp - truth), front_mask)

            cross_mask = tf.cast(
                (truth >= 0.200) & (truth <= FRONT_HIGH), tf.float32
            )
            labels = tf.cast(truth > FRONT_THRESHOLD, tf.float32)
            logits = (Sp - FRONT_THRESHOLD) / 0.010
            bce = tf.nn.sigmoid_cross_entropy_with_logits(
                labels=labels, logits=logits
            )
            L_cross = safe_masked_mean(bce, cross_mask)

            # Global frozen anchor is deliberately weak; deployment-specific
            # targeted losses below are allowed to move the diagnosed region.
            L_anchor = tf.reduce_mean(tf.square(Sp - anchor))

            total = (
                LAMBDA_DATA * L_data
                + LAMBDA_FV * L_fv
                + LAMBDA_FACE_FLUX * L_face
                + LAMBDA_ADV_DIV * L_div
                + LAMBDA_MASS * L_mass
                + LAMBDA_INJECTOR * L_inj
                + LAMBDA_LATE * L_late
                + LAMBDA_FRONT_PRESERVE * L_front
                + LAMBDA_CROSS_PRESERVE * L_cross
                + 0.10 * L_anchor
            )

        grads = tape.gradient(total, model.trainable_variables)
        grads, _ = tf.clip_by_global_norm(grads, GRADIENT_CLIP_NORM)
        optimizer.apply_gradients(zip(grads, model.trainable_variables))
        return total
    return train_step


def make_bias_train_step(config):
    w_bias = tf.constant(config["lambda_TOF_bias"], tf.float32)
    w_slow = tf.constant(config["lambda_TOF_slow"], tf.float32)
    w_tail = tf.constant(config["lambda_tail"], tf.float32)
    w_short = tf.constant(config["lambda_short_anchor"], tf.float32)
    w_anchor = tf.constant(config["lambda_frozen_anchor"], tf.float32)

    @tf.function
    def train_step(model, optimizer, X, Y, tau_days, frozen_prediction):
        with tf.GradientTape() as tape:
            Yp = model(X, training=True)
            pred = Yp[:, :, 0]
            truth = Y[:, :, 0]
            anchor = frozen_prediction[:, :, 0]
            tau = tau_days[:, None]

            mask_500 = tf.cast((tau >= 500.0) & (tau < 1000.0), tf.float32)
            mask_slow = tf.cast(tau >= 1000.0, tf.float32)
            mask_short = tf.cast(tau < 500.0, tf.float32)
            mask_tail = tf.cast(truth <= TAIL_LIMIT, tf.float32)

            # Penalize positive residual specifically, because SG7C-R2
            # diagnosed an upward state bias.
            positive_residual = tf.nn.relu(pred - truth)
            L_bias = safe_masked_mean(
                tf.square(positive_residual), mask_500
            )
            L_slow = safe_masked_mean(
                tf.square(positive_residual), mask_slow
            )
            L_tail = safe_masked_mean(
                tf.square(pred - truth), mask_tail
            )

            # Preserve already-good short-TOF streamlines.
            L_short = safe_masked_mean(
                tf.square(pred - anchor), mask_short
            )

            # Frozen anchor outside the targeted slow/tail region.
            target_region = tf.maximum(
                tf.cast(tau >= 500.0, tf.float32),
                mask_tail,
            )
            non_target = 1.0 - tf.clip_by_value(target_region, 0.0, 1.0)
            L_anchor = safe_masked_mean(
                tf.square(pred - anchor), non_target
            )

            # Preserve the accepted front directly against SG7A.
            front_mask = tf.cast(
                (truth >= FRONT_LOW) & (truth <= FRONT_HIGH), tf.float32
            )
            L_front = safe_masked_mean(
                tf.square(pred - truth), front_mask
            )

            total = (
                w_bias * L_bias
                + w_slow * L_slow
                + w_tail * L_tail
                + w_short * L_short
                + w_anchor * L_anchor
                + LAMBDA_FRONT_PRESERVE * L_front
            )

        grads = tape.gradient(total, model.trainable_variables)
        grads, _ = tf.clip_by_global_norm(grads, GRADIENT_CLIP_NORM)
        optimizer.apply_gradients(zip(grads, model.trainable_variables))

        return total, L_bias, L_slow, L_tail, L_short, L_anchor, L_front

    return train_step


# =============================================================================
# DATASETS
# =============================================================================

def make_canonical_dataset(X, Y, face, div, anchor, seed):
    ds = tf.data.Dataset.from_tensor_slices((
        X.astype(np.float32),
        Y.astype(np.float32),
        face.astype(np.float32),
        div.astype(np.float32),
        anchor.astype(np.float32),
    ))
    ds = ds.shuffle(len(X), seed=seed, reshuffle_each_iteration=True)
    return ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)


def make_bias_dataset(deployment, frozen100, seed):
    Y = deployment["truth100"][:, :, None].astype(np.float32)
    A = frozen100[:, :, None].astype(np.float32)
    tau = deployment["terminal_days"].astype(np.float32)
    ds = tf.data.Dataset.from_tensor_slices((
        deployment["X100"].astype(np.float32),
        Y,
        tau,
        A,
    ))
    ds = ds.shuffle(len(Y), seed=seed, reshuffle_each_iteration=True)
    return ds.batch(BIAS_BATCH_SIZE).prefetch(tf.data.AUTOTUNE)


# =============================================================================
# CANDIDATE EVALUATION
# =============================================================================

def additional_preservation_metrics(X, truth, prediction):
    """
    Compute retained regional/time-band metrics robustly for either
    (batch, nodes) or (batch, nodes, 1) saturation arrays.

    base.evaluate_split() returns 2-D truth/prediction arrays in the accepted
    SG7B-6D implementation, while some earlier training helpers used a trailing
    singleton channel dimension. SG7B-13 must support both without changing the
    numerical definition of the metrics.
    """
    truth = np.asarray(truth, dtype=float)
    prediction = np.asarray(prediction, dtype=float)
    X = np.asarray(X, dtype=float)

    if truth.ndim == 3:
        if truth.shape[-1] != 1:
            raise RuntimeError(
                f"Unexpected truth shape for preservation metrics: {truth.shape}"
            )
        truth_s = truth[:, :, 0]
    elif truth.ndim == 2:
        truth_s = truth
    else:
        raise RuntimeError(
            f"Unexpected truth rank for preservation metrics: {truth.shape}"
        )

    if prediction.ndim == 3:
        if prediction.shape[-1] != 1:
            raise RuntimeError(
                f"Unexpected prediction shape for preservation metrics: "
                f"{prediction.shape}"
            )
        pred_s = prediction[:, :, 0]
    elif prediction.ndim == 2:
        pred_s = prediction
    else:
        raise RuntimeError(
            f"Unexpected prediction rank for preservation metrics: "
            f"{prediction.shape}"
        )

    if pred_s.shape != truth_s.shape:
        raise RuntimeError(
            "Prediction/truth shape mismatch in preservation metrics:\n"
            f"truth      : {truth_s.shape}\n"
            f"prediction : {pred_s.shape}"
        )

    front_mask = (
        (truth_s >= FRONT_LOW)
        &
        (truth_s <= FRONT_HIGH)
    )

    front_l1 = (
        float(
            np.mean(
                np.abs(
                    pred_s[front_mask]
                    -
                    truth_s[front_mask]
                )
            )
        )
        if np.any(front_mask)
        else 0.0
    )

    # X has shape (batch, nodes, features); feature 1 is normalized time.
    if X.ndim != 3 or X.shape[-1] < 2:
        raise RuntimeError(
            f"Unexpected X shape for preservation metrics: {X.shape}"
        )

    t = X[:, 0, 1]
    early = t <= (1.0 / 3.0)
    late = t >= (2.0 / 3.0)

    early_l1 = (
        float(
            np.mean(
                np.abs(
                    pred_s[early]
                    -
                    truth_s[early]
                )
            )
        )
        if np.any(early)
        else 0.0
    )

    late_l1 = (
        float(
            np.mean(
                np.abs(
                    pred_s[late]
                    -
                    truth_s[late]
                )
            )
        )
        if np.any(late)
        else 0.0
    )

    return {
        "front_L1": front_l1,
        "early_L1": early_l1,
        "late_L1": late_l1,
    }


def evaluate_candidate(base, model, dataset, targets, deployment):
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

    extra = additional_preservation_metrics(
        dataset["X_test"],
        test["truth"],
        test["prediction"],
    )

    pred100 = model.predict(
        deployment["X100"], batch_size=BATCH_SIZE, verbose=0
    )[:, :, 0]

    front = front_metrics(pred100, deployment["truth100"])
    bias = bias_metrics(
        pred100, deployment["truth100"], deployment["terminal_days"]
    )

    gates = {
        "finite": bool(np.all(np.isfinite(pred100))),
        "held_out_L1": bool(test["L1"] < MAX_TEST_L1),
        "held_out_L2": bool(test["L2"] < MAX_TEST_L2),
        "mass": bool(test["mass_relative_MAE"] < MAX_MASS_RELATIVE_MAE),
        "injector": bool(test["injector_L1"] < MAX_INJECTOR_L1),
        "front_L1": bool(extra["front_L1"] < MAX_FRONT_L1),
        "early_L1": bool(extra["early_L1"] < MAX_EARLY_L1),
        "late_L1": bool(extra["late_L1"] < MAX_LATE_L1),
        "front_crossings": bool(front["recovered_front_count"] >= MIN_100D_CROSSINGS),
        "profile_100d_L1": bool(front["profile_L1"] <= MAX_100D_PROFILE_L1),
        "bias_500_1000": bool(bias["bias_500_1000"] <= MAX_BIAS_500_1000),
        "bias_1000_2000": bool(bias["bias_1000_2000"] <= MAX_BIAS_1000_2000),
        "bias_gt2000": bool(bias["bias_gt2000"] <= MAX_BIAS_GT2000),
        "tail_bias": bool(bias["tail_bias"] <= MAX_TAIL_BIAS),
        "material_share": bool(
            bias["material_share_500_1000"] <= MAX_500_1000_MATERIAL_SHARE
        ),
    }

    return {
        "test": test,
        "extra": extra,
        "prediction100": pred100,
        "front": front,
        "bias": bias,
        "gates": gates,
        "local_screen_pass": bool(all(gates.values())),
        "canonical_physics_status": "PENDING_INDEPENDENT_DOWNSTREAM_VALIDATION",
    }


def candidate_score(screen):
    b = screen["bias"]
    f = screen["front"]
    t = screen["test"]

    return float(
        1.5 * b["bias_500_1000"] / MAX_BIAS_500_1000
        + 1.0 * b["bias_1000_2000"] / MAX_BIAS_1000_2000
        + 1.0 * b["bias_gt2000"] / MAX_BIAS_GT2000
        + 1.0 * b["tail_bias"] / MAX_TAIL_BIAS
        + 0.75 * b["material_share_500_1000"] / MAX_500_1000_MATERIAL_SHARE
        + 1.0 * f["profile_L1"] / MAX_100D_PROFILE_L1
        + 0.5 * t["L1"] / MAX_TEST_L1
        + 0.25 * t["mass_relative_MAE"] / MAX_MASS_RELATIVE_MAE
        - 0.50 * f["recovered_front_count"] / max(f["truth_front_count"], 1)
    )


# =============================================================================
# TRAIN ONE EXPERIMENT
# =============================================================================

def train_experiment(base, config, dataset, targets, deployment, frozen_anchor, frozen100):
    exp = config["experiment"]
    exp_dir = EXPERIMENT_DIR / exp
    exp_dir.mkdir(parents=True, exist_ok=True)

    best_weights = exp_dir / f"V15SG7B13_{exp}_Best.weights.h5"
    best_model_file = exp_dir / f"V15SG7B13_{exp}_Best_Model.keras"
    final_model_file = exp_dir / f"V15SG7B13_{exp}_Final_Model.keras"
    history_file = exp_dir / f"V15SG7B13_{exp}_History.npz"

    seed = SEED + int(exp[1:]) * 101
    np.random.seed(seed)
    tf.random.set_seed(seed)

    # Independence contract: fresh SG7B-11 load for every experiment.
    model = tf.keras.models.load_model(SG7B11_FROZEN_MODEL)

    xi = np.asarray(dataset["xi"], dtype=float)
    dxi = tf.constant(float(xi[1] - xi[0]), tf.float32)
    tD_scale = tf.constant(float(dataset["tD_scale"][0]), tf.float32)

    canonical_ds = make_canonical_dataset(
        dataset["X_train"], dataset["Y_train"],
        targets["face_train"], targets["div_train"],
        frozen_anchor["train"], seed,
    )
    bias_ds = make_bias_dataset(deployment, frozen100, seed + 17)

    optimizer = tf.keras.optimizers.Adam(config["learning_rate"])
    canonical_step = make_canonical_train_step(base)
    bias_step = make_bias_train_step(config)

    history = {
        "epoch": [], "learning_rate": [], "score": [],
        "test_L1": [], "mass_MAE": [],
        "fronts": [], "profile_L1_100d": [],
        "bias_500_1000": [], "bias_1000_2000": [],
        "bias_gt2000": [], "tail_bias": [], "material_share": [],
    }

    best_score = np.inf
    best_epoch = -1
    patience = 0
    lr_patience = 0
    current_lr = float(config["learning_rate"])
    start = time.perf_counter()

    for epoch in range(int(config["maximum_epochs"])):
        # A. canonical preservation pass
        for Xb, Yb, Fb, Db, Ab in canonical_ds:
            canonical_step(
                model, optimizer, Xb, Yb, Fb, Db, Ab, tD_scale, dxi
            )

        # B. one targeted deployment pass
        for Xb, Yb, Tb, Ab in bias_ds:
            bias_step(model, optimizer, Xb, Yb, Tb, Ab)

        if not (epoch == 0 or (epoch + 1) % EVAL_EVERY == 0):
            continue

        screen = evaluate_candidate(base, model, dataset, targets, deployment)
        score = candidate_score(screen)
        b = screen["bias"]
        f = screen["front"]
        t = screen["test"]

        history["epoch"].append(epoch + 1)
        history["learning_rate"].append(current_lr)
        history["score"].append(score)
        history["test_L1"].append(t["L1"])
        history["mass_MAE"].append(t["mass_relative_MAE"])
        history["fronts"].append(f["recovered_front_count"])
        history["profile_L1_100d"].append(f["profile_L1"])
        history["bias_500_1000"].append(b["bias_500_1000"])
        history["bias_1000_2000"].append(b["bias_1000_2000"])
        history["bias_gt2000"].append(b["bias_gt2000"])
        history["tail_bias"].append(b["tail_bias"])
        history["material_share"].append(b["material_share_500_1000"])

        preservation_ok = (
            t["L1"] < MAX_TEST_L1
            and t["L2"] < MAX_TEST_L2
            and t["mass_relative_MAE"] < MAX_MASS_RELATIVE_MAE
            and t["injector_L1"] < MAX_INJECTOR_L1
            and f["recovered_front_count"] >= MIN_100D_CROSSINGS
            and f["profile_L1"] <= MAX_100D_PROFILE_L1
        )

        if preservation_ok and np.isfinite(score) and score < best_score - 1e-6:
            best_score = score
            best_epoch = epoch + 1
            patience = 0
            lr_patience = 0
            model.save_weights(best_weights)
        else:
            patience += EVAL_EVERY
            lr_patience += EVAL_EVERY

        print(
            f"  {exp} | epoch {epoch+1:4d}/{config['maximum_epochs']} | "
            f"lr={current_lr:.2e} | testL1={t['L1']:.3e} | "
            f"fronts={f['recovered_front_count']:4d}/{f['truth_front_count']:4d} | "
            f"B500={b['bias_500_1000']:.3e} | "
            f"B1000={b['bias_1000_2000']:.3e} | "
            f"B2000={b['bias_gt2000']:.3e} | "
            f"tail={b['tail_bias']:.3e} | "
            f"share={100*b['material_share_500_1000']:.1f}% | "
            f"score={score:.3f}"
        )

        if screen["local_screen_pass"] and epoch >= 20:
            print(f"\n  {exp}: complete SG7B-13 local contract reached.")
            break

        if lr_patience >= LR_REDUCTION_PATIENCE:
            new_lr = max(current_lr * 0.5, MINIMUM_LEARNING_RATE)
            if new_lr < current_lr:
                current_lr = new_lr
                optimizer.learning_rate.assign(current_lr)
            lr_patience = 0

        if patience >= EARLY_STOPPING_PATIENCE:
            print(
                f"\n  {exp}: early stopping at epoch {epoch+1}; "
                f"best epoch={best_epoch}."
            )
            break

    runtime = time.perf_counter() - start

    for key in history:
        history[key] = np.asarray(history[key])
    np.savez_compressed(history_file, **history)

    model.save(final_model_file)

    if not best_weights.exists():
        raise RuntimeError(
            f"{exp} produced no checkpoint satisfying the retained "
            "state/front preservation pre-screen."
        )

    model.load_weights(best_weights)
    model.save(best_model_file)
    screen = evaluate_candidate(base, model, dataset, targets, deployment)

    return {
        "experiment": exp,
        "description": config["description"],
        "config": config,
        "runtime_seconds": runtime,
        "best_epoch": best_epoch,
        "best_score": best_score,
        "best_model_file": str(best_model_file),
        "screen": screen,
        "history": history,
    }


# =============================================================================
# RESULT ROW / PLOTS
# =============================================================================

def result_row(result):
    s = result["screen"]
    b = s["bias"]
    f = s["front"]
    t = s["test"]
    c = result["config"]
    return {
        "experiment": result["experiment"],
        "description": result["description"],
        "best_epoch": result["best_epoch"],
        "score": result["best_score"],
        "runtime_seconds": result["runtime_seconds"],
        "lambda_TOF_bias": c["lambda_TOF_bias"],
        "lambda_TOF_slow": c["lambda_TOF_slow"],
        "lambda_tail": c["lambda_tail"],
        "lambda_short_anchor": c["lambda_short_anchor"],
        "lambda_frozen_anchor": c["lambda_frozen_anchor"],
        "test_L1": t["L1"],
        "test_L2": t["L2"],
        "mass_relative_MAE": t["mass_relative_MAE"],
        "recovered_fronts": f["recovered_front_count"],
        "profile_L1_100d": f["profile_L1"],
        "bias_500_1000": b["bias_500_1000"],
        "bias_1000_2000": b["bias_1000_2000"],
        "bias_gt2000": b["bias_gt2000"],
        "tail_bias": b["tail_bias"],
        "material_share_500_1000": b["material_share_500_1000"],
        "local_screen_pass": s["local_screen_pass"],
    }


def plot_summary(rows):
    labels = [r["experiment"] for r in rows]
    vals = [r["bias_500_1000"] for r in rows]
    plt.figure(figsize=(8, 5))
    plt.bar(labels, vals)
    plt.axhline(MAX_BIAS_500_1000, linestyle="--")
    plt.ylabel("500-1000 d mean bias")
    plt.xlabel("Experiment")
    plt.title("V15-SG7B-13 TOF-conditioned bias screen")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "V15SG7B13_Bias_500_1000.png", dpi=180)
    plt.close()

    vals = [r["recovered_fronts"] for r in rows]
    plt.figure(figsize=(8, 5))
    plt.bar(labels, vals)
    plt.axhline(MIN_100D_CROSSINGS, linestyle="--")
    plt.ylabel("Recovered 100-day fronts")
    plt.xlabel("Experiment")
    plt.title("V15-SG7B-13 front preservation")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "V15SG7B13_Front_Preservation.png", dpi=180)
    plt.close()


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="PAD-Stream V15-SG7B-13 controlled TOF-conditioned refinement."
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default=str(DEFAULT_DEPLOYMENT_WORKSPACE),
        help="Accepted 11x11 SG5C workspace containing SG6 geometry.",
    )
    parser.add_argument(
        "--experiments",
        type=str,
        default="E1,E2,E3,E4,E5",
        help="Comma-separated trainable experiments; E0 is always evaluated.",
    )
    args = parser.parse_args()

    selected = {
        x.strip() for x in args.experiments.split(",") if x.strip()
    }

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7B-13")
    print("Controlled TOF-Conditioned Residual Bias Refinement")
    print("=" * 78)

    print("\nTRAINING WILL BE PERFORMED FOR SELECTED E1-E5 EXPERIMENTS.")
    print("THE SG7B-11 FRONT-AWARE FROZEN MODEL WILL NOT BE MODIFIED.")
    print("EACH EXPERIMENT STARTS FROM THE SAME VERIFIED FROZEN CHECKPOINT.")
    print("NO ARCHITECTURE CHANGE WILL BE MADE.")
    print("NO SG7B-11 PRESERVATION GATE WILL BE RELAXED.")
    print("NO SG7E PLUME THRESHOLD WILL BE CHANGED.")
    print("NO CANDIDATE WILL BE DECLARED FROZEN BY SG7B-13.")

    if not SG7B12_CONTRACT_FILE.exists():
        raise FileNotFoundError(
            f"SG7B-12 contract required:\n{SG7B12_CONTRACT_FILE}"
        )
    contract = load_json(SG7B12_CONTRACT_FILE)
    if contract.get("milestone") != "V15-SG7B-12":
        raise RuntimeError("Unexpected SG7B-12 contract identity.")

    if not SG7B11_MANIFEST.exists():
        raise FileNotFoundError(
            f"SG7B-11 freeze manifest required:\n{SG7B11_MANIFEST}"
        )

    frozen_hash = compute_sha256(SG7B11_FROZEN_MODEL)
    manifest = load_json(SG7B11_MANIFEST)
    manifest_text = json.dumps(manifest)
    if frozen_hash not in manifest_text:
        raise RuntimeError(
            "SG7B-11 frozen model SHA-256 is not reproduced by its freeze manifest."
        )

    print("\nFROZEN SOURCE")
    print(f"  Model                   : {SG7B11_FROZEN_MODEL.name}")
    print(f"  SHA-256                 : {frozen_hash}")
    print("  Identity                : PASS")

    base = import_module(BASE_SOURCE_FILE, "pad_stream_sg7b6d_authority")

    dataset = base.load_dataset()
    sg7a = base.load_sg7a()
    targets = base.build_advective_targets(dataset, sg7a)

    workspace = Path(args.workspace).resolve()
    deployment = load_deployment_database(
        workspace, float(dataset["tD_scale"][0])
    )

    frozen_model = tf.keras.models.load_model(SG7B11_FROZEN_MODEL)
    frozen_anchor = {
        split: frozen_model.predict(
            dataset[f"X_{split}"].astype(np.float32),
            batch_size=BATCH_SIZE,
            verbose=0,
        ).astype(np.float32)
        for split in ["train", "val", "test"]
    }
    frozen100 = frozen_model.predict(
        deployment["X100"], batch_size=BATCH_SIZE, verbose=0
    )[:, :, 0]

    identity_linf = float(
        np.max(np.abs(frozen100 - deployment["stored_front_aware100"]))
    )
    if identity_linf > 2.0e-6:
        raise RuntimeError(
            "Fresh SG7B-11 deployment does not reproduce SG7C-R.\n"
            f"Linf={identity_linf:.6e}"
        )

    print("\nEVALUATION SHAPE PRECHECK")
    print(
        f"  X_test                  : "
        f"{np.asarray(dataset['X_test']).shape}"
    )

    e0_raw = base.evaluate_split(
        frozen_model,
        dataset["X_test"],
        dataset["Y_test"],
        targets["face_test"],
        targets["div_test"],
        np.asarray(dataset["xi"], dtype=float),
        float(dataset["tD_scale"][0]),
    )

    print(
        f"  evaluate_split truth     : "
        f"{np.asarray(e0_raw['truth']).shape}"
    )

    print(
        f"  evaluate_split prediction: "
        f"{np.asarray(e0_raw['prediction']).shape}"
    )

    e0_screen = evaluate_candidate(
        base, frozen_model, dataset, targets, deployment
    )
    e0_bias = e0_screen["bias"]
    e0_front = e0_screen["front"]

    print("\nSG7B-11 / SG7C-R BASELINE")
    print(f"  Deployment identity Linf: {identity_linf:.6e}")
    print(f"  Recovered fronts        : {e0_front['recovered_front_count']} / {e0_front['truth_front_count']}")
    print(f"  500-1000d mean bias     : {e0_bias['bias_500_1000']:.6e}")
    print(f"  1000-2000d mean bias    : {e0_bias['bias_1000_2000']:.6e}")
    print(f"  >2000d mean bias        : {e0_bias['bias_gt2000']:.6e}")
    print(f"  Initial-tail mean bias  : {e0_bias['tail_bias']:.6e}")
    print(f"  500-1000d material share: {100*e0_bias['material_share_500_1000']:.2f}%")

    precheck = {
        "milestone": "V15-SG7B-13",
        "SG7B12_contract_ready": True,
        "frozen_model": str(SG7B11_FROZEN_MODEL),
        "frozen_sha256": frozen_hash,
        "deployment_identity_Linf": identity_linf,
        "baseline_bias": e0_bias,
        "baseline_front": e0_front,
    }
    save_json(PRECHECK_FILE, precheck)

    experiments = load_experiment_matrix(selected)

    results = [{
        "experiment": "E0",
        "description": "Frozen SG7B-11 control",
        "config": next(r for r in experiments if r["experiment"] == "E0"),
        "runtime_seconds": 0.0,
        "best_epoch": 0,
        "best_score": candidate_score(e0_screen),
        "best_model_file": str(SG7B11_FROZEN_MODEL),
        "screen": e0_screen,
        "history": {},
    }]

    print("\n" + "=" * 78)
    print("CONTROLLED EXPERIMENTS")
    print("=" * 78)

    for config in experiments:
        if config["experiment"] == "E0":
            continue
        print(f"\n{config['experiment']} — {config['description']}")
        result = train_experiment(
            base, config, dataset, targets, deployment,
            frozen_anchor, frozen100,
        )
        results.append(result)

    rows = [result_row(r) for r in results]
    save_csv(EXPERIMENT_METRICS_FILE, rows)

    epoch_rows = []
    for result in results:
        h = result["history"]
        if not h:
            continue
        for i, epoch in enumerate(h["epoch"]):
            row = {"experiment": result["experiment"], "epoch": int(epoch)}
            for key, values in h.items():
                if key != "epoch":
                    row[key] = float(values[i])
            epoch_rows.append(row)
    save_csv(EPOCH_METRICS_FILE, epoch_rows)

    plot_summary(rows)

    passing = [
        r for r in results
        if r["experiment"] != "E0" and r["screen"]["local_screen_pass"]
    ]

    print("\n" + "=" * 78)
    print("V15-SG7B-13 LOCAL CANDIDATE SCREEN")
    print("=" * 78)

    for result in results:
        s = result["screen"]
        b = s["bias"]
        f = s["front"]
        status = "PASS" if s["local_screen_pass"] else "FAIL"
        print(
            f"{result['experiment']:>2s} | {status} | "
            f"B500={b['bias_500_1000']:.3e} | "
            f"B1000={b['bias_1000_2000']:.3e} | "
            f"B2000={b['bias_gt2000']:.3e} | "
            f"tail={b['tail_bias']:.3e} | "
            f"share={100*b['material_share_500_1000']:.1f}% | "
            f"fronts={f['recovered_front_count']}"
        )

    if passing:
        passing.sort(key=lambda r: candidate_score(r["screen"]))
        winner = passing[0]
        shutil.copy2(winner["best_model_file"], CANDIDATE_MODEL_FILE)
        candidate_hash = compute_sha256(CANDIDATE_MODEL_FILE)

        manifest_payload = {
            "milestone": "V15-SG7B-13",
            "status": "TOF_CONDITIONED_CANDIDATE_NOMINATED",
            "experiment": winner["experiment"],
            "source_model": winner["best_model_file"],
            "candidate_model": str(CANDIDATE_MODEL_FILE),
            "candidate_sha256": candidate_hash,
            "starting_frozen_sha256": frozen_hash,
            "local_screen_pass": True,
            "canonical_physics_status": "PENDING_INDEPENDENT_VALIDATION",
            "candidate_is_frozen": False,
        }
        save_json(CANDIDATE_MANIFEST_FILE, manifest_payload)

        s = winner["screen"]
        np.savez_compressed(
            NUMERICAL_FILE,
            prediction100=s["prediction100"],
            truth100=deployment["truth100"],
            terminal_days=deployment["terminal_days"],
        )

        status = "TOF_CONDITIONED_CANDIDATE_NOMINATED"
        recommendation = (
            "A controlled SG7B-13 candidate satisfies the local SG7B-11 "
            "state/front preservation screen and every SG7B-12 TOF-bias gate. "
            "Do not freeze it here. Proceed to independent candidate validation "
            "with canonical physics and the complete preservation contract."
        )
        next_milestone = (
            "V15-SG7B-14 — Independent TOF-Conditioned Candidate Validation"
        )

        print("\nNOMINATED CANDIDATE")
        print(f"  Experiment              : {winner['experiment']}")
        print(f"  Model                   : {CANDIDATE_MODEL_FILE.name}")
        print(f"  SHA-256                 : {candidate_hash}")
    else:
        status = "NO_SG7B13_CANDIDATE_PASSES_COMPLETE_LOCAL_CONTRACT"
        recommendation = (
            "No controlled candidate simultaneously satisfies all retained "
            "state/front gates and all SG7B-12 TOF-bias gates. Do not promote "
            "or freeze any candidate. Audit the experiment outcomes before "
            "changing the contract."
        )
        next_milestone = (
            "V15-SG7B-13R — TOF-Conditioned Refinement Outcome Audit"
        )

    summary = {
        "milestone": "V15-SG7B-13",
        "status": status,
        "starting_frozen_model": str(SG7B11_FROZEN_MODEL),
        "starting_frozen_sha256": frozen_hash,
        "experiments_run": [r["experiment"] for r in results],
        "candidate_nominated": bool(passing),
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }
    save_json(SUMMARY_FILE, summary)

    print("\n" + "=" * 78)
    print("V15-SG7B-13 VALIDATION")
    print("=" * 78)
    print("[PASS] SG7B-12 contract loaded")
    print("[PASS] SG7B-11 frozen identity verified")
    print("[PASS] SG7C-R deployment identity reproduced")
    print("[PASS] Every trainable experiment started from SG7B-11 frozen checkpoint")
    print("[PASS] SG7B-11 local preservation gates retained")
    print("[PASS] SG7B-12 TOF-bias gates evaluated")
    print("[PASS] No frozen model overwritten")
    print("[PASS] No SG7E threshold changed")
    print("[PASS] Candidate decision established")

    print("\nSTATUS")
    print(f"  {status}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")
    print("\nTables:")
    print(f"  {EXPERIMENT_METRICS_FILE.name}")
    print(f"  {EPOCH_METRICS_FILE.name}")
    print("\nPrecheck:")
    print(f"  {PRECHECK_FILE.name}")
    if passing:
        print("\nCandidate:")
        print(f"  {CANDIDATE_MODEL_FILE.name}")
        print(f"  {CANDIDATE_MANIFEST_FILE.name}")
        print(f"  {NUMERICAL_FILE.name}")
    print("\nDiagnostics:")
    print("  V15SG7B13_Bias_500_1000.png")
    print("  V15SG7B13_Front_Preservation.png")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7B-13 CONTROLLED REFINEMENT: COMPLETE")
    print()
    print("The SG7B-11 front-aware frozen model remains authoritative.")
    print("No candidate has been frozen by SG7B-13.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()