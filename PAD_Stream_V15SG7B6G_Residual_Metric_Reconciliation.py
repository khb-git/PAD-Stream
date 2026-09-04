from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf

# Import the frozen/corrected operator implementation rather than duplicating it.
import PAD_Stream_V15SG7B6FR_Activity_Scaled_Coupled_Refinement as sg6fr


# =============================================================================
# PAD-Stream V15-SG7B-6G
# Residual Metric and Freeze-Gate Reconciliation
#
# NO TRAINING.
#
# PURPOSE
# -------
# Reconcile the different residual measures that have appeared during the
# SG7B PI-RNN development.
#
#
# MODELS COMPARED
# ---------------
# SG7A
#     frozen classical finite-volume truth
#
# SG7B-6B
#     best previous physics-balanced PI-RNN checkpoint
#
# SG7B-6D
#     best saturation / component-accuracy PI-RNN checkpoint
#
#
# QUESTIONS
# ---------
# 1. Does self-normalized FV residual tell the same story as absolute
#    conservative balance?
#
# 2. Does normalization by SG7A physical activity change model ranking?
#
# 3. How large is:
#
#       R_NN - R_SG7A
#
#    compared with the governing-equation activity?
#
# 4. How sensitive are residual conclusions to the finite-difference
#    interval used for dS/dtD?
#
# 5. Is the current:
#
#       PI-RNN FV MAE / SG7A FV MAE
#
#    ratio a numerically well-conditioned comparison?
#
#
# IMPORTANT
# ---------
# This milestone does NOT:
#
#     change the current freeze threshold
#     freeze any model
#     train any model
#     modify the neural architecture
#
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent


DATASET_FILE = (
    ROOT
    / "output"
    / "V15_SG7B3"
    / "SG7B3_REFERENCE_DATASET.npz"
)


SG7A_FILE = (
    ROOT
    / "output"
    / "V15_SG7A"
    / "FULL_PHYSICS_STREAMLINE_SATURATION.npz"
)


MODEL_6B_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6B"
    / "V15SG7B6B_Best_Model.keras"
)


MODEL_6D_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6D"
    / "V15SG7B6D_Best_Model.keras"
)


OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B6G"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B6G_Summary.json"
)


METRIC_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7B6G_Residual_Metrics.csv"
)


DT_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7B6G_dt_Sensitivity.csv"
)


PROFILE_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7B6G_Profile_Metrics.csv"
)


DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7B6G_Residual_Reconciliation.npz"
)


# =============================================================================
# CANONICAL CONTRACT
# =============================================================================

EXPECTED_SG7A_FV_MAE = 6.323248e-04

CURRENT_MAX_FV_RATIO = 50.0

ACTIVITY_FLOOR = 1.0e-4

EPS = 1.0e-12

BATCH_SIZE = 32


# =============================================================================
# TEMPORAL-DIFFERENCE AUDIT
# =============================================================================

DT_MULTIPLIERS = np.asarray(
    [
        0.25,
        0.50,
        1.00,
        2.00,
        4.00,
    ],
    dtype=np.float64,
)


# =============================================================================
# LOAD DATABASES
# =============================================================================

def load_dataset():

    if not DATASET_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-3 reference dataset:\n"
            f"{DATASET_FILE}"
        )

    data = np.load(
        DATASET_FILE
    )

    required = [
        "X_test",
        "Y_test",
        "index_test",
        "tD_test",
        "xi",
        "tD_scale",
    ]

    for key in required:

        if key not in data:

            raise KeyError(
                f"Missing SG7B-3 field: {key}"
            )

    return {
        key: data[key]
        for key in required
    }


def load_sg7a():

    if not SG7A_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7A master database:\n"
            f"{SG7A_FILE}"
        )

    data = np.load(
        SG7A_FILE
    )

    required = [
        "xi",
        "master_tD",
        "master_saturation",
    ]

    for key in required:

        if key not in data:

            raise KeyError(
                f"Missing SG7A field: {key}"
            )

    return {
        key: data[key]
        for key in required
    }


# =============================================================================
# BASIC METRICS
# =============================================================================

def mae(values):

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


def safe_ratio(
    numerator,
    denominator,
):

    return float(
        numerator
        /
        max(
            denominator,
            EPS,
        )
    )


# =============================================================================
# SG7A INTERPOLATION
#
# Needed because dt multipliers 0.25 and 0.50 do not necessarily coincide
# with an existing SG7A master snapshot.
# =============================================================================

def interpolate_sg7a_profile(
    target_tD,
    master_tD,
    master_S,
):

    target_tD = float(
        np.clip(
            target_tD,
            master_tD[0],
            master_tD[-1],
        )
    )

    if target_tD <= master_tD[0]:

        return (
            master_S[0]
            .astype(
                np.float64
            )
            .copy()
        )

    if target_tD >= master_tD[-1]:

        return (
            master_S[-1]
            .astype(
                np.float64
            )
            .copy()
        )

    right = int(
        np.searchsorted(
            master_tD,
            target_tD,
            side="right",
        )
    )

    left = right - 1

    t0 = float(
        master_tD[left]
    )

    t1 = float(
        master_tD[right]
    )

    alpha = (
        target_tD
        - t0
    ) / (
        t1
        - t0
    )

    return (
        (1.0 - alpha)
        * master_S[left]
        +
        alpha
        * master_S[right]
    ).astype(
        np.float64
    )


