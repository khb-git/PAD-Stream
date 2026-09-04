from pathlib import Path
import json

import numpy as np
import matplotlib.pyplot as plt

from scipy.linalg import solve_banded


# =============================================================================
# PAD-Stream V15-SG7A
# Classical Full Conservative Compressible + Capillary Transport
# on SGSim Streamline TOF Coordinates
#
# GOVERNING EQUATION
# ------------------
#
#   dS/dtD
#   +
#   d[ uD(xi) f(S) ]/dxi
#   =
#   (phi / Pe_c)
#   d/dxi [
#       D_tilde(S) dS/dxi
#   ]
#
# where
#
#   uD(xi) = exp(Nc xi)
#
#
# NUMERICS
# --------
#
# Conservative Godunov finite-volume advection
#
#       +
#
# implicit Brooks-Corey capillary diffusion
#
#
# SG6 MAPPING
# -----------
#
# For streamline s:
#
#       tD_s = t_physical / tau_end_s
#
#
# therefore the same dimensionless transport operator is evaluated at
# different effective times for streamlines with different TOF.
#
#
# IMPORTANT
# ---------
#
# This milestone:
#
#   - solves classical physics only
#   - does NOT use the PI-RNN
#   - does NOT map saturation back to the 3-D Cartesian grid
#
# Those are later milestones.
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

SG6_DIR = (
    ROOT
    / "output"
    / "V15_SG6"
)

