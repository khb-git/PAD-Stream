from __future__ import annotations

from pathlib import Path
from collections import deque
import argparse
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7E-2
# Raw Map-Back / Projection Dependence Audit
#
# PURPOSE
# -------
#
# Diagnose WHY the high-resolution 11x11 SGSim streamline reconstruction
# remains dependent on the global conservative inventory projection even
# though direct streamline support has become substantially stronger.
#
#
# CURRENT DEVELOPMENT CONTEXT
# ---------------------------
#
# V15-SG5C seed-density study:
#
#     5x5   ->  550 streamlines
#     7x7   -> 1078 streamlines
#     9x9   -> 1782 streamlines
#    11x11  -> 2662 streamlines
#
#
# 11x11 candidate:
#
#     direct cell coverage      ~ 77.619 %
#     minimum covered inventory ~ 80.932 %
#
# SG7E-1 diagnosis:
#
#     PROJECTION_DEPENDENCE
#
#
# THIS MILESTONE CHANGES NOTHING.
#
# NO TRAINING.
# NO SEED-DENSITY CHANGE.
# NO MAP-BACK CHANGE.
# NO CONSERVATIVE-PROJECTION CHANGE.
# NO PLUME-THRESHOLD CHANGE.
#
#
# QUESTIONS
# ---------
#
# 1. Is the remaining PI-RNN / SG7A disagreement already present in the
#    pre-projection map-back field?
#
# 2. How much of the final state change is introduced by the global
#    conservative projection?
#
# 3. Is projection correction concentrated in:
#
#       - N = 0 unsupported cells?
#       - low-support cells?
#       - particular vertical layers?
#       - cells far from direct streamline support?
#
# 4. At the sensitive 100-day state, is plume-volume disagreement caused by
#    the raw map-back or by the conservative projection?
#
# 5. Has seed density reached the point where further refinement is unlikely
#    to address the dominant remaining error mechanism?
#
#
# POSSIBLE DIAGNOSES
# ------------------
#
#     UNSUPPORTED_CELL_PROJECTION_DOMINANT
#
#     RAW_MAPBACK_DISAGREEMENT
#
#     PROJECTION_AMPLIFICATION
#
#     SUPPORTED_REGION_PROJECTION_ERROR
#
#     MIXED_MAPBACK_PROJECTION_LIMITATION
#
#     PROJECTION_DEPENDENCE_ACCEPTABLE
#
# =============================================================================


# =============================================================================
# ROOT / DEFAULT SOURCE WORKSPACE
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
    / "V15_SG7E2"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# SOURCE FILES RELATIVE TO 11x11 WORKSPACE
# =============================================================================

SG7E1_DATABASE_RELATIVE = (
    Path("output")
    / "V15_SG7E1"
    / "V15SG7E1_Diagnostic_Database.npz"
)


SG7E1_SUMMARY_RELATIVE = (
    Path("output")
    / "V15_SG7E1"
    / "PAD_Stream_V15SG7E1_Summary.json"
)


SG7E_SUMMARY_RELATIVE = (
    Path("output")
    / "V15_SG7E"
    / "PAD_Stream_V15SG7E_Summary.json"
)


SG7D_SUMMARY_RELATIVE = (
    Path("output")
    / "V15_SG7D"
    / "PAD_Stream_V15SG7D_Summary.json"
)


# =============================================================================
# OUTPUTS
# =============================================================================

GLOBAL_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7E2_Global_Projection_Metrics.csv"
)


SUPPORT_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7E2_Projection_By_Support.csv"
)


LAYER_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7E2_Projection_By_Layer.csv"
)


DISTANCE_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7E2_Projection_By_Support_Distance.csv"
)


PLUME_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7E2_100d_Plume_Decomposition.csv"
)


DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7E2_Projection_Audit.npz"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7E2_Summary.json"
)


# =============================================================================
# GRID / SATURATION CONTRACT
# =============================================================================

NZ = 15
NY = 50
NX = 50

GRID_SHAPE = (
    NZ,
    NY,
    NX,
)


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
# DIAGNOSTIC REFERENCES
#
# These are NOT new freeze gates.
#
# They are only used to classify where the remaining projection correction
# resides.
# =============================================================================

SUPPORTED_COUNT_THRESHOLD = 1

HIGH_SUPPORT_THRESHOLD = 16


# If at least this fraction of total projection L1 is carried by N=0 cells,
# projection dependence is primarily an unsupported-cell issue.
UNSUPPORTED_PROJECTION_SHARE_REFERENCE = 0.70


# Raw state agreement reference retained from previous PAD-Stream validation.
RAW_STATE_L1_REFERENCE = 0.020


# Projection amplification ratio:
#
#     final PI-RNN-vs-SG7A L1
#     ------------------------
#     raw PI-RNN-vs-SG7A L1
#
# A value materially greater than one means the projection worsens the
# surrogate/reference discrepancy.
PROJECTION_AMPLIFICATION_REFERENCE = 1.25


EPS = 1.0e-14


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


# =============================================================================
# SUPPORT-DISTANCE BINS
#
# Distance is measured in Cartesian cell-neighbor steps from direct streamline
# support.
#
# 0 = directly supported.
# =============================================================================

DISTANCE_BINS = [
    (
        "d=0",
        0,
        0,
    ),

    (
        "d=1",
        1,
        1,
    ),

    (
        "d=2",
        2,
        2,
    ),

    (
        "d=3",
        3,
        3,
    ),

    (
        "d=4-5",
        4,
        5,
    ),

    (
        "d=6-10",
        6,
        10,
    ),

    (
        "d>10",
        11,
        None,
    ),
]


