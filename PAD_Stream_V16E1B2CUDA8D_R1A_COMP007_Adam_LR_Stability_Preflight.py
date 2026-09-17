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
# PAD-Stream V16E-1B2CUDA8D-R1A
#
# Prospective COMP007 Fresh-Adam Learning-Rate Stability Preflight
#
# SCIENTIFIC SCOPE
# ----------------
# CUDA8D-F1 proved that:
#   - both epoch-1 logical batches are stable at exact COMP005 initialization;
#   - the first fresh Adam(lr=1e-3) step destabilizes corrected physics;
#   - the saved CUDA8D E0001 state is exactly reproducible.
#
# R1A changes NO physics, architecture, loss term, dataset, split, Nc weighting,
# hard boundary lift, batch geometry, derivative engine, or acceptance target.
#
# It tests ONLY fresh-Adam learning rate, using the frozen TRAIN split.
#
# HOLDOUT IS NOT EVALUATED.
# NO OOD.
# NO TOF.
# B3 REMAINS BLOCKED.
#
# Production COMP006 artifacts are READ ONLY and are never modified.
# =============================================================================


MILESTONE = "V16E-1B2CUDA8D-R1A"

SOURCE_EXPERIMENT = "V16E-BLREP-COMP-CUDA-006"
PROSPECTIVE_EXPERIMENT = "V16E-BLREP-COMP-CUDA-007"


REPO = Path("/content/PAD-Stream")
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")


CUDA8D = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8D_COMP006_Authorized_Production_Training_Runner.py"
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

PROVENANCE_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8DR1A_COMP007_ADAM_LR_STABILITY_PREFLIGHT"
)

PROVENANCE_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

RESULTS_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8DR1A_Adam_LR_Stability_Results.json"
)

SUMMARY_PATH = (
    PROVENANCE_ROOT
    / "PAD_Stream_V16E1B2CUDA8DR1A_Summary.json"
)

HANDOFF_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8DR1A_Handoff.md"
)


