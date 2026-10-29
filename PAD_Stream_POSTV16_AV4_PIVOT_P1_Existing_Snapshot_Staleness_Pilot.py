#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Line3DCollection


MILESTONE = "POSTV16-AV4-PIVOT-P1"
STATUS_PASS = (
    "AV4PIVOTP1_EXISTING_SNAPSHOT_PRESSURE_DARCY_POLLOCK_TOF_STALENESS_PILOT_PASS_"
    "DAY365_REFERENCE_DAY500_DAY750_DAY1000_DIAGNOSTICS_AND_3D_VISUALS_PUBLISHED"
)
STATUS_FAIL = (
    "AV4PIVOTP1_EXISTING_SNAPSHOT_STALENESS_PILOT_SCIENTIFIC_FAIL_"
    "NO_CADENCE_SELECTION_NO_AUTOMATIC_RERUN"
)
STATUS_BLOCKED = "AV4PIVOTP1_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "38403e514545138698e18086b54aa205d2ff7ae9"
EXPECTED_BRANCH = "postv16-av4-pivot"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
BACKGROUND = 0.20
SELECTED_DAYS = [365.0, 500.0, 750.0, 1000.0]
ALL_TARGET_DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]
REFERENCE_DAY = 365.0
VIS_STREAMLINE_STRIDE = 8
PRESSURE_LINEAR_RESIDUAL_MAX = 1.0e-8
FLOW_LOCAL_REL_MAX = 1.0e-8
FLOW_GLOBAL_REL_MAX = 1.0e-8

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

P0_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P0_Pressure_Refresh_Cadence_Diagnostic_Design_Freeze"
P0_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P0_Summary.json"
P0_DECISION = "POSTV16_AV4_PIVOT_P0_Decision_Contract.json"
P0_STATUS = (
    "AV4PIVOTP0_PARALLEL_PRESSURE_REFRESH_CADENCE_DIAGNOSTIC_DESIGN_FREEZE_PASS_"
    "EXACT_CERTIFICATION_BRANCH_UNCHANGED_NO_PHYSICAL_TIME_ADVANCE_NO_TRAINING"
)

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA256 = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

OUT_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P1_Existing_Snapshot_Staleness_Pilot"
RECOVERY_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P1_Recovery_Checkpoints"
FAIL_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P1_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P1_BLOCKED"

A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"
SG5 = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG5_BLOB = "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"
SG6 = "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py"
SG6_BLOB = "70ceda68e02894167958d753d88b4dbd694731ab"
R3R2R1 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_BLOB = "740c6da03e73906646bf0153633187e749449f31"
PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    A2E:A2E_BLOB,
    SG2:SG2_BLOB,
    SG3:SG3_BLOB,
    SG4:SG4_BLOB,
    SG5:SG5_BLOB,
    SG6:SG6_BLOB,
    R3R2R1:R3R2R1_BLOB,
    PERM:PERM_BLOB,
}


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_array(a: np.ndarray) -> str:
    a = np.ascontiguousarray(np.asarray(a))
    h = hashlib.sha256()
    h.update(str(a.dtype).encode("utf-8"))
    h.update(str(a.shape).encode("utf-8"))
    h.update(a.tobytes(order="C"))
    return h.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def relative_l2(new: np.ndarray, ref: np.ndarray) -> float:
    a = np.asarray(new, dtype=np.float64)
    b = np.asarray(ref, dtype=np.float64)
    return float(np.linalg.norm((a-b).ravel()) / max(float(np.linalg.norm(b.ravel())), 1.0e-30))


def max_abs(new: np.ndarray, ref: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(new, dtype=np.float64) - np.asarray(ref, dtype=np.float64))))


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    v = np.asarray(values, dtype=np.float64)
    w = np.asarray(weights, dtype=np.float64)
    order = np.argsort(v)
    v = v[order]
    w = w[order]
    c = np.cumsum(w)
    c = c / c[-1]
    return float(np.interp(q, c, v))


def snapshot_dir(recovery: Path, day: float) -> Path:
    return recovery / f"day_{int(round(day)):04d}"


def checkpoint_paths(recovery: Path, day: float) -> tuple[Path, Path]:
    d = snapshot_dir(recovery, day)
    return d / "Diagnostic_State.npz", d / "Diagnostic_Metadata.json"


