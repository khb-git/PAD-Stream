from pathlib import Path
import json

import numpy as np
import matplotlib.pyplot as plt

from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import spsolve


# ======================================================================
# PAD-Stream Version 15-SG3
# Unit-Consistent Five-Spot Finite-Volume Pressure Solve
#
# PURPOSE
# -------
# 1. Load frozen SG1/SG2 geology.
# 2. Convert all physical quantities internally to SI units.
# 3. Build anisotropic finite-volume pressure coefficients.
# 4. Apply:
#       - no-flow external boundaries
#       - center rate-controlled CO2 injector
#       - four Peaceman BHP-controlled producers
#       - gravity
# 5. Solve steady reference-mobility pressure equation.
# 6. Validate residual and global mass balance.
#
# IMPORTANT
# ---------
# This is a pressure-physics milestone only.
# No Darcy-flux arrays, Pollock tracing, TOF, or transport yet.
# ======================================================================


# ----------------------------------------------------------------------
# PROJECT PATHS
# ----------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

SG1_PERM_FILE = ROOT / "SGSIM_50x50x15_PERM_MD.csv"

SG2_DIR = ROOT / "output" / "V15_SG2"

KFACE_X_FILE = SG2_DIR / "KFACE_X.npy"
KFACE_Y_FILE = SG2_DIR / "KFACE_Y.npy"
KFACE_Z_FILE = SG2_DIR / "KFACE_Z.npy"

OUTPUT_DIR = ROOT / "output" / "V15_SG3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG3_Summary.json"

PRESSURE_FILE = OUTPUT_DIR / "PRESSURE_PSI.npy"


# ----------------------------------------------------------------------
# GRID
# ----------------------------------------------------------------------

NX = 50
NY = 50
NZ = 15

DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0

N_CELLS = NX * NY * NZ

LX_FT = NX * DX_FT
LY_FT = NY * DY_FT
LZ_FT = NZ * DZ_FT


# ----------------------------------------------------------------------
# UNIT CONVERSIONS
# ----------------------------------------------------------------------

FT_TO_M = 0.3048
MD_TO_M2 = 9.869233e-16
CP_TO_PA_S = 1.0e-3

PSI_TO_PA = 6894.757293168
PA_TO_PSI = 1.0 / PSI_TO_PA

DAY_TO_S = 86400.0
TONNE_TO_KG = 1000.0


# SI grid dimensions
DX_M = DX_FT * FT_TO_M
DY_M = DY_FT * FT_TO_M
DZ_M = DZ_FT * FT_TO_M

AX_M2 = DY_M * DZ_M
AY_M2 = DX_M * DZ_M
AZ_M2 = DX_M * DY_M


# ----------------------------------------------------------------------
# REFERENCE FLUID / GRAVITY
# ----------------------------------------------------------------------

# Initial reference pressure solve is brine-mobility dominated.
MU_REF_CP = 0.50
MU_REF_PA_S = MU_REF_CP * CP_TO_PA_S

# Representative brine density for gravity.
RHO_BRINE_KG_M3 = 1020.0

G_M_S2 = 9.80665

GRAVITY_ON = True


# ----------------------------------------------------------------------
# INITIAL / WELL PRESSURES
# ----------------------------------------------------------------------

INITIAL_PRESSURE_PSI = 2500.0
PRODUCER_BHP_PSI = 2000.0

INITIAL_PRESSURE_PA = INITIAL_PRESSURE_PSI * PSI_TO_PA
PRODUCER_BHP_PA = PRODUCER_BHP_PSI * PSI_TO_PA


# ----------------------------------------------------------------------
# CO2 INJECTION CONTROL
# ----------------------------------------------------------------------

CO2_MASS_RATE_TONNES_DAY = 500.0
CO2_DENSITY_KG_M3 = 700.0

CO2_MASS_RATE_KG_S = (
    CO2_MASS_RATE_TONNES_DAY
    * TONNE_TO_KG
    / DAY_TO_S
)

