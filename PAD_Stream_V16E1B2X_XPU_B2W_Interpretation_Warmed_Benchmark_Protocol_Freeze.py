#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2X-XPU
B2W Performance Interpretation
+ Warmed Steady-State Exact-Graph Benchmark Protocol Freeze

Purpose
-------
Freeze the scientifically and operationally correct interpretation of B2W
before any equivalence-preserving derivative-engine optimization is attempted.

NO TRAINING.
NO OPTIMIZER.
NO OPTIMIZER STEP.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

B2W certified facts
-------------------
At microbatch 128, with the exact frozen B2S corrected graph:

    corrected exact graph + backward : 33.928 s
    matched first-order control       : 0.150 s
    synchronized ratio                : 226.822x

Measured corrected-stage components:

    model forward                     : 2.043 s
    local recurrent derivatives       : 11.956 s
    corrected physics algebra         : 2.797 s
    nonphysics + total assembly       : 0.122 s
    total backward                    : 17.009 s

B2W execution itself is certified.

However, the B2W timing ratio is NOT yet frozen as steady-state throughput
because the corrected profile was executed first in the process, while the
matched control was executed afterward.

The measured forward discrepancy:

    corrected-profile forward : 2.043 s
    later control forward      : 0.042 s

is ~49x despite the same frozen model, same microbatch, and same data rows.

This is direct evidence that first-use/runtime warm-up, kernel compilation,
caching, or synchronization effects materially contaminate at least the first
timing path. B2X does NOT guess which runtime mechanism is responsible.

What B2W still establishes
--------------------------
Even after removing the entire 2.043 s corrected forward term, the measured
local recurrent derivative construction plus corrected backward account for
~28.965 s of the 33.928 s synchronized path. Therefore the derivative engine
is clearly expensive, but its STEADY-STATE cost must be measured before an
optimization branch is chosen.

Next milestone
--------------
V16E-1B2Y-XPU — warmed steady-state exact-graph benchmark.

B2Y must use:
    * exact frozen B2S corrected graph;
    * exact same B2U/B2W reference microbatch = 128;
    * exact same 128 frozen dataset rows;
    * frozen COMP-XPU-004 weights;
    * NO optimizer, NO weight update.

Required runs:
    Corrected exact graph:
        1 unmeasured warm-up iteration
        3 measured uninstrumented iterations

    Matched first-order control:
        1 unmeasured warm-up iteration
        3 measured uninstrumented iterations

    Warmed synchronized stage profile:
        1 measured corrected stage-decomposition iteration
        after corrected graph warm-up

Each iteration must recreate the autograd graph and execute backward(), then
discard gradients.

B2Y reports:
    * per-repeat wall times;
    * median and mean corrected wall time;
    * median and mean control wall time;
    * corrected/control steady-state ratio;
    * profiles/second;
    * diagnostic 800-epoch projection from the warmed median;
    * warmed synchronized stage attribution;
    * peak XPU memory if available;
    * finite gradients;
    * exact no-weight-change/checkpoint-SHA gates.

No scientific numeric acceptance threshold is introduced.

Only AFTER B2Y may B2Z decide whether an equivalence-preserving derivative-
engine optimization branch is required.

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
MILESTONE = "V16E-1B2X-XPU"

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

# Exact graph authority.
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

# B2W authority.
B2W_SOURCE = (
    R
    / "PAD_Stream_V16E1B2W_XPU_Exact_Graph_Performance_Bottleneck_Audit.py"
)
B2W_SOURCE_SHA = "6027594adc37257fcfd2c129e6fa723572c3cadb473a746abd3ac613fe4512da"

B2W_DIR = (
    R / "output"
    / "V16_E1B2W_XPU_EXACT_GRAPH_PERFORMANCE_BOTTLENECK_AUDIT"
)
B2W_PROFILE = B2W_DIR / "V16E1B2W_Exact_Graph_Performance_Profile.json"
B2W_DECISION = B2W_DIR / "V16E1B2W_Performance_Bottleneck_Decision.json"
B2W_SUMMARY = B2W_DIR / "PAD_Stream_V16E1B2W_XPU_Summary.json"

