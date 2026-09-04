#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2AF-XPU
COMP-XPU-005 One-Logical-Batch Scratch Execution Rehearsal

Purpose
-------
Execute the V16E-1B2AE-authorized production-mechanics rehearsal for the
prospective corrected Stage-2 experiment:

    V16E-BLREP-COMP-XPU-005

This is SCRATCH ONLY.

It is NOT the COMP-XPU-005 training run.
Its weights MUST NEVER seed or resume COMP-XPU-005.

Authorized rehearsal
---------------------
Fresh seed-1337 initialization.

Exact adopted implementation:
    CHUNKED_BATCHED_VJP
    cotangent chunk size = 16

Exact training microbatch:
    128

Exactly one production-sized logical training batch:
    8192 profiles
    64 microbatches
    profile-weighted accumulation
    exactly one Adam optimizer step

Optimizer:
    torch.optim.Adam(
        model.parameters(),
        lr=1.0e-3,
        foreach=False,
    )

After the one step:
    * verify finite model parameters
    * write atomic scratch checkpoint
    * construct a new model + optimizer
    * reload model / optimizer / RNG state
    * verify exact model-state equality
    * verify exact optimizer-state equality
    * verify Python / NumPy / torch CPU / XPU RNG restoration
    * verify all bound contract and source hashes

NO OOD.
NO TOF.
NO B3 authorization.

Production-order fidelity
-------------------------
The rehearsal uses the exact frozen Stage-2 split / epoch-order semantics:

    split:
        rng = np.random.default_rng(seed=1337)
        shuffle all 14400 profile indices
        first 80% = 11520 train profiles

    epoch-1 training order:
        erng = np.random.default_rng(seed=1337 + 1)
        shuffle train_idx

    rehearsal logical batch:
        first 8192 profiles of that epoch-1 order

Thus the rehearsal is a genuine production-sized logical batch under the
frozen training-order rule.

Fresh-model fidelity
--------------------
The model is constructed from the exact frozen COMP-XPU-004 / eta architecture
class, but NO COMP-XPU-004 weights are loaded.

The exact construction rule is:

    EtaModel = B2J.build_eta_model_class(BASE_RUNNER)
    torch.manual_seed(1337)
    model = EtaModel().to(xpu)

COMP-XPU-004 remains provenance/comparison authority only.

Gradient-accumulation rule
--------------------------
For every rehearsal microbatch:

    raw_total_loss = exact corrected B2S total loss

    scaled_loss =
        raw_total_loss * (N_mb / 8192)

For the exact rehearsal geometry:

    N_mb = 128
    scale = 128 / 8192 = 1 / 64

64 scaled backward calls accumulate one logical-batch gradient.

Then:
    verify finite / nonzero accumulated parameter gradients
    optimizer.step() exactly once
    synchronize XPU
    verify all model parameters finite
    optimizer.zero_grad(set_to_none=True)

Checkpoint semantics
--------------------
The scratch checkpoint is explicitly NON-PRODUCTION:

    scratch_rehearsal = True
    completed_epoch = 0
    completed_logical_batches = 1
    allowed_as_COMP_XPU_005_resume_source = False

Atomic write:
    torch.save(temp)
    os.replace(temp, final)

The checkpoint payload binds:
    execution contract SHA
    accumulation contract SHA
    resume contract SHA
    B2AF protocol SHA
    dataset SHA
    B2S source SHA
    B2AC source SHA
    B2AE source SHA
    this B2AF source SHA
    derivative engine + chunk
    batch geometry
    seed
    model state
    optimizer state
    training-order identity
    loss summary
    Python RNG state
    NumPy RNG state
    torch CPU RNG state
    torch XPU RNG state if available

Fail-closed behavior
--------------------
If any authority, finite-gradient, optimizer-step, checkpoint, or restoration
gate fails:
    * write a scratch failure artifact
    * do not mark rehearsal certified
    * do not authorize COMP-XPU-005
    * do not authorize B3

If all gates pass:
    * B2AF is certified as execution-mechanics rehearsal only
    * a separate B2AG authorization freeze is still required before COMP-XPU-005
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
import sys
import time
import traceback
from typing import Any

import numpy as np
import torch


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2AF-XPU"
EXPERIMENT_ID = "V16E-BLREP-COMP-XPU-005"

SEED = 1337
ADOPTED_ENGINE = "CHUNKED_BATCHED_VJP"
ADOPTED_CHUNK = 16

N_TOTAL = 14400
N_TRAIN = 11520
LOGICAL_BATCH = 8192
MICROBATCH = 128
REHEARSAL_MICROBATCHES = 64
REHEARSAL_OPTIMIZER_STEPS = 1

LR = 1.0e-3

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

# Exact adopted chunked engine implementation.
B2AC_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AC_XPU_Chunked_Batched_VJP_Equivalence_Performance_Sweep.py"
)
B2AC_SOURCE_SHA = "59f7ea7b0dc2e901f5a42649691c2dab5f4dfc5d399f953eaab5ba773040cd53"

# B2AE authority and frozen contracts.
B2AE_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AE_XPU_COMP005_Execution_Preflight_Contract_Freeze.py"
)
B2AE_SOURCE_SHA = "8bc7eb7f7a927d172bd7438fde719ee3f31c234acc2a167772dc1f6a556d68cc"

B2AE_DIR = (
    R / "output"
    / "V16_E1B2AE_XPU_COMP005_EXECUTION_PREFLIGHT_CONTRACT"
)
EXECUTION_CONTRACT = B2AE_DIR / "V16E1B2AE_COMP_XPU_005_Execution_Contract.json"
ACCUMULATION_CONTRACT = B2AE_DIR / "V16E1B2AE_Optimizer_Accumulation_Contract.json"
RESUME_CONTRACT = B2AE_DIR / "V16E1B2AE_Checkpoint_Resume_Contract.json"
B2AF_PROTOCOL = B2AE_DIR / "V16E1B2AE_B2AF_Preflight_Rehearsal_Protocol.json"
B2AE_HANDOFF = B2AE_DIR / "V16E1B2AE_B2AF_Handoff.md"
B2AE_SUMMARY = B2AE_DIR / "PAD_Stream_V16E1B2AE_XPU_Summary.json"

EXECUTION_CONTRACT_SHA = "6bf7794f493b95d9922573f24fdee30d1ff9f0caac5a0075d70a9abfa9dae83e"
ACCUMULATION_CONTRACT_SHA = "fd07af361a788f6cbc2c93faad8a196223dfd9a5894e67e2475e96657a8a5425"
RESUME_CONTRACT_SHA = "ba9f86b236e2276e507988d9c44f96b428c59aa1bedc02575f0c2b09c13bc449"
B2AF_PROTOCOL_SHA = "d7a3e505983dcfa855d1291749da0cafa0ee97e3c9319a7e746c392860a69f4f"
B2AE_HANDOFF_SHA = "8a937b13c35dd4781a2efc1f56e670e36b16874a57594445d2d9e83dd22da0d1"
B2AE_SUMMARY_SHA = "84b073a12466611bb509e513846a07b5e389991ac4d1a6c5997045769c72f76d"

