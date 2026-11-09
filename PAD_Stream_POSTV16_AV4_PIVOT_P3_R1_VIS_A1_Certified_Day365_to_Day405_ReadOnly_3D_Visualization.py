#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm, colors

M = "POSTV16-AV4-PIVOT-P3-R1-VIS-A1"
NAME = "Certified Day365-to-Day405 Read-Only 3D Pressure / Saturation / Pollock-TOF Visualization"
PASS = "AV4PIVOTP3R1VISA1_CERTIFIED_DAY365_TO_DAY405_READ_ONLY_3D_VISUALIZATION_PASS_NO_PHYSICS_MUTATION"
BLOCK = "AV4PIVOTP3R1VISA1_TECHNICAL_OR_AUTHORITY_BLOCK_NO_PHYSICS_MUTATION"

BRANCH = "postv16-av4-pivot"
PARENT = "c167ce883ff2732a3328b9444bb6f165c7bb8205"  # R7-R10
RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

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
SAT_PLOT_THRESHOLD = 0.205
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

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_VIS_A1"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_Certified_Day365_to_Day405_ReadOnly_3D_Visualization")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
AUTHORITY = f"{OUT_TOKEN}_Source_Authority.csv"
METRICS = f"{OUT_TOKEN}_Observation_Metrics.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

# Day365 reference authority.
DAY365_STATE_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_STAGING" / "POSTV16_AV4_PIVOT_P3_R1_Day0365_Accepted_Dense_State.npz"
DAY365_STATE_SHA = "8c2ea7f39d855d4636b42384235a8252f372b9bdecc3aed5d3ee85e795ed2c8f"
DAY365_FLOW_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution" / "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
DAY365_FLOW_SHA = "b49d48baa9d791b69a9e9c41635e1930fae84114b93ceb15ab5b21d3441ba08d"