B2W_PROFILE_SHA = "0002769ed3be891dcc7c738eb801ac87915ee28db27d60faf6879c5580b491c2"
B2W_DECISION_SHA = "89525ae78930dd9ccdf3a550a9aea58393af782b27a4911ca89376c0b6d43dda"
B2W_SUMMARY_SHA = "6b441a2db2896af71e458b3ede22a4f6f0eab528ffec222f66ba3a9fe7b9026b"

EXPECTED_B2W_STATUS = (
    "V16E1B2W_XPU_EXACT_CORRECTED_GRAPH_PERFORMANCE_BOTTLENECK_AUDIT_COMPLETE_"
    "MICROBATCH_128_EXACT_CERTIFIED_B2S_GRAPH_PROFILED_WITH_SYNCHRONIZED_FORWARD_LOCAL_RECURRENT_DERIVATIVE_"
    "CORRECTED_PHYSICS_ALGEBRA_NONPHYSICS_LOSS_AND_TOTAL_BACKWARD_TIMINGS_"
    "MATCHED_FIRST_ORDER_NONPHYSICS_CONTROL_COMPLETE_FINITE_GRADIENTS_NO_WEIGHT_CHANGE_"
    "MICROBATCH_256_FROZEN_RUNTIME_ERROR_TEXT_PRESERVED_WITHOUT_RERUN_OR_RECLASSIFICATION_"
    "NO_OPTIMIZER_NO_WEIGHT_CHANGE_COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_"
    "B2X_PERFORMANCE_INTERPRETATION_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_B3_NOT_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2X_XPU_B2W_INTERPRETATION_WARMED_BENCHMARK_PROTOCOL"
)
OUT.mkdir(parents=True, exist_ok=True)

INTERPRETATION = OUT / "V16E1B2X_B2W_Performance_Interpretation.json"
PROTOCOL = OUT / "V16E1B2X_B2Y_Warmed_Steady_State_Protocol.json"
HANDOFF = OUT / "V16E1B2X_B2Y_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2X_XPU_Summary.json"

