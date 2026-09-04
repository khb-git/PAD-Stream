from __future__ import annotations

from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R2
# Residual Streamline-State Bias by TOF / Front-Band Audit
#
# NO TRAINING.
# NO MODEL CHANGE.
# NO SEED-DENSITY CHANGE.
# NO STREAMLINE-GEOMETRY CHANGE.
# NO MAP-BACK CHANGE.
# NO PLUME-THRESHOLD CHANGE.
#
# PURPOSE
# -------
# SG7D-R2C established that the remaining 100-day raw-grid false positives are
# driven primarily by a systematic positive PI-RNN state offset relative to SG7A:
#
#   systematic-offset FP cells = 99.89%
#   mean PI-RNN - SG7A offset  ≈ 1.07e-02
#
# SG7C-R2 returns to streamline space and localizes that residual state bias by:
#
#   1. terminal time of flight (TOF),
#   2. streamline dimensionless time tD = t / tau_end,
#   3. streamline coordinate xi,
#   4. SG7A saturation/front band,
#   5. producer destination,
#   6. local positive-bias occupancy.
#
# The milestone is diagnostic only. It does not retrain or modify the frozen
# front-aware PI-RNN.
#
# Diagnostic outcomes:
#
#   INITIAL_STATE_TAIL_BIAS
#   TOF_CONDITIONED_BIAS
#   FRONT_BAND_BIAS
#   BROAD_STREAMLINE_STATE_BIAS
#   RESIDUAL_BIAS_NOT_LOCALIZED
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

SG7DR2C_SUMMARY = (
    ROOT
    / "output"
    / "V15_SG7DR2C"
    / "PAD_Stream_V15SG7DR2C_Summary.json"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7CR2"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

TOF_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR2_Bias_By_Terminal_TOF.csv"
)

TD_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR2_Bias_By_tD.csv"
)

XI_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR2_Bias_By_Xi.csv"
)

STATE_BAND_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR2_Bias_By_SG7A_State_Band.csv"
)

PRODUCER_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR2_Bias_By_Producer.csv"
)

GLOBAL_TABLE = (
    OUTPUT_DIR
    / "V15SG7CR2_Global_Bias_Summary.csv"
)

DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7CR2_Residual_Streamline_Bias_Audit.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7CR2_Summary.json"
)


# =============================================================================
# CONTRACT
# =============================================================================

PRIMARY_TIME_DAYS = 100.0
PLUME_THRESHOLD = 0.210
INITIAL_STATE = 0.200
FRONT_HIGH = 0.300

# Bias considered materially positive at a node.
MATERIAL_POSITIVE_BIAS = 2.5e-3

# Tail region: SG7A essentially at initial saturation.
INITIAL_TAIL_MAX = 0.205

# Front band used in prior diagnostics.
FRONT_BAND_LOW = PLUME_THRESHOLD
FRONT_BAND_HIGH = FRONT_HIGH

# Classification guidance.
DOMINANT_NODE_SHARE = 0.50
BROAD_SHARE_GATE = 0.35
EPS = 1.0e-14


TOF_BINS_DAYS = [
    ("<=250d", None, 250.0),
    ("250-500d", 250.0, 500.0),
    ("500-1000d", 500.0, 1000.0),
    ("1000-2000d", 1000.0, 2000.0),
    (">2000d", 2000.0, None),
]

TD_BINS = [
    ("tD<0.05", None, 0.05),
    ("0.05-0.10", 0.05, 0.10),
    ("0.10-0.25", 0.10, 0.25),
    ("0.25-0.50", 0.25, 0.50),
    ("0.50-1.00", 0.50, 1.00),
    ("tD>=1.00", 1.00, None),
]

XI_BINS = [
    ("0.0-0.2", 0.0, 0.2),
    ("0.2-0.4", 0.2, 0.4),
    ("0.4-0.6", 0.4, 0.6),
    ("0.6-0.8", 0.6, 0.8),
    ("0.8-1.0", 0.8, 1.0000001),
]

