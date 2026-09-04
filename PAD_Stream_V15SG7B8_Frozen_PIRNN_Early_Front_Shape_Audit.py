from __future__ import annotations

from pathlib import Path
import argparse
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7B-8
# Frozen PI-RNN Early-Front Shape Audit
#
# NO TRAINING.
# NO MODEL WEIGHT CHANGES.
# NO ARCHITECTURE CHANGE.
# NO SEED-DENSITY CHANGE.
# NO MAP-BACK CHANGE.
# NO VALIDATION-THRESHOLD CHANGE.
#
#
# PURPOSE
# -------
#
# SG7D-2C established:
#
#       PI_RNN_FRONT_SMOOTHING_OR_THRESHOLD_AVOIDANCE
#
# At 100 days:
#
#       SG7A robust fronts   : 992
#       PI-RNN robust fronts : 0
#
# Therefore this milestone audits the frozen SG7B PI-RNN directly in
# streamline transport space.
#
#
# PRIMARY QUESTIONS
# -----------------
#
# 1. Does the PI-RNN approach S = 0.21 but remain on one side?
#
# 2. Is the PI-RNN transition broader than SG7A?
#
# 3. Is the PI-RNN front slope systematically weaker?
#
# 4. Is the discrepancy concentrated on particular streamline TOF families?
#
# 5. Does the PI-RNN reproduce the shock location approximately but smooth it?
#
#
# POSSIBLE DIAGNOSES
# ------------------
#
# FRONT_OVERSMOOTHING
#
# THRESHOLD_AVOIDANCE
#
# FRONT_POSITION_AND_SHAPE_BIAS
#
# EARLY_FRONT_ERROR_LOCALIZED
#
# FROZEN_PIRNN_FRONT_SHAPE_ACCEPTABLE
#
# =============================================================================


# =============================================================================
# ROOT / SOURCE
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
    / "V15_SG7B8"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# INPUT FILES
# =============================================================================

SG6_FILE_RELATIVE = (
    Path("output")
    / "V15_SG6"
    / "STREAMLINE_TRANSPORT_COORDINATES.npz"
)


SG7C_FILE_RELATIVE = (
    Path("output")
    / "V15_SG7C"
    / "SG7C_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"
)


SG7D2C_SUMMARY = (
    ROOT
    / "output"
    / "V15_SG7D2C"
    / "PAD_Stream_V15SG7D2C_Summary.json"
)


# =============================================================================
# OUTPUTS
# =============================================================================

PROFILE_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7B8_Profile_Front_Shape_Metrics.csv"
)


TIME_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7B8_Front_Shape_By_Time.csv"
)


TOF_BAND_FILE = (
    OUTPUT_DIR
    / "V15SG7B8_Front_Shape_By_TOF_Band.csv"
)


DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7B8_Front_Shape_Audit.npz"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B8_Summary.json"
)


# =============================================================================
# FRONT DEFINITIONS
# =============================================================================

S_INITIAL = 0.20

FRONT_THRESHOLD = 0.21


# Transition-band levels.
#
# These deliberately sit above the initial state and span the shock region.
LOW_LEVEL = 0.21
MID_LEVEL = 0.25
HIGH_LEVEL = 0.30


NEAR_THRESHOLD_TOL = 5.0e-4


EPS = 1.0e-14


# =============================================================================
# DIAGNOSTIC REFERENCES
#
# These are NOT freeze gates.
# =============================================================================

WIDTH_RATIO_REFERENCE = 1.50

SLOPE_RATIO_REFERENCE = 0.70

THRESHOLD_GAP_REFERENCE = 0.005

PROFILE_L1_REFERENCE = 0.02

EARLY_TIME_DAYS = 100.0


# =============================================================================
# TOF BANDS
# =============================================================================

TOF_BANDS = [
    (
        "fast",
        0.0,
        250.0,
    ),

    (
        "intermediate",
        250.0,
        500.0,
    ),

    (
        "slow",
        500.0,
        1000.0,
    ),

    (
        "very_slow",
        1000.0,
        None,
    ),
]


# =============================================================================
# BASIC HELPERS
# =============================================================================

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

    path = Path(
        path
    )

    if not path.exists():

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


def safe_mean(
    values,
):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    values = values[
        np.isfinite(
            values
        )
    ]

    if values.size == 0:

        return np.nan

    return float(
        np.mean(
            values
        )
    )