EXPECTED_B2AE_STATUS = (
    "V16E1B2AE_XPU_COMP_XPU_005_EXECUTION_PREFLIGHT_CONTRACT_FROZEN_"
    "FRESH_SEED_1337_INITIALIZATION_REQUIRED_COMP_XPU_004_CHECKPOINT_PROVENANCE_ONLY_NOT_INITIALIZER_"
    "CHUNKED_BATCHED_VJP_CHUNK_16_MICROBATCH_128_LOGICAL_BATCH_8192_AND_800_EPOCH_CONTRACT_BOUND_"
    "ADAM_LR_1E_3_FOREACH_FALSE_PROFILE_WEIGHTED_LOGICAL_BATCH_GRADIENT_ACCUMULATION_"
    "NINETY_MICROBATCHES_TWO_OPTIMIZER_STEPS_PER_EPOCH_AND_1600_TARGET_STEPS_BOUND_"
    "ATOMIC_EVERY_COMPLETED_EPOCH_CHECKPOINT_AND_EXACT_HASHED_RESUME_CONTRACT_FROZEN_"
    "B2AF_ONE_LOGICAL_BATCH_SCRATCH_OPTIMIZER_CHECKPOINT_RELOAD_REHEARSAL_AUTHORIZED_"
    "NO_TRAINING_IN_B2AE_NO_OPTIMIZER_OBJECT_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
    "COMP_XPU_005_FULL_TRAINING_NOT_AUTHORIZED_B3_NOT_AUTHORIZED"
)

# =============================================================================
# Scratch outputs
# =============================================================================

OUT = (
    R / "output"
    / "V16_E1B2AF_XPU_COMP005_SCRATCH_EXECUTION_REHEARSAL"
)
OUT.mkdir(parents=True, exist_ok=True)

SCRATCH_CHECKPOINT = OUT / "V16E1B2AF_SCRATCH_ONE_LOGICAL_BATCH.pt"
REHEARSAL_RESULTS = OUT / "V16E1B2AF_Scratch_Rehearsal_Results.json"
FAILURE = OUT / "V16E1B2AF_Scratch_Rehearsal_Failure.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2AF_XPU_Summary.json"


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


def atomic_json_write(payload, path: Path):
    tmp = path.with_suffix(path.suffix + ".tmp")

    tmp.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    os.replace(tmp, path)


def atomic_torch_save(payload, path: Path):
    tmp = path.with_suffix(path.suffix + ".tmp")

    if tmp.exists():
        tmp.unlink()

    torch.save(
        payload,
        tmp,
    )

    # Ensure the serialized bytes exist before promotion.
    if (
        not tmp.exists()
        or tmp.stat().st_size <= 0
    ):
        raise RuntimeError(
            "Atomic torch checkpoint temporary file was not written."
        )

    os.replace(
        tmp,
        path,
    )

    if (
        not path.exists()
        or path.stat().st_size <= 0
    ):
        raise RuntimeError(
            "Atomic torch checkpoint final file was not written."
        )


def tensor_tree_to_cpu(obj: Any):
    if torch.is_tensor(obj):
        return obj.detach().cpu().clone()

    if isinstance(obj, dict):
        return {
            k: tensor_tree_to_cpu(v)
            for k, v in obj.items()
        }

    if isinstance(obj, list):
        return [
            tensor_tree_to_cpu(v)
            for v in obj
        ]

    if isinstance(obj, tuple):
        return tuple(
            tensor_tree_to_cpu(v)
            for v in obj
        )

    return copy.deepcopy(obj)


def exact_tree_equal(a: Any, b: Any) -> bool:
    if torch.is_tensor(a) or torch.is_tensor(b):
        if not (
            torch.is_tensor(a)
            and torch.is_tensor(b)
        ):
            return False

        return (
            a.shape == b.shape
            and a.dtype == b.dtype
            and torch.equal(
                a.detach().cpu(),
                b.detach().cpu(),
            )
        )

    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        if not (
            isinstance(a, np.ndarray)
            and isinstance(b, np.ndarray)
        ):
            return False

        return (
            a.dtype == b.dtype
            and a.shape == b.shape
            and np.array_equal(a, b)
        )

    if isinstance(a, dict) or isinstance(b, dict):
        if not (
            isinstance(a, dict)
            and isinstance(b, dict)
        ):
            return False

        if set(a.keys()) != set(b.keys()):
            return False

        return all(
            exact_tree_equal(
                a[k],
                b[k],
            )
            for k in a.keys()
        )

    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        if not (
            isinstance(a, type(b))
            and isinstance(b, type(a))
        ):
            return False

        if len(a) != len(b):
            return False

        return all(
            exact_tree_equal(x, y)
            for x, y in zip(a, b)
        )

    return a == b


def all_model_parameters_finite(model) -> bool:
    return all(
        torch.isfinite(
            p.detach()
        ).all().item()
        for p in model.parameters()
    )


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

        grad_sq += float(
            torch.sum(
                g.double() ** 2
            ).cpu()
        )

    return {
        "gradient_tensor_count":
            int(tensor_count),

        "nonzero_gradient_tensor_count":
            int(nonzero_count),

        "gradients_finite":
            bool(finite_all),

        "gradient_l2_norm":
            float(
                math.sqrt(
                    max(
                        grad_sq,
                        0.0,
                    )
                )
            ),
    }


def model_state_cpu(model):
    return {
        name: tensor.detach().cpu().clone()
        for name, tensor
        in model.state_dict().items()
    }


def optimizer_state_cpu(optimizer):
    return tensor_tree_to_cpu(
        optimizer.state_dict()
    )


# =============================================================================
# RNG helpers
# =============================================================================

def get_xpu_rng_state():
    if not torch.xpu.is_available():
        return None

    if hasattr(torch.xpu, "get_rng_state_all"):
        try:
            states = torch.xpu.get_rng_state_all()
            return [
                s.detach().cpu().clone()
                for s in states
            ]
        except Exception:
            pass

    if hasattr(torch.xpu, "get_rng_state"):
        try:
            s = torch.xpu.get_rng_state()
            return [
                s.detach().cpu().clone()
            ]
        except Exception:
            pass

    return None


def set_xpu_rng_state(states):
    if states is None:
        return

    if hasattr(torch.xpu, "set_rng_state_all"):
        try:
            torch.xpu.set_rng_state_all(
                states
            )
            return
        except Exception:
            pass

    if (
        len(states) == 1
        and hasattr(
            torch.xpu,
            "set_rng_state",
        )
    ):
        torch.xpu.set_rng_state(
            states[0]
        )
        return

    raise RuntimeError(
        "Unable to restore saved XPU RNG state."
    )


def capture_rng_state():
    return {
        "python":
            copy.deepcopy(
                random.getstate()
            ),

        "numpy":
            copy.deepcopy(
                np.random.get_state()
            ),

        "torch_cpu":
            torch.get_rng_state()
            .detach()
            .cpu()
            .clone(),

        "torch_xpu":
            get_xpu_rng_state(),
    }


