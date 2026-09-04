from pathlib import Path
import json
import time

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7B-6B
# Targeted Physics-Dominant PI-RNN Fine-Tuning
#
# PURPOSE
# -------
# Continue training from the validated V15-SG7B-6 best model.
#
# NO architecture changes.
#
# The SG7B-6 plain-LSTM solution already demonstrated:
#
#   - good saturation-profile accuracy
#   - good injector-region accuracy
#   - acceptable mass conservation
#   - physical saturation bounds
#
# SG7B-7 failed only the strict PI-RNN / SG7A FV-residual ratio gate.
#
#
# SG7B-6B therefore:
#
#   1. loads V15SG7B6_Best_Model.keras
#   2. evaluates it with the EXACT SG7B-7 residual definition
#   3. fine-tunes at low learning rate
#   4. increases FV physics emphasis
#   5. retains data / mass / injector guardrails
#   6. gives modest extra emphasis to late-time profiles
#   7. selects checkpoints using PHYSICAL validation metrics
#
#
# TARGET
# ------
#
# SG7A truth FV relative MAE:
#
#       6.323248e-04
#
# SG7B-7 ratio freeze requirement:
#
#       PI-RNN / SG7A < 50
#
# Therefore:
#
#       PI-RNN FV relative MAE < 3.161624e-02
#
#
# NO:
#   - Fourier features
#   - FiLM
#   - front-coordinate input
#   - larger LSTM
#   - new classical truth
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

DATASET_FILE = (
    ROOT
    / "output"
    / "V15_SG7B3"
    / "SG7B3_REFERENCE_DATASET.npz"
)

SOURCE_MODEL_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6"
    / "V15SG7B6_Best_Model.keras"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B6B"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

BEST_WEIGHTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B6B_Best.weights.h5"
)

BEST_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B6B_Best_Model.keras"
)

FINAL_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B6B_Final_Model.keras"
)

HISTORY_FILE = (
    OUTPUT_DIR
    / "V15SG7B6B_Training_History.npz"
)

TEST_RESULTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B6B_Test_Results.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B6B_Summary.json"
)


# =============================================================================
# REPRODUCIBILITY
# =============================================================================

SEED = 14071789

np.random.seed(SEED)
tf.random.set_seed(SEED)


# =============================================================================
# FROZEN PHYSICS
# =============================================================================

SWC = 0.20
SOR = 0.20

S_INITIAL = SWC
S_INJECTED = 1.0 - SOR

KR_DISP_MAX = 0.80
KR_RES_MAX = 0.80

N_DISP = 2.0
N_RES = 2.0

MU_DISP = 0.50
MU_RES = 5.00

POROSITY = 0.20

NC = 0.10
PE_C = 22.0
LAMBDA_BC = 2.0

EPS = 1.0e-8


# =============================================================================
# SG7B-7 AUTHORITATIVE PHYSICS TARGET
# =============================================================================

SG7A_TRUTH_FV_RELATIVE_MAE = (
    6.323248e-04
)

MAX_FV_RATIO = 50.0

TARGET_FV_RELATIVE_MAE = (
    SG7A_TRUTH_FV_RELATIVE_MAE
    * MAX_FV_RATIO
)


# =============================================================================
# ARCHITECTURE
# =============================================================================

SEQUENCE_LENGTH = 201
BATCH_SIZE = 32

N_INJECTOR_NODES = 10


# =============================================================================
# FINE-TUNING CONFIGURATION
# =============================================================================

EPOCHS = 250

PATIENCE = 65

GRADIENT_CLIP_NORM = 5.0


# -----------------------------------------------------------------------------
# Learning-rate stages
# -----------------------------------------------------------------------------

LR_STAGE_1 = 1.0e-4
LR_STAGE_2 = 5.0e-5
LR_STAGE_3 = 2.5e-5

LR_STAGE_2_EPOCH = 100
LR_STAGE_3_EPOCH = 180


# -----------------------------------------------------------------------------
# Training-loss weights
# -----------------------------------------------------------------------------

LAMBDA_DATA = 1.0

# Physics is the primary refinement objective.
LAMBDA_PHYS = 0.20

# Preserve existing physical/data quality without allowing them
# to dominate this fine-tuning stage.
LAMBDA_MASS = 0.50
LAMBDA_INJECTOR = 0.50
LAMBDA_LATE = 0.50


# -----------------------------------------------------------------------------
# Validation checkpoint score
#
# Terms are normalized by desired physical acceptance levels.
# Physics receives the largest weight.
# -----------------------------------------------------------------------------

SCORE_WEIGHT_DATA = 1.00
SCORE_WEIGHT_PHYS = 2.00
SCORE_WEIGHT_MASS = 0.50
SCORE_WEIGHT_INJECTOR = 0.25
SCORE_WEIGHT_LATE = 0.50


# =============================================================================
# FINAL SG7B-6B GUARDRAILS
# =============================================================================

MAX_TEST_L1 = 0.020

MAX_FV_RELATIVE_MAE = (
    TARGET_FV_RELATIVE_MAE
)

MAX_MASS_RELATIVE_MAE = 0.030

MAX_INJECTOR_L1 = 0.015

MAX_LATE_L1 = 0.025


# =============================================================================
# LOAD DATASET
# =============================================================================

def load_dataset():

    if not DATASET_FILE.exists():

        raise FileNotFoundError(
            "Missing frozen SG7B-3 dataset:\n"
            f"{DATASET_FILE}"
        )

    data = np.load(
        DATASET_FILE
    )

    required = [
        "X_train",
        "Y_train",
        "X_val",
        "Y_val",
        "X_test",
        "Y_test",
        "tD_train",
        "tD_val",
        "tD_test",
        "xi",
        "tD_scale",
    ]

    for key in required:

        if key not in data:

            raise KeyError(
                f"Dataset field missing: {key}"
            )

    return {
        key: data[key]
        for key in required
    }


