from pathlib import Path
import json

import numpy as np
import matplotlib.pyplot as plt


# ======================================================================
# PAD-Stream Version 15-SG2
# 3D Anisotropic Finite-Volume Transmissibility Construction
#
# PURPOSE
# -------
# 1. Load the frozen SGSim permeability realization.
# 2. Reconstruct:
#       Kx = Ky = K_SGSim
#       Kz = 0.1 K_SGSim
# 3. Compute harmonic face permeability.
# 4. Compute Tx, Ty, Tz on all internal Cartesian faces.
# 5. Validate face counts, positivity, and anisotropic behavior.
#
# IMPORTANT
# ---------
# This milestone performs NO pressure solve and NO well control.
# ======================================================================


# ----------------------------------------------------------------------
# PROJECT PATHS
# ----------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

INPUT_PERM_FILE = ROOT / "SGSIM_50x50x15_PERM_MD.csv"

OUTPUT_DIR = ROOT / "output" / "V15_SG2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG2_Summary.json"


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


# ----------------------------------------------------------------------
# ROCK / FLUID
# ----------------------------------------------------------------------

KV_KH_RATIO = 0.10

# Reference viscosity for transmissibility validation.
# Mobility coupling will be introduced later.
MU_CP = 1.0


# ----------------------------------------------------------------------
# FACE AREAS
# ----------------------------------------------------------------------

AX_FT2 = DY_FT * DZ_FT      # face normal to x
AY_FT2 = DX_FT * DZ_FT      # face normal to y
AZ_FT2 = DX_FT * DY_FT      # face normal to z


# ======================================================================
# LOAD GEOLOGY
# ======================================================================

def load_permeability():

    if not INPUT_PERM_FILE.exists():
        raise FileNotFoundError(
            f"Could not find:\n{INPUT_PERM_FILE}"
        )

    values = np.loadtxt(
        INPUT_PERM_FILE,
        skiprows=1,
        dtype=float,
    )

    if values.size != N_CELLS:
        raise ValueError(
            f"Expected {N_CELLS:,} values, "
            f"found {values.size:,}."
        )

    return values.reshape(
        (NZ, NY, NX),
        order="C",
    )


# ======================================================================
# HARMONIC AVERAGING
# ======================================================================

def harmonic_average(a, b):
    """
    Harmonic average of two positive permeability values.
    """

    return 2.0 * a * b / (a + b)


# ======================================================================
# TRANSMISSIBILITY CONSTRUCTION
# ======================================================================

def build_directional_permeability(k):

    kx = k.copy()
    ky = k.copy()
    kz = KV_KH_RATIO * k

    return kx, ky, kz


def build_face_permeabilities(kx, ky, kz):
    """
    Internal face permeability arrays.

    Shapes:
        kfx : (NZ, NY, NX-1)
        kfy : (NZ, NY-1, NX)
        kfz : (NZ-1, NY, NX)
    """

    kfx = harmonic_average(
        kx[:, :, :-1],
        kx[:, :, 1:],
    )

    kfy = harmonic_average(
        ky[:, :-1, :],
        ky[:, 1:, :],
    )

    kfz = harmonic_average(
        kz[:-1, :, :],
        kz[1:, :, :],
    )

    return kfx, kfy, kfz


def build_transmissibilities(kfx, kfy, kfz):
    """
    Geometric finite-volume transmissibilities.

    Units remain in:
        mD * ft / cP

    Conversion to field-unit flow coefficients can be added
    in the pressure-solver milestone.
    """

    tx = (
        kfx
        * AX_FT2
        / (MU_CP * DX_FT)
    )

    ty = (
        kfy
        * AY_FT2
        / (MU_CP * DY_FT)
    )

    tz = (
        kfz
        * AZ_FT2
        / (MU_CP * DZ_FT)
    )

    return tx, ty, tz


# ======================================================================
# STATISTICS
# ======================================================================

def stats_dict(a):

    return {
        "shape": list(a.shape),
        "count": int(a.size),
        "min": float(a.min()),
        "max": float(a.max()),
        "mean": float(a.mean()),
        "median": float(np.median(a)),
        "p10": float(np.percentile(a, 10)),
        "p90": float(np.percentile(a, 90)),
    }


