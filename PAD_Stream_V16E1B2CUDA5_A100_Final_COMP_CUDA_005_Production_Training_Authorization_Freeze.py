#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2CUDA5-A100
Final COMP-CUDA-005 Production-Training Authorization Freeze

Purpose
-------
Interpret the certified CUDA4R full-8192 selected-geometry rehearsal and freeze
final production authorization for:

    V16E-BLREP-COMP-CUDA-005

THIS MILESTONE DOES NOT TRAIN.

If every gate passes, CUDA5 changes exactly one authorization state:

    COMP005_CUDA_full_training_authorized:
        False -> True

B3 remains NOT authorized.  A separate post-training Stage-2 scientific
closure/comparison milestone is required before B3.

Certified execution authority
-----------------------------
CUDA4R certified the CUDA3-selected implementation on the full first 8192
profiles of the frozen epoch-1 training order:

    device/backend        : NVIDIA A100 / CUDA
    recurrent HO-autograd : native CUDA RNN path; cuDNN disabled only around
                            the recurrent higher-order-autograd graph
    microbatch            : 1024
    batched-VJP chunk     : 64
    logical batch         : 8192
    microbatches          : 8
    optimizer steps       : 1
    optimizer             : Adam(lr=1e-3, foreach=False)
    TF32                   : disabled
    AMP                    : disabled

Certified CUDA4R evidence:

    full-8192 loss equivalence            : PASS
    every parameter-gradient equivalence  : PASS
    gradient-norm equivalence             : PASS
    model reload exact                    : PASS
    optimizer reload exact                : PASS
    RNG reload exact                      : PASS
    CUDA4R scratch usable as resume       : FALSE

Observed CUDA4R performance:

    8192-profile wall time : 87.902 s
    throughput             : 93.195 profiles/s
    peak CUDA memory       : 43.106 GiB

The timing is diagnostic evidence only; CUDA5 does not make a runtime promise.

Fresh production start
----------------------
COMP-CUDA-005 MUST begin from a brand-new seed=1337 model initialization.

Forbidden production initializers / resume sources:
    * COMP-XPU-004 checkpoint
    * CUDA2RR scratch checkpoint
    * CUDA4R scratch checkpoint
    * any CUDA3 benchmark state
    * any COMP-XPU-001/002/003/004 checkpoint
    * any prior Stage-2 checkpoint not created by the authorized
      COMP-CUDA-005 production runner

After production begins, resume is permitted ONLY from an atomic completed-
epoch checkpoint created by the authorized production runner itself, with all
frozen source, dataset, CUDA5 contract, geometry, optimizer, and RNG bindings
matching exactly.

Frozen production geometry
--------------------------
Training profiles per epoch : 11520
Logical batch               : 8192
Microbatch                  : 1024
VJP chunk                   : 64
Epochs                      : 800
Seed                        : 1337

Each epoch has two logical chunks:

    chunk 0: 8192 profiles
        8 x 1024 microbatches
        each backward scaled by 1024/8192 = 1/8
        one optimizer step

    chunk 1: 3328 profiles
        1024 + 1024 + 1024 + 256
        each backward scaled by N_mb/3328
        one optimizer step

Therefore:

    microbatches / epoch    : 12
    optimizer steps / epoch : 2
    target optimizer steps  : 1600

Optimizer:

    torch.optim.Adam(
        model.parameters(),
        lr=1.0e-3,
        foreach=False,
    )

No scheduler.
No mixed precision / AMP.
No gradient clipping.
TF32 disabled.

Scientific model
----------------
UNCHANGED from the frozen corrected Stage-2 science:

    sequence features  : [xi, eta]
    physical conditioner p11:
        [no, nw, swi/swc, sor, mu_w, mu_o, phi, tD, xD_star, Sw_star, Nc]
    conditioner dim    : 11
    recurrent hidden   : 64
    recurrent layers   : 2
    physical Nc        : unscaled in the physical equations
    teacher            : frozen Stage-2 conservative Godunov dataset
    physics residual   : corrected conservative moving-fan residual
    RH closure         : frozen
    loss definitions   : frozen
    loss weights       : frozen
    source-native split: frozen
    OOD                : prohibited during development/training closure
    TOF                : not used in Stage-2 reproduction

Evaluation remains development-holdout only and is NOT OOD.

Production checkpoint rule
--------------------------
Atomic checkpoint after every completed epoch.

No mid-epoch resume.
No mid-logical-batch resume.
No partial-gradient resume.
No failed partial run may be labeled COMPLETE.
Preserve the last valid completed-epoch checkpoint on failure.

Production completion requires:
    completed_epoch == 800
    optimizer_steps_completed == 1600
    model parameters finite
    development-holdout metrics finite
    checkpoint/artifact hashes written
    OOD_used == False
    TOF_used == False

CUDA5 authorizes production training but does not itself materialize or execute
the production runner.  The next milestone is CUDA6: materialize the exact
provenance-bound production runner under this authorization.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import os
import subprocess
import sys
from typing import Any

import torch


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2CUDA5-A100"
EXPERIMENT_ID = "V16E-BLREP-COMP-CUDA-005"
SEED = 1337
N_TRAIN = 11520
LOGICAL_BATCH = 8192
SECOND_LOGICAL_CHUNK = N_TRAIN - LOGICAL_BATCH
MICROBATCH = 1024
VJP_CHUNK = 64
EPOCHS = 800
MICROBATCHES_FIRST_CHUNK = 8
MICROBATCHES_SECOND_CHUNK = 4
MICROBATCHES_PER_EPOCH = 12
OPTIMIZER_STEPS_PER_EPOCH = 2
TARGET_OPTIMIZER_STEPS = 1600
LR = 1.0e-3
ADOPTED_ENGINE = "CHUNKED_BATCHED_VJP_NATIVE_CUDA_RNN"

RUNTIME_ROOT = Path("/content/PAD_Stream_Runtime")
DRIVE_ROOT = Path("/content/drive/MyDrive/PAD_Stream_Compute")

# =============================================================================
# Frozen scientific / data authorities
# =============================================================================

DATASET = RUNTIME_ROOT / "datasets" / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

COMP004_CHECKPOINT = RUNTIME_ROOT / "xpu_reference" / "V16E_BLREP_COMP_XPU_004.pt"
COMP004_CHECKPOINT_SHA = "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69"

B2S_SOURCE = R / "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
B2S_SOURCE_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"

B2AC_SOURCE = R / "PAD_Stream_V16E1B2AC_XPU_Chunked_Batched_VJP_Equivalence_Performance_Sweep.py"
B2AC_SOURCE_SHA = "59f7ea7b0dc2e901f5a42649691c2dab5f4dfc5d399f953eaab5ba773040cd53"