Q_INJ_M3_S = (
    CO2_MASS_RATE_KG_S
    / CO2_DENSITY_KG_M3
)

Q_INJ_M3_DAY = Q_INJ_M3_S * DAY_TO_S


# ----------------------------------------------------------------------
# FIVE-SPOT GEOMETRY
# ----------------------------------------------------------------------

INJECTOR_I = 24
INJECTOR_J = 24

PRODUCERS = {
    "PROD_SW": {"i": 4, "j": 4},
    "PROD_SE": {"i": 45, "j": 4},
    "PROD_NW": {"i": 4, "j": 45},
    "PROD_NE": {"i": 45, "j": 45},
}

# Physical Layers 6-10 -> zero-based 5-9.
COMPLETION_K = list(range(5, 10))

N_INJECTOR_PERFS = len(COMPLETION_K)

Q_INJ_PERF_M3_S = (
    Q_INJ_M3_S / N_INJECTOR_PERFS
)


# ----------------------------------------------------------------------
# PEACEMAN WELL PARAMETERS
# ----------------------------------------------------------------------

WELL_RADIUS_FT = 0.25
WELL_RADIUS_M = WELL_RADIUS_FT * FT_TO_M

SKIN = 0.0


# ======================================================================
# INDEXING
# ======================================================================

def cell_id(k, j, i):
    """
    Flatten (k,j,i) into one pressure unknown.
    X varies fastest.
    """
    return (k * NY + j) * NX + i


def cell_center_x_ft(i):
    return (i + 0.5) * DX_FT


def cell_center_y_ft(j):
    return (j + 0.5) * DY_FT


def cell_center_z_m(k):
    """
    Z positive upward.

    Layer 1 is treated as the bottom layer.
    """
    return (k + 0.5) * DZ_M


# ======================================================================
# LOAD FROZEN SG1 / SG2 STATE
# ======================================================================

def load_cell_permeability():

    values = np.loadtxt(
        SG1_PERM_FILE,
        skiprows=1,
        dtype=float,
    )

    if values.size != N_CELLS:
        raise ValueError(
            f"Expected {N_CELLS:,} permeability values; "
            f"found {values.size:,}."
        )

    return values.reshape(
        (NZ, NY, NX),
        order="C",
    )


def load_face_permeabilities():

    required = [
        KFACE_X_FILE,
        KFACE_Y_FILE,
        KFACE_Z_FILE,
    ]

    for f in required:
        if not f.exists():
            raise FileNotFoundError(
                f"Missing frozen SG2 output:\n{f}"
            )

    kfx_md = np.load(KFACE_X_FILE)
    kfy_md = np.load(KFACE_Y_FILE)
    kfz_md = np.load(KFACE_Z_FILE)

    if kfx_md.shape != (NZ, NY, NX - 1):
        raise ValueError("Invalid KFACE_X shape.")

    if kfy_md.shape != (NZ, NY - 1, NX):
        raise ValueError("Invalid KFACE_Y shape.")

    if kfz_md.shape != (NZ - 1, NY, NX):
        raise ValueError("Invalid KFACE_Z shape.")

    return kfx_md, kfy_md, kfz_md


# ======================================================================
# SI TRANSMISSIBILITIES
# ======================================================================

def construct_si_transmissibilities(
    kfx_md,
    kfy_md,
    kfz_md,
):
    """
    T units:
        m^3 / (Pa s)

    q = T * DeltaP
    """

    kfx = kfx_md * MD_TO_M2
    kfy = kfy_md * MD_TO_M2
    kfz = kfz_md * MD_TO_M2

    tx = (
        kfx
        * AX_M2
        / (MU_REF_PA_S * DX_M)
    )

    ty = (
        kfy
        * AY_M2
        / (MU_REF_PA_S * DY_M)
    )

    tz = (
        kfz
        * AZ_M2
        / (MU_REF_PA_S * DZ_M)
    )

    return tx, ty, tz


