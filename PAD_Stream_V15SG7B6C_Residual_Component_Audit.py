from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7B-6C
# Conservative Residual Component Audit
#
# PURPOSE
# -------
# Explain the remaining conservative FV residual floor in the fine-tuned
# SG7B-6B PI-RNN.
#
#
# NO TRAINING IS PERFORMED.
#
#
# Governing residual:
#
#       R =
#           dS/dtD
#           +
#           div(F_adv)
#           -
#           div(G_cap)
#
#
# This milestone compares SG7A truth and SG7B-6B for:
#
#       1. temporal term
#               dS/dtD
#
#       2. advective term
#               div(F_adv)
#
#       3. capillary term
#               div(G_cap)
#
#       4. complete FV residual
#
#
# ADDITIONAL AUDITS
# -----------------
#
# A. Regional:
#       injector
#       high-gradient/front
#       interior
#       outlet
#
# B. Time:
#       early
#       middle
#       late
#
# C. Time-difference sensitivity:
#
#       dt multiplier = 0.5, 1, 2, 4
#
# D. Residual normalization:
#       identify contribution from low-activity regions.
#
#
# SOURCE MODEL
# ------------
#       V15SG7B6B_Best_Model.keras
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


MODEL_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6B"
    / "V15SG7B6B_Best_Model.keras"
)


OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B6C"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B6C_Summary.json"
)


PROFILE_METRICS_CSV = (
    OUTPUT_DIR
    / "V15SG7B6C_Profile_Component_Metrics.csv"
)


DT_SENSITIVITY_CSV = (
    OUTPUT_DIR
    / "V15SG7B6C_TimeDerivative_Sensitivity.csv"
)


RESULTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B6C_Component_Audit.npz"
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

SEQUENCE_LENGTH = 201

BATCH_SIZE = 32


# =============================================================================
# SG7B-7 REFERENCE VALUES
# =============================================================================

SG7A_REFERENCE_FV_RELATIVE_MAE = (
    6.323248e-04
)

SG7B6B_REFERENCE_FV_RELATIVE_MAE = (
    4.084900e-02
)

FREEZE_RATIO_TARGET = 50.0

FREEZE_ABSOLUTE_FV_TARGET = (
    SG7A_REFERENCE_FV_RELATIVE_MAE
    * FREEZE_RATIO_TARGET
)


# =============================================================================
# TIME-DIFFERENCE AUDIT
# =============================================================================

DT_MULTIPLIERS = [
    0.5,
    1.0,
    2.0,
    4.0,
]


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
            "Missing frozen SG7A solution:\n"
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
# NUMPY ROCK / FLUID FUNCTIONS
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


# =============================================================================
# GODUNOV FLUX
# =============================================================================

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


# =============================================================================
# SPATIAL FV COMPONENTS
# =============================================================================

