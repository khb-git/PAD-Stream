#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2AA-XPU
Looped-VJP vs Batched-VJP Local Recurrent Derivative
Equivalence + Warmed Performance Audit

Purpose
-------
Test the first equivalence-preserving optimization authorized by V16E-1B2Z.

NO TRAINING.
NO OPTIMIZER.
NO OPTIMIZER STEP.
NO WEIGHT UPDATE.
NO CHECKPOINT MUTATION.
NO OOD.
NO TOF.

Scientific model
----------------
UNCHANGED.

The exact frozen B2S complete corrected loss path remains authoritative.
The ONLY prospective implementation change is:

    baseline:
        64 separate torch.autograd.grad VJPs

    prospective:
        one torch.autograd.grad call with is_grads_batched=True
        and 64 one-hot sequence-output cotangents

The optimized engine must recover the exact same local quantities:

    N_xi(j) = dN_j / dxi_j
    N_tD(j) = dN_j / dp11[tD]
    N_X(j)  = dN_j / dp11[xD_star]

Equivalence-first policy
------------------------
Before performance is measured, compare:

    N_xi
    N_tD
    N_X
    corrected residual
    physics loss
    complete total loss
    all model-parameter gradients after backward

using only the B2Z-frozen float32-machine-epsilon-derived computational
identity budget:

    tolerance =
        1024 * eps_float32 * max(1, max_abs(reference), max_abs(candidate))

This is an implementation-equivalence budget only.
It is NOT a scientific model threshold.

If is_grads_batched=True is unsupported on the Intel-XPU/LSTM path:
    * preserve exact runtime error
    * do NOT silently fall back
    * do NOT benchmark performance
    * do NOT authorize training

If equivalence fails:
    * preserve exact differences
    * do NOT benchmark performance
    * do NOT authorize training

If equivalence passes:
    baseline loop engine:
        1 unmeasured warm-up
        3 measured repeats

    batched VJP engine:
        1 unmeasured warm-up
        3 measured repeats

Every repeat recreates the graph, calls backward(), synchronizes XPU,
verifies finite/nonzero gradients, verifies exact weight equality, verifies
the frozen checkpoint SHA, and clears gradients.

COMP-XPU-005 full training remains blocked.
B3 remains blocked.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import math
import statistics
import sys
import time
import traceback

import numpy as np
import torch


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2AA-XPU"

REFERENCE_MICROBATCH = 128
WARMUP_REPEATS = 1
MEASURED_REPEATS = 3

FLOAT32_EPS = float(np.finfo(np.float32).eps)
IDENTITY_EPS_MULTIPLIER = 1024.0

# =============================================================================
# Frozen authority
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

# Warmed baseline.
B2Y_DIR = (
    R / "output"
    / "V16_E1B2Y_XPU_WARMED_STEADY_STATE_EXACT_GRAPH_BENCHMARK"
)
B2Y_RESULTS = B2Y_DIR / "V16E1B2Y_Warmed_Steady_State_Results.json"
B2Y_RESULTS_SHA = "32d5a9a1e8c0970a497fe81dffb5c877d8ac23439a463d701e1d9b0bcd163b16"

# B2Z authority.
B2Z_SOURCE = (
    R
    / "PAD_Stream_V16E1B2Z_XPU_B2Y_Interpretation_Derivative_Engine_Optimization_Protocol_Freeze.py"
)
B2Z_SOURCE_SHA = "9a1e36ef91799d1e6c431ea78877a98dbdaa474d6f09b2e0c958b10a0f75b6a7"

B2Z_DIR = (
    R / "output"
    / "V16_E1B2Z_XPU_B2Y_INTERPRETATION_DERIVATIVE_ENGINE_OPTIMIZATION_PROTOCOL"
)
B2Z_INTERPRETATION = B2Z_DIR / "V16E1B2Z_B2Y_Performance_Interpretation.json"
B2Z_PROTOCOL = B2Z_DIR / "V16E1B2Z_B2AA_Batched_VJP_Optimization_Protocol.json"
B2Z_HANDOFF = B2Z_DIR / "V16E1B2Z_B2AA_Handoff.md"
B2Z_SUMMARY = B2Z_DIR / "PAD_Stream_V16E1B2Z_XPU_Summary.json"

B2Z_INTERPRETATION_SHA = "6b83e5d1d72e5f01d5dd683047f9b1ffc078d88750edc3471b9563c0973df5d2"
B2Z_PROTOCOL_SHA = "f2c5c120cbacd4d5066d88a85ede85e85dcc4d389287994e902fd828f94531ef"
B2Z_HANDOFF_SHA = "37ff01b10265c88d2f9a641bc3bba87435a90a2f04f0e4619a28ccc534100a4d"
B2Z_SUMMARY_SHA = "936d32fb671f308d7118316334fbe5eecda5ad54f8f145ab3b41752896ec9567"

EXPECTED_B2Z_STATUS = (
    "V16E1B2Z_XPU_B2Y_WARMED_PERFORMANCE_INTERPRETATION_AND_DERIVATIVE_ENGINE_OPTIMIZATION_PROTOCOL_FROZEN_"
    "STEADY_STATE_CORRECTED_COST_CONFIRMED_AND_LOCAL_RECURRENT_DERIVATIVE_PLUS_SECOND_ORDER_BACKWARD_BOTTLENECK_LOCALIZED_"
    "EQUIVALENCE_PRESERVING_IMPLEMENTATION_OPTIMIZATION_REQUIRED_BEFORE_COMP_XPU_005_EXECUTION_CONTRACT_"
    "B2AA_BATCHED_VJP_IS_GRADS_BATCHED_TRUE_LOCAL_DERIVATIVE_ENGINE_EQUIVALENCE_AND_PERFORMANCE_AUDIT_AUTHORIZED_"
    "SCIENTIFIC_MODEL_RESIDUAL_LOSSES_DATASET_AND_PHYSICAL_NC_FROZEN_"
    "NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2AA_XPU_BATCHED_VJP_EQUIVALENCE_PERFORMANCE_AUDIT"
)
OUT.mkdir(parents=True, exist_ok=True)