# ======================================================================
# PEACEMAN WELL INDEX
# ======================================================================

def peaceman_well_index_si(
    kx_md,
    ky_md,
):
    """
    Vertical well, anisotropic horizontal permeability.

    Returns WI in:
        m^3 / (Pa s)

    q = WI * (Pcell - Pbhp)
    """

    kx = kx_md * MD_TO_M2
    ky = ky_md * MD_TO_M2

    # Peaceman equivalent radius for rectangular anisotropic cell.
    ratio_yx = np.sqrt(ky / kx)
    ratio_xy = np.sqrt(kx / ky)

    numerator = 0.28 * np.sqrt(
        ratio_yx * DX_M**2
        +
        ratio_xy * DY_M**2
    )

    denominator = (
        (ky / kx) ** 0.25
        +
        (kx / ky) ** 0.25
    )

    re = numerator / denominator

    kh = np.sqrt(kx * ky)

    denom = (
        np.log(re / WELL_RADIUS_M)
        + SKIN
    )

    if denom <= 0.0:
        raise ValueError(
            "Invalid Peaceman denominator."
        )

    wi = (
        2.0
        * np.pi
        * kh
        * DZ_M
        /
        (
            MU_REF_PA_S
            * denom
        )
    )

    return wi, re


# ======================================================================
# PRESSURE MATRIX ASSEMBLY
# ======================================================================

def assemble_pressure_system(
    k_cell_md,
    tx,
    ty,
    tz,
):

    A = lil_matrix(
        (N_CELLS, N_CELLS),
        dtype=float,
    )

    b = np.zeros(
        N_CELLS,
        dtype=float,
    )

    producer_wi = {}

    # --------------------------------------------------------------
    # Internal finite-volume connections
    # --------------------------------------------------------------

    for k in range(NZ):

        zc = cell_center_z_m(k)

        for j in range(NY):

            for i in range(NX):

                c = cell_id(k, j, i)

                diag = 0.0
                rhs_gravity = 0.0

                # WEST
                if i > 0:
                    n = cell_id(k, j, i - 1)
                    t = tx[k, j, i - 1]

                    diag += t
                    A[c, n] -= t

                # EAST
                if i < NX - 1:
                    n = cell_id(k, j, i + 1)
                    t = tx[k, j, i]

                    diag += t
                    A[c, n] -= t

                # SOUTH
                if j > 0:
                    n = cell_id(k, j - 1, i)
                    t = ty[k, j - 1, i]

                    diag += t
                    A[c, n] -= t

                # NORTH
                if j < NY - 1:
                    n = cell_id(k, j + 1, i)
                    t = ty[k, j, i]

                    diag += t
                    A[c, n] -= t

                # BOTTOM
                if k > 0:

                    n = cell_id(k - 1, j, i)
                    t = tz[k - 1, j, i]

                    zn = cell_center_z_m(k - 1)

                    diag += t
                    A[c, n] -= t

                    if GRAVITY_ON:
                        rhs_gravity += (
                                t
                                * RHO_BRINE_KG_M3
                                * G_M_S2
                                * (zn - zc)
                        )

                # TOP
                if k < NZ - 1:

                    n = cell_id(k + 1, j, i)
                    t = tz[k, j, i]

                    zn = cell_center_z_m(k + 1)

                    diag += t
                    A[c, n] -= t

                    if GRAVITY_ON:
                        rhs_gravity += (
                                t
                                * RHO_BRINE_KG_M3
                                * G_M_S2
                                * (zn - zc)
                        )

                A[c, c] += diag

                b[c] += rhs_gravity

    # --------------------------------------------------------------
    # Rate-controlled injector
    # --------------------------------------------------------------

    for k in COMPLETION_K:

        c = cell_id(
            k,
            INJECTOR_J,
            INJECTOR_I,
        )

        b[c] += Q_INJ_PERF_M3_S

    # --------------------------------------------------------------
    # BHP-controlled producers
    # --------------------------------------------------------------

    for name, well in PRODUCERS.items():

        perf_data = []

        i = well["i"]
        j = well["j"]

        for k in COMPLETION_K:

            k_md = k_cell_md[k, j, i]

            wi, re = peaceman_well_index_si(
                k_md,
                k_md,
            )

            c = cell_id(k, j, i)

            A[c, c] += wi

            b[c] += (
                wi
                * PRODUCER_BHP_PA
            )

            perf_data.append({
                "k": k,
                "wi_si": wi,
                "re_m": re,
            })

        producer_wi[name] = perf_data

    return csr_matrix(A), b, producer_wi


