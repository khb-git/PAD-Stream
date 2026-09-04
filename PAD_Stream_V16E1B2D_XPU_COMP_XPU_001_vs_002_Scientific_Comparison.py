#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2D-XPU
COMP-XPU-001 vs COMP-XPU-002 Scientific Comparison

Purpose
-------
Compare the frozen 400-epoch Stage-2 compressible reproduction against the
completed 800-epoch one-factor reproduction.

NO TRAINING.
NO OPTIMIZER.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

The comparison repeats the B2A diagnostic structure for COMP-XPU-002:
  * overall reproduction diagnostic metrics,
  * per-Nc holdout MAE/RMSE/max error,
  * full-domain fine-grid Godunov error,
  * front-excluded error,
  * front-position error,
  * Nc-response ratios.

It then compares those results with the frozen COMP-XPU-001/B2A evidence.
No new numerical acceptance threshold is invented.
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
MILESTONE = "V16E-1B2D-XPU"

# ---------------------------------------------------------------------
# Frozen Stage-2 source / B2C runner
# ---------------------------------------------------------------------

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

B2C_RUNNER = R / "PAD_Stream_V16E1B2C_XPU_COMP_XPU_002_800Epoch_Compressible_Reproduction.py"
B2C_RUNNER_SHA = "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18"

# ---------------------------------------------------------------------
# Shared frozen dataset
# ---------------------------------------------------------------------