def save_checkpoint(
    recovery: Path,
    day: float,
    runner_blob: str,
    saturation_sha: str,
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
) -> None:
    d = snapshot_dir(recovery, day)
    d.mkdir(parents=True, exist_ok=True)
    state_path, meta_path = checkpoint_paths(recovery, day)
    tmp_state = state_path.with_suffix(".npz.tmp")
    with tmp_state.open("wb") as f:
        np.savez_compressed(f, **arrays)
    tmp_state.replace(state_path)
    meta = dict(metadata)
    meta.update({
        "milestone": MILESTONE,
        "day": float(day),
        "runner_blob": runner_blob,
        "saturation_sha256": saturation_sha,
        "state_sha256": sha256_file(state_path),
    })
    tmp_meta = meta_path.with_suffix(".json.tmp")
    tmp_meta.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_meta.replace(meta_path)


def load_checkpoint(
    recovery: Path,
    day: float,
    runner_blob: str,
    saturation_sha: str,
) -> tuple[dict[str, np.ndarray], dict[str, Any]] | None:
    state_path, meta_path = checkpoint_paths(recovery, day)
    if not state_path.is_file() or not meta_path.is_file():
        return None
    meta = load_json(meta_path)
    if (
        meta.get("milestone") != MILESTONE
        or abs(float(meta.get("day", -1.0)) - float(day)) > 1.0e-12
        or meta.get("runner_blob") != runner_blob
        or meta.get("saturation_sha256") != saturation_sha
        or meta.get("state_sha256") != sha256_file(state_path)
    ):
        raise GateError(f"invalid_checkpoint_day_{day:g}")
    with np.load(state_path, allow_pickle=False) as z:
        arrays = {k: np.asarray(z[k]).copy() for k in z.files}
    return arrays, meta


def flatten_flux(qx: np.ndarray, qy: np.ndarray, qz: np.ndarray) -> np.ndarray:
    return np.concatenate([qx.ravel(), qy.ravel(), qz.ravel()])


def seed_key(point: np.ndarray) -> tuple[float, float, float]:
    p = np.asarray(point, dtype=np.float64)
    return tuple(float(v) for v in np.round(p, 8))


