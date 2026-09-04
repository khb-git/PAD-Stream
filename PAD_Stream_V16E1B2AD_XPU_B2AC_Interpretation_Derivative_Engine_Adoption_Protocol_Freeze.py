#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2AD-XPU
B2AC Chunked Batched-VJP Interpretation
+ Derivative-Engine Adoption Protocol Freeze

Purpose
-------
Interpret the completed V16E-1B2AC chunked batched-VJP sweep and freeze the
implementation route for the prospective corrected Stage-2 experiment.

NO TRAINING.
NO OPTIMIZER.
NO OPTIMIZER STEP.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

B2AC certified evidence
-----------------------
Reference microbatch:
    128

Exact loop baseline:
    median 10.102 s
    throughput 12.670 profiles/s

Chunked batched-VJP candidates:
    chunk 2   : fully equivalent, median 10.101 s
    chunk 4   : fully equivalent, median  8.583 s
    chunk 8   : fully equivalent, median  7.928 s
    chunk 16  : fully equivalent, median  7.867 s
    chunk 32  : fully equivalent, median  8.039 s

All five candidates:
    * runtime-successful
    * derivative-equivalent
    * corrected-residual-equivalent
    * physics-loss-equivalent
    * total-loss-equivalent
    * parameter-gradient-equivalent
    * no fallback
    * no optimizer
    * no weight update
    * frozen COMP-XPU-004 checkpoint unchanged

B2AC descriptive fastest:
    chunk 16

Interpretation
--------------
Chunk 16 is adopted as the prospective derivative-engine implementation for
COMP-XPU-005 because:

    1. It passed the complete frozen implementation-equivalence firewall.
    2. It produced the lowest median wall time in the frozen B2AC sweep.
    3. It uses less simultaneous cotangent batching than chunk 32.

This is an operational implementation selection.

It does NOT claim:
    * statistical superiority over chunks 8 or 32;
    * a new scientific model;
    * a new physics loss;
    * a new derivative definition.

The exact derivatives remain:
    N_xi(j) = dN_j/dxi_j
    N_tD(j) = dN_j/dp11[tD]
    N_X(j)  = dN_j/dp11[xD_star]

The corrected conservative Stage-2 residual remains unchanged.

Prospective execution geometry
------------------------------
Frozen Stage-2 geometry remains:
    train profiles = 11520
    logical batch  = 8192
    microbatch     = 128
    target epochs  = 800

Using the B2AC chunk-16 isolated median only as an operational diagnostic:
    microbatches/epoch = 90

The resulting full-run projection is frozen as a diagnostic only,
not a runtime promise.

Next milestone
--------------
V16E-1B2AE-XPU

Freeze the COMP-XPU-005 execution-preflight contract using:

    derivative engine:
        chunked batched-VJP, chunk size 16

    microbatch:
        128

    exact scientific settings:
        frozen from COMP-XPU-004 / B2R / B2Z

B2AE must define the exact prospective training runner and a fail-closed
execution preflight before the 800-epoch run is authorized.

COMP-XPU-005 full training remains NOT authorized in B2AD.
B3 remains blocked.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import sys


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2AD-XPU"

REFERENCE_MICROBATCH = 128
ADOPTED_CHUNK = 16
CANDIDATES = [2, 4, 8, 16, 32]

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

# Training geometry authority.
B2U_DIR = (
    R / "output"
    / "V16_E1B2U_XPU_EXTENDED_CORRECTED_RESIDUAL_THROUGHPUT"
)
B2U_RESULTS = B2U_DIR / "V16E1B2U_Extended_Throughput_Memory_Results.json"
B2U_RESULTS_SHA = "e71f398c88feee2260c50109055b917103e76800365954823f320457a0d30075"

# B2AC execution authority.
B2AC_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AC_XPU_Chunked_Batched_VJP_Equivalence_Performance_Sweep.py"
)
B2AC_SOURCE_SHA = "59f7ea7b0dc2e901f5a42649691c2dab5f4dfc5d399f953eaab5ba773040cd53"

