from pathlib import Path
import json
import time

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7B-6F-R
# Activity-Scaled Coupled Conservative Refinement
#
# PURPOSE
# -------
# Correct the loss-scaling problem identified in V15-SG7B-6F.
#
# SG7B-6F attempted coupled conservative refinement starting from the
# highly accurate SG7B-6D checkpoint. However, its coupled balance loss
# was normalized by the magnitude of the SG7A residual itself.
#
# Because the frozen SG7A finite-volume residual is intentionally very
# small, that normalization produced an excessively large effective
# optimization force. The model therefore moved immediately away from
# the strong SG7B-6D starting solution.
#
#
# CORRECTED COUPLED LOSS
# ----------------------
#
# Governing equation:
#
#       R =
#           dS/dtD
#           +
#           div(F_adv)
#           -
#           div(G_cap)
#
#
# Canonical SG7A activity:
#
#       A_SG7A =
#           |dS/dtD|
#           +
#           |div(F_adv)|
#           +
#           |div(G_cap)|
#           +
#           1e-4
#
#
# Corrected coupled balance loss:
#
#       L_balance =
#           mean(
#               [
#                   (R_NN - R_SG7A)
#                   /
#                   A_SG7A
#               ]^2
#           )
#
#
# SOURCE MODEL
# ------------
#
#       V15SG7B6D_Best_Model.keras
#
#
# CHECKPOINT CONTRACT
# -------------------
#
# Epoch zero is a valid checkpoint.
#
# The incoming SG7B-6D model is saved before fine-tuning starts.
# A refined SG7B-6F-R checkpoint must actually outperform the incoming
# SG7B-6D checkpoint before replacing it.
#
#
# ARCHITECTURE
# ------------
#
# No architecture changes:
#
#       Plain stacked LSTM
#       Hidden units = 64
#       LSTM layers = 2
#
#       Fourier features = False
#       FiLM = False
#       Front coordinate = False
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
    / "V15_SG7B6FR"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


BEST_WEIGHTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B6FR_Best.weights.h5"
)


BEST_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B6FR_Best_Model.keras"
)


FINAL_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B6FR_Final_Model.keras"
)


HISTORY_FILE = (
    OUTPUT_DIR
    / "V15SG7B6FR_Training_History.npz"
)


TEST_RESULTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B6FR_Test_Results.npz"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B6FR_Summary.json"
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
# CANONICAL FREEZE TARGET
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
# V15-SG7B-6F-R TRAINING CONFIGURATION
# =============================================================================

EPOCHS = 220

PATIENCE = 60

GRADIENT_CLIP_NORM = 5.0


# -----------------------------------------------------------------------------
# Conservative low-learning-rate refinement
#
# SG7B-6D is already a highly accurate surrogate.
# SG7B-6F-R therefore uses substantially smaller updates than SG7B-6F.
# -----------------------------------------------------------------------------

LR_STAGE_1 = 5.0e-6
LR_STAGE_2 = 2.5e-6
LR_STAGE_3 = 1.0e-6

LR_STAGE_2_EPOCH = 80
LR_STAGE_3_EPOCH = 150


# =============================================================================
# CORRECTED LOSS WEIGHTS
# =============================================================================

# Preserve SG7B-6D saturation accuracy.
LAMBDA_DATA = 1.00


# Activity-scaled coupled conservative balance.
#
# Reduced from SG7B-6F because the corrected normalization now carries
# physically meaningful local scaling.
LAMBDA_BALANCE = 0.25


# Direct normalized finite-volume residual.
LAMBDA_FV = 0.20


# Weak individual PDE-component regularizers.
#
# These are deliberately secondary to the full coupled balance.
LAMBDA_TEMPORAL = 0.025
LAMBDA_ADV = 0.025
LAMBDA_CAP = 0.025


# Preserve global storage / mass behavior.
LAMBDA_MASS = 0.30


# =============================================================================
# CHECKPOINT SCORE
#
# Conservation must dominate checkpoint selection.
# =============================================================================

