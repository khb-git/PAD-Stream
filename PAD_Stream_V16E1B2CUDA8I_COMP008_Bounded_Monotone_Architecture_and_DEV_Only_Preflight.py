#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import math
import os
import sys

import numpy as np
import torch
import torch.nn.functional as F


# =============================================================================
# PAD-Stream V16E-1B2CUDA8I
#
# COMP008 Bounded-Monotone Architecture Implementation
# and DEV-Only Stage-2 Preflight
#
# FINAL DIAGNOSTIC / IMPLEMENTATION MILESTONE FOR CURRENT STAGE-2 CYCLE.
#
# PURPOSE
# -------
# 1. Use the NEW DEV dataset only to test whether COMP007 independently
#    reproduces the retrospective Nc=0 injector-side corrected-residual pattern.
#
# 2. Implement and preflight the CUDA8G bounded-monotone COMP008 output map:
#
#       z_i  ->  positive interval decrement q_j
#            ->  normalized interval weight w_j
#            ->  cumulative coordinate C_i
#            ->  S_i = S_inj - (S_inj - Sw*) C_i
#
#    This must make, by construction:
#       - injector endpoint exact,
#       - shock-tip endpoint exact,
#       - upper/lower saturation bounds exact,
#       - non-increasing saturation exact to numerical tolerance.
#
# 3. Verify corrected-physics derivative-engine parity and finite backward graph
#    on DEV only.
#
# NO TRAINING.
# NO OPTIMIZER STEP.
# NO BLIND CERT SCIENTIFIC INSPECTION.
# NO OOD.
# NO TOF.
# B3 REMAINS BLOCKED.
#
# If CUDA8I passes, CUDA8J is authorized as the FINAL Stage-2 development
# decision / COMP008 training-contract freeze.
# =============================================================================


MILESTONE = "V16E-1B2CUDA8I"
PROSPECTIVE_EXPERIMENT = "V16E-BLREP-COMP-CUDA-008"


# =============================================================================
# Paths
# =============================================================================

REPO = Path("/content/PAD-Stream")
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")


CUDA8G_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8G_Stage2_Architecture_Redesign_and_New_Certification_Protocol_Freeze.py"
)

CUDA8G_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_redesign"
    / "V16E1B2CUDA8G_ARCHITECTURE_AND_CERTIFICATION_PROTOCOL_FREEZE"
)

CUDA8G_ARCHITECTURE = (
    CUDA8G_ROOT
    / "V16E1B2CUDA8G_COMP008_Bounded_Monotone_Architecture_Protocol.json"
)

CUDA8G_DATA_PROTOCOL = (
    CUDA8G_ROOT
    / "V16E1B2CUDA8G_New_SourceNative_Data_Protocol.json"
)

CUDA8G_CERTIFICATION = (
    CUDA8G_ROOT
    / "V16E1B2CUDA8G_Stage2_Certification_Protocol.json"
)


CUDA8HRR1_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8HRR1_CUDA8H_SHA_Literal_Repair_Generate_and_Freeze_New_DEV_and_Blind_CERT_Datasets.py"
)

CUDA8HRR1_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_redesign"
    / "V16E1B2CUDA8HRR1_NEW_DEV_AND_BLIND_CERT_DATA_FREEZE"
)

CUDA8HRR1_RESULTS = (
    CUDA8HRR1_ROOT
    / "V16E1B2CUDA8HRR1_Data_Generation_Results.json"
)

CUDA8HRR1_SUMMARY = (
    CUDA8HRR1_ROOT
    / "PAD_Stream_V16E1B2CUDA8HRR1_Summary.json"
)

CUDA8HRR1_HANDOFF = (
    CUDA8HRR1_ROOT
    / "V16E1B2CUDA8HRR1_Handoff.md"
)


DEV_DATASET = (
    DRIVE
    / "datasets"
    / "stage2_redesign"
    / "V16E_STAGE2_DEV_GODUNOV_SEED20260918.npz"
)

DEV_META = (
    DRIVE
    / "datasets"
    / "stage2_redesign"
    / "V16E_STAGE2_DEV_GODUNOV_SEED20260918.json"
)

DEV_SELECTION = (
    DRIVE
    / "datasets"
    / "stage2_redesign"
    / "V16E_STAGE2_DEV_GODUNOV_SEED20260918_SELECTION.npy"
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


CUDA6 = (
    REPO
    / "PAD_Stream_V16E1B2CUDA6_A100_COMP_CUDA_005_Authorized_Production_Runner.py"
)

COMP004 = (
    DRIVE
    / "provenance"
    / "xpu_reference"
    / "V16E_BLREP_COMP_XPU_004.pt"
)

RUN007 = (
    DRIVE
    / "runs"
    / "V16E-BLREP-COMP-CUDA-007"
)

COMP007 = (
    RUN007
    / "V16E_BLREP_COMP_CUDA_007.pt"
)


PROVENANCE_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_redesign"
    / "V16E1B2CUDA8I_COMP008_BOUNDED_MONOTONE_DEV_PREFLIGHT"
)

PROVENANCE_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

RESULTS_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8I_COMP008_DEV_Preflight_Results.json"
)

SUMMARY_PATH = (
    PROVENANCE_ROOT
    / "PAD_Stream_V16E1B2CUDA8I_Summary.json"
)

HANDOFF_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8I_Handoff.md"
)


# =============================================================================
# Frozen hashes
# =============================================================================