RESULTS = OUT / "V16E1B2AA_Batched_VJP_Equivalence_Performance_Results.json"
DECISION = OUT / "V16E1B2AA_Batched_VJP_Decision.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2AA_XPU_Summary.json"


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


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sync_xpu():
    if hasattr(torch.xpu, "synchronize"):
        torch.xpu.synchronize()


def reset_peak_memory():
    if hasattr(torch.xpu, "reset_peak_memory_stats"):
        try:
            torch.xpu.reset_peak_memory_stats()
        except Exception:
            pass


def peak_memory_bytes():
    if hasattr(torch.xpu, "max_memory_allocated"):
        try:
            return int(torch.xpu.max_memory_allocated())
        except Exception:
            return None
    return None


def clear_gradients(model, xi, p11):
    for p in model.parameters():
        p.grad = None

    if xi.grad is not None:
        xi.grad = None

    if p11.grad is not None:
        p11.grad = None


def clone_parameters(model):
    return {
        name: p.detach().cpu().clone()
        for name, p in model.named_parameters()
    }


def parameters_equal(model, before):
    return all(
        torch.equal(
            p.detach().cpu(),
            before[name],
        )
        for name, p in model.named_parameters()
    )


def gradient_summary(model):
    grad_sq = 0.0
    tensor_count = 0
    nonzero_count = 0
    finite_all = True

    for p in model.parameters():
        if p.grad is None:
            continue

        tensor_count += 1
        g = p.grad.detach()

        if not torch.isfinite(g).all().item():
            finite_all = False

        if torch.count_nonzero(g).item() > 0:
            nonzero_count += 1

        grad_sq += float(
            torch.sum(g.double() ** 2).cpu()
        )

    return {
        "gradient_tensor_count":
            int(tensor_count),

        "nonzero_gradient_tensor_count":
            int(nonzero_count),

        "gradients_finite":
            bool(finite_all),

        "gradient_l2_norm":
            float(math.sqrt(max(grad_sq, 0.0))),
    }


def get_reference_ids(b2u):
    for rec in b2u.get("candidate_results", []):
        if int(rec.get("microbatch", -1)) == REFERENCE_MICROBATCH:
            ids = rec.get("dataset_indices")
            if not isinstance(ids, list) or len(ids) != REFERENCE_MICROBATCH:
                raise RuntimeError(
                    "B2U microbatch-128 dataset indices missing/incomplete."
                )
            return np.asarray(ids, dtype=int)

    raise RuntimeError("B2U microbatch-128 record not found.")


def load_model_and_batch(B2S, ids, device, suffix):
    M = B2S.import_module(
        B2S.BASE_RUNNER,
        f"b2aa_base_{suffix}",
    )

    J = B2S.import_module(
        B2S.B2J_SOURCE,
        f"b2aa_comp004_{suffix}",
    )

    d = np.load(DATASET)

    EtaModel = J.build_eta_model_class(M)

    ck = torch.load(
        COMP004_CHECKPOINT,
        map_location="cpu",
        weights_only=False,
    )

    model = EtaModel()
    model.load_state_dict(
        ck["model_state_dict"],
        strict=True,
    )
    model.to(device)
    model.train()

    xi = (
        torch.from_numpy(d["xi"][ids])
        .to(device)
        .detach()
        .clone()
        .requires_grad_(True)
    )

    Sw = torch.from_numpy(
        d["Sw"][ids]
    ).to(device)

    p11 = (
        torch.from_numpy(d["p11"][ids])
        .to(device)
        .detach()
        .clone()
        .requires_grad_(True)
    )

    ai = torch.from_numpy(
        d["ai"][ids]
    ).to(device)

    at = torch.from_numpy(
        d["at"][ids]
    ).to(device)

    return M, model, xi, Sw, p11, ai, at


# =============================================================================
# Optimized local recurrent derivative engine
# =============================================================================

def batched_local_recurrent_derivatives_create_graph(
    S_pred,
    xi,
    p11,
):
    """
    Batched equivalent of B2S.local_recurrent_derivatives_create_graph().

    Baseline output for sequence node j:
        S_pred[:,j,:].sum()

    Therefore the j-th VJP cotangent is 1 for every batch item/channel at
    sequence node j and 0 elsewhere.

    With is_grads_batched=True, grad_outputs has shape:
        [T, B, T, 1]

    where leading dimension T is the VJP batch.
    """
    if S_pred.ndim != 3:
        raise RuntimeError(
            f"Unexpected S_pred rank {S_pred.ndim}; expected [B,T,1]."
        )

    B, T, C = S_pred.shape

    if C != 1:
        raise RuntimeError(
            f"Unexpected output channels {C}; expected 1."
        )

    # 64 one-hot sequence-output cotangents, repeated across the physical batch.
    eye = torch.eye(
        T,
        dtype=S_pred.dtype,
        device=S_pred.device,
    )

    V = (
        eye[:, None, :, None]
        .expand(T, B, T, 1)
    )

    gx_batched, gp_batched = torch.autograd.grad(
        outputs=S_pred,
        inputs=(xi, p11),
        grad_outputs=V,
        retain_graph=True,
        create_graph=True,
        allow_unused=False,
        is_grads_batched=True,
    )

    # gx_batched: [T_vjp, B, T_input, 1]
    # For VJP j, recover dN_j/dxi_j from the matching input-sequence diagonal.
    j = torch.arange(
        T,
        device=S_pred.device,
    )

    N_xi = (
        gx_batched[
            j,
            :,
            j,
            0,
        ]
        .transpose(0, 1)
        .unsqueeze(-1)
    )

    # gp_batched: [T_vjp, B, 11]
    # The conditioner is shared across sequence nodes, so each VJP j directly
    # provides dN_j/dp11[tD] and dN_j/dp11[xD_star].
    N_tD = (
        gp_batched[:, :, 7]
        .transpose(0, 1)
        .unsqueeze(-1)
    )

    N_X = (
        gp_batched[:, :, 8]
        .transpose(0, 1)
        .unsqueeze(-1)
    )

    return N_xi, N_tD, N_X


