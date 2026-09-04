#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2S-XPU
Corrected Conservative Stage-2 Residual Backward Feasibility Benchmark

Purpose
-------
Benchmark the exact corrected Stage-2 physics-loss derivative graph on the
user's Intel XPU BEFORE any corrected training is authorized.

NO OPTIMIZER.
NO OPTIMIZER STEP.
NO WEIGHT UPDATE.
NO CHECKPOINT MUTATION.
NO OOD.
NO TOF.

Authority
---------
V16E-1B2R authorizes only this feasibility benchmark.

Prospective corrected model:
    V16E-BLREP-COMP-XPU-005

Frozen baseline model loaded for the benchmark:
    V16E-BLREP-COMP-XPU-004

Scientific change under feasibility test:
    Replace the old algebraic characteristic physics loss with the corrected
    conservative moving-fan residual:

        R_cons =
            N_tD
            + Xdot*N_X
            + [uD*fw'(N)/X - xi*Xdot/X] * N_xi
            + Nc*uD*fw(N)

        uD = exp(Nc*xi*X)

        Xdot = exp(Nc*X) * sigma_BL

        sigma_BL =
            [fw(Sw_star)-fw(swc)] / [Sw_star-swc]

The residual uses interior fan nodes only.

Training-graph requirement
--------------------------
The benchmark computes local recurrent derivatives with create_graph=True:

    N_xi(j) = dN_j/dxi_j
    N_tD(j) = dN_j/dp11[tD]
    N_X(j)  = dN_j/dp11[xD_star]

then forms the COMPLETE frozen Stage-2 total loss:

    lambda_data   * L_data
  + lambda_phys   * L_corrected_physics
  + lambda_bc     * L_injector
  + lambda_tip    * L_tip
  + lambda_anchor * L_anchor
  + lambda_mono   * L_monotonicity

and calls total.backward().

Gradients are inspected and immediately discarded.
No optimizer object is created.

Candidate microbatches
----------------------
    1, 2, 4, 8, 16

Each candidate runs in a separate Python subprocess / XPU context so that an
OOM or device-loss event cannot invalidate successful smaller candidates or
mutate the frozen checkpoint.

Selection rule
--------------
Select the largest TESTED candidate that completes:
    * finite forward prediction
    * finite corrected residual
    * finite complete total loss
    * backward()
    * XPU synchronization
    * finite parameter gradients
    * exact in-memory parameter equality before/after backward
    * unchanged checkpoint SHA

This is an operational selection rule only.
No scientific numerical acceptance threshold is introduced.

B3 remains blocked.
Corrected 800-epoch training remains blocked pending a later B2T protocol freeze.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import copy
import gc
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


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2S-XPU"

CANDIDATES = [1, 2, 4, 8, 16]
NC_VALUES = [0.0, 0.05, 0.10, 0.20, 0.30]
SEED = 1337

# =============================================================================
# Frozen authority
# =============================================================================

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

BASE_RUNNER = (
    R
    / "PAD_Stream_V16E1B2C_XPU_COMP_XPU_002_800Epoch_Compressible_Reproduction.py"
)
BASE_RUNNER_SHA = "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18"

B2J_SOURCE = (
    R
    / "PAD_Stream_V16E1B2J_XPU_COMP_XPU_004_Physics_Aware_Nc_Coordinate_Channel_Reproduction.py"
)
B2J_SOURCE_SHA = "fcc4074863a46f6b8d356a01ff0b4b2182d0ffa3ebc9b3fd053e35282f897a4c"

B2O_DIR = (
    R / "output"
    / "V16_E1B2O_XPU_CONSERVATIVE_RESIDUAL_AUTOGRAD_VERIFICATION"
)
B2O_AUTOGRAD = B2O_DIR / "V16E1B2O_COMP004_Autograd_Residual_Form_Verification.json"
B2O_AUTOGRAD_SHA = "fb347b81ece990860e2caf599e9d276296a833f800b3c881dfec5235f76bb39e"

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
COMP004_MANIFEST = COMP004_DIR / "V16E_BLREP_COMP_XPU_004_Manifest.json"
COMP004_MANIFEST_SHA = "989d3aaca374b44a9f6f9d0a35b9b0ddf8a86b3665e5b58f9bbb4f97ad08add7"
COMP004_SUMMARY = COMP004_DIR / "PAD_Stream_V16E1B2J_XPU_Summary.json"
COMP004_SUMMARY_SHA = "d4fc1de7a0257be90f2629e7e1469a30f2e7011d5586e32799f9c2f7338658b0"

# B2R authority
B2R_SOURCE = (
    R
    / "PAD_Stream_V16E1B2R_XPU_B2Q_Interpretation_Corrected_Stage2_Feasibility_Protocol_Freeze.py"
)
B2R_SOURCE_SHA = "a80f0be6d98ebfaf29b609b04cfaef96ff42c68786ab9a057c1ebb7822403269"

B2R_DIR = (
    R / "output"
    / "V16_E1B2R_XPU_B2Q_INTERPRETATION_CORRECTED_STAGE2_PROTOCOL"
)
B2R_INTERPRETATION = B2R_DIR / "V16E1B2R_B2Q_Scientific_Interpretation.json"
B2R_PROSPECTIVE = B2R_DIR / "V16E1B2R_COMP_XPU_005_Prospective_Scientific_Protocol.json"
B2R_FEASIBILITY = B2R_DIR / "V16E1B2R_B2S_Autograd_Backward_Feasibility_Protocol.json"
B2R_HANDOFF = B2R_DIR / "V16E1B2R_B2S_Handoff.md"
B2R_SUMMARY = B2R_DIR / "PAD_Stream_V16E1B2R_XPU_Summary.json"

B2R_INTERPRETATION_SHA = "5065f9a8fd9bfece81e4de1123ac0a18a3912e253cdad0266fdac2d559953485"
B2R_PROSPECTIVE_SHA = "7dfdc867086a2229832965be1496cdd8bc4415d239e5bef371f8a472fda8988b"
B2R_FEASIBILITY_SHA = "24cb9c45e9416160a827fb14f4a1408a4e6c0bd3d4f9aad1af30bae2f93ac8c9"
B2R_HANDOFF_SHA = "42d94131bce5c6d7d2c3701424aa359aa6f875cc5a27fb38456f2ad7aa2677ec"
B2R_SUMMARY_SHA = "8e16e592c832a71ec14c85ae5eb9a31201ce99f31e8a99b8e8af5510600de4db"

EXPECTED_B2R_STATUS = (
    "V16E1B2R_XPU_B2Q_NATIVE_CONSERVATION_INTERPRETATION_FROZEN_"
    "EXACT_GODUNOV_FINITE_VOLUME_BALANCE_MACHINE_PRECISION_VERIFIED_ZERO_CLIP_EVENTS_"
    "FAN_SHOCK_INTERPOLATION_AND_SPARSE_TIME_CONTINUOUS_RESIDUAL_ARTIFACTS_SEPARATED_"
    "CORRECTED_CONSERVATIVE_MOVING_FAN_RESIDUAL_SCIENTIFICALLY_READY_FOR_PROSPECTIVE_STAGE2_STUDY_"
    "COMP_XPU_005_ONE_FACTOR_PHYSICS_RESIDUAL_REPLACEMENT_DEFINED_BUT_FULL_TRAINING_NOT_YET_AUTHORIZED_"
    "B2S_EXACT_AUTOGRAD_BACKWARD_FEASIBILITY_BENCHMARK_AUTHORIZED_"
    "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_B3_NOT_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2S_XPU_CORRECTED_RESIDUAL_BACKWARD_FEASIBILITY"
)
OUT.mkdir(parents=True, exist_ok=True)

RESULTS = OUT / "V16E1B2S_Corrected_Residual_Backward_Feasibility.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2S_XPU_Summary.json"
CHILD_DIR = OUT / "candidate_results"
CHILD_DIR.mkdir(parents=True, exist_ok=True)


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


def atomic_json_write(payload, path: Path):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp, path)


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