# Certified recurrent observation authorities. Day405 hashes are bound dynamically
# to the formal R7-R10 PASS summary and checked against the actual files + manifest.
OBS = {
    370: {
        "dir": "POSTV16_AV4_PIVOT_P3_R1_R5_R2_Checkpoint_Resume_CarryForward_Day370_Pilot_and_Exact_Flow_Diagnostic",
        "state": "POSTV16_AV4_PIVOT_P3_R1_R5_R2_Day0370_Accepted_Dense_State.npz",
        "diag": "POSTV16_AV4_PIVOT_P3_R1_R5_R2_Day0370_Exact_Flow_Diagnostic.npz",
        "state_sha": "04fe6318623b1a7e4bf003cf49504648a2f32729a96c5a557294f664f4c35122",
        "diag_sha": "705409ee1b04241d294d9404d2945f4aa307ea0b2b68612a1cf8f86d7558e48a",
    },
    375: {
        "dir": "POSTV16_AV4_PIVOT_P3_R1_R6_Day370_to_Day375_SecondObservation_Pilot_and_Exact_Flow_Diagnostic",
        "state": "POSTV16_AV4_PIVOT_P3_R1_R6_Day0375_Accepted_Dense_State.npz",
        "diag": "POSTV16_AV4_PIVOT_P3_R1_R6_Day0375_Exact_Flow_Diagnostic.npz",
        "state_sha": "89b69ed69ef2c67babcf1e52ead0add950f366379c849f23645be5b18dc5d7ac",
        "diag_sha": "43957d890246452bcfc78467f19aba4f48feaaf9a0ffa58aababe7e7189e9c31",
    },
    380: {
        "dir": "POSTV16_AV4_PIVOT_P3_R1_R7_R5_XY2_Checkpoint_Resume_Day380_Pilot_and_Exact_Flow_Diagnostic",
        "state": "POSTV16_AV4_PIVOT_P3_R1_R7_R5_Day0380_Accepted_Dense_State.npz",
        "diag": "POSTV16_AV4_PIVOT_P3_R1_R7_R5_Day0380_Exact_Flow_Diagnostic.npz",
        "state_sha": "691bde994f9b0c80f2fc53f575ed642fd0aaef5259d8bb6d20b8508957f63eca",
        "diag_sha": "1f17c00888774c20c1f9a9a9a45965536f8412107721d676ab7b12d287249189",
    },
    385: {
        "dir": "POSTV16_AV4_PIVOT_P3_R1_R7_R6_XY2_Day380_to_Day385_FourthObservation_Pilot_and_Exact_Flow_Diagnostic",
        "state": "POSTV16_AV4_PIVOT_P3_R1_R7_R6_Day0385_Accepted_Dense_State.npz",
        "diag": "POSTV16_AV4_PIVOT_P3_R1_R7_R6_Day0385_Exact_Flow_Diagnostic.npz",
        "state_sha": "18a98bd27661fd1f2464f5e46e74389c794e2bdfc58a68541ee381a526d29988",
        "diag_sha": "3ec8d7b6a7877847501396478d5757761ed54a33de1358a2cc157859daba1c7d",
    },
    390: {
        "dir": "POSTV16_AV4_PIVOT_P3_R1_R7_R7_XY2_Day385_to_Day390_FifthObservation_Pilot_and_Exact_Flow_Diagnostic",
        "state": "POSTV16_AV4_PIVOT_P3_R1_R7_R7_Day0390_Accepted_Dense_State.npz",
        "diag": "POSTV16_AV4_PIVOT_P3_R1_R7_R7_Day0390_Exact_Flow_Diagnostic.npz",
        "state_sha": "83e26d77f5f853412b817c37dcd4d3958ba4469bbd14c10a8467a256b52c33ee",
        "diag_sha": "a5e2271830649b37e0de38459a9ead58fb79d4c20c185fee1d3390e9e749c9dc",
    },
    395: {
        "dir": "POSTV16_AV4_PIVOT_P3_R1_R7_R8_R3_XY2_Day390_to_Day395_SixthObservation_Pilot_and_Exact_Flow_Diagnostic",
        "state": "POSTV16_AV4_PIVOT_P3_R1_R7_R8_R3_Day0395_Accepted_Dense_State.npz",
        "diag": "POSTV16_AV4_PIVOT_P3_R1_R7_R8_R3_Day0395_Exact_Flow_Diagnostic.npz",
        "state_sha": "15a59e11db310a0eadc628dc8075d3bf58b19b97bf0648f94566682bb25f77e5",
        "diag_sha": "83a4911575266aa8380a33c94849061b91aa055da203f35455b0566fff8413a8",
    },
    400: {
        "dir": "POSTV16_AV4_PIVOT_P3_R1_R7_R9_XY2_Day395_to_Day400_SeventhObservation_Pilot_and_Exact_Flow_Diagnostic",
        "state": "POSTV16_AV4_PIVOT_P3_R1_R7_R9_Day0400_Accepted_Dense_State.npz",
        "diag": "POSTV16_AV4_PIVOT_P3_R1_R7_R9_Day0400_Exact_Flow_Diagnostic.npz",
        "state_sha": "9630449981429d90f3265dad60875217873000061a294b2bf60bbe806cb5c5d4",
        "diag_sha": "2e772ca70526a2c64bc0a84f3fbc42c2540593e6b7d79dc74787e33b52c0ac42",
    },
    405: {
        "dir": "POSTV16_AV4_PIVOT_P3_R1_R7_R10_XY2_Day400_to_Day405_EighthObservation_Pilot_and_Exact_Flow_Diagnostic",
        "state": "POSTV16_AV4_PIVOT_P3_R1_R7_R10_Day0405_Accepted_Dense_State.npz",
        "diag": "POSTV16_AV4_PIVOT_P3_R1_R7_R10_Day0405_Exact_Flow_Diagnostic.npz",
        "state_sha": None,
        "diag_sha": None,
    },
}

R7R10_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R10_Summary.json"
R7R10_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R7_R10_Decision_Contract.json"
R7R10_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R7_R10_Artifact_Manifest.csv"
R7R10_STATUS = "AV4PIVOTP3R1R7R10_XY2_DAY400_TO_DAY405_EIGHTH_OBSERVATION_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"
R7R10_CLASS = "P3R1_R7_XY2_DAY400_TO_DAY405_EIGHTH_OBSERVATION_TRANSPORT_AND_EXACT_FLOW_DIAGNOSTIC_CERTIFIED_NO_GENERIC_STAGE2_FALLBACK_DAY410_PILOT_AUTHORIZED"

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
    rows = csv_rows(directory / filename)
    if not rows:
        raise GateError(f"manifest_empty:{directory / filename}")
    out: dict[str, str] = {}
    for row in rows:
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p}")
        actual = sha256(p)
        if actual != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}:{actual}:{row['sha256']}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        out[p.name] = actual
    return out


