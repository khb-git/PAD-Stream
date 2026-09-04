from pathlib import Path
import json
import time
import zipfile
import shutil

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7B-4
# Reference-Case Plain-LSTM PI-RNN Training
#
# CORRECTED SERIALIZATION-SAFE VERSION
#
# PURPOSE
# -------
# Train the first PAD-Stream full-physics PI-RNN against the frozen
# SG7A master transport solution.
#
# Input:
#
#       [xi, normalized tD]
#
# Output:
#
#       S(xi,tD)
#
#
# LOSS
# ----
#
#   L =
#       lambda_data * L_data
#       +
#       lambda_phys * L_FV
#       +
#       lambda_bc * L_BC
#       +
#       lambda_mass * L_mass
#
#
# PRIMARY PHYSICS LOSS
# --------------------
# Conservative finite-volume residual approved in V15-SG7B-2.
#
#
# IMPORTANT CORRECTION
# --------------------
# The previous version used an anonymous Keras Lambda layer for:
#
#       S = Smin + (Smax-Smin) sigmoid(z)
#
# TensorFlow/Keras 2.21 could save that model but could not reload it because
# the Lambda output shape could not be reconstructed.
#
# This version uses only standard serializable Keras layers:
#
#       Activation("sigmoid")
#       +
#       Rescaling
#
#
# RECOVERY
# --------
# If the previous SG7B-4 training run already exists, this script attempts
# to recover the trained checkpoint automatically.
#
# It:
#
#   1. extracts model.weights.h5 from the old .keras archive,
#   2. loads those weights into a legacy-compatible model,
#   3. transfers weighted layers into the corrected model,
#   4. evaluates the test set,
#   5. saves a clean serializable model.
#
# Therefore the completed training run does not need to be repeated unless
# recovery fails or FORCE_RETRAIN = True.
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

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B4"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# -----------------------------------------------------------------------------
# Legacy outputs from the first SG7B-4 run
# -----------------------------------------------------------------------------

LEGACY_BEST_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B4_Best_Model.keras"
)

LEGACY_FINAL_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B4_Final_Model.keras"
)


# -----------------------------------------------------------------------------
# Corrected outputs
# -----------------------------------------------------------------------------

BEST_WEIGHTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B4_Best.weights.h5"
)

RECOVERED_WEIGHTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B4_Best_Recovered.weights.h5"
)

BEST_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B4_Best_Model_Serializable.keras"
)

FINAL_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B4_Final_Model_Serializable.keras"
)

HISTORY_FILE = (
    OUTPUT_DIR
    / "V15SG7B4_Training_History.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B4_Summary.json"
)

TEST_RESULTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B4_Test_Results.npz"
)


# =============================================================================
# EXECUTION MODE
# =============================================================================

# False:
#   attempt to recover the already-completed training run first.
#
# True:
#   ignore old checkpoints and retrain from scratch.

FORCE_RETRAIN = False


# =============================================================================
# REPRODUCIBILITY
# =============================================================================

SEED = 14071789

np.random.seed(
    SEED
)

tf.random.set_seed(
    SEED
)


# =============================================================================
# FROZEN SG7A / SG7B PHYSICS
# =============================================================================

SWC = 0.20
SOR = 0.20

S_INITIAL = SWC
S_INJECTED = (
    1.0
    - SOR
)

MOBILE_SATURATION_RANGE = (
    S_INJECTED
    - S_INITIAL
)

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
# NETWORK
# =============================================================================

SEQUENCE_LENGTH = 201

INPUT_FEATURES = 2

HIDDEN_SIZE = 64

N_LSTM_LAYERS = 2

DROPOUT = 0.0


# =============================================================================
# TRAINING
# =============================================================================

EPOCHS = 400

BATCH_SIZE = 32

LEARNING_RATE = 1.0e-3

PATIENCE = 60

GRADIENT_CLIP_NORM = 5.0


# -----------------------------------------------------------------------------
# Loss weights
# -----------------------------------------------------------------------------

LAMBDA_DATA = 1.0

LAMBDA_PHYS_MAX = 0.05

LAMBDA_BC_LOSS = 1.0

LAMBDA_MASS = 2.0


# -----------------------------------------------------------------------------
# Physics warm-up
# -----------------------------------------------------------------------------

PHYS_WARMUP_START = 20

PHYS_WARMUP_END = 100


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

    dataset = {
        key: data[key]
        for key in required
    }

    return dataset


# =============================================================================
# PHYSICS FUNCTIONS
# =============================================================================

@tf.function
def effective_saturation_tf(
    S,
):

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
def fractional_flow_tf(
    S,
):

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


# =============================================================================
# BROOKS-COREY DIFFUSION SHAPE
# =============================================================================

