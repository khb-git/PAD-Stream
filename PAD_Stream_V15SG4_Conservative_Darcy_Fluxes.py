from pathlib import Path
import json

import numpy as np
import matplotlib.pyplot as plt


# ======================================================================
# PAD-Stream Version 15-SG4
# Conservative Darcy Face Fluxes
#
# PURPOSE
# -------
# 1. Load frozen SG2 face permeability fields.
# 2. Load frozen SG3 pressure solution.
# 3. Reconstruct SI transmissibilities.
# 4. Compute Darcy volumetric flux on every internal face.
# 5. Include gravity consistently in vertical flux.
# 6. Construct cell-wise flux divergence.
# 7. Compare divergence against injector / producer well terms.
# 8. Validate local and global conservation.
#
# NO Pollock tracing or transport is performed here.
# ======================================================================


# ----------------------------------------------------------------------
# PATHS
# ----------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

SG1_PERM_FILE = ROOT / "SGSIM_50x50x15_PERM_MD.csv"

SG2_DIR = ROOT / "output" / "V15_SG2"
SG3_DIR = ROOT / "output" / "V15_SG3"

KFACE_X_FILE = SG2_DIR / "KFACE_X.npy"
KFACE_Y_FILE = SG2_DIR / "KFACE_Y.npy"
KFACE_Z_FILE = SG2_DIR / "KFACE_Z.npy"

PRESSURE_FILE = SG3_DIR / "PRESSURE_PSI.npy"

OUTPUT_DIR = ROOT / "output" / "V15_SG4"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG4_Summary.json"


# ----------------------------------------------------------------------
# GRID
# ----------------------------------------------------------------------

NX = 50
NY = 50
NZ = 15

DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0

LX_FT = NX * DX_FT
LY_FT = NY * DY_FT
LZ_FT = NZ * DZ_FT

N_CELLS = NX * NY * NZ


# ----------------------------------------------------------------------
# UNIT CONVERSIONS
# ----------------------------------------------------------------------

FT_TO_M = 0.3048
MD_TO_M2 = 9.869233e-16
CP_TO_PA_S = 1.0e-3

PSI_TO_PA = 6894.757293168

DAY_TO_S = 86400.0
TONNE_TO_KG = 1000.0


# ----------------------------------------------------------------------
# SI GRID GEOMETRY
# ----------------------------------------------------------------------

DX_M = DX_FT * FT_TO_M
DY_M = DY_FT * FT_TO_M
DZ_M = DZ_FT * FT_TO_M

AX_M2 = DY_M * DZ_M
AY_M2 = DX_M * DZ_M
AZ_M2 = DX_M * DY_M


# ----------------------------------------------------------------------
# FLUID / GRAVITY
# ----------------------------------------------------------------------

MU_REF_CP = 0.50
MU_REF_PA_S = MU_REF_CP * CP_TO_PA_S

RHO_BRINE_KG_M3 = 1020.0
G_M_S2 = 9.80665

GRAVITY_ON = True


# ----------------------------------------------------------------------
# WELL CONTROLS — MUST MATCH SG3
# ----------------------------------------------------------------------

CO2_MASS_RATE_TONNES_DAY = 500.0
CO2_DENSITY_KG_M3 = 700.0

Q_INJ_M3_S = (
    CO2_MASS_RATE_TONNES_DAY
    * TONNE_TO_KG
    / DAY_TO_S
    / CO2_DENSITY_KG_M3
)

PRODUCER_BHP_PSI = 2000.0
PRODUCER_BHP_PA = PRODUCER_BHP_PSI * PSI_TO_PA

WELL_RADIUS_FT = 0.25
WELL_RADIUS_M = WELL_RADIUS_FT * FT_TO_M

SKIN = 0.0

INJECTOR_I = 24
INJECTOR_J = 24

PRODUCERS = {
    "PROD_SW": {"i": 4, "j": 4},
    "PROD_SE": {"i": 45, "j": 4},
    "PROD_NW": {"i": 4, "j": 45},
    "PROD_NE": {"i": 45, "j": 45},
}

COMPLETION_K = list(range(5, 10))

