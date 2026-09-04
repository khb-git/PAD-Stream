from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V16B-8
# Independent Directional / FMM / Pollock TOF Comparison
#
# PURPOSE
# -------
# Compare, without calibration:
#
#   1) frozen isotropic FMM arrival time from V16B-2
#   2) frozen directional advective travel time from V16B-7
#   3) frozen Pollock streamline TOF from Foundation Case 0001
#
# All comparisons are performed on the same frozen Pollock streamline nodes.
#
# PRIMARY SCIENTIFIC QUESTION
# ---------------------------
# Does restoring the direction of the Darcy velocity field reduce the
# discrepancy between scalar-speed Fast Marching and exact Pollock TOF?
#
# HARD CONSTRAINTS
# ----------------
# NO FMM rerun.
# NO directional PDE rerun.
# NO Pollock retrace.
# NO affine fit.
# NO scaling.
# NO offset correction.
# NO speed recalibration.
# NO producer_id reconstruction.
# NO SG3/SG4 rerun.
# NO model.predict.
# NO training.
#
# PRIMARY COMPARISON
# ------------------
# RAW PHYSICAL OUTPUTS ONLY:
#
#     T_FMM(x_s,n)
#     tau_ADV(x_s,n)
#     tau_POLLOCK(s,n)
#
# The directional field and FMM field are both sampled at the already-frozen
# Pollock XYZ nodes using the same trilinear cell-centered interpolation.
#
# DECISION METRICS
# ----------------
#
#   delta_MAE = MAE_FMM - MAE_ADV
#   delta_RMSE = RMSE_FMM - RMSE_ADV
#   delta_r = r_ADV - r_FMM
#
# Positive delta_MAE / delta_RMSE means ADV improved absolute error.
# Positive delta_r means ADV improved ordering/correlation.
#
# No arbitrary accuracy threshold is imposed.
# =============================================================================


ROOT = Path(__file__).resolve().parent

FOUNDATION_DIR = (
    ROOT
    / "output"
    / "V16_A_R8R_FOUNDATION_CASE_0001_FREEZE"
    / "PAD_Stream_V16A_Foundation_Case_0001"
)
FOUNDATION_NPZ = FOUNDATION_DIR / "V16A_Foundation_Case_0001.npz"

B2_DIR = ROOT / "output" / "V16_B2_EXACT_3D_FMM_ARRIVAL_TIME_BASELINE"
B2_NPZ = B2_DIR / "V16B2_Exact_3D_FMM_Arrival_Time.npz"
B2_SUMMARY = B2_DIR / "PAD_Stream_V16B2_Summary.json"

B3_DIR = ROOT / "output" / "V16_B3_INDEPENDENT_FMM_POLLOCK_TOF_COMPARISON"
B3_NPZ = B3_DIR / "V16B3_FMM_Pollock_TOF_Comparison.npz"
B3_SUMMARY = B3_DIR / "PAD_Stream_V16B3_Summary.json"

B7_DIR = ROOT / "output" / "V16_B7_CONTROLLED_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_SOLVE"
B7_NPZ = B7_DIR / "V16B7_Directional_Advective_Travel_Time.npz"
B7_SUMMARY = B7_DIR / "PAD_Stream_V16B7_Summary.json"

OUT = ROOT / "output" / "V16_B8_INDEPENDENT_DIRECTIONAL_FMM_POLLOCK_COMPARISON"
OUT.mkdir(parents=True, exist_ok=True)

IDENTITY_CSV = OUT / "V16B8_Input_Identity.csv"
NODE_CSV = OUT / "V16B8_Nodewise_Three_Way_Comparison.csv"
TERMINAL_CSV = OUT / "V16B8_Terminal_Three_Way_Comparison.csv"
MONO_CSV = OUT / "V16B8_Streamline_Monotonicity_Comparison.csv"
GLOBAL_CSV = OUT / "V16B8_Global_Comparison_Statistics.csv"
IMPROVEMENT_CSV = OUT / "V16B8_ADV_vs_FMM_Improvement_Metrics.csv"
CLASS_CSV = OUT / "V16B8_Three_Way_Interpretation.csv"
GATES_CSV = OUT / "V16B8_Final_Comparison_Gates.csv"
DECISION_CSV = OUT / "V16B8_Comparison_Decision.csv"

NUMERICAL = OUT / "V16B8_Directional_FMM_Pollock_Comparison.npz"
CONTRACT_JSON = OUT / "V16B8_Three_Way_Comparison_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16B8_Summary.json"

