from __future__ import annotations

from pathlib import Path
import argparse
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7E-R1
# Residual Front-to-Plume / Classification Audit
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
# Diagnose why SG7E-R still fails the 100-day plume-volume gate even after
# the front-aware PI-RNN recovered 949 / 992 streamline fronts.
#
# The audit decomposes the full-grid discrepancy into:
#
#   1. raw streamline-to-cell reconstruction,
#   2. conservative projection,
#   3. supported vs unsupported cells,
#   4. near-threshold classification sensitivity,
#   5. displaced-phase inventory,
#   6. original frozen vs front-aware grid-level changes.
#
# The primary plume threshold remains:
#
#       S >= 0.21
#
# which is the same threshold used throughout the SG7E / SG7E-1 diagnostic
# branch. This milestone does NOT change that threshold.
#
# Diagnostic outcomes:
#
#   RAW_MAPBACK_DOMINATED
#   CONSERVATIVE_PROJECTION_DOMINATED
#   BINARY_THRESHOLD_AMPLIFICATION
#   MIXED_RAW_AND_THRESHOLD_EFFECTS
#   MIXED_PROJECTION_AND_THRESHOLD_EFFECTS
#
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

FRONT_AWARE_SG7E_SUMMARY = (
    ROOT
    / "output"
    / "V15_SG7ER"
    / "PAD_Stream_V15SG7ER_Summary.json"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7ER1"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

GLOBAL_TABLE = (
    OUTPUT_DIR
    / "V15SG7ER1_Global_Decomposition.csv"
)

SUPPORT_TABLE = (
    OUTPUT_DIR
    / "V15SG7ER1_Support_Decomposition.csv"
)

THRESHOLD_TABLE = (
    OUTPUT_DIR
    / "V15SG7ER1_Threshold_Band_Audit.csv"
)

CLASSIFICATION_TABLE = (
    OUTPUT_DIR
    / "V15SG7ER1_Classification_Transitions.csv"
)

INVENTORY_TABLE = (
    OUTPUT_DIR
    / "V15SG7ER1_Inventory_Audit.csv"
)

A_B_TABLE = (
    OUTPUT_DIR
    / "V15SG7ER1_Original_vs_FrontAware_Grid.csv"
)

DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7ER1_Residual_Front_to_Plume_Audit.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7ER1_Summary.json"
)


# =============================================================================
# CONTRACT
# =============================================================================

PRIMARY_TIME_DAYS = 100.0
PLUME_THRESHOLD = 0.210
PLUME_VOLUME_GATE = 0.10

# Threshold sensitivity is diagnostic only.
THRESHOLD_BANDS = [
    0.001,
    0.0025,
    0.005,
    0.010,
    0.020,
]

EPS = 1.0e-14

# Independently regenerated SG7A grid states are considered numerically
# equivalent when their maximum absolute difference remains below this level.
# The observed A/B differences were ~2.9e-08 with zero cells above 1e-06.
SG7A_EQUIVALENCE_TOL = 1.0e-6


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


def plume_mask(
    saturation,
    threshold=PLUME_THRESHOLD,
):

    return (
        np.asarray(
            saturation,
            dtype=np.float64,
        )
        >=
        float(
            threshold
        )
    )


def plume_metrics(
    prediction,
    truth,
    threshold=PLUME_THRESHOLD,
):

    prediction = np.asarray(
        prediction,
        dtype=np.float64,
    )

    truth = np.asarray(
        truth,
        dtype=np.float64,
    )

    p = plume_mask(
        prediction,
        threshold,
    )

    t = plume_mask(
        truth,
        threshold,
    )

    p_count = int(
        np.sum(
            p
        )
    )

    t_count = int(
        np.sum(
            t
        )
    )

    intersection = int(
        np.sum(
            p
            &
            t
        )
    )

    union = int(
        np.sum(
            p
            |
            t
        )
    )

    iou = (
        float(
            intersection
            /
            union
        )
        if union > 0
        else 1.0
    )

    volume_error = float(
        abs(
            p_count
            -
            t_count
        )
        /
        max(
            t_count,
            1,
        )
    )

    false_positive = int(
        np.sum(
            p
            &
            ~t
        )
    )

    false_negative = int(
        np.sum(
            ~p
            &
            t
        )
    )

    return {
        "predicted_plume_cells":
            p_count,

        "truth_plume_cells":
            t_count,

        "intersection_cells":
            intersection,

        "union_cells":
            union,

        "IoU":
            iou,

        "volume_relative_error":
            volume_error,

        "false_positive_cells":
            false_positive,

        "false_negative_cells":
            false_negative,

        "mismatch_cells":
            false_positive
            +
            false_negative,
    }


