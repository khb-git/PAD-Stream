from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm


# ============================================================
# PAD-Stream SGSim permeability transformation
# ============================================================

# ---------------------------
# Grid definition
# ---------------------------
NX = 50
NY = 50
NZ = 15

DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0

EXPECTED_CELLS = NX * NY * NZ

# SGeMS layers 6-10 are the higher-permeability injection unit.
# Python indexing is zero-based, so this becomes [5:10].
INJ_K_START = 5
INJ_K_STOP = 10

# ---------------------------
# Permeability bounds
# ---------------------------
BACKGROUND_K_MIN_MD = 50.0
BACKGROUND_K_MAX_MD = 700.0

INJECTION_K_MIN_MD = 300.0
INJECTION_K_MAX_MD = 1000.0

# Nonlinear exponent controlling the permeability distribution.
PERM_EXPONENT = 2.0

# ---------------------------
# File paths
# ---------------------------
ROOT = Path(__file__).resolve().parent

INPUT_FILE = ROOT / "SGSIM_50x50x15_GAUSS.csv"

OUTPUT_DIR = ROOT / "output" / "sgsim_validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PERM_ONLY_FILE = ROOT / "SGSIM_50x50x15_PERM_MD.csv"
GAUSS_PERM_FILE = ROOT / "SGSIM_50x50x15_GAUSS_PERM.csv"