def sync_xpu():
    if hasattr(torch.xpu, "synchronize"):
        torch.xpu.synchronize()


def empty_xpu_cache():
    if hasattr(torch.xpu, "empty_cache"):
        torch.xpu.empty_cache()


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


def classify_runtime_error(text: str) -> str:
    t = text.lower()
    if (
        "out of memory" in t
        or "oom" in t
        or "ze_result_error_out_of_device_memory" in t
    ):
        return "OOM"
    if (
        "device lost" in t
        or "ur_result_error_device_lost" in t
        or "ze_result_error_device_lost" in t
    ):
        return "DEVICE_LOST"
    return "RUNTIME_ERROR"


def frozen_split_indices(n):
    rng = np.random.default_rng(SEED)
    idx = np.arange(n)
    rng.shuffle(idx)
    n_train = int(0.8 * n)
    return idx[:n_train], idx[n_train:]


def balanced_holdout_pool(p11, holdout_idx, needed=max(CANDIDATES)):
    by_nc = {}

    for nc in NC_VALUES:
        ids = holdout_idx[
            np.isclose(
                p11[holdout_idx, 10],
                nc,
                atol=1e-7,
            )
        ]
        ids = np.sort(ids)

        if len(ids) < 4:
            raise RuntimeError(
                f"Insufficient holdout rows for Nc={nc}"
            )

        by_nc[nc] = ids

    pool = []
    round_i = 0

    while len(pool) < needed:
        for nc in NC_VALUES:
            ids = by_nc[nc]
            pool.append(
                int(ids[round_i % len(ids)])
            )
            if len(pool) >= needed:
                break
        round_i += 1

    return np.asarray(pool, dtype=int)


