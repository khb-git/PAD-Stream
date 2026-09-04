#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2V-XPU
B2U Throughput / Memory Interpretation
+ Exact-Graph Performance-Diagnostic Protocol Freeze

Purpose
-------
Interpret the completed B2U extended benchmark without over-claiming what it
proved.

NO TRAINING.
NO OPTIMIZER.
NO OPTIMIZER STEP.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

B2U evidence
------------
Tested corrected-residual microbatches:
    32, 64, 128, 256

Observed:
    32  PASS
    64  PASS
    128 PASS
    256 FAIL (frozen B2U classification: RUNTIME_ERROR)

Therefore:
    * 128 is the largest PROVEN FEASIBLE tested microbatch.
    * 128 is NOT automatically the hardware ceiling.
    * 256 is NOT automatically classified as OOM unless the frozen child error
      text explicitly establishes that.
    * Full COMP-XPU-005 training is NOT authorized simply because 128 passed.

B2U diagnostic full-run projection at microbatch 128 remains operationally
large (~29.4 days for 800 epochs from the isolated candidate measurement).
That projection is not a runtime promise, but it is sufficient evidence that
the exact second-order derivative engine should be profiled before committing
to a full corrected Stage-2 run.

Next milestone
--------------
V16E-1B2W-XPU — exact-graph performance bottleneck audit.

B2W must:
    * use frozen COMP-XPU-004 weights unchanged;
    * use the exact certified B2S corrected residual graph;
    * use microbatch 128 as the largest proven-feasible reference;
    * create NO optimizer and perform NO weight update;
    * decompose wall time into:
          model forward
          local recurrent derivative construction
          corrected residual algebra / fractional-flow derivative
          non-physics loss construction
          total backward
          XPU synchronization
    * compare against a matched first-order/non-physics backward control;
    * preserve exact residual identities and checkpoint SHA;
    * record the exact frozen B2U microbatch-256 failure text/classification
      without guessing its cause.

Only after B2W may an implementation-optimization branch or final execution
contract be selected.

B3 remains blocked.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import sys


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2V-XPU"

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

# B2S exact implementation authority
B2S_SOURCE = (
    R
    / "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
)
B2S_SOURCE_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"

# B2T
B2T_DIR = (
    R / "output"
    / "V16_E1B2T_XPU_B2S_INTERPRETATION_EXTENDED_THROUGHPUT_PROTOCOL"
)
B2T_PROTOCOL = B2T_DIR / "V16E1B2T_B2U_Extended_Throughput_Protocol.json"
B2T_SUMMARY = B2T_DIR / "PAD_Stream_V16E1B2T_XPU_Summary.json"

B2T_PROTOCOL_SHA = "0858cbf9934b95ca29d07f20f3157c20660a2e4684d432ced0e19e7659ed7598"
B2T_SUMMARY_SHA = "9a54f2c7bb56160ec705153ec5f33b66070c8ae432aea157340c40548f516187"

# B2U
B2U_SOURCE = (
    R
    / "PAD_Stream_V16E1B2U_XPU_Extended_Corrected_Residual_Throughput_Memory_Benchmark.py"
)
B2U_SOURCE_SHA = "3c41bf0876ccb4e2b2b2193870bca2639a06ef6a7539c3e0166cdbde50e82519"

B2U_DIR = (
    R / "output"
    / "V16_E1B2U_XPU_EXTENDED_CORRECTED_RESIDUAL_THROUGHPUT"
)
B2U_RESULTS = B2U_DIR / "V16E1B2U_Extended_Throughput_Memory_Results.json"
B2U_DECISION = B2U_DIR / "V16E1B2U_Operational_Microbatch_Decision.json"
B2U_SUMMARY = B2U_DIR / "PAD_Stream_V16E1B2U_XPU_Summary.json"

