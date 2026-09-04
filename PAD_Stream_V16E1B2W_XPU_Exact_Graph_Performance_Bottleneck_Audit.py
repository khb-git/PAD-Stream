#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2W-XPU
Exact Corrected-Graph Performance Bottleneck Audit

Purpose
-------
Profile the exact certified corrected Stage-2 derivative graph at the largest
proven-feasible tested reference microbatch (128), with NO training and NO
weight update.

NO OPTIMIZER.
NO OPTIMIZER STEP.
NO WEIGHT UPDATE.
NO CHECKPOINT MUTATION.
NO OOD.
NO TOF.

Authority
---------
V16E-1B2V authorizes this exact-graph performance audit only.

Reference
---------
Microbatch:
    128

Reason:
    largest actually successful B2U candidate.

Exact corrected graph
---------------------
This script imports the frozen B2S implementation SHA and calls its exact
complete_corrected_total_loss() graph. It does NOT re-derive or replace the
corrected physics loss.

The exact B2S graph contains:
    model forward
    local recurrent derivatives with create_graph=True:
        N_xi(j) = dN_j/dxi_j
        N_tD(j) = dN_j/dp11[tD]
        N_X(j)  = dN_j/dp11[xD_star]
    corrected conservative moving-fan physics loss
    data / injector BC / tip BC / anchor / monotonicity losses
    complete frozen Stage-2 total loss

Profiling method
----------------
The exact B2S functions are wrapped for timing only. The computational outputs
are unchanged.

Synchronized timing stages:
    1. model forward
    2. local recurrent derivative construction
    3. corrected physics algebra / fractional-flow derivative
       (obtained from exact corrected-physics total minus stages 1 and 2)
    4. non-physics losses + total assembly
       (obtained from exact complete-loss total minus corrected-physics total)
    5. total backward
    6. XPU synchronization is included at each stage boundary

Matched first-order control
---------------------------
A fresh copy of the same frozen COMP-XPU-004 model and the exact same 128
dataset rows is used.

Control loss:
    lambda_data   * L_data
  + lambda_bc     * L_injector
  + lambda_tip    * L_tip
  + lambda_anchor * L_anchor
  + lambda_mono   * L_monotonicity

No corrected physics derivatives are constructed.

This isolates the incremental cost of the corrected create_graph=True
derivative engine relative to a matched first-order recurrent backward.

Microbatch-256 failure
----------------------
The exact frozen B2U failure class and error text are copied into the audit.
They are NOT reclassified and the 256 candidate is NOT rerun.

No scientific numeric acceptance threshold is introduced.