# ======================================================================
# VALIDATION
# ======================================================================

def validate(
    k,
    kx,
    ky,
    kz,
    kfx,
    kfy,
    kfz,
    tx,
    ty,
    tz,
):

    print("\n" + "=" * 78)
    print("V15-SG2 VALIDATION GATES")
    print("=" * 78)

    checks = []

    checks.append(
        (
            "Cell permeability shape = (15, 50, 50)",
            k.shape == (15, 50, 50),
        )
    )

    checks.append(
        (
            "Kx = K",
            np.allclose(kx, k),
        )
    )

    checks.append(
        (
            "Ky = K",
            np.allclose(ky, k),
        )
    )

    checks.append(
        (
            "Kz = 0.1 K",
            np.allclose(kz, 0.1 * k),
        )
    )

    checks.append(
        (
            "Tx shape = (15, 50, 49)",
            tx.shape == (15, 50, 49),
        )
    )

    checks.append(
        (
            "Ty shape = (15, 49, 50)",
            ty.shape == (15, 49, 50),
        )
    )

    checks.append(
        (
            "Tz shape = (14, 50, 50)",
            tz.shape == (14, 50, 50),
        )
    )

    checks.append(
        (
            "All Tx > 0",
            np.all(tx > 0.0),
        )
    )

    checks.append(
        (
            "All Ty > 0",
            np.all(ty > 0.0),
        )
    )

    checks.append(
        (
            "All Tz > 0",
            np.all(tz > 0.0),
        )
    )

    # Direct harmonic-average spot checks.
    expected_x = harmonic_average(
        kx[7, 24, 24],
        kx[7, 24, 25],
    )

    checks.append(
        (
            "X-face harmonic averaging correct",
            np.isclose(
                kfx[7, 24, 24],
                expected_x,
            ),
        )
    )

    expected_y = harmonic_average(
        ky[7, 24, 24],
        ky[7, 25, 24],
    )

    checks.append(
        (
            "Y-face harmonic averaging correct",
            np.isclose(
                kfy[7, 24, 24],
                expected_y,
            ),
        )
    )

    expected_z = harmonic_average(
        kz[7, 24, 24],
        kz[8, 24, 24],
    )

    checks.append(
        (
            "Z-face harmonic averaging correct",
            np.isclose(
                kfz[7, 24, 24],
                expected_z,
            ),
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
            "V15-SG2 validation failed."
        )

    print(
        "V15-SG2 TRANSMISSIBILITY VALIDATION: PASS"
    )


# ======================================================================
# DIAGNOSTIC PLOTS
# ======================================================================

def plot_tx_layer8(tx):

    # Physical layer 8 => zero-based k=7
    layer = tx[7]

    fig, ax = plt.subplots(
        figsize=(8, 7)
    )

    im = ax.imshow(
        layer,
        origin="lower",
        extent=[
            DX_FT,
            NX * DX_FT - DX_FT,
            0,
            NY * DY_FT,
        ],
        aspect="auto",
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
    )

    cbar.set_label(
        "Tx (mD ft / cP)"
    )

    ax.set_title(
        "PAD-Stream V15-SG2\n"
        "X-direction Transmissibility - Layer 8"
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Y (ft)")

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR / "V15SG2_TX_Layer08.png",
        dpi=300,
    )

    plt.close(fig)


def plot_ty_layer8(ty):

    layer = ty[7]

    fig, ax = plt.subplots(
        figsize=(8, 7)
    )

    im = ax.imshow(
        layer,
        origin="lower",
        extent=[
            0,
            NX * DX_FT,
            DY_FT,
            NY * DY_FT - DY_FT,
        ],
        aspect="auto",
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
    )

    cbar.set_label(
        "Ty (mD ft / cP)"
    )

    ax.set_title(
        "PAD-Stream V15-SG2\n"
        "Y-direction Transmissibility - Layer 8"
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Y (ft)")

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR / "V15SG2_TY_Layer08.png",
        dpi=300,
    )

    plt.close(fig)


def plot_tz_section(tz):

    middle_y = NY // 2

    section = tz[
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
            NX * DX_FT,
            DZ_FT,
            NZ * DZ_FT - DZ_FT,
        ],
        aspect="auto",
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
    )

    cbar.set_label(
        "Tz (mD ft / cP)"
    )

    ax.set_title(
        "PAD-Stream V15-SG2\n"
        "Vertical Transmissibility Section"
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Z (ft)")

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR / "V15SG2_TZ_VerticalSection.png",
        dpi=300,
    )

    plt.close(fig)