DATASET = (
    R / "output" / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

# ---------------------------------------------------------------------
# COMP-XPU-001 / B2A baseline evidence
# ---------------------------------------------------------------------

B2_BASE_DIR = (
    R / "output" / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-001"
)

B2_BASE_CHECKPOINT = B2_BASE_DIR / "V16E_BLREP_COMP_XPU_001.pt"
B2_BASE_METRICS = B2_BASE_DIR / "V16E_BLREP_COMP_XPU_001_Metrics.json"
B2A_AUDIT = B2_BASE_DIR / "V16E_BLREP_COMP_XPU_001_Nc_Diagnostic_Audit.json"
B2A_SUMMARY = B2_BASE_DIR / "PAD_Stream_V16E1B2A_XPU_Summary.json"

B2_BASE_CHECKPOINT_SHA = "f2239f21603e01a2c80abbb18a787c6b0861959683d99d31261c495ad087f3d0"
B2_BASE_METRICS_SHA = "81fc2e7587f1005445f789d1e9b2e0eb7cbb8a0719a3b9768a692c9e6e124723"
B2A_AUDIT_SHA = "44906c63200587e0200b209720dd1e3950708e8089ee90fc8f1476b9a7b29045"
B2A_SUMMARY_SHA = "edadbdfcd83996860d92b556e067692100688d48c9aa5c139adc8b76ec4532ae"

# ---------------------------------------------------------------------
# COMP-XPU-002 final evidence
# ---------------------------------------------------------------------

B2C_DIR = (
    R / "output" / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-002"
)

B2C_PORT = B2C_DIR / "V16E_BLREP_COMP_XPU_002_Framework_Port_Protocol.json"
B2C_CHECKPOINT = B2C_DIR / "V16E_BLREP_COMP_XPU_002.pt"
B2C_CONFIG = B2C_DIR / "V16E_BLREP_COMP_XPU_002_Config.json"
B2C_HISTORY = B2C_DIR / "V16E_BLREP_COMP_XPU_002_Training_History.json"
B2C_METRICS = B2C_DIR / "V16E_BLREP_COMP_XPU_002_Metrics.json"
B2C_MANIFEST = B2C_DIR / "V16E_BLREP_COMP_XPU_002_Manifest.json"
B2C_SUMMARY = B2C_DIR / "PAD_Stream_V16E1B2C_XPU_Summary.json"
R2_AMENDMENT = B2C_DIR / "V16E_BLREP_COMP_XPU_002_R2_LowMemory_Adam_Execution_Amendment.json"
R2_RECORD = B2C_DIR / "V16E_BLREP_COMP_XPU_002_R2_Execution_Record.json"

B2C_PORT_SHA = "a11a6d527c2d566d690062a6e9d9a247bf9fabd994cc7bb72d5bbe995bfa8ca5"
B2C_CHECKPOINT_SHA = "fca205b1981fbbdf15424af8ac8174df88ff7addf99e718548319a81f87d271b"
B2C_CONFIG_SHA = "b80fa49b048c2680f2130f1cee451f55e50b86ccf49b6df89d1472d1f99c1cee"
B2C_HISTORY_SHA = "9bf5d1cf6726d4a97867f7f7a953bb1a2a49e62f553f3696673832672f976f9b"
B2C_METRICS_SHA = "f17fa9f5d6e5954119dc3e412fc01052b4cfb6173c157ac71ff1aa04b0a0385d"
B2C_MANIFEST_SHA = "3ab6abb7fe60ef5e6dcacfa3f543c65578a39fb64b0219357a658604edc1a48f"
B2C_SUMMARY_SHA = "8ede892568a1e21c989f5c2782a3f0696e00480a0d671771e6fead754a6b9788"
R2_AMENDMENT_SHA = "7fefa284d163de2f9825e31077226889cceea991e12af6a5e6b43d3e795a5ead"
R2_RECORD_SHA = "e2f2b0c22bfab49ff2d3aac2b46b3b341f5aeb7b69875a89c303e30a80e05788"

EXPECTED_B2C_STATUS = (
    "V16E1B2C_XPU_COMP_XPU_002_800_EPOCH_ONE_FACTOR_REPRODUCTION_COMPLETE_"
    "FRESH_INITIALIZATION_FROZEN_DATASET_ARCHITECTURE_LOSSES_SEED_BATCH_AND_NC_TRANSFORM_UNCHANGED_"
    "INTEL_XPU_EXECUTION_CHECKPOINT_AND_METRICS_SHA_BOUND_"
    "REPRODUCTION_DIAGNOSTICS_FINITE_SATURATION_BOUNDS_PASS_NO_OOD_NO_TOF_"
    "V16E1B2D_COMPARISON_INTERPRETATION_REQUIRED_B3_NOT_YET_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2D_XPU_COMPRESSIBLE_400_vs_800_COMPARISON"
)
OUT.mkdir(parents=True, exist_ok=True)

COMPARISON = OUT / "V16E1B2D_COMP_XPU_001_vs_002_Comparison.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2D_XPU_Summary.json"

NC_VALUES = [0.0, 0.05, 0.10, 0.20, 0.30]
SEED = 1337


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


def import_b2c_runner():
    spec = importlib.util.spec_from_file_location(
        "v16e1b2c_frozen_runner",
        B2C_RUNNER,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not import frozen B2C runner.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def aggregate_errors(err):
    e = np.abs(np.asarray(err).ravel())
    return {
        "mae": float(np.mean(e)),
        "rmse": float(np.sqrt(np.mean(e**2))),
        "max_abs_error": float(np.max(e)),
        "p95_abs_error": float(np.quantile(e, 0.95)),
        "p99_abs_error": float(np.quantile(e, 0.99)),
        "n": int(e.size),
    }


def pct_improvement(old, new):
    if old == 0:
        return None
    return float((old - new) / old * 100.0)


def per_nc_holdout(model, arrays, holdout_idx, device):
    xi, Sw, p11, tD, ai, at = arrays
    out = {}

    for nc in NC_VALUES:
        mask = np.isclose(p11[holdout_idx, 10], nc, atol=1e-7)
        ids = holdout_idx[mask]

        if len(ids) == 0:
            raise RuntimeError(f"No holdout profiles for Nc={nc}")

        pred_parts = []
        batch = 1024

        for i0 in range(0, len(ids), batch):
            sub = ids[i0:i0 + batch]
            with torch.no_grad():
                x = torch.from_numpy(xi[sub]).to(device)
                p = torch.from_numpy(p11[sub]).to(device)
                pred = model(x, p).cpu().numpy()
            pred_parts.append(pred)

        pred = np.concatenate(pred_parts, axis=0)
        err = pred - Sw[ids]

        out[f"{nc:.2f}"] = {
            "profile_count": int(len(ids)),
            **aggregate_errors(err),
        }

    return out


def source_case_diagnostic(model, M, p_case, nc, device):
    t_bt = M.breakthrough_time_days(p_case, Nc=nc)
    times = np.linspace(100.0, 0.95 * t_bt, 8)

    full_errors = []
    excluded_errors = []
    front_errors = []

    half_width = 5.0 / M.NX_REF * 3.0

    for t in times:
        r = M.predict_against_ref(
            model, p_case, float(t), nc, device
        )

        pred = np.interp(
            r["xD_true"],
            r["xD_pred"],
            r["Sw_pred"],
        )
        err = pred - r["Sw_true"]

        full_errors.append(err)

        mask = (
            np.abs(r["xD_true"] - r["xD_star_true"])
            > half_width
        )
        excluded_errors.append(err[mask])

        grid = np.linspace(
            p_case["swc"],
            1.0 - p_case["sor"],
            800,
        )
        _, fw = M.dfw_dsw_np(grid, p_case)
        Sw_star, _, _, _ = M.welge_tangent(
            grid, fw, p_case["swc"]
        )

        pred_front = M.godunov_front_from_profile(
            r["xD_pred"],
            r["Sw_pred"],
            Sw_star,
            p_case["swc"],
        )

        if np.isfinite(pred_front) and np.isfinite(r["xD_star_true"]):
            front_errors.append(
                float(pred_front - r["xD_star_true"])
            )

    fe = np.asarray(front_errors, dtype=float)

    return {
        "Nc": float(nc),
        "front_exclusion_half_width_xD": float(half_width),
        "full_domain": aggregate_errors(np.concatenate(full_errors)),
        "front_excluded": aggregate_errors(np.concatenate(excluded_errors)),
        "front_position": {
            "mean_signed_error_xD": float(np.mean(fe)),
            "mae_xD": float(np.mean(np.abs(fe))),
            "max_abs_error_xD": float(np.max(np.abs(fe))),
            "n": int(len(fe)),
        },
    }


def trend_ratio(records, metric):
    y0 = float(records["0.00"][metric])
    y3 = float(records["0.30"][metric])
    return float(y3 / max(y0, 1e-30))


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2D-XPU")
    print("COMP-XPU-001 vs COMP-XPU-002 Scientific Comparison")
    print("=" * 80)
    print("NO TRAINING — comparison only.\n")

    if SUMMARY.exists():
        raise RuntimeError("B2D summary already exists; refusing overwrite.")

    gates = {
        "Stage2_SHA_exact": exact(STAGE2, STAGE2_SHA),
        "B2C_runner_SHA_exact": exact(B2C_RUNNER, B2C_RUNNER_SHA),
        "dataset_SHA_exact": exact(DATASET, DATASET_SHA),

        "B2_base_checkpoint_SHA_exact": exact(B2_BASE_CHECKPOINT, B2_BASE_CHECKPOINT_SHA),
        "B2_base_metrics_SHA_exact": exact(B2_BASE_METRICS, B2_BASE_METRICS_SHA),
        "B2A_audit_SHA_exact": exact(B2A_AUDIT, B2A_AUDIT_SHA),
        "B2A_summary_SHA_exact": exact(B2A_SUMMARY, B2A_SUMMARY_SHA),

        "B2C_port_SHA_exact": exact(B2C_PORT, B2C_PORT_SHA),
        "B2C_checkpoint_SHA_exact": exact(B2C_CHECKPOINT, B2C_CHECKPOINT_SHA),
        "B2C_config_SHA_exact": exact(B2C_CONFIG, B2C_CONFIG_SHA),
        "B2C_history_SHA_exact": exact(B2C_HISTORY, B2C_HISTORY_SHA),
        "B2C_metrics_SHA_exact": exact(B2C_METRICS, B2C_METRICS_SHA),
        "B2C_manifest_SHA_exact": exact(B2C_MANIFEST, B2C_MANIFEST_SHA),
        "B2C_summary_SHA_exact": exact(B2C_SUMMARY, B2C_SUMMARY_SHA),
        "R2_amendment_SHA_exact": exact(R2_AMENDMENT, R2_AMENDMENT_SHA),
        "R2_record_SHA_exact": exact(R2_RECORD, R2_RECORD_SHA),
    }

    b2c_summary = read_json(B2C_SUMMARY)
    gates["B2C_status_exact"] = (
        b2c_summary.get("status") == EXPECTED_B2C_STATUS
    )
    gates["B2C_B3_false"] = b2c_summary.get("B3_authorized") is False
    gates["B2C_comparison_required"] = (
        b2c_summary.get("comparison_required_before_B3") is True
    )

    print("AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError("B2D blocked by artifact authority mismatch.")

    M = import_b2c_runner()

    if not torch.xpu.is_available():
        raise RuntimeError("Intel XPU unavailable for B2D evaluation.")

    device = torch.device("xpu")

    payload = torch.load(
        B2C_CHECKPOINT,
        map_location="cpu",
        weights_only=False,
    )

    model = M.CompressiblePIRNNXPU()
    model.load_state_dict(payload["model_state_dict"], strict=True)
    model.to(device)
    model.eval()

    gates["model_eval_mode"] = model.training is False
    gates["checkpoint_unchanged"] = sha256(B2C_CHECKPOINT) == B2C_CHECKPOINT_SHA

    d = np.load(DATASET)
    arrays = (
        d["xi"], d["Sw"], d["p11"],
        d["tD"], d["ai"], d["at"],
    )

    xi, Sw, p11, tD, ai, at = arrays

    rng = np.random.default_rng(SEED)
    idx = np.arange(len(xi))
    rng.shuffle(idx)
    n_train = int(0.8 * len(idx))
    holdout_idx = idx[n_train:]

    print("\nCOMP-XPU-002 PER-Nc HOLDOUT")
    new_holdout = per_nc_holdout(
        model, arrays, holdout_idx, device
    )
    for nc, vals in new_holdout.items():
        print(
            f"  Nc={nc} | MAE={vals['mae']:.6e} "
            f"| RMSE={vals['rmse']:.6e} "
            f"| max={vals['max_abs_error']:.6e}"
        )

    p1 = M.make_case(
        no=2.0, nw=2.0,
        swc=0.20, sor=0.20,
        mu_w=0.5, mu_o=0.7,
        phi=0.20,
    )
    p2 = M.make_case(
        no=3.0, nw=2.0,
        swc=0.15, sor=0.25,
        mu_w=6.0, mu_o=0.9,
        phi=0.25,
    )

    new_cases = {"case1": {}, "case2": {}}

    print("\nCOMP-XPU-002 FULL vs FRONT-EXCLUDED")
    for label, p_case in (("case1", p1), ("case2", p2)):
        for nc in NC_VALUES:
            rec = source_case_diagnostic(
                model, M, p_case, nc, device
            )
            new_cases[label][f"{nc:.2f}"] = rec

            print(
                f"  {label} Nc={nc:.2f} "
                f"| full={rec['full_domain']['mae']:.6e} "
                f"| excl={rec['front_excluded']['mae']:.6e} "
                f"| front={rec['front_position']['mae_xD']:.6e}"
            )

    old_metrics = read_json(B2_BASE_METRICS)
    new_metrics = read_json(B2C_METRICS)
    old_audit = read_json(B2A_AUDIT)

    old_overall = old_metrics["holdout"]
    new_overall = new_metrics["holdout"]

    old_holdout = old_audit["holdout_by_Nc"]
    old_cases = old_audit["case_results"]

    # Freeze direct comparisons.
    overall_compare = {}
    for metric in ("mse", "rmse", "mae", "max_abs_error"):
        old = float(old_overall[metric])
        new = float(new_overall[metric])
        overall_compare[metric] = {
            "COMP_XPU_001": old,
            "COMP_XPU_002": new,
            "percent_improvement_positive_is_better":
                pct_improvement(old, new),
        }

    per_nc_compare = {}
    for nc in [f"{x:.2f}" for x in NC_VALUES]:
        per_nc_compare[nc] = {}
        for metric in ("mae", "rmse", "max_abs_error"):
            old = float(old_holdout[nc][metric])
            new = float(new_holdout[nc][metric])
            per_nc_compare[nc][metric] = {
                "COMP_XPU_001": old,
                "COMP_XPU_002": new,
                "percent_improvement_positive_is_better":
                    pct_improvement(old, new),
            }

    case_compare = {"case1": {}, "case2": {}}
    for label in ("case1", "case2"):
        for nc in [f"{x:.2f}" for x in NC_VALUES]:
            case_compare[label][nc] = {
                "full_domain_mae": {
                    "COMP_XPU_001":
                        old_cases[label][nc]["full_domain"]["mae"],
                    "COMP_XPU_002":
                        new_cases[label][nc]["full_domain"]["mae"],
                    "percent_improvement_positive_is_better":
                        pct_improvement(
                            old_cases[label][nc]["full_domain"]["mae"],
                            new_cases[label][nc]["full_domain"]["mae"],
                        ),
                },
                "front_excluded_mae": {
                    "COMP_XPU_001":
                        old_cases[label][nc]["front_excluded"]["mae"],
                    "COMP_XPU_002":
                        new_cases[label][nc]["front_excluded"]["mae"],
                    "percent_improvement_positive_is_better":
                        pct_improvement(
                            old_cases[label][nc]["front_excluded"]["mae"],
                            new_cases[label][nc]["front_excluded"]["mae"],
                        ),
                },
                "front_position_mae_xD": {
                    "COMP_XPU_001":
                        old_cases[label][nc]["front_position"]["mae_xD"],
                    "COMP_XPU_002":
                        new_cases[label][nc]["front_position"]["mae_xD"],
                    "percent_improvement_positive_is_better":
                        pct_improvement(
                            old_cases[label][nc]["front_position"]["mae_xD"],
                            new_cases[label][nc]["front_position"]["mae_xD"],
                        ),
                },
            }

    old_holdout_ratio = trend_ratio(old_holdout, "mae")
    new_holdout_ratio = trend_ratio(new_holdout, "mae")

    old_case1_full = {
        nc: {"mae": old_cases["case1"][nc]["full_domain"]["mae"]}
        for nc in old_cases["case1"]
    }
    new_case1_full = {
        nc: {"mae": new_cases["case1"][nc]["full_domain"]["mae"]}
        for nc in new_cases["case1"]
    }

    old_case1_excl = {
        nc: {"mae": old_cases["case1"][nc]["front_excluded"]["mae"]}
        for nc in old_cases["case1"]
    }
    new_case1_excl = {
        nc: {"mae": new_cases["case1"][nc]["front_excluded"]["mae"]}
        for nc in new_cases["case1"]
    }

    old_case1_full_ratio = trend_ratio(old_case1_full, "mae")
    new_case1_full_ratio = trend_ratio(new_case1_full, "mae")
    old_case1_excl_ratio = trend_ratio(old_case1_excl, "mae")
    new_case1_excl_ratio = trend_ratio(new_case1_excl, "mae")

    ratios = {
        "holdout_Nc030_over_Nc000": {
            "COMP_XPU_001": old_holdout_ratio,
            "COMP_XPU_002": new_holdout_ratio,
            "percent_ratio_reduction_positive_is_flatter":
                pct_improvement(old_holdout_ratio, new_holdout_ratio),
        },
        "case1_full_domain_Nc030_over_Nc000": {
            "COMP_XPU_001": old_case1_full_ratio,
            "COMP_XPU_002": new_case1_full_ratio,
            "percent_ratio_reduction_positive_is_flatter":
                pct_improvement(old_case1_full_ratio, new_case1_full_ratio),
        },
        "case1_front_excluded_Nc030_over_Nc000": {
            "COMP_XPU_001": old_case1_excl_ratio,
            "COMP_XPU_002": new_case1_excl_ratio,
            "percent_ratio_reduction_positive_is_flatter":
                pct_improvement(old_case1_excl_ratio, new_case1_excl_ratio),
        },
    }

    comparison = {
        "milestone": MILESTONE,
        "classification":
            "NO_TRAINING_400_VS_800_STAGE2_SCIENTIFIC_COMPARISON",

        "experiment_1": {
            "id": "V16E-BLREP-COMP-XPU-001",
            "epochs": 400,
            "checkpoint_sha256": B2_BASE_CHECKPOINT_SHA,
            "B2A_audit_sha256": B2A_AUDIT_SHA,
        },

        "experiment_2": {
            "id": "V16E-BLREP-COMP-XPU-002",
            "epochs": 800,
            "checkpoint_sha256": B2C_CHECKPOINT_SHA,
            "R2_operational_amendment_sha256": R2_AMENDMENT_SHA,
            "scientific_hyperparameters_changed_vs_B2B":
                "epochs only; R2 foreach=False was an execution-memory implementation amendment",
        },

        "overall_comparison": overall_compare,
        "per_Nc_holdout_comparison": per_nc_compare,
        "case_comparison": case_compare,
        "Nc_response_ratios": ratios,

        "interpretation_policy":
            "No numeric pass/fail threshold is introduced. Determine whether "
            "extra training primarily improves absolute errors, whether the "
            "relative high-Nc degradation meaningfully changes, and whether "
            "front-excluded behavior supports or rejects undertraining as a "
            "sufficient explanation.",

        "B3_automatically_authorized": False,
        "no_training": True,
        "no_OOD": True,
        "no_TOF": True,
    }

    COMPARISON.write_text(
        json.dumps(comparison, indent=2),
        encoding="utf-8",
    )

    gates.update({
        "new_per_Nc_metrics_finite":
            all(
                finite(v[m])
                for v in new_holdout.values()
                for m in ("mae", "rmse", "max_abs_error")
            ),
        "new_case_metrics_finite":
            all(
                finite(rec["full_domain"]["mae"])
                and finite(rec["front_excluded"]["mae"])
                and finite(rec["front_position"]["mae_xD"])
                for case in new_cases.values()
                for rec in case.values()
            ),
        "comparison_written":
            COMPARISON.exists() and COMPARISON.stat().st_size > 0,
        "checkpoint_still_unchanged":
            sha256(B2C_CHECKPOINT) == B2C_CHECKPOINT_SHA,
        "no_training": True,
        "no_optimizer": True,
        "no_weight_update": True,
        "no_OOD": True,
        "no_TOF": True,
        "no_numeric_threshold": True,
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2D_XPU_COMP_XPU_001_VS_002_SCIENTIFIC_COMPARISON_COMPLETE_"
        "OVERALL_PER_NC_HOLDOUT_FULL_DOMAIN_FRONT_EXCLUDED_AND_FRONT_POSITION_TRENDS_FROZEN_"
        "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
        "B3_DECISION_REQUIRES_INTERPRETATION"
        if ok else
        "V16E1B2D_XPU_COMPARISON_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone": MILESTONE,
        "status": status,
        "comparison_sha256": sha256(COMPARISON),
        "B3_authorized": False,
        "B3_decision_requires_interpretation": True,
        "overall_RMSE_percent_improvement":
            overall_compare["rmse"]["percent_improvement_positive_is_better"],
        "overall_MAE_percent_improvement":
            overall_compare["mae"]["percent_improvement_positive_is_better"],
        "holdout_ratio_400": old_holdout_ratio,
        "holdout_ratio_800": new_holdout_ratio,
        "case1_full_ratio_400": old_case1_full_ratio,
        "case1_full_ratio_800": new_case1_full_ratio,
        "case1_front_excluded_ratio_400": old_case1_excl_ratio,
        "case1_front_excluded_ratio_800": new_case1_excl_ratio,
        "gates": {k: bool(v) for k, v in gates.items()},
    }

    SUMMARY.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\n400 vs 800 SUMMARY")
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
        f"{old_holdout_ratio:.4f}x -> {new_holdout_ratio:.4f}x"
    )
    print(
        "  Case1 full ratio        :",
        f"{old_case1_full_ratio:.4f}x -> {new_case1_full_ratio:.4f}x"
    )
    print(
        "  Case1 front-excl ratio  :",
        f"{old_case1_excl_ratio:.4f}x -> {new_case1_excl_ratio:.4f}x"
    )

    print("\nFINAL GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)
    print("\nHASHES")
    print("  Comparison:", sha256(COMPARISON))
    print("  Summary   :", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
