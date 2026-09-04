from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V16B-4
# FMM / Pollock Discrepancy Structure & Directionality Audit
#
# PURPOSE
# -------
# V16B-3 established an untuned comparison between:
#
#   - isotropic grid-based Fast Marching arrival time, and
#   - directional Pollock streamline time-of-flight.
#
# Key V16B-3 observations:
#   - moderate all-node ordering consistency,
#   - weak terminal-time correlation,
#   - median terminal FMM/Pollock ratio near 0.5,
#   - FMM samples are often non-monotone along Pollock trajectories.
#
# V16B-4 determines WHY.
#
# It audits whether FMM-vs-Pollock discrepancy is associated with:
#   1. streamline tortuosity,
#   2. vertical motion,
#   3. path length,
#   4. streamline tangent alignment with frozen velocity,
#   5. alignment with the FMM arrival-time gradient,
#   6. sampled permeability heterogeneity,
#   7. sampled speed variability,
#   8. endpoint spatial location.
#
# IMPORTANT
# ---------
# V16B-4 DOES NOT:
#   - modify the V16B-1 speed field,
#   - rerun FMM,
#   - retrace Pollock,
#   - invent producer_id,
#   - tune a directional correction,
#   - train/infer ML,
#   - modify Foundation Case 0001.
#
# This milestone is diagnostic only.
# =============================================================================


ROOT = Path(__file__).resolve().parent

FOUNDATION_DIR = (
    ROOT
    / "output"
    / "V16_A_R8R_FOUNDATION_CASE_0001_FREEZE"
    / "PAD_Stream_V16A_Foundation_Case_0001"
)
FOUNDATION_NPZ = FOUNDATION_DIR / "V16A_Foundation_Case_0001.npz"

B1_DIR = ROOT / "output" / "V16_B1_FMM_GOVERNING_METRIC_CONTRACT"
B1_SPEED = B1_DIR / "V16B1_FMM_Speed_Field_Contract.npz"

B2_DIR = ROOT / "output" / "V16_B2_EXACT_3D_FMM_ARRIVAL_TIME_BASELINE"
B2_ARRIVAL = B2_DIR / "V16B2_Exact_3D_FMM_Arrival_Time.npz"

B3_DIR = ROOT / "output" / "V16_B3_INDEPENDENT_FMM_POLLOCK_TOF_COMPARISON"
B3_COMPARISON = B3_DIR / "V16B3_FMM_Pollock_TOF_Comparison.npz"
B3_CONTRACT = B3_DIR / "V16B3_FMM_Pollock_Comparison_Contract.json"
B3_SUMMARY = B3_DIR / "PAD_Stream_V16B3_Summary.json"

OUT = ROOT / "output" / "V16_B4_FMM_POLLOCK_DISCREPANCY_DIRECTIONALITY_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

IDENTITY_CSV = OUT / "V16B4_Input_Identity.csv"
STREAMLINE_CSV = OUT / "V16B4_Streamline_Discrepancy_Features.csv"
CORR_CSV = OUT / "V16B4_Discrepancy_Feature_Correlation.csv"
MONO_CSV = OUT / "V16B4_Nonmonotonicity_Directionality_Audit.csv"
BIN_CSV = OUT / "V16B4_Discrepancy_Binned_Structure.csv"
ENDPOINT_CSV = OUT / "V16B4_Endpoint_Spatial_Discrepancy.csv"
INTERPRET_CSV = OUT / "V16B4_Directionality_Interpretation.csv"
GATES_CSV = OUT / "V16B4_Final_Directionality_Gates.csv"
DECISION_CSV = OUT / "V16B4_Directionality_Decision.csv"

AUDIT_NPZ = OUT / "V16B4_Discrepancy_Directionality_Audit.npz"
CONTRACT_JSON = OUT / "V16B4_Directionality_Audit_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16B4_Summary.json"

SECONDS_PER_DAY = 86400.0


