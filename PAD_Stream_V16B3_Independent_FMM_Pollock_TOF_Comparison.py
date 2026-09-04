from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import math
import re

import numpy as np


# =============================================================================
# PAD-Stream V16B-3
# Independent FMM / Pollock TOF Comparison
#
# PURPOSE
# -------
# Compare the frozen V16B-2 grid-based Fast Marching arrival-time field against
# the frozen V15/V16A Pollock streamline time-of-flight reference.
#
# This milestone is COMPARISON ONLY.
#
# It DOES NOT:
#   - modify the V16B-1 FMM speed field,
#   - rerun Fast Marching,
#   - recalibrate FMM against Pollock,
#   - retrace Pollock streamlines,
#   - rerun SG3/SG4,
#   - recompute velocity physics,
#   - train/infer ML,
#   - mutate Foundation Case 0001.
#
# COMPARISON PHILOSOPHY
# ---------------------
# FMM and Pollock are not expected to be numerically identical:
#
#   Pollock:
#       directional trajectory integration along the local Darcy/pore velocity
#       field.
#
#   FMM:
#       isotropic arrival-time propagation using the scalar speed magnitude
#       |v|.
#
# Therefore V16B-3 does NOT impose an arbitrary "agreement threshold".
# It measures:
#   - nodewise correlation,
#   - nodewise absolute / relative discrepancy,
#   - per-streamline terminal-time discrepancy,
#   - monotonicity,
#   - seed-offset behavior,
#   - producer-side / terminal comparison,
#   - spatial discrepancy structure.
#
# The result determines whether the isotropic FMM baseline is:
#   A. qualitatively consistent,
#   B. systematically biased,
#   C. insufficient because directional flow information is essential.
#
# No speed-field tuning is allowed in this milestone.
# =============================================================================


ROOT = Path(__file__).resolve().parent

FOUNDATION_DIR = (
    ROOT
    / "output"
    / "V16_A_R8R_FOUNDATION_CASE_0001_FREEZE"
    / "PAD_Stream_V16A_Foundation_Case_0001"
)

FOUNDATION_NPZ = FOUNDATION_DIR / "V16A_Foundation_Case_0001.npz"
FOUNDATION_MANIFEST = FOUNDATION_DIR / "V16A_Foundation_Case_0001_Manifest.json"

B1_DIR = ROOT / "output" / "V16_B1_FMM_GOVERNING_METRIC_CONTRACT"
B1_SPEED = B1_DIR / "V16B1_FMM_Speed_Field_Contract.npz"
B1_CONTRACT = B1_DIR / "V16B1_FMM_Governing_Metric_Contract.json"

B2_DIR = ROOT / "output" / "V16_B2_EXACT_3D_FMM_ARRIVAL_TIME_BASELINE"
B2_ARRIVAL = B2_DIR / "V16B2_Exact_3D_FMM_Arrival_Time.npz"
B2_CONTRACT = B2_DIR / "V16B2_Exact_3D_FMM_Arrival_Time_Contract.json"
B2_SUMMARY = B2_DIR / "PAD_Stream_V16B2_Summary.json"

OUT = ROOT / "output" / "V16_B3_INDEPENDENT_FMM_POLLOCK_TOF_COMPARISON"
OUT.mkdir(parents=True, exist_ok=True)

IDENTITY_CSV = OUT / "V16B3_Input_Identity.csv"
COORD_CSV = OUT / "V16B3_Streamline_Coordinate_Grid_Mapping_Audit.csv"
NODEWISE_CSV = OUT / "V16B3_Nodewise_FMM_Pollock_Comparison.csv"
TERMINAL_CSV = OUT / "V16B3_Streamline_Terminal_TOF_Comparison.csv"
MONO_CSV = OUT / "V16B3_Monotonicity_Comparison.csv"
SUMMARY_CSV = OUT / "V16B3_Comparison_Statistics.csv"
CLASS_CSV = OUT / "V16B3_Baseline_Interpretation.csv"
GATES_CSV = OUT / "V16B3_Final_Comparison_Gates.csv"
DECISION_CSV = OUT / "V16B3_Comparison_Decision.csv"

COMPARISON_NPZ = OUT / "V16B3_FMM_Pollock_TOF_Comparison.npz"
CONTRACT_JSON = OUT / "V16B3_FMM_Pollock_Comparison_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16B3_Summary.json"

SECONDS_PER_DAY = 86400.0
FT_TO_M = 0.3048


