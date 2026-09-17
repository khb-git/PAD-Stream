from pathlib import Path
import hashlib
import json
import math
import os

import torch


# =============================================================================
# PAD-Stream V16E-1B2CUDA8D-R1C
#
# COMP007 Production Contract Freeze and Authorization
#
# PURPOSE
# -------
# Freeze the exact production-training contract for COMP007 after:
#
#   - CUDA8D-F1 proved COMP006 lr=1e-3 first-step destabilization;
#   - R1AR selected fresh Adam lr=1e-4 as the largest one-step-stable LR;
#   - R1B confirmed lr=1e-4 across 10 TRAIN epochs / 20 optimizer steps;
#   - every R1B step gate passed;
#   - final full-TRAIN gates passed.
#
# R1C DOES NOT TRAIN.
#
# It freezes the contract that the next production runner must execute.
#
# HOLDOUT REMAINS DARK DURING PRODUCTION TRAINING.
# NO OOD.
# NO TOF.
# B3 REMAINS BLOCKED.
# =============================================================================


MILESTONE = "V16E-1B2CUDA8D-R1C"
EXPERIMENT = "V16E-BLREP-COMP-CUDA-007"


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

R1B = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8D_R1B_COMP007_Multi_Step_Optimizer_Stability_Confirmation.py"
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

R1B_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8DR1B_COMP007_MULTI_STEP_STABILITY_CONFIRMATION"
)

R1B_RESULTS = (
    R1B_ROOT
    / "V16E1B2CUDA8DR1B_Multi_Step_Stability_Results.json"
)

R1B_SUMMARY = (
    R1B_ROOT
    / "PAD_Stream_V16E1B2CUDA8DR1B_Summary.json"
)

R1B_HANDOFF = (
    R1B_ROOT
    / "V16E1B2CUDA8DR1B_Handoff.md"
)


PROVENANCE_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8DR1C_COMP007_PRODUCTION_CONTRACT_AUTHORIZATION"
)

PROVENANCE_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

CONTRACT_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8DR1C_COMP007_Production_Training_Contract.json"
)

SUMMARY_PATH = (
    PROVENANCE_ROOT
    / "PAD_Stream_V16E1B2CUDA8DR1C_Summary.json"
)

HANDOFF_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8DR1C_Handoff.md"
)


# =============================================================================
# Frozen SHA authorities
# =============================================================================

EXPECTED = {
    "CUDA8D":
        "be4dca13cf44a8c77caad7feae89b7e2a33e68eacbe339efdae6e951f35b05db",

    "R1A_FAILED":
        "e2673c4dccf426cd67d964db95b3d81502fb85aa0d36ce7821139fd8abd42ff5",

    "R1AR":
        "317b1cc528f8e2b8c141800390d790f26597b6df1d8e870f9246438d541515ac",

    "R1B":
        "864ca74a8eb7fb4e889bf7bfc37e6c009403acd3509d485c5a64bb48c19f3651",

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

    "R1B_RESULTS":
        "e0edb4ad7ba2578e2f9a1425e52933dd42945b0083baac72b135cb86d7024f99",

    "R1B_SUMMARY":
        "52a4e95b24dbb30ca1fe853c0c6e977931475245c9ff438c408385ecf69b7d16",

    "R1B_HANDOFF":
        "6ac7b57bcb1b085dd3bc9d38df93954f85b37b3f5f142590c1128add0f1980b7",

    "train_idx":
        "c3d1d9080af67a8ecfa018d3f757dac1fd9f19f7977f2cdf25622d613c7195b8",

    "holdout_idx":
        "4b64a27875ebe04f96d717f0e9eab43017a5325c352b5c4233284adafa308613",
}


# =============================================================================
# Exact COMP007 production contract
# =============================================================================

SEED = 1337

TARGET_EPOCHS = 800
EXPECTED_OPTIMIZER_STEPS_PER_EPOCH = 2
EXPECTED_TARGET_OPTIMIZER_STEPS = 1600

LEARNING_RATE = 1.0e-4

ADOPTED_CHUNK = 64
MICROBATCH = 1024
LOGICAL_BATCH = 8192
SECOND_LOGICAL_CHUNK = 3328
EXPECTED_MICROBATCHES_PER_EPOCH = 12

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


