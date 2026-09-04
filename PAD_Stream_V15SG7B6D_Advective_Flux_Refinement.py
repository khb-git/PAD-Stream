from pathlib import Path
import json
import time

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7B-6D
# Targeted Conservative Advective-Flux Refinement
#
# PURPOSE
# -------
# Fine-tune the SG7B-6B PI-RNN specifically against the dominant residual
# mechanism identified in SG7B-6C:
#
#       ADVECTIVE FLUX / ADVECTIVE DIVERGENCE MISMATCH
#
#
# SOURCE MODEL
# ------------
#       V15SG7B6B_Best_Model.keras
#
#
# CANONICAL PHYSICS CONTRACT
# --------------------------
# Established in V15-SG7B-6C-R:
#
#       SG7A master_saturation is the canonical classical truth source.
#
#       For this positive-velocity regime,
#
#           u_D(xi) = exp(Nc xi) > 0
#
#       the Godunov and positive-upwind face fluxes are identical:
#
#           F_(i+1/2) = u_(i+1/2) f(S_i)
#
#
# REFINEMENT LOSSES
# -----------------
#
#   L =
#       lambda_data      * L_data
#     + lambda_FV        * L_FV
#     + lambda_face      * L_face_flux
#     + lambda_div       * L_adv_div
#     + lambda_mass      * L_mass
#     + lambda_injector  * L_injector
#     + lambda_late      * L_late
#
#
# IMPORTANT
# ---------
# SG7A face-flux and divergence targets are generated directly from:
#
#       master_saturation[index]
#
# NOT from the float32 SG7B-3 Y arrays.
#
#
# NO:
#   - new architecture
#   - Fourier features
#   - FiLM
#   - front-coordinate input
#   - new classical solver
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


SG7A_FILE = (
    ROOT
    / "output"
    / "V15_SG7A"
    / "FULL_PHYSICS_STREAMLINE_SATURATION.npz"
)


SOURCE_MODEL_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6B"
    / "V15SG7B6B_Best_Model.keras"
)


OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B6D"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


BEST_WEIGHTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B6D_Best.weights.h5"
)


BEST_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B6D_Best_Model.keras"
)


FINAL_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B6D_Final_Model.keras"
)


HISTORY_FILE = (
    OUTPUT_DIR
    / "V15SG7B6D_Training_History.npz"
)


TEST_RESULTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B6D_Test_Results.npz"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B6D_Summary.json"
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
# CANONICAL SG7B-6C-R TRUTH METRIC
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
# DIMENSIONS
# =============================================================================

SEQUENCE_LENGTH = 201

N_FACES = (
    SEQUENCE_LENGTH
    + 1
)

BATCH_SIZE = 32

N_INJECTOR_NODES = 10


# =============================================================================
# FINE-TUNING CONFIGURATION
# =============================================================================

EPOCHS = 220

PATIENCE = 55

GRADIENT_CLIP_NORM = 5.0


# -----------------------------------------------------------------------------
# Learning-rate schedule
# -----------------------------------------------------------------------------

LR_STAGE_1 = 5.0e-5
LR_STAGE_2 = 2.5e-5
LR_STAGE_3 = 1.0e-5

LR_STAGE_2_EPOCH = 80
LR_STAGE_3_EPOCH = 150


# =============================================================================
# TRAINING LOSS WEIGHTS
# =============================================================================

# Preserve already excellent saturation fit.
LAMBDA_DATA = 1.00

# Continue conservative residual enforcement.
LAMBDA_FV = 0.20

# New SG7B-6D targeted terms.
LAMBDA_FACE_FLUX = 1.00
LAMBDA_ADV_DIV = 1.50

# Existing guardrail terms.
LAMBDA_MASS = 0.40
LAMBDA_INJECTOR = 0.30
LAMBDA_LATE = 0.30


# =============================================================================
# VALIDATION / CHECKPOINT WEIGHTS
# =============================================================================

SCORE_WEIGHT_DATA = 1.0
SCORE_WEIGHT_FV = 2.0
SCORE_WEIGHT_FACE = 1.0
SCORE_WEIGHT_DIV = 1.5
SCORE_WEIGHT_MASS = 0.5


# =============================================================================
# FINAL GUARDRAILS
# =============================================================================

MAX_TEST_L1 = 0.020

MAX_TEST_L2 = 0.030

MAX_MASS_RELATIVE_MAE = 0.030

MAX_INJECTOR_L1 = 0.015

MAX_LATE_L1 = 0.025


# =============================================================================
# LOAD DATA
# =============================================================================

def load_dataset():

    if not DATASET_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-3 dataset:\n"
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
        "index_train",
        "index_val",
        "index_test",
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