# ======================================================================
# SOLVE
# ======================================================================

def solve_pressure(A, b):

    print("\nSolving sparse system...")
    print(
        f"  Unknowns               : {A.shape[0]:,}"
    )
    print(
        f"  Nonzeros               : {A.nnz:,}"
    )

    p_pa = spsolve(A, b)

    if not np.all(np.isfinite(p_pa)):
        raise RuntimeError(
            "Pressure solve produced non-finite values."
        )

    p_psi = (
        p_pa
        * PA_TO_PSI
    ).reshape(
        (NZ, NY, NX),
        order="C",
    )

    return p_pa, p_psi


# ======================================================================
# WELL RATE CALCULATION
# ======================================================================

def calculate_well_rates(
    p_psi,
    producer_wi,
):

    rates = {}

    total_prod_m3_s = 0.0

    for name, well in PRODUCERS.items():

        i = well["i"]
        j = well["j"]

        q_total = 0.0
        perf_rates = []

        for perf in producer_wi[name]:

            k = perf["k"]
            wi = perf["wi_si"]

            pcell_pa = (
                p_psi[k, j, i]
                * PSI_TO_PA
            )

            q = wi * (
                pcell_pa
                - PRODUCER_BHP_PA
            )

            q_total += q

            perf_rates.append(
                q * DAY_TO_S
            )

        rates[name] = {
            "m3_s": float(q_total),
            "m3_day": float(
                q_total * DAY_TO_S
            ),
            "perf_m3_day": [
                float(x)
                for x in perf_rates
            ],
        }

        total_prod_m3_s += q_total

    return rates, total_prod_m3_s


# ======================================================================
# VALIDATION
# ======================================================================

def validate_solution(
    A,
    b,
    p_pa,
    p_psi,
    producer_rates,
    total_prod_m3_s,
):

    residual = (
        A @ p_pa - b
    )

    abs_res_norm = np.linalg.norm(
        residual
    )

    rhs_norm = np.linalg.norm(b)

    rel_res_norm = (
        abs_res_norm
        / max(rhs_norm, 1.0e-30)
    )

    mass_error_m3_s = (
        Q_INJ_M3_S
        - total_prod_m3_s
    )

    mass_error_fraction = (
        abs(mass_error_m3_s)
        / Q_INJ_M3_S
    )

    injector_pressures = np.array([
        p_psi[
            k,
            INJECTOR_J,
            INJECTOR_I,
        ]
        for k in COMPLETION_K
    ])

    print("\n" + "=" * 78)
    print("V15-SG3 VALIDATION")
    print("=" * 78)

    checks = [
        (
            "Pressure field finite",
            np.all(np.isfinite(p_psi)),
        ),
        (
            "Pressure system residual < 1e-8",
            rel_res_norm < 1.0e-8,
        ),
        (
            "All producer rates > 0",
            all(
                x["m3_s"] > 0.0
                for x in producer_rates.values()
            ),
        ),
        (
            "Global mass-balance error < 0.1%",
            mass_error_fraction < 1.0e-3,
        ),
        (
            "Injector completion pressure > producer BHP",
            injector_pressures.mean()
            > PRODUCER_BHP_PSI,
        ),
    ]

    all_passed = True

    for description, passed in checks:

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"[{status:4s}] {description}"
        )

        if not passed:
            all_passed = False

    print("=" * 78)

    print(
        f"Relative linear residual : "
        f"{rel_res_norm:.6e}"
    )

    print(
        f"Mass-balance error       : "
        f"{100.0 * mass_error_fraction:.6f} %"
    )

    if not all_passed:
        raise RuntimeError(
            "V15-SG3 validation failed."
        )

    return {
        "relative_linear_residual":
            float(rel_res_norm),

        "mass_balance_error_fraction":
            float(mass_error_fraction),

        "injector_mean_pressure_psi":
            float(
                injector_pressures.mean()
            ),

        "injector_min_pressure_psi":
            float(
                injector_pressures.min()
            ),

        "injector_max_pressure_psi":
            float(
                injector_pressures.max()
            ),
    }


