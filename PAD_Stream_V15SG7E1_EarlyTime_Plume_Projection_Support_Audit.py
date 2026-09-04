from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7E-1
# Early-Time Plume / Projection / Support Audit
#
# NO TRAINING.
# NO SEED-DENSITY CHANGE.
# NO MAP-BACK CHANGE.
# NO VALIDATION-THRESHOLD CHANGE.
#
#
# PURPOSE
# -------
# Diagnose the isolated V15-SG7E plume-volume failure at 100 days:
#
#       plume-volume error = 10.343%
#
# against the established:
#
#       <= 10%
#
#
# SG7E otherwise showed:
#
#       footprint IoU = 1.0000
#       strong-plume IoU ~ 0.997
#       core IoU ~ 0.990
#       centroid displacement = 0.078 cells
#       vertical extent difference = 0
#
#
# Therefore SG7E-1 asks:
#
#   1. Is the 100-day plume-volume discrepancy sensitive to the chosen
#      saturation threshold?
#
#   2. Do PI-RNN and SG7A already agree BEFORE the global conservative
#      projection?
#
#   3. How much displaced-phase inventory resides in directly covered
#      versus uncovered cells?
#
#   4. Are large projection corrections concentrated in cells with weak
#      or zero streamline support?
#
#
# POSSIBLE DIAGNOSES
# ------------------
#
# THRESHOLD_SENSITIVITY
# PROJECTION_DEPENDENCE
# INSUFFICIENT_STREAMLINE_SUPPORT
# SUPPORT_WEIGHTED_PROJECTION_BEHAVIOR_ACCEPTABLE
# MIXED_LIMITATION
#
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent


SG7E_FILE = (
    ROOT
    / "output"
    / "V15_SG7E"
    / "V15SG7E_Plume_Coverage_Validation.npz"
)


SG7E_SUMMARY_FILE = (
    ROOT
    / "output"
    / "V15_SG7E"
    / "PAD_Stream_V15SG7E_Summary.json"
)

SG7E_PLUME_METRICS_FILE = (
    ROOT
    / "output"
    / "V15_SG7E"
    / "V15SG7E_Plume_Metrics.csv"
)

SG7D_FILE = (
    ROOT
    / "output"
    / "V15_SG7D"
    / "SG7D_CONSERVATIVE_GRID_MAPBACK.npz"
)


OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7E1"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


THRESHOLD_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7E1_Threshold_Sensitivity.csv"
)


RAW_CORRECTED_FILE = (
    OUTPUT_DIR
    / "V15SG7E1_Raw_vs_Corrected.csv"
)


INVENTORY_FILE = (
    OUTPUT_DIR
    / "V15SG7E1_Covered_Uncovered_Inventory.csv"
)


SUPPORT_FILE = (
    OUTPUT_DIR
    / "V15SG7E1_Projection_vs_Support.csv"
)


DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7E1_Diagnostic_Database.npz"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7E1_Summary.json"
)


# =============================================================================
# GRID / PHYSICS CONTRACT
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

POROSITY = 0.20

CELL_BULK_VOLUME_M3 = (
    DX_M
    *
    DY_M
    *
    DZ_M
)

CELL_PORE_VOLUME_M3 = (
    POROSITY
    *
    CELL_BULK_VOLUME_M3
)


S_INITIAL = 0.20

S_MIN = 0.20
S_MAX = 0.80


# =============================================================================
# THRESHOLD AUDIT
#
# These are DIAGNOSTIC thresholds only.
#
# We are NOT selecting a new acceptance threshold from this list.
# =============================================================================

DELTA_S_THRESHOLDS = np.asarray(
    [
        0.005,
        0.010,
        0.020,
        0.050,
    ],
    dtype=np.float64,
)


CORE_THRESHOLD = 0.50


# =============================================================================
# EXISTING SG7E ACCEPTANCE REFERENCE
# =============================================================================

SG7E_VOLUME_ERROR_GATE = 0.10

PRIMARY_DELTA_S = 0.010


# =============================================================================
# SUPPORT BINS
# =============================================================================

SUPPORT_BINS = [
    (
        "N=0",
        0,
        0,
    ),

    (
        "N=1",
        1,
        1,
    ),

    (
        "N=2-3",
        2,
        3,
    ),

    (
        "N=4-7",
        4,
        7,
    ),

    (
        "N=8-15",
        8,
        15,
    ),

    (
        "N>=16",
        16,
        None,
    ),
]


EPS = 1.0e-14


# =============================================================================
# HELPERS
# =============================================================================

def mae(values):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    if values.size == 0:

        return 0.0

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

    if values.size == 0:

        return 0.0

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
# LOAD SAME-CASE SG7E PRIMARY PLUME REFERENCE
#
# IMPORTANT
# ---------
#
# SG7E-1 originally used the canonical 7x7 value:
#
#       10.343%
#
# as a hard-coded reproduction target.
#
# That is valid only for the original 7x7 case.
#
# During SG5C, each seed-density branch has its own SG7E result.
#
# Therefore SG7E-1 must reproduce the SG7E result generated in the SAME
# workspace and SAME seed case.
#
# No validation threshold is being changed.
# =============================================================================

