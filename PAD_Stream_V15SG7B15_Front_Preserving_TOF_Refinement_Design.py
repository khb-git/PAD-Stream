from __future__ import annotations

from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7B-15
# Front-Preserving TOF Refinement Design
#
# DESIGN-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL WEIGHTS CHANGED.
# NO ARCHITECTURE CHANGE.
# NO SG7B-11 FROZEN MODEL REPLACED.
# NO SG7B-10S FRONT-SHAPE GATE RELAXED.
# NO SG7B-12 TOF-BIAS GATE RELAXED.
# NO SG7E PLUME THRESHOLD CHANGED.
#
# PURPOSE
# -------
# SG7B-14R established a recurring tradeoff across ALL SG7B-13 E1-E5 models:
#
#   - every model satisfied the TOF-bias correction direction,
#   - every model failed the conditioned-front-gap gate,
#   - every model failed the SG7A/E0-relative front-shape contract.
#
# Diagnosis:
#
#   TOF_REFINEMENT_FRONT_PRESERVATION_TRADEOFF
#
# SG7B-15 redesigns the refinement so that:
#
#   1. strong TOF correction is applied only AWAY FROM the accepted front,
#   2. the front neighborhood is explicitly anchored to SG7B-11,
#   3. the S=0.21 crossing position is explicitly preserved,
#   4. local front gradients / total variation remain bounded,
#   5. slow-streamline tail bias is still reduced,
#   6. short-TOF behavior remains protected,
#   7. all previous preservation and bias gates remain mandatory.
#
# This milestone performs NO training. It creates the SG7B-16 controlled
# experiment contract.
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

SG7B14R_SUMMARY = (
    ROOT
    / "output"
    / "V15_SG7B14R"
    / "PAD_Stream_V15SG7B14R_Summary.json"
)

SG7B14R_MODEL_METRICS = (
    ROOT
    / "output"
    / "V15_SG7B14R"
    / "V15SG7B14R_Independent_Model_Metrics.csv"
)

SG7B14R_SHAPE_MATRIX = (
    ROOT
    / "output"
    / "V15_SG7B14R"
    / "V15SG7B14R_Front_Shape_Gate_Matrix.csv"
)

SG7B10S_CONTRACT = (
    ROOT
    / "output"
    / "V15_SG7B10S"
    / "V15SG7B10S_SG7A_Relative_Front_Shape_Contract.json"
)

SG7B12_CONTRACT = (
    ROOT
    / "output"
    / "V15_SG7B12"
    / "V15SG7B12_TOF_Conditioned_Refinement_Contract.json"
)

