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


# =============================================================================
# PAD-Stream V16E-1B2CUDA8D
#
# COMP006 Authorized Production Training Runner
#
# AUTHORITY
# ---------
# Executes ONLY the frozen CUDA8C production contract.
#
# Scientific changes relative to frozen COMP005:
#   1. exact COMP005 warm start;
#   2. deterministic differentiable injector/tip boundary lift;
#   3. corrected conservative physics balanced across frozen Nc strata;
#   4. L1 positive-slope monotonicity penalty.
#
# No holdout evaluation occurs anywhere in this runner.
# No OOD.
# No TOF.
# B3 remains blocked.
#
# Recovery authority:
#   only a successfully completed epoch is resumable authority.
# =============================================================================


MILESTONE = "V16E-1B2CUDA8D"
EXPERIMENT = "V16E-BLREP-COMP-CUDA-006"

STATUS_RUNNING = (
    "V16E1B2CUDA8D_COMP006_AUTHORIZED_PRODUCTION_TRAINING_RUNNING_"
    "CUDA8C_CONTRACT_BOUND_WARM_START_FROZEN_COMP005_FRESH_ADAM_"
    "HARD_BOUNDARY_LIFT_EQUAL_NC_CORRECTED_PHYSICS_L1_MONOTONICITY_"
    "HOLDOUT_FORBIDDEN_NO_OOD_NO_TOF_B3_BLOCKED"
)

STATUS_COMPLETE = (
    "V16E1B2CUDA8D_COMP006_AUTHORIZED_PRODUCTION_TRAINING_COMPLETE_"
    "CUDA8C_CONTRACT_SATISFIED_WARM_START_FROZEN_COMP005_"
    "800_EPOCHS_1600_OPTIMIZER_STEPS_COMPLETE_"
    "HARD_BOUNDARY_LIFT_EQUAL_NC_CORRECTED_PHYSICS_L1_MONOTONICITY_"
    "FINAL_EPOCH_800_AUTHORITY_NO_HOLDOUT_EVALUATION_NO_OOD_NO_TOF_"
    "STAGE2_POSTTRAINING_CLOSURE_REQUIRED_B3_REMAINS_BLOCKED"
)


# =============================================================================
# Paths
# =============================================================================

REPO = Path("/content/PAD-Stream")
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")

RUN005 = DRIVE / "runs" / "V16E-BLREP-COMP-CUDA-005"

DATASET = (
    DRIVE
    / "datasets"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)

COMP005 = (
    RUN005
    / "V16E_BLREP_COMP_CUDA_005.pt"
)

RECOVERY005_E0800 = (
    RUN005
    / "recovery"
    / "V16E_BLREP_COMP_CUDA_005_RECOVERY_E0800.pt"
)

CUDA6 = (
    REPO
    / "PAD_Stream_V16E1B2CUDA6_A100_COMP_CUDA_005_Authorized_Production_Runner.py"
)

CUDA8A_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8A_TARGETED_STAGE2_REPAIR_PROTOCOL_FREEZE"
)

CUDA8A_PROTOCOL = (
    CUDA8A_ROOT
    / "V16E1B2CUDA8A_Targeted_Stage2_Repair_Protocol.json"
)

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

CUDA8BR_IMPLEMENTATION = (
    CUDA8BR_ROOT
    / "V16E1B2CUDA8BR_COMP006_Implementation_Preflight.json"
)

CUDA8C_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8C_COMP006_Production_Training_Contract_Authorization_Freeze.py"
)

CUDA8C_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8C_COMP006_PRODUCTION_TRAINING_AUTHORIZATION"
)

CUDA8C_CONTRACT = (
    CUDA8C_ROOT
    / "V16E1B2CUDA8C_COMP006_Production_Training_Contract.json"
)

CUDA8C_SUMMARY = (
    CUDA8C_ROOT
    / "PAD_Stream_V16E1B2CUDA8C_Summary.json"
)

CUDA8C_HANDOFF = (
    CUDA8C_ROOT
    / "V16E1B2CUDA8C_Handoff.md"
)


# Persistent COMP006 run root.
RUN_ROOT = (
    DRIVE
    / "runs"
    / EXPERIMENT
)

RECOVERY_DIR = RUN_ROOT / "recovery"

RECOVERY_LATEST = (
    RECOVERY_DIR
    / "V16E_BLREP_COMP_CUDA_006_RECOVERY_LATEST.json"
)

CONFIG = (
    RUN_ROOT
    / "V16E_BLREP_COMP_CUDA_006_CONFIG.json"
)

HISTORY = (
    RUN_ROOT
    / "V16E_BLREP_COMP_CUDA_006_HISTORY.json"
)