# =============================================================================
# PHYSICS FUNCTIONS
# =============================================================================

@tf.function
def effective_saturation_tf(S):

    span = (
        1.0
        - SWC
        - SOR
    )

    Se = (
        S
        - SWC
    ) / span

    return tf.clip_by_value(
        Se,
        0.0,
        1.0,
    )


@tf.function
def fractional_flow_tf(S):

    Se = effective_saturation_tf(
        S
    )

    kr_disp = (
        KR_DISP_MAX
        * tf.pow(
            Se,
            N_DISP,
        )
    )

    kr_res = (
        KR_RES_MAX
        * tf.pow(
            1.0 - Se,
            N_RES,
        )
    )

    lambda_disp = (
        kr_disp
        / MU_DISP
    )

    lambda_res = (
        kr_res
        / MU_RES
    )

    return (
        lambda_disp
        /
        (
            lambda_disp
            + lambda_res
            + EPS
        )
    )


@tf.function
def diffusion_shape_tf(S):

    span = (
        1.0
        - SWC
        - SOR
    )

    Se = (
        S
        - SWC
    ) / span

    Se = tf.clip_by_value(
        Se,
        1.0e-6,
        1.0 - 1.0e-6,
    )

    kr_res = (
        KR_RES_MAX
        * tf.pow(
            1.0 - Se,
            N_RES,
        )
    )

    fw = fractional_flow_tf(
        S
    )

    exponent = (
        -1.0
        / LAMBDA_BC
        - 1.0
    )

    raw = (
        kr_res
        * fw
        * tf.pow(
            Se,
            exponent,
        )
    )

    # -------------------------------------------------------------------------
    # Frozen SG7A normalization at Se = 0.5
    # -------------------------------------------------------------------------

    Se_mid = 0.5

    kr_disp_mid = (
        KR_DISP_MAX
        * Se_mid ** N_DISP
    )

    kr_res_mid = (
        KR_RES_MAX
        * (
            1.0 - Se_mid
        ) ** N_RES
    )

    lambda_disp_mid = (
        kr_disp_mid
        / MU_DISP
    )

    lambda_res_mid = (
        kr_res_mid
        / MU_RES
    )

    fw_mid = (
        lambda_disp_mid
        /
        (
            lambda_disp_mid
            + lambda_res_mid
        )
    )

    norm = (
        kr_res_mid
        * fw_mid
        * Se_mid ** exponent
    )

    return (
        raw
        / norm
    )


# =============================================================================
# INPUT AT ARBITRARY tD
# =============================================================================

def build_input_for_time(
    base_x,
    normalized_time,
):

    xi = (
        base_x[
            :,
            :,
            0:1
        ]
    )

    n_nodes = tf.shape(
        xi
    )[1]

    normalized_time = tf.reshape(
        normalized_time,
        (
            -1,
            1,
            1,
        ),
    )

    time_feature = tf.tile(
        normalized_time,
        (
            1,
            n_nodes,
            1,
        ),
    )

    return tf.concat(
        [
            xi,
            time_feature,
        ],
        axis=2,
    )


# =============================================================================
# AUTHORITATIVE SG7B-7 FV RESIDUAL
# =============================================================================

def finite_volume_residual(
    model,
    X,
    tD_scale,
    training,
):

    xi = (
        X[
            0,
            :,
            0
        ]
    )

    dxi = (
        xi[1]
        - xi[0]
    )

    # -------------------------------------------------------------------------
    # Time derivative
    # -------------------------------------------------------------------------

    t_norm = (
        X[
            :,
            0,
            1
        ]
    )

    t_actual = (
        t_norm
        * tD_scale
    )

    dt_reference = (
        tD_scale
        / 800.0
    )

    t_minus = tf.maximum(
        t_actual
        - dt_reference,
        0.0,
    )

    t_plus = tf.minimum(
        t_actual
        + dt_reference,
        tD_scale,
    )

    denominator = (
        t_plus
        - t_minus
        + EPS
    )

    X_minus = build_input_for_time(
        X,
        t_minus
        / tD_scale,
    )

    X_plus = build_input_for_time(
        X,
        t_plus
        / tD_scale,
    )

    S_minus = (
        model(
            X_minus,
            training=training,
        )[
            :,
            :,
            0
        ]
    )

    S_plus = (
        model(
            X_plus,
            training=training,
        )[
            :,
            :,
            0
        ]
    )

    S = (
        model(
            X,
            training=training,
        )[
            :,
            :,
            0
        ]
    )

    S_t = (
        S_plus
        - S_minus
    ) / tf.reshape(
        denominator,
        (
            -1,
            1,
        ),
    )

    batch_size = tf.shape(
        S
    )[0]

    # -------------------------------------------------------------------------
    # Conservative advective flux
    # -------------------------------------------------------------------------

    face_xi = tf.linspace(
        0.0,
        1.0,
        SEQUENCE_LENGTH + 1,
    )

    u_face = tf.exp(
        NC
        * face_xi
    )

    fw = fractional_flow_tf(
        S
    )

    f_injected = (
        fractional_flow_tf(
            tf.constant(
                S_INJECTED,
                dtype=tf.float32,
            )
        )
    )

    F_left = (
        tf.ones(
            (
                batch_size,
                1,
            ),
            dtype=tf.float32,
        )
        *
        u_face[0]
        *
        f_injected
    )

    F_internal = (
        fw[
            :,
            :-1
        ]
        *
        u_face[
            1:-1
        ][
            None,
            :
        ]
    )

    F_outlet = (
        fw[
            :,
            -1:
        ]
        *
        u_face[-1]
    )

    F_adv = tf.concat(
        [
            F_left,
            F_internal,
            F_outlet,
        ],
        axis=1,
    )

    div_adv = (
        F_adv[
            :,
            1:
        ]
        -
        F_adv[
            :,
            :-1
        ]
    ) / dxi

    # -------------------------------------------------------------------------
    # Capillary flux
    # -------------------------------------------------------------------------

    D_cell = diffusion_shape_tf(
        S
    )

    D_internal = (
        0.5
        * (
            D_cell[
                :,
                :-1
            ]
            +
            D_cell[
                :,
                1:
            ]
        )
    )

    G_internal = (
        POROSITY
        / PE_C
        *
        D_internal
        *
        (
            S[
                :,
                1:
            ]
            -
            S[
                :,
                :-1
            ]
        )
        / dxi
    )

    D_injected = (
        diffusion_shape_tf(
            tf.constant(
                S_INJECTED,
                dtype=tf.float32,
            )
        )
    )

    D_left = (
        0.5
        * (
            D_injected
            +
            D_cell[
                :,
                0
            ]
        )
    )

    G_left = (
        POROSITY
        / PE_C
        *
        D_left
        *
        (
            S[
                :,
                0
            ]
            -
            S_INJECTED
        )
        / (
            0.5
            * dxi
        )
    )[
        :,
        None
    ]

    G_right = tf.zeros(
        (
            batch_size,
            1,
        ),
        dtype=tf.float32,
    )

    G_cap = tf.concat(
        [
            G_left,
            G_internal,
            G_right,
        ],
        axis=1,
    )

    div_cap = (
        G_cap[
            :,
            1:
        ]
        -
        G_cap[
            :,
            :-1
        ]
    ) / dxi

    residual = (
        S_t
        +
        div_adv
        -
        div_cap
    )

    scale = (
        tf.abs(
            S_t
        )
        +
        tf.abs(
            div_adv
        )
        +
        tf.abs(
            div_cap
        )
        +
        1.0e-4
    )

    relative = (
        residual
        / scale
    )

    return (
        residual,
        relative,
        S,
    )


