from pathlib import Path
import hashlib
import importlib.util
import json
import math
import os

import numpy as np
import torch


# =============================================================================
# PAD-Stream V16E-1B2CUDA8F
#
# Stage-2 Failed-Gate Evidence Review
#
# READ-ONLY SCIENTIFIC FORENSIC.
#
# CUDA8E produced a valid negative Stage-2 disposition. CUDA8F does not alter
# that disposition and does not create a repair protocol.
#
# It localizes only the three CUDA8E failed gates:
#   1. Nc=0 corrected-residual RMSE vs COMP004;
#   2. monotonicity violation fraction vs COMP004;
#   3. upper saturation bound.
#
# NO TRAINING.
# NO MODEL SELECTION.
# NO THRESHOLD CHANGES.
# NO REPAIR AUTHORIZATION.
# NO OOD.
# NO TOF.
# B3 REMAINS BLOCKED.
# =============================================================================


MILESTONE = "V16E-1B2CUDA8F"
EXPERIMENT = "V16E-BLREP-COMP-CUDA-007"


REPO = Path("/content/PAD-Stream")
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")


CUDA6 = (
    REPO
    / "PAD_Stream_V16E1B2CUDA6_A100_COMP_CUDA_005_Authorized_Production_Runner.py"
)

CUDA8E_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8E_COMP007_PostTraining_Stage2_Closure_Evaluation.py"
)

DATASET = (
    DRIVE
    / "datasets"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
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

RECOVERY005_E0800 = (
    RUN005
    / "recovery"
    / "V16E_BLREP_COMP_CUDA_005_RECOVERY_E0800.pt"
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


CUDA8E_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8E_COMP007_STAGE2_POSTTRAINING_CLOSURE"
)

CUDA8E_RESULTS = (
    CUDA8E_ROOT
    / "V16E1B2CUDA8E_COMP007_Stage2_Closure_Results.json"
)

CUDA8E_DISPOSITION = (
    CUDA8E_ROOT
    / "V16E1B2CUDA8E_COMP007_Stage2_Disposition.json"
)

CUDA8E_SUMMARY = (
    CUDA8E_ROOT
    / "PAD_Stream_V16E1B2CUDA8E_Summary.json"
)

CUDA8E_HANDOFF = (
    CUDA8E_ROOT
    / "V16E1B2CUDA8E_Handoff.md"
)


PROVENANCE_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8F_STAGE2_FAILED_GATE_EVIDENCE_REVIEW"
)

PROVENANCE_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

RESULTS_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8F_Failed_Gate_Evidence_Review.json"
)

SUMMARY_PATH = (
    PROVENANCE_ROOT
    / "PAD_Stream_V16E1B2CUDA8F_Summary.json"
)

HANDOFF_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8F_Handoff.md"
)


EXPECTED = {
    "CUDA6":
        "385e18b64ebf068a06e5daec11449e3700f69ad743627d4520905f273bf7c552",

    "CUDA8E_SOURCE":
        "41c9bc07388130274f9cd06b043eafa3669f21ef81746f4bb8f7f23b57736eba",

    "dataset":
        "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c",

    "COMP004":
        "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69",

    "RECOVERY005_E0800":
        "fbdbf6b7bff0b22625e7dbcd09500c258c6deeeec6ed4f846407f6e927435157",

    "COMP007":
        "98521407ab803b4899a75988c65f303f94e9447dd25e159e7cc3ffdb7e9c042d",

    "CUDA8E_RESULTS":
        "cf8c38345083dc50484c74de5289f84320bf1f75b6ee75e459fec67d08e0da5a",

    "CUDA8E_DISPOSITION":
        "9b9a3627d9de9ea9fb36e4233e910ddc5c686ab062b3f6aa2673a8ede4d10026",

    "CUDA8E_SUMMARY":
        "dd1450db14363a26c52b21028636bbff57f23234cb83c570e6f916fd0c3aa4fd",

    "CUDA8E_HANDOFF":
        "9ffa5203b4ef783336798e83429f91a265862122016f49aa0f5f93a3675363c6",

    "B2S":
        "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea",

    "BASE_M":
        "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18",

    "ETA_J":
        "fcc4074863a46f6b8d356a01ff0b4b2182d0ffa3ebc9b3fd053e35282f897a4c",

    "CUDA3":
        "1065788f8f82d7f58aba873b8396cf70a17906571421315151640a0c879df886",

    "holdout_idx":
        "4b64a27875ebe04f96d717f0e9eab43017a5325c352b5c4233284adafa308613",
}