# =============================================================================
# SG7A TEMPORAL COMPONENT AT ARBITRARY DT
# =============================================================================

def sg7a_temporal_at_dt(
    tD_values,
    master_tD,
    master_S,
    base_dt,
    multiplier,
):

    temporal = np.zeros(
        (
            len(tD_values),
            master_S.shape[1],
        ),
        dtype=np.float64,
    )

    for p, tD in enumerate(
        tD_values
    ):

        delta = (
            base_dt
            * multiplier
        )

        t_minus = max(
            float(tD)
            - delta,
            float(
                master_tD[0]
            ),
        )

        t_plus = min(
            float(tD)
            + delta,
            float(
                master_tD[-1]
            ),
        )

        S_minus = (
            interpolate_sg7a_profile(
                t_minus,
                master_tD,
                master_S,
            )
        )

        S_plus = (
            interpolate_sg7a_profile(
                t_plus,
                master_tD,
                master_S,
            )
        )

        effective_dt = (
            t_plus
            - t_minus
        )

        temporal[p] = (
            S_plus
            - S_minus
        ) / max(
            effective_dt,
            EPS,
        )

    return temporal


# =============================================================================
# MODEL INPUT FOR ARBITRARY TIME
# =============================================================================

def make_model_input(
    xi,
    tD_values,
    tD_scale,
):

    xi = np.asarray(
        xi,
        dtype=np.float32,
    )

    tD_values = np.asarray(
        tD_values,
        dtype=np.float64,
    )

    X = np.zeros(
        (
            len(tD_values),
            len(xi),
            2,
        ),
        dtype=np.float32,
    )

    X[
        :,
        :,
        0
    ] = xi[
        None,
        :
    ]

    X[
        :,
        :,
        1
    ] = (
        tD_values
        / tD_scale
    )[
        :,
        None
    ]

    return X


# =============================================================================
# PI-RNN TEMPORAL COMPONENT AT ARBITRARY DT
# =============================================================================

def model_temporal_at_dt(
    model,
    xi,
    tD_values,
    tD_scale,
    base_dt,
    multiplier,
):

    delta = (
        base_dt
        * multiplier
    )

    t_minus = np.maximum(
        tD_values
        - delta,
        0.0,
    )

    t_plus = np.minimum(
        tD_values
        + delta,
        tD_scale,
    )

    X_minus = make_model_input(
        xi,
        t_minus,
        tD_scale,
    )

    X_plus = make_model_input(
        xi,
        t_plus,
        tD_scale,
    )

    S_minus = (
        model.predict(
            X_minus,
            batch_size=BATCH_SIZE,
            verbose=0,
        )[
            :,
            :,
            0
        ]
    ).astype(
        np.float64
    )

    S_plus = (
        model.predict(
            X_plus,
            batch_size=BATCH_SIZE,
            verbose=0,
        )[
            :,
            :,
            0
        ]
    ).astype(
        np.float64
    )

    effective_dt = (
        t_plus
        - t_minus
    )

    return (
        S_plus
        -
        S_minus
    ) / (
        effective_dt[
            :,
            None
        ]
        +
        EPS
    )


# =============================================================================
# SPATIAL COMPONENT DATABASE
#
# Uses the exact canonical operator functions imported from SG7B-6F-R.
# =============================================================================

def spatial_database(
    saturation,
    xi,
):

    n_profiles = (
        saturation.shape[0]
    )

    adv = np.zeros_like(
        saturation,
        dtype=np.float64,
    )

    cap = np.zeros_like(
        saturation,
        dtype=np.float64,
    )

    for p in range(
        n_profiles
    ):

        (
            adv[p],
            cap[p],
        ) = (
            sg6fr
            .canonical_spatial_components_np(
                saturation[p],
                xi,
            )
        )

    return (
        adv,
        cap,
    )


# =============================================================================
# RESIDUAL METRIC DEFINITIONS
# =============================================================================