def safe_percentile(
    values,
    percentile,
):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    values = values[
        np.isfinite(
            values
        )
    ]

    if values.size == 0:

        return np.nan

    return float(
        np.percentile(
            values,
            percentile,
        )
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

    sg6_path = (
        source_workspace
        /
        SG6_FILE_RELATIVE
    )

    sg7c_path = (
        source_workspace
        /
        SG7C_FILE_RELATIVE
    )

    for path in [
        sg6_path,
        sg7c_path,
        SG7D2C_SUMMARY,
    ]:

        if not Path(
            path
        ).exists():

            raise FileNotFoundError(
                f"Missing required input:\n{path}"
            )

    sg6 = np.load(
        sg6_path,
        allow_pickle=True,
    )

    sg7c = np.load(
        sg7c_path,
        allow_pickle=True,
    )

    sg7d2c_summary = load_json(
        SG7D2C_SUMMARY
    )

    return (
        sg6,
        sg7c,
        sg7d2c_summary,
    )


# =============================================================================
# EXTRACT SG6
# =============================================================================

def extract_sg6(
    sg6,
):

    xi_key = find_key(
        sg6,
        [
            "xi",
            "transport_xi",
        ],
        "normalized streamline coordinate",
    )

    tau_end_key = find_key(
        sg6,
        [
            "tau_end_s",
            "terminal_tau_s",
            "terminal_tof_s",
        ],
        "terminal streamline TOF",
    )

    weight_key = find_key(
        sg6,
        [
            "weights_m3_s",
            "weights",
            "flow_weights_m3_s",
        ],
        "streamline flow weights",
    )

    producer_key = find_key(
        sg6,
        [
            "producer",
            "producer_id",
            "producer_index",
        ],
        "producer identifier",
    )

    streamline_id_key = find_key(
        sg6,
        [
            "streamline_id",
            "id",
        ],
        "streamline identifier",
    )

    xi = np.asarray(
        sg6[
            xi_key
        ],
        dtype=np.float64,
    )

    tau_end_s = np.asarray(
        sg6[
            tau_end_key
        ],
        dtype=np.float64,
    )

    weights = np.asarray(
        sg6[
            weight_key
        ],
        dtype=np.float64,
    )

    producer = np.asarray(
        sg6[
            producer_key
        ]
    )

    streamline_id = np.asarray(
        sg6[
            streamline_id_key
        ]
    )

    return (
        xi,
        tau_end_s,
        weights,
        producer,
        streamline_id,
    )


# =============================================================================
# EXTRACT SG7C
# =============================================================================

def extract_sg7c(
    sg7c,
):

    times_key = find_key(
        sg7c,
        [
            "times_days",
            "physical_times_days",
            "deployment_times_days",
        ],
        "deployment times",
    )

    pirnn_key = find_key(
        sg7c,
        [
            "PI_RNN_saturation",
            "pirnn_saturation",
            "predicted_saturation",
            "S_pirnn",
        ],
        "PI-RNN saturation",
    )

    truth_key = find_key(
        sg7c,
        [
            "SG7A_saturation",
            "truth_saturation",
            "reference_saturation",
            "S_truth",
        ],
        "SG7A saturation",
    )

    times = np.asarray(
        sg7c[
            times_key
        ],
        dtype=np.float64,
    )

    pirnn = np.asarray(
        sg7c[
            pirnn_key
        ],
        dtype=np.float64,
    )

    truth = np.asarray(
        sg7c[
            truth_key
        ],
        dtype=np.float64,
    )

    return (
        times,
        pirnn,
        truth,
    )


# =============================================================================
# THRESHOLD POSITION
#
# Return the most downstream crossing of a specified level.
#
# If no crossing exists, return NaN.
# =============================================================================

def level_position(
    saturation,
    xi,
    level,
):

    saturation = np.asarray(
        saturation,
        dtype=np.float64,
    )

    above = (
        saturation
        >
        level
    )

    transitions = np.where(
        above[:-1]
        !=
        above[1:]
    )[0]

    if transitions.size == 0:

        return np.nan

    node = int(
        transitions[-1]
    )

    s0 = float(
        saturation[
            node
        ]
    )

    s1 = float(
        saturation[
            node + 1
        ]
    )

    if abs(
        s1
        -
        s0
    ) <= EPS:

        alpha = 0.5

    else:

        alpha = (
            level
            -
            s0
        ) / (
            s1
            -
            s0
        )

        alpha = float(
            np.clip(
                alpha,
                0.0,
                1.0,
            )
        )

    return float(
        xi[
            node
        ]
        +
        alpha
        *
        (
            xi[
                node + 1
            ]
            -
            xi[
                node
            ]
        )
    )


# =============================================================================
# FRONT WIDTH
#
# We define width using HIGH_LEVEL and LOW_LEVEL.
#
# If both positions exist:
#
#       width = |xi_low - xi_high|
#
# Smaller width = sharper front.
# =============================================================================

def transition_width(
    saturation,
    xi,
):

    xi_high = level_position(
        saturation,
        xi,
        HIGH_LEVEL,
    )

    xi_low = level_position(
        saturation,
        xi,
        LOW_LEVEL,
    )

    if (
        not np.isfinite(
            xi_high
        )
        or
        not np.isfinite(
            xi_low
        )
    ):

        return (
            np.nan,
            xi_high,
            xi_low,
        )

    width = abs(
        xi_low
        -
        xi_high
    )

    return (
        float(
            width
        ),
        float(
            xi_high
        ),
        float(
            xi_low
        ),
    )


# =============================================================================
# LOCAL FRONT SLOPE
#
# Use maximum absolute dS/dxi in a narrow front neighborhood.
# =============================================================================

def local_front_slope(
    saturation,
    xi,
):

    saturation = np.asarray(
        saturation,
        dtype=np.float64,
    )

    derivative = np.gradient(
        saturation,
        xi,
    )

    front_mask = (
        (
            saturation
            >=
            LOW_LEVEL
        )
        &
        (
            saturation
            <=
            HIGH_LEVEL
        )
    )

    if np.any(
        front_mask
    ):

        return float(
            np.max(
                np.abs(
                    derivative[
                        front_mask
                    ]
                )
            )
        )

    closest = int(
        np.argmin(
            np.abs(
                saturation
                -
                MID_LEVEL
            )
        )
    )

    return float(
        abs(
            derivative[
                closest
            ]
        )
    )


# =============================================================================
# PROFILE METRICS
# =============================================================================

def profile_metrics(
    saturation,
    xi,
):

    saturation = np.asarray(
        saturation,
        dtype=np.float64,
    )

    (
        width,
        xi_high,
        xi_low,
    ) = transition_width(
        saturation,
        xi,
    )

    xi_mid = level_position(
        saturation,
        xi,
        MID_LEVEL,
    )

    slope = local_front_slope(
        saturation,
        xi,
    )

    closest_threshold_distance = float(
        np.min(
            np.abs(
                saturation
                -
                FRONT_THRESHOLD
            )
        )
    )

    closest_threshold_index = int(
        np.argmin(
            np.abs(
                saturation
                -
                FRONT_THRESHOLD
            )
        )
    )

    closest_threshold_value = float(
        saturation[
            closest_threshold_index
        ]
    )

    minimum = float(
        np.min(
            saturation
        )
    )

    maximum = float(
        np.max(
            saturation
        )
    )

    has_threshold_crossing = bool(
        np.any(
            (
                saturation[:-1]
                -
                FRONT_THRESHOLD
            )
            *
            (
                saturation[1:]
                -
                FRONT_THRESHOLD
            )
            <
            0.0
        )
    )

    near_threshold = bool(
        closest_threshold_distance
        <=
        NEAR_THRESHOLD_TOL
    )

    total_variation = float(
        np.sum(
            np.abs(
                np.diff(
                    saturation
                )
            )
        )
    )

    return {
        "width":
            width,

        "xi_high":
            xi_high,

        "xi_mid":
            xi_mid,

        "xi_low":
            xi_low,

        "max_front_slope":
            slope,

        "closest_threshold_distance":
            closest_threshold_distance,

        "closest_threshold_value":
            closest_threshold_value,

        "minimum":
            minimum,

        "maximum":
            maximum,

        "has_threshold_crossing":
            has_threshold_crossing,

        "near_threshold":
            near_threshold,

        "total_variation":
            total_variation,
    }


# =============================================================================
# BUILD PROFILE TABLE
# =============================================================================

def audit_profiles(
    times,
    xi,
    tau_end_s,
    weights,
    producer,
    streamline_id,
    pirnn,
    truth,
):

    rows = []

    for time_index, time_days in enumerate(
        times
    ):

        for streamline in range(
            pirnn.shape[1]
        ):

            p = (
                pirnn[
                    time_index,
                    streamline
                ]
            )

            t = (
                truth[
                    time_index,
                    streamline
                ]
            )

            pirnn_metrics = profile_metrics(
                p,
                xi,
            )

            truth_metrics = profile_metrics(
                t,
                xi,
            )

            profile_l1 = float(
                np.mean(
                    np.abs(
                        p
                        -
                        t
                    )
                )
            )

            profile_l2 = float(
                np.sqrt(
                    np.mean(
                        (
                            p
                            -
                            t
                        ) ** 2
                    )
                )
            )

            if (
                np.isfinite(
                    pirnn_metrics[
                        "width"
                    ]
                )
                and
                np.isfinite(
                    truth_metrics[
                        "width"
                    ]
                )
                and
                truth_metrics[
                    "width"
                ]
                >
                EPS
            ):

                width_ratio = (
                    pirnn_metrics[
                        "width"
                    ]
                    /
                    truth_metrics[
                        "width"
                    ]
                )

            else:

                width_ratio = np.nan

            if (
                np.isfinite(
                    pirnn_metrics[
                        "max_front_slope"
                    ]
                )
                and
                np.isfinite(
                    truth_metrics[
                        "max_front_slope"
                    ]
                )
                and
                truth_metrics[
                    "max_front_slope"
                ]
                >
                EPS
            ):

                slope_ratio = (
                    pirnn_metrics[
                        "max_front_slope"
                    ]
                    /
                    truth_metrics[
                        "max_front_slope"
                    ]
                )

            else:

                slope_ratio = np.nan

            rows.append(
                {
                    "time_days":
                        float(
                            time_days
                        ),

                    "streamline_index":
                        streamline,

                    "streamline_id":
                        str(
                            streamline_id[
                                streamline
                            ]
                        ),

                    "producer":
                        str(
                            producer[
                                streamline
                            ]
                        ),

                    "terminal_TOF_days":
                        float(
                            tau_end_s[
                                streamline
                            ]
                            /
                            86400.0
                        ),

                    "flow_weight_m3_s":
                        float(
                            weights[
                                streamline
                            ]
                        ),

                    "profile_L1":
                        profile_l1,

                    "profile_L2":
                        profile_l2,

                    "SG7A_has_threshold_crossing":
                        truth_metrics[
                            "has_threshold_crossing"
                        ],

                    "PI_RNN_has_threshold_crossing":
                        pirnn_metrics[
                            "has_threshold_crossing"
                        ],

                    "SG7A_near_threshold":
                        truth_metrics[
                            "near_threshold"
                        ],

                    "PI_RNN_near_threshold":
                        pirnn_metrics[
                            "near_threshold"
                        ],

                    "SG7A_closest_threshold_distance":
                        truth_metrics[
                            "closest_threshold_distance"
                        ],

                    "PI_RNN_closest_threshold_distance":
                        pirnn_metrics[
                            "closest_threshold_distance"
                        ],

                    "SG7A_closest_threshold_value":
                        truth_metrics[
                            "closest_threshold_value"
                        ],

                    "PI_RNN_closest_threshold_value":
                        pirnn_metrics[
                            "closest_threshold_value"
                        ],

                    "SG7A_width":
                        truth_metrics[
                            "width"
                        ],

                    "PI_RNN_width":
                        pirnn_metrics[
                            "width"
                        ],

                    "width_ratio_PI_RNN_over_SG7A":
                        width_ratio,

                    "SG7A_front_slope":
                        truth_metrics[
                            "max_front_slope"
                        ],

                    "PI_RNN_front_slope":
                        pirnn_metrics[
                            "max_front_slope"
                        ],

                    "slope_ratio_PI_RNN_over_SG7A":
                        slope_ratio,

                    "SG7A_xi_high":
                        truth_metrics[
                            "xi_high"
                        ],

                    "PI_RNN_xi_high":
                        pirnn_metrics[
                            "xi_high"
                        ],

                    "SG7A_xi_mid":
                        truth_metrics[
                            "xi_mid"
                        ],

                    "PI_RNN_xi_mid":
                        pirnn_metrics[
                            "xi_mid"
                        ],

                    "SG7A_xi_low":
                        truth_metrics[
                            "xi_low"
                        ],

                    "PI_RNN_xi_low":
                        pirnn_metrics[
                            "xi_low"
                        ],

                    "SG7A_total_variation":
                        truth_metrics[
                            "total_variation"
                        ],

                    "PI_RNN_total_variation":
                        pirnn_metrics[
                            "total_variation"
                        ],
                }
            )

    return rows


# =============================================================================
# AGGREGATE BY TIME
# =============================================================================

def summarize_time(
    profile_rows,
    time_days,
):

    rows = [
        row
        for row
        in profile_rows
        if np.isclose(
            row[
                "time_days"
            ],
            time_days,
        )
    ]

    n = len(
        rows
    )

    truth_crossing = sum(
        row[
            "SG7A_has_threshold_crossing"
        ]
        for row
        in rows
    )

    pirnn_crossing = sum(
        row[
            "PI_RNN_has_threshold_crossing"
        ]
        for row
        in rows
    )

    truth_near = sum(
        row[
            "SG7A_near_threshold"
        ]
        for row
        in rows
    )

    pirnn_near = sum(
        row[
            "PI_RNN_near_threshold"
        ]
        for row
        in rows
    )

    width_ratios = [
        row[
            "width_ratio_PI_RNN_over_SG7A"
        ]
        for row
        in rows
    ]

    slope_ratios = [
        row[
            "slope_ratio_PI_RNN_over_SG7A"
        ]
        for row
        in rows
    ]

    pirnn_threshold_gap = [
        row[
            "PI_RNN_closest_threshold_distance"
        ]
        for row
        in rows
    ]

    truth_threshold_gap = [
        row[
            "SG7A_closest_threshold_distance"
        ]
        for row
        in rows
    ]

    profile_l1 = [
        row[
            "profile_L1"
        ]
        for row
        in rows
    ]

    return {
        "time_days":
            float(
                time_days
            ),

        "streamlines":
            n,

        "SG7A_threshold_crossings":
            truth_crossing,

        "PI_RNN_threshold_crossings":
            pirnn_crossing,

        "SG7A_near_threshold_profiles":
            truth_near,

        "PI_RNN_near_threshold_profiles":
            pirnn_near,

        "PI_RNN_threshold_gap_mean":
            safe_mean(
                pirnn_threshold_gap
            ),

        "PI_RNN_threshold_gap_P90":
            safe_percentile(
                pirnn_threshold_gap,
                90,
            ),

        "SG7A_threshold_gap_mean":
            safe_mean(
                truth_threshold_gap
            ),

        "width_ratio_mean":
            safe_mean(
                width_ratios
            ),

        "width_ratio_P50":
            safe_percentile(
                width_ratios,
                50,
            ),

        "width_ratio_P90":
            safe_percentile(
                width_ratios,
                90,
            ),

        "slope_ratio_mean":
            safe_mean(
                slope_ratios
            ),

        "slope_ratio_P50":
            safe_percentile(
                slope_ratios,
                50,
            ),

        "slope_ratio_P10":
            safe_percentile(
                slope_ratios,
                10,
            ),

        "profile_L1_mean":
            safe_mean(
                profile_l1
            ),

        "profile_L1_P90":
            safe_percentile(
                profile_l1,
                90,
            ),
    }


# =============================================================================
# TOF BAND SUMMARY
# =============================================================================

def summarize_tof_bands(
    profile_rows,
):

    output = []

    times = sorted(
        set(
            row[
                "time_days"
            ]
            for row
            in profile_rows
        )
    )

    for time_days in times:

        rows_time = [
            row
            for row
            in profile_rows
            if np.isclose(
                row[
                    "time_days"
                ],
                time_days,
            )
        ]

        for (
            label,
            lower,
            upper,
        ) in TOF_BANDS:

            if upper is None:

                selected = [
                    row
                    for row
                    in rows_time
                    if row[
                        "terminal_TOF_days"
                    ]
                    >=
                    lower
                ]

            else:

                selected = [
                    row
                    for row
                    in rows_time
                    if (
                        lower
                        <=
                        row[
                            "terminal_TOF_days"
                        ]
                        <
                        upper
                    )
                ]

            output.append(
                {
                    "time_days":
                        float(
                            time_days
                        ),

                    "TOF_band":
                        label,

                    "streamlines":
                        len(
                            selected
                        ),

                    "SG7A_crossings":
                        sum(
                            row[
                                "SG7A_has_threshold_crossing"
                            ]
                            for row
                            in selected
                        ),

                    "PI_RNN_crossings":
                        sum(
                            row[
                                "PI_RNN_has_threshold_crossing"
                            ]
                            for row
                            in selected
                        ),

                    "PI_RNN_threshold_gap_mean":
                        safe_mean(
                            [
                                row[
                                    "PI_RNN_closest_threshold_distance"
                                ]
                                for row
                                in selected
                            ]
                        ),

                    "width_ratio_mean":
                        safe_mean(
                            [
                                row[
                                    "width_ratio_PI_RNN_over_SG7A"
                                ]
                                for row
                                in selected
                            ]
                        ),

                    "slope_ratio_mean":
                        safe_mean(
                            [
                                row[
                                    "slope_ratio_PI_RNN_over_SG7A"
                                ]
                                for row
                                in selected
                            ]
                        ),

                    "profile_L1_mean":
                        safe_mean(
                            [
                                row[
                                    "profile_L1"
                                ]
                                for row
                                in selected
                            ]
                        ),
                }
            )

    return output


# =============================================================================
# REPRESENTATIVE PROFILE SELECTION
# =============================================================================

def representative_indices(
    tau_end_s,
):

    terminal_days = (
        tau_end_s
        /
        86400.0
    )

    targets = [
        180.0,
        350.0,
        900.0,
        1800.0,
    ]

    indices = []

    for target in targets:

        index = int(
            np.argmin(
                np.abs(
                    terminal_days
                    -
                    target
                )
            )
        )

        if index not in indices:

            indices.append(
                index
            )

    return indices


# =============================================================================
# PLOTS
# =============================================================================

def plot_threshold_gap(
    time_rows,
):

    times = [
        row[
            "time_days"
        ]
        for row
        in time_rows
    ]

    pirnn_gap = [
        row[
            "PI_RNN_threshold_gap_mean"
        ]
        for row
        in time_rows
    ]

    sg7a_gap = [
        row[
            "SG7A_threshold_gap_mean"
        ]
        for row
        in time_rows
    ]

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        times,
        pirnn_gap,
        marker="o",
        label="PI-RNN",
    )

    ax.plot(
        times,
        sg7a_gap,
        marker="s",
        label="SG7A",
    )

    ax.axhline(
        THRESHOLD_GAP_REFERENCE,
        linestyle="--",
        label="Diagnostic reference",
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        r"Mean min |S - 0.21|"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-8\n"
        "Distance from Early-Front Threshold"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B8_Threshold_Gap_vs_Time.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_width_ratio(
    time_rows,
):

    times = [
        row[
            "time_days"
        ]
        for row
        in time_rows
    ]

    values = [
        row[
            "width_ratio_mean"
        ]
        for row
        in time_rows
    ]

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        times,
        values,
        marker="o",
    )

    ax.axhline(
        1.0,
        linestyle="--",
        label="Equal width",
    )

    ax.axhline(
        WIDTH_RATIO_REFERENCE,
        linestyle=":",
        label="Oversmoothing reference",
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        "PI-RNN / SG7A transition width"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-8\n"
        "Front Transition Width Ratio"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B8_Front_Width_Ratio.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_slope_ratio(
    time_rows,
):

    times = [
        row[
            "time_days"
        ]
        for row
        in time_rows
    ]

    values = [
        row[
            "slope_ratio_mean"
        ]
        for row
        in time_rows
    ]

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        times,
        values,
        marker="o",
    )

    ax.axhline(
        1.0,
        linestyle="--",
        label="Equal slope",
    )

    ax.axhline(
        SLOPE_RATIO_REFERENCE,
        linestyle=":",
        label="Smoothing reference",
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        "PI-RNN / SG7A front slope"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-8\n"
        "Front Sharpness Ratio"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B8_Front_Slope_Ratio.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_representative_100d_profiles(
    xi,
    tau_end_s,
    pirnn_100,
    truth_100,
):

    indices = representative_indices(
        tau_end_s
    )

    fig, axes = plt.subplots(
        2,
        2,
        figsize=(
            12,
            9,
        )
    )

    axes = axes.ravel()

    for ax, streamline in zip(
        axes,
        indices,
    ):

        terminal_days = (
            tau_end_s[
                streamline
            ]
            /
            86400.0
        )

        ax.plot(
            xi,
            truth_100[
                streamline
            ],
            label="SG7A",
        )

        ax.plot(
            xi,
            pirnn_100[
                streamline
            ],
            label="PI-RNN",
        )

        ax.axhline(
            FRONT_THRESHOLD,
            linestyle="--",
            label="S=0.21",
        )

        ax.set_title(
            f"Streamline {streamline} | "
            f"TOF={terminal_days:.1f} d"
        )

        ax.set_xlabel(
            "xi"
        )

        ax.set_ylabel(
            "Saturation"
        )

        ax.legend()

    fig.suptitle(
        "PAD-Stream V15-SG7B-8\n"
        "Representative 100-Day Early-Front Profiles"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B8_Representative_Profiles_100d.png",
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
            "PAD-Stream V15-SG7B-8 "
            "frozen PI-RNN early-front shape audit."
        )
    )

    parser.add_argument(
        "--workspace",
        type=str,
        default=str(
            DEFAULT_SOURCE_WORKSPACE
        ),
        help=(
            "11x11 SG5C source workspace."
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
        "PAD-Stream Version 15-SG7B-8"
    )

    print(
        "Frozen PI-RNN Early-Front Shape Audit"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    print(
        "NO MODEL PARAMETERS WILL BE CHANGED."
    )

    print(
        "NO ARCHITECTURE CHANGE WILL BE MADE."
    )

    print(
        "NO SEED DENSITY WILL BE CHANGED."
    )

    print(
        "NO MAP-BACK OPERATOR WILL BE CHANGED."
    )

    print(
        "NO SG7E THRESHOLD WILL BE CHANGED."
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

    (
        sg6,
        sg7c,
        sg7d2c_summary,
    ) = load_inputs(
        source_workspace
    )

    if (
        sg7d2c_summary.get(
            "diagnosis"
        )
        !=
        "PI_RNN_FRONT_SMOOTHING_OR_THRESHOLD_AVOIDANCE"
    ):

        raise RuntimeError(
            "SG7B-8 requires SG7D-2C diagnosis:\n"
            "PI_RNN_FRONT_SMOOTHING_OR_THRESHOLD_AVOIDANCE"
        )

    (
        xi,
        tau_end_s,
        flow_weights,
        producer,
        streamline_id,
    ) = extract_sg6(
        sg6
    )

    (
        times,
        pirnn,
        truth,
    ) = extract_sg7c(
        sg7c
    )

    print(
        "\nSOURCE DATABASE"
    )

    print(
        f"  Streamlines             : "
        f"{pirnn.shape[1]:,}"
    )

    print(
        f"  Nodes                   : "
        f"{pirnn.shape[2]}"
    )

    print(
        f"  Deployment times        : "
        f"{times.tolist()}"
    )

    print(
        f"  Front threshold         : "
        f"{FRONT_THRESHOLD:.6f}"
    )

    print(
        f"  Transition band         : "
        f"{LOW_LEVEL:.3f} -> {HIGH_LEVEL:.3f}"
    )

    # =========================================================================
    # SHAPES
    # =========================================================================

    expected_shape = (
        len(
            times
        ),
        len(
            tau_end_s
        ),
        len(
            xi
        ),
    )

    if pirnn.shape != expected_shape:

        raise RuntimeError(
            "Unexpected PI-RNN deployment shape."
        )

    if truth.shape != expected_shape:

        raise RuntimeError(
            "Unexpected SG7A deployment shape."
        )

    # =========================================================================
    # AUDIT
    # =========================================================================

    profile_rows = audit_profiles(
        times,
        xi,
        tau_end_s,
        flow_weights,
        producer,
        streamline_id,
        pirnn,
        truth,
    )

    time_rows = [
        summarize_time(
            profile_rows,
            time_days,
        )
        for time_days
        in times
    ]

    tof_rows = summarize_tof_bands(
        profile_rows
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "EARLY-FRONT SHAPE DIAGNOSTICS"
    )

    print(
        "=" * 78
    )

    for row in time_rows:

        print(
            f"\n  t = {row['time_days']:.1f} days"
        )

        print(
            f"    SG7A crossings         : "
            f"{row['SG7A_threshold_crossings']:,}"
        )

        print(
            f"    PI-RNN crossings       : "
            f"{row['PI_RNN_threshold_crossings']:,}"
        )

        print(
            f"    SG7A near threshold    : "
            f"{row['SG7A_near_threshold_profiles']:,}"
        )

        print(
            f"    PI-RNN near threshold  : "
            f"{row['PI_RNN_near_threshold_profiles']:,}"
        )

        print(
            f"    PI-RNN threshold gap   : "
            f"{row['PI_RNN_threshold_gap_mean']:.6e}"
        )

        print(
            f"    Width ratio mean       : "
            f"{row['width_ratio_mean']:.6f}"
        )

        print(
            f"    Width ratio P90        : "
            f"{row['width_ratio_P90']:.6f}"
        )

        print(
            f"    Slope ratio mean       : "
            f"{row['slope_ratio_mean']:.6f}"
        )

        print(
            f"    Slope ratio P10        : "
            f"{row['slope_ratio_P10']:.6f}"
        )

        print(
            f"    Profile L1 mean        : "
            f"{row['profile_L1_mean']:.6e}"
        )

    # =========================================================================
    # 100-DAY DECISION
    # =========================================================================

    row_100 = next(
        row
        for row
        in time_rows
        if np.isclose(
            row[
                "time_days"
            ],
            EARLY_TIME_DAYS,
        )
    )

    crossing_missing = (
        row_100[
            "SG7A_threshold_crossings"
        ]
        >
        0
        and
        row_100[
            "PI_RNN_threshold_crossings"
        ]
        ==
        0
    )

    threshold_gap_large = (
        row_100[
            "PI_RNN_threshold_gap_mean"
        ]
        >
        THRESHOLD_GAP_REFERENCE
    )

    width_oversmoothed = (
        np.isfinite(
            row_100[
                "width_ratio_mean"
            ]
        )
        and
        row_100[
            "width_ratio_mean"
        ]
        >
        WIDTH_RATIO_REFERENCE
    )

    slope_too_weak = (
        np.isfinite(
            row_100[
                "slope_ratio_mean"
            ]
        )
        and
        row_100[
            "slope_ratio_mean"
        ]
        <
        SLOPE_RATIO_REFERENCE
    )

    continuous_state_good = (
        row_100[
            "profile_L1_mean"
        ]
        <
        PROFILE_L1_REFERENCE
    )

    # =========================================================================
    # DIAGNOSIS
    # =========================================================================

    if (
        crossing_missing
        and
        width_oversmoothed
        and
        slope_too_weak
        and
        continuous_state_good
    ):

        diagnosis = (
            "FRONT_OVERSMOOTHING"
        )

        recommendation = (
            "The frozen PI-RNN matches the continuous saturation field well "
            "but broadens and weakens the early displacement front enough to "
            "eliminate the SG7A threshold crossing. Reopen SG7B only through "
            "a targeted front-shape refinement branch."
        )

        next_milestone = (
            "V15-SG7B-9 — Front-Aware PI-RNN "
            "Targeted Refinement Design"
        )

    elif (
        crossing_missing
        and
        threshold_gap_large
        and
        continuous_state_good
    ):

        diagnosis = (
            "THRESHOLD_AVOIDANCE"
        )

        recommendation = (
            "The frozen PI-RNN remains systematically separated from the "
            "S=0.21 front threshold despite good continuous-state accuracy. "
            "Design a targeted front-location / threshold-crossing loss."
        )

        next_milestone = (
            "V15-SG7B-9 — Front-Aware PI-RNN "
            "Targeted Refinement Design"
        )

    elif (
        crossing_missing
        and
        not continuous_state_good
    ):

        diagnosis = (
            "FRONT_POSITION_AND_SHAPE_BIAS"
        )

        recommendation = (
            "The early front discrepancy is accompanied by larger continuous "
            "profile error. Revisit the early-time PI-RNN training balance "
            "before any grid reconstruction changes."
        )

        next_milestone = (
            "V15-SG7B-9 — Front-Aware PI-RNN "
            "Targeted Refinement Design"
        )

    elif (
        continuous_state_good
        and
        not crossing_missing
    ):

        diagnosis = (
            "EARLY_FRONT_ERROR_LOCALIZED"
        )

        recommendation = (
            "The frozen PI-RNN contains the required front but differs only "
            "locally in sharpness or location. A constrained front-aware "
            "refinement may be sufficient."
        )

        next_milestone = (
            "V15-SG7B-9 — Front-Aware PI-RNN "
            "Targeted Refinement Design"
        )

    else:

        diagnosis = (
            "FROZEN_PIRNN_FRONT_SHAPE_ACCEPTABLE"
        )

        recommendation = (
            "No dominant frozen-model front-shape defect is established. "
            "Return to the SG7D reconstruction branch."
        )

        next_milestone = (
            "V15-SG7D-3 — Constrained Front-Aware "
            "Map-Back Candidate Validation"
        )

    # =========================================================================
    # VALIDATION
    # =========================================================================

    checks = [
        (
            "Incoming SG7D-2C diagnosis reproduced",
            (
                sg7d2c_summary.get(
                    "diagnosis"
                )
                ==
                "PI_RNN_FRONT_SMOOTHING_OR_THRESHOLD_AVOIDANCE"
            ),
        ),

        (
            "2662 streamline source loaded",
            pirnn.shape[1]
            ==
            2662,
        ),

        (
            "201 nodes loaded",
            pirnn.shape[2]
            ==
            201,
        ),

        (
            "All PI-RNN profiles finite",
            np.all(
                np.isfinite(
                    pirnn
                )
            ),
        ),

        (
            "All SG7A profiles finite",
            np.all(
                np.isfinite(
                    truth
                )
            ),
        ),

        (
            "All profile metrics finite where defined",
            all(
                np.isfinite(
                    row[
                        "profile_L1"
                    ]
                )
                for row
                in profile_rows
            ),
        ),

        (
            "All deployment times summarized",
            len(
                time_rows
            )
            ==
            len(
                times
            ),
        ),

        (
            "Diagnostic classification established",
            diagnosis
            in
            {
                "FRONT_OVERSMOOTHING",
                "THRESHOLD_AVOIDANCE",
                "FRONT_POSITION_AND_SHAPE_BIAS",
                "EARLY_FRONT_ERROR_LOCALIZED",
                "FROZEN_PIRNN_FRONT_SHAPE_ACCEPTABLE",
            },
        ),
    ]

    passed = all(
        status
        for _, status
        in checks
    )

    # =========================================================================
    # PRINT FINAL RESULT
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-8 DIAGNOSTIC VALIDATION"
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
        "\n100-DAY FROZEN PI-RNN FRONT SHAPE"
    )

    print(
        f"  SG7A threshold crossings : "
        f"{row_100['SG7A_threshold_crossings']:,}"
    )

    print(
        f"  PI-RNN threshold crossings: "
        f"{row_100['PI_RNN_threshold_crossings']:,}"
    )

    print(
        f"  PI-RNN threshold gap mean: "
        f"{row_100['PI_RNN_threshold_gap_mean']:.6e}"
    )

    print(
        f"  PI-RNN threshold gap P90 : "
        f"{row_100['PI_RNN_threshold_gap_P90']:.6e}"
    )

    print(
        f"  Width ratio mean         : "
        f"{row_100['width_ratio_mean']:.6f}"
    )

    print(
        f"  Width ratio P90          : "
        f"{row_100['width_ratio_P90']:.6f}"
    )

    print(
        f"  Slope ratio mean         : "
        f"{row_100['slope_ratio_mean']:.6f}"
    )

    print(
        f"  Slope ratio P10          : "
        f"{row_100['slope_ratio_P10']:.6f}"
    )

    print(
        f"  Mean profile L1          : "
        f"{row_100['profile_L1_mean']:.6e}"
    )

    print(
        "\nDIAGNOSTIC FLAGS"
    )

    print(
        f"  SG7A front / PI-RNN none : "
        f"{crossing_missing}"
    )

    print(
        f"  Threshold gap large      : "
        f"{threshold_gap_large}"
    )

    print(
        f"  Width oversmoothed       : "
        f"{width_oversmoothed}"
    )

    print(
        f"  Front slope too weak     : "
        f"{slope_too_weak}"
    )

    print(
        f"  Continuous state good    : "
        f"{continuous_state_good}"
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
        PROFILE_METRICS_FILE,
        profile_rows,
    )

    save_csv(
        TIME_METRICS_FILE,
        time_rows,
    )

    save_csv(
        TOF_BAND_FILE,
        tof_rows,
    )

    # =========================================================================
    # DATABASE
    # =========================================================================

    np.savez_compressed(
        DATABASE_FILE,

        times_days=
            times,

        xi=
            xi,

        terminal_tof_s=
            tau_end_s,

        flow_weights_m3_s=
            flow_weights,

        PI_RNN_saturation=
            pirnn,

        SG7A_saturation=
            truth,
    )

    # =========================================================================
    # PLOTS
    # =========================================================================

    plot_threshold_gap(
        time_rows
    )

    plot_width_ratio(
        time_rows
    )

    plot_slope_ratio(
        time_rows
    )

    index_100 = int(
        np.argmin(
            np.abs(
                times
                -
                EARLY_TIME_DAYS
            )
        )
    )

    plot_representative_100d_profiles(
        xi,
        tau_end_s,
        pirnn[
            index_100
        ],
        truth[
            index_100
        ],
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7B-8",

        "description":
            (
                "Frozen PI-RNN early-front shape audit"
            ),

        "source_workspace":
            str(
                source_workspace
            ),

        "training_performed":
            False,

        "model_parameters_changed":
            False,

        "architecture_changed":
            False,

        "seed_density_changed":
            False,

        "mapback_operator_changed":
            False,

        "validation_threshold_changed":
            False,

        "front_contract": {
            "threshold":
                FRONT_THRESHOLD,

            "low_level":
                LOW_LEVEL,

            "mid_level":
                MID_LEVEL,

            "high_level":
                HIGH_LEVEL,
        },

        "100_day": {
            **row_100,
        },

        "diagnostic_flags": {
            "SG7A_front_PI_RNN_none":
                bool(
                    crossing_missing
                ),

            "threshold_gap_large":
                bool(
                    threshold_gap_large
                ),

            "front_width_oversmoothed":
                bool(
                    width_oversmoothed
                ),

            "front_slope_too_weak":
                bool(
                    slope_too_weak
                ),

            "continuous_state_good":
                bool(
                    continuous_state_good
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
    # OUTPUTS
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
        f"  {PROFILE_METRICS_FILE.name}"
    )

    print(
        f"  {TIME_METRICS_FILE.name}"
    )

    print(
        f"  {TOF_BAND_FILE.name}"
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
        "  V15SG7B8_Threshold_Gap_vs_Time.png"
    )

    print(
        "  V15SG7B8_Front_Width_Ratio.png"
    )

    print(
        "  V15SG7B8_Front_Slope_Ratio.png"
    )

    print(
        "  V15SG7B8_Representative_Profiles_100d.png"
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
            "V15-SG7B-8 AUDIT: PASS"
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
            "V15-SG7B-8 AUDIT: INCOMPLETE"
        )

        print()

        print(
            "Do not retrain the frozen PI-RNN until "
            "the early-front shape diagnosis is internally consistent."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()