# =============================================================================
# Exact corrected training-graph residual
# =============================================================================

def local_recurrent_derivatives_create_graph(
    S_pred,
    xi,
    p11,
):
    """
    Pointwise recurrent derivatives with create_graph=True.

    N_xi(j) = dN_j/dxi_j
    N_tD(j) = dN_j/dp11[7]
    N_X(j)  = dN_j/dp11[8]
    """
    T = S_pred.shape[1]

    gx_nodes = []
    gt_nodes = []
    gX_nodes = []

    for j in range(T):
        gx, gp = torch.autograd.grad(
            outputs=S_pred[:, j, :].sum(),
            inputs=(xi, p11),
            retain_graph=True,
            create_graph=True,
            allow_unused=False,
        )

        gx_nodes.append(
            gx[:, j, 0]
        )
        gt_nodes.append(
            gp[:, 7]
        )
        gX_nodes.append(
            gp[:, 8]
        )

    N_xi = torch.stack(
        gx_nodes,
        dim=1,
    ).unsqueeze(-1)

    N_tD = torch.stack(
        gt_nodes,
        dim=1,
    ).unsqueeze(-1)

    N_X = torch.stack(
        gX_nodes,
        dim=1,
    ).unsqueeze(-1)

    return N_xi, N_tD, N_X


def rh_xdot_coeff(M, p11_coeff):
    swc = p11_coeff[:, 2:3]
    X = p11_coeff[:, 8:9]
    Sw_star = p11_coeff[:, 9:10]
    Nc = p11_coeff[:, 10:11]

    S_pair = torch.cat(
        [
            swc.unsqueeze(1),
            Sw_star.unsqueeze(1),
        ],
        dim=1,
    )

    fw_pair = M.fractional_flow_torch(
        S_pair,
        p11_coeff,
    )

    fw_r = fw_pair[:, 0:1, :]
    fw_l = fw_pair[:, 1:2, :]

    denom = torch.clamp(
        (
            Sw_star
            - swc
        ).unsqueeze(1),
        min=1e-8,
    )

    sigma = (
        fw_l
        - fw_r
    ) / denom

    X3 = X.unsqueeze(1)
    Nc3 = Nc.unsqueeze(1)

    xdot = torch.exp(
        Nc3 * X3
    ) * sigma

    return xdot


