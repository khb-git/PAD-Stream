#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2CUDA4R-A100
CUDA3 K64 Engine Repair + Full 8192-Profile Logical-Batch Rehearsal

Purpose
-------
Adopt the CUDA3-selected A100 execution geometry only after reproducing the
certified CUDA2RR full-logical-batch computation at production scale.

Selected geometry authorized by CUDA3:
    microbatch = 1024
    batched-VJP cotangent chunk = 64
    logical batch = 8192
    microbatches = 8

This milestone:
    * uses the exact first 8192 epoch-1 training profiles
    * constructs a fresh seed-1337 model
    * NEVER loads COMP-XPU-004 as an initializer
    * accumulates one full logical-batch gradient with MB=1024, K=64
    * requires loss and EVERY parameter-gradient tensor to be equivalent to
      the certified CUDA2RR MB=128, K=16 baseline
    * reconstructs the CUDA2RR baseline gradient exactly from the first-step
      Adam exp_avg state in its frozen scratch checkpoint
    * performs exactly one Adam(lr=1e-3, foreach=False) step only after
      full-batch equivalence passes
    * writes/reloads a NON-PRODUCTION scratch checkpoint and verifies model,
      optimizer, and RNG restoration

CUDA2RR, CUDA3, and the failed CUDA4 source remain immutable authorities.
CUDA4R repairs only the engine-construction path.  The failed CUDA4 called the
older frozen B2AC factory, whose historical allow-list rejects K=64.  CUDA4R
instead imports the exact SHA-bound CUDA3 source and calls CUDA3's already
certified make_cuda3_chunked_batched_engine(64) factory directly.  B2AC remains
unchanged and frozen.

CUDA4R scratch weights MUST NEVER seed or resume COMP-005.

No OOD. No TOF. No B3.
Full COMP-005 CUDA training remains unauthorized in CUDA4R; a successful
CUDA4R only authorizes a final production-training authorization freeze (CUDA5).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import importlib.util
import json
import math
import os
import random
import subprocess
import time
import traceback

import numpy as np
import torch


# =============================================================================
# Milestone constants
# =============================================================================

R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2CUDA4R-A100"
EXPERIMENT_ID = "V16E-BLREP-COMP-CUDA-005-SELECTED-GEOMETRY-SCRATCH"
SEED = 1337
N_TOTAL = 14400
N_TRAIN = 11520
LOGICAL_BATCH = 8192
SELECTED_MICROBATCH = 1024
SELECTED_CHUNK = 64
SELECTED_MICROBATCHES = 8
LR = 1.0e-3
FLOAT32_EPS = float(np.finfo(np.float32).eps)
IDENTITY_EPS_MULTIPLIER = 1024.0

RUNTIME_ROOT = Path("/content/PAD_Stream_Runtime")
DRIVE_ROOT = Path("/content/drive/MyDrive/PAD_Stream_Compute")

DATASET = RUNTIME_ROOT / "datasets" / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"
COMP004_CHECKPOINT = RUNTIME_ROOT / "xpu_reference" / "V16E_BLREP_COMP_XPU_004.pt"
COMP004_CHECKPOINT_SHA = "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69"

B2S_SOURCE = R / "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
B2S_SOURCE_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"
B2AC_SOURCE = R / "PAD_Stream_V16E1B2AC_XPU_Chunked_Batched_VJP_Equivalence_Performance_Sweep.py"
B2AC_SOURCE_SHA = "59f7ea7b0dc2e901f5a42649691c2dab5f4dfc5d399f953eaab5ba773040cd53"

CUDA4_FAILED_SOURCE = R / "PAD_Stream_V16E1B2CUDA4_A100_Selected_Geometry_Full_Logical_Batch_Rehearsal.py"
CUDA4_FAILED_SOURCE_SHA = "2b1c2d347cee38479dfd56f78caaea442737c1217306494bde0b0ee6f907c3fa"

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
CUDA2RR_SCRATCH = CUDA2RR_DIR / "V16E1B2CUDA2RR_SCRATCH_ONE_LOGICAL_BATCH.pt"
CUDA2RR_SCRATCH_SHA = "3e86248597a85b5880794f7b219726e072aadd8a5fe5dd72d03132ef1d00d014"

