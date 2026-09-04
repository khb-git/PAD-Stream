from __future__ import annotations

from pathlib import Path
import argparse
import csv
import importlib.util
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7B-10S
# SG7A-Relative Front-Shape Preservation Contract
#
# NO TRAINING.
# NO MODEL WEIGHT CHANGES.
# NO ARCHITECTURE CHANGE.
# NO EXISTING SG7B-7R FREEZE GATE RELAXATION.
# NO SG7E THRESHOLD CHANGE.
# NO CANDIDATE PROMOTION.
#
# PURPOSE
# -------
# SG7B-10R established:
#
#   SG7A monotonic violation :  0.000%
#   E0 frozen violation      : 17.637%
#   E2 violation             : 18.569%
#
# and showed that E2:
#
#   - recovered 949 / 992 SG7A 100-day fronts,
#   - reduced the front-conditioned threshold gap,
#   - improved 100-day profile L1,
#   - did not materially worsen the pre-existing local monotonicity floor,
#   - produced smaller positive-dS amplitudes than E0.
#
# Therefore SG7B-10S replaces the *new SG7B-9 absolute local-shape safeguard*
# with an SG7A-relative / E0-relative preservation contract.
#
# IMPORTANT:
# This milestone does NOT alter any original SG7B-7R freeze gate.
# It only reconciles the additional front-shape safeguard introduced during
# the post-freeze front-aware refinement branch.
#
# The preservation philosophy is:
#
#   FRONT IMPROVEMENT IS REQUIRED
#                +
#   LOCAL SHAPE MUST NOT MATERIALLY DEGRADE RELATIVE TO E0 / SG7A
#
# Candidate shape is evaluated with multiple complementary quantities:
#
#   1. local positive-dS violation fraction
#   2. P99 positive-dS amplitude
#   3. maximum positive-dS amplitude
#   4. front-band derivative MAE vs SG7A
#   5. front-band saturation L1 vs SG7A
#   6. front-band total-variation discrepancy vs SG7A
#
# The accepted preservation allowance is 10% relative to the E0-to-SG7A
# discrepancy. This is a design tolerance, not a relaxation of SG7B-7R.
# =============================================================================


# =============================================================================
# ROOT / INPUTS / OUTPUTS
# =============================================================================

ROOT = Path(__file__).resolve().parent

OUTPUT_DIR = ROOT / "output" / "V15_SG7B10S"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SG7B10_SOURCE = (
    ROOT
    / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"
)

SG7B10R_SUMMARY = (
    ROOT
    / "output"
    / "V15_SG7B10R"
    / "PAD_Stream_V15SG7B10R_Summary.json"
)

SG7B10R_DATABASE = (
    ROOT
    / "output"
    / "V15_SG7B10R"
    / "V15SG7B10R_Monotonicity_Audit.npz"
)

SG7B10R_GLOBAL = (
    ROOT
    / "output"
    / "V15_SG7B10R"
    / "V15SG7B10R_Monotonicity_Global.csv"
)

SG7B9_CONTRACT = (
    ROOT
    / "output"
    / "V15_SG7B9"
    / "V15SG7B9_Front_Aware_Refinement_Contract.json"
)

SG7B10_METRICS = (
    ROOT
    / "output"
    / "V15_SG7B10"
    / "V15SG7B10_Experiment_Metrics.csv"
)

CONTRACT_FILE = (
    OUTPUT_DIR
    / "V15SG7B10S_SG7A_Relative_Front_Shape_Contract.json"
)

SHAPE_METRICS_FILE = (
    OUTPUT_DIR
    / "V15SG7B10S_Shape_Metrics.csv"
)

GATE_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG7B10S_Preservation_Gates.csv"
)

CANDIDATE_SCREEN_FILE = (
    OUTPUT_DIR
    / "V15SG7B10S_E2_Candidate_Screen.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B10S_Summary.json"
)

DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG7B10S_Shape_Contract_Database.npz"
)


# =============================================================================
# CONTRACT DESIGN
# =============================================================================

# Relative preservation allowance for the *additional* front-shape safeguard.
#
# Candidate discrepancy may be at most 10% larger than the accepted frozen
# E0 discrepancy relative to SG7A.
SHAPE_RELATIVE_ALLOWANCE = 0.10

# Numerical floor used when a denominator is essentially zero.
EPS = 1.0e-12

