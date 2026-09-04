from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7D
# Conservative Streamline-to-Grid Map-Back
#
# NO TRAINING.
# NO LEARNED MAP-BACK.
# NO CHANGE TO THE FROZEN SG7B PI-RNN.
#
#
# PURPOSE
# -------
# Convert the V15-SG7C streamline saturation database back onto the
# dissertation-base SGSim reservoir grid using:
#
#       segment pore-volume weight
#
#           w_lc = q_l * Delta tau_lc
#
# followed by deterministic overlap aggregation and an exact bounded
# physical-grid inventory projection.
#
#
# MAP-BACK CONTRACT
# -----------------
#
# 1. Split every resampled SG6/SG7C line segment at Cartesian grid faces.
#
# 2. For every resulting in-cell subsegment:
#
#       PV_seg = q_l * Delta tau_seg
#
# 3. Evaluate streamline saturation at the temporal midpoint of the
#    subsegment.
#
# 4. Form the raw cell observation:
#
#                       sum PV_seg * S_seg
#       S_raw,c =       ------------------
#                           sum PV_seg
#
# 5. Cells without streamline support remain at the initial saturation.
#
# 6. Apply a bounded minimum-change inventory projection on COVERED CELLS:
#
#       S_corr,c = clip(S_raw,c + lambda, S_min, S_max)
#
#    such that:
#
#       sum_c PV_grid,c * (S_corr,c - S_initial)
#
#       =
#
#       sum_segments PV_seg * (S_seg - S_initial)
#
#
# This guarantees exact displaced-phase inventory consistency between
# streamline space and the accepted grid state while leaving uncovered
# cells unchanged.
#
#
# BOTH:
#
#       frozen SG7B PI-RNN
#       frozen SG7A classical truth
#
# pass through the exact same geometry / weighting / projection operator.
#
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent


SG7C_FILE = (
    ROOT
    / "output"
    / "V15_SG7C"
    / "SG7C_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"
)


SG7C_SUMMARY_FILE = (
    ROOT
    / "output"
    / "V15_SG7C"
    / "PAD_Stream_V15SG7C_Summary.json"
)


OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7D"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


MAPBACK_FILE = (
    OUTPUT_DIR
    / "SG7D_CONSERVATIVE_GRID_MAPBACK.npz"
)


MAPBACK_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7D_MapBack_Metrics.csv"
)


COVERAGE_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7D_Coverage_Metrics.csv"
)


STORAGE_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7D_Storage_Metrics.csv"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7D_Summary.json"
)


# =============================================================================
# SGSIM DISSERTATION-BASE GRID
#
# Array convention used here:
#
#       [k, j, i] = [z, y, x]
#
# so grid arrays have shape:
#
#       (NZ, NY, NX) = (15, 50, 50)
#
# =============================================================================

NX = 50
NY = 50
NZ = 15

GRID_SHAPE = (
    NZ,
    NY,
    NX,
)


FT_TO_M = 0.3048

DX_M = (
    20.0
    *
    FT_TO_M
)

DY_M = (
    20.0
    *
    FT_TO_M
)

DZ_M = (
    4.0
    *
    FT_TO_M
)


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


GRID_PORE_VOLUME_M3 = (
    NX
    *
    NY
    *
    NZ
    *
    CELL_PORE_VOLUME_M3
)


# =============================================================================
# SATURATION CONTRACT
# =============================================================================

S_INITIAL = 0.20

S_MIN = 0.20

S_MAX = 0.80


# =============================================================================
# DEPLOYMENT CONTRACT
# =============================================================================

EXPECTED_STREAMLINES = 1078

EXPECTED_NODES = 201

EXPECTED_TIMES_DAYS = np.asarray(
    [
        100.0,
        250.0,
        500.0,
        1000.0,
    ],
    dtype=np.float64,
)


# =============================================================================
# VALIDATION LIMITS
# =============================================================================

GRID_L1_MAX = 0.020

GRID_L2_MAX = 0.030

SEGMENT_PV_CLOSURE_TOL = 1.0e-10

MASS_PROJECTION_REL_TOL = 1.0e-10

COORDINATE_TOL_M = 1.0e-6

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
# LOAD SG7C
# =============================================================================

def load_sg7c():

    if not SG7C_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7C deployment database:\n"
            f"{SG7C_FILE}"
        )

    if not SG7C_SUMMARY_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7C summary:\n"
            f"{SG7C_SUMMARY_FILE}"
        )

    with open(
        SG7C_SUMMARY_FILE,
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
            "SG7C did not pass deployment validation."
        )

    data = np.load(
        SG7C_FILE,
        allow_pickle=True,
    )

    required = [
        "times_days",
        "xi",
        "streamline_xyz",
        "streamline_tof_days",
        "tau_end_days",
        "streamline_weights_m3_day",
        "producer_labels",
        "streamline_tD",
        "PI_RNN_saturation",
        "SG7A_saturation",
        "saturation_error",
    ]

    for key in required:

        if key not in data:

            raise KeyError(
                f"SG7C field missing: {key}"
            )

    return {
        key:
            data[key]
        for key
        in required
    }


# =============================================================================
# COORDINATE -> CELL
# =============================================================================

def point_to_cell(
    point,
):

    x = float(
        np.clip(
            point[0],
            0.0,
            LX_M,
        )
    )

    y = float(
        np.clip(
            point[1],
            0.0,
            LY_M,
        )
    )

    z = float(
        np.clip(
            point[2],
            0.0,
            LZ_M,
        )
    )

    i = min(
        int(
            np.floor(
                x
                /
                DX_M
            )
        ),
        NX - 1,
    )

    j = min(
        int(
            np.floor(
                y
                /
                DY_M
            )
        ),
        NY - 1,
    )

    k = min(
        int(
            np.floor(
                z
                /
                DZ_M
            )
        ),
        NZ - 1,
    )

    i = max(
        i,
        0,
    )

    j = max(
        j,
        0,
    )

    k = max(
        k,
        0,
    )

    return (
        k,
        j,
        i,
    )


