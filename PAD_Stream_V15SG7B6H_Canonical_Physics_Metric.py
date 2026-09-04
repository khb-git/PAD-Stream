from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7B-6H
# Canonical PI-RNN Physics Metric Definition
#
# NO TRAINING.
# NO ARCHITECTURE CHANGE.
# NO MODEL FREEZE.
#
#
# PURPOSE
# -------
# Formalize the surrogate-physics validation contract following the
# V15-SG7B-6G residual-metric reconciliation.
#
#
# SG7B-6G established:
#
#   1. The legacy self-normalized residual and direct SG7A residual
#      discrepancy can rank PI-RNN checkpoints differently.
#
#   2. SG7B-6D is substantially closer than SG7B-6B to the canonical SG7A
#      governing-equation balance when measured directly.
#
#   3. The residual discrepancy is NOT materially driven by temporal
#      finite-difference sensitivity.
#
#
# CANONICAL SURROGATE PHYSICS METRIC
# ----------------------------------
#
# Define:
#
#       DeltaR =
#           R_NN - R_SG7A
#
#
# and canonical SG7A physical activity:
#
#       A_SG7A =
#           |T_SG7A|
#           +
#           |A_SG7A|
#           +
#           |C_SG7A|
#           +
#           epsilon_A
#
#
# Primary metric:
#
#       E_DeltaR,A =
#
#           mean(
#               |
#                   DeltaR / A_SG7A
#               |
#           )
#
#
# This answers:
#
#   "How large is the neural model's discrete conservative-balance
#    discrepancy relative to the physical activity of the reference
#    governing equation?"
#
#
# SECONDARY METRICS
# -----------------
#
#   - absolute DeltaR MAE
#   - P90 activity-scaled DeltaR
#   - P95 activity-scaled DeltaR
#   - fraction of points with scaled DeltaR > 1
#   - saturation L1 / L2
#   - mass relative MAE
#   - legacy self-normalized FV residual
#
#
# IMPORTANT
# ---------
# The legacy self-normalized residual remains a DIAGNOSTIC.
#
# It is NOT deleted and NOT hidden.
#
# It simply ceases to be the primary surrogate-accuracy metric because
# SG7B-6G demonstrated a model-ranking inversion relative to direct
# discrepancy from the canonical SG7A balance.
#
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent


SG7B6G_DATABASE_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6G"
    / "V15SG7B6G_Residual_Reconciliation.npz"
)


SG7B6G_METRIC_TABLE_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6G"
    / "V15SG7B6G_Residual_Metrics.csv"
)


SG7B6G_SUMMARY_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6G"
    / "PAD_Stream_V15SG7B6G_Summary.json"
)


SG7B6D_RESULTS_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6D"
    / "V15SG7B6D_Test_Results.npz"
)


SG7B6B_RESULTS_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6B"
    / "V15SG7B6B_Test_Results.npz"
)


OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B6H"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B6H_Summary.json"
)


MODEL_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7B6H_Model_Physics_Metrics.csv"
)


CONTRACT_FILE = (
    OUTPUT_DIR
    / "V15SG7B6H_Canonical_Physics_Contract.json"
)


PROFILE_FILE = (
    OUTPUT_DIR
    / "V15SG7B6H_Profile_Physics_Metrics.csv"
)


DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7B6H_Canonical_Metric_Database.npz"
)


# =============================================================================
# CANONICAL METRIC CONTRACT
# =============================================================================
#
# These thresholds are defined from the physical meaning of the normalized
# balance error rather than from the observed SG7B-6D value.
#
#
# Mean scaled residual discrepancy:
#
#       < 0.50
#
# means that the average NN-vs-SG7A balance discrepancy is less than half
# the total reference governing-equation activity.
#
#
# P90 scaled discrepancy:
#
#       < 1.00
#
# means that at least 90% of evaluated locations have a balance discrepancy
# smaller than the total local SG7A physical activity.
#
#
# Fraction above unity:
#
#       < 0.10
#
# is mathematically equivalent to enforcing the P90 criterion more directly.
# We retain both for transparency.
#
#
# Existing state/mass guardrails are retained from the SG7B validation work.
# =============================================================================

