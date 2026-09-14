#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2CUDA1R
A100 Native-CUDA RNN Cross-Backend Equivalence Repair

Purpose
-------
Repair the CUDA1 execution-path incompatibility encountered when PyTorch
2.11 CUDA dispatched the LSTM through cuDNN and batched VJP requested
`is_grads_batched=True`. The cuDNN RNN backward operator does not provide
the vmap batching rule required by the frozen B2AC K=16 derivative engine.

This repair disables cuDNN ONLY while constructing/evaluating the recurrent
autograd graph, thereby retaining CUDA execution through PyTorch native CUDA
kernels while preserving the exact frozen Stage-2 scientific graph, B2AC
derivative engine, K=16 chunking, fixtures, and equivalence budget.

This milestone is deliberately narrow:
  * NO COMP-005 training
  * NO optimizer creation
  * NO optimizer step
  * NO weight update
  * NO OOD
  * NO TOF
  * NO AMP
  * NO TF32

The trained COMP-XPU-004 checkpoint is used ONLY as a read-only numerical
fixture because the frozen B2AC reference tensors were generated from that
checkpoint. It is NOT authorized as an initializer for prospective COMP-005
training.

Scientific graph
----------------
UNCHANGED from the frozen Stage-2 corrected-residual lineage:
  * [xi, eta] recurrent coordinate input
  * raw physical p11 conditioner
  * exact frozen fractional-flow/loss functions from B2C
  * corrected conservative moving-fan residual from B2S
  * RH front speed
  * local N_xi, shared-condition N_tD and N_X derivatives
  * chunked batched-VJP implementation with K=16 from B2AC

Equivalence budget
------------------
Exactly the frozen B2AC computational identity budget:

    bound = 1024 * eps_float32
            * max(1, max_abs(reference), max_abs(candidate))

This is an implementation-equivalence budget, NOT a scientific-model
accuracy threshold.

Execution
---------
Run as a fresh subprocess from the clean Git checkout, for example:

    python PAD_Stream_V16E1B2CUDA1R_A100_Native_CUDA_RNN_Equivalence_Repair.py

Default persistent fixtures:
  dataset:
    /content/PAD_Stream_Runtime/datasets/
      V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz

  frozen B2AC reference tensors:
    /content/PAD_Stream_Runtime/xpu_reference/
      V16E1B2AC_Loop_Baseline_Tensors.pt

  frozen COMP-XPU-004 read-only checkpoint fixture:
    /content/PAD_Stream_Runtime/xpu_reference/
      V16E_BLREP_COMP_XPU_004.pt

Results are written only to Google Drive provenance storage by default.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple
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

import numpy as np
import torch


MILESTONE = "V16E-1B2CUDA1R-A100"
SEED = 1337
REFERENCE_MICROBATCH = 128
ADOPTED_CHUNK = 16
FLOAT32_EPS = float(np.finfo(np.float32).eps)
IDENTITY_EPS_MULTIPLIER = 1024.0
PARENT_GIT_AUTHORITY = "d05a54e2bea2a7ac7e6ac47e93b11404c0a76be1"

DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"
REFERENCE_SHA = "7d0beaf0b00564f6965c9862c09c619a4c5b00d058fe0885bb911972e0325d57"
COMP004_CHECKPOINT_SHA = "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69"

B2C_NAME = "PAD_Stream_V16E1B2C_XPU_COMP_XPU_002_800Epoch_Compressible_Reproduction.py"
B2C_SHA = "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18"

B2J_NAME = "PAD_Stream_V16E1B2J_XPU_COMP_XPU_004_Physics_Aware_Nc_Coordinate_Channel_Reproduction.py"
B2J_SHA = "fcc4074863a46f6b8d356a01ff0b4b2182d0ffa3ebc9b3fd053e35282f897a4c"

B2S_NAME = "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
B2S_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"

B2AC_NAME = "PAD_Stream_V16E1B2AC_XPU_Chunked_Batched_VJP_Equivalence_Performance_Sweep.py"
B2AC_SHA = "59f7ea7b0dc2e901f5a42649691c2dab5f4dfc5d399f953eaab5ba773040cd53"

B2AE_NAME = "PAD_Stream_V16E1B2AE_XPU_COMP005_Execution_Preflight_Contract_Freeze.py"
B2AE_SHA = "8bc7eb7f7a927d172bd7438fde719ee3f31c234acc2a167772dc1f6a556d68cc"

B2AF_NAME = "PAD_Stream_V16E1B2AF_XPU_COMP005_One_Logical_Batch_Scratch_Rehearsal.py"
B2AF_SHA = "ef48eeb3e6d20cde86c5ddd6ab1632590480c58aef74d94369a419750040c29d"