# =============================================================================
# Equivalence helpers
# =============================================================================

def identity_compare(name, reference, candidate):
    a = reference.detach().float().cpu()
    b = candidate.detach().float().cpu()

    if a.shape != b.shape:
        return {
            "name": name,
            "shape_match": False,
            "reference_shape": list(a.shape),
            "candidate_shape": list(b.shape),
            "pass": False,
        }

    diff = torch.abs(a - b)

    scale = max(
        1.0,
        float(torch.max(torch.abs(a)).item()),
        float(torch.max(torch.abs(b)).item()),
    )

    bound = (
        IDENTITY_EPS_MULTIPLIER
        * FLOAT32_EPS
        * scale
    )

    max_abs = float(
        torch.max(diff).item()
    )

    return {
        "name":
            name,

        "shape_match":
            True,

        "shape":
            list(a.shape),

        "reference_max_abs":
            float(
                torch.max(
                    torch.abs(a)
                ).item()
            ),

        "candidate_max_abs":
            float(
                torch.max(
                    torch.abs(b)
                ).item()
            ),

        "max_abs_diff":
            max_abs,

        "eps_derived_bound":
            float(bound),

        "pass":
            bool(
                math.isfinite(max_abs)
                and max_abs <= bound
            ),
    }


def scalar_identity_compare(name, reference, candidate):
    a = float(reference)
    b = float(candidate)

    scale = max(
        1.0,
        abs(a),
        abs(b),
    )

    bound = (
        IDENTITY_EPS_MULTIPLIER
        * FLOAT32_EPS
        * scale
    )

    diff = abs(a - b)

    return {
        "name": name,
        "reference": a,
        "candidate": b,
        "abs_diff": float(diff),
        "eps_derived_bound": float(bound),
        "pass": bool(
            math.isfinite(diff)
            and diff <= bound
        ),
    }


def derivative_snapshot(B2S, engine, ids, device, suffix):
    M, model, xi, Sw, p11, ai, at = load_model_and_batch(
        B2S,
        ids,
        device,
        suffix,
    )

    S_pred = model(
        xi,
        p11,
    )

    N_xi, N_tD, N_X = engine(
        S_pred,
        xi,
        p11,
    )

    out = {
        "S_pred": S_pred.detach().cpu(),
        "N_xi": N_xi.detach().cpu(),
        "N_tD": N_tD.detach().cpu(),
        "N_X": N_X.detach().cpu(),
    }

    return out


def full_graph_snapshot(
    B2S,
    engine,
    ids,
    device,
    suffix,
):
    M, model, xi, Sw, p11, ai, at = load_model_and_batch(
        B2S,
        ids,
        device,
        suffix,
    )

    param_before = clone_parameters(model)

    original_engine = B2S.local_recurrent_derivatives_create_graph
    B2S.local_recurrent_derivatives_create_graph = engine

    try:
        S_pred, residual, parts = B2S.complete_corrected_total_loss(
            M,
            model,
            xi,
            Sw,
            p11,
            ai,
            at,
        )
    finally:
        B2S.local_recurrent_derivatives_create_graph = original_engine

    if not torch.isfinite(S_pred).all().item():
        raise RuntimeError(
            f"{suffix}: nonfinite prediction."
        )

    if not torch.isfinite(residual).all().item():
        raise RuntimeError(
            f"{suffix}: nonfinite corrected residual."
        )

    if not all(
        torch.isfinite(v).all().item()
        for v in parts.values()
    ):
        raise RuntimeError(
            f"{suffix}: nonfinite loss."
        )

    parts["total"].backward()
    sync_xpu()

    grads = {}
    grad_summary = gradient_summary(model)

    if not grad_summary["gradients_finite"]:
        raise RuntimeError(
            f"{suffix}: nonfinite model gradients."
        )

    for name, p in model.named_parameters():
        if p.grad is None:
            grads[name] = None
        else:
            grads[name] = p.grad.detach().cpu().clone()

    if not parameters_equal(
        model,
        param_before,
    ):
        raise RuntimeError(
            f"{suffix}: parameter value changed without optimizer."
        )

    if sha256(COMP004_CHECKPOINT) != COMP004_CHECKPOINT_SHA:
        raise RuntimeError(
            f"{suffix}: frozen checkpoint SHA changed."
        )

    return {
        "S_pred":
            S_pred.detach().cpu(),

        "residual":
            residual.detach().cpu(),

        "losses": {
            k: float(v.detach().cpu())
            for k, v in parts.items()
        },

        "parameter_gradients":
            grads,

        "gradient_summary":
            grad_summary,

        "weights_exactly_unchanged":
            True,

        "checkpoint_SHA_unchanged":
            True,
    }


def compare_parameter_gradients(reference, candidate):
    names = sorted(
        set(reference.keys())
        | set(candidate.keys())
    )

    records = []
    all_pass = True

    for name in names:
        a = reference.get(name)
        b = candidate.get(name)

        if a is None or b is None:
            same_none = (
                a is None
                and b is None
            )

            rec = {
                "name":
                    name,

                "both_none":
                    same_none,

                "pass":
                    bool(same_none),
            }
        else:
            rec = identity_compare(
                name,
                a,
                b,
            )

        records.append(rec)
        all_pass &= bool(rec["pass"])

    return {
        "all_parameter_gradients_pass":
            bool(all_pass),

        "records":
            records,
    }


# =============================================================================
# Warmed performance helper
# =============================================================================

