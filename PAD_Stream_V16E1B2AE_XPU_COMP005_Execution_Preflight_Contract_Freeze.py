#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2AE-XPU
COMP-XPU-005 Exact Execution-Preflight Contract Freeze

Purpose
-------
Freeze the exact operational execution contract for the prospective corrected
Stage-2 reproduction experiment:

    V16E-BLREP-COMP-XPU-005

using the B2AD-adopted derivative implementation:

    CHUNKED_BATCHED_VJP
    cotangent chunk size = 16
    training microbatch  = 128

NO TRAINING.
NO OPTIMIZER OBJECT.
NO OPTIMIZER STEP.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

This milestone freezes the prospective runner behavior and authorizes only a
separate controlled preflight rehearsal (V16E-1B2AF-XPU).

Scientific contract
-------------------
UNCHANGED from the corrected Stage-2 branch:

    architecture:
        [xi, eta] sequence features + raw physical p11
        2 x LSTM(64)
        saturation-range output map

    p11:
        [no,nw,swi/swc,sor,mu_w,mu_o,phi,tD,xD_star,Sw_star,Nc]

    teacher:
        frozen Stage-2 Godunov conservative dataset

    corrected residual:
        frozen conservative moving-fan residual

    physical Nc:
        unchanged

    losses:
        lambda_data   = 1.0
        lambda_phys   = 0.05
        lambda_bc     = 5.0
        lambda_tip    = 5.0
        lambda_anchor = 10.0
        lambda_mono   = 0.2
        lambda_shape  = 0.0

    epochs:
        800

    seed:
        1337

Fresh-training rule
-------------------
COMP-XPU-005 MUST be a fresh reproduction.

It MUST NOT initialize from the frozen COMP-XPU-004 checkpoint.

COMP-XPU-004 is provenance / comparison authority only.

The prospective training model must be freshly initialized using the exact
frozen model construction and seed=1337.

Optimizer contract
------------------
Prospective constructor:

    torch.optim.Adam(
        model.parameters(),
        lr=1.0e-3,
        foreach=False,
    )

No scheduler.
No mixed precision.
No gradient clipping.
No weight decay override.
No optimizer step per microbatch.

Gradient accumulation contract
------------------------------
Frozen geometry:

    train profiles : 11520
    logical batch  : 8192
    microbatch     : 128

Per epoch:

    logical chunk 1:
        8192 profiles
        64 microbatches
        1 optimizer step

    logical chunk 2:
        3328 profiles
        26 microbatches
        1 optimizer step

Therefore:

    microbatches per epoch = 90
    optimizer steps/epoch  = 2
    target optimizer steps = 1600 for 800 completed epochs

For a logical chunk containing N_chunk profiles and a microbatch containing
N_mb profiles:

    scaled_microbatch_loss =
        raw_microbatch_total_loss * (N_mb / N_chunk)

Then:

    scaled_microbatch_loss.backward()

for every microbatch in that logical chunk.

After all microbatches in the logical chunk:

    verify accumulated parameter gradients finite
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)

This preserves profile-weighted logical-batch mean semantics.

The final short logical chunk uses N_chunk=3328, not 8192, in the scaling
denominator.

Checkpoint / resume contract
----------------------------
Atomic epoch-boundary checkpoint after EVERY completed epoch.

Checkpoint payload must include at minimum:

    experiment id
    completed epoch
    model state_dict
    optimizer state_dict
    training history through completed epoch
    Python RNG state
    NumPy RNG state
    torch CPU RNG state
    torch XPU RNG state if available
    exact configuration contract SHA
    exact dataset SHA
    exact source SHAs
    derivative engine name
    cotangent chunk size
    logical batch
    microbatch
    seed
    no-OOD / no-TOF flags

Resume is allowed ONLY from a completed-epoch checkpoint whose bound hashes
and execution contract match exactly.

No mid-logical-batch resume.
No partial-gradient resume.
No silent config repair.
No checkpoint from COMP-XPU-004 or any earlier experiment may be used as the
COMP-XPU-005 starting state.

Evaluation contract
-------------------
Development holdout only; NOT OOD.

Evaluation must use:

    model.eval()
    torch.no_grad()

then return model to model.train() before more training.

No OOD claim.
No TOF use.