def coords_ft() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    kk, jj, ii = np.indices(GRID)
    x = (ii + 0.5) * DX_FT
    y = (jj + 0.5) * DY_FT
    z = (kk + 0.5) * DZ_FT
    return x, y, z


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


def add_wells(ax, labels: bool = False) -> None:
    z0 = (min(COMPLETION_K) + 0.5) * DZ_FT
    z1 = (max(COMPLETION_K) + 0.5) * DZ_FT
    xi = (INJECTOR_I + 0.5) * DX_FT
    yi = (INJECTOR_J + 0.5) * DY_FT
    ax.plot([xi, xi], [yi, yi], [z0, z1], linewidth=3.0, color="black", label="Injector" if labels else None)
    for n, (i, j) in PRODUCERS.items():
        x = (i + 0.5) * DX_FT
        y = (j + 0.5) * DY_FT
        ax.plot([x, x], [y, y], [z0, z1], linewidth=2.0, color="dimgray", label="Producers" if labels and n == "PROD_SW" else None)


def load_day365(drive: Path) -> dict[str, Any]:
    state = drive / DAY365_STATE_REL
    flow = drive / DAY365_FLOW_REL
    if not state.is_file() or not flow.is_file():
        raise GateError(f"Day365_authority_missing:{state}:{flow}")
    if sha256(state) != DAY365_STATE_SHA:
        raise GateError("Day365_state_SHA_mismatch")
    if sha256(flow) != DAY365_FLOW_SHA:
        raise GateError("Day365_flow_SHA_mismatch")
    with np.load(state, allow_pickle=False) as z:
        saturation = np.asarray(z["cartesian_saturation"], dtype=np.float64)
    with np.load(flow, allow_pickle=False) as z:
        pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
        xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
        tof = np.asarray(z["streamline_tof_s"], dtype=np.float64)
        tau_end = np.asarray(z["tau_end_s"], dtype=np.float64)
    return {
        "day": 365,
        "saturation": saturation,
        "pressure": pressure,
        "xyz_m": xyz,
        "tof_s": tof,
        "tau_end_s": tau_end,
        "state_sha": DAY365_STATE_SHA,
        "diag_sha": DAY365_FLOW_SHA,
        "state_file": str(state),
        "diag_file": str(flow),
        "source_kind": "Day365 accepted state + A2-E refreshed exact flow epoch",
    }


def bind_day405(drive: Path) -> tuple[str, str, dict[str, Any]]:
    d = drive / BASE_AV4 / OBS[405]["dir"]
    if not d.is_dir():
        raise GateError(f"R7R10_output_missing:{d}")
    for fn in [R7R10_SUMMARY, R7R10_DECISION, R7R10_MANIFEST, OBS[405]["state"], OBS[405]["diag"]]:
        if not (d / fn).is_file():
            raise GateError(f"R7R10_artifact_missing:{fn}")
    verify_manifest(d, R7R10_MANIFEST)
    s = js(d / R7R10_SUMMARY)
    dec = js(d / R7R10_DECISION)
    if s.get("status") != R7R10_STATUS:
        raise GateError(f"R7R10_status:{s.get('status')}")
    if s.get("classification") != R7R10_CLASS:
        raise GateError(f"R7R10_classification:{s.get('classification')}")
    if dec.get("Day405_to_Day410_repaired_pilot_authorized") is not True:
        raise GateError("R7R10_Day410_not_authorized")
    if dec.get("P4_authorized") is not False or dec.get("P3_R1_full_rerun_authorized") is not False:
        raise GateError("R7R10_lock_state_changed")
    if dec.get("Day405_exact_diagnostic_is_one_shot_no_feedback") is not True:
        raise GateError("R7R10_diagnostic_feedback_contract_changed")
    state_sha = str(s.get("Day405_state_sha256"))
    diag_sha = str(s.get("Day405_diagnostic_sha256"))
    if len(state_sha) != 64 or len(diag_sha) != 64:
        raise GateError("R7R10_missing_Day405_hashes")
    if sha256(d / OBS[405]["state"]) != state_sha:
        raise GateError("R7R10_Day405_state_SHA_mismatch")
    if sha256(d / OBS[405]["diag"]) != diag_sha:
        raise GateError("R7R10_Day405_diagnostic_SHA_mismatch")
    return state_sha, diag_sha, s