B2AE_SOURCE = R / "PAD_Stream_V16E1B2AE_XPU_COMP005_Execution_Preflight_Contract_Freeze.py"
B2AE_SOURCE_SHA = "8bc7eb7f7a927d172bd7438fde719ee3f31c234acc2a167772dc1f6a556d68cc"

B2AE_DIR = R / "output" / "V16_E1B2AE_XPU_COMP005_EXECUTION_PREFLIGHT_CONTRACT"
EXECUTION_CONTRACT = B2AE_DIR / "V16E1B2AE_COMP_XPU_005_Execution_Contract.json"
ACCUMULATION_CONTRACT = B2AE_DIR / "V16E1B2AE_Optimizer_Accumulation_Contract.json"
RESUME_CONTRACT = B2AE_DIR / "V16E1B2AE_Checkpoint_Resume_Contract.json"
B2AF_PROTOCOL = B2AE_DIR / "V16E1B2AE_B2AF_Preflight_Rehearsal_Protocol.json"
B2AE_HANDOFF = B2AE_DIR / "V16E1B2AE_B2AF_Handoff.md"
B2AE_SUMMARY = B2AE_DIR / "PAD_Stream_V16E1B2AE_XPU_Summary.json"

# Frozen Windows byte authorities.  Git may materialize these text files as LF
# on Linux.  exact_text_authority() accepts the Linux file only if deterministic
# CRLF reconstruction reproduces the ORIGINAL frozen SHA exactly.
EXECUTION_CONTRACT_SHA = "6bf7794f493b95d9922573f24fdee30d1ff9f0caac5a0075d70a9abfa9dae83e"
ACCUMULATION_CONTRACT_SHA = "fd07af361a788f6cbc2c93faad8a196223dfd9a5894e67e2475e96657a8a5425"
RESUME_CONTRACT_SHA = "ba9f86b236e2276e507988d9c44f96b428c59aa1bedc02575f0c2b09c13bc449"
B2AF_PROTOCOL_SHA = "d7a3e505983dcfa855d1291749da0cafa0ee97e3c9319a7e746c392860a69f4f"
B2AE_HANDOFF_SHA = "8a937b13c35dd4781a2efc1f56e670e36b16874a57594445d2d9e83dd22da0d1"
B2AE_SUMMARY_SHA = "84b073a12466611bb509e513846a07b5e389991ac4d1a6c5997045769c72f76d"

# =============================================================================
# CUDA migration / selected-geometry authority
# =============================================================================

CUDA2RR_SOURCE = R / "PAD_Stream_V16E1B2CUDA2RR_A100_Final_Cross_Platform_Text_Authority_Repair_Rehearsal.py"
CUDA2RR_SOURCE_SHA = "19b369a13832ce131fd7468ea7dd2c2689b2139dadcdf21d774b6266ef7c2755"
CUDA2RR_DIR = (
    DRIVE_ROOT / "provenance" / "cuda_rehearsal"
    / "V16E1B2CUDA2RR_A100_FINAL_CROSS_PLATFORM_TEXT_AUTHORITY_REPAIR_REHEARSAL"
)
CUDA2RR_RESULTS = CUDA2RR_DIR / "V16E1B2CUDA2RR_A100_Final_Cross_Platform_Text_Authority_Repair_Results.json"
CUDA2RR_RESULTS_SHA = "7b90304d287d141272c87b1b56dd07ef5b5ecee09773eeb54b348acc0f0e382d"
CUDA2RR_SUMMARY = CUDA2RR_DIR / "PAD_Stream_V16E1B2CUDA2RR_A100_Summary.json"
CUDA2RR_SUMMARY_SHA = "f3e724a222ade1ef684ffab26543769dc50a680ab212643d2c634800c63cf920"

CUDA3_SOURCE = R / "PAD_Stream_V16E1B2CUDA3_A100_Microbatch_Batched_VJP_Performance_Sweep.py"
CUDA3_SOURCE_SHA = "1065788f8f82d7f58aba873b8396cf70a17906571421315151640a0c879df886"
CUDA3_DIR = (
    DRIVE_ROOT / "provenance" / "cuda_performance"
    / "V16E1B2CUDA3_A100_MICROBATCH_BATCHED_VJP_PERFORMANCE_SWEEP"
)
CUDA3_RESULTS = CUDA3_DIR / "V16E1B2CUDA3_A100_Performance_Sweep_Results.json"
CUDA3_RESULTS_SHA = "c1422884db6ad0bab65f8d91deaed991f79dd593abfa01ca0d4920c14648c2ef"
CUDA3_SUMMARY = CUDA3_DIR / "PAD_Stream_V16E1B2CUDA3_A100_Summary.json"
CUDA3_SUMMARY_SHA = "52daea4d6669f30a94db1e0eeef14da5a541fe560f15c5339612e5b0faff003e"

CUDA4R_SOURCE = R / "PAD_Stream_V16E1B2CUDA4R_A100_CUDA3_K64_Engine_Repair_Full_Logical_Batch_Rehearsal.py"
CUDA4R_SOURCE_SHA = "6bbab60648b5e0ead67b1a51f0e804ded6893005464f390bc08210a8d629a3c1"
CUDA4R_DIR = (
    DRIVE_ROOT / "provenance" / "cuda_rehearsal"
    / "V16E1B2CUDA4R_A100_CUDA3_K64_ENGINE_REPAIR_FULL_LOGICAL_BATCH_REHEARSAL"
)
CUDA4R_RESULTS = CUDA4R_DIR / "V16E1B2CUDA4R_A100_CUDA3_K64_Engine_Repair_Full_Logical_Batch_Results.json"
CUDA4R_RESULTS_SHA = "f1548846062617eb7fa9aaba3e8c247411b2640dc778d1f8d44de2c5254439ea"
CUDA4R_GRADS = CUDA4R_DIR / "V16E1B2CUDA4R_MB1024_K64_Full8192_Gradients.pt"
CUDA4R_GRADS_SHA = "d29de777cc8bbb8839d5c63d554042137da6213f9331442b70ff4a018a4c138a"
CUDA4R_SCRATCH = CUDA4R_DIR / "V16E1B2CUDA4R_SCRATCH_ONE_LOGICAL_BATCH.pt"
CUDA4R_SCRATCH_SHA = "235debd529888a22b175a62b4378097514ac5786d2133bd6448d0e3132aedb67"
CUDA4R_SUMMARY = CUDA4R_DIR / "PAD_Stream_V16E1B2CUDA4R_A100_Summary.json"
CUDA4R_SUMMARY_SHA = "80acb080bc16f4814a0d73c3002026d4650741855ce2333546bee1d29f41ec9f"

