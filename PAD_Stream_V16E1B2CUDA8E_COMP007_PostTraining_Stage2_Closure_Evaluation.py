from pathlib import Path
import hashlib
import importlib.util
import json
import math
import os

import numpy as np
import torch


# =============================================================================
# PAD-Stream V16E-1B2CUDA8E
#
# COMP007 Post-Training Stage-2 Closure Evaluation
#
# PURPOSE
# -------
# Open the exact frozen source-native holdout ONLY AFTER the authorized
# COMP007 E0800 production checkpoint exists, and make the Stage-2 scientific
# disposition using the acceptance logic frozen before COMP007 production.
#
# NO TRAINING.
# NO MODEL SELECTION.
# NO THRESHOLD TUNING.
# NO OOD.
# NO TOF.
#
# Models compared on the exact same frozen holdout:
#
#   COMP004  frozen eta-input experimental reference
#   COMP005  frozen corrected-physics production predecessor
#   COMP007  frozen repaired E0800 production candidate
#
# Stage-2 certification requires ALL gates.
# B3 is authorized ONLY if Stage 2 certifies.
# =============================================================================


MILESTONE = "V16E-1B2CUDA8E"
EXPERIMENT = "V16E-BLREP-COMP-CUDA-007"


# =============================================================================
# Paths
# =============================================================================

REPO = Path("/content/PAD-Stream")
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")


DATASET = (
    DRIVE
    / "datasets"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)

CUDA6 = (
    REPO
    / "PAD_Stream_V16E1B2CUDA6_A100_COMP_CUDA_005_Authorized_Production_Runner.py"
)

CUDA8A_PROTOCOL = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8A_TARGETED_STAGE2_REPAIR_PROTOCOL_FREEZE"
    / "V16E1B2CUDA8A_Targeted_Stage2_Repair_Protocol.json"
)

CUDA8BR_NORMALIZATION = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8BR_COMP006_REPAIR_IMPLEMENTATION_PREFLIGHT"
    / "V16E1B2CUDA8BR_COMP005_TrainingSplit_Nc_Physics_Normalization.json"
)

COMP004 = (
    DRIVE
    / "provenance"
    / "xpu_reference"
    / "V16E_BLREP_COMP_XPU_004.pt"
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


R1C_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8D_R1C_COMP007_Production_Contract_Freeze_Authorization.py"
)

R1C_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8DR1C_COMP007_PRODUCTION_CONTRACT_AUTHORIZATION"
)

R1C_CONTRACT = (
    R1C_ROOT
    / "V16E1B2CUDA8DR1C_COMP007_Production_Training_Contract.json"
)


R1D_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8D_R1D_COMP007_Authorized_Production_Training_Runner.py"
)

RUN007 = (
    DRIVE
    / "runs"
    / EXPERIMENT
)

COMP007 = (
    RUN007
    / "V16E_BLREP_COMP_CUDA_007.pt"
)

HISTORY007 = (
    RUN007
    / "V16E_BLREP_COMP_CUDA_007_HISTORY.json"
)

RECOVERY007_E0800 = (
    RUN007
    / "recovery"
    / "V16E_BLREP_COMP_CUDA_007_RECOVERY_E0800.pt"
)

MANIFEST007 = (
    RUN007
    / "V16E_BLREP_COMP_CUDA_007_MANIFEST.json"
)

SUMMARY007 = (
    RUN007
    / "PAD_Stream_V16E1B2CUDA8DR1D_Summary.json"
)

HANDOFF007 = (
    RUN007
    / "V16E1B2CUDA8DR1D_Handoff.md"
)


PROVENANCE_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8E_COMP007_STAGE2_POSTTRAINING_CLOSURE"
)

PROVENANCE_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

RESULTS_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8E_COMP007_Stage2_Closure_Results.json"
)

DISPOSITION_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8E_COMP007_Stage2_Disposition.json"
)

SUMMARY_PATH = (
    PROVENANCE_ROOT
    / "PAD_Stream_V16E1B2CUDA8E_Summary.json"
)

HANDOFF_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8E_Handoff.md"
)


# =============================================================================
# Frozen hashes
# =============================================================================