def plot_transmissibility_histograms(
    tx,
    ty,
    tz,
):

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.hist(
        tx.ravel(),
        bins=50,
        alpha=0.5,
        label="Tx",
    )

    ax.hist(
        ty.ravel(),
        bins=50,
        alpha=0.5,
        label="Ty",
    )

    ax.hist(
        tz.ravel(),
        bins=50,
        alpha=0.5,
        label="Tz",
    )

    ax.set_xlabel(
        "Transmissibility (mD ft / cP)"
    )

    ax.set_ylabel(
        "Face count"
    )

    ax.set_title(
        "PAD-Stream V15-SG2\n"
        "Directional Transmissibility Distributions"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG2_Transmissibility_Histograms.png",
        dpi=300,
    )

    plt.close(fig)


# ======================================================================
# SAVE ARRAYS
# ======================================================================

def save_arrays(
    kfx,
    kfy,
    kfz,
    tx,
    ty,
    tz,
):

    np.save(
        OUTPUT_DIR / "KFACE_X.npy",
        kfx,
    )

    np.save(
        OUTPUT_DIR / "KFACE_Y.npy",
        kfy,
    )

    np.save(
        OUTPUT_DIR / "KFACE_Z.npy",
        kfz,
    )

    np.save(
        OUTPUT_DIR / "TX.npy",
        tx,
    )

    np.save(
        OUTPUT_DIR / "TY.npy",
        ty,
    )

    np.save(
        OUTPUT_DIR / "TZ.npy",
        tz,
    )


# ======================================================================
# SAVE SUMMARY
# ======================================================================