# ======================================================================
# PLOTS
# ======================================================================

def plot_pressure_layer8(
    p_psi,
):

    layer = 7

    fig, ax = plt.subplots(
        figsize=(8, 7)
    )

    im = ax.imshow(
        p_psi[layer],
        origin="lower",
        extent=[
            0,
            LX_FT,
            0,
            LY_FT,
        ],
        aspect="equal",
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
    )

    cbar.set_label(
        "Pressure (psi)"
    )

    # Pressure contours
    x = np.linspace(
        DX_FT / 2,
        LX_FT - DX_FT / 2,
        NX,
    )

    y = np.linspace(
        DY_FT / 2,
        LY_FT - DY_FT / 2,
        NY,
    )

    X, Y = np.meshgrid(
        x,
        y,
    )

    ax.contour(
        X,
        Y,
        p_psi[layer],
        levels=12,
        linewidths=0.8,
    )

    ax.scatter(
        cell_center_x_ft(INJECTOR_I),
        cell_center_y_ft(INJECTOR_J),
        marker="*",
        s=180,
        label="Injector",
    )

    for name, well in PRODUCERS.items():

        ax.scatter(
            cell_center_x_ft(
                well["i"]
            ),
            cell_center_y_ft(
                well["j"]
            ),
            marker="s",
            s=65,
            label=name,
        )

    ax.set_title(
        "PAD-Stream V15-SG3\n"
        "Five-Spot Pressure Field - Layer 8"
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Y (ft)")

    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.18, 1.0),
        fontsize=8,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG3_Pressure_Layer08.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


def plot_vertical_pressure(
    p_psi,
):

    middle_y = NY // 2

    section = p_psi[
        :,
        middle_y,
        :
    ]

    fig, ax = plt.subplots(
        figsize=(10, 4)
    )

    im = ax.imshow(
        section,
        origin="lower",
        extent=[
            0,
            LX_FT,
            0,
            LZ_FT,
        ],
        aspect="auto",
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
    )

    cbar.set_label(
        "Pressure (psi)"
    )

    ax.axhline(
        5 * DZ_FT,
        linestyle="--",
    )

    ax.axhline(
        10 * DZ_FT,
        linestyle="--",
    )

    ax.set_title(
        "PAD-Stream V15-SG3\n"
        "Vertical Pressure Section"
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Z (ft)")

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG3_Pressure_VerticalSection.png",
        dpi=300,
    )

    plt.close(fig)


def plot_pressure_histogram(
    p_psi,
):

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.hist(
        p_psi.ravel(),
        bins=50,
    )

    ax.axvline(
        PRODUCER_BHP_PSI,
        linestyle="--",
        label="Producer BHP",
    )

    ax.set_xlabel(
        "Pressure (psi)"
    )

    ax.set_ylabel(
        "Cell count"
    )

    ax.set_title(
        "PAD-Stream V15-SG3\n"
        "Pressure Distribution"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG3_Pressure_Histogram.png",
        dpi=300,
    )

    plt.close(fig)


