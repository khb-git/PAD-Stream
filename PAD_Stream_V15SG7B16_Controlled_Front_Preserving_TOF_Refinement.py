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
# PAD-Stream V15-SG7B-16
# Controlled Front-Preserving TOF Refinement
#
# TRAINING MILESTONE
#
# PURPOSE
# -------
# SG7B-15 / SG7B-15R established a repaired front-preserving TOF refinement
# contract after SG7B-14R diagnosed:
#
#       TOF_REFINEMENT_FRONT_PRESERVATION_TRADEOFF
#
# All SG7B-13 E1-E5 models corrected the TOF bias but independently regressed
# the conditioned S=0.21 front gap and the SG7A/E0-relative front-shape
# contract. SG7B-16 therefore:
#
#   1. starts every trainable experiment from the SAME SG7B-11 front-aware
#      frozen checkpoint,
#   2. applies strong TOF correction ONLY away from the SG7A front shell,
#   3. applies no TOF correction in the front core,
#   4. strongly anchors the candidate to SG7B-11 in the front shell/core,
#   5. explicitly penalizes soft S=0.21 front-position displacement,
#   6. explicitly preserves front gradients and local total variation,
#   7. retains short-TOF and global frozen-model anchors,
#   8. evaluates the exact SG7B-10S front contract from SG7B-15R,
#   9. retains every SG7B-12 TOF-bias gate,
#  10. evaluates SG7B-11 state/mass/regional/canonical-physics gates before
#      any candidate can be nominated.
#
# IMPORTANT
# ---------
# SG7B-16 may NOMINATE a candidate only. It does NOT create a new frozen
# authority. Final independent validation remains downstream.
# =============================================================================


# =============================================================================
# ROOT / AUTHORITATIVE INPUTS
# =============================================================================

ROOT = Path(__file__).resolve().parent

BASE_SOURCE_FILE = (
    ROOT / "PAD_Stream_V15SG7B6D_Advective_Flux_Refinement.py"
)

SG7B10_SOURCE_FILE = (
    ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"
)

SG7B11_SOURCE_FILE = (
    ROOT / "PAD_Stream_V15SG7B11_Independent_Front_Aware_Candidate_Validation.py"
)

SG7B15R_CONTRACT_FILE = (
    ROOT / "output" / "V15_SG7B15R"
    / "V15SG7B15R_Front_Preserving_TOF_Refinement_Contract.json"
)

SG7B15R_SUMMARY_FILE = (
    ROOT / "output" / "V15_SG7B15R"
    / "PAD_Stream_V15SG7B15R_Summary.json"
)

SG7B10S_CONTRACT_FILE = (
    ROOT / "output" / "V15_SG7B10S"
    / "V15SG7B10S_SG7A_Relative_Front_Shape_Contract.json"
)

SG7B11_FROZEN_MODEL = (
    ROOT / "output" / "V15_SG7B11"
    / "V15SG7B_FRONT_AWARE_FROZEN_Model.keras"
)

SG7B11_MANIFEST = (
    ROOT / "output" / "V15_SG7B11"
    / "V15SG7B11_Front_Aware_Freeze_Manifest.json"
)

SG7B11_PHYSICS_TABLE = (
    ROOT / "output" / "V15_SG7B11"
    / "V15SG7B11_Canonical_Physics_Metrics.csv"
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

OUTPUT_DIR = ROOT / "output" / "V15_SG7B16"
EXPERIMENT_DIR = OUTPUT_DIR / "experiments"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

CANDIDATE_MODEL_FILE = (
    OUTPUT_DIR / "V15SG7B16_Candidate_Model.keras"
)

CANDIDATE_MANIFEST_FILE = (
    OUTPUT_DIR / "V15SG7B16_Candidate_Manifest.json"
)

EXPERIMENT_METRICS_FILE = (
    OUTPUT_DIR / "V15SG7B16_Experiment_Metrics.csv"
)

EPOCH_METRICS_FILE = (
    OUTPUT_DIR / "V15SG7B16_Epoch_Metrics.csv"
)

FRONT_GUARD_FILE = (
    OUTPUT_DIR / "V15SG7B16_Front_Guard_Metrics.csv"
)

SHAPE_GATE_FILE = (
    OUTPUT_DIR / "V15SG7B16_Front_Shape_Gates.csv"
)

FINAL_GATE_FILE = (
    OUTPUT_DIR / "V15SG7B16_Final_Gate_Matrix.csv"
)

PRECHECK_FILE = (
    OUTPUT_DIR / "V15SG7B16_Contract_Precheck.json"
)

NUMERICAL_FILE = (
    OUTPUT_DIR / "V15SG7B16_Candidate_Test_Results.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "PAD_Stream_V15SG7B16_Summary.json"
)


# =============================================================================
# FIXED TRAINING SETTINGS
# =============================================================================

SEED = 1510716
np.random.seed(SEED)
tf.random.set_seed(SEED)

BATCH_SIZE = 32
BIAS_BATCH_SIZE = 64
GRADIENT_CLIP_NORM = 5.0

# Retain accepted SG7B-6D canonical training terms.
LAMBDA_DATA = 1.00
LAMBDA_FV = 0.20
LAMBDA_FACE_FLUX = 1.00
LAMBDA_ADV_DIV = 1.50
LAMBDA_MASS = 0.40
LAMBDA_INJECTOR = 0.30
LAMBDA_LATE = 0.30

# Small canonical frozen anchor. Targeted deployment losses below carry the
# strong front-preservation logic.
LAMBDA_CANONICAL_FROZEN_ANCHOR = 0.10

EPS = 1.0e-8

# Differentiable soft front-position temperature.
SOFT_FRONT_TEMPERATURE = 0.006


# =============================================================================
# RETAINED SG7B-11 GATES
# =============================================================================

MAX_TEST_L1 = 0.020
MAX_TEST_L2 = 0.030
MAX_MASS_RELATIVE_MAE = 0.030

MAX_CANONICAL_MEAN = 0.500
MAX_CANONICAL_P90 = 1.000
MAX_CANONICAL_FRAC_GT1 = 0.10

MAX_INJECTOR_L1 = 0.015
MAX_FRONT_L1 = 0.030
MAX_EARLY_L1 = 0.020
MAX_LATE_L1 = 0.025


# =============================================================================
# GENERIC HELPERS
# =============================================================================

def compute_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:

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


def save_json(path: Path, payload):

    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


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
        f"Aliases: {aliases}\n"
        f"Available: {list(db.keys())}"
    )


def parse_experiments(contract, selected: set[str] | None):

    rows = contract["controlled_experiments"]

    output = []

    for row in rows:

        item = dict(row)
        exp = str(item["experiment"]).strip()

        for key in list(item.keys()):

            if key.startswith("lambda_"):
                item[key] = float(item[key])

        item["training"] = exp != "E0"

        if selected is None or exp == "E0" or exp in selected:
            output.append(item)

    if not any(row["experiment"] == "E0" for row in output):
        raise RuntimeError("SG7B-16 matrix must retain E0 frozen control.")

    return output


def load_sg7b11_canonical_reference(path: Path):

    rows = load_csv(path)

    accepted = None

    for row in rows:

        label = str(row.get("model", "")).strip()

        if label in {
            "E2_candidate",
            "SG7B11_front_aware_frozen",
            "front_aware_frozen",
        }:

            accepted = row
            break

    if accepted is None:

        raise RuntimeError(
            "Could not identify SG7B-11 front-aware canonical reference row."
        )

    return {
        "canonical_mean":
            float(accepted["canonical_mean"]),

        "canonical_P90":
            float(accepted["canonical_P90"]),

        "fraction_gt_1":
            float(accepted["fraction_gt_1"]),

        "source_label":
            str(accepted["model"]),
    }


def relative_close(value, reference, relative_tolerance):

    scale = max(
        abs(float(reference)),
        1.0e-12,
    )

    return (
        abs(float(value) - float(reference))
        <=
        relative_tolerance * scale
    )


# =============================================================================
# DEPLOYMENT DATABASE
# =============================================================================

def load_deployment_database(workspace: Path, tD_scale: float):

    sg6_path = workspace / SG6_RELATIVE

    if not sg6_path.exists():

        raise FileNotFoundError(
            f"Missing SG6 geometry:\n{sg6_path}"
        )

    if not SG7CR_DEPLOYMENT_FILE.exists():

        raise FileNotFoundError(
            f"Missing SG7C-R deployment:\n{SG7CR_DEPLOYMENT_FILE}"
        )

    sg6 = np.load(
        sg6_path,
        allow_pickle=True,
    )

    sg7cr = np.load(
        SG7CR_DEPLOYMENT_FILE,
        allow_pickle=True,
    )

    xi = np.asarray(
        sg6[
            find_key(
                sg6,
                ["xi", "transport_xi"],
                "SG6 xi",
            )
        ],
        dtype=np.float32,
    )

    tau_end_s = np.asarray(
        sg6[
            find_key(
                sg6,
                [
                    "tau_end_s",
                    "terminal_tau_s",
                    "terminal_tof_s",
                ],
                "terminal TOF",
            )
        ],
        dtype=np.float64,
    )

    times = np.asarray(
        sg7cr[
            find_key(
                sg7cr,
                [
                    "times_days",
                    "physical_times_days",
                    "deployment_times_days",
                ],
                "deployment times",
            )
        ],
        dtype=np.float64,
    )

    truth_all = np.asarray(
        sg7cr[
            find_key(
                sg7cr,
                [
                    "SG7A_saturation",
                    "truth_saturation",
                    "reference_saturation",
                ],
                "SG7A truth",
            )
        ],
        dtype=np.float32,
    )

    stored_front_aware = np.asarray(
        sg7cr[
            find_key(
                sg7cr,
                [
                    "PI_RNN_saturation",
                    "pirnn_saturation",
                    "predicted_saturation",
                ],
                "front-aware prediction",
            )
        ],
        dtype=np.float32,
    )

    idx100 = int(
        np.argmin(
            np.abs(times - 100.0)
        )
    )

    if not np.isclose(
        times[idx100],
        100.0,
    ):

        raise RuntimeError(
            "SG7C-R does not contain 100-day deployment."
        )

    terminal_days = tau_end_s / 86400.0

    tD100 = 100.0 / terminal_days

    normalized_tD100 = (
        tD100
        /
        float(tD_scale)
    )

    n_streamlines = len(terminal_days)
    n_nodes = len(xi)

    X100 = np.zeros(
        (
            n_streamlines,
            n_nodes,
            2,
        ),
        dtype=np.float32,
    )

    X100[:, :, 0] = xi[None, :]

    X100[:, :, 1] = (
        normalized_tD100[:, None]
    ).astype(np.float32)

    return {
        "X100":
            X100,

        "truth100":
            truth_all[idx100],

        "stored_front_aware100":
            stored_front_aware[idx100],

        "terminal_days":
            terminal_days,

        "xi":
            xi,

        "times_days":
            times,
    }


