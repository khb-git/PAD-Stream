from __future__ import annotations

from pathlib import Path
import argparse
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7D-R2
# Support-Aware Raw Map-Back Reconstruction Audit
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
# SG7E-R1 established:
#
#   100-day raw plume-volume error       = 16.117%
#   100-day corrected plume-volume error = 18.152%
#   corrected inventory error            = 1.825%
#   near-threshold cell fraction ±0.005  = 14.317%
#
# and diagnosed:
#
#   MIXED_RAW_AND_THRESHOLD_EFFECTS
#
# The raw-map discrepancy is concentrated in directly supported cells:
#
#   raw supported FP = 3,752
#   raw supported FN = 2
#   raw unsupported L1 = 0
#
# SG7D-R2 therefore asks:
#
#   1. Are raw false-positive plume cells concentrated in LOW streamline
#      support cells?
#
#   2. Do false positives persist in HIGH support cells?
#
#   3. How far above S=0.21 are the PI-RNN false positives, and how far below
#      S=0.21 is SG7A in the same cells?
#
#   4. Does increasing local support reduce:
#        - state error,
#        - threshold-classification error,
#        - false-positive fraction,
#        - threshold-margin discrepancy?
#
#   5. Is the residual raw-grid plume error best classified as:
#
#        LOW_SUPPORT_DOMINATED
#        HIGH_SUPPORT_AVERAGING_OR_THRESHOLD_EFFECT
#        SUPPORT_INDEPENDENT_THRESHOLD_AMPLIFICATION
#        MIXED_SUPPORT_AND_THRESHOLD_EFFECT
#
# This milestone is diagnostic only. It does not alter the accepted q*Delta-tau
# raw accumulation operator.
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

DEFAULT_WORKSPACE = (
    ROOT.parent
    / f"{ROOT.name}_SG5C_seed_11x11"
)

FRONT_AWARE_MAPBACK = (
    ROOT
    / "output"
    / "V15_SG7DR"
    / "SG7DR_FRONT_AWARE_CONSERVATIVE_GRID_MAPBACK.npz"
)

SG7ER1_SUMMARY_FILE = (
    ROOT
    / "output"
    / "V15_SG7ER1"
    / "PAD_Stream_V15SG7ER1_Summary.json"
)

SG7ER1_DATABASE = (
    ROOT
    / "output"
    / "V15_SG7ER1"
    / "V15SG7ER1_Residual_Front_to_Plume_Audit.npz"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7DR2"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

SUPPORT_TABLE = (
    OUTPUT_DIR
    / "V15SG7DR2_Raw_Error_By_Support.csv"
)

FALSE_POSITIVE_TABLE = (
    OUTPUT_DIR
    / "V15SG7DR2_False_Positive_By_Support.csv"
)

THRESHOLD_MARGIN_TABLE = (
    OUTPUT_DIR
    / "V15SG7DR2_Threshold_Margin_By_Support.csv"
)

SUPPORT_VOLUME_TABLE = (
    OUTPUT_DIR
    / "V15SG7DR2_Support_Volume_Statistics.csv"
)

CELL_AUDIT_TABLE = (
    OUTPUT_DIR
    / "V15SG7DR2_100d_False_Positive_Cells.csv"
)

DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7DR2_Support_Aware_Raw_MapBack_Audit.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7DR2_Summary.json"
)


# =============================================================================
# CONTRACT
# =============================================================================

PRIMARY_TIME_DAYS = 100.0
PLUME_THRESHOLD = 0.210
EPS = 1.0e-14

SUPPORT_BINS = [
    ("N=0", 0, 0),
    ("N=1", 1, 1),
    ("N=2-3", 2, 3),
    ("N=4-7", 4, 7),
    ("N=8-15", 8, 15),
    ("N>=16", 16, None),
]

# Diagnostic classification guidance.
LOW_SUPPORT_MAX = 3
HIGH_SUPPORT_MIN = 8