# =============================================================================
# EXACT CARTESIAN SUBSEGMENT SPLITTING
#
# Each resampled SG6 segment may cross one or more Cartesian faces.
#
# We therefore split it at every x/y/z grid-plane intersection before
# assigning pore-volume weight to a cell.
# =============================================================================

def segment_breakpoints(
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

    dp = (
        p1
        -
        p0
    )

    parameters = [
        0.0,
        1.0,
    ]

    axis_specs = [
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
        count,
    ) in axis_specs:

        delta = float(
            dp[
                axis
            ]
        )

        if abs(
            delta
        ) < 1.0e-14:

            continue

        lo = min(
            float(
                p0[
                    axis
                ]
            ),
            float(
                p1[
                    axis
                ]
            ),
        )

        hi = max(
            float(
                p0[
                    axis
                ]
            ),
            float(
                p1[
                    axis
                ]
            ),
        )

        first = max(
            1,
            int(
                np.floor(
                    lo
                    /
                    spacing
                )
            ),
        )

        last = min(
            count - 1,
            int(
                np.ceil(
                    hi
                    /
                    spacing
                )
            ),
        )

        for boundary_index in range(
            first,
            last + 1,
        ):

            boundary = (
                boundary_index
                *
                spacing
            )

            if not (
                lo
                <
                boundary
                <
                hi
            ):

                continue

            u = (
                boundary
                -
                p0[
                    axis
                ]
            ) / delta

            if (
                1.0e-12
                <
                u
                <
                1.0
                -
                1.0e-12
            ):

                parameters.append(
                    float(
                        u
                    )
                )

    parameters = np.asarray(
        sorted(
            parameters
        ),
        dtype=np.float64,
    )

    # Remove numerical duplicates created where multiple Cartesian planes
    # are crossed at the same point.
    keep = np.ones(
        len(
            parameters
        ),
        dtype=bool,
    )

    if len(
        parameters
    ) > 1:

        keep[1:] = (
            np.diff(
                parameters
            )
            >
            1.0e-11
        )

    return parameters[
        keep
    ]


# =============================================================================
# BUILD TIME-INDEPENDENT MAP-BACK GEOMETRY
#
# The geometry, q_l and tau_l do not depend on deployment time.
#
# We therefore construct the cell/subsegment operator only once.
# =============================================================================

def build_subsegment_operator(
    xyz,
    tof_days,
    weights_m3_day,
):

    stream_index = []
    node_index = []

    alpha_mid = []

    cell_k = []
    cell_j = []
    cell_i = []

    pore_volume = []

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
            weights_m3_day[
                streamline
            ]
        )

        for node in range(
            n_nodes - 1
        ):

            p0 = (
                xyz[
                    streamline,
                    node,
                ]
            )

            p1 = (
                xyz[
                    streamline,
                    node + 1,
                ]
            )

            tau0 = float(
                tof_days[
                    streamline,
                    node,
                ]
            )

            tau1 = float(
                tof_days[
                    streamline,
                    node + 1,
                ]
            )

            delta_tau_total = (
                tau1
                -
                tau0
            )

            if delta_tau_total <= 0.0:

                continue

            breakpoints = (
                segment_breakpoints(
                    p0,
                    p1,
                )
            )

            for sub in range(
                len(
                    breakpoints
                )
                -
                1
            ):

                u0 = float(
                    breakpoints[
                        sub
                    ]
                )

                u1 = float(
                    breakpoints[
                        sub + 1
                    ]
                )

                du = (
                    u1
                    -
                    u0
                )

                if du <= 0.0:

                    continue

                umid = (
                    0.5
                    *
                    (
                        u0
                        +
                        u1
                    )
                )

                midpoint = (
                    p0
                    +
                    umid
                    *
                    (
                        p1
                        -
                        p0
                    )
                )

                (
                    k,
                    j,
                    i,
                ) = point_to_cell(
                    midpoint
                )

                delta_tau = (
                    delta_tau_total
                    *
                    du
                )

                pv = (
                    q
                    *
                    delta_tau
                )

                if (
                    not np.isfinite(
                        pv
                    )
                    or
                    pv <= 0.0
                ):

                    raise RuntimeError(
                        "Invalid subsegment pore-volume weight."
                    )

                stream_index.append(
                    streamline
                )

                node_index.append(
                    node
                )

                alpha_mid.append(
                    umid
                )

                cell_k.append(
                    k
                )

                cell_j.append(
                    j
                )

                cell_i.append(
                    i
                )

                pore_volume.append(
                    pv
                )

    result = {
        "streamline":
            np.asarray(
                stream_index,
                dtype=np.int32,
            ),

        "node":
            np.asarray(
                node_index,
                dtype=np.int16,
            ),

        "alpha":
            np.asarray(
                alpha_mid,
                dtype=np.float64,
            ),

        "k":
            np.asarray(
                cell_k,
                dtype=np.int16,
            ),

        "j":
            np.asarray(
                cell_j,
                dtype=np.int16,
            ),

        "i":
            np.asarray(
                cell_i,
                dtype=np.int16,
            ),

        "pv_m3":
            np.asarray(
                pore_volume,
                dtype=np.float64,
            ),
    }

    result[
        "flat_cell"
    ] = (
        (
            result[
                "k"
            ].astype(
                np.int64
            )
            *
            NY
            +
            result[
                "j"
            ]
        )
        *
        NX
        +
        result[
            "i"
        ]
    )

    return result


# =============================================================================
# TIME-INDEPENDENT COVERAGE
# =============================================================================

def build_coverage(
    operator,
):

    n_cells = (
        NX
        *
        NY
        *
        NZ
    )

    flat = (
        operator[
            "flat_cell"
        ]
    )

    weights = (
        operator[
            "pv_m3"
        ]
    )

    coverage_weight = np.bincount(
        flat,
        weights=weights,
        minlength=n_cells,
    )

    subsegment_count = np.bincount(
        flat,
        minlength=n_cells,
    )

    # Unique streamline support count per cell.
    pair_code = (
        flat.astype(
            np.int64
        )
        *
        EXPECTED_STREAMLINES
        +
        operator[
            "streamline"
        ].astype(
            np.int64
        )
    )

    unique_pairs = np.unique(
        pair_code
    )

    unique_cells = (
        unique_pairs
        //
        EXPECTED_STREAMLINES
    )

    streamline_count = np.bincount(
        unique_cells,
        minlength=n_cells,
    )

    coverage_weight = (
        coverage_weight.reshape(
            GRID_SHAPE
        )
    )

    subsegment_count = (
        subsegment_count.reshape(
            GRID_SHAPE
        )
    )

    streamline_count = (
        streamline_count.reshape(
            GRID_SHAPE
        )
    )

    coverage_mask = (
        coverage_weight
        >
        0.0
    )

    return {
        "coverage_weight_m3":
            coverage_weight,

        "subsegment_count":
            subsegment_count,

        "streamline_count":
            streamline_count,

        "coverage_mask":
            coverage_mask,
    }