def load_observation(drive: Path, day: int, spec: dict[str, Any]) -> dict[str, Any]:
    d = drive / BASE_AV4 / spec["dir"]
    state = d / spec["state"]
    diag = d / spec["diag"]
    if not state.is_file() or not diag.is_file():
        raise GateError(f"Day{day}_artifact_missing:{state}:{diag}")
    if sha256(state) != spec["state_sha"]:
        raise GateError(f"Day{day}_state_SHA_mismatch")
    if sha256(diag) != spec["diag_sha"]:
        raise GateError(f"Day{day}_diagnostic_SHA_mismatch")
    with np.load(state, allow_pickle=False) as z:
        state_sat = np.asarray(z["cartesian_saturation"], dtype=np.float64)
        physical_day = float(np.asarray(z["physical_day"]).reshape(()))
    with np.load(diag, allow_pickle=False) as z:
        saturation = np.asarray(z["saturation"], dtype=np.float64)
        pressure = np.asarray(z["pressure_psi"], dtype=np.float64)
        xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
        tof = np.asarray(z["streamline_tof_s"], dtype=np.float64)
        tau_end = np.asarray(z["tau_end_s"], dtype=np.float64)
        diag_day = float(np.asarray(z["diagnostic_day"]).reshape(()))
        no_fp = bool(np.asarray(z["diagnostic_is_same_time_fixed_point"]).reshape(()))
        feedback = bool(np.asarray(z["diagnostic_transport_feedback"]).reshape(()))
    if abs(physical_day - day) > 1.0e-10 or abs(diag_day - day) > 1.0e-10:
        raise GateError(f"Day{day}_time_mismatch:{physical_day}:{diag_day}")
    sat_err = float(np.max(np.abs(state_sat - saturation)))
    if sat_err > 1.0e-12:
        raise GateError(f"Day{day}_diagnostic_state_saturation_mismatch:{sat_err}")
    if no_fp or feedback:
        raise GateError(f"Day{day}_diagnostic_feedback_contract:{no_fp}:{feedback}")
    return {
        "day": day,
        "saturation": saturation,
        "pressure": pressure,
        "xyz_m": xyz,
        "tof_s": tof,
        "tau_end_s": tau_end,
        "state_sha": spec["state_sha"],
        "diag_sha": spec["diag_sha"],
        "state_file": str(state),
        "diag_file": str(diag),
        "source_kind": "accepted recurrent state + same-time exact no-feedback diagnostic",
    }


def validate_arrays(rec: dict[str, Any]) -> None:
    day = rec["day"]
    sat = rec["saturation"]
    p = rec["pressure"]
    xyz = rec["xyz_m"]
    tof = rec["tof_s"]
    tau = rec["tau_end_s"]
    if sat.shape != GRID or p.shape != GRID:
        raise GateError(f"Day{day}_grid_shape:{sat.shape}:{p.shape}")
    if xyz.ndim != 3 or xyz.shape[2] != 3:
        raise GateError(f"Day{day}_xyz_shape:{xyz.shape}")
    if tof.shape != xyz.shape[:2]:
        raise GateError(f"Day{day}_tof_shape:{tof.shape}:{xyz.shape}")
    if tau.shape != (xyz.shape[0],):
        raise GateError(f"Day{day}_tau_end_shape:{tau.shape}:{xyz.shape[0]}")
    for name, arr in [("sat", sat), ("pressure", p), ("xyz", xyz), ("tof", tof), ("tau", tau)]:
        if not np.all(np.isfinite(arr)):
            raise GateError(f"Day{day}_{name}_nonfinite")
    if float(np.min(sat)) < BACKGROUND - 1.0e-8 or float(np.max(sat)) > MAX_SAT + 1.0e-8:
        raise GateError(f"Day{day}_saturation_bounds:{np.min(sat)}:{np.max(sat)}")