EXPECTED = {
    "CUDA8D":
        "be4dca13cf44a8c77caad7feae89b7e2a33e68eacbe339efdae6e951f35b05db",

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
# Frozen repair / training geometry
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
# ONLY repair dimension under investigation
# =============================================================================

LR_CANDIDATES = (
    1.0e-3,   # failed COMP006 production control
    3.0e-4,
    1.0e-4,
    3.0e-5,
    1.0e-5,
)


# =============================================================================
# Prospectively frozen R1A stability gates
#
# A candidate passes only if, after ONE exact fresh-Adam step on epoch-1 batch 1:
#
#   - all quantities remain finite;
#   - exact hard boundary conditions remain exact;
#   - batch-2 corrected physics <= 2x its initialization value;
#   - batch-2 total loss <= 2x initialization;
#   - batch-2 source-native data MSE <= 2x initialization;
#   - batch-2 anchor MSE <= 5x initialization;
#   - batch-2 L1 monotonicity <= 5x initialization;
#   - EVERY Nc stratum's mean normalized residual <= 2x initialization.
#
# Selection rule:
#   choose the LARGEST learning rate satisfying EVERY frozen gate.
#
# This is TRAIN-only optimizer stabilization. It is not holdout model selection.
# =============================================================================

MAX_PHYSICS_AMPLIFICATION = 2.0
MAX_TOTAL_AMPLIFICATION = 2.0
MAX_DATA_AMPLIFICATION = 2.0
MAX_ANCHOR_AMPLIFICATION = 5.0
MAX_MONO_AMPLIFICATION = 5.0
MAX_NC_STRATUM_AMPLIFICATION = 2.0


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

        h.update(name.encode("utf-8"))
        h.update(str(t.dtype).encode("utf-8"))
        h.update(str(tuple(t.shape)).encode("utf-8"))
        h.update(t.numpy().tobytes())

    return h.hexdigest()


def gate(name, condition):
    ok = bool(condition)

    print(
        f"[{'PASS' if ok else 'FAIL'}] {name}"
    )

    if not ok:
        raise RuntimeError(
            f"CUDA8D-R1A authority gate failed: {name}"
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
        os.fsync(f.fileno())

    os.replace(
        tmp,
        path,
    )


print("=" * 110)
print("PAD-Stream V16E-1B2CUDA8D-R1A")
print("Prospective COMP007 Fresh-Adam Learning-Rate Stability Preflight")
print("=" * 110)
print()
print("ONLY learning rate is varied.")
print("Production COMP006 remains read only.")
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
    "COMP006_E0001_completed_epoch_exact",
    int(
        recovery006[
            "completed_epoch"
        ]
    )
    ==
    1,
)

gate(
    "COMP006_E0001_optimizer_steps_exact",
    int(
        recovery006[
            "optimizer_steps_completed"
        ]
    )
    ==
    2,
)


# =============================================================================
# Runtime
# =============================================================================

gate(
    "CUDA_available",
    torch.cuda.is_available(),
)

device = torch.device("cuda")

gpu_name = torch.cuda.get_device_name(0)

gpu_total_gib = (
    torch.cuda
    .get_device_properties(0)
    .total_memory
    /
    1024 ** 3
)


print()
print("RUNTIME")
print("  PyTorch :", torch.__version__)
print("  GPU     :", gpu_name)
print("  Memory  :", f"{gpu_total_gib:.3f} GiB")


gate(
    "A100_runtime",
    "A100" in gpu_name,
)

gate(
    "A100_memory_at_least_70GiB",
    gpu_total_gib >= 70.0,
)

gate(
    "PyTorch_2_11_0_cu128",
    str(torch.__version__)
    ==
    "2.11.0+cu128",
)


torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False


# =============================================================================
# Import frozen sources
# =============================================================================

spec = importlib.util.spec_from_file_location(
    "cuda6_for_cuda8dr1a",
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
    "cuda8dr1a_B2S",
)

M = C.import_module(
    B2S.BASE_RUNNER,
    "cuda8dr1a_M",
)

J = C.import_module(
    B2S.B2J_SOURCE,
    "cuda8dr1a_J",
)

CUDA3 = C.import_module(
    C.CUDA3_SOURCE,
    "cuda8dr1a_CUDA3",
)


gate(
    "B2S_SHA_exact",
    sha256(Path(B2S.__file__))
    ==
    EXPECTED["B2S"],
)

gate(
    "BASE_M_SHA_exact",
    sha256(Path(M.__file__))
    ==
    EXPECTED["BASE_M"],
)

gate(
    "ETA_J_SHA_exact",
    sha256(Path(J.__file__))
    ==
    EXPECTED["ETA_J"],
)

gate(
    "CUDA3_SHA_exact",
    sha256(Path(CUDA3.__file__))
    ==
    EXPECTED["CUDA3"],
)


# =============================================================================
# Dataset and frozen split
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
    array_sha256(train_idx)
    ==
    EXPECTED["train_idx"],
)

gate(
    "holdout_idx_SHA_exact",
    array_sha256(holdout_idx)
    ==
    EXPECTED["holdout_idx"],
)

gate(
    "train_count_11520",
    len(train_idx)
    ==
    N_TRAIN,
)


# =============================================================================
# Frozen Nc normalization
# =============================================================================

norm_artifact = json.loads(
    CUDA8BR_NORMALIZATION.read_text(
        encoding="utf-8"
    )
)

T_INTERIOR = (
    xi_all.shape[1]
    - 2
)

normalizer = {}
profile_counts = {}


for row in (
    norm_artifact[
        "Nc_strata"
    ].values()
):
    nc = float(
        row["Nc"]
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
    len(normalizer)
    ==
    NC_COUNT,
)

gate(
    "Nc_profile_counts_cover_train",
    sum(profile_counts.values())
    ==
    N_TRAIN,
)


