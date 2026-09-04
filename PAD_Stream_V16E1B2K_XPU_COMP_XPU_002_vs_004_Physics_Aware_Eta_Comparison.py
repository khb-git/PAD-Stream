#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2K-XPU
COMP-XPU-002 vs COMP-XPU-004 Scientific Comparison

Purpose
-------
Compare the frozen 800-epoch raw-Nc Stage-2 baseline
(V16E-BLREP-COMP-XPU-002) against the frozen 800-epoch physics-aware
eta-channel model (V16E-BLREP-COMP-XPU-004).

NO TRAINING.
NO OPTIMIZER.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

Frozen diagnostic structure
---------------------------
This comparison combines the previously frozen B2D/B2G/B2H diagnostics:

  * overall reproduction-development holdout metrics
  * per-Nc holdout MAE/RMSE/max error
  * per-Nc data/physics/total loss
  * Case 1 and Case 2 full-domain Godunov error
  * front-excluded error
  * front-position error
  * model-to-teacher Nc response gain
  * Nc=0.30 / Nc=0 response ratios
  * saturation bounds / finite prediction gates

No numerical pass/fail threshold is invented.
B3 is NOT automatically authorized by this script.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import math
import sys

import numpy as np
import torch


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2K-XPU"

# =============================================================================
# Frozen authorities
# =============================================================================

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

DATASET = (
    R / "output" / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

# Frozen base COMP-XPU-002 runner
BASE_RUNNER = (
    R
    / "PAD_Stream_V16E1B2C_XPU_COMP_XPU_002_800Epoch_Compressible_Reproduction.py"
)
BASE_RUNNER_SHA = "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18"

# B2G diagnostic source (per-Nc holdout + full/front/front-position)
B2G_SOURCE = (
    R
    / "PAD_Stream_V16E1B2G_XPU_COMP_XPU_002_vs_003_Nc_Conditioning_Comparison.py"
)
B2G_SOURCE_SHA = "18a8e63f0cc7de4c4e2093019c72b438f561bb2d66602c74b6e842bf13bd06aa"

# B2H diagnostic source (per-Nc losses + model-to-teacher response gain)
B2H_SOURCE = (
    R
    / "PAD_Stream_V16E1B2H_XPU_Nc_Conditioning_Response_Audit.py"
)
B2H_SOURCE_SHA = "6196f874a34414ae0db43c6c3253e9ad12755b959ac19d61e6bfe26327616987"

B2H_DIR = (
    R / "output"
    / "V16_E1B2H_XPU_NC_CONDITIONING_RESPONSE_AUDIT"
)
B2H_AUDIT = B2H_DIR / "V16E1B2H_Nc_Conditioning_Response_Audit.json"
B2H_SUMMARY = B2H_DIR / "PAD_Stream_V16E1B2H_XPU_Summary.json"

B2H_AUDIT_SHA = "e033f0e8b9e64729ef0469514e6c0909c2150c5290851648f98f5b8a0c60c8bc"
B2H_SUMMARY_SHA = "662ac29e5413d4761bbcf6234245e62bf11671f7a9412a33b8998fb8da10a48a"

# COMP-XPU-002 baseline
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

# COMP-XPU-004 / B2J
B2J_SOURCE = (
    R
    / "PAD_Stream_V16E1B2J_XPU_COMP_XPU_004_Physics_Aware_Nc_Coordinate_Channel_Reproduction.py"
)
B2J_SOURCE_SHA = "fcc4074863a46f6b8d356a01ff0b4b2182d0ffa3ebc9b3fd053e35282f897a4c"

COMP004_DIR = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-004"
)