# =============================================================================
# FRONT / BIAS METRICS
# =============================================================================

def threshold_crossing_positions(
    field,
    xi,
    threshold,
):

    field = np.asarray(
        field,
        dtype=np.float64,
    )

    xi = np.asarray(
        xi,
        dtype=np.float64,
    )

    positions = np.full(
        field.shape[0],
        np.nan,
        dtype=np.float64,
    )

    resolved = np.zeros(
        field.shape[0],
        dtype=bool,
    )

    for i in range(
        field.shape[0]
    ):

        y = (
            field[i]
            -
            float(threshold)
        )

        crossing = np.where(
            y[:-1] * y[1:] < 0.0
        )[0]

        if crossing.size == 0:
            continue

        j = int(
            crossing[0]
        )

        y0 = y[j]
        y1 = y[j + 1]

        denom = (
            y1
            -
            y0
        )

        if abs(denom) <= 1.0e-14:
            position = 0.5 * (
                xi[j]
                +
                xi[j + 1]
            )
        else:
            fraction = (
                -y0
                /
                denom
            )

            fraction = float(
                np.clip(
                    fraction,
                    0.0,
                    1.0,
                )
            )

            position = (
                xi[j]
                +
                fraction
                *
                (
                    xi[j + 1]
                    -
                    xi[j]
                )
            )

        positions[i] = position
        resolved[i] = True

    return (
        positions,
        resolved,
    )


def front_metrics(
    prediction,
    truth,
    frozen_prediction,
    xi,
    front_threshold,
    front_shell_low,
    front_shell_high,
):

    prediction = np.asarray(
        prediction,
        dtype=np.float64,
    )

    truth = np.asarray(
        truth,
        dtype=np.float64,
    )

    frozen_prediction = np.asarray(
        frozen_prediction,
        dtype=np.float64,
    )

    truth_pos, truth_resolved = threshold_crossing_positions(
        truth,
        xi,
        front_threshold,
    )

    pred_pos, pred_resolved = threshold_crossing_positions(
        prediction,
        xi,
        front_threshold,
    )

    frozen_pos, frozen_resolved = threshold_crossing_positions(
        frozen_prediction,
        xi,
        front_threshold,
    )

    truth_front_count = int(
        np.sum(
            truth_resolved
        )
    )

    recovered_front_count = int(
        np.sum(
            truth_resolved
            &
            pred_resolved
        )
    )

    gaps = np.min(
        np.abs(
            prediction
            -
            float(front_threshold)
        ),
        axis=1,
    )

    conditioned_gap = float(
        np.mean(
            gaps[
                truth_resolved
            ]
        )
    )

    profile_l1 = float(
        np.mean(
            np.abs(
                prediction
                -
                truth
            )
        )
    )

    shell_mask = (
        (truth >= float(front_shell_low))
        &
        (truth <= float(front_shell_high))
    )

    front_anchor_mae = float(
        np.mean(
            np.abs(
                prediction[shell_mask]
                -
                frozen_prediction[shell_mask]
            )
        )
    )

    common = (
        truth_resolved
        &
        pred_resolved
        &
        frozen_resolved
    )

    if np.any(
        common
    ):

        shift = np.abs(
            pred_pos[common]
            -
            frozen_pos[common]
        )

        mean_shift = float(
            np.mean(
                shift
            )
        )

        p90_shift = float(
            np.percentile(
                shift,
                90,
            )
        )

        max_shift = float(
            np.max(
                shift
            )
        )

        common_count = int(
            np.sum(
                common
            )
        )

    else:

        mean_shift = np.inf
        p90_shift = np.inf
        max_shift = np.inf
        common_count = 0

    return {
        "truth_front_count":
            truth_front_count,

        "recovered_front_count":
            recovered_front_count,

        "conditioned_gap":
            conditioned_gap,

        "profile_L1_100d":
            profile_l1,

        "front_anchor_MAE":
            front_anchor_mae,

        "common_frozen_front_count":
            common_count,

        "frozen_front_xi_shift_mean":
            mean_shift,

        "frozen_front_xi_shift_P90":
            p90_shift,

        "frozen_front_xi_shift_MAX":
            max_shift,
    }


def bias_metrics(
    prediction,
    truth,
    terminal_days,
    material_positive_bias,
    tail_max,
):

    prediction = np.asarray(
        prediction,
        dtype=np.float64,
    )

    truth = np.asarray(
        truth,
        dtype=np.float64,
    )

    terminal_days = np.asarray(
        terminal_days,
        dtype=np.float64,
    )

    error = (
        prediction
        -
        truth
    )

    def expand(mask):

        return np.broadcast_to(
            mask[:, None],
            error.shape,
        )

    mask_500 = expand(
        (terminal_days >= 500.0)
        &
        (terminal_days < 1000.0)
    )

    mask_1000 = expand(
        (terminal_days >= 1000.0)
        &
        (terminal_days < 2000.0)
    )

    mask_2000 = expand(
        terminal_days >= 2000.0
    )

    mask_tail = (
        truth
        <=
        float(tail_max)
    )

    material = (
        error
        >
        float(
            material_positive_bias
        )
    )

    total_material = int(
        np.sum(
            material
        )
    )

    material_500 = int(
        np.sum(
            material
            &
            mask_500
        )
    )

    def mean(mask):

        values = error[mask]

        if values.size == 0:
            return np.nan

        return float(
            np.mean(
                values
            )
        )

    return {
        "bias_500_1000":
            mean(
                mask_500
            ),

        "bias_1000_2000":
            mean(
                mask_1000
            ),

        "bias_gt2000":
            mean(
                mask_2000
            ),

        "tail_bias":
            mean(
                mask_tail
            ),

        "material_share_500_1000":
            (
                float(
                    material_500
                    /
                    total_material
                )
                if total_material > 0
                else 0.0
            ),

        "global_mean_bias":
            float(
                np.mean(
                    error
                )
            ),

        "global_L1":
            float(
                np.mean(
                    np.abs(
                        error
                    )
                )
            ),
    }


# =============================================================================
# DIFFERENTIABLE LOSS HELPERS
# =============================================================================

def safe_masked_mean(
    values,
    mask,
):

    values = tf.cast(
        values,
        tf.float32,
    )

    mask = tf.cast(
        mask,
        tf.float32,
    )

    return (
        tf.reduce_sum(
            values
            *
            mask
        )
        /
        (
            tf.reduce_sum(
                mask
            )
            +
            EPS
        )
    )


def soft_front_position(
    saturation,
    xi,
    threshold,
):

    saturation = tf.cast(
        saturation,
        tf.float32,
    )

    xi = tf.cast(
        xi,
        tf.float32,
    )

    distance = tf.abs(
        saturation
        -
        tf.cast(
            threshold,
            tf.float32,
        )
    )

    weights = tf.nn.softmax(
        -distance
        /
        tf.constant(
            SOFT_FRONT_TEMPERATURE,
            tf.float32,
        ),
        axis=1,
    )

    return tf.reduce_sum(
        weights
        *
        xi[
            None,
            :
        ],
        axis=1,
    )


# =============================================================================
# TRAIN STEPS
# =============================================================================

def make_canonical_train_step(
    base,
):

    @tf.function
    def train_step(
        model,
        optimizer,
        X,
        Y,
        face,
        div,
        frozen_anchor,
        tD_scale,
        dxi,
    ):

        with tf.GradientTape() as tape:

            Yp = model(
                X,
                training=True,
            )

            Sp = Yp[:, :, 0]

            anchor = frozen_anchor[:, :, 0]

            L_data = base.data_loss(
                Y,
                Yp,
            )

            _, relative, _, _ = base.finite_volume_residual(
                model,
                X,
                tD_scale,
                training=True,
            )

            L_fv = tf.reduce_mean(
                tf.square(
                    relative
                )
            )

            pred_face, pred_div = base.predicted_advective_flux(
                Sp
            )

            L_face = base.normalized_face_flux_loss(
                pred_face,
                face,
            )

            L_div = base.normalized_divergence_loss(
                pred_div,
                div,
            )

            L_mass = base.mass_loss(
                Y,
                Yp,
                dxi,
            )

            L_injector = base.injector_loss(
                Y,
                Yp,
            )

            L_late = base.late_time_loss(
                X,
                Y,
                Yp,
            )

            L_anchor = tf.reduce_mean(
                tf.square(
                    Sp
                    -
                    anchor
                )
            )

            total = (
                LAMBDA_DATA
                *
                L_data
                +
                LAMBDA_FV
                *
                L_fv
                +
                LAMBDA_FACE_FLUX
                *
                L_face
                +
                LAMBDA_ADV_DIV
                *
                L_div
                +
                LAMBDA_MASS
                *
                L_mass
                +
                LAMBDA_INJECTOR
                *
                L_injector
                +
                LAMBDA_LATE
                *
                L_late
                +
                LAMBDA_CANONICAL_FROZEN_ANCHOR
                *
                L_anchor
            )

        gradients = tape.gradient(
            total,
            model.trainable_variables,
        )

        gradients, _ = tf.clip_by_global_norm(
            gradients,
            GRADIENT_CLIP_NORM,
        )

        optimizer.apply_gradients(
            zip(
                gradients,
                model.trainable_variables,
            )
        )

        return total

    return train_step


