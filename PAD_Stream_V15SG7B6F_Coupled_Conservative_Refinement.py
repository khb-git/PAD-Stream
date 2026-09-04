from pathlib import Path
import json
import time

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7B-6F
# Coupled Conservative Component Refinement
#
# PURPOSE
# -------
# Fine-tune the SG7B-6D model using the COUPLED conservative balance rather
# than aggressively optimizing any one PDE component in isolation.
#
#
# SOURCE MODEL
# ------------
#       V15SG7B6D_Best_Model.keras
#
#
# CANONICAL TRUTH
# ---------------
#       SG7A master_saturation
#
#
# GOVERNING BALANCE
# -----------------
#
#       R =
#           dS/dtD
#           +
#           div(F_adv)
#           -
#           div(G_cap)
#
#
# Canonical target:
#
#       R_truth =
#           dS_truth/dtD
#           +
#           div(F_adv_truth)
#           -
#           div(G_cap_truth)
#
#
# Main new loss:
#
#       L_balance =
#           mean(
#               (R_pred - R_truth)^2
#           )
#
#
# Weak component regularizers:
#
#       L_t
#       L_adv
#       L_cap
#
#
# Full training objective:
#
#       L_total =
#           lambda_data    * L_data
#         + lambda_balance * L_balance
#         + lambda_FV      * L_FV
#         + lambda_t       * L_t
#         + lambda_adv     * L_adv
#         + lambda_cap     * L_cap
#         + lambda_mass    * L_mass
#
#
# NO:
#   - Fourier features
#   - FiLM
#   - front-coordinate input
#   - architecture expansion
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

SG7A_FILE = (
    ROOT
    / "output"
    / "V15_SG7A"
    / "FULL_PHYSICS_STREAMLINE_SATURATION.npz"
)

SOURCE_MODEL_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6D"
    / "V15SG7B6D_Best_Model.keras"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B6F"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

BEST_WEIGHTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B6F_Best.weights.h5"
)

BEST_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B6F_Best_Model.keras"
)

FINAL_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B6F_Final_Model.keras"
)

HISTORY_FILE = (
    OUTPUT_DIR
    / "V15SG7B6F_Training_History.npz"
)

TEST_RESULTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B6F_Test_Results.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B6F_Summary.json"
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
# CANONICAL FREEZE TARGETS
# =============================================================================

SG7A_TRUTH_FV_RELATIVE_MAE = 6.323248e-04

MAX_FV_RATIO = 50.0

TARGET_FV_RELATIVE_MAE = (
    SG7A_TRUTH_FV_RELATIVE_MAE
    * MAX_FV_RATIO
)


# =============================================================================
# DIMENSIONS
# =============================================================================

SEQUENCE_LENGTH = 201
N_FACES = 202

BATCH_SIZE = 32


# =============================================================================
# TRAINING CONFIGURATION
# =============================================================================

EPOCHS = 260

PATIENCE = 70

GRADIENT_CLIP_NORM = 5.0


# -----------------------------------------------------------------------------
# Learning rate
# -----------------------------------------------------------------------------

LR_STAGE_1 = 2.5e-5
LR_STAGE_2 = 1.0e-5
LR_STAGE_3 = 5.0e-6

LR_STAGE_2_EPOCH = 100
LR_STAGE_3_EPOCH = 190


# =============================================================================
# LOSS WEIGHTS
# =============================================================================

# Preserve extremely accurate SG7B-6D saturation fit.
LAMBDA_DATA = 1.00

# Central new term.
LAMBDA_BALANCE = 1.00

# Keep normalized FV consistency present.
LAMBDA_FV = 0.20

# Weak component regularizers only.
LAMBDA_TEMPORAL = 0.05
LAMBDA_ADV = 0.05
LAMBDA_CAP = 0.05

# Preserve mass.
LAMBDA_MASS = 0.30


# =============================================================================
# CHECKPOINT SCORE
# =============================================================================

SCORE_WEIGHT_FV = 2.0
SCORE_WEIGHT_BALANCE = 1.5
SCORE_WEIGHT_DATA = 0.5
SCORE_WEIGHT_MASS = 0.25


# =============================================================================
# GUARDRAILS
# =============================================================================