# =============================================================================
# BASIC HELPERS
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
    path: Path,
    rows: list[dict],
):

    if not rows:

        return

    with path.open(
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
    path: Path,
):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing JSON:\n{path}"
        )

    with path.open(
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


def relative_volume_error(
    prediction_mask,
    truth_mask,
):

    n_prediction = int(
        np.sum(
            prediction_mask
        )
    )

    n_truth = int(
        np.sum(
            truth_mask
        )
    )

    return abs(
        n_prediction
        -
        n_truth
    ) / max(
        n_truth,
        1,
    )


# =============================================================================
# LOAD SOURCE
# =============================================================================

def load_source(
    source_workspace: Path,
):

    database_path = (
        source_workspace
        /
        SG7E1_DATABASE_RELATIVE
    )

    summary_path = (
        source_workspace
        /
        SG7E1_SUMMARY_RELATIVE
    )

    sg7e_summary_path = (
        source_workspace
        /
        SG7E_SUMMARY_RELATIVE
    )

    sg7d_summary_path = (
        source_workspace
        /
        SG7D_SUMMARY_RELATIVE
    )

    if not database_path.exists():

        raise FileNotFoundError(
            "Missing SG7E-1 diagnostic database:\n"
            f"{database_path}"
        )

    db = np.load(
        database_path,
        allow_pickle=True,
    )

    required = [
        "times_days",
        "coverage_mask",
        "streamline_count",
        "PI_RNN_raw",
        "SG7A_raw",
        "PI_RNN_corrected",
        "SG7A_corrected",
    ]

    missing = [
        key
        for key
        in required
        if key not in db
    ]

    if missing:

        raise KeyError(
            "SG7E-1 database missing required field(s):\n"
            +
            "\n".join(
                f"  {key}"
                for key
                in missing
            )
        )

    times = np.asarray(
        db[
            "times_days"
        ],
        dtype=np.float64,
    )

    coverage_mask = np.asarray(
        db[
            "coverage_mask"
        ],
        dtype=bool,
    )

    streamline_count = np.asarray(
        db[
            "streamline_count"
        ],
        dtype=np.int64,
    )

    pirnn_raw = np.asarray(
        db[
            "PI_RNN_raw"
        ],
        dtype=np.float64,
    )

    truth_raw = np.asarray(
        db[
            "SG7A_raw"
        ],
        dtype=np.float64,
    )

    pirnn_corrected = np.asarray(
        db[
            "PI_RNN_corrected"
        ],
        dtype=np.float64,
    )

    truth_corrected = np.asarray(
        db[
            "SG7A_corrected"
        ],
        dtype=np.float64,
    )

    if coverage_mask.shape != GRID_SHAPE:

        raise RuntimeError(
            "Coverage-mask shape mismatch.\n"
            f"Expected: {GRID_SHAPE}\n"
            f"Observed: {coverage_mask.shape}"
        )

    if streamline_count.shape != GRID_SHAPE:

        raise RuntimeError(
            "Streamline-count shape mismatch."
        )

    expected_field_shape = (
        len(
            times
        ),
        NZ,
        NY,
        NX,
    )

    for (
        name,
        field,
    ) in [
        (
            "PI_RNN_raw",
            pirnn_raw,
        ),

        (
            "SG7A_raw",
            truth_raw,
        ),

        (
            "PI_RNN_corrected",
            pirnn_corrected,
        ),

        (
            "SG7A_corrected",
            truth_corrected,
        ),
    ]:

        if field.shape != expected_field_shape:

            raise RuntimeError(
                f"{name} shape mismatch.\n"
                f"Expected: {expected_field_shape}\n"
                f"Observed: {field.shape}"
            )

    return {
        "times":
            times,

        "coverage_mask":
            coverage_mask,

        "streamline_count":
            streamline_count,

        "pirnn_raw":
            pirnn_raw,

        "truth_raw":
            truth_raw,

        "pirnn_corrected":
            pirnn_corrected,

        "truth_corrected":
            truth_corrected,

        "sg7e1_summary":
            load_json(
                summary_path
            ),

        "sg7e_summary":
            load_json(
                sg7e_summary_path
            ),

        "sg7d_summary":
            load_json(
                sg7d_summary_path
            ),
    }


# =============================================================================
# CARTESIAN DISTANCE TO DIRECT STREAMLINE SUPPORT
#
# Pure-Python / NumPy breadth-first search.
#
# No SciPy dependency is required.
#
# 6-connected Cartesian neighborhood:
#
#       +/- x
#       +/- y
#       +/- z
#
# =============================================================================

def support_distance_map(
    coverage_mask,
):

    shape = (
        coverage_mask.shape
    )

    distance = np.full(
        shape,
        fill_value=-1,
        dtype=np.int32,
    )

    queue = deque()

    supported_indices = np.argwhere(
        coverage_mask
    )

    for (
        k,
        j,
        i,
    ) in supported_indices:

        distance[
            k,
            j,
            i
        ] = 0

        queue.append(
            (
                int(
                    k
                ),
                int(
                    j
                ),
                int(
                    i
                ),
            )
        )

    neighbors = [
        (
            -1,
            0,
            0,
        ),

        (
            1,
            0,
            0,
        ),

        (
            0,
            -1,
            0,
        ),

        (
            0,
            1,
            0,
        ),

        (
            0,
            0,
            -1,
        ),

        (
            0,
            0,
            1,
        ),
    ]

    while queue:

        (
            k,
            j,
            i,
        ) = queue.popleft()

        next_distance = (
            distance[
                k,
                j,
                i
            ]
            +
            1
        )

        for (
            dk,
            dj,
            di,
        ) in neighbors:

            nk = (
                k
                +
                dk
            )

            nj = (
                j
                +
                dj
            )

            ni = (
                i
                +
                di
            )

            if not (
                0
                <=
                nk
                <
                shape[0]
            ):

                continue

            if not (
                0
                <=
                nj
                <
                shape[1]
            ):

                continue

            if not (
                0
                <=
                ni
                <
                shape[2]
            ):

                continue

            if (
                distance[
                    nk,
                    nj,
                    ni
                ]
                >=
                0
            ):

                continue

            distance[
                nk,
                nj,
                ni
            ] = (
                next_distance
            )

            queue.append(
                (
                    nk,
                    nj,
                    ni,
                )
            )

    if np.any(
        distance
        <
        0
    ):

        raise RuntimeError(
            "Support-distance map contains unreachable cells."
        )

    return distance


# =============================================================================
# GLOBAL TIME-DEPENDENT DECOMPOSITION
# =============================================================================

def global_metrics_for_time(
    time_days,
    pirnn_raw,
    truth_raw,
    pirnn_corrected,
    truth_corrected,
    coverage_mask,
):

    raw_difference = (
        pirnn_raw
        -
        truth_raw
    )

    corrected_difference = (
        pirnn_corrected
        -
        truth_corrected
    )

    pirnn_projection = (
        pirnn_corrected
        -
        pirnn_raw
    )

    truth_projection = (
        truth_corrected
        -
        truth_raw
    )

    projection_difference = (
        pirnn_projection
        -
        truth_projection
    )

    raw_l1 = mae(
        raw_difference
    )

    corrected_l1 = mae(
        corrected_difference
    )

    amplification_ratio = (
        corrected_l1
        /
        max(
            raw_l1,
            EPS,
        )
    )

    unsupported = (
        ~coverage_mask
    )

    supported = (
        coverage_mask
    )

    pirnn_projection_absolute = np.abs(
        pirnn_projection
    )

    total_projection_l1_sum = float(
        np.sum(
            pirnn_projection_absolute
        )
    )

    unsupported_projection_l1_sum = float(
        np.sum(
            pirnn_projection_absolute[
                unsupported
            ]
        )
    )

    unsupported_projection_share = (
        unsupported_projection_l1_sum
        /
        max(
            total_projection_l1_sum,
            EPS,
        )
    )

    return {
        "time_days":
            float(
                time_days
            ),

        "raw_PI_RNN_vs_SG7A_L1":
            raw_l1,

        "raw_PI_RNN_vs_SG7A_L2":
            rms(
                raw_difference
            ),

        "raw_PI_RNN_vs_SG7A_Linf":
            maximum_absolute(
                raw_difference
            ),

        "corrected_PI_RNN_vs_SG7A_L1":
            corrected_l1,

        "corrected_PI_RNN_vs_SG7A_L2":
            rms(
                corrected_difference
            ),

        "corrected_PI_RNN_vs_SG7A_Linf":
            maximum_absolute(
                corrected_difference
            ),

        "projection_amplification_ratio":
            amplification_ratio,

        "PI_RNN_projection_MAE":
            mae(
                pirnn_projection
            ),

        "PI_RNN_projection_RMS":
            rms(
                pirnn_projection
            ),

        "PI_RNN_projection_MAX":
            maximum_absolute(
                pirnn_projection
            ),

        "SG7A_projection_MAE":
            mae(
                truth_projection
            ),

        "SG7A_projection_RMS":
            rms(
                truth_projection
            ),

        "SG7A_projection_MAX":
            maximum_absolute(
                truth_projection
            ),

        "projection_difference_MAE":
            mae(
                projection_difference
            ),

        "supported_PI_RNN_projection_MAE":
            mae(
                pirnn_projection[
                    supported
                ]
            ),

        "unsupported_PI_RNN_projection_MAE":
            mae(
                pirnn_projection[
                    unsupported
                ]
            ),

        "unsupported_projection_L1_share":
            unsupported_projection_share,

        "supported_raw_state_L1":
            mae(
                raw_difference[
                    supported
                ]
            ),

        "unsupported_raw_state_L1":
            mae(
                raw_difference[
                    unsupported
                ]
            ),

        "supported_corrected_state_L1":
            mae(
                corrected_difference[
                    supported
                ]
            ),

        "unsupported_corrected_state_L1":
            mae(
                corrected_difference[
                    unsupported
                ]
            ),
    }


# =============================================================================
# SUPPORT-BIN DECOMPOSITION
# =============================================================================

def support_bin_rows(
    time_days,
    pirnn_raw,
    pirnn_corrected,
    truth_raw,
    truth_corrected,
    streamline_count,
):

    pirnn_projection = (
        pirnn_corrected
        -
        pirnn_raw
    )

    truth_projection = (
        truth_corrected
        -
        truth_raw
    )

    raw_difference = (
        pirnn_raw
        -
        truth_raw
    )

    corrected_difference = (
        pirnn_corrected
        -
        truth_corrected
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

        n_cells = int(
            np.sum(
                mask
            )
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
                    n_cells,

                "PI_RNN_projection_MAE":
                    mae(
                        pirnn_projection[
                            mask
                        ]
                    ),

                "PI_RNN_projection_MAX":
                    maximum_absolute(
                        pirnn_projection[
                            mask
                        ]
                    ),

                "SG7A_projection_MAE":
                    mae(
                        truth_projection[
                            mask
                        ]
                    ),

                "raw_state_L1":
                    mae(
                        raw_difference[
                            mask
                        ]
                    ),

                "corrected_state_L1":
                    mae(
                        corrected_difference[
                            mask
                        ]
                    ),
            }
        )

    return rows


# =============================================================================
# LAYER DECOMPOSITION
# =============================================================================

def layer_rows(
    time_days,
    pirnn_raw,
    pirnn_corrected,
    truth_raw,
    truth_corrected,
    coverage_mask,
):

    pirnn_projection = (
        pirnn_corrected
        -
        pirnn_raw
    )

    truth_projection = (
        truth_corrected
        -
        truth_raw
    )

    raw_difference = (
        pirnn_raw
        -
        truth_raw
    )

    corrected_difference = (
        pirnn_corrected
        -
        truth_corrected
    )

    rows = []

    for k in range(
        NZ
    ):

        layer_mask = np.zeros(
            GRID_SHAPE,
            dtype=bool,
        )

        layer_mask[
            k,
            :,
            :
        ] = True

        supported = (
            layer_mask
            &
            coverage_mask
        )

        unsupported = (
            layer_mask
            &
            ~coverage_mask
        )

        coverage_fraction = float(
            np.mean(
                coverage_mask[
                    k
                ]
            )
        )

        rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "layer_one_based":
                    k
                    +
                    1,

                "coverage_fraction":
                    coverage_fraction,

                "PI_RNN_projection_MAE":
                    mae(
                        pirnn_projection[
                            layer_mask
                        ]
                    ),

                "SG7A_projection_MAE":
                    mae(
                        truth_projection[
                            layer_mask
                        ]
                    ),

                "raw_state_L1":
                    mae(
                        raw_difference[
                            layer_mask
                        ]
                    ),

                "corrected_state_L1":
                    mae(
                        corrected_difference[
                            layer_mask
                        ]
                    ),

                "supported_projection_MAE":
                    mae(
                        pirnn_projection[
                            supported
                        ]
                    ),

                "unsupported_projection_MAE":
                    mae(
                        pirnn_projection[
                            unsupported
                        ]
                    ),
            }
        )

    return rows


