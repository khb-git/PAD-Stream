#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2CUDA3-A100
Microbatch / Chunked-Batched-VJP Performance Sweep

Purpose
-------
Use the CUDA2RR-certified native-CUDA recurrent higher-order-autograd path to
rank faster implementation geometries for prospective COMP-CUDA-005 training.

NO TRAINING.
NO OPTIMIZER STEP.
NO WEIGHT UPDATE.
NO CHECKPOINT RESUME.
NO OOD.
NO TOF.
NO B3.

This milestone is a PERFORMANCE RANKING / IMPLEMENTATION-EQUIVALENCE sweep.
It does not authorize full COMP-005 training.

Authority
---------
CUDA2RR must exist, match its frozen source/results/summary SHA values, and
carry the exact status that authorizes the A100 performance sweep.

Benchmark sample
----------------
Use the exact frozen Stage-2 split and epoch-1 ordering, then benchmark the
first 2048 training profiles.  This sample is large enough to exercise
multiple production microbatches while keeping the sweep practical.

Two-stage sweep
---------------
Stage A — microbatch sweep at frozen K=16:
    microbatch = 128, 256, 512, 1024, 2048

Stage B — chunk sweep at the fastest equivalent feasible Stage-A microbatch:
    K = 4, 8, 16, 32, 64

Each candidate runs in a fresh subprocess / CUDA context, with:
    * fresh seed-1337 model construction
    * native CUDA recurrent graph (cuDNN disabled only inside higher-order graph)
    * corrected B2S total loss
    * profile-weighted gradient accumulation over the same 2048 profiles
    * NO optimizer.step()
    * exact proof that model parameters remain unchanged

A disposable 128-profile warm-up is performed before the measured fresh-model
pass.  Warm-up weights are discarded.

Equivalence firewall
--------------------
The baseline is microbatch=128, K=16 on the same 2048 profiles.
Every candidate must match:
    * all aggregate corrected-loss components
    * every accumulated parameter-gradient tensor

with the frozen B2AC float32 computational-identity budget:
    bound = 1024 * eps_float32 * max(1, max_abs(reference), max_abs(candidate))

Runtime/resource failures are recorded without fallback.

Outcome
-------
If at least one candidate is equivalent and feasible, record the fastest
candidate.  If it is faster than the certified CUDA2RR production geometry,
CUDA4 may rehearse that selected geometry on the full 8192-profile logical
batch before any production authorization.

COMP-005 CUDA full training remains unauthorized.
B3 remains unauthorized.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
import traceback
from typing import Any

import numpy as np
import torch


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2CUDA3-A100"
SEED = 1337
BENCHMARK_PROFILES = 2048
BASELINE_MICROBATCH = 128
BASELINE_CHUNK = 16
MICROBATCH_CANDIDATES = [128, 256, 512, 1024, 2048]
CHUNK_CANDIDATES = [4, 8, 16, 32, 64]
FLOAT32_EPS = float(np.finfo(np.float32).eps)
IDENTITY_EPS_MULTIPLIER = 1024.0

RUNTIME_ROOT = Path("/content/PAD_Stream_Runtime")
DRIVE_ROOT = Path("/content/drive/MyDrive/PAD_Stream_Compute")

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

# Context only; never used as a numerical gate for candidates.
CUDA2RR_FULL_LOGICAL_SECONDS = 661.319
CUDA2RR_FULL_LOGICAL_PEAK_GIB = 5.369
XPU_B2AF_FULL_LOGICAL_SECONDS = 503.661

OUT = (
    DRIVE_ROOT / "provenance" / "cuda_performance"
    / "V16E1B2CUDA3_A100_MICROBATCH_BATCHED_VJP_PERFORMANCE_SWEEP"
)
CANDIDATE_DIR = OUT / "candidates"
OUT.mkdir(parents=True, exist_ok=True)
CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY = OUT / "PAD_Stream_V16E1B2CUDA3_A100_Summary.json"
RESULTS = OUT / "V16E1B2CUDA3_A100_Performance_Sweep_Results.json"
FAILURE = OUT / "V16E1B2CUDA3_A100_Performance_Sweep_Failure.json"
BASELINE_GRADS = OUT / "V16E1B2CUDA3_Baseline_MB128_K16_Gradients.pt"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def exact(path: Path, expected: str) -> bool:
    return path.exists() and sha256(path) == expected


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json_write(payload: Any, path: Path):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def atomic_torch_save(payload: Any, path: Path):
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
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def sync_cuda():
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def model_state_cpu(model):
    return {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}