B2AC_DIR = (
    R / "output"
    / "V16_E1B2AC_XPU_CHUNKED_BATCHED_VJP_SWEEP"
)
B2AC_BASELINE_JSON = (
    B2AC_DIR / "loop_baseline"
    / "V16E1B2AC_Loop_Baseline.json"
)
B2AC_BASELINE_TENSOR = (
    B2AC_DIR / "loop_baseline"
    / "V16E1B2AC_Loop_Baseline_Tensors.pt"
)
B2AC_RESULTS = B2AC_DIR / "V16E1B2AC_Chunked_Batched_VJP_Sweep_Results.json"
B2AC_DECISION = B2AC_DIR / "V16E1B2AC_Chunked_Batched_VJP_Measurement_Decision.json"
B2AC_SUMMARY = B2AC_DIR / "PAD_Stream_V16E1B2AC_XPU_Summary.json"

B2AC_BASELINE_JSON_SHA = "6e40d16d2f7a6f6f29d374bff9c6ac95816f21569a8f307edf35ca116f5fa5cd"
B2AC_BASELINE_TENSOR_SHA = "7d0beaf0b00564f6965c9862c09c619a4c5b00d058fe0885bb911972e0325d57"
B2AC_RESULTS_SHA = "b2e6ac1f4483af1429f0e5cf4fe56d51024d0f0009dae008a64c3d1550cf3e34"
B2AC_DECISION_SHA = "4250cece29966553f9a3ef1ce9b8cc860b00cb853b5d875625a200b9e7daf5dc"
B2AC_SUMMARY_SHA = "810b2a8b1d3d7c6597cb3b48d751c4a89c86eee8bc2cc34eb16e5731e86a9ff7"

EXPECTED_B2AC_STATUS = (
    "V16E1B2AC_XPU_CHUNKED_BATCHED_VJP_SUBPROCESS_ISOLATED_EQUIVALENCE_AND_WARMED_PERFORMANCE_SWEEP_COMPLETE_"
    "EXACT_LOOP_BASELINE_DERIVATIVES_CORRECTED_GRAPH_PARAMETER_GRADIENTS_AND_WARMED_PERFORMANCE_SHA_BOUND_"
    "CHUNKS_2_4_8_16_32_ATTEMPTED_IN_FRESH_XPU_SUBPROCESSES_"
    "RUNTIME_DERIVATIVE_FULL_GRAPH_PARAMETER_GRADIENT_AND_PERFORMANCE_RESULTS_FROZEN_"
    "NO_AUTOMATIC_CANDIDATE_ADOPTION_NO_FALLBACK_NO_SCIENTIFIC_GRAPH_CHANGE_"
    "NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_"
    "B2AD_CHUNK_SWEEP_INTERPRETATION_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2AD_XPU_CHUNKED_VJP_ADOPTION_PROTOCOL"
)
OUT.mkdir(parents=True, exist_ok=True)

INTERPRETATION = OUT / "V16E1B2AD_B2AC_Interpretation.json"
ADOPTION = OUT / "V16E1B2AD_Derivative_Engine_Adoption.json"
B2AE_PROTOCOL = OUT / "V16E1B2AD_B2AE_Execution_Preflight_Protocol.json"
HANDOFF = OUT / "V16E1B2AD_B2AE_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2AD_XPU_Summary.json"


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