# =============================================================================
# DISTANCE DECOMPOSITION
# =============================================================================

def distance_rows(
    time_days,
    pirnn_raw,
    pirnn_corrected,
    truth_raw,
    truth_corrected,
    distance_map,
):

    pirnn_projection = (
        pirnn_corrected
        -
        pirnn_raw
    )

    raw_difference = (
        pirnn_raw
        -
        truth_raw
    )

    corrected_difference = (
        pirnn_corrected
        -
        truth_corrected
    )

    rows = []

    for (
        label,
        lower,
        upper,
    ) in DISTANCE_BINS:

        if upper is None:

            mask = (
                distance_map
                >=
                lower
            )

        else:

            mask = (
                (
                    distance_map
                    >=
                    lower
                )
                &
                (
                    distance_map
                    <=
                    upper
                )
            )

        rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "distance_bin":
                    label,

                "cells":
                    int(
                        np.sum(
                            mask
                        )
                    ),

                "PI_RNN_projection_MAE":
                    mae(
                        pirnn_projection[
                            mask
                        ]
                    ),

                "PI_RNN_projection_MAX":
                    maximum_absolute(
                        pirnn_projection[
                            mask
                        ]
                    ),

                "raw_state_L1":
                    mae(
                        raw_difference[
                            mask
                        ]
                    ),

                "corrected_state_L1":
                    mae(
                        corrected_difference[
                            mask
                        ]
                    ),
            }
        )

    return rows


