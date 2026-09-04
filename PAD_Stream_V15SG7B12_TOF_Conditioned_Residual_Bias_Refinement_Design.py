from __future__ import annotations

from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7B-12
# TOF-Conditioned Residual Bias Refinement Design
#
# DESIGN-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL WEIGHTS CHANGED.
# NO ARCHITECTURE CHANGE.
# NO FROZEN MODEL REPLACED.
# NO SG7B-11 GATE RELAXED.
# NO SG7E PLUME THRESHOLD CHANGED.
#
# PURPOSE
# -------
# SG7C-R2 localized the residual positive streamline-state bias primarily to
# long-TOF streamlines:
#
#   500-1000 d   mean bias ~ 4.76e-03
#   1000-2000 d  mean bias ~ 8.82e-03
#   >2000 d      mean bias ~ 1.03e-02
#
# The 500-1000 d band alone contains ~57.25% of all materially positive-bias
# nodes. SG7C-R2 therefore diagnosed:
#
#   TOF_CONDITIONED_BIAS
#
# SG7B-12 defines a controlled refinement contract that:
#
#   1. preserves the independently frozen front-aware SG7B-11 checkpoint,
#   2. preserves all SG7B-7R / SG7B-11 canonical physics and state gates,
#   3. preserves the front-aware recovery achieved by SG7B-10 / SG7B-11,
#   4. adds TOF-conditioned bias penalties targeted to slow streamlines,
#   5. adds an initial-state tail anchor,
#   6. defines a controlled experiment matrix for SG7B-13,
#   7. performs NO retraining in this milestone.
#
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

SG7CR2_SUMMARY = (
    ROOT
    / "output"
    / "V15_SG7CR2"
    / "PAD_Stream_V15SG7CR2_Summary.json"
)

SG7CR2_TOF_TABLE = (
    ROOT
    / "output"
    / "V15_SG7CR2"
    / "V15SG7CR2_Bias_By_Terminal_TOF.csv"
)

SG7CR2_STATE_TABLE = (
    ROOT
    / "output"
    / "V15_SG7CR2"
    / "V15SG7CR2_Bias_By_SG7A_State_Band.csv"
)

SG7B11_SUMMARY = (
    ROOT
    / "output"
    / "V15_SG7B11"
    / "PAD_Stream_V15SG7B11_Summary.json"
)

SG7B11_MANIFEST = (
    ROOT
    / "output"
    / "V15_SG7B11"
    / "V15SG7B11_Front_Aware_Freeze_Manifest.json"
)