def corrected_physics_loss_training_graph(
    M,
    model,
    xi,
    p11,
):
    S_pred = model(
        xi,
        p11,
    )

    N_xi, N_tD, N_X = (
        local_recurrent_derivatives_create_graph(
            S_pred,
            xi,
            p11,
        )
    )

    # Physical conditioner values are fixed coefficients for theta-gradient
    # evaluation. Detaching them reduces irrelevant input-gradient graph size
    # without changing gradients with respect to model parameters.
    pcoeff = p11.detach()
    xcoeff = xi.detach()

    fw = M.fractional_flow_torch(
        S_pred,
        pcoeff,
    )

    dfdS = torch.autograd.grad(
        outputs=fw,
        inputs=S_pred,
        grad_outputs=torch.ones_like(fw),
        retain_graph=True,
        create_graph=True,
        only_inputs=True,
    )[0]

    X = (
        pcoeff[:, 8:9]
        .unsqueeze(1)
    )
    Nc = (
        pcoeff[:, 10:11]
        .unsqueeze(1)
    )

    uD = torch.exp(
        Nc
        * xcoeff
        * X
    )

    xdot = rh_xdot_coeff(
        M,
        pcoeff,
    )

    residual = (
        N_tD
        + xdot * N_X
        + (
            uD * dfdS / X
            - xcoeff * xdot / X
        ) * N_xi
        + Nc * uD * fw
    )

    if residual.shape[1] > 2:
        residual_used = residual[:, 1:-1, :]
    else:
        residual_used = residual

    Lp = torch.mean(
        residual_used ** 2
    )

    return S_pred, Lp, residual_used


def complete_corrected_total_loss(
    M,
    model,
    xi,
    Sw,
    p11,
    ai,
    at,
):
    S_pred, Lp, residual = (
        corrected_physics_loss_training_graph(
            M,
            model,
            xi,
            p11,
        )
    )

    Ld = M.data_loss(
        S_pred,
        Sw,
    )

    Lbc = M.injector_bc_loss(
        S_pred,
        p11,
    )

    Ltip = M.tip_bc_loss(
        S_pred,
        p11,
    )

    La = M.anchor_loss(
        S_pred,
        ai,
        at,
    )

    Lmono = M.monotonicity_loss(
        S_pred,
    )

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
# Candidate child
# =============================================================================

