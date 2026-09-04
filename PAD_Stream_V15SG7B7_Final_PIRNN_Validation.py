from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7B-7
# Final PI-RNN Validation / Freeze Decision
#
# PURPOSE
# -------
# Perform the final independent validation of the reference-case full-physics
# PI-RNN trained in V15-SG7B-6.
#
#
# NO TRAINING IS PERFORMED.
#
#
# FINAL QUESTIONS
# ---------------
#
# 1. Does the SG7B-6 PI-RNN reproduce held-out SG7A saturation profiles?
#
# 2. Does it satisfy the conservative finite-volume physics well enough?
#
# 3. Does it preserve global saturation storage / mass?
#
# 4. Are errors localized at:
#       - injector
#       - high-gradient/front
#       - smooth interior
#       - outlet
#
# 5. Are errors concentrated at early, middle, or late dimensionless time?
#
# 6. How far is the PI-RNN residual from the residual of the SG7A truth itself?
#
# 7. Did SG7B-6 materially improve over the SG7B-4 reference model?
#
#
# If all freeze gates pass:
#
#       V15-SG7B REFERENCE FULL-PHYSICS PI-RNN = FROZEN
#
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent


# -----------------------------------------------------------------------------
# Dataset
# -----------------------------------------------------------------------------

DATASET_FILE = (
    ROOT
    / "output"
    / "V15_SG7B3"
    / "SG7B3_REFERENCE_DATASET.npz"
)


# -----------------------------------------------------------------------------
# Frozen SG7A master truth
# -----------------------------------------------------------------------------

SG7A_FILE = (
    ROOT
    / "output"
    / "V15_SG7A"
    / "FULL_PHYSICS_STREAMLINE_SATURATION.npz"
)


# -----------------------------------------------------------------------------
# SG7B-6 candidate model
# -----------------------------------------------------------------------------

SG7B6_MODEL_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6"
    / "V15SG7B6_Best_Model.keras"
)


# -----------------------------------------------------------------------------
# SG7B-4 baseline
# -----------------------------------------------------------------------------

SG7B4_RESULTS_FILE = (
    ROOT
    / "output"
    / "V15_SG7B4"
    / "V15SG7B4_Test_Results.npz"
)


# -----------------------------------------------------------------------------
# Output
# -----------------------------------------------------------------------------

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B7"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B7_Summary.json"
)

METRICS_CSV = (
    OUTPUT_DIR
    / "V15SG7B7_Profile_Metrics.csv"
)

RESULTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B7_Final_Validation.npz"
)


# =============================================================================
# FROZEN PHYSICS
# =============================================================================

SWC = 0.20
SOR = 0.20