B2AG_NAME = "PAD_Stream_V16E1B2AG_XPU_B2AF_Interpretation_Final_COMP005_Authorization_Freeze.py"
B2AG_SHA = "04a707ce25bb6b1736e43fca2c96815c138893fd380aedbcd29d9121089f84d4"

CUDA1_NAME = "PAD_Stream_V16E1B2CUDA1_A100_Cross_Backend_Equivalence_Preflight.py"
CUDA1_SHA = "2b1cf388c69b44dfab86d2e585ac041a4da245d296b7003e33a1d567985b6d03"


# =============================================================================
# Generic helpers
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def exact(path: Path, expected: str) -> bool:
    return path.exists() and path.is_file() and sha256(path) == expected


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def atomic_json_write(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def atomic_torch_save(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, tmp)
    os.replace(tmp, path)


def run_git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def git_parent_is_ancestor(repo: Path, parent: str, head: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", parent, head],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.returncode == 0


def sync_cuda() -> None:
    torch.cuda.synchronize()


def reset_cuda_peak_memory() -> None:
    torch.cuda.reset_peak_memory_stats()


def peak_cuda_memory_bytes() -> int:
    return int(torch.cuda.max_memory_allocated())


def cpu_clone(x: torch.Tensor) -> torch.Tensor:
    return x.detach().cpu().clone()


def tensor_stats(x: torch.Tensor) -> dict:
    y = x.detach().float().cpu()
    return {
        "shape": list(y.shape),
        "dtype": str(y.dtype),
        "finite": bool(torch.isfinite(y).all().item()),
        "min": float(y.min().item()),
        "max": float(y.max().item()),
        "mean_abs": float(y.abs().mean().item()),
        "max_abs": float(y.abs().max().item()),
    }


def identity_compare(name: str, reference: torch.Tensor, candidate: torch.Tensor) -> dict:
    r = reference.detach().float().cpu()
    c = candidate.detach().float().cpu()

    shape_match = tuple(r.shape) == tuple(c.shape)
    finite = bool(torch.isfinite(r).all().item() and torch.isfinite(c).all().item())

    if not shape_match:
        return {
            "name": name,
            "pass": False,
            "shape_match": False,
            "reference_shape": list(r.shape),
            "candidate_shape": list(c.shape),
            "finite": finite,
            "max_abs_difference": None,
            "bound": None,
        }

    diff = torch.abs(r - c)
    max_abs_diff = float(diff.max().item())
    max_abs_reference = float(r.abs().max().item())
    max_abs_candidate = float(c.abs().max().item())

    scale = max(1.0, max_abs_reference, max_abs_candidate)
    bound = IDENTITY_EPS_MULTIPLIER * FLOAT32_EPS * scale

    return {
        "name": name,
        "pass": bool(finite and max_abs_diff <= bound),
        "shape_match": True,
        "finite": finite,
        "max_abs_difference": max_abs_diff,
        "max_abs_reference": max_abs_reference,
        "max_abs_candidate": max_abs_candidate,
        "bound": float(bound),
        "difference_over_bound": float(max_abs_diff / bound) if bound > 0 else None,
    }


def scalar_identity_compare(name: str, reference: float, candidate: float) -> dict:
    r = float(reference)
    c = float(candidate)
    scale = max(1.0, abs(r), abs(c))
    bound = IDENTITY_EPS_MULTIPLIER * FLOAT32_EPS * scale
    diff = abs(r - c)
    finite = math.isfinite(r) and math.isfinite(c)
    return {
        "name": name,
        "pass": bool(finite and diff <= bound),
        "finite": bool(finite),
        "reference": r,
        "candidate": c,
        "absolute_difference": float(diff),
        "bound": float(bound),
        "difference_over_bound": float(diff / bound) if bound > 0 else None,
    }


def gradient_compare(reference: Dict[str, torch.Tensor], candidate: Dict[str, torch.Tensor]) -> dict:
    ref_names = list(reference.keys())
    cand_names = list(candidate.keys())
    names_match = ref_names == cand_names

    per_parameter = {}
    if names_match:
        for name in ref_names:
            per_parameter[name] = identity_compare(
                name,
                reference[name],
                candidate[name],
            )

    return {
        "parameter_names_match": bool(names_match),
        "reference_parameter_names": ref_names,
        "candidate_parameter_names": cand_names,
        "per_parameter": per_parameter,
        "all_parameter_gradients_pass": bool(
            names_match and all(v["pass"] for v in per_parameter.values())
        ),
    }


# =============================================================================
# Exact B2AC K=16 chunked batched-VJP derivative engine
# =============================================================================

def chunked_local_recurrent_derivatives_create_graph(
    S_pred: torch.Tensor,
    xi: torch.Tensor,
    p11: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    chunk_size = ADOPTED_CHUNK

    if S_pred.ndim != 3:
        raise RuntimeError(
            f"Unexpected S_pred rank {S_pred.ndim}; expected [B,T,1]."
        )

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

        V2 = torch.nn.functional.one_hot(
            global_j,
            num_classes=T,
        ).to(dtype=S_pred.dtype, device=S_pred.device)

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

        N_xi_chunk = (
            gx[local_j, :, global_j, 0]
            .transpose(0, 1)
            .unsqueeze(-1)
        )

        N_tD_chunk = gp[:, :, 7].transpose(0, 1).unsqueeze(-1)
        N_X_chunk = gp[:, :, 8].transpose(0, 1).unsqueeze(-1)

        nxi_chunks.append(N_xi_chunk)
        ntd_chunks.append(N_tD_chunk)
        nx_chunks.append(N_X_chunk)

    N_xi = torch.cat(nxi_chunks, dim=1)
    N_tD = torch.cat(ntd_chunks, dim=1)
    N_X = torch.cat(nx_chunks, dim=1)

    if (
        N_xi.shape != S_pred.shape
        or N_tD.shape != S_pred.shape
        or N_X.shape != S_pred.shape
    ):
        raise RuntimeError("Chunked derivative output shapes do not match S_pred.")

    return N_xi, N_tD, N_X


# =============================================================================
# Exact B2S corrected conservative Stage-2 graph
# =============================================================================

def rh_xdot_coeff(M, p11_coeff: torch.Tensor) -> torch.Tensor:
    swc = p11_coeff[:, 2:3]
    X = p11_coeff[:, 8:9]
    Sw_star = p11_coeff[:, 9:10]
    Nc = p11_coeff[:, 10:11]

    S_pair = torch.cat(
        [swc.unsqueeze(1), Sw_star.unsqueeze(1)],
        dim=1,
    )

    fw_pair = M.fractional_flow_torch(S_pair, p11_coeff)
    fw_r = fw_pair[:, 0:1, :]
    fw_l = fw_pair[:, 1:2, :]

    denom = torch.clamp(
        (Sw_star - swc).unsqueeze(1),
        min=1e-8,
    )

    sigma = (fw_l - fw_r) / denom

    X3 = X.unsqueeze(1)
    Nc3 = Nc.unsqueeze(1)
    xdot = torch.exp(Nc3 * X3) * sigma

    return xdot


def corrected_physics_loss_training_graph(
    M,
    model,
    xi: torch.Tensor,
    p11: torch.Tensor,
):
    S_pred = model(xi, p11)

    N_xi, N_tD, N_X = chunked_local_recurrent_derivatives_create_graph(
        S_pred,
        xi,
        p11,
    )

    # Exact B2S semantics: physical conditioner values are fixed coefficients
    # for theta-gradient evaluation.
    pcoeff = p11.detach()
    xcoeff = xi.detach()

    fw = M.fractional_flow_torch(S_pred, pcoeff)

    dfdS = torch.autograd.grad(
        outputs=fw,
        inputs=S_pred,
        grad_outputs=torch.ones_like(fw),
        retain_graph=True,
        create_graph=True,
        only_inputs=True,
    )[0]

    X = pcoeff[:, 8:9].unsqueeze(1)
    Nc = pcoeff[:, 10:11].unsqueeze(1)

    uD = torch.exp(Nc * xcoeff * X)
    xdot = rh_xdot_coeff(M, pcoeff)

    residual = (
        N_tD
        + xdot * N_X
        + (uD * dfdS / X - xcoeff * xdot / X) * N_xi
        + Nc * uD * fw
    )

    if residual.shape[1] > 2:
        residual_used = residual[:, 1:-1, :]
    else:
        residual_used = residual

    Lp = torch.mean(residual_used ** 2)
    return S_pred, Lp, residual_used


def complete_corrected_total_loss(
    M,
    model,
    xi: torch.Tensor,
    Sw: torch.Tensor,
    p11: torch.Tensor,
    ai: torch.Tensor,
    at: torch.Tensor,
):
    S_pred, Lp, residual = corrected_physics_loss_training_graph(
        M,
        model,
        xi,
        p11,
    )

    Ld = M.data_loss(S_pred, Sw)
    Lbc = M.injector_bc_loss(S_pred, p11)
    Ltip = M.tip_bc_loss(S_pred, p11)
    La = M.anchor_loss(S_pred, ai, at)
    Lmono = M.monotonicity_loss(S_pred)

    total = (
        M.LAMBDA_DATA * Ld
        + M.LAMBDA_PHYS * Lp
        + M.LAMBDA_BC * Lbc
        + M.LAMBDA_TIP * Ltip
        + M.LAMBDA_ANCHOR * La
        + M.LAMBDA_MONO * Lmono
    )

    parts = {
        "data": Ld,
        "physics": Lp,
        "bc_inj": Lbc,
        "bc_tip": Ltip,
        "anchor": La,
        "mono": Lmono,
        "total": total,
    }

    return S_pred, residual, parts


# =============================================================================
# Snapshot construction
# =============================================================================

def load_model(M, J, checkpoint: dict, device: torch.device):
    EtaModel = J.build_eta_model_class(M)
    model = EtaModel()
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.to(device)
    model.train()
    return model


def make_batch(dataset: dict, ids: np.ndarray, device: torch.device):
    xi = (
        torch.from_numpy(dataset["xi"][ids])
        .to(device)
        .detach()
        .clone()
        .requires_grad_(True)
    )
    Sw = torch.from_numpy(dataset["Sw"][ids]).to(device)
    p11 = (
        torch.from_numpy(dataset["p11"][ids])
        .to(device)
        .detach()
        .clone()
        .requires_grad_(True)
    )
    ai = torch.from_numpy(dataset["ai"][ids]).to(device)
    at = torch.from_numpy(dataset["at"][ids]).to(device)
    return xi, Sw, p11, ai, at


def derivative_snapshot(M, J, checkpoint: dict, dataset: dict, ids: np.ndarray, device):
    model = load_model(M, J, checkpoint, device)
    xi, _, p11, _, _ = make_batch(dataset, ids, device)

    reset_cuda_peak_memory()
    sync_cuda()
    t0 = time.perf_counter()

    # CUDA1R implementation repair only:
    # Disable cuDNN for the recurrent graph so PyTorch uses native CUDA RNN
    # kernels compatible with batched VJP/vmap and higher-order autograd.
    # The model, tensors, scientific graph, K=16 derivative algorithm, and
    # equivalence budget are unchanged.
    with torch.backends.cudnn.flags(enabled=False):
        S_pred = model(xi, p11)
        N_xi, N_tD, N_X = chunked_local_recurrent_derivatives_create_graph(
            S_pred,
            xi,
            p11,
        )

    sync_cuda()
    t1 = time.perf_counter()

    return {
        "S_pred": cpu_clone(S_pred),
        "N_xi": cpu_clone(N_xi),
        "N_tD": cpu_clone(N_tD),
        "N_X": cpu_clone(N_X),
        "wall_seconds": float(t1 - t0),
        "peak_cuda_memory_bytes": peak_cuda_memory_bytes(),
    }


def full_graph_snapshot(M, J, checkpoint: dict, dataset: dict, ids: np.ndarray, device):
    model = load_model(M, J, checkpoint, device)
    param_before = {
        name: p.detach().cpu().clone()
        for name, p in model.named_parameters()
    }

    for p in model.parameters():
        p.grad = None

    xi, Sw, p11, ai, at = make_batch(dataset, ids, device)

    reset_cuda_peak_memory()
    sync_cuda()
    t0 = time.perf_counter()

    # CUDA1R implementation repair only. The complete forward, derivative,
    # corrected-residual, and theta-backward graph is constructed with cuDNN
    # RNN dispatch disabled. CUDA remains the execution device.
    with torch.backends.cudnn.flags(enabled=False):
        S_pred, residual, parts = complete_corrected_total_loss(
            M,
            model,
            xi,
            Sw,
            p11,
            ai,
            at,
        )

        forward_done = time.perf_counter()

        if not torch.isfinite(S_pred).all().item():
            raise RuntimeError("Nonfinite forward prediction.")
        if not torch.isfinite(residual).all().item():
            raise RuntimeError("Nonfinite corrected residual.")
        if not all(torch.isfinite(v).all().item() for v in parts.values()):
            raise RuntimeError("Nonfinite loss component.")

        parts["total"].backward()
    sync_cuda()
    t1 = time.perf_counter()

    gradients = {}
    gradient_summary = {}

    for name, p in model.named_parameters():
        if p.grad is None:
            raise RuntimeError(f"Missing parameter gradient: {name}")
        g = p.grad.detach()
        if not torch.isfinite(g).all().item():
            raise RuntimeError(f"Nonfinite parameter gradient: {name}")
        gradients[name] = cpu_clone(g)
        gradient_summary[name] = tensor_stats(g)

    weights_exactly_unchanged = all(
        torch.equal(p.detach().cpu(), param_before[name])
        for name, p in model.named_parameters()
    )

    if not weights_exactly_unchanged:
        raise RuntimeError("Model parameter changed without optimizer step.")

    return {
        "S_pred": cpu_clone(S_pred),
        "residual": cpu_clone(residual),
        "parameter_gradients": gradients,
        "losses": {k: float(v.detach().cpu().item()) for k, v in parts.items()},
        "gradient_summary": gradient_summary,
        "weights_exactly_unchanged": True,
        "forward_plus_residual_seconds": float(forward_done - t0),
        "forward_residual_backward_seconds": float(t1 - t0),
        "peak_cuda_memory_bytes": peak_cuda_memory_bytes(),
    }


def reconstruct_reference_losses(M, reference: dict, dataset: dict, ids: np.ndarray) -> dict:
    # Reconstruct all scalar losses directly from serialized frozen B2AC tensors.
    # This does not require a model or a backend derivative graph.
    S_pred = reference["S_pred_full"].detach().float().cpu()
    residual = reference["residual"].detach().float().cpu()
    Sw = torch.from_numpy(dataset["Sw"][ids]).float().cpu()
    p11 = torch.from_numpy(dataset["p11"][ids]).float().cpu()
    ai = torch.from_numpy(dataset["ai"][ids]).cpu()
    at = torch.from_numpy(dataset["at"][ids]).float().cpu()

    Ld = M.data_loss(S_pred, Sw)
    Lp = torch.mean(residual ** 2)
    Lbc = M.injector_bc_loss(S_pred, p11)
    Ltip = M.tip_bc_loss(S_pred, p11)
    La = M.anchor_loss(S_pred, ai, at)
    Lmono = M.monotonicity_loss(S_pred)

    total = (
        M.LAMBDA_DATA * Ld
        + M.LAMBDA_PHYS * Lp
        + M.LAMBDA_BC * Lbc
        + M.LAMBDA_TIP * Ltip
        + M.LAMBDA_ANCHOR * La
        + M.LAMBDA_MONO * Lmono
    )

    return {
        "data": float(Ld.item()),
        "physics": float(Lp.item()),
        "bc_inj": float(Lbc.item()),
        "bc_tip": float(Ltip.item()),
        "anchor": float(La.item()),
        "mono": float(Lmono.item()),
        "total": float(total.item()),
    }


# =============================================================================
# Main
# =============================================================================

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default="/content/PAD-Stream")
    p.add_argument(
        "--dataset",
        default=(
            "/content/PAD_Stream_Runtime/datasets/"
            "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
        ),
    )
    p.add_argument(
        "--reference",
        default=(
            "/content/PAD_Stream_Runtime/xpu_reference/"
            "V16E1B2AC_Loop_Baseline_Tensors.pt"
        ),
    )
    p.add_argument(
        "--checkpoint",
        default=(
            "/content/PAD_Stream_Runtime/xpu_reference/"
            "V16E_BLREP_COMP_XPU_004.pt"
        ),
    )
    p.add_argument(
        "--out",
        default=(
            "/content/drive/MyDrive/PAD_Stream_Compute/provenance/"
            "cuda_equivalence/V16E1B2CUDA1R_A100_NATIVE_CUDA_RNN_EQUIVALENCE_REPAIR"
        ),
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    repo = Path(args.repo).resolve()
    dataset_path = Path(args.dataset).resolve()
    reference_path = Path(args.reference).resolve()
    checkpoint_path = Path(args.checkpoint).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    results_path = out / "V16E1B2CUDA1R_A100_Native_CUDA_RNN_Equivalence_Results.json"
    tensors_path = out / "V16E1B2CUDA1R_A100_Candidate_Tensors.pt"
    failure_path = out / "V16E1B2CUDA1R_A100_Native_CUDA_RNN_Equivalence_Failure.json"

    payload = {
        "milestone": MILESTONE,
        "status": "STARTED_NOT_AUTHORIZED",
        "created_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "scientific_graph_changed": False,
        "backend_changed": "INTEL_XPU_TO_NVIDIA_CUDA_A100",
        "implementation_repair": (
            "CUDNN_RNN_DISABLED_ONLY_FOR_RECURRENT_AUTOGRAD_GRAPH_"
            "NATIVE_CUDA_RNN_PATH_USED_FOR_BATCHED_VJP_COMPATIBILITY"
        ),
        "cuda1_failed_artifact_preserved": True,
        "optimizer_created": False,
        "optimizer_step": False,
        "weight_update": False,
        "training_performed": False,
        "ood_used": False,
        "tof_used": False,
        "amp_enabled": False,
        "tf32_enabled": False,
        "reference_checkpoint_role": (
            "READ_ONLY_B2AC_NUMERICAL_EQUIVALENCE_FIXTURE_"
            "PROHIBITED_AS_COMP005_TRAINING_INITIALIZER"
        ),
        "equivalence_budget": {
            "formula": (
                "1024 * eps_float32 * max(1, max_abs(reference), "
                "max_abs(candidate))"
            ),
            "eps_float32": FLOAT32_EPS,
            "multiplier": IDENTITY_EPS_MULTIPLIER,
            "scientific_accuracy_threshold": False,
        },
    }

    try:
        # ---------------------------------------------------------------------
        # Repository / source authority gates
        # ---------------------------------------------------------------------
        if not repo.exists():
            raise RuntimeError(f"Repository missing: {repo}")

        head = run_git(repo, "rev-parse", "HEAD")
        status = run_git(repo, "status", "--porcelain")
        clean = status == ""
        parent_is_ancestor = git_parent_is_ancestor(repo, PARENT_GIT_AUTHORITY, head)

        if not clean:
            raise RuntimeError("Git working tree is not clean.")
        if not parent_is_ancestor:
            raise RuntimeError(
                f"Parent authority commit {PARENT_GIT_AUTHORITY} is not an ancestor of HEAD {head}."
            )

        source_expectations = {
            B2C_NAME: B2C_SHA,
            B2J_NAME: B2J_SHA,
            B2S_NAME: B2S_SHA,
            B2AC_NAME: B2AC_SHA,
            B2AE_NAME: B2AE_SHA,
            B2AF_NAME: B2AF_SHA,
            B2AG_NAME: B2AG_SHA,
            CUDA1_NAME: CUDA1_SHA,
        }

        source_checks = {}
        for name, expected_sha in source_expectations.items():
            path = repo / name
            actual_sha = sha256(path) if path.exists() else None
            match = actual_sha == expected_sha
            source_checks[name] = {
                "exists": path.exists(),
                "expected_sha256": expected_sha,
                "actual_sha256": actual_sha,
                "match": bool(match),
            }
            if not match:
                raise RuntimeError(f"Frozen source SHA mismatch: {name}")

        # ---------------------------------------------------------------------
        # Scientific fixture authority gates
        # ---------------------------------------------------------------------
        fixture_checks = {
            "dataset": {
                "path": str(dataset_path),
                "expected_sha256": DATASET_SHA,
                "actual_sha256": sha256(dataset_path) if dataset_path.exists() else None,
            },
            "b2ac_reference": {
                "path": str(reference_path),
                "expected_sha256": REFERENCE_SHA,
                "actual_sha256": sha256(reference_path) if reference_path.exists() else None,
            },
            "comp004_checkpoint_read_only_fixture": {
                "path": str(checkpoint_path),
                "expected_sha256": COMP004_CHECKPOINT_SHA,
                "actual_sha256": sha256(checkpoint_path) if checkpoint_path.exists() else None,
            },
        }

        for rec in fixture_checks.values():
            rec["match"] = rec["actual_sha256"] == rec["expected_sha256"]
            if not rec["match"]:
                raise RuntimeError(f"Fixture SHA mismatch/missing: {rec['path']}")

        # ---------------------------------------------------------------------
        # CUDA execution contract
        # ---------------------------------------------------------------------
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable.")

        gpu_name = torch.cuda.get_device_name(0)
        if "A100" not in gpu_name.upper():
            raise RuntimeError(f"A100 required for this milestone; got {gpu_name}")

        # Freeze full-FP32 semantics. No autocast is used anywhere in this file.
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.set_float32_matmul_precision("highest")

        device = torch.device("cuda:0")

        # Import exact frozen architecture/loss authorities.
        M = import_module(repo / B2C_NAME, "v16e1b2cuda1_b2c")
        J = import_module(repo / B2J_NAME, "v16e1b2cuda1_b2j")

        if int(M.SEED) != SEED:
            raise RuntimeError(f"Frozen seed mismatch: {M.SEED}")
        if int(M.LOGICAL_BATCH) != 8192:
            raise RuntimeError(f"Frozen logical batch mismatch: {M.LOGICAL_BATCH}")

        # ---------------------------------------------------------------------
        # Load immutable fixtures
        # ---------------------------------------------------------------------
        with np.load(dataset_path, allow_pickle=False) as d:
            dataset = {k: d[k].copy() for k in d.files}

        reference = torch.load(
            reference_path,
            map_location="cpu",
            weights_only=True,
        )

        checkpoint = torch.load(
            checkpoint_path,
            map_location="cpu",
            weights_only=False,
        )

        ids = reference["reference_ids"].cpu().numpy().astype(int)
        if ids.shape != (REFERENCE_MICROBATCH,):
            raise RuntimeError(
                f"Expected {REFERENCE_MICROBATCH} reference ids, got {ids.shape}."
            )
        if np.any(ids < 0) or np.any(ids >= len(dataset["xi"])):
            raise RuntimeError("Reference ids outside dataset bounds.")

        # Dataset schema is frozen for Stage-2.
        expected_schema = {
            "xi": ((14400, 64, 1), np.dtype("float32")),
            "Sw": ((14400, 64, 1), np.dtype("float32")),
            "p11": ((14400, 11), np.dtype("float32")),
            "tD": ((14400,), np.dtype("float32")),
            "ai": ((14400, 4), np.dtype("int32")),
            "at": ((14400, 4), np.dtype("float32")),
        }
        for key, (shape, dtype) in expected_schema.items():
            if key not in dataset:
                raise RuntimeError(f"Dataset key missing: {key}")
            if dataset[key].shape != shape:
                raise RuntimeError(
                    f"Dataset shape mismatch {key}: {dataset[key].shape} != {shape}"
                )
            if dataset[key].dtype != dtype:
                raise RuntimeError(
                    f"Dataset dtype mismatch {key}: {dataset[key].dtype} != {dtype}"
                )

        # ---------------------------------------------------------------------
        # CUDA snapshots
        # ---------------------------------------------------------------------
        torch.manual_seed(SEED)
        torch.cuda.manual_seed_all(SEED)

        derivative = derivative_snapshot(
            M, J, checkpoint, dataset, ids, device
        )

        # Clear the first graph before independent full-graph snapshot.
        torch.cuda.empty_cache()

        full = full_graph_snapshot(
            M, J, checkpoint, dataset, ids, device
        )

        # ---------------------------------------------------------------------
        # Reconstruct frozen reference scalar losses
        # ---------------------------------------------------------------------
        reference_losses = reconstruct_reference_losses(M, reference, dataset, ids)

        # ---------------------------------------------------------------------
        # Frozen B2AC computational-identity comparisons
        # ---------------------------------------------------------------------
        derivative_checks = {
            "S_pred_derivative": identity_compare(
                "S_pred_derivative",
                reference["S_pred_derivative"],
                derivative["S_pred"],
            ),
            "N_xi": identity_compare("N_xi", reference["N_xi"], derivative["N_xi"]),
            "N_tD": identity_compare("N_tD", reference["N_tD"], derivative["N_tD"]),
            "N_X": identity_compare("N_X", reference["N_X"], derivative["N_X"]),
        }

        full_graph_checks = {
            "S_pred_full": identity_compare(
                "S_pred_full",
                reference["S_pred_full"],
                full["S_pred"],
            ),
            "corrected_residual": identity_compare(
                "corrected_residual",
                reference["residual"],
                full["residual"],
            ),
        }

        loss_checks = {
            name: scalar_identity_compare(
                name,
                reference_losses[name],
                full["losses"][name],
            )
            for name in reference_losses
        }

        gradient_checks = gradient_compare(
            reference["parameter_gradients"],
            full["parameter_gradients"],
        )

        derivative_pass = all(v["pass"] for v in derivative_checks.values())
        full_graph_pass = all(v["pass"] for v in full_graph_checks.values())
        loss_pass = all(v["pass"] for v in loss_checks.values())
        gradients_pass = bool(gradient_checks["all_parameter_gradients_pass"])
        weights_unchanged = bool(full["weights_exactly_unchanged"])

        all_pass = bool(
            derivative_pass
            and full_graph_pass
            and loss_pass
            and gradients_pass
            and weights_unchanged
        )

        candidate_tensors = {
            "reference_ids": torch.as_tensor(ids, dtype=torch.int64),
            "S_pred_derivative": derivative["S_pred"],
            "N_xi": derivative["N_xi"],
            "N_tD": derivative["N_tD"],
            "N_X": derivative["N_X"],
            "S_pred_full": full["S_pred"],
            "residual": full["residual"],
            "parameter_gradients": full["parameter_gradients"],
        }
        atomic_torch_save(candidate_tensors, tensors_path)

        payload.update({
            "status": (
                "V16E1B2CUDA1R_A100_NATIVE_CUDA_RNN_EQUIVALENCE_REPAIR_PASS_"
                "FROZEN_B2AC_128_PROFILE_REFERENCE_REPRODUCED_WITH_K16_CUDA_FP32_"
                "B2AF_GEOMETRY_A100_REHEARSAL_AUTHORIZED_"
                "COMP005_CUDA_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
                if all_pass else
                "V16E1B2CUDA1R_A100_NATIVE_CUDA_RNN_EQUIVALENCE_REPAIR_GATE_FAILURE_"
                "B2AF_GEOMETRY_A100_REHEARSAL_BLOCKED_"
                "COMP005_CUDA_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
            ),
            "git": {
                "head": head,
                "working_tree_clean": clean,
                "parent_authority_commit": PARENT_GIT_AUTHORITY,
                "parent_authority_is_ancestor": parent_is_ancestor,
            },
            "environment": {
                "python": sys.version,
                "pytorch": torch.__version__,
                "cuda_runtime": torch.version.cuda,
                "cuda_available": torch.cuda.is_available(),
                "gpu_name": gpu_name,
                "gpu_count": torch.cuda.device_count(),
                "amp_enabled": False,
                "cuda_matmul_tf32": bool(torch.backends.cuda.matmul.allow_tf32),
                "cudnn_tf32": bool(torch.backends.cudnn.allow_tf32),
                "float32_matmul_precision": torch.get_float32_matmul_precision(),
                "cudnn_globally_available": bool(torch.backends.cudnn.is_available()),
                "recurrent_autograd_backend": (
                    "PYTORCH_NATIVE_CUDA_WITH_CUDNN_DISABLED_IN_GRAPH_CONTEXT"
                ),
                "cudnn_disabled_only_for_recurrent_graph": True,
            },
            "source_checks": source_checks,
            "fixture_checks": fixture_checks,
            "reference": {
                "profiles": REFERENCE_MICROBATCH,
                "reference_ids": [int(x) for x in ids],
                "chunk": ADOPTED_CHUNK,
                "checkpoint_used_only_as_read_only_equivalence_fixture": True,
                "checkpoint_authorized_as_COMP005_initializer": False,
            },
            "derivative_checks": derivative_checks,
            "full_graph_checks": full_graph_checks,
            "loss_checks": loss_checks,
            "parameter_gradient_checks": gradient_checks,
            "gates": {
                "derivative_equivalence_pass": derivative_pass,
                "full_graph_equivalence_pass": full_graph_pass,
                "loss_equivalence_pass": loss_pass,
                "parameter_gradient_equivalence_pass": gradients_pass,
                "weights_exactly_unchanged": weights_unchanged,
                "overall_equivalence_pass": all_pass,
            },
            "cuda_measurement": {
                "derivative_wall_seconds": derivative["wall_seconds"],
                "derivative_peak_cuda_memory_bytes": derivative["peak_cuda_memory_bytes"],
                "full_forward_plus_residual_seconds": full["forward_plus_residual_seconds"],
                "full_forward_residual_backward_seconds": full["forward_residual_backward_seconds"],
                "full_peak_cuda_memory_bytes": full["peak_cuda_memory_bytes"],
                "performance_adoption_decision": False,
                "note": (
                    "Runtime/memory are diagnostic only. This milestone does not "
                    "select or optimize an A100 execution configuration."
                ),
            },
            "reference_losses_reconstructed_from_frozen_tensors": reference_losses,
            "candidate_losses": full["losses"],
            "candidate_gradient_summary": full["gradient_summary"],
            "candidate_tensor_artifact": str(tensors_path),
            "candidate_tensor_sha256": sha256(tensors_path),
            "runner_sha256": sha256(Path(__file__).resolve()),
            "next_step": (
                "V16E1B2CUDA2_A100_B2AF_GEOMETRY_ONE_LOGICAL_BATCH_REHEARSAL"
                if all_pass else
                "OPEN_CUDA_EQUIVALENCE_DIAGNOSTIC_BRANCH_BEFORE_ANY_REHEARSAL"
            ),
        })

        atomic_json_write(payload, results_path)

        print("=" * 100)
        print("PAD-STREAM V16E-1B2CUDA1R A100 NATIVE-CUDA RNN EQUIVALENCE REPAIR")
        print("=" * 100)
        print("Git HEAD                         :", head)
        print("GPU                              :", gpu_name)
        print("Dataset SHA                      : PASS")
        print("B2AC reference SHA               : PASS")
        print("COMP004 checkpoint fixture SHA   : PASS")
        print("Frozen source authority          : PASS")
        print("Derivative equivalence           :", "PASS" if derivative_pass else "FAIL")
        print("Full-graph equivalence           :", "PASS" if full_graph_pass else "FAIL")
        print("Loss equivalence                 :", "PASS" if loss_pass else "FAIL")
        print("Parameter-gradient equivalence   :", "PASS" if gradients_pass else "FAIL")
        print("Weights exactly unchanged        :", "PASS" if weights_unchanged else "FAIL")
        print("Overall                          :", "PASS" if all_pass else "FAIL")
        print("Results                          :", results_path)
        print("Candidate tensors                :", tensors_path)
        print("Candidate tensor SHA             :", sha256(tensors_path))
        print("Status                           :", payload["status"])
        print("Next                             :", payload["next_step"])
        print("=" * 100)

        return 0 if all_pass else 3

    except BaseException as exc:
        payload.update({
            "status": (
                "V16E1B2CUDA1R_A100_NATIVE_CUDA_RNN_EQUIVALENCE_REPAIR_EXECUTION_FAILURE_"
                "ALL_DOWNSTREAM_CUDA_EXECUTION_BLOCKED_COMP005_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
            ),
            "failure_class": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "runner_sha256": sha256(Path(__file__).resolve()),
        })
        atomic_json_write(payload, failure_path)
        print(payload["traceback"], file=sys.stderr)
        print("Failure artifact:", failure_path, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