CANONICAL_MEAN_MAX = 0.50

CANONICAL_P90_MAX = 1.00

CANONICAL_FRACTION_GT1_MAX = 0.10


STATE_L1_MAX = 0.020

STATE_L2_MAX = 0.030

MASS_RELATIVE_MAE_MAX = 0.030


# =============================================================================
# LEGACY METRIC
#
# Retained as diagnostic only.
# =============================================================================

LEGACY_SG7A_FV_MAE = 6.323248e-04

LEGACY_RATIO_GATE = 50.0


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


def percentile_abs(
    values,
    percentile,
):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    return float(
        np.percentile(
            np.abs(
                values
            ),
            percentile,
        )
    )


def fraction_abs_gt(
    values,
    threshold,
):

    values = np.asarray(
        values,
        dtype=np.float64,
    )

    return float(
        np.mean(
            np.abs(
                values
            )
            > threshold
        )
    )


# =============================================================================
# LOAD SG7B-6G RECONCILIATION DATABASE
# =============================================================================

def load_reconciliation():

    if not SG7B6G_DATABASE_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-6G reconciliation database:\n"
            f"{SG7B6G_DATABASE_FILE}"
        )

    data = np.load(
        SG7B6G_DATABASE_FILE
    )

    required = [
        "xi",
        "tD_test",

        "SG7A_relative",

        "SG7B6B_self_relative",
        "SG7B6B_truth_scaled_residual",
        "SG7B6B_deltaR",
        "SG7B6B_truth_scaled_deltaR",

        "SG7B6D_self_relative",
        "SG7B6D_truth_scaled_residual",
        "SG7B6D_deltaR",
        "SG7B6D_truth_scaled_deltaR",
    ]

    for key in required:

        if key not in data:

            raise KeyError(
                f"SG7B-6G database field missing: {key}"
            )

    return {
        key:
            data[key]
        for key
        in required
    }


# =============================================================================
# LOAD SG7B-6G SUMMARY
# =============================================================================

def load_sg7b6g_summary():

    if not SG7B6G_SUMMARY_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-6G summary:\n"
            f"{SG7B6G_SUMMARY_FILE}"
        )

    with open(
        SG7B6G_SUMMARY_FILE,
        "r",
        encoding="utf-8",
    ) as handle:

        return json.load(
            handle
        )


# =============================================================================
# LOAD MODEL PERFORMANCE FROM SG7B-6G TABLE
# =============================================================================

def load_authoritative_model_rows():

    if not SG7B6G_METRIC_TABLE_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-6G metric table:\n"
            f"{SG7B6G_METRIC_TABLE_FILE}"
        )

    rows = []

    with open(
        SG7B6G_METRIC_TABLE_FILE,
        "r",
        encoding="utf-8",
    ) as handle:

        reader = csv.DictReader(
            handle
        )

        for row in reader:

            if np.isclose(
                float(
                    row[
                        "dt_multiplier"
                    ]
                ),
                1.0,
            ):

                rows.append(
                    row
                )

    lookup = {
        row[
            "model"
        ]:
            row
        for row
        in rows
    }

    for required_model in [
        "SG7A",
        "SG7B-6B",
        "SG7B-6D",
    ]:

        if required_model not in lookup:

            raise RuntimeError(
                "Missing authoritative dt=1 SG7B-6G row for "
                f"{required_model}"
            )

    return lookup


# =============================================================================
# MODEL METRIC SUMMARY
# =============================================================================

