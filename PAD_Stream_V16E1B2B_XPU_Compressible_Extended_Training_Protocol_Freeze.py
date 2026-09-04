#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2B-XPU
Compressible BL Extended-Training Protocol Freeze

NO TRAINING. This milestone prospectively freezes one controlled Stage-2
intervention after V16E-1B2A showed that high-Nc error persists outside the
numerical front zone.

New experiment: V16E-BLREP-COMP-XPU-002
One-factor change: epochs 400 -> 800.

All other scientific/model settings remain unchanged. The new run must start
from fresh initialization; warm-starting from the 400-epoch checkpoint is
prohibited because that checkpoint does not contain Adam optimizer state.
"""

from pathlib import Path
import hashlib
import json
import sys

R = Path(__file__).resolve().parent
OUT = R / "output" / "V16_E1B2B_XPU_COMPRESSIBLE_EXTENDED_TRAINING_PROTOCOL_FREEZE"
OUT.mkdir(parents=True, exist_ok=True)

PROTOCOL = OUT / "V16E1B2B_COMP_XPU_002_Extended_Training_Protocol.json"
INTERPRETATION = OUT / "V16E1B2B_Nc_Diagnostic_Interpretation.json"
HANDOFF = OUT / "V16E1B2B_Execution_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2B_XPU_Summary.json"

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

B2_RUNNER = R / "PAD_Stream_V16E1B2_XPU_Final_Compressible_BL_PIRNN_Native_Coordinate_Reproduction.py"
B2_RUNNER_SHA = "bec3cb8366fa46b18f424f6434123438326e92896ff0dbac018a07cd7403c7ee"

B2_DIR = R / "output" / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS" / "V16E-BLREP-COMP-XPU-001"
B2_DATASET = R / "output" / "V16_E1B_XPU_DATASETS" / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
B2_PORT = B2_DIR / "V16E_BLREP_COMP_XPU_001_Framework_Port_Protocol.json"
B2_CHECKPOINT = B2_DIR / "V16E_BLREP_COMP_XPU_001.pt"
B2_CONFIG = B2_DIR / "V16E_BLREP_COMP_XPU_001_Config.json"
B2_HISTORY = B2_DIR / "V16E_BLREP_COMP_XPU_001_Training_History.json"
B2_METRICS = B2_DIR / "V16E_BLREP_COMP_XPU_001_Metrics.json"
B2_MANIFEST = B2_DIR / "V16E_BLREP_COMP_XPU_001_Manifest.json"
B2_SUMMARY = B2_DIR / "PAD_Stream_V16E1B2_XPU_Summary.json"

B2_DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"
B2_PORT_SHA = "28cf1fdc7cc1faa3f2183eecc137c6a547c1a593cb7348baaa786f24c1a4ff5b"
B2_CHECKPOINT_SHA = "f2239f21603e01a2c80abbb18a787c6b0861959683d99d31261c495ad087f3d0"
B2_CONFIG_SHA = "40ecaaf0876940b4ea5a6158cd6628df452b993e45821773fa9a82cb463d0e5c"
B2_HISTORY_SHA = "3ad1bb77c7b65dcba4db9206b3ffa77f53a10c5f7ba268a065cf23376ea00d7d"
B2_METRICS_SHA = "81fc2e7587f1005445f789d1e9b2e0eb7cbb8a0719a3b9768a692c9e6e124723"
B2_MANIFEST_SHA = "669bdf4f0139e2032718574c7648427c39eb084e87b532ab07370df183178368"
B2_SUMMARY_SHA = "e4a6294064f2d3d31cba614e223b9d7810577f7407d429eddf6c5ddbace474af"

B2A_SOURCE = R / "PAD_Stream_V16E1B2A_XPU_Compressible_Nc_Response_Diagnostic_Audit.py"
B2A_SOURCE_SHA = "2551345c78ab8abcecb181bff809d2436f353cc4d0a6ff643b59f6f1323c941c"
B2A_AUDIT = B2_DIR / "V16E_BLREP_COMP_XPU_001_Nc_Diagnostic_Audit.json"
B2A_SUMMARY = B2_DIR / "PAD_Stream_V16E1B2A_XPU_Summary.json"
B2A_AUDIT_SHA = "44906c63200587e0200b209720dd1e3950708e8089ee90fc8f1476b9a7b29045"
B2A_SUMMARY_SHA = "edadbdfcd83996860d92b556e067692100688d48c9aa5c139adc8b76ec4532ae"

EXPECTED_B2A_STATUS = (
    "V16E1B2A_XPU_COMPRESSIBLE_NC_RESPONSE_DIAGNOSTIC_AUDIT_COMPLETE_"
    "PER_NC_HOLDOUT_FULL_DOMAIN_FRONT_EXCLUDED_AND_FRONT_POSITION_METRICS_FROZEN_"
    "NO_TRAINING_NO_WEIGHT_CHANGE_B3_DECISION_REQUIRES_INTERPRETATION"
)

NEW_EXPERIMENT_ID = "V16E-BLREP-COMP-XPU-002"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def exact(path: Path, expected: str) -> bool:
    return path.exists() and path.is_file() and sha256(path) == expected


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2B-XPU")
    print("Compressible BL Extended-Training Protocol Freeze")
    print("=" * 80)
    print("PROTOCOL ONLY — NO TRAINING.\n")

    if SUMMARY.exists():
        raise RuntimeError("V16E-1B2B summary already exists; refusing overwrite.")

    gates = {
        "Stage2_source_SHA_exact": exact(STAGE2, STAGE2_SHA),
        "B2_runner_SHA_exact": exact(B2_RUNNER, B2_RUNNER_SHA),
        "B2_dataset_SHA_exact": exact(B2_DATASET, B2_DATASET_SHA),
        "B2_port_SHA_exact": exact(B2_PORT, B2_PORT_SHA),
        "B2_checkpoint_SHA_exact": exact(B2_CHECKPOINT, B2_CHECKPOINT_SHA),
        "B2_config_SHA_exact": exact(B2_CONFIG, B2_CONFIG_SHA),
        "B2_history_SHA_exact": exact(B2_HISTORY, B2_HISTORY_SHA),
        "B2_metrics_SHA_exact": exact(B2_METRICS, B2_METRICS_SHA),
        "B2_manifest_SHA_exact": exact(B2_MANIFEST, B2_MANIFEST_SHA),
        "B2_summary_SHA_exact": exact(B2_SUMMARY, B2_SUMMARY_SHA),
        "B2A_source_SHA_exact": exact(B2A_SOURCE, B2A_SOURCE_SHA),
        "B2A_audit_SHA_exact": exact(B2A_AUDIT, B2A_AUDIT_SHA),
        "B2A_summary_SHA_exact": exact(B2A_SUMMARY, B2A_SUMMARY_SHA),
    }

    b2a = read_json(B2A_SUMMARY) if B2A_SUMMARY.exists() else {}
    audit = read_json(B2A_AUDIT) if B2A_AUDIT.exists() else {}
    history = read_json(B2_HISTORY) if B2_HISTORY.exists() else {}

    gates.update({
        "B2A_status_exact": b2a.get("status") == EXPECTED_B2A_STATUS,
        "B2A_no_training": b2a.get("training_executed") is False,
        "B2A_no_weight_change": b2a.get("weights_modified") is False,
        "B2A_B3_not_auto_authorized": b2a.get("B3_automatically_authorized_by_this_audit") is False,
        "B2_history_400_epochs": len(history.get("epoch", [])) == 400,
        "B2_history_last_epoch_400": history.get("epoch", [None])[-1] == 400,
    })

    trends = audit.get("trends", {})
    holdout_ratio = trends.get("holdout_mae", {}).get("Nc030_to_Nc000_ratio")
    case1_full_ratio = trends.get("case1_full_domain_mae", {}).get("Nc030_to_Nc000_ratio")
    case1_excl_ratio = trends.get("case1_front_excluded_mae", {}).get("Nc030_to_Nc000_ratio")

    gates.update({
        "audit_holdout_ratio_present": isinstance(holdout_ratio, (int, float)),
        "audit_full_ratio_present": isinstance(case1_full_ratio, (int, float)),
        "audit_front_excluded_ratio_present": isinstance(case1_excl_ratio, (int, float)),
        "front_excluded_degradation_not_removed": isinstance(case1_excl_ratio, (int, float)) and case1_excl_ratio > 1.0,
    })

    print("AUTHORITY / INTERPRETATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError("V16E-1B2B protocol freeze blocked by authority/interpretation gate.")

    interpretation = {
        "milestone": "V16E-1B2B-XPU",
        "source_audit_sha256": B2A_AUDIT_SHA,
        "frozen_observations": {
            "holdout_MAE_Nc030_to_Nc000_ratio": holdout_ratio,
            "case1_full_domain_MAE_Nc030_to_Nc000_ratio": case1_full_ratio,
            "case1_front_excluded_MAE_Nc030_to_Nc000_ratio": case1_excl_ratio,
            "front_position_error_behavior": "does not worsen with Nc in audited cases",
        },
        "scientific_interpretation": (
            "High-Nc degradation is a profile/fan approximation issue rather than a numerical-front localization issue. "
            "The first controlled hypothesis is undertraining because the frozen Stage-2 source identifies a rising Nc MAE trend as potentially underweighted or undertrained conditioning, and the 400-epoch XPU history continued improving late in training."
        ),
        "not_concluded": [
            "Nc loss weighting is definitely wrong",
            "architecture is inadequate",
            "travel-time transform is wrong",
            "Godunov front definition is wrong",
        ],
    }
    INTERPRETATION.write_text(json.dumps(interpretation, indent=2), encoding="utf-8")

    protocol = {
        "milestone": "V16E-1B2B-XPU",
        "new_experiment_id": NEW_EXPERIMENT_ID,
        "classification": "PROSPECTIVE_ONE_FACTOR_EXTENDED_TRAINING_REPRODUCTION",
        "purpose": "Test undertraining as the first explanation for high-Nc profile degradation.",
        "one_factor_change": {"field": "epochs", "old": 400, "new": 800},
        "must_remain_identical": {
            "Stage2_source_sha256": STAGE2_SHA,
            "dataset_sha256": B2_DATASET_SHA,
            "conditioning": [
                "no", "nw", "swi", "sor", "mu_w", "mu_o", "phi",
                "tD", "xD_star", "Sw_star", "Nc"
            ],
            "param_dim": 11,
            "hidden": 64,
            "layers": 2,
            "optimizer": "Adam",
            "learning_rate": 1e-3,
            "logical_batch": 8192,
            "XPU_microbatch": 2048,
            "seed": 1337,
            "loss_weights": {
                "data": 1.0,
                "physics": 0.05,
                "injector_bc": 5.0,
                "tip_bc": 5.0,
                "anchor": 10.0,
                "monotonicity": 0.2,
                "shape": 0.0,
            },
            "Nc_grid": [0.0, 0.05, 0.10, 0.20, 0.30],
            "NX_TRAIN": 1601,
            "NX_REF": 3201,
            "n_fan": 64,
            "split_seed": 1337,
            "train_fraction": 0.8,
        },
        "initialization_policy": {
            "fresh_model_initialization_required": True,
            "warm_start_from_COMP_XPU_001_prohibited": True,
            "reason": "COMP-XPU-001 checkpoint lacks Adam optimizer state; warm-starting with a reset optimizer would add a second intervention.",
        },
        "evaluation_policy": {
            "same_source_native_split_reused": True,
            "split_independent_after_B2A": False,
            "split_role": "reproduction development diagnostic only; NOT OOD",
            "repeat_metrics": [
                "overall reproduction diagnostic MSE/RMSE/MAE/max error",
                "per-Nc diagnostic MAE/RMSE/max error",
                "full-domain fine-grid Godunov error",
                "front-excluded fine-grid Godunov error",
                "front-position error",
                "Nc=0 Stage-1 nesting diagnostics",
                "saturation bounds",
            ],
            "numeric_acceptance_threshold": None,
            "B3_automatic_authorization": False,
            "decision": (
                "After COMP-XPU-002 completes, compare descriptive trends against COMP-XPU-001. "
                "If high-Nc degradation materially persists, freeze a separate conditioning/loss study before B3; do not tune inside COMP-XPU-002."
            ),
        },
        "firewall": {
            "OOD_claim": False,
            "TOF": False,
            "architecture_change": False,
            "loss_weight_change": False,
            "dataset_change": False,
            "Nc_transform_change": False,
            "front_definition_change": False,
        },
    }
    PROTOCOL.write_text(json.dumps(protocol, indent=2), encoding="utf-8")

    handoff = (
        "# V16E-1B2B-XPU Execution Handoff\n\n"
        f"Authorized next experiment: **{NEW_EXPERIMENT_ID}**\n\n"
        "One-factor change only: **400 -> 800 epochs**.\n\n"
        "The new experiment must train from fresh initialization with the exact cached Stage-2 Godunov dataset and all other frozen settings unchanged.\n\n"
        "The existing COMP-XPU-001 checkpoint remains immutable and is comparison evidence only.\n\n"
        "The reused 80/20 reproduction split is now a development diagnostic set, not independent/OOD evidence.\n"
    )
    HANDOFF.write_text(handoff, encoding="utf-8")

    gates.update({
        "interpretation_written": INTERPRETATION.exists() and INTERPRETATION.stat().st_size > 0,
        "protocol_written": PROTOCOL.exists() and PROTOCOL.stat().st_size > 0,
        "handoff_written": HANDOFF.exists() and HANDOFF.stat().st_size > 0,
        "no_training": True,
        "one_factor_epochs_only": True,
        "fresh_initialization_required": True,
        "warm_start_prohibited": True,
        "B3_not_automatically_authorized": True,
        "no_OOD_claim": True,
        "no_TOF": True,
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2B_XPU_COMPRESSIBLE_EXTENDED_TRAINING_PROTOCOL_FROZEN_"
        "NC_PROFILE_DEGRADATION_NOT_FRONT_LOCALIZED_UNDERTRAINING_HYPOTHESIS_SELECTED_"
        "ONE_FACTOR_EPOCH_EXTENSION_400_TO_800_FRESH_INITIALIZATION_REQUIRED_"
        "DATASET_ARCHITECTURE_LOSSES_SEED_BATCH_AND_NC_TRANSFORM_UNCHANGED_"
        "REPRODUCTION_SPLIT_RECLASSIFIED_AS_DEVELOPMENT_DIAGNOSTIC_NO_OOD_NO_TOF_"
        "V16E_BLREP_COMP_XPU_002_TRAINING_AUTHORIZED_B3_NOT_YET_AUTHORIZED"
        if ok else
        "V16E1B2B_XPU_PROTOCOL_FREEZE_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone": "V16E-1B2B-XPU",
        "status": status,
        "authorized_next_experiment": NEW_EXPERIMENT_ID if ok else None,
        "training_authorized_next": bool(ok),
        "B3_authorized": False,
        "protocol_sha256": sha256(PROTOCOL),
        "interpretation_sha256": sha256(INTERPRETATION),
        "handoff_sha256": sha256(HANDOFF),
        "gates": {k: bool(v) for k, v in gates.items()},
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\nSTATUS")
    print(" ", status)
    print("\nHASHES")
    print("  Protocol      :", sha256(PROTOCOL))
    print("  Interpretation:", sha256(INTERPRETATION))
    print("  Handoff       :", sha256(HANDOFF))
    print("  Summary       :", sha256(SUMMARY))
    print("\nNEXT")
    print(" ", NEW_EXPERIMENT_ID, "— fresh 800-epoch Stage-2 XPU reproduction")

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
