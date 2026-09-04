from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7B-6E
# Coupled Residual Balance Audit
#
# PURPOSE
# -------
# Compare:
#
#   SG7B-6B
#       best physics-balanced PI-RNN
#
#   SG7B-6D
#       strongly advective-supervised PI-RNN
#
#
# NO TRAINING.
#
#
# Governing conservative residual:
#
#       R = S_t + div(F_adv) - div(G_cap)
#
#
# Relative to canonical SG7A truth:
#
#       Delta_t = S_t_NN - S_t_SG7A
#
#       Delta_A = div(F_adv_NN) - div(F_adv_SG7A)
#
#       Delta_C = div(G_cap_NN) - div(G_cap_SG7A)
#
#
# Therefore:
#
#       Delta_R =
#           Delta_t
#           + Delta_A
#           - Delta_C
#
#
# CENTRAL QUESTION
# ----------------
# SG7B-6D substantially improved:
#
#       saturation
#       face flux
#       advective divergence
#
# but made the complete FV residual worse.
#
# This milestone determines whether SG7B-6B benefited from signed
# cancellation among imperfect PDE components, and whether SG7B-6D
# destroyed that balance.
#
#
# CANONICAL TRUTH
# ---------------
# SG7A master_saturation directly.
#
# Canonical residual contract established in V15-SG7B-6C-R.
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


MODEL_6B_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6B"
    / "V15SG7B6B_Best_Model.keras"
)


MODEL_6D_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6D"
    / "V15SG7B6D_Best_Model.keras"
)


OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B6E"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B6E_Summary.json"
)


PROFILE_CSV = (
    OUTPUT_DIR
    / "V15SG7B6E_Profile_Balance_Metrics.csv"
)


REGIONAL_CSV = (
    OUTPUT_DIR
    / "V15SG7B6E_Regional_Balance_Metrics.csv"
)


RESULTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B6E_Coupled_Balance_Audit.npz"
)


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


EPS = 1.0e-12

BATCH_SIZE = 32

SEQUENCE_LENGTH = 201


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
                f"Missing dataset field: {key}"
            )

    return {
        key: data[key]
        for key in required
    }


def load_sg7a():

    if not SG7A_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7A master database:\n"
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
                f"Missing SG7A field: {key}"
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
# CANONICAL SPATIAL OPERATOR
# =============================================================================

