#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2Y-XPU
Warmed Steady-State Exact Corrected-Graph Benchmark

Purpose
-------
Establish a warmed, repeated steady-state performance baseline for the exact
certified corrected Stage-2 graph before any derivative-engine optimization
or COMP-XPU-005 execution contract is frozen.

NO TRAINING.
NO OPTIMIZER.
NO OPTIMIZER STEP.
NO WEIGHT UPDATE.
NO CHECKPOINT MUTATION.
NO OOD.
NO TOF.

Authority
---------
V16E-1B2X authorizes this benchmark only.

Reference
---------
Microbatch:
    128

Dataset rows:
    exact same frozen 128 rows used by B2U and B2W.

Corrected graph:
    exact frozen B2S complete_corrected_total_loss() implementation.

Benchmark plan
--------------
Corrected exact graph:
    1 unmeasured warm-up iteration
    3 measured uninstrumented forward+loss+backward iterations

Matched first-order/non-physics control:
    1 unmeasured warm-up iteration
    3 measured uninstrumented forward+loss+backward iterations

Warmed synchronized stage profile:
    1 corrected exact-graph stage-decomposition iteration
    using the already-certified B2W profiling function after runtime warm-up

Every iteration:
    * recreates a fresh autograd graph
    * executes backward()
    * synchronizes XPU
    * verifies finite gradients
    * verifies exact in-memory parameter equality
    * verifies frozen checkpoint SHA
    * clears gradients
    * performs NO optimizer step

Steady-state statistics
-----------------------
The uninstrumented measured repeats are authoritative for operational timing:

    corrected median / mean wall time
    control median / mean wall time
    corrected/control median / mean ratio
    corrected median profiles/s

The synchronized stage profile is diagnostic for attribution only.

Diagnostic full-run projection
------------------------------
The frozen B2U execution geometry is retained:

    train profiles : 11520
    logical batch  : 8192
    target epochs  : 800

The projection is recomputed from the WARMED CORRECTED MEDIAN.
It is an operational diagnostic only, not a runtime promise.

No scientific numeric acceptance threshold is introduced.

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

import numpy as np
import torch


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2Y-XPU"

REFERENCE_MICROBATCH = 128
WARMUP_REPEATS = 1
MEASURED_REPEATS = 3

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

# Exact corrected-graph authority.
B2S_SOURCE = (
    R
    / "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
)
B2S_SOURCE_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"

# B2U reference rows / execution geometry.
B2U_DIR = (
    R / "output"
    / "V16_E1B2U_XPU_EXTENDED_CORRECTED_RESIDUAL_THROUGHPUT"
)
B2U_RESULTS = B2U_DIR / "V16E1B2U_Extended_Throughput_Memory_Results.json"
B2U_RESULTS_SHA = "e71f398c88feee2260c50109055b917103e76800365954823f320457a0d30075"

# Certified B2W stage profiler.
B2W_SOURCE = (
    R
    / "PAD_Stream_V16E1B2W_XPU_Exact_Graph_Performance_Bottleneck_Audit.py"
)
B2W_SOURCE_SHA = "6027594adc37257fcfd2c129e6fa723572c3cadb473a746abd3ac613fe4512da"

B2W_DIR = (
    R / "output"
    / "V16_E1B2W_XPU_EXACT_GRAPH_PERFORMANCE_BOTTLENECK_AUDIT"
)
B2W_PROFILE = B2W_DIR / "V16E1B2W_Exact_Graph_Performance_Profile.json"
B2W_PROFILE_SHA = "0002769ed3be891dcc7c738eb801ac87915ee28db27d60faf6879c5580b491c2"

# B2X authority.
B2X_SOURCE = (
    R
    / "PAD_Stream_V16E1B2X_XPU_B2W_Interpretation_Warmed_Benchmark_Protocol_Freeze.py"
)
B2X_SOURCE_SHA = "b7da3272cb8621dcbe69a2881980969aeaa6c7da7b3ad43d271a5806e9f879e6"

B2X_DIR = (
    R / "output"
    / "V16_E1B2X_XPU_B2W_INTERPRETATION_WARMED_BENCHMARK_PROTOCOL"
)
B2X_INTERPRETATION = B2X_DIR / "V16E1B2X_B2W_Performance_Interpretation.json"
B2X_PROTOCOL = B2X_DIR / "V16E1B2X_B2Y_Warmed_Steady_State_Protocol.json"
B2X_HANDOFF = B2X_DIR / "V16E1B2X_B2Y_Handoff.md"
B2X_SUMMARY = B2X_DIR / "PAD_Stream_V16E1B2X_XPU_Summary.json"

