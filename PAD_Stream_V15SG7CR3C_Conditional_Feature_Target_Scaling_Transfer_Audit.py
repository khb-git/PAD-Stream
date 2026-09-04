from __future__ import annotations

from pathlib import Path
import argparse
import csv
import importlib.util
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R3C
# Conditional Feature / Target-Scaling Transfer Audit
#
# DIAGNOSTIC-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO ARCHITECTURE CHANGE.
# NO SG6 STREAMLINE GEOMETRY CHANGE.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# SG7C-R3B established:
#
#   MARGINAL_TIME_DISTRIBUTION_SHIFT_WITHOUT_DENSITY_ERROR_LINK
#
# The normalized-time distribution differs strongly between canonical training
# and SGSim deployment, but canonical support density itself does not explain
# the residual error.
#
# R3C therefore audits whether the mismatch comes from:
#
#   1. conditional-feature semantics,
#   2. feature scaling,
#   3. target saturation scaling/range,
#   4. interpolation of the canonical target manifold into deployment inputs,
#   5. or the frozen PI-RNN approximation itself.
#
# The central test is:
#
#   Given the deployment (xi, normalized-tD) input, reconstruct the canonical
#   target by interpolating the authoritative canonical dataset in normalized
#   time, then compare:
#
#       canonical-interpolated target  vs  SG7A deployment truth
#
# If these agree closely, feature semantics and target scaling are consistent,
# and the remaining residual belongs to frozen-model transfer/calibration
# rather than the target definition.
# =============================================================================


ROOT = Path(__file__).resolve().parent

SG7CR3B_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3B"
    / "PAD_Stream_V15SG7CR3B_Summary.json"
)

SG7CR3A_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3A"
    / "V15SG7CR3A_Coordinate_Audit.npz"
)

SG7CR_DEPLOYMENT = (
    ROOT / "output" / "V15_SG7CR"
    / "SG7CR_FRONT_AWARE_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"
)

