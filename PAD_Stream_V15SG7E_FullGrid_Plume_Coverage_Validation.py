from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7E
# Full-Grid Plume / Coverage Validation
#
# NO TRAINING.
# NO MODEL MODIFICATION.
# NO MAP-BACK MODIFICATION.
# NO CHANGE IN STREAMLINE SEED DENSITY.
#
#
# PURPOSE
# -------
# Independently diagnose the accepted V15-SG7D Eulerian reconstruction.
#
# This milestone evaluates:
#
#   1. Full-grid plume morphology
#   2. PI-RNN vs SG7A plume agreement
#   3. Layer-by-layer streamline coverage
#   4. Direct-support quality
#   5. Dependence on global conservative projection
#   6. Whether the current 7x7 seed system is adequate for freezing
#
#
# SG7E DOES NOT:
#
#   retrain the PI-RNN
#   alter SG7D
#   alter the conservative projection
#   increase streamline seeds
#   freeze a learned map-back
#
#
# If SG7E passes:
#
#       deterministic SGSim plume reconstruction can be frozen.
#
# If SG7E identifies insufficient spatial support:
#
#       return to SG5 seed-convergence analysis before proceeding.
#
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent


SG7D_FILE = (
    ROOT
    / "output"
    / "V15_SG7D"
    / "SG7D_CONSERVATIVE_GRID_MAPBACK.npz"
)


SG7D_SUMMARY_FILE = (
    ROOT
    / "output"
    / "V15_SG7D"
    / "PAD_Stream_V15SG7D_Summary.json"
)


SG7D_STORAGE_FILE = (
    ROOT
    / "output"
    / "V15_SG7D"
    / "V15SG7D_Storage_Metrics.csv"
)


OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7E"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


PLUME_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7E_Plume_Metrics.csv"
)


COVERAGE_BY_LAYER_FILE = (
    OUTPUT_DIR
    / "V15SG7E_Coverage_By_Layer.csv"
)


PROJECTION_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7E_Projection_Dependence.csv"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7E_Summary.json"
)


DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7E_Plume_Coverage_Validation.npz"
)


# =============================================================================
# GRID CONTRACT
# =============================================================================

NX = 50
NY = 50
NZ = 15

GRID_SHAPE = (
    NZ,
    NY,
    NX,
)


DX_M = 6.0960
DY_M = 6.0960
DZ_M = 1.2192

CELL_VOLUME_M3 = (
    DX_M
    *
    DY_M
    *
    DZ_M
)

POROSITY = 0.20

CELL_PORE_VOLUME_M3 = (
    POROSITY
    *
    CELL_VOLUME_M3
)


# =============================================================================
# SATURATION CONTRACT
# =============================================================================

S_INITIAL = 0.20

S_MIN = 0.20
S_MAX = 0.80


# =============================================================================
# PLUME THRESHOLDS
#
# We evaluate more than one plume definition.
#
# Primary plume:
#
#       S > S_initial + 0.01
#
# Strong plume:
#
#       S > S_initial + 0.05
#
# High-saturation core:
#
#       S > 0.50
#
# =============================================================================

PLUME_DELTA_S = 0.01

STRONG_PLUME_DELTA_S = 0.05

CORE_SATURATION = 0.50


# =============================================================================
# ACCURACY / MORPHOLOGY GATES
#
# These do NOT replace the already-passed SG7D error gates.
# They assess plume-level agreement.
# =============================================================================

FOOTPRINT_IOU_MIN = 0.90

PLUME_VOLUME_REL_ERROR_MAX = 0.10

CENTROID_DISTANCE_MAX_CELLS = 2.0

VERTICAL_EXTENT_DIFFERENCE_MAX_LAYERS = 2

COVERED_PLUME_FRACTION_MIN = 0.80


# =============================================================================
# PROJECTION DIAGNOSTICS
#
# These are initially diagnostic rather than hard physics gates.
# We do not want to invent an arbitrary projection threshold and use it
# retroactively to fail a physically conservative solution.
# =============================================================================

PROJECTION_FLAG_DELTA_S = 0.05


EPS = 1.0e-14


# =============================================================================
# HELPERS
# =============================================================================

def mae(values):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    return float(
        np.mean(
            np.abs(
                values
            )
        )
    )


def rms(values):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    return float(
        np.sqrt(
            np.mean(
                values ** 2
            )
        )
    )


def save_csv(
    path,
    rows,
):

    if not rows:

        return

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# =============================================================================
# LOAD SG7D
# =============================================================================

def load_sg7d():

    if not SG7D_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7D map-back database:\n"
            f"{SG7D_FILE}"
        )

    if not SG7D_SUMMARY_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7D summary:\n"
            f"{SG7D_SUMMARY_FILE}"
        )

    with open(
        SG7D_SUMMARY_FILE,
        "r",
        encoding="utf-8",
    ) as handle:

        summary = json.load(
            handle
        )

    if not summary.get(
        "validation_passed",
        False,
    ):

        raise RuntimeError(
            "SG7D did not pass validation."
        )

    data = np.load(
        SG7D_FILE
    )

    required = [
        "times_days",
        "grid_shape",
        "coverage_mask",
        "coverage_weight_m3",
        "subsegment_count",
        "streamline_count",
        "PI_RNN_raw_grid_saturation",
        "PI_RNN_corrected_grid_saturation",
        "SG7A_raw_grid_saturation",
        "SG7A_corrected_grid_saturation",
        "absolute_grid_error",
    ]

    for key in required:

        if key not in data:

            raise KeyError(
                f"SG7D field missing: {key}"
            )

    return {
        key:
            data[key]
        for key in required
    }


