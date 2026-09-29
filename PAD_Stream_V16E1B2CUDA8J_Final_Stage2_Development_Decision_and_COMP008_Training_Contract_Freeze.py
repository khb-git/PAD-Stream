#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import os

import numpy as np
import torch


# =============================================================================
# PAD-Stream V16E-1B2CUDA8J
#
# FINAL Stage-2 Development Decision
# and COMP008 Science / Training Contract Freeze
#
# HARD STOP FOR CURRENT STAGE-2 DEVELOPMENT CYCLE.
#
# NO MODEL TRAINING.
# NO OPTIMIZER STEP.
# NO DATASET GENERATION.
# NO BLIND CERT SCIENTIFIC INSPECTION.
# NO ORIGINAL-HOLDOUT REUSE.
# NO OOD.
# NO TOF.
# B3 REMAINS BLOCKED.
#
# If this freeze passes:
#   - COMP008 production training is authorized under THIS EXACT contract.
#   - no later architecture/loss/hyperparameter adjustment is authorized in
#     the current Stage-2 cycle.
#   - the next milestone is execution only (CUDA8K production training).
# =============================================================================


MILESTONE = "V16E-1B2CUDA8J"
EXPERIMENT = "V16E-BLREP-COMP-CUDA-008"

STATUS = (
    "CUDA8J_FINAL_STAGE2_DEVELOPMENT_CONTRACT_FROZEN_"
    "COMP008_BOUNDED_MONOTONE_ARCHITECTURE_"
    "INLET_WEIGHTED_CORRECTED_PHYSICS_"
    "EXACT_COMP007_WARM_START_FRESH_ADAM_LR1E4_"
    "800_EPOCHS_1600_STEPS_K64_MB1024_"
    "NO_BC_TIP_ANCHOR_MONO_OR_BOUNDS_PENALTIES_"
    "DEV_CLOSED_FOR_MODEL_SELECTION_BLIND_CERT_REMAINS_SEALED_"
    "COMP008_PRODUCTION_TRAINING_AUTHORIZED_"
    "NO_FURTHER_STAGE2_DEVELOPMENT_CHANGES_AUTHORIZED_"
    "B3_REMAINS_BLOCKED"
)


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


CUDA8IR1_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8IR1_DEV_Selection_Content_Hash_Repair_COMP008_Bounded_Monotone_Architecture_and_DEV_Only_Preflight.py"
)

CUDA8IR1_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_redesign"
    / "V16E1B2CUDA8IR1_COMP008_BOUNDED_MONOTONE_DEV_PREFLIGHT"
)

CUDA8IR1_RESULTS = (
    CUDA8IR1_ROOT
    / "V16E1B2CUDA8IR1_COMP008_DEV_Preflight_Results.json"
)

CUDA8IR1_SUMMARY = (
    CUDA8IR1_ROOT
    / "PAD_Stream_V16E1B2CUDA8IR1_Summary.json"
)

CUDA8IR1_HANDOFF = (
    CUDA8IR1_ROOT
    / "V16E1B2CUDA8IR1_Handoff.md"
)


TRAIN_DATASET = (
    DRIVE
    / "datasets"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)

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


RUN004 = (
    DRIVE
    / "provenance"
    / "xpu_reference"
)

COMP004 = (
    RUN004
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


RUN007 = (
    DRIVE
    / "runs"
    / "V16E-BLREP-COMP-CUDA-007"
)

COMP007 = (
    RUN007
    / "V16E_BLREP_COMP_CUDA_007.pt"
)


CUDA8D_R1D_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8D_R1D_COMP007_Authorized_Production_Training_Runner.py"
)


FREEZE_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_redesign"
    / "V16E1B2CUDA8J_FINAL_STAGE2_DEVELOPMENT_CONTRACT_FREEZE"
)

FREEZE_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)


ARCHITECTURE_PATH = (
    FREEZE_ROOT
    / "V16E1B2CUDA8J_COMP008_Architecture_Contract.json"
)

LOSS_PATH = (
    FREEZE_ROOT
    / "V16E1B2CUDA8J_COMP008_Loss_and_Physics_Contract.json"
)

TRAINING_PATH = (
    FREEZE_ROOT
    / "V16E1B2CUDA8J_COMP008_Production_Training_Contract.json"
)

CERTIFICATION_PATH = (
    FREEZE_ROOT
    / "V16E1B2CUDA8J_Stage2_Blind_Certification_Contract.json"
)

DECISION_PATH = (
    FREEZE_ROOT
    / "V16E1B2CUDA8J_Final_Development_Decision.json"
)

SUMMARY_PATH = (
    FREEZE_ROOT
    / "PAD_Stream_V16E1B2CUDA8J_Summary.json"
)