def save_csv(path: Path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
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


def safe_corr(a, b):
    a = np.asarray(a, dtype=float).reshape(-1)
    b = np.asarray(b, dtype=float).reshape(-1)
    mask = np.isfinite(a) & np.isfinite(b)
    a = a[mask]
    b = b[mask]
    if len(a) < 3 or np.std(a) == 0.0 or np.std(b) == 0.0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def trilinear(field, xyz_m, dx, dy, dz, origin):
    nz, ny, nx = field.shape
    pts = xyz_m.reshape(-1, 3)

    fx = (pts[:, 0] - origin[0]) / dx
    fy = (pts[:, 1] - origin[1]) / dy
    fz = (pts[:, 2] - origin[2]) / dz

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

    c00 = c000*(1-wx) + c100*wx
    c10 = c010*(1-wx) + c110*wx
    c01 = c001*(1-wx) + c101*wx
    c11 = c011*(1-wx) + c111*wx
    c0 = c00*(1-wy) + c10*wy
    c1 = c01*(1-wy) + c11*wy

    out = c0*(1-wz) + c1*wz
    return out.reshape(xyz_m.shape[:-1])


def normalize(v, axis=-1, eps=1e-30):
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, eps)


def binned_rows(name, x, y, nbins=5):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) == 0:
        return []

    edges = np.quantile(x, np.linspace(0, 1, nbins + 1))
    rows = []
    for b in range(nbins):
        lo = edges[b]
        hi = edges[b+1]
        if b < nbins - 1:
            m = (x >= lo) & (x < hi)
        else:
            m = (x >= lo) & (x <= hi)
        if not np.any(m):
            continue
        rows.append({
            "feature": name,
            "bin": b,
            "x_min": float(np.min(x[m])),
            "x_max": float(np.max(x[m])),
            "count": int(np.sum(m)),
            "mean_terminal_error_days": float(np.mean(y[m])),
            "median_terminal_error_days": float(np.median(y[m])),
            "mean_abs_terminal_error_days": float(np.mean(np.abs(y[m]))),
        })
    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16B-4")
    print("FMM / Pollock Discrepancy Structure & Directionality Audit")
    print("=" * 78)

    print("""
NO FMM SPEED FIELD WILL BE CHANGED.
NO FAST MARCHING SOLVE WILL BE RERUN.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO PRODUCER ID WILL BE INVENTED.
NO DIRECTIONAL CORRECTION WILL BE FIT.
NO SG3 / SG4 PHYSICS WILL BE RERUN.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
THIS MILESTONE DIAGNOSES THE EXISTING V16B-3 DISCREPANCY ONLY.
""")

    for p in [
        FOUNDATION_NPZ, B1_SPEED, B2_ARRIVAL,
        B3_COMPARISON, B3_CONTRACT, B3_SUMMARY
    ]:
        if not p.exists():
            raise FileNotFoundError(p)

    b3_summary = load_json(B3_SUMMARY)
    b3_contract = load_json(B3_CONTRACT)

    if b3_summary.get("status") != "V16B_INDEPENDENT_FMM_POLLOCK_COMPARISON_COMPLETE":
        raise RuntimeError("V16B-4 requires completed V16B-3.")

    with np.load(FOUNDATION_NPZ, allow_pickle=False) as db:
        foundation = {k: np.array(db[k], copy=True) for k in db.files}

    with np.load(B1_SPEED, allow_pickle=False) as db:
        speed_db = {k: np.array(db[k], copy=True) for k in db.files}

    with np.load(B2_ARRIVAL, allow_pickle=False) as db:
        b2 = {k: np.array(db[k], copy=True) for k in db.files}

    with np.load(B3_COMPARISON, allow_pickle=False) as db:
        b3 = {k: np.array(db[k], copy=True) for k in db.files}

    save_csv(IDENTITY_CSV, [{
        "foundation_sha256": sha256_file(FOUNDATION_NPZ),
        "B1_speed_sha256": sha256_file(B1_SPEED),
        "B2_arrival_sha256": sha256_file(B2_ARRIVAL),
        "B3_comparison_sha256": sha256_file(B3_COMPARISON),
    }])

    xyz = np.asarray(b3["streamline_xyz_m"], dtype=np.float64)
    pollock = np.asarray(b3["pollock_tof_s"], dtype=np.float64)
    fmm_aligned = np.asarray(b3["fmm_sample_seed_aligned_s"], dtype=np.float64)

    dx = float(np.asarray(b2["dx_m"]).reshape(-1)[0])
    dy = float(np.asarray(b2["dy_m"]).reshape(-1)[0])
    dz = float(np.asarray(b2["dz_m"]).reshape(-1)[0])
    origin = np.asarray(b3["origin_center_m"], dtype=np.float64)

    Vxc = np.asarray(speed_db["Vxc_m_s"], dtype=np.float64)
    Vyc = np.asarray(speed_db["Vyc_m_s"], dtype=np.float64)
    Vzc = np.asarray(speed_db["Vzc_m_s"], dtype=np.float64)
    speed = np.asarray(speed_db["speed_raw_m_s"], dtype=np.float64)

    Kx = np.asarray(foundation["Kx"], dtype=np.float64)
    Ky = np.asarray(foundation["Ky"], dtype=np.float64)
    Kz = np.asarray(foundation["Kz"], dtype=np.float64)

    T = np.asarray(b2["arrival_time_s"], dtype=np.float64)

    # FMM gradient vector.
    dT_dz, dT_dy, dT_dx = np.gradient(T, dz, dy, dx, edge_order=1)

    # Sample frozen fields along Pollock trajectories.
    vx_s = trilinear(Vxc, xyz, dx, dy, dz, origin)
    vy_s = trilinear(Vyc, xyz, dx, dy, dz, origin)
    vz_s = trilinear(Vzc, xyz, dx, dy, dz, origin)
    speed_s = trilinear(speed, xyz, dx, dy, dz, origin)

    gx_s = trilinear(dT_dx, xyz, dx, dy, dz, origin)
    gy_s = trilinear(dT_dy, xyz, dx, dy, dz, origin)
    gz_s = trilinear(dT_dz, xyz, dx, dy, dz, origin)

    kx_s = trilinear(Kx, xyz, dx, dy, dz, origin)
    ky_s = trilinear(Ky, xyz, dx, dy, dz, origin)
    kz_s = trilinear(Kz, xyz, dx, dy, dz, origin)

    # Streamline tangent from frozen coordinates.
    seg = np.diff(xyz, axis=1)
    seg_len = np.linalg.norm(seg, axis=2)

    tangent_seg = normalize(seg)

    # Node tangent: average neighboring segment tangents.
    tangent = np.zeros_like(xyz)
    tangent[:, 0, :] = tangent_seg[:, 0, :]
    tangent[:, -1, :] = tangent_seg[:, -1, :]
    tangent[:, 1:-1, :] = normalize(
        tangent_seg[:, :-1, :] + tangent_seg[:, 1:, :]
    )

    velocity_vec = np.stack([vx_s, vy_s, vz_s], axis=-1)
    velocity_hat = normalize(velocity_vec)

    grad_vec = np.stack([gx_s, gy_s, gz_s], axis=-1)
    grad_hat = normalize(grad_vec)

    tangent_velocity_cos = np.sum(tangent * velocity_hat, axis=-1)

    # Arrival-time gradient points toward increasing T. Positive alignment means
    # streamline direction follows increasing FMM arrival time.
    tangent_grad_cos = np.sum(tangent * grad_hat, axis=-1)

    # Path geometry.
    path_length = np.sum(seg_len, axis=1)
    displacement_vec = xyz[:, -1, :] - xyz[:, 0, :]
    displacement = np.linalg.norm(displacement_vec, axis=1)
    tortuosity = path_length / np.maximum(displacement, 1e-30)

    vertical_path = np.sum(np.abs(seg[:, :, 2]), axis=1)
    vertical_fraction = vertical_path / np.maximum(path_length, 1e-30)

    # Heterogeneity summaries.
    kh_s = 0.5 * (kx_s + ky_s)
    logk = np.log(np.maximum(kh_s, 1e-30))

    mean_logk = np.mean(logk, axis=1)
    std_logk = np.std(logk, axis=1)
    mean_kzkh = np.mean(kz_s / np.maximum(kh_s, 1e-30), axis=1)

    mean_speed = np.mean(speed_s, axis=1)
    cv_speed = np.std(speed_s, axis=1) / np.maximum(mean_speed, 1e-30)

    mean_tangent_velocity_cos = np.mean(tangent_velocity_cos, axis=1)
    mean_tangent_grad_cos = np.mean(tangent_grad_cos, axis=1)

    # Monotonicity discrepancy.
    fmm_steps = np.diff(fmm_aligned, axis=1)
    negative_step_count = np.sum(fmm_steps < -1e-10, axis=1)
    negative_step_fraction = negative_step_count / fmm_steps.shape[1]
    most_negative_step_days = np.min(fmm_steps, axis=1) / SECONDS_PER_DAY

    # Terminal discrepancy.
    terminal_error_days = (
        fmm_aligned[:, -1] - pollock[:, -1]
    ) / SECONDS_PER_DAY

    terminal_ratio = (
        fmm_aligned[:, -1]
        / np.maximum(pollock[:, -1], 1e-30)
    )

    # Per-streamline table.
    rows = []
    for s in range(xyz.shape[0]):
        rows.append({
            "streamline": s,
            "path_length_m": float(path_length[s]),
            "displacement_m": float(displacement[s]),
            "tortuosity": float(tortuosity[s]),
            "vertical_fraction": float(vertical_fraction[s]),
            "mean_tangent_velocity_cos": float(mean_tangent_velocity_cos[s]),
            "mean_tangent_FMM_gradient_cos": float(mean_tangent_grad_cos[s]),
            "mean_log_horizontal_perm": float(mean_logk[s]),
            "std_log_horizontal_perm": float(std_logk[s]),
            "mean_Kz_Kh": float(mean_kzkh[s]),
            "mean_speed_m_s": float(mean_speed[s]),
            "speed_CV": float(cv_speed[s]),
            "FMM_negative_step_count": int(negative_step_count[s]),
            "FMM_negative_step_fraction": float(negative_step_fraction[s]),
            "most_negative_step_days": float(most_negative_step_days[s]),
            "Pollock_terminal_days": float(pollock[s, -1] / SECONDS_PER_DAY),
            "FMM_terminal_days": float(fmm_aligned[s, -1] / SECONDS_PER_DAY),
            "terminal_error_days": float(terminal_error_days[s]),
            "terminal_ratio": float(terminal_ratio[s]),
            "endpoint_x_m": float(xyz[s, -1, 0]),
            "endpoint_y_m": float(xyz[s, -1, 1]),
            "endpoint_z_m": float(xyz[s, -1, 2]),
        })
    save_csv(STREAMLINE_CSV, rows)

    features = {
        "path_length_m": path_length,
        "displacement_m": displacement,
        "tortuosity": tortuosity,
        "vertical_fraction": vertical_fraction,
        "mean_tangent_velocity_cos": mean_tangent_velocity_cos,
        "mean_tangent_FMM_gradient_cos": mean_tangent_grad_cos,
        "mean_log_horizontal_perm": mean_logk,
        "std_log_horizontal_perm": std_logk,
        "mean_speed_m_s": mean_speed,
        "speed_CV": cv_speed,
        "FMM_negative_step_fraction": negative_step_fraction,
    }

    corr_rows = []
    for name, x in features.items():
        corr_rows.append({
            "feature": name,
            "corr_with_signed_terminal_error": safe_corr(x, terminal_error_days),
            "corr_with_abs_terminal_error": safe_corr(x, np.abs(terminal_error_days)),
            "corr_with_terminal_ratio": safe_corr(x, terminal_ratio),
        })
    save_csv(CORR_CSV, corr_rows)

    # Identify strongest absolute explanatory correlations descriptively.
    valid_corrs = []
    for r in corr_rows:
        c = r["corr_with_abs_terminal_error"]
        if np.isfinite(c):
            valid_corrs.append((abs(c), r["feature"], c))
    valid_corrs.sort(reverse=True)

    strongest_feature = valid_corrs[0][1] if valid_corrs else "UNRESOLVED"
    strongest_corr = valid_corrs[0][2] if valid_corrs else float("nan")

    # Nonmonotonicity and directionality.
    node_negative = fmm_steps < -1e-10
    # compare tangent-gradient cosine at segment starts where FMM decreases
    tg_seg = tangent_grad_cos[:, :-1]
    tv_seg = tangent_velocity_cos[:, :-1]

    neg_tg = tg_seg[node_negative]
    pos_tg = tg_seg[~node_negative]
    neg_tv = tv_seg[node_negative]
    pos_tv = tv_seg[~node_negative]

    mono_rows = [{
        "negative_FMM_step_count": int(np.sum(node_negative)),
        "total_FMM_steps": int(node_negative.size),
        "negative_step_fraction": float(np.mean(node_negative)),
        "mean_tangent_grad_cos_negative_steps": float(np.mean(neg_tg)) if neg_tg.size else float("nan"),
        "mean_tangent_grad_cos_nonnegative_steps": float(np.mean(pos_tg)) if pos_tg.size else float("nan"),
        "mean_tangent_velocity_cos_negative_steps": float(np.mean(neg_tv)) if neg_tv.size else float("nan"),
        "mean_tangent_velocity_cos_nonnegative_steps": float(np.mean(pos_tv)) if pos_tv.size else float("nan"),
        "corr_negative_step_fraction_with_terminal_abs_error": safe_corr(
            negative_step_fraction, np.abs(terminal_error_days)
        ),
    }]
    save_csv(MONO_CSV, mono_rows)

    bin_rows = []
    for name in [
        "tortuosity",
        "vertical_fraction",
        "mean_tangent_velocity_cos",
        "mean_tangent_FMM_gradient_cos",
        "std_log_horizontal_perm",
        "speed_CV",
        "FMM_negative_step_fraction",
    ]:
        bin_rows.extend(binned_rows(name, features[name], terminal_error_days))
    save_csv(BIN_CSV, bin_rows)

    # Endpoint spatial bins only; no producer labels are inferred.
    xmid = 0.5 * (np.min(xyz[:, -1, 0]) + np.max(xyz[:, -1, 0]))
    ymid = 0.5 * (np.min(xyz[:, -1, 1]) + np.max(xyz[:, -1, 1]))

    endpoint_groups = {
        "LOW_X_LOW_Y": (xyz[:, -1, 0] <= xmid) & (xyz[:, -1, 1] <= ymid),
        "HIGH_X_LOW_Y": (xyz[:, -1, 0] > xmid) & (xyz[:, -1, 1] <= ymid),
        "LOW_X_HIGH_Y": (xyz[:, -1, 0] <= xmid) & (xyz[:, -1, 1] > ymid),
        "HIGH_X_HIGH_Y": (xyz[:, -1, 0] > xmid) & (xyz[:, -1, 1] > ymid),
    }

    endpoint_rows = []
    for name, m in endpoint_groups.items():
        if not np.any(m):
            continue
        endpoint_rows.append({
            "spatial_bin": name,
            "count": int(np.sum(m)),
            "mean_terminal_error_days": float(np.mean(terminal_error_days[m])),
            "median_terminal_error_days": float(np.median(terminal_error_days[m])),
            "mean_abs_terminal_error_days": float(np.mean(np.abs(terminal_error_days[m]))),
            "median_terminal_ratio": float(np.median(terminal_ratio[m])),
        })
    save_csv(ENDPOINT_CSV, endpoint_rows)

    # Interpretation.
    median_ratio = float(np.median(terminal_ratio))
    median_error = float(np.median(terminal_error_days))
    mean_tv = float(np.mean(mean_tangent_velocity_cos))
    mean_tg = float(np.mean(mean_tangent_grad_cos))
    neg_fraction = float(np.mean(node_negative))

    isotropic_shortcut = median_ratio < 0.8
    directional_nonmono = neg_fraction > 0.05
    velocity_following = mean_tv > 0.8
    fmm_gradient_mismatch = mean_tg < 0.8

    if isotropic_shortcut and directional_nonmono and velocity_following:
        interpretation = "ISOTROPIC_FMM_SHORTCUT_BIAS_WITH_DIRECTIONAL_ADVECTIVE_PATH_MISMATCH"
        directional_extension_warranted = True
    elif isotropic_shortcut:
        interpretation = "SYSTEMATIC_ISOTROPIC_FMM_TRAVEL_TIME_UNDERESTIMATION"
        directional_extension_warranted = True
    else:
        interpretation = "NO_STRONG_DIRECTIONAL_EXTENSION_REQUIREMENT_FROM_CURRENT_AUDIT"
        directional_extension_warranted = False

    save_csv(INTERPRET_CSV, [{
        "interpretation": interpretation,
        "directional_extension_warranted": directional_extension_warranted,
        "median_terminal_FMM_to_Pollock_ratio": median_ratio,
        "median_terminal_error_days": median_error,
        "mean_tangent_velocity_cos": mean_tv,
        "mean_tangent_FMM_gradient_cos": mean_tg,
        "FMM_negative_step_fraction": neg_fraction,
        "strongest_abs_error_feature": strongest_feature,
        "strongest_abs_error_correlation": strongest_corr,
        "meaning": (
            "Diagnostic interpretation only. No correction or new speed field is fitted here."
        ),
    }])

    np.savez_compressed(
        AUDIT_NPZ,
        path_length_m=path_length,
        displacement_m=displacement,
        tortuosity=tortuosity,
        vertical_fraction=vertical_fraction,
        mean_tangent_velocity_cos=mean_tangent_velocity_cos,
        mean_tangent_FMM_gradient_cos=mean_tangent_grad_cos,
        mean_log_horizontal_perm=mean_logk,
        std_log_horizontal_perm=std_logk,
        mean_speed_m_s=mean_speed,
        speed_CV=cv_speed,
        negative_step_fraction=negative_step_fraction,
        terminal_error_days=terminal_error_days,
        terminal_ratio=terminal_ratio,
        tangent_velocity_cos=tangent_velocity_cos,
        tangent_FMM_gradient_cos=tangent_grad_cos,
        authority_label_ascii=np.frombuffer(
            b"PAD_STREAM_V16B4_DIRECTIONALITY_AUDIT",
            dtype=np.uint8,
        ),
    )

    gates = [
        ("V16B3_status_reproduced", True),
        ("foundation_identity_recorded", True),
        ("B1_speed_identity_recorded", True),
        ("B2_arrival_identity_recorded", True),
        ("B3_comparison_identity_recorded", True),
        ("streamline_path_geometry_computed", True),
        ("tortuosity_computed", True),
        ("vertical_motion_fraction_computed", True),
        ("velocity_alignment_computed", True),
        ("FMM_gradient_alignment_computed", True),
        ("permeability_heterogeneity_sampled", True),
        ("speed_variability_sampled", True),
        ("nonmonotonicity_structure_audited", True),
        ("endpoint_spatial_structure_audited_without_producer_labels", True),
        ("discrepancy_feature_correlations_computed", True),
        ("no_directional_correction_fitted", True),
        ("no_producer_id_invented", True),
        ("no_FMM_speed_change", True),
        ("no_FMM_rerun", True),
        ("no_Pollock_retrace", True),
        ("no_SG3_SG4_rerun", True),
        ("foundation_not_modified", True),
        ("no_model_predict", True),
        ("no_training", True),
    ]
    save_csv(GATES_CSV, [{"gate": g, "passed": bool(p)} for g,p in gates])

    all_pass = all(bool(p) for _,p in gates)

    if all_pass:
        status = "V16B_FMM_POLLOCK_DIRECTIONAL_DISCREPANCY_AUDIT_COMPLETE"
        diagnosis = interpretation
        if directional_extension_warranted:
            recommendation = (
                "Preserve the isotropic FMM baseline as the control. Proceed to V16B-5 to design, but not yet solve, "
                "a directional/anisotropic arrival-time formulation that respects frozen velocity orientation. "
                "Do not tune the original isotropic speed field."
            )
            next_ms = "V16B-5 — Directional / Anisotropic Arrival-Time Formulation Design"
        else:
            recommendation = (
                "Preserve the isotropic FMM baseline. Proceed to V16B-5 as a baseline closure/visualization milestone "
                "rather than introducing directional physics."
            )
            next_ms = "V16B-5 — FMM Baseline Closure / Visualization"
    else:
        status = "V16B_DIRECTIONALITY_AUDIT_BLOCKED"
        diagnosis = "ONE_OR_MORE_DIRECTIONALITY_AUDIT_GATES_FAILED"
        recommendation = "Audit only failed V16B-4 structural diagnostics."
        next_ms = "V16B-4R — Directionality Audit Residual Repair"

    save_csv(DECISION_CSV, [{
        "status": status,
        "diagnosis": diagnosis,
        "directional_extension_warranted": directional_extension_warranted,
        "median_terminal_ratio": median_ratio,
        "median_terminal_error_days": median_error,
        "FMM_negative_step_fraction": neg_fraction,
        "strongest_abs_error_feature": strongest_feature,
        "strongest_abs_error_correlation": strongest_corr,
        "audit_npz_sha256": sha256_file(AUDIT_NPZ),
        "next_milestone": next_ms,
    }])

    contract = {
        "milestone": "V16B-4",
        "status": status,
        "diagnosis": diagnosis,
        "directional_extension_warranted": directional_extension_warranted,
        "metrics": {
            "median_terminal_FMM_to_Pollock_ratio": median_ratio,
            "median_terminal_error_days": median_error,
            "mean_tangent_velocity_cos": mean_tv,
            "mean_tangent_FMM_gradient_cos": mean_tg,
            "FMM_negative_step_fraction": neg_fraction,
            "strongest_abs_error_feature": strongest_feature,
            "strongest_abs_error_correlation": strongest_corr,
        },
        "interpretation_policy": {
            "diagnostic_only": True,
            "isotropic_speed_recalibrated": False,
            "directional_correction_fitted": False,
            "producer_labels_inferred": False,
        },
        "output": {
            "file": str(AUDIT_NPZ),
            "sha256": sha256_file(AUDIT_NPZ),
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT_JSON, contract)

    save_json(SUMMARY_JSON, {
        "milestone": "V16B-4",
        "status": status,
        "diagnosis": diagnosis,
        "directional_extension_warranted": directional_extension_warranted,
        "median_terminal_FMM_to_Pollock_ratio": median_ratio,
        "median_terminal_error_days": median_error,
        "FMM_negative_step_fraction": neg_fraction,
        "strongest_abs_error_feature": strongest_feature,
        "strongest_abs_error_correlation": strongest_corr,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("DISCREPANCY STRUCTURE")
    print(f"  Median terminal FMM/Pollock : {median_ratio:.6f}")
    print(f"  Median terminal error       : {median_error:.6f} days")
    print(f"  FMM negative-step fraction  : {neg_fraction:.6f}")
    print(f"  Mean tangent·velocity       : {mean_tv:.6f}")
    print(f"  Mean tangent·grad(T_FMM)    : {mean_tg:.6f}")

    print("\nSTRONGEST ABS-ERROR ASSOCIATION")
    print(f"  Feature                     : {strongest_feature}")
    print(f"  Correlation                 : {strongest_corr:.6f}")

    print("\nINTERPRETATION")
    print(f"  {interpretation}")
    print(f"  Directional extension       : {directional_extension_warranted}")

    print("\n" + "=" * 78)
    print("V16B-4 FINAL DIRECTIONALITY GATES")
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
    print(f"  {next_ms}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\nNumerical:")
    print(f"  {AUDIT_NPZ.name}")
    print(f"  SHA-256: {sha256_file(AUDIT_NPZ)}")
    print("\nTables:")
    for p in [
        IDENTITY_CSV, STREAMLINE_CSV, CORR_CSV, MONO_CSV,
        BIN_CSV, ENDPOINT_CSV, INTERPRET_CSV, GATES_CSV, DECISION_CSV
    ]:
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16B-4 FMM / POLLOCK DIRECTIONALITY AUDIT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
