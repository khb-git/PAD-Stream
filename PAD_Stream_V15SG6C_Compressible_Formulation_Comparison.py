from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG6C
# Compressible Buckley-Leverett Formulation Comparison
#
# PURPOSE
# -------
# Formally compare two compressible BL formulations:
#
#   A) Travel-time transform formulation
#
#       dS/dt_D + u_D(x_D) df/dx_D = 0
#
#      with
#
#       u_D(x_D) = exp(Nc x_D)
#
#      and analytical coordinate transform
#
#       y_D = [1 - exp(-Nc x_D)] / Nc
#
#
#   B) Conservative Godunov formulation
#
#       dS/dt_D + d[u_D(x_D) f(S)]/dx_D = 0
#
#
# PAD-STREAM DECISION
# -------------------
# Conservative Godunov is the production compressible formulation for SG7.
#
# The transform formulation is retained as:
#
#   - analytical/reference model
#   - limiting-case diagnostic
#   - physics comparison
#
#
# IMPORTANT
# ---------
# SG6C contains COMPRESSIBILITY ONLY.
#
# Capillary pressure is intentionally excluded so the difference between
# the two advective governing equations can be isolated cleanly.
#
# SG1-SG6 remain frozen and untouched.
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG6C"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG6C_Summary.json"
)

METRICS_CSV = (
    OUTPUT_DIR
    / "V15SG6C_Metrics.csv"
)

CONVERGENCE_CSV = (
    OUTPUT_DIR
    / "V15SG6C_Godunov_GridConvergence.csv"
)


# =============================================================================
# ROCK / FLUID PARAMETERS
# =============================================================================

# These remain consistent with the established BL benchmark family.

SWC = 0.20
SOR = 0.20

SW_INIT = SWC
SW_INJ = 1.0 - SOR

KRW_MAX = 0.80
KRO_MAX = 0.80

NW = 2.0
NO = 2.0

MU_DISP = 0.50
MU_RES = 5.00

SATURATION_SPAN = (
    SW_INJ - SW_INIT
)

EPS = 1.0e-14


# =============================================================================
# COMPARISON MATRIX
# =============================================================================

NC_VALUES = [
    0.00,
    0.05,
    0.10,
    0.20,
    0.30,
]

NX_VALUES = [
    201,
    401,
    801,
    1601,
]

# Primary comparison time.
#
# With the current rock/fluid system, this is chosen so the incompressible
# shock remains inside the domain and the comparison remains pre-breakthrough.
TD_PRIMARY = 0.15

# Additional times used for selected diagnostics.
TD_VALUES = [
    0.05,
    0.10,
    0.15,
    0.20,
]

CFL = 0.45


# =============================================================================
# RELATIVE PERMEABILITY
# =============================================================================

def effective_saturation(sw):
    """
    Normalized displacing-phase saturation:

        Se = (Sw - Swc) / (1 - Swc - Sor)
    """

    sw = np.asarray(
        sw,
        dtype=float,
    )

    se = (
        (sw - SWC)
        /
        (
            1.0
            - SWC
            - SOR
        )
    )

    return np.clip(
        se,
        0.0,
        1.0,
    )


def relative_permeability(sw):
    """
    Corey relative permeabilities.
    """

    se = effective_saturation(
        sw
    )

    kr_disp = (
        KRW_MAX
        * se ** NW
    )

    kr_res = (
        KRO_MAX
        * (1.0 - se) ** NO
    )

    return (
        kr_disp,
        kr_res,
    )


# =============================================================================
# FRACTIONAL FLOW
# =============================================================================