EXPECTED = {
    "CUDA8G_SOURCE":
        "af7cbe21f216be173add5e59c954707931e433459d1bf817a0ec711bee1267b2",

    "CUDA8G_ARCHITECTURE":
        "e5c61bf1cb3c7b64acd52584c9a076253ae36fd51b7cca3e5fdd9aa7a1b2d135",

    "CUDA8G_DATA_PROTOCOL":
        "9c309766cc23b776a3a8db5ebac2c5c8d2ff5ed5a1eb7d79c6e7ca954211514b",

    "CUDA8G_CERTIFICATION":
        "eda537ef04b83fc22ed61881ea204136e531bdf330bbced6f497eff40f6e8490",

    "CUDA8HRR1_SOURCE":
        "eefec7b67ebab7b88f354495e9d238abb57984050f92233855c77b5e27b3c34d",

    "CUDA8HRR1_RESULTS":
        "3a8d540f72987135d67a83edadb925e7b54f942be81f4232716197839ff99e72",

    "CUDA8HRR1_SUMMARY":
        "563f47952f15036f621a3270f98f7fdb328ffbfd563f4a1124aef0253cfef138",

    "CUDA8HRR1_HANDOFF":
        "877a8eec927f09b213be5c8f297efa4754b3c6d121ab4d7eea444b5bd3997714",

    "DEV_DATASET":
        "55e5fe6868d78c930192af3af59d931275a83aa1f3ca46595969429718063821",

    "DEV_SELECTION":
        "79f680d42fd5c4de6f59385f88991af1b5013cd0090a486432c7bd4ec86f0359",

    "BLIND_CERT":
        "0eaf3fc1a6be77b2b804baf54e03837346754a411b92e5b1b19f83f3d8ddf265",

    "BLIND_CERT_SEAL":
        "7dd0bdd24c05e8d0265f77030247da3739b00eeca41af8c9495c22eaddc1c1ae",

    "CUDA6":
        "385e18b64ebf068a06e5daec11449e3700f69ad743627d4520905f273bf7c552",

    "COMP004":
        "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69",

    "COMP007":
        "98521407ab803b4899a75988c65f303f94e9447dd25e159e7cc3ffdb7e9c042d",

    "B2S":
        "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea",

    "BASE_M":
        "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18",

    "ETA_J":
        "fcc4074863a46f6b8d356a01ff0b4b2182d0ffa3ebc9b3fd053e35282f897a4c",

    "CUDA3":
        "1065788f8f82d7f58aba873b8396cf70a17906571421315151640a0c879df886",
}


# =============================================================================
# Preflight constants
# =============================================================================

EXPECTED_DEV_PROFILES = 2880
N_FAN = 64

EVAL_MICROBATCH = 256
VJP_CHUNK = 16

STRUCT_TOL = 1.0e-6
DERIVATIVE_PARITY_ATOL = 5.0e-6
GRAD_PARITY_ATOL = 2.0e-5

RETROSPECTIVE_INLET_XI_MAX = 0.16

NC_VALUES = (
    0.00,
    0.05,
    0.10,
    0.20,
    0.30,
)


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
    arr = np.ascontiguousarray(
        np.asarray(x)
    )

    return hashlib.sha256(
        arr.tobytes(order="C")
    ).hexdigest()


def gate(name, condition):
    ok = bool(condition)

    print(
        f"[{'PASS' if ok else 'FAIL'}] {name}"
    )

    if not ok:
        raise RuntimeError(
            f"CUDA8I preflight gate failed: {name}"
        )


def atomic_json(path: Path, obj):
    tmp = Path(
        str(path)
        +
        ".tmp"
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


def import_by_path(
    name,
    path,
):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


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
        if (
            key in payload
            and isinstance(
                payload[
                    key
                ],
                dict,
            )
        ):
            return payload[
                key
            ]

    if payload and all(
        torch.is_tensor(v)
        for v in payload.values()
    ):
        return payload

    raise RuntimeError(
        "No supported model state found."
    )


def strict_load(
    model,
    path,
):
    payload = torch.load(
        path,
        map_location="cpu",
        weights_only=False,
    )

    result = model.load_state_dict(
        extract_model_state(
            payload
        ),
        strict=True,
    )

    if (
        result.missing_keys
        or
        result.unexpected_keys
    ):
        raise RuntimeError(
            f"Strict checkpoint load failed: {path.name}"
        )

    return payload


def finite_tensor(x):
    return bool(
        torch.isfinite(x)
        .all()
        .item()
    )


def native_nc_mask(
    values,
    nc,
):
    target = np.asarray(
        nc,
        dtype=values.dtype,
    )

    return values == target


def error_metrics(
    pred,
    truth,
):
    error = (
        pred
        -
        truth
    )

    mse = float(
        np.mean(
            error ** 2
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
                        error
                    )
                )
            ),

        "max_abs":
            float(
                np.max(
                    np.abs(
                        error
                    )
                )
            ),
    }


def rmse(x):
    return math.sqrt(
        float(
            np.mean(
                np.asarray(
                    x
                )
                ** 2
            )
        )
    )


print("=" * 110)
print("PAD-Stream V16E-1B2CUDA8I")
print("COMP008 Bounded-Monotone Architecture Implementation and DEV-Only Preflight")
print("=" * 110)

print()
print("FINAL DIAGNOSTIC / IMPLEMENTATION MILESTONE FOR CURRENT STAGE-2 CYCLE.")
print("NO TRAINING.")
print("NO OPTIMIZER STEP.")
print("BLIND CERT SCIENTIFIC INSPECTION: FORBIDDEN.")
print("NO OOD.")
print("NO TOF.")
print("B3 REMAINS BLOCKED.")
print()


# =============================================================================
# Frozen authority gates
# =============================================================================