EXPECTED_CUDA4R_STATUS = (
    "V16E1B2CUDA4R_A100_CUDA3_K64_ENGINE_REPAIR_FULL_LOGICAL_BATCH_REHEARSAL_PASS_"
    "CUDA2RR_FULL_8192_BASELINE_AND_CUDA3_SELECTED_GEOMETRY_AUTHORITY_BOUND_"
    "FAILED_CUDA4_SOURCE_BOUND_B2AC_K64_ALLOWLIST_MISMATCH_REPAIRED_BY_DIRECT_SHA_BOUND_CUDA3_K64_ENGINE_REUSE_"
    "FRESH_SEED_1337_MODEL_CONFIRMED_NOT_COMP_XPU_004_INITIALIZER_"
    "EXACT_EPOCH1_FIRST_8192_TRAINING_PROFILES_MB1024_CHUNK64_EIGHT_PROFILE_WEIGHTED_BACKWARD_CALLS_COMPLETE_"
    "FULL_8192_LOSS_AND_EVERY_PARAMETER_GRADIENT_TENSOR_EQUIVALENT_TO_CERTIFIED_MB128_CHUNK16_BASELINE_"
    "EXACTLY_ONE_ADAM_LR_1E_3_FOREACH_FALSE_STEP_COMPLETE_POST_STEP_PARAMETERS_FINITE_"
    "ATOMIC_NONPRODUCTION_SCRATCH_CHECKPOINT_MODEL_OPTIMIZER_AND_RNG_RELOAD_VERIFIED_EXACT_"
    "NO_OOD_NO_TOF_SCRATCH_WEIGHTS_PROHIBITED_AS_COMP005_RESUME_SOURCE_"
    "CUDA5_FINAL_COMP005_TRAINING_AUTHORIZATION_FREEZE_AUTHORIZED_"
    "COMP005_CUDA_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
)

# =============================================================================
# CUDA5 outputs
# =============================================================================

OUT = (
    DRIVE_ROOT / "provenance" / "cuda_authorization"
    / "V16E1B2CUDA5_A100_FINAL_COMP_CUDA_005_PRODUCTION_TRAINING_AUTHORIZATION_FREEZE"
)
OUT.mkdir(parents=True, exist_ok=True)

INTERPRETATION = OUT / "V16E1B2CUDA5_CUDA4R_Interpretation.json"
AUTHORIZATION = OUT / "V16E1B2CUDA5_COMP_CUDA_005_Production_Authorization.json"
CUDA_ACCUMULATION = OUT / "V16E1B2CUDA5_COMP_CUDA_005_CUDA_Accumulation_Contract.json"
CUDA_RESUME = OUT / "V16E1B2CUDA5_COMP_CUDA_005_CUDA_Resume_Contract.json"
PRODUCTION_RUNNER_CONTRACT = OUT / "V16E1B2CUDA5_COMP_CUDA_005_Production_Runner_Contract.json"
HANDOFF = OUT / "V16E1B2CUDA5_COMP_CUDA_005_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2CUDA5_A100_Summary.json"
FAILURE = OUT / "V16E1B2CUDA5_Authorization_Failure.json"


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