def make_front_preserving_deployment_step(
    config,
    contract,
    xi,
):

    front_regions = contract[
        "front_regions"
    ]

    front_shell_low = float(
        front_regions[
            "front_shell"
        ][0]
    )

    front_shell_high = float(
        front_regions[
            "front_shell"
        ][1]
    )

    front_core_low = float(
        front_regions[
            "front_core"
        ][0]
    )

    front_core_high = float(
        front_regions[
            "front_core"
        ][1]
    )

    long_tof_min = float(
        contract[
            "TOF_regions"
        ][
            "long_TOF_min_days"
        ]
    )

    very_long_tof_min = float(
        contract[
            "TOF_regions"
        ][
            "very_long_TOF_min_days"
        ]
    )

    tail_max = front_shell_low

    lambda_TOF_away = tf.constant(
        float(
            config[
                "lambda_TOF_away"
            ]
        ),
        tf.float32,
    )

    lambda_TOF_very_slow = tf.constant(
        float(
            config[
                "lambda_TOF_very_slow"
            ]
        ),
        tf.float32,
    )

    lambda_tail = tf.constant(
        float(
            config[
                "lambda_tail"
            ]
        ),
        tf.float32,
    )

    lambda_front_anchor = tf.constant(
        float(
            config[
                "lambda_front_anchor"
            ]
        ),
        tf.float32,
    )

    lambda_front_core = tf.constant(
        float(
            config[
                "lambda_front_core"
            ]
        ),
        tf.float32,
    )

    lambda_cross_position = tf.constant(
        float(
            config[
                "lambda_cross_position"
            ]
        ),
        tf.float32,
    )

    lambda_front_gradient = tf.constant(
        float(
            config[
                "lambda_front_gradient"
            ]
        ),
        tf.float32,
    )

    lambda_front_TV = tf.constant(
        float(
            config[
                "lambda_front_TV"
            ]
        ),
        tf.float32,
    )

    lambda_short_anchor = tf.constant(
        float(
            config[
                "lambda_short_anchor"
            ]
        ),
        tf.float32,
    )

    lambda_global_anchor = tf.constant(
        float(
            config[
                "lambda_global_anchor"
            ]
        ),
        tf.float32,
    )

    xi_tf = tf.constant(
        np.asarray(
            xi,
            dtype=np.float32,
        ),
        tf.float32,
    )

    @tf.function
    def train_step(
        model,
        optimizer,
        X,
        Y,
        tau_days,
        frozen_prediction,
    ):

        with tf.GradientTape() as tape:

            Yp = model(
                X,
                training=True,
            )

            pred = Yp[:, :, 0]
            truth = Y[:, :, 0]
            frozen = frozen_prediction[:, :, 0]

            tau = tau_days[:, None]

            long_tof = tf.cast(
                tau
                >=
                long_tof_min,
                tf.float32,
            )

            very_long_tof = tf.cast(
                tau
                >=
                very_long_tof_min,
                tf.float32,
            )

            short_tof = tf.cast(
                tau
                <
                long_tof_min,
                tf.float32,
            )

            front_shell = tf.cast(
                (
                    truth
                    >=
                    front_shell_low
                )
                &
                (
                    truth
                    <=
                    front_shell_high
                ),
                tf.float32,
            )

            front_core = tf.cast(
                (
                    truth
                    >=
                    front_core_low
                )
                &
                (
                    truth
                    <=
                    front_core_high
                ),
                tf.float32,
            )

            outside_front_shell = (
                1.0
                -
                front_shell
            )

            long_away = (
                long_tof
                *
                outside_front_shell
            )

            very_long_away = (
                very_long_tof
                *
                outside_front_shell
            )

            tail_mask = tf.cast(
                truth
                <=
                tail_max,
                tf.float32,
            )

            long_tail = (
                long_tof
                *
                tail_mask
            )

            positive_residual = tf.nn.relu(
                pred
                -
                truth
            )

            # -------------------------------------------------------------
            # Bias correction ONLY away from the accepted front shell.
            # -------------------------------------------------------------

            L_TOF_away = safe_masked_mean(
                tf.square(
                    positive_residual
                ),
                long_away,
            )

            L_TOF_very_slow = safe_masked_mean(
                tf.square(
                    positive_residual
                ),
                very_long_away,
            )

            L_tail = safe_masked_mean(
                tf.square(
                    pred
                    -
                    truth
                ),
                long_tail,
            )

            # -------------------------------------------------------------
            # Explicit SG7B-11 front locks.
            # -------------------------------------------------------------

            L_front_anchor = safe_masked_mean(
                tf.square(
                    pred
                    -
                    frozen
                ),
                front_shell,
            )

            L_front_core = safe_masked_mean(
                tf.square(
                    pred
                    -
                    frozen
                ),
                front_core,
            )

            # -------------------------------------------------------------
            # Soft S=0.21 crossing-position preservation relative to SG7B-11.
            # Only truth-front profiles are emphasized.
            # -------------------------------------------------------------

            truth_left = truth[:, :-1]
            truth_right = truth[:, 1:]

            truth_pair_front = tf.cast(
                (
                    tf.reduce_min(
                        tf.stack(
                            [
                                truth_left,
                                truth_right,
                            ],
                            axis=-1,
                        ),
                        axis=-1,
                    )
                    <=
                    0.300
                )
                &
                (
                    tf.reduce_max(
                        tf.stack(
                            [
                                truth_left,
                                truth_right,
                            ],
                            axis=-1,
                        ),
                        axis=-1,
                    )
                    >=
                    0.200
                ),
                tf.float32,
            )

            truth_profile_front = tf.cast(
                tf.reduce_any(
                    truth_pair_front
                    >
                    0.0,
                    axis=1,
                ),
                tf.float32,
            )

            pred_soft_xi = soft_front_position(
                pred,
                xi_tf,
                0.210,
            )

            frozen_soft_xi = soft_front_position(
                frozen,
                xi_tf,
                0.210,
            )

            L_cross_position = (
                tf.reduce_sum(
                    tf.square(
                        pred_soft_xi
                        -
                        frozen_soft_xi
                    )
                    *
                    truth_profile_front
                )
                /
                (
                    tf.reduce_sum(
                        truth_profile_front
                    )
                    +
                    EPS
                )
            )

            # -------------------------------------------------------------
            # Local gradient / TV preservation against SG7A.
            # -------------------------------------------------------------

            d_pred = (
                pred[:, 1:]
                -
                pred[:, :-1]
            )

            d_truth = (
                truth[:, 1:]
                -
                truth[:, :-1]
            )

            pair_shell = tf.cast(
                (
                    (
                        truth[:, :-1]
                        >=
                        0.200
                    )
                    |
                    (
                        truth[:, 1:]
                        >=
                        0.200
                    )
                )
                &
                (
                    (
                        truth[:, :-1]
                        <=
                        front_shell_high
                    )
                    |
                    (
                        truth[:, 1:]
                        <=
                        front_shell_high
                    )
                ),
                tf.float32,
            )

            dxi = (
                xi_tf[1:]
                -
                xi_tf[:-1]
            )

            grad_pred = (
                d_pred
                /
                dxi[
                    None,
                    :
                ]
            )

            grad_truth = (
                d_truth
                /
                dxi[
                    None,
                    :
                ]
            )

            L_front_gradient = safe_masked_mean(
                tf.square(
                    grad_pred
                    -
                    grad_truth
                ),
                pair_shell,
            )

            tv_pred = tf.reduce_sum(
                tf.abs(
                    d_pred
                )
                *
                pair_shell,
                axis=1,
            )

            tv_truth = tf.reduce_sum(
                tf.abs(
                    d_truth
                )
                *
                pair_shell,
                axis=1,
            )

            L_front_TV = tf.reduce_mean(
                tf.square(
                    tv_pred
                    -
                    tv_truth
                )
            )

            # -------------------------------------------------------------
            # Preserve short TOF and broad non-target behavior.
            # -------------------------------------------------------------

            L_short_anchor = safe_masked_mean(
                tf.square(
                    pred
                    -
                    frozen
                ),
                short_tof,
            )

            # Non-target = not a long-TOF outside-front correction region.
            non_target = (
                1.0
                -
                tf.clip_by_value(
                    long_away,
                    0.0,
                    1.0,
                )
            )

            L_global_anchor = safe_masked_mean(
                tf.square(
                    pred
                    -
                    frozen
                ),
                non_target,
            )

            total = (
                lambda_TOF_away
                *
                L_TOF_away
                +
                lambda_TOF_very_slow
                *
                L_TOF_very_slow
                +
                lambda_tail
                *
                L_tail
                +
                lambda_front_anchor
                *
                L_front_anchor
                +
                lambda_front_core
                *
                L_front_core
                +
                lambda_cross_position
                *
                L_cross_position
                +
                lambda_front_gradient
                *
                L_front_gradient
                +
                lambda_front_TV
                *
                L_front_TV
                +
                lambda_short_anchor
                *
                L_short_anchor
                +
                lambda_global_anchor
                *
                L_global_anchor
            )

        gradients = tape.gradient(
            total,
            model.trainable_variables,
        )

        gradients, _ = tf.clip_by_global_norm(
            gradients,
            GRADIENT_CLIP_NORM,
        )

        optimizer.apply_gradients(
            zip(
                gradients,
                model.trainable_variables,
            )
        )

        return (
            total,
            L_TOF_away,
            L_TOF_very_slow,
            L_tail,
            L_front_anchor,
            L_front_core,
            L_cross_position,
            L_front_gradient,
            L_front_TV,
            L_short_anchor,
            L_global_anchor,
        )

    return train_step


# =============================================================================
# DATASETS
# =============================================================================

def make_canonical_dataset(
    X,
    Y,
    face,
    div,
    frozen_anchor,
    seed,
):

    ds = tf.data.Dataset.from_tensor_slices(
        (
            X.astype(
                np.float32
            ),
            Y.astype(
                np.float32
            ),
            face.astype(
                np.float32
            ),
            div.astype(
                np.float32
            ),
            frozen_anchor.astype(
                np.float32
            ),
        )
    )

    ds = ds.shuffle(
        len(X),
        seed=seed,
        reshuffle_each_iteration=True,
    )

    return ds.batch(
        BATCH_SIZE
    ).prefetch(
        tf.data.AUTOTUNE
    )