def run_candidate_child(
    microbatch: int,
    result_path: Path,
):
    payload = {
        "microbatch":
            int(microbatch),
        "success":
            False,
        "failure_class":
            None,
        "error":
            None,
        "optimizer_created":
            False,
        "weight_update":
            False,
    }

    try:
        if microbatch not in CANDIDATES:
            raise RuntimeError(
                f"Unauthorized candidate microbatch {microbatch}"
            )

        if not torch.xpu.is_available():
            raise RuntimeError(
                "Intel XPU unavailable."
            )

        M = import_module(
            BASE_RUNNER,
            f"b2s_base_{microbatch}",
        )
        J = import_module(
            B2J_SOURCE,
            f"b2s_comp004_{microbatch}",
        )

        d = np.load(
            DATASET
        )

        xi_all = d["xi"]
        Sw_all = d["Sw"]
        p11_all = d["p11"]
        ai_all = d["ai"]
        at_all = d["at"]

        _, holdout_idx = frozen_split_indices(
            len(xi_all)
        )

        pool = balanced_holdout_pool(
            p11_all,
            holdout_idx,
            needed=max(CANDIDATES),
        )

        ids = pool[
            :microbatch
        ]

        device = torch.device(
            "xpu"
        )

        EtaModel = J.build_eta_model_class(
            M
        )

        checkpoint_before = sha256(
            COMP004_CHECKPOINT
        )

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
        model.to(
            device
        )
        model.train()

        # Exact in-memory immutable parameter snapshot.
        param_before = {
            name:
                p.detach().cpu().clone()
            for name, p
            in model.named_parameters()
        }

        for p in model.parameters():
            p.grad = None

        xi = (
            torch.from_numpy(
                xi_all[ids]
            )
            .to(device)
            .detach()
            .clone()
            .requires_grad_(True)
        )

        Sw = torch.from_numpy(
            Sw_all[ids]
        ).to(device)

        p11 = (
            torch.from_numpy(
                p11_all[ids]
            )
            .to(device)
            .detach()
            .clone()
            .requires_grad_(True)
        )

        ai = torch.from_numpy(
            ai_all[ids]
        ).to(device)

        at = torch.from_numpy(
            at_all[ids]
        ).to(device)

        reset_peak_memory()
        sync_xpu()

        t0 = time.perf_counter()

        S_pred, residual, parts = (
            complete_corrected_total_loss(
                M,
                model,
                xi,
                Sw,
                p11,
                ai,
                at,
            )
        )

        forward_residual_done = time.perf_counter()

        if not torch.isfinite(
            S_pred
        ).all().item():
            raise RuntimeError(
                "Nonfinite forward prediction."
            )

        if not torch.isfinite(
            residual
        ).all().item():
            raise RuntimeError(
                "Nonfinite corrected residual."
            )

        if not all(
            torch.isfinite(
                v
            ).all().item()
            for v
            in parts.values()
        ):
            raise RuntimeError(
                "Nonfinite loss component."
            )

        parts[
            "total"
        ].backward()

        sync_xpu()

        t1 = time.perf_counter()

        grad_sq = 0.0
        grad_count = 0
        nonzero_grad_tensors = 0
        grad_finite = True

        for p in model.parameters():
            if p.grad is None:
                continue

            grad_count += 1

            g = p.grad.detach()

            if not torch.isfinite(
                g
            ).all().item():
                grad_finite = False

            if torch.count_nonzero(
                g
            ).item() > 0:
                nonzero_grad_tensors += 1

            grad_sq += float(
                torch.sum(
                    g.double() ** 2
                ).cpu()
            )

        if grad_count == 0:
            raise RuntimeError(
                "No parameter gradients were produced."
            )

        if not grad_finite:
            raise RuntimeError(
                "Nonfinite parameter gradient detected."
            )

        # Backward must never modify parameter values.
        params_equal = True

        for name, p in model.named_parameters():
            if not torch.equal(
                p.detach().cpu(),
                param_before[name],
            ):
                params_equal = False
                break

        if not params_equal:
            raise RuntimeError(
                "Model parameter value changed without optimizer step."
            )

        checkpoint_after = sha256(
            COMP004_CHECKPOINT
        )

        if (
            checkpoint_before
            != COMP004_CHECKPOINT_SHA
            or checkpoint_after
            != COMP004_CHECKPOINT_SHA
        ):
            raise RuntimeError(
                "Frozen COMP-XPU-004 checkpoint SHA changed."
            )

        payload.update({
            "success":
                True,

            "dataset_indices":
                [int(i) for i in ids],

            "physical_Nc_values":
                [
                    float(v)
                    for v
                    in p11_all[ids, 10]
                ],

            "prediction_finite":
                True,

            "residual_finite":
                True,

            "losses_finite":
                True,

            "parameter_gradients_finite":
                True,

            "parameter_gradient_tensor_count":
                int(grad_count),

            "nonzero_gradient_tensor_count":
                int(nonzero_grad_tensors),

            "parameter_gradient_l2_norm":
                float(
                    math.sqrt(
                        max(
                            grad_sq,
                            0.0,
                        )
                    )
                ),

            "weights_exactly_unchanged":
                True,

            "checkpoint_SHA_unchanged":
                True,

            "checkpoint_sha256":
                checkpoint_after,

            "losses": {
                k:
                    float(
                        v.detach().cpu()
                    )
                for k, v
                in parts.items()
            },

            "corrected_residual_MSE":
                float(
                    torch.mean(
                        residual.detach() ** 2
                    ).cpu()
                ),

            "forward_plus_residual_seconds":
                float(
                    forward_residual_done
                    - t0
                ),

            "forward_residual_backward_seconds":
                float(
                    t1 - t0
                ),

            "peak_xpu_memory_bytes":
                peak_memory_bytes(),

            "optimizer_created":
                False,

            "weight_update":
                False,
        })

        # Discard gradients explicitly.
        for p in model.parameters():
            p.grad = None

        del (
            xi,
            Sw,
            p11,
            ai,
            at,
            S_pred,
            residual,
            parts,
            model,
        )

        gc.collect()
        empty_xpu_cache()

        atomic_json_write(
            payload,
            result_path,
        )
        return 0

    except BaseException as exc:
        payload.update({
            "success":
                False,

            "failure_class":
                classify_runtime_error(
                    f"{type(exc).__name__}: {exc}"
                ),

            "error":
                f"{type(exc).__name__}: {exc}",

            "traceback":
                traceback.format_exc(),

            "peak_xpu_memory_bytes":
                peak_memory_bytes(),

            "optimizer_created":
                False,

            "weight_update":
                False,
        })

        try:
            atomic_json_write(
                payload,
                result_path,
            )
        except Exception:
            pass

        return 2


# =============================================================================
# Parent authority / orchestration
# =============================================================================