def restore_rng_state(state):
    random.setstate(
        state["python"]
    )

    np.random.set_state(
        state["numpy"]
    )

    torch.set_rng_state(
        state["torch_cpu"]
    )

    set_xpu_rng_state(
        state["torch_xpu"]
    )


def rng_state_equal(a, b):
    return exact_tree_equal(
        a,
        b,
    )


# =============================================================================
# Frozen split / epoch-order rule
# =============================================================================

def frozen_train_indices(n: int):
    rng = np.random.default_rng(
        SEED
    )

    idx = np.arange(
        n
    )

    rng.shuffle(
        idx
    )

    n_train = int(
        0.8 * n
    )

    return idx[:n_train]


def production_epoch_order(train_idx, epoch: int):
    erng = np.random.default_rng(
        SEED + epoch
    )

    order = train_idx.copy()

    erng.shuffle(
        order
    )

    return order


# =============================================================================
# Fresh model construction
# =============================================================================

def build_fresh_model_and_optimizer(
    B2S,
    device,
    suffix: str,
):
    M = B2S.import_module(
        B2S.BASE_RUNNER,
        f"b2af_base_{suffix}",
    )

    J = B2S.import_module(
        B2S.B2J_SOURCE,
        f"b2af_eta_{suffix}",
    )

    if not exact(
        B2S.BASE_RUNNER,
        B2S.BASE_RUNNER_SHA,
    ):
        raise RuntimeError(
            "Frozen Stage-2 base-runner SHA mismatch."
        )

    if not exact(
        B2S.B2J_SOURCE,
        B2S.B2J_SOURCE_SHA,
    ):
        raise RuntimeError(
            "Frozen COMP-XPU-004 eta-model source SHA mismatch."
        )

    if int(M.SEED) != SEED:
        raise RuntimeError(
            f"Frozen model seed mismatch: {M.SEED}"
        )

    if int(M.LOGICAL_BATCH) != LOGICAL_BATCH:
        raise RuntimeError(
            f"Frozen logical batch mismatch: {M.LOGICAL_BATCH}"
        )

    # Exact fresh model construction rule.
    EtaModel = J.build_eta_model_class(
        M
    )

    torch.manual_seed(
        SEED
    )

    model = EtaModel().to(
        device
    )

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LR,
        foreach=False,
    )

    return (
        M,
        J,
        model,
        optimizer,
    )


# =============================================================================
# Main rehearsal
# =============================================================================

