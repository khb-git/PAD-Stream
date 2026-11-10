#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
from PIL import Image, ImageDraw, ImageFont

M = "POSTV16-AV4-PIVOT-P3-R1-VIS-A3"
NAME = "Industry-Style Certified Reservoir Post-Processing: Geocellular Plume / Maps / Sections / Weighted Pollock-TOF"
PASS = "AV4PIVOTP3R1VISA3_INDUSTRY_STYLE_RESERVOIR_POSTPROCESSING_PASS_NO_PHYSICS_MUTATION"
BLOCK = "AV4PIVOTP3R1VISA3_TECHNICAL_OR_AUTHORITY_BLOCK_NO_PHYSICS_MUTATION"

BRANCH = "postv16-av4-pivot"
PARENT = "990afd2256523218166d27a6e9b269f837b23b59"  # VIS-A2
RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

VIS_A1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_VIS_A1_Certified_Day365_to_Day405_ReadOnly_3D_Visualization.py"
VIS_A1_RUNNER_BLOB = "40d79b83b8d9d0d1e7d9dd42c3a17b32f49e5173"
VIS_A2_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_VIS_A2_Certified_Visualization_Review_and_Animation.py"
VIS_A2_RUNNER_BLOB = "b6a3f0702f4369f9ed1e2d04edb1353eee6694cd"

VIS_A1_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_VIS_A1"
VIS_A1_REL = BASE_AV4 / (VIS_A1_TOKEN + "_Certified_Day365_to_Day405_ReadOnly_3D_Visualization")
VIS_A1_SUMMARY = f"PAD_Stream_{VIS_A1_TOKEN}_Summary.json"
VIS_A1_MANIFEST = f"{VIS_A1_TOKEN}_Artifact_Manifest.csv"
VIS_A1_STATUS = "AV4PIVOTP3R1VISA1_CERTIFIED_DAY365_TO_DAY405_READ_ONLY_3D_VISUALIZATION_PASS_NO_PHYSICS_MUTATION"

VIS_A2_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_VIS_A2"
VIS_A2_REL = BASE_AV4 / (VIS_A2_TOKEN + "_Certified_VIS_A1_Review_and_Time_Animation")
VIS_A2_SUMMARY = f"PAD_Stream_{VIS_A2_TOKEN}_Summary.json"
VIS_A2_MANIFEST = f"{VIS_A2_TOKEN}_Artifact_Manifest.csv"
VIS_A2_STATUS = "AV4PIVOTP3R1VISA2_CERTIFIED_VIS_A1_REVIEW_AND_TIME_ANIMATION_PASS_NO_PHYSICS_MUTATION"

DAYS = [365, 370, 375, 380, 385, 390, 395, 400, 405]
GRID = (15, 50, 50)
NZ, NY, NX = GRID
DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0
LX_FT = NX * DX_FT
LY_FT = NY * DY_FT
LZ_FT = NZ * DZ_FT
FT_TO_M = 0.3048
DAY_TO_S = 86400.0
BACKGROUND = 0.20
MAX_SAT = 0.80
VERTICAL_EXAGGERATION = 5.0

INJECTOR_I = 24
INJECTOR_J = 24
PRODUCERS = {
    "PROD_SW": (4, 4),
    "PROD_SE": (45, 4),
    "PROD_NW": (4, 45),
    "PROD_NE": (45, 45),
}
COMPLETION_K = list(range(5, 10))
MID_COMPLETION_K = 7  # zero-based k=7 -> physical layer 8, z center = 30 ft

# Property filters are visualization choices, not physics thresholds or regulatory criteria.
SG_DISPLAY_FILTER = 0.25
SG_OVERLAY_FILTER = 0.35
SG_METRIC_THRESHOLDS = (0.25, 0.30, 0.40, 0.50, 0.60)
STREAMLINE_MAX_STANDALONE = 180
STREAMLINE_MAX_OVERLAY = 100

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_VIS_A3"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_Industry_Style_Reservoir_PostProcessing")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
METRICS = f"{OUT_TOKEN}_Industry_Metrics.csv"
INDEX = f"{OUT_TOKEN}_Visualization_Index.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

CONTACT_TILE = (720, 576)
CONTACT_MARGIN = 18
GIF_FRAME = (960, 768)
GIF_DURATION_MS = 900


class GateError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def verify_manifest(directory: Path, filename: str) -> dict[str, str]:
    p = directory / filename
    if not p.is_file():
        raise GateError(f"manifest_missing:{p}")
    rows = csv_rows(p)
    if not rows:
        raise GateError(f"manifest_empty:{p}")
    result: dict[str, str] = {}
    for row in rows:
        fp = directory / row["file"]
        if not fp.is_file():
            raise GateError(f"manifest_artifact_missing:{fp.name}")
        actual = sha256(fp)
        if actual != row["sha256"]:
            raise GateError(f"manifest_sha:{fp.name}:{actual}:{row['sha256']}")
        if fp.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{fp.name}")
        result[fp.name] = actual
    return result


def load_module_exact(root: Path, filename: str, blob: str, module_name: str):
    p = root / filename
    if not p.is_file():
        raise GateError(f"source_runner_missing:{p}")
    actual_blob = gt(root, "hash-object", str(p))
    if actual_blob != blob:
        raise GateError(f"source_runner_blob:{filename}:{actual_blob}:{blob}")
    spec = importlib.util.spec_from_file_location(module_name, p)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_import:{filename}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def centers_and_edges() -> tuple[np.ndarray, ...]:
    xc = (np.arange(NX, dtype=np.float64) + 0.5) * DX_FT
    yc = (np.arange(NY, dtype=np.float64) + 0.5) * DY_FT
    zc = (np.arange(NZ, dtype=np.float64) + 0.5) * DZ_FT
    xe = np.arange(NX + 1, dtype=np.float64) * DX_FT
    ye = np.arange(NY + 1, dtype=np.float64) * DY_FT
    ze = np.arange(NZ + 1, dtype=np.float64) * DZ_FT
    return xc, yc, zc, xe, ye, ze


def add_map_wells(ax) -> None:
    xi = (INJECTOR_I + 0.5) * DX_FT
    yi = (INJECTOR_J + 0.5) * DY_FT
    ax.scatter([xi], [yi], marker="*", s=120, c="black", label="Injector", zorder=20)
    first = True
    for i, j in PRODUCERS.values():
        x = (i + 0.5) * DX_FT
        y = (j + 0.5) * DY_FT
        ax.scatter([x], [y], marker="s", s=45, facecolors="white", edgecolors="black",
                   linewidths=1.2, label="Producers" if first else None, zorder=20)
        first = False


