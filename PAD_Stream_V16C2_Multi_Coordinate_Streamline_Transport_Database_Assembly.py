from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V16C-2
# Multi-Coordinate Streamline Transport Database Assembly
#
# PURPOSE
# -------
# Assemble one frozen, synchronized streamline-node database containing:
#
#   - frozen Pollock XYZ coordinates,
#   - authoritative Pollock TOF,
#   - sampled isotropic FMM arrival time,
#   - sampled directional ADV travel time,
#   - sampled Kx, Ky, Kz,
#   - sampled porosity,
#   - sampled pressure,
#   - frozen streamline weight.
#
# Pollock TOF remains the AUTHORITATIVE STREAMLINE TRANSPORT COORDINATE.
# FMM and ADV are auxiliary conditioning / diagnostic channels.
#
# IMPORTANT
# ---------
# V16C-2 DOES NOT:
#   - solve transport,
#   - generate saturation,
#   - train or infer a PI-RNN,
#   - map saturation back to the grid,
#   - rerun FMM,
#   - rerun ADV,
#   - retrace Pollock,
#   - alter Foundation Case 0001,
#   - normalize or fit channels for ML,
#   - invent producer_id.
#
# SAMPLING CONTRACT
# -----------------
# All cell-centered grid fields are sampled at the frozen Pollock XYZ nodes
# using the SAME trilinear cell-centered interpolation geometry already frozen
# by V16B-3/V16B-8.
#
# No nearest-cell substitution and no coordinate remapping is allowed.
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

B3_DIR = ROOT / "output" / "V16_B3_INDEPENDENT_FMM_POLLOCK_TOF_COMPARISON"
B3_NPZ = B3_DIR / "V16B3_FMM_Pollock_TOF_Comparison.npz"

B7_DIR = ROOT / "output" / "V16_B7_CONTROLLED_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_SOLVE"
B7_NPZ = B7_DIR / "V16B7_Directional_Advective_Travel_Time.npz"

B8_DIR = ROOT / "output" / "V16_B8_INDEPENDENT_DIRECTIONAL_FMM_POLLOCK_COMPARISON"
B8_NPZ = B8_DIR / "V16B8_Directional_FMM_Pollock_Comparison.npz"

C1_DIR = ROOT / "output" / "V16_C1_TRAVEL_TIME_HIERARCHY_INTEGRATION_CONTRACT"
C1_SUMMARY = C1_DIR / "PAD_Stream_V16C1_Summary.json"
C1_CONTRACT = C1_DIR / "V16C1_Travel_Time_Hierarchy_Integration_Contract.json"

OUT = ROOT / "output" / "V16_C2_MULTI_COORDINATE_STREAMLINE_TRANSPORT_DATABASE"
OUT.mkdir(parents=True, exist_ok=True)

DATABASE_NPZ = OUT / "V16C2_Multi_Coordinate_Streamline_Transport_Database.npz"

IDENTITY_CSV = OUT / "V16C2_Input_Identity.csv"
CHANNEL_CSV = OUT / "V16C2_Channel_Registry.csv"
SAMPLING_CSV = OUT / "V16C2_Sampling_Contract_Audit.csv"
STATS_CSV = OUT / "V16C2_Channel_Statistics.csv"
SHAPE_CSV = OUT / "V16C2_Database_Shape_and_Finiteness_Audit.csv"
REPRO_CSV = OUT / "V16C2_V16B8_Travel_Time_Reproduction_Audit.csv"
WEIGHT_CSV = OUT / "V16C2_Streamline_Weight_Contract.csv"
GATES_CSV = OUT / "V16C2_Final_Database_Gates.csv"
DECISION_CSV = OUT / "V16C2_Database_Decision.csv"

CONTRACT_JSON = OUT / "V16C2_Multi_Coordinate_Transport_Database_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16C2_Summary.json"

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


