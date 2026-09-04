from pathlib import Path
import csv
import hashlib
import json
import shutil

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf

# Reuse the reconciled canonical operators.
import PAD_Stream_V15SG7B6FR_Activity_Scaled_Coupled_Refinement as sg6fr


# =============================================================================
# PAD-Stream V15-SG7B-7R
# Independent Final PI-RNN Freeze Validation
#
# NO TRAINING.
# NO ARCHITECTURE CHANGE.
# NO THRESHOLD TUNING.
#
#
# PURPOSE
# -------
# Independently validate the selected SG7B-6D PI-RNN checkpoint against:
#
#   1. Frozen SG7A full-physics truth
#   2. Canonical SG7B-6H physics metric contract
#   3. State-accuracy guardrails
#   4. Mass/storage consistency
#   5. Saturation physical bounds
#   6. Injector/front/interior/outlet behavior
#   7. Early/middle/late-time behavior
#   8. Model serialization/load integrity
#
#
# FINAL FREEZE CANDIDATE
# ----------------------
#
#       V15SG7B6D_Best_Model.keras
#
#
# CANONICAL PHYSICS METRIC
# ------------------------
#
#       DeltaR =
#           R_NN - R_SG7A
#
#
#       A_SG7A =
#           |T_SG7A|
#           +
#           |A_SG7A|
#           +
#           |C_SG7A|
#           +
#           1e-4
#
#
#       E_canonical =
#
#           |
#               DeltaR / A_SG7A
#           |
#
#
# The acceptance thresholds are read from the FROZEN SG7B-6H contract.
#
#
# LEGACY METRIC
# -------------
#
# Self-normalized FV residual remains visible as a diagnostic only.
#
# It is NOT used as a final freeze gate because SG7B-6G demonstrated
# residual-metric conditioning and model-ranking inversion.
#
#
# IF ALL FREEZE GATES PASS
# ------------------------
#
# A byte-identical copy of the accepted model is written as:
#
#       V15SG7B_FROZEN_Model.keras
#
# together with a SHA-256 checksum and freeze manifest.
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


CANDIDATE_MODEL_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6D"
    / "V15SG7B6D_Best_Model.keras"
)


CANONICAL_CONTRACT_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6H"
    / "V15SG7B6H_Canonical_Physics_Contract.json"
)


SG7B6H_SUMMARY_FILE = (
    ROOT
    / "output"
    / "V15_SG7B6H"
    / "PAD_Stream_V15SG7B6H_Summary.json"
)


OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B7R"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


FROZEN_MODEL_FILE = (
    OUTPUT_DIR
    / "V15SG7B_FROZEN_Model.keras"
)


FREEZE_MANIFEST_FILE = (
    OUTPUT_DIR
    / "V15SG7B_Freeze_Manifest.json"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B7R_Summary.json"
)


PROFILE_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7B7R_Profile_Metrics.csv"
)


REGIONAL_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7B7R_Regional_Metrics.csv"
)


NUMERICAL_FILE = (
    OUTPUT_DIR
    / "V15SG7B7R_Final_Validation.npz"
)


# =============================================================================
# FIXED PHYSICAL CONTRACT
# =============================================================================

SWC = sg6fr.SWC
SOR = sg6fr.SOR

S_MIN = SWC
S_MAX = 1.0 - SOR

ACTIVITY_FLOOR = 1.0e-4

EPS = 1.0e-12


# =============================================================================
# RETAINED HISTORICAL REGIONAL/TIME GUARDRAILS
#
# These are NOT invented from SG7B-6D results.
# They are retained from the earlier SG7B validation branch.
# =============================================================================

INJECTOR_L1_MAX = 0.015

FRONT_L1_MAX = 0.030

EARLY_L1_MAX = 0.020

LATE_L1_MAX = 0.025


# =============================================================================
# REGIONAL DEFINITIONS
#
# These are used consistently for the final independent validation.
# =============================================================================

INJECTOR_XI_MAX = 0.10

OUTLET_XI_MIN = 0.90

FRONT_GRADIENT_PERCENTILE = 80.0


# =============================================================================
# LOADERS
# =============================================================================

def load_dataset():

    if not DATASET_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-3 dataset:\n"
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
        key:
            data[key]
        for key in required
    }


def load_sg7a():

    if not SG7A_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7A database:\n"
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
        key:
            data[key]
        for key in required
    }


def load_contract():

    if not CANONICAL_CONTRACT_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-6H canonical contract:\n"
            f"{CANONICAL_CONTRACT_FILE}"
        )

    with open(
        CANONICAL_CONTRACT_FILE,
        "r",
        encoding="utf-8",
    ) as handle:

        contract = json.load(
            handle
        )

    required = [
        "primary_metric",
        "state_guardrails",
        "legacy_metric",
    ]

    for key in required:

        if key not in contract:

            raise KeyError(
                f"Canonical contract field missing: {key}"
            )

    return contract