COMP004_PORT = COMP004_DIR / "V16E_BLREP_COMP_XPU_004_Framework_Port_Protocol.json"
COMP004_CHECKPOINT = COMP004_DIR / "V16E_BLREP_COMP_XPU_004.pt"
COMP004_CONFIG = COMP004_DIR / "V16E_BLREP_COMP_XPU_004_Config.json"
COMP004_HISTORY = COMP004_DIR / "V16E_BLREP_COMP_XPU_004_Training_History.json"
COMP004_METRICS = COMP004_DIR / "V16E_BLREP_COMP_XPU_004_Metrics.json"
COMP004_MANIFEST = COMP004_DIR / "V16E_BLREP_COMP_XPU_004_Manifest.json"
COMP004_SUMMARY = COMP004_DIR / "PAD_Stream_V16E1B2J_XPU_Summary.json"

COMP004_PORT_SHA = "ca1d118061142103d8c0f1da2952dac8d8b3cc2997556b70c5738563847a0f6b"
COMP004_CHECKPOINT_SHA = "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69"
COMP004_CONFIG_SHA = "22588a6eddd0c12212b529b85e592d53844bd14b1dc5e163e3b7ce9a7318002a"
COMP004_HISTORY_SHA = "0b993558c1cd981be55d02412a91e58d3561fdd49435b3ae08a3f4aa29daf825"
COMP004_METRICS_SHA = "75a76341db626ee346c6a73b89524bf2721b1c46e75f4495fa72091378a9c14f"
COMP004_MANIFEST_SHA = "989d3aaca374b44a9f6f9d0a35b9b0ddf8a86b3665e5b58f9bbb4f97ad08add7"
COMP004_SUMMARY_SHA = "d4fc1de7a0257be90f2629e7e1469a30f2e7011d5586e32799f9c2f7338658b0"

EXPECTED_B2J_STATUS = (
    "V16E1B2J_XPU_COMP_XPU_004_PHYSICS_AWARE_NC_COORDINATE_CHANNEL_REPRODUCTION_COMPLETE_"
    "SEQUENCE_FEATURES_XI_PLUS_ETA_RAW_PHYSICAL_P11_UNCHANGED_NO_NC_SCALING_"
    "GODUNOV_TEACHER_PHYSICS_RESIDUAL_LOSSES_AND_DATASET_UNCHANGED_"
    "FRESH_800_EPOCH_INTEL_XPU_TRAINING_COMPLETE_CHECKPOINT_AND_METRICS_SHA_BOUND_"
    "DIAGNOSTICS_FINITE_SATURATION_BOUNDS_PASS_NO_OOD_NO_TOF_"
    "V16E1B2K_COMP_XPU_002_VS_004_COMPARISON_REQUIRED_B3_NOT_YET_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2K_XPU_COMPRESSIBLE_COMP002_vs_COMP004_COMPARISON"
)
OUT.mkdir(parents=True, exist_ok=True)

COMPARISON = OUT / "V16E1B2K_COMP_XPU_002_vs_004_Comparison.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2K_XPU_Summary.json"

NC_VALUES = [0.0, 0.05, 0.10, 0.20, 0.30]
SEED = 1337


# =============================================================================
# Helpers
# =============================================================================

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


