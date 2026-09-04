from pathlib import Path
import json
import csv

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7B-6C-R
# Residual Operator Reconciliation
#
# PURPOSE
# -------
# Reconcile the discrepancy between:
#
#   SG7B-7 SG7A truth FV relative MAE:
#       ~6.323248e-04
#
#   SG7B-6C SG7A truth FV relative MAE:
#       ~2.339423e-02
#
#
# NO TRAINING IS PERFORMED.
#
#
# QUESTIONS
# ---------
# 1. Does SG7B-3 Y_test exactly match SG7A master_saturation[index_test]?
#
# 2. Are test indices correctly mapped to test tD values?
#
# 3. Is the SG7A temporal derivative identical under both evaluation paths?
#
# 4. Are the advective and capillary terms identical?
#
# 5. Is the discrepancy caused by:
#
#       - dataset indexing
#       - Godunov face-flux implementation
#       - temporal differencing
#       - residual normalization
#       - mixing two different residual definitions
#
#
# OUTPUT
# ------
# Establish one canonical SG7A FV operator to be used by:
#
#   SG7B validation
#   SG7B physics losses
#   SG7B-6D advective refinement
#   dissertation metrics
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

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B6CR"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B6CR_Summary.json"
)

PROFILE_CSV = (
    OUTPUT_DIR
    / "V15SG7B6CR_Profile_Reconciliation.csv"
)

RESULTS_FILE = (
    OUTPUT_DIR
    / "V15SG7B6CR_Reconciliation.npz"
)


# =============================================================================
# PHYSICS
# =============================================================================

SWC = 0.20
SOR = 0.20

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

EPS = 1.0e-12


# =============================================================================
# EXPECTED VALUES FROM PRIOR MILESTONES
# =============================================================================

SG7B7_REPORTED_TRUTH_FV_MAE = (
    6.323248e-04
)

SG7B6C_REPORTED_TRUTH_FV_MAE = (
    2.339423e-02
)


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
        key:
            data[key]
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
                f"SG7A field missing: {key}"
            )

    return {
        key:
            data[key]
        for key in required
    }


# =============================================================================
# PHYSICS FUNCTIONS
# =============================================================================

def effective_saturation(
    S,
):

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


