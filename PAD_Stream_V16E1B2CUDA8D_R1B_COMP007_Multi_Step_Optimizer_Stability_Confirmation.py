from pathlib import Path
import hashlib
import importlib.util
import json
import math
import os
import random

import numpy as np
import torch


# =============================================================================
# PAD-Stream V16E-1B2CUDA8D-R1B
#
# Prospective COMP007 Multi-Step Optimizer Stability Confirmation
#
# PURPOSE
# -------
# R1AR selected fresh Adam lr=1e-4 as the largest learning rate passing every
# prospectively frozen one-step stability gate.
#
# R1B now tests that exact optimizer contract for:
#
#     10 complete frozen-TRAIN epochs
#     20 optimizer steps
#
# using the exact CUDA8D production geometry.
#
# Every training logical batch is compared against the SAME logical batch
# evaluated at the untouched exact COMP005 initialization. This removes
# batch-composition effects from the stability test.
#
# SCIENTIFIC INVARIANTS
# ---------------------
# - exact frozen COMP005 initialization
# - same lifted architecture
# - same corrected conservative PDE
# - same equal-Nc normalization
# - same source-native TRAIN split
# - same CUDA3 K=64 derivative engine
# - same loss coefficients
# - same 1024 microbatch
# - same 8192 + 3328 logical geometry
# - Adam foreach=False
# - AMP off
# - TF32 off
#
# ONLY optimizer repair relative to failed COMP006:
#
#     learning rate 1e-3 -> 1e-4
#
# HOLDOUT IS NEVER EVALUATED.
# NO OOD.
# NO TOF.
# B3 REMAINS BLOCKED.
#
# This milestone does NOT authorize production by itself.
# =============================================================================


MILESTONE = "V16E-1B2CUDA8D-R1B"

SOURCE_EXPERIMENT = "V16E-BLREP-COMP-CUDA-006"
PROSPECTIVE_EXPERIMENT = "V16E-BLREP-COMP-CUDA-007"


# =============================================================================
# Paths
# =============================================================================

REPO = Path("/content/PAD-Stream")
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")


CUDA8D = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8D_COMP006_Authorized_Production_Training_Runner.py"
)

R1A_FAILED = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8D_R1A_COMP007_Adam_LR_Stability_Preflight.py"
)

R1AR = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8D_R1AR_COMP007_Adam_LR_Stability_Preflight_Repair.py"
)

CUDA6 = (
    REPO
    / "PAD_Stream_V16E1B2CUDA6_A100_COMP_CUDA_005_Authorized_Production_Runner.py"
)

DATASET = (
    DRIVE
    / "datasets"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)

RUN005 = (
    DRIVE
    / "runs"
    / "V16E-BLREP-COMP-CUDA-005"
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

CUDA8BR_NORMALIZATION = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8BR_COMP006_REPAIR_IMPLEMENTATION_PREFLIGHT"
    / "V16E1B2CUDA8BR_COMP005_TrainingSplit_Nc_Physics_Normalization.json"
)

RUN006 = (
    DRIVE
    / "runs"
    / SOURCE_EXPERIMENT
)

RECOVERY006_E0001 = (
    RUN006
    / "recovery"
    / "V16E_BLREP_COMP_CUDA_006_RECOVERY_E0001.pt"
)

R1AR_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8DR1AR_COMP007_ADAM_LR_STABILITY_PREFLIGHT_REPAIR"
)

R1AR_RESULTS = (
    R1AR_ROOT
    / "V16E1B2CUDA8DR1AR_Adam_LR_Stability_Results.json"
)

R1AR_SUMMARY = (
    R1AR_ROOT
    / "PAD_Stream_V16E1B2CUDA8DR1AR_Summary.json"
)

R1AR_HANDOFF = (
    R1AR_ROOT
    / "V16E1B2CUDA8DR1AR_Handoff.md"
)


PROVENANCE_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8DR1B_COMP007_MULTI_STEP_STABILITY_CONFIRMATION"
)

PROVENANCE_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

RESULTS_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8DR1B_Multi_Step_Stability_Results.json"
)

SUMMARY_PATH = (
    PROVENANCE_ROOT
    / "PAD_Stream_V16E1B2CUDA8DR1B_Summary.json"
)

HANDOFF_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8DR1B_Handoff.md"
)


# =============================================================================
# Frozen hashes
# =============================================================================

