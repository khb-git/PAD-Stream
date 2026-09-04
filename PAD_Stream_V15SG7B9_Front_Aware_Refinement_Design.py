from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7B-9
# Front-Aware PI-RNN Targeted Refinement Design
#
# NO TRAINING.
# NO MODEL WEIGHT CHANGES.
# NO ARCHITECTURE CHANGE.
# NO FROZEN MODEL REPLACEMENT.
# NO FREEZE-GATE RELAXATION.
# NO SG7E THRESHOLD CHANGE.
#
#
# PURPOSE
# -------
#
# SG7B-8 established:
#
#       THRESHOLD_AVOIDANCE
#
# despite strong continuous-state accuracy.
#
#
# SG7B-9 therefore defines the controlled refinement contract for SG7B-10.
#
# It answers:
#
#   1. What defect are we trying to correct?
#
#   2. Which new front-aware loss terms are justified?
#
#   3. Which original frozen-model properties MUST be preserved?
#
#   4. Which training experiments will SG7B-10 run?
#
#   5. What constitutes improvement?
#
#   6. What constitutes unacceptable regression?
#
#
# IMPORTANT
# ---------
#
# SG7B-9 DOES NOT RETRAIN THE NETWORK.
#
# The existing frozen model remains authoritative until a future candidate
# independently passes all replacement gates.
#
# =============================================================================


# =============================================================================
# ROOT / OUTPUTS
# =============================================================================

ROOT = Path(__file__).resolve().parent


OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B9"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# INPUT FILES
# =============================================================================

SG7B8_SUMMARY_FILE = (
    ROOT
    / "output"
    / "V15_SG7B8"
    / "PAD_Stream_V15SG7B8_Summary.json"
)


SG7B8_TIME_METRICS_FILE = (
    ROOT
    / "output"
    / "V15_SG7B8"
    / "V15SG7B8_Front_Shape_By_Time.csv"
)


SG7B7R_SUMMARY_FILE = (
    ROOT
    / "output"
    / "V15_SG7B7R"
    / "PAD_Stream_V15SG7B7R_Summary.json"
)


SG7B_FREEZE_MANIFEST_FILE = (
    ROOT
    / "output"
    / "V15_SG7B7R"
    / "V15SG7B_Freeze_Manifest.json"
)


# =============================================================================
# OUTPUT FILES
# =============================================================================

CONTRACT_FILE = (
    OUTPUT_DIR
    / "V15SG7B9_Front_Aware_Refinement_Contract.json"
)


EXPERIMENT_MATRIX_FILE = (
    OUTPUT_DIR
    / "V15SG7B9_SG7B10_Experiment_Matrix.csv"
)


LOSS_COMPONENT_FILE = (
    OUTPUT_DIR
    / "V15SG7B9_Loss_Component_Design.csv"
)


PRESERVATION_GATES_FILE = (
    OUTPUT_DIR
    / "V15SG7B9_Preservation_Gates.csv"
)


FRONT_GATES_FILE = (
    OUTPUT_DIR
    / "V15SG7B9_Front_Improvement_Gates.csv"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B9_Summary.json"
)


# =============================================================================
# FROZEN SG7B IDENTITY
# =============================================================================

EXPECTED_FROZEN_SHA256 = (
    "9242af83e9aae6dc91ce215f78bf2a6d"
    "539972632d5e5ce759ea1fc83f3c11be"
)

FROZEN_MODEL_FILE = (
    ROOT
    / "output"
    / "V15_SG7B7R"
    / "V15SG7B_FROZEN_Model.keras"
)

# =============================================================================
# EXISTING FROZEN-MODEL PRESERVATION CONTRACT
#
# These come from the independently accepted SG7B-7R contract.
#
# THEY ARE NOT BEING RELAXED.
# =============================================================================

PRESERVE_L1_MAX = 0.020
PRESERVE_L2_MAX = 0.030
PRESERVE_MASS_MAE_MAX = 0.030

PRESERVE_CANONICAL_MEAN_MAX = 0.500
PRESERVE_CANONICAL_P90_MAX = 1.000
PRESERVE_CANONICAL_FRAC_GT1_MAX = 0.10

PRESERVE_INJECTOR_L1_MAX = 0.015
PRESERVE_FRONT_L1_MAX = 0.030

PRESERVE_EARLY_L1_MAX = 0.020
PRESERVE_LATE_L1_MAX = 0.025


# =============================================================================
# FRONT CONTRACT
# =============================================================================

FRONT_THRESHOLD = 0.210

FRONT_LOW_LEVEL = 0.210
FRONT_MID_LEVEL = 0.250
FRONT_HIGH_LEVEL = 0.300


# =============================================================================
# FRONT-AWARE TARGETS FOR SG7B-10
#
# These are refinement-design targets.
#
# They do not replace the existing SG7B freeze contract.
# =============================================================================

# Existing SG7B-7R state-accuracy reference used only as a design sanity check.
PROFILE_L1_REFERENCE = 0.020