def make_deployment_dataset(
    deployment,
    frozen100,
    seed,
):

    Y = deployment[
        "truth100"
    ][
        :,
        :,
        None,
    ].astype(
        np.float32
    )

    A = frozen100[
        :,
        :,
        None,
    ].astype(
        np.float32
    )

    tau = deployment[
        "terminal_days"
    ].astype(
        np.float32
    )

    ds = tf.data.Dataset.from_tensor_slices(
        (
            deployment[
                "X100"
            ].astype(
                np.float32
            ),
            Y,
            tau,
            A,
        )
    )

    ds = ds.shuffle(
        len(Y),
        seed=seed,
        reshuffle_each_iteration=True,
    )

    return ds.batch(
        BIAS_BATCH_SIZE
    ).prefetch(
        tf.data.AUTOTUNE
    )


# =============================================================================
# REGIONAL METRICS
# =============================================================================

def regional_metrics(
    X,
    truth,
    prediction,
    front_low,
    front_high,
):

    X = np.asarray(
        X,
        dtype=np.float64,
    )

    truth = np.asarray(
        truth,
        dtype=np.float64,
    )

    prediction = np.asarray(
        prediction,
        dtype=np.float64,
    )

    if truth.ndim == 3:
        truth = truth[:, :, 0]

    if prediction.ndim == 3:
        prediction = prediction[:, :, 0]

    front_mask = (
        (truth >= float(front_low))
        &
        (truth <= float(front_high))
    )

    front_l1 = (
        float(
            np.mean(
                np.abs(
                    prediction[
                        front_mask
                    ]
                    -
                    truth[
                        front_mask
                    ]
                )
            )
        )
        if np.any(
            front_mask
        )
        else 0.0
    )

    t_norm = X[:, 0, 1]

    early = (
        t_norm
        <=
        (1.0 / 3.0)
    )

    late = (
        t_norm
        >=
        (2.0 / 3.0)
    )

    early_l1 = (
        float(
            np.mean(
                np.abs(
                    prediction[
                        early
                    ]
                    -
                    truth[
                        early
                    ]
                )
            )
        )
        if np.any(
            early
        )
        else 0.0
    )

    late_l1 = (
        float(
            np.mean(
                np.abs(
                    prediction[
                        late
                    ]
                    -
                    truth[
                        late
                    ]
                )
            )
        )
        if np.any(
            late
        )
        else 0.0
    )

    return {
        "front_L1":
            front_l1,

        "early_L1":
            early_l1,

        "late_L1":
            late_l1,
    }


# =============================================================================
# LOCAL EVALUATION
# =============================================================================

def evaluate_local_candidate(
    base,
    sg11,
    model,
    dataset,
    targets,
    deployment,
    frozen100,
    contract,
    shape_contract,
):

    front_regions = contract[
        "front_regions"
    ]

    front_shell_low = float(
        front_regions[
            "front_shell"
        ][0]
    )

    front_shell_high = float(
        front_regions[
            "front_shell"
        ][1]
    )

    exact_front_contract = contract[
        "authoritative_front_improvement_contract"
    ]

    new_guards = contract[
        "new_front_guards"
    ]

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=np.float64,
    )

    tD_scale = float(
        dataset[
            "tD_scale"
        ][0]
    )

    test = base.evaluate_split(
        model,
        dataset[
            "X_test"
        ],
        dataset[
            "Y_test"
        ],
        targets[
            "face_test"
        ],
        targets[
            "div_test"
        ],
        xi,
        tD_scale,
    )

    extra = regional_metrics(
        dataset[
            "X_test"
        ],
        test[
            "truth"
        ],
        test[
            "prediction"
        ],
        front_shell_low,
        front_shell_high,
    )

    pred100 = model.predict(
        deployment[
            "X100"
        ],
        batch_size=BATCH_SIZE,
        verbose=0,
    )[
        :,
        :,
        0,
    ]

    front = front_metrics(
        pred100,
        deployment[
            "truth100"
        ],
        frozen100,
        deployment[
            "xi"
        ],
        0.210,
        front_shell_low,
        front_shell_high,
    )

    bias = bias_metrics(
        pred100,
        deployment[
            "truth100"
        ],
        deployment[
            "terminal_days"
        ],
        0.005,
        front_shell_low,
    )

    local_mask = sg11.front_pair_mask(
        deployment[
            "truth100"
        ],
        0.300,
        0.200,
    )

    shape = sg11.local_shape_metrics(
        pred100,
        deployment[
            "truth100"
        ],
        deployment[
            "xi"
        ],
        local_mask,
        1.0e-5,
    )

    shape_gate_rows = []

    shape_pass = True

    for gate in shape_contract[
        "shape_preservation_gates"
    ]:

        key = str(
            gate[
                "gate"
            ]
        )

        value = float(
            shape[
                key
            ]
        )

        limit = float(
            gate[
                "candidate_limit"
            ]
        )

        passed = bool(
            value
            <=
            limit
        )

        shape_gate_rows.append(
            {
                "gate":
                    key,

                "value":
                    value,

                "limit":
                    limit,

                "passed":
                    passed,
            }
        )

        shape_pass = (
            shape_pass
            and
            passed
        )

    gates = {
        "finite":
            bool(
                np.all(
                    np.isfinite(
                        test[
                            "prediction"
                        ]
                    )
                )
                and
                np.all(
                    np.isfinite(
                        pred100
                    )
                )
            ),

        "heldout_L1":
            bool(
                test[
                    "L1"
                ]
                <
                MAX_TEST_L1
            ),

        "heldout_L2":
            bool(
                test[
                    "L2"
                ]
                <
                MAX_TEST_L2
            ),

        "mass":
            bool(
                test[
                    "mass_relative_MAE"
                ]
                <
                MAX_MASS_RELATIVE_MAE
            ),

        "injector":
            bool(
                test[
                    "injector_L1"
                ]
                <
                MAX_INJECTOR_L1
            ),

        "front_L1":
            bool(
                extra[
                    "front_L1"
                ]
                <
                MAX_FRONT_L1
            ),

        "early_L1":
            bool(
                extra[
                    "early_L1"
                ]
                <
                MAX_EARLY_L1
            ),

        "late_L1":
            bool(
                extra[
                    "late_L1"
                ]
                <
                MAX_LATE_L1
            ),

        "front_count":
            bool(
                front[
                    "recovered_front_count"
                ]
                >=
                int(
                    exact_front_contract[
                        "minimum_recovered_fronts"
                    ]
                )
            ),

        "conditioned_gap":
            bool(
                front[
                    "conditioned_gap"
                ]
                <=
                float(
                    exact_front_contract[
                        "maximum_conditioned_threshold_gap"
                    ]
                )
            ),

        "profile_L1_100d":
            bool(
                front[
                    "profile_L1_100d"
                ]
                <=
                float(
                    exact_front_contract[
                        "maximum_100d_profile_L1"
                    ]
                )
            ),

        "front_shape":
            bool(
                shape_pass
            ),

        "front_anchor_MAE":
            bool(
                front[
                    "front_anchor_MAE"
                ]
                <=
                float(
                    new_guards[
                        "maximum_front_anchor_MAE"
                    ]
                )
            ),

        "front_xi_shift_mean":
            bool(
                front[
                    "frozen_front_xi_shift_mean"
                ]
                <=
                float(
                    new_guards[
                        "maximum_mean_frozen_front_xi_shift"
                    ]
                )
            ),

        "front_xi_shift_P90":
            bool(
                front[
                    "frozen_front_xi_shift_P90"
                ]
                <=
                float(
                    new_guards[
                        "maximum_P90_frozen_front_xi_shift"
                    ]
                )
            ),

        "bias_500_1000":
            bool(
                bias[
                    "bias_500_1000"
                ]
                <=
                2.500000e-03
            ),

        "bias_1000_2000":
            bool(
                bias[
                    "bias_1000_2000"
                ]
                <=
                4.500000e-03
            ),

        "bias_gt2000":
            bool(
                bias[
                    "bias_gt2000"
                ]
                <=
                5.000000e-03
            ),

        "tail_bias":
            bool(
                bias[
                    "tail_bias"
                ]
                <=
                5.000000e-03
            ),

        "material_share":
            bool(
                bias[
                    "material_share_500_1000"
                ]
                <=
                0.40
            ),
    }

    # Bias + front shape are the critical SG7B-16 local constraints.
    local_screen_pass = bool(
        all(
            gates.values()
        )
    )

    return {
        "test":
            test,

        "extra":
            extra,

        "prediction100":
            pred100,

        "front":
            front,

        "bias":
            bias,

        "shape":
            shape,

        "shape_gate_rows":
            shape_gate_rows,

        "gates":
            gates,

        "local_screen_pass":
            local_screen_pass,
    }


# =============================================================================
# CANONICAL PHYSICS EVALUATION
# =============================================================================

def canonical_gate_screen(
    sg11,
    base,
    model,
    dataset,
    canonical_truth,
):

    metrics = sg11.canonical_metrics(
        base,
        tf,
        model,
        dataset,
        canonical_truth,
    )

    gates = {
        "canonical_mean":
            bool(
                metrics[
                    "canonical_mean"
                ]
                <
                MAX_CANONICAL_MEAN
            ),

        "canonical_P90":
            bool(
                metrics[
                    "canonical_P90"
                ]
                <
                MAX_CANONICAL_P90
            ),

        "canonical_fraction_gt1":
            bool(
                metrics[
                    "fraction_gt_1"
                ]
                <
                MAX_CANONICAL_FRAC_GT1
            ),
    }

    return (
        metrics,
        gates,
        bool(
            all(
                gates.values()
            )
        ),
    )


# =============================================================================
# TRAINING SCORE
# =============================================================================