EXPECTED = {
    "dataset":
        "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c",

    "CUDA6":
        "385e18b64ebf068a06e5daec11449e3700f69ad743627d4520905f273bf7c552",

    "CUDA8A_PROTOCOL":
        "cf7b29c6b93afb7fcbef8fbb3d4e1106d7cd77ddd46469de611af48431f445b6",

    "CUDA8BR_NORMALIZATION":
        "ccd0e61fc8fc8f73890e83f537bb047aaa5f408c8f4125209cc36d0b79df3549",

    "COMP004":
        "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69",

    "COMP005":
        "aaca2ae60d7a789bf6d3d2a177d1b3b5188181809597b1be6901ed7473e0906f",

    "RECOVERY005_E0800":
        "fbdbf6b7bff0b22625e7dbcd09500c258c6deeeec6ed4f846407f6e927435157",

    "R1C_SOURCE":
        "f2c8c62c52dfd13f6c3c1ccd24684e3aaa5d3c446f86f48d7abef10a8acb6a4d",

    "R1C_CONTRACT":
        "bc01b863f44129ab8e8b422c3ac95781ca35b47f7db4593b6d882f130b854882",

    "R1D_SOURCE":
        "f67ab2a2ec493f424e998b6c7a3672c4e9ee43e2bf9e38df75f052c6c4977a2f",

    "HISTORY007":
        "7fdd7c43bc17be272bfe0092b5755f207698f9bc9d51184f7f96cda6fe7beb5c",

    "COMP007":
        "98521407ab803b4899a75988c65f303f94e9447dd25e159e7cc3ffdb7e9c042d",

    "RECOVERY007_E0800":
        "e3db280a37850d969f5a78ca29f6f773c98ad51baee4d9610ab49f636680d075",

    "MANIFEST007":
        "6fa33a00b696f63480310a03203141d8380d5c695b1f8f5faf474183a3ff7ac3",

    "SUMMARY007":
        "e2a4a878001a898e31e32c2bb94390098fea58fea7788547b1d361bf4c6979db",

    "HANDOFF007":
        "df46bc4730c3bc5ec41aa952c86afeedc4b5942131d3f9d1edd1d38216699281",

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
# Frozen CUDA7D reference values
#
# Used ONLY to prove that CUDA8E reproduces the previous evaluator semantics
# for COMP004/COMP005 before COMP007 is judged.
# =============================================================================

CUDA7D_REFERENCE = {
    "COMP004": {
        "source_rmse":
            8.956999042247e-03,

        "corrected_residual_rmse":
            1.690626426764e-01,

        "tip_rmse":
            1.3539852e-03,

        "mono_violation_fraction":
            1.88436949e-02,
    },

    "COMP005": {
        "source_rmse":
            7.151701434023e-03,

        "corrected_residual_rmse":
            1.321106545751e-01,

        "tip_rmse":
            3.1320145e-03,

        "mono_violation_fraction":
            2.137841711e-01,
    },
}


# =============================================================================
# Closure contract
# =============================================================================

NC_VALUES = (
    0.00,
    0.05,
    0.10,
    0.20,
    0.30,
)

N_HOLDOUT = 2880

# Evaluation-only geometry. Same CUDA3 derivative authority, smaller microbatch
# than production for closure robustness. Every compared model uses the same
# evaluation geometry.
EVAL_MICROBATCH = 256
ADOPTED_CHUNK = 64

# Numerical tolerance for "at least as good as" comparisons.
REL_COMPARE_TOL = 1.0e-6
ABS_COMPARE_TOL = 1.0e-12

# Physical gates.
BOUND_TOL = 1.0e-6
ENDPOINT_TOL = 1.0e-6

# CUDA7D evaluator-parity tolerances.
REFERENCE_RMSE_ATOL = 2.0e-6
REFERENCE_PHYS_ATOL = 2.0e-5
REFERENCE_TIP_ATOL = 2.0e-5
REFERENCE_MONO_ATOL = 2.0e-5


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


def gate(name, condition):
    ok = bool(condition)

    print(
        f"[{'PASS' if ok else 'FAIL'}] {name}"
    )

    if not ok:
        raise RuntimeError(
            f"CUDA8E authority/parity gate failed: {name}"
        )


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


def finite_tensor(x):
    return bool(
        torch.isfinite(x)
        .all()
        .item()
    )


def native_nc_mask_np(values, nc):
    target = np.asarray(
        nc,
        dtype=values.dtype,
    )

    return values == target


def compare_le(candidate, reference):
    return (
        float(candidate)
        <=
        float(reference)
        * (
            1.0
            +
            REL_COMPARE_TOL
        )
        +
        ABS_COMPARE_TOL
    )


def extract_model_state(payload):
    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeError(
            "Checkpoint payload is not a dictionary."
        )

    for key in (
        "model_state_dict",
        "model_state",
        "state_dict",
    ):
        if key in payload:
            state = payload[
                key
            ]

            if isinstance(
                state,
                dict,
            ):
                return state

    # Support a raw state_dict checkpoint only if every value is tensor-like.
    if payload and all(
        torch.is_tensor(v)
        for v in payload.values()
    ):
        return payload

    raise RuntimeError(
        "No supported model state found in checkpoint."
    )


def load_strict(
    model,
    path,
):
    payload = torch.load(
        path,
        map_location="cpu",
        weights_only=False,
    )

    state = extract_model_state(
        payload
    )

    result = model.load_state_dict(
        state,
        strict=True,
    )

    if (
        len(
            result.missing_keys
        )
        !=
        0
        or
        len(
            result.unexpected_keys
        )
        !=
        0
    ):
        raise RuntimeError(
            f"Strict load failed for {path.name}."
        )

    return payload


def error_metrics(
    pred,
    truth,
):
    e = (
        pred
        -
        truth
    )

    mse = float(
        np.mean(
            e ** 2
        )
    )

    return {
        "mse":
            mse,

        "rmse":
            math.sqrt(
                mse
            ),

        "mae":
            float(
                np.mean(
                    np.abs(
                        e
                    )
                )
            ),

        "max_abs":
            float(
                np.max(
                    np.abs(
                        e
                    )
                )
            ),
    }


print("=" * 110)
print("PAD-Stream V16E-1B2CUDA8E")
print("COMP007 Post-Training Stage-2 Closure Evaluation")
print("=" * 110)

print()
print("HOLDOUT IS NOW OPENED FOR THE PRE-FROZEN STAGE-2 DECISION.")
print("NO TRAINING.")
print("NO MODEL SELECTION.")
print("NO THRESHOLD TUNING.")
print("NO OOD.")
print("NO TOF.")
print()


# =============================================================================
# Authority gates
# =============================================================================

AUTHORITY = {
    "dataset":
        DATASET,

    "CUDA6":
        CUDA6,

    "CUDA8A_PROTOCOL":
        CUDA8A_PROTOCOL,

    "CUDA8BR_NORMALIZATION":
        CUDA8BR_NORMALIZATION,

    "COMP004":
        COMP004,

    "COMP005":
        COMP005,

    "RECOVERY005_E0800":
        RECOVERY005_E0800,

    "R1C_SOURCE":
        R1C_SOURCE,

    "R1C_CONTRACT":
        R1C_CONTRACT,

    "R1D_SOURCE":
        R1D_SOURCE,

    "HISTORY007":
        HISTORY007,

    "COMP007":
        COMP007,

    "RECOVERY007_E0800":
        RECOVERY007_E0800,

    "MANIFEST007":
        MANIFEST007,

    "SUMMARY007":
        SUMMARY007,

    "HANDOFF007":
        HANDOFF007,
}


print("FROZEN AUTHORITY GATES")

for name, path in AUTHORITY.items():
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


# =============================================================================
# Final COMP007 checkpoint contract gates
# =============================================================================

ckpt007_payload = torch.load(
    COMP007,
    map_location="cpu",
    weights_only=False,
)


print()
print("COMP007 E0800 CONTRACT GATES")

gate(
    "COMP007_experiment_exact",
    ckpt007_payload[
        "experiment"
    ]
    ==
    EXPERIMENT,
)

gate(
    "COMP007_completed_epoch_800",
    int(
        ckpt007_payload[
            "completed_epoch"
        ]
    )
    ==
    800,
)

gate(
    "COMP007_optimizer_steps_1600",
    int(
        ckpt007_payload[
            "optimizer_steps_completed"
        ]
    )
    ==
    1600,
)

gate(
    "COMP007_runner_SHA_exact",
    ckpt007_payload[
        "runner_sha256"
    ]
    ==
    EXPECTED[
        "R1D_SOURCE"
    ],
)

gate(
    "COMP007_holdout_previously_dark",
    ckpt007_payload[
        "holdout_evaluated"
    ]
    is False,
)

gate(
    "COMP007_Stage2_not_predeclared_certified",
    ckpt007_payload[
        "Stage2_certified"
    ]
    is False,
)

gate(
    "COMP007_B3_not_predeclared_authorized",
    ckpt007_payload[
        "B3_authorized"
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
    .get_device_properties(
        0
    )
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
# Import exact scientific authorities
# =============================================================================

spec = importlib.util.spec_from_file_location(
    "cuda6_for_cuda8e",
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
    "cuda8e_B2S",
)

M = C.import_module(
    B2S.BASE_RUNNER,
    "cuda8e_M",
)

J = C.import_module(
    B2S.B2J_SOURCE,
    "cuda8e_J",
)

CUDA3 = C.import_module(
    C.CUDA3_SOURCE,
    "cuda8e_CUDA3",
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
# Dataset / exact split
# =============================================================================

with np.load(
    DATASET,
    allow_pickle=False,
) as d:
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

    ai_all = np.array(
        d[
            "ai"
        ],
        copy=True,
    )

    at_all = np.array(
        d[
            "at"
        ],
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


print()
print("SPLIT AUTHORITY GATES")

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


# Exact holdout arrays. From this point onward the holdout is evaluation-only.
xi_h = xi_all[
    holdout_idx
]

Sw_h = Sw_all[
    holdout_idx
]

p11_h = p11_all[
    holdout_idx
]

ai_h = ai_all[
    holdout_idx
]

at_h = at_all[
    holdout_idx
]

nc_h = p11_h[
    :,
    10
]


nc0_mask = native_nc_mask_np(
    nc_h,
    0.0,
)

ncpos_mask = ~nc0_mask


gate(
    "holdout_contains_Nc0",
    int(
        np.sum(
            nc0_mask
        )
    )
    >
    0,
)

gate(
    "holdout_contains_Nc_positive",
    int(
        np.sum(
            ncpos_mask
        )
    )
    >
    0,
)


# =============================================================================
# Models
# =============================================================================

BaseEtaModel = J.build_eta_model_class(
    M
)


class COMP007LiftedModel(BaseEtaModel):

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


def make_model(
    label,
    checkpoint,
    lifted,
):
    model = (
        COMP007LiftedModel()
        if lifted
        else BaseEtaModel()
    ).to(
        device
    )

    load_strict(
        model,
        checkpoint,
    )

    model.eval()

    print(
        f"[PASS] {label}_strict_checkpoint_load"
    )

    return model


# =============================================================================
# Common evaluation
# =============================================================================

engine = CUDA3.make_cuda3_chunked_batched_engine(
    ADOPTED_CHUNK
)

original_engine = (
    B2S.local_recurrent_derivatives_create_graph
)


def evaluate_model(
    label,
    checkpoint,
    lifted,
):
    print()
    print("-" * 110)
    print(
        f"EVALUATING {label}"
    )
    print("-" * 110)

    model = make_model(
        label,
        checkpoint,
        lifted,
    )


    # -------------------------------------------------------------------------
    # Source-native predictions / physical metrics.
    # -------------------------------------------------------------------------

    prediction_chunks = []


    with torch.no_grad():
        for m0 in range(
            0,
            N_HOLDOUT,
            EVAL_MICROBATCH,
        ):
            mids = slice(
                m0,
                min(
                    m0
                    +
                    EVAL_MICROBATCH,
                    N_HOLDOUT,
                ),
            )

            xi = torch.from_numpy(
                xi_h[
                    mids
                ]
            ).to(
                device
            )

            p11 = torch.from_numpy(
                p11_h[
                    mids
                ]
            ).to(
                device
            )


            with torch.backends.cudnn.flags(
                enabled=False
            ):
                pred = model(
                    xi,
                    p11,
                )


            if not finite_tensor(
                pred
            ):
                raise RuntimeError(
                    f"{label}: nonfinite source-native prediction."
                )


            prediction_chunks.append(
                pred.detach()
                .cpu()
                .numpy()
            )


            del (
                xi,
                p11,
                pred,
            )


    pred = np.concatenate(
        prediction_chunks,
        axis=0,
    )


    source_global = error_metrics(
        pred,
        Sw_h,
    )

    source_nc0 = error_metrics(
        pred[
            nc0_mask
        ],
        Sw_h[
            nc0_mask
        ],
    )

    source_ncpos = error_metrics(
        pred[
            ncpos_mask
        ],
        Sw_h[
            ncpos_mask
        ],
    )


    swc = p11_h[
        :,
        2
    ][
        :,
        None,
        None
    ]

    sor = p11_h[
        :,
        3
    ][
        :,
        None,
        None
    ]

    upper = (
        1.0
        -
        sor
    )


    lower_violation = float(
        np.max(
            np.maximum(
                swc
                -
                pred,
                0.0,
            )
        )
    )

    upper_violation = float(
        np.max(
            np.maximum(
                pred
                -
                upper,
                0.0,
            )
        )
    )


    inj_target = (
        1.0
        -
        p11_h[
            :,
            3
        ]
    )

    tip_target = p11_h[
        :,
        9
    ]


    inj_error = (
        pred[
            :,
            0,
            0
        ]
        -
        inj_target
    )

    tip_error = (
        pred[
            :,
            -1,
            0
        ]
        -
        tip_target
    )


    injector_rmse = math.sqrt(
        float(
            np.mean(
                inj_error
                ** 2
            )
        )
    )

    tip_rmse = math.sqrt(
        float(
            np.mean(
                tip_error
                ** 2
            )
        )
    )


    dS = (
        pred[
            :,
            1:,
            0
        ]
        -
        pred[
            :,
            :-1,
            0
        ]
    )


    mono_violation_fraction = float(
        np.mean(
            dS
            >
            0.0
        )
    )


    # Anchor RMSE via frozen anchor loss definition.
    anchor_mse_weighted = 0.0
    anchor_count = 0


    with torch.no_grad():
        for m0 in range(
            0,
            N_HOLDOUT,
            EVAL_MICROBATCH,
        ):
            m1 = min(
                m0
                +
                EVAL_MICROBATCH,
                N_HOLDOUT,
            )

            m = (
                m1
                -
                m0
            )

            pred_t = torch.from_numpy(
                pred[
                    m0:m1
                ]
            ).to(
                device
            )

            ai_t = torch.from_numpy(
                ai_h[
                    m0:m1
                ]
            ).to(
                device
            )

            at_t = torch.from_numpy(
                at_h[
                    m0:m1
                ]
            ).to(
                device
            )


            a = M.anchor_loss(
                pred_t,
                ai_t,
                at_t,
            )


            anchor_mse_weighted += (
                float(
                    a.detach()
                    .cpu()
                    .item()
                )
                *
                m
            )

            anchor_count += m


            del (
                pred_t,
                ai_t,
                at_t,
                a,
            )


    anchor_mse = (
        anchor_mse_weighted
        /
        anchor_count
    )

    anchor_rmse = math.sqrt(
        anchor_mse
    )


    # -------------------------------------------------------------------------
    # Corrected conservative residual.
    # -------------------------------------------------------------------------

    residual_chunks = []


    B2S.local_recurrent_derivatives_create_graph = (
        engine
    )


    try:
        for m0 in range(
            0,
            N_HOLDOUT,
            EVAL_MICROBATCH,
        ):
            m1 = min(
                m0
                +
                EVAL_MICROBATCH,
                N_HOLDOUT,
            )


            xi = (
                torch.from_numpy(
                    xi_h[
                        m0:m1
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

            p11 = (
                torch.from_numpy(
                    p11_h[
                        m0:m1
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
                    S_pred,
                    _unused_global,
                    residual,
                ) = (
                    B2S.corrected_physics_loss_training_graph(
                        M,
                        model,
                        xi,
                        p11,
                    )
                )


            if not all(
                finite_tensor(
                    value
                )
                for value in (
                    S_pred,
                    residual,
                )
            ):
                raise RuntimeError(
                    f"{label}: nonfinite corrected residual."
                )


            residual_chunks.append(
                residual.detach()
                .cpu()
                .numpy()
            )


            del (
                xi,
                p11,
                S_pred,
                residual,
                _unused_global,
            )


            torch.cuda.empty_cache()


    finally:
        B2S.local_recurrent_derivatives_create_graph = (
            original_engine
        )


    residual_np = np.concatenate(
        residual_chunks,
        axis=0,
    )


    def residual_metrics(mask):
        r = residual_np[
            mask
        ]

        mse = float(
            np.mean(
                r
                ** 2
            )
        )

        return {
            "mse":
                mse,

            "rmse":
                math.sqrt(
                    mse
                ),

            "mae":
                float(
                    np.mean(
                        np.abs(
                            r
                        )
                    )
                ),

            "max_abs":
                float(
                    np.max(
                        np.abs(
                            r
                        )
                    )
                ),
        }


    physics_global = residual_metrics(
        np.ones(
            N_HOLDOUT,
            dtype=bool,
        )
    )

    physics_nc0 = residual_metrics(
        nc0_mask
    )

    physics_ncpos = residual_metrics(
        ncpos_mask
    )


    metrics = {
        "source_native": {
            "global":
                source_global,

            "Nc0":
                source_nc0,

            "Nc_positive":
                source_ncpos,
        },

        "corrected_residual": {
            "global":
                physics_global,

            "Nc0":
                physics_nc0,

            "Nc_positive":
                physics_ncpos,
        },

        "physical": {
            "prediction_finite":
                bool(
                    np.isfinite(
                        pred
                    ).all()
                ),

            "residual_finite":
                bool(
                    np.isfinite(
                        residual_np
                    ).all()
                ),

            "lower_bound_max_violation":
                lower_violation,

            "upper_bound_max_violation":
                upper_violation,

            "injector_rmse":
                injector_rmse,

            "tip_rmse":
                tip_rmse,

            "anchor_rmse":
                anchor_rmse,

            "mono_violation_fraction":
                mono_violation_fraction,

            # Sw_star is the frozen Rankine-Hugoniot shock-state authority
            # carried in p11 index 9. The moving-domain tip must match it.
            "RH_tip_state_max_abs":
                float(
                    np.max(
                        np.abs(
                            tip_error
                        )
                    )
                ),
        },
    }


    print(
        "Source global RMSE      :",
        f"{source_global['rmse']:.12e}",
    )

    print(
        "Source Nc=0 RMSE        :",
        f"{source_nc0['rmse']:.12e}",
    )

    print(
        "Source Nc>0 RMSE        :",
        f"{source_ncpos['rmse']:.12e}",
    )

    print(
        "Corrected global RMSE   :",
        f"{physics_global['rmse']:.12e}",
    )

    print(
        "Corrected Nc=0 RMSE     :",
        f"{physics_nc0['rmse']:.12e}",
    )

    print(
        "Corrected Nc>0 RMSE     :",
        f"{physics_ncpos['rmse']:.12e}",
    )

    print(
        "Tip RMSE                :",
        f"{tip_rmse:.12e}",
    )

    print(
        "Mono violation fraction :",
        f"{mono_violation_fraction:.12e}",
    )


    del model
    torch.cuda.empty_cache()


    return metrics


# =============================================================================
# Dataset RH-tip authority check
# =============================================================================

teacher_tip_max_abs = float(
    np.max(
        np.abs(
            Sw_h[
                :,
                -1,
                0
            ]
            -
            p11_h[
                :,
                9
            ]
        )
    )
)

gate(
    "holdout_teacher_RH_tip_contract",
    teacher_tip_max_abs
    <=
    ENDPOINT_TOL,
)


# =============================================================================
# Evaluate all models identically
# =============================================================================

metrics004 = evaluate_model(
    "COMP004",
    COMP004,
    lifted=False,
)

metrics005 = evaluate_model(
    "COMP005",
    COMP005,
    lifted=False,
)

metrics007 = evaluate_model(
    "COMP007",
    COMP007,
    lifted=True,
)


# =============================================================================
# Evaluator parity with CUDA7D
# =============================================================================

print()
print("=" * 110)
print("CUDA7D EVALUATOR PARITY GATES")
print("=" * 110)


def parity_gate(
    name,
    observed,
    expected,
    atol,
):
    diff = abs(
        float(
            observed
        )
        -
        float(
            expected
        )
    )

    ok = (
        diff
        <=
        atol
    )

    print(
        f"[{'PASS' if ok else 'FAIL'}] "
        f"{name} "
        f"| observed={observed:.12e} "
        f"| reference={expected:.12e} "
        f"| abs_diff={diff:.3e}"
    )

    return ok


parity = {
    "COMP004_source_rmse":
        parity_gate(
            "COMP004_source_rmse",
            metrics004[
                "source_native"
            ][
                "global"
            ][
                "rmse"
            ],
            CUDA7D_REFERENCE[
                "COMP004"
            ][
                "source_rmse"
            ],
            REFERENCE_RMSE_ATOL,
        ),

    "COMP005_source_rmse":
        parity_gate(
            "COMP005_source_rmse",
            metrics005[
                "source_native"
            ][
                "global"
            ][
                "rmse"
            ],
            CUDA7D_REFERENCE[
                "COMP005"
            ][
                "source_rmse"
            ],
            REFERENCE_RMSE_ATOL,
        ),

    "COMP004_corrected_rmse":
        parity_gate(
            "COMP004_corrected_rmse",
            metrics004[
                "corrected_residual"
            ][
                "global"
            ][
                "rmse"
            ],
            CUDA7D_REFERENCE[
                "COMP004"
            ][
                "corrected_residual_rmse"
            ],
            REFERENCE_PHYS_ATOL,
        ),

    "COMP005_corrected_rmse":
        parity_gate(
            "COMP005_corrected_rmse",
            metrics005[
                "corrected_residual"
            ][
                "global"
            ][
                "rmse"
            ],
            CUDA7D_REFERENCE[
                "COMP005"
            ][
                "corrected_residual_rmse"
            ],
            REFERENCE_PHYS_ATOL,
        ),

    "COMP004_tip_rmse":
        parity_gate(
            "COMP004_tip_rmse",
            metrics004[
                "physical"
            ][
                "tip_rmse"
            ],
            CUDA7D_REFERENCE[
                "COMP004"
            ][
                "tip_rmse"
            ],
            REFERENCE_TIP_ATOL,
        ),

    "COMP005_tip_rmse":
        parity_gate(
            "COMP005_tip_rmse",
            metrics005[
                "physical"
            ][
                "tip_rmse"
            ],
            CUDA7D_REFERENCE[
                "COMP005"
            ][
                "tip_rmse"
            ],
            REFERENCE_TIP_ATOL,
        ),

    "COMP004_mono_fraction":
        parity_gate(
            "COMP004_mono_fraction",
            metrics004[
                "physical"
            ][
                "mono_violation_fraction"
            ],
            CUDA7D_REFERENCE[
                "COMP004"
            ][
                "mono_violation_fraction"
            ],
            REFERENCE_MONO_ATOL,
        ),

    "COMP005_mono_fraction":
        parity_gate(
            "COMP005_mono_fraction",
            metrics005[
                "physical"
            ][
                "mono_violation_fraction"
            ],
            CUDA7D_REFERENCE[
                "COMP005"
            ][
                "mono_violation_fraction"
            ],
            REFERENCE_MONO_ATOL,
        ),
}


parity_pass = all(
    parity.values()
)


if not parity_pass:
    raise RuntimeError(
        "CUDA8E evaluator does not reproduce frozen CUDA7D semantics. "
        "Stage-2 disposition is blocked."
    )


# =============================================================================
# Frozen Stage-2 acceptance gates
# =============================================================================

print()
print("=" * 110)
print("STAGE-2 ACCEPTANCE GATES")
print("=" * 110)


acceptance = {
    # Preserve COMP005 global source-native accuracy.
    "preserve_COMP005_global_source_RMSE":
        compare_le(
            metrics007[
                "source_native"
            ][
                "global"
            ][
                "rmse"
            ],
            metrics005[
                "source_native"
            ][
                "global"
            ][
                "rmse"
            ],
        ),

    # Preserve COMP005 positive-Nc source-native accuracy.
    "preserve_COMP005_Nc_positive_source_RMSE":
        compare_le(
            metrics007[
                "source_native"
            ][
                "Nc_positive"
            ][
                "rmse"
            ],
            metrics005[
                "source_native"
            ][
                "Nc_positive"
            ][
                "rmse"
            ],
        ),

    # Preserve COMP005 global corrected conservative physics.
    "preserve_COMP005_global_corrected_RMSE":
        compare_le(
            metrics007[
                "corrected_residual"
            ][
                "global"
            ][
                "rmse"
            ],
            metrics005[
                "corrected_residual"
            ][
                "global"
            ][
                "rmse"
            ],
        ),

    # Preserve COMP005 positive-Nc corrected physics.
    "preserve_COMP005_Nc_positive_corrected_RMSE":
        compare_le(
            metrics007[
                "corrected_residual"
            ][
                "Nc_positive"
            ][
                "rmse"
            ],
            metrics005[
                "corrected_residual"
            ][
                "Nc_positive"
            ][
                "rmse"
            ],
        ),

    # Restore Nc=0 source-native regression to at least COMP004.
    "restore_COMP004_Nc0_source_RMSE":
        compare_le(
            metrics007[
                "source_native"
            ][
                "Nc0"
            ][
                "rmse"
            ],
            metrics004[
                "source_native"
            ][
                "Nc0"
            ][
                "rmse"
            ],
        ),

    # Restore Nc=0 corrected-physics regression to at least COMP004.
    "restore_COMP004_Nc0_corrected_RMSE":
        compare_le(
            metrics007[
                "corrected_residual"
            ][
                "Nc0"
            ][
                "rmse"
            ],
            metrics004[
                "corrected_residual"
            ][
                "Nc0"
            ][
                "rmse"
            ],
        ),

    # Restore tip behavior to at least COMP004.
    "restore_COMP004_tip_RMSE":
        compare_le(
            metrics007[
                "physical"
            ][
                "tip_rmse"
            ],
            metrics004[
                "physical"
            ][
                "tip_rmse"
            ],
        ),

    # Restore monotonicity to at least COMP004.
    "restore_COMP004_mono_violation_fraction":
        compare_le(
            metrics007[
                "physical"
            ][
                "mono_violation_fraction"
            ],
            metrics004[
                "physical"
            ][
                "mono_violation_fraction"
            ],
        ),

    # Physical gates.
    "predictions_finite":
        metrics007[
            "physical"
        ][
            "prediction_finite"
        ]
        is True,

    "corrected_residual_finite":
        metrics007[
            "physical"
        ][
            "residual_finite"
        ]
        is True,

    "lower_bound_PASS":
        metrics007[
            "physical"
        ][
            "lower_bound_max_violation"
        ]
        <=
        BOUND_TOL,

    "upper_bound_PASS":
        metrics007[
            "physical"
        ][
            "upper_bound_max_violation"
        ]
        <=
        BOUND_TOL,

    "injector_hard_boundary_PASS":
        metrics007[
            "physical"
        ][
            "injector_rmse"
        ]
        <=
        ENDPOINT_TOL,

    "RH_tip_state_PASS":
        metrics007[
            "physical"
        ][
            "RH_tip_state_max_abs"
        ]
        <=
        ENDPOINT_TOL,
}


for name, ok in acceptance.items():
    print(
        f"[{'PASS' if ok else 'FAIL'}] "
        f"{name}"
    )


all_acceptance_pass = all(
    acceptance.values()
)


# =============================================================================
# Disposition
# =============================================================================

if all_acceptance_pass:
    STAGE2_CERTIFIED = True
    B3_AUTHORIZED = True

    disposition = (
        "STAGE2_COMPRESSIBLE_CERTIFIED_"
        "COMP007_ALL_FROZEN_ACCEPTANCE_GATES_PASS_"
        "B3_CAPILLARY_STAGE3_AUTHORIZED"
    )

    next_milestone = (
        "V16E-1B3 — Stage-3 Capillary BL PI-RNN "
        "reproduction/development under the frozen four-phase BL roadmap"
    )

else:
    STAGE2_CERTIFIED = False
    B3_AUTHORIZED = False

    disposition = (
        "STAGE2_COMPRESSIBLE_NOT_CERTIFIED_"
        "ONE_OR_MORE_FROZEN_ACCEPTANCE_GATES_FAIL_"
        "B3_REMAINS_BLOCKED"
    )

    next_milestone = (
        "Stage-2 evidence review only. "
        "No B3 and no holdout-driven retraining."
    )


RUNNER_SHA = sha256(
    Path(
        __file__
    )
)


results = {
    "milestone":
        MILESTONE,

    "experiment":
        EXPERIMENT,

    "runner_sha256":
        RUNNER_SHA,

    "holdout_opened":
        True,

    "holdout_profiles":
        N_HOLDOUT,

    "holdout_idx_sha256":
        EXPECTED[
            "holdout_idx"
        ],

    "evaluation_geometry": {
        "microbatch":
            EVAL_MICROBATCH,

        "CUDA3_VJP_chunk":
            ADOPTED_CHUNK,
    },

    "CUDA7D_parity":
        parity,

    "CUDA7D_parity_PASS":
        parity_pass,

    "COMP004":
        metrics004,

    "COMP005":
        metrics005,

    "COMP007":
        metrics007,

    "acceptance_gates":
        acceptance,

    "all_acceptance_gates_PASS":
        all_acceptance_pass,

    "Stage2_certified":
        STAGE2_CERTIFIED,

    "B3_authorized":
        B3_AUTHORIZED,

    "disposition":
        disposition,

    "next_milestone":
        next_milestone,

    "OOD_used":
        False,

    "TOF_used":
        False,
}


atomic_json(
    RESULTS_PATH,
    results,
)


RESULTS_SHA = sha256(
    RESULTS_PATH
)


disposition_artifact = {
    "milestone":
        MILESTONE,

    "experiment":
        EXPERIMENT,

    "runner_sha256":
        RUNNER_SHA,

    "results_sha256":
        RESULTS_SHA,

    "all_acceptance_gates_PASS":
        all_acceptance_pass,

    "Stage2_certified":
        STAGE2_CERTIFIED,

    "B3_authorized":
        B3_AUTHORIZED,

    "disposition":
        disposition,

    "next_milestone":
        next_milestone,
}


atomic_json(
    DISPOSITION_PATH,
    disposition_artifact,
)


DISPOSITION_SHA = sha256(
    DISPOSITION_PATH
)


summary = {
    "milestone":
        MILESTONE,

    "experiment":
        EXPERIMENT,

    "runner_sha256":
        RUNNER_SHA,

    "results_sha256":
        RESULTS_SHA,

    "disposition_sha256":
        DISPOSITION_SHA,

    "Stage2_certified":
        STAGE2_CERTIFIED,

    "B3_authorized":
        B3_AUTHORIZED,

    "disposition":
        disposition,

    "next_milestone":
        next_milestone,

    "holdout_evaluated":
        True,

    "OOD_used":
        False,

    "TOF_used":
        False,
}


atomic_json(
    SUMMARY_PATH,
    summary,
)


SUMMARY_SHA = sha256(
    SUMMARY_PATH
)


handoff = f"""# PAD-Stream V16E-1B2CUDA8E

## Purpose

Post-training Stage-2 closure for frozen COMP007.

The exact source-native holdout is opened only after the authorized E0800
production checkpoint exists. No training, model selection, threshold tuning,
OOD, or TOF work occurs in this milestone.

## Evaluator parity

CUDA8E first reproduces the frozen CUDA7D COMP004/COMP005 reference metrics.
Parity pass:

`{parity_pass}`

## Stage-2 disposition

All frozen acceptance gates pass:

`{all_acceptance_pass}`

Stage 2 certified:

`{STAGE2_CERTIFIED}`

B3 authorized:

`{B3_AUTHORIZED}`

Disposition:

`{disposition}`

## COMP007 headline holdout metrics

Source-native global RMSE:

`{metrics007["source_native"]["global"]["rmse"]:.12e}`

Source-native Nc=0 RMSE:

`{metrics007["source_native"]["Nc0"]["rmse"]:.12e}`

Source-native Nc>0 RMSE:

`{metrics007["source_native"]["Nc_positive"]["rmse"]:.12e}`

Corrected-residual global RMSE:

`{metrics007["corrected_residual"]["global"]["rmse"]:.12e}`

Corrected-residual Nc=0 RMSE:

`{metrics007["corrected_residual"]["Nc0"]["rmse"]:.12e}`

Corrected-residual Nc>0 RMSE:

`{metrics007["corrected_residual"]["Nc_positive"]["rmse"]:.12e}`

Tip RMSE:

`{metrics007["physical"]["tip_rmse"]:.12e}`

Monotonicity violation fraction:

`{metrics007["physical"]["mono_violation_fraction"]:.12e}`

## Hashes

Runner SHA-256:

`{RUNNER_SHA}`

Results SHA-256:

`{RESULTS_SHA}`

Disposition SHA-256:

`{DISPOSITION_SHA}`

Summary SHA-256:

`{SUMMARY_SHA}`

## Next

{next_milestone}
"""


HANDOFF_PATH.write_text(
    handoff,
    encoding="utf-8",
)


HANDOFF_SHA = sha256(
    HANDOFF_PATH
)


# =============================================================================
# Final report
# =============================================================================

print()
print("=" * 110)
print("CUDA8E STAGE-2 CLOSURE RESULT")
print("=" * 110)

print()
print("COMP007 HEADLINE HOLDOUT METRICS")

print(
    "  Source global RMSE    :",
    f"{metrics007['source_native']['global']['rmse']:.12e}",
)

print(
    "  Source Nc=0 RMSE      :",
    f"{metrics007['source_native']['Nc0']['rmse']:.12e}",
)

print(
    "  Source Nc>0 RMSE      :",
    f"{metrics007['source_native']['Nc_positive']['rmse']:.12e}",
)

print(
    "  Corrected global RMSE :",
    f"{metrics007['corrected_residual']['global']['rmse']:.12e}",
)

print(
    "  Corrected Nc=0 RMSE   :",
    f"{metrics007['corrected_residual']['Nc0']['rmse']:.12e}",
)

print(
    "  Corrected Nc>0 RMSE   :",
    f"{metrics007['corrected_residual']['Nc_positive']['rmse']:.12e}",
)

print(
    "  Tip RMSE              :",
    f"{metrics007['physical']['tip_rmse']:.12e}",
)

print(
    "  Mono violation frac   :",
    f"{metrics007['physical']['mono_violation_fraction']:.12e}",
)

print()
print(
    "ALL ACCEPTANCE GATES PASS:",
    all_acceptance_pass,
)

print(
    "STAGE 2 CERTIFIED:",
    STAGE2_CERTIFIED,
)

print(
    "B3 AUTHORIZED:",
    B3_AUTHORIZED,
)

print(
    "DISPOSITION:",
    disposition,
)

print(
    "NEXT:",
    next_milestone,
)

print()
print(
    "Runner SHA      :",
    RUNNER_SHA,
)

print(
    "Results SHA     :",
    RESULTS_SHA,
)

print(
    "Disposition SHA :",
    DISPOSITION_SHA,
)

print(
    "Summary SHA     :",
    SUMMARY_SHA,
)

print(
    "Handoff SHA     :",
    HANDOFF_SHA,
)