# At 100 days SG7A showed 992 threshold crossings.
#
# We do NOT require a candidate to exactly reproduce all 992 immediately.
# The controlled refinement first needs to demonstrate substantial recovery.
FRONT_CROSSING_RECOVERY_MIN = 0.75


# Candidate must reduce the mean PI-RNN distance from S=0.21 by at least 75%
# relative to the frozen SG7B-8 baseline.
THRESHOLD_GAP_REDUCTION_MIN = 0.75


# Candidate early-profile L1 may not regress materially relative to the
# existing frozen baseline.
EARLY_PROFILE_L1_RELATIVE_REGRESSION_MAX = 0.10


# Candidate should not introduce excessive oscillation around the front.
LOCAL_MONOTONIC_VIOLATION_MAX = 0.02


# =============================================================================
# LOSS COMPONENT DESIGN
#
# SG7B-10 will use combinations of these components.
#
# =============================================================================

BASE_STATE_WEIGHT = 1.0

BASE_PHYSICS_WEIGHT = 1.0

BASE_MASS_WEIGHT = 1.0


# Front-zone state weighting:
#
# Amplifies supervision where SG7A lies near the early displacement front.
FRONT_ZONE_WEIGHT_OPTIONS = [
    2.0,
    4.0,
]


# Threshold-crossing loss:
#
# Encourages correct side-of-threshold classification around S=0.21.
CROSSING_WEIGHT_OPTIONS = [
    0.05,
    0.10,
]


# Front-location / shape loss:
#
# Uses differentiable front-region discrepancy rather than a hard front
# coordinate.
FRONT_SHAPE_WEIGHT_OPTIONS = [
    0.02,
    0.05,
]


# Gradient preservation:
#
# Prevents threshold recovery through a distorted or oscillatory profile.
GRADIENT_WEIGHT = 0.01


# Preservation / anchor:
#
# Penalizes movement away from the incoming frozen SG7B prediction outside
# the front region.
ANCHOR_WEIGHT = 0.10


# =============================================================================
# TRAINING DESIGN FOR SG7B-10
# =============================================================================

INITIAL_LEARNING_RATE = 2.5e-6

MAXIMUM_EPOCHS = 160

EARLY_STOPPING_PATIENCE = 30

LR_REDUCTION_PATIENCE = 12

MINIMUM_LEARNING_RATE = 2.5e-7


# =============================================================================
# FRONT-TIME EMPHASIS
#
# Existing problem is strongest at early physical time.
#
# Training itself still uses the full original domain. These factors only
# affect front-specific loss emphasis.
# =============================================================================

EARLY_TIME_WEIGHT = 4.0
MIDDLE_TIME_WEIGHT = 2.0
LATE_TIME_WEIGHT = 1.0


# =============================================================================
# HELPERS
# =============================================================================

