#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2Z-XPU
B2Y Warmed Performance Interpretation
+ Equivalence-Preserving Derivative-Engine Optimization Protocol Freeze

Purpose
-------
Freeze the operational interpretation of the warmed B2Y benchmark and define
the first implementation-only optimization branch for the corrected Stage-2
PI-RNN.

NO TRAINING.
NO OPTIMIZER.
NO OPTIMIZER STEP.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

B2Y certified steady-state evidence
-----------------------------------
Reference microbatch:
    128

Warmed uninstrumented corrected repeats:
    23.100 s
    20.541 s
    28.232 s

Corrected median:
    23.100 s

Matched first-order control median:
    0.109 s

Corrected/control warmed median ratio:
    211.653x

Corrected median throughput:
    5.541 profiles/s

Diagnostic 800-epoch projection:
    19.250 days

Warmed synchronized corrected stage profile:
    model forward                    0.026 s
    local recurrent derivatives      6.672 s
    corrected physics algebra        0.004 s
    nonphysics + total assembly      0.001 s
    total backward                  15.704 s

Therefore the dominant computational burden is the recurrent input-derivative
graph and backward through that graph, not model forward or conservative
residual algebra.

Development decision
--------------------
An equivalence-preserving derivative-engine optimization branch is required
before freezing the COMP-XPU-005 execution contract.

This is an operational development decision, not a scientific acceptance
threshold.

First authorized optimization
-----------------------------
V16E-1B2AA-XPU

Replace ONLY the implementation of the local recurrent derivative extraction.

Frozen baseline engine:
    for j in range(T):
        autograd.grad(
            S_pred[:,j,:].sum(),
            (xi, p11),
            create_graph=True,
            retain_graph=True
        )

        N_xi[:,j] = dN_j / dxi_j
        N_tD[:,j] = dN_j / dp11[tD]
        N_X[:,j]  = dN_j / dp11[xD_star]

Prospective optimized engine:
    one batched vector-Jacobian-product call using

        torch.autograd.grad(
            outputs=S_pred,
            inputs=(xi,p11),
            grad_outputs=V,
            create_graph=True,
            retain_graph=True,
            is_grads_batched=True
        )

    where V contains the 64 one-hot sequence-output cotangents.

For output node j, the batched result must recover exactly the same local
quantities:
    N_xi(j) = dN_j/dxi_j
    N_tD(j) = dN_j/dp11[tD]
    N_X(j)  = dN_j/dp11[xD_star]

Scientific graph frozen
-----------------------
The following MUST NOT change:
    * COMP-XPU-004 frozen baseline weights
    * [xi, eta] sequence architecture
    * raw physical 11-D p11
    * physical Nc
    * Rankine-Hugoniot Xdot closure
    * corrected conservative moving-fan residual
    * fractional-flow physics
    * all loss terms and weights
    * dataset and exact reference rows
    * no OOD
    * no TOF

B2AA required verification
--------------------------
No optimizer and no weight update.

On the exact B2Y reference microbatch=128 and exact same rows:

1. Baseline loop derivatives:
       N_xi_loop
       N_tD_loop
       N_X_loop

2. Batched-VJP derivatives:
       N_xi_batched
       N_tD_batched
       N_X_batched

3. Compare:
       derivative tensors
       corrected residual
       physics loss
       complete total loss
       parameter gradients after backward

4. Use only a float32-machine-epsilon-derived computational identity budget
   for numerical equivalence. This is NOT a scientific model threshold.

5. Benchmark warmed performance:
       baseline loop:
           1 warm-up + 3 measured repeats
       batched VJP:
           1 warm-up + 3 measured repeats

6. Record:
       median / mean wall time
       profiles/s
       peak XPU memory if available
       parameter-gradient equivalence
       weight equality
       checkpoint SHA equality

7. If is_grads_batched=True is unsupported by the Intel-XPU/LSTM path, record
   the exact runtime failure and stop. Do not silently fall back or alter the
   scientific model.

Only after B2AA may B2AB interpret whether the optimized engine is equivalent
and useful enough to become the COMP-XPU-005 execution implementation.

COMP-XPU-005 full training remains blocked.
B3 remains blocked.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import sys


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2Z-XPU"

# =============================================================================
# Frozen authorities
# =============================================================================

DATASET = (
    R / "output" / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

COMP004_DIR = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-004"
)
COMP004_CHECKPOINT = COMP004_DIR / "V16E_BLREP_COMP_XPU_004.pt"
COMP004_CHECKPOINT_SHA = "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69"