def fractional_flow(
    S,
):

    Se = effective_saturation(
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


def diffusion_shape(
    S,
):

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
            1.0
            - Se
        ) ** N_RES
    )

    fw = fractional_flow(
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
# TWO ADVECTIVE FLUX DEFINITIONS
# =============================================================================

def godunov_search_flux(
    S_left,
    S_right,
    n_sample=200,
):
    """
    Generic scalar Godunov search.

    Retained specifically to determine whether the truth discrepancy
    originates from the brute-force min/max Godunov implementation.
    """

    if abs(
        S_left
        - S_right
    ) < 1.0e-12:

        return float(
            fractional_flow(
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

    values = fractional_flow(
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


def upstream_flux(
    S_left,
):
    """
    Positive-velocity upstream flux used in the differentiable SG7B
    PI-RNN physics operator.
    """

    return float(
        fractional_flow(
            np.array(
                [S_left]
            )
        )[0]
    )


# =============================================================================
# SPATIAL OPERATOR
# =============================================================================

def spatial_operator(
    S,
    xi,
    advective_mode,
):

    S = np.asarray(
        S,
        dtype=float,
    )

    xi = np.asarray(
        xi,
        dtype=float,
    )

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

    velocity = np.exp(
        NC
        * face_xi
    )

    # -------------------------------------------------------------------------
    # ADVECTIVE FACE FLUX
    # -------------------------------------------------------------------------

    F = np.zeros(
        n + 1,
        dtype=float,
    )

    if advective_mode == "godunov_search":

        F[0] = (
            velocity[0]
            * godunov_search_flux(
                S_INJECTED,
                S[0],
            )
        )

        for face in range(
            1,
            n,
        ):

            F[face] = (
                velocity[face]
                * godunov_search_flux(
                    S[
                        face - 1
                    ],
                    S[
                        face
                    ],
                )
            )

    elif advective_mode == "positive_upwind":

        F[0] = (
            velocity[0]
            * upstream_flux(
                S_INJECTED
            )
        )

        for face in range(
            1,
            n,
        ):

            F[face] = (
                velocity[face]
                * upstream_flux(
                    S[
                        face - 1
                    ]
                )
            )

    else:

        raise ValueError(
            f"Unknown advective mode: "
            f"{advective_mode}"
        )

    # outlet
    F[n] = (
        velocity[n]
        * upstream_flux(
            S[-1]
        )
    )

    div_adv = (
        F[1:]
        - F[:-1]
    ) / dxi

    # -------------------------------------------------------------------------
    # CAPILLARY FLUX
    # -------------------------------------------------------------------------

    D = diffusion_shape(
        S
    )

    G = np.zeros(
        n + 1,
        dtype=float,
    )

    D_injected = float(
        diffusion_shape(
            np.array(
                [S_INJECTED]
            )
        )[0]
    )

    D_left = (
        0.5
        * (
            D_injected
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

    return {
        "F":
            F,

        "G":
            G,

        "div_adv":
            div_adv,

        "div_cap":
            div_cap,
    }


# =============================================================================
# TIME DERIVATIVE
# =============================================================================

def temporal_derivative(
    tD,
    S,
    index,
):

    index = int(
        index
    )

    if index == 0:

        dt = (
            tD[1]
            - tD[0]
        )

        return (
            S[1]
            - S[0]
        ) / dt

    if index == len(
        tD
    ) - 1:

        dt = (
            tD[-1]
            - tD[-2]
        )

        return (
            S[-1]
            - S[-2]
        ) / dt

    dt = (
        tD[
            index + 1
        ]
        -
        tD[
            index - 1
        ]
    )

    return (
        S[
            index + 1
        ]
        -
        S[
            index - 1
        ]
    ) / dt


# =============================================================================
# RESIDUAL
# =============================================================================

def residual_from_components(
    S_t,
    div_adv,
    div_cap,
):

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

    return {
        "residual":
            residual,

        "scale":
            scale,

        "relative":
            relative,
    }


# =============================================================================
# MAIN RECONCILIATION
# =============================================================================

def reconcile(
    dataset,
    sg7a,
):

    xi_dataset = np.asarray(
        dataset[
            "xi"
        ],
        dtype=float,
    )

    xi_sg7a = np.asarray(
        sg7a[
            "xi"
        ],
        dtype=float,
    )

    test_truth = np.asarray(
        dataset[
            "Y_test"
        ][
            :,
            :,
            0
        ],
        dtype=float,
    )

    test_tD = np.asarray(
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

    master_tD = np.asarray(
        sg7a[
            "master_tD"
        ],
        dtype=float,
    )

    master_S = np.asarray(
        sg7a[
            "master_saturation"
        ],
        dtype=float,
    )

    # -------------------------------------------------------------------------
    # DATASET / MASTER ALIGNMENT
    # -------------------------------------------------------------------------

    master_test_truth = (
        master_S[
            test_indices
        ]
    )

    saturation_alignment_error = (
        test_truth
        - master_test_truth
    )

    tD_alignment_error = (
        test_tD
        -
        master_tD[
            test_indices
        ]
    )

    xi_alignment_error = (
        xi_dataset
        - xi_sg7a
    )

    # -------------------------------------------------------------------------
    # RESIDUAL DATABASES
    # -------------------------------------------------------------------------

    n_profiles = (
        len(
            test_indices
        )
    )

    n_nodes = (
        len(
            xi_dataset
        )
    )

    time_term = np.zeros(
        (
            n_profiles,
            n_nodes,
        )
    )

    adv_search = np.zeros_like(
        time_term
    )

    adv_upwind = np.zeros_like(
        time_term
    )

    capillary = np.zeros_like(
        time_term
    )

    residual_search = np.zeros_like(
        time_term
    )

    residual_upwind = np.zeros_like(
        time_term
    )

    relative_search = np.zeros_like(
        time_term
    )

    relative_upwind = np.zeros_like(
        time_term
    )

    face_flux_difference_max = np.zeros(
        n_profiles
    )

    rows = []

    for p, index in enumerate(
        test_indices
    ):

        S = (
            master_S[
                index
            ]
        )

        S_t = temporal_derivative(
            master_tD,
            master_S,
            index,
        )

        search = spatial_operator(
            S,
            xi_sg7a,
            advective_mode=(
                "godunov_search"
            ),
        )

        upwind = spatial_operator(
            S,
            xi_sg7a,
            advective_mode=(
                "positive_upwind"
            ),
        )

        R_search = (
            residual_from_components(
                S_t,
                search[
                    "div_adv"
                ],
                search[
                    "div_cap"
                ],
            )
        )

        R_upwind = (
            residual_from_components(
                S_t,
                upwind[
                    "div_adv"
                ],
                upwind[
                    "div_cap"
                ],
            )
        )

        time_term[p] = S_t

        adv_search[p] = (
            search[
                "div_adv"
            ]
        )

        adv_upwind[p] = (
            upwind[
                "div_adv"
            ]
        )

        capillary[p] = (
            upwind[
                "div_cap"
            ]
        )

        residual_search[p] = (
            R_search[
                "residual"
            ]
        )

        residual_upwind[p] = (
            R_upwind[
                "residual"
            ]
        )

        relative_search[p] = (
            R_search[
                "relative"
            ]
        )

        relative_upwind[p] = (
            R_upwind[
                "relative"
            ]
        )

        face_flux_difference_max[p] = (
            np.max(
                np.abs(
                    search[
                        "F"
                    ]
                    -
                    upwind[
                        "F"
                    ]
                )
            )
        )

        rows.append({
            "profile":
                p,

            "master_index":
                int(
                    index
                ),

            "tD_dataset":
                float(
                    test_tD[p]
                ),

            "tD_master":
                float(
                    master_tD[
                        index
                    ]
                ),

            "saturation_alignment_Linf":
                float(
                    np.max(
                        np.abs(
                            saturation_alignment_error[
                                p
                            ]
                        )
                    )
                ),

            "godunov_search_relative_FV_MAE":
                float(
                    np.mean(
                        np.abs(
                            relative_search[
                                p
                            ]
                        )
                    )
                ),

            "positive_upwind_relative_FV_MAE":
                float(
                    np.mean(
                        np.abs(
                            relative_upwind[
                                p
                            ]
                        )
                    )
                ),

            "maximum_face_flux_difference":
                float(
                    face_flux_difference_max[
                        p
                    ]
                ),
        })

    return {
        "saturation_alignment_error":
            saturation_alignment_error,

        "tD_alignment_error":
            tD_alignment_error,

        "xi_alignment_error":
            xi_alignment_error,

        "time_term":
            time_term,

        "adv_search":
            adv_search,

        "adv_upwind":
            adv_upwind,

        "capillary":
            capillary,

        "residual_search":
            residual_search,

        "residual_upwind":
            residual_upwind,

        "relative_search":
            relative_search,

        "relative_upwind":
            relative_upwind,

        "face_flux_difference_max":
            face_flux_difference_max,

        "rows":
            rows,
    }


# =============================================================================
# METRICS
# =============================================================================

def mae(
    x,
):

    return float(
        np.mean(
            np.abs(
                x
            )
        )
    )


def rms(
    x,
):

    return float(
        np.sqrt(
            np.mean(
                np.asarray(
                    x
                ) ** 2
            )
        )
    )


# =============================================================================
# DETERMINE CANONICAL OPERATOR
# =============================================================================

def determine_canonical_operator(
    result,
):

    search_mae = mae(
        result[
            "relative_search"
        ]
    )

    upwind_mae = mae(
        result[
            "relative_upwind"
        ]
    )

    search_error_to_reported = abs(
        search_mae
        -
        SG7B7_REPORTED_TRUTH_FV_MAE
    )

    upwind_error_to_reported = abs(
        upwind_mae
        -
        SG7B7_REPORTED_TRUTH_FV_MAE
    )

    if (
        upwind_error_to_reported
        <
        search_error_to_reported
    ):

        canonical = (
            "POSITIVE_UPWIND"
        )

        canonical_mae = (
            upwind_mae
        )

    else:

        canonical = (
            "GODUNOV_SEARCH"
        )

        canonical_mae = (
            search_mae
        )

    return {
        "operator":
            canonical,

        "canonical_truth_FV_MAE":
            canonical_mae,

        "godunov_search_truth_FV_MAE":
            search_mae,

        "positive_upwind_truth_FV_MAE":
            upwind_mae,

        "distance_to_SG7B7_reported": {
            "godunov_search":
                search_error_to_reported,

            "positive_upwind":
                upwind_error_to_reported,
        },
    }


# =============================================================================
# VALIDATION
# =============================================================================

def validate(
    result,
    canonical,
):

    saturation_alignment = float(
        np.max(
            np.abs(
                result[
                    "saturation_alignment_error"
                ]
            )
        )
    )

    time_alignment = float(
        np.max(
            np.abs(
                result[
                    "tD_alignment_error"
                ]
            )
        )
    )

    xi_alignment = float(
        np.max(
            np.abs(
                result[
                    "xi_alignment_error"
                ]
            )
        )
    )

    checks = [
        (
            "SG7B-3 saturation agrees with SG7A master within float32 tolerance",
            saturation_alignment
            < 1.0e-7,
        ),

        (
            "SG7B-3 tD agrees with SG7A master",
            time_alignment
            < 1.0e-10,
        ),

        (
            "SG7B-3 xi agrees with SG7A master within float32 tolerance",
            xi_alignment
            < 1.0e-7,
        ),

        (
            "All truth residual values finite",
            np.all(
                np.isfinite(
                    result[
                        "relative_search"
                    ]
                )
            )
            and
            np.all(
                np.isfinite(
                    result[
                        "relative_upwind"
                    ]
                )
            ),
        ),

        (
            "Canonical operator identified",
            canonical[
                "operator"
            ]
            in [
                "POSITIVE_UPWIND",
                "GODUNOV_SEARCH",
            ],
        ),
    ]

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-6C-R VALIDATION"
    )

    print(
        "=" * 78
    )

    passed_all = True

    for description, passed in checks:

        print(
            f"[{'PASS' if passed else 'FAIL':4s}] "
            f"{description}"
        )

        if not passed:

            passed_all = False

    print(
        "=" * 78
    )

    return (
        passed_all,
        checks,
    )


# =============================================================================
# SAVE CSV
# =============================================================================

def save_csv(
    rows,
):

    with open(
        PROFILE_CSV,
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

def plot_profile_residual_comparison(
    dataset,
    result,
):

    tD = (
        dataset[
            "tD_test"
        ]
    )

    search = np.mean(
        np.abs(
            result[
                "relative_search"
            ]
        ),
        axis=1,
    )

    upwind = np.mean(
        np.abs(
            result[
                "relative_upwind"
            ]
        ),
        axis=1,
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        tD,
        search,
        label="Generic Godunov search",
    )

    ax.plot(
        tD,
        upwind,
        label="Positive-velocity upstream",
    )

    ax.axhline(
        SG7B7_REPORTED_TRUTH_FV_MAE,
        linestyle="--",
        label="SG7B-7 reported truth MAE",
    )

    ax.set_xlabel(
        r"$t_D$"
    )

    ax.set_ylabel(
        "Profile relative FV MAE"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6C-R\n"
        "SG7A Residual Operator Comparison"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6CR_Residual_Operator_Comparison.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_advective_difference(
    dataset,
    result,
):

    xi = dataset[
        "xi"
    ]

    tD = dataset[
        "tD_test"
    ]

    difference = np.abs(
        result[
            "adv_search"
        ]
        -
        result[
            "adv_upwind"
        ]
    )

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    im = ax.imshow(
        difference,
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
        "|div F_search - div F_upwind|"
    )

    ax.set_xlabel(
        r"$\xi$"
    )

    ax.set_ylabel(
        r"$t_D$"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6C-R\n"
        "Advective Operator Difference"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6CR_Advective_Operator_Difference.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_dataset_alignment(
    dataset,
    result,
):

    tD = dataset[
        "tD_test"
    ]

    saturation_error = np.max(
        np.abs(
            result[
                "saturation_alignment_error"
            ]
        ),
        axis=1,
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        tD,
        saturation_error,
    )

    ax.set_xlabel(
        r"$t_D$"
    )

    ax.set_ylabel(
        r"$L_\infty$ alignment error"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6C-R\n"
        "SG7B-3 Test Truth vs SG7A Master"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6CR_Dataset_Alignment.png",
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
        RESULTS_FILE,

        xi=
            dataset[
                "xi"
            ],

        tD_test=
            dataset[
                "tD_test"
            ],

        saturation_alignment_error=
            result[
                "saturation_alignment_error"
            ],

        tD_alignment_error=
            result[
                "tD_alignment_error"
            ],

        xi_alignment_error=
            result[
                "xi_alignment_error"
            ],

        time_term=
            result[
                "time_term"
            ],

        advective_godunov_search=
            result[
                "adv_search"
            ],

        advective_positive_upwind=
            result[
                "adv_upwind"
            ],

        capillary=
            result[
                "capillary"
            ],

        relative_residual_godunov_search=
            result[
                "relative_search"
            ],

        relative_residual_positive_upwind=
            result[
                "relative_upwind"
            ],
    )


# =============================================================================
# SUMMARY
# =============================================================================

def save_summary(
    result,
    canonical,
    validation_passed,
):

    search_mae = (
        canonical[
            "godunov_search_truth_FV_MAE"
        ]
    )

    upwind_mae = (
        canonical[
            "positive_upwind_truth_FV_MAE"
        ]
    )

    maximum_face_difference = float(
        np.max(
            result[
                "face_flux_difference_max"
            ]
        )
    )

    mean_face_difference = float(
        np.mean(
            result[
                "face_flux_difference_max"
            ]
        )
    )

    summary = {
        "milestone":
            "V15-SG7B-6C-R",

        "description":
            (
                "Reconciliation of SG7A truth "
                "finite-volume residual operators"
            ),

        "training_performed":
            False,

        "prior_reported_values": {
            "SG7B7_truth_FV_relative_MAE":
                SG7B7_REPORTED_TRUTH_FV_MAE,

            "SG7B6C_truth_FV_relative_MAE":
                SG7B6C_REPORTED_TRUTH_FV_MAE,
        },

        "dataset_alignment": {
            "maximum_saturation_difference":
                float(
                    np.max(
                        np.abs(
                            result[
                                "saturation_alignment_error"
                            ]
                        )
                    )
                ),

            "maximum_tD_difference":
                float(
                    np.max(
                        np.abs(
                            result[
                                "tD_alignment_error"
                            ]
                        )
                    )
                ),

            "maximum_xi_difference":
                float(
                    np.max(
                        np.abs(
                            result[
                                "xi_alignment_error"
                            ]
                        )
                    )
                ),
        },

        "operator_comparison": {
            "generic_Godunov_search_FV_relative_MAE":
                search_mae,

            "positive_velocity_upwind_FV_relative_MAE":
                upwind_mae,

            "maximum_face_flux_difference":
                maximum_face_difference,

            "mean_profile_maximum_face_flux_difference":
                mean_face_difference,
        },

        "canonical_operator": {
            "name":
                canonical[
                    "operator"
                ],

            "SG7A_truth_FV_relative_MAE":
                canonical[
                    "canonical_truth_FV_MAE"
                ],
        },

        "validation_passed":
            bool(
                validation_passed
            ),

        "status":
            (
                "CANONICAL_OPERATOR_ESTABLISHED"
                if validation_passed
                else
                "RECONCILIATION_INCOMPLETE"
            ),

        "next_milestone":
            (
                "V15-SG7B-6D - targeted advective-flux "
                "refinement using the canonical operator"
                if validation_passed
                else
                "Inspect residual operator discrepancy"
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
        "PAD-Stream Version 15-SG7B-6C-R"
    )

    print(
        "Residual Operator Reconciliation"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    dataset = load_dataset()

    sg7a = load_sg7a()

    print(
        "\nDATABASES"
    )

    print(
        f"  Test profiles           : "
        f"{len(dataset['index_test'])}"
    )

    print(
        f"  Test xi nodes           : "
        f"{len(dataset['xi'])}"
    )

    print(
        f"  SG7A master snapshots   : "
        f"{len(sg7a['master_tD'])}"
    )

    # -------------------------------------------------------------------------
    # RECONCILE
    # -------------------------------------------------------------------------

    result = reconcile(
        dataset,
        sg7a,
    )

    # -------------------------------------------------------------------------
    # ALIGNMENT
    # -------------------------------------------------------------------------

    saturation_alignment = float(
        np.max(
            np.abs(
                result[
                    "saturation_alignment_error"
                ]
            )
        )
    )

    time_alignment = float(
        np.max(
            np.abs(
                result[
                    "tD_alignment_error"
                ]
            )
        )
    )

    xi_alignment = float(
        np.max(
            np.abs(
                result[
                    "xi_alignment_error"
                ]
            )
        )
    )

    print(
        "\nDATASET / SG7A ALIGNMENT"
    )

    print(
        f"  Saturation Linf         : "
        f"{saturation_alignment:.6e}"
    )

    print(
        f"  tD Linf                 : "
        f"{time_alignment:.6e}"
    )

    print(
        f"  xi Linf                 : "
        f"{xi_alignment:.6e}"
    )

    # -------------------------------------------------------------------------
    # OPERATOR COMPARISON
    # -------------------------------------------------------------------------

    search_mae = mae(
        result[
            "relative_search"
        ]
    )

    upwind_mae = mae(
        result[
            "relative_upwind"
        ]
    )

    print(
        "\nSG7A TRUTH RESIDUAL — OPERATOR COMPARISON"
    )

    print(
        f"  Generic Godunov search  : "
        f"{search_mae:.6e}"
    )

    print(
        f"  Positive upwind         : "
        f"{upwind_mae:.6e}"
    )

    print(
        f"  SG7B-7 reported value   : "
        f"{SG7B7_REPORTED_TRUTH_FV_MAE:.6e}"
    )

    print(
        f"  SG7B-6C reported value  : "
        f"{SG7B6C_REPORTED_TRUTH_FV_MAE:.6e}"
    )

    print(
        "\nADVECTIVE FACE-FLUX DIFFERENCE"
    )

    print(
        f"  Max over all profiles   : "
        f"{np.max(result['face_flux_difference_max']):.6e}"
    )

    print(
        f"  Mean profile max        : "
        f"{np.mean(result['face_flux_difference_max']):.6e}"
    )

    # -------------------------------------------------------------------------
    # CANONICAL
    # -------------------------------------------------------------------------

    canonical = (
        determine_canonical_operator(
            result
        )
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "CANONICAL OPERATOR DECISION"
    )

    print(
        "=" * 78
    )

    print(
        f"Selected operator:"
    )

    print(
        f"  {canonical['operator']}"
    )

    print(
        f"\nCanonical SG7A truth FV MAE:"
    )

    print(
        f"  "
        f"{canonical['canonical_truth_FV_MAE']:.6e}"
    )

    print(
        "=" * 78
    )

    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------

    validation_passed, _ = validate(
        result,
        canonical,
    )

    # -------------------------------------------------------------------------
    # SAVE
    # -------------------------------------------------------------------------

    save_csv(
        result[
            "rows"
        ]
    )

    save_results(
        dataset,
        result,
    )

    plot_profile_residual_comparison(
        dataset,
        result,
    )

    plot_advective_difference(
        dataset,
        result,
    )

    plot_dataset_alignment(
        dataset,
        result,
    )

    save_summary(
        result,
        canonical,
        validation_passed,
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
        "  V15SG7B6CR_Residual_Operator_Comparison.png"
    )

    print(
        "  V15SG7B6CR_Advective_Operator_Difference.png"
    )

    print(
        "  V15SG7B6CR_Dataset_Alignment.png"
    )

    print(
        "\nTables:"
    )

    print(
        "  V15SG7B6CR_Profile_Reconciliation.csv"
    )

    print(
        "\nDatabase:"
    )

    print(
        "  V15SG7B6CR_Reconciliation.npz"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B6CR_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    if validation_passed:

        print(
            "V15-SG7B-6C-R COMPLETED"
        )

        print()

        print(
            "STATUS: CANONICAL RESIDUAL "
            "OPERATOR ESTABLISHED"
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7B-6D — Targeted "
            "Advective-Flux Refinement"
        )

    else:

        print(
            "V15-SG7B-6C-R INCOMPLETE"
        )

        print()

        print(
            "Do not proceed to SG7B-6D until "
            "dataset/operator alignment is resolved."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()