def load_sg7e_primary_reference():

    if not SG7E_PLUME_METRICS_FILE.exists():

        raise FileNotFoundError(
            "Missing same-case SG7E plume metrics:\n"
            f"{SG7E_PLUME_METRICS_FILE}"
        )

    with open(
        SG7E_PLUME_METRICS_FILE,
        "r",
        newline="",
        encoding="utf-8",
    ) as handle:

        rows = list(
            csv.DictReader(
                handle
            )
        )

    candidates = [
        row
        for row
        in rows
        if np.isclose(
            float(
                row[
                    "time_days"
                ]
            ),
            100.0,
        )
    ]

    if len(
        candidates
    ) != 1:

        raise RuntimeError(
            "Could not identify exactly one 100-day "
            "SG7E plume-metric row."
        )

    row = candidates[0]

    required = [
        "plume_volume_relative_error",
        "footprint_IoU",
    ]

    for key in required:

        if key not in row:

            raise KeyError(
                "SG7E plume metrics missing required field: "
                f"{key}"
            )

    return {
        "time_days":
            float(
                row[
                    "time_days"
                ]
            ),

        "plume_volume_relative_error":
            float(
                row[
                    "plume_volume_relative_error"
                ]
            ),

        "footprint_IoU":
            float(
                row[
                    "footprint_IoU"
                ]
            ),
    }

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

    n_union = int(
        np.sum(
            union
        )
    )

    if n_union == 0:

        return 1.0

    return float(
        np.sum(
            intersection
        )
        /
        n_union
    )


# =============================================================================
# LOAD
# =============================================================================

def load_inputs():

    if not SG7E_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7E diagnostic database:\n"
            f"{SG7E_FILE}"
        )

    if not SG7D_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7D map-back database:\n"
            f"{SG7D_FILE}"
        )

    if not SG7E_SUMMARY_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7E summary:\n"
            f"{SG7E_SUMMARY_FILE}"
        )

    with open(
        SG7E_SUMMARY_FILE,
        "r",
        encoding="utf-8",
    ) as handle:

        sg7e_summary = json.load(
            handle
        )

    sg7e = np.load(
        SG7E_FILE
    )

    sg7d = np.load(
        SG7D_FILE
    )

    required_sg7e = [
        "times_days",
        "coverage_mask",
        "streamline_count",
        "PI_RNN_corrected",
        "SG7A_corrected",
        "PI_RNN_raw",
        "SG7A_raw",
    ]

    for key in required_sg7e:

        if key not in sg7e:

            raise KeyError(
                f"SG7E field missing: {key}"
            )

    return {
        "times":
            np.asarray(
                sg7e[
                    "times_days"
                ],
                dtype=np.float64,
            ),

        "coverage_mask":
            np.asarray(
                sg7e[
                    "coverage_mask"
                ],
                dtype=bool,
            ),

        "streamline_count":
            np.asarray(
                sg7e[
                    "streamline_count"
                ],
                dtype=np.int64,
            ),

        "pirnn_corrected":
            np.asarray(
                sg7e[
                    "PI_RNN_corrected"
                ],
                dtype=np.float64,
            ),

        "truth_corrected":
            np.asarray(
                sg7e[
                    "SG7A_corrected"
                ],
                dtype=np.float64,
            ),

        "pirnn_raw":
            np.asarray(
                sg7e[
                    "PI_RNN_raw"
                ],
                dtype=np.float64,
            ),

        "truth_raw":
            np.asarray(
                sg7e[
                    "SG7A_raw"
                ],
                dtype=np.float64,
            ),

        "summary":
            sg7e_summary,
    }


# =============================================================================
# THRESHOLD-SENSITIVE PLUME METRICS
# =============================================================================

def threshold_metrics(
    pirnn,
    truth,
    delta_s,
):

    threshold = (
        S_INITIAL
        +
        float(
            delta_s
        )
    )

    mask_p = (
        pirnn
        >
        threshold
    )

    mask_t = (
        truth
        >
        threshold
    )

    cells_p = int(
        np.sum(
            mask_p
        )
    )

    cells_t = int(
        np.sum(
            mask_t
        )
    )

    volume_p = (
        cells_p
        *
        CELL_BULK_VOLUME_M3
    )

    volume_t = (
        cells_t
        *
        CELL_BULK_VOLUME_M3
    )

    relative_error = abs(
        volume_p
        -
        volume_t
    ) / max(
        volume_t,
        EPS,
    )

    footprint_p = np.any(
        mask_p,
        axis=0,
    )

    footprint_t = np.any(
        mask_t,
        axis=0,
    )

    footprint_iou = mask_iou(
        footprint_p,
        footprint_t,
    )

    volume_iou = mask_iou(
        mask_p,
        mask_t,
    )

    return {
        "threshold":
            threshold,

        "PI_RNN_cells":
            cells_p,

        "SG7A_cells":
            cells_t,

        "PI_RNN_volume_m3":
            volume_p,

        "SG7A_volume_m3":
            volume_t,

        "volume_relative_error":
            relative_error,

        "3D_plume_IoU":
            volume_iou,

        "footprint_IoU":
            footprint_iou,
    }


