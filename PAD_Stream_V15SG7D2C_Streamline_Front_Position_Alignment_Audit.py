from __future__ import annotations

from pathlib import Path
import argparse
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7D-2C
# Streamline Front-Position Alignment Audit
#
# NO TRAINING.
# NO PI-RNN WEIGHT CHANGES.
# NO SEED-DENSITY CHANGE.
# NO MAP-BACK CHANGE.
# NO CONSERVATIVE-PROJECTION CHANGE.
# NO SG7E VALIDATION-THRESHOLD CHANGE.
#
#
# PURPOSE
# -------
#
# SG7D-2B established:
#
#       SUBCELL_FRONT_GEOMETRY_DISAGREEMENT
#
# with the particularly important result at 100 days:
#
#       SG7A partial cells        : 2002
#       PI-RNN partial cells      : 0
#
#       SG7A crossing cells       : 847
#       PI-RNN crossing cells     : 0
#
# SG7D-2C therefore moves upstream from the Cartesian grid and directly
# compares the displacement-front position on each streamline.
#
#
# PRIMARY QUESTIONS
# -----------------
#
# 1. Does each SG7A streamline contain a resolvable S = 0.21 front?
#
# 2. Does the corresponding PI-RNN streamline contain a resolvable front?
#
# 3. If both fronts exist, how far apart are they in:
#
#       xi
#       TOF
#       physical XYZ distance
#
# 4. Are PI-RNN fronts systematically early or late?
#
# 5. Are discrepancies concentrated on particular TOF families or producers?
#
# 6. Was SG7D-2B's "zero PI-RNN crossing cells" caused by a strict
#    sign-change detector rather than a genuine absence of a front?
#
#
# FRONT FINDER
# ------------
#
# This audit deliberately uses a more robust front definition than the
# SG7D-2B strict sign test.
#
# Detection hierarchy:
#
#     1. exact / near-threshold node
#     2. strict sign bracket
#     3. first threshold transition using binary classification
#     4. closest-to-threshold fallback, but ONLY as a diagnostic fallback
#
#
# POSSIBLE DIAGNOSES
# ------------------
#
# PI_RNN_FRONT_POSITION_BIAS
#
# PI_RNN_FRONT_SMOOTHING_OR_THRESHOLD_AVOIDANCE
#
# FRONT_EXTRACTION_DISCRETIZATION_ISSUE
#
# FRONT_POSITION_ALIGNMENT_ACCEPTABLE
#
# MIXED_STREAMLINE_FRONT_DISAGREEMENT
#
# =============================================================================


# =============================================================================
# ROOT / SOURCE WORKSPACE
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
    / "V15_SG7D2C"
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


SG7D2B_SUMMARY = (
    ROOT
    / "output"
    / "V15_SG7D2B"
    / "PAD_Stream_V15SG7D2B_Summary.json"
)


# =============================================================================
# OUTPUTS
# =============================================================================

PROFILE_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7D2C_Streamline_Front_Metrics.csv"
)


TIME_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7D2C_Front_Metrics_By_Time.csv"
)


TOF_BAND_FILE = (
    OUTPUT_DIR
    / "V15SG7D2C_Front_Metrics_By_TOF_Band.csv"
)


PRODUCER_FILE = (
    OUTPUT_DIR
    / "V15SG7D2C_Front_Metrics_By_Producer.csv"
)


DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7D2C_Front_Alignment_Audit.npz"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7D2C_Summary.json"
)


# =============================================================================
# FRONT CONTRACT
# =============================================================================

S_INITIAL = 0.20

PRIMARY_DELTA_S = 0.010

FRONT_THRESHOLD = (
    S_INITIAL
    +
    PRIMARY_DELTA_S
)


# Near-threshold tolerance used to identify a node that effectively lies on
# the front.
FRONT_VALUE_TOL = 5.0e-4


EPS = 1.0e-14


# =============================================================================
# DIAGNOSTIC REFERENCES
#
# These are NOT new freeze gates.
# =============================================================================

XI_MAE_REFERENCE = 0.02

XI_P90_REFERENCE = 0.05

SPATIAL_P90_REFERENCE_M = 10.0

BOTH_FRONT_FRACTION_REFERENCE = 0.90

ONE_SIDED_FRONT_FRACTION_REFERENCE = 0.10


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
# HELPERS
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


