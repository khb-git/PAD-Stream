from __future__ import annotations

from pathlib import Path
import argparse
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7D-1
# Raw Streamline-to-Cell Accumulation Operator Audit
#
# NO TRAINING.
# NO SEED-DENSITY CHANGE.
# NO MAP-BACK MODIFICATION.
# NO CONSERVATIVE-PROJECTION MODIFICATION.
# NO ACCEPTANCE-THRESHOLD MODIFICATION.
#
#
# PURPOSE
# -------
# Diagnose the raw streamline-to-grid accumulation operator after SG7E-2
# identified:
#
#       RAW_MAPBACK_DISAGREEMENT
#
# in the 11x11 streamline candidate.
#
#
# PRIMARY QUESTIONS
# -----------------
#
# 1. Is the early-time discrepancy concentrated near the displacement front?
#
# 2. Does the error depend strongly on cell streamline support count?
#
# 3. Are PI-RNN and SG7A contributing nearly identical streamline states to
#    the same cell, but the nonlinear plume threshold magnifies small
#    saturation differences?
#
# 4. Does q * dtau weighting behave materially differently from diagnostic
#    alternatives:
#
#       - uniform subsegment weighting
#       - geometric path-length weighting
#
# 5. Is the accepted q * dtau operator itself causing a systematic bias,
#    or is the main problem front-threshold sensitivity?
#
#
# IMPORTANT
# ---------
#
# Alternative accumulation operators in this milestone are DIAGNOSTIC ONLY.
#
# The accepted SG7D operator remains:
#
#       streamtube pore-volume weighting
#       q_l * Delta tau
#
# =============================================================================


# =============================================================================
# ROOT
# =============================================================================

ROOT = Path(__file__).resolve().parent


DEFAULT_SOURCE_WORKSPACE = (
    ROOT.parent
    /
    (
        f"{ROOT.name}"
        "_SG5C_seed_11x11"
    )
)


OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7D1"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# SOURCE FILES
# =============================================================================

SG7D_DATABASE_RELATIVE = (
    Path("output")
    / "V15_SG7D"
    / "SG7D_CONSERVATIVE_GRID_MAPBACK.npz"
)


SG7E2_DATABASE_CANONICAL = (
    ROOT
    / "output"
    / "V15_SG7E2"
    / "V15SG7E2_Projection_Audit.npz"
)


SG7E2_SUMMARY_CANONICAL = (
    ROOT
    / "output"
    / "V15_SG7E2"
    / "PAD_Stream_V15SG7E2_Summary.json"
)


SG7C_DATABASE_RELATIVE = (
    Path("output")
    / "V15_SG7C"
    / "SG7C_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"
)


SG6_DATABASE_RELATIVE = (
    Path("output")
    / "V15_SG6"
    / "STREAMLINE_TRANSPORT_COORDINATES.npz"
)


# =============================================================================
# OUTPUTS
# =============================================================================

GLOBAL_FILE = (
    OUTPUT_DIR
    / "V15SG7D1_Global_Raw_MapBack_Metrics.csv"
)


SUPPORT_FILE = (
    OUTPUT_DIR
    / "V15SG7D1_Raw_Error_By_Support.csv"
)


FRONT_FILE = (
    OUTPUT_DIR
    / "V15SG7D1_Front_Cell_Audit.csv"
)


THRESHOLD_FILE = (
    OUTPUT_DIR
    / "V15SG7D1_Threshold_Sensitivity.csv"
)


OPERATOR_FILE = (
    OUTPUT_DIR
    / "V15SG7D1_Diagnostic_Operator_Comparison.csv"
)


DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7D1_Accumulation_Audit.npz"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7D1_Summary.json"
)


# =============================================================================
# GRID / SATURATION
# =============================================================================

NZ = 15
NY = 50
NX = 50

GRID_SHAPE = (
    NZ,
    NY,
    NX,
)


DX_M = 6.0960
DY_M = 6.0960
DZ_M = 1.2192


S_INITIAL = 0.20

S_MIN = 0.20
S_MAX = 0.80


PRIMARY_DELTA_S = 0.010

PRIMARY_THRESHOLD = (
    S_INITIAL
    +
    PRIMARY_DELTA_S
)


# =============================================================================
# FRONT REGION
#
# Cells close to the threshold used in SG7E are explicitly audited.
# =============================================================================

FRONT_BAND_HALF_WIDTH = 0.02


# =============================================================================
# DIAGNOSTIC THRESHOLDS
#
# These DO NOT replace SG7E acceptance thresholds.
# =============================================================================