def add_3d_wells(ax, labels: bool = False) -> None:
    z0 = (min(COMPLETION_K) + 0.5) * DZ_FT
    z1 = (max(COMPLETION_K) + 0.5) * DZ_FT
    xi = (INJECTOR_I + 0.5) * DX_FT
    yi = (INJECTOR_J + 0.5) * DY_FT
    ax.plot([xi, xi], [yi, yi], [z0, z1], linewidth=3.0, color="black",
            label="Injector" if labels else None)
    first = True
    for i, j in PRODUCERS.values():
        x = (i + 0.5) * DX_FT
        y = (j + 0.5) * DY_FT
        ax.plot([x, x], [y, y], [z0, z1], linewidth=2.0, color="dimgray",
                label="Producers" if labels and first else None)
        first = False


def format_3d(ax, title: str) -> None:
    ax.set_title(title, fontsize=11, pad=12)
    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Y (ft)")
    ax.set_zlabel("Z (ft)")
    ax.set_xlim(0, LX_FT)
    ax.set_ylim(0, LY_FT)
    ax.set_zlim(0, LZ_FT)
    ax.view_init(elev=24, azim=-58)
    ax.set_box_aspect((1.0, 1.0, (LZ_FT / LX_FT) * VERTICAL_EXAGGERATION))


def augment_flow_metadata(rec: dict[str, Any]) -> None:
    p = Path(rec["diag_file"])
    with np.load(p, allow_pickle=False) as z:
        if "streamline_weight_m3_s" not in z.files:
            raise GateError(f"Day{rec['day']}_streamline_weight_missing")
        rec["weights_m3_s"] = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
        if "producer_labels" in z.files:
            rec["producer_labels"] = np.asarray(z["producer_labels"]).astype("U64")
        else:
            rec["producer_labels"] = np.asarray([""] * rec["weights_m3_s"].size, dtype="U64")
    n = rec["xyz_m"].shape[0]
    if rec["weights_m3_s"].shape != (n,):
        raise GateError(f"Day{rec['day']}_weight_shape:{rec['weights_m3_s'].shape}:{n}")
    if rec["producer_labels"].shape != (n,):
        raise GateError(f"Day{rec['day']}_producer_label_shape:{rec['producer_labels'].shape}:{n}")
    if not np.all(np.isfinite(rec["weights_m3_s"])) or float(np.min(rec["weights_m3_s"])) < 0.0:
        raise GateError(f"Day{rec['day']}_invalid_streamline_weights")


def select_streamlines(rec: dict[str, Any], maximum: int) -> np.ndarray:
    weights = np.asarray(rec["weights_m3_s"], dtype=np.float64)
    labels = np.asarray(rec["producer_labels"]).astype("U64")
    n = weights.size
    if n <= maximum:
        return np.arange(n, dtype=np.int64)
    unique = sorted([x for x in set(labels.tolist()) if x])
    selected: list[int] = []
    if unique:
        quota = max(1, maximum // len(unique))
        for lab in unique:
            ids = np.where(labels == lab)[0]
            order = ids[np.argsort(weights[ids])[::-1]]
            selected.extend(int(x) for x in order[:quota])
    selected_set = set(selected)
    if len(selected) < maximum:
        order = np.argsort(weights)[::-1]
        for idx in order.tolist():
            if idx not in selected_set:
                selected.append(int(idx))
                selected_set.add(int(idx))
                if len(selected) >= maximum:
                    break
    return np.asarray(selected[:maximum], dtype=np.int64)


def plot_geocellular_saturation(rec: dict[str, Any], out: Path) -> Path:
    sat = np.asarray(rec["saturation"], dtype=np.float64)
    day = int(rec["day"])
    filled_kji = sat >= SG_DISPLAY_FILTER
    filled = filled_kji.transpose(2, 1, 0)  # x,y,z for matplotlib voxels
    sat_xyz = sat.transpose(2, 1, 0)
    _, _, _, xe, ye, ze = centers_and_edges()
    X, Y, Z = np.meshgrid(xe, ye, ze, indexing="ij")
    norm = colors.Normalize(vmin=BACKGROUND, vmax=MAX_SAT)
    cmap = plt.get_cmap("turbo")
    facecolors = cmap(norm(sat_xyz))
    alpha = 0.18 + 0.72 * np.clip((sat_xyz - SG_DISPLAY_FILTER) / max(MAX_SAT - SG_DISPLAY_FILTER, 1e-12), 0.0, 1.0)
    facecolors[..., 3] = np.where(filled, alpha, 0.0)

    fig = plt.figure(figsize=(10.5, 8.2))
    ax = fig.add_subplot(111, projection="3d")
    ax.voxels(X, Y, Z, filled, facecolors=facecolors, edgecolor=(0, 0, 0, 0.06), linewidth=0.10, shade=False)
    add_3d_wells(ax, labels=True)
    format_3d(ax, f"Day {day}: filtered geocellular CO₂ saturation (Sg ≥ {SG_DISPLAY_FILTER:.2f}) — 5× vertical exaggeration")
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, pad=0.08, shrink=0.72)
    cb.set_label("Gas saturation")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    p = out / f"Day{day:04d}_Saturation_Geocellular_3D.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


def plot_saturation_footprint(rec: dict[str, Any], out: Path) -> Path:
    sat = np.asarray(rec["saturation"], dtype=np.float64)
    day = int(rec["day"])
    footprint = np.max(sat, axis=0)
    xc, yc, _, xe, ye, _ = centers_and_edges()
    fig, ax = plt.subplots(figsize=(8.4, 7.2))
    pc = ax.pcolormesh(xe, ye, footprint, cmap="turbo", vmin=BACKGROUND, vmax=MAX_SAT, shading="flat")
    if float(np.min(footprint)) <= SG_DISPLAY_FILTER <= float(np.max(footprint)):
        ax.contour(xc, yc, footprint, levels=[SG_DISPLAY_FILTER], colors="black", linewidths=1.0)
    add_map_wells(ax)
    ax.set_aspect("equal")
    ax.set_xlim(0, LX_FT); ax.set_ylim(0, LY_FT)
    ax.set_xlabel("X (ft)"); ax.set_ylabel("Y (ft)")
    ax.set_title(f"Day {day}: maximum gas saturation through column\nblack contour: Sg = {SG_DISPLAY_FILTER:.2f} visualization boundary")
    cb = fig.colorbar(pc, ax=ax, pad=0.02)
    cb.set_label("Maximum gas saturation")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    p = out / f"Day{day:04d}_Saturation_Footprint_Map.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