S_INITIAL = SWC
S_INJECTED = (
    1.0
    - SOR
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

BATCH_SIZE = 32


# =============================================================================
# FREEZE GATES
# =============================================================================

MAX_TEST_L1 = 0.020

MAX_TEST_L2 = 0.030

MAX_FV_RELATIVE_MAE = 0.100

MAX_MASS_RELATIVE_MAE = 0.030

MAX_INJECTOR_L1 = 0.015

MAX_FRONT_L1 = 0.030

MAX_EARLY_TIME_L1 = 0.020

MAX_PI_TO_TRUTH_FV_RATIO = 50.0


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
        "X_test",
        "Y_test",
        "tD_test",
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
# NUMPY PHYSICS FOR SG7A TRUTH RESIDUAL
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
                dtype=float,
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
            + 1.0e-12
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
                dtype=float,
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


def godunov_fractional_flux_np(
    S_left,
    S_right,
    n_sample=100,
):

    if abs(
        S_left
        - S_right
    ) < 1.0e-12:

        return float(
            fractional_flow_np(
                np.array(
                    [S_left]
                )
            )[0]
        )

    samples = np.linspace(
        min(
            S_left,
            S_right,
        ),
        max(
            S_left,
            S_right,
        ),
        n_sample,
    )

    values = fractional_flow_np(
        samples
    )

    if S_left <= S_right:

        return float(
            np.min(
                values
            )
        )

    return float(
        np.max(
            values
        )
    )


def truth_fv_residual_snapshot(
    S,
    S_t,
    xi,
):

    n = len(
        S
    )

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

    F = np.zeros(
        n + 1,
        dtype=float,
    )

    # inlet
    F[0] = (
        u_face[0]
        * godunov_fractional_flux_np(
            S_INJECTED,
            S[0],
        )
    )

    # internal
    for face in range(
        1,
        n,
    ):

        F[face] = (
            u_face[face]
            * godunov_fractional_flux_np(
                S[
                    face - 1
                ],
                S[
                    face
                ],
            )
        )

    # outlet
    F[n] = (
        u_face[n]
        * fractional_flow_np(
            np.array(
                [S[-1]]
            )
        )[0]
    )

    div_adv = (
        F[1:]
        - F[:-1]
    ) / dxi

    # -------------------------------------------------------------------------
    # CAPILLARY FLUX
    # -------------------------------------------------------------------------

    D_cell = diffusion_shape_np(
        S
    )

    G = np.zeros(
        n + 1,
        dtype=float,
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
            + D_cell[0]
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
        / (
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
                D_cell[
                    face - 1
                ]
                +
                D_cell[
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

    residual = (
        S_t
        +
        div_adv
        -
        div_cap
    )

    scale = (
        np.abs(
            S_t
        )
        +
        np.abs(
            div_adv
        )
        +
        np.abs(
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
    )


# =============================================================================
# TENSORFLOW PHYSICS FOR PI-RNN
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


def pirnn_fv_residual(
    model,
    X,
    tD_scale,
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
            training=False,
        )[
            :,
            :,
            0
        ]
    )

    S_plus = (
        model(
            X_plus,
            training=False,
        )[
            :,
            :,
            0
        ]
    )

    S = (
        model(
            X,
            training=False,
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

    batch_size = (
        tf.shape(
            S
        )[0]
    )

    face_xi = tf.linspace(
        0.0,
        1.0,
        202,
    )

    u_face = tf.exp(
        NC
        * face_xi
    )

    fw = fractional_flow_tf(
        S
    )

    f_injected = fractional_flow_tf(
        tf.constant(
            S_INJECTED,
            dtype=tf.float32,
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

    F = tf.concat(
        [
            F_left,
            F_internal,
            F_outlet,
        ],
        axis=1,
    )

    div_adv = (
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

    D_injected = diffusion_shape_tf(
        tf.constant(
            S_INJECTED,
            dtype=tf.float32,
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

    G = tf.concat(
        [
            G_left,
            G_internal,
            G_right,
        ],
        axis=1,
    )

    div_cap = (
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
    )


# =============================================================================
# REGION MASKS
# =============================================================================

def build_region_masks(
    truth,
    xi,
):

    n_profiles, n_nodes = (
        truth.shape
    )

    injector = np.zeros(
        (
            n_profiles,
            n_nodes,
        ),
        dtype=bool,
    )

    outlet = np.zeros_like(
        injector
    )

    front = np.zeros_like(
        injector
    )

    n_boundary = max(
        3,
        int(
            0.05
            * n_nodes
        ),
    )

    injector[
        :,
        :n_boundary
    ] = True

    outlet[
        :,
        -n_boundary:
    ] = True

    for p in range(
        n_profiles
    ):

        gradient = np.abs(
            np.gradient(
                truth[p],
                xi,
                edge_order=2,
            )
        )

        threshold = np.quantile(
            gradient,
            0.90,
        )

        front[p] = (
            gradient
            >= threshold
        )

    interior = ~(
        injector
        |
        outlet
        |
        front
    )

    return {
        "injector":
            injector,

        "front":
            front,

        "interior":
            interior,

        "outlet":
            outlet,
    }


# =============================================================================
# SG7A TRUTH RESIDUAL ON TEST TIMES
# =============================================================================

def evaluate_truth_residual(
    sg7a,
    test_indices,
):

    xi = np.asarray(
        sg7a[
            "xi"
        ],
        dtype=float,
    )

    tD = np.asarray(
        sg7a[
            "master_tD"
        ],
        dtype=float,
    )

    S_all = np.asarray(
        sg7a[
            "master_saturation"
        ],
        dtype=float,
    )

    residuals = []

    relatives = []

    for idx in test_indices:

        idx = int(
            idx
        )

        S = (
            S_all[
                idx
            ]
        )

        if idx == 0:

            dt = (
                tD[1]
                - tD[0]
            )

            S_t = (
                S_all[1]
                - S_all[0]
            ) / dt

        elif idx == len(
            tD
        ) - 1:

            dt = (
                tD[-1]
                - tD[-2]
            )

            S_t = (
                S_all[-1]
                - S_all[-2]
            ) / dt

        else:

            dt = (
                tD[
                    idx + 1
                ]
                -
                tD[
                    idx - 1
                ]
            )

            S_t = (
                S_all[
                    idx + 1
                ]
                -
                S_all[
                    idx - 1
                ]
            ) / dt

        residual, relative = (
            truth_fv_residual_snapshot(
                S,
                S_t,
                xi,
            )
        )

        residuals.append(
            residual
        )

        relatives.append(
            relative
        )

    residuals = np.asarray(
        residuals
    )

    relatives = np.asarray(
        relatives
    )

    return {
        "residual":
            residuals,

        "relative":
            relatives,

        "relative_MAE":
            float(
                np.mean(
                    np.abs(
                        relatives
                    )
                )
            ),

        "relative_RMS":
            float(
                np.sqrt(
                    np.mean(
                        relatives ** 2
                    )
                )
            ),
    }


# =============================================================================
# MODEL EVALUATION
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

    truth = (
        dataset[
            "Y_test"
        ][
            :,
            :,
            0
        ]
    )

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

    error = (
        prediction
        - truth
    )

    abs_error = np.abs(
        error
    )

    profile_L1 = np.mean(
        abs_error,
        axis=1,
    )

    profile_L2 = np.sqrt(
        np.mean(
            error ** 2,
            axis=1,
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

    masks = build_region_masks(
        truth,
        xi,
    )

    regional = {}

    for name, mask in (
        masks.items()
    ):

        region_error = (
            error[
                mask
            ]
        )

        regional[name] = {
            "L1":
                float(
                    np.mean(
                        np.abs(
                            region_error
                        )
                    )
                ),

            "L2":
                float(
                    np.sqrt(
                        np.mean(
                            region_error ** 2
                        )
                    )
                ),

            "Linf":
                float(
                    np.max(
                        np.abs(
                            region_error
                        )
                    )
                ),
        }

    # -------------------------------------------------------------------------
    # Time bands
    # -------------------------------------------------------------------------

    q1 = np.quantile(
        tD,
        1.0 / 3.0,
    )

    q2 = np.quantile(
        tD,
        2.0 / 3.0,
    )

    early = (
        tD
        <= q1
    )

    middle = (
        (
            tD
            > q1
        )
        &
        (
            tD
            < q2
        )
    )

    late = (
        tD
        >= q2
    )

    time_bands = {}

    for name, mask in [
        (
            "early",
            early,
        ),
        (
            "middle",
            middle,
        ),
        (
            "late",
            late,
        ),
    ]:

        e = (
            error[
                mask
            ]
        )

        time_bands[name] = {
            "L1":
                float(
                    np.mean(
                        np.abs(
                            e
                        )
                    )
                ),

            "L2":
                float(
                    np.sqrt(
                        np.mean(
                            e ** 2
                        )
                    )
                ),
        }

    # -------------------------------------------------------------------------
    # FV residual
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

    residual_tf, relative_tf = (
        pirnn_fv_residual(
            model,
            X_tf,
            tD_scale,
        )
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

    # -------------------------------------------------------------------------
    # Regional FV
    # -------------------------------------------------------------------------

    regional_fv = {}

    for name, mask in (
        masks.items()
    ):

        values = (
            relative[
                mask
            ]
        )

        regional_fv[name] = {
            "MAE":
                float(
                    np.mean(
                        np.abs(
                            values
                        )
                    )
                ),

            "RMS":
                float(
                    np.sqrt(
                        np.mean(
                            values ** 2
                        )
                    )
                ),
        }

    # -------------------------------------------------------------------------
    # Mass / storage
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
    # Max pointwise error
    # -------------------------------------------------------------------------

    flat_idx = int(
        np.argmax(
            abs_error
        )
    )

    p_idx, x_idx = (
        np.unravel_index(
            flat_idx,
            abs_error.shape,
        )
    )

    max_error_location = {
        "tD":
            float(
                tD[
                    p_idx
                ]
            ),

        "xi":
            float(
                xi[
                    x_idx
                ]
            ),

        "truth":
            float(
                truth[
                    p_idx,
                    x_idx
                ]
            ),

        "prediction":
            float(
                prediction[
                    p_idx,
                    x_idx
                ]
            ),
    }

    return {
        "truth":
            truth,

        "prediction":
            prediction,

        "error":
            error,

        "profile_L1":
            profile_L1,

        "profile_L2":
            profile_L2,

        "relative_FV":
            relative,

        "L1":
            L1,

        "L2":
            L2,

        "Linf":
            Linf,

        "regional":
            regional,

        "regional_fv":
            regional_fv,

        "time_bands":
            time_bands,

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

        "max_error_location":
            max_error_location,
    }


# =============================================================================
# SG7B-4 BASELINE
# =============================================================================

def load_sg7b4_baseline():

    if not SG7B4_RESULTS_FILE.exists():

        return None

    data = np.load(
        SG7B4_RESULTS_FILE
    )

    required = [
        "truth",
        "prediction",
    ]

    for key in required:

        if key not in data:

            return None

    truth = (
        data[
            "truth"
        ]
    )

    pred = (
        data[
            "prediction"
        ]
    )

    error = (
        pred
        - truth
    )

    return {
        "L1":
            float(
                np.mean(
                    np.abs(
                        error
                    )
                )
            ),

        "L2":
            float(
                np.sqrt(
                    np.mean(
                        error ** 2
                    )
                )
            ),
    }


# =============================================================================
# PROFILE CSV
# =============================================================================

def save_profile_csv(
    dataset,
    result,
):

    tD = (
        dataset[
            "tD_test"
        ]
    )

    rows = []

    for i in range(
        len(tD)
    ):

        rows.append({
            "test_profile":
                i,

            "tD":
                float(
                    tD[i]
                ),

            "L1":
                float(
                    result[
                        "profile_L1"
                    ][i]
                ),

            "L2":
                float(
                    result[
                        "profile_L2"
                    ][i]
                ),
        })

    with open(
        METRICS_CSV,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# =============================================================================
# FINAL FREEZE GATES
# =============================================================================

def freeze_decision(
    result,
    truth_residual,
):

    truth_fv = (
        truth_residual[
            "relative_MAE"
        ]
    )

    pirnn_fv = (
        result[
            "fv_relative_MAE"
        ]
    )

    fv_ratio = (
        pirnn_fv
        /
        max(
            truth_fv,
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
            "Held-out L2 < 0.030",
            result[
                "L2"
            ]
            < MAX_TEST_L2,
        ),

        (
            "FV relative MAE < 0.10",
            result[
                "fv_relative_MAE"
            ]
            < MAX_FV_RELATIVE_MAE,
        ),

        (
            "Mass relative MAE < 0.03",
            result[
                "mass_relative_MAE"
            ]
            < MAX_MASS_RELATIVE_MAE,
        ),

        (
            "Injector-region L1 < 0.015",
            result[
                "regional"
            ][
                "injector"
            ][
                "L1"
            ]
            < MAX_INJECTOR_L1,
        ),

        (
            "High-gradient/front L1 < 0.030",
            result[
                "regional"
            ][
                "front"
            ][
                "L1"
            ]
            < MAX_FRONT_L1,
        ),

        (
            "Early-time L1 < 0.020",
            result[
                "time_bands"
            ][
                "early"
            ][
                "L1"
            ]
            < MAX_EARLY_TIME_L1,
        ),

        (
            "PI-RNN/SG7A FV residual ratio < 50",
            fv_ratio
            < MAX_PI_TO_TRUTH_FV_RATIO,
        ),
    ]

    all_passed = all(
        passed
        for _, passed
        in checks
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-7 FINAL FREEZE GATES"
    )

    print(
        "=" * 78
    )

    for description, passed in checks:

        print(
            f"[{'PASS' if passed else 'FAIL':4s}] "
            f"{description}"
        )

    print(
        "=" * 78
    )

    print(
        f"SG7A truth FV relative MAE : "
        f"{truth_fv:.6e}"
    )

    print(
        f"PI-RNN FV relative MAE     : "
        f"{pirnn_fv:.6e}"
    )

    print(
        f"PI-RNN / truth FV ratio    : "
        f"{fv_ratio:.3f}"
    )

    return (
        all_passed,
        checks,
        float(
            fv_ratio
        ),
    )


# =============================================================================
# PLOTS
# =============================================================================

def plot_profiles(
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
                "PI-RNN "
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
        "PAD-Stream V15-SG7B-7\n"
        "Final Held-Out SG7A vs PI-RNN Profiles"
    )

    ax.legend(
        fontsize=7,
        ncol=2,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B7_Final_Profiles.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_error_map(
    dataset,
    result,
):

    xi = dataset[
        "xi"
    ]

    tD = dataset[
        "tD_test"
    ]

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    im = ax.imshow(
        np.abs(
            result[
                "error"
            ]
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
        "|S_PI-RNN - S_SG7A|"
    )

    ax.set_xlabel(
        r"$\xi$"
    )

    ax.set_ylabel(
        r"$t_D$"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-7\n"
        "Final Held-Out Saturation Error"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B7_Error_Map.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_fv_maps(
    dataset,
    result,
    truth_residual,
):

    xi = dataset[
        "xi"
    ]

    tD = dataset[
        "tD_test"
    ]

    # SG7A truth
    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    im = ax.imshow(
        np.abs(
            truth_residual[
                "relative"
            ]
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
        "|Relative FV residual|"
    )

    ax.set_xlabel(
        r"$\xi$"
    )

    ax.set_ylabel(
        r"$t_D$"
    )

    ax.set_title(
        "V15-SG7B-7 — SG7A Truth FV Residual"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B7_SG7A_FV_Residual_Map.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    # PI-RNN
    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    im = ax.imshow(
        np.abs(
            result[
                "relative_FV"
            ]
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
        "|Relative FV residual|"
    )

    ax.set_xlabel(
        r"$\xi$"
    )

    ax.set_ylabel(
        r"$t_D$"
    )

    ax.set_title(
        "V15-SG7B-7 — PI-RNN FV Residual"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B7_PIRNN_FV_Residual_Map.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_regional_error(
    result,
):

    names = [
        "injector",
        "front",
        "interior",
        "outlet",
    ]

    values = [
        result[
            "regional"
        ][
            name
        ][
            "L1"
        ]
        for name in names
    ]

    fig, ax = plt.subplots(
        figsize=(
            8,
            6,
        )
    )

    ax.bar(
        names,
        values,
    )

    ax.set_ylabel(
        "Regional L1 saturation error"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-7\n"
        "Final Spatial Error Localization"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B7_Regional_Error.png",
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
        label="Global L1 freeze target",
    )

    ax.set_xlabel(
        r"$t_D$"
    )

    ax.set_ylabel(
        "Profile L1 error"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-7\n"
        "Final PI-RNN Error vs Dimensionless Time"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B7_Error_vs_tD.png",
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
    truth_residual,
):

    np.savez_compressed(
        RESULTS_FILE,

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

        saturation_error=
            result[
                "error"
            ],

        profile_L1=
            result[
                "profile_L1"
            ],

        pirnn_relative_FV=
            result[
                "relative_FV"
            ],

        sg7a_relative_FV=
            truth_residual[
                "relative"
            ],
    )


# =============================================================================
# SUMMARY
# =============================================================================

def save_summary(
    result,
    truth_residual,
    baseline,
    freeze_passed,
    fv_ratio,
):

    if baseline is None:

        baseline_section = {
            "available":
                False,
        }

    else:

        baseline_section = {
            "available":
                True,

            "SG7B4_L1":
                baseline[
                    "L1"
                ],

            "SG7B4_L2":
                baseline[
                    "L2"
                ],

            "SG7B6_L1":
                result[
                    "L1"
                ],

            "SG7B6_L2":
                result[
                    "L2"
                ],

            "L1_improvement_percent":
                float(
                    100.0
                    * (
                        baseline[
                            "L1"
                        ]
                        -
                        result[
                            "L1"
                        ]
                    )
                    /
                    baseline[
                        "L1"
                    ]
                ),
        }

    summary = {
        "milestone":
            "V15-SG7B-7",

        "description":
            (
                "Final validation and freeze decision "
                "for the reference full-physics PI-RNN"
            ),

        "training_performed":
            False,

        "model":
            "V15SG7B6_Best_Model.keras",

        "reference_case": {
            "Nc":
                NC,

            "Pe_c":
                PE_C,

            "lambda_bc":
                LAMBDA_BC,

            "phi":
                POROSITY,
        },

        "held_out_test": {
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

            "regional_error":
                result[
                    "regional"
                ],

            "regional_fv":
                result[
                    "regional_fv"
                ],

            "time_bands":
                result[
                    "time_bands"
                ],

            "maximum_error_location":
                result[
                    "max_error_location"
                ],
        },

        "SG7A_truth_residual": {
            "relative_MAE":
                truth_residual[
                    "relative_MAE"
                ],

            "relative_RMS":
                truth_residual[
                    "relative_RMS"
                ],
        },

        "PI_RNN_to_truth_FV_ratio":
            fv_ratio,

        "SG7B4_comparison":
            baseline_section,

        "freeze_passed":
            bool(
                freeze_passed
            ),

        "status":
            (
                "FROZEN_REFERENCE_PIRNN"
                if freeze_passed
                else
                "NOT_FROZEN"
            ),

        "next_milestone":
            (
                "V15-SG7B-8 - apply frozen PI-RNN "
                "to all SGSim streamlines"
                if freeze_passed
                else
                "V15-SG7B-6B - targeted refinement"
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
        "PAD-Stream Version 15-SG7B-7"
    )

    print(
        "Final PI-RNN Validation / Freeze Decision"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    # -------------------------------------------------------------------------
    # LOAD
    # -------------------------------------------------------------------------

    dataset = load_dataset()

    sg7a = load_sg7a()

    if not SG7B6_MODEL_FILE.exists():

        raise FileNotFoundError(
            "SG7B-6 best model missing:\n"
            f"{SG7B6_MODEL_FILE}"
        )

    print(
        "\nFINAL CANDIDATE"
    )

    print(
        "  V15SG7B6_Best_Model.keras"
    )

    print(
        f"  Test profiles           : "
        f"{len(dataset['X_test'])}"
    )

    print(
        f"  Sequence nodes          : "
        f"{len(dataset['xi'])}"
    )

    # -------------------------------------------------------------------------
    # MODEL
    # -------------------------------------------------------------------------

    model = tf.keras.models.load_model(
        SG7B6_MODEL_FILE
    )

    print(
        "  Model load              : PASS"
    )

    # -------------------------------------------------------------------------
    # PI-RNN
    # -------------------------------------------------------------------------

    result = evaluate_model(
        model,
        dataset,
    )

    print(
        "\nFINAL HELD-OUT PI-RNN RESULTS"
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
        f"  Maximum mass error      : "
        f"{result['mass_relative_max']:.6e}"
    )

    print(
        "\nREGIONAL SATURATION ERROR"
    )

    for name in [
        "injector",
        "front",
        "interior",
        "outlet",
    ]:

        print(
            f"  {name:10s} L1          : "
            f"{result['regional'][name]['L1']:.6e}"
        )

    print(
        "\nTIME-BAND SATURATION ERROR"
    )

    for name in [
        "early",
        "middle",
        "late",
    ]:

        print(
            f"  {name:10s} L1          : "
            f"{result['time_bands'][name]['L1']:.6e}"
        )

    # -------------------------------------------------------------------------
    # SG7A TRUTH FV RESIDUAL
    # -------------------------------------------------------------------------

    truth_residual = (
        evaluate_truth_residual(
            sg7a,
            dataset[
                "index_test"
            ],
        )
    )

    print(
        "\nSG7A TRUTH PHYSICS ON SAME TEST TIMES"
    )

    print(
        f"  FV relative MAE         : "
        f"{truth_residual['relative_MAE']:.6e}"
    )

    print(
        f"  FV relative RMS         : "
        f"{truth_residual['relative_RMS']:.6e}"
    )

    # -------------------------------------------------------------------------
    # SG7B4 BASELINE
    # -------------------------------------------------------------------------

    baseline = (
        load_sg7b4_baseline()
    )

    if baseline is not None:

        print(
            "\nSG7B-4 BASELINE COMPARISON"
        )

        print(
            f"  SG7B-4 L1               : "
            f"{baseline['L1']:.6e}"
        )

        print(
            f"  SG7B-6 L1               : "
            f"{result['L1']:.6e}"
        )

        improvement = (
            100.0
            * (
                baseline[
                    "L1"
                ]
                -
                result[
                    "L1"
                ]
            )
            /
            baseline[
                "L1"
            ]
        )

        print(
            f"  L1 improvement          : "
            f"{improvement:.2f}%"
        )

    # -------------------------------------------------------------------------
    # FREEZE
    # -------------------------------------------------------------------------

    (
        freeze_passed,
        _,
        fv_ratio,
    ) = freeze_decision(
        result,
        truth_residual,
    )

    # -------------------------------------------------------------------------
    # SAVE
    # -------------------------------------------------------------------------

    save_profile_csv(
        dataset,
        result,
    )

    save_results(
        dataset,
        result,
        truth_residual,
    )

    plot_profiles(
        dataset,
        result,
    )

    plot_error_map(
        dataset,
        result,
    )

    plot_fv_maps(
        dataset,
        result,
        truth_residual,
    )

    plot_regional_error(
        result,
    )

    plot_error_vs_time(
        dataset,
        result,
    )

    save_summary(
        result,
        truth_residual,
        baseline,
        freeze_passed,
        fv_ratio,
    )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print(
        "\nOUTPUTS"
    )

    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B7_Final_Profiles.png"
    )

    print(
        "  V15SG7B7_Error_Map.png"
    )

    print(
        "  V15SG7B7_SG7A_FV_Residual_Map.png"
    )

    print(
        "  V15SG7B7_PIRNN_FV_Residual_Map.png"
    )

    print(
        "  V15SG7B7_Regional_Error.png"
    )

    print(
        "  V15SG7B7_Error_vs_tD.png"
    )

    print(
        "\nNumerical:"
    )

    print(
        "  V15SG7B7_Profile_Metrics.csv"
    )

    print(
        "  V15SG7B7_Final_Validation.npz"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B7_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    if freeze_passed:

        print(
            "V15-SG7B-7 VALIDATION: PASS"
        )

        print()

        print(
            "V15-SG7B REFERENCE "
            "FULL-PHYSICS PI-RNN: FROZEN"
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7B-8 — Apply Frozen PI-RNN "
            "Across All SGSim Streamlines"
        )

    else:

        print(
            "V15-SG7B-7 VALIDATION: FAIL"
        )

        print()

        print(
            "V15-SG7B PI-RNN NOT FROZEN"
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7B-6B — Targeted "
            "Training Refinement"
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()