HANDOFF_PATH = (
    FREEZE_ROOT
    / "V16E1B2CUDA8J_Handoff.md"
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

    "CUDA8IR1_SOURCE":
        "8062708a912e303f165a173df739ff960a27ab312bf3903c10cab0553d9cbe86",

    "CUDA8IR1_RESULTS":
        "7fb3f69a53f08b3c26e3a0c7d86446f134964b2dfd8164a056e90bc6656763fd",

    "CUDA8IR1_SUMMARY":
        "29a96c61a4d9c215b309709b3782926f0f75129213c9df76a4d08903079e290b",

    "CUDA8IR1_HANDOFF":
        "909e2177d4ba3ca0f6b30af8daf9e7ce110c0867781816aefb9ebc98f44d9927",

    "TRAIN_DATASET":
        "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c",

    "DEV_DATASET":
        "55e5fe6868d78c930192af3af59d931275a83aa1f3ca46595969429718063821",

    "BLIND_CERT":
        "0eaf3fc1a6be77b2b804baf54e03837346754a411b92e5b1b19f83f3d8ddf265",

    "BLIND_CERT_SEAL":
        "7dd0bdd24c05e8d0265f77030247da3739b00eeca41af8c9495c22eaddc1c1ae",

    "COMP004":
        "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69",

    "COMP005":
        "aaca2ae60d7a789bf6d3d2a177d1b3b5188181809597b1be6901ed7473e0906f",

    "RECOVERY005_E0800":
        "fbdbf6b7bff0b22625e7dbcd09500c258c6deeeec6ed4f846407f6e927435157",

    "COMP007":
        "98521407ab803b4899a75988c65f303f94e9447dd25e159e7cc3ffdb7e9c042d",

    "CUDA8D_R1D_SOURCE":
        "f67ab2a2ec493f424e998b6c7a3672c4e9ee43e2bf9e38df75f052c6c4977a2f",
}


TRAIN_IDX_SHA = (
    "c3d1d9080af67a8ecfa018d3f757dac1fd9f19f7977f2cdf25622d613c7195b8"
)

HOLDOUT_IDX_SHA = (
    "4b64a27875ebe04f96d717f0e9eab43017a5325c352b5c4233284adafa308613"
)


# =============================================================================
# Final frozen decisions
# =============================================================================

SEED = 1337

N_TOTAL = 14400
N_TRAIN = 11520
N_RETIRED_HOLDOUT = 2880

NC_VALUES = [
    0.00,
    0.05,
    0.10,
    0.20,
    0.30,
]

TARGET_EPOCHS = 800
EXPECTED_OPTIMIZER_STEPS = 1600

OPTIMIZER = "Adam"
LR = 1.0e-4
FOREACH = False

VJP_CHUNK = 64
MICROBATCH = 1024
LOGICAL_BATCH_1 = 8192
LOGICAL_BATCH_2 = 3328
MICROBATCHES_PER_EPOCH = 12
OPTIMIZER_STEPS_PER_EPOCH = 2

LAMBDA_DATA = 1.0
LAMBDA_PHYS = 8.537526059395e-04

# Final inlet-focused physics weight.
#
# Raw:
#   w_raw(xi) = 1 + alpha * exp(-(xi/xi0)^2)
#
# Normalized on each profile's interior residual nodes:
#   w = w_raw / mean_j(w_raw)
#
# Thus mean spatial weight is exactly 1 and the existing lambda_physics scale
# is retained.  The weighting is continuous in xi and is NOT Nc-specific.
INLET_ALPHA = 3.0
INLET_XI0 = 0.16

REL_COMPARE_TOL = 1.0e-6
ABS_COMPARE_TOL = 1.0e-12

BOUND_TOL = 1.0e-6
ENDPOINT_TOL = 1.0e-6


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
            f"CUDA8J freeze gate failed: {name}"
        )


def atomic_json(
    path: Path,
    obj,
):
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
            sort_keys=True,
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


def compare_le(
    candidate,
    reference,
):
    candidate = float(
        candidate
    )

    reference = float(
        reference
    )

    return candidate <= (
        reference
        *
        (
            1.0
            +
            REL_COMPARE_TOL
        )
        +
        ABS_COMPARE_TOL
    )


print("=" * 110)
print("PAD-Stream V16E-1B2CUDA8J")
print("FINAL Stage-2 Development Decision and COMP008 Science / Training Contract Freeze")
print("=" * 110)