def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2AF-XPU")
    print("COMP-XPU-005 One-Logical-Batch Scratch Execution Rehearsal")
    print("=" * 80)
    print("SCRATCH ONLY — ONE ADAM STEP — NEVER A COMP-XPU-005 RESUME SOURCE.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2AF summary already exists; refusing overwrite."
        )

    # Remove only stale B2AF scratch files, never upstream or production artifacts.
    for p in (
        SCRATCH_CHECKPOINT,
        REHEARSAL_RESULTS,
        FAILURE,
    ):
        if p.exists():
            p.unlink()

    self_path = Path(
        __file__
    ).resolve()

    self_sha = sha256(
        self_path
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

        "B2AC_source_SHA_exact":
            exact(
                B2AC_SOURCE,
                B2AC_SOURCE_SHA,
            ),

        "B2AE_source_SHA_exact":
            exact(
                B2AE_SOURCE,
                B2AE_SOURCE_SHA,
            ),

        "execution_contract_SHA_exact":
            exact(
                EXECUTION_CONTRACT,
                EXECUTION_CONTRACT_SHA,
            ),

        "accumulation_contract_SHA_exact":
            exact(
                ACCUMULATION_CONTRACT,
                ACCUMULATION_CONTRACT_SHA,
            ),

        "resume_contract_SHA_exact":
            exact(
                RESUME_CONTRACT,
                RESUME_CONTRACT_SHA,
            ),

        "B2AF_protocol_SHA_exact":
            exact(
                B2AF_PROTOCOL,
                B2AF_PROTOCOL_SHA,
            ),

        "B2AE_handoff_SHA_exact":
            exact(
                B2AE_HANDOFF,
                B2AE_HANDOFF_SHA,
            ),

        "B2AE_summary_SHA_exact":
            exact(
                B2AE_SUMMARY,
                B2AE_SUMMARY_SHA,
            ),
    }

    b2ae = (
        read_json(
            B2AE_SUMMARY
        )
        if B2AE_SUMMARY.exists()
        else {}
    )

    execution = (
        read_json(
            EXECUTION_CONTRACT
        )
        if EXECUTION_CONTRACT.exists()
        else {}
    )

    accumulation = (
        read_json(
            ACCUMULATION_CONTRACT
        )
        if ACCUMULATION_CONTRACT.exists()
        else {}
    )

    resume = (
        read_json(
            RESUME_CONTRACT
        )
        if RESUME_CONTRACT.exists()
        else {}
    )

    protocol = (
        read_json(
            B2AF_PROTOCOL
        )
        if B2AF_PROTOCOL.exists()
        else {}
    )

    gates.update({
        "B2AE_status_exact":
            b2ae.get(
                "status"
            )
            == EXPECTED_B2AE_STATUS,

        "B2AE_B2AF_true":
            b2ae.get(
                "B2AF_authorized"
            )
            is True,

        "B2AE_training_false":
            b2ae.get(
                "COMP_XPU_005_full_training_authorized"
            )
            is False,

        "B2AE_B3_false":
            b2ae.get(
                "B3_authorized"
            )
            is False,

        "experiment_id_exact":
            execution.get(
                "experiment_id"
            )
            == EXPERIMENT_ID,

        "fresh_training_required":
            (
                execution
                .get("fresh_training", {})
                .get("required")
                is True
            ),

        "COMP004_initializer_false":
            (
                execution
                .get("fresh_training", {})
                .get("initialize_from_COMP004_checkpoint")
                is False
            ),

        "execution_engine_exact":
            (
                execution
                .get("derivative_engine", {})
                .get("name")
                == ADOPTED_ENGINE
            ),

        "execution_chunk_16":
            (
                execution
                .get("derivative_engine", {})
                .get("cotangent_chunk_size")
                == ADOPTED_CHUNK
            ),

        "execution_microbatch_128":
            (
                execution
                .get("training_geometry", {})
                .get("microbatch")
                == MICROBATCH
            ),

        "execution_logical_batch_8192":
            (
                execution
                .get("training_geometry", {})
                .get("logical_batch")
                == LOGICAL_BATCH
            ),

        "execution_optimizer_exact":
            (
                execution
                .get("optimizer", {})
                .get("constructor_expression")
                == "torch.optim.Adam(model.parameters(), lr=1.0e-3, foreach=False)"
            ),

        "accumulation_profile_weighted":
            accumulation.get(
                "profile_weighted_logical_mean"
            )
            is True,

        "accumulation_no_step_per_microbatch":
            accumulation.get(
                "no_optimizer_step_per_microbatch"
            )
            is True,

        "resume_atomic_true":
            resume.get(
                "atomic_write_required"
            )
            is True,

        "resume_mid_epoch_false":
            resume.get(
                "mid_epoch_resume_allowed"
            )
            is False,

        "protocol_next_exact":
            protocol.get(
                "authorized_next_milestone"
            )
            == MILESTONE,

        "protocol_scratch_only":
            protocol.get(
                "scratch_only"
            )
            is True,

        "protocol_scratch_not_seed":
            protocol.get(
                "scratch_weights_may_seed_COMP_XPU_005"
            )
            is False,

        "protocol_fresh_init":
            protocol.get(
                "fresh_initialization_required"
            )
            is True,

        "protocol_logical_profiles_8192":
            (
                protocol
                .get("rehearsal_geometry", {})
                .get("logical_profiles")
                == LOGICAL_BATCH
            ),

        "protocol_microbatch_128":
            (
                protocol
                .get("rehearsal_geometry", {})
                .get("microbatch")
                == MICROBATCH
            ),

        "protocol_microbatches_64":
            (
                protocol
                .get("rehearsal_geometry", {})
                .get("microbatches")
                == REHEARSAL_MICROBATCHES
            ),

        "protocol_optimizer_steps_1":
            (
                protocol
                .get("rehearsal_geometry", {})
                .get("optimizer_steps")
                == REHEARSAL_OPTIMIZER_STEPS
            ),
    })

    print("AUTHORITY / REHEARSAL GATES")

    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    if not all(
        gates.values()
    ):
        raise RuntimeError(
            "B2AF blocked by authority or B2AE contract mismatch."
        )

    if not torch.xpu.is_available():
        raise RuntimeError(
            "Intel XPU unavailable for B2AF."
        )

    try:
        # ---------------------------------------------------------------------
        # Load exact implementation authorities.
        # ---------------------------------------------------------------------

        B2S = import_module(
            B2S_SOURCE,
            "v16e1b2s_exact_b2af",
        )

        B2AC = import_module(
            B2AC_SOURCE,
            "v16e1b2ac_chunk_engine_b2af",
        )

        if not exact(
            B2S.BASE_RUNNER,
            B2S.BASE_RUNNER_SHA,
        ):
            raise RuntimeError(
                "B2S-bound base runner SHA mismatch."
            )

        if not exact(
            B2S.B2J_SOURCE,
            B2S.B2J_SOURCE_SHA,
        ):
            raise RuntimeError(
                "B2S-bound B2J eta runner SHA mismatch."
            )

        # ---------------------------------------------------------------------
        # Dataset + exact production split/order.
        # ---------------------------------------------------------------------

        d = np.load(
            DATASET
        )

        required_keys = {
            "xi",
            "Sw",
            "p11",
            "ai",
            "at",
        }

        missing = (
            required_keys
            - set(
                d.files
            )
        )

        if missing:
            raise RuntimeError(
                f"Dataset missing required arrays: {sorted(missing)}"
            )

        xi_all = d["xi"]
        Sw_all = d["Sw"]
        p11_all = d["p11"]
        ai_all = d["ai"]
        at_all = d["at"]

        if len(xi_all) != N_TOTAL:
            raise RuntimeError(
                f"Dataset profile count mismatch: {len(xi_all)}"
            )

        train_idx = frozen_train_indices(
            len(xi_all)
        )

        if len(train_idx) != N_TRAIN:
            raise RuntimeError(
                f"Frozen train split mismatch: {len(train_idx)}"
            )

        epoch1_order = production_epoch_order(
            train_idx,
            epoch=1,
        )

        logical_idx = epoch1_order[
            :LOGICAL_BATCH
        ]

        if len(logical_idx) != LOGICAL_BATCH:
            raise RuntimeError(
                "Rehearsal logical batch is not exactly 8192 profiles."
            )

        training_order_identity = {
            "split_seed":
                SEED,

            "epoch":
                1,

            "epoch_shuffle_seed":
                SEED + 1,

            "train_profiles":
                int(
                    len(train_idx)
                ),

            "logical_batch_profiles":
                int(
                    len(logical_idx)
                ),

            "logical_batch_indices_sha256":
                hashlib.sha256(
                    np.asarray(
                        logical_idx,
                        dtype=np.int64,
                    ).tobytes()
                ).hexdigest(),
        }

        # ---------------------------------------------------------------------
        # Fresh model / optimizer.
        # ---------------------------------------------------------------------

        device = torch.device(
            "xpu"
        )

        random.seed(
            SEED
        )

        np.random.seed(
            SEED
        )

        (
            M,
            J,
            model,
            optimizer,
        ) = build_fresh_model_and_optimizer(
            B2S,
            device,
            "train",
        )

        model.train()

        if {
            p.device.type
            for p in model.parameters()
        } != {"xpu"}:
            raise RuntimeError(
                "Fresh rehearsal model is not entirely on XPU."
            )

        if (
            model.lstm1.input_size != 13
            or model.lstm2.input_size != int(M.HIDDEN)
            or model.lstm2.hidden_size != int(M.HIDDEN)
        ):
            raise RuntimeError(
                "Fresh rehearsal model architecture mismatch."
            )

        initial_model_state = model_state_cpu(
            model
        )

        # Prove we did not load COMP004 weights by comparing fresh state to COMP004.
        comp004 = torch.load(
            COMP004_CHECKPOINT,
            map_location="cpu",
            weights_only=False,
        )

        comp004_state = tensor_tree_to_cpu(
            comp004[
                "model_state_dict"
            ]
        )

        fresh_initial_equals_COMP004 = exact_tree_equal(
            initial_model_state,
            comp004_state,
        )

        if fresh_initial_equals_COMP004:
            raise RuntimeError(
                "Fresh seed-1337 rehearsal initialization unexpectedly equals "
                "the frozen COMP-XPU-004 trained checkpoint."
            )

        # ---------------------------------------------------------------------
        # Exact adopted derivative engine.
        # ---------------------------------------------------------------------

        engine = B2AC.make_chunked_batched_engine(
            ADOPTED_CHUNK
        )

        original_engine = (
            B2S.local_recurrent_derivatives_create_graph
        )

        B2S.local_recurrent_derivatives_create_graph = engine

        # ---------------------------------------------------------------------
        # One exact production-sized logical batch.
        # ---------------------------------------------------------------------

        optimizer.zero_grad(
            set_to_none=True
        )

        weighted_sums = {
            "data": 0.0,
            "physics": 0.0,
            "bc_inj": 0.0,
            "bc_tip": 0.0,
            "anchor": 0.0,
            "mono": 0.0,
            "total": 0.0,
        }

        total_profiles = 0
        microbatch_records = []

        logical_t0 = time.perf_counter()

        try:
            for micro_i, m0 in enumerate(
                range(
                    0,
                    LOGICAL_BATCH,
                    MICROBATCH,
                ),
                start=1,
            ):
                ids = logical_idx[
                    m0:m0 + MICROBATCH
                ]

                m = len(
                    ids
                )

                if m != MICROBATCH:
                    raise RuntimeError(
                        f"Unexpected rehearsal microbatch size {m}."
                    )

                xi = (
                    torch.from_numpy(
                        xi_all[
                            ids
                        ]
                    )
                    .to(
                        device
                    )
                    .detach()
                    .clone()
                    .requires_grad_(
                        True
                    )
                )

                Sw = torch.from_numpy(
                    Sw_all[
                        ids
                    ]
                ).to(
                    device
                )

                p11 = (
                    torch.from_numpy(
                        p11_all[
                            ids
                        ]
                    )
                    .to(
                        device
                    )
                    .detach()
                    .clone()
                    .requires_grad_(
                        True
                    )
                )

                ai = torch.from_numpy(
                    ai_all[
                        ids
                    ]
                ).to(
                    device
                )

                at = torch.from_numpy(
                    at_all[
                        ids
                    ]
                ).to(
                    device
                )

                mb_t0 = time.perf_counter()

                (
                    S_pred,
                    residual,
                    parts,
                ) = B2S.complete_corrected_total_loss(
                    M,
                    model,
                    xi,
                    Sw,
                    p11,
                    ai,
                    at,
                )

                if not torch.isfinite(
                    S_pred
                ).all().item():
                    raise RuntimeError(
                        f"Microbatch {micro_i}: nonfinite prediction."
                    )

                if not torch.isfinite(
                    residual
                ).all().item():
                    raise RuntimeError(
                        f"Microbatch {micro_i}: nonfinite corrected residual."
                    )

                if not all(
                    torch.isfinite(
                        v
                    ).all().item()
                    for v in parts.values()
                ):
                    raise RuntimeError(
                        f"Microbatch {micro_i}: nonfinite loss."
                    )

                scale = (
                    float(
                        m
                    )
                    / float(
                        LOGICAL_BATCH
                    )
                )

                scaled_total = (
                    parts[
                        "total"
                    ]
                    * scale
                )

                scaled_total.backward()

                sync_xpu()

                mb_seconds = (
                    time.perf_counter()
                    - mb_t0
                )

                for k in weighted_sums:
                    weighted_sums[k] += (
                        float(
                            parts[
                                k
                            ]
                            .detach()
                            .cpu()
                        )
                        * m
                    )

                total_profiles += m

                microbatch_records.append({
                    "microbatch_index":
                        micro_i,

                    "profiles":
                        m,

                    "scale":
                        scale,

                    "raw_total_loss":
                        float(
                            parts[
                                "total"
                            ]
                            .detach()
                            .cpu()
                        ),

                    "physics_loss":
                        float(
                            parts[
                                "physics"
                            ]
                            .detach()
                            .cpu()
                        ),

                    "seconds":
                        float(
                            mb_seconds
                        ),
                })

                if (
                    micro_i == 1
                    or micro_i % 8 == 0
                    or micro_i == REHEARSAL_MICROBATCHES
                ):
                    print(
                        f"  microbatch {micro_i:02d}/{REHEARSAL_MICROBATCHES}"
                        f" | loss={microbatch_records[-1]['raw_total_loss']:.6e}"
                        f" | physics={microbatch_records[-1]['physics_loss']:.6e}"
                        f" | {mb_seconds:.3f}s"
                    )

                del (
                    xi,
                    Sw,
                    p11,
                    ai,
                    at,
                    S_pred,
                    residual,
                    parts,
                    scaled_total,
                )

        finally:
            B2S.local_recurrent_derivatives_create_graph = (
                original_engine
            )

        if total_profiles != LOGICAL_BATCH:
            raise RuntimeError(
                f"Rehearsal accumulated {total_profiles} profiles, expected 8192."
            )

        if len(
            microbatch_records
        ) != REHEARSAL_MICROBATCHES:
            raise RuntimeError(
                f"Rehearsal executed {len(microbatch_records)} microbatches, "
                f"expected {REHEARSAL_MICROBATCHES}."
            )

        sync_xpu()

        accumulated_gradients = parameter_gradient_summary(
            model
        )

        if not accumulated_gradients[
            "gradients_finite"
        ]:
            raise RuntimeError(
                "Accumulated logical-batch parameter gradients are nonfinite."
            )

        if accumulated_gradients[
            "nonzero_gradient_tensor_count"
        ] <= 0:
            raise RuntimeError(
                "Accumulated logical-batch parameter gradients are all zero."
            )

        pre_step_model_state = model_state_cpu(
            model
        )

        # Exactly ONE optimizer step.
        optimizer.step()

        sync_xpu()

        post_step_model_state = model_state_cpu(
            model
        )

        model_changed_after_step = (
            not exact_tree_equal(
                pre_step_model_state,
                post_step_model_state,
            )
        )

        if not model_changed_after_step:
            raise RuntimeError(
                "Exactly one Adam step completed but no model parameter changed."
            )

        if not all_model_parameters_finite(
            model
        ):
            raise RuntimeError(
                "Post-step model parameters are nonfinite."
            )

        optimizer.zero_grad(
            set_to_none=True
        )

        sync_xpu()

        logical_seconds = (
            time.perf_counter()
            - logical_t0
        )

        logical_mean_losses = {
            k:
                float(
                    weighted_sums[
                        k
                    ]
                    / LOGICAL_BATCH
                )
            for k in weighted_sums
        }

        # ---------------------------------------------------------------------
        # Capture exact post-step state for checkpoint / reload comparison.
        # ---------------------------------------------------------------------

        post_step_model_state = model_state_cpu(
            model
        )

        post_step_optimizer_state = optimizer_state_cpu(
            optimizer
        )

        saved_rng_state = capture_rng_state()

        source_sha_map = {
            "dataset_sha256":
                DATASET_SHA,

            "B2S_source_sha256":
                B2S_SOURCE_SHA,

            "B2S_base_runner_sha256":
                B2S.BASE_RUNNER_SHA,

            "B2S_B2J_source_sha256":
                B2S.B2J_SOURCE_SHA,

            "B2AC_source_sha256":
                B2AC_SOURCE_SHA,

            "B2AE_source_sha256":
                B2AE_SOURCE_SHA,

            "B2AF_source_sha256":
                self_sha,
        }

        checkpoint_payload = {
            "scratch_rehearsal":
                True,

            "experiment_id":
                EXPERIMENT_ID,

            "completed_epoch":
                0,

            "completed_logical_batches":
                1,

            "allowed_as_COMP_XPU_005_resume_source":
                False,

            "model_state_dict":
                model.state_dict(),

            "optimizer_state_dict":
                optimizer.state_dict(),

            "training_history":
                {
                    "scratch_logical_batch_mean_losses":
                        logical_mean_losses,

                    "scratch_logical_batch_seconds":
                        float(
                            logical_seconds
                        ),
                },

            "python_rng_state":
                saved_rng_state[
                    "python"
                ],

            "numpy_rng_state":
                saved_rng_state[
                    "numpy"
                ],

            "torch_cpu_rng_state":
                saved_rng_state[
                    "torch_cpu"
                ],

            "torch_xpu_rng_state":
                saved_rng_state[
                    "torch_xpu"
                ],

            "execution_contract_sha256":
                EXECUTION_CONTRACT_SHA,

            "accumulation_contract_sha256":
                ACCUMULATION_CONTRACT_SHA,

            "resume_contract_sha256":
                RESUME_CONTRACT_SHA,

            "B2AF_protocol_sha256":
                B2AF_PROTOCOL_SHA,

            "dataset_sha256":
                DATASET_SHA,

            "source_sha256_map":
                source_sha_map,

            "derivative_engine":
                ADOPTED_ENGINE,

            "cotangent_chunk_size":
                ADOPTED_CHUNK,

            "logical_batch":
                LOGICAL_BATCH,

            "microbatch":
                MICROBATCH,

            "seed":
                SEED,

            "training_order_identity":
                training_order_identity,

            "OOD_used":
                False,

            "TOF_used":
                False,
        }

        atomic_torch_save(
            checkpoint_payload,
            SCRATCH_CHECKPOINT,
        )

        scratch_checkpoint_sha = sha256(
            SCRATCH_CHECKPOINT
        )

        # ---------------------------------------------------------------------
        # Deliberately perturb process RNG before reload/restoration.
        # ---------------------------------------------------------------------

        random.random()
        np.random.random()
        torch.rand(
            8
        )

        try:
            torch.rand(
                8,
                device=device,
            )
            sync_xpu()
        except Exception:
            # XPU RNG perturbation is diagnostic only; restoration still gates
            # on exact saved/restored state if an XPU RNG state is available.
            pass

        # ---------------------------------------------------------------------
        # New model + optimizer instance, then exact reload.
        # ---------------------------------------------------------------------

        (
            M_reload,
            J_reload,
            model_reload,
            optimizer_reload,
        ) = build_fresh_model_and_optimizer(
            B2S,
            device,
            "reload",
        )

        scratch_loaded = torch.load(
            SCRATCH_CHECKPOINT,
            map_location="cpu",
            weights_only=False,
        )

        # Contract / provenance gates BEFORE applying scratch state.
        checkpoint_contract_gates = {
            "scratch_rehearsal_true":
                scratch_loaded.get(
                    "scratch_rehearsal"
                )
                is True,

            "completed_epoch_zero":
                scratch_loaded.get(
                    "completed_epoch"
                )
                == 0,

            "completed_logical_batches_one":
                scratch_loaded.get(
                    "completed_logical_batches"
                )
                == 1,

            "resume_source_false":
                scratch_loaded.get(
                    "allowed_as_COMP_XPU_005_resume_source"
                )
                is False,

            "execution_contract_SHA_exact":
                scratch_loaded.get(
                    "execution_contract_sha256"
                )
                == EXECUTION_CONTRACT_SHA,

            "accumulation_contract_SHA_exact":
                scratch_loaded.get(
                    "accumulation_contract_sha256"
                )
                == ACCUMULATION_CONTRACT_SHA,

            "resume_contract_SHA_exact":
                scratch_loaded.get(
                    "resume_contract_sha256"
                )
                == RESUME_CONTRACT_SHA,

            "B2AF_protocol_SHA_exact":
                scratch_loaded.get(
                    "B2AF_protocol_sha256"
                )
                == B2AF_PROTOCOL_SHA,

            "dataset_SHA_exact":
                scratch_loaded.get(
                    "dataset_sha256"
                )
                == DATASET_SHA,

            "source_SHA_map_exact":
                scratch_loaded.get(
                    "source_sha256_map"
                )
                == source_sha_map,

            "derivative_engine_exact":
                scratch_loaded.get(
                    "derivative_engine"
                )
                == ADOPTED_ENGINE,

            "chunk_16":
                scratch_loaded.get(
                    "cotangent_chunk_size"
                )
                == ADOPTED_CHUNK,

            "logical_batch_8192":
                scratch_loaded.get(
                    "logical_batch"
                )
                == LOGICAL_BATCH,

            "microbatch_128":
                scratch_loaded.get(
                    "microbatch"
                )
                == MICROBATCH,

            "seed_1337":
                scratch_loaded.get(
                    "seed"
                )
                == SEED,

            "OOD_false":
                scratch_loaded.get(
                    "OOD_used"
                )
                is False,

            "TOF_false":
                scratch_loaded.get(
                    "TOF_used"
                )
                is False,
        }

        if not all(
            checkpoint_contract_gates.values()
        ):
            failed = [
                k
                for k, v in checkpoint_contract_gates.items()
                if not v
            ]

            raise RuntimeError(
                "Scratch checkpoint contract gate failure: "
                + ", ".join(
                    failed
                )
            )

        model_reload.load_state_dict(
            scratch_loaded[
                "model_state_dict"
            ],
            strict=True,
        )

        optimizer_reload.load_state_dict(
            scratch_loaded[
                "optimizer_state_dict"
            ]
        )

        # Ensure optimizer tensors are on the parameter device after reload.
        for state in optimizer_reload.state.values():
            for key, value in state.items():
                if torch.is_tensor(
                    value
                ):
                    state[
                        key
                    ] = value.to(
                        device
                    )

        restored_rng_payload = {
            "python":
                scratch_loaded[
                    "python_rng_state"
                ],

            "numpy":
                scratch_loaded[
                    "numpy_rng_state"
                ],

            "torch_cpu":
                scratch_loaded[
                    "torch_cpu_rng_state"
                ],

            "torch_xpu":
                scratch_loaded[
                    "torch_xpu_rng_state"
                ],
        }

        restore_rng_state(
            restored_rng_payload
        )

        sync_xpu()

        reloaded_model_state = model_state_cpu(
            model_reload
        )

        reloaded_optimizer_state = optimizer_state_cpu(
            optimizer_reload
        )

        reloaded_rng_state = capture_rng_state()

        model_reload_exact = exact_tree_equal(
            post_step_model_state,
            reloaded_model_state,
        )

        optimizer_reload_exact = exact_tree_equal(
            post_step_optimizer_state,
            reloaded_optimizer_state,
        )

        rng_reload_exact = rng_state_equal(
            saved_rng_state,
            reloaded_rng_state,
        )

        if not model_reload_exact:
            raise RuntimeError(
                "Scratch checkpoint model state did not reload exactly."
            )

        if not optimizer_reload_exact:
            raise RuntimeError(
                "Scratch checkpoint optimizer state did not reload exactly."
            )

        if not rng_reload_exact:
            raise RuntimeError(
                "Scratch checkpoint RNG state did not restore exactly."
            )

        if not all_model_parameters_finite(
            model_reload
        ):
            raise RuntimeError(
                "Reloaded scratch model contains nonfinite parameters."
            )

        if sha256(
            COMP004_CHECKPOINT
        ) != COMP004_CHECKPOINT_SHA:
            raise RuntimeError(
                "Frozen COMP-XPU-004 checkpoint changed during B2AF."
            )

        # ---------------------------------------------------------------------
        # Final rehearsal gates.
        # ---------------------------------------------------------------------

        gates.update({
            "fresh_initialization_not_COMP004":
                fresh_initial_equals_COMP004 is False,

            "train_split_11520":
                len(
                    train_idx
                )
                == N_TRAIN,

            "epoch1_logical_batch_8192":
                len(
                    logical_idx
                )
                == LOGICAL_BATCH,

            "exact_64_microbatches":
                len(
                    microbatch_records
                )
                == REHEARSAL_MICROBATCHES,

            "every_microbatch_size_128":
                all(
                    rec[
                        "profiles"
                    ]
                    == MICROBATCH
                    for rec in microbatch_records
                ),

            "every_microbatch_scale_1_over_64":
                all(
                    math.isclose(
                        rec[
                            "scale"
                        ],
                        1.0 / 64.0,
                        rel_tol=0.0,
                        abs_tol=0.0,
                    )
                    for rec in microbatch_records
                ),

            "accumulated_gradients_finite":
                accumulated_gradients[
                    "gradients_finite"
                ]
                is True,

            "accumulated_gradients_nonzero":
                accumulated_gradients[
                    "nonzero_gradient_tensor_count"
                ]
                > 0,

            "exactly_one_optimizer_step":
                True,

            "model_changed_after_optimizer_step":
                model_changed_after_step is True,

            "post_step_parameters_finite":
                all_model_parameters_finite(
                    model
                ),

            "scratch_checkpoint_written":
                SCRATCH_CHECKPOINT.exists()
                and SCRATCH_CHECKPOINT.stat().st_size > 0,

            "scratch_checkpoint_nonproduction":
                scratch_loaded[
                    "allowed_as_COMP_XPU_005_resume_source"
                ]
                is False,

            "all_checkpoint_contract_gates":
                all(
                    checkpoint_contract_gates.values()
                ),

            "reloaded_model_exact":
                model_reload_exact,

            "reloaded_optimizer_exact":
                optimizer_reload_exact,

            "reloaded_RNG_exact":
                rng_reload_exact,

            "reloaded_parameters_finite":
                all_model_parameters_finite(
                    model_reload
                ),

            "COMP004_checkpoint_still_unchanged":
                sha256(
                    COMP004_CHECKPOINT
                )
                == COMP004_CHECKPOINT_SHA,

            "no_OOD":
                True,

            "no_TOF":
                True,

            "scratch_not_resume_source":
                True,

            "COMP005_full_training_not_authorized":
                True,

            "B3_not_authorized":
                True,
        })

        ok = all(
            bool(v)
            for v in gates.values()
        )

        results_payload = {
            "milestone":
                MILESTONE,

            "classification":
                "ONE_PRODUCTION_LOGICAL_BATCH_SCRATCH_EXECUTION_REHEARSAL",

            "experiment_id":
                EXPERIMENT_ID,

            "scratch_only":
                True,

            "allowed_as_COMP_XPU_005_resume_source":
                False,

            "B2AF_source_sha256":
                self_sha,

            "authority": {
                "dataset_sha256":
                    DATASET_SHA,

                "COMP004_checkpoint_sha256":
                    COMP004_CHECKPOINT_SHA,

                "B2S_source_sha256":
                    B2S_SOURCE_SHA,

                "B2S_base_runner_sha256":
                    B2S.BASE_RUNNER_SHA,

                "B2S_B2J_source_sha256":
                    B2S.B2J_SOURCE_SHA,

                "B2AC_source_sha256":
                    B2AC_SOURCE_SHA,

                "B2AE_source_sha256":
                    B2AE_SOURCE_SHA,

                "execution_contract_sha256":
                    EXECUTION_CONTRACT_SHA,

                "accumulation_contract_sha256":
                    ACCUMULATION_CONTRACT_SHA,

                "resume_contract_sha256":
                    RESUME_CONTRACT_SHA,

                "B2AF_protocol_sha256":
                    B2AF_PROTOCOL_SHA,
            },

            "fresh_initialization": {
                "seed":
                    SEED,

                "COMP004_weights_loaded":
                    False,

                "fresh_initial_equals_COMP004":
                    fresh_initial_equals_COMP004,
            },

            "training_order_identity":
                training_order_identity,

            "implementation": {
                "derivative_engine":
                    ADOPTED_ENGINE,

                "cotangent_chunk_size":
                    ADOPTED_CHUNK,

                "microbatch":
                    MICROBATCH,

                "logical_batch":
                    LOGICAL_BATCH,
            },

            "optimizer": {
                "type":
                    "Adam",

                "learning_rate":
                    LR,

                "foreach":
                    False,

                "optimizer_steps":
                    1,
            },

            "accumulation": {
                "logical_profiles":
                    LOGICAL_BATCH,

                "microbatches":
                    REHEARSAL_MICROBATCHES,

                "per_microbatch_profiles":
                    MICROBATCH,

                "per_microbatch_scale":
                    1.0 / 64.0,

                "gradient_summary_before_step":
                    accumulated_gradients,
            },

            "logical_batch_mean_losses":
                logical_mean_losses,

            "microbatch_records":
                microbatch_records,

            "logical_batch_seconds":
                float(
                    logical_seconds
                ),

            "model_changed_after_step":
                model_changed_after_step,

            "post_step_parameters_finite":
                all_model_parameters_finite(
                    model
                ),

            "scratch_checkpoint": {
                "path":
                    SCRATCH_CHECKPOINT.name,

                "sha256":
                    scratch_checkpoint_sha,

                "scratch_rehearsal":
                    True,

                "completed_epoch":
                    0,

                "completed_logical_batches":
                    1,

                "allowed_as_COMP_XPU_005_resume_source":
                    False,
            },

            "reload_verification": {
                "checkpoint_contract_gates":
                    checkpoint_contract_gates,

                "model_state_exact":
                    model_reload_exact,

                "optimizer_state_exact":
                    optimizer_reload_exact,

                "RNG_state_exact":
                    rng_reload_exact,

                "reloaded_parameters_finite":
                    all_model_parameters_finite(
                        model_reload
                    ),
            },

            "OOD_used":
                False,

            "TOF_used":
                False,

            "COMP_XPU_005_full_training_authorized":
                False,

            "B3_authorized":
                False,

            "gates":
                {
                    k: bool(v)
                    for k, v in gates.items()
                },
        }

        REHEARSAL_RESULTS.write_text(
            json.dumps(
                results_payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        gates[
            "results_written"
        ] = (
            REHEARSAL_RESULTS.exists()
            and REHEARSAL_RESULTS.stat().st_size > 0
        )

        ok = all(
            bool(v)
            for v in gates.values()
        )

        status = (
            "V16E1B2AF_XPU_COMP_XPU_005_ONE_LOGICAL_BATCH_SCRATCH_EXECUTION_REHEARSAL_COMPLETE_"
            "FRESH_SEED_1337_MODEL_CONFIRMED_NOT_COMP_XPU_004_INITIALIZER_"
            "EXACT_EPOCH1_PRODUCTION_ORDER_FIRST_8192_TRAINING_PROFILES_USED_"
            "CHUNKED_BATCHED_VJP_CHUNK_16_MICROBATCH_128_SIXTY_FOUR_PROFILE_WEIGHTED_BACKWARD_CALLS_COMPLETE_"
            "FINITE_NONZERO_ACCUMULATED_GRADIENTS_AND_EXACTLY_ONE_ADAM_LR_1E_3_FOREACH_FALSE_STEP_COMPLETE_"
            "POST_STEP_PARAMETERS_FINITE_ATOMIC_NONPRODUCTION_SCRATCH_CHECKPOINT_WRITTEN_"
            "MODEL_OPTIMIZER_AND_PYTHON_NUMPY_TORCH_CPU_XPU_RNG_STATE_RELOAD_VERIFIED_EXACT_"
            "COMP_XPU_004_CHECKPOINT_UNCHANGED_NO_OOD_NO_TOF_SCRATCH_WEIGHTS_PROHIBITED_AS_COMP_XPU_005_RESUME_SOURCE_"
            "B2AG_FINAL_TRAINING_AUTHORIZATION_FREEZE_REQUIRED_COMP_XPU_005_FULL_TRAINING_NOT_YET_AUTHORIZED_B3_NOT_AUTHORIZED"
            if ok else
            "V16E1B2AF_XPU_SCRATCH_REHEARSAL_COMPLETED_WITH_GATE_FAILURE"
        )

        summary_payload = {
            "milestone":
                MILESTONE,

            "status":
                status,

            "B2AF_source_sha256":
                self_sha,

            "rehearsal_results_sha256":
                sha256(
                    REHEARSAL_RESULTS
                ),

            "scratch_checkpoint_sha256":
                scratch_checkpoint_sha,

            "scratch_only":
                True,

            "scratch_allowed_as_COMP_XPU_005_resume_source":
                False,

            "logical_batch_profiles":
                LOGICAL_BATCH,

            "microbatches":
                REHEARSAL_MICROBATCHES,

            "optimizer_steps":
                1,

            "logical_batch_seconds":
                float(
                    logical_seconds
                ),

            "logical_batch_mean_total_loss":
                float(
                    logical_mean_losses[
                        "total"
                    ]
                ),

            "logical_batch_mean_physics_loss":
                float(
                    logical_mean_losses[
                        "physics"
                    ]
                ),

            "accumulated_gradient_l2_norm":
                float(
                    accumulated_gradients[
                        "gradient_l2_norm"
                    ]
                ),

            "model_reload_exact":
                model_reload_exact,

            "optimizer_reload_exact":
                optimizer_reload_exact,

            "RNG_reload_exact":
                rng_reload_exact,

            "B2AG_authorized":
                bool(
                    ok
                ),

            "COMP_XPU_005_full_training_authorized":
                False,

            "B3_authorized":
                False,

            "next_milestone":
                (
                    "V16E-1B2AG-XPU — interpret certified scratch rehearsal and "
                    "freeze final COMP-XPU-005 fresh-run authorization contract; "
                    "scratch B2AF weights remain permanently prohibited as a "
                    "production initializer or resume source"
                    if ok else
                    "V16E-1B2AF-R1 — diagnose scratch rehearsal gate failure"
                ),

            "gates":
                {
                    k: bool(v)
                    for k, v in gates.items()
                },
        }

        SUMMARY.write_text(
            json.dumps(
                summary_payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        print("\nREHEARSAL RESULT")
        print(
            "  logical batch profiles :",
            LOGICAL_BATCH,
        )
        print(
            "  microbatches            :",
            REHEARSAL_MICROBATCHES,
        )
        print(
            "  optimizer steps         :",
            1,
        )
        print(
            "  logical batch seconds   :",
            f"{logical_seconds:.3f}",
        )
        print(
            "  accumulated grad norm   :",
            f"{accumulated_gradients['gradient_l2_norm']:.6e}",
        )
        print(
            "  mean total loss         :",
            f"{logical_mean_losses['total']:.6e}",
        )
        print(
            "  mean physics loss       :",
            f"{logical_mean_losses['physics']:.6e}",
        )
        print(
            "  model reload exact      :",
            model_reload_exact,
        )
        print(
            "  optimizer reload exact  :",
            optimizer_reload_exact,
        )
        print(
            "  RNG reload exact        :",
            rng_reload_exact,
        )
        print(
            "  scratch usable as COMP005 resume:",
            False,
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
            "  B2AF Source       :",
            self_sha,
        )
        print(
            "  Rehearsal Results :",
            sha256(
                REHEARSAL_RESULTS
            ),
        )
        print(
            "  Scratch Checkpoint:",
            scratch_checkpoint_sha,
        )
        print(
            "  Summary           :",
            sha256(
                SUMMARY
            ),
        )

        print("\nNEXT")
        print(
            " ",
            summary_payload[
                "next_milestone"
            ],
        )

        if not ok:
            sys.exit(
                2
            )

    except BaseException as exc:
        failure_payload = {
            "milestone":
                MILESTONE,

            "classification":
                "SCRATCH_EXECUTION_REHEARSAL_FAILURE",

            "error":
                f"{type(exc).__name__}: {exc}",

            "traceback":
                traceback.format_exc(),

            "B2AF_source_sha256":
                self_sha,

            "COMP004_checkpoint_SHA_unchanged":
                (
                    COMP004_CHECKPOINT.exists()
                    and sha256(
                        COMP004_CHECKPOINT
                    )
                    == COMP004_CHECKPOINT_SHA
                ),

            "scratch_allowed_as_COMP_XPU_005_resume_source":
                False,

            "COMP_XPU_005_full_training_authorized":
                False,

            "B3_authorized":
                False,

            "gates_before_failure":
                {
                    k: bool(v)
                    for k, v in gates.items()
                },
        }

        atomic_json_write(
            failure_payload,
            FAILURE,
        )

        status = (
            "V16E1B2AF_XPU_SCRATCH_EXECUTION_REHEARSAL_FAILED_CLOSED_"
            "FAILURE_ARTIFACT_WRITTEN_NO_COMP_XPU_005_TRAINING_AUTHORIZATION_"
            "NO_B3_AUTHORIZATION"
        )

        summary_payload = {
            "milestone":
                MILESTONE,

            "status":
                status,

            "B2AF_source_sha256":
                self_sha,

            "failure_sha256":
                sha256(
                    FAILURE
                ),

            "error":
                failure_payload[
                    "error"
                ],

            "scratch_allowed_as_COMP_XPU_005_resume_source":
                False,

            "B2AG_authorized":
                False,

            "COMP_XPU_005_full_training_authorized":
                False,

            "B3_authorized":
                False,

            "next_milestone":
                "V16E-1B2AF-R1 — diagnose scratch rehearsal failure without "
                "altering any certified upstream artifact or scientific setting",
        }

        SUMMARY.write_text(
            json.dumps(
                summary_payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        print("\nFAIL-CLOSED RESULT")
        print(
            " ",
            failure_payload[
                "error"
            ],
        )

        print("\nSTATUS")
        print(
            " ",
            status,
        )

        print("\nHASHES")
        print(
            "  Failure:",
            sha256(
                FAILURE
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
            summary_payload[
                "next_milestone"
            ],
        )

        sys.exit(
            2
        )


if __name__ == "__main__":
    main()