Fail-closed runner behavior
---------------------------
The future COMP-XPU-005 runner must refuse to start when:

    dataset SHA mismatch
    source / protocol SHA mismatch
    adopted chunk != 16
    microbatch != 128
    logical batch != 8192
    epochs != 800
    seed != 1337
    scientific loss weights mismatch
    OOD or TOF requested
    final experiment artifacts already exist without explicit valid resume
    resume checkpoint contract/hash mismatch

During training it must stop and write a failure artifact if:

    any loss becomes nonfinite
    any accumulated parameter gradient becomes nonfinite
    any model parameter becomes nonfinite after optimizer step
    XPU runtime failure occurs
    checkpoint atomic write fails

No failed or partial run may be marked COMPLETE.

B2AF rehearsal
--------------
B2AE authorizes only:

    V16E-1B2AF-XPU

A controlled scratch rehearsal that:

    * starts from a fresh seed=1337 initialization;
    * uses chunked batched VJP chunk=16;
    * uses microbatch=128;
    * executes exactly ONE production-sized logical batch
      (8192 profiles = 64 microbatches);
    * creates the exact Adam optimizer above;
    * performs exactly ONE optimizer step;
    * verifies finite accumulated gradients and finite post-step parameters;
    * writes an atomic scratch checkpoint;
    * reloads model + optimizer + RNG state;
    * verifies checkpoint/reload state equality;
    * never promotes rehearsal weights to COMP-XPU-005;
    * never consumes OOD;
    * never uses TOF.

After B2AF, a separate authorization milestone is required before the actual
800-epoch COMP-XPU-005 run.

B3 remains blocked.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import sys


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2AE-XPU"

EXPERIMENT_ID = "V16E-BLREP-COMP-XPU-005"

ADOPTED_ENGINE = "CHUNKED_BATCHED_VJP"
ADOPTED_CHUNK = 16

SEED = 1337
EPOCHS = 800

N_TRAIN = 11520
LOGICAL_BATCH = 8192
MICROBATCH = 128

LOSS_WEIGHTS = {
    "lambda_data": 1.0,
    "lambda_phys": 0.05,
    "lambda_bc": 5.0,
    "lambda_tip": 5.0,
    "lambda_anchor": 10.0,
    "lambda_mono": 0.2,
    "lambda_shape": 0.0,
}

# =============================================================================
# Frozen authorities
# =============================================================================

DATASET = (
    R / "output" / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

# COMP004 is comparison/provenance authority only, NOT a training initializer.
COMP004_DIR = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-004"
)
COMP004_CHECKPOINT = COMP004_DIR / "V16E_BLREP_COMP_XPU_004.pt"
COMP004_CHECKPOINT_SHA = "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69"

# Exact corrected-graph authority.
B2S_SOURCE = (
    R
    / "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
)
B2S_SOURCE_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"

# Exact chunked-engine implementation authority.
B2AC_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AC_XPU_Chunked_Batched_VJP_Equivalence_Performance_Sweep.py"
)
B2AC_SOURCE_SHA = "59f7ea7b0dc2e901f5a42649691c2dab5f4dfc5d399f953eaab5ba773040cd53"

B2AC_DIR = (
    R / "output"
    / "V16_E1B2AC_XPU_CHUNKED_BATCHED_VJP_SWEEP"
)
B2AC_RESULTS = B2AC_DIR / "V16E1B2AC_Chunked_Batched_VJP_Sweep_Results.json"
B2AC_RESULTS_SHA = "b2e6ac1f4483af1429f0e5cf4fe56d51024d0f0009dae008a64c3d1550cf3e34"

# B2AD adoption authority.
B2AD_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AD_XPU_B2AC_Interpretation_Derivative_Engine_Adoption_Protocol_Freeze.py"
)
B2AD_SOURCE_SHA = "75883ac500f90637cb756c0237274aab7982f2090978897763a81d891f44c81f"

B2AD_DIR = (
    R / "output"
    / "V16_E1B2AD_XPU_CHUNKED_VJP_ADOPTION_PROTOCOL"
)
B2AD_INTERPRETATION = B2AD_DIR / "V16E1B2AD_B2AC_Interpretation.json"
B2AD_ADOPTION = B2AD_DIR / "V16E1B2AD_Derivative_Engine_Adoption.json"
B2AD_B2AE_PROTOCOL = B2AD_DIR / "V16E1B2AD_B2AE_Execution_Preflight_Protocol.json"
B2AD_HANDOFF = B2AD_DIR / "V16E1B2AD_B2AE_Handoff.md"
B2AD_SUMMARY = B2AD_DIR / "PAD_Stream_V16E1B2AD_XPU_Summary.json"