print()
print("HARD STOP FOR CURRENT STAGE-2 DEVELOPMENT CYCLE.")
print("NO TRAINING.")
print("NO OPTIMIZER STEP.")
print("NO DATASET GENERATION.")
print("BLIND CERT SCIENTIFIC INSPECTION: FORBIDDEN.")
print("ORIGINAL HOLDOUT REUSE: FORBIDDEN.")
print("NO OOD.")
print("NO TOF.")
print("B3 REMAINS BLOCKED.")
print()


# =============================================================================
# Authority gates
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

    "CUDA8IR1_SOURCE":
        CUDA8IR1_SOURCE,

    "CUDA8IR1_RESULTS":
        CUDA8IR1_RESULTS,

    "CUDA8IR1_SUMMARY":
        CUDA8IR1_SUMMARY,

    "CUDA8IR1_HANDOFF":
        CUDA8IR1_HANDOFF,

    "TRAIN_DATASET":
        TRAIN_DATASET,

    "DEV_DATASET":
        DEV_DATASET,

    "BLIND_CERT":
        BLIND_CERT,

    "BLIND_CERT_SEAL":
        BLIND_CERT_SEAL,

    "COMP004":
        COMP004,

    "COMP005":
        COMP005,

    "RECOVERY005_E0800":
        RECOVERY005_E0800,

    "COMP007":
        COMP007,

    "CUDA8D_R1D_SOURCE":
        CUDA8D_R1D_SOURCE,
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


# BLIND_CERT is HASHED ONLY above.
# It is never np.load'ed or torch.load'ed anywhere in CUDA8J.


# =============================================================================
# Training-split authority
# =============================================================================

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
print("TRAINING-SPLIT AUTHORITY")

gate(
    "train_count_11520",
    train_idx.shape
    ==
    (
        N_TRAIN,
    ),
)

gate(
    "retired_holdout_count_2880",
    holdout_idx.shape
    ==
    (
        N_RETIRED_HOLDOUT,
    ),
)

gate(
    "train_idx_SHA_exact",
    array_sha256(
        train_idx
    )
    ==
    TRAIN_IDX_SHA,
)

gate(
    "holdout_idx_SHA_exact",
    array_sha256(
        holdout_idx
    )
    ==
    HOLDOUT_IDX_SHA,
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
    "train_plus_holdout_cover_14400",
    np.union1d(
        train_idx,
        holdout_idx,
    ).size
    ==
    N_TOTAL,
)


# =============================================================================
# Bind CUDA8I-R1 evidence
# =============================================================================

i = json.loads(
    CUDA8IR1_RESULTS.read_text(
        encoding="utf-8"
    )
)


print()
print("CUDA8I-R1 EVIDENCE GATES")

gate(
    "CUDA8I_architecture_pass",
    i[
        "all_architecture_gates_PASS"
    ]
    is True,
)

gate(
    "CUDA8I_derivative_preflight_pass",
    i[
        "derivative_preflight_PASS"
    ]
    is True,
)

gate(
    "CUDA8I_CUDA8J_authorized",
    i[
        "CUDA8J_authorized"
    ]
    is True,
)

gate(
    "CUDA8I_COMP008_training_still_not_authorized",
    i[
        "COMP008_training_authorized"
    ]
    is False,
)

gate(
    "CUDA8I_Stage2_not_certified",
    i[
        "Stage2_certified"
    ]
    is False,
)

gate(
    "CUDA8I_B3_not_authorized",
    i[
        "B3_authorized"
    ]
    is False,
)

gate(
    "CUDA8I_blind_CERT_not_opened",
    i[
        "BLIND_CERT_scientifically_opened"
    ]
    is False,
)


loc = i[
    "Nc0_DEV_localization"
][
    "inlet_vs_rest"
]


gate(
    "independent_DEV_reproduces_inlet_localization_10_of_10",
    int(
        loc[
            "top10_nodes_inside_retrospective_zone"
        ]
    )
    ==
    10,
)

gate(
    "DEV_inlet_zone_COMP007_worse_than_COMP004",
    float(
        loc[
            "COMP007_inlet_zone_RMSE"
        ]
    )
    >
    float(
        loc[
            "COMP004_inlet_zone_RMSE"
        ]
    ),
)

gate(
    "DEV_localization_boundary_matches_xi0",
    math.isclose(
        float(
            loc[
                "retrospective_zone_xi_max"
            ]
        ),
        INLET_XI0,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ),
)


arch_m = i[
    "COMP008_architecture_metrics"
]


gate(
    "COMP008_injector_endpoint_exact_on_DEV",
    float(
        arch_m[
            "injector_endpoint_max_abs"
        ]
    )
    <=
    ENDPOINT_TOL,
)

