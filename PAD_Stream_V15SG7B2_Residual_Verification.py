from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7B-2
# Conservative PI-RNN Residual Verification Against Frozen SG7A Truth
#
# PURPOSE
# -------
# Before training the PI-RNN, verify that the physics residual intended for
# SG7B recognizes the frozen SG7A classical solution.
#
# Frozen SG7A governing equation:
#
#   dS/dtD
#   +
#   d[uD(xi) f(S)]/dxi
#   =
#   (phi / Pe_c)
#   d/dxi [
#       D_tilde(S) dS/dxi
#   ]
#
# with
#
#   uD(xi) = exp(Nc xi)
#
#
# TWO RESIDUALS ARE EVALUATED
# ---------------------------
#
# A) Conservative finite-volume residual
#
#       R_FV =
#           dS/dtD
#           +
#           div(F_adv)
#           -
#           div(F_cap)
#
#
# B) Strong-form diagnostic residual
#
#       R_strong =
#           dS/dtD
#           +
#           uD (df/dxi + Nc f)
#           -
#           (phi / Pe_c) d/dxi[D_tilde dS/dxi]
#
#
# The finite-volume residual is the PRIMARY residual because SG7A itself
# is a conservative finite-volume/operator-split solver.
#
# NO neural network is trained here.
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

SG7A_DIR = (
    ROOT
    / "output"
    / "V15_SG7A"
)

SG7A_FILE = (
    SG7A_DIR
    / "FULL_PHYSICS_STREAMLINE_SATURATION.npz"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B2"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B2_Summary.json"
)

TIME_CSV = (
    OUTPUT_DIR
    / "V15SG7B2_Residual_ByTime.csv"
)


# =============================================================================
# FROZEN SG7A PHYSICS
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


# =============================================================================
# LOAD FROZEN SG7A MASTER SOLUTION
# =============================================================================

def load_sg7a():

    if not SG7A_FILE.exists():

        raise FileNotFoundError(
            f"Frozen SG7A file not found:\n{SG7A_FILE}"
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

    xi = np.asarray(
        data["xi"],
        dtype=float,
    )

    master_tD = np.asarray(
        data["master_tD"],
        dtype=float,
    )

    master_S = np.asarray(
        data["master_saturation"],
        dtype=float,
    )

    if master_S.shape != (
        len(master_tD),
        len(xi),
    ):

        raise ValueError(
            "Unexpected SG7A master solution shape:\n"
            f"  master_tD = {master_tD.shape}\n"
            f"  xi        = {xi.shape}\n"
            f"  S         = {master_S.shape}"
        )

    return (
        xi,
        master_tD,
        master_S,
    )


# =============================================================================
# ROCK / FLUID FUNCTIONS
# =============================================================================

def effective_saturation(S):

    span = (
        1.0
        - SWC
        - SOR
    )

    Se = (
        np.asarray(
            S,
            dtype=float,
        )
        - SWC
    ) / span

    return np.clip(
        Se,
        0.0,
        1.0,
    )


def relative_permeability(S):

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
            1.0 - Se
        ) ** N_RES
    )

    return (
        kr_disp,
        kr_res,
    )


def fractional_flow(S):

    kr_d, kr_r = (
        relative_permeability(
            S
        )
    )

    lambda_d = (
        kr_d
        / MU_DISP
    )

    lambda_r = (
        kr_r
        / MU_RES
    )

    return (
        lambda_d
        /
        (
            lambda_d
            + lambda_r
            + EPS
        )
    )


# =============================================================================
# BROOKS-COREY NORMALIZED DIFFUSION SHAPE
# =============================================================================