# Exact corrected graph authority.
B2S_SOURCE = (
    R
    / "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
)
B2S_SOURCE_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"

# B2U exact reference rows.
B2U_DIR = (
    R / "output"
    / "V16_E1B2U_XPU_EXTENDED_CORRECTED_RESIDUAL_THROUGHPUT"
)
B2U_RESULTS = B2U_DIR / "V16E1B2U_Extended_Throughput_Memory_Results.json"
B2U_RESULTS_SHA = "e71f398c88feee2260c50109055b917103e76800365954823f320457a0d30075"

# B2Y authority.
B2Y_SOURCE = (
    R
    / "PAD_Stream_V16E1B2Y_XPU_Warmed_Steady_State_Exact_Graph_Benchmark.py"
)
B2Y_SOURCE_SHA = "fab7d1fccf3ff01fd20c146617be9e4a1766183073a3e242fceca75d441bb782"

B2Y_DIR = (
    R / "output"
    / "V16_E1B2Y_XPU_WARMED_STEADY_STATE_EXACT_GRAPH_BENCHMARK"
)
B2Y_RESULTS = B2Y_DIR / "V16E1B2Y_Warmed_Steady_State_Results.json"
B2Y_DECISION = B2Y_DIR / "V16E1B2Y_Steady_State_Performance_Decision.json"
B2Y_SUMMARY = B2Y_DIR / "PAD_Stream_V16E1B2Y_XPU_Summary.json"

B2Y_RESULTS_SHA = "32d5a9a1e8c0970a497fe81dffb5c877d8ac23439a463d701e1d9b0bcd163b16"
B2Y_DECISION_SHA = "892295d38ecdfd74977bd4c9051ede77adda4400bc4e24be01f2c0fd008be26d"
B2Y_SUMMARY_SHA = "2ad87ac6691f43f90fe981ab6aebbdf39e2f34ab478c7668b290f52d2ab47114"

EXPECTED_B2Y_STATUS = (
    "V16E1B2Y_XPU_WARMED_STEADY_STATE_EXACT_CORRECTED_GRAPH_BENCHMARK_COMPLETE_"
    "MICROBATCH_128_EXACT_B2S_GRAPH_AND_EXACT_B2U_B2W_REFERENCE_ROWS_PRESERVED_"
    "ONE_UNMEASURED_WARMUP_PLUS_THREE_UNINSTRUMENTED_MEASURED_CORRECTED_REPEATS_COMPLETE_"
    "ONE_UNMEASURED_WARMUP_PLUS_THREE_UNINSTRUMENTED_MEASURED_MATCHED_FIRST_ORDER_CONTROL_REPEATS_COMPLETE_"
    "WARMED_SYNCHRONIZED_CORRECTED_STAGE_PROFILE_COMPLETE_"
    "STEADY_STATE_MEDIAN_MEAN_THROUGHPUT_CORRECTED_CONTROL_RATIOS_AND_DIAGNOSTIC_FULL_RUN_PROJECTION_FROZEN_"
    "FINITE_GRADIENTS_NO_WEIGHT_CHANGE_NO_OPTIMIZER_COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_"
    "B2Z_PERFORMANCE_INTERPRETATION_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_B3_NOT_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2Z_XPU_B2Y_INTERPRETATION_DERIVATIVE_ENGINE_OPTIMIZATION_PROTOCOL"
)
OUT.mkdir(parents=True, exist_ok=True)

INTERPRETATION = OUT / "V16E1B2Z_B2Y_Performance_Interpretation.json"
PROTOCOL = OUT / "V16E1B2Z_B2AA_Batched_VJP_Optimization_Protocol.json"
HANDOFF = OUT / "V16E1B2Z_B2AA_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2Z_XPU_Summary.json"

REFERENCE_MICROBATCH = 128
EXPECTED_MEASURED_REPEATS = 3
FLOAT32_EPS = 1.1920928955078125e-07
IDENTITY_EPS_MULTIPLIER = 1024.0


