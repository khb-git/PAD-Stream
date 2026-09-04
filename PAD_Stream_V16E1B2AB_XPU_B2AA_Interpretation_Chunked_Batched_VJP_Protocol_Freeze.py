#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2AB-XPU
B2AA Runtime-Resource Interpretation
+ Chunked Batched-VJP Optimization Protocol Freeze

Purpose
-------
Interpret V16E-1B2AA without over-claiming its Level Zero / Unified Runtime
failure, and authorize the next equivalence-preserving derivative-engine route.

NO TRAINING.
NO OPTIMIZER.
NO OPTIMIZER STEP.
NO WEIGHT UPDATE.
NO CHECKPOINT MUTATION.
NO OOD.
NO TOF.

B2AA certified result
---------------------
The full 64-cotangent batched-VJP attempt at reference microbatch 128 failed:

    RuntimeError:
    level_zero backend failed with error: 40
    (UR_RESULT_ERROR_OUT_OF_RESOURCES)

B2AA used:
    torch.autograd.grad(..., is_grads_batched=True)

with all 64 one-hot sequence-output cotangents in one call.

No fallback was used.
No performance benchmark was run.
No optimizer existed.
No weight update occurred.
The scientific graph and frozen COMP-XPU-004 checkpoint were preserved.

Interpretation
--------------
The exact runtime evidence DOES support:

    FULL_64_COTANGENT_BATCHED_VJP_NOT_OPERATIONALLY_VIABLE
    ON_THE_CURRENT_INTEL_XPU_CONFIGURATION

The evidence DOES NOT by itself support:

    * is_grads_batched=True is universally unsupported;
    * the Intel XPU cannot execute any batched VJP;
    * the failure is necessarily an out-of-memory condition;
    * the failure is a scientific-model incompatibility.

The runtime specifically reported UR_RESULT_ERROR_OUT_OF_RESOURCES.
B2AB preserves that exact classification and does not silently relabel it.

Next equivalence-preserving route
---------------------------------
V16E-1B2AC-XPU

CHUNKED_BATCHED_VJP

Instead of one VJP call per sequence node (64 calls) or one giant VJP call
containing all 64 cotangents, partition the 64 output nodes into contiguous
chunks.

Authorized cotangent chunk sizes:

    2, 4, 8, 16, 32

Known endpoints:
    chunk = 1:
        certified loop-style baseline semantics

    chunk = 64:
        frozen B2AA UR_RESULT_ERROR_OUT_OF_RESOURCES at microbatch 128

For a chunk j0:j1 of size K:

    V_chunk shape:
        [K, B, T, 1]

    torch.autograd.grad(
        outputs=S_pred,
        inputs=(xi,p11),
        grad_outputs=V_chunk,
        create_graph=True,
        retain_graph=True,
        is_grads_batched=True
    )

Extract exactly:

    N_xi[:,j,:] = dN_j/dxi_j
    N_tD[:,j,:] = dN_j/dp11[tD]
    N_X[:,j,:]  = dN_j/dp11[xD_star]

for every j in the chunk.

Concatenate chunks in original sequence order.

Scientific graph frozen
-----------------------
The following MUST NOT change:

    * frozen COMP-XPU-004 checkpoint
    * [xi, eta] sequence architecture
    * raw physical 11-D p11
    * physical Nc
    * Rankine-Hugoniot front-speed closure
    * corrected conservative moving-fan residual
    * fractional-flow physics
    * all Stage-2 loss terms and weights
    * exact Stage-2 dataset
    * exact B2U/B2Y reference microbatch=128 rows
    * no OOD
    * no TOF

B2AC required execution structure
---------------------------------
Each chunk candidate must run in a FRESH subprocess / XPU context so a
resource failure cannot contaminate another candidate.

For each chunk size 2,4,8,16,32:

A. Runtime feasibility:
    attempt exact chunked local derivatives at microbatch 128.

B. If runtime succeeds, equivalence BEFORE performance:
    compare against the exact loop baseline:
        N_xi
        N_tD
        N_X
        corrected residual
        physics loss
        complete total loss
        every model-parameter gradient after backward

    Use only the already-frozen float32-machine-epsilon-derived computational
    identity budget:
        1024 * eps_float32 * max(1, |reference|, |candidate|)

C. Only if full equivalence passes:
    performance:
        1 unmeasured warm-up
        3 measured uninstrumented repeats