EVAL_MICROBATCH = 256
VJP_CHUNK = 64
UPPER_BOUND_TOL = 1.0e-6

NC_VALUES = (
    0.00,
    0.05,
    0.10,
    0.20,
    0.30,
)


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
            f"CUDA8F authority gate failed: {name}"
        )


def finite_tensor(x):
    return bool(
        torch.isfinite(x)
        .all()
        .item()
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


def extract_model_state(payload):
    for key in (
        "model_state_dict",
        "model_state",
        "state_dict",
    ):
        if (
            isinstance(
                payload,
                dict,
            )
            and key in payload
            and isinstance(
                payload[key],
                dict,
            )
        ):
            return payload[key]

    if (
        isinstance(
            payload,
            dict,
        )
        and payload
        and all(
            torch.is_tensor(v)
            for v in payload.values()
        )
    ):
        return payload

    raise RuntimeError(
        "No supported model state found."
    )


def strict_load(model, path):
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


def rmse(x):
    return math.sqrt(
        float(
            np.mean(
                np.asarray(x)
                ** 2
            )
        )
    )


def native_nc_mask(values, nc):
    return (
        values
        ==
        np.asarray(
            nc,
            dtype=values.dtype,
        )
    )


print("=" * 110)
print("PAD-Stream V16E-1B2CUDA8F")
print("Stage-2 Failed-Gate Evidence Review")
print("=" * 110)

print()
print("READ-ONLY HOLDOUT FORENSIC.")
print("NO TRAINING.")
print("NO MODEL SELECTION.")
print("NO THRESHOLD CHANGES.")
print("NO REPAIR AUTHORIZATION.")
print("NO OOD.")
print("NO TOF.")
print("B3 REMAINS BLOCKED.")
print()


AUTHORITY = {
    "CUDA6":
        CUDA6,

    "CUDA8E_SOURCE":
        CUDA8E_SOURCE,

    "dataset":
        DATASET,

    "COMP004":
        COMP004,

    "RECOVERY005_E0800":
        RECOVERY005_E0800,

    "COMP007":
        COMP007,

    "CUDA8E_RESULTS":
        CUDA8E_RESULTS,

    "CUDA8E_DISPOSITION":
        CUDA8E_DISPOSITION,

    "CUDA8E_SUMMARY":
        CUDA8E_SUMMARY,

    "CUDA8E_HANDOFF":
        CUDA8E_HANDOFF,
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


cuda8e = json.loads(
    CUDA8E_RESULTS.read_text(
        encoding="utf-8"
    )
)


gate(
    "CUDA8E_Stage2_not_certified",
    cuda8e[
        "Stage2_certified"
    ]
    is False,
)

gate(
    "CUDA8E_B3_not_authorized",
    cuda8e[
        "B3_authorized"
    ]
    is False,
)

gate(
    "CUDA8E_failed_Nc0_corrected_gate",
    cuda8e[
        "acceptance_gates"
    ][
        "restore_COMP004_Nc0_corrected_RMSE"
    ]
    is False,
)

gate(
    "CUDA8E_failed_monotonicity_gate",
    cuda8e[
        "acceptance_gates"
    ][
        "restore_COMP004_mono_violation_fraction"
    ]
    is False,
)

gate(
    "CUDA8E_failed_upper_bound_gate",
    cuda8e[
        "acceptance_gates"
    ][
        "upper_bound_PASS"
    ]
    is False,
)


# =============================================================================
# Runtime and scientific engine
# =============================================================================

gate(
    "CUDA_available",
    torch.cuda.is_available(),
)

device = torch.device(
    "cuda"
)

print()
print("RUNTIME")
print(
    "  PyTorch :",
    torch.__version__,
)
print(
    "  GPU     :",
    torch.cuda.get_device_name(0),
)


spec = importlib.util.spec_from_file_location(
    "cuda6_for_cuda8f",
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
    "cuda8f_B2S",
)

M = C.import_module(
    B2S.BASE_RUNNER,
    "cuda8f_M",
)

J = C.import_module(
    B2S.B2J_SOURCE,
    "cuda8f_J",
)

CUDA3 = C.import_module(
    C.CUDA3_SOURCE,
    "cuda8f_CUDA3",
)


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


# =============================================================================
# Exact holdout
# =============================================================================

with np.load(
    DATASET,
    allow_pickle=False,
) as d:
    xi_all = np.array(
        d["xi"],
        copy=True,
    )

    p11_all = np.array(
        d["p11"],
        copy=True,
    )


recovery005 = torch.load(
    RECOVERY005_E0800,
    map_location="cpu",
    weights_only=False,
)

holdout_idx = np.asarray(
    recovery005[
        "holdout_idx"
    ],
    dtype=np.int64,
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


xi_h = xi_all[
    holdout_idx
]

p11_h = p11_all[
    holdout_idx
]

nc_h = p11_h[
    :,
    10
]

tD_h = p11_h[
    :,
    7
]

nc0_mask = native_nc_mask(
    nc_h,
    0.0,
)


# =============================================================================
# Model definitions
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
    checkpoint,
    lifted,
):
    model = (
        LiftedModel()
        if lifted
        else BaseEtaModel()
    ).to(
        device
    )

    strict_load(
        model,
        checkpoint,
    )

    model.eval()

    return model


# =============================================================================
# Predictions
# =============================================================================

def predict_holdout(
    checkpoint,
    lifted,
):
    model = make_model(
        checkpoint,
        lifted,
    )

    chunks = []


    with torch.no_grad():
        for m0 in range(
            0,
            len(
                holdout_idx
            ),
            EVAL_MICROBATCH,
        ):
            m1 = min(
                m0
                +
                EVAL_MICROBATCH,
                len(
                    holdout_idx
                ),
            )

            xi = torch.from_numpy(
                xi_h[
                    m0:m1
                ]
            ).to(
                device
            )

            p11 = torch.from_numpy(
                p11_h[
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
                    "Nonfinite prediction."
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


print()
print("PREDICTION FORENSIC")

pred007 = predict_holdout(
    COMP007,
    lifted=True,
)


# =============================================================================
# Upper-bound localization
# =============================================================================

upper = (
    1.0
    -
    p11_h[
        :,
        3
    ][
        :,
        None,
        None
    ]
)

upper_excess = np.maximum(
    pred007
    -
    upper,
    0.0,
)

upper_positive = (
    upper_excess
    >
    UPPER_BOUND_TOL
)


upper_by_nc = {}


for nc in NC_VALUES:
    mask = native_nc_mask(
        nc_h,
        nc,
    )

    ex = upper_excess[
        mask
    ]

    pos = upper_positive[
        mask
    ]

    upper_by_nc[
        str(
            nc
        )
    ] = {
        "profiles":
            int(
                np.sum(
                    mask
                )
            ),

        "max_excess":
            float(
                np.max(
                    ex
                )
            ),

        "point_fraction_over_tol":
            float(
                np.mean(
                    pos
                )
            ),

        "profile_fraction_any_over_tol":
            float(
                np.mean(
                    np.any(
                        pos,
                        axis=(
                            1,
                            2,
                        ),
                    )
                )
            ),
    }


# =============================================================================
# Monotonicity localization
# =============================================================================

dS = (
    pred007[
        :,
        1:,
        0
    ]
    -
    pred007[
        :,
        :-1,
        0
    ]
)

positive_slope = (
    dS
    >
    0.0
)

positive_magnitude = np.maximum(
    dS,
    0.0,
)


mono_by_nc = {}


for nc in NC_VALUES:
    mask = native_nc_mask(
        nc_h,
        nc,
    )

    ds = positive_magnitude[
        mask
    ]

    pos = positive_slope[
        mask
    ]

    mono_by_nc[
        str(
            nc
        )
    ] = {
        "profiles":
            int(
                np.sum(
                    mask
                )
            ),

        "violation_fraction":
            float(
                np.mean(
                    pos
                )
            ),

        "mean_positive_slope":
            float(
                np.mean(
                    ds[
                        pos
                    ]
                )
                if np.any(
                    pos
                )
                else 0.0
            ),

        "max_positive_slope":
            float(
                np.max(
                    ds
                )
            ),

        "profile_fraction_any_violation":
            float(
                np.mean(
                    np.any(
                        pos,
                        axis=1,
                    )
                )
            ),
    }


# Nodewise monotonicity localization.
xi_nodes = np.mean(
    xi_h[
        :,
        :,
        0
    ],
    axis=0,
)

mono_node_fraction = np.mean(
    positive_slope,
    axis=0,
)

mono_top_idx = np.argsort(
    mono_node_fraction
)[
    ::-1
][
    :10
]


mono_top_nodes = [
    {
        "slope_index":
            int(
                idx
            ),

        "xi_left":
            float(
                xi_nodes[
                    idx
                ]
            ),

        "xi_right":
            float(
                xi_nodes[
                    idx
                    +
                    1
                ]
            ),

        "violation_fraction":
            float(
                mono_node_fraction[
                    idx
                ]
            ),

        "mean_positive_slope":
            float(
                np.mean(
                    positive_magnitude[
                        :,
                        idx
                    ]
                )
            ),
    }
    for idx in mono_top_idx
]


# =============================================================================
# Corrected residual localization: COMP004 vs COMP007, Nc=0 only
# =============================================================================

engine = CUDA3.make_cuda3_chunked_batched_engine(
    VJP_CHUNK
)

original_engine = (
    B2S.local_recurrent_derivatives_create_graph
)


def corrected_residual_nc0(
    checkpoint,
    lifted,
):
    model = make_model(
        checkpoint,
        lifted,
    )

    ids = np.where(
        nc0_mask
    )[0]

    chunks = []


    try:
        B2S.local_recurrent_derivatives_create_graph = (
            engine
        )


        for m0 in range(
            0,
            len(
                ids
            ),
            EVAL_MICROBATCH,
        ):
            local = ids[
                m0:
                m0
                +
                EVAL_MICROBATCH
            ]


            xi = (
                torch.from_numpy(
                    xi_h[
                        local
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
                        local
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
                    _unused,
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
                    "Nonfinite corrected residual."
                )


            chunks.append(
                residual.detach()
                .cpu()
                .numpy()
            )


            del (
                xi,
                p11,
                S_pred,
                residual,
                _unused,
            )

            torch.cuda.empty_cache()


    finally:
        B2S.local_recurrent_derivatives_create_graph = (
            original_engine
        )


    out = np.concatenate(
        chunks,
        axis=0,
    )


    del model
    torch.cuda.empty_cache()

    return (
        ids,
        out,
    )


print()
print("NC=0 CORRECTED-RESIDUAL FORENSIC")

nc0_ids_004, residual004 = (
    corrected_residual_nc0(
        COMP004,
        lifted=False,
    )
)

nc0_ids_007, residual007 = (
    corrected_residual_nc0(
        COMP007,
        lifted=True,
    )
)


gate(
    "Nc0_residual_profile_identity",
    np.array_equal(
        nc0_ids_004,
        nc0_ids_007,
    ),
)


# Residual shape is (profiles, interior_nodes, 1).
r004 = residual004[
    :,
    :,
    0
]

r007 = residual007[
    :,
    :,
    0
]


node_rmse004 = np.sqrt(
    np.mean(
        r004 ** 2,
        axis=0,
    )
)

node_rmse007 = np.sqrt(
    np.mean(
        r007 ** 2,
        axis=0,
    )
)

node_delta = (
    node_rmse007
    -
    node_rmse004
)

worst_delta_idx = np.argsort(
    node_delta
)[
    ::-1
][
    :10
]


# Corrected residual corresponds to interior xi nodes.
interior_xi = np.mean(
    xi_h[
        nc0_mask,
        1:-1,
        0
    ],
    axis=0,
)


nc0_worst_nodes = [
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
                node_delta[
                    idx
                ]
            ),
    }
    for idx in worst_delta_idx
]


# tD quartiles for Nc=0 profiles.
tD_nc0 = tD_h[
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
                    r004[
                        mask
                    ]
                ),

            "COMP007_corrected_RMSE":
                rmse(
                    r007[
                        mask
                    ]
                ),
        }
    )


# =============================================================================
# Exact failed-gate margins from frozen CUDA8E
# =============================================================================

m004 = cuda8e[
    "COMP004"
]

m007 = cuda8e[
    "COMP007"
]


nc0_corrected004 = float(
    m004[
        "corrected_residual"
    ][
        "Nc0"
    ][
        "rmse"
    ]
)

nc0_corrected007 = float(
    m007[
        "corrected_residual"
    ][
        "Nc0"
    ][
        "rmse"
    ]
)

mono004 = float(
    m004[
        "physical"
    ][
        "mono_violation_fraction"
    ]
)

mono007 = float(
    m007[
        "physical"
    ][
        "mono_violation_fraction"
    ]
)

upper_max = float(
    m007[
        "physical"
    ][
        "upper_bound_max_violation"
    ]
)


failed_gate_margins = {
    "Nc0_corrected_RMSE": {
        "COMP004_gate":
            nc0_corrected004,

        "COMP007":
            nc0_corrected007,

        "absolute_gap":
            (
                nc0_corrected007
                -
                nc0_corrected004
            ),

        "relative_gap_percent":
            (
                nc0_corrected007
                /
                nc0_corrected004
                -
                1.0
            )
            *
            100.0,
    },

    "monotonicity_violation_fraction": {
        "COMP004_gate":
            mono004,

        "COMP007":
            mono007,

        "absolute_gap":
            (
                mono007
                -
                mono004
            ),

        "ratio_to_COMP004":
            (
                mono007
                /
                mono004
            ),
    },

    "upper_bound": {
        "tolerance":
            UPPER_BOUND_TOL,

        "COMP007_max_violation":
            upper_max,

        "ratio_to_tolerance":
            (
                upper_max
                /
                UPPER_BOUND_TOL
            ),
    },
}


# =============================================================================
# Report
# =============================================================================

print()
print("=" * 110)
print("FAILED-GATE MARGINS")
print("=" * 110)

print(
    "Nc=0 corrected RMSE:"
)

print(
    "  COMP004 gate :",
    f"{nc0_corrected004:.12e}",
)

print(
    "  COMP007      :",
    f"{nc0_corrected007:.12e}",
)

print(
    "  relative gap :",
    f"{failed_gate_margins['Nc0_corrected_RMSE']['relative_gap_percent']:.3f}%",
)


print()
print(
    "Monotonicity violation fraction:"
)

print(
    "  COMP004 gate :",
    f"{mono004:.12e}",
)

print(
    "  COMP007      :",
    f"{mono007:.12e}",
)

print(
    "  ratio        :",
    f"{failed_gate_margins['monotonicity_violation_fraction']['ratio_to_COMP004']:.3f}x",
)


print()
print(
    "Upper-bound violation:"
)

print(
    "  tolerance    :",
    f"{UPPER_BOUND_TOL:.12e}",
)

print(
    "  max excess   :",
    f"{upper_max:.12e}",
)

print(
    "  ratio to tol :",
    f"{failed_gate_margins['upper_bound']['ratio_to_tolerance']:.3f}x",
)


print()
print("=" * 110)
print("UPPER-BOUND LOCALIZATION BY Nc")
print("=" * 110)

for nc in NC_VALUES:
    row = upper_by_nc[
        str(
            nc
        )
    ]

    print(
        f"Nc={nc:.2f} "
        f"| max={row['max_excess']:.6e} "
        f"| point_frac={row['point_fraction_over_tol']:.6e} "
        f"| profile_frac={row['profile_fraction_any_over_tol']:.6e}"
    )


print()
print("=" * 110)
print("MONOTONICITY LOCALIZATION BY Nc")
print("=" * 110)

for nc in NC_VALUES:
    row = mono_by_nc[
        str(
            nc
        )
    ]

    print(
        f"Nc={nc:.2f} "
        f"| violation_frac={row['violation_fraction']:.6e} "
        f"| mean_pos_slope={row['mean_positive_slope']:.6e} "
        f"| max_pos_slope={row['max_positive_slope']:.6e} "
        f"| profile_frac={row['profile_fraction_any_violation']:.6e}"
    )


print()
print("=" * 110)
print("NC=0 CORRECTED-RESIDUAL tD QUARTILES")
print("=" * 110)

for row in time_bins:
    print(
        f"Q{row['quartile']} "
        f"| tD [{row['tD_min']:.6e}, {row['tD_max']:.6e}] "
        f"| n={row['profiles']} "
        f"| COMP004={row['COMP004_corrected_RMSE']:.6e} "
        f"| COMP007={row['COMP007_corrected_RMSE']:.6e}"
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

    "source_disposition":
        cuda8e[
            "disposition"
        ],

    "Stage2_certified":
        False,

    "B3_authorized":
        False,

    "retraining_authorized":
        False,

    "threshold_changes_authorized":
        False,

    "failed_gate_margins":
        failed_gate_margins,

    "upper_bound_localization_by_Nc":
        upper_by_nc,

    "monotonicity_localization_by_Nc":
        mono_by_nc,

    "monotonicity_top_nodes":
        mono_top_nodes,

    "Nc0_corrected_residual_worst_nodes":
        nc0_worst_nodes,

    "Nc0_corrected_residual_tD_quartiles":
        time_bins,

    "holdout_used_for":
        "READ_ONLY_EVIDENCE_REVIEW_ONLY",

    "OOD_used":
        False,

    "TOF_used":
        False,

    "disposition":
        (
            "STAGE2_FAILED_GATE_EVIDENCE_REVIEW_COMPLETE_"
            "NEGATIVE_CUDA8E_DISPOSITION_UNCHANGED_"
            "NO_HOLDOUT_DRIVEN_RETRAINING_AUTHORIZED_"
            "B3_REMAINS_BLOCKED"
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

    "Stage2_certified":
        False,

    "B3_authorized":
        False,

    "retraining_authorized":
        False,

    "failed_gates": [
        "Nc0_corrected_RMSE",
        "monotonicity_violation_fraction",
        "upper_bound",
    ],

    "disposition":
        results[
            "disposition"
        ],

    "next":
        (
            "Scientific evidence review and roadmap decision only. "
            "No B3 and no holdout-driven Stage-2 retraining."
        ),
}


atomic_json(
    SUMMARY_PATH,
    summary,
)

SUMMARY_SHA = sha256(
    SUMMARY_PATH
)


handoff = f"""# PAD-Stream V16E-1B2CUDA8F

## Purpose

Read-only evidence review of the three CUDA8E Stage-2 failed gates.

No training, threshold changes, model selection, repair authorization, OOD,
TOF, or B3 work occurs here.

## Frozen CUDA8E disposition

Stage 2 certified: `False`

B3 authorized: `False`

## Failed-gate margins

Nc=0 corrected residual RMSE:

- COMP004 gate: `{nc0_corrected004:.12e}`
- COMP007: `{nc0_corrected007:.12e}`
- relative gap: `{failed_gate_margins["Nc0_corrected_RMSE"]["relative_gap_percent"]:.6f}%`

Monotonicity violation fraction:

- COMP004 gate: `{mono004:.12e}`
- COMP007: `{mono007:.12e}`
- ratio: `{failed_gate_margins["monotonicity_violation_fraction"]["ratio_to_COMP004"]:.6f}x`

Upper saturation bound:

- tolerance: `{UPPER_BOUND_TOL:.12e}`
- COMP007 maximum excess: `{upper_max:.12e}`
- ratio to tolerance: `{failed_gate_margins["upper_bound"]["ratio_to_tolerance"]:.6f}x`

## Status

Negative CUDA8E disposition remains unchanged.

No holdout-driven Stage-2 retraining is authorized.

B3 remains blocked.

## Hashes

Runner SHA-256:

`{RUNNER_SHA}`

Results SHA-256:

`{RESULTS_SHA}`

Summary SHA-256:

`{SUMMARY_SHA}`
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
print("CUDA8F RESULT")
print("=" * 110)

print(
    "Stage 2 certified:",
    False,
)

print(
    "B3 authorized:",
    False,
)

print(
    "Retraining authorized:",
    False,
)

print(
    "Disposition:",
    results[
        "disposition"
    ],
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