STATE_BANDS = [
    ("initial_tail", None, INITIAL_TAIL_MAX),
    ("threshold_approach", INITIAL_TAIL_MAX, PLUME_THRESHOLD),
    ("front_band", PLUME_THRESHOLD, FRONT_BAND_HIGH),
    ("swept_high", FRONT_BAND_HIGH, None),
]


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
        return json.load(handle)


def save_csv(path: Path, rows: list[dict]):

    if not rows:
        return

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)


def find_time_index(times, target):

    times = np.asarray(
        times,
        dtype=np.float64,
    )

    idx = int(
        np.argmin(
            np.abs(times - float(target))
        )
    )

    if abs(times[idx] - target) > 1.0e-6:
        raise RuntimeError(
            f"Could not locate {target} days."
        )

    return idx


def band_mask(values, low, high):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    if low is None and high is None:
        return np.ones_like(
            values,
            dtype=bool,
        )

    if low is None:
        return values < high

    if high is None:
        return values >= low

    return (
        (values >= low)
        &
        (values < high)
    )


def summarize_bias(
    label,
    error,
    mask,
):

    mask = np.asarray(
        mask,
        dtype=bool,
    )

    values = np.asarray(
        error,
        dtype=np.float64,
    )[mask]

    if values.size == 0:

        return {
            "band":
                label,
            "samples":
                0,
            "mean_bias":
                np.nan,
            "median_bias":
                np.nan,
            "L1":
                np.nan,
            "P90_abs":
                np.nan,
            "positive_bias_fraction":
                np.nan,
            "material_positive_fraction":
                np.nan,
            "share_of_all_material_positive_nodes":
                np.nan,
        }

    return {
        "band":
            label,

        "samples":
            int(values.size),

        "mean_bias":
            float(
                np.mean(values)
            ),

        "median_bias":
            float(
                np.median(values)
            ),

        "L1":
            float(
                np.mean(
                    np.abs(values)
                )
            ),

        "P90_abs":
            float(
                np.percentile(
                    np.abs(values),
                    90,
                )
            ),

        "positive_bias_fraction":
            float(
                np.mean(
                    values > 0.0
                )
            ),

        "material_positive_fraction":
            float(
                np.mean(
                    values
                    >=
                    MATERIAL_POSITIVE_BIAS
                )
            ),

        "share_of_all_material_positive_nodes":
            np.nan,
    }