EXPECTED = {
    "CUDA8D":
        "be4dca13cf44a8c77caad7feae89b7e2a33e68eacbe339efdae6e951f35b05db",

    "R1A_FAILED":
        "e2673c4dccf426cd67d964db95b3d81502fb85aa0d36ce7821139fd8abd42ff5",

    "R1AR":
        "317b1cc528f8e2b8c141800390d790f26597b6df1d8e870f9246438d541515ac",

    "CUDA6":
        "385e18b64ebf068a06e5daec11449e3700f69ad743627d4520905f273bf7c552",

    "dataset":
        "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c",

    "COMP005":
        "aaca2ae60d7a789bf6d3d2a177d1b3b5188181809597b1be6901ed7473e0906f",

    "RECOVERY005_E0800":
        "fbdbf6b7bff0b22625e7dbcd09500c258c6deeeec6ed4f846407f6e927435157",

    "CUDA8BR_NORMALIZATION":
        "ccd0e61fc8fc8f73890e83f537bb047aaa5f408c8f4125209cc36d0b79df3549",

    "R1AR_RESULTS":
        "6cac59727b0a71c65b47f72e669d9891df7bef43f08c491a334c1db344c3a670",

    "R1AR_SUMMARY":
        "b5ae5af29770d5c87f2196ae2d32414c0c3b409858f246a870adb7dbe2c2258a",

    "R1AR_HANDOFF":
        "7384c9ccab3d4a7ce7162f03bd88d603da5bbe578823cab6fdf6e90b178c6e7a",

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
# Exact R1B contract
# =============================================================================

SEED = 1337

SELECTED_LR = 1.0e-4

CONFIRMATION_EPOCHS = 10
EXPECTED_STEPS_PER_EPOCH = 2
CONFIRMATION_STEPS = (
    CONFIRMATION_EPOCHS
    * EXPECTED_STEPS_PER_EPOCH
)

NC_VALUES = (
    0.00,
    0.05,
    0.10,
    0.20,
    0.30,
)

NC_COUNT = len(NC_VALUES)

N_TRAIN = 11520

ADOPTED_CHUNK = 64
MICROBATCH = 1024
LOGICAL_BATCH = 8192
SECOND_LOGICAL_CHUNK = 3328

LAMBDA_DATA = 1.0
LAMBDA_PHYS = 8.537526059395e-04
LAMBDA_BC = 5.0
LAMBDA_TIP = 5.0
LAMBDA_ANCHOR = 10.0
LAMBDA_MONO = 0.2


# =============================================================================
# Prospectively frozen multi-step gates
#
# Per logical step, relative to the SAME logical batch evaluated at untouched
# COMP005 initialization:
#
#   physics <= 2x baseline
#   total   <= 2x baseline
#   data    <= 2x baseline
#   anchor  <= 5x baseline
#   mono    <= 5x baseline
#   every Nc mean normalized residual <= 2x baseline
#
# Hard boundary conditions remain exact.
# Gradients and model parameters remain finite.
#
# Final full-TRAIN state:
#
#   physics <= initial full-TRAIN physics
#   total   <= initial full-TRAIN total
#   data    <= 1.25x initial full-TRAIN data
#   anchor  <= 2x initial full-TRAIN anchor
#   mono    <= 2x initial full-TRAIN mono
#   every Nc normalized residual <= 1.5x its initial full-TRAIN value
#
# These thresholds are frozen before R1B execution.
# =============================================================================

STEP_MAX_PHYSICS_AMP = 2.0
STEP_MAX_TOTAL_AMP = 2.0
STEP_MAX_DATA_AMP = 2.0
STEP_MAX_ANCHOR_AMP = 5.0
STEP_MAX_MONO_AMP = 5.0
STEP_MAX_EACH_NC_AMP = 2.0

FINAL_MAX_PHYSICS_AMP = 1.0
FINAL_MAX_TOTAL_AMP = 1.0
FINAL_MAX_DATA_AMP = 1.25
FINAL_MAX_ANCHOR_AMP = 2.0
FINAL_MAX_MONO_AMP = 2.0
FINAL_MAX_EACH_NC_AMP = 1.5


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
            f"CUDA8D-R1B authority gate failed: {name}"
        )


def finite_tensor(x):
    return bool(
        torch.isfinite(x)
        .all()
        .item()
    )


def model_finite(model):
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


def atomic_json(path: Path, obj):
    tmp = Path(
        str(path)
        + ".tmp"
    )

    with tmp.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            obj,
            f,
            indent=2,
            allow_nan=False,
        )

        f.write("\n")
        f.flush()
        os.fsync(
            f.fileno()
        )

    os.replace(
        tmp,
        path,
    )


def ratio(value, baseline):
    return (
        float(value)
        /
        max(
            float(baseline),
            1.0e-30,
        )
    )


print("=" * 110)
print("PAD-Stream V16E-1B2CUDA8D-R1B")
print("Prospective COMP007 Multi-Step Optimizer Stability Confirmation")
print("=" * 110)

print()
print(
    "Selected fresh Adam LR:",
    f"{SELECTED_LR:.1e}",
)

print(
    "Confirmation epochs:",
    CONFIRMATION_EPOCHS,
)

print(
    "Confirmation optimizer steps:",
    CONFIRMATION_STEPS,
)

print("HOLDOUT EVALUATION: FORBIDDEN.")
print("No OOD.")
print("No TOF.")
print("B3 remains blocked.")
print()


# =============================================================================
# Frozen authority gates
# =============================================================================

AUTHORITY = {
    "CUDA8D":
        CUDA8D,

    "R1A_FAILED":
        R1A_FAILED,

    "R1AR":
        R1AR,

    "CUDA6":
        CUDA6,

    "dataset":
        DATASET,

    "COMP005":
        COMP005,

    "RECOVERY005_E0800":
        RECOVERY005_E0800,

    "CUDA8BR_NORMALIZATION":
        CUDA8BR_NORMALIZATION,

    "RECOVERY006_E0001":
        RECOVERY006_E0001,

    "R1AR_RESULTS":
        R1AR_RESULTS,

    "R1AR_SUMMARY":
        R1AR_SUMMARY,

    "R1AR_HANDOFF":
        R1AR_HANDOFF,
}