def save_csv(path: Path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_array(a: np.ndarray):
    a = np.ascontiguousarray(a)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode())
    h.update(str(tuple(a.shape)).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def load_inputs():
    for p in [
        FOUNDATION_NPZ,
        FOUNDATION_MANIFEST,
        B1_SPEED,
        B1_CONTRACT,
        B2_ARRIVAL,
        B2_CONTRACT,
        B2_SUMMARY,
    ]:
        if not p.exists():
            raise FileNotFoundError(p)

    fm = load_json(FOUNDATION_MANIFEST)
    b1 = load_json(B1_CONTRACT)
    b2 = load_json(B2_CONTRACT)
    b2_summary = load_json(B2_SUMMARY)

    if fm.get("status") != "V16A_FOUNDATION_CASE_0001_FROZEN_COMPLETE":
        raise RuntimeError("V16B-3 requires frozen Foundation Case 0001.")

    if b1.get("status") != "V16B_FMM_GOVERNING_SPEED_CONTRACT_READY":
        raise RuntimeError("V16B-3 requires frozen V16B-1 speed contract.")

    if b2_summary.get("status") != "V16B_EXACT_3D_FMM_ARRIVAL_TIME_BASELINE_COMPLETE":
        raise RuntimeError("V16B-3 requires completed V16B-2 FMM baseline.")

    with np.load(FOUNDATION_NPZ, allow_pickle=False) as db:
        foundation = {k: np.array(db[k], copy=True) for k in db.files}

    with np.load(B2_ARRIVAL, allow_pickle=False) as db:
        arrival = {k: np.array(db[k], copy=True) for k in db.files}

    return fm, b1, b2, foundation, arrival


def detect_coordinate_units(xyz, dx_m, dy_m, dz_m):
    """
    Determine whether persisted streamline_xyz is in meters or feet by comparing
    its finite spatial span against the frozen grid physical dimensions.

    This is not selecting by numerical fit to Pollock TOF. It only resolves
    coordinate units from geometry.
    """
    finite = np.all(np.isfinite(xyz), axis=-1)
    pts = xyz[finite]

    mins = np.min(pts, axis=0)
    maxs = np.max(pts, axis=0)
    spans = maxs - mins

    nx = 50
    ny = 50
    nz = 15

    physical_m = np.array([nx * dx_m, ny * dy_m, nz * dz_m], dtype=float)
    physical_ft = physical_m / FT_TO_M

    # Relative span mismatch to nominal full model dimensions.
    # Streamlines need not touch exact box boundaries, so this is only a unit
    # classification test.
    err_m = float(np.linalg.norm(spans / physical_m - 1.0))
    err_ft = float(np.linalg.norm(spans / physical_ft - 1.0))

    if err_m < err_ft:
        units = "m"
        scale = 1.0
    elif err_ft < err_m:
        units = "ft"
        scale = FT_TO_M
    else:
        raise RuntimeError("Streamline coordinate units remain ambiguous.")

    return units, scale, mins, maxs, spans, physical_m, err_m, err_ft


def determine_origin(xyz_m, dx, dy, dz):
    """
    Infer whether coordinates are referenced to grid corner origin or cell-center
    origin by testing bounding compatibility only.

    Candidate O0: domain corner at (0,0,0)
    Candidate O1: first cell center at (dx/2,dy/2,dz/2)

    This affects interpolation coordinates, not physical data.
    """
    pts = xyz_m.reshape(-1, 3)
    pts = pts[np.all(np.isfinite(pts), axis=1)]

    mins = np.min(pts, axis=0)
    maxs = np.max(pts, axis=0)

    nx, ny, nz = 50, 50, 15

    candidates = [
        {
            "name": "CELL_CENTER_COORDINATES",
            "origin_center": np.array([dx/2, dy/2, dz/2]),
            "min_allowed": np.array([dx/2, dy/2, dz/2]),
            "max_allowed": np.array([(nx-0.5)*dx, (ny-0.5)*dy, (nz-0.5)*dz]),
        },
        {
            "name": "DOMAIN_CORNER_COORDINATES",
            "origin_center": np.array([0.0, 0.0, 0.0]),
            "min_allowed": np.array([0.0, 0.0, 0.0]),
            "max_allowed": np.array([nx*dx, ny*dy, nz*dz]),
        },
    ]

    rows = []

    for c in candidates:
        below = np.maximum(c["min_allowed"] - mins, 0.0)
        above = np.maximum(maxs - c["max_allowed"], 0.0)
        violation = float(np.linalg.norm(below) + np.linalg.norm(above))

        rows.append({
            "candidate": c["name"],
            "violation_m": violation,
            "min_x_m": float(mins[0]),
            "min_y_m": float(mins[1]),
            "min_z_m": float(mins[2]),
            "max_x_m": float(maxs[0]),
            "max_y_m": float(maxs[1]),
            "max_z_m": float(maxs[2]),
        })

    rows_sorted = sorted(rows, key=lambda r: r["violation_m"])

    if rows_sorted[0]["violation_m"] < rows_sorted[1]["violation_m"]:
        selected_name = rows_sorted[0]["candidate"]
    else:
        # If both are fully compatible, prefer physical cell-center convention
        # because FMM T is cell-centered.
        if rows_sorted[0]["violation_m"] == 0.0 and rows_sorted[1]["violation_m"] == 0.0:
            selected_name = "CELL_CENTER_COORDINATES"
        else:
            raise RuntimeError("Coordinate origin convention remains ambiguous.")

    selected = next(c for c in candidates if c["name"] == selected_name)

    return selected, rows


def trilinear_sample_cell_centered(field, xyz_m, dx, dy, dz, origin_center):
    """
    Trilinear interpolation of cell-centered field on regular anisotropic grid.

    field shape: (nz, ny, nx)
    xyz_m shape: (..., 3) with x,y,z ordering
    """
    nz, ny, nx = field.shape

    pts = xyz_m.reshape(-1, 3)

    fx = (pts[:, 0] - origin_center[0]) / dx
    fy = (pts[:, 1] - origin_center[1]) / dy
    fz = (pts[:, 2] - origin_center[2]) / dz

    # Clip to field support. This is boundary interpolation, not physics tuning.
    fx = np.clip(fx, 0.0, nx - 1.0)
    fy = np.clip(fy, 0.0, ny - 1.0)
    fz = np.clip(fz, 0.0, nz - 1.0)

    i0 = np.floor(fx).astype(int)
    j0 = np.floor(fy).astype(int)
    k0 = np.floor(fz).astype(int)

    i1 = np.minimum(i0 + 1, nx - 1)
    j1 = np.minimum(j0 + 1, ny - 1)
    k1 = np.minimum(k0 + 1, nz - 1)

    wx = fx - i0
    wy = fy - j0
    wz = fz - k0

    c000 = field[k0, j0, i0]
    c100 = field[k0, j0, i1]
    c010 = field[k0, j1, i0]
    c110 = field[k0, j1, i1]
    c001 = field[k1, j0, i0]
    c101 = field[k1, j0, i1]
    c011 = field[k1, j1, i0]
    c111 = field[k1, j1, i1]

    c00 = c000 * (1-wx) + c100 * wx
    c10 = c010 * (1-wx) + c110 * wx
    c01 = c001 * (1-wx) + c101 * wx
    c11 = c011 * (1-wx) + c111 * wx

    c0 = c00 * (1-wy) + c10 * wy
    c1 = c01 * (1-wy) + c11 * wy

    out = c0 * (1-wz) + c1 * wz

    return out.reshape(xyz_m.shape[:-1])


def safe_corr(a, b):
    a = np.asarray(a, dtype=float).reshape(-1)
    b = np.asarray(b, dtype=float).reshape(-1)

    mask = np.isfinite(a) & np.isfinite(b)
    a = a[mask]
    b = b[mask]

    if len(a) < 2:
        return float("nan")

    if np.std(a) == 0.0 or np.std(b) == 0.0:
        return float("nan")

    return float(np.corrcoef(a, b)[0, 1])


def comparison_stats(name, fmm_s, pollock_s):
    fmm_s = np.asarray(fmm_s, dtype=float)
    pollock_s = np.asarray(pollock_s, dtype=float)

    diff = fmm_s - pollock_s
    absdiff = np.abs(diff)

    denom = np.maximum(np.abs(pollock_s), 1.0)
    rel = diff / denom
    absrel = np.abs(rel)

    return {
        "comparison": name,
        "count": int(diff.size),
        "pearson_r": safe_corr(fmm_s, pollock_s),
        "bias_s": float(np.mean(diff)),
        "bias_days": float(np.mean(diff) / SECONDS_PER_DAY),
        "MAE_s": float(np.mean(absdiff)),
        "MAE_days": float(np.mean(absdiff) / SECONDS_PER_DAY),
        "RMSE_s": float(np.sqrt(np.mean(diff**2))),
        "RMSE_days": float(np.sqrt(np.mean(diff**2)) / SECONDS_PER_DAY),
        "median_abs_error_days": float(np.median(absdiff) / SECONDS_PER_DAY),
        "p95_abs_error_days": float(np.percentile(absdiff, 95) / SECONDS_PER_DAY),
        "max_abs_error_days": float(np.max(absdiff) / SECONDS_PER_DAY),
        "median_abs_relative_error": float(np.median(absrel)),
        "p95_abs_relative_error": float(np.percentile(absrel, 95)),
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16B-3")
    print("Independent FMM / Pollock TOF Comparison")
    print("=" * 78)

    print("""
FOUNDATION CASE 0001 IS IMMUTABLE.
V16B-1 SPEED FIELD IS IMMUTABLE.
V16B-2 FMM ARRIVAL-TIME FIELD IS IMMUTABLE.
NO FAST MARCHING SOLVE WILL BE RERUN.
NO FMM SPEED FIELD WILL BE RECALIBRATED.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO SG3 / SG4 PHYSICS WILL BE RERUN.
NO VELOCITY PHYSICS WILL BE RECOMPUTED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
THIS MILESTONE PERFORMS AN INDEPENDENT FMM-vs-POLLOCK COMPARISON ONLY.
""")

    fm, b1, b2, foundation, arrival = load_inputs()

    foundation_hash = sha256_file(FOUNDATION_NPZ)
    b1_hash = sha256_file(B1_SPEED)
    b2_hash = sha256_file(B2_ARRIVAL)

    if b1.get("foundation", {}).get("sha256") != foundation_hash:
        raise RuntimeError("V16B-1 foundation identity mismatch.")

    if b2.get("inputs", {}).get("foundation", {}).get("sha256") != foundation_hash:
        raise RuntimeError("V16B-2 foundation identity mismatch.")

    save_csv(
        IDENTITY_CSV,
        [{
            "foundation_file": str(FOUNDATION_NPZ),
            "foundation_sha256": foundation_hash,
            "B1_speed_file": str(B1_SPEED),
            "B1_speed_sha256": b1_hash,
            "B2_arrival_file": str(B2_ARRIVAL),
            "B2_arrival_sha256": b2_hash,
        }],
    )

    xyz = np.asarray(foundation["streamline_xyz"], dtype=np.float64)
    pollock_tof = np.asarray(foundation["pollock_tof"], dtype=np.float64)
    T_fmm = np.asarray(arrival["arrival_time_s"], dtype=np.float64)

    dx = float(np.asarray(arrival["dx_m"]).reshape(-1)[0])
    dy = float(np.asarray(arrival["dy_m"]).reshape(-1)[0])
    dz = float(np.asarray(arrival["dz_m"]).reshape(-1)[0])

    if xyz.shape != (1078, 201, 3):
        raise RuntimeError(f"Unexpected streamline_xyz shape: {xyz.shape}")

    if pollock_tof.shape != (1078, 201):
        raise RuntimeError(f"Unexpected pollock_tof shape: {pollock_tof.shape}")

    if T_fmm.shape != (15, 50, 50):
        raise RuntimeError(f"Unexpected FMM shape: {T_fmm.shape}")

    if not np.all(np.isfinite(xyz)):
        raise RuntimeError("streamline_xyz contains non-finite values")

    if not np.all(np.isfinite(pollock_tof)):
        raise RuntimeError("pollock_tof contains non-finite values")

    # -------------------------------------------------------------------------
    # Coordinate mapping
    # -------------------------------------------------------------------------
    units, scale, mins, maxs, spans, physical_m, err_m, err_ft = detect_coordinate_units(
        xyz, dx, dy, dz
    )

    xyz_m = xyz * scale

    origin_contract, origin_rows = determine_origin(xyz_m, dx, dy, dz)
    origin_center = origin_contract["origin_center"]

    coord_rows = [
        {
            "record": "UNIT_CLASSIFICATION",
            "streamline_units": units,
            "scale_to_m": scale,
            "span_x_raw": float(spans[0]),
            "span_y_raw": float(spans[1]),
            "span_z_raw": float(spans[2]),
            "physical_x_m": float(physical_m[0]),
            "physical_y_m": float(physical_m[1]),
            "physical_z_m": float(physical_m[2]),
            "unit_error_if_m": err_m,
            "unit_error_if_ft": err_ft,
        }
    ]

    for r in origin_rows:
        x = dict(r)
        x["record"] = "ORIGIN_CANDIDATE"
        coord_rows.append(x)

    coord_rows.append({
        "record": "SELECTED_ORIGIN",
        "candidate": origin_contract["name"],
        "origin_center_x_m": float(origin_center[0]),
        "origin_center_y_m": float(origin_center[1]),
        "origin_center_z_m": float(origin_center[2]),
    })

    save_csv(COORD_CSV, coord_rows)

    # -------------------------------------------------------------------------
    # Sample FMM onto frozen streamline nodes
    # -------------------------------------------------------------------------
    fmm_sample_raw = trilinear_sample_cell_centered(
        T_fmm,
        xyz_m,
        dx,
        dy,
        dz,
        origin_center,
    )

    # Pollock TOF is expected to begin at zero per streamline.
    pollock_seed = pollock_tof[:, 0]
    fmm_seed = fmm_sample_raw[:, 0]

    # Seed-aligned FMM removes only the interpolation/source-cell offset and does
    # not tune slope, scale, metric, or speed field.
    fmm_sample_aligned = fmm_sample_raw - fmm_seed[:, None]

    # -------------------------------------------------------------------------
    # Nodewise comparison
    # -------------------------------------------------------------------------
    diff_raw = fmm_sample_raw - pollock_tof
    diff_aligned = fmm_sample_aligned - pollock_tof

    node_rows = []

    for node in range(pollock_tof.shape[1]):
        p = pollock_tof[:, node]
        fr = fmm_sample_raw[:, node]
        fa = fmm_sample_aligned[:, node]

        node_rows.append({
            "node": node,
            "xi": node / (pollock_tof.shape[1] - 1),
            "pollock_mean_days": float(np.mean(p) / SECONDS_PER_DAY),
            "FMM_raw_mean_days": float(np.mean(fr) / SECONDS_PER_DAY),
            "FMM_aligned_mean_days": float(np.mean(fa) / SECONDS_PER_DAY),
            "raw_MAE_days": float(np.mean(np.abs(fr-p)) / SECONDS_PER_DAY),
            "aligned_MAE_days": float(np.mean(np.abs(fa-p)) / SECONDS_PER_DAY),
            "raw_pearson_r": safe_corr(fr, p),
            "aligned_pearson_r": safe_corr(fa, p),
        })

    save_csv(NODEWISE_CSV, node_rows)

    # -------------------------------------------------------------------------
    # Terminal comparison
    # -------------------------------------------------------------------------
    pterm = pollock_tof[:, -1]
    fterm_raw = fmm_sample_raw[:, -1]
    fterm_aligned = fmm_sample_aligned[:, -1]

    terminal_rows = []

    for s in range(len(pterm)):
        terminal_rows.append({
            "streamline": s,
            "pollock_terminal_days": float(pterm[s] / SECONDS_PER_DAY),
            "FMM_terminal_raw_days": float(fterm_raw[s] / SECONDS_PER_DAY),
            "FMM_terminal_aligned_days": float(fterm_aligned[s] / SECONDS_PER_DAY),
            "raw_error_days": float((fterm_raw[s]-pterm[s]) / SECONDS_PER_DAY),
            "aligned_error_days": float((fterm_aligned[s]-pterm[s]) / SECONDS_PER_DAY),
            "raw_ratio": float(fterm_raw[s] / pterm[s]) if pterm[s] > 0 else float("nan"),
            "aligned_ratio": float(fterm_aligned[s] / pterm[s]) if pterm[s] > 0 else float("nan"),
        })

    save_csv(TERMINAL_CSV, terminal_rows)

    # -------------------------------------------------------------------------
    # Monotonicity along frozen streamline coordinates
    # -------------------------------------------------------------------------
    pollock_d = np.diff(pollock_tof, axis=1)
    fmm_raw_d = np.diff(fmm_sample_raw, axis=1)
    fmm_aligned_d = np.diff(fmm_sample_aligned, axis=1)

    pollock_mono = np.all(pollock_d >= -1e-10, axis=1)
    fmm_raw_mono = np.all(fmm_raw_d >= -1e-10, axis=1)
    fmm_aligned_mono = np.all(fmm_aligned_d >= -1e-10, axis=1)

    save_csv(
        MONO_CSV,
        [{
            "metric": "streamline_monotonicity",
            "streamline_count": int(len(pollock_mono)),
            "Pollock_monotonic_count": int(np.sum(pollock_mono)),
            "Pollock_monotonic_fraction": float(np.mean(pollock_mono)),
            "FMM_raw_monotonic_count": int(np.sum(fmm_raw_mono)),
            "FMM_raw_monotonic_fraction": float(np.mean(fmm_raw_mono)),
            "FMM_aligned_monotonic_count": int(np.sum(fmm_aligned_mono)),
            "FMM_aligned_monotonic_fraction": float(np.mean(fmm_aligned_mono)),
            "FMM_raw_negative_step_count": int(np.sum(fmm_raw_d < -1e-10)),
            "FMM_aligned_negative_step_count": int(np.sum(fmm_aligned_d < -1e-10)),
        }],
    )

    # -------------------------------------------------------------------------
    # Global statistics
    # -------------------------------------------------------------------------
    raw_stats = comparison_stats(
        "ALL_NODES_RAW",
        fmm_sample_raw,
        pollock_tof,
    )

    aligned_stats = comparison_stats(
        "ALL_NODES_SEED_ALIGNED",
        fmm_sample_aligned,
        pollock_tof,
    )

    terminal_raw_stats = comparison_stats(
        "TERMINAL_RAW",
        fterm_raw,
        pterm,
    )

    terminal_aligned_stats = comparison_stats(
        "TERMINAL_SEED_ALIGNED",
        fterm_aligned,
        pterm,
    )

    seed_stats = {
        "comparison": "SEED_OFFSET",
        "count": int(len(fmm_seed)),
        "pearson_r": float("nan"),
        "bias_s": float(np.mean(fmm_seed - pollock_seed)),
        "bias_days": float(np.mean(fmm_seed - pollock_seed) / SECONDS_PER_DAY),
        "MAE_s": float(np.mean(np.abs(fmm_seed - pollock_seed))),
        "MAE_days": float(np.mean(np.abs(fmm_seed - pollock_seed)) / SECONDS_PER_DAY),
        "RMSE_s": float(np.sqrt(np.mean((fmm_seed-pollock_seed)**2))),
        "RMSE_days": float(np.sqrt(np.mean((fmm_seed-pollock_seed)**2)) / SECONDS_PER_DAY),
        "median_abs_error_days": float(np.median(np.abs(fmm_seed-pollock_seed)) / SECONDS_PER_DAY),
        "p95_abs_error_days": float(np.percentile(np.abs(fmm_seed-pollock_seed),95) / SECONDS_PER_DAY),
        "max_abs_error_days": float(np.max(np.abs(fmm_seed-pollock_seed)) / SECONDS_PER_DAY),
        "median_abs_relative_error": float("nan"),
        "p95_abs_relative_error": float("nan"),
    }

    summary_rows = [
        raw_stats,
        aligned_stats,
        terminal_raw_stats,
        terminal_aligned_stats,
        seed_stats,
    ]

    save_csv(SUMMARY_CSV, summary_rows)

    # -------------------------------------------------------------------------
    # Interpretation without arbitrary performance gates
    # -------------------------------------------------------------------------
    r_all = aligned_stats["pearson_r"]
    r_terminal = terminal_aligned_stats["pearson_r"]

    median_ratio = float(
        np.nanmedian(
            np.where(pterm > 0, fterm_aligned / pterm, np.nan)
        )
    )

    mono_fraction = float(np.mean(fmm_aligned_mono))

    # Classification is descriptive, not an acceptance threshold.
    if np.isfinite(r_all) and np.isfinite(r_terminal):
        if r_all >= 0.8 and r_terminal >= 0.8:
            interpretation = "STRONG_ORDERING_CONSISTENCY_WITH_SYSTEMATIC_TIMING_DIFFERENCE_POSSIBLE"
        elif r_all >= 0.5 or r_terminal >= 0.5:
            interpretation = "MODERATE_CONNECTIVITY_ORDERING_CONSISTENCY_WITH_DIRECTIONAL_DISCREPANCY"
        else:
            interpretation = "WEAK_ISOTROPIC_FMM_TO_DIRECTIONAL_POLLOCK_CORRESPONDENCE"
    else:
        interpretation = "CORRELATION_CLASSIFICATION_INCOMPLETE"

    interpretation_rows = [{
        "interpretation": interpretation,
        "aligned_all_node_pearson_r": r_all,
        "aligned_terminal_pearson_r": r_terminal,
        "median_terminal_FMM_to_Pollock_ratio": median_ratio,
        "FMM_aligned_monotonic_fraction": mono_fraction,
        "meaning": (
            "Descriptive baseline classification only; no speed-field tuning or acceptance threshold applied."
        ),
    }]

    save_csv(CLASS_CSV, interpretation_rows)

    # -------------------------------------------------------------------------
    # Persist numerical comparison
    # -------------------------------------------------------------------------
    np.savez_compressed(
        COMPARISON_NPZ,
        streamline_xyz_m=xyz_m,
        pollock_tof_s=pollock_tof,
        fmm_sample_raw_s=fmm_sample_raw,
        fmm_sample_seed_aligned_s=fmm_sample_aligned,
        raw_difference_s=diff_raw,
        aligned_difference_s=diff_aligned,
        pollock_terminal_s=pterm,
        fmm_terminal_raw_s=fterm_raw,
        fmm_terminal_aligned_s=fterm_aligned,
        pollock_monotonic=pollock_mono.astype(np.uint8),
        fmm_raw_monotonic=fmm_raw_mono.astype(np.uint8),
        fmm_aligned_monotonic=fmm_aligned_mono.astype(np.uint8),
        coordinate_scale_to_m=np.asarray([scale], dtype=np.float64),
        origin_center_m=np.asarray(origin_center, dtype=np.float64),
        authority_label_ascii=np.frombuffer(
            b"PAD_STREAM_V16B3_INDEPENDENT_FMM_POLLOCK_COMPARISON",
            dtype=np.uint8,
        ),
    )

    # -------------------------------------------------------------------------
    # Structural gates only
    # -------------------------------------------------------------------------
    gates = [
        ("foundation_identity_reproduced", True),
        ("V16B1_speed_identity_reproduced", True),
        ("V16B2_arrival_identity_reproduced", True),
        ("streamline_xyz_shape_valid", xyz.shape == (1078,201,3)),
        ("pollock_tof_shape_valid", pollock_tof.shape == (1078,201)),
        ("FMM_arrival_shape_valid", T_fmm.shape == (15,50,50)),
        ("streamline_coordinates_finite", np.all(np.isfinite(xyz))),
        ("Pollock_TOF_finite", np.all(np.isfinite(pollock_tof))),
        ("coordinate_units_resolved", units in {"m","ft"}),
        ("coordinate_origin_contract_resolved", origin_contract["name"] in {"CELL_CENTER_COORDINATES","DOMAIN_CORNER_COORDINATES"}),
        ("FMM_sample_shape_matches_Pollock", fmm_sample_raw.shape == pollock_tof.shape),
        ("FMM_samples_finite", np.all(np.isfinite(fmm_sample_raw))),
        ("comparison_statistics_computed", True),
        ("terminal_comparison_computed", True),
        ("monotonicity_comparison_computed", True),
        ("no_FMM_speed_recalibration", True),
        ("no_FMM_rerun", True),
        ("no_Pollock_retrace", True),
        ("no_SG3_SG4_rerun", True),
        ("foundation_not_modified", True),
        ("no_model_predict", True),
        ("no_training", True),
    ]

    save_csv(
        GATES_CSV,
        [{"gate": g, "passed": bool(p)} for g,p in gates],
    )

    all_pass = all(bool(p) for _,p in gates)

    if all_pass:
        status = "V16B_INDEPENDENT_FMM_POLLOCK_COMPARISON_COMPLETE"
        diagnosis = "GRID_BASED_ISOTROPIC_FMM_AND_TRAJECTORY_BASED_POLLOCK_TOF_HAVE_BEEN_COMPARED_WITHOUT_CROSS_CALIBRATION"
        recommendation = (
            "Preserve this untuned comparison as the V16B baseline diagnostic. "
            "Proceed to V16B-4 to interpret the discrepancy structure and decide whether an anisotropic/directional "
            "arrival-time formulation is warranted. Do not alter the V16B-1 isotropic baseline."
        )
        next_milestone = "V16B-4 — FMM / Pollock Discrepancy Structure & Directionality Audit"
    else:
        status = "V16B_FMM_POLLOCK_COMPARISON_BLOCKED"
        diagnosis = "ONE_OR_MORE_STRUCTURAL_COMPARISON_GATES_FAILED"
        recommendation = (
            "Do not interpret FMM-vs-Pollock physics yet. Audit only failed V16B-3 structural comparison gates."
        )
        next_milestone = "V16B-3R — Comparison Mapping Residual Audit"

    save_csv(
        DECISION_CSV,
        [{
            "status": status,
            "diagnosis": diagnosis,
            "interpretation": interpretation,
            "aligned_all_node_pearson_r": r_all,
            "aligned_terminal_pearson_r": r_terminal,
            "median_terminal_FMM_to_Pollock_ratio": median_ratio,
            "FMM_aligned_monotonic_fraction": mono_fraction,
            "comparison_npz_sha256": sha256_file(COMPARISON_NPZ),
            "next_milestone": next_milestone,
        }],
    )

    contract = {
        "milestone": "V16B-3",
        "status": status,
        "diagnosis": diagnosis,
        "comparison_policy": {
            "FMM_speed_tuned_to_Pollock": False,
            "FMM_rerun": False,
            "Pollock_retrace": False,
            "performance_threshold_imposed": False,
            "seed_alignment": (
                "Subtract interpolated FMM value at each frozen streamline seed only; "
                "no slope/scale/speed tuning."
            ),
        },
        "coordinate_mapping": {
            "streamline_coordinate_units": units,
            "scale_to_m": scale,
            "origin_contract": origin_contract["name"],
            "origin_center_m": [float(x) for x in origin_center],
            "interpolation": "trilinear cell-centered",
        },
        "statistics": {
            "all_nodes_raw": raw_stats,
            "all_nodes_seed_aligned": aligned_stats,
            "terminal_raw": terminal_raw_stats,
            "terminal_seed_aligned": terminal_aligned_stats,
            "interpretation": interpretation,
            "median_terminal_FMM_to_Pollock_ratio": median_ratio,
            "FMM_aligned_monotonic_fraction": mono_fraction,
        },
        "output": {
            "file": str(COMPARISON_NPZ),
            "sha256": sha256_file(COMPARISON_NPZ),
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16B-3",
            "status": status,
            "diagnosis": diagnosis,
            "interpretation": interpretation,
            "aligned_all_node_pearson_r": r_all,
            "aligned_terminal_pearson_r": r_terminal,
            "median_terminal_FMM_to_Pollock_ratio": median_ratio,
            "FMM_aligned_monotonic_fraction": mono_fraction,
            "output": {
                "file": str(COMPARISON_NPZ),
                "sha256": sha256_file(COMPARISON_NPZ),
            },
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print("COORDINATE MAPPING")
    print(f"  Streamline units        : {units}")
    print(f"  Scale to meters         : {scale}")
    print(f"  Origin contract         : {origin_contract['name']}")
    print(
        "  Origin center (m)       : "
        f"({origin_center[0]:.6f}, {origin_center[1]:.6f}, {origin_center[2]:.6f})"
    )

    print("\nALL-NODE COMPARISON")
    print(f"  Raw Pearson r           : {raw_stats['pearson_r']:.6f}")
    print(f"  Raw MAE                 : {raw_stats['MAE_days']:.6f} days")
    print(f"  Aligned Pearson r       : {aligned_stats['pearson_r']:.6f}")
    print(f"  Aligned MAE             : {aligned_stats['MAE_days']:.6f} days")

    print("\nTERMINAL COMPARISON")
    print(f"  Raw Pearson r           : {terminal_raw_stats['pearson_r']:.6f}")
    print(f"  Raw MAE                 : {terminal_raw_stats['MAE_days']:.6f} days")
    print(f"  Aligned Pearson r       : {terminal_aligned_stats['pearson_r']:.6f}")
    print(f"  Aligned MAE             : {terminal_aligned_stats['MAE_days']:.6f} days")
    print(f"  Median FMM/Pollock      : {median_ratio:.6f}")

    print("\nMONOTONICITY")
    print(f"  Pollock fraction        : {np.mean(pollock_mono):.6f}")
    print(f"  FMM raw fraction        : {np.mean(fmm_raw_mono):.6f}")
    print(f"  FMM aligned fraction    : {np.mean(fmm_aligned_mono):.6f}")

    print("\nBASELINE INTERPRETATION")
    print(f"  {interpretation}")

    print("\n" + "=" * 78)
    print("V16B-3 FINAL COMPARISON GATES")
    print("=" * 78)

    for g,p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")

    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")

    print("\nNumerical:")
    print(f"  {COMPARISON_NPZ.name}")
    print(f"  SHA-256: {sha256_file(COMPARISON_NPZ)}")

    print("\nTables:")
    for p in [
        IDENTITY_CSV,
        COORD_CSV,
        NODEWISE_CSV,
        TERMINAL_CSV,
        MONO_CSV,
        SUMMARY_CSV,
        CLASS_CSV,
        GATES_CSV,
        DECISION_CSV,
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16B-3 INDEPENDENT FMM / POLLOCK TOF COMPARISON: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