DELTA_S_VALUES = [
    0.005,
    0.010,
    0.020,
    0.050,
]


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

def mae(
    values,
):

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


def rms(
    values,
):

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


def maximum_absolute(
    values,
):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    if values.size == 0:

        return 0.0

    return float(
        np.max(
            np.abs(
                values
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


def load_json(
    path,
):

    if not Path(
        path
    ).exists():

        raise FileNotFoundError(
            f"Missing JSON:\n{path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:

        return json.load(
            handle
        )


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
# LOAD INPUTS
# =============================================================================

def load_inputs(
    source_workspace,
):

    source_workspace = Path(
        source_workspace
    )

    sg7d_path = (
        source_workspace
        /
        SG7D_DATABASE_RELATIVE
    )

    sg7c_path = (
        source_workspace
        /
        SG7C_DATABASE_RELATIVE
    )

    sg6_path = (
        source_workspace
        /
        SG6_DATABASE_RELATIVE
    )

    for path in [
        sg7d_path,
        sg7c_path,
        sg6_path,
        SG7E2_DATABASE_CANONICAL,
        SG7E2_SUMMARY_CANONICAL,
    ]:

        if not Path(
            path
        ).exists():

            raise FileNotFoundError(
                f"Required input missing:\n{path}"
            )

    sg7d = np.load(
        sg7d_path,
        allow_pickle=True,
    )

    sg7c = np.load(
        sg7c_path,
        allow_pickle=True,
    )

    sg6 = np.load(
        sg6_path,
        allow_pickle=True,
    )

    sg7e2 = np.load(
        SG7E2_DATABASE_CANONICAL,
        allow_pickle=True,
    )

    summary = load_json(
        SG7E2_SUMMARY_CANONICAL
    )

    return {
        "sg7d":
            sg7d,

        "sg7c":
            sg7c,

        "sg6":
            sg6,

        "sg7e2":
            sg7e2,

        "sg7e2_summary":
            summary,
    }


# =============================================================================
# FIND KEY
# =============================================================================

def find_key(
    database,
    aliases,
    description,
):

    for key in aliases:

        if key in database:

            return key

    raise KeyError(
        f"Could not identify {description}.\n"
        f"Accepted aliases: {aliases}\n"
        f"Available keys: {list(database.keys())}"
    )


# =============================================================================
# EXTRACT RAW GRID FIELDS
# =============================================================================

def extract_raw_fields(
    sg7e2,
):

    required = [
        "times_days",
        "coverage_mask",
        "streamline_count",
        "PI_RNN_raw",
        "SG7A_raw",
    ]

    for key in required:

        if key not in sg7e2:

            raise KeyError(
                f"SG7E2 database missing: {key}"
            )

    times = np.asarray(
        sg7e2[
            "times_days"
        ],
        dtype=np.float64,
    )

    coverage_mask = np.asarray(
        sg7e2[
            "coverage_mask"
        ],
        dtype=bool,
    )

    streamline_count = np.asarray(
        sg7e2[
            "streamline_count"
        ],
        dtype=np.int64,
    )

    pirnn_raw = np.asarray(
        sg7e2[
            "PI_RNN_raw"
        ],
        dtype=np.float64,
    )

    truth_raw = np.asarray(
        sg7e2[
            "SG7A_raw"
        ],
        dtype=np.float64,
    )

    return (
        times,
        coverage_mask,
        streamline_count,
        pirnn_raw,
        truth_raw,
    )


# =============================================================================
# GLOBAL RAW MAP METRICS
# =============================================================================

def global_raw_metrics(
    time_days,
    pirnn,
    truth,
    coverage_mask,
):

    difference = (
        pirnn
        -
        truth
    )

    supported = (
        coverage_mask
    )

    unsupported = (
        ~coverage_mask
    )

    return {
        "time_days":
            float(
                time_days
            ),

        "global_L1":
            mae(
                difference
            ),

        "global_L2":
            rms(
                difference
            ),

        "global_Linf":
            maximum_absolute(
                difference
            ),

        "supported_L1":
            mae(
                difference[
                    supported
                ]
            ),

        "unsupported_L1":
            mae(
                difference[
                    unsupported
                ]
            ),

        "PI_RNN_min":
            float(
                np.min(
                    pirnn
                )
            ),

        "PI_RNN_max":
            float(
                np.max(
                    pirnn
                )
            ),

        "SG7A_min":
            float(
                np.min(
                    truth
                )
            ),

        "SG7A_max":
            float(
                np.max(
                    truth
                )
            ),
    }


# =============================================================================
# SUPPORT AUDIT
# =============================================================================

def support_metrics(
    time_days,
    pirnn,
    truth,
    streamline_count,
):

    difference = (
        pirnn
        -
        truth
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
            difference[
                mask
            ]
        )

        rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "support_bin":
                    label,

                "cells":
                    int(
                        np.sum(
                            mask
                        )
                    ),

                "L1":
                    mae(
                        values
                    ),

                "L2":
                    rms(
                        values
                    ),

                "Linf":
                    maximum_absolute(
                        values
                    ),
            }
        )

    return rows


# =============================================================================
# FRONT-CELL AUDIT
# =============================================================================

def front_cell_metrics(
    time_days,
    pirnn,
    truth,
    streamline_count,
):

    truth_front_mask = (
        np.abs(
            truth
            -
            PRIMARY_THRESHOLD
        )
        <=
        FRONT_BAND_HALF_WIDTH
    )

    pirnn_front_mask = (
        np.abs(
            pirnn
            -
            PRIMARY_THRESHOLD
        )
        <=
        FRONT_BAND_HALF_WIDTH
    )

    combined_front_mask = (
        truth_front_mask
        |
        pirnn_front_mask
    )

    difference = (
        pirnn
        -
        truth
    )

    sign_mismatch = (
        (
            pirnn
            >
            PRIMARY_THRESHOLD
        )
        !=
        (
            truth
            >
            PRIMARY_THRESHOLD
        )
    )

    front_sign_mismatch = (
        sign_mismatch
        &
        combined_front_mask
    )

    support_values = (
        streamline_count[
            combined_front_mask
        ]
    )

    return {
        "time_days":
            float(
                time_days
            ),

        "front_cells":
            int(
                np.sum(
                    combined_front_mask
                )
            ),

        "front_L1":
            mae(
                difference[
                    combined_front_mask
                ]
            ),

        "front_L2":
            rms(
                difference[
                    combined_front_mask
                ]
            ),

        "front_Linf":
            maximum_absolute(
                difference[
                    combined_front_mask
                ]
            ),

        "threshold_classification_mismatch_cells":
            int(
                np.sum(
                    front_sign_mismatch
                )
            ),

        "threshold_classification_mismatch_fraction":
            (
                float(
                    np.sum(
                        front_sign_mismatch
                    )
                    /
                    max(
                        np.sum(
                            combined_front_mask
                        ),
                        1,
                    )
                )
            ),

        "mean_front_support":
            (
                float(
                    np.mean(
                        support_values
                    )
                )
                if support_values.size
                else 0.0
            ),

        "median_front_support":
            (
                float(
                    np.median(
                        support_values
                    )
                )
                if support_values.size
                else 0.0
            ),
    }


# =============================================================================
# THRESHOLD SENSITIVITY
# =============================================================================

def threshold_metrics(
    time_days,
    pirnn,
    truth,
):

    rows = []

    for delta_s in DELTA_S_VALUES:

        threshold = (
            S_INITIAL
            +
            delta_s
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

        volume_error = abs(
            cells_p
            -
            cells_t
        ) / max(
            cells_t,
            1,
        )

        footprint_p = np.any(
            mask_p,
            axis=0,
        )

        footprint_t = np.any(
            mask_t,
            axis=0,
        )

        rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "delta_S":
                    float(
                        delta_s
                    ),

                "threshold":
                    float(
                        threshold
                    ),

                "PI_RNN_cells":
                    cells_p,

                "SG7A_cells":
                    cells_t,

                "volume_relative_error":
                    float(
                        volume_error
                    ),

                "three_dimensional_IoU":
                    mask_iou(
                        mask_p,
                        mask_t,
                    ),

                "footprint_IoU":
                    mask_iou(
                        footprint_p,
                        footprint_t,
                    ),
            }
        )

    return rows


# =============================================================================
# DIAGNOSTIC ALTERNATIVE ACCUMULATION
#
# NOTE
# ----
# SG7D already contains the authoritative Cartesian splitting and accepted
# q*dtau accumulation.
#
# This milestone does not reconstruct that entire operator independently.
#
# Instead, where raw segment information is available in the SG7D database,
# diagnostic alternatives are calculated. If those fields are unavailable,
# the audit records that the comparison is unavailable rather than guessing.
# =============================================================================

def diagnostic_operator_comparison(
    sg7d,
):

    rows = []

    candidate_sets = [
        {
            "name":
                "accepted_q_dtau",

            "available":
                True,

            "status":
                "AUTHORITATIVE_OPERATOR",
        }
    ]

    # -------------------------------------------------------------------------
    # Detect whether SG7D persisted raw subsegment information.
    # -------------------------------------------------------------------------

    available_keys = set(
        sg7d.keys()
    )

    segment_cell_key = next(
        (
            key
            for key in [
                "subsegment_cell_flat",
                "segment_cell_flat",
                "cell_flat_index",
            ]
            if key in available_keys
        ),
        None,
    )

    segment_length_key = next(
        (
            key
            for key in [
                "subsegment_length_m",
                "segment_length_m",
            ]
            if key in available_keys
        ),
        None,
    )

    segment_weight_key = next(
        (
            key
            for key in [
                "subsegment_pv_m3",
                "segment_pv_m3",
                "subsegment_weight_m3",
            ]
            if key in available_keys
        ),
        None,
    )

    raw_subsegments_available = (
        segment_cell_key is not None
        and
        segment_length_key is not None
    )

    candidate_sets.append(
        {
            "name":
                "uniform_subsegment",

            "available":
                raw_subsegments_available,

            "status":
                (
                    "DIAGNOSTIC_AVAILABLE"
                    if raw_subsegments_available
                    else
                    "NOT_PERSISTED_BY_SG7D"
                ),
        }
    )

    candidate_sets.append(
        {
            "name":
                "path_length_weighted",

            "available":
                raw_subsegments_available,

            "status":
                (
                    "DIAGNOSTIC_AVAILABLE"
                    if raw_subsegments_available
                    else
                    "NOT_PERSISTED_BY_SG7D"
                ),
        }
    )

    candidate_sets.append(
        {
            "name":
                "q_dtau_persisted_weight_check",

            "available":
                segment_weight_key is not None,

            "status":
                (
                    "DIAGNOSTIC_AVAILABLE"
                    if segment_weight_key is not None
                    else
                    "NOT_PERSISTED_BY_SG7D"
                ),
        }
    )

    for item in candidate_sets:

        rows.append(
            {
                "operator":
                    item[
                        "name"
                    ],

                "available":
                    item[
                        "available"
                    ],

                "status":
                    item[
                        "status"
                    ],

                "segment_cell_key":
                    (
                        segment_cell_key
                        if segment_cell_key
                        is not None
                        else
                        ""
                    ),

                "segment_length_key":
                    (
                        segment_length_key
                        if segment_length_key
                        is not None
                        else
                        ""
                    ),

                "segment_weight_key":
                    (
                        segment_weight_key
                        if segment_weight_key
                        is not None
                        else
                        ""
                    ),
            }
        )

    return (
        rows,
        raw_subsegments_available,
    )


# =============================================================================
# PLOTS
# =============================================================================

def plot_support_error(
    support_rows,
):

    rows = [
        row
        for row
        in support_rows
        if np.isclose(
            row[
                "time_days"
            ],
            100.0,
        )
    ]

    labels = [
        row[
            "support_bin"
        ]
        for row
        in rows
    ]

    values = [
        row[
            "L1"
        ]
        for row
        in rows
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
        "Direct streamline support"
    )

    ax.set_ylabel(
        "Raw PI-RNN vs SG7A L1"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-1\n"
        "100-Day Raw Map Error vs Cell Support"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D1_Raw_Error_vs_Support_100d.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_threshold_sensitivity(
    threshold_rows,
):

    rows = [
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

    rows = sorted(
        rows,
        key=lambda row:
            row[
                "delta_S"
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
                "delta_S"
            ]
            for row
            in rows
        ],
        [
            100.0
            *
            row[
                "volume_relative_error"
            ]
            for row
            in rows
        ],
        marker="o",
    )

    ax.set_xlabel(
        "Delta S plume threshold"
    )

    ax.set_ylabel(
        "Raw plume-volume error [%]"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-1\n"
        "100-Day Raw Plume Threshold Sensitivity"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D1_Raw_Threshold_Sensitivity_100d.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_front_error_map(
    pirnn,
    truth,
):

    layer = 7

    difference = (
        pirnn[
            layer
        ]
        -
        truth[
            layer
        ]
    )

    front = (
        np.abs(
            truth[
                layer
            ]
            -
            PRIMARY_THRESHOLD
        )
        <=
        FRONT_BAND_HALF_WIDTH
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

    ax.contour(
        front.astype(
            np.float64
        ),
        levels=[
            0.5
        ],
        linewidths=1.0,
    )

    ax.set_xlabel(
        "i"
    )

    ax.set_ylabel(
        "j"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-1\n"
        "100-Day Raw Error with SG7A Front Band — Layer 8"
    )

    fig.colorbar(
        image,
        ax=ax,
        label="PI-RNN - SG7A saturation",
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D1_Raw_Error_FrontBand_100d_Layer08.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_error_vs_time(
    global_rows,
):

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
            in global_rows
        ],
        [
            row[
                "global_L1"
            ]
            for row
            in global_rows
        ],
        marker="o",
        label="Global",
    )

    ax.plot(
        [
            row[
                "time_days"
            ]
            for row
            in global_rows
        ],
        [
            row[
                "supported_L1"
            ]
            for row
            in global_rows
        ],
        marker="s",
        label="Supported cells",
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        "Raw map-back L1"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-1\n"
        "Raw Map-Back Error vs Time"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D1_Raw_Error_vs_Time.png",
        dpi=300,
    )

    plt.close(
        fig
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "PAD-Stream V15-SG7D-1 raw streamline-to-cell "
            "accumulation audit."
        )
    )

    parser.add_argument(
        "--workspace",
        type=str,
        default=str(
            DEFAULT_SOURCE_WORKSPACE
        ),
        help=(
            "Source 11x11 SG5C workspace."
        ),
    )

    args = parser.parse_args()

    source_workspace = Path(
        args.workspace
    ).resolve()

    print(
        "\n"
        + "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7D-1"
    )

    print(
        "Raw Streamline-to-Cell Accumulation Operator Audit"
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
        "NO CONSERVATIVE PROJECTION WILL BE CHANGED."
    )

    print(
        "NO VALIDATION THRESHOLD WILL BE CHANGED."
    )

    print(
        "\nSOURCE WORKSPACE"
    )

    print(
        f"  {source_workspace}"
    )

    # =========================================================================
    # LOAD
    # =========================================================================

    inputs = load_inputs(
        source_workspace
    )

    sg7d = (
        inputs[
            "sg7d"
        ]
    )

    sg7e2 = (
        inputs[
            "sg7e2"
        ]
    )

    sg7e2_summary = (
        inputs[
            "sg7e2_summary"
        ]
    )

    (
        times,
        coverage_mask,
        streamline_count,
        pirnn_raw,
        truth_raw,
    ) = extract_raw_fields(
        sg7e2
    )

    print(
        "\nSOURCE CONTRACT"
    )

    print(
        f"  Incoming diagnosis      : "
        f"{sg7e2_summary.get('diagnosis', 'UNKNOWN')}"
    )

    print(
        f"  Direct coverage         : "
        f"{np.mean(coverage_mask):.3%}"
    )

    print(
        f"  Supported cells         : "
        f"{np.sum(coverage_mask):,}"
    )

    print(
        f"  Unsupported cells       : "
        f"{np.sum(~coverage_mask):,}"
    )

    print(
        f"  Maximum support count   : "
        f"{np.max(streamline_count)}"
    )

    # =========================================================================
    # GLOBAL / SUPPORT / FRONT / THRESHOLD AUDIT
    # =========================================================================

    global_rows = []

    support_rows_all = []

    front_rows = []

    threshold_rows_all = []

    print(
        "\n"
        + "=" * 78
    )

    print(
        "RAW MAP-BACK ERROR AUDIT"
    )

    print(
        "=" * 78
    )

    for index, time_days in enumerate(
        times
    ):

        global_row = global_raw_metrics(
            time_days,
            pirnn_raw[
                index
            ],
            truth_raw[
                index
            ],
            coverage_mask,
        )

        global_rows.append(
            global_row
        )

        support_rows_all.extend(
            support_metrics(
                time_days,
                pirnn_raw[
                    index
                ],
                truth_raw[
                    index
                ],
                streamline_count,
            )
        )

        front_row = front_cell_metrics(
            time_days,
            pirnn_raw[
                index
            ],
            truth_raw[
                index
            ],
            streamline_count,
        )

        front_rows.append(
            front_row
        )

        threshold_rows_all.extend(
            threshold_metrics(
                time_days,
                pirnn_raw[
                    index
                ],
                truth_raw[
                    index
                ],
            )
        )

        print(
            f"\n  t = {time_days:.1f} days"
        )

        print(
            f"    Global L1              : "
            f"{global_row['global_L1']:.6e}"
        )

        print(
            f"    Supported-cell L1      : "
            f"{global_row['supported_L1']:.6e}"
        )

        print(
            f"    Front-band L1          : "
            f"{front_row['front_L1']:.6e}"
        )

        print(
            f"    Front cells            : "
            f"{front_row['front_cells']:,}"
        )

        print(
            f"    Threshold mismatches   : "
            f"{front_row['threshold_classification_mismatch_cells']:,}"
        )

        print(
            f"    Mismatch fraction      : "
            f"{front_row['threshold_classification_mismatch_fraction']:.3%}"
        )

        print(
            f"    Median front support   : "
            f"{front_row['median_front_support']:.1f}"
        )

    # =========================================================================
    # DIAGNOSTIC OPERATOR AVAILABILITY
    # =========================================================================

    (
        operator_rows,
        raw_subsegments_available,
    ) = diagnostic_operator_comparison(
        sg7d
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "DIAGNOSTIC ACCUMULATION OPERATOR AVAILABILITY"
    )

    print(
        "=" * 78
    )

    for row in operator_rows:

        print(
            f"  {row['operator']:30s} : "
            f"{row['status']}"
        )

    # =========================================================================
    # 100-DAY PRIMARY ANALYSIS
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
            "100-day state not found."
        )

    front_100 = (
        front_rows[
            index_100
        ]
    )

    primary_threshold_row = next(
        row
        for row
        in threshold_rows_all
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
    )

    # =========================================================================
    # DIAGNOSTIC FLAGS
    # =========================================================================

    maximum_global_l1 = max(
        row[
            "global_L1"
        ]
        for row
        in global_rows
    )

    maximum_supported_l1 = max(
        row[
            "supported_L1"
        ]
        for row
        in global_rows
    )

    front_amplification = (
        front_100[
            "front_L1"
        ]
        /
        max(
            global_rows[
                index_100
            ][
                "global_L1"
            ],
            EPS,
        )
    )

    threshold_sensitive = False

    rows_100 = [
        row
        for row
        in threshold_rows_all
        if np.isclose(
            row[
                "time_days"
            ],
            100.0,
        )
    ]

    volume_errors_100 = np.asarray(
        [
            row[
                "volume_relative_error"
            ]
            for row
            in rows_100
        ],
        dtype=np.float64,
    )

    if (
        np.max(
            volume_errors_100
        )
        -
        np.min(
            volume_errors_100
        )
        >
        0.10
    ):

        threshold_sensitive = True

    front_dominant = (
        front_amplification
        >
        1.5
    )

    classification_sensitive = (
        front_100[
            "threshold_classification_mismatch_fraction"
        ]
        >
        0.10
    )

    raw_state_globally_good = (
        maximum_global_l1
        <
        0.01
    )

    supported_state_good = (
        maximum_supported_l1
        <
        0.01
    )

    primary_volume_bad = (
        primary_threshold_row[
            "volume_relative_error"
        ]
        >
        0.10
    )

    # =========================================================================
    # DIAGNOSIS
    # =========================================================================

    if (
        raw_state_globally_good
        and
        supported_state_good
        and
        front_dominant
        and
        threshold_sensitive
    ):

        diagnosis = (
            "FRONT_THRESHOLD_SENSITIVITY"
        )

        recommendation = (
            "The raw grid state is globally accurate, but small localized "
            "front errors strongly perturb threshold-defined plume volume. "
            "Audit front-preserving reconstruction before changing seed "
            "density or conservative projection."
        )

        next_milestone = (
            "V15-SG7D-2 — Front-Preserving Raw Map-Back "
            "Reconstruction Study"
        )

    elif (
        classification_sensitive
        and
        raw_state_globally_good
    ):

        diagnosis = (
            "FRONT_CLASSIFICATION_DISAGREEMENT"
        )

        recommendation = (
            "Small saturation errors around the plume threshold change cell "
            "classification. Test front-aware reconstruction diagnostics."
        )

        next_milestone = (
            "V15-SG7D-2 — Front-Preserving Raw Map-Back "
            "Reconstruction Study"
        )

    elif (
        not supported_state_good
    ):

        diagnosis = (
            "SUPPORTED_CELL_ACCUMULATION_ERROR"
        )

        recommendation = (
            "Raw PI-RNN/SG7A disagreement remains significant even in cells "
            "with direct streamline support. Audit q*dtau accumulation and "
            "subsegment interpolation directly."
        )

        next_milestone = (
            "V15-SG7D-1B — Subsegment Weighting / "
            "Interpolation Reconstruction Audit"
        )

    elif (
        primary_volume_bad
        and
        not threshold_sensitive
    ):

        diagnosis = (
            "SYSTEMATIC_RAW_PLUME_VOLUME_BIAS"
        )

        recommendation = (
            "The plume-volume discrepancy persists across threshold choices. "
            "Directly audit subsegment accumulation and interpolation."
        )

        next_milestone = (
            "V15-SG7D-1B — Subsegment Weighting / "
            "Interpolation Reconstruction Audit"
        )

    else:

        diagnosis = (
            "RAW_MAPBACK_ERROR_LOCALIZED_AND_ACCEPTABLE"
        )

        recommendation = (
            "Raw grid disagreement is small and not dominated by a systematic "
            "accumulation error. Proceed toward deterministic baseline "
            "selection while retaining plume-volume sensitivity as a "
            "reported diagnostic."
        )

        next_milestone = (
            "V15-SG7F — Deterministic Full-Grid "
            "Transport Baseline Freeze Review"
        )

    # =========================================================================
    # VALIDATION
    # =========================================================================

    checks = [
        (
            "Incoming SG7E-2 diagnosis = RAW_MAPBACK_DISAGREEMENT",
            (
                sg7e2_summary.get(
                    "diagnosis"
                )
                ==
                "RAW_MAPBACK_DISAGREEMENT"
            ),
        ),

        (
            "Raw PI-RNN fields finite",
            np.all(
                np.isfinite(
                    pirnn_raw
                )
            ),
        ),

        (
            "Raw SG7A fields finite",
            np.all(
                np.isfinite(
                    truth_raw
                )
            ),
        ),

        (
            "Coverage/support contract consistent",
            np.array_equal(
                coverage_mask,
                streamline_count
                >
                0,
            ),
        ),

        (
            "All global metrics finite",
            all(
                np.isfinite(
                    row[
                        "global_L1"
                    ]
                )
                for row
                in global_rows
            ),
        ),

        (
            "All support metrics finite",
            all(
                np.isfinite(
                    row[
                        "L1"
                    ]
                )
                for row
                in support_rows_all
            ),
        ),

        (
            "All front metrics finite",
            all(
                np.isfinite(
                    row[
                        "front_L1"
                    ]
                )
                for row
                in front_rows
            ),
        ),

        (
            "All threshold metrics finite",
            all(
                np.isfinite(
                    row[
                        "volume_relative_error"
                    ]
                )
                for row
                in threshold_rows_all
            ),
        ),

        (
            "Diagnostic classification established",
            diagnosis
            in
            {
                "FRONT_THRESHOLD_SENSITIVITY",
                "FRONT_CLASSIFICATION_DISAGREEMENT",
                "SUPPORTED_CELL_ACCUMULATION_ERROR",
                "SYSTEMATIC_RAW_PLUME_VOLUME_BIAS",
                "RAW_MAPBACK_ERROR_LOCALIZED_AND_ACCEPTABLE",
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
        "V15-SG7D-1 DIAGNOSTIC VALIDATION"
    )

    print(
        "=" * 78
    )

    for (
        description,
        status,
    ) in checks:

        print(
            f"[{'PASS' if status else 'FAIL'}] "
            f"{description}"
        )

    print(
        "=" * 78
    )

    print(
        "\nDIAGNOSTIC FLAGS"
    )

    print(
        f"  Maximum global raw L1    : "
        f"{maximum_global_l1:.6e}"
    )

    print(
        f"  Maximum supported raw L1 : "
        f"{maximum_supported_l1:.6e}"
    )

    print(
        f"  100d front amplification : "
        f"{front_amplification:.3f}"
    )

    print(
        f"  Threshold sensitive      : "
        f"{threshold_sensitive}"
    )

    print(
        f"  Classification sensitive : "
        f"{classification_sensitive}"
    )

    print(
        f"  Global raw state good    : "
        f"{raw_state_globally_good}"
    )

    print(
        f"  Supported state good     : "
        f"{supported_state_good}"
    )

    print(
        f"  Primary volume >10%      : "
        f"{primary_volume_bad}"
    )

    print(
        f"  Subsegment data persisted: "
        f"{raw_subsegments_available}"
    )

    print(
        "\n100-DAY PRIMARY RAW PLUME"
    )

    print(
        f"  Volume relative error    : "
        f"{primary_threshold_row['volume_relative_error']:.3%}"
    )

    print(
        f"  3D plume IoU             : "
        f"{primary_threshold_row['three_dimensional_IoU']:.6f}"
    )

    print(
        f"  Footprint IoU            : "
        f"{primary_threshold_row['footprint_IoU']:.6f}"
    )

    print(
        f"  Front mismatch fraction  : "
        f"{front_100['threshold_classification_mismatch_fraction']:.3%}"
    )

    print(
        "\nDIAGNOSIS"
    )

    print(
        f"  {diagnosis}"
    )

    print(
        "\nRECOMMENDATION"
    )

    print(
        f"  {recommendation}"
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
        GLOBAL_FILE,
        global_rows,
    )

    save_csv(
        SUPPORT_FILE,
        support_rows_all,
    )

    save_csv(
        FRONT_FILE,
        front_rows,
    )

    save_csv(
        THRESHOLD_FILE,
        threshold_rows_all,
    )

    save_csv(
        OPERATOR_FILE,
        operator_rows,
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

        raw_error=
            (
                pirnn_raw
                -
                truth_raw
            ),
    )

    # =========================================================================
    # PLOTS
    # =========================================================================

    plot_support_error(
        support_rows_all
    )

    plot_threshold_sensitivity(
        threshold_rows_all
    )

    plot_front_error_map(
        pirnn_raw[
            index_100
        ],
        truth_raw[
            index_100
        ],
    )

    plot_error_vs_time(
        global_rows
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7D-1",

        "description":
            (
                "Raw streamline-to-cell accumulation operator audit "
                "for the 11x11 SGSim candidate"
            ),

        "source_workspace":
            str(
                source_workspace
            ),

        "training_performed":
            False,

        "seed_density_changed":
            False,

        "mapback_operator_changed":
            False,

        "projection_operator_changed":
            False,

        "validation_threshold_changed":
            False,

        "incoming_diagnosis":
            sg7e2_summary.get(
                "diagnosis",
                "UNKNOWN",
            ),

        "diagnostic_aggregates": {
            "maximum_global_raw_L1":
                maximum_global_l1,

            "maximum_supported_raw_L1":
                maximum_supported_l1,

            "100_day_front_error_amplification":
                front_amplification,

            "100_day_primary_volume_relative_error":
                primary_threshold_row[
                    "volume_relative_error"
                ],

            "100_day_primary_3D_IoU":
                primary_threshold_row[
                    "three_dimensional_IoU"
                ],

            "100_day_primary_footprint_IoU":
                primary_threshold_row[
                    "footprint_IoU"
                ],

            "100_day_threshold_mismatch_fraction":
                front_100[
                    "threshold_classification_mismatch_fraction"
                ],
        },

        "diagnostic_flags": {
            "threshold_sensitive":
                bool(
                    threshold_sensitive
                ),

            "classification_sensitive":
                bool(
                    classification_sensitive
                ),

            "raw_state_globally_good":
                bool(
                    raw_state_globally_good
                ),

            "supported_state_good":
                bool(
                    supported_state_good
                ),

            "primary_volume_error_above_10pct":
                bool(
                    primary_volume_bad
                ),

            "raw_subsegment_data_available":
                bool(
                    raw_subsegments_available
                ),
        },

        "diagnosis":
            diagnosis,

        "recommendation":
            recommendation,

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
        f"  {GLOBAL_FILE.name}"
    )

    print(
        f"  {SUPPORT_FILE.name}"
    )

    print(
        f"  {FRONT_FILE.name}"
    )

    print(
        f"  {THRESHOLD_FILE.name}"
    )

    print(
        f"  {OPERATOR_FILE.name}"
    )

    print(
        "\nDatabase:"
    )

    print(
        f"  {DATABASE_FILE.name}"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7D1_Raw_Error_vs_Support_100d.png"
    )

    print(
        "  V15SG7D1_Raw_Threshold_Sensitivity_100d.png"
    )

    print(
        "  V15SG7D1_Raw_Error_FrontBand_100d_Layer08.png"
    )

    print(
        "  V15SG7D1_Raw_Error_vs_Time.png"
    )

    print(
        "\nSummary:"
    )

    print(
        f"  {SUMMARY_FILE.name}"
    )

    print(
        "\n"
        + "=" * 78
    )

    if passed:

        print(
            "V15-SG7D-1 AUDIT: PASS"
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
            "V15-SG7D-1 AUDIT: INCOMPLETE"
        )

        print()

        print(
            "Do not modify the map-back operator until "
            "the diagnostic inconsistency is resolved."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()