def fractional_flow(sw):
    """
    Fractional flow of the displacing phase.
    """

    kr_d, kr_r = (
        relative_permeability(
            sw
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


def fractional_flow_derivative(sw):
    """
    Numerical derivative df/dS.

    A central finite-difference derivative is sufficient here because
    the analytical reference grid is extremely dense.
    """

    sw = np.asarray(
        sw,
        dtype=float,
    )

    h = (
        1.0e-5
        * SATURATION_SPAN
    )

    sw_plus = np.clip(
        sw + h,
        SW_INIT,
        SW_INJ,
    )

    sw_minus = np.clip(
        sw - h,
        SW_INIT,
        SW_INJ,
    )

    denominator = (
        sw_plus
        - sw_minus
    )

    derivative = (
        fractional_flow(sw_plus)
        - fractional_flow(sw_minus)
    ) / (
        denominator
        + EPS
    )

    return derivative


# =============================================================================
# WELGE SHOCK CONSTRUCTION
# =============================================================================

def compute_welge_shock():
    """
    Robust Welge tangent construction.

    For the initial state SW_INIT, maximize the secant slope:

        [f(S) - f(S_i)] / [S - S_i]

    This is numerically more robust than directly searching for the
    equality

        df/dS = secant slope

    because the latter admits a spurious root arbitrarily close to S_i.
    """

    sw = np.linspace(
        SW_INIT,
        SW_INJ,
        50001,
    )

    fw = fractional_flow(
        sw
    )

    f_initial = float(
        fractional_flow(
            np.array(
                [SW_INIT]
            )
        )[0]
    )

    secant = np.full_like(
        sw,
        -np.inf,
        dtype=float,
    )

    valid = (
        sw > SW_INIT
    )

    secant[valid] = (
        fw[valid]
        - f_initial
    ) / (
        sw[valid]
        - SW_INIT
    )

    idx = int(
        np.argmax(
            secant
        )
    )

    sw_shock = float(
        sw[idx]
    )

    fw_shock = float(
        fw[idx]
    )

    shock_speed = float(
        secant[idx]
    )

    derivative_shock = float(
        fractional_flow_derivative(
            np.array(
                [sw_shock]
            )
        )[0]
    )

    tangent_error = abs(
        derivative_shock
        - shock_speed
    )

    return {
        "sw_shock":
            sw_shock,

        "fw_shock":
            fw_shock,

        "shock_speed":
            shock_speed,

        "dfds_shock":
            derivative_shock,

        "tangent_error":
            tangent_error,
    }


WELGE = compute_welge_shock()

SW_SHOCK = (
    WELGE["sw_shock"]
)

FW_SHOCK = (
    WELGE["fw_shock"]
)

SHOCK_SPEED = (
    WELGE["shock_speed"]
)


# =============================================================================
# TRANSFORM FORMULATION
# =============================================================================

def y_of_x(xd, nc):
    """
    Travel-time coordinate:

        y_D = [1 - exp(-Nc x_D)] / Nc

    Exact incompressible limit:

        Nc -> 0  =>  y_D = x_D

    expm1 is used for numerical stability.
    """

    xd = np.asarray(
        xd,
        dtype=float,
    )

    if abs(nc) < 1.0e-12:

        return xd.copy()

    return (
        -np.expm1(
            -nc * xd
        )
        / nc
    )


def x_of_y(yd, nc):
    """
    Inverse transform:

        x_D = -ln(1 - Nc y_D)/Nc

    Exact limit:

        Nc -> 0  =>  x_D = y_D
    """

    yd = np.asarray(
        yd,
        dtype=float,
    )

    if abs(nc) < 1.0e-12:

        return yd.copy()

    argument = np.clip(
        nc * yd,
        None,
        1.0 - 1.0e-14,
    )

    return (
        -np.log1p(
            -argument
        )
        / nc
    )


def transformed_domain_length(nc):
    """
    Length of x_D = 1 domain in transformed y_D coordinates.
    """

    return float(
        y_of_x(
            1.0,
            nc,
        )
    )


def transform_solution(
    td,
    nc,
    nx,
):
    """
    Entropy-correct analytical Buckley-Leverett solution in transformed
    y_D coordinates, mapped back onto x_D.

    The rarefaction branch spans:

        S_shock <= S <= S_inj

    and is defined by

        y_D / t_D = df/dS.

    Ahead of the shock:

        S = S_initial.
    """

    xd = np.linspace(
        0.0,
        1.0,
        nx,
    )

    yd = y_of_x(
        xd,
        nc,
    )

    eta = (
        yd
        / max(
            td,
            EPS,
        )
    )

    sw = np.full(
        nx,
        SW_INIT,
        dtype=float,
    )

    # Dense rarefaction saturation branch.
    sw_branch = np.linspace(
        SW_SHOCK,
        SW_INJ,
        50001,
    )

    characteristic_speed = (
        fractional_flow_derivative(
            sw_branch
        )
    )

    # On the physical rarefaction branch, df/dS runs from ~shock speed
    # at S_shock toward ~0 at the injected saturation.
    #
    # Sorting lets np.interp safely recover S(eta).
    order = np.argsort(
        characteristic_speed
    )

    speed_sorted = (
        characteristic_speed[
            order
        ]
    )

    saturation_sorted = (
        sw_branch[
            order
        ]
    )

    behind_shock = (
        eta
        <= SHOCK_SPEED
    )

    if np.any(
        behind_shock
    ):

        eta_local = np.clip(
            eta[
                behind_shock
            ],
            speed_sorted.min(),
            speed_sorted.max(),
        )

        sw[
            behind_shock
        ] = np.interp(
            eta_local,
            speed_sorted,
            saturation_sorted,
        )

    # Exact injector state.
    sw[0] = SW_INJ

    return (
        xd,
        sw,
    )


# =============================================================================
# DIMENSIONLESS VELOCITY MODEL
# =============================================================================

def velocity_dimensionless(
    xd,
    nc,
):
    """
    Prescribed compressible velocity field:

        u_D(x_D) = exp(Nc x_D)
    """

    return np.exp(
        nc
        * np.asarray(
            xd,
            dtype=float,
        )
    )


# =============================================================================
# GODUNOV FLUX
# =============================================================================

def godunov_fractional_flux(
    sw_left,
    sw_right,
    n_sample=100,
):
    """
    Entropy-correct scalar Godunov flux.

    This mirrors the validated V14 logic:

    if S_L <= S_R:
        min f(S) over [S_L,S_R]

    else:
        max f(S) over [S_R,S_L]
    """

    if abs(
        sw_left
        - sw_right
    ) < 1.0e-12:

        return float(
            fractional_flow(
                np.array(
                    [sw_left]
                )
            )[0]
        )

    saturation_samples = np.linspace(
        min(
            sw_left,
            sw_right,
        ),
        max(
            sw_left,
            sw_right,
        ),
        n_sample,
    )

    flux_samples = (
        fractional_flow(
            saturation_samples
        )
    )

    if sw_left <= sw_right:

        return float(
            np.min(
                flux_samples
            )
        )

    return float(
        np.max(
            flux_samples
        )
    )


# =============================================================================
# CONSERVATIVE GODUNOV SOLVER
# =============================================================================

def godunov_solution(
    td,
    nc,
    nx,
    cfl=CFL,
):
    """
    Finite-volume solution of:

        dS/dt_D
        +
        d[u_D(x_D) f(S)]/dx_D
        =
        0

    The unknowns are CELL AVERAGES.

    Face flux:

        F_{i+1/2}
        =
        u_D(x_{i+1/2})
        *
        F_Godunov(S_i,S_{i+1})

    Boundary conditions:

        left:
            injected saturation / imposed inflow

        right:
            open outflow

    Returns:

        x_cell
        S_cell
        diagnostics
    """

    if nx < 3:

        raise ValueError(
            "nx must be at least 3."
        )

    dx = (
        1.0 / nx
    )

    x_cell = (
        np.arange(nx)
        + 0.5
    ) * dx

    x_face = np.linspace(
        0.0,
        1.0,
        nx + 1,
    )

    u_cell = (
        velocity_dimensionless(
            x_cell,
            nc,
        )
    )

    u_face = (
        velocity_dimensionless(
            x_face,
            nc,
        )
    )

    sw = np.full(
        nx,
        SW_INIT,
        dtype=float,
    )

    # -------------------------------------------------------------------------
    # CFL
    # -------------------------------------------------------------------------

    saturation_scan = np.linspace(
        SW_INIT,
        SW_INJ,
        5001,
    )

    max_dfds = float(
        np.max(
            np.abs(
                fractional_flow_derivative(
                    saturation_scan
                )
            )
        )
    )

    max_characteristic_speed = (
        float(
            np.max(
                u_cell
            )
        )
        * max_dfds
    )

    dt_cfl = (
        cfl
        * dx
        / (
            max_characteristic_speed
            + EPS
        )
    )

    n_steps = max(
        1,
        int(
            np.ceil(
                td
                / dt_cfl
            )
        ),
    )

    dt = (
        td
        / n_steps
    )

    # Track exact FV mass change.
    storage_initial = float(
        np.sum(
            sw - SW_INIT
        )
        * dx
    )

    cumulative_inflow = 0.0
    cumulative_outflow = 0.0

    # -------------------------------------------------------------------------
    # TIME MARCH
    # -------------------------------------------------------------------------

    for _ in range(
        n_steps
    ):

        flux = np.zeros(
            nx + 1,
            dtype=float,
        )

        # -------------------------------------------------------------
        # LEFT / INJECTION FACE
        # -------------------------------------------------------------

        flux[0] = (
            u_face[0]
            * godunov_fractional_flux(
                SW_INJ,
                sw[0],
            )
        )

        # -------------------------------------------------------------
        # INTERNAL FACES
        # -------------------------------------------------------------

        for face in range(
            1,
            nx,
        ):

            f_god = (
                godunov_fractional_flux(
                    sw[
                        face - 1
                    ],
                    sw[
                        face
                    ],
                )
            )

            flux[face] = (
                u_face[face]
                * f_god
            )

        # -------------------------------------------------------------
        # RIGHT / OPEN OUTFLOW FACE
        # -------------------------------------------------------------

        flux[nx] = (
            u_face[nx]
            * fractional_flow(
                np.array(
                    [sw[-1]]
                )
            )[0]
        )

        # -------------------------------------------------------------
        # CONSERVATIVE FV UPDATE
        # -------------------------------------------------------------

        sw_new = (
            sw
            -
            (
                dt
                / dx
            )
            * (
                flux[1:]
                -
                flux[:-1]
            )
        )

        # Very small floating-point excursions may occur.
        #
        # Large clipping would violate conservation and therefore
        # should be caught by the material-balance diagnostic.
        sw = np.clip(
            sw_new,
            SW_INIT,
            SW_INJ,
        )

        cumulative_inflow += (
            flux[0]
            * dt
        )

        cumulative_outflow += (
            flux[-1]
            * dt
        )

    storage_final = float(
        np.sum(
            sw - SW_INIT
        )
        * dx
    )

    net_boundary_input = (
        cumulative_inflow
        - cumulative_outflow
    )

    conservation_error = (
        storage_final
        - storage_initial
        - net_boundary_input
    )

    relative_conservation_error = (
        abs(
            conservation_error
        )
        /
        max(
            abs(
                net_boundary_input
            ),
            1.0e-14,
        )
    )

    diagnostics = {
        "dx":
            float(dx),

        "dt":
            float(dt),

        "n_steps":
            int(n_steps),

        "max_characteristic_speed":
            float(
                max_characteristic_speed
            ),

        "storage_initial":
            float(
                storage_initial
            ),

        "storage_final":
            float(
                storage_final
            ),

        "cumulative_inflow":
            float(
                cumulative_inflow
            ),

        "cumulative_outflow":
            float(
                cumulative_outflow
            ),

        "net_boundary_input":
            float(
                net_boundary_input
            ),

        "conservation_error":
            float(
                conservation_error
            ),

        "relative_conservation_error":
            float(
                relative_conservation_error
            ),
    }

    return (
        x_cell,
        sw,
        diagnostics,
    )


# =============================================================================
# COMMON GRID INTERPOLATION
# =============================================================================

def interpolate_profile(
    x,
    sw,
    x_common,
):
    """
    Interpolate profile onto comparison grid.
    """

    return np.interp(
        x_common,
        x,
        sw,
        left=sw[0],
        right=sw[-1],
    )


# =============================================================================
# FRONT POSITION
# =============================================================================

def front_target_saturation():
    """
    Mid-jump front criterion between initial saturation and Welge shock state.

    This is less sensitive to first-order Godunov rounding than using
    the top of the smeared front.
    """

    return (
        SW_INIT
        +
        0.5
        * (
            SW_SHOCK
            - SW_INIT
        )
    )


def front_position_midjump(
    x,
    sw,
):
    """
    Locate the first downward crossing of the mid-jump saturation.
    """

    target = (
        front_target_saturation()
    )

    x = np.asarray(
        x,
        dtype=float,
    )

    sw = np.asarray(
        sw,
        dtype=float,
    )

    crossing = np.where(
        sw <= target
    )[0]

    if len(
        crossing
    ) == 0:

        return 1.0

    idx = int(
        crossing[0]
    )

    if idx == 0:

        return float(
            x[0]
        )

    x1 = x[
        idx - 1
    ]

    x2 = x[idx]

    s1 = sw[
        idx - 1
    ]

    s2 = sw[idx]

    if abs(
        s2 - s1
    ) < EPS:

        return float(
            x2
        )

    fraction = (
        target
        - s1
    ) / (
        s2
        - s1
    )

    return float(
        x1
        +
        fraction
        * (
            x2 - x1
        )
    )


# =============================================================================
# STORAGE
# =============================================================================

def integrated_excess_saturation(
    x,
    sw,
):
    """
    Integral:

        integral_0^1 [S(x)-S_initial] dx
    """

    return float(
        np.trapezoid(
            sw - SW_INIT,
            x,
        )
    )


def cell_average_excess_saturation(
    sw,
):
    """
    Exact FV storage for uniform unit-length grid of cell averages.
    """

    return float(
        np.mean(
            sw - SW_INIT
        )
    )


# =============================================================================
# COMPARISON METRICS
# =============================================================================

def calculate_metrics(
    nc,
    td,
    nx,
):

    # -------------------------------------------------------------------------
    # TRANSFORM
    # -------------------------------------------------------------------------

    x_transform, sw_transform = (
        transform_solution(
            td,
            nc,
            nx,
        )
    )

    # -------------------------------------------------------------------------
    # GODUNOV
    # -------------------------------------------------------------------------

    (
        x_godunov,
        sw_godunov,
        godunov_diag,
    ) = godunov_solution(
        td,
        nc,
        nx,
    )

    # -------------------------------------------------------------------------
    # COMMON HIGH-RESOLUTION GRID
    # -------------------------------------------------------------------------

    n_common = max(
        8001,
        4 * nx,
    )

    x_common = np.linspace(
        0.0,
        1.0,
        n_common,
    )

    st = interpolate_profile(
        x_transform,
        sw_transform,
        x_common,
    )

    sg = interpolate_profile(
        x_godunov,
        sw_godunov,
        x_common,
    )

    error = (
        sg - st
    )

    # -------------------------------------------------------------------------
    # NORMS
    # -------------------------------------------------------------------------

    l1 = float(
        np.trapezoid(
            np.abs(
                error
            ),
            x_common,
        )
    )

    l2 = float(
        np.sqrt(
            np.trapezoid(
                error ** 2,
                x_common,
            )
        )
    )

    linf = float(
        np.max(
            np.abs(
                error
            )
        )
    )

    # -------------------------------------------------------------------------
    # FRONT
    # -------------------------------------------------------------------------

    front_transform = (
        front_position_midjump(
            x_transform,
            sw_transform,
        )
    )

    front_godunov = (
        front_position_midjump(
            x_godunov,
            sw_godunov,
        )
    )

    # -------------------------------------------------------------------------
    # STORAGE
    # -------------------------------------------------------------------------

    storage_transform = (
        integrated_excess_saturation(
            x_transform,
            sw_transform,
        )
    )

    storage_godunov = (
        cell_average_excess_saturation(
            sw_godunov
        )
    )

    return {
        "Nc":
            float(nc),

        "tD":
            float(td),

        "nx":
            int(nx),

        "L1_transform_vs_godunov":
            float(l1),

        "L2_transform_vs_godunov":
            float(l2),

        "Linf_transform_vs_godunov":
            float(linf),

        "front_transform":
            float(
                front_transform
            ),

        "front_godunov":
            float(
                front_godunov
            ),

        "front_difference":
            float(
                front_godunov
                - front_transform
            ),

        "storage_transform":
            float(
                storage_transform
            ),

        "storage_godunov":
            float(
                storage_godunov
            ),

        "storage_difference":
            float(
                storage_godunov
                - storage_transform
            ),

        "godunov_net_boundary_input":
            float(
                godunov_diag[
                    "net_boundary_input"
                ]
            ),

        "godunov_conservation_error":
            float(
                godunov_diag[
                    "conservation_error"
                ]
            ),

        "godunov_relative_conservation_error":
            float(
                godunov_diag[
                    "relative_conservation_error"
                ]
            ),

        "godunov_steps":
            int(
                godunov_diag[
                    "n_steps"
                ]
            ),
    }


# =============================================================================
# FULL COMPARISON MATRIX
# =============================================================================

def run_comparison_matrix():

    rows = []

    print(
        "\nCOMPARISON MATRIX"
    )

    print(
        "-" * 78
    )

    for nc in NC_VALUES:

        print(
            f"\nNc = {nc:.3f}"
        )

        for nx in NX_VALUES:

            result = (
                calculate_metrics(
                    nc,
                    TD_PRIMARY,
                    nx,
                )
            )

            rows.append(
                result
            )

            print(
                f"  nx={nx:4d} | "
                f"L1={result['L1_transform_vs_godunov']:.6e} | "
                f"front Δ={result['front_difference']:+.6e} | "
                f"storage Δ={result['storage_difference']:+.6e} | "
                f"MB={result['godunov_relative_conservation_error']:.3e}"
            )

    return rows


# =============================================================================
# GODUNOV GRID CONVERGENCE
# =============================================================================

def godunov_grid_convergence(
    nc,
    td,
):

    nx_reference = (
        NX_VALUES[-1]
    )

    (
        x_ref,
        sw_ref,
        diag_ref,
    ) = godunov_solution(
        td,
        nc,
        nx_reference,
    )

    rows = []

    for nx in NX_VALUES[:-1]:

        (
            x,
            sw,
            diag,
        ) = godunov_solution(
            td,
            nc,
            nx,
        )

        sw_reference_on_grid = (
            np.interp(
                x,
                x_ref,
                sw_ref,
            )
        )

        error = (
            sw
            -
            sw_reference_on_grid
        )

        rows.append({
            "Nc":
                float(nc),

            "tD":
                float(td),

            "nx":
                int(nx),

            "reference_nx":
                int(
                    nx_reference
                ),

            "L1_to_1601":
                float(
                    np.mean(
                        np.abs(
                            error
                        )
                    )
                ),

            "L2_to_1601":
                float(
                    np.sqrt(
                        np.mean(
                            error ** 2
                        )
                    )
                ),

            "Linf_to_1601":
                float(
                    np.max(
                        np.abs(
                            error
                        )
                    )
                ),

            "relative_conservation_error":
                float(
                    diag[
                        "relative_conservation_error"
                    ]
                ),
        })

    return (
        rows,
        diag_ref,
    )


# =============================================================================
# CSV OUTPUT
# =============================================================================

def write_csv(
    path,
    rows,
):

    if not rows:

        return

    fieldnames = list(
        rows[0].keys()
    )

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# =============================================================================
# FIGURE — FRACTIONAL FLOW / WELGE
# =============================================================================

def plot_fractional_flow_welge():

    sw = np.linspace(
        SW_INIT,
        SW_INJ,
        2001,
    )

    fw = fractional_flow(
        sw
    )

    tangent = (
        SHOCK_SPEED
        * (
            sw
            - SW_INIT
        )
    )

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.plot(
        sw,
        fw,
        linewidth=2.2,
        label="Fractional flow",
    )

    ax.plot(
        sw,
        tangent,
        "--",
        linewidth=1.8,
        label="Welge tangent",
    )

    ax.scatter(
        [SW_SHOCK],
        [FW_SHOCK],
        s=70,
        label=(
            f"Shock: S={SW_SHOCK:.3f}"
        ),
    )

    ax.set_xlabel(
        "Displacing-phase saturation"
    )

    ax.set_ylabel(
        "Fractional flow"
    )

    ax.set_title(
        "PAD-Stream V15-SG6C\n"
        "Fractional Flow and Welge Construction"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG6C_Welge_Construction.png",
        dpi=300,
    )

    plt.close(fig)


# =============================================================================
# FIGURE — Nc = 0 NESTING
# =============================================================================

def plot_nc0_nesting():

    nx = 1601

    (
        xt,
        st,
    ) = transform_solution(
        TD_PRIMARY,
        0.0,
        nx,
    )

    (
        xg,
        sg,
        _,
    ) = godunov_solution(
        TD_PRIMARY,
        0.0,
        nx,
    )

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.plot(
        xt,
        st,
        linewidth=2.2,
        label="Analytical / transform",
    )

    ax.plot(
        xg,
        sg,
        "--",
        linewidth=1.8,
        label="Conservative Godunov",
    )

    ax.axhline(
        SW_SHOCK,
        linestyle=":",
        linewidth=1.4,
        label=(
            f"Shock saturation = {SW_SHOCK:.3f}"
        ),
    )

    ax.set_xlabel(
        r"$x_D$"
    )

    ax.set_ylabel(
        "Saturation"
    )

    ax.set_title(
        "PAD-Stream V15-SG6C\n"
        r"$N_c=0$ Incompressible Nesting Test"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG6C_Nc0_Nesting.png",
        dpi=300,
    )

    plt.close(fig)


# =============================================================================
# FIGURE — COMPRESSIBILITY PROFILES
# =============================================================================

def plot_compressibility_profiles():

    nx = 1601

    fig, axes = plt.subplots(
        2,
        2,
        figsize=(
            12,
            9,
        ),
    )

    for ax, nc in zip(
        axes.ravel(),
        NC_VALUES[1:],
    ):

        (
            xt,
            st,
        ) = transform_solution(
            TD_PRIMARY,
            nc,
            nx,
        )

        (
            xg,
            sg,
            _,
        ) = godunov_solution(
            TD_PRIMARY,
            nc,
            nx,
        )

        ax.plot(
            xt,
            st,
            linewidth=2.0,
            label="Transform",
        )

        ax.plot(
            xg,
            sg,
            "--",
            linewidth=1.8,
            label="Conservative Godunov",
        )

        ax.set_xlabel(
            r"$x_D$"
        )

        ax.set_ylabel(
            "Saturation"
        )

        ax.set_title(
            rf"$N_c={nc:.2f}$"
        )

        ax.legend()

    fig.suptitle(
        "PAD-Stream V15-SG6C\n"
        "Transform vs Conservative Compressible BL",
        fontsize=14,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG6C_Compressibility_Profiles.png",
        dpi=300,
    )

    plt.close(fig)


# =============================================================================
# FIGURE — GODUNOV GRID CONVERGENCE
# =============================================================================

def plot_godunov_grid_convergence():

    nc = 0.30

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    for nx in NX_VALUES:

        (
            x,
            sw,
            _,
        ) = godunov_solution(
            TD_PRIMARY,
            nc,
            nx,
        )

        ax.plot(
            x,
            sw,
            label=(
                f"Nx={nx}"
            ),
        )

    ax.set_xlabel(
        r"$x_D$"
    )

    ax.set_ylabel(
        "Saturation"
    )

    ax.set_title(
        "PAD-Stream V15-SG6C\n"
        r"Conservative Godunov Grid Convergence — $N_c=0.30$"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG6C_Godunov_GridConvergence.png",
        dpi=300,
    )

    plt.close(fig)


# =============================================================================
# FIGURE — FRONT POSITION VS Nc
# =============================================================================

def plot_front_position_vs_nc():

    nx = 1601

    transform_front = []
    godunov_front = []

    for nc in NC_VALUES:

        (
            xt,
            st,
        ) = transform_solution(
            TD_PRIMARY,
            nc,
            nx,
        )

        (
            xg,
            sg,
            _,
        ) = godunov_solution(
            TD_PRIMARY,
            nc,
            nx,
        )

        transform_front.append(
            front_position_midjump(
                xt,
                st,
            )
        )

        godunov_front.append(
            front_position_midjump(
                xg,
                sg,
            )
        )

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.plot(
        NC_VALUES,
        transform_front,
        "o-",
        label="Transform",
    )

    ax.plot(
        NC_VALUES,
        godunov_front,
        "s--",
        label="Conservative Godunov",
    )

    ax.set_xlabel(
        r"Compressibility number $N_c$"
    )

    ax.set_ylabel(
        r"Front position $x_{D,f}$"
    )

    ax.set_title(
        "PAD-Stream V15-SG6C\n"
        "Front Position vs Compressibility"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG6C_FrontPosition_vs_Nc.png",
        dpi=300,
    )

    plt.close(fig)


# =============================================================================
# FIGURE — FORMULATION DIFFERENCE VS Nc
# =============================================================================

def plot_formulation_difference(
    rows,
):

    finest = [
        row
        for row in rows
        if row["nx"] == 1601
    ]

    nc = np.array([
        row["Nc"]
        for row in finest
    ])

    l1 = np.array([
        row[
            "L1_transform_vs_godunov"
        ]
        for row in finest
    ])

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.plot(
        nc,
        l1,
        "o-",
    )

    ax.set_xlabel(
        r"Compressibility number $N_c$"
    )

    ax.set_ylabel(
        r"$L_1$ profile difference"
    )

    ax.set_title(
        "PAD-Stream V15-SG6C\n"
        "Transform–Conservative Difference"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG6C_FormulationDifference_vs_Nc.png",
        dpi=300,
    )

    plt.close(fig)


# =============================================================================
# FIGURE — CONSERVATION ERROR
# =============================================================================

def plot_conservation_error(
    rows,
):

    finest = [
        row
        for row in rows
        if row["nx"] == 1601
    ]

    nc = np.array([
        row["Nc"]
        for row in finest
    ])

    error = np.array([
        row[
            "godunov_relative_conservation_error"
        ]
        for row in finest
    ])

    error = np.maximum(
        error,
        1.0e-18,
    )

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.semilogy(
        nc,
        error,
        "o-",
    )

    ax.set_xlabel(
        r"Compressibility number $N_c$"
    )

    ax.set_ylabel(
        "Relative material-balance error"
    )

    ax.set_title(
        "PAD-Stream V15-SG6C\n"
        "Conservative Godunov Material Balance"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG6C_Godunov_ConservationError.png",
        dpi=300,
    )

    plt.close(fig)


# =============================================================================
# VALIDATION
# =============================================================================

def validate(
    rows,
    convergence_rows,
):

    def row_for(
        nc,
        nx,
    ):

        return next(
            row
            for row in rows
            if (
                np.isclose(
                    row["Nc"],
                    nc,
                )
                and
                row["nx"] == nx
            )
        )

    nc0_201 = row_for(
        0.0,
        201,
    )

    nc0_1601 = row_for(
        0.0,
        1601,
    )

    nc30_1601 = row_for(
        0.30,
        1601,
    )

    conv_201 = next(
        row
        for row
        in convergence_rows
        if row["nx"] == 201
    )

    conv_801 = next(
        row
        for row
        in convergence_rows
        if row["nx"] == 801
    )

    finest = [
        row
        for row in rows
        if row["nx"] == 1601
    ]

    max_mb_error = max(
        row[
            "godunov_relative_conservation_error"
        ]
        for row in finest
    )

    checks = [
        (
            "Welge shock saturation lies inside mobile saturation interval",
            (
                SW_INIT
                <
                SW_SHOCK
                <
                SW_INJ
            ),
        ),

        (
            "Welge tangent derivative matches secant slope",
            WELGE[
                "tangent_error"
            ] < 5.0e-3,
        ),

        (
            "Nc=0 transform/Godunov L1 difference < 0.02",
            nc0_1601[
                "L1_transform_vs_godunov"
            ] < 0.02,
        ),

        (
            "Nc=0 transform/Godunov difference decreases with refinement",
            nc0_1601[
                "L1_transform_vs_godunov"
            ]
            <
            nc0_201[
                "L1_transform_vs_godunov"
            ],
        ),

        (
            "Godunov grid refinement reduces profile error",
            conv_801[
                "L1_to_1601"
            ]
            <
            conv_201[
                "L1_to_1601"
            ],
        ),

        (
            "Conservative Godunov material balance < 1e-8",
            max_mb_error
            < 1.0e-8,
        ),

        (
            "Nc=0.30 formulations remain measurably different",
            nc30_1601[
                "L1_transform_vs_godunov"
            ] > 1.0e-4,
        ),
    ]

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG6C VALIDATION"
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
        f"Nc=0, Nx=201 L1        : "
        f"{nc0_201['L1_transform_vs_godunov']:.6e}"
    )

    print(
        f"Nc=0, Nx=1601 L1       : "
        f"{nc0_1601['L1_transform_vs_godunov']:.6e}"
    )

    print(
        f"Nc=0.30, Nx=1601 L1    : "
        f"{nc30_1601['L1_transform_vs_godunov']:.6e}"
    )

    print(
        f"Max Godunov MB error    : "
        f"{max_mb_error:.6e}"
    )

    if not all_passed:

        raise RuntimeError(
            "V15-SG6C validation failed. "
            "Do not freeze SG6C."
        )

    print(
        "\nV15-SG6C FORMULATION VALIDATION: PASS"
    )

    return {
        "nc0_l1_nx201":
            float(
                nc0_201[
                    "L1_transform_vs_godunov"
                ]
            ),

        "nc0_l1_nx1601":
            float(
                nc0_1601[
                    "L1_transform_vs_godunov"
                ]
            ),

        "nc030_l1_nx1601":
            float(
                nc30_1601[
                    "L1_transform_vs_godunov"
                ]
            ),

        "maximum_godunov_relative_material_balance_error":
            float(
                max_mb_error
            ),
    }


# =============================================================================
# SUMMARY
# =============================================================================

def save_summary(
    rows,
    convergence_rows,
    validation,
    finest_reference_diag,
):

    finest_metrics = {}

    for row in rows:

        if row["nx"] == 1601:

            key = (
                f"Nc_{row['Nc']:.2f}"
            )

            finest_metrics[
                key
            ] = row

    summary = {
        "milestone":
            "V15-SG6C",

        "description":
            (
                "Compressible Buckley-Leverett "
                "formulation comparison"
            ),

        "status":
            "PASS",

        "scope":
            "compressibility only; no capillary pressure",

        "selected_pad_stream_formulation":
            "conservative Godunov",

        "reference_formulation":
            "analytical travel-time transform",

        "governing_equations": {
            "transform":
                (
                    "dS/dtD + "
                    "uD(xD) df/dxD = 0"
                ),

            "conservative":
                (
                    "dS/dtD + "
                    "d[uD(xD) f(S)]/dxD = 0"
                ),

            "velocity":
                "uD(xD) = exp(Nc xD)",

            "equation_difference":
                (
                    "d(uD f)/dxD = "
                    "uD df/dxD + Nc uD f"
                ),
        },

        "rock_fluid": {
            "Swc":
                SWC,

            "Sor":
                SOR,

            "krw_max":
                KRW_MAX,

            "kro_max":
                KRO_MAX,

            "nw":
                NW,

            "no":
                NO,

            "mu_displacing":
                MU_DISP,

            "mu_resident":
                MU_RES,
        },

        "Welge": {
            "shock_saturation":
                SW_SHOCK,

            "shock_fractional_flow":
                FW_SHOCK,

            "shock_speed":
                SHOCK_SPEED,

            "dfds_at_shock":
                WELGE[
                    "dfds_shock"
                ],

            "tangent_error":
                WELGE[
                    "tangent_error"
                ],
        },

        "Nc_values":
            NC_VALUES,

        "Nx_values":
            NX_VALUES,

        "primary_dimensionless_time":
            TD_PRIMARY,

        "finest_grid_metrics":
            finest_metrics,

        "godunov_grid_convergence_Nc_0p30":
            convergence_rows,

        "finest_reference_godunov_diagnostics":
            finest_reference_diag,

        "validation":
            validation,

        "physics_decision":
            (
                "Conservative Godunov advection is retained "
                "for PAD-Stream SG7 because it preserves the "
                "divergence-form transport equation and provides "
                "direct finite-volume material conservation. "
                "The travel-time transform remains an analytical "
                "reference and reduced compressibility model."
            ),

        "next_milestone":
            (
                "V15-SG7A - classical full conservative "
                "compressible + capillary transport "
                "in SGSim streamline TOF space"
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
        "PAD-Stream Version 15-SG6C"
    )

    print(
        "Compressible Buckley-Leverett Formulation Comparison"
    )

    print(
        "=" * 78
    )

    # -------------------------------------------------------------------------
    # PARAMETERS
    # -------------------------------------------------------------------------

    print(
        "\nROCK / FLUID"
    )

    print(
        f"  Swc                     : "
        f"{SWC:.3f}"
    )

    print(
        f"  Sor                     : "
        f"{SOR:.3f}"
    )

    print(
        f"  Saturation interval     : "
        f"{SW_INIT:.3f} - {SW_INJ:.3f}"
    )

    print(
        f"  nw / no                 : "
        f"{NW:.2f} / {NO:.2f}"
    )

    print(
        f"  krw_max / kro_max       : "
        f"{KRW_MAX:.2f} / {KRO_MAX:.2f}"
    )

    print(
        f"  mu_displacing           : "
        f"{MU_DISP:.3f}"
    )

    print(
        f"  mu_resident             : "
        f"{MU_RES:.3f}"
    )

    # -------------------------------------------------------------------------
    # WELGE
    # -------------------------------------------------------------------------

    print(
        "\nWELGE SHOCK"
    )

    print(
        f"  Shock saturation        : "
        f"{SW_SHOCK:.6f}"
    )

    print(
        f"  Shock fractional flow   : "
        f"{FW_SHOCK:.6f}"
    )

    print(
        f"  Shock speed             : "
        f"{SHOCK_SPEED:.6f}"
    )

    print(
        f"  df/dS at shock          : "
        f"{WELGE['dfds_shock']:.6f}"
    )

    print(
        f"  Tangent error           : "
        f"{WELGE['tangent_error']:.6e}"
    )

    # -------------------------------------------------------------------------
    # FORMULATIONS
    # -------------------------------------------------------------------------

    print(
        "\nFORMULATIONS"
    )

    print(
        "  Transform:"
    )

    print(
        "    dS/dtD + uD df/dxD = 0"
    )

    print(
        "\n  Conservative Godunov:"
    )

    print(
        "    dS/dtD + d(uD f)/dxD = 0"
    )

    print(
        "\n  Velocity:"
    )

    print(
        "    uD = exp(Nc xD)"
    )

    print(
        "\n  Conservative expansion:"
    )

    print(
        "    d(uD f)/dxD = "
        "uD df/dxD + Nc uD f"
    )

    # -------------------------------------------------------------------------
    # RUN COMPARISON
    # -------------------------------------------------------------------------

    rows = (
        run_comparison_matrix()
    )

    (
        convergence_rows,
        finest_reference_diag,
    ) = (
        godunov_grid_convergence(
            nc=0.30,
            td=TD_PRIMARY,
        )
    )

    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------

    validation = validate(
        rows,
        convergence_rows,
    )

    # -------------------------------------------------------------------------
    # SAVE TABLES
    # -------------------------------------------------------------------------

    write_csv(
        METRICS_CSV,
        rows,
    )

    write_csv(
        CONVERGENCE_CSV,
        convergence_rows,
    )

    # -------------------------------------------------------------------------
    # FIGURES
    # -------------------------------------------------------------------------

    plot_fractional_flow_welge()

    plot_nc0_nesting()

    plot_compressibility_profiles()

    plot_godunov_grid_convergence()

    plot_front_position_vs_nc()

    plot_formulation_difference(
        rows
    )

    plot_conservation_error(
        rows
    )

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------

    save_summary(
        rows,
        convergence_rows,
        validation,
        finest_reference_diag,
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
        "\nTables:"
    )

    print(
        "  V15SG6C_Metrics.csv"
    )

    print(
        "  V15SG6C_Godunov_GridConvergence.csv"
    )

    print(
        "\nFigures:"
    )

    print(
        "  V15SG6C_Welge_Construction.png"
    )

    print(
        "  V15SG6C_Nc0_Nesting.png"
    )

    print(
        "  V15SG6C_Compressibility_Profiles.png"
    )

    print(
        "  V15SG6C_Godunov_GridConvergence.png"
    )

    print(
        "  V15SG6C_FrontPosition_vs_Nc.png"
    )

    print(
        "  V15SG6C_FormulationDifference_vs_Nc.png"
    )

    print(
        "  V15SG6C_Godunov_ConservationError.png"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG6C_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG6C COMPLETED SUCCESSFULLY"
    )

    print(
        "Selected PAD-Stream compressible formulation:"
    )

    print(
        "CONSERVATIVE GODUNOV"
    )

    print(
        "\nTransform formulation retained as:"
    )

    print(
        "ANALYTICAL / REFERENCE COMPARATOR"
    )

    print(
        "\nNext milestone:"
    )

    print(
        "V15-SG7A — Classical full conservative "
        "compressible + capillary transport "
        "in SGSim TOF space"
    )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()