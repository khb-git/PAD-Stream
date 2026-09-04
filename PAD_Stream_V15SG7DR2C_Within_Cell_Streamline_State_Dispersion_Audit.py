from __future__ import annotations

from pathlib import Path
import argparse
import csv
import json
import math

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7D-R2C
# Within-Cell Streamline-State Dispersion Audit
#
# NO TRAINING.
# NO MODEL CHANGE.
# NO SEED-DENSITY CHANGE.
# NO MAP-BACK CHANGE.
# NO CONSERVATIVE PROJECTION CHANGE.
# NO PLUME-THRESHOLD CHANGE.
#
# PURPOSE
# -------
# SG7D-R2 established that the remaining 100-day raw-grid false positives are
# NOT a sparse-support problem:
#
#   total raw false positives = 3,752
#   N<=3 share               = 9.17%
#   N>=8 share               = 69.14%
#
# Diagnosis:
#
#   HIGH_SUPPORT_AVERAGING_OR_THRESHOLD_EFFECT
#
# SG7D-R2C reconstructs the Cartesian streamline subsegments directly from the
# unchanged SG6/SG7C-R geometry and evaluates the within-cell distributions of
# PI-RNN and SG7A streamline states BEFORE q*Delta-tau cell averaging.
#
# For every Cartesian subsegment m crossing cell c:
#
#       w_m = q_streamline * Delta tau_m
#
# and the raw SG7D cell value is reconstructed as:
#
#                  sum_m w_m S_m
#       S_bar_c = -----------------
#                     sum_m w_m
#
# The audit validates that this reconstruction reproduces the persisted SG7D-R
# raw grid, then studies false-positive cells using:
#
#   - weighted mean
#   - weighted standard deviation
#   - weighted P10 / P50 / P90
#   - minimum / maximum
#   - fraction of subsegment weight above S=0.21
#   - PI-RNN vs SG7A within-cell dispersion
#   - mixed-front occupancy
#
# Diagnostic outcomes:
#
#   MIXED_SUBCELL_FRONT_AVERAGING
#   SYSTEMATIC_STREAMLINE_STATE_OFFSET
#   MIXED_AVERAGING_AND_STATE_OFFSET
#   WITHIN_CELL_DISPERSION_NOT_EXPLANATORY
#
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

SG7CR_DATABASE = (
    ROOT
    / "output"
    / "V15_SG7CR"
    / "SG7CR_FRONT_AWARE_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"
)

SG7DR_DATABASE = (
    ROOT
    / "output"
    / "V15_SG7DR"
    / "SG7DR_FRONT_AWARE_CONSERVATIVE_GRID_MAPBACK.npz"
)

SG7DR2_SUMMARY = (
    ROOT
    / "output"
    / "V15_SG7DR2"
    / "PAD_Stream_V15SG7DR2_Summary.json"
)

SG7DR2_DATABASE = (
    ROOT
    / "output"
    / "V15_SG7DR2"
    / "V15SG7DR2_Support_Aware_Raw_MapBack_Audit.npz"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7DR2C"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

CELL_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7DR2C_False_Positive_Cell_Dispersion.csv"
)

SUPPORT_BIN_FILE = (
    OUTPUT_DIR
    / "V15SG7DR2C_Dispersion_By_Support.csv"
)

GLOBAL_FILE = (
    OUTPUT_DIR
    / "V15SG7DR2C_Global_Subsegment_Reconstruction.csv"
)

DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7DR2C_Within_Cell_Dispersion_Audit.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7DR2C_Summary.json"
)


# =============================================================================
# CONTRACT
# =============================================================================

PRIMARY_TIME_DAYS = 100.0
PLUME_THRESHOLD = 0.210

# Raw reconstruction should agree closely with the persisted SG7D-R raw field.
RAW_RECONSTRUCTION_LINF_TOL = 5.0e-5
RAW_RECONSTRUCTION_L1_TOL = 5.0e-6

# A cell is "mixed" if materially different fractions of subsegment weight lie
# above and below the threshold.
MIXED_WEIGHT_LOW = 0.10
MIXED_WEIGHT_HIGH = 0.90

# A systematic streamline-state offset is considered material when PI-RNN is
# shifted upward from SG7A by at least this weighted-mean amount in FP cells.
MATERIAL_MEAN_OFFSET = 2.5e-3

# Classification logic.
MIXED_FP_SHARE_GATE = 0.50
OFFSET_FP_SHARE_GATE = 0.50

EPS = 1.0e-14


# =============================================================================
# HELPERS
# =============================================================================

def load_json(path: Path):

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


def find_time_index(
    times,
    target,
):

    times = np.asarray(
        times,
        dtype=np.float64,
    )

    idx = int(
        np.argmin(
            np.abs(
                times - float(target)
            )
        )
    )

    if abs(
        times[idx] - target
    ) > 1.0e-6:

        raise RuntimeError(
            f"Could not locate {target} days."
        )

    return idx


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

    total = np.sum(
        weights
    )

    if total <= EPS:

        return np.nan

    return float(
        np.sum(
            weights * values
        ) / total
    )