def plot_saturation(rec: dict[str, Any], out: Path) -> int:
    day = rec["day"]
    sat = rec["saturation"]
    x, y, z = coords_ft()
    mask = sat >= SAT_PLOT_THRESHOLD
    if int(np.count_nonzero(mask)) < 25:
        mask = sat > BACKGROUND + 1.0e-5
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    pts = ax.scatter(x[mask], y[mask], z[mask], c=sat[mask], cmap="turbo", vmin=BACKGROUND, vmax=MAX_SAT, s=10, alpha=0.55, linewidths=0)
    add_wells(ax, labels=True)
    format_3d(ax, f"Day {day}: CO₂ saturation plume — 5× vertical exaggeration")
    cb = fig.colorbar(pts, ax=ax, pad=0.08, shrink=0.72)
    cb.set_label("Gas saturation")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / f"Day{day:04d}_Saturation_Plume_3D.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    return int(np.count_nonzero(mask))


def plot_pressure(rec: dict[str, Any], out: Path, pmin: float, pmax: float) -> None:
    day = rec["day"]
    p = rec["pressure"]
    x, y, z = coords_ft()
    sample = np.zeros(GRID, dtype=bool)
    sample[:, ::2, ::2] = True
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    pts = ax.scatter(x[sample], y[sample], z[sample], c=p[sample], cmap="viridis", vmin=pmin, vmax=pmax, s=8, alpha=0.38, linewidths=0)
    add_wells(ax, labels=True)
    format_3d(ax, f"Day {day}: exact refreshed pressure field — 5× vertical exaggeration")
    cb = fig.colorbar(pts, ax=ax, pad=0.08, shrink=0.72)
    cb.set_label("Pressure (psi)")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / f"Day{day:04d}_Pressure_Field_3D.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_streamlines(rec: dict[str, Any], out: Path, tof_norm: colors.Normalize, stride: int = 3) -> None:
    day = rec["day"]
    xyz_ft = rec["xyz_m"] / FT_TO_M
    tau_days = rec["tau_end_s"] / DAY_TO_S
    cmap = cm.get_cmap("plasma")
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    for idx in range(0, xyz_ft.shape[0], stride):
        line = xyz_ft[idx]
        ax.plot(line[:, 0], line[:, 1], line[:, 2], color=cmap(tof_norm(max(tau_days[idx], 1.0e-9))), linewidth=0.8, alpha=0.66)
    add_wells(ax, labels=True)
    format_3d(ax, f"Day {day}: exact Pollock streamlines colored by terminal TOF")
    sm = cm.ScalarMappable(norm=tof_norm, cmap=cmap)
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, pad=0.08, shrink=0.72)
    cb.set_label("Terminal TOF (days, log scale)")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / f"Day{day:04d}_Pollock_Streamlines_TOF_3D.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_combined(rec: dict[str, Any], out: Path, tof_norm: colors.Normalize, stride: int = 5) -> None:
    day = rec["day"]
    sat = rec["saturation"]
    x, y, z = coords_ft()
    mask = sat >= SAT_PLOT_THRESHOLD
    if int(np.count_nonzero(mask)) < 25:
        mask = sat > BACKGROUND + 1.0e-5
    xyz_ft = rec["xyz_m"] / FT_TO_M
    tau_days = rec["tau_end_s"] / DAY_TO_S
    cmap = cm.get_cmap("plasma")
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    plume = ax.scatter(x[mask], y[mask], z[mask], c=sat[mask], cmap="turbo", vmin=BACKGROUND, vmax=MAX_SAT, s=9, alpha=0.30, linewidths=0)
    for idx in range(0, xyz_ft.shape[0], stride):
        line = xyz_ft[idx]
        ax.plot(line[:, 0], line[:, 1], line[:, 2], color=cmap(tof_norm(max(tau_days[idx], 1.0e-9))), linewidth=0.65, alpha=0.52)
    add_wells(ax, labels=True)
    format_3d(ax, f"Day {day}: saturation plume + exact Pollock streamline overlay")
    cb = fig.colorbar(plume, ax=ax, pad=0.08, shrink=0.72)
    cb.set_label("Gas saturation")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / f"Day{day:04d}_Saturation_Streamline_Overlay_3D.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_progression(records: list[dict[str, Any]], out: Path) -> None:
    x, y, z = coords_ft()
    fig = plt.figure(figsize=(16, 14))
    for n, rec in enumerate(records, start=1):
        ax = fig.add_subplot(3, 3, n, projection="3d")
        sat = rec["saturation"]
        mask = sat >= SAT_PLOT_THRESHOLD
        if int(np.count_nonzero(mask)) < 25:
            mask = sat > BACKGROUND + 1.0e-5
        ax.scatter(x[mask], y[mask], z[mask], c=sat[mask], cmap="turbo", vmin=BACKGROUND, vmax=MAX_SAT, s=3, alpha=0.52, linewidths=0)
        add_wells(ax, labels=False)
        ax.set_title(f"Day {rec['day']}", fontsize=10)
        ax.set_xlim(0, LX_FT); ax.set_ylim(0, LY_FT); ax.set_zlim(0, LZ_FT)
        ax.set_box_aspect((1, 1, (LZ_FT / LX_FT) * VERTICAL_EXAGGERATION))
        ax.view_init(elev=24, azim=-58)
        ax.set_xticks([0, 500, 1000]); ax.set_yticks([0, 500, 1000]); ax.set_zticks([0, 30, 60])
        ax.tick_params(labelsize=6)
        if n not in (7,8,9): ax.set_xticklabels([])
        if n not in (1,4,7): ax.set_yticklabels([])
    sm = cm.ScalarMappable(norm=colors.Normalize(vmin=BACKGROUND, vmax=MAX_SAT), cmap="turbo")
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=fig.axes, fraction=0.018, pad=0.02)
    cbar.set_label("Gas saturation")
    fig.suptitle("PAD-Stream certified 3D saturation-plume progression: Day365–Day405\n5× vertical exaggeration; exact 5-day observation sequence", fontsize=15)
    fig.savefig(out / f"{OUT_TOKEN}_Saturation_Plume_Progression_3D.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def observation_metrics(rec: dict[str, Any], plotted_cells: int) -> dict[str, Any]:
    sat = rec["saturation"]
    p = rec["pressure"]
    tau_days = rec["tau_end_s"] / DAY_TO_S
    x, y, z = coords_ft()
    plume = sat > BACKGROUND + 1.0e-5
    weights = np.clip(sat - BACKGROUND, 0.0, None)
    sw = float(np.sum(weights))
    if sw > 0.0:
        cx = float(np.sum(x * weights) / sw)
        cy = float(np.sum(y * weights) / sw)
        cz = float(np.sum(z * weights) / sw)
    else:
        cx = cy = cz = float("nan")
    cell_volume_ft3 = DX_FT * DY_FT * DZ_FT
    return {
        "day": rec["day"],
        "pressure_min_psi": float(np.min(p)),
        "pressure_mean_psi": float(np.mean(p)),
        "pressure_max_psi": float(np.max(p)),
        "pressure_std_psi": float(np.std(p)),
        "saturation_min": float(np.min(sat)),
        "saturation_mean": float(np.mean(sat)),
        "saturation_max": float(np.max(sat)),
        "plume_cells_above_background": int(np.count_nonzero(plume)),
        "plume_cells_plotted": int(plotted_cells),
        "plume_bulk_volume_ft3": float(np.count_nonzero(plume) * cell_volume_ft3),
        "saturation_excess_centroid_x_ft": cx,
        "saturation_excess_centroid_y_ft": cy,
        "saturation_excess_centroid_z_ft": cz,
        "streamline_count": int(rec["xyz_m"].shape[0]),
        "nodes_per_streamline": int(rec["xyz_m"].shape[1]),
        "tau_end_min_days": float(np.min(tau_days)),
        "tau_end_median_days": float(np.median(tau_days)),
        "tau_end_max_days": float(np.max(tau_days)),
        "state_sha256": rec["state_sha"],
        "diagnostic_sha256": rec["diag_sha"],
    }


def selftest() -> None:
    assert GRID == (15, 50, 50)
    assert LX_FT == 1000.0 and LY_FT == 1000.0 and LZ_FT == 60.0
    assert sorted([365] + list(OBS)) == [365, 370, 375, 380, 385, 390, 395, 400, 405]
    x, y, z = coords_ft()
    assert x.shape == GRID and y.shape == GRID and z.shape == GRID
    assert abs(float(x[0,0,0]) - 10.0) < 1e-12
    assert abs(float(y[0,0,0]) - 10.0) < 1e-12
    assert abs(float(z[0,0,0]) - 2.0) < 1e-12
    assert abs(float(x[-1,-1,-1]) - 990.0) < 1e-12
    assert abs(float(z[-1,-1,-1]) - 58.0) < 1e-12
    assert R7R10_STATUS.endswith("PASS")
    assert "DAY410_PILOT_AUTHORIZED" in R7R10_CLASS
    print("POSTV16 AV4 PIVOT P3-R1 VIS-A1 structural self-test: PASS")


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
        print("=" * 150, flush=True)
        print("POSTV16-AV4-PIVOT-P3-R1-VIS-A1 — CERTIFIED DAY365-TO-DAY405 READ-ONLY 3D VISUALIZATION", flush=True)
        print("NO TRANSPORT ADVANCE. NO PRESSURE SOLVE. NO DARCY RECOMPUTATION. NO POLLOCK RETRACING. NO STATE MUTATION.", flush=True)
        print("SOURCE DATA ARE THE ALREADY-CERTIFIED ACCEPTED STATES AND EXACT SAME-TIME NO-FEEDBACK DIAGNOSTICS.", flush=True)
        print("=" * 150, flush=True)

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_R7R10_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        stage = "visualization_output_firewall"
        gate("VIS_output_does_not_preexist", not out.exists(), str(out))
        if staging.exists(): shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=False)

        stage = "R7R10_Day405_closure_authority"
        day405_state_sha, day405_diag_sha, r10sum = bind_day405(drive)
        OBS[405]["state_sha"] = day405_state_sha
        OBS[405]["diag_sha"] = day405_diag_sha
        gate("R7R10_status_exact", r10sum.get("status") == R7R10_STATUS, r10sum.get("status"))
        gate("R7R10_classification_exact", r10sum.get("classification") == R7R10_CLASS, r10sum.get("classification"))
        gate("R7R10_segment_no_generic_fallback", int(r10sum.get("segment_generic_XY2_fallback_step_count")) == 0, r10sum.get("segment_generic_XY2_fallback_step_count"))
        gate("R7R10_Day405_reached", abs(float(r10sum.get("pilot_final_day")) - 405.0) <= 1e-12, r10sum.get("pilot_final_day"))
        gate("R7R10_P4_locked", r10sum.get("P4_authorized") is False)
        print("R7-R10 Day405 formal PASS confirmed from Drive artifacts.", flush=True)
        print("Day405 state SHA256      :", day405_state_sha, flush=True)
        print("Day405 diagnostic SHA256 :", day405_diag_sha, flush=True)

        stage = "source_observation_authority"
        records: list[dict[str, Any]] = []
        rec365 = load_day365(drive)
        validate_arrays(rec365)
        records.append(rec365)
        authority_rows = [{
            "day": 365,
            "source_kind": rec365["source_kind"],
            "state_file": rec365["state_file"],
            "state_sha256": rec365["state_sha"],
            "diagnostic_file": rec365["diag_file"],
            "diagnostic_sha256": rec365["diag_sha"],
        }]
        gate("Day365_authority_exact", True)

        for day in sorted(OBS):
            rec = load_observation(drive, day, OBS[day])
            validate_arrays(rec)
            records.append(rec)
            authority_rows.append({
                "day": day,
                "source_kind": rec["source_kind"],
                "state_file": rec["state_file"],
                "state_sha256": rec["state_sha"],
                "diagnostic_file": rec["diag_file"],
                "diagnostic_sha256": rec["diag_sha"],
            })
            gate(f"Day{day}_state_and_exact_diagnostic_authority", True)

        stage = "global_visualization_scales"
        pmin = min(float(np.min(r["pressure"])) for r in records)
        pmax = max(float(np.max(r["pressure"])) for r in records)
        tau_min = min(float(np.min(r["tau_end_s"] / DAY_TO_S)) for r in records)
        tau_max = max(float(np.max(r["tau_end_s"] / DAY_TO_S)) for r in records)
        gate("pressure_scale_finite", np.isfinite(pmin) and np.isfinite(pmax) and pmax > pmin, (pmin, pmax))
        gate("TOF_scale_positive", tau_min > 0.0 and tau_max > tau_min, (tau_min, tau_max))
        tof_norm = colors.LogNorm(vmin=tau_min, vmax=tau_max)

        stage = "render_3D_plots"
        metric_rows = []
        for rec in records:
            day = rec["day"]
            print(f"[VIS] Day {day}: saturation plume", flush=True)
            plotted = plot_saturation(rec, staging)
            print(f"[VIS] Day {day}: pressure field", flush=True)
            plot_pressure(rec, staging, pmin, pmax)
            print(f"[VIS] Day {day}: Pollock + TOF", flush=True)
            plot_streamlines(rec, staging, tof_norm)
            print(f"[VIS] Day {day}: saturation + streamline overlay", flush=True)
            plot_combined(rec, staging, tof_norm)
            metric_rows.append(observation_metrics(rec, plotted))
        print("[VIS] Day365-to-Day405 plume progression montage", flush=True)
        plot_progression(records, staging)

        stage = "publication"
        write_csv(staging / AUTHORITY, authority_rows)
        write_csv(staging / METRICS, metric_rows)
        pngs = sorted(staging.glob("*.png"))
        expected_png_count = len(records) * 4 + 1
        gate("expected_3D_plot_count", len(pngs) == expected_png_count, len(pngs))
        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "repository_parent_R7R10_commit": PARENT,
            "source_R7R10_status": R7R10_STATUS,
            "source_R7R10_classification": R7R10_CLASS,
            "Day405_state_sha256": day405_state_sha,
            "Day405_diagnostic_sha256": day405_diag_sha,
            "observation_days": [int(r["day"]) for r in records],
            "grid_shape_kji": list(GRID),
            "cell_dimensions_ft": [DZ_FT, DY_FT, DX_FT],
            "reservoir_dimensions_ft_xyz": [LX_FT, LY_FT, LZ_FT],
            "vertical_exaggeration": VERTICAL_EXAGGERATION,
            "saturation_plot_threshold": SAT_PLOT_THRESHOLD,
            "global_pressure_min_psi": pmin,
            "global_pressure_max_psi": pmax,
            "global_terminal_TOF_min_days": tau_min,
            "global_terminal_TOF_max_days": tau_max,
            "per_observation_plot_count": 4,
            "progression_montage_count": 1,
            "total_png_count": len(pngs),
            "plots": [p.name for p in pngs],
            "source_authority_table": AUTHORITY,
            "observation_metrics_table": METRICS,
            "read_only_visualization": True,
            "authoritative_physics_state_mutated": False,
            "authoritative_physical_time_advanced": False,
            "pressure_solve_executed": False,
            "Darcy_recomputation_executed": False,
            "Pollock_retracing_executed": False,
            "transport_execution_executed": False,
            "Day405_to_Day410_transport_executed": False,
            "Day405_to_Day410_transport_remains_authorized": True,
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
        }
        (staging / SUMMARY).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest_rows = []
        for p in sorted(staging.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                manifest_rows.append({"file": p.name, "sha256": sha256(p), "bytes": p.stat().st_size})
        write_csv(staging / MANIFEST, manifest_rows)
        staging.rename(out)

        print("=" * 150, flush=True)
        print(M, "PASS", flush=True)
        print("R7-R10 Day405 closure                    : CONFIRMED", flush=True)
        print("Observation days                         :", [r["day"] for r in records], flush=True)
        print("3D PNG files                             :", len(pngs), flush=True)
        print("Output directory                         :", out, flush=True)
        print("Authoritative physics state mutated      : False", flush=True)
        print("Authoritative physical time advanced     : False", flush=True)
        print("Day405->Day410 transport executed        : False", flush=True)
        print("Day405->Day410 transport remains allowed : True", flush=True)
        print("P4 authorized                            : False", flush=True)
        print("=" * 150, flush=True)
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