gate(
    "COMP008_tip_endpoint_exact_on_DEV",
    float(
        arch_m[
            "tip_endpoint_max_abs"
        ]
    )
    <=
    ENDPOINT_TOL,
)

gate(
    "COMP008_upper_bound_exact_on_DEV",
    float(
        arch_m[
            "upper_bound_max_violation"
        ]
    )
    <=
    BOUND_TOL,
)

gate(
    "COMP008_lower_bound_exact_on_DEV",
    float(
        arch_m[
            "lower_bound_max_violation"
        ]
    )
    <=
    BOUND_TOL,
)

gate(
    "COMP008_monotone_exact_on_DEV",
    float(
        arch_m[
            "positive_slope_max"
        ]
    )
    <=
    BOUND_TOL,
)


# =============================================================================
# FINAL architecture contract
# =============================================================================

ARCHITECTURE = {
    "milestone":
        MILESTONE,

    "experiment":
        EXPERIMENT,

    "development_status":
        "FINAL_FROZEN",

    "trunk": {
        "coordinate_inputs":
            [
                "xi",
                "eta",
            ],

        "physical_parameter_state":
            "p11",

        "p11_order": [
            "no",
            "nw",
            "swi_or_swc",
            "sor",
            "mu_w",
            "mu_o",
            "phi",
            "tD",
            "xD_star",
            "Sw_star",
            "Nc",
        ],

        "recurrent_family":
            "COMP007-controlled Stage-2 recurrent trunk",

        "LSTM_hidden":
            64,

        "LSTM_layers":
            2,

        "scalar_latent_per_node":
            True,
    },

    "bounded_monotone_output": {
        "latent":
            "z_i",

        "interval_positive_decrement":
            "q_j = softplus(0.5*(z_j + z_{j+1})) + 1e-8",

        "normalized_interval_weight":
            "w_j = q_j / sum_k(q_k)",

        "cumulative_coordinate":
            "C_0=0; C_i=sum_{j=0}^{i-1}(w_j); C_last=1",

        "saturation":
            "S_i = S_inj - (S_inj - Sw_star)*C_i",

        "S_inj":
            "1 - Sor",

        "Sw_star":
            "p11 index 9, frozen Rankine-Hugoniot shock-state authority",

        "epsilon":
            1.0e-8,
    },

    "architectural_guarantees": [
        "injector endpoint exact to numerical tolerance",
        "shock-tip endpoint exact to numerical tolerance",
        "Sw_star <= S <= S_inj",
        "non-increasing saturation along xi",
    ],

    "initialization": {
        "model_weights":
            "EXACT_FROZEN_COMP007",

        "checkpoint":
            str(
                COMP007
            ),

        "checkpoint_sha256":
            EXPECTED[
                "COMP007"
            ],

        "interpretation":
            (
                "All COMP007 network tensors are loaded exactly. "
                "The scalar output is reinterpreted as latent z by the "
                "bounded-monotone COMP008 forward map. CUDA8I-R1 verified "
                "finite forward, corrected residual, backward graph, and "
                "CUDA3-vs-loop derivative parity under this exact fixture."
            ),
    },

    "forbidden_changes_after_CUDA8J": [
        "change recurrent width/depth",
        "change coordinate inputs",
        "change p11 state",
        "change bounded-monotone map",
        "change initialization source",
        "add a second output head",
        "add capillary/TOF/OOD physics",
    ],
}


# =============================================================================
# FINAL loss / physics contract
# =============================================================================