def exact_state_equal(a, b) -> bool:
    if a.keys() != b.keys():
        return False
    return all(torch.equal(a[k], b[k]) for k in a)


def gradient_state_cpu(model):
    out = {}
    for name, p in model.named_parameters():
        if p.grad is None:
            out[name] = None
        else:
            out[name] = p.grad.detach().cpu().clone()
    return out


def gradients_finite_nonzero(grads: dict[str, Any]):
    finite = True
    nonzero = False
    sq = 0.0
    tensors = 0
    for g in grads.values():
        if g is None:
            continue
        tensors += 1
        finite = finite and bool(torch.isfinite(g).all().item())
        if bool(torch.any(g != 0).item()):
            nonzero = True
        sq += float(torch.sum(g.double() * g.double()).item())
    return {
        "finite": finite,
        "nonzero": nonzero,
        "gradient_tensor_count": tensors,
        "global_l2_norm": math.sqrt(sq),
    }


def identity_bound(a_max: float, b_max: float) -> float:
    return IDENTITY_EPS_MULTIPLIER * FLOAT32_EPS * max(1.0, a_max, b_max)


def compare_scalar(ref: float, cand: float):
    bound = identity_bound(abs(ref), abs(cand))
    diff = abs(ref - cand)
    return {"pass": diff <= bound, "abs_diff": diff, "bound": bound}


def compare_gradient_dict(ref: dict[str, Any], cand: dict[str, Any]):
    details = {}
    overall = True
    if ref.keys() != cand.keys():
        return {"pass": False, "reason": "gradient key mismatch", "details": {}}
    for name in ref:
        a = ref[name]
        b = cand[name]
        if a is None or b is None:
            ok = (a is None and b is None)
            details[name] = {"pass": ok, "none_match": ok}
            overall = overall and ok
            continue
        if tuple(a.shape) != tuple(b.shape):
            details[name] = {"pass": False, "shape_ref": list(a.shape), "shape_cand": list(b.shape)}
            overall = False
            continue
        diff = torch.max(torch.abs(a - b)).item() if a.numel() else 0.0
        amax = torch.max(torch.abs(a)).item() if a.numel() else 0.0
        bmax = torch.max(torch.abs(b)).item() if b.numel() else 0.0
        bound = identity_bound(amax, bmax)
        ok = math.isfinite(diff) and diff <= bound
        details[name] = {
            "pass": ok,
            "max_abs_diff": float(diff),
            "reference_max_abs": float(amax),
            "candidate_max_abs": float(bmax),
            "bound": float(bound),
        }
        overall = overall and ok
    return {"pass": overall, "details": details}



def make_cuda3_chunked_batched_engine(chunk_size: int):
    """Exact B2AC chunked batched-VJP algorithm, generalized to K=64.

    K=4/8/16/32 is algorithmically identical to frozen B2AC.  K=64 simply
    executes the same loop as one full 64-cotangent chunk.  CUDA3 itself is
    source-hash bound, and every candidate must pass the baseline equivalence
    firewall before it can be performance-eligible.
    """
    if chunk_size not in CHUNK_CANDIDATES:
        raise RuntimeError(f"Unauthorized CUDA3 chunk size {chunk_size}")

    def engine(S_pred, xi, p11):
        if S_pred.ndim != 3:
            raise RuntimeError(f"Unexpected S_pred rank {S_pred.ndim}; expected [B,T,1].")
        B, T, C = S_pred.shape
        if C != 1:
            raise RuntimeError(f"Unexpected output channel count {C}; expected 1.")

        nxi_chunks = []
        ntd_chunks = []
        nx_chunks = []
        for j0 in range(0, T, chunk_size):
            j1 = min(T, j0 + chunk_size)
            K = j1 - j0
            global_j = torch.arange(j0, j1, device=S_pred.device)
            local_j = torch.arange(K, device=S_pred.device)
            V2 = torch.nn.functional.one_hot(global_j, num_classes=T).to(
                dtype=S_pred.dtype, device=S_pred.device
            )
            V = V2[:, None, :, None].expand(K, B, T, 1)
            gx, gp = torch.autograd.grad(
                outputs=S_pred,
                inputs=(xi, p11),
                grad_outputs=V,
                retain_graph=True,
                create_graph=True,
                allow_unused=False,
                is_grads_batched=True,
            )
            N_xi_chunk = gx[local_j, :, global_j, 0].transpose(0, 1).unsqueeze(-1)
            N_tD_chunk = gp[:, :, 7].transpose(0, 1).unsqueeze(-1)
            N_X_chunk = gp[:, :, 8].transpose(0, 1).unsqueeze(-1)
            nxi_chunks.append(N_xi_chunk)
            ntd_chunks.append(N_tD_chunk)
            nx_chunks.append(N_X_chunk)

        N_xi = torch.cat(nxi_chunks, dim=1)
        N_tD = torch.cat(ntd_chunks, dim=1)
        N_X = torch.cat(nx_chunks, dim=1)
        if N_xi.shape != S_pred.shape or N_tD.shape != S_pred.shape or N_X.shape != S_pred.shape:
            raise RuntimeError("CUDA3 chunked derivative output shapes do not match S_pred.")
        return N_xi, N_tD, N_X

    return engine