# =============================================================================
# INTEGRATION
# =============================================================================

def trapezoid_integral_tf(
    S,
    dxi,
):

    interior = tf.reduce_sum(
        S[
            :,
            1:-1
        ],
        axis=1,
    )

    endpoints = (
        0.5
        * (
            S[
                :,
                0
            ]
            +
            S[
                :,
                -1
            ]
        )
    )

    return (
        dxi
        * (
            interior
            +
            endpoints
        )
    )


# =============================================================================
# TRAINING LOSSES
# =============================================================================

def data_loss(
    Y_true,
    Y_pred,
):

    return tf.reduce_mean(
        tf.square(
            Y_pred
            - Y_true
        )
    )


def injector_loss(
    Y_true,
    Y_pred,
):

    truth = (
        Y_true[
            :,
            :N_INJECTOR_NODES,
            0
        ]
    )

    pred = (
        Y_pred[
            :,
            :N_INJECTOR_NODES,
            0
        ]
    )

    return tf.reduce_mean(
        tf.square(
            pred
            - truth
        )
    )


def mass_loss(
    Y_true,
    Y_pred,
    dxi,
):

    truth = (
        Y_true[
            :,
            :,
            0
        ]
    )

    pred = (
        Y_pred[
            :,
            :,
            0
        ]
    )

    true_mass = trapezoid_integral_tf(
        truth,
        dxi,
    )

    pred_mass = trapezoid_integral_tf(
        pred,
        dxi,
    )

    return tf.reduce_mean(
        tf.square(
            pred_mass
            - true_mass
        )
    )


def late_time_data_loss(
    X,
    Y_true,
    Y_pred,
):
    """
    Apply modest extra supervision to the late-time third of the
    dimensionless-time interval.

    This does not create new physics; it only emphasizes existing SG7A truth
    where SG7B-7 identified the largest time-band error.
    """

    t_norm = (
        X[
            :,
            0,
            1
        ]
    )

    mask = tf.cast(
        t_norm
        >= (2.0 / 3.0),
        tf.float32,
    )

    profile_mse = tf.reduce_mean(
        tf.square(
            Y_pred
            - Y_true
        ),
        axis=[
            1,
            2,
        ],
    )

    numerator = tf.reduce_sum(
        mask
        * profile_mse
    )

    denominator = (
        tf.reduce_sum(
            mask
        )
        + EPS
    )

    return (
        numerator
        / denominator
    )


# =============================================================================
# TRAIN STEP
# =============================================================================

@tf.function
def train_step(
    model,
    optimizer,
    X,
    Y,
    tD_scale,
    dxi,
):

    with tf.GradientTape() as tape:

        Y_pred = model(
            X,
            training=True,
        )

        L_data = data_loss(
            Y,
            Y_pred,
        )

        (
            _,
            relative,
            _,
        ) = finite_volume_residual(
            model,
            X,
            tD_scale,
            training=True,
        )

        L_phys = tf.reduce_mean(
            tf.square(
                relative
            )
        )

        L_mass = mass_loss(
            Y,
            Y_pred,
            dxi,
        )

        L_inj = injector_loss(
            Y,
            Y_pred,
        )

        L_late = late_time_data_loss(
            X,
            Y,
            Y_pred,
        )

        total = (
            LAMBDA_DATA
            * L_data
            +
            LAMBDA_PHYS
            * L_phys
            +
            LAMBDA_MASS
            * L_mass
            +
            LAMBDA_INJECTOR
            * L_inj
            +
            LAMBDA_LATE
            * L_late
        )

    gradients = tape.gradient(
        total,
        model.trainable_variables,
    )

    gradients, _ = (
        tf.clip_by_global_norm(
            gradients,
            GRADIENT_CLIP_NORM,
        )
    )

    optimizer.apply_gradients(
        zip(
            gradients,
            model.trainable_variables,
        )
    )

    return (
        total,
        L_data,
        L_phys,
        L_mass,
        L_inj,
        L_late,
    )


# =============================================================================
# DATA PIPELINE
# =============================================================================