for name, path in AUTHORITY.items():
    gate(
        f"{name}_exists",
        path.exists(),
    )


for name, path in {
    key: value
    for key, value
    in AUTHORITY.items()
    if key != "RECOVERY006_E0001"
}.items():
    gate(
        f"{name}_SHA_exact",
        sha256(path)
        ==
        EXPECTED[name],
    )


COMP006_E0001_SHA = sha256(
    RECOVERY006_E0001
)

recovery006 = torch.load(
    RECOVERY006_E0001,
    map_location="cpu",
    weights_only=False,
)


gate(
    "COMP006_E0001_experiment_exact",
    recovery006[
        "experiment"
    ]
    ==
    SOURCE_EXPERIMENT,
)

gate(
    "COMP006_E0001_runner_SHA_exact",
    recovery006[
        "runner_sha256"
    ]
    ==
    EXPECTED[
        "CUDA8D"
    ],
)

gate(
    "COMP006_E0001_epoch_exact",
    int(
        recovery006[
            "completed_epoch"
        ]
    )
    ==
    1,
)


r1ar_results = json.loads(
    R1AR_RESULTS.read_text(
        encoding="utf-8"
    )
)


gate(
    "R1AR_selected_lr_exact_1e_4",
    float(
        r1ar_results[
            "selected_learning_rate"
        ]
    )
    ==
    SELECTED_LR,
)

gate(
    "R1AR_production_not_authorized",
    r1ar_results[
        "production_authorized"
    ]
    is False,
)

gate(
    "R1AR_holdout_not_evaluated",
    r1ar_results[
        "holdout_evaluated"
    ]
    is False,
)


# =============================================================================
# Runtime
# =============================================================================

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

gpu_total_gib = (
    torch.cuda
    .get_device_properties(0)
    .total_memory
    /
    1024 ** 3
)


print()
print("RUNTIME")

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


# =============================================================================
# Import exact frozen scientific engine
# =============================================================================

spec = importlib.util.spec_from_file_location(
    "cuda6_for_cuda8dr1b",
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
    "cuda8dr1b_B2S",
)

M = C.import_module(
    B2S.BASE_RUNNER,
    "cuda8dr1b_M",
)

J = C.import_module(
    B2S.B2J_SOURCE,
    "cuda8dr1b_J",
)

