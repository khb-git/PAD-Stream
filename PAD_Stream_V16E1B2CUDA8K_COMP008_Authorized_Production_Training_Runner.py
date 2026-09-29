#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import math
import os
import random
import time

import numpy as np
import torch
import torch.nn.functional as F


# =============================================================================
# PAD-Stream V16E-1B2CUDA8K
#
# COMP008 Authorized Production Training Runner
#
# EXECUTION ONLY.
#
# AUTHORITY
# ---------
# Executes ONLY the frozen CUDA8J COMP008 science/training contract.
#
# NO architecture changes.
# NO loss changes.
# NO hyperparameter changes.
# NO DEV inspection.
# NO original holdout evaluation.
# NO blind CERT scientific inspection.
# NO OOD.
# NO TOF.
# NO early stopping.
# NO checkpoint selection.
# B3 remains blocked until CUDA8L blind certification.
#
# Recovery authority:
#   only a successfully completed epoch is resumable authority.
#
# Final production authority:
#   completed epoch 800 only.
# =============================================================================


MILESTONE = "V16E-1B2CUDA8K"
EXPERIMENT = "V16E-BLREP-COMP-CUDA-008"


STATUS_RUNNING = (
    "V16E1B2CUDA8K_COMP008_AUTHORIZED_PRODUCTION_TRAINING_RUNNING_"
    "CUDA8J_CONTRACT_BOUND_BOUNDED_MONOTONE_EXACT_COMP007_INIT_"
    "FRESH_ADAM_LR1E4_800EPOCH_1600STEP_K64_MB1024_"
    "EQUAL_NC_CORRECTED_PHYSICS_SMOOTH_INLET_WEIGHT_ALPHA3_XI016_"
    "NO_BC_TIP_ANCHOR_MONO_BOUNDS_PENALTIES_"
    "HOLDOUT_DEV_CERT_FORBIDDEN_NO_OOD_NO_TOF_B3_BLOCKED"
)


STATUS_COMPLETE = (
    "V16E1B2CUDA8K_COMP008_AUTHORIZED_PRODUCTION_TRAINING_COMPLETE_"
    "CUDA8J_CONTRACT_SATISFIED_BOUNDED_MONOTONE_EXACT_COMP007_INIT_"
    "FRESH_ADAM_LR1E4_800_EPOCHS_1600_OPTIMIZER_STEPS_COMPLETE_"
    "EQUAL_NC_CORRECTED_PHYSICS_SMOOTH_INLET_WEIGHT_ALPHA3_XI016_"
    "FINAL_EPOCH_800_AUTHORITY_NO_HOLDOUT_DEV_CERT_EVALUATION_"
    "NO_OOD_NO_TOF_STAGE2_BLIND_CERTIFICATION_REQUIRED_B3_BLOCKED"
)


# =============================================================================
# Paths
# =============================================================================

REPO = Path("/content/PAD-Stream")
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")


# Frozen Stage-2 training data.
DATASET = (
    DRIVE
    / "datasets"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)


# Split authority from COMP005.
RUN005 = (
    DRIVE
    / "runs"
    / "V16E-BLREP-COMP-CUDA-005"
)

RECOVERY005_E0800 = (
    RUN005
    / "recovery"
    / "V16E_BLREP_COMP_CUDA_005_RECOVERY_E0800.pt"
)


# Exact COMP007 initialization.
RUN007 = (
    DRIVE
    / "runs"
    / "V16E-BLREP-COMP-CUDA-007"
)

COMP007 = (
    RUN007
    / "V16E_BLREP_COMP_CUDA_007.pt"
)


# Frozen equal-Nc normalization authority.
CUDA8BR_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8BR_COMP006_REPAIR_IMPLEMENTATION_PREFLIGHT"
)

CUDA8BR_NORMALIZATION = (
    CUDA8BR_ROOT
    / "V16E1B2CUDA8BR_COMP005_TrainingSplit_Nc_Physics_Normalization.json"
)


# CUDA6 is the source authority used to resolve B2S/M/J/CUDA3.
CUDA6 = (
    REPO
    / "PAD_Stream_V16E1B2CUDA6_A100_COMP_CUDA_005_Authorized_Production_Runner.py"
)


# CUDA8J final development freeze.
CUDA8J_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8J_Final_Stage2_Development_Decision_and_COMP008_Training_Contract_Freeze.py"
)

CUDA8J_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_redesign"
    / "V16E1B2CUDA8J_FINAL_STAGE2_DEVELOPMENT_CONTRACT_FREEZE"
)

CUDA8J_ARCHITECTURE = (
    CUDA8J_ROOT
    / "V16E1B2CUDA8J_COMP008_Architecture_Contract.json"
)

CUDA8J_LOSS = (
    CUDA8J_ROOT
    / "V16E1B2CUDA8J_COMP008_Loss_and_Physics_Contract.json"
)

CUDA8J_TRAINING = (
    CUDA8J_ROOT
    / "V16E1B2CUDA8J_COMP008_Production_Training_Contract.json"
)

CUDA8J_CERTIFICATION = (
    CUDA8J_ROOT
    / "V16E1B2CUDA8J_Stage2_Blind_Certification_Contract.json"
)

CUDA8J_DECISION = (
    CUDA8J_ROOT
    / "V16E1B2CUDA8J_Final_Development_Decision.json"
)

CUDA8J_SUMMARY = (
    CUDA8J_ROOT
    / "PAD_Stream_V16E1B2CUDA8J_Summary.json"
)

CUDA8J_HANDOFF = (
    CUDA8J_ROOT
    / "V16E1B2CUDA8J_Handoff.md"
)


# Firewall artifacts. These are HASHED ONLY. They are never loaded.
DEV_DATASET = (
    DRIVE
    / "datasets"
    / "stage2_redesign"
    / "V16E_STAGE2_DEV_GODUNOV_SEED20260918.npz"
)

BLIND_CERT = (
    DRIVE
    / "datasets"
    / "stage2_redesign"
    / "sealed_certification"
    / "V16E_STAGE2_BLIND_CERT_GODUNOV_SEED20260919.npz"
)

BLIND_CERT_SEAL = (
    DRIVE
    / "datasets"
    / "stage2_redesign"
    / "sealed_certification"
    / "V16E_STAGE2_BLIND_CERT_SEALED.json"
)


# Persistent COMP008 run root.
RUN_ROOT = (
    DRIVE
    / "runs"
    / EXPERIMENT
)

RECOVERY_DIR = (
    RUN_ROOT
    / "recovery"
)

RECOVERY_LATEST = (
    RECOVERY_DIR
    / "V16E_BLREP_COMP_CUDA_008_RECOVERY_LATEST.json"
)

CONFIG = (
    RUN_ROOT
    / "V16E_BLREP_COMP_CUDA_008_CONFIG.json"
)

HISTORY = (
    RUN_ROOT
    / "V16E_BLREP_COMP_CUDA_008_HISTORY.json"
)

FINAL_CHECKPOINT = (
    RUN_ROOT
    / "V16E_BLREP_COMP_CUDA_008.pt"
)

MANIFEST = (
    RUN_ROOT
    / "V16E_BLREP_COMP_CUDA_008_MANIFEST.json"
)

SUMMARY = (
    RUN_ROOT
    / "PAD_Stream_V16E1B2CUDA8K_Summary.json"
)

HANDOFF = (
    RUN_ROOT
    / "V16E1B2CUDA8K_Handoff.md"
)


RUN_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

RECOVERY_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# Frozen hashes
# =============================================================================

EXPECTED = {
    "dataset":
        "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c",

    "RECOVERY005_E0800":
        "fbdbf6b7bff0b22625e7dbcd09500c258c6deeeec6ed4f846407f6e927435157",

    "COMP007":
        "98521407ab803b4899a75988c65f303f94e9447dd25e159e7cc3ffdb7e9c042d",

    "COMP007_STATE":
        "e89ccd3a1f0b44fb95d96135bbab17149ef5f0fafd9fc1002d37110884505f60",

    "CUDA8BR_NORMALIZATION":
        "ccd0e61fc8fc8f73890e83f537bb047aaa5f408c8f4125209cc36d0b79df3549",

    "CUDA6":
        "385e18b64ebf068a06e5daec11449e3700f69ad743627d4520905f273bf7c552",

    "CUDA8J_SOURCE":
        "cccf266b6b1e84047e233823da8100d14d61ce400931b169dc365fa680c11187",

    "CUDA8J_ARCHITECTURE":
        "4cae0a004c445f589aae040c340f026ddf285eff07ac67ac42e9710ba2034ab5",

    "CUDA8J_LOSS":
        "b5745fa551c25c0713051adc90125382485df0d907301d2db99577bf5763d931",

    "CUDA8J_TRAINING":
        "9a195b03f303eca78471c9b9d5df653468e48fa90758158da604bfb149229a6e",

    "CUDA8J_CERTIFICATION":
        "71abcc4a28dac85798d7673d3a16825303d327f7d85ae2473e17f658b354534d",

    "CUDA8J_DECISION":
        "b1f31f32591dc75950ddad9c2aed24b0fd92f9d5828075fa59649a1d86c71fc0",

    "CUDA8J_SUMMARY":
        "57465a49d5e24f206f14f36e4f583e948ab8588b6b4cb0435603fb26ace23332",

    "CUDA8J_HANDOFF":
        "290369361c985a47a7e221dd8a7e5c1742f89b636adcc2e90a4b7b0bdcbc6d0b",

    "DEV_DATASET":
        "55e5fe6868d78c930192af3af59d931275a83aa1f3ca46595969429718063821",

    "BLIND_CERT":
        "0eaf3fc1a6be77b2b804baf54e03837346754a411b92e5b1b19f83f3d8ddf265",

    "BLIND_CERT_SEAL":
        "7dd0bdd24c05e8d0265f77030247da3739b00eeca41af8c9495c22eaddc1c1ae",

    "B2S":
        "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea",

    "BASE_M":
        "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18",

    "ETA_J":
        "fcc4074863a46f6b8d356a01ff0b4b2182d0ffa3ebc9b3fd053e35282f897a4c",

    "CUDA3":
        "1065788f8f82d7f58aba873b8396cf70a17906571421315151640a0c879df886",

    "train_idx":
        "c3d1d9080af67a8ecfa018d3f757dac1fd9f19f7977f2cdf25622d613c7195b8",

    "holdout_idx":
        "4b64a27875ebe04f96d717f0e9eab43017a5325c352b5c4233284adafa308613",
}