def authority_gates():
    gates = {}
    gates["git_working_tree_clean"] = run_git(R, "status", "--porcelain") == ""
    gates["CUDA_available"] = torch.cuda.is_available()
    gates["A100_runtime"] = gates["CUDA_available"] and "A100" in torch.cuda.get_device_name(0).upper()
    gates["CUDA2RR_source_SHA_exact"] = exact(CUDA2RR_SOURCE, CUDA2RR_SOURCE_SHA)
    gates["CUDA2RR_results_SHA_exact"] = exact(CUDA2RR_RESULTS, CUDA2RR_RESULTS_SHA)
    gates["CUDA2RR_summary_SHA_exact"] = exact(CUDA2RR_SUMMARY, CUDA2RR_SUMMARY_SHA)
    if CUDA2RR_SUMMARY.exists():
        s = read_json(CUDA2RR_SUMMARY)
        gates["CUDA2RR_status_exact"] = s.get("status") == EXPECTED_CUDA2RR_STATUS
        gates["CUDA2RR_full_training_false"] = s.get("COMP005_CUDA_full_training_authorized") is False
        gates["CUDA2RR_B3_false"] = s.get("B3_authorized") is False
    else:
        gates["CUDA2RR_status_exact"] = False
        gates["CUDA2RR_full_training_false"] = False
        gates["CUDA2RR_B3_false"] = False
    return gates


def load_science_modules():
    C2 = import_module(CUDA2RR_SOURCE, "cuda2rr_authority_module")
    if not exact(C2.B2S_SOURCE, C2.B2S_SOURCE_SHA):
        raise RuntimeError("B2S source SHA mismatch")
    if not exact(C2.B2AC_SOURCE, C2.B2AC_SOURCE_SHA):
        raise RuntimeError("B2AC source SHA mismatch")
    if not exact(C2.DATASET, C2.DATASET_SHA):
        raise RuntimeError("Dataset SHA mismatch")
    B2S = import_module(C2.B2S_SOURCE, "cuda3_b2s")
    B2AC = import_module(C2.B2AC_SOURCE, "cuda3_b2ac")
    return C2, B2S, B2AC


def benchmark_ids(C2):
    train_idx = C2.frozen_train_indices(C2.N_TOTAL)
    order = C2.production_epoch_order(train_idx, 1)
    ids = order[:BENCHMARK_PROFILES]
    if len(ids) != BENCHMARK_PROFILES:
        raise RuntimeError("Benchmark order length mismatch")
    return ids