# =============================================================================
# RAW VERSUS CORRECTED
# =============================================================================

def raw_corrected_metrics(
    pirnn_raw,
    truth_raw,
    pirnn_corrected,
    truth_corrected,
    delta_s,
):

    raw = threshold_metrics(
        pirnn_raw,
        truth_raw,
        delta_s,
    )

    corrected = threshold_metrics(
        pirnn_corrected,
        truth_corrected,
        delta_s,
    )

    raw_state_L1 = mae(
        pirnn_raw
        -
        truth_raw
    )

    corrected_state_L1 = mae(
        pirnn_corrected
        -
        truth_corrected
    )

    return {
        "raw_volume_error":
            raw[
                "volume_relative_error"
            ],

        "corrected_volume_error":
            corrected[
                "volume_relative_error"
            ],

        "raw_3D_IoU":
            raw[
                "3D_plume_IoU"
            ],

        "corrected_3D_IoU":
            corrected[
                "3D_plume_IoU"
            ],

        "raw_footprint_IoU":
            raw[
                "footprint_IoU"
            ],

        "corrected_footprint_IoU":
            corrected[
                "footprint_IoU"
            ],

        "raw_state_L1":
            raw_state_L1,

        "corrected_state_L1":
            corrected_state_L1,
    }


# =============================================================================
# COVERED / UNCOVERED DISPLACED-PHASE INVENTORY
# =============================================================================

def inventory_partition(
    saturation,
    coverage_mask,
):

    displaced = (
        CELL_PORE_VOLUME_M3
        *
        np.maximum(
            saturation
            -
            S_INITIAL,
            0.0,
        )
    )

    total = float(
        np.sum(
            displaced
        )
    )

    covered = float(
        np.sum(
            displaced[
                coverage_mask
            ]
        )
    )

    uncovered = float(
        np.sum(
            displaced[
                ~coverage_mask
            ]
        )
    )

    return {
        "total_m3":
            total,

        "covered_m3":
            covered,

        "uncovered_m3":
            uncovered,

        "covered_fraction":
            (
                covered
                /
                max(
                    total,
                    EPS,
                )
            ),

        "uncovered_fraction":
            (
                uncovered
                /
                max(
                    total,
                    EPS,
                )
            ),
    }


# =============================================================================
# PROJECTION VS SUPPORT
# =============================================================================

def support_bin_metrics(
    raw,
    corrected,
    streamline_count,
):

    correction = np.abs(
        corrected
        -
        raw
    )

    rows = []

    for (
        label,
        lower,
        upper,
    ) in SUPPORT_BINS:

        if upper is None:

            mask = (
                streamline_count
                >=
                lower
            )

        else:

            mask = (
                (
                    streamline_count
                    >=
                    lower
                )
                &
                (
                    streamline_count
                    <=
                    upper
                )
            )

        values = (
            correction[
                mask
            ]
        )

        rows.append(
            {
                "support_bin":
                    label,

                "cells":
                    int(
                        np.sum(
                            mask
                        )
                    ),

                "projection_MAE":
                    mae(
                        values
                    ),

                "projection_RMS":
                    rms(
                        values
                    ),

                "projection_MAX":
                    (
                        float(
                            np.max(
                                values
                            )
                        )
                        if values.size
                        else 0.0
                    ),

                "fraction_deltaS_gt_0p05":
                    (
                        float(
                            np.mean(
                                values
                                >
                                0.05
                            )
                        )
                        if values.size
                        else 0.0
                    ),

                "fraction_deltaS_gt_0p10":
                    (
                        float(
                            np.mean(
                                values
                                >
                                0.10
                            )
                        )
                        if values.size
                        else 0.0
                    ),
            }
        )

    return rows


# =============================================================================
# PLOTS
# =============================================================================