B2AD_INTERPRETATION_SHA = "1020d7b5c28204f908021171f934ea054427968779d77ea83e032f62ba9b7974"
B2AD_ADOPTION_SHA = "498e99bfec42d7fe0bc9ab1456668a4d446061a92d1b7dbbaecb4bb89cd3385b"
B2AD_B2AE_PROTOCOL_SHA = "7395ed741b9df83f4c1cc4d1f1a79367286ea747fb2ca0a5389a58116b17cb42"
B2AD_HANDOFF_SHA = "b52a16c6f7777660122c6d9ce2bf428bf009a3d990cc1540a7f225f1db213cb2"
B2AD_SUMMARY_SHA = "47bfbd6ce556186a1cf906cdaef4485cb88956f373b637de5e039baf2802c87d"

EXPECTED_B2AD_STATUS = (
    "V16E1B2AD_XPU_B2AC_CHUNKED_BATCHED_VJP_INTERPRETATION_AND_DERIVATIVE_ENGINE_ADOPTION_PROTOCOL_FROZEN_"
    "ALL_CHUNKS_2_4_8_16_32_RUNTIME_SUCCESSFUL_FULLY_EQUIVALENT_AND_PERFORMANCE_MEASURED_"
    "CHUNK_16_ADOPTED_AS_PROSPECTIVE_COMP_XPU_005_IMPLEMENTATION_ROUTE_BASED_ON_LOWEST_FROZEN_B2AC_MEDIAN_"
    "WITHOUT_STATISTICAL_SUPERIORITY_CLAIM_OR_SCIENTIFIC_GRAPH_CHANGE_"
    "MICROBATCH_128_LOGICAL_BATCH_8192_AND_800_EPOCH_GEOMETRY_PRESERVED_"
    "B2AE_EXECUTION_PREFLIGHT_PROTOCOL_AUTHORIZED_NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
    "COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
)

# =============================================================================
# Outputs
# =============================================================================

OUT = (
    R / "output"
    / "V16_E1B2AE_XPU_COMP005_EXECUTION_PREFLIGHT_CONTRACT"
)
OUT.mkdir(parents=True, exist_ok=True)

EXECUTION_CONTRACT = OUT / "V16E1B2AE_COMP_XPU_005_Execution_Contract.json"
ACCUMULATION_CONTRACT = OUT / "V16E1B2AE_Optimizer_Accumulation_Contract.json"
RESUME_CONTRACT = OUT / "V16E1B2AE_Checkpoint_Resume_Contract.json"
B2AF_PROTOCOL = OUT / "V16E1B2AE_B2AF_Preflight_Rehearsal_Protocol.json"
HANDOFF = OUT / "V16E1B2AE_B2AF_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2AE_XPU_Summary.json"


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