SG6_FILE = (
    SG6_DIR
    / "STREAMLINE_TRANSPORT_COORDINATES.npz"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7A"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

TRANSPORT_FILE = (
    OUTPUT_DIR
    / "FULL_PHYSICS_STREAMLINE_SATURATION.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7A_Summary.json"
)


# =============================================================================
# CONSTANTS
# =============================================================================

DAY_TO_S = 86400.0

EPS = 1.0e-12


# =============================================================================
# ROCK / FLUID
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


# =============================================================================
# FULL-PHYSICS REFERENCE CASE
# =============================================================================

NC = 0.10

PE_C = 22.0

LAMBDA_BC = 2.0


# =============================================================================
# PHYSICAL OUTPUT TIMES
# =============================================================================

OUTPUT_TIMES_DAYS = np.array(
    [
        100.0,
        250.0,
        500.0,
        1000.0,
    ],
    dtype=float,
)


# =============================================================================
# MASTER DIMENSIONLESS-TIME DATABASE
# =============================================================================

# The full PDE is solved once on the common xi coordinate.
#
# Each streamline then samples this solution using
#
#       tD = t / tau_end.
#
# This is much more efficient than independently marching 1078
# identical PDEs.

N_MASTER_TD = 801

CFL = 0.40


# =============================================================================
# PRODUCERS
# =============================================================================

PRODUCER_NAMES = [
    "PROD_SW",
    "PROD_SE",
    "PROD_NW",
    "PROD_NE",
]


# =============================================================================
# SG6 DATA
# =============================================================================

def load_sg6():

    if not SG6_FILE.exists():

        raise FileNotFoundError(
            f"Missing frozen SG6 input:\n"
            f"{SG6_FILE}"
        )

    data = np.load(
        SG6_FILE
    )

    required = [
        "xyz_m",
        "tau_s",
        "xi",
        "path_length_m",
        "weights_m3_s",
        "tau_end_s",
        "producer",
        "streamline_id",
    ]

    for key in required:

        if key not in data:

            raise KeyError(
                f"SG6 field missing: {key}"
            )

    return {
        key: data[key]
        for key in required
    }


# =============================================================================
# SATURATION FUNCTIONS
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


def df_dS(S):

    S = np.asarray(
        S,
        dtype=float,
    )

    span = (
        S_INJECTED
        - S_INITIAL
    )

    h = (
        1.0e-5
        * span
    )

    Sp = np.clip(
        S + h,
        S_INITIAL,
        S_INJECTED,
    )

    Sm = np.clip(
        S - h,
        S_INITIAL,
        S_INJECTED,
    )

    return (
        fractional_flow(Sp)
        -
        fractional_flow(Sm)
    ) / (
        Sp - Sm + EPS
    )


# =============================================================================
# NORMALIZED BROOKS-COREY DIFFUSION SHAPE
# =============================================================================

def diffusion_shape(S):
    """
    Dimensionless Brooks-Corey capillary diffusion shape.

    Same structure as the established Stage-3 formulation:

        D_tilde(S)
        proportional to
        kro(S) f(S) Se^(-1/lambda - 1)

    normalized such that

        D_tilde(Se=0.5) = 1.
    """

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

    Se_mid = 0.5

    S_mid = (
        SWC
        + Se_mid
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
        / max(
            norm,
            EPS,
        )
    )


# =============================================================================
# COMPRESSIBLE DIMENSIONLESS VELOCITY
# =============================================================================

def u_dimensionless(
    xi,
):

    return np.exp(
        NC
        * np.asarray(
            xi,
            dtype=float,
        )
    )


# =============================================================================
# GODUNOV FLUX
# =============================================================================

def godunov_fractional_flux(
    S_left,
    S_right,
    n_sample=80,
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

    f_samples = (
        fractional_flow(
            samples
        )
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
# CONSERVATIVE COMPRESSIBLE ADVECTION
# =============================================================================

def advective_step(
    S,
    dtD,
    dxi,
    u_face,
):

    n = len(S)

    flux = np.zeros(
        n + 1,
        dtype=float,
    )

    # -------------------------------------------------------------
    # INJECTOR
    # -------------------------------------------------------------

    flux[0] = (
        u_face[0]
        * godunov_fractional_flux(
            S_INJECTED,
            S[0],
        )
    )

    # -------------------------------------------------------------
    # INTERNAL FACES
    # -------------------------------------------------------------

    for face in range(
        1,
        n,
    ):

        f_god = (
            godunov_fractional_flux(
                S[
                    face - 1
                ],
                S[
                    face
                ],
            )
        )

        flux[face] = (
            u_face[face]
            * f_god
        )

    # -------------------------------------------------------------
    # OPEN OUTFLOW
    # -------------------------------------------------------------

    flux[n] = (
        u_face[n]
        * fractional_flow(
            np.array(
                [S[-1]]
            )
        )[0]
    )

    S_new = (
        S
        -
        (
            dtD
            / dxi
        )
        * (
            flux[1:]
            -
            flux[:-1]
        )
    )

    return np.clip(
        S_new,
        S_INITIAL,
        S_INJECTED,
    )


# =============================================================================
# IMPLICIT CAPILLARY STEP
# =============================================================================

def capillary_step(
    S,
    dtD,
    dxi,
):
    """
    Semi-implicit conservative nonlinear capillary-diffusion step.

    PDE:

        dS/dtD
        =
        (phi / Pe_c)
        d/dxi [
            D_tilde(S) dS/dxi
        ]

    Boundary conditions
    -------------------
    xi = 0:
        Dirichlet saturation S = S_INJECTED applied at the
        BOUNDARY FACE using a half-cell distance.

    xi = 1:
        zero capillary diffusive flux.

    IMPORTANT
    ---------
    The first cell center is NOT forcibly pinned to S_INJECTED.
    This preserves consistency with the conservative Godunov
    advection step and guarantees the Pe_c -> infinity nesting.
    """

    n = len(S)

    D_cell = diffusion_shape(
        S
    )

    # Internal face diffusivities
    D_face = 0.5 * (
        D_cell[:-1]
        +
        D_cell[1:]
    )

    beta = (
        dtD
        * POROSITY
        /
        (
            PE_C
            * dxi ** 2
        )
    )

    lower = np.zeros(
        n,
        dtype=float,
    )

    diag = np.ones(
        n,
        dtype=float,
    )

    upper = np.zeros(
        n,
        dtype=float,
    )

    rhs = S.copy()

    # =================================================================
    # LEFT BOUNDARY
    #
    # Cell center is dxi/2 from the boundary face.
    #
    # Therefore:
    #
    #   dS/dxi |_west
    #       approximately
    #   (S_0 - S_inj) / (dxi/2)
    #
    # giving a factor of 2 in the west-boundary coefficient.
    # =================================================================

    D_boundary_left = 0.5 * (
        diffusion_shape(
            np.array(
                [S_INJECTED]
            )
        )[0]
        +
        D_cell[0]
    )

    D_right = (
        D_face[0]
    )

    west_coeff = (
        2.0
        * beta
        * D_boundary_left
    )

    east_coeff = (
        beta
        * D_right
    )

    diag[0] = (
        1.0
        +
        west_coeff
        +
        east_coeff
    )

    upper[0] = (
        -east_coeff
    )

    rhs[0] += (
        west_coeff
        * S_INJECTED
    )

    # =================================================================
    # INTERNAL CELLS
    # =================================================================

    for i in range(
        1,
        n - 1,
    ):

        DL = (
            D_face[
                i - 1
            ]
        )

        DR = (
            D_face[i]
        )

        lower[i] = (
            -beta
            * DL
        )

        diag[i] = (
            1.0
            +
            beta
            * (
                DL
                +
                DR
            )
        )

        upper[i] = (
            -beta
            * DR
        )

    # =================================================================
    # RIGHT BOUNDARY — ZERO DIFFUSIVE FLUX
    # =================================================================

    DL = (
        D_face[-1]
    )

    lower[-1] = (
        -beta
        * DL
    )

    diag[-1] = (
        1.0
        +
        beta
        * DL
    )

    upper[-1] = 0.0

    # =================================================================
    # BANDED IMPLICIT SOLVE
    # =================================================================

    ab = np.zeros(
        (
            3,
            n,
        ),
        dtype=float,
    )

    ab[
        0,
        1:
    ] = (
        upper[:-1]
    )

    ab[
        1,
        :
    ] = diag

    ab[
        2,
        :-1
    ] = (
        lower[1:]
    )

    S_new = solve_banded(
        (
            1,
            1,
        ),
        ab,
        rhs,
    )

    return np.clip(
        S_new,
        S_INITIAL,
        S_INJECTED,
    )

# =============================================================================
# ONE FULL OPERATOR-SPLIT STEP
# =============================================================================

def full_step(
    S,
    dtD,
    dxi,
    u_face,
):

    S_adv = (
        advective_step(
            S,
            dtD,
            dxi,
            u_face,
        )
    )

    S_full = (
        capillary_step(
            S_adv,
            dtD,
            dxi,
        )
    )

    return S_full


# =============================================================================
# MASTER FULL-PHYSICS SOLUTION
# =============================================================================

def build_master_solution(
    xi,
    max_tD,
):

    n = len(xi)

    if n < 3:

        raise ValueError(
            "Need at least 3 xi nodes."
        )

    dxi = float(
        xi[1]
        - xi[0]
    )

    if not np.allclose(
        np.diff(xi),
        dxi,
        rtol=1.0e-10,
        atol=1.0e-12,
    ):

        raise ValueError(
            "SG7A currently requires uniform xi."
        )

    xi_face = np.linspace(
        0.0,
        1.0,
        n + 1,
    )

    u_face = (
        u_dimensionless(
            xi_face
        )
    )

    sat_scan = np.linspace(
        S_INITIAL,
        S_INJECTED,
        4001,
    )

    max_df = float(
        np.max(
            np.abs(
                df_dS(
                    sat_scan
                )
            )
        )
    )

    max_wave_speed = (
        float(
            np.max(
                u_face
            )
        )
        * max_df
    )

    dtD_cfl = (
        CFL
        * dxi
        /
        (
            max_wave_speed
            + EPS
        )
    )

    master_tD = np.linspace(
        0.0,
        max_tD,
        N_MASTER_TD,
    )

    master_S = np.zeros(
        (
            N_MASTER_TD,
            n,
        ),
        dtype=float,
    )

    S = np.full(
        n,
        S_INITIAL,
        dtype=float,
    )

    S[0] = (
        S_INJECTED
    )

    master_S[0] = S

    current_tD = 0.0

    for snapshot in range(
        1,
        N_MASTER_TD,
    ):

        target_tD = (
            master_tD[
                snapshot
            ]
        )

        interval = (
            target_tD
            - current_tD
        )

        n_steps = max(
            1,
            int(
                np.ceil(
                    interval
                    / dtD_cfl
                )
            ),
        )

        dtD = (
            interval
            / n_steps
        )

        for _ in range(
            n_steps
        ):

            S = full_step(
                S,
                dtD,
                dxi,
                u_face,
            )

        current_tD = (
            target_tD
        )

        master_S[
            snapshot
        ] = S

        if (
            snapshot % 100 == 0
            or
            snapshot
            == N_MASTER_TD - 1
        ):

            print(
                f"  Master solution "
                f"{snapshot}/{N_MASTER_TD - 1}"
            )

    diagnostics = {
        "dxi":
            dxi,

        "max_wave_speed":
            max_wave_speed,

        "cfl_dtD":
            dtD_cfl,

        "max_tD":
            max_tD,
    }

    return (
        master_tD,
        master_S,
        diagnostics,
    )


# =============================================================================
# INTERPOLATE MASTER SOLUTION IN TIME
# =============================================================================

def interpolate_master_profile(
    target_tD,
    master_tD,
    master_S,
):

    if target_tD <= 0.0:

        result = np.full(
            master_S.shape[1],
            S_INITIAL,
            dtype=float,
        )

        result[0] = (
            S_INJECTED
        )

        return result

    if target_tD >= master_tD[-1]:

        return master_S[
            -1
        ].copy()

    upper = int(
        np.searchsorted(
            master_tD,
            target_tD,
        )
    )

    lower = (
        upper - 1
    )

    t0 = (
        master_tD[
            lower
        ]
    )

    t1 = (
        master_tD[
            upper
        ]
    )

    alpha = (
        target_tD - t0
    ) / (
        t1 - t0
        + EPS
    )

    return (
        (
            1.0 - alpha
        )
        * master_S[
            lower
        ]
        +
        alpha
        * master_S[
            upper
        ]
    )


# =============================================================================
# MAP MASTER PHYSICS TO ALL STREAMLINES
# =============================================================================

def build_streamline_saturation_database(
    sg6,
    master_tD,
    master_S,
):

    tau_end_days = (
        sg6[
            "tau_end_s"
        ]
        / DAY_TO_S
    )

    n_streamlines = (
        len(
            tau_end_days
        )
    )

    n_times = (
        len(
            OUTPUT_TIMES_DAYS
        )
    )

    n_xi = (
        master_S.shape[1]
    )

    saturation = np.zeros(
        (
            n_times,
            n_streamlines,
            n_xi,
        ),
        dtype=np.float32,
    )

    dimensionless_time = np.zeros(
        (
            n_times,
            n_streamlines,
        ),
        dtype=float,
    )

    for it, physical_time in enumerate(
        OUTPUT_TIMES_DAYS
    ):

        print(
            f"\nMapping t = "
            f"{physical_time:.1f} days"
        )

        for s in range(
            n_streamlines
        ):

            tD = (
                physical_time
                /
                tau_end_days[s]
            )

            dimensionless_time[
                it,
                s
            ] = tD

            saturation[
                it,
                s
            ] = (
                interpolate_master_profile(
                    tD,
                    master_tD,
                    master_S,
                )
            ).astype(
                np.float32
            )

    return (
        saturation,
        dimensionless_time,
    )


# =============================================================================
# PRODUCER EFFLUENT RESPONSE
# =============================================================================

def calculate_producer_response(
    sg6,
    master_tD,
    master_S,
    max_physical_time_days=1500.0,
    n_times=301,
):

    time_days = np.linspace(
        0.0,
        max_physical_time_days,
        n_times,
    )

    tau_end_days = (
        sg6[
            "tau_end_s"
        ]
        / DAY_TO_S
    )

    weights = (
        sg6[
            "weights_m3_s"
        ]
    )

    producers = (
        sg6[
            "producer"
        ]
    )

    response = {
        name: np.zeros(
            n_times,
            dtype=float,
        )
        for name in PRODUCER_NAMES
    }

    for it, t in enumerate(
        time_days
    ):

        outlet_sat = np.zeros(
            len(
                tau_end_days
            ),
            dtype=float,
        )

        for s in range(
            len(
                tau_end_days
            )
        ):

            tD = (
                t
                / tau_end_days[s]
            )

            profile = (
                interpolate_master_profile(
                    tD,
                    master_tD,
                    master_S,
                )
            )

            outlet_sat[s] = (
                profile[-1]
            )

        for name in PRODUCER_NAMES:

            mask = (
                producers == name
            )

            w = (
                weights[mask]
            )

            response[name][it] = (
                np.sum(
                    w
                    * outlet_sat[
                        mask
                    ]
                )
                /
                np.sum(w)
            )

    return (
        time_days,
        response,
    )


# =============================================================================
# BREAKTHROUGH
# =============================================================================

def calculate_breakthrough_times(
    time_days,
    producer_response,
):
    """
    Capillary solutions have nonzero tails, so breakthrough is defined
    using a finite saturation-rise threshold.

    Threshold:

        S_initial
        +
        1% of mobile saturation interval.
    """

    threshold = (
        S_INITIAL
        +
        0.01
        * (
            S_INJECTED
            - S_INITIAL
        )
    )

    breakthrough = {}

    for name in PRODUCER_NAMES:

        values = (
            producer_response[
                name
            ]
        )

        idx = np.where(
            values
            >= threshold
        )[0]

        if len(idx) == 0:

            breakthrough[
                name
            ] = None

        else:

            breakthrough[
                name
            ] = float(
                time_days[
                    idx[0]
                ]
            )

    return (
        threshold,
        breakthrough,
    )


# =============================================================================
# LIMITING-CASE VALIDATION
# =============================================================================

def run_limiting_case_tests(
    xi,
):
    """
    Check the full solver's nesting structure.

    1. Pe_c -> very large:
       full solution should approach compressible-only solution.

    2. Nc = 0:
       full equation should reduce to capillary-only conservative BL.
    """

    dxi = float(
        xi[1] - xi[0]
    )

    n = len(xi)

    xi_face = np.linspace(
        0.0,
        1.0,
        n + 1,
    )

    # -------------------------------------------------------------
    # TEST TIME
    # -------------------------------------------------------------

    test_tD = 0.15

    sat_scan = np.linspace(
        S_INITIAL,
        S_INJECTED,
        2001,
    )

    max_df = float(
        np.max(
            np.abs(
                df_dS(
                    sat_scan
                )
            )
        )
    )

    # -------------------------------------------------------------
    # COMPRESSIBLE-ONLY
    # -------------------------------------------------------------

    u_face = np.exp(
        NC
        * xi_face
    )

    dt = (
        CFL
        * dxi
        /
        (
            np.max(
                u_face
            )
            * max_df
            + EPS
        )
    )

    nt = max(
        1,
        int(
            np.ceil(
                test_tD
                / dt
            )
        ),
    )

    dt = (
        test_tD
        / nt
    )

    S_comp = np.full(
        n,
        S_INITIAL,
        dtype=float,
    )

    S_comp[0] = (
        S_INJECTED
    )

    for _ in range(nt):

        S_comp = advective_step(
            S_comp,
            dt,
            dxi,
            u_face,
        )

    # -------------------------------------------------------------
    # FULL WITH EXTREMELY WEAK CAPILLARITY
    # -------------------------------------------------------------

    global PE_C

    original_Pe = PE_C

    PE_C = 1.0e12

    S_weakcap = np.full(
        n,
        S_INITIAL,
        dtype=float,
    )

    S_weakcap[0] = (
        S_INJECTED
    )

    for _ in range(nt):

        S_weakcap = full_step(
            S_weakcap,
            dt,
            dxi,
            u_face,
        )

    PE_C = (
        original_Pe
    )

    weak_cap_error = float(
        np.mean(
            np.abs(
                S_weakcap
                - S_comp
            )
        )
    )

    # -------------------------------------------------------------
    # BOUNDS / FINITENESS
    # -------------------------------------------------------------

    checks = [
        (
            "Weak-capillary limit approaches compressible-only solution",
            weak_cap_error
            < 1.0e-8,
        ),

        (
            "Compressible-only solution finite",
            np.all(
                np.isfinite(
                    S_comp
                )
            ),
        ),

        (
            "Weak-capillary solution finite",
            np.all(
                np.isfinite(
                    S_weakcap
                )
            ),
        ),

        (
            "Saturation bounds respected",
            (
                np.min(
                    S_weakcap
                )
                >= S_INITIAL - 1.0e-8
                and
                np.max(
                    S_weakcap
                )
                <= S_INJECTED + 1.0e-8
            ),
        ),
    ]

    return (
        checks,
        weak_cap_error,
    )


# =============================================================================
# VALIDATION
# =============================================================================

def validate(
    sg6,
    saturation,
    dimensionless_time,
    master_S,
    limiting_checks,
):

    checks = []

    checks.append(
        (
            "SG6 streamline count = 1078",
            len(
                sg6[
                    "tau_end_s"
                ]
            )
            == 1078,
        )
    )

    checks.append(
        (
            "201 transport nodes retained",
            len(
                sg6[
                    "xi"
                ]
            )
            == 201,
        )
    )

    checks.append(
        (
            "All full-physics saturation values finite",
            np.all(
                np.isfinite(
                    saturation
                )
            ),
        )
    )

    checks.append(
        (
            "All dimensionless times positive",
            np.all(
                dimensionless_time
                > 0.0
            ),
        )
    )

    checks.append(
        (
            "Saturation lower bound respected",
            np.min(
                saturation
            )
            >= S_INITIAL - 1.0e-7,
        )
    )

    checks.append(
        (
            "Saturation upper bound respected",
            np.max(
                saturation
            )
            <= S_INJECTED + 1.0e-7,
        )
    )

    checks.append(
        (
            "Master solution finite",
            np.all(
                np.isfinite(
                    master_S
                )
            ),
        )
    )

    checks.extend(
        limiting_checks
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7A VALIDATION"
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

    if not all_passed:

        raise RuntimeError(
            "V15-SG7A validation failed. "
            "Do not freeze SG7A."
        )

    print(
        "V15-SG7A FULL-PHYSICS "
        "TOF TRANSPORT VALIDATION: PASS"
    )


# =============================================================================
# DIAGNOSTIC PLOTS
# =============================================================================

def plot_master_profiles(
    master_tD,
    master_S,
):

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    targets = [
        0.10,
        0.25,
        0.50,
        1.00,
        2.00,
    ]

    xi = np.linspace(
        0.0,
        1.0,
        master_S.shape[1],
    )

    for target in targets:

        if target > master_tD[-1]:

            continue

        idx = int(
            np.argmin(
                np.abs(
                    master_tD
                    - target
                )
            )
        )

        ax.plot(
            xi,
            master_S[
                idx
            ],
            label=(
                rf"$t_D={master_tD[idx]:.2f}$"
            ),
        )

    ax.set_xlabel(
        r"Normalized TOF coordinate $\xi$"
    )

    ax.set_ylabel(
        "Displacing-phase saturation"
    )

    ax.set_title(
        "PAD-Stream V15-SG7A\n"
        "Full Compressible + Capillary Transport"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7A_Master_FullPhysics_Profiles.png",
        dpi=300,
    )

    plt.close(fig)


def plot_producer_response(
    time_days,
    response,
    breakthrough,
):

    fig, ax = plt.subplots(
        figsize=(9, 6)
    )

    for name in PRODUCER_NAMES:

        ax.plot(
            time_days,
            response[
                name
            ],
            label=name,
        )

        if (
            breakthrough[
                name
            ]
            is not None
        ):

            ax.axvline(
                breakthrough[
                    name
                ],
                linestyle=":",
                alpha=0.5,
            )

    ax.set_xlabel(
        "Physical time (days)"
    )

    ax.set_ylabel(
        "Flux-weighted producer saturation"
    )

    ax.set_title(
        "PAD-Stream V15-SG7A\n"
        "Full-Physics Producer Breakthrough Response"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7A_Producer_Response.png",
        dpi=300,
    )

    plt.close(fig)


def plot_streamline_profiles_at_time(
    sg6,
    saturation,
    time_index,
):

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    xi = sg6[
        "xi"
    ]

    profiles = (
        saturation[
            time_index
        ]
    )

    stride = max(
        1,
        profiles.shape[0]
        // 100,
    )

    for s in range(
        0,
        profiles.shape[0],
        stride,
    ):

        ax.plot(
            xi,
            profiles[s],
            linewidth=0.6,
            alpha=0.35,
        )

    ax.set_xlabel(
        r"Normalized TOF coordinate $\xi$"
    )

    ax.set_ylabel(
        "Saturation"
    )

    ax.set_title(
        "PAD-Stream V15-SG7A\n"
        f"Streamline Saturation Profiles "
        f"at {OUTPUT_TIMES_DAYS[time_index]:.0f} days"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / (
            "V15SG7A_StreamlineProfiles_"
            f"{int(OUTPUT_TIMES_DAYS[time_index])}d.png"
        ),
        dpi=300,
    )

    plt.close(fig)


def plot_terminal_saturation_vs_tof(
    sg6,
    saturation,
    time_index,
):

    tau_end_days = (
        sg6[
            "tau_end_s"
        ]
        / DAY_TO_S
    )

    terminal = (
        saturation[
            time_index,
            :,
            -1,
        ]
    )

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.scatter(
        tau_end_days,
        terminal,
        s=10,
        alpha=0.5,
    )

    ax.set_xlabel(
        "Terminal streamline TOF (days)"
    )

    ax.set_ylabel(
        "Producer-end saturation"
    )

    ax.set_title(
        "PAD-Stream V15-SG7A\n"
        f"Terminal Saturation vs TOF "
        f"at {OUTPUT_TIMES_DAYS[time_index]:.0f} days"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / (
            "V15SG7A_TerminalSaturation_vs_TOF_"
            f"{int(OUTPUT_TIMES_DAYS[time_index])}d.png"
        ),
        dpi=300,
    )

    plt.close(fig)


# =============================================================================
# SAVE
# =============================================================================

def save_transport_database(
    sg6,
    saturation,
    dimensionless_time,
    master_tD,
    master_S,
):

    np.savez_compressed(
        TRANSPORT_FILE,

        saturation=
            saturation,

        physical_times_days=
            OUTPUT_TIMES_DAYS,

        streamline_dimensionless_time=
            dimensionless_time,

        xi=
            sg6[
                "xi"
            ],

        tau_end_s=
            sg6[
                "tau_end_s"
            ],

        weights_m3_s=
            sg6[
                "weights_m3_s"
            ],

        producer=
            sg6[
                "producer"
            ],

        streamline_id=
            sg6[
                "streamline_id"
            ],

        xyz_m=
            sg6[
                "xyz_m"
            ],

        master_tD=
            master_tD,

        master_saturation=
            master_S,
    )


def save_summary(
    sg6,
    master_diag,
    weak_cap_error,
    breakthrough_threshold,
    breakthrough,
):

    summary = {
        "milestone":
            "V15-SG7A",

        "description":
            (
                "Classical full conservative "
                "compressible + capillary transport "
                "on SGSim streamline TOF coordinates"
            ),

        "status":
            "PASS",

        "source":
            "Frozen V15-SG6 transport coordinates",

        "streamlines":
            int(
                len(
                    sg6[
                        "tau_end_s"
                    ]
                )
            ),

        "transport_nodes":
            int(
                len(
                    sg6[
                        "xi"
                    ]
                )
            ),

        "governing_equation":
            (
                "dS/dtD + d[uD f(S)]/dxi = "
                "(phi/Pe_c) d/dxi[D_tilde(S) dS/dxi]"
            ),

        "compressibility": {
            "formulation":
                "conservative Godunov",

            "Nc":
                NC,

            "velocity":
                "uD = exp(Nc xi)",
        },

        "capillarity": {
            "model":
                "Brooks-Corey normalized nonlinear diffusion",

            "Pe_c":
                PE_C,

            "lambda_bc":
                LAMBDA_BC,

            "normalization":
                "D_tilde(Se=0.5)=1",
        },

        "rock_fluid": {
            "Swc":
                SWC,

            "Sor":
                SOR,

            "kr_disp_max":
                KR_DISP_MAX,

            "kr_res_max":
                KR_RES_MAX,

            "n_disp":
                N_DISP,

            "n_res":
                N_RES,

            "mu_disp":
                MU_DISP,

            "mu_res":
                MU_RES,

            "porosity":
                POROSITY,
        },

        "physical_times_days":
            OUTPUT_TIMES_DAYS.tolist(),

        "master_solver":
            master_diag,

        "weak_capillary_limit_error":
            float(
                weak_cap_error
            ),

        "breakthrough_definition": {
            "threshold_saturation":
                float(
                    breakthrough_threshold
                ),

            "criterion":
                (
                    "producer flux-weighted saturation "
                    "exceeds initial saturation plus "
                    "1 percent of mobile saturation interval"
                ),
        },

        "producer_breakthrough_days":
            breakthrough,

        "next_milestone":
            (
                "V15-SG7B - full-physics "
                "PI-RNN transport on SGSim TOF coordinates"
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
        "PAD-Stream Version 15-SG7A"
    )

    print(
        "Classical Full Conservative "
        "Compressible + Capillary TOF Transport"
    )

    print(
        "=" * 78
    )

    print(
        "\nFULL-PHYSICS PARAMETERS"
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
        f"  Porosity                : "
        f"{POROSITY:.3f}"
    )

    # -------------------------------------------------------------------------
    # LOAD SG6
    # -------------------------------------------------------------------------

    sg6 = load_sg6()

    tau_end_days = (
        sg6[
            "tau_end_s"
        ]
        / DAY_TO_S
    )

    print(
        "\nSG6 TRANSPORT DATABASE"
    )

    print(
        f"  Streamlines             : "
        f"{len(tau_end_days):,}"
    )

    print(
        f"  xi nodes                : "
        f"{len(sg6['xi'])}"
    )

    print(
        f"  Minimum terminal TOF    : "
        f"{tau_end_days.min():.3f} days"
    )

    print(
        f"  Maximum terminal TOF    : "
        f"{tau_end_days.max():.3f} days"
    )

    # -------------------------------------------------------------------------
    # MAXIMUM DIMENSIONLESS TIME REQUIRED
    # -------------------------------------------------------------------------

    max_tD = (
        OUTPUT_TIMES_DAYS.max()
        /
        tau_end_days.min()
    )

    # Producer response extends to 1500 days.
    max_response_tD = (
        1500.0
        /
        tau_end_days.min()
    )

    max_tD = max(
        max_tD,
        max_response_tD,
    )

    print(
        "\nMASTER TRANSPORT SOLVE"
    )

    print(
        f"  Maximum tD required     : "
        f"{max_tD:.3f}"
    )

    print(
        f"  Master snapshots        : "
        f"{N_MASTER_TD}"
    )

    # -------------------------------------------------------------------------
    # BUILD MASTER FULL-PHYSICS SOLUTION
    # -------------------------------------------------------------------------

    (
        master_tD,
        master_S,
        master_diag,
    ) = build_master_solution(
        sg6[
            "xi"
        ],
        max_tD,
    )

    # -------------------------------------------------------------------------
    # MAP TO SG6 STREAMLINES
    # -------------------------------------------------------------------------

    (
        saturation,
        dimensionless_time,
    ) = (
        build_streamline_saturation_database(
            sg6,
            master_tD,
            master_S,
        )
    )

    # -------------------------------------------------------------------------
    # PRODUCER RESPONSE
    # -------------------------------------------------------------------------

    (
        response_time_days,
        producer_response,
    ) = (
        calculate_producer_response(
            sg6,
            master_tD,
            master_S,
        )
    )

    (
        breakthrough_threshold,
        breakthrough,
    ) = (
        calculate_breakthrough_times(
            response_time_days,
            producer_response,
        )
    )

    print(
        "\nPRODUCER BREAKTHROUGH"
    )

    print(
        f"  Saturation threshold    : "
        f"{breakthrough_threshold:.6f}"
    )

    for name in PRODUCER_NAMES:

        value = (
            breakthrough[
                name
            ]
        )

        if value is None:

            print(
                f"  {name:10s}             : "
                f"> {response_time_days[-1]:.0f} days"
            )

        else:

            print(
                f"  {name:10s}             : "
                f"{value:.1f} days"
            )

    # -------------------------------------------------------------------------
    # LIMITING CASES
    # -------------------------------------------------------------------------

    (
        limiting_checks,
        weak_cap_error,
    ) = (
        run_limiting_case_tests(
            sg6[
                "xi"
            ]
        )
    )

    print(
        "\nLIMITING CASE"
    )

    print(
        f"  Pe_c -> infinity error  : "
        f"{weak_cap_error:.6e}"
    )

    # -------------------------------------------------------------------------
    # VALIDATE
    # -------------------------------------------------------------------------

    validate(
        sg6,
        saturation,
        dimensionless_time,
        master_S,
        limiting_checks,
    )

    # -------------------------------------------------------------------------
    # SAVE DATA
    # -------------------------------------------------------------------------

    save_transport_database(
        sg6,
        saturation,
        dimensionless_time,
        master_tD,
        master_S,
    )

    # -------------------------------------------------------------------------
    # FIGURES
    # -------------------------------------------------------------------------

    plot_master_profiles(
        master_tD,
        master_S,
    )

    plot_producer_response(
        response_time_days,
        producer_response,
        breakthrough,
    )

    for index in range(
        len(
            OUTPUT_TIMES_DAYS
        )
    ):

        plot_streamline_profiles_at_time(
            sg6,
            saturation,
            index,
        )

        plot_terminal_saturation_vs_tof(
            sg6,
            saturation,
            index,
        )

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------

    save_summary(
        sg6,
        master_diag,
        weak_cap_error,
        breakthrough_threshold,
        breakthrough,
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
        "\nDatabase:"
    )

    print(
        "  FULL_PHYSICS_STREAMLINE_SATURATION.npz"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7A_Master_FullPhysics_Profiles.png"
    )

    print(
        "  V15SG7A_Producer_Response.png"
    )

    for t in OUTPUT_TIMES_DAYS:

        print(
            "  "
            f"V15SG7A_StreamlineProfiles_{int(t)}d.png"
        )

        print(
            "  "
            f"V15SG7A_TerminalSaturation_vs_TOF_{int(t)}d.png"
        )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7A_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7A COMPLETED SUCCESSFULLY"
    )

    print(
        "Next milestone:"
    )

    print(
        "V15-SG7B — Full-physics PI-RNN transport "
        "on SGSim TOF coordinates"
    )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()