# =============================================================================
# CELL CENTERS
# =============================================================================

def grid_centers():

    x = (
        np.arange(
            NX,
            dtype=np.float64,
        )
        +
        0.5
    ) * DX_M

    y = (
        np.arange(
            NY,
            dtype=np.float64,
        )
        +
        0.5
    ) * DY_M

    z = (
        np.arange(
            NZ,
            dtype=np.float64,
        )
        +
        0.5
    ) * DZ_M

    Z, Y, X = np.meshgrid(
        z,
        y,
        x,
        indexing="ij",
    )

    return (
        X,
        Y,
        Z,
    )


# =============================================================================
# PLUME MASKS
# =============================================================================

def plume_masks(
    saturation,
):

    primary = (
        saturation
        >
        S_INITIAL
        +
        PLUME_DELTA_S
    )

    strong = (
        saturation
        >
        S_INITIAL
        +
        STRONG_PLUME_DELTA_S
    )

    core = (
        saturation
        >
        CORE_SATURATION
    )

    return {
        "primary":
            primary,

        "strong":
            strong,

        "core":
            core,
    }


# =============================================================================
# IOU
# =============================================================================

def mask_iou(
    a,
    b,
):

    a = np.asarray(
        a,
        dtype=bool,
    )

    b = np.asarray(
        b,
        dtype=bool,
    )

    union = np.logical_or(
        a,
        b,
    )

    intersection = np.logical_and(
        a,
        b,
    )

    union_count = int(
        np.sum(
            union
        )
    )

    if union_count == 0:

        return 1.0

    return float(
        np.sum(
            intersection
        )
        /
        union_count
    )


# =============================================================================
# SATURATION-WEIGHTED CENTROID
#
# Weight with saturation increase above initial state.
# =============================================================================

def plume_centroid(
    saturation,
    X,
    Y,
    Z,
):

    delta = np.maximum(
        saturation
        -
        S_INITIAL,
        0.0,
    )

    total = float(
        np.sum(
            delta
        )
    )

    if total <= EPS:

        return (
            np.nan,
            np.nan,
            np.nan,
        )

    cx = float(
        np.sum(
            delta
            *
            X
        )
        /
        total
    )

    cy = float(
        np.sum(
            delta
            *
            Y
        )
        /
        total
    )

    cz = float(
        np.sum(
            delta
            *
            Z
        )
        /
        total
    )

    return (
        cx,
        cy,
        cz,
    )


# =============================================================================
# VERTICAL EXTENT
# =============================================================================

def vertical_extent_layers(
    plume_mask,
):

    layer_has_plume = np.any(
        plume_mask,
        axis=(
            1,
            2,
        ),
    )

    layers = np.where(
        layer_has_plume
    )[0]

    if len(
        layers
    ) == 0:

        return {
            "min_layer":
                -1,

            "max_layer":
                -1,

            "extent_layers":
                0,
        }

    return {
        "min_layer":
            int(
                layers[0]
            ),

        "max_layer":
            int(
                layers[-1]
            ),

        "extent_layers":
            int(
                layers[-1]
                -
                layers[0]
                +
                1
            ),
    }


# =============================================================================
# PLUME VOLUME
#
# We report:
#
#   geometric plume cell volume
#   plume pore volume
#   displaced-phase volume
# =============================================================================

def plume_volume_metrics(
    saturation,
    plume_mask,
):

    plume_cells = int(
        np.sum(
            plume_mask
        )
    )

    geometric_volume = (
        plume_cells
        *
        CELL_VOLUME_M3
    )

    plume_pore_volume = (
        plume_cells
        *
        CELL_PORE_VOLUME_M3
    )

    displaced_volume = float(
        np.sum(
            CELL_PORE_VOLUME_M3
            *
            np.maximum(
                saturation
                -
                S_INITIAL,
                0.0,
            )
        )
    )

    return {
        "plume_cells":
            plume_cells,

        "geometric_volume_m3":
            geometric_volume,

        "plume_pore_volume_m3":
            plume_pore_volume,

        "displaced_phase_volume_m3":
            displaced_volume,
    }


# =============================================================================
# PLUME COVERAGE SUPPORT
# =============================================================================

def plume_support_metrics(
    plume_mask,
    coverage_mask,
    streamline_count,
):

    plume_cells = int(
        np.sum(
            plume_mask
        )
    )

    if plume_cells == 0:

        return {
            "covered_plume_cells":
                0,

            "covered_plume_fraction":
                1.0,

            "mean_streamline_support":
                0.0,

            "median_streamline_support":
                0.0,

            "minimum_streamline_support":
                0,
        }

    covered_plume = (
        plume_mask
        &
        coverage_mask
    )

    support = (
        streamline_count[
            plume_mask
        ]
    )

    return {
        "covered_plume_cells":
            int(
                np.sum(
                    covered_plume
                )
            ),

        "covered_plume_fraction":
            float(
                np.sum(
                    covered_plume
                )
                /
                plume_cells
            ),

        "mean_streamline_support":
            float(
                np.mean(
                    support
                )
            ),

        "median_streamline_support":
            float(
                np.median(
                    support
                )
            ),

        "minimum_streamline_support":
            int(
                np.min(
                    support
                )
            ),
    }