def make_tf_dataset(
    X,
    Y,
    training,
):

    ds = tf.data.Dataset.from_tensor_slices(
        (
            X.astype(
                np.float32
            ),
            Y.astype(
                np.float32
            ),
        )
    )

    if training:

        ds = ds.shuffle(
            buffer_size=len(
                X
            ),
            seed=SEED,
            reshuffle_each_iteration=True,
        )

    ds = ds.batch(
        BATCH_SIZE
    )

    ds = ds.prefetch(
        tf.data.AUTOTUNE
    )

    return ds


# =============================================================================
# FULL-SPLIT METRICS
# =============================================================================

def evaluate_split(
    model,
    X,
    Y,
    xi,
    tD_scale,
):

    X_np = X.astype(
        np.float32
    )

    truth = (
        Y[
            :,
            :,
            0
        ]
    )

    prediction = (
        model.predict(
            X_np,
            batch_size=BATCH_SIZE,
            verbose=0,
        )[
            :,
            :,
            0
        ]
    )

    error = (
        prediction
        - truth
    )

    L1 = float(
        np.mean(
            np.abs(
                error
            )
        )
    )

    L2 = float(
        np.sqrt(
            np.mean(
                error ** 2
            )
        )
    )

    Linf = float(
        np.max(
            np.abs(
                error
            )
        )
    )

    # -------------------------------------------------------------------------
    # FV residual
    # -------------------------------------------------------------------------

    X_tf = tf.constant(
        X_np,
        dtype=tf.float32,
    )

    scale_tf = tf.constant(
        float(
            tD_scale
        ),
        dtype=tf.float32,
    )

    (
        _,
        relative_tf,
        _,
    ) = finite_volume_residual(
        model,
        X_tf,
        scale_tf,
        training=False,
    )

    relative = (
        relative_tf.numpy()
    )

    fv_relative_MAE = float(
        np.mean(
            np.abs(
                relative
            )
        )
    )

    fv_relative_RMS = float(
        np.sqrt(
            np.mean(
                relative ** 2
            )
        )
    )

    # -------------------------------------------------------------------------
    # Mass
    # -------------------------------------------------------------------------

    true_mass = np.trapezoid(
        truth,
        xi,
        axis=1,
    )

    pred_mass = np.trapezoid(
        prediction,
        xi,
        axis=1,
    )

    mass_relative = (
        np.abs(
            pred_mass
            - true_mass
        )
        /
        (
            np.abs(
                true_mass
            )
            + 1.0e-12
        )
    )

    mass_relative_MAE = float(
        np.mean(
            mass_relative
        )
    )

    mass_relative_max = float(
        np.max(
            mass_relative
        )
    )

    # -------------------------------------------------------------------------
    # Injector region
    # -------------------------------------------------------------------------

    injector_error = (
        prediction[
            :,
            :N_INJECTOR_NODES
        ]
        -
        truth[
            :,
            :N_INJECTOR_NODES
        ]
    )

    injector_L1 = float(
        np.mean(
            np.abs(
                injector_error
            )
        )
    )

    # -------------------------------------------------------------------------
    # Late time
    # -------------------------------------------------------------------------

    t_norm = (
        X_np[
            :,
            0,
            1
        ]
    )

    late_mask = (
        t_norm
        >= (2.0 / 3.0)
    )

    if np.any(
        late_mask
    ):

        late_error = (
            error[
                late_mask
            ]
        )

        late_L1 = float(
            np.mean(
                np.abs(
                    late_error
                )
            )
        )

    else:

        late_L1 = 0.0

    profile_L1 = np.mean(
        np.abs(
            error
        ),
        axis=1,
    )

    return {
        "truth":
            truth,

        "prediction":
            prediction,

        "error":
            error,

        "profile_L1":
            profile_L1,

        "L1":
            L1,

        "L2":
            L2,

        "Linf":
            Linf,

        "fv_relative_MAE":
            fv_relative_MAE,

        "fv_relative_RMS":
            fv_relative_RMS,

        "mass_relative_MAE":
            mass_relative_MAE,

        "mass_relative_max":
            mass_relative_max,

        "injector_L1":
            injector_L1,

        "late_L1":
            late_L1,

        "min_prediction":
            float(
                np.min(
                    prediction
                )
            ),

        "max_prediction":
            float(
                np.max(
                    prediction
                )
            ),
    }


# =============================================================================
# PHYSICS-AWARE CHECKPOINT SCORE
# =============================================================================

def validation_score(
    metrics,
):
    """
    Lower is better.

    Each term is normalized by the final desired performance scale.

    Physics receives the largest coefficient because the other categories
    already passed SG7B-7.
    """

    data_term = (
        metrics[
            "L1"
        ]
        / MAX_TEST_L1
    )

    physics_term = (
        metrics[
            "fv_relative_MAE"
        ]
        / TARGET_FV_RELATIVE_MAE
    )

    mass_term = (
        metrics[
            "mass_relative_MAE"
        ]
        / MAX_MASS_RELATIVE_MAE
    )

    injector_term = (
        metrics[
            "injector_L1"
        ]
        / MAX_INJECTOR_L1
    )

    late_term = (
        metrics[
            "late_L1"
        ]
        / MAX_LATE_L1
    )

    return float(
        SCORE_WEIGHT_DATA
        * data_term
        +
        SCORE_WEIGHT_PHYS
        * physics_term
        +
        SCORE_WEIGHT_MASS
        * mass_term
        +
        SCORE_WEIGHT_INJECTOR
        * injector_term
        +
        SCORE_WEIGHT_LATE
        * late_term
    )


# =============================================================================
# LEARNING-RATE SCHEDULE
# =============================================================================

def learning_rate_for_epoch(
    epoch,
):

    if epoch < LR_STAGE_2_EPOCH:

        return LR_STAGE_1

    if epoch < LR_STAGE_3_EPOCH:

        return LR_STAGE_2

    return LR_STAGE_3