def spatial_components_np(
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

    # -------------------------------------------------------------------------
    # Advective flux
    # -------------------------------------------------------------------------

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

    fw = fractional_flow_np(
        S
    )

    F = np.zeros(
        n + 1,
        dtype=np.float64,
    )

    # injector
    F[0] = (
        u_face[0]
        * fractional_flow_np(
            np.array(
                [S_INJECTED],
                dtype=np.float64,
            )
        )[0]
    )

    # internal
    F[1:n] = (
        u_face[1:n]
        * fw[:-1]
    )

    # outlet
    F[n] = (
        u_face[n]
        * fw[-1]
    )

    div_adv = (
        F[1:]
        -
        F[:-1]
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
                [S_INJECTED],
                dtype=np.float64,
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
        -
        G[:-1]
    ) / dxi

    return {
        "div_adv":
            div_adv,

        "div_cap":
            div_cap,

        "F":
            F,

        "G":
            G,
    }


# =============================================================================
# SG7A TEMPORAL DERIVATIVE
# =============================================================================

def sg7a_temporal_derivative(
    master_tD,
    master_S,
    index,
):

    index = int(index)

    if index == 0:

        dt = (
            master_tD[1]
            -
            master_tD[0]
        )

        return (
            master_S[1]
            -
            master_S[0]
        ) / dt

    if index == (
        len(master_tD)
        - 1
    ):

        dt = (
            master_tD[-1]
            -
            master_tD[-2]
        )

        return (
            master_S[-1]
            -
            master_S[-2]
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
# MODEL INPUT AT ARBITRARY TIME
# =============================================================================

def make_model_input(
    xi,
    tD_values,
    tD_scale,
):

    tD_values = np.asarray(
        tD_values,
        dtype=np.float64,
    )

    X = np.zeros(
        (
            len(tD_values),
            len(xi),
            2,
        ),
        dtype=np.float32,
    )

    X[
        :,
        :,
        0
    ] = np.asarray(
        xi,
        dtype=np.float32,
    )[
        None,
        :
    ]

    X[
        :,
        :,
        1
    ] = (
        tD_values
        / tD_scale
    )[
        :,
        None
    ]

    return X


# =============================================================================
# PI-RNN TEMPORAL DERIVATIVE
# =============================================================================

def pirnn_temporal_derivative(
    model,
    xi,
    tD_values,
    tD_scale,
):

    dt_reference = (
        tD_scale
        / 800.0
    )

    t_minus = np.maximum(
        tD_values
        - dt_reference,
        0.0,
    )

    t_plus = np.minimum(
        tD_values
        + dt_reference,
        tD_scale,
    )

    X_minus = make_model_input(
        xi,
        t_minus,
        tD_scale,
    )

    X_plus = make_model_input(
        xi,
        t_plus,
        tD_scale,
    )

    S_minus = (
        model.predict(
            X_minus,
            batch_size=BATCH_SIZE,
            verbose=0,
        )[
            :,
            :,
            0
        ]
    )

    S_plus = (
        model.predict(
            X_plus,
            batch_size=BATCH_SIZE,
            verbose=0,
        )[
            :,
            :,
            0
        ]
    )

    dt = (
        t_plus
        -
        t_minus
    )

    return (
        S_plus
        -
        S_minus
    ) / dt[
        :,
        None
    ]


# =============================================================================
# CANONICAL SG7A COMPONENT DATABASE
# =============================================================================

def build_truth_components(
    dataset,
    sg7a,
):

    xi = np.asarray(
        sg7a[
            "xi"
        ],
        dtype=np.float64,
    )

    indices = np.asarray(
        dataset[
            "index_test"
        ],
        dtype=int,
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

    n_profiles = len(indices)

    truth_S = np.zeros(
        (
            n_profiles,
            len(xi),
        ),
        dtype=np.float64,
    )

    truth_dt = np.zeros_like(
        truth_S
    )

    truth_adv = np.zeros_like(
        truth_S
    )

    truth_cap = np.zeros_like(
        truth_S
    )

    for p, index in enumerate(
        indices
    ):

        S = (
            master_S[
                index
            ]
        )

        truth_S[p] = S

        truth_dt[p] = (
            sg7a_temporal_derivative(
                master_tD,
                master_S,
                index,
            )
        )

        spatial = (
            spatial_components_np(
                S,
                xi,
            )
        )

        truth_adv[p] = (
            spatial[
                "div_adv"
            ]
        )

        truth_cap[p] = (
            spatial[
                "div_cap"
            ]
        )

    truth_residual = (
        truth_dt
        +
        truth_adv
        -
        truth_cap
    )

    truth_scale = (
        np.abs(
            truth_dt
        )
        +
        np.abs(
            truth_adv
        )
        +
        np.abs(
            truth_cap
        )
        +
        1.0e-4
    )

    truth_relative = (
        truth_residual
        /
        truth_scale
    )

    return {
        "S":
            truth_S,

        "dt":
            truth_dt,

        "adv":
            truth_adv,

        "cap":
            truth_cap,

        "residual":
            truth_residual,

        "relative":
            truth_relative,
    }


# =============================================================================
# MODEL COMPONENT DATABASE
# =============================================================================

def build_model_components(
    model,
    dataset,
    truth,
):

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=np.float64,
    )

    tD = np.asarray(
        dataset[
            "tD_test"
        ],
        dtype=np.float64,
    )

    tD_scale = float(
        dataset[
            "tD_scale"
        ][0]
    )

    prediction = (
        model.predict(
            dataset[
                "X_test"
            ].astype(
                np.float32
            ),
            batch_size=BATCH_SIZE,
            verbose=0,
        )[
            :,
            :,
            0
        ]
    )

    model_dt = (
        pirnn_temporal_derivative(
            model,
            xi,
            tD,
            tD_scale,
        )
    )

    model_adv = np.zeros_like(
        prediction,
        dtype=np.float64,
    )

    model_cap = np.zeros_like(
        prediction,
        dtype=np.float64,
    )

    for p in range(
        len(tD)
    ):

        spatial = (
            spatial_components_np(
                prediction[p],
                xi,
            )
        )

        model_adv[p] = (
            spatial[
                "div_adv"
            ]
        )

        model_cap[p] = (
            spatial[
                "div_cap"
            ]
        )

    model_residual = (
        model_dt
        +
        model_adv
        -
        model_cap
    )

    model_scale = (
        np.abs(
            model_dt
        )
        +
        np.abs(
            model_adv
        )
        +
        np.abs(
            model_cap
        )
        +
        1.0e-4
    )

    model_relative = (
        model_residual
        /
        model_scale
    )

    delta_t = (
        model_dt
        -
        truth[
            "dt"
        ]
    )

    delta_adv = (
        model_adv
        -
        truth[
            "adv"
        ]
    )

    delta_cap = (
        model_cap
        -
        truth[
            "cap"
        ]
    )

    delta_balance = (
        delta_t
        +
        delta_adv
        -
        delta_cap
    )

    return {
        "prediction":
            prediction,

        "dt":
            model_dt,

        "adv":
            model_adv,

        "cap":
            model_cap,

        "residual":
            model_residual,

        "relative":
            model_relative,

        "delta_t":
            delta_t,

        "delta_adv":
            delta_adv,

        "delta_cap":
            delta_cap,

        "delta_balance":
            delta_balance,
    }


# =============================================================================
# METRICS
# =============================================================================

def mae(x):

    return float(
        np.mean(
            np.abs(
                x
            )
        )
    )


def rms(x):

    return float(
        np.sqrt(
            np.mean(
                np.asarray(
                    x
                ) ** 2
            )
        )
    )


def safe_corr(
    a,
    b,
):

    a = np.asarray(
        a
    ).ravel()

    b = np.asarray(
        b
    ).ravel()

    if (
        np.std(a)
        < 1.0e-14
        or
        np.std(b)
        < 1.0e-14
    ):

        return 0.0

    return float(
        np.corrcoef(
            a,
            b,
        )[0, 1]
    )


# =============================================================================
# CANCELLATION METRICS
# =============================================================================

def cancellation_metrics(
    model_result,
):
    """
    Let:

        a = Delta_t
        b = Delta_adv
        c = -Delta_cap

    Then:

        Delta_R = a + b + c

    Define cancellation index:

        CI =
            1
            -
            |a+b+c|
            /
            (|a|+|b|+|c|)

    CI -> 1:
        strong cancellation

    CI -> 0:
        little cancellation
    """

    a = (
        model_result[
            "delta_t"
        ]
    )

    b = (
        model_result[
            "delta_adv"
        ]
    )

    c = (
        -model_result[
            "delta_cap"
        ]
    )

    numerator = np.abs(
        a
        +
        b
        +
        c
    )

    denominator = (
        np.abs(a)
        +
        np.abs(b)
        +
        np.abs(c)
        +
        EPS
    )

    cancellation_index = (
        1.0
        -
        numerator
        / denominator
    )

    cancellation_index = np.clip(
        cancellation_index,
        0.0,
        1.0,
    )

    return {
        "mean_cancellation_index":
            float(
                np.mean(
                    cancellation_index
                )
            ),

        "median_cancellation_index":
            float(
                np.median(
                    cancellation_index
                )
            ),

        "corr_t_adv":
            safe_corr(
                a,
                b,
            ),

        "corr_t_minuscap":
            safe_corr(
                a,
                c,
            ),

        "corr_adv_minuscap":
            safe_corr(
                b,
                c,
            ),

        "corr_t_plus_adv_minuscap":
            safe_corr(
                a + b,
                c,
            ),

        "cancellation_index":
            cancellation_index,
    }


# =============================================================================
# GLOBAL MODEL SUMMARY
# =============================================================================

def summarize_model(
    name,
    model_result,
    truth,
):

    saturation_error = (
        model_result[
            "prediction"
        ]
        -
        truth[
            "S"
        ]
    )

    cancellation = (
        cancellation_metrics(
            model_result
        )
    )

    return {
        "name":
            name,

        "saturation_L1":
            mae(
                saturation_error
            ),

        "saturation_L2":
            rms(
                saturation_error
            ),

        "temporal_difference_MAE":
            mae(
                model_result[
                    "delta_t"
                ]
            ),

        "advective_difference_MAE":
            mae(
                model_result[
                    "delta_adv"
                ]
            ),

        "capillary_difference_MAE":
            mae(
                model_result[
                    "delta_cap"
                ]
            ),

        "balance_difference_MAE":
            mae(
                model_result[
                    "delta_balance"
                ]
            ),

        "absolute_residual_MAE":
            mae(
                model_result[
                    "residual"
                ]
            ),

        "relative_residual_MAE":
            mae(
                model_result[
                    "relative"
                ]
            ),

        "relative_residual_RMS":
            rms(
                model_result[
                    "relative"
                ]
            ),

        "mean_cancellation_index":
            cancellation[
                "mean_cancellation_index"
            ],

        "median_cancellation_index":
            cancellation[
                "median_cancellation_index"
            ],

        "corr_t_adv":
            cancellation[
                "corr_t_adv"
            ],

        "corr_t_minuscap":
            cancellation[
                "corr_t_minuscap"
            ],

        "corr_adv_minuscap":
            cancellation[
                "corr_adv_minuscap"
            ],

        "corr_t_plus_adv_minuscap":
            cancellation[
                "corr_t_plus_adv_minuscap"
            ],
    }


# =============================================================================
# REGIONS
# =============================================================================

def build_region_masks(
    truth_S,
    xi,
):

    n_profiles, n_nodes = (
        truth_S.shape
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
                truth_S[p],
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
# REGIONAL METRICS
# =============================================================================

def regional_metrics(
    model_name,
    model_result,
    masks,
):

    rows = []

    for region, mask in (
        masks.items()
    ):

        a = (
            model_result[
                "delta_t"
            ][
                mask
            ]
        )

        b = (
            model_result[
                "delta_adv"
            ][
                mask
            ]
        )

        c = (
            -model_result[
                "delta_cap"
            ][
                mask
            ]
        )

        balance = (
            a
            +
            b
            +
            c
        )

        denominator = (
            np.abs(a)
            +
            np.abs(b)
            +
            np.abs(c)
            +
            EPS
        )

        cancellation = (
            1.0
            -
            np.abs(
                balance
            )
            /
            denominator
        )

        cancellation = np.clip(
            cancellation,
            0.0,
            1.0,
        )

        rows.append({
            "model":
                model_name,

            "region":
                region,

            "temporal_difference_MAE":
                mae(a),

            "advective_difference_MAE":
                mae(b),

            "capillary_difference_MAE":
                mae(-c),

            "balance_difference_MAE":
                mae(balance),

            "relative_residual_MAE":
                mae(
                    model_result[
                        "relative"
                    ][
                        mask
                    ]
                ),

            "mean_cancellation_index":
                float(
                    np.mean(
                        cancellation
                    )
                ),

            "corr_t_adv":
                safe_corr(
                    a,
                    b,
                ),

            "corr_t_minuscap":
                safe_corr(
                    a,
                    c,
                ),

            "corr_adv_minuscap":
                safe_corr(
                    b,
                    c,
                ),
        })

    return rows


# =============================================================================
# TIME-BAND METRICS
# =============================================================================

def time_band_metrics(
    model_result,
    tD,
):

    q1 = np.quantile(
        tD,
        1.0 / 3.0,
    )

    q2 = np.quantile(
        tD,
        2.0 / 3.0,
    )

    masks = {
        "early":
            tD <= q1,

        "middle":
            (
                (tD > q1)
                &
                (tD < q2)
            ),

        "late":
            tD >= q2,
    }

    output = {}

    for name, mask in (
        masks.items()
    ):

        a = (
            model_result[
                "delta_t"
            ][
                mask
            ]
        )

        b = (
            model_result[
                "delta_adv"
            ][
                mask
            ]
        )

        c = (
            -model_result[
                "delta_cap"
            ][
                mask
            ]
        )

        denominator = (
            np.abs(a)
            +
            np.abs(b)
            +
            np.abs(c)
            +
            EPS
        )

        cancellation = (
            1.0
            -
            np.abs(
                a + b + c
            )
            /
            denominator
        )

        output[name] = {
            "temporal_difference_MAE":
                mae(a),

            "advective_difference_MAE":
                mae(b),

            "capillary_difference_MAE":
                mae(-c),

            "balance_difference_MAE":
                mae(
                    a + b + c
                ),

            "relative_residual_MAE":
                mae(
                    model_result[
                        "relative"
                    ][
                        mask
                    ]
                ),

            "mean_cancellation_index":
                float(
                    np.mean(
                        np.clip(
                            cancellation,
                            0.0,
                            1.0,
                        )
                    )
                ),
        }

    return output


# =============================================================================
# PROFILE-BY-PROFILE METRICS
# =============================================================================

def profile_metrics(
    dataset,
    result_6b,
    result_6d,
):

    rows = []

    tD = np.asarray(
        dataset[
            "tD_test"
        ]
    )

    for p in range(
        len(tD)
    ):

        row = {
            "profile":
                p,

            "tD":
                float(
                    tD[p]
                ),
        }

        for label, result in [
            (
                "SG7B6B",
                result_6b,
            ),
            (
                "SG7B6D",
                result_6d,
            ),
        ]:

            a = (
                result[
                    "delta_t"
                ][p]
            )

            b = (
                result[
                    "delta_adv"
                ][p]
            )

            c = (
                -result[
                    "delta_cap"
                ][p]
            )

            balance = (
                a
                +
                b
                +
                c
            )

            cancellation = (
                1.0
                -
                np.abs(
                    balance
                )
                /
                (
                    np.abs(a)
                    +
                    np.abs(b)
                    +
                    np.abs(c)
                    +
                    EPS
                )
            )

            row[
                f"{label}_temporal_MAE"
            ] = mae(a)

            row[
                f"{label}_advective_MAE"
            ] = mae(b)

            row[
                f"{label}_capillary_MAE"
            ] = mae(-c)

            row[
                f"{label}_balance_MAE"
            ] = mae(balance)

            row[
                f"{label}_relative_FV_MAE"
            ] = mae(
                result[
                    "relative"
                ][p]
            )

            row[
                f"{label}_cancellation_index"
            ] = float(
                np.mean(
                    np.clip(
                        cancellation,
                        0.0,
                        1.0,
                    )
                )
            )

        rows.append(
            row
        )

    return rows


# =============================================================================
# DIAGNOSIS
# =============================================================================

def determine_diagnosis(
    summary_6b,
    summary_6d,
):

    fv_worsened = (
        summary_6d[
            "relative_residual_MAE"
        ]
        >
        summary_6b[
            "relative_residual_MAE"
        ]
    )

    adv_improved = (
        summary_6d[
            "advective_difference_MAE"
        ]
        <
        summary_6b[
            "advective_difference_MAE"
        ]
    )

    cancellation_decreased = (
        summary_6d[
            "mean_cancellation_index"
        ]
        <
        summary_6b[
            "mean_cancellation_index"
        ]
    )

    temporal_worsened = (
        summary_6d[
            "temporal_difference_MAE"
        ]
        >
        summary_6b[
            "temporal_difference_MAE"
        ]
    )

    capillary_worsened = (
        summary_6d[
            "capillary_difference_MAE"
        ]
        >
        summary_6b[
            "capillary_difference_MAE"
        ]
    )

    if (
        fv_worsened
        and
        adv_improved
        and
        cancellation_decreased
    ):

        diagnosis = (
            "LOSS_OF_COUPLED_ERROR_CANCELLATION"
        )

        recommendation = (
            "SG7B-6D improved the targeted advective component but "
            "reduced the signed cancellation among temporal, advective, "
            "and capillary errors. The next training milestone should "
            "optimize coupled residual balance rather than individual "
            "advective terms."
        )

    elif (
        fv_worsened
        and
        adv_improved
        and
        temporal_worsened
    ):

        diagnosis = (
            "ADVECTIVE_TEMPORAL_TRADEOFF"
        )

        recommendation = (
            "Advective refinement shifted the solution into a poorer "
            "temporal-consistency regime. The next milestone should "
            "jointly constrain accumulation and advective divergence."
        )

    elif (
        fv_worsened
        and
        adv_improved
        and
        capillary_worsened
    ):

        diagnosis = (
            "ADVECTIVE_CAPILLARY_TRADEOFF"
        )

        recommendation = (
            "Advective improvement degraded the capillary balance. "
            "The next training objective should preserve the coupled "
            "advection-capillarity balance."
        )

    else:

        diagnosis = (
            "MIXED_COUPLED_BALANCE_CHANGE"
        )

        recommendation = (
            "The SG7B-6B to SG7B-6D transition altered several PDE "
            "components simultaneously. The next refinement should "
            "use the full signed balance error rather than independently "
            "weighted component losses."
        )

    return {
        "diagnosis":
            diagnosis,

        "fv_worsened":
            bool(
                fv_worsened
            ),

        "advective_improved":
            bool(
                adv_improved
            ),

        "cancellation_decreased":
            bool(
                cancellation_decreased
            ),

        "temporal_worsened":
            bool(
                temporal_worsened
            ),

        "capillary_worsened":
            bool(
                capillary_worsened
            ),

        "recommendation":
            recommendation,
    }


# =============================================================================
# SAVE CSV
# =============================================================================

def save_csv(
    path,
    rows,
):

    with open(
        path,
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
# PLOTS
# =============================================================================

def plot_component_comparison(
    summary_6b,
    summary_6d,
):

    names = [
        "Temporal",
        "Advective",
        "Capillary",
        "Balance",
    ]

    values_6b = [
        summary_6b[
            "temporal_difference_MAE"
        ],
        summary_6b[
            "advective_difference_MAE"
        ],
        summary_6b[
            "capillary_difference_MAE"
        ],
        summary_6b[
            "balance_difference_MAE"
        ],
    ]

    values_6d = [
        summary_6d[
            "temporal_difference_MAE"
        ],
        summary_6d[
            "advective_difference_MAE"
        ],
        summary_6d[
            "capillary_difference_MAE"
        ],
        summary_6d[
            "balance_difference_MAE"
        ],
    ]

    x = np.arange(
        len(names)
    )

    width = 0.35

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.bar(
        x - width / 2,
        values_6b,
        width,
        label="SG7B-6B",
    )

    ax.bar(
        x + width / 2,
        values_6d,
        width,
        label="SG7B-6D",
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        names
    )

    ax.set_ylabel(
        "MAE relative to SG7A component"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6E\n"
        "Coupled PDE Component Comparison"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6E_Component_Comparison.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_cancellation_comparison(
    summary_6b,
    summary_6d,
):

    names = [
        "Mean cancellation",
        "Median cancellation",
    ]

    values_6b = [
        summary_6b[
            "mean_cancellation_index"
        ],
        summary_6b[
            "median_cancellation_index"
        ],
    ]

    values_6d = [
        summary_6d[
            "mean_cancellation_index"
        ],
        summary_6d[
            "median_cancellation_index"
        ],
    ]

    x = np.arange(
        len(names)
    )

    width = 0.35

    fig, ax = plt.subplots(
        figsize=(
            8,
            6,
        )
    )

    ax.bar(
        x - width / 2,
        values_6b,
        width,
        label="SG7B-6B",
    )

    ax.bar(
        x + width / 2,
        values_6d,
        width,
        label="SG7B-6D",
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        names
    )

    ax.set_ylim(
        0.0,
        1.0,
    )

    ax.set_ylabel(
        "Cancellation index"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6E\n"
        "Signed PDE Error Cancellation"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6E_Cancellation_Comparison.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_signed_scatter(
    result,
    label,
):

    a = (
        result[
            "delta_t"
        ].ravel()
    )

    b = (
        result[
            "delta_adv"
        ].ravel()
    )

    c = (
        -result[
            "delta_cap"
        ].ravel()
    )

    # downsample only for plotting
    n = len(a)

    if n > 10000:

        indices = np.linspace(
            0,
            n - 1,
            10000,
            dtype=int,
        )

        a = a[
            indices
        ]

        b = b[
            indices
        ]

        c = c[
            indices
        ]

    fig, ax = plt.subplots(
        figsize=(
            8,
            6,
        )
    )

    ax.scatter(
        b,
        a + c,
        s=8,
        alpha=0.35,
    )

    ax.set_xlabel(
        r"$\Delta_A$"
    )

    ax.set_ylabel(
        r"$\Delta_t-\Delta_C$"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6E\n"
        f"{label}: Advective vs Remaining Signed Error"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / f"V15SG7B6E_{label}_Signed_Balance.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_balance_maps(
    dataset,
    result_6b,
    result_6d,
):

    xi = dataset[
        "xi"
    ]

    tD = dataset[
        "tD_test"
    ]

    for label, result in [
        (
            "SG7B6B",
            result_6b,
        ),
        (
            "SG7B6D",
            result_6d,
        ),
    ]:

        fig, ax = plt.subplots(
            figsize=(
                10,
                6,
            )
        )

        im = ax.imshow(
            np.abs(
                result[
                    "delta_balance"
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
            r"$|\Delta_t+\Delta_A-\Delta_C|$"
        )

        ax.set_xlabel(
            r"$\xi$"
        )

        ax.set_ylabel(
            r"$t_D$"
        )

        ax.set_title(
            "PAD-Stream V15-SG7B-6E\n"
            f"{label} Coupled Balance Error"
        )

        fig.tight_layout()

        fig.savefig(
            OUTPUT_DIR
            / f"V15SG7B6E_{label}_Balance_Error_Map.png",
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
    truth,
    result_6b,
    result_6d,
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

        truth_S=
            truth[
                "S"
            ],

        truth_dt=
            truth[
                "dt"
            ],

        truth_adv=
            truth[
                "adv"
            ],

        truth_cap=
            truth[
                "cap"
            ],

        sg7b6b_prediction=
            result_6b[
                "prediction"
            ],

        sg7b6b_delta_t=
            result_6b[
                "delta_t"
            ],

        sg7b6b_delta_adv=
            result_6b[
                "delta_adv"
            ],

        sg7b6b_delta_cap=
            result_6b[
                "delta_cap"
            ],

        sg7b6b_delta_balance=
            result_6b[
                "delta_balance"
            ],

        sg7b6b_relative_FV=
            result_6b[
                "relative"
            ],

        sg7b6d_prediction=
            result_6d[
                "prediction"
            ],

        sg7b6d_delta_t=
            result_6d[
                "delta_t"
            ],

        sg7b6d_delta_adv=
            result_6d[
                "delta_adv"
            ],

        sg7b6d_delta_cap=
            result_6d[
                "delta_cap"
            ],

        sg7b6d_delta_balance=
            result_6d[
                "delta_balance"
            ],

        sg7b6d_relative_FV=
            result_6d[
                "relative"
            ],
    )


# =============================================================================
# SUMMARY
# =============================================================================

def save_summary(
    truth,
    summary_6b,
    summary_6d,
    regional_rows,
    time_6b,
    time_6d,
    diagnosis,
):

    truth_fv = mae(
        truth[
            "relative"
        ]
    )

    summary = {
        "milestone":
            "V15-SG7B-6E",

        "description":
            (
                "Coupled signed residual-balance audit comparing "
                "SG7B-6B and SG7B-6D"
            ),

        "training_performed":
            False,

        "canonical_truth_source":
            "SG7A master_saturation",

        "SG7A_truth_FV_relative_MAE":
            truth_fv,

        "SG7B6B":
            summary_6b,

        "SG7B6D":
            summary_6d,

        "regional_metrics":
            regional_rows,

        "time_band_SG7B6B":
            time_6b,

        "time_band_SG7B6D":
            time_6d,

        "diagnosis":
            diagnosis,

        "status":
            "COUPLED_BALANCE_AUDIT_COMPLETE",

        "recommended_next_milestone":
            (
                "V15-SG7B-6F — Coupled Conservative "
                "Component Refinement"
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
        "PAD-Stream Version 15-SG7B-6E"
    )

    print(
        "Coupled Residual Balance Audit"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    # -------------------------------------------------------------------------
    # Load data
    # -------------------------------------------------------------------------

    dataset = load_dataset()

    sg7a = load_sg7a()

    if not MODEL_6B_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-6B model:\n"
            f"{MODEL_6B_FILE}"
        )

    if not MODEL_6D_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-6D model:\n"
            f"{MODEL_6D_FILE}"
        )

    model_6b = tf.keras.models.load_model(
        MODEL_6B_FILE
    )

    model_6d = tf.keras.models.load_model(
        MODEL_6D_FILE
    )

    print(
        "\nMODELS"
    )

    print(
        "  SG7B-6B load            : PASS"
    )

    print(
        "  SG7B-6D load            : PASS"
    )

    print(
        f"  Test profiles           : "
        f"{len(dataset['X_test'])}"
    )

    # -------------------------------------------------------------------------
    # Canonical truth components
    # -------------------------------------------------------------------------

    print(
        "\nBuilding canonical SG7A component database..."
    )

    truth = build_truth_components(
        dataset,
        sg7a,
    )

    print(
        f"  SG7A relative FV MAE    : "
        f"{mae(truth['relative']):.6e}"
    )

    # -------------------------------------------------------------------------
    # Build model components
    # -------------------------------------------------------------------------

    print(
        "\nEvaluating SG7B-6B..."
    )

    result_6b = (
        build_model_components(
            model_6b,
            dataset,
            truth,
        )
    )

    print(
        "Evaluating SG7B-6D..."
    )

    result_6d = (
        build_model_components(
            model_6d,
            dataset,
            truth,
        )
    )

    # -------------------------------------------------------------------------
    # Summaries
    # -------------------------------------------------------------------------

    summary_6b = summarize_model(
        "SG7B-6B",
        result_6b,
        truth,
    )

    summary_6d = summarize_model(
        "SG7B-6D",
        result_6d,
        truth,
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "GLOBAL COUPLED-BALANCE COMPARISON"
    )

    print(
        "=" * 78
    )

    for label, summary in [
        (
            "SG7B-6B",
            summary_6b,
        ),
        (
            "SG7B-6D",
            summary_6d,
        ),
    ]:

        print(
            f"\n{label}"
        )

        print(
            f"  Saturation L1           : "
            f"{summary['saturation_L1']:.6e}"
        )

        print(
            f"  Temporal difference MAE : "
            f"{summary['temporal_difference_MAE']:.6e}"
        )

        print(
            f"  Advective difference MAE: "
            f"{summary['advective_difference_MAE']:.6e}"
        )

        print(
            f"  Capillary difference MAE: "
            f"{summary['capillary_difference_MAE']:.6e}"
        )

        print(
            f"  Coupled balance MAE     : "
            f"{summary['balance_difference_MAE']:.6e}"
        )

        print(
            f"  Relative FV MAE         : "
            f"{summary['relative_residual_MAE']:.6e}"
        )

        print(
            f"  Mean cancellation index : "
            f"{summary['mean_cancellation_index']:.6f}"
        )

        print(
            f"  corr(Delta_t,Delta_A)   : "
            f"{summary['corr_t_adv']:.6f}"
        )

        print(
            f"  corr(Delta_A,-Delta_C)  : "
            f"{summary['corr_adv_minuscap']:.6f}"
        )

        print(
            f"  corr(Delta_t,-Delta_C)  : "
            f"{summary['corr_t_minuscap']:.6f}"
        )

    # -------------------------------------------------------------------------
    # Regions
    # -------------------------------------------------------------------------

    masks = build_region_masks(
        truth[
            "S"
        ],
        dataset[
            "xi"
        ],
    )

    regional_6b = regional_metrics(
        "SG7B-6B",
        result_6b,
        masks,
    )

    regional_6d = regional_metrics(
        "SG7B-6D",
        result_6d,
        masks,
    )

    regional_rows = (
        regional_6b
        +
        regional_6d
    )

    # -------------------------------------------------------------------------
    # Time bands
    # -------------------------------------------------------------------------

    time_6b = time_band_metrics(
        result_6b,
        dataset[
            "tD_test"
        ],
    )

    time_6d = time_band_metrics(
        result_6d,
        dataset[
            "tD_test"
        ],
    )

    # -------------------------------------------------------------------------
    # Diagnosis
    # -------------------------------------------------------------------------

    diagnosis = determine_diagnosis(
        summary_6b,
        summary_6d,
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-6E DIAGNOSIS"
    )

    print(
        "=" * 78
    )

    print(
        f"Diagnosis:"
    )

    print(
        f"  {diagnosis['diagnosis']}"
    )

    print(
        "\nDiagnostic flags:"
    )

    print(
        f"  FV worsened             : "
        f"{diagnosis['fv_worsened']}"
    )

    print(
        f"  Advective improved      : "
        f"{diagnosis['advective_improved']}"
    )

    print(
        f"  Cancellation decreased  : "
        f"{diagnosis['cancellation_decreased']}"
    )

    print(
        f"  Temporal worsened       : "
        f"{diagnosis['temporal_worsened']}"
    )

    print(
        f"  Capillary worsened      : "
        f"{diagnosis['capillary_worsened']}"
    )

    print(
        "\nRecommendation:"
    )

    print(
        f"  {diagnosis['recommendation']}"
    )

    print(
        "=" * 78
    )

    # -------------------------------------------------------------------------
    # Save tables
    # -------------------------------------------------------------------------

    profile_rows = profile_metrics(
        dataset,
        result_6b,
        result_6d,
    )

    save_csv(
        PROFILE_CSV,
        profile_rows,
    )

    save_csv(
        REGIONAL_CSV,
        regional_rows,
    )

    # -------------------------------------------------------------------------
    # Plots
    # -------------------------------------------------------------------------

    plot_component_comparison(
        summary_6b,
        summary_6d,
    )

    plot_cancellation_comparison(
        summary_6b,
        summary_6d,
    )

    plot_signed_scatter(
        result_6b,
        "SG7B6B",
    )

    plot_signed_scatter(
        result_6d,
        "SG7B6D",
    )

    plot_balance_maps(
        dataset,
        result_6b,
        result_6d,
    )

    # -------------------------------------------------------------------------
    # Save database / summary
    # -------------------------------------------------------------------------

    save_results(
        dataset,
        truth,
        result_6b,
        result_6d,
    )

    save_summary(
        truth,
        summary_6b,
        summary_6d,
        regional_rows,
        time_6b,
        time_6d,
        diagnosis,
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
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B6E_Component_Comparison.png"
    )

    print(
        "  V15SG7B6E_Cancellation_Comparison.png"
    )

    print(
        "  V15SG7B6E_SG7B6B_Signed_Balance.png"
    )

    print(
        "  V15SG7B6E_SG7B6D_Signed_Balance.png"
    )

    print(
        "  V15SG7B6E_SG7B6B_Balance_Error_Map.png"
    )

    print(
        "  V15SG7B6E_SG7B6D_Balance_Error_Map.png"
    )

    print(
        "\nTables:"
    )

    print(
        "  V15SG7B6E_Profile_Balance_Metrics.csv"
    )

    print(
        "  V15SG7B6E_Regional_Balance_Metrics.csv"
    )

    print(
        "\nNumerical database:"
    )

    print(
        "  V15SG7B6E_Coupled_Balance_Audit.npz"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B6E_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-6E COMPLETED"
    )

    print()

    print(
        "STATUS: COUPLED RESIDUAL BALANCE AUDITED"
    )

    print()

    print(
        "Next milestone:"
    )

    print(
        "V15-SG7B-6F — Coupled Conservative "
        "Component Refinement"
    )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()