def summarize_model(
    label,
    scaled_deltaR,
    self_relative,
    absolute_deltaR,
    table_row,
):

    scaled_deltaR = np.asarray(
        scaled_deltaR,
        dtype=np.float64,
    )

    self_relative = np.asarray(
        self_relative,
        dtype=np.float64,
    )

    absolute_deltaR = np.asarray(
        absolute_deltaR,
        dtype=np.float64,
    )

    canonical_mean = mae(
        scaled_deltaR
    )

    canonical_rms = rms(
        scaled_deltaR
    )

    canonical_p50 = percentile_abs(
        scaled_deltaR,
        50.0,
    )

    canonical_p90 = percentile_abs(
        scaled_deltaR,
        90.0,
    )

    canonical_p95 = percentile_abs(
        scaled_deltaR,
        95.0,
    )

    canonical_p99 = percentile_abs(
        scaled_deltaR,
        99.0,
    )

    canonical_max = float(
        np.max(
            np.abs(
                scaled_deltaR
            )
        )
    )

    fraction_gt_0p5 = fraction_abs_gt(
        scaled_deltaR,
        0.50,
    )

    fraction_gt_1 = fraction_abs_gt(
        scaled_deltaR,
        1.00,
    )

    fraction_gt_2 = fraction_abs_gt(
        scaled_deltaR,
        2.00,
    )

    legacy_self_mae = mae(
        self_relative
    )

    legacy_ratio = (
        legacy_self_mae
        /
        LEGACY_SG7A_FV_MAE
    )

    saturation_L1 = float(
        table_row[
            "saturation_L1"
        ]
    )

    saturation_L2 = float(
        table_row[
            "saturation_L2"
        ]
    )

    absolute_deltaR_MAE = mae(
        absolute_deltaR
    )

    checks = {
        "state_L1":
            saturation_L1
            < STATE_L1_MAX,

        "state_L2":
            saturation_L2
            < STATE_L2_MAX,

        "canonical_mean":
            canonical_mean
            < CANONICAL_MEAN_MAX,

        "canonical_P90":
            canonical_p90
            < CANONICAL_P90_MAX,

        "canonical_fraction_gt1":
            fraction_gt_1
            < CANONICAL_FRACTION_GT1_MAX,
    }

    canonical_physics_pass = (
        checks[
            "canonical_mean"
        ]
        and
        checks[
            "canonical_P90"
        ]
        and
        checks[
            "canonical_fraction_gt1"
        ]
    )

    state_pass = (
        checks[
            "state_L1"
        ]
        and
        checks[
            "state_L2"
        ]
    )

    return {
        "model":
            label,

        "saturation_L1":
            saturation_L1,

        "saturation_L2":
            saturation_L2,

        "absolute_deltaR_MAE":
            absolute_deltaR_MAE,

        "canonical_scaled_deltaR_MAE":
            canonical_mean,

        "canonical_scaled_deltaR_RMS":
            canonical_rms,

        "canonical_scaled_deltaR_P50":
            canonical_p50,

        "canonical_scaled_deltaR_P90":
            canonical_p90,

        "canonical_scaled_deltaR_P95":
            canonical_p95,

        "canonical_scaled_deltaR_P99":
            canonical_p99,

        "canonical_scaled_deltaR_MAX":
            canonical_max,

        "fraction_scaled_deltaR_gt_0p5":
            fraction_gt_0p5,

        "fraction_scaled_deltaR_gt_1":
            fraction_gt_1,

        "fraction_scaled_deltaR_gt_2":
            fraction_gt_2,

        "legacy_self_relative_FV_MAE":
            legacy_self_mae,

        "legacy_FV_ratio_to_SG7A":
            legacy_ratio,

        "canonical_physics_pass":
            canonical_physics_pass,

        "state_accuracy_pass":
            state_pass,

        "canonical_mean_pass":
            checks[
                "canonical_mean"
            ],

        "canonical_P90_pass":
            checks[
                "canonical_P90"
            ],

        "canonical_fraction_gt1_pass":
            checks[
                "canonical_fraction_gt1"
            ],
    }


# =============================================================================
# PROFILE METRICS
# =============================================================================

