#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2AG-XPU
B2AF Scratch-Rehearsal Interpretation
+ Final COMP-XPU-005 Fresh-Run Authorization Freeze

Purpose
-------
Interpret the certified V16E-1B2AF execution rehearsal and freeze the FINAL
authorization contract for the prospective corrected Stage-2 production run:

    V16E-BLREP-COMP-XPU-005

THIS MILESTONE DOES NOT TRAIN.

If every gate passes, this milestone changes exactly one authorization state:

    COMP_XPU_005_full_training_authorized:
        False -> True

B3 remains NOT authorized.

Certified B2AF evidence
-----------------------
B2AF executed exactly one production-sized logical training batch:

    8192 profiles
    64 microbatches
    128 profiles/microbatch
    chunked batched VJP chunk=16
    profile-weighted accumulation
    exactly one Adam(lr=1e-3, foreach=False) step

Certified results:

    logical batch seconds:
        503.661 s

    accumulated gradient norm:
        5.658700e+00

    logical-batch mean total loss:
        1.326690e+00

    logical-batch mean physics loss:
        1.271869e-03

    model reload exact:
        True

    optimizer reload exact:
        True

    RNG reload exact:
        True

The scratch checkpoint is NON-PRODUCTION:

    scratch_rehearsal = True
    completed_epoch = 0
    completed_logical_batches = 1
    allowed_as_COMP_XPU_005_resume_source = False

It is permanently prohibited as a COMP-XPU-005 initializer or resume source.

Fresh-run production authorization
----------------------------------
COMP-XPU-005 MUST begin from a brand-new seed=1337 initialization.

Forbidden initializers:
    * COMP-XPU-004 checkpoint
    * B2AF scratch checkpoint
    * any COMP-XPU-001/002/003/004 checkpoint
    * any other prior Stage-2 checkpoint

The only allowed production resume source is a checkpoint created by the
authorized COMP-XPU-005 production runner itself after a COMPLETED epoch,
with exact execution-contract / accumulation-contract / resume-contract /
source / dataset hashes.

Frozen production implementation
--------------------------------
Experiment:
    V16E-BLREP-COMP-XPU-005

Derivative engine:
    CHUNKED_BATCHED_VJP

Cotangent chunk:
    16

Microbatch:
    128

Logical batch:
    8192

Epochs:
    800

Seed:
    1337

Optimizer:
    torch.optim.Adam(
        model.parameters(),
        lr=1.0e-3,
        foreach=False,
    )

Gradient accumulation:
    logical chunk 8192:
        64 microbatches
        each loss scaled by 128/8192

    final logical chunk 3328:
        26 microbatches
        each loss scaled by 128/3328

Per epoch:
    90 microbatches
    2 optimizer steps

Target:
    1600 optimizer steps over 800 completed epochs

Checkpoint:
    atomic after every completed epoch

Evaluation:
    development holdout only
    model.eval()
    torch.no_grad()
    return model.train()
    NOT OOD

No TOF.

Scientific settings
-------------------
UNCHANGED.

This authorization does NOT change:
    * [xi,eta] architecture
    * p11 physical conditioner
    * physical Nc
    * Godunov teacher
    * corrected conservative moving-fan residual
    * RH front-speed closure
    * loss definitions
    * loss weights
    * source-native split semantics
    * holdout role

Production runner firewall
--------------------------
The future production runner MUST refuse to start if:

    any bound authority SHA mismatches
    experiment id differs
    seed differs
    adopted derivative engine differs
    chunk differs from 16
    microbatch differs from 128
    logical batch differs from 8192
    epochs differs from 800
    optimizer differs
    loss weights differ
    OOD requested
    TOF requested
    B2AF scratch checkpoint supplied as initializer/resume
    COMP-XPU-004 supplied as initializer/resume
    final COMP-XPU-005 completion artifacts already exist
    resume checkpoint is not a valid completed-epoch COMP-XPU-005 checkpoint

Production failure behavior:
    stop fail-closed
    preserve last valid completed-epoch checkpoint
    write failure artifact
    never label partial run COMPLETE

Production completion requirements:
    all 800 epochs completed
    exactly 1600 optimizer steps completed
    checkpoint/state hashes bound
    development holdout metrics finite
    saturation bounds diagnostic finite
    no OOD
    no TOF

Post-training:
    a separate Stage-2 scientific closure/comparison milestone is required
    before B3.