def residual_metrics(
    temporal,
    adv,
    cap,
    truth_temporal,
    truth_adv,
    truth_cap,
):

    residual = (
        temporal
        +
        adv
        -
        cap
    )

    truth_residual = (
        truth_temporal
        +
        truth_adv
        -
        truth_cap
    )

    self_activity = (
        np.abs(
            temporal
        )
        +
        np.abs(
            adv
        )
        +
        np.abs(
            cap
        )
        +
        ACTIVITY_FLOOR
    )

    truth_activity = (
        np.abs(
            truth_temporal
        )
        +
        np.abs(
            truth_adv
        )
        +
        np.abs(
            truth_cap
        )
        +
        ACTIVITY_FLOOR
    )

    self_relative = (
        residual
        /
        self_activity
    )

    truth_scaled_residual = (
        residual
        /
        truth_activity
    )

    residual_difference = (
        residual
        -
        truth_residual
    )

    truth_scaled_difference = (
        residual_difference
        /
        truth_activity
    )

    return {
        "residual":
            residual,

        "truth_residual":
            truth_residual,

        "self_activity":
            self_activity,

        "truth_activity":
            truth_activity,

        "self_relative":
            self_relative,

        "truth_scaled_residual":
            truth_scaled_residual,

        "residual_difference":
            residual_difference,

        "truth_scaled_difference":
            truth_scaled_difference,
    }


# =============================================================================
# BUILD CANONICAL SG7A REFERENCE
# =============================================================================

def build_truth_reference(
    dataset,
    sg7a,
    multiplier,
):

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=np.float64,
    )

    tD_values = np.asarray(
        dataset[
            "tD_test"
        ],
        dtype=np.float64,
    )

    master_tD = np.asarray(
        sg7a[
            "master_tD"
        ],
        dtype=np.float64,
    )

    master_S = np.asarray(
        sg7a[
            "master_saturation"
        ],
        dtype=np.float64,
    )

    indices = np.asarray(
        dataset[
            "index_test"
        ],
        dtype=int,
    )

    truth_S = (
        master_S[
            indices
        ]
    )

    base_dt = float(
        dataset[
            "tD_scale"
        ][0]
        / 800.0
    )

    temporal = (
        sg7a_temporal_at_dt(
            tD_values,
            master_tD,
            master_S,
            base_dt,
            multiplier,
        )
    )

    (
        adv,
        cap,
    ) = spatial_database(
        truth_S,
        xi,
    )

    residual = (
        temporal
        +
        adv
        -
        cap
    )

    activity = (
        np.abs(
            temporal
        )
        +
        np.abs(
            adv
        )
        +
        np.abs(
            cap
        )
        +
        ACTIVITY_FLOOR
    )

    relative = (
        residual
        /
        activity
    )

    return {
        "S":
            truth_S,

        "temporal":
            temporal,

        "adv":
            adv,

        "cap":
            cap,

        "residual":
            residual,

        "activity":
            activity,

        "relative":
            relative,
    }


# =============================================================================
# BUILD MODEL RESULT
# =============================================================================

def build_model_result(
    model,
    dataset,
    truth,
    multiplier,
):

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=np.float64,
    )

    tD_values = np.asarray(
        dataset[
            "tD_test"
        ],
        dtype=np.float64,
    )

    tD_scale = float(
        dataset[
            "tD_scale"
        ][0]
    )

    base_dt = (
        tD_scale
        / 800.0
    )

    prediction = (
        model.predict(
            dataset[
                "X_test"
            ].astype(
                np.float32
            ),
            batch_size=BATCH_SIZE,
            verbose=0,
        )[
            :,
            :,
            0
        ]
    ).astype(
        np.float64
    )

    temporal = (
        model_temporal_at_dt(
            model,
            xi,
            tD_values,
            tD_scale,
            base_dt,
            multiplier,
        )
    )

    (
        adv,
        cap,
    ) = spatial_database(
        prediction,
        xi,
    )

    metrics = residual_metrics(
        temporal,
        adv,
        cap,
        truth[
            "temporal"
        ],
        truth[
            "adv"
        ],
        truth[
            "cap"
        ],
    )

    return {
        "prediction":
            prediction,

        "temporal":
            temporal,

        "adv":
            adv,

        "cap":
            cap,

        **metrics,
    }


# =============================================================================
# GLOBAL SUMMARY ROW
# =============================================================================

def global_summary_row(
    model_name,
    result,
    truth,
    multiplier,
):

    saturation_error = (
        result[
            "prediction"
        ]
        -
        truth[
            "S"
        ]
    )

    temporal_error = (
        result[
            "temporal"
        ]
        -
        truth[
            "temporal"
        ]
    )

    adv_error = (
        result[
            "adv"
        ]
        -
        truth[
            "adv"
        ]
    )

    cap_error = (
        result[
            "cap"
        ]
        -
        truth[
            "cap"
        ]
    )

    self_relative_mae = mae(
        result[
            "self_relative"
        ]
    )

    truth_scaled_residual_mae = mae(
        result[
            "truth_scaled_residual"
        ]
    )

    residual_difference_mae = mae(
        result[
            "residual_difference"
        ]
    )

    truth_scaled_difference_mae = mae(
        result[
            "truth_scaled_difference"
        ]
    )

    return {
        "model":
            model_name,

        "dt_multiplier":
            float(
                multiplier
            ),

        "saturation_L1":
            mae(
                saturation_error
            ),

        "saturation_L2":
            rms(
                saturation_error
            ),

        "temporal_difference_MAE":
            mae(
                temporal_error
            ),

        "advective_difference_MAE":
            mae(
                adv_error
            ),

        "capillary_difference_MAE":
            mae(
                cap_error
            ),

        "absolute_residual_MAE":
            mae(
                result[
                    "residual"
                ]
            ),

        "self_relative_FV_MAE":
            self_relative_mae,

        "truth_scaled_residual_MAE":
            truth_scaled_residual_mae,

        "residual_difference_MAE":
            residual_difference_mae,

        "truth_scaled_difference_MAE":
            truth_scaled_difference_mae,

        "legacy_ratio_to_SG7A":
            safe_ratio(
                self_relative_mae,
                EXPECTED_SG7A_FV_MAE,
            ),
    }