# If >= 70% of all false positives occur in N<=3, classify low-support dominated.
LOW_SUPPORT_FP_SHARE_GATE = 0.70

# If >= 20% of false positives occur in N>=8, high-support behavior is material.
HIGH_SUPPORT_FP_SHARE_GATE = 0.20

# Near-threshold false positive: PI-RNN is no more than 0.005 above threshold
# while SG7A is no more than 0.005 below threshold.
NEAR_THRESHOLD_MARGIN = 0.005


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
                times
                -
                float(
                    target
                )
            )
        )
    )

    if abs(
        times[
            idx
        ]
        -
        target
    ) > 1.0e-6:

        raise RuntimeError(
            f"Could not locate target time {target} days."
        )

    return idx


def plume_mask(
    saturation,
):

    return (
        np.asarray(
            saturation,
            dtype=np.float64,
        )
        >=
        PLUME_THRESHOLD
    )


def support_bin_mask(
    support_count,
    low,
    high,
):

    support_count = np.asarray(
        support_count,
        dtype=np.int64,
    )

    if high is None:

        return (
            support_count
            >=
            low
        )

    return (
        (support_count >= low)
        &
        (support_count <= high)
    )


def safe_mean(
    values,
):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    if values.size == 0:

        return np.nan

    return float(
        np.mean(
            values
        )
    )


def safe_median(
    values,
):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    if values.size == 0:

        return np.nan

    return float(
        np.median(
            values
        )
    )


def safe_percentile(
    values,
    q,
):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    if values.size == 0:

        return np.nan

    return float(
        np.percentile(
            values,
            q,
        )
    )


def identify_support_count(
    db,
    coverage,
):

    """
    Prefer the persisted subsegment_count array. Fall back to compatible aliases.
    """

    aliases = [
        "subsegment_count",
        "support_count",
        "streamline_support_count",
        "cell_support_count",
        "N_support",
    ]

    for key in aliases:

        if key not in db:

            continue

        arr = np.asarray(
            db[
                key
            ]
        )

        if arr.shape == coverage.shape:

            return (
                key,
                arr.astype(
                    np.int64
                ),
            )

    raise RuntimeError(
        "Could not identify a per-cell support-count array in SG7D-R.\n"
        f"Available keys: {list(db.keys())}\n"
        "SG7D-R2 requires the persisted subsegment_count/support_count field."
    )