# =============================================================================
# FINE-TUNE
# =============================================================================

def fine_tune(
    model,
    dataset,
):

    optimizer = (
        tf.keras.optimizers.Adam(
            learning_rate=(
                LR_STAGE_1
            )
        )
    )

    train_ds = make_tf_dataset(
        dataset[
            "X_train"
        ],
        dataset[
            "Y_train"
        ],
        True,
    )

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=float,
    )

    dxi = tf.constant(
        float(
            xi[1]
            - xi[0]
        ),
        dtype=tf.float32,
    )

    tD_scale_value = float(
        dataset[
            "tD_scale"
        ][0]
    )

    tD_scale_tf = tf.constant(
        tD_scale_value,
        dtype=tf.float32,
    )

    # -------------------------------------------------------------------------
    # PRE-FINE-TUNING VALIDATION
    # -------------------------------------------------------------------------

    baseline_val = evaluate_split(
        model,
        dataset[
            "X_val"
        ],
        dataset[
            "Y_val"
        ],
        xi,
        tD_scale_value,
    )

    baseline_test = evaluate_split(
        model,
        dataset[
            "X_test"
        ],
        dataset[
            "Y_test"
        ],
        xi,
        tD_scale_value,
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "PRE-FINE-TUNING AUTHORITATIVE BASELINE"
    )

    print(
        "=" * 78
    )

    print(
        f"Validation L1              : "
        f"{baseline_val['L1']:.6e}"
    )

    print(
        f"Validation FV relative MAE : "
        f"{baseline_val['fv_relative_MAE']:.6e}"
    )

    print(
        f"Test L1                    : "
        f"{baseline_test['L1']:.6e}"
    )

    print(
        f"Test FV relative MAE       : "
        f"{baseline_test['fv_relative_MAE']:.6e}"
    )

    print(
        f"Test FV / SG7A ratio       : "
        f"{baseline_test['fv_relative_MAE'] / SG7A_TRUTH_FV_RELATIVE_MAE:.3f}"
    )

    print(
        "=" * 78
    )

    # -------------------------------------------------------------------------
    # HISTORY
    # -------------------------------------------------------------------------

    history = {
        "epoch": [],
        "learning_rate": [],

        "train_total": [],
        "train_data": [],
        "train_phys": [],
        "train_mass": [],
        "train_injector": [],
        "train_late": [],

        "val_L1": [],
        "val_L2": [],
        "val_FV_MAE": [],
        "val_FV_RMS": [],
        "val_mass_MAE": [],
        "val_injector_L1": [],
        "val_late_L1": [],
        "val_score": [],
    }

    best_score = np.inf

    best_epoch = -1

    best_validation = None

    patience_counter = 0

    start_time = (
        time.perf_counter()
    )

    # -------------------------------------------------------------------------
    # TRAIN
    # -------------------------------------------------------------------------

    for epoch in range(
        EPOCHS
    ):

        lr = learning_rate_for_epoch(
            epoch
        )

        optimizer.learning_rate.assign(
            lr
        )

        train_values = []

        for (
            X_batch,
            Y_batch
        ) in train_ds:

            values = train_step(
                model,
                optimizer,
                X_batch,
                Y_batch,
                tD_scale_tf,
                dxi,
            )

            train_values.append(
                [
                    float(
                        value.numpy()
                    )
                    for value in values
                ]
            )

        train_values = np.mean(
            train_values,
            axis=0,
        )

        # ---------------------------------------------------------------------
        # Full validation metrics
        #
        # This is intentionally performed on the complete validation set
        # because checkpoint selection is the scientific decision variable.
        # ---------------------------------------------------------------------

        val_metrics = evaluate_split(
            model,
            dataset[
                "X_val"
            ],
            dataset[
                "Y_val"
            ],
            xi,
            tD_scale_value,
        )

        score = validation_score(
            val_metrics
        )

        # ---------------------------------------------------------------------
        # HISTORY
        # ---------------------------------------------------------------------

        history[
            "epoch"
        ].append(
            epoch + 1
        )

        history[
            "learning_rate"
        ].append(
            lr
        )

        train_keys = [
            "train_total",
            "train_data",
            "train_phys",
            "train_mass",
            "train_injector",
            "train_late",
        ]

        for (
            key,
            value
        ) in zip(
            train_keys,
            train_values,
        ):

            history[
                key
            ].append(
                float(
                    value
                )
            )

        history[
            "val_L1"
        ].append(
            val_metrics[
                "L1"
            ]
        )

        history[
            "val_L2"
        ].append(
            val_metrics[
                "L2"
            ]
        )

        history[
            "val_FV_MAE"
        ].append(
            val_metrics[
                "fv_relative_MAE"
            ]
        )

        history[
            "val_FV_RMS"
        ].append(
            val_metrics[
                "fv_relative_RMS"
            ]
        )

        history[
            "val_mass_MAE"
        ].append(
            val_metrics[
                "mass_relative_MAE"
            ]
        )

        history[
            "val_injector_L1"
        ].append(
            val_metrics[
                "injector_L1"
            ]
        )

        history[
            "val_late_L1"
        ].append(
            val_metrics[
                "late_L1"
            ]
        )

        history[
            "val_score"
        ].append(
            score
        )

        # ---------------------------------------------------------------------
        # CHECKPOINT
        # ---------------------------------------------------------------------

        data_guardrail = (
            val_metrics[
                "L1"
            ]
            < MAX_TEST_L1
        )

        mass_guardrail = (
            val_metrics[
                "mass_relative_MAE"
            ]
            < MAX_MASS_RELATIVE_MAE
        )

        injector_guardrail = (
            val_metrics[
                "injector_L1"
            ]
            < MAX_INJECTOR_L1
        )

        eligible = (
            data_guardrail
            and
            mass_guardrail
            and
            injector_guardrail
        )

        if (
            eligible
            and
            score < best_score
        ):

            best_score = (
                score
            )

            best_epoch = (
                epoch
                + 1
            )

            best_validation = (
                val_metrics.copy()
            )

            patience_counter = 0

            model.save_weights(
                BEST_WEIGHTS_FILE
            )

        else:

            patience_counter += 1

        # ---------------------------------------------------------------------
        # LOG
        # ---------------------------------------------------------------------

        if (
            epoch == 0
            or
            (
                epoch + 1
            ) % 10 == 0
        ):

            ratio = (
                val_metrics[
                    "fv_relative_MAE"
                ]
                /
                SG7A_TRUTH_FV_RELATIVE_MAE
            )

            print(
                f"Epoch "
                f"{epoch + 1:4d}/{EPOCHS} | "
                f"lr={lr:.2e} | "
                f"L1={val_metrics['L1']:.3e} | "
                f"FV={val_metrics['fv_relative_MAE']:.3e} | "
                f"ratio={ratio:6.1f} | "
                f"mass={val_metrics['mass_relative_MAE']:.3e} | "
                f"late={val_metrics['late_L1']:.3e} | "
                f"score={score:.3f}"
            )

        # ---------------------------------------------------------------------
        # EARLY TARGET HIT
        #
        # We still keep training until patience unless the model passes all
        # major validation targets with comfortable margin.
        # ---------------------------------------------------------------------

        comfortable_physics = (
            val_metrics[
                "fv_relative_MAE"
            ]
            < 0.028
        )

        comfortable_data = (
            val_metrics[
                "L1"
            ]
            < 0.018
        )

        comfortable_mass = (
            val_metrics[
                "mass_relative_MAE"
            ]
            < 0.025
        )

        if (
            comfortable_physics
            and
            comfortable_data
            and
            comfortable_mass
            and
            epoch >= 40
        ):

            print(
                "\nComfortable physics target reached."
            )

            print(
                "Ending fine-tuning early."
            )

            break

        # ---------------------------------------------------------------------
        # PATIENCE
        # ---------------------------------------------------------------------

        if (
            patience_counter
            >= PATIENCE
        ):

            print(
                "\nFine-tuning early stopping:"
            )

            print(
                f"  Best epoch              : "
                f"{best_epoch}"
            )

            print(
                f"  Best validation score   : "
                f"{best_score:.6e}"
            )

            break

    runtime = (
        time.perf_counter()
        - start_time
    )

    # -------------------------------------------------------------------------
    # SAVE HISTORY / FINAL MODEL
    # -------------------------------------------------------------------------

    np.savez_compressed(
        HISTORY_FILE,
        **{
            key:
                np.asarray(
                    value
                )
            for (
                key,
                value
            ) in history.items()
        },
    )

    model.save(
        FINAL_MODEL_FILE
    )

    if not BEST_WEIGHTS_FILE.exists():

        raise RuntimeError(
            "No eligible SG7B-6B checkpoint was created.\n"
            "Fine-tuning violated one or more guardrails."
        )

    model.load_weights(
        BEST_WEIGHTS_FILE
    )

    model.save(
        BEST_MODEL_FILE
    )

    return {
        "history":
            history,

        "runtime":
            runtime,

        "best_epoch":
            best_epoch,

        "best_score":
            best_score,

        "best_validation":
            best_validation,

        "baseline_validation":
            baseline_val,

        "baseline_test":
            baseline_test,
    }


