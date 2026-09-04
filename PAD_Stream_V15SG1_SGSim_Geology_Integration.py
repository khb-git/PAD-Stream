from pathlib import Path
import json

import numpy as np
import matplotlib.pyplot as plt


# ======================================================================
# PAD-Stream Version 15-SG1
# SGSim Geological Model Integration
#
# PURPOSE
# -------
# 1. Load the finalized 50 x 50 x 15 SGSim permeability realization.
# 2. Preserve SGeMS X-fastest / Y / Z ordering.
# 3. Construct directional permeability:
#       Kx = Ky = K_SGSim
#       Kz = 0.1 * K_SGSim
# 4. Construct constant porosity phi = 0.20.
# 5. Define the 20-ft injection unit: physical layers 6-10.
# 6. Define the initial full five-spot well geometry.
# 7. Construct the uniform initial pressure field, P0 = 2500 psi.
# 8. Generate diagnostics and validation outputs.
#
# IMPORTANT
# ---------
# This milestone performs NO pressure solve.
# ======================================================================


# ----------------------------------------------------------------------
# PROJECT PATHS
# ----------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

INPUT_PERM_FILE = ROOT / "SGSIM_50x50x15_PERM_MD.csv"

OUTPUT_DIR = ROOT / "output" / "V15_SG1"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG1_Summary.json"


# ----------------------------------------------------------------------
# GRID DEFINITION
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
# ROCK PROPERTIES
# ----------------------------------------------------------------------

POROSITY = 0.20

# Directional permeability treatment
KH_MULTIPLIER = 1.0
KV_KH_RATIO = 0.10


# ----------------------------------------------------------------------
# SGSim INJECTION UNIT
# ----------------------------------------------------------------------

# Physical SGeMS layers 6-10
#
# Python is zero-based:
#   SGeMS layer 6  -> Python k = 5
#   SGeMS layer 10 -> Python k = 9
#
# Slice stop is exclusive, therefore 5:10.
INJECTION_K_START = 5
INJECTION_K_STOP = 10

INJECTION_PHYSICAL_LAYER_START = 6
INJECTION_PHYSICAL_LAYER_STOP = 10

INJECTION_THICKNESS_FT = (
    INJECTION_K_STOP - INJECTION_K_START
) * DZ_FT


# ----------------------------------------------------------------------
# INITIAL PRESSURE / WELL SPECIFICATION
# ----------------------------------------------------------------------

INITIAL_PRESSURE_PSI = 2500.0
PRODUCER_BHP_PSI = 2000.0

# Rate will be introduced explicitly in the pressure-solver milestone.
# SG1 only defines the injector location/completion.
INJECTOR_CONTROL = "RATE_CONTROLLED_RATE_TBD_IN_SG3"

# Zero-based (j, i) indices.
#
# 50 x 50 has no single exact center cell.
# We choose (24,24), whose cell center is (490,490) ft.
INJECTOR_I = 24
INJECTOR_J = 24

# Near-corner producers with a 5-cell buffer from conceptual corners.
PRODUCERS = {
    "PROD_SW": {"i": 4, "j": 4},
    "PROD_SE": {"i": 45, "j": 4},
    "PROD_NW": {"i": 4, "j": 45},
    "PROD_NE": {"i": 45, "j": 45},
}


# ======================================================================
# UTILITY FUNCTIONS
# ======================================================================

def cell_center_x(i):
    """X coordinate of Cartesian cell center in ft."""
    return (i + 0.5) * DX_FT


def cell_center_y(j):
    """Y coordinate of Cartesian cell center in ft."""
    return (j + 0.5) * DY_FT


def cell_center_z(k):
    """Z coordinate of Cartesian cell center in ft."""
    return (k + 0.5) * DZ_FT


def load_permeability():
    """
    Load the one-property SGeMS permeability export.

    Expected file structure:

        PERM_MD
        value_1
        value_2
        ...

    Ordering:
        X fastest
        then Y
        then Z

    Therefore:
        reshape -> (NZ, NY, NX)
    """

    if not INPUT_PERM_FILE.exists():
        raise FileNotFoundError(
            f"\nCould not find SGSim permeability file:\n"
            f"{INPUT_PERM_FILE}"
        )

    values = np.loadtxt(
        INPUT_PERM_FILE,
        skiprows=1,
        dtype=float,
    )

    if values.size != N_CELLS:
        raise ValueError(
            f"SG1 GRID VALIDATION FAILED:\n"
            f"Expected {N_CELLS:,} permeability values for "
            f"{NX} x {NY} x {NZ}, but found {values.size:,}."
        )

    perm = values.reshape(
        (NZ, NY, NX),
        order="C",
    )

    return perm