# =============================================================================
# Exact COMP006/Prospective COMP007 model and objective
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
            .unsqueeze(1)
        )

        Sw_star = (
            p11_phys[
                :,
                9:10
            ]
            .unsqueeze(1)
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

        return (
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
            - Sw
        )
        ** 2
    )

    profile_residual_mse = torch.mean(
        residual ** 2,
        dim=(1, 2),
    )

    nc = p11[:, 10]

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
            + mask.to(
                torch.int16
            )
        )

        if bool(
            torch.any(mask).item()
        ):
            global_profile_weight = (
                float(N_TRAIN)
                /
                (
                    float(NC_COUNT)
                    *
                    float(
                        profile_counts[val]
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
                    normalizer[val]
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
        S_hat[:, 1:, :]
        -
        S_hat[:, :-1, :]
    )

    Lmono = torch.mean(
        torch.relu(
            dS
        )
    )

    total = (
        LAMBDA_DATA * Ldata

        + LAMBDA_PHYS * Lphys

        + LAMBDA_BC * Lbc

        + LAMBDA_TIP * Ltip

        + LAMBDA_ANCHOR * Lanchor

        + LAMBDA_MONO * Lmono
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
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)

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
        and len(
            result.unexpected_keys
        )
        ==
        0,
    )

    return model


# =============================================================================
# Exact epoch-1 logical batches
# =============================================================================

order = C.production_epoch_order(
    train_idx,
    1,
)

batch1 = order[
    :LOGICAL_BATCH
]

batch2 = order[
    LOGICAL_BATCH:
]


gate(
    "batch1_count_8192",
    len(batch1)
    ==
    LOGICAL_BATCH,
)

gate(
    "batch2_count_3328",
    len(batch2)
    ==
    SECOND_LOGICAL_CHUNK,
)


# =============================================================================
# Logical batch evaluation / gradient capture
# =============================================================================

def evaluate_logical(
    model,
    ids,
):
    model.train()

    logical_n = len(ids)

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
            + MICROBATCH
        ]

        m = len(mids)

        xi = (
            torch.from_numpy(
                xi_all[mids]
            )
            .to(device)
            .detach()
            .clone()
            .requires_grad_(True)
        )

        Sw = torch.from_numpy(
            Sw_all[mids]
        ).to(device)

        p11 = (
            torch.from_numpy(
                p11_all[mids]
            )
            .to(device)
            .detach()
            .clone()
            .requires_grad_(True)
        )

        ai = torch.from_numpy(
            ai_all[mids]
        ).to(device)

        at = torch.from_numpy(
            at_all[mids]
        ).to(device)


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


        for value in (
            out["S_hat"],
            out["residual"],
            *out["parts"].values(),
        ):
            if not finite_tensor(
                value
            ):
                raise RuntimeError(
                    "Nonfinite quantity in R1A evaluation."
                )


        for key in sums:
            sums[key] += (
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
                * m
            )


        with torch.no_grad():
            for val in NC_VALUES:
                mask = native_nc_mask_torch(
                    out["nc"],
                    val,
                )

                nmask = int(
                    torch.sum(mask)
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
                    normalizer[val]
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
            sums[key]
            /
            float(logical_n)
        for key in sums
    }


    result["Nc"] = {
        str(val): {
            "count":
                nc_diag[val][
                    "count"
                ],

            "mean_normalized_residual":
                (
                    nc_diag[val][
                        "normalized_sum"
                    ]
                    /
                    nc_diag[val][
                        "count"
                    ]
                ),
        }
        for val in NC_VALUES
    }


    return result


def capture_batch1_gradients(
    model,
):
    model.train()

    logical_n = len(batch1)

    model.zero_grad(
        set_to_none=True
    )


    for m0 in range(
        0,
        logical_n,
        MICROBATCH,
    ):
        mids = batch1[
            m0:
            m0
            + MICROBATCH
        ]

        m = len(mids)

        xi = (
            torch.from_numpy(
                xi_all[mids]
            )
            .to(device)
            .detach()
            .clone()
            .requires_grad_(True)
        )

        Sw = torch.from_numpy(
            Sw_all[mids]
        ).to(device)

        p11 = (
            torch.from_numpy(
                p11_all[mids]
            )
            .to(device)
            .detach()
            .clone()
            .requires_grad_(True)
        )

        ai = torch.from_numpy(
            ai_all[mids]
        ).to(device)

        at = torch.from_numpy(
            at_all[mids]
        ).to(device)


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

            scaled = (
                out[
                    "parts"
                ][
                    "total"
                ]
                *
                (
                    float(m)
                    /
                    float(logical_n)
                )
            )

            scaled.backward()


        del (
            xi,
            Sw,
            p11,
            ai,
            at,
            out,
            scaled,
        )


    grads = {}

    global_sq = 0.0
    max_abs = 0.0


    for name, p in model.named_parameters():
        if p.grad is None:
            raise RuntimeError(
                f"Missing gradient: {name}"
            )

        if not finite_tensor(
            p.grad
        ):
            raise RuntimeError(
                f"Nonfinite gradient: {name}"
            )

        g = (
            p.grad
            .detach()
            .cpu()
            .clone()
        )

        grads[name] = g

        global_sq += float(
            torch.sum(
                g.double()
                ** 2
            )
            .item()
        )

        max_abs = max(
            max_abs,
            float(
                torch.max(
                    torch.abs(g)
                )
                .item()
            ),
        )


    model.zero_grad(
        set_to_none=True
    )


    return {
        "grads":
            grads,

        "global_norm":
            math.sqrt(global_sq),

        "max_abs":
            max_abs,
    }