EXPECTED_CUDA2RR_STATUS = (
    "V16E1B2CUDA2RR_A100_FINAL_CROSS_PLATFORM_TEXT_AUTHORITY_REPAIR_REHEARSAL_PASS_"
    "CUDA1R_NATIVE_CUDA_RNN_EQUIVALENCE_AUTHORITY_BOUND_FROZEN_WINDOWS_TEXT_SHA_REPRODUCED_BY_EXACT_CRLF_RECONSTRUCTION_"
    "FRESH_SEED_1337_MODEL_CONFIRMED_NOT_COMP_XPU_004_INITIALIZER_"
    "EXACT_EPOCH1_PRODUCTION_ORDER_FIRST_8192_TRAINING_PROFILES_USED_"
    "CHUNKED_BATCHED_VJP_CHUNK_16_MICROBATCH_128_SIXTY_FOUR_PROFILE_WEIGHTED_BACKWARD_CALLS_COMPLETE_"
    "FINITE_NONZERO_ACCUMULATED_GRADIENTS_AND_EXACTLY_ONE_ADAM_LR_1E_3_FOREACH_FALSE_STEP_COMPLETE_"
    "POST_STEP_PARAMETERS_FINITE_ATOMIC_NONPRODUCTION_SCRATCH_CHECKPOINT_WRITTEN_"
    "MODEL_OPTIMIZER_AND_PYTHON_NUMPY_TORCH_CPU_CUDA_RNG_STATE_RELOAD_VERIFIED_EXACT_"
    "COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_SCRATCH_WEIGHTS_PROHIBITED_AS_COMP005_RESUME_SOURCE_"
    "A100_PERFORMANCE_SWEEP_AUTHORIZED_COMP005_CUDA_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
)

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
EXPECTED_CUDA3_STATUS = (
    "V16E1B2CUDA3_A100_MICROBATCH_BATCHED_VJP_PERFORMANCE_SWEEP_PASS_"
    "CUDA2RR_AUTHORITY_BOUND_FRESH_SEED_1337_FIXED_FIRST_2048_EPOCH1_TRAINING_PROFILES_"
    "NO_TRAINING_NO_OPTIMIZER_STEP_NO_WEIGHT_UPDATE_NATIVE_CUDA_RNN_HIGHER_ORDER_AUTOGRAD_"
    "ALL_ELIGIBLE_CANDIDATES_REQUIRED_FLOAT32_EPSILON_DERIVED_LOSS_AND_PARAMETER_GRADIENT_EQUIVALENCE_"
    "SELECTED_MICROBATCH_1024_CHUNK_64_"
    "SELECTED_CANDIDATE_FASTER_THAN_MB128_K16_BASELINE_"
    "CUDA4_FULL_8192_PROFILE_SELECTED_GEOMETRY_REHEARSAL_AUTHORIZED_"
    "COMP005_CUDA_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
)