B2X_INTERPRETATION_SHA = "c1738bc884722662478432cb809d33b5b0b27f8da6572b2ffe7f64e9caa92020"
B2X_PROTOCOL_SHA = "050b392482ceed9ccc7b8c12a95cb349abe4d5226101492ed71bc7695da3b453"
B2X_HANDOFF_SHA = "49aa8c1461927b19265eeae9666b216b1fbd4e88d498e97cfb97432ab1a00882"
B2X_SUMMARY_SHA = "1db5ea519eefcf9bbd28ac2a364b149e81ad24a169b1442c83d6dfdede2f77f2"

EXPECTED_B2X_STATUS = (
    "V16E1B2X_XPU_B2W_PERFORMANCE_INTERPRETATION_AND_WARMED_STEADY_STATE_BENCHMARK_PROTOCOL_FROZEN_"
    "B2W_EXACT_GRAPH_EXECUTION_CERTIFIED_BUT_FIRST_PASS_SYNCHRONIZED_226X_RATIO_NOT_PROMOTED_TO_STEADY_STATE_"
    "CORRECTED_VS_CONTROL_FORWARD_TIMING_DISCREPANCY_BOUND_AS_DIRECT_EVIDENCE_OF_FIRST_USE_RUNTIME_CONTAMINATION_WITHOUT_CAUSE_GUESS_"
    "DERIVATIVE_ENGINE_COST_REMAINS_MATERIALLY_LARGE_"
    "B2Y_MICROBATCH_128_ONE_WARMUP_THREE_REPEAT_UNINSTRUMENTED_CORRECTED_AND_MATCHED_CONTROL_PLUS_WARMED_STAGE_PROFILE_AUTHORIZED_"
    "NO_TRAINING_NO_OPTIMIZER_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2Y_XPU_WARMED_STEADY_STATE_EXACT_GRAPH_BENCHMARK"
)
OUT.mkdir(parents=True, exist_ok=True)

RESULTS = OUT / "V16E1B2Y_Warmed_Steady_State_Results.json"
DECISION = OUT / "V16E1B2Y_Steady_State_Performance_Decision.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2Y_XPU_Summary.json"


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


def clear_gradients(model, xi, p11):
    for p in model.parameters():
        p.grad = None

    if xi.grad is not None:
        xi.grad = None

    if p11.grad is not None:
        p11.grad = None


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


def microbatches_per_epoch(
    n_train: int,
    logical_batch: int,
    microbatch: int,
) -> int:
    total = 0

    for b0 in range(
        0,
        n_train,
        logical_batch,
    ):
        chunk = min(
            logical_batch,
            n_train - b0,
        )

        total += int(
            math.ceil(
                chunk / microbatch
            )
        )

    return total


def get_reference_ids_and_geometry(b2u):
    rows = {
        int(rec["microbatch"]): rec
        for rec in b2u.get(
            "candidate_results",
            [],
        )
        if "microbatch" in rec
    }

    rec128 = rows.get(
        REFERENCE_MICROBATCH
    )

    if rec128 is None:
        raise RuntimeError(
            "B2U microbatch-128 record missing."
        )

    ids = rec128.get(
        "dataset_indices"
    )

    if (
        not isinstance(ids, list)
        or len(ids)
        != REFERENCE_MICROBATCH
    ):
        raise RuntimeError(
            "B2U microbatch-128 reference ids missing/incomplete."
        )

    split = b2u.get(
        "training_split",
        {},
    )

    return (
        np.asarray(
            ids,
            dtype=int,
        ),
        int(split["train_profiles"]),
        int(split["logical_batch"]),
        int(split["target_epochs"]),
    )