def weighted_mean(
    values,
    weights,
):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    weights = np.asarray(
        weights,
        dtype=np.float64,
    )

    if values.size == 0:

        return np.nan

    denominator = float(
        np.sum(
            weights
        )
    )

    if denominator <= EPS:

        return float(
            np.mean(
                values
            )
        )

    return float(
        np.sum(
            values
            *
            weights
        )
        /
        denominator
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
# LOAD SOURCE DATA
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
        SG7D2B_SUMMARY,
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

    sg7d2b_summary = load_json(
        SG7D2B_SUMMARY
    )

    return (
        sg6,
        sg7c,
        sg7d2b_summary,
    )


# =============================================================================
# EXTRACT SG6
# =============================================================================

def extract_sg6(
    sg6,
):

    xyz_key = find_key(
        sg6,
        [
            "xyz_m",
            "transport_xyz",
            "xyz",
            "streamline_xyz",
        ],
        "streamline XYZ",
    )

    tau_key = find_key(
        sg6,
        [
            "tau_s",
            "tof_s",
            "tau",
        ],
        "streamline TOF",
    )

    xi_key = find_key(
        sg6,
        [
            "xi",
            "transport_xi",
        ],
        "streamline normalized coordinate",
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

    tau_end_key = find_key(
        sg6,
        [
            "tau_end_s",
            "terminal_tau_s",
            "terminal_tof_s",
        ],
        "terminal TOF",
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

    xyz = np.asarray(
        sg6[
            xyz_key
        ],
        dtype=np.float64,
    )

    tau_s = np.asarray(
        sg6[
            tau_key
        ],
        dtype=np.float64,
    )

    xi = np.asarray(
        sg6[
            xi_key
        ],
        dtype=np.float64,
    )

    weights = np.asarray(
        sg6[
            weight_key
        ],
        dtype=np.float64,
    )

    tau_end_s = np.asarray(
        sg6[
            tau_end_key
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
        xyz,
        tau_s,
        xi,
        weights,
        tau_end_s,
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
# LINEAR INTERPOLATION OF XYZ / TAU
# =============================================================================

def interpolate_vector(
    values,
    node_index,
    alpha,
):

    return (
        values[
            node_index
        ]
        +
        alpha
        *
        (
            values[
                node_index + 1
            ]
            -
            values[
                node_index
            ]
        )
    )


# =============================================================================
# ROBUST FRONT FINDER
#
# Assumes the displacement state is high upstream and approaches initial
# saturation downstream.
#
# The desired front is therefore the transition between:
#
#       S > FRONT_THRESHOLD
#
# and
#
#       S <= FRONT_THRESHOLD
#
# progressing from injector toward producer.
# =============================================================================

def resolve_front(
    saturation,
    xi,
    tau,
    xyz,
):

    saturation = np.asarray(
        saturation,
        dtype=np.float64,
    )

    n_nodes = int(
        saturation.size
    )

    if n_nodes != len(
        xi
    ):

        raise RuntimeError(
            "Saturation/xi node count mismatch."
        )

    # -------------------------------------------------------------------------
    # Basic range
    # -------------------------------------------------------------------------

    maximum = float(
        np.max(
            saturation
        )
    )

    minimum = float(
        np.min(
            saturation
        )
    )

    # -------------------------------------------------------------------------
    # If the entire profile is one side of threshold, no actual threshold front
    # exists within the sampled streamline domain.
    # -------------------------------------------------------------------------

    any_above = bool(
        np.any(
            saturation
            >
            FRONT_THRESHOLD
        )
    )

    any_below_or_equal = bool(
        np.any(
            saturation
            <=
            FRONT_THRESHOLD
        )
    )

    # -------------------------------------------------------------------------
    # Detect exact / near-threshold nodes.
    # -------------------------------------------------------------------------

    near_indices = np.where(
        np.abs(
            saturation
            -
            FRONT_THRESHOLD
        )
        <=
        FRONT_VALUE_TOL
    )[0]

    # -------------------------------------------------------------------------
    # Strict brackets
    # -------------------------------------------------------------------------

    strict_brackets = []

    for node in range(
        n_nodes
        -
        1
    ):

        a = (
            saturation[
                node
            ]
            -
            FRONT_THRESHOLD
        )

        b = (
            saturation[
                node + 1
            ]
            -
            FRONT_THRESHOLD
        )

        if (
            a
            *
            b
            <
            0.0
        ):

            strict_brackets.append(
                node
            )

    # -------------------------------------------------------------------------
    # Binary transition brackets
    #
    # Includes cases where one endpoint equals threshold.
    # -------------------------------------------------------------------------

    above = (
        saturation
        >
        FRONT_THRESHOLD
    )

    transitions = np.where(
        above[:-1]
        !=
        above[1:]
    )[0]

    # -------------------------------------------------------------------------
    # Prefer strict bracket because interpolation is cleanest.
    # -------------------------------------------------------------------------

    if strict_brackets:

        node = int(
            strict_brackets[-1]
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

        alpha = float(
            (
                FRONT_THRESHOLD
                -
                s0
            )
            /
            (
                s1
                -
                s0
            )
        )

        alpha = float(
            np.clip(
                alpha,
                0.0,
                1.0,
            )
        )

        method = (
            "STRICT_BRACKET"
        )

        resolved = True

    elif transitions.size:

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
        ) > EPS:

            alpha = float(
                (
                    FRONT_THRESHOLD
                    -
                    s0
                )
                /
                (
                    s1
                    -
                    s0
                )
            )

            alpha = float(
                np.clip(
                    alpha,
                    0.0,
                    1.0,
                )
            )

        else:

            alpha = 0.5

        method = (
            "BINARY_TRANSITION"
        )

        resolved = True

    elif (
        near_indices.size
        and
        any_above
    ):

        # Prefer the most downstream near-threshold node.
        near_node = int(
            near_indices[-1]
        )

        if near_node == n_nodes - 1:

            node = (
                n_nodes
                -
                2
            )

            alpha = 1.0

        else:

            node = near_node

            alpha = 0.0

        method = (
            "NEAR_THRESHOLD_NODE"
        )

        resolved = True

    else:

        # ---------------------------------------------------------------------
        # No physical threshold crossing resolved.
        #
        # Store closest point as diagnostic only.
        # ---------------------------------------------------------------------

        closest = int(
            np.argmin(
                np.abs(
                    saturation
                    -
                    FRONT_THRESHOLD
                )
            )
        )

        if closest >= n_nodes - 1:

            node = (
                n_nodes
                -
                2
            )

            alpha = 1.0

        else:

            node = closest

            alpha = 0.0

        method = (
            "CLOSEST_NODE_FALLBACK"
        )

        resolved = False

    # -------------------------------------------------------------------------
    # Position
    # -------------------------------------------------------------------------

    xi_front = float(
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

    tau_front = float(
        interpolate_vector(
            tau,
            node,
            alpha,
        )
    )

    xyz_front = np.asarray(
        interpolate_vector(
            xyz,
            node,
            alpha,
        ),
        dtype=np.float64,
    )

    # -------------------------------------------------------------------------
    # Additional profile diagnostics
    # -------------------------------------------------------------------------

    total_variation = float(
        np.sum(
            np.abs(
                np.diff(
                    saturation
                )
            )
        )
    )

    monotonic_violation = float(
        np.mean(
            np.diff(
                saturation
            )
            >
            1.0e-6
        )
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

    return {
        "resolved":
            bool(
                resolved
            ),

        "method":
            method,

        "node_index":
            int(
                node
            ),

        "alpha":
            float(
                alpha
            ),

        "xi":
            xi_front,

        "tau_s":
            tau_front,

        "xyz":
            xyz_front,

        "profile_min":
            minimum,

        "profile_max":
            maximum,

        "any_above":
            any_above,

        "any_below_or_equal":
            any_below_or_equal,

        "near_threshold_nodes":
            int(
                near_indices.size
            ),

        "strict_crossing_count":
            int(
                len(
                    strict_brackets
                )
            ),

        "binary_transition_count":
            int(
                transitions.size
            ),

        "closest_threshold_distance":
            closest_threshold_distance,

        "total_variation":
            total_variation,

        "monotonic_violation_fraction":
            monotonic_violation,
    }


# =============================================================================
# STREAMLINE CLASSIFICATION
# =============================================================================

def classify_pair(
    truth_front,
    pirnn_front,
):

    if (
        truth_front[
            "resolved"
        ]
        and
        pirnn_front[
            "resolved"
        ]
    ):

        return (
            "BOTH_HAVE_FRONT"
        )

    if (
        truth_front[
            "resolved"
        ]
        and
        not pirnn_front[
            "resolved"
        ]
    ):

        return (
            "SG7A_ONLY_FRONT"
        )

    if (
        not truth_front[
            "resolved"
        ]
        and
        pirnn_front[
            "resolved"
        ]
    ):

        return (
            "PIRNN_ONLY_FRONT"
        )

    return (
        "NEITHER_HAS_FRONT"
    )


# =============================================================================
# BUILD PROFILE ROWS
# =============================================================================

def audit_time(
    time_days,
    xyz,
    tau_s,
    xi,
    weights,
    tau_end_s,
    producer,
    streamline_id,
    pirnn_profiles,
    truth_profiles,
):

    rows = []

    n_streamlines = int(
        xyz.shape[0]
    )

    for streamline in range(
        n_streamlines
    ):

        truth_front = resolve_front(
            truth_profiles[
                streamline
            ],
            xi,
            tau_s[
                streamline
            ],
            xyz[
                streamline
            ],
        )

        pirnn_front = resolve_front(
            pirnn_profiles[
                streamline
            ],
            xi,
            tau_s[
                streamline
            ],
            xyz[
                streamline
            ],
        )

        category = classify_pair(
            truth_front,
            pirnn_front,
        )

        if category == "BOTH_HAVE_FRONT":

            delta_xi = (
                pirnn_front[
                    "xi"
                ]
                -
                truth_front[
                    "xi"
                ]
            )

            delta_tau_s = (
                pirnn_front[
                    "tau_s"
                ]
                -
                truth_front[
                    "tau_s"
                ]
            )

            delta_xyz = (
                pirnn_front[
                    "xyz"
                ]
                -
                truth_front[
                    "xyz"
                ]
            )

            spatial_error_m = float(
                np.linalg.norm(
                    delta_xyz
                )
            )

        else:

            delta_xi = np.nan
            delta_tau_s = np.nan
            spatial_error_m = np.nan

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

                "flow_weight_m3_s":
                    float(
                        weights[
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

                "front_category":
                    category,

                "SG7A_resolved":
                    truth_front[
                        "resolved"
                    ],

                "PI_RNN_resolved":
                    pirnn_front[
                        "resolved"
                    ],

                "SG7A_method":
                    truth_front[
                        "method"
                    ],

                "PI_RNN_method":
                    pirnn_front[
                        "method"
                    ],

                "SG7A_xi_front":
                    truth_front[
                        "xi"
                    ],

                "PI_RNN_xi_front":
                    pirnn_front[
                        "xi"
                    ],

                "delta_xi":
                    delta_xi,

                "absolute_delta_xi":
                    (
                        abs(
                            delta_xi
                        )
                        if np.isfinite(
                            delta_xi
                        )
                        else np.nan
                    ),

                "SG7A_tau_front_days":
                    truth_front[
                        "tau_s"
                    ]
                    /
                    86400.0,

                "PI_RNN_tau_front_days":
                    pirnn_front[
                        "tau_s"
                    ]
                    /
                    86400.0,

                "delta_tau_front_days":
                    (
                        delta_tau_s
                        /
                        86400.0
                        if np.isfinite(
                            delta_tau_s
                        )
                        else np.nan
                    ),

                "absolute_delta_tau_days":
                    (
                        abs(
                            delta_tau_s
                        )
                        /
                        86400.0
                        if np.isfinite(
                            delta_tau_s
                        )
                        else np.nan
                    ),

                "spatial_front_error_m":
                    spatial_error_m,

                "SG7A_strict_crossings":
                    truth_front[
                        "strict_crossing_count"
                    ],

                "PI_RNN_strict_crossings":
                    pirnn_front[
                        "strict_crossing_count"
                    ],

                "SG7A_binary_transitions":
                    truth_front[
                        "binary_transition_count"
                    ],

                "PI_RNN_binary_transitions":
                    pirnn_front[
                        "binary_transition_count"
                    ],

                "SG7A_near_threshold_nodes":
                    truth_front[
                        "near_threshold_nodes"
                    ],

                "PI_RNN_near_threshold_nodes":
                    pirnn_front[
                        "near_threshold_nodes"
                    ],

                "SG7A_closest_threshold_distance":
                    truth_front[
                        "closest_threshold_distance"
                    ],

                "PI_RNN_closest_threshold_distance":
                    pirnn_front[
                        "closest_threshold_distance"
                    ],

                "SG7A_total_variation":
                    truth_front[
                        "total_variation"
                    ],

                "PI_RNN_total_variation":
                    pirnn_front[
                        "total_variation"
                    ],

                "SG7A_monotonic_violation_fraction":
                    truth_front[
                        "monotonic_violation_fraction"
                    ],

                "PI_RNN_monotonic_violation_fraction":
                    pirnn_front[
                        "monotonic_violation_fraction"
                    ],
            }
        )

    return rows


# =============================================================================
# AGGREGATE TIME METRICS
# =============================================================================

def summarize_time(
    time_days,
    rows,
):

    rows_time = [
        row
        for row
        in rows
        if np.isclose(
            row[
                "time_days"
            ],
            time_days,
        )
    ]

    n = int(
        len(
            rows_time
        )
    )

    categories = {
        category:
            sum(
                row[
                    "front_category"
                ]
                ==
                category
                for row
                in rows_time
            )
        for category
        in [
            "BOTH_HAVE_FRONT",
            "SG7A_ONLY_FRONT",
            "PIRNN_ONLY_FRONT",
            "NEITHER_HAS_FRONT",
        ]
    }

    both_rows = [
        row
        for row
        in rows_time
        if row[
            "front_category"
        ]
        ==
        "BOTH_HAVE_FRONT"
    ]

    abs_xi = np.asarray(
        [
            row[
                "absolute_delta_xi"
            ]
            for row
            in both_rows
        ],
        dtype=np.float64,
    )

    abs_tau = np.asarray(
        [
            row[
                "absolute_delta_tau_days"
            ]
            for row
            in both_rows
        ],
        dtype=np.float64,
    )

    spatial = np.asarray(
        [
            row[
                "spatial_front_error_m"
            ]
            for row
            in both_rows
        ],
        dtype=np.float64,
    )

    signed_xi = np.asarray(
        [
            row[
                "delta_xi"
            ]
            for row
            in both_rows
        ],
        dtype=np.float64,
    )

    flow_weights = np.asarray(
        [
            row[
                "flow_weight_m3_s"
            ]
            for row
            in both_rows
        ],
        dtype=np.float64,
    )

    strict_truth = sum(
        row[
            "SG7A_strict_crossings"
        ]
        >
        0
        for row
        in rows_time
    )

    strict_pirnn = sum(
        row[
            "PI_RNN_strict_crossings"
        ]
        >
        0
        for row
        in rows_time
    )

    robust_truth = sum(
        bool(
            row[
                "SG7A_resolved"
            ]
        )
        for row
        in rows_time
    )

    robust_pirnn = sum(
        bool(
            row[
                "PI_RNN_resolved"
            ]
        )
        for row
        in rows_time
    )

    return {
        "time_days":
            float(
                time_days
            ),

        "streamlines":
            n,

        "both_have_front":
            categories[
                "BOTH_HAVE_FRONT"
            ],

        "SG7A_only_front":
            categories[
                "SG7A_ONLY_FRONT"
            ],

        "PI_RNN_only_front":
            categories[
                "PIRNN_ONLY_FRONT"
            ],

        "neither_has_front":
            categories[
                "NEITHER_HAS_FRONT"
            ],

        "both_front_fraction":
            categories[
                "BOTH_HAVE_FRONT"
            ]
            /
            max(
                n,
                1,
            ),

        "one_sided_front_fraction":
            (
                categories[
                    "SG7A_ONLY_FRONT"
                ]
                +
                categories[
                    "PIRNN_ONLY_FRONT"
                ]
            )
            /
            max(
                n,
                1,
            ),

        "SG7A_strict_front_profiles":
            strict_truth,

        "PI_RNN_strict_front_profiles":
            strict_pirnn,

        "SG7A_robust_front_profiles":
            robust_truth,

        "PI_RNN_robust_front_profiles":
            robust_pirnn,

        "front_xi_MAE":
            (
                float(
                    np.mean(
                        abs_xi
                    )
                )
                if abs_xi.size
                else np.nan
            ),

        "front_xi_P50":
            safe_percentile(
                abs_xi,
                50,
            ),

        "front_xi_P90":
            safe_percentile(
                abs_xi,
                90,
            ),

        "front_xi_P95":
            safe_percentile(
                abs_xi,
                95,
            ),

        "front_xi_MAX":
            (
                float(
                    np.max(
                        abs_xi
                    )
                )
                if abs_xi.size
                else np.nan
            ),

        "signed_front_xi_bias":
            (
                float(
                    np.mean(
                        signed_xi
                    )
                )
                if signed_xi.size
                else np.nan
            ),

        "flow_weighted_front_xi_MAE":
            (
                weighted_mean(
                    abs_xi,
                    flow_weights,
                )
                if abs_xi.size
                else np.nan
            ),

        "front_TOF_MAE_days":
            (
                float(
                    np.mean(
                        abs_tau
                    )
                )
                if abs_tau.size
                else np.nan
            ),

        "front_TOF_P90_days":
            safe_percentile(
                abs_tau,
                90,
            ),

        "front_spatial_MAE_m":
            (
                float(
                    np.mean(
                        spatial
                    )
                )
                if spatial.size
                else np.nan
            ),

        "front_spatial_P50_m":
            safe_percentile(
                spatial,
                50,
            ),

        "front_spatial_P90_m":
            safe_percentile(
                spatial,
                90,
            ),

        "front_spatial_P95_m":
            safe_percentile(
                spatial,
                95,
            ),

        "front_spatial_MAX_m":
            (
                float(
                    np.max(
                        spatial
                    )
                )
                if spatial.size
                else np.nan
            ),

        "flow_weighted_spatial_MAE_m":
            (
                weighted_mean(
                    spatial,
                    flow_weights,
                )
                if spatial.size
                else np.nan
            ),
    }


# =============================================================================
# TOF BAND SUMMARY
# =============================================================================

def summarize_tof_bands(
    profile_rows,
):

    result = []

    for time_days in sorted(
        set(
            row[
                "time_days"
            ]
            for row
            in profile_rows
        )
    ):

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

            both = [
                row
                for row
                in selected
                if row[
                    "front_category"
                ]
                ==
                "BOTH_HAVE_FRONT"
            ]

            abs_xi = np.asarray(
                [
                    row[
                        "absolute_delta_xi"
                    ]
                    for row
                    in both
                ],
                dtype=np.float64,
            )

            spatial = np.asarray(
                [
                    row[
                        "spatial_front_error_m"
                    ]
                    for row
                    in both
                ],
                dtype=np.float64,
            )

            result.append(
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

                    "both_have_front":
                        len(
                            both
                        ),

                    "front_xi_MAE":
                        (
                            float(
                                np.mean(
                                    abs_xi
                                )
                            )
                            if abs_xi.size
                            else np.nan
                        ),

                    "front_xi_P90":
                        safe_percentile(
                            abs_xi,
                            90,
                        ),

                    "front_spatial_MAE_m":
                        (
                            float(
                                np.mean(
                                    spatial
                                )
                            )
                            if spatial.size
                            else np.nan
                        ),

                    "front_spatial_P90_m":
                        safe_percentile(
                            spatial,
                            90,
                        ),
                }
            )

    return result


# =============================================================================
# PRODUCER SUMMARY
# =============================================================================

def summarize_producers(
    profile_rows,
):

    result = []

    times = sorted(
        set(
            row[
                "time_days"
            ]
            for row
            in profile_rows
        )
    )

    producers = sorted(
        set(
            row[
                "producer"
            ]
            for row
            in profile_rows
        )
    )

    for time_days in times:

        for producer in producers:

            selected = [
                row
                for row
                in profile_rows
                if (
                    np.isclose(
                        row[
                            "time_days"
                        ],
                        time_days,
                    )
                    and
                    row[
                        "producer"
                    ]
                    ==
                    producer
                )
            ]

            both = [
                row
                for row
                in selected
                if row[
                    "front_category"
                ]
                ==
                "BOTH_HAVE_FRONT"
            ]

            abs_xi = np.asarray(
                [
                    row[
                        "absolute_delta_xi"
                    ]
                    for row
                    in both
                ],
                dtype=np.float64,
            )

            spatial = np.asarray(
                [
                    row[
                        "spatial_front_error_m"
                    ]
                    for row
                    in both
                ],
                dtype=np.float64,
            )

            result.append(
                {
                    "time_days":
                        float(
                            time_days
                        ),

                    "producer":
                        producer,

                    "streamlines":
                        len(
                            selected
                        ),

                    "both_have_front":
                        len(
                            both
                        ),

                    "front_xi_MAE":
                        (
                            float(
                                np.mean(
                                    abs_xi
                                )
                            )
                            if abs_xi.size
                            else np.nan
                        ),

                    "front_xi_P90":
                        safe_percentile(
                            abs_xi,
                            90,
                        ),

                    "front_spatial_MAE_m":
                        (
                            float(
                                np.mean(
                                    spatial
                                )
                            )
                            if spatial.size
                            else np.nan
                        ),

                    "front_spatial_P90_m":
                        safe_percentile(
                            spatial,
                            90,
                        ),
                }
            )

    return result


# =============================================================================
# PLOTS
# =============================================================================

def plot_front_presence(
    time_rows,
):

    times = [
        row[
            "time_days"
        ]
        for row
        in time_rows
    ]

    both = [
        100.0
        *
        row[
            "both_front_fraction"
        ]
        for row
        in time_rows
    ]

    one_sided = [
        100.0
        *
        row[
            "one_sided_front_fraction"
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
        both,
        marker="o",
        label="Both models resolve front",
    )

    ax.plot(
        times,
        one_sided,
        marker="s",
        label="Only one model resolves front",
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        "Streamlines [%]"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-2C\n"
        "Front Resolution by Streamline"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D2C_Front_Resolution_vs_Time.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_front_xi_error(
    time_rows,
):

    times = [
        row[
            "time_days"
        ]
        for row
        in time_rows
    ]

    mae_values = [
        row[
            "front_xi_MAE"
        ]
        for row
        in time_rows
    ]

    p90_values = [
        row[
            "front_xi_P90"
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
        mae_values,
        marker="o",
        label="MAE",
    )

    ax.plot(
        times,
        p90_values,
        marker="s",
        label="P90",
    )

    ax.axhline(
        XI_MAE_REFERENCE,
        linestyle="--",
        label="MAE diagnostic reference",
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        "|Delta xi_front|"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-2C\n"
        "Streamline Front-Position Error"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D2C_Front_Xi_Error_vs_Time.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_spatial_error(
    time_rows,
):

    times = [
        row[
            "time_days"
        ]
        for row
        in time_rows
    ]

    mae_values = [
        row[
            "front_spatial_MAE_m"
        ]
        for row
        in time_rows
    ]

    p90_values = [
        row[
            "front_spatial_P90_m"
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
        mae_values,
        marker="o",
        label="MAE",
    )

    ax.plot(
        times,
        p90_values,
        marker="s",
        label="P90",
    )

    ax.axhline(
        SPATIAL_P90_REFERENCE_M,
        linestyle="--",
        label="Diagnostic reference",
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        "Front displacement [m]"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-2C\n"
        "Physical Front Displacement"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D2C_Front_Spatial_Error_vs_Time.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_100d_scatter(
    profile_rows,
):

    rows = [
        row
        for row
        in profile_rows
        if (
            np.isclose(
                row[
                    "time_days"
                ],
                100.0,
            )
            and
            row[
                "front_category"
            ]
            ==
            "BOTH_HAVE_FRONT"
        )
    ]

    if not rows:

        return

    truth = np.asarray(
        [
            row[
                "SG7A_xi_front"
            ]
            for row
            in rows
        ],
        dtype=np.float64,
    )

    prediction = np.asarray(
        [
            row[
                "PI_RNN_xi_front"
            ]
            for row
            in rows
        ],
        dtype=np.float64,
    )

    fig, ax = plt.subplots(
        figsize=(
            7,
            7,
        )
    )

    ax.scatter(
        truth,
        prediction,
        s=12,
        alpha=0.5,
    )

    lower = float(
        min(
            np.min(
                truth
            ),
            np.min(
                prediction
            ),
        )
    )

    upper = float(
        max(
            np.max(
                truth
            ),
            np.max(
                prediction
            ),
        )
    )

    ax.plot(
        [
            lower,
            upper,
        ],
        [
            lower,
            upper,
        ],
        linestyle="--",
    )

    ax.set_xlabel(
        "SG7A xi_front"
    )

    ax.set_ylabel(
        "PI-RNN xi_front"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-2C\n"
        "100-Day Front Alignment"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D2C_Front_Xi_Scatter_100d.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_100d_error_vs_tof(
    profile_rows,
):

    rows = [
        row
        for row
        in profile_rows
        if (
            np.isclose(
                row[
                    "time_days"
                ],
                100.0,
            )
            and
            row[
                "front_category"
            ]
            ==
            "BOTH_HAVE_FRONT"
        )
    ]

    if not rows:

        return

    tof = [
        row[
            "terminal_TOF_days"
        ]
        for row
        in rows
    ]

    error = [
        row[
            "absolute_delta_xi"
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

    ax.scatter(
        tof,
        error,
        s=12,
        alpha=0.5,
    )

    ax.set_xlabel(
        "Terminal streamline TOF [days]"
    )

    ax.set_ylabel(
        "|Delta xi_front|"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-2C\n"
        "100-Day Front Error vs Streamline TOF"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D2C_Front_Error_vs_TOF_100d.png",
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
            "PAD-Stream V15-SG7D-2C "
            "streamline front-position alignment audit."
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

    # =========================================================================
    # HEADER
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7D-2C"
    )

    print(
        "Streamline Front-Position Alignment Audit"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    print(
        "NO PI-RNN PARAMETERS WILL BE CHANGED."
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
        sg7d2b_summary,
    ) = load_inputs(
        source_workspace
    )

    if (
        sg7d2b_summary.get(
            "diagnosis"
        )
        !=
        "SUBCELL_FRONT_GEOMETRY_DISAGREEMENT"
    ):

        raise RuntimeError(
            "SG7D-2C requires SG7D-2B diagnosis:\n"
            "SUBCELL_FRONT_GEOMETRY_DISAGREEMENT"
        )

    (
        xyz,
        tau_s,
        xi,
        flow_weights,
        tau_end_s,
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

    # =========================================================================
    # SOURCE
    # =========================================================================

    print(
        "\nSOURCE DATABASE"
    )

    print(
        f"  Streamlines             : "
        f"{xyz.shape[0]:,}"
    )

    print(
        f"  Nodes                   : "
        f"{xyz.shape[1]}"
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
        f"  Near-threshold tolerance: "
        f"{FRONT_VALUE_TOL:.1e}"
    )

    # =========================================================================
    # SHAPE VALIDATION
    # =========================================================================

    expected_shape = (
        len(
            times
        ),
        xyz.shape[0],
        xyz.shape[1],
    )

    if pirnn.shape != expected_shape:

        raise RuntimeError(
            "Unexpected PI-RNN saturation shape.\n"
            f"Expected: {expected_shape}\n"
            f"Observed: {pirnn.shape}"
        )

    if truth.shape != expected_shape:

        raise RuntimeError(
            "Unexpected SG7A saturation shape."
        )

    # =========================================================================
    # PROFILE AUDIT
    # =========================================================================

    profile_rows = []

    print(
        "\n"
        + "=" * 78
    )

    print(
        "STREAMLINE FRONT ALIGNMENT"
    )

    print(
        "=" * 78
    )

    for time_index, time_days in enumerate(
        times
    ):

        rows = audit_time(
            time_days,
            xyz,
            tau_s,
            xi,
            flow_weights,
            tau_end_s,
            producer,
            streamline_id,
            pirnn[
                time_index
            ],
            truth[
                time_index
            ],
        )

        profile_rows.extend(
            rows
        )

        summary = summarize_time(
            time_days,
            profile_rows,
        )

        print(
            f"\n  t = {time_days:.1f} days"
        )

        print(
            f"    SG7A strict fronts     : "
            f"{summary['SG7A_strict_front_profiles']:,}"
        )

        print(
            f"    PI-RNN strict fronts   : "
            f"{summary['PI_RNN_strict_front_profiles']:,}"
        )

        print(
            f"    SG7A robust fronts     : "
            f"{summary['SG7A_robust_front_profiles']:,}"
        )

        print(
            f"    PI-RNN robust fronts   : "
            f"{summary['PI_RNN_robust_front_profiles']:,}"
        )

        print(
            f"    Both fronts resolved   : "
            f"{summary['both_have_front']:,}"
        )

        print(
            f"    SG7A-only fronts       : "
            f"{summary['SG7A_only_front']:,}"
        )

        print(
            f"    PI-RNN-only fronts     : "
            f"{summary['PI_RNN_only_front']:,}"
        )

        print(
            f"    Neither                : "
            f"{summary['neither_has_front']:,}"
        )

        print(
            f"    Front xi MAE           : "
            f"{summary['front_xi_MAE']:.6e}"
        )

        print(
            f"    Front xi P90           : "
            f"{summary['front_xi_P90']:.6e}"
        )

        print(
            f"    Signed xi bias         : "
            f"{summary['signed_front_xi_bias']:.6e}"
        )

        print(
            f"    Spatial MAE            : "
            f"{summary['front_spatial_MAE_m']:.6f} m"
        )

        print(
            f"    Spatial P90            : "
            f"{summary['front_spatial_P90_m']:.6f} m"
        )

    # =========================================================================
    # TIME SUMMARIES
    # =========================================================================

    time_rows = [
        summarize_time(
            time_days,
            profile_rows,
        )
        for time_days
        in times
    ]

    tof_band_rows = summarize_tof_bands(
        profile_rows
    )

    producer_rows = summarize_producers(
        profile_rows
    )

    # =========================================================================
    # 100-DAY AUTHORITATIVE DIAGNOSTIC
    # =========================================================================

    row_100 = next(
        row
        for row
        in time_rows
        if np.isclose(
            row[
                "time_days"
            ],
            100.0,
        )
    )

    both_front_fraction_good = (
        row_100[
            "both_front_fraction"
        ]
        >=
        BOTH_FRONT_FRACTION_REFERENCE
    )

    one_sided_low = (
        row_100[
            "one_sided_front_fraction"
        ]
        <
        ONE_SIDED_FRONT_FRACTION_REFERENCE
    )

    xi_mae_good = (
        np.isfinite(
            row_100[
                "front_xi_MAE"
            ]
        )
        and
        row_100[
            "front_xi_MAE"
        ]
        <
        XI_MAE_REFERENCE
    )

    xi_p90_good = (
        np.isfinite(
            row_100[
                "front_xi_P90"
            ]
        )
        and
        row_100[
            "front_xi_P90"
        ]
        <
        XI_P90_REFERENCE
    )

    spatial_p90_good = (
        np.isfinite(
            row_100[
                "front_spatial_P90_m"
            ]
        )
        and
        row_100[
            "front_spatial_P90_m"
        ]
        <
        SPATIAL_P90_REFERENCE_M
    )

    strict_crossing_gap = abs(
        row_100[
            "SG7A_strict_front_profiles"
        ]
        -
        row_100[
            "PI_RNN_strict_front_profiles"
        ]
    )

    robust_crossing_gap = abs(
        row_100[
            "SG7A_robust_front_profiles"
        ]
        -
        row_100[
            "PI_RNN_robust_front_profiles"
        ]
    )

    strict_gap_large = (
        strict_crossing_gap
        >
        0.20
        *
        xyz.shape[0]
    )

    robust_gap_small = (
        robust_crossing_gap
        <
        0.10
        *
        xyz.shape[0]
    )

    # =========================================================================
    # DIAGNOSIS
    # =========================================================================

    if (
        strict_gap_large
        and
        robust_gap_small
        and
        xi_mae_good
        and
        xi_p90_good
    ):

        diagnosis = (
            "FRONT_EXTRACTION_DISCRETIZATION_ISSUE"
        )

        recommendation = (
            "The apparent absence of PI-RNN threshold crossings is largely "
            "caused by the strict crossing definition. Robust front positions "
            "align adequately with SG7A. Update downstream front diagnostics "
            "without retraining the PI-RNN."
        )

        next_milestone = (
            "V15-SG7D-2D — Robust Front-Aware "
            "Eulerian Reconstruction Validation"
        )

    elif (
        both_front_fraction_good
        and
        xi_mae_good
        and
        xi_p90_good
        and
        spatial_p90_good
    ):

        diagnosis = (
            "FRONT_POSITION_ALIGNMENT_ACCEPTABLE"
        )

        recommendation = (
            "PI-RNN and SG7A streamline fronts are spatially aligned. The "
            "remaining Eulerian mismatch is caused primarily by converting "
            "aligned Lagrangian fronts onto Cartesian cells."
        )

        next_milestone = (
            "V15-SG7D-3 — Constrained Front-Aware "
            "Map-Back Candidate Validation"
        )

    elif (
        row_100[
            "one_sided_front_fraction"
        ]
        >=
        ONE_SIDED_FRONT_FRACTION_REFERENCE
    ):

        diagnosis = (
            "PI_RNN_FRONT_SMOOTHING_OR_THRESHOLD_AVOIDANCE"
        )

        recommendation = (
            "A substantial fraction of SG7A and PI-RNN profiles do not share "
            "a resolvable threshold front. Audit the PI-RNN front shape and "
            "training target near the early displacement front before "
            "modifying the grid reconstruction."
        )

        next_milestone = (
            "V15-SG7B-8 — Frozen PI-RNN "
            "Early-Front Shape Audit"
        )

    elif (
        not xi_mae_good
        or
        not xi_p90_good
        or
        not spatial_p90_good
    ):

        diagnosis = (
            "PI_RNN_FRONT_POSITION_BIAS"
        )

        recommendation = (
            "Both models contain recognizable fronts, but PI-RNN front "
            "location is systematically displaced from SG7A. The next "
            "milestone should audit early-front transport accuracy directly."
        )

        next_milestone = (
            "V15-SG7B-8 — Frozen PI-RNN "
            "Early-Front Shape Audit"
        )

    else:

        diagnosis = (
            "MIXED_STREAMLINE_FRONT_DISAGREEMENT"
        )

        recommendation = (
            "The front discrepancy contains both detection and spatial "
            "alignment effects. Audit the frozen PI-RNN early-front shape "
            "before changing SG7D."
        )

        next_milestone = (
            "V15-SG7B-8 — Frozen PI-RNN "
            "Early-Front Shape Audit"
        )

    # =========================================================================
    # VALIDATION
    # =========================================================================

    checks = [
        (
            "Incoming SG7D-2B diagnosis reproduced",
            (
                sg7d2b_summary.get(
                    "diagnosis"
                )
                ==
                "SUBCELL_FRONT_GEOMETRY_DISAGREEMENT"
            ),
        ),

        (
            "2662 streamline source loaded",
            xyz.shape[0]
            ==
            2662,
        ),

        (
            "201 streamline nodes loaded",
            xyz.shape[1]
            ==
            201,
        ),

        (
            "All geometry finite",
            (
                np.all(
                    np.isfinite(
                        xyz
                    )
                )
                and
                np.all(
                    np.isfinite(
                        tau_s
                    )
                )
            ),
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
            "Every profile classified",
            len(
                profile_rows
            )
            ==
            (
                len(
                    times
                )
                *
                xyz.shape[0]
            ),
        ),

        (
            "All robust front positions finite",
            all(
                (
                    np.isfinite(
                        row[
                            "SG7A_xi_front"
                        ]
                    )
                    and
                    np.isfinite(
                        row[
                            "PI_RNN_xi_front"
                        ]
                    )
                )
                for row
                in profile_rows
            ),
        ),

        (
            "Diagnostic classification established",
            diagnosis
            in
            {
                "PI_RNN_FRONT_POSITION_BIAS",
                "PI_RNN_FRONT_SMOOTHING_OR_THRESHOLD_AVOIDANCE",
                "FRONT_EXTRACTION_DISCRETIZATION_ISSUE",
                "FRONT_POSITION_ALIGNMENT_ACCEPTABLE",
                "MIXED_STREAMLINE_FRONT_DISAGREEMENT",
            },
        ),
    ]

    passed = all(
        status
        for _, status
        in checks
    )

    # =========================================================================
    # PRINT FINAL DIAGNOSTIC
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7D-2C DIAGNOSTIC VALIDATION"
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
        "\n100-DAY FRONT ALIGNMENT"
    )

    print(
        f"  SG7A strict fronts       : "
        f"{row_100['SG7A_strict_front_profiles']:,}"
    )

    print(
        f"  PI-RNN strict fronts     : "
        f"{row_100['PI_RNN_strict_front_profiles']:,}"
    )

    print(
        f"  SG7A robust fronts       : "
        f"{row_100['SG7A_robust_front_profiles']:,}"
    )

    print(
        f"  PI-RNN robust fronts     : "
        f"{row_100['PI_RNN_robust_front_profiles']:,}"
    )

    print(
        f"  Both fronts resolved     : "
        f"{row_100['both_have_front']:,}"
    )

    print(
        f"  Both-front fraction      : "
        f"{row_100['both_front_fraction']:.3%}"
    )

    print(
        f"  SG7A-only fronts         : "
        f"{row_100['SG7A_only_front']:,}"
    )

    print(
        f"  PI-RNN-only fronts       : "
        f"{row_100['PI_RNN_only_front']:,}"
    )

    print(
        f"  One-sided fraction       : "
        f"{row_100['one_sided_front_fraction']:.3%}"
    )

    print(
        f"  Front xi MAE             : "
        f"{row_100['front_xi_MAE']:.6e}"
    )

    print(
        f"  Front xi P90             : "
        f"{row_100['front_xi_P90']:.6e}"
    )

    print(
        f"  Front xi MAX             : "
        f"{row_100['front_xi_MAX']:.6e}"
    )

    print(
        f"  Signed xi bias           : "
        f"{row_100['signed_front_xi_bias']:.6e}"
    )

    print(
        f"  Flow-weighted xi MAE     : "
        f"{row_100['flow_weighted_front_xi_MAE']:.6e}"
    )

    print(
        f"  Front TOF MAE            : "
        f"{row_100['front_TOF_MAE_days']:.6f} days"
    )

    print(
        f"  Front TOF P90            : "
        f"{row_100['front_TOF_P90_days']:.6f} days"
    )

    print(
        f"  Spatial front MAE        : "
        f"{row_100['front_spatial_MAE_m']:.6f} m"
    )

    print(
        f"  Spatial front P90        : "
        f"{row_100['front_spatial_P90_m']:.6f} m"
    )

    print(
        f"  Spatial front MAX        : "
        f"{row_100['front_spatial_MAX_m']:.6f} m"
    )

    print(
        "\nDIAGNOSTIC FLAGS"
    )

    print(
        f"  Strict crossing gap large: "
        f"{strict_gap_large}"
    )

    print(
        f"  Robust crossing gap small: "
        f"{robust_gap_small}"
    )

    print(
        f"  Both-front fraction good : "
        f"{both_front_fraction_good}"
    )

    print(
        f"  One-sided fronts low     : "
        f"{one_sided_low}"
    )

    print(
        f"  xi MAE acceptable        : "
        f"{xi_mae_good}"
    )

    print(
        f"  xi P90 acceptable        : "
        f"{xi_p90_good}"
    )

    print(
        f"  Spatial P90 acceptable   : "
        f"{spatial_p90_good}"
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
        tof_band_rows,
    )

    save_csv(
        PRODUCER_FILE,
        producer_rows,
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

        tau_s=
            tau_s,

        xyz_m=
            xyz,

        flow_weights_m3_s=
            flow_weights,

        terminal_tof_s=
            tau_end_s,

        PI_RNN_saturation=
            pirnn,

        SG7A_saturation=
            truth,
    )

    # =========================================================================
    # PLOTS
    # =========================================================================

    plot_front_presence(
        time_rows
    )

    plot_front_xi_error(
        time_rows
    )

    plot_spatial_error(
        time_rows
    )

    plot_100d_scatter(
        profile_rows
    )

    plot_100d_error_vs_tof(
        profile_rows
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7D-2C",

        "description":
            (
                "Streamline-level PI-RNN / SG7A "
                "front-position alignment audit"
            ),

        "source_workspace":
            str(
                source_workspace
            ),

        "training_performed":
            False,

        "PI_RNN_parameters_changed":
            False,

        "seed_density_changed":
            False,

        "mapback_operator_changed":
            False,

        "projection_operator_changed":
            False,

        "validation_threshold_changed":
            False,

        "front_contract": {
            "threshold":
                FRONT_THRESHOLD,

            "near_threshold_tolerance":
                FRONT_VALUE_TOL,

            "detection_methods": [
                "STRICT_BRACKET",
                "BINARY_TRANSITION",
                "NEAR_THRESHOLD_NODE",
                "CLOSEST_NODE_FALLBACK",
            ],
        },

        "100_day": {
            **row_100,
        },

        "diagnostic_flags": {
            "strict_crossing_gap_large":
                bool(
                    strict_gap_large
                ),

            "robust_crossing_gap_small":
                bool(
                    robust_gap_small
                ),

            "both_front_fraction_good":
                bool(
                    both_front_fraction_good
                ),

            "one_sided_front_fraction_low":
                bool(
                    one_sided_low
                ),

            "xi_MAE_acceptable":
                bool(
                    xi_mae_good
                ),

            "xi_P90_acceptable":
                bool(
                    xi_p90_good
                ),

            "spatial_P90_acceptable":
                bool(
                    spatial_p90_good
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
    # OUTPUT LIST
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
        f"  {PRODUCER_FILE.name}"
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
        "  V15SG7D2C_Front_Resolution_vs_Time.png"
    )

    print(
        "  V15SG7D2C_Front_Xi_Error_vs_Time.png"
    )

    print(
        "  V15SG7D2C_Front_Spatial_Error_vs_Time.png"
    )

    print(
        "  V15SG7D2C_Front_Xi_Scatter_100d.png"
    )

    print(
        "  V15SG7D2C_Front_Error_vs_TOF_100d.png"
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
            "V15-SG7D-2C AUDIT: PASS"
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
            "V15-SG7D-2C AUDIT: INCOMPLETE"
        )

        print()

        print(
            "Do not change SG7B or SG7D until "
            "the front-alignment audit is internally consistent."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()