# =============================================================================
# Exact CUDA8J COMP008 production contract
# =============================================================================

SEED = 1337

NC_VALUES = (
    0.00,
    0.05,
    0.10,
    0.20,
    0.30,
)

NC_COUNT = len(
    NC_VALUES
)

N_TOTAL = 14400
N_TRAIN = 11520
N_HOLDOUT = 2880

TARGET_EPOCHS = 800

LR = 1.0e-4

ADOPTED_CHUNK = 64
MICROBATCH = 1024
LOGICAL_BATCH = 8192
SECOND_LOGICAL_CHUNK = 3328

EXPECTED_MICROBATCHES_PER_EPOCH = 12
EXPECTED_OPTIMIZER_STEPS_PER_EPOCH = 2
EXPECTED_TARGET_OPTIMIZER_STEPS = 1600

LAMBDA_DATA = 1.0
LAMBDA_PHYS = 8.537526059395e-04

INLET_ALPHA = 3.0
INLET_XI0 = 0.16

STRUCT_TOL = 1.0e-6


# =============================================================================
# Helpers
# =============================================================================

def sha256(
    path: Path,
) -> str:

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        for block in iter(
            lambda: f.read(
                1024
                *
                1024
            ),
            b"",
        ):
            h.update(
                block
            )

    return h.hexdigest()


def array_sha256(
    x,
) -> str:

    a = np.ascontiguousarray(
        np.asarray(
            x,
            dtype=np.int64,
        )
    )

    return hashlib.sha256(
        a.tobytes(
            order="C"
        )
    ).hexdigest()


def state_tensor_hash(
    state,
) -> str:

    h = hashlib.sha256()

    for name in sorted(
        state.keys()
    ):

        t = (
            state[
                name
            ]
            .detach()
            .cpu()
            .contiguous()
        )

        h.update(
            name.encode(
                "utf-8"
            )
        )

        h.update(
            str(
                t.dtype
            ).encode(
                "utf-8"
            )
        )

        h.update(
            str(
                tuple(
                    t.shape
                )
            ).encode(
                "utf-8"
            )
        )

        h.update(
            t.numpy()
            .tobytes()
        )

    return h.hexdigest()


def gate(
    name,
    condition,
):

    ok = bool(
        condition
    )

    print(
        f"[{'PASS' if ok else 'FAIL'}] {name}"
    )

    if not ok:
        raise RuntimeError(
            f"CUDA8K gate failed: {name}"
        )


def finite_tensor(
    x,
) -> bool:

    return bool(
        torch.isfinite(
            x
        )
        .all()
        .item()
    )


def model_finite(
    model,
) -> bool:

    return all(
        finite_tensor(
            p
        )
        for p
        in model.parameters()
    )


def native_nc_mask_torch(
    values,
    nc,
):

    target = torch.as_tensor(
        nc,
        dtype=values.dtype,
        device=values.device,
    )

    return (
        values
        ==
        target
    )


def jsonable(
    obj,
):

    if isinstance(
        obj,
        dict,
    ):

        return {
            str(
                k
            ):
                jsonable(
                    v
                )
            for k, v
            in obj.items()
        }

    if isinstance(
        obj,
        (
            list,
            tuple,
        ),
    ):

        return [
            jsonable(
                v
            )
            for v
            in obj
        ]

    if isinstance(
        obj,
        np.ndarray,
    ):

        return jsonable(
            obj.tolist()
        )

    if isinstance(
        obj,
        np.generic,
    ):

        return jsonable(
            obj.item()
        )

    if isinstance(
        obj,
        torch.Tensor,
    ):

        return jsonable(
            obj.detach()
            .cpu()
            .numpy()
        )

    if isinstance(
        obj,
        float,
    ):

        if not math.isfinite(
            obj
        ):

            raise ValueError(
                "Refusing to serialize non-finite float."
            )

    return obj


def write_json_atomic(
    path: Path,
    obj,
):

    tmp = path.with_suffix(
        path.suffix
        +
        ".tmp"
    )

    tmp.write_text(
        json.dumps(
            jsonable(
                obj
            ),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        +
        "\n",
        encoding="utf-8",
    )

    os.replace(
        tmp,
        path,
    )


def torch_save_atomic(
    path: Path,
    obj,
):

    tmp = path.with_suffix(
        path.suffix
        +
        ".tmp"
    )

    torch.save(
        obj,
        tmp,
    )

    os.replace(
        tmp,
        path,
    )


def sync_cuda():

    torch.cuda.synchronize()


def empty_history():

    return {
        "epoch":
            [],

        "data":
            [],

        "physics":
            [],

        "total":
            [],

        "epoch_seconds":
            [],

        "optimizer_steps_completed":
            [],

        "peak_allocated_GiB":
            [],
    }


def validate_history(
    history,
    completed_epoch,
    optimizer_steps_completed,
):

    required = {
        "epoch",
        "data",
        "physics",
        "total",
        "epoch_seconds",
        "optimizer_steps_completed",
        "peak_allocated_GiB",
    }

    if set(
        history.keys()
    ) != required:

        raise RuntimeError(
            "Recovery history keys do not match CUDA8K contract."
        )

    n = len(
        history[
            "epoch"
        ]
    )

    if n != completed_epoch:

        raise RuntimeError(
            "Recovery history length does not equal completed epoch."
        )

    for key in required:

        if len(
            history[
                key
            ]
        ) != n:

            raise RuntimeError(
                f"Recovery history length mismatch for {key}."
            )

    if completed_epoch > 0:

        if (
            history[
                "epoch"
            ][
                -1
            ]
            !=
            completed_epoch
        ):

            raise RuntimeError(
                "Recovery history final epoch is inconsistent."
            )

        if (
            history[
                "optimizer_steps_completed"
            ][
                -1
            ]
            !=
            optimizer_steps_completed
        ):

            raise RuntimeError(
                "Recovery history optimizer-step count is inconsistent."
            )


def import_by_path(
    name,
    path,
):

    spec = (
        importlib.util
        .spec_from_file_location(
            name,
            path,
        )
    )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        module
    )

    return module


# =============================================================================
# Banner
# =============================================================================

print(
    "="
    *
    110
)

print(
    "PAD-Stream V16E-1B2CUDA8K"
)

print(
    "COMP008 Authorized Production Training Runner"
)

print(
    "="
    *
    110
)

print()

print(
    "EXECUTION ONLY UNDER FROZEN CUDA8J CONTRACT."
)

print(
    "NO DEVELOPMENT CHANGES AUTHORIZED."
)

print(
    "ORIGINAL HOLDOUT EVALUATION: FORBIDDEN."
)

print(
    "DEV USE DURING PRODUCTION: FORBIDDEN."
)

print(
    "BLIND CERT SCIENTIFIC INSPECTION: FORBIDDEN."
)

print(
    "NO OOD."
)

print(
    "NO TOF."
)

print(
    "B3 REMAINS BLOCKED."
)

print()


# =============================================================================
# Frozen authority gates
# =============================================================================

AUTHORITY = {
    "dataset":
        DATASET,

    "RECOVERY005_E0800":
        RECOVERY005_E0800,

    "COMP007":
        COMP007,

    "CUDA8BR_NORMALIZATION":
        CUDA8BR_NORMALIZATION,

    "CUDA6":
        CUDA6,

    "CUDA8J_SOURCE":
        CUDA8J_SOURCE,

    "CUDA8J_ARCHITECTURE":
        CUDA8J_ARCHITECTURE,

    "CUDA8J_LOSS":
        CUDA8J_LOSS,

    "CUDA8J_TRAINING":
        CUDA8J_TRAINING,

    "CUDA8J_CERTIFICATION":
        CUDA8J_CERTIFICATION,

    "CUDA8J_DECISION":
        CUDA8J_DECISION,

    "CUDA8J_SUMMARY":
        CUDA8J_SUMMARY,

    "CUDA8J_HANDOFF":
        CUDA8J_HANDOFF,

    "DEV_DATASET":
        DEV_DATASET,

    "BLIND_CERT":
        BLIND_CERT,

    "BLIND_CERT_SEAL":
        BLIND_CERT_SEAL,
}


print(
    "FROZEN AUTHORITY GATES"
)

for name, path in (
    AUTHORITY.items()
):

    gate(
        f"{name}_exists",
        path.exists(),
    )

    gate(
        f"{name}_SHA_exact",
        sha256(
            path
        )
        ==
        EXPECTED[
            name
        ],
    )


# IMPORTANT:
# DEV_DATASET and BLIND_CERT are only byte-hashed above.
# They are never loaded by this runner.


# =============================================================================
# CUDA8J contract gates
# =============================================================================

arch_contract = json.loads(
    CUDA8J_ARCHITECTURE.read_text(
        encoding="utf-8"
    )
)

loss_contract = json.loads(
    CUDA8J_LOSS.read_text(
        encoding="utf-8"
    )
)

training_contract = json.loads(
    CUDA8J_TRAINING.read_text(
        encoding="utf-8"
    )
)

cert_contract = json.loads(
    CUDA8J_CERTIFICATION.read_text(
        encoding="utf-8"
    )
)

decision = json.loads(
    CUDA8J_DECISION.read_text(
        encoding="utf-8"
    )
)


print()
print(
    "CUDA8J CONTRACT GATES"
)


gate(
    "experiment_exact_COMP008",
    decision[
        "experiment"
    ]
    ==
    EXPERIMENT,
)

gate(
    "development_cycle_closed",
    decision[
        "development_cycle_closed"
    ]
    is True,
)

gate(
    "production_training_authorized",
    decision[
        "COMP008_production_training_authorized"
    ]
    is True,
)

gate(
    "exact_CUDA8J_contract_required",
    decision[
        "COMP008_training_must_follow_exact_CUDA8J_contract"
    ]
    is True,
)

gate(
    "no_further_adjustments_authorized",
    decision[
        "further_current_cycle_architecture_loss_hyperparameter_adjustment_authorized"
    ]
    is False,
)

gate(
    "Stage2_not_yet_certified",
    decision[
        "Stage2_certified"
    ]
    is False,
)

gate(
    "B3_not_yet_authorized",
    decision[
        "B3_authorized"
    ]
    is False,
)

gate(
    "blind_CERT_not_opened",
    decision[
        "blind_CERT_scientifically_opened"
    ]
    is False,
)


gate(
    "architecture_final_frozen",
    arch_contract[
        "development_status"
    ]
    ==
    "FINAL_FROZEN",
)