def weighted_std(
    values,
    weights,
):

    mu = weighted_mean(
        values,
        weights,
    )

    if not np.isfinite(
        mu
    ):

        return np.nan

    weights = np.asarray(
        weights,
        dtype=np.float64,
    )

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    total = np.sum(
        weights
    )

    return float(
        np.sqrt(
            np.sum(
                weights
                *
                (values - mu) ** 2
            )
            /
            max(
                total,
                EPS,
            )
        )
    )


def weighted_percentile(
    values,
    weights,
    percentile,
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

    order = np.argsort(
        values
    )

    v = values[
        order
    ]

    w = weights[
        order
    ]

    cumulative = np.cumsum(
        w
    )

    total = cumulative[
        -1
    ]

    if total <= EPS:

        return np.nan

    target = (
        float(percentile)
        /
        100.0
        *
        total
    )

    idx = int(
        np.searchsorted(
            cumulative,
            target,
            side="left",
        )
    )

    idx = min(
        idx,
        len(v) - 1,
    )

    return float(
        v[
            idx
        ]
    )


def cell_flat_index(
    k,
    j,
    i,
    ny,
    nx,
):

    return (
        int(k)
        *
        ny
        *
        nx
        +
        int(j)
        *
        nx
        +
        int(i)
    )


def split_segment_cartesian(
    p0,
    p1,
    tau0,
    tau1,
    dx,
    dy,
    dz,
    nx,
    ny,
    nz,
):

    """
    Split one straight streamline segment at every Cartesian cell boundary.

    Returns tuples:
        (k, j, i, a0, a1, dtau_sub)

    where a0/a1 are local segment fractions in [0,1].
    """

    p0 = np.asarray(
        p0,
        dtype=np.float64,
    )

    p1 = np.asarray(
        p1,
        dtype=np.float64,
    )

    delta = (
        p1 - p0
    )

    cuts = [
        0.0,
        1.0,
    ]

    for axis, (
        spacing,
        ncell,
    ) in enumerate(
        [
            (dx, nx),
            (dy, ny),
            (dz, nz),
        ]
    ):

        d = delta[
            axis
        ]

        if abs(
            d
        ) <= 1.0e-15:

            continue

        lo = min(
            p0[axis],
            p1[axis],
        )

        hi = max(
            p0[axis],
            p1[axis],
        )

        first = int(
            math.floor(
                lo / spacing
            )
        ) + 1

        last = int(
            math.floor(
                hi / spacing
            )
        )

        first = max(
            first,
            1,
        )

        last = min(
            last,
            ncell - 1,
        )

        for boundary_idx in range(
            first,
            last + 1,
        ):

            boundary = (
                boundary_idx
                *
                spacing
            )

            a = (
                boundary
                -
                p0[axis]
            ) / d

            if (
                a > 1.0e-12
                and
                a < 1.0 - 1.0e-12
            ):

                cuts.append(
                    float(a)
                )

    cuts = np.asarray(
        sorted(
            set(
                cuts
            )
        ),
        dtype=np.float64,
    )

    dtau = float(
        tau1 - tau0
    )

    result = []

    for left, right in zip(
        cuts[:-1],
        cuts[1:],
    ):

        if right - left <= 1.0e-14:

            continue

        mid = (
            0.5
            *
            (
                left + right
            )
        )

        pmid = (
            p0
            +
            mid
            *
            delta
        )

        i = int(
            np.floor(
                pmid[0] / dx
            )
        )

        j = int(
            np.floor(
                pmid[1] / dy
            )
        )

        k = int(
            np.floor(
                pmid[2] / dz
            )
        )

        i = min(
            max(
                i,
                0,
            ),
            nx - 1,
        )

        j = min(
            max(
                j,
                0,
            ),
            ny - 1,
        )

        k = min(
            max(
                k,
                0,
            ),
            nz - 1,
        )

        result.append(
            (
                k,
                j,
                i,
                float(left),
                float(right),
                float(
                    dtau
                    *
                    (
                        right - left
                    )
                ),
            )
        )

    return result


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "PAD-Stream V15-SG7D-R2C within-cell streamline-state "
            "dispersion audit."
        )
    )

    parser.parse_args()

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7D-R2C"
    )

    print(
        "Within-Cell Streamline-State Dispersion Audit"
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
        "NO SEED DENSITY WILL BE CHANGED."
    )

    print(
        "NO MAP-BACK OPERATOR WILL BE CHANGED."
    )

    print(
        "NO CONSERVATIVE PROJECTION WILL BE CHANGED."
    )

    print(
        "NO PLUME THRESHOLD WILL BE CHANGED."
    )

    # =========================================================================
    # PRECONDITIONS
    # =========================================================================

    for path in [
        SG7CR_DATABASE,
        SG7DR_DATABASE,
        SG7DR2_SUMMARY,
        SG7DR2_DATABASE,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"Missing SG7D-R2C prerequisite:\n{path}"
            )

    sg7dr2_summary = load_json(
        SG7DR2_SUMMARY
    )

    if (
        sg7dr2_summary.get(
            "diagnosis"
        )
        !=
        "HIGH_SUPPORT_AVERAGING_OR_THRESHOLD_EFFECT"
    ):

        raise RuntimeError(
            "SG7D-R2C requires SG7D-R2 diagnosis:\n"
            "HIGH_SUPPORT_AVERAGING_OR_THRESHOLD_EFFECT"
        )

    sg7cr = np.load(
        SG7CR_DATABASE,
        allow_pickle=True,
    )

    sg7dr = np.load(
        SG7DR_DATABASE,
        allow_pickle=True,
    )

    sg7dr2 = np.load(
        SG7DR2_DATABASE,
        allow_pickle=True,
    )

    # =========================================================================
    # AUTHORITATIVE INPUTS
    # =========================================================================

    times = np.asarray(
        sg7cr[
            "times_days"
        ],
        dtype=np.float64,
    )

    i100 = find_time_index(
        times,
        PRIMARY_TIME_DAYS,
    )

    xyz = np.asarray(
        sg7cr[
            "xyz_m"
        ],
        dtype=np.float64,
    )

    tau_s = np.asarray(
        sg7cr[
            "tau_s"
        ],
        dtype=np.float64,
    )

    weights_q = np.asarray(
        sg7cr[
            "weights_m3_s"
        ],
        dtype=np.float64,
    )

    pirnn_profiles = np.asarray(
        sg7cr[
            "PI_RNN_saturation"
        ],
        dtype=np.float64,
    )[
        i100
    ]

    sg7a_profiles = np.asarray(
        sg7cr[
            "SG7A_saturation"
        ],
        dtype=np.float64,
    )[
        i100
    ]

    grid_shape = tuple(
        np.asarray(
            sg7dr[
                "grid_shape"
            ]
        ).astype(
            int
        ).tolist()
    )

    nz, ny, nx = grid_shape

    dx = float(
        np.asarray(
            sg7dr[
                "dx_m"
            ]
        ).reshape(
            -1
        )[
            0
        ]
    )

    dy = float(
        np.asarray(
            sg7dr[
                "dy_m"
            ]
        ).reshape(
            -1
        )[
            0
        ]
    )

    dz = float(
        np.asarray(
            sg7dr[
                "dz_m"
            ]
        ).reshape(
            -1
        )[
            0
        ]
    )

    raw_grid_pirnn = np.asarray(
        sg7dr[
            "PI_RNN_raw_grid_saturation"
        ],
        dtype=np.float64,
    )[
        i100
    ]

    raw_grid_sg7a = np.asarray(
        sg7dr[
            "SG7A_raw_grid_saturation"
        ],
        dtype=np.float64,
    )[
        i100
    ]

    support_count_reference = np.asarray(
        sg7dr2[
            "support_count"
        ],
        dtype=np.int64,
    )

    false_positive = np.asarray(
        sg7dr2[
            "false_positive_mask"
        ],
        dtype=bool,
    )

    print(
        "\nRECONSTRUCTION CONTRACT"
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
        f"  Grid                    : "
        f"{grid_shape}"
    )

    print(
        f"  dx / dy / dz            : "
        f"{dx:.4f} / {dy:.4f} / {dz:.4f} m"
    )

    print(
        f"  100-day false positives : "
        f"{np.sum(false_positive):,}"
    )

    # =========================================================================
    # REBUILD SUBSEGMENT DATABASE
    # =========================================================================

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "RECONSTRUCTING CARTESIAN SUBSEGMENT STATE DATABASE"
    )

    print(
        "=" * 78
    )

    cell_index_list = []
    streamline_list = []
    weight_list = []
    pirnn_state_list = []
    sg7a_state_list = []

    n_streamlines = xyz.shape[
        0
    ]

    n_nodes = xyz.shape[
        1
    ]

    for s in range(
        n_streamlines
    ):

        q = float(
            weights_q[
                s
            ]
        )

        for n in range(
            n_nodes - 1
        ):

            tau0 = float(
                tau_s[
                    s,
                    n
                ]
            )

            tau1 = float(
                tau_s[
                    s,
                    n + 1
                ]
            )

            if (
                not np.isfinite(
                    tau0
                )
                or
                not np.isfinite(
                    tau1
                )
                or
                tau1 <= tau0
            ):

                continue

            pieces = split_segment_cartesian(
                xyz[
                    s,
                    n
                ],
                xyz[
                    s,
                    n + 1
                ],
                tau0,
                tau1,
                dx,
                dy,
                dz,
                nx,
                ny,
                nz,
            )

            sp0 = float(
                pirnn_profiles[
                    s,
                    n
                ]
            )

            sp1 = float(
                pirnn_profiles[
                    s,
                    n + 1
                ]
            )

            st0 = float(
                sg7a_profiles[
                    s,
                    n
                ]
            )

            st1 = float(
                sg7a_profiles[
                    s,
                    n + 1
                ]
            )

            for (
                k,
                j,
                i,
                a0,
                a1,
                dtau_sub,
            ) in pieces:

                amid = (
                    0.5
                    *
                    (
                        a0 + a1
                    )
                )

                sp = (
                    sp0
                    +
                    amid
                    *
                    (
                        sp1 - sp0
                    )
                )

                st = (
                    st0
                    +
                    amid
                    *
                    (
                        st1 - st0
                    )
                )

                w = (
                    q
                    *
                    dtau_sub
                )

                if (
                    not np.isfinite(
                        w
                    )
                    or
                    w <= 0.0
                ):

                    continue

                cell_index_list.append(
                    cell_flat_index(
                        k,
                        j,
                        i,
                        ny,
                        nx,
                    )
                )

                streamline_list.append(
                    s
                )

                weight_list.append(
                    w
                )

                pirnn_state_list.append(
                    sp
                )

                sg7a_state_list.append(
                    st
                )

    cell_index = np.asarray(
        cell_index_list,
        dtype=np.int64,
    )

    streamline_index = np.asarray(
        streamline_list,
        dtype=np.int32,
    )

    sub_weight = np.asarray(
        weight_list,
        dtype=np.float64,
    )

    sub_pirnn = np.asarray(
        pirnn_state_list,
        dtype=np.float64,
    )

    sub_sg7a = np.asarray(
        sg7a_state_list,
        dtype=np.float64,
    )

    del (
        cell_index_list,
        streamline_list,
        weight_list,
        pirnn_state_list,
        sg7a_state_list,
    )

    print(
        f"  Reconstructed subsegments: "
        f"{cell_index.size:,}"
    )

    # =========================================================================
    # RECONSTRUCT RAW GRID MEANS
    # =========================================================================

    n_cells = (
        nz
        *
        ny
        *
        nx
    )

    weight_sum = np.bincount(
        cell_index,
        weights=sub_weight,
        minlength=n_cells,
    )

    pirnn_sum = np.bincount(
        cell_index,
        weights=(
            sub_weight
            *
            sub_pirnn
        ),
        minlength=n_cells,
    )

    sg7a_sum = np.bincount(
        cell_index,
        weights=(
            sub_weight
            *
            sub_sg7a
        ),
        minlength=n_cells,
    )

    reconstructed_support_count = np.bincount(
        cell_index,
        minlength=n_cells,
    ).astype(
        np.int64
    )

    reconstructed_pirnn = np.full(
        n_cells,
        np.nan,
        dtype=np.float64,
    )

    reconstructed_sg7a = np.full(
        n_cells,
        np.nan,
        dtype=np.float64,
    )

    supported_flat = (
        weight_sum > 0.0
    )

    reconstructed_pirnn[
        supported_flat
    ] = (
        pirnn_sum[
            supported_flat
        ]
        /
        weight_sum[
            supported_flat
        ]
    )

    reconstructed_sg7a[
        supported_flat
    ] = (
        sg7a_sum[
            supported_flat
        ]
        /
        weight_sum[
            supported_flat
        ]
    )

    reconstructed_pirnn_grid = reconstructed_pirnn.reshape(
        grid_shape
    )

    reconstructed_sg7a_grid = reconstructed_sg7a.reshape(
        grid_shape
    )

    reconstructed_support_grid = reconstructed_support_count.reshape(
        grid_shape
    )

    coverage = (
        support_count_reference > 0
    )

    pirnn_diff = np.abs(
        reconstructed_pirnn_grid[
            coverage
        ]
        -
        raw_grid_pirnn[
            coverage
        ]
    )

    sg7a_diff = np.abs(
        reconstructed_sg7a_grid[
            coverage
        ]
        -
        raw_grid_sg7a[
            coverage
        ]
    )

    pirnn_l1 = float(
        np.mean(
            pirnn_diff
        )
    )

    pirnn_linf = float(
        np.max(
            pirnn_diff
        )
    )

    sg7a_l1 = float(
        np.mean(
            sg7a_diff
        )
    )

    sg7a_linf = float(
        np.max(
            sg7a_diff
        )
    )

    support_exact = bool(
        np.array_equal(
            reconstructed_support_grid,
            support_count_reference,
        )
    )

    print(
        "\nRAW OPERATOR REPRODUCTION"
    )

    print(
        f"  Support count exact      : "
        f"{support_exact}"
    )

    print(
        f"  PI-RNN reconstruction L1 : "
        f"{pirnn_l1:.6e}"
    )

    print(
        f"  PI-RNN reconstruction max: "
        f"{pirnn_linf:.6e}"
    )

    print(
        f"  SG7A reconstruction L1   : "
        f"{sg7a_l1:.6e}"
    )

    print(
        f"  SG7A reconstruction max  : "
        f"{sg7a_linf:.6e}"
    )

    # =========================================================================
    # GROUP SUBSEGMENTS BY CELL
    # =========================================================================

    order = np.argsort(
        cell_index,
        kind="stable",
    )

    sorted_cell = cell_index[
        order
    ]

    sorted_weight = sub_weight[
        order
    ]

    sorted_pirnn = sub_pirnn[
        order
    ]

    sorted_sg7a = sub_sg7a[
        order
    ]

    sorted_streamline = streamline_index[
        order
    ]

    unique_cell, start_index, counts = np.unique(
        sorted_cell,
        return_index=True,
        return_counts=True,
    )

    false_positive_flat = false_positive.reshape(
        -1
    )

    fp_flat_indices = np.flatnonzero(
        false_positive_flat
    )

    fp_set = set(
        fp_flat_indices.tolist()
    )

    cell_rows = []

    mixed_count = 0
    offset_count = 0
    total_fp_with_segments = 0

    for flat_cell, start, count in zip(
        unique_cell,
        start_index,
        counts,
    ):

        if int(
            flat_cell
        ) not in fp_set:

            continue

        stop = (
            start + count
        )

        w = sorted_weight[
            start:stop
        ]

        sp = sorted_pirnn[
            start:stop
        ]

        st = sorted_sg7a[
            start:stop
        ]

        stream_ids = sorted_streamline[
            start:stop
        ]

        wsum = float(
            np.sum(
                w
            )
        )

        pirnn_mean = weighted_mean(
            sp,
            w,
        )

        sg7a_mean = weighted_mean(
            st,
            w,
        )

        pirnn_above_fraction = float(
            np.sum(
                w[
                    sp >= PLUME_THRESHOLD
                ]
            )
            /
            max(
                wsum,
                EPS,
            )
        )

        sg7a_above_fraction = float(
            np.sum(
                w[
                    st >= PLUME_THRESHOLD
                ]
            )
            /
            max(
                wsum,
                EPS,
            )
        )

        pirnn_mixed = bool(
            pirnn_above_fraction
            >=
            MIXED_WEIGHT_LOW
            and
            pirnn_above_fraction
            <=
            MIXED_WEIGHT_HIGH
        )

        sg7a_mixed = bool(
            sg7a_above_fraction
            >=
            MIXED_WEIGHT_LOW
            and
            sg7a_above_fraction
            <=
            MIXED_WEIGHT_HIGH
        )

        mixed_cell = bool(
            pirnn_mixed
            or
            sg7a_mixed
        )

        mean_offset = float(
            pirnn_mean
            -
            sg7a_mean
        )

        systematic_offset = bool(
            mean_offset
            >=
            MATERIAL_MEAN_OFFSET
        )

        if mixed_cell:

            mixed_count += 1

        if systematic_offset:

            offset_count += 1

        total_fp_with_segments += 1

        k = int(
            flat_cell
            //
            (
                ny * nx
            )
        )

        rem = int(
            flat_cell
            %
            (
                ny * nx
            )
        )

        j = int(
            rem
            //
            nx
        )

        i = int(
            rem
            %
            nx
        )

        cell_rows.append(
            {
                "k":
                    k,

                "j":
                    j,

                "i":
                    i,

                "subsegments":
                    int(
                        count
                    ),

                "unique_streamlines":
                    int(
                        np.unique(
                            stream_ids
                        ).size
                    ),

                "weight_sum":
                    wsum,

                "PI_RNN_weighted_mean":
                    pirnn_mean,

                "SG7A_weighted_mean":
                    sg7a_mean,

                "weighted_mean_offset":
                    mean_offset,

                "PI_RNN_weighted_std":
                    weighted_std(
                        sp,
                        w,
                    ),

                "SG7A_weighted_std":
                    weighted_std(
                        st,
                        w,
                    ),

                "PI_RNN_min":
                    float(
                        np.min(
                            sp
                        )
                    ),

                "PI_RNN_P10":
                    weighted_percentile(
                        sp,
                        w,
                        10,
                    ),

                "PI_RNN_P50":
                    weighted_percentile(
                        sp,
                        w,
                        50,
                    ),

                "PI_RNN_P90":
                    weighted_percentile(
                        sp,
                        w,
                        90,
                    ),

                "PI_RNN_max":
                    float(
                        np.max(
                            sp
                        )
                    ),

                "SG7A_min":
                    float(
                        np.min(
                            st
                        )
                    ),

                "SG7A_P10":
                    weighted_percentile(
                        st,
                        w,
                        10,
                    ),

                "SG7A_P50":
                    weighted_percentile(
                        st,
                        w,
                        50,
                    ),

                "SG7A_P90":
                    weighted_percentile(
                        st,
                        w,
                        90,
                    ),

                "SG7A_max":
                    float(
                        np.max(
                            st
                        )
                    ),

                "PI_RNN_weight_above_threshold":
                    pirnn_above_fraction,

                "SG7A_weight_above_threshold":
                    sg7a_above_fraction,

                "mixed_cell":
                    mixed_cell,

                "systematic_mean_offset":
                    systematic_offset,
            }
        )

    mixed_share = float(
        mixed_count
        /
        max(
            total_fp_with_segments,
            1,
        )
    )

    offset_share = float(
        offset_count
        /
        max(
            total_fp_with_segments,
            1,
        )
    )

    # =========================================================================
    # SUPPORT-BIN SUMMARY OF DISPERSION
    # =========================================================================

    support_bins = [
        ("N=1", 1, 1),
        ("N=2-3", 2, 3),
        ("N=4-7", 4, 7),
        ("N=8-15", 8, 15),
        ("N>=16", 16, None),
    ]

    support_rows = []

    for label, low, high in support_bins:

        selected = []

        for row in cell_rows:

            n = row[
                "subsegments"
            ]

            inside = (
                n >= low
                and
                (
                    high is None
                    or
                    n <= high
                )
            )

            if inside:

                selected.append(
                    row
                )

        if not selected:

            continue

        support_rows.append(
            {
                "support_bin":
                    label,

                "false_positive_cells":
                    len(
                        selected
                    ),

                "mean_weighted_mean_offset":
                    float(
                        np.mean(
                            [
                                row[
                                    "weighted_mean_offset"
                                ]
                                for row
                                in selected
                            ]
                        )
                    ),

                "median_weighted_mean_offset":
                    float(
                        np.median(
                            [
                                row[
                                    "weighted_mean_offset"
                                ]
                                for row
                                in selected
                            ]
                        )
                    ),

                "mean_PI_RNN_std":
                    float(
                        np.mean(
                            [
                                row[
                                    "PI_RNN_weighted_std"
                                ]
                                for row
                                in selected
                            ]
                        )
                    ),

                "mean_SG7A_std":
                    float(
                        np.mean(
                            [
                                row[
                                    "SG7A_weighted_std"
                                ]
                                for row
                                in selected
                            ]
                        )
                    ),

                "mean_PI_RNN_above_fraction":
                    float(
                        np.mean(
                            [
                                row[
                                    "PI_RNN_weight_above_threshold"
                                ]
                                for row
                                in selected
                            ]
                        )
                    ),

                "mean_SG7A_above_fraction":
                    float(
                        np.mean(
                            [
                                row[
                                    "SG7A_weight_above_threshold"
                                ]
                                for row
                                in selected
                            ]
                        )
                    ),

                "mixed_cell_fraction":
                    float(
                        np.mean(
                            [
                                row[
                                    "mixed_cell"
                                ]
                                for row
                                in selected
                            ]
                        )
                    ),

                "systematic_offset_fraction":
                    float(
                        np.mean(
                            [
                                row[
                                    "systematic_mean_offset"
                                ]
                                for row
                                in selected
                            ]
                        )
                    ),
            }
        )

    # =========================================================================
    # DIAGNOSIS
    # =========================================================================

    mixed_material = bool(
        mixed_share
        >=
        MIXED_FP_SHARE_GATE
    )

    offset_material = bool(
        offset_share
        >=
        OFFSET_FP_SHARE_GATE
    )

    if (
        mixed_material
        and
        not offset_material
    ):

        diagnosis = (
            "MIXED_SUBCELL_FRONT_AVERAGING"
        )

        recommendation = (
            "Most false-positive cells contain materially mixed above/below-threshold "
            "subsegment populations, while a systematic PI-RNN-to-SG7A mean shift is "
            "not dominant. The remaining binary plume-volume error is primarily a "
            "subcell front representation issue. Preserve q*Delta-tau conservation "
            "and move to a threshold-robust continuous/fractional plume validation."
        )

        next_milestone = (
            "V15-SG7E-R2 — Threshold-Robust Continuous / Fractional "
            "Plume Metric Audit"
        )

    elif (
        offset_material
        and
        not mixed_material
    ):

        diagnosis = (
            "SYSTEMATIC_STREAMLINE_STATE_OFFSET"
        )

        recommendation = (
            "Most false-positive cells show a material PI-RNN upward state shift "
            "relative to SG7A without dominant mixed subcell occupancy. Audit the "
            "remaining streamline-state bias by TOF/front band before changing "
            "the map-back operator."
        )

        next_milestone = (
            "V15-SG7C-R2 — Residual Streamline-State Bias by TOF Audit"
        )

    elif (
        mixed_material
        and
        offset_material
    ):

        diagnosis = (
            "MIXED_AVERAGING_AND_STATE_OFFSET"
        )

        recommendation = (
            "Both mixed subcell front occupancy and a systematic PI-RNN-to-SG7A "
            "mean shift materially contribute to false-positive cells. Separate "
            "the two effects using fractional plume occupancy and TOF-conditioned "
            "streamline-state diagnostics."
        )

        next_milestone = (
            "V15-SG7E-R2 — Fractional Plume / Residual State-Bias Decomposition"
        )

    else:

        diagnosis = (
            "WITHIN_CELL_DISPERSION_NOT_EXPLANATORY"
        )

        recommendation = (
            "Within-cell mixed occupancy and systematic mean offset do not explain "
            "most false-positive cells under the current criteria. Audit the raw "
            "reconstruction state interpolation and segment sampling definitions."
        )

        next_milestone = (
            "V15-SG7D-R2D — Subsegment State-Interpolation Audit"
        )

    # =========================================================================
    # PRINT
    # =========================================================================

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "FALSE-POSITIVE WITHIN-CELL DISPERSION"
    )

    print(
        "=" * 78
    )

    print(
        f"False-positive cells audited : "
        f"{total_fp_with_segments:,}"
    )

    print(
        f"Mixed subcell-front cells    : "
        f"{mixed_count:,} "
        f"({100.0 * mixed_share:.2f}%)"
    )

    print(
        f"Systematic mean-offset cells : "
        f"{offset_count:,} "
        f"({100.0 * offset_share:.2f}%)"
    )

    if cell_rows:

        mean_offset_all = float(
            np.mean(
                [
                    row[
                        "weighted_mean_offset"
                    ]
                    for row
                    in cell_rows
                ]
            )
        )

        median_offset_all = float(
            np.median(
                [
                    row[
                        "weighted_mean_offset"
                    ]
                    for row
                    in cell_rows
                ]
            )
        )

        print(
            f"Mean PI-RNN - SG7A cell mean : "
            f"{mean_offset_all:.6e}"
        )

        print(
            f"Median cell mean offset       : "
            f"{median_offset_all:.6e}"
        )

    print(
        "\nDISPERSION BY SUPPORT"
    )

    for row in support_rows:

        print(
            f"  {row['support_bin']:<7s} | "
            f"FP={row['false_positive_cells']:5d} | "
            f"dMean={row['mean_weighted_mean_offset']:.6e} | "
            f"PIstd={row['mean_PI_RNN_std']:.6e} | "
            f"SG7Astd={row['mean_SG7A_std']:.6e} | "
            f"mixed={100.0 * row['mixed_cell_fraction']:6.2f}% | "
            f"offset={100.0 * row['systematic_offset_fraction']:6.2f}%"
        )

    # =========================================================================
    # SAVE
    # =========================================================================

    save_csv(
        CELL_METRICS_FILE,
        cell_rows,
    )

    save_csv(
        SUPPORT_BIN_FILE,
        support_rows,
    )

    global_rows = [
        {
            "reconstructed_subsegments":
                int(
                    cell_index.size
                ),

            "support_count_exact":
                support_exact,

            "PI_RNN_reconstruction_L1":
                pirnn_l1,

            "PI_RNN_reconstruction_Linf":
                pirnn_linf,

            "SG7A_reconstruction_L1":
                sg7a_l1,

            "SG7A_reconstruction_Linf":
                sg7a_linf,

            "false_positive_cells":
                total_fp_with_segments,

            "mixed_cell_share":
                mixed_share,

            "systematic_offset_share":
                offset_share,
        }
    ]

    save_csv(
        GLOBAL_FILE,
        global_rows,
    )

    np.savez_compressed(
        DATABASE_FILE,

        cell_index=
            cell_index.astype(
                np.int32
            ),

        streamline_index=
            streamline_index.astype(
                np.int32
            ),

        subsegment_weight_q_dtau=
            sub_weight.astype(
                np.float64
            ),

        PI_RNN_subsegment_saturation=
            sub_pirnn.astype(
                np.float32
            ),

        SG7A_subsegment_saturation=
            sub_sg7a.astype(
                np.float32
            ),

        reconstructed_PI_RNN_raw_grid=
            reconstructed_pirnn_grid.astype(
                np.float32
            ),

        reconstructed_SG7A_raw_grid=
            reconstructed_sg7a_grid.astype(
                np.float32
            ),

        reconstructed_support_count=
            reconstructed_support_grid.astype(
                np.int32
            ),

        false_positive_mask=
            false_positive,

        plume_threshold=
            np.asarray(
                [
                    PLUME_THRESHOLD
                ],
                dtype=np.float64,
            ),
    )

    # =========================================================================
    # PLOTS
    # =========================================================================

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    if cell_rows:

        x = np.asarray(
            [
                row[
                    "SG7A_weighted_mean"
                ]
                for row
                in cell_rows
            ]
        )

        y = np.asarray(
            [
                row[
                    "PI_RNN_weighted_mean"
                ]
                for row
                in cell_rows
            ]
        )

        ax.scatter(
            x,
            y,
            s=12,
            alpha=0.5,
        )

        lo = min(
            np.min(
                x
            ),
            np.min(
                y
            ),
        )

        hi = max(
            np.max(
                x
            ),
            np.max(
                y
            ),
        )

        ax.plot(
            [
                lo,
                hi,
            ],
            [
                lo,
                hi,
            ],
            linestyle="--",
        )

        ax.axvline(
            PLUME_THRESHOLD,
            linestyle=":",
        )

        ax.axhline(
            PLUME_THRESHOLD,
            linestyle=":",
        )

    ax.set_xlabel(
        "SG7A weighted cell mean"
    )

    ax.set_ylabel(
        "PI-RNN weighted cell mean"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-R2C\n"
        "False-Positive Cell Mean States"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7DR2C_False_Positive_Cell_Mean_Scatter.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    if cell_rows:

        ax.hist(
            [
                row[
                    "PI_RNN_weight_above_threshold"
                ]
                for row
                in cell_rows
            ],
            bins=40,
            alpha=0.7,
            label="PI-RNN",
        )

        ax.hist(
            [
                row[
                    "SG7A_weight_above_threshold"
                ]
                for row
                in cell_rows
            ],
            bins=40,
            alpha=0.7,
            label="SG7A",
        )

    ax.set_xlabel(
        "q*Delta-tau weight fraction above S=0.21"
    )

    ax.set_ylabel(
        "False-positive cells"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-R2C\n"
        "Within-Cell Threshold Occupancy"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7DR2C_Threshold_Occupancy_Distribution.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    if support_rows:

        labels = [
            row[
                "support_bin"
            ]
            for row
            in support_rows
        ]

        ax.plot(
            labels,
            [
                row[
                    "mean_PI_RNN_std"
                ]
                for row
                in support_rows
            ],
            marker="o",
            label="PI-RNN",
        )

        ax.plot(
            labels,
            [
                row[
                    "mean_SG7A_std"
                ]
                for row
                in support_rows
            ],
            marker="s",
            label="SG7A",
        )

    ax.set_xlabel(
        "Support bin"
    )

    ax.set_ylabel(
        "Mean weighted within-cell standard deviation"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-R2C\n"
        "Within-Cell State Dispersion vs Support"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7DR2C_Dispersion_vs_Support.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    # =========================================================================
    # VALIDATION
    # =========================================================================

    checks = [
        (
            "Incoming SG7D-R2 diagnosis reproduced",
            sg7dr2_summary.get(
                "diagnosis"
            )
            ==
            "HIGH_SUPPORT_AVERAGING_OR_THRESHOLD_EFFECT",
        ),

        (
            "Subsegment database reconstructed",
            cell_index.size
            >
            0,
        ),

        (
            "All reconstructed subsegment weights positive and finite",
            bool(
                np.all(
                    np.isfinite(
                        sub_weight
                    )
                )
                and
                np.all(
                    sub_weight
                    >
                    0.0
                )
            ),
        ),

        (
            "All reconstructed PI-RNN subsegment states finite",
            bool(
                np.all(
                    np.isfinite(
                        sub_pirnn
                    )
                )
            ),
        ),

        (
            "All reconstructed SG7A subsegment states finite",
            bool(
                np.all(
                    np.isfinite(
                        sub_sg7a
                    )
                )
            ),
        ),

        (
            "Support count reproduced exactly",
            support_exact,
        ),

        (
            "PI-RNN raw operator reproduced",
            pirnn_l1
            <=
            RAW_RECONSTRUCTION_L1_TOL
            and
            pirnn_linf
            <=
            RAW_RECONSTRUCTION_LINF_TOL,
        ),

        (
            "SG7A raw operator reproduced",
            sg7a_l1
            <=
            RAW_RECONSTRUCTION_L1_TOL
            and
            sg7a_linf
            <=
            RAW_RECONSTRUCTION_LINF_TOL,
        ),

        (
            "False-positive cells contain reconstructed subsegments",
            total_fp_with_segments
            ==
            int(
                np.sum(
                    false_positive
                )
            ),
        ),

        (
            "Diagnostic classification established",
            diagnosis
            in
            {
                "MIXED_SUBCELL_FRONT_AVERAGING",
                "SYSTEMATIC_STREAMLINE_STATE_OFFSET",
                "MIXED_AVERAGING_AND_STATE_OFFSET",
                "WITHIN_CELL_DISPERSION_NOT_EXPLANATORY",
            },
        ),
    ]

    passed = all(
        flag
        for (
            _,
            flag,
        )
        in checks
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "V15-SG7D-R2C DIAGNOSTIC VALIDATION"
    )

    print(
        "=" * 78
    )

    for description, flag in checks:

        print(
            f"[{'PASS' if flag else 'FAIL'}] "
            f"{description}"
        )

    print(
        "=" * 78
    )

    print(
        "\nDIAGNOSTIC FLAGS"
    )

    print(
        f"  Mixed FP cell share       : "
        f"{100.0 * mixed_share:.2f}%"
    )

    print(
        f"  Systematic-offset share   : "
        f"{100.0 * offset_share:.2f}%"
    )

    print(
        f"  Mixed occupancy material  : "
        f"{mixed_material}"
    )

    print(
        f"  State offset material     : "
        f"{offset_material}"
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
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7D-R2C",

        "description":
            "Within-cell streamline-state dispersion audit",

        "training_performed":
            False,

        "model_changed":
            False,

        "seed_density_changed":
            False,

        "mapback_changed":
            False,

        "projection_changed":
            False,

        "plume_threshold_changed":
            False,

        "primary_time_days":
            PRIMARY_TIME_DAYS,

        "raw_operator_reproduction": {
            "support_count_exact":
                support_exact,

            "PI_RNN_L1":
                pirnn_l1,

            "PI_RNN_Linf":
                pirnn_linf,

            "SG7A_L1":
                sg7a_l1,

            "SG7A_Linf":
                sg7a_linf,
        },

        "100_day_false_positive_dispersion": {
            "cells":
                total_fp_with_segments,

            "mixed_cell_share":
                mixed_share,

            "systematic_mean_offset_share":
                offset_share,
        },

        "diagnosis":
            diagnosis,

        "recommendation":
            recommendation,

        "validation_passed":
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
        f"  {CELL_METRICS_FILE.name}"
    )

    print(
        f"  {SUPPORT_BIN_FILE.name}"
    )

    print(
        f"  {GLOBAL_FILE.name}"
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
        "  V15SG7DR2C_False_Positive_Cell_Mean_Scatter.png"
    )

    print(
        "  V15SG7DR2C_Threshold_Occupancy_Distribution.png"
    )

    print(
        "  V15SG7DR2C_Dispersion_vs_Support.png"
    )

    print(
        "\nSummary:"
    )

    print(
        f"  {SUMMARY_FILE.name}"
    )

    print(
        "\n"
        +
        "=" * 78
    )

    if passed:

        print(
            "V15-SG7D-R2C AUDIT: PASS"
        )

        print()

        print(
            f"Diagnosis:\n  {diagnosis}"
        )

        print()

        print(
            f"Next milestone:\n  {next_milestone}"
        )

    else:

        print(
            "V15-SG7D-R2C AUDIT: INCOMPLETE"
        )

        print()

        print(
            "Do not change training, map-back, projection, seed density, "
            "or plume threshold until the subsegment reconstruction is verified."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":

    main()