def load_sg7a():

    if not SG7A_FILE.exists():

        raise FileNotFoundError(
            "Missing frozen SG7A master solution:\n"
            f"{SG7A_FILE}"
        )

    data = np.load(
        SG7A_FILE
    )

    required = [
        "xi",
        "master_tD",
        "master_saturation",
    ]

    for key in required:

        if key not in data:

            raise KeyError(
                f"SG7A field missing: {key}"
            )

    return {
        key: data[key]
        for key in required
    }


# =============================================================================
# NUMPY PHYSICS FOR CANONICAL SG7A TARGET GENERATION
# =============================================================================

def effective_saturation_np(S):

    span = (
        1.0
        - SWC
        - SOR
    )

    return np.clip(
        (
            np.asarray(
                S,
                dtype=np.float64,
            )
            - SWC
        )
        / span,
        0.0,
        1.0,
    )


def fractional_flow_np(S):

    Se = effective_saturation_np(
        S
    )

    kr_disp = (
        KR_DISP_MAX
        * Se ** N_DISP
    )

    kr_res = (
        KR_RES_MAX
        * (
            1.0
            - Se
        ) ** N_RES
    )

    mobility_disp = (
        kr_disp
        / MU_DISP
    )

    mobility_res = (
        kr_res
        / MU_RES
    )

    return (
        mobility_disp
        /
        (
            mobility_disp
            + mobility_res
            + 1.0e-14
        )
    )


# =============================================================================
# CANONICAL ADVECTIVE TARGET
# =============================================================================

def canonical_advective_flux_np(
    S,
    xi,
):
    """
    Canonical positive-velocity Godunov/upwind flux.

    SG7B-6C-R established:

        generic Godunov search == positive upwind

    for the current u_D > 0 regime.
    """

    S = np.asarray(
        S,
        dtype=np.float64,
    )

    xi = np.asarray(
        xi,
        dtype=np.float64,
    )

    n = len(S)

    dxi = float(
        xi[1]
        - xi[0]
    )

    face_xi = np.linspace(
        0.0,
        1.0,
        n + 1,
        dtype=np.float64,
    )

    u_face = np.exp(
        NC
        * face_xi
    )

    face_flux = np.zeros(
        n + 1,
        dtype=np.float64,
    )

    # -------------------------------------------------------------------------
    # Injector face
    # -------------------------------------------------------------------------

    face_flux[0] = (
        u_face[0]
        * float(
            fractional_flow_np(
                np.array(
                    [S_INJECTED],
                    dtype=np.float64,
                )
            )[0]
        )
    )

    # -------------------------------------------------------------------------
    # Internal faces
    # -------------------------------------------------------------------------

    fw_cell = fractional_flow_np(
        S
    )

    face_flux[
        1:n
    ] = (
        u_face[
            1:n
        ]
        * fw_cell[
            :-1
        ]
    )

    # -------------------------------------------------------------------------
    # Outlet face
    # -------------------------------------------------------------------------

    face_flux[n] = (
        u_face[n]
        * fw_cell[-1]
    )

    divergence = (
        face_flux[1:]
        -
        face_flux[:-1]
    ) / dxi

    return (
        face_flux,
        divergence,
    )


# =============================================================================
# BUILD CANONICAL TARGET DATABASE
# =============================================================================

def build_advective_targets(
    dataset,
    sg7a,
):

    xi = np.asarray(
        sg7a[
            "xi"
        ],
        dtype=np.float64,
    )

    master_S = np.asarray(
        sg7a[
            "master_saturation"
        ],
        dtype=np.float64,
    )

    targets = {}

    for split in [
        "train",
        "val",
        "test",
    ]:

        indices = np.asarray(
            dataset[
                f"index_{split}"
            ],
            dtype=int,
        )

        face_array = np.zeros(
            (
                len(indices),
                N_FACES,
            ),
            dtype=np.float32,
        )

        div_array = np.zeros(
            (
                len(indices),
                SEQUENCE_LENGTH,
            ),
            dtype=np.float32,
        )

        for p, index in enumerate(
            indices
        ):

            face_flux, divergence = (
                canonical_advective_flux_np(
                    master_S[
                        index
                    ],
                    xi,
                )
            )

            face_array[p] = (
                face_flux.astype(
                    np.float32
                )
            )

            div_array[p] = (
                divergence.astype(
                    np.float32
                )
            )

        targets[
            f"face_{split}"
        ] = face_array

        targets[
            f"div_{split}"
        ] = div_array

    return targets