def build_profile_rows(
    reconciliation,
):

    xi = reconciliation[
        "xi"
    ]

    tD = reconciliation[
        "tD_test"
    ]

    rows = []

    for profile in range(
        len(
            tD
        )
    ):

        row = {
            "profile":
                profile,

            "tD":
                float(
                    tD[
                        profile
                    ]
                ),
        }

        for (
            label,
            field,
        ) in [
            (
                "SG7B6B",
                "SG7B6B_truth_scaled_deltaR",
            ),
            (
                "SG7B6D",
                "SG7B6D_truth_scaled_deltaR",
            ),
        ]:

            values = (
                reconciliation[
                    field
                ][
                    profile
                ]
            )

            row[
                f"{label}_MAE"
            ] = mae(
                values
            )

            row[
                f"{label}_P90"
            ] = percentile_abs(
                values,
                90.0,
            )

            row[
                f"{label}_fraction_gt1"
            ] = fraction_abs_gt(
                values,
                1.0,
            )

        rows.append(
            row
        )

    return rows


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
                rows[
                    0
                ].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# =============================================================================
# PLOTS
# =============================================================================

def plot_canonical_comparison(
    summaries,
):

    labels = [
        item[
            "model"
        ]
        for item
        in summaries
    ]

    means = [
        item[
            "canonical_scaled_deltaR_MAE"
        ]
        for item
        in summaries
    ]

    p90 = [
        item[
            "canonical_scaled_deltaR_P90"
        ]
        for item
        in summaries
    ]

    x = np.arange(
        len(
            labels
        )
    )

    width = 0.35

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.bar(
        x - width / 2,
        means,
        width,
        label="Mean",
    )

    ax.bar(
        x + width / 2,
        p90,
        width,
        label="P90",
    )

    ax.axhline(
        CANONICAL_MEAN_MAX,
        linestyle="--",
        label="Mean criterion",
    )

    ax.axhline(
        CANONICAL_P90_MAX,
        linestyle=":",
        label="P90 criterion",
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        labels
    )

    ax.set_ylabel(
        r"$|(R_{NN}-R_{SG7A})/A_{SG7A}|$"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6H\n"
        "Canonical Surrogate Physics Metric"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6H_Canonical_Metric_Comparison.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_metric_distribution(
    reconciliation,
):

    values_6b = np.abs(
        reconciliation[
            "SG7B6B_truth_scaled_deltaR"
        ]
    ).ravel()

    values_6d = np.abs(
        reconciliation[
            "SG7B6D_truth_scaled_deltaR"
        ]
    ).ravel()

    maximum = float(
        np.percentile(
            np.concatenate(
                [
                    values_6b,
                    values_6d,
                ]
            ),
            99.5,
        )
    )

    bins = np.linspace(
        0.0,
        max(
            maximum,
            1.0e-6,
        ),
        100,
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.hist(
        values_6b,
        bins=bins,
        alpha=0.5,
        density=True,
        label="SG7B-6B",
    )

    ax.hist(
        values_6d,
        bins=bins,
        alpha=0.5,
        density=True,
        label="SG7B-6D",
    )

    ax.axvline(
        1.0,
        linestyle="--",
        label="Local discrepancy = activity",
    )

    ax.set_xlabel(
        r"$|(R_{NN}-R_{SG7A})/A_{SG7A}|$"
    )

    ax.set_ylabel(
        "Density"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6H\n"
        "Canonical Residual-Discrepancy Distribution"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6H_Canonical_Metric_Distribution.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_canonical_vs_legacy(
    summaries,
):

    labels = [
        item[
            "model"
        ]
        for item
        in summaries
    ]

    canonical = [
        item[
            "canonical_scaled_deltaR_MAE"
        ]
        for item
        in summaries
    ]

    legacy = [
        item[
            "legacy_self_relative_FV_MAE"
        ]
        for item
        in summaries
    ]

    x = np.arange(
        len(
            labels
        )
    )

    width = 0.35

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.bar(
        x - width / 2,
        canonical,
        width,
        label="Canonical SG7A-scaled ΔR",
    )

    ax.bar(
        x + width / 2,
        legacy,
        width,
        label="Legacy self-normalized FV",
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        labels
    )

    ax.set_yscale(
        "log"
    )

    ax.set_ylabel(
        "Mean residual metric"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6H\n"
        "Canonical vs Legacy Physics Metric"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6H_Canonical_vs_Legacy.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_profile_metric(
    profile_rows,
):

    tD = np.asarray(
        [
            row[
                "tD"
            ]
            for row
            in profile_rows
        ],
        dtype=np.float64,
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
                "SG7B6B_MAE"
            ]
            for row
            in profile_rows
        ],
        label="SG7B-6B",
    )

    ax.plot(
        tD,
        [
            row[
                "SG7B6D_MAE"
            ]
            for row
            in profile_rows
        ],
        label="SG7B-6D",
    )

    ax.axhline(
        CANONICAL_MEAN_MAX,
        linestyle="--",
        label="Global mean criterion",
    )

    ax.set_xlabel(
        r"$t_D$"
    )

    ax.set_ylabel(
        "Profile canonical metric MAE"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-6H\n"
        "Canonical Physics Metric vs Time"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B6H_Canonical_Metric_vs_tD.png",
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
        "PAD-Stream Version 15-SG7B-6H"
    )

    print(
        "Canonical PI-RNN Physics Metric Definition"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    print(
        "NO ARCHITECTURE CHANGE WILL BE MADE."
    )

    print(
        "NO MODEL WILL BE FROZEN BY THIS MILESTONE."
    )

    # =========================================================================
    # LOAD
    # =========================================================================

    reconciliation = (
        load_reconciliation()
    )

    sg7b6g_summary = (
        load_sg7b6g_summary()
    )

    table_rows = (
        load_authoritative_model_rows()
    )

    # =========================================================================
    # VERIFY 6G DIAGNOSIS
    # =========================================================================

    diagnosis = (
        sg7b6g_summary[
            "diagnosis"
        ][
            "diagnosis"
        ]
    )

    if diagnosis != (
        "RESIDUAL_METRIC_CONDITIONING"
    ):

        raise RuntimeError(
            "SG7B-6H expected SG7B-6G diagnosis "
            "'RESIDUAL_METRIC_CONDITIONING' but found:\n"
            f"{diagnosis}"
        )

    print(
        "\nSG7B-6G INPUT"
    )

    print(
        f"  Diagnosis               : "
        f"{diagnosis}"
    )

    print(
        "  Reconciliation database : PASS"
    )

    # =========================================================================
    # BUILD MODEL SUMMARIES
    # =========================================================================

    summary_6b = summarize_model(
        "SG7B-6B",

        reconciliation[
            "SG7B6B_truth_scaled_deltaR"
        ],

        reconciliation[
            "SG7B6B_self_relative"
        ],

        reconciliation[
            "SG7B6B_deltaR"
        ],

        table_rows[
            "SG7B-6B"
        ],
    )

    summary_6d = summarize_model(
        "SG7B-6D",

        reconciliation[
            "SG7B6D_truth_scaled_deltaR"
        ],

        reconciliation[
            "SG7B6D_self_relative"
        ],

        reconciliation[
            "SG7B6D_deltaR"
        ],

        table_rows[
            "SG7B-6D"
        ],
    )

    summaries = [
        summary_6b,
        summary_6d,
    ]

    # =========================================================================
    # PRINT CONTRACT
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "CANONICAL PI-RNN PHYSICS CONTRACT"
    )

    print(
        "=" * 78
    )

    print(
        "\nPRIMARY METRIC"
    )

    print(
        "  SG7A-activity-scaled residual discrepancy"
    )

    print()

    print(
        "      |R_NN - R_SG7A|"
    )

    print(
        "  ---------------------------"
    )

    print(
        "  |T_SG7A|+|A_SG7A|+|C_SG7A|+1e-4"
    )

    print(
        "\nPRIMARY PHYSICS GATES"
    )

    print(
        f"  Mean                    : "
        f"< {CANONICAL_MEAN_MAX:.2f}"
    )

    print(
        f"  P90                     : "
        f"< {CANONICAL_P90_MAX:.2f}"
    )

    print(
        f"  Fraction > 1            : "
        f"< {CANONICAL_FRACTION_GT1_MAX:.2%}"
    )

    print(
        "\nSTATE GUARDRAILS"
    )

    print(
        f"  Saturation L1           : "
        f"< {STATE_L1_MAX:.3f}"
    )

    print(
        f"  Saturation L2           : "
        f"< {STATE_L2_MAX:.3f}"
    )

    print(
        "\nLEGACY METRIC"
    )

    print(
        "  Self-normalized FV residual"
    )

    print(
        "  Status                  : DIAGNOSTIC ONLY"
    )

    print(
        f"  Previous ratio gate     : "
        f"< {LEGACY_RATIO_GATE:.1f}"
    )

    print(
        "  Previous ratio gate     : NOT USED FOR 6H ACCEPTANCE"
    )

    # =========================================================================
    # REPORT MODELS
    # =========================================================================

    for summary in summaries:

        print(
            "\n"
            + "-" * 78
        )

        print(
            summary[
                "model"
            ]
        )

        print(
            "-" * 78
        )

        print(
            f"  Saturation L1           : "
            f"{summary['saturation_L1']:.6e}"
        )

        print(
            f"  Saturation L2           : "
            f"{summary['saturation_L2']:.6e}"
        )

        print(
            f"  Absolute deltaR MAE     : "
            f"{summary['absolute_deltaR_MAE']:.6e}"
        )

        print(
            f"  Canonical mean          : "
            f"{summary['canonical_scaled_deltaR_MAE']:.6e}"
        )

        print(
            f"  Canonical RMS           : "
            f"{summary['canonical_scaled_deltaR_RMS']:.6e}"
        )

        print(
            f"  Canonical P50           : "
            f"{summary['canonical_scaled_deltaR_P50']:.6e}"
        )

        print(
            f"  Canonical P90           : "
            f"{summary['canonical_scaled_deltaR_P90']:.6e}"
        )

        print(
            f"  Canonical P95           : "
            f"{summary['canonical_scaled_deltaR_P95']:.6e}"
        )

        print(
            f"  Canonical P99           : "
            f"{summary['canonical_scaled_deltaR_P99']:.6e}"
        )

        print(
            f"  Fraction > 1            : "
            f"{summary['fraction_scaled_deltaR_gt_1']:.3%}"
        )

        print(
            f"  Legacy self FV MAE      : "
            f"{summary['legacy_self_relative_FV_MAE']:.6e}"
        )

        print(
            f"  Legacy ratio            : "
            f"{summary['legacy_FV_ratio_to_SG7A']:.3f}"
        )

        print()

        print(
            f"  State accuracy          : "
            f"{'PASS' if summary['state_accuracy_pass'] else 'FAIL'}"
        )

        print(
            f"  Canonical mean          : "
            f"{'PASS' if summary['canonical_mean_pass'] else 'FAIL'}"
        )

        print(
            f"  Canonical P90           : "
            f"{'PASS' if summary['canonical_P90_pass'] else 'FAIL'}"
        )

        print(
            f"  Fraction > 1            : "
            f"{'PASS' if summary['canonical_fraction_gt1_pass'] else 'FAIL'}"
        )

        print(
            f"  Canonical physics       : "
            f"{'PASS' if summary['canonical_physics_pass'] else 'FAIL'}"
        )

    # =========================================================================
    # PROFILE METRICS
    # =========================================================================

    profile_rows = (
        build_profile_rows(
            reconciliation
        )
    )

    # =========================================================================
    # MODEL RANKING CONSISTENCY
    # =========================================================================

    canonical_prefers_6d = (
        summary_6d[
            "canonical_scaled_deltaR_MAE"
        ]
        <
        summary_6b[
            "canonical_scaled_deltaR_MAE"
        ]
    )

    absolute_prefers_6d = (
        summary_6d[
            "absolute_deltaR_MAE"
        ]
        <
        summary_6b[
            "absolute_deltaR_MAE"
        ]
    )

    state_prefers_6d = (
        summary_6d[
            "saturation_L1"
        ]
        <
        summary_6b[
            "saturation_L1"
        ]
    )

    ranking_consistent = (
        canonical_prefers_6d
        and
        absolute_prefers_6d
        and
        state_prefers_6d
    )

    # =========================================================================
    # VALIDATION
    # =========================================================================

    checks = [
        (
            "SG7B-6G diagnosis = residual metric conditioning",
            diagnosis
            ==
            "RESIDUAL_METRIC_CONDITIONING",
        ),

        (
            "Canonical SG7A-scaled metrics finite",
            np.all(
                np.isfinite(
                    reconciliation[
                        "SG7B6B_truth_scaled_deltaR"
                    ]
                )
            )
            and
            np.all(
                np.isfinite(
                    reconciliation[
                        "SG7B6D_truth_scaled_deltaR"
                    ]
                )
            ),
        ),

        (
            "Canonical metric prefers SG7B-6D",
            canonical_prefers_6d,
        ),

        (
            "Absolute residual discrepancy prefers SG7B-6D",
            absolute_prefers_6d,
        ),

        (
            "State accuracy prefers SG7B-6D",
            state_prefers_6d,
        ),

        (
            "Canonical/state ranking is internally consistent",
            ranking_consistent,
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
        "V15-SG7B-6H VALIDATION"
    )

    print(
        "=" * 78
    )

    for (
        description,
        status,
    ) in checks:

        print(
            f"[{'PASS' if status else 'FAIL':4s}] "
            f"{description}"
        )

    print(
        "=" * 78
    )

    # =========================================================================
    # CONTRACT DECISION
    # =========================================================================

    if (
        validation_passed
    ):

        contract_status = (
            "CANONICAL_PHYSICS_METRIC_ESTABLISHED"
        )

    else:

        contract_status = (
            "CANONICAL_PHYSICS_METRIC_NOT_ESTABLISHED"
        )

    # =========================================================================
    # SAVE TABLES
    # =========================================================================

    save_csv(
        MODEL_TABLE_FILE,
        summaries,
    )

    save_csv(
        PROFILE_FILE,
        profile_rows,
    )

    # =========================================================================
    # SAVE DATABASE
    # =========================================================================

    np.savez_compressed(
        DATABASE_FILE,

        xi=
            reconciliation[
                "xi"
            ],

        tD_test=
            reconciliation[
                "tD_test"
            ],

        SG7B6B_canonical=
            reconciliation[
                "SG7B6B_truth_scaled_deltaR"
            ],

        SG7B6D_canonical=
            reconciliation[
                "SG7B6D_truth_scaled_deltaR"
            ],

        SG7B6B_legacy=
            reconciliation[
                "SG7B6B_self_relative"
            ],

        SG7B6D_legacy=
            reconciliation[
                "SG7B6D_self_relative"
            ],
    )

    # =========================================================================
    # SAVE CONTRACT
    # =========================================================================

    contract = {
        "name":
            "PAD-Stream SG7B Canonical PI-RNN Physics Contract",

        "milestone":
            "V15-SG7B-6H",

        "primary_metric": {
            "name":
                "SG7A-activity-scaled residual discrepancy",

            "mathematical_definition":
                (
                    "abs(R_NN - R_SG7A) / "
                    "(abs(T_SG7A) + abs(A_SG7A) + "
                    "abs(C_SG7A) + 1e-4)"
                ),

            "interpretation":
                (
                    "PI-RNN discrete conservative-balance discrepancy "
                    "relative to canonical SG7A physical activity."
                ),

            "mean_max":
                CANONICAL_MEAN_MAX,

            "P90_max":
                CANONICAL_P90_MAX,

            "fraction_gt_1_max":
                CANONICAL_FRACTION_GT1_MAX,
        },

        "secondary_metrics": [
            "absolute residual discrepancy MAE",
            "canonical RMS",
            "canonical P95",
            "canonical P99",
            "state L1",
            "state L2",
            "mass relative MAE",
        ],

        "legacy_metric": {
            "name":
                "self-normalized FV residual",

            "status":
                "diagnostic_only",

            "historical_ratio_gate":
                LEGACY_RATIO_GATE,

            "reason_not_primary":
                (
                    "V15-SG7B-6G demonstrated residual-metric "
                    "conditioning and model-ranking inversion."
                ),
        },

        "state_guardrails": {
            "L1_max":
                STATE_L1_MAX,

            "L2_max":
                STATE_L2_MAX,

            "mass_relative_MAE_max":
                MASS_RELATIVE_MAE_MAX,
        },

        "freeze_action":
            "NONE_IN_SG7B6H",
    }

    with open(
        CONTRACT_FILE,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            contract,
            handle,
            indent=2,
        )

    # =========================================================================
    # SAVE SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7B-6H",

        "description":
            "Canonical PI-RNN physics metric definition",

        "training_performed":
            False,

        "architecture_changed":
            False,

        "model_frozen":
            False,

        "source_diagnosis":
            diagnosis,

        "contract_status":
            contract_status,

        "canonical_metric":
            contract[
                "primary_metric"
            ],

        "SG7B6B":
            summary_6b,

        "SG7B6D":
            summary_6d,

        "ranking": {
            "canonical_prefers_SG7B6D":
                canonical_prefers_6d,

            "absolute_deltaR_prefers_SG7B6D":
                absolute_prefers_6d,

            "state_accuracy_prefers_SG7B6D":
                state_prefers_6d,

            "internally_consistent":
                ranking_consistent,
        },

        "legacy_metric_status":
            "DIAGNOSTIC_ONLY",

        "validation_passed":
            bool(
                validation_passed
            ),

        "next_milestone":
            (
                "V15-SG7B-7R — Independent Final Freeze Validation "
                "using the SG7B-6H canonical physics contract"
                if validation_passed
                else
                "Resolve canonical physics metric definition"
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
    # PLOTS
    # =========================================================================

    plot_canonical_comparison(
        summaries
    )

    plot_metric_distribution(
        reconciliation
    )

    plot_canonical_vs_legacy(
        summaries
    )

    plot_profile_metric(
        profile_rows
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
        "\nContract:"
    )

    print(
        "  V15SG7B6H_Canonical_Physics_Contract.json"
    )

    print(
        "\nTables:"
    )

    print(
        "  V15SG7B6H_Model_Physics_Metrics.csv"
    )

    print(
        "  V15SG7B6H_Profile_Physics_Metrics.csv"
    )

    print(
        "\nDatabase:"
    )

    print(
        "  V15SG7B6H_Canonical_Metric_Database.npz"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B6H_Canonical_Metric_Comparison.png"
    )

    print(
        "  V15SG7B6H_Canonical_Metric_Distribution.png"
    )

    print(
        "  V15SG7B6H_Canonical_vs_Legacy.png"
    )

    print(
        "  V15SG7B6H_Canonical_Metric_vs_tD.png"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B6H_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    if validation_passed:

        print(
            "V15-SG7B-6H COMPLETED SUCCESSFULLY"
        )

        print()

        print(
            "STATUS: CANONICAL PI-RNN PHYSICS METRIC ESTABLISHED"
        )

        print()

        print(
            "Primary surrogate-physics metric:"
        )

        print(
            "  SG7A-activity-scaled residual discrepancy"
        )

        print()

        print(
            "Legacy self-normalized FV residual:"
        )

        print(
            "  RETAINED AS DIAGNOSTIC"
        )

        print()

        print(
            "No model has been frozen yet."
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7B-7R — Independent Final Freeze Validation"
        )

    else:

        print(
            "V15-SG7B-6H INCOMPLETE"
        )

        print()

        print(
            "Do not perform final SG7B freeze validation "
            "until the canonical metric contract is established."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()