def parent_main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2S-XPU")
    print("Corrected Conservative Residual Backward Feasibility Benchmark")
    print("=" * 80)
    print("NO OPTIMIZER — NO WEIGHT UPDATE — subprocess-isolated candidates.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2S summary already exists; refusing overwrite."
        )

    gates = {
        "Stage2_source_SHA_exact":
            exact(
                STAGE2,
                STAGE2_SHA,
            ),

        "base_runner_SHA_exact":
            exact(
                BASE_RUNNER,
                BASE_RUNNER_SHA,
            ),

        "B2J_source_SHA_exact":
            exact(
                B2J_SOURCE,
                B2J_SOURCE_SHA,
            ),

        "B2O_autograd_SHA_exact":
            exact(
                B2O_AUTOGRAD,
                B2O_AUTOGRAD_SHA,
            ),

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

        "COMP004_manifest_SHA_exact":
            exact(
                COMP004_MANIFEST,
                COMP004_MANIFEST_SHA,
            ),

        "COMP004_summary_SHA_exact":
            exact(
                COMP004_SUMMARY,
                COMP004_SUMMARY_SHA,
            ),

        "B2R_source_SHA_exact":
            exact(
                B2R_SOURCE,
                B2R_SOURCE_SHA,
            ),

        "B2R_interpretation_SHA_exact":
            exact(
                B2R_INTERPRETATION,
                B2R_INTERPRETATION_SHA,
            ),

        "B2R_prospective_SHA_exact":
            exact(
                B2R_PROSPECTIVE,
                B2R_PROSPECTIVE_SHA,
            ),

        "B2R_feasibility_SHA_exact":
            exact(
                B2R_FEASIBILITY,
                B2R_FEASIBILITY_SHA,
            ),

        "B2R_handoff_SHA_exact":
            exact(
                B2R_HANDOFF,
                B2R_HANDOFF_SHA,
            ),

        "B2R_summary_SHA_exact":
            exact(
                B2R_SUMMARY,
                B2R_SUMMARY_SHA,
            ),
    }

    b2r = (
        read_json(
            B2R_SUMMARY
        )
        if B2R_SUMMARY.exists()
        else {}
    )

    b2r_feas = (
        read_json(
            B2R_FEASIBILITY
        )
        if B2R_FEASIBILITY.exists()
        else {}
    )

    b2o = (
        read_json(
            B2O_AUTOGRAD
        )
        if B2O_AUTOGRAD.exists()
        else {}
    )

    gates.update({
        "B2R_status_exact":
            b2r.get(
                "status"
            )
            == EXPECTED_B2R_STATUS,

        "B2R_full_training_false":
            b2r.get(
                "corrected_Stage2_full_training_authorized"
            )
            is False,

        "B2R_B2S_true":
            b2r.get(
                "B2S_feasibility_authorized"
            )
            is True,

        "B2R_B3_false":
            b2r.get(
                "B3_authorized"
            )
            is False,

        "B2R_candidate_microbatches_exact":
            b2r_feas.get(
                "candidate_microbatches"
            )
            == CANDIDATES,

        "B2R_optimizer_false":
            b2r_feas.get(
                "optimizer"
            )
            is False,

        "B2R_weight_update_false":
            b2r_feas.get(
                "weight_update"
            )
            is False,
    })

    rh = (
        b2o.get(
            "front_speed_closures",
            {},
        ).get(
            "Rankine_Hugoniot",
            {},
        )
    )

    fd = (
        b2o.get(
            "front_speed_closures",
            {},
        ).get(
            "finite_difference_Godunov_front",
            {},
        )
    )

    gates.update({
        "B2O_RH_form_identity_certified":
            rh.get(
                "forms_match_within_machine_epsilon_scaled_bound"
            )
            is True,

        "B2O_FD_form_identity_certified":
            fd.get(
                "forms_match_within_machine_epsilon_scaled_bound"
            )
            is True,

        "B2O_RH_Nc0_nesting_certified":
            rh.get(
                "Nc0_nesting_matches_within_machine_epsilon_scaled_bound"
            )
            is True,

        "B2O_FD_Nc0_nesting_certified":
            fd.get(
                "Nc0_nesting_matches_within_machine_epsilon_scaled_bound"
            )
            is True,
    })

    print("AUTHORITY / FEASIBILITY GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    if not all(gates.values()):
        raise RuntimeError(
            "B2S blocked by authority/protocol mismatch."
        )

    # Remove stale candidate result files only. This does not touch any
    # scientific checkpoint or prior milestone artifact.
    for p in CHILD_DIR.glob(
        "candidate_mb*.json"
    ):
        try:
            p.unlink()
        except OSError:
            pass

    script = Path(
        __file__
    ).resolve()

    candidate_results = []

    print("\nCANDIDATE BENCHMARKS")
    print("  Each candidate runs in an isolated child process.")
    print("  No optimizer object is created.\n")

    for mb in CANDIDATES:
        result_path = (
            CHILD_DIR
            / f"candidate_mb{mb:02d}.json"
        )

        cmd = [
            sys.executable,
            str(script),
            "--candidate",
            str(mb),
            "--result-path",
            str(result_path),
        ]

        t0 = time.perf_counter()

        proc = subprocess.run(
            cmd,
            cwd=str(R),
            capture_output=True,
            text=True,
        )

        elapsed = (
            time.perf_counter()
            - t0
        )

        if result_path.exists():
            rec = read_json(
                result_path
            )
        else:
            combined = (
                (proc.stdout or "")
                + "\n"
                + (proc.stderr or "")
            ).strip()

            rec = {
                "microbatch":
                    int(mb),
                "success":
                    False,
                "failure_class":
                    classify_runtime_error(
                        combined
                    ),
                "error":
                    combined[-4000:],
                "optimizer_created":
                    False,
                "weight_update":
                    False,
            }

        rec[
            "subprocess_returncode"
        ] = int(
            proc.returncode
        )

        rec[
            "subprocess_wall_seconds"
        ] = float(
            elapsed
        )

        candidate_results.append(
            rec
        )

        if rec.get(
            "success"
        ):
            mem = rec.get(
                "peak_xpu_memory_bytes"
            )

            mem_text = (
                f"{mem / (1024**3):.3f} GiB"
                if isinstance(mem, int)
                and mem >= 0
                else "n/a"
            )

            print(
                f"  microbatch={mb:2d} | PASS "
                f"| total={rec['forward_residual_backward_seconds']:.3f}s "
                f"| grad_norm={rec['parameter_gradient_l2_norm']:.6e} "
                f"| peak={mem_text}"
            )
        else:
            print(
                f"  microbatch={mb:2d} | FAIL "
                f"| class={rec.get('failure_class')} "
                f"| returncode={proc.returncode}"
            )

        # Frozen checkpoint must remain untouched after EVERY child.
        if sha256(
            COMP004_CHECKPOINT
        ) != COMP004_CHECKPOINT_SHA:
            raise RuntimeError(
                "COMP-XPU-004 checkpoint changed during B2S."
            )

    successful = [
        int(
            rec[
                "microbatch"
            ]
        )
        for rec in candidate_results
        if rec.get(
            "success"
        )
    ]

    selected = (
        max(
            successful
        )
        if successful
        else None
    )

    # Every child must explicitly report no optimizer and no update if it
    # produced a result artifact. Missing/crashed children are still classified
    # as failures but the parent itself never creates an optimizer.
    all_reported_no_optimizer = all(
        rec.get(
            "optimizer_created"
        )
        is False
        for rec in candidate_results
    )

    all_reported_no_update = all(
        rec.get(
            "weight_update"
        )
        is False
        for rec in candidate_results
    )

    results_payload = {
        "milestone":
            MILESTONE,

        "classification":
            "NO_OPTIMIZER_NO_WEIGHT_UPDATE_CORRECTED_RESIDUAL_BACKWARD_FEASIBILITY",

        "prospective_experiment":
            "V16E-BLREP-COMP-XPU-005",

        "baseline_checkpoint":
            {
                "experiment":
                    "V16E-BLREP-COMP-XPU-004",
                "sha256":
                    COMP004_CHECKPOINT_SHA,
            },

        "candidate_microbatches":
            CANDIDATES,

        "candidate_results":
            candidate_results,

        "successful_microbatches":
            successful,

        "largest_successful_tested_microbatch":
            selected,

        "selection_rule":
            "largest tested candidate completing finite forward, corrected residual, "
            "complete loss backward, XPU synchronization, finite parameter gradients, "
            "and exact no-weight-change/checkpoint-SHA gates",

        "scientific_settings_changed":
            False,

        "optimizer_created":
            False,

        "optimizer_step":
            False,

        "weight_update":
            False,

        "checkpoint_mutated":
            False,

        "OOD_used":
            False,

        "TOF_used":
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

    gates.update({
        "all_five_candidates_attempted":
            len(
                candidate_results
            )
            == len(
                CANDIDATES
            ),

        "all_candidate_microbatches_recorded":
            {
                int(
                    r[
                        "microbatch"
                    ]
                )
                for r
                in candidate_results
            }
            == set(
                CANDIDATES
            ),

        "at_least_one_candidate_success":
            selected is not None,

        "all_reported_no_optimizer":
            bool(
                all_reported_no_optimizer
            ),

        "all_reported_no_weight_update":
            bool(
                all_reported_no_update
            ),

        "COMP004_checkpoint_still_unchanged":
            sha256(
                COMP004_CHECKPOINT
            )
            == COMP004_CHECKPOINT_SHA,

        "results_written":
            RESULTS.exists()
            and RESULTS.stat().st_size > 0,

        "parent_created_no_optimizer":
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

    ok = all(
        bool(v)
        for v
        in gates.items()
    )

    # Fix Python dict-items issue explicitly below.
    ok = all(
        bool(v)
        for v
        in gates.values()
    )

    if ok:
        status = (
            "V16E1B2S_XPU_CORRECTED_CONSERVATIVE_STAGE2_RESIDUAL_BACKWARD_FEASIBILITY_COMPLETE_"
            "CREATE_GRAPH_TRUE_LOCAL_RECURRENT_XI_TD_XDSTAR_DERIVATIVES_COMPLETE_FROZEN_TOTAL_LOSS_BACKWARD_"
            "INTEL_XPU_CANDIDATES_1_2_4_8_16_ATTEMPTED_LARGEST_SUCCESSFUL_TESTED_MICROBATCH_BOUND_"
            "FINITE_PARAMETER_GRADIENTS_CONFIRMED_NO_OPTIMIZER_NO_OPTIMIZER_STEP_NO_WEIGHT_CHANGE_"
            "COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_"
            "B2T_OPERATIONAL_TRAINING_PROTOCOL_FREEZE_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_B3_NOT_AUTHORIZED"
        )
    else:
        status = (
            "V16E1B2S_XPU_CORRECTED_RESIDUAL_FEASIBILITY_COMPLETED_WITH_GATE_FAILURE"
        )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "results_sha256":
            sha256(
                RESULTS
            ),

        "successful_microbatches":
            successful,

        "largest_successful_tested_microbatch":
            selected,

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                f"V16E-1B2T-XPU — freeze operational corrected-training protocol "
                f"with tested microbatch={selected}; authorize fresh COMP-XPU-005 "
                f"only after protocol freeze"
                if ok
                else
                "V16E-1B2S-R1 — diagnose corrected-residual XPU feasibility failure"
            ),

        "gates":
            {
                k:
                    bool(v)
                for k, v
                in gates.items()
            },
    }

    SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nSELECTION")
    print(
        "  successful candidates:",
        successful,
    )
    print(
        "  largest successful tested microbatch:",
        selected,
    )

    print("\nFINAL GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    print("\nSTATUS")
    print(
        " ",
        status,
    )

    print("\nHASHES")
    print(
        "  Results:",
        sha256(
            RESULTS
        ),
    )
    print(
        "  Summary:",
        sha256(
            SUMMARY
        ),
    )

    print("\nNEXT")
    print(
        " ",
        summary[
            "next_milestone"
        ],
    )

    if not ok:
        sys.exit(2)


# =============================================================================
# CLI
# =============================================================================

def parse_args():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--candidate",
        type=int,
        default=None,
    )

    ap.add_argument(
        "--result-path",
        type=Path,
        default=None,
    )

    return ap.parse_args()


def main():
    args = parse_args()

    if args.candidate is not None:
        if args.result_path is None:
            raise RuntimeError(
                "--result-path is required with --candidate"
            )

        rc = run_candidate_child(
            args.candidate,
            args.result_path,
        )
        sys.exit(
            rc
        )

    parent_main()


if __name__ == "__main__":
    main()