# =============================================================================
# PROJECTION DEPENDENCE
# =============================================================================

def projection_metrics(
    raw,
    corrected,
    coverage_mask,
):

    correction = (
        corrected
        -
        raw
    )

    absolute = np.abs(
        correction
    )

    covered = (
        absolute[
            coverage_mask
        ]
    )

    uncovered = (
        absolute[
            ~coverage_mask
        ]
    )

    return {
        "global_MAE":
            mae(
                correction
            ),

        "global_RMS":
            rms(
                correction
            ),

        "global_MAX":
            float(
                np.max(
                    absolute
                )
            ),

        "covered_MAE":
            (
                mae(
                    covered
                )
                if covered.size
                else 0.0
            ),

        "covered_MAX":
            (
                float(
                    np.max(
                        covered
                    )
                )
                if covered.size
                else 0.0
            ),

        "uncovered_MAE":
            (
                mae(
                    uncovered
                )
                if uncovered.size
                else 0.0
            ),

        "uncovered_MAX":
            (
                float(
                    np.max(
                        uncovered
                    )
                )
                if uncovered.size
                else 0.0
            ),

        "fraction_cells_deltaS_gt_0p05":
            float(
                np.mean(
                    absolute
                    >
                    PROJECTION_FLAG_DELTA_S
                )
            ),

        "fraction_covered_deltaS_gt_0p05":
            (
                float(
                    np.mean(
                        covered
                        >
                        PROJECTION_FLAG_DELTA_S
                    )
                )
                if covered.size
                else 0.0
            ),

        "fraction_uncovered_deltaS_gt_0p05":
            (
                float(
                    np.mean(
                        uncovered
                        >
                        PROJECTION_FLAG_DELTA_S
                    )
                )
                if uncovered.size
                else 0.0
            ),
    }


# =============================================================================
# LAYER COVERAGE
# =============================================================================

def layer_coverage_rows(
    coverage_mask,
    streamline_count,
    coverage_weight,
):

    rows = []

    cells_per_layer = (
        NX
        *
        NY
    )

    for k in range(
        NZ
    ):

        layer_mask = (
            coverage_mask[
                k
            ]
        )

        covered = int(
            np.sum(
                layer_mask
            )
        )

        support = (
            streamline_count[
                k
            ][
                layer_mask
            ]
        )

        rows.append(
            {
                "zero_based_k":
                    k,

                "physical_layer":
                    k + 1,

                "covered_cells":
                    covered,

                "total_cells":
                    cells_per_layer,

                "coverage_fraction":
                    float(
                        covered
                        /
                        cells_per_layer
                    ),

                "mean_streamline_support_covered":
                    (
                        float(
                            np.mean(
                                support
                            )
                        )
                        if support.size
                        else 0.0
                    ),

                "median_streamline_support_covered":
                    (
                        float(
                            np.median(
                                support
                            )
                        )
                        if support.size
                        else 0.0
                    ),

                "maximum_streamline_support":
                    int(
                        np.max(
                            streamline_count[
                                k
                            ]
                        )
                    ),

                "coverage_weight_m3":
                    float(
                        np.sum(
                            coverage_weight[
                                k
                            ]
                        )
                    ),
            }
        )

    return rows


# =============================================================================
# DIAGNOSTIC PLOTS
# =============================================================================