FRONT_AWARE_FROZEN_MODEL = (
    ROOT
    / "output"
    / "V15_SG7B11"
    / "V15SG7B_FRONT_AWARE_FROZEN_Model.keras"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7B12"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

CONTRACT_FILE = (
    OUTPUT_DIR
    / "V15SG7B12_TOF_Conditioned_Refinement_Contract.json"
)

LOSS_TABLE = (
    OUTPUT_DIR
    / "V15SG7B12_Loss_Component_Design.csv"
)

PRESERVATION_TABLE = (
    OUTPUT_DIR
    / "V15SG7B12_Preservation_Gates.csv"
)

BIAS_GATE_TABLE = (
    OUTPUT_DIR
    / "V15SG7B12_Bias_Improvement_Gates.csv"
)

EXPERIMENT_TABLE = (
    OUTPUT_DIR
    / "V15SG7B12_SG7B13_Experiment_Matrix.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B12_Summary.json"
)


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


def read_csv(path: Path):

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
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(rows)


def to_float(value):

    if value is None:
        return np.nan

    if isinstance(
        value,
        (
            float,
            int,
            np.floating,
            np.integer,
        ),
    ):
        return float(value)

    try:
        return float(
            str(value).strip()
        )
    except Exception:
        return np.nan


def find_row(rows, band_name):

    for row in rows:
        if row.get(
            "band"
        ) == band_name:
            return row

    raise KeyError(
        f"Could not find band '{band_name}' in table."
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
        "PAD-Stream Version 15-SG7B-12"
    )

    print(
        "TOF-Conditioned Residual Bias Refinement Design"
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
        "NO SG7B-11 GATE WILL BE RELAXED."
    )

    print(
        "NO SG7E PLUME THRESHOLD WILL BE CHANGED."
    )

    # =========================================================================
    # PRECONDITIONS
    # =========================================================================

    for path in [
        SG7CR2_SUMMARY,
        SG7CR2_TOF_TABLE,
        SG7CR2_STATE_TABLE,
        SG7B11_SUMMARY,
        SG7B11_MANIFEST,
        FRONT_AWARE_FROZEN_MODEL,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing SG7B-12 prerequisite:\n{path}"
            )

    sg7cr2 = load_json(
        SG7CR2_SUMMARY
    )

    sg7b11 = load_json(
        SG7B11_SUMMARY
    )

    manifest = load_json(
        SG7B11_MANIFEST
    )

    tof_rows = read_csv(
        SG7CR2_TOF_TABLE
    )

    state_rows = read_csv(
        SG7CR2_STATE_TABLE
    )

    if (
        sg7cr2.get(
            "diagnosis"
        )
        !=
        "TOF_CONDITIONED_BIAS"
    ):
        raise RuntimeError(
            "SG7B-12 requires SG7C-R2 diagnosis:\n"
            "TOF_CONDITIONED_BIAS"
        )

    if (
        sg7b11.get(
            "status"
        )
        !=
        "FRONT_AWARE_PI_RNN_FROZEN"
    ):
        raise RuntimeError(
            "SG7B-12 requires SG7B-11 frozen front-aware checkpoint."
        )

    # =========================================================================
    # INGEST DIAGNOSTIC BASELINE
    # =========================================================================

    tof_500_1000 = find_row(
        tof_rows,
        "500-1000d",
    )

    tof_1000_2000 = find_row(
        tof_rows,
        "1000-2000d",
    )

    tof_gt_2000 = find_row(
        tof_rows,
        ">2000d",
    )

    tail_row = find_row(
        state_rows,
        "initial_tail",
    )

    front_row = find_row(
        state_rows,
        "front_band",
    )

    baseline = {
        "TOF_500_1000_mean_bias":
            to_float(
                tof_500_1000.get(
                    "mean_bias"
                )
            ),

        "TOF_500_1000_material_share":
            to_float(
                tof_500_1000.get(
                    "share_of_all_material_positive_nodes"
                )
            ),

        "TOF_1000_2000_mean_bias":
            to_float(
                tof_1000_2000.get(
                    "mean_bias"
                )
            ),

        "TOF_gt_2000_mean_bias":
            to_float(
                tof_gt_2000.get(
                    "mean_bias"
                )
            ),

        "tail_mean_bias":
            to_float(
                tail_row.get(
                    "mean_bias"
                )
            ),

        "tail_material_share":
            to_float(
                tail_row.get(
                    "share_of_all_material_positive_nodes"
                )
            ),

        "front_mean_bias":
            to_float(
                front_row.get(
                    "mean_bias"
                )
            ),
    }

    print(
        "\nSG7C-R2 DIAGNOSTIC INPUT"
    )

    print(
        f"  Diagnosis               : "
        f"{sg7cr2.get('diagnosis')}"
    )

    print(
        f"  500-1000d mean bias     : "
        f"{baseline['TOF_500_1000_mean_bias']:.6e}"
    )

    print(
        f"  500-1000d material share: "
        f"{100.0 * baseline['TOF_500_1000_material_share']:.2f}%"
    )

    print(
        f"  1000-2000d mean bias    : "
        f"{baseline['TOF_1000_2000_mean_bias']:.6e}"
    )

    print(
        f"  >2000d mean bias        : "
        f"{baseline['TOF_gt_2000_mean_bias']:.6e}"
    )

    print(
        f"  Initial-tail mean bias  : "
        f"{baseline['tail_mean_bias']:.6e}"
    )

    print(
        f"  Front-band mean bias    : "
        f"{baseline['front_mean_bias']:.6e}"
    )

    # =========================================================================
    # LOSS DESIGN
    # =========================================================================

    loss_rows = [
        {
            "component":
                "L_state",

            "role":
                "Preserve global saturation accuracy",

            "target":
                "All held-out profiles",

            "weight_role":
                "mandatory base term",
        },

        {
            "component":
                "L_phys",

            "role":
                "Preserve canonical SG7A-relative physics contract",

            "target":
                "Held-out physics residual",

            "weight_role":
                "mandatory base term",
        },

        {
            "component":
                "L_mass",

            "role":
                "Preserve displaced-phase inventory accuracy",

            "target":
                "Held-out mass/inventory",

            "weight_role":
                "mandatory base term",
        },

        {
            "component":
                "L_front",

            "role":
                "Preserve recovered S=0.21 fronts",

            "target":
                "Early front-zone samples",

            "weight_role":
                "retain front-aware contract",
        },

        {
            "component":
                "L_shape",

            "role":
                "Preserve SG7A/E0-relative front shape",

            "target":
                "Front-local gradients / TV",

            "weight_role":
                "retain front-aware contract",
        },

        {
            "component":
                "L_TOF_bias",

            "role":
                "Penalize positive PI-RNN bias on slow streamlines",

            "target":
                "tau_end >= 500 days",

            "weight_role":
                "new primary correction",
        },

        {
            "component":
                "L_TOF_slow",

            "role":
                "Strongly penalize positive state floor on very slow streamlines",

            "target":
                "tau_end >= 1000 days",

            "weight_role":
                "new strong correction",
        },

        {
            "component":
                "L_tail_anchor",

            "role":
                "Anchor unswept PI-RNN state to SG7A / initial saturation",

            "target":
                "SG7A S <= 0.205",

            "weight_role":
                "new secondary correction",
        },

        {
            "component":
                "L_short_TOF_anchor",

            "role":
                "Prevent degradation on fast streamlines already slightly negatively biased",

            "target":
                "tau_end <= 500 days",

            "weight_role":
                "new preservation anchor",
        },

        {
            "component":
                "L_frozen_anchor",

            "role":
                "Keep candidate close to SG7B-11 away from targeted regions",

            "target":
                "non-target samples",

            "weight_role":
                "new preservation anchor",
        },
    ]

    # =========================================================================
    # PRESERVATION CONTRACT
    # =========================================================================

    preservation_rows = [
        {
            "gate":
                "Held-out L1",

            "limit":
                "< 0.020",

            "source":
                "SG7B-7R / SG7B-11",

            "status":
                "mandatory",
        },

        {
            "gate":
                "Held-out L2",

            "limit":
                "< 0.030",

            "source":
                "SG7B-7R / SG7B-11",

            "status":
                "mandatory",
        },

        {
            "gate":
                "Mass relative MAE",

            "limit":
                "< 0.030",

            "source":
                "SG7B-7R / SG7B-11",

            "status":
                "mandatory",
        },

        {
            "gate":
                "Canonical mean",

            "limit":
                "< 0.500",

            "source":
                "SG7B-6H / SG7B-11",

            "status":
                "mandatory",
        },

        {
            "gate":
                "Canonical P90",

            "limit":
                "< 1.000",

            "source":
                "SG7B-6H / SG7B-11",

            "status":
                "mandatory",
        },

        {
            "gate":
                "Canonical fraction > 1",

            "limit":
                "< 10%",

            "source":
                "SG7B-6H / SG7B-11",

            "status":
                "mandatory",
        },

        {
            "gate":
                "Injector-region L1",

            "limit":
                "< 0.015",

            "source":
                "SG7B-7R / SG7B-11",

            "status":
                "mandatory",
        },

        {
            "gate":
                "Front-region L1",

            "limit":
                "< 0.030",

            "source":
                "SG7B-7R / SG7B-11",

            "status":
                "mandatory",
        },

        {
            "gate":
                "Early-time L1",

            "limit":
                "< 0.020",

            "source":
                "SG7B-7R / SG7B-11",

            "status":
                "mandatory",
        },

        {
            "gate":
                "Late-time L1",

            "limit":
                "< 0.025",

            "source":
                "SG7B-7R / SG7B-11",

            "status":
                "mandatory",
        },

        {
            "gate":
                "Recovered 100d fronts",

            "limit":
                ">= 744",

            "source":
                "SG7B-9 / SG7B-11",

            "status":
                "mandatory",
        },

        {
            "gate":
                "100d conditioned front gap",

            "limit":
                "<= SG7B-10S contract",

            "source":
                "SG7B-10S / SG7B-11",

            "status":
                "mandatory",
        },

        {
            "gate":
                "100d profile L1",

            "limit":
                "<= SG7B-10S contract",

            "source":
                "SG7B-10S / SG7B-11",

            "status":
                "mandatory",
        },

        {
            "gate":
                "SG7A/E0-relative front shape",

            "limit":
                "all SG7B-10S gates pass",

            "source":
                "SG7B-10S / SG7B-11",

            "status":
                "mandatory",
        },
    ]

    # =========================================================================
    # NEW BIAS-IMPROVEMENT CONTRACT
    # =========================================================================

    # Design goals are deliberately relative to SG7C-R2 diagnostics.
    target_500_1000 = min(
        2.5e-3,
        0.55
        *
        baseline[
            "TOF_500_1000_mean_bias"
        ],
    )

    target_1000_2000 = min(
        4.5e-3,
        0.55
        *
        baseline[
            "TOF_1000_2000_mean_bias"
        ],
    )

    target_gt_2000 = min(
        5.0e-3,
        0.55
        *
        baseline[
            "TOF_gt_2000_mean_bias"
        ],
    )

    target_tail = min(
        5.0e-3,
        0.55
        *
        baseline[
            "tail_mean_bias"
        ],
    )

    bias_gate_rows = [
        {
            "gate":
                "500-1000d mean positive bias",

            "baseline":
                baseline[
                    "TOF_500_1000_mean_bias"
                ],

            "target_limit":
                target_500_1000,

            "improvement_required":
                ">=45% reduction",
        },

        {
            "gate":
                "1000-2000d mean positive bias",

            "baseline":
                baseline[
                    "TOF_1000_2000_mean_bias"
                ],

            "target_limit":
                target_1000_2000,

            "improvement_required":
                ">=45% reduction",
        },

        {
            "gate":
                ">2000d mean positive bias",

            "baseline":
                baseline[
                    "TOF_gt_2000_mean_bias"
                ],

            "target_limit":
                target_gt_2000,

            "improvement_required":
                ">=45% reduction",
        },

        {
            "gate":
                "Initial-tail mean positive bias",

            "baseline":
                baseline[
                    "tail_mean_bias"
                ],

            "target_limit":
                target_tail,

            "improvement_required":
                ">=45% reduction",
        },

        {
            "gate":
                "500-1000d material-positive-node share",

            "baseline":
                baseline[
                    "TOF_500_1000_material_share"
                ],

            "target_limit":
                0.40,

            "improvement_required":
                "reduce dominant TOF concentration",
        },
    ]

    # =========================================================================
    # CONTROLLED SG7B-13 EXPERIMENT MATRIX
    # =========================================================================

    experiment_rows = [
        {
            "experiment":
                "E0",

            "description":
                "Frozen SG7B-11 control",

            "lambda_TOF_bias":
                0.0,

            "lambda_TOF_slow":
                0.0,

            "lambda_tail":
                0.0,

            "lambda_short_anchor":
                0.0,

            "lambda_frozen_anchor":
                0.0,
        },

        {
            "experiment":
                "E1",

            "description":
                "Moderate TOF-bias correction",

            "lambda_TOF_bias":
                0.50,

            "lambda_TOF_slow":
                0.25,

            "lambda_tail":
                0.10,

            "lambda_short_anchor":
                0.25,

            "lambda_frozen_anchor":
                1.00,
        },

        {
            "experiment":
                "E2",

            "description":
                "Balanced TOF + tail correction",

            "lambda_TOF_bias":
                0.75,

            "lambda_TOF_slow":
                0.50,

            "lambda_tail":
                0.25,

            "lambda_short_anchor":
                0.35,

            "lambda_frozen_anchor":
                1.00,
        },

        {
            "experiment":
                "E3",

            "description":
                "Strong slow-streamline correction",

            "lambda_TOF_bias":
                0.75,

            "lambda_TOF_slow":
                0.85,

            "lambda_tail":
                0.25,

            "lambda_short_anchor":
                0.40,

            "lambda_frozen_anchor":
                1.25,
        },

        {
            "experiment":
                "E4",

            "description":
                "Strong tail-anchor correction",

            "lambda_TOF_bias":
                0.70,

            "lambda_TOF_slow":
                0.55,

            "lambda_tail":
                0.55,

            "lambda_short_anchor":
                0.40,

            "lambda_frozen_anchor":
                1.25,
        },

        {
            "experiment":
                "E5",

            "description":
                "Conservative bias correction",

            "lambda_TOF_bias":
                0.45,

            "lambda_TOF_slow":
                0.35,

            "lambda_tail":
                0.20,

            "lambda_short_anchor":
                0.50,

            "lambda_frozen_anchor":
                1.50,
        },
    ]

    # =========================================================================
    # TRAINING CONTRACT FOR SG7B-13
    # =========================================================================

    training_contract = {
        "starting_checkpoint":
            str(
                FRONT_AWARE_FROZEN_MODEL
            ),

        "maximum_epochs":
            140,

        "initial_learning_rate":
            1.5e-6,

        "minimum_learning_rate":
            1.5e-7,

        "early_stop_patience":
            28,

        "lr_reduction_patience":
            10,

        "batch_strategy":
            "retain SG7B-10 batching; add TOF-conditioned sample weights",

        "targeted_TOF_weighting": {
            "<=500d":
                1.0,

            "500-1000d":
                3.0,

            "1000-2000d":
                4.0,

            ">2000d":
                4.0,
        },

        "state_region_weighting": {
            "initial_tail_S<=0.205":
                3.0,

            "front_band_0.21_to_0.30":
                1.5,

            "swept_high":
                1.0,
        },

        "selection_rule":
            (
                "Candidate must satisfy every original SG7B-11 preservation "
                "gate AND every SG7B-12 bias-improvement gate. No scalar "
                "training score may override a failed mandatory gate."
            ),
    }

    # =========================================================================
    # PRINT CONTRACT
    # =========================================================================

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "TOF-CONDITIONED LOSS DESIGN"
    )

    print(
        "=" * 78
    )

    print(
        "\nPreserved terms:"
    )

    print(
        "  L_state                 : global state accuracy"
    )

    print(
        "  L_phys                  : canonical SG7A-relative physics"
    )

    print(
        "  L_mass                  : inventory accuracy"
    )

    print(
        "  L_front                 : recovered front preservation"
    )

    print(
        "  L_shape                 : front-shape preservation"
    )

    print(
        "\nNew targeted terms:"
    )

    print(
        "  L_TOF_bias              : reduce positive bias for tau_end >= 500 d"
    )

    print(
        "  L_TOF_slow              : stronger correction for tau_end >= 1000 d"
    )

    print(
        "  L_tail_anchor           : anchor SG7A initial-state tail"
    )

    print(
        "  L_short_TOF_anchor      : preserve already-good fast streamlines"
    )

    print(
        "  L_frozen_anchor         : preserve SG7B-11 outside targeted regions"
    )

    print(
        "\nConceptual objective:"
    )

    print(
        "  L_total ="
    )

    print(
        "      L_state + L_phys + L_mass + L_front + L_shape"
    )

    print(
        "    + lambda_TOF_bias   * L_TOF_bias"
    )

    print(
        "    + lambda_TOF_slow   * L_TOF_slow"
    )

    print(
        "    + lambda_tail       * L_tail_anchor"
    )

    print(
        "    + lambda_short      * L_short_TOF_anchor"
    )

    print(
        "    + lambda_anchor     * L_frozen_anchor"
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "SG7B-13 BIAS-IMPROVEMENT CONTRACT"
    )

    print(
        "=" * 78
    )

    for row in bias_gate_rows:

        print(
            f"  {row['gate']:<38s} "
            f"baseline={row['baseline']:.6e} "
            f"target<={row['target_limit']:.6e}"
        )

    print(
        "\nAll SG7B-11 front/state/mass/canonical-physics gates remain mandatory."
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "SG7B-13 CONTROLLED EXPERIMENT MATRIX"
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
    # SAVE OUTPUTS
    # =========================================================================

    save_csv(
        LOSS_TABLE,
        loss_rows,
    )

    save_csv(
        PRESERVATION_TABLE,
        preservation_rows,
    )

    save_csv(
        BIAS_GATE_TABLE,
        bias_gate_rows,
    )

    save_csv(
        EXPERIMENT_TABLE,
        experiment_rows,
    )

    contract = {
        "milestone":
            "V15-SG7B-12",

        "description":
            "TOF-conditioned residual bias refinement design",

        "training_performed":
            False,

        "weights_changed":
            False,

        "architecture_changed":
            False,

        "frozen_model_replaced":
            False,

        "SG7B11_gates_relaxed":
            False,

        "SG7E_threshold_changed":
            False,

        "incoming_diagnosis":
            sg7cr2.get(
                "diagnosis"
            ),

        "starting_checkpoint":
            str(
                FRONT_AWARE_FROZEN_MODEL
            ),

        "starting_checkpoint_sha256":
            manifest.get(
                "front_aware_frozen_sha256"
            ),

        "diagnostic_baseline":
            baseline,

        "new_loss_terms": {
            "L_TOF_bias":
                "positive-bias penalty for tau_end >= 500 days",

            "L_TOF_slow":
                "strong positive-bias penalty for tau_end >= 1000 days",

            "L_tail_anchor":
                "anchor SG7A initial-state tail S<=0.205",

            "L_short_TOF_anchor":
                "preserve fast-streamline behavior",

            "L_frozen_anchor":
                "preserve SG7B-11 away from targeted regions",
        },

        "bias_improvement_gates":
            bias_gate_rows,

        "preservation_gates":
            preservation_rows,

        "training_contract":
            training_contract,

        "controlled_experiments":
            experiment_rows,

        "next_milestone":
            "V15-SG7B-13 — Controlled TOF-Conditioned Residual Bias Refinement",
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
    # PLOTS
    # =========================================================================

    fig, ax = plt.subplots(
        figsize=(
            10,
            6,
        )
    )

    labels = [
        "500-1000d",
        "1000-2000d",
        ">2000d",
        "initial tail",
    ]

    baseline_values = [
        baseline[
            "TOF_500_1000_mean_bias"
        ],
        baseline[
            "TOF_1000_2000_mean_bias"
        ],
        baseline[
            "TOF_gt_2000_mean_bias"
        ],
        baseline[
            "tail_mean_bias"
        ],
    ]

    target_values = [
        target_500_1000,
        target_1000_2000,
        target_gt_2000,
        target_tail,
    ]

    x = np.arange(
        len(
            labels
        )
    )

    width = 0.38

    ax.bar(
        x - width / 2,
        baseline_values,
        width,
        label="SG7C-R2 baseline",
    )

    ax.bar(
        x + width / 2,
        target_values,
        width,
        label="SG7B-13 target",
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        labels
    )

    ax.set_ylabel(
        "Mean positive bias"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-12\n"
        "TOF-Conditioned Bias Reduction Contract"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B12_Bias_Reduction_Targets.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    fig, ax = plt.subplots(
        figsize=(
            11,
            6,
        )
    )

    experiments = [
        row[
            "experiment"
        ]
        for row
        in experiment_rows
    ]

    ax.plot(
        experiments,
        [
            row[
                "lambda_TOF_bias"
            ]
            for row
            in experiment_rows
        ],
        marker="o",
        label="lambda_TOF_bias",
    )

    ax.plot(
        experiments,
        [
            row[
                "lambda_TOF_slow"
            ]
            for row
            in experiment_rows
        ],
        marker="s",
        label="lambda_TOF_slow",
    )

    ax.plot(
        experiments,
        [
            row[
                "lambda_tail"
            ]
            for row
            in experiment_rows
        ],
        marker="^",
        label="lambda_tail",
    )

    ax.plot(
        experiments,
        [
            row[
                "lambda_frozen_anchor"
            ]
            for row
            in experiment_rows
        ],
        marker="d",
        label="lambda_frozen_anchor",
    )

    ax.set_xlabel(
        "Controlled SG7B-13 experiment"
    )

    ax.set_ylabel(
        "Relative loss weight"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-12\n"
        "Controlled TOF-Conditioned Experiment Matrix"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B12_Experiment_Matrix.png",
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
            "SG7C-R2 diagnosis = TOF_CONDITIONED_BIAS",
            sg7cr2.get(
                "diagnosis"
            )
            ==
            "TOF_CONDITIONED_BIAS",
        ),

        (
            "SG7B-11 front-aware checkpoint remains frozen",
            sg7b11.get(
                "status"
            )
            ==
            "FRONT_AWARE_PI_RNN_FROZEN",
        ),

        (
            "Starting frozen model exists",
            FRONT_AWARE_FROZEN_MODEL.exists(),
        ),

        (
            "Slow-TOF positive bias confirmed",
            baseline[
                "TOF_1000_2000_mean_bias"
            ]
            >
            0.0
            and
            baseline[
                "TOF_gt_2000_mean_bias"
            ]
            >
            0.0,
        ),

        (
            "500-1000d dominant material-bias share confirmed",
            baseline[
                "TOF_500_1000_material_share"
            ]
            >
            0.50,
        ),

        (
            "Bias targets stricter than baseline",
            target_500_1000
            <
            baseline[
                "TOF_500_1000_mean_bias"
            ]
            and
            target_1000_2000
            <
            baseline[
                "TOF_1000_2000_mean_bias"
            ]
            and
            target_gt_2000
            <
            baseline[
                "TOF_gt_2000_mean_bias"
            ]
            and
            target_tail
            <
            baseline[
                "tail_mean_bias"
            ],
        ),

        (
            "Preservation contract retains canonical physics gates",
            any(
                row[
                    "gate"
                ]
                ==
                "Canonical mean"
                for row
                in preservation_rows
            )
            and
            any(
                row[
                    "gate"
                ]
                ==
                "Canonical P90"
                for row
                in preservation_rows
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
            "No training performed by SG7B-12",
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
        "V15-SG7B-12 DESIGN VALIDATION"
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
        "TOF_CONDITIONED_REFINEMENT_CONTRACT_READY"
        if passed
        else
        "TOF_CONDITIONED_REFINEMENT_CONTRACT_INCOMPLETE"
    )

    next_milestone = (
        "V15-SG7B-13 — Controlled TOF-Conditioned Residual Bias Refinement"
        if passed
        else
        "V15-SG7B-12R — TOF-Conditioned Contract Repair"
    )

    recommendation = (
        "Proceed to a controlled SG7B-13 refinement branch starting from the "
        "front-aware frozen SG7B-11 checkpoint. Candidate selection must satisfy "
        "every original SG7B-11 preservation gate together with the new "
        "TOF-conditioned bias-reduction contract."
        if passed
        else
        "Do not train until the SG7B-12 design contract validates."
    )

    summary = {
        "milestone":
            "V15-SG7B-12",

        "description":
            "TOF-conditioned residual bias refinement design",

        "training_performed":
            False,

        "incoming_diagnosis":
            sg7cr2.get(
                "diagnosis"
            ),

        "status":
            status,

        "validation_passed":
            bool(
                passed
            ),

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
        f"  {LOSS_TABLE.name}"
    )

    print(
        f"  {PRESERVATION_TABLE.name}"
    )

    print(
        f"  {BIAS_GATE_TABLE.name}"
    )

    print(
        f"  {EXPERIMENT_TABLE.name}"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG7B12_Bias_Reduction_Targets.png"
    )

    print(
        "  V15SG7B12_Experiment_Matrix.png"
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
            "V15-SG7B-12 DESIGN: PASS"
        )

        print()

        print(
            "STATUS:"
        )

        print(
            "TOF-CONDITIONED RESIDUAL-BIAS REFINEMENT CONTRACT ESTABLISHED"
        )

        print()

        print(
            "The SG7B-11 front-aware frozen model remains authoritative."
        )

        print(
            "No retraining has occurred."
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7B-13 — Controlled TOF-Conditioned Residual Bias Refinement"
        )

    else:

        print(
            "V15-SG7B-12 DESIGN: FAIL"
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":

    main()