# =============================================================================
# 100-DAY PLUME DECOMPOSITION
# =============================================================================

def plume_metrics(
    field_prediction,
    field_truth,
):

    prediction_mask = (
        field_prediction
        >
        PRIMARY_THRESHOLD
    )

    truth_mask = (
        field_truth
        >
        PRIMARY_THRESHOLD
    )

    prediction_footprint = np.any(
        prediction_mask,
        axis=0,
    )

    truth_footprint = np.any(
        truth_mask,
        axis=0,
    )

    return {
        "volume_relative_error":
            relative_volume_error(
                prediction_mask,
                truth_mask,
            ),

        "three_dimensional_IoU":
            mask_iou(
                prediction_mask,
                truth_mask,
            ),

        "footprint_IoU":
            mask_iou(
                prediction_footprint,
                truth_footprint,
            ),

        "PI_RNN_plume_cells":
            int(
                np.sum(
                    prediction_mask
                )
            ),

        "SG7A_plume_cells":
            int(
                np.sum(
                    truth_mask
                )
            ),
    }


# =============================================================================
# PLOTS
# =============================================================================

def plot_global_errors(
    global_rows,
):

    times = np.asarray(
        [
            row[
                "time_days"
            ]
            for row
            in global_rows
        ],
        dtype=np.float64,
    )

    raw = np.asarray(
        [
            row[
                "raw_PI_RNN_vs_SG7A_L1"
            ]
            for row
            in global_rows
        ],
        dtype=np.float64,
    )

    corrected = np.asarray(
        [
            row[
                "corrected_PI_RNN_vs_SG7A_L1"
            ]
            for row
            in global_rows
        ],
        dtype=np.float64,
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        times,
        raw,
        marker="o",
        label="Pre-projection map-back",
    )

    ax.plot(
        times,
        corrected,
        marker="s",
        label="After conservative projection",
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        "PI-RNN vs SG7A L1"
    )

    ax.set_title(
        "PAD-Stream V15-SG7E-2\n"
        "Raw vs Projected Grid Error"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7E2_Raw_vs_Projected_Error.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_projection_share(
    global_rows,
):

    times = np.asarray(
        [
            row[
                "time_days"
            ]
            for row
            in global_rows
        ],
        dtype=np.float64,
    )

    share = np.asarray(
        [
            row[
                "unsupported_projection_L1_share"
            ]
            for row
            in global_rows
        ],
        dtype=np.float64,
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        times,
        share,
        marker="o",
    )

    ax.axhline(
        UNSUPPORTED_PROJECTION_SHARE_REFERENCE,
        linestyle="--",
        label="Diagnostic reference",
    )

    ax.set_ylim(
        0.0,
        1.05,
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        "Fraction of projection L1 in N=0 cells"
    )

    ax.set_title(
        "PAD-Stream V15-SG7E-2\n"
        "Unsupported-Cell Projection Share"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7E2_Unsupported_Projection_Share.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_support_projection(
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
            1000.0,
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
            "PI_RNN_projection_MAE"
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
        "Mean |projection correction|"
    )

    ax.set_title(
        "PAD-Stream V15-SG7E-2\n"
        "Projection Dependence vs Streamline Support — 1000 d"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7E2_Projection_vs_Support_1000d.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_distance_projection(
    distance_rows_all,
):

    rows = [
        row
        for row
        in distance_rows_all
        if np.isclose(
            row[
                "time_days"
            ],
            1000.0,
        )
    ]

    labels = [
        row[
            "distance_bin"
        ]
        for row
        in rows
    ]

    values = [
        row[
            "PI_RNN_projection_MAE"
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
        "Cell distance from direct streamline support"
    )

    ax.set_ylabel(
        "Mean |projection correction|"
    )

    ax.set_title(
        "PAD-Stream V15-SG7E-2\n"
        "Projection Correction vs Distance from Support — 1000 d"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7E2_Projection_vs_SupportDistance_1000d.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_layer_projection(
    layer_rows_all,
):

    rows = [
        row
        for row
        in layer_rows_all
        if np.isclose(
            row[
                "time_days"
            ],
            1000.0,
        )
    ]

    layers = [
        row[
            "layer_one_based"
        ]
        for row
        in rows
    ]

    values = [
        row[
            "PI_RNN_projection_MAE"
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

    ax.plot(
        layers,
        values,
        marker="o",
    )

    ax.set_xlabel(
        "Layer"
    )

    ax.set_ylabel(
        "PI-RNN projection MAE"
    )

    ax.set_title(
        "PAD-Stream V15-SG7E-2\n"
        "Projection Dependence by Vertical Layer — 1000 d"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7E2_Projection_By_Layer_1000d.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_100d_maps(
    pirnn_raw,
    truth_raw,
    pirnn_corrected,
    truth_corrected,
    coverage_mask,
):

    layer = 7

    fields = [
        (
            "PI-RNN pre-projection",
            pirnn_raw[
                layer
            ],
        ),

        (
            "SG7A pre-projection",
            truth_raw[
                layer
            ],
        ),

        (
            "PI-RNN projected",
            pirnn_corrected[
                layer
            ],
        ),

        (
            "SG7A projected",
            truth_corrected[
                layer
            ],
        ),
    ]

    fig, axes = plt.subplots(
        2,
        2,
        figsize=(
            11,
            10,
        )
    )

    for (
        ax,
        (
            title,
            field,
        ),
    ) in zip(
        axes.ravel(),
        fields,
    ):

        image = ax.imshow(
            field,
            origin="lower",
            vmin=S_MIN,
            vmax=S_MAX,
        )

        ax.set_title(
            title
        )

        ax.set_xlabel(
            "i"
        )

        ax.set_ylabel(
            "j"
        )

        fig.colorbar(
            image,
            ax=ax,
        )

    fig.suptitle(
        "PAD-Stream V15-SG7E-2\n"
        "100-Day Map-Back / Projection Audit — Layer 8"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7E2_Raw_vs_Projected_100d_Layer08.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    projection = (
        pirnn_corrected
        -
        pirnn_raw
    )

    fig, ax = plt.subplots(
        figsize=(
            8,
            7,
        )
    )

    image = ax.imshow(
        projection[
            layer
        ],
        origin="lower",
    )

    unsupported_layer = (
        ~coverage_mask[
            layer
        ]
    )

    ax.contour(
        unsupported_layer.astype(
            np.float64
        ),
        levels=[
            0.5
        ],
        linewidths=0.8,
    )

    ax.set_title(
        "PAD-Stream V15-SG7E-2\n"
        "PI-RNN Projection Correction with N=0 Boundary — 100 d, Layer 8"
    )

    ax.set_xlabel(
        "i"
    )

    ax.set_ylabel(
        "j"
    )

    fig.colorbar(
        image,
        ax=ax,
        label=r"$S_{projected}-S_{raw}$",
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7E2_ProjectionCorrection_100d_Layer08.png",
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
            "PAD-Stream V15-SG7E-2 raw map-back / "
            "projection dependence audit."
        )
    )

    parser.add_argument(
        "--workspace",
        type=str,
        default=str(
            DEFAULT_SOURCE_WORKSPACE
        ),
        help=(
            "Source SG5C case workspace. "
            "Defaults to the 11x11 sensitivity workspace."
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
        "PAD-Stream Version 15-SG7E-2"
    )

    print(
        "Raw Map-Back / Projection Dependence Audit"
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
        "NO PLUME VALIDATION THRESHOLD WILL BE CHANGED."
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

    data = load_source(
        source_workspace
    )

    times = (
        data[
            "times"
        ]
    )

    coverage_mask = (
        data[
            "coverage_mask"
        ]
    )

    streamline_count = (
        data[
            "streamline_count"
        ]
    )

    pirnn_raw = (
        data[
            "pirnn_raw"
        ]
    )

    truth_raw = (
        data[
            "truth_raw"
        ]
    )

    pirnn_corrected = (
        data[
            "pirnn_corrected"
        ]
    )

    truth_corrected = (
        data[
            "truth_corrected"
        ]
    )

    sg7e1_summary = (
        data[
            "sg7e1_summary"
        ]
    )

    # =========================================================================
    # SOURCE CONTRACT
    # =========================================================================

    direct_coverage = float(
        np.mean(
            coverage_mask
        )
    )

    supported_cells = int(
        np.sum(
            coverage_mask
        )
    )

    unsupported_cells = int(
        np.sum(
            ~coverage_mask
        )
    )

    print(
        "\nSOURCE SUPPORT CONTRACT"
    )

    print(
        f"  Grid                    : "
        f"{GRID_SHAPE}"
    )

    print(
        f"  Directly supported cells: "
        f"{supported_cells:,}"
    )

    print(
        f"  Unsupported cells       : "
        f"{unsupported_cells:,}"
    )

    print(
        f"  Direct coverage         : "
        f"{direct_coverage:.3%}"
    )

    print(
        f"  Maximum support count   : "
        f"{int(np.max(streamline_count))}"
    )

    print(
        f"  SG7E-1 diagnosis        : "
        f"{sg7e1_summary.get('diagnosis', 'UNKNOWN')}"
    )

    # =========================================================================
    # PRE-PROJECTION FALLBACK SANITY
    #
    # SG7D contract says uncovered cells receive initial-state fallback before
    # global conservative projection.
    # =========================================================================

    pirnn_uncovered_raw_difference = np.max(
        np.abs(
            pirnn_raw[
                :,
                ~coverage_mask
            ]
            -
            S_INITIAL
        )
    )

    truth_uncovered_raw_difference = np.max(
        np.abs(
            truth_raw[
                :,
                ~coverage_mask
            ]
            -
            S_INITIAL
        )
    )

    fallback_contract_valid = (
        pirnn_uncovered_raw_difference
        <
        1.0e-10
        and
        truth_uncovered_raw_difference
        <
        1.0e-10
    )

    print(
        "\nPRE-PROJECTION FALLBACK CONTRACT"
    )

    print(
        f"  PI-RNN max |Sraw-Si| N=0: "
        f"{pirnn_uncovered_raw_difference:.6e}"
    )

    print(
        f"  SG7A max |Sraw-Si| N=0  : "
        f"{truth_uncovered_raw_difference:.6e}"
    )

    print(
        f"  Contract valid           : "
        f"{fallback_contract_valid}"
    )

    # =========================================================================
    # DISTANCE MAP
    # =========================================================================

    print(
        "\nBuilding Cartesian distance-to-support map..."
    )

    distance_map = (
        support_distance_map(
            coverage_mask
        )
    )

    print(
        f"  Maximum cell distance    : "
        f"{int(np.max(distance_map))}"
    )

    # =========================================================================
    # TIME-DEPENDENT DECOMPOSITION
    # =========================================================================

    global_rows = []

    support_rows_all = []

    layer_rows_all = []

    distance_rows_all = []

    print(
        "\n"
        + "=" * 78
    )

    print(
        "GLOBAL RAW / PROJECTION DECOMPOSITION"
    )

    print(
        "=" * 78
    )

    for time_index, time_days in enumerate(
        times
    ):

        global_row = global_metrics_for_time(
            time_days,
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
            coverage_mask,
        )

        global_rows.append(
            global_row
        )

        support_rows_all.extend(
            support_bin_rows(
                time_days,
                pirnn_raw[
                    time_index
                ],
                pirnn_corrected[
                    time_index
                ],
                truth_raw[
                    time_index
                ],
                truth_corrected[
                    time_index
                ],
                streamline_count,
            )
        )

        layer_rows_all.extend(
            layer_rows(
                time_days,
                pirnn_raw[
                    time_index
                ],
                pirnn_corrected[
                    time_index
                ],
                truth_raw[
                    time_index
                ],
                truth_corrected[
                    time_index
                ],
                coverage_mask,
            )
        )

        distance_rows_all.extend(
            distance_rows(
                time_days,
                pirnn_raw[
                    time_index
                ],
                pirnn_corrected[
                    time_index
                ],
                truth_raw[
                    time_index
                ],
                truth_corrected[
                    time_index
                ],
                distance_map,
            )
        )

        print(
            f"\n  t = {time_days:.1f} days"
        )

        print(
            f"    Raw PI-RNN/SG7A L1     : "
            f"{global_row['raw_PI_RNN_vs_SG7A_L1']:.6e}"
        )

        print(
            f"    Projected PI-RNN/SG7A  : "
            f"{global_row['corrected_PI_RNN_vs_SG7A_L1']:.6e}"
        )

        print(
            f"    Projection amplification: "
            f"{global_row['projection_amplification_ratio']:.3f}"
        )

        print(
            f"    PI-RNN projection MAE   : "
            f"{global_row['PI_RNN_projection_MAE']:.6e}"
        )

        print(
            f"    Supported proj. MAE     : "
            f"{global_row['supported_PI_RNN_projection_MAE']:.6e}"
        )

        print(
            f"    Unsupported proj. MAE   : "
            f"{global_row['unsupported_PI_RNN_projection_MAE']:.6e}"
        )

        print(
            f"    N=0 projection share    : "
            f"{global_row['unsupported_projection_L1_share']:.3%}"
        )

    # =========================================================================
    # 100-DAY PLUME DECOMPOSITION
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
            "100-day deployment state not found."
        )

    raw_plume = plume_metrics(
        pirnn_raw[
            index_100
        ],
        truth_raw[
            index_100
        ],
    )

    projected_plume = plume_metrics(
        pirnn_corrected[
            index_100
        ],
        truth_corrected[
            index_100
        ],
    )

    plume_rows = [
        {
            "state":
                "pre_projection",

            **raw_plume,
        },

        {
            "state":
                "projected",

            **projected_plume,
        },
    ]

    print(
        "\n"
        + "=" * 78
    )

    print(
        "100-DAY PLUME DECOMPOSITION"
    )

    print(
        "=" * 78
    )

    print(
        "\nPRE-PROJECTION"
    )

    print(
        f"  Volume relative error   : "
        f"{raw_plume['volume_relative_error']:.3%}"
    )

    print(
        f"  3D plume IoU            : "
        f"{raw_plume['three_dimensional_IoU']:.6f}"
    )

    print(
        f"  Footprint IoU           : "
        f"{raw_plume['footprint_IoU']:.6f}"
    )

    print(
        "\nAFTER CONSERVATIVE PROJECTION"
    )

    print(
        f"  Volume relative error   : "
        f"{projected_plume['volume_relative_error']:.3%}"
    )

    print(
        f"  3D plume IoU            : "
        f"{projected_plume['three_dimensional_IoU']:.6f}"
    )

    print(
        f"  Footprint IoU           : "
        f"{projected_plume['footprint_IoU']:.6f}"
    )

    # =========================================================================
    # DIAGNOSTIC AGGREGATES
    # =========================================================================

    max_raw_l1 = max(
        row[
            "raw_PI_RNN_vs_SG7A_L1"
        ]
        for row
        in global_rows
    )

    max_corrected_l1 = max(
        row[
            "corrected_PI_RNN_vs_SG7A_L1"
        ]
        for row
        in global_rows
    )

    max_amplification = max(
        row[
            "projection_amplification_ratio"
        ]
        for row
        in global_rows
    )

    minimum_unsupported_share = min(
        row[
            "unsupported_projection_L1_share"
        ]
        for row
        in global_rows
    )

    maximum_supported_projection_mae = max(
        row[
            "supported_PI_RNN_projection_MAE"
        ]
        for row
        in global_rows
    )

    maximum_unsupported_projection_mae = max(
        row[
            "unsupported_PI_RNN_projection_MAE"
        ]
        for row
        in global_rows
    )

    # =========================================================================
    # DIAGNOSIS
    # =========================================================================

    raw_state_good = (
        max_raw_l1
        <
        RAW_STATE_L1_REFERENCE
    )

    unsupported_projection_dominant = (
        minimum_unsupported_share
        >=
        UNSUPPORTED_PROJECTION_SHARE_REFERENCE
    )

    projection_amplifies_error = (
        max_amplification
        >
        PROJECTION_AMPLIFICATION_REFERENCE
    )

    supported_projection_small = (
        maximum_supported_projection_mae
        <
        0.02
    )

    raw_100_volume_bad = (
        raw_plume[
            "volume_relative_error"
        ]
        >
        0.10
    )

    projected_100_volume_bad = (
        projected_plume[
            "volume_relative_error"
        ]
        >
        0.10
    )

    if (
        raw_state_good
        and
        unsupported_projection_dominant
        and
        supported_projection_small
        and
        not projection_amplifies_error
    ):

        diagnosis = (
            "UNSUPPORTED_CELL_PROJECTION_DOMINANT"
        )

        recommendation = (
            "The remaining projection dependence is dominated by cells "
            "without direct streamline support. Further seed-density "
            "refinement may still be justified, but only after quantifying "
            "the marginal coverage gain expected beyond 11x11."
        )

        next_milestone = (
            "V15-SG5D — High-Density Seed Extrapolation / "
            "Marginal Coverage Study"
        )

    elif (
        not raw_state_good
        or
        raw_100_volume_bad
    ):

        diagnosis = (
            "RAW_MAPBACK_DISAGREEMENT"
        )

        recommendation = (
            "The disagreement is already present before conservative "
            "projection. Diagnose the streamline-to-cell accumulation "
            "operator rather than increasing seed density."
        )

        next_milestone = (
            "V15-SG7D-1 — Raw Streamline-to-Cell "
            "Accumulation Operator Audit"
        )

    elif projection_amplifies_error:

        diagnosis = (
            "PROJECTION_AMPLIFICATION"
        )

        recommendation = (
            "The conservative projection is materially amplifying "
            "PI-RNN/SG7A disagreement. Audit the bounded inventory "
            "projection formulation before any additional seed refinement."
        )

        next_milestone = (
            "V15-SG7D-2 — Conservative Inventory "
            "Projection Operator Audit"
        )

    elif not supported_projection_small:

        diagnosis = (
            "SUPPORTED_REGION_PROJECTION_ERROR"
        )

        recommendation = (
            "Projection corrections remain material even in directly "
            "supported cells. Additional streamline density alone is "
            "unlikely to resolve the dominant limitation."
        )

        next_milestone = (
            "V15-SG7D-2 — Conservative Inventory "
            "Projection Operator Audit"
        )

    elif (
        raw_state_good
        and
        not projected_100_volume_bad
    ):

        diagnosis = (
            "PROJECTION_DEPENDENCE_ACCEPTABLE"
        )

        recommendation = (
            "Raw transport agreement and projected plume behavior are "
            "acceptable. The 11x11 candidate can move toward final "
            "deterministic baseline selection."
        )

        next_milestone = (
            "V15-SG7F — Deterministic Full-Grid "
            "Transport Baseline Freeze"
        )

    else:

        diagnosis = (
            "MIXED_MAPBACK_PROJECTION_LIMITATION"
        )

        recommendation = (
            "Both raw map-back and projection effects contribute. "
            "Perform a direct map-back operator audit before modifying "
            "seed density or projection logic."
        )

        next_milestone = (
            "V15-SG7D-1 — Raw Streamline-to-Cell "
            "Accumulation Operator Audit"
        )

    # =========================================================================
    # VALIDATION
    #
    # PASS means this audit is internally complete.
    #
    # It does NOT mean the 11x11 candidate is frozen.
    # =========================================================================

    checks = [
        (
            "SG7E-1 source diagnosis available",
            (
                sg7e1_summary.get(
                    "diagnosis"
                )
                is not None
            ),
        ),

        (
            "11x11 source grid has direct support",
            supported_cells
            >
            0,
        ),

        (
            "Coverage mask and support count agree",
            np.array_equal(
                coverage_mask,
                streamline_count
                >
                0,
            ),
        ),

        (
            "Pre-projection uncovered cells retain initial state",
            fallback_contract_valid,
        ),

        (
            "Distance-to-support map finite",
            np.all(
                distance_map
                >=
                0
            ),
        ),

        (
            "All global metrics finite",
            all(
                np.isfinite(
                    value
                )
                for row
                in global_rows
                for key, value
                in row.items()
                if key
                !=
                "time_days"
            ),
        ),

        (
            "All support metrics finite",
            all(
                np.isfinite(
                    row[
                        "PI_RNN_projection_MAE"
                    ]
                )
                for row
                in support_rows_all
            ),
        ),

        (
            "All layer metrics finite",
            all(
                np.isfinite(
                    row[
                        "PI_RNN_projection_MAE"
                    ]
                )
                for row
                in layer_rows_all
            ),
        ),

        (
            "100-day plume decomposition finite",
            all(
                np.isfinite(
                    row[
                        "volume_relative_error"
                    ]
                )
                for row
                in plume_rows
            ),
        ),

        (
            "Diagnostic classification established",
            diagnosis
            in
            {
                "UNSUPPORTED_CELL_PROJECTION_DOMINANT",
                "RAW_MAPBACK_DISAGREEMENT",
                "PROJECTION_AMPLIFICATION",
                "SUPPORTED_REGION_PROJECTION_ERROR",
                "MIXED_MAPBACK_PROJECTION_LIMITATION",
                "PROJECTION_DEPENDENCE_ACCEPTABLE",
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
        "V15-SG7E-2 DIAGNOSTIC VALIDATION"
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
        f"  Maximum raw L1           : "
        f"{max_raw_l1:.6e}"
    )

    print(
        f"  Maximum projected L1     : "
        f"{max_corrected_l1:.6e}"
    )

    print(
        f"  Maximum amplification    : "
        f"{max_amplification:.3f}"
    )

    print(
        f"  Min N=0 projection share : "
        f"{minimum_unsupported_share:.3%}"
    )

    print(
        f"  Max supported proj. MAE  : "
        f"{maximum_supported_projection_mae:.6e}"
    )

    print(
        f"  Max unsupported proj. MAE: "
        f"{maximum_unsupported_projection_mae:.6e}"
    )

    print(
        f"  Raw state agreement good : "
        f"{raw_state_good}"
    )

    print(
        f"  N=0 projection dominant  : "
        f"{unsupported_projection_dominant}"
    )

    print(
        f"  Projection amplifies err.: "
        f"{projection_amplifies_error}"
    )

    print(
        f"  Supported projection low : "
        f"{supported_projection_small}"
    )

    print(
        f"  Raw 100d volume >10%     : "
        f"{raw_100_volume_bad}"
    )

    print(
        f"  Projected 100d >10%      : "
        f"{projected_100_volume_bad}"
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
    # SAVE TABLES
    # =========================================================================

    save_csv(
        GLOBAL_TABLE_FILE,
        global_rows,
    )

    save_csv(
        SUPPORT_TABLE_FILE,
        support_rows_all,
    )

    save_csv(
        LAYER_TABLE_FILE,
        layer_rows_all,
    )

    save_csv(
        DISTANCE_TABLE_FILE,
        distance_rows_all,
    )

    save_csv(
        PLUME_TABLE_FILE,
        plume_rows,
    )

    # =========================================================================
    # NUMERICAL DATABASE
    # =========================================================================

    np.savez_compressed(
        DATABASE_FILE,

        times_days=
            times,

        coverage_mask=
            coverage_mask,

        streamline_count=
            streamline_count,

        support_distance_cells=
            distance_map,

        PI_RNN_raw=
            pirnn_raw,

        SG7A_raw=
            truth_raw,

        PI_RNN_corrected=
            pirnn_corrected,

        SG7A_corrected=
            truth_corrected,

        PI_RNN_projection_delta=
            (
                pirnn_corrected
                -
                pirnn_raw
            ),

        SG7A_projection_delta=
            (
                truth_corrected
                -
                truth_raw
            ),
    )

    # =========================================================================
    # PLOTS
    # =========================================================================

    plot_global_errors(
        global_rows
    )

    plot_projection_share(
        global_rows
    )

    plot_support_projection(
        support_rows_all
    )

    plot_distance_projection(
        distance_rows_all
    )

    plot_layer_projection(
        layer_rows_all
    )

    plot_100d_maps(
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
        coverage_mask,
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7E-2",

        "description":
            (
                "Raw map-back and conservative projection "
                "dependence audit for the 11x11 SGSim "
                "streamline candidate"
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

        "source_support": {
            "direct_cell_coverage_fraction":
                direct_coverage,

            "supported_cells":
                supported_cells,

            "unsupported_cells":
                unsupported_cells,

            "maximum_streamline_support_count":
                int(
                    np.max(
                        streamline_count
                    )
                ),

            "incoming_SG7E1_diagnosis":
                sg7e1_summary.get(
                    "diagnosis",
                    "UNKNOWN",
                ),
        },

        "fallback_contract": {
            "PI_RNN_max_uncovered_raw_deviation":
                float(
                    pirnn_uncovered_raw_difference
                ),

            "SG7A_max_uncovered_raw_deviation":
                float(
                    truth_uncovered_raw_difference
                ),

            "valid":
                bool(
                    fallback_contract_valid
                ),
        },

        "diagnostic_aggregates": {
            "maximum_raw_L1":
                max_raw_l1,

            "maximum_corrected_L1":
                max_corrected_l1,

            "maximum_projection_amplification_ratio":
                max_amplification,

            "minimum_unsupported_projection_share":
                minimum_unsupported_share,

            "maximum_supported_projection_MAE":
                maximum_supported_projection_mae,

            "maximum_unsupported_projection_MAE":
                maximum_unsupported_projection_mae,

            "raw_100d_plume_volume_relative_error":
                raw_plume[
                    "volume_relative_error"
                ],

            "projected_100d_plume_volume_relative_error":
                projected_plume[
                    "volume_relative_error"
                ],
        },

        "diagnostic_flags": {
            "raw_state_agreement_good":
                bool(
                    raw_state_good
                ),

            "unsupported_projection_dominant":
                bool(
                    unsupported_projection_dominant
                ),

            "projection_amplifies_error":
                bool(
                    projection_amplifies_error
                ),

            "supported_projection_small":
                bool(
                    supported_projection_small
                ),

            "raw_100d_volume_error_above_10pct":
                bool(
                    raw_100_volume_bad
                ),

            "projected_100d_volume_error_above_10pct":
                bool(
                    projected_100_volume_bad
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

    with SUMMARY_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            summary,
            handle,
            indent=2,
        )

    # =========================================================================
    # FINAL
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
        f"  {GLOBAL_TABLE_FILE.name}"
    )

    print(
        f"  {SUPPORT_TABLE_FILE.name}"
    )

    print(
        f"  {LAYER_TABLE_FILE.name}"
    )

    print(
        f"  {DISTANCE_TABLE_FILE.name}"
    )

    print(
        f"  {PLUME_TABLE_FILE.name}"
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
        "  V15SG7E2_Raw_vs_Projected_Error.png"
    )

    print(
        "  V15SG7E2_Unsupported_Projection_Share.png"
    )

    print(
        "  V15SG7E2_Projection_vs_Support_1000d.png"
    )

    print(
        "  V15SG7E2_Projection_vs_SupportDistance_1000d.png"
    )

    print(
        "  V15SG7E2_Projection_By_Layer_1000d.png"
    )

    print(
        "  V15SG7E2_Raw_vs_Projected_100d_Layer08.png"
    )

    print(
        "  V15SG7E2_ProjectionCorrection_100d_Layer08.png"
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
            "V15-SG7E-2 AUDIT: PASS"
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
            "V15-SG7E-2 AUDIT: INCOMPLETE"
        )

        print()

        print(
            "Do not alter seed density, map-back, or "
            "projection logic until this audit is resolved."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()