def diffusion_shape(S):

    S = np.asarray(
        S,
        dtype=float,
    )

    span = (
        1.0
        - SWC
        - SOR
    )

    Se = np.clip(
        (
            S - SWC
        ) / span,
        1.0e-6,
        1.0 - 1.0e-6,
    )

    kr_res = (
        KR_RES_MAX
        * (
            1.0 - Se
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

    # Normalization at Se = 0.5
    Se_mid = 0.5

    S_mid = (
        SWC
        +
        Se_mid
        * span
    )

    kr_mid = (
        KR_RES_MAX
        * (
            1.0 - Se_mid
        ) ** N_RES
    )

    fw_mid = float(
        fractional_flow(
            np.array(
                [S_mid]
            )
        )[0]
    )

    norm = (
        kr_mid
        * fw_mid
        * Se_mid ** exponent
    )

    return (
        raw
        /
        max(
            norm,
            EPS,
        )
    )


# =============================================================================
# DIMENSIONLESS VELOCITY
# =============================================================================

def u_dimensionless(xi):

    return np.exp(
        NC
        * np.asarray(
            xi,
            dtype=float,
        )
    )


# =============================================================================
# GODUNOV FRACTIONAL-FLOW FLUX
# =============================================================================

def godunov_fractional_flux(
    S_left,
    S_right,
    n_sample=100,
):

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

    f_samples = fractional_flow(
        samples
    )

    if S_left <= S_right:

        return float(
            np.min(
                f_samples
            )
        )

    return float(
        np.max(
            f_samples
        )
    )


# =============================================================================
# FV ADVECTIVE FACE FLUXES
# =============================================================================

def advective_flux_faces(
    S,
    xi,
):
    """
    Construct conservative advective face fluxes:

        F = u_D f_Godunov

    using the same boundary philosophy as SG7A.
    """

    n = len(S)

    dxi = (
        xi[1]
        - xi[0]
    )

    face_xi = np.linspace(
        0.0,
        1.0,
        n + 1,
    )

    u_face = u_dimensionless(
        face_xi
    )

    flux = np.zeros(
        n + 1,
        dtype=float,
    )

    # Injector boundary
    flux[0] = (
        u_face[0]
        * godunov_fractional_flux(
            S_INJECTED,
            S[0],
        )
    )

    # Internal faces
    for face in range(
        1,
        n,
    ):

        f_god = godunov_fractional_flux(
            S[
                face - 1
            ],
            S[
                face
            ],
        )

        flux[face] = (
            u_face[face]
            * f_god
        )

    # Open outlet
    flux[n] = (
        u_face[n]
        * fractional_flow(
            np.array(
                [S[-1]]
            )
        )[0]
    )

    return flux


# =============================================================================
# FV CAPILLARY FACE FLUXES
# =============================================================================

def capillary_flux_faces(
    S,
    xi,
):
    """
    Construct capillary flux:

        G =
        (phi / Pe_c)
        D_tilde
        dS/dxi

    Boundary conditions follow SG7A:

    xi = 0:
        Dirichlet S = S_INJECTED at boundary face.

    xi = 1:
        zero diffusive flux.
    """

    n = len(S)

    dxi = (
        xi[1]
        - xi[0]
    )

    D_cell = diffusion_shape(
        S
    )

    G = np.zeros(
        n + 1,
        dtype=float,
    )

    # -------------------------------------------------------------------------
    # LEFT BOUNDARY
    #
    # Boundary-to-cell-center distance = dxi/2.
    # -------------------------------------------------------------------------

    D_left_boundary = float(
        diffusion_shape(
            np.array(
                [S_INJECTED]
            )
        )[0]
    )

    D_left_face = (
        0.5
        * (
            D_left_boundary
            + D_cell[0]
        )
    )

    gradient_left = (
        S[0]
        - S_INJECTED
    ) / (
        0.5
        * dxi
    )

    G[0] = (
        POROSITY
        / PE_C
        * D_left_face
        * gradient_left
    )

    # -------------------------------------------------------------------------
    # INTERNAL FACES
    # -------------------------------------------------------------------------

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

        gradient = (
            S[
                face
            ]
            -
            S[
                face - 1
            ]
        ) / dxi

        G[face] = (
            POROSITY
            / PE_C
            * D_face
            * gradient
        )

    # -------------------------------------------------------------------------
    # OUTLET — ZERO DIFFUSIVE FLUX
    # -------------------------------------------------------------------------

    G[n] = 0.0

    return G


# =============================================================================
# TIME DERIVATIVE
# =============================================================================

def temporal_derivative(
    master_tD,
    master_S,
):
    """
    Central time derivative where possible.

    Forward difference at first snapshot.
    Backward difference at final snapshot.
    """

    nt, nx = master_S.shape

    S_t = np.zeros_like(
        master_S,
        dtype=float,
    )

    # Forward
    dt = (
        master_tD[1]
        - master_tD[0]
    )

    S_t[0] = (
        master_S[1]
        - master_S[0]
    ) / dt

    # Central
    for n in range(
        1,
        nt - 1,
    ):

        dt = (
            master_tD[
                n + 1
            ]
            -
            master_tD[
                n - 1
            ]
        )

        S_t[n] = (
            master_S[
                n + 1
            ]
            -
            master_S[
                n - 1
            ]
        ) / dt

    # Backward
    dt = (
        master_tD[-1]
        - master_tD[-2]
    )

    S_t[-1] = (
        master_S[-1]
        - master_S[-2]
    ) / dt

    return S_t


# =============================================================================
# CONSERVATIVE FV RESIDUAL
# =============================================================================

def fv_residual_snapshot(
    S,
    S_t,
    xi,
):
    """
    Evaluate:

        R =
        dS/dtD
        +
        div(F_adv)
        -
        div(G_cap)
    """

    dxi = float(
        xi[1]
        - xi[0]
    )

    F_adv = advective_flux_faces(
        S,
        xi,
    )

    G_cap = capillary_flux_faces(
        S,
        xi,
    )

    div_adv = (
        F_adv[1:]
        -
        F_adv[:-1]
    ) / dxi

    div_cap = (
        G_cap[1:]
        -
        G_cap[:-1]
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
        1.0e-6
    )

    relative = (
        residual
        / scale
    )

    return {
        "residual":
            residual,

        "relative":
            relative,

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
# STRONG-FORM DIAGNOSTIC RESIDUAL
# =============================================================================

def strong_residual_snapshot(
    S,
    S_t,
    xi,
):
    """
    Diagnostic only.

        R =
        S_t
        +
        u_D (df/dxi + Nc f)
        -
        (phi / Pe_c)
        d/dxi[D_tilde dS/dxi]
    """

    dxi = float(
        xi[1]
        - xi[0]
    )

    f = fractional_flow(
        S
    )

    D = diffusion_shape(
        S
    )

    # Cell-centered first derivative
    df_dxi = np.gradient(
        f,
        dxi,
        edge_order=2,
    )

    dS_dxi = np.gradient(
        S,
        dxi,
        edge_order=2,
    )

    diffusive_quantity = (
        D
        * dS_dxi
    )

    d_diffusive_quantity = (
        np.gradient(
            diffusive_quantity,
            dxi,
            edge_order=2,
        )
    )

    u = u_dimensionless(
        xi
    )

    adv = (
        u
        * (
            df_dxi
            +
            NC
            * f
        )
    )

    diff = (
        POROSITY
        / PE_C
        * d_diffusive_quantity
    )

    residual = (
        S_t
        +
        adv
        -
        diff
    )

    scale = (
        np.abs(
            S_t
        )
        +
        np.abs(
            adv
        )
        +
        np.abs(
            diff
        )
        +
        1.0e-6
    )

    relative = (
        residual
        / scale
    )

    return {
        "residual":
            residual,

        "relative":
            relative,

        "adv":
            adv,

        "diff":
            diff,
    }


# =============================================================================
# FRONT / HIGH-GRADIENT MASK
# =============================================================================

def gradient_masks(
    S,
    xi,
):
    """
    Split domain into:

      injector region
      outlet region
      high-gradient/front region
      remaining interior
    """

    n = len(S)

    gradient = np.abs(
        np.gradient(
            S,
            xi,
            edge_order=2,
        )
    )

    # High-gradient region = top 10 percent of gradient magnitudes.
    threshold = np.quantile(
        gradient,
        0.90,
    )

    high_gradient = (
        gradient
        >= threshold
    )

    injector = np.zeros(
        n,
        dtype=bool,
    )

    injector[
        :max(
            3,
            int(
                0.05 * n
            ),
        )
    ] = True

    outlet = np.zeros(
        n,
        dtype=bool,
    )

    outlet[
        -max(
            3,
            int(
                0.05 * n
            ),
        ):
    ] = True

    interior = ~(
        injector
        |
        outlet
        |
        high_gradient
    )

    return {
        "injector":
            injector,

        "outlet":
            outlet,

        "high_gradient":
            high_gradient,

        "interior":
            interior,
    }


# =============================================================================
# METRICS
# =============================================================================

def residual_metrics(
    residual,
    relative,
    masks,
):

    def stats(mask):

        if not np.any(
            mask
        ):

            return {
                "mae": None,
                "rms": None,
                "max": None,
                "relative_mae": None,
            }

        r = residual[
            mask
        ]

        rr = relative[
            mask
        ]

        return {
            "mae":
                float(
                    np.mean(
                        np.abs(r)
                    )
                ),

            "rms":
                float(
                    np.sqrt(
                        np.mean(
                            r ** 2
                        )
                    )
                ),

            "max":
                float(
                    np.max(
                        np.abs(r)
                    )
                ),

            "relative_mae":
                float(
                    np.mean(
                        np.abs(rr)
                    )
                ),
        }

    all_mask = np.ones(
        len(residual),
        dtype=bool,
    )

    return {
        "all":
            stats(
                all_mask
            ),

        "interior":
            stats(
                masks[
                    "interior"
                ]
            ),

        "high_gradient":
            stats(
                masks[
                    "high_gradient"
                ]
            ),

        "injector":
            stats(
                masks[
                    "injector"
                ]
            ),

        "outlet":
            stats(
                masks[
                    "outlet"
                ]
            ),
    }


# =============================================================================
# RUN RESIDUAL ANALYSIS
# =============================================================================

def analyze_residuals(
    xi,
    master_tD,
    master_S,
):

    S_t_all = temporal_derivative(
        master_tD,
        master_S,
    )

    nt = len(
        master_tD
    )

    nx = len(
        xi
    )

    fv_map = np.zeros(
        (
            nt,
            nx,
        ),
        dtype=float,
    )

    fv_relative_map = np.zeros_like(
        fv_map
    )

    strong_map = np.zeros_like(
        fv_map
    )

    strong_relative_map = np.zeros_like(
        fv_map
    )

    rows = []

    for n in range(
        nt
    ):

        S = (
            master_S[n]
        )

        S_t = (
            S_t_all[n]
        )

        masks = gradient_masks(
            S,
            xi,
        )

        fv = fv_residual_snapshot(
            S,
            S_t,
            xi,
        )

        strong = (
            strong_residual_snapshot(
                S,
                S_t,
                xi,
            )
        )

        fv_map[n] = (
            fv[
                "residual"
            ]
        )

        fv_relative_map[n] = (
            fv[
                "relative"
            ]
        )

        strong_map[n] = (
            strong[
                "residual"
            ]
        )

        strong_relative_map[n] = (
            strong[
                "relative"
            ]
        )

        fv_stats = residual_metrics(
            fv[
                "residual"
            ],
            fv[
                "relative"
            ],
            masks,
        )

        strong_stats = residual_metrics(
            strong[
                "residual"
            ],
            strong[
                "relative"
            ],
            masks,
        )

        # Domain-integrated FV residual
        integrated = float(
            np.sum(
                fv[
                    "residual"
                ]
            )
            * (
                xi[1]
                - xi[0]
            )
        )

        rows.append({
            "snapshot":
                int(n),

            "tD":
                float(
                    master_tD[n]
                ),

            "fv_mae":
                fv_stats[
                    "all"
                ][
                    "mae"
                ],

            "fv_rms":
                fv_stats[
                    "all"
                ][
                    "rms"
                ],

            "fv_max":
                fv_stats[
                    "all"
                ][
                    "max"
                ],

            "fv_relative_mae":
                fv_stats[
                    "all"
                ][
                    "relative_mae"
                ],

            "fv_interior_relative_mae":
                fv_stats[
                    "interior"
                ][
                    "relative_mae"
                ],

            "fv_front_relative_mae":
                fv_stats[
                    "high_gradient"
                ][
                    "relative_mae"
                ],

            "fv_injector_relative_mae":
                fv_stats[
                    "injector"
                ][
                    "relative_mae"
                ],

            "fv_outlet_relative_mae":
                fv_stats[
                    "outlet"
                ][
                    "relative_mae"
                ],

            "fv_integrated_residual":
                integrated,

            "strong_mae":
                strong_stats[
                    "all"
                ][
                    "mae"
                ],

            "strong_relative_mae":
                strong_stats[
                    "all"
                ][
                    "relative_mae"
                ],
        })

        if (
            n % 100 == 0
            or n == nt - 1
        ):

            print(
                f"  Residual snapshot "
                f"{n}/{nt - 1}"
            )

    return {
        "rows":
            rows,

        "fv_map":
            fv_map,

        "fv_relative_map":
            fv_relative_map,

        "strong_map":
            strong_map,

        "strong_relative_map":
            strong_relative_map,

        "S_t":
            S_t_all,
    }


# =============================================================================
# SAVE CSV
# =============================================================================

def save_csv(
    rows,
):

    with open(
        TIME_CSV,
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

def plot_residual_map(
    xi,
    tD,
    relative_map,
):

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    im = ax.imshow(
        np.abs(
            relative_map
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
        r"TOF coordinate $\xi$"
    )

    ax.set_ylabel(
        r"Dimensionless time $t_D$"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-2\n"
        "Conservative Residual Map on Frozen SG7A Truth"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B2_Residual_Map.png",
        dpi=300,
    )

    plt.close(fig)


def plot_residual_vs_time(
    rows,
):

    tD = np.array([
        r[
            "tD"
        ]
        for r in rows
    ])

    fv = np.array([
        r[
            "fv_relative_mae"
        ]
        for r in rows
    ])

    interior = np.array([
        (
            r[
                "fv_interior_relative_mae"
            ]
            if r[
                "fv_interior_relative_mae"
            ]
            is not None
            else np.nan
        )
        for r in rows
    ])

    front = np.array([
        (
            r[
                "fv_front_relative_mae"
            ]
            if r[
                "fv_front_relative_mae"
            ]
            is not None
            else np.nan
        )
        for r in rows
    ])

    fig, ax = plt.subplots(
        figsize=(9, 6)
    )

    ax.semilogy(
        tD,
        np.maximum(
            fv,
            1.0e-12,
        ),
        label="Whole domain",
    )

    ax.semilogy(
        tD,
        np.maximum(
            interior,
            1.0e-12,
        ),
        label="Interior",
    )

    ax.semilogy(
        tD,
        np.maximum(
            front,
            1.0e-12,
        ),
        label="High-gradient region",
    )

    ax.set_xlabel(
        r"$t_D$"
    )

    ax.set_ylabel(
        "Mean absolute relative residual"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-2\n"
        "FV Residual vs Dimensionless Time"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B2_Residual_vs_tD.png",
        dpi=300,
    )

    plt.close(fig)


def plot_residual_vs_xi(
    xi,
    relative_map,
):

    # Ignore first and final saved time when averaging because
    # one-sided time derivatives are used there.
    if relative_map.shape[0] > 2:

        data = relative_map[
            1:-1
        ]

    else:

        data = relative_map

    mean_abs = np.mean(
        np.abs(
            data
        ),
        axis=0,
    )

    fig, ax = plt.subplots(
        figsize=(9, 6)
    )

    ax.semilogy(
        xi,
        np.maximum(
            mean_abs,
            1.0e-12,
        ),
    )

    ax.set_xlabel(
        r"TOF coordinate $\xi$"
    )

    ax.set_ylabel(
        "Time-averaged absolute relative residual"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-2\n"
        "FV Residual vs TOF Coordinate"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B2_Residual_vs_Xi.png",
        dpi=300,
    )

    plt.close(fig)


def plot_truth_profile_check(
    xi,
    tD,
    S,
    relative_map,
):

    targets = [
        0.10,
        0.50,
        1.00,
        2.00,
        5.00,
    ]

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(
            9,
            9,
        ),
    )

    ax1 = axes[0]

    for target in targets:

        if target > tD[-1]:

            continue

        idx = int(
            np.argmin(
                np.abs(
                    tD - target
                )
            )
        )

        ax1.plot(
            xi,
            S[idx],
            label=(
                rf"$t_D={tD[idx]:.2f}$"
            ),
        )

    ax1.set_xlabel(
        r"$\xi$"
    )

    ax1.set_ylabel(
        "Saturation"
    )

    ax1.set_title(
        "Frozen SG7A Master Profiles"
    )

    ax1.legend()

    ax2 = axes[1]

    mean_abs_residual = np.mean(
        np.abs(
            relative_map[
                1:-1
            ]
        ),
        axis=0,
    )

    ax2.plot(
        xi,
        mean_abs_residual,
    )

    ax2.set_xlabel(
        r"$\xi$"
    )

    ax2.set_ylabel(
        "Mean |relative FV residual|"
    )

    ax2.set_title(
        "Residual Seen by Proposed SG7B Physics Loss"
    )

    fig.suptitle(
        "PAD-Stream V15-SG7B-2 — Truth/Residual Verification",
        fontsize=14,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B2_Truth_Profile_Check.png",
        dpi=300,
    )

    plt.close(fig)


# =============================================================================
# VALIDATION
# =============================================================================

def validate(
    rows,
):
    """
    The master file stores snapshots rather than each internal SG7A timestep,
    so we do NOT demand machine-zero local residuals.

    We evaluate central-time snapshots only, excluding:
      - tD = 0
      - final one-sided snapshot
    """

    core = rows[
        1:-1
    ]

    fv_relative = np.array([
        r[
            "fv_relative_mae"
        ]
        for r in core
    ])

    interior_relative = np.array([
        r[
            "fv_interior_relative_mae"
        ]
        for r in core
        if r[
            "fv_interior_relative_mae"
        ]
        is not None
    ])

    integrated = np.array([
        r[
            "fv_integrated_residual"
        ]
        for r in core
    ])

    strong_relative = np.array([
        r[
            "strong_relative_mae"
        ]
        for r in core
    ])

    mean_fv_relative = float(
        np.mean(
            fv_relative
        )
    )

    median_fv_relative = float(
        np.median(
            fv_relative
        )
    )

    mean_interior_relative = float(
        np.mean(
            interior_relative
        )
    )

    mean_integrated_abs = float(
        np.mean(
            np.abs(
                integrated
            )
        )
    )

    mean_integrated_signed = float(
        np.mean(
            integrated
        )
    )

    mean_strong_relative = float(
        np.mean(
            strong_relative
        )
    )

    checks = [
        (
            "FV residual finite",
            np.all(
                np.isfinite(
                    fv_relative
                )
            ),
        ),

        (
            "Interior FV residual finite",
            np.all(
                np.isfinite(
                    interior_relative
                )
            ),
        ),

        (
            "Integrated residual finite",
            np.all(
                np.isfinite(
                    integrated
                )
            ),
        ),

        (
            "Mean interior relative FV residual < 1%",
            mean_interior_relative
            < 0.01,
        ),

        (
            "Mean whole-domain relative FV residual < 5%",
            mean_fv_relative
            < 0.05,
        ),

        (
            "No strong systematic integrated-residual bias",
            abs(
                mean_integrated_signed
            )
            <
            max(
                1.0e-3,
                0.25
                * mean_integrated_abs,
            ),
        ),
    ]

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-2 RESIDUAL VALIDATION"
    )

    print(
        "=" * 78
    )

    all_passed = True

    for description, passed in checks:

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

    print(
        f"Mean FV relative residual       : "
        f"{mean_fv_relative:.6e}"
    )

    print(
        f"Median FV relative residual     : "
        f"{median_fv_relative:.6e}"
    )

    print(
        f"Mean interior FV relative       : "
        f"{mean_interior_relative:.6e}"
    )

    print(
        f"Mean |integrated FV residual|   : "
        f"{mean_integrated_abs:.6e}"
    )

    print(
        f"Mean signed integrated residual : "
        f"{mean_integrated_signed:.6e}"
    )

    print(
        f"Mean strong-form relative       : "
        f"{mean_strong_relative:.6e}"
    )

    if not all_passed:

        raise RuntimeError(
            "V15-SG7B-2 residual verification failed. "
            "Do not train SG7B yet."
        )

    print(
        "\n"
        "V15-SG7B-2 RESIDUAL VERIFICATION: PASS"
    )

    return {
        "mean_fv_relative_residual":
            mean_fv_relative,

        "median_fv_relative_residual":
            median_fv_relative,

        "mean_interior_fv_relative_residual":
            mean_interior_relative,

        "mean_absolute_integrated_fv_residual":
            mean_integrated_abs,

        "mean_signed_integrated_fv_residual":
            mean_integrated_signed,

        "mean_strong_form_relative_residual":
            mean_strong_relative,
    }


# =============================================================================
# SAVE SUMMARY
# =============================================================================

def save_summary(
    xi,
    master_tD,
    master_S,
    validation,
):

    summary = {
        "milestone":
            "V15-SG7B-2",

        "description":
            (
                "Conservative PI-RNN physics residual "
                "verification against frozen SG7A truth"
            ),

        "status":
            "PASS",

        "source":
            "Frozen V15-SG7A master transport solution",

        "grid": {
            "xi_nodes":
                int(
                    len(xi)
                ),

            "time_snapshots":
                int(
                    len(
                        master_tD
                    )
                ),

            "solution_shape":
                list(
                    master_S.shape
                ),
        },

        "physics": {
            "Nc":
                NC,

            "Pe_c":
                PE_C,

            "lambda_bc":
                LAMBDA_BC,

            "phi":
                POROSITY,

            "velocity":
                "uD = exp(Nc xi)",

            "primary_residual":
                (
                    "dS/dtD + div(F_Godunov) "
                    "- div(G_capillary)"
                ),

            "diagnostic_residual":
                (
                    "dS/dtD + "
                    "uD(df/dxi + Nc f) "
                    "- (phi/Pe_c)d/dxi[D_tilde dS/dxi]"
                ),
        },

        "validation":
            validation,

        "training_decision":
            (
                "If PASS, the conservative finite-volume residual "
                "is approved as the primary SG7B PI-RNN physics loss."
            ),

        "next_milestone":
            (
                "V15-SG7B-3 - reference-case PI-RNN "
                "dataset and training design"
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
        "PAD-Stream Version 15-SG7B-2"
    )

    print(
        "Conservative PI-RNN Residual Verification"
    )

    print(
        "=" * 78
    )

    # -------------------------------------------------------------------------
    # LOAD
    # -------------------------------------------------------------------------

    (
        xi,
        master_tD,
        master_S,
    ) = load_sg7a()

    print(
        "\nFROZEN SG7A MASTER DATABASE"
    )

    print(
        f"  xi nodes                : "
        f"{len(xi)}"
    )

    print(
        f"  tD snapshots            : "
        f"{len(master_tD)}"
    )

    print(
        f"  saturation shape        : "
        f"{master_S.shape}"
    )

    print(
        f"  tD range                : "
        f"{master_tD[0]:.6f} -> "
        f"{master_tD[-1]:.6f}"
    )

    print(
        f"  xi range                : "
        f"{xi[0]:.6f} -> "
        f"{xi[-1]:.6f}"
    )

    print(
        "\nPHYSICS"
    )

    print(
        f"  Nc                      : "
        f"{NC:.3f}"
    )

    print(
        f"  Pe_c                    : "
        f"{PE_C:.3f}"
    )

    print(
        f"  lambda_BC               : "
        f"{LAMBDA_BC:.3f}"
    )

    print(
        f"  phi                     : "
        f"{POROSITY:.3f}"
    )

    print(
        "\nEvaluating frozen SG7A truth..."
    )

    result = analyze_residuals(
        xi,
        master_tD,
        master_S,
    )

    rows = (
        result[
            "rows"
        ]
    )

    # -------------------------------------------------------------------------
    # VALIDATE
    # -------------------------------------------------------------------------

    validation = validate(
        rows
    )

    # -------------------------------------------------------------------------
    # SAVE
    # -------------------------------------------------------------------------

    save_csv(
        rows
    )

    plot_residual_map(
        xi,
        master_tD,
        result[
            "fv_relative_map"
        ],
    )

    plot_residual_vs_time(
        rows
    )

    plot_residual_vs_xi(
        xi,
        result[
            "fv_relative_map"
        ],
    )

    plot_truth_profile_check(
        xi,
        master_tD,
        master_S,
        result[
            "fv_relative_map"
        ],
    )

    save_summary(
        xi,
        master_tD,
        master_S,
        validation,
    )

    print(
        "\nOUTPUTS"
    )

    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print(
        "\nGenerated:"
    )

    print(
        "  PAD_Stream_V15SG7B2_Summary.json"
    )

    print(
        "  V15SG7B2_Residual_ByTime.csv"
    )

    print(
        "  V15SG7B2_Residual_Map.png"
    )

    print(
        "  V15SG7B2_Residual_vs_Xi.png"
    )

    print(
        "  V15SG7B2_Residual_vs_tD.png"
    )

    print(
        "  V15SG7B2_Truth_Profile_Check.png"
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-2 COMPLETED SUCCESSFULLY"
    )

    print(
        "Proposed SG7B physics loss:"
    )

    print(
        "CONSERVATIVE FINITE-VOLUME RESIDUAL"
    )

    print(
        "\nNext milestone:"
    )

    print(
        "V15-SG7B-3 — Reference-case "
        "PI-RNN dataset and training design"
    )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()