SCORE_WEIGHT_FV = 3.00

SCORE_WEIGHT_BALANCE = 1.00

SCORE_WEIGHT_DATA = 0.25

SCORE_WEIGHT_MASS = 0.25


# =============================================================================
# VALIDATION GUARDRAILS
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

        # Required by the final error-vs-time diagnostic.
        # This was missing in the original SG7B-6F script and caused:
        #
        #     KeyError: 'tD_test'
        #
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

        n_profiles = len(
            indices
        )

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

        # ---------------------------------------------------------------------
        # NEW IN V15-SG7B-6F-R
        #
        # Canonical physical activity scale used to normalize the coupled
        # residual difference:
        #
        #     A_SG7A =
        #         |dS/dtD|
        #         +
        #         |div(F_adv)|
        #         +
        #         |div(G_cap)|
        #         +
        #         1e-4
        #
        # This replaces the incorrect normalization by the nearly-zero
        # SG7A residual itself.
        # ---------------------------------------------------------------------

        target_activity = np.zeros_like(
            target_t
        )

        for p, index in enumerate(
            indices
        ):

            S = (
                master_S[
                    index
                ]
            )

            temporal = (
                temporal_derivative_np(
                    master_tD,
                    master_S,
                    index,
                )
            )

            (
                adv,
                cap,
            ) = (
                canonical_spatial_components_np(
                    S,
                    xi,
                )
            )

            residual = (
                temporal
                +
                adv
                -
                cap
            )

            activity = (
                np.abs(
                    temporal
                )
                +
                np.abs(
                    adv
                )
                +
                np.abs(
                    cap
                )
                +
                1.0e-4
            )

            target_t[p] = (
                temporal.astype(
                    np.float32
                )
            )

            target_adv[p] = (
                adv.astype(
                    np.float32
                )
            )

            target_cap[p] = (
                cap.astype(
                    np.float32
                )
            )

            target_residual[p] = (
                residual.astype(
                    np.float32
                )
            )

            target_activity[p] = (
                activity.astype(
                    np.float32
                )
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

        targets[
            f"activity_{split}"
        ] = target_activity

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

def activity_scaled_balance_loss(
    predicted_residual,
    target_residual,
    target_activity,
):
    """
    Activity-scaled coupled conservative loss.

    The original SG7B-6F normalized the residual mismatch by the
    SG7A residual magnitude itself. Because the frozen SG7A residual is
    intentionally very small, that created an excessively large effective
    optimization force.

    SG7B-6F-R instead normalizes by the canonical SG7A physical activity:

        |dS/dtD|
        +
        |div(F_adv)|
        +
        |div(G_cap)|
        +
        1e-4

    Therefore:

        L_balance =
            mean(
                [
                    (R_NN - R_SG7A)
                    /
                    A_SG7A
                ]^2
            )
    """

    normalized_error = (
        predicted_residual
        -
        target_residual
    ) / (
        target_activity
        +
        EPS
    )

    return tf.reduce_mean(
        tf.square(
            normalized_error
        )
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
    target_activity,
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
        # Data fidelity
        # ---------------------------------------------------------------------

        L_data = tf.reduce_mean(
            tf.square(
                Y_pred
                -
                Y
            )
        )

        # ---------------------------------------------------------------------
        # CORRECTED COUPLED CONSERVATIVE LOSS
        #
        # Use SG7A physical activity, not the near-zero SG7A residual,
        # as the normalization scale.
        # ---------------------------------------------------------------------

        L_balance = (
            activity_scaled_balance_loss(
                residual,
                target_residual,
                target_activity,
            )
        )

        # ---------------------------------------------------------------------
        # Direct normalized FV residual
        # ---------------------------------------------------------------------

        L_fv = tf.reduce_mean(
            tf.square(
                relative
            )
        )

        # ---------------------------------------------------------------------
        # Weak component regularizers
        #
        # These remain normalized by their own target magnitudes because
        # temporal, advective and capillary components have meaningful
        # nonzero physical scales.
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
        # Mass / storage
        # ---------------------------------------------------------------------

        L_mass = (
            mass_loss(
                Y,
                Y_pred,
                dxi,
            )
        )

        # ---------------------------------------------------------------------
        # Total SG7B-6F-R objective
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
    activity,
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

                activity.astype(
                    np.float32
                ),
            )
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

    # -------------------------------------------------------------------------
    # FV conservation is the dominant checkpoint criterion.
    #
    # Normalize against the final freeze target:
    #
    #     FV_MAE < TARGET_FV_RELATIVE_MAE
    #
    # so values below 1.0 are already within the desired range.
    # -------------------------------------------------------------------------

    fv_term = (
        metrics[
            "FV_MAE"
        ]
        /
        TARGET_FV_RELATIVE_MAE
    )

    # -------------------------------------------------------------------------
    # Coupled balance relative to the incoming SG7B-6D checkpoint.
    #
    # A value < 1.0 means the refinement improved the absolute coupled
    # balance relative to epoch zero.
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Saturation accuracy remains a guardrail.
    #
    # We do not want an apparently physics-improved checkpoint that destroys
    # the already excellent SG7B-6D saturation approximation.
    # -------------------------------------------------------------------------

    data_term = (
        metrics[
            "L1"
        ]
        /
        MAX_TEST_L1
    )

    # -------------------------------------------------------------------------
    # Mass / storage remains a guardrail.
    # -------------------------------------------------------------------------

    mass_term = (
        metrics[
            "mass_relative_MAE"
        ]
        /
        MAX_MASS_RELATIVE_MAE
    )

    # -------------------------------------------------------------------------
    # Final score
    #
    # FV conservation dominates.
    #
    # SG7B-6F showed that choosing a checkpoint using weaker conservation
    # emphasis can retain a model with excellent saturation accuracy but
    # unacceptable governing-equation consistency.
    # -------------------------------------------------------------------------

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

    # =========================================================================
    # TRAINING DATASET
    # =========================================================================

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

        targets[
            "activity_train"
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

    # =========================================================================
    # EPOCH ZERO — INCOMING SG7B-6D BASELINE
    #
    # This checkpoint must be preserved before any fine-tuning occurs.
    # =========================================================================

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

    baseline_score = checkpoint_score(
        baseline_val,
        baseline_val[
            "balance_MAE"
        ],
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "EPOCH-ZERO SG7B-6D BASELINE"
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
        f"Validation score          : "
        f"{baseline_score:.6e}"
    )

    print()

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

    print()

    print(
        "Epoch-zero checkpoint     : SAVED"
    )

    print(
        "=" * 78
    )

    # =========================================================================
    # PRESERVE EPOCH ZERO AS THE INITIAL BEST CHECKPOINT
    # =========================================================================

    best_score = (
        baseline_score
    )

    best_epoch = 0

    best_validation = (
        baseline_val.copy()
    )

    patience_counter = 0

    model.save_weights(
        BEST_WEIGHTS_FILE
    )

    # =========================================================================
    # HISTORY
    #
    # Epoch zero is included explicitly.
    # =========================================================================

    history = {
        "epoch": [
            0
        ],

        "learning_rate": [
            0.0
        ],

        "train_total": [
            np.nan
        ],

        "train_data": [
            np.nan
        ],

        "train_balance": [
            np.nan
        ],

        "train_FV": [
            np.nan
        ],

        "train_temporal": [
            np.nan
        ],

        "train_adv": [
            np.nan
        ],

        "train_cap": [
            np.nan
        ],

        "train_mass": [
            np.nan
        ],

        "val_L1": [
            baseline_val[
                "L1"
            ]
        ],

        "val_FV_MAE": [
            baseline_val[
                "FV_MAE"
            ]
        ],

        "val_balance_MAE": [
            baseline_val[
                "balance_MAE"
            ]
        ],

        "val_temporal_MAE": [
            baseline_val[
                "temporal_MAE"
            ]
        ],

        "val_adv_MAE": [
            baseline_val[
                "adv_MAE"
            ]
        ],

        "val_cap_MAE": [
            baseline_val[
                "cap_MAE"
            ]
        ],

        "val_mass_MAE": [
            baseline_val[
                "mass_relative_MAE"
            ]
        ],

        "val_score": [
            baseline_score
        ],
    }

    start_time = (
        time.perf_counter()
    )

    # =========================================================================
    # FINE-TUNING LOOP
    # =========================================================================

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

        train_rows = []

        for (
            X_batch,
            Y_batch,
            target_t,
            target_adv,
            target_cap,
            target_residual,
            target_activity,
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
                target_activity,

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

        # =====================================================================
        # FULL VALIDATION
        # =====================================================================

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

        # =====================================================================
        # HISTORY
        # =====================================================================

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

        # =====================================================================
        # GUARDRAILS
        # =====================================================================

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

        # =====================================================================
        # CHECKPOINT SELECTION
        #
        # The refined model must beat the incoming SG7B-6D score.
        # =====================================================================

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
                val.copy()
            )

            patience_counter = 0

            model.save_weights(
                BEST_WEIGHTS_FILE
            )

        else:

            patience_counter += 1

        # =====================================================================
        # LOGGING
        # =====================================================================

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

            marker = (
                "*"
                if (
                    epoch + 1
                    ==
                    best_epoch
                )
                else
                " "
            )

            print(
                f"{marker} Epoch "
                f"{epoch + 1:4d}/{EPOCHS} | "
                f"lr={lr:.2e} | "
                f"L1={val['L1']:.3e} | "
                f"FV={val['FV_MAE']:.3e} | "
                f"ratio={ratio:6.1f} | "
                f"bal={val['balance_MAE']:.3e} | "
                f"balImp={balance_improvement:7.2f}% | "
                f"t={val['temporal_MAE']:.3e} | "
                f"A={val['adv_MAE']:.3e} | "
                f"C={val['cap_MAE']:.3e} | "
                f"score={score:.3f}"
            )

        # =====================================================================
        # FINAL TARGET HIT
        # =====================================================================

        target_reached = (
            val[
                "FV_MAE"
            ]
            < TARGET_FV_RELATIVE_MAE

            and

            val[
                "balance_MAE"
            ]
            <
            baseline_val[
                "balance_MAE"
            ]

            and

            val[
                "L1"
            ]
            < MAX_TEST_L1

            and

            val[
                "mass_relative_MAE"
            ]
            < MAX_MASS_RELATIVE_MAE
        )

        if (
            target_reached
            and
            epoch >= 30
        ):

            print(
                "\nSG7B-6F-R coupled-conservative "
                "validation target reached."
            )

            break

        # =====================================================================
        # EARLY STOPPING
        # =====================================================================

        if (
            patience_counter
            >= PATIENCE
        ):

            print(
                "\nSG7B-6F-R early stopping:"
            )

            print(
                f"  Best epoch              : "
                f"{best_epoch}"
            )

            print(
                f"  Best validation score   : "
                f"{best_score:.6e}"
            )

            if (
                best_epoch
                == 0
            ):

                print(
                    "  Result                  : "
                    "No refinement beat SG7B-6D."
                )

            break

    runtime = (
        time.perf_counter()
        -
        start_time
    )

    # =========================================================================
    # SAVE TRAINING HISTORY
    # =========================================================================

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

    # =========================================================================
    # SAVE TERMINAL TRAINING STATE
    #
    # This is not necessarily the best checkpoint.
    # =========================================================================

    model.save(
        FINAL_MODEL_FILE
    )

    # =========================================================================
    # RESTORE TRUE BEST CHECKPOINT
    #
    # Because epoch zero was saved before training, this is guaranteed to be
    # at least as good as the incoming SG7B-6D checkpoint under the scoring
    # contract.
    # =========================================================================

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
        "V15-SG7B-6F-R VALIDATION"
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
        "PAD-Stream V15-SG7B-6F-R\n"
        "Coupled Conservative Refinement"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6FR_Training_History.png",
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
        "PAD-Stream V15-SG7B-6F-R\n"
        "Held-Out Coupled-Conservative Profiles"
    )

    ax.legend(
        fontsize=7,
        ncol=2,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6FR_Test_Profiles.png",
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
        "PAD-Stream V15-SG7B-6F-R\n"
        "Held-Out Saturation Error vs Time"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6FR_Error_vs_tD.png",
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
            "V15-SG7B-6F-R",

        "description":
            (
                "Activity-scaled coupled conservative refinement "
                "with epoch-zero checkpoint preservation"
            ),

        "source_model":
            "V15SG7B6D_Best_Model.keras",

        "architecture_changed":
            False,

        "canonical_truth":
            "SG7A master_saturation",

        "corrections_from_SG7B6F": {
            "activity_scaled_balance_loss":
                True,

            "epoch_zero_checkpoint_preserved":
                True,

            "lower_learning_rate":
                True,

            "tD_test_dataset_field_restored":
                True,
        },

        "canonical_physics": {
            "SG7A_truth_FV_relative_MAE":
                SG7A_TRUTH_FV_RELATIVE_MAE,

            "maximum_allowed_FV_ratio":
                MAX_FV_RATIO,

            "required_PI_RNN_FV_relative_MAE":
                TARGET_FV_RELATIVE_MAE,

            "balance_normalization":
                (
                    "|S_t_SG7A| + "
                    "|divF_SG7A| + "
                    "|divG_SG7A| + 1e-4"
                ),
        },

        "loss_design": {
            "lambda_data":
                LAMBDA_DATA,

            "lambda_balance":
                LAMBDA_BALANCE,

            "lambda_FV":
                LAMBDA_FV,

            "lambda_temporal":
                LAMBDA_TEMPORAL,

            "lambda_advective":
                LAMBDA_ADV,

            "lambda_capillary":
                LAMBDA_CAP,

            "lambda_mass":
                LAMBDA_MASS,
        },

        "checkpoint_score_weights": {
            "FV":
                SCORE_WEIGHT_FV,

            "balance":
                SCORE_WEIGHT_BALANCE,

            "data":
                SCORE_WEIGHT_DATA,

            "mass":
                SCORE_WEIGHT_MASS,
        },

        "learning_rate_schedule": {
            "stage_1":
                LR_STAGE_1,

            "stage_2":
                LR_STAGE_2,

            "stage_3":
                LR_STAGE_3,

            "stage_2_epoch":
                LR_STAGE_2_EPOCH,

            "stage_3_epoch":
                LR_STAGE_3_EPOCH,
        },

        "epoch_zero_validation": {
            "L1":
                training[
                    "baseline_val"
                ][
                    "L1"
                ],

            "L2":
                training[
                    "baseline_val"
                ][
                    "L2"
                ],

            "FV_MAE":
                training[
                    "baseline_val"
                ][
                    "FV_MAE"
                ],

            "balance_MAE":
                training[
                    "baseline_val"
                ][
                    "balance_MAE"
                ],

            "mass_relative_MAE":
                training[
                    "baseline_val"
                ][
                    "mass_relative_MAE"
                ],
        },

        "epoch_zero_test": {
            "L1":
                baseline[
                    "L1"
                ],

            "L2":
                baseline[
                    "L2"
                ],

            "Linf":
                baseline[
                    "Linf"
                ],

            "FV_MAE":
                baseline[
                    "FV_MAE"
                ],

            "balance_MAE":
                baseline[
                    "balance_MAE"
                ],

            "temporal_MAE":
                baseline[
                    "temporal_MAE"
                ],

            "advective_MAE":
                baseline[
                    "adv_MAE"
                ],

            "capillary_MAE":
                baseline[
                    "cap_MAE"
                ],

            "mass_relative_MAE":
                baseline[
                    "mass_relative_MAE"
                ],
        },

        "best_checkpoint": {
            "epoch":
                int(
                    training[
                        "best_epoch"
                    ]
                ),

            "validation_score":
                float(
                    training[
                        "best_score"
                    ]
                ),

            "epoch_zero_retained":
                bool(
                    training[
                        "best_epoch"
                    ]
                    == 0
                ),
        },

        "best_checkpoint_test": {
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

            "advective_MAE":
                result[
                    "adv_MAE"
                ],

            "capillary_MAE":
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
    }

    # =========================================================================
    # STATUS / NEXT MILESTONE
    # =========================================================================

    if passed:

        summary[
            "status"
        ] = (
            "PASS_CANDIDATE_FOR_FINAL_FREEZE"
        )

        summary[
            "next_milestone"
        ] = (
            "V15-SG7B-7R — Independent Final "
            "PI-RNN Freeze Validation"
        )

    elif (
        training[
            "best_epoch"
        ]
        == 0
    ):

        summary[
            "status"
        ] = (
            "SOURCE_CHECKPOINT_RETAINED"
        )

        summary[
            "next_milestone"
        ] = (
            "Review SG7B-6F-R trajectory before "
            "further PI-RNN refinement"
        )

    else:

        summary[
            "status"
        ] = (
            "CORRECTED_REFINEMENT_IMPROVED_SOURCE_"
            "BUT_TARGET_NOT_REACHED"
        )

        summary[
            "next_milestone"
        ] = (
            "Review SG7B-6F-R best checkpoint and "
            "remaining FV residual mechanism"
        )

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
        "PAD-Stream Version 15-SG7B-6F-R"
    )

    print(
        "Activity-Scaled Coupled Conservative Refinement"
    )

    print(
        "=" * 78
    )

    print(
        f"\nTensorFlow version       : "
        f"{tf.__version__}"
    )

    print(
        "\nCORRECTED COUPLED LOSS DESIGN"
    )

    print(
        "  Balance normalization   : "
        "SG7A physical activity"
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
        f"  Mass weight             : "
        f"{LAMBDA_MASS}"
    )

    print(
        f"  Initial learning rate   : "
        f"{LR_STAGE_1:.1e}"
    )

    print(
        "  Epoch-zero preservation : True"
    )

    print(
        f"  FV freeze target        : "
        f"< {TARGET_FV_RELATIVE_MAE:.6e}"
    )

    # =========================================================================
    # LOAD DATABASES
    # =========================================================================

    dataset = load_dataset()

    sg7a = load_sg7a()

    if not SOURCE_MODEL_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-6D model:\n"
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
        "  V15SG7B6D_Best_Model.keras"
    )

    print(
        "  Load                    : PASS"
    )

    print(
        f"  Parameters              : "
        f"{model.count_params():,}"
    )

    # =========================================================================
    # BUILD CANONICAL ACTIVITY-SCALED TARGETS
    # =========================================================================

    print(
        "\nBUILDING CANONICAL ACTIVITY-SCALED TARGETS..."
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

    print(
        f"  Train activity          : "
        f"{targets['activity_train'].shape}"
    )

    print(
        f"  Validation activity     : "
        f"{targets['activity_val'].shape}"
    )

    print(
        f"  Test activity           : "
        f"{targets['activity_test'].shape}"
    )

    # =========================================================================
    # TARGET SANITY CHECK
    # =========================================================================

    for split in [
        "train",
        "val",
        "test",
    ]:

        activity = (
            targets[
                f"activity_{split}"
            ]
        )

        if not np.all(
            np.isfinite(
                activity
            )
        ):

            raise RuntimeError(
                f"Non-finite SG7A activity "
                f"target detected in {split} split."
            )

        if np.any(
            activity
            <= 0.0
        ):

            raise RuntimeError(
                f"Non-positive SG7A activity "
                f"target detected in {split} split."
            )

    print(
        "\nTARGET SANITY CHECK"
    )

    print(
        "  All activity values finite  : PASS"
    )

    print(
        "  All activity values positive: PASS"
    )

    print(
        f"  Activity min             : "
        f"{np.min(targets['activity_train']):.6e}"
    )

    print(
        f"  Activity mean            : "
        f"{np.mean(targets['activity_train']):.6e}"
    )

    print(
        f"  Activity max             : "
        f"{np.max(targets['activity_train']):.6e}"
    )

    # =========================================================================
    # FINE-TUNE
    # =========================================================================

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

    if (
        training[
            "best_epoch"
        ]
        == 0
    ):

        print(
            "  Best checkpoint         : "
            "incoming SG7B-6D source"
        )

    else:

        print(
            "  Best checkpoint         : "
            "SG7B-6F-R refined state"
        )

    # =========================================================================
    # LOAD THE ACTUAL BEST CHECKPOINT
    # =========================================================================

    if not BEST_MODEL_FILE.exists():

        raise FileNotFoundError(
            "Best SG7B-6F-R model was not saved:\n"
            f"{BEST_MODEL_FILE}"
        )

    best_model = (
        tf.keras.models.load_model(
            BEST_MODEL_FILE
        )
    )

    print(
        "\nBEST CHECKPOINT"
    )

    print(
        f"  {BEST_MODEL_FILE.name}"
    )

    print(
        "  Model load              : PASS"
    )

    # =========================================================================
    # HELD-OUT TEST
    # =========================================================================

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
        "\nBEST-CHECKPOINT HELD-OUT TEST"
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

    # =========================================================================
    # VALIDATION
    # =========================================================================

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

    # =========================================================================
    # SAVE DIAGNOSTICS
    # =========================================================================

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

    # =========================================================================
    # OUTPUT SUMMARY
    # =========================================================================

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
        "  V15SG7B6FR_Best_Model.keras"
    )

    print(
        "  V15SG7B6FR_Final_Model.keras"
    )

    print(
        "  V15SG7B6FR_Best.weights.h5"
    )

    print(
        "\nTraining:"
    )

    print(
        "  V15SG7B6FR_Training_History.npz"
    )

    print(
        "\nNumerical:"
    )

    print(
        "  V15SG7B6FR_Test_Results.npz"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B6FR_Summary.json"
    )

    # =========================================================================
    # FINAL MILESTONE DECISION
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    if passed:

        print(
            "V15-SG7B-6F-R VALIDATION: PASS"
        )

        print()

        print(
            "STATUS: FINAL FREEZE CANDIDATE"
        )

        print()

        print(
            "The activity-scaled coupled conservative "
            "refinement satisfied the current SG7B freeze gates."
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7B-7R — Independent Final "
            "PI-RNN Freeze Validation"
        )

    elif (
        training[
            "best_epoch"
        ]
        == 0
    ):

        print(
            "V15-SG7B-6F-R VALIDATION: "
            "TARGET NOT REACHED"
        )

        print()

        print(
            "STATUS: SG7B-6D SOURCE CHECKPOINT RETAINED"
        )

        print()

        print(
            "No SG7B-6F-R fine-tuned checkpoint "
            "outperformed epoch-zero SG7B-6D under "
            "the corrected checkpoint contract."
        )

        print()

        print(
            "The original source model remains the "
            "authoritative checkpoint from this branch."
        )

    else:

        print(
            "V15-SG7B-6F-R VALIDATION: "
            "TARGET NOT REACHED"
        )

        print()

        print(
            "STATUS: CORRECTED REFINEMENT IMPROVED SOURCE "
            "BUT DID NOT REACH FINAL FV TARGET"
        )

        print()

        print(
            "The best SG7B-6F-R checkpoint improved the "
            "incoming SG7B-6D checkpoint under the corrected "
            "score, but further diagnosis is required before "
            "any additional training."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()