def apply_exact_fresh_adam_step(
    model,
    grads,
    lr,
):
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=lr,
        foreach=False,
    )

    gate(
        f"Adam_{lr}_fresh_state",
        len(
            optimizer.state
        )
        ==
        0,
    )


    named = dict(
        model.named_parameters()
    )


    for name, grad_cpu in grads.items():
        named[
            name
        ].grad = grad_cpu.to(
            device=device,
            dtype=named[
                name
            ].dtype,
        )


    before = {
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
            f"Nonfinite model after Adam step at lr={lr}."
        )


    max_update = 0.0
    update_sq = 0.0
    n = 0
    worst = None


    for name, p in model.named_parameters():
        d = (
            p.detach()
            .cpu()
            .double()
            -
            before[
                name
            ].double()
        )

        this_max = float(
            torch.max(
                torch.abs(d)
            )
            .item()
        )

        if this_max > max_update:
            max_update = this_max
            worst = name

        update_sq += float(
            torch.sum(
                d ** 2
            )
            .item()
        )

        n += d.numel()


    optimizer.zero_grad(
        set_to_none=True
    )


    return {
        "max_abs_update":
            max_update,

        "update_rmse":
            math.sqrt(
                update_sq
                /
                max(
                    n,
                    1,
                )
            ),

        "worst_tensor":
            worst,
    }


# =============================================================================
# Execute R1A
# =============================================================================

engine = CUDA3.make_cuda3_chunked_batched_engine(
    ADOPTED_CHUNK
)

original_engine = (
    B2S.local_recurrent_derivatives_create_graph
)