def load_model_and_batch(
    B2S,
    B2W,
    ids,
    device,
    module_suffix,
):
    # Reuse the already-certified B2W loader behavior, but use unique imported
    # module names in this process to avoid accidental naming collisions.
    M = B2S.import_module(
        B2S.BASE_RUNNER,
        f"b2y_base_{module_suffix}",
    )

    J = B2S.import_module(
        B2S.B2J_SOURCE,
        f"b2y_comp004_{module_suffix}",
    )

    d = np.load(
        DATASET
    )

    EtaModel = J.build_eta_model_class(
        M
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

    xi = (
        torch.from_numpy(
            d["xi"][ids]
        )
        .to(device)
        .detach()
        .clone()
        .requires_grad_(True)
    )

    Sw = torch.from_numpy(
        d["Sw"][ids]
    ).to(device)

    p11 = (
        torch.from_numpy(
            d["p11"][ids]
        )
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

    return (
        M,
        model,
        xi,
        Sw,
        p11,
        ai,
        at,
    )


# =============================================================================
# Uninstrumented corrected repeats
# =============================================================================

def corrected_iteration(
    B2S,
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

    t0 = time.perf_counter()

    S_pred, residual, parts = (
        B2S.complete_corrected_total_loss(
            M,
            model,
            xi,
            Sw,
            p11,
            ai,
            at,
        )
    )

    if not torch.isfinite(
        S_pred
    ).all().item():
        raise RuntimeError(
            "Corrected repeat produced nonfinite prediction."
        )

    if not torch.isfinite(
        residual
    ).all().item():
        raise RuntimeError(
            "Corrected repeat produced nonfinite residual."
        )

    if not all(
        torch.isfinite(v).all().item()
        for v in parts.values()
    ):
        raise RuntimeError(
            "Corrected repeat produced nonfinite loss."
        )

    parts["total"].backward()

    sync_xpu()

    elapsed = (
        time.perf_counter()
        - t0
    )

    grads = gradient_summary(
        model
    )

    if not grads[
        "gradients_finite"
    ]:
        raise RuntimeError(
            "Corrected repeat produced nonfinite parameter gradients."
        )

    if grads[
        "nonzero_gradient_tensor_count"
    ] <= 0:
        raise RuntimeError(
            "Corrected repeat produced no nonzero parameter gradients."
        )

    weights_unchanged = parameters_equal(
        model,
        param_before,
    )

    if not weights_unchanged:
        raise RuntimeError(
            "Corrected repeat changed model parameters."
        )

    checkpoint_unchanged = (
        sha256(
            COMP004_CHECKPOINT
        )
        == COMP004_CHECKPOINT_SHA
    )

    if not checkpoint_unchanged:
        raise RuntimeError(
            "Corrected repeat changed frozen checkpoint SHA."
        )

    rec = {
        "wall_seconds":
            float(elapsed),

        "profiles_per_second":
            float(
                REFERENCE_MICROBATCH
                / elapsed
            ),

        "prediction_finite":
            True,

        "residual_finite":
            True,

        "losses_finite":
            True,

        "gradient_summary":
            grads,

        "weights_exactly_unchanged":
            True,

        "checkpoint_SHA_unchanged":
            True,

        "peak_xpu_memory_bytes":
            peak_memory_bytes(),

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
    }

    clear_gradients(
        model,
        xi,
        p11,
    )

    del (
        S_pred,
        residual,
        parts,
    )

    return rec


# =============================================================================
# Matched first-order repeats
# =============================================================================

def control_iteration(
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

    t0 = time.perf_counter()

    S_pred = model(
        xi,
        p11,
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
        + M.LAMBDA_BC * Lbc
        + M.LAMBDA_TIP * Ltip
        + M.LAMBDA_ANCHOR * La
        + M.LAMBDA_MONO * Lmono
    )

    if not torch.isfinite(
        S_pred
    ).all().item():
        raise RuntimeError(
            "Control repeat produced nonfinite prediction."
        )

    if not torch.isfinite(
        total
    ).all().item():
        raise RuntimeError(
            "Control repeat produced nonfinite loss."
        )

    total.backward()

    sync_xpu()

    elapsed = (
        time.perf_counter()
        - t0
    )

    grads = gradient_summary(
        model
    )

    if not grads[
        "gradients_finite"
    ]:
        raise RuntimeError(
            "Control repeat produced nonfinite parameter gradients."
        )

    if grads[
        "nonzero_gradient_tensor_count"
    ] <= 0:
        raise RuntimeError(
            "Control repeat produced no nonzero parameter gradients."
        )

    weights_unchanged = parameters_equal(
        model,
        param_before,
    )

    if not weights_unchanged:
        raise RuntimeError(
            "Control repeat changed model parameters."
        )

    checkpoint_unchanged = (
        sha256(
            COMP004_CHECKPOINT
        )
        == COMP004_CHECKPOINT_SHA
    )

    if not checkpoint_unchanged:
        raise RuntimeError(
            "Control repeat changed frozen checkpoint SHA."
        )

    rec = {
        "wall_seconds":
            float(elapsed),

        "profiles_per_second":
            float(
                REFERENCE_MICROBATCH
                / elapsed
            ),

        "prediction_finite":
            True,

        "loss_finite":
            True,

        "gradient_summary":
            grads,

        "weights_exactly_unchanged":
            True,

        "checkpoint_SHA_unchanged":
            True,

        "peak_xpu_memory_bytes":
            peak_memory_bytes(),

        "losses": {
            "data":
                float(
                    Ld.detach().cpu()
                ),

            "bc_inj":
                float(
                    Lbc.detach().cpu()
                ),

            "bc_tip":
                float(
                    Ltip.detach().cpu()
                ),

            "anchor":
                float(
                    La.detach().cpu()
                ),

            "mono":
                float(
                    Lmono.detach().cpu()
                ),

            "total_without_physics":
                float(
                    total.detach().cpu()
                ),
        },
    }

    clear_gradients(
        model,
        xi,
        p11,
    )

    del (
        S_pred,
        Ld,
        Lbc,
        Ltip,
        La,
        Lmono,
        total,
    )

    return rec


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2Y-XPU")
    print("Warmed Steady-State Exact Corrected-Graph Benchmark")
    print("=" * 80)
    print("NO TRAINING — NO OPTIMIZER — NO WEIGHT UPDATE.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2Y summary already exists; refusing overwrite."
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

        "B2W_source_SHA_exact":
            exact(
                B2W_SOURCE,
                B2W_SOURCE_SHA,
            ),

        "B2W_profile_SHA_exact":
            exact(
                B2W_PROFILE,
                B2W_PROFILE_SHA,
            ),

        "B2X_source_SHA_exact":
            exact(
                B2X_SOURCE,
                B2X_SOURCE_SHA,
            ),

        "B2X_interpretation_SHA_exact":
            exact(
                B2X_INTERPRETATION,
                B2X_INTERPRETATION_SHA,
            ),

        "B2X_protocol_SHA_exact":
            exact(
                B2X_PROTOCOL,
                B2X_PROTOCOL_SHA,
            ),

        "B2X_handoff_SHA_exact":
            exact(
                B2X_HANDOFF,
                B2X_HANDOFF_SHA,
            ),

        "B2X_summary_SHA_exact":
            exact(
                B2X_SUMMARY,
                B2X_SUMMARY_SHA,
            ),
    }

    b2u = (
        read_json(
            B2U_RESULTS
        )
        if B2U_RESULTS.exists()
        else {}
    )

    b2w_profile = (
        read_json(
            B2W_PROFILE
        )
        if B2W_PROFILE.exists()
        else {}
    )

    b2x = (
        read_json(
            B2X_SUMMARY
        )
        if B2X_SUMMARY.exists()
        else {}
    )

    b2x_protocol = (
        read_json(
            B2X_PROTOCOL
        )
        if B2X_PROTOCOL.exists()
        else {}
    )

    gates.update({
        "B2X_status_exact":
            b2x.get(
                "status"
            )
            == EXPECTED_B2X_STATUS,

        "B2X_reference_microbatch_128":
            b2x.get(
                "reference_microbatch"
            )
            == REFERENCE_MICROBATCH,

        "B2X_B2Y_true":
            b2x.get(
                "B2Y_authorized"
            )
            is True,

        "B2X_training_false":
            b2x.get(
                "COMP_XPU_005_full_training_authorized"
            )
            is False,

        "B2X_B3_false":
            b2x.get(
                "B3_authorized"
            )
            is False,

        "B2X_protocol_next_exact":
            b2x_protocol.get(
                "authorized_next_milestone"
            )
            == MILESTONE,

        "B2X_protocol_reference_128":
            (
                b2x_protocol
                .get("reference", {})
                .get("microbatch")
                == REFERENCE_MICROBATCH
            ),

        "B2X_corrected_warmup_1":
            (
                b2x_protocol
                .get("corrected_graph_runs", {})
                .get("unmeasured_warmup_iterations")
                == WARMUP_REPEATS
            ),

        "B2X_corrected_measured_3":
            (
                b2x_protocol
                .get("corrected_graph_runs", {})
                .get("measured_uninstrumented_iterations")
                == MEASURED_REPEATS
            ),

        "B2X_control_warmup_1":
            (
                b2x_protocol
                .get("matched_control_runs", {})
                .get("unmeasured_warmup_iterations")
                == WARMUP_REPEATS
            ),

        "B2X_control_measured_3":
            (
                b2x_protocol
                .get("matched_control_runs", {})
                .get("measured_uninstrumented_iterations")
                == MEASURED_REPEATS
            ),

        "B2X_protocol_training_false":
            (
                b2x_protocol
                .get("scientific_firewall", {})
                .get("training")
                is False
            ),

        "B2X_protocol_optimizer_false":
            (
                b2x_protocol
                .get("scientific_firewall", {})
                .get("optimizer")
                is False
            ),

        "B2X_protocol_weight_update_false":
            (
                b2x_protocol
                .get("scientific_firewall", {})
                .get("weight_update")
                is False
            ),
    })

    (
        reference_ids,
        n_train,
        logical_batch,
        target_epochs,
    ) = get_reference_ids_and_geometry(
        b2u
    )

    b2w_corrected_ids = (
        b2w_profile
        .get(
            "corrected_exact_graph_profile",
            {},
        )
        .get(
            "dataset_indices"
        )
    )

    b2w_control_ids = (
        b2w_profile
        .get(
            "matched_first_order_nonphysics_control",
            {},
        )
        .get(
            "dataset_indices"
        )
    )

    gates.update({
        "B2U_reference_ids_128":
            len(
                reference_ids
            )
            == REFERENCE_MICROBATCH,

        "B2W_reference_ids_match_B2U":
            (
                [int(x) for x in reference_ids]
                == b2w_corrected_ids
                == b2w_control_ids
            ),

        "B2U_train_profiles_positive":
            n_train > 0,

        "B2U_logical_batch_positive":
            logical_batch > 0,

        "B2U_target_epochs_positive":
            target_epochs > 0,
    })

    print("AUTHORITY / WARMED-BENCHMARK GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    if not all(
        gates.values()
    ):
        raise RuntimeError(
            "B2Y blocked by authority/protocol mismatch."
        )

    if not torch.xpu.is_available():
        raise RuntimeError(
            "Intel XPU unavailable for B2Y."
        )

    B2S = import_module(
        B2S_SOURCE,
        "v16e1b2s_exact_graph_b2y",
    )

    B2W = import_module(
        B2W_SOURCE,
        "v16e1b2w_stage_profiler_b2y",
    )

    device = torch.device(
        "xpu"
    )

    # -------------------------------------------------------------------------
    # Corrected exact graph: same model/batch across warm-up + measured repeats.
    # -------------------------------------------------------------------------

    (
        M_corr,
        model_corr,
        xi_corr,
        Sw_corr,
        p11_corr,
        ai_corr,
        at_corr,
    ) = load_model_and_batch(
        B2S,
        B2W,
        reference_ids,
        device,
        "corrected",
    )

    corr_param_before = clone_parameters(
        model_corr
    )

    print("\nCORRECTED EXACT GRAPH — WARM-UP")
    corrected_warmup = corrected_iteration(
        B2S,
        M_corr,
        model_corr,
        xi_corr,
        Sw_corr,
        p11_corr,
        ai_corr,
        at_corr,
        corr_param_before,
    )

    print(
        "  warm-up completed",
        f"| wall={corrected_warmup['wall_seconds']:.3f}s",
        f"| throughput={corrected_warmup['profiles_per_second']:.3f} profiles/s",
    )

    corrected_repeats = []

    print("\nCORRECTED EXACT GRAPH — MEASURED REPEATS")

    for i in range(
        MEASURED_REPEATS
    ):
        rec = corrected_iteration(
            B2S,
            M_corr,
            model_corr,
            xi_corr,
            Sw_corr,
            p11_corr,
            ai_corr,
            at_corr,
            corr_param_before,
        )

        corrected_repeats.append(
            rec
        )

        print(
            f"  repeat {i + 1}: "
            f"{rec['wall_seconds']:.3f}s "
            f"| {rec['profiles_per_second']:.3f} profiles/s "
            f"| grad_norm={rec['gradient_summary']['gradient_l2_norm']:.6e}"
        )

    if not parameters_equal(
        model_corr,
        corr_param_before,
    ):
        raise RuntimeError(
            "Corrected model changed after repeat block."
        )

    if sha256(
        COMP004_CHECKPOINT
    ) != COMP004_CHECKPOINT_SHA:
        raise RuntimeError(
            "Checkpoint changed after corrected repeat block."
        )

    # -------------------------------------------------------------------------
    # Matched first-order control: fresh model, same exact rows.
    # -------------------------------------------------------------------------

    (
        M_ctl,
        model_ctl,
        xi_ctl,
        Sw_ctl,
        p11_ctl,
        ai_ctl,
        at_ctl,
    ) = load_model_and_batch(
        B2S,
        B2W,
        reference_ids,
        device,
        "control",
    )

    ctl_param_before = clone_parameters(
        model_ctl
    )

    print("\nMATCHED FIRST-ORDER CONTROL — WARM-UP")
    control_warmup = control_iteration(
        M_ctl,
        model_ctl,
        xi_ctl,
        Sw_ctl,
        p11_ctl,
        ai_ctl,
        at_ctl,
        ctl_param_before,
    )

    print(
        "  warm-up completed",
        f"| wall={control_warmup['wall_seconds']:.3f}s",
        f"| throughput={control_warmup['profiles_per_second']:.3f} profiles/s",
    )

    control_repeats = []

    print("\nMATCHED FIRST-ORDER CONTROL — MEASURED REPEATS")

    for i in range(
        MEASURED_REPEATS
    ):
        rec = control_iteration(
            M_ctl,
            model_ctl,
            xi_ctl,
            Sw_ctl,
            p11_ctl,
            ai_ctl,
            at_ctl,
            ctl_param_before,
        )

        control_repeats.append(
            rec
        )

        print(
            f"  repeat {i + 1}: "
            f"{rec['wall_seconds']:.3f}s "
            f"| {rec['profiles_per_second']:.3f} profiles/s "
            f"| grad_norm={rec['gradient_summary']['gradient_l2_norm']:.6e}"
        )

    if not parameters_equal(
        model_ctl,
        ctl_param_before,
    ):
        raise RuntimeError(
            "Control model changed after repeat block."
        )

    if sha256(
        COMP004_CHECKPOINT
    ) != COMP004_CHECKPOINT_SHA:
        raise RuntimeError(
            "Checkpoint changed after control repeat block."
        )

    # -------------------------------------------------------------------------
    # Warmed synchronized stage profile.
    #
    # Reuse exact certified B2W stage profiler. Runtime has already executed
    # multiple corrected/control graphs in this process, so this is not the
    # first corrected execution of the process.
    # -------------------------------------------------------------------------

    print("\nWARMED SYNCHRONIZED CORRECTED STAGE PROFILE")

    warmed_stage_profile = (
        B2W.profile_corrected_graph(
            B2S,
            reference_ids,
            device,
        )
    )

    print(
        "  model forward                :",
        f"{warmed_stage_profile['model_forward_seconds']:.3f} s",
    )
    print(
        "  local recurrent derivatives  :",
        f"{warmed_stage_profile['local_recurrent_derivative_seconds']:.3f} s",
    )
    print(
        "  corrected physics algebra    :",
        f"{warmed_stage_profile['corrected_physics_algebra_fractional_flow_seconds']:.3f} s",
    )
    print(
        "  nonphysics + total assembly  :",
        f"{warmed_stage_profile['nonphysics_loss_plus_total_assembly_seconds']:.3f} s",
    )
    print(
        "  total backward               :",
        f"{warmed_stage_profile['total_backward_seconds']:.3f} s",
    )

    # -------------------------------------------------------------------------
    # Steady-state statistics from uninstrumented measured repeats.
    # -------------------------------------------------------------------------

    corr_times = [
        float(rec["wall_seconds"])
        for rec
        in corrected_repeats
    ]

    ctl_times = [
        float(rec["wall_seconds"])
        for rec
        in control_repeats
    ]

    corr_median = float(
        statistics.median(
            corr_times
        )
    )

    corr_mean = float(
        statistics.mean(
            corr_times
        )
    )

    ctl_median = float(
        statistics.median(
            ctl_times
        )
    )

    ctl_mean = float(
        statistics.mean(
            ctl_times
        )
    )

    median_ratio = float(
        corr_median
        / max(
            ctl_median,
            1e-30,
        )
    )

    mean_ratio = float(
        corr_mean
        / max(
            ctl_mean,
            1e-30,
        )
    )

    corrected_median_throughput = float(
        REFERENCE_MICROBATCH
        / corr_median
    )

    n_micro = microbatches_per_epoch(
        n_train=n_train,
        logical_batch=logical_batch,
        microbatch=REFERENCE_MICROBATCH,
    )

    projected_epoch_seconds = float(
        n_micro
        * corr_median
    )

    projected_hours_per_epoch = float(
        projected_epoch_seconds
        / 3600.0
    )

    projected_days_800 = float(
        projected_epoch_seconds
        * target_epochs
        / 86400.0
    )

    # -------------------------------------------------------------------------
    # Final gates.
    # -------------------------------------------------------------------------

    gates.update({
        "corrected_warmup_completed":
            finite(
                corrected_warmup[
                    "wall_seconds"
                ]
            ),

        "corrected_three_measured_repeats":
            len(
                corrected_repeats
            )
            == MEASURED_REPEATS,

        "control_warmup_completed":
            finite(
                control_warmup[
                    "wall_seconds"
                ]
            ),

        "control_three_measured_repeats":
            len(
                control_repeats
            )
            == MEASURED_REPEATS,

        "all_corrected_repeat_times_finite":
            all(
                finite(x)
                for x in corr_times
            ),

        "all_control_repeat_times_finite":
            all(
                finite(x)
                for x in ctl_times
            ),

        "all_corrected_gradients_finite":
            all(
                rec[
                    "gradient_summary"
                ][
                    "gradients_finite"
                ]
                is True
                for rec in corrected_repeats
            ),

        "all_control_gradients_finite":
            all(
                rec[
                    "gradient_summary"
                ][
                    "gradients_finite"
                ]
                is True
                for rec in control_repeats
            ),

        "all_corrected_weights_unchanged":
            all(
                rec[
                    "weights_exactly_unchanged"
                ]
                is True
                for rec in corrected_repeats
            ),

        "all_control_weights_unchanged":
            all(
                rec[
                    "weights_exactly_unchanged"
                ]
                is True
                for rec in control_repeats
            ),

        "all_corrected_checkpoint_SHA_unchanged":
            all(
                rec[
                    "checkpoint_SHA_unchanged"
                ]
                is True
                for rec in corrected_repeats
            ),

        "all_control_checkpoint_SHA_unchanged":
            all(
                rec[
                    "checkpoint_SHA_unchanged"
                ]
                is True
                for rec in control_repeats
            ),

        "warmed_stage_prediction_finite":
            warmed_stage_profile[
                "prediction_finite"
            ]
            is True,

        "warmed_stage_residual_finite":
            warmed_stage_profile[
                "residual_finite"
            ]
            is True,

        "warmed_stage_losses_finite":
            warmed_stage_profile[
                "losses_finite"
            ]
            is True,

        "warmed_stage_gradients_finite":
            warmed_stage_profile[
                "gradient_summary"
            ][
                "gradients_finite"
            ]
            is True,

        "warmed_stage_weights_unchanged":
            warmed_stage_profile[
                "weights_exactly_unchanged"
            ]
            is True,

        "warmed_stage_checkpoint_SHA_unchanged":
            warmed_stage_profile[
                "checkpoint_SHA_unchanged"
            ]
            is True,

        "same_reference_rows_corrected_control_stage":
            (
                [int(x) for x in reference_ids]
                == warmed_stage_profile[
                    "dataset_indices"
                ]
            ),

        "steady_state_statistics_finite":
            all(
                finite(v)
                for v in (
                    corr_median,
                    corr_mean,
                    ctl_median,
                    ctl_mean,
                    median_ratio,
                    mean_ratio,
                    corrected_median_throughput,
                    projected_hours_per_epoch,
                    projected_days_800,
                )
            ),

        "COMP004_checkpoint_still_unchanged":
            sha256(
                COMP004_CHECKPOINT
            )
            == COMP004_CHECKPOINT_SHA,

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

    results_payload = {
        "milestone":
            MILESTONE,

        "classification":
            "WARMED_REPEATED_NO_UPDATE_STEADY_STATE_EXACT_GRAPH_BENCHMARK",

        "reference": {
            "microbatch":
                REFERENCE_MICROBATCH,

            "dataset_indices":
                [int(x) for x in reference_ids],

            "checkpoint_sha256":
                COMP004_CHECKPOINT_SHA,

            "exact_B2S_source_sha256":
                B2S_SOURCE_SHA,
        },

        "corrected_exact_graph": {
            "warmup":
                corrected_warmup,

            "measured_repeats":
                corrected_repeats,

            "wall_times_seconds":
                corr_times,

            "median_wall_seconds":
                corr_median,

            "mean_wall_seconds":
                corr_mean,

            "median_profiles_per_second":
                corrected_median_throughput,
        },

        "matched_first_order_control": {
            "warmup":
                control_warmup,

            "measured_repeats":
                control_repeats,

            "wall_times_seconds":
                ctl_times,

            "median_wall_seconds":
                ctl_median,

            "mean_wall_seconds":
                ctl_mean,
        },

        "steady_state_ratios": {
            "median_corrected_over_control":
                median_ratio,

            "mean_corrected_over_control":
                mean_ratio,
        },

        "warmed_synchronized_stage_profile":
            warmed_stage_profile,

        "diagnostic_full_run_projection_from_corrected_median": {
            "train_profiles":
                n_train,

            "logical_batch":
                logical_batch,

            "microbatch":
                REFERENCE_MICROBATCH,

            "microbatches_per_epoch":
                n_micro,

            "target_epochs":
                target_epochs,

            "projected_seconds_per_epoch":
                projected_epoch_seconds,

            "projected_hours_per_epoch":
                projected_hours_per_epoch,

            "projected_days_for_target_epochs":
                projected_days_800,

            "semantics":
                "operational diagnostic only; not a runtime promise",
        },

        "timing_semantics": {
            "steady_state_authority":
                "uninstrumented measured-repeat median/mean after one unmeasured warm-up",

            "stage_profile_role":
                "diagnostic attribution only; synchronized wrappers add timing boundaries",
        },

        "optimizer_created":
            False,

        "optimizer_step":
            False,

        "weight_update":
            False,

        "checkpoint_mutated":
            False,

        "scientific_settings_changed":
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

    # Descriptive dominant stage from the warmed profile only.
    stage_times = {
        "model_forward":
            float(
                warmed_stage_profile[
                    "model_forward_seconds"
                ]
            ),

        "local_recurrent_derivatives":
            float(
                warmed_stage_profile[
                    "local_recurrent_derivative_seconds"
                ]
            ),

        "corrected_physics_algebra":
            float(
                warmed_stage_profile[
                    "corrected_physics_algebra_fractional_flow_seconds"
                ]
            ),

        "nonphysics_loss_assembly":
            float(
                warmed_stage_profile[
                    "nonphysics_loss_plus_total_assembly_seconds"
                ]
            ),

        "total_backward":
            float(
                warmed_stage_profile[
                    "total_backward_seconds"
                ]
            ),
    }

    dominant_stage = max(
        stage_times,
        key=stage_times.get,
    )

    decision_payload = {
        "milestone":
            MILESTONE,

        "steady_state_corrected_median_seconds":
            corr_median,

        "steady_state_corrected_mean_seconds":
            corr_mean,

        "steady_state_control_median_seconds":
            ctl_median,

        "steady_state_control_mean_seconds":
            ctl_mean,

        "steady_state_median_corrected_over_control_ratio":
            median_ratio,

        "steady_state_mean_corrected_over_control_ratio":
            mean_ratio,

        "steady_state_corrected_median_profiles_per_second":
            corrected_median_throughput,

        "warmed_dominant_measured_stage":
            dominant_stage,

        "warmed_stage_times_seconds":
            stage_times,

        "diagnostic_projection": {
            "hours_per_epoch":
                projected_hours_per_epoch,

            "days_for_target_epochs":
                projected_days_800,

            "target_epochs":
                target_epochs,

            "semantics":
                "operational diagnostic only; not a runtime promise",
        },

        "optimization_branch_authorized":
            False,

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_decision_required":
            "V16E-1B2Z-XPU must interpret the warmed steady-state baseline and "
            "decide whether an equivalence-preserving derivative-engine optimization "
            "branch is required before the COMP-XPU-005 execution-contract freeze.",
    }

    DECISION.write_text(
        json.dumps(
            decision_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    gates.update({
        "results_written":
            RESULTS.exists()
            and RESULTS.stat().st_size > 0,

        "decision_written":
            DECISION.exists()
            and DECISION.stat().st_size > 0,

        "COMP005_training_not_authorized":
            True,

        "B3_not_authorized":
            True,
    })

    ok = all(
        bool(v)
        for v in gates.values()
    )

    status = (
        "V16E1B2Y_XPU_WARMED_STEADY_STATE_EXACT_CORRECTED_GRAPH_BENCHMARK_COMPLETE_"
        "MICROBATCH_128_EXACT_B2S_GRAPH_AND_EXACT_B2U_B2W_REFERENCE_ROWS_PRESERVED_"
        "ONE_UNMEASURED_WARMUP_PLUS_THREE_UNINSTRUMENTED_MEASURED_CORRECTED_REPEATS_COMPLETE_"
        "ONE_UNMEASURED_WARMUP_PLUS_THREE_UNINSTRUMENTED_MEASURED_MATCHED_FIRST_ORDER_CONTROL_REPEATS_COMPLETE_"
        "WARMED_SYNCHRONIZED_CORRECTED_STAGE_PROFILE_COMPLETE_"
        "STEADY_STATE_MEDIAN_MEAN_THROUGHPUT_CORRECTED_CONTROL_RATIOS_AND_DIAGNOSTIC_FULL_RUN_PROJECTION_FROZEN_"
        "FINITE_GRADIENTS_NO_WEIGHT_CHANGE_NO_OPTIMIZER_COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_"
        "B2Z_PERFORMANCE_INTERPRETATION_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2Y_XPU_WARMED_BENCHMARK_COMPLETED_WITH_GATE_FAILURE"
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

        "decision_sha256":
            sha256(
                DECISION
            ),

        "reference_microbatch":
            REFERENCE_MICROBATCH,

        "corrected_median_seconds":
            corr_median,

        "corrected_mean_seconds":
            corr_mean,

        "control_median_seconds":
            ctl_median,

        "control_mean_seconds":
            ctl_mean,

        "median_corrected_over_control_ratio":
            median_ratio,

        "mean_corrected_over_control_ratio":
            mean_ratio,

        "corrected_median_profiles_per_second":
            corrected_median_throughput,

        "diagnostic_hours_per_epoch":
            projected_hours_per_epoch,

        "diagnostic_days_for_target_epochs":
            projected_days_800,

        "warmed_dominant_measured_stage":
            dominant_stage,

        "optimization_branch_authorized":
            False,

        "COMP_XPU_005_full_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2Z-XPU — interpret warmed steady-state corrected/control "
                "performance and stage attribution; decide whether an equivalence-"
                "preserving derivative-engine optimization branch is required before "
                "freezing the COMP-XPU-005 execution contract"
                if ok else
                "V16E-1B2Y-R1 — diagnose warmed-benchmark gate failure"
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

    print("\nSTEADY-STATE RESULTS")
    print(
        "  corrected times:",
        " / ".join(
            f"{x:.3f}s"
            for x in corr_times
        ),
    )
    print(
        "  corrected median / mean:",
        f"{corr_median:.3f}s / {corr_mean:.3f}s",
    )
    print(
        "  control times:",
        " / ".join(
            f"{x:.3f}s"
            for x in ctl_times
        ),
    )
    print(
        "  control median / mean:",
        f"{ctl_median:.3f}s / {ctl_mean:.3f}s",
    )
    print(
        "  corrected/control median ratio:",
        f"{median_ratio:.3f}x",
    )
    print(
        "  corrected median throughput:",
        f"{corrected_median_throughput:.3f} profiles/s",
    )
    print(
        "  warmed dominant stage:",
        dominant_stage,
    )
    print(
        "  diagnostic projection:",
        f"{projected_hours_per_epoch:.3f} h/epoch, "
        f"{projected_days_800:.3f} d/{target_epochs}ep",
    )
    print(
        "  NOTE: projection is diagnostic, not a runtime promise."
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
        "  Results :",
        sha256(
            RESULTS
        ),
    )
    print(
        "  Decision:",
        sha256(
            DECISION
        ),
    )
    print(
        "  Summary :",
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


if __name__ == "__main__":
    main()