gate(
    "architecture_exact_COMP007_init",
    arch_contract[
        "initialization"
    ][
        "model_weights"
    ]
    ==
    "EXACT_FROZEN_COMP007",
)

gate(
    "architecture_hidden64",
    int(
        arch_contract[
            "trunk"
        ][
            "LSTM_hidden"
        ]
    )
    ==
    64,
)

gate(
    "architecture_layers2",
    int(
        arch_contract[
            "trunk"
        ][
            "LSTM_layers"
        ]
    )
    ==
    2,
)

gate(
    "architecture_epsilon_1e8",
    math.isclose(
        float(
            arch_contract[
                "bounded_monotone_output"
            ][
                "epsilon"
            ]
        ),
        1.0e-8,
        rel_tol=0.0,
        abs_tol=1.0e-20,
    ),
)


gate(
    "loss_data_enabled",
    loss_contract[
        "data_loss"
    ][
        "enabled"
    ]
    is True,
)

gate(
    "loss_lambda_data_exact",
    float(
        loss_contract[
            "data_loss"
        ][
            "lambda"
        ]
    )
    ==
    LAMBDA_DATA,
)

gate(
    "loss_physics_enabled",
    loss_contract[
        "corrected_conservative_physics"
    ][
        "enabled"
    ]
    is True,
)

gate(
    "loss_lambda_physics_exact",
    float(
        loss_contract[
            "corrected_conservative_physics"
        ][
            "lambda"
        ]
    )
    ==
    LAMBDA_PHYS,
)

gate(
    "inlet_weight_enabled",
    loss_contract[
        "inlet_spatial_physics_weight"
    ][
        "enabled"
    ]
    is True,
)

gate(
    "inlet_weight_not_Nc_specific",
    loss_contract[
        "inlet_spatial_physics_weight"
    ][
        "Nc_specific"
    ]
    is False,
)

gate(
    "inlet_alpha_exact_3",
    float(
        loss_contract[
            "inlet_spatial_physics_weight"
        ][
            "alpha"
        ]
    )
    ==
    INLET_ALPHA,
)

gate(
    "inlet_xi0_exact_016",
    float(
        loss_contract[
            "inlet_spatial_physics_weight"
        ][
            "xi0"
        ]
    )
    ==
    INLET_XI0,
)

for removed_name in (
    "injector_BC",
    "tip_BC",
    "anchor",
    "monotonicity",
    "bounds",
):

    gate(
        f"removed_{removed_name}_disabled",
        loss_contract[
            "removed_objectives"
        ][
            removed_name
        ][
            "enabled"
        ]
        is False,
    )


gate(
    "training_seed_exact",
    int(
        training_contract[
            "randomness"
        ][
            "seed"
        ]
    )
    ==
    SEED,
)

gate(
    "training_exact_COMP007_init",
    training_contract[
        "initialization"
    ][
        "model"
    ]
    ==
    "EXACT_FROZEN_COMP007",
)

gate(
    "training_fresh_Adam",
    training_contract[
        "initialization"
    ][
        "optimizer"
    ]
    ==
    "FRESH_ADAM",
)

gate(
    "optimizer_no_state_transfer",
    training_contract[
        "initialization"
    ][
        "optimizer_state_transfer"
    ]
    is False,
)

gate(
    "optimizer_Adam",
    training_contract[
        "optimizer"
    ][
        "type"
    ]
    ==
    "Adam",
)

gate(
    "learning_rate_exact_1e4",
    float(
        training_contract[
            "optimizer"
        ][
            "learning_rate"
        ]
    )
    ==
    LR,
)

gate(
    "foreach_false",
    training_contract[
        "optimizer"
    ][
        "foreach"
    ]
    is False,
)

gate(
    "scheduler_none",
    training_contract[
        "optimizer"
    ][
        "scheduler"
    ]
    is None,
)

gate(
    "clipping_none",
    training_contract[
        "optimizer"
    ][
        "gradient_clipping"
    ]
    is None,
)

gate(
    "AMP_off",
    training_contract[
        "optimizer"
    ][
        "AMP"
    ]
    is False,
)

gate(
    "TF32_off",
    training_contract[
        "optimizer"
    ][
        "TF32"
    ]
    is False,
)

gate(
    "epochs_exact_800",
    int(
        training_contract[
            "horizon"
        ][
            "epochs"
        ]
    )
    ==
    TARGET_EPOCHS,
)

gate(
    "steps_exact_1600",
    int(
        training_contract[
            "horizon"
        ][
            "optimizer_steps"
        ]
    )
    ==
    EXPECTED_TARGET_OPTIMIZER_STEPS,
)

gate(
    "early_stopping_false",
    training_contract[
        "horizon"
    ][
        "early_stopping"
    ]
    is False,
)

gate(
    "final_E800_only",
    training_contract[
        "horizon"
    ][
        "checkpoint_selection"
    ]
    ==
    "FINAL_COMPLETED_EPOCH_800_ONLY",
)

gate(
    "VJP_K64",
    int(
        training_contract[
            "geometry"
        ][
            "VJP_chunk"
        ]
    )
    ==
    ADOPTED_CHUNK,
)

gate(
    "microbatch_1024",
    int(
        training_contract[
            "geometry"
        ][
            "microbatch"
        ]
    )
    ==
    MICROBATCH,
)

gate(
    "logical_batch_8192",
    int(
        training_contract[
            "geometry"
        ][
            "logical_batch_1"
        ]
    )
    ==
    LOGICAL_BATCH,
)

gate(
    "second_logical_chunk_3328",
    int(
        training_contract[
            "geometry"
        ][
            "logical_batch_2"
        ]
    )
    ==
    SECOND_LOGICAL_CHUNK,
)

gate(
    "microbatches_per_epoch_12",
    int(
        training_contract[
            "geometry"
        ][
            "microbatches_per_epoch"
        ]
    )
    ==
    EXPECTED_MICROBATCHES_PER_EPOCH,
)

gate(
    "optimizer_steps_per_epoch_2",
    int(
        training_contract[
            "geometry"
        ][
            "optimizer_steps_per_epoch"
        ]
    )
    ==
    EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
)

gate(
    "original_holdout_forbidden",
    training_contract[
        "data"
    ][
        "original_holdout_use"
    ]
    ==
    "FORBIDDEN",
)

gate(
    "DEV_forbidden_during_production",
    training_contract[
        "data"
    ][
        "DEV_use_during_production"
    ]
    ==
    "FORBIDDEN_FOR_TRAINING_CHECKPOINT_SELECTION_EARLY_STOPPING_OR_ABORT_DECISIONS",
)

gate(
    "blind_CERT_forbidden_until_final_checkpoint",
    training_contract[
        "data"
    ][
        "blind_CERT_use_during_production"
    ]
    ==
    "FORBIDDEN_UNTIL_FINAL_E800_CHECKPOINT_IS_FROZEN",
)

gate(
    "cert_single_use",
    cert_contract[
        "blind_dataset"
    ][
        "single_use"
    ]
    is True,
)

gate(
    "cert_still_sealed",
    cert_contract[
        "blind_dataset"
    ][
        "scientifically_sealed_now"
    ]
    is True,
)


# =============================================================================
# Runtime gates
# =============================================================================

print()
print(
    "RUNTIME GATES"
)


gate(
    "CUDA_available",
    torch.cuda.is_available(),
)

device = torch.device(
    "cuda"
)

gpu_name = torch.cuda.get_device_name(
    0
)

gpu_total_bytes = (
    torch.cuda
    .get_device_properties(
        0
    )
    .total_memory
)

gpu_total_gib = (
    gpu_total_bytes
    /
    1024
    **
    3
)


print(
    "  PyTorch :",
    torch.__version__,
)

print(
    "  GPU     :",
    gpu_name,
)

print(
    "  Memory  :",
    f"{gpu_total_gib:.3f} GiB",
)


gate(
    "A100_runtime",
    "A100"
    in gpu_name,
)

gate(
    "A100_memory_at_least_70GiB",
    gpu_total_gib
    >=
    70.0,
)

gate(
    "PyTorch_2_11_0_cu128",
    str(
        torch.__version__
    )
    ==
    "2.11.0+cu128",
)


torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False


gate(
    "TF32_matmul_OFF",
    torch.backends.cuda.matmul.allow_tf32
    is False,
)

gate(
    "TF32_cudnn_OFF",
    torch.backends.cudnn.allow_tf32
    is False,
)


# =============================================================================
# Exact scientific / production authorities
# =============================================================================

C = import_by_path(
    "cuda8k_cuda6",
    CUDA6,
)

B2S = C.import_module(
    C.B2S_SOURCE,
    "cuda8k_B2S",
)

M = C.import_module(
    B2S.BASE_RUNNER,
    "cuda8k_M",
)

J = C.import_module(
    B2S.B2J_SOURCE,
    "cuda8k_J",
)

CUDA3 = C.import_module(
    C.CUDA3_SOURCE,
    "cuda8k_CUDA3",
)


print()
print(
    "SCIENTIFIC SOURCE GATES"
)


gate(
    "B2S_SHA_exact",
    sha256(
        Path(
            B2S.__file__
        )
    )
    ==
    EXPECTED[
        "B2S"
    ],
)

gate(
    "BASE_M_SHA_exact",
    sha256(
        Path(
            M.__file__
        )
    )
    ==
    EXPECTED[
        "BASE_M"
    ],
)

gate(
    "ETA_J_SHA_exact",
    sha256(
        Path(
            J.__file__
        )
    )
    ==
    EXPECTED[
        "ETA_J"
    ],
)

gate(
    "CUDA3_SHA_exact",
    sha256(
        Path(
            CUDA3.__file__
        )
    )
    ==
    EXPECTED[
        "CUDA3"
    ],
)


# =============================================================================
# Dataset and frozen split
# =============================================================================

with np.load(
    DATASET,
    allow_pickle=False,
) as d:

    required = (
        "xi",
        "Sw",
        "p11",
        "tD",
        "ai",
        "at",
    )

    missing = [
        key
        for key
        in required
        if key
        not in d.files
    ]

    gate(
        "dataset_required_arrays",
        len(
            missing
        )
        ==
        0,
    )

    xi_all = np.array(
        d[
            "xi"
        ],
        copy=True,
    )

    Sw_all = np.array(
        d[
            "Sw"
        ],
        copy=True,
    )

    p11_all = np.array(
        d[
            "p11"
        ],
        copy=True,
    )