CUDA3 = C.import_module(
    C.CUDA3_SOURCE,
    "cuda8dr1b_CUDA3",
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
# Dataset / exact frozen split
# =============================================================================

with np.load(
    DATASET,
    allow_pickle=False,
) as d:
    xi_all = np.array(
        d["xi"],
        copy=True,
    )

    Sw_all = np.array(
        d["Sw"],
        copy=True,
    )

    p11_all = np.array(
        d["p11"],
        copy=True,
    )

    ai_all = np.array(
        d["ai"],
        copy=True,
    )

    at_all = np.array(
        d["at"],
        copy=True,
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


# =============================================================================
# Frozen Nc normalizers
# =============================================================================

norm_artifact = json.loads(
    CUDA8BR_NORMALIZATION.read_text(
        encoding="utf-8"
    )
)

T_INTERIOR = (
    xi_all.shape[1]
    -
    2
)

normalizer = {}
profile_counts = {}


for row in (
    norm_artifact[
        "Nc_strata"
    ].values()
):
    nc = float(
        row[
            "Nc"
        ]
    )

    residual_count = int(
        row[
            "residual_count"
        ]
    )

    normalizer[nc] = float(
        row[
            "residual_MSE"
        ]
    )

    profile_counts[nc] = (
        residual_count
        //
        T_INTERIOR
    )


gate(
    "five_Nc_normalizers",
    len(
        normalizer
    )
    ==
    NC_COUNT,
)

gate(
    "Nc_profile_counts_cover_train",
    sum(
        profile_counts.values()
    )
    ==
    N_TRAIN,
)


# =============================================================================
# Exact lifted model / objective
# =============================================================================

BaseEtaModel = J.build_eta_model_class(
    M
)


class LiftedModel(BaseEtaModel):

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
            -
            sor
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

        return (
            S_raw

            + (
                1.0
                -
                xi_seq
            )
            * (
                S_inj
                -
                S0
            )

            + xi_seq
            * (
                Sw_star
                -
                S1
            )
        )


def comp_loss(
    model,
    xi,
    Sw,
    p11,
    ai,
    at,
):
    (
        S_hat,
        _unused_global_physics,
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
        ** 2
    )

    profile_residual_mse = torch.mean(
        residual ** 2,
        dim=(
            1,
            2,
        ),
    )

    nc = p11[
        :,
        10
    ]

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
            "Profile failed exact Nc assignment."
        )


    Lphys = (
        physics_weighted_sum
        /
        float(
            xi.shape[0]
        )
    )

    Lbc = M.injector_bc_loss(
        S_hat,
        p11,
    )

    Ltip = M.tip_bc_loss(
        S_hat,
        p11,
    )

    Lanchor = M.anchor_loss(
        S_hat,
        ai,
        at,
    )

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


    return {
        "S_hat":
            S_hat,

        "residual":
            residual,

        "profile_residual_mse":
            profile_residual_mse,

        "nc":
            nc,

        "parts": {
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
        },
    }


def fresh_model():
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


    model = LiftedModel().to(
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
        "fresh_model_COMP005_strict",
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


    return model


# =============================================================================
# Memory-safe logical evaluation
# =============================================================================

def evaluate_ids(
    model,
    ids,
):
    model.train()

    total_n = len(
        ids
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

    nc_diag = {
        val: {
            "count": 0,
            "normalized_sum": 0.0,
        }
        for val in NC_VALUES
    }


    for m0 in range(
        0,
        total_n,
        MICROBATCH,
    ):
        mids = ids[
            m0:
            m0
            +
            MICROBATCH
        ]

        m = len(
            mids
        )


        xi = (
            torch.from_numpy(
                xi_all[
                    mids
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
                mids
            ]
        ).to(
            device
        )

        p11 = (
            torch.from_numpy(
                p11_all[
                    mids
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
                mids
            ]
        ).to(
            device
        )

        at = torch.from_numpy(
            at_all[
                mids
            ]
        ).to(
            device
        )


        with torch.backends.cudnn.flags(
            enabled=False
        ):
            out = comp_loss(
                model,
                xi,
                Sw,
                p11,
                ai,
                at,
            )


        if not all(
            finite_tensor(
                value
            )
            for value in (
                out[
                    "S_hat"
                ],
                out[
                    "residual"
                ],
                *out[
                    "parts"
                ].values(),
            )
        ):
            raise RuntimeError(
                "Nonfinite quantity in R1B evaluation."
            )


        for key in sums:
            sums[
                key
            ] += (
                float(
                    out[
                        "parts"
                    ][
                        key
                    ]
                    .detach()
                    .cpu()
                    .item()
                )
                *
                m
            )


        with torch.no_grad():
            for val in NC_VALUES:
                mask = native_nc_mask_torch(
                    out[
                        "nc"
                    ],
                    val,
                )

                nmask = int(
                    torch.sum(
                        mask
                    )
                    .cpu()
                    .item()
                )

                if nmask <= 0:
                    continue

                normalized = (
                    out[
                        "profile_residual_mse"
                    ][
                        mask
                    ]
                    /
                    normalizer[
                        val
                    ]
                )

                nc_diag[
                    val
                ][
                    "count"
                ] += nmask

                nc_diag[
                    val
                ][
                    "normalized_sum"
                ] += float(
                    torch.sum(
                        normalized
                    )
                    .cpu()
                    .item()
                )

            if "mask" in locals():
                del mask

            if "normalized" in locals():
                del normalized


        del (
            xi,
            Sw,
            p11,
            ai,
            at,
            out,
        )


    result = {
        key:
            sums[
                key
            ]
            /
            float(
                total_n
            )
        for key in sums
    }


    result[
        "Nc"
    ] = {
        str(
            val
        ): {
            "count":
                nc_diag[
                    val
                ][
                    "count"
                ],

            "mean_normalized_residual":
                (
                    nc_diag[
                        val
                    ][
                        "normalized_sum"
                    ]
                    /
                    nc_diag[
                        val
                    ][
                        "count"
                    ]
                ),
        }
        for val in NC_VALUES
    }


    return result


# =============================================================================
# Exact logical training step
# =============================================================================

def train_logical_step(
    model,
    optimizer,
    ids,
):
    model.train()

    logical_n = len(
        ids
    )

    optimizer.zero_grad(
        set_to_none=True
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

    nc_diag = {
        val: {
            "count": 0,
            "normalized_sum": 0.0,
        }
        for val in NC_VALUES
    }


    for m0 in range(
        0,
        logical_n,
        MICROBATCH,
    ):
        mids = ids[
            m0:
            m0
            +
            MICROBATCH
        ]

        m = len(
            mids
        )


        xi = (
            torch.from_numpy(
                xi_all[
                    mids
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
                mids
            ]
        ).to(
            device
        )

        p11 = (
            torch.from_numpy(
                p11_all[
                    mids
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
                mids
            ]
        ).to(
            device
        )

        at = torch.from_numpy(
            at_all[
                mids
            ]
        ).to(
            device
        )


        with torch.backends.cudnn.flags(
            enabled=False
        ):
            out = comp_loss(
                model,
                xi,
                Sw,
                p11,
                ai,
                at,
            )


        if not all(
            finite_tensor(
                value
            )
            for value in (
                out[
                    "S_hat"
                ],
                out[
                    "residual"
                ],
                *out[
                    "parts"
                ].values(),
            )
        ):
            raise RuntimeError(
                "Nonfinite quantity in R1B training step."
            )


        if (
            float(
                out[
                    "parts"
                ][
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
                "Hard injector boundary lost exactness."
            )


        if (
            float(
                out[
                    "parts"
                ][
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
                "Hard tip boundary lost exactness."
            )


        for key in sums:
            sums[
                key
            ] += (
                float(
                    out[
                        "parts"
                    ][
                        key
                    ]
                    .detach()
                    .cpu()
                    .item()
                )
                *
                m
            )


        with torch.no_grad():
            for val in NC_VALUES:
                mask = native_nc_mask_torch(
                    out[
                        "nc"
                    ],
                    val,
                )

                nmask = int(
                    torch.sum(
                        mask
                    )
                    .cpu()
                    .item()
                )

                if nmask <= 0:
                    continue

                normalized = (
                    out[
                        "profile_residual_mse"
                    ][
                        mask
                    ]
                    /
                    normalizer[
                        val
                    ]
                )

                nc_diag[
                    val
                ][
                    "count"
                ] += nmask

                nc_diag[
                    val
                ][
                    "normalized_sum"
                ] += float(
                    torch.sum(
                        normalized
                    )
                    .cpu()
                    .item()
                )

            if "mask" in locals():
                del mask

            if "normalized" in locals():
                del normalized


        scaled_total = (
            out[
                "parts"
            ][
                "total"
            ]
            *
            (
                float(
                    m
                )
                /
                float(
                    logical_n
                )
            )
        )


        with torch.backends.cudnn.flags(
            enabled=False
        ):
            scaled_total.backward()


        del (
            xi,
            Sw,
            p11,
            ai,
            at,
            out,
            scaled_total,
        )


    global_sq = 0.0
    max_abs_grad = 0.0
    nonzero_grad_tensors = 0


    for p in model.parameters():
        if p.grad is None:
            raise RuntimeError(
                "Missing model gradient."
            )

        if not finite_tensor(
            p.grad
        ):
            raise RuntimeError(
                "Nonfinite model gradient."
            )

        if bool(
            torch.any(
                p.grad
                !=
                0
            ).item()
        ):
            nonzero_grad_tensors += 1

        global_sq += float(
            torch.sum(
                p.grad
                .detach()
                .double()
                ** 2
            )
            .cpu()
            .item()
        )

        max_abs_grad = max(
            max_abs_grad,
            float(
                torch.max(
                    torch.abs(
                        p.grad
                    )
                )
                .detach()
                .cpu()
                .item()
            ),
        )


    if nonzero_grad_tensors <= 0:
        raise RuntimeError(
            "All gradients are zero."
        )


    pre_state = {
        name:
            p.detach()
            .cpu()
            .clone()
        for name, p in model.named_parameters()
    }


    optimizer.step()
    torch.cuda.synchronize()


    if not model_finite(
        model
    ):
        raise RuntimeError(
            "Model became nonfinite after optimizer step."
        )


    update_sq = 0.0
    update_max = 0.0
    update_worst = None
    update_n = 0


    for name, p in model.named_parameters():
        d = (
            p.detach()
            .cpu()
            .double()
            -
            pre_state[
                name
            ].double()
        )

        dmax = float(
            torch.max(
                torch.abs(
                    d
                )
            )
            .item()
        )

        if dmax > update_max:
            update_max = dmax
            update_worst = name

        update_sq += float(
            torch.sum(
                d ** 2
            )
            .item()
        )

        update_n += d.numel()


    optimizer.zero_grad(
        set_to_none=True
    )


    metrics = {
        key:
            sums[
                key
            ]
            /
            float(
                logical_n
            )
        for key in sums
    }


    metrics[
        "Nc"
    ] = {
        str(
            val
        ): {
            "count":
                nc_diag[
                    val
                ][
                    "count"
                ],

            "mean_normalized_residual":
                (
                    nc_diag[
                        val
                    ][
                        "normalized_sum"
                    ]
                    /
                    nc_diag[
                        val
                    ][
                        "count"
                    ]
                ),
        }
        for val in NC_VALUES
    }


    return {
        "metrics":
            metrics,

        "gradient": {
            "global_norm":
                math.sqrt(
                    global_sq
                ),

            "max_abs":
                max_abs_grad,

            "nonzero_tensor_count":
                nonzero_grad_tensors,
        },

        "update": {
            "max_abs":
                update_max,

            "rmse":
                math.sqrt(
                    update_sq
                    /
                    max(
                        update_n,
                        1,
                    )
                ),

            "worst_tensor":
                update_worst,
        },
    }


# =============================================================================
# Build exact 20-step deterministic schedule
# =============================================================================

schedule = []


for epoch in range(
    1,
    CONFIRMATION_EPOCHS
    +
    1,
):
    order = C.production_epoch_order(
        train_idx,
        epoch,
    )

    gate(
        f"epoch_{epoch}_order_count_11520",
        len(
            order
        )
        ==
        N_TRAIN,
    )

    first = order[
        :LOGICAL_BATCH
    ]

    second = order[
        LOGICAL_BATCH:
    ]

    gate(
        f"epoch_{epoch}_batch1_8192",
        len(
            first
        )
        ==
        LOGICAL_BATCH,
    )

    gate(
        f"epoch_{epoch}_batch2_3328",
        len(
            second
        )
        ==
        SECOND_LOGICAL_CHUNK,
    )

    schedule.append(
        {
            "epoch":
                epoch,

            "logical":
                1,

            "ids":
                first,
        }
    )

    schedule.append(
        {
            "epoch":
                epoch,

            "logical":
                2,

            "ids":
                second,
        }
    )


gate(
    "confirmation_schedule_20_steps",
    len(
        schedule
    )
    ==
    CONFIRMATION_STEPS,
)


# =============================================================================
# Execute R1B
# =============================================================================

engine = CUDA3.make_cuda3_chunked_batched_engine(
    ADOPTED_CHUNK
)

original_engine = (
    B2S.local_recurrent_derivatives_create_graph
)


try:
    B2S.local_recurrent_derivatives_create_graph = (
        engine
    )


    # -------------------------------------------------------------------------
    # Exact untouched COMP005 baseline.
    # -------------------------------------------------------------------------

    baseline_model = fresh_model()

    baseline_model_hash = state_tensor_hash(
        baseline_model.state_dict()
    )


    print()
    print("BASELINE MODEL")

    print(
        "  exact COMP005-loaded tensor SHA:",
        baseline_model_hash,
    )


    print()
    print(
        "Evaluating full frozen TRAIN baseline..."
    )


    full_train_initial = evaluate_ids(
        baseline_model,
        train_idx,
    )


    print(
        "  initial TRAIN physics:",
        f"{full_train_initial['physics']:.12e}",
    )

    print(
        "  initial TRAIN total  :",
        f"{full_train_initial['total']:.12e}",
    )


    # -------------------------------------------------------------------------
    # Baseline every exact logical batch at untouched COMP005.
    # -------------------------------------------------------------------------

    print()
    print(
        "Building same-batch COMP005 baselines for 20 logical steps..."
    )


    logical_baselines = []


    for step_number, row in enumerate(
        schedule,
        start=1,
    ):
        torch.cuda.empty_cache()

        b = evaluate_ids(
            baseline_model,
            row[
                "ids"
            ],
        )

        logical_baselines.append(
            b
        )

        print(
            f"  baseline step {step_number:02d}/"
            f"{CONFIRMATION_STEPS} "
            f"| epoch {row['epoch']:02d} "
            f"| logical {row['logical']} "
            f"| physics {b['physics']:.6e} "
            f"| total {b['total']:.6e}"
        )


    del baseline_model
    torch.cuda.empty_cache()


    # -------------------------------------------------------------------------
    # Exact prospective COMP007 optimizer trajectory.
    # -------------------------------------------------------------------------

    model = fresh_model()

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=SELECTED_LR,
        foreach=False,
    )


    gate(
        "fresh_Adam_state_empty",
        len(
            optimizer.state
        )
        ==
        0,
    )


    step_records = []

    all_step_gates_pass = True


    for step_number, (
        row,
        baseline,
    ) in enumerate(
        zip(
            schedule,
            logical_baselines,
        ),
        start=1,
    ):
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()


        result = train_logical_step(
            model,
            optimizer,
            row[
                "ids"
            ],
        )


        current = result[
            "metrics"
        ]


        amplification = {
            "physics":
                ratio(
                    current[
                        "physics"
                    ],
                    baseline[
                        "physics"
                    ],
                ),

            "total":
                ratio(
                    current[
                        "total"
                    ],
                    baseline[
                        "total"
                    ],
                ),

            "data":
                ratio(
                    current[
                        "data"
                    ],
                    baseline[
                        "data"
                    ],
                ),

            "anchor":
                ratio(
                    current[
                        "anchor"
                    ],
                    baseline[
                        "anchor"
                    ],
                ),

            "mono":
                ratio(
                    current[
                        "mono"
                    ],
                    baseline[
                        "mono"
                    ],
                ),
        }


        nc_amplification = {
            str(
                val
            ):
                ratio(
                    current[
                        "Nc"
                    ][
                        str(
                            val
                        )
                    ][
                        "mean_normalized_residual"
                    ],
                    baseline[
                        "Nc"
                    ][
                        str(
                            val
                        )
                    ][
                        "mean_normalized_residual"
                    ],
                )
            for val in NC_VALUES
        }


        gates = {
            "finite":
                all(
                    math.isfinite(
                        float(
                            current[
                                key
                            ]
                        )
                    )
                    for key in (
                        "data",
                        "physics",
                        "bc_inj",
                        "bc_tip",
                        "anchor",
                        "mono",
                        "total",
                    )
                )
                and all(
                    math.isfinite(
                        float(
                            nc_amplification[
                                str(
                                    val
                                )
                            ]
                        )
                    )
                    for val in NC_VALUES
                )
                and model_finite(
                    model
                ),

            "bc_exact":
                current[
                    "bc_inj"
                ]
                <=
                1.0e-12
                and current[
                    "bc_tip"
                ]
                <=
                1.0e-12,

            "physics_amp_le_2":
                amplification[
                    "physics"
                ]
                <=
                STEP_MAX_PHYSICS_AMP,

            "total_amp_le_2":
                amplification[
                    "total"
                ]
                <=
                STEP_MAX_TOTAL_AMP,

            "data_amp_le_2":
                amplification[
                    "data"
                ]
                <=
                STEP_MAX_DATA_AMP,

            "anchor_amp_le_5":
                amplification[
                    "anchor"
                ]
                <=
                STEP_MAX_ANCHOR_AMP,

            "mono_amp_le_5":
                amplification[
                    "mono"
                ]
                <=
                STEP_MAX_MONO_AMP,

            "all_Nc_amp_le_2":
                all(
                    value
                    <=
                    STEP_MAX_EACH_NC_AMP
                    for value in nc_amplification.values()
                ),
        }


        step_pass = all(
            gates.values()
        )


        if not step_pass:
            all_step_gates_pass = False


        peak_gib = (
            torch.cuda
            .max_memory_allocated()
            /
            1024 ** 3
        )


        record = {
            "step":
                step_number,

            "epoch":
                row[
                    "epoch"
                ],

            "logical_batch":
                row[
                    "logical"
                ],

            "baseline":
                baseline,

            "pre_step_metrics":
                current,

            "amplification":
                amplification,

            "Nc_amplification":
                nc_amplification,

            "gradient":
                result[
                    "gradient"
                ],

            "update":
                result[
                    "update"
                ],

            "peak_allocated_GiB":
                peak_gib,

            "gates":
                gates,

            "PASS":
                step_pass,
        }


        step_records.append(
            record
        )


        print(
            f"[R1B] step {step_number:02d}/"
            f"{CONFIRMATION_STEPS} "
            f"| epoch {row['epoch']:02d} "
            f"| logical {row['logical']} "
            f"| phys {current['physics']:.6e} "
            f"(x{amplification['physics']:.3f}) "
            f"| total {current['total']:.6e} "
            f"(x{amplification['total']:.3f}) "
            f"| data x{amplification['data']:.3f} "
            f"| maxNc x{max(nc_amplification.values()):.3f} "
            f"| grad {result['gradient']['global_norm']:.3e} "
            f"| upd {result['update']['max_abs']:.3e} "
            f"| peak {peak_gib:.2f} GiB "
            f"| {'PASS' if step_pass else 'FAIL'}"
        )


    # -------------------------------------------------------------------------
    # Final full-TRAIN confirmation.
    # -------------------------------------------------------------------------

    print()
    print(
        "Evaluating final full frozen TRAIN state..."
    )


    full_train_final = evaluate_ids(
        model,
        train_idx,
    )


    final_amplification = {
        "physics":
            ratio(
                full_train_final[
                    "physics"
                ],
                full_train_initial[
                    "physics"
                ],
            ),

        "total":
            ratio(
                full_train_final[
                    "total"
                ],
                full_train_initial[
                    "total"
                ],
            ),

        "data":
            ratio(
                full_train_final[
                    "data"
                ],
                full_train_initial[
                    "data"
                ],
            ),

        "anchor":
            ratio(
                full_train_final[
                    "anchor"
                ],
                full_train_initial[
                    "anchor"
                ],
            ),

        "mono":
            ratio(
                full_train_final[
                    "mono"
                ],
                full_train_initial[
                    "mono"
                ],
            ),
    }


    final_nc_amplification = {
        str(
            val
        ):
            ratio(
                full_train_final[
                    "Nc"
                ][
                    str(
                        val
                    )
                ][
                    "mean_normalized_residual"
                ],
                full_train_initial[
                    "Nc"
                ][
                    str(
                        val
                    )
                ][
                    "mean_normalized_residual"
                ],
            )
        for val in NC_VALUES
    }


    final_gates = {
        "finite":
            all(
                math.isfinite(
                    float(
                        full_train_final[
                            key
                        ]
                    )
                )
                for key in (
                    "data",
                    "physics",
                    "bc_inj",
                    "bc_tip",
                    "anchor",
                    "mono",
                    "total",
                )
            )
            and model_finite(
                model
            ),

        "bc_exact":
            full_train_final[
                "bc_inj"
            ]
            <=
            1.0e-12
            and full_train_final[
                "bc_tip"
            ]
            <=
            1.0e-12,

        "physics_not_worse_than_initial":
            final_amplification[
                "physics"
            ]
            <=
            FINAL_MAX_PHYSICS_AMP,

        "total_not_worse_than_initial":
            final_amplification[
                "total"
            ]
            <=
            FINAL_MAX_TOTAL_AMP,

        "data_amp_le_1_25":
            final_amplification[
                "data"
            ]
            <=
            FINAL_MAX_DATA_AMP,

        "anchor_amp_le_2":
            final_amplification[
                "anchor"
            ]
            <=
            FINAL_MAX_ANCHOR_AMP,

        "mono_amp_le_2":
            final_amplification[
                "mono"
            ]
            <=
            FINAL_MAX_MONO_AMP,

        "all_Nc_amp_le_1_5":
            all(
                value
                <=
                FINAL_MAX_EACH_NC_AMP
                for value
                in final_nc_amplification.values()
            ),
    }


    final_pass = all(
        final_gates.values()
    )


    final_model_hash = state_tensor_hash(
        model.state_dict()
    )


finally:
    B2S.local_recurrent_derivatives_create_graph = (
        original_engine
    )


# =============================================================================
# Disposition
# =============================================================================

overall_pass = (
    all_step_gates_pass
    and
    final_pass
)


if overall_pass:
    disposition = (
        "R1B_MULTI_STEP_STABILITY_CONFIRMED_"
        "COMP007_PRODUCTION_CONTRACT_FREEZE_AUTHORIZED_"
        "PRODUCTION_TRAINING_NOT_YET_AUTHORIZED"
    )

    next_milestone = (
        "V16E-1B2CUDA8D-R1C — "
        "COMP007 Production Contract Freeze and Authorization"
    )

else:
    disposition = (
        "R1B_MULTI_STEP_STABILITY_NOT_CONFIRMED_"
        "COMP007_PRODUCTION_NOT_AUTHORIZED_"
        "FURTHER_OPTIMIZER_REPAIR_REQUIRED"
    )

    next_milestone = (
        "Further optimizer repair required before COMP007 production."
    )


runner_sha = sha256(
    Path(
        __file__
    )
)


results = {
    "milestone":
        MILESTONE,

    "source_experiment":
        SOURCE_EXPERIMENT,

    "prospective_experiment":
        PROSPECTIVE_EXPERIMENT,

    "runner_sha256":
        runner_sha,

    "selected_learning_rate":
        SELECTED_LR,

    "confirmation_epochs":
        CONFIRMATION_EPOCHS,

    "confirmation_optimizer_steps":
        CONFIRMATION_STEPS,

    "baseline_model_tensor_sha256":
        baseline_model_hash,

    "final_model_tensor_sha256":
        final_model_hash,

    "full_train_initial":
        full_train_initial,

    "full_train_final":
        full_train_final,

    "final_amplification":
        final_amplification,

    "final_Nc_amplification":
        final_nc_amplification,

    "final_gates":
        final_gates,

    "all_step_gates_pass":
        all_step_gates_pass,

    "step_records":
        step_records,

    "overall_PASS":
        overall_pass,

    "disposition":
        disposition,

    "holdout_evaluated":
        False,

    "OOD_used":
        False,

    "TOF_used":
        False,

    "B3_authorized":
        False,

    "production_training_authorized":
        False,

    "next_milestone":
        next_milestone,
}


atomic_json(
    RESULTS_PATH,
    results,
)


results_sha = sha256(
    RESULTS_PATH
)


summary = {
    "milestone":
        MILESTONE,

    "runner_sha256":
        runner_sha,

    "results_sha256":
        results_sha,

    "selected_learning_rate":
        SELECTED_LR,

    "confirmation_epochs":
        CONFIRMATION_EPOCHS,

    "confirmation_optimizer_steps":
        CONFIRMATION_STEPS,

    "all_step_gates_pass":
        all_step_gates_pass,

    "final_gates_pass":
        final_pass,

    "overall_PASS":
        overall_pass,

    "final_amplification":
        final_amplification,

    "final_Nc_amplification":
        final_nc_amplification,

    "disposition":
        disposition,

    "next_milestone":
        next_milestone,

    "holdout_evaluated":
        False,

    "production_training_authorized":
        False,

    "B3_authorized":
        False,
}


atomic_json(
    SUMMARY_PATH,
    summary,
)


summary_sha = sha256(
    SUMMARY_PATH
)


handoff = f"""# PAD-Stream V16E-1B2CUDA8D-R1B

## Purpose

Confirm the R1AR-selected fresh Adam learning rate across a multi-step
trajectory before freezing any COMP007 production contract.

## Selected optimizer repair

Fresh Adam learning rate:

`{SELECTED_LR}`

## Confirmation horizon

- {CONFIRMATION_EPOCHS} complete frozen-TRAIN epochs
- {CONFIRMATION_STEPS} optimizer steps
- same CUDA8D production geometry
- same deterministic production ordering

## Scientific invariants

- exact COMP005 initialization
- unchanged model architecture
- unchanged corrected conservative PDE
- unchanged hard boundary lift
- unchanged equal-Nc normalization
- unchanged loss coefficients
- unchanged TRAIN split
- no holdout evaluation
- no OOD
- no TOF
- B3 blocked

## Result

All step gates pass:

`{all_step_gates_pass}`

Final full-TRAIN gates pass:

`{final_pass}`

Overall PASS:

`{overall_pass}`

Disposition:

`{disposition}`

## Final full-TRAIN amplification relative to exact COMP005 initialization

```text
physics : {final_amplification["physics"]:.12e}
total   : {final_amplification["total"]:.12e}
data    : {final_amplification["data"]:.12e}
anchor  : {final_amplification["anchor"]:.12e}
mono    : {final_amplification["mono"]:.12e}
```

## Hashes

Runner SHA-256:

`{runner_sha}`

Results SHA-256:

`{results_sha}`

Summary SHA-256:

`{summary_sha}`

## Next

{next_milestone}
"""


HANDOFF_PATH.write_text(
    handoff,
    encoding="utf-8",
)


handoff_sha = sha256(
    HANDOFF_PATH
)


print()
print("=" * 110)
print("CUDA8D-R1B RESULT")
print("=" * 110)

print(
    "All step gates pass:",
    all_step_gates_pass,
)

print(
    "Final full-TRAIN gates pass:",
    final_pass,
)

print(
    "Overall PASS:",
    overall_pass,
)

print()
print("Final full-TRAIN amplification:")

for key in (
    "physics",
    "total",
    "data",
    "anchor",
    "mono",
):
    print(
        f"  {key:<8}: "
        f"{final_amplification[key]:.12e}"
    )


print()
print("Final Nc amplification:")

for val in NC_VALUES:
    print(
        f"  Nc={val:.2f}: "
        f"{final_nc_amplification[str(val)]:.12e}"
    )


print()
print(
    "Disposition:",
    disposition,
)

print(
    "Next:",
    next_milestone,
)

print()
print(
    "Runner SHA :",
    runner_sha,
)

print(
    "Results SHA:",
    results_sha,
)

print(
    "Summary SHA:",
    summary_sha,
)

print(
    "Handoff SHA:",
    handoff_sha,
)

print()
print("PRODUCTION TRAINING AUTHORIZED: NO")
print("HOLDOUT EVALUATED: NO")
print("OOD USED: NO")
print("TOF USED: NO")
print("B3 AUTHORIZED: NO")