D. Record:
    exact runtime result
    exact error text if failed
    derivative / residual / loss / gradient identity results
    median and mean wall time
    profiles/s
    peak XPU memory if available
    exact parameter equality
    exact checkpoint SHA equality

E. No silent fallback.

Selection semantics
-------------------
B2AC does NOT automatically adopt the fastest chunk.

It binds measured runtime/equivalence/performance results only.

B2AD must interpret the candidate set and select an implementation route.

No scientific numerical acceptance threshold is introduced.

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
MILESTONE = "V16E-1B2AB-XPU"

REFERENCE_MICROBATCH = 128
CHUNK_CANDIDATES = [2, 4, 8, 16, 32]
KNOWN_LOOP_CHUNK = 1
KNOWN_FAILED_FULL_CHUNK = 64

FLOAT32_EPS = 1.1920928955078125e-07
IDENTITY_EPS_MULTIPLIER = 1024.0

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

# Exact corrected graph.
B2S_SOURCE = (
    R
    / "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
)
B2S_SOURCE_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"

# Exact reference rows.
B2U_DIR = (
    R / "output"
    / "V16_E1B2U_XPU_EXTENDED_CORRECTED_RESIDUAL_THROUGHPUT"
)
B2U_RESULTS = B2U_DIR / "V16E1B2U_Extended_Throughput_Memory_Results.json"
B2U_RESULTS_SHA = "e71f398c88feee2260c50109055b917103e76800365954823f320457a0d30075"

# Warmed baseline authority.
B2Y_DIR = (
    R / "output"
    / "V16_E1B2Y_XPU_WARMED_STEADY_STATE_EXACT_GRAPH_BENCHMARK"
)
B2Y_RESULTS = B2Y_DIR / "V16E1B2Y_Warmed_Steady_State_Results.json"
B2Y_RESULTS_SHA = "32d5a9a1e8c0970a497fe81dffb5c877d8ac23439a463d701e1d9b0bcd163b16"

# B2Z protocol authority.
B2Z_DIR = (
    R / "output"
    / "V16_E1B2Z_XPU_B2Y_INTERPRETATION_DERIVATIVE_ENGINE_OPTIMIZATION_PROTOCOL"
)
B2Z_PROTOCOL = B2Z_DIR / "V16E1B2Z_B2AA_Batched_VJP_Optimization_Protocol.json"
B2Z_SUMMARY = B2Z_DIR / "PAD_Stream_V16E1B2Z_XPU_Summary.json"

B2Z_PROTOCOL_SHA = "f2c5c120cbacd4d5066d88a85ede85e85dcc4d389287994e902fd828f94531ef"
B2Z_SUMMARY_SHA = "936d32fb671f308d7118316334fbe5eecda5ad54f8f145ab3b41752896ec9567"

# B2AA source and certified runtime-failure artifacts.
B2AA_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AA_XPU_Batched_VJP_Equivalence_Performance_Audit.py"
)
B2AA_SOURCE_SHA = "2306ea121d5aead6de1a710cbe4b2eeee688ec03039fb1a4f252a966da1f048c"

B2AA_DIR = (
    R / "output"
    / "V16_E1B2AA_XPU_BATCHED_VJP_EQUIVALENCE_PERFORMANCE_AUDIT"
)
B2AA_RESULTS = B2AA_DIR / "V16E1B2AA_Batched_VJP_Equivalence_Performance_Results.json"
B2AA_DECISION = B2AA_DIR / "V16E1B2AA_Batched_VJP_Decision.json"
B2AA_SUMMARY = B2AA_DIR / "PAD_Stream_V16E1B2AA_XPU_Summary.json"

B2AA_RESULTS_SHA = "05313d8400067592d181541efb88c92cae6980e96a4b7d334c4beeedc97309e0"
B2AA_DECISION_SHA = "d8f45f9c9dba02816ced6554b6c97b5ed76a00cdd50e370697326b621f91695d"
B2AA_SUMMARY_SHA = "43ea0981e3b0076aadc8f25f4cc366029839e9882aa660eb35c0dee6dd7f73f0"

EXPECTED_B2AA_STATUS = (
    "V16E1B2AA_XPU_BATCHED_VJP_EQUIVALENCE_AUDIT_COMPLETE_"
    "IS_GRADS_BATCHED_TRUE_RUNTIME_FAILURE_RECORDED_EXACTLY_NO_FALLBACK_"
    "SCIENTIFIC_GRAPH_COMP_XPU_004_CHECKPOINT_AND_NO_UPDATE_FIREWALL_PRESERVED_"
    "PERFORMANCE_BENCHMARK_NOT_RUN_B2AB_IMPLEMENTATION_INTERPRETATION_REQUIRED_"
    "COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
)