BASE_SOURCE = (
    ROOT / "PAD_Stream_V15SG7B6D_Advective_Flux_Refinement.py"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3C"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_TABLE = OUTPUT_DIR / "V15SG7CR3C_Feature_Semantics.csv"
TARGET_TABLE = OUTPUT_DIR / "V15SG7CR3C_Target_Scaling_Audit.csv"
INTERP_TABLE = OUTPUT_DIR / "V15SG7CR3C_Canonical_Interpolation_Metrics.csv"
TIME_TABLE = OUTPUT_DIR / "V15SG7CR3C_Interpolation_By_Time.csv"
TOF_TABLE = OUTPUT_DIR / "V15SG7CR3C_Interpolation_By_TOF_Band.csv"
NUMERICAL_FILE = OUTPUT_DIR / "V15SG7CR3C_Feature_Target_Audit.npz"
SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG7CR3C_Summary.json"


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def save_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def import_module(path: Path, name: str):
    if not path.exists():
        raise FileNotFoundError(f"Missing source module:\n{path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import module:\n{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_key(db, aliases, description):
    for key in aliases:
        if key in db:
            return key
    raise KeyError(
        f"Could not identify {description}.\n"
        f"Aliases: {aliases}\n"
        f"Available keys: {list(db.keys())}"
    )


def profile_time_feature(X):
    X = np.asarray(X, dtype=float)
    if X.ndim != 3 or X.shape[-1] < 2:
        raise RuntimeError(f"Unexpected canonical input shape: {X.shape}")

    # Canonical sequence convention: feature 0 = xi, feature 1 = normalized tD.
    time_feature = X[:, :, 1]

    within_profile_span = np.max(time_feature, axis=1) - np.min(time_feature, axis=1)

    return (
        np.mean(time_feature, axis=1),
        within_profile_span,
    )


def prepare_canonical_profiles(dataset):
    blocks = []

    for split in ["train", "val", "test"]:
        X = np.asarray(dataset[f"X_{split}"], dtype=float)
        Y = np.asarray(dataset[f"Y_{split}"], dtype=float)

        if Y.ndim == 3:
            Y = Y[:, :, 0]

        tnorm, span = profile_time_feature(X)

        blocks.append((split, X, Y, tnorm, span))

    records = []

    for split, X, Y, tnorm, span in blocks:
        for i in range(X.shape[0]):
            records.append({
                "split": split,
                "tnorm": float(tnorm[i]),
                "span": float(span[i]),
                "xi": np.asarray(X[i, :, 0], dtype=float),
                "target": np.asarray(Y[i], dtype=float),
            })

    records.sort(key=lambda item: item["tnorm"])

    # If duplicate time profiles exist across splits, average them.
    unique_times = []
    unique_targets = []
    canonical_xi = None

    grouped = {}

    for item in records:
        key = round(item["tnorm"], 12)
        grouped.setdefault(key, []).append(item)

    for key in sorted(grouped.keys()):
        group = grouped[key]

        if canonical_xi is None:
            canonical_xi = group[0]["xi"]

        for item in group:
            if not np.allclose(item["xi"], canonical_xi, atol=1e-12, rtol=0.0):
                raise RuntimeError(
                    "Canonical xi grid changes across profiles; "
                    "simple time interpolation is not valid."
                )

        unique_times.append(float(np.mean([item["tnorm"] for item in group])))
        unique_targets.append(
            np.mean(
                np.stack([item["target"] for item in group], axis=0),
                axis=0,
            )
        )

    return {
        "records": records,
        "times": np.asarray(unique_times, dtype=float),
        "targets": np.asarray(unique_targets, dtype=float),
        "xi": np.asarray(canonical_xi, dtype=float),
        "max_within_profile_time_span": max(item["span"] for item in records),
    }


def interpolate_targets(time_grid, target_grid, query_times):
    time_grid = np.asarray(time_grid, dtype=float)
    target_grid = np.asarray(target_grid, dtype=float)
    query_times = np.asarray(query_times, dtype=float)

    if np.any(np.diff(time_grid) <= 0.0):
        raise RuntimeError("Canonical normalized-time grid must be strictly increasing.")

    out = np.empty((len(query_times), target_grid.shape[1]), dtype=float)

    for j in range(target_grid.shape[1]):
        out[:, j] = np.interp(
            query_times,
            time_grid,
            target_grid[:, j],
        )

    return out


def stat(arr, fn):
    arr = np.asarray(arr, dtype=float)
    return float(fn(arr))


def main():

    parser = argparse.ArgumentParser(
        description="PAD-Stream V15-SG7C-R3C conditional-feature / target-scaling audit."
    )
    args = parser.parse_args()

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3C")
    print("Conditional Feature / Target-Scaling Transfer Audit")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO MODEL PARAMETERS WILL BE CHANGED.")
    print("NO ARCHITECTURE CHANGE WILL BE MADE.")
    print("NO DEPLOYMENT FEATURE CONVENTION WILL BE CHANGED.")
    print("NO TARGET SCALING WILL BE CHANGED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for path in [
        SG7CR3B_SUMMARY,
        SG7CR3A_NUMERICAL,
        SG7CR_DEPLOYMENT,
        BASE_SOURCE,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing SG7C-R3C prerequisite:\n{path}")

    r3b = load_json(SG7CR3B_SUMMARY)

    if r3b.get("diagnosis") != "MARGINAL_TIME_DISTRIBUTION_SHIFT_WITHOUT_DENSITY_ERROR_LINK":
        raise RuntimeError(
            "SG7C-R3C requires SG7C-R3B diagnosis:\n"
            "MARGINAL_TIME_DISTRIBUTION_SHIFT_WITHOUT_DENSITY_ERROR_LINK"
        )

    base = import_module(
        BASE_SOURCE,
        "pad_stream_sg7b6d_for_sg7cr3c",
    )

    dataset = base.load_dataset()
    canonical = prepare_canonical_profiles(dataset)

    r3a_db = np.load(SG7CR3A_NUMERICAL, allow_pickle=True)
    sg7cr = np.load(SG7CR_DEPLOYMENT, allow_pickle=True)

    deployment_xi = np.asarray(
        r3a_db[
            find_key(r3a_db, ["xi"], "deployment xi")
        ],
        dtype=float,
    )

    normalized_input = np.asarray(
        r3a_db[
            find_key(r3a_db, ["normalized_input"], "deployment normalized time")
        ],
        dtype=float,
    )

    tau_end_days = np.asarray(
        r3a_db[
            find_key(r3a_db, ["tau_end_days"], "terminal TOF")
        ],
        dtype=float,
    )

    times_days = np.asarray(
        r3a_db[
            find_key(r3a_db, ["times_days"], "deployment times")
        ],
        dtype=float,
    )

    pirnn = np.asarray(
        sg7cr[
            find_key(
                sg7cr,
                ["PI_RNN_saturation", "pirnn_saturation", "predicted_saturation"],
                "PI-RNN deployment saturation",
            )
        ],
        dtype=float,
    )

    truth = np.asarray(
        sg7cr[
            find_key(
                sg7cr,
                ["SG7A_saturation", "truth_saturation", "reference_saturation"],
                "SG7A deployment truth",
            )
        ],
        dtype=float,
    )

    n_times, n_streamlines, n_nodes = truth.shape

    if len(deployment_xi) != n_nodes:
        raise RuntimeError("Deployment xi does not match SG7C-R node count.")

    # -------------------------------------------------------------------------
    # Feature semantics
    # -------------------------------------------------------------------------

    canonical_xi = canonical["xi"]
    canonical_times = canonical["times"]
    canonical_targets = canonical["targets"]

    xi_match = bool(
        np.allclose(canonical_xi, deployment_xi, atol=1e-10, rtol=0.0)
    )

    canonical_time_profile_constant = bool(
        canonical["max_within_profile_time_span"] <= 1.0e-12
    )

    deployment_feature_min = float(np.min(normalized_input))
    deployment_feature_max = float(np.max(normalized_input))

    canonical_feature_min = float(np.min(canonical_times))
    canonical_feature_max = float(np.max(canonical_times))

    deployment_inside_canonical_range = bool(
        deployment_feature_min >= canonical_feature_min - 1e-12
        and deployment_feature_max <= canonical_feature_max + 1e-12
    )

    feature_rows = [
        {
            "feature": "xi",
            "canonical_min": float(np.min(canonical_xi)),
            "canonical_max": float(np.max(canonical_xi)),
            "deployment_min": float(np.min(deployment_xi)),
            "deployment_max": float(np.max(deployment_xi)),
            "semantic_check": "same node coordinate",
            "pass": xi_match,
        },
        {
            "feature": "normalized_tD",
            "canonical_min": canonical_feature_min,
            "canonical_max": canonical_feature_max,
            "deployment_min": deployment_feature_min,
            "deployment_max": deployment_feature_max,
            "semantic_check": "constant within sequence profile",
            "pass": canonical_time_profile_constant,
        },
        {
            "feature": "normalized_tD_domain",
            "canonical_min": canonical_feature_min,
            "canonical_max": canonical_feature_max,
            "deployment_min": deployment_feature_min,
            "deployment_max": deployment_feature_max,
            "semantic_check": "deployment inside canonical feature range",
            "pass": deployment_inside_canonical_range,
        },
    ]

    # -------------------------------------------------------------------------
    # Target scaling/range audit
    # -------------------------------------------------------------------------

    canonical_target_min = float(np.min(canonical_targets))
    canonical_target_max = float(np.max(canonical_targets))
    deployment_truth_min = float(np.min(truth))
    deployment_truth_max = float(np.max(truth))
    pirnn_min = float(np.min(pirnn))
    pirnn_max = float(np.max(pirnn))

    target_range_consistent = bool(
        deployment_truth_min >= canonical_target_min - 1e-6
        and deployment_truth_max <= canonical_target_max + 1e-6
    )

    target_rows = [
        {
            "field": "canonical_target",
            "minimum": canonical_target_min,
            "maximum": canonical_target_max,
            "mean": float(np.mean(canonical_targets)),
            "std": float(np.std(canonical_targets)),
        },
        {
            "field": "SGSim_SG7A_truth",
            "minimum": deployment_truth_min,
            "maximum": deployment_truth_max,
            "mean": float(np.mean(truth)),
            "std": float(np.std(truth)),
        },
        {
            "field": "SGSim_PI_RNN",
            "minimum": pirnn_min,
            "maximum": pirnn_max,
            "mean": float(np.mean(pirnn)),
            "std": float(np.std(pirnn)),
        },
    ]

    # -------------------------------------------------------------------------
    # Canonical manifold interpolation at every deployment input
    # -------------------------------------------------------------------------

    interpolation_error = np.zeros_like(truth, dtype=float)
    model_error = pirnn - truth
    canonical_interp = np.zeros_like(truth, dtype=float)

    time_rows = []

    for it, t_days in enumerate(times_days):

        # Each streamline at a given physical time has its own normalized tD.
        query_times = normalized_input[it]

        interpolated = interpolate_targets(
            canonical_times,
            canonical_targets,
            query_times,
        )

        canonical_interp[it] = interpolated

        interp_err = interpolated - truth[it]
        interpolation_error[it] = interp_err

        model_err = model_error[it]

        time_rows.append({
            "time_days": float(t_days),
            "canonical_interp_L1_vs_SG7A": float(np.mean(np.abs(interp_err))),
            "canonical_interp_L2_vs_SG7A": float(np.sqrt(np.mean(interp_err**2))),
            "canonical_interp_Linf_vs_SG7A": float(np.max(np.abs(interp_err))),
            "PI_RNN_L1_vs_SG7A": float(np.mean(np.abs(model_err))),
            "PI_RNN_signed_bias": float(np.mean(model_err)),
        })

    interp_l1 = float(np.mean(np.abs(interpolation_error)))
    interp_l2 = float(np.sqrt(np.mean(interpolation_error**2)))
    interp_linf = float(np.max(np.abs(interpolation_error)))

    model_l1 = float(np.mean(np.abs(model_error)))
    model_l2 = float(np.sqrt(np.mean(model_error**2)))
    model_linf = float(np.max(np.abs(model_error)))

    # If canonical interpolated truth reproduces deployment SG7A far more closely
    # than the PI-RNN does, target semantics are consistent and model transfer is
    # the residual mechanism.
    improvement_factor = (
        model_l1 / interp_l1
        if interp_l1 > 0.0
        else np.inf
    )

    interp_rows = [{
        "canonical_interp_L1_vs_SG7A": interp_l1,
        "canonical_interp_L2_vs_SG7A": interp_l2,
        "canonical_interp_Linf_vs_SG7A": interp_linf,
        "PI_RNN_L1_vs_SG7A": model_l1,
        "PI_RNN_L2_vs_SG7A": model_l2,
        "PI_RNN_Linf_vs_SG7A": model_linf,
        "model_to_interp_L1_ratio": improvement_factor,
    }]

    # -------------------------------------------------------------------------
    # TOF-band interpolation audit
    # -------------------------------------------------------------------------

    tof_bands = [
        ("<=250d", -np.inf, 250.0),
        ("250-500d", 250.0, 500.0),
        ("500-1000d", 500.0, 1000.0),
        ("1000-2000d", 1000.0, 2000.0),
        (">2000d", 2000.0, np.inf),
    ]

    tof_rows = []

    for label, lo, hi in tof_bands:

        sl_mask = (tau_end_days > lo) & (tau_end_days <= hi)

        if not np.any(sl_mask):
            continue

        interp_err = interpolation_error[:, sl_mask, :]
        mdl_err = model_error[:, sl_mask, :]

        tof_rows.append({
            "TOF_band": label,
            "streamlines": int(np.sum(sl_mask)),
            "canonical_interp_L1": float(np.mean(np.abs(interp_err))),
            "canonical_interp_signed_bias": float(np.mean(interp_err)),
            "PI_RNN_L1": float(np.mean(np.abs(mdl_err))),
            "PI_RNN_signed_bias": float(np.mean(mdl_err)),
            "model_to_interp_L1_ratio": (
                float(np.mean(np.abs(mdl_err))) /
                max(float(np.mean(np.abs(interp_err))), 1e-15)
            ),
        })

    # -------------------------------------------------------------------------
    # Diagnosis
    # -------------------------------------------------------------------------

    feature_semantics_pass = bool(
        xi_match
        and canonical_time_profile_constant
        and deployment_inside_canonical_range
    )

    target_scaling_pass = bool(
        target_range_consistent
    )

    canonical_manifold_matches = bool(
        interp_l1 <= 5.0e-4
        and interp_linf <= 5.0e-3
    )

    model_error_dominates_interp = bool(
        improvement_factor >= 5.0
    )

    if (
        feature_semantics_pass
        and target_scaling_pass
        and canonical_manifold_matches
        and model_error_dominates_interp
    ):
        diagnosis = "FEATURE_AND_TARGET_TRANSFER_VALID_MODEL_APPROXIMATION_RESIDUAL"
        recommendation = (
            "The canonical feature semantics, normalized-time domain, and saturation "
            "target scaling are consistent with SGSim deployment. Interpolating the "
            "canonical target manifold at deployment inputs reproduces SG7A much more "
            "closely than the frozen PI-RNN does. Keep SG7B-11 frozen and design a "
            "non-invasive deployment calibration/transfer correction rather than "
            "changing target definitions or retraining the front solution globally."
        )
        next_milestone = (
            "V15-SG7C-R3D — Frozen PI-RNN Deployment Calibration Design"
        )

    elif not feature_semantics_pass:
        diagnosis = "CONDITIONAL_FEATURE_SEMANTICS_MISMATCH"
        recommendation = (
            "Canonical and deployment features do not share the same semantics/domain. "
            "Repair the feature construction before any model calibration."
        )
        next_milestone = (
            "V15-SG7C-R3C-FIX — Conditional Feature Construction Repair"
        )

    elif not target_scaling_pass or not canonical_manifold_matches:
        diagnosis = "TARGET_MANIFOLD_OR_SCALING_MISMATCH"
        recommendation = (
            "The canonical target manifold does not reproduce SGSim SG7A truth at "
            "matched inputs. Audit saturation target construction/scaling and SG7A "
            "deployment truth generation before modifying the PI-RNN."
        )
        next_milestone = (
            "V15-SG7C-R3C2 — Target-Manifold Reconciliation Audit"
        )

    else:
        diagnosis = "TRANSFER_RESIDUAL_REQUIRES_DECOMPOSITION"
        recommendation = (
            "Feature semantics and target ranges appear valid, but the interpolation "
            "test does not cleanly isolate the residual to frozen-model approximation. "
            "Decompose the residual by xi, normalized time, and TOF before calibration."
        )
        next_milestone = (
            "V15-SG7C-R3D — Frozen PI-RNN Deployment Residual Decomposition"
        )

    # -------------------------------------------------------------------------
    # Save
    # -------------------------------------------------------------------------

    save_csv(FEATURE_TABLE, feature_rows)
    save_csv(TARGET_TABLE, target_rows)
    save_csv(INTERP_TABLE, interp_rows)
    save_csv(TIME_TABLE, time_rows)
    save_csv(TOF_TABLE, tof_rows)

    np.savez_compressed(
        NUMERICAL_FILE,
        canonical_times=canonical_times,
        canonical_xi=canonical_xi,
        canonical_targets=canonical_targets,
        deployment_normalized_input=normalized_input,
        deployment_truth=truth,
        deployment_pirnn=pirnn,
        canonical_interpolated_target=canonical_interp,
        interpolation_error=interpolation_error,
        model_error=model_error,
        tau_end_days=tau_end_days,
        times_days=times_days,
    )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    plt.figure(figsize=(9, 5))
    plt.hist(canonical_times, bins=50, alpha=0.6, label="canonical profiles")
    plt.hist(normalized_input.ravel(), bins=50, alpha=0.6, label="SGSim deployment")
    plt.xlabel("Normalized tD")
    plt.ylabel("Count")
    plt.title("V15-SG7C-R3C Canonical vs Deployment Conditional-Time Feature")
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3C_Normalized_Time_Comparison.png",
        dpi=300,
    )
    plt.close()

    idx100 = int(np.argmin(np.abs(times_days - 100.0)))

    plt.figure(figsize=(10, 6))
    sample_ids = np.linspace(0, n_streamlines - 1, min(8, n_streamlines)).astype(int)
    for sid in sample_ids:
        plt.plot(
            deployment_xi,
            truth[idx100, sid],
            linewidth=1.0,
            alpha=0.7,
        )
        plt.plot(
            deployment_xi,
            canonical_interp[idx100, sid],
            linestyle="--",
            linewidth=1.0,
            alpha=0.7,
        )
    plt.xlabel("xi")
    plt.ylabel("Saturation")
    plt.title("V15-SG7C-R3C 100d SG7A vs Canonical-Interpolated Targets")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3C_Canonical_Interpolation_100d.png",
        dpi=300,
    )
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.scatter(
        normalized_input.ravel(),
        np.mean(model_error, axis=2).ravel(),
        s=8,
        alpha=0.3,
    )
    plt.xlabel("Normalized tD")
    plt.ylabel("Profile mean PI-RNN - SG7A")
    plt.title("V15-SG7C-R3C Frozen Model Residual vs Conditional Time")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3C_Model_Bias_vs_Normalized_Time.png",
        dpi=300,
    )
    plt.close()

    # -------------------------------------------------------------------------
    # Print
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("CONDITIONAL FEATURE AUDIT")
    print("=" * 78)
    print(f"Canonical xi == deployment xi : {xi_match}")
    print(f"Canonical t feature constant  : {canonical_time_profile_constant}")
    print(
        f"Canonical normalized tD range : "
        f"{canonical_feature_min:.6e} -> {canonical_feature_max:.6e}"
    )
    print(
        f"Deployment normalized tD range: "
        f"{deployment_feature_min:.6e} -> {deployment_feature_max:.6e}"
    )
    print(f"Deployment inside range       : {deployment_inside_canonical_range}")

    print("\nTARGET SCALING")
    print(
        f"Canonical target range        : "
        f"{canonical_target_min:.6f} -> {canonical_target_max:.6f}"
    )
    print(
        f"SGSim SG7A truth range        : "
        f"{deployment_truth_min:.6f} -> {deployment_truth_max:.6f}"
    )
    print(
        f"PI-RNN deployment range       : "
        f"{pirnn_min:.6f} -> {pirnn_max:.6f}"
    )

    print("\nCANONICAL TARGET INTERPOLATION")
    print(f"Canonical interp L1 vs SG7A   : {interp_l1:.6e}")
    print(f"Canonical interp L2 vs SG7A   : {interp_l2:.6e}")
    print(f"Canonical interp Linf vs SG7A : {interp_linf:.6e}")
    print(f"Frozen PI-RNN L1 vs SG7A      : {model_l1:.6e}")
    print(f"Model/interp L1 ratio         : {improvement_factor:.3f}")

    print("\nTOF-BAND TARGET TRANSFER")
    for row in tof_rows:
        print(
            f"  {row['TOF_band']:<12s} | "
            f"interpL1={row['canonical_interp_L1']:.3e} | "
            f"modelL1={row['PI_RNN_L1']:.3e} | "
            f"modelBias={row['PI_RNN_signed_bias']:.3e} | "
            f"ratio={row['model_to_interp_L1_ratio']:.2f}"
        )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3C DIAGNOSTIC VALIDATION")
    print("=" * 78)
    print("[PASS] SG7C-R3B diagnosis reproduced")
    print("[PASS] Canonical feature semantics reconstructed")
    print("[PASS] Canonical target manifold reconstructed")
    print("[PASS] Deployment feature range audited")
    print("[PASS] Target saturation ranges audited")
    print("[PASS] Canonical target interpolated at deployment inputs")
    print("[PASS] Interpolation residual compared with frozen-model residual")
    print("[PASS] TOF-band transfer decomposition generated")
    print("[PASS] Diagnostic classification established")
    print("=" * 78)

    print("\nDIAGNOSTIC FLAGS")
    print(f"  Feature semantics valid       : {feature_semantics_pass}")
    print(f"  Target scaling valid          : {target_scaling_pass}")
    print(f"  Canonical manifold matches    : {canonical_manifold_matches}")
    print(f"  Model error dominates interp  : {model_error_dominates_interp}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    summary = {
        "milestone": "V15-SG7C-R3C",
        "status": "CONDITIONAL_FEATURE_TARGET_SCALING_AUDIT_COMPLETE",
        "incoming_diagnosis": r3b.get("diagnosis"),
        "diagnosis": diagnosis,
        "feature_semantics_pass": feature_semantics_pass,
        "target_scaling_pass": target_scaling_pass,
        "canonical_manifold_matches": canonical_manifold_matches,
        "model_error_dominates_interpolation_error": model_error_dominates_interp,
        "canonical_interp_L1": interp_l1,
        "canonical_interp_Linf": interp_linf,
        "PI_RNN_L1": model_l1,
        "model_to_interp_L1_ratio": improvement_factor,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(SUMMARY_FILE, summary)

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")
    print("\nTables:")
    print(f"  {FEATURE_TABLE.name}")
    print(f"  {TARGET_TABLE.name}")
    print(f"  {INTERP_TABLE.name}")
    print(f"  {TIME_TABLE.name}")
    print(f"  {TOF_TABLE.name}")
    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")
    print("\nDiagnostics:")
    print("  V15SG7CR3C_Normalized_Time_Comparison.png")
    print("  V15SG7CR3C_Canonical_Interpolation_100d.png")
    print("  V15SG7CR3C_Model_Bias_vs_Normalized_Time.png")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3C AUDIT: PASS")
    print()
    print("No training was performed.")
    print("No model, feature, target, map-back, or validation gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
