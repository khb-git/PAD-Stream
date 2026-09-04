from pathlib import Path
import json
import time

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7B-6
# Rebalanced Plain-LSTM PI-RNN Training
#
# PURPOSE
# -------
# Controlled retraining of the SG7B-4 reference PI-RNN.
#
# Architecture is unchanged:
#
#   [xi, normalized tD]
#          |
#        LSTM
#          |
#        LSTM
#          |
#   TimeDistributed Dense
#          |
#       sigmoid
#          |
#      Rescaling
#          |
#        S(xi,tD)
#
#
# CHANGES FROM SG7B-4
# -------------------
#
# 1. Higher FV physics weight:
#
#       0.05 -> 0.10
#
# 2. Slower physics warm-up.
#
# 3. Explicit injector-region loss.
#
# 4. Physics-aware checkpoint selection:
#
#       J_val =
#           L_data
#           +
#           alpha_phys * L_FV
#           +
#           alpha_mass * L_mass
#           +
#           alpha_inj * L_injector
#
#
# NO:
#   - Fourier features
#   - FiLM
#   - front coordinate
#   - shock-location input
#
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
    / "V15_SG7B6"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

BEST_WEIGHTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B6_Best.weights.h5"
)

BEST_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B6_Best_Model.keras"
)

FINAL_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B6_Final_Model.keras"
)

HISTORY_FILE = (
    OUTPUT_DIR
    / "V15SG7B6_Training_History.npz"
)

TEST_RESULTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B6_Test_Results.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B6_Summary.json"
)


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
# FROZEN PHYSICS
# =============================================================================

SWC = 0.20
SOR = 0.20

S_INITIAL = SWC
S_INJECTED = 1.0 - SOR

MOBILE_RANGE = (
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


# =============================================================================
# TRAINING CONFIGURATION
# =============================================================================

EPOCHS = 500
BATCH_SIZE = 32

LEARNING_RATE = 7.5e-4

PATIENCE = 90

GRADIENT_CLIP_NORM = 5.0


# -----------------------------------------------------------------------------
# Loss weights
# -----------------------------------------------------------------------------

LAMBDA_DATA = 1.0

LAMBDA_PHYS_MAX = 0.10

LAMBDA_BC = 0.50

LAMBDA_INJECTOR = 3.0

LAMBDA_MASS = 1.0


# -----------------------------------------------------------------------------
# Physics ramp
# -----------------------------------------------------------------------------

PHYS_WARMUP_START = 30

PHYS_WARMUP_END = 160


# -----------------------------------------------------------------------------
# Injector region
#
# First 5% of the 201-node TOF grid.
# -----------------------------------------------------------------------------

INJECTOR_FRACTION = 0.05

N_INJECTOR_NODES = max(
    3,
    int(
        INJECTOR_FRACTION
        * SEQUENCE_LENGTH
    ),
)


# -----------------------------------------------------------------------------
# Physics-aware checkpoint score
# -----------------------------------------------------------------------------

CHECKPOINT_ALPHA_PHYS = 0.10

CHECKPOINT_ALPHA_MASS = 1.00

CHECKPOINT_ALPHA_INJECTOR = 1.00


# =============================================================================
# DATA
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
        key:
            data[key]
        for key in required
    }


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
# MODEL
# =============================================================================

def build_model():

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
            scale=MOBILE_RANGE,
            offset=S_INITIAL,
            name="physical_saturation",
        )(sigmoid_output)
    )

    return tf.keras.Model(
        inputs=inputs,
        outputs=outputs,
        name=(
            "PAD_Stream_"
            "V15SG7B6_PIRNN"
        ),
    )