def verify_6h_summary():

    if not SG7B6H_SUMMARY_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-6H summary:\n"
            f"{SG7B6H_SUMMARY_FILE}"
        )

    with open(
        SG7B6H_SUMMARY_FILE,
        "r",
        encoding="utf-8",
    ) as handle:

        summary = json.load(
            handle
        )

    if (
        summary.get(
            "contract_status"
        )
        !=
        "CANONICAL_PHYSICS_METRIC_ESTABLISHED"
    ):

        raise RuntimeError(
            "SG7B-6H canonical physics contract "
            "was not established successfully."
        )

    return summary


# =============================================================================
# HELPERS
# =============================================================================

def mae(
    values,
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
        )
    )


def rms(
    values,
):

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

    return float(
        np.percentile(
            np.abs(
                np.asarray(
                    values,
                    dtype=np.float64,
                )
            ),
            percentile,
        )
    )


def fraction_abs_gt(
    values,
    threshold,
):

    return float(
        np.mean(
            np.abs(
                np.asarray(
                    values,
                    dtype=np.float64,
                )
            )
            > threshold
        )
    )


def sha256_file(
    path,
):

    digest = hashlib.sha256()

    with open(
        path,
        "rb",
    ) as handle:

        while True:

            block = handle.read(
                1024 * 1024
            )

            if not block:

                break

            digest.update(
                block
            )

    return digest.hexdigest()


# =============================================================================
# BUILD CANONICAL SG7A TEST DATABASE
# =============================================================================