# =============================================================================
# Helpers
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def exact(path: Path, expected: str) -> bool:
    return path.exists() and path.is_file() and sha256(path) == expected


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def finite(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2Z-XPU")
    print("B2Y Warmed Performance Interpretation")
    print("+ Equivalence-Preserving Derivative-Engine Optimization Protocol Freeze")
    print("=" * 80)
    print("PROTOCOL ONLY — NO TRAINING — NO OPTIMIZER.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2Z summary already exists; refusing overwrite."
        )

    gates = {
        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),

        "COMP004_checkpoint_SHA_exact":
            exact(COMP004_CHECKPOINT, COMP004_CHECKPOINT_SHA),

        "B2S_source_SHA_exact":
            exact(B2S_SOURCE, B2S_SOURCE_SHA),

        "B2U_results_SHA_exact":
            exact(B2U_RESULTS, B2U_RESULTS_SHA),

        "B2Y_source_SHA_exact":
            exact(B2Y_SOURCE, B2Y_SOURCE_SHA),

        "B2Y_results_SHA_exact":
            exact(B2Y_RESULTS, B2Y_RESULTS_SHA),

        "B2Y_decision_SHA_exact":
            exact(B2Y_DECISION, B2Y_DECISION_SHA),

        "B2Y_summary_SHA_exact":
            exact(B2Y_SUMMARY, B2Y_SUMMARY_SHA),
    }

    b2u = read_json(B2U_RESULTS) if B2U_RESULTS.exists() else {}
    b2y = read_json(B2Y_RESULTS) if B2Y_RESULTS.exists() else {}
    b2y_decision = read_json(B2Y_DECISION) if B2Y_DECISION.exists() else {}
    b2y_summary = read_json(B2Y_SUMMARY) if B2Y_SUMMARY.exists() else {}

    gates.update({
        "B2Y_status_exact":
            b2y_summary.get("status") == EXPECTED_B2Y_STATUS,

        "B2Y_reference_microbatch_128":
            b2y_summary.get("reference_microbatch")
            == REFERENCE_MICROBATCH,

        "B2Y_training_false":
            b2y_summary.get("COMP_XPU_005_full_training_authorized")
            is False,

        "B2Y_optimization_false":
            b2y_summary.get("optimization_branch_authorized")
            is False,

        "B2Y_B3_false":
            b2y_summary.get("B3_authorized")
            is False,
    })

    corrected = b2y.get("corrected_exact_graph", {})
    control = b2y.get("matched_first_order_control", {})
    ratios = b2y.get("steady_state_ratios", {})
    stage = b2y.get("warmed_synchronized_stage_profile", {})
    projection = b2y.get(
        "diagnostic_full_run_projection_from_corrected_median",
        {},
    )

    gates.update({
        "corrected_three_measured_repeats":
            len(corrected.get("measured_repeats", []))
            == EXPECTED_MEASURED_REPEATS,

        "control_three_measured_repeats":
            len(control.get("measured_repeats", []))
            == EXPECTED_MEASURED_REPEATS,

        "corrected_median_finite":
            finite(corrected.get("median_wall_seconds")),

        "corrected_mean_finite":
            finite(corrected.get("mean_wall_seconds")),

        "control_median_finite":
            finite(control.get("median_wall_seconds")),

        "control_mean_finite":
            finite(control.get("mean_wall_seconds")),

        "median_ratio_finite":
            finite(ratios.get("median_corrected_over_control")),

        "mean_ratio_finite":
            finite(ratios.get("mean_corrected_over_control")),

        "corrected_throughput_finite":
            finite(corrected.get("median_profiles_per_second")),

        "projection_days_finite":
            finite(projection.get("projected_days_for_target_epochs")),

        "warmed_forward_finite":
            finite(stage.get("model_forward_seconds")),

        "warmed_derivative_time_finite":
            finite(stage.get("local_recurrent_derivative_seconds")),

        "warmed_physics_algebra_finite":
            finite(
                stage.get(
                    "corrected_physics_algebra_fractional_flow_seconds"
                )
            ),

        "warmed_nonphysics_finite":
            finite(
                stage.get(
                    "nonphysics_loss_plus_total_assembly_seconds"
                )
            ),

        "warmed_backward_finite":
            finite(stage.get("total_backward_seconds")),

        "warmed_stage_weights_unchanged":
            stage.get("weights_exactly_unchanged") is True,

        "warmed_stage_checkpoint_SHA_unchanged":
            stage.get("checkpoint_SHA_unchanged") is True,
    })

    # Preserve exact B2U/B2Y reference rows.
    b2u_rows = {
        int(rec["microbatch"]): rec
        for rec in b2u.get("candidate_results", [])
        if "microbatch" in rec
    }

    ref_ids = (
        b2u_rows.get(REFERENCE_MICROBATCH, {})
        .get("dataset_indices")
    )

    b2y_ids = (
        b2y.get("reference", {})
        .get("dataset_indices")
    )

    gates.update({
        "B2U_reference_ids_present":
            isinstance(ref_ids, list)
            and len(ref_ids) == REFERENCE_MICROBATCH,

        "B2Y_reference_ids_match_B2U":
            ref_ids == b2y_ids,

        "B2Y_decision_dominant_stage_backward":
            b2y_decision.get("warmed_dominant_measured_stage")
            == "total_backward",
    })

    print("AUTHORITY / INTERPRETATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "B2Z blocked by authority or B2Y evidence mismatch."
        )

    corrected_median = float(corrected["median_wall_seconds"])
    corrected_mean = float(corrected["mean_wall_seconds"])
    control_median = float(control["median_wall_seconds"])
    median_ratio = float(ratios["median_corrected_over_control"])
    throughput = float(corrected["median_profiles_per_second"])
    projected_days = float(projection["projected_days_for_target_epochs"])

    forward_s = float(stage["model_forward_seconds"])
    deriv_s = float(stage["local_recurrent_derivative_seconds"])
    phys_s = float(
        stage["corrected_physics_algebra_fractional_flow_seconds"]
    )
    nonphys_s = float(
        stage["nonphysics_loss_plus_total_assembly_seconds"]
    )
    backward_s = float(stage["total_backward_seconds"])

    stage_sum = (
        forward_s
        + deriv_s
        + phys_s
        + nonphys_s
        + backward_s
    )

    derivative_plus_backward = deriv_s + backward_s

    derivative_plus_backward_fraction = (
        derivative_plus_backward
        / max(stage_sum, 1e-30)
    )

    interpretation = {
        "milestone":
            MILESTONE,

        "classification":
            "B2Y_WARMED_STEADY_STATE_PERFORMANCE_INTERPRETATION",

        "B2Y_execution_status":
            "CERTIFIED",

        "steady_state_measurements": {
            "reference_microbatch":
                REFERENCE_MICROBATCH,

            "corrected_median_seconds":
                corrected_median,

            "corrected_mean_seconds":
                corrected_mean,

            "control_median_seconds":
                control_median,

            "corrected_over_control_median_ratio":
                median_ratio,

            "corrected_median_profiles_per_second":
                throughput,

            "diagnostic_days_for_target_epochs":
                projected_days,

            "projection_semantics":
                "operational diagnostic only; not a runtime promise",
        },

        "warmed_stage_attribution": {
            "model_forward_seconds":
                forward_s,

            "local_recurrent_derivatives_seconds":
                deriv_s,

            "corrected_physics_algebra_seconds":
                phys_s,

            "nonphysics_loss_assembly_seconds":
                nonphys_s,

            "total_backward_seconds":
                backward_s,

            "stage_sum_seconds":
                stage_sum,

            "derivative_plus_backward_seconds":
                derivative_plus_backward,

            "derivative_plus_backward_fraction":
                derivative_plus_backward_fraction,

            "dominant_measured_stage":
                "total_backward",
        },

        "development_decision":
            "EQUIVALENCE_PRESERVING_DERIVATIVE_ENGINE_OPTIMIZATION_REQUIRED_BEFORE_EXECUTION_CONTRACT",

        "decision_basis":
            "The warmed benchmark removed first-use forward contamination while "
            "the corrected graph remained far more expensive than the matched "
            "first-order control. The warmed stage attribution localizes nearly "
            "all corrected-path time to local recurrent derivative construction "
            "and backward through that derivative graph.",

        "scientific_acceptance_threshold_used":
            False,

        "scientific_model_changed":
            False,

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,
    }

    INTERPRETATION.write_text(
        json.dumps(interpretation, indent=2),
        encoding="utf-8",
    )

    protocol = {
        "milestone":
            MILESTONE,

        "authorized_next_milestone":
            "V16E-1B2AA-XPU",

        "classification":
            "NO_UPDATE_BATCHED_VJP_DERIVATIVE_ENGINE_EQUIVALENCE_AND_PERFORMANCE_AUDIT",

        "reference": {
            "microbatch":
                REFERENCE_MICROBATCH,

            "dataset_indices":
                ref_ids,

            "frozen_checkpoint":
                "V16E-BLREP-COMP-XPU-004",

            "checkpoint_sha256":
                COMP004_CHECKPOINT_SHA,

            "exact_corrected_graph_source_sha256":
                B2S_SOURCE_SHA,
        },

        "baseline_derivative_engine": {
            "name":
                "LOOPED_LOCAL_VJP",

            "semantics":
                "one autograd.grad call per sequence output node j",

            "sequence_nodes":
                64,

            "quantities": [
                "N_xi(j)=dN_j/dxi_j",
                "N_tD(j)=dN_j/dp11[tD]",
                "N_X(j)=dN_j/dp11[xD_star]",
            ],

            "create_graph":
                True,

            "retain_graph":
                True,
        },

        "prospective_optimized_derivative_engine": {
            "name":
                "BATCHED_LOCAL_VJP",

            "implementation":
                "torch.autograd.grad with is_grads_batched=True",

            "grad_outputs":
                "64 one-hot sequence-output cotangents batched in one call",

            "required_semantics":
                "recover the same local diagonal N_xi and shared-conditioner "
                "N_tD/N_X derivatives as the baseline loop",

            "create_graph":
                True,

            "retain_graph":
                True,

            "scientific_change":
                False,
        },

        "equivalence_verification": {
            "required_objects": [
                "N_xi",
                "N_tD",
                "N_X",
                "corrected residual",
                "physics loss",
                "complete total loss",
                "all parameter gradients after backward",
            ],

            "identity_budget": {
                "float32_epsilon":
                    FLOAT32_EPS,

                "multiplier":
                    IDENTITY_EPS_MULTIPLIER,

                "semantics":
                    "computational implementation-equivalence tolerance only; "
                    "not a scientific model threshold",
            },

            "weights_must_remain_exactly_unchanged":
                True,

            "checkpoint_SHA_must_remain_exact":
                True,
        },

        "performance_benchmark": {
            "baseline_loop": {
                "warmup_iterations":
                    1,
                "measured_iterations":
                    3,
            },

            "batched_vjp": {
                "warmup_iterations":
                    1,
                "measured_iterations":
                    3,
            },

            "required_outputs": [
                "repeat wall times",
                "median wall time",
                "mean wall time",
                "profiles per second",
                "peak XPU memory if available",
                "batched-vs-loop speed ratio",
            ],
        },

        "runtime_failure_policy": {
            "if_is_grads_batched_unsupported":
                "record exact runtime error and stop; do not silently fall back",

            "allowed_result":
                "operational incompatibility without scientific implication",
        },

        "scientific_firewall": {
            "training":
                False,
            "optimizer":
                False,
            "optimizer_step":
                False,
            "weight_update":
                False,
            "architecture_change":
                False,
            "loss_change":
                False,
            "physics_change":
                False,
            "Nc_change":
                False,
            "OOD":
                False,
            "TOF":
                False,
            "B3_authorized":
                False,
        },

        "COMP_XPU_005_full_training_authorized":
            False,
    }

    PROTOCOL.write_text(
        json.dumps(protocol, indent=2),
        encoding="utf-8",
    )

    handoff = (
        "# V16E-1B2Z-XPU — B2AA Batched-VJP Optimization Handoff\n\n"
        "## B2Y certified result\n\n"
        "The warmed exact corrected graph remains substantially more expensive "
        "than the matched first-order control. Forward and residual algebra are "
        "negligible relative to local recurrent derivative construction and "
        "backward through the create_graph=True derivative graph.\n\n"
        "## First optimization branch\n\n"
        "Do not change the model or physics. Replace only the 64-call Python loop "
        "used to obtain N_xi, N_tD, and N_X with one batched VJP call using "
        "`torch.autograd.grad(..., is_grads_batched=True)` and 64 one-hot "
        "sequence-output cotangents.\n\n"
        "## Equivalence is mandatory\n\n"
        "Before timing is considered useful, compare loop vs batched engines for:\n\n"
        "* N_xi\n"
        "* N_tD\n"
        "* N_X\n"
        "* corrected residual\n"
        "* physics loss\n"
        "* complete total loss\n"
        "* every parameter gradient after backward\n\n"
        "Only a float32-machine-epsilon-derived implementation budget may be used.\n\n"
        "## Performance\n\n"
        "For both engines: one warm-up plus three measured repeats on the exact "
        "same frozen 128 rows.\n\n"
        "No optimizer. No weight update. If Intel XPU/LSTM does not support the "
        "batched-VJP path, preserve the exact error and stop rather than changing "
        "the scientific graph.\n\n"
        "COMP-XPU-005 full training and B3 remain blocked.\n"
    )

    HANDOFF.write_text(
        handoff,
        encoding="utf-8",
    )

    gates.update({
        "interpretation_written":
            INTERPRETATION.exists()
            and INTERPRETATION.stat().st_size > 0,

        "optimization_protocol_written":
            PROTOCOL.exists()
            and PROTOCOL.stat().st_size > 0,

        "handoff_written":
            HANDOFF.exists()
            and HANDOFF.stat().st_size > 0,

        "B2Y_execution_preserved":
            True,

        "optimization_required_frozen":
            True,

        "batched_VJP_is_implementation_only":
            True,

        "equivalence_required_before_adoption":
            True,

        "B2AA_authorized":
            True,

        "COMP005_training_not_authorized":
            True,

        "B3_not_authorized":
            True,

        "no_training":
            True,

        "no_optimizer":
            True,

        "no_optimizer_step":
            True,

        "no_weight_update":
            True,

        "no_OOD":
            True,

        "no_TOF":
            True,

        "no_scientific_numeric_threshold":
            True,
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2Z_XPU_B2Y_WARMED_PERFORMANCE_INTERPRETATION_AND_DERIVATIVE_ENGINE_OPTIMIZATION_PROTOCOL_FROZEN_"
        "STEADY_STATE_CORRECTED_COST_CONFIRMED_AND_LOCAL_RECURRENT_DERIVATIVE_PLUS_SECOND_ORDER_BACKWARD_BOTTLENECK_LOCALIZED_"
        "EQUIVALENCE_PRESERVING_IMPLEMENTATION_OPTIMIZATION_REQUIRED_BEFORE_COMP_XPU_005_EXECUTION_CONTRACT_"
        "B2AA_BATCHED_VJP_IS_GRADS_BATCHED_TRUE_LOCAL_DERIVATIVE_ENGINE_EQUIVALENCE_AND_PERFORMANCE_AUDIT_AUTHORIZED_"
        "SCIENTIFIC_MODEL_RESIDUAL_LOSSES_DATASET_AND_PHYSICAL_NC_FROZEN_"
        "NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2Z_XPU_PROTOCOL_FREEZE_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "interpretation_sha256":
            sha256(INTERPRETATION),

        "protocol_sha256":
            sha256(PROTOCOL),

        "handoff_sha256":
            sha256(HANDOFF),

        "reference_microbatch":
            REFERENCE_MICROBATCH,

        "B2Y_corrected_median_seconds":
            corrected_median,

        "B2Y_control_median_seconds":
            control_median,

        "B2Y_corrected_control_median_ratio":
            median_ratio,

        "B2Y_corrected_median_profiles_per_second":
            throughput,

        "B2Y_diagnostic_days_for_target_epochs":
            projected_days,

        "B2Y_derivative_plus_backward_seconds":
            derivative_plus_backward,

        "B2Y_derivative_plus_backward_fraction":
            derivative_plus_backward_fraction,

        "B2AA_authorized":
            bool(ok),

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2AA-XPU — no-update looped-VJP vs is_grads_batched=True "
                "batched-VJP local recurrent derivative equivalence and warmed "
                "performance audit at exact microbatch 128"
                if ok else
                "V16E-1B2Z-R1 — diagnose B2Y interpretation/protocol gate failure"
            ),

        "gates":
            {
                k: bool(v)
                for k, v in gates.items()
            },
    }

    SUMMARY.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nB2Y PERFORMANCE INTERPRETATION")
    print(
        "  corrected median:",
        f"{corrected_median:.3f} s",
    )
    print(
        "  control median:",
        f"{control_median:.3f} s",
    )
    print(
        "  corrected/control:",
        f"{median_ratio:.3f}x",
    )
    print(
        "  corrected throughput:",
        f"{throughput:.3f} profiles/s",
    )
    print(
        "  derivative + backward:",
        f"{derivative_plus_backward:.3f} s "
        f"({100.0 * derivative_plus_backward_fraction:.1f}% of warmed stage sum)",
    )
    print(
        "  diagnostic target-epoch projection:",
        f"{projected_days:.3f} days",
    )
    print(
        "  DECISION: equivalence-preserving derivative-engine optimization required."
    )

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Interpretation:", sha256(INTERPRETATION))
    print("  Protocol      :", sha256(PROTOCOL))
    print("  Handoff       :", sha256(HANDOFF))
    print("  Summary       :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