def performance_iteration(
    B2S,
    engine,
    M,
    model,
    xi,
    Sw,
    p11,
    ai,
    at,
    param_before,
):
    clear_gradients(
        model,
        xi,
        p11,
    )

    reset_peak_memory()
    sync_xpu()

    original_engine = B2S.local_recurrent_derivatives_create_graph
    B2S.local_recurrent_derivatives_create_graph = engine

    try:
        t0 = time.perf_counter()

        S_pred, residual, parts = B2S.complete_corrected_total_loss(
            M,
            model,
            xi,
            Sw,
            p11,
            ai,
            at,
        )

        if not torch.isfinite(S_pred).all().item():
            raise RuntimeError(
                "Performance iteration: nonfinite prediction."
            )

        if not torch.isfinite(residual).all().item():
            raise RuntimeError(
                "Performance iteration: nonfinite residual."
            )

        if not all(
            torch.isfinite(v).all().item()
            for v in parts.values()
        ):
            raise RuntimeError(
                "Performance iteration: nonfinite loss."
            )

        parts["total"].backward()

        sync_xpu()

        elapsed = (
            time.perf_counter()
            - t0
        )

    finally:
        B2S.local_recurrent_derivatives_create_graph = original_engine

    grads = gradient_summary(
        model
    )

    if not grads["gradients_finite"]:
        raise RuntimeError(
            "Performance iteration: nonfinite gradients."
        )

    if grads["nonzero_gradient_tensor_count"] <= 0:
        raise RuntimeError(
            "Performance iteration: no nonzero parameter gradients."
        )

    if not parameters_equal(
        model,
        param_before,
    ):
        raise RuntimeError(
            "Performance iteration changed parameter values."
        )

    if sha256(COMP004_CHECKPOINT) != COMP004_CHECKPOINT_SHA:
        raise RuntimeError(
            "Performance iteration changed frozen checkpoint SHA."
        )

    rec = {
        "wall_seconds":
            float(elapsed),

        "profiles_per_second":
            float(
                REFERENCE_MICROBATCH
                / elapsed
            ),

        "gradient_summary":
            grads,

        "weights_exactly_unchanged":
            True,

        "checkpoint_SHA_unchanged":
            True,

        "peak_xpu_memory_bytes":
            peak_memory_bytes(),

        "total_loss":
            float(
                parts["total"].detach().cpu()
            ),

        "physics_loss":
            float(
                parts["physics"].detach().cpu()
            ),
    }

    clear_gradients(
        model,
        xi,
        p11,
    )

    return rec