def plot_layer_coverage(
    layer_rows,
):

    layers = [
        row[
            "physical_layer"
        ]
        for row
        in layer_rows
    ]

    coverage = [
        row[
            "coverage_fraction"
        ]
        for row
        in layer_rows
    ]

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.bar(
        layers,
        coverage,
    )

    ax.set_xlabel(
        "Physical layer"
    )

    ax.set_ylabel(
        "Direct streamline cell coverage"
    )

    ax.set_ylim(
        0.0,
        1.0,
    )

    ax.set_title(
        "PAD-Stream V15-SG7E\n"
        "Layer-by-Layer Direct Coverage"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7E_Coverage_By_Layer.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_plume_footprint(
    time_days,
    pirnn,
    truth,
):

    pirnn_mask = (
        pirnn
        >
        S_INITIAL
        +
        PLUME_DELTA_S
    )

    truth_mask = (
        truth
        >
        S_INITIAL
        +
        PLUME_DELTA_S
    )

    pirnn_footprint = np.any(
        pirnn_mask,
        axis=0,
    )

    truth_footprint = np.any(
        truth_mask,
        axis=0,
    )

    difference = (
        pirnn_footprint.astype(
            int
        )
        -
        truth_footprint.astype(
            int
        )
    )

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(
            15,
            5,
        )
    )

    axes[0].imshow(
        pirnn_footprint,
        origin="lower",
    )

    axes[0].set_title(
        "PI-RNN footprint"
    )

    axes[1].imshow(
        truth_footprint,
        origin="lower",
    )

    axes[1].set_title(
        "SG7A footprint"
    )

    image = axes[2].imshow(
        difference,
        origin="lower",
    )

    axes[2].set_title(
        "Footprint difference"
    )

    fig.colorbar(
        image,
        ax=axes[2],
    )

    for ax in axes:

        ax.set_xlabel(
            "i"
        )

        ax.set_ylabel(
            "j"
        )

    fig.suptitle(
        "PAD-Stream V15-SG7E — "
        f"Plume Footprint — {time_days:.0f} days"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        /
        (
            "V15SG7E_PlumeFootprint_"
            f"{int(time_days)}d.png"
        ),
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_projection_map(
    time_days,
    raw,
    corrected,
):

    layer = 7

    difference = (
        corrected[
            layer
        ]
        -
        raw[
            layer
        ]
    )

    fig, ax = plt.subplots(
        figsize=(
            8,
            7,
        )
    )

    image = ax.imshow(
        difference,
        origin="lower",
    )

    colorbar = fig.colorbar(
        image,
        ax=ax,
    )

    colorbar.set_label(
        "Projection correction ΔS"
    )

    ax.set_xlabel(
        "i"
    )

    ax.set_ylabel(
        "j"
    )

    ax.set_title(
        "PAD-Stream V15-SG7E\n"
        f"Projection Correction — Layer 8 — "
        f"{time_days:.0f} days"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        /
        (
            "V15SG7E_Projection_Layer08_"
            f"{int(time_days)}d.png"
        ),
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_centroid_trajectory(
    plume_rows,
):

    times = np.asarray(
        [
            row[
                "time_days"
            ]
            for row
            in plume_rows
        ],
        dtype=np.float64,
    )

    fig, ax = plt.subplots(
        figsize=(
            8,
            7,
        )
    )

    ax.plot(
        [
            row[
                "PI_RNN_centroid_x_m"
            ]
            for row
            in plume_rows
        ],
        [
            row[
                "PI_RNN_centroid_y_m"
            ]
            for row
            in plume_rows
        ],
        marker="o",
        label="PI-RNN",
    )

    ax.plot(
        [
            row[
                "SG7A_centroid_x_m"
            ]
            for row
            in plume_rows
        ],
        [
            row[
                "SG7A_centroid_y_m"
            ]
            for row
            in plume_rows
        ],
        marker="s",
        label="SG7A",
    )

    for index, time_days in enumerate(
        times
    ):

        ax.annotate(
            f"{time_days:.0f}d",
            (
                plume_rows[index][
                    "PI_RNN_centroid_x_m"
                ],
                plume_rows[index][
                    "PI_RNN_centroid_y_m"
                ],
            ),
        )

    ax.set_xlabel(
        "Centroid x [m]"
    )

    ax.set_ylabel(
        "Centroid y [m]"
    )

    ax.set_title(
        "PAD-Stream V15-SG7E\n"
        "Plume Centroid Trajectory"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7E_Centroid_Trajectory.png",
        dpi=300,
    )

    plt.close(
        fig
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
        "PAD-Stream Version 15-SG7E"
    )

    print(
        "Full-Grid Plume / Coverage Validation"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    print(
        "NO STREAMLINE SEED DENSITY WILL BE CHANGED."
    )

    print(
        "NO MAP-BACK OPERATOR WILL BE CHANGED."
    )

    # =========================================================================
    # LOAD
    # =========================================================================

    sg7d = load_sg7d()

    times = np.asarray(
        sg7d[
            "times_days"
        ],
        dtype=np.float64,
    )

    coverage_mask = np.asarray(
        sg7d[
            "coverage_mask"
        ],
        dtype=bool,
    )

    coverage_weight = np.asarray(
        sg7d[
            "coverage_weight_m3"
        ],
        dtype=np.float64,
    )

    streamline_count = np.asarray(
        sg7d[
            "streamline_count"
        ],
        dtype=np.int64,
    )

    pirnn_raw = np.asarray(
        sg7d[
            "PI_RNN_raw_grid_saturation"
        ],
        dtype=np.float64,
    )

    pirnn = np.asarray(
        sg7d[
            "PI_RNN_corrected_grid_saturation"
        ],
        dtype=np.float64,
    )

    truth_raw = np.asarray(
        sg7d[
            "SG7A_raw_grid_saturation"
        ],
        dtype=np.float64,
    )

    truth = np.asarray(
        sg7d[
            "SG7A_corrected_grid_saturation"
        ],
        dtype=np.float64,
    )

    # =========================================================================
    # GRID
    # =========================================================================

    grid_shape = tuple(
        int(value)
        for value
        in np.asarray(
            sg7d[
                "grid_shape"
            ]
        )
    )

    if grid_shape != GRID_SHAPE:

        raise RuntimeError(
            "SG7D grid shape does not match SG7E contract.\n"
            f"Expected: {GRID_SHAPE}\n"
            f"Found   : {grid_shape}"
        )

    X, Y, Z = grid_centers()

    covered_cells = int(
        np.sum(
            coverage_mask
        )
    )

    total_cells = (
        NX
        *
        NY
        *
        NZ
    )

    coverage_fraction = (
        covered_cells
        /
        total_cells
    )

    print(
        "\nSG7D INPUT"
    )

    print(
        f"  Grid                    : "
        f"{GRID_SHAPE}"
    )

    print(
        f"  Deployment times        : "
        f"{times.tolist()}"
    )

    print(
        f"  Covered cells           : "
        f"{covered_cells:,} / {total_cells:,}"
    )

    print(
        f"  Direct coverage         : "
        f"{coverage_fraction:.3%}"
    )

    # =========================================================================
    # LAYER COVERAGE
    # =========================================================================

    layer_rows = layer_coverage_rows(
        coverage_mask,
        streamline_count,
        coverage_weight,
    )

    min_layer_coverage = min(
        row[
            "coverage_fraction"
        ]
        for row
        in layer_rows
    )

    max_layer_coverage = max(
        row[
            "coverage_fraction"
        ]
        for row
        in layer_rows
    )

    print(
        "\nLAYER COVERAGE"
    )

    print(
        f"  Minimum                 : "
        f"{min_layer_coverage:.3%}"
    )

    print(
        f"  Maximum                 : "
        f"{max_layer_coverage:.3%}"
    )

    # =========================================================================
    # TIME-BY-TIME PLUME ANALYSIS
    # =========================================================================

    plume_rows = []

    projection_rows = []

    canonical_passes = []

    plume_support_passes = []

    print(
        "\nPLUME VALIDATION"
    )

    for t_index, time_days in enumerate(
        times
    ):

        P = (
            pirnn[
                t_index
            ]
        )

        T = (
            truth[
                t_index
            ]
        )

        P_raw = (
            pirnn_raw[
                t_index
            ]
        )

        T_raw = (
            truth_raw[
                t_index
            ]
        )

        masks_P = plume_masks(
            P
        )

        masks_T = plume_masks(
            T
        )

        # ---------------------------------------------------------------------
        # Primary plume volume
        # ---------------------------------------------------------------------

        volume_P = plume_volume_metrics(
            P,
            masks_P[
                "primary"
            ],
        )

        volume_T = plume_volume_metrics(
            T,
            masks_T[
                "primary"
            ],
        )

        # ---------------------------------------------------------------------
        # Footprint
        # ---------------------------------------------------------------------

        footprint_P = np.any(
            masks_P[
                "primary"
            ],
            axis=0,
        )

        footprint_T = np.any(
            masks_T[
                "primary"
            ],
            axis=0,
        )

        footprint_iou = mask_iou(
            footprint_P,
            footprint_T,
        )

        volume_relative_error = abs(
            volume_P[
                "geometric_volume_m3"
            ]
            -
            volume_T[
                "geometric_volume_m3"
            ]
        ) / max(
            volume_T[
                "geometric_volume_m3"
            ],
            EPS,
        )

        # ---------------------------------------------------------------------
        # Centroid
        # ---------------------------------------------------------------------

        centroid_P = plume_centroid(
            P,
            X,
            Y,
            Z,
        )

        centroid_T = plume_centroid(
            T,
            X,
            Y,
            Z,
        )

        centroid_distance_m = float(
            np.sqrt(
                (
                    centroid_P[0]
                    -
                    centroid_T[0]
                ) ** 2
                +
                (
                    centroid_P[1]
                    -
                    centroid_T[1]
                ) ** 2
                +
                (
                    centroid_P[2]
                    -
                    centroid_T[2]
                ) ** 2
            )
        )

        characteristic_cell_length = (
            (
                DX_M
                +
                DY_M
                +
                DZ_M
            )
            /
            3.0
        )

        centroid_distance_cells = (
            centroid_distance_m
            /
            characteristic_cell_length
        )

        # ---------------------------------------------------------------------
        # Vertical extent
        # ---------------------------------------------------------------------

        vertical_P = vertical_extent_layers(
            masks_P[
                "primary"
            ]
        )

        vertical_T = vertical_extent_layers(
            masks_T[
                "primary"
            ]
        )

        vertical_difference = abs(
            vertical_P[
                "extent_layers"
            ]
            -
            vertical_T[
                "extent_layers"
            ]
        )

        # ---------------------------------------------------------------------
        # Plume direct coverage
        # ---------------------------------------------------------------------

        support_P = plume_support_metrics(
            masks_P[
                "primary"
            ],
            coverage_mask,
            streamline_count,
        )

        support_T = plume_support_metrics(
            masks_T[
                "primary"
            ],
            coverage_mask,
            streamline_count,
        )

        # ---------------------------------------------------------------------
        # Strong plume and core IoU
        # ---------------------------------------------------------------------

        strong_iou = mask_iou(
            masks_P[
                "strong"
            ],
            masks_T[
                "strong"
            ],
        )

        core_iou = mask_iou(
            masks_P[
                "core"
            ],
            masks_T[
                "core"
            ],
        )

        # ---------------------------------------------------------------------
        # Projection dependence
        # ---------------------------------------------------------------------

        projection_P = projection_metrics(
            P_raw,
            P,
            coverage_mask,
        )

        projection_T = projection_metrics(
            T_raw,
            T,
            coverage_mask,
        )

        # ---------------------------------------------------------------------
        # Acceptance flags
        # ---------------------------------------------------------------------

        footprint_pass = (
            footprint_iou
            >=
            FOOTPRINT_IOU_MIN
        )

        volume_pass = (
            volume_relative_error
            <=
            PLUME_VOLUME_REL_ERROR_MAX
        )

        centroid_pass = (
            centroid_distance_cells
            <=
            CENTROID_DISTANCE_MAX_CELLS
        )

        vertical_pass = (
            vertical_difference
            <=
            VERTICAL_EXTENT_DIFFERENCE_MAX_LAYERS
        )

        plume_support_pass = (
            support_T[
                "covered_plume_fraction"
            ]
            >=
            COVERED_PLUME_FRACTION_MIN
        )

        canonical_pass = (
            footprint_pass
            and
            volume_pass
            and
            centroid_pass
            and
            vertical_pass
        )

        canonical_passes.append(
            canonical_pass
        )

        plume_support_passes.append(
            plume_support_pass
        )

        plume_rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "PI_RNN_plume_cells":
                    volume_P[
                        "plume_cells"
                    ],

                "SG7A_plume_cells":
                    volume_T[
                        "plume_cells"
                    ],

                "PI_RNN_plume_volume_m3":
                    volume_P[
                        "geometric_volume_m3"
                    ],

                "SG7A_plume_volume_m3":
                    volume_T[
                        "geometric_volume_m3"
                    ],

                "plume_volume_relative_error":
                    volume_relative_error,

                "footprint_IoU":
                    footprint_iou,

                "strong_plume_IoU":
                    strong_iou,

                "high_saturation_core_IoU":
                    core_iou,

                "PI_RNN_centroid_x_m":
                    centroid_P[0],

                "PI_RNN_centroid_y_m":
                    centroid_P[1],

                "PI_RNN_centroid_z_m":
                    centroid_P[2],

                "SG7A_centroid_x_m":
                    centroid_T[0],

                "SG7A_centroid_y_m":
                    centroid_T[1],

                "SG7A_centroid_z_m":
                    centroid_T[2],

                "centroid_distance_m":
                    centroid_distance_m,

                "centroid_distance_cells":
                    centroid_distance_cells,

                "PI_RNN_vertical_extent_layers":
                    vertical_P[
                        "extent_layers"
                    ],

                "SG7A_vertical_extent_layers":
                    vertical_T[
                        "extent_layers"
                    ],

                "vertical_extent_difference_layers":
                    vertical_difference,

                "PI_RNN_direct_plume_coverage":
                    support_P[
                        "covered_plume_fraction"
                    ],

                "SG7A_direct_plume_coverage":
                    support_T[
                        "covered_plume_fraction"
                    ],

                "SG7A_mean_plume_streamline_support":
                    support_T[
                        "mean_streamline_support"
                    ],

                "SG7A_median_plume_streamline_support":
                    support_T[
                        "median_streamline_support"
                    ],

                "footprint_pass":
                    footprint_pass,

                "volume_pass":
                    volume_pass,

                "centroid_pass":
                    centroid_pass,

                "vertical_pass":
                    vertical_pass,

                "plume_support_pass":
                    plume_support_pass,

                "canonical_plume_pass":
                    canonical_pass,
            }
        )

        projection_rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "PI_RNN_projection_MAE":
                    projection_P[
                        "global_MAE"
                    ],

                "PI_RNN_projection_MAX":
                    projection_P[
                        "global_MAX"
                    ],

                "PI_RNN_covered_projection_MAE":
                    projection_P[
                        "covered_MAE"
                    ],

                "PI_RNN_uncovered_projection_MAE":
                    projection_P[
                        "uncovered_MAE"
                    ],

                "PI_RNN_fraction_cells_deltaS_gt_0p05":
                    projection_P[
                        "fraction_cells_deltaS_gt_0p05"
                    ],

                "PI_RNN_fraction_covered_deltaS_gt_0p05":
                    projection_P[
                        "fraction_covered_deltaS_gt_0p05"
                    ],

                "PI_RNN_fraction_uncovered_deltaS_gt_0p05":
                    projection_P[
                        "fraction_uncovered_deltaS_gt_0p05"
                    ],

                "SG7A_projection_MAE":
                    projection_T[
                        "global_MAE"
                    ],

                "SG7A_projection_MAX":
                    projection_T[
                        "global_MAX"
                    ],

                "SG7A_covered_projection_MAE":
                    projection_T[
                        "covered_MAE"
                    ],

                "SG7A_uncovered_projection_MAE":
                    projection_T[
                        "uncovered_MAE"
                    ],

                "SG7A_fraction_cells_deltaS_gt_0p05":
                    projection_T[
                        "fraction_cells_deltaS_gt_0p05"
                    ],
            }
        )

        print(
            f"\n  t = {time_days:.1f} days"
        )

        print(
            f"    Footprint IoU          : "
            f"{footprint_iou:.4f}"
        )

        print(
            f"    Strong-plume IoU       : "
            f"{strong_iou:.4f}"
        )

        print(
            f"    Core IoU               : "
            f"{core_iou:.4f}"
        )

        print(
            f"    Plume volume error     : "
            f"{volume_relative_error:.3%}"
        )

        print(
            f"    Centroid displacement  : "
            f"{centroid_distance_cells:.3f} cells"
        )

        print(
            f"    Vertical extent diff   : "
            f"{vertical_difference} layers"
        )

        print(
            f"    SG7A plume coverage    : "
            f"{support_T['covered_plume_fraction']:.3%}"
        )

        print(
            f"    PI-RNN projection MAE  : "
            f"{projection_P['global_MAE']:.6e}"
        )

        print(
            f"    PI-RNN projection MAX  : "
            f"{projection_P['global_MAX']:.6e}"
        )

        # ---------------------------------------------------------------------
        # Figures
        # ---------------------------------------------------------------------

        plot_plume_footprint(
            time_days,
            P,
            T,
        )

        plot_projection_map(
            time_days,
            P_raw,
            P,
        )

    # =========================================================================
    # GLOBAL DECISION
    # =========================================================================

    plume_morphology_pass = all(
        canonical_passes
    )

    plume_coverage_pass = all(
        plume_support_passes
    )

    # -------------------------------------------------------------------------
    # Seed-density diagnosis
    #
    # We deliberately distinguish:
    #
    #   map-back validity
    #   plume agreement
    #   streamline support adequacy
    #
    # If plume morphology agrees but direct plume coverage is poor, seed
    # convergence becomes the next scientific question.
    # -------------------------------------------------------------------------

    if (
        plume_morphology_pass
        and
        plume_coverage_pass
    ):

        seed_decision = (
            "CURRENT_7X7_SEEDING_ACCEPTABLE"
        )

        next_milestone = (
            "V15-SG7F — Freeze Deterministic Full-Grid "
            "Transport Baseline / PAD-Stream Integration"
        )

    elif (
        plume_morphology_pass
        and
        not plume_coverage_pass
    ):

        seed_decision = (
            "REOPEN_SEED_CONVERGENCE_FOR_SPATIAL_SUPPORT"
        )

        next_milestone = (
            "V15-SG5C — Streamline Seed-Density "
            "Convergence for Eulerian Coverage"
        )

    else:

        seed_decision = (
            "PLUME_RECONSTRUCTION_REQUIRES_DIAGNOSIS"
        )

        next_milestone = (
            "Diagnose SG7E plume morphology discrepancy "
            "before changing seed density"
        )

    validation_passed = (
        plume_morphology_pass
    )

    # =========================================================================
    # VALIDATION PRINT
    # =========================================================================

    checks = [
        (
            "SG7D accepted map-back database loaded",
            True,
        ),

        (
            "Grid shape = 15 x 50 x 50",
            grid_shape
            ==
            GRID_SHAPE,
        ),

        (
            "Coverage mask finite",
            np.all(
                np.isfinite(
                    coverage_mask
                )
            ),
        ),

        (
            "PI-RNN full-grid saturation finite",
            np.all(
                np.isfinite(
                    pirnn
                )
            ),
        ),

        (
            "SG7A full-grid saturation finite",
            np.all(
                np.isfinite(
                    truth
                )
            ),
        ),

        (
            "PI-RNN saturation bounds respected",
            np.min(
                pirnn
            )
            >=
            S_MIN
            -
            1.0e-8
            and
            np.max(
                pirnn
            )
            <=
            S_MAX
            +
            1.0e-8,
        ),

        (
            "SG7A saturation bounds respected",
            np.min(
                truth
            )
            >=
            S_MIN
            -
            1.0e-8
            and
            np.max(
                truth
            )
            <=
            S_MAX
            +
            1.0e-8,
        ),

        (
            f"All plume footprint IoU >= {FOOTPRINT_IOU_MIN:.2f}",
            all(
                row[
                    "footprint_pass"
                ]
                for row
                in plume_rows
            ),
        ),

        (
            (
                "All plume-volume relative errors "
                f"<= {PLUME_VOLUME_REL_ERROR_MAX:.0%}"
            ),
            all(
                row[
                    "volume_pass"
                ]
                for row
                in plume_rows
            ),
        ),

        (
            (
                "All centroid offsets <= "
                f"{CENTROID_DISTANCE_MAX_CELLS:.1f} cells"
            ),
            all(
                row[
                    "centroid_pass"
                ]
                for row
                in plume_rows
            ),
        ),

        (
            (
                "All vertical extent differences <= "
                f"{VERTICAL_EXTENT_DIFFERENCE_MAX_LAYERS} layers"
            ),
            all(
                row[
                    "vertical_pass"
                ]
                for row
                in plume_rows
            ),
        ),
    ]

    validation_passed = all(
        status
        for _, status
        in checks
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7E FULL-GRID PLUME VALIDATION"
    )

    print(
        "=" * 78
    )

    for description, status in checks:

        print(
            f"[{'PASS' if status else 'FAIL':4s}] "
            f"{description}"
        )

    print(
        "=" * 78
    )

    print(
        f"Direct cell coverage       : "
        f"{coverage_fraction:.3%}"
    )

    print(
        f"Minimum layer coverage     : "
        f"{min_layer_coverage:.3%}"
    )

    print(
        f"Maximum layer coverage     : "
        f"{max_layer_coverage:.3%}"
    )

    print(
        f"Plume morphology pass      : "
        f"{plume_morphology_pass}"
    )

    print(
        f"Direct plume support pass  : "
        f"{plume_coverage_pass}"
    )

    print(
        f"Seed-density decision      : "
        f"{seed_decision}"
    )

    # =========================================================================
    # SAVE TABLES
    # =========================================================================

    save_csv(
        PLUME_METRICS_FILE,
        plume_rows,
    )

    save_csv(
        COVERAGE_BY_LAYER_FILE,
        layer_rows,
    )

    save_csv(
        PROJECTION_METRICS_FILE,
        projection_rows,
    )

    # =========================================================================
    # DATABASE
    # =========================================================================

    np.savez_compressed(
        DATABASE_FILE,

        times_days=
            times,

        coverage_mask=
            coverage_mask,

        streamline_count=
            streamline_count,

        coverage_weight_m3=
            coverage_weight,

        PI_RNN_corrected=
            pirnn,

        SG7A_corrected=
            truth,

        PI_RNN_raw=
            pirnn_raw,

        SG7A_raw=
            truth_raw,
    )

    # =========================================================================
    # PLOTS
    # =========================================================================

    plot_layer_coverage(
        layer_rows
    )

    plot_centroid_trajectory(
        plume_rows
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    maximum_projection_mae = max(
        row[
            "PI_RNN_projection_MAE"
        ]
        for row
        in projection_rows
    )

    maximum_projection_fraction_gt_005 = max(
        row[
            "PI_RNN_fraction_cells_deltaS_gt_0p05"
        ]
        for row
        in projection_rows
    )

    minimum_plume_coverage = min(
        row[
            "SG7A_direct_plume_coverage"
        ]
        for row
        in plume_rows
    )

    minimum_footprint_iou = min(
        row[
            "footprint_IoU"
        ]
        for row
        in plume_rows
    )

    maximum_centroid_distance = max(
        row[
            "centroid_distance_cells"
        ]
        for row
        in plume_rows
    )

    maximum_volume_error = max(
        row[
            "plume_volume_relative_error"
        ]
        for row
        in plume_rows
    )

    summary = {
        "milestone":
            "V15-SG7E",

        "description":
            (
                "Full-grid plume morphology, coverage, "
                "projection-dependence, and seed-density validation"
            ),

        "training_performed":
            False,

        "mapback_modified":
            False,

        "seed_density_modified":
            False,

        "source":
            "V15-SG7D",

        "coverage": {
            "covered_cells":
                covered_cells,

            "total_cells":
                total_cells,

            "direct_cell_coverage_fraction":
                coverage_fraction,

            "minimum_layer_coverage":
                min_layer_coverage,

            "maximum_layer_coverage":
                max_layer_coverage,

            "minimum_SG7A_plume_direct_coverage":
                minimum_plume_coverage,
        },

        "plume_agreement": {
            "minimum_footprint_IoU":
                minimum_footprint_iou,

            "maximum_plume_volume_relative_error":
                maximum_volume_error,

            "maximum_centroid_distance_cells":
                maximum_centroid_distance,

            "morphology_pass":
                plume_morphology_pass,
        },

        "projection_dependence": {
            "maximum_PI_RNN_projection_MAE":
                maximum_projection_mae,

            "maximum_fraction_cells_deltaS_gt_0p05":
                maximum_projection_fraction_gt_005,

            "status":
                "DIAGNOSTIC_ONLY_IN_SG7E",
        },

        "streamline_support": {
            "required_direct_plume_fraction":
                COVERED_PLUME_FRACTION_MIN,

            "all_times_pass":
                plume_coverage_pass,

            "seed_density_decision":
                seed_decision,
        },

        "validation_passed":
            bool(
                validation_passed
            ),

        "status":
            (
                "FULL_GRID_PLUME_VALIDATION_PASS"
                if validation_passed
                else
                "FULL_GRID_PLUME_VALIDATION_FAIL"
            ),

        "next_milestone":
            next_milestone,
    }

    with open(
        SUMMARY_FILE,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            summary,
            handle,
            indent=2,
        )

    # =========================================================================
    # OUTPUT
    # =========================================================================

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
        "  V15SG7E_Plume_Metrics.csv"
    )

    print(
        "  V15SG7E_Coverage_By_Layer.csv"
    )

    print(
        "  V15SG7E_Projection_Dependence.csv"
    )

    print(
        "\nDatabase:"
    )

    print(
        "  V15SG7E_Plume_Coverage_Validation.npz"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7E_Coverage_By_Layer.png"
    )

    print(
        "  V15SG7E_Centroid_Trajectory.png"
    )

    for time_days in times:

        print(
            "  "
            f"V15SG7E_PlumeFootprint_{int(time_days)}d.png"
        )

        print(
            "  "
            f"V15SG7E_Projection_Layer08_{int(time_days)}d.png"
        )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7E_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    if validation_passed:

        print(
            "V15-SG7E FULL-GRID PLUME VALIDATION: PASS"
        )

        print()

        if seed_decision == (
            "CURRENT_7X7_SEEDING_ACCEPTABLE"
        ):

            print(
                "STATUS:"
            )

            print(
                "CURRENT 7x7 STREAMLINE SYSTEM "
                "ACCEPTED FOR DETERMINISTIC SGSIM PLUME"
            )

            print()

            print(
                "Next milestone:"
            )

            print(
                "V15-SG7F — Freeze Deterministic Full-Grid "
                "Transport Baseline / PAD-Stream Integration"
            )

        else:

            print(
                "STATUS:"
            )

            print(
                "PLUME MORPHOLOGY ACCEPTABLE, BUT "
                "DIRECT STREAMLINE SUPPORT REQUIRES REVIEW"
            )

            print()

            print(
                "Next milestone:"
            )

            print(
                "V15-SG5C — Streamline Seed-Density "
                "Convergence for Eulerian Coverage"
            )

    else:

        print(
            "V15-SG7E FULL-GRID PLUME VALIDATION: FAIL"
        )

        print()

        print(
            "DO NOT CHANGE SEED DENSITY AUTOMATICALLY."
        )

        print(
            "First diagnose which plume morphology "
            "criterion failed."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()