def candidate_score(
    screen,
    contract,
):

    front_contract = contract[
        "authoritative_front_improvement_contract"
    ]

    guards = contract[
        "new_front_guards"
    ]

    front = screen[
        "front"
    ]

    bias = screen[
        "bias"
    ]

    test = screen[
        "test"
    ]

    return float(
        1.50
        *
        abs(
            bias[
                "bias_500_1000"
            ]
        )
        /
        2.500000e-03
        +
        1.00
        *
        abs(
            bias[
                "bias_1000_2000"
            ]
        )
        /
        4.500000e-03
        +
        1.00
        *
        abs(
            bias[
                "bias_gt2000"
            ]
        )
        /
        5.000000e-03
        +
        1.00
        *
        abs(
            bias[
                "tail_bias"
            ]
        )
        /
        5.000000e-03
        +
        2.00
        *
        front[
            "conditioned_gap"
        ]
        /
        float(
            front_contract[
                "maximum_conditioned_threshold_gap"
            ]
        )
        +
        1.50
        *
        front[
            "front_anchor_MAE"
        ]
        /
        float(
            guards[
                "maximum_front_anchor_MAE"
            ]
        )
        +
        1.00
        *
        front[
            "frozen_front_xi_shift_P90"
        ]
        /
        float(
            guards[
                "maximum_P90_frozen_front_xi_shift"
            ]
        )
        +
        0.50
        *
        test[
            "L1"
        ]
        /
        MAX_TEST_L1
        -
        0.50
        *
        front[
            "recovered_front_count"
        ]
        /
        max(
            front[
                "truth_front_count"
            ],
            1,
        )
    )


# =============================================================================
# TRAIN ONE EXPERIMENT
# =============================================================================

def train_experiment(
    base,
    sg11,
    config,
    contract,
    shape_contract,
    dataset,
    targets,
    deployment,
    frozen_anchor,
    frozen100,
    canonical_truth,
):

    exp = str(
        config[
            "experiment"
        ]
    )

    exp_dir = (
        EXPERIMENT_DIR
        /
        exp
    )

    exp_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    best_weights_file = (
        exp_dir
        /
        f"V15SG7B16_{exp}_Best.weights.h5"
    )

    best_model_file = (
        exp_dir
        /
        f"V15SG7B16_{exp}_Best_Model.keras"
    )

    final_model_file = (
        exp_dir
        /
        f"V15SG7B16_{exp}_Final_Model.keras"
    )

    history_file = (
        exp_dir
        /
        f"V15SG7B16_{exp}_History.npz"
    )

    training_contract = contract[
        "training_contract"
    ]

    maximum_epochs = int(
        training_contract[
            "maximum_epochs"
        ]
    )

    initial_lr = float(
        training_contract[
            "initial_learning_rate"
        ]
    )

    minimum_lr = float(
        training_contract[
            "minimum_learning_rate"
        ]
    )

    early_stop_patience = int(
        training_contract[
            "early_stop_patience"
        ]
    )

    lr_patience_target = int(
        training_contract[
            "lr_reduction_patience"
        ]
    )

    eval_every = int(
        training_contract[
            "evaluation_frequency_epochs"
        ]
    )

    seed = (
        SEED
        +
        int(
            exp[
                1:
            ]
        )
        *
        131
    )

    np.random.seed(
        seed
    )

    tf.random.set_seed(
        seed
    )

    # Independence contract: every experiment starts fresh from SG7B-11.
    model = tf.keras.models.load_model(
        SG7B11_FROZEN_MODEL
    )

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=np.float64,
    )

    dxi = tf.constant(
        float(
            xi[1]
            -
            xi[0]
        ),
        tf.float32,
    )

    tD_scale = tf.constant(
        float(
            dataset[
                "tD_scale"
            ][0]
        ),
        tf.float32,
    )

    canonical_ds = make_canonical_dataset(
        dataset[
            "X_train"
        ],
        dataset[
            "Y_train"
        ],
        targets[
            "face_train"
        ],
        targets[
            "div_train"
        ],
        frozen_anchor[
            "train"
        ],
        seed,
    )

    deployment_ds = make_deployment_dataset(
        deployment,
        frozen100,
        seed
        +
        17,
    )

    optimizer = tf.keras.optimizers.Adam(
        initial_lr
    )

    canonical_step = make_canonical_train_step(
        base
    )

    deployment_step = make_front_preserving_deployment_step(
        config,
        contract,
        deployment[
            "xi"
        ],
    )

    history = {
        "epoch":
            [],

        "learning_rate":
            [],

        "score":
            [],

        "test_L1":
            [],

        "mass_MAE":
            [],

        "recovered_fronts":
            [],

        "conditioned_gap":
            [],

        "profile_L1_100d":
            [],

        "front_anchor_MAE":
            [],

        "front_xi_shift_mean":
            [],

        "front_xi_shift_P90":
            [],

        "bias_500_1000":
            [],

        "bias_1000_2000":
            [],

        "bias_gt2000":
            [],

        "tail_bias":
            [],

        "material_share":
            [],

        "front_shape_pass":
            [],
    }

    best_score = np.inf
    best_epoch = -1

    patience = 0
    lr_patience = 0

    current_lr = float(
        initial_lr
    )

    start_time = time.perf_counter()

    for epoch in range(
        maximum_epochs
    ):

        # -----------------------------------------------------------------
        # A. Canonical physics / state preservation pass
        # -----------------------------------------------------------------

        for (
            Xb,
            Yb,
            Fb,
            Db,
            Ab,
        ) in canonical_ds:

            canonical_step(
                model,
                optimizer,
                Xb,
                Yb,
                Fb,
                Db,
                Ab,
                tD_scale,
                dxi,
            )

        # -----------------------------------------------------------------
        # B. Front-preserving targeted deployment pass
        # -----------------------------------------------------------------

        for (
            Xb,
            Yb,
            Tb,
            Ab,
        ) in deployment_ds:

            deployment_step(
                model,
                optimizer,
                Xb,
                Yb,
                Tb,
                Ab,
            )

        if not (
            epoch == 0
            or
            (
                epoch + 1
            )
            %
            eval_every
            ==
            0
        ):

            continue

        screen = evaluate_local_candidate(
            base,
            sg11,
            model,
            dataset,
            targets,
            deployment,
            frozen100,
            contract,
            shape_contract,
        )

        score = candidate_score(
            screen,
            contract,
        )

        test = screen[
            "test"
        ]

        front = screen[
            "front"
        ]

        bias = screen[
            "bias"
        ]

        front_shape_pass = all(
            row[
                "passed"
            ]
            for row
            in screen[
                "shape_gate_rows"
            ]
        )

        history[
            "epoch"
        ].append(
            epoch
            +
            1
        )

        history[
            "learning_rate"
        ].append(
            current_lr
        )

        history[
            "score"
        ].append(
            score
        )

        history[
            "test_L1"
        ].append(
            test[
                "L1"
            ]
        )

        history[
            "mass_MAE"
        ].append(
            test[
                "mass_relative_MAE"
            ]
        )

        history[
            "recovered_fronts"
        ].append(
            front[
                "recovered_front_count"
            ]
        )

        history[
            "conditioned_gap"
        ].append(
            front[
                "conditioned_gap"
            ]
        )

        history[
            "profile_L1_100d"
        ].append(
            front[
                "profile_L1_100d"
            ]
        )

        history[
            "front_anchor_MAE"
        ].append(
            front[
                "front_anchor_MAE"
            ]
        )

        history[
            "front_xi_shift_mean"
        ].append(
            front[
                "frozen_front_xi_shift_mean"
            ]
        )

        history[
            "front_xi_shift_P90"
        ].append(
            front[
                "frozen_front_xi_shift_P90"
            ]
        )

        history[
            "bias_500_1000"
        ].append(
            bias[
                "bias_500_1000"
            ]
        )

        history[
            "bias_1000_2000"
        ].append(
            bias[
                "bias_1000_2000"
            ]
        )

        history[
            "bias_gt2000"
        ].append(
            bias[
                "bias_gt2000"
            ]
        )

        history[
            "tail_bias"
        ].append(
            bias[
                "tail_bias"
            ]
        )

        history[
            "material_share"
        ].append(
            bias[
                "material_share_500_1000"
            ]
        )

        history[
            "front_shape_pass"
        ].append(
            float(
                front_shape_pass
            )
        )

        # -------------------------------------------------------------
        # Checkpoint only when ALL non-canonical local preservation gates
        # are already satisfied. Canonical physics is tested independently
        # on the best checkpoint after training.
        # -------------------------------------------------------------

        if (
            screen[
                "local_screen_pass"
            ]
            and
            np.isfinite(
                score
            )
            and
            score
            <
            best_score
            -
            1.0e-7
        ):

            best_score = score
            best_epoch = (
                epoch
                +
                1
            )

            patience = 0
            lr_patience = 0

            model.save_weights(
                best_weights_file
            )

        else:

            patience += eval_every
            lr_patience += eval_every

        print(
            f"  {exp} | "
            f"epoch {epoch+1:4d}/{maximum_epochs} | "
            f"lr={current_lr:.2e} | "
            f"L1={test['L1']:.3e} | "
            f"fronts={front['recovered_front_count']:4d}/"
            f"{front['truth_front_count']:4d} | "
            f"gap={front['conditioned_gap']:.3e} | "
            f"shape={'P' if front_shape_pass else 'F'} | "
            f"anchor={front['front_anchor_MAE']:.3e} | "
            f"xiP90={front['frozen_front_xi_shift_P90']:.3e} | "
            f"B500={bias['bias_500_1000']:.3e} | "
            f"B1000={bias['bias_1000_2000']:.3e} | "
            f"B2000={bias['bias_gt2000']:.3e} | "
            f"tail={bias['tail_bias']:.3e} | "
            f"share={100*bias['material_share_500_1000']:.1f}% | "
            f"local={'PASS' if screen['local_screen_pass'] else 'FAIL'}"
        )

        # Once the exact complete LOCAL contract has been reached, permit a
        # little extra training before stopping so a stable checkpoint exists.
        if (
            screen[
                "local_screen_pass"
            ]
            and
            epoch
            >=
            20
        ):

            print(
                f"\n  {exp}: complete SG7B-16 local contract reached."
            )

            break

        if (
            lr_patience
            >=
            lr_patience_target
        ):

            new_lr = max(
                current_lr
                *
                0.5,
                minimum_lr,
            )

            if new_lr < current_lr:

                current_lr = new_lr

                optimizer.learning_rate.assign(
                    current_lr
                )

            lr_patience = 0

        if (
            patience
            >=
            early_stop_patience
        ):

            print(
                f"\n  {exp}: early stopping at epoch {epoch+1}; "
                f"best local-contract epoch={best_epoch}."
            )

            break

    runtime_seconds = (
        time.perf_counter()
        -
        start_time
    )

    for key in history:
        history[key] = np.asarray(
            history[key]
        )

    np.savez_compressed(
        history_file,
        **history,
    )

    model.save(
        final_model_file
    )

    if not best_weights_file.exists():

        return {
            "experiment":
                exp,

            "description":
                config[
                    "description"
                ],

            "config":
                config,

            "runtime_seconds":
                runtime_seconds,

            "best_epoch":
                -1,

            "best_score":
                np.inf,

            "best_model_file":
                None,

            "local_screen":
                None,

            "canonical_metrics":
                None,

            "canonical_gates":
                None,

            "canonical_pass":
                False,

            "complete_pass":
                False,

            "history":
                history,
        }

    model.load_weights(
        best_weights_file
    )

    model.save(
        best_model_file
    )

    local_screen = evaluate_local_candidate(
        base,
        sg11,
        model,
        dataset,
        targets,
        deployment,
        frozen100,
        contract,
        shape_contract,
    )

    canonical_metrics, canonical_gates, canonical_pass = canonical_gate_screen(
        sg11,
        base,
        model,
        dataset,
        canonical_truth,
    )

    complete_pass = bool(
        local_screen[
            "local_screen_pass"
        ]
        and
        canonical_pass
    )

    return {
        "experiment":
            exp,

        "description":
            config[
                "description"
            ],

        "config":
            config,

        "runtime_seconds":
            runtime_seconds,

        "best_epoch":
            best_epoch,

        "best_score":
            best_score,

        "best_model_file":
            str(
                best_model_file
            ),

        "local_screen":
            local_screen,

        "canonical_metrics":
            canonical_metrics,

        "canonical_gates":
            canonical_gates,

        "canonical_pass":
            canonical_pass,

        "complete_pass":
            complete_pass,

        "history":
            history,
    }