REFERENCE_MICROBATCH = 128
WARMUP_REPEATS = 1
MEASURED_REPEATS = 3


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
    print("PAD-Stream V16E-1B2X-XPU")
    print("B2W Performance Interpretation")
    print("+ Warmed Steady-State Benchmark Protocol Freeze")
    print("=" * 80)
    print("PROTOCOL ONLY — NO TRAINING — NO OPTIMIZER.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2X summary already exists; refusing overwrite."
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

        "B2W_source_SHA_exact":
            exact(B2W_SOURCE, B2W_SOURCE_SHA),

        "B2W_profile_SHA_exact":
            exact(B2W_PROFILE, B2W_PROFILE_SHA),

        "B2W_decision_SHA_exact":
            exact(B2W_DECISION, B2W_DECISION_SHA),

        "B2W_summary_SHA_exact":
            exact(B2W_SUMMARY, B2W_SUMMARY_SHA),
    }

    b2w = read_json(B2W_PROFILE) if B2W_PROFILE.exists() else {}
    b2w_summary = read_json(B2W_SUMMARY) if B2W_SUMMARY.exists() else {}
    b2u = read_json(B2U_RESULTS) if B2U_RESULTS.exists() else {}

    gates.update({
        "B2W_status_exact":
            b2w_summary.get("status") == EXPECTED_B2W_STATUS,

        "B2W_reference_microbatch_128":
            b2w_summary.get("reference_microbatch")
            == REFERENCE_MICROBATCH,

        "B2W_training_false":
            b2w_summary.get("COMP_XPU_005_full_training_authorized")
            is False,

        "B2W_B3_false":
            b2w_summary.get("B3_authorized")
            is False,

        "B2W_exact_graph_unchanged":
            (
                b2w.get("exact_graph_authority", {})
                .get("scientific_graph_changed")
                is False
            ),
    })

    corrected = b2w.get("corrected_exact_graph_profile", {})
    control = b2w.get("matched_first_order_nonphysics_control", {})
    ratios = b2w.get("performance_ratios", {})

    gates.update({
        "corrected_forward_finite":
            finite(corrected.get("model_forward_seconds")),

        "control_forward_finite":
            finite(control.get("model_forward_seconds")),

        "corrected_derivative_time_finite":
            finite(
                corrected.get(
                    "local_recurrent_derivative_seconds"
                )
            ),

        "corrected_backward_finite":
            finite(corrected.get("total_backward_seconds")),

        "corrected_total_finite":
            finite(
                corrected.get(
                    "forward_graph_plus_backward_wall_seconds"
                )
            ),

        "control_total_finite":
            finite(
                control.get(
                    "forward_loss_backward_wall_seconds"
                )
            ),

        "B2W_ratio_finite":
            finite(
                ratios.get(
                    "corrected_over_first_order_total_wall"
                )
            ),

        "corrected_weights_unchanged":
            corrected.get("weights_exactly_unchanged") is True,

        "control_weights_unchanged":
            control.get("weights_exactly_unchanged") is True,

        "corrected_checkpoint_SHA_unchanged":
            corrected.get("checkpoint_SHA_unchanged") is True,

        "control_checkpoint_SHA_unchanged":
            control.get("checkpoint_SHA_unchanged") is True,
    })

    # Exact B2U/B2W reference rows are preserved for B2Y.
    b2u_rows = {
        int(rec["microbatch"]): rec
        for rec in b2u.get("candidate_results", [])
        if "microbatch" in rec
    }

    reference_ids = (
        b2u_rows.get(REFERENCE_MICROBATCH, {})
        .get("dataset_indices")
    )

    gates.update({
        "B2U_reference_ids_present":
            (
                isinstance(reference_ids, list)
                and len(reference_ids)
                == REFERENCE_MICROBATCH
            ),

        "B2W_same_reference_ids":
            corrected.get("dataset_indices")
            == reference_ids
            == control.get("dataset_indices"),
    })

    print("AUTHORITY / INTERPRETATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "B2X blocked by authority or B2W evidence mismatch."
        )

    corrected_forward = float(
        corrected["model_forward_seconds"]
    )
    control_forward = float(
        control["model_forward_seconds"]
    )

    forward_ratio = (
        corrected_forward
        / max(control_forward, 1e-30)
    )

    derivative_seconds = float(
        corrected[
            "local_recurrent_derivative_seconds"
        ]
    )

    backward_seconds = float(
        corrected[
            "total_backward_seconds"
        ]
    )

    corrected_total = float(
        corrected[
            "forward_graph_plus_backward_wall_seconds"
        ]
    )

    derivative_plus_backward = (
        derivative_seconds
        + backward_seconds
    )

    interpretation = {
        "milestone":
            MILESTONE,

        "classification":
            "B2W_SYNCHRONIZED_PROFILE_INTERPRETATION",

        "B2W_execution_status":
            "CERTIFIED",

        "frozen_B2W_measurements": {
            "corrected_model_forward_seconds":
                corrected_forward,

            "control_model_forward_seconds":
                control_forward,

            "corrected_forward_over_control_forward":
                float(forward_ratio),

            "local_recurrent_derivative_seconds":
                derivative_seconds,

            "corrected_physics_algebra_seconds":
                float(
                    corrected[
                        "corrected_physics_algebra_fractional_flow_seconds"
                    ]
                ),

            "corrected_total_backward_seconds":
                backward_seconds,

            "corrected_exact_graph_plus_backward_seconds":
                corrected_total,

            "matched_control_total_seconds":
                float(
                    control[
                        "forward_loss_backward_wall_seconds"
                    ]
                ),

            "corrected_over_control_synchronized_ratio":
                float(
                    ratios[
                        "corrected_over_first_order_total_wall"
                    ]
                ),

            "derivative_plus_backward_seconds":
                float(derivative_plus_backward),
        },

        "steady_state_interpretation": {
            "B2W_ratio_classification":
                "FIRST_PASS_SYNCHRONIZED_DIAGNOSTIC_NOT_YET_STEADY_STATE_BASELINE",

            "reason":
                "The corrected path was executed before the matched control. "
                "The same frozen model/reference batch showed a corrected-profile "
                "forward time far larger than the later control forward time. "
                "Therefore first-use runtime effects contaminate at least one "
                "measured stage.",

            "runtime_cause":
                "NOT_DIAGNOSED_IN_B2X",

            "prohibited_runtime_claims": [
                "the 2.043 s forward is steady-state model forward time",
                "the 226.822x ratio is the final steady-state corrected/control ratio",
                "the discrepancy is definitively caused by JIT compilation",
                "the discrepancy is definitively caused by kernel caching",
            ],
        },

        "still_supported_by_B2W": {
            "derivative_engine_expensive":
                True,

            "evidence":
                "Local recurrent derivative construction plus corrected backward "
                "account for a large measured share of the corrected path even "
                "before steady-state timing is established.",

            "derivative_plus_backward_seconds_B2W":
                float(derivative_plus_backward),

            "fraction_of_B2W_corrected_total":
                float(
                    derivative_plus_backward
                    / max(corrected_total, 1e-30)
                ),
        },

        "decision":
            "REQUIRE_WARMED_REPEATED_STEADY_STATE_BENCHMARK_BEFORE_OPTIMIZATION_BRANCH",

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,
    }

    INTERPRETATION.write_text(
        json.dumps(
            interpretation,
            indent=2,
        ),
        encoding="utf-8",
    )

    protocol = {
        "milestone":
            MILESTONE,

        "authorized_next_milestone":
            "V16E-1B2Y-XPU",

        "classification":
            "WARMED_REPEATED_NO_UPDATE_STEADY_STATE_EXACT_GRAPH_BENCHMARK",

        "reference": {
            "microbatch":
                REFERENCE_MICROBATCH,

            "dataset_indices":
                reference_ids,

            "model":
                "frozen COMP-XPU-004",

            "checkpoint_sha256":
                COMP004_CHECKPOINT_SHA,

            "exact_corrected_graph_source_sha256":
                B2S_SOURCE_SHA,
        },

        "corrected_graph_runs": {
            "unmeasured_warmup_iterations":
                WARMUP_REPEATS,

            "measured_uninstrumented_iterations":
                MEASURED_REPEATS,

            "per_iteration":
                "recreate graph -> corrected complete loss -> backward -> "
                "XPU synchronize -> inspect finite gradients -> discard gradients",

            "optimizer":
                False,

            "weight_update":
                False,
        },

        "matched_control_runs": {
            "unmeasured_warmup_iterations":
                WARMUP_REPEATS,

            "measured_uninstrumented_iterations":
                MEASURED_REPEATS,

            "same_model_architecture":
                True,

            "same_reference_rows":
                True,

            "optimizer":
                False,

            "weight_update":
                False,
        },

        "warmed_stage_profile": {
            "required":
                True,

            "iterations":
                1,

            "timing_stages": [
                "model forward",
                "local recurrent derivative construction",
                "corrected physics algebra / fractional-flow derivative",
                "nonphysics loss + total assembly",
                "total backward",
            ],

            "precondition":
                "execute corrected warm-up before stage-profile measurement",
        },

        "required_outputs": [
            "corrected repeat wall times",
            "corrected median wall time",
            "corrected mean wall time",
            "control repeat wall times",
            "control median wall time",
            "control mean wall time",
            "median corrected/control ratio",
            "mean corrected/control ratio",
            "corrected median profiles per second",
            "diagnostic hours per epoch from warmed corrected median",
            "diagnostic days for 800 epochs from warmed corrected median",
            "warmed synchronized stage attribution",
            "finite gradients each repeat",
            "weights unchanged each repeat",
            "checkpoint SHA unchanged",
            "peak XPU memory if available",
        ],

        "timing_policy":
            "Use XPU synchronization immediately before and after each uninstrumented "
            "measured iteration. Warm-up iterations are excluded from reported "
            "steady-state statistics.",

        "projection_policy":
            "Full-run projections remain operational diagnostics only, not runtime promises.",

        "scientific_firewall": {
            "training":
                False,
            "optimizer":
                False,
            "optimizer_step":
                False,
            "weight_update":
                False,
            "scientific_settings_changed":
                False,
            "COMP004_checkpoint_mutation":
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
        json.dumps(
            protocol,
            indent=2,
        ),
        encoding="utf-8",
    )

    handoff = (
        "# V16E-1B2X-XPU — B2Y Warmed Benchmark Handoff\n\n"
        "## B2W is certified\n\n"
        "The exact corrected graph completed with finite gradients and no weight "
        "mutation. Its synchronized profile showed a very large cost relative to "
        "the matched first-order control.\n\n"
        "## Why B2W is not yet the steady-state baseline\n\n"
        "The corrected profile ran first. Its model-forward timing was 2.043 s, "
        "whereas the later matched-control forward was 0.042 s on the same model "
        "and reference batch. B2X does not guess the runtime cause, but this directly "
        "shows first-use/runtime state affected the measurement.\n\n"
        "## B2Y\n\n"
        "Use microbatch 128 and the exact same 128 B2U/B2W rows.\n\n"
        "Corrected graph:\n"
        "  * 1 unmeasured warm-up\n"
        "  * 3 uninstrumented measured backward iterations\n\n"
        "Matched control:\n"
        "  * 1 unmeasured warm-up\n"
        "  * 3 uninstrumented measured backward iterations\n\n"
        "Then perform one warmed synchronized corrected stage profile.\n\n"
        "No optimizer and no weight update. Only after B2Y should we decide whether "
        "to optimize the recurrent derivative engine or freeze the execution contract.\n\n"
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

        "warmed_protocol_written":
            PROTOCOL.exists()
            and PROTOCOL.stat().st_size > 0,

        "handoff_written":
            HANDOFF.exists()
            and HANDOFF.stat().st_size > 0,

        "B2W_execution_preserved":
            True,

        "B2W_ratio_not_promoted_to_steady_state":
            True,

        "runtime_cause_not_invented":
            True,

        "B2Y_authorized":
            True,

        "optimization_branch_not_yet_authorized":
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

    ok = all(
        bool(v)
        for v in gates.values()
    )

    status = (
        "V16E1B2X_XPU_B2W_PERFORMANCE_INTERPRETATION_AND_WARMED_STEADY_STATE_BENCHMARK_PROTOCOL_FROZEN_"
        "B2W_EXACT_GRAPH_EXECUTION_CERTIFIED_BUT_FIRST_PASS_SYNCHRONIZED_226X_RATIO_NOT_PROMOTED_TO_STEADY_STATE_"
        "CORRECTED_VS_CONTROL_FORWARD_TIMING_DISCREPANCY_BOUND_AS_DIRECT_EVIDENCE_OF_FIRST_USE_RUNTIME_CONTAMINATION_WITHOUT_CAUSE_GUESS_"
        "DERIVATIVE_ENGINE_COST_REMAINS_MATERIALLY_LARGE_"
        "B2Y_MICROBATCH_128_ONE_WARMUP_THREE_REPEAT_UNINSTRUMENTED_CORRECTED_AND_MATCHED_CONTROL_PLUS_WARMED_STAGE_PROFILE_AUTHORIZED_"
        "NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2X_XPU_PROTOCOL_FREEZE_COMPLETED_WITH_GATE_FAILURE"
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

        "B2W_corrected_forward_seconds":
            corrected_forward,

        "B2W_control_forward_seconds":
            control_forward,

        "B2W_forward_ratio":
            float(forward_ratio),

        "B2W_derivative_plus_backward_seconds":
            float(derivative_plus_backward),

        "B2Y_authorized":
            bool(ok),

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2Y-XPU — warmed steady-state exact corrected-graph and matched-control "
                "benchmark at microbatch 128: one warm-up plus three measured iterations each, "
                "followed by one warmed synchronized stage profile; no optimizer or weight update"
                if ok else
                "V16E-1B2X-R1 — diagnose B2W interpretation/protocol gate failure"
            ),

        "gates":
            {
                k: bool(v)
                for k, v in gates.items()
            },
    }

    SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nB2W INTERPRETATION")
    print(
        "  corrected forward:",
        f"{corrected_forward:.3f} s",
    )
    print(
        "  later control forward:",
        f"{control_forward:.3f} s",
    )
    print(
        "  forward discrepancy:",
        f"{forward_ratio:.3f}x",
    )
    print(
        "  derivative + corrected backward:",
        f"{derivative_plus_backward:.3f} s",
    )
    print("  B2W 226.8x ratio: diagnostic, NOT steady-state freeze.")

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