def plot_threshold_sensitivity(
    threshold_rows,
):

    thresholds = sorted(
        set(
            row[
                "delta_S"
            ]
            for row
            in threshold_rows
        )
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    rows_100 = [
        row
        for row
        in threshold_rows
        if np.isclose(
            row[
                "time_days"
            ],
            100.0,
        )
    ]

    rows_100 = sorted(
        rows_100,
        key=lambda row:
            row[
                "delta_S"
            ],
    )

    ax.plot(
        [
            row[
                "delta_S"
            ]
            for row
            in rows_100
        ],
        [
            100.0
            *
            row[
                "corrected_volume_relative_error"
            ]
            for row
            in rows_100
        ],
        marker="o",
        label="Corrected-grid volume error",
    )

    ax.plot(
        [
            row[
                "delta_S"
            ]
            for row
            in rows_100
        ],
        [
            100.0
            *
            row[
                "raw_volume_relative_error"
            ]
            for row
            in rows_100
        ],
        marker="s",
        label="Raw-grid volume error",
    )

    ax.axhline(
        100.0
        *
        SG7E_VOLUME_ERROR_GATE,
        linestyle="--",
        label="Existing SG7E gate",
    )

    ax.set_xlabel(
        r"$\Delta S$ plume threshold"
    )

    ax.set_ylabel(
        "Plume-volume relative error [%]"
    )

    ax.set_title(
        "PAD-Stream V15-SG7E-1\n"
        "100-Day Plume-Threshold Sensitivity"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7E1_Threshold_Sensitivity_100d.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_inventory_partition(
    inventory_rows,
):

    times = sorted(
        set(
            row[
                "time_days"
            ]
            for row
            in inventory_rows
        )
    )

    truth_rows = [
        row
        for row
        in inventory_rows
        if row[
            "model"
        ]
        ==
        "SG7A"
    ]

    truth_rows = sorted(
        truth_rows,
        key=lambda row:
            row[
                "time_days"
            ],
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        [
            row[
                "time_days"
            ]
            for row
            in truth_rows
        ],
        [
            row[
                "covered_fraction"
            ]
            for row
            in truth_rows
        ],
        marker="o",
        label="Covered inventory fraction",
    )

    ax.plot(
        [
            row[
                "time_days"
            ]
            for row
            in truth_rows
        ],
        [
            row[
                "uncovered_fraction"
            ]
            for row
            in truth_rows
        ],
        marker="s",
        label="Uncovered inventory fraction",
    )

    ax.set_xlabel(
        "Time [days]"
    )

    ax.set_ylabel(
        "Fraction of displaced-phase inventory"
    )

    ax.set_ylim(
        0.0,
        1.0,
    )

    ax.set_title(
        "PAD-Stream V15-SG7E-1\n"
        "SG7A Inventory Support Partition"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7E1_Inventory_Coverage.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_projection_vs_support(
    support_rows,
):

    rows_1000 = [
        row
        for row
        in support_rows
        if np.isclose(
            row[
                "time_days"
            ],
            1000.0,
        )
        and
        row[
            "model"
        ]
        ==
        "PI-RNN"
    ]

    labels = [
        row[
            "support_bin"
        ]
        for row
        in rows_1000
    ]

    values = [
        row[
            "projection_MAE"
        ]
        for row
        in rows_1000
    ]

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.bar(
        labels,
        values,
    )

    ax.set_xlabel(
        "Unique streamline support"
    )

    ax.set_ylabel(
        "Mean |projection correction|"
    )

    ax.set_title(
        "PAD-Stream V15-SG7E-1\n"
        "1000-Day Projection Correction vs Support"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7E1_Projection_vs_Support_1000d.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_raw_corrected_100d(
    pirnn_raw,
    truth_raw,
    pirnn_corrected,
    truth_corrected,
):

    layer = 7

    fig, axes = plt.subplots(
        2,
        2,
        figsize=(
            11,
            10,
        )
    )

    im0 = axes[0, 0].imshow(
        pirnn_raw[
            layer
        ],
        origin="lower",
        vmin=S_MIN,
        vmax=S_MAX,
    )

    axes[0, 0].set_title(
        "PI-RNN raw"
    )

    fig.colorbar(
        im0,
        ax=axes[0, 0],
    )

    im1 = axes[0, 1].imshow(
        truth_raw[
            layer
        ],
        origin="lower",
        vmin=S_MIN,
        vmax=S_MAX,
    )

    axes[0, 1].set_title(
        "SG7A raw"
    )

    fig.colorbar(
        im1,
        ax=axes[0, 1],
    )

    im2 = axes[1, 0].imshow(
        pirnn_corrected[
            layer
        ],
        origin="lower",
        vmin=S_MIN,
        vmax=S_MAX,
    )

    axes[1, 0].set_title(
        "PI-RNN corrected"
    )

    fig.colorbar(
        im2,
        ax=axes[1, 0],
    )

    im3 = axes[1, 1].imshow(
        truth_corrected[
            layer
        ],
        origin="lower",
        vmin=S_MIN,
        vmax=S_MAX,
    )

    axes[1, 1].set_title(
        "SG7A corrected"
    )

    fig.colorbar(
        im3,
        ax=axes[1, 1],
    )

    for ax in axes.ravel():

        ax.set_xlabel(
            "i"
        )

        ax.set_ylabel(
            "j"
        )

    fig.suptitle(
        "PAD-Stream V15-SG7E-1\n"
        "100-Day Raw vs Conservative Grid Reconstruction — Layer 8"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7E1_Raw_vs_Corrected_100d.png",
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
        "PAD-Stream Version 15-SG7E-1"
    )

    print(
        "Early-Time Plume / Projection / Support Audit"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    print(
        "NO SEED DENSITY WILL BE CHANGED."
    )

    print(
        "NO MAP-BACK OPERATOR WILL BE CHANGED."
    )

    print(
        "NO SG7E VALIDATION THRESHOLD WILL BE CHANGED."
    )

    data = load_inputs()

    times = data[
        "times"
    ]

    coverage_mask = data[
        "coverage_mask"
    ]

    streamline_count = data[
        "streamline_count"
    ]

    pirnn_raw = data[
        "pirnn_raw"
    ]

    truth_raw = data[
        "truth_raw"
    ]

    pirnn_corrected = data[
        "pirnn_corrected"
    ]

    truth_corrected = data[
        "truth_corrected"
    ]

    # =========================================================================
    # SAME-CASE SG7E REPRODUCTION CONTRACT
    # =========================================================================

    sg7e_primary_reference = (
        load_sg7e_primary_reference()
    )

    print(
        "\nSAME-CASE SG7E PRIMARY REFERENCE"
    )

    print(
        f"  Time                    : "
        f"{sg7e_primary_reference['time_days']:.1f} days"
    )

    print(
        f"  Volume relative error   : "
        f"{sg7e_primary_reference['plume_volume_relative_error']:.3%}"
    )

    print(
        f"  Footprint IoU           : "
        f"{sg7e_primary_reference['footprint_IoU']:.6f}"
    )

    # =========================================================================
    # FIND 100-DAY INDEX
    # =========================================================================

    index_100 = int(
        np.argmin(
            np.abs(
                times
                -
                100.0
            )
        )
    )

    if not np.isclose(
        times[
            index_100
        ],
        100.0,
    ):

        raise RuntimeError(
            "100-day SG7E state is not available."
        )

    # =========================================================================
    # 1. THRESHOLD SENSITIVITY
    # =========================================================================

    threshold_rows = []

    print(
        "\n"
        + "=" * 78
    )

    print(
        "PLUME-THRESHOLD SENSITIVITY"
    )

    print(
        "=" * 78
    )

    for time_index, time_days in enumerate(
        times
    ):

        for delta_s in (
            DELTA_S_THRESHOLDS
        ):

            raw_metrics = (
                threshold_metrics(
                    pirnn_raw[
                        time_index
                    ],
                    truth_raw[
                        time_index
                    ],
                    delta_s,
                )
            )

            corrected_metrics = (
                threshold_metrics(
                    pirnn_corrected[
                        time_index
                    ],
                    truth_corrected[
                        time_index
                    ],
                    delta_s,
                )
            )

            threshold_rows.append(
                {
                    "time_days":
                        float(
                            time_days
                        ),

                    "delta_S":
                        float(
                            delta_s
                        ),

                    "absolute_threshold":
                        float(
                            S_INITIAL
                            +
                            delta_s
                        ),

                    "raw_volume_relative_error":
                        raw_metrics[
                            "volume_relative_error"
                        ],

                    "corrected_volume_relative_error":
                        corrected_metrics[
                            "volume_relative_error"
                        ],

                    "raw_3D_IoU":
                        raw_metrics[
                            "3D_plume_IoU"
                        ],

                    "corrected_3D_IoU":
                        corrected_metrics[
                            "3D_plume_IoU"
                        ],

                    "raw_footprint_IoU":
                        raw_metrics[
                            "footprint_IoU"
                        ],

                    "corrected_footprint_IoU":
                        corrected_metrics[
                            "footprint_IoU"
                        ],
                }
            )

            if np.isclose(
                time_days,
                100.0,
            ):

                print(
                    f"  ΔS={delta_s:.3f} | "
                    f"raw volume error="
                    f"{raw_metrics['volume_relative_error']:.3%} | "
                    f"corrected="
                    f"{corrected_metrics['volume_relative_error']:.3%} | "
                    f"raw IoU="
                    f"{raw_metrics['3D_plume_IoU']:.4f} | "
                    f"corrected IoU="
                    f"{corrected_metrics['3D_plume_IoU']:.4f}"
                )

    # =========================================================================
    # 2. RAW VS CORRECTED
    # =========================================================================

    raw_corrected_rows = []

    print(
        "\n"
        + "=" * 78
    )

    print(
        "RAW VS CORRECTED PI-RNN / SG7A AGREEMENT"
    )

    print(
        "=" * 78
    )

    for time_index, time_days in enumerate(
        times
    ):

        metrics = raw_corrected_metrics(
            pirnn_raw[
                time_index
            ],
            truth_raw[
                time_index
            ],
            pirnn_corrected[
                time_index
            ],
            truth_corrected[
                time_index
            ],
            PRIMARY_DELTA_S,
        )

        raw_corrected_rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                **metrics,
            }
        )

        print(
            f"\n  t={time_days:.0f} days"
        )

        print(
            f"    Raw state L1           : "
            f"{metrics['raw_state_L1']:.6e}"
        )

        print(
            f"    Corrected state L1     : "
            f"{metrics['corrected_state_L1']:.6e}"
        )

        print(
            f"    Raw 3D plume IoU       : "
            f"{metrics['raw_3D_IoU']:.4f}"
        )

        print(
            f"    Corrected 3D plume IoU : "
            f"{metrics['corrected_3D_IoU']:.4f}"
        )

        print(
            f"    Raw volume error       : "
            f"{metrics['raw_volume_error']:.3%}"
        )

        print(
            f"    Corrected volume error : "
            f"{metrics['corrected_volume_error']:.3%}"
        )

    # =========================================================================
    # 3. COVERED / UNCOVERED INVENTORY
    # =========================================================================

    inventory_rows = []

    print(
        "\n"
        + "=" * 78
    )

    print(
        "DISPLACED-PHASE INVENTORY SUPPORT"
    )

    print(
        "=" * 78
    )

    for time_index, time_days in enumerate(
        times
    ):

        for (
            model_name,
            saturation,
        ) in [
            (
                "PI-RNN",
                pirnn_corrected[
                    time_index
                ],
            ),

            (
                "SG7A",
                truth_corrected[
                    time_index
                ],
            ),
        ]:

            inv = inventory_partition(
                saturation,
                coverage_mask,
            )

            inventory_rows.append(
                {
                    "time_days":
                        float(
                            time_days
                        ),

                    "model":
                        model_name,

                    **inv,
                }
            )

            print(
                f"  {time_days:6.0f} d | "
                f"{model_name:6s} | "
                f"covered={inv['covered_fraction']:.3%} | "
                f"uncovered={inv['uncovered_fraction']:.3%} | "
                f"total={inv['total_m3']:.3f} m3"
            )

    # =========================================================================
    # 4. PROJECTION VS SUPPORT
    # =========================================================================

    support_rows = []

    print(
        "\n"
        + "=" * 78
    )

    print(
        "PROJECTION CORRECTION VS STREAMLINE SUPPORT"
    )

    print(
        "=" * 78
    )

    for time_index, time_days in enumerate(
        times
    ):

        for (
            model_name,
            raw,
            corrected,
        ) in [
            (
                "PI-RNN",
                pirnn_raw[
                    time_index
                ],
                pirnn_corrected[
                    time_index
                ],
            ),

            (
                "SG7A",
                truth_raw[
                    time_index
                ],
                truth_corrected[
                    time_index
                ],
            ),
        ]:

            rows = support_bin_metrics(
                raw,
                corrected,
                streamline_count,
            )

            for row in rows:

                support_rows.append(
                    {
                        "time_days":
                            float(
                                time_days
                            ),

                        "model":
                            model_name,

                        **row,
                    }
                )

            if np.isclose(
                time_days,
                1000.0,
            ) and model_name == "PI-RNN":

                print(
                    "\n  PI-RNN at 1000 days"
                )

                for row in rows:

                    print(
                        f"    {row['support_bin']:7s} | "
                        f"cells={row['cells']:6d} | "
                        f"MAE={row['projection_MAE']:.6e} | "
                        f"MAX={row['projection_MAX']:.6e} | "
                        f">0.05={row['fraction_deltaS_gt_0p05']:.2%}"
                    )

    # =========================================================================
    # DIAGNOSIS
    # =========================================================================

    primary_100 = [
        row
        for row
        in threshold_rows
        if (
            np.isclose(
                row[
                    "time_days"
                ],
                100.0,
            )
            and
            np.isclose(
                row[
                    "delta_S"
                ],
                PRIMARY_DELTA_S,
            )
        )
    ][0]

    other_100 = [
        row
        for row
        in threshold_rows
        if (
            np.isclose(
                row[
                    "time_days"
                ],
                100.0,
            )
            and
            not np.isclose(
                row[
                    "delta_S"
                ],
                PRIMARY_DELTA_S,
            )
        )
    ]

    other_errors = np.asarray(
        [
            row[
                "corrected_volume_relative_error"
            ]
            for row
            in other_100
        ],
        dtype=np.float64,
    )

    threshold_sensitive = (
        (
            np.max(
                other_errors
            )
            -
            np.min(
                other_errors
            )
        )
        >
        0.05
    )

    raw_100 = raw_corrected_rows[
        index_100
    ]

    raw_agreement_good = (
        raw_100[
            "raw_state_L1"
        ]
        <
        0.020
        and
        raw_100[
            "raw_3D_IoU"
        ]
        >
        0.90
    )

    sg7a_inventory_rows = [
        row
        for row
        in inventory_rows
        if row[
            "model"
        ]
        ==
        "SG7A"
    ]

    minimum_covered_inventory_fraction = min(
        row[
            "covered_fraction"
        ]
        for row
        in sg7a_inventory_rows
    )

    inventory_support_strong = (
        minimum_covered_inventory_fraction
        >=
        0.75
    )

    # -------------------------------------------------------------------------
    # Does projection magnitude decrease with support?
    # Compare unsupported cells with strongly supported cells.
    # -------------------------------------------------------------------------

    pirnn_1000_support = [
        row
        for row
        in support_rows
        if (
            row[
                "model"
            ]
            ==
            "PI-RNN"
            and
            np.isclose(
                row[
                    "time_days"
                ],
                1000.0,
            )
        )
    ]

    support_lookup = {
        row[
            "support_bin"
        ]:
            row
        for row
        in pirnn_1000_support
    }

    unsupported_projection = (
        support_lookup[
            "N=0"
        ][
            "projection_MAE"
        ]
    )

    high_support_projection = (
        support_lookup[
            "N>=16"
        ][
            "projection_MAE"
        ]
    )

    projection_support_hierarchy = (
        unsupported_projection
        >
        high_support_projection
    )

    # =========================================================================
    # DECISION
    # =========================================================================

    if (
        raw_agreement_good
        and
        inventory_support_strong
        and
        projection_support_hierarchy
    ):

        if threshold_sensitive:

            diagnosis = (
                "THRESHOLD_SENSITIVITY_WITH_ACCEPTABLE_SUPPORT"
            )

        else:

            diagnosis = (
                "SUPPORT_WEIGHTED_PROJECTION_BEHAVIOR_ACCEPTABLE"
            )

        next_milestone = (
            "V15-SG7F — Deterministic Full-Grid "
            "Transport Baseline Freeze"
        )

    elif (
        not inventory_support_strong
        or
        not projection_support_hierarchy
    ):

        diagnosis = (
            "INSUFFICIENT_STREAMLINE_SUPPORT"
        )

        next_milestone = (
            "V15-SG5C — Streamline Seed-Density "
            "Convergence for Eulerian Coverage"
        )

    elif not raw_agreement_good:

        diagnosis = (
            "PROJECTION_DEPENDENCE"
        )

        next_milestone = (
            "Diagnose raw map-back disagreement before "
            "changing streamline density"
        )

    else:

        diagnosis = (
            "MIXED_LIMITATION"
        )

        next_milestone = (
            "Review SG7E-1 diagnostics before selecting "
            "seed or map-back refinement"
        )

    # =========================================================================
    # VALIDATION
    #
    # This is a diagnostic milestone. PASS means the audit completed and
    # generated a scientifically interpretable diagnosis.
    # =========================================================================

    checks = [
        (
            "100-day SG7E plume-volume metric reproduced",
            np.isclose(
                primary_100[
                    "corrected_volume_relative_error"
                ],
                sg7e_primary_reference[
                    "plume_volume_relative_error"
                ],
                rtol=1.0e-8,
                atol=1.0e-10,
            ),
        ),

        (
            "100-day SG7E footprint IoU reproduced",
            np.isclose(
                primary_100[
                    "corrected_footprint_IoU"
                ],
                sg7e_primary_reference[
                    "footprint_IoU"
                ],
                rtol=1.0e-8,
                atol=1.0e-10,
            ),
        ),

        (
            "All threshold metrics finite",
            all(
                np.isfinite(
                    row[
                        "corrected_volume_relative_error"
                    ]
                )
                for row
                in threshold_rows
            ),
        ),

        (
            "All raw/corrected metrics finite",
            all(
                np.isfinite(
                    row[
                        "raw_state_L1"
                    ]
                )
                for row
                in raw_corrected_rows
            ),
        ),

        (
            "All inventory metrics finite",
            all(
                np.isfinite(
                    row[
                        "covered_fraction"
                    ]
                )
                for row
                in inventory_rows
            ),
        ),

        (
            "All support metrics finite",
            all(
                np.isfinite(
                    row[
                        "projection_MAE"
                    ]
                )
                for row
                in support_rows
            ),
        ),

        (
            "Diagnostic classification established",
            diagnosis
            in
            {
                "THRESHOLD_SENSITIVITY_WITH_ACCEPTABLE_SUPPORT",
                "SUPPORT_WEIGHTED_PROJECTION_BEHAVIOR_ACCEPTABLE",
                "INSUFFICIENT_STREAMLINE_SUPPORT",
                "PROJECTION_DEPENDENCE",
                "MIXED_LIMITATION",
            },
        ),
    ]

    passed = all(
        status
        for _, status
        in checks
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7E-1 DIAGNOSTIC VALIDATION"
    )

    print(
        "=" * 78
    )

    for (
        description,
        status,
    ) in checks:

        print(
            f"[{'PASS' if status else 'FAIL':4s}] "
            f"{description}"
        )

    print(
        "=" * 78
    )

    print(
        "\nDIAGNOSTIC FLAGS"
    )

    print(
        f"  Threshold sensitive      : "
        f"{threshold_sensitive}"
    )

    print(
        f"  Raw agreement good       : "
        f"{raw_agreement_good}"
    )

    print(
        f"  Min covered inventory    : "
        f"{minimum_covered_inventory_fraction:.3%}"
    )

    print(
        f"  Inventory support strong : "
        f"{inventory_support_strong}"
    )

    print(
        f"  N=0 projection MAE      : "
        f"{unsupported_projection:.6e}"
    )

    print(
        f"  N>=16 projection MAE    : "
        f"{high_support_projection:.6e}"
    )

    print(
        f"  Support hierarchy valid  : "
        f"{projection_support_hierarchy}"
    )

    print(
        "\nDIAGNOSIS"
    )

    print(
        f"  {diagnosis}"
    )

    print(
        "\nNEXT MILESTONE"
    )

    print(
        f"  {next_milestone}"
    )

    # =========================================================================
    # SAVE
    # =========================================================================

    save_csv(
        THRESHOLD_TABLE_FILE,
        threshold_rows,
    )

    save_csv(
        RAW_CORRECTED_FILE,
        raw_corrected_rows,
    )

    save_csv(
        INVENTORY_FILE,
        inventory_rows,
    )

    save_csv(
        SUPPORT_FILE,
        support_rows,
    )

    np.savez_compressed(
        DATABASE_FILE,

        times_days=
            times,

        coverage_mask=
            coverage_mask,

        streamline_count=
            streamline_count,

        PI_RNN_raw=
            pirnn_raw,

        SG7A_raw=
            truth_raw,

        PI_RNN_corrected=
            pirnn_corrected,

        SG7A_corrected=
            truth_corrected,
    )

    # =========================================================================
    # PLOTS
    # =========================================================================

    plot_threshold_sensitivity(
        threshold_rows
    )

    plot_inventory_partition(
        inventory_rows
    )

    plot_projection_vs_support(
        support_rows
    )

    plot_raw_corrected_100d(
        pirnn_raw[
            index_100
        ],
        truth_raw[
            index_100
        ],
        pirnn_corrected[
            index_100
        ],
        truth_corrected[
            index_100
        ],
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7E-1",

        "description":
            (
                "Early-time plume threshold, projection dependence, "
                "inventory support, and streamline-support audit"
            ),

        "training_performed":
            False,

        "seed_density_changed":
            False,

        "mapback_changed":
            False,

        "validation_threshold_changed":
            False,

        "source":
            "V15-SG7E",

        "100_day_primary_result": {
    "delta_S":
        PRIMARY_DELTA_S,

    "SG7E_reference_volume_relative_error":
        sg7e_primary_reference[
            "plume_volume_relative_error"
        ],

    "SG7E1_recomputed_volume_relative_error":
        primary_100[
            "corrected_volume_relative_error"
        ],

    "SG7E_reference_footprint_IoU":
        sg7e_primary_reference[
            "footprint_IoU"
        ],

    "SG7E1_recomputed_footprint_IoU":
        primary_100[
            "corrected_footprint_IoU"
        ],

    "existing_volume_gate":
        SG7E_VOLUME_ERROR_GATE,

    "same_case_reproduction":
        bool(
            np.isclose(
                primary_100[
                    "corrected_volume_relative_error"
                ],
                sg7e_primary_reference[
                    "plume_volume_relative_error"
                ],
                rtol=1.0e-8,
                atol=1.0e-10,
            )
            and
            np.isclose(
                primary_100[
                    "corrected_footprint_IoU"
                ],
                sg7e_primary_reference[
                    "footprint_IoU"
                ],
                rtol=1.0e-8,
                atol=1.0e-10,
            )
        ),
},

        "diagnostic_flags": {
            "threshold_sensitive":
                bool(
                    threshold_sensitive
                ),

            "raw_PI_RNN_SG7A_agreement_good":
                bool(
                    raw_agreement_good
                ),

            "minimum_SG7A_covered_inventory_fraction":
                minimum_covered_inventory_fraction,

            "inventory_support_strong":
                bool(
                    inventory_support_strong
                ),

            "unsupported_projection_MAE":
                unsupported_projection,

            "high_support_projection_MAE":
                high_support_projection,

            "projection_support_hierarchy":
                bool(
                    projection_support_hierarchy
                ),
        },

        "diagnosis":
            diagnosis,

        "audit_passed":
            bool(
                passed
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
        "  V15SG7E1_Threshold_Sensitivity.csv"
    )

    print(
        "  V15SG7E1_Raw_vs_Corrected.csv"
    )

    print(
        "  V15SG7E1_Covered_Uncovered_Inventory.csv"
    )

    print(
        "  V15SG7E1_Projection_vs_Support.csv"
    )

    print(
        "\nDatabase:"
    )

    print(
        "  V15SG7E1_Diagnostic_Database.npz"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7E1_Threshold_Sensitivity_100d.png"
    )

    print(
        "  V15SG7E1_Inventory_Coverage.png"
    )

    print(
        "  V15SG7E1_Projection_vs_Support_1000d.png"
    )

    print(
        "  V15SG7E1_Raw_vs_Corrected_100d.png"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7E1_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    if passed:

        print(
            "V15-SG7E-1 AUDIT: PASS"
        )

        print()

        print(
            "Diagnosis:"
        )

        print(
            f"  {diagnosis}"
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            f"  {next_milestone}"
        )

    else:

        print(
            "V15-SG7E-1 AUDIT: INCOMPLETE"
        )

        print()

        print(
            "Do not modify seed density or map-back "
            "until the diagnostic inconsistency is resolved."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()