Q_INJ_PERF_M3_S = (
    Q_INJ_M3_S / len(COMPLETION_K)
)


# ======================================================================
# LOAD DATA
# ======================================================================

def load_inputs():

    required = [
        SG1_PERM_FILE,
        KFACE_X_FILE,
        KFACE_Y_FILE,
        KFACE_Z_FILE,
        PRESSURE_FILE,
    ]

    for path in required:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing required frozen input:\n{path}"
            )

    k_values = np.loadtxt(
        SG1_PERM_FILE,
        skiprows=1,
        dtype=float,
    )

    k_cell = k_values.reshape(
        (NZ, NY, NX),
        order="C",
    )

    kfx_md = np.load(KFACE_X_FILE)
    kfy_md = np.load(KFACE_Y_FILE)
    kfz_md = np.load(KFACE_Z_FILE)

    pressure_psi = np.load(PRESSURE_FILE)

    if pressure_psi.shape != (NZ, NY, NX):
        raise ValueError(
            f"Invalid pressure shape: {pressure_psi.shape}"
        )

    return (
        k_cell,
        kfx_md,
        kfy_md,
        kfz_md,
        pressure_psi,
    )


# ======================================================================
# TRANSMISSIBILITY
# ======================================================================

def construct_si_transmissibilities(
    kfx_md,
    kfy_md,
    kfz_md,
):

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
# FACE FLUXES
# ======================================================================

def compute_face_fluxes(
    pressure_psi,
    tx,
    ty,
    tz,
):

    p_pa = pressure_psi * PSI_TO_PA

    # --------------------------------------------------------------
    # X faces
    #
    # Positive qx means flow in +X:
    # cell i -> cell i+1
    # --------------------------------------------------------------

    dp_x = (
        p_pa[:, :, 1:]
        - p_pa[:, :, :-1]
    )

    qx = -tx * dp_x

    # --------------------------------------------------------------
    # Y faces
    #
    # Positive qy means flow in +Y:
    # cell j -> cell j+1
    # --------------------------------------------------------------

    dp_y = (
        p_pa[:, 1:, :]
        - p_pa[:, :-1, :]
    )

    qy = -ty * dp_y

    # --------------------------------------------------------------
    # Z faces
    #
    # Positive qz means flow upward (+Z):
    # layer k -> layer k+1
    #
    # Darcy:
    #
    # q = -T [ DeltaP + rho g DeltaZ ]
    #
    # for z positive upward.
    # --------------------------------------------------------------

    dp_z = (
        p_pa[1:, :, :]
        - p_pa[:-1, :, :]
    )

    dz = DZ_M

    if GRAVITY_ON:

        potential_difference = (
            dp_z
            + RHO_BRINE_KG_M3
            * G_M_S2
            * dz
        )

    else:

        potential_difference = dp_z

    qz = (
        -tz
        * potential_difference
    )

    return qx, qy, qz


# ======================================================================
# CELL FLUX DIVERGENCE
# ======================================================================

def compute_flux_divergence(
    qx,
    qy,
    qz,
):
    """
    Net outward volumetric rate from each cell.

    Positive:
        net flow leaving cell.

    Negative:
        net flow entering cell.

    Internal-face contributions cancel exactly when summed globally.
    """

    div = np.zeros(
        (NZ, NY, NX),
        dtype=float,
    )

    # X faces
    div[:, :, :-1] += qx
    div[:, :, 1:] -= qx

    # Y faces
    div[:, :-1, :] += qy
    div[:, 1:, :] -= qy

    # Z faces
    div[:-1, :, :] += qz
    div[1:, :, :] -= qz

    return div


# ======================================================================
# PEACEMAN PRODUCER RATE
# ======================================================================