def construct_reservoir_state(k_sgsim):
    """
    Build directional permeability, porosity,
    pressure, and injection-unit mask.
    """

    kx = KH_MULTIPLIER * k_sgsim.copy()
    ky = KH_MULTIPLIER * k_sgsim.copy()
    kz = KV_KH_RATIO * k_sgsim.copy()

    phi = np.full(
        (NZ, NY, NX),
        POROSITY,
        dtype=float,
    )

    pressure_initial = np.full(
        (NZ, NY, NX),
        INITIAL_PRESSURE_PSI,
        dtype=float,
    )

    injection_mask = np.zeros(
        (NZ, NY, NX),
        dtype=bool,
    )

    injection_mask[
        INJECTION_K_START:INJECTION_K_STOP,
        :,
        :
    ] = True

    return {
        "K": k_sgsim,
        "Kx": kx,
        "Ky": ky,
        "Kz": kz,
        "phi": phi,
        "P0": pressure_initial,
        "injection_mask": injection_mask,
    }


def construct_wells():
    """
    Construct well metadata.

    All five wells are initially completed only in
    physical SGeMS layers 6-10.
    """

    completion_k = list(
        range(INJECTION_K_START, INJECTION_K_STOP)
    )

    injector = {
        "name": "INJECTOR",
        "type": "injector",
        "i": INJECTOR_I,
        "j": INJECTOR_J,
        "x_ft": cell_center_x(INJECTOR_I),
        "y_ft": cell_center_y(INJECTOR_J),
        "completion_k_zero_based": completion_k,
        "completion_layers_one_based": list(
            range(
                INJECTION_PHYSICAL_LAYER_START,
                INJECTION_PHYSICAL_LAYER_STOP + 1,
            )
        ),
        "control": INJECTOR_CONTROL,
    }

    producers = {}

    for name, ij in PRODUCERS.items():

        i = ij["i"]
        j = ij["j"]

        producers[name] = {
            "name": name,
            "type": "producer",
            "i": i,
            "j": j,
            "x_ft": cell_center_x(i),
            "y_ft": cell_center_y(j),
            "completion_k_zero_based": completion_k,
            "completion_layers_one_based": list(
                range(
                    INJECTION_PHYSICAL_LAYER_START,
                    INJECTION_PHYSICAL_LAYER_STOP + 1,
                )
            ),
            "control": "FIXED_BHP",
            "bhp_psi": PRODUCER_BHP_PSI,
        }

    return injector, producers


# ======================================================================
# VALIDATION
# ======================================================================

def compute_statistics(state):

    k = state["K"]
    kx = state["Kx"]
    ky = state["Ky"]
    kz = state["Kz"]
    phi = state["phi"]
    p0 = state["P0"]

    background = np.concatenate(
        [
            k[:INJECTION_K_START].ravel(),
            k[INJECTION_K_STOP:].ravel(),
        ]
    )

    injection = k[
        INJECTION_K_START:INJECTION_K_STOP
    ].ravel()

    stats = {
        "grid": {
            "nx": NX,
            "ny": NY,
            "nz": NZ,
            "cells": int(N_CELLS),
            "dx_ft": DX_FT,
            "dy_ft": DY_FT,
            "dz_ft": DZ_FT,
            "lx_ft": LX_FT,
            "ly_ft": LY_FT,
            "lz_ft": LZ_FT,
        },

        "permeability_md": {
            "min": float(k.min()),
            "max": float(k.max()),
            "mean": float(k.mean()),
            "median": float(np.median(k)),
            "p10": float(np.percentile(k, 10)),
            "p90": float(np.percentile(k, 90)),
        },

        "background_md": {
            "cells": int(background.size),
            "min": float(background.min()),
            "max": float(background.max()),
            "mean": float(background.mean()),
            "median": float(np.median(background)),
        },

        "injection_unit_md": {
            "cells": int(injection.size),
            "min": float(injection.min()),
            "max": float(injection.max()),
            "mean": float(injection.mean()),
            "median": float(np.median(injection)),
        },

        "directional_permeability_md": {
            "kx_min": float(kx.min()),
            "kx_max": float(kx.max()),
            "ky_min": float(ky.min()),
            "ky_max": float(ky.max()),
            "kz_min": float(kz.min()),
            "kz_max": float(kz.max()),
            "kv_kh_ratio": KV_KH_RATIO,
        },

        "porosity": {
            "min": float(phi.min()),
            "max": float(phi.max()),
            "mean": float(phi.mean()),
        },

        "initial_pressure_psi": {
            "min": float(p0.min()),
            "max": float(p0.max()),
            "mean": float(p0.mean()),
        },
    }

    stats["injection_background_mean_k_ratio"] = float(
        injection.mean() / background.mean()
    )

    return stats