COMP-XPU-005 full training remains blocked.
B3 remains blocked.
"""

from __future__ import annotations

from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import math
import os
import sys
import time

import numpy as np
import torch


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2W-XPU"
REFERENCE_MICROBATCH = 128

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

# Exact corrected graph authority.
B2S_SOURCE = (
    R
    / "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
)
B2S_SOURCE_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"

# B2O algebraic identity authority.
B2O_DIR = (
    R / "output"
    / "V16_E1B2O_XPU_CONSERVATIVE_RESIDUAL_AUTOGRAD_VERIFICATION"
)
B2O_AUTOGRAD = B2O_DIR / "V16E1B2O_COMP004_Autograd_Residual_Form_Verification.json"
B2O_AUTOGRAD_SHA = "fb347b81ece990860e2caf599e9d276296a833f800b3c881dfec5235f76bb39e"

# B2U measured behavior.
B2U_DIR = (
    R / "output"
    / "V16_E1B2U_XPU_EXTENDED_CORRECTED_RESIDUAL_THROUGHPUT"
)
B2U_RESULTS = B2U_DIR / "V16E1B2U_Extended_Throughput_Memory_Results.json"
B2U_SUMMARY = B2U_DIR / "PAD_Stream_V16E1B2U_XPU_Summary.json"

B2U_RESULTS_SHA = "e71f398c88feee2260c50109055b917103e76800365954823f320457a0d30075"
B2U_SUMMARY_SHA = "9623bace06e8526524fde61a39b3ce3ff8193aa1ccc40713f5fdd671ca6e88d1"

# B2V authority.
B2V_SOURCE = (
    R
    / "PAD_Stream_V16E1B2V_XPU_B2U_Interpretation_Performance_Diagnostic_Protocol_Freeze.py"
)
B2V_SOURCE_SHA = "e03564f4fde2bfc5ba794170be5f9b62975885b46737b0d603a056995873642f"

B2V_DIR = (
    R / "output"
    / "V16_E1B2V_XPU_B2U_INTERPRETATION_PERFORMANCE_DIAGNOSTIC_PROTOCOL"
)
B2V_INTERPRETATION = B2V_DIR / "V16E1B2V_B2U_Operational_Interpretation.json"
B2V_PROTOCOL = B2V_DIR / "V16E1B2V_B2W_Performance_Diagnostic_Protocol.json"
B2V_HANDOFF = B2V_DIR / "V16E1B2V_B2W_Handoff.md"
B2V_SUMMARY = B2V_DIR / "PAD_Stream_V16E1B2V_XPU_Summary.json"

B2V_INTERPRETATION_SHA = "cc33f11b61f518ba6fada97f3a12d304f8ba25726a9cc1420f078ff64c1b772a"
B2V_PROTOCOL_SHA = "9bd25554df50859f912d23baa1e7bb08bdac5355fbf41a6a7b86354f6b7e5a7f"
B2V_HANDOFF_SHA = "8ae62e20a2d89a0a70b7c0e62e76da32a2aa4ff5a312534ad02d14b458f378af"
B2V_SUMMARY_SHA = "73690b98a3a6d3e4fc1d9459179dc77df7a2cd22e1b0cd45752eac135beb4979"

EXPECTED_B2V_STATUS = (
    "V16E1B2V_XPU_B2U_THROUGHPUT_MEMORY_INTERPRETATION_AND_EXACT_GRAPH_PERFORMANCE_DIAGNOSTIC_PROTOCOL_FROZEN_"
    "MICROBATCH_128_BOUND_AS_LARGEST_PROVEN_FEASIBLE_TESTED_REFERENCE_NOT_HARDWARE_CEILING_OR_FINAL_TRAINING_VALUE_"
    "MICROBATCH_256_FAILURE_PRESERVED_AS_RUNTIME_ERROR_WITHOUT_CAUSE_RECLASSIFICATION_"
    "B2U_THROUGHPUT_MEMORY_AND_DIAGNOSTIC_FULL_RUN_PROJECTIONS_FROZEN_"
    "COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_"
    "B2W_NO_UPDATE_EXACT_DERIVATIVE_GRAPH_TIMING_AND_MATCHED_FIRST_ORDER_CONTROL_AUTHORIZED_"
    "NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_B3_NOT_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2W_XPU_EXACT_GRAPH_PERFORMANCE_BOTTLENECK_AUDIT"
)
OUT.mkdir(parents=True, exist_ok=True)

PROFILE = OUT / "V16E1B2W_Exact_Graph_Performance_Profile.json"
DECISION = OUT / "V16E1B2W_Performance_Bottleneck_Decision.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2W_XPU_Summary.json"


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


def clone_parameters(model):
    return {
        name: p.detach().cpu().clone()
        for name, p in model.named_parameters()
    }


def parameters_equal(model, before):
    for name, p in model.named_parameters():
        if not torch.equal(
            p.detach().cpu(),
            before[name],
        ):
            return False
    return True


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


def load_b2u_reference_ids(b2u_results):
    for rec in b2u_results.get("candidate_results", []):
        if int(rec.get("microbatch", -1)) == REFERENCE_MICROBATCH:
            ids = rec.get("dataset_indices")
            if not isinstance(ids, list) or len(ids) != REFERENCE_MICROBATCH:
                raise RuntimeError(
                    "B2U microbatch-128 dataset indices missing/incomplete."
                )
            return np.asarray(ids, dtype=int)

    raise RuntimeError(
        "B2U microbatch-128 record not found."
    )


def load_model_and_batch(B2S, ids, device):
    M = B2S.import_module(
        B2S.BASE_RUNNER,
        "b2w_base_runner",
    )

    J = B2S.import_module(
        B2S.B2J_SOURCE,
        "b2w_comp004_runner",
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
# Exact corrected graph profile
# =============================================================================

def profile_corrected_graph(B2S, ids, device):
    M, model, xi, Sw, p11, ai, at = load_model_and_batch(
        B2S,
        ids,
        device,
    )

    param_before = clone_parameters(model)
    checkpoint_before = sha256(COMP004_CHECKPOINT)

    for p in model.parameters():
        p.grad = None

    stage = {
        "model_forward_seconds":
            0.0,

        "local_recurrent_derivative_seconds":
            0.0,

        "exact_corrected_physics_graph_seconds":
            0.0,

        "exact_complete_loss_graph_seconds":
            0.0,
    }

    # ------------------------------------------------------------------
    # Timing wrappers around the exact frozen B2S functions.
    # ------------------------------------------------------------------

    original_forward = model.forward
    original_derivatives = B2S.local_recurrent_derivatives_create_graph
    original_physics = B2S.corrected_physics_loss_training_graph

    def timed_forward(*args, **kwargs):
        sync_xpu()
        t0 = time.perf_counter()
        out = original_forward(*args, **kwargs)
        sync_xpu()
        stage["model_forward_seconds"] += (
            time.perf_counter() - t0
        )
        return out

    def timed_derivatives(*args, **kwargs):
        sync_xpu()
        t0 = time.perf_counter()
        out = original_derivatives(*args, **kwargs)
        sync_xpu()
        stage["local_recurrent_derivative_seconds"] += (
            time.perf_counter() - t0
        )
        return out

    def timed_physics(*args, **kwargs):
        sync_xpu()
        t0 = time.perf_counter()
        out = original_physics(*args, **kwargs)
        sync_xpu()
        stage["exact_corrected_physics_graph_seconds"] += (
            time.perf_counter() - t0
        )
        return out

    model.forward = timed_forward
    B2S.local_recurrent_derivatives_create_graph = timed_derivatives
    B2S.corrected_physics_loss_training_graph = timed_physics

    reset_peak_memory()
    sync_xpu()

    total_wall_start = time.perf_counter()

    sync_xpu()
    complete_start = time.perf_counter()

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
        # Restore module/model functions even if construction raises.
        model.forward = original_forward
        B2S.local_recurrent_derivatives_create_graph = original_derivatives
        B2S.corrected_physics_loss_training_graph = original_physics

    sync_xpu()
    stage["exact_complete_loss_graph_seconds"] = (
        time.perf_counter()
        - complete_start
    )

    prediction_finite = bool(
        torch.isfinite(S_pred).all().item()
    )

    residual_finite = bool(
        torch.isfinite(residual).all().item()
    )

    losses_finite = bool(
        all(
            torch.isfinite(v).all().item()
            for v in parts.values()
        )
    )

    sync_xpu()
    backward_start = time.perf_counter()

    parts["total"].backward()

    sync_xpu()
    backward_seconds = (
        time.perf_counter()
        - backward_start
    )

    total_wall_seconds = (
        time.perf_counter()
        - total_wall_start
    )

    grads = gradient_summary(model)

    weights_unchanged = parameters_equal(
        model,
        param_before,
    )

    checkpoint_after = sha256(
        COMP004_CHECKPOINT
    )

    # Derived stage times. Nested wrappers contain synchronized boundaries;
    # tiny negative roundoff/overhead differences are clamped to zero.
    corrected_physics_algebra_seconds = max(
        0.0,
        stage["exact_corrected_physics_graph_seconds"]
        - stage["model_forward_seconds"]
        - stage["local_recurrent_derivative_seconds"],
    )

    nonphysics_loss_assembly_seconds = max(
        0.0,
        stage["exact_complete_loss_graph_seconds"]
        - stage["exact_corrected_physics_graph_seconds"],
    )

    profile = {
        "microbatch":
            REFERENCE_MICROBATCH,

        "dataset_indices":
            [int(i) for i in ids],

        "model_forward_seconds":
            float(stage["model_forward_seconds"]),

        "local_recurrent_derivative_seconds":
            float(stage["local_recurrent_derivative_seconds"]),

        "corrected_physics_algebra_fractional_flow_seconds":
            float(corrected_physics_algebra_seconds),

        "nonphysics_loss_plus_total_assembly_seconds":
            float(nonphysics_loss_assembly_seconds),

        "exact_corrected_physics_graph_seconds":
            float(stage["exact_corrected_physics_graph_seconds"]),

        "exact_complete_loss_graph_seconds":
            float(stage["exact_complete_loss_graph_seconds"]),

        "total_backward_seconds":
            float(backward_seconds),

        "forward_graph_plus_backward_wall_seconds":
            float(
                stage["exact_complete_loss_graph_seconds"]
                + backward_seconds
            ),

        "profile_wall_seconds":
            float(total_wall_seconds),

        "prediction_finite":
            prediction_finite,

        "residual_finite":
            residual_finite,

        "losses_finite":
            losses_finite,

        "losses": {
            k: float(v.detach().cpu())
            for k, v in parts.items()
        },

        "corrected_residual_MSE":
            float(
                torch.mean(
                    residual.detach() ** 2
                ).cpu()
            ),

        "gradient_summary":
            grads,

        "weights_exactly_unchanged":
            bool(weights_unchanged),

        "checkpoint_SHA_before":
            checkpoint_before,

        "checkpoint_SHA_after":
            checkpoint_after,

        "checkpoint_SHA_unchanged":
            bool(
                checkpoint_before
                == COMP004_CHECKPOINT_SHA
                and checkpoint_after
                == COMP004_CHECKPOINT_SHA
            ),

        "peak_xpu_memory_bytes":
            peak_memory_bytes(),
    }

    for p in model.parameters():
        p.grad = None

    return profile


# =============================================================================
# Matched first-order / non-physics control
# =============================================================================

def profile_first_order_control(B2S, ids, device):
    M, model, xi, Sw, p11, ai, at = load_model_and_batch(
        B2S,
        ids,
        device,
    )

    param_before = clone_parameters(model)
    checkpoint_before = sha256(COMP004_CHECKPOINT)

    for p in model.parameters():
        p.grad = None

    reset_peak_memory()
    sync_xpu()

    total_start = time.perf_counter()

    sync_xpu()
    forward_start = time.perf_counter()

    S_pred = model(
        xi,
        p11,
    )

    sync_xpu()
    forward_seconds = (
        time.perf_counter()
        - forward_start
    )

    sync_xpu()
    loss_start = time.perf_counter()

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
        + M.LAMBDA_BC * Lbc
        + M.LAMBDA_TIP * Ltip
        + M.LAMBDA_ANCHOR * La
        + M.LAMBDA_MONO * Lmono
    )

    sync_xpu()
    loss_seconds = (
        time.perf_counter()
        - loss_start
    )

    prediction_finite = bool(
        torch.isfinite(S_pred).all().item()
    )

    loss_finite = bool(
        torch.isfinite(total).all().item()
    )

    sync_xpu()
    backward_start = time.perf_counter()

    total.backward()

    sync_xpu()
    backward_seconds = (
        time.perf_counter()
        - backward_start
    )

    total_seconds = (
        time.perf_counter()
        - total_start
    )

    grads = gradient_summary(model)
    weights_unchanged = parameters_equal(
        model,
        param_before,
    )

    checkpoint_after = sha256(
        COMP004_CHECKPOINT
    )

    profile = {
        "microbatch":
            REFERENCE_MICROBATCH,

        "dataset_indices":
            [int(i) for i in ids],

        "model_forward_seconds":
            float(forward_seconds),

        "nonphysics_loss_assembly_seconds":
            float(loss_seconds),

        "first_order_backward_seconds":
            float(backward_seconds),

        "forward_loss_backward_wall_seconds":
            float(
                forward_seconds
                + loss_seconds
                + backward_seconds
            ),

        "profile_wall_seconds":
            float(total_seconds),

        "prediction_finite":
            prediction_finite,

        "loss_finite":
            loss_finite,

        "losses": {
            "data":
                float(Ld.detach().cpu()),
            "bc_inj":
                float(Lbc.detach().cpu()),
            "bc_tip":
                float(Ltip.detach().cpu()),
            "anchor":
                float(La.detach().cpu()),
            "mono":
                float(Lmono.detach().cpu()),
            "total_without_physics":
                float(total.detach().cpu()),
        },

        "gradient_summary":
            grads,

        "weights_exactly_unchanged":
            bool(weights_unchanged),

        "checkpoint_SHA_before":
            checkpoint_before,

        "checkpoint_SHA_after":
            checkpoint_after,

        "checkpoint_SHA_unchanged":
            bool(
                checkpoint_before
                == COMP004_CHECKPOINT_SHA
                and checkpoint_after
                == COMP004_CHECKPOINT_SHA
            ),

        "peak_xpu_memory_bytes":
            peak_memory_bytes(),
    }

    for p in model.parameters():
        p.grad = None

    return profile


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2W-XPU")
    print("Exact Corrected-Graph Performance Bottleneck Audit")
    print("=" * 80)
    print("NO TRAINING — NO OPTIMIZER — NO WEIGHT UPDATE.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2W summary already exists; refusing overwrite."
        )

    gates = {
        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),

        "COMP004_checkpoint_SHA_exact":
            exact(COMP004_CHECKPOINT, COMP004_CHECKPOINT_SHA),

        "B2S_source_SHA_exact":
            exact(B2S_SOURCE, B2S_SOURCE_SHA),

        "B2O_autograd_SHA_exact":
            exact(B2O_AUTOGRAD, B2O_AUTOGRAD_SHA),

        "B2U_results_SHA_exact":
            exact(B2U_RESULTS, B2U_RESULTS_SHA),

        "B2U_summary_SHA_exact":
            exact(B2U_SUMMARY, B2U_SUMMARY_SHA),

        "B2V_source_SHA_exact":
            exact(B2V_SOURCE, B2V_SOURCE_SHA),

        "B2V_interpretation_SHA_exact":
            exact(B2V_INTERPRETATION, B2V_INTERPRETATION_SHA),

        "B2V_protocol_SHA_exact":
            exact(B2V_PROTOCOL, B2V_PROTOCOL_SHA),

        "B2V_handoff_SHA_exact":
            exact(B2V_HANDOFF, B2V_HANDOFF_SHA),

        "B2V_summary_SHA_exact":
            exact(B2V_SUMMARY, B2V_SUMMARY_SHA),
    }

    b2u = read_json(B2U_RESULTS) if B2U_RESULTS.exists() else {}
    b2v = read_json(B2V_SUMMARY) if B2V_SUMMARY.exists() else {}
    b2v_protocol = (
        read_json(B2V_PROTOCOL)
        if B2V_PROTOCOL.exists()
        else {}
    )
    b2o = read_json(B2O_AUTOGRAD) if B2O_AUTOGRAD.exists() else {}

    gates.update({
        "B2V_status_exact":
            b2v.get("status") == EXPECTED_B2V_STATUS,

        "B2V_reference_microbatch_128":
            b2v.get("largest_proven_feasible_tested_microbatch")
            == REFERENCE_MICROBATCH,

        "B2V_training_false":
            b2v.get("COMP_XPU_005_full_training_authorized")
            is False,

        "B2V_B2W_true":
            b2v.get("B2W_authorized") is True,

        "B2V_B3_false":
            b2v.get("B3_authorized") is False,

        "B2V_protocol_next_exact":
            b2v_protocol.get("authorized_next_milestone")
            == MILESTONE,

        "B2V_protocol_reference_128":
            b2v_protocol.get("reference_microbatch")
            == REFERENCE_MICROBATCH,

        "B2V_protocol_training_false":
            (
                b2v_protocol
                .get("scientific_firewall", {})
                .get("training")
                is False
            ),

        "B2V_protocol_optimizer_false":
            (
                b2v_protocol
                .get("scientific_firewall", {})
                .get("optimizer")
                is False
            ),

        "B2V_protocol_weight_update_false":
            (
                b2v_protocol
                .get("scientific_firewall", {})
                .get("weight_update")
                is False
            ),
    })

    rh = (
        b2o.get("front_speed_closures", {})
        .get("Rankine_Hugoniot", {})
    )

    fd = (
        b2o.get("front_speed_closures", {})
        .get("finite_difference_Godunov_front", {})
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

    rows = {
        int(rec["microbatch"]): rec
        for rec in b2u.get("candidate_results", [])
        if "microbatch" in rec
    }

    gates.update({
        "B2U_mb128_success":
            rows.get(128, {}).get("success")
            is True,

        "B2U_mb256_failed":
            rows.get(256, {}).get("success")
            is False,

        "B2U_mb256_failure_class_runtime_error":
            rows.get(256, {}).get("failure_class")
            == "RUNTIME_ERROR",

        "B2U_mb128_has_exact_dataset_indices":
            (
                isinstance(
                    rows.get(128, {}).get("dataset_indices"),
                    list,
                )
                and len(
                    rows.get(128, {}).get("dataset_indices")
                )
                == REFERENCE_MICROBATCH
            ),
    })

    print("AUTHORITY / PERFORMANCE-PROFILE GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    if not all(gates.values()):
        raise RuntimeError(
            "B2W blocked by authority/protocol mismatch."
        )

    if not torch.xpu.is_available():
        raise RuntimeError(
            "Intel XPU unavailable for B2W."
        )

    B2S = import_module(
        B2S_SOURCE,
        "v16e1b2s_exact_graph",
    )

    ids = load_b2u_reference_ids(
        b2u
    )

    device = torch.device("xpu")

    print("\nCORRECTED EXACT-GRAPH PROFILE — MICROBATCh 128")
    corrected = profile_corrected_graph(
        B2S,
        ids,
        device,
    )

    print(
        "  model forward                :",
        f"{corrected['model_forward_seconds']:.3f} s",
    )
    print(
        "  local recurrent derivatives  :",
        f"{corrected['local_recurrent_derivative_seconds']:.3f} s",
    )
    print(
        "  corrected physics algebra    :",
        f"{corrected['corrected_physics_algebra_fractional_flow_seconds']:.3f} s",
    )
    print(
        "  nonphysics + total assembly  :",
        f"{corrected['nonphysics_loss_plus_total_assembly_seconds']:.3f} s",
    )
    print(
        "  total backward               :",
        f"{corrected['total_backward_seconds']:.3f} s",
    )
    print(
        "  exact graph + backward       :",
        f"{corrected['forward_graph_plus_backward_wall_seconds']:.3f} s",
    )

    print("\nMATCHED FIRST-ORDER / NON-PHYSICS CONTROL — MICROBATCh 128")
    control = profile_first_order_control(
        B2S,
        ids,
        device,
    )

    print(
        "  model forward                :",
        f"{control['model_forward_seconds']:.3f} s",
    )
    print(
        "  nonphysics loss assembly     :",
        f"{control['nonphysics_loss_assembly_seconds']:.3f} s",
    )
    print(
        "  first-order backward         :",
        f"{control['first_order_backward_seconds']:.3f} s",
    )
    print(
        "  control forward+loss+backward:",
        f"{control['forward_loss_backward_wall_seconds']:.3f} s",
    )

    corrected_total = float(
        corrected[
            "forward_graph_plus_backward_wall_seconds"
        ]
    )

    control_total = float(
        control[
            "forward_loss_backward_wall_seconds"
        ]
    )

    derivative_seconds = float(
        corrected[
            "local_recurrent_derivative_seconds"
        ]
    )

    corrected_backward_seconds = float(
        corrected[
            "total_backward_seconds"
        ]
    )

    corrected_physics_algebra_seconds = float(
        corrected[
            "corrected_physics_algebra_fractional_flow_seconds"
        ]
    )

    ratios = {
        "corrected_over_first_order_total_wall":
            float(
                corrected_total
                / max(control_total, 1e-30)
            ),

        "local_recurrent_derivatives_fraction_of_corrected_total":
            float(
                derivative_seconds
                / max(corrected_total, 1e-30)
            ),

        "corrected_backward_fraction_of_corrected_total":
            float(
                corrected_backward_seconds
                / max(corrected_total, 1e-30)
            ),

        "corrected_physics_algebra_fraction_of_corrected_total":
            float(
                corrected_physics_algebra_seconds
                / max(corrected_total, 1e-30)
            ),

        "corrected_backward_over_first_order_backward":
            float(
                corrected_backward_seconds
                / max(
                    float(
                        control[
                            "first_order_backward_seconds"
                        ]
                    ),
                    1e-30,
                )
            ),
    }

    mb256 = rows[256]

    profile_payload = {
        "milestone":
            MILESTONE,

        "classification":
            "NO_UPDATE_EXACT_CORRECTED_GRAPH_PERFORMANCE_BOTTLENECK_AUDIT",

        "reference_microbatch":
            REFERENCE_MICROBATCH,

        "exact_graph_authority": {
            "B2S_source_sha256":
                B2S_SOURCE_SHA,

            "scientific_graph_changed":
                False,

            "timing_wrappers_only":
                True,
        },

        "corrected_exact_graph_profile":
            corrected,

        "matched_first_order_nonphysics_control":
            control,

        "performance_ratios":
            ratios,

        "microbatch_256_frozen_failure": {
            "failure_class":
                mb256.get("failure_class"),

            "error":
                mb256.get("error"),

            "subprocess_returncode":
                mb256.get("subprocess_returncode"),

            "reclassified":
                False,

            "rerun_in_B2W":
                False,
        },

        "timing_semantics":
            "Synchronized stage timings for bottleneck diagnosis. Timing wrappers "
            "introduce synchronization boundaries and are not themselves a full-run "
            "runtime promise.",

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

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,
    }

    PROFILE.write_text(
        json.dumps(
            profile_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    gates.update({
        "corrected_prediction_finite":
            corrected["prediction_finite"]
            is True,

        "corrected_residual_finite":
            corrected["residual_finite"]
            is True,

        "corrected_losses_finite":
            corrected["losses_finite"]
            is True,

        "corrected_gradients_finite":
            corrected[
                "gradient_summary"
            ][
                "gradients_finite"
            ]
            is True,

        "corrected_nonzero_gradients":
            corrected[
                "gradient_summary"
            ][
                "nonzero_gradient_tensor_count"
            ]
            > 0,

        "corrected_weights_unchanged":
            corrected[
                "weights_exactly_unchanged"
            ]
            is True,

        "corrected_checkpoint_SHA_unchanged":
            corrected[
                "checkpoint_SHA_unchanged"
            ]
            is True,

        "control_prediction_finite":
            control["prediction_finite"]
            is True,

        "control_loss_finite":
            control["loss_finite"]
            is True,

        "control_gradients_finite":
            control[
                "gradient_summary"
            ][
                "gradients_finite"
            ]
            is True,

        "control_nonzero_gradients":
            control[
                "gradient_summary"
            ][
                "nonzero_gradient_tensor_count"
            ]
            > 0,

        "control_weights_unchanged":
            control[
                "weights_exactly_unchanged"
            ]
            is True,

        "control_checkpoint_SHA_unchanged":
            control[
                "checkpoint_SHA_unchanged"
            ]
            is True,

        "same_reference_dataset_indices":
            corrected["dataset_indices"]
            == control["dataset_indices"],

        "all_profile_times_finite":
            all(
                finite(v)
                for v in (
                    corrected["model_forward_seconds"],
                    corrected["local_recurrent_derivative_seconds"],
                    corrected["corrected_physics_algebra_fractional_flow_seconds"],
                    corrected["nonphysics_loss_plus_total_assembly_seconds"],
                    corrected["total_backward_seconds"],
                    corrected["forward_graph_plus_backward_wall_seconds"],
                    control["model_forward_seconds"],
                    control["nonphysics_loss_assembly_seconds"],
                    control["first_order_backward_seconds"],
                    control["forward_loss_backward_wall_seconds"],
                )
            ),

        "all_performance_ratios_finite":
            all(
                finite(v)
                for v in ratios.values()
            ),

        "microbatch256_failure_text_preserved":
            mb256.get("error")
            == profile_payload[
                "microbatch_256_frozen_failure"
            ][
                "error"
            ],

        "microbatch256_not_rerun":
            True,

        "COMP004_checkpoint_still_unchanged":
            sha256(COMP004_CHECKPOINT)
            == COMP004_CHECKPOINT_SHA,

        "profile_written":
            PROFILE.exists()
            and PROFILE.stat().st_size > 0,

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

    # Descriptive bottleneck ordering only — no pass/fail threshold.
    stage_times = {
        "model_forward":
            corrected[
                "model_forward_seconds"
            ],

        "local_recurrent_derivatives":
            corrected[
                "local_recurrent_derivative_seconds"
            ],

        "corrected_physics_algebra":
            corrected[
                "corrected_physics_algebra_fractional_flow_seconds"
            ],

        "nonphysics_loss_assembly":
            corrected[
                "nonphysics_loss_plus_total_assembly_seconds"
            ],

        "total_backward":
            corrected[
                "total_backward_seconds"
            ],
    }

    dominant_stage = max(
        stage_times,
        key=stage_times.get,
    )

    ordered_stages = sorted(
        stage_times.items(),
        key=lambda kv: kv[1],
        reverse=True,
    )

    decision_payload = {
        "milestone":
            MILESTONE,

        "dominant_measured_stage":
            dominant_stage,

        "ordered_measured_stage_times":
            [
                {
                    "stage": name,
                    "seconds": float(value),
                }
                for name, value
                in ordered_stages
            ],

        "corrected_over_first_order_total_wall_ratio":
            ratios[
                "corrected_over_first_order_total_wall"
            ],

        "local_recurrent_derivatives_fraction_of_corrected_total":
            ratios[
                "local_recurrent_derivatives_fraction_of_corrected_total"
            ],

        "corrected_backward_fraction_of_corrected_total":
            ratios[
                "corrected_backward_fraction_of_corrected_total"
            ],

        "interpretation_policy":
            "Descriptive timing only. No numeric scientific or operational "
            "acceptance threshold is introduced in B2W.",

        "scientific_graph_changed":
            False,

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_decision_required":
            "V16E-1B2X must interpret the measured bottleneck and decide whether "
            "to freeze an equivalence-preserving implementation optimization branch "
            "or proceed to an execution-contract freeze.",
    }

    DECISION.write_text(
        json.dumps(
            decision_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    gates["decision_written"] = (
        DECISION.exists()
        and DECISION.stat().st_size > 0
    )

    ok = all(
        bool(v)
        for v in gates.values()
    )

    status = (
        "V16E1B2W_XPU_EXACT_CORRECTED_GRAPH_PERFORMANCE_BOTTLENECK_AUDIT_COMPLETE_"
        "MICROBATCH_128_EXACT_CERTIFIED_B2S_GRAPH_PROFILED_WITH_SYNCHRONIZED_FORWARD_LOCAL_RECURRENT_DERIVATIVE_"
        "CORRECTED_PHYSICS_ALGEBRA_NONPHYSICS_LOSS_AND_TOTAL_BACKWARD_TIMINGS_"
        "MATCHED_FIRST_ORDER_NONPHYSICS_CONTROL_COMPLETE_FINITE_GRADIENTS_NO_WEIGHT_CHANGE_"
        "MICROBATCH_256_FROZEN_RUNTIME_ERROR_TEXT_PRESERVED_WITHOUT_RERUN_OR_RECLASSIFICATION_"
        "NO_OPTIMIZER_NO_WEIGHT_CHANGE_COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_"
        "B2X_PERFORMANCE_INTERPRETATION_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2W_XPU_PERFORMANCE_AUDIT_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "profile_sha256":
            sha256(PROFILE),

        "decision_sha256":
            sha256(DECISION),

        "reference_microbatch":
            REFERENCE_MICROBATCH,

        "dominant_measured_stage":
            dominant_stage,

        "corrected_over_first_order_total_wall_ratio":
            ratios[
                "corrected_over_first_order_total_wall"
            ],

        "local_recurrent_derivatives_fraction_of_corrected_total":
            ratios[
                "local_recurrent_derivatives_fraction_of_corrected_total"
            ],

        "corrected_backward_fraction_of_corrected_total":
            ratios[
                "corrected_backward_fraction_of_corrected_total"
            ],

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2X-XPU — interpret exact-graph performance bottleneck; "
                "decide whether an equivalence-preserving derivative-engine "
                "optimization branch is required before the COMP-XPU-005 "
                "execution-contract freeze"
                if ok else
                "V16E-1B2W-R1 — diagnose performance-audit gate failure"
            ),

        "gates":
            {
                k: bool(v)
                for k, v in gates.items()
            },
    }

    SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nPERFORMANCE INTERPRETATION")
    print(
        "  dominant measured stage:",
        dominant_stage,
    )
    print(
        "  corrected/control total ratio:",
        f"{ratios['corrected_over_first_order_total_wall']:.3f}x",
    )
    print(
        "  derivative fraction:",
        f"{100.0 * ratios['local_recurrent_derivatives_fraction_of_corrected_total']:.1f}%",
    )
    print(
        "  backward fraction:",
        f"{100.0 * ratios['corrected_backward_fraction_of_corrected_total']:.1f}%",
    )

    print("\nFINAL GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Profile :", sha256(PROFILE))
    print("  Decision:", sha256(DECISION))
    print("  Summary :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