def exact_text_authority(path: Path, expected: str) -> tuple[bool, str]:
    if not path.exists() or not path.is_file():
        return False, "MISSING"
    raw = path.read_bytes()
    raw_sha = hashlib.sha256(raw).hexdigest()
    if raw_sha == expected:
        return True, "RAW_EXACT"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False, "NON_UTF8_RAW_MISMATCH"
    logical = text.replace("\r\n", "\n").replace("\r", "\n")
    crlf = logical.replace("\n", "\r\n").encode("utf-8")
    crlf_sha = hashlib.sha256(crlf).hexdigest()
    if crlf_sha == expected:
        return True, "GIT_LF_WITH_EXACT_FROZEN_CRLF_RECONSTRUCTION"
    return False, "CONTENT_MISMATCH"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json_write(payload: Any, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def atomic_text_write(text: str, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def git_clean() -> bool:
    try:
        p = subprocess.run(
            ["git", "-C", str(R), "status", "--porcelain"],
            text=True,
            capture_output=True,
            check=True,
        )
        return p.stdout.strip() == ""
    except Exception:
        return False


def finite(v: Any) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def write_failure(reason: str, gates: dict[str, bool]) -> None:
    payload = {
        "milestone": MILESTONE,
        "reason": reason,
        "COMP005_CUDA_full_training_authorized": False,
        "B3_authorized": False,
        "gates": {k: bool(v) for k, v in gates.items()},
    }
    atomic_json_write(payload, FAILURE)


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    print("=" * 100)
    print("PAD-Stream V16E-1B2CUDA5-A100")
    print("Final COMP-CUDA-005 Production-Training Authorization Freeze")
    print("=" * 100)
    print("AUTHORIZATION FREEZE ONLY — NO TRAINING IN CUDA5.\n")

    if SUMMARY.exists():
        raise RuntimeError("CUDA5 summary already exists; refusing overwrite.")

    for p in [INTERPRETATION, AUTHORIZATION, CUDA_ACCUMULATION, CUDA_RESUME,
              PRODUCTION_RUNNER_CONTRACT, HANDOFF, FAILURE]:
        if p.exists():
            raise RuntimeError(f"CUDA5 output already exists; refusing overwrite: {p}")

    # Freeze production numerical backend policy now; CUDA5 itself does not train.
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False

    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NONE"

    text_authorities = {
        "execution_contract": exact_text_authority(EXECUTION_CONTRACT, EXECUTION_CONTRACT_SHA),
        "accumulation_contract": exact_text_authority(ACCUMULATION_CONTRACT, ACCUMULATION_CONTRACT_SHA),
        "resume_contract": exact_text_authority(RESUME_CONTRACT, RESUME_CONTRACT_SHA),
        "B2AF_protocol": exact_text_authority(B2AF_PROTOCOL, B2AF_PROTOCOL_SHA),
        "B2AE_handoff": exact_text_authority(B2AE_HANDOFF, B2AE_HANDOFF_SHA),
        "B2AE_summary": exact_text_authority(B2AE_SUMMARY, B2AE_SUMMARY_SHA),
    }

    c4_summary = read_json(CUDA4R_SUMMARY) if CUDA4R_SUMMARY.exists() else {}
    c4_results = read_json(CUDA4R_RESULTS) if CUDA4R_RESULTS.exists() else {}

    # Scratch is evidence only.  Loading it here does not initialize any model.
    c4_scratch = {}
    if CUDA4R_SCRATCH.exists():
        c4_scratch = torch.load(CUDA4R_SCRATCH, map_location="cpu", weights_only=False)

    gates: dict[str, bool] = {
        "git_working_tree_clean": git_clean(),
        "CUDA_available": torch.cuda.is_available(),
        "A100_runtime": "A100" in gpu_name.upper(),
        "TF32_matmul_disabled": (not torch.backends.cuda.matmul.allow_tf32) if torch.cuda.is_available() else False,
        "TF32_cudnn_disabled": (not torch.backends.cudnn.allow_tf32) if torch.cuda.is_available() else False,
        "dataset_SHA_exact": exact(DATASET, DATASET_SHA),
        "COMP004_checkpoint_SHA_exact": exact(COMP004_CHECKPOINT, COMP004_CHECKPOINT_SHA),
        "B2S_source_SHA_exact": exact(B2S_SOURCE, B2S_SOURCE_SHA),
        "B2AC_source_SHA_exact": exact(B2AC_SOURCE, B2AC_SOURCE_SHA),
        "B2AE_source_SHA_exact": exact(B2AE_SOURCE, B2AE_SOURCE_SHA),
        "execution_contract_text_authority_exact": text_authorities["execution_contract"][0],
        "accumulation_contract_text_authority_exact": text_authorities["accumulation_contract"][0],
        "resume_contract_text_authority_exact": text_authorities["resume_contract"][0],
        "B2AF_protocol_text_authority_exact": text_authorities["B2AF_protocol"][0],
        "B2AE_handoff_text_authority_exact": text_authorities["B2AE_handoff"][0],
        "B2AE_summary_text_authority_exact": text_authorities["B2AE_summary"][0],
        "CUDA2RR_source_SHA_exact": exact(CUDA2RR_SOURCE, CUDA2RR_SOURCE_SHA),
        "CUDA2RR_results_SHA_exact": exact(CUDA2RR_RESULTS, CUDA2RR_RESULTS_SHA),
        "CUDA2RR_summary_SHA_exact": exact(CUDA2RR_SUMMARY, CUDA2RR_SUMMARY_SHA),
        "CUDA3_source_SHA_exact": exact(CUDA3_SOURCE, CUDA3_SOURCE_SHA),
        "CUDA3_results_SHA_exact": exact(CUDA3_RESULTS, CUDA3_RESULTS_SHA),
        "CUDA3_summary_SHA_exact": exact(CUDA3_SUMMARY, CUDA3_SUMMARY_SHA),
        "CUDA4R_source_SHA_exact": exact(CUDA4R_SOURCE, CUDA4R_SOURCE_SHA),
        "CUDA4R_results_SHA_exact": exact(CUDA4R_RESULTS, CUDA4R_RESULTS_SHA),
        "CUDA4R_selected_gradients_SHA_exact": exact(CUDA4R_GRADS, CUDA4R_GRADS_SHA),
        "CUDA4R_scratch_SHA_exact": exact(CUDA4R_SCRATCH, CUDA4R_SCRATCH_SHA),
        "CUDA4R_summary_SHA_exact": exact(CUDA4R_SUMMARY, CUDA4R_SUMMARY_SHA),
        "CUDA4R_status_exact": c4_summary.get("status") == EXPECTED_CUDA4R_STATUS,
        "CUDA4R_selected_microbatch_1024": c4_summary.get("selected_microbatch") == MICROBATCH,
        "CUDA4R_selected_chunk_64": c4_summary.get("selected_chunk") == VJP_CHUNK,
        "CUDA4R_logical_batch_8192": c4_summary.get("logical_batch_profiles") == LOGICAL_BATCH,
        "CUDA4R_microbatches_8": c4_summary.get("microbatches") == MICROBATCHES_FIRST_CHUNK,
        "CUDA4R_full_8192_equivalence": c4_summary.get("full_8192_equivalence_pass") is True,
        "CUDA4R_model_reload_exact": c4_summary.get("model_reload_exact") is True,
        "CUDA4R_optimizer_reload_exact": c4_summary.get("optimizer_reload_exact") is True,
        "CUDA4R_RNG_reload_exact": c4_summary.get("RNG_reload_exact") is True,
        "CUDA4R_scratch_resume_false": c4_summary.get("scratch_allowed_as_COMP005_resume_source") is False,
        "CUDA4R_CUDA5_authorized": c4_summary.get("CUDA5_final_COMP005_training_authorization_freeze_authorized") is True,
        "CUDA4R_training_false": c4_summary.get("COMP005_CUDA_full_training_authorized") is False,
        "CUDA4R_B3_false": c4_summary.get("B3_authorized") is False,
        "CUDA4R_results_full_equivalence": c4_results.get("full_8192_equivalence_pass") is True,
        "CUDA4R_results_MB1024": c4_results.get("selected_geometry", {}).get("microbatch") == MICROBATCH,
        "CUDA4R_results_K64": c4_results.get("selected_geometry", {}).get("chunk") == VJP_CHUNK,
        "CUDA4R_results_logical8192": c4_results.get("selected_geometry", {}).get("logical_batch") == LOGICAL_BATCH,
        "CUDA4R_results_training_false": c4_results.get("COMP005_CUDA_full_training_authorized") is False,
        "CUDA4R_results_B3_false": c4_results.get("B3_authorized") is False,
        "CUDA4R_scratch_true": c4_scratch.get("scratch_rehearsal") is True,
        "CUDA4R_scratch_resume_prohibited": c4_scratch.get("allowed_as_COMP005_resume_source") is False,
        "CUDA4R_scratch_completed_epoch_zero": c4_scratch.get("completed_epoch") == 0,
        "CUDA4R_scratch_MB1024": c4_scratch.get("selected_microbatch") == MICROBATCH,
        "CUDA4R_scratch_K64": c4_scratch.get("selected_chunk") == VJP_CHUNK,
        "CUDA4R_scratch_logical8192": c4_scratch.get("logical_batch") == LOGICAL_BATCH,
        "derived_second_chunk_3328": SECOND_LOGICAL_CHUNK == 3328,
        "derived_microbatches_first_chunk_8": MICROBATCHES_FIRST_CHUNK == 8,
        "derived_microbatches_second_chunk_4": MICROBATCHES_SECOND_CHUNK == 4,
        "derived_microbatches_per_epoch_12": MICROBATCHES_PER_EPOCH == 12,
        "derived_optimizer_steps_per_epoch_2": OPTIMIZER_STEPS_PER_EPOCH == 2,
        "derived_target_optimizer_steps_1600": TARGET_OPTIMIZER_STEPS == 1600,
    }

    print("AUTHORITY / FINAL-AUTHORIZATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nCROSS-PLATFORM FROZEN TEXT AUTHORITY")
    for k, (ok, mode) in text_authorities.items():
        print(f"  {k:24s}: {'PASS' if ok else 'FAIL'} | {mode}")

    if not all(gates.values()):
        write_failure("CUDA5 blocked by upstream authority or CUDA4R certification mismatch.", gates)
        raise RuntimeError("CUDA5 blocked by authority or CUDA4R certification mismatch.")

    logical_seconds = float(c4_summary.get("logical_batch_seconds", float("nan")))
    throughput = float(c4_summary.get("throughput_profiles_per_s", float("nan")))
    peak_gib = float(c4_summary.get("peak_cuda_memory_gib", float("nan")))
    grad_norm = float(c4_summary.get("candidate_gradient_l2_norm", float("nan")))
    total_loss = float(c4_summary.get("logical_batch_mean_total_loss", float("nan")))
    physics_loss = float(c4_summary.get("logical_batch_mean_physics_loss", float("nan")))

    perf_gates = {
        "CUDA4R_logical_seconds_finite": finite(logical_seconds) and logical_seconds > 0.0,
        "CUDA4R_throughput_finite": finite(throughput) and throughput > 0.0,
        "CUDA4R_peak_memory_finite": finite(peak_gib) and peak_gib > 0.0,
        "CUDA4R_gradient_norm_finite_positive": finite(grad_norm) and grad_norm > 0.0,
        "CUDA4R_total_loss_finite": finite(total_loss),
        "CUDA4R_physics_loss_finite": finite(physics_loss),
    }
    gates.update(perf_gates)
    if not all(perf_gates.values()):
        write_failure("CUDA5 blocked by nonfinite CUDA4R evidence.", gates)
        raise RuntimeError("CUDA5 blocked by nonfinite CUDA4R evidence.")

    # Diagnostic projection only.  No runtime promise.
    projected_second_chunk_seconds = float(SECOND_LOGICAL_CHUNK / throughput)
    projected_epoch_seconds = float(logical_seconds + projected_second_chunk_seconds)
    projected_hours_per_epoch = float(projected_epoch_seconds / 3600.0)
    projected_hours_800 = float(projected_epoch_seconds * EPOCHS / 3600.0)
    projected_days_800 = float(projected_hours_800 / 24.0)

    self_sha = sha256(Path(__file__).resolve())

    first_chunk_schedule = [1024] * 8
    second_chunk_schedule = [1024, 1024, 1024, 256]
    first_scales = [1024 / 8192] * 8
    second_scales = [1024 / 3328, 1024 / 3328, 1024 / 3328, 256 / 3328]

    interpretation = {
        "milestone": MILESTONE,
        "classification": "CUDA4R_CERTIFIED_SELECTED_GEOMETRY_INTERPRETATION",
        "experiment_id": EXPERIMENT_ID,
        "CUDA4R_execution_status": "CERTIFIED",
        "certified_geometry": {
            "device": "NVIDIA A100 CUDA",
            "microbatch": MICROBATCH,
            "cotangent_chunk_size": VJP_CHUNK,
            "logical_batch": LOGICAL_BATCH,
            "first_logical_chunk_microbatches": MICROBATCHES_FIRST_CHUNK,
            "full_8192_equivalence_pass": True,
        },
        "certified_rehearsal": {
            "logical_batch_seconds": logical_seconds,
            "throughput_profiles_per_s": throughput,
            "peak_cuda_memory_gib": peak_gib,
            "candidate_gradient_l2_norm": grad_norm,
            "logical_batch_mean_total_loss": total_loss,
            "logical_batch_mean_physics_loss": physics_loss,
            "model_reload_exact": True,
            "optimizer_reload_exact": True,
            "RNG_reload_exact": True,
        },
        "diagnostic_projection_only": {
            "projected_second_3328_chunk_seconds": projected_second_chunk_seconds,
            "projected_epoch_seconds": projected_epoch_seconds,
            "projected_hours_per_epoch": projected_hours_per_epoch,
            "projected_hours_for_800_epochs": projected_hours_800,
            "projected_days_for_800_epochs": projected_days_800,
            "runtime_promise": False,
        },
        "scratch_checkpoint_role": "PROVENANCE_EVIDENCE_ONLY",
        "CUDA4R_scratch_allowed_as_initializer": False,
        "CUDA4R_scratch_allowed_as_resume": False,
        "scientific_model_changed": False,
        "authorization_decision": "AUTHORIZE_FRESH_COMP_CUDA_005_PRODUCTION_TRAINING",
        "B3_authorized": False,
    }
    atomic_json_write(interpretation, INTERPRETATION)

    accumulation = {
        "milestone": MILESTONE,
        "classification": "COMP_CUDA_005_PROFILE_WEIGHTED_LOGICAL_BATCH_ACCUMULATION_CONTRACT",
        "train_profiles": N_TRAIN,
        "logical_batch": LOGICAL_BATCH,
        "microbatch_nominal": MICROBATCH,
        "epoch_chunks": [
            {
                "chunk_index": 0,
                "profiles": 8192,
                "microbatch_sizes": first_chunk_schedule,
                "microbatch_scales": first_scales,
                "microbatches": 8,
                "optimizer_steps": 1,
                "scale_formula": "N_mb / 8192",
            },
            {
                "chunk_index": 1,
                "profiles": 3328,
                "microbatch_sizes": second_chunk_schedule,
                "microbatch_scales": second_scales,
                "microbatches": 4,
                "optimizer_steps": 1,
                "scale_formula": "N_mb / 3328",
            },
        ],
        "generic_rule": "scaled_loss = raw_microbatch_total_loss * (N_mb / N_current_logical_chunk)",
        "microbatches_per_epoch": MICROBATCHES_PER_EPOCH,
        "optimizer_steps_per_epoch": OPTIMIZER_STEPS_PER_EPOCH,
        "target_optimizer_steps": TARGET_OPTIMIZER_STEPS,
        "profile_weighted_logical_mean": True,
        "optimizer_step_per_microbatch": False,
        "accumulated_gradients_must_be_finite_before_step": True,
        "model_parameters_must_be_finite_after_step": True,
    }
    atomic_json_write(accumulation, CUDA_ACCUMULATION)

    resume_contract = {
        "milestone": MILESTONE,
        "classification": "COMP_CUDA_005_ATOMIC_COMPLETED_EPOCH_RESUME_CONTRACT",
        "checkpoint_frequency": "after every completed epoch",
        "atomic_write_required": True,
        "mid_epoch_resume_allowed": False,
        "mid_logical_batch_resume_allowed": False,
        "partial_gradient_resume_allowed": False,
        "scratch_checkpoint_resume_allowed": False,
        "required_payload_fields": [
            "experiment_id",
            "completed_epoch",
            "optimizer_steps_completed",
            "model_state_dict",
            "optimizer_state_dict",
            "training_history",
            "python_rng_state",
            "numpy_rng_state",
            "torch_cpu_rng_state",
            "torch_cuda_rng_state",
            "CUDA5_summary_sha256",
            "CUDA5_authorization_sha256",
            "CUDA5_accumulation_contract_sha256",
            "CUDA5_resume_contract_sha256",
            "dataset_sha256",
            "source_sha256_map",
            "derivative_engine",
            "cotangent_chunk_size",
            "logical_batch",
            "microbatch",
            "seed",
            "OOD_used",
            "TOF_used",
        ],
        "resume_gates": [
            "experiment_id exact",
            "completed_epoch >= 1 and is a completed epoch boundary",
            "checkpoint created by the authorized COMP-CUDA-005 production runner",
            "CUDA5 summary SHA exact",
            "CUDA5 authorization SHA exact",
            "CUDA5 accumulation contract SHA exact",
            "CUDA5 resume contract SHA exact",
            "dataset SHA exact",
            "all bound source SHAs exact",
            "derivative engine exact",
            "cotangent chunk == 64",
            "logical batch == 8192",
            "nominal microbatch == 1024",
            "seed == 1337",
            "OOD_used == False",
            "TOF_used == False",
        ],
        "resume_on_mismatch": "REFUSE",
        "COMP004_checkpoint_allowed_as_training_resume": False,
        "CUDA2RR_scratch_allowed_as_training_resume": False,
        "CUDA4R_scratch_allowed_as_training_resume": False,
        "failed_partial_run_may_be_marked_complete": False,
        "preserve_last_valid_completed_epoch_checkpoint_on_failure": True,
    }
    atomic_json_write(resume_contract, CUDA_RESUME)

    authorization = {
        "milestone": MILESTONE,
        "classification": "FINAL_COMP_CUDA_005_FRESH_PRODUCTION_TRAINING_AUTHORIZATION",
        "experiment_id": EXPERIMENT_ID,
        "authorized": True,
        "fresh_initialization_required": True,
        "seed": SEED,
        "allowed_initializers": [
            "brand-new model construction from frozen Stage-2 architecture with seed=1337"
        ],
        "forbidden_initializers_or_resume_sources": [
            "COMP-XPU-004 checkpoint",
            "CUDA2RR scratch checkpoint",
            "CUDA4R scratch checkpoint",
            "CUDA3 benchmark state",
            "COMP-XPU-001 checkpoint",
            "COMP-XPU-002 checkpoint",
            "COMP-XPU-003 checkpoint",
            "any prior Stage-2 checkpoint not produced by the authorized COMP-CUDA-005 production runner",
        ],
        "allowed_resume_source_after_run_begins": (
            "only an atomic completed-epoch checkpoint created by the authorized COMP-CUDA-005 "
            "production runner with exact CUDA5/source/dataset/geometry/optimizer bindings"
        ),
        "scientific_model": {
            "sequence_features": ["xi", "eta"],
            "conditioner": ["no", "nw", "swi_swc", "sor", "mu_w", "mu_o", "phi", "tD", "xD_star", "Sw_star", "Nc"],
            "conditioner_dim": 11,
            "hidden": 64,
            "layers": 2,
            "physical_Nc_scaled_for_network": False,
            "teacher": "frozen Stage-2 conservative Godunov dataset",
            "corrected_physics": "frozen conservative moving-fan residual",
            "scientific_change": False,
        },
        "implementation": {
            "backend": "CUDA",
            "required_gpu_class": "NVIDIA A100",
            "derivative_engine": ADOPTED_ENGINE,
            "native_cuda_rnn_higher_order_autograd": True,
            "cudnn_disabled_only_around_recurrent_higher_order_autograd_graph": True,
            "cotangent_chunk_size": VJP_CHUNK,
            "microbatch": MICROBATCH,
            "logical_batch": LOGICAL_BATCH,
            "epochs": EPOCHS,
            "seed": SEED,
            "TF32": False,
            "AMP": False,
        },
        "optimizer": {
            "constructor_expression": "torch.optim.Adam(model.parameters(), lr=1.0e-3, foreach=False)",
            "learning_rate": LR,
            "foreach": False,
            "scheduler": None,
            "mixed_precision": False,
            "gradient_clipping": None,
        },
        "microbatches_per_epoch": MICROBATCHES_PER_EPOCH,
        "optimizer_steps_per_epoch": OPTIMIZER_STEPS_PER_EPOCH,
        "target_optimizer_steps": TARGET_OPTIMIZER_STEPS,
        "checkpoint_rule": "atomic after every completed epoch",
        "evaluation_role": "frozen source-native development holdout only; NOT OOD",
        "OOD_used": False,
        "TOF_used": False,
        "scientific_settings_changed": False,
        "COMP005_CUDA_full_training_authorized": True,
        "B3_authorized": False,
    }
    atomic_json_write(authorization, AUTHORIZATION)

    # Now that the CUDA5 contracts exist, the future production runner can bind
    # their concrete SHAs without circularity.
    runner_contract = {
        "milestone": MILESTONE,
        "classification": "AUTHORIZED_COMP_CUDA_005_PRODUCTION_RUNNER_CONTRACT",
        "experiment_id": EXPERIMENT_ID,
        "runner_must_bind": {
            "dataset_sha256": DATASET_SHA,
            "COMP004_checkpoint_provenance_sha256": COMP004_CHECKPOINT_SHA,
            "B2S_source_sha256": B2S_SOURCE_SHA,
            "B2AC_source_sha256": B2AC_SOURCE_SHA,
            "B2AE_source_sha256": B2AE_SOURCE_SHA,
            "CUDA2RR_source_sha256": CUDA2RR_SOURCE_SHA,
            "CUDA2RR_results_sha256": CUDA2RR_RESULTS_SHA,
            "CUDA2RR_summary_sha256": CUDA2RR_SUMMARY_SHA,
            "CUDA3_source_sha256": CUDA3_SOURCE_SHA,
            "CUDA3_results_sha256": CUDA3_RESULTS_SHA,
            "CUDA3_summary_sha256": CUDA3_SUMMARY_SHA,
            "CUDA4R_source_sha256": CUDA4R_SOURCE_SHA,
            "CUDA4R_results_sha256": CUDA4R_RESULTS_SHA,
            "CUDA4R_selected_gradients_sha256": CUDA4R_GRADS_SHA,
            "CUDA4R_scratch_checkpoint_sha256_provenance_only": CUDA4R_SCRATCH_SHA,
            "CUDA4R_summary_sha256": CUDA4R_SUMMARY_SHA,
            "CUDA5_interpretation_sha256": sha256(INTERPRETATION),
            "CUDA5_authorization_sha256": sha256(AUTHORIZATION),
            "CUDA5_accumulation_contract_sha256": sha256(CUDA_ACCUMULATION),
            "CUDA5_resume_contract_sha256": sha256(CUDA_RESUME),
            "CUDA5_runner_freeze_source_sha256": self_sha,
        },
        "fresh_start_gates": [
            "no production completion artifact exists",
            "no initializer checkpoint supplied",
            "fresh seed=1337 model constructed",
            "fresh model state is not equal to COMP-XPU-004 trained state",
            "fresh model state is not loaded from CUDA2RR or CUDA4R scratch state",
        ],
        "execution_gates": [
            "A100 CUDA runtime",
            "TF32 disabled",
            "AMP disabled",
            "native CUDA RNN higher-order-autograd path",
            "cuDNN disabled only around recurrent higher-order-autograd graph",
            "VJP chunk 64 exact",
            "nominal microbatch 1024 exact",
            "logical batch 8192 exact",
            "profile-weighted accumulation exact",
            "12 microbatches per complete epoch",
            "2 optimizer steps per complete epoch",
            "Adam lr=1e-3 foreach=False",
            "no scheduler",
            "no gradient clipping",
        ],
        "resume_gates": resume_contract["resume_gates"],
        "training_fail_closed_on": [
            "nonfinite loss",
            "nonfinite accumulated gradient",
            "nonfinite model parameter after optimizer step",
            "CUDA runtime error",
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
        "partial_run_may_be_marked_complete": False,
        "preserve_last_valid_completed_epoch_checkpoint_on_failure": True,
        "CUDA4R_scratch_may_initialize_or_resume": False,
        "post_training_next": "Stage-2 scientific closure/comparison milestone before B3",
    }
    atomic_json_write(runner_contract, PRODUCTION_RUNNER_CONTRACT)

    handoff = f"""# V16E-1B2CUDA5-A100 — COMP-CUDA-005 Production Handoff

## Final authorization

`{EXPERIMENT_ID}` is authorized for fresh production training after CUDA5 passes.
CUDA5 itself performs no training.

## Fresh start is mandatory

- Seed: {SEED}
- Do not load COMP-XPU-004 weights.
- Do not load CUDA2RR scratch weights.
- Do not load CUDA4R scratch weights.
- Do not load any prior Stage-2 checkpoint.

After production begins, resume is permitted only from an atomic completed-epoch
checkpoint produced by the authorized COMP-CUDA-005 runner with exact matching
CUDA5, source, dataset, geometry, optimizer, and RNG bindings.

## Frozen CUDA production mechanics

- GPU class: NVIDIA A100
- derivative engine: {ADOPTED_ENGINE}
- VJP chunk: {VJP_CHUNK}
- nominal microbatch: {MICROBATCH}
- logical batch: {LOGICAL_BATCH}
- train profiles/epoch: {N_TRAIN}
- microbatches/epoch: {MICROBATCHES_PER_EPOCH}
- optimizer steps/epoch: {OPTIMIZER_STEPS_PER_EPOCH}
- epochs: {EPOCHS}
- optimizer steps total: {TARGET_OPTIMIZER_STEPS}
- Adam(lr=1e-3, foreach=False)
- TF32 disabled
- AMP disabled
- no scheduler
- no gradient clipping
- atomic checkpoint after every completed epoch

### Epoch accumulation

Chunk 0: 8192 = 8 x 1024; each backward scale = 1/8.

Chunk 1: 3328 = 1024 + 1024 + 1024 + 256; each backward scale = N_mb/3328.

Exactly one optimizer step follows each logical chunk.

## CUDA4R evidence

- full-8192 loss equivalence: PASS
- every parameter-gradient tensor equivalence: PASS
- gradient-norm equivalence: PASS
- 8192-profile wall time: {logical_seconds:.3f} s
- observed throughput: {throughput:.3f} profiles/s
- peak CUDA memory: {peak_gib:.3f} GiB
- accumulated gradient norm: {grad_norm:.9e}
- model reload exact: True
- optimizer reload exact: True
- RNG reload exact: True

The CUDA4R scratch checkpoint is permanently prohibited as a production
initializer or resume source.

## Runtime diagnostic only

At the CUDA4R observed throughput, a simple profile-count projection gives about
{projected_epoch_seconds:.3f} s/epoch and {projected_hours_800:.3f} h for 800
epochs before evaluation/checkpoint/Colab overhead. This is a diagnostic
projection, not a runtime promise.

## Next

Materialize the exact provenance-bound COMP-CUDA-005 production runner (CUDA6),
then execute/resume the fresh 800-epoch run under this CUDA5 authorization.
After completion, perform a separate Stage-2 scientific closure/comparison
milestone before B3.
"""
    atomic_text_write(handoff, HANDOFF)

    gates.update({
        "interpretation_written": INTERPRETATION.exists() and INTERPRETATION.stat().st_size > 0,
        "authorization_written": AUTHORIZATION.exists() and AUTHORIZATION.stat().st_size > 0,
        "CUDA_accumulation_contract_written": CUDA_ACCUMULATION.exists() and CUDA_ACCUMULATION.stat().st_size > 0,
        "CUDA_resume_contract_written": CUDA_RESUME.exists() and CUDA_RESUME.stat().st_size > 0,
        "production_runner_contract_written": PRODUCTION_RUNNER_CONTRACT.exists() and PRODUCTION_RUNNER_CONTRACT.stat().st_size > 0,
        "handoff_written": HANDOFF.exists() and HANDOFF.stat().st_size > 0,
        "fresh_production_start_required": authorization["fresh_initialization_required"] is True,
        "CUDA4R_scratch_forbidden": "CUDA4R scratch checkpoint" in authorization["forbidden_initializers_or_resume_sources"],
        "COMP004_forbidden": "COMP-XPU-004 checkpoint" in authorization["forbidden_initializers_or_resume_sources"],
        "COMP005_CUDA_training_authorized": authorization["COMP005_CUDA_full_training_authorized"] is True,
        "B3_not_authorized": authorization["B3_authorized"] is False,
        "no_training_in_CUDA5": True,
        "no_OOD": True,
        "no_TOF": True,
        "no_scientific_numeric_acceptance_threshold_added": True,
    })

    ok = all(bool(v) for v in gates.values())
    if not ok:
        write_failure("CUDA5 final output gate failure.", gates)
        raise RuntimeError("CUDA5 final output gate failure.")

    status = (
        "V16E1B2CUDA5_A100_FINAL_COMP_CUDA_005_PRODUCTION_TRAINING_AUTHORIZATION_FROZEN_"
        "CUDA4R_FULL_8192_MB1024_K64_SELECTED_GEOMETRY_REHEARSAL_CERTIFIED_"
        "FULL_LOSS_EVERY_PARAMETER_GRADIENT_AND_GRADIENT_NORM_EQUIVALENCE_CONFIRMED_"
        "ATOMIC_SCRATCH_CHECKPOINT_MODEL_OPTIMIZER_AND_RNG_RELOAD_VERIFIED_EXACT_"
        "CUDA2RR_CUDA4R_SCRATCH_AND_COMP_XPU_004_PRIOR_WEIGHTS_PERMANENTLY_PROHIBITED_AS_PRODUCTION_INITIALIZERS_OR_RESUME_SOURCES_"
        "FRESH_SEED_1337_COMP_CUDA_005_MB1024_CHUNK64_LOGICAL8192_EPOCHS800_ADAM_LR1E_3_FOREACH_FALSE_AUTHORIZED_"
        "TWELVE_MICROBATCHES_TWO_OPTIMIZER_STEPS_PER_EPOCH_1600_TARGET_STEPS_PROFILE_WEIGHTED_ACCUMULATION_FROZEN_"
        "A100_NATIVE_CUDA_RNN_HIGHER_ORDER_AUTOGRAD_TF32_OFF_AMP_OFF_ATOMIC_COMPLETED_EPOCH_RESUME_CONTRACT_BOUND_"
        "NO_TRAINING_IN_CUDA5_NO_OOD_NO_TOF_COMP005_CUDA_FULL_TRAINING_AUTHORIZED_"
        "B3_NOT_AUTHORIZED_STAGE2_SCIENTIFIC_CLOSURE_REQUIRED_AFTER_TRAINING"
    )

    summary_payload = {
        "milestone": MILESTONE,
        "status": status,
        "runner_sha256": self_sha,
        "interpretation_sha256": sha256(INTERPRETATION),
        "authorization_sha256": sha256(AUTHORIZATION),
        "CUDA_accumulation_contract_sha256": sha256(CUDA_ACCUMULATION),
        "CUDA_resume_contract_sha256": sha256(CUDA_RESUME),
        "production_runner_contract_sha256": sha256(PRODUCTION_RUNNER_CONTRACT),
        "handoff_sha256": sha256(HANDOFF),
        "experiment_id": EXPERIMENT_ID,
        "selected_microbatch": MICROBATCH,
        "selected_chunk": VJP_CHUNK,
        "logical_batch_profiles": LOGICAL_BATCH,
        "train_profiles_per_epoch": N_TRAIN,
        "microbatches_per_epoch": MICROBATCHES_PER_EPOCH,
        "optimizer_steps_per_epoch": OPTIMIZER_STEPS_PER_EPOCH,
        "target_optimizer_steps": TARGET_OPTIMIZER_STEPS,
        "epochs": EPOCHS,
        "fresh_initialization_required": True,
        "CUDA4R_scratch_allowed_as_COMP005_resume_source": False,
        "COMP004_allowed_as_COMP005_initializer": False,
        "COMP005_CUDA_full_training_authorized": True,
        "B3_authorized": False,
        "diagnostic_CUDA4R_profiles_per_second": throughput,
        "diagnostic_projected_hours_per_epoch": projected_hours_per_epoch,
        "diagnostic_projected_hours_for_800_epochs": projected_hours_800,
        "diagnostic_projected_days_for_800_epochs": projected_days_800,
        "diagnostic_runtime_promise": False,
        "text_authority_modes": {k: mode for k, (_, mode) in text_authorities.items()},
        "next_milestone": (
            "V16E-1B2CUDA6 — materialize the exact provenance-bound COMP-CUDA-005 production runner; "
            "then execute/resume the fresh 800-epoch corrected Stage-2 CUDA run under CUDA5; "
            "after completion perform Stage-2 scientific closure before B3"
        ),
        "gates": {k: bool(v) for k, v in gates.items()},
    }
    atomic_json_write(summary_payload, SUMMARY)

    print("\nCUDA4R INTERPRETATION")
    print("  logical batch seconds  :", f"{logical_seconds:.3f}")
    print("  throughput             :", f"{throughput:.3f} profiles/s")
    print("  peak CUDA memory       :", f"{peak_gib:.3f} GiB")
    print("  accumulated grad norm  :", f"{grad_norm:.9e}")
    print("  full-8192 equivalence  :", True)
    print("  CUDA4R scratch resume  :", "PERMANENTLY FORBIDDEN")

    print("\nFINAL CUDA PRODUCTION AUTHORIZATION")
    print("  experiment             :", EXPERIMENT_ID)
    print("  fresh seed             :", SEED)
    print("  derivative engine      :", ADOPTED_ENGINE)
    print("  VJP chunk              :", VJP_CHUNK)
    print("  nominal microbatch     :", MICROBATCH)
    print("  logical batch          :", LOGICAL_BATCH)
    print("  microbatches/epoch     :", MICROBATCHES_PER_EPOCH)
    print("  optimizer steps/epoch  :", OPTIMIZER_STEPS_PER_EPOCH)
    print("  epochs                 :", EPOCHS)
    print("  target optimizer steps :", TARGET_OPTIMIZER_STEPS)
    print("  COMP-CUDA-005 training :", "AUTHORIZED")
    print("  B3                      :", "NOT AUTHORIZED")
    print(
        "  diagnostic projection :",
        f"{projected_epoch_seconds:.3f} s/epoch, "
        f"{projected_hours_800:.3f} h/800ep ({projected_days_800:.3f} d), not a promise",
    )

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  CUDA5 Runner       :", self_sha)
    print("  Interpretation     :", sha256(INTERPRETATION))
    print("  Authorization      :", sha256(AUTHORIZATION))
    print("  Accumulation       :", sha256(CUDA_ACCUMULATION))
    print("  Resume Contract    :", sha256(CUDA_RESUME))
    print("  Runner Contract    :", sha256(PRODUCTION_RUNNER_CONTRACT))
    print("  Handoff            :", sha256(HANDOFF))
    print("  Summary            :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary_payload["next_milestone"])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("\nSTATUS")
        print("  V16E1B2CUDA5_A100_FINAL_AUTHORIZATION_FREEZE_FAILURE_COMP005_CUDA_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED")
        print("\nERROR")
        print(" ", repr(exc))
        raise