def load_json(
    path: Path,
):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing JSON input:\n{path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:

        return json.load(
            handle
        )


def load_csv(
    path: Path,
):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing CSV input:\n{path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as handle:

        return list(
            csv.DictReader(
                handle
            )
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


def find_nested_value(
    obj,
    candidate_keys,
):

    """
    Recursively search a JSON-like structure for the first matching key.

    This makes SG7B-9 tolerant of minor summary/manifest nesting differences.
    """

    if isinstance(
        obj,
        dict,
    ):

        for key in candidate_keys:

            if key in obj:

                return obj[
                    key
                ]

        for value in obj.values():

            result = find_nested_value(
                value,
                candidate_keys,
            )

            if result is not None:

                return result

    elif isinstance(
        obj,
        list,
    ):

        for value in obj:

            result = find_nested_value(
                value,
                candidate_keys,
            )

            if result is not None:

                return result

    return None


# =============================================================================
# LOAD / RECONCILE SG7B-8 INPUT
# =============================================================================

def extract_sg7b8_contract(
    summary,
    time_rows,
):

    diagnosis = summary.get(
        "diagnosis",
        None,
    )

    if diagnosis != "THRESHOLD_AVOIDANCE":

        raise RuntimeError(
            "SG7B-9 requires SG7B-8 diagnosis:\n"
            "THRESHOLD_AVOIDANCE\n\n"
            f"Observed:\n{diagnosis}"
        )

    row_100 = None

    for row in time_rows:

        if np.isclose(
            float(
                row[
                    "time_days"
                ]
            ),
            100.0,
        ):

            row_100 = row

            break

    if row_100 is None:

        raise RuntimeError(
            "SG7B-8 100-day metric row not found."
        )

    return {
        "diagnosis":
            diagnosis,

        "SG7A_crossings_100d":
            int(
                float(
                    row_100[
                        "SG7A_threshold_crossings"
                    ]
                )
            ),

        "PI_RNN_crossings_100d":
            int(
                float(
                    row_100[
                        "PI_RNN_threshold_crossings"
                    ]
                )
            ),

        "PI_RNN_threshold_gap_mean_100d":
            float(
                row_100[
                    "PI_RNN_threshold_gap_mean"
                ]
            ),

        "PI_RNN_threshold_gap_P90_100d":
            float(
                row_100[
                    "PI_RNN_threshold_gap_P90"
                ]
            ),

        "profile_L1_mean_100d":
            float(
                row_100[
                    "profile_L1_mean"
                ]
            ),
    }


# =============================================================================
# FROZEN MODEL IDENTITY
# =============================================================================

def compute_sha256(
    path: Path,
    chunk_size: int = 1024 * 1024,
):

    path = Path(
        path
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Frozen SG7B model not found:\n{path}"
        )

    sha256 = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                chunk_size
            )

            if not chunk:

                break

            sha256.update(
                chunk
            )

    return sha256.hexdigest()


def reconcile_frozen_identity(
    freeze_manifest,
    sg7b7r_summary,
):

    """
    Verify frozen SG7B identity directly from the authoritative model file.

    The SG7B-7R JSON records are retained as supporting provenance, but model
    identity is established from the actual .keras file rather than relying
    on a particular JSON key layout.
    """

    # -------------------------------------------------------------------------
    # Direct model-file hash
    # -------------------------------------------------------------------------

    actual_hash = compute_sha256(
        FROZEN_MODEL_FILE
    )

    identity_pass = (
        actual_hash
        ==
        EXPECTED_FROZEN_SHA256
    )

    # -------------------------------------------------------------------------
    # Optional provenance hashes from JSON
    #
    # These are informative only. Their absence must NOT invalidate a direct
    # model-file identity check.
    # -------------------------------------------------------------------------

    hash_candidates = [
        "sha256",
        "SHA-256",
        "sha_256",
        "model_sha256",
        "model_sha_256",
        "frozen_model_sha256",
        "frozen_model_sha_256",
        "model_hash",
        "hash",
    ]

    manifest_hash = find_nested_value(
        freeze_manifest,
        hash_candidates,
    )

    summary_hash = find_nested_value(
        sg7b7r_summary,
        hash_candidates,
    )

    return {
        "model_file":
            str(
                FROZEN_MODEL_FILE
            ),

        "actual_model_hash":
            actual_hash,

        "expected_model_hash":
            EXPECTED_FROZEN_SHA256,

        "manifest_hash":
            (
                str(
                    manifest_hash
                ).strip()
                if manifest_hash is not None
                else None
            ),

        "summary_hash":
            (
                str(
                    summary_hash
                ).strip()
                if summary_hash is not None
                else None
            ),

        "identity_pass":
            bool(
                identity_pass
            ),
    }


# =============================================================================
# LOSS COMPONENT TABLE
# =============================================================================

def build_loss_component_table():

    rows = [
        {
            "component":
                "state_data",

            "symbol":
                "L_state",

            "purpose":
                (
                    "Preserve global SG7A saturation agreement."
                ),

            "region":
                "all nodes",

            "time_emphasis":
                "all times",

            "candidate_weight":
                BASE_STATE_WEIGHT,

            "new_in_SG7B9":
                False,
        },

        {
            "component":
                "canonical_physics",

            "symbol":
                "L_phys",

            "purpose":
                (
                    "Preserve frozen canonical surrogate-physics agreement."
                ),

            "region":
                "all nodes",

            "time_emphasis":
                "all times",

            "candidate_weight":
                BASE_PHYSICS_WEIGHT,

            "new_in_SG7B9":
                False,
        },

        {
            "component":
                "mass",

            "symbol":
                "L_mass",

            "purpose":
                (
                    "Preserve displaced-phase inventory."
                ),

            "region":
                "whole profile",

            "time_emphasis":
                "all times",

            "candidate_weight":
                BASE_MASS_WEIGHT,

            "new_in_SG7B9":
                False,
        },

        {
            "component":
                "front_zone_state",

            "symbol":
                "L_front",

            "purpose":
                (
                    "Increase state supervision around SG7A front zone "
                    "S in [0.21, 0.30]."
                ),

            "region":
                "SG7A front band",

            "time_emphasis":
                "early dominant",

            "candidate_weight":
                "2.0 or 4.0",

            "new_in_SG7B9":
                True,
        },

        {
            "component":
                "threshold_crossing",

            "symbol":
                "L_cross",

            "purpose":
                (
                    "Correct SG7B-8 threshold avoidance at S=0.21."
                ),

            "region":
                "front-adjacent nodes",

            "time_emphasis":
                "early dominant",

            "candidate_weight":
                "0.05 or 0.10",

            "new_in_SG7B9":
                True,
        },

        {
            "component":
                "front_shape",

            "symbol":
                "L_shape",

            "purpose":
                (
                    "Preserve SG7A local front morphology without using a "
                    "non-differentiable hard front coordinate."
                ),

            "region":
                "front band",

            "time_emphasis":
                "early/middle",

            "candidate_weight":
                "0.02 or 0.05",

            "new_in_SG7B9":
                True,
        },

        {
            "component":
                "front_gradient",

            "symbol":
                "L_grad",

            "purpose":
                (
                    "Prevent artificial oscillation or distorted sharpness "
                    "during threshold recovery."
                ),

            "region":
                "front band",

            "time_emphasis":
                "early/middle",

            "candidate_weight":
                GRADIENT_WEIGHT,

            "new_in_SG7B9":
                True,
        },

        {
            "component":
                "frozen_anchor",

            "symbol":
                "L_anchor",

            "purpose":
                (
                    "Keep refined prediction close to frozen SG7B outside "
                    "the diagnosed front region."
                ),

            "region":
                "non-front nodes",

            "time_emphasis":
                "all times",

            "candidate_weight":
                ANCHOR_WEIGHT,

            "new_in_SG7B9":
                True,
        },
    ]

    return rows


# =============================================================================
# PRESERVATION GATES
# =============================================================================

def build_preservation_gates():

    return [
        {
            "metric":
                "held_out_L1",

            "operator":
                "<",

            "threshold":
                PRESERVE_L1_MAX,

            "status":
                "UNCHANGED_FROM_SG7B7R",
        },

        {
            "metric":
                "held_out_L2",

            "operator":
                "<",

            "threshold":
                PRESERVE_L2_MAX,

            "status":
                "UNCHANGED_FROM_SG7B7R",
        },

        {
            "metric":
                "mass_relative_MAE",

            "operator":
                "<",

            "threshold":
                PRESERVE_MASS_MAE_MAX,

            "status":
                "UNCHANGED_FROM_SG7B7R",
        },

        {
            "metric":
                "canonical_mean",

            "operator":
                "<",

            "threshold":
                PRESERVE_CANONICAL_MEAN_MAX,

            "status":
                "UNCHANGED_FROM_SG7B7R",
        },

        {
            "metric":
                "canonical_P90",

            "operator":
                "<",

            "threshold":
                PRESERVE_CANONICAL_P90_MAX,

            "status":
                "UNCHANGED_FROM_SG7B7R",
        },

        {
            "metric":
                "canonical_fraction_gt_1",

            "operator":
                "<",

            "threshold":
                PRESERVE_CANONICAL_FRAC_GT1_MAX,

            "status":
                "UNCHANGED_FROM_SG7B7R",
        },

        {
            "metric":
                "injector_L1",

            "operator":
                "<",

            "threshold":
                PRESERVE_INJECTOR_L1_MAX,

            "status":
                "UNCHANGED_FROM_SG7B7R",
        },

        {
            "metric":
                "front_L1",

            "operator":
                "<",

            "threshold":
                PRESERVE_FRONT_L1_MAX,

            "status":
                "UNCHANGED_FROM_SG7B7R",
        },

        {
            "metric":
                "early_time_L1",

            "operator":
                "<",

            "threshold":
                PRESERVE_EARLY_L1_MAX,

            "status":
                "UNCHANGED_FROM_SG7B7R",
        },

        {
            "metric":
                "late_time_L1",

            "operator":
                "<",

            "threshold":
                PRESERVE_LATE_L1_MAX,

            "status":
                "UNCHANGED_FROM_SG7B7R",
        },
    ]


# =============================================================================
# FRONT IMPROVEMENT GATES
# =============================================================================

def build_front_gates(
    sg7b8,
):

    target_crossings = int(
        np.ceil(
            FRONT_CROSSING_RECOVERY_MIN
            *
            sg7b8[
                "SG7A_crossings_100d"
            ]
        )
    )

    maximum_gap = (
        (
            1.0
            -
            THRESHOLD_GAP_REDUCTION_MIN
        )
        *
        sg7b8[
            "PI_RNN_threshold_gap_mean_100d"
        ]
    )

    maximum_profile_l1 = (
        (
            1.0
            +
            EARLY_PROFILE_L1_RELATIVE_REGRESSION_MAX
        )
        *
        sg7b8[
            "profile_L1_mean_100d"
        ]
    )

    return [
        {
            "metric":
                "100d_PI_RNN_threshold_crossings",

            "operator":
                ">=",

            "threshold":
                target_crossings,

            "basis":
                (
                    f">= {FRONT_CROSSING_RECOVERY_MIN:.0%} "
                    "of SG7A 100-day front count"
                ),
        },

        {
            "metric":
                "100d_threshold_gap_mean",

            "operator":
                "<=",

            "threshold":
                maximum_gap,

            "basis":
                (
                    f">= {THRESHOLD_GAP_REDUCTION_MIN:.0%} "
                    "reduction from SG7B-8"
                ),
        },

        {
            "metric":
                "100d_profile_L1",

            "operator":
                "<=",

            "threshold":
                maximum_profile_l1,

            "basis":
                (
                    "<= 10% relative regression from "
                    "frozen SG7B-8 early profile L1"
                ),
        },

        {
            "metric":
                "front_local_monotonic_violation",

            "operator":
                "<=",

            "threshold":
                LOCAL_MONOTONIC_VIOLATION_MAX,

            "basis":
                "prevent oscillatory artificial crossing",
        },
    ]


# =============================================================================
# SG7B-10 EXPERIMENT MATRIX
#
# Deliberately small.
#
# We do NOT launch a large hyperparameter search.
#
# This is a controlled mechanism test.
# =============================================================================

def build_experiment_matrix():

    rows = []

    experiment_id = 1

    # -------------------------------------------------------------------------
    # E0
    #
    # Existing frozen model.
    #
    # NO TRAINING.
    # -------------------------------------------------------------------------

    rows.append(
        {
            "experiment":
                "E0",

            "description":
                "Frozen SG7B control",

            "front_zone_weight":
                0.0,

            "crossing_weight":
                0.0,

            "front_shape_weight":
                0.0,

            "gradient_weight":
                0.0,

            "anchor_weight":
                0.0,

            "learning_rate":
                0.0,

            "maximum_epochs":
                0,

            "training":
                False,

            "role":
                "CONTROL",
        }
    )

    # -------------------------------------------------------------------------
    # Primary controlled designs
    # -------------------------------------------------------------------------

    designs = [
        (
            "E1",
            "Front-zone state emphasis only",
            2.0,
            0.0,
            0.0,
        ),

        (
            "E2",
            "Front-zone + threshold crossing",
            2.0,
            0.05,
            0.0,
        ),

        (
            "E3",
            "Front-zone + stronger threshold crossing",
            2.0,
            0.10,
            0.0,
        ),

        (
            "E4",
            "Front-zone + crossing + shape",
            2.0,
            0.05,
            0.02,
        ),

        (
            "E5",
            "Strong front-zone + crossing + shape",
            4.0,
            0.05,
            0.02,
        ),

        (
            "E6",
            "Strong front-aware balanced candidate",
            4.0,
            0.10,
            0.05,
        ),
    ]

    for (
        experiment,
        description,
        front_weight,
        crossing_weight,
        shape_weight,
    ) in designs:

        rows.append(
            {
                "experiment":
                    experiment,

                "description":
                    description,

                "front_zone_weight":
                    front_weight,

                "crossing_weight":
                    crossing_weight,

                "front_shape_weight":
                    shape_weight,

                "gradient_weight":
                    GRADIENT_WEIGHT,

                "anchor_weight":
                    ANCHOR_WEIGHT,

                "learning_rate":
                    INITIAL_LEARNING_RATE,

                "maximum_epochs":
                    MAXIMUM_EPOCHS,

                "training":
                    True,

                "role":
                    "CONTROLLED_REFINEMENT",
            }
        )

        experiment_id += 1

    return rows


# =============================================================================
# PLOT EXPERIMENT MATRIX
# =============================================================================

def plot_experiment_matrix(
    experiment_rows,
):

    training_rows = [
        row
        for row
        in experiment_rows
        if row[
            "training"
        ]
    ]

    labels = [
        row[
            "experiment"
        ]
        for row
        in training_rows
    ]

    front_weights = np.asarray(
        [
            row[
                "front_zone_weight"
            ]
            for row
            in training_rows
        ],
        dtype=np.float64,
    )

    crossing_weights = np.asarray(
        [
            row[
                "crossing_weight"
            ]
            for row
            in training_rows
        ],
        dtype=np.float64,
    )

    shape_weights = np.asarray(
        [
            row[
                "front_shape_weight"
            ]
            for row
            in training_rows
        ],
        dtype=np.float64,
    )

    x = np.arange(
        len(
            labels
        )
    )

    width = 0.25

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    ax.bar(
        x
        -
        width,
        front_weights,
        width,
        label="Front-zone",
    )

    ax.bar(
        x,
        crossing_weights,
        width,
        label="Crossing",
    )

    ax.bar(
        x
        +
        width,
        shape_weights,
        width,
        label="Shape",
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        labels
    )

    ax.set_ylabel(
        "Loss weight"
    )

    ax.set_xlabel(
        "SG7B-10 experiment"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-9\n"
        "Controlled Front-Aware Experiment Matrix"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B9_Experiment_Matrix.png",
        dpi=300,
    )

    plt.close(
        fig
    )


# =============================================================================
# PLOT GATE STRUCTURE
# =============================================================================

def plot_gate_structure():

    categories = [
        "State",
        "Physics",
        "Mass",
        "Front",
        "Early",
        "Late",
    ]

    number_of_gates = [
        2,
        3,
        1,
        4,
        1,
        1,
    ]

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.bar(
        categories,
        number_of_gates,
    )

    ax.set_ylabel(
        "Number of required validation checks"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-9\n"
        "Candidate Preservation / Improvement Contract"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B9_Validation_Contract.png",
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
        "PAD-Stream Version 15-SG7B-9"
    )

    print(
        "Front-Aware PI-RNN Targeted Refinement Design"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    print(
        "NO MODEL WEIGHTS WILL BE CHANGED."
    )

    print(
        "NO ARCHITECTURE CHANGE WILL BE MADE."
    )

    print(
        "NO FROZEN MODEL WILL BE REPLACED."
    )

    print(
        "NO SG7B-7R FREEZE GATE WILL BE RELAXED."
    )

    print(
        "NO SG7E THRESHOLD WILL BE CHANGED."
    )

    # =========================================================================
    # LOAD AUTHORITATIVE INPUTS
    # =========================================================================

    sg7b8_summary = load_json(
        SG7B8_SUMMARY_FILE
    )

    sg7b8_time_rows = load_csv(
        SG7B8_TIME_METRICS_FILE
    )

    sg7b7r_summary = load_json(
        SG7B7R_SUMMARY_FILE
    )

    freeze_manifest = load_json(
        SG7B_FREEZE_MANIFEST_FILE
    )

    # =========================================================================
    # RECONCILE SG7B-8
    # =========================================================================

    sg7b8 = extract_sg7b8_contract(
        sg7b8_summary,
        sg7b8_time_rows,
    )

    print(
        "\nSG7B-8 DIAGNOSTIC INPUT"
    )

    print(
        f"  Diagnosis               : "
        f"{sg7b8['diagnosis']}"
    )

    print(
        f"  SG7A crossings @100d    : "
        f"{sg7b8['SG7A_crossings_100d']:,}"
    )

    print(
        f"  PI-RNN crossings @100d  : "
        f"{sg7b8['PI_RNN_crossings_100d']:,}"
    )

    print(
        f"  PI-RNN mean gap @100d   : "
        f"{sg7b8['PI_RNN_threshold_gap_mean_100d']:.6e}"
    )

    print(
        f"  PI-RNN gap P90 @100d    : "
        f"{sg7b8['PI_RNN_threshold_gap_P90_100d']:.6e}"
    )

    print(
        f"  Mean profile L1 @100d   : "
        f"{sg7b8['profile_L1_mean_100d']:.6e}"
    )

    # =========================================================================
    # FROZEN MODEL IDENTITY
    # =========================================================================

    identity = reconcile_frozen_identity(
        freeze_manifest,
        sg7b7r_summary,
    )

    print(
        "\nFROZEN SG7B BASELINE"
    )

    print(
        f"  Model                   : "
        f"{Path(identity['model_file']).name}"
    )

    print(
        f"  Expected SHA-256        : "
        f"{identity['expected_model_hash']}"
    )

    print(
        f"  Actual SHA-256          : "
        f"{identity['actual_model_hash']}"
    )

    print(
        f"  Identity verified       : "
        f"{identity['identity_pass']}"
    )

    if not identity[
        "identity_pass"
    ]:

        raise RuntimeError(
            "Frozen SG7B identity could not be verified.\n"
            "Do not design a refinement branch from an ambiguous source model."
        )

    # =========================================================================
    # DESIGN TABLES
    # =========================================================================

    loss_rows = build_loss_component_table()

    preservation_rows = build_preservation_gates()

    front_gate_rows = build_front_gates(
        sg7b8
    )

    experiment_rows = build_experiment_matrix()

    # =========================================================================
    # PRINT LOSS DESIGN
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "FRONT-AWARE LOSS DESIGN"
    )

    print(
        "=" * 78
    )

    print(
        "\nBase preservation terms:"
    )

    print(
        "  L_state                 : retain global state accuracy"
    )

    print(
        "  L_phys                  : retain canonical physics"
    )

    print(
        "  L_mass                  : retain inventory accuracy"
    )

    print(
        "\nNew targeted terms:"
    )

    print(
        "  L_front                 : emphasize SG7A front-zone state"
    )

    print(
        "  L_cross                 : correct S=0.21 threshold avoidance"
    )

    print(
        "  L_shape                 : preserve local front morphology"
    )

    print(
        "  L_grad                  : suppress artificial oscillation"
    )

    print(
        "  L_anchor                : preserve frozen solution away from front"
    )

    print(
        "\nConceptual refinement objective:"
    )

    print(
        "  L_total ="
    )

    print(
        "      L_state"
    )

    print(
        "    + L_phys"
    )

    print(
        "    + L_mass"
    )

    print(
        "    + lambda_front * L_front"
    )

    print(
        "    + lambda_cross * L_cross"
    )

    print(
        "    + lambda_shape * L_shape"
    )

    print(
        "    + lambda_grad * L_grad"
    )

    print(
        "    + lambda_anchor * L_anchor"
    )

    # =========================================================================
    # FRONT GATES
    # =========================================================================

    crossing_gate = next(
        row
        for row
        in front_gate_rows
        if row[
            "metric"
        ]
        ==
        "100d_PI_RNN_threshold_crossings"
    )

    gap_gate = next(
        row
        for row
        in front_gate_rows
        if row[
            "metric"
        ]
        ==
        "100d_threshold_gap_mean"
    )

    early_l1_gate = next(
        row
        for row
        in front_gate_rows
        if row[
            "metric"
        ]
        ==
        "100d_profile_L1"
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "SG7B-10 FRONT-IMPROVEMENT CONTRACT"
    )

    print(
        "=" * 78
    )

    print(
        f"  Minimum 100d crossings  : "
        f"{int(crossing_gate['threshold']):,}"
    )

    print(
        f"  Maximum mean S=0.21 gap : "
        f"{gap_gate['threshold']:.6e}"
    )

    print(
        f"  Maximum 100d profile L1 : "
        f"{early_l1_gate['threshold']:.6e}"
    )

    print(
        f"  Local monotonic violation: "
        f"<= {LOCAL_MONOTONIC_VIOLATION_MAX:.3%}"
    )

    print(
        "\nThese are ADDITIONAL requirements."
    )

    print(
        "All original SG7B-7R state, mass, regional, and canonical-physics"
    )

    print(
        "gates remain mandatory."
    )

    # =========================================================================
    # TRAINING CONTRACT
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "SG7B-10 CONTROLLED TRAINING CONTRACT"
    )

    print(
        "=" * 78
    )

    print(
        f"  Starting checkpoint     : V15SG7B_FROZEN_Model.keras"
    )

    print(
        f"  Initial learning rate   : {INITIAL_LEARNING_RATE:.2e}"
    )

    print(
        f"  Minimum learning rate   : {MINIMUM_LEARNING_RATE:.2e}"
    )

    print(
        f"  Maximum epochs          : {MAXIMUM_EPOCHS}"
    )

    print(
        f"  Early-stop patience     : {EARLY_STOPPING_PATIENCE}"
    )

    print(
        f"  LR reduction patience   : {LR_REDUCTION_PATIENCE}"
    )

    print(
        "\nTime emphasis:"
    )

    print(
        f"  Early                   : {EARLY_TIME_WEIGHT:.1f}"
    )

    print(
        f"  Middle                  : {MIDDLE_TIME_WEIGHT:.1f}"
    )

    print(
        f"  Late                    : {LATE_TIME_WEIGHT:.1f}"
    )

    print(
        "\nControlled experiments:"
    )

    for row in experiment_rows:

        print(
            f"  {row['experiment']:>2s} | "
            f"{row['description']}"
        )

    # =========================================================================
    # DESIGN VALIDATION
    # =========================================================================

    checks = [
        (
            "SG7B-8 diagnosis = THRESHOLD_AVOIDANCE",
            (
                sg7b8[
                    "diagnosis"
                ]
                ==
                "THRESHOLD_AVOIDANCE"
            ),
        ),

        (
            "Frozen SG7B identity verified",
            identity[
                "identity_pass"
            ],
        ),

        (
            "SG7A has early threshold fronts",
            sg7b8[
                "SG7A_crossings_100d"
            ]
            >
            0,
        ),

        (
            "Frozen PI-RNN has zero early threshold crossings",
            sg7b8[
                "PI_RNN_crossings_100d"
            ]
            ==
            0,
        ),

        (
            "Frozen early-profile L1 remains good",
            sg7b8[
                "profile_L1_mean_100d"
            ]
            <
            PROFILE_L1_REFERENCE,
        ),

        (
            "Front gate target is nonzero",
            int(
                crossing_gate[
                    "threshold"
                ]
            )
            >
            0,
        ),

        (
            "Threshold-gap target is stricter than frozen baseline",
            gap_gate[
                "threshold"
            ]
            <
            sg7b8[
                "PI_RNN_threshold_gap_mean_100d"
            ],
        ),

        (
            "Preservation contract retains canonical physics gates",
            any(
                row[
                    "metric"
                ]
                ==
                "canonical_mean"
                for row
                in preservation_rows
            ),
        ),

        (
            "Controlled experiment matrix contains frozen control",
            any(
                row[
                    "role"
                ]
                ==
                "CONTROL"
                for row
                in experiment_rows
            ),
        ),

        (
            "No training performed by SG7B-9",
            True,
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
        "V15-SG7B-9 DESIGN VALIDATION"
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

    # =========================================================================
    # DECISION
    # =========================================================================

    if passed:

        diagnosis = (
            "FRONT_AWARE_REFINEMENT_CONTRACT_READY"
        )

        recommendation = (
            "Proceed to a controlled SG7B-10 refinement branch starting "
            "from the frozen SG7B checkpoint. Run the defined experiment "
            "matrix without replacing the frozen model. Candidate selection "
            "must satisfy both front-improvement gates and the complete "
            "original SG7B-7R preservation contract."
        )

        next_milestone = (
            "V15-SG7B-10 — Controlled Front-Aware PI-RNN Refinement"
        )

    else:

        diagnosis = (
            "REFINEMENT_CONTRACT_INCOMPLETE"
        )

        recommendation = (
            "Do not retrain SG7B. Resolve the failed SG7B-9 design checks."
        )

        next_milestone = (
            "V15-SG7B-9R — Refinement Contract Reconciliation"
        )

    print(
        "\nSTATUS"
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
        LOSS_COMPONENT_FILE,
        loss_rows,
    )

    save_csv(
        PRESERVATION_GATES_FILE,
        preservation_rows,
    )

    save_csv(
        FRONT_GATES_FILE,
        front_gate_rows,
    )

    save_csv(
        EXPERIMENT_MATRIX_FILE,
        experiment_rows,
    )

    # =========================================================================
    # CONTRACT JSON
    # =========================================================================

    contract = {
        "milestone":
            "V15-SG7B-9",

        "purpose":
            (
                "Define a controlled front-aware refinement strategy for "
                "the frozen SG7B PI-RNN after SG7B-8 diagnosed threshold "
                "avoidance."
            ),

        "training_performed":
            False,

        "architecture_changed":
            False,

        "frozen_model_replaced":
            False,

        "freeze_gate_relaxed":
            False,

        "frozen_model": {
            "filename":
                "V15SG7B_FROZEN_Model.keras",

            "expected_sha256":
                EXPECTED_FROZEN_SHA256,

            "identity_verified":
                identity[
                    "identity_pass"
                ],
        },

        "incoming_SG7B8": {
            **sg7b8,
        },

        "front_contract": {
            "threshold":
                FRONT_THRESHOLD,

            "low_level":
                FRONT_LOW_LEVEL,

            "mid_level":
                FRONT_MID_LEVEL,

            "high_level":
                FRONT_HIGH_LEVEL,
        },

        "loss_design": {
            "base_state_weight":
                BASE_STATE_WEIGHT,

            "base_physics_weight":
                BASE_PHYSICS_WEIGHT,

            "base_mass_weight":
                BASE_MASS_WEIGHT,

            "front_zone_weight_options":
                FRONT_ZONE_WEIGHT_OPTIONS,

            "crossing_weight_options":
                CROSSING_WEIGHT_OPTIONS,

            "front_shape_weight_options":
                FRONT_SHAPE_WEIGHT_OPTIONS,

            "gradient_weight":
                GRADIENT_WEIGHT,

            "anchor_weight":
                ANCHOR_WEIGHT,
        },

        "time_emphasis": {
            "early":
                EARLY_TIME_WEIGHT,

            "middle":
                MIDDLE_TIME_WEIGHT,

            "late":
                LATE_TIME_WEIGHT,
        },

        "training_design": {
            "initial_learning_rate":
                INITIAL_LEARNING_RATE,

            "minimum_learning_rate":
                MINIMUM_LEARNING_RATE,

            "maximum_epochs":
                MAXIMUM_EPOCHS,

            "early_stopping_patience":
                EARLY_STOPPING_PATIENCE,

            "lr_reduction_patience":
                LR_REDUCTION_PATIENCE,
        },

        "front_improvement_gates":
            front_gate_rows,

        "preservation_gates":
            preservation_rows,

        "candidate_replacement_rule": (
            "A refined candidate may NOT replace the frozen SG7B model "
            "unless it independently passes all front-improvement gates "
            "AND all original SG7B-7R preservation gates."
        ),

        "next_milestone":
            next_milestone,
    }

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            contract,
            handle,
            indent=2,
        )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG7B-9",

        "description":
            "Front-aware PI-RNN targeted refinement design",

        "training_performed":
            False,

        "frozen_model_changed":
            False,

        "architecture_changed":
            False,

        "incoming_diagnosis":
            sg7b8[
                "diagnosis"
            ],

        "frozen_model_identity_verified":
            identity[
                "identity_pass"
            ],

        "number_of_training_candidates":
            sum(
                row[
                    "training"
                ]
                for row
                in experiment_rows
            ),

        "front_improvement_target": {
            "minimum_100d_crossings":
                int(
                    crossing_gate[
                        "threshold"
                    ]
                ),

            "maximum_100d_threshold_gap_mean":
                float(
                    gap_gate[
                        "threshold"
                    ]
                ),

            "maximum_100d_profile_L1":
                float(
                    early_l1_gate[
                        "threshold"
                    ]
                ),
        },

        "preservation_contract_retained":
            True,

        "design_passed":
            bool(
                passed
            ),

        "status":
            diagnosis,

        "recommendation":
            recommendation,

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
    # PLOTS
    # =========================================================================

    plot_experiment_matrix(
        experiment_rows
    )

    plot_gate_structure()

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
        "\nContract:"
    )

    print(
        f"  {CONTRACT_FILE.name}"
    )

    print(
        "\nTables:"
    )

    print(
        f"  {LOSS_COMPONENT_FILE.name}"
    )

    print(
        f"  {PRESERVATION_GATES_FILE.name}"
    )

    print(
        f"  {FRONT_GATES_FILE.name}"
    )

    print(
        f"  {EXPERIMENT_MATRIX_FILE.name}"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B9_Experiment_Matrix.png"
    )

    print(
        "  V15SG7B9_Validation_Contract.png"
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
            "V15-SG7B-9 DESIGN: PASS"
        )

        print()

        print(
            "STATUS:"
        )

        print(
            "FRONT-AWARE PI-RNN REFINEMENT CONTRACT ESTABLISHED"
        )

        print()

        print(
            "The frozen SG7B model remains authoritative."
        )

        print(
            "No retraining has occurred."
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7B-10 — Controlled Front-Aware PI-RNN Refinement"
        )

    else:

        print(
            "V15-SG7B-9 DESIGN: INCOMPLETE"
        )

        print()

        print(
            "DO NOT START SG7B-10."
        )

    print(
        "=" * 78
    )


# =============================================================================
# SCRIPT ENTRY
# =============================================================================

if __name__ == "__main__":
    main()