# =============================================================================
# FINAL TEST VALIDATION
# =============================================================================

def validate_test_result(
    result,
):

    fv_ratio = (
        result[
            "fv_relative_MAE"
        ]
        /
        SG7A_TRUTH_FV_RELATIVE_MAE
    )

    checks = [
        (
            "Predictions finite",
            np.all(
                np.isfinite(
                    result[
                        "prediction"
                    ]
                )
            ),
        ),

        (
            "Saturation lower bound respected",
            result[
                "min_prediction"
            ]
            >= S_INITIAL
            - 1.0e-7,
        ),

        (
            "Saturation upper bound respected",
            result[
                "max_prediction"
            ]
            <= S_INJECTED
            + 1.0e-7,
        ),

        (
            "Held-out L1 < 0.020",
            result[
                "L1"
            ]
            < MAX_TEST_L1,
        ),

        (
            "FV relative MAE < 0.031616",
            result[
                "fv_relative_MAE"
            ]
            < MAX_FV_RELATIVE_MAE,
        ),

        (
            "PI-RNN / SG7A FV ratio < 50",
            fv_ratio
            < MAX_FV_RATIO,
        ),

        (
            "Mass relative MAE < 0.030",
            result[
                "mass_relative_MAE"
            ]
            < MAX_MASS_RELATIVE_MAE,
        ),

        (
            "Injector L1 < 0.015",
            result[
                "injector_L1"
            ]
            < MAX_INJECTOR_L1,
        ),

        (
            "Late-time L1 < 0.025",
            result[
                "late_L1"
            ]
            < MAX_LATE_L1,
        ),
    ]

    all_passed = all(
        passed
        for (
            _,
            passed
        ) in checks
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-6B VALIDATION"
    )

    print(
        "=" * 78
    )

    for (
        description,
        passed
    ) in checks:

        print(
            f"[{'PASS' if passed else 'FAIL':4s}] "
            f"{description}"
        )

    print(
        "=" * 78
    )

    print(
        f"SG7A FV relative MAE      : "
        f"{SG7A_TRUTH_FV_RELATIVE_MAE:.6e}"
    )

    print(
        f"PI-RNN FV relative MAE    : "
        f"{result['fv_relative_MAE']:.6e}"
    )

    print(
        f"PI-RNN / SG7A FV ratio    : "
        f"{fv_ratio:.3f}"
    )

    return (
        all_passed,
        float(
            fv_ratio
        ),
    )


# =============================================================================
# PLOTS
# =============================================================================