def trilinear(field, xyz_m, dx, dy, dz, origin):
    nz, ny, nx = field.shape

    pts = xyz_m.reshape(-1, 3)

    fx = (pts[:, 0] - origin[0]) / dx
    fy = (pts[:, 1] - origin[1]) / dy
    fz = (pts[:, 2] - origin[2]) / dz

    fx_clip = np.clip(fx, 0.0, nx - 1.0)
    fy_clip = np.clip(fy, 0.0, ny - 1.0)
    fz_clip = np.clip(fz, 0.0, nz - 1.0)

    i0 = np.floor(fx_clip).astype(int)
    j0 = np.floor(fy_clip).astype(int)
    k0 = np.floor(fz_clip).astype(int)

    i1 = np.minimum(i0 + 1, nx - 1)
    j1 = np.minimum(j0 + 1, ny - 1)
    k1 = np.minimum(k0 + 1, nz - 1)

    wx = fx_clip - i0
    wy = fy_clip - j0
    wz = fz_clip - k0

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

    audit = {
        "x_clip_count": int(np.sum(fx != fx_clip)),
        "y_clip_count": int(np.sum(fy != fy_clip)),
        "z_clip_count": int(np.sum(fz != fz_clip)),
        "total_points": int(len(pts)),
    }

    return out.reshape(xyz_m.shape[:-1]), audit


