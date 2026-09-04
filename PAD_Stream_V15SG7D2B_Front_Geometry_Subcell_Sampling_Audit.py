from __future__ import annotations

from pathlib import Path
import argparse
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7D-2B
# Front Geometry / Subcell Sampling Audit
#
# NO TRAINING.
# NO SEED-DENSITY CHANGE.
# NO CHANGE TO AUTHORITATIVE q*Delta-tau MAP-BACK.
# NO CHANGE TO CONSERVATIVE PROJECTION.
# NO CHANGE TO SG7E PLUME THRESHOLD.
#
#
# PURPOSE
# -------
#
# SG7D-1 diagnosed:
#
#       FRONT_CLASSIFICATION_DISAGREEMENT
#
# SG7D-2 then showed:
#
#       FRONT_DISAGREEMENT_NOT_CONTROLLED_BY_CELL_AVERAGING
#
# Therefore SG7D-2B asks whether the remaining early-time plume discrepancy
# is caused by SUBCELL FRONT GEOMETRY.
#
#
# The accepted SG7D state assigns one saturation value to each Cartesian cell.
#
# A sharp front, however, may cut through a cell:
#
#               swept
#       ---------------------
#               |           |
#               |   FRONT   |
#               |      /    |
#               |     /     |
#               |    /      |
#               |           |
#       ---------------------
#              unswept
#
#
# A cell can therefore be partially swept even when its averaged saturation
# falls slightly above or below the SG7E threshold.
#
#
# THIS MILESTONE COMPUTES
# -----------------------
#
#       1. exact linear threshold crossing within each subsegment
#       2. fractional swept length
#       3. fractional swept q*Delta-tau
#       4. threshold crossing count per cell
#       5. crossing distance from cell center
#       6. binary plume-volume error
#       7. fractional swept-volume error
#       8. soft/fractional IoU
#       9. relationship between binary mismatch and partial sweep
#
#
# POSSIBLE DIAGNOSES
# ------------------
#
# SUBCELL_PARTIAL_SWEEP_EXPLAINS_BINARY_MISMATCH
#
# SUBCELL_FRONT_GEOMETRY_DISAGREEMENT
#
# STREAMLINE_SUPPORT_GEOMETRY_LIMITATION
#
# BINARY_PLUME_METRIC_DOMINANT
#
# FRONT_GEOMETRY_NOT_PRIMARY_LIMITATION
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
    / "V15_SG7D2B"
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


SG7D1_SUMMARY = (
    ROOT
    / "output"
    / "V15_SG7D1"
    / "PAD_Stream_V15SG7D1_Summary.json"
)


SG7D2_SUMMARY = (
    ROOT
    / "output"
    / "V15_SG7D2"
    / "PAD_Stream_V15SG7D2_Summary.json"
)


# =============================================================================
# OUTPUT FILES
# =============================================================================

GLOBAL_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7D2B_Global_Subcell_Metrics.csv"
)


CELL_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7D2B_100d_Cell_Front_Geometry.csv"
)


LAYER_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7D2B_100d_Layer_Metrics.csv"
)


MISMATCH_FILE = (
    OUTPUT_DIR
    / "V15SG7D2B_100d_Mismatch_Cell_Metrics.csv"
)


DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7D2B_Subcell_Front_Audit.npz"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7D2B_Summary.json"
)


# =============================================================================
# GRID
# =============================================================================

NZ = 15
NY = 50
NX = 50

GRID_SHAPE = (
    NZ,
    NY,
    NX,
)


N_CELLS = (
    NZ
    *
    NY
    *
    NX
)


DX_M = 6.0960
DY_M = 6.0960
DZ_M = 1.2192


# =============================================================================
# SATURATION / FRONT
# =============================================================================

S_INITIAL = 0.20

S_MIN = 0.20
S_MAX = 0.80


PRIMARY_DELTA_S = 0.010

PRIMARY_THRESHOLD = (
    S_INITIAL
    +
    PRIMARY_DELTA_S
)


EPS = 1.0e-14


# =============================================================================
# PARTIAL-SWEEP DIAGNOSTIC RANGE
#
# Cells whose fractional swept occupancy lies well away from 0 and 1 are
# genuinely cut by the front at subcell scale.
# =============================================================================

PARTIAL_SWEEP_MIN = 0.05
PARTIAL_SWEEP_MAX = 0.95


STRONGLY_PARTIAL_MIN = 0.20
STRONGLY_PARTIAL_MAX = 0.80


# =============================================================================
# DIAGNOSTIC REFERENCES
#
# These do NOT alter SG7E acceptance gates.
# =============================================================================

FRACTIONAL_VOLUME_ERROR_REFERENCE = 0.10

MISMATCH_PARTIAL_SHARE_REFERENCE = 0.60

SOFT_IOU_REFERENCE = 0.90

DIRECT_SUPPORT_REFERENCE = 0.75


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


def soft_iou(
    a,
    b,
):

    a = np.asarray(
        a,
        dtype=np.float64,
    )

    b = np.asarray(
        b,
        dtype=np.float64,
    )

    numerator = float(
        np.sum(
            np.minimum(
                a,
                b,
            )
        )
    )

    denominator = float(
        np.sum(
            np.maximum(
                a,
                b,
            )
        )
    )

    if denominator <= EPS:

        return 1.0

    return (
        numerator
        /
        denominator
    )


def flatten_cell(
    k,
    j,
    i,
):

    return (
        k
        *
        NY
        *
        NX
        +
        j
        *
        NX
        +
        i
    )