def plot_saturation_section(rec: dict[str, Any], out: Path, orientation: str) -> Path:
    sat = np.asarray(rec["saturation"], dtype=np.float64)
    day = int(rec["day"])
    xc, yc, _, xe, ye, ze = centers_and_edges()
    if orientation == "XZ":
        data = sat[:, INJECTOR_J, :]
        he = xe; hc = xc; hlabel = "X (ft)"
        plane = f"Y = {(INJECTOR_J + 0.5) * DY_FT:.0f} ft"
    elif orientation == "YZ":
        data = sat[:, :, INJECTOR_I]
        he = ye; hc = yc; hlabel = "Y (ft)"
        plane = f"X = {(INJECTOR_I + 0.5) * DX_FT:.0f} ft"
    else:
        raise ValueError(orientation)
    fig, ax = plt.subplots(figsize=(10.0, 4.6))
    pc = ax.pcolormesh(he, ze, data, cmap="turbo", vmin=BACKGROUND, vmax=MAX_SAT, shading="flat")
    if float(np.min(data)) <= SG_DISPLAY_FILTER <= float(np.max(data)):
        zc = (np.arange(NZ) + 0.5) * DZ_FT
        ax.contour(hc, zc, data, levels=[SG_DISPLAY_FILTER], colors="black", linewidths=0.9)
    inj_h = (INJECTOR_I + 0.5) * DX_FT if orientation == "XZ" else (INJECTOR_J + 0.5) * DY_FT
    z0 = (min(COMPLETION_K) + 0.5) * DZ_FT
    z1 = (max(COMPLETION_K) + 0.5) * DZ_FT
    ax.plot([inj_h, inj_h], [z0, z1], color="black", linewidth=3.0, label="Injector completion")
    ax.set_xlim(0, LX_FT if orientation == "XZ" else LY_FT); ax.set_ylim(0, LZ_FT)
    ax.set_xlabel(hlabel); ax.set_ylabel("Z (ft)")
    ax.set_title(f"Day {day}: gas-saturation {orientation} section through injector ({plane})")
    cb = fig.colorbar(pc, ax=ax, pad=0.02)
    cb.set_label("Gas saturation")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    p = out / f"Day{day:04d}_Saturation_{orientation}_Section.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