def peaceman_well_index_si(
    kx_md,
    ky_md,
):

    kx = kx_md * MD_TO_M2
    ky = ky_md * MD_TO_M2

    ratio_yx = np.sqrt(ky / kx)
    ratio_xy = np.sqrt(kx / ky)

    numerator = (
        0.28
        * np.sqrt(
            ratio_yx * DX_M**2
            +
            ratio_xy * DY_M**2
        )
    )

    denominator = (
        (ky / kx) ** 0.25
        +
        (kx / ky) ** 0.25
    )

    re = numerator / denominator

    kh = np.sqrt(kx * ky)

    wi = (
        2.0
        * np.pi
        * kh
        * DZ_M
        /
        (
            MU_REF_PA_S
            * (
                np.log(
                    re / WELL_RADIUS_M
                )
                + SKIN
            )
        )
    )

    return wi


def construct_expected_well_rates(
    k_cell,
    pressure_psi,
):

    p_pa = pressure_psi * PSI_TO_PA

    well_source = np.zeros(
        (NZ, NY, NX),
        dtype=float,
    )

    # --------------------------------------------------------------
    # Injector
    #
    # Positive source means injection INTO the reservoir.
    # For our outward-divergence convention,
    # expected div = + source.
    # --------------------------------------------------------------

    for k in COMPLETION_K:

        well_source[
            k,
            INJECTOR_J,
            INJECTOR_I,
        ] += Q_INJ_PERF_M3_S

    # --------------------------------------------------------------
    # Producers
    #
    # Producer withdrawal is negative source.
    # --------------------------------------------------------------

    producer_rates = {}

    for name, well in PRODUCERS.items():

        i = well["i"]
        j = well["j"]

        q_total = 0.0

        perf_rates = []

        for k in COMPLETION_K:

            wi = peaceman_well_index_si(
                k_cell[k, j, i],
                k_cell[k, j, i],
            )

            q_prod = (
                wi
                * (
                    p_pa[k, j, i]
                    - PRODUCER_BHP_PA
                )
            )

            # production is a sink
            well_source[k, j, i] -= q_prod

            q_total += q_prod

            perf_rates.append(
                q_prod * DAY_TO_S
            )

        producer_rates[name] = {
            "m3_day": float(
                q_total * DAY_TO_S
            ),
            "perf_m3_day": [
                float(x)
                for x in perf_rates
            ],
        }

    return (
        well_source,
        producer_rates,
    )


# ======================================================================
# CONSERVATION VALIDATION
# ======================================================================