def load_sgems_gaussian(path: Path) -> np.ndarray:
    """
    Read the exported SGeMS Gaussian realization.

    The SGeMS CSV contains:
        line 1: property name
        remaining lines: one value per grid cell

    SGeMS ordering is assumed to be:
        X fastest, then Y, then Z.

    Therefore reshaping to (NZ, NY, NX) in NumPy C-order
    reconstructs the 3D grid correctly.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find input file:\n{path}"
        )

    values = np.loadtxt(path, skiprows=1, dtype=float)

    if values.size != EXPECTED_CELLS:
        raise ValueError(
            f"Expected {EXPECTED_CELLS:,} values for a "
            f"{NX} x {NY} x {NZ} grid, but found {values.size:,}."
        )

    return values.reshape((NZ, NY, NX), order="C")


def transform_to_permeability(z: np.ndarray):
    """
    Convert the Gaussian SGSim realization into physical permeability.

    Step 1:
        U = Phi(Z)

    Step 2:
        Background:
            K = 50 + 950 * U^2

        Injection interval, layers 6-10:
            K = 300 + 700 * U^2
    """

    # Standard-normal Gaussian CDF
    u = norm.cdf(z)

    # Background transformation
    k = (
        BACKGROUND_K_MIN_MD
        + (BACKGROUND_K_MAX_MD - BACKGROUND_K_MIN_MD)
        * u**PERM_EXPONENT
    )

    # Higher-permeability injection interval
    u_inj = u[INJ_K_START:INJ_K_STOP, :, :]

    k[INJ_K_START:INJ_K_STOP, :, :] = (
        INJECTION_K_MIN_MD
        + (INJECTION_K_MAX_MD - INJECTION_K_MIN_MD)
        * u_inj**PERM_EXPONENT
    )

    return u, k


def print_statistics(z: np.ndarray, k: np.ndarray):
    """
    Print validation statistics for the Gaussian realization,
    complete permeability model, background unit, and injection unit.
    """

    background = np.concatenate(
        (
            k[:INJ_K_START, :, :].ravel(),
            k[INJ_K_STOP:, :, :].ravel(),
        )
    )

    injection = k[INJ_K_START:INJ_K_STOP, :, :].ravel()

    print("=" * 72)
    print("PAD-Stream SGSim permeability transformation")
    print("=" * 72)

    print("\nGRID")
    print(f"  NX, NY, NZ           : {NX}, {NY}, {NZ}")
    print(f"  Total cells          : {k.size:,}")
    print(f"  Cell size            : {DX_FT} x {DY_FT} x {DZ_FT} ft")
    print(
        f"  Physical dimensions  : "
        f"{NX * DX_FT:.1f} x "
        f"{NY * DY_FT:.1f} x "
        f"{NZ * DZ_FT:.1f} ft"
    )

    print("\nGAUSSIAN SGSIM FIELD")
    print(f"  Minimum              : {z.min():.6f}")
    print(f"  Maximum              : {z.max():.6f}")
    print(f"  Mean                 : {z.mean():.6f}")
    print(f"  Std. deviation       : {z.std():.6f}")

    print("\nFULL PERMEABILITY MODEL")
    print(f"  Minimum              : {k.min():.3f} mD")
    print(f"  Maximum              : {k.max():.3f} mD")
    print(f"  Mean                 : {k.mean():.3f} mD")
    print(f"  Median               : {np.median(k):.3f} mD")
    print(f"  P10                  : {np.percentile(k, 10):.3f} mD")
    print(f"  P90                  : {np.percentile(k, 90):.3f} mD")

    print("\nBACKGROUND UNIT")
    print("  SGeMS layers         : 1-5 and 11-15")
    print(f"  Number of cells      : {background.size:,}")
    print(f"  Minimum              : {background.min():.3f} mD")
    print(f"  Maximum              : {background.max():.3f} mD")
    print(f"  Mean                 : {background.mean():.3f} mD")
    print(f"  Median               : {np.median(background):.3f} mD")

    print("\nINJECTION UNIT")
    print("  SGeMS layers         : 6-10")
    print(f"  Thickness            : {5 * DZ_FT:.1f} ft")
    print(f"  Number of cells      : {injection.size:,}")
    print(f"  Minimum              : {injection.min():.3f} mD")
    print(f"  Maximum              : {injection.max():.3f} mD")
    print(f"  Mean                 : {injection.mean():.3f} mD")
    print(f"  Median               : {np.median(injection):.3f} mD")

    ratio = injection.mean() / background.mean()

    print("\nINJECTION/BACKGROUND CONTRAST")
    print(f"  Mean K ratio         : {ratio:.3f}")

    if injection.mean() <= background.mean():
        print("  WARNING: Injection unit mean K is not higher than background.")
    else:
        print("  PASS: Injection unit has higher mean permeability.")

    print("=" * 72)


def save_outputs(z: np.ndarray, k: np.ndarray):
    """
    Save files while preserving SGeMS X-fastest/Y/Z ordering.
    """

    z_flat = z.ravel(order="C")
    k_flat = k.ravel(order="C")

    # Single-property file for straightforward SGeMS import
    np.savetxt(
        PERM_ONLY_FILE,
        k_flat,
        fmt="%.8f",
        header="PERM_MD",
        comments="",
    )

    # Two-property CSV useful for Python/PAD-Stream analysis
    combined = np.column_stack((z_flat, k_flat))

    np.savetxt(
        GAUSS_PERM_FILE,
        combined,
        delimiter=",",
        fmt="%.8f",
        header="GAUSS_SGSIM_CONT__real0,PERM_MD",
        comments="",
    )


def save_layer_plot(k: np.ndarray, layer_number: int):
    """
    Save an XY permeability map for one SGeMS layer.
    layer_number is one-based, e.g. 1 through 15.
    """

    k_index = layer_number - 1

    fig, ax = plt.subplots(figsize=(7, 6))

    image = ax.imshow(
        k[k_index, :, :],
        origin="lower",
        extent=[
            0,
            NX * DX_FT,
            0,
            NY * DY_FT,
        ],
        aspect="equal",
    )

    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("Permeability (mD)")

    unit_name = (
        "Injection Unit"
        if 6 <= layer_number <= 10
        else "Background Unit"
    )

    ax.set_title(
        f"SGSim Permeability - Layer {layer_number} ({unit_name})"
    )
    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Y (ft)")

    fig.tight_layout()

    outfile = (
        OUTPUT_DIR
        / f"permeability_layer_{layer_number:02d}.png"
    )

    fig.savefig(outfile, dpi=300)
    plt.close(fig)


def save_histogram(k: np.ndarray):
    fig, ax = plt.subplots(figsize=(8, 6))

    ax.hist(k.ravel(), bins=50)

    ax.set_xlabel("Permeability (mD)")
    ax.set_ylabel("Cell count")
    ax.set_title("SGSim 3D Permeability Distribution")

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR / "permeability_histogram.png",
        dpi=300,
    )

    plt.close(fig)


def save_vertical_section(k: np.ndarray):
    """
    Save an X-Z section through the middle Y row.
    """

    middle_y = NY // 2

    section = k[:, middle_y, :]

    fig, ax = plt.subplots(figsize=(10, 4))

    image = ax.imshow(
        section,
        origin="lower",
        extent=[
            0,
            NX * DX_FT,
            0,
            NZ * DZ_FT,
        ],
        aspect="auto",
    )

    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("Permeability (mD)")

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Z (ft)")
    ax.set_title(
        "SGSim Permeability Vertical Section "
        f"(Y ≈ {middle_y * DY_FT:.0f} ft)"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR / "permeability_vertical_section.png",
        dpi=300,
    )

    plt.close(fig)


def main():
    print(f"Reading:\n  {INPUT_FILE}\n")

    z = load_sgems_gaussian(INPUT_FILE)

    _, permeability = transform_to_permeability(z)

    print_statistics(z, permeability)

    save_outputs(z, permeability)

    # Representative background + injection-unit layers
    for layer in [1, 3, 5, 6, 8, 10, 11, 13, 15]:
        save_layer_plot(permeability, layer)

    save_histogram(permeability)
    save_vertical_section(permeability)

    print("\nSaved permeability files:")
    print(f"  {PERM_ONLY_FILE}")
    print(f"  {GAUSS_PERM_FILE}")

    print("\nSaved validation figures:")
    print(f"  {OUTPUT_DIR}")

    print("\nTransformation completed successfully.")


if __name__ == "__main__":
    main()