def safe_fraction(num, den):
    return float(
        num
        /
        max(
            den,
            1,
        )
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7C-R2"
    )

    print(
        "Residual Streamline-State Bias by TOF / Front-Band Audit"
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
        "NO STREAMLINE GEOMETRY WILL BE CHANGED."
    )

    print(
        "NO MAP-BACK OPERATOR WILL BE CHANGED."
    )

    print(
        "NO PLUME THRESHOLD WILL BE CHANGED."
    )

    # =========================================================================
    # PRECONDITIONS
    # =========================================================================

    for path in [
        SG7CR_DATABASE,
        SG7DR2C_SUMMARY,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"Missing SG7C-R2 prerequisite:\n{path}"
            )

    sg7dr2c_summary = load_json(
        SG7DR2C_SUMMARY
    )

    if (
        sg7dr2c_summary.get(
            "diagnosis"
        )
        !=
        "SYSTEMATIC_STREAMLINE_STATE_OFFSET"
    ):

        raise RuntimeError(
            "SG7C-R2 requires SG7D-R2C diagnosis:\n"
            "SYSTEMATIC_STREAMLINE_STATE_OFFSET"
        )

    db = np.load(
        SG7CR_DATABASE,
        allow_pickle=True,
    )

    required_keys = [
        "times_days",
        "xi",
        "tau_end_s",
        "weights_m3_s",
        "producer",
        "PI_RNN_saturation",
        "SG7A_saturation",
    ]

    for key in required_keys:

        if key not in db:

            raise KeyError(
                f"SG7C-R database missing key: {key}"
            )

    times = np.asarray(
        db[
            "times_days"
        ],
        dtype=np.float64,
    )

    i100 = find_time_index(
        times,
        PRIMARY_TIME_DAYS,
    )

    xi = np.asarray(
        db[
            "xi"
        ],
        dtype=np.float64,
    )

    tau_end_days = (
        np.asarray(
            db[
                "tau_end_s"
            ],
            dtype=np.float64,
        )
        /
        86400.0
    )

    flow_weights = np.asarray(
        db[
            "weights_m3_s"
        ],
        dtype=np.float64,
    )

    producer = np.asarray(
        db[
            "producer"
        ]
    )

    prediction = np.asarray(
        db[
            "PI_RNN_saturation"
        ],
        dtype=np.float64,
    )[
        i100
    ]

    truth = np.asarray(
        db[
            "SG7A_saturation"
        ],
        dtype=np.float64,
    )[
        i100
    ]

    error = (
        prediction
        -
        truth
    )

    n_streamlines, n_nodes = prediction.shape

    if n_nodes != xi.size:

        raise RuntimeError(
            "Prediction node count does not match xi."
        )

    tD = (
        PRIMARY_TIME_DAYS
        /
        tau_end_days
    )

    tD_grid = np.repeat(
        tD[
            :,
            None
        ],
        n_nodes,
        axis=1,
    )

    tau_grid = np.repeat(
        tau_end_days[
            :,
            None
        ],
        n_nodes,
        axis=1,
    )

    xi_grid = np.repeat(
        xi[
            None,
            :
        ],
        n_streamlines,
        axis=0,
    )

    # =========================================================================
    # GLOBAL BIAS
    # =========================================================================

    material_positive = (
        error
        >=
        MATERIAL_POSITIVE_BIAS
    )

    total_material_positive = int(
        np.sum(
            material_positive
        )
    )

    global_mean_bias = float(
        np.mean(
            error
        )
    )

    global_l1 = float(
        np.mean(
            np.abs(
                error
            )
        )
    )

    global_positive_fraction = float(
        np.mean(
            error > 0.0
        )
    )

    global_material_fraction = float(
        np.mean(
            material_positive
        )
    )

    print(
        "\nSTREAMLINE BIAS CONTRACT"
    )

    print(
        f"  Streamlines             : "
        f"{n_streamlines:,}"
    )

    print(
        f"  Nodes                   : "
        f"{n_nodes}"
    )

    print(
        f"  Physical time           : "
        f"{PRIMARY_TIME_DAYS:.1f} days"
    )

    print(
        f"  Terminal TOF range      : "
        f"{np.min(tau_end_days):.3f} -> "
        f"{np.max(tau_end_days):.3f} days"
    )

    print(
        f"  tD range                : "
        f"{np.min(tD):.6f} -> "
        f"{np.max(tD):.6f}"
    )

    print(
        f"  Global mean bias        : "
        f"{global_mean_bias:.6e}"
    )

    print(
        f"  Global L1               : "
        f"{global_l1:.6e}"
    )

    print(
        f"  Positive-bias fraction  : "
        f"{100.0 * global_positive_fraction:.2f}%"
    )

    print(
        f"  Material +bias fraction : "
        f"{100.0 * global_material_fraction:.2f}%"
    )

    # =========================================================================
    # TOF BANDS
    # =========================================================================

    tof_rows = []

    for label, low, high in TOF_BINS_DAYS:

        streamline_mask = band_mask(
            tau_end_days,
            low,
            high,
        )

        node_mask = np.repeat(
            streamline_mask[
                :,
                None
            ],
            n_nodes,
            axis=1,
        )

        row = summarize_bias(
            label,
            error,
            node_mask,
        )

        material_count = int(
            np.sum(
                material_positive
                &
                node_mask
            )
        )

        row[
            "streamlines"
        ] = int(
            np.sum(
                streamline_mask
            )
        )

        row[
            "TOF_low_days"
        ] = (
            ""
            if low is None
            else low
        )

        row[
            "TOF_high_days"
        ] = (
            ""
            if high is None
            else high
        )

        row[
            "share_of_all_material_positive_nodes"
        ] = safe_fraction(
            material_count,
            total_material_positive,
        )

        tof_rows.append(
            row
        )

    # =========================================================================
    # tD BANDS
    # =========================================================================

    td_rows = []

    for label, low, high in TD_BINS:

        streamline_mask = band_mask(
            tD,
            low,
            high,
        )

        node_mask = np.repeat(
            streamline_mask[
                :,
                None
            ],
            n_nodes,
            axis=1,
        )

        row = summarize_bias(
            label,
            error,
            node_mask,
        )

        material_count = int(
            np.sum(
                material_positive
                &
                node_mask
            )
        )

        row[
            "streamlines"
        ] = int(
            np.sum(
                streamline_mask
            )
        )

        row[
            "tD_low"
        ] = (
            ""
            if low is None
            else low
        )

        row[
            "tD_high"
        ] = (
            ""
            if high is None
            else high
        )

        row[
            "share_of_all_material_positive_nodes"
        ] = safe_fraction(
            material_count,
            total_material_positive,
        )

        td_rows.append(
            row
        )

    # =========================================================================
    # XI BANDS
    # =========================================================================

    xi_rows = []

    for label, low, high in XI_BINS:

        node_mask = band_mask(
            xi_grid,
            low,
            high,
        )

        row = summarize_bias(
            label,
            error,
            node_mask,
        )

        material_count = int(
            np.sum(
                material_positive
                &
                node_mask
            )
        )

        row[
            "xi_low"
        ] = low

        row[
            "xi_high"
        ] = high

        row[
            "share_of_all_material_positive_nodes"
        ] = safe_fraction(
            material_count,
            total_material_positive,
        )

        xi_rows.append(
            row
        )

    # =========================================================================
    # SG7A STATE / FRONT BANDS
    # =========================================================================

    state_rows = []

    for label, low, high in STATE_BANDS:

        node_mask = band_mask(
            truth,
            low,
            high,
        )

        row = summarize_bias(
            label,
            error,
            node_mask,
        )

        material_count = int(
            np.sum(
                material_positive
                &
                node_mask
            )
        )

        row[
            "state_low"
        ] = (
            ""
            if low is None
            else low
        )

        row[
            "state_high"
        ] = (
            ""
            if high is None
            else high
        )

        row[
            "share_of_all_material_positive_nodes"
        ] = safe_fraction(
            material_count,
            total_material_positive,
        )

        state_rows.append(
            row
        )

    # =========================================================================
    # PRODUCER BANDS
    # =========================================================================

    producer_rows = []

    for prod in np.unique(
        producer
    ):

        streamline_mask = (
            producer
            ==
            prod
        )

        node_mask = np.repeat(
            streamline_mask[
                :,
                None
            ],
            n_nodes,
            axis=1,
        )

        row = summarize_bias(
            str(
                prod
            ),
            error,
            node_mask,
        )

        material_count = int(
            np.sum(
                material_positive
                &
                node_mask
            )
        )

        row[
            "producer"
        ] = str(
            prod
        )

        row[
            "streamlines"
        ] = int(
            np.sum(
                streamline_mask
            )
        )

        row[
            "flow_weight_m3_day"
        ] = float(
            np.sum(
                flow_weights[
                    streamline_mask
                ]
            )
            *
            86400.0
        )

        row[
            "share_of_all_material_positive_nodes"
        ] = safe_fraction(
            material_count,
            total_material_positive,
        )

        producer_rows.append(
            row
        )

    # =========================================================================
    # SPECIAL REGIONS
    # =========================================================================

    initial_tail_mask = (
        truth
        <=
        INITIAL_TAIL_MAX
    )

    threshold_approach_mask = (
        (truth > INITIAL_TAIL_MAX)
        &
        (truth < PLUME_THRESHOLD)
    )

    front_band_mask = (
        (truth >= FRONT_BAND_LOW)
        &
        (truth <= FRONT_BAND_HIGH)
    )

    swept_mask = (
        truth > FRONT_BAND_HIGH
    )

    tail_material_share = safe_fraction(
        np.sum(
            material_positive
            &
            initial_tail_mask
        ),
        total_material_positive,
    )

    approach_material_share = safe_fraction(
        np.sum(
            material_positive
            &
            threshold_approach_mask
        ),
        total_material_positive,
    )

    front_material_share = safe_fraction(
        np.sum(
            material_positive
            &
            front_band_mask
        ),
        total_material_positive,
    )

    swept_material_share = safe_fraction(
        np.sum(
            material_positive
            &
            swept_mask
        ),
        total_material_positive,
    )

    tail_mean_bias = float(
        np.mean(
            error[
                initial_tail_mask
            ]
        )
    ) if np.any(
        initial_tail_mask
    ) else np.nan

    front_mean_bias = float(
        np.mean(
            error[
                front_band_mask
            ]
        )
    ) if np.any(
        front_band_mask
    ) else np.nan

    # =========================================================================
    # DIAGNOSIS
    # =========================================================================

    # Find most dominant TOF and xi buckets.
    dominant_tof_row = max(
        tof_rows,
        key=lambda row:
            (
                -1.0
                if not np.isfinite(
                    row[
                        "share_of_all_material_positive_nodes"
                    ]
                )
                else
                row[
                    "share_of_all_material_positive_nodes"
                ]
            ),
    )

    dominant_xi_row = max(
        xi_rows,
        key=lambda row:
            (
                -1.0
                if not np.isfinite(
                    row[
                        "share_of_all_material_positive_nodes"
                    ]
                )
                else
                row[
                    "share_of_all_material_positive_nodes"
                ]
            ),
    )

    tail_dominated = bool(
        tail_material_share
        >=
        DOMINANT_NODE_SHARE
    )

    front_dominated = bool(
        front_material_share
        >=
        DOMINANT_NODE_SHARE
    )

    tof_dominated = bool(
        dominant_tof_row[
            "share_of_all_material_positive_nodes"
        ]
        >=
        DOMINANT_NODE_SHARE
    )

    broad_bias = bool(
        sum(
            row[
                "share_of_all_material_positive_nodes"
            ]
            >=
            0.10
            for row
            in state_rows
            if np.isfinite(
                row[
                    "share_of_all_material_positive_nodes"
                ]
            )
        )
        >=
        3
    )

    if tail_dominated:

        diagnosis = (
            "INITIAL_STATE_TAIL_BIAS"
        )

        recommendation = (
            "Most material positive PI-RNN bias occurs where SG7A remains "
            "near the initial saturation. The residual full-grid plume error "
            "is therefore caused by an elevated unswept/tail state rather than "
            "a remaining front-location failure. Design a tail-anchor refinement "
            "that preserves the frozen front-aware improvements and all SG7B-11 "
            "physics gates."
        )

        next_milestone = (
            "V15-SG7B-12 — Initial-State Tail-Anchor "
            "Refinement Design"
        )

    elif front_dominated:

        diagnosis = (
            "FRONT_BAND_BIAS"
        )

        recommendation = (
            "Material positive bias remains concentrated inside the SG7A front "
            "band. Audit the front-aware refinement loss for a systematic state "
            "level shift before additional grid work."
        )

        next_milestone = (
            "V15-SG7B-12 — Front-Level Bias Refinement Design"
        )

    elif tof_dominated:

        diagnosis = (
            "TOF_CONDITIONED_BIAS"
        )

        recommendation = (
            "Material positive state bias is concentrated in one terminal-TOF "
            "population. Design a TOF-conditioned correction/refinement while "
            "preserving the accepted front and canonical-physics contracts."
        )

        next_milestone = (
            "V15-SG7B-12 — TOF-Conditioned Residual Bias "
            "Refinement Design"
        )

    elif broad_bias:

        diagnosis = (
            "BROAD_STREAMLINE_STATE_BIAS"
        )

        recommendation = (
            "The positive residual state bias is distributed across multiple "
            "SG7A state bands rather than a single front/tail/TOF region. "
            "Audit the front-aware model calibration globally before any "
            "localized refinement."
        )

        next_milestone = (
            "V15-SG7B-12 — Global State-Bias Calibration Audit"
        )

    else:

        diagnosis = (
            "RESIDUAL_BIAS_NOT_LOCALIZED"
        )

        recommendation = (
            "The remaining streamline-state offset is not dominated by a single "
            "TOF, xi, or SG7A state region under the current bands. Refine the "
            "conditioning analysis before retraining."
        )

        next_milestone = (
            "V15-SG7C-R2B — Adaptive Residual Bias Localization Audit"
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
        "BIAS BY TERMINAL TOF"
    )

    print(
        "=" * 78
    )

    for row in tof_rows:

        print(
            f"{row['band']:<12s} | "
            f"SL={row['streamlines']:4d} | "
            f"mean={row['mean_bias']:.6e} | "
            f"L1={row['L1']:.6e} | "
            f"mat+={100.0 * row['material_positive_fraction']:6.2f}% | "
            f"share={100.0 * row['share_of_all_material_positive_nodes']:6.2f}%"
        )

    print(
        "\nBIAS BY SG7A STATE BAND"
    )

    for row in state_rows:

        print(
            f"{row['band']:<20s} | "
            f"N={row['samples']:7d} | "
            f"mean={row['mean_bias']:.6e} | "
            f"L1={row['L1']:.6e} | "
            f"mat+={100.0 * row['material_positive_fraction']:6.2f}% | "
            f"share={100.0 * row['share_of_all_material_positive_nodes']:6.2f}%"
        )

    print(
        "\nBIAS BY XI"
    )

    for row in xi_rows:

        print(
            f"{row['band']:<8s} | "
            f"mean={row['mean_bias']:.6e} | "
            f"L1={row['L1']:.6e} | "
            f"share={100.0 * row['share_of_all_material_positive_nodes']:6.2f}%"
        )

    print(
        "\nLOCALIZATION FLAGS"
    )

    print(
        f"  Tail material-bias share    : "
        f"{100.0 * tail_material_share:.2f}%"
    )

    print(
        f"  Threshold-approach share    : "
        f"{100.0 * approach_material_share:.2f}%"
    )

    print(
        f"  Front-band share            : "
        f"{100.0 * front_material_share:.2f}%"
    )

    print(
        f"  Swept-high share            : "
        f"{100.0 * swept_material_share:.2f}%"
    )

    print(
        f"  Tail mean bias              : "
        f"{tail_mean_bias:.6e}"
    )

    print(
        f"  Front-band mean bias        : "
        f"{front_mean_bias:.6e}"
    )

    print(
        f"  Dominant TOF band           : "
        f"{dominant_tof_row['band']} "
        f"({100.0 * dominant_tof_row['share_of_all_material_positive_nodes']:.2f}%)"
    )

    print(
        f"  Dominant xi band            : "
        f"{dominant_xi_row['band']} "
        f"({100.0 * dominant_xi_row['share_of_all_material_positive_nodes']:.2f}%)"
    )

    # =========================================================================
    # SAVE TABLES
    # =========================================================================

    save_csv(
        TOF_TABLE,
        tof_rows,
    )

    save_csv(
        TD_TABLE,
        td_rows,
    )

    save_csv(
        XI_TABLE,
        xi_rows,
    )

    save_csv(
        STATE_BAND_TABLE,
        state_rows,
    )

    save_csv(
        PRODUCER_TABLE,
        producer_rows,
    )

    global_rows = [
        {
            "time_days":
                PRIMARY_TIME_DAYS,

            "global_mean_bias":
                global_mean_bias,

            "global_L1":
                global_l1,

            "positive_bias_fraction":
                global_positive_fraction,

            "material_positive_fraction":
                global_material_fraction,

            "tail_material_share":
                tail_material_share,

            "threshold_approach_material_share":
                approach_material_share,

            "front_material_share":
                front_material_share,

            "swept_material_share":
                swept_material_share,

            "tail_mean_bias":
                tail_mean_bias,

            "front_mean_bias":
                front_mean_bias,

            "dominant_TOF_band":
                dominant_tof_row[
                    "band"
                ],

            "dominant_TOF_share":
                dominant_tof_row[
                    "share_of_all_material_positive_nodes"
                ],

            "dominant_xi_band":
                dominant_xi_row[
                    "band"
                ],

            "dominant_xi_share":
                dominant_xi_row[
                    "share_of_all_material_positive_nodes"
                ],
        }
    ]

    save_csv(
        GLOBAL_TABLE,
        global_rows,
    )

    # =========================================================================
    # DATABASE
    # =========================================================================

    np.savez_compressed(
        DATABASE_FILE,

        error_100d=
            error.astype(
                np.float32
            ),

        PI_RNN_100d=
            prediction.astype(
                np.float32
            ),

        SG7A_100d=
            truth.astype(
                np.float32
            ),

        material_positive_mask=
            material_positive,

        terminal_TOF_days=
            tau_end_days.astype(
                np.float64
            ),

        streamline_tD_100d=
            tD.astype(
                np.float64
            ),

        xi=
            xi.astype(
                np.float64
            ),

        producer=
            producer,

        flow_weights_m3_s=
            flow_weights.astype(
                np.float64
            ),
    )

    # =========================================================================
    # PLOTS
    # =========================================================================

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    ax.bar(
        [
            row[
                "band"
            ]
            for row
            in state_rows
        ],
        [
            100.0
            *
            row[
                "share_of_all_material_positive_nodes"
            ]
            for row
            in state_rows
        ],
    )

    ax.set_ylabel(
        "Share of material positive-bias nodes [%]"
    )

    ax.set_xlabel(
        "SG7A state band"
    )

    ax.set_title(
        "PAD-Stream V15-SG7C-R2\n"
        "Residual Bias Localization by SG7A State"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7CR2_Bias_Share_By_State_Band.png",
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
        [
            row[
                "band"
            ]
            for row
            in tof_rows
        ],
        [
            row[
                "mean_bias"
            ]
            for row
            in tof_rows
        ],
        marker="o",
    )

    ax.set_ylabel(
        "Mean PI-RNN - SG7A bias"
    )

    ax.set_xlabel(
        "Terminal TOF band"
    )

    ax.set_title(
        "PAD-Stream V15-SG7C-R2\n"
        "Residual Bias vs Terminal TOF"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7CR2_Mean_Bias_vs_TOF.png",
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
        xi,
        np.mean(
            error,
            axis=0,
        ),
    )

    ax.axhline(
        0.0,
        linestyle="--",
    )

    ax.set_xlabel(
        "xi"
    )

    ax.set_ylabel(
        "Mean PI-RNN - SG7A bias"
    )

    ax.set_title(
        "PAD-Stream V15-SG7C-R2\n"
        "Mean Residual Bias Along Streamline Coordinate"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7CR2_Mean_Bias_vs_Xi.png",
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
            "Incoming SG7D-R2C diagnosis reproduced",
            sg7dr2c_summary.get(
                "diagnosis"
            )
            ==
            "SYSTEMATIC_STREAMLINE_STATE_OFFSET",
        ),

        (
            "SG7C-R prediction finite",
            bool(
                np.all(
                    np.isfinite(
                        prediction
                    )
                )
            ),
        ),

        (
            "SG7A truth finite",
            bool(
                np.all(
                    np.isfinite(
                        truth
                    )
                )
            ),
        ),

        (
            "Terminal TOF finite and positive",
            bool(
                np.all(
                    np.isfinite(
                        tau_end_days
                    )
                )
                and
                np.all(
                    tau_end_days
                    >
                    0.0
                )
            ),
        ),

        (
            "Residual bias samples available",
            error.size
            >
            0,
        ),

        (
            "Material positive-bias population nonzero",
            total_material_positive
            >
            0,
        ),

        (
            "All localization tables populated",
            bool(
                tof_rows
                and
                td_rows
                and
                xi_rows
                and
                state_rows
                and
                producer_rows
            ),
        ),

        (
            "Diagnostic classification established",
            diagnosis
            in
            {
                "INITIAL_STATE_TAIL_BIAS",
                "TOF_CONDITIONED_BIAS",
                "FRONT_BAND_BIAS",
                "BROAD_STREAMLINE_STATE_BIAS",
                "RESIDUAL_BIAS_NOT_LOCALIZED",
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
        "V15-SG7C-R2 DIAGNOSTIC VALIDATION"
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
        f"  Tail dominated          : "
        f"{tail_dominated}"
    )

    print(
        f"  Front dominated         : "
        f"{front_dominated}"
    )

    print(
        f"  TOF dominated           : "
        f"{tof_dominated}"
    )

    print(
        f"  Broad bias              : "
        f"{broad_bias}"
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
            "V15-SG7C-R2",

        "description":
            "Residual streamline-state bias by TOF / front-band audit",

        "training_performed":
            False,

        "model_changed":
            False,

        "seed_density_changed":
            False,

        "streamline_geometry_changed":
            False,

        "mapback_changed":
            False,

        "plume_threshold_changed":
            False,

        "primary_time_days":
            PRIMARY_TIME_DAYS,

        "global_bias": {
            "mean":
                global_mean_bias,

            "L1":
                global_l1,

            "positive_fraction":
                global_positive_fraction,

            "material_positive_fraction":
                global_material_fraction,
        },

        "localization": {
            "tail_material_share":
                tail_material_share,

            "threshold_approach_material_share":
                approach_material_share,

            "front_material_share":
                front_material_share,

            "swept_material_share":
                swept_material_share,

            "tail_mean_bias":
                tail_mean_bias,

            "front_mean_bias":
                front_mean_bias,

            "dominant_TOF_band":
                dominant_tof_row[
                    "band"
                ],

            "dominant_TOF_share":
                dominant_tof_row[
                    "share_of_all_material_positive_nodes"
                ],

            "dominant_xi_band":
                dominant_xi_row[
                    "band"
                ],

            "dominant_xi_share":
                dominant_xi_row[
                    "share_of_all_material_positive_nodes"
                ],
        },

        "diagnostic_flags": {
            "tail_dominated":
                tail_dominated,

            "front_dominated":
                front_dominated,

            "TOF_dominated":
                tof_dominated,

            "broad_bias":
                broad_bias,
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
        f"  {TOF_TABLE.name}"
    )

    print(
        f"  {TD_TABLE.name}"
    )

    print(
        f"  {XI_TABLE.name}"
    )

    print(
        f"  {STATE_BAND_TABLE.name}"
    )

    print(
        f"  {PRODUCER_TABLE.name}"
    )

    print(
        f"  {GLOBAL_TABLE.name}"
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
        "  V15SG7CR2_Bias_Share_By_State_Band.png"
    )

    print(
        "  V15SG7CR2_Mean_Bias_vs_TOF.png"
    )

    print(
        "  V15SG7CR2_Mean_Bias_vs_Xi.png"
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
            "V15-SG7C-R2 AUDIT: PASS"
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
            "V15-SG7C-R2 AUDIT: INCOMPLETE"
        )

        print()

        print(
            "Do not retrain or modify transport until the residual "
            "streamline-state bias has been localized."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":

    main()