def plot_pressure_layer(rec: dict[str, Any], out: Path, pmin: float, pmax: float) -> Path:
    p3d = np.asarray(rec["pressure"], dtype=np.float64)
    day = int(rec["day"])
    data = p3d[MID_COMPLETION_K]
    xc, yc, _, xe, ye, _ = centers_and_edges()
    fig, ax = plt.subplots(figsize=(8.4, 7.2))
    pc = ax.pcolormesh(xe, ye, data, cmap="viridis", vmin=pmin, vmax=pmax, shading="flat")
    levels = np.linspace(pmin, pmax, 9)[1:-1]
    if levels.size:
        cs = ax.contour(xc, yc, data, levels=levels, colors="black", linewidths=0.35, alpha=0.45)
        ax.clabel(cs, inline=True, fontsize=6, fmt="%.0f")
    add_map_wells(ax)
    ax.set_aspect("equal")
    ax.set_xlim(0, LX_FT); ax.set_ylim(0, LY_FT)
    ax.set_xlabel("X (ft)"); ax.set_ylabel("Y (ft)")
    zft = (MID_COMPLETION_K + 0.5) * DZ_FT
    ax.set_title(f"Day {day}: exact pressure map — physical layer {MID_COMPLETION_K + 1} (z = {zft:.0f} ft)")
    cb = fig.colorbar(pc, ax=ax, pad=0.02)
    cb.set_label("Pressure (psi)")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    path = out / f"Day{day:04d}_Pressure_Layer_Map.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_deltap_layer(rec: dict[str, Any], p365: np.ndarray, out: Path, dpmax: float) -> Path:
    p3d = np.asarray(rec["pressure"], dtype=np.float64)
    day = int(rec["day"])
    data = (p3d - p365)[MID_COMPLETION_K]
    xc, yc, _, xe, ye, _ = centers_and_edges()
    norm = colors.TwoSlopeNorm(vmin=-dpmax, vcenter=0.0, vmax=dpmax)
    fig, ax = plt.subplots(figsize=(8.4, 7.2))
    pc = ax.pcolormesh(xe, ye, data, cmap="coolwarm", norm=norm, shading="flat")
    if float(np.min(data)) < 0.0 < float(np.max(data)):
        ax.contour(xc, yc, data, levels=[0.0], colors="black", linewidths=0.8)
    add_map_wells(ax)
    ax.set_aspect("equal")
    ax.set_xlim(0, LX_FT); ax.set_ylim(0, LY_FT)
    ax.set_xlabel("X (ft)"); ax.set_ylabel("Y (ft)")
    zft = (MID_COMPLETION_K + 0.5) * DZ_FT
    ax.set_title(f"Day {day}: pressure change from Day365 — physical layer {MID_COMPLETION_K + 1} (z = {zft:.0f} ft)")
    cb = fig.colorbar(pc, ax=ax, pad=0.02)
    cb.set_label("ΔP = P(day) − P(Day365) (psi)")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    path = out / f"Day{day:04d}_DeltaP_Layer_Map.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_pressure_section_day405(rec: dict[str, Any], out: Path, pmin: float, pmax: float, orientation: str) -> Path:
    p3d = np.asarray(rec["pressure"], dtype=np.float64)
    xc, yc, _, xe, ye, ze = centers_and_edges()
    if orientation == "XZ":
        data = p3d[:, INJECTOR_J, :]
        he = xe; hc = xc; hlabel = "X (ft)"; extent = LX_FT
        plane = f"Y = {(INJECTOR_J + 0.5) * DY_FT:.0f} ft"
    elif orientation == "YZ":
        data = p3d[:, :, INJECTOR_I]
        he = ye; hc = yc; hlabel = "Y (ft)"; extent = LY_FT
        plane = f"X = {(INJECTOR_I + 0.5) * DX_FT:.0f} ft"
    else:
        raise ValueError(orientation)
    zc = (np.arange(NZ) + 0.5) * DZ_FT
    fig, ax = plt.subplots(figsize=(10.0, 4.6))
    pc = ax.pcolormesh(he, ze, data, cmap="viridis", vmin=pmin, vmax=pmax, shading="flat")
    levels = np.linspace(pmin, pmax, 9)[1:-1]
    cs = ax.contour(hc, zc, data, levels=levels, colors="black", linewidths=0.35, alpha=0.5)
    ax.clabel(cs, inline=True, fontsize=6, fmt="%.0f")
    inj_h = (INJECTOR_I + 0.5) * DX_FT if orientation == "XZ" else (INJECTOR_J + 0.5) * DY_FT
    z0 = (min(COMPLETION_K) + 0.5) * DZ_FT
    z1 = (max(COMPLETION_K) + 0.5) * DZ_FT
    ax.plot([inj_h, inj_h], [z0, z1], color="black", linewidth=3.0, label="Injector completion")
    ax.set_xlim(0, extent); ax.set_ylim(0, LZ_FT)
    ax.set_xlabel(hlabel); ax.set_ylabel("Z (ft)")
    ax.set_title(f"Day 405: exact pressure {orientation} section through injector ({plane})")
    cb = fig.colorbar(pc, ax=ax, pad=0.02)
    cb.set_label("Pressure (psi)")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    path = out / f"Day0405_Pressure_{orientation}_Section.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_pollock_weighted(rec: dict[str, Any], out: Path, tof_norm: colors.Normalize) -> Path:
    day = int(rec["day"])
    selected = select_streamlines(rec, STREAMLINE_MAX_STANDALONE)
    xyz_ft = np.asarray(rec["xyz_m"], dtype=np.float64) / FT_TO_M
    tau_days = np.asarray(rec["tau_end_s"], dtype=np.float64) / DAY_TO_S
    weights = np.asarray(rec["weights_m3_s"], dtype=np.float64)
    wmax = max(float(np.max(weights[selected])), 1.0e-30)
    cmap = plt.get_cmap("plasma")

    fig = plt.figure(figsize=(10.5, 8.2))
    ax = fig.add_subplot(111, projection="3d")
    for idx in selected.tolist():
        line = xyz_ft[idx]
        lw = 0.45 + 2.25 * math.sqrt(max(float(weights[idx]), 0.0) / wmax)
        ax.plot(line[:, 0], line[:, 1], line[:, 2], color=cmap(tof_norm(max(float(tau_days[idx]), 1e-12))), linewidth=lw, alpha=0.78)
    add_3d_wells(ax, labels=True)
    format_3d(ax, f"Day {day}: representative exact Pollock network — TOF color, flow-weight line width")
    sm = plt.cm.ScalarMappable(norm=tof_norm, cmap=cmap)
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, pad=0.08, shrink=0.72)
    cb.set_label("Terminal TOF (days, log scale)")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    path = out / f"Day{day:04d}_Pollock_Weighted_TOF_3D.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_plume_streamline_overlay(rec: dict[str, Any], out: Path, tof_norm: colors.Normalize) -> Path:
    sat = np.asarray(rec["saturation"], dtype=np.float64)
    day = int(rec["day"])
    filled_kji = sat >= SG_OVERLAY_FILTER
    filled = filled_kji.transpose(2, 1, 0)
    sat_xyz = sat.transpose(2, 1, 0)
    _, _, _, xe, ye, ze = centers_and_edges()
    X, Y, Z = np.meshgrid(xe, ye, ze, indexing="ij")
    snorm = colors.Normalize(vmin=BACKGROUND, vmax=MAX_SAT)
    scmap = plt.get_cmap("turbo")
    facecolors = scmap(snorm(sat_xyz))
    alpha = 0.12 + 0.48 * np.clip((sat_xyz - SG_OVERLAY_FILTER) / max(MAX_SAT - SG_OVERLAY_FILTER, 1e-12), 0.0, 1.0)
    facecolors[..., 3] = np.where(filled, alpha, 0.0)

    selected = select_streamlines(rec, STREAMLINE_MAX_OVERLAY)
    xyz_ft = np.asarray(rec["xyz_m"], dtype=np.float64) / FT_TO_M
    tau_days = np.asarray(rec["tau_end_s"], dtype=np.float64) / DAY_TO_S
    weights = np.asarray(rec["weights_m3_s"], dtype=np.float64)
    wmax = max(float(np.max(weights[selected])), 1.0e-30)
    tcmap = plt.get_cmap("plasma")

    fig = plt.figure(figsize=(10.5, 8.2))
    ax = fig.add_subplot(111, projection="3d")
    ax.voxels(X, Y, Z, filled, facecolors=facecolors, edgecolor=(0, 0, 0, 0.04), linewidth=0.08, shade=False)
    for idx in selected.tolist():
        line = xyz_ft[idx]
        lw = 0.50 + 2.0 * math.sqrt(max(float(weights[idx]), 0.0) / wmax)
        ax.plot(line[:, 0], line[:, 1], line[:, 2], color=tcmap(tof_norm(max(float(tau_days[idx]), 1e-12))), linewidth=lw, alpha=0.90)
    add_3d_wells(ax, labels=True)
    format_3d(ax, f"Day {day}: filtered CO₂ cells (Sg ≥ {SG_OVERLAY_FILTER:.2f}) + representative exact Pollock paths")
    sm = plt.cm.ScalarMappable(norm=tof_norm, cmap=tcmap)
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, pad=0.08, shrink=0.72)
    cb.set_label("Terminal TOF (days, log scale)")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    path = out / f"Day{day:04d}_Plume_Streamline_Overlay_3D.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def centered_canvas(img: Image.Image, size: tuple[int, int], background=(255, 255, 255)) -> Image.Image:
    src = img.convert("RGB")
    src.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, background)
    x = (size[0] - src.width) // 2
    y = (size[1] - src.height) // 2
    canvas.paste(src, (x, y))
    return canvas


def label_tile(tile: Image.Image, label: str) -> Image.Image:
    out = tile.copy()
    draw = ImageDraw.Draw(out)
    font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
    draw.rectangle((5, 5, 17 + tw, 15 + th), fill=(255, 255, 255))
    draw.text((10, 9), label, fill=(0, 0, 0), font=font)
    return out


def make_contact_sheet(paths: list[Path], labels: list[str], output: Path) -> None:
    if len(paths) != 9 or len(labels) != 9:
        raise GateError("contact_sheet_requires_nine_frames")
    tw, th = CONTACT_TILE; m = CONTACT_MARGIN
    sheet = Image.new("RGB", (3 * tw + 4 * m, 3 * th + 4 * m), (242, 242, 242))
    for n, (path, label) in enumerate(zip(paths, labels)):
        with Image.open(path) as im:
            tile = centered_canvas(im, CONTACT_TILE)
        tile = label_tile(tile, label)
        row, col = divmod(n, 3)
        sheet.paste(tile, (m + col * (tw + m), m + row * (th + m)))
    sheet.save(output, format="PNG", optimize=False)