OUT = (
    DRIVE_ROOT / "provenance" / "cuda_rehearsal"
    / "V16E1B2CUDA4R_A100_CUDA3_K64_ENGINE_REPAIR_FULL_LOGICAL_BATCH_REHEARSAL"
)
OUT.mkdir(parents=True, exist_ok=True)
RESULTS = OUT / "V16E1B2CUDA4R_A100_CUDA3_K64_Engine_Repair_Full_Logical_Batch_Results.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2CUDA4R_A100_Summary.json"
FAILURE = OUT / "V16E1B2CUDA4R_A100_CUDA3_K64_Engine_Repair_Failure.json"
SCRATCH_CHECKPOINT = OUT / "V16E1B2CUDA4R_SCRATCH_ONE_LOGICAL_BATCH.pt"
SELECTED_GRADS = OUT / "V16E1B2CUDA4R_MB1024_K64_Full8192_Gradients.pt"


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


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json_write(payload: Any, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def atomic_torch_save(payload: Any, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, tmp)
    os.replace(tmp, path)


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def sync_cuda() -> None:
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def model_state_cpu(model) -> dict[str, torch.Tensor]:
    return {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}


def gradient_state_cpu(model) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, p in model.named_parameters():
        out[name] = None if p.grad is None else p.grad.detach().cpu().clone()
    return out


def gradient_summary(grads: dict[str, Any]) -> dict[str, Any]:
    finite = True
    nonzero = False
    sq = 0.0
    tensors = 0
    for g in grads.values():
        if g is None:
            continue
        tensors += 1
        finite = finite and bool(torch.isfinite(g).all().item())
        nonzero = nonzero or bool(torch.any(g != 0).item())
        sq += float(torch.sum(g.double() * g.double()).item())
    return {
        "finite": bool(finite),
        "nonzero": bool(nonzero),
        "gradient_tensor_count": int(tensors),
        "global_l2_norm": float(math.sqrt(max(sq, 0.0))),
    }


def identity_bound(a_max: float, b_max: float) -> float:
    return IDENTITY_EPS_MULTIPLIER * FLOAT32_EPS * max(1.0, a_max, b_max)


def compare_scalar(ref: float, cand: float) -> dict[str, Any]:
    bound = identity_bound(abs(ref), abs(cand))
    diff = abs(ref - cand)
    return {"pass": bool(math.isfinite(diff) and diff <= bound), "abs_diff": float(diff), "bound": float(bound)}


def compare_gradient_dict(ref: dict[str, Any], cand: dict[str, Any]) -> dict[str, Any]:
    details: dict[str, Any] = {}
    if ref.keys() != cand.keys():
        return {"pass": False, "reason": "gradient key mismatch", "details": {}}
    overall = True
    for name in ref:
        a, b = ref[name], cand[name]
        if a is None or b is None:
            ok = a is None and b is None
            details[name] = {"pass": ok, "none_match": ok}
            overall = overall and ok
            continue
        if tuple(a.shape) != tuple(b.shape):
            details[name] = {"pass": False, "shape_ref": list(a.shape), "shape_cand": list(b.shape)}
            overall = False
            continue
        diff = float(torch.max(torch.abs(a - b)).item()) if a.numel() else 0.0
        amax = float(torch.max(torch.abs(a)).item()) if a.numel() else 0.0
        bmax = float(torch.max(torch.abs(b)).item()) if b.numel() else 0.0
        bound = identity_bound(amax, bmax)
        ok = math.isfinite(diff) and diff <= bound
        details[name] = {
            "pass": bool(ok),
            "max_abs_diff": diff,
            "reference_max_abs": amax,
            "candidate_max_abs": bmax,
            "bound": float(bound),
        }
        overall = overall and ok
    return {"pass": bool(overall), "details": details}


def recover_first_adam_gradient(checkpoint: dict[str, Any], model) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recover the exact first-step gradient from Adam exp_avg=(1-beta1)*g."""
    opt = checkpoint["optimizer_state_dict"]
    groups = opt.get("param_groups", [])
    if len(groups) != 1:
        raise RuntimeError(f"Expected one Adam parameter group, got {len(groups)}")
    group = groups[0]
    betas = group.get("betas", (0.9, 0.999))
    beta1 = float(betas[0])
    if not math.isclose(beta1, 0.9, rel_tol=0.0, abs_tol=0.0):
        raise RuntimeError(f"Unexpected Adam beta1={beta1}")
    if float(group.get("weight_decay", 0.0)) != 0.0:
        raise RuntimeError("Baseline Adam weight_decay is not zero; exp_avg inversion would not be the raw gradient")
    if bool(group.get("maximize", False)):
        raise RuntimeError("Baseline Adam maximize=True is unsupported for gradient recovery")

    ids = list(group.get("params", []))
    names = [name for name, _ in model.named_parameters()]
    if len(ids) != len(names):
        raise RuntimeError(f"Optimizer/model parameter-count mismatch: {len(ids)} vs {len(names)}")

    state = opt.get("state", {})
    grads: dict[str, Any] = {}
    steps: dict[str, int] = {}
    denom = 1.0 - beta1
    for name, pid in zip(names, ids):
        entry = state.get(pid)
        if entry is None and str(pid) in state:
            entry = state[str(pid)]
        if entry is None:
            raise RuntimeError(f"Missing Adam state for parameter {name} / id {pid}")
        step_obj = entry.get("step")
        step = int(step_obj.item()) if torch.is_tensor(step_obj) else int(step_obj)
        steps[name] = step
        if step != 1:
            raise RuntimeError(f"Expected Adam step=1 for {name}, got {step}")
        exp_avg = entry.get("exp_avg")
        if exp_avg is None:
            raise RuntimeError(f"Missing Adam exp_avg for {name}")
        grads[name] = exp_avg.detach().cpu().clone() / denom

    return grads, {
        "beta1": beta1,
        "all_steps_one": all(v == 1 for v in steps.values()),
        "parameter_steps": steps,
        "derivation": "gradient = exp_avg / (1 - beta1) after the first Adam step from zero optimizer state",
    }


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    print("=" * 100)
    print("PAD-Stream V16E-1B2CUDA4R-A100")
    print("Selected Geometry Full 8192-Profile Logical-Batch Rehearsal")
    print("=" * 100)
    print("SCRATCH ONLY — MB=1024, K=64 — ONE ADAM STEP — NEVER A COMP-005 RESUME SOURCE.\n")

    if SUMMARY.exists():
        raise RuntimeError("CUDA4R summary already exists; refusing overwrite.")
    for p in [RESULTS, FAILURE, SCRATCH_CHECKPOINT, SELECTED_GRADS]:
        if p.exists():
            p.unlink()

    git_clean = run_git(R, "status", "--porcelain") == ""
    if not git_clean:
        raise RuntimeError("Git working tree is not clean.")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable for CUDA4R.")
    gpu_name = torch.cuda.get_device_name(0)
    if "A100" not in gpu_name.upper():
        raise RuntimeError(f"CUDA4R requires an A100-class runtime; got {gpu_name!r}")

    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")

    c2rr_summary = read_json(CUDA2RR_SUMMARY) if CUDA2RR_SUMMARY.exists() else {}
    c2rr_results = read_json(CUDA2RR_RESULTS) if CUDA2RR_RESULTS.exists() else {}
    c3_summary = read_json(CUDA3_SUMMARY) if CUDA3_SUMMARY.exists() else {}
    c3_results = read_json(CUDA3_RESULTS) if CUDA3_RESULTS.exists() else {}

    gates: dict[str, bool] = {
        "git_working_tree_clean": git_clean,
        "CUDA_available": torch.cuda.is_available(),
        "A100_runtime": "A100" in gpu_name.upper(),
        "TF32_matmul_disabled": torch.backends.cuda.matmul.allow_tf32 is False,
        "TF32_cudnn_disabled": torch.backends.cudnn.allow_tf32 is False,
        "dataset_SHA_exact": exact(DATASET, DATASET_SHA),
        "COMP004_checkpoint_SHA_exact": exact(COMP004_CHECKPOINT, COMP004_CHECKPOINT_SHA),
        "B2S_source_SHA_exact": exact(B2S_SOURCE, B2S_SOURCE_SHA),
        "B2AC_source_SHA_exact": exact(B2AC_SOURCE, B2AC_SOURCE_SHA),
        "CUDA4_failed_source_SHA_exact": exact(CUDA4_FAILED_SOURCE, CUDA4_FAILED_SOURCE_SHA),
        "CUDA2RR_source_SHA_exact": exact(CUDA2RR_SOURCE, CUDA2RR_SOURCE_SHA),
        "CUDA2RR_results_SHA_exact": exact(CUDA2RR_RESULTS, CUDA2RR_RESULTS_SHA),
        "CUDA2RR_summary_SHA_exact": exact(CUDA2RR_SUMMARY, CUDA2RR_SUMMARY_SHA),
        "CUDA2RR_scratch_SHA_exact": exact(CUDA2RR_SCRATCH, CUDA2RR_SCRATCH_SHA),
        "CUDA3_source_SHA_exact": exact(CUDA3_SOURCE, CUDA3_SOURCE_SHA),
        "CUDA3_results_SHA_exact": exact(CUDA3_RESULTS, CUDA3_RESULTS_SHA),
        "CUDA3_summary_SHA_exact": exact(CUDA3_SUMMARY, CUDA3_SUMMARY_SHA),
        "CUDA2RR_status_exact": c2rr_summary.get("status") == EXPECTED_CUDA2RR_STATUS,
        "CUDA2RR_sweep_authorized": c2rr_summary.get("CUDA3_A100_performance_sweep_authorized") is True,
        "CUDA2RR_training_false": c2rr_summary.get("COMP005_CUDA_full_training_authorized") is False,
        "CUDA2RR_B3_false": c2rr_summary.get("B3_authorized") is False,
        "CUDA3_status_exact": c3_summary.get("status") == EXPECTED_CUDA3_STATUS,
        "CUDA3_selected_microbatch_1024": c3_summary.get("selected_microbatch") == SELECTED_MICROBATCH,
        "CUDA3_selected_chunk_64": c3_summary.get("selected_chunk") == SELECTED_CHUNK,
        "CUDA3_CUDA4_authorized": c3_summary.get("CUDA4_full_8192_selected_geometry_rehearsal_authorized") is True,
        "CUDA3_training_false": c3_summary.get("COMP005_CUDA_full_training_authorized") is False,
        "CUDA3_B3_false": c3_summary.get("B3_authorized") is False,
        "CUDA3_results_selected_microbatch_1024": c3_results.get("selected", {}).get("microbatch") == SELECTED_MICROBATCH,
        "CUDA3_results_selected_chunk_64": c3_results.get("selected", {}).get("chunk") == SELECTED_CHUNK,
        "CUDA3_selected_faster_than_baseline": c3_results.get("selected", {}).get("faster_than_baseline") is True,
        "CUDA3_results_CUDA4_authorized": c3_results.get("CUDA4_full_8192_selected_geometry_rehearsal_authorized") is True,
    }

    print("AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)
    if not all(gates.values()):
        raise RuntimeError("CUDA4R blocked by authority gate failure.")

    try:
        C2 = import_module(CUDA2RR_SOURCE, "v16e1b2cuda2rr_authority")
        B2S = import_module(B2S_SOURCE, "v16e1b2s_cuda4r")
        B2AC = import_module(B2AC_SOURCE, "v16e1b2ac_cuda4r")
        C3 = import_module(CUDA3_SOURCE, "v16e1b2cuda3_k64_authority")

        if not exact(B2S.BASE_RUNNER, B2S.BASE_RUNNER_SHA):
            raise RuntimeError("B2S-bound base runner SHA mismatch.")
        if not exact(B2S.B2J_SOURCE, B2S.B2J_SOURCE_SHA):
            raise RuntimeError("B2S-bound B2J eta-model source SHA mismatch.")

        d = np.load(DATASET)
        required = {"xi", "Sw", "p11", "ai", "at"}
        missing = required - set(d.files)
        if missing:
            raise RuntimeError(f"Dataset missing arrays: {sorted(missing)}")
        xi_all, Sw_all, p11_all, ai_all, at_all = (d["xi"], d["Sw"], d["p11"], d["ai"], d["at"])
        if len(xi_all) != N_TOTAL:
            raise RuntimeError(f"Dataset profile count mismatch: {len(xi_all)}")

        train_idx = C2.frozen_train_indices(len(xi_all))
        epoch1_order = C2.production_epoch_order(train_idx, epoch=1)
        logical_idx = epoch1_order[:LOGICAL_BATCH]
        if len(train_idx) != N_TRAIN or len(logical_idx) != LOGICAL_BATCH:
            raise RuntimeError("Frozen training-order geometry mismatch.")
        logical_indices_sha = hashlib.sha256(np.asarray(logical_idx, dtype=np.int64).tobytes()).hexdigest()

        device = torch.device("cuda")
        random.seed(SEED)
        np.random.seed(SEED)
        M, J, model, optimizer = C2.build_fresh_model_and_optimizer(B2S, device, "cuda4_train")
        model.train()

        if {p.device.type for p in model.parameters()} != {"cuda"}:
            raise RuntimeError("Fresh CUDA4R model is not entirely on CUDA.")

        initial_state = model_state_cpu(model)
        comp004 = torch.load(COMP004_CHECKPOINT, map_location="cpu", weights_only=False)
        comp004_state = C2.tensor_tree_to_cpu(comp004["model_state_dict"])
        fresh_initial_equals_COMP004 = C2.exact_tree_equal(initial_state, comp004_state)
        if fresh_initial_equals_COMP004:
            raise RuntimeError("Fresh CUDA4R initialization unexpectedly equals COMP-XPU-004 checkpoint.")

        # Recover the certified full-batch baseline gradient from CUDA2RR's first Adam step.
        baseline_cp = torch.load(CUDA2RR_SCRATCH, map_location="cpu", weights_only=False)
        baseline_grads, recovery = recover_first_adam_gradient(baseline_cp, model)
        baseline_grad_summary = gradient_summary(baseline_grads)
        if not baseline_grad_summary["finite"] or not baseline_grad_summary["nonzero"]:
            raise RuntimeError("Recovered CUDA2RR baseline gradients are invalid.")

        baseline_losses = c2rr_results.get("logical_batch_mean_losses", {})
        expected_loss_keys = {"data", "physics", "bc_inj", "bc_tip", "anchor", "mono", "total"}
        if set(baseline_losses.keys()) != expected_loss_keys:
            raise RuntimeError(f"CUDA2RR baseline loss keys mismatch: {sorted(baseline_losses.keys())}")

        engine = C3.make_cuda3_chunked_batched_engine(SELECTED_CHUNK)
        original_engine = B2S.local_recurrent_derivatives_create_graph
        B2S.local_recurrent_derivatives_create_graph = engine

        optimizer.zero_grad(set_to_none=True)
        weighted_sums = {k: 0.0 for k in expected_loss_keys}
        microbatch_records: list[dict[str, Any]] = []
        total_profiles = 0

        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        sync_cuda()
        t0 = time.perf_counter()

        try:
            for micro_i, m0 in enumerate(range(0, LOGICAL_BATCH, SELECTED_MICROBATCH), start=1):
                ids = logical_idx[m0:m0 + SELECTED_MICROBATCH]
                m = len(ids)
                if m != SELECTED_MICROBATCH:
                    raise RuntimeError(f"Unexpected CUDA4R microbatch size {m}")

                xi = torch.from_numpy(xi_all[ids]).to(device).detach().clone().requires_grad_(True)
                Sw = torch.from_numpy(Sw_all[ids]).to(device)
                p11 = torch.from_numpy(p11_all[ids]).to(device).detach().clone().requires_grad_(True)
                ai = torch.from_numpy(ai_all[ids]).to(device)
                at = torch.from_numpy(at_all[ids]).to(device)

                mb_t0 = time.perf_counter()
                with torch.backends.cudnn.flags(enabled=False):
                    S_pred, residual, parts = B2S.complete_corrected_total_loss(
                        M, model, xi, Sw, p11, ai, at
                    )

                if not torch.isfinite(S_pred).all().item():
                    raise RuntimeError(f"Microbatch {micro_i}: nonfinite prediction")
                if not torch.isfinite(residual).all().item():
                    raise RuntimeError(f"Microbatch {micro_i}: nonfinite residual")
                if not all(torch.isfinite(v).all().item() for v in parts.values()):
                    raise RuntimeError(f"Microbatch {micro_i}: nonfinite loss")

                scale = float(m) / float(LOGICAL_BATCH)
                scaled_total = parts["total"] * scale
                with torch.backends.cudnn.flags(enabled=False):
                    scaled_total.backward()
                sync_cuda()
                mb_seconds = time.perf_counter() - mb_t0

                for k in weighted_sums:
                    weighted_sums[k] += float(parts[k].detach().cpu()) * m
                total_profiles += m
                microbatch_records.append({
                    "microbatch_index": int(micro_i),
                    "profiles": int(m),
                    "scale": float(scale),
                    "raw_total_loss": float(parts["total"].detach().cpu()),
                    "physics_loss": float(parts["physics"].detach().cpu()),
                    "seconds": float(mb_seconds),
                })
                print(
                    f"  microbatch {micro_i:02d}/{SELECTED_MICROBATCHES}"
                    f" | loss={microbatch_records[-1]['raw_total_loss']:.6e}"
                    f" | physics={microbatch_records[-1]['physics_loss']:.6e}"
                    f" | {mb_seconds:.3f}s"
                )

                del xi, Sw, p11, ai, at, S_pred, residual, parts, scaled_total
        finally:
            B2S.local_recurrent_derivatives_create_graph = original_engine

        sync_cuda()
        logical_seconds = time.perf_counter() - t0
        peak_gib = float(torch.cuda.max_memory_allocated() / (1024.0 ** 3))

        if total_profiles != LOGICAL_BATCH:
            raise RuntimeError(f"CUDA4R accumulated {total_profiles} profiles, expected {LOGICAL_BATCH}")
        if len(microbatch_records) != SELECTED_MICROBATCHES:
            raise RuntimeError(f"CUDA4R executed {len(microbatch_records)} microbatches, expected {SELECTED_MICROBATCHES}")
        if not all(r["profiles"] == SELECTED_MICROBATCH for r in microbatch_records):
            raise RuntimeError("CUDA4R microbatch-size invariant failed")
        expected_scale = SELECTED_MICROBATCH / LOGICAL_BATCH
        if not all(math.isclose(r["scale"], expected_scale, rel_tol=0.0, abs_tol=0.0) for r in microbatch_records):
            raise RuntimeError("CUDA4R profile-weighted accumulation scale invariant failed")

        logical_mean_losses = {k: weighted_sums[k] / float(LOGICAL_BATCH) for k in weighted_sums}
        candidate_grads = gradient_state_cpu(model)
        candidate_grad_summary = gradient_summary(candidate_grads)
        if not candidate_grad_summary["finite"] or not candidate_grad_summary["nonzero"]:
            raise RuntimeError("CUDA4R accumulated gradients are invalid")

        # Full-8192 numerical equivalence against certified CUDA2RR baseline.
        loss_cmp = {k: compare_scalar(float(baseline_losses[k]), float(logical_mean_losses[k])) for k in sorted(expected_loss_keys)}
        grad_cmp = compare_gradient_dict(baseline_grads, candidate_grads)
        norm_cmp = compare_scalar(
            float(baseline_grad_summary["global_l2_norm"]),
            float(candidate_grad_summary["global_l2_norm"]),
        )
        full_equivalence = all(v["pass"] for v in loss_cmp.values()) and grad_cmp["pass"] and norm_cmp["pass"]

        print("\nFULL-8192 EQUIVALENCE")
        print("  loss components equivalent :", all(v["pass"] for v in loss_cmp.values()))
        print("  parameter gradients equiv  :", grad_cmp["pass"])
        print("  gradient norm equivalent    :", norm_cmp["pass"])
        print("  overall                     :", full_equivalence)

        if not full_equivalence:
            raise RuntimeError("Selected MB=1024/K=64 geometry failed full-8192 equivalence against CUDA2RR baseline")

        atomic_torch_save(candidate_grads, SELECTED_GRADS)
        selected_grads_sha = sha256(SELECTED_GRADS)

        # Exactly one optimizer step, only after full-batch equivalence passes.
        pre_step_model_state = model_state_cpu(model)
        optimizer.step()
        sync_cuda()
        post_step_model_state = model_state_cpu(model)
        model_changed = not C2.exact_tree_equal(pre_step_model_state, post_step_model_state)
        if not model_changed:
            raise RuntimeError("Exactly one Adam step completed but no model parameter changed")
        if not C2.all_model_parameters_finite(model):
            raise RuntimeError("Post-step model parameters are nonfinite")
        optimizer.zero_grad(set_to_none=True)

        post_step_optimizer_state = C2.optimizer_state_cpu(optimizer)
        saved_rng_state = C2.capture_rng_state()
        self_sha = sha256(Path(__file__).resolve())

        checkpoint_payload = {
            "scratch_rehearsal": True,
            "milestone": MILESTONE,
            "experiment_id": EXPERIMENT_ID,
            "completed_epoch": 0,
            "completed_logical_batches": 1,
            "allowed_as_COMP005_resume_source": False,
            "selected_microbatch": SELECTED_MICROBATCH,
            "selected_chunk": SELECTED_CHUNK,
            "logical_batch": LOGICAL_BATCH,
            "optimizer_steps": 1,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "python_rng_state": saved_rng_state["python"],
            "numpy_rng_state": saved_rng_state["numpy"],
            "torch_cpu_rng_state": saved_rng_state["torch_cpu"],
            "torch_cuda_rng_state": saved_rng_state["torch_cuda"],
            "dataset_sha256": DATASET_SHA,
            "CUDA2RR_source_sha256": CUDA2RR_SOURCE_SHA,
            "CUDA2RR_results_sha256": CUDA2RR_RESULTS_SHA,
            "CUDA2RR_summary_sha256": CUDA2RR_SUMMARY_SHA,
            "CUDA2RR_scratch_sha256": CUDA2RR_SCRATCH_SHA,
            "CUDA3_source_sha256": CUDA3_SOURCE_SHA,
            "CUDA3_results_sha256": CUDA3_RESULTS_SHA,
            "CUDA3_summary_sha256": CUDA3_SUMMARY_SHA,
            "CUDA4R_runner_sha256": self_sha,
            "training_order_identity": {
                "split_seed": SEED,
                "epoch": 1,
                "epoch_shuffle_seed": SEED + 1,
                "train_profiles": int(len(train_idx)),
                "logical_batch_profiles": int(len(logical_idx)),
                "logical_batch_indices_sha256": logical_indices_sha,
            },
            "logical_batch_mean_losses": logical_mean_losses,
            "gradient_equivalence": {
                "full_8192_pass": True,
                "candidate_gradient_artifact_sha256": selected_grads_sha,
                "identity_eps_multiplier": IDENTITY_EPS_MULTIPLIER,
                "float32_eps": FLOAT32_EPS,
            },
            "OOD_used": False,
            "TOF_used": False,
        }
        atomic_torch_save(checkpoint_payload, SCRATCH_CHECKPOINT)
        scratch_sha = sha256(SCRATCH_CHECKPOINT)

        # Perturb RNG, then construct a new model/optimizer and verify exact reload.
        random.random()
        np.random.random()
        torch.rand(8)
        torch.rand(8, device=device)
        sync_cuda()

        _, _, model_reload, optimizer_reload = C2.build_fresh_model_and_optimizer(B2S, device, "cuda4_reload")
        loaded = torch.load(SCRATCH_CHECKPOINT, map_location="cpu", weights_only=False)
        checkpoint_gates = {
            "scratch_rehearsal_true": loaded.get("scratch_rehearsal") is True,
            "resume_source_false": loaded.get("allowed_as_COMP005_resume_source") is False,
            "completed_epoch_zero": loaded.get("completed_epoch") == 0,
            "completed_logical_batches_one": loaded.get("completed_logical_batches") == 1,
            "selected_microbatch_1024": loaded.get("selected_microbatch") == SELECTED_MICROBATCH,
            "selected_chunk_64": loaded.get("selected_chunk") == SELECTED_CHUNK,
            "logical_batch_8192": loaded.get("logical_batch") == LOGICAL_BATCH,
            "optimizer_steps_one": loaded.get("optimizer_steps") == 1,
            "dataset_SHA_exact": loaded.get("dataset_sha256") == DATASET_SHA,
            "CUDA2RR_scratch_SHA_exact": loaded.get("CUDA2RR_scratch_sha256") == CUDA2RR_SCRATCH_SHA,
            "CUDA3_results_SHA_exact": loaded.get("CUDA3_results_sha256") == CUDA3_RESULTS_SHA,
            "CUDA4R_runner_SHA_exact": loaded.get("CUDA4R_runner_sha256") == self_sha,
        }
        if not all(checkpoint_gates.values()):
            raise RuntimeError(f"CUDA4R scratch checkpoint contract failure: {checkpoint_gates}")

        model_reload.load_state_dict(loaded["model_state_dict"])
        optimizer_reload.load_state_dict(loaded["optimizer_state_dict"])
        C2.restore_rng_state({
            "python": loaded["python_rng_state"],
            "numpy": loaded["numpy_rng_state"],
            "torch_cpu": loaded["torch_cpu_rng_state"],
            "torch_cuda": loaded["torch_cuda_rng_state"],
        })

        model_reload_exact = C2.exact_tree_equal(model_state_cpu(model_reload), post_step_model_state)
        optimizer_reload_exact = C2.exact_tree_equal(C2.optimizer_state_cpu(optimizer_reload), post_step_optimizer_state)
        rng_reload_exact = C2.rng_state_equal(C2.capture_rng_state(), saved_rng_state)
        reloaded_finite = C2.all_model_parameters_finite(model_reload)

        if not model_reload_exact:
            raise RuntimeError("CUDA4R model state did not reload exactly")
        if not optimizer_reload_exact:
            raise RuntimeError("CUDA4R optimizer state did not reload exactly")
        if not rng_reload_exact:
            raise RuntimeError("CUDA4R RNG state did not reload exactly")
        if not reloaded_finite:
            raise RuntimeError("CUDA4R reloaded model contains nonfinite parameters")
        if sha256(COMP004_CHECKPOINT) != COMP004_CHECKPOINT_SHA:
            raise RuntimeError("Frozen COMP-XPU-004 checkpoint changed during CUDA4R")

        gates.update({
            "fresh_initialization_not_COMP004": fresh_initial_equals_COMP004 is False,
            "train_split_11520": len(train_idx) == N_TRAIN,
            "epoch1_logical_batch_8192": len(logical_idx) == LOGICAL_BATCH,
            "exact_8_microbatches": len(microbatch_records) == SELECTED_MICROBATCHES,
            "every_microbatch_size_1024": all(r["profiles"] == SELECTED_MICROBATCH for r in microbatch_records),
            "every_microbatch_scale_1_over_8": all(math.isclose(r["scale"], 1.0 / 8.0, rel_tol=0.0, abs_tol=0.0) for r in microbatch_records),
            "recovered_baseline_gradients_finite": baseline_grad_summary["finite"],
            "recovered_baseline_gradients_nonzero": baseline_grad_summary["nonzero"],
            "candidate_gradients_finite": candidate_grad_summary["finite"],
            "candidate_gradients_nonzero": candidate_grad_summary["nonzero"],
            "full_8192_loss_equivalence": all(v["pass"] for v in loss_cmp.values()),
            "full_8192_parameter_gradient_equivalence": grad_cmp["pass"],
            "full_8192_gradient_norm_equivalence": norm_cmp["pass"],
            "full_8192_overall_equivalence": full_equivalence,
            "exactly_one_optimizer_step": True,
            "model_changed_after_optimizer_step": model_changed,
            "post_step_parameters_finite": C2.all_model_parameters_finite(model),
            "scratch_checkpoint_written": SCRATCH_CHECKPOINT.exists(),
            "scratch_checkpoint_nonproduction": loaded.get("allowed_as_COMP005_resume_source") is False,
            "all_checkpoint_contract_gates": all(checkpoint_gates.values()),
            "reloaded_model_exact": model_reload_exact,
            "reloaded_optimizer_exact": optimizer_reload_exact,
            "reloaded_RNG_exact": rng_reload_exact,
            "reloaded_parameters_finite": reloaded_finite,
            "COMP004_checkpoint_still_unchanged": sha256(COMP004_CHECKPOINT) == COMP004_CHECKPOINT_SHA,
            "no_OOD": True,
            "no_TOF": True,
            "scratch_not_resume_source": True,
            "COMP005_full_training_not_authorized": True,
            "B3_not_authorized": True,
        })

        ok = all(bool(v) for v in gates.values())
        status = (
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
            if ok else
            "V16E1B2CUDA4R_A100_CUDA3_K64_ENGINE_REPAIR_FULL_LOGICAL_BATCH_REHEARSAL_GATE_FAILURE_"
            "COMP005_CUDA_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
        )

        results_payload = {
            "milestone": MILESTONE,
            "status": status,
            "runner_sha256": self_sha,
            "authority_gates": gates,
            "gpu": gpu_name,
            "selected_geometry": {
                "microbatch": SELECTED_MICROBATCH,
                "chunk": SELECTED_CHUNK,
                "logical_batch": LOGICAL_BATCH,
                "microbatches": SELECTED_MICROBATCHES,
                "profile_weighted_scale": 1.0 / 8.0,
            },
            "training_order_identity": {
                "split_seed": SEED,
                "epoch": 1,
                "epoch_shuffle_seed": SEED + 1,
                "train_profiles": int(len(train_idx)),
                "logical_batch_indices_sha256": logical_indices_sha,
            },
            "baseline_gradient_recovery": recovery,
            "baseline_gradient_summary": baseline_grad_summary,
            "candidate_gradient_summary": candidate_grad_summary,
            "loss_equivalence": loss_cmp,
            "parameter_gradient_equivalence": grad_cmp,
            "gradient_norm_equivalence": norm_cmp,
            "full_8192_equivalence_pass": bool(full_equivalence),
            "logical_batch_mean_losses": logical_mean_losses,
            "logical_batch_seconds": float(logical_seconds),
            "throughput_profiles_per_s": float(LOGICAL_BATCH / logical_seconds),
            "peak_cuda_memory_gib": peak_gib,
            "microbatch_records": microbatch_records,
            "selected_gradient_artifact": str(SELECTED_GRADS),
            "selected_gradient_artifact_sha256": selected_grads_sha,
            "scratch_checkpoint": str(SCRATCH_CHECKPOINT),
            "scratch_checkpoint_sha256": scratch_sha,
            "checkpoint_contract_gates": checkpoint_gates,
            "model_reload_exact": model_reload_exact,
            "optimizer_reload_exact": optimizer_reload_exact,
            "RNG_reload_exact": rng_reload_exact,
            "CUDA5_final_COMP005_training_authorization_freeze_authorized": bool(ok),
            "COMP005_CUDA_full_training_authorized": False,
            "B3_authorized": False,
            "OOD_used": False,
            "TOF_used": False,
        }
        atomic_json_write(results_payload, RESULTS)
        gates["results_written"] = RESULTS.exists() and RESULTS.stat().st_size > 0
        ok = all(bool(v) for v in gates.values())
        if not ok:
            raise RuntimeError("CUDA4R final gate failure after results write")

        summary_payload = {
            "milestone": MILESTONE,
            "status": status,
            "runner_sha256": self_sha,
            "results_sha256": sha256(RESULTS),
            "scratch_checkpoint_sha256": scratch_sha,
            "selected_gradient_artifact_sha256": selected_grads_sha,
            "selected_microbatch": SELECTED_MICROBATCH,
            "selected_chunk": SELECTED_CHUNK,
            "logical_batch_profiles": LOGICAL_BATCH,
            "microbatches": SELECTED_MICROBATCHES,
            "logical_batch_seconds": float(logical_seconds),
            "throughput_profiles_per_s": float(LOGICAL_BATCH / logical_seconds),
            "peak_cuda_memory_gib": peak_gib,
            "logical_batch_mean_total_loss": float(logical_mean_losses["total"]),
            "logical_batch_mean_physics_loss": float(logical_mean_losses["physics"]),
            "candidate_gradient_l2_norm": float(candidate_grad_summary["global_l2_norm"]),
            "baseline_gradient_l2_norm": float(baseline_grad_summary["global_l2_norm"]),
            "full_8192_equivalence_pass": True,
            "model_reload_exact": model_reload_exact,
            "optimizer_reload_exact": optimizer_reload_exact,
            "RNG_reload_exact": rng_reload_exact,
            "scratch_allowed_as_COMP005_resume_source": False,
            "CUDA5_final_COMP005_training_authorization_freeze_authorized": True,
            "COMP005_CUDA_full_training_authorized": False,
            "B3_authorized": False,
            "next_milestone": (
                "V16E-1B2CUDA5 — final COMP-CUDA-005 production-training authorization freeze; "
                "CUDA4R scratch weights remain permanently prohibited as a production initializer or resume source"
            ),
            "gates": {k: bool(v) for k, v in gates.items()},
        }
        atomic_json_write(summary_payload, SUMMARY)

        print("\nREHEARSAL RESULT")
        print("  logical batch profiles     :", LOGICAL_BATCH)
        print("  microbatch                 :", SELECTED_MICROBATCH)
        print("  VJP chunk                  :", SELECTED_CHUNK)
        print("  microbatches               :", SELECTED_MICROBATCHES)
        print("  logical batch seconds      :", f"{logical_seconds:.3f}")
        print("  throughput profiles/s      :", f"{LOGICAL_BATCH / logical_seconds:.3f}")
        print("  peak CUDA memory (GiB)     :", f"{peak_gib:.3f}")
        print("  baseline grad norm         :", f"{baseline_grad_summary['global_l2_norm']:.9e}")
        print("  selected grad norm         :", f"{candidate_grad_summary['global_l2_norm']:.9e}")
        print("  mean total loss            :", f"{logical_mean_losses['total']:.9e}")
        print("  mean physics loss          :", f"{logical_mean_losses['physics']:.9e}")
        print("  full-8192 equivalence      :", True)
        print("  model reload exact         :", model_reload_exact)
        print("  optimizer reload exact     :", optimizer_reload_exact)
        print("  RNG reload exact           :", rng_reload_exact)
        print("  scratch usable as resume   :", False)

        print("\nFINAL GATES")
        for k, v in gates.items():
            print("[PASS]" if v else "[FAIL]", k)

        print("\nSTATUS")
        print(" ", status)
        print("\nHASHES")
        print("  CUDA4R Runner      :", self_sha)
        print("  Results            :", sha256(RESULTS))
        print("  Selected Gradients :", selected_grads_sha)
        print("  Scratch Checkpoint :", scratch_sha)
        print("  Summary            :", sha256(SUMMARY))
        print("\nNEXT")
        print("  V16E-1B2CUDA5 — final COMP-CUDA-005 production-training authorization freeze")
        return 0

    except Exception as exc:
        failure = {
            "milestone": MILESTONE,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "gates": gates,
            "COMP005_CUDA_full_training_authorized": False,
            "B3_authorized": False,
        }
        atomic_json_write(failure, FAILURE)
        print(failure["traceback"])
        print("\nSTATUS")
        print("  V16E1B2CUDA4R_A100_CUDA3_K64_ENGINE_REPAIR_FULL_LOGICAL_BATCH_REHEARSAL_FAILURE_"
              "COMP005_CUDA_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