def spatial_components_np(
    S,
    xi,
):
    """
    Return:

        div_adv
        div_cap
        F_adv
        G_cap
    """

    S = np.asarray(
        S,
        dtype=float,
    )

    n = len(
        S
    )

    dxi = float(
        xi[1]
        - xi[0]
    )

    # -------------------------------------------------------------------------
    # ADVECTIVE FACE FLUX
    # -------------------------------------------------------------------------

    face_xi = np.linspace(
        0.0,
        1.0,
        n + 1,
    )

    u_face = np.exp(
        NC
        * face_xi
    )

    F_adv = np.zeros(
        n + 1,
        dtype=float,
    )

    F_adv[0] = (
        u_face[0]
        * godunov_fractional_flux_np(
            S_INJECTED,
            S[0],
        )
    )

    for face in range(
        1,
        n,
    ):

        F_adv[face] = (
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

    F_adv[n] = (
        u_face[n]
        * fractional_flow_np(
            np.array(
                [S[-1]]
            )
        )[0]
    )

    div_adv = (
        F_adv[1:]
        - F_adv[:-1]
    ) / dxi

    # -------------------------------------------------------------------------
    # CAPILLARY FLUX
    # -------------------------------------------------------------------------

    D_cell = diffusion_shape_np(
        S
    )

    G_cap = np.zeros(
        n + 1,
        dtype=float,
    )

    D_injected = float(
        diffusion_shape_np(
            np.array(
                [S_INJECTED]
            )
        )[0]
    )

    D_left = (
        0.5
        * (
            D_injected
            + D_cell[0]
        )
    )

    G_cap[0] = (
        POROSITY
        / PE_C
        *
        D_left
        *
        (
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
                D_cell[
                    face - 1
                ]
                +
                D_cell[
                    face
                ]
            )
        )

        G_cap[face] = (
            POROSITY
            / PE_C
            *
            D_face
            *
            (
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

    G_cap[n] = 0.0

    div_cap = (
        G_cap[1:]
        - G_cap[:-1]
    ) / dxi

    return {
        "div_adv":
            div_adv,

        "div_cap":
            div_cap,

        "F_adv":
            F_adv,

        "G_cap":
            G_cap,
    }


# =============================================================================
# SG7A TIME DERIVATIVE
# =============================================================================

def sg7a_time_derivative(
    master_tD,
    master_S,
    index,
):

    index = int(
        index
    )

    if index <= 0:

        dt = (
            master_tD[1]
            - master_tD[0]
        )

        return (
            master_S[1]
            - master_S[0]
        ) / dt

    if index >= (
        len(master_tD) - 1
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
# BUILD NETWORK INPUT
# =============================================================================

def make_model_input(
    xi,
    tD_actual,
    tD_scale,
):

    t_norm = (
        tD_actual
        / tD_scale
    )

    X = np.zeros(
        (
            len(
                np.atleast_1d(
                    tD_actual
                )
            ),
            len(xi),
            2,
        ),
        dtype=np.float32,
    )

    X[
        :,
        :,
        0
    ] = xi[
        None,
        :
    ]

    for i, value in enumerate(
        np.atleast_1d(
            t_norm
        )
    ):

        X[
            i,
            :,
            1
        ] = value

    return X


# =============================================================================
# PI-RNN TEMPORAL DERIVATIVE
# =============================================================================

def pirnn_time_derivative(
    model,
    xi,
    tD_values,
    tD_scale,
    dt_multiplier,
):

    base_dt = (
        tD_scale
        / 800.0
    )

    dt_requested = (
        dt_multiplier
        * base_dt
    )

    tD_values = np.asarray(
        tD_values,
        dtype=float,
    )

    t_minus = np.maximum(
        tD_values
        - dt_requested,
        0.0,
    )

    t_plus = np.minimum(
        tD_values
        + dt_requested,
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

    dt_effective = (
        t_plus
        - t_minus
    )

    derivative = (
        S_plus
        - S_minus
    ) / dt_effective[
        :,
        None
    ]

    return derivative


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
# COMPONENT AUDIT
# =============================================================================

def perform_component_audit(
    model,
    dataset,
    sg7a,
    dt_multiplier=1.0,
):

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=float,
    )

    tD_test = np.asarray(
        dataset[
            "tD_test"
        ],
        dtype=float,
    )

    test_indices = np.asarray(
        dataset[
            "index_test"
        ],
        dtype=int,
    )

    truth = np.asarray(
        dataset[
            "Y_test"
        ][
            :,
            :,
            0
        ],
        dtype=float,
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

    # -------------------------------------------------------------------------
    # TEMPORAL TERMS
    # -------------------------------------------------------------------------

    truth_dt = np.zeros_like(
        truth
    )

    for p, master_index in enumerate(
        test_indices
    ):

        truth_dt[p] = (
            sg7a_time_derivative(
                np.asarray(
                    sg7a[
                        "master_tD"
                    ],
                    dtype=float,
                ),
                np.asarray(
                    sg7a[
                        "master_saturation"
                    ],
                    dtype=float,
                ),
                master_index,
            )
        )

    pirnn_dt = (
        pirnn_time_derivative(
            model,
            xi,
            tD_test,
            tD_scale,
            dt_multiplier,
        )
    )

    # -------------------------------------------------------------------------
    # SPATIAL TERMS
    # -------------------------------------------------------------------------

    truth_adv = np.zeros_like(
        truth
    )

    truth_cap = np.zeros_like(
        truth
    )

    pirnn_adv = np.zeros_like(
        truth
    )

    pirnn_cap = np.zeros_like(
        truth
    )

    for p in range(
        len(
            tD_test
        )
    ):

        truth_components = (
            spatial_components_np(
                truth[p],
                xi,
            )
        )

        pirnn_components = (
            spatial_components_np(
                prediction[p],
                xi,
            )
        )

        truth_adv[p] = (
            truth_components[
                "div_adv"
            ]
        )

        truth_cap[p] = (
            truth_components[
                "div_cap"
            ]
        )

        pirnn_adv[p] = (
            pirnn_components[
                "div_adv"
            ]
        )

        pirnn_cap[p] = (
            pirnn_components[
                "div_cap"
            ]
        )

    # -------------------------------------------------------------------------
    # FULL RESIDUALS
    # -------------------------------------------------------------------------

    truth_residual = (
        truth_dt
        +
        truth_adv
        -
        truth_cap
    )

    pirnn_residual = (
        pirnn_dt
        +
        pirnn_adv
        -
        pirnn_cap
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

    pirnn_scale = (
        np.abs(
            pirnn_dt
        )
        +
        np.abs(
            pirnn_adv
        )
        +
        np.abs(
            pirnn_cap
        )
        +
        1.0e-4
    )

    truth_relative = (
        truth_residual
        / truth_scale
    )

    pirnn_relative = (
        pirnn_residual
        / pirnn_scale
    )

    # -------------------------------------------------------------------------
    # COMPONENT DIFFERENCES
    # -------------------------------------------------------------------------

    temporal_difference = (
        pirnn_dt
        - truth_dt
    )

    advective_difference = (
        pirnn_adv
        - truth_adv
    )

    capillary_difference = (
        pirnn_cap
        - truth_cap
    )

    residual_difference = (
        pirnn_residual
        - truth_residual
    )

    return {
        "truth":
            truth,

        "prediction":
            prediction,

        "truth_dt":
            truth_dt,

        "pirnn_dt":
            pirnn_dt,

        "truth_adv":
            truth_adv,

        "pirnn_adv":
            pirnn_adv,

        "truth_cap":
            truth_cap,

        "pirnn_cap":
            pirnn_cap,

        "truth_residual":
            truth_residual,

        "pirnn_residual":
            pirnn_residual,

        "truth_relative":
            truth_relative,

        "pirnn_relative":
            pirnn_relative,

        "truth_scale":
            truth_scale,

        "pirnn_scale":
            pirnn_scale,

        "temporal_difference":
            temporal_difference,

        "advective_difference":
            advective_difference,

        "capillary_difference":
            capillary_difference,

        "residual_difference":
            residual_difference,
    }


# =============================================================================
# METRIC HELPERS
# =============================================================================

def mae(values):

    return float(
        np.mean(
            np.abs(
                values
            )
        )
    )


def rms(values):

    return float(
        np.sqrt(
            np.mean(
                np.asarray(
                    values
                ) ** 2
            )
        )
    )


# =============================================================================
# REGIONAL COMPONENT METRICS
# =============================================================================

def regional_component_metrics(
    result,
    masks,
):

    output = {}

    for region_name, mask in (
        masks.items()
    ):

        output[
            region_name
        ] = {
            "temporal_difference_MAE":
                mae(
                    result[
                        "temporal_difference"
                    ][
                        mask
                    ]
                ),

            "advective_difference_MAE":
                mae(
                    result[
                        "advective_difference"
                    ][
                        mask
                    ]
                ),

            "capillary_difference_MAE":
                mae(
                    result[
                        "capillary_difference"
                    ][
                        mask
                    ]
                ),

            "pirnn_residual_MAE":
                mae(
                    result[
                        "pirnn_residual"
                    ][
                        mask
                    ]
                ),

            "pirnn_relative_residual_MAE":
                mae(
                    result[
                        "pirnn_relative"
                    ][
                        mask
                    ]
                ),
        }

    return output


# =============================================================================
# TIME-BAND METRICS
# =============================================================================

def time_band_metrics(
    result,
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

        output[name] = {
            "temporal_difference_MAE":
                mae(
                    result[
                        "temporal_difference"
                    ][
                        mask
                    ]
                ),

            "advective_difference_MAE":
                mae(
                    result[
                        "advective_difference"
                    ][
                        mask
                    ]
                ),

            "capillary_difference_MAE":
                mae(
                    result[
                        "capillary_difference"
                    ][
                        mask
                    ]
                ),

            "pirnn_relative_residual_MAE":
                mae(
                    result[
                        "pirnn_relative"
                    ][
                        mask
                    ]
                ),
        }

    return output


# =============================================================================
# LOW-ACTIVITY NORMALIZATION AUDIT
# =============================================================================

def normalization_audit(
    result,
):
    """
    Determine whether the relative FV residual is being inflated in regions
    where the physical terms themselves are small.
    """

    scale = (
        result[
            "pirnn_scale"
        ]
    )

    relative = np.abs(
        result[
            "pirnn_relative"
        ]
    )

    absolute_residual = np.abs(
        result[
            "pirnn_residual"
        ]
    )

    thresholds = [
        0.01,
        0.05,
        0.10,
        0.25,
    ]

    output = {}

    for quantile in thresholds:

        scale_threshold = float(
            np.quantile(
                scale,
                quantile,
            )
        )

        mask = (
            scale
            <= scale_threshold
        )

        output[
            f"lowest_{int(quantile * 100)}pct_activity"
        ] = {
            "fraction_of_points":
                float(
                    np.mean(
                        mask
                    )
                ),

            "scale_threshold":
                scale_threshold,

            "relative_residual_MAE":
                mae(
                    relative[
                        mask
                    ]
                ),

            "absolute_residual_MAE":
                mae(
                    absolute_residual[
                        mask
                    ]
                ),

            "fraction_of_total_relative_residual":
                float(
                    np.sum(
                        relative[
                            mask
                        ]
                    )
                    /
                    (
                        np.sum(
                            relative
                        )
                        + EPS
                    )
                ),
        }

    return output


# =============================================================================
# DOMINANT COMPONENT
# =============================================================================

def determine_dominant_component(
    result,
):

    temporal = mae(
        result[
            "temporal_difference"
        ]
    )

    advective = mae(
        result[
            "advective_difference"
        ]
    )

    capillary = mae(
        result[
            "capillary_difference"
        ]
    )

    values = {
        "TEMPORAL":
            temporal,

        "ADVECTIVE":
            advective,

        "CAPILLARY":
            capillary,
    }

    dominant = max(
        values,
        key=values.get,
    )

    total = (
        temporal
        +
        advective
        +
        capillary
        +
        EPS
    )

    fractions = {
        key:
            float(
                value
                / total
            )
        for key, value
        in values.items()
    }

    return {
        "dominant_component":
            dominant,

        "component_MAE":
            values,

        "relative_contribution_proxy":
            fractions,
    }


# =============================================================================
# TIME-DIFFERENCE SENSITIVITY
# =============================================================================

def run_dt_sensitivity(
    model,
    dataset,
    sg7a,
):

    rows = []

    audits = {}

    for multiplier in (
        DT_MULTIPLIERS
    ):

        print(
            f"\nAuditing dt multiplier = "
            f"{multiplier:.2f}"
        )

        result = (
            perform_component_audit(
                model,
                dataset,
                sg7a,
                dt_multiplier=(
                    multiplier
                ),
            )
        )

        fv_mae = mae(
            result[
                "pirnn_relative"
            ]
        )

        absolute_mae = mae(
            result[
                "pirnn_residual"
            ]
        )

        temporal_error = mae(
            result[
                "temporal_difference"
            ]
        )

        adv_error = mae(
            result[
                "advective_difference"
            ]
        )

        cap_error = mae(
            result[
                "capillary_difference"
            ]
        )

        ratio = (
            fv_mae
            /
            SG7A_REFERENCE_FV_RELATIVE_MAE
        )

        rows.append({
            "dt_multiplier":
                multiplier,

            "pirnn_relative_FV_MAE":
                fv_mae,

            "pirnn_absolute_FV_MAE":
                absolute_mae,

            "PI_RNN_to_SG7A_ratio":
                ratio,

            "temporal_component_difference_MAE":
                temporal_error,

            "advective_component_difference_MAE":
                adv_error,

            "capillary_component_difference_MAE":
                cap_error,
        })

        audits[
            multiplier
        ] = result

        print(
            f"  FV relative MAE       : "
            f"{fv_mae:.6e}"
        )

        print(
            f"  FV / SG7A ratio       : "
            f"{ratio:.3f}"
        )

        print(
            f"  Temporal difference   : "
            f"{temporal_error:.6e}"
        )

        print(
            f"  Advective difference  : "
            f"{adv_error:.6e}"
        )

        print(
            f"  Capillary difference  : "
            f"{cap_error:.6e}"
        )

    return (
        rows,
        audits,
    )


# =============================================================================
# SAVE CSV
# =============================================================================

def save_dt_csv(
    rows,
):

    with open(
        DT_SENSITIVITY_CSV,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = (
            csv.DictWriter(
                f,
                fieldnames=list(
                    rows[0].keys()
                ),
            )
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def save_profile_csv(
    dataset,
    result,
):

    tD = np.asarray(
        dataset[
            "tD_test"
        ],
        dtype=float,
    )

    rows = []

    for p in range(
        len(tD)
    ):

        rows.append({
            "profile":
                p,

            "tD":
                float(
                    tD[p]
                ),

            "saturation_L1":
                mae(
                    result[
                        "prediction"
                    ][p]
                    -
                    result[
                        "truth"
                    ][p]
                ),

            "temporal_difference_MAE":
                mae(
                    result[
                        "temporal_difference"
                    ][p]
                ),

            "advective_difference_MAE":
                mae(
                    result[
                        "advective_difference"
                    ][p]
                ),

            "capillary_difference_MAE":
                mae(
                    result[
                        "capillary_difference"
                    ][p]
                ),

            "PI_RNN_relative_FV_MAE":
                mae(
                    result[
                        "pirnn_relative"
                    ][p]
                ),
        })

    with open(
        PROFILE_METRICS_CSV,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = (
            csv.DictWriter(
                f,
                fieldnames=list(
                    rows[0].keys()
                ),
            )
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# =============================================================================
# PLOTS
# =============================================================================

def plot_component_mae(
    dominant,
):

    names = [
        "Temporal",
        "Advective",
        "Capillary",
    ]

    values = [
        dominant[
            "component_MAE"
        ][
            "TEMPORAL"
        ],

        dominant[
            "component_MAE"
        ][
            "ADVECTIVE"
        ],

        dominant[
            "component_MAE"
        ][
            "CAPILLARY"
        ],
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
        "MAE vs SG7A component"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6C\n"
        "Residual Component Difference"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6C_Component_MAE.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_dt_sensitivity(
    rows,
):

    dt_multiplier = np.array([
        row[
            "dt_multiplier"
        ]
        for row in rows
    ])

    fv = np.array([
        row[
            "pirnn_relative_FV_MAE"
        ]
        for row in rows
    ])

    fig, ax = plt.subplots(
        figsize=(
            8,
            6,
        )
    )

    ax.plot(
        dt_multiplier,
        fv,
        marker="o",
    )

    ax.axhline(
        FREEZE_ABSOLUTE_FV_TARGET,
        linestyle="--",
        label="Freeze target",
    )

    ax.set_xlabel(
        r"$\Delta t_D$ multiplier"
    )

    ax.set_ylabel(
        "PI-RNN relative FV MAE"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6C\n"
        "Temporal-Difference Sensitivity"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6C_dt_Sensitivity.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_component_error_maps(
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

    components = [
        (
            "temporal_difference",
            "Temporal component difference",
            "V15SG7B6C_Temporal_Error_Map.png",
        ),
        (
            "advective_difference",
            "Advective component difference",
            "V15SG7B6C_Advective_Error_Map.png",
        ),
        (
            "capillary_difference",
            "Capillary component difference",
            "V15SG7B6C_Capillary_Error_Map.png",
        ),
        (
            "pirnn_relative",
            "PI-RNN relative FV residual",
            "V15SG7B6C_Relative_FV_Map.png",
        ),
    ]

    for (
        key,
        title,
        filename,
    ) in components:

        fig, ax = plt.subplots(
            figsize=(
                10,
                6,
            )
        )

        im = ax.imshow(
            np.abs(
                result[
                    key
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
            "Absolute magnitude"
        )

        ax.set_xlabel(
            r"$\xi$"
        )

        ax.set_ylabel(
            r"$t_D$"
        )

        ax.set_title(
            "PAD-Stream V15-SG7B-6C\n"
            + title
        )

        fig.tight_layout()

        fig.savefig(
            OUTPUT_DIR
            / filename,
            dpi=300,
        )

        plt.close(
            fig
        )


def plot_truth_vs_pirnn_components(
    dataset,
    result,
):

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=float,
    )

    tD = np.asarray(
        dataset[
            "tD_test"
        ],
        dtype=float,
    )

    profile_errors = np.mean(
        np.abs(
            result[
                "pirnn_relative"
            ]
        ),
        axis=1,
    )

    selected = int(
        np.argmax(
            profile_errors
        )
    )

    components = [
        (
            "truth_dt",
            "pirnn_dt",
            "Temporal term",
            "V15SG7B6C_Temporal_Profile.png",
        ),
        (
            "truth_adv",
            "pirnn_adv",
            "Advective divergence",
            "V15SG7B6C_Advective_Profile.png",
        ),
        (
            "truth_cap",
            "pirnn_cap",
            "Capillary divergence",
            "V15SG7B6C_Capillary_Profile.png",
        ),
    ]

    for (
        truth_key,
        pirnn_key,
        title,
        filename,
    ) in components:

        fig, ax = plt.subplots(
            figsize=(
                9,
                6,
            )
        )

        ax.plot(
            xi,
            result[
                truth_key
            ][
                selected
            ],
            linewidth=2.0,
            label="SG7A",
        )

        ax.plot(
            xi,
            result[
                pirnn_key
            ][
                selected
            ],
            linestyle="--",
            linewidth=1.5,
            label="PI-RNN",
        )

        ax.set_xlabel(
            r"$\xi$"
        )

        ax.set_ylabel(
            title
        )

        ax.set_title(
            "PAD-Stream V15-SG7B-6C\n"
            f"{title} at tD={tD[selected]:.4f}"
        )

        ax.legend()

        fig.tight_layout()

        fig.savefig(
            OUTPUT_DIR
            / filename,
            dpi=300,
        )

        plt.close(
            fig
        )


# =============================================================================
# DIAGNOSIS
# =============================================================================

def determine_diagnosis(
    dominant,
    dt_rows,
    normalization,
):

    component = (
        dominant[
            "dominant_component"
        ]
    )

    fv_values = np.array([
        row[
            "pirnn_relative_FV_MAE"
        ]
        for row in dt_rows
    ])

    fv_range = (
        np.max(
            fv_values
        )
        -
        np.min(
            fv_values
        )
    )

    fv_mean = np.mean(
        fv_values
    )

    dt_sensitive = (
        fv_range
        / max(
            fv_mean,
            EPS,
        )
        > 0.20
    )

    low_activity_share = (
        normalization[
            "lowest_10pct_activity"
        ][
            "fraction_of_total_relative_residual"
        ]
    )

    low_activity_dominant = (
        low_activity_share
        > 0.25
    )

    if dt_sensitive:

        diagnosis = (
            "TEMPORAL_DIFFERENTIATION_SENSITIVITY"
        )

        recommendation = (
            "The measured FV residual depends materially on the "
            "finite-difference interval used for dS/dtD. The next "
            "step should refine temporal-consistency treatment and "
            "the derivative evaluation before modifying architecture."
        )

    elif (
        component
        == "CAPILLARY"
    ):

        diagnosis = (
            "CAPILLARY_GRADIENT_LIMITATION"
        )

        recommendation = (
            "The remaining residual floor is dominated by the "
            "capillary-divergence mismatch. A targeted capillary-gradient "
            "or flux-consistency refinement should be tested next."
        )

    elif (
        component
        == "TEMPORAL"
    ):

        diagnosis = (
            "TEMPORAL_CONSISTENCY_LIMITATION"
        )

        recommendation = (
            "The temporal derivative mismatch dominates. The next "
            "training experiment should enforce adjacent-time consistency "
            "rather than simply increasing the global FV weight."
        )

    elif (
        component
        == "ADVECTIVE"
    ):

        diagnosis = (
            "ADVECTIVE_FLUX_LIMITATION"
        )

        recommendation = (
            "The dominant discrepancy is in conservative advective flux. "
            "The next refinement should directly emphasize face-flux "
            "consistency with SG7A."
        )

    elif low_activity_dominant:

        diagnosis = (
            "RELATIVE_RESIDUAL_NORMALIZATION_EFFECT"
        )

        recommendation = (
            "A disproportionate share of the relative residual arises "
            "from low-activity regions. Reassess the normalization metric "
            "before imposing further network complexity."
        )

    else:

        diagnosis = (
            "MIXED_COMPONENT_FLOOR"
        )

        recommendation = (
            "No single component dominates strongly. The current "
            "plain-LSTM surrogate is close to SG7A, but the remaining "
            "physics floor is distributed. A controlled flux/temporal "
            "consistency refinement should precede architecture changes."
        )

    return {
        "diagnosis":
            diagnosis,

        "recommendation":
            recommendation,

        "dt_sensitive":
            bool(
                dt_sensitive
            ),

        "low_activity_dominant":
            bool(
                low_activity_dominant
            ),

        "dominant_component":
            component,
    }


# =============================================================================
# SAVE RESULTS
# =============================================================================

def save_results(
    dataset,
    audit,
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
            audit[
                "truth"
            ],

        prediction=
            audit[
                "prediction"
            ],

        truth_dt=
            audit[
                "truth_dt"
            ],

        pirnn_dt=
            audit[
                "pirnn_dt"
            ],

        truth_adv=
            audit[
                "truth_adv"
            ],

        pirnn_adv=
            audit[
                "pirnn_adv"
            ],

        truth_cap=
            audit[
                "truth_cap"
            ],

        pirnn_cap=
            audit[
                "pirnn_cap"
            ],

        truth_relative_residual=
            audit[
                "truth_relative"
            ],

        pirnn_relative_residual=
            audit[
                "pirnn_relative"
            ],
    )


# =============================================================================
# SUMMARY
# =============================================================================

def save_summary(
    audit,
    regional,
    time_bands,
    dominant,
    normalization,
    dt_rows,
    diagnosis,
):

    summary = {
        "milestone":
            "V15-SG7B-6C",

        "description":
            (
                "Conservative FV residual-component audit "
                "for the SG7B-6B PI-RNN"
            ),

        "training_performed":
            False,

        "source_model":
            "V15SG7B6B_Best_Model.keras",

        "reference_targets": {
            "SG7A_FV_relative_MAE":
                SG7A_REFERENCE_FV_RELATIVE_MAE,

            "SG7B6B_previous_FV_relative_MAE":
                SG7B6B_REFERENCE_FV_RELATIVE_MAE,

            "freeze_absolute_FV_target":
                FREEZE_ABSOLUTE_FV_TARGET,

            "freeze_ratio_target":
                FREEZE_RATIO_TARGET,
        },

        "authoritative_dt_multiplier":
            1.0,

        "global_component_differences": {
            "temporal_MAE":
                mae(
                    audit[
                        "temporal_difference"
                    ]
                ),

            "advective_MAE":
                mae(
                    audit[
                        "advective_difference"
                    ]
                ),

            "capillary_MAE":
                mae(
                    audit[
                        "capillary_difference"
                    ]
                ),

            "PI_RNN_absolute_residual_MAE":
                mae(
                    audit[
                        "pirnn_residual"
                    ]
                ),

            "PI_RNN_relative_residual_MAE":
                mae(
                    audit[
                        "pirnn_relative"
                    ]
                ),

            "SG7A_relative_residual_MAE":
                mae(
                    audit[
                        "truth_relative"
                    ]
                ),
        },

        "dominant_component":
            dominant,

        "regional":
            regional,

        "time_bands":
            time_bands,

        "normalization_audit":
            normalization,

        "dt_sensitivity":
            dt_rows,

        "diagnosis":
            diagnosis,

        "status":
            "AUDIT_COMPLETE",

        "next_action":
            diagnosis[
                "recommendation"
            ],
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
        "PAD-Stream Version 15-SG7B-6C"
    )

    print(
        "Conservative Residual Component Audit"
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

    if not MODEL_FILE.exists():

        raise FileNotFoundError(
            "SG7B-6B model missing:\n"
            f"{MODEL_FILE}"
        )

    model = (
        tf.keras.models.load_model(
            MODEL_FILE
        )
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
        f"  Test profiles           : "
        f"{len(dataset['X_test'])}"
    )

    print(
        f"  xi nodes                : "
        f"{len(dataset['xi'])}"
    )

    # -------------------------------------------------------------------------
    # DT SENSITIVITY
    # -------------------------------------------------------------------------

    print(
        "\n"
        + "=" * 78
    )

    print(
        "TIME-DIFFERENCE SENSITIVITY"
    )

    print(
        "=" * 78
    )

    (
        dt_rows,
        audits,
    ) = run_dt_sensitivity(
        model,
        dataset,
        sg7a,
    )

    # Authoritative SG7B-7 definition
    audit = (
        audits[
            1.0
        ]
    )

    # -------------------------------------------------------------------------
    # COMPONENT METRICS
    # -------------------------------------------------------------------------

    masks = build_region_masks(
        audit[
            "truth"
        ],
        dataset[
            "xi"
        ],
    )

    regional = (
        regional_component_metrics(
            audit,
            masks,
        )
    )

    time_bands = (
        time_band_metrics(
            audit,
            dataset[
                "tD_test"
            ],
        )
    )

    normalization = (
        normalization_audit(
            audit
        )
    )

    dominant = (
        determine_dominant_component(
            audit
        )
    )

    diagnosis = (
        determine_diagnosis(
            dominant,
            dt_rows,
            normalization,
        )
    )

    # -------------------------------------------------------------------------
    # GLOBAL RESULTS
    # -------------------------------------------------------------------------

    print(
        "\n"
        + "=" * 78
    )

    print(
        "AUTHORITATIVE COMPONENT AUDIT"
    )

    print(
        "=" * 78
    )

    print(
        f"Temporal component MAE    : "
        f"{mae(audit['temporal_difference']):.6e}"
    )

    print(
        f"Advective component MAE   : "
        f"{mae(audit['advective_difference']):.6e}"
    )

    print(
        f"Capillary component MAE   : "
        f"{mae(audit['capillary_difference']):.6e}"
    )

    print(
        f"PI-RNN absolute FV MAE    : "
        f"{mae(audit['pirnn_residual']):.6e}"
    )

    print(
        f"PI-RNN relative FV MAE    : "
        f"{mae(audit['pirnn_relative']):.6e}"
    )

    print(
        f"SG7A relative FV MAE      : "
        f"{mae(audit['truth_relative']):.6e}"
    )

    ratio = (
        mae(
            audit[
                "pirnn_relative"
            ]
        )
        /
        max(
            mae(
                audit[
                    "truth_relative"
                ]
            ),
            EPS,
        )
    )

    print(
        f"PI-RNN / SG7A ratio       : "
        f"{ratio:.3f}"
    )

    print(
        "\nDOMINANT COMPONENT"
    )

    print(
        f"  {dominant['dominant_component']}"
    )

    print(
        "\nREGIONAL RELATIVE FV MAE"
    )

    for region in [
        "injector",
        "front",
        "interior",
        "outlet",
    ]:

        print(
            f"  {region:10s}            : "
            f"{regional[region]['pirnn_relative_residual_MAE']:.6e}"
        )

    print(
        "\nTIME-BAND RELATIVE FV MAE"
    )

    for band in [
        "early",
        "middle",
        "late",
    ]:

        print(
            f"  {band:10s}            : "
            f"{time_bands[band]['pirnn_relative_residual_MAE']:.6e}"
        )

    print(
        "\nNORMALIZATION AUDIT"
    )

    for key, values in (
        normalization.items()
    ):

        print(
            f"  {key}"
        )

        print(
            f"    relative residual MAE : "
            f"{values['relative_residual_MAE']:.6e}"
        )

        print(
            f"    residual contribution : "
            f"{100.0 * values['fraction_of_total_relative_residual']:.2f}%"
        )

    # -------------------------------------------------------------------------
    # DIAGNOSIS
    # -------------------------------------------------------------------------

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-6C DIAGNOSIS"
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
        "\nDominant component:"
    )

    print(
        f"  {diagnosis['dominant_component']}"
    )

    print(
        "\nTime-derivative sensitivity:"
    )

    print(
        f"  {diagnosis['dt_sensitive']}"
    )

    print(
        "\nLow-activity normalization dominance:"
    )

    print(
        f"  {diagnosis['low_activity_dominant']}"
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
    # SAVE
    # -------------------------------------------------------------------------

    save_dt_csv(
        dt_rows
    )

    save_profile_csv(
        dataset,
        audit,
    )

    save_results(
        dataset,
        audit,
    )

    plot_component_mae(
        dominant
    )

    plot_dt_sensitivity(
        dt_rows
    )

    plot_component_error_maps(
        dataset,
        audit,
    )

    plot_truth_vs_pirnn_components(
        dataset,
        audit,
    )

    save_summary(
        audit,
        regional,
        time_bands,
        dominant,
        normalization,
        dt_rows,
        diagnosis,
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
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B6C_Component_MAE.png"
    )

    print(
        "  V15SG7B6C_dt_Sensitivity.png"
    )

    print(
        "  V15SG7B6C_Temporal_Error_Map.png"
    )

    print(
        "  V15SG7B6C_Advective_Error_Map.png"
    )

    print(
        "  V15SG7B6C_Capillary_Error_Map.png"
    )

    print(
        "  V15SG7B6C_Relative_FV_Map.png"
    )

    print(
        "  V15SG7B6C_Temporal_Profile.png"
    )

    print(
        "  V15SG7B6C_Advective_Profile.png"
    )

    print(
        "  V15SG7B6C_Capillary_Profile.png"
    )

    print(
        "\nTables:"
    )

    print(
        "  V15SG7B6C_Profile_Component_Metrics.csv"
    )

    print(
        "  V15SG7B6C_TimeDerivative_Sensitivity.csv"
    )

    print(
        "\nNumerical database:"
    )

    print(
        "  V15SG7B6C_Component_Audit.npz"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B6C_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-6C COMPLETED"
    )

    print(
        "STATUS: RESIDUAL FLOOR DIAGNOSED"
    )

    print()

    print(
        "No architecture change has been made."
    )

    print(
        "The next milestone will follow the "
        "diagnosed dominant residual mechanism."
    )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()