LOSS = {
    "milestone":
        MILESTONE,

    "experiment":
        EXPERIMENT,

    "data_loss": {
        "enabled":
            True,

        "definition":
            "mean((S_pred - S_teacher)^2)",

        "lambda":
            LAMBDA_DATA,
    },

    "corrected_conservative_physics": {
        "enabled":
            True,

        "equation":
            (
                "R_cons = N_tD + Xdot*N_X + "
                "[exp(Nc*xi*X)*fw'(N)/X - xi*Xdot/X]*N_xi + "
                "Nc*exp(Nc*xi*X)*fw(N)"
            ),

        "Rankine_Hugoniot":
            "Xdot = exp(Nc*X)*sigma_BL",

        "lambda":
            LAMBDA_PHYS,

        "Nc_balancing":
            (
                "retain exact frozen COMP007 equal-Nc normalization "
                "and frozen training-set Nc normalizers"
            ),
    },

    "inlet_spatial_physics_weight": {
        "enabled":
            True,

        "Nc_specific":
            False,

        "applied_to":
            "interior corrected-residual squared terms before per-profile reduction",

        "raw_formula":
            "w_raw(xi) = 1 + alpha*exp(-(xi/xi0)^2)",

        "normalized_formula":
            "w(xi) = w_raw(xi) / mean_interior(w_raw)",

        "alpha":
            INLET_ALPHA,

        "xi0":
            INLET_XI0,

        "mean_weight_per_profile":
            1.0,

        "reason":
            (
                "CUDA8I-R1 independently reproduced the Nc=0 excess-residual "
                "localization on NEW DEV: all top-10 excess nodes were inside "
                "xi<=0.16 and COMP007 inlet-zone corrected RMSE exceeded COMP004. "
                "The treatment is continuous in xi and applied to all Nc values "
                "rather than switching on Nc==0."
            ),

        "hyperparameter_search":
            False,

        "alpha_policy":
            (
                "alpha=3.0 is frozen as a single moderate non-swept emphasis. "
                "Because weights are normalized to unit mean, the global "
                "lambda_physics scale is not increased."
            ),
    },

    "removed_objectives": {
        "injector_BC":
            {
                "enabled":
                    False,

                "reason":
                    "exact architectural endpoint",
            },

        "tip_BC":
            {
                "enabled":
                    False,

                "reason":
                    "exact architectural shock-tip endpoint",
            },

        "anchor":
            {
                "enabled":
                    False,

                "reason":
                    (
                        "CUDA8G allowed anchor retention only if independently "
                        "justified on DEV; CUDA8I-R1 did not establish such a need. "
                        "Full-profile source-native data loss remains."
                    ),
            },

        "monotonicity":
            {
                "enabled":
                    False,

                "reason":
                    "architectural guarantee",
            },

        "bounds":
            {
                "enabled":
                    False,

                "reason":
                    "architectural guarantee",
            },
    },

    "total_loss":
        (
            "L_total = 1.0*L_data + "
            "8.537526059395e-4*L_corrected_physics_inlet_weighted_equal_Nc"
        ),

    "forbidden_after_CUDA8J": [
        "change lambda_data",
        "change lambda_physics",
        "change alpha",
        "change xi0",
        "make inlet weighting Nc-specific",
        "add BC loss",
        "add tip loss",
        "add anchor loss",
        "add monotonicity loss",
        "add bounds penalty",
        "add another repair term",
    ],
}


# =============================================================================
# FINAL production-training contract
# =============================================================================

TRAINING = {
    "milestone":
        MILESTONE,

    "experiment":
        EXPERIMENT,

    "authorization":
        "AUTHORIZED_AFTER_SUCCESSFUL_CUDA8J_FREEZE",

    "data": {
        "training_dataset":
            str(
                TRAIN_DATASET
            ),

        "training_dataset_sha256":
            EXPECTED[
                "TRAIN_DATASET"
            ],

        "dataset_seed":
            SEED,

        "total_profiles":
            N_TOTAL,

        "train_profiles":
            N_TRAIN,

        "train_idx_sha256":
            TRAIN_IDX_SHA,

        "retired_original_holdout_profiles":
            N_RETIRED_HOLDOUT,

        "retired_holdout_idx_sha256":
            HOLDOUT_IDX_SHA,

        "original_holdout_use":
            "FORBIDDEN",

        "DEV_use_during_production":
            "FORBIDDEN_FOR_TRAINING_CHECKPOINT_SELECTION_EARLY_STOPPING_OR_ABORT_DECISIONS",

        "blind_CERT_use_during_production":
            "FORBIDDEN_UNTIL_FINAL_E800_CHECKPOINT_IS_FROZEN",
    },

    "initialization": {
        "model":
            "EXACT_FROZEN_COMP007",

        "optimizer":
            "FRESH_ADAM",

        "optimizer_state_transfer":
            False,
    },

    "randomness": {
        "seed":
            SEED,

        "python":
            SEED,

        "numpy":
            SEED,

        "torch":
            SEED,

        "cuda":
            SEED,
    },

    "optimizer": {
        "type":
            OPTIMIZER,

        "learning_rate":
            LR,

        "foreach":
            FOREACH,

        "scheduler":
            None,

        "gradient_clipping":
            None,

        "AMP":
            False,

        "TF32":
            False,
    },

    "horizon": {
        "epochs":
            TARGET_EPOCHS,

        "optimizer_steps":
            EXPECTED_OPTIMIZER_STEPS,

        "optimizer_steps_per_epoch":
            OPTIMIZER_STEPS_PER_EPOCH,

        "early_stopping":
            False,

        "checkpoint_selection":
            "FINAL_COMPLETED_EPOCH_800_ONLY",
    },

    "geometry": {
        "derivative_engine":
            "CUDA3_CHUNKED_BATCHED_VJP",

        "VJP_chunk":
            VJP_CHUNK,

        "microbatch":
            MICROBATCH,

        "logical_batch_1":
            LOGICAL_BATCH_1,

        "logical_batch_2":
            LOGICAL_BATCH_2,

        "microbatches_per_epoch":
            MICROBATCHES_PER_EPOCH,

        "optimizer_steps_per_epoch":
            OPTIMIZER_STEPS_PER_EPOCH,
    },

    "recovery": {
        "atomic":
            True,

        "cadence":
            "every successfully completed epoch",

        "authority":
            "only a successfully completed epoch is resumable",

        "exact_hash_resume":
            True,

        "orphaned_recovery_policy":
            "fail closed; never guess authority",
    },

    "execution_policy": {
        "production_runner_may_preflight_finiteness_before_first_optimizer_step":
            True,

        "preflight_may_change_contract":
            False,

        "if_preflight_fails":
            (
                "stop execution; implementation repair may reproduce the exact "
                "CUDA8J contract but may not change science/hyperparameters"
            ),

        "if_training_fails_numerically":
            (
                "stop execution; no learning-rate/loss/architecture tuning is "
                "authorized in the current Stage-2 development cycle"
            ),
    },

    "development_hard_stop": {
        "architecture_changes_after_CUDA8J":
            False,

        "loss_changes_after_CUDA8J":
            False,

        "hyperparameter_changes_after_CUDA8J":
            False,

        "DEV_threshold_tuning_after_CUDA8J":
            False,

        "new_repair_objective_after_CUDA8J":
            False,
    },
}


