#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2A-XPU
Compressible BL Nc-Response Diagnostic Audit

Purpose
-------
Diagnose the Stage-2 compressible reproduction WITHOUT retraining.

The frozen Stage-2 source states that MAE should remain approximately flat
across Nc and that a rising trend may indicate underweighted or undertrained
Nc conditioning. The completed V16E-1B2-XPU run passed all preregistered
finite/bounds/artifact gates but showed increasing Case-1 MAE at high Nc.

This audit determines whether that increase is:
  1. primarily localized to the thin numerical shock/front zone, or
  2. distributed through the fan/profile.

No new numerical acceptance threshold is invented here.

NO TRAINING.
NO OPTIMIZER.
NO WEIGHT UPDATE.
NO TOF.
NO OOD.
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
EXPERIMENT_ID = "V16E-BLREP-COMP-XPU-001"
MILESTONE = "V16E-1B2A-XPU"

RUNNER = R / "PAD_Stream_V16E1B2_XPU_Final_Compressible_BL_PIRNN_Native_Coordinate_Reproduction.py"
RUNNER_SHA = "bec3cb8366fa46b18f424f6434123438326e92896ff0dbac018a07cd7403c7ee"

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

OUT = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / EXPERIMENT_ID
)

DATASET = (
    R / "output"
    / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

PORT_PROTOCOL = OUT / "V16E_BLREP_COMP_XPU_001_Framework_Port_Protocol.json"
CHECKPOINT = OUT / "V16E_BLREP_COMP_XPU_001.pt"
CONFIG = OUT / "V16E_BLREP_COMP_XPU_001_Config.json"
HISTORY = OUT / "V16E_BLREP_COMP_XPU_001_Training_History.json"
METRICS = OUT / "V16E_BLREP_COMP_XPU_001_Metrics.json"
MANIFEST = OUT / "V16E_BLREP_COMP_XPU_001_Manifest.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2_XPU_Summary.json"

PORT_PROTOCOL_SHA = "28cf1fdc7cc1faa3f2183eecc137c6a547c1a593cb7348baaa786f24c1a4ff5b"
CHECKPOINT_SHA = "f2239f21603e01a2c80abbb18a787c6b0861959683d99d31261c495ad087f3d0"
CONFIG_SHA = "40ecaaf0876940b4ea5a6158cd6628df452b993e45821773fa9a82cb463d0e5c"
HISTORY_SHA = "3ad1bb77c7b65dcba4db9206b3ffa77f53a10c5f7ba268a065cf23376ea00d7d"
METRICS_SHA = "81fc2e7587f1005445f789d1e9b2e0eb7cbb8a0719a3b9768a692c9e6e124723"
MANIFEST_SHA = "669bdf4f0139e2032718574c7648427c39eb084e87b532ab07370df183178368"
SUMMARY_SHA = "e4a6294064f2d3d31cba614e223b9d7810577f7407d429eddf6c5ddbace474af"

EXPECTED_STATUS = (
    "V16E1B2_XPU_FINAL_COMPRESSIBLE_BL_PI_RNN_"
    "FRAMEWORK_EQUIVALENT_NATIVE_COORDINATE_REPRODUCTION_COMPLETE_"
    "CONSERVATIVE_GODUNOV_TEACHER_BOUND_"
    "NC_CONDITIONING_AND_TRAVEL_TIME_RESIDUAL_CERTIFIED_"
    "INTEL_XPU_EXECUTION_CONFIRMED_NEW_CHECKPOINT_SHA_BOUND_"
    "SOURCE_NATIVE_HOLDOUT_CASE_DIAGNOSTICS_AND_NC_SWEEP_FINITE_"
    "SATURATION_BOUNDS_PASS_STAGE1_NC0_NESTING_EVALUATED_"
    "NO_OOD_NO_TOF_"
    "V16E1B3_XPU_CAPILLARY_PORT_AUTHORIZED"
)

AUDIT = OUT / "V16E_BLREP_COMP_XPU_001_Nc_Diagnostic_Audit.json"
AUDIT_SUMMARY = OUT / "PAD_Stream_V16E1B2A_XPU_Summary.json"

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


def import_runner():
    spec = importlib.util.spec_from_file_location("v16e1b2_xpu_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not import frozen Stage-2 XPU runner.")
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


def per_nc_holdout(model, arrays, holdout_idx, device):
    xi, Sw, p11, tD, ai, at = arrays
    out = {}

    for nc in NC_VALUES:
        mask = np.isclose(p11[holdout_idx, 10], nc, atol=1e-7)
        ids = holdout_idx[mask]

        if len(ids) == 0:
            raise RuntimeError(f"No holdout profiles found for Nc={nc}")

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
    """
    Compute both full-domain and source-convention front-excluded error.

    The frozen Stage-2 source uses a thin-front exclusion in its optional
    side-by-side:
        |xD - xD_star| > (5/NX_REF)*3
    """
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
        if np.any(mask):
            excluded_errors.append(err[mask])

        # Estimate predicted front from the reconstructed profile using the same
        # Stage-2 mid-jump definition.
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

    full = aggregate_errors(np.concatenate(full_errors))
    excluded = aggregate_errors(np.concatenate(excluded_errors))

    fe = np.asarray(front_errors, dtype=float)

    return {
        "Nc": float(nc),
        "front_exclusion_half_width_xD": float(half_width),
        "full_domain": full,
        "front_excluded": excluded,
        "front_position": {
            "mean_signed_error_xD": float(np.mean(fe)),
            "mae_xD": float(np.mean(np.abs(fe))),
            "max_abs_error_xD": float(np.max(np.abs(fe))),
            "n": int(len(fe)),
        },
    }


def trend_summary(values_by_nc, metric_key):
    xs = np.array(NC_VALUES, dtype=float)
    ys = np.array(
        [values_by_nc[f"{x:.2f}"][metric_key] for x in xs],
        dtype=float,
    )

    slope = float(np.polyfit(xs, ys, 1)[0])
    ratio = float(ys[-1] / max(ys[0], 1e-30))

    return {
        "Nc": xs.tolist(),
        metric_key: ys.tolist(),
        "linear_slope_per_Nc": slope,
        "Nc030_to_Nc000_ratio": ratio,
        "minimum_value": float(np.min(ys)),
        "maximum_value": float(np.max(ys)),
    }


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2A-XPU")
    print("Compressible BL Nc-Response Diagnostic Audit")
    print("=" * 80)
    print("NO TRAINING — diagnostic evaluation only.\n")

    if AUDIT_SUMMARY.exists():
        raise RuntimeError("Audit summary already exists; refusing overwrite.")

    gates = {
        "runner_SHA_exact": exact(RUNNER, RUNNER_SHA),
        "Stage2_SHA_exact": exact(STAGE2, STAGE2_SHA),
        "dataset_SHA_exact": exact(DATASET, DATASET_SHA),
        "port_protocol_SHA_exact": exact(PORT_PROTOCOL, PORT_PROTOCOL_SHA),
        "checkpoint_SHA_exact": exact(CHECKPOINT, CHECKPOINT_SHA),
        "config_SHA_exact": exact(CONFIG, CONFIG_SHA),
        "history_SHA_exact": exact(HISTORY, HISTORY_SHA),
        "metrics_SHA_exact": exact(METRICS, METRICS_SHA),
        "manifest_SHA_exact": exact(MANIFEST, MANIFEST_SHA),
        "summary_SHA_exact": exact(SUMMARY, SUMMARY_SHA),
    }

    summary = read_json(SUMMARY) if SUMMARY.exists() else {}
    gates["status_exact"] = summary.get("status") == EXPECTED_STATUS

    print("AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError("V16E-1B2A blocked by artifact authority mismatch.")

    M = import_runner()

    print("\nRUNTIME")
    print("  PyTorch:", torch.__version__)
    print("  XPU available:", torch.xpu.is_available())

    if not torch.xpu.is_available():
        raise RuntimeError("XPU unavailable.")

    device = torch.device("xpu")

    payload = torch.load(
        CHECKPOINT,
        map_location="cpu",
        weights_only=False,
    )

    model = M.CompressiblePIRNNXPU()
    model.load_state_dict(payload["model_state_dict"], strict=True)
    model.to(device)
    model.eval()

    gates["model_eval_mode"] = model.training is False
    gates["checkpoint_unchanged_after_load"] = sha256(CHECKPOINT) == CHECKPOINT_SHA

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

    print("\nPER-Nc SOURCE-NATIVE HOLDOUT")
    holdout_by_nc = per_nc_holdout(
        model, arrays, holdout_idx, device
    )

    for nc, vals in holdout_by_nc.items():
        print(
            f"  Nc={nc} | N={vals['profile_count']:4d} "
            f"| MAE={vals['mae']:.6e} "
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

    case_results = {
        "case1": {},
        "case2": {},
    }

    print("\nFULL vs FRONT-EXCLUDED FINE-GRID GODUNOV ERRORS")

    for label, p_case in [("case1", p1), ("case2", p2)]:
        for nc in NC_VALUES:
            rec = source_case_diagnostic(
                model, M, p_case, nc, device
            )
            case_results[label][f"{nc:.2f}"] = rec

            print(
                f"  {label} Nc={nc:.2f} "
                f"| full MAE={rec['full_domain']['mae']:.6e} "
                f"| excl-front MAE={rec['front_excluded']['mae']:.6e} "
                f"| front MAE(xD)={rec['front_position']['mae_xD']:.6e}"
            )

    holdout_trend = trend_summary(
        holdout_by_nc,
        "mae",
    )

    case1_full_simple = {
        nc: {
            "mae": case_results["case1"][nc]["full_domain"]["mae"]
        }
        for nc in case_results["case1"]
    }
    case1_excl_simple = {
        nc: {
            "mae": case_results["case1"][nc]["front_excluded"]["mae"]
        }
        for nc in case_results["case1"]
    }

    case1_full_trend = trend_summary(
        case1_full_simple,
        "mae",
    )
    case1_excluded_trend = trend_summary(
        case1_excl_simple,
        "mae",
    )

    # Descriptive interpretation only; no threshold-driven pass/fail.
    audit = {
        "milestone": MILESTONE,
        "experiment_id": EXPERIMENT_ID,
        "classification": "NO_TRAINING_SCIENTIFIC_DIAGNOSTIC_AUDIT",

        "question":
            "Is the observed high-Nc error increase mainly a numerical-front "
            "localization effect or a broader fan/profile degradation?",

        "source_diagnostic_basis":
            "Stage-2 source says Nc sweep MAE should stay flat; rising trend "
            "may indicate Nc conditioning is underweighted or undertrained.",

        "front_exclusion_convention":
            "|xD-xD_star| > (5/NX_REF)*3, matching the frozen Stage-2 "
            "optional side-by-side diagnostic.",

        "holdout_by_Nc": holdout_by_nc,
        "case_results": case_results,

        "trends": {
            "holdout_mae": holdout_trend,
            "case1_full_domain_mae": case1_full_trend,
            "case1_front_excluded_mae": case1_excluded_trend,
        },

        "decision_policy":
            "No new numerical threshold is used. Review the relative behavior "
            "of full-domain, front-excluded, front-position, and holdout trends "
            "before authorizing any retraining or V16E-1B3 continuation.",

        "training_executed": False,
        "optimizer_created": False,
        "weights_modified": False,
        "TOF_used": False,
        "OOD_used": False,
    }

    AUDIT.write_text(
        json.dumps(audit, indent=2),
        encoding="utf-8",
    )

    gates.update({
        "all_holdout_Nc_metrics_finite": all(
            all(
                finite(vals[k])
                for k in ("mae", "rmse", "max_abs_error")
            )
            for vals in holdout_by_nc.values()
        ),
        "all_case_metrics_finite": all(
            finite(rec["full_domain"]["mae"])
            and finite(rec["front_excluded"]["mae"])
            and finite(rec["front_position"]["mae_xD"])
            for case in case_results.values()
            for rec in case.values()
        ),
        "audit_written": AUDIT.exists() and AUDIT.stat().st_size > 0,
        "checkpoint_still_unchanged": sha256(CHECKPOINT) == CHECKPOINT_SHA,
        "no_training": True,
        "no_optimizer": True,
        "no_weight_update": True,
        "no_TOF": True,
        "no_OOD": True,
        "no_new_numeric_threshold": True,
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2A_XPU_COMPRESSIBLE_NC_RESPONSE_DIAGNOSTIC_AUDIT_COMPLETE_"
        "PER_NC_HOLDOUT_FULL_DOMAIN_FRONT_EXCLUDED_AND_FRONT_POSITION_METRICS_FROZEN_"
        "NO_TRAINING_NO_WEIGHT_CHANGE_B3_DECISION_REQUIRES_INTERPRETATION"
        if ok else
        "V16E1B2A_XPU_DIAGNOSTIC_AUDIT_COMPLETED_WITH_GATE_FAILURE"
    )

    out_summary = {
        "milestone": MILESTONE,
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "checkpoint_sha256": CHECKPOINT_SHA,
        "audit_sha256": sha256(AUDIT),
        "training_executed": False,
        "weights_modified": False,
        "B3_automatically_authorized_by_this_audit": False,
        "next":
            "Interpret V16E-1B2A diagnostics and decide whether Stage-2 is "
            "accepted as reproduced or requires a prospectively frozen retraining protocol.",
        "gates": {k: bool(v) for k, v in gates.items()},
    }

    AUDIT_SUMMARY.write_text(
        json.dumps(out_summary, indent=2),
        encoding="utf-8",
    )

    print("\nTREND SUMMARY")
    print(
        "  Holdout MAE Nc0.30/Nc0.00:",
        f"{holdout_trend['Nc030_to_Nc000_ratio']:.4f}x",
    )
    print(
        "  Case1 full-domain MAE ratio:",
        f"{case1_full_trend['Nc030_to_Nc000_ratio']:.4f}x",
    )
    print(
        "  Case1 front-excluded MAE ratio:",
        f"{case1_excluded_trend['Nc030_to_Nc000_ratio']:.4f}x",
    )

    print("\nFINAL GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Checkpoint:", sha256(CHECKPOINT))
    print("  Audit     :", sha256(AUDIT))
    print("  Summary   :", sha256(AUDIT_SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