gate(
    "dataset_profiles_14400",
    len(
        xi_all
    )
    ==
    N_TOTAL,
)

gate(
    "fan_nodes_64",
    xi_all.shape[
        1
    ]
    ==
    64,
)

gate(
    "dataset_arrays_finite",
    np.isfinite(
        xi_all
    ).all()
    and
    np.isfinite(
        Sw_all
    ).all()
    and
    np.isfinite(
        p11_all
    ).all(),
)


recovery005 = torch.load(
    RECOVERY005_E0800,
    map_location="cpu",
    weights_only=False,
)

train_idx = np.asarray(
    recovery005[
        "train_idx"
    ],
    dtype=np.int64,
)

holdout_idx = np.asarray(
    recovery005[
        "holdout_idx"
    ],
    dtype=np.int64,
)


print()
print(
    "SPLIT FIREWALL GATES"
)


gate(
    "train_idx_SHA_exact",
    array_sha256(
        train_idx
    )
    ==
    EXPECTED[
        "train_idx"
    ],
)

gate(
    "holdout_idx_SHA_exact",
    array_sha256(
        holdout_idx
    )
    ==
    EXPECTED[
        "holdout_idx"
    ],
)

gate(
    "train_count_11520",
    len(
        train_idx
    )
    ==
    N_TRAIN,
)

gate(
    "holdout_count_2880",
    len(
        holdout_idx
    )
    ==
    N_HOLDOUT,
)

gate(
    "train_holdout_disjoint",
    np.intersect1d(
        train_idx,
        holdout_idx,
    ).size
    ==
    0,
)

gate(
    "train_holdout_cover_14400",
    np.union1d(
        train_idx,
        holdout_idx,
    ).size
    ==
    N_TOTAL,
)


# =============================================================================
# Frozen equal-Nc normalization
# =============================================================================

norm_artifact = json.loads(
    CUDA8BR_NORMALIZATION.read_text(
        encoding="utf-8"
    )
)

normalizer = {}
profile_counts = {}

T_INTERIOR = (
    xi_all.shape[
        1
    ]
    -
    2
)


for _key, row in (
    norm_artifact[
        "Nc_strata"
    ].items()
):

    nc = float(
        row[
            "Nc"
        ]
    )

    mse = float(
        row[
            "residual_MSE"
        ]
    )

    residual_count = int(
        row[
            "residual_count"
        ]
    )


    gate(
        f"Nc_{nc}_normalizer_finite",
        math.isfinite(
            mse
        )
        and
        mse
        >
        0.0,
    )

    gate(
        f"Nc_{nc}_residual_count_divisible",
        residual_count
        %
        T_INTERIOR
        ==
        0,
    )


    normalizer[
        nc
    ] = mse

    profile_counts[
        nc
    ] = (
        residual_count
        //
        T_INTERIOR
    )


gate(
    "five_normalizers",
    len(
        normalizer
    )
    ==
    NC_COUNT,
)

gate(
    "normalizer_profile_counts_cover_training",
    sum(
        profile_counts.values()
    )
    ==
    N_TRAIN,
)


# =============================================================================
# COMP008 bounded-monotone architecture
# =============================================================================

BaseEtaModel = J.build_eta_model_class(
    M
)


class COMP008BoundedMonotoneModel(
    BaseEtaModel
):

    EPSILON = 1.0e-8

    def forward(
        self,
        xi_seq,
        p11_phys,
    ):

        z = super().forward(
            xi_seq,
            p11_phys,
        )


        interval_logits = (
            0.5
            *
            (
                z[
                    :,
                    :-1,
                    :
                ]
                +
                z[
                    :,
                    1:,
                    :
                ]
            )
        )


        q = (
            F.softplus(
                interval_logits
            )
            +
            self.EPSILON
        )


        w = (
            q
            /
            q.sum(
                dim=1,
                keepdim=True,
            )
        )


        cumulative = torch.cumsum(
            w,
            dim=1,
        )


        zero = torch.zeros_like(
            z[
                :,
                :1,
                :
            ]
        )

        one = torch.ones_like(
            z[
                :,
                :1,
                :
            ]
        )


        Ccoord = torch.cat(
            [
                zero,
                cumulative[
                    :,
                    :-1,
                    :
                ],
                one,
            ],
            dim=1,
        )


        sor = (
            p11_phys[
                :,
                3:4
            ]
            .unsqueeze(
                1
            )
        )

        Sw_star = (
            p11_phys[
                :,
                9:10
            ]
            .unsqueeze(
                1
            )
        )

        S_inj = (
            1.0
            -
            sor
        )


        S_hat = (
            S_inj
            -
            (
                S_inj
                -
                Sw_star
            )
            *
            Ccoord
        )


        return S_hat


# =============================================================================
# Exact CUDA8J objective
# =============================================================================

def inlet_weighted_profile_residual_mse(
    residual,
    xi,
):

    xi_interior = (
        xi[
            :,
            1:-1,
            :
        ]
    )


    if (
        residual.shape
        !=
        xi_interior.shape
    ):

        raise RuntimeError(
            "Corrected residual / interior-xi shape mismatch: "
            f"{tuple(residual.shape)} vs {tuple(xi_interior.shape)}"
        )


    raw_weight = (
        1.0
        +
        INLET_ALPHA
        *
        torch.exp(
            -
            (
                xi_interior
                /
                INLET_XI0
            )
            **
            2
        )
    )


    normalized_weight = (
        raw_weight
        /
        torch.mean(
            raw_weight,
            dim=(
                1,
                2,
            ),
            keepdim=True,
        )
    )


    if not finite_tensor(
        normalized_weight
    ):

        raise RuntimeError(
            "Nonfinite inlet spatial physics weight."
        )


    return torch.mean(
        normalized_weight
        *
        residual
        **
        2,
        dim=(
            1,
            2,
        ),
    )


def comp008_loss(
    model,
    xi,
    Sw,
    p11,
):

    (
        S_hat,
        _global_unweighted_physics,
        residual,
    ) = (
        B2S.corrected_physics_loss_training_graph(
            M,
            model,
            xi,
            p11,
        )
    )


    Ldata = torch.mean(
        (
            S_hat
            -
            Sw
        )
        **
        2
    )


    profile_residual_mse = (
        inlet_weighted_profile_residual_mse(
            residual,
            xi,
        )
    )


    nc = (
        p11[
            :,
            10
        ]
    )


    physics_weighted_sum = torch.zeros(
        (),
        device=xi.device,
        dtype=xi.dtype,
    )


    assignment_count = torch.zeros_like(
        nc,
        dtype=torch.int16,
    )


    for val in NC_VALUES:

        mask = native_nc_mask_torch(
            nc,
            val,
        )


        assignment_count = (
            assignment_count
            +
            mask.to(
                torch.int16
            )
        )


        if bool(
            torch.any(
                mask
            ).item()
        ):

            global_profile_weight = (
                float(
                    N_TRAIN
                )
                /
                (
                    float(
                        NC_COUNT
                    )
                    *
                    float(
                        profile_counts[
                            val
                        ]
                    )
                )
            )


            physics_weighted_sum = (
                physics_weighted_sum

                +
                global_profile_weight
                *
                torch.sum(
                    profile_residual_mse[
                        mask
                    ]
                    /
                    normalizer[
                        val
                    ]
                )
            )


    if not bool(
        torch.all(
            assignment_count
            ==
            1
        ).item()
    ):

        raise RuntimeError(
            "Each COMP008 training profile must map to exactly one frozen Nc stratum."
        )


    Lphys = (
        physics_weighted_sum
        /
        float(
            xi.shape[
                0
            ]
        )
    )


    total = (
        LAMBDA_DATA
        *
        Ldata

        +
        LAMBDA_PHYS
        *
        Lphys
    )


    parts = {
        "data":
            Ldata,

        "physics":
            Lphys,

        "total":
            total,
    }


    return (
        S_hat,
        residual,
        parts,
    )


# =============================================================================
# Model / optimizer construction
# =============================================================================

def build_model_optimizer():

    random.seed(
        SEED
    )

    np.random.seed(
        SEED
    )

    torch.manual_seed(
        SEED
    )

    torch.cuda.manual_seed_all(
        SEED
    )


    model = (
        COMP008BoundedMonotoneModel()
        .to(
            device
        )
    )


    ckpt007 = torch.load(
        COMP007,
        map_location="cpu",
        weights_only=False,
    )


    if (
        "model_state_dict"
        not in ckpt007
    ):

        raise RuntimeError(
            "COMP007 checkpoint does not contain model_state_dict."
        )


    result = model.load_state_dict(
        ckpt007[
            "model_state_dict"
        ],
        strict=True,
    )


    gate(
        "COMP007_warm_start_strict",
        len(
            result.missing_keys
        )
        ==
        0
        and
        len(
            result.unexpected_keys
        )
        ==
        0,
    )


    gate(
        "warm_started_parameters_finite",
        model_finite(
            model
        ),
    )


    warm_start_hash = state_tensor_hash(
        model.state_dict()
    )


    gate(
        "COMP007_model_state_tensor_SHA_exact",
        warm_start_hash
        ==
        EXPECTED[
            "COMP007_STATE"
        ],
    )


    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LR,
        foreach=False,
    )


    gate(
        "fresh_Adam_has_no_state",
        len(
            optimizer.state
        )
        ==
        0,
    )


    return (
        model,
        optimizer,
        warm_start_hash,
    )


# =============================================================================
# Production-only implementation preflight
# =============================================================================

