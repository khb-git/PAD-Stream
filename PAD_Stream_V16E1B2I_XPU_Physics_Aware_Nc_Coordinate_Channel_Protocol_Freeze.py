#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2I-XPU
Physics-Aware Nc Coordinate-Channel Protocol Freeze

Purpose
-------
Freeze the next controlled Stage-2 experiment after V16E-1B2H established:

  * physical Nc groups are all well represented in train/holdout;
  * per-Nc data and physics losses rise toward high Nc;
  * COMP-XPU-002 and COMP-XPU-003 both under-respond to physical Nc relative
    to the conservative Godunov teacher;
  * simple input scaling improves absolute error but does not flatten the
    relative high-Nc weakness.

This milestone performs NO TRAINING.

New experiment
--------------
V16E-BLREP-COMP-XPU-004

One scientific architecture change
----------------------------------
Keep the original raw physical 11-D conditioner unchanged and add ONE
physics-aware sequence channel to the existing xi channel:

    x_D(xi) = xi * xD_star

    y(x_D; Nc) =
        x_D                                      if Nc -> 0
        -expm1(-Nc*x_D) / Nc                     otherwise

    eta(xi; Nc) = y(xi*xD_star; Nc) / y(xD_star; Nc)

The LSTM sequence input changes from:

    [xi]

to:

    [xi, eta]

while the repeated raw 11-D physical conditioner remains unchanged.

Properties:
  * eta is dimensionless and bounded approximately in [0,1];
  * eta(0)=0 and eta(1)=1;
  * at Nc=0, eta(xi)=xi exactly;
  * eta exposes the compressibility-induced coordinate stretch already used
    by the frozen Stage-2 physics formulation.

Scientific firewall
-------------------
UNCHANGED:
  * physical Nc values
  * exact frozen Godunov dataset
  * conservative Godunov teacher
  * breakthrough-time calculation
  * physics residual
  * y(x;Nc) definition itself
  * raw 11-D p11 conditioner
  * loss terms and loss weights
  * 800 epochs
  * fresh seed-1337 initialization
  * 2 x LSTM(64)
  * Adam lr=1e-3
  * logical batch=8192
  * XPU microbatch=2048
  * Adam foreach=False
  * NX_TRAIN=1601 / NX_REF=3201
  * source-native 80/20 split as development diagnostic only
  * no OOD
  * no TOF

This protocol does NOT authorize B3. COMP-XPU-004 must be trained and compared
prospectively against COMP-XPU-002 (raw conditioner baseline) using the frozen
B2D/B2G diagnostic structure.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import sys


R = Path(__file__).resolve().parent

OUT = (
    R / "output"
    / "V16_E1B2I_XPU_PHYSICS_AWARE_NC_COORDINATE_CHANNEL_PROTOCOL_FREEZE"
)
OUT.mkdir(parents=True, exist_ok=True)

PROTOCOL = OUT / "V16E1B2I_COMP_XPU_004_Physics_Aware_Nc_Channel_Protocol.json"
INTERPRETATION = OUT / "V16E1B2I_B2H_Interpretation.json"
HANDOFF = OUT / "V16E1B2I_Execution_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2I_XPU_Summary.json"

# ---------------------------------------------------------------------
# Frozen Stage-2 source
# ---------------------------------------------------------------------

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

# ---------------------------------------------------------------------
# COMP-XPU-002 baseline
# ---------------------------------------------------------------------

COMP002_DIR = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-002"
)

COMP002_CHECKPOINT = COMP002_DIR / "V16E_BLREP_COMP_XPU_002.pt"
COMP002_METRICS = COMP002_DIR / "V16E_BLREP_COMP_XPU_002_Metrics.json"
COMP002_MANIFEST = COMP002_DIR / "V16E_BLREP_COMP_XPU_002_Manifest.json"
COMP002_SUMMARY = COMP002_DIR / "PAD_Stream_V16E1B2C_XPU_Summary.json"

COMP002_CHECKPOINT_SHA = "fca205b1981fbbdf15424af8ac8174df88ff7addf99e718548319a81f87d271b"
COMP002_METRICS_SHA = "f17fa9f5d6e5954119dc3e412fc01052b4cfb6173c157ac71ff1aa04b0a0385d"
COMP002_MANIFEST_SHA = "3ab6abb7fe60ef5e6dcacfa3f543c65578a39fb64b0219357a658604edc1a48f"
COMP002_SUMMARY_SHA = "8ede892568a1e21c989f5c2782a3f0696e00480a0d671771e6fead754a6b9788"