def plot_training_history(
    history,
):

    epoch = np.asarray(
        history[
            "epoch"
        ]
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.semilogy(
        epoch,
        history[
            "val_L1"
        ],
        label="Validation L1",
    )

    ax.semilogy(
        epoch,
        history[
            "val_FV_MAE"
        ],
        label="Validation FV MAE",
    )

    ax.semilogy(
        epoch,
        history[
            "val_mass_MAE"
        ],
        label="Validation mass MAE",
    )

    ax.semilogy(
        epoch,
        history[
            "val_late_L1"
        ],
        label="Validation late-time L1",
    )

    ax.axhline(
        TARGET_FV_RELATIVE_MAE,
        linestyle="--",
        label="FV freeze target",
    )

    ax.set_xlabel(
        "Fine-tuning epoch"
    )

    ax.set_ylabel(
        "Metric"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6B\n"
        "Physics-Dominant Fine-Tuning"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6B_Training_History.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_test_profiles(
    dataset,
    result,
):

    xi = (
        dataset[
            "xi"
        ]
    )

    tD = (
        dataset[
            "tD_test"
        ]
    )

    positions = np.linspace(
        0,
        len(tD) - 1,
        6,
        dtype=int,
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            7,
        )
    )

    for p in positions:

        ax.plot(
            xi,
            result[
                "truth"
            ][p],
            linewidth=2.0,
            label=(
                "SG7A "
                f"tD={tD[p]:.2f}"
            ),
        )

        ax.plot(
            xi,
            result[
                "prediction"
            ][p],
            linestyle="--",
            linewidth=1.4,
            label=(
                "SG7B-6B "
                f"tD={tD[p]:.2f}"
            ),
        )

    ax.set_xlabel(
        r"TOF coordinate $\xi$"
    )

    ax.set_ylabel(
        "Saturation"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6B\n"
        "Held-Out Fine-Tuned PI-RNN Profiles"
    )

    ax.legend(
        fontsize=7,
        ncol=2,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6B_Test_Profiles.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_error_vs_time(
    dataset,
    result,
):

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        dataset[
            "tD_test"
        ],
        result[
            "profile_L1"
        ],
    )

    ax.axhline(
        MAX_TEST_L1,
        linestyle="--",
        label="L1 guardrail",
    )

    ax.set_xlabel(
        r"$t_D$"
    )

    ax.set_ylabel(
        "Profile L1 error"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6B\n"
        "Held-Out Error vs Dimensionless Time"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6B_Error_vs_tD.png",
        dpi=300,
    )

    plt.close(
        fig
    )


# =============================================================================
# SAVE RESULTS
# =============================================================================

def save_test_results(
    dataset,
    result,
):

    np.savez_compressed(
        TEST_RESULTS_FILE,

        xi=
            dataset[
                "xi"
            ],

        tD_test=
            dataset[
                "tD_test"
            ],

        truth=
            result[
                "truth"
            ],

        prediction=
            result[
                "prediction"
            ],

        error=
            result[
                "error"
            ],

        profile_L1=
            result[
                "profile_L1"
            ],
    )


# =============================================================================
# SUMMARY
# =============================================================================

def save_summary(
    training,
    test_result,
    validation_passed,
    fv_ratio,
):

    baseline = (
        training[
            "baseline_test"
        ]
    )

    summary = {
        "milestone":
            "V15-SG7B-6B",

        "description":
            (
                "Targeted physics-dominant fine-tuning "
                "of the SG7B-6 reference PI-RNN"
            ),

        "source_model":
            "V15SG7B6_Best_Model.keras",

        "architecture_changed":
            False,

        "architecture": {
            "type":
                "plain stacked LSTM",

            "fourier_features":
                False,

            "film":
                False,

            "front_coordinate":
                False,
        },

        "physics_target": {
            "SG7A_truth_FV_relative_MAE":
                SG7A_TRUTH_FV_RELATIVE_MAE,

            "maximum_allowed_ratio":
                MAX_FV_RATIO,

            "required_PI_RNN_FV_relative_MAE":
                TARGET_FV_RELATIVE_MAE,
        },

        "fine_tuning": {
            "epochs_requested":
                EPOCHS,

            "best_epoch":
                int(
                    training[
                        "best_epoch"
                    ]
                ),

            "runtime_seconds":
                float(
                    training[
                        "runtime"
                    ]
                ),

            "physics_loss_weight":
                LAMBDA_PHYS,

            "learning_rate_stage_1":
                LR_STAGE_1,

            "learning_rate_stage_2":
                LR_STAGE_2,

            "learning_rate_stage_3":
                LR_STAGE_3,
        },

        "pre_finetuning_test": {
            "L1":
                baseline[
                    "L1"
                ],

            "FV_relative_MAE":
                baseline[
                    "fv_relative_MAE"
                ],

            "mass_relative_MAE":
                baseline[
                    "mass_relative_MAE"
                ],
        },

        "post_finetuning_test": {
            "L1":
                test_result[
                    "L1"
                ],

            "L2":
                test_result[
                    "L2"
                ],

            "Linf":
                test_result[
                    "Linf"
                ],

            "FV_relative_MAE":
                test_result[
                    "fv_relative_MAE"
                ],

            "FV_relative_RMS":
                test_result[
                    "fv_relative_RMS"
                ],

            "FV_ratio_to_SG7A":
                fv_ratio,

            "mass_relative_MAE":
                test_result[
                    "mass_relative_MAE"
                ],

            "mass_relative_max":
                test_result[
                    "mass_relative_max"
                ],

            "injector_L1":
                test_result[
                    "injector_L1"
                ],

            "late_time_L1":
                test_result[
                    "late_L1"
                ],

            "minimum_prediction":
                test_result[
                    "min_prediction"
                ],

            "maximum_prediction":
                test_result[
                    "max_prediction"
                ],
        },

        "validation_passed":
            bool(
                validation_passed
            ),

        "status":
            (
                "PASS_CANDIDATE_FOR_SG7B7"
                if validation_passed
                else
                "TARGET_NOT_REACHED"
            ),

        "next_milestone":
            (
                "Rerun V15-SG7B-7 final validation "
                "using V15SG7B6B_Best_Model.keras"
                if validation_passed
                else
                "Review SG7B-6B physics optimization "
                "before changing architecture"
            ),
    }

    with open(
        SUMMARY_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            summary,
            f,
            indent=2,
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        + "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7B-6B"
    )

    print(
        "Targeted Physics-Dominant PI-RNN Fine-Tuning"
    )

    print(
        "=" * 78
    )

    print(
        f"\nTensorFlow version       : "
        f"{tf.__version__}"
    )

    print(
        "\nAUTHORITATIVE PHYSICS TARGET"
    )

    print(
        f"  SG7A FV relative MAE    : "
        f"{SG7A_TRUTH_FV_RELATIVE_MAE:.6e}"
    )

    print(
        f"  Maximum ratio           : "
        f"{MAX_FV_RATIO:.1f}"
    )

    print(
        f"  Required PI-RNN FV MAE  : "
        f"< {TARGET_FV_RELATIVE_MAE:.6e}"
    )

    print(
        "\nFINE-TUNING"
    )

    print(
        f"  Starting model          : "
        f"V15SG7B6_Best_Model.keras"
    )

    print(
        f"  Physics loss weight     : "
        f"{LAMBDA_PHYS}"
    )

    print(
        f"  Initial learning rate   : "
        f"{LR_STAGE_1:.1e}"
    )

    print(
        f"  Maximum epochs          : "
        f"{EPOCHS}"
    )

    # -------------------------------------------------------------------------
    # LOAD
    # -------------------------------------------------------------------------

    dataset = load_dataset()

    if not SOURCE_MODEL_FILE.exists():

        raise FileNotFoundError(
            "SG7B-6 source model missing:\n"
            f"{SOURCE_MODEL_FILE}"
        )

    model = (
        tf.keras.models.load_model(
            SOURCE_MODEL_FILE
        )
    )

    print(
        "\nSOURCE MODEL"
    )

    print(
        "  Model load              : PASS"
    )

    print(
        f"  Trainable parameters    : "
        f"{model.count_params():,}"
    )

    # -------------------------------------------------------------------------
    # FINE-TUNE
    # -------------------------------------------------------------------------

    training = fine_tune(
        model,
        dataset,
    )

    print(
        "\nFINE-TUNING COMPLETE"
    )

    print(
        f"  Runtime                 : "
        f"{training['runtime']:.2f} s"
    )

    print(
        f"  Best epoch              : "
        f"{training['best_epoch']}"
    )

    print(
        f"  Best validation score   : "
        f"{training['best_score']:.6e}"
    )

    # -------------------------------------------------------------------------
    # LOAD BEST
    # -------------------------------------------------------------------------

    best_model = (
        tf.keras.models.load_model(
            BEST_MODEL_FILE
        )
    )

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=float,
    )

    tD_scale = float(
        dataset[
            "tD_scale"
        ][0]
    )

    result = evaluate_split(
        best_model,
        dataset[
            "X_test"
        ],
        dataset[
            "Y_test"
        ],
        xi,
        tD_scale,
    )

    print(
        "\nPOST-FINE-TUNING HELD-OUT TEST"
    )

    print(
        f"  L1                      : "
        f"{result['L1']:.6e}"
    )

    print(
        f"  L2                      : "
        f"{result['L2']:.6e}"
    )

    print(
        f"  Linf                    : "
        f"{result['Linf']:.6e}"
    )

    print(
        f"  FV relative MAE         : "
        f"{result['fv_relative_MAE']:.6e}"
    )

    print(
        f"  FV relative RMS         : "
        f"{result['fv_relative_RMS']:.6e}"
    )

    print(
        f"  Mass relative MAE       : "
        f"{result['mass_relative_MAE']:.6e}"
    )

    print(
        f"  Injector L1             : "
        f"{result['injector_L1']:.6e}"
    )

    print(
        f"  Late-time L1            : "
        f"{result['late_L1']:.6e}"
    )

    # -------------------------------------------------------------------------
    # VALIDATE
    # -------------------------------------------------------------------------

    (
        validation_passed,
        fv_ratio,
    ) = validate_test_result(
        result
    )

    # -------------------------------------------------------------------------
    # OUTPUTS
    # -------------------------------------------------------------------------

    plot_training_history(
        training[
            "history"
        ]
    )

    plot_test_profiles(
        dataset,
        result,
    )

    plot_error_vs_time(
        dataset,
        result,
    )

    save_test_results(
        dataset,
        result,
    )

    save_summary(
        training,
        result,
        validation_passed,
        fv_ratio,
    )

    print(
        "\nOUTPUTS"
    )

    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print(
        "\nModels:"
    )

    print(
        "  V15SG7B6B_Best_Model.keras"
    )

    print(
        "  V15SG7B6B_Final_Model.keras"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B6B_Training_History.png"
    )

    print(
        "  V15SG7B6B_Test_Profiles.png"
    )

    print(
        "  V15SG7B6B_Error_vs_tD.png"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B6B_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    if validation_passed:

        print(
            "V15-SG7B-6B VALIDATION: PASS"
        )

        print()

        print(
            "STATUS: READY TO RE-RUN SG7B-7"
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7B-7R — Final PI-RNN "
            "Freeze Validation Using SG7B-6B"
        )

    else:

        print(
            "V15-SG7B-6B VALIDATION: "
            "TARGET NOT REACHED"
        )

        print()

        print(
            "DO NOT CHANGE ARCHITECTURE YET."
        )

        print()

        print(
            "Review the fine-tuning trajectory "
            "before deciding the next refinement."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()