def run_one_pass(C2, B2S, B2AC, microbatch: int, chunk: int, *, warmup: bool):
    device = torch.device("cuda")
    M, _J, model, _optimizer = C2.build_fresh_model_and_optimizer(
        B2S, device, f"cuda3_mb{microbatch}_k{chunk}_{'warm' if warmup else 'measure'}"
    )
    initial = model_state_cpu(model)

    data = np.load(C2.DATASET)
    xi_all = data["xi"]
    Sw_all = data["Sw"]
    p11_all = data["p11"]
    ai_all = data["ai"]
    at_all = data["at"]
    ids_all = benchmark_ids(C2)
    ids_use = ids_all[:128] if warmup else ids_all
    logical_n = len(ids_use)

    engine = make_cuda3_chunked_batched_engine(chunk)
    original_engine = B2S.local_recurrent_derivatives_create_graph
    B2S.local_recurrent_derivatives_create_graph = engine

    model.zero_grad(set_to_none=True)
    weighted = {k: 0.0 for k in ["data", "physics", "bc_inj", "bc_tip", "anchor", "mono", "total"]}
    records = []

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    sync_cuda()
    t0 = time.perf_counter()

    try:
        for i, m0 in enumerate(range(0, logical_n, microbatch), start=1):
            ids = ids_use[m0:m0 + microbatch]
            m = len(ids)
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
            if not torch.isfinite(S_pred).all().item() or not torch.isfinite(residual).all().item():
                raise RuntimeError("Nonfinite prediction/residual")
            if not all(torch.isfinite(v).all().item() for v in parts.values()):
                raise RuntimeError("Nonfinite loss")

            scale = float(m) / float(logical_n)
            scaled_total = parts["total"] * scale
            with torch.backends.cudnn.flags(enabled=False):
                scaled_total.backward()
            sync_cuda()
            mb_sec = time.perf_counter() - mb_t0

            for k in weighted:
                weighted[k] += float(parts[k].detach().cpu()) * m
            records.append({"index": i, "profiles": m, "seconds": mb_sec})

            del xi, Sw, p11, ai, at, S_pred, residual, parts, scaled_total
    finally:
        B2S.local_recurrent_derivatives_create_graph = original_engine

    sync_cuda()
    seconds = time.perf_counter() - t0
    peak_gib = torch.cuda.max_memory_allocated() / (1024.0 ** 3)
    grads = gradient_state_cpu(model)
    gsum = gradients_finite_nonzero(grads)
    final = model_state_cpu(model)
    unchanged = exact_state_equal(initial, final)
    means = {k: weighted[k] / float(logical_n) for k in weighted}

    return {
        "seconds": float(seconds),
        "throughput_profiles_per_s": float(logical_n / seconds),
        "peak_cuda_memory_gib": float(peak_gib),
        "profiles": int(logical_n),
        "microbatches": len(records),
        "loss_means": means,
        "gradient_summary": gsum,
        "model_parameters_exactly_unchanged": unchanged,
        "microbatch_records": records,
    }, grads


def candidate_child(microbatch: int, chunk: int) -> int:
    key = f"mb{microbatch}_k{chunk}"
    out_json = CANDIDATE_DIR / f"{key}.json"
    out_grad = CANDIDATE_DIR / f"{key}_gradients.pt"
    for p in [out_json, out_grad]:
        if p.exists():
            p.unlink()

    payload = {
        "milestone": MILESTONE,
        "candidate": {"microbatch": microbatch, "chunk": chunk},
        "success": False,
    }
    try:
        gates = authority_gates()
        if not all(gates.values()):
            raise RuntimeError(f"Authority gate failure: {gates}")
        if BENCHMARK_PROFILES % microbatch != 0:
            raise RuntimeError("Candidate microbatch must exactly divide 2048")
        if microbatch not in MICROBATCH_CANDIDATES:
            raise RuntimeError("Unauthorized microbatch candidate")
        if chunk not in CHUNK_CANDIDATES:
            raise RuntimeError("Unauthorized chunk candidate")

        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.set_float32_matmul_precision("highest")

        C2, B2S, B2AC = load_science_modules()

        # Disposable warm-up; discard all state afterwards.
        _warm, _ = run_one_pass(C2, B2S, B2AC, microbatch, chunk, warmup=True)
        torch.cuda.empty_cache()

        measured, grads = run_one_pass(C2, B2S, B2AC, microbatch, chunk, warmup=False)
        if not measured["gradient_summary"]["finite"]:
            raise RuntimeError("Candidate gradients nonfinite")
        if not measured["gradient_summary"]["nonzero"]:
            raise RuntimeError("Candidate gradients all zero")
        if not measured["model_parameters_exactly_unchanged"]:
            raise RuntimeError("Model parameters changed without optimizer step")

        atomic_torch_save(grads, out_grad)
        payload.update({
            "success": True,
            "authority_gates": gates,
            "measurement": measured,
            "gradient_artifact": str(out_grad),
            "gradient_artifact_sha256": sha256(out_grad),
            "no_optimizer_step": True,
            "no_weight_update": True,
            "COMP005_CUDA_full_training_authorized": False,
            "B3_authorized": False,
        })
        atomic_json_write(payload, out_json)
        print(json.dumps({
            "candidate": key,
            "success": True,
            "seconds": measured["seconds"],
            "throughput": measured["throughput_profiles_per_s"],
            "peak_gib": measured["peak_cuda_memory_gib"],
            "grad_norm": measured["gradient_summary"]["global_l2_norm"],
        }, indent=2))
        return 0
    except Exception as exc:
        payload.update({
            "success": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "COMP005_CUDA_full_training_authorized": False,
            "B3_authorized": False,
        })
        atomic_json_write(payload, out_json)
        print(payload["traceback"], file=sys.stderr)
        return 2