def make_gif(paths: list[Path], labels: list[str], output: Path) -> None:
    frames: list[Image.Image] = []
    for path, label in zip(paths, labels):
        with Image.open(path) as im:
            frame = centered_canvas(im, GIF_FRAME)
        frames.append(label_tile(frame, label))
    frames[0].save(output, save_all=True, append_images=frames[1:], duration=GIF_DURATION_MS,
                   loop=0, optimize=False, disposal=2)


def make_four_panel(items: list[tuple[Path, str]], output: Path) -> None:
    if len(items) != 4:
        raise GateError("four_panel_requires_four_items")
    tile_size = (900, 720); margin = 20
    canvas = Image.new("RGB", (2 * tile_size[0] + 3 * margin, 2 * tile_size[1] + 3 * margin), (242, 242, 242))
    for n, (path, label) in enumerate(items):
        with Image.open(path) as im:
            tile = centered_canvas(im, tile_size)
        tile = label_tile(tile, label)
        row, col = divmod(n, 2)
        canvas.paste(tile, (margin + col * (tile_size[0] + margin), margin + row * (tile_size[1] + margin)))
    canvas.save(output, format="PNG", optimize=False)


def observation_metrics(rec: dict[str, Any], p365: np.ndarray, displayed_count: int) -> dict[str, Any]:
    sat = np.asarray(rec["saturation"], dtype=np.float64)
    p = np.asarray(rec["pressure"], dtype=np.float64)
    dp = p - p365
    footprint = np.max(sat, axis=0)
    row: dict[str, Any] = {
        "day": int(rec["day"]),
        "pressure_min_psi": float(np.min(p)),
        "pressure_mean_psi": float(np.mean(p)),
        "pressure_max_psi": float(np.max(p)),
        "deltaP_min_psi": float(np.min(dp)),
        "deltaP_mean_psi": float(np.mean(dp)),
        "deltaP_max_psi": float(np.max(dp)),
        "streamline_count_total": int(rec["xyz_m"].shape[0]),
        "streamline_count_displayed": int(displayed_count),
        "total_streamline_weight_m3_s": float(np.sum(rec["weights_m3_s"])),
        "displayed_streamline_weight_fraction": float(np.sum(rec["weights_m3_s"][select_streamlines(rec, displayed_count)]) / max(np.sum(rec["weights_m3_s"]), 1e-30)),
        "tau_end_min_days": float(np.min(rec["tau_end_s"]) / DAY_TO_S),
        "tau_end_median_days": float(np.median(rec["tau_end_s"]) / DAY_TO_S),
        "tau_end_max_days": float(np.max(rec["tau_end_s"]) / DAY_TO_S),
    }
    cell_volume = DX_FT * DY_FT * DZ_FT
    cell_area = DX_FT * DY_FT
    for t in SG_METRIC_THRESHOLDS:
        code = f"{int(round(t * 100)):02d}"
        row[f"cells_Sg_ge_{code}"] = int(np.count_nonzero(sat >= t))
        row[f"bulk_volume_ft3_Sg_ge_{code}"] = float(np.count_nonzero(sat >= t) * cell_volume)
        row[f"footprint_cells_Sg_ge_{code}"] = int(np.count_nonzero(footprint >= t))
        row[f"footprint_area_ft2_Sg_ge_{code}"] = float(np.count_nonzero(footprint >= t) * cell_area)
    return row


def make_metrics_plots(rows: list[dict[str, Any]], out: Path) -> list[Path]:
    day = np.asarray([r["day"] for r in rows], dtype=np.float64)
    outputs: list[Path] = []

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for t in SG_METRIC_THRESHOLDS:
        code = f"{int(round(t * 100)):02d}"
        area = np.asarray([r[f"footprint_area_ft2_Sg_ge_{code}"] for r in rows], dtype=np.float64)
        ax.plot(day, area / 43560.0, marker="o", label=f"Sg ≥ {t:.2f}")
    ax.set_xlabel("Observation day"); ax.set_ylabel("Plume footprint area (acres)")
    ax.set_title("CO₂ plume footprint growth by visualization/property threshold")
    ax.grid(True, alpha=0.25); ax.legend(ncol=2)
    fig.tight_layout()
    p = out / f"{OUT_TOKEN}_Plume_Footprint_Area_Evolution.png"
    fig.savefig(p, dpi=200, bbox_inches="tight"); plt.close(fig); outputs.append(p)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(day, [r["pressure_min_psi"] for r in rows], marker="o", label="Absolute P min")
    ax.plot(day, [r["pressure_mean_psi"] for r in rows], marker="o", label="Absolute P mean")
    ax.plot(day, [r["pressure_max_psi"] for r in rows], marker="o", label="Absolute P max")
    ax.set_xlabel("Observation day"); ax.set_ylabel("Pressure (psi)")
    ax.set_title("Exact pressure evolution")
    ax.grid(True, alpha=0.25); ax.legend()
    fig.tight_layout()
    p = out / f"{OUT_TOKEN}_Pressure_Evolution.png"
    fig.savefig(p, dpi=200, bbox_inches="tight"); plt.close(fig); outputs.append(p)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(day, [r["deltaP_min_psi"] for r in rows], marker="o", label="ΔP min")
    ax.plot(day, [r["deltaP_mean_psi"] for r in rows], marker="o", label="ΔP mean")
    ax.plot(day, [r["deltaP_max_psi"] for r in rows], marker="o", label="ΔP max")
    ax.axhline(0.0, linewidth=0.8, color="black")
    ax.set_xlabel("Observation day"); ax.set_ylabel("ΔP vs Day365 (psi)")
    ax.set_title("Pressure response relative to Day365")
    ax.grid(True, alpha=0.25); ax.legend()
    fig.tight_layout()
    p = out / f"{OUT_TOKEN}_DeltaP_Evolution.png"
    fig.savefig(p, dpi=200, bbox_inches="tight"); plt.close(fig); outputs.append(p)
    return outputs