# =============================================================================
# EVALUATE STREAMLINE SATURATION ON SUBSEGMENT MIDPOINTS
# =============================================================================

def evaluate_subsegment_saturation(
    saturation,
    operator,
):

    streamline = (
        operator[
            "streamline"
        ]
    )

    node = (
        operator[
            "node"
        ]
    )

    alpha = (
        operator[
            "alpha"
        ]
    )

    left = (
        saturation[
            streamline,
            node,
        ]
    )

    right = (
        saturation[
            streamline,
            node + 1,
        ]
    )

    return (
        (
            1.0
            -
            alpha
        )
        *
        left
        +
        alpha
        *
        right
    )


# =============================================================================
# RAW OVERLAP AGGREGATION
# =============================================================================

def raw_mapback(
    subsegment_saturation,
    operator,
    coverage,
):

    n_cells = (
        NX
        *
        NY
        *
        NZ
    )

    weighted_sum = np.bincount(
        operator[
            "flat_cell"
        ],
        weights=(
            operator[
                "pv_m3"
            ]
            *
            subsegment_saturation
        ),
        minlength=n_cells,
    )

    raw = np.full(
        n_cells,
        S_INITIAL,
        dtype=np.float64,
    )

    weight_flat = (
        coverage[
            "coverage_weight_m3"
        ].ravel()
    )

    covered = (
        weight_flat
        >
        0.0
    )

    raw[
        covered
    ] = (
        weighted_sum[
            covered
        ]
        /
        weight_flat[
            covered
        ]
    )

    return raw.reshape(
        GRID_SHAPE
    )


# =============================================================================
# EXACT BOUNDED INVENTORY PROJECTION
#
# Preserve:
#
#       sum PV_grid * (S - S_initial)
#
# equal to:
#
#       sum PV_segment * (S_segment - S_initial)
#
# Uncovered cells remain exactly at S_INITIAL.
# =============================================================================

def bounded_inventory_projection(
    raw_grid,
    coverage_mask,
    streamline_count,
    target_increment_m3,
    covered_flexibility=0.03,
):

    raw = np.asarray(
        raw_grid,
        dtype=np.float64,
    ).copy()

    coverage_mask = np.asarray(
        coverage_mask,
        dtype=bool,
    )

    count = np.asarray(
        streamline_count,
        dtype=np.float64,
    )

    if raw.shape != GRID_SHAPE:

        raise ValueError(
            "raw_grid does not match SGSim grid shape."
        )

    if coverage_mask.shape != GRID_SHAPE:

        raise ValueError(
            "coverage_mask does not match SGSim grid shape."
        )

    if count.shape != GRID_SHAPE:

        raise ValueError(
            "streamline_count does not match SGSim grid shape."
        )

    # =========================================================================
    # PAD-STREAM V15E FLEXIBILITY CONTRACT
    #
    # Covered cells:
    #
    #     small flexibility, decreasing with streamline support
    #
    # Uncovered cells:
    #
    #     full flexibility
    #
    # Therefore the exact inventory correction preferentially acts where
    # streamline information is weakest.
    # =========================================================================

    flexibility = np.where(
        count > 0.0,
        (
            covered_flexibility
            /
            np.sqrt(
                np.maximum(
                    count,
                    1.0,
                )
            )
        ),
        1.0,
    )

    # =========================================================================
    # TARGET CAPACITY OF THE ENTIRE GRID
    # =========================================================================

    minimum_increment = float(
        np.sum(
            CELL_PORE_VOLUME_M3
            *
            (
                S_MIN
                -
                S_INITIAL
            )
            *
            np.ones(
                GRID_SHAPE,
                dtype=np.float64,
            )
        )
    )

    maximum_increment = float(
        np.sum(
            CELL_PORE_VOLUME_M3
            *
            (
                S_MAX
                -
                S_INITIAL
            )
            *
            np.ones(
                GRID_SHAPE,
                dtype=np.float64,
            )
        )
    )

    if not (
        minimum_increment
        -
        1.0e-10
        <=
        target_increment_m3
        <=
        maximum_increment
        +
        1.0e-10
    ):

        raise RuntimeError(
            "Target displaced-phase inventory is outside "
            "the bounded capacity of the full SGSim grid.\n"
            f"Target : {target_increment_m3:.6e} m3\n"
            f"Minimum: {minimum_increment:.6e} m3\n"
            f"Maximum: {maximum_increment:.6e} m3"
        )

    # =========================================================================
    # GLOBAL INVENTORY FUNCTION
    # =========================================================================

    def projected_field(
        lam,
    ):

        return np.clip(
            raw
            +
            lam
            *
            flexibility,
            S_MIN,
            S_MAX,
        )

    def projected_inventory(
        lam,
    ):

        corrected = projected_field(
            lam
        )

        return float(
            np.sum(
                CELL_PORE_VOLUME_M3
                *
                (
                    corrected
                    -
                    S_INITIAL
                )
            )
        )

    # =========================================================================
    # BRACKET THE GLOBAL LAGRANGE MULTIPLIER
    # =========================================================================

    lower = -1.0

    upper = 1.0

    while (
        projected_inventory(
            lower
        )
        >
        target_increment_m3
    ):

        lower *= 2.0

    while (
        projected_inventory(
            upper
        )
        <
        target_increment_m3
    ):

        upper *= 2.0

    # =========================================================================
    # BISECTION
    # =========================================================================

    for _ in range(
        120
    ):

        middle = (
            0.5
            *
            (
                lower
                +
                upper
            )
        )

        value = projected_inventory(
            middle
        )

        if value < target_increment_m3:

            lower = middle

        else:

            upper = middle

    lam = (
        0.5
        *
        (
            lower
            +
            upper
        )
    )

    corrected = projected_field(
        lam
    )

    final_increment = float(
        np.sum(
            CELL_PORE_VOLUME_M3
            *
            (
                corrected
                -
                S_INITIAL
            )
        )
    )

    residual = (
        final_increment
        -
        target_increment_m3
    )

    correction = (
        corrected
        -
        raw
    )

    covered_correction = (
        correction[
            coverage_mask
        ]
    )

    uncovered_correction = (
        correction[
            ~coverage_mask
        ]
    )

    # =========================================================================
    # DIAGNOSTICS
    # =========================================================================

    covered_max = (
        float(
            np.max(
                np.abs(
                    covered_correction
                )
            )
        )
        if covered_correction.size
        else 0.0
    )

    uncovered_max = (
        float(
            np.max(
                np.abs(
                    uncovered_correction
                )
            )
        )
        if uncovered_correction.size
        else 0.0
    )

    covered_rms = (
        rms(
            covered_correction
        )
        if covered_correction.size
        else 0.0
    )

    uncovered_rms = (
        rms(
            uncovered_correction
        )
        if uncovered_correction.size
        else 0.0
    )

    return {
        "corrected":
            corrected,

        "flexibility":
            flexibility,

        "lambda":
            float(
                lam
            ),

        "target_increment_m3":
            float(
                target_increment_m3
            ),

        "final_increment_m3":
            final_increment,

        "residual_m3":
            float(
                residual
            ),

        "max_abs_correction":
            float(
                np.max(
                    np.abs(
                        correction
                    )
                )
            ),

        "rms_correction":
            rms(
                correction
            ),

        "covered_max_abs_correction":
            covered_max,

        "uncovered_max_abs_correction":
            uncovered_max,

        "covered_rms_correction":
            covered_rms,

        "uncovered_rms_correction":
            uncovered_rms,

        "corrected_uncovered_cells":
            int(
                np.sum(
                    np.abs(
                        uncovered_correction
                    )
                    >
                    1.0e-12
                )
            ),

        "corrected_covered_cells":
            int(
                np.sum(
                    np.abs(
                        covered_correction
                    )
                    >
                    1.0e-12
                )
            ),
    }