def gate(name, condition):
    ok = bool(condition)

    print(
        f"[{'PASS' if ok else 'FAIL'}] {name}"
    )

    if not ok:
        raise RuntimeError(
            f"CUDA8D-R1C gate failed: {name}"
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


# =============================================================================
# Banner
# =============================================================================

print("=" * 110)
print("PAD-Stream V16E-1B2CUDA8D-R1C")
print("COMP007 Production Contract Freeze and Authorization")
print("=" * 110)

print()
print("R1C DOES NOT TRAIN.")
print("HOLDOUT EVALUATION DURING PRODUCTION: FORBIDDEN.")
print("No OOD.")
print("No TOF.")
print("B3 remains blocked.")
print()


# =============================================================================
# Authority gates
# =============================================================================

AUTHORITY = {
    "CUDA8D":
        CUDA8D,

    "R1A_FAILED":
        R1A_FAILED,

    "R1AR":
        R1AR,

    "R1B":
        R1B,

    "dataset":
        DATASET,

    "COMP005":
        COMP005,

    "RECOVERY005_E0800":
        RECOVERY005_E0800,

    "CUDA8BR_NORMALIZATION":
        CUDA8BR_NORMALIZATION,

    "R1AR_RESULTS":
        R1AR_RESULTS,

    "R1AR_SUMMARY":
        R1AR_SUMMARY,

    "R1AR_HANDOFF":
        R1AR_HANDOFF,

    "R1B_RESULTS":
        R1B_RESULTS,

    "R1B_SUMMARY":
        R1B_SUMMARY,

    "R1B_HANDOFF":
        R1B_HANDOFF,
}


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


# =============================================================================
# R1AR evidence gates
# =============================================================================

r1ar_results = json.loads(
    R1AR_RESULTS.read_text(
        encoding="utf-8"
    )
)


print()
print("R1AR EVIDENCE GATES")

gate(
    "R1AR_selected_lr_exact",
    math.isclose(
        float(
            r1ar_results[
                "selected_learning_rate"
            ]
        ),
        LEARNING_RATE,
        rel_tol=0.0,
        abs_tol=0.0,
    ),
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
# R1B evidence gates
# =============================================================================

r1b_results = json.loads(
    R1B_RESULTS.read_text(
        encoding="utf-8"
    )
)


print()
print("R1B EVIDENCE GATES")

gate(
    "R1B_selected_lr_exact",
    math.isclose(
        float(
            r1b_results[
                "selected_learning_rate"
            ]
        ),
        LEARNING_RATE,
        rel_tol=0.0,
        abs_tol=0.0,
    ),
)

gate(
    "R1B_confirmation_epochs_10",
    int(
        r1b_results[
            "confirmation_epochs"
        ]
    )
    ==
    10,
)

gate(
    "R1B_confirmation_steps_20",
    int(
        r1b_results[
            "confirmation_optimizer_steps"
        ]
    )
    ==
    20,
)

gate(
    "R1B_all_step_gates_pass",
    r1b_results[
        "all_step_gates_pass"
    ]
    is True,
)

gate(
    "R1B_overall_PASS",
    r1b_results[
        "overall_PASS"
    ]
    is True,
)

gate(
    "R1B_holdout_not_evaluated",
    r1b_results[
        "holdout_evaluated"
    ]
    is False,
)

gate(
    "R1B_production_training_not_previously_authorized",
    r1b_results[
        "production_training_authorized"
    ]
    is False,
)


expected_disposition = (
    "R1B_MULTI_STEP_STABILITY_CONFIRMED_"
    "COMP007_PRODUCTION_CONTRACT_FREEZE_AUTHORIZED_"
    "PRODUCTION_TRAINING_NOT_YET_AUTHORIZED"
)

gate(
    "R1B_disposition_exact",
    r1b_results[
        "disposition"
    ]
    ==
    expected_disposition,
)


# =============================================================================
# Final R1B scientific stability evidence
# =============================================================================

final_amp = r1b_results[
    "final_amplification"
]

final_nc_amp = r1b_results[
    "final_Nc_amplification"
]


print()
print("R1B FINAL TRAIN STABILITY GATES")

gate(
    "final_physics_improved",
    float(
        final_amp[
            "physics"
        ]
    )
    <=
    1.0,
)

gate(
    "final_total_improved",
    float(
        final_amp[
            "total"
        ]
    )
    <=
    1.0,
)

gate(
    "final_data_within_1_25",
    float(
        final_amp[
            "data"
        ]
    )
    <=
    1.25,
)

gate(
    "final_anchor_within_2",
    float(
        final_amp[
            "anchor"
        ]
    )
    <=
    2.0,
)

gate(
    "final_mono_within_2",
    float(
        final_amp[
            "mono"
        ]
    )
    <=
    2.0,
)

gate(
    "all_final_Nc_within_1_5",
    all(
        float(value)
        <=
        1.5
        for value in final_nc_amp.values()
    ),
)


# =============================================================================
# Runtime/environment declaration
# =============================================================================

print()
print("RUNTIME DECLARATION")

gate(
    "CUDA_available",
    torch.cuda.is_available(),
)

device_name = torch.cuda.get_device_name(
    0
)

total_gib = (
    torch.cuda
    .get_device_properties(0)
    .total_memory
    /
    1024 ** 3
)

print(
    "  PyTorch :",
    torch.__version__,
)

print(
    "  GPU     :",
    device_name,
)

print(
    "  Memory  :",
    f"{total_gib:.3f} GiB",
)

gate(
    "A100_runtime",
    "A100"
    in device_name,
)

gate(
    "A100_memory_at_least_70GiB",
    total_gib
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


# =============================================================================
# Freeze production contract
# =============================================================================

RUNNER_SHA = sha256(
    Path(
        __file__
    )
)


CONTRACT = {
    "milestone":
        MILESTONE,

    "experiment":
        EXPERIMENT,

    "COMP007_production_training_authorized":
        True,

    "Stage2_certified":
        False,

    "B3_authorized":
        False,

    "runner_sha256":
        RUNNER_SHA,

    "evidence": {
        "R1AR_runner_sha256":
            EXPECTED[
                "R1AR"
            ],

        "R1AR_results_sha256":
            EXPECTED[
                "R1AR_RESULTS"
            ],

        "R1B_runner_sha256":
            EXPECTED[
                "R1B"
            ],

        "R1B_results_sha256":
            EXPECTED[
                "R1B_RESULTS"
            ],

        "R1B_summary_sha256":
            EXPECTED[
                "R1B_SUMMARY"
            ],

        "R1B_handoff_sha256":
            EXPECTED[
                "R1B_HANDOFF"
            ],
    },

    "initialization": {
        "model_weights":
            "EXACT_FROZEN_COMP005",

        "model_checkpoint_sha256":
            EXPECTED[
                "COMP005"
            ],

        "optimizer_state":
            "FRESH",

        "optimizer_momentum_transferred":
            False,
    },

    "model": {
        "architecture":
            "UNCHANGED_COMP006_LIFTED_ETA_MODEL",

        "new_trainable_parameters":
            0,

        "hard_boundary_lift":
            True,
    },

    "physics": {
        "governing_equation":
            "CORRECTED_CONSERVATIVE_STAGE2_COMPRESSIBLE_PDE",

        "equal_Nc_normalized":
            True,

        "normalization_sha256":
            EXPECTED[
                "CUDA8BR_NORMALIZATION"
            ],

        "Nc_values": [
            0.00,
            0.05,
            0.10,
            0.20,
            0.30,
        ],
    },

    "optimizer": {
        "type":
            "Adam",

        "learning_rate":
            LEARNING_RATE,

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

        "lambda_monotonicity_L1":
            LAMBDA_MONO,
    },

    "training_data": {
        "dataset_sha256":
            EXPECTED[
                "dataset"
            ],

        "train_idx_sha256":
            EXPECTED[
                "train_idx"
            ],

        "holdout_idx_sha256":
            EXPECTED[
                "holdout_idx"
            ],

        "train_profiles":
            11520,

        "holdout_profiles":
            2880,

        "holdout_evaluation_during_training":
            False,

        "holdout_used_for_model_selection":
            False,

        "OOD_used":
            False,

        "TOF_used":
            False,
    },

    "production_geometry": {
        "device_class":
            "NVIDIA_A100_80GB",

        "PyTorch":
            "2.11.0+cu128",

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

    "production_training": {
        "seed":
            SEED,

        "epochs":
            TARGET_EPOCHS,

        "optimizer_steps":
            EXPECTED_TARGET_OPTIMIZER_STEPS,

        "checkpoint_after_every_completed_epoch":
            True,

        "atomic_recovery":
            True,

        "exact_runner_hash_resume":
            True,

        "orphaned_recovery_fail_closed":
            True,
    },

    "checkpoint_selection": {
        "authority":
            "FINAL_COMPLETED_EPOCH_800",

        "early_stopping":
            False,

        "best_holdout_checkpoint_selection":
            False,

        "holdout_checkpoint_selection":
            False,
    },

    "post_training": {
        "Stage2_posttraining_closure_required":
            True,

        "holdout_evaluation_authorized_only_after_epoch800":
            True,

        "B3_remains_blocked_until_Stage2_certification":
            True,
    },
}


atomic_json(
    CONTRACT_PATH,
    CONTRACT,
)


CONTRACT_SHA = sha256(
    CONTRACT_PATH
)


SUMMARY = {
    "milestone":
        MILESTONE,

    "experiment":
        EXPERIMENT,

    "runner_sha256":
        RUNNER_SHA,

    "contract_sha256":
        CONTRACT_SHA,

    "selected_learning_rate":
        LEARNING_RATE,

    "target_epochs":
        TARGET_EPOCHS,

    "target_optimizer_steps":
        EXPECTED_TARGET_OPTIMIZER_STEPS,

    "COMP007_production_training_authorized":
        True,

    "Stage2_certified":
        False,

    "B3_authorized":
        False,

    "holdout_evaluation_during_training":
        False,

    "next_milestone":
        (
            "V16E-1B2CUDA8D-R1D — "
            "COMP007 Authorized Production Training Runner"
        ),
}


atomic_json(
    SUMMARY_PATH,
    SUMMARY,
)


SUMMARY_SHA = sha256(
    SUMMARY_PATH
)


HANDOFF = f"""# PAD-Stream V16E-1B2CUDA8D-R1C

## Status

COMP007 production training is authorized.

This milestone freezes the production contract only.
No training was performed by R1C.

## Experiment

`{EXPERIMENT}`

## Optimizer repair

Fresh Adam learning rate:

`{LEARNING_RATE}`

This is the only optimizer-contract change relative to failed COMP006.

## Production contract

- Exact frozen COMP005 model initialization
- Fresh Adam state
- Adam foreach=False
- LR = {LEARNING_RATE}
- 800 epochs
- 1600 optimizer steps
- CUDA3 K=64 derivative engine
- microbatch 1024
- logical chunks 8192 + 3328
- corrected conservative physics
- equal-Nc normalization
- hard injector/tip boundary lift
- L1 positive-slope monotonicity
- AMP OFF
- TF32 OFF
- no scheduler
- no gradient clipping
- atomic recovery after every completed epoch
- exact-runner-hash resume only
- orphaned recovery fails closed

## Firewall

Holdout evaluation during production training: FORBIDDEN.

Holdout model selection: FORBIDDEN.

OOD: FORBIDDEN.

TOF: FORBIDDEN.

B3: BLOCKED.

The final completed epoch 800 is the production checkpoint authority.

## Scientific status

Stage 2 is NOT yet certified.

After COMP007 production completes, a separate post-training Stage-2 closure
must evaluate the frozen holdout and the previously frozen acceptance gates.

## Hashes

R1C runner SHA-256:

`{RUNNER_SHA}`

Contract SHA-256:

`{CONTRACT_SHA}`

Summary SHA-256:

`{SUMMARY_SHA}`

## Next

`V16E-1B2CUDA8D-R1D — COMP007 Authorized Production Training Runner`
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
print("CUDA8D-R1C RESULT")
print("=" * 110)

print(
    "COMP007 production training authorized:",
    True,
)

print(
    "Selected learning rate:",
    LEARNING_RATE,
)

print(
    "Target epochs:",
    TARGET_EPOCHS,
)

print(
    "Target optimizer steps:",
    EXPECTED_TARGET_OPTIMIZER_STEPS,
)

print()
print(
    "Runner SHA  :",
    RUNNER_SHA,
)

print(
    "Contract SHA:",
    CONTRACT_SHA,
)

print(
    "Summary SHA :",
    SUMMARY_SHA,
)

print(
    "Handoff SHA :",
    HANDOFF_SHA,
)

print()
print("STAGE 2 CERTIFIED: NO")
print("B3 AUTHORIZED: NO")
print("HOLDOUT DURING TRAINING: FORBIDDEN")

print()
print(
    "NEXT: "
    "V16E-1B2CUDA8D-R1D — "
    "COMP007 Authorized Production Training Runner"
)