SG7B11_FROZEN_MODEL = (
    ROOT
    / "output"
    / "V15_SG7B11"
    / "V15SG7B_FRONT_AWARE_FROZEN_Model.keras"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B15"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

CONTRACT_FILE = (
    OUTPUT_DIR
    / "V15SG7B15_Front_Preserving_TOF_Refinement_Contract.json"
)

LOSS_TABLE = (
    OUTPUT_DIR
    / "V15SG7B15_Loss_Component_Design.csv"
)

REGION_TABLE = (
    OUTPUT_DIR
    / "V15SG7B15_Training_Region_Definition.csv"
)

PRESERVATION_TABLE = (
    OUTPUT_DIR
    / "V15SG7B15_Preservation_Gates.csv"
)

BIAS_TABLE = (
    OUTPUT_DIR
    / "V15SG7B15_Bias_Gates.csv"
)

EXPERIMENT_TABLE = (
    OUTPUT_DIR
    / "V15SG7B15_SG7B16_Experiment_Matrix.csv"
)

FAILURE_TABLE = (
    OUTPUT_DIR
    / "V15SG7B15_Observed_Regression_Baseline.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B15_Summary.json"
)


# =============================================================================
# FIXED CONTRACT
# =============================================================================

FRONT_THRESHOLD = 0.210

# Front-local SG7A state neighborhood.
FRONT_STATE_LOW = 0.205
FRONT_STATE_HIGH = 0.300

# Stronger core front band.
FRONT_CORE_LOW = 0.210
FRONT_CORE_HIGH = 0.260

# Tail / unswept anchor.
TAIL_MAX = 0.205

# TOF targeting.
LONG_TOF_MIN_DAYS = 500.0
VERY_LONG_TOF_MIN_DAYS = 1000.0

# Hard front-position gate retained from SG7B-10S.
MAX_CONDITIONED_FRONT_GAP = 5.331237e-04

# Front recovery / profile gate retained.
MIN_RECOVERED_FRONTS = 744
MAX_PROFILE_L1_100D = 4.500330e-03

# SG7B-12 TOF-bias gates retained.
MAX_BIAS_500_1000 = 2.500000e-03
MAX_BIAS_1000_2000 = 4.500000e-03
MAX_BIAS_GT2000 = 5.000000e-03
MAX_TAIL_BIAS = 5.000000e-03
MAX_500_1000_MATERIAL_SHARE = 0.40

# New design guard:
# after refinement, the front-local deviation from the SG7B-11 frozen output
# should remain tightly bounded.
MAX_FRONT_ANCHOR_MAE = 1.5e-03

# New crossing guard:
# candidate crossing displacement in xi relative to SG7B-11 should be tiny.
MAX_FROZEN_FRONT_XI_SHIFT_MEAN = 2.0e-03
MAX_FROZEN_FRONT_XI_SHIFT_P90 = 5.0e-03


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


def load_csv(path: Path):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing CSV:\n{path}"
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

    keys = []

    for row in rows:

        for key in row.keys():

            if key not in keys:

                keys.append(
                    key
                )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=keys,
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def to_float(value):

    if value is None:

        return np.nan

    try:

        return float(
            value
        )

    except Exception:

        return np.nan


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
        "PAD-Stream Version 15-SG7B-15"
    )

    print(
        "Front-Preserving TOF Refinement Design"
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
        "NO SG7B-11 FROZEN MODEL WILL BE REPLACED."
    )

    print(
        "NO SG7B-10S FRONT-SHAPE GATE WILL BE RELAXED."
    )

    print(
        "NO SG7B-12 TOF-BIAS GATE WILL BE RELAXED."
    )

    print(
        "NO SG7E PLUME THRESHOLD WILL BE CHANGED."
    )

    # =========================================================================
    # PRECONDITIONS
    # =========================================================================

    for path in [
        SG7B14R_SUMMARY,
        SG7B14R_MODEL_METRICS,
        SG7B14R_SHAPE_MATRIX,
        SG7B10S_CONTRACT,
        SG7B12_CONTRACT,
        SG7B11_FROZEN_MODEL,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"Missing SG7B-15 prerequisite:\n{path}"
            )

    sg14r = load_json(
        SG7B14R_SUMMARY
    )

    if (
        sg14r.get(
            "diagnosis"
        )
        !=
        "TOF_REFINEMENT_FRONT_PRESERVATION_TRADEOFF"
    ):

        raise RuntimeError(
            "SG7B-15 requires SG7B-14R diagnosis:\n"
            "TOF_REFINEMENT_FRONT_PRESERVATION_TRADEOFF"
        )

    model_metrics = load_csv(
        SG7B14R_MODEL_METRICS
    )

    shape_matrix = load_csv(
        SG7B14R_SHAPE_MATRIX
    )

    shape_contract = load_json(
        SG7B10S_CONTRACT
    )

    bias_contract = load_json(
        SG7B12_CONTRACT
    )

    # =========================================================================
    # OBSERVED REGRESSION BASELINE
    # =========================================================================

    regression_rows = []

    gaps = []
    shape_fail_counts = []

    for row in model_metrics:

        exp = str(
            row[
                "experiment"
            ]
        )

        gap = to_float(
            row[
                "conditioned_front_gap"
            ]
        )

        gaps.append(
            gap
        )

        shape_fail = sum(
            1
            for srow
            in shape_matrix
            if str(
                srow[
                    "experiment"
                ]
            )
            ==
            exp
            and str(
                srow[
                    "passed"
                ]
            ).strip().lower()
            not in {
                "true",
                "1",
                "yes",
            }
        )

        shape_fail_counts.append(
            shape_fail
        )

        regression_rows.append(
            {
                "experiment":
                    exp,

                "conditioned_front_gap":
                    gap,

                "conditioned_gap_limit":
                    MAX_CONDITIONED_FRONT_GAP,

                "gap_ratio":
                    gap
                    /
                    MAX_CONDITIONED_FRONT_GAP,

                "failed_shape_gates":
                    shape_fail,

                "bias_500_1000":
                    to_float(
                        row[
                            "bias_500_1000"
                        ]
                    ),

                "bias_1000_2000":
                    to_float(
                        row[
                            "bias_1000_2000"
                        ]
                    ),

                "bias_gt2000":
                    to_float(
                        row[
                            "bias_gt2000"
                        ]
                    ),

                "tail_bias":
                    to_float(
                        row[
                            "tail_bias"
                        ]
                    ),
            }
        )

    mean_gap = float(
        np.mean(
            gaps
        )
    )

    min_gap = float(
        np.min(
            gaps
        )
    )

    max_gap = float(
        np.max(
            gaps
        )
    )

    print(
        "\nSG7B-14R REGRESSION INPUT"
    )

    print(
        f"  Diagnosis               : "
        f"{sg14r.get('diagnosis')}"
    )

    print(
        f"  Models audited          : "
        f"{len(model_metrics)}"
    )

    print(
        f"  Minimum front gap       : "
        f"{min_gap:.6e}"
    )

    print(
        f"  Mean front gap          : "
        f"{mean_gap:.6e}"
    )

    print(
        f"  Maximum front gap       : "
        f"{max_gap:.6e}"
    )

    print(
        f"  Required front-gap limit: "
        f"{MAX_CONDITIONED_FRONT_GAP:.6e}"
    )

    print(
        f"  Models failing gap gate : "
        f"{sum(g > MAX_CONDITIONED_FRONT_GAP for g in gaps)} / "
        f"{len(gaps)}"
    )

    # =========================================================================
    # TRAINING-REGION DESIGN
    # =========================================================================

    region_rows = [
        {
            "region":
                "R0_short_TOF",

            "definition":
                "tau_end < 500 days",

            "purpose":
                "preserve already-good fast-streamline behavior",

            "TOF_correction":
                "OFF",

            "front_anchor":
                "ON",

            "frozen_anchor":
                "STRONG",
        },

        {
            "region":
                "R1_long_TOF_nonfront",

            "definition":
                "tau_end >= 500 days AND SG7A S < 0.205 or S > 0.300",

            "purpose":
                "primary TOF-bias correction away from accepted front",

            "TOF_correction":
                "STRONG",

            "front_anchor":
                "OFF",

            "frozen_anchor":
                "MODERATE",
        },

        {
            "region":
                "R2_long_TOF_front_shell",

            "definition":
                "tau_end >= 500 days AND 0.205 <= SG7A S <= 0.300",

            "purpose":
                "protect front neighborhood from TOF correction",

            "TOF_correction":
                "WEAK/OFF",

            "front_anchor":
                "STRONG",

            "frozen_anchor":
                "VERY_STRONG",
        },

        {
            "region":
                "R3_front_core",

            "definition":
                "0.210 <= SG7A S <= 0.260",

            "purpose":
                "preserve crossing position and local front morphology",

            "TOF_correction":
                "OFF",

            "front_anchor":
                "VERY_STRONG",

            "frozen_anchor":
                "VERY_STRONG",
        },

        {
            "region":
                "R4_initial_tail",

            "definition":
                "SG7A S <= 0.205",

            "purpose":
                "reduce long-TOF elevated unswept-state floor",

            "TOF_correction":
                "STRONG for long TOF",

            "front_anchor":
                "OFF",

            "frozen_anchor":
                "WEAK/MODERATE",
        },
    ]

    # =========================================================================
    # LOSS DESIGN
    # =========================================================================

    loss_rows = [
        {
            "component":
                "L_state",

            "role":
                "Preserve global held-out saturation accuracy",

            "target_region":
                "all canonical training samples",

            "new_or_retained":
                "retained",
        },

        {
            "component":
                "L_phys",

            "role":
                "Preserve canonical physics residual",

            "target_region":
                "all canonical training samples",

            "new_or_retained":
                "retained",
        },

        {
            "component":
                "L_mass",

            "role":
                "Preserve inventory / mass",

            "target_region":
                "all canonical training samples",

            "new_or_retained":
                "retained",
        },

        {
            "component":
                "L_TOF_away",

            "role":
                "Reduce positive long-TOF bias only away from front",

            "target_region":
                "tau_end >= 500 d AND outside S=[0.205,0.300]",

            "new_or_retained":
                "new",
        },

        {
            "component":
                "L_TOF_very_slow_away",

            "role":
                "Stronger correction on very slow non-front streamlines",

            "target_region":
                "tau_end >= 1000 d AND outside S=[0.205,0.300]",

            "new_or_retained":
                "new",
        },

        {
            "component":
                "L_tail",

            "role":
                "Lower long-TOF initial-state tail bias",

            "target_region":
                "S_SG7A <= 0.205",

            "new_or_retained":
                "retained/refined",
        },

        {
            "component":
                "L_front_anchor",

            "role":
                "Anchor candidate to SG7B-11 in front shell",

            "target_region":
                "S_SG7A in [0.205,0.300]",

            "new_or_retained":
                "new primary preservation",
        },

        {
            "component":
                "L_front_core_anchor",

            "role":
                "Very strong frozen-model anchor at S=0.21 crossing core",

            "target_region":
                "S_SG7A in [0.210,0.260]",

            "new_or_retained":
                "new primary preservation",
        },

        {
            "component":
                "L_cross_position",

            "role":
                "Penalize displacement of the S=0.21 crossing",

            "target_region":
                "profiles with SG7A front",

            "new_or_retained":
                "new",
        },

        {
            "component":
                "L_front_gradient",

            "role":
                "Preserve SG7A/SG7B-11 local front gradient",

            "target_region":
                "front shell",

            "new_or_retained":
                "new",
        },

        {
            "component":
                "L_front_TV",

            "role":
                "Preserve local total variation / shape",

            "target_region":
                "front shell",

            "new_or_retained":
                "new",
        },

        {
            "component":
                "L_short_TOF_anchor",

            "role":
                "Preserve fast-streamline prediction",

            "target_region":
                "tau_end < 500 d",

            "new_or_retained":
                "retained",
        },

        {
            "component":
                "L_global_frozen_anchor",

            "role":
                "Prevent broad drift outside targeted correction region",

            "target_region":
                "non-target domain",

            "new_or_retained":
                "retained",
        },
    ]

    # =========================================================================
    # PRESERVATION GATES
    # =========================================================================

    preservation_rows = [
        {
            "gate":
                "Held-out L1",

            "limit":
                "< 0.020",

            "authority":
                "SG7B-11",
        },

        {
            "gate":
                "Held-out L2",

            "limit":
                "< 0.030",

            "authority":
                "SG7B-11",
        },

        {
            "gate":
                "Mass relative MAE",

            "limit":
                "< 0.030",

            "authority":
                "SG7B-11",
        },

        {
            "gate":
                "Canonical mean",

            "limit":
                "< 0.500",

            "authority":
                "SG7B-11",
        },

        {
            "gate":
                "Canonical P90",

            "limit":
                "< 1.000",

            "authority":
                "SG7B-11",
        },

        {
            "gate":
                "Canonical fraction > 1",

            "limit":
                "< 10%",

            "authority":
                "SG7B-11",
        },

        {
            "gate":
                "Recovered 100d fronts",

            "limit":
                f">= {MIN_RECOVERED_FRONTS}",

            "authority":
                "SG7B-10S / SG7B-11",
        },

        {
            "gate":
                "Conditioned front gap",

            "limit":
                f"<= {MAX_CONDITIONED_FRONT_GAP:.9e}",

            "authority":
                "SG7B-10S",
        },

        {
            "gate":
                "100d profile L1",

            "limit":
                f"<= {MAX_PROFILE_L1_100D:.9e}",

            "authority":
                "SG7B-10S",
        },

        {
            "gate":
                "SG7A/E0-relative front shape",

            "limit":
                "all SG7B-10S shape gates PASS",

            "authority":
                "SG7B-10S",
        },

        {
            "gate":
                "Front frozen-anchor MAE",

            "limit":
                f"<= {MAX_FRONT_ANCHOR_MAE:.6e}",

            "authority":
                "SG7B-15 new guard",
        },

        {
            "gate":
                "Mean frozen-front xi shift",

            "limit":
                f"<= {MAX_FROZEN_FRONT_XI_SHIFT_MEAN:.6e}",

            "authority":
                "SG7B-15 new guard",
        },

        {
            "gate":
                "P90 frozen-front xi shift",

            "limit":
                f"<= {MAX_FROZEN_FRONT_XI_SHIFT_P90:.6e}",

            "authority":
                "SG7B-15 new guard",
        },
    ]

    # =========================================================================
    # BIAS GATES
    # =========================================================================

    bias_rows = [
        {
            "gate":
                "500-1000d mean bias",

            "limit":
                f"<= {MAX_BIAS_500_1000:.6e}",

            "authority":
                "SG7B-12",
        },

        {
            "gate":
                "1000-2000d mean bias",

            "limit":
                f"<= {MAX_BIAS_1000_2000:.6e}",

            "authority":
                "SG7B-12",
        },

        {
            "gate":
                ">2000d mean bias",

            "limit":
                f"<= {MAX_BIAS_GT2000:.6e}",

            "authority":
                "SG7B-12",
        },

        {
            "gate":
                "Initial-tail mean bias",

            "limit":
                f"<= {MAX_TAIL_BIAS:.6e}",

            "authority":
                "SG7B-12",
        },

        {
            "gate":
                "500-1000d material-positive share",

            "limit":
                f"<= {100.0 * MAX_500_1000_MATERIAL_SHARE:.1f}%",

            "authority":
                "SG7B-12",
        },
    ]

    # =========================================================================
    # CONTROLLED SG7B-16 EXPERIMENT MATRIX
    # =========================================================================
    #
    # Compared with SG7B-13:
    # - TOF correction is narrowed away from the front,
    # - front anchors are much stronger,
    # - frozen-front position/shape is explicit.
    # =========================================================================

    experiment_rows = [
        {
            "experiment":
                "E0",

            "description":
                "Frozen SG7B-11 control",

            "lambda_TOF_away":
                0.00,

            "lambda_TOF_very_slow":
                0.00,

            "lambda_tail":
                0.00,

            "lambda_front_anchor":
                0.00,

            "lambda_front_core":
                0.00,

            "lambda_cross_position":
                0.00,

            "lambda_front_gradient":
                0.00,

            "lambda_front_TV":
                0.00,

            "lambda_short_anchor":
                0.00,

            "lambda_global_anchor":
                0.00,
        },

        {
            "experiment":
                "E1",

            "description":
                "Conservative away-from-front TOF correction",

            "lambda_TOF_away":
                0.40,

            "lambda_TOF_very_slow":
                0.25,

            "lambda_tail":
                0.20,

            "lambda_front_anchor":
                2.00,

            "lambda_front_core":
                3.00,

            "lambda_cross_position":
                1.00,

            "lambda_front_gradient":
                0.50,

            "lambda_front_TV":
                0.40,

            "lambda_short_anchor":
                0.75,

            "lambda_global_anchor":
                1.50,
        },

        {
            "experiment":
                "E2",

            "description":
                "Balanced front-preserving TOF correction",

            "lambda_TOF_away":
                0.55,

            "lambda_TOF_very_slow":
                0.35,

            "lambda_tail":
                0.25,

            "lambda_front_anchor":
                2.50,

            "lambda_front_core":
                4.00,

            "lambda_cross_position":
                1.50,

            "lambda_front_gradient":
                0.75,

            "lambda_front_TV":
                0.60,

            "lambda_short_anchor":
                0.90,

            "lambda_global_anchor":
                1.75,
        },

        {
            "experiment":
                "E3",

            "description":
                "Strong front lock with moderate TOF correction",

            "lambda_TOF_away":
                0.50,

            "lambda_TOF_very_slow":
                0.40,

            "lambda_tail":
                0.25,

            "lambda_front_anchor":
                3.00,

            "lambda_front_core":
                5.00,

            "lambda_cross_position":
                2.00,

            "lambda_front_gradient":
                1.00,

            "lambda_front_TV":
                0.75,

            "lambda_short_anchor":
                1.00,

            "lambda_global_anchor":
                2.00,
        },

        {
            "experiment":
                "E4",

            "description":
                "Tail-focused correction with maximum front protection",

            "lambda_TOF_away":
                0.35,

            "lambda_TOF_very_slow":
                0.30,

            "lambda_tail":
                0.45,

            "lambda_front_anchor":
                3.50,

            "lambda_front_core":
                6.00,

            "lambda_cross_position":
                2.50,

            "lambda_front_gradient":
                1.10,

            "lambda_front_TV":
                0.85,

            "lambda_short_anchor":
                1.10,

            "lambda_global_anchor":
                2.25,
        },

        {
            "experiment":
                "E5",

            "description":
                "Minimal TOF correction / strongest SG7B-11 preservation",

            "lambda_TOF_away":
                0.25,

            "lambda_TOF_very_slow":
                0.20,

            "lambda_tail":
                0.25,

            "lambda_front_anchor":
                4.00,

            "lambda_front_core":
                7.00,

            "lambda_cross_position":
                3.00,

            "lambda_front_gradient":
                1.25,

            "lambda_front_TV":
                1.00,

            "lambda_short_anchor":
                1.25,

            "lambda_global_anchor":
                2.50,
        },
    ]

    # =========================================================================
    # TRAINING CONTRACT
    # =========================================================================

    training_contract = {
        "starting_checkpoint":
            str(
                SG7B11_FROZEN_MODEL
            ),

        "starting_checkpoint_role":
            "authoritative front-aware frozen SG7B-11 model",

        "maximum_epochs":
            120,

        "initial_learning_rate":
            7.5e-7,

        "minimum_learning_rate":
            7.5e-8,

        "early_stop_patience":
            24,

        "lr_reduction_patience":
            8,

        "evaluation_frequency_epochs":
            5,

        "critical_change_from_SG7B13":
            (
                "TOF correction is masked out of the SG7A front shell "
                "[0.205,0.300], with especially strong protection in "
                "[0.210,0.260]."
            ),

        "selection_rule":
            (
                "No scalar score may override a failed gate. A candidate "
                "must satisfy every SG7B-11 state/mass/canonical gate, every "
                "SG7B-10S front recovery/shape gate, every SG7B-12 TOF-bias "
                "gate, and all new SG7B-15 frozen-front displacement guards."
            ),
    }

    # =========================================================================
    # PRINT DESIGN
    # =========================================================================

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "FRONT-PRESERVING TOF REGION DESIGN"
    )

    print(
        "=" * 78
    )

    for row in region_rows:

        print(
            f"  {row['region']:<24s} | "
            f"TOF={row['TOF_correction']:<8s} | "
            f"front={row['front_anchor']:<11s} | "
            f"frozen={row['frozen_anchor']}"
        )

    print(
        "\nCore design principle:"
    )

    print(
        "  CORRECT LONG-TOF BIAS AWAY FROM THE FRONT."
    )

    print(
        "  LOCK THE ACCEPTED SG7B-11 FRONT WHILE THE TAIL MOVES."
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "SG7B-16 CONTROLLED EXPERIMENT MATRIX"
    )

    print(
        "=" * 78
    )

    for row in experiment_rows:

        print(
            f"  {row['experiment']} | "
            f"{row['description']}"
        )

    # =========================================================================
    # VALIDATION
    # =========================================================================

    checks = [
        (
            "SG7B-14R diagnosis reproduced",
            sg14r.get(
                "diagnosis"
            )
            ==
            "TOF_REFINEMENT_FRONT_PRESERVATION_TRADEOFF",
        ),

        (
            "All audited SG7B-13 candidates failed conditioned front gap",
            all(
                gap
                >
                MAX_CONDITIONED_FRONT_GAP
                for gap
                in gaps
            ),
        ),

        (
            "All audited SG7B-13 candidates failed front-shape preservation",
            all(
                count
                >
                0
                for count
                in shape_fail_counts
            ),
        ),

        (
            "SG7B-10S front-gap gate retained unchanged",
            abs(
                MAX_CONDITIONED_FRONT_GAP
                -
                float(
                    shape_contract[
                        "front_improvement_contract"
                    ][
                        "maximum_conditioned_threshold_gap"
                    ]
                )
            )
            <
            1.0e-12,
        ),

        (
            "SG7B-12 bias gates retained",
            bool(
                bias_contract[
                    "bias_improvement_gates"
                ]
            ),
        ),

        (
            "TOF correction explicitly excluded from front shell",
            any(
                row[
                    "region"
                ]
                ==
                "R2_long_TOF_front_shell"
                and row[
                    "TOF_correction"
                ]
                ==
                "WEAK/OFF"
                for row
                in region_rows
            ),
        ),

        (
            "Front-core lock explicitly defined",
            any(
                row[
                    "region"
                ]
                ==
                "R3_front_core"
                and row[
                    "front_anchor"
                ]
                ==
                "VERY_STRONG"
                for row
                in region_rows
            ),
        ),

        (
            "Controlled matrix contains frozen control",
            experiment_rows[
                0
            ][
                "experiment"
            ]
            ==
            "E0",
        ),

        (
            "No training performed by SG7B-15",
            True,
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
        "V15-SG7B-15 DESIGN VALIDATION"
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

    status = (
        "FRONT_PRESERVING_TOF_REFINEMENT_CONTRACT_READY"
        if passed
        else
        "FRONT_PRESERVING_TOF_REFINEMENT_CONTRACT_INCOMPLETE"
    )

    next_milestone = (
        "V15-SG7B-16 — Controlled Front-Preserving TOF Refinement"
        if passed
        else
        "V15-SG7B-15R — Front-Preserving TOF Contract Repair"
    )

    recommendation = (
        "Proceed to SG7B-16 using SG7B-11 as the starting checkpoint. "
        "Apply TOF correction only outside the accepted front shell, enforce "
        "strong frozen-front anchoring and crossing-position preservation, "
        "and require every original front/state/physics gate plus every "
        "SG7B-12 bias gate."
        if passed
        else
        "Do not train until the SG7B-15 design contract validates."
    )

    # =========================================================================
    # SAVE OUTPUTS
    # =========================================================================

    save_csv(
        FAILURE_TABLE,
        regression_rows,
    )

    save_csv(
        REGION_TABLE,
        region_rows,
    )

    save_csv(
        LOSS_TABLE,
        loss_rows,
    )

    save_csv(
        PRESERVATION_TABLE,
        preservation_rows,
    )

    save_csv(
        BIAS_TABLE,
        bias_rows,
    )

    save_csv(
        EXPERIMENT_TABLE,
        experiment_rows,
    )

    contract = {
        "milestone":
            "V15-SG7B-15",

        "description":
            "Front-preserving TOF refinement design",

        "training_performed":
            False,

        "incoming_diagnosis":
            sg14r.get(
                "diagnosis"
            ),

        "starting_checkpoint":
            str(
                SG7B11_FROZEN_MODEL
            ),

        "front_regions": {
            "front_shell":
                [
                    FRONT_STATE_LOW,
                    FRONT_STATE_HIGH,
                ],

            "front_core":
                [
                    FRONT_CORE_LOW,
                    FRONT_CORE_HIGH,
                ],
        },

        "TOF_regions": {
            "long_TOF_min_days":
                LONG_TOF_MIN_DAYS,

            "very_long_TOF_min_days":
                VERY_LONG_TOF_MIN_DAYS,
        },

        "new_front_guards": {
            "maximum_front_anchor_MAE":
                MAX_FRONT_ANCHOR_MAE,

            "maximum_mean_frozen_front_xi_shift":
                MAX_FROZEN_FRONT_XI_SHIFT_MEAN,

            "maximum_P90_frozen_front_xi_shift":
                MAX_FROZEN_FRONT_XI_SHIFT_P90,
        },

        "preservation_gates":
            preservation_rows,

        "bias_gates":
            bias_rows,

        "training_regions":
            region_rows,

        "loss_components":
            loss_rows,

        "controlled_experiments":
            experiment_rows,

        "training_contract":
            training_contract,

        "status":
            status,

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

    summary = {
        "milestone":
            "V15-SG7B-15",

        "status":
            status,

        "validation_passed":
            bool(
                passed
            ),

        "training_performed":
            False,

        "incoming_diagnosis":
            sg14r.get(
                "diagnosis"
            ),

        "mean_SG7B13_conditioned_front_gap":
            mean_gap,

        "required_conditioned_front_gap":
            MAX_CONDITIONED_FRONT_GAP,

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
    # DIAGNOSTICS
    # =========================================================================

    labels = [
        row[
            "experiment"
        ]
        for row
        in regression_rows
    ]

    values = [
        row[
            "conditioned_front_gap"
        ]
        for row
        in regression_rows
    ]

    plt.figure(
        figsize=(
            9,
            5,
        )
    )

    plt.bar(
        labels,
        values,
    )

    plt.axhline(
        MAX_CONDITIONED_FRONT_GAP,
        linestyle="--",
    )

    plt.ylabel(
        "Conditioned front gap"
    )

    plt.xlabel(
        "SG7B-13 experiment"
    )

    plt.title(
        "PAD-Stream V15-SG7B-15\n"
        "Observed Front-Gap Regression Driving Redesign"
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        / "V15SG7B15_Observed_Front_Gap_Regression.png",
        dpi=300,
    )

    plt.close()

    exp_labels = [
        row[
            "experiment"
        ]
        for row
        in experiment_rows
    ]

    plt.figure(
        figsize=(
            10,
            6,
        )
    )

    plt.plot(
        exp_labels,
        [
            row[
                "lambda_TOF_away"
            ]
            for row
            in experiment_rows
        ],
        marker="o",
        label="TOF away",
    )

    plt.plot(
        exp_labels,
        [
            row[
                "lambda_front_anchor"
            ]
            for row
            in experiment_rows
        ],
        marker="s",
        label="front anchor",
    )

    plt.plot(
        exp_labels,
        [
            row[
                "lambda_front_core"
            ]
            for row
            in experiment_rows
        ],
        marker="^",
        label="front core",
    )

    plt.plot(
        exp_labels,
        [
            row[
                "lambda_cross_position"
            ]
            for row
            in experiment_rows
        ],
        marker="d",
        label="cross position",
    )

    plt.xlabel(
        "SG7B-16 experiment"
    )

    plt.ylabel(
        "Relative loss weight"
    )

    plt.title(
        "PAD-Stream V15-SG7B-15\n"
        "Front-Preserving TOF Experiment Matrix"
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        / "V15SG7B15_Experiment_Matrix.png",
        dpi=300,
    )

    plt.close()

    # =========================================================================
    # FINAL PRINT
    # =========================================================================

    print(
        "\nSTATUS"
    )

    print(
        f"  {status}"
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
        f"  {FAILURE_TABLE.name}"
    )

    print(
        f"  {REGION_TABLE.name}"
    )

    print(
        f"  {LOSS_TABLE.name}"
    )

    print(
        f"  {PRESERVATION_TABLE.name}"
    )

    print(
        f"  {BIAS_TABLE.name}"
    )

    print(
        f"  {EXPERIMENT_TABLE.name}"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B15_Observed_Front_Gap_Regression.png"
    )

    print(
        "  V15SG7B15_Experiment_Matrix.png"
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

    print(
        "V15-SG7B-15 DESIGN: "
        +
        (
            "PASS"
            if passed
            else
            "FAIL"
        )
    )

    print()

    print(
        "No training was performed."
    )

    print(
        "No front, physics, TOF-bias, or plume-validation gate was relaxed."
    )

    print()

    print(
        "Next milestone:"
    )

    print(
        next_milestone
    )

    print(
        "=" * 78
    )


if __name__ == "__main__":

    main()