def microbatches_for_chunk(n_chunk: int, microbatch: int) -> int:
    return int(math.ceil(n_chunk / microbatch))


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2AE-XPU")
    print("COMP-XPU-005 Exact Execution-Preflight Contract Freeze")
    print("=" * 80)
    print("PROTOCOL ONLY — NO TRAINING — NO OPTIMIZER OBJECT.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2AE summary already exists; refusing overwrite."
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

        "B2AC_results_SHA_exact":
            exact(B2AC_RESULTS, B2AC_RESULTS_SHA),

        "B2AD_source_SHA_exact":
            exact(B2AD_SOURCE, B2AD_SOURCE_SHA),

        "B2AD_interpretation_SHA_exact":
            exact(B2AD_INTERPRETATION, B2AD_INTERPRETATION_SHA),

        "B2AD_adoption_SHA_exact":
            exact(B2AD_ADOPTION, B2AD_ADOPTION_SHA),

        "B2AD_B2AE_protocol_SHA_exact":
            exact(B2AD_B2AE_PROTOCOL, B2AD_B2AE_PROTOCOL_SHA),

        "B2AD_handoff_SHA_exact":
            exact(B2AD_HANDOFF, B2AD_HANDOFF_SHA),

        "B2AD_summary_SHA_exact":
            exact(B2AD_SUMMARY, B2AD_SUMMARY_SHA),
    }

    b2ad = read_json(B2AD_SUMMARY) if B2AD_SUMMARY.exists() else {}
    adoption = read_json(B2AD_ADOPTION) if B2AD_ADOPTION.exists() else {}
    upstream_protocol = (
        read_json(B2AD_B2AE_PROTOCOL)
        if B2AD_B2AE_PROTOCOL.exists()
        else {}
    )

    gates.update({
        "B2AD_status_exact":
            b2ad.get("status") == EXPECTED_B2AD_STATUS,

        "B2AD_B2AE_true":
            b2ad.get("B2AE_authorized") is True,

        "B2AD_training_false":
            b2ad.get("COMP_XPU_005_full_training_authorized") is False,

        "B2AD_B3_false":
            b2ad.get("B3_authorized") is False,

        "adopted_engine_exact":
            adoption.get("adopted_engine") == ADOPTED_ENGINE,

        "adopted_chunk_16":
            adoption.get("cotangent_chunk_size") == ADOPTED_CHUNK,

        "adoption_reference_microbatch_128":
            adoption.get("reference_microbatch") == MICROBATCH,

        "adoption_training_false":
            adoption.get("training_authorized") is False,

        "upstream_experiment_exact":
            upstream_protocol.get("prospective_experiment") == EXPERIMENT_ID,

        "upstream_engine_exact":
            (
                upstream_protocol
                .get("implementation_contract", {})
                .get("derivative_engine")
                == ADOPTED_ENGINE
            ),

        "upstream_chunk_16":
            (
                upstream_protocol
                .get("implementation_contract", {})
                .get("cotangent_chunk_size")
                == ADOPTED_CHUNK
            ),

        "upstream_microbatch_128":
            (
                upstream_protocol
                .get("implementation_contract", {})
                .get("microbatch")
                == MICROBATCH
            ),

        "upstream_logical_batch_8192":
            (
                upstream_protocol
                .get("implementation_contract", {})
                .get("logical_batch")
                == LOGICAL_BATCH
            ),

        "upstream_epochs_800":
            (
                upstream_protocol
                .get("implementation_contract", {})
                .get("target_epochs")
                == EPOCHS
            ),
    })

    first_chunk = LOGICAL_BATCH
    second_chunk = N_TRAIN - LOGICAL_BATCH

    first_micro = microbatches_for_chunk(
        first_chunk,
        MICROBATCH,
    )
    second_micro = microbatches_for_chunk(
        second_chunk,
        MICROBATCH,
    )

    micro_per_epoch = (
        first_micro
        + second_micro
    )

    optimizer_steps_per_epoch = 2
    target_optimizer_steps = (
        optimizer_steps_per_epoch
        * EPOCHS
    )

    gates.update({
        "train_profiles_11520":
            N_TRAIN == 11520,

        "logical_batch_8192":
            LOGICAL_BATCH == 8192,

        "microbatch_128":
            MICROBATCH == 128,

        "epochs_800":
            EPOCHS == 800,

        "seed_1337":
            SEED == 1337,

        "first_logical_chunk_8192":
            first_chunk == 8192,

        "second_logical_chunk_3328":
            second_chunk == 3328,

        "first_chunk_64_microbatches":
            first_micro == 64,

        "second_chunk_26_microbatches":
            second_micro == 26,

        "microbatches_per_epoch_90":
            micro_per_epoch == 90,

        "optimizer_steps_per_epoch_2":
            optimizer_steps_per_epoch == 2,

        "target_optimizer_steps_1600":
            target_optimizer_steps == 1600,
    })

    print("AUTHORITY / EXECUTION-CONTRACT GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "B2AE blocked by authority or B2AD contract mismatch."
        )

    # -------------------------------------------------------------------------
    # Exact prospective execution contract.
    # -------------------------------------------------------------------------

    execution_contract = {
        "milestone":
            MILESTONE,

        "experiment_id":
            EXPERIMENT_ID,

        "classification":
            "FRESH_CORRECTED_STAGE2_REPRODUCTION_EXECUTION_CONTRACT",

        "fresh_training": {
            "required":
                True,

            "seed":
                SEED,

            "initialize_from_COMP004_checkpoint":
                False,

            "COMP004_role":
                "provenance/comparison authority only",

            "rule":
                "construct a fresh model using the frozen model class and seed=1337",
        },

        "scientific_model": {
            "sequence_features":
                ["xi", "eta"],

            "conditioner":
                [
                    "no",
                    "nw",
                    "swi_swc",
                    "sor",
                    "mu_w",
                    "mu_o",
                    "phi",
                    "tD",
                    "xD_star",
                    "Sw_star",
                    "Nc",
                ],

            "conditioner_dim":
                11,

            "hidden":
                64,

            "layers":
                2,

            "physical_Nc_scaled_for_network":
                False,

            "teacher":
                "frozen Stage-2 conservative Godunov dataset",

            "corrected_physics":
                "frozen conservative moving-fan residual",

            "scientific_graph_source_sha256":
                B2S_SOURCE_SHA,

            "scientific_change":
                False,
        },

        "derivative_engine": {
            "name":
                ADOPTED_ENGINE,

            "cotangent_chunk_size":
                ADOPTED_CHUNK,

            "implementation_source_sha256":
                B2AC_SOURCE_SHA,

            "equivalence_basis_sha256":
                B2AC_RESULTS_SHA,

            "scientific_change":
                False,
        },

        "loss_weights":
            LOSS_WEIGHTS,

        "training_geometry": {
            "train_profiles":
                N_TRAIN,

            "logical_batch":
                LOGICAL_BATCH,

            "microbatch":
                MICROBATCH,

            "microbatches_per_epoch":
                micro_per_epoch,

            "optimizer_steps_per_epoch":
                optimizer_steps_per_epoch,

            "epochs":
                EPOCHS,

            "target_optimizer_steps":
                target_optimizer_steps,
        },

        "optimizer": {
            "constructor_expression":
                "torch.optim.Adam(model.parameters(), lr=1.0e-3, foreach=False)",

            "learning_rate":
                1.0e-3,

            "foreach":
                False,

            "scheduler":
                None,

            "mixed_precision":
                False,

            "gradient_clipping":
                None,
        },

        "evaluation": {
            "dataset_role":
                "frozen source-native development holdout; NOT OOD",

            "model_eval_required":
                True,

            "torch_no_grad_required":
                True,

            "return_to_model_train_after_eval":
                True,

            "OOD_claim":
                False,

            "TOF_used":
                False,
        },

        "full_training_authorized":
            False,
    }

    EXECUTION_CONTRACT.write_text(
        json.dumps(execution_contract, indent=2),
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # Accumulation contract.
    # -------------------------------------------------------------------------

    accumulation_contract = {
        "milestone":
            MILESTONE,

        "classification":
            "LOGICAL_BATCH_GRADIENT_ACCUMULATION_CONTRACT",

        "train_profiles":
            N_TRAIN,

        "logical_batch":
            LOGICAL_BATCH,

        "microbatch":
            MICROBATCH,

        "epoch_chunks": [
            {
                "chunk_index":
                    0,

                "profiles":
                    first_chunk,

                "microbatches":
                    first_micro,

                "optimizer_steps":
                    1,

                "per_microbatch_scale_formula":
                    "N_mb / 8192",
            },
            {
                "chunk_index":
                    1,

                "profiles":
                    second_chunk,

                "microbatches":
                    second_micro,

                "optimizer_steps":
                    1,

                "per_microbatch_scale_formula":
                    "N_mb / 3328",
            },
        ],

        "generic_rule":
            "scaled_loss = raw_microbatch_total_loss * (N_mb / N_current_logical_chunk)",

        "step_rule": [
            "optimizer.zero_grad(set_to_none=True) before first microbatch of logical chunk",
            "backward() scaled loss for every microbatch in logical chunk",
            "verify accumulated parameter gradients finite",
            "optimizer.step() exactly once after logical chunk",
            "verify model parameters finite after step",
            "optimizer.zero_grad(set_to_none=True) after completed step",
        ],

        "microbatches_per_epoch":
            micro_per_epoch,

        "optimizer_steps_per_epoch":
            optimizer_steps_per_epoch,

        "target_optimizer_steps":
            target_optimizer_steps,

        "profile_weighted_logical_mean":
            True,

        "no_optimizer_step_per_microbatch":
            True,
    }

    ACCUMULATION_CONTRACT.write_text(
        json.dumps(accumulation_contract, indent=2),
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # Checkpoint / resume contract.
    # -------------------------------------------------------------------------

    resume_contract = {
        "milestone":
            MILESTONE,

        "classification":
            "ATOMIC_EPOCH_BOUNDARY_CHECKPOINT_RESUME_CONTRACT",

        "checkpoint_frequency":
            "after every completed epoch",

        "atomic_write_required":
            True,

        "mid_epoch_resume_allowed":
            False,

        "mid_logical_batch_resume_allowed":
            False,

        "partial_gradient_resume_allowed":
            False,

        "required_payload_fields": [
            "experiment_id",
            "completed_epoch",
            "model_state_dict",
            "optimizer_state_dict",
            "training_history",
            "python_rng_state",
            "numpy_rng_state",
            "torch_cpu_rng_state",
            "torch_xpu_rng_state_if_available",
            "execution_contract_sha256",
            "accumulation_contract_sha256",
            "dataset_sha256",
            "source_sha256_map",
            "derivative_engine",
            "cotangent_chunk_size",
            "logical_batch",
            "microbatch",
            "seed",
            "OOD_used_false",
            "TOF_used_false",
        ],

        "resume_gates": [
            "experiment_id exact",
            "execution contract SHA exact",
            "accumulation contract SHA exact",
            "dataset SHA exact",
            "all bound source SHAs exact",
            "derivative engine exact",
            "cotangent chunk exact",
            "logical batch exact",
            "microbatch exact",
            "seed exact",
            "completed_epoch is an integer completed epoch boundary",
        ],

        "resume_on_mismatch":
            "REFUSE",

        "COMP004_checkpoint_allowed_as_training_resume":
            False,

        "failed_partial_run_may_be_marked_complete":
            False,
    }

    RESUME_CONTRACT.write_text(
        json.dumps(resume_contract, indent=2),
        encoding="utf-8",
    )

    # We now have concrete SHAs for the two contracts that the rehearsal and
    # future runner must bind.
    execution_sha = sha256(EXECUTION_CONTRACT)
    accumulation_sha = sha256(ACCUMULATION_CONTRACT)
    resume_sha = sha256(RESUME_CONTRACT)

    # -------------------------------------------------------------------------
    # B2AF controlled rehearsal protocol.
    # -------------------------------------------------------------------------

    b2af_protocol = {
        "milestone":
            MILESTONE,

        "authorized_next_milestone":
            "V16E-1B2AF-XPU",

        "classification":
            "ONE_LOGICAL_BATCH_OPTIMIZER_AND_CHECKPOINT_RELOAD_REHEARSAL",

        "scratch_only":
            True,

        "scratch_weights_may_seed_COMP_XPU_005":
            False,

        "fresh_initialization_required":
            True,

        "seed":
            SEED,

        "reference_contracts": {
            "execution_contract_sha256":
                execution_sha,

            "accumulation_contract_sha256":
                accumulation_sha,

            "resume_contract_sha256":
                resume_sha,
        },

        "rehearsal_geometry": {
            "logical_profiles":
                LOGICAL_BATCH,

            "microbatch":
                MICROBATCH,

            "microbatches":
                first_micro,

            "optimizer_steps":
                1,
        },

        "rehearsal_optimizer":
            "torch.optim.Adam(model.parameters(), lr=1.0e-3, foreach=False)",

        "required_sequence": [
            "construct fresh seed=1337 model",
            "construct exact Adam optimizer",
            "select one production-sized 8192-profile logical training chunk",
            "optimizer.zero_grad(set_to_none=True)",
            "run 64 chunk16-corrected microbatches of size 128",
            "scale each raw total loss by 128/8192 before backward",
            "verify accumulated gradients finite and nonzero",
            "optimizer.step() exactly once",
            "verify post-step model parameters finite",
            "write atomic scratch checkpoint",
            "reload model + optimizer + RNG from scratch checkpoint",
            "verify exact reloaded model state equality",
            "verify exact reloaded optimizer state equality",
            "verify checkpoint contract/source hashes",
            "mark scratch rehearsal PASS only if all gates pass",
        ],

        "rehearsal_output_is_training_artifact":
            False,

        "rehearsal_output_is_resume_source_for_COMP005":
            False,

        "full_training_authorized":
            False,

        "scientific_firewall": {
            "OOD":
                False,

            "TOF":
                False,

            "B3_authorized":
                False,

            "scientific_settings_changed":
                False,
        },
    }

    B2AF_PROTOCOL.write_text(
        json.dumps(b2af_protocol, indent=2),
        encoding="utf-8",
    )

    handoff = (
        "# V16E-1B2AE-XPU — B2AF Execution-Preflight Handoff\n\n"
        "## Prospective experiment\n\n"
        f"`{EXPERIMENT_ID}`\n\n"
        "## Frozen implementation\n\n"
        f"* derivative engine: `{ADOPTED_ENGINE}`\n"
        f"* cotangent chunk: {ADOPTED_CHUNK}\n"
        f"* microbatch: {MICROBATCH}\n"
        f"* logical batch: {LOGICAL_BATCH}\n"
        f"* epochs: {EPOCHS}\n"
        f"* seed: {SEED}\n\n"
        "## Fresh training\n\n"
        "COMP-XPU-005 must start from a fresh seed=1337 model initialization. "
        "The frozen COMP-XPU-004 checkpoint is comparison/provenance authority only "
        "and must never be used as the COMP-XPU-005 initializer.\n\n"
        "## Gradient accumulation\n\n"
        "* 8192-profile logical chunk: 64 microbatches, scale each loss by 128/8192\n"
        "* 3328-profile final logical chunk: 26 microbatches, scale each loss by 128/3328\n"
        "* 90 microbatches/epoch\n"
        "* 2 optimizer steps/epoch\n"
        "* 1600 optimizer steps over 800 completed epochs\n\n"
        "## Optimizer\n\n"
        "`torch.optim.Adam(model.parameters(), lr=1.0e-3, foreach=False)`\n\n"
        "No scheduler, mixed precision, or gradient clipping.\n\n"
        "## Resume\n\n"
        "Atomic checkpoint after every completed epoch. Resume only from an exact "
        "hash-matching completed-epoch checkpoint with model, optimizer, history, "
        "and RNG states. No mid-batch or partial-gradient resume.\n\n"
        "## B2AF\n\n"
        "Run one scratch production-sized logical batch (8192 profiles / 64 "
        "microbatches), perform exactly one Adam step, save and reload an atomic "
        "scratch checkpoint, and verify model/optimizer/RNG restoration. The scratch "
        "weights are never allowed to seed COMP-XPU-005.\n\n"
        "Full COMP-XPU-005 training remains blocked until the rehearsal is certified "
        "and a separate authorization milestone passes. B3 remains blocked.\n"
    )

    HANDOFF.write_text(
        handoff,
        encoding="utf-8",
    )

    gates.update({
        "execution_contract_written":
            EXECUTION_CONTRACT.exists()
            and EXECUTION_CONTRACT.stat().st_size > 0,

        "accumulation_contract_written":
            ACCUMULATION_CONTRACT.exists()
            and ACCUMULATION_CONTRACT.stat().st_size > 0,

        "resume_contract_written":
            RESUME_CONTRACT.exists()
            and RESUME_CONTRACT.stat().st_size > 0,

        "B2AF_protocol_written":
            B2AF_PROTOCOL.exists()
            and B2AF_PROTOCOL.stat().st_size > 0,

        "handoff_written":
            HANDOFF.exists()
            and HANDOFF.stat().st_size > 0,

        "fresh_training_required":
            execution_contract["fresh_training"]["required"] is True,

        "COMP004_not_initializer":
            (
                execution_contract["fresh_training"]
                ["initialize_from_COMP004_checkpoint"]
                is False
            ),

        "chunk16_bound":
            (
                execution_contract["derivative_engine"]
                ["cotangent_chunk_size"]
                == ADOPTED_CHUNK
            ),

        "optimizer_constructor_bound":
            (
                execution_contract["optimizer"]
                ["constructor_expression"]
                == "torch.optim.Adam(model.parameters(), lr=1.0e-3, foreach=False)"
            ),

        "profile_weighted_accumulation_bound":
            accumulation_contract["profile_weighted_logical_mean"] is True,

        "atomic_epoch_checkpoint_bound":
            resume_contract["atomic_write_required"] is True,

        "no_mid_epoch_resume":
            resume_contract["mid_epoch_resume_allowed"] is False,

        "B2AF_scratch_only":
            b2af_protocol["scratch_only"] is True,

        "B2AF_scratch_not_COMP005_seed":
            b2af_protocol["scratch_weights_may_seed_COMP_XPU_005"] is False,

        "B2AF_authorized":
            True,

        "COMP005_full_training_not_authorized":
            True,

        "B3_not_authorized":
            True,

        "no_training":
            True,

        "no_optimizer_object_created":
            True,

        "no_optimizer_step":
            True,

        "no_weight_update":
            True,

        "no_OOD":
            True,

        "no_TOF":
            True,
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2AE_XPU_COMP_XPU_005_EXECUTION_PREFLIGHT_CONTRACT_FROZEN_"
        "FRESH_SEED_1337_INITIALIZATION_REQUIRED_COMP_XPU_004_CHECKPOINT_PROVENANCE_ONLY_NOT_INITIALIZER_"
        "CHUNKED_BATCHED_VJP_CHUNK_16_MICROBATCH_128_LOGICAL_BATCH_8192_AND_800_EPOCH_CONTRACT_BOUND_"
        "ADAM_LR_1E_3_FOREACH_FALSE_PROFILE_WEIGHTED_LOGICAL_BATCH_GRADIENT_ACCUMULATION_"
        "NINETY_MICROBATCHES_TWO_OPTIMIZER_STEPS_PER_EPOCH_AND_1600_TARGET_STEPS_BOUND_"
        "ATOMIC_EVERY_COMPLETED_EPOCH_CHECKPOINT_AND_EXACT_HASHED_RESUME_CONTRACT_FROZEN_"
        "B2AF_ONE_LOGICAL_BATCH_SCRATCH_OPTIMIZER_CHECKPOINT_RELOAD_REHEARSAL_AUTHORIZED_"
        "NO_TRAINING_IN_B2AE_NO_OPTIMIZER_OBJECT_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
        "COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2AE_XPU_EXECUTION_CONTRACT_FREEZE_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "execution_contract_sha256":
            execution_sha,

        "accumulation_contract_sha256":
            accumulation_sha,

        "resume_contract_sha256":
            resume_sha,

        "B2AF_protocol_sha256":
            sha256(B2AF_PROTOCOL),

        "handoff_sha256":
            sha256(HANDOFF),

        "experiment_id":
            EXPERIMENT_ID,

        "adopted_derivative_engine":
            ADOPTED_ENGINE,

        "adopted_cotangent_chunk_size":
            ADOPTED_CHUNK,

        "microbatch":
            MICROBATCH,

        "logical_batch":
            LOGICAL_BATCH,

        "epochs":
            EPOCHS,

        "microbatches_per_epoch":
            micro_per_epoch,

        "optimizer_steps_per_epoch":
            optimizer_steps_per_epoch,

        "target_optimizer_steps":
            target_optimizer_steps,

        "B2AF_authorized":
            bool(ok),

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2AF-XPU — scratch one-production-logical-batch rehearsal "
                "using fresh seed1337, chunked batched VJP chunk16, microbatch128, "
                "profile-weighted accumulation, one exact Adam step, atomic "
                "checkpoint write/reload, and model/optimizer/RNG restoration checks; "
                "rehearsal weights must never seed COMP-XPU-005"
                if ok else
                "V16E-1B2AE-R1 — diagnose execution-contract freeze gate failure"
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

    print("\nEXECUTION CONTRACT")
    print("  experiment           :", EXPERIMENT_ID)
    print("  fresh initialization :", "YES — seed 1337")
    print("  COMP004 initializer  :", "NO")
    print("  derivative engine    :", ADOPTED_ENGINE)
    print("  cotangent chunk      :", ADOPTED_CHUNK)
    print("  microbatch           :", MICROBATCH)
    print("  logical batch        :", LOGICAL_BATCH)
    print("  epochs               :", EPOCHS)
    print("  microbatches/epoch   :", micro_per_epoch)
    print("  optimizer steps/epoch:", optimizer_steps_per_epoch)
    print("  target optimizer steps:", target_optimizer_steps)
    print(
        "  optimizer            :",
        "Adam(lr=1e-3, foreach=False)",
    )
    print("  checkpoint           : every completed epoch, atomic")
    print("  resume               : exact hash-matching epoch boundary only")

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Execution Contract :", execution_sha)
    print("  Accumulation       :", accumulation_sha)
    print("  Resume Contract    :", resume_sha)
    print("  B2AF Protocol      :", sha256(B2AF_PROTOCOL))
    print("  Handoff            :", sha256(HANDOFF))
    print("  Summary            :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