DATASET = (
    R / "output"
    / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

# ---------------------------------------------------------------------
# B2G scaling comparison
# ---------------------------------------------------------------------

B2G_SOURCE = (
    R
    / "PAD_Stream_V16E1B2G_XPU_COMP_XPU_002_vs_003_Nc_Conditioning_Comparison.py"
)
B2G_SOURCE_SHA = "18a8e63f0cc7de4c4e2093019c72b438f561bb2d66602c74b6e842bf13bd06aa"

B2G_DIR = (
    R / "output"
    / "V16_E1B2G_XPU_COMPRESSIBLE_COMP002_vs_COMP003_COMPARISON"
)
B2G_COMPARISON = B2G_DIR / "V16E1B2G_COMP_XPU_002_vs_003_Comparison.json"
B2G_SUMMARY = B2G_DIR / "PAD_Stream_V16E1B2G_XPU_Summary.json"

B2G_COMPARISON_SHA = "f283e87e1fb1ac115016846dd60817040e177714a2f2f117956554a530179320"
B2G_SUMMARY_SHA = "5d771ba5daba6e8630c5612aa8f1b76d0d9db73097486060e62fc663a29dee4b"

# ---------------------------------------------------------------------
# B2H response audit
# ---------------------------------------------------------------------

B2H_SOURCE = R / "PAD_Stream_V16E1B2H_XPU_Nc_Conditioning_Response_Audit.py"
B2H_SOURCE_SHA = "6196f874a34414ae0db43c6c3253e9ad12755b959ac19d61e6bfe26327616987"

B2H_DIR = (
    R / "output"
    / "V16_E1B2H_XPU_NC_CONDITIONING_RESPONSE_AUDIT"
)
B2H_AUDIT = B2H_DIR / "V16E1B2H_Nc_Conditioning_Response_Audit.json"
B2H_SUMMARY = B2H_DIR / "PAD_Stream_V16E1B2H_XPU_Summary.json"

B2H_AUDIT_SHA = "e033f0e8b9e64729ef0469514e6c0909c2150c5290851648f98f5b8a0c60c8bc"
B2H_SUMMARY_SHA = "662ac29e5413d4761bbcf6234245e62bf11671f7a9412a33b8998fb8da10a48a"

EXPECTED_B2H_STATUS = (
    "V16E1B2H_XPU_NC_CONDITIONING_RESPONSE_AUDIT_COMPLETE_"
    "PHYSICAL_NC_COUNTS_PER_NC_LOSS_COMPONENTS_AND_MODEL_TO_TEACHER_RESPONSE_GAINS_FROZEN_"
    "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
    "NEXT_INTERVENTION_REQUIRES_INTERPRETATION_B3_NOT_AUTHORIZED"
)

NEW_EXPERIMENT_ID = "V16E-BLREP-COMP-XPU-004"


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


def finite(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2I-XPU")
    print("Physics-Aware Nc Coordinate-Channel Protocol Freeze")
    print("=" * 80)
    print("PROTOCOL ONLY — NO TRAINING.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2I summary already exists; refusing overwrite."
        )

    gates = {
        "Stage2_source_SHA_exact":
            exact(STAGE2, STAGE2_SHA),

        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),

        "COMP002_checkpoint_SHA_exact":
            exact(COMP002_CHECKPOINT, COMP002_CHECKPOINT_SHA),
        "COMP002_metrics_SHA_exact":
            exact(COMP002_METRICS, COMP002_METRICS_SHA),
        "COMP002_manifest_SHA_exact":
            exact(COMP002_MANIFEST, COMP002_MANIFEST_SHA),
        "COMP002_summary_SHA_exact":
            exact(COMP002_SUMMARY, COMP002_SUMMARY_SHA),

        "B2G_source_SHA_exact":
            exact(B2G_SOURCE, B2G_SOURCE_SHA),
        "B2G_comparison_SHA_exact":
            exact(B2G_COMPARISON, B2G_COMPARISON_SHA),
        "B2G_summary_SHA_exact":
            exact(B2G_SUMMARY, B2G_SUMMARY_SHA),

        "B2H_source_SHA_exact":
            exact(B2H_SOURCE, B2H_SOURCE_SHA),
        "B2H_audit_SHA_exact":
            exact(B2H_AUDIT, B2H_AUDIT_SHA),
        "B2H_summary_SHA_exact":
            exact(B2H_SUMMARY, B2H_SUMMARY_SHA),
    }

    b2h_summary = read_json(B2H_SUMMARY) if B2H_SUMMARY.exists() else {}
    audit = read_json(B2H_AUDIT) if B2H_AUDIT.exists() else {}

    gates.update({
        "B2H_status_exact":
            b2h_summary.get("status") == EXPECTED_B2H_STATUS,
        "B2H_B3_false":
            b2h_summary.get("B3_authorized") is False,
        "B2H_interpretation_required":
            b2h_summary.get("next_intervention_requires_interpretation") is True,
    })

    counts = audit.get("physical_Nc_counts", {})
    losses = audit.get("holdout_loss_components", {})
    gains = audit.get("response_gain", {})

    expected_nc_keys = {"0.00", "0.05", "0.10", "0.20", "0.30"}

    gates.update({
        "all_Nc_groups_present_all":
            set(counts.get("all", {}).keys()) == expected_nc_keys,
        "all_Nc_groups_present_train":
            set(counts.get("train", {}).keys()) == expected_nc_keys,
        "all_Nc_groups_present_holdout":
            set(counts.get("holdout", {}).keys()) == expected_nc_keys,
        "all_train_Nc_counts_positive":
            all(
                int(v) > 0
                for v in counts.get("train", {}).values()
            ),
        "all_holdout_Nc_counts_positive":
            all(
                int(v) > 0
                for v in counts.get("holdout", {}).values()
            ),
    })

    comp2_losses = losses.get("COMP_XPU_002", {})
    comp3_losses = losses.get("COMP_XPU_003", {})

    gates.update({
        "COMP002_per_Nc_losses_present":
            set(comp2_losses.keys()) == expected_nc_keys,
        "COMP003_per_Nc_losses_present":
            set(comp3_losses.keys()) == expected_nc_keys,
        "all_per_Nc_losses_finite":
            all(
                finite(rec.get(k))
                for model_rec in (comp2_losses, comp3_losses)
                for rec in model_rec.values()
                for k in ("data", "physics", "total")
            ),
    })

    # Freeze natural response-gain observation relative to the teacher reference 1.0.
    # This is not an invented acceptance threshold; gain=1 is the definition of
    # equal model/teacher profile-change magnitude.
    all_gain_values = []
    all_excl_gain_values = []

    for case_name in ("case1", "case2"):
        for model_name in ("COMP_XPU_002", "COMP_XPU_003"):
            records = gains.get(case_name, {}).get(model_name, {})
            for rec in records.values():
                all_gain_values.append(
                    rec.get("model_to_teacher_response_gain")
                )
                all_excl_gain_values.append(
                    rec.get("front_excluded_model_to_teacher_response_gain")
                )

    gates.update({
        "response_gain_values_present":
            len(all_gain_values) == 16,
        "front_excluded_gain_values_present":
            len(all_excl_gain_values) == 16,
        "all_response_gains_finite":
            all(finite(v) for v in all_gain_values),
        "all_front_excluded_gains_finite":
            all(finite(v) for v in all_excl_gain_values),
        "all_response_gains_below_teacher_reference":
            all(float(v) < 1.0 for v in all_gain_values),
        "all_front_excluded_gains_below_teacher_reference":
            all(float(v) < 1.0 for v in all_excl_gain_values),
    })

    print("AUTHORITY / INTERPRETATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "V16E-1B2I protocol freeze blocked by authority/interpretation gate."
        )

    interpretation = {
        "milestone": "V16E-1B2I-XPU",
        "B2H_audit_sha256": B2H_AUDIT_SHA,

        "frozen_observations": {
            "physical_Nc_counts": counts,
            "COMP_XPU_002_per_Nc_holdout_losses": comp2_losses,
            "COMP_XPU_003_per_Nc_holdout_losses": comp3_losses,
            "all_model_to_teacher_response_gains_below_1": True,
            "all_front_excluded_model_to_teacher_response_gains_below_1": True,
            "response_gain_reference":
                "1.0 means model and teacher have equal mean absolute profile-change magnitude",
        },

        "scientific_interpretation":
            "The frozen physical Nc groups are all well represented, so a missing "
            "or severely depleted high-Nc training group is not the explanation. "
            "Both COMP-XPU-002 and COMP-XPU-003 show systematically sub-unity "
            "model-to-teacher Nc response gains in both source cases, including "
            "front-excluded diagnostics. Simple Nc input scaling increases some "
            "response gains but does not solve the relative high-Nc weakness. "
            "The next controlled hypothesis is therefore that the recurrent model "
            "needs the known compressibility coordinate stretch exposed explicitly "
            "as a sequence feature rather than relying on the LSTM to infer it "
            "from the scalar conditioner.",

        "why_not_weighting_first":
            "Per-Nc losses increase with Nc, but the sample groups are already "
            "represented and the audit directly demonstrates insufficient profile "
            "response to Nc. A fixed high-Nc loss multiplier would require choosing "
            "a new weighting magnitude without a source-prescribed value. The "
            "physics-aware coordinate channel tests the observed response deficiency "
            "without inventing a loss coefficient.",

        "not_concluded": [
            "loss weighting can never help",
            "the original Stage-2 source is invalid",
            "the Godunov teacher is incorrect",
            "a physics-aware channel is guaranteed to solve the issue",
        ],
    }

    INTERPRETATION.write_text(
        json.dumps(interpretation, indent=2),
        encoding="utf-8",
    )

    protocol = {
        "milestone": "V16E-1B2I-XPU",
        "new_experiment_id": NEW_EXPERIMENT_ID,
        "classification":
            "PROSPECTIVE_ONE_FACTOR_PHYSICS_AWARE_NC_SEQUENCE_FEATURE_STUDY",

        "hypothesis":
            "The persistent high-Nc under-response arises because the LSTM must "
            "infer the known compressibility coordinate stretch indirectly from "
            "the raw scalar Nc conditioner. Supplying the normalized stretched "
            "coordinate eta as an explicit sequence feature may improve Nc response.",

        "one_scientific_change": {
            "field": "sequence_input_features",
            "old": ["xi"],
            "new": ["xi", "eta"],
            "eta_definition": {
                "xD": "xi * xD_star",
                "y": "-expm1(-Nc*xD)/Nc with exact Nc->0 limit y=xD",
                "eta": "y(xi*xD_star;Nc) / y(xD_star;Nc)",
            },
            "input_feature_count_old": 1,
            "input_feature_count_new": 2,
        },

        "mathematical_properties": {
            "eta_at_xi_0": 0.0,
            "eta_at_xi_1": 1.0,
            "eta_Nc0_limit": "xi",
            "eta_dimensionless": True,
            "eta_uses_physical_Nc": True,
            "eta_uses_physical_xD_star": True,
        },

        "raw_conditioner_policy": {
            "p11_remains":
                "[no,nw,swi,sor,mu_w,mu_o,phi,tD,xD_star,Sw_star,Nc_physical]",
            "Nc_scaled_in_p11": False,
            "COMP_XPU_003_Nc_over_0p30_not_carried_forward": True,
            "comparison_baseline": "COMP-XPU-002",
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
            "physical_Nc_grid": [0.0, 0.05, 0.10, 0.20, 0.30],
            "train_fraction": 0.8,
            "split_seed": 1337,
        },

        "physics_firewall": {
            "Godunov_teacher_changed": False,
            "physical_Nc_changed": False,
            "breakthrough_time_changed": False,
            "physics_residual_changed": False,
            "y_transform_changed": False,
            "front_definition_changed": False,
            "loss_weights_changed": False,
            "dataset_rebuilt": False,
            "raw_p11_changed": False,
            "OOD_claim": False,
            "TOF": False,
        },

        "runtime_feature_policy": {
            "derive_eta_from_frozen_xi_and_physical_p11_at_runtime": True,
            "dataset_file_contents_modified": False,
            "new_dataset_artifact_required": False,
        },

        "evaluation_policy": {
            "development_diagnostic_split_reused": True,
            "NOT_independent_test": True,
            "NOT_OOD": True,
            "compare_against": "COMP-XPU-002",
            "repeat_metrics": [
                "overall reproduction-development metrics",
                "per-Nc holdout MAE/RMSE/max error",
                "per-Nc data/physics/total loss",
                "full-domain fine-grid Godunov error",
                "front-excluded fine-grid Godunov error",
                "front-position error",
                "model-to-teacher Nc response gain",
                "Nc0.30/Nc0 response ratios",
                "Nc=0 Stage-1 nesting diagnostics",
                "saturation bounds",
            ],
            "numeric_acceptance_threshold": None,
            "B3_automatic_authorization": False,
        },
    }

    PROTOCOL.write_text(
        json.dumps(protocol, indent=2),
        encoding="utf-8",
    )

    handoff = (
        "# V16E-1B2I-XPU Execution Handoff\n\n"
        f"Authorized next experiment: **{NEW_EXPERIMENT_ID}**.\n\n"
        "Use COMP-XPU-002 as the scientific baseline. Keep the exact raw physical "
        "11-D conditioner unchanged and add one runtime-derived sequence channel:\n\n"
        "    eta = y(xi*xD_star; Nc) / y(xD_star; Nc)\n\n"
        "where y(x;Nc) = -expm1(-Nc*x)/Nc with the exact Nc->0 limit y=x.\n\n"
        "The sequence feature array becomes [xi, eta]. The Godunov teacher, "
        "physical Nc, physics residual, loss weights, training schedule, dataset, "
        "and all other settings remain unchanged.\n\n"
        "COMP-XPU-003 scaling is not carried forward into COMP-XPU-004.\n\n"
        "B3 remains blocked until COMP-XPU-004 is trained and compared against "
        "COMP-XPU-002 using the frozen diagnostics.\n"
    )

    HANDOFF.write_text(
        handoff,
        encoding="utf-8",
    )

    gates.update({
        "interpretation_written":
            INTERPRETATION.exists() and INTERPRETATION.stat().st_size > 0,
        "protocol_written":
            PROTOCOL.exists() and PROTOCOL.stat().st_size > 0,
        "handoff_written":
            HANDOFF.exists() and HANDOFF.stat().st_size > 0,
        "one_scientific_change_only":
            True,
        "raw_p11_preserved":
            True,
        "physical_Nc_preserved":
            True,
        "loss_weights_preserved":
            True,
        "dataset_preserved":
            True,
        "COMP003_scaling_not_carried_forward":
            True,
        "B3_not_authorized":
            True,
        "no_training":
            True,
        "no_OOD":
            True,
        "no_TOF":
            True,
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2I_XPU_PHYSICS_AWARE_NC_COORDINATE_CHANNEL_PROTOCOL_FROZEN_"
        "NC_GROUPS_REPRESENTED_SYSTEMATIC_MODEL_TO_TEACHER_UNDER_RESPONSE_CONFIRMED_"
        "SIMPLE_NC_SCALING_NOT_SUFFICIENT_"
        "ONE_FACTOR_SEQUENCE_FEATURE_XI_PLUS_NORMALIZED_STRETCHED_COORDINATE_ETA_AUTHORIZED_"
        "RAW_PHYSICAL_P11_GODUNOV_TEACHER_PHYSICS_RESIDUAL_LOSSES_AND_DATASET_UNCHANGED_"
        "FRESH_800_EPOCH_COMP_XPU_004_AUTHORIZED_NO_OOD_NO_TOF_B3_NOT_YET_AUTHORIZED"
        if ok else
        "V16E1B2I_XPU_PROTOCOL_FREEZE_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone": "V16E-1B2I-XPU",
        "status": status,
        "authorized_next_experiment":
            NEW_EXPERIMENT_ID if ok else None,
        "training_authorized_next":
            bool(ok),
        "B3_authorized":
            False,
        "protocol_sha256":
            sha256(PROTOCOL),
        "interpretation_sha256":
            sha256(INTERPRETATION),
        "handoff_sha256":
            sha256(HANDOFF),
        "gates":
            {k: bool(v) for k, v in gates.items()},
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
        "— fresh 800-epoch physics-aware Nc coordinate-channel study",
    )

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