AUTHORITY = {
    "CUDA8G_SOURCE":
        CUDA8G_SOURCE,

    "CUDA8G_ARCHITECTURE":
        CUDA8G_ARCHITECTURE,

    "CUDA8G_DATA_PROTOCOL":
        CUDA8G_DATA_PROTOCOL,

    "CUDA8G_CERTIFICATION":
        CUDA8G_CERTIFICATION,

    "CUDA8HRR1_SOURCE":
        CUDA8HRR1_SOURCE,

    "CUDA8HRR1_RESULTS":
        CUDA8HRR1_RESULTS,

    "CUDA8HRR1_SUMMARY":
        CUDA8HRR1_SUMMARY,

    "CUDA8HRR1_HANDOFF":
        CUDA8HRR1_HANDOFF,

    "DEV_DATASET":
        DEV_DATASET,

    "DEV_SELECTION":
        DEV_SELECTION,

    "BLIND_CERT":
        BLIND_CERT,

    "BLIND_CERT_SEAL":
        BLIND_CERT_SEAL,

    "CUDA6":
        CUDA6,

    "COMP004":
        COMP004,

    "COMP007":
        COMP007,
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


# NOTE:
# BLIND_CERT is HASHED ONLY above.
# It is intentionally never opened or loaded anywhere in CUDA8I.


hrr1 = json.loads(
    CUDA8HRR1_RESULTS.read_text(
        encoding="utf-8"
    )
)


gate(
    "HRR1_DEV_profiles_2880",
    int(
        hrr1[
            "DEV"
        ][
            "profiles"
        ]
    )
    ==
    EXPECTED_DEV_PROFILES,
)

gate(
    "HRR1_BLIND_CERT_scientifically_sealed",
    hrr1[
        "BLIND_CERT"
    ][
        "scientifically_sealed"
    ]
    is True,
)

gate(
    "HRR1_COMP008_preflight_authorized",
    hrr1[
        "COMP008_implementation_preflight_authorized"
    ]
    is True,
)

gate(
    "HRR1_COMP008_training_not_authorized",
    hrr1[
        "COMP008_training_authorized"
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
print("  PyTorch :", torch.__version__)
print("  GPU     :", gpu_name)
print("  Memory  :", f"{gpu_total_gib:.3f} GiB")


gate(
    "A100_runtime",
    "A100"
    in gpu_name,
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

C = import_by_path(
    "cuda8i_cuda6",
    CUDA6,
)

B2S = C.import_module(
    C.B2S_SOURCE,
    "cuda8i_B2S",
)

M = C.import_module(
    B2S.BASE_RUNNER,
    "cuda8i_M",
)

J = C.import_module(
    B2S.B2J_SOURCE,
    "cuda8i_J",
)

CUDA3 = C.import_module(
    C.CUDA3_SOURCE,
    "cuda8i_CUDA3",
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
# Load DEV only
# =============================================================================

with np.load(
    DEV_DATASET,
    allow_pickle=False,
) as d:
    keys = set(
        d.files
    )

    gate(
        "DEV_schema_exact",
        keys
        ==
        {
            "xi",
            "Sw",
            "p11",
            "tD",
            "ai",
            "at",
        },
    )

    xi_dev = np.array(
        d[
            "xi"
        ],
        copy=True,
    )

    Sw_dev = np.array(
        d[
            "Sw"
        ],
        copy=True,
    )

    p11_dev = np.array(
        d[
            "p11"
        ],
        copy=True,
    )

    tD_dev = np.array(
        d[
            "tD"
        ],
        copy=True,
    )


print()
print("DEV STRUCTURE")

print("  xi  :", xi_dev.shape)
print("  Sw  :", Sw_dev.shape)
print("  p11 :", p11_dev.shape)
print("  tD  :", tD_dev.shape)


gate(
    "DEV_profile_count_2880",
    xi_dev.shape[
        0
    ]
    ==
    EXPECTED_DEV_PROFILES,
)

gate(
    "DEV_fan_nodes_64",
    xi_dev.shape[
        1
    ]
    ==
    N_FAN,
)

gate(
    "DEV_arrays_finite",
    all(
        np.isfinite(
            arr
        ).all()
        for arr in (
            xi_dev,
            Sw_dev,
            p11_dev,
            tD_dev,
        )
    ),
)


nc_dev = p11_dev[
    :,
    10
]

nc0_mask = native_nc_mask(
    nc_dev,
    0.0,
)

ncpos_mask = ~nc0_mask


for nc in NC_VALUES:
    gate(
        f"DEV_contains_Nc_{nc:.2f}",
        int(
            np.sum(
                native_nc_mask(
                    nc_dev,
                    nc,
                )
            )
        )
        >
        0,
    )


# Physical ordering required by bounded-monotone construction.
S_inj_dev = (
    1.0
    -
    p11_dev[
        :,
        3
    ]
)

Sw_star_dev = p11_dev[
    :,
    9
]

swc_dev = p11_dev[
    :,
    2
]


gate(
    "DEV_Sinj_ge_Swstar",
    np.all(
        S_inj_dev
        +
        STRUCT_TOL
        >=
        Sw_star_dev
    ),
)

gate(
    "DEV_Swstar_ge_swc",
    np.all(
        Sw_star_dev
        +
        STRUCT_TOL
        >=
        swc_dev
    ),
)


# =============================================================================
# Model definitions
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
            *
            (
                S_inj
                -
                S0
            )

            + xi_seq
            *
            (
                Sw_star
                -
                S1
            )
        )


class COMP008BoundedMonotoneModel(BaseEtaModel):
    """
    Same recurrent trunk / parameter state layout as COMP007, but the raw
    scalar sequence is interpreted as latent logits z_i.

    The output map itself enforces:
      S(0) = S_inj
      S(1) = Sw_star
      Sw_star <= S <= S_inj
      S[i+1] <= S[i]
    """

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

        # Positive interval decrement strengths.
        interval_logits = 0.5 * (
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

        q = (
            F.softplus(
                interval_logits
            )
            +
            self.EPSILON
        )

        denom = q.sum(
            dim=1,
            keepdim=True,
        )

        w = (
            q
            /
            denom
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

        # Exact C0 = 0 and Cend = 1.
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

        S = (
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

        return S


def make_model(
    cls,
    checkpoint,
):
    model = cls().to(
        device
    )

    strict_load(
        model,
        checkpoint,
    )

    model.eval()

    return model


# =============================================================================
# Part A — Independent DEV diagnosis of frozen COMP007
# =============================================================================

print()
print("=" * 110)
print("PART A — FROZEN COMP007 DEV-ONLY DIAGNOSTIC")
print("=" * 110)


def source_predict(
    cls,
    checkpoint,
):
    model = make_model(
        cls,
        checkpoint,
    )

    chunks = []

    with torch.no_grad():
        for m0 in range(
            0,
            EXPECTED_DEV_PROFILES,
            EVAL_MICROBATCH,
        ):
            m1 = min(
                m0
                +
                EVAL_MICROBATCH,
                EXPECTED_DEV_PROFILES,
            )

            xi = torch.from_numpy(
                xi_dev[
                    m0:m1
                ]
            ).to(
                device
            )

            p11 = torch.from_numpy(
                p11_dev[
                    m0:m1
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
                    "Nonfinite DEV prediction."
                )

            chunks.append(
                pred.detach()
                .cpu()
                .numpy()
            )

            del (
                xi,
                p11,
                pred,
            )

    out = np.concatenate(
        chunks,
        axis=0,
    )

    del model
    torch.cuda.empty_cache()

    return out


pred004 = source_predict(
    BaseEtaModel,
    COMP004,
)

pred007 = source_predict(
    COMP007LiftedModel,
    COMP007,
)


source_metrics = {
    "COMP004": {
        "global":
            error_metrics(
                pred004,
                Sw_dev,
            ),

        "Nc0":
            error_metrics(
                pred004[
                    nc0_mask
                ],
                Sw_dev[
                    nc0_mask
                ],
            ),

        "Nc_positive":
            error_metrics(
                pred004[
                    ncpos_mask
                ],
                Sw_dev[
                    ncpos_mask
                ],
            ),
    },

    "COMP007": {
        "global":
            error_metrics(
                pred007,
                Sw_dev,
            ),

        "Nc0":
            error_metrics(
                pred007[
                    nc0_mask
                ],
                Sw_dev[
                    nc0_mask
                ],
            ),

        "Nc_positive":
            error_metrics(
                pred007[
                    ncpos_mask
                ],
                Sw_dev[
                    ncpos_mask
                ],
            ),
    },
}


print(
    "COMP004 DEV global source RMSE:",
    f"{source_metrics['COMP004']['global']['rmse']:.12e}",
)

print(
    "COMP007 DEV global source RMSE:",
    f"{source_metrics['COMP007']['global']['rmse']:.12e}",
)

print(
    "COMP004 DEV Nc=0 source RMSE :",
    f"{source_metrics['COMP004']['Nc0']['rmse']:.12e}",
)

print(
    "COMP007 DEV Nc=0 source RMSE :",
    f"{source_metrics['COMP007']['Nc0']['rmse']:.12e}",
)


# Corrected residuals on DEV.
chunk_engine = CUDA3.make_cuda3_chunked_batched_engine(
    VJP_CHUNK
)

original_engine = (
    B2S.local_recurrent_derivatives_create_graph
)


def corrected_residual_all(
    cls,
    checkpoint,
):
    model = make_model(
        cls,
        checkpoint,
    )

    residual_chunks = []

    B2S.local_recurrent_derivatives_create_graph = (
        chunk_engine
    )

    try:
        for m0 in range(
            0,
            EXPECTED_DEV_PROFILES,
            EVAL_MICROBATCH,
        ):
            m1 = min(
                m0
                +
                EVAL_MICROBATCH,
                EXPECTED_DEV_PROFILES,
            )

            xi = (
                torch.from_numpy(
                    xi_dev[
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
                    p11_dev[
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

            if not finite_tensor(
                residual
            ):
                raise RuntimeError(
                    "Nonfinite DEV corrected residual."
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

    out = np.concatenate(
        residual_chunks,
        axis=0,
    )

    del model
    torch.cuda.empty_cache()

    return out


res004 = corrected_residual_all(
    BaseEtaModel,
    COMP004,
)

res007 = corrected_residual_all(
    COMP007LiftedModel,
    COMP007,
)


def residual_metrics(
    residual,
    mask,
):
    r = residual[
        mask
    ]

    return {
        "rmse":
            rmse(
                r
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


corrected_metrics = {
    "COMP004": {
        "global":
            residual_metrics(
                res004,
                np.ones(
                    EXPECTED_DEV_PROFILES,
                    dtype=bool,
                ),
            ),

        "Nc0":
            residual_metrics(
                res004,
                nc0_mask,
            ),

        "Nc_positive":
            residual_metrics(
                res004,
                ncpos_mask,
            ),
    },

    "COMP007": {
        "global":
            residual_metrics(
                res007,
                np.ones(
                    EXPECTED_DEV_PROFILES,
                    dtype=bool,
                ),
            ),

        "Nc0":
            residual_metrics(
                res007,
                nc0_mask,
            ),

        "Nc_positive":
            residual_metrics(
                res007,
                ncpos_mask,
            ),
    },
}


print(
    "COMP004 DEV Nc=0 corrected RMSE:",
    f"{corrected_metrics['COMP004']['Nc0']['rmse']:.12e}",
)

print(
    "COMP007 DEV Nc=0 corrected RMSE:",
    f"{corrected_metrics['COMP007']['Nc0']['rmse']:.12e}",
)


# Nc=0 xi localization.
r004_nc0 = res004[
    nc0_mask,
    :,
    0,
]

r007_nc0 = res007[
    nc0_mask,
    :,
    0,
]


interior_xi = np.mean(
    xi_dev[
        nc0_mask,
        1:-1,
        0,
    ],
    axis=0,
)


node_rmse004 = np.sqrt(
    np.mean(
        r004_nc0
        ** 2,
        axis=0,
    )
)

node_rmse007 = np.sqrt(
    np.mean(
        r007_nc0
        ** 2,
        axis=0,
    )
)

node_gap = (
    node_rmse007
    -
    node_rmse004
)


worst_idx = np.argsort(
    node_gap
)[
    ::-1
][
    :10
]


worst_nodes = [
    {
        "interior_index":
            int(
                idx
            ),

        "xi":
            float(
                interior_xi[
                    idx
                ]
            ),

        "COMP004_RMSE":
            float(
                node_rmse004[
                    idx
                ]
            ),

        "COMP007_RMSE":
            float(
                node_rmse007[
                    idx
                ]
            ),

        "absolute_RMSE_gap":
            float(
                node_gap[
                    idx
                ]
            ),
    }
    for idx in worst_idx
]


inlet_node_mask = (
    interior_xi
    <=
    RETROSPECTIVE_INLET_XI_MAX
)

rest_node_mask = (
    interior_xi
    >
    RETROSPECTIVE_INLET_XI_MAX
)


inlet_localization = {
    "retrospective_zone_xi_max":
        RETROSPECTIVE_INLET_XI_MAX,

    "top10_nodes_inside_retrospective_zone":
        int(
            np.sum(
                interior_xi[
                    worst_idx
                ]
                <=
                RETROSPECTIVE_INLET_XI_MAX
            )
        ),

    "top10_nodes_total":
        10,

    "COMP004_inlet_zone_RMSE":
        rmse(
            r004_nc0[
                :,
                inlet_node_mask
            ]
        ),

    "COMP007_inlet_zone_RMSE":
        rmse(
            r007_nc0[
                :,
                inlet_node_mask
            ]
        ),

    "COMP004_rest_zone_RMSE":
        rmse(
            r004_nc0[
                :,
                rest_node_mask
            ]
        ),

    "COMP007_rest_zone_RMSE":
        rmse(
            r007_nc0[
                :,
                rest_node_mask
            ]
        ),
}


inlet_localization[
    "inlet_zone_gap"
] = (
    inlet_localization[
        "COMP007_inlet_zone_RMSE"
    ]
    -
    inlet_localization[
        "COMP004_inlet_zone_RMSE"
    ]
)

inlet_localization[
    "rest_zone_gap"
] = (
    inlet_localization[
        "COMP007_rest_zone_RMSE"
    ]
    -
    inlet_localization[
        "COMP004_rest_zone_RMSE"
    ]
)


print()
print("NEW DEV Nc=0 RESIDUAL LOCALIZATION")

print(
    "  top-10 excess nodes with xi<=0.16:",
    f"{inlet_localization['top10_nodes_inside_retrospective_zone']}/10",
)

print(
    "  COMP004 inlet-zone RMSE:",
    f"{inlet_localization['COMP004_inlet_zone_RMSE']:.12e}",
)

print(
    "  COMP007 inlet-zone RMSE:",
    f"{inlet_localization['COMP007_inlet_zone_RMSE']:.12e}",
)

print(
    "  COMP004 rest-zone RMSE :",
    f"{inlet_localization['COMP004_rest_zone_RMSE']:.12e}",
)

print(
    "  COMP007 rest-zone RMSE :",
    f"{inlet_localization['COMP007_rest_zone_RMSE']:.12e}",
)


# tD quartiles on Nc=0 DEV.
tD_nc0 = tD_dev[
    nc0_mask
]

quartile_edges = np.quantile(
    tD_nc0,
    [
        0.0,
        0.25,
        0.50,
        0.75,
        1.0,
    ],
)


time_bins = []

for i in range(
    4
):
    lo = quartile_edges[
        i
    ]

    hi = quartile_edges[
        i
        +
        1
    ]

    if i < 3:
        mask = (
            (
                tD_nc0
                >=
                lo
            )
            &
            (
                tD_nc0
                <
                hi
            )
        )
    else:
        mask = (
            (
                tD_nc0
                >=
                lo
            )
            &
            (
                tD_nc0
                <=
                hi
            )
        )

    time_bins.append(
        {
            "quartile":
                i
                +
                1,

            "tD_min":
                float(
                    lo
                ),

            "tD_max":
                float(
                    hi
                ),

            "profiles":
                int(
                    np.sum(
                        mask
                    )
                ),

            "COMP004_corrected_RMSE":
                rmse(
                    r004_nc0[
                        mask
                    ]
                ),

            "COMP007_corrected_RMSE":
                rmse(
                    r007_nc0[
                        mask
                    ]
                ),
        }
    )


# =============================================================================
# Part B — COMP008 bounded-monotone implementation preflight
# =============================================================================

print()
print("=" * 110)
print("PART B — COMP008 BOUNDED-MONOTONE ARCHITECTURE PREFLIGHT")
print("=" * 110)


# Use COMP007 state ONLY as a realistic latent-trunk fixture for implementation
# preflight. This does NOT authorize warm-start training.
prototype = make_model(
    COMP008BoundedMonotoneModel,
    COMP007,
)


prototype_chunks = []

with torch.no_grad():
    for m0 in range(
        0,
        EXPECTED_DEV_PROFILES,
        EVAL_MICROBATCH,
    ):
        m1 = min(
            m0
            +
            EVAL_MICROBATCH,
            EXPECTED_DEV_PROFILES,
        )

        xi = torch.from_numpy(
            xi_dev[
                m0:m1
            ]
        ).to(
            device
        )

        p11 = torch.from_numpy(
            p11_dev[
                m0:m1
            ]
        ).to(
            device
        )

        with torch.backends.cudnn.flags(
            enabled=False
        ):
            pred = prototype(
                xi,
                p11,
            )

        gate(
            f"prototype_forward_finite_{m0}_{m1}",
            finite_tensor(
                pred
            ),
        )

        prototype_chunks.append(
            pred.detach()
            .cpu()
            .numpy()
        )

        del (
            xi,
            p11,
            pred,
        )


proto = np.concatenate(
    prototype_chunks,
    axis=0,
)


inj_error = np.abs(
    proto[
        :,
        0,
        0
    ]
    -
    S_inj_dev
)

tip_error = np.abs(
    proto[
        :,
        -1,
        0
    ]
    -
    Sw_star_dev
)


upper = S_inj_dev[
    :,
    None,
    None
]

lower = Sw_star_dev[
    :,
    None,
    None
]


upper_violation = np.maximum(
    proto
    -
    upper,
    0.0,
)

lower_violation = np.maximum(
    lower
    -
    proto,
    0.0,
)


positive_slope = np.maximum(
    proto[
        :,
        1:,
        0
    ]
    -
    proto[
        :,
        :-1,
        0
    ],
    0.0,
)


architecture_metrics = {
    "injector_endpoint_max_abs":
        float(
            np.max(
                inj_error
            )
        ),

    "tip_endpoint_max_abs":
        float(
            np.max(
                tip_error
            )
        ),

    "upper_bound_max_violation":
        float(
            np.max(
                upper_violation
            )
        ),

    "lower_bound_max_violation":
        float(
            np.max(
                lower_violation
            )
        ),

    "positive_slope_max":
        float(
            np.max(
                positive_slope
            )
        ),

    "positive_slope_violation_fraction":
        float(
            np.mean(
                positive_slope
                >
                STRUCT_TOL
            )
        ),

    "prediction_finite":
        bool(
            np.isfinite(
                proto
            ).all()
        ),
}


print()
print("ARCHITECTURAL GUARANTEES")

for key, value in architecture_metrics.items():
    print(
        f"  {key}: {value}"
    )


architecture_gates = {
    "injector_endpoint_exact":
        architecture_metrics[
            "injector_endpoint_max_abs"
        ]
        <=
        STRUCT_TOL,

    "tip_endpoint_exact":
        architecture_metrics[
            "tip_endpoint_max_abs"
        ]
        <=
        STRUCT_TOL,

    "upper_bound_exact":
        architecture_metrics[
            "upper_bound_max_violation"
        ]
        <=
        STRUCT_TOL,

    "lower_bound_exact":
        architecture_metrics[
            "lower_bound_max_violation"
        ]
        <=
        STRUCT_TOL,

    "monotonicity_exact":
        architecture_metrics[
            "positive_slope_max"
        ]
        <=
        STRUCT_TOL,

    "prediction_finite":
        architecture_metrics[
            "prediction_finite"
        ]
        is True,
}


for name, ok in architecture_gates.items():
    gate(
        name,
        ok,
    )


# =============================================================================
# Derivative-engine parity on one deterministic profile per Nc
# =============================================================================

print()
print("DERIVATIVE-ENGINE PARITY")


parity_ids = []

for nc in NC_VALUES:
    ids = np.where(
        native_nc_mask(
            nc_dev,
            nc,
        )
    )[0]

    if ids.size == 0:
        raise RuntimeError(
            f"No DEV profiles for Nc={nc}."
        )

    parity_ids.append(
        int(
            ids[
                0
            ]
        )
    )


parity_ids = np.asarray(
    parity_ids,
    dtype=np.int64,
)


def run_physics_with_engine(
    engine,
    do_backward,
):
    model = make_model(
        COMP008BoundedMonotoneModel,
        COMP007,
    )

    xi = (
        torch.from_numpy(
            xi_dev[
                parity_ids
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
            p11_dev[
                parity_ids
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

    truth = torch.from_numpy(
        Sw_dev[
            parity_ids
        ]
    ).to(
        device
    )

    old = (
        B2S.local_recurrent_derivatives_create_graph
    )

    B2S.local_recurrent_derivatives_create_graph = (
        engine
    )

    try:
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

        data_loss = torch.mean(
            (
                S_pred
                -
                truth
            )
            ** 2
        )

        physics_loss = torch.mean(
            residual
            ** 2
        )

        total = (
            data_loss
            +
            1.0e-3
            *
            physics_loss
        )

        grads = None

        if do_backward:
            model.zero_grad(
                set_to_none=True
            )

            total.backward()

            grad_parts = []

            for param in model.parameters():
                if param.grad is not None:
                    grad_parts.append(
                        param.grad.detach()
                        .flatten()
                        .cpu()
                    )

            if not grad_parts:
                raise RuntimeError(
                    "No model gradients produced."
                )

            grads = torch.cat(
                grad_parts
            ).numpy()

        out = {
            "S":
                S_pred.detach()
                .cpu()
                .numpy(),

            "residual":
                residual.detach()
                .cpu()
                .numpy(),

            "data_loss":
                float(
                    data_loss.detach()
                    .cpu()
                    .item()
                ),

            "physics_loss":
                float(
                    physics_loss.detach()
                    .cpu()
                    .item()
                ),

            "total_loss":
                float(
                    total.detach()
                    .cpu()
                    .item()
                ),

            "grads":
                grads,

            "S_finite":
                finite_tensor(
                    S_pred
                ),

            "residual_finite":
                finite_tensor(
                    residual
                ),

            "total_finite":
                finite_tensor(
                    total
                ),
        }

    finally:
        B2S.local_recurrent_derivatives_create_graph = (
            old
        )

    del (
        model,
        xi,
        p11,
        truth,
    )

    torch.cuda.empty_cache()

    return out


# Frozen loop/original engine.
loop_result = run_physics_with_engine(
    original_engine,
    do_backward=True,
)

# CUDA3 K16 chunked batched engine.
chunk_result = run_physics_with_engine(
    chunk_engine,
    do_backward=True,
)


S_parity_max = float(
    np.max(
        np.abs(
            loop_result[
                "S"
            ]
            -
            chunk_result[
                "S"
            ]
        )
    )
)

residual_parity_max = float(
    np.max(
        np.abs(
            loop_result[
                "residual"
            ]
            -
            chunk_result[
                "residual"
            ]
        )
    )
)


grad_loop = loop_result[
    "grads"
]

grad_chunk = chunk_result[
    "grads"
]


gate(
    "gradient_vector_size_equal",
    grad_loop.shape
    ==
    grad_chunk.shape,
)


grad_parity_max = float(
    np.max(
        np.abs(
            grad_loop
            -
            grad_chunk
        )
    )
)

grad_parity_rmse = rmse(
    grad_loop
    -
    grad_chunk
)


derivative_parity = {
    "profiles":
        parity_ids.tolist(),

    "Nc_values":
        [
            float(
                nc_dev[
                    idx
                ]
            )
            for idx in parity_ids
        ],

    "S_max_abs_difference":
        S_parity_max,

    "residual_max_abs_difference":
        residual_parity_max,

    "gradient_max_abs_difference":
        grad_parity_max,

    "gradient_RMSE_difference":
        grad_parity_rmse,

    "loop_data_loss":
        loop_result[
            "data_loss"
        ],

    "chunk_data_loss":
        chunk_result[
            "data_loss"
        ],

    "loop_physics_loss":
        loop_result[
            "physics_loss"
        ],

    "chunk_physics_loss":
        chunk_result[
            "physics_loss"
        ],
}


print(
    "  S max abs difference       :",
    f"{S_parity_max:.12e}",
)

print(
    "  residual max abs difference:",
    f"{residual_parity_max:.12e}",
)

print(
    "  gradient max abs difference:",
    f"{grad_parity_max:.12e}",
)

print(
    "  gradient RMSE difference   :",
    f"{grad_parity_rmse:.12e}",
)


gate(
    "loop_forward_finite",
    loop_result[
        "S_finite"
    ],
)

gate(
    "loop_residual_finite",
    loop_result[
        "residual_finite"
    ],
)

gate(
    "loop_total_finite",
    loop_result[
        "total_finite"
    ],
)

gate(
    "chunk_forward_finite",
    chunk_result[
        "S_finite"
    ],
)

gate(
    "chunk_residual_finite",
    chunk_result[
        "residual_finite"
    ],
)

gate(
    "chunk_total_finite",
    chunk_result[
        "total_finite"
    ],
)

gate(
    "loop_gradients_finite",
    np.isfinite(
        grad_loop
    ).all(),
)

gate(
    "chunk_gradients_finite",
    np.isfinite(
        grad_chunk
    ).all(),
)

gate(
    "chunk_vs_loop_S_parity",
    S_parity_max
    <=
    DERIVATIVE_PARITY_ATOL,
)

gate(
    "chunk_vs_loop_residual_parity",
    residual_parity_max
    <=
    DERIVATIVE_PARITY_ATOL,
)

gate(
    "chunk_vs_loop_gradient_parity",
    grad_parity_max
    <=
    GRAD_PARITY_ATOL,
)


# =============================================================================
# Final decision
# =============================================================================

ALL_ARCHITECTURE_GATES_PASS = all(
    architecture_gates.values()
)

DERIVATIVE_PREFLIGHT_PASS = (
    loop_result[
        "S_finite"
    ]
    and
    loop_result[
        "residual_finite"
    ]
    and
    loop_result[
        "total_finite"
    ]
    and
    chunk_result[
        "S_finite"
    ]
    and
    chunk_result[
        "residual_finite"
    ]
    and
    chunk_result[
        "total_finite"
    ]
    and
    np.isfinite(
        grad_loop
    ).all()
    and
    np.isfinite(
        grad_chunk
    ).all()
    and
    S_parity_max
    <=
    DERIVATIVE_PARITY_ATOL
    and
    residual_parity_max
    <=
    DERIVATIVE_PARITY_ATOL
    and
    grad_parity_max
    <=
    GRAD_PARITY_ATOL
)


CUDA8J_AUTHORIZED = (
    ALL_ARCHITECTURE_GATES_PASS
    and
    DERIVATIVE_PREFLIGHT_PASS
)


if CUDA8J_AUTHORIZED:
    disposition = (
        "CUDA8I_COMPLETE_COMP008_BOUNDED_MONOTONE_IMPLEMENTATION_PREFLIGHT_PASS_"
        "DEV_DIAGNOSTIC_COMPLETE_CUDA8J_FINAL_STAGE2_DEVELOPMENT_CONTRACT_FREEZE_AUTHORIZED_"
        "COMP008_TRAINING_NOT_YET_AUTHORIZED_B3_REMAINS_BLOCKED"
    )
else:
    disposition = (
        "CUDA8I_PREFLIGHT_FAILED_CUDA8J_NOT_AUTHORIZED_"
        "COMP008_TRAINING_NOT_AUTHORIZED_B3_REMAINS_BLOCKED"
    )


RUNNER_SHA = sha256(
    Path(
        __file__
    )
)


results = {
    "milestone":
        MILESTONE,

    "prospective_experiment":
        PROSPECTIVE_EXPERIMENT,

    "runner_sha256":
        RUNNER_SHA,

    "DEV_dataset_sha256":
        EXPECTED[
            "DEV_DATASET"
        ],

    "BLIND_CERT_dataset_sha256":
        EXPECTED[
            "BLIND_CERT"
        ],

    "BLIND_CERT_scientifically_opened":
        False,

    "source_native_DEV_metrics":
        source_metrics,

    "corrected_residual_DEV_metrics":
        corrected_metrics,

    "Nc0_DEV_localization": {
        "worst_nodes":
            worst_nodes,

        "inlet_vs_rest":
            inlet_localization,

        "tD_quartiles":
            time_bins,

        "interpretation_policy":
            (
                "Descriptive DEV evidence only. CUDA8J makes the final "
                "development decision; no binary inlet-repair gate is imposed in CUDA8I."
            ),
    },

    "COMP008_architecture_metrics":
        architecture_metrics,

    "COMP008_architecture_gates":
        architecture_gates,

    "derivative_engine_parity":
        derivative_parity,

    "all_architecture_gates_PASS":
        ALL_ARCHITECTURE_GATES_PASS,

    "derivative_preflight_PASS":
        DERIVATIVE_PREFLIGHT_PASS,

    "CUDA8J_authorized":
        CUDA8J_AUTHORIZED,

    "COMP008_training_authorized":
        False,

    "Stage2_certified":
        False,

    "B3_authorized":
        False,

    "OOD_used":
        False,

    "TOF_used":
        False,

    "disposition":
        disposition,

    "next_milestone":
        (
            "V16E-1B2CUDA8J — FINAL Stage-2 development decision and "
            "COMP008 science/training contract freeze"
            if CUDA8J_AUTHORIZED
            else
            "Resolve CUDA8I implementation failure without opening blind CERT"
        ),
}


atomic_json(
    RESULTS_PATH,
    results,
)

RESULTS_SHA = sha256(
    RESULTS_PATH
)


summary = {
    "milestone":
        MILESTONE,

    "runner_sha256":
        RUNNER_SHA,

    "results_sha256":
        RESULTS_SHA,

    "BLIND_CERT_scientifically_opened":
        False,

    "all_architecture_gates_PASS":
        ALL_ARCHITECTURE_GATES_PASS,

    "derivative_preflight_PASS":
        DERIVATIVE_PREFLIGHT_PASS,

    "CUDA8J_authorized":
        CUDA8J_AUTHORIZED,

    "COMP008_training_authorized":
        False,

    "Stage2_certified":
        False,

    "B3_authorized":
        False,

    "disposition":
        disposition,

    "next":
        results[
            "next_milestone"
        ],
}


atomic_json(
    SUMMARY_PATH,
    summary,
)

SUMMARY_SHA = sha256(
    SUMMARY_PATH
)


handoff = f"""# PAD-Stream V16E-1B2CUDA8I

## Role

Final diagnostic / implementation milestone for the current Stage-2
development cycle.

No training occurred.

No optimizer step occurred.

The blind certification dataset was hash-verified only and was never opened.

## Frozen COMP007 on NEW DEV

COMP004 global source RMSE:

`{source_metrics["COMP004"]["global"]["rmse"]:.12e}`

COMP007 global source RMSE:

`{source_metrics["COMP007"]["global"]["rmse"]:.12e}`

COMP004 Nc=0 corrected RMSE:

`{corrected_metrics["COMP004"]["Nc0"]["rmse"]:.12e}`

COMP007 Nc=0 corrected RMSE:

`{corrected_metrics["COMP007"]["Nc0"]["rmse"]:.12e}`

Top-10 Nc=0 excess-residual nodes inside xi<=0.16:

`{inlet_localization["top10_nodes_inside_retrospective_zone"]}/10`

COMP004 inlet-zone corrected RMSE:

`{inlet_localization["COMP004_inlet_zone_RMSE"]:.12e}`

COMP007 inlet-zone corrected RMSE:

`{inlet_localization["COMP007_inlet_zone_RMSE"]:.12e}`

COMP004 rest-zone corrected RMSE:

`{inlet_localization["COMP004_rest_zone_RMSE"]:.12e}`

COMP007 rest-zone corrected RMSE:

`{inlet_localization["COMP007_rest_zone_RMSE"]:.12e}`

CUDA8J will use this DEV evidence to make the final inlet-treatment decision.

## COMP008 bounded-monotone implementation

Architectural gates pass:

`{ALL_ARCHITECTURE_GATES_PASS}`

Injector endpoint max error:

`{architecture_metrics["injector_endpoint_max_abs"]:.12e}`

Tip endpoint max error:

`{architecture_metrics["tip_endpoint_max_abs"]:.12e}`

Upper-bound max violation:

`{architecture_metrics["upper_bound_max_violation"]:.12e}`

Lower-bound max violation:

`{architecture_metrics["lower_bound_max_violation"]:.12e}`

Positive-slope max:

`{architecture_metrics["positive_slope_max"]:.12e}`

## Derivative / backward preflight

Derivative-engine preflight pass:

`{DERIVATIVE_PREFLIGHT_PASS}`

CUDA3-vs-loop residual max difference:

`{residual_parity_max:.12e}`

CUDA3-vs-loop gradient max difference:

`{grad_parity_max:.12e}`

## Authorization

CUDA8J authorized:

`{CUDA8J_AUTHORIZED}`

COMP008 training authorized:

`False`

Stage 2 certified:

`False`

B3 authorized:

`False`

## Hashes

Runner SHA-256:

`{RUNNER_SHA}`

Results SHA-256:

`{RESULTS_SHA}`

Summary SHA-256:

`{SUMMARY_SHA}`

## Next

{results["next_milestone"]}
"""


HANDOFF_PATH.write_text(
    handoff,
    encoding="utf-8",
)

HANDOFF_SHA = sha256(
    HANDOFF_PATH
)


print()
print("=" * 110)
print("CUDA8I RESULT")
print("=" * 110)

print(
    "Architecture gates PASS :",
    ALL_ARCHITECTURE_GATES_PASS,
)

print(
    "Derivative preflight PASS:",
    DERIVATIVE_PREFLIGHT_PASS,
)

print(
    "CUDA8J authorized       :",
    CUDA8J_AUTHORIZED,
)

print(
    "COMP008 training auth   :",
    False,
)

print(
    "Stage 2 certified       :",
    False,
)

print(
    "B3 authorized           :",
    False,
)

print()
print(
    "Disposition:",
    disposition,
)

print()
print(
    "Runner SHA :",
    RUNNER_SHA,
)

print(
    "Results SHA:",
    RESULTS_SHA,
)

print(
    "Summary SHA:",
    SUMMARY_SHA,
)

print(
    "Handoff SHA:",
    HANDOFF_SHA,
)

print()
print(
    "NEXT:",
    results[
        "next_milestone"
    ],
)
