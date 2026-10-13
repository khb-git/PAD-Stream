from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import zipfile
from typing import Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MILESTONE = "POSTV16-D2"
STATUS = "POSTV16_STREAMLINE_TO_GRID_CO2_SATURATION_ATTRIBUTION_AUDIT_COMPLETED"
NEXT = "POSTV16-D2 interpretation gate - decide whether POSTV16-D3 variable-porosity sensitivity is scientifically warranted or proceed to IBDP"
RELEASE_ID = "PAD-STREAM-V16-RC1-B92D52088D01078A"
RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_A1_CACHE_SHA256 = "2acbbbc8608eb771d1a6ea6909c7d37caec2ee77666a7828226e3a9e531d316e"
EXPECTED_TERMINAL_RESTART_SHA256 = "af0097b5e7befc7417286fbb90cc2139a3dab583cb3cce972c9293c7b7fe0a7e"

S_BACKGROUND = 0.20
POROSITY = 0.20
DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0
FT_TO_M = 0.3048
DAY_TO_S = 86400.0
LAYER8_K = 7
GRID_SHAPE = (15, 50, 50)
FLOW_DAYS_EXPECTED = np.asarray([100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0])
PLOT_DAYS = np.asarray([30.0, 100.0, 250.0, 500.0, 750.0, 1000.0])
FIGS = [f"D2-{i:02d}" for i in range(1, 9)]

SOURCES = {
    "A1": ("PAD_Stream_V16VIS_A1_Visual_Authority_Manifest_and_Data_Extraction.py", "7ed31f0e69b63489f25a1833cdc3693f735b1233"),
    "C1": ("PAD_Stream_V16VIS_C1_Final_V16_Visual_Package_Integration_and_Closeout_Audit.py", "d2b18f1a75fdefc1778e6350b7a16551b1a76a1b"),
    "D1": ("PAD_Stream_POSTV16_D1_Heterogeneity_to_Plume_Response_Diagnostic_Audit.py", "2425b74e2f40f8b6e1b3bccda485c2d6788e90a8"),
    "SG2": ("PAD_Stream_V15SG2_Anisotropic_Transmissibility.py", "7242012d3e758472abc3ee7f543831b92d2cf419"),
    "SG3": ("PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py", "66a379cd97ee9120f69e7e7e949171541e4918c3"),
    "SG4": ("PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py", "8d49f88bdf55b0da087af2bed04e69967740e695"),
    "SG5": ("PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py", "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"),
    "SG6": ("PAD_Stream_V15SG6_TOF_Transport_Coordinates.py", "70ceda68e02894167958d753d88b4dbd694731ab"),
    "SG7A": ("PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py", "a4dd47338e7a85f130a6a70d0a41211e38c655f8"),
    "R3R2R1": ("PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py", "740c6da03e73906646bf0153633187e749449f31"),
    "R3R4R1": ("PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py", "5f8433437ce111533338ceada922f51abb2edefe"),
    "R2": ("PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py", "a127f8730a16e150713420ea547a8de6255550ef"),
    "E37A": ("PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py", "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"),
    "E47": ("PAD_Stream_V16E47_Repaired_Production_Continuation_to_Exact_1000Day_Observation.py", "b3f6a4212e18e13239eb7bd5703c43484b376dcb"),
}