def launch_candidate(microbatch: int, chunk: int):
    cmd = [sys.executable, str(Path(__file__).resolve()), "--candidate", str(microbatch), str(chunk)]
    print(f"\n--- candidate mb={microbatch}, K={chunk} ---")
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.returncode != 0 and proc.stderr.strip():
        tail = "\n".join(proc.stderr.strip().splitlines()[-12:])
        print(tail)
    path = CANDIDATE_DIR / f"mb{microbatch}_k{chunk}.json"
    if not path.exists():
        return {
            "candidate": {"microbatch": microbatch, "chunk": chunk},
            "success": False,
            "error": "candidate result artifact missing",
        }
    return read_json(path)


def attach_equivalence(candidate: dict, baseline_losses: dict, baseline_grads: dict):
    if not candidate.get("success"):
        candidate["equivalence"] = {"pass": False, "reason": "candidate execution failed"}
        return candidate
    losses = candidate["measurement"]["loss_means"]
    loss_cmp = {k: compare_scalar(float(baseline_losses[k]), float(losses[k])) for k in baseline_losses}
    grad_path = Path(candidate["gradient_artifact"])
    cand_grads = torch.load(grad_path, map_location="cpu", weights_only=False)
    grad_cmp = compare_gradient_dict(baseline_grads, cand_grads)
    eq = all(v["pass"] for v in loss_cmp.values()) and grad_cmp["pass"]
    candidate["equivalence"] = {
        "pass": bool(eq),
        "loss_components": loss_cmp,
        "parameter_gradients": grad_cmp,
        "identity_eps_multiplier": IDENTITY_EPS_MULTIPLIER,
        "float32_eps": FLOAT32_EPS,
    }
    return candidate