def validate_conservation(
    qx,
    qy,
    qz,
    div,
    well_source,
):

    # --------------------------------------------------------------
    # IMPORTANT SIGN CONVENTION
    #
    # div = net outward internal-face flow.
    #
    # For steady conservation:
    #
    # div = source
    #
    # Injection source > 0
    # Production source < 0
    # --------------------------------------------------------------

    error = (
        div
        - well_source
    )

    max_abs_error = np.max(
        np.abs(error)
    )

    l2_error = np.linalg.norm(
        error.ravel()
    )

    source_norm = np.linalg.norm(
        well_source.ravel()
    )

    relative_error = (
        l2_error
        / max(source_norm, 1.0e-30)
    )

    global_divergence = float(
        div.sum()
    )

    global_well_source = float(
        well_source.sum()
    )

    global_mismatch = (
        global_divergence
        - global_well_source
    )

    qinj = Q_INJ_M3_S

    global_relative_mismatch = (
        abs(global_mismatch)
        / qinj
    )

    # Non-well cell mask
    well_mask = (
        np.abs(well_source) > 0.0
    )

    nonwell_error = np.abs(
        div[~well_mask]
    )

    max_nonwell_div = (
        float(nonwell_error.max())
        if nonwell_error.size
        else 0.0
    )

    print("\n" + "=" * 78)
    print("V15-SG4 CONSERVATION VALIDATION")
    print("=" * 78)

    checks = [
        (
            "Qx shape = (15, 50, 49)",
            qx.shape
            == (15, 50, 49),
        ),
        (
            "Qy shape = (15, 49, 50)",
            qy.shape
            == (15, 49, 50),
        ),
        (
            "Qz shape = (14, 50, 50)",
            qz.shape
            == (14, 50, 50),
        ),
        (
            "All face fluxes finite",
            (
                np.all(np.isfinite(qx))
                and np.all(np.isfinite(qy))
                and np.all(np.isfinite(qz))
            ),
        ),
        (
            "Local conservation relative L2 error < 1e-8",
            relative_error < 1.0e-8,
        ),
        (
            "Global conservation mismatch < 1e-8 injection rate",
            global_relative_mismatch < 1.0e-8,
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
        f"Local relative L2 error    : "
        f"{relative_error:.6e}"
    )

    print(
        f"Maximum absolute cell error: "
        f"{max_abs_error:.6e} m3/s"
    )

    print(
        f"Maximum non-well divergence: "
        f"{max_nonwell_div:.6e} m3/s"
    )

    print(
        f"Global divergence sum      : "
        f"{global_divergence:.6e} m3/s"
    )

    print(
        f"Global well-source sum     : "
        f"{global_well_source:.6e} m3/s"
    )

    print(
        f"Global relative mismatch   : "
        f"{global_relative_mismatch:.6e}"
    )

    if not all_passed:
        raise RuntimeError(
            "V15-SG4 conservation validation failed."
        )

    print(
        "V15-SG4 CONSERVATIVE FLUX VALIDATION: PASS"
    )

    return {
        "local_relative_l2_error":
            float(relative_error),

        "maximum_absolute_cell_error_m3_s":
            float(max_abs_error),

        "maximum_nonwell_divergence_m3_s":
            float(max_nonwell_div),

        "global_divergence_m3_s":
            float(global_divergence),

        "global_well_source_m3_s":
            float(global_well_source),

        "global_relative_mismatch":
            float(global_relative_mismatch),
    }


# ======================================================================
# DIAGNOSTIC PLOTS
# ======================================================================

def cell_center_velocity_layer8(
    qx,
    qy,
):
    """
    Build simple cell-centered XY flux components by averaging
    neighboring face volumetric rates.

    These are for visualization only.

    Pollock in SG5 will use the actual face flux arrays directly.
    """

    k = 7

    qx_cell = np.zeros(
        (NY, NX),
        dtype=float,
    )

    qy_cell = np.zeros(
        (NY, NX),
        dtype=float,
    )

    # X component
    qx_cell[:, 0] = qx[k, :, 0]
    qx_cell[:, -1] = qx[k, :, -1]

    qx_cell[:, 1:-1] = (
        0.5
        * (
            qx[k, :, :-1]
            +
            qx[k, :, 1:]
        )
    )

    # Y component
    qy_cell[0, :] = qy[k, 0, :]
    qy_cell[-1, :] = qy[k, -1, :]

    qy_cell[1:-1, :] = (
        0.5
        * (
            qy[k, :-1, :]
            +
            qy[k, 1:, :]
        )
    )

    return qx_cell, qy_cell


def plot_flux_magnitude_layer8(
    qx,
    qy,
):

    qxc, qyc = (
        cell_center_velocity_layer8(
            qx,
            qy,
        )
    )

    mag = np.sqrt(
        qxc**2
        +
        qyc**2
    )

    mag_day = (
        mag * DAY_TO_S
    )

    fig, ax = plt.subplots(
        figsize=(8, 7)
    )

    im = ax.imshow(
        mag_day,
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
        "Approx. horizontal cell flux magnitude (m³/day)"
    )

    ax.set_title(
        "PAD-Stream V15-SG4\n"
        "Horizontal Darcy Flux Magnitude - Layer 8"
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Y (ft)")

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG4_FluxMagnitude_Layer08.png",
        dpi=300,
    )

    plt.close(fig)


def plot_flux_vectors_layer8(
    qx,
    qy,
):

    qxc, qyc = (
        cell_center_velocity_layer8(
            qx,
            qy,
        )
    )

    qxc = qxc * DAY_TO_S
    qyc = qyc * DAY_TO_S

    x = np.arange(NX) * DX_FT + DX_FT / 2
    y = np.arange(NY) * DY_FT + DY_FT / 2

    X, Y = np.meshgrid(
        x,
        y,
    )

    skip = 3

    fig, ax = plt.subplots(
        figsize=(8, 7)
    )

    mag = np.sqrt(
        qxc**2
        +
        qyc**2
    )

    im = ax.imshow(
        mag,
        origin="lower",
        extent=[
            0,
            LX_FT,
            0,
            LY_FT,
        ],
        aspect="equal",
    )

    fig.colorbar(
        im,
        ax=ax,
        label="Approx. horizontal flux magnitude (m³/day)",
    )

    ax.quiver(
        X[::skip, ::skip],
        Y[::skip, ::skip],
        qxc[::skip, ::skip],
        qyc[::skip, ::skip],
    )

    ax.set_title(
        "PAD-Stream V15-SG4\n"
        "Darcy Flux Directions - Layer 8"
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Y (ft)")

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG4_FluxVectors_Layer08.png",
        dpi=300,
    )

    plt.close(fig)


def plot_vertical_flux_section(
    qz,
):

    middle_y = NY // 2

    section = (
        qz[:, middle_y, :]
        * DAY_TO_S
    )

    fig, ax = plt.subplots(
        figsize=(10, 4)
    )

    vmax = np.max(
        np.abs(section)
    )

    im = ax.imshow(
        section,
        origin="lower",
        extent=[
            0,
            LX_FT,
            DZ_FT,
            LZ_FT - DZ_FT,
        ],
        aspect="auto",
        vmin=-vmax,
        vmax=vmax,
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
    )

    cbar.set_label(
        "Vertical face flux qz (m³/day)"
    )

    ax.axhline(
        20.0,
        linestyle="--",
    )

    ax.axhline(
        40.0,
        linestyle="--",
    )

    ax.set_title(
        "PAD-Stream V15-SG4\n"
        "Vertical Darcy Flux Section"
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Z (ft)")

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG4_QZ_VerticalSection.png",
        dpi=300,
    )

    plt.close(fig)


def plot_divergence_layer8(
    div,
    well_source,
):

    k = 7

    residual = (
        div[k]
        - well_source[k]
    ) * DAY_TO_S

    fig, ax = plt.subplots(
        figsize=(8, 7)
    )

    vmax = np.max(
        np.abs(residual)
    )

    if vmax == 0.0:
        vmax = 1.0e-12

    im = ax.imshow(
        residual,
        origin="lower",
        extent=[
            0,
            LX_FT,
            0,
            LY_FT,
        ],
        aspect="equal",
        vmin=-vmax,
        vmax=vmax,
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
    )

    cbar.set_label(
        "Conservation residual (m³/day)"
    )

    ax.set_title(
        "PAD-Stream V15-SG4\n"
        "Cell Conservation Residual - Layer 8"
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Y (ft)")

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG4_ConservationResidual_Layer08.png",
        dpi=300,
    )

    plt.close(fig)


# ======================================================================
# SAVE OUTPUTS
# ======================================================================

def save_outputs(
    qx,
    qy,
    qz,
    div,
    well_source,
):

    np.save(
        OUTPUT_DIR / "QX_M3_S.npy",
        qx,
    )

    np.save(
        OUTPUT_DIR / "QY_M3_S.npy",
        qy,
    )

    np.save(
        OUTPUT_DIR / "QZ_M3_S.npy",
        qz,
    )

    np.save(
        OUTPUT_DIR / "FLUX_DIVERGENCE_M3_S.npy",
        div,
    )

    np.save(
        OUTPUT_DIR / "WELL_SOURCE_M3_S.npy",
        well_source,
    )


def stats(a):

    return {
        "shape": list(a.shape),
        "min": float(a.min()),
        "max": float(a.max()),
        "mean": float(a.mean()),
        "mean_abs": float(
            np.mean(np.abs(a))
        ),
    }


def save_summary(
    qx,
    qy,
    qz,
    producer_rates,
    conservation,
):

    summary = {
        "milestone":
            "V15-SG4",

        "description":
            "Conservative Darcy face fluxes",

        "status":
            "PASS",

        "sign_convention": {
            "qx_positive":
                "+X",
            "qy_positive":
                "+Y",
            "qz_positive":
                "+Z/upward",
            "divergence_positive":
                "net outward rate",
        },

        "fluid": {
            "reference_viscosity_cp":
                MU_REF_CP,
            "brine_density_kg_m3":
                RHO_BRINE_KG_M3,
            "gravity_on":
                GRAVITY_ON,
        },

        "qx_m3_s":
            stats(qx),

        "qy_m3_s":
            stats(qy),

        "qz_m3_s":
            stats(qz),

        "producer_rates":
            producer_rates,

        "conservation":
            conservation,

        "next_milestone":
            "V15-SG5 - Pollock streamline tracing",
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
    print("PAD-Stream Version 15-SG4")
    print("Conservative Darcy Face Fluxes")
    print("=" * 78)

    (
        k_cell,
        kfx_md,
        kfy_md,
        kfz_md,
        pressure_psi,
    ) = load_inputs()

    tx, ty, tz = (
        construct_si_transmissibilities(
            kfx_md,
            kfy_md,
            kfz_md,
        )
    )

    qx, qy, qz = (
        compute_face_fluxes(
            pressure_psi,
            tx,
            ty,
            tz,
        )
    )

    print("\nFACE FLUX ARRAYS")

    print(
        f"  Qx shape               : {qx.shape}"
    )

    print(
        f"  Qy shape               : {qy.shape}"
    )

    print(
        f"  Qz shape               : {qz.shape}"
    )

    print("\nFACE FLUX STATISTICS")

    print(
        f"  Qx min/max             : "
        f"{qx.min()*DAY_TO_S:.6f} / "
        f"{qx.max()*DAY_TO_S:.6f} m3/day"
    )

    print(
        f"  Qy min/max             : "
        f"{qy.min()*DAY_TO_S:.6f} / "
        f"{qy.max()*DAY_TO_S:.6f} m3/day"
    )

    print(
        f"  Qz min/max             : "
        f"{qz.min()*DAY_TO_S:.6f} / "
        f"{qz.max()*DAY_TO_S:.6f} m3/day"
    )

    div = compute_flux_divergence(
        qx,
        qy,
        qz,
    )

    (
        well_source,
        producer_rates,
    ) = construct_expected_well_rates(
        k_cell,
        pressure_psi,
    )

    print("\nPRODUCER RATES RECONSTRUCTED FROM SG3 PRESSURE")

    total_prod = 0.0

    for name, data in producer_rates.items():

        print(
            f"  {name:10s}             : "
            f"{data['m3_day']:.6f} m3/day"
        )

        total_prod += data[
            "m3_day"
        ]

    print(
        f"  Total production       : "
        f"{total_prod:.6f} m3/day"
    )

    print(
        f"  Total injection        : "
        f"{Q_INJ_M3_S * DAY_TO_S:.6f} m3/day"
    )

    conservation = (
        validate_conservation(
            qx,
            qy,
            qz,
            div,
            well_source,
        )
    )

    save_outputs(
        qx,
        qy,
        qz,
        div,
        well_source,
    )

    plot_flux_magnitude_layer8(
        qx,
        qy,
    )

    plot_flux_vectors_layer8(
        qx,
        qy,
    )

    plot_vertical_flux_section(
        qz,
    )

    plot_divergence_layer8(
        div,
        well_source,
    )

    save_summary(
        qx,
        qy,
        qz,
        producer_rates,
        conservation,
    )

    print("\nOUTPUTS")

    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print("\nSaved arrays:")
    print("  QX_M3_S.npy")
    print("  QY_M3_S.npy")
    print("  QZ_M3_S.npy")
    print("  FLUX_DIVERGENCE_M3_S.npy")
    print("  WELL_SOURCE_M3_S.npy")

    print("\nSaved diagnostics:")
    print("  V15SG4_FluxMagnitude_Layer08.png")
    print("  V15SG4_FluxVectors_Layer08.png")
    print("  V15SG4_QZ_VerticalSection.png")
    print("  V15SG4_ConservationResidual_Layer08.png")

    print("\n" + "=" * 78)
    print(
        "V15-SG4 COMPLETED SUCCESSFULLY"
    )
    print(
        "Next milestone: V15-SG5"
    )
    print(
        "Exact Pollock streamline tracing"
    )
    print("=" * 78)


if __name__ == "__main__":
    main()