B2U_RESULTS_SHA = "e71f398c88feee2260c50109055b917103e76800365954823f320457a0d30075"
B2U_DECISION_SHA = "00c4418adb1b491f8fec0a177bcbc36a2fe4a79363f116474d81d625498457cf"
B2U_SUMMARY_SHA = "9623bace06e8526524fde61a39b3ce3ff8193aa1ccc40713f5fdd671ca6e88d1"

EXPECTED_B2U_STATUS = (
    "V16E1B2U_XPU_EXTENDED_CORRECTED_RESIDUAL_BACKWARD_THROUGHPUT_MEMORY_BENCHMARK_COMPLETE_"
    "EXACT_CERTIFIED_B2S_CREATE_GRAPH_TRUE_RECURRENT_DERIVATIVE_AND_TOTAL_LOSS_GRAPH_REUSED_"
    "EXTENDED_MICROBATCHES_32_64_128_256_ATTEMPTED_SUBPROCESS_ISOLATED_"
    "LARGEST_ACTUALLY_SUCCESSFUL_TESTED_MICROBATCH_AND_DIAGNOSTIC_FULL_RUN_PROJECTIONS_BOUND_"
    "FINITE_GRADIENTS_AND_NO_WEIGHT_CHANGE_CONFIRMED_FOR_SUCCESSFUL_CANDIDATES_"
    "NO_OPTIMIZER_NO_OPTIMIZER_STEP_COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_"
    "B2V_EXECUTION_CONTRACT_FREEZE_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_B3_NOT_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2V_XPU_B2U_INTERPRETATION_PERFORMANCE_DIAGNOSTIC_PROTOCOL"
)
OUT.mkdir(parents=True, exist_ok=True)

INTERPRETATION = OUT / "V16E1B2V_B2U_Operational_Interpretation.json"
PROTOCOL = OUT / "V16E1B2V_B2W_Performance_Diagnostic_Protocol.json"
HANDOFF = OUT / "V16E1B2V_B2W_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2V_XPU_Summary.json"