# =============================================================================
# SG7A SUMMARY ROW
# =============================================================================

def truth_summary_row(
    truth,
    multiplier,
):

    relative_mae = mae(
        truth[
            "relative"
        ]
    )

    return {
        "model":
            "SG7A",

        "dt_multiplier":
            float(
                multiplier
            ),

        "saturation_L1":
            0.0,

        "saturation_L2":
            0.0,

        "temporal_difference_MAE":
            0.0,

        "advective_difference_MAE":
            0.0,

        "capillary_difference_MAE":
            0.0,

        "absolute_residual_MAE":
            mae(
                truth[
                    "residual"
                ]
            ),

        "self_relative_FV_MAE":
            relative_mae,

        "truth_scaled_residual_MAE":
            relative_mae,

        "residual_difference_MAE":
            0.0,

        "truth_scaled_difference_MAE":
            0.0,

        "legacy_ratio_to_SG7A":
            safe_ratio(
                relative_mae,
                EXPECTED_SG7A_FV_MAE,
            ),
    }


# =============================================================================
# PROFILE METRICS
# =============================================================================

def profile_rows(
    dataset,
    truth,
    result_6b,
    result_6d,
):

    rows = []

    tD = np.asarray(
        dataset[
            "tD_test"
        ],
        dtype=np.float64,
    )

    for p in range(
        len(tD)
    ):

        row = {
            "profile":
                int(
                    p
                ),

            "tD":
                float(
                    tD[p]
                ),

            "SG7A_FV_MAE":
                mae(
                    truth[
                        "relative"
                    ][p]
                ),
        }

        for (
            label,
            result,
        ) in [
            (
                "SG7B6B",
                result_6b,
            ),
            (
                "SG7B6D",
                result_6d,
            ),
        ]:

            row[
                f"{label}_self_FV_MAE"
            ] = mae(
                result[
                    "self_relative"
                ][p]
            )

            row[
                f"{label}_truth_scaled_residual_MAE"
            ] = mae(
                result[
                    "truth_scaled_residual"
                ][p]
            )

            row[
                f"{label}_deltaR_MAE"
            ] = mae(
                result[
                    "residual_difference"
                ][p]
            )

            row[
                f"{label}_truth_scaled_deltaR_MAE"
            ] = mae(
                result[
                    "truth_scaled_difference"
                ][p]
            )

        rows.append(
            row
        )

    return rows


# =============================================================================
# DIAGNOSTIC DECISION
# =============================================================================

def determine_diagnosis(
    row_6b,
    row_6d,
    dt_rows_6d,
):

    # -------------------------------------------------------------------------
    # Does model ranking differ depending on residual definition?
    # -------------------------------------------------------------------------

    self_prefers_6b = (
        row_6b[
            "self_relative_FV_MAE"
        ]
        <
        row_6d[
            "self_relative_FV_MAE"
        ]
    )

    absolute_delta_prefers_6d = (
        row_6d[
            "residual_difference_MAE"
        ]
        <
        row_6b[
            "residual_difference_MAE"
        ]
    )

    truth_scaled_delta_prefers_6d = (
        row_6d[
            "truth_scaled_difference_MAE"
        ]
        <
        row_6b[
            "truth_scaled_difference_MAE"
        ]
    )

    metric_ranking_inversion = (
        self_prefers_6b
        and
        (
            absolute_delta_prefers_6d
            or
            truth_scaled_delta_prefers_6d
        )
    )

    # -------------------------------------------------------------------------
    # dt sensitivity of SG7B-6D
    # -------------------------------------------------------------------------

    dt_values = np.asarray(
        [
            row[
                "self_relative_FV_MAE"
            ]
            for row
            in dt_rows_6d
        ],
        dtype=np.float64,
    )

    dt_sensitivity_factor = (
        np.max(
            dt_values
        )
        /
        max(
            np.min(
                dt_values
            ),
            EPS,
        )
    )

    derivative_sensitive = (
        dt_sensitivity_factor
        > 1.25
    )

    # -------------------------------------------------------------------------
    # Diagnosis
    # -------------------------------------------------------------------------

    if (
        metric_ranking_inversion
        and
        derivative_sensitive
    ):

        diagnosis = (
            "RESIDUAL_METRIC_AND_TEMPORAL_CONDITIONING"
        )

        recommendation = (
            "The current FV freeze ratio mixes residual normalization "
            "effects with finite-difference derivative sensitivity. "
            "Do not change the freeze gate yet. Reconcile the canonical "
            "PI-RNN physics metric before additional training."
        )

    elif metric_ranking_inversion:

        diagnosis = (
            "RESIDUAL_METRIC_CONDITIONING"
        )

        recommendation = (
            "Residual definitions produce different model rankings. "
            "The next milestone should establish one canonical surrogate "
            "physics metric before changing architecture or freeze gates."
        )

    elif derivative_sensitive:

        diagnosis = (
            "TEMPORAL_DERIVATIVE_CONDITIONING"
        )

        recommendation = (
            "Residual conclusions are materially sensitive to the finite-"
            "difference interval used for dS/dtD. The next milestone should "
            "stabilize the temporal derivative operator."
        )

    else:

        diagnosis = (
            "TRUE_PIRNN_PHYSICS_FLOOR"
        )

        recommendation = (
            "Residual rankings are stable across definitions and temporal "
            "step sizes. The remaining discrepancy is more consistent with "
            "a real representational/architecture physics floor."
        )

    return {
        "diagnosis":
            diagnosis,

        "self_metric_prefers_SG7B6B":
            bool(
                self_prefers_6b
            ),

        "absolute_deltaR_prefers_SG7B6D":
            bool(
                absolute_delta_prefers_6d
            ),

        "truth_scaled_deltaR_prefers_SG7B6D":
            bool(
                truth_scaled_delta_prefers_6d
            ),

        "metric_ranking_inversion":
            bool(
                metric_ranking_inversion
            ),

        "SG7B6D_dt_sensitivity_factor":
            float(
                dt_sensitivity_factor
            ),

        "temporal_derivative_sensitive":
            bool(
                derivative_sensitive
            ),

        "recommendation":
            recommendation,
    }