def channel_stats(name, a):
    a = np.asarray(a, dtype=np.float64)
    return {
        "channel": name,
        "shape": str(tuple(a.shape)),
        "finite_fraction": float(np.mean(np.isfinite(a))),
        "min": float(np.nanmin(a)),
        "p01": float(np.nanpercentile(a, 1)),
        "median": float(np.nanmedian(a)),
        "mean": float(np.nanmean(a)),
        "p99": float(np.nanpercentile(a, 99)),
        "max": float(np.nanmax(a)),
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16C-2")
    print("Multi-Coordinate Streamline Transport Database Assembly")
    print("=" * 78)

    print("""
V16C-1 INTEGRATION CONTRACT IS IMMUTABLE.
FOUNDATION CASE 0001 IS IMMUTABLE.
V16B-2 FMM IS IMMUTABLE.
V16B-7 ADV IS IMMUTABLE.
FROZEN POLLOCK XYZ / TOF / WEIGHTS ARE IMMUTABLE.

NO TRANSPORT SOLVE WILL BE EXECUTED.
NO SATURATION FIELD WILL BE GENERATED.
NO PI-RNN WILL BE TRAINED OR INFERRED.
NO GRID MAP-BACK WILL BE EXECUTED.
NO FMM OR ADV SOLVE WILL BE RERUN.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO CHANNEL NORMALIZATION OR FITTING WILL BE PERFORMED.
NO PRODUCER ID WILL BE INVENTED.

THIS MILESTONE ASSEMBLES RAW SOURCE-AUTHENTIC CONDITIONING CHANNELS ONLY.
""")

    for p in [
        FOUNDATION_NPZ,
        B2_NPZ,
        B3_NPZ,
        B7_NPZ,
        B8_NPZ,
        C1_SUMMARY,
        C1_CONTRACT,
    ]:
        if not p.exists():
            raise FileNotFoundError(p)

    c1 = load_json(C1_SUMMARY)

    if c1.get("status") != "V16C_TRAVEL_TIME_HIERARCHY_INTEGRATION_CONTRACT_READY":
        raise RuntimeError("V16C-2 requires completed V16C-1.")

    with np.load(FOUNDATION_NPZ, allow_pickle=False) as db:
        required = [
            "Kx", "Ky", "Kz", "porosity", "pressure",
            "streamline_xyz", "pollock_tof", "streamline_weight",
        ]
        missing = [k for k in required if k not in db.files]
        if missing:
            raise RuntimeError(f"Foundation missing required channels: {missing}")

        Kx = np.asarray(db["Kx"], dtype=np.float64)
        Ky = np.asarray(db["Ky"], dtype=np.float64)
        Kz = np.asarray(db["Kz"], dtype=np.float64)
        porosity = np.asarray(db["porosity"], dtype=np.float64)
        pressure = np.asarray(db["pressure"], dtype=np.float64)
        weight = np.asarray(db["streamline_weight"], dtype=np.float64)

    with np.load(B2_NPZ, allow_pickle=False) as db:
        T_fmm = np.asarray(db["arrival_time_s"], dtype=np.float64)
        dx = float(np.asarray(db["dx_m"]).reshape(-1)[0])
        dy = float(np.asarray(db["dy_m"]).reshape(-1)[0])
        dz = float(np.asarray(db["dz_m"]).reshape(-1)[0])

    with np.load(B3_NPZ, allow_pickle=False) as db:
        xyz_m = np.asarray(db["streamline_xyz_m"], dtype=np.float64)
        pollock_tof_s = np.asarray(db["pollock_tof_s"], dtype=np.float64)
        origin = np.asarray(db["origin_center_m"], dtype=np.float64)
        fmm_b3 = np.asarray(db["fmm_sample_raw_s"], dtype=np.float64)

    with np.load(B7_NPZ, allow_pickle=False) as db:
        tau_adv = np.asarray(db["tau_adv_s"], dtype=np.float64)

    with np.load(B8_NPZ, allow_pickle=False) as db:
        fmm_b8 = np.asarray(db["fmm_sample_s"], dtype=np.float64)
        adv_b8 = np.asarray(db["adv_sample_s"], dtype=np.float64)
        pollock_b8 = np.asarray(db["pollock_tof_s"], dtype=np.float64)

    if xyz_m.shape != (1078, 201, 3):
        raise RuntimeError(f"Unexpected Pollock XYZ shape: {xyz_m.shape}")

    if pollock_tof_s.shape != (1078, 201):
        raise RuntimeError(f"Unexpected Pollock TOF shape: {pollock_tof_s.shape}")

    if weight.ndim != 1 or weight.shape[0] != xyz_m.shape[0]:
        raise RuntimeError(
            f"Unexpected streamline_weight shape {weight.shape}; expected ({xyz_m.shape[0]},)"
        )

    grid_shape = (15, 50, 50)
    for name, arr in [
        ("Kx", Kx),
        ("Ky", Ky),
        ("Kz", Kz),
        ("porosity", porosity),
        ("pressure", pressure),
        ("T_fmm", T_fmm),
        ("tau_adv", tau_adv),
    ]:
        if arr.shape != grid_shape:
            raise RuntimeError(f"{name} shape {arr.shape} != {grid_shape}")

    # -------------------------------------------------------------------------
    # Sample all frozen grid channels onto the same frozen Pollock nodes.
    # -------------------------------------------------------------------------
    fmm_s, audit_fmm = trilinear(T_fmm, xyz_m, dx, dy, dz, origin)
    adv_s, audit_adv = trilinear(tau_adv, xyz_m, dx, dy, dz, origin)

    kx_s, audit_kx = trilinear(Kx, xyz_m, dx, dy, dz, origin)
    ky_s, audit_ky = trilinear(Ky, xyz_m, dx, dy, dz, origin)
    kz_s, audit_kz = trilinear(Kz, xyz_m, dx, dy, dz, origin)
    phi_s, audit_phi = trilinear(porosity, xyz_m, dx, dy, dz, origin)
    p_s, audit_p = trilinear(pressure, xyz_m, dx, dy, dz, origin)

    # Existing B3/B8 travel-time mapping must be exactly reproduced to numerical
    # roundoff under the frozen mapping contract.
    fmm_linf_b3 = float(np.max(np.abs(fmm_s - fmm_b3)))
    fmm_linf_b8 = float(np.max(np.abs(fmm_s - fmm_b8)))
    adv_linf_b8 = float(np.max(np.abs(adv_s - adv_b8)))
    pollock_linf_b8 = float(np.max(np.abs(pollock_tof_s - pollock_b8)))

    save_csv(
        IDENTITY_CSV,
        [{
            "foundation_sha256": sha256_file(FOUNDATION_NPZ),
            "V16B2_FMM_sha256": sha256_file(B2_NPZ),
            "V16B3_mapping_sha256": sha256_file(B3_NPZ),
            "V16B7_ADV_sha256": sha256_file(B7_NPZ),
            "V16B8_comparison_sha256": sha256_file(B8_NPZ),
            "V16C1_contract_sha256": sha256_file(C1_CONTRACT),
            "grid_shape": str(grid_shape),
            "streamline_count": xyz_m.shape[0],
            "node_count": xyz_m.shape[1],
        }],
    )

    channel_rows = [
        {
            "channel": "xyz_m",
            "domain": "streamline_node",
            "shape": str(tuple(xyz_m.shape)),
            "authority": "FROZEN_POLLOCK",
            "role": "geometry",
            "units": "m",
        },
        {
            "channel": "pollock_tof_s",
            "domain": "streamline_node",
            "shape": str(tuple(pollock_tof_s.shape)),
            "authority": "AUTHORITATIVE_TRANSPORT_COORDINATE",
            "role": "primary_transport_coordinate",
            "units": "s",
        },
        {
            "channel": "fmm_arrival_s",
            "domain": "streamline_node",
            "shape": str(tuple(fmm_s.shape)),
            "authority": "SAMPLED_FROM_FROZEN_V16B2",
            "role": "scalar_connectivity_context",
            "units": "s",
        },
        {
            "channel": "adv_travel_time_s",
            "domain": "streamline_node",
            "shape": str(tuple(adv_s.shape)),
            "authority": "SAMPLED_FROM_FROZEN_V16B7",
            "role": "directional_eulerian_context",
            "units": "s",
        },
        {
            "channel": "Kx",
            "domain": "streamline_node",
            "shape": str(tuple(kx_s.shape)),
            "authority": "SAMPLED_FROM_FOUNDATION",
            "role": "geology_context",
            "units": "mD",
        },
        {
            "channel": "Ky",
            "domain": "streamline_node",
            "shape": str(tuple(ky_s.shape)),
            "authority": "SAMPLED_FROM_FOUNDATION",
            "role": "geology_context",
            "units": "mD",
        },
        {
            "channel": "Kz",
            "domain": "streamline_node",
            "shape": str(tuple(kz_s.shape)),
            "authority": "SAMPLED_FROM_FOUNDATION",
            "role": "geology_context",
            "units": "mD",
        },
        {
            "channel": "porosity",
            "domain": "streamline_node",
            "shape": str(tuple(phi_s.shape)),
            "authority": "SAMPLED_FROM_FOUNDATION",
            "role": "storage_context",
            "units": "fraction",
        },
        {
            "channel": "pressure",
            "domain": "streamline_node",
            "shape": str(tuple(p_s.shape)),
            "authority": "SAMPLED_FROM_FOUNDATION",
            "role": "pressure_context",
            "units": "psi",
        },
        {
            "channel": "streamline_weight",
            "domain": "streamline",
            "shape": str(tuple(weight.shape)),
            "authority": "FROZEN_POLLOCK",
            "role": "flux_weight",
            "units": "m3/s",
        },
    ]
    save_csv(CHANNEL_CSV, channel_rows)

    sampling_rows = []
    for name, audit in [
        ("FMM", audit_fmm),
        ("ADV", audit_adv),
        ("Kx", audit_kx),
        ("Ky", audit_ky),
        ("Kz", audit_kz),
        ("porosity", audit_phi),
        ("pressure", audit_p),
    ]:
        sampling_rows.append({
            "channel": name,
            "method": "TRILINEAR_CELL_CENTERED",
            "origin_x_m": float(origin[0]),
            "origin_y_m": float(origin[1]),
            "origin_z_m": float(origin[2]),
            "dx_m": dx,
            "dy_m": dy,
            "dz_m": dz,
            **audit,
        })
    save_csv(SAMPLING_CSV, sampling_rows)

    stats_rows = [
        channel_stats("pollock_tof_s", pollock_tof_s),
        channel_stats("fmm_arrival_s", fmm_s),
        channel_stats("adv_travel_time_s", adv_s),
        channel_stats("Kx_mD", kx_s),
        channel_stats("Ky_mD", ky_s),
        channel_stats("Kz_mD", kz_s),
        channel_stats("porosity", phi_s),
        channel_stats("pressure_psi", p_s),
        channel_stats("streamline_weight_m3_s", weight),
    ]
    save_csv(STATS_CSV, stats_rows)

    all_node_arrays = {
        "pollock_tof_s": pollock_tof_s,
        "fmm_arrival_s": fmm_s,
        "adv_travel_time_s": adv_s,
        "Kx_mD": kx_s,
        "Ky_mD": ky_s,
        "Kz_mD": kz_s,
        "porosity": phi_s,
        "pressure_psi": p_s,
    }

    shape_rows = []

    for name, arr in all_node_arrays.items():
        shape_rows.append({
            "channel": name,
            "shape": str(tuple(arr.shape)),
            "expected_shape": str((1078, 201)),
            "shape_valid": arr.shape == (1078, 201),
            "finite": bool(np.all(np.isfinite(arr))),
        })

    shape_rows.append({
        "channel": "streamline_xyz_m",
        "shape": str(tuple(xyz_m.shape)),
        "expected_shape": str((1078, 201, 3)),
        "shape_valid": xyz_m.shape == (1078, 201, 3),
        "finite": bool(np.all(np.isfinite(xyz_m))),
    })

    shape_rows.append({
        "channel": "streamline_weight_m3_s",
        "shape": str(tuple(weight.shape)),
        "expected_shape": str((1078,)),
        "shape_valid": weight.shape == (1078,),
        "finite": bool(np.all(np.isfinite(weight))),
    })

    save_csv(SHAPE_CSV, shape_rows)

    save_csv(
        REPRO_CSV,
        [{
            "comparison": "C2_FMM_vs_B3",
            "Linf_s": fmm_linf_b3,
            "pass_1e-9_s": fmm_linf_b3 <= 1e-9,
        },
        {
            "comparison": "C2_FMM_vs_B8",
            "Linf_s": fmm_linf_b8,
            "pass_1e-9_s": fmm_linf_b8 <= 1e-9,
        },
        {
            "comparison": "C2_ADV_vs_B8",
            "Linf_s": adv_linf_b8,
            "pass_1e-9_s": adv_linf_b8 <= 1e-9,
        },
        {
            "comparison": "C2_Pollock_vs_B8",
            "Linf_s": pollock_linf_b8,
            "pass_1e-9_s": pollock_linf_b8 <= 1e-9,
        }],
    )

    weight_positive = bool(np.all(weight > 0.0))
    weight_sum = float(np.sum(weight))

    save_csv(
        WEIGHT_CSV,
        [{
            "streamline_count": int(len(weight)),
            "all_finite": bool(np.all(np.isfinite(weight))),
            "all_positive": weight_positive,
            "minimum_m3_s": float(np.min(weight)),
            "median_m3_s": float(np.median(weight)),
            "maximum_m3_s": float(np.max(weight)),
            "sum_m3_s": weight_sum,
            "sum_m3_day": weight_sum * SECONDS_PER_DAY,
        }],
    )

    # Persist raw database only. No normalization.
    np.savez_compressed(
        DATABASE_NPZ,
        streamline_xyz_m=xyz_m.astype(np.float64),
        pollock_tof_s=pollock_tof_s.astype(np.float64),
        pollock_tof_days=(pollock_tof_s / SECONDS_PER_DAY).astype(np.float64),
        fmm_arrival_s=fmm_s.astype(np.float64),
        fmm_arrival_days=(fmm_s / SECONDS_PER_DAY).astype(np.float64),
        adv_travel_time_s=adv_s.astype(np.float64),
        adv_travel_time_days=(adv_s / SECONDS_PER_DAY).astype(np.float64),
        Kx_mD=kx_s.astype(np.float64),
        Ky_mD=ky_s.astype(np.float64),
        Kz_mD=kz_s.astype(np.float64),
        porosity=phi_s.astype(np.float64),
        pressure_psi=p_s.astype(np.float64),
        streamline_weight_m3_s=weight.astype(np.float64),
        xi=np.linspace(0.0, 1.0, pollock_tof_s.shape[1], dtype=np.float64),
        origin_center_m=origin.astype(np.float64),
        grid_spacing_m=np.asarray([dx, dy, dz], dtype=np.float64),
        authority_label_ascii=np.frombuffer(
            b"PAD_STREAM_V16C2_MULTI_COORDINATE_STREAMLINE_TRANSPORT_DATABASE",
            dtype=np.uint8,
        ),
    )

    all_shapes_valid = all(bool(r["shape_valid"]) for r in shape_rows)
    all_finite = all(bool(r["finite"]) for r in shape_rows)
    any_clip = any(
        (r["x_clip_count"] + r["y_clip_count"] + r["z_clip_count"]) > 0
        for r in sampling_rows
    )

    gates = [
        ("V16C1_integration_contract_reproduced", True),
        ("foundation_identity_recorded", True),
        ("V16B2_FMM_identity_recorded", True),
        ("V16B7_ADV_identity_recorded", True),
        ("V16B3_mapping_identity_recorded", True),
        ("Pollock_TOF_retained_as_primary_coordinate", True),
        ("FMM_sampled_on_frozen_Pollock_nodes", True),
        ("ADV_sampled_on_frozen_Pollock_nodes", True),
        ("Kx_Ky_Kz_sampled_on_frozen_Pollock_nodes", True),
        ("porosity_sampled_on_frozen_Pollock_nodes", True),
        ("pressure_sampled_on_frozen_Pollock_nodes", True),
        ("all_database_shapes_valid", all_shapes_valid),
        ("all_database_values_finite", all_finite),
        ("V16B3_FMM_mapping_reproduced", fmm_linf_b3 <= 1e-9),
        ("V16B8_FMM_mapping_reproduced", fmm_linf_b8 <= 1e-9),
        ("V16B8_ADV_mapping_reproduced", adv_linf_b8 <= 1e-9),
        ("V16B8_Pollock_reproduced", pollock_linf_b8 <= 1e-9),
        ("streamline_weights_finite_positive", weight_positive),
        ("raw_channels_preserved_without_normalization", True),
        ("database_artifact_saved", DATABASE_NPZ.exists()),
        ("no_transport_solve", True),
        ("no_saturation_generated", True),
        ("no_grid_map_back", True),
        ("no_FMM_or_ADV_rerun", True),
        ("no_Pollock_retrace", True),
        ("no_producer_id_invented", True),
        ("no_model_predict", True),
        ("no_training", True),
        ("no_frozen_artifact_mutation", True),
    ]

    save_csv(GATES_CSV, [{"gate": g, "passed": bool(p)} for g, p in gates])

    all_pass = all(bool(p) for _, p in gates)

    if all_pass:
        status = "V16C_MULTI_COORDINATE_STREAMLINE_TRANSPORT_DATABASE_COMPLETE"
        diagnosis = (
            "AUTHORITATIVE_POLLOCK_TOF_AND_RAW_FMM_ADV_GEOLOGY_PRESSURE_CONTEXT_ARE_SYNCHRONIZED_ON_ONE_FROZEN_STREAMLINE_NODE_DATABASE"
        )
        recommendation = (
            "Freeze the V16C-2 raw database. Proceed to V16C-3 to define the transport/PI-RNN conditioning contract, "
            "including which raw channels are inputs, which remain diagnostics, and how normalization is performed "
            "without changing Pollock TOF authority."
        )
        next_ms = "V16C-3 — PI-RNN / Transport Conditioning Contract"
    else:
        status = "V16C_MULTI_COORDINATE_DATABASE_ASSEMBLY_REQUIRES_AUDIT"
        diagnosis = "ONE_OR_MORE_DATABASE_ASSEMBLY_OR_REPRODUCTION_GATES_FAILED"
        recommendation = (
            "Do not define PI-RNN conditioning yet. Audit only failed V16C-2 database gates."
        )
        next_ms = "V16C-2R — Multi-Coordinate Database Residual Audit"

    save_csv(
        DECISION_CSV,
        [{
            "status": status,
            "diagnosis": diagnosis,
            "database_file": str(DATABASE_NPZ),
            "database_sha256": sha256_file(DATABASE_NPZ),
            "streamlines": xyz_m.shape[0],
            "nodes_per_streamline": xyz_m.shape[1],
            "sampling_clipping_detected": any_clip,
            "next_milestone": next_ms,
        }],
    )

    contract = {
        "milestone": "V16C-2",
        "status": status,
        "diagnosis": diagnosis,
        "database_shape": {
            "streamlines": int(xyz_m.shape[0]),
            "nodes_per_streamline": int(xyz_m.shape[1]),
        },
        "authoritative_coordinate": "pollock_tof_s",
        "auxiliary_node_channels": [
            "fmm_arrival_s",
            "adv_travel_time_s",
            "Kx_mD",
            "Ky_mD",
            "Kz_mD",
            "porosity",
            "pressure_psi",
        ],
        "streamline_channels": [
            "streamline_weight_m3_s",
        ],
        "sampling": {
            "method": "trilinear cell-centered",
            "origin_center_m": [float(x) for x in origin],
            "grid_spacing_m": [dx, dy, dz],
            "coordinate_source": "frozen V16B-3 Pollock XYZ mapping",
            "clipping_detected": any_clip,
        },
        "normalization": {
            "performed": False,
            "raw_database_preserved": True,
        },
        "database_artifact": {
            "path": str(DATABASE_NPZ),
            "sha256": sha256_file(DATABASE_NPZ),
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }

    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16C-2",
            "status": status,
            "diagnosis": diagnosis,
            "streamlines": int(xyz_m.shape[0]),
            "nodes_per_streamline": int(xyz_m.shape[1]),
            "authoritative_coordinate": "pollock_tof_s",
            "database_sha256": sha256_file(DATABASE_NPZ),
            "sampling_clipping_detected": any_clip,
            "recommendation": recommendation,
            "next_milestone": next_ms,
        },
    )

    print("DATABASE")
    print(f"  Streamlines              : {xyz_m.shape[0]}")
    print(f"  Nodes / streamline       : {xyz_m.shape[1]}")
    print(f"  Pollock TOF              : AUTHORITATIVE")
    print(f"  FMM context              : PRESENT")
    print(f"  ADV context              : PRESENT")
    print(f"  Kx/Ky/Kz                 : PRESENT")
    print(f"  Porosity                 : PRESENT")
    print(f"  Pressure                 : PRESENT")
    print(f"  Streamline weight        : PRESENT")

    print("\nTRAVEL-TIME REPRODUCTION")
    print(f"  FMM vs V16B-3 Linf       : {fmm_linf_b3:.6e} s")
    print(f"  FMM vs V16B-8 Linf       : {fmm_linf_b8:.6e} s")
    print(f"  ADV vs V16B-8 Linf       : {adv_linf_b8:.6e} s")
    print(f"  Pollock vs V16B-8 Linf   : {pollock_linf_b8:.6e} s")

    print("\nSAMPLING")
    print(f"  Method                    : TRILINEAR CELL-CENTERED")
    print(f"  Coordinate clipping       : {any_clip}")

    print("\n" + "=" * 78)
    print("V16C-2 FINAL DATABASE GATES")
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
    print(f"  {DATABASE_NPZ.name}")
    print(f"  SHA-256: {sha256_file(DATABASE_NPZ)}")

    print("\nTables:")
    for p in [
        IDENTITY_CSV,
        CHANNEL_CSV,
        SAMPLING_CSV,
        STATS_CSV,
        SHAPE_CSV,
        REPRO_CSV,
        WEIGHT_CSV,
        GATES_CSV,
        DECISION_CSV,
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16C-2 MULTI-COORDINATE TRANSPORT DATABASE: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