No scientific numeric acceptance threshold is introduced here.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import sys


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2AG-XPU"
EXPERIMENT_ID = "V16E-BLREP-COMP-XPU-005"

SEED = 1337
ADOPTED_ENGINE = "CHUNKED_BATCHED_VJP"
ADOPTED_CHUNK = 16
MICROBATCH = 128
LOGICAL_BATCH = 8192
N_TRAIN = 11520
EPOCHS = 800

EXPECTED_MICROBATCHES_PER_EPOCH = 90
EXPECTED_OPTIMIZER_STEPS_PER_EPOCH = 2
EXPECTED_TARGET_OPTIMIZER_STEPS = 1600

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

B2S_SOURCE = (
    R
    / "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
)
B2S_SOURCE_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"

B2AC_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AC_XPU_Chunked_Batched_VJP_Equivalence_Performance_Sweep.py"
)
B2AC_SOURCE_SHA = "59f7ea7b0dc2e901f5a42649691c2dab5f4dfc5d399f953eaab5ba773040cd53"

# B2AE execution contract authority.
B2AE_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AE_XPU_COMP005_Execution_Preflight_Contract_Freeze.py"
)
B2AE_SOURCE_SHA = "8bc7eb7f7a927d172bd7438fde719ee3f31c234acc2a167772dc1f6a556d68cc"

B2AE_DIR = (
    R / "output"
    / "V16_E1B2AE_XPU_COMP005_EXECUTION_PREFLIGHT_CONTRACT"
)
EXECUTION_CONTRACT = B2AE_DIR / "V16E1B2AE_COMP_XPU_005_Execution_Contract.json"
ACCUMULATION_CONTRACT = B2AE_DIR / "V16E1B2AE_Optimizer_Accumulation_Contract.json"
RESUME_CONTRACT = B2AE_DIR / "V16E1B2AE_Checkpoint_Resume_Contract.json"
B2AF_PROTOCOL = B2AE_DIR / "V16E1B2AE_B2AF_Preflight_Rehearsal_Protocol.json"
B2AE_SUMMARY = B2AE_DIR / "PAD_Stream_V16E1B2AE_XPU_Summary.json"

EXECUTION_CONTRACT_SHA = "6bf7794f493b95d9922573f24fdee30d1ff9f0caac5a0075d70a9abfa9dae83e"
ACCUMULATION_CONTRACT_SHA = "fd07af361a788f6cbc2c93faad8a196223dfd9a5894e67e2475e96657a8a5425"
RESUME_CONTRACT_SHA = "ba9f86b236e2276e507988d9c44f96b428c59aa1bedc02575f0c2b09c13bc449"
B2AF_PROTOCOL_SHA = "d7a3e505983dcfa855d1291749da0cafa0ee97e3c9319a7e746c392860a69f4f"
B2AE_SUMMARY_SHA = "84b073a12466611bb509e513846a07b5e389991ac4d1a6c5997045769c72f76d"

# B2AF rehearsal authority.
B2AF_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AF_XPU_COMP005_One_Logical_Batch_Scratch_Rehearsal.py"
)
B2AF_SOURCE_SHA = "ef48eeb3e6d20cde86c5ddd6ab1632590480c58aef74d94369a419750040c29d"

B2AF_DIR = (
    R / "output"
    / "V16_E1B2AF_XPU_COMP005_SCRATCH_EXECUTION_REHEARSAL"
)
B2AF_RESULTS = B2AF_DIR / "V16E1B2AF_Scratch_Rehearsal_Results.json"
B2AF_SCRATCH_CHECKPOINT = B2AF_DIR / "V16E1B2AF_SCRATCH_ONE_LOGICAL_BATCH.pt"
B2AF_SUMMARY = B2AF_DIR / "PAD_Stream_V16E1B2AF_XPU_Summary.json"

B2AF_RESULTS_SHA = "232a27e9f7241915fc6b2febec976b382b28ed1aaeb63f28d5c0f3cce3b68390"
B2AF_SCRATCH_CHECKPOINT_SHA = "2fe57da770711257f6087446543e5a2d230d36a2263a7c5648bcc5bf40475152"
B2AF_SUMMARY_SHA = "182fd98351231b58847d391c3cda0554bb257e9753809acb20dc76be99230907"

