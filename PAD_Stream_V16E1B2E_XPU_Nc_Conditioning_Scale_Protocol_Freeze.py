#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2E-XPU
Compressible BL Nc Conditioning-Scale Protocol Freeze

Purpose
-------
Freeze the next controlled Stage-2 experiment after V16E-1B2D established:

  1) 800 epochs improves absolute Stage-2 accuracy;
  2) the relative high-Nc weakness persists;
  3) undertraining alone is therefore not a sufficient explanation.

Source inspection also confirms that Stage 2 concatenates the raw 11-D
conditioning vector directly into the LSTM input, with Nc as the last entry
and no explicit conditioner normalization in build_model.

This milestone performs NO TRAINING.

New experiment
--------------
V16E-BLREP-COMP-XPU-003

ONE SCIENTIFIC CHANGE ONLY
--------------------------
Network conditioning representation of Nc:

    old: Nc_cond = Nc
    new: Nc_cond = Nc / 0.30

Thus the frozen training grid maps:

    0.00 -> 0.000000
    0.05 -> 0.166667
    0.10 -> 0.333333
    0.20 -> 0.666667
    0.30 -> 1.000000

CRITICAL PHYSICS FIREWALL
-------------------------
The physical Nc used by:
  * Godunov teacher,
  * breakthrough time,
  * travel-time transform,
  * physics residual y(x;Nc),
  * diagnostics / labels,

MUST remain the original physical Nc in [0, 0.30].

Only the copy of Nc presented to the neural-network conditioner is scaled.
The physics residual must NOT read the scaled conditioner value as physical Nc.

Therefore COMP-XPU-003 requires an explicit separation:

    p11_phys  = [..., Nc_physical]
    p11_model = [..., Nc_physical / 0.30]

The range-map indices swc=2, sor=3 and the physical indices
xD_star=8, Sw_star=9 remain unchanged.

Everything else remains frozen relative to COMP-XPU-002:
  * exact Stage-2 Godunov dataset
  * exact Stage-2 source equations
  * 800 epochs
  * fresh seed-1337 initialization
  * 2 x LSTM(64)
  * Adam lr=1e-3
  * same loss terms / weights
  * logical batch 8192
  * XPU microbatch 2048
  * Adam foreach=False execution amendment
  * same 80/20 reproduction-development split
  * same NX_TRAIN=1601, NX_REF=3201
  * no OOD
  * no TOF

B3 remains blocked until COMP-XPU-003 is trained and compared prospectively
against COMP-XPU-002 using the already-frozen B2D diagnostic structure.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys


R = Path(__file__).resolve().parent

OUT = (
    R / "output"
    / "V16_E1B2E_XPU_NC_CONDITIONING_SCALE_PROTOCOL_FREEZE"
)
OUT.mkdir(parents=True, exist_ok=True)

PROTOCOL = OUT / "V16E1B2E_COMP_XPU_003_Nc_Conditioning_Scale_Protocol.json"
INTERPRETATION = OUT / "V16E1B2E_B2D_Interpretation.json"
HANDOFF = OUT / "V16E1B2E_Execution_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2E_XPU_Summary.json"

# ---------------------------------------------------------------------
# Stage-2 source
# ---------------------------------------------------------------------

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

# ---------------------------------------------------------------------
# COMP-XPU-002 / B2C evidence
# ---------------------------------------------------------------------

B2C_RUNNER = R / "PAD_Stream_V16E1B2C_XPU_COMP_XPU_002_800Epoch_Compressible_Reproduction.py"
B2C_RUNNER_SHA = "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18"

B2C_DIR = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-002"
)

DATASET = (
    R / "output"
    / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)

B2C_CHECKPOINT = B2C_DIR / "V16E_BLREP_COMP_XPU_002.pt"
B2C_METRICS = B2C_DIR / "V16E_BLREP_COMP_XPU_002_Metrics.json"
B2C_MANIFEST = B2C_DIR / "V16E_BLREP_COMP_XPU_002_Manifest.json"
B2C_SUMMARY = B2C_DIR / "PAD_Stream_V16E1B2C_XPU_Summary.json"
R2_AMENDMENT = B2C_DIR / "V16E_BLREP_COMP_XPU_002_R2_LowMemory_Adam_Execution_Amendment.json"
R2_RECORD = B2C_DIR / "V16E_BLREP_COMP_XPU_002_R2_Execution_Record.json"

DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"
B2C_CHECKPOINT_SHA = "fca205b1981fbbdf15424af8ac8174df88ff7addf99e718548319a81f87d271b"
B2C_METRICS_SHA = "f17fa9f5d6e5954119dc3e412fc01052b4cfb6173c157ac71ff1aa04b0a0385d"
B2C_MANIFEST_SHA = "3ab6abb7fe60ef5e6dcacfa3f543c65578a39fb64b0219357a658604edc1a48f"
B2C_SUMMARY_SHA = "8ede892568a1e21c989f5c2782a3f0696e00480a0d671771e6fead754a6b9788"
R2_AMENDMENT_SHA = "7fefa284d163de2f9825e31077226889cceea991e12af6a5e6b43d3e795a5ead"
R2_RECORD_SHA = "e2f2b0c22bfab49ff2d3aac2b46b3b341f5aeb7b69875a89c303e30a80e05788"

# ---------------------------------------------------------------------
# B2D comparison evidence
# ---------------------------------------------------------------------

B2D_SOURCE = R / "PAD_Stream_V16E1B2D_XPU_COMP_XPU_001_vs_002_Scientific_Comparison.py"
B2D_SOURCE_SHA = "ece92813cd9ccd59afd0c8eb708cc6964863d22d425acc47e20b55082c2efe00"

B2D_DIR = (
    R / "output"
    / "V16_E1B2D_XPU_COMPRESSIBLE_400_vs_800_COMPARISON"
)
B2D_COMPARISON = B2D_DIR / "V16E1B2D_COMP_XPU_001_vs_002_Comparison.json"
B2D_SUMMARY = B2D_DIR / "PAD_Stream_V16E1B2D_XPU_Summary.json"

B2D_COMPARISON_SHA = "e956f5eb82b34b5af9a085674d8c0ae34da666d65b0c478d37fa71af2ce974fc"
B2D_SUMMARY_SHA = "90af2e6e06b49f220e9cbb61fa84ee21312e8d45311c97ff95bc5e75b4210f8c"

EXPECTED_B2D_STATUS = (
    "V16E1B2D_XPU_COMP_XPU_001_VS_002_SCIENTIFIC_COMPARISON_COMPLETE_"
    "OVERALL_PER_NC_HOLDOUT_FULL_DOMAIN_FRONT_EXCLUDED_AND_FRONT_POSITION_TRENDS_FROZEN_"
    "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
    "B3_DECISION_REQUIRES_INTERPRETATION"
)