# Original SG7B-9 front-recovery design requirements.
# These remain as front-improvement requirements.
MIN_FRONT_RECOVERY_FRACTION = 0.75
MIN_THRESHOLD_GAP_REDUCTION = 0.75
MAX_EARLY_PROFILE_L1_RELATIVE_REGRESSION = 0.10


# =============================================================================
# HELPERS
# =============================================================================

def load_module(path: Path, name: str):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing source module:\n{path}"
        )

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:

        raise RuntimeError(
            f"Could not import source module:\n{path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


def load_json(
    path: Path,
):

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


def load_csv(
    path: Path,
):

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


def safe_ratio(
    numerator,
    denominator,
):

    numerator = float(
        numerator
    )

    denominator = float(
        denominator
    )

    if abs(
        denominator
    ) <= EPS:

        if abs(
            numerator
        ) <= EPS:

            return 1.0

        return np.inf

    return (
        numerator
        /
        denominator
    )


def front_pair_mask(
    truth,
    front_high,
    crossing_low,
):

    truth = np.asarray(
        truth,
        dtype=np.float64,
    )

    left = (
        truth[
            :,
            :-1
        ]
    )

    right = (
        truth[
            :,
            1:
        ]
    )

    return (
        (
            np.minimum(
                left,
                right,
            )
            <=
            float(
                front_high
            )
        )
        &
        (
            np.maximum(
                left,
                right,
            )
            >=
            float(
                crossing_low
            )
        )
    )


# =============================================================================
# SHAPE METRICS
# =============================================================================

def local_shape_metrics(
    field,
    truth,
    xi,
    mask,
    monotonic_tol,
):

    field = np.asarray(
        field,
        dtype=np.float64,
    )

    truth = np.asarray(
        truth,
        dtype=np.float64,
    )

    xi = np.asarray(
        xi,
        dtype=np.float64,
    )

    d_field = (
        field[
            :,
            1:
        ]
        -
        field[
            :,
            :-1
        ]
    )

    d_truth = (
        truth[
            :,
            1:
        ]
        -
        truth[
            :,
            :-1
        ]
    )

    dxi = (
        xi[
            1:
        ]
        -
        xi[
            :-1
        ]
    )

    grad_field = (
        d_field
        /
        dxi[
            None,
            :
        ]
    )

    grad_truth = (
        d_truth
        /
        dxi[
            None,
            :
        ]
    )

    local_d = (
        d_field[
            mask
        ]
    )

    local_truth_d = (
        d_truth[
            mask
        ]
    )

    local_grad = (
        grad_field[
            mask
        ]
    )

    local_truth_grad = (
        grad_truth[
            mask
        ]
    )

    positive = (
        local_d[
            local_d
            >
            monotonic_tol
        ]
    )

    if local_d.size == 0:

        raise RuntimeError(
            "Front-local mask contains no eligible samples."
        )

    violation_fraction = float(
        np.mean(
            local_d
            >
            monotonic_tol
        )
    )

    p99_positive = (
        float(
            np.percentile(
                positive,
                99,
            )
        )
        if positive.size
        else 0.0
    )

    max_positive = (
        float(
            np.max(
                positive
            )
        )
        if positive.size
        else 0.0
    )

    gradient_mae = float(
        np.mean(
            np.abs(
                local_grad
                -
                local_truth_grad
            )
        )
    )

    # Node mask induced by the local pair mask.
    node_mask = np.zeros_like(
        field,
        dtype=bool,
    )

    node_mask[
        :,
        :-1
    ] |= mask

    node_mask[
        :,
        1:
    ] |= mask

    front_state_l1 = float(
        np.mean(
            np.abs(
                field[
                    node_mask
                ]
                -
                truth[
                    node_mask
                ]
            )
        )
    )

    # Per-profile total variation over the front-local pairs.
    tv_field = np.sum(
        np.abs(
            d_field
        )
        *
        mask,
        axis=1,
    )

    tv_truth = np.sum(
        np.abs(
            d_truth
        )
        *
        mask,
        axis=1,
    )

    tv_mae = float(
        np.mean(
            np.abs(
                tv_field
                -
                tv_truth
            )
        )
    )

    signed_gradient_bias = float(
        np.mean(
            local_grad
            -
            local_truth_grad
        )
    )

    return {
        "eligible_pairs":
            int(
                local_d.size
            ),

        "violation_fraction":
            violation_fraction,

        "positive_dS_P99":
            p99_positive,

        "positive_dS_MAX":
            max_positive,

        "gradient_MAE_vs_SG7A":
            gradient_mae,

        "front_state_L1_vs_SG7A":
            front_state_l1,

        "front_TV_MAE_vs_SG7A":
            tv_mae,

        "signed_gradient_bias":
            signed_gradient_bias,
    }


# =============================================================================
# RELATIVE PRESERVATION CONTRACT
# =============================================================================

def build_gate_rows(
    e0_metrics,
):

    one_plus = (
        1.0
        +
        SHAPE_RELATIVE_ALLOWANCE
    )

    return [
        {
            "gate":
                "violation_fraction",

            "reference":
                "E0 frozen",

            "reference_value":
                e0_metrics[
                    "violation_fraction"
                ],

            "allowance":
                SHAPE_RELATIVE_ALLOWANCE,

            "operator":
                "<=",

            "candidate_limit":
                one_plus
                *
                e0_metrics[
                    "violation_fraction"
                ],

            "interpretation":
                (
                    "Candidate may not increase the E0-to-SG7A "
                    "local monotonicity discrepancy by more than 10%."
                ),
        },

        {
            "gate":
                "positive_dS_P99",

            "reference":
                "E0 frozen",

            "reference_value":
                e0_metrics[
                    "positive_dS_P99"
                ],

            "allowance":
                SHAPE_RELATIVE_ALLOWANCE,

            "operator":
                "<=",

            "candidate_limit":
                one_plus
                *
                e0_metrics[
                    "positive_dS_P99"
                ],

            "interpretation":
                (
                    "Candidate positive-increment P99 may not exceed "
                    "110% of the frozen baseline."
                ),
        },

        {
            "gate":
                "positive_dS_MAX",

            "reference":
                "E0 frozen",

            "reference_value":
                e0_metrics[
                    "positive_dS_MAX"
                ],

            "allowance":
                SHAPE_RELATIVE_ALLOWANCE,

            "operator":
                "<=",

            "candidate_limit":
                one_plus
                *
                e0_metrics[
                    "positive_dS_MAX"
                ],

            "interpretation":
                (
                    "Candidate maximum positive increment may not exceed "
                    "110% of the frozen baseline."
                ),
        },

        {
            "gate":
                "gradient_MAE_vs_SG7A",

            "reference":
                "E0-to-SG7A",

            "reference_value":
                e0_metrics[
                    "gradient_MAE_vs_SG7A"
                ],

            "allowance":
                SHAPE_RELATIVE_ALLOWANCE,

            "operator":
                "<=",

            "candidate_limit":
                one_plus
                *
                e0_metrics[
                    "gradient_MAE_vs_SG7A"
                ],

            "interpretation":
                (
                    "Candidate front-band gradient discrepancy may not "
                    "degrade by more than 10% relative to E0."
                ),
        },

        {
            "gate":
                "front_state_L1_vs_SG7A",

            "reference":
                "E0-to-SG7A",

            "reference_value":
                e0_metrics[
                    "front_state_L1_vs_SG7A"
                ],

            "allowance":
                SHAPE_RELATIVE_ALLOWANCE,

            "operator":
                "<=",

            "candidate_limit":
                one_plus
                *
                e0_metrics[
                    "front_state_L1_vs_SG7A"
                ],

            "interpretation":
                (
                    "Candidate front-band state error may not degrade "
                    "by more than 10% relative to E0."
                ),
        },

        {
            "gate":
                "front_TV_MAE_vs_SG7A",

            "reference":
                "E0-to-SG7A",

            "reference_value":
                e0_metrics[
                    "front_TV_MAE_vs_SG7A"
                ],

            "allowance":
                SHAPE_RELATIVE_ALLOWANCE,

            "operator":
                "<=",

            "candidate_limit":
                one_plus
                *
                e0_metrics[
                    "front_TV_MAE_vs_SG7A"
                ],

            "interpretation":
                (
                    "Candidate front-band total-variation discrepancy "
                    "may not degrade by more than 10% relative to E0."
                ),
        },
    ]


def screen_candidate(
    candidate_metrics,
    gate_rows,
):

    results = []

    for gate in gate_rows:

        metric = (
            gate[
                "gate"
            ]
        )

        value = float(
            candidate_metrics[
                metric
            ]
        )

        limit = float(
            gate[
                "candidate_limit"
            ]
        )

        passed = bool(
            value
            <=
            limit
        )

        results.append(
            {
                "gate":
                    metric,

                "candidate_value":
                    value,

                "limit":
                    limit,

                "ratio_to_E0_reference":
                    safe_ratio(
                        value,
                        gate[
                            "reference_value"
                        ],
                    ),

                "pass":
                    passed,
            }
        )

    return results


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "PAD-Stream V15-SG7B-10S "
            "SG7A-relative front-shape preservation contract."
        )
    )

    parser.parse_args()

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7B-10S"
    )

    print(
        "SG7A-Relative Front-Shape Preservation Contract"
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
        "NO ORIGINAL SG7B-7R FREEZE GATE WILL BE RELAXED."
    )

    print(
        "NO SG7E THRESHOLD WILL BE CHANGED."
    )

    print(
        "NO CANDIDATE WILL BE PROMOTED BY SG7B-10S."
    )

    # =========================================================================
    # PRECONDITIONS
    # =========================================================================

    required = [
        SG7B10_SOURCE,
        SG7B10R_SUMMARY,
        SG7B10R_DATABASE,
        SG7B10R_GLOBAL,
        SG7B9_CONTRACT,
        SG7B10_METRICS,
    ]

    for path in required:

        if not path.exists():

            raise FileNotFoundError(
                f"Missing SG7B-10S prerequisite:\n{path}"
            )

    sg10r_summary = load_json(
        SG7B10R_SUMMARY
    )

    if (
        sg10r_summary.get(
            "milestone"
        )
        !=
        "V15-SG7B-10R"
    ):

        raise RuntimeError(
            "Unexpected SG7B-10R summary identity."
        )

    if (
        sg10r_summary.get(
            "diagnosis"
        )
        !=
        "PREEXISTING_MONOTONICITY_METRIC_FLOOR"
    ):

        raise RuntimeError(
            "SG7B-10S requires SG7B-10R diagnosis:\n"
            "PREEXISTING_MONOTONICITY_METRIC_FLOOR"
        )

    sg7b9_contract = load_json(
        SG7B9_CONTRACT
    )

    sg10 = load_module(
        SG7B10_SOURCE,
        "pad_stream_sg7b10_contract_source",
    )

    database = np.load(
        SG7B10R_DATABASE,
        allow_pickle=True,
    )

    truth = np.asarray(
        database[
            "truth100"
        ],
        dtype=np.float64,
    )

    e0 = np.asarray(
        database[
            "E0_frozen100"
        ],
        dtype=np.float64,
    )

    e2 = np.asarray(
        database[
            "E2_best100"
        ],
        dtype=np.float64,
    )

    xi = np.asarray(
        database[
            "xi"
        ],
        dtype=np.float64,
    )

    local_mask = front_pair_mask(
        truth,
        sg10.FRONT_HIGH,
        sg10.CROSSING_LOW,
    )

    tol = float(
        sg10.MONOTONIC_TOL
    )

    # =========================================================================
    # SHAPE METRICS
    # =========================================================================

    truth_metrics = local_shape_metrics(
        truth,
        truth,
        xi,
        local_mask,
        tol,
    )

    e0_metrics = local_shape_metrics(
        e0,
        truth,
        xi,
        local_mask,
        tol,
    )

    e2_metrics = local_shape_metrics(
        e2,
        truth,
        xi,
        local_mask,
        tol,
    )

    truth_front = sg10.front_metrics_np(
        truth,
        truth,
    )

    e0_front = sg10.front_metrics_np(
        e0,
        truth,
    )

    e2_front = sg10.front_metrics_np(
        e2,
        truth,
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "SG7A-RELATIVE SHAPE METRICS"
    )

    print(
        "=" * 78
    )

    for label, metrics in [
        (
            "SG7A truth",
            truth_metrics,
        ),

        (
            "E0 frozen",
            e0_metrics,
        ),

        (
            "E2 candidate",
            e2_metrics,
        ),
    ]:

        print(
            f"\n{label}"
        )

        print(
            f"  Local violation fraction: "
            f"{100.0 * metrics['violation_fraction']:.3f}%"
        )

        print(
            f"  Positive dS P99         : "
            f"{metrics['positive_dS_P99']:.6e}"
        )

        print(
            f"  Positive dS max         : "
            f"{metrics['positive_dS_MAX']:.6e}"
        )

        print(
            f"  Gradient MAE vs SG7A    : "
            f"{metrics['gradient_MAE_vs_SG7A']:.6e}"
        )

        print(
            f"  Front-state L1 vs SG7A  : "
            f"{metrics['front_state_L1_vs_SG7A']:.6e}"
        )

        print(
            f"  Front-TV MAE vs SG7A    : "
            f"{metrics['front_TV_MAE_vs_SG7A']:.6e}"
        )

    # =========================================================================
    # BUILD CONTRACT
    # =========================================================================

    gate_rows = build_gate_rows(
        e0_metrics
    )

    candidate_screen = screen_candidate(
        e2_metrics,
        gate_rows,
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "FRONT-SHAPE PRESERVATION GATES"
    )

    print(
        "=" * 78
    )

    for row in candidate_screen:

        print(
            f"[{'PASS' if row['pass'] else 'FAIL'}] "
            f"{row['gate']:<28s} "
            f"E2={row['candidate_value']:.6e} "
            f"limit={row['limit']:.6e} "
            f"ratio={row['ratio_to_E0_reference']:.3f}"
        )

    shape_preserved = all(
        row[
            "pass"
        ]
        for row in candidate_screen
    )

    # =========================================================================
    # FRONT IMPROVEMENT CONTRACT
    # =========================================================================

    truth_front_count = int(
        e2_front[
            "truth_front_count"
        ]
    )

    minimum_crossings = int(
        np.ceil(
            MIN_FRONT_RECOVERY_FRACTION
            *
            truth_front_count
        )
    )

    baseline_conditioned_gap = float(
        e0_front[
            "conditioned_threshold_gap_mean"
        ]
    )

    maximum_conditioned_gap = (
        (
            1.0
            -
            MIN_THRESHOLD_GAP_REDUCTION
        )
        *
        baseline_conditioned_gap
    )

    baseline_profile_l1 = float(
        e0_front[
            "profile_L1_mean"
        ]
    )

    maximum_profile_l1 = (
        (
            1.0
            +
            MAX_EARLY_PROFILE_L1_RELATIVE_REGRESSION
        )
        *
        baseline_profile_l1
    )

    front_recovery_pass = bool(
        e2_front[
            "recovered_front_count"
        ]
        >=
        minimum_crossings
    )

    gap_pass = bool(
        e2_front[
            "conditioned_threshold_gap_mean"
        ]
        <=
        maximum_conditioned_gap
    )

    profile_l1_pass = bool(
        e2_front[
            "profile_L1_mean"
        ]
        <=
        maximum_profile_l1
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "FRONT-IMPROVEMENT GATES RETAINED"
    )

    print(
        "=" * 78
    )

    print(
        f"[{'PASS' if front_recovery_pass else 'FAIL'}] "
        f"Recovered fronts >= {minimum_crossings:,} "
        f"({e2_front['recovered_front_count']:,})"
    )

    print(
        f"[{'PASS' if gap_pass else 'FAIL'}] "
        f"Conditioned gap <= {maximum_conditioned_gap:.6e} "
        f"({e2_front['conditioned_threshold_gap_mean']:.6e})"
    )

    print(
        f"[{'PASS' if profile_l1_pass else 'FAIL'}] "
        f"100d profile L1 <= {maximum_profile_l1:.6e} "
        f"({e2_front['profile_L1_mean']:.6e})"
    )

    # =========================================================================
    # CONTRACT DECISION
    # =========================================================================

    front_improvement_pass = bool(
        front_recovery_pass
        and
        gap_pass
        and
        profile_l1_pass
    )

    contract_consistent = bool(
        shape_preserved
        and
        front_improvement_pass
    )

    if contract_consistent:

        status = (
            "E2_PASSES_RELATIVE_FRONT_SHAPE_SCREEN"
        )

        recommendation = (
            "E2 satisfies the SG7A/E0-relative front-shape preservation "
            "contract while retaining the required front-recovery improvement. "
            "Do not freeze E2 here. Proceed to independent SG7B-11 validation "
            "against the complete original SG7B-7R state, mass, regional, and "
            "canonical-physics contract."
        )

        next_milestone = (
            "V15-SG7B-11 — Independent Front-Aware Candidate Validation"
        )

    else:

        status = (
            "E2_REQUIRES_SHAPE_REGULARIZED_REFINEMENT"
        )

        recommendation = (
            "E2 does not satisfy the SG7A/E0-relative front-shape preservation "
            "contract. Keep the original frozen SG7B model authoritative and "
            "resume controlled shape/gradient-regularized refinement."
        )

        next_milestone = (
            "V15-SG7B-10B — Shape-Regularized Front-Aware Refinement"
        )

    # =========================================================================
    # VALIDATION
    # =========================================================================

    checks = [
        (
            "Incoming SG7B-10R diagnosis reproduced",
            (
                sg10r_summary.get(
                    "diagnosis"
                )
                ==
                "PREEXISTING_MONOTONICITY_METRIC_FLOOR"
            ),
        ),

        (
            "SG7B-9 contract retained",
            (
                sg7b9_contract.get(
                    "milestone"
                )
                ==
                "V15-SG7B-9"
            ),
        ),

        (
            "SG7A field finite",
            bool(
                np.all(
                    np.isfinite(
                        truth
                    )
                )
            ),
        ),

        (
            "E0 field finite",
            bool(
                np.all(
                    np.isfinite(
                        e0
                    )
                )
            ),
        ),

        (
            "E2 field finite",
            bool(
                np.all(
                    np.isfinite(
                        e2
                    )
                )
            ),
        ),

        (
            "Front-local mask populated",
            bool(
                np.any(
                    local_mask
                )
            ),
        ),

        (
            "SG7A monotonic reference remains zero",
            (
                truth_metrics[
                    "violation_fraction"
                ]
                <=
                EPS
            ),
        ),

        (
            "Relative preservation gates constructed",
            (
                len(
                    gate_rows
                )
                ==
                6
            ),
        ),

        (
            "Contract decision established",
            status
            in
            {
                "E2_PASSES_RELATIVE_FRONT_SHAPE_SCREEN",
                "E2_REQUIRES_SHAPE_REGULARIZED_REFINEMENT",
            },
        ),
    ]

    audit_passed = all(
        flag
        for _, flag
        in checks
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "V15-SG7B-10S DESIGN VALIDATION"
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

    # =========================================================================
    # SAVE TABLES
    # =========================================================================

    shape_rows = []

    for label, metrics in [
        (
            "SG7A",
            truth_metrics,
        ),

        (
            "E0",
            e0_metrics,
        ),

        (
            "E2",
            e2_metrics,
        ),
    ]:

        shape_rows.append(
            {
                "field":
                    label,

                **metrics,
            }
        )

    save_csv(
        SHAPE_METRICS_FILE,
        shape_rows,
    )

    save_csv(
        GATE_TABLE_FILE,
        gate_rows,
    )

    save_csv(
        CANDIDATE_SCREEN_FILE,
        candidate_screen,
    )

    # =========================================================================
    # PLOTS
    # =========================================================================

    metric_names = [
        "violation_fraction",
        "positive_dS_P99",
        "positive_dS_MAX",
        "gradient_MAE_vs_SG7A",
        "front_state_L1_vs_SG7A",
        "front_TV_MAE_vs_SG7A",
    ]

    ratios = []

    for metric in metric_names:

        ratios.append(
            safe_ratio(
                e2_metrics[
                    metric
                ],
                e0_metrics[
                    metric
                ],
            )
        )

    fig, ax = plt.subplots(
        figsize=(
            11,
            6,
        )
    )

    ax.bar(
        metric_names,
        ratios,
    )

    ax.axhline(
        1.0,
        linestyle="--",
        label="E0 reference",
    )

    ax.axhline(
        1.0
        +
        SHAPE_RELATIVE_ALLOWANCE,
        linestyle=":",
        label="10% preservation limit",
    )

    ax.set_ylabel(
        "E2 / E0 metric ratio"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-10S\n"
        "SG7A-Relative Front-Shape Preservation"
    )

    ax.tick_params(
        axis="x",
        rotation=35,
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B10S_E2_vs_E0_Shape_Ratios.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    fig, ax = plt.subplots(
        figsize=(
            8,
            6,
        )
    )

    front_labels = [
        "E0",
        "E2",
        "Required",
    ]

    front_values = [
        e0_front[
            "recovered_front_count"
        ],
        e2_front[
            "recovered_front_count"
        ],
        minimum_crossings,
    ]

    ax.bar(
        front_labels,
        front_values,
    )

    ax.set_ylabel(
        "100-day recovered fronts"
    )

    ax.set_title(
        "PAD-Stream V15-SG7B-10S\n"
        "Front-Recovery Contract"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG7B10S_Front_Recovery_Contract.png",
        dpi=300,
    )

    plt.close(
        fig
    )

    # =========================================================================
    # DATABASE
    # =========================================================================

    np.savez_compressed(
        DATABASE_FILE,

        truth100=
            truth.astype(
                np.float32
            ),

        E0_frozen100=
            e0.astype(
                np.float32
            ),

        E2_candidate100=
            e2.astype(
                np.float32
            ),

        xi=
            xi.astype(
                np.float32
            ),

        local_mask=
            local_mask,

        shape_relative_allowance=
            np.asarray(
                [
                    SHAPE_RELATIVE_ALLOWANCE
                ],
                dtype=np.float64,
            ),
    )

    # =========================================================================
    # CONTRACT JSON
    # =========================================================================

    contract = {
        "milestone":
            "V15-SG7B-10S",

        "description":
            (
                "SG7A-relative / E0-relative front-shape preservation contract "
                "for front-aware SG7B refinement candidates"
            ),

        "training_performed":
            False,

        "model_parameters_changed":
            False,

        "architecture_changed":
            False,

        "original_SG7B7R_gate_relaxed":
            False,

        "SG7E_threshold_changed":
            False,

        "candidate_promoted":
            False,

        "incoming_diagnosis":
            sg10r_summary.get(
                "diagnosis"
            ),

        "design_principle": (
            "A front-aware candidate must materially improve the diagnosed "
            "front-recovery defect while not degrading local front-shape "
            "discrepancy by more than 10% relative to the accepted E0-to-SG7A "
            "baseline. All original SG7B-7R freeze gates remain mandatory."
        ),

        "shape_relative_allowance":
            SHAPE_RELATIVE_ALLOWANCE,

        "front_improvement_contract": {
            "minimum_recovered_fronts":
                minimum_crossings,

            "maximum_conditioned_threshold_gap":
                maximum_conditioned_gap,

            "maximum_100d_profile_L1":
                maximum_profile_l1,
        },

        "shape_preservation_gates":
            gate_rows,

        "E2_screen":
            candidate_screen,

        "E2_front_improvement": {
            "recovered_fronts":
                int(
                    e2_front[
                        "recovered_front_count"
                    ]
                ),

            "truth_fronts":
                int(
                    e2_front[
                        "truth_front_count"
                    ]
                ),

            "conditioned_threshold_gap":
                float(
                    e2_front[
                        "conditioned_threshold_gap_mean"
                    ]
                ),

            "profile_L1_100d":
                float(
                    e2_front[
                        "profile_L1_mean"
                    ]
                ),
        },

        "status":
            status,

        "recommendation":
            recommendation,

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
            "V15-SG7B-10S",

        "description":
            "SG7A-relative front-shape preservation contract",

        "audit_passed":
            bool(
                audit_passed
            ),

        "shape_preserved_by_E2":
            bool(
                shape_preserved
            ),

        "front_improvement_passed_by_E2":
            bool(
                front_improvement_pass
            ),

        "E2_contract_pass":
            bool(
                contract_consistent
            ),

        "status":
            status,

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
        "\nContract:"
    )

    print(
        f"  {CONTRACT_FILE.name}"
    )

    print(
        "\nTables:"
    )

    print(
        f"  {SHAPE_METRICS_FILE.name}"
    )

    print(
        f"  {GATE_TABLE_FILE.name}"
    )

    print(
        f"  {CANDIDATE_SCREEN_FILE.name}"
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
        "  V15SG7B10S_E2_vs_E0_Shape_Ratios.png"
    )

    print(
        "  V15SG7B10S_Front_Recovery_Contract.png"
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

    if audit_passed:

        print(
            "V15-SG7B-10S CONTRACT: PASS"
        )

        print()

        print(
            "No original SG7B-7R gate has been relaxed."
        )

        print(
            "No candidate has been promoted."
        )

        print()

        print(
            f"Status:\n  {status}"
        )

        print()

        print(
            f"Next milestone:\n  {next_milestone}"
        )

    else:

        print(
            "V15-SG7B-10S CONTRACT: INCOMPLETE"
        )

        print()

        print(
            "Do not promote E2 or resume refinement until the "
            "relative shape contract is internally consistent."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":

    main()