EXPECTED_B2AF_STATUS = (
    "V16E1B2AF_XPU_COMP_XPU_005_ONE_LOGICAL_BATCH_SCRATCH_EXECUTION_REHEARSAL_COMPLETE_"
    "FRESH_SEED_1337_MODEL_CONFIRMED_NOT_COMP_XPU_004_INITIALIZER_"
    "EXACT_EPOCH1_PRODUCTION_ORDER_FIRST_8192_TRAINING_PROFILES_USED_"
    "CHUNKED_BATCHED_VJP_CHUNK_16_MICROBATCH_128_SIXTY_FOUR_PROFILE_WEIGHTED_BACKWARD_CALLS_COMPLETE_"
    "FINITE_NONZERO_ACCUMULATED_GRADIENTS_AND_EXACTLY_ONE_ADAM_LR_1E_3_FOREACH_FALSE_STEP_COMPLETE_"
    "POST_STEP_PARAMETERS_FINITE_ATOMIC_NONPRODUCTION_SCRATCH_CHECKPOINT_WRITTEN_"
    "MODEL_OPTIMIZER_AND_PYTHON_NUMPY_TORCH_CPU_XPU_RNG_STATE_RELOAD_VERIFIED_EXACT_"
    "COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_SCRATCH_WEIGHTS_PROHIBITED_AS_COMP_XPU_005_RESUME_SOURCE_"
    "B2AG_FINAL_TRAINING_AUTHORIZATION_FREEZE_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_B3_NOT_AUTHORIZED"
)

# =============================================================================
# Outputs
# =============================================================================

OUT = (
    R / "output"
    / "V16_E1B2AG_XPU_FINAL_COMP005_AUTHORIZATION"
)
OUT.mkdir(parents=True, exist_ok=True)