def warmed_performance_block(
    B2S,
    engine,
    ids,
    device,
    suffix,
):
    M, model, xi, Sw, p11, ai, at = load_model_and_batch(
        B2S,
        ids,
        device,
        suffix,
    )

    param_before = clone_parameters(
        model
    )

    warmup = performance_iteration(
        B2S,
        engine,
        M,
        model,
        xi,
        Sw,
        p11,
        ai,
        at,
        param_before,
    )

    repeats = []

    for _ in range(
        MEASURED_REPEATS
    ):
        repeats.append(
            performance_iteration(
                B2S,
                engine,
                M,
                model,
                xi,
                Sw,
                p11,
                ai,
                at,
                param_before,
            )
        )

    times = [
        float(rec["wall_seconds"])
        for rec in repeats
    ]

    median_s = float(
        statistics.median(
            times
        )
    )

    mean_s = float(
        statistics.mean(
            times
        )
    )

    return {
        "warmup":
            warmup,

        "measured_repeats":
            repeats,

        "wall_times_seconds":
            times,

        "median_wall_seconds":
            median_s,

        "mean_wall_seconds":
            mean_s,

        "median_profiles_per_second":
            float(
                REFERENCE_MICROBATCH
                / median_s
            ),
    }


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2AA-XPU")
    print("Looped-VJP vs Batched-VJP Derivative Engine")
    print("Equivalence + Warmed Performance Audit")
    print("=" * 80)
    print("NO TRAINING — NO OPTIMIZER — NO WEIGHT UPDATE.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2AA summary already exists; refusing overwrite."
        )

    gates = {
        "dataset_SHA_exact":
            exact(
                DATASET,
                DATASET_SHA,
            ),

        "COMP004_checkpoint_SHA_exact":
            exact(
                COMP004_CHECKPOINT,
                COMP004_CHECKPOINT_SHA,
            ),

        "B2S_source_SHA_exact":
            exact(
                B2S_SOURCE,
                B2S_SOURCE_SHA,
            ),

        "B2U_results_SHA_exact":
            exact(
                B2U_RESULTS,
                B2U_RESULTS_SHA,
            ),

        "B2Y_results_SHA_exact":
            exact(
                B2Y_RESULTS,
                B2Y_RESULTS_SHA,
            ),

        "B2Z_source_SHA_exact":
            exact(
                B2Z_SOURCE,
                B2Z_SOURCE_SHA,
            ),

        "B2Z_interpretation_SHA_exact":
            exact(
                B2Z_INTERPRETATION,
                B2Z_INTERPRETATION_SHA,
            ),

        "B2Z_protocol_SHA_exact":
            exact(
                B2Z_PROTOCOL,
                B2Z_PROTOCOL_SHA,
            ),

        "B2Z_handoff_SHA_exact":
            exact(
                B2Z_HANDOFF,
                B2Z_HANDOFF_SHA,
            ),

        "B2Z_summary_SHA_exact":
            exact(
                B2Z_SUMMARY,
                B2Z_SUMMARY_SHA,
            ),
    }

    b2u = (
        read_json(
            B2U_RESULTS
        )
        if B2U_RESULTS.exists()
        else {}
    )

    b2y = (
        read_json(
            B2Y_RESULTS
        )
        if B2Y_RESULTS.exists()
        else {}
    )

    b2z = (
        read_json(
            B2Z_SUMMARY
        )
        if B2Z_SUMMARY.exists()
        else {}
    )

    b2z_protocol = (
        read_json(
            B2Z_PROTOCOL
        )
        if B2Z_PROTOCOL.exists()
        else {}
    )

    gates.update({
        "B2Z_status_exact":
            b2z.get(
                "status"
            )
            == EXPECTED_B2Z_STATUS,

        "B2Z_reference_microbatch_128":
            b2z.get(
                "reference_microbatch"
            )
            == REFERENCE_MICROBATCH,

        "B2Z_B2AA_true":
            b2z.get(
                "B2AA_authorized"
            )
            is True,

        "B2Z_training_false":
            b2z.get(
                "COMP_XPU_005_full_training_authorized"
            )
            is False,

        "B2Z_B3_false":
            b2z.get(
                "B3_authorized"
            )
            is False,

        "B2Z_protocol_next_exact":
            b2z_protocol.get(
                "authorized_next_milestone"
            )
            == MILESTONE,

        "B2Z_protocol_reference_128":
            (
                b2z_protocol
                .get("reference", {})
                .get("microbatch")
                == REFERENCE_MICROBATCH
            ),

        "B2Z_identity_epsilon_exact":
            (
                b2z_protocol
                .get("equivalence_verification", {})
                .get("identity_budget", {})
                .get("float32_epsilon")
                == FLOAT32_EPS
            ),

        "B2Z_identity_multiplier_1024":
            (
                b2z_protocol
                .get("equivalence_verification", {})
                .get("identity_budget", {})
                .get("multiplier")
                == IDENTITY_EPS_MULTIPLIER
            ),

        "B2Z_training_firewall_false":
            (
                b2z_protocol
                .get("scientific_firewall", {})
                .get("training")
                is False
            ),

        "B2Z_optimizer_firewall_false":
            (
                b2z_protocol
                .get("scientific_firewall", {})
                .get("optimizer")
                is False
            ),

        "B2Z_weight_update_firewall_false":
            (
                b2z_protocol
                .get("scientific_firewall", {})
                .get("weight_update")
                is False
            ),
    })

    ids = get_reference_ids(
        b2u
    )

    b2y_ids = (
        b2y.get("reference", {})
        .get("dataset_indices")
    )

    gates.update({
        "reference_ids_128":
            len(ids)
            == REFERENCE_MICROBATCH,

        "B2Y_reference_ids_match":
            [int(x) for x in ids]
            == b2y_ids,
    })

    print("AUTHORITY / OPTIMIZATION-PROTOCOL GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    if not all(
        gates.values()
    ):
        raise RuntimeError(
            "B2AA blocked by authority/protocol mismatch."
        )

    if not torch.xpu.is_available():
        raise RuntimeError(
            "Intel XPU unavailable for B2AA."
        )

    B2S = import_module(
        B2S_SOURCE,
        "v16e1b2s_exact_graph_b2aa",
    )

    baseline_engine = (
        B2S.local_recurrent_derivatives_create_graph
    )

    device = torch.device(
        "xpu"
    )

    # =========================================================================
    # 1. Derivative-engine equivalence.
    # =========================================================================

    print("\nDERIVATIVE TENSOR EQUIVALENCE")

    baseline_derivatives = derivative_snapshot(
        B2S,
        baseline_engine,
        ids,
        device,
        "derivative_loop",
    )

    try:
        batched_derivatives = derivative_snapshot(
            B2S,
            batched_local_recurrent_derivatives_create_graph,
            ids,
            device,
            "derivative_batched",
        )
    except BaseException as exc:
        runtime_error = (
            f"{type(exc).__name__}: {exc}"
        )

        results_payload = {
            "milestone":
                MILESTONE,

            "classification":
                "BATCHED_VJP_OPERATIONAL_RUNTIME_FAILURE",

            "authority_gates":
                {
                    k: bool(v)
                    for k, v in gates.items()
                },

            "batched_vjp_supported":
                False,

            "runtime_error":
                runtime_error,

            "traceback":
                traceback.format_exc(),

            "fallback_used":
                False,

            "performance_benchmark_run":
                False,

            "optimizer_created":
                False,

            "optimizer_step":
                False,

            "weight_update":
                False,

            "checkpoint_mutated":
                False,

            "COMP_XPU_005_full_training_authorized":
                False,

            "B3_authorized":
                False,
        }

        RESULTS.write_text(
            json.dumps(
                results_payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        decision_payload = {
            "milestone":
                MILESTONE,

            "batched_vjp_adoptable":
                False,

            "reason":
                "is_grads_batched=True path produced a runtime failure on the "
                "frozen Intel-XPU/LSTM graph.",

            "runtime_error":
                runtime_error,

            "fallback_used":
                False,

            "next_decision_required":
                "V16E-1B2AB-XPU must interpret the exact runtime incompatibility "
                "and select the next equivalence-preserving implementation route.",

            "COMP_XPU_005_full_training_authorized":
                False,

            "B3_authorized":
                False,
        }

        DECISION.write_text(
            json.dumps(
                decision_payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        status = (
            "V16E1B2AA_XPU_BATCHED_VJP_EQUIVALENCE_AUDIT_COMPLETE_"
            "IS_GRADS_BATCHED_TRUE_RUNTIME_FAILURE_RECORDED_EXACTLY_NO_FALLBACK_"
            "SCIENTIFIC_GRAPH_COMP_XPU_004_CHECKPOINT_AND_NO_UPDATE_FIREWALL_PRESERVED_"
            "PERFORMANCE_BENCHMARK_NOT_RUN_B2AB_IMPLEMENTATION_INTERPRETATION_REQUIRED_"
            "COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
        )

        summary_payload = {
            "milestone":
                MILESTONE,

            "status":
                status,

            "results_sha256":
                sha256(
                    RESULTS
                ),

            "decision_sha256":
                sha256(
                    DECISION
                ),

            "batched_vjp_supported":
                False,

            "equivalence_pass":
                False,

            "performance_benchmark_run":
                False,

            "COMP_XPU_005_full_training_authorized":
                False,

            "B3_authorized":
                False,

            "next_milestone":
                "V16E-1B2AB-XPU — interpret batched-VJP runtime incompatibility "
                "and freeze the next equivalence-preserving derivative-engine route",

            "gates":
                {
                    **{
                        k: bool(v)
                        for k, v
                        in gates.items()
                    },

                    "runtime_failure_recorded":
                        True,

                    "no_fallback":
                        True,

                    "no_training":
                        True,

                    "no_optimizer":
                        True,

                    "no_optimizer_step":
                        True,

                    "no_weight_update":
                        True,

                    "COMP004_checkpoint_still_unchanged":
                        sha256(
                            COMP004_CHECKPOINT
                        )
                        == COMP004_CHECKPOINT_SHA,
                },
        }

        SUMMARY.write_text(
            json.dumps(
                summary_payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        print("\nBATCHED-VJP RUNTIME RESULT")
        print("  supported : NO")
        print("  error     :", runtime_error)
        print("  fallback  : NONE")

        print("\nSTATUS")
        print(" ", status)

        print("\nHASHES")
        print("  Results :", sha256(RESULTS))
        print("  Decision:", sha256(DECISION))
        print("  Summary :", sha256(SUMMARY))

        print("\nNEXT")
        print(" ", summary_payload["next_milestone"])
        return

    derivative_checks = {
        "S_pred":
            identity_compare(
                "S_pred",
                baseline_derivatives["S_pred"],
                batched_derivatives["S_pred"],
            ),

        "N_xi":
            identity_compare(
                "N_xi",
                baseline_derivatives["N_xi"],
                batched_derivatives["N_xi"],
            ),

        "N_tD":
            identity_compare(
                "N_tD",
                baseline_derivatives["N_tD"],
                batched_derivatives["N_tD"],
            ),

        "N_X":
            identity_compare(
                "N_X",
                baseline_derivatives["N_X"],
                batched_derivatives["N_X"],
            ),
    }

    for name, rec in derivative_checks.items():
        print(
            f"  {name:6s} "
            f"| maxdiff={rec['max_abs_diff']:.6e} "
            f"| bound={rec['eps_derived_bound']:.6e} "
            f"| {'PASS' if rec['pass'] else 'FAIL'}"
        )

    derivative_equivalence_pass = all(
        rec["pass"]
        for rec in derivative_checks.values()
    )

    if not derivative_equivalence_pass:
        results_payload = {
            "milestone":
                MILESTONE,

            "classification":
                "BATCHED_VJP_DERIVATIVE_EQUIVALENCE_FAILURE",

            "batched_vjp_supported":
                True,

            "derivative_checks":
                derivative_checks,

            "equivalence_pass":
                False,

            "performance_benchmark_run":
                False,

            "fallback_used":
                False,

            "optimizer_created":
                False,

            "weight_update":
                False,

            "COMP_XPU_005_full_training_authorized":
                False,

            "B3_authorized":
                False,
        }

        RESULTS.write_text(
            json.dumps(
                results_payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        decision_payload = {
            "milestone":
                MILESTONE,

            "batched_vjp_adoptable":
                False,

            "reason":
                "Local derivative tensors exceeded the frozen computational "
                "identity budget.",

            "performance_benchmark_run":
                False,

            "next_decision_required":
                "V16E-1B2AB-XPU must interpret the derivative-equivalence failure.",

            "COMP_XPU_005_full_training_authorized":
                False,

            "B3_authorized":
                False,
        }

        DECISION.write_text(
            json.dumps(
                decision_payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        status = (
            "V16E1B2AA_XPU_BATCHED_VJP_DERIVATIVE_EQUIVALENCE_AUDIT_COMPLETE_"
            "IS_GRADS_BATCHED_TRUE_RUNTIME_SUPPORTED_BUT_LOCAL_DERIVATIVE_IDENTITY_BUDGET_FAILED_"
            "PERFORMANCE_BENCHMARK_NOT_RUN_NO_FALLBACK_NO_TRAINING_NO_WEIGHT_CHANGE_"
            "B2AB_IMPLEMENTATION_INTERPRETATION_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
        )

        summary_payload = {
            "milestone":
                MILESTONE,

            "status":
                status,

            "results_sha256":
                sha256(
                    RESULTS
                ),

            "decision_sha256":
                sha256(
                    DECISION
                ),

            "batched_vjp_supported":
                True,

            "equivalence_pass":
                False,

            "performance_benchmark_run":
                False,

            "COMP_XPU_005_full_training_authorized":
                False,

            "B3_authorized":
                False,

            "next_milestone":
                "V16E-1B2AB-XPU — interpret batched-VJP derivative-equivalence failure",

            "gates":
                {
                    **{
                        k: bool(v)
                        for k, v
                        in gates.items()
                    },

                    "batched_runtime_supported":
                        True,

                    "derivative_equivalence_pass":
                        False,

                    "performance_skipped_as_required":
                        True,

                    "no_training":
                        True,

                    "no_optimizer":
                        True,

                    "no_weight_update":
                        True,
                },
        }

        SUMMARY.write_text(
            json.dumps(
                summary_payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        print("\nSTATUS")
        print(" ", status)

        print("\nNEXT")
        print(" ", summary_payload["next_milestone"])
        return

    # =========================================================================
    # 2. Full corrected graph and parameter-gradient equivalence.
    # =========================================================================

    print("\nFULL CORRECTED GRAPH EQUIVALENCE")

    baseline_full = full_graph_snapshot(
        B2S,
        baseline_engine,
        ids,
        device,
        "full_loop",
    )

    batched_full = full_graph_snapshot(
        B2S,
        batched_local_recurrent_derivatives_create_graph,
        ids,
        device,
        "full_batched",
    )

    full_checks = {
        "S_pred":
            identity_compare(
                "S_pred",
                baseline_full["S_pred"],
                batched_full["S_pred"],
            ),

        "corrected_residual":
            identity_compare(
                "corrected_residual",
                baseline_full["residual"],
                batched_full["residual"],
            ),

        "physics_loss":
            scalar_identity_compare(
                "physics_loss",
                baseline_full["losses"]["physics"],
                batched_full["losses"]["physics"],
            ),

        "total_loss":
            scalar_identity_compare(
                "total_loss",
                baseline_full["losses"]["total"],
                batched_full["losses"]["total"],
            ),
    }

    gradient_checks = compare_parameter_gradients(
        baseline_full[
            "parameter_gradients"
        ],
        batched_full[
            "parameter_gradients"
        ],
    )

    for name, rec in full_checks.items():
        if "max_abs_diff" in rec:
            print(
                f"  {name:20s} "
                f"| maxdiff={rec['max_abs_diff']:.6e} "
                f"| bound={rec['eps_derived_bound']:.6e} "
                f"| {'PASS' if rec['pass'] else 'FAIL'}"
            )
        else:
            print(
                f"  {name:20s} "
                f"| diff={rec['abs_diff']:.6e} "
                f"| bound={rec['eps_derived_bound']:.6e} "
                f"| {'PASS' if rec['pass'] else 'FAIL'}"
            )

    print(
        "  parameter gradients   |",
        "PASS"
        if gradient_checks[
            "all_parameter_gradients_pass"
        ]
        else "FAIL",
    )

    full_equivalence_pass = (
        all(
            rec["pass"]
            for rec in full_checks.values()
        )
        and gradient_checks[
            "all_parameter_gradients_pass"
        ]
    )

    if not full_equivalence_pass:
        results_payload = {
            "milestone":
                MILESTONE,

            "classification":
                "BATCHED_VJP_FULL_GRAPH_EQUIVALENCE_FAILURE",

            "batched_vjp_supported":
                True,

            "derivative_checks":
                derivative_checks,

            "full_graph_checks":
                full_checks,

            "parameter_gradient_checks":
                gradient_checks,

            "equivalence_pass":
                False,

            "performance_benchmark_run":
                False,

            "fallback_used":
                False,

            "optimizer_created":
                False,

            "weight_update":
                False,

            "COMP_XPU_005_full_training_authorized":
                False,

            "B3_authorized":
                False,
        }

        RESULTS.write_text(
            json.dumps(
                results_payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        DECISION.write_text(
            json.dumps(
                {
                    "milestone":
                        MILESTONE,

                    "batched_vjp_adoptable":
                        False,

                    "reason":
                        "Full corrected graph or model-parameter gradients exceeded "
                        "the frozen computational identity budget.",

                    "performance_benchmark_run":
                        False,

                    "COMP_XPU_005_full_training_authorized":
                        False,

                    "B3_authorized":
                        False,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        status = (
            "V16E1B2AA_XPU_BATCHED_VJP_FULL_GRAPH_EQUIVALENCE_AUDIT_COMPLETE_"
            "LOCAL_DERIVATIVES_PASSED_BUT_CORRECTED_RESIDUAL_LOSS_OR_PARAMETER_GRADIENT_IDENTITY_FAILED_"
            "PERFORMANCE_BENCHMARK_NOT_RUN_NO_FALLBACK_NO_TRAINING_NO_WEIGHT_CHANGE_"
            "B2AB_IMPLEMENTATION_INTERPRETATION_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
        )

        SUMMARY.write_text(
            json.dumps(
                {
                    "milestone":
                        MILESTONE,

                    "status":
                        status,

                    "results_sha256":
                        sha256(
                            RESULTS
                        ),

                    "decision_sha256":
                        sha256(
                            DECISION
                        ),

                    "batched_vjp_supported":
                        True,

                    "equivalence_pass":
                        False,

                    "performance_benchmark_run":
                        False,

                    "COMP_XPU_005_full_training_authorized":
                        False,

                    "B3_authorized":
                        False,

                    "next_milestone":
                        "V16E-1B2AB-XPU — interpret batched-VJP full-graph equivalence failure",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        print("\nSTATUS")
        print(" ", status)
        return

    # =========================================================================
    # 3. Warmed performance only after equivalence passes.
    # =========================================================================

    print("\nWARMED PERFORMANCE — LOOPED VJP")

    loop_perf = warmed_performance_block(
        B2S,
        baseline_engine,
        ids,
        device,
        "perf_loop",
    )

    print(
        "  times :",
        " / ".join(
            f"{x:.3f}s"
            for x in loop_perf[
                "wall_times_seconds"
            ]
        ),
    )
    print(
        "  median:",
        f"{loop_perf['median_wall_seconds']:.3f}s",
        "| throughput:",
        f"{loop_perf['median_profiles_per_second']:.3f} profiles/s",
    )

    print("\nWARMED PERFORMANCE — BATCHED VJP")

    batched_perf = warmed_performance_block(
        B2S,
        batched_local_recurrent_derivatives_create_graph,
        ids,
        device,
        "perf_batched",
    )

    print(
        "  times :",
        " / ".join(
            f"{x:.3f}s"
            for x in batched_perf[
                "wall_times_seconds"
            ]
        ),
    )
    print(
        "  median:",
        f"{batched_perf['median_wall_seconds']:.3f}s",
        "| throughput:",
        f"{batched_perf['median_profiles_per_second']:.3f} profiles/s",
    )

    loop_median = float(
        loop_perf[
            "median_wall_seconds"
        ]
    )

    batched_median = float(
        batched_perf[
            "median_wall_seconds"
        ]
    )

    speed_ratio_loop_over_batched = float(
        loop_median
        / max(
            batched_median,
            1e-30,
        )
    )

    throughput_ratio = float(
        batched_perf[
            "median_profiles_per_second"
        ]
        / max(
            loop_perf[
                "median_profiles_per_second"
            ],
            1e-30,
        )
    )

    results_payload = {
        "milestone":
            MILESTONE,

        "classification":
            "BATCHED_VJP_EQUIVALENCE_AND_WARMED_PERFORMANCE_AUDIT",

        "reference": {
            "microbatch":
                REFERENCE_MICROBATCH,

            "dataset_indices":
                [int(x) for x in ids],

            "checkpoint_sha256":
                COMP004_CHECKPOINT_SHA,

            "exact_B2S_source_sha256":
                B2S_SOURCE_SHA,
        },

        "batched_vjp_supported":
            True,

        "identity_budget": {
            "float32_epsilon":
                FLOAT32_EPS,

            "multiplier":
                IDENTITY_EPS_MULTIPLIER,

            "semantics":
                "computational implementation-equivalence only",
        },

        "derivative_checks":
            derivative_checks,

        "full_graph_checks":
            full_checks,

        "parameter_gradient_checks":
            gradient_checks,

        "equivalence_pass":
            True,

        "performance": {
            "looped_vjp":
                loop_perf,

            "batched_vjp":
                batched_perf,

            "loop_median_over_batched_median":
                speed_ratio_loop_over_batched,

            "batched_throughput_over_loop_throughput":
                throughput_ratio,
        },

        "optimizer_created":
            False,

        "optimizer_step":
            False,

        "weight_update":
            False,

        "checkpoint_mutated":
            False,

        "scientific_graph_changed":
            False,

        "fallback_used":
            False,

        "OOD_used":
            False,

        "TOF_used":
            False,

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,
    }

    RESULTS.write_text(
        json.dumps(
            results_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    decision_payload = {
        "milestone":
            MILESTONE,

        "batched_vjp_supported":
            True,

        "equivalence_pass":
            True,

        "loop_median_seconds":
            loop_median,

        "batched_median_seconds":
            batched_median,

        "loop_median_over_batched_median":
            speed_ratio_loop_over_batched,

        "batched_throughput_over_loop_throughput":
            throughput_ratio,

        "batched_vjp_adoptable":
            False,

        "reason_not_yet_adopted":
            "B2AA freezes equivalence and measured performance only. "
            "B2AB must interpret whether the implementation should be adopted "
            "for the COMP-XPU-005 execution branch.",

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,
    }

    DECISION.write_text(
        json.dumps(
            decision_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    final_gates = {
        **gates,

        "batched_runtime_supported":
            True,

        "derivative_equivalence_pass":
            derivative_equivalence_pass,

        "full_graph_equivalence_pass":
            full_equivalence_pass,

        "parameter_gradient_equivalence_pass":
            gradient_checks[
                "all_parameter_gradients_pass"
            ],

        "loop_three_measured_repeats":
            len(
                loop_perf[
                    "measured_repeats"
                ]
            )
            == MEASURED_REPEATS,

        "batched_three_measured_repeats":
            len(
                batched_perf[
                    "measured_repeats"
                ]
            )
            == MEASURED_REPEATS,

        "loop_times_finite":
            all(
                math.isfinite(x)
                for x in loop_perf[
                    "wall_times_seconds"
                ]
            ),

        "batched_times_finite":
            all(
                math.isfinite(x)
                for x in batched_perf[
                    "wall_times_seconds"
                ]
            ),

        "COMP004_checkpoint_still_unchanged":
            sha256(
                COMP004_CHECKPOINT
            )
            == COMP004_CHECKPOINT_SHA,

        "results_written":
            RESULTS.exists()
            and RESULTS.stat().st_size > 0,

        "decision_written":
            DECISION.exists()
            and DECISION.stat().st_size > 0,

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
    }

    ok = all(
        bool(v)
        for v in final_gates.values()
    )

    status = (
        "V16E1B2AA_XPU_BATCHED_VJP_LOCAL_RECURRENT_DERIVATIVE_EQUIVALENCE_AND_WARMED_PERFORMANCE_AUDIT_COMPLETE_"
        "IS_GRADS_BATCHED_TRUE_RUNTIME_SUPPORTED_N_XI_N_TD_N_X_CORRECTED_RESIDUAL_PHYSICS_LOSS_TOTAL_LOSS_AND_PARAMETER_GRADIENTS_"
        "WITHIN_FROZEN_FLOAT32_MACHINE_EPSILON_DERIVED_IMPLEMENTATION_IDENTITY_BUDGET_"
        "ONE_WARMUP_THREE_MEASURED_LOOPED_AND_BATCHED_VJP_REPEATS_COMPLETE_"
        "PERFORMANCE_RESULTS_FROZEN_NO_SCIENTIFIC_GRAPH_CHANGE_NO_FALLBACK_NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_"
        "COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_B2AB_ADOPTION_INTERPRETATION_REQUIRED_"
        "COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2AA_XPU_BATCHED_VJP_AUDIT_COMPLETED_WITH_GATE_FAILURE"
    )

    summary_payload = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "results_sha256":
            sha256(
                RESULTS
            ),

        "decision_sha256":
            sha256(
                DECISION
            ),

        "reference_microbatch":
            REFERENCE_MICROBATCH,

        "batched_vjp_supported":
            True,

        "equivalence_pass":
            True,

        "loop_median_seconds":
            loop_median,

        "batched_median_seconds":
            batched_median,

        "loop_median_over_batched_median":
            speed_ratio_loop_over_batched,

        "loop_median_profiles_per_second":
            float(
                loop_perf[
                    "median_profiles_per_second"
                ]
            ),

        "batched_median_profiles_per_second":
            float(
                batched_perf[
                    "median_profiles_per_second"
                ]
            ),

        "performance_benchmark_run":
            True,

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2AB-XPU — interpret batched-VJP equivalence and warmed "
                "performance; decide whether to adopt the optimized derivative engine "
                "for the prospective COMP-XPU-005 execution branch"
                if ok else
                "V16E-1B2AA-R1 — diagnose batched-VJP audit gate failure"
            ),

        "gates":
            {
                k: bool(v)
                for k, v in final_gates.items()
            },
    }

    SUMMARY.write_text(
        json.dumps(
            summary_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nPERFORMANCE COMPARISON")
    print(
        "  loop median    :",
        f"{loop_median:.3f}s",
    )
    print(
        "  batched median :",
        f"{batched_median:.3f}s",
    )
    print(
        "  loop/batched   :",
        f"{speed_ratio_loop_over_batched:.3f}x",
    )
    print(
        "  throughput gain:",
        f"{throughput_ratio:.3f}x",
    )

    print("\nFINAL GATES")
    for k, v in final_gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Results :", sha256(RESULTS))
    print("  Decision:", sha256(DECISION))
    print("  Summary :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary_payload["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