EXPECTED_CANDIDATES = [32, 64, 128, 256]
EXPECTED_SUCCESS = [32, 64, 128]
REFERENCE_MICROBATCH = 128


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
    print("PAD-Stream V16E-1B2V-XPU")
    print("B2U Throughput / Memory Interpretation")
    print("+ Exact-Graph Performance-Diagnostic Protocol Freeze")
    print("=" * 80)
    print("PROTOCOL ONLY — NO TRAINING — NO OPTIMIZER.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2V summary already exists; refusing overwrite."
        )

    gates = {
        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),

        "COMP004_checkpoint_SHA_exact":
            exact(COMP004_CHECKPOINT, COMP004_CHECKPOINT_SHA),

        "B2S_source_SHA_exact":
            exact(B2S_SOURCE, B2S_SOURCE_SHA),

        "B2T_protocol_SHA_exact":
            exact(B2T_PROTOCOL, B2T_PROTOCOL_SHA),

        "B2T_summary_SHA_exact":
            exact(B2T_SUMMARY, B2T_SUMMARY_SHA),

        "B2U_source_SHA_exact":
            exact(B2U_SOURCE, B2U_SOURCE_SHA),

        "B2U_results_SHA_exact":
            exact(B2U_RESULTS, B2U_RESULTS_SHA),

        "B2U_decision_SHA_exact":
            exact(B2U_DECISION, B2U_DECISION_SHA),

        "B2U_summary_SHA_exact":
            exact(B2U_SUMMARY, B2U_SUMMARY_SHA),
    }

    b2u = read_json(B2U_RESULTS) if B2U_RESULTS.exists() else {}
    b2u_decision = read_json(B2U_DECISION) if B2U_DECISION.exists() else {}
    b2u_summary = read_json(B2U_SUMMARY) if B2U_SUMMARY.exists() else {}

    gates.update({
        "B2U_status_exact":
            b2u_summary.get("status") == EXPECTED_B2U_STATUS,

        "B2U_candidates_exact":
            b2u.get("candidate_microbatches")
            == EXPECTED_CANDIDATES,

        "B2U_successes_exact":
            b2u.get("successful_microbatches")
            == EXPECTED_SUCCESS,

        "B2U_largest_success_128":
            b2u.get("largest_successful_tested_microbatch")
            == REFERENCE_MICROBATCH,

        "B2U_training_false":
            b2u.get("COMP_XPU_005_full_training_authorized")
            is False,

        "B2U_optimizer_false":
            b2u.get("optimizer_created") is False,

        "B2U_optimizer_step_false":
            b2u.get("optimizer_step") is False,

        "B2U_weight_update_false":
            b2u.get("weight_update") is False,

        "B2U_checkpoint_mutated_false":
            b2u.get("checkpoint_mutated") is False,

        "B2U_B3_false":
            b2u.get("B3_authorized") is False,

        "B2U_decision_not_finalized":
            b2u_decision.get(
                "operational_microbatch_finalized_for_training"
            )
            is False,
    })

    rows = {
        int(rec["microbatch"]): rec
        for rec in b2u.get("candidate_results", [])
        if "microbatch" in rec
    }

    gates.update({
        "all_candidate_records_present":
            set(rows.keys()) == set(EXPECTED_CANDIDATES),

        "mb32_success":
            rows[32].get("success") is True,

        "mb64_success":
            rows[64].get("success") is True,

        "mb128_success":
            rows[128].get("success") is True,

        "mb256_failed":
            rows[256].get("success") is False,

        "mb256_failure_class_runtime_error":
            rows[256].get("failure_class")
            == "RUNTIME_ERROR",

        "successful_times_finite":
            all(
                finite(rows[m].get("forward_residual_backward_seconds"))
                for m in EXPECTED_SUCCESS
            ),

        "successful_memory_finite":
            all(
                (
                    rows[m].get("peak_xpu_memory_bytes") is None
                    or finite(rows[m].get("peak_xpu_memory_bytes"))
                )
                for m in EXPECTED_SUCCESS
            ),

        "successful_gradients_finite":
            all(
                rows[m].get("parameter_gradients_finite") is True
                for m in EXPECTED_SUCCESS
            ),

        "successful_weights_unchanged":
            all(
                rows[m].get("weights_exactly_unchanged") is True
                for m in EXPECTED_SUCCESS
            ),

        "successful_checkpoint_SHA_unchanged":
            all(
                rows[m].get("checkpoint_SHA_unchanged") is True
                for m in EXPECTED_SUCCESS
            ),
    })

    projections = b2u.get("diagnostic_full_run_projections", {})

    gates.update({
        "projection_32_present":
            "32" in projections,

        "projection_64_present":
            "64" in projections,

        "projection_128_present":
            "128" in projections,

        "projection_128_finite":
            finite(
                projections.get("128", {})
                .get("projected_days_for_800_epochs")
            ),
    })

    print("AUTHORITY / INTERPRETATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "B2V blocked by authority or B2U evidence mismatch."
        )

    throughput = {
        m: float(rows[m]["profiles_per_second"])
        for m in EXPECTED_SUCCESS
    }

    memory = {
        m: rows[m].get("peak_xpu_memory_bytes")
        for m in EXPECTED_SUCCESS
    }

    p128 = projections["128"]

    mb256_error = rows[256].get("error")
    mb256_failure_class = rows[256].get("failure_class")

    interpretation = {
        "milestone":
            MILESTONE,

        "classification":
            "B2U_EXTENDED_THROUGHPUT_MEMORY_INTERPRETATION",

        "frozen_measurements": {
            str(m): {
                "success":
                    bool(rows[m].get("success")),

                "forward_residual_backward_seconds":
                    rows[m].get(
                        "forward_residual_backward_seconds"
                    ),

                "profiles_per_second":
                    rows[m].get("profiles_per_second"),

                "peak_xpu_memory_bytes":
                    rows[m].get("peak_xpu_memory_bytes"),

                "failure_class":
                    rows[m].get("failure_class"),

                "error":
                    rows[m].get("error"),
            }
            for m in EXPECTED_CANDIDATES
        },

        "throughput_scaling": {
            "32_profiles_per_second":
                throughput[32],

            "64_profiles_per_second":
                throughput[64],

            "128_profiles_per_second":
                throughput[128],

            "64_over_32":
                float(throughput[64] / throughput[32]),

            "128_over_64":
                float(throughput[128] / throughput[64]),

            "128_over_32":
                float(throughput[128] / throughput[32]),
        },

        "memory_scaling": {
            "32_peak_bytes":
                memory[32],

            "64_peak_bytes":
                memory[64],

            "128_peak_bytes":
                memory[128],
        },

        "microbatch_128": {
            "classification":
                "LARGEST_PROVEN_FEASIBLE_TESTED_REFERENCE",

            "not_classified_as":
                [
                    "hardware ceiling",
                    "final training microbatch",
                    "full-run execution authorization",
                ],

            "diagnostic_projected_hours_per_epoch":
                float(
                    p128[
                        "projected_hours_per_epoch"
                    ]
                ),

            "diagnostic_projected_days_for_800_epochs":
                float(
                    p128[
                        "projected_days_for_800_epochs"
                    ]
                ),

            "projection_semantics":
                "operational diagnostic only; not a runtime promise",
        },

        "microbatch_256": {
            "success":
                False,

            "frozen_failure_class":
                mb256_failure_class,

            "frozen_error_text":
                mb256_error,

            "interpretation":
                "Failure mechanism is not reclassified in B2V. In particular, "
                "RUNTIME_ERROR is not silently converted to OOM or hardware ceiling.",
        },

        "decision":
            "DO_NOT_AUTHORIZE_FULL_COMP_XPU_005_TRAINING_YET",

        "reason":
            "The largest proven-feasible exact-graph reference still carries an "
            "operationally large isolated-measurement full-run projection, while "
            "the next larger candidate failed without a frozen OOM classification. "
            "The exact derivative engine should be performance-profiled before the "
            "execution contract is frozen.",

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
            "V16E-1B2W-XPU",

        "classification":
            "NO_UPDATE_EXACT_GRAPH_PERFORMANCE_BOTTLENECK_AUDIT",

        "reference_microbatch":
            REFERENCE_MICROBATCH,

        "reference_reason":
            "largest actually successful B2U candidate",

        "implementation_authority":
            {
                "B2S_source_sha256":
                    B2S_SOURCE_SHA,

                "rule":
                    "Reuse the exact certified corrected-residual derivative "
                    "functions; do not change the scientific graph.",
            },

        "required_timing_decomposition": [
            "model forward",
            "local recurrent derivative construction N_xi/N_tD/N_X",
            "fractional-flow plus dfdS and corrected residual algebra",
            "non-physics loss construction",
            "complete corrected total loss assembly",
            "total backward",
            "XPU synchronization",
        ],

        "matched_control":
            {
                "type":
                    "first-order non-physics backward",

                "purpose":
                    "quantify the incremental cost of the corrected derivative "
                    "engine relative to the same recurrent model/data/BC/anchor/"
                    "monotonicity graph without corrected physics derivatives",

                "weight_update":
                    False,

                "optimizer":
                    False,
            },

        "microbatch_256_policy":
            {
                "frozen_failure_class":
                    mb256_failure_class,

                "frozen_error_text":
                    mb256_error,

                "B2W_rule":
                    "Preserve exact text/classification. Do not diagnose from label "
                    "alone. Any reproduction must be isolated and no-update.",
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
        json.dumps(protocol, indent=2),
        encoding="utf-8",
    )

    handoff = (
        "# V16E-1B2V-XPU — B2W Performance Diagnostic Handoff\n\n"
        "## B2U certified result\n\n"
        "* microbatch 32: PASS\n"
        "* microbatch 64: PASS\n"
        "* microbatch 128: PASS\n"
        "* microbatch 256: FAIL, frozen class RUNTIME_ERROR\n\n"
        "Microbatch 128 is the largest proven-feasible tested value. It is not "
        "declared the hardware ceiling or final training value.\n\n"
        "## Why full training is still blocked\n\n"
        "The B2U isolated timing projection at microbatch 128 remains operationally "
        "large for 800 epochs. The projection is diagnostic only, but warrants "
        "profiling of the exact second-order derivative engine before committing to "
        "the full run.\n\n"
        "## B2W\n\n"
        "Profile the exact B2S corrected graph at microbatch 128 with no optimizer "
        "and no weight update. Time forward, local recurrent derivatives, corrected "
        "residual algebra, non-physics losses, backward, and synchronization. Also "
        "run a matched first-order/non-physics backward control.\n\n"
        "Preserve the exact microbatch-256 error text from B2U; do not guess whether "
        "it was memory, runtime support, or another device/runtime condition.\n\n"
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

        "performance_protocol_written":
            PROTOCOL.exists()
            and PROTOCOL.stat().st_size > 0,

        "handoff_written":
            HANDOFF.exists()
            and HANDOFF.stat().st_size > 0,

        "microbatch128_bound_as_reference_only":
            True,

        "microbatch256_not_reclassified":
            True,

        "full_training_not_authorized":
            True,

        "B2W_authorized":
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
        "V16E1B2V_XPU_B2U_THROUGHPUT_MEMORY_INTERPRETATION_AND_EXACT_GRAPH_PERFORMANCE_DIAGNOSTIC_PROTOCOL_FROZEN_"
        "MICROBATCH_128_BOUND_AS_LARGEST_PROVEN_FEASIBLE_TESTED_REFERENCE_NOT_HARDWARE_CEILING_OR_FINAL_TRAINING_VALUE_"
        "MICROBATCH_256_FAILURE_PRESERVED_AS_RUNTIME_ERROR_WITHOUT_CAUSE_RECLASSIFICATION_"
        "B2U_THROUGHPUT_MEMORY_AND_DIAGNOSTIC_FULL_RUN_PROJECTIONS_FROZEN_"
        "COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_"
        "B2W_NO_UPDATE_EXACT_DERIVATIVE_GRAPH_TIMING_AND_MATCHED_FIRST_ORDER_CONTROL_AUTHORIZED_"
        "NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2V_XPU_PROTOCOL_FREEZE_COMPLETED_WITH_GATE_FAILURE"
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

        "largest_proven_feasible_tested_microbatch":
            REFERENCE_MICROBATCH,

        "microbatch_256_failure_class":
            mb256_failure_class,

        "microbatch_128_diagnostic_hours_per_epoch":
            float(p128["projected_hours_per_epoch"]),

        "microbatch_128_diagnostic_days_for_800_epochs":
            float(p128["projected_days_for_800_epochs"]),

        "COMP_XPU_005_full_training_authorized":
            False,

        "B2W_authorized":
            bool(ok),

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2W-XPU — no-update exact corrected-graph performance "
                "bottleneck audit at microbatch 128 with matched first-order control"
                if ok else
                "V16E-1B2V-R1 — diagnose B2U interpretation/protocol gate failure"
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

    print("\nB2U INTERPRETATION")
    print(
        "  throughput 32/64/128:",
        f"{throughput[32]:.3f} / "
        f"{throughput[64]:.3f} / "
        f"{throughput[128]:.3f} profiles/s",
    )
    print(
        "  microbatch 128 projection:",
        f"{p128['projected_hours_per_epoch']:.3f} h/epoch, "
        f"{p128['projected_days_for_800_epochs']:.3f} d/800ep",
    )
    print(
        "  microbatch 256 frozen failure class:",
        mb256_failure_class,
    )
    print("  microbatch 128: reference only; NOT final training value.")

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