def unflatten_cell(
    flat,
):

    k = (
        flat
        //
        (
            NY
            *
            NX
        )
    )

    remainder = (
        flat
        %
        (
            NY
            *
            NX
        )
    )

    j = (
        remainder
        //
        NX
    )

    i = (
        remainder
        %
        NX
    )

    return (
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


def point_to_cell(
    point,
):

    x, y, z = point

    i = int(
        np.floor(
            x
            /
            DX_M
        )
    )

    j = int(
        np.floor(
            y
            /
            DY_M
        )
    )

    k = int(
        np.floor(
            z
            /
            DZ_M
        )
    )

    i = min(
        max(
            i,
            0,
        ),
        NX - 1,
    )

    j = min(
        max(
            j,
            0,
        ),
        NY - 1,
    )

    k = min(
        max(
            k,
            0,
        ),
        NZ - 1,
    )

    return (
        k,
        j,
        i,
    )


def cell_center(
    flat_index,
):

    (
        k,
        j,
        i,
    ) = unflatten_cell(
        flat_index
    )

    return np.asarray(
        [
            (
                i
                +
                0.5
            )
            *
            DX_M,

            (
                j
                +
                0.5
            )
            *
            DY_M,

            (
                k
                +
                0.5
            )
            *
            DZ_M,
        ],
        dtype=np.float64,
    )


# =============================================================================
# INPUT LOAD
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
        SG7D1_SUMMARY,
        SG7D2_SUMMARY,
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

    sg7d1 = load_json(
        SG7D1_SUMMARY
    )

    sg7d2 = load_json(
        SG7D2_SUMMARY
    )

    return (
        sg6,
        sg7c,
        sg7d1,
        sg7d2,
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
        "streamline coordinates",
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

    weight_key = find_key(
        sg6,
        [
            "weights_m3_s",
            "weights",
            "flow_weights_m3_s",
        ],
        "streamline flow weights",
    )

    xyz = np.asarray(
        sg6[
            xyz_key
        ],
        dtype=np.float64,
    )

    tau = np.asarray(
        sg6[
            tau_key
        ],
        dtype=np.float64,
    )

    weights = np.asarray(
        sg6[
            weight_key
        ],
        dtype=np.float64,
    )

    return (
        xyz,
        tau,
        weights,
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
# BUILD CARTESIAN GEOMETRY ONCE
#
# Store the original streamline segment index and the two local alpha values
# defining each Cartesian subsegment.
#
# Saturation can then be evaluated later for any deployment time.
# =============================================================================

def split_alpha_values(
    p0,
    p1,
):

    p0 = np.asarray(
        p0,
        dtype=np.float64,
    )

    p1 = np.asarray(
        p1,
        dtype=np.float64,
    )

    direction = (
        p1
        -
        p0
    )

    alpha_values = [
        0.0,
        1.0,
    ]

    spacings = [
        (
            0,
            DX_M,
            NX,
        ),

        (
            1,
            DY_M,
            NY,
        ),

        (
            2,
            DZ_M,
            NZ,
        ),
    ]

    for (
        axis,
        spacing,
        n_cells,
    ) in spacings:

        if abs(
            direction[
                axis
            ]
        ) <= EPS:

            continue

        for plane_index in range(
            1,
            n_cells,
        ):

            plane = (
                plane_index
                *
                spacing
            )

            alpha = (
                plane
                -
                p0[
                    axis
                ]
            ) / direction[
                axis
            ]

            if (
                EPS
                <
                alpha
                <
                1.0
                -
                EPS
            ):

                alpha_values.append(
                    float(
                        alpha
                    )
                )

    return np.asarray(
        sorted(
            set(
                np.round(
                    alpha_values,
                    14,
                )
            )
        ),
        dtype=np.float64,
    )


def build_geometry_database(
    xyz,
    tau,
    flow_weights,
):

    cell_index = []

    streamline_index = []

    node_index = []

    alpha0_values = []

    alpha1_values = []

    length_values = []

    dtau_values = []

    qdtau_values = []

    n_streamlines = (
        xyz.shape[0]
    )

    n_nodes = (
        xyz.shape[1]
    )

    for streamline in range(
        n_streamlines
    ):

        q = float(
            flow_weights[
                streamline
            ]
        )

        for node in range(
            n_nodes
            -
            1
        ):

            p0 = np.asarray(
                xyz[
                    streamline,
                    node
                ],
                dtype=np.float64,
            )

            p1 = np.asarray(
                xyz[
                    streamline,
                    node + 1
                ],
                dtype=np.float64,
            )

            direction = (
                p1
                -
                p0
            )

            alpha_values = (
                split_alpha_values(
                    p0,
                    p1,
                )
            )

            tau0 = float(
                tau[
                    streamline,
                    node
                ]
            )

            tau1 = float(
                tau[
                    streamline,
                    node + 1
                ]
            )

            delta_tau_segment = (
                tau1
                -
                tau0
            )

            for index in range(
                len(
                    alpha_values
                )
                -
                1
            ):

                a0 = float(
                    alpha_values[
                        index
                    ]
                )

                a1 = float(
                    alpha_values[
                        index + 1
                    ]
                )

                amid = (
                    0.5
                    *
                    (
                        a0
                        +
                        a1
                    )
                )

                pa = (
                    p0
                    +
                    a0
                    *
                    direction
                )

                pb = (
                    p0
                    +
                    a1
                    *
                    direction
                )

                pm = (
                    p0
                    +
                    amid
                    *
                    direction
                )

                (
                    k,
                    j,
                    i,
                ) = point_to_cell(
                    pm
                )

                length = float(
                    np.linalg.norm(
                        pb
                        -
                        pa
                    )
                )

                dtau = float(
                    delta_tau_segment
                    *
                    (
                        a1
                        -
                        a0
                    )
                )

                cell_index.append(
                    flatten_cell(
                        k,
                        j,
                        i,
                    )
                )

                streamline_index.append(
                    streamline
                )

                node_index.append(
                    node
                )

                alpha0_values.append(
                    a0
                )

                alpha1_values.append(
                    a1
                )

                length_values.append(
                    length
                )

                dtau_values.append(
                    dtau
                )

                qdtau_values.append(
                    q
                    *
                    dtau
                )

    return {
        "cell_index":
            np.asarray(
                cell_index,
                dtype=np.int32,
            ),

        "streamline_index":
            np.asarray(
                streamline_index,
                dtype=np.int32,
            ),

        "node_index":
            np.asarray(
                node_index,
                dtype=np.int16,
            ),

        "alpha0":
            np.asarray(
                alpha0_values,
                dtype=np.float64,
            ),

        "alpha1":
            np.asarray(
                alpha1_values,
                dtype=np.float64,
            ),

        "length":
            np.asarray(
                length_values,
                dtype=np.float64,
            ),

        "dtau":
            np.asarray(
                dtau_values,
                dtype=np.float64,
            ),

        "qdtau":
            np.asarray(
                qdtau_values,
                dtype=np.float64,
            ),
    }


# =============================================================================
# SATURATION AT SUBSEGMENT ENDPOINTS
# =============================================================================

def evaluate_subsegment_endpoints(
    geometry,
    streamline_saturation,
):

    stream = (
        geometry[
            "streamline_index"
        ]
    )

    node = (
        geometry[
            "node_index"
        ]
    )

    alpha0 = (
        geometry[
            "alpha0"
        ]
    )

    alpha1 = (
        geometry[
            "alpha1"
        ]
    )

    s_node0 = (
        streamline_saturation[
            stream,
            node
        ]
    )

    s_node1 = (
        streamline_saturation[
            stream,
            node + 1
        ]
    )

    delta_s = (
        s_node1
        -
        s_node0
    )

    s0 = (
        s_node0
        +
        alpha0
        *
        delta_s
    )

    s1 = (
        s_node0
        +
        alpha1
        *
        delta_s
    )

    smid = (
        0.5
        *
        (
            s0
            +
            s1
        )
    )

    return (
        s0,
        s1,
        smid,
    )


# =============================================================================
# EXACT LINEAR FRACTION ABOVE THRESHOLD
#
# s(u) = s0 + u(s1-s0), 0 <= u <= 1
#
# Return fraction of the subsegment satisfying:
#
#       s(u) > threshold
# =============================================================================

def fraction_above_threshold(
    s0,
    s1,
    threshold,
):

    s0 = np.asarray(
        s0,
        dtype=np.float64,
    )

    s1 = np.asarray(
        s1,
        dtype=np.float64,
    )

    result = np.zeros_like(
        s0,
        dtype=np.float64,
    )

    both_above = (
        (s0 > threshold)
        &
        (s1 > threshold)
    )

    both_below = (
        (s0 <= threshold)
        &
        (s1 <= threshold)
    )

    result[
        both_above
    ] = 1.0

    mixed = (
        ~both_above
        &
        ~both_below
    )

    if np.any(
        mixed
    ):

        s0m = (
            s0[
                mixed
            ]
        )

        s1m = (
            s1[
                mixed
            ]
        )

        ds = (
            s1m
            -
            s0m
        )

        u_cross = (
            threshold
            -
            s0m
        ) / ds

        increasing = (
            ds
            >
            0.0
        )

        fraction = np.empty_like(
            u_cross
        )

        fraction[
            increasing
        ] = (
            1.0
            -
            u_cross[
                increasing
            ]
        )

        fraction[
            ~increasing
        ] = (
            u_cross[
                ~increasing
            ]
        )

        result[
            mixed
        ] = np.clip(
            fraction,
            0.0,
            1.0,
        )

    return result


# =============================================================================
# CROSSING DETECTION
# =============================================================================

def crossing_mask(
    s0,
    s1,
    threshold,
):

    return (
        (
            s0
            -
            threshold
        )
        *
        (
            s1
            -
            threshold
        )
        <
        0.0
    )


# =============================================================================
# CELL AGGREGATION
# =============================================================================

def weighted_cell_average(
    cell_index,
    values,
    weights,
    fallback,
):

    numerator = np.bincount(
        cell_index,
        weights=(
            values
            *
            weights
        ),
        minlength=N_CELLS,
    )

    denominator = np.bincount(
        cell_index,
        weights=weights,
        minlength=N_CELLS,
    )

    output = np.full(
        N_CELLS,
        fallback,
        dtype=np.float64,
    )

    supported = (
        denominator
        >
        EPS
    )

    output[
        supported
    ] = (
        numerator[
            supported
        ]
        /
        denominator[
            supported
        ]
    )

    return (
        output,
        denominator,
    )


def cell_counts(
    cell_index,
):

    return np.bincount(
        cell_index,
        minlength=N_CELLS,
    ).astype(
        np.int32
    )


# =============================================================================
# CROSSING DISTANCE FROM CELL CENTER
# =============================================================================

def crossing_distance_statistics(
    geometry,
    xyz,
    s0,
    s1,
):

    cross = crossing_mask(
        s0,
        s1,
        PRIMARY_THRESHOLD,
    )

    sum_distance = np.zeros(
        N_CELLS,
        dtype=np.float64,
    )

    count_crossing = np.zeros(
        N_CELLS,
        dtype=np.int32,
    )

    crossing_indices = np.where(
        cross
    )[0]

    for index in crossing_indices:

        streamline = int(
            geometry[
                "streamline_index"
            ][
                index
            ]
        )

        node = int(
            geometry[
                "node_index"
            ][
                index
            ]
        )

        a0 = float(
            geometry[
                "alpha0"
            ][
                index
            ]
        )

        a1 = float(
            geometry[
                "alpha1"
            ][
                index
            ]
        )

        sa = float(
            s0[
                index
            ]
        )

        sb = float(
            s1[
                index
            ]
        )

        if abs(
            sb
            -
            sa
        ) <= EPS:

            continue

        u_local = (
            PRIMARY_THRESHOLD
            -
            sa
        ) / (
            sb
            -
            sa
        )

        u_local = float(
            np.clip(
                u_local,
                0.0,
                1.0,
            )
        )

        alpha_cross = (
            a0
            +
            u_local
            *
            (
                a1
                -
                a0
            )
        )

        p0 = np.asarray(
            xyz[
                streamline,
                node
            ],
            dtype=np.float64,
        )

        p1 = np.asarray(
            xyz[
                streamline,
                node + 1
            ],
            dtype=np.float64,
        )

        point = (
            p0
            +
            alpha_cross
            *
            (
                p1
                -
                p0
            )
        )

        cell = int(
            geometry[
                "cell_index"
            ][
                index
            ]
        )

        center = cell_center(
            cell
        )

        distance = float(
            np.linalg.norm(
                point
                -
                center
            )
        )

        sum_distance[
            cell
        ] += (
            distance
        )

        count_crossing[
            cell
        ] += 1

    mean_distance = np.zeros(
        N_CELLS,
        dtype=np.float64,
    )

    valid = (
        count_crossing
        >
        0
    )

    mean_distance[
        valid
    ] = (
        sum_distance[
            valid
        ]
        /
        count_crossing[
            valid
        ]
    )

    return (
        count_crossing,
        mean_distance,
    )


# =============================================================================
# MODEL-SPECIFIC SUBCELL FIELD
# =============================================================================

def build_subcell_fields(
    geometry,
    xyz,
    streamline_saturation,
):

    (
        s0,
        s1,
        smid,
    ) = evaluate_subsegment_endpoints(
        geometry,
        streamline_saturation,
    )

    fraction = (
        fraction_above_threshold(
            s0,
            s1,
            PRIMARY_THRESHOLD,
        )
    )

    cell_index = (
        geometry[
            "cell_index"
        ]
    )

    qdtau = (
        geometry[
            "qdtau"
        ]
    )

    length = (
        geometry[
            "length"
        ]
    )

    # -------------------------------------------------------------------------
    # Authoritative q*dtau saturation mean
    # -------------------------------------------------------------------------

    mean_saturation_flat, support_weight = (
        weighted_cell_average(
            cell_index,
            smid,
            qdtau,
            S_INITIAL,
        )
    )

    # -------------------------------------------------------------------------
    # Fraction of q*dtau lying above threshold
    # -------------------------------------------------------------------------

    swept_qdtau_flat, _ = (
        weighted_cell_average(
            cell_index,
            fraction,
            qdtau,
            0.0,
        )
    )

    # -------------------------------------------------------------------------
    # Fraction of geometric subsegment length lying above threshold
    # -------------------------------------------------------------------------

    swept_length_flat, _ = (
        weighted_cell_average(
            cell_index,
            fraction,
            length,
            0.0,
        )
    )

    # -------------------------------------------------------------------------
    # Crossings
    # -------------------------------------------------------------------------

    (
        crossing_count_flat,
        crossing_distance_flat,
    ) = crossing_distance_statistics(
        geometry,
        xyz,
        s0,
        s1,
    )

    return {
        "mean_saturation":
            mean_saturation_flat.reshape(
                GRID_SHAPE
            ),

        "swept_qdtau_fraction":
            swept_qdtau_flat.reshape(
                GRID_SHAPE
            ),

        "swept_length_fraction":
            swept_length_flat.reshape(
                GRID_SHAPE
            ),

        "crossing_count":
            crossing_count_flat.reshape(
                GRID_SHAPE
            ),

        "mean_crossing_distance_m":
            crossing_distance_flat.reshape(
                GRID_SHAPE
            ),

        "support_weight":
            support_weight.reshape(
                GRID_SHAPE
            ),
    }


# =============================================================================
# GLOBAL METRICS
# =============================================================================

def global_metrics(
    time_days,
    pirnn,
    truth,
):

    mean_p = (
        pirnn[
            "mean_saturation"
        ]
    )

    mean_t = (
        truth[
            "mean_saturation"
        ]
    )

    frac_p = (
        pirnn[
            "swept_qdtau_fraction"
        ]
    )

    frac_t = (
        truth[
            "swept_qdtau_fraction"
        ]
    )

    hard_p = (
        mean_p
        >
        PRIMARY_THRESHOLD
    )

    hard_t = (
        mean_t
        >
        PRIMARY_THRESHOLD
    )

    hard_volume_error = abs(
        int(
            np.sum(
                hard_p
            )
        )
        -
        int(
            np.sum(
                hard_t
            )
        )
    ) / max(
        int(
            np.sum(
                hard_t
            )
        ),
        1,
    )

    fractional_volume_p = float(
        np.sum(
            frac_p
        )
    )

    fractional_volume_t = float(
        np.sum(
            frac_t
        )
    )

    fractional_volume_error = abs(
        fractional_volume_p
        -
        fractional_volume_t
    ) / max(
        fractional_volume_t,
        EPS,
    )

    mismatch = (
        hard_p
        !=
        hard_t
    )

    partial_truth = (
        (
            frac_t
            >
            PARTIAL_SWEEP_MIN
        )
        &
        (
            frac_t
            <
            PARTIAL_SWEEP_MAX
        )
    )

    partial_pirnn = (
        (
            frac_p
            >
            PARTIAL_SWEEP_MIN
        )
        &
        (
            frac_p
            <
            PARTIAL_SWEEP_MAX
        )
    )

    partial_either = (
        partial_truth
        |
        partial_pirnn
    )

    strongly_partial = (
        (
            (
                frac_t
                >
                STRONGLY_PARTIAL_MIN
            )
            &
            (
                frac_t
                <
                STRONGLY_PARTIAL_MAX
            )
        )
        |
        (
            (
                frac_p
                >
                STRONGLY_PARTIAL_MIN
            )
            &
            (
                frac_p
                <
                STRONGLY_PARTIAL_MAX
            )
        )
    )

    mismatch_count = int(
        np.sum(
            mismatch
        )
    )

    mismatch_partial_count = int(
        np.sum(
            mismatch
            &
            partial_either
        )
    )

    mismatch_strong_partial_count = int(
        np.sum(
            mismatch
            &
            strongly_partial
        )
    )

    mismatch_partial_share = (
        mismatch_partial_count
        /
        max(
            mismatch_count,
            1,
        )
    )

    mismatch_strong_partial_share = (
        mismatch_strong_partial_count
        /
        max(
            mismatch_count,
            1,
        )
    )

    return {
        "time_days":
            float(
                time_days
            ),

        "binary_plume_volume_error":
            float(
                hard_volume_error
            ),

        "fractional_swept_volume_error":
            float(
                fractional_volume_error
            ),

        "binary_3D_IoU":
            mask_iou(
                hard_p,
                hard_t,
            ),

        "fractional_soft_IoU":
            soft_iou(
                frac_p,
                frac_t,
            ),

        "binary_mismatch_cells":
            mismatch_count,

        "partial_cells_PI_RNN":
            int(
                np.sum(
                    partial_pirnn
                )
            ),

        "partial_cells_SG7A":
            int(
                np.sum(
                    partial_truth
                )
            ),

        "binary_mismatch_partial_cells":
            mismatch_partial_count,

        "binary_mismatch_partial_share":
            float(
                mismatch_partial_share
            ),

        "binary_mismatch_strong_partial_share":
            float(
                mismatch_strong_partial_share
            ),

        "PI_RNN_fractional_plume_cells_equivalent":
            fractional_volume_p,

        "SG7A_fractional_plume_cells_equivalent":
            fractional_volume_t,
    }


# =============================================================================
# 100-DAY CELL TABLE
# =============================================================================

def build_cell_rows(
    pirnn,
    truth,
):

    rows = []

    mean_p = (
        pirnn[
            "mean_saturation"
        ].ravel()
    )

    mean_t = (
        truth[
            "mean_saturation"
        ].ravel()
    )

    frac_q_p = (
        pirnn[
            "swept_qdtau_fraction"
        ].ravel()
    )

    frac_q_t = (
        truth[
            "swept_qdtau_fraction"
        ].ravel()
    )

    frac_l_p = (
        pirnn[
            "swept_length_fraction"
        ].ravel()
    )

    frac_l_t = (
        truth[
            "swept_length_fraction"
        ].ravel()
    )

    cross_p = (
        pirnn[
            "crossing_count"
        ].ravel()
    )

    cross_t = (
        truth[
            "crossing_count"
        ].ravel()
    )

    dist_p = (
        pirnn[
            "mean_crossing_distance_m"
        ].ravel()
    )

    dist_t = (
        truth[
            "mean_crossing_distance_m"
        ].ravel()
    )

    support = (
        truth[
            "support_weight"
        ].ravel()
        >
        EPS
    )

    for flat in range(
        N_CELLS
    ):

        (
            k,
            j,
            i,
        ) = unflatten_cell(
            flat
        )

        hard_p = bool(
            mean_p[
                flat
            ]
            >
            PRIMARY_THRESHOLD
        )

        hard_t = bool(
            mean_t[
                flat
            ]
            >
            PRIMARY_THRESHOLD
        )

        mismatch = (
            hard_p
            !=
            hard_t
        )

        partial = (
            (
                PARTIAL_SWEEP_MIN
                <
                frac_q_p[
                    flat
                ]
                <
                PARTIAL_SWEEP_MAX
            )
            or
            (
                PARTIAL_SWEEP_MIN
                <
                frac_q_t[
                    flat
                ]
                <
                PARTIAL_SWEEP_MAX
            )
        )

        rows.append(
            {
                "flat_cell":
                    flat,

                "layer":
                    k
                    +
                    1,

                "j":
                    j,

                "i":
                    i,

                "directly_supported":
                    bool(
                        support[
                            flat
                        ]
                    ),

                "PI_RNN_mean_saturation":
                    float(
                        mean_p[
                            flat
                        ]
                    ),

                "SG7A_mean_saturation":
                    float(
                        mean_t[
                            flat
                        ]
                    ),

                "PI_RNN_binary_plume":
                    hard_p,

                "SG7A_binary_plume":
                    hard_t,

                "binary_mismatch":
                    mismatch,

                "partial_sweep_cell":
                    partial,

                "PI_RNN_qdtau_swept_fraction":
                    float(
                        frac_q_p[
                            flat
                        ]
                    ),

                "SG7A_qdtau_swept_fraction":
                    float(
                        frac_q_t[
                            flat
                        ]
                    ),

                "PI_RNN_length_swept_fraction":
                    float(
                        frac_l_p[
                            flat
                        ]
                    ),

                "SG7A_length_swept_fraction":
                    float(
                        frac_l_t[
                            flat
                        ]
                    ),

                "PI_RNN_crossing_count":
                    int(
                        cross_p[
                            flat
                        ]
                    ),

                "SG7A_crossing_count":
                    int(
                        cross_t[
                            flat
                        ]
                    ),

                "PI_RNN_mean_crossing_distance_m":
                    float(
                        dist_p[
                            flat
                        ]
                    ),

                "SG7A_mean_crossing_distance_m":
                    float(
                        dist_t[
                            flat
                        ]
                    ),
            }
        )

    return rows


# =============================================================================
# LAYER METRICS
# =============================================================================

def build_layer_rows(
    pirnn,
    truth,
):

    rows = []

    for k in range(
        NZ
    ):

        mean_p = (
            pirnn[
                "mean_saturation"
            ][
                k
            ]
        )

        mean_t = (
            truth[
                "mean_saturation"
            ][
                k
            ]
        )

        frac_p = (
            pirnn[
                "swept_qdtau_fraction"
            ][
                k
            ]
        )

        frac_t = (
            truth[
                "swept_qdtau_fraction"
            ][
                k
            ]
        )

        hard_p = (
            mean_p
            >
            PRIMARY_THRESHOLD
        )

        hard_t = (
            mean_t
            >
            PRIMARY_THRESHOLD
        )

        binary_error = abs(
            int(
                np.sum(
                    hard_p
                )
            )
            -
            int(
                np.sum(
                    hard_t
                )
            )
        ) / max(
            int(
                np.sum(
                    hard_t
                )
            ),
            1,
        )

        fractional_error = abs(
            float(
                np.sum(
                    frac_p
                )
            )
            -
            float(
                np.sum(
                    frac_t
                )
            )
        ) / max(
            float(
                np.sum(
                    frac_t
                )
            ),
            EPS,
        )

        rows.append(
            {
                "layer":
                    k
                    +
                    1,

                "binary_volume_error":
                    float(
                        binary_error
                    ),

                "fractional_volume_error":
                    float(
                        fractional_error
                    ),

                "binary_IoU":
                    mask_iou(
                        hard_p,
                        hard_t,
                    ),

                "fractional_soft_IoU":
                    soft_iou(
                        frac_p,
                        frac_t,
                    ),

                "PI_RNN_partial_cells":
                    int(
                        np.sum(
                            (
                                frac_p
                                >
                                PARTIAL_SWEEP_MIN
                            )
                            &
                            (
                                frac_p
                                <
                                PARTIAL_SWEEP_MAX
                            )
                        )
                    ),

                "SG7A_partial_cells":
                    int(
                        np.sum(
                            (
                                frac_t
                                >
                                PARTIAL_SWEEP_MIN
                            )
                            &
                            (
                                frac_t
                                <
                                PARTIAL_SWEEP_MAX
                            )
                        )
                    ),
            }
        )

    return rows


# =============================================================================
# PLOTS
# =============================================================================

def plot_volume_error(
    global_rows,
):

    times = [
        row[
            "time_days"
        ]
        for row
        in global_rows
    ]

    binary = [
        100.0
        *
        row[
            "binary_plume_volume_error"
        ]
        for row
        in global_rows
    ]

    fractional = [
        100.0
        *
        row[
            "fractional_swept_volume_error"
        ]
        for row
        in global_rows
    ]

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        times,
        binary,
        marker="o",
        label="Binary cell plume",
    )

    ax.plot(
        times,
        fractional,
        marker="s",
        label="Fractional subcell plume",
    )

    ax.axhline(
        10.0,
        linestyle="--",
        label="Existing SG7E 10% reference",
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        "PI-RNN vs SG7A plume-volume error [%]"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-2B\n"
        "Binary vs Subcell-Fractional Plume Volume"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D2B_Binary_vs_Fractional_Volume_Error.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_soft_iou(
    global_rows,
):

    times = [
        row[
            "time_days"
        ]
        for row
        in global_rows
    ]

    hard = [
        row[
            "binary_3D_IoU"
        ]
        for row
        in global_rows
    ]

    soft = [
        row[
            "fractional_soft_IoU"
        ]
        for row
        in global_rows
    ]

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        times,
        hard,
        marker="o",
        label="Binary 3D IoU",
    )

    ax.plot(
        times,
        soft,
        marker="s",
        label="Fractional soft IoU",
    )

    ax.set_ylim(
        0.0,
        1.05,
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        "IoU"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-2B\n"
        "Binary vs Fractional Front Agreement"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D2B_Binary_vs_Soft_IoU.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_100d_layer8(
    pirnn,
    truth,
):

    layer = 7

    fields = [
        (
            "PI-RNN swept fraction",
            pirnn[
                "swept_qdtau_fraction"
            ][
                layer
            ],
        ),

        (
            "SG7A swept fraction",
            truth[
                "swept_qdtau_fraction"
            ][
                layer
            ],
        ),

        (
            "Absolute difference",
            np.abs(
                pirnn[
                    "swept_qdtau_fraction"
                ][
                    layer
                ]
                -
                truth[
                    "swept_qdtau_fraction"
                ][
                    layer
                ]
            ),
        ),
    ]

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(
            15,
            5,
        )
    )

    for (
        ax,
        (
            title,
            field,
        ),
    ) in zip(
        axes,
        fields,
    ):

        image = ax.imshow(
            field,
            origin="lower",
            vmin=(
                0.0
                if title
                !=
                "Absolute difference"
                else
                None
            ),
            vmax=(
                1.0
                if title
                !=
                "Absolute difference"
                else
                None
            ),
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
        "PAD-Stream V15-SG7D-2B\n"
        "100-Day Subcell Swept Fraction — Layer 8"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D2B_SweptFraction_100d_Layer08.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_100d_crossings(
    truth,
):

    layer = 7

    crossing = (
        truth[
            "crossing_count"
        ][
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
        crossing,
        origin="lower",
    )

    ax.set_xlabel(
        "i"
    )

    ax.set_ylabel(
        "j"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-2B\n"
        "SG7A Threshold Crossings per Cell — 100 d, Layer 8"
    )

    fig.colorbar(
        image,
        ax=ax,
        label="Crossing count",
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D2B_ThresholdCrossings_100d_Layer08.png",
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
            "PAD-Stream V15-SG7D-2B "
            "front geometry / subcell sampling audit."
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
        "PAD-Stream Version 15-SG7D-2B"
    )

    print(
        "Front Geometry / Subcell Sampling Audit"
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
        sg7d1_summary,
        sg7d2_summary,
    ) = load_inputs(
        source_workspace
    )

    if (
        sg7d1_summary.get(
            "diagnosis"
        )
        !=
        "FRONT_CLASSIFICATION_DISAGREEMENT"
    ):

        raise RuntimeError(
            "SG7D-2B requires SG7D-1 diagnosis:\n"
            "FRONT_CLASSIFICATION_DISAGREEMENT"
        )

    if (
        sg7d2_summary.get(
            "diagnosis"
        )
        !=
        "FRONT_DISAGREEMENT_NOT_CONTROLLED_BY_CELL_AVERAGING"
    ):

        raise RuntimeError(
            "SG7D-2B requires SG7D-2 diagnosis:\n"
            "FRONT_DISAGREEMENT_NOT_CONTROLLED_BY_CELL_AVERAGING"
        )

    (
        xyz,
        tau,
        flow_weights,
    ) = extract_sg6(
        sg6
    )

    (
        times,
        pirnn_streamline,
        truth_streamline,
    ) = extract_sg7c(
        sg7c
    )

    print(
        "\nSOURCE DATABASE"
    )

    print(
        f"  Streamlines             : "
        f"{xyz.shape[0]:,}"
    )

    print(
        f"  Nodes per streamline    : "
        f"{xyz.shape[1]}"
    )

    print(
        f"  Deployment times        : "
        f"{times.tolist()}"
    )

    print(
        f"  Total flow weight       : "
        f"{np.sum(flow_weights):.6e} m3/s"
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

    if pirnn_streamline.shape != expected_shape:

        raise RuntimeError(
            "Unexpected PI-RNN streamline field shape.\n"
            f"Expected: {expected_shape}\n"
            f"Observed: {pirnn_streamline.shape}"
        )

    if truth_streamline.shape != expected_shape:

        raise RuntimeError(
            "Unexpected SG7A streamline field shape."
        )

    # =========================================================================
    # GEOMETRY
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "BUILDING CARTESIAN SUBCELL FRONT GEOMETRY"
    )

    print(
        "=" * 78
    )

    geometry = (
        build_geometry_database(
            xyz,
            tau,
            flow_weights,
        )
    )

    n_subsegments = int(
        len(
            geometry[
                "cell_index"
            ]
        )
    )

    unique_cells = int(
        len(
            np.unique(
                geometry[
                    "cell_index"
                ]
            )
        )
    )

    direct_support_fraction = (
        unique_cells
        /
        N_CELLS
    )

    print(
        f"  Cartesian subsegments   : "
        f"{n_subsegments:,}"
    )

    print(
        f"  Directly sampled cells  : "
        f"{unique_cells:,} / {N_CELLS:,}"
    )

    print(
        f"  Direct support fraction : "
        f"{direct_support_fraction:.3%}"
    )

    print(
        f"  Minimum q*dtau          : "
        f"{np.min(geometry['qdtau']):.6e}"
    )

    print(
        f"  Maximum q*dtau          : "
        f"{np.max(geometry['qdtau']):.6e}"
    )

    # =========================================================================
    # TIME LOOP
    # =========================================================================

    global_rows = []

    fields_by_time = {}

    print(
        "\n"
        + "=" * 78
    )

    print(
        "SUBCELL FRONT AUDIT"
    )

    print(
        "=" * 78
    )

    for time_index, time_days in enumerate(
        times
    ):

        print(
            f"\n  t = {time_days:.1f} days"
        )

        pirnn_fields = (
            build_subcell_fields(
                geometry,
                xyz,
                pirnn_streamline[
                    time_index
                ],
            )
        )

        truth_fields = (
            build_subcell_fields(
                geometry,
                xyz,
                truth_streamline[
                    time_index
                ],
            )
        )

        metrics = (
            global_metrics(
                time_days,
                pirnn_fields,
                truth_fields,
            )
        )

        global_rows.append(
            metrics
        )

        fields_by_time[
            float(
                time_days
            )
        ] = {
            "pirnn":
                pirnn_fields,

            "truth":
                truth_fields,
        }

        print(
            f"    Binary volume error    : "
            f"{metrics['binary_plume_volume_error']:.3%}"
        )

        print(
            f"    Fractional volume error: "
            f"{metrics['fractional_swept_volume_error']:.3%}"
        )

        print(
            f"    Binary 3D IoU          : "
            f"{metrics['binary_3D_IoU']:.6f}"
        )

        print(
            f"    Fractional soft IoU    : "
            f"{metrics['fractional_soft_IoU']:.6f}"
        )

        print(
            f"    Binary mismatch cells  : "
            f"{metrics['binary_mismatch_cells']:,}"
        )

        print(
            f"    Mismatch partial share : "
            f"{metrics['binary_mismatch_partial_share']:.3%}"
        )

        print(
            f"    Strong partial share   : "
            f"{metrics['binary_mismatch_strong_partial_share']:.3%}"
        )

    # =========================================================================
    # 100 DAY
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

    metrics_100 = (
        global_rows[
            index_100
        ]
    )

    fields_100 = (
        fields_by_time[
            100.0
        ]
    )

    pirnn_100 = (
        fields_100[
            "pirnn"
        ]
    )

    truth_100 = (
        fields_100[
            "truth"
        ]
    )

    cell_rows = (
        build_cell_rows(
            pirnn_100,
            truth_100,
        )
    )

    mismatch_rows = [
        row
        for row
        in cell_rows
        if row[
            "binary_mismatch"
        ]
    ]

    layer_rows = (
        build_layer_rows(
            pirnn_100,
            truth_100,
        )
    )

    # =========================================================================
    # ADDITIONAL 100-DAY GEOMETRIC METRICS
    # =========================================================================

    truth_crossing_cells = int(
        np.sum(
            truth_100[
                "crossing_count"
            ]
            >
            0
        )
    )

    pirnn_crossing_cells = int(
        np.sum(
            pirnn_100[
                "crossing_count"
            ]
            >
            0
        )
    )

    truth_partial_cells = int(
        np.sum(
            (
                truth_100[
                    "swept_qdtau_fraction"
                ]
                >
                PARTIAL_SWEEP_MIN
            )
            &
            (
                truth_100[
                    "swept_qdtau_fraction"
                ]
                <
                PARTIAL_SWEEP_MAX
            )
        )
    )

    pirnn_partial_cells = int(
        np.sum(
            (
                pirnn_100[
                    "swept_qdtau_fraction"
                ]
                >
                PARTIAL_SWEEP_MIN
            )
            &
            (
                pirnn_100[
                    "swept_qdtau_fraction"
                ]
                <
                PARTIAL_SWEEP_MAX
            )
        )
    )

    # =========================================================================
    # DIAGNOSTIC FLAGS
    # =========================================================================

    binary_bad = (
        metrics_100[
            "binary_plume_volume_error"
        ]
        >
        0.10
    )

    fractional_good = (
        metrics_100[
            "fractional_swept_volume_error"
        ]
        <
        FRACTIONAL_VOLUME_ERROR_REFERENCE
    )

    fractional_agreement_good = (
        metrics_100[
            "fractional_soft_IoU"
        ]
        >=
        SOFT_IOU_REFERENCE
    )

    mismatch_partial_dominant = (
        metrics_100[
            "binary_mismatch_partial_share"
        ]
        >=
        MISMATCH_PARTIAL_SHARE_REFERENCE
    )

    support_strong = (
        direct_support_fraction
        >=
        DIRECT_SUPPORT_REFERENCE
    )

    # =========================================================================
    # DIAGNOSIS
    # =========================================================================

    if (
        binary_bad
        and
        fractional_good
        and
        fractional_agreement_good
        and
        mismatch_partial_dominant
    ):

        diagnosis = (
            "SUBCELL_PARTIAL_SWEEP_EXPLAINS_BINARY_MISMATCH"
        )

        recommendation = (
            "The early-time binary plume discrepancy is largely explained "
            "by partially swept Cartesian cells. Continuous streamline "
            "transport agrees much better when subcell occupancy is retained. "
            "The next milestone should test a constrained front-aware "
            "Eulerian reconstruction without changing the frozen transport."
        )

        next_milestone = (
            "V15-SG7D-3 — Constrained Front-Aware "
            "Map-Back Candidate Validation"
        )

    elif (
        binary_bad
        and
        not fractional_good
        and
        support_strong
    ):

        diagnosis = (
            "SUBCELL_FRONT_GEOMETRY_DISAGREEMENT"
        )

        recommendation = (
            "Even fractional subcell occupancy remains inconsistent between "
            "PI-RNN and SG7A. The next step should inspect local streamline "
            "front positions rather than modifying cell averaging."
        )

        next_milestone = (
            "V15-SG7D-2C — Streamline Front-Position "
            "Alignment Audit"
        )

    elif (
        binary_bad
        and
        not support_strong
    ):

        diagnosis = (
            "STREAMLINE_SUPPORT_GEOMETRY_LIMITATION"
        )

        recommendation = (
            "The subcell audit still lacks sufficient direct geometric "
            "support. Revisit local/adaptive streamline seeding rather than "
            "globally increasing seed density."
        )

        next_milestone = (
            "V15-SG5D — Adaptive Front-Region "
            "Streamline Seeding Study"
        )

    elif (
        fractional_good
        and
        fractional_agreement_good
        and
        not mismatch_partial_dominant
    ):

        diagnosis = (
            "BINARY_PLUME_METRIC_DOMINANT"
        )

        recommendation = (
            "Continuous and fractional plume representations agree, but the "
            "binary cell metric remains unusually sensitive. Retain the "
            "existing physical reconstruction and reassess how plume geometry "
            "should be reported, without changing physics thresholds."
        )

        next_milestone = (
            "V15-SG7E-3 — Continuous / Fractional "
            "Plume Validation Framework"
        )

    else:

        diagnosis = (
            "FRONT_GEOMETRY_NOT_PRIMARY_LIMITATION"
        )

        recommendation = (
            "Subcell front geometry does not fully explain the discrepancy. "
            "Inspect streamline front-position alignment directly."
        )

        next_milestone = (
            "V15-SG7D-2C — Streamline Front-Position "
            "Alignment Audit"
        )

    # =========================================================================
    # VALIDATION
    # =========================================================================

    checks = [
        (
            "Incoming SG7D-1 diagnosis reproduced",
            (
                sg7d1_summary.get(
                    "diagnosis"
                )
                ==
                "FRONT_CLASSIFICATION_DISAGREEMENT"
            ),
        ),

        (
            "Incoming SG7D-2 diagnosis reproduced",
            (
                sg7d2_summary.get(
                    "diagnosis"
                )
                ==
                "FRONT_DISAGREEMENT_NOT_CONTROLLED_BY_CELL_AVERAGING"
            ),
        ),

        (
            "2662 streamline source loaded",
            xyz.shape[0]
            ==
            2662,
        ),

        (
            "201 transport nodes loaded",
            xyz.shape[1]
            ==
            201,
        ),

        (
            "Cartesian subsegments finite",
            (
                np.all(
                    np.isfinite(
                        geometry[
                            "length"
                        ]
                    )
                )
                and
                np.all(
                    np.isfinite(
                        geometry[
                            "qdtau"
                        ]
                    )
                )
            ),
        ),

        (
            "All q*dtau weights nonnegative",
            np.all(
                geometry[
                    "qdtau"
                ]
                >=
                0.0
            ),
        ),

        (
            "All fractional swept fields bounded",
            all(
                (
                    np.min(
                        fields_by_time[
                            float(
                                time
                            )
                        ][
                            model
                        ][
                            "swept_qdtau_fraction"
                        ]
                    )
                    >=
                    -1.0e-12
                    and
                    np.max(
                        fields_by_time[
                            float(
                                time
                            )
                        ][
                            model
                        ][
                            "swept_qdtau_fraction"
                        ]
                    )
                    <=
                    1.0
                    +
                    1.0e-12
                )
                for time
                in times
                for model
                in [
                    "pirnn",
                    "truth",
                ]
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
            "100-day cell audit generated",
            len(
                cell_rows
            )
            ==
            N_CELLS,
        ),

        (
            "Diagnostic classification established",
            diagnosis
            in
            {
                "SUBCELL_PARTIAL_SWEEP_EXPLAINS_BINARY_MISMATCH",
                "SUBCELL_FRONT_GEOMETRY_DISAGREEMENT",
                "STREAMLINE_SUPPORT_GEOMETRY_LIMITATION",
                "BINARY_PLUME_METRIC_DOMINANT",
                "FRONT_GEOMETRY_NOT_PRIMARY_LIMITATION",
            },
        ),
    ]

    passed = all(
        status
        for _, status
        in checks
    )

    # =========================================================================
    # PRINT RESULT
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7D-2B DIAGNOSTIC VALIDATION"
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
        "\n100-DAY SUBCELL FRONT RESULT"
    )

    print(
        f"  Binary plume-volume error : "
        f"{metrics_100['binary_plume_volume_error']:.3%}"
    )

    print(
        f"  Fractional volume error   : "
        f"{metrics_100['fractional_swept_volume_error']:.3%}"
    )

    print(
        f"  Binary 3D IoU             : "
        f"{metrics_100['binary_3D_IoU']:.6f}"
    )

    print(
        f"  Fractional soft IoU       : "
        f"{metrics_100['fractional_soft_IoU']:.6f}"
    )

    print(
        f"  Binary mismatch cells     : "
        f"{metrics_100['binary_mismatch_cells']:,}"
    )

    print(
        f"  Mismatch partial share    : "
        f"{metrics_100['binary_mismatch_partial_share']:.3%}"
    )

    print(
        f"  Strong partial share      : "
        f"{metrics_100['binary_mismatch_strong_partial_share']:.3%}"
    )

    print(
        f"  SG7A partial cells        : "
        f"{truth_partial_cells:,}"
    )

    print(
        f"  PI-RNN partial cells      : "
        f"{pirnn_partial_cells:,}"
    )

    print(
        f"  SG7A crossing cells       : "
        f"{truth_crossing_cells:,}"
    )

    print(
        f"  PI-RNN crossing cells     : "
        f"{pirnn_crossing_cells:,}"
    )

    print(
        "\nDIAGNOSTIC FLAGS"
    )

    print(
        f"  Binary error >10%         : "
        f"{binary_bad}"
    )

    print(
        f"  Fractional error <10%     : "
        f"{fractional_good}"
    )

    print(
        f"  Fractional soft IoU >=0.9 : "
        f"{fractional_agreement_good}"
    )

    print(
        f"  Partial mismatch dominant : "
        f"{mismatch_partial_dominant}"
    )

    print(
        f"  Direct support strong     : "
        f"{support_strong}"
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
        GLOBAL_METRICS_FILE,
        global_rows,
    )

    save_csv(
        CELL_METRICS_FILE,
        cell_rows,
    )

    save_csv(
        LAYER_METRICS_FILE,
        layer_rows,
    )

    save_csv(
        MISMATCH_FILE,
        mismatch_rows,
    )

    # =========================================================================
    # DATABASE
    # =========================================================================

    np.savez_compressed(
        DATABASE_FILE,

        times_days=
            times,

        cell_index=
            geometry[
                "cell_index"
            ],

        streamline_index=
            geometry[
                "streamline_index"
            ],

        node_index=
            geometry[
                "node_index"
            ],

        alpha0=
            geometry[
                "alpha0"
            ],

        alpha1=
            geometry[
                "alpha1"
            ],

        subsegment_length_m=
            geometry[
                "length"
            ],

        subsegment_dtau_s=
            geometry[
                "dtau"
            ],

        subsegment_qdtau_m3=
            geometry[
                "qdtau"
            ],

        PI_RNN_100d_mean_saturation=
            pirnn_100[
                "mean_saturation"
            ],

        SG7A_100d_mean_saturation=
            truth_100[
                "mean_saturation"
            ],

        PI_RNN_100d_swept_fraction=
            pirnn_100[
                "swept_qdtau_fraction"
            ],

        SG7A_100d_swept_fraction=
            truth_100[
                "swept_qdtau_fraction"
            ],

        PI_RNN_100d_crossing_count=
            pirnn_100[
                "crossing_count"
            ],

        SG7A_100d_crossing_count=
            truth_100[
                "crossing_count"
            ],

        PI_RNN_100d_crossing_distance_m=
            pirnn_100[
                "mean_crossing_distance_m"
            ],

        SG7A_100d_crossing_distance_m=
            truth_100[
                "mean_crossing_distance_m"
            ],
    )

    # =========================================================================
    # PLOTS
    # =========================================================================

    plot_volume_error(
        global_rows
    )

    plot_soft_iou(
        global_rows
    )

    plot_100d_layer8(
        pirnn_100,
        truth_100,
    )

    plot_100d_crossings(
        truth_100
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7D-2B",

        "description":
            (
                "Front geometry and subcell sampling audit "
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

        "source": {
            "streamlines":
                int(
                    xyz.shape[0]
                ),

            "transport_nodes":
                int(
                    xyz.shape[1]
                ),

            "cartesian_subsegments":
                n_subsegments,

            "directly_sampled_cells":
                unique_cells,

            "direct_support_fraction":
                direct_support_fraction,
        },

        "100_day": {
            "binary_plume_volume_error":
                metrics_100[
                    "binary_plume_volume_error"
                ],

            "fractional_swept_volume_error":
                metrics_100[
                    "fractional_swept_volume_error"
                ],

            "binary_3D_IoU":
                metrics_100[
                    "binary_3D_IoU"
                ],

            "fractional_soft_IoU":
                metrics_100[
                    "fractional_soft_IoU"
                ],

            "binary_mismatch_cells":
                metrics_100[
                    "binary_mismatch_cells"
                ],

            "binary_mismatch_partial_share":
                metrics_100[
                    "binary_mismatch_partial_share"
                ],

            "strong_partial_share":
                metrics_100[
                    "binary_mismatch_strong_partial_share"
                ],

            "SG7A_partial_cells":
                truth_partial_cells,

            "PI_RNN_partial_cells":
                pirnn_partial_cells,

            "SG7A_crossing_cells":
                truth_crossing_cells,

            "PI_RNN_crossing_cells":
                pirnn_crossing_cells,
        },

        "diagnostic_flags": {
            "binary_error_above_10pct":
                bool(
                    binary_bad
                ),

            "fractional_error_below_10pct":
                bool(
                    fractional_good
                ),

            "fractional_soft_IoU_good":
                bool(
                    fractional_agreement_good
                ),

            "partial_sweep_dominates_binary_mismatch":
                bool(
                    mismatch_partial_dominant
                ),

            "direct_support_strong":
                bool(
                    support_strong
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
        f"  {GLOBAL_METRICS_FILE.name}"
    )

    print(
        f"  {CELL_METRICS_FILE.name}"
    )

    print(
        f"  {LAYER_METRICS_FILE.name}"
    )

    print(
        f"  {MISMATCH_FILE.name}"
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
        "  V15SG7D2B_Binary_vs_Fractional_Volume_Error.png"
    )

    print(
        "  V15SG7D2B_Binary_vs_Soft_IoU.png"
    )

    print(
        "  V15SG7D2B_SweptFraction_100d_Layer08.png"
    )

    print(
        "  V15SG7D2B_ThresholdCrossings_100d_Layer08.png"
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
            "V15-SG7D-2B AUDIT: PASS"
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
            "V15-SG7D-2B AUDIT: INCOMPLETE"
        )

        print()

        print(
            "Do not modify SG7D until the subcell "
            "front audit is internally consistent."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()