def main_parent() -> int:
    print("=" * 100)
    print("PAD-Stream V16E-1B2CUDA3-A100")
    print("A100 Microbatch / Batched-VJP Performance Sweep")
    print("=" * 100)
    print("NO TRAINING — NO OPTIMIZER STEP — NO WEIGHT UPDATE\n")

    if SUMMARY.exists():
        raise RuntimeError("CUDA3 summary already exists; refusing overwrite")

    gates = authority_gates()
    print("AUTHORITY GATES")
    for k, v in gates.items():
        print(f"[{'PASS' if v else 'FAIL'}] {k}")
    if not all(gates.values()):
        raise RuntimeError("CUDA3 blocked by authority failure")

    # Remove only CUDA3 candidate artifacts from prior incomplete attempt.
    for p in CANDIDATE_DIR.glob("mb*_k*.json"):
        p.unlink()
    for p in CANDIDATE_DIR.glob("mb*_k*_gradients.pt"):
        p.unlink()
    for p in [RESULTS, FAILURE, BASELINE_GRADS]:
        if p.exists():
            p.unlink()

    all_results = []

    print("\nSTAGE A — MICROBATCh SWEEP AT K=16")
    baseline = None
    for mb in MICROBATCH_CANDIDATES:
        rec = launch_candidate(mb, BASELINE_CHUNK)
        all_results.append(rec)
        if mb == BASELINE_MICROBATCH:
            if not rec.get("success"):
                raise RuntimeError("CUDA3 baseline mb128/K16 failed")
            baseline = rec
            source_grad = Path(rec["gradient_artifact"])
            atomic_torch_save(
                torch.load(source_grad, map_location="cpu", weights_only=False),
                BASELINE_GRADS,
            )
            rec["equivalence"] = {"pass": True, "reference": True}

    if baseline is None:
        raise RuntimeError("CUDA3 baseline missing")
    baseline_grads = torch.load(BASELINE_GRADS, map_location="cpu", weights_only=False)
    baseline_losses = baseline["measurement"]["loss_means"]

    for rec in all_results:
        if rec is baseline:
            continue
        attach_equivalence(rec, baseline_losses, baseline_grads)

    stage_a_pass = [
        r for r in all_results
        if r.get("success") and r.get("equivalence", {}).get("pass")
    ]
    if not stage_a_pass:
        raise RuntimeError("No equivalent feasible Stage-A candidate")
    best_a = min(stage_a_pass, key=lambda r: r["measurement"]["seconds"])
    best_mb = int(best_a["candidate"]["microbatch"])

    print("\nSTAGE A RESULT")
    for rec in all_results:
        c = rec["candidate"]
        if rec.get("success"):
            m = rec["measurement"]
            eq = rec.get("equivalence", {}).get("pass", False)
            print(
                f"mb={c['microbatch']:4d} K={c['chunk']:2d} | "
                f"eq={eq} | {m['seconds']:.3f}s | "
                f"{m['throughput_profiles_per_s']:.3f} prof/s | "
                f"{m['peak_cuda_memory_gib']:.3f} GiB"
            )
        else:
            print(f"mb={c['microbatch']:4d} K={c['chunk']:2d} | FAILED | {rec.get('error','')}")
    print(f"Best Stage-A microbatch: {best_mb}")

    print("\nSTAGE B — CHUNK SWEEP AT BEST MICROBATCh")
    stage_b = []
    for k in CHUNK_CANDIDATES:
        existing = next(
            (r for r in all_results if r.get("candidate", {}).get("microbatch") == best_mb and r.get("candidate", {}).get("chunk") == k),
            None,
        )
        rec = existing if existing is not None else launch_candidate(best_mb, k)
        if existing is None:
            all_results.append(rec)
            attach_equivalence(rec, baseline_losses, baseline_grads)
        stage_b.append(rec)

    stage_b_pass = [
        r for r in stage_b
        if r.get("success") and r.get("equivalence", {}).get("pass")
    ]
    if not stage_b_pass:
        raise RuntimeError("No equivalent feasible Stage-B candidate")
    best = min(stage_b_pass, key=lambda r: r["measurement"]["seconds"])

    base_sec = float(baseline["measurement"]["seconds"])
    best_sec = float(best["measurement"]["seconds"])
    speedup = base_sec / best_sec
    best_is_faster = best_sec < base_sec

    print("\nSTAGE B RESULT")
    for rec in stage_b:
        c = rec["candidate"]
        if rec.get("success"):
            m = rec["measurement"]
            eq = rec.get("equivalence", {}).get("pass", False)
            print(
                f"mb={c['microbatch']:4d} K={c['chunk']:2d} | "
                f"eq={eq} | {m['seconds']:.3f}s | "
                f"{m['throughput_profiles_per_s']:.3f} prof/s | "
                f"{m['peak_cuda_memory_gib']:.3f} GiB"
            )
        else:
            print(f"mb={c['microbatch']:4d} K={c['chunk']:2d} | FAILED | {rec.get('error','')}")

    status = (
        "V16E1B2CUDA3_A100_MICROBATCH_BATCHED_VJP_PERFORMANCE_SWEEP_PASS_"
        "CUDA2RR_AUTHORITY_BOUND_FRESH_SEED_1337_FIXED_FIRST_2048_EPOCH1_TRAINING_PROFILES_"
        "NO_TRAINING_NO_OPTIMIZER_STEP_NO_WEIGHT_UPDATE_NATIVE_CUDA_RNN_HIGHER_ORDER_AUTOGRAD_"
        "ALL_ELIGIBLE_CANDIDATES_REQUIRED_FLOAT32_EPSILON_DERIVED_LOSS_AND_PARAMETER_GRADIENT_EQUIVALENCE_"
        f"SELECTED_MICROBATCH_{best['candidate']['microbatch']}_CHUNK_{best['candidate']['chunk']}_"
        + (
            "SELECTED_CANDIDATE_FASTER_THAN_MB128_K16_BASELINE_"
            "CUDA4_FULL_8192_PROFILE_SELECTED_GEOMETRY_REHEARSAL_AUTHORIZED_"
            if best_is_faster else
            "NO_CANDIDATE_FASTER_THAN_MB128_K16_BASELINE_"
            "CUDA4_SELECTED_GEOMETRY_ADOPTION_REHEARSAL_NOT_AUTHORIZED_"
        )
        + "COMP005_CUDA_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
    )

    self_sha = sha256(Path(__file__).resolve())
    results_payload = {
        "milestone": MILESTONE,
        "status": status,
        "runner_sha256": self_sha,
        "authority_gates": gates,
        "benchmark_profiles": BENCHMARK_PROFILES,
        "benchmark_order": "first_2048_profiles_of_frozen_epoch1_training_order",
        "baseline": {
            "microbatch": BASELINE_MICROBATCH,
            "chunk": BASELINE_CHUNK,
            "seconds": base_sec,
            "throughput_profiles_per_s": baseline["measurement"]["throughput_profiles_per_s"],
            "peak_cuda_memory_gib": baseline["measurement"]["peak_cuda_memory_gib"],
        },
        "selected": {
            "microbatch": int(best["candidate"]["microbatch"]),
            "chunk": int(best["candidate"]["chunk"]),
            "seconds": best_sec,
            "throughput_profiles_per_s": best["measurement"]["throughput_profiles_per_s"],
            "peak_cuda_memory_gib": best["measurement"]["peak_cuda_memory_gib"],
            "baseline_over_selected_speedup": speedup,
            "faster_than_baseline": best_is_faster,
        },
        "context_only": {
            "CUDA2RR_full_8192_seconds": CUDA2RR_FULL_LOGICAL_SECONDS,
            "CUDA2RR_full_8192_peak_gib": CUDA2RR_FULL_LOGICAL_PEAK_GIB,
            "XPU_B2AF_full_8192_seconds": XPU_B2AF_FULL_LOGICAL_SECONDS,
        },
        "candidate_results": all_results,
        "baseline_gradient_artifact": str(BASELINE_GRADS),
        "baseline_gradient_artifact_sha256": sha256(BASELINE_GRADS),
        "CUDA4_full_8192_selected_geometry_rehearsal_authorized": bool(best_is_faster),
        "COMP005_CUDA_full_training_authorized": False,
        "B3_authorized": False,
    }
    atomic_json_write(results_payload, RESULTS)

    summary_payload = {
        "milestone": MILESTONE,
        "status": status,
        "runner_sha256": self_sha,
        "results_sha256": sha256(RESULTS),
        "selected_microbatch": int(best["candidate"]["microbatch"]),
        "selected_chunk": int(best["candidate"]["chunk"]),
        "baseline_over_selected_speedup": speedup,
        "selected_peak_cuda_memory_gib": best["measurement"]["peak_cuda_memory_gib"],
        "CUDA4_full_8192_selected_geometry_rehearsal_authorized": bool(best_is_faster),
        "COMP005_CUDA_full_training_authorized": False,
        "B3_authorized": False,
    }
    atomic_json_write(summary_payload, SUMMARY)

    print("\nFINAL")
    print("  Selected microbatch       :", best["candidate"]["microbatch"])
    print("  Selected VJP chunk        :", best["candidate"]["chunk"])
    print("  Baseline seconds          :", f"{base_sec:.3f}")
    print("  Selected seconds          :", f"{best_sec:.3f}")
    print("  Baseline/selected speedup :", f"{speedup:.3f}x")
    print("  Selected peak CUDA GiB    :", f"{best['measurement']['peak_cuda_memory_gib']:.3f}")
    print("  CUDA4 authorized          :", bool(best_is_faster))
    print("  COMP005 training          : NOT AUTHORIZED")
    print("  B3                        : NOT AUTHORIZED")
    print("\nSTATUS")
    print(" ", status)
    print("\nHASHES")
    print("  CUDA3 Runner :", self_sha)
    print("  Results      :", sha256(RESULTS))
    print("  Summary      :", sha256(SUMMARY))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", nargs=2, metavar=("MICROBATCH", "CHUNK"), type=int)
    args = parser.parse_args()
    if args.candidate is not None:
        return candidate_child(args.candidate[0], args.candidate[1])
    try:
        return main_parent()
    except Exception as exc:
        payload = {
            "milestone": MILESTONE,
            "status": "V16E1B2CUDA3_A100_PERFORMANCE_SWEEP_FAILURE_COMP005_CUDA_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "COMP005_CUDA_full_training_authorized": False,
            "B3_authorized": False,
        }
        atomic_json_write(payload, FAILURE)
        print(payload["traceback"], file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
