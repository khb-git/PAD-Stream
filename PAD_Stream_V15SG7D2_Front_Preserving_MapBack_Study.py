from __future__ import annotations

from pathlib import Path
import argparse
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7D-2
# Front-Preserving Raw Map-Back Reconstruction Study
#
# NO TRAINING.
# NO SEED-DENSITY CHANGE.
# NO CHANGE TO THE AUTHORITATIVE SG7D OPERATOR.
# NO CHANGE TO CONSERVATIVE PROJECTION.
# NO CHANGE TO SG7E PLUME THRESHOLDS.
#
#
# PURPOSE
# -------
# Reconstruct the 11x11 Cartesian streamline subsegment database and compare
# the accepted SG7D raw map-back operator against several FRONT-PRESERVING
# DIAGNOSTIC alternatives.
#
#
# AUTHORITATIVE OPERATOR
# ----------------------
#
#     q * Delta tau weighted mean
#
#
# DIAGNOSTIC CANDIDATES
# ---------------------
#
#     1. q * Delta tau weighted mean
#     2. uniform subsegment mean
#     3. path-length weighted mean
#     4. maximum subsegment saturation
#     5. 90th percentile saturation
#
#
# IMPORTANT
# ---------
#
# No candidate becomes authoritative in this milestone.
#
# SG7D-2 only identifies whether front smearing / averaging is responsible
# for the early-time plume-classification disagreement.
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
    / "V15_SG7D2"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# SOURCE FILES
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


SG7D1_SUMMARY_FILE = (
    ROOT
    / "output"
    / "V15_SG7D1"
    / "PAD_Stream_V15SG7D1_Summary.json"
)


# =============================================================================
# OUTPUTS
# =============================================================================

OPERATOR_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7D2_Operator_Metrics.csv"
)


THRESHOLD_FILE = (
    OUTPUT_DIR
    / "V15SG7D2_100d_Threshold_Metrics.csv"
)


FRONT_FILE = (
    OUTPUT_DIR
    / "V15SG7D2_Front_Cell_Metrics.csv"
)


SUBSEGMENT_FILE = (
    OUTPUT_DIR
    / "V15SG7D2_Subsegment_Summary.csv"
)


DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7D2_Front_Preserving_Study.npz"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7D2_Summary.json"
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


DX_M = 6.0960
DY_M = 6.0960
DZ_M = 1.2192


LX_M = (
    NX
    *
    DX_M
)

LY_M = (
    NY
    *
    DY_M
)

LZ_M = (
    NZ
    *
    DZ_M
)


# =============================================================================
# SATURATION
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


FRONT_BAND_HALF_WIDTH = 0.02


# =============================================================================
# OPERATOR NAMES
# =============================================================================

OPERATORS = [
    "q_dtau_mean",
    "uniform_mean",
    "path_length_mean",
    "maximum",
    "percentile_90",
]


EPS = 1.0e-14


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

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:

        return json.load(
            handle
        )


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

    count = int(
        np.sum(
            union
        )
    )

    if count == 0:

        return 1.0

    return float(
        np.sum(
            intersection
        )
        /
        count
    )


# =============================================================================
# FIND NPZ KEY
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
# LOAD SG6 / SG7C
# =============================================================================

