#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2CUDA6-A100
Authorized COMP-CUDA-005 Fresh Corrected Stage-2 Production Runner

Experiment
----------
    V16E-BLREP-COMP-CUDA-005

Authority
---------
V16E-1B2CUDA5 authorizes this production run.

Scientific model
----------------
UNCHANGED from the frozen corrected Stage-2 branch:
    * sequence features [xi, eta]
    * raw physical 11-D p11 conditioner
    * 2 x LSTM(64)
    * frozen Godunov conservative teacher
    * corrected conservative moving-fan residual

Certified CUDA execution geometry
---------------------------------
    device/backend        : NVIDIA A100 / CUDA
    recurrent HO-autograd : native CUDA RNN path
    cuDNN                  : disabled only around recurrent higher-order graph
    VJP chunk              : 64
    logical batch          : 8192
    nominal microbatch     : 1024
    microbatches/epoch     : 12
    optimizer steps/epoch  : 2
    epochs                 : 800
    target optimizer steps : 1600
    optimizer              : Adam(lr=1e-3, foreach=False)
    TF32                    : OFF
    AMP                     : OFF
    scheduler               : none
    gradient clipping       : none

Fresh start / resume
--------------------
The production experiment begins from a BRAND-NEW seed=1337 model.
The following are permanently prohibited as production initializers/resume:
    * COMP-XPU-004
    * CUDA2RR scratch
    * CUDA4R scratch
    * any CUDA3 benchmark state
    * any prior Stage-2 checkpoint not created by THIS CUDA6 runner

After production begins, resume is allowed ONLY from this exact runner's
atomic completed-epoch checkpoint with exact runner, source, dataset, CUDA5
contract, optimizer, geometry and RNG bindings.

No mid-epoch, mid-logical-batch, or partial-gradient resume is allowed.
A failed partial epoch is never promoted.

Persistence
-----------
Large immutable inputs are staged from persistent Google Drive into
/content/PAD_Stream_Runtime after exact SHA verification.  Production recovery
checkpoints and final artifacts are written to Google Drive after every
completed epoch so a Colab runtime reset can resume safely.

Evaluation
----------
Development/source-native holdout only. NOT OOD. NO TOF.

Completion
----------
COMP-CUDA-005 is complete only when all 800 epochs and 1600 optimizer steps
finish, the final model/evaluation are finite, all final artifacts are hash-
bound, OOD_used=False and TOF_used=False.