def pct_improvement(old, new):
    old = float(old)
    new = float(new)
    if old == 0.0:
        return None
    return float((old - new) / old * 100.0)


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def response_ratio(records, metric):
    return float(
        records["0.30"][metric]
        / max(float(records["0.00"][metric]), 1e-30)
    )


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2K-XPU")
    print("COMP-XPU-002 vs COMP-XPU-004 Scientific Comparison")
    print("=" * 80)
    print("NO TRAINING — comparison only.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "B2K summary already exists; refusing overwrite."
        )

    gates = {
        "Stage2_SHA_exact":
            exact(STAGE2, STAGE2_SHA),
        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),
        "base_runner_SHA_exact":
            exact(BASE_RUNNER, BASE_RUNNER_SHA),

        "B2G_source_SHA_exact":
            exact(B2G_SOURCE, B2G_SOURCE_SHA),
        "B2H_source_SHA_exact":
            exact(B2H_SOURCE, B2H_SOURCE_SHA),
        "B2H_audit_SHA_exact":
            exact(B2H_AUDIT, B2H_AUDIT_SHA),
        "B2H_summary_SHA_exact":
            exact(B2H_SUMMARY, B2H_SUMMARY_SHA),

        "COMP002_checkpoint_SHA_exact":
            exact(COMP002_CHECKPOINT, COMP002_CHECKPOINT_SHA),
        "COMP002_metrics_SHA_exact":
            exact(COMP002_METRICS, COMP002_METRICS_SHA),
        "COMP002_manifest_SHA_exact":
            exact(COMP002_MANIFEST, COMP002_MANIFEST_SHA),
        "COMP002_summary_SHA_exact":
            exact(COMP002_SUMMARY, COMP002_SUMMARY_SHA),

        "B2J_source_SHA_exact":
            exact(B2J_SOURCE, B2J_SOURCE_SHA),
        "COMP004_port_SHA_exact":
            exact(COMP004_PORT, COMP004_PORT_SHA),
        "COMP004_checkpoint_SHA_exact":
            exact(COMP004_CHECKPOINT, COMP004_CHECKPOINT_SHA),
        "COMP004_config_SHA_exact":
            exact(COMP004_CONFIG, COMP004_CONFIG_SHA),
        "COMP004_history_SHA_exact":
            exact(COMP004_HISTORY, COMP004_HISTORY_SHA),
        "COMP004_metrics_SHA_exact":
            exact(COMP004_METRICS, COMP004_METRICS_SHA),
        "COMP004_manifest_SHA_exact":
            exact(COMP004_MANIFEST, COMP004_MANIFEST_SHA),
        "COMP004_summary_SHA_exact":
            exact(COMP004_SUMMARY, COMP004_SUMMARY_SHA),
    }

    b2j_summary = read_json(COMP004_SUMMARY) if COMP004_SUMMARY.exists() else {}

    gates.update({
        "B2J_status_exact":
            b2j_summary.get("status") == EXPECTED_B2J_STATUS,
        "B2J_B3_false":
            b2j_summary.get("B3_authorized") is False,
        "B2J_comparison_required":
            b2j_summary.get("comparison_required_before_B3") is True,
    })

    print("AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "B2K blocked by artifact authority mismatch."
        )

    # Reuse frozen diagnostic implementations.
    G = import_module(B2G_SOURCE, "v16e1b2g_diag")
    H = import_module(B2H_SOURCE, "v16e1b2h_diag")
    J = import_module(B2J_SOURCE, "v16e1b2j_comp004")

    M = J.import_base_runner()
    EtaModel = J.build_eta_model_class(M)

    if not torch.xpu.is_available():
        raise RuntimeError(
            "Intel XPU unavailable for B2K evaluation."
        )

    device = torch.device("xpu")

    # -------------------------------------------------------------------------
    # Load immutable models.
    # -------------------------------------------------------------------------

    p2 = torch.load(
        COMP002_CHECKPOINT,
        map_location="cpu",
        weights_only=False,
    )
    model2 = M.CompressiblePIRNNXPU()
    model2.load_state_dict(
        p2["model_state_dict"],
        strict=True,
    )
    model2.to(device)
    model2.eval()

    p4 = torch.load(
        COMP004_CHECKPOINT,
        map_location="cpu",
        weights_only=False,
    )
    model4 = EtaModel()
    model4.load_state_dict(
        p4["model_state_dict"],
        strict=True,
    )
    model4.to(device)
    model4.eval()

    gates.update({
        "COMP002_model_eval_mode":
            model2.training is False,
        "COMP004_model_eval_mode":
            model4.training is False,
        "COMP002_checkpoint_unchanged":
            sha256(COMP002_CHECKPOINT) == COMP002_CHECKPOINT_SHA,
        "COMP004_checkpoint_unchanged":
            sha256(COMP004_CHECKPOINT) == COMP004_CHECKPOINT_SHA,
        "COMP004_eta_channel_flag":
            p4.get("sequence_features") == ["xi", "eta"],
        "COMP004_raw_p11_unscaled_flag":
            p4.get("raw_p11_scaled") is False,
        "COMP004_physical_Nc_unchanged_flag":
            p4.get("physical_Nc_unchanged") is True,
        "COMP004_first_LSTM_input_width_13":
            int(p4.get("first_LSTM_input_width")) == 13,
    })

    # -------------------------------------------------------------------------
    # Exact frozen dataset / split.
    # -------------------------------------------------------------------------

    d = np.load(DATASET)
    arrays = (
        d["xi"],
        d["Sw"],
        d["p11"],
        d["tD"],
        d["ai"],
        d["at"],
    )

    xi, Sw, p11, tD, ai, at = arrays
    train_idx, holdout_idx = H.split_indices(len(xi))

    # -------------------------------------------------------------------------
    # Overall metrics from frozen artifacts.
    # -------------------------------------------------------------------------

    metrics2 = read_json(COMP002_METRICS)
    metrics4 = read_json(COMP004_METRICS)

    overall2 = metrics2["holdout"]
    overall4 = metrics4["holdout"]

    overall_compare = {}

    for metric in ("mse", "rmse", "mae", "max_abs_error"):
        old = float(overall2[metric])
        new = float(overall4[metric])

        overall_compare[metric] = {
            "COMP_XPU_002": old,
            "COMP_XPU_004": new,
            "percent_improvement_positive_is_better":
                pct_improvement(old, new),
        }

    # -------------------------------------------------------------------------
    # Per-Nc holdout error.
    # -------------------------------------------------------------------------

    print("\nPER-Nc HOLDOUT — COMP-XPU-002")
    hold2 = G.per_nc_holdout(
        model2,
        arrays,
        holdout_idx,
        device,
    )

    for nc, rec in hold2.items():
        print(
            f"  Nc={nc} | MAE={rec['mae']:.6e} "
            f"| RMSE={rec['rmse']:.6e} "
            f"| max={rec['max_abs_error']:.6e}"
        )

    print("\nPER-Nc HOLDOUT — COMP-XPU-004")
    hold4 = G.per_nc_holdout(
        model4,
        arrays,
        holdout_idx,
        device,
    )

    for nc, rec in hold4.items():
        print(
            f"  Nc={nc} | MAE={rec['mae']:.6e} "
            f"| RMSE={rec['rmse']:.6e} "
            f"| max={rec['max_abs_error']:.6e}"
        )

    per_nc_holdout_compare = {}

    for nc in [f"{x:.2f}" for x in NC_VALUES]:
        per_nc_holdout_compare[nc] = {}

        for metric in ("mae", "rmse", "max_abs_error"):
            old = float(hold2[nc][metric])
            new = float(hold4[nc][metric])

            per_nc_holdout_compare[nc][metric] = {
                "COMP_XPU_002": old,
                "COMP_XPU_004": new,
                "percent_improvement_positive_is_better":
                    pct_improvement(old, new),
            }

    # -------------------------------------------------------------------------
    # Per-Nc loss components.
    # -------------------------------------------------------------------------

    print("\nPER-Nc LOSS COMPONENTS — COMP-XPU-002")
    loss2 = H.per_nc_losses(
        M,
        model2,
        arrays,
        holdout_idx,
        device,
    )

    for nc, rec in loss2.items():
        print(
            f"  Nc={nc} | Data={rec['data']:.6e} "
            f"| Phys={rec['physics']:.6e} "
            f"| Total={rec['total']:.6e}"
        )

    print("\nPER-Nc LOSS COMPONENTS — COMP-XPU-004")
    loss4 = H.per_nc_losses(
        M,
        model4,
        arrays,
        holdout_idx,
        device,
    )

    for nc, rec in loss4.items():
        print(
            f"  Nc={nc} | Data={rec['data']:.6e} "
            f"| Phys={rec['physics']:.6e} "
            f"| Total={rec['total']:.6e}"
        )

    per_nc_loss_compare = {}

    for nc in [f"{x:.2f}" for x in NC_VALUES]:
        per_nc_loss_compare[nc] = {}

        for metric in ("data", "physics", "total"):
            old = float(loss2[nc][metric])
            new = float(loss4[nc][metric])

            per_nc_loss_compare[nc][metric] = {
                "COMP_XPU_002": old,
                "COMP_XPU_004": new,
                "percent_improvement_positive_is_better":
                    pct_improvement(old, new),
            }

    # -------------------------------------------------------------------------
    # Source cases: full/front-excluded/front-position.
    # -------------------------------------------------------------------------

    p_case1 = M.make_case(
        no=2.0,
        nw=2.0,
        swc=0.20,
        sor=0.20,
        mu_w=0.5,
        mu_o=0.7,
        phi=0.20,
    )

    p_case2 = M.make_case(
        no=3.0,
        nw=2.0,
        swc=0.15,
        sor=0.25,
        mu_w=6.0,
        mu_o=0.9,
        phi=0.25,
    )

    case2_diag = {
        "case1": {},
        "case2": {},
    }
    case4_diag = {
        "case1": {},
        "case2": {},
    }

    print("\nFULL vs FRONT-EXCLUDED — COMP-XPU-002")
    for label, p_case in (
        ("case1", p_case1),
        ("case2", p_case2),
    ):
        for nc in NC_VALUES:
            rec = G.source_case_diagnostic(
                model2,
                M,
                p_case,
                nc,
                device,
            )
            case2_diag[label][f"{nc:.2f}"] = rec

            print(
                f"  {label} Nc={nc:.2f} "
                f"| full={rec['full_domain']['mae']:.6e} "
                f"| excl={rec['front_excluded']['mae']:.6e} "
                f"| front={rec['front_position']['mae_xD']:.6e}"
            )

    print("\nFULL vs FRONT-EXCLUDED — COMP-XPU-004")
    for label, p_case in (
        ("case1", p_case1),
        ("case2", p_case2),
    ):
        for nc in NC_VALUES:
            rec = G.source_case_diagnostic(
                model4,
                M,
                p_case,
                nc,
                device,
            )
            case4_diag[label][f"{nc:.2f}"] = rec

            print(
                f"  {label} Nc={nc:.2f} "
                f"| full={rec['full_domain']['mae']:.6e} "
                f"| excl={rec['front_excluded']['mae']:.6e} "
                f"| front={rec['front_position']['mae_xD']:.6e}"
            )

    case_compare = {
        "case1": {},
        "case2": {},
    }

    for label in ("case1", "case2"):
        for nc in [f"{x:.2f}" for x in NC_VALUES]:
            old = case2_diag[label][nc]
            new = case4_diag[label][nc]

            case_compare[label][nc] = {
                "full_domain_mae": {
                    "COMP_XPU_002":
                        float(old["full_domain"]["mae"]),
                    "COMP_XPU_004":
                        float(new["full_domain"]["mae"]),
                    "percent_improvement_positive_is_better":
                        pct_improvement(
                            old["full_domain"]["mae"],
                            new["full_domain"]["mae"],
                        ),
                },
                "front_excluded_mae": {
                    "COMP_XPU_002":
                        float(old["front_excluded"]["mae"]),
                    "COMP_XPU_004":
                        float(new["front_excluded"]["mae"]),
                    "percent_improvement_positive_is_better":
                        pct_improvement(
                            old["front_excluded"]["mae"],
                            new["front_excluded"]["mae"],
                        ),
                },
                "front_position_mae_xD": {
                    "COMP_XPU_002":
                        float(old["front_position"]["mae_xD"]),
                    "COMP_XPU_004":
                        float(new["front_position"]["mae_xD"]),
                    "percent_improvement_positive_is_better":
                        pct_improvement(
                            old["front_position"]["mae_xD"],
                            new["front_position"]["mae_xD"],
                        ),
                },
            }

    # -------------------------------------------------------------------------
    # Model-to-teacher Nc response gains.
    # -------------------------------------------------------------------------

    print("\nNc RESPONSE GAIN — CASE 1")
    gain2_c1 = H.response_gain_for_case(
        M,
        model2,
        p_case1,
        device,
    )
    gain4_c1 = H.response_gain_for_case(
        M,
        model4,
        p_case1,
        device,
    )

    for key in gain2_c1:
        print(
            f"  {key} "
            f"| COMP002={gain2_c1[key]['model_to_teacher_response_gain']:.4f} "
            f"| COMP004={gain4_c1[key]['model_to_teacher_response_gain']:.4f} "
            f"| excl002={gain2_c1[key]['front_excluded_model_to_teacher_response_gain']:.4f} "
            f"| excl004={gain4_c1[key]['front_excluded_model_to_teacher_response_gain']:.4f}"
        )

    print("\nNc RESPONSE GAIN — CASE 2")
    gain2_c2 = H.response_gain_for_case(
        M,
        model2,
        p_case2,
        device,
    )
    gain4_c2 = H.response_gain_for_case(
        M,
        model4,
        p_case2,
        device,
    )

    for key in gain2_c2:
        print(
            f"  {key} "
            f"| COMP002={gain2_c2[key]['model_to_teacher_response_gain']:.4f} "
            f"| COMP004={gain4_c2[key]['model_to_teacher_response_gain']:.4f} "
            f"| excl002={gain2_c2[key]['front_excluded_model_to_teacher_response_gain']:.4f} "
            f"| excl004={gain4_c2[key]['front_excluded_model_to_teacher_response_gain']:.4f}"
        )

    gain_compare = {
        "case1": {},
        "case2": {},
    }

    for label, old_group, new_group in (
        ("case1", gain2_c1, gain4_c1),
        ("case2", gain2_c2, gain4_c2),
    ):
        for interval in old_group:
            gain_compare[label][interval] = {
                "full_response_gain": {
                    "COMP_XPU_002":
                        float(old_group[interval]["model_to_teacher_response_gain"]),
                    "COMP_XPU_004":
                        float(new_group[interval]["model_to_teacher_response_gain"]),
                    "distance_to_teacher_reference_1_COMP002":
                        abs(1.0 - float(
                            old_group[interval]["model_to_teacher_response_gain"]
                        )),
                    "distance_to_teacher_reference_1_COMP004":
                        abs(1.0 - float(
                            new_group[interval]["model_to_teacher_response_gain"]
                        )),
                },
                "front_excluded_response_gain": {
                    "COMP_XPU_002":
                        float(old_group[interval]["front_excluded_model_to_teacher_response_gain"]),
                    "COMP_XPU_004":
                        float(new_group[interval]["front_excluded_model_to_teacher_response_gain"]),
                    "distance_to_teacher_reference_1_COMP002":
                        abs(1.0 - float(
                            old_group[interval]["front_excluded_model_to_teacher_response_gain"]
                        )),
                    "distance_to_teacher_reference_1_COMP004":
                        abs(1.0 - float(
                            new_group[interval]["front_excluded_model_to_teacher_response_gain"]
                        )),
                },
            }

    # -------------------------------------------------------------------------
    # Nc=0.30 / Nc=0 response ratios.
    # -------------------------------------------------------------------------

    hold_ratio2 = response_ratio(hold2, "mae")
    hold_ratio4 = response_ratio(hold4, "mae")

    case1_full2 = {
        nc: {"mae": rec["full_domain"]["mae"]}
        for nc, rec in case2_diag["case1"].items()
    }
    case1_full4 = {
        nc: {"mae": rec["full_domain"]["mae"]}
        for nc, rec in case4_diag["case1"].items()
    }

    case1_excl2 = {
        nc: {"mae": rec["front_excluded"]["mae"]}
        for nc, rec in case2_diag["case1"].items()
    }
    case1_excl4 = {
        nc: {"mae": rec["front_excluded"]["mae"]}
        for nc, rec in case4_diag["case1"].items()
    }

    full_ratio2 = response_ratio(case1_full2, "mae")
    full_ratio4 = response_ratio(case1_full4, "mae")
    excl_ratio2 = response_ratio(case1_excl2, "mae")
    excl_ratio4 = response_ratio(case1_excl4, "mae")

    ratios = {
        "holdout_Nc030_over_Nc000": {
            "COMP_XPU_002": hold_ratio2,
            "COMP_XPU_004": hold_ratio4,
            "percent_ratio_reduction_positive_is_flatter":
                pct_improvement(hold_ratio2, hold_ratio4),
        },
        "case1_full_domain_Nc030_over_Nc000": {
            "COMP_XPU_002": full_ratio2,
            "COMP_XPU_004": full_ratio4,
            "percent_ratio_reduction_positive_is_flatter":
                pct_improvement(full_ratio2, full_ratio4),
        },
        "case1_front_excluded_Nc030_over_Nc000": {
            "COMP_XPU_002": excl_ratio2,
            "COMP_XPU_004": excl_ratio4,
            "percent_ratio_reduction_positive_is_flatter":
                pct_improvement(excl_ratio2, excl_ratio4),
        },
    }

    comparison = {
        "milestone":
            MILESTONE,

        "classification":
            "NO_TRAINING_COMP002_VS_COMP004_PHYSICS_AWARE_ETA_CHANNEL_COMPARISON",

        "experiment_1": {
            "id":
                "V16E-BLREP-COMP-XPU-002",
            "epochs":
                800,
            "sequence_features":
                ["xi"],
            "raw_conditioner":
                "physical 11-D p11",
            "checkpoint_sha256":
                COMP002_CHECKPOINT_SHA,
        },

        "experiment_2": {
            "id":
                "V16E-BLREP-COMP-XPU-004",
            "epochs":
                800,
            "sequence_features":
                ["xi", "eta"],
            "eta_definition":
                "y(xi*xD_star;Nc)/y(xD_star;Nc)",
            "raw_conditioner":
                "physical 11-D p11 unchanged",
            "Nc_scaling":
                False,
            "physical_Nc_changed":
                False,
            "checkpoint_sha256":
                COMP004_CHECKPOINT_SHA,
        },

        "overall_comparison":
            overall_compare,

        "per_Nc_holdout_comparison":
            per_nc_holdout_compare,

        "per_Nc_loss_comparison":
            per_nc_loss_compare,

        "case_comparison":
            case_compare,

        "model_to_teacher_response_gain_comparison":
            gain_compare,

        "Nc_response_ratios":
            ratios,

        "interpretation_policy":
            "No numeric pass/fail threshold is introduced. Determine whether "
            "the eta-channel improves absolute errors, per-Nc loss behavior, "
            "relative high-Nc response ratios, and model-to-teacher Nc response "
            "gains without degrading Stage-1 nesting or saturation bounds.",

        "B3_automatically_authorized":
            False,

        "no_training":
            True,
        "no_optimizer":
            True,
        "no_weight_update":
            True,
        "no_OOD":
            True,
        "no_TOF":
            True,
    }

    COMPARISON.write_text(
        json.dumps(
            comparison,
            indent=2,
        ),
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # Final gates.
    # -------------------------------------------------------------------------

    all_holdout_records = [
        rec
        for model_group in (hold2, hold4)
        for rec in model_group.values()
    ]

    all_loss_records = [
        rec
        for model_group in (loss2, loss4)
        for rec in model_group.values()
    ]

    all_case_records = [
        rec
        for model_cases in (case2_diag, case4_diag)
        for case_group in model_cases.values()
        for rec in case_group.values()
    ]

    all_gain_records = [
        rec
        for group in (gain2_c1, gain4_c1, gain2_c2, gain4_c2)
        for rec in group.values()
    ]

    gates.update({
        "all_per_Nc_holdout_metrics_finite":
            all(
                finite(rec[k])
                for rec in all_holdout_records
                for k in ("mae", "rmse", "max_abs_error")
            ),

        "all_per_Nc_losses_finite":
            all(
                finite(rec[k])
                for rec in all_loss_records
                for k in ("data", "physics", "total")
            ),

        "all_case_metrics_finite":
            all(
                finite(rec["full_domain"]["mae"])
                and finite(rec["front_excluded"]["mae"])
                and finite(rec["front_position"]["mae_xD"])
                for rec in all_case_records
            ),

        "all_response_gains_finite":
            all(
                finite(rec["model_to_teacher_response_gain"])
                and finite(rec["front_excluded_model_to_teacher_response_gain"])
                for rec in all_gain_records
            ),

        "comparison_written":
            COMPARISON.exists()
            and COMPARISON.stat().st_size > 0,

        "COMP002_checkpoint_still_unchanged":
            sha256(COMP002_CHECKPOINT)
            == COMP002_CHECKPOINT_SHA,

        "COMP004_checkpoint_still_unchanged":
            sha256(COMP004_CHECKPOINT)
            == COMP004_CHECKPOINT_SHA,

        "no_training":
            True,

        "no_optimizer":
            True,

        "no_weight_update":
            True,

        "no_OOD":
            True,

        "no_TOF":
            True,

        "no_numeric_threshold":
            True,
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2K_XPU_COMP_XPU_002_VS_004_PHYSICS_AWARE_ETA_CHANNEL_COMPARISON_COMPLETE_"
        "OVERALL_PER_NC_HOLDOUT_PER_NC_LOSSES_FULL_DOMAIN_FRONT_EXCLUDED_FRONT_POSITION_"
        "MODEL_TO_TEACHER_RESPONSE_GAINS_AND_NC_RESPONSE_RATIOS_FROZEN_"
        "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
        "B3_DECISION_REQUIRES_INTERPRETATION"
        if ok else
        "V16E1B2K_XPU_COMPARISON_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "comparison_sha256":
            sha256(COMPARISON),

        "B3_authorized":
            False,

        "B3_decision_requires_interpretation":
            True,

        "overall_RMSE_percent_improvement":
            overall_compare[
                "rmse"
            ][
                "percent_improvement_positive_is_better"
            ],

        "overall_MAE_percent_improvement":
            overall_compare[
                "mae"
            ][
                "percent_improvement_positive_is_better"
            ],

        "holdout_ratio_COMP002":
            hold_ratio2,

        "holdout_ratio_COMP004":
            hold_ratio4,

        "case1_full_ratio_COMP002":
            full_ratio2,

        "case1_full_ratio_COMP004":
            full_ratio4,

        "case1_front_excluded_ratio_COMP002":
            excl_ratio2,

        "case1_front_excluded_ratio_COMP004":
            excl_ratio4,

        "gates":
            {
                k: bool(v)
                for k, v
                in gates.items()
            },
    }

    SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nCOMP-XPU-002 vs COMP-XPU-004 SUMMARY")
    print(
        "  Overall RMSE improvement:",
        f"{summary['overall_RMSE_percent_improvement']:.3f}%"
    )
    print(
        "  Overall MAE improvement :",
        f"{summary['overall_MAE_percent_improvement']:.3f}%"
    )
    print(
        "  Holdout Nc0.30/Nc0 ratio:",
        f"{hold_ratio2:.4f}x -> {hold_ratio4:.4f}x"
    )
    print(
        "  Case1 full ratio        :",
        f"{full_ratio2:.4f}x -> {full_ratio4:.4f}x"
    )
    print(
        "  Case1 front-excl ratio  :",
        f"{excl_ratio2:.4f}x -> {excl_ratio4:.4f}x"
    )

    print("\nFINAL GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Comparison:", sha256(COMPARISON))
    print("  Summary   :", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