try:
    B2S.local_recurrent_derivatives_create_graph = engine


    # Initialization baselines.
    baseline_model = fresh_model()

    baseline_state_hash = state_tensor_hash(
        baseline_model.state_dict()
    )


    print()
    print("EXACT COMP005-LOADED BASELINE")
    print(
        "  model tensor SHA:",
        baseline_state_hash,
    )


    batch1_init = evaluate_logical(
        baseline_model,
        batch1,
    )

    batch2_init = evaluate_logical(
        baseline_model,
        batch2,
    )


    # One exact batch-1 gradient is sufficient because LR does not alter the
    # gradient at the common initialization.
    gradient_info = capture_batch1_gradients(
        baseline_model
    )


    print(
        "  batch1 gradient norm:",
        f"{gradient_info['global_norm']:.12e}",
    )

    print(
        "  batch1 gradient max :",
        f"{gradient_info['max_abs']:.12e}",
    )


    results = []


    for lr in LR_CANDIDATES:

        print()
        print("-" * 110)
        print(
            f"FRESH ADAM LR CANDIDATE: {lr:.1e}"
        )
        print("-" * 110)


        candidate = fresh_model()


        update = apply_exact_fresh_adam_step(
            candidate,
            gradient_info[
                "grads"
            ],
            lr,
        )


        batch2_post = evaluate_logical(
            candidate,
            batch2,
        )


        amplification = {
            "physics":
                batch2_post[
                    "physics"
                ]
                /
                batch2_init[
                    "physics"
                ],

            "total":
                batch2_post[
                    "total"
                ]
                /
                batch2_init[
                    "total"
                ],

            "data":
                batch2_post[
                    "data"
                ]
                /
                batch2_init[
                    "data"
                ],

            "anchor":
                batch2_post[
                    "anchor"
                ]
                /
                batch2_init[
                    "anchor"
                ],

            "mono":
                batch2_post[
                    "mono"
                ]
                /
                max(
                    batch2_init[
                        "mono"
                    ],
                    1.0e-30,
                ),
        }


        nc_amplification = {}


        for val in NC_VALUES:
            key = str(val)

            nc_amplification[
                key
            ] = (
                batch2_post[
                    "Nc"
                ][
                    key
                ][
                    "mean_normalized_residual"
                ]
                /
                batch2_init[
                    "Nc"
                ][
                    key
                ][
                    "mean_normalized_residual"
                ]
            )


        gates = {
            "finite":
                all(
                    math.isfinite(
                        float(
                            batch2_post[key]
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
                            batch2_post["Nc"][str(val)][
                                "mean_normalized_residual"
                            ]
                        )
                    )
                    for val in NC_VALUES
                )
                and model_finite(
                    candidate
                ),

            "bc_exact":
                batch2_post[
                    "bc_inj"
                ]
                <=
                1.0e-12
                and batch2_post[
                    "bc_tip"
                ]
                <=
                1.0e-12,

            "physics_amp_le_2":
                amplification[
                    "physics"
                ]
                <=
                MAX_PHYSICS_AMPLIFICATION,

            "total_amp_le_2":
                amplification[
                    "total"
                ]
                <=
                MAX_TOTAL_AMPLIFICATION,

            "data_amp_le_2":
                amplification[
                    "data"
                ]
                <=
                MAX_DATA_AMPLIFICATION,

            "anchor_amp_le_5":
                amplification[
                    "anchor"
                ]
                <=
                MAX_ANCHOR_AMPLIFICATION,

            "mono_amp_le_5":
                amplification[
                    "mono"
                ]
                <=
                MAX_MONO_AMPLIFICATION,

            "all_Nc_amp_le_2":
                all(
                    value
                    <=
                    MAX_NC_STRATUM_AMPLIFICATION
                    for value
                    in nc_amplification.values()
                ),
        }


        passed = all(
            gates.values()
        )


        result = {
            "learning_rate":
                lr,

            "update":
                update,

            "batch2_post_step1":
                batch2_post,

            "amplification":
                amplification,

            "Nc_amplification":
                nc_amplification,

            "gates":
                gates,

            "PASS":
                passed,
        }


        results.append(
            result
        )


        print(
            "Update max abs:",
            f"{update['max_abs_update']:.12e}",
        )

        print(
            "Update RMSE   :",
            f"{update['update_rmse']:.12e}",
        )

        print(
            "Batch2 physics:",
            f"{batch2_post['physics']:.12e}",
            "| amp",
            f"{amplification['physics']:.6e}",
        )

        print(
            "Batch2 total  :",
            f"{batch2_post['total']:.12e}",
            "| amp",
            f"{amplification['total']:.6e}",
        )

        print(
            "Batch2 data   :",
            f"{batch2_post['data']:.12e}",
            "| amp",
            f"{amplification['data']:.6e}",
        )

        print(
            "Batch2 anchor :",
            f"{batch2_post['anchor']:.12e}",
            "| amp",
            f"{amplification['anchor']:.6e}",
        )

        print(
            "Batch2 mono   :",
            f"{batch2_post['mono']:.12e}",
            "| amp",
            f"{amplification['mono']:.6e}",
        )


        for val in NC_VALUES:
            print(
                f"  Nc={val:.2f} residual amp:",
                f"{nc_amplification[str(val)]:.6e}",
            )


        print(
            "Candidate disposition:",
            "PASS"
            if passed
            else "FAIL",
        )


        del candidate
        torch.cuda.empty_cache()


finally:
    B2S.local_recurrent_derivatives_create_graph = (
        original_engine
    )


# =============================================================================
# Select largest stable LR
# =============================================================================

passing = [
    row
    for row in results
    if row["PASS"]
]


