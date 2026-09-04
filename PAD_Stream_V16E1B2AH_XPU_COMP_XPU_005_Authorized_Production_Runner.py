#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2AH-XPU
Authorized COMP-XPU-005 Fresh Corrected Stage-2 Production Runner

Experiment
----------
    V16E-BLREP-COMP-XPU-005

Authority
---------
V16E-1B2AG authorizes this production run.

Scientific model
----------------
UNCHANGED from the corrected Stage-2 branch.

Architecture:
    [xi, eta] sequence features + raw physical 11-D p11
    2 x LSTM(64)
    source-defined saturation-range output map

Teacher:
    frozen Stage-2 Godunov conservative dataset

Physics objective:
    corrected conservative moving-fan residual

Derivative engine:
    CHUNKED_BATCHED_VJP
    cotangent chunk = 16

Training:
    fresh seed = 1337
    epochs = 800
    logical batch = 8192
    microbatch = 128
    90 microbatches / epoch
    2 Adam steps / epoch
    1600 Adam steps total

Optimizer:
    torch.optim.Adam(
        model.parameters(),
        lr=1.0e-3,
        foreach=False,
    )

Accumulation:
    scaled_microbatch_loss =
        raw_microbatch_total_loss
        * (N_mb / N_current_logical_chunk)

Checkpoint:
    atomic after EVERY completed epoch

Resume:
    automatic from this runner's latest exact completed-epoch checkpoint only

Forbidden as production initializer/resume:
    * COMP-XPU-004 checkpoint
    * B2AF scratch checkpoint
    * all prior Stage-2 checkpoints

Evaluation:
    frozen development holdout only
    NOT OOD
    NO TOF

Failure behavior
----------------
A failure or interruption inside an epoch NEVER promotes the partial epoch.

The runner preserves the latest valid completed-epoch recovery checkpoint,
writes a failure artifact, and exits nonzero.

Rerun THIS SAME command to resume.

Completion
----------
A COMPLETE status requires:
    800 completed epochs
    1600 optimizer steps
    finite final model
    finite development-holdout metrics
    saturation-bounds diagnostic
    final checkpoint/history/config/metrics/manifest SHA binding
    no OOD
    no TOF

B3 remains blocked after training.
A separate V16E-1B2AI-XPU Stage-2 scientific closure/comparison is required.
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


# =============================================================================
# Frozen production identity
# =============================================================================

R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2AH-XPU"
EXPERIMENT_ID = "V16E-BLREP-COMP-XPU-005"

SEED = 1337
TARGET_EPOCHS = 800

ADOPTED_ENGINE = "CHUNKED_BATCHED_VJP"
ADOPTED_CHUNK = 16

LOGICAL_BATCH = 8192
MICROBATCH = 128
N_TOTAL = 14400
N_TRAIN = 11520
N_HOLDOUT = 2880

EXPECTED_MICROBATCHES_PER_EPOCH = 90
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


# =============================================================================
# Frozen authorities
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

# Exact corrected loss graph.
B2S_SOURCE = (
    R
    / "PAD_Stream_V16E1B2S_XPU_Corrected_Residual_Backward_Feasibility_Benchmark.py"
)
B2S_SOURCE_SHA = "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea"

# Exact chunked derivative engine.
B2AC_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AC_XPU_Chunked_Batched_VJP_Equivalence_Performance_Sweep.py"
)
B2AC_SOURCE_SHA = "59f7ea7b0dc2e901f5a42649691c2dab5f4dfc5d399f953eaab5ba773040cd53"

# B2AE execution contracts.
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

EXECUTION_CONTRACT_SHA = "6bf7794f493b95d9922573f24fdee30d1ff9f0caac5a0075d70a9abfa9dae83e"
ACCUMULATION_CONTRACT_SHA = "fd07af361a788f6cbc2c93faad8a196223dfd9a5894e67e2475e96657a8a5425"
RESUME_CONTRACT_SHA = "ba9f86b236e2276e507988d9c44f96b428c59aa1bedc02575f0c2b09c13bc449"

# B2AF scratch rehearsal authority. Evidence only.
B2AF_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AF_XPU_COMP005_One_Logical_Batch_Scratch_Rehearsal.py"
)
B2AF_SOURCE_SHA = "ef48eeb3e6d20cde86c5ddd6ab1632590480c58aef74d94369a419750040c29d"

B2AF_DIR = (
    R / "output"
    / "V16_E1B2AF_XPU_COMP005_SCRATCH_EXECUTION_REHEARSAL"
)
B2AF_RESULTS = B2AF_DIR / "V16E1B2AF_Scratch_Rehearsal_Results.json"
B2AF_SCRATCH_CHECKPOINT = B2AF_DIR / "V16E1B2AF_SCRATCH_ONE_LOGICAL_BATCH.pt"
B2AF_SUMMARY = B2AF_DIR / "PAD_Stream_V16E1B2AF_XPU_Summary.json"

B2AF_RESULTS_SHA = "232a27e9f7241915fc6b2febec976b382b28ed1aaeb63f28d5c0f3cce3b68390"
B2AF_SCRATCH_CHECKPOINT_SHA = "2fe57da770711257f6087446543e5a2d230d36a2263a7c5648bcc5bf40475152"
B2AF_SUMMARY_SHA = "182fd98351231b58847d391c3cda0554bb257e9753809acb20dc76be99230907"

# Final B2AG authorization authority.
B2AG_SOURCE = (
    R
    / "PAD_Stream_V16E1B2AG_XPU_B2AF_Interpretation_Final_COMP005_Authorization_Freeze.py"
)
B2AG_SOURCE_SHA = "04a707ce25bb6b1736e43fca2c96815c138893fd380aedbcd29d9121089f84d4"

B2AG_DIR = (
    R / "output"
    / "V16_E1B2AG_XPU_FINAL_COMP005_AUTHORIZATION"
)
B2AG_INTERPRETATION = B2AG_DIR / "V16E1B2AG_B2AF_Rehearsal_Interpretation.json"
B2AG_AUTHORIZATION = B2AG_DIR / "V16E1B2AG_COMP_XPU_005_Fresh_Run_Authorization.json"
B2AG_RUNNER_CONTRACT = B2AG_DIR / "V16E1B2AG_COMP_XPU_005_Production_Runner_Contract.json"
B2AG_HANDOFF = B2AG_DIR / "V16E1B2AG_COMP_XPU_005_Handoff.md"
B2AG_SUMMARY = B2AG_DIR / "PAD_Stream_V16E1B2AG_XPU_Summary.json"

B2AG_INTERPRETATION_SHA = "6c2a90809911c4481b9b14684e1e6551e6caba06804bd272cea7bb2f5360b3ff"
B2AG_AUTHORIZATION_SHA = "d29469101d4d4af979410140dad261bd0814ad27ff486e317b96bc969b4a2db0"
B2AG_RUNNER_CONTRACT_SHA = "080cd2c8a2139284d250c2362430cb765cba48e31b4e9f91e679c30057607df6"
B2AG_HANDOFF_SHA = "539a93207a363072541c488e96106b5c353cee8eeaf11f09105ebd73c40180d9"
B2AG_SUMMARY_SHA = "a45fc17979b0e20d35fd16733919885268e08700f4e0886b1d95fd6a149bc4b5"

EXPECTED_B2AG_STATUS = (
    "V16E1B2AG_XPU_B2AF_EXECUTION_REHEARSAL_INTERPRETATION_AND_FINAL_COMP_XPU_005_FRESH_RUN_AUTHORIZATION_FROZEN_"
    "PRODUCTION_SIZED_8192_PROFILE_CHUNK16_MICROBATCH128_PROFILE_WEIGHTED_ACCUMULATION_AND_ONE_ADAM_STEP_REHEARSAL_CERTIFIED_"
    "ATOMIC_SCRATCH_CHECKPOINT_MODEL_OPTIMIZER_AND_RNG_RELOAD_VERIFIED_EXACT_"
    "B2AF_SCRATCH_CHECKPOINT_PERMANENTLY_PROHIBITED_AS_PRODUCTION_INITIALIZER_OR_RESUME_SOURCE_"
    "COMP_XPU_004_AND_ALL_PRIOR_STAGE2_CHECKPOINTS_PROHIBITED_AS_FRESH_RUN_INITIALIZERS_"
    "FRESH_SEED_1337_COMP_XPU_005_RUN_CHUNK16_MICROBATCH128_LOGICAL8192_EPOCHS800_ADAM_LR1E_3_FOREACH_FALSE_AUTHORIZED_"
    "NINETY_MICROBATCHES_TWO_OPTIMIZER_STEPS_PER_EPOCH_1600_TARGET_STEPS_AND_ATOMIC_COMPLETED_EPOCH_RESUME_CONTRACT_BOUND_"
    "NO_TRAINING_IN_B2AG_NO_OOD_NO_TOF_COMP_XPU_005_FULL_TRAINING_AUTHORIZED_"
    "B3_NOT_AUTHORIZED_STAGE2_SCIENTIFIC_CLOSURE_REQUIRED_AFTER_TRAINING"
)


# =============================================================================
# Production output paths
# =============================================================================

OUT = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / EXPERIMENT_ID
)
OUT.mkdir(parents=True, exist_ok=True)

RECOVERY_DIR = OUT / "recovery"
RECOVERY_DIR.mkdir(parents=True, exist_ok=True)

RECOVERY_LATEST = RECOVERY_DIR / "V16E_BLREP_COMP_XPU_005_RECOVERY_LATEST.json"