EXPECTED_RUNTIME_FRAGMENT = "UR_RESULT_ERROR_OUT_OF_RESOURCES"

OUT = (
    R / "output"
    / "V16_E1B2AB_XPU_B2AA_INTERPRETATION_CHUNKED_BATCHED_VJP_PROTOCOL"
)
OUT.mkdir(parents=True, exist_ok=True)

INTERPRETATION = OUT / "V16E1B2AB_B2AA_Runtime_Interpretation.json"
PROTOCOL = OUT / "V16E1B2AB_B2AC_Chunked_Batched_VJP_Protocol.json"
HANDOFF = OUT / "V16E1B2AB_B2AC_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2AB_XPU_Summary.json"


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


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2AB-XPU")
    print("B2AA Runtime-Resource Interpretation")
    print("+ Chunked Batched-VJP Optimization Protocol Freeze")
    print("=" * 80)
    print("PROTOCOL ONLY — NO TRAINING — NO OPTIMIZER.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2AB summary already exists; refusing overwrite."
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

        "B2Y_results_SHA_exact":
            exact(B2Y_RESULTS, B2Y_RESULTS_SHA),

        "B2Z_protocol_SHA_exact":
            exact(B2Z_PROTOCOL, B2Z_PROTOCOL_SHA),

        "B2Z_summary_SHA_exact":
            exact(B2Z_SUMMARY, B2Z_SUMMARY_SHA),

        "B2AA_source_SHA_exact":
            exact(B2AA_SOURCE, B2AA_SOURCE_SHA),

        "B2AA_results_SHA_exact":
            exact(B2AA_RESULTS, B2AA_RESULTS_SHA),

        "B2AA_decision_SHA_exact":
            exact(B2AA_DECISION, B2AA_DECISION_SHA),

        "B2AA_summary_SHA_exact":
            exact(B2AA_SUMMARY, B2AA_SUMMARY_SHA),
    }

    b2aa_results = read_json(B2AA_RESULTS) if B2AA_RESULTS.exists() else {}
    b2aa_decision = read_json(B2AA_DECISION) if B2AA_DECISION.exists() else {}
    b2aa_summary = read_json(B2AA_SUMMARY) if B2AA_SUMMARY.exists() else {}
    b2z_protocol = read_json(B2Z_PROTOCOL) if B2Z_PROTOCOL.exists() else {}
    b2u = read_json(B2U_RESULTS) if B2U_RESULTS.exists() else {}

    runtime_error = b2aa_results.get("runtime_error", "")

    gates.update({
        "B2AA_status_exact":
            b2aa_summary.get("status") == EXPECTED_B2AA_STATUS,

        "B2AA_batched_supported_false":
            b2aa_summary.get("batched_vjp_supported") is False,

        "B2AA_equivalence_false":
            b2aa_summary.get("equivalence_pass") is False,

        "B2AA_performance_false":
            b2aa_summary.get("performance_benchmark_run") is False,

        "B2AA_training_false":
            b2aa_summary.get("COMP_XPU_005_full_training_authorized") is False,

        "B2AA_B3_false":
            b2aa_summary.get("B3_authorized") is False,

        "B2AA_results_fallback_false":
            b2aa_results.get("fallback_used") is False,

        "B2AA_results_weight_update_false":
            b2aa_results.get("weight_update") is False,

        "B2AA_runtime_error_fragment_exact":
            EXPECTED_RUNTIME_FRAGMENT in runtime_error,

        "B2AA_decision_adoptable_false":
            b2aa_decision.get("batched_vjp_adoptable") is False,

        "B2Z_reference_128":
            (
                b2z_protocol
                .get("reference", {})
                .get("microbatch")
                == REFERENCE_MICROBATCH
            ),

        "B2Z_identity_eps_exact":
            (
                b2z_protocol
                .get("equivalence_verification", {})
                .get("identity_budget", {})
                .get("float32_epsilon")
                == FLOAT32_EPS
            ),

        "B2Z_identity_multiplier_exact":
            (
                b2z_protocol
                .get("equivalence_verification", {})
                .get("identity_budget", {})
                .get("multiplier")
                == IDENTITY_EPS_MULTIPLIER
            ),
    })

    # Preserve exact 128 B2U reference rows.
    ref_ids = None
    for rec in b2u.get("candidate_results", []):
        if int(rec.get("microbatch", -1)) == REFERENCE_MICROBATCH:
            ref_ids = rec.get("dataset_indices")
            break

    gates.update({
        "B2U_reference_ids_present":
            isinstance(ref_ids, list)
            and len(ref_ids) == REFERENCE_MICROBATCH,

        "chunk_candidates_exact":
            CHUNK_CANDIDATES == [2, 4, 8, 16, 32],

        "known_loop_endpoint_1":
            KNOWN_LOOP_CHUNK == 1,

        "known_failed_full_endpoint_64":
            KNOWN_FAILED_FULL_CHUNK == 64,
    })

    print("AUTHORITY / INTERPRETATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "B2AB blocked by authority or B2AA evidence mismatch."
        )

    interpretation = {
        "milestone":
            MILESTONE,

        "classification":
            "B2AA_FULL_BATCHED_VJP_RUNTIME_RESOURCE_INTERPRETATION",

        "B2AA_execution_status":
            "CERTIFIED_FAIL_CLOSED_RUNTIME_RESULT",

        "exact_runtime_error":
            runtime_error,

        "frozen_runtime_token":
            EXPECTED_RUNTIME_FRAGMENT,

        "supported_conclusions": [
            "The 64-cotangent single-call batched VJP is not operationally viable "
            "at microbatch 128 on the current Intel-XPU/runtime configuration.",
            "B2AA preserved the scientific graph and checkpoint.",
            "B2AA used no fallback and produced no performance benchmark.",
        ],

        "prohibited_conclusions": [
            "is_grads_batched=True is universally unsupported",
            "all batched VJP sizes will fail",
            "the error is definitively an OOM",
            "the error proves a scientific-model incompatibility",
            "microbatch 128 itself is invalid for the loop baseline",
        ],

        "next_route":
            "CHUNKED_BATCHED_VJP",

        "route_rationale":
            "The resource failure occurred for the maximum 64-cotangent VJP batch. "
            "Chunking preserves the same derivatives while reducing simultaneous "
            "batched-VJP resource demand and still reducing the 64-call loop count.",

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
            "V16E-1B2AC-XPU",

        "classification":
            "SUBPROCESS_ISOLATED_CHUNKED_BATCHED_VJP_EQUIVALENCE_PERFORMANCE_SWEEP",

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

        "known_endpoints": {
            "chunk_1":
                "certified loop-style VJP baseline semantics",

            "chunk_64":
                {
                    "status":
                        "B2AA_RUNTIME_FAILURE",

                    "exact_runtime_error":
                        runtime_error,

                    "reclassification":
                        False,
                },
        },

        "authorized_chunk_candidates":
            CHUNK_CANDIDATES,

        "chunked_engine_definition": {
            "output_nodes":
                64,

            "partition":
                "contiguous chunks in original sequence order",

            "per_chunk_grad_outputs_shape":
                "[K,B,T,1]",

            "autograd_call":
                "torch.autograd.grad(..., is_grads_batched=True, "
                "create_graph=True, retain_graph=True)",

            "required_local_derivatives": [
                "N_xi(j)=dN_j/dxi_j",
                "N_tD(j)=dN_j/dp11[tD]",
                "N_X(j)=dN_j/dp11[xD_star]",
            ],

            "assembly":
                "concatenate chunk outputs into exact original 64-node ordering",

            "scientific_change":
                False,
        },

        "candidate_execution": {
            "isolation":
                "fresh subprocess / XPU context per chunk candidate",

            "sequence": [
                "runtime feasibility",
                "derivative equivalence",
                "full corrected-graph equivalence",
                "parameter-gradient equivalence",
                "only then warmed performance",
            ],

            "runtime_failure_policy":
                "record exact error; no fallback; continue other isolated candidates",

            "equivalence_failure_policy":
                "record exact differences; skip performance for that candidate",
        },

        "equivalence_budget": {
            "float32_epsilon":
                FLOAT32_EPS,

            "multiplier":
                IDENTITY_EPS_MULTIPLIER,

            "formula":
                "1024*eps_float32*max(1,max_abs(reference),max_abs(candidate))",

            "semantics":
                "computational implementation-equivalence only; not scientific",
        },

        "required_equivalence_objects": [
            "N_xi",
            "N_tD",
            "N_X",
            "corrected residual",
            "physics loss",
            "complete total loss",
            "all parameter gradients",
        ],

        "performance_if_equivalent": {
            "warmup_iterations":
                1,

            "measured_iterations":
                3,

            "required_outputs": [
                "repeat wall times",
                "median wall time",
                "mean wall time",
                "profiles per second",
                "peak XPU memory if available",
            ],
        },

        "selection_policy":
            "B2AC binds measurements only. B2AD performs interpretation/adoption. "
            "Do not automatically select fastest candidate.",

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
        "# V16E-1B2AB-XPU — B2AC Chunked Batched-VJP Handoff\n\n"
        "## B2AA certified result\n\n"
        "The one-call 64-cotangent batched VJP failed at microbatch 128 with:\n\n"
        f"`{runtime_error}`\n\n"
        "This is preserved as a runtime-resource result. Do not reinterpret it as "
        "proof that every `is_grads_batched=True` configuration is unsupported.\n\n"
        "## B2AC route\n\n"
        "Test cotangent chunk sizes:\n\n"
        "* 2\n"
        "* 4\n"
        "* 8\n"
        "* 16\n"
        "* 32\n\n"
        "Known endpoints:\n\n"
        "* chunk 1 = loop baseline semantics\n"
        "* chunk 64 = B2AA runtime-resource failure\n\n"
        "Every candidate must use a fresh subprocess/XPU context.\n\n"
        "## Equivalence first\n\n"
        "For every runtime-successful candidate compare N_xi, N_tD, N_X, corrected "
        "residual, physics loss, total loss, and every parameter gradient to the "
        "exact loop baseline using only the frozen float32 epsilon-derived budget.\n\n"
        "Only equivalent candidates receive one warm-up plus three measured repeats.\n\n"
        "No optimizer, no weight update, no fallback, no OOD, no TOF.\n\n"
        "B2AC does not adopt a candidate. B2AD interprets the measured set.\n\n"
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

        "chunked_protocol_written":
            PROTOCOL.exists()
            and PROTOCOL.stat().st_size > 0,

        "handoff_written":
            HANDOFF.exists()
            and HANDOFF.stat().st_size > 0,

        "B2AA_runtime_result_preserved":
            True,

        "B2AA_not_overinterpreted":
            True,

        "chunked_route_implementation_only":
            True,

        "B2AC_authorized":
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
        "V16E1B2AB_XPU_B2AA_RUNTIME_RESOURCE_INTERPRETATION_AND_CHUNKED_BATCHED_VJP_PROTOCOL_FROZEN_"
        "FULL_64_COTANGENT_IS_GRADS_BATCHED_TRUE_CALL_PRESERVED_AS_UR_RESULT_ERROR_OUT_OF_RESOURCES_"
        "WITHOUT_UNIVERSAL_UNSUPPORTED_OR_OOM_RECLASSIFICATION_"
        "CHUNKED_BATCHED_VJP_CANDIDATES_2_4_8_16_32_AUTHORIZED_AS_IMPLEMENTATION_ONLY_ROUTE_"
        "EXACT_LOOP_BASELINE_FULL_CORRECTED_GRAPH_AND_FLOAT32_EPSILON_DERIVED_EQUIVALENCE_FIREWALL_PRESERVED_"
        "SUBPROCESS_ISOLATION_NO_FALLBACK_EQUIVALENCE_BEFORE_PERFORMANCE_REQUIRED_"
        "NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
        "COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2AB_XPU_PROTOCOL_FREEZE_COMPLETED_WITH_GATE_FAILURE"
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

        "B2AA_runtime_error":
            runtime_error,

        "authorized_chunk_candidates":
            CHUNK_CANDIDATES,

        "known_loop_chunk":
            KNOWN_LOOP_CHUNK,

        "known_failed_full_chunk":
            KNOWN_FAILED_FULL_CHUNK,

        "B2AC_authorized":
            bool(ok),

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2AC-XPU — subprocess-isolated chunked is_grads_batched=True "
                "VJP sweep for cotangent chunks 2,4,8,16,32 at exact microbatch 128; "
                "equivalence before warmed performance; no optimizer or weight update"
                if ok else
                "V16E-1B2AB-R1 — diagnose B2AA interpretation/protocol gate failure"
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

    print("\nB2AA INTERPRETATION")
    print("  exact runtime result :", runtime_error)
    print("  frozen meaning       : full 64-cotangent request not viable")
    print("  NOT frozen as        : universal is_grads_batched unsupported")
    print("  next route           : chunked batched VJP")
    print("  candidates           :", CHUNK_CANDIDATES)

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