def load_source(
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
        SG7D1_SUMMARY_FILE,
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

    sg7d1_summary = load_json(
        SG7D1_SUMMARY_FILE
    )

    return (
        sg6,
        sg7c,
        sg7d1_summary,
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
        "time of flight",
    )

    xi_key = find_key(
        sg6,
        [
            "xi",
            "transport_xi",
        ],
        "normalized coordinate",
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

    return (
        xyz,
        tau,
        xi,
        weights,
    )


# =============================================================================
# EXTRACT SG7C SATURATION
# =============================================================================

def extract_sg7c_fields(
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
        "PI-RNN streamline saturation",
    )

    truth_key = find_key(
        sg7c,
        [
            "SG7A_saturation",
            "truth_saturation",
            "reference_saturation",
            "S_truth",
        ],
        "SG7A streamline saturation",
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
# CELL INDEX
# =============================================================================

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


# =============================================================================
# CARTESIAN SEGMENT SPLITTING
#
# Split a streamline segment wherever it crosses Cartesian grid planes.
# =============================================================================

def split_segment_cartesian(
    p0,
    p1,
    tau0,
    tau1,
    s0,
    s1,
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

    # -------------------------------------------------------------------------
    # x planes
    # -------------------------------------------------------------------------

    if abs(
        direction[0]
    ) > EPS:

        for i in range(
            1,
            NX,
        ):

            plane = (
                i
                *
                DX_M
            )

            alpha = (
                plane
                -
                p0[0]
            ) / direction[0]

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

    # -------------------------------------------------------------------------
    # y planes
    # -------------------------------------------------------------------------

    if abs(
        direction[1]
    ) > EPS:

        for j in range(
            1,
            NY,
        ):

            plane = (
                j
                *
                DY_M
            )

            alpha = (
                plane
                -
                p0[1]
            ) / direction[1]

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

    # -------------------------------------------------------------------------
    # z planes
    # -------------------------------------------------------------------------

    if abs(
        direction[2]
    ) > EPS:

        for k in range(
            1,
            NZ,
        ):

            plane = (
                k
                *
                DZ_M
            )

            alpha = (
                plane
                -
                p0[2]
            ) / direction[2]

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

    alpha_values = np.asarray(
        sorted(
            set(
                np.round(
                    alpha_values,
                    decimals=14,
                )
            )
        ),
        dtype=np.float64,
    )

    subsegments = []

    for index in range(
        len(
            alpha_values
        )
        -
        1
    ):

        a0 = (
            alpha_values[
                index
            ]
        )

        a1 = (
            alpha_values[
                index
                +
                1
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

        cell = point_to_cell(
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
            (
                tau1
                -
                tau0
            )
            *
            (
                a1
                -
                a0
            )
        )

        smid = float(
            s0
            +
            amid
            *
            (
                s1
                -
                s0
            )
        )

        subsegments.append(
            {
                "cell":
                    cell,

                "length":
                    length,

                "dtau":
                    dtau,

                "saturation":
                    smid,
            }
        )

    return subsegments


# =============================================================================
# BUILD SUBSEGMENTS FOR ONE SATURATION FIELD
# =============================================================================

def build_subsegment_database(
    xyz,
    tau,
    weights,
    saturation,
):

    cell_index = []
    streamline_index = []
    length_values = []
    dtau_values = []
    qdtau_values = []
    saturation_values = []

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
            weights[
                streamline
            ]
        )

        for node in range(
            n_nodes
            -
            1
        ):

            p0 = (
                xyz[
                    streamline,
                    node
                ]
            )

            p1 = (
                xyz[
                    streamline,
                    node + 1
                ]
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

            s0 = float(
                saturation[
                    streamline,
                    node
                ]
            )

            s1 = float(
                saturation[
                    streamline,
                    node + 1
                ]
            )

            pieces = split_segment_cartesian(
                p0,
                p1,
                tau0,
                tau1,
                s0,
                s1,
            )

            for piece in pieces:

                (
                    k,
                    j,
                    i,
                ) = (
                    piece[
                        "cell"
                    ]
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

                length_values.append(
                    piece[
                        "length"
                    ]
                )

                dtau_values.append(
                    piece[
                        "dtau"
                    ]
                )

                qdtau_values.append(
                    q
                    *
                    piece[
                        "dtau"
                    ]
                )

                saturation_values.append(
                    piece[
                        "saturation"
                    ]
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

        "saturation":
            np.asarray(
                saturation_values,
                dtype=np.float64,
            ),
    }


# =============================================================================
# ACCUMULATE OPERATOR
# =============================================================================

def accumulate_operator(
    subsegments,
    operator,
):

    cell_index = (
        subsegments[
            "cell_index"
        ]
    )

    saturation = (
        subsegments[
            "saturation"
        ]
    )

    length = (
        subsegments[
            "length"
        ]
    )

    qdtau = (
        subsegments[
            "qdtau"
        ]
    )

    n_cells = (
        NZ
        *
        NY
        *
        NX
    )

    field = np.full(
        n_cells,
        S_INITIAL,
        dtype=np.float64,
    )

    unique_cells = np.unique(
        cell_index
    )

    for cell in unique_cells:

        mask = (
            cell_index
            ==
            cell
        )

        values = (
            saturation[
                mask
            ]
        )

        if operator == "q_dtau_mean":

            weights = (
                qdtau[
                    mask
                ]
            )

            denom = float(
                np.sum(
                    weights
                )
            )

            if denom > EPS:

                value = float(
                    np.sum(
                        weights
                        *
                        values
                    )
                    /
                    denom
                )

            else:

                value = float(
                    np.mean(
                        values
                    )
                )

        elif operator == "uniform_mean":

            value = float(
                np.mean(
                    values
                )
            )

        elif operator == "path_length_mean":

            weights = (
                length[
                    mask
                ]
            )

            denom = float(
                np.sum(
                    weights
                )
            )

            if denom > EPS:

                value = float(
                    np.sum(
                        weights
                        *
                        values
                    )
                    /
                    denom
                )

            else:

                value = float(
                    np.mean(
                        values
                    )
                )

        elif operator == "maximum":

            value = float(
                np.max(
                    values
                )
            )

        elif operator == "percentile_90":

            value = float(
                np.percentile(
                    values,
                    90.0,
                )
            )

        else:

            raise ValueError(
                f"Unknown operator: {operator}"
            )

        field[
            cell
        ] = value

    return (
        field
        .reshape(
            GRID_SHAPE
        )
    )


# =============================================================================
# OPERATOR METRICS
# =============================================================================

def operator_metrics(
    time_days,
    operator,
    pirnn_grid,
    truth_grid,
):

    difference = (
        pirnn_grid
        -
        truth_grid
    )

    mask_p = (
        pirnn_grid
        >
        PRIMARY_THRESHOLD
    )

    mask_t = (
        truth_grid
        >
        PRIMARY_THRESHOLD
    )

    footprint_p = np.any(
        mask_p,
        axis=0,
    )

    footprint_t = np.any(
        mask_t,
        axis=0,
    )

    volume_error = abs(
        int(
            np.sum(
                mask_p
            )
        )
        -
        int(
            np.sum(
                mask_t
            )
        )
    ) / max(
        int(
            np.sum(
                mask_t
            )
        ),
        1,
    )

    front_mask = (
        (
            np.abs(
                truth_grid
                -
                PRIMARY_THRESHOLD
            )
            <=
            FRONT_BAND_HALF_WIDTH
        )
        |
        (
            np.abs(
                pirnn_grid
                -
                PRIMARY_THRESHOLD
            )
            <=
            FRONT_BAND_HALF_WIDTH
        )
    )

    mismatch = (
        (
            pirnn_grid
            >
            PRIMARY_THRESHOLD
        )
        !=
        (
            truth_grid
            >
            PRIMARY_THRESHOLD
        )
    )

    return {
        "time_days":
            float(
                time_days
            ),

        "operator":
            operator,

        "global_L1":
            mae(
                difference
            ),

        "global_L2":
            rms(
                difference
            ),

        "plume_volume_relative_error":
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

        "front_L1":
            mae(
                difference[
                    front_mask
                ]
            ),

        "front_mismatch_fraction":
            float(
                np.sum(
                    mismatch
                    &
                    front_mask
                )
                /
                max(
                    np.sum(
                        front_mask
                    ),
                    1,
                )
            ),
    }


# =============================================================================
# PLOTS
# =============================================================================

def plot_operator_volume_error(
    metrics_rows,
):

    rows = [
        row
        for row
        in metrics_rows
        if np.isclose(
            row[
                "time_days"
            ],
            100.0,
        )
    ]

    labels = [
        row[
            "operator"
        ]
        for row
        in rows
    ]

    values = [
        100.0
        *
        row[
            "plume_volume_relative_error"
        ]
        for row
        in rows
    ]

    fig, ax = plt.subplots(
        figsize=(
            11,
            6,
        )
    )

    ax.bar(
        labels,
        values,
    )

    ax.set_ylabel(
        "100-day plume-volume error [%]"
    )

    ax.set_xlabel(
        "Diagnostic accumulation operator"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-2\n"
        "Front-Preserving Operator Comparison"
    )

    ax.tick_params(
        axis="x",
        rotation=25,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D2_Operator_Volume_Error_100d.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_operator_front_mismatch(
    metrics_rows,
):

    rows = [
        row
        for row
        in metrics_rows
        if np.isclose(
            row[
                "time_days"
            ],
            100.0,
        )
    ]

    labels = [
        row[
            "operator"
        ]
        for row
        in rows
    ]

    values = [
        100.0
        *
        row[
            "front_mismatch_fraction"
        ]
        for row
        in rows
    ]

    fig, ax = plt.subplots(
        figsize=(
            11,
            6,
        )
    )

    ax.bar(
        labels,
        values,
    )

    ax.set_ylabel(
        "100-day front classification mismatch [%]"
    )

    ax.set_xlabel(
        "Diagnostic accumulation operator"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-2\n"
        "Front Classification Sensitivity"
    )

    ax.tick_params(
        axis="x",
        rotation=25,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D2_Front_Mismatch_100d.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_100d_operator_maps(
    operator_grids,
):

    layer = 7

    operator = (
        "q_dtau_mean"
    )

    pirnn = (
        operator_grids[
            operator
        ][
            "pirnn"
        ]
    )

    truth = (
        operator_grids[
            operator
        ][
            "truth"
        ]
    )

    difference = (
        pirnn[
            layer
        ]
        -
        truth[
            layer
        ]
    )

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(
            15,
            5,
        )
    )

    image0 = axes[0].imshow(
        pirnn[
            layer
        ],
        origin="lower",
        vmin=S_MIN,
        vmax=S_MAX,
    )

    axes[0].set_title(
        "PI-RNN q*dtau"
    )

    fig.colorbar(
        image0,
        ax=axes[0],
    )

    image1 = axes[1].imshow(
        truth[
            layer
        ],
        origin="lower",
        vmin=S_MIN,
        vmax=S_MAX,
    )

    axes[1].set_title(
        "SG7A q*dtau"
    )

    fig.colorbar(
        image1,
        ax=axes[1],
    )

    image2 = axes[2].imshow(
        difference,
        origin="lower",
    )

    axes[2].set_title(
        "PI-RNN - SG7A"
    )

    fig.colorbar(
        image2,
        ax=axes[2],
    )

    fig.suptitle(
        "PAD-Stream V15-SG7D-2\n"
        "100-Day Authoritative Raw Reconstruction — Layer 8"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D2_Authoritative_100d_Layer08.png",
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
            "PAD-Stream V15-SG7D-2 front-preserving raw map-back study."
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
        "PAD-Stream Version 15-SG7D-2"
    )

    print(
        "Front-Preserving Raw Map-Back Reconstruction Study"
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
        "NO AUTHORITATIVE MAP-BACK OPERATOR WILL BE CHANGED."
    )

    print(
        "NO CONSERVATIVE PROJECTION WILL BE CHANGED."
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
    ) = load_source(
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
            "SG7D-2 requires incoming diagnosis "
            "FRONT_CLASSIFICATION_DISAGREEMENT."
        )

    (
        xyz,
        tau,
        xi,
        flow_weights,
    ) = extract_sg6(
        sg6
    )

    (
        times,
        pirnn_streamline,
        truth_streamline,
    ) = extract_sg7c_fields(
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
        f"  Nodes                   : "
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
    # VALIDATE SHAPES
    # =========================================================================

    if pirnn_streamline.shape != truth_streamline.shape:

        raise RuntimeError(
            "PI-RNN and SG7A streamline field shapes differ."
        )

    expected_shape = (
        len(
            times
        ),
        xyz.shape[0],
        xyz.shape[1],
    )

    if pirnn_streamline.shape != expected_shape:

        raise RuntimeError(
            "Unexpected streamline saturation shape.\n"
            f"Expected: {expected_shape}\n"
            f"Observed: {pirnn_streamline.shape}"
        )

    # =========================================================================
    # BUILD OPERATOR STUDY
    # =========================================================================

    metrics_rows = []

    threshold_rows = []

    front_rows = []

    subsegment_summary_rows = []

    saved_operator_grids_100d = {}

    all_operator_grids = {}

    print(
        "\n"
        + "=" * 78
    )

    print(
        "RECONSTRUCTING CARTESIAN SUBSEGMENT DATABASE"
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

        # ---------------------------------------------------------------------
        # PI-RNN subsegments
        # ---------------------------------------------------------------------

        pirnn_segments = build_subsegment_database(
            xyz,
            tau,
            flow_weights,
            pirnn_streamline[
                time_index
            ],
        )

        # ---------------------------------------------------------------------
        # SG7A subsegments
        # ---------------------------------------------------------------------

        truth_segments = build_subsegment_database(
            xyz,
            tau,
            flow_weights,
            truth_streamline[
                time_index
            ],
        )

        # ---------------------------------------------------------------------
        # Geometry must match exactly
        # ---------------------------------------------------------------------

        geometry_match = (
            np.array_equal(
                pirnn_segments[
                    "cell_index"
                ],
                truth_segments[
                    "cell_index"
                ],
            )
            and
            np.allclose(
                pirnn_segments[
                    "length"
                ],
                truth_segments[
                    "length"
                ],
            )
            and
            np.allclose(
                pirnn_segments[
                    "qdtau"
                ],
                truth_segments[
                    "qdtau"
                ],
            )
        )

        if not geometry_match:

            raise RuntimeError(
                "PI-RNN and SG7A subsegment geometry mismatch."
            )

        if time_index == 0:

            subsegment_summary_rows.append(
                {
                    "streamlines":
                        int(
                            xyz.shape[0]
                        ),

                    "nodes_per_streamline":
                        int(
                            xyz.shape[1]
                        ),

                    "subsegments":
                        int(
                            len(
                                pirnn_segments[
                                    "cell_index"
                                ]
                            )
                        ),

                    "unique_cells":
                        int(
                            len(
                                np.unique(
                                    pirnn_segments[
                                        "cell_index"
                                    ]
                                )
                            )
                        ),

                    "minimum_length_m":
                        float(
                            np.min(
                                pirnn_segments[
                                    "length"
                                ]
                            )
                        ),

                    "maximum_length_m":
                        float(
                            np.max(
                                pirnn_segments[
                                    "length"
                                ]
                            )
                        ),

                    "minimum_qdtau":
                        float(
                            np.min(
                                pirnn_segments[
                                    "qdtau"
                                ]
                            )
                        ),

                    "maximum_qdtau":
                        float(
                            np.max(
                                pirnn_segments[
                                    "qdtau"
                                ]
                            )
                        ),
                }
            )

        # ---------------------------------------------------------------------
        # Apply all operators
        # ---------------------------------------------------------------------

        time_operator_grids = {}

        for operator in OPERATORS:

            pirnn_grid = accumulate_operator(
                pirnn_segments,
                operator,
            )

            truth_grid = accumulate_operator(
                truth_segments,
                operator,
            )

            metrics = operator_metrics(
                time_days,
                operator,
                pirnn_grid,
                truth_grid,
            )

            metrics_rows.append(
                metrics
            )

            time_operator_grids[
                operator
            ] = {
                "pirnn":
                    pirnn_grid,

                "truth":
                    truth_grid,
            }

            if np.isclose(
                time_days,
                100.0,
            ):

                threshold_rows.append(
                    {
                        **metrics,
                    }
                )

                front_rows.append(
                    {
                        "operator":
                            operator,

                        "front_L1":
                            metrics[
                                "front_L1"
                            ],

                        "front_mismatch_fraction":
                            metrics[
                                "front_mismatch_fraction"
                            ],

                        "plume_volume_relative_error":
                            metrics[
                                "plume_volume_relative_error"
                            ],
                    }
                )

        all_operator_grids[
            float(
                time_days
            )
        ] = (
            time_operator_grids
        )

        if np.isclose(
            time_days,
            100.0,
        ):

            saved_operator_grids_100d = (
                time_operator_grids
            )

        # ---------------------------------------------------------------------
        # Print compact comparison
        # ---------------------------------------------------------------------

        for operator in OPERATORS:

            row = next(
                item
                for item
                in metrics_rows
                if (
                    np.isclose(
                        item[
                            "time_days"
                        ],
                        time_days,
                    )
                    and
                    item[
                        "operator"
                    ]
                    ==
                    operator
                )
            )

            print(
                f"    {operator:20s} | "
                f"L1={row['global_L1']:.6e} | "
                f"Verr={row['plume_volume_relative_error']:.3%} | "
                f"IoU={row['three_dimensional_IoU']:.4f} | "
                f"frontMismatch={row['front_mismatch_fraction']:.2%}"
            )

    # =========================================================================
    # 100-DAY OPERATOR DECISION
    # =========================================================================

    rows_100 = [
        row
        for row
        in metrics_rows
        if np.isclose(
            row[
                "time_days"
            ],
            100.0,
        )
    ]

    accepted = next(
        row
        for row
        in rows_100
        if row[
            "operator"
        ]
        ==
        "q_dtau_mean"
    )

    candidates = [
        row
        for row
        in rows_100
        if row[
            "operator"
        ]
        !=
        "q_dtau_mean"
    ]

    best_volume_candidate = min(
        candidates,
        key=lambda row:
            row[
                "plume_volume_relative_error"
            ],
    )

    best_front_candidate = min(
        candidates,
        key=lambda row:
            row[
                "front_mismatch_fraction"
            ],
    )

    best_l1_candidate = min(
        candidates,
        key=lambda row:
            row[
                "global_L1"
            ],
    )

    volume_improvement = (
        accepted[
            "plume_volume_relative_error"
        ]
        -
        best_volume_candidate[
            "plume_volume_relative_error"
        ]
    )

    mismatch_improvement = (
        accepted[
            "front_mismatch_fraction"
        ]
        -
        best_front_candidate[
            "front_mismatch_fraction"
        ]
    )

    # =========================================================================
    # DIAGNOSIS
    # =========================================================================

    front_preserving_candidate_exists = (
        volume_improvement
        >
        0.05
        or
        mismatch_improvement
        >
        0.10
    )

    candidate_preserves_state_accuracy = (
        best_volume_candidate[
            "global_L1"
        ]
        <
        0.01
    )

    if (
        front_preserving_candidate_exists
        and
        candidate_preserves_state_accuracy
    ):

        diagnosis = (
            "AVERAGING_INDUCED_FRONT_SMEARING"
        )

        recommendation = (
            "At least one front-preserving accumulation candidate materially "
            "reduces threshold-defined plume error without sacrificing global "
            "state accuracy. The next milestone should validate a constrained "
            "front-aware operator against conservation and later-time behavior."
        )

        next_milestone = (
            "V15-SG7D-3 — Constrained Front-Aware "
            "Map-Back Candidate Validation"
        )

    elif (
        not front_preserving_candidate_exists
    ):

        diagnosis = (
            "FRONT_DISAGREEMENT_NOT_CONTROLLED_BY_CELL_AVERAGING"
        )

        recommendation = (
            "Alternative cell accumulation statistics do not materially "
            "improve early-time front agreement. Return to streamline sampling "
            "or local front reconstruction geometry rather than replacing the "
            "accepted q*Delta-tau operator."
        )

        next_milestone = (
            "V15-SG7D-2B — Front Geometry / "
            "Subcell Sampling Audit"
        )

    else:

        diagnosis = (
            "FRONT_PRESERVATION_STATE_ACCURACY_TRADEOFF"
        )

        recommendation = (
            "A front-preserving candidate improves plume classification but "
            "degrades continuous saturation accuracy. Do not replace SG7D; "
            "study a localized front-aware hybrid operator."
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
            "Incoming SG7D-1 diagnosis is front classification disagreement",
            (
                sg7d1_summary.get(
                    "diagnosis"
                )
                ==
                "FRONT_CLASSIFICATION_DISAGREEMENT"
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
            "All subsegment geometry finite",
            all(
                np.isfinite(
                    value
                )
                for row
                in subsegment_summary_rows
                for key, value
                in row.items()
                if key
                not in
                {
                    "streamlines",
                    "nodes_per_streamline",
                    "subsegments",
                    "unique_cells",
                }
            ),
        ),

        (
            "All operator metrics finite",
            all(
                np.isfinite(
                    row[
                        "global_L1"
                    ]
                )
                for row
                in metrics_rows
            ),
        ),

        (
            "Authoritative q*dtau operator evaluated",
            any(
                row[
                    "operator"
                ]
                ==
                "q_dtau_mean"
                for row
                in metrics_rows
            ),
        ),

        (
            "Front-preserving candidates evaluated",
            all(
                any(
                    row[
                        "operator"
                    ]
                    ==
                    operator
                    for row
                    in metrics_rows
                )
                for operator
                in [
                    "maximum",
                    "percentile_90",
                ]
            ),
        ),

        (
            "Diagnostic classification established",
            diagnosis
            in
            {
                "AVERAGING_INDUCED_FRONT_SMEARING",
                "FRONT_DISAGREEMENT_NOT_CONTROLLED_BY_CELL_AVERAGING",
                "FRONT_PRESERVATION_STATE_ACCURACY_TRADEOFF",
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
        "V15-SG7D-2 DIAGNOSTIC VALIDATION"
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
        "\n100-DAY AUTHORITATIVE OPERATOR"
    )

    print(
        f"  Operator                 : "
        f"{accepted['operator']}"
    )

    print(
        f"  Global L1                : "
        f"{accepted['global_L1']:.6e}"
    )

    print(
        f"  Volume relative error    : "
        f"{accepted['plume_volume_relative_error']:.3%}"
    )

    print(
        f"  Front mismatch           : "
        f"{accepted['front_mismatch_fraction']:.3%}"
    )

    print(
        "\nBEST DIAGNOSTIC CANDIDATES"
    )

    print(
        f"  Best volume candidate    : "
        f"{best_volume_candidate['operator']}"
    )

    print(
        f"    Volume error           : "
        f"{best_volume_candidate['plume_volume_relative_error']:.3%}"
    )

    print(
        f"    Global L1              : "
        f"{best_volume_candidate['global_L1']:.6e}"
    )

    print(
        f"  Best front candidate     : "
        f"{best_front_candidate['operator']}"
    )

    print(
        f"    Front mismatch         : "
        f"{best_front_candidate['front_mismatch_fraction']:.3%}"
    )

    print(
        f"  Best L1 candidate        : "
        f"{best_l1_candidate['operator']}"
    )

    print(
        f"    Global L1              : "
        f"{best_l1_candidate['global_L1']:.6e}"
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
        OPERATOR_METRICS_FILE,
        metrics_rows,
    )

    save_csv(
        THRESHOLD_FILE,
        threshold_rows,
    )

    save_csv(
        FRONT_FILE,
        front_rows,
    )

    save_csv(
        SUBSEGMENT_FILE,
        subsegment_summary_rows,
    )

    # =========================================================================
    # DATABASE
    # =========================================================================

    np.savez_compressed(
        DATABASE_FILE,

        times_days=
            times,

        operator_names=
            np.asarray(
                OPERATORS,
                dtype=object,
            ),

        cell_index=
            pirnn_segments[
                "cell_index"
            ],

        streamline_index=
            pirnn_segments[
                "streamline_index"
            ],

        subsegment_length_m=
            pirnn_segments[
                "length"
            ],

        subsegment_dtau_s=
            pirnn_segments[
                "dtau"
            ],

        subsegment_qdtau_m3=
            pirnn_segments[
                "qdtau"
            ],
    )

    # =========================================================================
    # PLOTS
    # =========================================================================

    plot_operator_volume_error(
        metrics_rows
    )

    plot_operator_front_mismatch(
        metrics_rows
    )

    plot_100d_operator_maps(
        saved_operator_grids_100d
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7D-2",

        "description":
            (
                "Front-preserving raw streamline-to-grid "
                "accumulation operator study"
            ),

        "source_workspace":
            str(
                source_workspace
            ),

        "authoritative_operator":
            "q_dtau_mean",

        "diagnostic_operators":
            OPERATORS,

        "training_performed":
            False,

        "seed_density_changed":
            False,

        "authoritative_operator_changed":
            False,

        "projection_operator_changed":
            False,

        "100_day_authoritative": {
            "global_L1":
                accepted[
                    "global_L1"
                ],

            "plume_volume_relative_error":
                accepted[
                    "plume_volume_relative_error"
                ],

            "front_mismatch_fraction":
                accepted[
                    "front_mismatch_fraction"
                ],
        },

        "best_volume_candidate": {
            "operator":
                best_volume_candidate[
                    "operator"
                ],

            "volume_error":
                best_volume_candidate[
                    "plume_volume_relative_error"
                ],

            "global_L1":
                best_volume_candidate[
                    "global_L1"
                ],
        },

        "best_front_candidate": {
            "operator":
                best_front_candidate[
                    "operator"
                ],

            "front_mismatch_fraction":
                best_front_candidate[
                    "front_mismatch_fraction"
                ],
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
        f"  {OPERATOR_METRICS_FILE.name}"
    )

    print(
        f"  {THRESHOLD_FILE.name}"
    )

    print(
        f"  {FRONT_FILE.name}"
    )

    print(
        f"  {SUBSEGMENT_FILE.name}"
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
        "  V15SG7D2_Operator_Volume_Error_100d.png"
    )

    print(
        "  V15SG7D2_Front_Mismatch_100d.png"
    )

    print(
        "  V15SG7D2_Authoritative_100d_Layer08.png"
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
            "V15-SG7D-2 STUDY: PASS"
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
            "V15-SG7D-2 STUDY: INCOMPLETE"
        )

        print()

        print(
            "Do not modify the authoritative SG7D operator "
            "until the study inconsistency is resolved."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()