# =============================================================================
# FINAL blind-certification contract
# =============================================================================

CERTIFICATION = {
    "milestone":
        MILESTONE,

    "experiment":
        EXPERIMENT,

    "blind_dataset": {
        "path":
            str(
                BLIND_CERT
            ),

        "sha256":
            EXPECTED[
                "BLIND_CERT"
            ],

        "scientifically_sealed_now":
            True,

        "open_only_after":
            "final COMP008 E800 checkpoint and its SHA-256 are frozen",

        "single_use":
            True,
    },

    "models_compared_on_same_blind_set": [
        "COMP004",
        "COMP005",
        "COMP007",
        "COMP008",
    ],

    "reference_checkpoint_hashes": {
        "COMP004":
            EXPECTED[
                "COMP004"
            ],

        "COMP005":
            EXPECTED[
                "COMP005"
            ],

        "COMP007":
            EXPECTED[
                "COMP007"
            ],
    },

    "comparison_tolerances": {
        "relative":
            REL_COMPARE_TOL,

        "absolute":
            ABS_COMPARE_TOL,
    },

    "preserve_COMP005": [
        {
            "metric":
                "global source-native RMSE",

            "rule":
                "COMP008 <= COMP005 within frozen numerical comparison tolerance",
        },

        {
            "metric":
                "Nc>0 source-native RMSE",

            "rule":
                "COMP008 <= COMP005 within frozen numerical comparison tolerance",
        },

        {
            "metric":
                "global corrected-residual RMSE",

            "rule":
                "COMP008 <= COMP005 within frozen numerical comparison tolerance",
        },

        {
            "metric":
                "Nc>0 corrected-residual RMSE",

            "rule":
                "COMP008 <= COMP005 within frozen numerical comparison tolerance",
        },
    ],

    "restore_or_beat_COMP004": [
        {
            "metric":
                "Nc=0 source-native RMSE",

            "rule":
                "COMP008 <= COMP004 within frozen numerical comparison tolerance",
        },

        {
            "metric":
                "Nc=0 corrected-residual RMSE",

            "rule":
                "COMP008 <= COMP004 within frozen numerical comparison tolerance",
        },

        {
            "metric":
                "tip/shock-state RMSE",

            "rule":
                "COMP008 <= COMP004 within frozen numerical comparison tolerance",
        },

        {
            "metric":
                "monotonicity violation fraction",

            "rule":
                "COMP008 <= COMP004 within frozen numerical comparison tolerance",
        },
    ],

    "absolute_physical_gates": {
        "predictions_finite":
            True,

        "corrected_residual_finite":
            True,

        "lower_bound_max_violation_le":
            BOUND_TOL,

        "upper_bound_max_violation_le":
            BOUND_TOL,

        "injector_endpoint_max_abs_le":
            ENDPOINT_TOL,

        "Rankine_Hugoniot_tip_endpoint_max_abs_le":
            ENDPOINT_TOL,
    },

    "all_gates_required":
        True,

    "partial_pass_certifies":
        False,

    "if_pass":
        "STAGE2_CERTIFIED_B3_AUTHORIZED",

    "if_fail":
        (
            "STAGE2_RECORDED_AS_UNRESOLVED; blind CERT is not reused for "
            "tuning and no additional current-cycle repair is authorized"
        ),
}