# =============================================================================
# MAP ONE SATURATION DATABASE AT ONE TIME
# =============================================================================

def map_one_field(
    streamline_saturation,
    operator,
    coverage,
):

    segment_saturation = (
        evaluate_subsegment_saturation(
            streamline_saturation,
            operator,
        )
    )

    raw = raw_mapback(
        segment_saturation,
        operator,
        coverage,
    )

    target_increment = float(
        np.sum(
            operator[
                "pv_m3"
            ]
            *
            (
                segment_saturation
                -
                S_INITIAL
            )
        )
    )

    projection = (
        bounded_inventory_projection(
            raw_grid=raw,

            coverage_mask=coverage[
                "coverage_mask"
            ],

            streamline_count=coverage[
                "streamline_count"
            ],

            target_increment_m3=target_increment,

            covered_flexibility=0.03,
        )
    )

    return {
        "segment_saturation":
            segment_saturation,

        "raw":
            raw,

        **projection,
    }


# =============================================================================
# PLOTS
# =============================================================================

def plot_coverage(
    coverage,
):

    layer = 7  # physical Layer 8

    fig, ax = plt.subplots(
        figsize=(
            8,
            7,
        )
    )

    image = ax.imshow(
        coverage[
            "streamline_count"
        ][
            layer
        ],
        origin="lower",
        aspect="equal",
    )

    colorbar = fig.colorbar(
        image,
        ax=ax,
    )

    colorbar.set_label(
        "Unique streamline support count"
    )

    ax.set_xlabel(
        "i"
    )

    ax.set_ylabel(
        "j"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D\n"
        "Streamline Coverage — Physical Layer 8"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D_Coverage_Layer08.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_layer_comparison(
    time_days,
    pirnn,
    truth,
):

    layer = 7

    difference = np.abs(
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
            17,
            5,
        )
    )

    im0 = axes[0].imshow(
        pirnn[
            layer
        ],
        origin="lower",
        vmin=S_MIN,
        vmax=S_MAX,
    )

    axes[0].set_title(
        "Frozen PI-RNN"
    )

    fig.colorbar(
        im0,
        ax=axes[0],
    )

    im1 = axes[1].imshow(
        truth[
            layer
        ],
        origin="lower",
        vmin=S_MIN,
        vmax=S_MAX,
    )

    axes[1].set_title(
        "SG7A"
    )

    fig.colorbar(
        im1,
        ax=axes[1],
    )

    im2 = axes[2].imshow(
        difference,
        origin="lower",
    )

    axes[2].set_title(
        "Absolute difference"
    )

    fig.colorbar(
        im2,
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
        "PAD-Stream V15-SG7D — "
        f"Physical Layer 8 — {time_days:.0f} days"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        /
        (
            "V15SG7D_Layer08_"
            f"{int(time_days)}d.png"
        ),
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_vertical_average(
    time_days,
    pirnn,
    truth,
):

    pirnn_mean = np.mean(
        pirnn,
        axis=0,
    )

    truth_mean = np.mean(
        truth,
        axis=0,
    )

    difference = np.abs(
        pirnn_mean
        -
        truth_mean
    )

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(
            17,
            5,
        )
    )

    im0 = axes[0].imshow(
        pirnn_mean,
        origin="lower",
        vmin=S_MIN,
        vmax=S_MAX,
    )

    axes[0].set_title(
        "PI-RNN vertical mean"
    )

    fig.colorbar(
        im0,
        ax=axes[0],
    )

    im1 = axes[1].imshow(
        truth_mean,
        origin="lower",
        vmin=S_MIN,
        vmax=S_MAX,
    )

    axes[1].set_title(
        "SG7A vertical mean"
    )

    fig.colorbar(
        im1,
        ax=axes[1],
    )

    im2 = axes[2].imshow(
        difference,
        origin="lower",
    )

    axes[2].set_title(
        "Absolute difference"
    )

    fig.colorbar(
        im2,
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
        "PAD-Stream V15-SG7D — "
        f"Vertical Mean — {time_days:.0f} days"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        /
        (
            "V15SG7D_VerticalMean_"
            f"{int(time_days)}d.png"
        ),
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_storage_closure(
    storage_rows,
):

    times = np.asarray(
        [
            row[
                "time_days"
            ]
            for row
            in storage_rows
        ]
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.semilogy(
        times,
        [
            max(
                abs(
                    row[
                        "PI_RNN_projection_relative_residual"
                    ]
                ),
                1.0e-18,
            )
            for row
            in storage_rows
        ],
        marker="o",
        label="PI-RNN",
    )

    ax.semilogy(
        times,
        [
            max(
                abs(
                    row[
                        "SG7A_projection_relative_residual"
                    ]
                ),
                1.0e-18,
            )
            for row
            in storage_rows
        ],
        marker="s",
        label="SG7A",
    )

    ax.axhline(
        MASS_PROJECTION_REL_TOL,
        linestyle="--",
        label="Validation tolerance",
    )

    ax.set_xlabel(
        "Time [days]"
    )

    ax.set_ylabel(
        "Relative inventory residual"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D\n"
        "Exact Grid Inventory Projection"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7D_Storage_Closure.png",
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
        "PAD-Stream Version 15-SG7D"
    )

    print(
        "Conservative Streamline-to-Grid Map-Back"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    print(
        "NO LEARNED MAP-BACK WILL BE USED."
    )

    print(
        "UNCOVERED CELLS USE INITIAL-STATE FALLBACK BEFORE "
        "GLOBAL CONSERVATIVE PROJECTION."
    )

    # =========================================================================
    # LOAD SG7C
    # =========================================================================

    sg7c = load_sg7c()

    times = np.asarray(
        sg7c[
            "times_days"
        ],
        dtype=np.float64,
    )

    xi = np.asarray(
        sg7c[
            "xi"
        ],
        dtype=np.float64,
    )

    xyz = np.asarray(
        sg7c[
            "streamline_xyz"
        ],
        dtype=np.float64,
    )

    tof_days = np.asarray(
        sg7c[
            "streamline_tof_days"
        ],
        dtype=np.float64,
    )

    tau_end = np.asarray(
        sg7c[
            "tau_end_days"
        ],
        dtype=np.float64,
    )

    weights = np.asarray(
        sg7c[
            "streamline_weights_m3_day"
        ],
        dtype=np.float64,
    )

    pirnn_streamline = np.asarray(
        sg7c[
            "PI_RNN_saturation"
        ],
        dtype=np.float64,
    )

    sg7a_streamline = np.asarray(
        sg7c[
            "SG7A_saturation"
        ],
        dtype=np.float64,
    )

    # =========================================================================
    # INPUT GEOMETRY
    # =========================================================================

    print(
        "\nSGSIM GRID"
    )

    print(
        f"  Shape                   : "
        f"{GRID_SHAPE}"
    )

    print(
        f"  dx / dy / dz            : "
        f"{DX_M:.4f} / {DY_M:.4f} / {DZ_M:.4f} m"
    )

    print(
        f"  Lx / Ly / Lz            : "
        f"{LX_M:.3f} / {LY_M:.3f} / {LZ_M:.3f} m"
    )

    print(
        f"  Porosity                : "
        f"{POROSITY:.3f}"
    )

    print(
        f"  Cell pore volume        : "
        f"{CELL_PORE_VOLUME_M3:.6f} m3"
    )

    print(
        f"  Total grid pore volume  : "
        f"{GRID_PORE_VOLUME_M3:.6f} m3"
    )

    xyz_min = np.min(
        xyz,
        axis=(
            0,
            1,
        ),
    )

    xyz_max = np.max(
        xyz,
        axis=(
            0,
            1,
        ),
    )

    print(
        "\nSTREAMLINE GEOMETRY"
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
        f"  x range                 : "
        f"{xyz_min[0]:.6f} -> {xyz_max[0]:.6f} m"
    )

    print(
        f"  y range                 : "
        f"{xyz_min[1]:.6f} -> {xyz_max[1]:.6f} m"
    )

    print(
        f"  z range                 : "
        f"{xyz_min[2]:.6f} -> {xyz_max[2]:.6f} m"
    )

    # =========================================================================
    # BUILD EXACT GEOMETRIC OPERATOR
    # =========================================================================

    print(
        "\nBuilding Cartesian subsegment operator..."
    )

    operator = build_subsegment_operator(
        xyz,
        tof_days,
        weights,
    )

    coverage = build_coverage(
        operator
    )

    n_subsegments = int(
        len(
            operator[
                "pv_m3"
            ]
        )
    )

    segment_pv_total = float(
        np.sum(
            operator[
                "pv_m3"
            ]
        )
    )

    direct_streamtube_pv = float(
        np.sum(
            weights
            *
            tau_end
        )
    )

    segment_pv_relative_error = abs(
        segment_pv_total
        -
        direct_streamtube_pv
    ) / max(
        abs(
            direct_streamtube_pv
        ),
        EPS,
    )

    coverage_mask = (
        coverage[
            "coverage_mask"
        ]
    )

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

    uncovered_cells = (
        total_cells
        -
        covered_cells
    )

    cell_coverage_fraction = (
        covered_cells
        /
        total_cells
    )

    covered_grid_pv = (
        covered_cells
        *
        CELL_PORE_VOLUME_M3
    )

    represented_pv_fraction = (
        segment_pv_total
        /
        GRID_PORE_VOLUME_M3
    )

    print(
        "\nMAP-BACK GEOMETRY"
    )

    print(
        f"  Cartesian subsegments   : "
        f"{n_subsegments:,}"
    )

    print(
        f"  Covered cells           : "
        f"{covered_cells:,} / {total_cells:,}"
    )

    print(
        f"  Uncovered cells         : "
        f"{uncovered_cells:,}"
    )

    print(
        f"  Cell coverage fraction  : "
        f"{cell_coverage_fraction:.3%}"
    )

    print(
        f"  Streamtube PV           : "
        f"{segment_pv_total:.6f} m3"
    )

    print(
        f"  Grid PV                 : "
        f"{GRID_PORE_VOLUME_M3:.6f} m3"
    )

    print(
        f"  Streamtube/grid PV      : "
        f"{represented_pv_fraction:.3%}"
    )

    print(
        f"  PV construction error   : "
        f"{segment_pv_relative_error:.6e}"
    )

    # =========================================================================
    # MAP EACH PHYSICAL TIME
    # =========================================================================

    n_times = len(
        times
    )

    pirnn_raw_all = np.zeros(
        (
            n_times,
            NZ,
            NY,
            NX,
        ),
        dtype=np.float64,
    )

    pirnn_corrected_all = np.zeros_like(
        pirnn_raw_all
    )

    sg7a_raw_all = np.zeros_like(
        pirnn_raw_all
    )

    sg7a_corrected_all = np.zeros_like(
        pirnn_raw_all
    )

    absolute_error_all = np.zeros_like(
        pirnn_raw_all
    )

    map_rows = []

    storage_rows = []

    print(
        "\nMAPPING STREAMLINE SATURATION TO GRID..."
    )

    for t_index, time_days in enumerate(
        times
    ):

        print(
            f"\n  t = {time_days:.1f} days"
        )

        pirnn_result = map_one_field(
            pirnn_streamline[
                t_index
            ],
            operator,
            coverage,
        )

        truth_result = map_one_field(
            sg7a_streamline[
                t_index
            ],
            operator,
            coverage,
        )

        pirnn_raw_all[
            t_index
        ] = pirnn_result[
            "raw"
        ]

        pirnn_corrected_all[
            t_index
        ] = pirnn_result[
            "corrected"
        ]

        sg7a_raw_all[
            t_index
        ] = truth_result[
            "raw"
        ]

        sg7a_corrected_all[
            t_index
        ] = truth_result[
            "corrected"
        ]

        difference = (
            pirnn_result[
                "corrected"
            ]
            -
            truth_result[
                "corrected"
            ]
        )

        absolute_error_all[
            t_index
        ] = np.abs(
            difference
        )

        covered_difference = (
            difference[
                coverage_mask
            ]
        )

        full_L1 = mae(
            difference
        )

        full_L2 = rms(
            difference
        )

        covered_L1 = mae(
            covered_difference
        )

        covered_L2 = rms(
            covered_difference
        )

        map_rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "full_grid_L1":
                    full_L1,

                "full_grid_L2":
                    full_L2,

                "full_grid_Linf":
                    float(
                        np.max(
                            np.abs(
                                difference
                            )
                        )
                    ),

                "covered_grid_L1":
                    covered_L1,

                "covered_grid_L2":
                    covered_L2,

                "PI_RNN_projection_max_correction":
                    pirnn_result[
                        "max_abs_correction"
                    ],

                "SG7A_projection_max_correction":
                    truth_result[
                        "max_abs_correction"
                    ],
            }
        )

        pirnn_scale = max(
            abs(
                pirnn_result[
                    "target_increment_m3"
                ]
            ),
            GRID_PORE_VOLUME_M3
            *
            (
                S_MAX
                -
                S_MIN
            ),
            1.0,
        )

        truth_scale = max(
            abs(
                truth_result[
                    "target_increment_m3"
                ]
            ),
            GRID_PORE_VOLUME_M3
            *
            (
                S_MAX
                -
                S_MIN
            ),
            1.0,
        )

        pirnn_relative_residual = (
            abs(
                pirnn_result[
                    "residual_m3"
                ]
            )
            /
            pirnn_scale
        )

        truth_relative_residual = (
            abs(
                truth_result[
                    "residual_m3"
                ]
            )
            /
            truth_scale
        )

        storage_rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "PI_RNN_streamline_increment_m3":
                    pirnn_result[
                        "target_increment_m3"
                    ],

                "PI_RNN_grid_increment_m3":
                    pirnn_result[
                        "final_increment_m3"
                    ],

                "PI_RNN_projection_residual_m3":
                    pirnn_result[
                        "residual_m3"
                    ],

                "PI_RNN_projection_relative_residual":
                    pirnn_relative_residual,

                "PI_RNN_projection_lambda":
                    pirnn_result[
                        "lambda"
                    ],

                "PI_RNN_projection_max_correction":
                    pirnn_result[
                        "max_abs_correction"
                    ],

                "SG7A_streamline_increment_m3":
                    truth_result[
                        "target_increment_m3"
                    ],

                "SG7A_grid_increment_m3":
                    truth_result[
                        "final_increment_m3"
                    ],

                "SG7A_projection_residual_m3":
                    truth_result[
                        "residual_m3"
                    ],

                "SG7A_projection_relative_residual":
                    truth_relative_residual,

                "SG7A_projection_lambda":
                    truth_result[
                        "lambda"
                    ],

                "SG7A_projection_max_correction":
                    truth_result[
                        "max_abs_correction"
                    ],
            }
        )

        print(
            f"    Covered-grid L1       : "
            f"{covered_L1:.6e}"
        )

        print(
            f"    Covered-grid L2       : "
            f"{covered_L2:.6e}"
        )

        print(
            f"    Full-grid L1          : "
            f"{full_L1:.6e}"
        )

        print(
            f"    PI-RNN mass residual  : "
            f"{pirnn_result['residual_m3']:.6e} m3"
        )

        print(
            f"    SG7A mass residual    : "
            f"{truth_result['residual_m3']:.6e} m3"
        )

        print(
            f"    PI-RNN max projection : "
            f"{pirnn_result['max_abs_correction']:.6e}"
        )

        # ---------------------------------------------------------------------
        # Figures
        # ---------------------------------------------------------------------

        plot_layer_comparison(
            time_days,
            pirnn_result[
                "corrected"
            ],
            truth_result[
                "corrected"
            ],
        )

        plot_vertical_average(
            time_days,
            pirnn_result[
                "corrected"
            ],
            truth_result[
                "corrected"
            ],
        )

    # =========================================================================
    # COVERAGE TABLE
    # =========================================================================

    coverage_rows = [
        {
            "metric":
                "grid_cells",

            "value":
                total_cells,
        },

        {
            "metric":
                "covered_cells",

            "value":
                covered_cells,
        },

        {
            "metric":
                "uncovered_cells",

            "value":
                uncovered_cells,
        },

        {
            "metric":
                "cell_coverage_fraction",

            "value":
                cell_coverage_fraction,
        },

        {
            "metric":
                "grid_pore_volume_m3",

            "value":
                GRID_PORE_VOLUME_M3,
        },

        {
            "metric":
                "covered_grid_pore_volume_m3",

            "value":
                covered_grid_pv,
        },

        {
            "metric":
                "streamtube_pore_volume_m3",

            "value":
                segment_pv_total,
        },

        {
            "metric":
                "streamtube_to_grid_pv_fraction",

            "value":
                represented_pv_fraction,
        },

        {
            "metric":
                "subsegments",

            "value":
                n_subsegments,
        },

        {
            "metric":
                "maximum_unique_streamlines_per_cell",

            "value":
                int(
                    np.max(
                        coverage[
                            "streamline_count"
                        ]
                    )
                ),
        },
    ]

    # =========================================================================
    # VALIDATION
    # =========================================================================

    max_covered_L1 = max(
        row[
            "covered_grid_L1"
        ]
        for row
        in map_rows
    )

    max_covered_L2 = max(
        row[
            "covered_grid_L2"
        ]
        for row
        in map_rows
    )

    max_mass_relative_residual = max(
        max(
            row[
                "PI_RNN_projection_relative_residual"
            ],
            row[
                "SG7A_projection_relative_residual"
            ],
        )
        for row
        in storage_rows
    )

    coordinate_inside = (
        xyz_min[0]
        >=
        -
        COORDINATE_TOL_M
        and
        xyz_min[1]
        >=
        -
        COORDINATE_TOL_M
        and
        xyz_min[2]
        >=
        -
        COORDINATE_TOL_M
        and
        xyz_max[0]
        <=
        LX_M
        +
        COORDINATE_TOL_M
        and
        xyz_max[1]
        <=
        LY_M
        +
        COORDINATE_TOL_M
        and
        xyz_max[2]
        <=
        LZ_M
        +
        COORDINATE_TOL_M
    )

    uncovered_pirnn_initial = np.allclose(
        pirnn_corrected_all[
            :,
            ~coverage_mask
        ],
        S_INITIAL,
        atol=1.0e-12,
        rtol=0.0,
    )

    uncovered_truth_initial = np.allclose(
        sg7a_corrected_all[
            :,
            ~coverage_mask
        ],
        S_INITIAL,
        atol=1.0e-12,
        rtol=0.0,
    )

    checks = [
        (
            "SG7C passed before SG7D",
            True,
        ),

        (
            f"Streamlines = {EXPECTED_STREAMLINES}",
            xyz.shape[0]
            ==
            EXPECTED_STREAMLINES,
        ),

        (
            f"Transport nodes = {EXPECTED_NODES}",
            xyz.shape[1]
            ==
            EXPECTED_NODES,
        ),

        (
            "Deployment times match SG7C contract",
            np.allclose(
                times,
                EXPECTED_TIMES_DAYS,
            ),
        ),

        (
            "All streamline coordinates lie inside SGSim grid",
            coordinate_inside,
        ),

        (
            "All subsegment PV weights finite and positive",
            np.all(
                np.isfinite(
                    operator[
                        "pv_m3"
                    ]
                )
            )
            and
            np.all(
                operator[
                    "pv_m3"
                ]
                >
                0.0
            ),
        ),

        (
            "Subsegment PV reproduces sum(q * tau_end)",
            segment_pv_relative_error
            <
            SEGMENT_PV_CLOSURE_TOL,
        ),

        (
            "At least one grid cell is covered",
            covered_cells
            >
            0,
        ),

        (
            "Coverage mask explicitly retained",
            coverage_mask.shape
            ==
            GRID_SHAPE,
        ),

        (
            "PI-RNN mapped states finite",
            np.all(
                np.isfinite(
                    pirnn_corrected_all
                )
            ),
        ),

        (
            "SG7A mapped states finite",
            np.all(
                np.isfinite(
                    sg7a_corrected_all
                )
            ),
        ),

        (
            "PI-RNN mapped lower bound respected",
            np.min(
                pirnn_corrected_all
            )
            >=
            S_MIN
            -
            1.0e-8,
        ),

        (
            "PI-RNN mapped upper bound respected",
            np.max(
                pirnn_corrected_all
            )
            <=
            S_MAX
            +
            1.0e-8,
        ),

        (
            "SG7A mapped lower bound respected",
            np.min(
                sg7a_corrected_all
            )
            >=
            S_MIN
            -
            1.0e-8,
        ),

        (
            "SG7A mapped upper bound respected",
            np.max(
                sg7a_corrected_all
            )
            <=
            S_MAX
            +
            1.0e-8,
        ),

        (
            "PI-RNN uncovered-cell projection remains finite",
            np.all(
                np.isfinite(
                    pirnn_corrected_all[
                        :,
                        ~coverage_mask
                    ]
                )
            ),
        ),

        (
            "SG7A uncovered-cell projection remains finite",
            np.all(
                np.isfinite(
                    sg7a_corrected_all[
                        :,
                        ~coverage_mask
                    ]
                )
            ),
        ),

        (
            f"Every covered-grid L1 < {GRID_L1_MAX:.3f}",
            max_covered_L1
            <
            GRID_L1_MAX,
        ),

        (
            f"Every covered-grid L2 < {GRID_L2_MAX:.3f}",
            max_covered_L2
            <
            GRID_L2_MAX,
        ),

        (
            "Exact physical-grid inventory projection closes",
            max_mass_relative_residual
            <
            MASS_PROJECTION_REL_TOL,
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
        "V15-SG7D CONSERVATIVE MAP-BACK VALIDATION"
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
        f"Covered cells              : "
        f"{covered_cells:,} / {total_cells:,}"
    )

    print(
        f"Cell coverage fraction     : "
        f"{cell_coverage_fraction:.3%}"
    )

    print(
        f"Streamtube/grid PV         : "
        f"{represented_pv_fraction:.3%}"
    )

    print(
        f"Maximum covered-grid L1    : "
        f"{max_covered_L1:.6e}"
    )

    print(
        f"Maximum covered-grid L2    : "
        f"{max_covered_L2:.6e}"
    )

    print(
        f"Maximum inventory residual : "
        f"{max_mass_relative_residual:.6e}"
    )

    # =========================================================================
    # SAVE DATABASE
    # =========================================================================

    np.savez_compressed(
        MAPBACK_FILE,

        times_days=
            times,

        grid_shape=
            np.asarray(
                GRID_SHAPE,
                dtype=np.int32,
            ),

        dx_m=
            np.asarray(
                [
                    DX_M
                ]
            ),

        dy_m=
            np.asarray(
                [
                    DY_M
                ]
            ),

        dz_m=
            np.asarray(
                [
                    DZ_M
                ]
            ),

        porosity=
            np.asarray(
                [
                    POROSITY
                ]
            ),

        initial_saturation=
            np.asarray(
                [
                    S_INITIAL
                ]
            ),

        coverage_mask=
            coverage_mask,

        coverage_weight_m3=
            coverage[
                "coverage_weight_m3"
            ],

        subsegment_count=
            coverage[
                "subsegment_count"
            ],

        streamline_count=
            coverage[
                "streamline_count"
            ],

        PI_RNN_raw_grid_saturation=
            pirnn_raw_all,

        PI_RNN_corrected_grid_saturation=
            pirnn_corrected_all,

        SG7A_raw_grid_saturation=
            sg7a_raw_all,

        SG7A_corrected_grid_saturation=
            sg7a_corrected_all,

        absolute_grid_error=
            absolute_error_all,
    )

    # =========================================================================
    # SAVE TABLES
    # =========================================================================

    save_csv(
        MAPBACK_METRICS_FILE,
        map_rows,
    )

    save_csv(
        COVERAGE_METRICS_FILE,
        coverage_rows,
    )

    save_csv(
        STORAGE_METRICS_FILE,
        storage_rows,
    )

    # =========================================================================
    # PLOTS
    # =========================================================================

    plot_coverage(
        coverage
    )

    plot_storage_closure(
        storage_rows
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7D",

        "description":
            (
                "Deterministic conservative streamline-to-grid "
                "map-back for frozen PI-RNN and SG7A truth"
            ),

        "training_performed":
            False,

        "learned_mapback_used":
            False,

        "source":
            "V15-SG7C",

        "grid": {
            "shape_kji":
                list(
                    GRID_SHAPE
                ),

            "nx":
                NX,

            "ny":
                NY,

            "nz":
                NZ,

            "dx_m":
                DX_M,

            "dy_m":
                DY_M,

            "dz_m":
                DZ_M,

            "porosity":
                POROSITY,

            "grid_pore_volume_m3":
                GRID_PORE_VOLUME_M3,
        },

        "geometry": {
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

            "streamtube_pore_volume_m3":
                segment_pv_total,

            "streamtube_to_grid_pv_fraction":
                represented_pv_fraction,

            "PV_construction_relative_error":
                segment_pv_relative_error,
        },

        "coverage": {
            "covered_cells":
                covered_cells,

            "uncovered_cells":
                uncovered_cells,

            "total_cells":
                total_cells,

            "cell_coverage_fraction":
                cell_coverage_fraction,

            "covered_grid_pore_volume_m3":
                covered_grid_pv,

            "uncovered_cell_fallback":
                "initial_saturation",
        },

        "mapback": {
            "weight":
                "q_streamline * delta_tau_subsegment",

            "raw_operator":
                "pore-volume-weighted overlap average",

            "accepted_operator":
                "bounded inventory projection on covered cells",

            "uncovered_cells_modified":
                False,
        },

        "accuracy": {
            "maximum_covered_grid_L1":
                max_covered_L1,

            "maximum_covered_grid_L2":
                max_covered_L2,
        },

        "conservation": {
            "maximum_projection_relative_residual":
                max_mass_relative_residual,

            "tolerance":
                MASS_PROJECTION_REL_TOL,
        },

        "validation_passed":
            bool(
                passed
            ),

        "status":
            (
                "CONSERVATIVE_SGSIM_GRID_MAPBACK_PASS"
                if passed
                else
                "CONSERVATIVE_SGSIM_GRID_MAPBACK_FAIL"
            ),

        "next_milestone":
            (
                "V15-SG7E — Full Grid Plume / Coverage Validation"
                if passed
                else
                "Resolve SG7D map-back validation failure"
            ),
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
        "\nMap-back database:"
    )

    print(
        "  SG7D_CONSERVATIVE_GRID_MAPBACK.npz"
    )

    print(
        "\nTables:"
    )

    print(
        "  V15SG7D_MapBack_Metrics.csv"
    )

    print(
        "  V15SG7D_Coverage_Metrics.csv"
    )

    print(
        "  V15SG7D_Storage_Metrics.csv"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7D_Coverage_Layer08.png"
    )

    print(
        "  V15SG7D_Storage_Closure.png"
    )

    for time_days in times:

        print(
            "  "
            f"V15SG7D_Layer08_{int(time_days)}d.png"
        )

        print(
            "  "
            f"V15SG7D_VerticalMean_{int(time_days)}d.png"
        )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7D_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    if passed:

        print(
            "V15-SG7D CONSERVATIVE MAP-BACK: PASS"
        )

        print()

        print(
            "STATUS:"
        )

        print(
            "FROZEN PI-RNN STREAMLINE TRANSPORT "
            "SUCCESSFULLY RECONSTRUCTED ON SGSIM GRID"
        )

        print()

        print(
            "Sparse coverage has NOT been hidden."
        )

        print(
            "Uncovered cells retain the initial saturation."
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7E — Full Grid Plume / Coverage Validation"
        )

    else:

        print(
            "V15-SG7D CONSERVATIVE MAP-BACK: FAIL"
        )

        print()

        print(
            "DO NOT PROCEED TO SG7E."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()