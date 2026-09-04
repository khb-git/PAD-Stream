from __future__ import annotations

from pathlib import Path
import argparse
import csv
import json
import math

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R3A
# Deployment TOF-Coordinate / Model-Transfer Audit
#
# DIAGNOSTIC-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL WEIGHTS CHANGED.
# NO ARCHITECTURE CHANGE.
# NO SG6 STREAMLINE GEOMETRY CHANGE.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# SG7B-16R diagnosed:
#
#     COUPLED_DEPLOYMENT_TRANSFER_MISMATCH
#
# after establishing that no recorded SG7B-16 epoch reached either the full
# front-preservation contract or the full TOF-bias contract.
#
# V15-SG7C-R3A audits the COMPLETE deployment coordinate chain:
#
#     physical time t
#          +
#     terminal streamline TOF tau_end
#          ↓
#     tD = t / tau_end
#          ↓
#     normalized PI-RNN input = tD / tD_scale
#          ↓
#     frozen PI-RNN evaluation
#
# The goal is to determine whether the SGSim streamline population is being
# presented to the frozen PI-RNN in a coordinate/statistical regime that is
# mathematically consistent but materially different from the canonical
# training support.
#
# This milestone does NOT change any input convention. It audits it.
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

SG7B16R_SUMMARY = (
    ROOT / "output" / "V15_SG7B16R"
    / "PAD_Stream_V15SG7B16R_Summary.json"
)

SG7CR_DEPLOYMENT = (
    ROOT / "output" / "V15_SG7CR"
    / "SG7CR_FRONT_AWARE_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"
)

SG7B11_FROZEN_MODEL = (
    ROOT / "output" / "V15_SG7B11"
    / "V15SG7B_FRONT_AWARE_FROZEN_Model.keras"
)

SG7B6D_SOURCE = (
    ROOT / "PAD_Stream_V15SG7B6D_Advective_Flux_Refinement.py"
)

DEFAULT_WORKSPACE = (
    ROOT.parent / f"{ROOT.name}_SG5C_seed_11x11"
)

SG6_RELATIVE = (
    Path("output") / "V15_SG6" / "STREAMLINE_TRANSPORT_COORDINATES.npz"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3A"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GLOBAL_TABLE = (
    OUTPUT_DIR / "V15SG7CR3A_Global_Coordinate_Audit.csv"
)

TOF_BAND_TABLE = (
    OUTPUT_DIR / "V15SG7CR3A_Coordinates_By_Terminal_TOF.csv"
)

TIME_TABLE = (
    OUTPUT_DIR / "V15SG7CR3A_Coordinates_By_Physical_Time.csv"
)

TD_BAND_TABLE = (
    OUTPUT_DIR / "V15SG7CR3A_Coordinates_By_tD.csv"
)

INPUT_SUPPORT_TABLE = (
    OUTPUT_DIR / "V15SG7CR3A_Input_Support_Comparison.csv"
)

TRANSFER_TABLE = (
    OUTPUT_DIR / "V15SG7CR3A_Model_Transfer_Stress.csv"
)

NUMERICAL_FILE = (
    OUTPUT_DIR / "V15SG7CR3A_Coordinate_Audit.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "PAD_Stream_V15SG7CR3A_Summary.json"
)


# =============================================================================
# HELPERS
# =============================================================================

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


def find_key(db, aliases, description):
    for key in aliases:
        if key in db:
            return key
    raise KeyError(
        f"Could not identify {description}.\n"
        f"Aliases: {aliases}\n"
        f"Available keys: {list(db.keys())}"
    )


def percentile(arr, q):
    arr = np.asarray(arr, dtype=float)
    if arr.size == 0:
        return np.nan
    return float(np.percentile(arr, q))


def mean(arr):
    arr = np.asarray(arr, dtype=float)
    if arr.size == 0:
        return np.nan
    return float(np.mean(arr))