A1_REL = Path("visuals") / RID / "Phase_A_Authority_and_Data_Extraction"
C1_REL = Path("visuals") / RID / "Phase_C1_Final_Visual_Package_Closeout"
D1_REL = Path("post_v16") / RID / "POSTV16_D1_Heterogeneity_to_Plume_Response_Diagnostic_Audit"
E47_REL = Path("provenance/hybrid_dp/V16E47_REPAIRED_PRODUCTION_EXACT_1000D_OBSERVATION")
E47_RESTART = "V16E47_Authoritative_1000d_PostObservation_Refreshed_Restart.npz"
OUT_REL = Path("post_v16") / RID / "POSTV16_D2_Streamline_to_Grid_CO2_Saturation_Attribution_Audit"
BLOCKED_REL = Path("post_v16") / RID / "POSTV16_D2_BLOCKED"


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_blob_sha(path: Path, root: Path) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), "hash-object", str(path)],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def immutable_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise GateError(f"existing_output_differs:{path.name}")
    else:
        path.write_bytes(data)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"module_load_failed:{path}")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def save_figure(fig: plt.Figure, out: Path, stem: str) -> list[dict[str, Any]]:
    rows = []
    for ext in ("png", "pdf"):
        p = out / f"{stem}.{ext}"
        if p.exists():
            raise GateError(f"existing_figure:{p.name}")
        fig.savefig(p, dpi=300, bbox_inches="tight")
        rows.append({"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size})
    plt.close(fig)
    return rows


def quantile_stats(values: np.ndarray) -> dict[str, float]:
    a = np.asarray(values, dtype=np.float64).ravel()
    a = a[np.isfinite(a)]
    if a.size == 0:
        return {k: float("nan") for k in ["min", "p01", "p05", "p10", "p25", "p50", "p75", "p90", "p95", "p99", "max", "mean", "std"]}
    q = np.quantile(a, [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99])
    return {
        "min": float(np.min(a)), "p01": float(q[0]), "p05": float(q[1]), "p10": float(q[2]),
        "p25": float(q[3]), "p50": float(q[4]), "p75": float(q[5]), "p90": float(q[6]),
        "p95": float(q[7]), "p99": float(q[8]), "max": float(np.max(a)),
        "mean": float(np.mean(a)), "std": float(np.std(a)),
    }


def corr(a: np.ndarray, b: np.ndarray) -> float:
    x = np.asarray(a, dtype=np.float64).ravel()
    y = np.asarray(b, dtype=np.float64).ravel()
    m = np.isfinite(x) & np.isfinite(y)
    if np.count_nonzero(m) < 3:
        return float("nan")
    x = x[m]; y = y[m]
    if np.std(x) <= 1e-15 or np.std(y) <= 1e-15:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def coords_to_cell(points_m: np.ndarray, shape: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    p = np.asarray(points_m, dtype=np.float64)
    dx = DX_FT * FT_TO_M; dy = DY_FT * FT_TO_M; dz = DZ_FT * FT_TO_M
    i = np.clip(np.floor(p[:, 0] / dx).astype(int), 0, shape[2] - 1)
    j = np.clip(np.floor(p[:, 1] / dy).astype(int), 0, shape[1] - 1)
    k = np.clip(np.floor(p[:, 2] / dz).astype(int), 0, shape[0] - 1)
    return k, j, i


def streamline_cell_mask(streamlines: list[dict[str, Any]], shape: tuple[int, int, int]) -> np.ndarray:
    mask = np.zeros(shape, dtype=bool)
    for s in streamlines:
        pts = np.asarray(s["points_m"], dtype=np.float64)
        if pts.ndim != 2 or pts.shape[0] == 0:
            continue
        if pts.shape[0] == 1:
            sample = pts
        else:
            mid = 0.5 * (pts[:-1] + pts[1:])
            sample = np.vstack([pts[:1], mid, pts[-1:]])
        k, j, i = coords_to_cell(sample, shape)
        mask[k, j, i] = True
    return mask


def build_flow_streamlines(mods: dict[str, Any], perm: np.ndarray, sat: np.ndarray, pressure: np.ndarray):
    sg2, sg3, sg4, sg5, r3 = mods["SG2"], mods["SG3"], mods["SG4"], mods["SG5"], mods["R3R2R1"]
    kx, ky, kz = sg2.build_directional_permeability(perm)
    kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
    tx0, ty0, tz0 = sg3.construct_si_transmissibilities(kfx, kfy, kfz)
    mobility = r3.phase_mobility_fields(sat)
    tx, ty, tz, _ = r3.build_updated_transmissibilities(sg3, tx0, ty0, tz0, mobility["lambda_total"])
    qx, qy, qz = sg4.compute_face_fluxes(pressure, tx, ty, tz)
    vx, vy, vz = sg5.construct_face_pore_velocities(qx, qy, qz)
    faces, seeds = sg5.build_seeds(qx, qy, qz)
    streamlines = sg5.trace_streamlines(seeds, vx, vy, vz)
    captured = [s for s in streamlines if s["status"] == "PRODUCER"]
    if len(captured) != len(streamlines):
        raise GateError(f"nonproducer_streamlines:{len(captured)}:{len(streamlines)}")
    return streamlines, faces, seeds


def capillary_mass_tendency(r2: Any, sat: np.ndarray, perm: np.ndarray, pressure: np.ndarray, p_ref_pa: float) -> np.ndarray:
    S = np.asarray(sat, dtype=np.float64)
    k_md = np.asarray(perm, dtype=np.float64)
    p = np.asarray(pressure, dtype=np.float64)
    Dx, Dy, Dz = r2._capillary_diffusion_coefficients_kji(S, k_md)
    dx = DX_FT * FT_TO_M; dy = DY_FT * FT_TO_M; dz = DZ_FT * FT_TO_M
    ax = dy * dz; ay = dx * dz; az = dx * dy
    tx = ax * 0.5 * (Dx[:, :, :-1] + Dx[:, :, 1:]) / dx
    ty = ay * 0.5 * (Dy[:, :-1, :] + Dy[:, 1:, :]) / dy
    tz = az * 0.5 * (Dz[:-1, :, :] + Dz[1:, :, :]) / dz
    qx = -tx * (S[:, :, 1:] - S[:, :, :-1])
    qy = -ty * (S[:, 1:, :] - S[:, :-1, :])
    qz = -tz * (S[1:, :, :] - S[:-1, :, :])
    rho = r2.gas_density_from_state(S, p, p_ref_pa)
    mx = qx * np.where(qx >= 0.0, rho[:, :, :-1], rho[:, :, 1:])
    my = qy * np.where(qy >= 0.0, rho[:, :-1, :], rho[:, 1:, :])
    mz = qz * np.where(qz >= 0.0, rho[:-1, :, :], rho[1:, :, :])
    div = np.zeros(GRID_SHAPE, dtype=np.float64)
    div[:, :, :-1] += mx; div[:, :, 1:] -= mx
    div[:, :-1, :] += my; div[:, 1:, :] -= my
    div[:-1, :, :] += mz; div[1:, :, :] -= mz
    return -div


def self_test() -> None:
    if S_BACKGROUND != 0.20 or POROSITY != 0.20:
        raise RuntimeError("frozen_porosity_or_background")
    if tuple(GRID_SHAPE) != (15, 50, 50):
        raise RuntimeError("grid")
    if len(FIGS) != 8:
        raise RuntimeError("figure_count")
    if not np.array_equal(FLOW_DAYS_EXPECTED, np.asarray([100., 150., 250., 365., 500., 750., 1000.])):
        raise RuntimeError("flow_days")
    a = np.asarray([0.0, 0.1, 0.2, 0.3])
    s = quantile_stats(a)
    if abs(s["mean"] - 0.15) > 1e-12:
        raise RuntimeError("stats")
    print("PAD-Stream POSTV16-D2 streamline-to-grid CO2 saturation attribution self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL
    gates: dict[str, dict[str, Any]] = {}
    stage: str | None = None

    def gate(name: str, ok: Any, detail: Any = "") -> None:
        passed = bool(ok)
        gates[name] = {"passed": passed, "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 164)
        print("PAD-Stream POSTV16-D2 — Streamline-to-Grid CO2 Saturation Attribution Audit")
        print("=" * 164)
        print("Release                    :", RELEASE_ID)
        print("V16 mutation               : none")
        print("Transport rerun            : none")
        print("Flow reconstruction        : read-only at seven frozen post-refresh checkpoints")
        print("Frozen porosity            : 0.20 constant; no porosity sensitivity is executed in D2")

        stage = "source_binding"
        for role, (fn, expected_blob) in SOURCES.items():
            p = root / fn
            gate(f"{role}_source_exists", p.is_file(), p)
            actual = git_blob_sha(p, root)
            gate(f"{role}_blob_exact", actual == expected_blob, actual)

        stage = "closed_authority_chain"
        a1 = drive / A1_REL
        c1 = drive / C1_REL
        d1 = drive / D1_REL
        for p in [
            a1 / "PAD_Stream_V16VIS_A1_Summary.json",
            a1 / "V16VIS_A1_Final_Closure.json",
            a1 / "V16VIS_A1_Authoritative_Visual_Data.npz",
            c1 / "PAD_Stream_V16VIS_C1_Summary.json",
            c1 / "V16VIS_C1_Final_Closure.json",
            d1 / "PAD_Stream_POSTV16_D1_Summary.json",
            d1 / "POSTV16_D1_Final_Closure.json",
        ]:
            gate(f"exists_{p.name}", p.is_file(), p)
        a1s = load_json(a1 / "PAD_Stream_V16VIS_A1_Summary.json")
        a1c = load_json(a1 / "V16VIS_A1_Final_Closure.json")
        c1s = load_json(c1 / "PAD_Stream_V16VIS_C1_Summary.json")
        c1c = load_json(c1 / "V16VIS_C1_Final_Closure.json")
        d1s = load_json(d1 / "PAD_Stream_POSTV16_D1_Summary.json")
        d1c = load_json(d1 / "POSTV16_D1_Final_Closure.json")
        gate("A1_closed", a1c.get("all_gates_passed") is True)
        gate("C1_closed", c1s.get("status") == "FINAL_V16_VISUAL_PACKAGE_INTEGRATED_AND_CLOSED" and c1c.get("V16_visual_package_formally_closed") is True)
        gate("D1_closed", d1s.get("status") == "POSTV16_HETEROGENEITY_TO_PLUME_RESPONSE_DIAGNOSTIC_AUDIT_COMPLETED" and d1c.get("diagnostic_audit_complete") is True)
        gate("D1_no_mutation", d1c.get("accepted_simulation_state_modified") is False and d1c.get("V16_release_modified") is False)

        cache = a1 / "V16VIS_A1_Authoritative_Visual_Data.npz"
        cache_sha = sha256_file(cache)
        gate("A1_cache_SHA_exact", cache_sha == EXPECTED_A1_CACHE_SHA256, cache_sha)
        gate("A1_summary_cache_SHA_exact", a1s.get("visual_cache_sha256") == cache_sha)

        stage = "frozen_arrays"
        with np.load(cache, allow_pickle=False) as z:
            perm = np.asarray(z["permeability_md"], dtype=np.float64)
            x = np.asarray(z["x_center_ft"], dtype=np.float64)
            y = np.asarray(z["y_center_ft"], dtype=np.float64)
            depth = np.asarray(z["depth_center_ft"], dtype=np.float64)
            plume_days = np.asarray(z["plume_days"], dtype=np.float64)
            plume_sat = np.asarray(z["plume_saturation"], dtype=np.float64)
            flow_days = np.asarray(z["flow_days"], dtype=np.float64)
            flow_sat = np.asarray(z["flow_saturation"], dtype=np.float64)
            flow_p = np.asarray(z["flow_pressure_psi"], dtype=np.float64)
        gate("perm_shape", perm.shape == GRID_SHAPE, perm.shape)
        gate("plume_shape", plume_sat.shape == (9,) + GRID_SHAPE, plume_sat.shape)
        gate("flow_shape", flow_sat.shape == flow_p.shape and flow_sat.shape[1:] == GRID_SHAPE, flow_sat.shape)
        gate("flow_days_exact", np.array_equal(flow_days, FLOW_DAYS_EXPECTED), flow_days.tolist())
        sg_obs = plume_sat - S_BACKGROUND
        sg_flow = flow_sat - S_BACKGROUND
        gate("CO2_saturation_finite", np.all(np.isfinite(sg_obs)) and np.all(np.isfinite(sg_flow)))
        gate("CO2_saturation_nonnegative", float(np.min(sg_obs)) >= -1.0e-3, float(np.min(sg_obs)))
        gate("constant_porosity_contract", POROSITY == 0.20)

        stage = "terminal_restart_thermodynamic_authority"
        restart = drive / E47_REL / E47_RESTART
        gate("terminal_restart_exists", restart.is_file(), restart)
        restart_sha = sha256_file(restart)
        gate("terminal_restart_SHA_exact", restart_sha == EXPECTED_TERMINAL_RESTART_SHA256, restart_sha)
        with np.load(restart, allow_pickle=False) as z:
            restart_sat = np.asarray(z["transport_saturation"], dtype=np.float64)
            restart_p = np.asarray(z["accepted_pressure_psi"], dtype=np.float64)
            p_ref_pa = float(np.asarray(z["co2_density_reference_pressure_pa"]).reshape(()))
            restart_stored_mass = float(np.asarray(z["stored_co2_mass_current_kg"]).reshape(()))
        gate("terminal_restart_sat_matches_A1_flow", np.array_equal(restart_sat, flow_sat[-1]))
        gate("terminal_restart_pressure_matches_A1_flow", np.array_equal(restart_p, flow_p[-1]))
        gate("terminal_p_ref_positive", np.isfinite(p_ref_pa) and p_ref_pa > 0.0, p_ref_pa)

        if out.exists() and any(out.iterdir()):
            raise GateError("D2_output_directory_not_empty")
        out.mkdir(parents=True, exist_ok=True)

        stage = "load_frozen_modules"
        mods = {role: load_module(root / SOURCES[role][0], f"postv16_d2_{role.lower()}") for role in ["SG2", "SG3", "SG4", "SG5", "SG6", "R3R2R1", "R3R4R1", "R2"]}
        r2 = mods["R2"]

        # ------------------------------------------------------------------
        # D2-01: full CO2 saturation census.
        # ------------------------------------------------------------------
        stage = "D2_01_global_saturation_census"
        global_rows: list[dict[str, Any]] = []
        for day, field in zip(plume_days, sg_obs):
            row = {"day": float(day), **quantile_stats(field)}
            row["coefficient_of_variation"] = row["std"] / max(abs(row["mean"]), 1e-30)
            global_rows.append(row)
        immutable_write(out / "POSTV16_D2_Global_CO2_Saturation_Census.csv", csv_bytes(global_rows))

        fig, ax = plt.subplots(figsize=(9.5, 6.2))
        td = np.asarray([r["day"] for r in global_rows])
        p10 = np.asarray([r["p10"] for r in global_rows]); p90 = np.asarray([r["p90"] for r in global_rows])
        p25 = np.asarray([r["p25"] for r in global_rows]); p75 = np.asarray([r["p75"] for r in global_rows])
        med = np.asarray([r["p50"] for r in global_rows]); mean = np.asarray([r["mean"] for r in global_rows])
        ax.fill_between(td, p10, p90, alpha=0.22, label="P10–P90")
        ax.fill_between(td, p25, p75, alpha=0.32, label="P25–P75")
        ax.plot(td, med, marker="o", label="Median $S_g$")
        ax.plot(td, mean, marker="s", label="Mean $S_g$")
        ax.set_xlabel("Time, days"); ax.set_ylabel("Incremental CO$_2$ saturation, $S_g=S-0.20$")
        ax.set_title("D2-01 — Full-grid individual CO₂ saturation census")
        ax.grid(alpha=0.25); ax.legend()
        rendered = save_figure(fig, out, "D2_01_Full_Grid_CO2_Saturation_Census")

        # ------------------------------------------------------------------
        # D2-02: layer census.
        # ------------------------------------------------------------------
        stage = "D2_02_layer_census"
        layer_rows: list[dict[str, Any]] = []
        layer_mean = np.zeros((len(plume_days), 15), dtype=float)
        for it, (day, field) in enumerate(zip(plume_days, sg_obs)):
            for k in range(15):
                stats = quantile_stats(field[k])
                layer_mean[it, k] = stats["mean"]
                layer_rows.append({"day": float(day), "physical_layer": k + 1, **stats})
        immutable_write(out / "POSTV16_D2_Layer_CO2_Saturation_Census.csv", csv_bytes(layer_rows))
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), constrained_layout=True)
        im = axes[0].imshow(layer_mean.T, origin="upper", aspect="auto", extent=[plume_days[0], plume_days[-1], 15.5, 0.5])
        axes[0].set_xlabel("Time, days"); axes[0].set_ylabel("Physical layer (1 shallowest)")
        axes[0].set_title("Mean $S_g$ by layer and time"); fig.colorbar(im, ax=axes[0], label="Mean $S_g$")
        term_rows = [r for r in layer_rows if r["day"] == 1000.0]
        layers = np.asarray([r["physical_layer"] for r in term_rows])
        axes[1].fill_betweenx(layers, [r["p10"] for r in term_rows], [r["p90"] for r in term_rows], alpha=0.25, label="P10–P90")
        axes[1].plot([r["p50"] for r in term_rows], layers, marker="o", label="Median")
        axes[1].plot([r["mean"] for r in term_rows], layers, marker="s", label="Mean")
        axes[1].invert_yaxis(); axes[1].set_xlabel("$S_g$ at 1000 d"); axes[1].set_ylabel("Physical layer")
        axes[1].set_title("1000-day layer distributions"); axes[1].legend()
        fig.suptitle("D2-02 — Vertical distribution of individual CO₂ saturation")
        rendered += save_figure(fig, out, "D2_02_Layer_CO2_Saturation_Census")

        # ------------------------------------------------------------------
        # D2-03: spatial-region census.
        # ------------------------------------------------------------------
        stage = "D2_03_region_census"
        X, Y = np.meshgrid(x, y, indexing="xy")
        R = np.hypot(X - 490.0, Y - 490.0)
        r3d = np.broadcast_to(R[None, :, :], GRID_SHAPE)
        xm = np.broadcast_to(X[None, :, :], GRID_SHAPE)
        ym = np.broadcast_to(Y[None, :, :], GRID_SHAPE)
        kvals = perm.ravel(); q20, q80 = np.quantile(kvals, [0.2, 0.8])
        masks: dict[str, np.ndarray] = {}
        m = np.zeros(GRID_SHAPE, bool); m[:5] = True; masks["upper_layers_1_5"] = m
        m = np.zeros(GRID_SHAPE, bool); m[5:10] = True; masks["completed_layers_6_10"] = m
        m = np.zeros(GRID_SHAPE, bool); m[10:] = True; masks["lower_layers_11_15"] = m
        masks["near_injector_R_le_200ft"] = r3d <= 200.0
        masks["mid_radius_200_400ft"] = (r3d > 200.0) & (r3d <= 400.0)
        masks["outer_radius_gt_400ft"] = r3d > 400.0
        masks["SW_quadrant"] = (xm < 500.0) & (ym < 500.0)
        masks["SE_quadrant"] = (xm >= 500.0) & (ym < 500.0)
        masks["NW_quadrant"] = (xm < 500.0) & (ym >= 500.0)
        masks["NE_quadrant"] = (xm >= 500.0) & (ym >= 500.0)
        masks["lowest_K_quintile"] = perm <= q20
        masks["highest_K_quintile"] = perm >= q80
        region_rows: list[dict[str, Any]] = []
        for day, field in zip(plume_days, sg_obs):
            for name, mask in masks.items():
                region_rows.append({"day": float(day), "region": name, "cell_count": int(np.count_nonzero(mask)), **quantile_stats(field[mask])})
        immutable_write(out / "POSTV16_D2_Spatial_Region_CO2_Saturation_Census.csv", csv_bytes(region_rows))
        fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.5), constrained_layout=True)
        for name in ["near_injector_R_le_200ft", "mid_radius_200_400ft", "outer_radius_gt_400ft"]:
            rr = [r for r in region_rows if r["region"] == name]
            axes[0].plot([r["day"] for r in rr], [r["mean"] for r in rr], marker="o", label=name.replace("_", " "))
        for name in ["upper_layers_1_5", "completed_layers_6_10", "lower_layers_11_15"]:
            rr = [r for r in region_rows if r["region"] == name]
            axes[1].plot([r["day"] for r in rr], [r["mean"] for r in rr], marker="o", label=name.replace("_", " "))
        for ax in axes:
            ax.set_xlabel("Time, days"); ax.set_ylabel("Mean $S_g$"); ax.grid(alpha=0.25); ax.legend(fontsize=8)
        axes[0].set_title("Radial regions"); axes[1].set_title("Vertical regions")
        fig.suptitle("D2-03 — CO₂ saturation in distinct reservoir regions")
        rendered += save_figure(fig, out, "D2_03_Spatial_Region_CO2_Saturation_Response")

        # ------------------------------------------------------------------
        # D2-04: within-time normalized plume contrast.
        # ------------------------------------------------------------------
        stage = "D2_04_normalized_plume"
        fig, axes = plt.subplots(2, 3, figsize=(14, 9), constrained_layout=True)
        extent = [0.0, 1000.0, 0.0, 1000.0]
        im = None
        normalized_rows = []
        for ax, day in zip(axes.ravel(), PLOT_DAYS):
            q = int(np.where(np.isclose(plume_days, day))[0][0])
            layer = sg_obs[q, LAYER8_K]
            lo = float(np.min(layer)); hi = float(np.max(layer)); span = max(hi - lo, 1e-12)
            sn = (layer - lo) / span
            im = ax.imshow(sn, origin="lower", extent=extent, vmin=0.0, vmax=1.0, aspect="equal")
            cs = ax.contour(sn, levels=[0.25, 0.50, 0.75], origin="lower", extent=extent, linewidths=1.0)
            ax.clabel(cs, fmt=lambda v: f"S*={v:.2f}", fontsize=7)
            ax.set_title(f"{day:.0f} d | raw $S_g$ {lo:.3f}–{hi:.3f}")
            ax.set_xlabel("X, ft"); ax.set_ylabel("Y, ft")
            normalized_rows.append({"day": float(day), "layer": 8, "raw_min_sg": lo, "raw_max_sg": hi, "raw_range_sg": hi - lo, "raw_std_sg": float(np.std(layer))})
        if im is not None:
            fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.82, label=r"Within-time normalized $S^*=(S_g-S_{g,min})/(S_{g,max}-S_{g,min})$")
        fig.suptitle("D2-04 — Plume geometry after removing the rising domain-wide saturation floor")
        immutable_write(out / "POSTV16_D2_Layer8_Normalized_Plume_Contrast.csv", csv_bytes(normalized_rows))
        rendered += save_figure(fig, out, "D2_04_Layer8_Within_Time_Normalized_Plume_Contrast")

        # ------------------------------------------------------------------
        # D2-05 and D2-06: flow-checkpoint reconstruction and cumulative support.
        # ------------------------------------------------------------------
        stage = "flow_checkpoint_reconstruction"
        coverage_rows: list[dict[str, Any]] = []
        support_rows: list[dict[str, Any]] = []
        cumulative = np.zeros(GRID_SHAPE, dtype=bool)
        checkpoint_masks: dict[float, np.ndarray] = {}
        terminal_streamlines = None
        terminal_db = None
        for it, day in enumerate(flow_days):
            print(f"\nRead-only flow-checkpoint Pollock reconstruction: {day:.0f} d", flush=True)
            sl, faces, seeds = build_flow_streamlines(mods, perm, flow_sat[it], flow_p[it])
            epoch_mask = streamline_cell_mask(sl, GRID_SHAPE)
            cumulative |= epoch_mask
            checkpoint_masks[float(day)] = cumulative.copy()
            obs_idx = int(np.where(np.isclose(plume_days, day))[0][0])
            obs_field = sg_obs[obs_idx]
            flow_field = sg_flow[it]
            outside = ~cumulative
            def mean_or_nan(a): return float(np.mean(a)) if a.size else float("nan")
            def median_or_nan(a): return float(np.median(a)) if a.size else float("nan")
            coverage_rows.append({
                "day": float(day), "streamline_count": len(sl), "outgoing_injector_faces": len(faces),
                "epoch_supported_cells": int(np.count_nonzero(epoch_mask)), "epoch_supported_fraction": float(np.mean(epoch_mask)),
                "cumulative_checkpoint_supported_cells": int(np.count_nonzero(cumulative)), "cumulative_checkpoint_supported_fraction": float(np.mean(cumulative)),
                "coverage_interpretation": "LOWER_BOUND_FROM_SEVEN_FROZEN_POST_REFRESH_FLOW_CHECKPOINTS",
            })
            support_rows.append({
                "day": float(day),
                "obs_mean_sg_inside_cumulative_support": mean_or_nan(obs_field[cumulative]),
                "obs_median_sg_inside_cumulative_support": median_or_nan(obs_field[cumulative]),
                "obs_mean_sg_outside_cumulative_support": mean_or_nan(obs_field[outside]),
                "obs_median_sg_outside_cumulative_support": median_or_nan(obs_field[outside]),
                "flow_mean_sg_inside_cumulative_support": mean_or_nan(flow_field[cumulative]),
                "flow_mean_sg_outside_cumulative_support": mean_or_nan(flow_field[outside]),
                "outside_cells": int(np.count_nonzero(outside)),
                "outside_fraction_obs_sg_gt_0p01": float(np.mean(obs_field[outside] > 0.01)) if np.any(outside) else 0.0,
                "outside_fraction_obs_sg_gt_0p05": float(np.mean(obs_field[outside] > 0.05)) if np.any(outside) else 0.0,
                "outside_fraction_obs_sg_gt_0p10": float(np.mean(obs_field[outside] > 0.10)) if np.any(outside) else 0.0,
            })
            if float(day) == 1000.0:
                terminal_streamlines = sl
                converted = mods["R3R4R1"].convert_sg5_to_sg6_streamlines(sl)
                terminal_db = mods["SG6"].build_transport_database(converted)
                mods["SG6"].validate_transport(terminal_db)
        gate("terminal_streamlines_available", terminal_streamlines is not None)
        gate("terminal_transport_database_available", terminal_db is not None)
        immutable_write(out / "POSTV16_D2_Flow_Checkpoint_Cumulative_Streamline_Coverage.csv", csv_bytes(coverage_rows))
        immutable_write(out / "POSTV16_D2_Cumulative_Support_vs_Saturation.csv", csv_bytes(support_rows))
        immutable_write(
            out / "POSTV16_D2_Flow_Checkpoint_Coverage_Masks.npz",
            deterministic_npz_bytes({f"cumulative_day_{int(day):04d}": mask for day, mask in checkpoint_masks.items()}),
        )

        stage = "D2_05_representative_streamline_profiles"
        assert terminal_db is not None
        tau_end_days = np.asarray(terminal_db["tau_end_s"], dtype=np.float64) / DAY_TO_S
        xi = np.asarray(terminal_db["xi"], dtype=np.float64)
        xyz = np.asarray(terminal_db["xyz_m"], dtype=np.float64)
        labels = np.asarray(terminal_db["producer"]).astype(str)
        targets = np.quantile(tau_end_days, [0.10, 0.50, 0.90])
        selected_idx: list[int] = []
        for target in targets:
            order = np.argsort(np.abs(tau_end_days - target))
            chosen = next(int(v) for v in order if int(v) not in selected_idx)
            selected_idx.append(chosen)
        profile_rows: list[dict[str, Any]] = []
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.3), constrained_layout=True)
        terminal_obs_sg = sg_obs[-1]
        for label_name, idx in zip(["short_TOF", "median_TOF", "long_TOF"], selected_idx):
            k, j, i = coords_to_cell(xyz[idx], GRID_SHAPE)
            prof = terminal_obs_sg[k, j, i]
            tau_path_days = np.asarray(terminal_db["tau_s"][idx], dtype=np.float64) / DAY_TO_S
            tend = float(tau_end_days[idx]); tD = 1000.0 / tend
            legend = f"{label_name}: τend={tend:.1f} d, tD={tD:.2f}, {labels[idx]}"
            axes[0].plot(xi, prof, linewidth=1.8, label=legend)
            axes[1].plot(xi, tau_path_days, linewidth=1.8, label=label_name)
            for n in range(len(xi)):
                profile_rows.append({
                    "selection": label_name, "streamline_index": idx, "producer": labels[idx],
                    "tau_end_days": tend, "dimensionless_time_1000d_over_tau_end": tD,
                    "xi": float(xi[n]), "tau_days": float(tau_path_days[n]),
                    "sampled_pre_refresh_CO2_saturation_sg": float(prof[n]),
                    "k": int(k[n]), "j": int(j[n]), "i": int(i[n]),
                })
        axes[0].set_xlabel(r"Normalized streamline coordinate $\xi$"); axes[0].set_ylabel("Sampled frozen grid $S_g$")
        axes[0].set_title("1000-day CO₂ saturation sampled along representative streamlines"); axes[0].legend(fontsize=7)
        axes[1].set_xlabel(r"Normalized streamline coordinate $\xi$"); axes[1].set_ylabel("Cumulative TOF, days")
        axes[1].set_title("The same paths in physical time-of-flight space"); axes[1].legend(fontsize=8)
        fig.suptitle("D2-05 — Streamline theory: different paths sample transport at different $t_D=t/\tau_{end}$")
        immutable_write(out / "POSTV16_D2_Representative_Streamline_CO2_Saturation_Profiles.csv", csv_bytes(profile_rows))
        rendered += save_figure(fig, out, "D2_05_Representative_Streamline_CO2_Saturation_Profiles")

        stage = "D2_06_cumulative_coverage_figure"
        fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)
        map_days = [100.0, 250.0, 500.0, 1000.0]
        for ax, day in zip(axes.ravel()[:4], map_days):
            ax.imshow(checkpoint_masks[day][LAYER8_K], origin="lower", extent=[0, 1000, 0, 1000], vmin=0, vmax=1, aspect="equal")
            ax.set_title(f"Cumulative sampled path support through {day:.0f} d")
            ax.set_xlabel("X, ft"); ax.set_ylabel("Y, ft")
        axes[1, 1].plot([r["day"] for r in coverage_rows], [100 * r["epoch_supported_fraction"] for r in coverage_rows], marker="o", label="Single checkpoint")
        axes[1, 1].plot([r["day"] for r in coverage_rows], [100 * r["cumulative_checkpoint_supported_fraction"] for r in coverage_rows], marker="s", label="Cumulative checkpoint union")
        axes[1, 1].set_xlabel("Time, days"); axes[1, 1].set_ylabel("3-D grid cells intersected, %"); axes[1, 1].grid(alpha=0.25); axes[1, 1].legend(fontsize=8)
        axes[1, 1].set_title("Seven-checkpoint coverage lower bound")
        axes[1, 2].axis("off")
        axes[1, 2].text(0.02, 0.98,
            "Important:\nThis is a LOWER BOUND on historical streamline support.\n"
            "V16 refreshed the flow field on a <=4.9417-day policy,\n"
            "but only seven post-refresh flow checkpoints are preserved\n"
            "in the A1 visual authority cache.\n\n"
            "If this sparse union already covers most of the grid,\n"
            "repeated streamline sweep can explain broad saturation.\n"
            "If not, capillary redistribution and unsaved intermediate\n"
            "flow epochs remain the other attribution mechanisms.",
            va="top", fontsize=10)
        fig.suptitle("D2-06 — Cumulative streamline support from frozen flow checkpoints")
        rendered += save_figure(fig, out, "D2_06_Cumulative_Flow_Checkpoint_Streamline_Coverage")

        # ------------------------------------------------------------------
        # Thermodynamic cell mass and capillary redistribution tendency.
        # ------------------------------------------------------------------
        stage = "terminal_cellwise_mass"
        cell_pv_m3 = POROSITY * (DX_FT * FT_TO_M) * (DY_FT * FT_TO_M) * (DZ_FT * FT_TO_M)
        rho_terminal = np.asarray(r2.gas_density_from_state(flow_sat[-1], flow_p[-1], p_ref_pa), dtype=np.float64)
        terminal_flow_sg = np.clip(flow_sat[-1] - S_BACKGROUND, 0.0, 0.60)
        cell_mass_kg = cell_pv_m3 * rho_terminal * terminal_flow_sg
        recomputed_stored = float(np.sum(cell_mass_kg))
        mass_tol = max(1e-6, 1e-10 * max(abs(restart_stored_mass), 1.0))
        gate("terminal_cellwise_mass_matches_restart", abs(recomputed_stored - restart_stored_mass) <= mass_tol, recomputed_stored - restart_stored_mass)

        stage = "terminal_capillary_tendency"
        dm_dt_kg_s = capillary_mass_tendency(r2, flow_sat[-1], perm, flow_p[-1], p_ref_pa)
        dm_dt_kg_day = dm_dt_kg_s * DAY_TO_S
        net_tendency = float(np.sum(dm_dt_kg_day))
        cap_tol = max(1e-8, 1e-12 * max(float(np.sum(np.abs(dm_dt_kg_day))), 1.0))
        gate("capillary_tendency_net_internal_conservation", abs(net_tendency) <= cap_tol, net_tendency)
        cap_corr = corr(dm_dt_kg_day, terminal_flow_sg)
        cap_rows = [{
            "terminal_day": 1000.0,
            "net_internal_capillary_mass_tendency_kg_day": net_tendency,
            "mean_abs_cell_capillary_mass_tendency_kg_day": float(np.mean(np.abs(dm_dt_kg_day))),
            "max_abs_cell_capillary_mass_tendency_kg_day": float(np.max(np.abs(dm_dt_kg_day))),
            "pearson_capillary_mass_tendency_vs_sg": cap_corr,
            "interpretation": "negative correlation indicates high-Sg cells tend to lose mass while low-Sg cells tend to gain mass under the instantaneous no-flow capillary operator",
        }]
        immutable_write(out / "POSTV16_D2_Terminal_Capillary_Redistribution_Tendency.csv", csv_bytes(cap_rows))

        stage = "D2_07_support_capillary_figure"
        final_cumulative = checkpoint_masks[1000.0]
        outside = ~final_cumulative
        fig, axes = plt.subplots(2, 2, figsize=(13, 10), constrained_layout=True)
        axes[0, 0].imshow(final_cumulative[LAYER8_K], origin="lower", extent=[0,1000,0,1000], vmin=0, vmax=1)
        axes[0, 0].set_title("Layer 8: cumulative checkpoint streamline support")
        im = axes[0, 1].imshow(sg_obs[-1, LAYER8_K], origin="lower", extent=[0,1000,0,1000])
        axes[0, 1].set_title("Layer 8: frozen pre-refresh $S_g$ at 1000 d"); fig.colorbar(im, ax=axes[0,1], label="$S_g$")
        im2 = axes[1, 0].imshow(dm_dt_kg_day[LAYER8_K], origin="lower", extent=[0,1000,0,1000])
        axes[1, 0].set_title("Layer 8: instantaneous capillary mass tendency"); fig.colorbar(im2, ax=axes[1,0], label="kg/day per cell")
        inside_vals = sg_obs[-1][final_cumulative]
        outside_vals = sg_obs[-1][outside]
        bins = np.linspace(float(np.min(sg_obs[-1])), float(np.max(sg_obs[-1])), 45)
        axes[1, 1].hist(inside_vals, bins=bins, alpha=0.55, density=True, label=f"Inside sparse cumulative support (n={inside_vals.size:,})")
        if outside_vals.size:
            axes[1, 1].hist(outside_vals, bins=bins, alpha=0.55, density=True, label=f"Outside sparse cumulative support (n={outside_vals.size:,})")
        axes[1, 1].set_xlabel("Pre-refresh $S_g$ at 1000 d"); axes[1, 1].set_ylabel("Density"); axes[1, 1].legend(fontsize=8)
        axes[1, 1].set_title("Saturation inside vs outside seven-checkpoint path union")
        for ax in axes.ravel()[:3]: ax.set_xlabel("X, ft"); ax.set_ylabel("Y, ft")
        fig.suptitle("D2-07 — Attribution evidence: path support, saturation, and capillary smoothing tendency")
        rendered += save_figure(fig, out, "D2_07_Path_Support_Saturation_and_Capillary_Attribution")

        # ------------------------------------------------------------------
        # D2-08: full terminal cellwise state + porosity decision inputs.
        # ------------------------------------------------------------------
        stage = "terminal_cellwise_table"
        term_epoch_mask = streamline_cell_mask(terminal_streamlines, GRID_SHAPE)  # type: ignore[arg-type]
        # K quintile labels.
        qedges = np.quantile(perm.ravel(), [0, .2, .4, .6, .8, 1.0])
        qbin = np.digitize(perm.ravel(), qedges[1:-1], right=True).reshape(GRID_SHAPE) + 1
        cell_rows: list[dict[str, Any]] = []
        for k in range(15):
            for j in range(50):
                for i in range(50):
                    radial = float(np.hypot(x[i] - 490.0, y[j] - 490.0))
                    quadrant = ("W" if x[i] < 500 else "E") + ("S" if y[j] < 500 else "N")
                    vertical = "upper_1_5" if k < 5 else ("completed_6_10" if k < 10 else "lower_11_15")
                    cell_rows.append({
                        "k": k, "j": j, "i": i, "physical_layer": k + 1,
                        "x_ft": float(x[i]), "y_ft": float(y[j]), "depth_ft": float(depth[k]),
                        "permeability_md": float(perm[k,j,i]), "K_quintile": int(qbin[k,j,i]),
                        "pre_refresh_transport_saturation_1000d": float(plume_sat[-1,k,j,i]),
                        "pre_refresh_CO2_saturation_sg_1000d": float(sg_obs[-1,k,j,i]),
                        "post_refresh_transport_saturation_1000d": float(flow_sat[-1,k,j,i]),
                        "post_refresh_CO2_saturation_sg_1000d": float(terminal_flow_sg[k,j,i]),
                        "post_refresh_pressure_psi_1000d": float(flow_p[-1,k,j,i]),
                        "post_refresh_CO2_density_kg_m3_1000d": float(rho_terminal[k,j,i]),
                        "post_refresh_cell_CO2_mass_kg_1000d": float(cell_mass_kg[k,j,i]),
                        "terminal_checkpoint_streamline_supported": bool(term_epoch_mask[k,j,i]),
                        "cumulative_seven_checkpoint_streamline_supported": bool(final_cumulative[k,j,i]),
                        "radial_distance_from_injector_ft": radial,
                        "quadrant": quadrant, "vertical_region": vertical,
                        "frozen_porosity": POROSITY,
                    })
        immutable_write(out / "POSTV16_D2_Terminal_37500_Cell_CO2_State.csv", csv_bytes(cell_rows))

        fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
        im0 = axes[0].imshow(perm[LAYER8_K], origin="lower", extent=[0,1000,0,1000])
        axes[0].set_title("Layer 8 SGSim permeability"); fig.colorbar(im0, ax=axes[0], label="mD")
        im1 = axes[1].imshow(sg_obs[-1, LAYER8_K], origin="lower", extent=[0,1000,0,1000])
        axes[1].set_title("Layer 8 pre-refresh $S_g$"); fig.colorbar(im1, ax=axes[1], label="$S_g$")
        im2 = axes[2].imshow(cell_mass_kg[LAYER8_K], origin="lower", extent=[0,1000,0,1000])
        axes[2].set_title("Layer 8 post-refresh cell CO₂ mass"); fig.colorbar(im2, ax=axes[2], label="kg/cell")
        for ax in axes: ax.set_xlabel("X, ft"); ax.set_ylabel("Y, ft")
        fig.suptitle("D2-08 — Terminal cellwise CO₂ state under frozen constant porosity φ=0.20")
        rendered += save_figure(fig, out, "D2_08_Terminal_Cellwise_CO2_State_and_Mass")

        gate("rendered_file_count_exact", len(rendered) == 16, len(rendered))
        gate("all_rendered_files_nonempty", all(int(r["bytes"]) > 0 for r in rendered))

        stage = "closeout"
        terminal_global = global_rows[-1]
        terminal_support = coverage_rows[-1]
        terminal_support_sat = support_rows[-1]
        constant_phi_nonuniform = bool(terminal_global["std"] > 1e-12 and terminal_global["max"] - terminal_global["min"] > 1e-12)
        porosity_contract = {
            "frozen_porosity": POROSITY,
            "variable_porosity_used_in_D2": False,
            "why": "D2 must first attribute the frozen V16 constant-porosity plume using streamline theory, cumulative path support, cellwise CO2 mass, and capillary redistribution.",
            "porosity_physics": [
                "cell pore volume PV=phi*Vbulk",
                "pore velocity and TOF depend on porosity through pore-volume storage along flow paths",
                "component-mass capacity per cell depends on porosity",
            ],
            "decision_rule": "Do not introduce heterogeneous porosity as a visual repair. Authorize POSTV16-D3 only if D2 closes transport attribution and a physically based porosity field is scientifically warranted for storage/TOF realism.",
            "constant_porosity_already_produces_nonuniform_saturation": constant_phi_nonuniform,
            "porosity_sensitivity_decision": "PENDING_D2_INTERPRETATION",
        }
        theory_contract = {
            "streamline_theory_chain": "K(x)->pressure->Darcy flux->Pollock streamline geometry->TOF tau->1D transport in xi/tau->E37A control-volume component-mass deposition->Cartesian no-flow capillary redistribution->grid Sg(x,t)",
            "dimensionless_streamline_time": "tD_s=t_physical/tau_end_s",
            "CO2_saturation_definition": "Sg = transport_saturation - 0.20",
            "mapback_authority": "V16E37A control-volume-aligned component-mass transfer; no global plume rescaling and no old SG7D whole-grid inventory projection",
            "capillary_authority": "pairwise internally conservative no-flow Cartesian capillary mass redistribution",
            "cumulative_coverage_limitation": "seven frozen post-refresh flow checkpoints provide a lower bound only; production flow refresh policy permits many intermediate epochs not stored in A1",
            "no_V16_mutation": True,
            "no_transport_rerun": True,
            "no_training": True,
            "no_calibration": True,
        }
        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "release_id": RELEASE_ID,
            "V16_frozen": True,
            "simulation_executed": False,
            "transport_rerun": False,
            "accepted_state_mutation": False,
            "frozen_porosity": POROSITY,
            "terminal_pre_refresh_sg_min": terminal_global["min"],
            "terminal_pre_refresh_sg_mean": terminal_global["mean"],
            "terminal_pre_refresh_sg_median": terminal_global["p50"],
            "terminal_pre_refresh_sg_max": terminal_global["max"],
            "terminal_pre_refresh_sg_std": terminal_global["std"],
            "constant_porosity_state_nonuniform": constant_phi_nonuniform,
            "terminal_checkpoint_streamline_supported_fraction": terminal_support["epoch_supported_fraction"],
            "terminal_cumulative_seven_checkpoint_supported_fraction": terminal_support["cumulative_checkpoint_supported_fraction"],
            "terminal_obs_mean_sg_inside_cumulative_support": terminal_support_sat["obs_mean_sg_inside_cumulative_support"],
            "terminal_obs_mean_sg_outside_cumulative_support": terminal_support_sat["obs_mean_sg_outside_cumulative_support"],
            "terminal_recomputed_stored_co2_mass_kg": recomputed_stored,
            "terminal_authoritative_stored_co2_mass_kg": restart_stored_mass,
            "terminal_mass_recompute_residual_kg": recomputed_stored - restart_stored_mass,
            "terminal_capillary_net_internal_tendency_kg_day": net_tendency,
            "terminal_capillary_tendency_vs_sg_correlation": cap_corr,
            "variable_porosity_sensitivity_executed": False,
            "porosity_sensitivity_decision": "PENDING_D2_INTERPRETATION",
            "terminal_cellwise_rows": len(cell_rows),
            "diagnostic_figure_families": FIGS,
            "rendered_png_pdf_files": 16,
            "next": NEXT,
        }
        closure = {
            "milestone": MILESTONE,
            "status": STATUS,
            "all_gates_passed": all(v["passed"] for v in gates.values()),
            "gate_count": len(gates),
            "individual_CO2_saturations_audited": True,
            "full_37500_cell_terminal_state_exported": True,
            "streamline_theory_built_into_postV16_plan": True,
            "seven_checkpoint_cumulative_path_support_reconstructed": True,
            "cumulative_path_support_is_lower_bound": True,
            "terminal_capillary_tendency_audited_read_only": True,
            "cellwise_component_mass_recomputed_exactly": True,
            "variable_porosity_not_used_as_visual_fix": True,
            "accepted_simulation_state_modified": False,
            "V16_release_modified": False,
            "next": NEXT,
        }
        captions = [
            {"figure_id": "D2-01", "caption": "Full-grid individual CO2 saturation quantiles through all nine frozen observations; Sg is the runtime incremental CO2 saturation S-0.20, not an arbitrary visualization threshold."},
            {"figure_id": "D2-02", "caption": "Layer-by-layer CO2 saturation statistics show how the frozen plume is distributed vertically rather than only in plan view."},
            {"figure_id": "D2-03", "caption": "Regional CO2 saturation statistics separate radial sweep around the injector from upper/completed/lower-layer storage response."},
            {"figure_id": "D2-04", "caption": "Within-time normalized Layer-8 saturation removes the rising domain-wide floor and exposes relative plume geometry at each observation time."},
            {"figure_id": "D2-05", "caption": "Representative short-, median-, and long-TOF streamlines sample different frozen CO2 saturation histories; labels include tau_end and tD=1000/tau_end to restore the core streamline-simulation interpretation."},
            {"figure_id": "D2-06", "caption": "Union of cells intersected by exact Pollock streamlines reconstructed at seven preserved post-refresh flow checkpoints. This is a lower bound on historical path coverage because intermediate production refresh epochs are not all retained in the A1 cache."},
            {"figure_id": "D2-07", "caption": "Terminal attribution comparison between sparse cumulative checkpoint path support, frozen saturation, and the instantaneous internally conservative capillary mass-redistribution tendency."},
            {"figure_id": "D2-08", "caption": "Terminal cellwise permeability, incremental CO2 saturation, and component mass under the frozen constant-porosity phi=0.20 model. The accompanying CSV contains all 37,500 cells."},
        ]
        stems = [
            "D2_01_Full_Grid_CO2_Saturation_Census",
            "D2_02_Layer_CO2_Saturation_Census",
            "D2_03_Spatial_Region_CO2_Saturation_Response",
            "D2_04_Layer8_Within_Time_Normalized_Plume_Contrast",
            "D2_05_Representative_Streamline_CO2_Saturation_Profiles",
            "D2_06_Cumulative_Flow_Checkpoint_Streamline_Coverage",
            "D2_07_Path_Support_Saturation_and_Capillary_Attribution",
            "D2_08_Terminal_Cellwise_CO2_State_and_Mass",
        ]
        figure_index = [
            {"figure_id": fid, "stem": stem, "files": f"{stem}.png;{stem}.pdf", "authority": "DERIVED_READ_ONLY_FROM_FROZEN_V16", "release_id": RELEASE_ID}
            for fid, stem in zip(FIGS, stems)
        ]
        immutable_write(out / "POSTV16_D2_Theory_Contract.json", json_bytes(theory_contract))
        immutable_write(out / "POSTV16_D2_Porosity_Decision_Contract.json", json_bytes(porosity_contract))
        immutable_write(out / "POSTV16_D2_Figure_Index.csv", csv_bytes(figure_index))
        immutable_write(out / "POSTV16_D2_Figure_Captions.csv", csv_bytes(captions))
        immutable_write(out / "PAD_Stream_POSTV16_D2_Summary.json", json_bytes(summary))
        immutable_write(out / "POSTV16_D2_Final_Gate_Matrix.csv", csv_bytes([{"gate": k, **v} for k, v in gates.items()]))
        immutable_write(out / "POSTV16_D2_Final_Closure.json", json_bytes(closure))

        manifest = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_D2_Artifact_Manifest.csv":
                manifest.append({"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size})
        immutable_write(out / "POSTV16_D2_Artifact_Manifest.csv", csv_bytes(manifest))

        print("\n" + "=" * 164)
        print("PAD-Stream POSTV16-D2: PASS")
        print("=" * 164)
        print(f"{'Status':72}: {STATUS}")
        print(f"{'Terminal pre-refresh Sg min / mean / median / max':72}: {terminal_global['min']:.6f} / {terminal_global['mean']:.6f} / {terminal_global['p50']:.6f} / {terminal_global['max']:.6f}")
        print(f"{'Terminal pre-refresh Sg standard deviation':72}: {terminal_global['std']:.6f}")
        print(f"{'Constant-porosity terminal state nonuniform':72}: {constant_phi_nonuniform}")
        print(f"{'Terminal single-checkpoint streamline support':72}: {100*terminal_support['epoch_supported_fraction']:.3f}%")
        print(f"{'Cumulative seven-checkpoint support lower bound':72}: {100*terminal_support['cumulative_checkpoint_supported_fraction']:.3f}%")
        print(f"{'Terminal mean Sg inside cumulative support':72}: {terminal_support_sat['obs_mean_sg_inside_cumulative_support']:.6f}")
        print(f"{'Terminal mean Sg outside cumulative support':72}: {terminal_support_sat['obs_mean_sg_outside_cumulative_support']:.6f}")
        print(f"{'Terminal cellwise stored-mass residual':72}: {recomputed_stored-restart_stored_mass:.12e} kg")
        print(f"{'Terminal capillary net internal tendency':72}: {net_tendency:.12e} kg/day")
        print(f"{'Terminal capillary tendency vs Sg correlation':72}: {cap_corr:.6f}")
        print(f"{'Terminal individual cell rows exported':72}: {len(cell_rows):,}")
        print(f"{'Variable porosity sensitivity executed':72}: False")
        print(f"{'Accepted simulation state modified':72}: False")
        print(f"{'V16 release modified':72}: False")
        print(f"{'Next':72}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "POSTV16_STREAMLINE_TO_GRID_CO2_SATURATION_ATTRIBUTION_AUDIT_BLOCKED",
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
        }
        p = blocked / "POSTV16_D2_Blocked_Report.json"
        p.write_bytes(json_bytes(report))
        print("\n" + "=" * 164)
        print("PAD-Stream POSTV16-D2: BLOCKED")
        print("=" * 164)
        print("Report      :", p)
        print("Failed stage:", stage)
        print("Exception   :", repr(exc))
        return 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