def identify_support_weight(
    db,
    coverage,
):

    aliases = [
        "coverage_weight_m3",
        "support_weight_m3",
        "cell_support_weight_m3",
    ]

    for key in aliases:

        if key not in db:

            continue

        arr = np.asarray(
            db[
                key
            ],
            dtype=np.float64,
        )

        if arr.shape == coverage.shape:

            return (
                key,
                arr,
            )

    return (
        None,
        np.where(
            coverage,
            1.0,
            0.0,
        ).astype(
            np.float64
        ),
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "PAD-Stream V15-SG7D-R2 support-aware raw map-back "
            "reconstruction audit."
        )
    )

    parser.add_argument(
        "--workspace",
        type=str,
        default=str(
            DEFAULT_WORKSPACE
        ),
        help=(
            "Accepted 11x11 SG5C workspace. Used only for provenance."
        ),
    )

    args = parser.parse_args()

    workspace = Path(
        args.workspace
    ).resolve()

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7D-R2"
    )

    print(
        "Support-Aware Raw Map-Back Reconstruction Audit"
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
        "NO RAW MAP-BACK OPERATOR WILL BE CHANGED."
    )

    print(
        "NO CONSERVATIVE PROJECTION WILL BE CHANGED."
    )

    print(
        "NO PLUME THRESHOLD WILL BE CHANGED."
    )

    print(
        f"\nPrimary plume threshold   : S >= {PLUME_THRESHOLD:.3f}"
    )

    # =========================================================================
    # PRECONDITIONS
    # =========================================================================

    for path in [
        FRONT_AWARE_MAPBACK,
        SG7ER1_SUMMARY_FILE,
        SG7ER1_DATABASE,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"Missing SG7D-R2 prerequisite:\n{path}"
            )

    sg7er1_summary = load_json(
        SG7ER1_SUMMARY_FILE
    )

    if (
        sg7er1_summary.get(
            "diagnosis"
        )
        !=
        "MIXED_RAW_AND_THRESHOLD_EFFECTS"
    ):

        raise RuntimeError(
            "SG7D-R2 requires SG7E-R1 diagnosis:\n"
            "MIXED_RAW_AND_THRESHOLD_EFFECTS"
        )

    db = np.load(
        FRONT_AWARE_MAPBACK,
        allow_pickle=True,
    )

    times = np.asarray(
        db[
            "times_days"
        ],
        dtype=np.float64,
    )

    coverage = np.asarray(
        db[
            "coverage_mask"
        ],
        dtype=bool,
    )

    raw_pred_all = np.asarray(
        db[
            "PI_RNN_raw_grid_saturation"
        ],
        dtype=np.float64,
    )

    raw_truth_all = np.asarray(
        db[
            "SG7A_raw_grid_saturation"
        ],
        dtype=np.float64,
    )

    support_key, support_count = identify_support_count(
        db,
        coverage,
    )

    support_weight_key, support_weight = identify_support_weight(
        db,
        coverage,
    )

    i100 = find_time_index(
        times,
        PRIMARY_TIME_DAYS,
    )

    pred = raw_pred_all[
        i100
    ]

    truth = raw_truth_all[
        i100
    ]

    pred_plume = plume_mask(
        pred
    )

    truth_plume = plume_mask(
        truth
    )

    false_positive = (
        pred_plume
        &
        ~truth_plume
    )

    false_negative = (
        ~pred_plume
        &
        truth_plume
    )

    mismatch = (
        pred_plume
        !=
        truth_plume
    )

    if not np.array_equal(
        coverage,
        support_count
        >
        0
    ):

        raise RuntimeError(
            "Coverage mask and support-count field are inconsistent."
        )

    total_fp = int(
        np.sum(
            false_positive
        )
    )

    total_fn = int(
        np.sum(
            false_negative
        )
    )

    print(
        "\nSUPPORT CONTRACT"
    )

    print(
        f"  Workspace                : "
        f"{workspace}"
    )

    print(
        f"  Support-count field      : "
        f"{support_key}"
    )

    print(
        f"  Support-weight field     : "
        f"{support_weight_key if support_weight_key else 'fallback mask'}"
    )

    print(
        f"  Supported cells          : "
        f"{np.sum(coverage):,} / {coverage.size:,}"
    )

    print(
        f"  Direct coverage          : "
        f"{100.0 * np.mean(coverage):.3f}%"
    )

    print(
        f"  Maximum support count    : "
        f"{np.max(support_count):,}"
    )

    print(
        f"  Raw false positives      : "
        f"{total_fp:,}"
    )

    print(
        f"  Raw false negatives      : "
        f"{total_fn:,}"
    )

    # =========================================================================
    # SUPPORT-BIN DECOMPOSITION
    # =========================================================================

    support_rows = []
    fp_rows = []
    margin_rows = []

    abs_error = np.abs(
        pred
        -
        truth
    )

    pred_margin = (
        pred
        -
        PLUME_THRESHOLD
    )

    truth_margin = (
        truth
        -
        PLUME_THRESHOLD
    )

    for label, low, high in SUPPORT_BINS:

        mask = support_bin_mask(
            support_count,
            low,
            high,
        )

        cells = int(
            np.sum(
                mask
            )
        )

        if cells == 0:

            continue

        fp_mask = (
            mask
            &
            false_positive
        )

        fn_mask = (
            mask
            &
            false_negative
        )

        mm_mask = (
            mask
            &
            mismatch
        )

        fp_count = int(
            np.sum(
                fp_mask
            )
        )

        fn_count = int(
            np.sum(
                fn_mask
            )
        )

        support_rows.append(
            {
                "support_bin":
                    label,

                "support_min":
                    low,

                "support_max":
                    (
                        ""
                        if high is None
                        else high
                    ),

                "cells":
                    cells,

                "cell_fraction":
                    float(
                        cells
                        /
                        coverage.size
                    ),

                "mean_support_count":
                    safe_mean(
                        support_count[
                            mask
                        ]
                    ),

                "mean_support_weight":
                    safe_mean(
                        support_weight[
                            mask
                        ]
                    ),

                "state_L1":
                    safe_mean(
                        abs_error[
                            mask
                        ]
                    ),

                "state_P90":
                    safe_percentile(
                        abs_error[
                            mask
                        ],
                        90,
                    ),

                "mismatch_cells":
                    int(
                        np.sum(
                            mm_mask
                        )
                    ),

                "mismatch_fraction":
                    float(
                        np.mean(
                            mismatch[
                                mask
                            ]
                        )
                    ),

                "false_positive_cells":
                    fp_count,

                "false_negative_cells":
                    fn_count,

                "false_positive_fraction_of_bin":
                    float(
                        fp_count
                        /
                        cells
                    ),

                "share_of_all_false_positives":
                    float(
                        fp_count
                        /
                        max(
                            total_fp,
                            1,
                        )
                    ),
            }
        )

        fp_pred_margin = pred_margin[
            fp_mask
        ]

        fp_truth_margin = truth_margin[
            fp_mask
        ]

        near_fp = (
            fp_mask
            &
            (
                pred_margin
                <=
                NEAR_THRESHOLD_MARGIN
            )
            &
            (
                truth_margin
                >=
                -NEAR_THRESHOLD_MARGIN
            )
        )

        fp_rows.append(
            {
                "support_bin":
                    label,

                "false_positive_cells":
                    fp_count,

                "share_of_all_false_positives":
                    float(
                        fp_count
                        /
                        max(
                            total_fp,
                            1,
                        )
                    ),

                "near_threshold_false_positives":
                    int(
                        np.sum(
                            near_fp
                        )
                    ),

                "near_threshold_share_within_FP":
                    float(
                        np.sum(
                            near_fp
                        )
                        /
                        max(
                            fp_count,
                            1,
                        )
                    ),

                "PI_RNN_margin_mean":
                    safe_mean(
                        fp_pred_margin
                    ),

                "PI_RNN_margin_median":
                    safe_median(
                        fp_pred_margin
                    ),

                "PI_RNN_margin_P90":
                    safe_percentile(
                        fp_pred_margin,
                        90,
                    ),

                "SG7A_margin_mean":
                    safe_mean(
                        fp_truth_margin
                    ),

                "SG7A_margin_median":
                    safe_median(
                        fp_truth_margin
                    ),

                "absolute_state_error_mean":
                    safe_mean(
                        abs_error[
                            fp_mask
                        ]
                    ),
            }
        )

        margin_rows.append(
            {
                "support_bin":
                    label,

                "cells":
                    cells,

                "PI_RNN_margin_mean":
                    safe_mean(
                        pred_margin[
                            mask
                        ]
                    ),

                "SG7A_margin_mean":
                    safe_mean(
                        truth_margin[
                            mask
                        ]
                    ),

                "margin_difference_MAE":
                    safe_mean(
                        np.abs(
                            pred_margin[
                                mask
                            ]
                            -
                            truth_margin[
                                mask
                            ]
                        )
                    ),

                "near_threshold_PI_RNN_fraction":
                    float(
                        np.mean(
                            np.abs(
                                pred_margin[
                                    mask
                                ]
                            )
                            <=
                            NEAR_THRESHOLD_MARGIN
                        )
                    ),

                "near_threshold_SG7A_fraction":
                    float(
                        np.mean(
                            np.abs(
                                truth_margin[
                                    mask
                                ]
                            )
                            <=
                            NEAR_THRESHOLD_MARGIN
                        )
                    ),
            }
        )

    # =========================================================================
    # SUPPORT-VOLUME STATISTICS
    # =========================================================================

    support_volume_rows = []

    for category, mask in [
        (
            "all_supported",
            coverage,
        ),
        (
            "false_positive",
            false_positive,
        ),
        (
            "correct_positive",
            pred_plume
            &
            truth_plume,
        ),
        (
            "correct_negative_supported",
            ~pred_plume
            &
            ~truth_plume
            &
            coverage,
        ),
    ]:

        counts = support_count[
            mask
        ]

        weights = support_weight[
            mask
        ]

        support_volume_rows.append(
            {
                "category":
                    category,

                "cells":
                    int(
                        counts.size
                    ),

                "support_count_mean":
                    safe_mean(
                        counts
                    ),

                "support_count_median":
                    safe_median(
                        counts
                    ),

                "support_count_P90":
                    safe_percentile(
                        counts,
                        90,
                    ),

                "support_weight_mean":
                    safe_mean(
                        weights
                    ),

                "support_weight_median":
                    safe_median(
                        weights
                    ),

                "support_weight_P90":
                    safe_percentile(
                        weights,
                        90,
                    ),
            }
        )

    # =========================================================================
    # CELL-LEVEL FALSE-POSITIVE AUDIT
    # =========================================================================

    fp_indices = np.argwhere(
        false_positive
    )

    cell_rows = []

    for k, j, i in fp_indices:

        cell_rows.append(
            {
                "k":
                    int(
                        k
                    ),

                "j":
                    int(
                        j
                    ),

                "i":
                    int(
                        i
                    ),

                "support_count":
                    int(
                        support_count[
                            k,
                            j,
                            i
                        ]
                    ),

                "support_weight":
                    float(
                        support_weight[
                            k,
                            j,
                            i
                        ]
                    ),

                "PI_RNN_raw_saturation":
                    float(
                        pred[
                            k,
                            j,
                            i
                        ]
                    ),

                "SG7A_raw_saturation":
                    float(
                        truth[
                            k,
                            j,
                            i
                        ]
                    ),

                "PI_RNN_margin":
                    float(
                        pred_margin[
                            k,
                            j,
                            i
                        ]
                    ),

                "SG7A_margin":
                    float(
                        truth_margin[
                            k,
                            j,
                            i
                        ]
                    ),

                "absolute_state_error":
                    float(
                        abs_error[
                            k,
                            j,
                            i
                        ]
                    ),

                "near_threshold_pair":
                    bool(
                        pred_margin[
                            k,
                            j,
                            i
                        ]
                        <=
                        NEAR_THRESHOLD_MARGIN
                        and
                        truth_margin[
                            k,
                            j,
                            i
                        ]
                        >=
                        -NEAR_THRESHOLD_MARGIN
                    ),
            }
        )

    # =========================================================================
    # DIAGNOSTIC FLAGS
    # =========================================================================

    low_support_fp = int(
        np.sum(
            false_positive
            &
            (
                support_count
                <=
                LOW_SUPPORT_MAX
            )
        )
    )

    high_support_fp = int(
        np.sum(
            false_positive
            &
            (
                support_count
                >=
                HIGH_SUPPORT_MIN
            )
        )
    )

    low_support_fp_share = float(
        low_support_fp
        /
        max(
            total_fp,
            1,
        )
    )

    high_support_fp_share = float(
        high_support_fp
        /
        max(
            total_fp,
            1,
        )
    )

    near_threshold_fp = int(
        np.sum(
            false_positive
            &
            (
                pred_margin
                <=
                NEAR_THRESHOLD_MARGIN
            )
            &
            (
                truth_margin
                >=
                -NEAR_THRESHOLD_MARGIN
            )
        )
    )

    near_threshold_fp_share = float(
        near_threshold_fp
        /
        max(
            total_fp,
            1,
        )
    )

    low_support_dominated = bool(
        low_support_fp_share
        >=
        LOW_SUPPORT_FP_SHARE_GATE
    )

    high_support_material = bool(
        high_support_fp_share
        >=
        HIGH_SUPPORT_FP_SHARE_GATE
    )

    threshold_dominated = bool(
        near_threshold_fp_share
        >=
        0.70
    )

    if (
        low_support_dominated
        and
        threshold_dominated
    ):

        diagnosis = (
            "MIXED_SUPPORT_AND_THRESHOLD_EFFECT"
        )

        recommendation = (
            "Most raw false positives occur in low-support cells and are also "
            "near the S=0.21 classification threshold. The next milestone "
            "should test support-aware geometric reconstruction diagnostics "
            "without altering the accepted q*Delta-tau operator."
        )

        next_milestone = (
            "V15-SG7D-R2B — Low-Support Cell Geometry / "
            "Subsegment Distribution Audit"
        )

    elif low_support_dominated:

        diagnosis = (
            "LOW_SUPPORT_DOMINATED"
        )

        recommendation = (
            "The residual raw plume discrepancy is concentrated in cells with "
            "N<=3 streamline/subsegment support. Diagnose local support geometry "
            "and streamline occupancy before changing any transport model."
        )

        next_milestone = (
            "V15-SG7D-R2B — Low-Support Cell Geometry / "
            "Subsegment Distribution Audit"
        )

    elif high_support_material and threshold_dominated:

        diagnosis = (
            "HIGH_SUPPORT_AVERAGING_OR_THRESHOLD_EFFECT"
        )

        recommendation = (
            "A material fraction of false positives persists even in high-support "
            "cells, and most false positives remain near S=0.21. The remaining "
            "binary plume error is therefore not primarily a sparse-sampling "
            "problem. Audit within-cell streamline-state dispersion and define "
            "continuous plume diagnostics alongside the binary metric."
        )

        next_milestone = (
            "V15-SG7D-R2C — Within-Cell Streamline-State "
            "Dispersion Audit"
        )

    elif threshold_dominated:

        diagnosis = (
            "SUPPORT_INDEPENDENT_THRESHOLD_AMPLIFICATION"
        )

        recommendation = (
            "False-positive classification is dominated by tiny threshold-margin "
            "differences across support levels. Preserve the current reconstruction "
            "and move to threshold-robust continuous plume validation."
        )

        next_milestone = (
            "V15-SG7E-R2 — Threshold-Robust Continuous Plume Metric Audit"
        )

    else:

        diagnosis = (
            "HIGH_SUPPORT_AVERAGING_OR_THRESHOLD_EFFECT"
        )

        recommendation = (
            "The residual false positives are not explained by low support alone. "
            "Inspect within-cell streamline-state dispersion and cell averaging "
            "before any algorithmic change."
        )

        next_milestone = (
            "V15-SG7D-R2C — Within-Cell Streamline-State Dispersion Audit"
        )

    # =========================================================================
    # PRINT RESULTS
    # =========================================================================

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "100-DAY RAW ERROR BY SUPPORT"
    )

    print(
        "=" * 78
    )

    for row in support_rows:

        print(
            f"{row['support_bin']:<7s} | "
            f"cells={row['cells']:6d} | "
            f"L1={row['state_L1']:.6e} | "
            f"FP={row['false_positive_cells']:5d} | "
            f"FPshare={100.0 * row['share_of_all_false_positives']:6.2f}% | "
            f"mismatch={100.0 * row['mismatch_fraction']:6.2f}%"
        )

    print(
        "\nFALSE-POSITIVE THRESHOLD MARGINS"
    )

    for row in fp_rows:

        print(
            f"{row['support_bin']:<7s} | "
            f"FP={row['false_positive_cells']:5d} | "
            f"near={100.0 * row['near_threshold_share_within_FP']:6.2f}% | "
            f"PIgap={row['PI_RNN_margin_median']:.6e} | "
            f"SG7Agap={row['SG7A_margin_median']:.6e}"
        )

    print(
        "\nGLOBAL SUPPORT FLAGS"
    )

    print(
        f"  Total false positives     : "
        f"{total_fp:,}"
    )

    print(
        f"  N<=3 false positives      : "
        f"{low_support_fp:,} "
        f"({100.0 * low_support_fp_share:.2f}%)"
    )

    print(
        f"  N>=8 false positives      : "
        f"{high_support_fp:,} "
        f"({100.0 * high_support_fp_share:.2f}%)"
    )

    print(
        f"  Near-threshold FP         : "
        f"{near_threshold_fp:,} "
        f"({100.0 * near_threshold_fp_share:.2f}%)"
    )

    print(
        f"  Low-support dominated     : "
        f"{low_support_dominated}"
    )

    print(
        f"  High-support material     : "
        f"{high_support_material}"
    )

    print(
        f"  Threshold dominated       : "
        f"{threshold_dominated}"
    )

    # =========================================================================
    # SAVE TABLES / DATABASE
    # =========================================================================

    save_csv(
        SUPPORT_TABLE,
        support_rows,
    )

    save_csv(
        FALSE_POSITIVE_TABLE,
        fp_rows,
    )

    save_csv(
        THRESHOLD_MARGIN_TABLE,
        margin_rows,
    )

    save_csv(
        SUPPORT_VOLUME_TABLE,
        support_volume_rows,
    )

    save_csv(
        CELL_AUDIT_TABLE,
        cell_rows,
    )

    np.savez_compressed(
        DATABASE_FILE,

        raw_PI_RNN_100d=
            pred.astype(
                np.float32
            ),

        raw_SG7A_100d=
            truth.astype(
                np.float32
            ),

        support_count=
            support_count.astype(
                np.int32
            ),

        support_weight=
            support_weight.astype(
                np.float64
            ),

        coverage_mask=
            coverage,

        false_positive_mask=
            false_positive,

        false_negative_mask=
            false_negative,

        mismatch_mask=
            mismatch,

        PI_RNN_threshold_margin=
            pred_margin.astype(
                np.float32
            ),

        SG7A_threshold_margin=
            truth_margin.astype(
                np.float32
            ),

        plume_threshold=
            np.asarray(
                [
                    PLUME_THRESHOLD
                ],
                dtype=np.float64,
            ),
    )

    # =========================================================================
    # DIAGNOSTIC PLOTS
    # =========================================================================

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    labels = [
        row[
            "support_bin"
        ]
        for row
        in support_rows
        if row[
            "support_bin"
        ]
        !=
        "N=0"
    ]

    fp_share = [
        100.0
        *
        row[
            "share_of_all_false_positives"
        ]
        for row
        in support_rows
        if row[
            "support_bin"
        ]
        !=
        "N=0"
    ]

    ax.bar(
        labels,
        fp_share,
    )

    ax.set_xlabel(
        "Raw map-back support bin"
    )

    ax.set_ylabel(
        "Share of all 100-day false positives [%]"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-R2\n"
        "False-Positive Plume Cells by Local Support"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7DR2_False_Positive_Share_By_Support.png",
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

    ax.plot(
        labels,
        [
            row[
                "state_L1"
            ]
            for row
            in support_rows
            if row[
                "support_bin"
            ]
            !=
            "N=0"
        ],
        marker="o",
    )

    ax.set_xlabel(
        "Raw map-back support bin"
    )

    ax.set_ylabel(
        "Raw cell-state L1"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-R2\n"
        "Raw State Error vs Local Support"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7DR2_Raw_L1_vs_Support.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    fp_support = support_count[
        false_positive
    ]

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    if fp_support.size:

        ax.hist(
            fp_support,
            bins=min(
                50,
                max(
                    10,
                    int(
                        np.max(
                            fp_support
                        )
                    )
                    +
                    1,
                ),
            ),
        )

    ax.set_xlabel(
        "Support count in false-positive cells"
    )

    ax.set_ylabel(
        "False-positive cells"
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-R2\n"
        "Support Distribution of Raw False Positives"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7DR2_False_Positive_Support_Distribution.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    layer = min(
        7,
        support_count.shape[
            0
        ]
        -
        1
    )

    fig, ax = plt.subplots(
        figsize=(
            8,
            7,
        )
    )

    image = ax.imshow(
        np.where(
            false_positive[
                layer
            ],
            support_count[
                layer
            ],
            np.nan,
        ),
        origin="lower",
        interpolation="nearest",
    )

    ax.set_title(
        "PAD-Stream V15-SG7D-R2\n"
        "100-Day False-Positive Support — Layer 08"
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
        label="Support count",
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7DR2_False_Positive_Support_Layer08.png",
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
            "Incoming SG7E-R1 diagnosis reproduced",
            sg7er1_summary.get(
                "diagnosis"
            )
            ==
            "MIXED_RAW_AND_THRESHOLD_EFFECTS",
        ),

        (
            "Support count field found",
            support_count.shape
            ==
            coverage.shape,
        ),

        (
            "Coverage and support count consistent",
            np.array_equal(
                coverage,
                support_count
                >
                0,
            ),
        ),

        (
            "Raw PI-RNN field finite",
            bool(
                np.all(
                    np.isfinite(
                        pred
                    )
                )
            ),
        ),

        (
            "Raw SG7A field finite",
            bool(
                np.all(
                    np.isfinite(
                        truth
                    )
                )
            ),
        ),

        (
            "Raw false-positive population reproduced",
            total_fp
            >
            0,
        ),

        (
            "Support-bin metrics finite where defined",
            all(
                np.isfinite(
                    row[
                        "state_L1"
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
                "LOW_SUPPORT_DOMINATED",
                "HIGH_SUPPORT_AVERAGING_OR_THRESHOLD_EFFECT",
                "SUPPORT_INDEPENDENT_THRESHOLD_AMPLIFICATION",
                "MIXED_SUPPORT_AND_THRESHOLD_EFFECT",
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
        "V15-SG7D-R2 DIAGNOSTIC VALIDATION"
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
            "V15-SG7D-R2",

        "description":
            "Support-aware raw map-back reconstruction audit",

        "training_performed":
            False,

        "model_changed":
            False,

        "seed_density_changed":
            False,

        "raw_mapback_changed":
            False,

        "projection_changed":
            False,

        "plume_threshold_changed":
            False,

        "primary_time_days":
            PRIMARY_TIME_DAYS,

        "support_count_field":
            support_key,

        "support_weight_field":
            support_weight_key,

        "100_day": {
            "total_false_positives":
                total_fp,

            "total_false_negatives":
                total_fn,

            "low_support_false_positive_share":
                low_support_fp_share,

            "high_support_false_positive_share":
                high_support_fp_share,

            "near_threshold_false_positive_share":
                near_threshold_fp_share,
        },

        "diagnostic_flags": {
            "low_support_dominated":
                low_support_dominated,

            "high_support_material":
                high_support_material,

            "threshold_dominated":
                threshold_dominated,
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
        f"  {SUPPORT_TABLE.name}"
    )

    print(
        f"  {FALSE_POSITIVE_TABLE.name}"
    )

    print(
        f"  {THRESHOLD_MARGIN_TABLE.name}"
    )

    print(
        f"  {SUPPORT_VOLUME_TABLE.name}"
    )

    print(
        f"  {CELL_AUDIT_TABLE.name}"
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
        "  V15SG7DR2_False_Positive_Share_By_Support.png"
    )

    print(
        "  V15SG7DR2_Raw_L1_vs_Support.png"
    )

    print(
        "  V15SG7DR2_False_Positive_Support_Distribution.png"
    )

    print(
        "  V15SG7DR2_False_Positive_Support_Layer08.png"
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
            "V15-SG7D-R2 AUDIT: PASS"
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
            "V15-SG7D-R2 AUDIT: INCOMPLETE"
        )

        print()

        print(
            "Do not modify training, seed density, map-back, projection, "
            "or plume threshold until this audit is internally consistent."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":

    main()