def build_truth_database(
    dataset,
    sg7a,
):

    indices = np.asarray(
        dataset[
            "index_test"
        ],
        dtype=int,
    )

    xi = np.asarray(
        dataset[
            "xi"
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

    truth = (
        master_S[
            indices
        ]
    )

    n_profiles = len(
        indices
    )

    temporal = np.zeros_like(
        truth,
        dtype=np.float64,
    )

    adv = np.zeros_like(
        truth,
        dtype=np.float64,
    )

    cap = np.zeros_like(
        truth,
        dtype=np.float64,
    )

    for p, index in enumerate(
        indices
    ):

        temporal[p] = (
            sg6fr.temporal_derivative_np(
                master_tD,
                master_S,
                int(
                    index
                ),
            )
        )

        (
            adv[p],
            cap[p],
        ) = (
            sg6fr.canonical_spatial_components_np(
                truth[p],
                xi,
            )
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

    self_relative = (
        residual
        /
        activity
    )

    return {
        "S":
            truth,

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

        "self_relative":
            self_relative,
    }


# =============================================================================
# BUILD PI-RNN TEST DATABASE
# =============================================================================

def build_model_database(
    model,
    dataset,
    truth,
):

    X = (
        dataset[
            "X_test"
        ].astype(
            np.float32
        )
    )

    tD_scale = float(
        dataset[
            "tD_scale"
        ][0]
    )

    (
        S_tf,
        temporal_tf,
        adv_tf,
        cap_tf,
        residual_tf,
        self_relative_tf,
    ) = (
        sg6fr.model_components_tf(
            model,
            tf.constant(
                X
            ),
            tf.constant(
                tD_scale,
                dtype=tf.float32,
            ),
            training=False,
        )
    )

    S = (
        S_tf.numpy()
        .astype(
            np.float64
        )
    )

    temporal = (
        temporal_tf.numpy()
        .astype(
            np.float64
        )
    )

    adv = (
        adv_tf.numpy()
        .astype(
            np.float64
        )
    )

    cap = (
        cap_tf.numpy()
        .astype(
            np.float64
        )
    )

    residual = (
        residual_tf.numpy()
        .astype(
            np.float64
        )
    )

    self_relative = (
        self_relative_tf.numpy()
        .astype(
            np.float64
        )
    )

    deltaR = (
        residual
        -
        truth[
            "residual"
        ]
    )

    canonical = (
        deltaR
        /
        truth[
            "activity"
        ]
    )

    return {
        "S":
            S,

        "temporal":
            temporal,

        "adv":
            adv,

        "cap":
            cap,

        "residual":
            residual,

        "self_relative":
            self_relative,

        "deltaR":
            deltaR,

        "canonical":
            canonical,
    }


# =============================================================================
# STATE / MASS METRICS
# =============================================================================

def state_metrics(
    truth,
    prediction,
    xi,
):

    error = (
        prediction
        -
        truth
    )

    L1 = mae(
        error
    )

    L2 = rms(
        error
    )

    Linf = float(
        np.max(
            np.abs(
                error
            )
        )
    )

    true_mass = np.trapezoid(
        truth,
        xi,
        axis=1,
    )

    predicted_mass = np.trapezoid(
        prediction,
        xi,
        axis=1,
    )

    relative_mass = (
        np.abs(
            predicted_mass
            -
            true_mass
        )
        /
        (
            np.abs(
                true_mass
            )
            +
            EPS
        )
    )

    return {
        "error":
            error,

        "L1":
            L1,

        "L2":
            L2,

        "Linf":
            Linf,

        "true_mass":
            true_mass,

        "predicted_mass":
            predicted_mass,

        "mass_relative_error":
            relative_mass,

        "mass_relative_MAE":
            float(
                np.mean(
                    relative_mass
                )
            ),

        "mass_relative_MAX":
            float(
                np.max(
                    relative_mass
                )
            ),
    }


# =============================================================================
# REGIONAL METRICS
# =============================================================================

def build_regional_metrics(
    truth,
    prediction,
    xi,
):

    error = np.abs(
        prediction
        -
        truth
    )

    injector_mask_1d = (
        xi
        <=
        INJECTOR_XI_MAX
    )

    outlet_mask_1d = (
        xi
        >=
        OUTLET_XI_MIN
    )

    gradient = np.abs(
        np.gradient(
            truth,
            xi,
            axis=1,
        )
    )

    front_threshold = np.percentile(
        gradient,
        FRONT_GRADIENT_PERCENTILE,
        axis=1,
        keepdims=True,
    )

    front_mask = (
        gradient
        >=
        front_threshold
    )

    injector_mask = np.broadcast_to(
        injector_mask_1d[
            None,
            :
        ],
        truth.shape,
    )

    outlet_mask = np.broadcast_to(
        outlet_mask_1d[
            None,
            :
        ],
        truth.shape,
    )

    interior_mask = (
        ~injector_mask
        &
        ~outlet_mask
        &
        ~front_mask
    )

    def masked_mae(
        mask,
    ):

        if not np.any(
            mask
        ):

            return np.nan

        return float(
            np.mean(
                error[
                    mask
                ]
            )
        )

    return {
        "injector_L1":
            masked_mae(
                injector_mask
            ),

        "front_L1":
            masked_mae(
                front_mask
            ),

        "interior_L1":
            masked_mae(
                interior_mask
            ),

        "outlet_L1":
            masked_mae(
                outlet_mask
            ),

        "front_fraction":
            float(
                np.mean(
                    front_mask
                )
            ),
    }


# =============================================================================
# TIME-BAND METRICS
# =============================================================================

def build_time_metrics(
    truth,
    prediction,
    tD,
):

    profile_L1 = np.mean(
        np.abs(
            prediction
            -
            truth
        ),
        axis=1,
    )

    q1, q2 = np.quantile(
        tD,
        [
            1.0 / 3.0,
            2.0 / 3.0,
        ],
    )

    early = (
        tD
        <=
        q1
    )

    middle = (
        (tD > q1)
        &
        (tD <= q2)
    )

    late = (
        tD
        >
        q2
    )

    return {
        "profile_L1":
            profile_L1,

        "early_L1":
            float(
                np.mean(
                    profile_L1[
                        early
                    ]
                )
            ),

        "middle_L1":
            float(
                np.mean(
                    profile_L1[
                        middle
                    ]
                )
            ),

        "late_L1":
            float(
                np.mean(
                    profile_L1[
                        late
                    ]
                )
            ),

        "early_max_tD":
            float(
                q1
            ),

        "middle_max_tD":
            float(
                q2
            ),
    }


# =============================================================================
# CANONICAL PHYSICS METRICS
# =============================================================================

def canonical_metrics(
    canonical,
):

    return {
        "mean":
            mae(
                canonical
            ),

        "RMS":
            rms(
                canonical
            ),

        "P50":
            percentile_abs(
                canonical,
                50.0,
            ),

        "P90":
            percentile_abs(
                canonical,
                90.0,
            ),

        "P95":
            percentile_abs(
                canonical,
                95.0,
            ),

        "P99":
            percentile_abs(
                canonical,
                99.0,
            ),

        "MAX":
            float(
                np.max(
                    np.abs(
                        canonical
                    )
                )
            ),

        "fraction_gt_1":
            fraction_abs_gt(
                canonical,
                1.0,
            ),

        "fraction_gt_2":
            fraction_abs_gt(
                canonical,
                2.0,
            ),
    }


# =============================================================================
# PROFILE TABLE
# =============================================================================

def build_profile_rows(
    dataset,
    state,
    model_db,
    truth_db,
):

    tD = np.asarray(
        dataset[
            "tD_test"
        ],
        dtype=np.float64,
    )

    rows = []

    for p in range(
        len(
            tD
        )
    ):

        rows.append(
            {
                "profile":
                    int(
                        p
                    ),

                "tD":
                    float(
                        tD[p]
                    ),

                "state_L1":
                    float(
                        np.mean(
                            np.abs(
                                state[
                                    "error"
                                ][p]
                            )
                        )
                    ),

                "canonical_MAE":
                    mae(
                        model_db[
                            "canonical"
                        ][p]
                    ),

                "canonical_P90":
                    percentile_abs(
                        model_db[
                            "canonical"
                        ][p],
                        90.0,
                    ),

                "legacy_self_FV_MAE":
                    mae(
                        model_db[
                            "self_relative"
                        ][p]
                    ),

                "SG7A_self_FV_MAE":
                    mae(
                        truth_db[
                            "self_relative"
                        ][p]
                    ),

                "mass_relative_error":
                    float(
                        state[
                            "mass_relative_error"
                        ][p]
                    ),
            }
        )

    return rows


# =============================================================================
# CSV
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

def plot_profiles(
    dataset,
    truth,
    prediction,
):

    xi = np.asarray(
        dataset[
            "xi"
        ]
    )

    tD = np.asarray(
        dataset[
            "tD_test"
        ]
    )

    order = np.argsort(
        tD
    )

    positions = np.linspace(
        0,
        len(
            order
        )
        - 1,
        6,
        dtype=int,
    )

    selected = (
        order[
            positions
        ]
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            7,
        )
    )

    for p in selected:

        ax.plot(
            xi,
            truth[p],
            linewidth=2,
            label=(
                f"SG7A tD={tD[p]:.2f}"
            ),
        )

        ax.plot(
            xi,
            prediction[p],
            linestyle="--",
            linewidth=1.4,
            label=(
                f"PI-RNN tD={tD[p]:.2f}"
            ),
        )

    ax.set_xlabel(
        r"$\xi$"
    )

    ax.set_ylabel(
        "Saturation"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-7R\n"
        "Independent Final PI-RNN Profiles"
    )

    ax.legend(
        fontsize=7,
        ncol=2,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B7R_Final_Profiles.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_error_map(
    dataset,
    state,
):

    xi = np.asarray(
        dataset[
            "xi"
        ]
    )

    tD = np.asarray(
        dataset[
            "tD_test"
        ]
    )

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    image = ax.imshow(
        np.abs(
            state[
                "error"
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
        "Absolute saturation error"
    )

    ax.set_xlabel(
        r"$\xi$"
    )

    ax.set_ylabel(
        r"$t_D$"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-7R\n"
        "Final Saturation Error Map"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B7R_Error_Map.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_canonical_map(
    dataset,
    canonical,
):

    xi = np.asarray(
        dataset[
            "xi"
        ]
    )

    tD = np.asarray(
        dataset[
            "tD_test"
        ]
    )

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    image = ax.imshow(
        np.abs(
            canonical
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
        "PAD-Stream V15-SG7B-7R\n"
        "Canonical PI-RNN Physics Metric"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B7R_Canonical_Physics_Map.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_error_vs_time(
    dataset,
    time_metrics,
):

    tD = np.asarray(
        dataset[
            "tD_test"
        ]
    )

    order = np.argsort(
        tD
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        tD[
            order
        ],
        time_metrics[
            "profile_L1"
        ][
            order
        ],
    )

    ax.axhline(
        EARLY_L1_MAX,
        linestyle="--",
        label="Early-time guardrail",
    )

    ax.axhline(
        LATE_L1_MAX,
        linestyle=":",
        label="Late-time guardrail",
    )

    ax.set_xlabel(
        r"$t_D$"
    )

    ax.set_ylabel(
        "Profile L1 error"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-7R\n"
        "Final PI-RNN Error vs Time"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B7R_Error_vs_tD.png",
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_canonical_distribution(
    canonical,
):

    values = np.abs(
        canonical
    ).ravel()

    upper = float(
        np.percentile(
            values,
            99.5,
        )
    )

    bins = np.linspace(
        0.0,
        max(
            upper,
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
        values,
        bins=bins,
        density=True,
    )

    ax.axvline(
        1.0,
        linestyle="--",
        label="Discrepancy = SG7A activity",
    )

    ax.set_xlabel(
        r"$|(R_{NN}-R_{SG7A})/A_{SG7A}|$"
    )

    ax.set_ylabel(
        "Density"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-7R\n"
        "Canonical Physics Metric Distribution"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B7R_Canonical_Distribution.png",
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
        "PAD-Stream Version 15-SG7B-7R"
    )

    print(
        "Independent Final PI-RNN Freeze Validation"
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
        "NO VALIDATION THRESHOLD WILL BE CHANGED."
    )

    # =========================================================================
    # LOAD CONTRACT
    # =========================================================================

    contract = load_contract()

    verify_6h_summary()

    primary_contract = (
        contract[
            "primary_metric"
        ]
    )

    state_contract = (
        contract[
            "state_guardrails"
        ]
    )

    canonical_mean_max = float(
        primary_contract[
            "mean_max"
        ]
    )

    canonical_p90_max = float(
        primary_contract[
            "P90_max"
        ]
    )

    canonical_fraction_gt1_max = float(
        primary_contract[
            "fraction_gt_1_max"
        ]
    )

    state_L1_max = float(
        state_contract[
            "L1_max"
        ]
    )

    state_L2_max = float(
        state_contract[
            "L2_max"
        ]
    )

    mass_relative_max = float(
        state_contract[
            "mass_relative_MAE_max"
        ]
    )

    print(
        "\nFROZEN SG7B-6H CONTRACT"
    )

    print(
        f"  Canonical mean          : "
        f"< {canonical_mean_max:.3f}"
    )

    print(
        f"  Canonical P90           : "
        f"< {canonical_p90_max:.3f}"
    )

    print(
        f"  Fraction > 1            : "
        f"< {canonical_fraction_gt1_max:.2%}"
    )

    print(
        f"  Saturation L1           : "
        f"< {state_L1_max:.3f}"
    )

    print(
        f"  Saturation L2           : "
        f"< {state_L2_max:.3f}"
    )

    print(
        f"  Mass relative MAE       : "
        f"< {mass_relative_max:.3f}"
    )

    print(
        "\nRETAINED REGIONAL/TIME GUARDRAILS"
    )

    print(
        f"  Injector L1             : "
        f"< {INJECTOR_L1_MAX:.3f}"
    )

    print(
        f"  Front L1                : "
        f"< {FRONT_L1_MAX:.3f}"
    )

    print(
        f"  Early-time L1           : "
        f"< {EARLY_L1_MAX:.3f}"
    )

    print(
        f"  Late-time L1            : "
        f"< {LATE_L1_MAX:.3f}"
    )

    # =========================================================================
    # LOAD DATA
    # =========================================================================

    dataset = load_dataset()

    sg7a = load_sg7a()

    if not CANDIDATE_MODEL_FILE.exists():

        raise FileNotFoundError(
            "Missing SG7B-6D candidate:\n"
            f"{CANDIDATE_MODEL_FILE}"
        )

    source_hash = sha256_file(
        CANDIDATE_MODEL_FILE
    )

    model = tf.keras.models.load_model(
        CANDIDATE_MODEL_FILE
    )

    print(
        "\nFINAL CANDIDATE"
    )

    print(
        f"  Model                   : "
        f"{CANDIDATE_MODEL_FILE.name}"
    )

    print(
        "  Model load              : PASS"
    )

    print(
        f"  Parameters              : "
        f"{model.count_params():,}"
    )

    print(
        f"  SHA-256                 : "
        f"{source_hash}"
    )

    print(
        f"  Test profiles           : "
        f"{len(dataset['X_test'])}"
    )

    print(
        f"  Sequence nodes          : "
        f"{len(dataset['xi'])}"
    )

    # =========================================================================
    # INDEPENDENT RECOMPUTATION
    # =========================================================================

    print(
        "\nRecomputing frozen SG7A reference..."
    )

    truth_db = build_truth_database(
        dataset,
        sg7a,
    )

    print(
        "Recomputing SG7B-6D prediction and residual..."
    )

    model_db = build_model_database(
        model,
        dataset,
        truth_db,
    )

    # =========================================================================
    # STATE
    # =========================================================================

    xi = np.asarray(
        dataset[
            "xi"
        ],
        dtype=np.float64,
    )

    state = state_metrics(
        truth_db[
            "S"
        ],
        model_db[
            "S"
        ],
        xi,
    )

    # =========================================================================
    # CANONICAL PHYSICS
    # =========================================================================

    canonical = canonical_metrics(
        model_db[
            "canonical"
        ]
    )

    absolute_deltaR_MAE = mae(
        model_db[
            "deltaR"
        ]
    )

    # =========================================================================
    # LEGACY DIAGNOSTIC
    # =========================================================================

    legacy_self_FV_MAE = mae(
        model_db[
            "self_relative"
        ]
    )

    SG7A_self_FV_MAE = mae(
        truth_db[
            "self_relative"
        ]
    )

    legacy_ratio = (
        legacy_self_FV_MAE
        /
        max(
            SG7A_self_FV_MAE,
            EPS,
        )
    )

    # =========================================================================
    # REGIONAL / TIME
    # =========================================================================

    regional = build_regional_metrics(
        truth_db[
            "S"
        ],
        model_db[
            "S"
        ],
        xi,
    )

    tD = np.asarray(
        dataset[
            "tD_test"
        ],
        dtype=np.float64,
    )

    time_metrics = build_time_metrics(
        truth_db[
            "S"
        ],
        model_db[
            "S"
        ],
        tD,
    )

    # =========================================================================
    # SATURATION BOUNDS
    # =========================================================================

    prediction_min = float(
        np.min(
            model_db[
                "S"
            ]
        )
    )

    prediction_max = float(
        np.max(
            model_db[
                "S"
            ]
        )
    )

    # =========================================================================
    # PRINT METRICS
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "FINAL HELD-OUT STATE ACCURACY"
    )

    print(
        "=" * 78
    )

    print(
        f"L1                       : "
        f"{state['L1']:.6e}"
    )

    print(
        f"L2                       : "
        f"{state['L2']:.6e}"
    )

    print(
        f"Linf                     : "
        f"{state['Linf']:.6e}"
    )

    print(
        f"Predicted saturation     : "
        f"{prediction_min:.6f} -> {prediction_max:.6f}"
    )

    print(
        f"Mass relative MAE        : "
        f"{state['mass_relative_MAE']:.6e}"
    )

    print(
        f"Maximum mass error       : "
        f"{state['mass_relative_MAX']:.6e}"
    )

    print(
        "\nCANONICAL PHYSICS"
    )

    print(
        f"Absolute deltaR MAE      : "
        f"{absolute_deltaR_MAE:.6e}"
    )

    print(
        f"Canonical mean           : "
        f"{canonical['mean']:.6e}"
    )

    print(
        f"Canonical RMS            : "
        f"{canonical['RMS']:.6e}"
    )

    print(
        f"Canonical P50            : "
        f"{canonical['P50']:.6e}"
    )

    print(
        f"Canonical P90            : "
        f"{canonical['P90']:.6e}"
    )

    print(
        f"Canonical P95            : "
        f"{canonical['P95']:.6e}"
    )

    print(
        f"Canonical P99            : "
        f"{canonical['P99']:.6e}"
    )

    print(
        f"Fraction > 1             : "
        f"{canonical['fraction_gt_1']:.3%}"
    )

    print(
        "\nREGIONAL SATURATION ERROR"
    )

    print(
        f"Injector L1              : "
        f"{regional['injector_L1']:.6e}"
    )

    print(
        f"Front L1                 : "
        f"{regional['front_L1']:.6e}"
    )

    print(
        f"Interior L1              : "
        f"{regional['interior_L1']:.6e}"
    )

    print(
        f"Outlet L1                : "
        f"{regional['outlet_L1']:.6e}"
    )

    print(
        "\nTIME-BAND SATURATION ERROR"
    )

    print(
        f"Early L1                 : "
        f"{time_metrics['early_L1']:.6e}"
    )

    print(
        f"Middle L1                : "
        f"{time_metrics['middle_L1']:.6e}"
    )

    print(
        f"Late L1                  : "
        f"{time_metrics['late_L1']:.6e}"
    )

    print(
        "\nLEGACY DIAGNOSTIC — NOT A FREEZE GATE"
    )

    print(
        f"PI-RNN self FV MAE       : "
        f"{legacy_self_FV_MAE:.6e}"
    )

    print(
        f"SG7A self FV MAE         : "
        f"{SG7A_self_FV_MAE:.6e}"
    )

    print(
        f"Legacy ratio             : "
        f"{legacy_ratio:.3f}"
    )

    # =========================================================================
    # AUTHORITATIVE FREEZE GATES
    # =========================================================================

    checks = [
        (
            "Model loads successfully",
            True,
        ),

        (
            "Predictions finite",
            np.all(
                np.isfinite(
                    model_db[
                        "S"
                    ]
                )
            ),
        ),

        (
            "Canonical physics values finite",
            np.all(
                np.isfinite(
                    model_db[
                        "canonical"
                    ]
                )
            ),
        ),

        (
            "Saturation lower bound respected",
            prediction_min
            >=
            S_MIN
            -
            1.0e-6,
        ),

        (
            "Saturation upper bound respected",
            prediction_max
            <=
            S_MAX
            +
            1.0e-6,
        ),

        (
            f"Held-out L1 < {state_L1_max:.3f}",
            state[
                "L1"
            ]
            <
            state_L1_max,
        ),

        (
            f"Held-out L2 < {state_L2_max:.3f}",
            state[
                "L2"
            ]
            <
            state_L2_max,
        ),

        (
            f"Mass relative MAE < {mass_relative_max:.3f}",
            state[
                "mass_relative_MAE"
            ]
            <
            mass_relative_max,
        ),

        (
            f"Canonical mean < {canonical_mean_max:.3f}",
            canonical[
                "mean"
            ]
            <
            canonical_mean_max,
        ),

        (
            f"Canonical P90 < {canonical_p90_max:.3f}",
            canonical[
                "P90"
            ]
            <
            canonical_p90_max,
        ),

        (
            (
                "Canonical fraction > 1 "
                f"< {canonical_fraction_gt1_max:.2%}"
            ),
            canonical[
                "fraction_gt_1"
            ]
            <
            canonical_fraction_gt1_max,
        ),

        (
            f"Injector-region L1 < {INJECTOR_L1_MAX:.3f}",
            regional[
                "injector_L1"
            ]
            <
            INJECTOR_L1_MAX,
        ),

        (
            f"High-gradient/front L1 < {FRONT_L1_MAX:.3f}",
            regional[
                "front_L1"
            ]
            <
            FRONT_L1_MAX,
        ),

        (
            f"Early-time L1 < {EARLY_L1_MAX:.3f}",
            time_metrics[
                "early_L1"
            ]
            <
            EARLY_L1_MAX,
        ),

        (
            f"Late-time L1 < {LATE_L1_MAX:.3f}",
            time_metrics[
                "late_L1"
            ]
            <
            LATE_L1_MAX,
        ),
    ]

    freeze_passed = all(
        status
        for _, status
        in checks
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG7B-7R FINAL FREEZE GATES"
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
    # PROFILE TABLE
    # =========================================================================

    profile_rows = build_profile_rows(
        dataset,
        state,
        model_db,
        truth_db,
    )

    save_csv(
        PROFILE_METRICS_FILE,
        profile_rows,
    )

    regional_rows = [
        {
            "region":
                "injector",

            "L1":
                regional[
                    "injector_L1"
                ],
        },

        {
            "region":
                "front",

            "L1":
                regional[
                    "front_L1"
                ],
        },

        {
            "region":
                "interior",

            "L1":
                regional[
                    "interior_L1"
                ],
        },

        {
            "region":
                "outlet",

            "L1":
                regional[
                    "outlet_L1"
                ],
        },

        {
            "region":
                "early_time",

            "L1":
                time_metrics[
                    "early_L1"
                ],
        },

        {
            "region":
                "middle_time",

            "L1":
                time_metrics[
                    "middle_L1"
                ],
        },

        {
            "region":
                "late_time",

            "L1":
                time_metrics[
                    "late_L1"
                ],
        },
    ]

    save_csv(
        REGIONAL_METRICS_FILE,
        regional_rows,
    )

    # =========================================================================
    # NUMERICAL DATABASE
    # =========================================================================

    np.savez_compressed(
        NUMERICAL_FILE,

        xi=
            dataset[
                "xi"
            ],

        tD_test=
            dataset[
                "tD_test"
            ],

        truth=
            truth_db[
                "S"
            ],

        prediction=
            model_db[
                "S"
            ],

        error=
            state[
                "error"
            ],

        canonical_metric=
            model_db[
                "canonical"
            ],

        deltaR=
            model_db[
                "deltaR"
            ],

        PI_RNN_self_relative=
            model_db[
                "self_relative"
            ],

        SG7A_self_relative=
            truth_db[
                "self_relative"
            ],

        profile_L1=
            time_metrics[
                "profile_L1"
            ],

        mass_relative_error=
            state[
                "mass_relative_error"
            ],
    )

    # =========================================================================
    # DIAGNOSTICS
    # =========================================================================

    plot_profiles(
        dataset,
        truth_db[
            "S"
        ],
        model_db[
            "S"
        ],
    )

    plot_error_map(
        dataset,
        state,
    )

    plot_canonical_map(
        dataset,
        model_db[
            "canonical"
        ],
    )

    plot_error_vs_time(
        dataset,
        time_metrics,
    )

    plot_canonical_distribution(
        model_db[
            "canonical"
        ]
    )

    # =========================================================================
    # FREEZE MODEL ONLY AFTER ALL GATES PASS
    # =========================================================================

    frozen_hash = None

    if freeze_passed:

        shutil.copy2(
            CANDIDATE_MODEL_FILE,
            FROZEN_MODEL_FILE,
        )

        frozen_hash = sha256_file(
            FROZEN_MODEL_FILE
        )

        if (
            frozen_hash
            !=
            source_hash
        ):

            raise RuntimeError(
                "Frozen-model SHA-256 does not match "
                "accepted source checkpoint."
            )

    # =========================================================================
    # MANIFEST
    # =========================================================================

    manifest = {
        "milestone":
            "V15-SG7B-7R",

        "candidate_model":
            str(
                CANDIDATE_MODEL_FILE
            ),

        "candidate_model_name":
            CANDIDATE_MODEL_FILE.name,

        "candidate_SHA256":
            source_hash,

        "freeze_passed":
            bool(
                freeze_passed
            ),

        "frozen_model":
            (
                str(
                    FROZEN_MODEL_FILE
                )
                if freeze_passed
                else None
            ),

        "frozen_SHA256":
            frozen_hash,

        "canonical_contract":
            str(
                CANONICAL_CONTRACT_FILE
            ),

        "canonical_contract_milestone":
            "V15-SG7B-6H",

        "canonical_operator_source":
            (
                "PAD_Stream_V15SG7B6FR_"
                "Activity_Scaled_Coupled_Refinement.py"
            ),

        "training_performed":
            False,

        "architecture_changed":
            False,

        "thresholds_changed":
            False,

        "legacy_self_FV_used_as_freeze_gate":
            False,

        "freeze_checks": [
            {
                "description":
                    description,

                "passed":
                    bool(
                        status
                    ),
            }
            for (
                description,
                status,
            ) in checks
        ],
    }

    with open(
        FREEZE_MANIFEST_FILE,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            manifest,
            handle,
            indent=2,
        )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7B-7R",

        "description":
            "Independent final PI-RNN freeze validation",

        "candidate":
            "V15SG7B6D_Best_Model.keras",

        "candidate_SHA256":
            source_hash,

        "canonical_contract":
            "V15-SG7B-6H",

        "training_performed":
            False,

        "architecture_changed":
            False,

        "thresholds_changed":
            False,

        "state": {
            "L1":
                state[
                    "L1"
                ],

            "L2":
                state[
                    "L2"
                ],

            "Linf":
                state[
                    "Linf"
                ],

            "minimum_prediction":
                prediction_min,

            "maximum_prediction":
                prediction_max,

            "mass_relative_MAE":
                state[
                    "mass_relative_MAE"
                ],

            "mass_relative_MAX":
                state[
                    "mass_relative_MAX"
                ],
        },

        "canonical_physics": {
            **canonical,

            "absolute_deltaR_MAE":
                absolute_deltaR_MAE,
        },

        "regional": regional,

        "time_bands": {
            "early_L1":
                time_metrics[
                    "early_L1"
                ],

            "middle_L1":
                time_metrics[
                    "middle_L1"
                ],

            "late_L1":
                time_metrics[
                    "late_L1"
                ],
        },

        "legacy_diagnostic": {
            "PI_RNN_self_FV_MAE":
                legacy_self_FV_MAE,

            "SG7A_self_FV_MAE":
                SG7A_self_FV_MAE,

            "legacy_ratio":
                legacy_ratio,

            "used_as_freeze_gate":
                False,
        },

        "freeze_passed":
            bool(
                freeze_passed
            ),

        "status":
            (
                "V15_SG7B_PIRNN_FROZEN"
                if freeze_passed
                else
                "V15_SG7B_PIRNN_NOT_FROZEN"
            ),

        "frozen_model":
            (
                FROZEN_MODEL_FILE.name
                if freeze_passed
                else None
            ),

        "frozen_SHA256":
            frozen_hash,
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
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B7R_Final_Profiles.png"
    )

    print(
        "  V15SG7B7R_Error_Map.png"
    )

    print(
        "  V15SG7B7R_Canonical_Physics_Map.png"
    )

    print(
        "  V15SG7B7R_Error_vs_tD.png"
    )

    print(
        "  V15SG7B7R_Canonical_Distribution.png"
    )

    print(
        "\nTables:"
    )

    print(
        "  V15SG7B7R_Profile_Metrics.csv"
    )

    print(
        "  V15SG7B7R_Regional_Metrics.csv"
    )

    print(
        "\nNumerical:"
    )

    print(
        "  V15SG7B7R_Final_Validation.npz"
    )

    print(
        "\nFreeze manifest:"
    )

    print(
        "  V15SG7B_Freeze_Manifest.json"
    )

    print(
        "\nSummary:"
    )

    print(
        "  PAD_Stream_V15SG7B7R_Summary.json"
    )

    print(
        "\n"
        + "=" * 78
    )

    if freeze_passed:

        print(
            "V15-SG7B-7R FINAL VALIDATION: PASS"
        )

        print()

        print(
            "STATUS:"
        )

        print(
            "V15-SG7B PI-RNN FROZEN"
        )

        print()

        print(
            "Frozen model:"
        )

        print(
            f"  {FROZEN_MODEL_FILE.name}"
        )

        print()

        print(
            "SHA-256:"
        )

        print(
            f"  {frozen_hash}"
        )

        print()

        print(
            "SG7B full-physics PI-RNN development "
            "is complete for the reference case."
        )

    else:

        print(
            "V15-SG7B-7R FINAL VALIDATION: FAIL"
        )

        print()

        print(
            "STATUS:"
        )

        print(
            "V15-SG7B PI-RNN NOT FROZEN"
        )

        print()

        print(
            "No frozen model copy was created."
        )

        print()

        print(
            "Review the failed authoritative gate(s) "
            "before proceeding."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()