def matched_streamline_indices(
    ref_xyz: np.ndarray,
    cur_xyz: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    ref = {seed_key(ref_xyz[i, 0]): i for i in range(ref_xyz.shape[0])}
    cur = {seed_key(cur_xyz[i, 0]): i for i in range(cur_xyz.shape[0])}
    common = sorted(set(ref) & set(cur))
    return (
        np.asarray([ref[k] for k in common], dtype=np.int64),
        np.asarray([cur[k] for k in common], dtype=np.int64),
    )


def compute_cell_darcy(
    sg4: Any,
    qx: np.ndarray,
    qy: np.ndarray,
    qz: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    ux = np.zeros(GRID, dtype=np.float64)
    uy = np.zeros(GRID, dtype=np.float64)
    uz = np.zeros(GRID, dtype=np.float64)

    fx = np.asarray(qx, dtype=np.float64) / float(sg4.AX_M2)
    fy = np.asarray(qy, dtype=np.float64) / float(sg4.AY_M2)
    fz = np.asarray(qz, dtype=np.float64) / float(sg4.AZ_M2)

    ux[:, :, 0] = fx[:, :, 0]
    ux[:, :, -1] = fx[:, :, -1]
    ux[:, :, 1:-1] = 0.5 * (fx[:, :, :-1] + fx[:, :, 1:])

    uy[:, 0, :] = fy[:, 0, :]
    uy[:, -1, :] = fy[:, -1, :]
    uy[:, 1:-1, :] = 0.5 * (fy[:, :-1, :] + fy[:, 1:, :])

    uz[0, :, :] = fz[0, :, :]
    uz[-1, :, :] = fz[-1, :, :]
    uz[1:-1, :, :] = 0.5 * (fz[:-1, :, :] + fz[1:, :, :])

    mag = np.sqrt(ux*ux + uy*uy + uz*uz)
    return ux, uy, uz, mag


def set_3d_axes(ax, sg3: Any) -> None:
    ax.set_xlim(0.0, float(sg3.NX * sg3.DX_M))
    ax.set_ylim(0.0, float(sg3.NY * sg3.DY_M))
    ax.set_zlim(0.0, float(sg3.NZ * sg3.DZ_M))
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_zlabel("z (m)")
    ax.view_init(elev=24, azim=-58)


def save_figure(fig, path: Path) -> None:
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_quantitative(rows: list[dict[str, Any]], plot_dir: Path) -> list[str]:
    plot_dir.mkdir(parents=True, exist_ok=True)
    days = np.asarray([r["day"] for r in rows], dtype=float)
    specs = [
        ("pressure_relative_L2_vs_day.png", "pressure_relative_L2", "Pressure relative L2", "Pressure staleness vs day"),
        ("pressure_Linf_psi_vs_day.png", "pressure_Linf_psi", "Pressure Linf (psi)", "Maximum pressure change vs day"),
        ("darcy_flux_relative_L2_vs_day.png", "darcy_flux_relative_L2", "Darcy flux relative L2", "Darcy-flux staleness vs day"),
        ("tof_relative_L2_vs_day.png", "tof_relative_L2", "TOF relative L2", "TOF staleness vs day"),
        ("streamline_RMS_displacement_vs_day.png", "streamline_RMS_displacement_m", "RMS streamline displacement (m)", "Streamline geometry migration vs day"),
        ("diagnostic_refresh_runtime_vs_day.png", "total_runtime_s", "Runtime (s)", "Diagnostic refresh runtime vs day"),
    ]
    written=[]
    for filename,key,ylabel,title in specs:
        vals=np.asarray([r[key] for r in rows], dtype=float)
        fig=plt.figure(figsize=(7.2,4.6))
        ax=fig.add_subplot(111)
        ax.plot(days, vals, marker="o")
        ax.set_xlabel("Day")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(True, alpha=0.25)
        save_figure(fig, plot_dir/filename)
        written.append(filename)
    return written


def plot_3d_suite(
    states: dict[float, dict[str, np.ndarray]],
    sg3: Any,
    sg4: Any,
    plot_dir: Path,
) -> list[str]:
    plot_dir.mkdir(parents=True, exist_ok=True)
    all_p = np.concatenate([states[d]["pressure_psi"].ravel() for d in SELECTED_DAYS])
    pnorm = Normalize(vmin=float(np.min(all_p)), vmax=float(np.max(all_p)))

    all_tof_end = np.concatenate([states[d]["tau_end_s"].ravel()/86400.0 for d in SELECTED_DAYS])
    tnorm = Normalize(vmin=float(np.min(all_tof_end)), vmax=float(np.max(all_tof_end)))

    darcy = {}
    max_mag = 0.0
    for d in SELECTED_DAYS:
        ux,uy,uz,mag=compute_cell_darcy(sg4, states[d]["qx"],states[d]["qy"],states[d]["qz"])
        darcy[d]=(ux,uy,uz,mag)
        max_mag=max(max_mag,float(np.max(mag)))

    ref_xyz = states[REFERENCE_DAY]["xyz_m"]
    written=[]

    xcent=(np.arange(NX)+0.5)*float(sg3.DX_M)
    ycent=(np.arange(NY)+0.5)*float(sg3.DY_M)
    zcent=(np.arange(NZ)+0.5)*float(sg3.DZ_M)
    Z,Y,X=np.meshgrid(zcent,ycent,xcent,indexing="ij")

    for d in SELECTED_DAYS:
        tag=f"day{int(d):04d}"
        sat=states[d]["saturation"]
        p=states[d]["pressure_psi"]
        xyz=states[d]["xyz_m"]
        tau_end=states[d]["tau_end_s"]/86400.0

        # 3D plume
        mask=sat > (BACKGROUND + 1.0e-10)
        fig=plt.figure(figsize=(8,6))
        ax=fig.add_subplot(111,projection="3d")
        sc=ax.scatter(X[mask],Y[mask],Z[mask],c=sat[mask],s=5,alpha=0.45,norm=Normalize(BACKGROUND,0.80))
        fig.colorbar(sc,ax=ax,pad=0.08,label="CO2 saturation")
        ax.set_title(f"3D CO2 saturation plume — Day {int(d)}")
        set_3d_axes(ax,sg3)
        fn=f"3D_CO2_saturation_plume_{tag}.png"
        save_figure(fig,plot_dir/fn); written.append(fn)

        # 3D pressure
        fig=plt.figure(figsize=(8,6))
        ax=fig.add_subplot(111,projection="3d")
        sc=ax.scatter(X.ravel(),Y.ravel(),Z.ravel(),c=p.ravel(),s=2,alpha=0.18,norm=pnorm)
        fig.colorbar(sc,ax=ax,pad=0.08,label="Pressure (psi)")
        ax.set_title(f"3D refreshed pressure field — Day {int(d)}")
        set_3d_axes(ax,sg3)
        fn=f"3D_pressure_field_{tag}.png"
        save_figure(fig,plot_dir/fn); written.append(fn)

        # 3D Darcy
        ux,uy,uz,mag=darcy[d]
        kk=np.arange(0,NZ,2)
        jj=np.arange(0,NY,5)
        ii=np.arange(0,NX,5)
        K,J,I=np.meshgrid(kk,jj,ii,indexing="ij")
        xs=X[K,J,I]; ys=Y[K,J,I]; zs=Z[K,J,I]
        us=ux[K,J,I]; vs=uy[K,J,I]; ws=uz[K,J,I]; ms=mag[K,J,I]
        fig=plt.figure(figsize=(8,6))
        ax=fig.add_subplot(111,projection="3d")
        sc=ax.scatter(xs,ys,zs,c=ms,s=9,alpha=0.65,norm=Normalize(0.0,max_mag if max_mag>0 else 1.0))
        if max_mag > 0.0:
            arrow_scale=12.0/max_mag
            ax.quiver(xs,ys,zs,us*arrow_scale,vs*arrow_scale,ws*arrow_scale,length=1.0,normalize=False,linewidth=0.5)
        fig.colorbar(sc,ax=ax,pad=0.08,label="Darcy speed (m/s)")
        ax.set_title(f"3D Darcy-flow field — Day {int(d)}")
        set_3d_axes(ax,sg3)
        fn=f"3D_Darcy_flow_{tag}.png"
        save_figure(fig,plot_dir/fn); written.append(fn)

        # 3D Pollock
        segs=[xyz[i] for i in range(0,xyz.shape[0],VIS_STREAMLINE_STRIDE)]
        fig=plt.figure(figsize=(8,6))
        ax=fig.add_subplot(111,projection="3d")
        lc=Line3DCollection(segs,linewidths=0.55,alpha=0.55)
        ax.add_collection3d(lc)
        ax.set_title(f"3D Pollock streamlines — Day {int(d)}\nvisualization stride={VIS_STREAMLINE_STRIDE}; metrics use all matched paths")
        set_3d_axes(ax,sg3)
        fn=f"3D_Pollock_streamlines_{tag}.png"
        save_figure(fig,plot_dir/fn); written.append(fn)

        # 3D TOF-colored streamlines
        idx=np.arange(0,xyz.shape[0],VIS_STREAMLINE_STRIDE)
        segs=[xyz[i] for i in idx]
        fig=plt.figure(figsize=(8,6))
        ax=fig.add_subplot(111,projection="3d")
        lc=Line3DCollection(segs,linewidths=0.65,alpha=0.70,norm=tnorm)
        lc.set_array(tau_end[idx])
        ax.add_collection3d(lc)
        fig.colorbar(lc,ax=ax,pad=0.08,label="End TOF (days)")
        ax.set_title(f"3D TOF-colored streamlines — Day {int(d)}")
        set_3d_axes(ax,sg3)
        fn=f"3D_TOF_colored_streamlines_{tag}.png"
        save_figure(fig,plot_dir/fn); written.append(fn)

        # Frozen/reference vs refreshed overlay
        ri,ci=matched_streamline_indices(ref_xyz,xyz)
        if ri.size > 0:
            ri=ri[::VIS_STREAMLINE_STRIDE]
            ci=ci[::VIS_STREAMLINE_STRIDE]
        ref_segs=[ref_xyz[i] for i in ri]
        cur_segs=[xyz[i] for i in ci]
        fig=plt.figure(figsize=(8,6))
        ax=fig.add_subplot(111,projection="3d")
        if ref_segs:
            ax.add_collection3d(Line3DCollection(ref_segs,linewidths=0.55,alpha=0.40,linestyles="dashed"))
        if cur_segs:
            ax.add_collection3d(Line3DCollection(cur_segs,linewidths=0.65,alpha=0.65,linestyles="solid"))
        ax.set_title(
            f"Day-365 reference vs Day-{int(d)} refreshed streamlines\n"
            "dashed=Day365 reference; solid=current; matched seed locations only"
        )
        set_3d_axes(ax,sg3)
        fn=f"3D_frozen_vs_refreshed_streamline_overlay_{tag}.png"
        save_figure(fig,plot_dir/fn); written.append(fn)

    return written


def run_snapshot(
    *,
    day: float,
    saturation: np.ndarray,
    permeability_md: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
    a2e: Any,
    sg2: Any,
    sg3: Any,
    sg4: Any,
    sg5: Any,
    sg6: Any,
    r3r2r1: Any,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    t0=time.time()

    kx,ky,kz=sg2.build_directional_permeability(permeability_md)
    kfx,kfy,kfz=sg2.build_face_permeabilities(kx,ky,kz)
    tx_ref,ty_ref,tz_ref=sg3.construct_si_transmissibilities(kfx,kfy,kfz)

    t_pressure0=time.time()
    mobility=a2e.spatial_mobility(saturation,nw,no,krw_max,kro_max)
    tx,ty,tz,_=r3r2r1.build_updated_transmissibilities(
        sg3,tx_ref,ty_ref,tz_ref,mobility["lambda_total"]
    )
    A,b,producer_wi=r3r2r1.assemble_updated_pressure_system(
        sg3,permeability_md,tx,ty,tz,mobility["lambda_total"]
    )
    _,pressure_psi,pressure_res=r3r2r1.solve_updated_pressure(sg3,A,b)
    pressure_runtime=time.time()-t_pressure0
    if pressure_res >= PRESSURE_LINEAR_RESIDUAL_MAX:
        raise ScientificFail("pressure_linear_residual",{"day":day,"value":pressure_res})

    t_darcy0=time.time()
    producer_rates,producer_sink=r3r2r1.producer_rates_updated(sg3,pressure_psi,producer_wi)
    qx,qy,qz=sg4.compute_face_fluxes(pressure_psi,tx,ty,tz)
    conservation=r3r2r1.flow_conservation_metrics(sg3,sg4,qx,qy,qz,producer_sink)
    darcy_runtime=time.time()-t_darcy0
    if float(conservation["local_relative_l2_error"]) >= FLOW_LOCAL_REL_MAX:
        raise ScientificFail("Darcy_local_conservation",{"day":day,"value":conservation["local_relative_l2_error"]})
    if float(conservation["global_relative_mismatch"]) >= FLOW_GLOBAL_REL_MAX:
        raise ScientificFail("Darcy_global_conservation",{"day":day,"value":conservation["global_relative_mismatch"]})

    t_pollock0=time.time()
    vx,vy,vz=sg5.construct_face_pore_velocities(qx,qy,qz)
    faces,seeds=sg5.build_seeds(qx,qy,qz)
    streamlines=sg5.trace_streamlines(seeds,vx,vy,vz)
    sg5_validation=sg5.validate_streamlines(faces,seeds,streamlines)
    pollock_runtime=time.time()-t_pollock0

    t_tof0=time.time()
    sg6_streamlines=a2e.convert_sg5_to_sg6(streamlines)
    db=sg6.build_transport_database(sg6_streamlines)
    sg6.validate_transport(db)
    tof_runtime=time.time()-t_tof0

    arrays={
        "saturation":np.asarray(saturation,dtype=np.float64),
        "pressure_psi":np.asarray(pressure_psi,dtype=np.float64),
        "qx":np.asarray(qx,dtype=np.float64),
        "qy":np.asarray(qy,dtype=np.float64),
        "qz":np.asarray(qz,dtype=np.float64),
        "xyz_m":np.asarray(db["xyz_m"],dtype=np.float64),
        "tof_s":np.asarray(db["tau_s"],dtype=np.float64),
        "weights_m3_s":np.asarray(db["weights_m3_s"],dtype=np.float64),
        "tau_end_s":np.asarray(db["tau_end_s"],dtype=np.float64),
        "streamline_id":np.asarray(db["streamline_id"],dtype=np.int64),
    }
    meta={
        "pressure_linear_relative_residual":float(pressure_res),
        "Darcy_local_relative_l2_error":float(conservation["local_relative_l2_error"]),
        "Darcy_global_relative_mismatch":float(conservation["global_relative_mismatch"]),
        "streamline_count":int(sg5_validation["streamline_count"]),
        "producer_capture_count":int(sg5_validation["producer_capture_count"]),
        "capture_fraction":float(sg5_validation["capture_fraction"]),
        "pressure_runtime_s":float(pressure_runtime),
        "Darcy_runtime_s":float(darcy_runtime),
        "Pollock_runtime_s":float(pollock_runtime),
        "TOF_runtime_s":float(tof_runtime),
        "total_runtime_s":float(time.time()-t0),
        "producer_rates_m3_day":{k:float(v["m3_day"]) for k,v in producer_rates.items()},
    }
    return arrays,meta


def compute_staleness_rows(
    states: dict[float,dict[str,np.ndarray]],
    metadata: dict[float,dict[str,Any]],
) -> list[dict[str,Any]]:
    ref=states[REFERENCE_DAY]
    ref_flux=flatten_flux(ref["qx"],ref["qy"],ref["qz"])
    ref_xyz=ref["xyz_m"]
    ref_mean=float(np.average(ref["tau_end_s"]/86400.0,weights=ref["weights_m3_s"]))
    ref_p50=weighted_quantile(ref["tau_end_s"]/86400.0,ref["weights_m3_s"],0.50)
    ref_p90=weighted_quantile(ref["tau_end_s"]/86400.0,ref["weights_m3_s"],0.90)

    rows=[]
    for day in SELECTED_DAYS:
        cur=states[day]
        cur_flux=flatten_flux(cur["qx"],cur["qy"],cur["qz"])
        ri,ci=matched_streamline_indices(ref_xyz,cur["xyz_m"])
        if ri.size:
            displacement=np.sqrt(np.sum((cur["xyz_m"][ci]-ref_xyz[ri])**2,axis=2))
            rms=float(np.sqrt(np.mean(displacement**2)))
            mx=float(np.max(displacement))
            tof_rel=relative_l2(cur["tof_s"][ci],ref["tof_s"][ri])
        else:
            rms=float("nan"); mx=float("nan"); tof_rel=float("nan")

        cur_mean=float(np.average(cur["tau_end_s"]/86400.0,weights=cur["weights_m3_s"]))
        cur_p50=weighted_quantile(cur["tau_end_s"]/86400.0,cur["weights_m3_s"],0.50)
        cur_p90=weighted_quantile(cur["tau_end_s"]/86400.0,cur["weights_m3_s"],0.90)

        row={
            "day":float(day),
            "pressure_relative_L2":relative_l2(cur["pressure_psi"],ref["pressure_psi"]),
            "pressure_Linf_psi":max_abs(cur["pressure_psi"],ref["pressure_psi"]),
            "darcy_flux_relative_L2":relative_l2(cur_flux,ref_flux),
            "darcy_flux_Linf_m3_s":max_abs(cur_flux,ref_flux),
            "matched_streamline_count":int(ri.size),
            "seed_match_fraction":float(ri.size/max(ref_xyz.shape[0],1)),
            "streamline_RMS_displacement_m":rms,
            "streamline_max_displacement_m":mx,
            "tof_relative_L2":tof_rel,
            "weighted_mean_TOF_shift_days":float(cur_mean-ref_mean),
            "weighted_P50_TOF_shift_days":float(cur_p50-ref_p50),
            "weighted_P90_TOF_shift_days":float(cur_p90-ref_p90),
            **{k:v for k,v in metadata[day].items() if k != "producer_rates_m3_day"},
        }
        rows.append(row)
    return rows


def self_test() -> None:
    assert SELECTED_DAYS == [365.0,500.0,750.0,1000.0]
    assert REFERENCE_DAY in SELECTED_DAYS
    a=np.asarray([1.0,2.0,3.0])
    assert relative_l2(a,a)==0.0
    assert max_abs(a,a)==0.0
    print("POSTV16 AV4 PIVOT P1 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root=Path(project_root).resolve()
    drive=Path(drive_root).resolve()
    out=drive/OUT_REL
    recovery=drive/RECOVERY_REL
    fail_dir=drive/FAIL_REL
    block_dir=drive/BLOCK_REL
    stage="preflight"
    scientific_started=False

    def gate(name: str, passed: Any, value: Any=None):
        ok=bool(passed)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("="*190)
    print("POSTV16-AV4-PIVOT-P1 -- EXISTING-SNAPSHOT PRESSURE/DARCY/POLLOCK/TOF STALENESS PILOT")
    print("="*190)
    print("REFERENCE: A6E AV3CR0003 Day-365 snapshot refreshed diagnostically with the same one-shot operator.")
    print("SNAPSHOTS: Day 365, 500, 750, 1000.")
    print("NO E2 FIVE-STAGE ASSIGNMENT. NO MAPBACK. NO SAME-TIME FIXED-POINT ITERATION.")
    print("NO REFRESHED-GEOMETRY TRANSPORT FEEDBACK. NO TRAINING. NO R3-R6-R1 RECOVERY ACCESS.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P1_Summary.json"
        fail_report=fail_dir/"POSTV16_AV4_PIVOT_P1_Scientific_Fail_Report.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P1_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P1 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_P1_FAIL",not fail_report.exists(),str(fail_report))
        gate("no_preexisting_P1_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        branch=git_text(root,"branch","--show-current")
        parent=git_text(root,"rev-parse","HEAD^")
        dirty=git_text(root,"status","--porcelain")
        runner_blob=git_text(root,"hash-object",str(root/Path(__file__).name))
        gate("repository_branch_exact",branch==EXPECTED_BRANCH,branch)
        gate("repository_parent_is_P0_commit",parent==EXPECTED_PARENT,parent)
        gate("repository_clean",dirty=="",repr(dirty))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="P0_binding"
        p0=drive/P0_REL
        gate("P0_output_present",p0.is_dir(),str(p0))
        p0s=load_json(p0/P0_SUMMARY)
        p0d=load_json(p0/P0_DECISION)
        gate("P0_status_exact",p0s.get("status")==P0_STATUS,p0s.get("status"))
        gate("P0_P1_authorized",p0d.get("AV4_PIVOT_P1_authorized") is True,p0d.get("AV4_PIVOT_P1_authorized"))
        gate("P0_exact_branch_not_invalidated",p0d.get("current_R3R6R1_execution_invalidated") is False)

        stage="A2E_operator_authority"
        a2edir=drive/A2E_REL
        gate("A2E_output_present",a2edir.is_dir(),str(a2edir))
        a2es=load_json(a2edir/A2E_SUMMARY)
        gate("A2E_refresh_operator_PASS",a2es.get("status")==A2E_STATUS,a2es.get("status"))

        stage="A6E_snapshot_authority"
        a6e_state_path=drive/A6E_REL/A6E_STATE
        gate("A6E_state_present",a6e_state_path.is_file(),str(a6e_state_path))
        gate("A6E_state_SHA_exact",sha256_file(a6e_state_path)==A6E_STATE_SHA256,sha256_file(a6e_state_path))
        with np.load(a6e_state_path,allow_pickle=False) as z:
            state={k:np.asarray(z[k]).copy() for k in z.files}

        required={"grid_saturation","target_days","nw","no","krw_max","kro_max"}
        gate("A6E_required_arrays",required.issubset(state),sorted(required))
        target_days=np.asarray(state["target_days"],dtype=np.float64)
        grid_sat=np.asarray(state["grid_saturation"],dtype=np.float64)
        nw=np.asarray(state["nw"],dtype=np.float64)
        no=np.asarray(state["no"],dtype=np.float64)
        krw=np.asarray(state["krw_max"],dtype=np.float64)
        kro=np.asarray(state["kro_max"],dtype=np.float64)
        gate("A6E_target_days_exact",np.array_equal(target_days,np.asarray(ALL_TARGET_DAYS,dtype=np.float64)),target_days.tolist())
        gate("A6E_saturation_shape",grid_sat.shape==(len(ALL_TARGET_DAYS),)+GRID,grid_sat.shape)
        gate("A6E_constitutive_shapes",all(x.shape==GRID for x in [nw,no,krw,kro]))

        stage="load_frozen_physics"
        a2e=load_module(root/A2E,"av4_pivot_p1_a2e")
        sg2=load_module(root/SG2,"av4_pivot_p1_sg2")
        sg3=load_module(root/SG3,"av4_pivot_p1_sg3")
        sg4=load_module(root/SG4,"av4_pivot_p1_sg4")
        sg5=load_module(root/SG5,"av4_pivot_p1_sg5")
        sg6=load_module(root/SG6,"av4_pivot_p1_sg6")
        r3r2r1=load_module(root/R3R2R1,"av4_pivot_p1_r3r2r1")

        perm=np.loadtxt(root/PERM,skiprows=1,dtype=np.float64).reshape(GRID,order="C")
        gate("permeability_shape",perm.shape==GRID,perm.shape)

        scientific_started=True
        recovery.mkdir(parents=True,exist_ok=True)
        states: dict[float,dict[str,np.ndarray]]={}
        metas: dict[float,dict[str,Any]]={}

        for day in SELECTED_DAYS:
            idx=int(np.where(np.isclose(target_days,day,rtol=0.0,atol=1.0e-12))[0][0])
            sat=np.asarray(grid_sat[idx],dtype=np.float64)
            sat_sha=sha256_array(sat)
            cached=load_checkpoint(recovery,day,runner_blob,sat_sha)
            if cached is not None:
                arrays,meta=cached
                print(f"[PASS] reused durable P1 snapshot checkpoint -- Day {day:g}")
            else:
                stage=f"snapshot_day_{int(day)}"
                print()
                print("="*190)
                print(f"P1 DIAGNOSTIC SNAPSHOT -- DAY {day:g}")
                print("="*190)
                arrays,meta=run_snapshot(
                    day=day,
                    saturation=sat,
                    permeability_md=perm,
                    nw=nw,no=no,krw_max=krw,kro_max=kro,
                    a2e=a2e,sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,r3r2r1=r3r2r1,
                )
                save_checkpoint(recovery,day,runner_blob,sat_sha,arrays,meta)
                print(f"[PASS] durable P1 snapshot checkpoint published -- Day {day:g}")
            states[day]=arrays
            metas[day]=meta

        stage="staleness_metrics"
        rows=compute_staleness_rows(states,metas)
        gate("Day365_reference_zero_pressure",abs(rows[0]["pressure_relative_L2"])<=1.0e-15,rows[0]["pressure_relative_L2"])
        gate("Day365_reference_zero_Darcy",abs(rows[0]["darcy_flux_relative_L2"])<=1.0e-15,rows[0]["darcy_flux_relative_L2"])
        gate("all_rows_finite_core_metrics",all(
            np.isfinite(r["pressure_relative_L2"])
            and np.isfinite(r["darcy_flux_relative_L2"])
            and np.isfinite(r["total_runtime_s"])
            for r in rows
        ))

        stage="plotting"
        local_stage=Path("/content")/"PAD_Stream_AV4_PIVOT_P1_Final_Artifacts"
        if local_stage.exists():
            shutil.rmtree(local_stage)
        local_stage.mkdir(parents=True)
        plot_dir=local_stage/"plots"
        quantitative=plot_quantitative(rows,plot_dir)
        three_d=plot_3d_suite(states,sg3,sg4,plot_dir)

        # Publish raw diagnostic arrays for downstream P2/P4 reuse.
        snapshot_files=[]
        for day in SELECTED_DAYS:
            fn=f"POSTV16_AV4_PIVOT_P1_Day_{int(day):04d}_Diagnostic_State.npz"
            p=local_stage/fn
            with p.open("wb") as f:
                np.savez_compressed(f,**states[day])
            snapshot_files.append(fn)

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "reference_day":REFERENCE_DAY,
            "selected_days":SELECTED_DAYS,
            "scientific_execution":True,
            "diagnostic_only":True,
            "five_stage_E2_assignment_executed":False,
            "mapback_executed":False,
            "same_time_fixed_point_iteration_executed":False,
            "refreshed_geometry_transport_feedback_executed":False,
            "R3R6R1_recovery_accessed":False,
            "P1_3D_visuals_published":True,
            "quantitative_plot_count":len(quantitative),
            "threeD_plot_count":len(three_d),
            "snapshot_checkpoint_count":len(SELECTED_DAYS),
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "scientific_interpretation":(
                "P1 measures flow-field staleness by applying the same frozen spatial-mobility/"
                "pressure/Darcy/Pollock/TOF diagnostic operator independently to the A6E integrated "
                "snapshot family. It does not claim conservative refreshed-geometry continuation "
                "and does not replace or invalidate the exact R3-R6-R1 certification branch."
            ),
            "AV4_PIVOT_P2_authorized":True,
            "P2_name":"Dense Day365-to-Day500 Frozen-Flow Snapshot Generation for 5-day/50-day Cadence Study",
            "periodic_cadence_selected_now":False,
            "candidate_cadences_days":[50.0,5.0],
            "R3R6R1_execution_invalidated":False,
            "O3R7_authorized":False,
            "F5_dataset_generation_authorized":False,
            "training_authorized":False,
        }
        plot_manifest={
            "quantitative":quantitative,
            "threeD":three_d,
            "matched_view":{
                "camera_elevation_deg":24,
                "camera_azimuth_deg":-58,
                "same_domain_bounds":True,
                "pressure_global_normalization":True,
                "TOF_global_normalization":True,
                "Darcy_global_normalization":True,
                "saturation_normalization":[BACKGROUND,0.80],
            },
            "visualization_streamline_stride":VIS_STREAMLINE_STRIDE,
            "metrics_use_full_matched_streamline_population":True,
        }

        (local_stage/"PAD_Stream_POSTV16_AV4_PIVOT_P1_Summary.json").write_bytes(json_bytes(summary))
        (local_stage/"POSTV16_AV4_PIVOT_P1_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local_stage/"POSTV16_AV4_PIVOT_P1_Staleness_Metrics.csv").write_bytes(csv_bytes(rows))
        (local_stage/"POSTV16_AV4_PIVOT_P1_Plot_Manifest.json").write_bytes(json_bytes(plot_manifest))

        # Copy plot directory into local stage already present. Build final manifest over every file.
        manifest=[]
        for p in sorted(local_stage.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local_stage)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local_stage/"POSTV16_AV4_PIVOT_P1_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        stage="immutable_publish"
        if out.exists():
            raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local_stage,out)

        print()
        print("="*190)
        print("POSTV16-AV4-PIVOT-P1: PASS")
        print("Existing-snapshot staleness pilot complete.")
        print("Published quantitative plots :",len(quantitative))
        print("Published 3D plots           :",len(three_d))
        print("P2 dense Day365-to-Day500 snapshot generation authorized.")
        print("No periodic cadence selected yet.")
        print("="*190)
        return 0

    except ScientificFail as exc:
        fail_dir.mkdir(parents=True,exist_ok=True)
        p=fail_dir/"POSTV16_AV4_PIVOT_P1_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_FAIL,
                "failed_stage":stage,
                "failed_gate":exc.gate,
                "detail":exc.detail,
                "scientific_execution_started":scientific_started,
                "R3R6R1_execution_invalidated":False,
                "automatic_rerun_authorized":False,
            },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(MILESTONE+": SCIENTIFIC FAIL")
        print("Gate:",exc.gate)
        print("Detail:",exc.detail)
        return 3

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P1_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "scientific_execution_started":scientific_started,
                "recovery_checkpoints_preserved":True,
                "R3R6R1_execution_invalidated":False,
                "automatic_rerun_authorized":False,
            },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(MILESTONE+": BLOCKED")
        print("Stage:",stage)
        print("Exception:",repr(exc))
        return 2


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()


if __name__=="__main__":
    args=parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))