CONFIG = OUT / "V16E_BLREP_COMP_XPU_005_Config.json"
HISTORY = OUT / "V16E_BLREP_COMP_XPU_005_Training_History.json"
CHECKPOINT = OUT / "V16E_BLREP_COMP_XPU_005.pt"
METRICS = OUT / "V16E_BLREP_COMP_XPU_005_Metrics.json"
MANIFEST = OUT / "V16E_BLREP_COMP_XPU_005_Manifest.json"
FAILURE = OUT / "V16E_BLREP_COMP_XPU_005_Latest_Failure.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2AH_XPU_Summary.json"


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


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(R))
    except ValueError:
        return str(path)


def jsonable(v):
    if isinstance(v, dict):
        return {
            str(k): jsonable(x)
            for k, x in v.items()
        }

    if isinstance(v, (list, tuple)):
        return [
            jsonable(x)
            for x in v
        ]

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
        raise RuntimeError(
            f"Could not import {path}"
        )

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def atomic_json_write(payload, destination: Path):
    tmp = destination.with_suffix(
        destination.suffix + ".tmp"
    )

    tmp.write_text(
        json.dumps(
            jsonable(payload),
            indent=2,
        ),
        encoding="utf-8",
    )

    os.replace(
        tmp,
        destination,
    )


def atomic_torch_save(payload, destination: Path):
    tmp = destination.with_suffix(
        destination.suffix + ".tmp"
    )

    if tmp.exists():
        tmp.unlink()

    torch.save(
        payload,
        tmp,
    )

    if (
        not tmp.exists()
        or tmp.stat().st_size <= 0
    ):
        raise RuntimeError(
            "Temporary checkpoint was not written."
        )

    os.replace(
        tmp,
        destination,
    )

    if (
        not destination.exists()
        or destination.stat().st_size <= 0
    ):
        raise RuntimeError(
            "Final checkpoint was not written."
        )