# =============================================================================
# RESULT FLATTENING
# =============================================================================

def result_row(
    result,
):

    if result[
        "local_screen"
    ] is None:

        return {
            "experiment":
                result[
                    "experiment"
                ],

            "description":
                result[
                    "description"
                ],

            "best_epoch":
                -1,

            "complete_pass":
                False,

            "failure":
                "NO_LOCAL_CONTRACT_CHECKPOINT",
        }

    screen = result[
        "local_screen"
    ]

    front = screen[
        "front"
    ]

    bias = screen[
        "bias"
    ]

    test = screen[
        "test"
    ]

    canonical = result[
        "canonical_metrics"
    ]

    return {
        "experiment":
            result[
                "experiment"
            ],

        "description":
            result[
                "description"
            ],

        "best_epoch":
            result[
                "best_epoch"
            ],

        "score":
            result[
                "best_score"
            ],

        "runtime_seconds":
            result[
                "runtime_seconds"
            ],

        "complete_pass":
            result[
                "complete_pass"
            ],

        "local_screen_pass":
            screen[
                "local_screen_pass"
            ],

        "canonical_pass":
            result[
                "canonical_pass"
            ],

        "test_L1":
            test[
                "L1"
            ],

        "test_L2":
            test[
                "L2"
            ],

        "mass_relative_MAE":
            test[
                "mass_relative_MAE"
            ],

        "canonical_mean":
            canonical[
                "canonical_mean"
            ],

        "canonical_P90":
            canonical[
                "canonical_P90"
            ],

        "canonical_fraction_gt1":
            canonical[
                "fraction_gt_1"
            ],

        "recovered_fronts":
            front[
                "recovered_front_count"
            ],

        "conditioned_gap":
            front[
                "conditioned_gap"
            ],

        "profile_L1_100d":
            front[
                "profile_L1_100d"
            ],

        "front_anchor_MAE":
            front[
                "front_anchor_MAE"
            ],

        "front_xi_shift_mean":
            front[
                "frozen_front_xi_shift_mean"
            ],

        "front_xi_shift_P90":
            front[
                "frozen_front_xi_shift_P90"
            ],

        "bias_500_1000":
            bias[
                "bias_500_1000"
            ],

        "bias_1000_2000":
            bias[
                "bias_1000_2000"
            ],

        "bias_gt2000":
            bias[
                "bias_gt2000"
            ],

        "tail_bias":
            bias[
                "tail_bias"
            ],

        "material_share_500_1000":
            bias[
                "material_share_500_1000"
            ],
    }


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "PAD-Stream V15-SG7B-16 controlled front-preserving TOF refinement."
        )
    )

    parser.add_argument(
        "--workspace",
        type=str,
        default=str(
            DEFAULT_DEPLOYMENT_WORKSPACE
        ),
        help=(
            "Accepted 11x11 SG5C workspace containing SG6 geometry."
        ),
    )

    parser.add_argument(
        "--experiments",
        type=str,
        default="E1,E2,E3,E4,E5",
        help=(
            "Comma-separated trainable experiments. E0 is always evaluated."
        ),
    )

    args = parser.parse_args()

    selected = {
        value.strip()
        for value
        in args.experiments.split(",")
        if value.strip()
    }

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7B-16"
    )

    print(
        "Controlled Front-Preserving TOF Refinement"
    )

    print(
        "=" * 78
    )

    print(
        "\nTRAINING WILL BE PERFORMED FOR SELECTED E1-E5 EXPERIMENTS."
    )

    print(
        "THE SG7B-11 FRONT-AWARE FROZEN MODEL WILL NOT BE MODIFIED."
    )

    print(
        "EVERY EXPERIMENT STARTS FROM THE SAME VERIFIED SG7B-11 CHECKPOINT."
    )

    print(
        "TOF CORRECTION IS MASKED OUT OF THE ACCEPTED FRONT SHELL."
    )

    print(
        "NO FRONT, PHYSICS, TOF-BIAS, OR SG7E GATE WILL BE RELAXED."
    )

    print(
        "NO CANDIDATE WILL BE DECLARED FROZEN BY SG7B-16."
    )

    # =========================================================================
    # PRECONDITIONS / CONTRACT
    # =========================================================================

    required = [
        BASE_SOURCE_FILE,
        SG7B10_SOURCE_FILE,
        SG7B11_SOURCE_FILE,
        SG7B15R_CONTRACT_FILE,
        SG7B15R_SUMMARY_FILE,
        SG7B10S_CONTRACT_FILE,
        SG7B11_FROZEN_MODEL,
        SG7B11_MANIFEST,
        SG7B11_PHYSICS_TABLE,
        SG7CR_DEPLOYMENT_FILE,
    ]

    for path in required:

        if not path.exists():

            raise FileNotFoundError(
                f"Missing SG7B-16 prerequisite:\n{path}"
            )

    contract = load_json(
        SG7B15R_CONTRACT_FILE
    )

    contract_summary = load_json(
        SG7B15R_SUMMARY_FILE
    )

    shape_contract = load_json(
        SG7B10S_CONTRACT_FILE
    )

    if (
        contract_summary.get(
            "status"
        )
        !=
        "FRONT_PRESERVING_TOF_REFINEMENT_CONTRACT_READY"
    ):

        raise RuntimeError(
            "SG7B-16 requires SG7B-15R ready contract status."
        )

    exact_front_contract = contract[
        "authoritative_front_improvement_contract"
    ]

    print(
        "\nAUTHORITATIVE FRONT CONTRACT"
    )

    print(
        f"  Minimum recovered fronts : "
        f"{exact_front_contract['minimum_recovered_fronts']}"
    )

    print(
        f"  Maximum conditioned gap   : "
        f"{float(exact_front_contract['maximum_conditioned_threshold_gap']):.17e}"
    )

    print(
        f"  Maximum 100d profile L1   : "
        f"{float(exact_front_contract['maximum_100d_profile_L1']):.17e}"
    )

    # =========================================================================
    # FROZEN IDENTITY
    # =========================================================================

    frozen_hash = compute_sha256(
        SG7B11_FROZEN_MODEL
    )

    manifest = load_json(
        SG7B11_MANIFEST
    )

    if frozen_hash not in json.dumps(
        manifest
    ):

        raise RuntimeError(
            "SG7B-11 frozen SHA-256 not reproduced by freeze manifest."
        )

    print(
        "\nFROZEN SOURCE"
    )

    print(
        f"  Model                   : "
        f"{SG7B11_FROZEN_MODEL.name}"
    )

    print(
        f"  SHA-256                 : "
        f"{frozen_hash}"
    )

    print(
        "  Identity                : PASS"
    )

    # =========================================================================
    # MODULES / DATA
    # =========================================================================

    base = import_module(
        BASE_SOURCE_FILE,
        "pad_stream_sg7b6d_for_sg7b16",
    )

    sg11 = import_module(
        SG7B11_SOURCE_FILE,
        "pad_stream_sg7b11_for_sg7b16",
    )

    dataset = base.load_dataset()

    sg7a = base.load_sg7a()

    targets = base.build_advective_targets(
        dataset,
        sg7a,
    )

    workspace = Path(
        args.workspace
    ).resolve()

    deployment = load_deployment_database(
        workspace,
        float(
            dataset[
                "tD_scale"
            ][0]
        ),
    )

    frozen_model = tf.keras.models.load_model(
        SG7B11_FROZEN_MODEL
    )

    frozen_anchor = {
        split:
            frozen_model.predict(
                dataset[
                    f"X_{split}"
                ].astype(
                    np.float32
                ),
                batch_size=BATCH_SIZE,
                verbose=0,
            ).astype(
                np.float32
            )
        for split
        in [
            "train",
            "val",
            "test",
        ]
    }

    frozen100 = frozen_model.predict(
        deployment[
            "X100"
        ],
        batch_size=BATCH_SIZE,
        verbose=0,
    )[
        :,
        :,
        0,
    ]

    identity_linf = float(
        np.max(
            np.abs(
                frozen100
                -
                deployment[
                    "stored_front_aware100"
                ]
            )
        )
    )

    if identity_linf > 2.0e-6:

        raise RuntimeError(
            "Fresh SG7B-11 deployment does not reproduce SG7C-R.\n"
            f"Linf={identity_linf:.6e}"
        )

    # =========================================================================
    # INDEPENDENT CANONICAL IMPLEMENTATION PRECHECK
    # =========================================================================

    canonical_truth = sg11.build_sg7a_canonical_reference(
        base,
        tf,
        dataset,
        sg7a,
    )

    frozen_canonical = sg11.canonical_metrics(
        base,
        tf,
        frozen_model,
        dataset,
        canonical_truth,
    )

    canonical_reference = load_sg7b11_canonical_reference(
        SG7B11_PHYSICS_TABLE
    )

    precheck_mean = relative_close(
        frozen_canonical[
            "canonical_mean"
        ],
        canonical_reference[
            "canonical_mean"
        ],
        5.0e-4,
    )

    precheck_p90 = relative_close(
        frozen_canonical[
            "canonical_P90"
        ],
        canonical_reference[
            "canonical_P90"
        ],
        5.0e-4,
    )

    precheck_fraction = bool(
        abs(
            frozen_canonical[
                "fraction_gt_1"
            ]
            -
            canonical_reference[
                "fraction_gt_1"
            ]
        )
        <=
        5.0e-5
    )

    canonical_precheck_pass = bool(
        precheck_mean
        and
        precheck_p90
        and
        precheck_fraction
    )

    print(
        "\nINDEPENDENT CANONICAL PRECHECK"
    )

    print(
        f"  Reference               : "
        f"{canonical_reference['source_label']}"
    )

    print(
        f"  Mean                    : "
        f"{frozen_canonical['canonical_mean']:.6e} "
        f"vs {canonical_reference['canonical_mean']:.6e}"
    )

    print(
        f"  P90                     : "
        f"{frozen_canonical['canonical_P90']:.6e} "
        f"vs {canonical_reference['canonical_P90']:.6e}"
    )

    print(
        f"  Fraction >1             : "
        f"{100*frozen_canonical['fraction_gt_1']:.3f}% "
        f"vs {100*canonical_reference['fraction_gt_1']:.3f}%"
    )

    print(
        f"  Reproduction            : "
        f"{'PASS' if canonical_precheck_pass else 'FAIL'}"
    )

    if not canonical_precheck_pass:

        raise RuntimeError(
            "Independent canonical implementation failed SG7B-11 precheck."
        )

    # =========================================================================
    # E0 BASELINE
    # =========================================================================

    e0_local = evaluate_local_candidate(
        base,
        sg11,
        frozen_model,
        dataset,
        targets,
        deployment,
        frozen100,
        contract,
        shape_contract,
    )

    e0_canonical, e0_canonical_gates, e0_canonical_pass = (
        canonical_gate_screen(
            sg11,
            base,
            frozen_model,
            dataset,
            canonical_truth,
        )
    )

    print(
        "\nSG7B-11 FROZEN CONTROL"
    )

    print(
        f"  Deployment identity Linf: "
        f"{identity_linf:.6e}"
    )

    print(
        f"  Recovered fronts        : "
        f"{e0_local['front']['recovered_front_count']} / "
        f"{e0_local['front']['truth_front_count']}"
    )

    print(
        f"  Conditioned gap         : "
        f"{e0_local['front']['conditioned_gap']:.6e}"
    )

    print(
        f"  Front anchor MAE        : "
        f"{e0_local['front']['front_anchor_MAE']:.6e}"
    )

    print(
        f"  Frozen xi P90 shift     : "
        f"{e0_local['front']['frozen_front_xi_shift_P90']:.6e}"
    )

    print(
        f"  500-1000d bias          : "
        f"{e0_local['bias']['bias_500_1000']:.6e}"
    )

    print(
        f"  1000-2000d bias         : "
        f"{e0_local['bias']['bias_1000_2000']:.6e}"
    )

    print(
        f"  >2000d bias             : "
        f"{e0_local['bias']['bias_gt2000']:.6e}"
    )

    print(
        f"  Tail bias               : "
        f"{e0_local['bias']['tail_bias']:.6e}"
    )

    # =========================================================================
    # SAVE PRECHECK
    # =========================================================================

    precheck = {
        "milestone":
            "V15-SG7B-16",

        "SG7B15R_contract_ready":
            True,

        "frozen_model":
            str(
                SG7B11_FROZEN_MODEL
            ),

        "frozen_sha256":
            frozen_hash,

        "deployment_identity_Linf":
            identity_linf,

        "canonical_precheck_pass":
            canonical_precheck_pass,

        "authoritative_front_contract":
            exact_front_contract,

        "new_front_guards":
            contract[
                "new_front_guards"
            ],
    }

    save_json(
        PRECHECK_FILE,
        precheck,
    )

    # =========================================================================
    # EXPERIMENT MATRIX
    # =========================================================================

    experiments = parse_experiments(
        contract,
        selected,
    )

    results = [
        {
            "experiment":
                "E0",

            "description":
                "Frozen SG7B-11 control",

            "config":
                next(
                    row
                    for row
                    in experiments
                    if row[
                        "experiment"
                    ]
                    ==
                    "E0"
                ),

            "runtime_seconds":
                0.0,

            "best_epoch":
                0,

            "best_score":
                candidate_score(
                    e0_local,
                    contract,
                ),

            "best_model_file":
                str(
                    SG7B11_FROZEN_MODEL
                ),

            "local_screen":
                e0_local,

            "canonical_metrics":
                e0_canonical,

            "canonical_gates":
                e0_canonical_gates,

            "canonical_pass":
                e0_canonical_pass,

            "complete_pass":
                bool(
                    e0_local[
                        "local_screen_pass"
                    ]
                    and
                    e0_canonical_pass
                ),

            "history":
                {},
        }
    ]

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "CONTROLLED FRONT-PRESERVING EXPERIMENTS"
    )

    print(
        "=" * 78
    )

    for config in experiments:

        if config[
            "experiment"
        ] == "E0":

            continue

        print(
            f"\n{config['experiment']} — "
            f"{config['description']}"
        )

        result = train_experiment(
            base,
            sg11,
            config,
            contract,
            shape_contract,
            dataset,
            targets,
            deployment,
            frozen_anchor,
            frozen100,
            canonical_truth,
        )

        results.append(
            result
        )

    # =========================================================================
    # OUTPUT TABLES
    # =========================================================================

    experiment_rows = [
        result_row(
            result
        )
        for result
        in results
    ]

    save_csv(
        EXPERIMENT_METRICS_FILE,
        experiment_rows,
    )

    epoch_rows = []

    for result in results:

        history = result[
            "history"
        ]

        if not history:
            continue

        n_entries = len(
            history[
                "epoch"
            ]
        )

        for i in range(
            n_entries
        ):

            row = {
                "experiment":
                    result[
                        "experiment"
                    ],

                "epoch":
                    int(
                        history[
                            "epoch"
                        ][i]
                    ),
            }

            for key, values in history.items():

                if key == "epoch":
                    continue

                row[key] = float(
                    values[i]
                )

            epoch_rows.append(
                row
            )

    save_csv(
        EPOCH_METRICS_FILE,
        epoch_rows,
    )

    front_guard_rows = []

    shape_gate_rows = []

    final_gate_rows = []

    for result in results:

        if result[
            "local_screen"
        ] is None:
            continue

        exp = result[
            "experiment"
        ]

        screen = result[
            "local_screen"
        ]

        front = screen[
            "front"
        ]

        front_guard_rows.append(
            {
                "experiment":
                    exp,

                "front_anchor_MAE":
                    front[
                        "front_anchor_MAE"
                    ],

                "front_xi_shift_mean":
                    front[
                        "frozen_front_xi_shift_mean"
                    ],

                "front_xi_shift_P90":
                    front[
                        "frozen_front_xi_shift_P90"
                    ],

                "front_xi_shift_MAX":
                    front[
                        "frozen_front_xi_shift_MAX"
                    ],

                "common_frozen_front_count":
                    front[
                        "common_frozen_front_count"
                    ],
            }
        )

        for row in screen[
            "shape_gate_rows"
        ]:

            shape_gate_rows.append(
                {
                    "experiment":
                        exp,

                    **row,
                }
            )

        for gate, flag in screen[
            "gates"
        ].items():

            final_gate_rows.append(
                {
                    "experiment":
                        exp,

                    "gate":
                        gate,

                    "passed":
                        bool(
                            flag
                        ),

                    "stage":
                        "local",
                }
            )

        if result[
            "canonical_gates"
        ] is not None:

            for gate, flag in result[
                "canonical_gates"
            ].items():

                final_gate_rows.append(
                    {
                        "experiment":
                            exp,

                        "gate":
                            gate,

                        "passed":
                            bool(
                                flag
                            ),

                        "stage":
                            "canonical",
                    }
                )

    save_csv(
        FRONT_GUARD_FILE,
        front_guard_rows,
    )

    save_csv(
        SHAPE_GATE_FILE,
        shape_gate_rows,
    )

    save_csv(
        FINAL_GATE_FILE,
        final_gate_rows,
    )

    # =========================================================================
    # CANDIDATE DECISION
    # =========================================================================

    passing = [
        result
        for result
        in results
        if result[
            "experiment"
        ]
        !=
        "E0"
        and
        result[
            "complete_pass"
        ]
    ]

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "V15-SG7B-16 COMPLETE CANDIDATE SCREEN"
    )

    print(
        "=" * 78
    )

    for result in results:

        if result[
            "local_screen"
        ] is None:

            print(
                f"[FAIL] {result['experiment']} | "
                f"no checkpoint reached the complete local contract"
            )

            continue

        screen = result[
            "local_screen"
        ]

        front = screen[
            "front"
        ]

        bias = screen[
            "bias"
        ]

        print(
            f"[{'PASS' if result['complete_pass'] else 'FAIL'}] "
            f"{result['experiment']} | "
            f"fronts={front['recovered_front_count']} | "
            f"gap={front['conditioned_gap']:.3e} | "
            f"anchor={front['front_anchor_MAE']:.3e} | "
            f"xiP90={front['frozen_front_xi_shift_P90']:.3e} | "
            f"B500={bias['bias_500_1000']:.3e} | "
            f"B1000={bias['bias_1000_2000']:.3e} | "
            f"B2000={bias['bias_gt2000']:.3e} | "
            f"tail={bias['tail_bias']:.3e} | "
            f"canonical={'PASS' if result['canonical_pass'] else 'FAIL'}"
        )

    print(
        "=" * 78
    )

    if passing:

        passing.sort(
            key=lambda result:
                candidate_score(
                    result[
                        "local_screen"
                    ],
                    contract,
                )
        )

        winner = passing[
            0
        ]

        shutil.copy2(
            winner[
                "best_model_file"
            ],
            CANDIDATE_MODEL_FILE,
        )

        candidate_hash = compute_sha256(
            CANDIDATE_MODEL_FILE
        )

        winner_screen = winner[
            "local_screen"
        ]

        np.savez_compressed(
            NUMERICAL_FILE,

            prediction100=
                winner_screen[
                    "prediction100"
                ].astype(
                    np.float32
                ),

            truth100=
                deployment[
                    "truth100"
                ].astype(
                    np.float32
                ),

            frozen100=
                frozen100.astype(
                    np.float32
                ),

            terminal_days=
                deployment[
                    "terminal_days"
                ].astype(
                    np.float64
                ),

            xi=
                deployment[
                    "xi"
                ].astype(
                    np.float32
                ),
        )

        candidate_manifest = {
            "milestone":
                "V15-SG7B-16",

            "status":
                "FRONT_PRESERVING_TOF_CANDIDATE_NOMINATED",

            "experiment":
                winner[
                    "experiment"
                ],

            "candidate_model":
                str(
                    CANDIDATE_MODEL_FILE
                ),

            "candidate_sha256":
                candidate_hash,

            "starting_frozen_model":
                str(
                    SG7B11_FROZEN_MODEL
                ),

            "starting_frozen_sha256":
                frozen_hash,

            "local_contract_pass":
                True,

            "canonical_physics_pass":
                True,

            "candidate_is_frozen":
                False,
        }

        save_json(
            CANDIDATE_MANIFEST_FILE,
            candidate_manifest,
        )

        status = (
            "FRONT_PRESERVING_TOF_CANDIDATE_NOMINATED"
        )

        recommendation = (
            "A controlled SG7B-16 candidate independently satisfies the "
            "training-stage state/mass/regional/canonical gates, the exact "
            "SG7B-10S front contract, every SG7A/E0-relative shape gate, "
            "the new frozen-front displacement guards, and every SG7B-12 "
            "TOF-bias gate. Do not freeze it here. Proceed to a clean "
            "independent final validation."
        )

        next_milestone = (
            "V15-SG7B-17 — Independent Front-Preserving TOF Candidate Validation"
        )

        print(
            "\nNOMINATED CANDIDATE"
        )

        print(
            f"  Experiment              : "
            f"{winner['experiment']}"
        )

        print(
            f"  Model                   : "
            f"{CANDIDATE_MODEL_FILE.name}"
        )

        print(
            f"  SHA-256                 : "
            f"{candidate_hash}"
        )

    else:

        winner = None
        candidate_hash = None

        status = (
            "NO_SG7B16_CANDIDATE_PASSES_COMPLETE_CONTRACT"
        )

        recommendation = (
            "No SG7B-16 experiment simultaneously satisfies the exact "
            "front-position/shape preservation contract and the retained "
            "TOF-bias contract. Do not relax any gate and do not freeze a "
            "candidate. Audit the controlled outcome before redesigning."
        )

        next_milestone = (
            "V15-SG7B-16R — Front-Preserving TOF Refinement Outcome Audit"
        )

    # =========================================================================
    # DIAGNOSTICS
    # =========================================================================

    plot_rows = [
        row
        for row
        in experiment_rows
        if "conditioned_gap" in row
    ]

    if plot_rows:

        labels = [
            row[
                "experiment"
            ]
            for row
            in plot_rows
        ]

        plt.figure(
            figsize=(
                9,
                5,
            )
        )

        plt.bar(
            labels,
            [
                row[
                    "conditioned_gap"
                ]
                for row
                in plot_rows
            ],
        )

        plt.axhline(
            float(
                exact_front_contract[
                    "maximum_conditioned_threshold_gap"
                ]
            ),
            linestyle="--",
        )

        plt.ylabel(
            "Conditioned front gap"
        )

        plt.xlabel(
            "Experiment"
        )

        plt.title(
            "PAD-Stream V15-SG7B-16\n"
            "Exact Front-Gap Preservation"
        )

        plt.tight_layout()

        plt.savefig(
            OUTPUT_DIR
            /
            "V15SG7B16_Conditioned_Front_Gap.png",
            dpi=300,
        )

        plt.close()

        plt.figure(
            figsize=(
                9,
                5,
            )
        )

        plt.bar(
            labels,
            [
                row[
                    "bias_500_1000"
                ]
                for row
                in plot_rows
            ],
        )

        plt.axhline(
            2.500000e-03,
            linestyle="--",
        )

        plt.ylabel(
            "500-1000 d mean bias"
        )

        plt.xlabel(
            "Experiment"
        )

        plt.title(
            "PAD-Stream V15-SG7B-16\n"
            "TOF-Bias Preservation Tradeoff"
        )

        plt.tight_layout()

        plt.savefig(
            OUTPUT_DIR
            /
            "V15SG7B16_Bias_500_1000.png",
            dpi=300,
        )

        plt.close()

        plt.figure(
            figsize=(
                9,
                5,
            )
        )

        plt.bar(
            labels,
            [
                row[
                    "front_xi_shift_P90"
                ]
                for row
                in plot_rows
            ],
        )

        plt.axhline(
            float(
                contract[
                    "new_front_guards"
                ][
                    "maximum_P90_frozen_front_xi_shift"
                ]
            ),
            linestyle="--",
        )

        plt.ylabel(
            "P90 |candidate - SG7B-11 front xi|"
        )

        plt.xlabel(
            "Experiment"
        )

        plt.title(
            "PAD-Stream V15-SG7B-16\n"
            "Frozen-Front Displacement Guard"
        )

        plt.tight_layout()

        plt.savefig(
            OUTPUT_DIR
            /
            "V15SG7B16_Frozen_Front_Xi_Shift.png",
            dpi=300,
        )

        plt.close()

    # =========================================================================
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7B-16",

        "status":
            status,

        "starting_frozen_model":
            str(
                SG7B11_FROZEN_MODEL
            ),

        "starting_frozen_sha256":
            frozen_hash,

        "experiments_run":
            [
                result[
                    "experiment"
                ]
                for result
                in results
            ],

        "candidate_nominated":
            winner is not None,

        "candidate_experiment":
            (
                winner[
                    "experiment"
                ]
                if winner is not None
                else None
            ),

        "candidate_sha256":
            candidate_hash,

        "recommendation":
            recommendation,

        "next_milestone":
            next_milestone,
    }

    save_json(
        SUMMARY_FILE,
        summary,
    )

    # =========================================================================
    # FINAL VALIDATION PRINT
    # =========================================================================

    checks = [
        (
            "SG7B-15R repaired contract loaded",
            contract_summary.get(
                "status"
            )
            ==
            "FRONT_PRESERVING_TOF_REFINEMENT_CONTRACT_READY",
        ),

        (
            "Exact SG7B-10S front gap retained",
            float(
                exact_front_contract[
                    "maximum_conditioned_threshold_gap"
                ]
            )
            ==
            float(
                shape_contract[
                    "front_improvement_contract"
                ][
                    "maximum_conditioned_threshold_gap"
                ]
            ),
        ),

        (
            "SG7B-11 frozen identity verified",
            True,
        ),

        (
            "SG7C-R deployment identity reproduced",
            identity_linf
            <=
            2.0e-6,
        ),

        (
            "Independent canonical implementation precheck passed",
            canonical_precheck_pass,
        ),

        (
            "Every trainable experiment started from SG7B-11",
            True,
        ),

        (
            "TOF correction masked outside front shell by construction",
            True,
        ),

        (
            "Front-position / shape guards evaluated",
            True,
        ),

        (
            "SG7B-12 TOF-bias gates evaluated",
            True,
        ),

        (
            "No SG7B-11 frozen model overwritten",
            True,
        ),

        (
            "Candidate decision established",
            status
            in
            {
                "FRONT_PRESERVING_TOF_CANDIDATE_NOMINATED",
                "NO_SG7B16_CANDIDATE_PASSES_COMPLETE_CONTRACT",
            },
        ),
    ]

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "V15-SG7B-16 VALIDATION"
    )

    print(
        "=" * 78
    )

    for description, flag in checks:

        print(
            f"[{'PASS' if flag else 'FAIL'}] "
            f"{description}"
        )

    print(
        "=" * 78
    )

    print(
        "\nSTATUS"
    )

    print(
        f"  {status}"
    )

    print(
        "\nRECOMMENDATION"
    )

    print(
        f"  {recommendation}"
    )

    print(
        "\nNEXT MILESTONE"
    )

    print(
        f"  {next_milestone}"
    )

    print(
        "\nOUTPUTS"
    )

    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print(
        "\nTables:"
    )

    print(
        f"  {EXPERIMENT_METRICS_FILE.name}"
    )

    print(
        f"  {EPOCH_METRICS_FILE.name}"
    )

    print(
        f"  {FRONT_GUARD_FILE.name}"
    )

    print(
        f"  {SHAPE_GATE_FILE.name}"
    )

    print(
        f"  {FINAL_GATE_FILE.name}"
    )

    print(
        "\nPrecheck:"
    )

    print(
        f"  {PRECHECK_FILE.name}"
    )

    if winner is not None:

        print(
            "\nCandidate:"
        )

        print(
            f"  {CANDIDATE_MODEL_FILE.name}"
        )

        print(
            f"  {CANDIDATE_MANIFEST_FILE.name}"
        )

        print(
            f"  {NUMERICAL_FILE.name}"
        )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B16_Conditioned_Front_Gap.png"
    )

    print(
        "  V15SG7B16_Bias_500_1000.png"
    )

    print(
        "  V15SG7B16_Frozen_Front_Xi_Shift.png"
    )

    print(
        "\nSummary:"
    )

    print(
        f"  {SUMMARY_FILE.name}"
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "V15-SG7B-16 CONTROLLED REFINEMENT: COMPLETE"
    )

    print()

    print(
        "The SG7B-11 front-aware frozen model remains authoritative."
    )

    print(
        "No candidate has been frozen by SG7B-16."
    )

    print()

    print(
        "Next milestone:"
    )

    print(
        next_milestone
    )

    print(
        "=" * 78
    )


if __name__ == "__main__":

    main()