MAX_TEST_L1 = 0.020
MAX_TEST_L2 = 0.030
MAX_MASS_RELATIVE_MAE = 0.030


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
# NUMPY PHYSICS
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
            1.0 - Se
        ) ** N_RES
    )

    mob_disp = (
        kr_disp
        / MU_DISP
    )

    mob_res = (
        kr_res
        / MU_RES
    )

    return (
        mob_disp
        /
        (
            mob_disp
            + mob_res
            + 1.0e-14
        )
    )


def diffusion_shape_np(S):

    span = (
        1.0
        - SWC
        - SOR
    )

    Se = np.clip(
        (
            np.asarray(
                S,
                dtype=np.float64,
            )
            - SWC
        )
        / span,
        1.0e-6,
        1.0 - 1.0e-6,
    )

    kr_res = (
        KR_RES_MAX
        * (
            1.0 - Se
        ) ** N_RES
    )

    fw = fractional_flow_np(
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
        * Se ** exponent
    )

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

    mob_disp_mid = (
        kr_disp_mid
        / MU_DISP
    )

    mob_res_mid = (
        kr_res_mid
        / MU_RES
    )

    fw_mid = (
        mob_disp_mid
        /
        (
            mob_disp_mid
            + mob_res_mid
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
# CANONICAL SPATIAL COMPONENTS
# =============================================================================

def canonical_spatial_components_np(
    S,
    xi,
):

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
    )

    u_face = np.exp(
        NC
        * face_xi
    )

    fw = fractional_flow_np(
        S
    )

    # -------------------------------------------------------------------------
    # Advective flux
    # -------------------------------------------------------------------------

    F = np.zeros(
        n + 1,
        dtype=np.float64,
    )

    F[0] = (
        u_face[0]
        * fractional_flow_np(
            np.array(
                [S_INJECTED]
            )
        )[0]
    )

    F[1:n] = (
        u_face[1:n]
        * fw[:-1]
    )

    F[n] = (
        u_face[n]
        * fw[-1]
    )

    div_adv = (
        F[1:]
        - F[:-1]
    ) / dxi

    # -------------------------------------------------------------------------
    # Capillary flux
    # -------------------------------------------------------------------------

    D = diffusion_shape_np(
        S
    )

    G = np.zeros(
        n + 1,
        dtype=np.float64,
    )

    D_inj = float(
        diffusion_shape_np(
            np.array(
                [S_INJECTED]
            )
        )[0]
    )

    D_left = (
        0.5
        * (
            D_inj
            + D[0]
        )
    )

    G[0] = (
        POROSITY
        / PE_C
        * D_left
        * (
            S[0]
            - S_INJECTED
        )
        /
        (
            0.5
            * dxi
        )
    )

    for face in range(
        1,
        n,
    ):

        D_face = (
            0.5
            * (
                D[
                    face - 1
                ]
                +
                D[
                    face
                ]
            )
        )

        G[face] = (
            POROSITY
            / PE_C
            * D_face
            * (
                S[
                    face
                ]
                -
                S[
                    face - 1
                ]
            )
            / dxi
        )

    G[n] = 0.0

    div_cap = (
        G[1:]
        - G[:-1]
    ) / dxi

    return (
        div_adv,
        div_cap,
    )


# =============================================================================
# SG7A TEMPORAL DERIVATIVE
# =============================================================================

def temporal_derivative_np(
    master_tD,
    master_S,
    index,
):

    index = int(index)

    if index == 0:

        dt = (
            master_tD[1]
            - master_tD[0]
        )

        return (
            master_S[1]
            - master_S[0]
        ) / dt

    if index == (
        len(master_tD)
        - 1
    ):

        dt = (
            master_tD[-1]
            - master_tD[-2]
        )

        return (
            master_S[-1]
            - master_S[-2]
        ) / dt

    dt = (
        master_tD[
            index + 1
        ]
        -
        master_tD[
            index - 1
        ]
    )

    return (
        master_S[
            index + 1
        ]
        -
        master_S[
            index - 1
        ]
    ) / dt


# =============================================================================
# BUILD CANONICAL COMPONENT TARGETS
# =============================================================================

def build_component_targets(
    dataset,
    sg7a,
):

    xi = np.asarray(
        sg7a[
            "xi"
        ],
        dtype=np.float64,
    )

    master_tD = np.asarray(
        sg7a[
            "master_tD"
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

        n_profiles = len(indices)

        target_t = np.zeros(
            (
                n_profiles,
                SEQUENCE_LENGTH,
            ),
            dtype=np.float32,
        )

        target_adv = np.zeros_like(
            target_t
        )

        target_cap = np.zeros_like(
            target_t
        )

        target_residual = np.zeros_like(
            target_t
        )

        for p, index in enumerate(
            indices
        ):

            S = master_S[
                index
            ]

            temporal = temporal_derivative_np(
                master_tD,
                master_S,
                index,
            )

            adv, cap = (
                canonical_spatial_components_np(
                    S,
                    xi,
                )
            )

            residual = (
                temporal
                + adv
                - cap
            )

            target_t[p] = temporal.astype(
                np.float32
            )

            target_adv[p] = adv.astype(
                np.float32
            )

            target_cap[p] = cap.astype(
                np.float32
            )

            target_residual[p] = residual.astype(
                np.float32
            )

        targets[
            f"temporal_{split}"
        ] = target_t

        targets[
            f"adv_{split}"
        ] = target_adv

        targets[
            f"cap_{split}"
        ] = target_cap

        targets[
            f"residual_{split}"
        ] = target_residual

    return targets


# =============================================================================
# TF PHYSICS
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

    mob_disp = (
        kr_disp
        / MU_DISP
    )

    mob_res = (
        kr_res
        / MU_RES
    )

    return (
        mob_disp
        /
        (
            mob_disp
            + mob_res
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

    mob_disp_mid = (
        kr_disp_mid
        / MU_DISP
    )

    mob_res_mid = (
        kr_res_mid
        / MU_RES
    )

    fw_mid = (
        mob_disp_mid
        /
        (
            mob_disp_mid
            + mob_res_mid
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
# ARBITRARY TIME INPUT
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
# DIFFERENTIABLE MODEL COMPONENTS
# =============================================================================

def model_components_tf(
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
    # Model saturation
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

    # -------------------------------------------------------------------------
    # Temporal
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

    temporal = (
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
    # Advective divergence
    # -------------------------------------------------------------------------

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

    outlet_face = (
        fw[
            :,
            -1:
        ]
        *
        u_face[-1]
    )

    F = tf.concat(
        [
            left_face,
            internal_faces,
            outlet_face,
        ],
        axis=1,
    )

    adv = (
        F[
            :,
            1:
        ]
        -
        F[
            :,
            :-1
        ]
    ) / dxi

    # -------------------------------------------------------------------------
    # Capillary divergence
    # -------------------------------------------------------------------------

    D = diffusion_shape_tf(
        S
    )

    D_internal = (
        0.5
        * (
            D[
                :,
                :-1
            ]
            +
            D[
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
            D[
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

    G = tf.concat(
        [
            G_left,
            G_internal,
            G_right,
        ],
        axis=1,
    )

    cap = (
        G[
            :,
            1:
        ]
        -
        G[
            :,
            :-1
        ]
    ) / dxi

    # -------------------------------------------------------------------------
    # Full residual
    # -------------------------------------------------------------------------

    residual = (
        temporal
        +
        adv
        -
        cap
    )

    scale = (
        tf.abs(
            temporal
        )
        +
        tf.abs(
            adv
        )
        +
        tf.abs(
            cap
        )
        +
        1.0e-4
    )

    relative = (
        residual
        / scale
    )

    return (
        S,
        temporal,
        adv,
        cap,
        residual,
        relative,
    )


# =============================================================================
# NORMALIZED COMPONENT LOSS
# =============================================================================

def normalized_component_loss(
    prediction,
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
                prediction
                - target
            )
        )
        /
        scale
    )


# =============================================================================
# MASS
# =============================================================================

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

    true_mass = (
        dxi
        * (
            tf.reduce_sum(
                truth[
                    :,
                    1:-1
                ],
                axis=1,
            )
            +
            0.5
            * (
                truth[
                    :,
                    0
                ]
                +
                truth[
                    :,
                    -1
                ]
            )
        )
    )

    pred_mass = (
        dxi
        * (
            tf.reduce_sum(
                pred[
                    :,
                    1:-1
                ],
                axis=1,
            )
            +
            0.5
            * (
                pred[
                    :,
                    0
                ]
                +
                pred[
                    :,
                    -1
                ]
            )
        )
    )

    return tf.reduce_mean(
        tf.square(
            pred_mass
            - true_mass
        )
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
    target_temporal,
    target_adv,
    target_cap,
    target_residual,
    tD_scale,
    dxi,
):

    with tf.GradientTape() as tape:

        (
            S,
            temporal,
            adv,
            cap,
            residual,
            relative,
        ) = model_components_tf(
            model,
            X,
            tD_scale,
            training=True,
        )

        Y_pred = (
            S[
                :,
                :,
                None
            ]
        )

        # ---------------------------------------------------------------------
        # Data
        # ---------------------------------------------------------------------

        L_data = tf.reduce_mean(
            tf.square(
                Y_pred
                - Y
            )
        )

        # ---------------------------------------------------------------------
        # Coupled discrete balance
        # ---------------------------------------------------------------------

        L_balance = (
            normalized_component_loss(
                residual,
                target_residual,
            )
        )

        # ---------------------------------------------------------------------
        # Absolute FV residual
        # ---------------------------------------------------------------------

        L_fv = tf.reduce_mean(
            tf.square(
                relative
            )
        )

        # ---------------------------------------------------------------------
        # Weak component regularizers
        # ---------------------------------------------------------------------

        L_t = (
            normalized_component_loss(
                temporal,
                target_temporal,
            )
        )

        L_adv = (
            normalized_component_loss(
                adv,
                target_adv,
            )
        )

        L_cap = (
            normalized_component_loss(
                cap,
                target_cap,
            )
        )

        # ---------------------------------------------------------------------
        # Mass
        # ---------------------------------------------------------------------

        L_mass = (
            mass_loss(
                Y,
                Y_pred,
                dxi,
            )
        )

        # ---------------------------------------------------------------------
        # Total
        # ---------------------------------------------------------------------

        total = (
            LAMBDA_DATA
            * L_data

            +
            LAMBDA_BALANCE
            * L_balance

            +
            LAMBDA_FV
            * L_fv

            +
            LAMBDA_TEMPORAL
            * L_t

            +
            LAMBDA_ADV
            * L_adv

            +
            LAMBDA_CAP
            * L_cap

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
        L_balance,
        L_fv,
        L_t,
        L_adv,
        L_cap,
        L_mass,
    )


# =============================================================================
# DATASET PIPELINE
# =============================================================================

def make_tf_dataset(
    X,
    Y,
    temporal,
    adv,
    cap,
    residual,
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
                temporal.astype(
                    np.float32
                ),
                adv.astype(
                    np.float32
                ),
                cap.astype(
                    np.float32
                ),
                residual.astype(
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
    target_temporal,
    target_adv,
    target_cap,
    target_residual,
    xi,
    tD_scale,
):

    X_tf = tf.constant(
        X.astype(
            np.float32
        )
    )

    (
        S_tf,
        temporal_tf,
        adv_tf,
        cap_tf,
        residual_tf,
        relative_tf,
    ) = model_components_tf(
        model,
        X_tf,
        tf.constant(
            tD_scale,
            dtype=tf.float32,
        ),
        training=False,
    )

    prediction = (
        S_tf.numpy()
    )

    truth = (
        Y[
            :,
            :,
            0
        ]
    )

    temporal = (
        temporal_tf.numpy()
    )

    adv = (
        adv_tf.numpy()
    )

    cap = (
        cap_tf.numpy()
    )

    residual = (
        residual_tf.numpy()
    )

    relative = (
        relative_tf.numpy()
    )

    error = (
        prediction
        - truth
    )

    # -------------------------------------------------------------------------
    # Saturation
    # -------------------------------------------------------------------------

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
    # Physics
    # -------------------------------------------------------------------------

    FV_MAE = float(
        np.mean(
            np.abs(
                relative
            )
        )
    )

    FV_RMS = float(
        np.sqrt(
            np.mean(
                relative ** 2
            )
        )
    )

    balance_error = (
        residual
        - target_residual
    )

    balance_MAE = float(
        np.mean(
            np.abs(
                balance_error
            )
        )
    )

    temporal_MAE = float(
        np.mean(
            np.abs(
                temporal
                - target_temporal
            )
        )
    )

    adv_MAE = float(
        np.mean(
            np.abs(
                adv
                - target_adv
            )
        )
    )

    cap_MAE = float(
        np.mean(
            np.abs(
                cap
                - target_cap
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

    return {
        "truth":
            truth,

        "prediction":
            prediction,

        "error":
            error,

        "L1":
            L1,

        "L2":
            L2,

        "Linf":
            Linf,

        "FV_MAE":
            FV_MAE,

        "FV_RMS":
            FV_RMS,

        "balance_MAE":
            balance_MAE,

        "temporal_MAE":
            temporal_MAE,

        "adv_MAE":
            adv_MAE,

        "cap_MAE":
            cap_MAE,

        "mass_relative_MAE":
            mass_relative_MAE,

        "profile_L1":
            np.mean(
                np.abs(
                    error
                ),
                axis=1,
            ),

        "relative_FV":
            relative,
    }


# =============================================================================
# CHECKPOINT SCORE
# =============================================================================

def checkpoint_score(
    metrics,
    baseline_balance,
):

    fv_term = (
        metrics[
            "FV_MAE"
        ]
        /
        TARGET_FV_RELATIVE_MAE
    )

    balance_term = (
        metrics[
            "balance_MAE"
        ]
        /
        max(
            baseline_balance,
            1.0e-12,
        )
    )

    data_term = (
        metrics[
            "L1"
        ]
        /
        MAX_TEST_L1
    )

    mass_term = (
        metrics[
            "mass_relative_MAE"
        ]
        /
        MAX_MASS_RELATIVE_MAE
    )

    return float(
        SCORE_WEIGHT_FV
        * fv_term

        +
        SCORE_WEIGHT_BALANCE
        * balance_term

        +
        SCORE_WEIGHT_DATA
        * data_term

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

    train_ds = make_tf_dataset(
        dataset[
            "X_train"
        ],
        dataset[
            "Y_train"
        ],
        targets[
            "temporal_train"
        ],
        targets[
            "adv_train"
        ],
        targets[
            "cap_train"
        ],
        targets[
            "residual_train"
        ],
        True,
    )

    optimizer = (
        tf.keras.optimizers.Adam(
            learning_rate=(
                LR_STAGE_1
            )
        )
    )

    # -------------------------------------------------------------------------
    # Incoming baseline
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
            "temporal_val"
        ],
        targets[
            "adv_val"
        ],
        targets[
            "cap_val"
        ],
        targets[
            "residual_val"
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
            "temporal_test"
        ],
        targets[
            "adv_test"
        ],
        targets[
            "cap_test"
        ],
        targets[
            "residual_test"
        ],
        xi,
        tD_scale,
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "PRE-REFINEMENT SG7B-6D BASELINE"
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
        f"{baseline_val['FV_MAE']:.6e}"
    )

    print(
        f"Validation balance MAE    : "
        f"{baseline_val['balance_MAE']:.6e}"
    )

    print(
        f"Test L1                   : "
        f"{baseline_test['L1']:.6e}"
    )

    print(
        f"Test FV MAE               : "
        f"{baseline_test['FV_MAE']:.6e}"
    )

    print(
        f"Test FV / SG7A ratio      : "
        f"{baseline_test['FV_MAE'] / SG7A_TRUTH_FV_RELATIVE_MAE:.3f}"
    )

    print(
        f"Test balance MAE          : "
        f"{baseline_test['balance_MAE']:.6e}"
    )

    print(
        "=" * 78
    )

    # -------------------------------------------------------------------------
    # History
    # -------------------------------------------------------------------------

    history = {
        "epoch": [],
        "learning_rate": [],

        "train_total": [],
        "train_data": [],
        "train_balance": [],
        "train_FV": [],
        "train_temporal": [],
        "train_adv": [],
        "train_cap": [],
        "train_mass": [],

        "val_L1": [],
        "val_FV_MAE": [],
        "val_balance_MAE": [],
        "val_temporal_MAE": [],
        "val_adv_MAE": [],
        "val_cap_MAE": [],
        "val_mass_MAE": [],
        "val_score": [],
    }

    best_score = np.inf
    best_epoch = -1
    patience_counter = 0

    start_time = (
        time.perf_counter()
    )

    # -------------------------------------------------------------------------
    # Training loop
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

        train_rows = []

        for (
            X_batch,
            Y_batch,
            target_t,
            target_adv,
            target_cap,
            target_residual,
        ) in train_ds:

            values = train_step(
                model,
                optimizer,
                X_batch,
                Y_batch,
                target_t,
                target_adv,
                target_cap,
                target_residual,
                tD_scale_tf,
                dxi,
            )

            train_rows.append(
                [
                    float(
                        value.numpy()
                    )
                    for value
                    in values
                ]
            )

        train_mean = np.mean(
            train_rows,
            axis=0,
        )

        # ---------------------------------------------------------------------
        # Validation
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
                "temporal_val"
            ],
            targets[
                "adv_val"
            ],
            targets[
                "cap_val"
            ],
            targets[
                "residual_val"
            ],
            xi,
            tD_scale,
        )

        score = checkpoint_score(
            val,
            baseline_val[
                "balance_MAE"
            ],
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
            "train_balance",
            "train_FV",
            "train_temporal",
            "train_adv",
            "train_cap",
            "train_mass",
        ]

        for (
            key,
            value
        ) in zip(
            train_keys,
            train_mean,
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
            "val_FV_MAE"
        ].append(
            val[
                "FV_MAE"
            ]
        )

        history[
            "val_balance_MAE"
        ].append(
            val[
                "balance_MAE"
            ]
        )

        history[
            "val_temporal_MAE"
        ].append(
            val[
                "temporal_MAE"
            ]
        )

        history[
            "val_adv_MAE"
        ].append(
            val[
                "adv_MAE"
            ]
        )

        history[
            "val_cap_MAE"
        ].append(
            val[
                "cap_MAE"
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
        )

        if (
            eligible
            and
            score < best_score
        ):

            best_score = score
            best_epoch = epoch + 1
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

            ratio = (
                val[
                    "FV_MAE"
                ]
                /
                SG7A_TRUTH_FV_RELATIVE_MAE
            )

            balance_improvement = (
                100.0
                * (
                    baseline_val[
                        "balance_MAE"
                    ]
                    -
                    val[
                        "balance_MAE"
                    ]
                )
                /
                max(
                    baseline_val[
                        "balance_MAE"
                    ],
                    1.0e-12,
                )
            )

            print(
                f"Epoch "
                f"{epoch + 1:4d}/{EPOCHS} | "
                f"lr={lr:.2e} | "
                f"L1={val['L1']:.3e} | "
                f"FV={val['FV_MAE']:.3e} | "
                f"ratio={ratio:6.1f} | "
                f"bal={val['balance_MAE']:.3e} | "
                f"balImp={balance_improvement:6.2f}% | "
                f"t={val['temporal_MAE']:.3e} | "
                f"A={val['adv_MAE']:.3e} | "
                f"C={val['cap_MAE']:.3e} | "
                f"score={score:.3f}"
            )

        # ---------------------------------------------------------------------
        # Comfortable target
        # ---------------------------------------------------------------------

        comfortable = (
            val[
                "FV_MAE"
            ]
            < 0.028

            and

            val[
                "L1"
            ]
            < 0.015

            and

            val[
                "balance_MAE"
            ]
            <
            baseline_val[
                "balance_MAE"
            ]
        )

        if (
            comfortable
            and
            epoch >= 30
        ):

            print(
                "\nComfortable coupled-conservative "
                "target reached."
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
                "\nSG7B-6F early stopping:"
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
    # Save
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
            "No eligible SG7B-6F checkpoint "
            "was created."
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
# FINAL VALIDATION
# =============================================================================

def validate_test(
    result,
    baseline,
):

    fv_ratio = (
        result[
            "FV_MAE"
        ]
        /
        SG7A_TRUTH_FV_RELATIVE_MAE
    )

    balance_improvement = (
        100.0
        * (
            baseline[
                "balance_MAE"
            ]
            -
            result[
                "balance_MAE"
            ]
        )
        /
        max(
            baseline[
                "balance_MAE"
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
            "Coupled balance improves",
            result[
                "balance_MAE"
            ]
            <
            baseline[
                "balance_MAE"
            ],
        ),

        (
            "FV relative MAE < 0.031616",
            result[
                "FV_MAE"
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

    passed = all(
        status
        for _, status
        in checks
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-6F VALIDATION"
    )

    print(
        "=" * 78
    )

    for (
        description,
        status
    ) in checks:

        print(
            f"[{'PASS' if status else 'FAIL':4s}] "
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
        f"{result['FV_MAE']:.6e}"
    )

    print(
        f"PI-RNN / SG7A ratio       : "
        f"{fv_ratio:.3f}"
    )

    print(
        f"Coupled balance change    : "
        f"{balance_improvement:.2f}%"
    )

    return (
        passed,
        float(
            fv_ratio
        ),
        float(
            balance_improvement
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
            "val_balance_MAE"
        ],
        label="Coupled balance MAE",
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
        "PAD-Stream V15-SG7B-6F\n"
        "Coupled Conservative Refinement"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6F_Training_History.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_profiles(
    dataset,
    result,
):

    xi = dataset[
        "xi"
    ]

    positions = np.linspace(
        0,
        len(
            result[
                "truth"
            ]
        )
        - 1,
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
                f"SG7A #{p}"
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
                f"SG7B-6F #{p}"
            ),
        )

    ax.set_xlabel(
        r"$\xi$"
    )

    ax.set_ylabel(
        "Saturation"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6F\n"
        "Held-Out Coupled-Conservative Profiles"
    )

    ax.legend(
        fontsize=7,
        ncol=2,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6F_Test_Profiles.png",
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
        "PAD-Stream V15-SG7B-6F\n"
        "Held-Out Saturation Error vs Time"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6F_Error_vs_tD.png",
        dpi=300,
    )

    plt.close(
        fig
    )


# =============================================================================
# SAVE RESULTS
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
    balance_improvement,
):

    baseline = (
        training[
            "baseline_test"
        ]
    )

    summary = {
        "milestone":
            "V15-SG7B-6F",

        "description":
            (
                "Coupled conservative component refinement "
                "starting from SG7B-6D"
            ),

        "source_model":
            "V15SG7B6D_Best_Model.keras",

        "architecture_changed":
            False,

        "canonical_truth":
            "SG7A master_saturation",

        "loss_design": {
            "lambda_data":
                LAMBDA_DATA,

            "lambda_balance":
                LAMBDA_BALANCE,

            "lambda_FV":
                LAMBDA_FV,

            "lambda_temporal":
                LAMBDA_TEMPORAL,

            "lambda_adv":
                LAMBDA_ADV,

            "lambda_cap":
                LAMBDA_CAP,

            "lambda_mass":
                LAMBDA_MASS,
        },

        "pre_refinement_test": {
            "L1":
                baseline[
                    "L1"
                ],

            "FV_MAE":
                baseline[
                    "FV_MAE"
                ],

            "balance_MAE":
                baseline[
                    "balance_MAE"
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

            "FV_MAE":
                result[
                    "FV_MAE"
                ],

            "FV_RMS":
                result[
                    "FV_RMS"
                ],

            "FV_ratio_to_SG7A":
                fv_ratio,

            "balance_MAE":
                result[
                    "balance_MAE"
                ],

            "temporal_MAE":
                result[
                    "temporal_MAE"
                ],

            "adv_MAE":
                result[
                    "adv_MAE"
                ],

            "cap_MAE":
                result[
                    "cap_MAE"
                ],

            "mass_relative_MAE":
                result[
                    "mass_relative_MAE"
                ],
        },

        "balance_improvement_percent":
            balance_improvement,

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

        "validation_passed":
            bool(
                passed
            ),

        "status":
            (
                "PASS_CANDIDATE_FOR_FINAL_FREEZE"
                if passed
                else
                "COUPLED_REFINEMENT_COMPLETE_TARGET_NOT_REACHED"
            ),

        "next_milestone":
            (
                "V15-SG7B-7R — Independent Final Freeze Validation"
                if passed
                else
                "Review SG7B-6F coupled-balance trajectory"
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
        "PAD-Stream Version 15-SG7B-6F"
    )

    print(
        "Coupled Conservative Component Refinement"
    )

    print(
        "=" * 78
    )

    print(
        f"\nTensorFlow version       : "
        f"{tf.__version__}"
    )

    print(
        "\nCOUPLED LOSS DESIGN"
    )

    print(
        f"  Balance weight          : "
        f"{LAMBDA_BALANCE}"
    )

    print(
        f"  FV weight               : "
        f"{LAMBDA_FV}"
    )

    print(
        f"  Temporal regularizer    : "
        f"{LAMBDA_TEMPORAL}"
    )

    print(
        f"  Advective regularizer   : "
        f"{LAMBDA_ADV}"
    )

    print(
        f"  Capillary regularizer   : "
        f"{LAMBDA_CAP}"
    )

    print(
        f"  FV freeze target        : "
        f"< {TARGET_FV_RELATIVE_MAE:.6e}"
    )

    # -------------------------------------------------------------------------
    # Load
    # -------------------------------------------------------------------------

    dataset = load_dataset()

    sg7a = load_sg7a()

    if not SOURCE_MODEL_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-6D model:\n"
            f"{SOURCE_MODEL_FILE}"
        )

    model = tf.keras.models.load_model(
        SOURCE_MODEL_FILE
    )

    print(
        "\nSOURCE MODEL"
    )

    print(
        "  V15SG7B6D_Best_Model.keras"
    )

    print(
        "  Load                    : PASS"
    )

    print(
        f"  Parameters              : "
        f"{model.count_params():,}"
    )

    # -------------------------------------------------------------------------
    # Targets
    # -------------------------------------------------------------------------

    print(
        "\nBUILDING CANONICAL COUPLED TARGETS..."
    )

    targets = build_component_targets(
        dataset,
        sg7a,
    )

    print(
        f"  Train temporal          : "
        f"{targets['temporal_train'].shape}"
    )

    print(
        f"  Train advective         : "
        f"{targets['adv_train'].shape}"
    )

    print(
        f"  Train capillary         : "
        f"{targets['cap_train'].shape}"
    )

    print(
        f"  Train residual          : "
        f"{targets['residual_train'].shape}"
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
    # Best checkpoint
    # -------------------------------------------------------------------------

    best_model = tf.keras.models.load_model(
        BEST_MODEL_FILE
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
            "temporal_test"
        ],
        targets[
            "adv_test"
        ],
        targets[
            "cap_test"
        ],
        targets[
            "residual_test"
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
        f"{result['FV_MAE']:.6e}"
    )

    print(
        f"  FV relative RMS         : "
        f"{result['FV_RMS']:.6e}"
    )

    print(
        f"  Coupled balance MAE     : "
        f"{result['balance_MAE']:.6e}"
    )

    print(
        f"  Temporal difference MAE : "
        f"{result['temporal_MAE']:.6e}"
    )

    print(
        f"  Advective difference MAE: "
        f"{result['adv_MAE']:.6e}"
    )

    print(
        f"  Capillary difference MAE: "
        f"{result['cap_MAE']:.6e}"
    )

    print(
        f"  Mass relative MAE       : "
        f"{result['mass_relative_MAE']:.6e}"
    )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    (
        passed,
        fv_ratio,
        balance_improvement,
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

    plot_profiles(
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
        balance_improvement,
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
        "  V15SG7B6F_Best_Model.keras"
    )

    print(
        "  V15SG7B6F_Final_Model.keras"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B6F_Training_History.png"
    )

    print(
        "  V15SG7B6F_Test_Profiles.png"
    )

    print(
        "  V15SG7B6F_Error_vs_tD.png"
    )

    print(
        "\nNumerical:"
    )

    print(
        "  V15SG7B6F_Test_Results.npz"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B6F_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    if passed:

        print(
            "V15-SG7B-6F VALIDATION: PASS"
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
            "V15-SG7B-6F VALIDATION: "
            "TARGET NOT REACHED"
        )

        print()

        print(
            "Review whether coupled balance improved "
            "without restoring a large normalized FV residual."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()