def save_summary(
    k,
    kfx,
    kfy,
    kfz,
    tx,
    ty,
    tz,
):

    summary = {
        "milestone": "V15-SG2",
        "description":
            "3D anisotropic finite-volume transmissibilities",

        "status": "PASS",

        "input_permeability_file":
            str(INPUT_PERM_FILE),

        "grid": {
            "nx": NX,
            "ny": NY,
            "nz": NZ,
            "dx_ft": DX_FT,
            "dy_ft": DY_FT,
            "dz_ft": DZ_FT,
            "cells": N_CELLS,
        },

        "directional_permeability": {
            "kx": "K_SGSim",
            "ky": "K_SGSim",
            "kz": f"{KV_KH_RATIO} * K_SGSim",
        },

        "reference_viscosity_cp":
            MU_CP,

        "face_areas_ft2": {
            "Ax": AX_FT2,
            "Ay": AY_FT2,
            "Az": AZ_FT2,
        },

        "cell_permeability_md":
            stats_dict(k),

        "face_permeability_x_md":
            stats_dict(kfx),

        "face_permeability_y_md":
            stats_dict(kfy),

        "face_permeability_z_md":
            stats_dict(kfz),

        "transmissibility_x":
            stats_dict(tx),

        "transmissibility_y":
            stats_dict(ty),

        "transmissibility_z":
            stats_dict(tz),

        "pressure_solve_performed":
            False,

        "next_milestone":
            "V15-SG3 - five-spot pressure solve",
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
    print("PAD-Stream Version 15-SG2")
    print(
        "3D Anisotropic Finite-Volume Transmissibilities"
    )
    print("=" * 78)

    # --------------------------------------------------------------
    # Load SG1 geology
    # --------------------------------------------------------------

    k = load_permeability()

    kx, ky, kz = (
        build_directional_permeability(k)
    )

    # --------------------------------------------------------------
    # Face permeability
    # --------------------------------------------------------------

    kfx, kfy, kfz = (
        build_face_permeabilities(
            kx,
            ky,
            kz,
        )
    )

    # --------------------------------------------------------------
    # Transmissibility
    # --------------------------------------------------------------

    tx, ty, tz = (
        build_transmissibilities(
            kfx,
            kfy,
            kfz,
        )
    )

    # --------------------------------------------------------------
    # Print diagnostics
    # --------------------------------------------------------------

    print("\nGRID / FACE GEOMETRY")

    print(
        f"  Cell grid              : "
        f"{NZ} x {NY} x {NX}"
    )

    print(
        f"  Tx shape               : "
        f"{tx.shape}"
    )

    print(
        f"  Ty shape               : "
        f"{ty.shape}"
    )

    print(
        f"  Tz shape               : "
        f"{tz.shape}"
    )

    print(
        f"  Ax                      : "
        f"{AX_FT2:.1f} ft^2"
    )

    print(
        f"  Ay                      : "
        f"{AY_FT2:.1f} ft^2"
    )

    print(
        f"  Az                      : "
        f"{AZ_FT2:.1f} ft^2"
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

    print("\nFACE PERMEABILITY")

    print(
        f"  Kfx mean                : "
        f"{kfx.mean():.3f} mD"
    )

    print(
        f"  Kfy mean                : "
        f"{kfy.mean():.3f} mD"
    )

    print(
        f"  Kfz mean                : "
        f"{kfz.mean():.3f} mD"
    )

    print("\nTRANSMISSIBILITY")

    print(
        f"  Tx mean                 : "
        f"{tx.mean():.3f}"
    )

    print(
        f"  Ty mean                 : "
        f"{ty.mean():.3f}"
    )

    print(
        f"  Tz mean                 : "
        f"{tz.mean():.3f}"
    )

    print(
        f"  Tx min/max              : "
        f"{tx.min():.3f} / {tx.max():.3f}"
    )

    print(
        f"  Ty min/max              : "
        f"{ty.min():.3f} / {ty.max():.3f}"
    )

    print(
        f"  Tz min/max              : "
        f"{tz.min():.3f} / {tz.max():.3f}"
    )

    # --------------------------------------------------------------
    # Validation
    # --------------------------------------------------------------

    validate(
        k,
        kx,
        ky,
        kz,
        kfx,
        kfy,
        kfz,
        tx,
        ty,
        tz,
    )

    # --------------------------------------------------------------
    # Save arrays
    # --------------------------------------------------------------

    save_arrays(
        kfx,
        kfy,
        kfz,
        tx,
        ty,
        tz,
    )

    # --------------------------------------------------------------
    # Plots
    # --------------------------------------------------------------

    plot_tx_layer8(tx)
    plot_ty_layer8(ty)
    plot_tz_section(tz)

    plot_transmissibility_histograms(
        tx,
        ty,
        tz,
    )

    # --------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------

    save_summary(
        k,
        kfx,
        kfy,
        kfz,
        tx,
        ty,
        tz,
    )

    print("\nOUTPUTS")

    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print("\nSaved arrays:")
    print("  KFACE_X.npy")
    print("  KFACE_Y.npy")
    print("  KFACE_Z.npy")
    print("  TX.npy")
    print("  TY.npy")
    print("  TZ.npy")

    print("\nSaved diagnostics:")
    print("  V15SG2_TX_Layer08.png")
    print("  V15SG2_TY_Layer08.png")
    print("  V15SG2_TZ_VerticalSection.png")
    print(
        "  V15SG2_Transmissibility_Histograms.png"
    )

    print("\nSummary:")
    print(
        f"  {SUMMARY_FILE}"
    )

    print("\n" + "=" * 78)
    print(
        "V15-SG2 COMPLETED SUCCESSFULLY"
    )
    print(
        "Next milestone: V15-SG3"
    )
    print(
        "Five-spot finite-volume pressure solve"
    )
    print("=" * 78)


if __name__ == "__main__":
    main()