def production_preflight(
    model,
    optimizer,
):

    # One deterministic TRAIN profile from each frozen Nc stratum.
    chosen = []

    nc_train = (
        p11_all[
            train_idx,
            10
        ]
    )


    for val in NC_VALUES:

        rel = np.where(
            nc_train
            ==
            np.asarray(
                val,
                dtype=nc_train.dtype,
            )
        )[
            0
        ]

        if rel.size <= 0:

            raise RuntimeError(
                f"No training profile found for Nc={val}."
            )

        chosen.append(
            int(
                train_idx[
                    rel[
                        0
                    ]
                ]
            )
        )


    ids = np.asarray(
        chosen,
        dtype=np.int64,
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


    engine = (
        CUDA3
        .make_cuda3_chunked_batched_engine(
            ADOPTED_CHUNK
        )
    )

    original_engine = (
        B2S
        .local_recurrent_derivatives_create_graph
    )


    try:

        (
            B2S
            .local_recurrent_derivatives_create_graph
        ) = engine


        model.train()

        optimizer.zero_grad(
            set_to_none=True
        )


        with torch.backends.cudnn.flags(
            enabled=False
        ):

            (
                S_hat,
                residual,
                parts,
            ) = (
                comp008_loss(
                    model,
                    xi,
                    Sw,
                    p11,
                )
            )


        gate(
            "preflight_prediction_finite",
            finite_tensor(
                S_hat
            ),
        )

        gate(
            "preflight_residual_finite",
            finite_tensor(
                residual
            ),
        )

        gate(
            "preflight_losses_finite",
            all(
                finite_tensor(
                    v
                )
                for v
                in parts.values()
            ),
        )


        S_inj = (
            1.0
            -
            p11[
                :,
                3
            ]
        )

        Sw_star = (
            p11[
                :,
                9
            ]
        )


        injector_error = torch.max(
            torch.abs(
                S_hat[
                    :,
                    0,
                    0
                ]
                -
                S_inj
            )
        )

        tip_error = torch.max(
            torch.abs(
                S_hat[
                    :,
                    -1,
                    0
                ]
                -
                Sw_star
            )
        )

        upper_violation = torch.max(
            torch.relu(
                S_hat[
                    :,
                    :,
                    0
                ]
                -
                S_inj[
                    :,
                    None
                ]
            )
        )

        lower_violation = torch.max(
            torch.relu(
                Sw_star[
                    :,
                    None
                ]
                -
                S_hat[
                    :,
                    :,
                    0
                ]
            )
        )

        positive_slope = torch.max(
            torch.relu(
                S_hat[
                    :,
                    1:,
                    0
                ]
                -
                S_hat[
                    :,
                    :-1,
                    0
                ]
            )
        )


        gate(
            "preflight_injector_endpoint_exact",
            float(
                injector_error
                .detach()
                .cpu()
                .item()
            )
            <=
            STRUCT_TOL,
        )

        gate(
            "preflight_tip_endpoint_exact",
            float(
                tip_error
                .detach()
                .cpu()
                .item()
            )
            <=
            STRUCT_TOL,
        )

        gate(
            "preflight_upper_bound_exact",
            float(
                upper_violation
                .detach()
                .cpu()
                .item()
            )
            <=
            STRUCT_TOL,
        )

        gate(
            "preflight_lower_bound_exact",
            float(
                lower_violation
                .detach()
                .cpu()
                .item()
            )
            <=
            STRUCT_TOL,
        )

        gate(
            "preflight_monotonicity_exact",
            float(
                positive_slope
                .detach()
                .cpu()
                .item()
            )
            <=
            STRUCT_TOL,
        )


        with torch.backends.cudnn.flags(
            enabled=False
        ):

            parts[
                "total"
            ].backward()


        grad_summary = (
            C.parameter_gradient_summary(
                model
            )
        )


        gate(
            "preflight_gradients_finite",
            grad_summary[
                "gradients_finite"
            ],
        )

        gate(
            "preflight_nonzero_gradients",
            grad_summary[
                "nonzero_gradient_tensor_count"
            ]
            >
            0,
        )


        # No optimizer step is allowed during preflight.
        gate(
            "preflight_optimizer_state_still_empty",
            len(
                optimizer.state
            )
            ==
            0,
        )


        optimizer.zero_grad(
            set_to_none=True
        )


    finally:

        (
            B2S
            .local_recurrent_derivatives_create_graph
        ) = (
            original_engine
        )


        del (
            xi,
            Sw,
            p11,
        )

        torch.cuda.empty_cache()


# =============================================================================
# Runner / configuration authority
# =============================================================================

RUNNER_PATH = Path(
    __file__
)

RUNNER_SHA = sha256(
    RUNNER_PATH
)


CONFIG_OBJECT = {
    "milestone":
        MILESTONE,

    "experiment":
        EXPERIMENT,

    "status":
        STATUS_RUNNING,

    "runner_sha256":
        RUNNER_SHA,

    "CUDA8J_authorities": {
        "source":
            EXPECTED[
                "CUDA8J_SOURCE"
            ],

        "architecture":
            EXPECTED[
                "CUDA8J_ARCHITECTURE"
            ],

        "loss":
            EXPECTED[
                "CUDA8J_LOSS"
            ],

        "training":
            EXPECTED[
                "CUDA8J_TRAINING"
            ],

        "certification":
            EXPECTED[
                "CUDA8J_CERTIFICATION"
            ],

        "decision":
            EXPECTED[
                "CUDA8J_DECISION"
            ],

        "summary":
            EXPECTED[
                "CUDA8J_SUMMARY"
            ],

        "handoff":
            EXPECTED[
                "CUDA8J_HANDOFF"
            ],
    },

    "data": {
        "dataset_sha256":
            EXPECTED[
                "dataset"
            ],

        "train_idx_sha256":
            EXPECTED[
                "train_idx"
            ],

        "retired_holdout_idx_sha256":
            EXPECTED[
                "holdout_idx"
            ],

        "DEV_dataset_sha256":
            EXPECTED[
                "DEV_DATASET"
            ],

        "blind_CERT_dataset_sha256":
            EXPECTED[
                "BLIND_CERT"
            ],

        "original_holdout_evaluated":
            False,

        "DEV_loaded":
            False,

        "blind_CERT_loaded":
            False,
    },

    "initialization": {
        "checkpoint_sha256":
            EXPECTED[
                "COMP007"
            ],

        "model_state_tensor_sha256":
            EXPECTED[
                "COMP007_STATE"
            ],

        "optimizer":
            "FRESH_ADAM",
    },

    "architecture": {
        "bounded_monotone":
            True,

        "hidden":
            64,

        "layers":
            2,

        "epsilon":
            1.0e-8,
    },

    "loss": {
        "lambda_data":
            LAMBDA_DATA,

        "lambda_physics":
            LAMBDA_PHYS,

        "equal_Nc_normalization":
            True,

        "normalization_sha256":
            EXPECTED[
                "CUDA8BR_NORMALIZATION"
            ],

        "inlet_weight": {
            "alpha":
                INLET_ALPHA,

            "xi0":
                INLET_XI0,

            "mean_normalized_per_profile":
                True,

            "Nc_specific":
                False,
        },

        "BC":
            False,

        "tip":
            False,

        "anchor":
            False,

        "monotonicity":
            False,

        "bounds":
            False,
    },

    "training": {
        "seed":
            SEED,

        "epochs":
            TARGET_EPOCHS,

        "optimizer_steps":
            EXPECTED_TARGET_OPTIMIZER_STEPS,

        "optimizer":
            "Adam",

        "learning_rate":
            LR,

        "foreach":
            False,

        "scheduler":
            None,

        "gradient_clipping":
            None,

        "AMP":
            False,

        "TF32":
            False,

        "early_stopping":
            False,
    },

    "geometry": {
        "VJP_chunk":
            ADOPTED_CHUNK,

        "microbatch":
            MICROBATCH,

        "logical_batch":
            LOGICAL_BATCH,

        "second_logical_chunk":
            SECOND_LOGICAL_CHUNK,

        "microbatches_per_epoch":
            EXPECTED_MICROBATCHES_PER_EPOCH,

        "optimizer_steps_per_epoch":
            EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
    },

    "recovery": {
        "completed_epoch_only":
            True,

        "atomic":
            True,

        "exact_runner_hash_resume":
            True,

        "orphaned_recovery_fail_closed":
            True,
    },

    "final_checkpoint_authority":
        "FINAL_COMPLETED_EPOCH_800_ONLY",
}


if CONFIG.exists():

    existing_config = json.loads(
        CONFIG.read_text(
            encoding="utf-8"
        )
    )

    gate(
        "existing_config_exact",
        existing_config
        ==
        CONFIG_OBJECT,
    )

else:

    write_json_atomic(
        CONFIG,
        CONFIG_OBJECT,
    )


CONFIG_SHA = sha256(
    CONFIG
)


# =============================================================================
# Recovery
# =============================================================================

def recovery_path(
    epoch: int,
) -> Path:

    return (
        RECOVERY_DIR
        /
        f"V16E_BLREP_COMP_CUDA_008_RECOVERY_E{epoch:04d}.pt"
    )


def rng_state_payload():

    return {
        "python_random_state":
            random.getstate(),

        "numpy_random_state":
            np.random.get_state(),

        "torch_cpu_rng_state":
            torch.get_rng_state(),

        "torch_cuda_rng_state_all":
            torch.cuda.get_rng_state_all(),
    }


def restore_rng_state(
    payload,
):

    random.setstate(
        payload[
            "python_random_state"
        ]
    )

    np.random.set_state(
        payload[
            "numpy_random_state"
        ]
    )

    torch.set_rng_state(
        payload[
            "torch_cpu_rng_state"
        ]
    )

    torch.cuda.set_rng_state_all(
        payload[
            "torch_cuda_rng_state_all"
        ]
    )


def save_recovery(
    model,
    optimizer,
    history,
    completed_epoch,
    optimizer_steps_completed,
):

    if completed_epoch < 1:

        raise RuntimeError(
            "Only completed epochs may be recovery authority."
        )


    expected_steps = (
        completed_epoch
        *
        EXPECTED_OPTIMIZER_STEPS_PER_EPOCH
    )


    if (
        optimizer_steps_completed
        !=
        expected_steps
    ):

        raise RuntimeError(
            "Cannot save recovery: optimizer-step count does not match completed epoch."
        )


    validate_history(
        history,
        completed_epoch,
        optimizer_steps_completed,
    )


    path = recovery_path(
        completed_epoch
    )


    payload = {
        "experiment":
            EXPERIMENT,

        "milestone":
            MILESTONE,

        "runner_sha256":
            RUNNER_SHA,

        "config_sha256":
            CONFIG_SHA,

        "CUDA8J_training_contract_sha256":
            EXPECTED[
                "CUDA8J_TRAINING"
            ],

        "CUDA8J_loss_contract_sha256":
            EXPECTED[
                "CUDA8J_LOSS"
            ],

        "dataset_sha256":
            EXPECTED[
                "dataset"
            ],

        "COMP007_initialization_sha256":
            EXPECTED[
                "COMP007"
            ],

        "COMP007_state_tensor_sha256":
            EXPECTED[
                "COMP007_STATE"
            ],

        "normalization_sha256":
            EXPECTED[
                "CUDA8BR_NORMALIZATION"
            ],

        "completed_epoch":
            int(
                completed_epoch
            ),

        "optimizer_steps_completed":
            int(
                optimizer_steps_completed
            ),

        "model_state_dict":
            model.state_dict(),

        "optimizer_state_dict":
            optimizer.state_dict(),

        "history":
            history,

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

        "rng":
            rng_state_payload(),

        "training_contract": {
            "target_epochs":
                TARGET_EPOCHS,

            "target_optimizer_steps":
                EXPECTED_TARGET_OPTIMIZER_STEPS,

            "microbatch":
                MICROBATCH,

            "logical_batch":
                LOGICAL_BATCH,

            "second_logical_chunk":
                SECOND_LOGICAL_CHUNK,

            "VJP_chunk":
                ADOPTED_CHUNK,

            "learning_rate":
                LR,

            "lambda_data":
                LAMBDA_DATA,

            "lambda_physics":
                LAMBDA_PHYS,

            "inlet_alpha":
                INLET_ALPHA,

            "inlet_xi0":
                INLET_XI0,
        },
    }


    torch_save_atomic(
        path,
        payload,
    )


    recovery_sha = sha256(
        path
    )


    pointer = {
        "experiment":
            EXPERIMENT,

        "runner_sha256":
            RUNNER_SHA,

        "config_sha256":
            CONFIG_SHA,

        "completed_epoch":
            int(
                completed_epoch
            ),

        "optimizer_steps_completed":
            int(
                optimizer_steps_completed
            ),

        "recovery_path":
            str(
                path
            ),

        "recovery_sha256":
            recovery_sha,
    }


    write_json_atomic(
        RECOVERY_LATEST,
        pointer,
    )

    write_json_atomic(
        HISTORY,
        history,
    )


    return (
        path,
        recovery_sha,
    )


def load_recovery(
    model,
    optimizer,
):

    if not RECOVERY_LATEST.exists():

        orphaned = sorted(
            RECOVERY_DIR.glob(
                "V16E_BLREP_COMP_CUDA_008_RECOVERY_E*.pt"
            )
        )


        if orphaned:

            raise RuntimeError(
                "COMP008 recovery checkpoints exist but RECOVERY_LATEST.json "
                "is missing. Failing closed rather than guessing authority."
            )


        return None


    pointer = json.loads(
        RECOVERY_LATEST.read_text(
            encoding="utf-8"
        )
    )


    gate(
        "recovery_pointer_experiment",
        pointer[
            "experiment"
        ]
        ==
        EXPERIMENT,
    )

    gate(
        "recovery_pointer_runner_SHA",
        pointer[
            "runner_sha256"
        ]
        ==
        RUNNER_SHA,
    )

    gate(
        "recovery_pointer_config_SHA",
        pointer[
            "config_sha256"
        ]
        ==
        CONFIG_SHA,
    )


    path = Path(
        pointer[
            "recovery_path"
        ]
    )


    gate(
        "recovery_file_exists",
        path.exists(),
    )

    gate(
        "recovery_file_SHA_exact",
        sha256(
            path
        )
        ==
        pointer[
            "recovery_sha256"
        ],
    )


    recovery = torch.load(
        path,
        map_location="cpu",
        weights_only=False,
    )


    gate(
        "recovery_experiment",
        recovery[
            "experiment"
        ]
        ==
        EXPERIMENT,
    )

    gate(
        "recovery_runner_SHA",
        recovery[
            "runner_sha256"
        ]
        ==
        RUNNER_SHA,
    )

    gate(
        "recovery_config_SHA",
        recovery[
            "config_sha256"
        ]
        ==
        CONFIG_SHA,
    )

    gate(
        "recovery_CUDA8J_training_contract_SHA",
        recovery[
            "CUDA8J_training_contract_sha256"
        ]
        ==
        EXPECTED[
            "CUDA8J_TRAINING"
        ],
    )

    gate(
        "recovery_CUDA8J_loss_contract_SHA",
        recovery[
            "CUDA8J_loss_contract_sha256"
        ]
        ==
        EXPECTED[
            "CUDA8J_LOSS"
        ],
    )

    gate(
        "recovery_dataset_SHA",
        recovery[
            "dataset_sha256"
        ]
        ==
        EXPECTED[
            "dataset"
        ],
    )

    gate(
        "recovery_COMP007_initialization_SHA",
        recovery[
            "COMP007_initialization_sha256"
        ]
        ==
        EXPECTED[
            "COMP007"
        ],
    )

    gate(
        "recovery_COMP007_state_tensor_SHA",
        recovery[
            "COMP007_state_tensor_sha256"
        ]
        ==
        EXPECTED[
            "COMP007_STATE"
        ],
    )

    gate(
        "recovery_normalization_SHA",
        recovery[
            "normalization_sha256"
        ]
        ==
        EXPECTED[
            "CUDA8BR_NORMALIZATION"
        ],
    )


    completed_epoch = int(
        recovery[
            "completed_epoch"
        ]
    )

    optimizer_steps_completed = int(
        recovery[
            "optimizer_steps_completed"
        ]
    )


    gate(
        "recovery_epoch_in_range",
        1
        <=
        completed_epoch
        <=
        TARGET_EPOCHS,
    )

    gate(
        "recovery_optimizer_steps_exact",
        optimizer_steps_completed
        ==
        completed_epoch
        *
        EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
    )


    recovered_train_idx = np.asarray(
        recovery[
            "train_idx"
        ],
        dtype=np.int64,
    )

    recovered_holdout_idx = np.asarray(
        recovery[
            "holdout_idx"
        ],
        dtype=np.int64,
    )


    gate(
        "recovery_train_idx_SHA_exact",
        array_sha256(
            recovered_train_idx
        )
        ==
        EXPECTED[
            "train_idx"
        ],
    )

    gate(
        "recovery_holdout_idx_SHA_exact",
        array_sha256(
            recovered_holdout_idx
        )
        ==
        EXPECTED[
            "holdout_idx"
        ],
    )


    frozen_tc = recovery[
        "training_contract"
    ]


    gate(
        "recovery_target_epochs_exact",
        int(
            frozen_tc[
                "target_epochs"
            ]
        )
        ==
        TARGET_EPOCHS,
    )

    gate(
        "recovery_target_steps_exact",
        int(
            frozen_tc[
                "target_optimizer_steps"
            ]
        )
        ==
        EXPECTED_TARGET_OPTIMIZER_STEPS,
    )

    gate(
        "recovery_microbatch_exact",
        int(
            frozen_tc[
                "microbatch"
            ]
        )
        ==
        MICROBATCH,
    )

    gate(
        "recovery_logical_batch_exact",
        int(
            frozen_tc[
                "logical_batch"
            ]
        )
        ==
        LOGICAL_BATCH,
    )

    gate(
        "recovery_second_chunk_exact",
        int(
            frozen_tc[
                "second_logical_chunk"
            ]
        )
        ==
        SECOND_LOGICAL_CHUNK,
    )

    gate(
        "recovery_VJP_chunk_exact",
        int(
            frozen_tc[
                "VJP_chunk"
            ]
        )
        ==
        ADOPTED_CHUNK,
    )

    gate(
        "recovery_lr_exact",
        float(
            frozen_tc[
                "learning_rate"
            ]
        )
        ==
        LR,
    )

    gate(
        "recovery_lambda_data_exact",
        float(
            frozen_tc[
                "lambda_data"
            ]
        )
        ==
        LAMBDA_DATA,
    )

    gate(
        "recovery_lambda_physics_exact",
        float(
            frozen_tc[
                "lambda_physics"
            ]
        )
        ==
        LAMBDA_PHYS,
    )

    gate(
        "recovery_inlet_alpha_exact",
        float(
            frozen_tc[
                "inlet_alpha"
            ]
        )
        ==
        INLET_ALPHA,
    )

    gate(
        "recovery_inlet_xi0_exact",
        float(
            frozen_tc[
                "inlet_xi0"
            ]
        )
        ==
        INLET_XI0,
    )


    history = recovery[
        "history"
    ]


    validate_history(
        history,
        completed_epoch,
        optimizer_steps_completed,
    )


    result = model.load_state_dict(
        recovery[
            "model_state_dict"
        ],
        strict=True,
    )


    gate(
        "recovery_model_state_strict",
        len(
            result.missing_keys
        )
        ==
        0
        and
        len(
            result.unexpected_keys
        )
        ==
        0,
    )


    optimizer.load_state_dict(
        recovery[
            "optimizer_state_dict"
        ]
    )


    C.move_optimizer_state_to_device(
        optimizer,
        device,
    )


    gate(
        "recovered_model_parameters_finite",
        model_finite(
            model
        ),
    )


    restore_rng_state(
        recovery[
            "rng"
        ]
    )


    return {
        "completed_epoch":
            completed_epoch,

        "optimizer_steps_completed":
            optimizer_steps_completed,

        "history":
            history,

        "path":
            path,

        "sha256":
            pointer[
                "recovery_sha256"
            ],
    }


# =============================================================================
# Production training
# =============================================================================

def train_or_resume():

    (
        model,
        optimizer,
        warm_start_hash,
    ) = (
        build_model_optimizer()
    )


    recovery = load_recovery(
        model,
        optimizer,
    )


    if recovery is None:

        print()
        print(
            "PRODUCTION IMPLEMENTATION PREFLIGHT"
        )

        production_preflight(
            model,
            optimizer,
        )


        start_epoch = 1

        optimizer_steps_completed = 0

        history = empty_history()


        print()
        print(
            "PRODUCTION START"
        )

        print(
            "  mode                  : FRESH"
        )

        print(
            "  initialization        : FROZEN COMP007"
        )

        print(
            "  warm-start tensor SHA :",
            warm_start_hash,
        )

        print(
            "  optimizer             : FRESH Adam"
        )

    else:

        start_epoch = (
            recovery[
                "completed_epoch"
            ]
            +
            1
        )

        optimizer_steps_completed = (
            recovery[
                "optimizer_steps_completed"
            ]
        )

        history = recovery[
            "history"
        ]


        print()
        print(
            "PRODUCTION RESUME"
        )

        print(
            "  completed epoch       :",
            recovery[
                "completed_epoch"
            ],
        )

        print(
            "  optimizer steps       :",
            optimizer_steps_completed,
        )

        print(
            "  recovery SHA          :",
            recovery[
                "sha256"
            ],
        )


    print()
    print(
        "PRODUCTION TRAINING CONTRACT"
    )

    print(
        "  device                :",
        device,
    )

    print(
        "  GPU                   :",
        gpu_name,
    )

    print(
        "  train profiles        :",
        N_TRAIN,
    )

    print(
        "  original holdout      :",
        N_HOLDOUT,
        "(RETIRED / NOT EVALUATED)",
    )

    print(
        "  DEV                   : NOT LOADED"
    )

    print(
        "  blind CERT            : SEALED / NOT LOADED"
    )

    print(
        "  VJP chunk             :",
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
        "  second logical chunk  :",
        SECOND_LOGICAL_CHUNK,
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
        "  data lambda           :",
        LAMBDA_DATA,
    )

    print(
        "  physics lambda        :",
        f"{LAMBDA_PHYS:.15e}",
    )

    print(
        "  inlet alpha           :",
        INLET_ALPHA,
    )

    print(
        "  inlet xi0             :",
        INLET_XI0,
    )

    print(
        "  inlet normalized      : YES"
    )

    print(
        "  BC/tip/anchor/mono/bounds penalties: NONE"
    )

    print(
        "  AMP                   : OFF"
    )

    print(
        "  TF32                  : OFF"
    )

    print(
        "  early stopping        : NO"
    )


    if (
        start_epoch
        >
        TARGET_EPOCHS
    ):

        gate(
            "completed_history_800_epochs",
            len(
                history[
                    "epoch"
                ]
            )
            ==
            TARGET_EPOCHS,
        )

        gate(
            "completed_optimizer_steps_1600",
            optimizer_steps_completed
            ==
            EXPECTED_TARGET_OPTIMIZER_STEPS,
        )

        return (
            model,
            optimizer,
            history,
            optimizer_steps_completed,
        )


    engine = (
        CUDA3
        .make_cuda3_chunked_batched_engine(
            ADOPTED_CHUNK
        )
    )

    original_engine = (
        B2S
        .local_recurrent_derivatives_create_graph
    )

    session_t0 = time.time()


    try:

        (
            B2S
            .local_recurrent_derivatives_create_graph
        ) = engine


        model.train()


        for epoch in range(
            start_epoch,
            TARGET_EPOCHS
            +
            1,
        ):

            epoch_t0 = time.time()

            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()


            order = C.production_epoch_order(
                train_idx,
                epoch,
            )


            gate(
                f"epoch_{epoch}_order_count",
                len(
                    order
                )
                ==
                N_TRAIN,
            )


            sums = {
                "data":
                    0.0,

                "physics":
                    0.0,

                "total":
                    0.0,
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
                    +
                    LOGICAL_BATCH
                ]

                logical_n = len(
                    logical_idx
                )


                if logical_n not in (
                    LOGICAL_BATCH,
                    SECOND_LOGICAL_CHUNK,
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
                        +
                        MICROBATCH
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


                    Sw = (
                        torch.from_numpy(
                            Sw_all[
                                ids
                            ]
                        )
                        .to(
                            device
                        )
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


                    with torch.backends.cudnn.flags(
                        enabled=False
                    ):

                        (
                            S_hat,
                            residual,
                            parts,
                        ) = (
                            comp008_loss(
                                model,
                                xi,
                                Sw,
                                p11,
                            )
                        )


                    if not finite_tensor(
                        S_hat
                    ):

                        raise RuntimeError(
                            f"Epoch {epoch}: nonfinite prediction."
                        )


                    if not finite_tensor(
                        residual
                    ):

                        raise RuntimeError(
                            f"Epoch {epoch}: nonfinite corrected residual."
                        )


                    if not all(
                        finite_tensor(
                            v
                        )
                        for v
                        in parts.values()
                    ):

                        raise RuntimeError(
                            f"Epoch {epoch}: nonfinite loss."
                        )


                    scale = (
                        float(
                            m
                        )
                        /
                        float(
                            logical_n
                        )
                    )


                    scaled_total = (
                        parts[
                            "total"
                        ]
                        *
                        scale
                    )


                    with torch.backends.cudnn.flags(
                        enabled=False
                    ):

                        scaled_total.backward()


                    for key in sums:

                        sums[
                            key
                        ] += (
                            float(
                                parts[
                                    key
                                ]
                                .detach()
                                .cpu()
                                .item()
                            )
                            *
                            m
                        )


                    count += m

                    epoch_microbatches += 1


                    del (
                        xi,
                        Sw,
                        p11,
                        S_hat,
                        residual,
                        parts,
                        scaled_total,
                    )


                accumulated = (
                    C.parameter_gradient_summary(
                        model
                    )
                )


                if not accumulated[
                    "gradients_finite"
                ]:

                    raise RuntimeError(
                        f"Epoch {epoch}: accumulated gradients are nonfinite."
                    )


                if (
                    accumulated[
                        "nonzero_gradient_tensor_count"
                    ]
                    <=
                    0
                ):

                    raise RuntimeError(
                        f"Epoch {epoch}: all accumulated gradients are zero."
                    )


                optimizer.step()

                sync_cuda()


                optimizer_steps_completed += 1

                epoch_optimizer_steps += 1


                if not model_finite(
                    model
                ):

                    raise RuntimeError(
                        f"Epoch {epoch}: model parameters became nonfinite."
                    )


                optimizer.zero_grad(
                    set_to_none=True
                )


            sync_cuda()


            if count != N_TRAIN:

                raise RuntimeError(
                    f"Epoch {epoch}: accepted {count} profiles; expected {N_TRAIN}."
                )


            if (
                epoch_microbatches
                !=
                EXPECTED_MICROBATCHES_PER_EPOCH
            ):

                raise RuntimeError(
                    f"Epoch {epoch}: executed {epoch_microbatches} microbatches; "
                    f"expected {EXPECTED_MICROBATCHES_PER_EPOCH}."
                )


            if (
                epoch_optimizer_steps
                !=
                EXPECTED_OPTIMIZER_STEPS_PER_EPOCH
            ):

                raise RuntimeError(
                    f"Epoch {epoch}: executed {epoch_optimizer_steps} optimizer steps; "
                    f"expected {EXPECTED_OPTIMIZER_STEPS_PER_EPOCH}."
                )


            expected_steps = (
                epoch
                *
                EXPECTED_OPTIMIZER_STEPS_PER_EPOCH
            )


            if (
                optimizer_steps_completed
                !=
                expected_steps
            ):

                raise RuntimeError(
                    f"Epoch {epoch}: cumulative optimizer steps "
                    f"{optimizer_steps_completed}; expected {expected_steps}."
                )


            sec = (
                time.time()
                -
                epoch_t0
            )


            n = max(
                count,
                1
            )


            history[
                "epoch"
            ].append(
                epoch
            )


            for key in (
                "data",
                "physics",
                "total",
            ):

                history[
                    key
                ].append(
                    sums[
                        key
                    ]
                    /
                    n
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


            peak_gib = (
                torch.cuda
                .max_memory_allocated()
                /
                1024
                **
                3
            )


            history[
                "peak_allocated_GiB"
            ].append(
                float(
                    peak_gib
                )
            )


            (
                recovery_path_saved,
                recovery_sha,
            ) = (
                save_recovery(
                    model,
                    optimizer,
                    history,
                    epoch,
                    optimizer_steps_completed,
                )
            )


            print(
                f"[COMP-CUDA-008] "
                f"Epoch {epoch:04d}/{TARGET_EPOCHS} "
                f"| Data "
                f"{history['data'][-1]:.3e} "
                f"| Phys "
                f"{history['physics'][-1]:.3e} "
                f"| Total "
                f"{history['total'][-1]:.3e} "
                f"| {sec/60.0:.2f} min/epoch "
                f"| Peak {peak_gib:.2f} GiB "
                f"| steps "
                f"{optimizer_steps_completed}/"
                f"{EXPECTED_TARGET_OPTIMIZER_STEPS} "
                f"| recovery "
                f"{recovery_path_saved.name} "
                f"| recoverySHA "
                f"{recovery_sha[:12]}... "
                f"| session "
                f"{(time.time()-session_t0)/3600.0:.2f} h"
            )


    finally:

        (
            B2S
            .local_recurrent_derivatives_create_graph
        ) = (
            original_engine
        )


    return (
        model,
        optimizer,
        history,
        optimizer_steps_completed,
    )


# =============================================================================
# Finalization
# =============================================================================

def finalize(
    model,
    history,
    optimizer_steps_completed,
):

    gate(
        "final_history_800_epochs",
        len(
            history[
                "epoch"
            ]
        )
        ==
        TARGET_EPOCHS,
    )

    gate(
        "final_epoch_exact_800",
        history[
            "epoch"
        ][
            -1
        ]
        ==
        TARGET_EPOCHS,
    )

    gate(
        "final_optimizer_steps_1600",
        optimizer_steps_completed
        ==
        EXPECTED_TARGET_OPTIMIZER_STEPS,
    )

    gate(
        "final_model_parameters_finite",
        model_finite(
            model
        ),
    )


    final_state_hash = state_tensor_hash(
        model.state_dict()
    )


    final_payload = {
        "experiment":
            EXPERIMENT,

        "milestone":
            MILESTONE,

        "status":
            STATUS_COMPLETE,

        "runner_sha256":
            RUNNER_SHA,

        "config_sha256":
            CONFIG_SHA,

        "CUDA8J_architecture_contract_sha256":
            EXPECTED[
                "CUDA8J_ARCHITECTURE"
            ],

        "CUDA8J_loss_contract_sha256":
            EXPECTED[
                "CUDA8J_LOSS"
            ],

        "CUDA8J_training_contract_sha256":
            EXPECTED[
                "CUDA8J_TRAINING"
            ],

        "CUDA8J_certification_contract_sha256":
            EXPECTED[
                "CUDA8J_CERTIFICATION"
            ],

        "dataset_sha256":
            EXPECTED[
                "dataset"
            ],

        "COMP007_initialization_sha256":
            EXPECTED[
                "COMP007"
            ],

        "normalization_sha256":
            EXPECTED[
                "CUDA8BR_NORMALIZATION"
            ],

        "completed_epoch":
            TARGET_EPOCHS,

        "optimizer_steps_completed":
            optimizer_steps_completed,

        "model_state_tensor_sha256":
            final_state_hash,

        "model_state_dict":
            model.state_dict(),

        "original_holdout_evaluated":
            False,

        "DEV_loaded":
            False,

        "blind_CERT_loaded":
            False,

        "OOD_used":
            False,

        "TOF_used":
            False,

        "Stage2_certified":
            False,

        "B3_authorized":
            False,
    }


    if FINAL_CHECKPOINT.exists():

        existing = torch.load(
            FINAL_CHECKPOINT,
            map_location="cpu",
            weights_only=False,
        )


        gate(
            "existing_final_experiment",
            existing[
                "experiment"
            ]
            ==
            EXPERIMENT,
        )

        gate(
            "existing_final_runner_SHA",
            existing[
                "runner_sha256"
            ]
            ==
            RUNNER_SHA,
        )

        gate(
            "existing_final_epoch_800",
            int(
                existing[
                    "completed_epoch"
                ]
            )
            ==
            TARGET_EPOCHS,
        )

        gate(
            "existing_final_state_tensor_SHA",
            existing[
                "model_state_tensor_sha256"
            ]
            ==
            final_state_hash,
        )

    else:

        torch_save_atomic(
            FINAL_CHECKPOINT,
            final_payload,
        )


    final_checkpoint_sha = sha256(
        FINAL_CHECKPOINT
    )


    gate(
        "final_recovery_E0800_exists",
        recovery_path(
            TARGET_EPOCHS
        ).exists(),
    )


    recovery800_sha = sha256(
        recovery_path(
            TARGET_EPOCHS
        )
    )


    history_sha = sha256(
        HISTORY
    )


    manifest = {
        "experiment":
            EXPERIMENT,

        "milestone":
            MILESTONE,

        "status":
            STATUS_COMPLETE,

        "runner_sha256":
            RUNNER_SHA,

        "config_sha256":
            CONFIG_SHA,

        "CUDA8J_source_sha256":
            EXPECTED[
                "CUDA8J_SOURCE"
            ],

        "CUDA8J_architecture_sha256":
            EXPECTED[
                "CUDA8J_ARCHITECTURE"
            ],

        "CUDA8J_loss_sha256":
            EXPECTED[
                "CUDA8J_LOSS"
            ],

        "CUDA8J_training_sha256":
            EXPECTED[
                "CUDA8J_TRAINING"
            ],

        "CUDA8J_certification_sha256":
            EXPECTED[
                "CUDA8J_CERTIFICATION"
            ],

        "CUDA8J_decision_sha256":
            EXPECTED[
                "CUDA8J_DECISION"
            ],

        "dataset_sha256":
            EXPECTED[
                "dataset"
            ],

        "COMP007_initialization_sha256":
            EXPECTED[
                "COMP007"
            ],

        "normalization_sha256":
            EXPECTED[
                "CUDA8BR_NORMALIZATION"
            ],

        "history_sha256":
            history_sha,

        "final_checkpoint_sha256":
            final_checkpoint_sha,

        "final_model_state_tensor_sha256":
            final_state_hash,

        "recovery_E0800_sha256":
            recovery800_sha,

        "completed_epoch":
            TARGET_EPOCHS,

        "optimizer_steps_completed":
            optimizer_steps_completed,

        "original_holdout_evaluated":
            False,

        "DEV_loaded":
            False,

        "blind_CERT_loaded":
            False,

        "OOD_used":
            False,

        "TOF_used":
            False,

        "Stage2_certified":
            False,

        "B3_authorized":
            False,
    }


    write_json_atomic(
        MANIFEST,
        manifest,
    )


    manifest_sha = sha256(
        MANIFEST
    )


    summary = {
        "milestone":
            MILESTONE,

        "experiment":
            EXPERIMENT,

        "status":
            STATUS_COMPLETE,

        "runner_sha256":
            RUNNER_SHA,

        "config_sha256":
            CONFIG_SHA,

        "history_sha256":
            history_sha,

        "checkpoint_sha256":
            final_checkpoint_sha,

        "model_state_tensor_sha256":
            final_state_hash,

        "manifest_sha256":
            manifest_sha,

        "recovery_E0800_sha256":
            recovery800_sha,

        "completed_epochs":
            TARGET_EPOCHS,

        "optimizer_steps_completed":
            optimizer_steps_completed,

        "final_training_losses": {
            "data":
                history[
                    "data"
                ][
                    -1
                ],

            "physics":
                history[
                    "physics"
                ][
                    -1
                ],

            "total":
                history[
                    "total"
                ][
                    -1
                ],
        },

        "original_holdout_evaluated":
            False,

        "DEV_loaded":
            False,

        "blind_CERT_loaded":
            False,

        "production_checkpoint_authority":
            "FINAL_COMPLETED_EPOCH_800",

        "development_cycle_closed":
            True,

        "Stage2_certified":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2CUDA8L — one-time blind Stage-2 certification "
                "of frozen COMP008 against COMP004/005/007"
            ),
    }


    write_json_atomic(
        SUMMARY,
        summary,
    )


    summary_sha = sha256(
        SUMMARY
    )


    handoff = f"""# PAD-Stream V16E-1B2CUDA8K

## Status

`{STATUS_COMPLETE}`

## Experiment

`{EXPERIMENT}`

## Training completion

- 800 completed epochs
- 1600 optimizer steps
- exact frozen COMP007 model-state initialization
- fresh Adam optimizer state
- learning rate 1e-4
- CUDA3 K=64 higher-order derivative engine
- microbatch 1024
- logical chunks 8192 + 3328
- bounded-monotone COMP008 output
- equal-Nc normalized corrected conservative physics
- smooth inlet residual weighting:
  `w_raw = 1 + 3*exp(-(xi/0.16)^2)`
- inlet weights normalized to mean 1 per profile
- no BC loss
- no tip loss
- no anchor loss
- no monotonicity loss
- no bounds penalty

## Firewall

The original source-native holdout was NOT evaluated.

The new DEV dataset was NOT loaded.

The blind CERT dataset was NOT loaded or scientifically inspected.

No OOD data were used.

No TOF data were used.

No checkpoint selection or early stopping occurred.

The final completed epoch 800 is the frozen production authority.

## Hashes

CUDA8K runner SHA-256:

`{RUNNER_SHA}`

CUDA8J training-contract SHA-256:

`{EXPECTED["CUDA8J_TRAINING"]}`

Config SHA-256:

`{CONFIG_SHA}`

History SHA-256:

`{history_sha}`

Final checkpoint SHA-256:

`{final_checkpoint_sha}`

Final model-state tensor SHA-256:

`{final_state_hash}`

Recovery E0800 SHA-256:

`{recovery800_sha}`

Manifest SHA-256:

`{manifest_sha}`

Summary SHA-256:

`{summary_sha}`

## Stage-2 status

Production training completion does NOT itself certify Stage 2.

Stage 2 remains uncertified until the single-use blind CUDA8L evaluation.

B3 remains blocked.

## Next

`V16E-1B2CUDA8L — one-time blind Stage-2 certification of frozen COMP008 against COMP004/005/007`
"""


    HANDOFF.write_text(
        handoff,
        encoding="utf-8",
    )


    handoff_sha = sha256(
        HANDOFF
    )


    return {
        "history_sha":
            history_sha,

        "checkpoint_sha":
            final_checkpoint_sha,

        "model_state_tensor_sha":
            final_state_hash,

        "recovery800_sha":
            recovery800_sha,

        "manifest_sha":
            manifest_sha,

        "summary_sha":
            summary_sha,

        "handoff_sha":
            handoff_sha,
    }


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":

    print()
    print(
        "RUNNER AUTHORITY"
    )

    print(
        "  runner SHA            :",
        RUNNER_SHA,
    )

    print(
        "  CUDA8J architecture SHA:",
        EXPECTED[
            "CUDA8J_ARCHITECTURE"
        ],
    )

    print(
        "  CUDA8J loss SHA        :",
        EXPECTED[
            "CUDA8J_LOSS"
        ],
    )

    print(
        "  CUDA8J training SHA    :",
        EXPECTED[
            "CUDA8J_TRAINING"
        ],
    )

    print(
        "  COMP007 init SHA       :",
        EXPECTED[
            "COMP007"
        ],
    )

    print(
        "  COMP007 state SHA      :",
        EXPECTED[
            "COMP007_STATE"
        ],
    )

    print(
        "  normalization SHA      :",
        EXPECTED[
            "CUDA8BR_NORMALIZATION"
        ],
    )


    (
        model,
        optimizer,
        history,
        optimizer_steps_completed,
    ) = train_or_resume()


    artifacts = finalize(
        model,
        history,
        optimizer_steps_completed,
    )


    # Frozen authorities must remain unchanged.
    gate(
        "COMP007_artifact_unchanged",
        sha256(
            COMP007
        )
        ==
        EXPECTED[
            "COMP007"
        ],
    )

    gate(
        "DEV_artifact_unchanged",
        sha256(
            DEV_DATASET
        )
        ==
        EXPECTED[
            "DEV_DATASET"
        ],
    )

    gate(
        "BLIND_CERT_artifact_unchanged",
        sha256(
            BLIND_CERT
        )
        ==
        EXPECTED[
            "BLIND_CERT"
        ],
    )


    print()
    print(
        "="
        *
        110
    )

    print(
        "CUDA8K COMP008 PRODUCTION TRAINING COMPLETE"
    )

    print(
        "="
        *
        110
    )

    print(
        "Runner SHA            :",
        RUNNER_SHA,
    )

    print(
        "History SHA           :",
        artifacts[
            "history_sha"
        ],
    )

    print(
        "Checkpoint SHA        :",
        artifacts[
            "checkpoint_sha"
        ],
    )

    print(
        "Model-state tensor SHA:",
        artifacts[
            "model_state_tensor_sha"
        ],
    )

    print(
        "Recovery E0800 SHA    :",
        artifacts[
            "recovery800_sha"
        ],
    )

    print(
        "Manifest SHA          :",
        artifacts[
            "manifest_sha"
        ],
    )

    print(
        "Summary SHA           :",
        artifacts[
            "summary_sha"
        ],
    )

    print(
        "Handoff SHA           :",
        artifacts[
            "handoff_sha"
        ],
    )

    print()

    print(
        "ORIGINAL HOLDOUT EVALUATED : NO"
    )

    print(
        "DEV LOADED                 : NO"
    )

    print(
        "BLIND CERT LOADED          : NO"
    )

    print(
        "STAGE 2 CERTIFIED          : NO"
    )

    print(
        "B3 AUTHORIZED              : NO"
    )

    print()

    print(
        "NEXT: V16E-1B2CUDA8L — one-time blind Stage-2 certification "
        "of frozen COMP008 against COMP004/005/007"
    )