SECONDS_PER_DAY = 86400.0


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
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


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
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    b = np.asarray(b, dtype=np.float64).reshape(-1)

    mask = np.isfinite(a) & np.isfinite(b)
    a = a[mask]
    b = b[mask]

    if len(a) < 3:
        return float("nan")

    if np.std(a) == 0.0 or np.std(b) == 0.0:
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

    c00 = c000 * (1.0 - wx) + c100 * wx
    c10 = c010 * (1.0 - wx) + c110 * wx
    c01 = c001 * (1.0 - wx) + c101 * wx
    c11 = c011 * (1.0 - wx) + c111 * wx

    c0 = c00 * (1.0 - wy) + c10 * wy
    c1 = c01 * (1.0 - wy) + c11 * wy

    out = c0 * (1.0 - wz) + c1 * wz

    return out.reshape(xyz_m.shape[:-1])


def comparison_stats(name, pred_s, truth_s):
    pred_s = np.asarray(pred_s, dtype=np.float64)
    truth_s = np.asarray(truth_s, dtype=np.float64)

    diff = pred_s - truth_s
    absdiff = np.abs(diff)

    denom = np.maximum(np.abs(truth_s), 1.0)
    absrel = absdiff / denom

    return {
        "comparison": name,
        "count": int(diff.size),
        "pearson_r": safe_corr(pred_s, truth_s),
        "bias_days": float(np.mean(diff) / SECONDS_PER_DAY),
        "MAE_days": float(np.mean(absdiff) / SECONDS_PER_DAY),
        "RMSE_days": float(np.sqrt(np.mean(diff**2)) / SECONDS_PER_DAY),
        "median_abs_error_days": float(np.median(absdiff) / SECONDS_PER_DAY),
        "p95_abs_error_days": float(np.percentile(absdiff, 95) / SECONDS_PER_DAY),
        "max_abs_error_days": float(np.max(absdiff) / SECONDS_PER_DAY),
        "median_abs_relative_error": float(np.median(absrel)),
        "p95_abs_relative_error": float(np.percentile(absrel, 95)),
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16B-8")
    print("Independent Directional / FMM / Pollock TOF Comparison")
    print("=" * 78)

    print("""
V16B-2 ISOTROPIC FMM FIELD IS IMMUTABLE.
V16B-7 DIRECTIONAL ADVECTIVE FIELD IS IMMUTABLE.
FROZEN POLLOCK STREAMLINES / TOF ARE IMMUTABLE.
NO FAST MARCHING SOLVE WILL BE RERUN.
NO DIRECTIONAL PDE WILL BE RERUN.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO FIELD WILL BE SCALED, SHIFTED, ALIGNED, OR RECALIBRATED.
NO SPEED FIELD WILL BE CHANGED.
NO PRODUCER ID WILL BE INVENTED.
NO SG3 / SG4 PHYSICS WILL BE RERUN.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
THIS MILESTONE PERFORMS A RAW THREE-WAY COMPARISON ONLY.
""")

    for p in [
        FOUNDATION_NPZ,
        B2_NPZ,
        B2_SUMMARY,
        B3_NPZ,
        B3_SUMMARY,
        B7_NPZ,
        B7_SUMMARY,
    ]:
        if not p.exists():
            raise FileNotFoundError(p)

    b2_summary = load_json(B2_SUMMARY)
    b3_summary = load_json(B3_SUMMARY)
    b7_summary = load_json(B7_SUMMARY)

    if b2_summary.get("status") != "V16B_EXACT_3D_FMM_ARRIVAL_TIME_BASELINE_COMPLETE":
        raise RuntimeError("V16B-8 requires completed V16B-2.")

    if b3_summary.get("status") != "V16B_INDEPENDENT_FMM_POLLOCK_COMPARISON_COMPLETE":
        raise RuntimeError("V16B-8 requires completed V16B-3 mapping contract.")

    if b7_summary.get("status") != "V16B_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_SOLVE_COMPLETE":
        raise RuntimeError("V16B-8 requires completed V16B-7.")

    with np.load(B2_NPZ, allow_pickle=False) as db:
        T_fmm = np.asarray(db["arrival_time_s"], dtype=np.float64)
        dx = float(np.asarray(db["dx_m"]).reshape(-1)[0])
        dy = float(np.asarray(db["dy_m"]).reshape(-1)[0])
        dz = float(np.asarray(db["dz_m"]).reshape(-1)[0])

    with np.load(B3_NPZ, allow_pickle=False) as db:
        xyz_m = np.asarray(db["streamline_xyz_m"], dtype=np.float64)
        pollock = np.asarray(db["pollock_tof_s"], dtype=np.float64)
        origin = np.asarray(db["origin_center_m"], dtype=np.float64)
        fmm_b3_raw = np.asarray(db["fmm_sample_raw_s"], dtype=np.float64)

    with np.load(B7_NPZ, allow_pickle=False) as db:
        tau_adv = np.asarray(db["tau_adv_s"], dtype=np.float64)

    if T_fmm.shape != (15, 50, 50):
        raise RuntimeError(f"Unexpected FMM shape: {T_fmm.shape}")

    if tau_adv.shape != (15, 50, 50):
        raise RuntimeError(f"Unexpected ADV shape: {tau_adv.shape}")

    if xyz_m.shape != (1078, 201, 3):
        raise RuntimeError(f"Unexpected XYZ shape: {xyz_m.shape}")

    if pollock.shape != (1078, 201):
        raise RuntimeError(f"Unexpected Pollock shape: {pollock.shape}")

    fmm_sample = trilinear(T_fmm, xyz_m, dx, dy, dz, origin)
    adv_sample = trilinear(tau_adv, xyz_m, dx, dy, dz, origin)

    # Reproduce B3 FMM raw mapping exactly.
    fmm_mapping_linf = float(np.max(np.abs(fmm_sample - fmm_b3_raw)))

    if fmm_mapping_linf > 1e-9:
        raise RuntimeError(
            f"V16B-8 FMM mapping does not reproduce V16B-3. Linf={fmm_mapping_linf}"
        )

    save_csv(
        IDENTITY_CSV,
        [{
            "foundation_sha256": sha256_file(FOUNDATION_NPZ),
            "V16B2_FMM_sha256": sha256_file(B2_NPZ),
            "V16B3_mapping_sha256": sha256_file(B3_NPZ),
            "V16B7_ADV_sha256": sha256_file(B7_NPZ),
            "FMM_mapping_reproduction_Linf_s": fmm_mapping_linf,
        }],
    )

    # -------------------------------------------------------------------------
    # Global raw comparisons
    # -------------------------------------------------------------------------
    fmm_all = comparison_stats("FMM_vs_POLLOCK_ALL_NODES_RAW", fmm_sample, pollock)
    adv_all = comparison_stats("ADV_vs_POLLOCK_ALL_NODES_RAW", adv_sample, pollock)

    fmm_term = comparison_stats(
        "FMM_vs_POLLOCK_TERMINAL_RAW",
        fmm_sample[:, -1],
        pollock[:, -1],
    )
    adv_term = comparison_stats(
        "ADV_vs_POLLOCK_TERMINAL_RAW",
        adv_sample[:, -1],
        pollock[:, -1],
    )

    save_csv(GLOBAL_CSV, [fmm_all, adv_all, fmm_term, adv_term])

    # -------------------------------------------------------------------------
    # Nodewise comparison
    # -------------------------------------------------------------------------
    node_rows = []

    for node in range(pollock.shape[1]):
        p = pollock[:, node]
        f = fmm_sample[:, node]
        a = adv_sample[:, node]

        f_mae = float(np.mean(np.abs(f - p)) / SECONDS_PER_DAY)
        a_mae = float(np.mean(np.abs(a - p)) / SECONDS_PER_DAY)

        node_rows.append({
            "node": node,
            "xi": node / (pollock.shape[1] - 1),
            "Pollock_mean_days": float(np.mean(p) / SECONDS_PER_DAY),
            "FMM_mean_days": float(np.mean(f) / SECONDS_PER_DAY),
            "ADV_mean_days": float(np.mean(a) / SECONDS_PER_DAY),
            "FMM_MAE_days": f_mae,
            "ADV_MAE_days": a_mae,
            "ADV_minus_FMM_MAE_days": a_mae - f_mae,
            "FMM_pearson_r": safe_corr(f, p),
            "ADV_pearson_r": safe_corr(a, p),
        })

    save_csv(NODE_CSV, node_rows)

    # -------------------------------------------------------------------------
    # Terminal streamline comparison
    # -------------------------------------------------------------------------
    pterm = pollock[:, -1]
    fterm = fmm_sample[:, -1]
    aterm = adv_sample[:, -1]

    terminal_rows = []

    for s in range(len(pterm)):
        f_err = (fterm[s] - pterm[s]) / SECONDS_PER_DAY
        a_err = (aterm[s] - pterm[s]) / SECONDS_PER_DAY

        terminal_rows.append({
            "streamline": s,
            "Pollock_terminal_days": float(pterm[s] / SECONDS_PER_DAY),
            "FMM_terminal_days": float(fterm[s] / SECONDS_PER_DAY),
            "ADV_terminal_days": float(aterm[s] / SECONDS_PER_DAY),
            "FMM_error_days": float(f_err),
            "ADV_error_days": float(a_err),
            "FMM_abs_error_days": float(abs(f_err)),
            "ADV_abs_error_days": float(abs(a_err)),
            "ADV_abs_error_improvement_days": float(abs(f_err) - abs(a_err)),
            "FMM_to_Pollock_ratio": float(fterm[s] / pterm[s]) if pterm[s] > 0 else float("nan"),
            "ADV_to_Pollock_ratio": float(aterm[s] / pterm[s]) if pterm[s] > 0 else float("nan"),
        })

    save_csv(TERMINAL_CSV, terminal_rows)

    # -------------------------------------------------------------------------
    # Monotonicity along frozen Pollock trajectories
    # -------------------------------------------------------------------------
    pstep = np.diff(pollock, axis=1)
    fstep = np.diff(fmm_sample, axis=1)
    astep = np.diff(adv_sample, axis=1)

    p_mono = np.all(pstep >= -1e-10, axis=1)
    f_mono = np.all(fstep >= -1e-10, axis=1)
    a_mono = np.all(astep >= -1e-10, axis=1)

    f_neg = fstep < -1e-10
    a_neg = astep < -1e-10

    save_csv(
        MONO_CSV,
        [{
            "streamline_count": int(len(p_mono)),
            "Pollock_monotonic_fraction": float(np.mean(p_mono)),
            "FMM_monotonic_fraction": float(np.mean(f_mono)),
            "ADV_monotonic_fraction": float(np.mean(a_mono)),
            "FMM_negative_step_count": int(np.sum(f_neg)),
            "ADV_negative_step_count": int(np.sum(a_neg)),
            "FMM_negative_step_fraction": float(np.mean(f_neg)),
            "ADV_negative_step_fraction": float(np.mean(a_neg)),
            "ADV_minus_FMM_monotonic_fraction": float(np.mean(a_mono) - np.mean(f_mono)),
            "FMM_minus_ADV_negative_step_fraction": float(np.mean(f_neg) - np.mean(a_neg)),
        }],
    )

    # -------------------------------------------------------------------------
    # Direct improvement metrics
    # -------------------------------------------------------------------------
    improvement = {
        "delta_all_node_MAE_days_FMM_minus_ADV": float(fmm_all["MAE_days"] - adv_all["MAE_days"]),
        "delta_all_node_RMSE_days_FMM_minus_ADV": float(fmm_all["RMSE_days"] - adv_all["RMSE_days"]),
        "delta_all_node_r_ADV_minus_FMM": float(adv_all["pearson_r"] - fmm_all["pearson_r"]),
        "delta_terminal_MAE_days_FMM_minus_ADV": float(fmm_term["MAE_days"] - adv_term["MAE_days"]),
        "delta_terminal_RMSE_days_FMM_minus_ADV": float(fmm_term["RMSE_days"] - adv_term["RMSE_days"]),
        "delta_terminal_r_ADV_minus_FMM": float(adv_term["pearson_r"] - fmm_term["pearson_r"]),
        "delta_monotonic_fraction_ADV_minus_FMM": float(np.mean(a_mono) - np.mean(f_mono)),
        "delta_negative_step_fraction_FMM_minus_ADV": float(np.mean(f_neg) - np.mean(a_neg)),
        "median_terminal_FMM_to_Pollock_ratio": float(np.nanmedian(fterm / np.maximum(pterm, 1e-30))),
        "median_terminal_ADV_to_Pollock_ratio": float(np.nanmedian(aterm / np.maximum(pterm, 1e-30))),
        "fraction_streamlines_ADV_lower_abs_terminal_error_than_FMM": float(
            np.mean(np.abs(aterm - pterm) < np.abs(fterm - pterm))
        ),
    }

    save_csv(IMPROVEMENT_CSV, [improvement])

    # -------------------------------------------------------------------------
    # Descriptive interpretation only.
    # -------------------------------------------------------------------------
    mae_improved = improvement["delta_all_node_MAE_days_FMM_minus_ADV"] > 0
    terminal_mae_improved = improvement["delta_terminal_MAE_days_FMM_minus_ADV"] > 0
    corr_improved = improvement["delta_all_node_r_ADV_minus_FMM"] > 0
    terminal_corr_improved = improvement["delta_terminal_r_ADV_minus_FMM"] > 0
    monotonicity_improved = improvement["delta_monotonic_fraction_ADV_minus_FMM"] > 0

    improvement_count = sum([
        mae_improved,
        terminal_mae_improved,
        corr_improved,
        terminal_corr_improved,
        monotonicity_improved,
    ])

    if improvement_count >= 4:
        interpretation = "DIRECTIONAL_ADVECTIVE_FORMULATION_SUBSTANTIALLY_IMPROVES_POLLOCK_CONSISTENCY"
    elif improvement_count >= 2:
        interpretation = "DIRECTIONAL_ADVECTIVE_FORMULATION_PARTIALLY_IMPROVES_POLLOCK_CONSISTENCY"
    else:
        interpretation = "DIRECTIONAL_ADVECTIVE_FORMULATION_DOES_NOT_SYSTEMATICALLY_IMPROVE_POLLOCK_CONSISTENCY"

    save_csv(
        CLASS_CSV,
        [{
            "interpretation": interpretation,
            "improved_metric_count_out_of_5": improvement_count,
            "all_node_MAE_improved": mae_improved,
            "terminal_MAE_improved": terminal_mae_improved,
            "all_node_correlation_improved": corr_improved,
            "terminal_correlation_improved": terminal_corr_improved,
            "monotonicity_improved": monotonicity_improved,
            "note": "Descriptive comparison only; no field was fitted or recalibrated.",
        }],
    )

    np.savez_compressed(
        NUMERICAL,
        streamline_xyz_m=xyz_m,
        pollock_tof_s=pollock,
        fmm_sample_s=fmm_sample,
        adv_sample_s=adv_sample,
        fmm_error_s=fmm_sample - pollock,
        adv_error_s=adv_sample - pollock,
        fmm_monotonic=f_mono.astype(np.uint8),
        adv_monotonic=a_mono.astype(np.uint8),
        fmm_negative_steps=f_neg.astype(np.uint8),
        adv_negative_steps=a_neg.astype(np.uint8),
        authority_label_ascii=np.frombuffer(
            b"PAD_STREAM_V16B8_RAW_THREE_WAY_COMPARISON",
            dtype=np.uint8,
        ),
    )

    gates = [
        ("V16B2_FMM_status_reproduced", True),
        ("V16B3_mapping_status_reproduced", True),
        ("V16B7_ADV_status_reproduced", True),
        ("FMM_mapping_reproduces_V16B3", fmm_mapping_linf <= 1e-9),
        ("Pollock_shape_valid", pollock.shape == (1078, 201)),
        ("FMM_sample_shape_valid", fmm_sample.shape == pollock.shape),
        ("ADV_sample_shape_valid", adv_sample.shape == pollock.shape),
        ("all_three_arrays_finite", np.all(np.isfinite(pollock)) and np.all(np.isfinite(fmm_sample)) and np.all(np.isfinite(adv_sample))),
        ("raw_all_node_comparison_computed", True),
        ("raw_terminal_comparison_computed", True),
        ("streamline_monotonicity_comparison_computed", True),
        ("direct_ADV_vs_FMM_improvement_metrics_computed", True),
        ("no_scaling_or_offset_alignment", True),
        ("no_FMM_rerun", True),
        ("no_ADV_rerun", True),
        ("no_Pollock_retrace", True),
        ("no_speed_recalibration", True),
        ("no_producer_id_invented", True),
        ("no_SG3_SG4_rerun", True),
        ("no_model_predict", True),
        ("no_training", True),
    ]

    save_csv(
        GATES_CSV,
        [{"gate": g, "passed": bool(p)} for g, p in gates],
    )

    all_pass = all(bool(p) for _, p in gates)

    if all_pass:
        status = "V16B_INDEPENDENT_DIRECTIONAL_FMM_POLLOCK_COMPARISON_COMPLETE"
        diagnosis = interpretation
        recommendation = (
            "Preserve all three untuned baselines. Use the V16B-8 evidence to decide the final role of isotropic FMM "
            "and directional advective travel time in PAD-Stream. Proceed to V16B-9 for branch interpretation / "
            "architecture role decision; do not recalibrate either method."
        )
        next_ms = "V16B-9 — FMM / Directional Travel-Time Architecture Role Decision"
    else:
        status = "V16B_THREE_WAY_COMPARISON_BLOCKED"
        diagnosis = "ONE_OR_MORE_STRUCTURAL_THREE_WAY_COMPARISON_GATES_FAILED"
        recommendation = "Audit only failed V16B-8 structural comparison gates."
        next_ms = "V16B-8R — Three-Way Comparison Residual Audit"

    save_csv(
        DECISION_CSV,
        [{
            "status": status,
            "diagnosis": diagnosis,
            **improvement,
            "numerical_sha256": sha256_file(NUMERICAL),
            "next_milestone": next_ms,
        }],
    )

    contract = {
        "milestone": "V16B-8",
        "status": status,
        "diagnosis": diagnosis,
        "comparison_policy": {
            "raw_physical_outputs_only": True,
            "scaling": False,
            "offset_alignment": False,
            "speed_recalibration": False,
            "Pollock_retrace": False,
        },
        "global_statistics": {
            "FMM_all_nodes": fmm_all,
            "ADV_all_nodes": adv_all,
            "FMM_terminal": fmm_term,
            "ADV_terminal": adv_term,
        },
        "improvement_metrics": improvement,
        "interpretation": interpretation,
        "output": {
            "file": str(NUMERICAL),
            "sha256": sha256_file(NUMERICAL),
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }

    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16B-8",
            "status": status,
            "diagnosis": diagnosis,
            "interpretation": interpretation,
            "FMM_all_node_MAE_days": fmm_all["MAE_days"],
            "ADV_all_node_MAE_days": adv_all["MAE_days"],
            "FMM_all_node_r": fmm_all["pearson_r"],
            "ADV_all_node_r": adv_all["pearson_r"],
            "FMM_terminal_MAE_days": fmm_term["MAE_days"],
            "ADV_terminal_MAE_days": adv_term["MAE_days"],
            "FMM_terminal_r": fmm_term["pearson_r"],
            "ADV_terminal_r": adv_term["pearson_r"],
            **improvement,
            "recommendation": recommendation,
            "next_milestone": next_ms,
        },
    )

    print("ALL-NODE RAW COMPARISON")
    print(f"  FMM Pearson r            : {fmm_all['pearson_r']:.6f}")
    print(f"  ADV Pearson r            : {adv_all['pearson_r']:.6f}")
    print(f"  FMM MAE                  : {fmm_all['MAE_days']:.6f} days")
    print(f"  ADV MAE                  : {adv_all['MAE_days']:.6f} days")
    print(f"  Delta MAE FMM-ADV        : {improvement['delta_all_node_MAE_days_FMM_minus_ADV']:.6f} days")

    print("\nTERMINAL RAW COMPARISON")
    print(f"  FMM Pearson r            : {fmm_term['pearson_r']:.6f}")
    print(f"  ADV Pearson r            : {adv_term['pearson_r']:.6f}")
    print(f"  FMM MAE                  : {fmm_term['MAE_days']:.6f} days")
    print(f"  ADV MAE                  : {adv_term['MAE_days']:.6f} days")
    print(f"  FMM median ratio         : {improvement['median_terminal_FMM_to_Pollock_ratio']:.6f}")
    print(f"  ADV median ratio         : {improvement['median_terminal_ADV_to_Pollock_ratio']:.6f}")

    print("\nMONOTONICITY")
    print(f"  FMM monotonic fraction   : {np.mean(f_mono):.6f}")
    print(f"  ADV monotonic fraction   : {np.mean(a_mono):.6f}")
    print(f"  FMM negative-step frac.  : {np.mean(f_neg):.6f}")
    print(f"  ADV negative-step frac.  : {np.mean(a_neg):.6f}")

    print("\nINTERPRETATION")
    print(f"  {interpretation}")

    print("\n" + "=" * 78)
    print("V16B-8 FINAL THREE-WAY COMPARISON GATES")
    print("=" * 78)

    for g, p in gates:
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
    print(f"  {NUMERICAL.name}")
    print(f"  SHA-256: {sha256_file(NUMERICAL)}")

    print("\nTables:")
    for p in [
        IDENTITY_CSV,
        NODE_CSV,
        TERMINAL_CSV,
        MONO_CSV,
        GLOBAL_CSV,
        IMPROVEMENT_CSV,
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
    print("PAD-STREAM V16B-8 INDEPENDENT DIRECTIONAL / FMM / POLLOCK COMPARISON: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