def selftest() -> None:
    assert DAYS == list(range(365, 406, 5))
    assert GRID == (15, 50, 50)
    assert PARENT == "990afd2256523218166d27a6e9b269f837b23b59"
    assert 0.20 < SG_DISPLAY_FILTER < SG_OVERLAY_FILTER < MAX_SAT
    assert MID_COMPLETION_K in COMPLETION_K
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        kk, jj, ii = np.indices(GRID)
        r2 = ((ii - 24.0) / 13.0) ** 2 + ((jj - 24.0) / 11.0) ** 2 + ((kk - 7.0) / 4.0) ** 2
        sat = BACKGROUND + 0.55 * np.exp(-r2)
        p = 2350.0 + 250.0 * np.exp(-(((ii - 24.0) / 18.0) ** 2 + ((jj - 24.0) / 18.0) ** 2)) + kk * 2.0
        nsl = 24; nn = 31
        xyz = np.zeros((nsl, nn, 3), dtype=np.float64)
        tau = np.zeros(nsl, dtype=np.float64)
        weights = np.linspace(0.2, 1.0, nsl) * 1e-4
        labels = np.asarray([list(PRODUCERS)[n % 4] for n in range(nsl)], dtype="U64")
        for s in range(nsl):
            a = 2 * np.pi * s / nsl
            rr = np.linspace(0, 430, nn)
            xyz[s, :, 0] = (490 + rr * np.cos(a)) * FT_TO_M
            xyz[s, :, 1] = (490 + rr * np.sin(a)) * FT_TO_M
            xyz[s, :, 2] = (30 + 7 * np.sin(np.linspace(0, np.pi, nn))) * FT_TO_M
            tau[s] = (100 + 30 * s) * DAY_TO_S
        rec = {"day": 405, "saturation": sat, "pressure": p, "xyz_m": xyz, "tau_end_s": tau,
               "weights_m3_s": weights, "producer_labels": labels}
        tof_norm = colors.LogNorm(vmin=float(np.min(tau / DAY_TO_S)), vmax=float(np.max(tau / DAY_TO_S)))
        a = plot_geocellular_saturation(rec, out)
        b = plot_saturation_footprint(rec, out)
        c = plot_pressure_layer(rec, out, float(np.min(p)), float(np.max(p)))
        d = plot_pollock_weighted(rec, out, tof_norm)
        for q in (a, b, c, d):
            assert q.is_file() and q.stat().st_size > 0
    print("POSTV16 AV4 PIVOT P3-R1 VIS-A3 structural/render self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    staging = drive / STAGE_REL
    blocked = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({"stage": stage, "gate": name, "pass": ok, "detail": "" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"), flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("=" * 160, flush=True)
        print("POSTV16-AV4-PIVOT-P3-R1-VIS-A3 — INDUSTRY-STYLE CERTIFIED RESERVOIR POST-PROCESSING", flush=True)
        print("GEOCELLULAR PROPERTY FILTERS + PLAN MAPS + SECTIONS + DELTA-P + WEIGHTED EXACT POLLOCK/TOF.", flush=True)
        print("READ-ONLY POST-PROCESSING ONLY. NO PRESSURE SOLVE. NO DARCY RECOMPUTATION. NO POLLOCK RETRACING. NO TRANSPORT ADVANCE.", flush=True)
        print("REGULATORY PRESSURE-FRONT/AOR THRESHOLD IS INTENTIONALLY NOT INFERRED IN THIS MILESTONE.", flush=True)
        print("=" * 160, flush=True)

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_VIS_A2_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        a1 = load_module_exact(root, VIS_A1_RUNNER, VIS_A1_RUNNER_BLOB, "pad_stream_vis_a1_authority")
        _a2 = load_module_exact(root, VIS_A2_RUNNER, VIS_A2_RUNNER_BLOB, "pad_stream_vis_a2_authority")

        stage = "VIS_A1_VIS_A2_formal_authority"
        a1dir = drive / VIS_A1_REL
        a2dir = drive / VIS_A2_REL
        gate("VIS_A1_output_exists", a1dir.is_dir(), str(a1dir))
        gate("VIS_A2_output_exists", a2dir.is_dir(), str(a2dir))
        a1_manifest = verify_manifest(a1dir, VIS_A1_MANIFEST)
        a2_manifest = verify_manifest(a2dir, VIS_A2_MANIFEST)
        a1sum = js(a1dir / VIS_A1_SUMMARY)
        a2sum = js(a2dir / VIS_A2_SUMMARY)
        gate("VIS_A1_status_exact", a1sum.get("status") == VIS_A1_STATUS, a1sum.get("status"))
        gate("VIS_A2_status_exact", a2sum.get("status") == VIS_A2_STATUS, a2sum.get("status"))
        gate("VIS_A2_source_VIS_A1_status_exact", a2sum.get("source_VIS_A1_status") == VIS_A1_STATUS, a2sum.get("source_VIS_A1_status"))
        gate("VIS_A2_no_physics_mutation", a2sum.get("authoritative_physics_state_mutated") is False)
        gate("VIS_A2_no_transport_advance", a2sum.get("Day405_to_Day410_transport_executed") is False)
        gate("VIS_A2_Day410_authority_preserved", a2sum.get("Day405_to_Day410_transport_remains_authorized") is True)
        gate("VIS_A2_P4_locked", a2sum.get("P4_authorized") is False)
        gate("Day405_state_lineage_match", a2sum.get("source_Day405_state_sha256") == a1sum.get("Day405_state_sha256"))
        gate("Day405_diagnostic_lineage_match", a2sum.get("source_Day405_diagnostic_sha256") == a1sum.get("Day405_diagnostic_sha256"))

        stage = "source_scientific_arrays"
        state405_sha, diag405_sha, r10sum = a1.bind_day405(drive)
        a1.OBS[405]["state_sha"] = state405_sha
        a1.OBS[405]["diag_sha"] = diag405_sha
        records: list[dict[str, Any]] = []
        rec365 = a1.load_day365(drive)
        a1.validate_arrays(rec365)
        augment_flow_metadata(rec365)
        records.append(rec365)
        for day in sorted(a1.OBS):
            rec = a1.load_observation(drive, day, a1.OBS[day])
            a1.validate_arrays(rec)
            augment_flow_metadata(rec)
            records.append(rec)
        gate("observation_days_exact", [int(r["day"]) for r in records] == DAYS, [r["day"] for r in records])
        gate("Day405_state_hash_exact", records[-1]["state_sha"] == a1sum.get("Day405_state_sha256"), records[-1]["state_sha"])
        gate("Day405_diagnostic_hash_exact", records[-1]["diag_sha"] == a1sum.get("Day405_diagnostic_sha256"), records[-1]["diag_sha"])

        stage = "global_fixed_scales"
        pmin = min(float(np.min(r["pressure"])) for r in records)
        pmax = max(float(np.max(r["pressure"])) for r in records)
        p365 = np.asarray(records[0]["pressure"], dtype=np.float64)
        dpmax = max(float(np.max(np.abs(np.asarray(r["pressure"]) - p365))) for r in records)
        dpmax = max(dpmax, 1.0e-6)
        tau_min = min(float(np.min(r["tau_end_s"]) / DAY_TO_S) for r in records)
        tau_max = max(float(np.max(r["tau_end_s"]) / DAY_TO_S) for r in records)
        gate("absolute_pressure_scale_finite", np.isfinite(pmin) and np.isfinite(pmax) and pmax > pmin, (pmin, pmax))
        gate("deltaP_scale_finite", np.isfinite(dpmax) and dpmax > 0.0, dpmax)
        gate("TOF_scale_positive", tau_min > 0.0 and tau_max > tau_min, (tau_min, tau_max))
        tof_norm = colors.LogNorm(vmin=tau_min, vmax=tau_max)

        stage = "output_firewall"
        gate("VIS_A3_output_does_not_preexist", not out.exists(), str(out))
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=False)

        stage = "industry_style_render"
        index_rows: list[dict[str, Any]] = []
        metric_rows: list[dict[str, Any]] = []
        sequences: dict[str, list[Path]] = {
            "Geocellular_Saturation": [],
            "Saturation_Footprint": [],
            "Saturation_XZ": [],
            "Saturation_YZ": [],
            "DeltaP_Layer": [],
            "Pollock_Weighted_TOF": [],
            "Plume_Streamline_Overlay": [],
        }
        labels = [f"Day {d}" for d in DAYS]
        day405_paths: dict[str, Path] = {}

        for rec in records:
            day = int(rec["day"])
            print(f"[VIS-A3] Day {day}: geocellular saturation", flush=True)
            p_geocell = plot_geocellular_saturation(rec, staging)
            print(f"[VIS-A3] Day {day}: saturation footprint", flush=True)
            p_foot = plot_saturation_footprint(rec, staging)
            print(f"[VIS-A3] Day {day}: XZ saturation section", flush=True)
            p_xz = plot_saturation_section(rec, staging, "XZ")
            print(f"[VIS-A3] Day {day}: YZ saturation section", flush=True)
            p_yz = plot_saturation_section(rec, staging, "YZ")
            print(f"[VIS-A3] Day {day}: pressure layer map", flush=True)
            p_p = plot_pressure_layer(rec, staging, pmin, pmax)
            print(f"[VIS-A3] Day {day}: delta-P layer map", flush=True)
            p_dp = plot_deltap_layer(rec, p365, staging, dpmax)
            print(f"[VIS-A3] Day {day}: weighted Pollock/TOF", flush=True)
            p_sl = plot_pollock_weighted(rec, staging, tof_norm)
            print(f"[VIS-A3] Day {day}: plume + weighted Pollock overlay", flush=True)
            p_ov = plot_plume_streamline_overlay(rec, staging, tof_norm)

            sequences["Geocellular_Saturation"].append(p_geocell)
            sequences["Saturation_Footprint"].append(p_foot)
            sequences["Saturation_XZ"].append(p_xz)
            sequences["Saturation_YZ"].append(p_yz)
            sequences["DeltaP_Layer"].append(p_dp)
            sequences["Pollock_Weighted_TOF"].append(p_sl)
            sequences["Plume_Streamline_Overlay"].append(p_ov)
            for typ, path in [
                ("geocellular_saturation", p_geocell), ("saturation_footprint", p_foot),
                ("saturation_xz", p_xz), ("saturation_yz", p_yz), ("pressure_layer", p_p),
                ("deltaP_layer", p_dp), ("pollock_weighted_tof", p_sl), ("plume_streamline_overlay", p_ov),
            ]:
                index_rows.append({"artifact": path.name, "type": typ, "day": day})
            metric_rows.append(observation_metrics(rec, p365, min(STREAMLINE_MAX_STANDALONE, rec["xyz_m"].shape[0])))
            if day == 405:
                day405_paths = {"geocell": p_geocell, "foot": p_foot, "xz": p_xz, "yz": p_yz,
                                "pressure": p_p, "deltaP": p_dp, "pollock": p_sl, "overlay": p_ov}

        stage = "Day405_engineering_sections_and_panels"
        rec405 = records[-1]
        p_pxz = plot_pressure_section_day405(rec405, staging, pmin, pmax, "XZ")
        p_pyz = plot_pressure_section_day405(rec405, staging, pmin, pmax, "YZ")
        index_rows.extend([
            {"artifact": p_pxz.name, "type": "pressure_xz", "day": 405},
            {"artifact": p_pyz.name, "type": "pressure_yz", "day": 405},
        ])
        sat_panel = staging / f"{OUT_TOKEN}_Day0405_Saturation_Flow_Industry_Review.png"
        make_four_panel([
            (day405_paths["geocell"], "A — filtered geocellular Sg"),
            (day405_paths["foot"], "B — Sg footprint"),
            (day405_paths["xz"], "C — injector XZ Sg section"),
            (day405_paths["pollock"], "D — weighted exact Pollock / TOF"),
        ], sat_panel)
        pressure_panel = staging / f"{OUT_TOKEN}_Day0405_Pressure_Industry_Review.png"
        make_four_panel([
            (day405_paths["pressure"], "A — absolute pressure map"),
            (day405_paths["deltaP"], "B — ΔP map vs Day365"),
            (p_pxz, "C — injector XZ pressure section"),
            (p_pyz, "D — injector YZ pressure section"),
        ], pressure_panel)
        index_rows.extend([
            {"artifact": sat_panel.name, "type": "Day405_four_panel_saturation_flow", "day": 405},
            {"artifact": pressure_panel.name, "type": "Day405_four_panel_pressure", "day": 405},
        ])

        stage = "time_comparison_products"
        contact_outputs: list[Path] = []
        for kind, seq in sequences.items():
            p = staging / f"{OUT_TOKEN}_{kind}_Day365_to_Day405_ContactSheet.png"
            make_contact_sheet(seq, labels, p)
            contact_outputs.append(p)
            index_rows.append({"artifact": p.name, "type": "contact_sheet", "day": "365-405", "source_kind": kind})
        gif_kinds = ["Saturation_Footprint", "DeltaP_Layer", "Pollock_Weighted_TOF", "Plume_Streamline_Overlay"]
        gif_outputs: list[Path] = []
        for kind in gif_kinds:
            p = staging / f"{OUT_TOKEN}_{kind}_Day365_to_Day405.gif"
            make_gif(sequences[kind], labels, p)
            gif_outputs.append(p)
            index_rows.append({"artifact": p.name, "type": "gif_animation", "day": "365-405", "source_kind": kind})

        stage = "quantitative_review"
        write_csv(staging / METRICS, metric_rows)
        metric_plots = make_metrics_plots(metric_rows, staging)
        for p in metric_plots:
            index_rows.append({"artifact": p.name, "type": "metrics_review", "day": "365-405"})
        write_csv(staging / INDEX, index_rows)

        stage = "publication"
        pngs = sorted(staging.glob("*.png"))
        gifs = sorted(staging.glob("*.gif"))
        expected_png = 9 * 8 + 2 + 2 + 7 + 3  # per-day + pressure sections + Day405 panels + contact sheets + metric plots
        expected_gif = 4
        gate("expected_VIS_A3_PNG_count", len(pngs) == expected_png, (len(pngs), expected_png))
        gate("expected_VIS_A3_GIF_count", len(gifs) == expected_gif, (len(gifs), expected_gif))
        for p in gifs:
            with Image.open(p) as im:
                gate(f"GIF_nine_frames:{p.name}", getattr(im, "n_frames", 1) == 9, getattr(im, "n_frames", 1))

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "repository_parent_VIS_A2_commit": PARENT,
            "source_VIS_A1_status": VIS_A1_STATUS,
            "source_VIS_A2_status": VIS_A2_STATUS,
            "source_VIS_A1_summary_sha256": sha256(a1dir / VIS_A1_SUMMARY),
            "source_VIS_A2_summary_sha256": sha256(a2dir / VIS_A2_SUMMARY),
            "source_VIS_A1_manifest_sha256": sha256(a1dir / VIS_A1_MANIFEST),
            "source_VIS_A2_manifest_sha256": sha256(a2dir / VIS_A2_MANIFEST),
            "source_Day405_state_sha256": a1sum.get("Day405_state_sha256"),
            "source_Day405_diagnostic_sha256": a1sum.get("Day405_diagnostic_sha256"),
            "observation_days": DAYS,
            "industry_style_rendering_contract": {
                "3D_saturation": "geocellular voxel/property-filter rendering",
                "saturation_plan_view": "maximum Sg through vertical column",
                "saturation_sections": ["injector XZ", "injector YZ"],
                "pressure_plan_view": f"physical layer {MID_COMPLETION_K + 1}",
                "pressure_change": "DeltaP relative to Day365 with fixed symmetric scale",
                "streamlines": "exact Pollock paths; representative high-flow subset; line width proportional to streamline volumetric weight; color by terminal TOF",
                "time_comparison": "fixed camera, fixed geometry, fixed color limits across Day365-Day405",
            },
            "saturation_display_filter": SG_DISPLAY_FILTER,
            "saturation_overlay_filter": SG_OVERLAY_FILTER,
            "saturation_metric_thresholds": list(SG_METRIC_THRESHOLDS),
            "pressure_map_zero_based_k": MID_COMPLETION_K,
            "pressure_map_physical_layer": MID_COMPLETION_K + 1,
            "pressure_map_z_center_ft": (MID_COMPLETION_K + 0.5) * DZ_FT,
            "global_pressure_min_psi": pmin,
            "global_pressure_max_psi": pmax,
            "global_abs_deltaP_limit_psi": dpmax,
            "global_terminal_TOF_min_days": tau_min,
            "global_terminal_TOF_max_days": tau_max,
            "standalone_streamline_display_cap": STREAMLINE_MAX_STANDALONE,
            "overlay_streamline_display_cap": STREAMLINE_MAX_OVERLAY,
            "total_VIS_A3_png_count": len(pngs),
            "total_VIS_A3_gif_count": len(gifs),
            "visualization_index": INDEX,
            "industry_metrics_table": METRICS,
            "regulatory_pressure_front_threshold_inferred": False,
            "regulatory_pressure_front_or_AoR_claim_made": False,
            "read_only_postprocessing": True,
            "pressure_solve_executed": False,
            "Darcy_recomputation_executed": False,
            "Pollock_retracing_executed": False,
            "TOF_recomputation_executed": False,
            "transport_execution_executed": False,
            "authoritative_physics_state_mutated": False,
            "authoritative_physical_time_advanced": False,
            "Day405_to_Day410_transport_executed": False,
            "Day405_to_Day410_transport_remains_authorized": True,
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
            "recommended_next_action": "Review the Day405 saturation/flow and pressure four-panel engineering figures plus the Day365-to-Day405 contact sheets/GIFs. If the industry-style presentation is scientifically clear, freeze VIS-A3 as the post-processing presentation contract and resume the already-authorized Day405-to-Day410 ninth-observation transport pilot. Define any regulatory pressure-front/AoR threshold separately before generating such a contour.",
        }
        (staging / SUMMARY).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest_rows = []
        for p in sorted(staging.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                manifest_rows.append({"file": p.name, "sha256": sha256(p), "bytes": p.stat().st_size})
        write_csv(staging / MANIFEST, manifest_rows)
        staging.rename(out)

        print("=" * 160, flush=True)
        print(M, "PASS", flush=True)
        print("Observation days                         :", DAYS, flush=True)
        print("Industry-style PNG files                 :", len(pngs), flush=True)
        print("Industry-style GIF animations            :", len(gifs), flush=True)
        print("Geocellular Sg display filter            :", SG_DISPLAY_FILTER, flush=True)
        print("Overlay Sg display filter                :", SG_OVERLAY_FILTER, flush=True)
        print("Pressure map physical layer              :", MID_COMPLETION_K + 1, flush=True)
        print("Regulatory pressure-front threshold made : False", flush=True)
        print("Authoritative physics state mutated      : False", flush=True)
        print("Day405->Day410 transport executed        : False", flush=True)
        print("Day405->Day410 transport remains allowed : True", flush=True)
        print("P4 authorized                            : False", flush=True)
        print("Output directory                         :", out, flush=True)
        print("=" * 160, flush=True)
        return 0

    except Exception as exc:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        blocked.mkdir(parents=True, exist_ok=True)
        report = blocked / f"{OUT_TOKEN}_Blocked_Report.json"
        report.write_text(json.dumps({
            "milestone": M,
            "status": BLOCK,
            "failed_stage": stage,
            "exception": repr(exc),
            "authoritative_physics_state_mutated": False,
            "authoritative_physical_time_advanced": False,
            "Day405_to_Day410_transport_executed": False,
            "P4_authorized": False,
            "gates_completed": gates,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(M, "TECHNICAL / AUTHORITY BLOCK", flush=True)
        print("Stage:", stage, flush=True)
        print("Exception:", repr(exc), flush=True)
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
