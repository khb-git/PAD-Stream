from __future__ import annotations

from pathlib import Path
import argparse
import csv
import importlib.util
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7C-R3B
# Canonical-vs-SGSim Input-Support / Transfer-Density Audit
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
# SG7C-R3A established:
#
#   1. deployed tD exactly reproduces t / tau_end,
#   2. all deployed tD values remain inside the frozen PI-RNN domain,
#   3. residual bias is strongly correlated with terminal TOF,
#   4. simple low-normalized-tD concentration alone does not explain the
#      transfer mismatch.
#
# Diagnosis:
#
#   TRANSFER_MISMATCH_NOT_EXPLAINED_BY_SIMPLE_TD_SUPPORT_SHIFT
#
# R3B therefore compares the canonical training support against the actual
# SGSim deployment support in:
#
#       xi
#       normalized tD
#       joint (xi, normalized tD)
#
# and asks whether deployment error rises in low-density canonical regions.
#
# This milestone does NOT change the PI-RNN or its input convention.
# =============================================================================


ROOT = Path(__file__).resolve().parent

SG7CR3A_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3A"
    / "PAD_Stream_V15SG7CR3A_Summary.json"
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

OUTPUT_DIR = ROOT / "output" / "V15_SG7CR3B"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GLOBAL_TABLE = OUTPUT_DIR / "V15SG7CR3B_Global_Support_Comparison.csv"
XI_TABLE = OUTPUT_DIR / "V15SG7CR3B_Support_By_Xi.csv"
TD_TABLE = OUTPUT_DIR / "V15SG7CR3B_Support_By_Normalized_tD.csv"
JOINT_TABLE = OUTPUT_DIR / "V15SG7CR3B_Joint_Support_Density.csv"
ERROR_DENSITY_TABLE = OUTPUT_DIR / "V15SG7CR3B_Error_vs_Canonical_Density.csv"
TOF_DENSITY_TABLE = OUTPUT_DIR / "V15SG7CR3B_TOF_Band_Density_Stress.csv"
NUMERICAL_FILE = OUTPUT_DIR / "V15SG7CR3B_Transfer_Density_Audit.npz"
SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG7CR3B_Summary.json"


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