# =============================================================================
# SAVE CSV
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


# =============================================================================
# PLOTS
# =============================================================================

def plot_metric_comparison(
    authoritative_rows,
):

    labels = [
        "SG7B-6B",
        "SG7B-6D",
    ]

    rows = {
        row[
            "model"
        ]:
            row
        for row
        in authoritative_rows
    }

    x = np.arange(
        len(
            labels
        )
    )

    width = 0.19

    self_values = [
        rows[
            label
        ][
            "self_relative_FV_MAE"
        ]
        for label
        in labels
    ]

    truth_scale_values = [
        rows[
            label
        ][
            "truth_scaled_residual_MAE"
        ]
        for label
        in labels
    ]

    delta_values = [
        rows[
            label
        ][
            "residual_difference_MAE"
        ]
        for label
        in labels
    ]

    delta_relative_values = [
        rows[
            label
        ][
            "truth_scaled_difference_MAE"
        ]
        for label
        in labels
    ]

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    ax.bar(
        x - 1.5 * width,
        self_values,
        width,
        label="Self-normalized FV",
    )

    ax.bar(
        x - 0.5 * width,
        truth_scale_values,
        width,
        label="SG7A-scaled residual",
    )

    ax.bar(
        x + 0.5 * width,
        delta_values,
        width,
        label="Absolute ΔR",
    )

    ax.bar(
        x + 1.5 * width,
        delta_relative_values,
        width,
        label="SG7A-scaled ΔR",
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        labels
    )

    ax.set_ylabel(
        "Residual metric"
    )

    ax.set_yscale(
        "log"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6G\n"
        "Residual Metric Reconciliation"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6G_Residual_Metric_Comparison.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_dt_sensitivity(
    dt_rows,
):

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    for label in [
        "SG7A",
        "SG7B-6B",
        "SG7B-6D",
    ]:

        rows = [
            row
            for row
            in dt_rows
            if row[
                "model"
            ] == label
        ]

        rows = sorted(
            rows,
            key=lambda item:
                item[
                    "dt_multiplier"
                ],
        )

        ax.plot(
            [
                row[
                    "dt_multiplier"
                ]
                for row
                in rows
            ],
            [
                row[
                    "self_relative_FV_MAE"
                ]
                for row
                in rows
            ],
            marker="o",
            label=label,
        )

    ax.set_xscale(
        "log"
    )

    ax.set_yscale(
        "log"
    )

    ax.set_xlabel(
        r"$\Delta t$ multiplier"
    )

    ax.set_ylabel(
        "Self-normalized FV MAE"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6G\n"
        "Temporal-Difference Sensitivity"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6G_dt_Sensitivity.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_profile_metric_comparison(
    profile_data,
):

    tD = np.asarray(
        [
            row[
                "tD"
            ]
            for row
            in profile_data
        ]
    )

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    ax.plot(
        tD,
        [
            row[
                "SG7B6B_self_FV_MAE"
            ]
            for row
            in profile_data
        ],
        label="SG7B-6B self FV",
    )

    ax.plot(
        tD,
        [
            row[
                "SG7B6D_self_FV_MAE"
            ]
            for row
            in profile_data
        ],
        label="SG7B-6D self FV",
    )

    ax.plot(
        tD,
        [
            row[
                "SG7B6B_truth_scaled_deltaR_MAE"
            ]
            for row
            in profile_data
        ],
        linestyle="--",
        label="SG7B-6B SG7A-scaled ΔR",
    )

    ax.plot(
        tD,
        [
            row[
                "SG7B6D_truth_scaled_deltaR_MAE"
            ]
            for row
            in profile_data
        ],
        linestyle="--",
        label="SG7B-6D SG7A-scaled ΔR",
    )

    ax.set_yscale(
        "log"
    )

    ax.set_xlabel(
        r"$t_D$"
    )

    ax.set_ylabel(
        "Residual metric"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6G\n"
        "Residual Metrics vs Dimensionless Time"
    )

    ax.legend(
        fontsize=8,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6G_Residual_Metrics_vs_tD.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_residual_maps(
    dataset,
    result_6b,
    result_6d,
):

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=np.float64,
    )

    tD = np.asarray(
        dataset[
            "tD_test"
        ],
        dtype=np.float64,
    )

    for (
        label,
        result,
    ) in [
        (
            "SG7B6B",
            result_6b,
        ),
        (
            "SG7B6D",
            result_6d,
        ),
    ]:

        fig, ax = plt.subplots(
            figsize=(
                10,
                6,
            )
        )

        image = ax.imshow(
            np.abs(
                result[
                    "truth_scaled_difference"
                ]
            ),
            origin="lower",
            aspect="auto",
            extent=[
                xi[0],
                xi[-1],
                tD[0],
                tD[-1],
            ],
        )

        colorbar = fig.colorbar(
            image,
            ax=ax,
        )

        colorbar.set_label(
            r"$|(R_{NN}-R_{SG7A})/A_{SG7A}|$"
        )

        ax.set_xlabel(
            r"$\xi$"
        )

        ax.set_ylabel(
            r"$t_D$"
        )

        ax.set_title(
            "PAD-Stream V15-SG7B-6G\n"
            f"{label} SG7A-Scaled Residual Difference"
        )

        fig.tight_layout()

        fig.savefig(
            OUTPUT_DIR
            / f"V15SG7B6G_{label}_Scaled_DeltaR_Map.png",
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
        "PAD-Stream Version 15-SG7B-6G"
    )

    print(
        "Residual Metric and Freeze-Gate Reconciliation"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    print(
        "NO FREEZE GATE WILL BE CHANGED."
    )

    # =========================================================================
    # LOAD
    # =========================================================================

    dataset = load_dataset()

    sg7a = load_sg7a()

    if not MODEL_6B_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-6B model:\n"
            f"{MODEL_6B_FILE}"
        )

    if not MODEL_6D_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-6D model:\n"
            f"{MODEL_6D_FILE}"
        )

    model_6b = tf.keras.models.load_model(
        MODEL_6B_FILE
    )

    model_6d = tf.keras.models.load_model(
        MODEL_6D_FILE
    )

    print(
        "\nMODELS"
    )

    print(
        "  SG7B-6B load            : PASS"
    )

    print(
        "  SG7B-6D load            : PASS"
    )

    print(
        f"  Test profiles           : "
        f"{len(dataset['X_test'])}"
    )

    print(
        f"  xi nodes                : "
        f"{len(dataset['xi'])}"
    )

    # =========================================================================
    # DT AUDIT
    # =========================================================================

    all_rows = []

    authoritative_truth = None
    authoritative_6b = None
    authoritative_6d = None

    print(
        "\n"
        + "=" * 78
    )

    print(
        "TEMPORAL-DIFFERENCE / RESIDUAL-METRIC AUDIT"
    )

    print(
        "=" * 78
    )

    for multiplier in DT_MULTIPLIERS:

        print(
            f"\ndt multiplier = "
            f"{multiplier:.2f}"
        )

        truth = build_truth_reference(
            dataset,
            sg7a,
            multiplier,
        )

        result_6b = build_model_result(
            model_6b,
            dataset,
            truth,
            multiplier,
        )

        result_6d = build_model_result(
            model_6d,
            dataset,
            truth,
            multiplier,
        )

        row_truth = truth_summary_row(
            truth,
            multiplier,
        )

        row_6b = global_summary_row(
            "SG7B-6B",
            result_6b,
            truth,
            multiplier,
        )

        row_6d = global_summary_row(
            "SG7B-6D",
            result_6d,
            truth,
            multiplier,
        )

        all_rows.extend(
            [
                row_truth,
                row_6b,
                row_6d,
            ]
        )

        print(
            f"  SG7A FV               : "
            f"{row_truth['self_relative_FV_MAE']:.6e}"
        )

        print(
            f"  SG7B-6B self FV       : "
            f"{row_6b['self_relative_FV_MAE']:.6e}"
        )

        print(
            f"  SG7B-6D self FV       : "
            f"{row_6d['self_relative_FV_MAE']:.6e}"
        )

        print(
            f"  SG7B-6B scaled deltaR : "
            f"{row_6b['truth_scaled_difference_MAE']:.6e}"
        )

        print(
            f"  SG7B-6D scaled deltaR : "
            f"{row_6d['truth_scaled_difference_MAE']:.6e}"
        )

        if np.isclose(
            multiplier,
            1.0,
        ):

            authoritative_truth = truth
            authoritative_6b = result_6b
            authoritative_6d = result_6d

            authoritative_row_truth = row_truth
            authoritative_row_6b = row_6b
            authoritative_row_6d = row_6d

    # =========================================================================
    # CANONICAL SG7A CHECK
    # =========================================================================

    canonical_error = abs(
        authoritative_row_truth[
            "self_relative_FV_MAE"
        ]
        -
        EXPECTED_SG7A_FV_MAE
    )

    canonical_relative_error = (
        canonical_error
        /
        EXPECTED_SG7A_FV_MAE
    )

    canonical_pass = (
        canonical_relative_error
        < 0.05
    )

    # =========================================================================
    # PROFILE DATA
    # =========================================================================

    profiles = profile_rows(
        dataset,
        authoritative_truth,
        authoritative_6b,
        authoritative_6d,
    )

    # =========================================================================
    # DIAGNOSIS
    # =========================================================================

    dt_rows_6d = [
        row
        for row
        in all_rows
        if row[
            "model"
        ] == "SG7B-6D"
    ]

    diagnosis = determine_diagnosis(
        authoritative_row_6b,
        authoritative_row_6d,
        dt_rows_6d,
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "AUTHORITATIVE dt = 1.0 COMPARISON"
    )

    print(
        "=" * 78
    )

    print(
        "\nSG7A"
    )

    print(
        f"  Self FV MAE             : "
        f"{authoritative_row_truth['self_relative_FV_MAE']:.6e}"
    )

    print(
        "\nSG7B-6B"
    )

    print(
        f"  Saturation L1           : "
        f"{authoritative_row_6b['saturation_L1']:.6e}"
    )

    print(
        f"  Self FV MAE             : "
        f"{authoritative_row_6b['self_relative_FV_MAE']:.6e}"
    )

    print(
        f"  SG7A-scaled residual    : "
        f"{authoritative_row_6b['truth_scaled_residual_MAE']:.6e}"
    )

    print(
        f"  Absolute deltaR MAE     : "
        f"{authoritative_row_6b['residual_difference_MAE']:.6e}"
    )

    print(
        f"  SG7A-scaled deltaR      : "
        f"{authoritative_row_6b['truth_scaled_difference_MAE']:.6e}"
    )

    print(
        "\nSG7B-6D"
    )

    print(
        f"  Saturation L1           : "
        f"{authoritative_row_6d['saturation_L1']:.6e}"
    )

    print(
        f"  Self FV MAE             : "
        f"{authoritative_row_6d['self_relative_FV_MAE']:.6e}"
    )

    print(
        f"  SG7A-scaled residual    : "
        f"{authoritative_row_6d['truth_scaled_residual_MAE']:.6e}"
    )

    print(
        f"  Absolute deltaR MAE     : "
        f"{authoritative_row_6d['residual_difference_MAE']:.6e}"
    )

    print(
        f"  SG7A-scaled deltaR      : "
        f"{authoritative_row_6d['truth_scaled_difference_MAE']:.6e}"
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-6G DIAGNOSIS"
    )

    print(
        "=" * 78
    )

    print(
        f"Diagnosis:"
    )

    print(
        f"  {diagnosis['diagnosis']}"
    )

    print(
        "\nDiagnostic flags:"
    )

    print(
        f"  Self metric prefers 6B : "
        f"{diagnosis['self_metric_prefers_SG7B6B']}"
    )

    print(
        f"  Absolute deltaR -> 6D   : "
        f"{diagnosis['absolute_deltaR_prefers_SG7B6D']}"
    )

    print(
        f"  Scaled deltaR -> 6D     : "
        f"{diagnosis['truth_scaled_deltaR_prefers_SG7B6D']}"
    )

    print(
        f"  Ranking inversion       : "
        f"{diagnosis['metric_ranking_inversion']}"
    )

    print(
        f"  6D dt sensitivity factor: "
        f"{diagnosis['SG7B6D_dt_sensitivity_factor']:.3f}"
    )

    print(
        f"  Derivative sensitive    : "
        f"{diagnosis['temporal_derivative_sensitive']}"
    )

    print(
        "\nRecommendation:"
    )

    print(
        f"  {diagnosis['recommendation']}"
    )

    # =========================================================================
    # VALIDATION
    # =========================================================================

    checks = [
        (
            "SG7A canonical FV residual reproduced within 5%",
            canonical_pass,
        ),

        (
            "All SG7A residual metrics finite",
            np.all(
                np.isfinite(
                    authoritative_truth[
                        "relative"
                    ]
                )
            ),
        ),

        (
            "All SG7B-6B residual metrics finite",
            np.all(
                np.isfinite(
                    authoritative_6b[
                        "self_relative"
                    ]
                )
            ),
        ),

        (
            "All SG7B-6D residual metrics finite",
            np.all(
                np.isfinite(
                    authoritative_6d[
                        "self_relative"
                    ]
                )
            ),
        ),

        (
            "All dt sensitivity results finite",
            all(
                np.isfinite(
                    row[
                        "self_relative_FV_MAE"
                    ]
                )
                for row
                in all_rows
            ),
        ),
    ]

    validation_passed = all(
        status
        for _, status
        in checks
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-6G VALIDATION"
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

    # =========================================================================
    # SAVE DATA
    # =========================================================================

    save_csv(
        METRIC_TABLE_FILE,
        all_rows,
    )

    save_csv(
        DT_TABLE_FILE,
        all_rows,
    )

    save_csv(
        PROFILE_TABLE_FILE,
        profiles,
    )

    np.savez_compressed(
        DATABASE_FILE,

        xi=
            dataset[
                "xi"
            ],

        tD_test=
            dataset[
                "tD_test"
            ],

        SG7A_relative=
            authoritative_truth[
                "relative"
            ],

        SG7B6B_self_relative=
            authoritative_6b[
                "self_relative"
            ],

        SG7B6B_truth_scaled_residual=
            authoritative_6b[
                "truth_scaled_residual"
            ],

        SG7B6B_deltaR=
            authoritative_6b[
                "residual_difference"
            ],

        SG7B6B_truth_scaled_deltaR=
            authoritative_6b[
                "truth_scaled_difference"
            ],

        SG7B6D_self_relative=
            authoritative_6d[
                "self_relative"
            ],

        SG7B6D_truth_scaled_residual=
            authoritative_6d[
                "truth_scaled_residual"
            ],

        SG7B6D_deltaR=
            authoritative_6d[
                "residual_difference"
            ],

        SG7B6D_truth_scaled_deltaR=
            authoritative_6d[
                "truth_scaled_difference"
            ],
    )

    # =========================================================================
    # PLOTS
    # =========================================================================

    plot_metric_comparison(
        [
            authoritative_row_6b,
            authoritative_row_6d,
        ]
    )

    plot_dt_sensitivity(
        all_rows
    )

    plot_profile_metric_comparison(
        profiles
    )

    plot_residual_maps(
        dataset,
        authoritative_6b,
        authoritative_6d,
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7B-6G",

        "description":
            (
                "Residual metric and freeze-gate reconciliation "
                "with temporal-difference sensitivity audit"
            ),

        "training_performed":
            False,

        "freeze_gate_changed":
            False,

        "canonical_expected_SG7A_FV_MAE":
            EXPECTED_SG7A_FV_MAE,

        "canonical_recomputed_SG7A_FV_MAE":
            authoritative_row_truth[
                "self_relative_FV_MAE"
            ],

        "canonical_reproduction_relative_error":
            canonical_relative_error,

        "current_max_FV_ratio":
            CURRENT_MAX_FV_RATIO,

        "authoritative_dt_multiplier":
            1.0,

        "SG7B6B":
            authoritative_row_6b,

        "SG7B6D":
            authoritative_row_6d,

        "diagnosis":
            diagnosis,

        "validation_passed":
            bool(
                validation_passed
            ),

        "status":
            (
                "RESIDUAL_METRIC_RECONCILIATION_COMPLETE"
                if validation_passed
                else
                "RESIDUAL_METRIC_RECONCILIATION_INCOMPLETE"
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
        "\nTables:"
    )

    print(
        "  V15SG7B6G_Residual_Metrics.csv"
    )

    print(
        "  V15SG7B6G_dt_Sensitivity.csv"
    )

    print(
        "  V15SG7B6G_Profile_Metrics.csv"
    )

    print(
        "\nDatabase:"
    )

    print(
        "  V15SG7B6G_Residual_Reconciliation.npz"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B6G_Residual_Metric_Comparison.png"
    )

    print(
        "  V15SG7B6G_dt_Sensitivity.png"
    )

    print(
        "  V15SG7B6G_Residual_Metrics_vs_tD.png"
    )

    print(
        "  V15SG7B6G_SG7B6B_Scaled_DeltaR_Map.png"
    )

    print(
        "  V15SG7B6G_SG7B6D_Scaled_DeltaR_Map.png"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B6G_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    if validation_passed:

        print(
            "V15-SG7B-6G COMPLETED SUCCESSFULLY"
        )

        print()

        print(
            "STATUS: RESIDUAL METRICS RECONCILED"
        )

        print()

        print(
            "No freeze threshold has been changed."
        )

        print(
            "No PI-RNN has been frozen by this milestone."
        )

        print()

        print(
            "The next milestone will be selected from "
            "the SG7B-6G diagnostic result."
        )

    else:

        print(
            "V15-SG7B-6G INCOMPLETE"
        )

        print()

        print(
            "Do not continue PI-RNN refinement until the "
            "canonical residual metric comparison is reconciled."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()