def microbatches_per_epoch(n_train: int, logical_batch: int, microbatch: int) -> int:
    total = 0

    for b0 in range(0, n_train, logical_batch):
        chunk = min(logical_batch, n_train - b0)
        total += int(math.ceil(chunk / microbatch))

    return total


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2AD-XPU")
    print("B2AC Chunked Batched-VJP Interpretation")
    print("+ Derivative-Engine Adoption Protocol Freeze")
    print("=" * 80)
    print("PROTOCOL ONLY — NO TRAINING — NO OPTIMIZER.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2AD summary already exists; refusing overwrite."
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

        "B2AC_source_SHA_exact":
            exact(B2AC_SOURCE, B2AC_SOURCE_SHA),

        "B2AC_baseline_JSON_SHA_exact":
            exact(B2AC_BASELINE_JSON, B2AC_BASELINE_JSON_SHA),

        "B2AC_baseline_tensor_SHA_exact":
            exact(B2AC_BASELINE_TENSOR, B2AC_BASELINE_TENSOR_SHA),

        "B2AC_results_SHA_exact":
            exact(B2AC_RESULTS, B2AC_RESULTS_SHA),

        "B2AC_decision_SHA_exact":
            exact(B2AC_DECISION, B2AC_DECISION_SHA),

        "B2AC_summary_SHA_exact":
            exact(B2AC_SUMMARY, B2AC_SUMMARY_SHA),
    }

    b2ac = read_json(B2AC_RESULTS) if B2AC_RESULTS.exists() else {}
    b2ac_decision = read_json(B2AC_DECISION) if B2AC_DECISION.exists() else {}
    b2ac_summary = read_json(B2AC_SUMMARY) if B2AC_SUMMARY.exists() else {}
    b2u = read_json(B2U_RESULTS) if B2U_RESULTS.exists() else {}

    gates.update({
        "B2AC_status_exact":
            b2ac_summary.get("status") == EXPECTED_B2AC_STATUS,

        "B2AC_runtime_success_all":
            b2ac.get("runtime_successful_chunks") == CANDIDATES,

        "B2AC_derivative_equivalent_all":
            b2ac.get("derivative_equivalent_chunks") == CANDIDATES,

        "B2AC_fully_equivalent_all":
            b2ac.get("fully_equivalent_chunks") == CANDIDATES,

        "B2AC_performance_all":
            b2ac.get("performance_measured_chunks") == CANDIDATES,

        "B2AC_descriptive_fastest_16":
            b2ac.get("descriptive_fastest_equivalent_measured_chunk")
            == ADOPTED_CHUNK,

        "B2AC_candidate_adopted_false":
            b2ac.get("candidate_adopted") is False,

        "B2AC_no_fallback":
            b2ac.get("fallback_used") is False,

        "B2AC_no_optimizer":
            b2ac.get("optimizer_created") is False,

        "B2AC_no_optimizer_step":
            b2ac.get("optimizer_step") is False,

        "B2AC_no_weight_update":
            b2ac.get("weight_update") is False,

        "B2AC_graph_unchanged":
            b2ac.get("scientific_graph_changed") is False,

        "B2AC_training_false":
            b2ac.get("COMP_XPU_005_full_training_authorized") is False,

        "B2AC_B3_false":
            b2ac.get("B3_authorized") is False,

        "B2AC_decision_candidate_adopted_false":
            b2ac_decision.get("candidate_adopted") is False,
    })

    perf = b2ac.get("measured_performance", {})

    gates.update({
        "performance_keys_exact":
            set(perf.keys()) == {str(c) for c in CANDIDATES},

        "all_candidate_medians_finite":
            all(
                finite(perf[str(c)].get("median_seconds"))
                for c in CANDIDATES
            ),

        "all_candidate_means_finite":
            all(
                finite(perf[str(c)].get("mean_seconds"))
                for c in CANDIDATES
            ),

        "all_candidate_throughputs_finite":
            all(
                finite(perf[str(c)].get("median_profiles_per_second"))
                for c in CANDIDATES
            ),

        "chunk16_is_measured_minimum":
            float(perf["16"]["median_seconds"])
            == min(
                float(perf[str(c)]["median_seconds"])
                for c in CANDIDATES
            ),
    })

    # Training geometry is bound from the already-frozen B2U results artifact.
    split = b2u.get("training_split", {})

    n_train = int(split.get("train_profiles", 0))
    logical_batch = int(split.get("logical_batch", 0))
    target_epochs = int(split.get("target_epochs", 0))

    gates.update({
        "train_profiles_11520":
            n_train == 11520,

        "logical_batch_8192":
            logical_batch == 8192,

        "target_epochs_800":
            target_epochs == 800,

        "reference_microbatch_128":
            REFERENCE_MICROBATCH == 128,
    })

    print("AUTHORITY / ADOPTION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "B2AD blocked by authority or B2AC evidence mismatch."
        )

    loop_median = float(
        b2ac["reference"]["loop_baseline_performance_median_seconds"]
    )

    chunk16_median = float(
        perf["16"]["median_seconds"]
    )

    chunk16_mean = float(
        perf["16"]["mean_seconds"]
    )

    chunk16_throughput = float(
        perf["16"]["median_profiles_per_second"]
    )

    loop_over_chunk16 = float(
        perf["16"]["loop_over_candidate_median_ratio"]
    )

    n_micro = microbatches_per_epoch(
        n_train=n_train,
        logical_batch=logical_batch,
        microbatch=REFERENCE_MICROBATCH,
    )

    projected_epoch_seconds = float(
        n_micro * chunk16_median
    )

    projected_hours_per_epoch = float(
        projected_epoch_seconds / 3600.0
    )

    projected_days_for_target = float(
        projected_epoch_seconds
        * target_epochs
        / 86400.0
    )

    interpretation = {
        "milestone":
            MILESTONE,

        "classification":
            "B2AC_CHUNKED_BATCHED_VJP_SWEEP_INTERPRETATION",

        "B2AC_execution_status":
            "CERTIFIED",

        "measured_candidates":
            {
                str(c): {
                    "median_seconds":
                        float(perf[str(c)]["median_seconds"]),

                    "mean_seconds":
                        float(perf[str(c)]["mean_seconds"]),

                    "median_profiles_per_second":
                        float(
                            perf[str(c)]["median_profiles_per_second"]
                        ),

                    "loop_over_candidate_median_ratio":
                        float(
                            perf[str(c)]["loop_over_candidate_median_ratio"]
                        ),
                }
                for c in CANDIDATES
            },

        "all_candidates_fully_equivalent":
            True,

        "descriptive_fastest_chunk":
            ADOPTED_CHUNK,

        "selection_interpretation":
            "Chunk 16 is the lowest-median fully-equivalent candidate in the frozen "
            "B2AC sweep. The selection is operational and does not claim statistical "
            "superiority over nearby candidates.",

        "prohibited_claims": [
            "chunk 16 changes the scientific model",
            "chunk 16 changes the corrected residual",
            "chunk 16 changes any Stage-2 loss weight",
            "chunk 16 is statistically proven faster than chunk 8 or chunk 32",
            "chunk 16 is a new derivative definition",
        ],

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

    adoption = {
        "milestone":
            MILESTONE,

        "classification":
            "PROSPECTIVE_COMP_XPU_005_DERIVATIVE_ENGINE_ADOPTION",

        "adopted_engine":
            "CHUNKED_BATCHED_VJP",

        "cotangent_chunk_size":
            ADOPTED_CHUNK,

        "reference_microbatch":
            REFERENCE_MICROBATCH,

        "equivalence_basis":
            {
                "B2AC_results_sha256":
                    B2AC_RESULTS_SHA,

                "derivative_equivalence":
                    True,

                "corrected_residual_equivalence":
                    True,

                "physics_loss_equivalence":
                    True,

                "total_loss_equivalence":
                    True,

                "parameter_gradient_equivalence":
                    True,

                "identity_budget":
                    "frozen float32-machine-epsilon-derived computational budget",
            },

        "performance_basis":
            {
                "loop_baseline_median_seconds":
                    loop_median,

                "chunk16_median_seconds":
                    chunk16_median,

                "chunk16_mean_seconds":
                    chunk16_mean,

                "chunk16_median_profiles_per_second":
                    chunk16_throughput,

                "loop_over_chunk16_median_ratio":
                    loop_over_chunk16,

                "interpretation":
                    "frozen B2AC measurement; operational selection only",
            },

        "scientific_graph_frozen":
            True,

        "architecture_frozen":
            True,

        "corrected_residual_frozen":
            True,

        "losses_and_weights_frozen":
            True,

        "dataset_frozen":
            True,

        "physical_Nc_frozen":
            True,

        "training_authorized":
            False,
    }

    ADOPTION.write_text(
        json.dumps(adoption, indent=2),
        encoding="utf-8",
    )

    b2ae_protocol = {
        "milestone":
            MILESTONE,

        "authorized_next_milestone":
            "V16E-1B2AE-XPU",

        "classification":
            "COMP_XPU_005_EXECUTION_PREFLIGHT_PROTOCOL_FREEZE",

        "prospective_experiment":
            "V16E-BLREP-COMP-XPU-005",

        "implementation_contract": {
            "derivative_engine":
                "CHUNKED_BATCHED_VJP",

            "cotangent_chunk_size":
                ADOPTED_CHUNK,

            "microbatch":
                REFERENCE_MICROBATCH,

            "logical_batch":
                logical_batch,

            "target_epochs":
                target_epochs,

            "scientific_graph_source":
                "exact frozen B2S corrected Stage-2 graph",

            "scientific_change":
                False,
        },

        "frozen_training_geometry": {
            "train_profiles":
                n_train,

            "microbatches_per_epoch":
                n_micro,

            "logical_batch":
                logical_batch,

            "microbatch":
                REFERENCE_MICROBATCH,

            "target_epochs":
                target_epochs,
        },

        "diagnostic_projection_from_B2AC_chunk16": {
            "chunk16_median_seconds":
                chunk16_median,

            "projected_seconds_per_epoch":
                projected_epoch_seconds,

            "projected_hours_per_epoch":
                projected_hours_per_epoch,

            "projected_days_for_target_epochs":
                projected_days_for_target,

            "semantics":
                "operational diagnostic only; not a runtime promise",
        },

        "B2AE_requirements": [
            "bind the exact chunk-16 derivative implementation",
            "bind exact source and artifact SHAs",
            "bind exact COMP-XPU-005 scientific settings",
            "define fail-closed prospective training runner behavior",
            "define checkpoint/resume behavior",
            "define optimizer and gradient-accumulation contract",
            "define a no-OOD/no-TOF execution preflight",
            "do not authorize the 800-epoch run unless all execution-preflight gates pass",
        ],

        "scientific_firewall": {
            "training_in_B2AD":
                False,

            "optimizer_in_B2AD":
                False,

            "optimizer_step_in_B2AD":
                False,

            "weight_update_in_B2AD":
                False,

            "scientific_settings_changed":
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

    B2AE_PROTOCOL.write_text(
        json.dumps(b2ae_protocol, indent=2),
        encoding="utf-8",
    )

    handoff = (
        "# V16E-1B2AD-XPU — B2AE Execution-Preflight Handoff\n\n"
        "## Adopted derivative implementation\n\n"
        "* Engine: chunked batched VJP\n"
        "* Cotangent chunk size: 16\n"
        "* Reference training microbatch: 128\n\n"
        "The adoption is implementation-only. B2AC certified derivative, corrected "
        "residual, losses, and parameter-gradient equivalence to the exact loop "
        "baseline.\n\n"
        "## Performance basis\n\n"
        f"* Loop baseline median: {loop_median:.6f} s\n"
        f"* Chunk-16 median: {chunk16_median:.6f} s\n"
        f"* Loop/chunk-16 ratio: {loop_over_chunk16:.6f}x\n"
        f"* Chunk-16 throughput: {chunk16_throughput:.6f} profiles/s\n\n"
        "Chunk 16 was the lowest measured median in B2AC. This is not a statistical "
        "superiority claim over chunk 8 or 32.\n\n"
        "## Diagnostic execution geometry\n\n"
        f"* Train profiles: {n_train}\n"
        f"* Logical batch: {logical_batch}\n"
        f"* Microbatch: {REFERENCE_MICROBATCH}\n"
        f"* Microbatches/epoch: {n_micro}\n"
        f"* Target epochs: {target_epochs}\n"
        f"* Diagnostic projection: {projected_hours_per_epoch:.6f} h/epoch, "
        f"{projected_days_for_target:.6f} days/{target_epochs} epochs\n\n"
        "The projection is not a runtime promise.\n\n"
        "## Next\n\n"
        "B2AE must freeze the exact COMP-XPU-005 execution-preflight contract, "
        "including optimizer, accumulation, checkpoint/resume, and fail-closed "
        "training-runner behavior. Full training remains blocked until B2AE passes.\n\n"
        "B3 remains blocked.\n"
    )

    HANDOFF.write_text(
        handoff,
        encoding="utf-8",
    )

    gates.update({
        "interpretation_written":
            INTERPRETATION.exists()
            and INTERPRETATION.stat().st_size > 0,

        "adoption_written":
            ADOPTION.exists()
            and ADOPTION.stat().st_size > 0,

        "B2AE_protocol_written":
            B2AE_PROTOCOL.exists()
            and B2AE_PROTOCOL.stat().st_size > 0,

        "handoff_written":
            HANDOFF.exists()
            and HANDOFF.stat().st_size > 0,

        "chunk16_adopted_as_implementation_only":
            True,

        "scientific_graph_unchanged":
            True,

        "B2AE_authorized":
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
        "V16E1B2AD_XPU_B2AC_CHUNKED_BATCHED_VJP_INTERPRETATION_AND_DERIVATIVE_ENGINE_ADOPTION_PROTOCOL_FROZEN_"
        "ALL_CHUNKS_2_4_8_16_32_RUNTIME_SUCCESSFUL_FULLY_EQUIVALENT_AND_PERFORMANCE_MEASURED_"
        "CHUNK_16_ADOPTED_AS_PROSPECTIVE_COMP_XPU_005_IMPLEMENTATION_ROUTE_BASED_ON_LOWEST_FROZEN_B2AC_MEDIAN_"
        "WITHOUT_STATISTICAL_SUPERIORITY_CLAIM_OR_SCIENTIFIC_GRAPH_CHANGE_"
        "MICROBATCH_128_LOGICAL_BATCH_8192_AND_800_EPOCH_GEOMETRY_PRESERVED_"
        "B2AE_EXECUTION_PREFLIGHT_PROTOCOL_AUTHORIZED_NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
        "COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2AD_XPU_PROTOCOL_FREEZE_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "interpretation_sha256":
            sha256(INTERPRETATION),

        "adoption_sha256":
            sha256(ADOPTION),

        "B2AE_protocol_sha256":
            sha256(B2AE_PROTOCOL),

        "handoff_sha256":
            sha256(HANDOFF),

        "adopted_derivative_engine":
            "CHUNKED_BATCHED_VJP",

        "adopted_cotangent_chunk_size":
            ADOPTED_CHUNK,

        "reference_microbatch":
            REFERENCE_MICROBATCH,

        "loop_baseline_median_seconds":
            loop_median,

        "chunk16_median_seconds":
            chunk16_median,

        "loop_over_chunk16_median_ratio":
            loop_over_chunk16,

        "chunk16_median_profiles_per_second":
            chunk16_throughput,

        "diagnostic_hours_per_epoch":
            projected_hours_per_epoch,

        "diagnostic_days_for_target_epochs":
            projected_days_for_target,

        "B2AE_authorized":
            bool(ok),

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2AE-XPU — freeze exact COMP-XPU-005 execution-preflight "
                "contract using chunked batched VJP chunk=16 and microbatch=128; "
                "bind optimizer, gradient accumulation, checkpoint/resume, and "
                "fail-closed prospective runner behavior before full training"
                if ok else
                "V16E-1B2AD-R1 — diagnose B2AC interpretation/adoption gate failure"
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

    print("\nB2AC ADOPTION INTERPRETATION")
    print("  loop median       :", f"{loop_median:.3f} s")
    print("  chunk 16 median   :", f"{chunk16_median:.3f} s")
    print("  loop/chunk 16     :", f"{loop_over_chunk16:.3f}x")
    print("  chunk 16 throughput:", f"{chunk16_throughput:.3f} profiles/s")
    print("  adopted engine    : CHUNKED_BATCHED_VJP")
    print("  adopted chunk     :", ADOPTED_CHUNK)
    print("  interpretation    : implementation-only; no statistical superiority claim")
    print(
        "  diagnostic projection:",
        f"{projected_hours_per_epoch:.3f} h/epoch, "
        f"{projected_days_for_target:.3f} d/{target_epochs}ep",
    )

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Interpretation:", sha256(INTERPRETATION))
    print("  Adoption      :", sha256(ADOPTION))
    print("  B2AE Protocol :", sha256(B2AE_PROTOCOL))
    print("  Handoff       :", sha256(HANDOFF))
    print("  Summary       :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