def finite_corr(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if np.sum(mask) < 3:
        return np.nan
    return float(np.corrcoef(x[mask], y[mask])[0, 1])


def bin_index(values, edges):
    idx = np.digitize(values, edges) - 1
    idx = np.clip(idx, 0, len(edges) - 2)
    return idx


def main():

    parser = argparse.ArgumentParser(
        description="PAD-Stream V15-SG7C-R3B canonical-vs-SGSim support-density audit."
    )

    parser.add_argument(
        "--xi-bins",
        type=int,
        default=24,
        help="Number of xi bins for joint support audit.",
    )

    parser.add_argument(
        "--td-bins",
        type=int,
        default=24,
        help="Number of normalized-tD bins for joint support audit.",
    )

    args = parser.parse_args()

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3B")
    print("Canonical-vs-SGSim Input-Support / Transfer-Density Audit")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO MODEL PARAMETERS WILL BE CHANGED.")
    print("NO ARCHITECTURE CHANGE WILL BE MADE.")
    print("NO DEPLOYMENT COORDINATE CONVENTION WILL BE CHANGED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for path in [
        SG7CR3A_SUMMARY,
        SG7CR3A_NUMERICAL,
        SG7CR_DEPLOYMENT,
        BASE_SOURCE,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing SG7C-R3B prerequisite:\n{path}")

    r3a = load_json(SG7CR3A_SUMMARY)

    if r3a.get("diagnosis") != "TRANSFER_MISMATCH_NOT_EXPLAINED_BY_SIMPLE_TD_SUPPORT_SHIFT":
        raise RuntimeError(
            "SG7C-R3B requires SG7C-R3A diagnosis:\n"
            "TRANSFER_MISMATCH_NOT_EXPLAINED_BY_SIMPLE_TD_SUPPORT_SHIFT"
        )

    base = import_module(
        BASE_SOURCE,
        "pad_stream_sg7b6d_for_sg7cr3b",
    )

    dataset = base.load_dataset()

    # -------------------------------------------------------------------------
    # Canonical training support
    # -------------------------------------------------------------------------

    X_train = np.asarray(dataset["X_train"], dtype=float)
    X_val = np.asarray(dataset["X_val"], dtype=float)
    X_test = np.asarray(dataset["X_test"], dtype=float)

    X_all = np.concatenate([X_train, X_val, X_test], axis=0)

    if X_all.ndim != 3 or X_all.shape[-1] < 2:
        raise RuntimeError(
            f"Unexpected canonical input shape: {X_all.shape}"
        )

    canonical_xi = X_all[:, :, 0].ravel()
    canonical_tnorm = X_all[:, :, 1].ravel()

    # -------------------------------------------------------------------------
    # Deployment support from R3A + SG7C-R
    # -------------------------------------------------------------------------

    r3a_db = np.load(SG7CR3A_NUMERICAL, allow_pickle=True)
    sg7cr = np.load(SG7CR_DEPLOYMENT, allow_pickle=True)

    deployment_xi = np.asarray(
        r3a_db[
            find_key(
                r3a_db,
                ["xi"],
                "deployment xi",
            )
        ],
        dtype=float,
    )

    normalized_input = np.asarray(
        r3a_db[
            find_key(
                r3a_db,
                ["normalized_input"],
                "normalized PI-RNN time input",
            )
        ],
        dtype=float,
    )

    tau_end_days = np.asarray(
        r3a_db[
            find_key(
                r3a_db,
                ["tau_end_days"],
                "terminal TOF days",
            )
        ],
        dtype=float,
    )

    times_days = np.asarray(
        r3a_db[
            find_key(
                r3a_db,
                ["times_days"],
                "deployment times",
            )
        ],
        dtype=float,
    )

    pirnn = np.asarray(
        sg7cr[
            find_key(
                sg7cr,
                ["PI_RNN_saturation", "pirnn_saturation", "predicted_saturation"],
                "deployment PI-RNN field",
            )
        ],
        dtype=float,
    )

    truth = np.asarray(
        sg7cr[
            find_key(
                sg7cr,
                ["SG7A_saturation", "truth_saturation", "reference_saturation"],
                "deployment SG7A truth",
            )
        ],
        dtype=float,
    )

    n_times, n_streamlines, n_nodes = pirnn.shape

    if normalized_input.shape != (n_times, n_streamlines):
        raise RuntimeError(
            f"normalized_input shape {normalized_input.shape} does not match "
            f"deployment {(n_times, n_streamlines)}"
        )

    if len(deployment_xi) != n_nodes:
        raise RuntimeError(
            "Deployment xi count does not match SG7C-R node count."
        )

    # Expand deployment coordinates to node-level samples.
    dep_xi = np.broadcast_to(
        deployment_xi[None, None, :],
        (n_times, n_streamlines, n_nodes),
    ).ravel()

    dep_tnorm = np.broadcast_to(
        normalized_input[:, :, None],
        (n_times, n_streamlines, n_nodes),
    ).ravel()

    dep_error = (pirnn - truth).ravel()
    dep_abs_error = np.abs(dep_error)

    # -------------------------------------------------------------------------
    # Common support domain / bins
    # -------------------------------------------------------------------------

    xi_min = min(float(np.min(canonical_xi)), float(np.min(dep_xi)))
    xi_max = max(float(np.max(canonical_xi)), float(np.max(dep_xi)))

    td_min = min(float(np.min(canonical_tnorm)), float(np.min(dep_tnorm)))
    td_max = max(float(np.max(canonical_tnorm)), float(np.max(dep_tnorm)))

    xi_edges = np.linspace(xi_min, xi_max, args.xi_bins + 1)
    td_edges = np.linspace(td_min, td_max, args.td_bins + 1)

    canon_hist2d, _, _ = np.histogram2d(
        canonical_xi,
        canonical_tnorm,
        bins=[xi_edges, td_edges],
    )

    dep_hist2d, _, _ = np.histogram2d(
        dep_xi,
        dep_tnorm,
        bins=[xi_edges, td_edges],
    )

    canon_density = canon_hist2d / max(np.sum(canon_hist2d), 1.0)
    dep_density = dep_hist2d / max(np.sum(dep_hist2d), 1.0)

    # Canonical density assigned to every deployment sample.
    xi_idx = bin_index(dep_xi, xi_edges)
    td_idx = bin_index(dep_tnorm, td_edges)

    dep_canonical_density = canon_density[xi_idx, td_idx]

    # Also compute occupancy count (before normalization) for intuitive diagnostics.
    dep_canonical_count = canon_hist2d[xi_idx, td_idx]

    # -------------------------------------------------------------------------
    # Global support comparison
    # -------------------------------------------------------------------------

    zero_support_fraction = float(
        np.mean(dep_canonical_count <= 0.0)
    )

    sparse_1_fraction = float(
        np.mean(dep_canonical_count <= 1.0)
    )

    sparse_5_fraction = float(
        np.mean(dep_canonical_count <= 5.0)
    )

    # Compare deployment and canonical marginals using total variation distance.
    canon_xi_hist, _ = np.histogram(canonical_xi, bins=xi_edges)
    dep_xi_hist, _ = np.histogram(dep_xi, bins=xi_edges)

    canon_td_hist, _ = np.histogram(canonical_tnorm, bins=td_edges)
    dep_td_hist, _ = np.histogram(dep_tnorm, bins=td_edges)

    canon_xi_p = canon_xi_hist / max(np.sum(canon_xi_hist), 1.0)
    dep_xi_p = dep_xi_hist / max(np.sum(dep_xi_hist), 1.0)

    canon_td_p = canon_td_hist / max(np.sum(canon_td_hist), 1.0)
    dep_td_p = dep_td_hist / max(np.sum(dep_td_hist), 1.0)

    tv_xi = 0.5 * float(np.sum(np.abs(canon_xi_p - dep_xi_p)))
    tv_td = 0.5 * float(np.sum(np.abs(canon_td_p - dep_td_p)))
    tv_joint = 0.5 * float(np.sum(np.abs(canon_density - dep_density)))

    density_error_corr = finite_corr(
        np.log10(dep_canonical_density + 1.0e-12),
        dep_abs_error,
    )

    density_signed_corr = finite_corr(
        np.log10(dep_canonical_density + 1.0e-12),
        dep_error,
    )

    global_rows = [{
        "canonical_samples": int(canonical_xi.size),
        "deployment_samples": int(dep_xi.size),
        "xi_bins": args.xi_bins,
        "td_bins": args.td_bins,
        "canonical_xi_min": float(np.min(canonical_xi)),
        "canonical_xi_max": float(np.max(canonical_xi)),
        "deployment_xi_min": float(np.min(dep_xi)),
        "deployment_xi_max": float(np.max(dep_xi)),
        "canonical_tnorm_min": float(np.min(canonical_tnorm)),
        "canonical_tnorm_max": float(np.max(canonical_tnorm)),
        "deployment_tnorm_min": float(np.min(dep_tnorm)),
        "deployment_tnorm_max": float(np.max(dep_tnorm)),
        "TV_distance_xi": tv_xi,
        "TV_distance_normalized_tD": tv_td,
        "TV_distance_joint_xi_tD": tv_joint,
        "deployment_zero_canonical_support_fraction": zero_support_fraction,
        "deployment_canonical_count_le_1_fraction": sparse_1_fraction,
        "deployment_canonical_count_le_5_fraction": sparse_5_fraction,
        "corr_log_canonical_density_abs_error": density_error_corr,
        "corr_log_canonical_density_signed_error": density_signed_corr,
    }]

    # -------------------------------------------------------------------------
    # Marginal xi support
    # -------------------------------------------------------------------------

    xi_rows = []

    for i in range(args.xi_bins):

        mask_dep = xi_idx == i

        xi_rows.append({
            "xi_bin": i,
            "xi_low": xi_edges[i],
            "xi_high": xi_edges[i + 1],
            "canonical_fraction": float(canon_xi_p[i]),
            "deployment_fraction": float(dep_xi_p[i]),
            "deployment_to_canonical_ratio": (
                float(dep_xi_p[i] / canon_xi_p[i])
                if canon_xi_p[i] > 0.0
                else np.inf
            ),
            "deployment_mean_abs_error": (
                float(np.mean(dep_abs_error[mask_dep]))
                if np.any(mask_dep)
                else np.nan
            ),
            "deployment_mean_signed_error": (
                float(np.mean(dep_error[mask_dep]))
                if np.any(mask_dep)
                else np.nan
            ),
        })

    # -------------------------------------------------------------------------
    # Marginal normalized-tD support
    # -------------------------------------------------------------------------

    td_rows = []

    for j in range(args.td_bins):

        mask_dep = td_idx == j

        td_rows.append({
            "td_bin": j,
            "tnorm_low": td_edges[j],
            "tnorm_high": td_edges[j + 1],
            "canonical_fraction": float(canon_td_p[j]),
            "deployment_fraction": float(dep_td_p[j]),
            "deployment_to_canonical_ratio": (
                float(dep_td_p[j] / canon_td_p[j])
                if canon_td_p[j] > 0.0
                else np.inf
            ),
            "deployment_mean_abs_error": (
                float(np.mean(dep_abs_error[mask_dep]))
                if np.any(mask_dep)
                else np.nan
            ),
            "deployment_mean_signed_error": (
                float(np.mean(dep_error[mask_dep]))
                if np.any(mask_dep)
                else np.nan
            ),
        })

    # -------------------------------------------------------------------------
    # Joint support table
    # -------------------------------------------------------------------------

    joint_rows = []

    for i in range(args.xi_bins):
        for j in range(args.td_bins):

            dep_mask = (xi_idx == i) & (td_idx == j)

            if not np.any(dep_mask) and canon_hist2d[i, j] == 0:
                continue

            joint_rows.append({
                "xi_bin": i,
                "td_bin": j,
                "xi_low": xi_edges[i],
                "xi_high": xi_edges[i + 1],
                "tnorm_low": td_edges[j],
                "tnorm_high": td_edges[j + 1],
                "canonical_count": int(canon_hist2d[i, j]),
                "deployment_count": int(dep_hist2d[i, j]),
                "canonical_density": float(canon_density[i, j]),
                "deployment_density": float(dep_density[i, j]),
                "deployment_to_canonical_density_ratio": (
                    float(dep_density[i, j] / canon_density[i, j])
                    if canon_density[i, j] > 0.0
                    else np.inf
                ),
                "deployment_mean_abs_error": (
                    float(np.mean(dep_abs_error[dep_mask]))
                    if np.any(dep_mask)
                    else np.nan
                ),
                "deployment_mean_signed_error": (
                    float(np.mean(dep_error[dep_mask]))
                    if np.any(dep_mask)
                    else np.nan
                ),
            })

    # -------------------------------------------------------------------------
    # Error by canonical-density quantile
    # -------------------------------------------------------------------------

    positive_density = dep_canonical_density[dep_canonical_density > 0.0]

    if positive_density.size:
        q_edges = np.quantile(
            positive_density,
            [0.0, 0.10, 0.25, 0.50, 0.75, 0.90, 1.0],
        )
        q_edges = np.unique(q_edges)
    else:
        q_edges = np.array([0.0, 1.0])

    error_density_rows = []

    # Explicit zero-support bin.
    zero_mask = dep_canonical_density <= 0.0

    error_density_rows.append({
        "density_band": "zero_support",
        "samples": int(np.sum(zero_mask)),
        "sample_fraction": float(np.mean(zero_mask)),
        "canonical_density_min": 0.0,
        "canonical_density_max": 0.0,
        "mean_abs_error": (
            float(np.mean(dep_abs_error[zero_mask]))
            if np.any(zero_mask)
            else np.nan
        ),
        "mean_signed_error": (
            float(np.mean(dep_error[zero_mask]))
            if np.any(zero_mask)
            else np.nan
        ),
    })

    for k in range(len(q_edges) - 1):

        lo = q_edges[k]
        hi = q_edges[k + 1]

        if k == len(q_edges) - 2:
            mask = (
                (dep_canonical_density >= lo)
                &
                (dep_canonical_density <= hi)
                &
                (dep_canonical_density > 0.0)
            )
        else:
            mask = (
                (dep_canonical_density >= lo)
                &
                (dep_canonical_density < hi)
                &
                (dep_canonical_density > 0.0)
            )

        if not np.any(mask):
            continue

        error_density_rows.append({
            "density_band": f"Q{k+1}",
            "samples": int(np.sum(mask)),
            "sample_fraction": float(np.mean(mask)),
            "canonical_density_min": float(lo),
            "canonical_density_max": float(hi),
            "mean_abs_error": float(np.mean(dep_abs_error[mask])),
            "mean_signed_error": float(np.mean(dep_error[mask])),
        })

    # -------------------------------------------------------------------------
    # TOF-band density stress at 100 days
    # -------------------------------------------------------------------------

    idx100 = int(np.argmin(np.abs(times_days - 100.0)))

    if not np.isclose(times_days[idx100], 100.0):
        raise RuntimeError("100-day deployment snapshot not found.")

    error100 = pirnn[idx100] - truth[idx100]

    # 100d node-level density lookup.
    dep100_tnorm = np.broadcast_to(
        normalized_input[idx100, :, None],
        (n_streamlines, n_nodes),
    )

    dep100_xi = np.broadcast_to(
        deployment_xi[None, :],
        (n_streamlines, n_nodes),
    )

    xi_idx100 = bin_index(dep100_xi.ravel(), xi_edges)
    td_idx100 = bin_index(dep100_tnorm.ravel(), td_edges)

    density100 = canon_density[xi_idx100, td_idx100].reshape(
        n_streamlines,
        n_nodes,
    )

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

        dens = density100[sl_mask].ravel()
        err = error100[sl_mask].ravel()

        tof_rows.append({
            "TOF_band": label,
            "streamlines": int(np.sum(sl_mask)),
            "mean_canonical_density": float(np.mean(dens)),
            "median_canonical_density": float(np.median(dens)),
            "zero_support_fraction": float(np.mean(dens <= 0.0)),
            "mean_abs_error": float(np.mean(np.abs(err))),
            "mean_signed_error": float(np.mean(err)),
        })

    # -------------------------------------------------------------------------
    # Diagnosis
    # -------------------------------------------------------------------------

    low_density_error_high = False

    nonzero_density_rows = [
        row for row in error_density_rows
        if row["density_band"] != "zero_support"
        and np.isfinite(row["mean_abs_error"])
    ]

    if len(nonzero_density_rows) >= 2:
        first_err = nonzero_density_rows[0]["mean_abs_error"]
        last_err = nonzero_density_rows[-1]["mean_abs_error"]
        low_density_error_high = bool(first_err >= 1.25 * last_err)

    density_correlation_material = bool(
        np.isfinite(density_error_corr)
        and density_error_corr <= -0.25
    )

    joint_shift_material = bool(
        tv_joint >= 0.20
    )

    zero_support_material = bool(
        zero_support_fraction >= 0.05
    )

    marginal_td_shift_material = bool(
        tv_td >= 0.15
    )

    if (
        joint_shift_material
        and density_correlation_material
        and low_density_error_high
    ):
        diagnosis = "CANONICAL_SUPPORT_DENSITY_TRANSFER_MISMATCH"
        recommendation = (
            "SGSim deployment occupies materially different joint (xi, normalized-tD) "
            "support than the canonical training set, and deployment error rises as "
            "canonical density falls. Keep SG7B-11 frozen. Design a density-aware "
            "transfer/calibration mechanism or selectively enrich canonical support "
            "without retraining the front solution globally."
        )
        next_milestone = (
            "V15-SG7C-R3C — Density-Aware Frozen-Model Transfer Calibration Design"
        )

    elif zero_support_material:
        diagnosis = "CANONICAL_SUPPORT_HOLES_IN_SGSIM_DEPLOYMENT"
        recommendation = (
            "A material portion of SGSim deployment falls into joint input bins with "
            "zero canonical training occupancy. Map those support holes explicitly "
            "before any model correction."
        )
        next_milestone = (
            "V15-SG7C-R3C — Canonical Support-Hole Localization Audit"
        )

    elif marginal_td_shift_material and not density_correlation_material:
        diagnosis = "MARGINAL_TIME_DISTRIBUTION_SHIFT_WITHOUT_DENSITY_ERROR_LINK"
        recommendation = (
            "The normalized-time distribution differs from canonical training, but "
            "local canonical density does not strongly explain the residual error. "
            "Audit conditional feature construction and target scaling next."
        )
        next_milestone = (
            "V15-SG7C-R3C — Conditional Feature / Target-Scaling Transfer Audit"
        )

    else:
        diagnosis = "TRANSFER_MISMATCH_NOT_DOMINATED_BY_CANONICAL_SUPPORT_DENSITY"
        recommendation = (
            "Canonical support density alone does not explain the SGSim residual. "
            "Audit conditional feature semantics, saturation target normalization, "
            "and deployment-time feature construction before any further retraining."
        )
        next_milestone = (
            "V15-SG7C-R3C — Conditional Feature / Target-Scaling Transfer Audit"
        )

    # -------------------------------------------------------------------------
    # Save
    # -------------------------------------------------------------------------

    save_csv(GLOBAL_TABLE, global_rows)
    save_csv(XI_TABLE, xi_rows)
    save_csv(TD_TABLE, td_rows)
    save_csv(JOINT_TABLE, joint_rows)
    save_csv(ERROR_DENSITY_TABLE, error_density_rows)
    save_csv(TOF_DENSITY_TABLE, tof_rows)

    np.savez_compressed(
        NUMERICAL_FILE,
        xi_edges=xi_edges,
        td_edges=td_edges,
        canonical_hist2d=canon_hist2d,
        deployment_hist2d=dep_hist2d,
        canonical_density=canon_density,
        deployment_density=dep_density,
        deployment_sample_canonical_density=dep_canonical_density,
        deployment_abs_error=dep_abs_error,
        deployment_signed_error=dep_error,
    )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    plt.figure(figsize=(9, 6))
    plt.imshow(
        canon_density.T,
        origin="lower",
        aspect="auto",
        extent=[xi_edges[0], xi_edges[-1], td_edges[0], td_edges[-1]],
    )
    plt.xlabel("xi")
    plt.ylabel("Normalized tD")
    plt.title("V15-SG7C-R3B Canonical Joint Input Density")
    plt.colorbar(label="Canonical density")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3B_Canonical_Joint_Density.png",
        dpi=300,
    )
    plt.close()

    plt.figure(figsize=(9, 6))
    plt.imshow(
        dep_density.T,
        origin="lower",
        aspect="auto",
        extent=[xi_edges[0], xi_edges[-1], td_edges[0], td_edges[-1]],
    )
    plt.xlabel("xi")
    plt.ylabel("Normalized tD")
    plt.title("V15-SG7C-R3B SGSim Deployment Joint Input Density")
    plt.colorbar(label="Deployment density")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3B_Deployment_Joint_Density.png",
        dpi=300,
    )
    plt.close()

    plt.figure(figsize=(9, 6))
    plt.scatter(
        np.log10(dep_canonical_density + 1.0e-12),
        dep_abs_error,
        s=3,
        alpha=0.15,
    )
    plt.xlabel("log10 canonical joint density at deployment sample")
    plt.ylabel("|PI-RNN - SG7A|")
    plt.title("V15-SG7C-R3B Error vs Canonical Support Density")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3B_Error_vs_Canonical_Density.png",
        dpi=300,
    )
    plt.close()

    labels = [row["density_band"] for row in error_density_rows]
    values = [row["mean_abs_error"] for row in error_density_rows]

    plt.figure(figsize=(9, 5))
    plt.bar(labels, values)
    plt.xlabel("Canonical-density band")
    plt.ylabel("Deployment mean absolute error")
    plt.title("V15-SG7C-R3B Error by Canonical-Density Quantile")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7CR3B_Error_By_Density_Quantile.png",
        dpi=300,
    )
    plt.close()

    # -------------------------------------------------------------------------
    # Print
    # -------------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("GLOBAL SUPPORT COMPARISON")
    print("=" * 78)
    print(f"Canonical samples           : {canonical_xi.size:,}")
    print(f"Deployment samples          : {dep_xi.size:,}")
    print(f"TV distance xi              : {tv_xi:.6f}")
    print(f"TV distance normalized tD   : {tv_td:.6f}")
    print(f"TV distance joint xi/tD     : {tv_joint:.6f}")
    print(f"Zero canonical support frac : {100.0*zero_support_fraction:.3f}%")
    print(f"Canonical count <=1 frac    : {100.0*sparse_1_fraction:.3f}%")
    print(f"Canonical count <=5 frac    : {100.0*sparse_5_fraction:.3f}%")
    print(f"corr(log density, |error|)  : {density_error_corr:.6f}")
    print(f"corr(log density, error)    : {density_signed_corr:.6f}")

    print("\nTOF-BAND DENSITY STRESS @100d")
    for row in tof_rows:
        print(
            f"  {row['TOF_band']:<12s} | "
            f"density={row['mean_canonical_density']:.3e} | "
            f"zero={100*row['zero_support_fraction']:.2f}% | "
            f"L1={row['mean_abs_error']:.3e} | "
            f"bias={row['mean_signed_error']:.3e}"
        )

    print("\n" + "=" * 78)
    print("V15-SG7C-R3B DIAGNOSTIC VALIDATION")
    print("=" * 78)
    print("[PASS] SG7C-R3A transfer-mismatch diagnosis reproduced")
    print("[PASS] Canonical training inputs loaded")
    print("[PASS] SGSim deployment inputs reconstructed")
    print("[PASS] Common xi / normalized-tD support grid constructed")
    print("[PASS] Marginal support comparison completed")
    print("[PASS] Joint support-density comparison completed")
    print("[PASS] Error-vs-density relationship established")
    print("[PASS] TOF-band density stress established")
    print("[PASS] Diagnostic classification established")
    print("=" * 78)

    print("\nDIAGNOSTIC FLAGS")
    print(f"  Joint support shift material : {joint_shift_material}")
    print(f"  Marginal tD shift material  : {marginal_td_shift_material}")
    print(f"  Zero-support material       : {zero_support_material}")
    print(f"  Density-error correlation   : {density_correlation_material}")
    print(f"  Low-density error elevated  : {low_density_error_high}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    summary = {
        "milestone": "V15-SG7C-R3B",
        "status": "CANONICAL_VS_SGSIM_TRANSFER_DENSITY_AUDIT_COMPLETE",
        "incoming_diagnosis": r3a.get("diagnosis"),
        "diagnosis": diagnosis,
        "TV_distance_xi": tv_xi,
        "TV_distance_normalized_tD": tv_td,
        "TV_distance_joint_xi_tD": tv_joint,
        "zero_support_fraction": zero_support_fraction,
        "sparse_count_le_1_fraction": sparse_1_fraction,
        "sparse_count_le_5_fraction": sparse_5_fraction,
        "corr_log_density_abs_error": density_error_corr,
        "corr_log_density_signed_error": density_signed_corr,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(SUMMARY_FILE, summary)

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")
    print("\nTables:")
    print(f"  {GLOBAL_TABLE.name}")
    print(f"  {XI_TABLE.name}")
    print(f"  {TD_TABLE.name}")
    print(f"  {JOINT_TABLE.name}")
    print(f"  {ERROR_DENSITY_TABLE.name}")
    print(f"  {TOF_DENSITY_TABLE.name}")
    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")
    print("\nDiagnostics:")
    print("  V15SG7CR3B_Canonical_Joint_Density.png")
    print("  V15SG7CR3B_Deployment_Joint_Density.png")
    print("  V15SG7CR3B_Error_vs_Canonical_Density.png")
    print("  V15SG7CR3B_Error_By_Density_Quantile.png")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3B AUDIT: PASS")
    print()
    print("No training was performed.")
    print("No model, coordinate, map-back, or validation gate was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