def cpu_clone(obj: Any):
    if torch.is_tensor(obj):
        return obj.detach().cpu().clone()

    if isinstance(obj, dict):
        return {
            k: cpu_clone(v)
            for k, v in obj.items()
        }

    if isinstance(obj, list):
        return [
            cpu_clone(v)
            for v in obj
        ]

    if isinstance(obj, tuple):
        return tuple(
            cpu_clone(v)
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
            a.shape == b.shape
            and a.dtype == b.dtype
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
        if type(a) is not type(b):
            return False

        if len(a) != len(b):
            return False

        return all(
            exact_tree_equal(x, y)
            for x, y in zip(a, b)
        )

    return a == b


def move_optimizer_state_to_device(optimizer, device):
    for state in optimizer.state.values():
        for key, value in list(state.items()):
            if torch.is_tensor(value):
                state[key] = value.to(
                    device
                )


def sync_xpu():
    if hasattr(torch.xpu, "synchronize"):
        torch.xpu.synchronize()


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

        if not torch.isfinite(
            g
        ).all().item():
            finite_all = False

        if torch.count_nonzero(
            g
        ).item() > 0:
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


# =============================================================================
# RNG state helpers
# =============================================================================

def get_xpu_rng_state():
    if not torch.xpu.is_available():
        return None

    if hasattr(torch.xpu, "get_rng_state_all"):
        try:
            return [
                s.detach().cpu().clone()
                for s in torch.xpu.get_rng_state_all()
            ]
        except Exception:
            pass

    if hasattr(torch.xpu, "get_rng_state"):
        try:
            return [
                torch.xpu.get_rng_state()
                .detach()
                .cpu()
                .clone()
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


# =============================================================================
# Frozen split / epoch order
# =============================================================================

def frozen_split(n: int):
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

    return (
        idx[:n_train],
        idx[n_train:],
    )


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
# Authority validation
# =============================================================================

def authority_gates():
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

        "B2AF_source_SHA_exact":
            exact(
                B2AF_SOURCE,
                B2AF_SOURCE_SHA,
            ),

        "B2AF_results_SHA_exact":
            exact(
                B2AF_RESULTS,
                B2AF_RESULTS_SHA,
            ),

        "B2AF_scratch_checkpoint_SHA_exact":
            exact(
                B2AF_SCRATCH_CHECKPOINT,
                B2AF_SCRATCH_CHECKPOINT_SHA,
            ),

        "B2AF_summary_SHA_exact":
            exact(
                B2AF_SUMMARY,
                B2AF_SUMMARY_SHA,
            ),

        "B2AG_source_SHA_exact":
            exact(
                B2AG_SOURCE,
                B2AG_SOURCE_SHA,
            ),

        "B2AG_interpretation_SHA_exact":
            exact(
                B2AG_INTERPRETATION,
                B2AG_INTERPRETATION_SHA,
            ),

        "B2AG_authorization_SHA_exact":
            exact(
                B2AG_AUTHORIZATION,
                B2AG_AUTHORIZATION_SHA,
            ),

        "B2AG_runner_contract_SHA_exact":
            exact(
                B2AG_RUNNER_CONTRACT,
                B2AG_RUNNER_CONTRACT_SHA,
            ),

        "B2AG_handoff_SHA_exact":
            exact(
                B2AG_HANDOFF,
                B2AG_HANDOFF_SHA,
            ),

        "B2AG_summary_SHA_exact":
            exact(
                B2AG_SUMMARY,
                B2AG_SUMMARY_SHA,
            ),
    }

    auth = (
        read_json(
            B2AG_AUTHORIZATION
        )
        if B2AG_AUTHORIZATION.exists()
        else {}
    )

    runner_contract = (
        read_json(
            B2AG_RUNNER_CONTRACT
        )
        if B2AG_RUNNER_CONTRACT.exists()
        else {}
    )

    ag_summary = (
        read_json(
            B2AG_SUMMARY
        )
        if B2AG_SUMMARY.exists()
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

    gates.update({
        "B2AG_status_exact":
            ag_summary.get(
                "status"
            )
            == EXPECTED_B2AG_STATUS,

        "B2AG_training_authorized":
            ag_summary.get(
                "COMP_XPU_005_full_training_authorized"
            )
            is True,

        "B2AG_B3_false":
            ag_summary.get(
                "B3_authorized"
            )
            is False,

        "authorization_experiment_exact":
            auth.get(
                "experiment_id"
            )
            == EXPERIMENT_ID,

        "authorization_true":
            auth.get(
                "authorized"
            )
            is True,

        "authorization_fresh_true":
            auth.get(
                "fresh_initialization_required"
            )
            is True,

        "authorization_seed_1337":
            auth.get(
                "seed"
            )
            == SEED,

        "authorization_engine_exact":
            (
                auth
                .get("implementation", {})
                .get("derivative_engine")
                == ADOPTED_ENGINE
            ),

        "authorization_chunk_16":
            (
                auth
                .get("implementation", {})
                .get("cotangent_chunk_size")
                == ADOPTED_CHUNK
            ),

        "authorization_microbatch_128":
            (
                auth
                .get("implementation", {})
                .get("microbatch")
                == MICROBATCH
            ),

        "authorization_logical_batch_8192":
            (
                auth
                .get("implementation", {})
                .get("logical_batch")
                == LOGICAL_BATCH
            ),

        "authorization_epochs_800":
            (
                auth
                .get("implementation", {})
                .get("epochs")
                == TARGET_EPOCHS
            ),

        "authorization_target_steps_1600":
            auth.get(
                "target_optimizer_steps"
            )
            == EXPECTED_TARGET_OPTIMIZER_STEPS,

        "B2AF_scratch_forbidden":
            "B2AF scratch checkpoint"
            in auth.get(
                "forbidden_initializers_or_resume_sources",
                [],
            ),

        "COMP004_forbidden":
            "COMP-XPU-004 checkpoint"
            in auth.get(
                "forbidden_initializers_or_resume_sources",
                [],
            ),

        "runner_contract_experiment_exact":
            runner_contract.get(
                "experiment_id"
            )
            == EXPERIMENT_ID,

        "execution_experiment_exact":
            execution.get(
                "experiment_id"
            )
            == EXPERIMENT_ID,

        "execution_fresh_true":
            (
                execution
                .get("fresh_training", {})
                .get("required")
                is True
            ),

        "execution_COMP004_initializer_false":
            (
                execution
                .get("fresh_training", {})
                .get("initialize_from_COMP004_checkpoint")
                is False
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

        "accumulation_steps_1600":
            accumulation.get(
                "target_optimizer_steps"
            )
            == EXPECTED_TARGET_OPTIMIZER_STEPS,

        "resume_COMP004_forbidden":
            resume.get(
                "COMP004_checkpoint_allowed_as_training_resume"
            )
            is False,

        "resume_epoch_boundary_only":
            (
                resume.get(
                    "mid_epoch_resume_allowed"
                )
                is False
                and resume.get(
                    "mid_logical_batch_resume_allowed"
                )
                is False
                and resume.get(
                    "partial_gradient_resume_allowed"
                )
                is False
            ),

        "no_OOD":
            True,

        "no_TOF":
            True,
    })

    return gates


# =============================================================================
# Fresh model construction
# =============================================================================

def build_fresh_model_optimizer(B2S, device, suffix: str):
    M = B2S.import_module(
        B2S.BASE_RUNNER,
        f"b2ah_base_{suffix}",
    )

    J = B2S.import_module(
        B2S.B2J_SOURCE,
        f"b2ah_eta_{suffix}",
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
            "B2S-bound eta-model source SHA mismatch."
        )

    if int(M.SEED) != SEED:
        raise RuntimeError(
            f"Frozen base-runner seed mismatch: {M.SEED}"
        )

    if int(M.LOGICAL_BATCH) != LOGICAL_BATCH:
        raise RuntimeError(
            f"Frozen base-runner logical batch mismatch: {M.LOGICAL_BATCH}"
        )

    expected_losses = {
        "lambda_data":
            float(M.LAMBDA_DATA),

        "lambda_phys":
            float(M.LAMBDA_PHYS),

        "lambda_bc":
            float(M.LAMBDA_BC),

        "lambda_tip":
            float(M.LAMBDA_TIP),

        "lambda_anchor":
            float(M.LAMBDA_ANCHOR),

        "lambda_mono":
            float(M.LAMBDA_MONO),

        "lambda_shape":
            float(getattr(M, "LAMBDA_SHAPE", 0.0)),
    }

    if expected_losses != LOSS_WEIGHTS:
        raise RuntimeError(
            "Frozen Stage-2 loss weights do not match B2AG production contract.\n"
            f"Expected: {LOSS_WEIGHTS}\n"
            f"Actual  : {expected_losses}"
        )

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
# Production configuration
# =============================================================================

def expected_config(runner_sha: str, B2S):
    return {
        "milestone":
            MILESTONE,

        "experiment_id":
            EXPERIMENT_ID,

        "classification":
            "AUTHORIZED_FRESH_CORRECTED_STAGE2_PRODUCTION_RUN",

        "runner_sha256":
            runner_sha,

        "framework":
            {
                "name":
                    "PyTorch XPU",

                "pytorch_version":
                    torch.__version__,

                "mixed_precision":
                    False,
            },

        "fresh_initialization":
            {
                "required":
                    True,

                "seed":
                    SEED,

                "COMP004_initializer":
                    False,

                "B2AF_scratch_initializer":
                    False,
            },

        "scientific_model":
            {
                "sequence_features":
                    ["xi", "eta"],

                "conditioner_dim":
                    11,

                "hidden":
                    64,

                "layers":
                    2,

                "physical_Nc_scaled":
                    False,

                "corrected_residual":
                    "conservative moving-fan residual",

                "scientific_graph_source_sha256":
                    B2S_SOURCE_SHA,

                "scientific_change":
                    False,
            },

        "derivative_engine":
            {
                "name":
                    ADOPTED_ENGINE,

                "cotangent_chunk_size":
                    ADOPTED_CHUNK,

                "implementation_source_sha256":
                    B2AC_SOURCE_SHA,
            },

        "training":
            {
                "train_profiles":
                    N_TRAIN,

                "holdout_profiles":
                    N_HOLDOUT,

                "logical_batch":
                    LOGICAL_BATCH,

                "microbatch":
                    MICROBATCH,

                "microbatches_per_epoch":
                    EXPECTED_MICROBATCHES_PER_EPOCH,

                "optimizer_steps_per_epoch":
                    EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,

                "epochs":
                    TARGET_EPOCHS,

                "target_optimizer_steps":
                    EXPECTED_TARGET_OPTIMIZER_STEPS,
            },

        "optimizer":
            {
                "name":
                    "Adam",

                "learning_rate":
                    LR,

                "foreach":
                    False,

                "scheduler":
                    None,

                "gradient_clipping":
                    None,
            },

        "loss_weights":
            LOSS_WEIGHTS,

        "contracts":
            {
                "execution_contract_sha256":
                    EXECUTION_CONTRACT_SHA,

                "accumulation_contract_sha256":
                    ACCUMULATION_CONTRACT_SHA,

                "resume_contract_sha256":
                    RESUME_CONTRACT_SHA,

                "B2AG_authorization_sha256":
                    B2AG_AUTHORIZATION_SHA,

                "B2AG_runner_contract_sha256":
                    B2AG_RUNNER_CONTRACT_SHA,
            },

        "dataset":
            {
                "path":
                    rel(
                        DATASET
                    ),

                "sha256":
                    DATASET_SHA,
            },

        "evaluation":
            {
                "role":
                    "development diagnostic; NOT OOD",

                "model_eval":
                    True,

                "torch_no_grad":
                    True,

                "OOD":
                    False,

                "TOF":
                    False,
            },
    }


# =============================================================================
# Recovery checkpoints
# =============================================================================

def recovery_path(epoch: int) -> Path:
    return (
        RECOVERY_DIR
        / f"V16E_BLREP_COMP_XPU_005_RECOVERY_E{epoch:04d}.pt"
    )


def source_sha_map(runner_sha: str, B2S):
    return {
        "B2AH_runner_sha256":
            runner_sha,

        "B2S_source_sha256":
            B2S_SOURCE_SHA,

        "B2S_base_runner_sha256":
            B2S.BASE_RUNNER_SHA,

        "B2S_eta_source_sha256":
            B2S.B2J_SOURCE_SHA,

        "B2AC_source_sha256":
            B2AC_SOURCE_SHA,

        "B2AE_source_sha256":
            B2AE_SOURCE_SHA,

        "B2AF_source_sha256":
            B2AF_SOURCE_SHA,

        "B2AG_source_sha256":
            B2AG_SOURCE_SHA,
    }


def save_recovery_checkpoint(
    B2S,
    runner_sha,
    model,
    optimizer,
    history,
    completed_epoch,
    optimizer_steps_completed,
    train_idx,
    holdout_idx,
):
    if completed_epoch < 1:
        raise RuntimeError(
            "Production recovery checkpoint requires completed_epoch >= 1."
        )

    if (
        optimizer_steps_completed
        != completed_epoch
        * EXPECTED_OPTIMIZER_STEPS_PER_EPOCH
    ):
        raise RuntimeError(
            "Optimizer-step count is inconsistent with completed epoch."
        )

    rng = capture_rng_state()

    ck_path = recovery_path(
        completed_epoch
    )

    payload = {
        "recovery_schema":
            "V16E1B2AH_XPU_COMP005_COMPLETED_EPOCH_V1",

        "experiment_id":
            EXPERIMENT_ID,

        "created_by_authorized_B2AH_runner":
            True,

        "runner_sha256":
            runner_sha,

        "completed_epoch":
            int(
                completed_epoch
            ),

        "optimizer_steps_completed":
            int(
                optimizer_steps_completed
            ),

        "target_epochs":
            TARGET_EPOCHS,

        "target_optimizer_steps":
            EXPECTED_TARGET_OPTIMIZER_STEPS,

        "seed":
            SEED,

        "logical_batch":
            LOGICAL_BATCH,

        "microbatch":
            MICROBATCH,

        "derivative_engine":
            ADOPTED_ENGINE,

        "cotangent_chunk_size":
            ADOPTED_CHUNK,

        "learning_rate":
            LR,

        "optimizer":
            "Adam(foreach=False)",

        "execution_contract_sha256":
            EXECUTION_CONTRACT_SHA,

        "accumulation_contract_sha256":
            ACCUMULATION_CONTRACT_SHA,

        "resume_contract_sha256":
            RESUME_CONTRACT_SHA,

        "B2AG_authorization_sha256":
            B2AG_AUTHORIZATION_SHA,

        "B2AG_runner_contract_sha256":
            B2AG_RUNNER_CONTRACT_SHA,

        "dataset_sha256":
            DATASET_SHA,

        "source_sha256_map":
            source_sha_map(
                runner_sha,
                B2S,
            ),

        "model_state_dict":
            cpu_clone(
                model.state_dict()
            ),

        "optimizer_state_dict":
            cpu_clone(
                optimizer.state_dict()
            ),

        "history":
            copy.deepcopy(
                history
            ),

        "train_idx":
            np.asarray(
                train_idx,
                dtype=np.int64,
            ),

        "holdout_idx":
            np.asarray(
                holdout_idx,
                dtype=np.int64,
            ),

        "python_rng_state":
            rng[
                "python"
            ],

        "numpy_rng_state":
            rng[
                "numpy"
            ],

        "torch_cpu_rng_state":
            rng[
                "torch_cpu"
            ],

        "torch_xpu_rng_state":
            rng[
                "torch_xpu"
            ],

        "training_semantics":
            {
                "fresh_experiment":
                    True,

                "epoch_boundary_only":
                    True,

                "partial_epoch_accepted":
                    False,

                "optimizer_state_restored_on_resume":
                    True,

                "B2AF_scratch_resume":
                    False,

                "COMP004_resume":
                    False,

                "OOD":
                    False,

                "TOF":
                    False,
            },
    }

    atomic_torch_save(
        payload,
        ck_path,
    )

    ck_sha = sha256(
        ck_path
    )

    latest = {
        "experiment_id":
            EXPERIMENT_ID,

        "created_by_authorized_B2AH_runner":
            True,

        "runner_sha256":
            runner_sha,

        "completed_epoch":
            int(
                completed_epoch
            ),

        "optimizer_steps_completed":
            int(
                optimizer_steps_completed
            ),

        "checkpoint_path":
            rel(
                ck_path
            ),

        "checkpoint_sha256":
            ck_sha,

        "execution_contract_sha256":
            EXECUTION_CONTRACT_SHA,

        "accumulation_contract_sha256":
            ACCUMULATION_CONTRACT_SHA,

        "resume_contract_sha256":
            RESUME_CONTRACT_SHA,

        "B2AG_authorization_sha256":
            B2AG_AUTHORIZATION_SHA,

        "dataset_sha256":
            DATASET_SHA,

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
    }

    atomic_json_write(
        latest,
        RECOVERY_LATEST,
    )

    # Keep current and immediately previous completed-epoch recovery payloads.
    keep_epochs = {
        completed_epoch,
        max(
            completed_epoch - 1,
            1,
        ),
    }

    for old in RECOVERY_DIR.glob(
        "V16E_BLREP_COMP_XPU_005_RECOVERY_E*.pt"
    ):
        try:
            stem_epoch = int(
                old.stem.split("_E")[-1]
            )
        except Exception:
            continue

        if stem_epoch not in keep_epochs:
            try:
                old.unlink()
            except OSError:
                pass

    print(
        f"  [RECOVERY] completed epoch {completed_epoch:04d}"
        f" | optimizer steps {optimizer_steps_completed:04d}"
    )
    print(
        "             SHA-256:",
        ck_sha,
    )

    return (
        ck_path,
        ck_sha,
    )


def load_valid_recovery(
    B2S,
    runner_sha,
    model,
    optimizer,
    device,
):
    if not RECOVERY_LATEST.exists():
        stale_recovery = list(
            RECOVERY_DIR.glob(
                "V16E_BLREP_COMP_XPU_005_RECOVERY_E*.pt"
            )
        )

        if stale_recovery:
            raise RuntimeError(
                "Production recovery checkpoint files exist but the exact "
                "LATEST pointer is missing. Refusing ambiguous resume."
            )

        return None

    latest = read_json(
        RECOVERY_LATEST
    )

    pointer_checks = {
        "experiment_id":
            latest.get(
                "experiment_id"
            )
            == EXPERIMENT_ID,

        "created_by_runner":
            latest.get(
                "created_by_authorized_B2AH_runner"
            )
            is True,

        "runner_sha":
            latest.get(
                "runner_sha256"
            )
            == runner_sha,

        "execution_contract":
            latest.get(
                "execution_contract_sha256"
            )
            == EXECUTION_CONTRACT_SHA,

        "accumulation_contract":
            latest.get(
                "accumulation_contract_sha256"
            )
            == ACCUMULATION_CONTRACT_SHA,

        "resume_contract":
            latest.get(
                "resume_contract_sha256"
            )
            == RESUME_CONTRACT_SHA,

        "B2AG_authorization":
            latest.get(
                "B2AG_authorization_sha256"
            )
            == B2AG_AUTHORIZATION_SHA,

        "dataset":
            latest.get(
                "dataset_sha256"
            )
            == DATASET_SHA,

        "engine":
            latest.get(
                "derivative_engine"
            )
            == ADOPTED_ENGINE,

        "chunk":
            latest.get(
                "cotangent_chunk_size"
            )
            == ADOPTED_CHUNK,

        "logical_batch":
            latest.get(
                "logical_batch"
            )
            == LOGICAL_BATCH,

        "microbatch":
            latest.get(
                "microbatch"
            )
            == MICROBATCH,

        "seed":
            latest.get(
                "seed"
            )
            == SEED,
    }

    if not all(
        pointer_checks.values()
    ):
        failed = [
            k
            for k, v in pointer_checks.items()
            if not v
        ]

        raise RuntimeError(
            "Production recovery pointer mismatch: "
            + ", ".join(
                failed
            )
        )

    ck_path = (
        R / latest[
            "checkpoint_path"
        ]
    )

    if not ck_path.exists():
        raise RuntimeError(
            f"Recovery checkpoint does not exist: {ck_path}"
        )

    actual_sha = sha256(
        ck_path
    )

    if actual_sha != latest.get(
        "checkpoint_sha256"
    ):
        raise RuntimeError(
            "Production recovery checkpoint SHA mismatch.\n"
            f"Expected: {latest.get('checkpoint_sha256')}\n"
            f"Actual  : {actual_sha}"
        )

    # Explicitly prohibit B2AF scratch checkpoint identity.
    if actual_sha == B2AF_SCRATCH_CHECKPOINT_SHA:
        raise RuntimeError(
            "B2AF scratch checkpoint is permanently prohibited as "
            "a COMP-XPU-005 resume source."
        )

    if actual_sha == COMP004_CHECKPOINT_SHA:
        raise RuntimeError(
            "COMP-XPU-004 checkpoint is prohibited as a COMP-XPU-005 resume source."
        )

    payload = torch.load(
        ck_path,
        map_location="cpu",
        weights_only=False,
    )

    completed_epoch = int(
        payload.get(
            "completed_epoch",
            -1,
        )
    )

    optimizer_steps_completed = int(
        payload.get(
            "optimizer_steps_completed",
            -1,
        )
    )

    payload_checks = {
        "schema":
            payload.get(
                "recovery_schema"
            )
            == "V16E1B2AH_XPU_COMP005_COMPLETED_EPOCH_V1",

        "experiment_id":
            payload.get(
                "experiment_id"
            )
            == EXPERIMENT_ID,

        "created_by_runner":
            payload.get(
                "created_by_authorized_B2AH_runner"
            )
            is True,

        "runner_sha":
            payload.get(
                "runner_sha256"
            )
            == runner_sha,

        "completed_epoch_range":
            1 <= completed_epoch <= TARGET_EPOCHS,

        "optimizer_step_count":
            optimizer_steps_completed
            == completed_epoch
            * EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,

        "target_epochs":
            payload.get(
                "target_epochs"
            )
            == TARGET_EPOCHS,

        "target_optimizer_steps":
            payload.get(
                "target_optimizer_steps"
            )
            == EXPECTED_TARGET_OPTIMIZER_STEPS,

        "seed":
            payload.get(
                "seed"
            )
            == SEED,

        "logical_batch":
            payload.get(
                "logical_batch"
            )
            == LOGICAL_BATCH,

        "microbatch":
            payload.get(
                "microbatch"
            )
            == MICROBATCH,

        "engine":
            payload.get(
                "derivative_engine"
            )
            == ADOPTED_ENGINE,

        "chunk":
            payload.get(
                "cotangent_chunk_size"
            )
            == ADOPTED_CHUNK,

        "learning_rate":
            payload.get(
                "learning_rate"
            )
            == LR,

        "execution_contract":
            payload.get(
                "execution_contract_sha256"
            )
            == EXECUTION_CONTRACT_SHA,

        "accumulation_contract":
            payload.get(
                "accumulation_contract_sha256"
            )
            == ACCUMULATION_CONTRACT_SHA,

        "resume_contract":
            payload.get(
                "resume_contract_sha256"
            )
            == RESUME_CONTRACT_SHA,

        "B2AG_authorization":
            payload.get(
                "B2AG_authorization_sha256"
            )
            == B2AG_AUTHORIZATION_SHA,

        "B2AG_runner_contract":
            payload.get(
                "B2AG_runner_contract_sha256"
            )
            == B2AG_RUNNER_CONTRACT_SHA,

        "dataset":
            payload.get(
                "dataset_sha256"
            )
            == DATASET_SHA,

        "source_sha_map":
            payload.get(
                "source_sha256_map"
            )
            == source_sha_map(
                runner_sha,
                B2S,
            ),
    }

    if not all(
        payload_checks.values()
    ):
        failed = [
            k
            for k, v in payload_checks.items()
            if not v
        ]

        raise RuntimeError(
            "Production recovery payload mismatch: "
            + ", ".join(
                failed
            )
        )

    history = payload.get(
        "history",
        {},
    )

    if (
        not isinstance(
            history.get(
                "epoch"
            ),
            list,
        )
        or len(
            history[
                "epoch"
            ]
        )
        != completed_epoch
        or history[
            "epoch"
        ][-1]
        != completed_epoch
    ):
        raise RuntimeError(
            "Production recovery history does not match completed epoch."
        )

    train_idx = np.asarray(
        payload[
            "train_idx"
        ],
        dtype=np.int64,
    )

    holdout_idx = np.asarray(
        payload[
            "holdout_idx"
        ],
        dtype=np.int64,
    )

    expected_train, expected_holdout = frozen_split(
        N_TOTAL
    )

    if not np.array_equal(
        train_idx,
        expected_train,
    ):
        raise RuntimeError(
            "Production recovery train split differs from frozen split."
        )

    if not np.array_equal(
        holdout_idx,
        expected_holdout,
    ):
        raise RuntimeError(
            "Production recovery holdout split differs from frozen split."
        )

    model.load_state_dict(
        payload[
            "model_state_dict"
        ],
        strict=True,
    )

    model.to(
        device
    )

    optimizer.load_state_dict(
        payload[
            "optimizer_state_dict"
        ]
    )

    move_optimizer_state_to_device(
        optimizer,
        device,
    )

    restore_rng_state({
        "python":
            payload[
                "python_rng_state"
            ],

        "numpy":
            payload[
                "numpy_rng_state"
            ],

        "torch_cpu":
            payload[
                "torch_cpu_rng_state"
            ],

        "torch_xpu":
            payload[
                "torch_xpu_rng_state"
            ],
    })

    sync_xpu()

    if not all_model_parameters_finite(
        model
    ):
        raise RuntimeError(
            "Recovered model contains nonfinite parameters."
        )

    print("\nVALID PRODUCTION RECOVERY FOUND")
    print(
        "  completed epoch       :",
        completed_epoch,
    )
    print(
        "  optimizer steps       :",
        optimizer_steps_completed,
    )
    print(
        "  checkpoint            :",
        ck_path,
    )
    print(
        "  checkpoint SHA-256    :",
        actual_sha,
    )
    print(
        "  next epoch            :",
        completed_epoch + 1,
    )

    return {
        "completed_epoch":
            completed_epoch,

        "optimizer_steps_completed":
            optimizer_steps_completed,

        "history":
            history,

        "train_idx":
            train_idx,

        "holdout_idx":
            holdout_idx,

        "checkpoint_path":
            ck_path,

        "checkpoint_sha256":
            actual_sha,
    }


# =============================================================================
# Training
# =============================================================================

def empty_history():
    return {
        "epoch": [],
        "data": [],
        "physics": [],
        "bc_inj": [],
        "bc_tip": [],
        "anchor": [],
        "mono": [],
        "total": [],
        "epoch_seconds": [],
        "optimizer_steps_completed": [],
    }


def train_or_resume(
    B2S,
    B2AC,
    M,
    model,
    optimizer,
    arrays,
    device,
    runner_sha,
):
    (
        xi_all,
        Sw_all,
        p11_all,
        tD_all,
        ai_all,
        at_all,
    ) = arrays

    train_idx, holdout_idx = frozen_split(
        len(
            xi_all
        )
    )

    if (
        len(
            train_idx
        )
        != N_TRAIN
        or len(
            holdout_idx
        )
        != N_HOLDOUT
    ):
        raise RuntimeError(
            "Frozen 80/20 split counts are not 11520/2880."
        )

    history = empty_history()

    recovery = load_valid_recovery(
        B2S=B2S,
        runner_sha=runner_sha,
        model=model,
        optimizer=optimizer,
        device=device,
    )

    if recovery is None:
        start_epoch = 1
        optimizer_steps_completed = 0

        print("\nPRODUCTION START")
        print(
            "  mode                  : FRESH"
        )
        print(
            "  seed                  :",
            SEED,
        )
        print(
            "  COMP-XPU-004 weights  : NOT LOADED"
        )
        print(
            "  B2AF scratch weights  : NOT LOADED"
        )

    else:
        start_epoch = (
            recovery[
                "completed_epoch"
            ]
            + 1
        )

        optimizer_steps_completed = (
            recovery[
                "optimizer_steps_completed"
            ]
        )

        history = recovery[
            "history"
        ]

        train_idx = recovery[
            "train_idx"
        ]

        holdout_idx = recovery[
            "holdout_idx"
        ]

        print(
            "  mode                  : RESUME"
        )

    print("\nPRODUCTION TRAINING CONTRACT")
    print(
        "  device                :",
        device,
    )
    print(
        "  train profiles        :",
        len(
            train_idx
        ),
    )
    print(
        "  holdout profiles      :",
        len(
            holdout_idx
        ),
    )
    print(
        "  derivative engine     :",
        ADOPTED_ENGINE,
    )
    print(
        "  cotangent chunk       :",
        ADOPTED_CHUNK,
    )
    print(
        "  logical batch         :",
        LOGICAL_BATCH,
    )
    print(
        "  microbatch            :",
        MICROBATCH,
    )
    print(
        "  microbatches/epoch    :",
        EXPECTED_MICROBATCHES_PER_EPOCH,
    )
    print(
        "  optimizer steps/epoch :",
        EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
    )
    print(
        "  target epochs         :",
        TARGET_EPOCHS,
    )
    print(
        "  target optimizer steps:",
        EXPECTED_TARGET_OPTIMIZER_STEPS,
    )
    print(
        "  starting epoch        :",
        start_epoch,
    )
    print(
        "  mixed precision       : OFF"
    )

    if start_epoch > TARGET_EPOCHS:
        if (
            len(
                history[
                    "epoch"
                ]
            )
            != TARGET_EPOCHS
            or optimizer_steps_completed
            != EXPECTED_TARGET_OPTIMIZER_STEPS
        ):
            raise RuntimeError(
                "Recovery claims training beyond target but history/step count is inconsistent."
            )

        return (
            history,
            train_idx,
            holdout_idx,
            optimizer_steps_completed,
        )

    engine = B2AC.make_chunked_batched_engine(
        ADOPTED_CHUNK
    )

    original_engine = (
        B2S.local_recurrent_derivatives_create_graph
    )

    session_t0 = time.time()

    try:
        B2S.local_recurrent_derivatives_create_graph = engine

        for epoch in range(
            start_epoch,
            TARGET_EPOCHS + 1,
        ):
            epoch_t0 = time.time()

            order = production_epoch_order(
                train_idx,
                epoch,
            )

            sums = {
                "data": 0.0,
                "physics": 0.0,
                "bc_inj": 0.0,
                "bc_tip": 0.0,
                "anchor": 0.0,
                "mono": 0.0,
                "total": 0.0,
            }

            count = 0
            epoch_microbatches = 0
            epoch_optimizer_steps = 0

            for b0 in range(
                0,
                len(
                    order
                ),
                LOGICAL_BATCH,
            ):
                logical_idx = order[
                    b0:
                    b0
                    + LOGICAL_BATCH
                ]

                logical_n = len(
                    logical_idx
                )

                if logical_n not in (
                    8192,
                    3328,
                ):
                    raise RuntimeError(
                        f"Unexpected logical chunk size {logical_n}."
                    )

                optimizer.zero_grad(
                    set_to_none=True
                )

                for m0 in range(
                    0,
                    logical_n,
                    MICROBATCH,
                ):
                    ids = logical_idx[
                        m0:
                        m0
                        + MICROBATCH
                    ]

                    m = len(
                        ids
                    )

                    if m <= 0:
                        raise RuntimeError(
                            "Empty training microbatch."
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
                            f"Epoch {epoch}: nonfinite prediction."
                        )

                    if not torch.isfinite(
                        residual
                    ).all().item():
                        raise RuntimeError(
                            f"Epoch {epoch}: nonfinite corrected residual."
                        )

                    if not all(
                        torch.isfinite(
                            v
                        ).all().item()
                        for v in parts.values()
                    ):
                        raise RuntimeError(
                            f"Epoch {epoch}: nonfinite loss."
                        )

                    scale = (
                        float(
                            m
                        )
                        / float(
                            logical_n
                        )
                    )

                    scaled_total = (
                        parts[
                            "total"
                        ]
                        * scale
                    )

                    scaled_total.backward()

                    for k in sums:
                        sums[
                            k
                        ] += (
                            float(
                                parts[
                                    k
                                ]
                                .detach()
                                .cpu()
                            )
                            * m
                        )

                    count += m
                    epoch_microbatches += 1

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

                accumulated = parameter_gradient_summary(
                    model
                )

                if not accumulated[
                    "gradients_finite"
                ]:
                    raise RuntimeError(
                        f"Epoch {epoch}: accumulated parameter gradients are nonfinite."
                    )

                if accumulated[
                    "nonzero_gradient_tensor_count"
                ] <= 0:
                    raise RuntimeError(
                        f"Epoch {epoch}: accumulated parameter gradients are all zero."
                    )

                optimizer.step()

                sync_xpu()

                optimizer_steps_completed += 1
                epoch_optimizer_steps += 1

                if not all_model_parameters_finite(
                    model
                ):
                    raise RuntimeError(
                        f"Epoch {epoch}: model parameters became nonfinite after optimizer step."
                    )

                optimizer.zero_grad(
                    set_to_none=True
                )

            # Epoch is accepted only after all queued XPU work succeeds.
            sync_xpu()

            if count != N_TRAIN:
                raise RuntimeError(
                    f"Epoch {epoch}: accepted {count} profiles; expected {N_TRAIN}."
                )

            if (
                epoch_microbatches
                != EXPECTED_MICROBATCHES_PER_EPOCH
            ):
                raise RuntimeError(
                    f"Epoch {epoch}: executed {epoch_microbatches} microbatches; "
                    f"expected {EXPECTED_MICROBATCHES_PER_EPOCH}."
                )

            if (
                epoch_optimizer_steps
                != EXPECTED_OPTIMIZER_STEPS_PER_EPOCH
            ):
                raise RuntimeError(
                    f"Epoch {epoch}: executed {epoch_optimizer_steps} optimizer steps; "
                    f"expected {EXPECTED_OPTIMIZER_STEPS_PER_EPOCH}."
                )

            expected_steps_after_epoch = (
                epoch
                * EXPECTED_OPTIMIZER_STEPS_PER_EPOCH
            )

            if (
                optimizer_steps_completed
                != expected_steps_after_epoch
            ):
                raise RuntimeError(
                    f"Epoch {epoch}: cumulative optimizer steps "
                    f"{optimizer_steps_completed}; expected {expected_steps_after_epoch}."
                )

            sec = (
                time.time()
                - epoch_t0
            )

            n = max(
                count,
                1,
            )

            history[
                "epoch"
            ].append(
                epoch
            )

            for k in sums:
                history[
                    k
                ].append(
                    sums[
                        k
                    ]
                    / n
                )

            history[
                "epoch_seconds"
            ].append(
                float(
                    sec
                )
            )

            history[
                "optimizer_steps_completed"
            ].append(
                int(
                    optimizer_steps_completed
                )
            )

            print(
                f"[COMP005] Epoch {epoch:04d}/{TARGET_EPOCHS} "
                f"| Data {history['data'][-1]:.3e} "
                f"| Phys {history['physics'][-1]:.3e} "
                f"| BC {history['bc_inj'][-1]:.3e} "
                f"| Tip {history['bc_tip'][-1]:.3e} "
                f"| Anchor {history['anchor'][-1]:.3e} "
                f"| Mono {history['mono'][-1]:.3e} "
                f"| Total {history['total'][-1]:.3e} "
                f"| {sec/60.0:.2f} min/epoch "
                f"| steps {optimizer_steps_completed}/{EXPECTED_TARGET_OPTIMIZER_STEPS} "
                f"| session {(time.time()-session_t0)/3600.0:.2f} h"
            )

            save_recovery_checkpoint(
                B2S=B2S,
                runner_sha=runner_sha,
                model=model,
                optimizer=optimizer,
                history=history,
                completed_epoch=epoch,
                optimizer_steps_completed=optimizer_steps_completed,
                train_idx=train_idx,
                holdout_idx=holdout_idx,
            )

    finally:
        B2S.local_recurrent_derivatives_create_graph = (
            original_engine
        )

    return (
        history,
        train_idx,
        holdout_idx,
        optimizer_steps_completed,
    )


# =============================================================================
# Evaluation
# =============================================================================

def evaluate_development(
    M,
    model,
    arrays,
    holdout_idx,
    device,
):
    model.eval()

    if model.training:
        raise RuntimeError(
            "model.eval() did not place model in evaluation mode."
        )

    print("\nSOURCE-NATIVE DEVELOPMENT-DIAGNOSTIC HOLDOUT")

    # M.holdout_metrics is itself @torch.no_grad().
    holdout = M.holdout_metrics(
        model,
        arrays,
        holdout_idx,
        device,
    )

    print(
        f"  MSE     : {holdout['mse']:.12e}"
    )
    print(
        f"  RMSE    : {holdout['rmse']:.12e}"
    )
    print(
        f"  MAE     : {holdout['mae']:.12e}"
    )
    print(
        f"  Max |e| : {holdout['max_abs_error']:.12e}"
    )
    print(
        "  Bounds  :",
        "PASS"
        if holdout[
            "bounds_pass"
        ]
        else "FAIL",
    )

    p1 = M.make_case(
        no=2.0,
        nw=2.0,
        swc=0.20,
        sor=0.20,
        mu_w=0.5,
        mu_o=0.7,
        phi=0.20,
    )

    p2 = M.make_case(
        no=3.0,
        nw=2.0,
        swc=0.15,
        sor=0.25,
        mu_w=6.0,
        mu_o=0.9,
        phi=0.25,
    )

    print("\nSOURCE CASE DIAGNOSTICS")

    cases = {
        "case1_nc0_stage1_nesting":
            M.evaluate_case(
                model,
                p1,
                0.0,
                device,
            ),

        "case1_nc01":
            M.evaluate_case(
                model,
                p1,
                0.10,
                device,
            ),

        "case2_nc0_stage1_nesting":
            M.evaluate_case(
                model,
                p2,
                0.0,
                device,
            ),

        "case2_nc02":
            M.evaluate_case(
                model,
                p2,
                0.20,
                device,
            ),
    }

    for name, case in cases.items():
        print(
            f"  {name:<30} "
            f"R2={case['diagnostics']['r_squared']:.8f} "
            f"max_res={case['diagnostics']['max_abs_residual']:.5e}"
        )

    print("\nNc ACCURACY SWEEP — CASE 1")

    sweep = M.nc_accuracy_sweep(
        model,
        p1,
        device,
    )

    for nc, vals in sweep.items():
        print(
            f"  Nc={nc} "
            f"MAE={vals['mae']:.5e} "
            f"max={vals['max_abs_error']:.5e}"
        )

    model.train()

    if not model.training:
        raise RuntimeError(
            "Model did not return to train() after evaluation."
        )

    return (
        holdout,
        cases,
        sweep,
    )


def case_finite(case):
    return (
        len(
            case[
                "rows"
            ]
        )
        == 15
        and all(
            finite(
                r[
                    "mse"
                ]
            )
            and finite(
                r[
                    "mae"
                ]
            )
            and finite(
                r[
                    "max_abs_err"
                ]
            )
            for r in case[
                "rows"
            ]
        )
        and finite(
            case[
                "diagnostics"
            ][
                "r_squared"
            ]
        )
        and finite(
            case[
                "diagnostics"
            ][
                "max_abs_residual"
            ]
        )
    )


# =============================================================================
# Failure artifact
# =============================================================================

def write_failure(
    exc,
    runner_sha,
    latest_safe_epoch,
    latest_safe_sha,
    optimizer_steps_completed,
):
    payload = {
        "milestone":
            MILESTONE,

        "experiment_id":
            EXPERIMENT_ID,

        "classification":
            "PRODUCTION_RUN_FAILURE_FAIL_CLOSED",

        "runner_sha256":
            runner_sha,

        "exception_type":
            type(
                exc
            ).__name__,

        "exception_message":
            str(
                exc
            ),

        "traceback":
            traceback.format_exc(),

        "latest_safe_completed_epoch":
            latest_safe_epoch,

        "latest_safe_checkpoint_sha256":
            latest_safe_sha,

        "optimizer_steps_completed_in_process":
            optimizer_steps_completed,

        "partial_epoch_accepted":
            False,

        "COMP_XPU_005_complete":
            False,

        "B3_authorized":
            False,

        "OOD_used":
            False,

        "TOF_used":
            False,

        "rerun_instruction":
            "Rerun this exact B2AH command. The runner will restore only the "
            "latest valid completed-epoch COMP-XPU-005 checkpoint.",
    }

    atomic_json_write(
        payload,
        FAILURE,
    )

    return sha256(
        FAILURE
    )


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2AH-XPU")
    print("Authorized COMP-XPU-005 Fresh Corrected Stage-2 Production Runner")
    print("=" * 80)
    print("Experiment:", EXPERIMENT_ID)
    print("B3 remains blocked until post-training Stage-2 scientific closure.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "Completed COMP-XPU-005 summary exists; refusing overwrite/retraining."
        )

    runner_path = Path(
        __file__
    ).resolve()

    runner_sha = sha256(
        runner_path
    )

    gates = authority_gates()

    print("AUTHORITY / PRODUCTION-RUN GATES")

    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    if not all(
        gates.values()
    ):
        failed = [
            k
            for k, v in gates.items()
            if not v
        ]

        raise RuntimeError(
            "B2AH blocked by final authorization mismatch: "
            + ", ".join(
                failed
            )
        )

    if not torch.xpu.is_available():
        raise RuntimeError(
            "Intel XPU unavailable for authorized COMP-XPU-005 run."
        )

    # Import exact certified implementation sources.
    B2S = import_module(
        B2S_SOURCE,
        "v16e1b2s_exact_b2ah",
    )

    B2AC = import_module(
        B2AC_SOURCE,
        "v16e1b2ac_chunk_engine_b2ah",
    )

    if not exact(
        B2S.BASE_RUNNER,
        B2S.BASE_RUNNER_SHA,
    ):
        raise RuntimeError(
            "B2S-bound Stage-2 base-runner SHA mismatch."
        )

    if not exact(
        B2S.B2J_SOURCE,
        B2S.B2J_SOURCE_SHA,
    ):
        raise RuntimeError(
            "B2S-bound eta-model source SHA mismatch."
        )

    # Load frozen dataset.
    d = np.load(
        DATASET
    )

    required_keys = {
        "xi",
        "Sw",
        "p11",
        "tD",
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
            f"Frozen dataset missing required arrays: {sorted(missing)}"
        )

    arrays = (
        d[
            "xi"
        ],
        d[
            "Sw"
        ],
        d[
            "p11"
        ],
        d[
            "tD"
        ],
        d[
            "ai"
        ],
        d[
            "at"
        ],
    )

    if len(
        arrays[
            0
        ]
    ) != N_TOTAL:
        raise RuntimeError(
            f"Frozen dataset profile count {len(arrays[0])}; expected {N_TOTAL}."
        )

    device = torch.device(
        "xpu"
    )

    # Fresh construction ALWAYS happens first. A valid production recovery may
    # then replace this state. No prior experiment checkpoint is ever loaded.
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
    ) = build_fresh_model_optimizer(
        B2S,
        device,
        "production",
    )

    if {
        p.device.type
        for p in model.parameters()
    } != {
        "xpu"
    }:
        raise RuntimeError(
            "Production model is not entirely on Intel XPU."
        )

    # Fresh state must not be the trained COMP-XPU-004 checkpoint.
    fresh_state = cpu_clone(
        model.state_dict()
    )

    comp004_payload = torch.load(
        COMP004_CHECKPOINT,
        map_location="cpu",
        weights_only=False,
    )

    if exact_tree_equal(
        fresh_state,
        cpu_clone(
            comp004_payload[
                "model_state_dict"
            ]
        ),
    ):
        raise RuntimeError(
            "Fresh COMP-XPU-005 model unexpectedly equals COMP-XPU-004 trained state."
        )

    # Deterministic production config. This is written before training and is
    # safe to recreate only if byte-identical.
    config_payload = expected_config(
        runner_sha,
        B2S,
    )

    expected_config_text = json.dumps(
        jsonable(
            config_payload
        ),
        indent=2,
    )

    if CONFIG.exists():
        actual_config_text = CONFIG.read_text(
            encoding="utf-8"
        )

        if actual_config_text != expected_config_text:
            raise RuntimeError(
                "Existing COMP-XPU-005 config differs from this authorized runner."
            )

    else:
        CONFIG.write_text(
            expected_config_text,
            encoding="utf-8",
        )

    config_sha = sha256(
        CONFIG
    )

    print("\nPRODUCTION CONFIG")
    print(
        "  runner SHA-256        :",
        runner_sha,
    )
    print(
        "  config SHA-256        :",
        config_sha,
    )
    print(
        "  derivative engine     :",
        ADOPTED_ENGINE,
    )
    print(
        "  cotangent chunk       :",
        ADOPTED_CHUNK,
    )
    print(
        "  microbatch            :",
        MICROBATCH,
    )
    print(
        "  logical batch         :",
        LOGICAL_BATCH,
    )
    print(
        "  epochs                :",
        TARGET_EPOCHS,
    )
    print(
        "  optimizer             : Adam(lr=1e-3, foreach=False)"
    )

    latest_safe_epoch = None
    latest_safe_sha = None
    optimizer_steps_in_process = 0

    try:
        (
            history,
            train_idx,
            holdout_idx,
            optimizer_steps_completed,
        ) = train_or_resume(
            B2S=B2S,
            B2AC=B2AC,
            M=M,
            model=model,
            optimizer=optimizer,
            arrays=arrays,
            device=device,
            runner_sha=runner_sha,
        )

        optimizer_steps_in_process = (
            optimizer_steps_completed
        )

        if RECOVERY_LATEST.exists():
            latest = read_json(
                RECOVERY_LATEST
            )

            latest_safe_epoch = latest.get(
                "completed_epoch"
            )

            latest_safe_sha = latest.get(
                "checkpoint_sha256"
            )

        # ---------------------------------------------------------------------
        # Completion gates before final archival/evaluation
        # ---------------------------------------------------------------------

        training_gates = {
            "full_800_epochs_completed":
                len(
                    history[
                        "epoch"
                    ]
                )
                == TARGET_EPOCHS,

            "history_last_epoch_800":
                history[
                    "epoch"
                ][-1]
                == TARGET_EPOCHS,

            "optimizer_steps_1600":
                optimizer_steps_completed
                == EXPECTED_TARGET_OPTIMIZER_STEPS,

            "history_last_optimizer_step_1600":
                history[
                    "optimizer_steps_completed"
                ][-1]
                == EXPECTED_TARGET_OPTIMIZER_STEPS,

            "final_model_parameters_finite":
                all_model_parameters_finite(
                    model
                ),

            "latest_recovery_exists":
                RECOVERY_LATEST.exists(),

            "config_SHA_still_exact":
                sha256(
                    CONFIG
                )
                == config_sha,

            "COMP004_checkpoint_still_unchanged":
                sha256(
                    COMP004_CHECKPOINT
                )
                == COMP004_CHECKPOINT_SHA,

            "B2AF_scratch_still_unchanged":
                sha256(
                    B2AF_SCRATCH_CHECKPOINT
                )
                == B2AF_SCRATCH_CHECKPOINT_SHA,

            "no_OOD":
                True,

            "no_TOF":
                True,
        }

        if not all(
            training_gates.values()
        ):
            failed = [
                k
                for k, v in training_gates.items()
                if not v
            ]

            raise RuntimeError(
                "COMP-XPU-005 training completion gate failure: "
                + ", ".join(
                    failed
                )
            )

        # ---------------------------------------------------------------------
        # Write final history and final model checkpoint
        # ---------------------------------------------------------------------

        HISTORY.write_text(
            json.dumps(
                jsonable(
                    history
                ),
                indent=2,
            ),
            encoding="utf-8",
        )

        final_checkpoint_payload = {
            "experiment_id":
                EXPERIMENT_ID,

            "milestone":
                MILESTONE,

            "runner_sha256":
                runner_sha,

            "framework":
                "PyTorch XPU",

            "pytorch_version":
                torch.__version__,

            "fresh_initialization":
                True,

            "seed":
                SEED,

            "sequence_features":
                ["xi", "eta"],

            "conditioning":
                list(
                    getattr(
                        M,
                        "CONDITIONING",
                        [],
                    )
                ),

            "param_dim":
                int(
                    getattr(
                        M,
                        "PARAM_DIM",
                        11,
                    )
                ),

            "hidden":
                int(
                    M.HIDDEN
                ),

            "layers":
                int(
                    M.LAYERS
                ),

            "derivative_engine":
                ADOPTED_ENGINE,

            "cotangent_chunk_size":
                ADOPTED_CHUNK,

            "microbatch":
                MICROBATCH,

            "logical_batch":
                LOGICAL_BATCH,

            "epochs_completed":
                TARGET_EPOCHS,

            "optimizer_steps_completed":
                optimizer_steps_completed,

            "execution_contract_sha256":
                EXECUTION_CONTRACT_SHA,

            "accumulation_contract_sha256":
                ACCUMULATION_CONTRACT_SHA,

            "resume_contract_sha256":
                RESUME_CONTRACT_SHA,

            "B2AG_authorization_sha256":
                B2AG_AUTHORIZATION_SHA,

            "B2AG_runner_contract_sha256":
                B2AG_RUNNER_CONTRACT_SHA,

            "dataset_sha256":
                DATASET_SHA,

            "source_sha256_map":
                source_sha_map(
                    runner_sha,
                    B2S,
                ),

            "model_state_dict":
                cpu_clone(
                    model.state_dict()
                ),

            "OOD_used":
                False,

            "TOF_used":
                False,
        }

        atomic_torch_save(
            final_checkpoint_payload,
            CHECKPOINT,
        )

        history_sha = sha256(
            HISTORY
        )

        checkpoint_sha = sha256(
            CHECKPOINT
        )

        # ---------------------------------------------------------------------
        # Development evaluation
        # ---------------------------------------------------------------------

        (
            holdout,
            cases,
            sweep,
        ) = evaluate_development(
            M=M,
            model=model,
            arrays=arrays,
            holdout_idx=holdout_idx,
            device=device,
        )

        eval_gates = {
            "model_returned_to_train_after_eval":
                model.training
                is True,

            "holdout_predictions_finite":
                holdout[
                    "finite_predictions"
                ],

            "holdout_bounds_pass":
                holdout[
                    "bounds_pass"
                ],

            "holdout_metrics_finite":
                all(
                    finite(
                        holdout[
                            k
                        ]
                    )
                    for k in (
                        "mse",
                        "rmse",
                        "mae",
                        "max_abs_error",
                    )
                ),

            "all_four_source_cases_finite":
                all(
                    case_finite(
                        c
                    )
                    for c in cases.values()
                ),

            "Nc_sweep_all_finite":
                all(
                    finite(
                        vals[
                            "mae"
                        ]
                    )
                    and finite(
                        vals[
                            "max_abs_error"
                        ]
                    )
                    for vals in sweep.values()
                ),

            "Stage1_nesting_Nc0_evaluated":
                (
                    "case1_nc0_stage1_nesting"
                    in cases
                    and
                    "case2_nc0_stage1_nesting"
                    in cases
                ),

            "development_holdout_not_OOD":
                True,

            "no_TOF":
                True,

            "no_numeric_threshold_invented":
                True,
        }

        metrics = {
            "milestone":
                MILESTONE,

            "experiment_id":
                EXPERIMENT_ID,

            "classification":
                "AUTHORIZED_CORRECTED_CONSERVATIVE_STAGE2_PRODUCTION_REPRODUCTION",

            "training":
                {
                    "fresh_initialization":
                        True,

                    "epochs_completed":
                        len(
                            history[
                                "epoch"
                            ]
                        ),

                    "optimizer_steps_completed":
                        optimizer_steps_completed,

                    "logical_batch":
                        LOGICAL_BATCH,

                    "microbatch":
                        MICROBATCH,

                    "derivative_engine":
                        ADOPTED_ENGINE,

                    "cotangent_chunk_size":
                        ADOPTED_CHUNK,

                    "final_losses":
                        {
                            k:
                                history[
                                    k
                                ][-1]
                            for k in (
                                "data",
                                "physics",
                                "bc_inj",
                                "bc_tip",
                                "anchor",
                                "mono",
                                "total",
                            )
                        },

                    "mean_epoch_seconds":
                        float(
                            np.mean(
                                history[
                                    "epoch_seconds"
                                ]
                            )
                        ),

                    "median_epoch_seconds":
                        float(
                            np.median(
                                history[
                                    "epoch_seconds"
                                ]
                            )
                        ),
                },

            "holdout":
                holdout,

            "source_cases":
                cases,

            "Nc_accuracy_sweep_case1":
                sweep,

            "evaluation_semantics":
                "source-native development diagnostic; NOT OOD",

            "threshold_policy":
                "No numerical scientific acceptance threshold invented or applied.",

            "OOD_used":
                False,

            "TOF_used":
                False,
        }

        METRICS.write_text(
            json.dumps(
                jsonable(
                    metrics
                ),
                indent=2,
            ),
            encoding="utf-8",
        )

        metrics_sha = sha256(
            METRICS
        )

        manifest = {
            "milestone":
                MILESTONE,

            "experiment_id":
                EXPERIMENT_ID,

            "classification":
                "PROVENANCE_BOUND_CORRECTED_STAGE2_PRODUCTION_ARTIFACT_MANIFEST",

            "authorization":
                {
                    "B2AG_source_sha256":
                        B2AG_SOURCE_SHA,

                    "B2AG_interpretation_sha256":
                        B2AG_INTERPRETATION_SHA,

                    "B2AG_authorization_sha256":
                        B2AG_AUTHORIZATION_SHA,

                    "B2AG_runner_contract_sha256":
                        B2AG_RUNNER_CONTRACT_SHA,

                    "B2AG_summary_sha256":
                        B2AG_SUMMARY_SHA,
                },

            "contracts":
                {
                    "execution_contract_sha256":
                        EXECUTION_CONTRACT_SHA,

                    "accumulation_contract_sha256":
                        ACCUMULATION_CONTRACT_SHA,

                    "resume_contract_sha256":
                        RESUME_CONTRACT_SHA,
                },

            "sources":
                source_sha_map(
                    runner_sha,
                    B2S,
                ),

            "immutable_evidence":
                {
                    "COMP004_checkpoint_sha256":
                        COMP004_CHECKPOINT_SHA,

                    "B2AF_results_sha256":
                        B2AF_RESULTS_SHA,

                    "B2AF_scratch_checkpoint_sha256":
                        B2AF_SCRATCH_CHECKPOINT_SHA,

                    "B2AF_summary_sha256":
                        B2AF_SUMMARY_SHA,
                },

            "artifacts":
                {
                    "dataset":
                        {
                            "path":
                                rel(
                                    DATASET
                                ),

                            "sha256":
                                DATASET_SHA,
                        },

                    "config":
                        {
                            "path":
                                rel(
                                    CONFIG
                                ),

                            "sha256":
                                config_sha,
                        },

                    "history":
                        {
                            "path":
                                rel(
                                    HISTORY
                                ),

                            "sha256":
                                history_sha,
                        },

                    "checkpoint":
                        {
                            "path":
                                rel(
                                    CHECKPOINT
                                ),

                            "sha256":
                                checkpoint_sha,
                        },

                    "metrics":
                        {
                            "path":
                                rel(
                                    METRICS
                                ),

                            "sha256":
                                metrics_sha,
                        },
                },

            "completion":
                {
                    "epochs":
                        TARGET_EPOCHS,

                    "optimizer_steps":
                        optimizer_steps_completed,

                    "fresh_initialization":
                        True,

                    "B2AF_scratch_used_as_initializer":
                        False,

                    "COMP004_used_as_initializer":
                        False,

                    "OOD":
                        False,

                    "TOF":
                        False,
                },
        }

        MANIFEST.write_text(
            json.dumps(
                jsonable(
                    manifest
                ),
                indent=2,
            ),
            encoding="utf-8",
        )

        manifest_sha = sha256(
            MANIFEST
        )

        final_gates = {
            **gates,
            **training_gates,
            **eval_gates,

            "config_written":
                CONFIG.exists()
                and CONFIG.stat().st_size
                > 0,

            "history_written":
                HISTORY.exists()
                and HISTORY.stat().st_size
                > 0,

            "checkpoint_written":
                CHECKPOINT.exists()
                and CHECKPOINT.stat().st_size
                > 0,

            "metrics_written":
                METRICS.exists()
                and METRICS.stat().st_size
                > 0,

            "manifest_written":
                MANIFEST.exists()
                and MANIFEST.stat().st_size
                > 0,

            "manifest_config_SHA_exact":
                read_json(
                    MANIFEST
                )[
                    "artifacts"
                ][
                    "config"
                ][
                    "sha256"
                ]
                == sha256(
                    CONFIG
                ),

            "manifest_history_SHA_exact":
                read_json(
                    MANIFEST
                )[
                    "artifacts"
                ][
                    "history"
                ][
                    "sha256"
                ]
                == sha256(
                    HISTORY
                ),

            "manifest_checkpoint_SHA_exact":
                read_json(
                    MANIFEST
                )[
                    "artifacts"
                ][
                    "checkpoint"
                ][
                    "sha256"
                ]
                == sha256(
                    CHECKPOINT
                ),

            "manifest_metrics_SHA_exact":
                read_json(
                    MANIFEST
                )[
                    "artifacts"
                ][
                    "metrics"
                ][
                    "sha256"
                ]
                == sha256(
                    METRICS
                ),

            "COMP004_checkpoint_unchanged_final":
                sha256(
                    COMP004_CHECKPOINT
                )
                == COMP004_CHECKPOINT_SHA,

            "B2AF_scratch_unchanged_final":
                sha256(
                    B2AF_SCRATCH_CHECKPOINT
                )
                == B2AF_SCRATCH_CHECKPOINT_SHA,

            "B3_not_authorized":
                True,
        }

        ok = all(
            bool(
                v
            )
            for v in final_gates.values()
        )

        status = (
            "V16E1B2AH_XPU_COMP_XPU_005_AUTHORIZED_FRESH_CORRECTED_STAGE2_PRODUCTION_RUN_COMPLETE_"
            "FRESH_SEED_1337_INITIALIZATION_CHUNKED_BATCHED_VJP_CHUNK16_MICROBATCH128_LOGICAL8192_"
            "EIGHT_HUNDRED_COMPLETED_EPOCHS_NINETY_MICROBATCHES_PER_EPOCH_TWO_ADAM_STEPS_PER_EPOCH_"
            "ONE_THOUSAND_SIX_HUNDRED_TOTAL_OPTIMIZER_STEPS_ATOMIC_COMPLETED_EPOCH_RECOVERY_CONTRACT_SATISFIED_"
            "FINAL_CHECKPOINT_HISTORY_CONFIG_METRICS_AND_MANIFEST_SHA_BOUND_"
            "DEVELOPMENT_HOLDOUT_AND_SOURCE_DIAGNOSTICS_FINITE_SATURATION_BOUNDS_PASS_"
            "B2AF_SCRATCH_AND_COMP_XPU_004_NEVER_USED_AS_PRODUCTION_INITIALIZERS_"
            "NO_OOD_NO_TOF_B2AI_STAGE2_SCIENTIFIC_CLOSURE_REQUIRED_B3_NOT_AUTHORIZED"
            if ok else
            "V16E1B2AH_XPU_COMP_XPU_005_COMPLETED_WITH_GATE_FAILURE"
        )

        summary_payload = {
            "milestone":
                MILESTONE,

            "experiment_id":
                EXPERIMENT_ID,

            "status":
                status,

            "runner_sha256":
                runner_sha,

            "dataset_sha256":
                DATASET_SHA,

            "config_sha256":
                sha256(
                    CONFIG
                ),

            "history_sha256":
                sha256(
                    HISTORY
                ),

            "checkpoint_sha256":
                sha256(
                    CHECKPOINT
                ),

            "metrics_sha256":
                sha256(
                    METRICS
                ),

            "manifest_sha256":
                manifest_sha,

            "epochs_completed":
                len(
                    history[
                        "epoch"
                    ]
                ),

            "optimizer_steps_completed":
                optimizer_steps_completed,

            "fresh_initialization":
                True,

            "B2AF_scratch_used_as_initializer":
                False,

            "COMP004_used_as_initializer":
                False,

            "holdout_mse":
                holdout[
                    "mse"
                ],

            "holdout_rmse":
                holdout[
                    "rmse"
                ],

            "holdout_mae":
                holdout[
                    "mae"
                ],

            "holdout_max_abs_error":
                holdout[
                    "max_abs_error"
                ],

            "holdout_bounds_pass":
                holdout[
                    "bounds_pass"
                ],

            "B3_authorized":
                False,

            "Stage2_scientific_closure_required":
                True,

            "next_milestone":
                (
                    "V16E-1B2AI-XPU — compare corrected COMP-XPU-005 against "
                    "the frozen Stage-2 source-faithful and best-accuracy branches, "
                    "including overall and per-Nc development holdout, source-case "
                    "full/front-excluded/front-position behavior, corrected physics "
                    "objective diagnostics, and close Stage-2 before B3"
                    if ok else
                    "V16E-1B2AH-R1 — diagnose failed completion gate without "
                    "changing certified upstream science or production contracts"
                ),

            "gates":
                {
                    k:
                        bool(
                            v
                        )
                    for k, v in final_gates.items()
                },
        }

        SUMMARY.write_text(
            json.dumps(
                jsonable(
                    summary_payload
                ),
                indent=2,
            ),
            encoding="utf-8",
        )

        print("\nFINAL GATES")

        for k, v in final_gates.items():
            print(
                "[PASS]" if v else "[FAIL]",
                k,
            )

        print("\nSTATUS")
        print(
            " ",
            status,
        )

        print("\nARTIFACT HASHES")
        print(
            "  Runner    :",
            runner_sha,
        )
        print(
            "  Dataset   :",
            DATASET_SHA,
        )
        print(
            "  Config    :",
            sha256(
                CONFIG
            ),
        )
        print(
            "  History   :",
            sha256(
                HISTORY
            ),
        )
        print(
            "  Checkpoint:",
            sha256(
                CHECKPOINT
            ),
        )
        print(
            "  Metrics   :",
            sha256(
                METRICS
            ),
        )
        print(
            "  Manifest  :",
            sha256(
                MANIFEST
            ),
        )
        print(
            "  Summary   :",
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
        # Determine latest certified completed epoch from pointer, if any.
        if RECOVERY_LATEST.exists():
            try:
                latest = read_json(
                    RECOVERY_LATEST
                )

                latest_safe_epoch = latest.get(
                    "completed_epoch"
                )

                latest_safe_sha = latest.get(
                    "checkpoint_sha256"
                )
            except Exception:
                pass

        failure_sha = write_failure(
            exc=exc,
            runner_sha=runner_sha,
            latest_safe_epoch=latest_safe_epoch,
            latest_safe_sha=latest_safe_sha,
            optimizer_steps_completed=optimizer_steps_in_process,
        )

        print("\n" + "=" * 80)
        print("COMP-XPU-005 PRODUCTION RUN FAILED CLOSED")
        print("=" * 80)
        print(
            "Failure:",
            f"{type(exc).__name__}: {exc}",
        )
        print(
            "Latest safe completed epoch:",
            latest_safe_epoch,
        )
        print(
            "Latest safe checkpoint SHA :",
            latest_safe_sha,
        )
        print(
            "Failure artifact SHA       :",
            failure_sha,
        )
        print()
        print(
            "No partial epoch has been accepted."
        )
        print(
            "Rerun this SAME B2AH command to resume from the latest "
            "valid completed-epoch COMP-XPU-005 checkpoint."
        )
        print(
            "B2AF scratch and COMP-XPU-004 remain prohibited as resume sources."
        )

        # Preserve KeyboardInterrupt semantics while still writing the failure.
        if isinstance(
            exc,
            KeyboardInterrupt,
        ):
            raise SystemExit(
                130
            )

        raise SystemExit(
            75
        )


if __name__ == "__main__":
    main()