# =============================================================================
# TENSORFLOW PHYSICS
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
            1.0
            - Se,
            N_RES,
        )
    )

    mobility_disp = (
        kr_disp
        / MU_DISP
    )

    mobility_res = (
        kr_res
        / MU_RES
    )

    return (
        mobility_disp
        /
        (
            mobility_disp
            + mobility_res
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
            1.0
            - Se,
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

    mobility_disp_mid = (
        kr_disp_mid
        / MU_DISP
    )

    mobility_res_mid = (
        kr_res_mid
        / MU_RES
    )

    fw_mid = (
        mobility_disp_mid
        /
        (
            mobility_disp_mid
            + mobility_res_mid
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
# MODEL INPUT AT ARBITRARY TIME
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
# DIFFERENTIABLE ADVECTIVE FLUX
# =============================================================================

def predicted_advective_flux(
    S,
):
    """
    S shape:
        (batch, 201)

    Returns:
        face_flux   : (batch, 202)
        divergence  : (batch, 201)
    """

    batch_size = tf.shape(
        S
    )[0]

    face_xi = tf.linspace(
        0.0,
        1.0,
        N_FACES,
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

    # Injector face
    left_face = (
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

    # Internal positive-upwind faces
    internal_faces = (
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

    # Outlet
    outlet_face = (
        fw[
            :,
            -1:
        ]
        *
        u_face[-1]
    )

    face_flux = tf.concat(
        [
            left_face,
            internal_faces,
            outlet_face,
        ],
        axis=1,
    )

    dxi = (
        1.0
        /
        (
            SEQUENCE_LENGTH
            - 1
        )
    )

    divergence = (
        face_flux[
            :,
            1:
        ]
        -
        face_flux[
            :,
            :-1
        ]
    ) / dxi

    return (
        face_flux,
        divergence,
    )


# =============================================================================
# FULL CONSERVATIVE FV RESIDUAL
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

    dt_effective = (
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
        dt_effective,
        (
            -1,
            1,
        ),
    )

    # -------------------------------------------------------------------------
    # Advective
    # -------------------------------------------------------------------------

    _, div_adv = (
        predicted_advective_flux(
            S
        )
    )

    # -------------------------------------------------------------------------
    # Capillary
    # -------------------------------------------------------------------------

    batch_size = tf.shape(
        S
    )[0]

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
        /
        (
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
        div_adv,
    )


# =============================================================================
# AUXILIARY LOSSES
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


def injector_loss(
    Y_true,
    Y_pred,
):

    return tf.reduce_mean(
        tf.square(
            Y_pred[
                :,
                :N_INJECTOR_NODES,
                0
            ]
            -
            Y_true[
                :,
                :N_INJECTOR_NODES,
                0
            ]
        )
    )


def late_time_loss(
    X,
    Y_true,
    Y_pred,
):

    time_normalized = (
        X[
            :,
            0,
            1
        ]
    )

    mask = tf.cast(
        time_normalized
        >= (2.0 / 3.0),
        dtype=tf.float32,
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

    return (
        tf.reduce_sum(
            mask
            * profile_mse
        )
        /
        (
            tf.reduce_sum(
                mask
            )
            + EPS
        )
    )


# =============================================================================
# ADVECTIVE TARGET LOSSES
# =============================================================================

def normalized_face_flux_loss(
    predicted,
    target,
):

    scale = (
        tf.reduce_mean(
            tf.square(
                target
            )
        )
        +
        1.0e-8
    )

    return (
        tf.reduce_mean(
            tf.square(
                predicted
                - target
            )
        )
        / scale
    )


def normalized_divergence_loss(
    predicted,
    target,
):

    scale = (
        tf.reduce_mean(
            tf.square(
                target
            )
        )
        +
        1.0e-8
    )

    return (
        tf.reduce_mean(
            tf.square(
                predicted
                - target
            )
        )
        / scale
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
    target_face,
    target_div,
    tD_scale,
    dxi,
):

    with tf.GradientTape() as tape:

        Y_pred = model(
            X,
            training=True,
        )

        S_pred = (
            Y_pred[
                :,
                :,
                0
            ]
        )

        # ---------------------------------------------------------------------
        # Data
        # ---------------------------------------------------------------------

        L_data = data_loss(
            Y,
            Y_pred,
        )

        # ---------------------------------------------------------------------
        # Full FV
        # ---------------------------------------------------------------------

        (
            _,
            relative,
            _,
            _,
        ) = finite_volume_residual(
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

        # ---------------------------------------------------------------------
        # Direct advective flux supervision
        # ---------------------------------------------------------------------

        predicted_face, predicted_div = (
            predicted_advective_flux(
                S_pred
            )
        )

        L_face = (
            normalized_face_flux_loss(
                predicted_face,
                target_face,
            )
        )

        L_div = (
            normalized_divergence_loss(
                predicted_div,
                target_div,
            )
        )

        # ---------------------------------------------------------------------
        # Guardrails
        # ---------------------------------------------------------------------

        L_mass = mass_loss(
            Y,
            Y_pred,
            dxi,
        )

        L_injector = injector_loss(
            Y,
            Y_pred,
        )

        L_late = late_time_loss(
            X,
            Y,
            Y_pred,
        )

        # ---------------------------------------------------------------------
        # Total
        # ---------------------------------------------------------------------

        total = (
            LAMBDA_DATA
            * L_data

            +
            LAMBDA_FV
            * L_fv

            +
            LAMBDA_FACE_FLUX
            * L_face

            +
            LAMBDA_ADV_DIV
            * L_div

            +
            LAMBDA_MASS
            * L_mass

            +
            LAMBDA_INJECTOR
            * L_injector

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
        L_fv,
        L_face,
        L_div,
        L_mass,
        L_injector,
        L_late,
    )


# =============================================================================
# DATASET PIPELINE
# =============================================================================

def make_tf_dataset(
    X,
    Y,
    face_target,
    div_target,
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
                face_target.astype(
                    np.float32
                ),
                div_target.astype(
                    np.float32
                ),
            )
        )
    )

    if training:

        ds = ds.shuffle(
            buffer_size=len(X),
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
# FULL-SPLIT EVALUATION
# =============================================================================

def evaluate_split(
    model,
    X,
    Y,
    target_face,
    target_div,
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

    abs_error = np.abs(
        error
    )

    # -------------------------------------------------------------------------
    # Saturation
    # -------------------------------------------------------------------------

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

    profile_L1 = np.mean(
        abs_error,
        axis=1,
    )

    # -------------------------------------------------------------------------
    # PI-RNN FV
    # -------------------------------------------------------------------------

    X_tf = tf.constant(
        X_np,
        dtype=tf.float32,
    )

    scale_tf = tf.constant(
        tD_scale,
        dtype=tf.float32,
    )

    (
        _,
        relative_tf,
        _,
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
    # Advective target agreement
    # -------------------------------------------------------------------------

    prediction_tf = tf.constant(
        prediction,
        dtype=tf.float32,
    )

    predicted_face_tf, predicted_div_tf = (
        predicted_advective_flux(
            prediction_tf
        )
    )

    predicted_face = (
        predicted_face_tf.numpy()
    )

    predicted_div = (
        predicted_div_tf.numpy()
    )

    face_error = (
        predicted_face
        - target_face
    )

    div_error = (
        predicted_div
        - target_div
    )

    face_MAE = float(
        np.mean(
            np.abs(
                face_error
            )
        )
    )

    div_MAE = float(
        np.mean(
            np.abs(
                div_error
            )
        )
    )

    face_relative_MAE = float(
        face_MAE
        /
        (
            np.mean(
                np.abs(
                    target_face
                )
            )
            + 1.0e-12
        )
    )

    div_relative_MAE = float(
        div_MAE
        /
        (
            np.mean(
                np.abs(
                    target_div
                )
            )
            + 1.0e-12
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
    # Injector
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
        >= (
            2.0
            / 3.0
        )
    )

    if np.any(
        late_mask
    ):

        late_L1 = float(
            np.mean(
                np.abs(
                    error[
                        late_mask
                    ]
                )
            )
        )

    else:

        late_L1 = 0.0

    return {
        "truth":
            truth,

        "prediction":
            prediction,

        "error":
            error,

        "profile_L1":
            profile_L1,

        "relative_FV":
            relative,

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

        "face_MAE":
            face_MAE,

        "face_relative_MAE":
            face_relative_MAE,

        "div_MAE":
            div_MAE,

        "div_relative_MAE":
            div_relative_MAE,

        "mass_relative_MAE":
            mass_relative_MAE,

        "mass_relative_max":
            mass_relative_max,

        "injector_L1":
            injector_L1,

        "late_L1":
            late_L1,

        "minimum_prediction":
            float(
                np.min(
                    prediction
                )
            ),

        "maximum_prediction":
            float(
                np.max(
                    prediction
                )
            ),
    }


# =============================================================================
# CHECKPOINT SCORE
# =============================================================================

def checkpoint_score(
    metrics,
    baseline_adv,
):
    """
    Normalize terms against physically meaningful scales.

    For face/divergence error, normalize against the SG7B-6B baseline so
    the score directly rewards improvement relative to the incoming model.
    """

    data_term = (
        metrics[
            "L1"
        ]
        / MAX_TEST_L1
    )

    fv_term = (
        metrics[
            "fv_relative_MAE"
        ]
        /
        TARGET_FV_RELATIVE_MAE
    )

    face_term = (
        metrics[
            "face_relative_MAE"
        ]
        /
        max(
            baseline_adv[
                "face_relative_MAE"
            ],
            1.0e-8,
        )
    )

    div_term = (
        metrics[
            "div_relative_MAE"
        ]
        /
        max(
            baseline_adv[
                "div_relative_MAE"
            ],
            1.0e-8,
        )
    )

    mass_term = (
        metrics[
            "mass_relative_MAE"
        ]
        /
        MAX_MASS_RELATIVE_MAE
    )

    return float(
        SCORE_WEIGHT_DATA
        * data_term

        +
        SCORE_WEIGHT_FV
        * fv_term

        +
        SCORE_WEIGHT_FACE
        * face_term

        +
        SCORE_WEIGHT_DIV
        * div_term

        +
        SCORE_WEIGHT_MASS
        * mass_term
    )


# =============================================================================
# LEARNING RATE
# =============================================================================

def learning_rate_for_epoch(
    epoch,
):

    if (
        epoch
        < LR_STAGE_2_EPOCH
    ):

        return (
            LR_STAGE_1
        )

    if (
        epoch
        < LR_STAGE_3_EPOCH
    ):

        return (
            LR_STAGE_2
        )

    return (
        LR_STAGE_3
    )


# =============================================================================
# FINE-TUNE
# =============================================================================

def fine_tune(
    model,
    dataset,
    targets,
):

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

    tD_scale = float(
        dataset[
            "tD_scale"
        ][0]
    )

    tD_scale_tf = tf.constant(
        tD_scale,
        dtype=tf.float32,
    )

    train_ds = (
        make_tf_dataset(
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
            True,
        )
    )

    optimizer = (
        tf.keras.optimizers.Adam(
            learning_rate=(
                LR_STAGE_1
            )
        )
    )

    # -------------------------------------------------------------------------
    # Incoming SG7B-6B baseline
    # -------------------------------------------------------------------------

    baseline_val = evaluate_split(
        model,
        dataset[
            "X_val"
        ],
        dataset[
            "Y_val"
        ],
        targets[
            "face_val"
        ],
        targets[
            "div_val"
        ],
        xi,
        tD_scale,
    )

    baseline_test = evaluate_split(
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

    print(
        "\n"
        + "=" * 78
    )

    print(
        "PRE-REFINEMENT SG7B-6B BASELINE"
    )

    print(
        "=" * 78
    )

    print(
        f"Validation L1             : "
        f"{baseline_val['L1']:.6e}"
    )

    print(
        f"Validation FV MAE         : "
        f"{baseline_val['fv_relative_MAE']:.6e}"
    )

    print(
        f"Validation face rel MAE   : "
        f"{baseline_val['face_relative_MAE']:.6e}"
    )

    print(
        f"Validation div rel MAE    : "
        f"{baseline_val['div_relative_MAE']:.6e}"
    )

    print()

    print(
        f"Test L1                   : "
        f"{baseline_test['L1']:.6e}"
    )

    print(
        f"Test FV MAE               : "
        f"{baseline_test['fv_relative_MAE']:.6e}"
    )

    print(
        f"Test FV / SG7A ratio      : "
        f"{baseline_test['fv_relative_MAE'] / SG7A_TRUTH_FV_RELATIVE_MAE:.3f}"
    )

    print(
        f"Test face rel MAE         : "
        f"{baseline_test['face_relative_MAE']:.6e}"
    )

    print(
        f"Test div rel MAE          : "
        f"{baseline_test['div_relative_MAE']:.6e}"
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
        "train_FV": [],
        "train_face": [],
        "train_div": [],
        "train_mass": [],
        "train_injector": [],
        "train_late": [],

        "val_L1": [],
        "val_L2": [],
        "val_FV_MAE": [],
        "val_face_relative_MAE": [],
        "val_div_relative_MAE": [],
        "val_mass_MAE": [],
        "val_injector_L1": [],
        "val_late_L1": [],
        "val_score": [],
    }

    best_score = np.inf

    best_epoch = -1

    patience_counter = 0

    start_time = (
        time.perf_counter()
    )

    # -------------------------------------------------------------------------
    # TRAINING LOOP
    # -------------------------------------------------------------------------

    for epoch in range(
        EPOCHS
    ):

        lr = (
            learning_rate_for_epoch(
                epoch
            )
        )

        optimizer.learning_rate.assign(
            lr
        )

        batch_metrics = []

        for (
            X_batch,
            Y_batch,
            face_batch,
            div_batch,
        ) in train_ds:

            values = train_step(
                model,
                optimizer,
                X_batch,
                Y_batch,
                face_batch,
                div_batch,
                tD_scale_tf,
                dxi,
            )

            batch_metrics.append(
                [
                    float(
                        value.numpy()
                    )
                    for value
                    in values
                ]
            )

        train_metrics = np.mean(
            batch_metrics,
            axis=0,
        )

        # ---------------------------------------------------------------------
        # Full validation
        # ---------------------------------------------------------------------

        val = evaluate_split(
            model,
            dataset[
                "X_val"
            ],
            dataset[
                "Y_val"
            ],
            targets[
                "face_val"
            ],
            targets[
                "div_val"
            ],
            xi,
            tD_scale,
        )

        score = checkpoint_score(
            val,
            baseline_val,
        )

        # ---------------------------------------------------------------------
        # History
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
            "train_FV",
            "train_face",
            "train_div",
            "train_mass",
            "train_injector",
            "train_late",
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

        history[
            "val_L1"
        ].append(
            val[
                "L1"
            ]
        )

        history[
            "val_L2"
        ].append(
            val[
                "L2"
            ]
        )

        history[
            "val_FV_MAE"
        ].append(
            val[
                "fv_relative_MAE"
            ]
        )

        history[
            "val_face_relative_MAE"
        ].append(
            val[
                "face_relative_MAE"
            ]
        )

        history[
            "val_div_relative_MAE"
        ].append(
            val[
                "div_relative_MAE"
            ]
        )

        history[
            "val_mass_MAE"
        ].append(
            val[
                "mass_relative_MAE"
            ]
        )

        history[
            "val_injector_L1"
        ].append(
            val[
                "injector_L1"
            ]
        )

        history[
            "val_late_L1"
        ].append(
            val[
                "late_L1"
            ]
        )

        history[
            "val_score"
        ].append(
            score
        )

        # ---------------------------------------------------------------------
        # Guardrails
        # ---------------------------------------------------------------------

        eligible = (
            val[
                "L1"
            ]
            < MAX_TEST_L1

            and

            val[
                "L2"
            ]
            < MAX_TEST_L2

            and

            val[
                "mass_relative_MAE"
            ]
            < MAX_MASS_RELATIVE_MAE

            and

            val[
                "injector_L1"
            ]
            < MAX_INJECTOR_L1
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

            patience_counter = 0

            model.save_weights(
                BEST_WEIGHTS_FILE
            )

        else:

            patience_counter += 1

        # ---------------------------------------------------------------------
        # Logging
        # ---------------------------------------------------------------------

        if (
            epoch == 0
            or
            (
                epoch + 1
            ) % 10 == 0
        ):

            fv_ratio = (
                val[
                    "fv_relative_MAE"
                ]
                /
                SG7A_TRUTH_FV_RELATIVE_MAE
            )

            div_improvement = (
                100.0
                * (
                    baseline_val[
                        "div_relative_MAE"
                    ]
                    -
                    val[
                        "div_relative_MAE"
                    ]
                )
                /
                max(
                    baseline_val[
                        "div_relative_MAE"
                    ],
                    1.0e-12,
                )
            )

            print(
                f"Epoch "
                f"{epoch + 1:4d}/{EPOCHS} | "
                f"lr={lr:.2e} | "
                f"L1={val['L1']:.3e} | "
                f"FV={val['fv_relative_MAE']:.3e} | "
                f"ratio={fv_ratio:6.1f} | "
                f"face={val['face_relative_MAE']:.3e} | "
                f"div={val['div_relative_MAE']:.3e} | "
                f"divImp={div_improvement:6.2f}% | "
                f"score={score:.3f}"
            )

        # ---------------------------------------------------------------------
        # Comfortable target
        # ---------------------------------------------------------------------

        comfortable = (
            val[
                "fv_relative_MAE"
            ]
            < 0.028

            and

            val[
                "L1"
            ]
            < 0.015

            and

            val[
                "mass_relative_MAE"
            ]
            < 0.025
        )

        if (
            comfortable
            and
            epoch >= 30
        ):

            print(
                "\nComfortable SG7B-6D "
                "validation target reached."
            )

            break

        # ---------------------------------------------------------------------
        # Early stopping
        # ---------------------------------------------------------------------

        if (
            patience_counter
            >= PATIENCE
        ):

            print(
                "\nSG7B-6D early stopping:"
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
    # Save history and final state
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
            "No eligible SG7B-6D checkpoint "
            "was produced."
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

        "baseline_val":
            baseline_val,

        "baseline_test":
            baseline_test,
    }


# =============================================================================
# FINAL TEST VALIDATION
# =============================================================================

def validate_test(
    result,
    baseline,
):

    fv_ratio = (
        result[
            "fv_relative_MAE"
        ]
        /
        SG7A_TRUTH_FV_RELATIVE_MAE
    )

    div_improvement = (
        100.0
        * (
            baseline[
                "div_relative_MAE"
            ]
            -
            result[
                "div_relative_MAE"
            ]
        )
        /
        max(
            baseline[
                "div_relative_MAE"
            ],
            1.0e-12,
        )
    )

    face_improvement = (
        100.0
        * (
            baseline[
                "face_relative_MAE"
            ]
            -
            result[
                "face_relative_MAE"
            ]
        )
        /
        max(
            baseline[
                "face_relative_MAE"
            ],
            1.0e-12,
        )
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
                "minimum_prediction"
            ]
            >= S_INITIAL
            - 1.0e-7,
        ),

        (
            "Saturation upper bound respected",
            result[
                "maximum_prediction"
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
            "Held-out L2 < 0.030",
            result[
                "L2"
            ]
            < MAX_TEST_L2,
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

        (
            "Advective divergence improves",
            result[
                "div_relative_MAE"
            ]
            <
            baseline[
                "div_relative_MAE"
            ],
        ),

        (
            "FV relative MAE < 0.031616",
            result[
                "fv_relative_MAE"
            ]
            <
            TARGET_FV_RELATIVE_MAE,
        ),

        (
            "PI-RNN / SG7A FV ratio < 50",
            fv_ratio
            < MAX_FV_RATIO,
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
        "V15-SG7B-6D VALIDATION"
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
        f"SG7A truth FV MAE         : "
        f"{SG7A_TRUTH_FV_RELATIVE_MAE:.6e}"
    )

    print(
        f"PI-RNN FV MAE             : "
        f"{result['fv_relative_MAE']:.6e}"
    )

    print(
        f"PI-RNN / SG7A ratio       : "
        f"{fv_ratio:.3f}"
    )

    print(
        f"Face-flux improvement     : "
        f"{face_improvement:.2f}%"
    )

    print(
        f"Adv-divergence improvement: "
        f"{div_improvement:.2f}%"
    )

    return (
        all_passed,
        float(
            fv_ratio
        ),
        float(
            face_improvement
        ),
        float(
            div_improvement
        ),
    )


# =============================================================================
# PLOTS
# =============================================================================

def plot_history(
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
            "val_face_relative_MAE"
        ],
        label="Face-flux relative MAE",
    )

    ax.semilogy(
        epoch,
        history[
            "val_div_relative_MAE"
        ],
        label="Adv-div relative MAE",
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
        "PAD-Stream V15-SG7B-6D\n"
        "Targeted Advective-Flux Refinement"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6D_Training_History.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_test_profiles(
    dataset,
    result,
):

    xi = dataset[
        "xi"
    ]

    tD = dataset[
        "tD_test"
    ]

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
                "SG7B-6D "
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
        "PAD-Stream V15-SG7B-6D\n"
        "Held-Out Advective-Refined Profiles"
    )

    ax.legend(
        fontsize=7,
        ncol=2,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6D_Test_Profiles.png",
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
        "PAD-Stream V15-SG7B-6D\n"
        "Held-Out Saturation Error vs Time"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6D_Error_vs_tD.png",
        dpi=300,
    )

    plt.close(
        fig
    )


# =============================================================================
# SAVE NUMERICAL RESULTS
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

        relative_FV=
            result[
                "relative_FV"
            ],
    )


# =============================================================================
# SUMMARY
# =============================================================================

def save_summary(
    training,
    result,
    passed,
    fv_ratio,
    face_improvement,
    div_improvement,
):

    baseline = (
        training[
            "baseline_test"
        ]
    )

    summary = {
        "milestone":
            "V15-SG7B-6D",

        "description":
            (
                "Targeted conservative advective-face-flux "
                "and divergence refinement"
            ),

        "source_model":
            "V15SG7B6B_Best_Model.keras",

        "architecture_changed":
            False,

        "canonical_truth_source":
            (
                "SG7A master_saturation directly"
            ),

        "canonical_advective_operator":
            (
                "positive-velocity Godunov/upwind"
            ),

        "canonical_SG7A_FV_relative_MAE":
            SG7A_TRUTH_FV_RELATIVE_MAE,

        "required_PI_RNN_FV_relative_MAE":
            TARGET_FV_RELATIVE_MAE,

        "training": {
            "runtime_seconds":
                float(
                    training[
                        "runtime"
                    ]
                ),

            "best_epoch":
                int(
                    training[
                        "best_epoch"
                    ]
                ),

            "best_score":
                float(
                    training[
                        "best_score"
                    ]
                ),

            "lambda_FV":
                LAMBDA_FV,

            "lambda_face_flux":
                LAMBDA_FACE_FLUX,

            "lambda_adv_divergence":
                LAMBDA_ADV_DIV,
        },

        "pre_refinement_test": {
            "L1":
                baseline[
                    "L1"
                ],

            "FV_relative_MAE":
                baseline[
                    "fv_relative_MAE"
                ],

            "face_relative_MAE":
                baseline[
                    "face_relative_MAE"
                ],

            "div_relative_MAE":
                baseline[
                    "div_relative_MAE"
                ],
        },

        "post_refinement_test": {
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

            "FV_relative_MAE":
                result[
                    "fv_relative_MAE"
                ],

            "FV_relative_RMS":
                result[
                    "fv_relative_RMS"
                ],

            "FV_ratio_to_SG7A":
                fv_ratio,

            "face_relative_MAE":
                result[
                    "face_relative_MAE"
                ],

            "div_relative_MAE":
                result[
                    "div_relative_MAE"
                ],

            "mass_relative_MAE":
                result[
                    "mass_relative_MAE"
                ],

            "injector_L1":
                result[
                    "injector_L1"
                ],

            "late_L1":
                result[
                    "late_L1"
                ],

            "minimum_prediction":
                result[
                    "minimum_prediction"
                ],

            "maximum_prediction":
                result[
                    "maximum_prediction"
                ],
        },

        "improvement": {
            "face_flux_percent":
                face_improvement,

            "advective_divergence_percent":
                div_improvement,
        },

        "validation_passed":
            bool(
                passed
            ),

        "status":
            (
                "PASS_CANDIDATE_FOR_FINAL_FREEZE"
                if passed
                else
                "ADVECTIVE_REFINEMENT_COMPLETE_TARGET_NOT_REACHED"
            ),

        "next_milestone":
            (
                "V15-SG7B-7R - independent final "
                "freeze validation"
                if passed
                else
                "Review SG7B-6D refinement trajectory"
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
        "PAD-Stream Version 15-SG7B-6D"
    )

    print(
        "Targeted Conservative Advective-Flux Refinement"
    )

    print(
        "=" * 78
    )

    print(
        f"\nTensorFlow version       : "
        f"{tf.__version__}"
    )

    print(
        "\nCANONICAL PHYSICS CONTRACT"
    )

    print(
        "  Truth source            : "
        "SG7A master_saturation"
    )

    print(
        "  Advective flux          : "
        "positive-flow Godunov/upwind"
    )

    print(
        f"  SG7A FV relative MAE    : "
        f"{SG7A_TRUTH_FV_RELATIVE_MAE:.6e}"
    )

    print(
        f"  Freeze ratio target     : "
        f"< {MAX_FV_RATIO:.1f}"
    )

    print(
        f"  Required PI-RNN FV MAE  : "
        f"< {TARGET_FV_RELATIVE_MAE:.6e}"
    )

    # -------------------------------------------------------------------------
    # Load
    # -------------------------------------------------------------------------

    dataset = load_dataset()

    sg7a = load_sg7a()

    if not SOURCE_MODEL_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-6B model:\n"
            f"{SOURCE_MODEL_FILE}"
        )

    model = tf.keras.models.load_model(
        SOURCE_MODEL_FILE
    )

    print(
        "\nSOURCE MODEL"
    )

    print(
        "  V15SG7B6B_Best_Model.keras"
    )

    print(
        "  Model load              : PASS"
    )

    print(
        f"  Parameters              : "
        f"{model.count_params():,}"
    )

    # -------------------------------------------------------------------------
    # Canonical advective target database
    # -------------------------------------------------------------------------

    print(
        "\nBUILDING CANONICAL ADVECTIVE TARGETS..."
    )

    targets = build_advective_targets(
        dataset,
        sg7a,
    )

    print(
        "  Training face targets   : "
        f"{targets['face_train'].shape}"
    )

    print(
        "  Training div targets    : "
        f"{targets['div_train'].shape}"
    )

    print(
        "  Validation face targets : "
        f"{targets['face_val'].shape}"
    )

    print(
        "  Test face targets       : "
        f"{targets['face_test'].shape}"
    )

    # -------------------------------------------------------------------------
    # Fine-tune
    # -------------------------------------------------------------------------

    training = fine_tune(
        model,
        dataset,
        targets,
    )

    print(
        "\nREFINEMENT COMPLETE"
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
    # Reload best
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
        targets[
            "face_test"
        ],
        targets[
            "div_test"
        ],
        xi,
        tD_scale,
    )

    print(
        "\nPOST-REFINEMENT HELD-OUT TEST"
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
        f"  Face relative MAE       : "
        f"{result['face_relative_MAE']:.6e}"
    )

    print(
        f"  Adv-div relative MAE    : "
        f"{result['div_relative_MAE']:.6e}"
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
    # Validate
    # -------------------------------------------------------------------------

    (
        passed,
        fv_ratio,
        face_improvement,
        div_improvement,
    ) = validate_test(
        result,
        training[
            "baseline_test"
        ],
    )

    # -------------------------------------------------------------------------
    # Save
    # -------------------------------------------------------------------------

    plot_history(
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

    save_results(
        dataset,
        result,
    )

    save_summary(
        training,
        result,
        passed,
        fv_ratio,
        face_improvement,
        div_improvement,
    )

    # -------------------------------------------------------------------------
    # Final
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
        "  V15SG7B6D_Best_Model.keras"
    )

    print(
        "  V15SG7B6D_Final_Model.keras"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B6D_Training_History.png"
    )

    print(
        "  V15SG7B6D_Test_Profiles.png"
    )

    print(
        "  V15SG7B6D_Error_vs_tD.png"
    )

    print(
        "\nNumerical:"
    )

    print(
        "  V15SG7B6D_Test_Results.npz"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B6D_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    if passed:

        print(
            "V15-SG7B-6D VALIDATION: PASS"
        )

        print()

        print(
            "STATUS: FINAL FREEZE CANDIDATE"
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7B-7R — Independent Final "
            "PI-RNN Freeze Validation"
        )

    else:

        print(
            "V15-SG7B-6D VALIDATION: "
            "TARGET NOT REACHED"
        )

        print()

        print(
            "DO NOT CHANGE ARCHITECTURE AUTOMATICALLY."
        )

        print()

        print(
            "Review whether explicit advective "
            "supervision lowered the residual floor."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()