@tf.function
def diffusion_shape_tf(
    S,
):

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
    # Frozen normalization:
    #
    # D_tilde(Se=0.5) = 1
    # -------------------------------------------------------------------------

    Se_mid = 0.5

    kr_disp_mid = (
        KR_DISP_MAX
        * Se_mid ** N_DISP
    )

    kr_res_mid = (
        KR_RES_MAX
        * (
            1.0
            - Se_mid
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
# CORRECTED SERIALIZATION-SAFE MODEL
# =============================================================================

def build_model():
    """
    Corrected SG7B-4 model.

    Architecture:

        [xi, normalized tD]
                |
              LSTM
                |
              LSTM
                |
        TimeDistributed Dense
                |
            sigmoid
                |
            Rescaling
                |
        physical saturation

    There are NO:
        - Fourier features
        - FiLM layers
        - front-location inputs
        - anonymous Lambda layers
    """

    inputs = tf.keras.Input(
        shape=(
            SEQUENCE_LENGTH,
            INPUT_FEATURES,
        ),
        name="xi_tD_sequence",
    )

    x = inputs

    for layer_id in range(
        N_LSTM_LAYERS
    ):

        x = tf.keras.layers.LSTM(
            HIDDEN_SIZE,
            return_sequences=True,
            dropout=DROPOUT,
            name=(
                f"lstm_{layer_id + 1}"
            ),
        )(x)

    raw = (
        tf.keras.layers.TimeDistributed(
            tf.keras.layers.Dense(
                1
            ),
            name="raw_saturation",
        )(x)
    )

    sigmoid_output = (
        tf.keras.layers.Activation(
            "sigmoid",
            name="saturation_sigmoid",
        )(raw)
    )

    outputs = (
        tf.keras.layers.Rescaling(
            scale=(
                MOBILE_SATURATION_RANGE
            ),
            offset=(
                S_INITIAL
            ),
            name="physical_saturation",
        )(sigmoid_output)
    )

    model = tf.keras.Model(
        inputs=inputs,
        outputs=outputs,
        name=(
            "PAD_Stream_"
            "V15SG7B4_PIRNN"
        ),
    )

    return model


# =============================================================================
# LEGACY MODEL USED ONLY FOR CHECKPOINT RECOVERY
# =============================================================================

def build_legacy_recovery_model():
    """
    Reproduce the weighted-layer topology of the original SG7B-4 model.

    The Lambda layer includes an explicit output_shape here so the model itself
    can exist safely in TensorFlow 2.21.

    We do NOT save this model.

    Its only purpose is to load the old trained weights and transfer:

        lstm_1
        lstm_2
        raw_saturation

    into the corrected serialization-safe model.
    """

    inputs = tf.keras.Input(
        shape=(
            SEQUENCE_LENGTH,
            INPUT_FEATURES,
        ),
        name="xi_tD_sequence",
    )

    x = inputs

    for layer_id in range(
        N_LSTM_LAYERS
    ):

        x = tf.keras.layers.LSTM(
            HIDDEN_SIZE,
            return_sequences=True,
            dropout=DROPOUT,
            name=(
                f"lstm_{layer_id + 1}"
            ),
        )(x)

    raw = (
        tf.keras.layers.TimeDistributed(
            tf.keras.layers.Dense(
                1
            ),
            name="raw_saturation",
        )(x)
    )

    outputs = tf.keras.layers.Lambda(
        lambda z:
        (
            S_INITIAL
            +
            MOBILE_SATURATION_RANGE
            * tf.sigmoid(z)
        ),
        output_shape=(
            SEQUENCE_LENGTH,
            1,
        ),
        name="physical_saturation",
    )(raw)

    return tf.keras.Model(
        inputs=inputs,
        outputs=outputs,
        name=(
            "PAD_Stream_"
            "V15SG7B4_LegacyRecovery"
        ),
    )


# =============================================================================
# EXTRACT WEIGHTS FROM OLD KERAS ARCHIVE
# =============================================================================

def extract_legacy_weights(
    model_file,
    output_weights,
):

    if not model_file.exists():

        return False

    print(
        "\nAttempting recovery from:"
    )

    print(
        f"  {model_file}"
    )

    try:

        with zipfile.ZipFile(
            model_file,
            "r",
        ) as archive:

            names = (
                archive.namelist()
            )

            weight_name = None

            for name in names:

                if name.endswith(
                    "model.weights.h5"
                ):

                    weight_name = name

                    break

            if weight_name is None:

                print(
                    "  Could not locate "
                    "model.weights.h5."
                )

                return False

            with archive.open(
                weight_name
            ) as source:

                with open(
                    output_weights,
                    "wb",
                ) as destination:

                    shutil.copyfileobj(
                        source,
                        destination,
                    )

        print(
            "  Legacy weights extracted."
        )

        print(
            f"  {output_weights}"
        )

        return True

    except Exception as exc:

        print(
            "\nLegacy checkpoint extraction failed:"
        )

        print(
            f"  {exc}"
        )

        return False


# =============================================================================
# TRANSFER LEGACY WEIGHTS
# =============================================================================

def recover_trained_model(
    corrected_model,
):
    """
    Attempt to recover the previously completed SG7B-4 run.

    Returns:
        success
        history
        best_epoch
        best_val
    """

    if FORCE_RETRAIN:

        return (
            False,
            None,
            None,
            None,
        )

    if not (
        LEGACY_BEST_MODEL_FILE.exists()
        and HISTORY_FILE.exists()
    ):

        print(
            "\nNo complete legacy checkpoint/history "
            "pair found."
        )

        return (
            False,
            None,
            None,
            None,
        )

    extracted = (
        extract_legacy_weights(
            LEGACY_BEST_MODEL_FILE,
            RECOVERED_WEIGHTS_FILE,
        )
    )

    if not extracted:

        return (
            False,
            None,
            None,
            None,
        )

    try:

        legacy_model = (
            build_legacy_recovery_model()
        )

        legacy_model.load_weights(
            RECOVERED_WEIGHTS_FILE
        )

        weighted_layer_names = [
            "lstm_1",
            "lstm_2",
            "raw_saturation",
        ]

        for layer_name in (
            weighted_layer_names
        ):

            source_layer = (
                legacy_model.get_layer(
                    layer_name
                )
            )

            target_layer = (
                corrected_model.get_layer(
                    layer_name
                )
            )

            target_layer.set_weights(
                source_layer.get_weights()
            )

        history_data = np.load(
            HISTORY_FILE
        )

        history = {
            key:
                history_data[
                    key
                ].tolist()
            for key
            in history_data.files
        }

        if (
            "val_data"
            not in history
        ):

            raise KeyError(
                "Training history does not "
                "contain val_data."
            )

        val_data = np.asarray(
            history[
                "val_data"
            ],
            dtype=float,
        )

        best_position = int(
            np.argmin(
                val_data
            )
        )

        best_epoch = (
            best_position
            + 1
        )

        best_val = float(
            val_data[
                best_position
            ]
        )

        corrected_model.save_weights(
            BEST_WEIGHTS_FILE
        )

        corrected_model.save(
            BEST_MODEL_FILE
        )

        print(
            "\n"
            + "=" * 78
        )

        print(
            "LEGACY SG7B-4 TRAINING RUN RECOVERED"
        )

        print(
            "=" * 78
        )

        print(
            f"  Best epoch              : "
            f"{best_epoch}"
        )

        print(
            f"  Best validation MSE     : "
            f"{best_val:.6e}"
        )

        print(
            "\nCorrected serializable model:"
        )

        print(
            f"  {BEST_MODEL_FILE}"
        )

        print(
            "=" * 78
        )

        return (
            True,
            history,
            best_epoch,
            best_val,
        )

    except Exception as exc:

        print(
            "\nLegacy checkpoint recovery "
            "failed:"
        )

        print(
            f"  {exc}"
        )

        print(
            "\nThe script will fall back "
            "to retraining."
        )

        return (
            False,
            None,
            None,
            None,
        )


# =============================================================================
# MODEL INPUT AT ARBITRARY tD
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

    n_nodes = (
        tf.shape(
            xi
        )[1]
    )

    normalized_time = (
        tf.reshape(
            normalized_time,
            (
                -1,
                1,
                1,
            ),
        )
    )

    t_feature = tf.tile(
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
            t_feature,
        ],
        axis=2,
    )


# =============================================================================
# DIFFERENTIABLE CONSERVATIVE FV RESIDUAL
# =============================================================================

def finite_volume_residual(
    model,
    X,
    tD_scale,
    training,
):

    dtype = tf.float32

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
    # Actual dimensionless time
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

    # Frozen SG7A stored 801 snapshots
    # across the full master tD interval.
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

    tn_minus = (
        t_minus
        / tD_scale
    )

    tn_plus = (
        t_plus
        / tD_scale
    )

    X_minus = (
        build_input_for_time(
            X,
            tn_minus,
        )
    )

    X_plus = (
        build_input_for_time(
            X,
            tn_plus,
        )
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

    # -------------------------------------------------------------------------
    # Temporal derivative
    # -------------------------------------------------------------------------

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

    batch_size = (
        tf.shape(
            S
        )[0]
    )

    # -------------------------------------------------------------------------
    # Conservative advective face flux
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
                dtype=dtype,
            )
        )
    )

    F_left = (
        tf.ones(
            (
                batch_size,
                1,
            ),
            dtype=dtype,
        )
        *
        (
            u_face[0]
            * f_injected
        )
    )

    # Positive velocity and monotone fractional flow:
    #
    # upstream cell gives Godunov flux.
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
    # Capillary face flux
    # -------------------------------------------------------------------------

    D_cell = (
        diffusion_shape_tf(
            S
        )
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

    grad_internal = (
        S[
            :,
            1:
        ]
        -
        S[
            :,
            :-1
        ]
    ) / dxi

    G_internal = (
        POROSITY
        / PE_C
        *
        D_internal
        *
        grad_internal
    )

    # -------------------------------------------------------------------------
    # Left capillary boundary
    # -------------------------------------------------------------------------

    D_injected = (
        diffusion_shape_tf(
            tf.constant(
                S_INJECTED,
                dtype=dtype,
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

    grad_left = (
        S[
            :,
            0
        ]
        -
        S_INJECTED
    ) / (
        0.5
        * dxi
    )

    G_left = (
        POROSITY
        / PE_C
        *
        D_left
        *
        grad_left
    )[
        :,
        None
    ]

    # -------------------------------------------------------------------------
    # Outlet:
    # zero capillary diffusive flux
    # -------------------------------------------------------------------------

    G_right = tf.zeros(
        (
            batch_size,
            1,
        ),
        dtype=dtype,
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

    # -------------------------------------------------------------------------
    # Conservative residual
    # -------------------------------------------------------------------------

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

    relative_residual = (
        residual
        / scale
    )

    return (
        residual,
        relative_residual,
        S,
    )


# =============================================================================
# DATA LOSS
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


# =============================================================================
# INITIAL / BOUNDARY LOSS
# =============================================================================

def boundary_loss(
    model,
    X,
    training,
):
    """
    Constrain:

        1. frozen SG7A tD=0 initial state
        2. outlet zero-gradient behavior
    """

    batch_size = (
        tf.shape(
            X
        )[0]
    )

    # -------------------------------------------------------------------------
    # Initial state
    # -------------------------------------------------------------------------

    zero_time = tf.zeros(
        (
            batch_size,
        ),
        dtype=tf.float32,
    )

    X_zero = (
        build_input_for_time(
            X,
            zero_time,
        )
    )

    S_zero = (
        model(
            X_zero,
            training=training,
        )[
            :,
            :,
            0
        ]
    )

    target_zero = (
        tf.ones_like(
            S_zero
        )
        * S_INITIAL
    )

    first_column = (
        tf.ones(
            (
                batch_size,
                1,
            ),
            dtype=tf.float32,
        )
        * S_INJECTED
    )

    target_zero = tf.concat(
        [
            first_column,
            target_zero[
                :,
                1:
            ],
        ],
        axis=1,
    )

    L_initial = (
        tf.reduce_mean(
            tf.square(
                S_zero
                - target_zero
            )
        )
    )

    # -------------------------------------------------------------------------
    # Outlet zero-gradient capillary behavior
    # -------------------------------------------------------------------------

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

    outlet_gradient = (
        S[
            :,
            -1
        ]
        -
        S[
            :,
            -2
        ]
    )

    L_outlet = (
        tf.reduce_mean(
            tf.square(
                outlet_gradient
            )
        )
    )

    return (
        L_initial
        +
        L_outlet
    )


# =============================================================================
# GLOBAL MASS / STORAGE LOSS
# =============================================================================

def trapezoid_integral(
    S,
    dxi,
):

    interior = (
        tf.reduce_sum(
            S[
                :,
                1:-1
            ],
            axis=1,
        )
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


def mass_loss(
    Y_true,
    Y_pred,
    dxi,
):

    true_profile = (
        Y_true[
            :,
            :,
            0
        ]
    )

    pred_profile = (
        Y_pred[
            :,
            :,
            0
        ]
    )

    true_mass = (
        trapezoid_integral(
            true_profile,
            dxi,
        )
    )

    pred_mass = (
        trapezoid_integral(
            pred_profile,
            dxi,
        )
    )

    return (
        tf.reduce_mean(
            tf.square(
                pred_mass
                - true_mass
            )
        )
    )


# =============================================================================
# PHYSICS WARM-UP
# =============================================================================

def physics_weight(
    epoch,
):

    if (
        epoch
        < PHYS_WARMUP_START
    ):

        return 0.0

    if (
        epoch
        >= PHYS_WARMUP_END
    ):

        return (
            LAMBDA_PHYS_MAX
        )

    fraction = (
        epoch
        - PHYS_WARMUP_START
    ) / (
        PHYS_WARMUP_END
        - PHYS_WARMUP_START
    )

    return (
        LAMBDA_PHYS_MAX
        * fraction
    )


# =============================================================================
# TRAINING STEP
# =============================================================================

@tf.function
def train_step(
    model,
    optimizer,
    X,
    Y,
    tD_scale,
    lambda_phys,
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
            relative_residual,
            _,
        ) = finite_volume_residual(
            model,
            X,
            tD_scale,
            training=True,
        )

        L_phys = (
            tf.reduce_mean(
                tf.square(
                    relative_residual
                )
            )
        )

        L_bc = boundary_loss(
            model,
            X,
            training=True,
        )

        L_mass = mass_loss(
            Y,
            Y_pred,
            dxi,
        )

        total = (
            LAMBDA_DATA
            * L_data
            +
            lambda_phys
            * L_phys
            +
            LAMBDA_BC_LOSS
            * L_bc
            +
            LAMBDA_MASS
            * L_mass
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
        L_bc,
        L_mass,
    )


# =============================================================================
# VALIDATION STEP
# =============================================================================

@tf.function
def validation_step(
    model,
    X,
    Y,
    tD_scale,
    lambda_phys,
    dxi,
):

    Y_pred = model(
        X,
        training=False,
    )

    L_data = data_loss(
        Y,
        Y_pred,
    )

    (
        _,
        relative_residual,
        _,
    ) = finite_volume_residual(
        model,
        X,
        tD_scale,
        training=False,
    )

    L_phys = (
        tf.reduce_mean(
            tf.square(
                relative_residual
            )
        )
    )

    L_bc = boundary_loss(
        model,
        X,
        training=False,
    )

    L_mass = mass_loss(
        Y,
        Y_pred,
        dxi,
    )

    total = (
        LAMBDA_DATA
        * L_data
        +
        lambda_phys
        * L_phys
        +
        LAMBDA_BC_LOSS
        * L_bc
        +
        LAMBDA_MASS
        * L_mass
    )

    return (
        total,
        L_data,
        L_phys,
        L_bc,
        L_mass,
    )


# =============================================================================
# DATA PIPELINE
# =============================================================================

def make_tf_dataset(
    X,
    Y,
    training,
):

    ds = (
        tf.data.Dataset
        .from_tensor_slices(
            (
                X.astype(
                    np.float32
                ),
                Y.astype(
                    np.float32
                ),
            )
        )
    )

    if training:

        ds = ds.shuffle(
            buffer_size=(
                len(X)
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
# TRAIN MODEL
# =============================================================================

def train_model(
    model,
    dataset,
):

    optimizer = (
        tf.keras.optimizers.Adam(
            learning_rate=(
                LEARNING_RATE
            )
        )
    )

    train_ds = (
        make_tf_dataset(
            dataset[
                "X_train"
            ],
            dataset[
                "Y_train"
            ],
            True,
        )
    )

    val_ds = (
        make_tf_dataset(
            dataset[
                "X_val"
            ],
            dataset[
                "Y_val"
            ],
            False,
        )
    )

    tD_scale = tf.constant(
        float(
            dataset[
                "tD_scale"
            ][0]
        ),
        dtype=tf.float32,
    )

    xi = dataset[
        "xi"
    ]

    dxi = tf.constant(
        float(
            xi[1]
            - xi[0]
        ),
        dtype=tf.float32,
    )

    history = {
        "epoch": [],
        "lambda_phys": [],

        "train_total": [],
        "train_data": [],
        "train_phys": [],
        "train_bc": [],
        "train_mass": [],

        "val_total": [],
        "val_data": [],
        "val_phys": [],
        "val_bc": [],
        "val_mass": [],
    }

    best_val = np.inf

    best_epoch = -1

    patience_counter = 0

    start_time = (
        time.perf_counter()
    )

    for epoch in range(
        EPOCHS
    ):

        lambda_phys = (
            physics_weight(
                epoch
            )
        )

        lambda_phys_tf = (
            tf.constant(
                lambda_phys,
                dtype=tf.float32,
            )
        )

        # ---------------------------------------------------------------------
        # TRAIN
        # ---------------------------------------------------------------------

        train_metrics = []

        for (
            X_batch,
            Y_batch
        ) in train_ds:

            values = train_step(
                model,
                optimizer,
                X_batch,
                Y_batch,
                tD_scale,
                lambda_phys_tf,
                dxi,
            )

            train_metrics.append(
                [
                    float(
                        value.numpy()
                    )
                    for value in values
                ]
            )

        train_metrics = np.mean(
            train_metrics,
            axis=0,
        )

        # ---------------------------------------------------------------------
        # VALIDATION
        # ---------------------------------------------------------------------

        val_metrics = []

        for (
            X_batch,
            Y_batch
        ) in val_ds:

            values = (
                validation_step(
                    model,
                    X_batch,
                    Y_batch,
                    tD_scale,
                    lambda_phys_tf,
                    dxi,
                )
            )

            val_metrics.append(
                [
                    float(
                        value.numpy()
                    )
                    for value in values
                ]
            )

        val_metrics = np.mean(
            val_metrics,
            axis=0,
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
            "lambda_phys"
        ].append(
            lambda_phys
        )

        train_keys = [
            "train_total",
            "train_data",
            "train_phys",
            "train_bc",
            "train_mass",
        ]

        for (
            key,
            value
        ) in zip(
            train_keys,
            train_metrics,
        ):

            history[
                key
            ].append(
                float(
                    value
                )
            )

        val_keys = [
            "val_total",
            "val_data",
            "val_phys",
            "val_bc",
            "val_mass",
        ]

        for (
            key,
            value
        ) in zip(
            val_keys,
            val_metrics,
        ):

            history[
                key
            ].append(
                float(
                    value
                )
            )

        # ---------------------------------------------------------------------
        # BEST CHECKPOINT
        #
        # Keep same selection criterion as the first run:
        # validation data MSE.
        #
        # SG7B-5 will determine whether a physics-aware checkpoint metric
        # should replace this later.
        # ---------------------------------------------------------------------

        validation_target = (
            val_metrics[1]
        )

        if (
            validation_target
            < best_val
        ):

            best_val = float(
                validation_target
            )

            best_epoch = (
                epoch + 1
            )

            patience_counter = 0

            # Save weights only during training.
            #
            # This avoids model-serialization issues entirely.
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

            print(
                f"Epoch "
                f"{epoch + 1:4d}/{EPOCHS} | "
                f"phys={lambda_phys:.4f} | "
                f"train data="
                f"{train_metrics[1]:.3e} | "
                f"train FV="
                f"{train_metrics[2]:.3e} | "
                f"val data="
                f"{val_metrics[1]:.3e} | "
                f"val FV="
                f"{val_metrics[2]:.3e}"
            )

        # ---------------------------------------------------------------------
        # EARLY STOPPING
        # ---------------------------------------------------------------------

        if (
            patience_counter
            >= PATIENCE
        ):

            print(
                "\nEarly stopping:"
            )

            print(
                f"  Best epoch              : "
                f"{best_epoch}"
            )

            print(
                f"  Best validation MSE     : "
                f"{best_val:.6e}"
            )

            break

    runtime = (
        time.perf_counter()
        - start_time
    )

    # -------------------------------------------------------------------------
    # Save history
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

    # -------------------------------------------------------------------------
    # Save final serializable model
    # -------------------------------------------------------------------------

    model.save(
        FINAL_MODEL_FILE
    )

    # -------------------------------------------------------------------------
    # Restore best weights
    # -------------------------------------------------------------------------

    model.load_weights(
        BEST_WEIGHTS_FILE
    )

    # Save clean best model.
    model.save(
        BEST_MODEL_FILE
    )

    return (
        history,
        runtime,
        best_epoch,
        best_val,
    )


# =============================================================================
# TEST EVALUATION
# =============================================================================

def evaluate_model(
    model,
    X,
    Y,
):

    prediction_raw = model.predict(
        X,
        batch_size=BATCH_SIZE,
        verbose=0,
    )

    truth = (
        Y[
            :,
            :,
            0
        ]
    )

    prediction = (
        prediction_raw[
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

    profile_L1 = np.mean(
        np.abs(
            error
        ),
        axis=1,
    )

    return {
        "prediction":
            prediction,

        "truth":
            truth,

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
# TEST FV RESIDUAL
# =============================================================================

def evaluate_test_physics(
    model,
    dataset,
):

    X = tf.constant(
        dataset[
            "X_test"
        ].astype(
            np.float32
        )
    )

    tD_scale = tf.constant(
        float(
            dataset[
                "tD_scale"
            ][0]
        ),
        dtype=tf.float32,
    )

    (
        residual,
        relative_residual,
        _,
    ) = finite_volume_residual(
        model,
        X,
        tD_scale,
        training=False,
    )

    residual_np = (
        residual.numpy()
    )

    relative_np = (
        relative_residual.numpy()
    )

    return {
        "fv_rms":
            float(
                np.sqrt(
                    np.mean(
                        residual_np ** 2
                    )
                )
            ),

        "fv_relative_mae":
            float(
                np.mean(
                    np.abs(
                        relative_np
                    )
                )
            ),

        "fv_relative_rms":
            float(
                np.sqrt(
                    np.mean(
                        relative_np ** 2
                    )
                )
            ),
    }


# =============================================================================
# TEST MASS ERROR
# =============================================================================

def evaluate_test_mass(
    dataset,
    test_result,
):

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=float,
    )

    truth = (
        test_result[
            "truth"
        ]
    )

    prediction = (
        test_result[
            "prediction"
        ]
    )

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

    error = (
        pred_mass
        - true_mass
    )

    relative_error = (
        np.abs(
            error
        )
        /
        (
            np.abs(
                true_mass
            )
            + 1.0e-12
        )
    )

    return {
        "mass_mae":
            float(
                np.mean(
                    np.abs(
                        error
                    )
                )
            ),

        "mass_relative_mae":
            float(
                np.mean(
                    relative_error
                )
            ),

        "mass_relative_max":
            float(
                np.max(
                    relative_error
                )
            ),
    }


# =============================================================================
# TRAINING HISTORY PLOT
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
            "train_data"
        ],
        label="Train data",
    )

    ax.semilogy(
        epoch,
        history[
            "val_data"
        ],
        label="Validation data",
    )

    ax.semilogy(
        epoch,
        history[
            "train_phys"
        ],
        label="Train FV",
    )

    ax.semilogy(
        epoch,
        history[
            "val_phys"
        ],
        label="Validation FV",
    )

    ax.set_xlabel(
        "Epoch"
    )

    ax.set_ylabel(
        "Loss"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-4\n"
        "PI-RNN Training History"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B4_Training_History.png",
        dpi=300,
    )

    plt.close(
        fig
    )


# =============================================================================
# TEST PROFILE PLOT
# =============================================================================

def plot_test_profiles(
    xi,
    tD,
    truth,
    prediction,
):

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    positions = np.linspace(
        0,
        len(tD) - 1,
        5,
        dtype=int,
    )

    for position in positions:

        ax.plot(
            xi,
            truth[
                position
            ],
            linewidth=2.0,
            label=(
                "Truth "
                f"tD={tD[position]:.2f}"
            ),
        )

        ax.plot(
            xi,
            prediction[
                position
            ],
            linestyle="--",
            linewidth=1.5,
            label=(
                "PI-RNN "
                f"tD={tD[position]:.2f}"
            ),
        )

    ax.set_xlabel(
        r"TOF coordinate $\xi$"
    )

    ax.set_ylabel(
        "Saturation"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-4\n"
        "Held-Out Test Profiles"
    )

    ax.legend(
        fontsize=8,
        ncol=2,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B4_Test_Profiles.png",
        dpi=300,
    )

    plt.close(
        fig
    )


# =============================================================================
# TEST ERROR VS tD
# =============================================================================

def plot_error_vs_time(
    tD,
    profile_L1,
):

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        tD,
        profile_L1,
    )

    ax.set_xlabel(
        r"$t_D$"
    )

    ax.set_ylabel(
        "Profile L1 error"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-4\n"
        "Held-Out Test Error vs Dimensionless Time"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B4_Test_Error_vs_tD.png",
        dpi=300,
    )

    plt.close(
        fig
    )


# =============================================================================
# PREDICTION ERROR MAP
# =============================================================================

def plot_error_map(
    xi,
    tD,
    error,
):

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    im = ax.imshow(
        np.abs(
            error
        ),
        origin="lower",
        aspect="auto",
        extent=[
            xi[0],
            xi[-1],
            tD[0],
            tD[-1],
        ],
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
    )

    cbar.set_label(
        "|PI-RNN - SG7A saturation|"
    )

    ax.set_xlabel(
        r"TOF coordinate $\xi$"
    )

    ax.set_ylabel(
        r"Dimensionless time $t_D$"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-4\n"
        "Held-Out Prediction Error Map"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B4_Test_Error_Map.png",
        dpi=300,
    )

    plt.close(
        fig
    )


# =============================================================================
# SAVE TEST RESULTS
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
# SAVE SUMMARY
# =============================================================================

def save_summary(
    recovered,
    runtime,
    best_epoch,
    best_val,
    test_result,
    physics_result,
    mass_result,
):

    summary = {
        "milestone":
            "V15-SG7B-4",

        "description":
            (
                "Reference-case plain-LSTM "
                "full-physics PI-RNN training"
            ),

        "architecture": {
            "type":
                "plain stacked LSTM",

            "hidden_size":
                HIDDEN_SIZE,

            "lstm_layers":
                N_LSTM_LAYERS,

            "sequence_length":
                SEQUENCE_LENGTH,

            "input":
                "[xi, normalized tD]",

            "output":
                "S(xi,tD)",

            "fourier_features":
                False,

            "film":
                False,

            "front_coordinate":
                False,

            "serialization":
                (
                    "standard Keras Activation + "
                    "Rescaling; no anonymous Lambda"
                ),
        },

        "physics": {
            "Nc":
                NC,

            "Pe_c":
                PE_C,

            "lambda_bc":
                LAMBDA_BC,

            "porosity":
                POROSITY,

            "physics_loss":
                (
                    "conservative finite-volume "
                    "residual validated in SG7B-2"
                ),
        },

        "loss_weights": {
            "data":
                LAMBDA_DATA,

            "physics_max":
                LAMBDA_PHYS_MAX,

            "boundary":
                LAMBDA_BC_LOSS,

            "mass":
                LAMBDA_MASS,
        },

        "training": {
            "recovered_previous_run":
                bool(
                    recovered
                ),

            "requested_epochs":
                EPOCHS,

            "batch_size":
                BATCH_SIZE,

            "learning_rate":
                LEARNING_RATE,

            "best_epoch":
                int(
                    best_epoch
                ),

            "best_validation_data_mse":
                float(
                    best_val
                ),

            "runtime_seconds":
                (
                    None
                    if runtime is None
                    else float(
                        runtime
                    )
                ),
        },

        "held_out_test": {
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

            "minimum_predicted_saturation":
                test_result[
                    "min_prediction"
                ],

            "maximum_predicted_saturation":
                test_result[
                    "max_prediction"
                ],

            "FV_residual_RMS":
                physics_result[
                    "fv_rms"
                ],

            "FV_relative_MAE":
                physics_result[
                    "fv_relative_mae"
                ],

            "FV_relative_RMS":
                physics_result[
                    "fv_relative_rms"
                ],

            "mass_MAE":
                mass_result[
                    "mass_mae"
                ],

            "mass_relative_MAE":
                mass_result[
                    "mass_relative_mae"
                ],

            "mass_relative_max":
                mass_result[
                    "mass_relative_max"
                ],
        },

        "status":
            "TRAINED_NOT_YET_FROZEN",

        "freeze_decision":
            (
                "Deferred to V15-SG7B-5 "
                "detailed validation."
            ),

        "next_milestone":
            (
                "V15-SG7B-5 - detailed PI-RNN "
                "validation against frozen SG7A"
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
        "PAD-Stream Version 15-SG7B-4"
    )

    print(
        "Reference-Case Plain-LSTM PI-RNN Training"
    )

    print(
        "Corrected Serialization-Safe Version"
    )

    print(
        "=" * 78
    )

    print(
        f"\nTensorFlow version       : "
        f"{tf.__version__}"
    )

    print(
        "Execution device(s)     : "
        f"{tf.config.list_physical_devices()}"
    )

    # -------------------------------------------------------------------------
    # DATASET
    # -------------------------------------------------------------------------

    dataset = (
        load_dataset()
    )

    print(
        "\nDATASET"
    )

    print(
        f"  Training profiles       : "
        f"{len(dataset['X_train'])}"
    )

    print(
        f"  Validation profiles     : "
        f"{len(dataset['X_val'])}"
    )

    print(
        f"  Test profiles           : "
        f"{len(dataset['X_test'])}"
    )

    print(
        f"  Sequence nodes          : "
        f"{dataset['X_train'].shape[1]}"
    )

    print(
        f"  Input features          : "
        f"{dataset['X_train'].shape[2]}"
    )

    print(
        "\nNETWORK"
    )

    print(
        "  Architecture            : "
        "Plain stacked LSTM"
    )

    print(
        f"  Hidden units            : "
        f"{HIDDEN_SIZE}"
    )

    print(
        f"  LSTM layers             : "
        f"{N_LSTM_LAYERS}"
    )

    print(
        "  Fourier features        : False"
    )

    print(
        "  FiLM                    : False"
    )

    print(
        "  Front coordinate        : False"
    )

    print(
        "  Anonymous Lambda layer  : False"
    )

    print(
        "\nLOSS"
    )

    print(
        f"  Data weight             : "
        f"{LAMBDA_DATA}"
    )

    print(
        f"  FV physics max weight   : "
        f"{LAMBDA_PHYS_MAX}"
    )

    print(
        f"  Boundary weight         : "
        f"{LAMBDA_BC_LOSS}"
    )

    print(
        f"  Mass weight             : "
        f"{LAMBDA_MASS}"
    )

    # -------------------------------------------------------------------------
    # BUILD CORRECTED MODEL
    # -------------------------------------------------------------------------

    model = (
        build_model()
    )

    model.summary()

    # -------------------------------------------------------------------------
    # RECOVER OR TRAIN
    # -------------------------------------------------------------------------

    (
        recovered,
        history,
        best_epoch,
        best_val,
    ) = recover_trained_model(
        model
    )

    runtime = None

    if not recovered:

        print(
            "\n"
            + "=" * 78
        )

        print(
            "TRAINING SG7B-4"
        )

        print(
            "=" * 78
        )

        (
            history,
            runtime,
            best_epoch,
            best_val,
        ) = train_model(
            model,
            dataset,
        )

        print(
            "\nTRAINING COMPLETE"
        )

        print(
            f"  Runtime                 : "
            f"{runtime:.2f} s"
        )

        print(
            f"  Best epoch              : "
            f"{best_epoch}"
        )

        print(
            f"  Best validation MSE     : "
            f"{best_val:.6e}"
        )

    else:

        print(
            "\nTraining was NOT repeated."
        )

        print(
            "Recovered previous trained "
            "checkpoint successfully."
        )

    # -------------------------------------------------------------------------
    # SERIALIZATION TEST
    #
    # Save and reload the corrected model immediately.
    # If this fails, SG7B-4 must not proceed.
    # -------------------------------------------------------------------------

    print(
        "\nSERIALIZATION CHECK"
    )

    model.save(
        BEST_MODEL_FILE
    )

    reloaded_model = (
        tf.keras.models.load_model(
            BEST_MODEL_FILE
        )
    )

    print(
        "  Corrected model save/load : PASS"
    )

    # -------------------------------------------------------------------------
    # HELD-OUT TEST
    # -------------------------------------------------------------------------

    test_result = (
        evaluate_model(
            reloaded_model,
            dataset[
                "X_test"
            ],
            dataset[
                "Y_test"
            ],
        )
    )

    physics_result = (
        evaluate_test_physics(
            reloaded_model,
            dataset,
        )
    )

    mass_result = (
        evaluate_test_mass(
            dataset,
            test_result,
        )
    )

    print(
        "\nHELD-OUT TEST"
    )

    print(
        f"  L1                      : "
        f"{test_result['L1']:.6e}"
    )

    print(
        f"  L2                      : "
        f"{test_result['L2']:.6e}"
    )

    print(
        f"  Linf                    : "
        f"{test_result['Linf']:.6e}"
    )

    print(
        f"  Predicted saturation    : "
        f"{test_result['min_prediction']:.6f} "
        f"-> "
        f"{test_result['max_prediction']:.6f}"
    )

    print(
        "\nHELD-OUT PHYSICS"
    )

    print(
        f"  FV residual RMS         : "
        f"{physics_result['fv_rms']:.6e}"
    )

    print(
        f"  FV relative MAE         : "
        f"{physics_result['fv_relative_mae']:.6e}"
    )

    print(
        f"  FV relative RMS         : "
        f"{physics_result['fv_relative_rms']:.6e}"
    )

    print(
        "\nHELD-OUT MASS / STORAGE"
    )

    print(
        f"  Mass MAE                : "
        f"{mass_result['mass_mae']:.6e}"
    )

    print(
        f"  Relative mass MAE       : "
        f"{mass_result['mass_relative_mae']:.6e}"
    )

    print(
        f"  Maximum relative error  : "
        f"{mass_result['mass_relative_max']:.6e}"
    )

    # -------------------------------------------------------------------------
    # DIAGNOSTICS
    # -------------------------------------------------------------------------

    plot_training_history(
        history
    )

    plot_test_profiles(
        dataset[
            "xi"
        ],
        dataset[
            "tD_test"
        ],
        test_result[
            "truth"
        ],
        test_result[
            "prediction"
        ],
    )

    plot_error_vs_time(
        dataset[
            "tD_test"
        ],
        test_result[
            "profile_L1"
        ],
    )

    plot_error_map(
        dataset[
            "xi"
        ],
        dataset[
            "tD_test"
        ],
        test_result[
            "error"
        ],
    )

    # -------------------------------------------------------------------------
    # SAVE TEST DATA
    # -------------------------------------------------------------------------

    save_test_results(
        dataset,
        test_result,
    )

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------

    save_summary(
        recovered,
        runtime,
        best_epoch,
        best_val,
        test_result,
        physics_result,
        mass_result,
    )

    # -------------------------------------------------------------------------
    # FINAL OUTPUT
    # -------------------------------------------------------------------------

    print(
        "\nOUTPUTS"
    )

    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print(
        "\nCorrected model:"
    )

    print(
        "  V15SG7B4_Best_Model_Serializable.keras"
    )

    if (
        BEST_WEIGHTS_FILE.exists()
    ):

        print(
            "  V15SG7B4_Best.weights.h5"
        )

    print(
        "\nEvaluation data:"
    )

    print(
        "  V15SG7B4_Test_Results.npz"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B4_Training_History.png"
    )

    print(
        "  V15SG7B4_Test_Profiles.png"
    )

    print(
        "  V15SG7B4_Test_Error_vs_tD.png"
    )

    print(
        "  V15SG7B4_Test_Error_Map.png"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B4_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-4 COMPLETED"
    )

    print(
        "STATUS: TRAINED — NOT YET FROZEN"
    )

    print(
        "\nNext milestone:"
    )

    print(
        "V15-SG7B-5 — Detailed PI-RNN "
        "Validation Against Frozen SG7A"
    )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()