B3 remains blocked.  A separate Stage-2 scientific closure milestone is
required after this run.
"""

from __future__ import annotations

from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import math
import os
import random
import shutil
import subprocess
import time
import traceback
from typing import Any

import numpy as np
import torch


# =============================================================================
# Frozen production identity
# =============================================================================

R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2CUDA6-A100"
EXPERIMENT_ID = "V16E-BLREP-COMP-CUDA-005"

SEED = 1337
TARGET_EPOCHS = 800

ADOPTED_ENGINE = "CHUNKED_BATCHED_VJP_NATIVE_CUDA_RNN"
ADOPTED_CHUNK = 64

LOGICAL_BATCH = 8192
MICROBATCH = 1024
N_TOTAL = 14400
N_TRAIN = 11520
N_HOLDOUT = 2880
SECOND_LOGICAL_CHUNK = 3328

EXPECTED_MICROBATCHES_PER_EPOCH = 12
EXPECTED_OPTIMIZER_STEPS_PER_EPOCH = 2
EXPECTED_TARGET_OPTIMIZER_STEPS = 1600

LR = 1.0e-3

LOSS_WEIGHTS = {
    "lambda_data": 1.0,
    "lambda_phys": 0.05,
    "lambda_bc": 5.0,
    "lambda_tip": 5.0,
    "lambda_anchor": 10.0,
    "lambda_mono": 0.2,
    "lambda_shape": 0.0,
}

RUNTIME_ROOT = Path("/content/PAD_Stream_Runtime")
DRIVE_ROOT = Path("/content/drive/MyDrive/PAD_Stream_Compute")


# =============================================================================
# Frozen authorities
# =============================================================================

DATASET = RUNTIME_ROOT / "datasets" / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
DATASET_DRIVE = DRIVE_ROOT / "datasets" / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

COMP004_CHECKPOINT = RUNTIME_ROOT / "xpu_reference" / "V16E_BLREP_COMP_XPU_004.pt"
COMP004_DRIVE = DRIVE_ROOT / "provenance" / "xpu_reference" / "V16E_BLREP_COMP_XPU_004.pt"
COMP004_CHECKPOINT_SHA = "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69"

B2S_SOURCE = R / "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
B2S_SOURCE_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"

B2AC_SOURCE = R / "PAD_Stream_V16E1B2AC_XPU_Chunked_Batched_VJP_Equivalence_Performance_Sweep.py"
B2AC_SOURCE_SHA = "59f7ea7b0dc2e901f5a42649691c2dab5f4dfc5d399f953eaab5ba773040cd53"

B2AE_SOURCE = R / "PAD_Stream_V16E1B2AE_XPU_COMP005_Execution_Preflight_Contract_Freeze.py"
B2AE_SOURCE_SHA = "8bc7eb7f7a927d172bd7438fde719ee3f31c234acc2a167772dc1f6a556d68cc"

CUDA2RR_SOURCE = R / "PAD_Stream_V16E1B2CUDA2RR_A100_Final_Cross_Platform_Text_Authority_Repair_Rehearsal.py"
CUDA2RR_SOURCE_SHA = "19b369a13832ce131fd7468ea7dd2c2689b2139dadcdf21d774b6266ef7c2755"
CUDA2RR_DIR = DRIVE_ROOT / "provenance" / "cuda_rehearsal" / "V16E1B2CUDA2RR_A100_FINAL_CROSS_PLATFORM_TEXT_AUTHORITY_REPAIR_REHEARSAL"
CUDA2RR_RESULTS = CUDA2RR_DIR / "V16E1B2CUDA2RR_A100_Final_Cross_Platform_Text_Authority_Repair_Results.json"
CUDA2RR_RESULTS_SHA = "7b90304d287d141272c87b1b56dd07ef5b5ecee09773eeb54b348acc0f0e382d"
CUDA2RR_SUMMARY = CUDA2RR_DIR / "PAD_Stream_V16E1B2CUDA2RR_A100_Summary.json"
CUDA2RR_SUMMARY_SHA = "f3e724a222ade1ef684ffab26543769dc50a680ab212643d2c634800c63cf920"
CUDA2RR_SCRATCH = CUDA2RR_DIR / "V16E1B2CUDA2RR_SCRATCH_ONE_LOGICAL_BATCH.pt"
CUDA2RR_SCRATCH_SHA = "3e86248597a85b5880794f7b219726e072aadd8a5fe5dd72d03132ef1d00d014"

CUDA3_SOURCE = R / "PAD_Stream_V16E1B2CUDA3_A100_Microbatch_Batched_VJP_Performance_Sweep.py"
CUDA3_SOURCE_SHA = "1065788f8f82d7f58aba873b8396cf70a17906571421315151640a0c879df886"
CUDA3_DIR = DRIVE_ROOT / "provenance" / "cuda_performance" / "V16E1B2CUDA3_A100_MICROBATCH_BATCHED_VJP_PERFORMANCE_SWEEP"
CUDA3_RESULTS = CUDA3_DIR / "V16E1B2CUDA3_A100_Performance_Sweep_Results.json"
CUDA3_RESULTS_SHA = "c1422884db6ad0bab65f8d91deaed991f79dd593abfa01ca0d4920c14648c2ef"
CUDA3_SUMMARY = CUDA3_DIR / "PAD_Stream_V16E1B2CUDA3_A100_Summary.json"
CUDA3_SUMMARY_SHA = "52daea4d6669f30a94db1e0eeef14da5a541fe560f15c5339612e5b0faff003e"

CUDA4R_SOURCE = R / "PAD_Stream_V16E1B2CUDA4R_A100_CUDA3_K64_Engine_Repair_Full_Logical_Batch_Rehearsal.py"
CUDA4R_SOURCE_SHA = "6bbab60648b5e0ead67b1a51f0e804ded6893005464f390bc08210a8d629a3c1"
CUDA4R_DIR = DRIVE_ROOT / "provenance" / "cuda_rehearsal" / "V16E1B2CUDA4R_A100_CUDA3_K64_ENGINE_REPAIR_FULL_LOGICAL_BATCH_REHEARSAL"
CUDA4R_RESULTS = CUDA4R_DIR / "V16E1B2CUDA4R_A100_CUDA3_K64_Engine_Repair_Full_Logical_Batch_Results.json"
CUDA4R_RESULTS_SHA = "f1548846062617eb7fa9aaba3e8c247411b2640dc778d1f8d44de2c5254439ea"
CUDA4R_GRADS = CUDA4R_DIR / "V16E1B2CUDA4R_MB1024_K64_Full8192_Gradients.pt"
CUDA4R_GRADS_SHA = "d29de777cc8bbb8839d5c63d554042137da6213f9331442b70ff4a018a4c138a"
CUDA4R_SCRATCH = CUDA4R_DIR / "V16E1B2CUDA4R_SCRATCH_ONE_LOGICAL_BATCH.pt"
CUDA4R_SCRATCH_SHA = "235debd529888a22b175a62b4378097514ac5786d2133bd6448d0e3132aedb67"
CUDA4R_SUMMARY = CUDA4R_DIR / "PAD_Stream_V16E1B2CUDA4R_A100_Summary.json"
CUDA4R_SUMMARY_SHA = "80acb080bc16f4814a0d73c3002026d4650741855ce2333546bee1d29f41ec9f"

CUDA5_SOURCE = R / "PAD_Stream_V16E1B2CUDA5_A100_Final_COMP_CUDA_005_Production_Training_Authorization_Freeze.py"
CUDA5_SOURCE_SHA = "b4bae9e3f0931c24b943aaecb20905bb5b0bef211faafb28209f8420e2401b98"
CUDA5_DIR = DRIVE_ROOT / "provenance" / "cuda_authorization" / "V16E1B2CUDA5_A100_FINAL_COMP_CUDA_005_PRODUCTION_TRAINING_AUTHORIZATION_FREEZE"
CUDA5_INTERPRETATION = CUDA5_DIR / "V16E1B2CUDA5_CUDA4R_Interpretation.json"
CUDA5_AUTHORIZATION = CUDA5_DIR / "V16E1B2CUDA5_COMP_CUDA_005_Production_Authorization.json"
CUDA5_ACCUMULATION = CUDA5_DIR / "V16E1B2CUDA5_COMP_CUDA_005_CUDA_Accumulation_Contract.json"
CUDA5_RESUME = CUDA5_DIR / "V16E1B2CUDA5_COMP_CUDA_005_CUDA_Resume_Contract.json"
CUDA5_RUNNER_CONTRACT = CUDA5_DIR / "V16E1B2CUDA5_COMP_CUDA_005_Production_Runner_Contract.json"
CUDA5_HANDOFF = CUDA5_DIR / "V16E1B2CUDA5_COMP_CUDA_005_Handoff.md"
CUDA5_SUMMARY = CUDA5_DIR / "PAD_Stream_V16E1B2CUDA5_A100_Summary.json"

CUDA5_INTERPRETATION_SHA = "1f9c627f96dd7ef5e1cb22aa1a1dd59ea407d531a8c88219dae2686ea00d17aa"
CUDA5_AUTHORIZATION_SHA = "eb259367ce046b3a850bba43d164d0be9c2af3def55282686e3c65639b8db8ab"
CUDA5_ACCUMULATION_SHA = "849c683b3244cd3db7042ee1fb71161c47ff8c1e8d21f7324a53e803c44d44ca"
CUDA5_RESUME_SHA = "d91a9a723f3fdc5cc54d2efc77aa716709eaefc6d163ac5bb495d805e1deec8f"
CUDA5_RUNNER_CONTRACT_SHA = "bc1a4cbac4e28c5014b83375f71ccbf7e321316704abb58d9f848944dc77e3b5"
CUDA5_HANDOFF_SHA = "22f1359f1a8dd1803c64ec85c3fac103e0639c6fc2c4db1665e6a647c2b0a0d3"
CUDA5_SUMMARY_SHA = "7f826de000315573792b4618743cea54a277580d97f19f26cefaf72dc307274c"

EXPECTED_CUDA5_STATUS = (
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


# =============================================================================
# Production output paths (persistent Drive)
# =============================================================================

OUT = DRIVE_ROOT / "runs" / EXPERIMENT_ID
RECOVERY_DIR = OUT / "recovery"
OUT.mkdir(parents=True, exist_ok=True)
RECOVERY_DIR.mkdir(parents=True, exist_ok=True)

RECOVERY_LATEST = RECOVERY_DIR / "V16E_BLREP_COMP_CUDA_005_RECOVERY_LATEST.json"
CONFIG = OUT / "V16E_BLREP_COMP_CUDA_005_Config.json"
HISTORY = OUT / "V16E_BLREP_COMP_CUDA_005_Training_History.json"
CHECKPOINT = OUT / "V16E_BLREP_COMP_CUDA_005.pt"
METRICS = OUT / "V16E_BLREP_COMP_CUDA_005_Metrics.json"
MANIFEST = OUT / "V16E_BLREP_COMP_CUDA_005_Manifest.json"
FAILURE = OUT / "V16E_BLREP_COMP_CUDA_005_Latest_Failure.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2CUDA6_A100_Summary.json"


# =============================================================================
# General helpers
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


def jsonable(v):
    if isinstance(v, dict):
        return {str(k): jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (np.integer, np.floating, np.bool_)):
        return v.item()
    if isinstance(v, Path):
        return str(v)
    return v


def finite(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_git(*args: str) -> str:
    p = subprocess.run(["git", "-C", str(R), *args], text=True, capture_output=True, check=True)
    return p.stdout.strip()


def atomic_json_write(payload, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    tmp.write_text(json.dumps(jsonable(payload), indent=2), encoding="utf-8")
    os.replace(tmp, destination)


def atomic_text_write(text: str, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, destination)


def atomic_torch_save(payload, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()
    torch.save(payload, tmp)
    if not tmp.exists() or tmp.stat().st_size <= 0:
        raise RuntimeError("Temporary checkpoint was not written.")
    os.replace(tmp, destination)
    if not destination.exists() or destination.stat().st_size <= 0:
        raise RuntimeError("Final checkpoint was not written.")


def cpu_clone(obj: Any):
    if torch.is_tensor(obj):
        return obj.detach().cpu().clone()
    if isinstance(obj, dict):
        return {k: cpu_clone(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [cpu_clone(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(cpu_clone(v) for v in obj)
    return copy.deepcopy(obj)


def exact_tree_equal(a: Any, b: Any) -> bool:
    if torch.is_tensor(a) or torch.is_tensor(b):
        return torch.is_tensor(a) and torch.is_tensor(b) and a.shape == b.shape and a.dtype == b.dtype and torch.equal(a.detach().cpu(), b.detach().cpu())
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return isinstance(a, np.ndarray) and isinstance(b, np.ndarray) and a.shape == b.shape and a.dtype == b.dtype and np.array_equal(a, b)
    if isinstance(a, dict) or isinstance(b, dict):
        return isinstance(a, dict) and isinstance(b, dict) and set(a.keys()) == set(b.keys()) and all(exact_tree_equal(a[k], b[k]) for k in a.keys())
    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        return type(a) is type(b) and len(a) == len(b) and all(exact_tree_equal(x, y) for x, y in zip(a, b))
    return a == b


def move_optimizer_state_to_device(optimizer, device):
    for state in optimizer.state.values():
        for key, value in list(state.items()):
            if torch.is_tensor(value):
                state[key] = value.to(device)


def sync_cuda():
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def all_model_parameters_finite(model) -> bool:
    return all(torch.isfinite(p.detach()).all().item() for p in model.parameters())


def parameter_gradient_summary(model):
    tensor_count = 0
    nonzero_count = 0
    finite_all = True
    grad_sq = 0.0
    for p in model.parameters():
        if p.grad is None:
            continue
        tensor_count += 1
        g = p.grad.detach()
        if not torch.isfinite(g).all().item():
            finite_all = False
        if torch.count_nonzero(g).item() > 0:
            nonzero_count += 1
        grad_sq += float(torch.sum(g.double() ** 2).cpu())
    return {
        "gradient_tensor_count": int(tensor_count),
        "nonzero_gradient_tensor_count": int(nonzero_count),
        "gradients_finite": bool(finite_all),
        "gradient_l2_norm": float(math.sqrt(max(grad_sq, 0.0))),
    }


def ensure_runtime_copy(runtime_path: Path, drive_path: Path, expected_sha: str, label: str):
    if exact(runtime_path, expected_sha):
        return
    if not exact(drive_path, expected_sha):
        raise RuntimeError(f"{label}: neither exact runtime copy nor exact Drive authority is available. Drive path: {drive_path}")
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = runtime_path.with_suffix(runtime_path.suffix + ".tmp")
    shutil.copy2(drive_path, tmp)
    os.replace(tmp, runtime_path)
    if not exact(runtime_path, expected_sha):
        raise RuntimeError(f"{label}: runtime materialization SHA mismatch.")
    print(f"[RUNTIME] Restored {label} from persistent Drive authority.")


# =============================================================================
# RNG state helpers
# =============================================================================

def capture_rng_state():
    return {
        "python": copy.deepcopy(random.getstate()),
        "numpy": copy.deepcopy(np.random.get_state()),
        "torch_cpu": torch.get_rng_state().detach().cpu().clone(),
        "torch_cuda": [s.detach().cpu().clone() for s in torch.cuda.get_rng_state_all()] if torch.cuda.is_available() else None,
    }


def restore_rng_state(state):
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch_cpu"])
    if state.get("torch_cuda") is not None:
        torch.cuda.set_rng_state_all(state["torch_cuda"])


# =============================================================================
# Frozen split / epoch order
# =============================================================================

def frozen_split(n: int):
    rng = np.random.default_rng(SEED)
    idx = np.arange(n)
    rng.shuffle(idx)
    n_train = int(0.8 * n)
    return idx[:n_train], idx[n_train:]


def production_epoch_order(train_idx, epoch: int):
    erng = np.random.default_rng(SEED + epoch)
    order = train_idx.copy()
    erng.shuffle(order)
    return order


# =============================================================================
# CUDA5 authority validation
# =============================================================================

def authority_gates():
    s5 = read_json(CUDA5_SUMMARY) if CUDA5_SUMMARY.exists() else {}
    a5 = read_json(CUDA5_AUTHORIZATION) if CUDA5_AUTHORIZATION.exists() else {}
    r5 = read_json(CUDA5_RUNNER_CONTRACT) if CUDA5_RUNNER_CONTRACT.exists() else {}

    bind = r5.get("runner_must_bind", {}) if isinstance(r5, dict) else {}

    gates = {
        "git_working_tree_clean": run_git("status", "--porcelain") == "",
        "CUDA_available": torch.cuda.is_available(),
        "A100_runtime": torch.cuda.is_available() and "A100" in torch.cuda.get_device_name(0).upper(),
        "TF32_matmul_disabled": torch.cuda.is_available() and not torch.backends.cuda.matmul.allow_tf32,
        "TF32_cudnn_disabled": torch.cuda.is_available() and not torch.backends.cudnn.allow_tf32,
        "dataset_SHA_exact": exact(DATASET, DATASET_SHA),
        "COMP004_checkpoint_SHA_exact": exact(COMP004_CHECKPOINT, COMP004_CHECKPOINT_SHA),
        "B2S_source_SHA_exact": exact(B2S_SOURCE, B2S_SOURCE_SHA),
        "B2AC_source_SHA_exact": exact(B2AC_SOURCE, B2AC_SOURCE_SHA),
        "B2AE_source_SHA_exact": exact(B2AE_SOURCE, B2AE_SOURCE_SHA),
        "CUDA2RR_source_SHA_exact": exact(CUDA2RR_SOURCE, CUDA2RR_SOURCE_SHA),
        "CUDA2RR_results_SHA_exact": exact(CUDA2RR_RESULTS, CUDA2RR_RESULTS_SHA),
        "CUDA2RR_summary_SHA_exact": exact(CUDA2RR_SUMMARY, CUDA2RR_SUMMARY_SHA),
        "CUDA2RR_scratch_SHA_exact": exact(CUDA2RR_SCRATCH, CUDA2RR_SCRATCH_SHA),
        "CUDA3_source_SHA_exact": exact(CUDA3_SOURCE, CUDA3_SOURCE_SHA),
        "CUDA3_results_SHA_exact": exact(CUDA3_RESULTS, CUDA3_RESULTS_SHA),
        "CUDA3_summary_SHA_exact": exact(CUDA3_SUMMARY, CUDA3_SUMMARY_SHA),
        "CUDA4R_source_SHA_exact": exact(CUDA4R_SOURCE, CUDA4R_SOURCE_SHA),
        "CUDA4R_results_SHA_exact": exact(CUDA4R_RESULTS, CUDA4R_RESULTS_SHA),
        "CUDA4R_gradients_SHA_exact": exact(CUDA4R_GRADS, CUDA4R_GRADS_SHA),
        "CUDA4R_scratch_SHA_exact": exact(CUDA4R_SCRATCH, CUDA4R_SCRATCH_SHA),
        "CUDA4R_summary_SHA_exact": exact(CUDA4R_SUMMARY, CUDA4R_SUMMARY_SHA),
        "CUDA5_source_SHA_exact": exact(CUDA5_SOURCE, CUDA5_SOURCE_SHA),
        "CUDA5_interpretation_SHA_exact": exact(CUDA5_INTERPRETATION, CUDA5_INTERPRETATION_SHA),
        "CUDA5_authorization_SHA_exact": exact(CUDA5_AUTHORIZATION, CUDA5_AUTHORIZATION_SHA),
        "CUDA5_accumulation_SHA_exact": exact(CUDA5_ACCUMULATION, CUDA5_ACCUMULATION_SHA),
        "CUDA5_resume_SHA_exact": exact(CUDA5_RESUME, CUDA5_RESUME_SHA),
        "CUDA5_runner_contract_SHA_exact": exact(CUDA5_RUNNER_CONTRACT, CUDA5_RUNNER_CONTRACT_SHA),
        "CUDA5_handoff_SHA_exact": exact(CUDA5_HANDOFF, CUDA5_HANDOFF_SHA),
        "CUDA5_summary_SHA_exact": exact(CUDA5_SUMMARY, CUDA5_SUMMARY_SHA),
        "CUDA5_status_exact": s5.get("status") == EXPECTED_CUDA5_STATUS,
        "CUDA5_experiment_exact": s5.get("experiment_id") == EXPERIMENT_ID,
        "CUDA5_MB1024": s5.get("selected_microbatch") == MICROBATCH,
        "CUDA5_K64": s5.get("selected_chunk") == ADOPTED_CHUNK,
        "CUDA5_logical8192": s5.get("logical_batch_profiles") == LOGICAL_BATCH,
        "CUDA5_train11520": s5.get("train_profiles_per_epoch") == N_TRAIN,
        "CUDA5_microbatches12": s5.get("microbatches_per_epoch") == EXPECTED_MICROBATCHES_PER_EPOCH,
        "CUDA5_steps_per_epoch2": s5.get("optimizer_steps_per_epoch") == EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
        "CUDA5_target_steps1600": s5.get("target_optimizer_steps") == EXPECTED_TARGET_OPTIMIZER_STEPS,
        "CUDA5_epochs800": s5.get("epochs") == TARGET_EPOCHS,
        "CUDA5_fresh_init_required": s5.get("fresh_initialization_required") is True,
        "CUDA5_training_authorized": s5.get("COMP005_CUDA_full_training_authorized") is True,
        "CUDA5_B3_false": s5.get("B3_authorized") is False,
        "authorization_training_true": a5.get("COMP005_CUDA_full_training_authorized") is True,
        "authorization_B3_false": a5.get("B3_authorized") is False,
        "authorization_fresh_true": a5.get("fresh_initialization_required") is True,
        "runner_contract_experiment_exact": r5.get("experiment_id") == EXPERIMENT_ID,
        "runner_contract_dataset_bind": bind.get("dataset_sha256") == DATASET_SHA,
        "runner_contract_B2S_bind": bind.get("B2S_source_sha256") == B2S_SOURCE_SHA,
        "runner_contract_B2AC_bind": bind.get("B2AC_source_sha256") == B2AC_SOURCE_SHA,
        "runner_contract_CUDA2RR_results_bind": bind.get("CUDA2RR_results_sha256") == CUDA2RR_RESULTS_SHA,
        "runner_contract_CUDA2RR_summary_bind": bind.get("CUDA2RR_summary_sha256") == CUDA2RR_SUMMARY_SHA,
        "runner_contract_CUDA3_bind": bind.get("CUDA3_source_sha256") == CUDA3_SOURCE_SHA,
        "runner_contract_CUDA3_results_bind": bind.get("CUDA3_results_sha256") == CUDA3_RESULTS_SHA,
        "runner_contract_CUDA3_summary_bind": bind.get("CUDA3_summary_sha256") == CUDA3_SUMMARY_SHA,
        "runner_contract_CUDA4R_bind": bind.get("CUDA4R_source_sha256") == CUDA4R_SOURCE_SHA,
        "runner_contract_CUDA4R_results_bind": bind.get("CUDA4R_results_sha256") == CUDA4R_RESULTS_SHA,
        "runner_contract_CUDA4R_gradients_bind": bind.get("CUDA4R_selected_gradients_sha256") == CUDA4R_GRADS_SHA,
        "runner_contract_CUDA4R_scratch_bind": bind.get("CUDA4R_scratch_checkpoint_sha256_provenance_only") == CUDA4R_SCRATCH_SHA,
        "runner_contract_CUDA4R_summary_bind": bind.get("CUDA4R_summary_sha256") == CUDA4R_SUMMARY_SHA,
        "runner_contract_CUDA5_interpretation_bind": bind.get("CUDA5_interpretation_sha256") == CUDA5_INTERPRETATION_SHA,
        "runner_contract_CUDA5_authorization_bind": bind.get("CUDA5_authorization_sha256") == CUDA5_AUTHORIZATION_SHA,
        "runner_contract_CUDA5_accumulation_bind": bind.get("CUDA5_accumulation_contract_sha256") == CUDA5_ACCUMULATION_SHA,
        "runner_contract_CUDA5_resume_bind": bind.get("CUDA5_resume_contract_sha256") == CUDA5_RESUME_SHA,
        "runner_contract_CUDA5_source_bind": bind.get("CUDA5_runner_freeze_source_sha256") == CUDA5_SOURCE_SHA,
        "no_OOD": True,
        "no_TOF": True,
    }
    return gates


# =============================================================================
# Fresh model construction
# =============================================================================

def build_fresh_model_optimizer(B2S, device, suffix: str):
    M = B2S.import_module(B2S.BASE_RUNNER, f"cuda6_base_{suffix}")
    J = B2S.import_module(B2S.B2J_SOURCE, f"cuda6_eta_{suffix}")

    if not exact(B2S.BASE_RUNNER, B2S.BASE_RUNNER_SHA):
        raise RuntimeError("B2S-bound base runner SHA mismatch.")
    if not exact(B2S.B2J_SOURCE, B2S.B2J_SOURCE_SHA):
        raise RuntimeError("B2S-bound eta-model source SHA mismatch.")
    if int(M.SEED) != SEED:
        raise RuntimeError(f"Frozen base-runner seed mismatch: {M.SEED}")
    if int(M.LOGICAL_BATCH) != LOGICAL_BATCH:
        raise RuntimeError(f"Frozen base-runner logical batch mismatch: {M.LOGICAL_BATCH}")

    expected_losses = {
        "lambda_data": float(M.LAMBDA_DATA),
        "lambda_phys": float(M.LAMBDA_PHYS),
        "lambda_bc": float(M.LAMBDA_BC),
        "lambda_tip": float(M.LAMBDA_TIP),
        "lambda_anchor": float(M.LAMBDA_ANCHOR),
        "lambda_mono": float(M.LAMBDA_MONO),
        "lambda_shape": float(getattr(M, "LAMBDA_SHAPE", 0.0)),
    }
    if expected_losses != LOSS_WEIGHTS:
        raise RuntimeError(f"Frozen Stage-2 loss weights mismatch. Expected {LOSS_WEIGHTS}, actual {expected_losses}")

    EtaModel = J.build_eta_model_class(M)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    model = EtaModel().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, foreach=False)
    return M, J, model, optimizer


# =============================================================================
# Production config / provenance map
# =============================================================================

def source_sha_map(runner_sha: str, B2S):
    return {
        "CUDA6_runner_sha256": runner_sha,
        "B2S_source_sha256": B2S_SOURCE_SHA,
        "B2S_base_runner_sha256": B2S.BASE_RUNNER_SHA,
        "B2S_eta_source_sha256": B2S.B2J_SOURCE_SHA,
        "B2AC_source_sha256": B2AC_SOURCE_SHA,
        "B2AE_source_sha256": B2AE_SOURCE_SHA,
        "CUDA2RR_source_sha256": CUDA2RR_SOURCE_SHA,
        "CUDA3_source_sha256": CUDA3_SOURCE_SHA,
        "CUDA4R_source_sha256": CUDA4R_SOURCE_SHA,
        "CUDA5_source_sha256": CUDA5_SOURCE_SHA,
    }


def expected_config(runner_sha: str, B2S):
    return {
        "milestone": MILESTONE,
        "experiment_id": EXPERIMENT_ID,
        "classification": "AUTHORIZED_FRESH_CORRECTED_STAGE2_CUDA_PRODUCTION_RUN",
        "runner_sha256": runner_sha,
        "framework": {
            "name": "PyTorch CUDA",
            "pytorch_version": torch.__version__,
            "device": torch.cuda.get_device_name(0),
            "mixed_precision": False,
            "TF32_matmul": False,
            "TF32_cudnn": False,
        },
        "fresh_initialization": {
            "required": True,
            "seed": SEED,
            "COMP004_initializer": False,
            "CUDA2RR_scratch_initializer": False,
            "CUDA4R_scratch_initializer": False,
        },
        "scientific_model": {
            "sequence_features": ["xi", "eta"],
            "conditioner_dim": 11,
            "hidden": 64,
            "layers": 2,
            "physical_Nc_scaled": False,
            "corrected_residual": "conservative moving-fan residual",
            "scientific_graph_source_sha256": B2S_SOURCE_SHA,
            "scientific_change": False,
        },
        "derivative_engine": {
            "name": ADOPTED_ENGINE,
            "cotangent_chunk_size": ADOPTED_CHUNK,
            "implementation_source_sha256": CUDA3_SOURCE_SHA,
            "cudnn_disabled_only_around_higher_order_graph": True,
        },
        "training": {
            "train_profiles": N_TRAIN,
            "holdout_profiles": N_HOLDOUT,
            "logical_batch": LOGICAL_BATCH,
            "microbatch": MICROBATCH,
            "microbatches_per_epoch": EXPECTED_MICROBATCHES_PER_EPOCH,
            "optimizer_steps_per_epoch": EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
            "epochs": TARGET_EPOCHS,
            "target_optimizer_steps": EXPECTED_TARGET_OPTIMIZER_STEPS,
            "logical_chunks_per_epoch": [LOGICAL_BATCH, SECOND_LOGICAL_CHUNK],
        },
        "optimizer": {
            "name": "Adam",
            "learning_rate": LR,
            "foreach": False,
            "scheduler": None,
            "gradient_clipping": None,
        },
        "loss_weights": LOSS_WEIGHTS,
        "CUDA5_contracts": {
            "authorization_sha256": CUDA5_AUTHORIZATION_SHA,
            "accumulation_sha256": CUDA5_ACCUMULATION_SHA,
            "resume_sha256": CUDA5_RESUME_SHA,
            "runner_contract_sha256": CUDA5_RUNNER_CONTRACT_SHA,
            "summary_sha256": CUDA5_SUMMARY_SHA,
        },
        "dataset": {"path": str(DATASET), "sha256": DATASET_SHA},
        "evaluation": {"role": "development diagnostic; NOT OOD", "OOD": False, "TOF": False},
    }


# =============================================================================
# Recovery checkpoints
# =============================================================================

def recovery_path(epoch: int) -> Path:
    return RECOVERY_DIR / f"V16E_BLREP_COMP_CUDA_005_RECOVERY_E{epoch:04d}.pt"


def save_recovery_checkpoint(B2S, runner_sha, model, optimizer, history, completed_epoch, optimizer_steps_completed, train_idx, holdout_idx):
    if completed_epoch < 1:
        raise RuntimeError("Production recovery checkpoint requires completed_epoch >= 1.")
    if optimizer_steps_completed != completed_epoch * EXPECTED_OPTIMIZER_STEPS_PER_EPOCH:
        raise RuntimeError("Optimizer-step count inconsistent with completed epoch.")

    rng = capture_rng_state()
    ck_path = recovery_path(completed_epoch)
    payload = {
        "recovery_schema": "V16E1B2CUDA6_COMP_CUDA_005_COMPLETED_EPOCH_V1",
        "experiment_id": EXPERIMENT_ID,
        "created_by_authorized_CUDA6_runner": True,
        "runner_sha256": runner_sha,
        "completed_epoch": int(completed_epoch),
        "optimizer_steps_completed": int(optimizer_steps_completed),
        "target_epochs": TARGET_EPOCHS,
        "target_optimizer_steps": EXPECTED_TARGET_OPTIMIZER_STEPS,
        "seed": SEED,
        "logical_batch": LOGICAL_BATCH,
        "microbatch": MICROBATCH,
        "microbatches_per_epoch": EXPECTED_MICROBATCHES_PER_EPOCH,
        "derivative_engine": ADOPTED_ENGINE,
        "cotangent_chunk_size": ADOPTED_CHUNK,
        "learning_rate": LR,
        "optimizer": "Adam(foreach=False)",
        "CUDA5_authorization_sha256": CUDA5_AUTHORIZATION_SHA,
        "CUDA5_accumulation_sha256": CUDA5_ACCUMULATION_SHA,
        "CUDA5_resume_sha256": CUDA5_RESUME_SHA,
        "CUDA5_runner_contract_sha256": CUDA5_RUNNER_CONTRACT_SHA,
        "CUDA5_summary_sha256": CUDA5_SUMMARY_SHA,
        "dataset_sha256": DATASET_SHA,
        "source_sha256_map": source_sha_map(runner_sha, B2S),
        "model_state_dict": cpu_clone(model.state_dict()),
        "optimizer_state_dict": cpu_clone(optimizer.state_dict()),
        "history": copy.deepcopy(history),
        "train_idx": np.asarray(train_idx, dtype=np.int64),
        "holdout_idx": np.asarray(holdout_idx, dtype=np.int64),
        "python_rng_state": rng["python"],
        "numpy_rng_state": rng["numpy"],
        "torch_cpu_rng_state": rng["torch_cpu"],
        "torch_cuda_rng_state": rng["torch_cuda"],
        "training_semantics": {
            "fresh_experiment": True,
            "epoch_boundary_only": True,
            "partial_epoch_accepted": False,
            "optimizer_state_restored_on_resume": True,
            "COMP004_resume": False,
            "CUDA2RR_scratch_resume": False,
            "CUDA4R_scratch_resume": False,
            "OOD": False,
            "TOF": False,
        },
    }
    atomic_torch_save(payload, ck_path)
    ck_sha = sha256(ck_path)

    latest = {
        "experiment_id": EXPERIMENT_ID,
        "created_by_authorized_CUDA6_runner": True,
        "runner_sha256": runner_sha,
        "completed_epoch": int(completed_epoch),
        "optimizer_steps_completed": int(optimizer_steps_completed),
        "checkpoint_path": str(ck_path),
        "checkpoint_sha256": ck_sha,
        "CUDA5_authorization_sha256": CUDA5_AUTHORIZATION_SHA,
        "CUDA5_resume_sha256": CUDA5_RESUME_SHA,
        "CUDA5_runner_contract_sha256": CUDA5_RUNNER_CONTRACT_SHA,
        "dataset_sha256": DATASET_SHA,
        "derivative_engine": ADOPTED_ENGINE,
        "cotangent_chunk_size": ADOPTED_CHUNK,
        "logical_batch": LOGICAL_BATCH,
        "microbatch": MICROBATCH,
        "seed": SEED,
    }
    atomic_json_write(latest, RECOVERY_LATEST)

    keep_epochs = {completed_epoch, max(completed_epoch - 1, 1)}
    for old in RECOVERY_DIR.glob("V16E_BLREP_COMP_CUDA_005_RECOVERY_E*.pt"):
        try:
            old_epoch = int(old.stem.split("_E")[-1])
        except Exception:
            continue
        if old_epoch not in keep_epochs:
            try:
                old.unlink()
            except OSError:
                pass

    print(f"  [RECOVERY] completed epoch {completed_epoch:04d} | optimizer steps {optimizer_steps_completed:04d}")
    print("             SHA-256:", ck_sha)
    return ck_path, ck_sha


def load_valid_recovery(B2S, runner_sha, model, optimizer, device):
    if not RECOVERY_LATEST.exists():
        stale = list(RECOVERY_DIR.glob("V16E_BLREP_COMP_CUDA_005_RECOVERY_E*.pt"))
        if stale:
            raise RuntimeError("Recovery checkpoint files exist but exact LATEST pointer is missing; refusing ambiguous resume.")
        return None

    latest = read_json(RECOVERY_LATEST)
    pointer_checks = {
        "experiment_id": latest.get("experiment_id") == EXPERIMENT_ID,
        "created_by_runner": latest.get("created_by_authorized_CUDA6_runner") is True,
        "runner_sha": latest.get("runner_sha256") == runner_sha,
        "CUDA5_authorization": latest.get("CUDA5_authorization_sha256") == CUDA5_AUTHORIZATION_SHA,
        "CUDA5_resume": latest.get("CUDA5_resume_sha256") == CUDA5_RESUME_SHA,
        "CUDA5_runner_contract": latest.get("CUDA5_runner_contract_sha256") == CUDA5_RUNNER_CONTRACT_SHA,
        "dataset": latest.get("dataset_sha256") == DATASET_SHA,
        "engine": latest.get("derivative_engine") == ADOPTED_ENGINE,
        "chunk": latest.get("cotangent_chunk_size") == ADOPTED_CHUNK,
        "logical_batch": latest.get("logical_batch") == LOGICAL_BATCH,
        "microbatch": latest.get("microbatch") == MICROBATCH,
        "seed": latest.get("seed") == SEED,
    }
    if not all(pointer_checks.values()):
        raise RuntimeError("Production recovery pointer mismatch: " + ", ".join(k for k, v in pointer_checks.items() if not v))

    ck_path = Path(latest["checkpoint_path"])
    if not ck_path.exists():
        raise RuntimeError(f"Recovery checkpoint does not exist: {ck_path}")
    actual_sha = sha256(ck_path)
    if actual_sha != latest.get("checkpoint_sha256"):
        raise RuntimeError("Production recovery checkpoint SHA mismatch.")
    if actual_sha in {COMP004_CHECKPOINT_SHA, CUDA2RR_SCRATCH_SHA, CUDA4R_SCRATCH_SHA}:
        raise RuntimeError("A prohibited prior/scratch checkpoint was presented as COMP-CUDA-005 recovery.")

    payload = torch.load(ck_path, map_location="cpu", weights_only=False)
    completed_epoch = int(payload.get("completed_epoch", -1))
    optimizer_steps_completed = int(payload.get("optimizer_steps_completed", -1))
    checks = {
        "schema": payload.get("recovery_schema") == "V16E1B2CUDA6_COMP_CUDA_005_COMPLETED_EPOCH_V1",
        "experiment_id": payload.get("experiment_id") == EXPERIMENT_ID,
        "created_by_runner": payload.get("created_by_authorized_CUDA6_runner") is True,
        "runner_sha": payload.get("runner_sha256") == runner_sha,
        "completed_epoch_range": 1 <= completed_epoch <= TARGET_EPOCHS,
        "optimizer_steps": optimizer_steps_completed == completed_epoch * EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
        "target_epochs": payload.get("target_epochs") == TARGET_EPOCHS,
        "target_optimizer_steps": payload.get("target_optimizer_steps") == EXPECTED_TARGET_OPTIMIZER_STEPS,
        "seed": payload.get("seed") == SEED,
        "logical_batch": payload.get("logical_batch") == LOGICAL_BATCH,
        "microbatch": payload.get("microbatch") == MICROBATCH,
        "microbatches_per_epoch": payload.get("microbatches_per_epoch") == EXPECTED_MICROBATCHES_PER_EPOCH,
        "engine": payload.get("derivative_engine") == ADOPTED_ENGINE,
        "chunk": payload.get("cotangent_chunk_size") == ADOPTED_CHUNK,
        "learning_rate": payload.get("learning_rate") == LR,
        "CUDA5_authorization": payload.get("CUDA5_authorization_sha256") == CUDA5_AUTHORIZATION_SHA,
        "CUDA5_accumulation": payload.get("CUDA5_accumulation_sha256") == CUDA5_ACCUMULATION_SHA,
        "CUDA5_resume": payload.get("CUDA5_resume_sha256") == CUDA5_RESUME_SHA,
        "CUDA5_runner_contract": payload.get("CUDA5_runner_contract_sha256") == CUDA5_RUNNER_CONTRACT_SHA,
        "CUDA5_summary": payload.get("CUDA5_summary_sha256") == CUDA5_SUMMARY_SHA,
        "dataset": payload.get("dataset_sha256") == DATASET_SHA,
        "source_sha_map": payload.get("source_sha256_map") == source_sha_map(runner_sha, B2S),
    }
    if not all(checks.values()):
        raise RuntimeError("Production recovery payload mismatch: " + ", ".join(k for k, v in checks.items() if not v))

    history = payload.get("history", {})
    if not isinstance(history.get("epoch"), list) or len(history["epoch"]) != completed_epoch or history["epoch"][-1] != completed_epoch:
        raise RuntimeError("Production recovery history does not match completed epoch.")

    train_idx = np.asarray(payload["train_idx"], dtype=np.int64)
    holdout_idx = np.asarray(payload["holdout_idx"], dtype=np.int64)
    expected_train, expected_holdout = frozen_split(N_TOTAL)
    if not np.array_equal(train_idx, expected_train) or not np.array_equal(holdout_idx, expected_holdout):
        raise RuntimeError("Production recovery split differs from frozen split.")

    model.load_state_dict(payload["model_state_dict"], strict=True)
    model.to(device)
    optimizer.load_state_dict(payload["optimizer_state_dict"])
    move_optimizer_state_to_device(optimizer, device)
    restore_rng_state({
        "python": payload["python_rng_state"],
        "numpy": payload["numpy_rng_state"],
        "torch_cpu": payload["torch_cpu_rng_state"],
        "torch_cuda": payload["torch_cuda_rng_state"],
    })
    sync_cuda()
    if not all_model_parameters_finite(model):
        raise RuntimeError("Recovered model contains nonfinite parameters.")

    print("\nVALID PRODUCTION RECOVERY FOUND")
    print("  completed epoch       :", completed_epoch)
    print("  optimizer steps       :", optimizer_steps_completed)
    print("  checkpoint            :", ck_path)
    print("  checkpoint SHA-256    :", actual_sha)
    print("  next epoch            :", completed_epoch + 1)

    return {
        "completed_epoch": completed_epoch,
        "optimizer_steps_completed": optimizer_steps_completed,
        "history": history,
        "train_idx": train_idx,
        "holdout_idx": holdout_idx,
        "checkpoint_path": ck_path,
        "checkpoint_sha256": actual_sha,
    }


# =============================================================================
# Training
# =============================================================================

def empty_history():
    return {
        "epoch": [], "data": [], "physics": [], "bc_inj": [], "bc_tip": [],
        "anchor": [], "mono": [], "total": [], "epoch_seconds": [],
        "optimizer_steps_completed": [],
    }


def train_or_resume(B2S, CUDA3, M, model, optimizer, arrays, device, runner_sha):
    xi_all, Sw_all, p11_all, _tD_all, ai_all, at_all = arrays
    train_idx, holdout_idx = frozen_split(len(xi_all))
    if len(train_idx) != N_TRAIN or len(holdout_idx) != N_HOLDOUT:
        raise RuntimeError("Frozen 80/20 split counts are not 11520/2880.")

    history = empty_history()
    recovery = load_valid_recovery(B2S, runner_sha, model, optimizer, device)
    if recovery is None:
        start_epoch = 1
        optimizer_steps_completed = 0
        print("\nPRODUCTION START")
        print("  mode                  : FRESH")
        print("  seed                  :", SEED)
        print("  COMP-XPU-004 weights  : NOT LOADED")
        print("  CUDA2RR scratch       : NOT LOADED")
        print("  CUDA4R scratch        : NOT LOADED")
    else:
        start_epoch = recovery["completed_epoch"] + 1
        optimizer_steps_completed = recovery["optimizer_steps_completed"]
        history = recovery["history"]
        train_idx = recovery["train_idx"]
        holdout_idx = recovery["holdout_idx"]
        print("  mode                  : RESUME")

    print("\nPRODUCTION TRAINING CONTRACT")
    print("  device                :", device)
    print("  train profiles        :", len(train_idx))
    print("  holdout profiles      :", len(holdout_idx))
    print("  derivative engine     :", ADOPTED_ENGINE)
    print("  VJP chunk             :", ADOPTED_CHUNK)
    print("  logical batch         :", LOGICAL_BATCH)
    print("  microbatch            :", MICROBATCH)
    print("  microbatches/epoch    :", EXPECTED_MICROBATCHES_PER_EPOCH)
    print("  optimizer steps/epoch :", EXPECTED_OPTIMIZER_STEPS_PER_EPOCH)
    print("  target epochs         :", TARGET_EPOCHS)
    print("  target optimizer steps:", EXPECTED_TARGET_OPTIMIZER_STEPS)
    print("  starting epoch        :", start_epoch)
    print("  TF32                  : OFF")
    print("  AMP                   : OFF")

    if start_epoch > TARGET_EPOCHS:
        if len(history["epoch"]) != TARGET_EPOCHS or optimizer_steps_completed != EXPECTED_TARGET_OPTIMIZER_STEPS:
            raise RuntimeError("Recovery claims training beyond target but history/step count is inconsistent.")
        return history, train_idx, holdout_idx, optimizer_steps_completed

    engine = CUDA3.make_cuda3_chunked_batched_engine(ADOPTED_CHUNK)
    original_engine = B2S.local_recurrent_derivatives_create_graph
    session_t0 = time.time()

    try:
        B2S.local_recurrent_derivatives_create_graph = engine
        model.train()

        for epoch in range(start_epoch, TARGET_EPOCHS + 1):
            epoch_t0 = time.time()
            order = production_epoch_order(train_idx, epoch)
            sums = {"data": 0.0, "physics": 0.0, "bc_inj": 0.0, "bc_tip": 0.0, "anchor": 0.0, "mono": 0.0, "total": 0.0}
            count = 0
            epoch_microbatches = 0
            epoch_optimizer_steps = 0

            for b0 in range(0, len(order), LOGICAL_BATCH):
                logical_idx = order[b0:b0 + LOGICAL_BATCH]
                logical_n = len(logical_idx)
                if logical_n not in (LOGICAL_BATCH, SECOND_LOGICAL_CHUNK):
                    raise RuntimeError(f"Unexpected logical chunk size {logical_n}.")

                optimizer.zero_grad(set_to_none=True)
                for m0 in range(0, logical_n, MICROBATCH):
                    ids = logical_idx[m0:m0 + MICROBATCH]
                    m = len(ids)
                    if m <= 0:
                        raise RuntimeError("Empty training microbatch.")

                    xi = torch.from_numpy(xi_all[ids]).to(device).detach().clone().requires_grad_(True)
                    Sw = torch.from_numpy(Sw_all[ids]).to(device)
                    p11 = torch.from_numpy(p11_all[ids]).to(device).detach().clone().requires_grad_(True)
                    ai = torch.from_numpy(ai_all[ids]).to(device)
                    at = torch.from_numpy(at_all[ids]).to(device)

                    with torch.backends.cudnn.flags(enabled=False):
                        S_pred, residual, parts = B2S.complete_corrected_total_loss(M, model, xi, Sw, p11, ai, at)

                    if not torch.isfinite(S_pred).all().item():
                        raise RuntimeError(f"Epoch {epoch}: nonfinite prediction.")
                    if not torch.isfinite(residual).all().item():
                        raise RuntimeError(f"Epoch {epoch}: nonfinite corrected residual.")
                    if not all(torch.isfinite(v).all().item() for v in parts.values()):
                        raise RuntimeError(f"Epoch {epoch}: nonfinite loss.")

                    scale = float(m) / float(logical_n)
                    scaled_total = parts["total"] * scale
                    with torch.backends.cudnn.flags(enabled=False):
                        scaled_total.backward()

                    for k in sums:
                        sums[k] += float(parts[k].detach().cpu()) * m
                    count += m
                    epoch_microbatches += 1

                    del xi, Sw, p11, ai, at, S_pred, residual, parts, scaled_total

                accumulated = parameter_gradient_summary(model)
                if not accumulated["gradients_finite"]:
                    raise RuntimeError(f"Epoch {epoch}: accumulated parameter gradients are nonfinite.")
                if accumulated["nonzero_gradient_tensor_count"] <= 0:
                    raise RuntimeError(f"Epoch {epoch}: accumulated parameter gradients are all zero.")

                optimizer.step()
                sync_cuda()
                optimizer_steps_completed += 1
                epoch_optimizer_steps += 1

                if not all_model_parameters_finite(model):
                    raise RuntimeError(f"Epoch {epoch}: model parameters became nonfinite after optimizer step.")
                optimizer.zero_grad(set_to_none=True)

            sync_cuda()
            if count != N_TRAIN:
                raise RuntimeError(f"Epoch {epoch}: accepted {count} profiles; expected {N_TRAIN}.")
            if epoch_microbatches != EXPECTED_MICROBATCHES_PER_EPOCH:
                raise RuntimeError(f"Epoch {epoch}: executed {epoch_microbatches} microbatches; expected {EXPECTED_MICROBATCHES_PER_EPOCH}.")
            if epoch_optimizer_steps != EXPECTED_OPTIMIZER_STEPS_PER_EPOCH:
                raise RuntimeError(f"Epoch {epoch}: executed {epoch_optimizer_steps} optimizer steps; expected {EXPECTED_OPTIMIZER_STEPS_PER_EPOCH}.")
            expected_steps = epoch * EXPECTED_OPTIMIZER_STEPS_PER_EPOCH
            if optimizer_steps_completed != expected_steps:
                raise RuntimeError(f"Epoch {epoch}: cumulative optimizer steps {optimizer_steps_completed}; expected {expected_steps}.")

            sec = time.time() - epoch_t0
            n = max(count, 1)
            history["epoch"].append(epoch)
            for k in sums:
                history[k].append(sums[k] / n)
            history["epoch_seconds"].append(float(sec))
            history["optimizer_steps_completed"].append(int(optimizer_steps_completed))

            print(
                f"[COMP-CUDA-005] Epoch {epoch:04d}/{TARGET_EPOCHS} "
                f"| Data {history['data'][-1]:.3e} | Phys {history['physics'][-1]:.3e} "
                f"| BC {history['bc_inj'][-1]:.3e} | Tip {history['bc_tip'][-1]:.3e} "
                f"| Anchor {history['anchor'][-1]:.3e} | Mono {history['mono'][-1]:.3e} "
                f"| Total {history['total'][-1]:.3e} | {sec/60.0:.2f} min/epoch "
                f"| steps {optimizer_steps_completed}/{EXPECTED_TARGET_OPTIMIZER_STEPS} "
                f"| session {(time.time()-session_t0)/3600.0:.2f} h"
            )

            save_recovery_checkpoint(B2S, runner_sha, model, optimizer, history, epoch, optimizer_steps_completed, train_idx, holdout_idx)

    finally:
        B2S.local_recurrent_derivatives_create_graph = original_engine

    return history, train_idx, holdout_idx, optimizer_steps_completed


# =============================================================================
# Development evaluation
# =============================================================================

def evaluate_development(M, model, arrays, holdout_idx, device):
    model.eval()
    if model.training:
        raise RuntimeError("model.eval() did not place model in evaluation mode.")

    print("\nSOURCE-NATIVE DEVELOPMENT-DIAGNOSTIC HOLDOUT")
    holdout = M.holdout_metrics(model, arrays, holdout_idx, device)
    print(f"  MSE     : {holdout['mse']:.12e}")
    print(f"  RMSE    : {holdout['rmse']:.12e}")
    print(f"  MAE     : {holdout['mae']:.12e}")
    print(f"  Max |e| : {holdout['max_abs_error']:.12e}")
    print("  Bounds  :", "PASS" if holdout["bounds_pass"] else "FAIL")

    p1 = M.make_case(no=2.0, nw=2.0, swc=0.20, sor=0.20, mu_w=0.5, mu_o=0.7, phi=0.20)
    p2 = M.make_case(no=3.0, nw=2.0, swc=0.15, sor=0.25, mu_w=6.0, mu_o=0.9, phi=0.25)
    cases = {
        "case1_nc0_stage1_nesting": M.evaluate_case(model, p1, 0.0, device),
        "case1_nc01": M.evaluate_case(model, p1, 0.10, device),
        "case2_nc0_stage1_nesting": M.evaluate_case(model, p2, 0.0, device),
        "case2_nc02": M.evaluate_case(model, p2, 0.20, device),
    }
    print("\nSOURCE CASE DIAGNOSTICS")
    for name, case in cases.items():
        print(f"  {name:<30} R2={case['diagnostics']['r_squared']:.8f} max_res={case['diagnostics']['max_abs_residual']:.5e}")

    print("\nNc ACCURACY SWEEP — CASE 1")
    sweep = M.nc_accuracy_sweep(model, p1, device)
    for nc, vals in sweep.items():
        print(f"  Nc={nc} MAE={vals['mae']:.5e} max={vals['max_abs_error']:.5e}")

    model.train()
    if not model.training:
        raise RuntimeError("Model did not return to train() after evaluation.")
    return holdout, cases, sweep


def case_finite(case):
    return (
        len(case["rows"]) == 15
        and all(finite(r["mse"]) and finite(r["mae"]) and finite(r["max_abs_err"]) for r in case["rows"])
        and finite(case["diagnostics"]["r_squared"])
        and finite(case["diagnostics"]["max_abs_residual"])
    )


# =============================================================================
# Failure artifact
# =============================================================================

def write_failure(exc, runner_sha, latest_safe_epoch, latest_safe_sha, optimizer_steps_completed):
    payload = {
        "milestone": MILESTONE,
        "experiment_id": EXPERIMENT_ID,
        "classification": "PRODUCTION_RUN_FAILURE_FAIL_CLOSED",
        "runner_sha256": runner_sha,
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "traceback": traceback.format_exc(),
        "latest_safe_completed_epoch": latest_safe_epoch,
        "latest_safe_checkpoint_sha256": latest_safe_sha,
        "optimizer_steps_completed_in_process": optimizer_steps_completed,
        "partial_epoch_accepted": False,
        "COMP_CUDA_005_complete": False,
        "B3_authorized": False,
        "OOD_used": False,
        "TOF_used": False,
        "rerun_instruction": "Rerun this exact CUDA6 runner after restoring the same Git commit and CUDA5 authority. Only the latest exact completed-epoch CUDA6 checkpoint may resume.",
    }
    atomic_json_write(payload, FAILURE)
    return sha256(FAILURE)


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 100)
    print("PAD-Stream V16E-1B2CUDA6-A100")
    print("Authorized COMP-CUDA-005 Fresh Corrected Stage-2 Production Runner")
    print("=" * 100)
    print("Experiment:", EXPERIMENT_ID)
    print("B3 remains blocked until post-training Stage-2 scientific closure.\n")

    if SUMMARY.exists():
        raise RuntimeError("Completed COMP-CUDA-005 summary exists; refusing overwrite/retraining.")

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable for authorized COMP-CUDA-005 run.")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False

    # Re-materialize immutable hot inputs if Colab runtime storage was reset.
    ensure_runtime_copy(DATASET, DATASET_DRIVE, DATASET_SHA, "Stage-2 dataset")
    ensure_runtime_copy(COMP004_CHECKPOINT, COMP004_DRIVE, COMP004_CHECKPOINT_SHA, "COMP-XPU-004 provenance fixture")

    runner_path = Path(__file__).resolve()
    runner_sha = sha256(runner_path)

    gates = authority_gates()
    print("AUTHORITY / PRODUCTION-RUN GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)
    if not all(gates.values()):
        raise RuntimeError("CUDA6 blocked by final authorization mismatch: " + ", ".join(k for k, v in gates.items() if not v))

    B2S = import_module(B2S_SOURCE, "v16e1b2s_exact_cuda6")
    CUDA3 = import_module(CUDA3_SOURCE, "v16e1b2cuda3_engine_cuda6")

    if not exact(B2S.BASE_RUNNER, B2S.BASE_RUNNER_SHA):
        raise RuntimeError("B2S-bound Stage-2 base-runner SHA mismatch.")
    if not exact(B2S.B2J_SOURCE, B2S.B2J_SOURCE_SHA):
        raise RuntimeError("B2S-bound eta-model source SHA mismatch.")

    d = np.load(DATASET)
    required = {"xi", "Sw", "p11", "tD", "ai", "at"}
    missing = required - set(d.files)
    if missing:
        raise RuntimeError(f"Frozen dataset missing arrays: {sorted(missing)}")
    arrays = (d["xi"], d["Sw"], d["p11"], d["tD"], d["ai"], d["at"])
    if len(arrays[0]) != N_TOTAL:
        raise RuntimeError(f"Frozen dataset profile count {len(arrays[0])}; expected {N_TOTAL}.")

    device = torch.device("cuda")
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)

    M, J, model, optimizer = build_fresh_model_optimizer(B2S, device, "production")
    if {p.device.type for p in model.parameters()} != {"cuda"}:
        raise RuntimeError("Production model is not entirely on CUDA.")

    fresh_state = cpu_clone(model.state_dict())
    comp004_payload = torch.load(COMP004_CHECKPOINT, map_location="cpu", weights_only=False)
    if exact_tree_equal(fresh_state, cpu_clone(comp004_payload["model_state_dict"])):
        raise RuntimeError("Fresh COMP-CUDA-005 model unexpectedly equals trained COMP-XPU-004 state.")

    # Scratch artifacts are read only as negative identity evidence; never loaded into model.
    for label, p, expected in [
        ("CUDA2RR", CUDA2RR_SCRATCH, CUDA2RR_SCRATCH_SHA),
        ("CUDA4R", CUDA4R_SCRATCH, CUDA4R_SCRATCH_SHA),
    ]:
        if not exact(p, expected):
            raise RuntimeError(f"{label} scratch provenance SHA mismatch.")
        payload = torch.load(p, map_location="cpu", weights_only=False)
        scratch_state = payload.get("model_state_dict") or payload.get("model_state")
        if scratch_state is not None and exact_tree_equal(fresh_state, cpu_clone(scratch_state)):
            raise RuntimeError(f"Fresh COMP-CUDA-005 model unexpectedly equals prohibited {label} scratch state.")

    config_payload = expected_config(runner_sha, B2S)
    config_text = json.dumps(jsonable(config_payload), indent=2)
    if CONFIG.exists():
        if CONFIG.read_text(encoding="utf-8") != config_text:
            raise RuntimeError("Existing COMP-CUDA-005 config differs from this authorized runner.")
    else:
        atomic_text_write(config_text, CONFIG)
    config_sha = sha256(CONFIG)

    print("\nPRODUCTION CONFIG")
    print("  runner SHA-256        :", runner_sha)
    print("  config SHA-256        :", config_sha)
    print("  derivative engine     :", ADOPTED_ENGINE)
    print("  VJP chunk             :", ADOPTED_CHUNK)
    print("  microbatch            :", MICROBATCH)
    print("  logical batch         :", LOGICAL_BATCH)
    print("  epochs                :", TARGET_EPOCHS)
    print("  optimizer             : Adam(lr=1e-3, foreach=False)")

    latest_safe_epoch = None
    latest_safe_sha = None
    optimizer_steps_in_process = 0

    try:
        history, train_idx, holdout_idx, optimizer_steps_completed = train_or_resume(
            B2S, CUDA3, M, model, optimizer, arrays, device, runner_sha
        )
        optimizer_steps_in_process = optimizer_steps_completed

        if RECOVERY_LATEST.exists():
            latest = read_json(RECOVERY_LATEST)
            latest_safe_epoch = latest.get("completed_epoch")
            latest_safe_sha = latest.get("checkpoint_sha256")

        training_gates = {
            "full_800_epochs_completed": len(history["epoch"]) == TARGET_EPOCHS,
            "history_last_epoch_800": history["epoch"][-1] == TARGET_EPOCHS,
            "optimizer_steps_1600": optimizer_steps_completed == EXPECTED_TARGET_OPTIMIZER_STEPS,
            "history_last_optimizer_step_1600": history["optimizer_steps_completed"][-1] == EXPECTED_TARGET_OPTIMIZER_STEPS,
            "final_model_parameters_finite": all_model_parameters_finite(model),
            "latest_recovery_exists": RECOVERY_LATEST.exists(),
            "config_SHA_still_exact": sha256(CONFIG) == config_sha,
            "COMP004_checkpoint_still_unchanged": sha256(COMP004_CHECKPOINT) == COMP004_CHECKPOINT_SHA,
            "CUDA2RR_scratch_still_unchanged": sha256(CUDA2RR_SCRATCH) == CUDA2RR_SCRATCH_SHA,
            "CUDA4R_scratch_still_unchanged": sha256(CUDA4R_SCRATCH) == CUDA4R_SCRATCH_SHA,
            "no_OOD": True,
            "no_TOF": True,
        }
        if not all(training_gates.values()):
            raise RuntimeError("COMP-CUDA-005 training completion gate failure: " + ", ".join(k for k, v in training_gates.items() if not v))

        atomic_json_write(history, HISTORY)

        final_checkpoint_payload = {
            "experiment_id": EXPERIMENT_ID,
            "milestone": MILESTONE,
            "runner_sha256": runner_sha,
            "framework": "PyTorch CUDA",
            "pytorch_version": torch.__version__,
            "device": torch.cuda.get_device_name(0),
            "fresh_initialization": True,
            "seed": SEED,
            "sequence_features": ["xi", "eta"],
            "conditioning": list(getattr(M, "CONDITIONING", [])),
            "param_dim": int(getattr(M, "PARAM_DIM", 11)),
            "hidden": int(M.HIDDEN),
            "layers": int(M.LAYERS),
            "derivative_engine": ADOPTED_ENGINE,
            "cotangent_chunk_size": ADOPTED_CHUNK,
            "microbatch": MICROBATCH,
            "logical_batch": LOGICAL_BATCH,
            "epochs_completed": TARGET_EPOCHS,
            "optimizer_steps_completed": optimizer_steps_completed,
            "CUDA5_authorization_sha256": CUDA5_AUTHORIZATION_SHA,
            "CUDA5_accumulation_sha256": CUDA5_ACCUMULATION_SHA,
            "CUDA5_resume_sha256": CUDA5_RESUME_SHA,
            "CUDA5_runner_contract_sha256": CUDA5_RUNNER_CONTRACT_SHA,
            "CUDA5_summary_sha256": CUDA5_SUMMARY_SHA,
            "dataset_sha256": DATASET_SHA,
            "source_sha256_map": source_sha_map(runner_sha, B2S),
            "model_state_dict": cpu_clone(model.state_dict()),
            "OOD_used": False,
            "TOF_used": False,
        }
        atomic_torch_save(final_checkpoint_payload, CHECKPOINT)
        history_sha = sha256(HISTORY)
        checkpoint_sha = sha256(CHECKPOINT)

        holdout, cases, sweep = evaluate_development(M, model, arrays, holdout_idx, device)
        eval_gates = {
            "model_returned_to_train_after_eval": model.training is True,
            "holdout_predictions_finite": holdout["finite_predictions"],
            "holdout_bounds_pass": holdout["bounds_pass"],
            "holdout_metrics_finite": all(finite(holdout[k]) for k in ("mse", "rmse", "mae", "max_abs_error")),
            "all_four_source_cases_finite": all(case_finite(c) for c in cases.values()),
            "Nc_sweep_all_finite": all(finite(vals["mae"]) and finite(vals["max_abs_error"]) for vals in sweep.values()),
            "no_OOD": True,
            "no_TOF": True,
        }
        if not all(eval_gates.values()):
            raise RuntimeError("COMP-CUDA-005 evaluation gate failure: " + ", ".join(k for k, v in eval_gates.items() if not v))

        metrics_payload = {
            "experiment_id": EXPERIMENT_ID,
            "milestone": MILESTONE,
            "classification": "SOURCE_NATIVE_DEVELOPMENT_DIAGNOSTIC_NOT_OOD",
            "holdout": holdout,
            "source_cases": cases,
            "Nc_accuracy_sweep_case1": sweep,
            "OOD_used": False,
            "TOF_used": False,
        }
        atomic_json_write(metrics_payload, METRICS)
        metrics_sha = sha256(METRICS)

        manifest_payload = {
            "milestone": MILESTONE,
            "experiment_id": EXPERIMENT_ID,
            "classification": "COMP_CUDA_005_COMPLETED_PRODUCTION_MANIFEST",
            "runner_sha256": runner_sha,
            "config_sha256": config_sha,
            "history_sha256": history_sha,
            "checkpoint_sha256": checkpoint_sha,
            "metrics_sha256": metrics_sha,
            "CUDA5_authorization_sha256": CUDA5_AUTHORIZATION_SHA,
            "CUDA5_runner_contract_sha256": CUDA5_RUNNER_CONTRACT_SHA,
            "CUDA5_summary_sha256": CUDA5_SUMMARY_SHA,
            "dataset_sha256": DATASET_SHA,
            "completed_epoch": TARGET_EPOCHS,
            "optimizer_steps_completed": optimizer_steps_completed,
            "fresh_initialization": True,
            "OOD_used": False,
            "TOF_used": False,
            "B3_authorized": False,
            "next": "Stage-2 scientific closure/comparison before B3",
        }
        atomic_json_write(manifest_payload, MANIFEST)
        manifest_sha = sha256(MANIFEST)

        final_gates = {
            **training_gates,
            **eval_gates,
            "checkpoint_written": CHECKPOINT.exists() and CHECKPOINT.stat().st_size > 0,
            "history_written": HISTORY.exists() and HISTORY.stat().st_size > 0,
            "metrics_written": METRICS.exists() and METRICS.stat().st_size > 0,
            "manifest_written": MANIFEST.exists() and MANIFEST.stat().st_size > 0,
            "checkpoint_hash_finite": len(checkpoint_sha) == 64,
            "history_hash_finite": len(history_sha) == 64,
            "metrics_hash_finite": len(metrics_sha) == 64,
            "manifest_hash_finite": len(manifest_sha) == 64,
            "B3_not_authorized": True,
        }
        if not all(final_gates.values()):
            raise RuntimeError("COMP-CUDA-005 final gate failure: " + ", ".join(k for k, v in final_gates.items() if not v))

        status = (
            "V16E1B2CUDA6_A100_COMP_CUDA_005_AUTHORIZED_PRODUCTION_RUN_COMPLETE_"
            "CUDA5_FINAL_AUTHORIZATION_BOUND_FRESH_SEED_1337_MB1024_CHUNK64_LOGICAL8192_"
            "TWELVE_MICROBATCHES_TWO_OPTIMIZER_STEPS_PER_EPOCH_800_EPOCHS_1600_STEPS_COMPLETE_"
            "NATIVE_CUDA_RNN_HIGHER_ORDER_AUTOGRAD_TF32_OFF_AMP_OFF_"
            "ATOMIC_COMPLETED_EPOCH_RESUME_CONTRACT_SATISFIED_"
            "FINAL_MODEL_AND_DEVELOPMENT_HOLDOUT_FINITE_NO_OOD_NO_TOF_"
            "STAGE2_SCIENTIFIC_CLOSURE_REQUIRED_B3_NOT_AUTHORIZED"
        )
        summary_payload = {
            "milestone": MILESTONE,
            "status": status,
            "experiment_id": EXPERIMENT_ID,
            "runner_sha256": runner_sha,
            "config_sha256": config_sha,
            "history_sha256": history_sha,
            "checkpoint_sha256": checkpoint_sha,
            "metrics_sha256": metrics_sha,
            "manifest_sha256": manifest_sha,
            "completed_epoch": TARGET_EPOCHS,
            "optimizer_steps_completed": optimizer_steps_completed,
            "final_holdout_mse": holdout["mse"],
            "final_holdout_rmse": holdout["rmse"],
            "final_holdout_mae": holdout["mae"],
            "final_holdout_max_abs_error": holdout["max_abs_error"],
            "holdout_bounds_pass": holdout["bounds_pass"],
            "OOD_used": False,
            "TOF_used": False,
            "COMP005_CUDA_training_complete": True,
            "B3_authorized": False,
            "next_milestone": "Stage-2 scientific closure/comparison before B3",
            "gates": {k: bool(v) for k, v in final_gates.items()},
        }
        atomic_json_write(summary_payload, SUMMARY)

        print("\nFINAL STATUS")
        print(" ", status)
        print("\nHASHES")
        print("  CUDA6 Runner :", runner_sha)
        print("  Config       :", config_sha)
        print("  History      :", history_sha)
        print("  Checkpoint   :", checkpoint_sha)
        print("  Metrics      :", metrics_sha)
        print("  Manifest     :", manifest_sha)
        print("  Summary      :", sha256(SUMMARY))
        print("\nNEXT")
        print("  Stage-2 scientific closure/comparison before B3. B3 remains NOT AUTHORIZED.")

    except Exception as exc:
        if RECOVERY_LATEST.exists():
            try:
                latest = read_json(RECOVERY_LATEST)
                latest_safe_epoch = latest.get("completed_epoch")
                latest_safe_sha = latest.get("checkpoint_sha256")
            except Exception:
                pass
        failure_sha = write_failure(exc, runner_sha, latest_safe_epoch, latest_safe_sha, optimizer_steps_in_process)
        print("\nFAIL-CLOSED")
        print("  latest safe completed epoch :", latest_safe_epoch)
        print("  latest safe checkpoint SHA  :", latest_safe_sha)
        print("  failure artifact SHA        :", failure_sha)
        print("  rerun this exact CUDA6 command to resume only from the latest valid completed epoch.")
        raise


if __name__ == "__main__":
    main()