FINAL_CHECKPOINT = (
    RUN_ROOT
    / "V16E_BLREP_COMP_CUDA_006.pt"
)

MANIFEST = (
    RUN_ROOT
    / "V16E_BLREP_COMP_CUDA_006_MANIFEST.json"
)

SUMMARY = (
    RUN_ROOT
    / "PAD_Stream_V16E1B2CUDA8D_Summary.json"
)

HANDOFF = (
    RUN_ROOT
    / "V16E1B2CUDA8D_Handoff.md"
)

RUN_ROOT.mkdir(parents=True, exist_ok=True)
RECOVERY_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Frozen hashes
# =============================================================================

EXPECTED = {
    "dataset":
        "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c",

    "COMP005":
        "aaca2ae60d7a789bf6d3d2a177d1b3b5188181809597b1be6901ed7473e0906f",

    "RECOVERY005_E0800":
        "fbdbf6b7bff0b22625e7dbcd09500c258c6deeeec6ed4f846407f6e927435157",

    "CUDA6":
        "385e18b64ebf068a06e5daec11449e3700f69ad743627d4520905f273bf7c552",

    "CUDA8A_PROTOCOL":
        "cf7b29c6b93afb7fcbef8fbb3d4e1106d7cd77ddd46469de611af48431f445b6",

    "CUDA8BR_NORMALIZATION":
        "ccd0e61fc8fc8f73890e83f537bb047aaa5f408c8f4125209cc36d0b79df3549",

    "CUDA8BR_IMPLEMENTATION":
        "0814f14b8a7cf19b754983d26a7c6c19e4c59d5275c72c7e90d6d2a5ceaf3a1c",

    "CUDA8C_SOURCE":
        "b91a4b0e9143c85b9f01ff13f59ccaf90cb1abf8f6afd1f36041738db6e0f08d",

    "CUDA8C_CONTRACT":
        "051381da0810dfc235700daded6fca51e8c47fa4080c4ae588b4e0d71dce3a51",

    "CUDA8C_SUMMARY":
        "42ee586b32e99b34eeceb8b779e1e693b6b7e206a73df7cd5162f8712c2e08c3",

    "CUDA8C_HANDOFF":
        "c86cc681071b34d64031864785ee7efe8615aa4c3eb44dc7d59867cf58751311",

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
# Exact CUDA8C production contract
# =============================================================================

SEED = 1337

NC_VALUES = (
    0.00,
    0.05,
    0.10,
    0.20,
    0.30,
)

NC_COUNT = len(NC_VALUES)

N_TOTAL = 14400
N_TRAIN = 11520
N_HOLDOUT = 2880

TARGET_EPOCHS = 800

LR = 1.0e-3

ADOPTED_CHUNK = 64
MICROBATCH = 1024
LOGICAL_BATCH = 8192
SECOND_LOGICAL_CHUNK = 3328

EXPECTED_MICROBATCHES_PER_EPOCH = 12
EXPECTED_OPTIMIZER_STEPS_PER_EPOCH = 2
EXPECTED_TARGET_OPTIMIZER_STEPS = 1600

LAMBDA_DATA = 1.0

LAMBDA_PHYS = 8.537526059395e-04

LAMBDA_BC = 5.0
LAMBDA_TIP = 5.0
LAMBDA_ANCHOR = 10.0
LAMBDA_MONO = 0.2


# =============================================================================
# Helpers
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def array_sha256(x) -> str:
    a = np.ascontiguousarray(
        np.asarray(
            x,
            dtype=np.int64,
        )
    )

    return hashlib.sha256(
        a.tobytes(order="C")
    ).hexdigest()


def state_tensor_hash(state) -> str:
    h = hashlib.sha256()

    for name in sorted(state.keys()):
        t = (
            state[name]
            .detach()
            .cpu()
            .contiguous()
        )

        h.update(
            name.encode("utf-8")
        )

        h.update(
            str(t.dtype).encode("utf-8")
        )

        h.update(
            str(tuple(t.shape)).encode("utf-8")
        )

        h.update(
            t.numpy().tobytes()
        )

    return h.hexdigest()


def gate(name, condition):
    ok = bool(condition)

    print(
        f"[{'PASS' if ok else 'FAIL'}] {name}"
    )

    if not ok:
        raise RuntimeError(
            f"CUDA8D gate failed: {name}"
        )


def finite_tensor(x) -> bool:
    return bool(
        torch.isfinite(x)
        .all()
        .item()
    )


def model_finite(model) -> bool:
    return all(
        finite_tensor(p)
        for p in model.parameters()
    )


def native_nc_mask_torch(values, nc):
    target = torch.as_tensor(
        nc,
        dtype=values.dtype,
        device=values.device,
    )

    return values == target


def jsonable(obj):
    if isinstance(obj, dict):
        return {
            str(k): jsonable(v)
            for k, v in obj.items()
        }

    if isinstance(obj, (list, tuple)):
        return [
            jsonable(v)
            for v in obj
        ]

    if isinstance(obj, np.ndarray):
        return jsonable(
            obj.tolist()
        )

    if isinstance(obj, np.generic):
        return jsonable(
            obj.item()
        )

    if isinstance(obj, torch.Tensor):
        return jsonable(
            obj.detach()
            .cpu()
            .numpy()
        )

    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError(
                "Refusing to serialize non-finite float."
            )

    return obj


def write_json_atomic(path: Path, obj):
    tmp = path.with_suffix(
        path.suffix + ".tmp"
    )

    tmp.write_text(
        json.dumps(
            jsonable(obj),
            indent=2,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    os.replace(
        tmp,
        path,
    )


def torch_save_atomic(path: Path, obj):
    tmp = path.with_suffix(
        path.suffix + ".tmp"
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
        "peak_allocated_GiB": [],
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
        "bc_inj",
        "bc_tip",
        "anchor",
        "mono",
        "total",
        "epoch_seconds",
        "optimizer_steps_completed",
        "peak_allocated_GiB",
    }

    if set(history.keys()) != required:
        raise RuntimeError(
            "Recovery history keys do not match CUDA8D contract."
        )

    n = len(
        history["epoch"]
    )

    if n != completed_epoch:
        raise RuntimeError(
            "Recovery history length does not equal completed epoch."
        )

    for key in required:
        if len(history[key]) != n:
            raise RuntimeError(
                f"Recovery history length mismatch for {key}."
            )

    if completed_epoch > 0:
        if history["epoch"][-1] != completed_epoch:
            raise RuntimeError(
                "Recovery history final epoch is inconsistent."
            )

        if (
            history[
                "optimizer_steps_completed"
            ][-1]
            != optimizer_steps_completed
        ):
            raise RuntimeError(
                "Recovery history optimizer-step count is inconsistent."
            )


# =============================================================================
# Banner
# =============================================================================

print("=" * 110)
print("PAD-Stream V16E-1B2CUDA8D")
print("COMP006 Authorized Production Training Runner")
print("=" * 110)

print()
print("CUDA8C-authorized production training only.")
print("HOLDOUT EVALUATION: FORBIDDEN.")
print("No OOD.")
print("No TOF.")
print("B3 remains blocked.")
print()


# =============================================================================
# Authority gates
# =============================================================================

AUTHORITY = {
    "dataset":
        DATASET,

    "COMP005":
        COMP005,

    "RECOVERY005_E0800":
        RECOVERY005_E0800,

    "CUDA6":
        CUDA6,

    "CUDA8A_PROTOCOL":
        CUDA8A_PROTOCOL,

    "CUDA8BR_NORMALIZATION":
        CUDA8BR_NORMALIZATION,

    "CUDA8BR_IMPLEMENTATION":
        CUDA8BR_IMPLEMENTATION,

    "CUDA8C_SOURCE":
        CUDA8C_SOURCE,

    "CUDA8C_CONTRACT":
        CUDA8C_CONTRACT,

    "CUDA8C_SUMMARY":
        CUDA8C_SUMMARY,

    "CUDA8C_HANDOFF":
        CUDA8C_HANDOFF,
}


print("FROZEN AUTHORITY GATES")

for name, path in AUTHORITY.items():
    gate(
        f"{name}_exists",
        path.exists(),
    )

    gate(
        f"{name}_SHA_exact",
        sha256(path)
        ==
        EXPECTED[name],
    )


COMP005_SHA_BEFORE = sha256(
    COMP005
)


# =============================================================================
# Self / contract
# =============================================================================

RUNNER_PATH = Path(__file__)
RUNNER_SHA = sha256(
    RUNNER_PATH
)

contract8c = json.loads(
    CUDA8C_CONTRACT.read_text(
        encoding="utf-8"
    )
)


print()
print("CUDA8C CONTRACT GATES")

gate(
    "experiment_exact",
    contract8c[
        "experiment"
    ]
    ==
    EXPERIMENT,
)

gate(
    "training_authorized",
    contract8c[
        "COMP006_production_training_authorized"
    ] is True,
)

gate(
    "warm_start_COMP005",
    contract8c[
        "initialization"
    ][
        "model_weights"
    ]
    ==
    "EXACT_FROZEN_COMP005",
)

gate(
    "fresh_optimizer_state",
    contract8c[
        "initialization"
    ][
        "optimizer_state"
    ]
    ==
    "FRESH",
)

gate(
    "final_epoch_authority",
    contract8c[
        "checkpoint_selection"
    ][
        "authority"
    ]
    ==
    "FINAL_COMPLETED_EPOCH_800",
)

gate(
    "holdout_evaluation_forbidden",
    contract8c[
        "training_data"
    ][
        "holdout_evaluation_during_training"
    ] is False,
)

gate(
    "holdout_model_selection_forbidden",
    contract8c[
        "training_data"
    ][
        "holdout_used_for_model_selection"
    ] is False,
)

gate(
    "no_early_stopping",
    contract8c[
        "checkpoint_selection"
    ][
        "early_stopping"
    ] is False,
)

gate(
    "no_OOD",
    contract8c[
        "training_data"
    ][
        "OOD_used"
    ] is False,
)

gate(
    "no_TOF",
    contract8c[
        "training_data"
    ][
        "TOF_used"
    ] is False,
)


# =============================================================================
# Runtime
# =============================================================================

print()
print("RUNTIME GATES")

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
    torch.cuda.get_device_properties(
        0
    ).total_memory
)

gpu_total_gib = (
    gpu_total_bytes
    / 1024 ** 3
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

# CUDA8C measured ~43.1 GiB peak. Fail closed on 40-GB-class devices.
gate(
    "A100_memory_at_least_70GiB",
    gpu_total_gib
    >= 70.0,
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

spec = importlib.util.spec_from_file_location(
    "cuda6_for_cuda8d",
    CUDA6,
)

C = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    C
)


B2S = C.import_module(
    C.B2S_SOURCE,
    "cuda8d_B2S",
)

M = C.import_module(
    B2S.BASE_RUNNER,
    "cuda8d_M",
)

J = C.import_module(
    B2S.B2J_SOURCE,
    "cuda8d_J",
)

CUDA3 = C.import_module(
    C.CUDA3_SOURCE,
    "cuda8d_CUDA3",
)


print()
print("SCIENTIFIC SOURCE GATES")

gate(
    "B2S_SHA_exact",
    sha256(
        Path(
            B2S.__file__
        )
    )
    ==
    EXPECTED["B2S"],
)

gate(
    "BASE_M_SHA_exact",
    sha256(
        Path(
            M.__file__
        )
    )
    ==
    EXPECTED["BASE_M"],
)

gate(
    "ETA_J_SHA_exact",
    sha256(
        Path(
            J.__file__
        )
    )
    ==
    EXPECTED["ETA_J"],
)

gate(
    "CUDA3_SHA_exact",
    sha256(
        Path(
            CUDA3.__file__
        )
    )
    ==
    EXPECTED["CUDA3"],
)


print()
print("PRODUCTION GEOMETRY GATES")

gate(
    "CUDA3_chunk64",
    ADOPTED_CHUNK
    == 64,
)

gate(
    "microbatch1024",
    MICROBATCH
    == 1024,
)

gate(
    "logical8192",
    LOGICAL_BATCH
    == 8192,
)

gate(
    "second_chunk3328",
    SECOND_LOGICAL_CHUNK
    == 3328,
)

gate(
    "twelve_microbatches",
    EXPECTED_MICROBATCHES_PER_EPOCH
    == 12,
)

gate(
    "two_optimizer_steps",
    EXPECTED_OPTIMIZER_STEPS_PER_EPOCH
    == 2,
)

gate(
    "eight_hundred_epochs",
    TARGET_EPOCHS
    == 800,
)

gate(
    "sixteen_hundred_steps",
    EXPECTED_TARGET_OPTIMIZER_STEPS
    == 1600,
)


# =============================================================================
# Dataset and exact frozen split
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
        for key in required
        if key not in d.files
    ]

    gate(
        "dataset_required_arrays",
        len(missing)
        == 0,
    )

    arrays = tuple(
        np.array(
            d[key],
            copy=True,
        )
        for key in required
    )


(
    xi_all,
    Sw_all,
    p11_all,
    _tD_all,
    ai_all,
    at_all,
) = arrays


gate(
    "dataset_profiles_14400",
    len(
        xi_all
    )
    ==
    N_TOTAL,
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
print("SPLIT FIREWALL GATES")

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


# =============================================================================
# Frozen Nc normalization
# =============================================================================

norm_artifact = json.loads(
    CUDA8BR_NORMALIZATION.read_text(
        encoding="utf-8"
    )
)


normalizer = {}
profile_counts = {}

T_INTERIOR = (
    xi_all.shape[1]
    - 2
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
        and mse > 0.0,
    )

    gate(
        f"Nc_{nc}_residual_count_divisible",
        residual_count
        % T_INTERIOR
        ==
        0,
    )

    normalizer[nc] = mse

    profile_counts[nc] = (
        residual_count
        // T_INTERIOR
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
# Exact COMP006 model
# =============================================================================

BaseEtaModel = J.build_eta_model_class(
    M
)


class COMP006LiftedModel(BaseEtaModel):

    def forward(
        self,
        xi_seq,
        p11_phys,
    ):
        S_raw = super().forward(
            xi_seq,
            p11_phys,
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
            - sor
        )

        S0 = S_raw[
            :,
            0:1,
            :
        ]

        S1 = S_raw[
            :,
            -1:,
            :
        ]

        S_hat = (
            S_raw

            + (
                1.0
                - xi_seq
            )
            * (
                S_inj
                - S0
            )

            + xi_seq
            * (
                Sw_star
                - S1
            )
        )

        return S_hat


# =============================================================================
# Exact COMP006 objective
# =============================================================================

def comp006_loss(
    model,
    xi,
    Sw,
    p11,
    ai,
    at,
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


    # Data
    Ldata = torch.mean(
        (
            S_hat
            - Sw
        )
        ** 2
    )


    # Corrected physics: fixed global per-profile stratum weights.
    profile_residual_mse = (
        torch.mean(
            residual
            ** 2,
            dim=(
                1,
                2,
            ),
        )
    )

    nc = p11[
        :,
        10
    ]

    physics_weighted_sum = (
        torch.zeros(
            (),
            device=xi.device,
            dtype=xi.dtype,
        )
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
            + mask.to(
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
                    * float(
                        profile_counts[
                            val
                        ]
                    )
                )
            )

            physics_weighted_sum = (
                physics_weighted_sum

                + global_profile_weight
                * torch.sum(
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
            "Each COMP006 training profile must map to "
            "exactly one frozen Nc stratum."
        )


    Lphys = (
        physics_weighted_sum
        /
        float(
            xi.shape[0]
        )
    )


    # Hard-boundary audit.
    Lbc = M.injector_bc_loss(
        S_hat,
        p11,
    )

    Ltip = M.tip_bc_loss(
        S_hat,
        p11,
    )


    # Frozen anchors.
    Lanchor = M.anchor_loss(
        S_hat,
        ai,
        at,
    )


    # L1 positive-slope monotonicity repair.
    dS = (
        S_hat[
            :,
            1:,
            :
        ]
        -
        S_hat[
            :,
            :-1,
            :
        ]
    )

    Lmono = torch.mean(
        torch.relu(
            dS
        )
    )


    total = (
        LAMBDA_DATA
        * Ldata

        + LAMBDA_PHYS
        * Lphys

        + LAMBDA_BC
        * Lbc

        + LAMBDA_TIP
        * Ltip

        + LAMBDA_ANCHOR
        * Lanchor

        + LAMBDA_MONO
        * Lmono
    )


    parts = {
        "data":
            Ldata,

        "physics":
            Lphys,

        "bc_inj":
            Lbc,

        "bc_tip":
            Ltip,

        "anchor":
            Lanchor,

        "mono":
            Lmono,

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


    model = COMP006LiftedModel().to(
        device
    )


    ckpt005 = torch.load(
        COMP005,
        map_location="cpu",
        weights_only=False,
    )


    result = model.load_state_dict(
        ckpt005[
            "model_state_dict"
        ],
        strict=True,
    )


    gate(
        "COMP005_warm_start_strict",
        len(
            result.missing_keys
        )
        ==
        0
        and len(
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
# Recovery
# =============================================================================

def recovery_path(epoch: int) -> Path:
    return (
        RECOVERY_DIR
        / f"V16E_BLREP_COMP_CUDA_006_RECOVERY_E{epoch:04d}.pt"
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


def restore_rng_state(payload):
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
        * EXPECTED_OPTIMIZER_STEPS_PER_EPOCH
    )

    if (
        optimizer_steps_completed
        != expected_steps
    ):
        raise RuntimeError(
            "Cannot save recovery: optimizer-step count "
            "does not match completed epoch."
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

        "CUDA8C_contract_sha256":
            EXPECTED[
                "CUDA8C_CONTRACT"
            ],

        "dataset_sha256":
            EXPECTED[
                "dataset"
            ],

        "COMP005_initialization_sha256":
            EXPECTED[
                "COMP005"
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

            "lambda_bc":
                LAMBDA_BC,

            "lambda_tip":
                LAMBDA_TIP,

            "lambda_anchor":
                LAMBDA_ANCHOR,

            "lambda_mono_L1":
                LAMBDA_MONO,
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
                "V16E_BLREP_COMP_CUDA_006_RECOVERY_E*.pt"
            )
        )

        if orphaned:
            raise RuntimeError(
                "COMP006 recovery checkpoints exist but "
                "RECOVERY_LATEST.json is missing. "
                "Failing closed rather than guessing which "
                "completed epoch is authoritative."
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
        "recovery_CUDA8C_contract_SHA",
        recovery[
            "CUDA8C_contract_sha256"
        ]
        ==
        EXPECTED[
            "CUDA8C_CONTRACT"
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
        "recovery_COMP005_initialization_SHA",
        recovery[
            "COMP005_initialization_sha256"
        ]
        ==
        EXPECTED[
            "COMP005"
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
        <= completed_epoch
        <= TARGET_EPOCHS,
    )

    gate(
        "recovery_optimizer_steps_exact",
        optimizer_steps_completed
        ==
        completed_epoch
        * EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
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
        and len(
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
# Freeze configuration before production starts
# =============================================================================

CONFIG_OBJECT = {
    "milestone":
        MILESTONE,

    "experiment":
        EXPERIMENT,

    "status":
        STATUS_RUNNING,

    "runner_sha256":
        RUNNER_SHA,

    "authorities": {
        name:
            EXPECTED[name]
        for name in (
            "dataset",
            "COMP005",
            "RECOVERY005_E0800",
            "CUDA6",
            "CUDA8A_PROTOCOL",
            "CUDA8BR_NORMALIZATION",
            "CUDA8BR_IMPLEMENTATION",
            "CUDA8C_SOURCE",
            "CUDA8C_CONTRACT",
            "CUDA8C_SUMMARY",
            "CUDA8C_HANDOFF",
            "B2S",
            "BASE_M",
            "ETA_J",
            "CUDA3",
            "train_idx",
            "holdout_idx",
        )
    },

    "initialization": {
        "model":
            "EXACT_FROZEN_COMP005",

        "optimizer":
            "FRESH_ADAM",

        "optimizer_momentum_transferred":
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
    },

    "geometry": {
        "derivative_engine":
            "CUDA3_CHUNKED_BATCHED_VJP",

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

    "loss": {
        "lambda_data":
            LAMBDA_DATA,

        "lambda_physics":
            LAMBDA_PHYS,

        "lambda_bc":
            LAMBDA_BC,

        "lambda_tip":
            LAMBDA_TIP,

        "lambda_anchor":
            LAMBDA_ANCHOR,

        "lambda_mono_L1":
            LAMBDA_MONO,

        "physics":
            "CORRECTED_CONSERVATIVE_EQUAL_NC_NORMALIZED",

        "boundary_lifting":
            True,

        "monotonicity":
            "L1_POSITIVE_SLOPE",
    },

    "firewall": {
        "holdout_evaluation_during_training":
            False,

        "holdout_checkpoint_selection":
            False,

        "early_stopping":
            False,

        "OOD":
            False,

        "TOF":
            False,

        "B3":
            False,
    },

    "checkpoint_authority":
        "FINAL_COMPLETED_EPOCH_800",
}


if CONFIG.exists():

    existing_config = json.loads(
        CONFIG.read_text(
            encoding="utf-8"
        )
    )

    gate(
        "existing_CONFIG_exact",
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
# Production training
# =============================================================================

def train_or_resume():

    model, optimizer, warm_start_hash = (
        build_model_optimizer()
    )


    recovery = load_recovery(
        model,
        optimizer,
    )


    if recovery is None:

        start_epoch = 1

        optimizer_steps_completed = 0

        history = empty_history()


        print()
        print("PRODUCTION START")

        print(
            "  mode                  : FRESH"
        )

        print(
            "  initialization        : FROZEN COMP005"
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


        print()
        print("PRODUCTION RESUME")

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
    print("PRODUCTION TRAINING CONTRACT")

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
        "  holdout profiles      :",
        N_HOLDOUT,
        "(NOT EVALUATED)",
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
        "  physics lambda        :",
        f"{LAMBDA_PHYS:.15e}",
    )

    print(
        "  mono L1 lambda        :",
        LAMBDA_MONO,
    )

    print(
        "  AMP                   : OFF"
    )

    print(
        "  TF32                  : OFF"
    )

    print(
        "  holdout evaluation    : FORBIDDEN"
    )


    if start_epoch > TARGET_EPOCHS:

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
        CUDA3.make_cuda3_chunked_batched_engine(
            ADOPTED_CHUNK
        )
    )

    original_engine = (
        B2S.local_recurrent_derivatives_create_graph
    )

    session_t0 = time.time()


    try:

        B2S.local_recurrent_derivatives_create_graph = (
            engine
        )

        model.train()


        for epoch in range(
            start_epoch,
            TARGET_EPOCHS
            + 1,
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
                    LOGICAL_BATCH,
                    SECOND_LOGICAL_CHUNK,
                ):

                    raise RuntimeError(
                        f"Unexpected logical chunk size "
                        f"{logical_n}."
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


                    with torch.backends.cudnn.flags(
                        enabled=False
                    ):

                        (
                            S_hat,
                            residual,
                            parts,
                        ) = (
                            comp006_loss(
                                model,
                                xi,
                                Sw,
                                p11,
                                ai,
                                at,
                            )
                        )


                    if not finite_tensor(
                        S_hat
                    ):

                        raise RuntimeError(
                            f"Epoch {epoch}: "
                            "nonfinite prediction."
                        )


                    if not finite_tensor(
                        residual
                    ):

                        raise RuntimeError(
                            f"Epoch {epoch}: "
                            "nonfinite corrected residual."
                        )


                    if not all(
                        finite_tensor(
                            v
                        )
                        for v
                        in parts.values()
                    ):

                        raise RuntimeError(
                            f"Epoch {epoch}: "
                            "nonfinite loss."
                        )


                    # Hard-boundary conditions are exact by construction.
                    if (
                        float(
                            parts[
                                "bc_inj"
                            ]
                            .detach()
                            .cpu()
                            .item()
                        )
                        >
                        1.0e-12
                    ):

                        raise RuntimeError(
                            f"Epoch {epoch}: "
                            "hard injector lift lost exactness."
                        )


                    if (
                        float(
                            parts[
                                "bc_tip"
                            ]
                            .detach()
                            .cpu()
                            .item()
                        )
                        >
                        1.0e-12
                    ):

                        raise RuntimeError(
                            f"Epoch {epoch}: "
                            "hard tip lift lost exactness."
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
                        * scale
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
                        f"Epoch {epoch}: "
                        "accumulated gradients are nonfinite."
                    )


                if (
                    accumulated[
                        "nonzero_gradient_tensor_count"
                    ]
                    <=
                    0
                ):

                    raise RuntimeError(
                        f"Epoch {epoch}: "
                        "all accumulated gradients are zero."
                    )


                optimizer.step()
                sync_cuda()


                optimizer_steps_completed += 1
                epoch_optimizer_steps += 1


                if not model_finite(
                    model
                ):

                    raise RuntimeError(
                        f"Epoch {epoch}: "
                        "model parameters became nonfinite."
                    )


                optimizer.zero_grad(
                    set_to_none=True
                )


            sync_cuda()


            if count != N_TRAIN:

                raise RuntimeError(
                    f"Epoch {epoch}: accepted "
                    f"{count} profiles; expected {N_TRAIN}."
                )


            if (
                epoch_microbatches
                !=
                EXPECTED_MICROBATCHES_PER_EPOCH
            ):

                raise RuntimeError(
                    f"Epoch {epoch}: executed "
                    f"{epoch_microbatches} microbatches; "
                    f"expected "
                    f"{EXPECTED_MICROBATCHES_PER_EPOCH}."
                )


            if (
                epoch_optimizer_steps
                !=
                EXPECTED_OPTIMIZER_STEPS_PER_EPOCH
            ):

                raise RuntimeError(
                    f"Epoch {epoch}: executed "
                    f"{epoch_optimizer_steps} optimizer steps; "
                    f"expected "
                    f"{EXPECTED_OPTIMIZER_STEPS_PER_EPOCH}."
                )


            expected_steps = (
                epoch
                * EXPECTED_OPTIMIZER_STEPS_PER_EPOCH
            )


            if (
                optimizer_steps_completed
                !=
                expected_steps
            ):

                raise RuntimeError(
                    f"Epoch {epoch}: cumulative optimizer steps "
                    f"{optimizer_steps_completed}; "
                    f"expected {expected_steps}."
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


            for key in (
                "data",
                "physics",
                "bc_inj",
                "bc_tip",
                "anchor",
                "mono",
                "total",
            ):

                history[
                    key
                ].append(
                    sums[
                        key
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


            peak_gib = (
                torch.cuda.max_memory_allocated()
                / 1024
                ** 3
            )


            history[
                "peak_allocated_GiB"
            ].append(
                float(
                    peak_gib
                )
            )


            recovery_path_saved, recovery_sha = (
                save_recovery(
                    model,
                    optimizer,
                    history,
                    epoch,
                    optimizer_steps_completed,
                )
            )


            print(
                f"[COMP-CUDA-006] "
                f"Epoch {epoch:04d}/{TARGET_EPOCHS} "
                f"| Data "
                f"{history['data'][-1]:.3e} "
                f"| Phys "
                f"{history['physics'][-1]:.3e} "
                f"| BC "
                f"{history['bc_inj'][-1]:.3e} "
                f"| Tip "
                f"{history['bc_tip'][-1]:.3e} "
                f"| Anchor "
                f"{history['anchor'][-1]:.3e} "
                f"| Mono "
                f"{history['mono'][-1]:.3e} "
                f"| Total "
                f"{history['total'][-1]:.3e} "
                f"| {sec/60.0:.2f} min/epoch "
                f"| Peak {peak_gib:.2f} GiB "
                f"| steps "
                f"{optimizer_steps_completed}/"
                f"{EXPECTED_TARGET_OPTIMIZER_STEPS} "
                f"| recovery "
                f"{recovery_path_saved.name} "
                f"| session "
                f"{(time.time()-session_t0)/3600.0:.2f} h"
            )


    finally:

        B2S.local_recurrent_derivatives_create_graph = (
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
        ][-1]
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

        "CUDA8C_contract_sha256":
            EXPECTED[
                "CUDA8C_CONTRACT"
            ],

        "dataset_sha256":
            EXPECTED[
                "dataset"
            ],

        "COMP005_initialization_sha256":
            EXPECTED[
                "COMP005"
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

        "holdout_evaluated":
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

        "dataset_sha256":
            EXPECTED[
                "dataset"
            ],

        "COMP005_initialization_sha256":
            EXPECTED[
                "COMP005"
            ],

        "CUDA8C_contract_sha256":
            EXPECTED[
                "CUDA8C_CONTRACT"
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

        "holdout_evaluated":
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
                ][-1],

            "physics":
                history[
                    "physics"
                ][-1],

            "bc_inj":
                history[
                    "bc_inj"
                ][-1],

            "bc_tip":
                history[
                    "bc_tip"
                ][-1],

            "anchor":
                history[
                    "anchor"
                ][-1],

            "mono":
                history[
                    "mono"
                ][-1],

            "total":
                history[
                    "total"
                ][-1],
        },

        "holdout_evaluated":
            False,

        "production_checkpoint_authority":
            "FINAL_COMPLETED_EPOCH_800",

        "Stage2_certified":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2CUDA8E — "
                "COMP006 Post-Training Stage-2 Closure Evaluation"
            ),
    }


    write_json_atomic(
        SUMMARY,
        summary,
    )


    summary_sha = sha256(
        SUMMARY
    )


    handoff = f"""# PAD-Stream V16E-1B2CUDA8D

## Status

{STATUS_COMPLETE}

## Experiment

`{EXPERIMENT}`

## Training completion

- 800 completed epochs
- 1600 optimizer steps
- exact frozen COMP005 initialization
- fresh Adam optimizer state
- CUDA3 K=64 higher-order derivative engine
- microbatch 1024
- logical chunks 8192 + 3328
- hard injector/tip boundary lift
- equal-Nc normalized corrected conservative physics
- L1 positive-slope monotonicity

## Firewall

The E0800 source-native holdout was NOT evaluated during production training.

No OOD data were used.

No TOF data were used.

No checkpoint was selected using holdout performance.

The final completed epoch 800 is the frozen production authority.

## Hashes

CUDA8D Runner SHA-256:
`{RUNNER_SHA}`

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

Training completion does NOT itself certify Stage 2.

B3 remains blocked.

## Next

`V16E-1B2CUDA8E — COMP006 Post-Training Stage-2 Closure Evaluation`
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
    print("RUNNER AUTHORITY")

    print(
        "  runner SHA           :",
        RUNNER_SHA,
    )

    print(
        "  CUDA8C contract SHA  :",
        EXPECTED[
            "CUDA8C_CONTRACT"
        ],
    )

    print(
        "  COMP005 init SHA     :",
        EXPECTED[
            "COMP005"
        ],
    )

    print(
        "  normalization SHA    :",
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


    # Frozen COMP005 must remain byte-for-byte unchanged.
    gate(
        "COMP005_artifact_unchanged",
        sha256(
            COMP005
        )
        ==
        COMP005_SHA_BEFORE
        ==
        EXPECTED[
            "COMP005"
        ],
    )


    print()
    print("=" * 110)
    print("CUDA8D PRODUCTION TRAINING COMPLETE")
    print("=" * 110)

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
    print("FINAL STATUS")
    print(
        STATUS_COMPLETE
    )


    print()
    print("HOLDOUT EVALUATED: NO")
    print("OOD USED: NO")
    print("TOF USED: NO")
    print("STAGE 2 CERTIFIED: NO")
    print("B3 AUTHORIZED: NO")


    print()
    print("NEXT")

    print(
        "V16E-1B2CUDA8E — "
        "COMP006 Post-Training Stage-2 Closure Evaluation"
    )