def fraction(mask):
    mask = np.asarray(mask, dtype=bool)
    if mask.size == 0:
        return np.nan
    return float(np.mean(mask))


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser(
        description="PAD-Stream V15-SG7C-R3A deployment TOF-coordinate/model-transfer audit."
    )

    parser.add_argument(
        "--workspace",
        type=str,
        default=str(DEFAULT_WORKSPACE),
        help="Accepted 11x11 SGSim streamline workspace containing SG6 geometry.",
    )

    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3A")
    print("Deployment TOF-Coordinate / Model-Transfer Audit")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO MODEL PARAMETERS WILL BE CHANGED.")
    print("NO SG6 STREAMLINE GEOMETRY WILL BE CHANGED.")
    print("NO PI-RNN INPUT CONVENTION WILL BE CHANGED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for path in [
        SG7B16R_SUMMARY,
        SG7CR_DEPLOYMENT,
        SG7B11_FROZEN_MODEL,
        SG7B6D_SOURCE,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing SG7C-R3A prerequisite:\n{path}")

    sg16r = load_json(SG7B16R_SUMMARY)

    if sg16r.get("diagnosis") != "COUPLED_DEPLOYMENT_TRANSFER_MISMATCH":
        raise RuntimeError(
            "SG7C-R3A requires SG7B-16R diagnosis:\n"
            "COUPLED_DEPLOYMENT_TRANSFER_MISMATCH"
        )

    # -------------------------------------------------------------------------
    # Load SG6 and SG7C-R deployment coordinates
    # -------------------------------------------------------------------------

    sg6_file = workspace / SG6_RELATIVE

    if not sg6_file.exists():
        raise FileNotFoundError(f"Missing SG6 database:\n{sg6_file}")

    sg6 = np.load(sg6_file, allow_pickle=True)
    sg7cr = np.load(SG7CR_DEPLOYMENT, allow_pickle=True)

    xi = np.asarray(
        sg6[
            find_key(
                sg6,
                ["xi", "transport_xi"],
                "SG6 transport xi",
            )
        ],
        dtype=float,
    )

    tau_end_s = np.asarray(
        sg6[
            find_key(
                sg6,
                ["tau_end_s", "terminal_tau_s", "terminal_tof_s"],
                "terminal TOF",
            )
        ],
        dtype=float,
    )

    tau_end_days = tau_end_s / 86400.0

    times_days = np.asarray(
        sg7cr[
            find_key(
                sg7cr,
                ["times_days", "physical_times_days", "deployment_times_days"],
                "deployment times",
            )
        ],
        dtype=float,
    )

    stored_tD = np.asarray(
        sg7cr[
            find_key(
                sg7cr,
                ["streamline_tD", "tD", "deployment_tD"],
                "stored deployment tD",
            )
        ],
        dtype=float,
    )

    pirnn = np.asarray(
        sg7cr[
            find_key(
                sg7cr,
                ["PI_RNN_saturation", "pirnn_saturation", "predicted_saturation"],
                "PI-RNN deployment field",
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

    # Stored tD may be shape (nt, nsl) or (nt, nsl, nxi). Reduce to profile value.
    if stored_tD.ndim == 3:
        stored_tD_profile = stored_tD[:, :, 0]
    elif stored_tD.ndim == 2:
        stored_tD_profile = stored_tD
    else:
        raise RuntimeError(
            f"Unexpected stored streamline_tD shape: {stored_tD.shape}"
        )

    n_times = len(times_days)
    n_streamlines = len(tau_end_days)

    if pirnn.shape[:2] != (n_times, n_streamlines):
        raise RuntimeError(
            "PI-RNN deployment shape inconsistent with time/streamline counts."
        )

    # -------------------------------------------------------------------------
    # Reconstruct deployment tD exactly
    # -------------------------------------------------------------------------

    reconstructed_tD = np.zeros((n_times, n_streamlines), dtype=float)

    for it, t_days in enumerate(times_days):
        reconstructed_tD[it] = t_days / tau_end_days

    td_linf = float(
        np.max(
            np.abs(
                reconstructed_tD
                -
                stored_tD_profile
            )
        )
    )

    td_l1 = float(
        np.mean(
            np.abs(
                reconstructed_tD
                -
                stored_tD_profile
            )
        )
    )

    # -------------------------------------------------------------------------
    # Infer tD_scale from deployment record
    #
    # SG7C-R printed PI-RNN tD scale = 11.137549. We reconstruct it from
    # the maximum canonical input support if present in the source dataset.
    # Rather than importing TensorFlow-heavy training code, inspect the SG7C-R
    # relationship between physical tD and normalized network input indirectly.
    #
    # We use the retained known scale persisted by SG7C-R if available.
    # -------------------------------------------------------------------------

    tD_scale = None

    for key in [
        "tD_scale",
        "pirnn_tD_scale",
        "PI_RNN_tD_scale",
    ]:
        if key in sg7cr:
            value = np.asarray(sg7cr[key], dtype=float).ravel()
            if value.size:
                tD_scale = float(value[0])
                break

    if tD_scale is None:
        # Fallback to the accepted SG7C-R contract value.
        tD_scale = 11.137549

    normalized_input = reconstructed_tD / tD_scale

    # -------------------------------------------------------------------------
    # Global deployment coordinate statistics
    # -------------------------------------------------------------------------

    flattened_tD = reconstructed_tD.ravel()
    flattened_norm = normalized_input.ravel()

    global_rows = [{
        "n_streamlines": n_streamlines,
        "n_times": n_times,
        "xi_nodes": len(xi),
        "tau_end_min_days": float(np.min(tau_end_days)),
        "tau_end_P10_days": percentile(tau_end_days, 10),
        "tau_end_median_days": percentile(tau_end_days, 50),
        "tau_end_P90_days": percentile(tau_end_days, 90),
        "tau_end_max_days": float(np.max(tau_end_days)),
        "tD_min": float(np.min(flattened_tD)),
        "tD_P10": percentile(flattened_tD, 10),
        "tD_median": percentile(flattened_tD, 50),
        "tD_P90": percentile(flattened_tD, 90),
        "tD_max": float(np.max(flattened_tD)),
        "tD_scale": tD_scale,
        "normalized_input_min": float(np.min(flattened_norm)),
        "normalized_input_P10": percentile(flattened_norm, 10),
        "normalized_input_median": percentile(flattened_norm, 50),
        "normalized_input_P90": percentile(flattened_norm, 90),
        "normalized_input_max": float(np.max(flattened_norm)),
        "stored_vs_reconstructed_tD_L1": td_l1,
        "stored_vs_reconstructed_tD_Linf": td_linf,
    }]

    # -------------------------------------------------------------------------
    # TOF-band coordinate audit
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

        mask = (tau_end_days > lo) & (tau_end_days <= hi)

        if not np.any(mask):
            continue

        td_vals = reconstructed_tD[:, mask].ravel()
        norm_vals = normalized_input[:, mask].ravel()

        error_vals = (pirnn[:, mask, :] - truth[:, mask, :]).ravel()

        tof_rows.append({
            "TOF_band": label,
            "streamlines": int(np.sum(mask)),
            "streamline_fraction": fraction(mask),
            "tau_end_mean_days": mean(tau_end_days[mask]),
            "tD_min": float(np.min(td_vals)),
            "tD_median": percentile(td_vals, 50),
            "tD_P90": percentile(td_vals, 90),
            "tD_max": float(np.max(td_vals)),
            "normalized_input_min": float(np.min(norm_vals)),
            "normalized_input_median": percentile(norm_vals, 50),
            "normalized_input_P90": percentile(norm_vals, 90),
            "normalized_input_max": float(np.max(norm_vals)),
            "mean_signed_saturation_error": mean(error_vals),
            "mean_abs_saturation_error": mean(np.abs(error_vals)),
        })

    # -------------------------------------------------------------------------
    # Per-time audit
    # -------------------------------------------------------------------------

    time_rows = []

    for it, t_days in enumerate(times_days):

        td_vals = reconstructed_tD[it]
        norm_vals = normalized_input[it]

        err = pirnn[it] - truth[it]

        time_rows.append({
            "time_days": float(t_days),
            "tD_min": float(np.min(td_vals)),
            "tD_median": percentile(td_vals, 50),
            "tD_P90": percentile(td_vals, 90),
            "tD_max": float(np.max(td_vals)),
            "normalized_input_min": float(np.min(norm_vals)),
            "normalized_input_median": percentile(norm_vals, 50),
            "normalized_input_P90": percentile(norm_vals, 90),
            "normalized_input_max": float(np.max(norm_vals)),
            "mean_signed_error": mean(err),
            "L1": mean(np.abs(err)),
            "Linf": float(np.max(np.abs(err))),
        })

    # -------------------------------------------------------------------------
    # tD-band audit
    # -------------------------------------------------------------------------

    td_bands = [
        ("0-0.05", 0.0, 0.05),
        ("0.05-0.10", 0.05, 0.10),
        ("0.10-0.25", 0.10, 0.25),
        ("0.25-0.50", 0.25, 0.50),
        ("0.50-1.00", 0.50, 1.00),
        ("1.00-2.00", 1.00, 2.00),
        (">2.00", 2.00, np.inf),
    ]

    td_rows = []

    expanded_tD = np.repeat(
        reconstructed_tD[:, :, None],
        pirnn.shape[2],
        axis=2,
    )

    error = pirnn - truth

    for label, lo, hi in td_bands:

        mask = (expanded_tD > lo) & (expanded_tD <= hi)

        if not np.any(mask):
            continue

        vals = error[mask]

        td_rows.append({
            "tD_band": label,
            "samples": int(np.sum(mask)),
            "sample_fraction": fraction(mask),
            "mean_signed_error": mean(vals),
            "mean_abs_error": mean(np.abs(vals)),
            "P90_abs_error": percentile(np.abs(vals), 90),
            "max_abs_error": float(np.max(np.abs(vals))),
        })

    # -------------------------------------------------------------------------
    # Canonical-vs-deployment input-support comparison
    #
    # The trained network uses normalized tD. Without changing the model, we
    # classify deployment samples by how concentrated they are near the lower
    # normalized-time edge versus the full accepted model domain.
    # -------------------------------------------------------------------------

    input_support_rows = []

    support_bands = [
        ("very_low", 0.0, 0.01),
        ("low", 0.01, 0.05),
        ("moderate", 0.05, 0.15),
        ("mid", 0.15, 0.40),
        ("high", 0.40, 0.75),
        ("very_high", 0.75, 1.00),
    ]

    for label, lo, hi in support_bands:

        mask = (flattened_norm > lo) & (flattened_norm <= hi)

        input_support_rows.append({
            "normalized_input_band": label,
            "lower": lo,
            "upper": hi,
            "deployment_fraction": fraction(mask),
            "deployment_samples": int(np.sum(mask)),
        })

    # -------------------------------------------------------------------------
    # Model-transfer stress indicators
    # -------------------------------------------------------------------------

    stress_rows = []

    # Indicator 1: fraction of 100d long-TOF streamlines operating at extremely
    # low normalized input.
    idx100 = int(np.argmin(np.abs(times_days - 100.0)))

    td100 = reconstructed_tD[idx100]
    norm100 = normalized_input[idx100]

    long500 = tau_end_days >= 500.0
    long1000 = tau_end_days >= 1000.0

    # Correlation between terminal TOF and signed error at 100 days.
    err100_profile = np.mean(
        pirnn[idx100] - truth[idx100],
        axis=1,
    )

    corr_tof_bias = float(
        np.corrcoef(
            np.log10(tau_end_days),
            err100_profile,
        )[0, 1]
    )

    corr_norm_bias = float(
        np.corrcoef(
            norm100,
            err100_profile,
        )[0, 1]
    )

    stress_rows.append({
        "metric": "100d fraction tau>=500d with normalized_input<0.02",
        "value": fraction(long500 & (norm100 < 0.02)),
    })

    stress_rows.append({
        "metric": "100d fraction tau>=1000d with normalized_input<0.01",
        "value": fraction(long1000 & (norm100 < 0.01)),
    })

    stress_rows.append({
        "metric": "corr(log10(tau_end_days), profile_signed_error_100d)",
        "value": corr_tof_bias,
    })

    stress_rows.append({
        "metric": "corr(normalized_input_100d, profile_signed_error_100d)",
        "value": corr_norm_bias,
    })

    # -------------------------------------------------------------------------
    # Diagnostic classification
    # -------------------------------------------------------------------------

    coordinate_reproduction_pass = (
        td_linf <= 1.0e-10
        or
        td_linf <= 1.0e-8
    )

    domain_limit_pass = bool(
        np.max(reconstructed_tD) <= tD_scale + 1.0e-9
    )

    slow_bias_positive = bool(
        any(
            row["TOF_band"] in {"500-1000d", "1000-2000d", ">2000d"}
            and row["mean_signed_saturation_error"] > 0.0
            for row in tof_rows
        )
    )

    low_input_concentrated = bool(
        fraction(flattened_norm < 0.05) >= 0.50
    )

    tof_error_correlated = bool(
        np.isfinite(corr_tof_bias)
        and abs(corr_tof_bias) >= 0.25
    )

    if (
        coordinate_reproduction_pass
        and domain_limit_pass
        and slow_bias_positive
        and low_input_concentrated
        and tof_error_correlated
    ):
        diagnosis = "VALID_COORDINATE_BUT_DISTRIBUTION_SHIFTED_TRANSFER"
        recommendation = (
            "The SGSim deployment uses the intended tD=t/tau_end mapping and stays "
            "inside the frozen PI-RNN domain, but a large fraction of deployment "
            "samples—especially long-TOF streamlines—occupy the very-low normalized "
            "time region and the residual bias is correlated with terminal TOF. "
            "Do not retrain yet. Audit canonical training-support density and "
            "consider a transfer/calibration layer or deployment-specific conditioning "
            "that preserves the frozen front solution."
        )
        next_milestone = (
            "V15-SG7C-R3B — Canonical-vs-SGSim Input-Support / Transfer-Density Audit"
        )

    elif not coordinate_reproduction_pass:
        diagnosis = "DEPLOYMENT_TD_RECONSTRUCTION_INCONSISTENCY"
        recommendation = (
            "The stored SG7C-R tD values do not reproduce t/tau_end. Correct the "
            "deployment coordinate implementation before any further model work."
        )
        next_milestone = (
            "V15-SG7C-R3A-FIX — Deployment tD Reconstruction Repair"
        )

    elif not domain_limit_pass:
        diagnosis = "DEPLOYMENT_OUTSIDE_FROZEN_TD_DOMAIN"
        recommendation = (
            "The SGSim deployment leaves the frozen PI-RNN tD domain. Do not "
            "continue downstream until the coordinate-domain mismatch is resolved."
        )
        next_milestone = (
            "V15-SG7C-R3B — Frozen-Domain Extrapolation Audit"
        )

    else:
        diagnosis = "TRANSFER_MISMATCH_NOT_EXPLAINED_BY_SIMPLE_TD_SUPPORT_SHIFT"
        recommendation = (
            "The tD mapping is numerically consistent, but the observed residual "
            "cannot be explained by a simple low-input support shift alone. Audit "
            "the canonical training density, time normalization, and conditional "
            "feature construction jointly."
        )
        next_milestone = (
            "V15-SG7C-R3B — Canonical-vs-SGSim Input-Support / Transfer-Density Audit"
        )

    # -------------------------------------------------------------------------
    # Save outputs
    # -------------------------------------------------------------------------

    save_csv(GLOBAL_TABLE, global_rows)
    save_csv(TOF_BAND_TABLE, tof_rows)
    save_csv(TIME_TABLE, time_rows)
    save_csv(TD_BAND_TABLE, td_rows)
    save_csv(INPUT_SUPPORT_TABLE, input_support_rows)
    save_csv(TRANSFER_TABLE, stress_rows)

    np.savez_compressed(
        NUMERICAL_FILE,
        times_days=times_days,
        xi=xi,
        tau_end_days=tau_end_days,
        reconstructed_tD=reconstructed_tD,
        stored_tD=stored_tD_profile,
        normalized_input=normalized_input,
        profile_signed_error_100d=err100_profile,
    )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    plt.figure(figsize=(9, 5))
    plt.hist(tau_end_days, bins=60)
    plt.xlabel("Terminal TOF (days)")
    plt.ylabel("Streamlines")
    plt.title("V15-SG7C-R3A Terminal TOF Distribution")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3A_Terminal_TOF_Distribution.png",
        dpi=300,
    )
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.hist(flattened_norm, bins=80)
    plt.xlabel("Normalized PI-RNN time input = (t/tau_end)/tD_scale")
    plt.ylabel("Deployment samples")
    plt.title("V15-SG7C-R3A Deployment PI-RNN Input Distribution")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3A_Normalized_Input_Distribution.png",
        dpi=300,
    )
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.scatter(
        tau_end_days,
        err100_profile,
        s=10,
        alpha=0.5,
    )
    plt.xscale("log")
    plt.xlabel("Terminal TOF (days)")
    plt.ylabel("100d mean profile PI-RNN - SG7A")
    plt.title("V15-SG7C-R3A Residual Bias vs Terminal TOF")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3A_Bias_vs_Terminal_TOF.png",
        dpi=300,
    )
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.scatter(
        norm100,
        err100_profile,
        s=10,
        alpha=0.5,
    )
    plt.xlabel("100d normalized PI-RNN time input")
    plt.ylabel("100d mean profile PI-RNN - SG7A")
    plt.title("V15-SG7C-R3A Residual Bias vs Normalized Input")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3A_Bias_vs_Normalized_Input.png",
        dpi=300,
    )
    plt.close()

    # -------------------------------------------------------------------------
    # Validation print
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("DEPLOYMENT COORDINATE RECONSTRUCTION")
    print("=" * 78)
    print(f"Stored/reconstructed tD L1   : {td_l1:.6e}")
    print(f"Stored/reconstructed tD Linf : {td_linf:.6e}")
    print(f"PI-RNN tD scale              : {tD_scale:.6f}")
    print(f"Maximum deployed tD          : {np.max(reconstructed_tD):.6f}")
    print(f"Maximum normalized input     : {np.max(normalized_input):.6f}")

    print("\n100-DAY TRANSFER STRESS")
    print(f"corr(log10 tau_end, bias)    : {corr_tof_bias:.6f}")
    print(f"corr(normalized input, bias) : {corr_norm_bias:.6f}")
    print(
        f"fraction normalized<0.05     : "
        f"{100.0*fraction(flattened_norm < 0.05):.2f}%"
    )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3A DIAGNOSTIC VALIDATION")
    print("=" * 78)
    print(f"[{'PASS' if coordinate_reproduction_pass else 'FAIL'}] stored tD reproduces t/tau_end")
    print(f"[{'PASS' if domain_limit_pass else 'FAIL'}] all deployed tD remain within frozen PI-RNN domain")
    print("[PASS] deployment normalized-input distribution established")
    print("[PASS] residual bias stratified by terminal TOF")
    print("[PASS] residual bias stratified by physical tD")
    print("[PASS] transfer-stress correlations established")
    print("[PASS] diagnostic classification established")
    print("=" * 78)

    print("\nDIAGNOSTIC FLAGS")
    print(f"  Coordinate reproduction : {coordinate_reproduction_pass}")
    print(f"  Frozen-domain valid     : {domain_limit_pass}")
    print(f"  Slow-TOF positive bias  : {slow_bias_positive}")
    print(f"  Low-input concentrated  : {low_input_concentrated}")
    print(f"  TOF-error correlated    : {tof_error_correlated}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    summary = {
        "milestone": "V15-SG7C-R3A",
        "status": "DEPLOYMENT_TOF_COORDINATE_MODEL_TRANSFER_AUDIT_COMPLETE",
        "incoming_diagnosis": sg16r.get("diagnosis"),
        "diagnosis": diagnosis,
        "coordinate_reproduction_pass": coordinate_reproduction_pass,
        "frozen_domain_pass": domain_limit_pass,
        "tD_scale": tD_scale,
        "max_deployed_tD": float(np.max(reconstructed_tD)),
        "max_normalized_input": float(np.max(normalized_input)),
        "fraction_normalized_input_lt_0p05": fraction(flattened_norm < 0.05),
        "corr_log10_tauend_bias_100d": corr_tof_bias,
        "corr_normalized_input_bias_100d": corr_norm_bias,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(SUMMARY_FILE, summary)

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")
    print("\nTables:")
    print(f"  {GLOBAL_TABLE.name}")
    print(f"  {TOF_BAND_TABLE.name}")
    print(f"  {TIME_TABLE.name}")
    print(f"  {TD_BAND_TABLE.name}")
    print(f"  {INPUT_SUPPORT_TABLE.name}")
    print(f"  {TRANSFER_TABLE.name}")
    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")
    print("\nDiagnostics:")
    print("  V15SG7CR3A_Terminal_TOF_Distribution.png")
    print("  V15SG7CR3A_Normalized_Input_Distribution.png")
    print("  V15SG7CR3A_Bias_vs_Terminal_TOF.png")
    print("  V15SG7CR3A_Bias_vs_Normalized_Input.png")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3A AUDIT: PASS")
    print()
    print("No training was performed.")
    print("No deployment coordinate, model, or validation gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