INTERPRETATION = OUT / "V16E1B2AG_B2AF_Rehearsal_Interpretation.json"
AUTHORIZATION = OUT / "V16E1B2AG_COMP_XPU_005_Fresh_Run_Authorization.json"
PRODUCTION_RUNNER_CONTRACT = OUT / "V16E1B2AG_COMP_XPU_005_Production_Runner_Contract.json"
HANDOFF = OUT / "V16E1B2AG_COMP_XPU_005_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2AG_XPU_Summary.json"


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
    print("PAD-Stream V16E-1B2AG-XPU")
    print("B2AF Rehearsal Interpretation")
    print("+ Final COMP-XPU-005 Fresh-Run Authorization Freeze")
    print("=" * 80)
    print("AUTHORIZATION FREEZE ONLY — NO TRAINING IN B2AG.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2AG summary already exists; refusing overwrite."
        )

    gates = {
        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),

        "COMP004_checkpoint_SHA_exact":
            exact(COMP004_CHECKPOINT, COMP004_CHECKPOINT_SHA),

        "B2S_source_SHA_exact":
            exact(B2S_SOURCE, B2S_SOURCE_SHA),

        "B2AC_source_SHA_exact":
            exact(B2AC_SOURCE, B2AC_SOURCE_SHA),

        "B2AE_source_SHA_exact":
            exact(B2AE_SOURCE, B2AE_SOURCE_SHA),

        "execution_contract_SHA_exact":
            exact(EXECUTION_CONTRACT, EXECUTION_CONTRACT_SHA),

        "accumulation_contract_SHA_exact":
            exact(ACCUMULATION_CONTRACT, ACCUMULATION_CONTRACT_SHA),

        "resume_contract_SHA_exact":
            exact(RESUME_CONTRACT, RESUME_CONTRACT_SHA),

        "B2AF_protocol_SHA_exact":
            exact(B2AF_PROTOCOL, B2AF_PROTOCOL_SHA),

        "B2AE_summary_SHA_exact":
            exact(B2AE_SUMMARY, B2AE_SUMMARY_SHA),

        "B2AF_source_SHA_exact":
            exact(B2AF_SOURCE, B2AF_SOURCE_SHA),

        "B2AF_results_SHA_exact":
            exact(B2AF_RESULTS, B2AF_RESULTS_SHA),

        "B2AF_scratch_checkpoint_SHA_exact":
            exact(B2AF_SCRATCH_CHECKPOINT, B2AF_SCRATCH_CHECKPOINT_SHA),

        "B2AF_summary_SHA_exact":
            exact(B2AF_SUMMARY, B2AF_SUMMARY_SHA),
    }

    results = read_json(B2AF_RESULTS) if B2AF_RESULTS.exists() else {}
    summary = read_json(B2AF_SUMMARY) if B2AF_SUMMARY.exists() else {}
    execution = read_json(EXECUTION_CONTRACT) if EXECUTION_CONTRACT.exists() else {}
    accumulation = (
        read_json(ACCUMULATION_CONTRACT)
        if ACCUMULATION_CONTRACT.exists()
        else {}
    )
    resume = read_json(RESUME_CONTRACT) if RESUME_CONTRACT.exists() else {}

    gates.update({
        "B2AF_status_exact":
            summary.get("status") == EXPECTED_B2AF_STATUS,

        "B2AF_scratch_only":
            summary.get("scratch_only") is True,

        "B2AF_scratch_resume_false":
            summary.get("scratch_allowed_as_COMP_XPU_005_resume_source")
            is False,

        "B2AF_logical_batch_8192":
            summary.get("logical_batch_profiles") == LOGICAL_BATCH,

        "B2AF_microbatches_64":
            summary.get("microbatches") == 64,

        "B2AF_optimizer_steps_1":
            summary.get("optimizer_steps") == 1,

        "B2AF_model_reload_exact":
            summary.get("model_reload_exact") is True,

        "B2AF_optimizer_reload_exact":
            summary.get("optimizer_reload_exact") is True,

        "B2AF_RNG_reload_exact":
            summary.get("RNG_reload_exact") is True,

        "B2AF_B2AG_true":
            summary.get("B2AG_authorized") is True,

        "B2AF_training_false":
            summary.get("COMP_XPU_005_full_training_authorized") is False,

        "B2AF_B3_false":
            summary.get("B3_authorized") is False,

        "results_scratch_only":
            results.get("scratch_only") is True,

        "results_resume_source_false":
            results.get("allowed_as_COMP_XPU_005_resume_source") is False,

        "results_COMP004_weights_loaded_false":
            (
                results.get("fresh_initialization", {})
                .get("COMP004_weights_loaded")
                is False
            ),

        "results_fresh_not_COMP004":
            (
                results.get("fresh_initialization", {})
                .get("fresh_initial_equals_COMP004")
                is False
            ),

        "results_engine_exact":
            (
                results.get("implementation", {})
                .get("derivative_engine")
                == ADOPTED_ENGINE
            ),

        "results_chunk_16":
            (
                results.get("implementation", {})
                .get("cotangent_chunk_size")
                == ADOPTED_CHUNK
            ),

        "results_microbatch_128":
            (
                results.get("implementation", {})
                .get("microbatch")
                == MICROBATCH
            ),

        "results_logical_batch_8192":
            (
                results.get("implementation", {})
                .get("logical_batch")
                == LOGICAL_BATCH
            ),

        "results_optimizer_steps_1":
            (
                results.get("optimizer", {})
                .get("optimizer_steps")
                == 1
            ),

        "results_all_gates_pass":
            all(
                bool(v)
                for v in results.get("gates", {}).values()
            ),

        "execution_experiment_exact":
            execution.get("experiment_id") == EXPERIMENT_ID,

        "execution_fresh_true":
            (
                execution.get("fresh_training", {})
                .get("required")
                is True
            ),

        "execution_COMP004_initializer_false":
            (
                execution.get("fresh_training", {})
                .get("initialize_from_COMP004_checkpoint")
                is False
            ),

        "execution_chunk_16":
            (
                execution.get("derivative_engine", {})
                .get("cotangent_chunk_size")
                == ADOPTED_CHUNK
            ),

        "execution_microbatch_128":
            (
                execution.get("training_geometry", {})
                .get("microbatch")
                == MICROBATCH
            ),

        "execution_logical_batch_8192":
            (
                execution.get("training_geometry", {})
                .get("logical_batch")
                == LOGICAL_BATCH
            ),

        "execution_epochs_800":
            (
                execution.get("training_geometry", {})
                .get("epochs")
                == EPOCHS
            ),

        "execution_microbatches_per_epoch_90":
            (
                execution.get("training_geometry", {})
                .get("microbatches_per_epoch")
                == EXPECTED_MICROBATCHES_PER_EPOCH
            ),

        "execution_optimizer_steps_per_epoch_2":
            (
                execution.get("training_geometry", {})
                .get("optimizer_steps_per_epoch")
                == EXPECTED_OPTIMIZER_STEPS_PER_EPOCH
            ),

        "execution_target_steps_1600":
            (
                execution.get("training_geometry", {})
                .get("target_optimizer_steps")
                == EXPECTED_TARGET_OPTIMIZER_STEPS
            ),

        "accumulation_profile_weighted":
            accumulation.get("profile_weighted_logical_mean") is True,

        "resume_COMP004_forbidden":
            resume.get("COMP004_checkpoint_allowed_as_training_resume") is False,

        "resume_mid_epoch_false":
            resume.get("mid_epoch_resume_allowed") is False,

        "resume_mid_logical_false":
            resume.get("mid_logical_batch_resume_allowed") is False,
    })

    logical_seconds = float(summary.get("logical_batch_seconds", float("nan")))
    grad_norm = float(summary.get("accumulated_gradient_l2_norm", float("nan")))
    total_loss = float(summary.get("logical_batch_mean_total_loss", float("nan")))
    physics_loss = float(summary.get("logical_batch_mean_physics_loss", float("nan")))

    gates.update({
        "B2AF_logical_seconds_finite":
            finite(logical_seconds),

        "B2AF_grad_norm_finite":
            finite(grad_norm),

        "B2AF_total_loss_finite":
            finite(total_loss),

        "B2AF_physics_loss_finite":
            finite(physics_loss),

        "B2AF_grad_norm_positive":
            grad_norm > 0.0,
    })

    print("AUTHORITY / FINAL-AUTHORIZATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "B2AG blocked by B2AF rehearsal or upstream contract mismatch."
        )

    rehearsal_throughput = float(
        LOGICAL_BATCH / logical_seconds
    )

    # Production-shaped diagnostic:
    # use the measured rehearsal throughput only as an operational projection.
    remaining_profiles = N_TRAIN - LOGICAL_BATCH
    projected_second_chunk_seconds = float(
        remaining_profiles / rehearsal_throughput
    )
    projected_epoch_seconds = float(
        logical_seconds + projected_second_chunk_seconds
    )
    projected_hours_per_epoch = float(
        projected_epoch_seconds / 3600.0
    )
    projected_days_800 = float(
        projected_epoch_seconds * EPOCHS / 86400.0
    )

    interpretation = {
        "milestone":
            MILESTONE,

        "classification":
            "B2AF_CERTIFIED_PRODUCTION_MECHANICS_INTERPRETATION",

        "B2AF_execution_status":
            "CERTIFIED",

        "certified_rehearsal": {
            "logical_batch_profiles":
                LOGICAL_BATCH,

            "microbatches":
                64,

            "optimizer_steps":
                1,

            "logical_batch_seconds":
                logical_seconds,

            "profiles_per_second":
                rehearsal_throughput,

            "accumulated_gradient_l2_norm":
                grad_norm,

            "logical_batch_mean_total_loss":
                total_loss,

            "logical_batch_mean_physics_loss":
                physics_loss,

            "model_reload_exact":
                True,

            "optimizer_reload_exact":
                True,

            "RNG_reload_exact":
                True,
        },

        "operational_interpretation":
            "The adopted chunk-16 corrected derivative engine, profile-weighted "
            "logical-batch accumulation, one-step Adam update, atomic checkpoint, "
            "and exact state restoration all executed successfully in production-sized "
            "scratch geometry.",

        "diagnostic_projection": {
            "rehearsal_profiles_per_second":
                rehearsal_throughput,

            "projected_second_logical_chunk_seconds":
                projected_second_chunk_seconds,

            "projected_epoch_seconds":
                projected_epoch_seconds,

            "projected_hours_per_epoch":
                projected_hours_per_epoch,

            "projected_days_for_800_epochs":
                projected_days_800,

            "semantics":
                "operational diagnostic only; not a runtime promise",
        },

        "scratch_checkpoint_role":
            "PROVENANCE_EVIDENCE_ONLY",

        "scratch_checkpoint_allowed_as_production_initializer":
            False,

        "scratch_checkpoint_allowed_as_production_resume":
            False,

        "scientific_model_changed":
            False,

        "authorization_decision":
            "AUTHORIZE_FRESH_COMP_XPU_005_PRODUCTION_RUN",

        "B3_authorized":
            False,
    }

    INTERPRETATION.write_text(
        json.dumps(interpretation, indent=2),
        encoding="utf-8",
    )

    authorization = {
        "milestone":
            MILESTONE,

        "classification":
            "FINAL_COMP_XPU_005_FRESH_RUN_AUTHORIZATION",

        "experiment_id":
            EXPERIMENT_ID,

        "authorized":
            True,

        "fresh_initialization_required":
            True,

        "seed":
            SEED,

        "allowed_initializers": [
            "brand-new model construction from frozen architecture with seed=1337"
        ],

        "forbidden_initializers_or_resume_sources": [
            "COMP-XPU-004 checkpoint",
            "B2AF scratch checkpoint",
            "COMP-XPU-001 checkpoint",
            "COMP-XPU-002 checkpoint",
            "COMP-XPU-003 checkpoint",
            "any prior Stage-2 checkpoint not produced by the authorized COMP-XPU-005 runner",
        ],

        "allowed_resume_source_after_run_begins":
            "only an atomic completed-epoch checkpoint created by the authorized "
            "COMP-XPU-005 production runner with exact matching bound hashes",

        "implementation": {
            "derivative_engine":
                ADOPTED_ENGINE,

            "cotangent_chunk_size":
                ADOPTED_CHUNK,

            "microbatch":
                MICROBATCH,

            "logical_batch":
                LOGICAL_BATCH,

            "epochs":
                EPOCHS,

            "seed":
                SEED,
        },

        "optimizer":
            "torch.optim.Adam(model.parameters(), lr=1.0e-3, foreach=False)",

        "microbatches_per_epoch":
            EXPECTED_MICROBATCHES_PER_EPOCH,

        "optimizer_steps_per_epoch":
            EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,

        "target_optimizer_steps":
            EXPECTED_TARGET_OPTIMIZER_STEPS,

        "checkpoint_rule":
            "atomic after every completed epoch",

        "evaluation_role":
            "development holdout only; NOT OOD",

        "OOD_used":
            False,

        "TOF_used":
            False,

        "scientific_settings_changed":
            False,

        "COMP_XPU_005_full_training_authorized":
            True,

        "B3_authorized":
            False,
    }

    AUTHORIZATION.write_text(
        json.dumps(authorization, indent=2),
        encoding="utf-8",
    )

    runner_contract = {
        "milestone":
            MILESTONE,

        "classification":
            "AUTHORIZED_COMP_XPU_005_PRODUCTION_RUNNER_CONTRACT",

        "experiment_id":
            EXPERIMENT_ID,

        "runner_must_bind": {
            "dataset_sha256":
                DATASET_SHA,

            "B2S_source_sha256":
                B2S_SOURCE_SHA,

            "B2AC_source_sha256":
                B2AC_SOURCE_SHA,

            "B2AE_source_sha256":
                B2AE_SOURCE_SHA,

            "B2AF_source_sha256":
                B2AF_SOURCE_SHA,

            "B2AF_results_sha256":
                B2AF_RESULTS_SHA,

            "B2AF_scratch_checkpoint_sha256":
                B2AF_SCRATCH_CHECKPOINT_SHA,

            "B2AF_summary_sha256":
                B2AF_SUMMARY_SHA,

            "execution_contract_sha256":
                EXECUTION_CONTRACT_SHA,

            "accumulation_contract_sha256":
                ACCUMULATION_CONTRACT_SHA,

            "resume_contract_sha256":
                RESUME_CONTRACT_SHA,
        },

        "fresh_start_gates": [
            "no production completion artifact exists",
            "no initializer checkpoint supplied",
            "fresh seed=1337 model constructed",
            "fresh model state is not equal to COMP-XPU-004 trained state",
            "fresh model state is not loaded from B2AF scratch state",
        ],

        "resume_gates": [
            "resume checkpoint experiment_id exact",
            "resume checkpoint completed_epoch >= 1",
            "resume checkpoint created by this authorized production runner",
            "execution contract SHA exact",
            "accumulation contract SHA exact",
            "resume contract SHA exact",
            "dataset SHA exact",
            "source SHA map exact",
            "derivative engine exact",
            "chunk 16 exact",
            "microbatch 128 exact",
            "logical batch 8192 exact",
            "seed 1337 exact",
        ],

        "training_fail_closed_on": [
            "nonfinite loss",
            "nonfinite accumulated gradient",
            "nonfinite model parameter after optimizer step",
            "XPU runtime error",
            "atomic checkpoint write failure",
            "authority SHA mismatch",
            "resume mismatch",
            "OOD requested",
            "TOF requested",
        ],

        "completion_gates": [
            "completed_epoch == 800",
            "optimizer_steps_completed == 1600",
            "final model parameters finite",
            "development holdout metrics finite",
            "checkpoint and artifact hashes written",
            "OOD_used == False",
            "TOF_used == False",
        ],

        "partial_run_may_be_marked_complete":
            False,

        "preserve_last_valid_completed_epoch_checkpoint_on_failure":
            True,

        "post_training_next":
            "Stage-2 scientific closure/comparison milestone before B3",
    }

    PRODUCTION_RUNNER_CONTRACT.write_text(
        json.dumps(runner_contract, indent=2),
        encoding="utf-8",
    )

    handoff = (
        "# V16E-1B2AG-XPU — COMP-XPU-005 Production Handoff\n\n"
        "## Final authorization\n\n"
        "`V16E-BLREP-COMP-XPU-005` is authorized to run after B2AG passes.\n\n"
        "## Fresh start is mandatory\n\n"
        "* Seed: 1337\n"
        "* Do not load COMP-XPU-004 weights\n"
        "* Do not load B2AF scratch weights\n"
        "* Do not load any prior Stage-2 checkpoint\n\n"
        "After the production run begins, resume is permitted only from an atomic "
        "completed-epoch checkpoint created by the authorized COMP-XPU-005 runner "
        "with exact matching hashes.\n\n"
        "## Frozen production mechanics\n\n"
        "* derivative engine: CHUNKED_BATCHED_VJP\n"
        "* cotangent chunk: 16\n"
        "* microbatch: 128\n"
        "* logical batch: 8192\n"
        "* 90 microbatches/epoch\n"
        "* 2 optimizer steps/epoch\n"
        "* 800 epochs\n"
        "* 1600 optimizer steps total\n"
        "* Adam(lr=1e-3, foreach=False)\n"
        "* atomic checkpoint every completed epoch\n\n"
        "## B2AF evidence\n\n"
        f"* 8192-profile rehearsal wall time: {logical_seconds:.6f} s\n"
        f"* observed rehearsal throughput: {rehearsal_throughput:.6f} profiles/s\n"
        f"* accumulated gradient norm: {grad_norm:.6e}\n"
        "* model reload exact: True\n"
        "* optimizer reload exact: True\n"
        "* RNG reload exact: True\n\n"
        "The B2AF scratch checkpoint is permanently prohibited as a production "
        "initializer or resume source.\n\n"
        "## Next\n\n"
        "Materialize the exact provenance-bound COMP-XPU-005 production runner and "
        "execute the fresh 800-epoch run. After completion, perform a separate "
        "Stage-2 scientific comparison/closure milestone before B3.\n"
    )

    HANDOFF.write_text(
        handoff,
        encoding="utf-8",
    )

    gates.update({
        "interpretation_written":
            INTERPRETATION.exists()
            and INTERPRETATION.stat().st_size > 0,

        "authorization_written":
            AUTHORIZATION.exists()
            and AUTHORIZATION.stat().st_size > 0,

        "runner_contract_written":
            PRODUCTION_RUNNER_CONTRACT.exists()
            and PRODUCTION_RUNNER_CONTRACT.stat().st_size > 0,

        "handoff_written":
            HANDOFF.exists()
            and HANDOFF.stat().st_size > 0,

        "fresh_production_start_required":
            authorization["fresh_initialization_required"] is True,

        "B2AF_scratch_forbidden":
            "B2AF scratch checkpoint"
            in authorization["forbidden_initializers_or_resume_sources"],

        "COMP004_forbidden":
            "COMP-XPU-004 checkpoint"
            in authorization["forbidden_initializers_or_resume_sources"],

        "COMP005_training_authorized":
            authorization["COMP_XPU_005_full_training_authorized"] is True,

        "B3_not_authorized":
            authorization["B3_authorized"] is False,

        "no_training_in_B2AG":
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
        "V16E1B2AG_XPU_B2AF_EXECUTION_REHEARSAL_INTERPRETATION_AND_FINAL_COMP_XPU_005_FRESH_RUN_AUTHORIZATION_FROZEN_"
        "PRODUCTION_SIZED_8192_PROFILE_CHUNK16_MICROBATCH128_PROFILE_WEIGHTED_ACCUMULATION_AND_ONE_ADAM_STEP_REHEARSAL_CERTIFIED_"
        "ATOMIC_SCRATCH_CHECKPOINT_MODEL_OPTIMIZER_AND_RNG_RELOAD_VERIFIED_EXACT_"
        "B2AF_SCRATCH_CHECKPOINT_PERMANENTLY_PROHIBITED_AS_PRODUCTION_INITIALIZER_OR_RESUME_SOURCE_"
        "COMP_XPU_004_AND_ALL_PRIOR_STAGE2_CHECKPOINTS_PROHIBITED_AS_FRESH_RUN_INITIALIZERS_"
        "FRESH_SEED_1337_COMP_XPU_005_RUN_CHUNK16_MICROBATCH128_LOGICAL8192_EPOCHS800_ADAM_LR1E_3_FOREACH_FALSE_AUTHORIZED_"
        "NINETY_MICROBATCHES_TWO_OPTIMIZER_STEPS_PER_EPOCH_1600_TARGET_STEPS_AND_ATOMIC_COMPLETED_EPOCH_RESUME_CONTRACT_BOUND_"
        "NO_TRAINING_IN_B2AG_NO_OOD_NO_TOF_COMP_XPU_005_FULL_TRAINING_AUTHORIZED_"
        "B3_NOT_AUTHORIZED_STAGE2_SCIENTIFIC_CLOSURE_REQUIRED_AFTER_TRAINING"
        if ok else
        "V16E1B2AG_XPU_FINAL_AUTHORIZATION_FREEZE_COMPLETED_WITH_GATE_FAILURE"
    )

    summary_payload = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "interpretation_sha256":
            sha256(INTERPRETATION),

        "authorization_sha256":
            sha256(AUTHORIZATION),

        "production_runner_contract_sha256":
            sha256(PRODUCTION_RUNNER_CONTRACT),

        "handoff_sha256":
            sha256(HANDOFF),

        "experiment_id":
            EXPERIMENT_ID,

        "rehearsal_logical_batch_seconds":
            logical_seconds,

        "rehearsal_profiles_per_second":
            rehearsal_throughput,

        "diagnostic_hours_per_epoch":
            projected_hours_per_epoch,

        "diagnostic_days_for_800_epochs":
            projected_days_800,

        "fresh_initialization_required":
            True,

        "B2AF_scratch_allowed_as_COMP_XPU_005_resume_source":
            False,

        "COMP004_allowed_as_COMP_XPU_005_initializer":
            False,

        "COMP_XPU_005_full_training_authorized":
            bool(ok),

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2AH-XPU — materialize the exact provenance-bound "
                "COMP-XPU-005 production runner and execute/resume the fresh "
                "800-epoch corrected Stage-2 run under the B2AG authorization; "
                "after completion, perform Stage-2 scientific closure before B3"
                if ok else
                "V16E-1B2AG-R1 — diagnose final-authorization gate failure"
            ),

        "gates":
            {
                k: bool(v)
                for k, v in gates.items()
            },
    }

    SUMMARY.write_text(
        json.dumps(summary_payload, indent=2),
        encoding="utf-8",
    )

    print("\nB2AF INTERPRETATION")
    print("  logical batch seconds :", f"{logical_seconds:.3f}")
    print("  throughput            :", f"{rehearsal_throughput:.3f} profiles/s")
    print("  accumulated grad norm :", f"{grad_norm:.6e}")
    print("  model reload exact    :", True)
    print("  optimizer reload exact:", True)
    print("  RNG reload exact      :", True)
    print("  B2AF scratch resume   :", "PERMANENTLY FORBIDDEN")

    print("\nFINAL PRODUCTION AUTHORIZATION")
    print("  experiment            :", EXPERIMENT_ID)
    print("  fresh seed            :", SEED)
    print("  derivative engine     :", ADOPTED_ENGINE)
    print("  cotangent chunk       :", ADOPTED_CHUNK)
    print("  microbatch            :", MICROBATCH)
    print("  logical batch         :", LOGICAL_BATCH)
    print("  epochs                :", EPOCHS)
    print("  microbatches/epoch    :", EXPECTED_MICROBATCHES_PER_EPOCH)
    print("  optimizer steps/epoch :", EXPECTED_OPTIMIZER_STEPS_PER_EPOCH)
    print("  target optimizer steps:", EXPECTED_TARGET_OPTIMIZER_STEPS)
    print("  COMP-XPU-005 training :", "AUTHORIZED")
    print("  B3                     :", "NOT AUTHORIZED")
    print(
        "  diagnostic projection :",
        f"{projected_hours_per_epoch:.3f} h/epoch, "
        f"{projected_days_800:.3f} d/800ep",
    )

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Interpretation :", sha256(INTERPRETATION))
    print("  Authorization  :", sha256(AUTHORIZATION))
    print("  Runner Contract:", sha256(PRODUCTION_RUNNER_CONTRACT))
    print("  Handoff        :", sha256(HANDOFF))
    print("  Summary        :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary_payload["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