def run_validation_gates(state, stats):

    print("\n" + "=" * 78)
    print("V15-SG1 VALIDATION GATES")
    print("=" * 78)

    checks = []

    # Grid
    checks.append(
        (
            "Cell count = 37,500",
            state["K"].size == 37500,
        )
    )

    checks.append(
        (
            "Shape = (15, 50, 50)",
            state["K"].shape == (15, 50, 50),
        )
    )

    # Permeability range
    checks.append(
        (
            "Global K >= 50 mD",
            state["K"].min() >= 49.99,
        )
    )

    checks.append(
        (
            "Global K <= 1000 mD",
            state["K"].max() <= 1000.01,
        )
    )

    # Directional permeability
    checks.append(
        (
            "Kx equals SGSim K",
            np.allclose(state["Kx"], state["K"]),
        )
    )

    checks.append(
        (
            "Ky equals SGSim K",
            np.allclose(state["Ky"], state["K"]),
        )
    )

    checks.append(
        (
            "Kz = 0.1 Kh",
            np.allclose(
                state["Kz"],
                KV_KH_RATIO * state["K"],
            ),
        )
    )

    # Porosity
    checks.append(
        (
            "Constant phi = 0.20",
            np.allclose(state["phi"], 0.20),
        )
    )

    # Pressure
    checks.append(
        (
            "Initial pressure = 2500 psi",
            np.allclose(
                state["P0"],
                INITIAL_PRESSURE_PSI,
            ),
        )
    )

    # Injection mask
    expected_injection_cells = (
        NX
        * NY
        * (
            INJECTION_K_STOP
            - INJECTION_K_START
        )
    )

    checks.append(
        (
            "Injection unit contains 12,500 cells",
            int(state["injection_mask"].sum())
            == expected_injection_cells,
        )
    )

    # Mean permeability contrast
    checks.append(
        (
            "Injection mean K > background mean K",
            stats[
                "injection_unit_md"
            ]["mean"]
            >
            stats[
                "background_md"
            ]["mean"],
        )
    )

    all_passed = True

    for description, passed in checks:

        status = "PASS" if passed else "FAIL"

        print(
            f"[{status:4s}] {description}"
        )

        if not passed:
            all_passed = False

    print("=" * 78)

    if not all_passed:
        raise RuntimeError(
            "V15-SG1 validation failed. "
            "Do not proceed to SG2."
        )

    print(
        "V15-SG1 GEOLOGICAL MODEL VALIDATION: PASS"
    )

    return True


# ======================================================================
# DIAGNOSTIC PLOTS
# ======================================================================