# =============================================================================
# INPUT AT ARBITRARY TIME
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
# CONSERVATIVE FV RESIDUAL
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
    # TIME DERIVATIVE
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

    dt = (
        t_plus
        - t_minus
        + EPS
    )

    X_minus = (
        build_input_for_time(
            X,
            t_minus
            / tD_scale,
        )
    )

    X_plus = (
        build_input_for_time(
            X,
            t_plus
            / tD_scale,
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

    S_t = (
        S_plus
        - S_minus
    ) / tf.reshape(
        dt,
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
    # ADVECTIVE FLUX
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
    # CAPILLARY FLUX
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
# LOSSES
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


def initial_boundary_loss(
    model,
    X,
    training,
):

    batch_size = (
        tf.shape(
            X
        )[0]
    )

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

    target = (
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

    target = tf.concat(
        [
            first_column,
            target[
                :,
                1:
            ],
        ],
        axis=1,
    )

    initial_loss = (
        tf.reduce_mean(
            tf.square(
                S_zero
                - target
            )
        )
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

    outlet_loss = (
        tf.reduce_mean(
            tf.square(
                outlet_gradient
            )
        )
    )

    return (
        initial_loss
        +
        outlet_loss
    )


def injector_region_loss(
    Y_true,
    Y_pred,
):
    """
    Explicitly emphasize the region where SG7B-5 found the
    largest errors.

    This is still data-grounded; it does not invent a new
    physical target.
    """

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

    truth = (
        Y_true[
            :,
            :,
            0
        ]
    )

    prediction = (
        Y_pred[
            :,
            :,
            0
        ]
    )

    true_mass = (
        trapezoid_integral(
            truth,
            dxi,
        )
    )

    pred_mass = (
        trapezoid_integral(
            prediction,
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
# PHYSICS WEIGHT
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
# CHECKPOINT SCORE
# =============================================================================

def checkpoint_score(
    L_data,
    L_phys,
    L_mass,
    L_injector,
):

    return (
        L_data
        +
        CHECKPOINT_ALPHA_PHYS
        * L_phys
        +
        CHECKPOINT_ALPHA_MASS
        * L_mass
        +
        CHECKPOINT_ALPHA_INJECTOR
        * L_injector
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
    lambda_phys,
    dxi,
):

    with tf.GradientTape() as tape:

        Y_pred = model(
            X,
            training=True,
        )

        L_data = (
            data_loss(
                Y,
                Y_pred,
            )
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

        L_phys = (
            tf.reduce_mean(
                tf.square(
                    relative
                )
            )
        )

        L_bc = (
            initial_boundary_loss(
                model,
                X,
                training=True,
            )
        )

        L_injector = (
            injector_region_loss(
                Y,
                Y_pred,
            )
        )

        L_mass = (
            mass_loss(
                Y,
                Y_pred,
                dxi,
            )
        )

        total = (
            LAMBDA_DATA
            * L_data
            +
            lambda_phys
            * L_phys
            +
            LAMBDA_BC
            * L_bc
            +
            LAMBDA_INJECTOR
            * L_injector
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
        L_injector,
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

    L_data = (
        data_loss(
            Y,
            Y_pred,
        )
    )

    (
        _,
        relative,
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
                relative
            )
        )
    )

    L_bc = (
        initial_boundary_loss(
            model,
            X,
            training=False,
        )
    )

    L_injector = (
        injector_region_loss(
            Y,
            Y_pred,
        )
    )

    L_mass = (
        mass_loss(
            Y,
            Y_pred,
            dxi,
        )
    )

    total = (
        LAMBDA_DATA
        * L_data
        +
        lambda_phys
        * L_phys
        +
        LAMBDA_BC
        * L_bc
        +
        LAMBDA_INJECTOR
        * L_injector
        +
        LAMBDA_MASS
        * L_mass
    )

    return (
        total,
        L_data,
        L_phys,
        L_bc,
        L_injector,
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
# TRAIN
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

    xi = (
        dataset[
            "xi"
        ]
    )

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
        "train_injector": [],
        "train_mass": [],

        "val_total": [],
        "val_data": [],
        "val_phys": [],
        "val_bc": [],
        "val_injector": [],
        "val_mass": [],
        "val_checkpoint_score": [],
    }

    best_score = np.inf
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

        lambda_phys_tf = tf.constant(
            lambda_phys,
            dtype=tf.float32,
        )

        # ---------------------------------------------------------------------
        # TRAIN
        # ---------------------------------------------------------------------

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
                tD_scale,
                lambda_phys_tf,
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
        # VALIDATION
        # ---------------------------------------------------------------------

        val_values = []

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

            val_values.append(
                [
                    float(
                        value.numpy()
                    )
                    for value in values
                ]
            )

        val_values = np.mean(
            val_values,
            axis=0,
        )

        validation_score = (
            checkpoint_score(
                L_data=(
                    val_values[1]
                ),
                L_phys=(
                    val_values[2]
                ),
                L_mass=(
                    val_values[5]
                ),
                L_injector=(
                    val_values[4]
                ),
            )
        )

        # ---------------------------------------------------------------------
        # STORE
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
            "train_injector",
            "train_mass",
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

        val_keys = [
            "val_total",
            "val_data",
            "val_phys",
            "val_bc",
            "val_injector",
            "val_mass",
        ]

        for (
            key,
            value
        ) in zip(
            val_keys,
            val_values,
        ):

            history[
                key
            ].append(
                float(
                    value
                )
            )

        history[
            "val_checkpoint_score"
        ].append(
            float(
                validation_score
            )
        )

        # ---------------------------------------------------------------------
        # CHECKPOINT
        # ---------------------------------------------------------------------

        if (
            validation_score
            <
            best_score
        ):

            best_score = float(
                validation_score
            )

            best_epoch = (
                epoch
                + 1
            )

            patience_counter = 0

            model.save_weights(
                BEST_WEIGHTS_FILE
            )

        else:

            patience_counter += 1

        # ---------------------------------------------------------------------
        # LOGGING
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
                f"data={val_values[1]:.3e} | "
                f"FV={val_values[2]:.3e} | "
                f"inj={val_values[4]:.3e} | "
                f"mass={val_values[5]:.3e} | "
                f"score={validation_score:.3e}"
            )

        # ---------------------------------------------------------------------
        # EARLY STOP
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
                f"  Best checkpoint score   : "
                f"{best_score:.6e}"
            )

            break

    runtime = (
        time.perf_counter()
        - start_time
    )

    # -------------------------------------------------------------------------
    # SAVE HISTORY
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
    # SAVE FINAL
    # -------------------------------------------------------------------------

    model.save(
        FINAL_MODEL_FILE
    )

    # -------------------------------------------------------------------------
    # RESTORE BEST
    # -------------------------------------------------------------------------

    model.load_weights(
        BEST_WEIGHTS_FILE
    )

    model.save(
        BEST_MODEL_FILE
    )

    return (
        history,
        runtime,
        best_epoch,
        best_score,
    )


# =============================================================================
# TEST METRICS
# =============================================================================

def evaluate_model(
    model,
    dataset,
):

    X = (
        dataset[
            "X_test"
        ].astype(
            np.float32
        )
    )

    Y = (
        dataset[
            "Y_test"
        ]
    )

    prediction = (
        model.predict(
            X,
            batch_size=BATCH_SIZE,
            verbose=0,
        )[
            :,
            :,
            0
        ]
    )

    truth = (
        Y[
            :,
            :,
            0
        ]
    )

    error = (
        prediction
        - truth
    )

    abs_error = (
        np.abs(
            error
        )
    )

    L1 = float(
        np.mean(
            abs_error
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
            abs_error
        )
    )

    profile_L1 = (
        np.mean(
            abs_error,
            axis=1,
        )
    )

    # -------------------------------------------------------------------------
    # Injector-region error
    # -------------------------------------------------------------------------

    injector_error = (
        error[
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
    # FV physics
    # -------------------------------------------------------------------------

    X_tf = tf.constant(
        X,
        dtype=tf.float32,
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
        residual_tf,
        relative_tf,
        _,
    ) = finite_volume_residual(
        model,
        X_tf,
        tD_scale,
        training=False,
    )

    residual = (
        residual_tf.numpy()
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

    fv_RMS = float(
        np.sqrt(
            np.mean(
                residual ** 2
            )
        )
    )

    # -------------------------------------------------------------------------
    # Mass
    # -------------------------------------------------------------------------

    xi = (
        dataset[
            "xi"
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

    mass_error = (
        pred_mass
        - true_mass
    )

    mass_relative = (
        np.abs(
            mass_error
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

        "injector_L1":
            injector_L1,

        "fv_RMS":
            fv_RMS,

        "fv_relative_MAE":
            fv_relative_MAE,

        "fv_relative_RMS":
            fv_relative_RMS,

        "mass_relative_MAE":
            mass_relative_MAE,

        "mass_relative_max":
            mass_relative_max,

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
# VALIDATION GATES
# =============================================================================

def validate_result(
    result,
):

    checks = [
        (
            "All predictions finite",
            np.all(
                np.isfinite(
                    result[
                        "prediction"
                    ]
                )
            ),
        ),

        (
            "Prediction lower bound respected",
            result[
                "min_prediction"
            ]
            >= S_INITIAL
            - 1.0e-7,
        ),

        (
            "Prediction upper bound respected",
            result[
                "max_prediction"
            ]
            <= S_INJECTED
            + 1.0e-7,
        ),

        (
            "Held-out L1 < 0.02",
            result[
                "L1"
            ] < 0.02,
        ),

        (
            "Held-out FV relative MAE < 0.10",
            result[
                "fv_relative_MAE"
            ] < 0.10,
        ),

        (
            "Held-out mass relative MAE < 0.03",
            result[
                "mass_relative_MAE"
            ] < 0.03,
        ),
    ]

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-6 VALIDATION"
    )

    print(
        "=" * 78
    )

    all_passed = True

    for (
        description,
        passed
    ) in checks:

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"[{status:4s}] "
            f"{description}"
        )

        if not passed:

            all_passed = False

    print(
        "=" * 78
    )

    return (
        all_passed,
        checks,
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
            "val_data"
        ],
        label="Validation data",
    )

    ax.semilogy(
        epoch,
        history[
            "val_phys"
        ],
        label="Validation FV",
    )

    ax.semilogy(
        epoch,
        history[
            "val_injector"
        ],
        label="Validation injector",
    )

    ax.semilogy(
        epoch,
        history[
            "val_mass"
        ],
        label="Validation mass",
    )

    ax.semilogy(
        epoch,
        history[
            "val_checkpoint_score"
        ],
        label="Checkpoint score",
    )

    ax.set_xlabel(
        "Epoch"
    )

    ax.set_ylabel(
        "Loss / score"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6\n"
        "Rebalanced Training History"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6_Training_History.png",
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
        5,
        dtype=int,
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    for position in positions:

        ax.plot(
            xi,
            result[
                "truth"
            ][
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
            result[
                "prediction"
            ][
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
        "PAD-Stream V15-SG7B-6\n"
        "Held-Out Test Profiles"
    )

    ax.legend(
        fontsize=8,
        ncol=2,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6_Test_Profiles.png",
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

    ax.set_xlabel(
        r"$t_D$"
    )

    ax.set_ylabel(
        "Profile L1 error"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6\n"
        "Held-Out Error vs Dimensionless Time"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6_Error_vs_tD.png",
        dpi=300,
    )

    plt.close(
        fig
    )


# =============================================================================
# SAVE
# =============================================================================

def save_results(
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


def save_summary(
    runtime,
    best_epoch,
    best_score,
    result,
    validation_passed,
):

    summary = {
        "milestone":
            "V15-SG7B-6",

        "description":
            (
                "Rebalanced plain-LSTM "
                "full-physics PI-RNN training"
            ),

        "architecture": {
            "type":
                "plain stacked LSTM",

            "hidden_size":
                HIDDEN_SIZE,

            "layers":
                N_LSTM_LAYERS,

            "fourier_features":
                False,

            "film":
                False,

            "front_coordinate":
                False,
        },

        "changes_from_SG7B4": {
            "physics_weight_max":
                LAMBDA_PHYS_MAX,

            "physics_warmup_start":
                PHYS_WARMUP_START,

            "physics_warmup_end":
                PHYS_WARMUP_END,

            "injector_region_nodes":
                N_INJECTOR_NODES,

            "injector_loss_weight":
                LAMBDA_INJECTOR,

            "mass_loss_weight":
                LAMBDA_MASS,

            "checkpoint_selection":
                (
                    "data + weighted FV + "
                    "mass + injector loss"
                ),
        },

        "training": {
            "runtime_seconds":
                float(
                    runtime
                ),

            "best_epoch":
                int(
                    best_epoch
                ),

            "best_checkpoint_score":
                float(
                    best_score
                ),
        },

        "test": {
            "L1":
                result[
                    "L1"
                ],

            "L2":
                result[
                    "L2"
                ],

            "Linf":
                result[
                    "Linf"
                ],

            "injector_L1":
                result[
                    "injector_L1"
                ],

            "fv_relative_MAE":
                result[
                    "fv_relative_MAE"
                ],

            "fv_relative_RMS":
                result[
                    "fv_relative_RMS"
                ],

            "mass_relative_MAE":
                result[
                    "mass_relative_MAE"
                ],

            "mass_relative_max":
                result[
                    "mass_relative_max"
                ],

            "minimum_prediction":
                result[
                    "min_prediction"
                ],

            "maximum_prediction":
                result[
                    "max_prediction"
                ],
        },

        "validation_passed":
            bool(
                validation_passed
            ),

        "status":
            (
                "PASS_CANDIDATE"
                if validation_passed
                else "REQUIRES_FURTHER_TUNING"
            ),

        "next_milestone":
            (
                "V15-SG7B-7 - final SG7B "
                "PI-RNN validation/freeze decision"
                if validation_passed
                else
                "V15-SG7B-6B - targeted "
                "training refinement"
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
        "PAD-Stream Version 15-SG7B-6"
    )

    print(
        "Rebalanced Plain-LSTM PI-RNN Training"
    )

    print(
        "=" * 78
    )

    print(
        f"\nTensorFlow version       : "
        f"{tf.__version__}"
    )

    print(
        "\nTRAINING CHANGES"
    )

    print(
        f"  FV physics max weight   : "
        f"{LAMBDA_PHYS_MAX}"
    )

    print(
        f"  Physics ramp            : "
        f"epoch {PHYS_WARMUP_START} "
        f"-> {PHYS_WARMUP_END}"
    )

    print(
        f"  Injector nodes          : "
        f"{N_INJECTOR_NODES}"
    )

    print(
        f"  Injector loss weight    : "
        f"{LAMBDA_INJECTOR}"
    )

    print(
        f"  Mass weight             : "
        f"{LAMBDA_MASS}"
    )

    print(
        "  Checkpoint              : "
        "physics-aware composite score"
    )

    dataset = (
        load_dataset()
    )

    print(
        "\nDATASET"
    )

    print(
        f"  Train                   : "
        f"{len(dataset['X_train'])}"
    )

    print(
        f"  Validation              : "
        f"{len(dataset['X_val'])}"
    )

    print(
        f"  Test                    : "
        f"{len(dataset['X_test'])}"
    )

    model = (
        build_model()
    )

    model.summary()

    (
        history,
        runtime,
        best_epoch,
        best_score,
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
        f"  Best checkpoint score   : "
        f"{best_score:.6e}"
    )

    # -------------------------------------------------------------------------
    # Reload serialization-safe best model
    # -------------------------------------------------------------------------

    best_model = (
        tf.keras.models.load_model(
            BEST_MODEL_FILE
        )
    )

    result = (
        evaluate_model(
            best_model,
            dataset,
        )
    )

    print(
        "\nHELD-OUT TEST"
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
        f"  Injector-region L1      : "
        f"{result['injector_L1']:.6e}"
    )

    print(
        f"  Saturation range        : "
        f"{result['min_prediction']:.6f} "
        f"-> "
        f"{result['max_prediction']:.6f}"
    )

    print(
        "\nHELD-OUT PHYSICS"
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
        "\nHELD-OUT MASS"
    )

    print(
        f"  Relative mass MAE       : "
        f"{result['mass_relative_MAE']:.6e}"
    )

    print(
        f"  Maximum relative mass   : "
        f"{result['mass_relative_max']:.6e}"
    )

    validation_passed, _ = (
        validate_result(
            result
        )
    )

    # -------------------------------------------------------------------------
    # PLOTS
    # -------------------------------------------------------------------------

    plot_training_history(
        history
    )

    plot_test_profiles(
        dataset,
        result,
    )

    plot_error_vs_time(
        dataset,
        result,
    )

    # -------------------------------------------------------------------------
    # SAVE
    # -------------------------------------------------------------------------

    save_results(
        dataset,
        result,
    )

    save_summary(
        runtime,
        best_epoch,
        best_score,
        result,
        validation_passed,
    )

    # -------------------------------------------------------------------------
    # OUTPUT
    # -------------------------------------------------------------------------

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
        "  V15SG7B6_Best_Model.keras"
    )

    print(
        "  V15SG7B6_Final_Model.keras"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B6_Training_History.png"
    )

    print(
        "  V15SG7B6_Test_Profiles.png"
    )

    print(
        "  V15SG7B6_Error_vs_tD.png"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B6_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-6 COMPLETED"
    )

    if validation_passed:

        print(
            "STATUS: PASS CANDIDATE"
        )

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7B-7 — Final PI-RNN "
            "Validation / Freeze Decision"
        )

    else:

        print(
            "STATUS: FURTHER TUNING REQUIRED"
        )

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7B-6B — Targeted "
            "PI-RNN Training Refinement"
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()