def displaced_inventory(
    saturation,
    initial_saturation,
    cell_pore_volume,
):

    saturation = np.asarray(
        saturation,
        dtype=np.float64,
    )

    displaced = np.maximum(
        saturation
        -
        float(
            initial_saturation
        ),
        0.0,
    )

    return float(
        np.sum(
            displaced
            *
            float(
                cell_pore_volume
            )
        )
    )


def mae_on_mask(
    a,
    b,
    mask,
):

    mask = np.asarray(
        mask,
        dtype=bool,
    )

    if not np.any(
        mask
    ):

        return np.nan

    return float(
        np.mean(
            np.abs(
                np.asarray(
                    a,
                    dtype=np.float64,
                )[
                    mask
                ]
                -
                np.asarray(
                    b,
                    dtype=np.float64,
                )[
                    mask
                ]
            )
        )
    )


def transition_counts(
    raw,
    corrected,
    threshold=PLUME_THRESHOLD,
):

    raw_mask = plume_mask(
        raw,
        threshold,
    )

    corrected_mask = plume_mask(
        corrected,
        threshold,
    )

    return {
        "below_to_above":
            int(
                np.sum(
                    ~raw_mask
                    &
                    corrected_mask
                )
            ),

        "above_to_below":
            int(
                np.sum(
                    raw_mask
                    &
                    ~corrected_mask
                )
            ),

        "unchanged_above":
            int(
                np.sum(
                    raw_mask
                    &
                    corrected_mask
                )
            ),

        "unchanged_below":
            int(
                np.sum(
                    ~raw_mask
                    &
                    ~corrected_mask
                )
            ),

        "changed_total":
            int(
                np.sum(
                    raw_mask
                    !=
                    corrected_mask
                )
            ),
    }


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


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "PAD-Stream V15-SG7E-R1 residual front-to-plume "
            "classification audit."
        )
    )

    parser.add_argument(
        "--workspace",
        type=str,
        default=str(
            DEFAULT_WORKSPACE
        ),
        help=(
            "Accepted 11x11 SG5C workspace containing original SG7D outputs."
        ),
    )

    args = parser.parse_args()

    workspace = Path(
        args.workspace
    ).resolve()

    original_mapback = (
        workspace
        / "output"
        / "V15_SG7D"
        / "SG7D_CONSERVATIVE_GRID_MAPBACK.npz"
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7E-R1"
    )

    print(
        "Residual Front-to-Plume / Classification Audit"
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

    print(
        f"\nPrimary plume threshold   : S >= {PLUME_THRESHOLD:.3f}"
    )

    # =========================================================================
    # PRECONDITIONS
    # =========================================================================

    for path in [
        FRONT_AWARE_MAPBACK,
        FRONT_AWARE_SG7E_SUMMARY,
        original_mapback,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"Missing SG7E-R1 prerequisite:\n{path}"
            )

    sg7er_summary = load_json(
        FRONT_AWARE_SG7E_SUMMARY
    )

    expected_statuses = {
        "FRONT_AWARE_PLUME_VALIDATION_REQUIRES_DIAGNOSIS",
        "PLUME_IMPROVED_BUT_VOLUME_GATE_NOT_YET_REACHED",
    }

    if (
        sg7er_summary.get(
            "status"
        )
        not in
        expected_statuses
    ):

        raise RuntimeError(
            "SG7E-R1 expected a failed-but-diagnostic SG7E-R status.\n"
            f"Observed: {sg7er_summary.get('status')}"
        )

    front_db = np.load(
        FRONT_AWARE_MAPBACK,
        allow_pickle=True,
    )

    old_db = np.load(
        original_mapback,
        allow_pickle=True,
    )

    required_keys = [
        "times_days",
        "grid_shape",
        "dx_m",
        "dy_m",
        "dz_m",
        "porosity",
        "initial_saturation",
        "coverage_mask",
        "PI_RNN_raw_grid_saturation",
        "PI_RNN_corrected_grid_saturation",
        "SG7A_raw_grid_saturation",
        "SG7A_corrected_grid_saturation",
    ]

    for key in required_keys:

        if key not in front_db:

            raise KeyError(
                f"Front-aware SG7D-R database missing key: {key}"
            )

        if key not in old_db:

            raise KeyError(
                f"Original SG7D database missing key: {key}"
            )

    times = np.asarray(
        front_db[
            "times_days"
        ],
        dtype=np.float64,
    )

    old_times = np.asarray(
        old_db[
            "times_days"
        ],
        dtype=np.float64,
    )

    if not np.allclose(
        times,
        old_times,
    ):

        raise RuntimeError(
            "Original and front-aware SG7D times do not match."
        )

    coverage = np.asarray(
        front_db[
            "coverage_mask"
        ],
        dtype=bool,
    )

    old_coverage = np.asarray(
        old_db[
            "coverage_mask"
        ],
        dtype=bool,
    )

    if not np.array_equal(
        coverage,
        old_coverage,
    ):

        raise RuntimeError(
            "Original and front-aware SG7D support masks differ."
        )

    raw_pred = np.asarray(
        front_db[
            "PI_RNN_raw_grid_saturation"
        ],
        dtype=np.float64,
    )

    corrected_pred = np.asarray(
        front_db[
            "PI_RNN_corrected_grid_saturation"
        ],
        dtype=np.float64,
    )

    raw_truth = np.asarray(
        front_db[
            "SG7A_raw_grid_saturation"
        ],
        dtype=np.float64,
    )

    corrected_truth = np.asarray(
        front_db[
            "SG7A_corrected_grid_saturation"
        ],
        dtype=np.float64,
    )

    old_raw_pred = np.asarray(
        old_db[
            "PI_RNN_raw_grid_saturation"
        ],
        dtype=np.float64,
    )

    old_corrected_pred = np.asarray(
        old_db[
            "PI_RNN_corrected_grid_saturation"
        ],
        dtype=np.float64,
    )

    old_raw_truth = np.asarray(
        old_db[
            "SG7A_raw_grid_saturation"
        ],
        dtype=np.float64,
    )

    old_corrected_truth = np.asarray(
        old_db[
            "SG7A_corrected_grid_saturation"
        ],
        dtype=np.float64,
    )

    truth_raw_linf = float(
        np.max(
            np.abs(
                raw_truth
                -
                old_raw_truth
            )
        )
    )

    truth_corrected_linf = float(
        np.max(
            np.abs(
                corrected_truth
                -
                old_corrected_truth
            )
        )
    )

    if (
        truth_raw_linf
        >
        SG7A_EQUIVALENCE_TOL
        or
        truth_corrected_linf
        >
        SG7A_EQUIVALENCE_TOL
    ):

        raise RuntimeError(
            "Original and front-aware branches do not share "
            "numerically equivalent SG7A grid truth.\n"
            f"Raw Linf       : {truth_raw_linf:.6e}\n"
            f"Corrected Linf : {truth_corrected_linf:.6e}\n"
            f"Tolerance      : {SG7A_EQUIVALENCE_TOL:.6e}"
        )

    dx = float(
        np.asarray(
            front_db[
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
            front_db[
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
            front_db[
                "dz_m"
            ]
        ).reshape(
            -1
        )[
            0
        ]
    )

    porosity = float(
        np.asarray(
            front_db[
                "porosity"
            ]
        ).reshape(
            -1
        )[
            0
        ]
    )

    initial_saturation = float(
        np.asarray(
            front_db[
                "initial_saturation"
            ]
        ).reshape(
            -1
        )[
            0
        ]
    )

    cell_pore_volume = (
        dx
        *
        dy
        *
        dz
        *
        porosity
    )

    print(
        "\nA/B GRID CONTRACT"
    )

    print(
        f"  Grid shape               : "
        f"{tuple(np.asarray(front_db['grid_shape']).astype(int).tolist())}"
    )

    print(
        f"  Directly supported cells : "
        f"{np.sum(coverage):,} / {coverage.size:,}"
    )

    print(
        f"  Direct coverage          : "
        f"{100.0 * np.mean(coverage):.3f}%"
    )

    print(
        f"  SG7A raw truth A/B Linf  : "
        f"{truth_raw_linf:.6e}"
    )

    print(
        f"  SG7A corr truth A/B Linf : "
        f"{truth_corrected_linf:.6e}"
    )

    print(
        f"  SG7A equivalence tol     : "
        f"{SG7A_EQUIVALENCE_TOL:.6e}"
    )

    print(
        f"  Cell pore volume         : "
        f"{cell_pore_volume:.6f} m3"
    )

    # =========================================================================
    # GLOBAL DECOMPOSITION
    # =========================================================================

    global_rows = []
    inventory_rows = []
    classification_rows = []
    ab_rows = []

    for it, time_days in enumerate(
        times
    ):

        raw_m = plume_metrics(
            raw_pred[
                it
            ],
            raw_truth[
                it
            ],
        )

        corr_m = plume_metrics(
            corrected_pred[
                it
            ],
            corrected_truth[
                it
            ],
        )

        old_raw_m = plume_metrics(
            old_raw_pred[
                it
            ],
            old_raw_truth[
                it
            ],
        )

        old_corr_m = plume_metrics(
            old_corrected_pred[
                it
            ],
            old_corrected_truth[
                it
            ],
        )

        raw_l1 = float(
            np.mean(
                np.abs(
                    raw_pred[
                        it
                    ]
                    -
                    raw_truth[
                        it
                    ]
                )
            )
        )

        corr_l1 = float(
            np.mean(
                np.abs(
                    corrected_pred[
                        it
                    ]
                    -
                    corrected_truth[
                        it
                    ]
                )
            )
        )

        raw_supported_l1 = mae_on_mask(
            raw_pred[
                it
            ],
            raw_truth[
                it
            ],
            coverage,
        )

        raw_unsupported_l1 = mae_on_mask(
            raw_pred[
                it
            ],
            raw_truth[
                it
            ],
            ~coverage,
        )

        corr_supported_l1 = mae_on_mask(
            corrected_pred[
                it
            ],
            corrected_truth[
                it
            ],
            coverage,
        )

        corr_unsupported_l1 = mae_on_mask(
            corrected_pred[
                it
            ],
            corrected_truth[
                it
            ],
            ~coverage,
        )

        global_rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "raw_L1":
                    raw_l1,

                "corrected_L1":
                    corr_l1,

                "raw_plume_volume_error":
                    raw_m[
                        "volume_relative_error"
                    ],

                "corrected_plume_volume_error":
                    corr_m[
                        "volume_relative_error"
                    ],

                "raw_IoU":
                    raw_m[
                        "IoU"
                    ],

                "corrected_IoU":
                    corr_m[
                        "IoU"
                    ],

                "raw_mismatch_cells":
                    raw_m[
                        "mismatch_cells"
                    ],

                "corrected_mismatch_cells":
                    corr_m[
                        "mismatch_cells"
                    ],

                "projection_volume_error_change":
                    corr_m[
                        "volume_relative_error"
                    ]
                    -
                    raw_m[
                        "volume_relative_error"
                    ],

                "raw_supported_L1":
                    raw_supported_l1,

                "raw_unsupported_L1":
                    raw_unsupported_l1,

                "corrected_supported_L1":
                    corr_supported_l1,

                "corrected_unsupported_L1":
                    corr_unsupported_l1,
            }
        )

        trans_pred = transition_counts(
            raw_pred[
                it
            ],
            corrected_pred[
                it
            ],
        )

        trans_truth = transition_counts(
            raw_truth[
                it
            ],
            corrected_truth[
                it
            ],
        )

        classification_rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "PI_RNN_below_to_above":
                    trans_pred[
                        "below_to_above"
                    ],

                "PI_RNN_above_to_below":
                    trans_pred[
                        "above_to_below"
                    ],

                "PI_RNN_changed_total":
                    trans_pred[
                        "changed_total"
                    ],

                "SG7A_below_to_above":
                    trans_truth[
                        "below_to_above"
                    ],

                "SG7A_above_to_below":
                    trans_truth[
                        "above_to_below"
                    ],

                "SG7A_changed_total":
                    trans_truth[
                        "changed_total"
                    ],
            }
        )

        pred_raw_inventory = displaced_inventory(
            raw_pred[
                it
            ],
            initial_saturation,
            cell_pore_volume,
        )

        truth_raw_inventory = displaced_inventory(
            raw_truth[
                it
            ],
            initial_saturation,
            cell_pore_volume,
        )

        pred_corr_inventory = displaced_inventory(
            corrected_pred[
                it
            ],
            initial_saturation,
            cell_pore_volume,
        )

        truth_corr_inventory = displaced_inventory(
            corrected_truth[
                it
            ],
            initial_saturation,
            cell_pore_volume,
        )

        inventory_rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "PI_RNN_raw_inventory_m3":
                    pred_raw_inventory,

                "SG7A_raw_inventory_m3":
                    truth_raw_inventory,

                "raw_inventory_relative_error":
                    abs(
                        pred_raw_inventory
                        -
                        truth_raw_inventory
                    )
                    /
                    max(
                        truth_raw_inventory,
                        EPS,
                    ),

                "PI_RNN_corrected_inventory_m3":
                    pred_corr_inventory,

                "SG7A_corrected_inventory_m3":
                    truth_corr_inventory,

                "corrected_inventory_relative_error":
                    abs(
                        pred_corr_inventory
                        -
                        truth_corr_inventory
                    )
                    /
                    max(
                        truth_corr_inventory,
                        EPS,
                    ),
            }
        )

        ab_rows.append(
            {
                "time_days":
                    float(
                        time_days
                    ),

                "original_raw_volume_error":
                    old_raw_m[
                        "volume_relative_error"
                    ],

                "front_aware_raw_volume_error":
                    raw_m[
                        "volume_relative_error"
                    ],

                "original_corrected_volume_error":
                    old_corr_m[
                        "volume_relative_error"
                    ],

                "front_aware_corrected_volume_error":
                    corr_m[
                        "volume_relative_error"
                    ],

                "original_raw_IoU":
                    old_raw_m[
                        "IoU"
                    ],

                "front_aware_raw_IoU":
                    raw_m[
                        "IoU"
                    ],

                "original_corrected_IoU":
                    old_corr_m[
                        "IoU"
                    ],

                "front_aware_corrected_IoU":
                    corr_m[
                        "IoU"
                    ],

                "front_aware_minus_original_raw":
                    raw_m[
                        "volume_relative_error"
                    ]
                    -
                    old_raw_m[
                        "volume_relative_error"
                    ],

                "front_aware_minus_original_corrected":
                    corr_m[
                        "volume_relative_error"
                    ]
                    -
                    old_corr_m[
                        "volume_relative_error"
                    ],
            }
        )

    # =========================================================================
    # SUPPORT DECOMPOSITION AT PRIMARY TIME
    # =========================================================================

    i100 = find_time_index(
        times,
        PRIMARY_TIME_DAYS,
    )

    support_rows = []

    for label, mask in [
        (
            "supported",
            coverage,
        ),
        (
            "unsupported",
            ~coverage,
        ),
    ]:

        for stage_name, pred, truth in [
            (
                "raw",
                raw_pred[
                    i100
                ],
                raw_truth[
                    i100
                ],
            ),
            (
                "corrected",
                corrected_pred[
                    i100
                ],
                corrected_truth[
                    i100
                ],
            ),
        ]:

            pred_mask = plume_mask(
                pred
            )

            truth_mask = plume_mask(
                truth
            )

            support_rows.append(
                {
                    "support_class":
                        label,

                    "stage":
                        stage_name,

                    "cells":
                        int(
                            np.sum(
                                mask
                            )
                        ),

                    "state_L1":
                        mae_on_mask(
                            pred,
                            truth,
                            mask,
                        ),

                    "PI_RNN_plume_cells":
                        int(
                            np.sum(
                                pred_mask
                                &
                                mask
                            )
                        ),

                    "SG7A_plume_cells":
                        int(
                            np.sum(
                                truth_mask
                                &
                                mask
                            )
                        ),

                    "false_positive_cells":
                        int(
                            np.sum(
                                pred_mask
                                &
                                ~truth_mask
                                &
                                mask
                            )
                        ),

                    "false_negative_cells":
                        int(
                            np.sum(
                                ~pred_mask
                                &
                                truth_mask
                                &
                                mask
                            )
                        ),
                }
            )

    # =========================================================================
    # THRESHOLD-BAND AUDIT AT 100 DAYS
    # =========================================================================

    threshold_rows = []

    for band in THRESHOLD_BANDS:

        for field_name, field in [
            (
                "SG7A_raw",
                raw_truth[
                    i100
                ],
            ),
            (
                "PI_RNN_raw",
                raw_pred[
                    i100
                ],
            ),
            (
                "SG7A_corrected",
                corrected_truth[
                    i100
                ],
            ),
            (
                "PI_RNN_corrected",
                corrected_pred[
                    i100
                ],
            ),
        ]:

            near = (
                np.abs(
                    field
                    -
                    PLUME_THRESHOLD
                )
                <=
                band
            )

            threshold_rows.append(
                {
                    "band_half_width":
                        float(
                            band
                        ),

                    "field":
                        field_name,

                    "near_threshold_cells":
                        int(
                            np.sum(
                                near
                            )
                        ),

                    "near_threshold_fraction":
                        float(
                            np.mean(
                                near
                            )
                        ),

                    "near_threshold_supported_cells":
                        int(
                            np.sum(
                                near
                                &
                                coverage
                            )
                        ),

                    "near_threshold_unsupported_cells":
                        int(
                            np.sum(
                                near
                                &
                                ~coverage
                            )
                        ),
                }
            )

    # =========================================================================
    # PRIMARY DIAGNOSTIC FLAGS
    # =========================================================================

    primary_global = global_rows[
        i100
    ]

    primary_inventory = inventory_rows[
        i100
    ]

    raw_error = float(
        primary_global[
            "raw_plume_volume_error"
        ]
    )

    corrected_error = float(
        primary_global[
            "corrected_plume_volume_error"
        ]
    )

    projection_delta = float(
        primary_global[
            "projection_volume_error_change"
        ]
    )

    corrected_inventory_error = float(
        primary_inventory[
            "corrected_inventory_relative_error"
        ]
    )

    # Use the ±0.005 band as the main "near-threshold" diagnostic.
    threshold_band = 0.005

    sg7a_corr_band = next(
        row
        for row in threshold_rows
        if (
            np.isclose(
                row[
                    "band_half_width"
                ],
                threshold_band,
            )
            and
            row[
                "field"
            ]
            ==
            "SG7A_corrected"
        )
    )

    pirnn_corr_band = next(
        row
        for row in threshold_rows
        if (
            np.isclose(
                row[
                    "band_half_width"
                ],
                threshold_band,
            )
            and
            row[
                "field"
            ]
            ==
            "PI_RNN_corrected"
        )
    )

    near_threshold_fraction = max(
        float(
            sg7a_corr_band[
                "near_threshold_fraction"
            ]
        ),
        float(
            pirnn_corr_band[
                "near_threshold_fraction"
            ]
        ),
    )

    raw_dominated = bool(
        raw_error
        >
        PLUME_VOLUME_GATE
        and
        abs(
            projection_delta
        )
        <
        0.05
    )

    projection_dominated = bool(
        raw_error
        <=
        PLUME_VOLUME_GATE
        and
        corrected_error
        >
        PLUME_VOLUME_GATE
    )

    threshold_amplified = bool(
        corrected_inventory_error
        <
        0.02
        and
        corrected_error
        >
        PLUME_VOLUME_GATE
        and
        near_threshold_fraction
        >
        0.05
    )

    if (
        raw_dominated
        and
        threshold_amplified
    ):

        diagnosis = (
            "MIXED_RAW_AND_THRESHOLD_EFFECTS"
        )

        recommendation = (
            "The 100-day plume-volume discrepancy is already present before "
            "conservative projection and is strongly amplified by binary "
            "classification near S=0.21 despite small continuous-state and "
            "inventory error. Do not modify the PI-RNN or projection. Audit "
            "the streamline-to-cell support/reconstruction geometry and adopt "
            "continuous plume diagnostics alongside the binary threshold metric."
        )

        next_milestone = (
            "V15-SG7D-R2 — Support-Aware Raw Map-Back "
            "Reconstruction Audit"
        )

    elif projection_dominated:

        diagnosis = (
            "CONSERVATIVE_PROJECTION_DOMINATED"
        )

        recommendation = (
            "Raw grid plume agreement is acceptable, but conservative "
            "projection creates the 100-day volume failure. Audit the bounded "
            "inventory projection spatial redistribution without changing its "
            "contract."
        )

        next_milestone = (
            "V15-SG7D-R3 — Conservative Projection Spatial Redistribution Audit"
        )

    elif threshold_amplified:

        diagnosis = (
            "BINARY_THRESHOLD_AMPLIFICATION"
        )

        recommendation = (
            "Continuous corrected-grid state and inventory remain accurate, "
            "but many cells lie close to S=0.21 so small saturation differences "
            "become a large binary plume-volume discrepancy. Preserve the "
            "physics and quantify threshold-robust continuous plume metrics."
        )

        next_milestone = (
            "V15-SG7E-R2 — Threshold-Robust Continuous Plume Metric Audit"
        )

    elif raw_dominated:

        diagnosis = (
            "RAW_MAPBACK_DOMINATED"
        )

        recommendation = (
            "The volume discrepancy is already present before conservative "
            "projection. Diagnose the support-aware raw streamline-to-cell "
            "reconstruction rather than changing PI-RNN training."
        )

        next_milestone = (
            "V15-SG7D-R2 — Support-Aware Raw Map-Back Reconstruction Audit"
        )

    else:

        diagnosis = (
            "MIXED_PROJECTION_AND_THRESHOLD_EFFECTS"
        )

        recommendation = (
            "The remaining plume discrepancy contains coupled raw, projection, "
            "and threshold effects. Retain the current frozen model and map-back "
            "and perform a support/projection spatial decomposition."
        )

        next_milestone = (
            "V15-SG7E-R2 — Coupled Grid-Classification Mechanism Audit"
        )

    # =========================================================================
    # PRINT AUDIT
    # =========================================================================

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "100-DAY RAW vs CORRECTED DECOMPOSITION"
    )

    print(
        "=" * 78
    )

    print(
        f"Raw plume-volume error       : "
        f"{100.0 * raw_error:.3f}%"
    )

    print(
        f"Corrected plume-volume error : "
        f"{100.0 * corrected_error:.3f}%"
    )

    print(
        f"Projection change            : "
        f"{100.0 * projection_delta:+.3f} percentage points"
    )

    print(
        f"Raw grid L1                  : "
        f"{primary_global['raw_L1']:.6e}"
    )

    print(
        f"Corrected grid L1            : "
        f"{primary_global['corrected_L1']:.6e}"
    )

    print(
        f"Corrected inventory error    : "
        f"{100.0 * corrected_inventory_error:.3f}%"
    )

    print(
        f"Near-threshold fraction ±0.005: "
        f"{100.0 * near_threshold_fraction:.3f}%"
    )

    print(
        "\nSUPPORT DECOMPOSITION @100d"
    )

    for row in support_rows:

        print(
            f"  {row['stage']:<9s} | "
            f"{row['support_class']:<11s} | "
            f"L1={row['state_L1']:.6e} | "
            f"FP={row['false_positive_cells']:,} | "
            f"FN={row['false_negative_cells']:,}"
        )

    print(
        "\nORIGINAL vs FRONT-AWARE @100d"
    )

    primary_ab = ab_rows[
        i100
    ]

    print(
        f"  Original raw volume error     : "
        f"{100.0 * primary_ab['original_raw_volume_error']:.3f}%"
    )

    print(
        f"  Front-aware raw volume error  : "
        f"{100.0 * primary_ab['front_aware_raw_volume_error']:.3f}%"
    )

    print(
        f"  Original corrected error      : "
        f"{100.0 * primary_ab['original_corrected_volume_error']:.3f}%"
    )

    print(
        f"  Front-aware corrected error   : "
        f"{100.0 * primary_ab['front_aware_corrected_volume_error']:.3f}%"
    )

    # =========================================================================
    # SAVE TABLES
    # =========================================================================

    save_csv(
        GLOBAL_TABLE,
        global_rows,
    )

    save_csv(
        SUPPORT_TABLE,
        support_rows,
    )

    save_csv(
        THRESHOLD_TABLE,
        threshold_rows,
    )

    save_csv(
        CLASSIFICATION_TABLE,
        classification_rows,
    )

    save_csv(
        INVENTORY_TABLE,
        inventory_rows,
    )

    save_csv(
        A_B_TABLE,
        ab_rows,
    )

    # =========================================================================
    # DATABASE
    # =========================================================================

    np.savez_compressed(
        DATABASE_FILE,

        times_days=
            times.astype(
                np.float64
            ),

        coverage_mask=
            coverage,

        PI_RNN_raw_grid_saturation=
            raw_pred.astype(
                np.float32
            ),

        PI_RNN_corrected_grid_saturation=
            corrected_pred.astype(
                np.float32
            ),

        SG7A_raw_grid_saturation=
            raw_truth.astype(
                np.float32
            ),

        SG7A_corrected_grid_saturation=
            corrected_truth.astype(
                np.float32
            ),

        original_PI_RNN_raw_grid_saturation=
            old_raw_pred.astype(
                np.float32
            ),

        original_PI_RNN_corrected_grid_saturation=
            old_corrected_pred.astype(
                np.float32
            ),

        plume_threshold=
            np.asarray(
                [
                    PLUME_THRESHOLD
                ],
                dtype=np.float64,
            ),

        cell_pore_volume_m3=
            np.asarray(
                [
                    cell_pore_volume
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

    ax.plot(
        times,
        [
            100.0
            *
            row[
                "raw_plume_volume_error"
            ]
            for row
            in global_rows
        ],
        marker="o",
        label="Raw grid",
    )

    ax.plot(
        times,
        [
            100.0
            *
            row[
                "corrected_plume_volume_error"
            ]
            for row
            in global_rows
        ],
        marker="s",
        label="After conservative projection",
    )

    ax.axhline(
        100.0
        *
        PLUME_VOLUME_GATE,
        linestyle="--",
        label="10% gate",
    )

    ax.set_xlabel(
        "Physical time [days]"
    )

    ax.set_ylabel(
        "Plume-volume relative error [%]"
    )

    ax.set_title(
        "PAD-Stream V15-SG7E-R1\n"
        "Raw vs Corrected Plume-Volume Error"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7ER1_Raw_vs_Corrected_Volume_Error.png",
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

    bands = sorted(
        set(
            row[
                "band_half_width"
            ]
            for row
            in threshold_rows
        )
    )

    for field in [
        "SG7A_corrected",
        "PI_RNN_corrected",
    ]:

        rows = [
            row
            for row
            in threshold_rows
            if row[
                "field"
            ]
            ==
            field
        ]

        ax.plot(
            [
                row[
                    "band_half_width"
                ]
                for row
                in rows
            ],
            [
                100.0
                *
                row[
                    "near_threshold_fraction"
                ]
                for row
                in rows
            ],
            marker="o",
            label=field,
        )

    ax.set_xlabel(
        "Threshold band half-width"
    )

    ax.set_ylabel(
        "Cells near S=0.21 [%]"
    )

    ax.set_title(
        "PAD-Stream V15-SG7E-R1\n"
        "Near-Threshold Cell Population at 100 Days"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7ER1_Threshold_Band_Population.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    # Layer-8 mismatch map.
    layer = min(
        7,
        corrected_pred.shape[
            1
        ]
        -
        1
    )

    mismatch = (
        plume_mask(
            corrected_pred[
                i100
            ]
        )
        !=
        plume_mask(
            corrected_truth[
                i100
            ]
        )
    )

    fig, ax = plt.subplots(
        figsize=(
            8,
            7,
        )
    )

    image = ax.imshow(
        mismatch[
            layer
        ].astype(
            float
        ),
        origin="lower",
        interpolation="nearest",
    )

    ax.set_title(
        "PAD-Stream V15-SG7E-R1\n"
        "100-Day Binary Plume Mismatch — Layer 08"
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
        label="Classification mismatch",
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7ER1_100d_Classification_Mismatch_Layer08.png",
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
            "SG7E-R diagnostic status reproduced",
            sg7er_summary.get(
                "status"
            )
            in
            expected_statuses,
        ),

        (
            "Original and front-aware support masks identical",
            np.array_equal(
                coverage,
                old_coverage,
            ),
        ),

        (
            "Original and front-aware SG7A truth numerically equivalent",
            truth_raw_linf
            <=
            SG7A_EQUIVALENCE_TOL
            and
            truth_corrected_linf
            <=
            SG7A_EQUIVALENCE_TOL,
        ),

        (
            "All front-aware raw grid states finite",
            bool(
                np.all(
                    np.isfinite(
                        raw_pred
                    )
                )
                and
                np.all(
                    np.isfinite(
                        raw_truth
                    )
                )
            ),
        ),

        (
            "All front-aware corrected grid states finite",
            bool(
                np.all(
                    np.isfinite(
                        corrected_pred
                    )
                )
                and
                np.all(
                    np.isfinite(
                        corrected_truth
                    )
                )
            ),
        ),

        (
            "100-day corrected plume failure reproduced",
            corrected_error
            >
            PLUME_VOLUME_GATE,
        ),

        (
            "Inventory audit finite",
            bool(
                np.isfinite(
                    corrected_inventory_error
                )
            ),
        ),

        (
            "Diagnostic classification established",
            diagnosis
            in
            {
                "RAW_MAPBACK_DOMINATED",
                "CONSERVATIVE_PROJECTION_DOMINATED",
                "BINARY_THRESHOLD_AMPLIFICATION",
                "MIXED_RAW_AND_THRESHOLD_EFFECTS",
                "MIXED_PROJECTION_AND_THRESHOLD_EFFECTS",
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
        "V15-SG7E-R1 DIAGNOSTIC VALIDATION"
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
        f"  Raw volume error >10%      : "
        f"{raw_error > PLUME_VOLUME_GATE}"
    )

    print(
        f"  Corrected volume >10%      : "
        f"{corrected_error > PLUME_VOLUME_GATE}"
    )

    print(
        f"  Projection dominated       : "
        f"{projection_dominated}"
    )

    print(
        f"  Raw dominated              : "
        f"{raw_dominated}"
    )

    print(
        f"  Threshold amplified        : "
        f"{threshold_amplified}"
    )

    print(
        f"  Corrected inventory error  : "
        f"{100.0 * corrected_inventory_error:.3f}%"
    )

    print(
        f"  Near-threshold cells ±.005 : "
        f"{100.0 * near_threshold_fraction:.3f}%"
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
            "V15-SG7E-R1",

        "description":
            "Residual front-to-plume / classification audit",

        "training_performed":
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

        "plume_threshold":
            PLUME_THRESHOLD,

        "SG7A_numerical_equivalence_tolerance":
            SG7A_EQUIVALENCE_TOL,

        "SG7A_raw_A_B_Linf":
            truth_raw_linf,

        "SG7A_corrected_A_B_Linf":
            truth_corrected_linf,

        "100_day": {
            "raw_plume_volume_error":
                raw_error,

            "corrected_plume_volume_error":
                corrected_error,

            "projection_volume_error_change":
                projection_delta,

            "raw_grid_L1":
                primary_global[
                    "raw_L1"
                ],

            "corrected_grid_L1":
                primary_global[
                    "corrected_L1"
                ],

            "corrected_inventory_relative_error":
                corrected_inventory_error,

            "near_threshold_fraction_pm_0p005":
                near_threshold_fraction,
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
        f"  {GLOBAL_TABLE.name}"
    )

    print(
        f"  {SUPPORT_TABLE.name}"
    )

    print(
        f"  {THRESHOLD_TABLE.name}"
    )

    print(
        f"  {CLASSIFICATION_TABLE.name}"
    )

    print(
        f"  {INVENTORY_TABLE.name}"
    )

    print(
        f"  {A_B_TABLE.name}"
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
        "  V15SG7ER1_Raw_vs_Corrected_Volume_Error.png"
    )

    print(
        "  V15SG7ER1_Threshold_Band_Population.png"
    )

    print(
        "  V15SG7ER1_100d_Classification_Mismatch_Layer08.png"
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
            "V15-SG7E-R1 AUDIT: PASS"
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
            "V15-SG7E-R1 AUDIT: INCOMPLETE"
        )

        print()

        print(
            "Do not modify training, seed density, projection, or plume "
            "threshold until this audit is internally consistent."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":

    main()