# ======================================================================
# SUMMARY
# ======================================================================

def save_summary(
    p_psi,
    producer_rates,
    validation,
    A,
):

    summary = {
        "milestone":
            "V15-SG3",

        "description":
            "Unit-consistent five-spot finite-volume pressure solve",

        "status":
            "PASS",

        "grid": {
            "nx": NX,
            "ny": NY,
            "nz": NZ,
            "cells": N_CELLS,
            "dx_ft": DX_FT,
            "dy_ft": DY_FT,
            "dz_ft": DZ_FT,
        },

        "reference_mobility": {
            "fluid":
                "initial brine reference",
            "viscosity_cp":
                MU_REF_CP,
            "density_kg_m3":
                RHO_BRINE_KG_M3,
        },

        "gravity_on":
            GRAVITY_ON,

        "external_boundaries":
            "NO_FLOW",

        "injection_control": {
            "mass_rate_tonnes_day":
                CO2_MASS_RATE_TONNES_DAY,
            "reference_co2_density_kg_m3":
                CO2_DENSITY_KG_M3,
            "reservoir_volume_rate_m3_day":
                Q_INJ_M3_DAY,
            "completed_layers":
                "6-10",
        },

        "producer_control": {
            "type":
                "PEACEMAN_FIXED_BHP",
            "bhp_psi":
                PRODUCER_BHP_PSI,
            "well_radius_ft":
                WELL_RADIUS_FT,
            "skin":
                SKIN,
        },

        "pressure_psi": {
            "min":
                float(p_psi.min()),
            "max":
                float(p_psi.max()),
            "mean":
                float(p_psi.mean()),
            "median":
                float(np.median(p_psi)),
        },

        "producer_rates":
            producer_rates,

        "injector_pressure":
            validation,

        "sparse_matrix": {
            "shape":
                list(A.shape),
            "nnz":
                int(A.nnz),
        },

        "next_milestone":
            "V15-SG4 - conservative Darcy face fluxes",
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


# ======================================================================
# MAIN
# ======================================================================

def main():

    print("\n" + "=" * 78)
    print(
        "PAD-Stream Version 15-SG3"
    )
    print(
        "Unit-Consistent Five-Spot Finite-Volume Pressure Solve"
    )
    print("=" * 78)

    print("\nREFERENCE CONDITIONS")

    print(
        f"  Reference viscosity     : "
        f"{MU_REF_CP:.3f} cP"
    )

    print(
        f"  Brine density           : "
        f"{RHO_BRINE_KG_M3:.1f} kg/m3"
    )

    print(
        f"  Gravity                 : "
        f"{GRAVITY_ON}"
    )

    print("\nCO2 INJECTION CONTROL")

    print(
        f"  Mass rate               : "
        f"{CO2_MASS_RATE_TONNES_DAY:.1f} tonnes/day"
    )

    print(
        f"  Reference CO2 density   : "
        f"{CO2_DENSITY_KG_M3:.1f} kg/m3"
    )

    print(
        f"  Reservoir volume rate   : "
        f"{Q_INJ_M3_DAY:.3f} m3/day"
    )

    print(
        f"  Per completion layer    : "
        f"{Q_INJ_M3_DAY / N_INJECTOR_PERFS:.3f} m3/day"
    )

    print("\nPRODUCTION CONTROL")

    print(
        f"  Producer BHP            : "
        f"{PRODUCER_BHP_PSI:.1f} psi"
    )

    print(
        f"  Well radius             : "
        f"{WELL_RADIUS_FT:.3f} ft"
    )

    print(
        f"  Skin                    : "
        f"{SKIN:.2f}"
    )

    # --------------------------------------------------------------
    # Load frozen state
    # --------------------------------------------------------------

    k_cell = load_cell_permeability()

    kfx_md, kfy_md, kfz_md = (
        load_face_permeabilities()
    )

    # --------------------------------------------------------------
    # SI transmissibilities
    # --------------------------------------------------------------

    tx, ty, tz = (
        construct_si_transmissibilities(
            kfx_md,
            kfy_md,
            kfz_md,
        )
    )

    print("\nSI TRANSMISSIBILITY")

    print(
        f"  Tx mean                : "
        f"{tx.mean():.6e} m3/(Pa s)"
    )

    print(
        f"  Ty mean                : "
        f"{ty.mean():.6e} m3/(Pa s)"
    )

    print(
        f"  Tz mean                : "
        f"{tz.mean():.6e} m3/(Pa s)"
    )

    # --------------------------------------------------------------
    # Assemble
    # --------------------------------------------------------------

    print("\nAssembling pressure system...")

    A, b, producer_wi = (
        assemble_pressure_system(
            k_cell,
            tx,
            ty,
            tz,
        )
    )

    # --------------------------------------------------------------
    # Solve
    # --------------------------------------------------------------

    p_pa, p_psi = solve_pressure(
        A,
        b,
    )

    print("\nPRESSURE RESULTS")

    print(
        f"  Minimum                 : "
        f"{p_psi.min():.3f} psi"
    )

    print(
        f"  Maximum                 : "
        f"{p_psi.max():.3f} psi"
    )

    print(
        f"  Mean                    : "
        f"{p_psi.mean():.3f} psi"
    )

    print(
        f"  Median                  : "
        f"{np.median(p_psi):.3f} psi"
    )

    # --------------------------------------------------------------
    # Wells
    # --------------------------------------------------------------

    producer_rates, total_prod = (
        calculate_well_rates(
            p_psi,
            producer_wi,
        )
    )

    print("\nPRODUCER RATES")

    for name, data in producer_rates.items():

        print(
            f"  {name:10s}             : "
            f"{data['m3_day']:.3f} m3/day"
        )

    print(
        f"  Total production        : "
        f"{total_prod * DAY_TO_S:.3f} m3/day"
    )

    print(
        f"  Total injection         : "
        f"{Q_INJ_M3_DAY:.3f} m3/day"
    )

    # --------------------------------------------------------------
    # Validation
    # --------------------------------------------------------------

    validation = validate_solution(
        A,
        b,
        p_pa,
        p_psi,
        producer_rates,
        total_prod,
    )

    print("\nINJECTOR PRESSURE")

    print(
        f"  Mean completion P       : "
        f"{validation['injector_mean_pressure_psi']:.3f} psi"
    )

    print(
        f"  Min completion P        : "
        f"{validation['injector_min_pressure_psi']:.3f} psi"
    )

    print(
        f"  Max completion P        : "
        f"{validation['injector_max_pressure_psi']:.3f} psi"
    )

    # --------------------------------------------------------------
    # Save
    # --------------------------------------------------------------

    np.save(
        PRESSURE_FILE,
        p_psi,
    )

    plot_pressure_layer8(
        p_psi
    )

    plot_vertical_pressure(
        p_psi
    )

    plot_pressure_histogram(
        p_psi
    )

    save_summary(
        p_psi,
        producer_rates,
        validation,
        A,
    )

    print("\nOUTPUTS")

    print(
        f"  {PRESSURE_FILE}"
    )

    print(
        f"  {SUMMARY_FILE}"
    )

    print(
        "  V15SG3_Pressure_Layer08.png"
    )

    print(
        "  V15SG3_Pressure_VerticalSection.png"
    )

    print(
        "  V15SG3_Pressure_Histogram.png"
    )

    print("\n" + "=" * 78)
    print(
        "V15-SG3 COMPLETED SUCCESSFULLY"
    )
    print(
        "Next milestone: V15-SG4"
    )
    print(
        "Conservative Darcy face fluxes"
    )
    print("=" * 78)


if __name__ == "__main__":
    main()