# =============================================================================
# Freeze the contracts
# =============================================================================

atomic_json(
    ARCHITECTURE_PATH,
    ARCHITECTURE,
)

ARCHITECTURE_SHA = sha256(
    ARCHITECTURE_PATH
)


atomic_json(
    LOSS_PATH,
    LOSS,
)

LOSS_SHA = sha256(
    LOSS_PATH
)


atomic_json(
    TRAINING_PATH,
    TRAINING,
)

TRAINING_SHA = sha256(
    TRAINING_PATH
)


atomic_json(
    CERTIFICATION_PATH,
    CERTIFICATION,
)

CERTIFICATION_SHA = sha256(
    CERTIFICATION_PATH
)


# =============================================================================
# Final decision
# =============================================================================

DECISION = {
    "milestone":
        MILESTONE,

    "experiment":
        EXPERIMENT,

    "status":
        STATUS,

    "CUDA8I_evidence_bound":
        True,

    "architecture_contract_sha256":
        ARCHITECTURE_SHA,

    "loss_contract_sha256":
        LOSS_SHA,

    "training_contract_sha256":
        TRAINING_SHA,

    "certification_contract_sha256":
        CERTIFICATION_SHA,

    "development_cycle_closed":
        True,

    "COMP008_production_training_authorized":
        True,

    "COMP008_training_must_follow_exact_CUDA8J_contract":
        True,

    "further_current_cycle_architecture_loss_hyperparameter_adjustment_authorized":
        False,

    "Stage2_certified":
        False,

    "B3_authorized":
        False,

    "blind_CERT_scientifically_opened":
        False,

    "OOD_used":
        False,

    "TOF_used":
        False,

    "next_milestone":
        (
            "V16E-1B2CUDA8K — COMP008 authorized production training "
            "under frozen CUDA8J contract; execution only"
        ),
}


atomic_json(
    DECISION_PATH,
    DECISION,
)

DECISION_SHA = sha256(
    DECISION_PATH
)


RUNNER_SHA = sha256(
    Path(
        __file__
    )
)


SUMMARY = {
    "milestone":
        MILESTONE,

    "experiment":
        EXPERIMENT,

    "status":
        STATUS,

    "runner_sha256":
        RUNNER_SHA,

    "architecture_contract_sha256":
        ARCHITECTURE_SHA,

    "loss_contract_sha256":
        LOSS_SHA,

    "training_contract_sha256":
        TRAINING_SHA,

    "certification_contract_sha256":
        CERTIFICATION_SHA,

    "decision_sha256":
        DECISION_SHA,

    "development_cycle_closed":
        True,

    "COMP008_production_training_authorized":
        True,

    "Stage2_certified":
        False,

    "B3_authorized":
        False,

    "blind_CERT_scientifically_opened":
        False,

    "next":
        DECISION[
            "next_milestone"
        ],
}


atomic_json(
    SUMMARY_PATH,
    SUMMARY,
)

SUMMARY_SHA = sha256(
    SUMMARY_PATH
)