NEW_EXPERIMENT_ID = "V16E-BLREP-COMP-XPU-003"
NC_SCALE_DENOMINATOR = 0.30


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


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2E-XPU")
    print("Compressible BL Nc Conditioning-Scale Protocol Freeze")
    print("=" * 80)
    print("PROTOCOL ONLY — NO TRAINING.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2E summary already exists; refusing overwrite."
        )

    gates = {
        "Stage2_source_SHA_exact":
            exact(STAGE2, STAGE2_SHA),
        "B2C_runner_SHA_exact":
            exact(B2C_RUNNER, B2C_RUNNER_SHA),
        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),
        "B2C_checkpoint_SHA_exact":
            exact(B2C_CHECKPOINT, B2C_CHECKPOINT_SHA),
        "B2C_metrics_SHA_exact":
            exact(B2C_METRICS, B2C_METRICS_SHA),
        "B2C_manifest_SHA_exact":
            exact(B2C_MANIFEST, B2C_MANIFEST_SHA),
        "B2C_summary_SHA_exact":
            exact(B2C_SUMMARY, B2C_SUMMARY_SHA),
        "R2_amendment_SHA_exact":
            exact(R2_AMENDMENT, R2_AMENDMENT_SHA),
        "R2_record_SHA_exact":
            exact(R2_RECORD, R2_RECORD_SHA),

        "B2D_source_SHA_exact":
            exact(B2D_SOURCE, B2D_SOURCE_SHA),
        "B2D_comparison_SHA_exact":
            exact(B2D_COMPARISON, B2D_COMPARISON_SHA),
        "B2D_summary_SHA_exact":
            exact(B2D_SUMMARY, B2D_SUMMARY_SHA),
    }

    b2d = read_json(B2D_SUMMARY) if B2D_SUMMARY.exists() else {}
    gates.update({
        "B2D_status_exact":
            b2d.get("status") == EXPECTED_B2D_STATUS,
        "B2D_B3_false":
            b2d.get("B3_authorized") is False,
        "B2D_interpretation_required":
            b2d.get("B3_decision_requires_interpretation") is True,
    })

    # Freeze the actual B2D descriptive evidence.
    overall_rmse_improvement = b2d.get(
        "overall_RMSE_percent_improvement"
    )
    overall_mae_improvement = b2d.get(
        "overall_MAE_percent_improvement"
    )
    holdout_ratio_400 = b2d.get("holdout_ratio_400")
    holdout_ratio_800 = b2d.get("holdout_ratio_800")
    full_ratio_400 = b2d.get("case1_full_ratio_400")
    full_ratio_800 = b2d.get("case1_full_ratio_800")
    excl_ratio_400 = b2d.get("case1_front_excluded_ratio_400")
    excl_ratio_800 = b2d.get("case1_front_excluded_ratio_800")

    for name, value in {
        "overall_rmse_improvement_present": overall_rmse_improvement,
        "overall_mae_improvement_present": overall_mae_improvement,
        "holdout_ratio_400_present": holdout_ratio_400,
        "holdout_ratio_800_present": holdout_ratio_800,
        "full_ratio_400_present": full_ratio_400,
        "full_ratio_800_present": full_ratio_800,
        "excl_ratio_400_present": excl_ratio_400,
        "excl_ratio_800_present": excl_ratio_800,
    }.items():
        gates[name] = isinstance(value, (int, float))

    # Undertraining alone is not sufficient if absolute accuracy improves but
    # a relative high-Nc weakness remains after 800 epochs.
    gates["absolute_accuracy_improved"] = (
        isinstance(overall_rmse_improvement, (int, float))
        and isinstance(overall_mae_improvement, (int, float))
        and overall_rmse_improvement > 0.0
        and overall_mae_improvement > 0.0
    )

    gates["high_Nc_relative_weakness_persists"] = (
        isinstance(holdout_ratio_800, (int, float))
        and isinstance(full_ratio_800, (int, float))
        and isinstance(excl_ratio_800, (int, float))
        and holdout_ratio_800 > 1.0
        and full_ratio_800 > 1.0
        and excl_ratio_800 > 1.0
    )

    print("AUTHORITY / INTERPRETATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "V16E-1B2E protocol freeze blocked by authority/interpretation gate."
        )

    interpretation = {
        "milestone": "V16E-1B2E-XPU",
        "B2D_comparison_sha256": B2D_COMPARISON_SHA,

        "frozen_observations": {
            "overall_RMSE_percent_improvement_400_to_800":
                overall_rmse_improvement,
            "overall_MAE_percent_improvement_400_to_800":
                overall_mae_improvement,
            "holdout_Nc030_over_Nc000_400":
                holdout_ratio_400,
            "holdout_Nc030_over_Nc000_800":
                holdout_ratio_800,
            "case1_full_Nc030_over_Nc000_400":
                full_ratio_400,
            "case1_full_Nc030_over_Nc000_800":
                full_ratio_800,
            "case1_front_excluded_Nc030_over_Nc000_400":
                excl_ratio_400,
            "case1_front_excluded_Nc030_over_Nc000_800":
                excl_ratio_800,
        },

        "source_architecture_observation":
            "Frozen Stage-2 build_model repeats the raw p_vec across sequence "
            "nodes and concatenates it directly with xi before the LSTM. "
            "Nc is the 11th/final conditioner. No explicit conditioner "
            "normalization is present in build_model.",

        "scientific_interpretation":
            "Increasing training duration from 400 to 800 epochs improved "
            "absolute accuracy but did not remove the relative high-Nc weakness. "
            "Undertraining alone is therefore not a sufficient explanation. "
            "A plausible next hypothesis is unfavorable Nc input scaling in "
            "the raw conditioner; this remains a hypothesis, not a conclusion.",

        "not_concluded": [
            "Nc input scaling is definitely the root cause",
            "the Stage-2 PDE residual is wrong",
            "the Godunov teacher is wrong",
            "the LSTM architecture is inadequate",
            "loss weights are definitely wrong",
        ],
    }

    INTERPRETATION.write_text(
        json.dumps(interpretation, indent=2),
        encoding="utf-8",
    )

    protocol = {
        "milestone": "V16E-1B2E-XPU",
        "new_experiment_id": NEW_EXPERIMENT_ID,
        "classification":
            "PROSPECTIVE_ONE_FACTOR_NC_CONDITIONING_SCALE_STUDY",

        "hypothesis":
            "The persistent high-Nc weakness may be caused in part by the "
            "raw neural-network conditioning scale of Nc.",

        "one_scientific_change": {
            "field": "network_conditioner_Nc_representation",
            "old": "Nc_cond = Nc_physical",
            "new": "Nc_cond = Nc_physical / 0.30",
            "physical_grid":
                [0.0, 0.05, 0.10, 0.20, 0.30],
            "network_grid": [
                0.0,
                0.05 / NC_SCALE_DENOMINATOR,
                0.10 / NC_SCALE_DENOMINATOR,
                0.20 / NC_SCALE_DENOMINATOR,
                1.0,
            ],
        },

        "mandatory_physics_conditioner_separation": {
            "p11_phys":
                "[no,nw,swi,sor,mu_w,mu_o,phi,tD,xD_star,Sw_star,Nc_physical]",
            "p11_model":
                "[no,nw,swi,sor,mu_w,mu_o,phi,tD,xD_star,Sw_star,Nc_physical/0.30]",
            "teacher_uses": "Nc_physical",
            "physics_residual_uses": "Nc_physical",
            "breakthrough_and_transform_use": "Nc_physical",
            "neural_LSTM_conditioner_uses": "p11_model",
            "range_map_indices_unchanged": {
                "swc": 2,
                "sor": 3,
            },
            "physics_indices_unchanged": {
                "xD_star": 8,
                "Sw_star": 9,
                "Nc_physical": 10,
            },
        },

        "must_remain_identical_to_COMP_XPU_002": {
            "Stage2_source_sha256": STAGE2_SHA,
            "dataset_sha256": DATASET_SHA,
            "epochs": 800,
            "fresh_initialization": True,
            "seed": 1337,
            "hidden": 64,
            "layers": 2,
            "optimizer": "Adam",
            "learning_rate": 1e-3,
            "logical_batch": 8192,
            "XPU_microbatch": 2048,
            "Adam_foreach": False,
            "loss_weights": {
                "data": 1.0,
                "physics": 0.05,
                "injector_bc": 5.0,
                "tip_bc": 5.0,
                "anchor": 10.0,
                "monotonicity": 0.2,
                "shape": 0.0,
            },
            "NX_TRAIN": 1601,
            "NX_REF": 3201,
            "n_fan": 64,
            "physical_Nc_grid":
                [0.0, 0.05, 0.10, 0.20, 0.30],
            "train_fraction": 0.8,
            "split_seed": 1337,
        },

        "dataset_policy": {
            "rebuild_Godunov_teacher": False,
            "reuse_exact_dataset": True,
            "dataset_contents_modified": False,
            "p11_physical_array_remains_authority": True,
            "scaled_model_conditioner_derived_at_runtime": True,
        },

        "evaluation_policy": {
            "same_development_diagnostic_split": True,
            "NOT_independent_test": True,
            "NOT_OOD": True,
            "repeat_B2D_structure": [
                "overall reproduction diagnostic metrics",
                "per-Nc holdout MAE/RMSE/max",
                "full-domain fine-grid Godunov error",
                "front-excluded fine-grid Godunov error",
                "front-position error",
                "Nc0.30/Nc0 response ratios",
                "Nc=0 Stage-1 nesting diagnostics",
                "saturation bounds",
            ],
            "numeric_acceptance_threshold": None,
            "B3_automatic_authorization": False,
        },

        "firewall": {
            "change_epochs": False,
            "change_dataset": False,
            "change_teacher": False,
            "change_architecture_width_or_depth": False,
            "change_loss_weights": False,
            "change_physical_Nc": False,
            "change_PDE_or_transform": False,
            "change_front_definition": False,
            "OOD_claim": False,
            "TOF": False,
        },
    }

    PROTOCOL.write_text(
        json.dumps(protocol, indent=2),
        encoding="utf-8",
    )

    handoff = (
        "# V16E-1B2E-XPU Execution Handoff\n\n"
        f"Authorized next experiment: **{NEW_EXPERIMENT_ID}**.\n\n"
        "One scientific change only: scale the copy of physical Nc presented "
        "to the neural-network conditioner by 1/0.30 so the training-grid "
        "conditioning interval maps from [0,0.30] to [0,1].\n\n"
        "The physical Nc used by the Godunov teacher, breakthrough calculation, "
        "travel-time transform, physics residual, diagnostics, and labels must "
        "remain unscaled.\n\n"
        "COMP-XPU-003 must start from fresh seed-1337 initialization and use "
        "800 epochs with the exact frozen dataset and all COMP-XPU-002 settings "
        "otherwise unchanged.\n\n"
        "B3 remains blocked until COMP-XPU-003 is compared with COMP-XPU-002.\n"
    )

    HANDOFF.write_text(
        handoff,
        encoding="utf-8",
    )

    gates.update({
        "interpretation_written":
            INTERPRETATION.exists()
            and INTERPRETATION.stat().st_size > 0,
        "protocol_written":
            PROTOCOL.exists()
            and PROTOCOL.stat().st_size > 0,
        "handoff_written":
            HANDOFF.exists()
            and HANDOFF.stat().st_size > 0,
        "one_scientific_change_only": True,
        "physical_Nc_unscaled": True,
        "model_Nc_scaled_only": True,
        "fresh_initialization_required": True,
        "dataset_reuse_required": True,
        "B3_not_authorized": True,
        "no_training": True,
        "no_OOD": True,
        "no_TOF": True,
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2E_XPU_NC_CONDITIONING_SCALE_PROTOCOL_FROZEN_"
        "UNDERTRAINING_NOT_SUFFICIENT_ABSOLUTE_ACCURACY_IMPROVED_BUT_RELATIVE_HIGH_NC_WEAKNESS_PERSISTS_"
        "RAW_STAGE2_CONDITIONER_DIRECT_CONCAT_CONFIRMED_"
        "ONE_FACTOR_NETWORK_NC_SCALE_0P30_TO_UNIT_INTERVAL_AUTHORIZED_"
        "PHYSICAL_NC_TEACHER_RESIDUAL_AND_TRANSFORM_UNCHANGED_"
        "FRESH_800_EPOCH_COMP_XPU_003_AUTHORIZED_NO_OOD_NO_TOF_B3_NOT_YET_AUTHORIZED"
        if ok else
        "V16E1B2E_XPU_PROTOCOL_FREEZE_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone": "V16E-1B2E-XPU",
        "status": status,
        "authorized_next_experiment":
            NEW_EXPERIMENT_ID if ok else None,
        "training_authorized_next": bool(ok),
        "B3_authorized": False,
        "protocol_sha256": sha256(PROTOCOL),
        "interpretation_sha256":
            sha256(INTERPRETATION),
        "handoff_sha256": sha256(HANDOFF),
        "gates": {
            k: bool(v)
            for k, v in gates.items()
        },
    }

    SUMMARY.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Protocol      :", sha256(PROTOCOL))
    print("  Interpretation:", sha256(INTERPRETATION))
    print("  Handoff       :", sha256(HANDOFF))
    print("  Summary       :", sha256(SUMMARY))

    print("\nNEXT")
    print(
        " ",
        NEW_EXPERIMENT_ID,
        "— fresh 800-epoch Nc-conditioning-scale XPU study",
    )

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