def plot_layer8(k, injector, producers):

    layer_number = 8
    k_index = layer_number - 1

    fig, ax = plt.subplots(
        figsize=(8, 7)
    )

    im = ax.imshow(
        k[k_index],
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
        "Permeability (mD)"
    )

    # Injector
    ax.scatter(
        injector["x_ft"],
        injector["y_ft"],
        marker="*",
        s=180,
        label="Injector",
    )

    # Producers
    for name, well in producers.items():

        ax.scatter(
            well["x_ft"],
            well["y_ft"],
            marker="s",
            s=80,
            label=name,
        )

    ax.set_title(
        "PAD-Stream V15-SG1\n"
        "SGSim Permeability - Layer 8"
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Y (ft)")

    ax.legend(
        loc="upper right",
        fontsize=8,
    )

    fig.tight_layout()

    outfile = (
        OUTPUT_DIR
        / "V15SG1_PERM_Layer08_FiveSpot.png"
    )

    fig.savefig(
        outfile,
        dpi=300,
    )

    plt.close(fig)


def plot_vertical_section(k):

    middle_y = NY // 2

    section = k[
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
        "Permeability (mD)"
    )

    # Injection interval boundaries
    z_bottom = INJECTION_K_START * DZ_FT
    z_top = INJECTION_K_STOP * DZ_FT

    ax.axhline(
        z_bottom,
        linestyle="--",
        linewidth=1.5,
    )

    ax.axhline(
        z_top,
        linestyle="--",
        linewidth=1.5,
    )

    ax.set_title(
        "PAD-Stream V15-SG1\n"
        "SGSim Vertical Permeability Section"
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Z (ft)")

    fig.tight_layout()

    outfile = (
        OUTPUT_DIR
        / "V15SG1_PERM_VerticalSection.png"
    )

    fig.savefig(
        outfile,
        dpi=300,
    )

    plt.close(fig)


def plot_permeability_histogram(k):

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.hist(
        k.ravel(),
        bins=50,
    )

    ax.set_xlabel(
        "Permeability (mD)"
    )

    ax.set_ylabel(
        "Cell count"
    )

    ax.set_title(
        "PAD-Stream V15-SG1\n"
        "SGSim Permeability Distribution"
    )

    fig.tight_layout()

    outfile = (
        OUTPUT_DIR
        / "V15SG1_PERM_Histogram.png"
    )

    fig.savefig(
        outfile,
        dpi=300,
    )

    plt.close(fig)


def plot_kz_layer8(kz):

    layer_number = 8
    k_index = layer_number - 1

    fig, ax = plt.subplots(
        figsize=(8, 7)
    )

    im = ax.imshow(
        kz[k_index],
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
        "Vertical Permeability Kz (mD)"
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Y (ft)")

    ax.set_title(
        "PAD-Stream V15-SG1\n"
        "Vertical Permeability Kz - Layer 8"
    )

    fig.tight_layout()

    outfile = (
        OUTPUT_DIR
        / "V15SG1_KZ_Layer08.png"
    )

    fig.savefig(
        outfile,
        dpi=300,
    )

    plt.close(fig)


# ======================================================================
# SUMMARY FILE
# ======================================================================

def save_summary(
    stats,
    injector,
    producers,
):

    summary = {
        "milestone": "V15-SG1",
        "description":
            "SGSim Geological Model Integration",

        "status": "PASS",

        "input_file":
            str(INPUT_PERM_FILE),

        "grid":
            stats["grid"],

        "permeability_md":
            stats["permeability_md"],

        "background_md":
            stats["background_md"],

        "injection_unit_md":
            stats["injection_unit_md"],

        "directional_permeability_md":
            stats[
                "directional_permeability_md"
            ],

        "porosity":
            stats["porosity"],

        "initial_pressure_psi":
            stats[
                "initial_pressure_psi"
            ],

        "injection_background_mean_k_ratio":
            stats[
                "injection_background_mean_k_ratio"
            ],

        "injection_unit": {
            "physical_layers":
                "6-10",

            "python_k_indices":
                "5:10",

            "thickness_ft":
                INJECTION_THICKNESS_FT,
        },

        "boundary_conditions": {
            "external_faces":
                "NO_FLOW",

            "top":
                "NO_FLOW",

            "bottom":
                "NO_FLOW",
        },

        "injector":
            injector,

        "producers":
            producers,

        "pressure_solve_performed":
            False,

        "next_milestone":
            "V15-SG2 - 3D anisotropic finite-volume transmissibilities",
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
        "PAD-Stream Version 15-SG1"
    )
    print(
        "SGSim Geological Model Integration"
    )
    print("=" * 78)

    print(
        f"\nInput permeability file:\n"
        f"  {INPUT_PERM_FILE}"
    )

    # --------------------------------------------------------------
    # 1. Load SGSim permeability
    # --------------------------------------------------------------

    k_sgsim = load_permeability()

    print(
        "\nSGSim permeability loaded successfully."
    )

    print(
        f"Array shape: {k_sgsim.shape}"
    )

    # --------------------------------------------------------------
    # 2. Build reservoir state
    # --------------------------------------------------------------

    state = construct_reservoir_state(
        k_sgsim
    )

    # --------------------------------------------------------------
    # 3. Define five-spot wells
    # --------------------------------------------------------------

    injector, producers = construct_wells()

    # --------------------------------------------------------------
    # 4. Compute statistics
    # --------------------------------------------------------------

    stats = compute_statistics(
        state
    )

    print("\nGRID")
    print(
        f"  Shape                 : "
        f"{NX} x {NY} x {NZ}"
    )
    print(
        f"  Cells                 : "
        f"{N_CELLS:,}"
    )
    print(
        f"  Cell dimensions       : "
        f"{DX_FT} x {DY_FT} x {DZ_FT} ft"
    )
    print(
        f"  Physical dimensions   : "
        f"{LX_FT} x {LY_FT} x {LZ_FT} ft"
    )

    print("\nPERMEABILITY")
    print(
        f"  Global min            : "
        f"{stats['permeability_md']['min']:.3f} mD"
    )
    print(
        f"  Global max            : "
        f"{stats['permeability_md']['max']:.3f} mD"
    )
    print(
        f"  Global mean           : "
        f"{stats['permeability_md']['mean']:.3f} mD"
    )
    print(
        f"  Background mean       : "
        f"{stats['background_md']['mean']:.3f} mD"
    )
    print(
        f"  Injection-unit mean   : "
        f"{stats['injection_unit_md']['mean']:.3f} mD"
    )

    print("\nDIRECTIONAL PERMEABILITY")
    print(
        "  Kx = K_SGSim"
    )
    print(
        "  Ky = K_SGSim"
    )
    print(
        f"  Kz = {KV_KH_RATIO:.2f} K_SGSim"
    )
    print(
        f"  Kz max                : "
        f"{stats['directional_permeability_md']['kz_max']:.3f} mD"
    )

    print("\nPOROSITY")
    print(
        f"  phi                    : "
        f"{POROSITY:.3f}"
    )

    print("\nINJECTION UNIT")
    print(
        "  Physical layers        : 6-10"
    )
    print(
        "  Python indices          : 5:10"
    )
    print(
        f"  Thickness               : "
        f"{INJECTION_THICKNESS_FT:.1f} ft"
    )

    print("\nFIVE-SPOT WELL GEOMETRY")

    print(
        f"  Injector                : "
        f"(i={injector['i']}, "
        f"j={injector['j']})"
    )

    print(
        f"  Injector coordinates    : "
        f"({injector['x_ft']:.1f}, "
        f"{injector['y_ft']:.1f}) ft"
    )

    for name, well in producers.items():

        print(
            f"  {name:23s}: "
            f"(i={well['i']}, "
            f"j={well['j']}) "
            f"-> "
            f"({well['x_ft']:.1f}, "
            f"{well['y_ft']:.1f}) ft"
        )

    print("\nINITIAL PRESSURE / BOUNDARIES")
    print(
        f"  Initial pressure        : "
        f"{INITIAL_PRESSURE_PSI:.1f} psi"
    )
    print(
        f"  Producer BHP            : "
        f"{PRODUCER_BHP_PSI:.1f} psi"
    )
    print(
        "  External boundaries     : NO FLOW"
    )
    print(
        "  Pressure solve           : NOT PERFORMED IN SG1"
    )

    # --------------------------------------------------------------
    # 5. Validation gates
    # --------------------------------------------------------------

    run_validation_gates(
        state,
        stats,
    )

    # --------------------------------------------------------------
    # 6. Diagnostic plots
    # --------------------------------------------------------------

    plot_layer8(
        state["K"],
        injector,
        producers,
    )

    plot_vertical_section(
        state["K"]
    )

    plot_permeability_histogram(
        state["K"]
    )

    plot_kz_layer8(
        state["Kz"]
    )

    # --------------------------------------------------------------
    # 7. Save summary
    # --------------------------------------------------------------

    save_summary(
        stats,
        injector,
        producers,
    )

    print("\nOUTPUTS")
    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print(
        f"\n  Summary:\n"
        f"    {SUMMARY_FILE}"
    )

    print("\nGenerated diagnostics:")
    print(
        "  V15SG1_PERM_Layer08_FiveSpot.png"
    )
    print(
        "  V15SG1_PERM_VerticalSection.png"
    )
    print(
        "  V15SG1_PERM_Histogram.png"
    )
    print(
        "  V15SG1_KZ_Layer08.png"
    )

    print("\n" + "=" * 78)
    print(
        "V15-SG1 COMPLETED SUCCESSFULLY"
    )
    print(
        "Next milestone: V15-SG2"
    )
    print(
        "3D anisotropic finite-volume transmissibilities"
    )
    print("=" * 78)


if __name__ == "__main__":
    main()