HANDOFF = f"""# PAD-Stream V16E-1B2CUDA8J

## Status

`{STATUS}`

CUDA8J is the final development decision for the current Stage-2 cycle.

No training occurred.

No optimizer step occurred.

The original holdout was not used.

The blind certification dataset was hash-verified only and was not opened.

## Final COMP008 architecture

- `[xi, eta] + p11`
- controlled 2-layer LSTM trunk, hidden width 64
- exact frozen COMP007 model initialization
- bounded-monotone cumulative-decrement output
- exact injector endpoint
- exact Rankine-Hugoniot shock-tip endpoint
- architectural saturation bounds
- architectural non-increasing saturation

## Final loss

`L = 1.0 * L_data + 8.537526059395e-4 * L_corrected_physics`

Corrected physics retains the frozen equal-Nc normalization.

The corrected-residual squared terms receive one continuous inlet-focused
spatial weight:

`w_raw(xi) = 1 + 3*exp(-(xi/0.16)^2)`

and

`w = w_raw / mean_interior(w_raw)`.

This is not Nc-specific and was not selected by a hyperparameter sweep.

Injector BC, tip BC, anchor, monotonicity, and bounds penalties are all removed.

## Final production contract

- experiment: `{EXPERIMENT}`
- seed: 1337
- exact original training set: 11,520 profiles
- original holdout: retired / forbidden
- DEV: forbidden for production model selection, early stopping, or abort decisions
- blind CERT: sealed until final E800 checkpoint SHA is frozen
- exact frozen COMP007 initialization
- fresh Adam
- learning rate: `1e-4`
- `foreach=False`
- 800 epochs
- 1600 optimizer steps
- CUDA3 chunked batched VJP, K=64
- microbatch 1024
- logical chunks 8192 + 3328
- AMP off
- TF32 off
- no scheduler
- no clipping
- no early stopping
- only completed epochs are recovery authority
- final completed epoch 800 is the production checkpoint authority

## Hard stop

After this freeze, no current-cycle changes are authorized to:

- architecture;
- losses;
- loss weights;
- inlet weighting alpha or xi0;
- optimizer or learning rate;
- training horizon;
- batching / VJP geometry;
- initialization;
- certification thresholds.

An implementation-only repair may reproduce this exact contract if execution
fails technically, but it may not alter the frozen science or hyperparameters.

## Final blind certification

COMP004, COMP005, COMP007, and COMP008 are evaluated on the same single-use
blind CERT set only after the final COMP008 E800 checkpoint is frozen.

All frozen Stage-2 gates are required.

A blind failure is recorded and is not tuned against.

## Authorization

COMP008 production training authorized:

`True`

Stage 2 certified:

`False`

B3 authorized:

`False`

## Hashes

Runner SHA-256:

`{RUNNER_SHA}`

Architecture contract SHA-256:

`{ARCHITECTURE_SHA}`

Loss contract SHA-256:

`{LOSS_SHA}`

Training contract SHA-256:

`{TRAINING_SHA}`

Certification contract SHA-256:

`{CERTIFICATION_SHA}`

Decision SHA-256:

`{DECISION_SHA}`

Summary SHA-256:

`{SUMMARY_SHA}`

## Next

`{DECISION["next_milestone"]}`
"""


HANDOFF_PATH.write_text(
    HANDOFF,
    encoding="utf-8",
)

HANDOFF_SHA = sha256(
    HANDOFF_PATH
)


print()
print("=" * 110)
print("CUDA8J FINAL CONTRACT")
print("=" * 110)

print("Architecture:")
print("  bounded monotone       : YES")
print("  exact COMP007 init     : YES")
print("  hidden/layers          : 64 / 2")

print()
print("Loss:")
print("  lambda data            :", LAMBDA_DATA)
print("  lambda physics         :", f"{LAMBDA_PHYS:.15e}")
print("  inlet alpha            :", INLET_ALPHA)
print("  inlet xi0              :", INLET_XI0)
print("  inlet mean-normalized  : YES")
print("  Nc-specific inlet rule : NO")
print("  BC penalty             : NO")
print("  tip penalty            : NO")
print("  anchor penalty         : NO")
print("  monotonicity penalty   : NO")
print("  bounds penalty         : NO")

print()
print("Training:")
print("  seed                    :", SEED)
print("  optimizer               :", OPTIMIZER)
print("  learning rate           :", LR)
print("  epochs                  :", TARGET_EPOCHS)
print("  optimizer steps         :", EXPECTED_OPTIMIZER_STEPS)
print("  VJP chunk               :", VJP_CHUNK)
print("  microbatch              :", MICROBATCH)
print("  logical batches         :", LOGICAL_BATCH_1, "+", LOGICAL_BATCH_2)
print("  AMP                     : OFF")
print("  TF32                    : OFF")
print("  scheduler               : NONE")
print("  clipping                : NONE")
print("  early stopping          : NO")

print()
print("Firewall:")
print("  original holdout        : RETIRED / FORBIDDEN")
print("  DEV production selection: FORBIDDEN")
print("  blind CERT              : SEALED")
print("  OOD                     : NO")
print("  TOF                     : NO")

print()
print("=" * 110)
print("CUDA8J RESULT")
print("=" * 110)

print("DEVELOPMENT CYCLE CLOSED                : YES")
print("COMP008 PRODUCTION TRAINING AUTHORIZED  : YES")
print("FURTHER CURRENT-CYCLE ADJUSTMENTS       : NO")
print("STAGE 2 CERTIFIED                       : NO")
print("B3 AUTHORIZED                           : NO")
print("BLIND CERT SCIENTIFICALLY OPENED        : NO")

print()
print("Runner SHA       :", RUNNER_SHA)
print("Architecture SHA :", ARCHITECTURE_SHA)
print("Loss SHA         :", LOSS_SHA)
print("Training SHA     :", TRAINING_SHA)
print("Certification SHA:", CERTIFICATION_SHA)
print("Decision SHA     :", DECISION_SHA)
print("Summary SHA      :", SUMMARY_SHA)
print("Handoff SHA      :", HANDOFF_SHA)

print()
print("NEXT:", DECISION["next_milestone"])