if passing:
    selected = max(
        passing,
        key=lambda row:
            row[
                "learning_rate"
            ],
    )

    selected_lr = float(
        selected[
            "learning_rate"
        ]
    )

    disposition = (
        "R1A_STABLE_LR_FOUND_"
        "R1B_MULTI_STEP_CONFIRMATION_AUTHORIZED_"
        "PRODUCTION_NOT_YET_AUTHORIZED"
    )

else:
    selected_lr = None

    disposition = (
        "R1A_NO_STABLE_LR_FOUND_"
        "REQUIRES_FURTHER_OPTIMIZER_REPAIR_"
        "PRODUCTION_NOT_AUTHORIZED"
    )


runner_sha = sha256(
    Path(__file__)
)


results_artifact = {
    "milestone":
        MILESTONE,

    "source_experiment":
        SOURCE_EXPERIMENT,

    "prospective_experiment":
        PROSPECTIVE_EXPERIMENT,

    "runner_sha256":
        runner_sha,

    "COMP006_E0001_sha256":
        COMP006_E0001_SHA,

    "baseline_model_tensor_sha256":
        baseline_state_hash,

    "batch1_initialization":
        batch1_init,

    "batch2_initialization":
        batch2_init,

    "batch1_gradient": {
        "global_norm":
            gradient_info[
                "global_norm"
            ],

        "max_abs":
            gradient_info[
                "max_abs"
            ],
    },

    "candidate_learning_rates":
        list(
            LR_CANDIDATES
        ),

    "acceptance_thresholds": {
        "max_physics_amplification":
            MAX_PHYSICS_AMPLIFICATION,

        "max_total_amplification":
            MAX_TOTAL_AMPLIFICATION,

        "max_data_amplification":
            MAX_DATA_AMPLIFICATION,

        "max_anchor_amplification":
            MAX_ANCHOR_AMPLIFICATION,

        "max_mono_amplification":
            MAX_MONO_AMPLIFICATION,

        "max_each_Nc_stratum_amplification":
            MAX_NC_STRATUM_AMPLIFICATION,
    },

    "selection_rule":
        "LARGEST_LEARNING_RATE_PASSING_EVERY_FROZEN_GATE",

    "results":
        results,

    "selected_learning_rate":
        selected_lr,

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

    "production_authorized":
        False,
}


atomic_json(
    RESULTS_PATH,
    results_artifact,
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
        selected_lr,

    "disposition":
        disposition,

    "next_milestone":
        (
            "V16E-1B2CUDA8D-R1B — "
            "Prospective COMP007 Multi-Step Optimizer Stability Confirmation"
            if selected_lr is not None
            else
            "Further optimizer repair required before production."
        ),

    "holdout_evaluated":
        False,

    "production_authorized":
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


handoff = f"""# PAD-Stream V16E-1B2CUDA8D-R1A

## Purpose

Train-only fresh-Adam learning-rate stability preflight after CUDA8D-F1 proved
that the first COMP006 Adam step at lr=1e-3 destabilized corrected physics.

## Scientific invariants

- Same corrected conservative PDE.
- Same differentiable hard boundary lift.
- Same equal-Nc normalization.
- Same source-native training split.
- Same CUDA3 K=64 derivative engine.
- Same loss weights.
- Same model architecture.
- Same exact COMP005 initialization.
- No holdout evaluation.
- No OOD.
- No TOF.
- B3 blocked.

## Only investigated dimension

Fresh Adam learning rate.

Candidates:

{list(LR_CANDIDATES)}

## Selection rule

Largest learning rate passing every prospectively frozen stability gate.

## Result

Selected learning rate:

`{selected_lr}`

Disposition:

`{disposition}`

## Hashes

Runner SHA-256:

`{runner_sha}`

COMP006 E0001 SHA-256:

`{COMP006_E0001_SHA}`

Results SHA-256:

`{results_sha}`

Summary SHA-256:

`{summary_sha}`

## Next

{summary["next_milestone"]}
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
print("CUDA8D-R1A RESULT")
print("=" * 110)

print(
    "Selected learning rate:",
    selected_lr,
)

print(
    "Disposition:",
    disposition,
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
print("PRODUCTION AUTHORIZED: NO")
print("HOLDOUT EVALUATED: NO")
print("OOD USED: NO")
print("TOF USED: NO")
print("B3 AUTHORIZED: NO")
