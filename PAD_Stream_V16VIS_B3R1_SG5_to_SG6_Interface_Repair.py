from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
from typing import Any

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable


MILESTONE = "V16VIS-B3R1"
STATUS = "FROZEN_V16_POLLOCK_STREAMLINE_AND_TOF_VISUALS_VALIDATED_R1"
NEXT = "V16VIS-B4 - Frozen V16 CO2 Plume Evolution Visuals"

RELEASE_ID = "PAD-STREAM-V16-RC1-B92D52088D01078A"
RELEASE_PATH_ID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

A1_RUNNER = "PAD_Stream_V16VIS_A1_Visual_Authority_Manifest_and_Data_Extraction.py"
A1_GIT_BLOB = "7ed31f0e69b63489f25a1833cdc3693f735b1233"
B2_RUNNER = "PAD_Stream_V16VIS_B2_Frozen_V16_Pressure_and_Darcy_Flow_Visuals.py"
B2_GIT_BLOB = "414fd135a137bb3ad9df75cb1d22bb41e559e05d"
B3_FAILED_RUNNER = "PAD_Stream_V16VIS_B3_Frozen_V16_Pollock_Streamline_and_TOF_Visuals.py"
B3_FAILED_GIT_BLOB = "b43201c73946665deafd8360add67a501ebe60ff"
SG2_RUNNER = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_GIT_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3_RUNNER = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_GIT_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
SG4_RUNNER = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_GIT_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"
SG5_RUNNER = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG5_GIT_BLOB = "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"
SG6_RUNNER = "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py"
SG6_GIT_BLOB = "70ceda68e02894167958d753d88b4dbd694731ab"
R3R2R1_RUNNER = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_GIT_BLOB = "740c6da03e73906646bf0153633187e749449f31"
R3R4R1_RUNNER = "PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4R1_GIT_BLOB = "5f8433437ce111533338ceada922f51abb2edefe"

EXPECTED_A1_STATUS = "V16_VISUAL_AUTHORITY_MANIFEST_AND_DATA_EXTRACTION_VALIDATED"
EXPECTED_B2_STATUS = "FROZEN_V16_PRESSURE_AND_DARCY_FLOW_VISUALS_VALIDATED"
EXPECTED_A1_CACHE_SHA256 = "2acbbbc8608eb771d1a6ea6909c7d37caec2ee77666a7828226e3a9e531d316e"
TERMINAL_DAY = 1000.0

A1_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_A_Authority_and_Data_Extraction"
B2_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_B2_Pressure_and_Darcy_Flow"
OUT_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_B3R1_Pollock_Streamline_and_TOF_Interface_Repair"
BLOCKED_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_B3R1_BLOCKED"

A1_CACHE = "V16VIS_A1_Authoritative_Visual_Data.npz"
A1_SUMMARY = "PAD_Stream_V16VIS_A1_Summary.json"
A1_CLOSURE = "V16VIS_A1_Final_Closure.json"
A1_COORD = "V16VIS_A1_Coordinate_Convention.json"
A1_MANIFEST = "V16VIS_A1_Artifact_Manifest.csv"

B2_SUMMARY = "PAD_Stream_V16VIS_B2_Summary.json"
B2_CLOSURE = "V16VIS_B2_Final_Closure.json"
B2_MANIFEST = "V16VIS_B2_Artifact_Manifest.csv"

GRID_SHAPE = (15, 50, 50)
NX, NY, NZ = 50, 50, 15
DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0
LX_FT = 1000.0
LY_FT = 1000.0
LZ_FT = 60.0
FT_TO_M = 0.3048
M_TO_FT = 1.0 / FT_TO_M
DAY_TO_S = 86400.0

INJECTOR_I = 24
INJECTOR_J = 24
PRODUCERS = {
    "PROD_SW": {"i": 4, "j": 4},
    "PROD_SE": {"i": 45, "j": 4},
    "PROD_NW": {"i": 4, "j": 45},
    "PROD_NE": {"i": 45, "j": 45},
}
PRODUCER_NAMES = ["PROD_SW", "PROD_SE", "PROD_NW", "PROD_NE"]
COMPLETION_TOP_DEPTH_FT = 20.0
COMPLETION_BASE_DEPTH_FT = 40.0

DPI = 300
FIGSIZE = (9.0, 7.0)
VERTICAL_EXAGGERATION = 4.166666666666667

FIGURE_VARIANTS = [
    ("S01", "full_3d", "S01_Full_3D_V16_Pollock_Streamline_Field_1000d"),
    ("S02", "by_producer", "S02_V16_Streamlines_by_Producer_1000d"),
    ("S03", "by_terminal_tof", "S03_V16_Streamlines_by_Terminal_TOF_1000d"),
    ("S04", "representative_anatomy", "S04_Representative_Streamline_Anatomy_1000d"),
    ("T01", "weighted_histogram", "T01_V16_Reservoir_TOF_Distribution_1000d"),
    ("T02", "selected_distance_tof", "T02_Distance_vs_TOF_Selected_Streamlines_1000d"),
    ("T03", "xi_tof_schematic", "T03_Xi_TOF_Transport_Coordinate_Schematic"),
]


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_blob_sha(path: Path, root: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), "hash-object", str(path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout.strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists():
            if p.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            p.write_bytes(data)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"module_spec_failed:{path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save_figure(fig: plt.Figure, out: Path, stem: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ext in ("png", "pdf"):
        p = out / f"{stem}.{ext}"
        if p.exists():
            raise GateError(f"existing_figure:{p.name}")
        fig.savefig(p, dpi=DPI, bbox_inches="tight")
        rows.append({"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size})
    plt.close(fig)
    return rows


def cell_center_x_ft(i: int) -> float:
    return (i + 0.5) * DX_FT


def cell_center_y_ft(j: int) -> float:
    return (j + 0.5) * DY_FT


def add_wells_3d(ax: Any) -> None:
    inj_x = cell_center_x_ft(INJECTOR_I)
    inj_y = cell_center_y_ft(INJECTOR_J)
    ax.plot(
        [inj_x, inj_x], [inj_y, inj_y],
        [COMPLETION_TOP_DEPTH_FT, COMPLETION_BASE_DEPTH_FT],
        linewidth=2.2, marker="^", markevery=[0], label="INJECTOR"
    )
    for name, well in PRODUCERS.items():
        x = cell_center_x_ft(well["i"])
        y = cell_center_y_ft(well["j"])
        ax.plot(
            [x, x], [y, y],
            [COMPLETION_TOP_DEPTH_FT, COMPLETION_BASE_DEPTH_FT],
            linewidth=1.8, marker="v", markevery=[0], label=name
        )


def configure_3d(ax: Any, title: str) -> None:
    ax.set_title(title)
    ax.set_xlabel("X, ft")
    ax.set_ylabel("Y, ft")
    ax.set_zlabel("Depth below reservoir top, ft (+z downward)")
    ax.set_xlim(0.0, LX_FT)
    ax.set_ylim(0.0, LY_FT)
    ax.set_zlim(LZ_FT, 0.0)
    ax.set_box_aspect((LX_FT, LY_FT, LZ_FT * VERTICAL_EXAGGERATION))


def producer_color_map() -> dict[str, Any]:
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    return {name: colors[i % len(colors)] for i, name in enumerate(PRODUCER_NAMES)}


def select_weighted_median_index(values: np.ndarray, weights: np.ndarray, mask: np.ndarray | None = None) -> int:
    values = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if mask is None:
        indices = np.arange(values.size)
    else:
        indices = np.flatnonzero(mask)
    if indices.size == 0:
        raise GateError("empty_selection_for_weighted_median")
    v = values[indices]
    w = weights[indices]
    order = np.argsort(v)
    idx_sorted = indices[order]
    w_sorted = w[order]
    cumulative = np.cumsum(w_sorted)
    target = 0.5 * cumulative[-1]
    return int(idx_sorted[np.searchsorted(cumulative, target, side="left")])


def render_s01(out: Path, db: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    xyz_ft = db["xyz_m"] * M_TO_FT
    fig = plt.figure(figsize=FIGSIZE)
    ax = fig.add_subplot(111, projection="3d")
    for pts in xyz_ft:
        ax.plot(pts[:, 0], pts[:, 1], pts[:, 2], linewidth=0.42, alpha=0.28)
    add_wells_3d(ax)
    configure_3d(ax, "S01 — Full 3D Frozen V16 Pollock Streamline Field (1000 d)")
    ax.text2D(
        0.02, 0.02,
        f"{len(xyz_ft):,} producer-captured streamlines | vertical exaggeration {VERTICAL_EXAGGERATION:.2f}×",
        transform=ax.transAxes,
    )
    return save_figure(fig, out, "S01_Full_3D_V16_Pollock_Streamline_Field_1000d")


def render_s02(out: Path, db: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    xyz_ft = db["xyz_m"] * M_TO_FT
    labels = np.asarray(db["producer"]).astype(str)
    cmap = producer_color_map()
    fig = plt.figure(figsize=FIGSIZE)
    ax = fig.add_subplot(111, projection="3d")
    for name in PRODUCER_NAMES:
        idx = np.flatnonzero(labels == name)
        for n, s in enumerate(idx):
            pts = xyz_ft[s]
            ax.plot(
                pts[:, 0], pts[:, 1], pts[:, 2],
                linewidth=0.50, alpha=0.36,
                color=cmap[name],
                label=name if n == 0 else None,
            )
    add_wells_3d(ax)
    configure_3d(ax, "S02 — Frozen V16 Pollock Streamlines Colored by Producer (1000 d)")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.98), fontsize=8)
    return save_figure(fig, out, "S02_V16_Streamlines_by_Producer_1000d")


def render_s03(out: Path, db: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    xyz_ft = db["xyz_m"] * M_TO_FT
    tau_end_days = np.asarray(db["tau_end_s"], dtype=np.float64) / DAY_TO_S
    norm = Normalize(vmin=float(np.min(tau_end_days)), vmax=float(np.max(tau_end_days)))
    cmap = plt.get_cmap("viridis")
    fig = plt.figure(figsize=FIGSIZE)
    ax = fig.add_subplot(111, projection="3d")
    for pts, tau_d in zip(xyz_ft, tau_end_days):
        ax.plot(
            pts[:, 0], pts[:, 1], pts[:, 2],
            linewidth=0.52, alpha=0.40,
            color=cmap(norm(tau_d)),
        )
    add_wells_3d(ax)
    configure_3d(ax, "S03 — Frozen V16 Pollock Streamlines Colored by Terminal TOF (1000 d)")
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.72, pad=0.08)
    cbar.set_label("Terminal time-of-flight, days")
    return save_figure(fig, out, "S03_V16_Streamlines_by_Terminal_TOF_1000d")


def render_s04(out: Path, db: dict[str, np.ndarray], representative_index: int) -> list[dict[str, Any]]:
    pts_ft = db["xyz_m"][representative_index] * M_TO_FT
    tau_days = db["tau_s"][representative_index] / DAY_TO_S
    xi = np.asarray(db["xi"], dtype=np.float64)
    label = str(db["producer"][representative_index])
    path_end_ft = float(db["path_length_m"][representative_index, -1] * M_TO_FT)
    marker_xi = np.asarray([0.0, 0.25, 0.50, 0.75, 1.0])
    marker_indices = [int(np.argmin(np.abs(xi - q))) for q in marker_xi]

    fig = plt.figure(figsize=FIGSIZE)
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(pts_ft[:, 0], pts_ft[:, 1], pts_ft[:, 2], linewidth=2.0)
    ax.scatter(
        pts_ft[marker_indices, 0],
        pts_ft[marker_indices, 1],
        pts_ft[marker_indices, 2],
        s=38,
    )
    for q, idx in zip(marker_xi, marker_indices):
        ax.text(
            pts_ft[idx, 0], pts_ft[idx, 1], pts_ft[idx, 2],
            f" ξ={q:.2f}\n τ={tau_days[idx]:.1f} d",
            fontsize=7,
        )
    add_wells_3d(ax)
    configure_3d(ax, "S04 — Representative Frozen V16 Streamline Anatomy")
    ax.text2D(
        0.02, 0.02,
        f"Producer: {label} | terminal TOF: {tau_days[-1]:.2f} d | path length: {path_end_ft:.1f} ft",
        transform=ax.transAxes,
    )
    return save_figure(fig, out, "S04_Representative_Streamline_Anatomy_1000d")


def render_t01(out: Path, db: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    tau_days = np.asarray(db["tau_end_s"], dtype=np.float64) / DAY_TO_S
    weights_day = np.asarray(db["weights_m3_s"], dtype=np.float64) * DAY_TO_S
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.hist(tau_days, bins=42, weights=weights_day)
    ax.set_xlabel("Terminal time-of-flight, days")
    ax.set_ylabel("Streamline flow weight, m³/day")
    ax.set_title("T01 — Frozen V16 Reservoir Time-of-Flight Distribution (1000 d)")
    ax.text(
        0.98, 0.97,
        f"N = {len(tau_days):,}\nMin = {np.min(tau_days):.2f} d\nMedian = {np.median(tau_days):.2f} d\nMax = {np.max(tau_days):.2f} d",
        transform=ax.transAxes, ha="right", va="top",
    )
    return save_figure(fig, out, "T01_V16_Reservoir_TOF_Distribution_1000d")


def render_t02(out: Path, db: dict[str, np.ndarray], selected_by_producer: dict[str, int]) -> list[dict[str, Any]]:
    cmap = producer_color_map()
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for name in PRODUCER_NAMES:
        idx = selected_by_producer[name]
        length_ft = db["path_length_m"][idx] * M_TO_FT
        tau_days = db["tau_s"][idx] / DAY_TO_S
        ax.plot(length_ft, tau_days, linewidth=1.8, label=name, color=cmap[name])
        ax.scatter([length_ft[-1]], [tau_days[-1]], s=30, color=cmap[name])
    ax.set_xlabel("Cumulative distance along streamline, ft")
    ax.set_ylabel("Cumulative time-of-flight, days")
    ax.set_title("T02 — Distance vs TOF on Representative Producer Streamlines (1000 d)")
    ax.legend()
    return save_figure(fig, out, "T02_Distance_vs_TOF_Selected_Streamlines_1000d")


def render_t03(out: Path) -> list[dict[str, Any]]:
    xi = np.linspace(0.0, 1.0, 201)
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(xi, xi, linewidth=2.2)
    ax.scatter([0.0, 0.25, 0.50, 0.75, 1.0], [0.0, 0.25, 0.50, 0.75, 1.0], s=36)
    ax.set_xlabel(r"Normalized transport coordinate $\xi = \tau/\tau_{end}$")
    ax.set_ylabel(r"Normalized time-of-flight $\tau/\tau_{end}$")
    ax.set_title("T03 — SG6 ξ–TOF Transport-Coordinate Contract")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.text(0.02, 0.93, "Injector / streamline origin", transform=ax.transAxes, va="top")
    ax.text(0.98, 0.08, "Producer / streamline terminus", transform=ax.transAxes, ha="right")
    ax.text(
        0.50, 0.18,
        "201 common ξ nodes\nPollock cumulative pore-velocity time = physical TOF\nNo transport solve is performed in SG6",
        transform=ax.transAxes, ha="center",
    )
    ax.grid(True, alpha=0.25)
    return save_figure(fig, out, "T03_Xi_TOF_Transport_Coordinate_Schematic")


def self_test() -> None:
    if RELEASE_ID != "PAD-STREAM-V16-RC1-B92D52088D01078A":
        raise RuntimeError("release_identity")
    if GRID_SHAPE != (15, 50, 50):
        raise RuntimeError("grid_identity")
    if len(FIGURE_VARIANTS) != 7:
        raise RuntimeError("figure_variant_count")
    if PRODUCER_NAMES != ["PROD_SW", "PROD_SE", "PROD_NW", "PROD_NE"]:
        raise RuntimeError("producer_order")
    if OUT_REL != Path("visuals") / RELEASE_PATH_ID / "Phase_B3R1_Pollock_Streamline_and_TOF_Interface_Repair":
        raise RuntimeError("output_path")
    if VERTICAL_EXAGGERATION <= 1.0:
        raise RuntimeError("vertical_exaggeration")
    if COMPLETION_TOP_DEPTH_FT != 20.0 or COMPLETION_BASE_DEPTH_FT != 40.0:
        raise RuntimeError("completion_depth")
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.plot([0.0, 1.0], [0.0, 1.0], [2.0, 58.0])
    ax.set_zlim(60.0, 0.0)
    plt.close(fig)
    print("PAD-Stream V16VIS-B3R1 SG5-to-SG6 interface repair self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    a1 = drive / A1_REL
    b2 = drive / B2_REL
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    failed_stage: str | None = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 164)
        print("PAD-Stream V16VIS-B3R1 — SG5-to-SG6 Interface Repair for Frozen V16 Pollock / TOF Visuals")
        print("=" * 164)
        print("Release                    :", RELEASE_ID)
        print("Simulation                  : none")
        print("Accepted-state mutation     : none")
        print("Flow state                  : direct frozen A1 terminal 1000-day state")
        print("Streamline reconstruction   : exact frozen SG5 Pollock tracing")
        print("TOF coordinates             : exact frozen SG6 transport-coordinate construction")
        print("Display convention          : +z downward / increasing depth")

        failed_stage = "repository_source_binding"
        source_bindings = [
            ("A1", A1_RUNNER, A1_GIT_BLOB),
            ("B2", B2_RUNNER, B2_GIT_BLOB),
            ("B3_FAILED_PARENT", B3_FAILED_RUNNER, B3_FAILED_GIT_BLOB),
            ("SG2", SG2_RUNNER, SG2_GIT_BLOB),
            ("SG3", SG3_RUNNER, SG3_GIT_BLOB),
            ("SG4", SG4_RUNNER, SG4_GIT_BLOB),
            ("SG5", SG5_RUNNER, SG5_GIT_BLOB),
            ("SG6", SG6_RUNNER, SG6_GIT_BLOB),
            ("R3R2R1", R3R2R1_RUNNER, R3R2R1_GIT_BLOB),
            ("R3R4R1", R3R4R1_RUNNER, R3R4R1_GIT_BLOB),
        ]
        for role, filename, expected in source_bindings:
            p = root / filename
            gate(f"{role}_exists", p.is_file(), p)
            actual = git_blob_sha(p, root)
            gate(f"{role}_git_blob_exact", actual == expected, actual)

        failed_stage = "phase_prerequisite_binding"
        for name in [A1_CACHE, A1_SUMMARY, A1_CLOSURE, A1_COORD, A1_MANIFEST]:
            gate(f"A1_exists_{name}", (a1 / name).is_file(), a1 / name)
        for name in [B2_SUMMARY, B2_CLOSURE, B2_MANIFEST]:
            gate(f"B2_exists_{name}", (b2 / name).is_file(), b2 / name)

        a1_summary = load_json(a1 / A1_SUMMARY)
        a1_closure = load_json(a1 / A1_CLOSURE)
        coord = load_json(a1 / A1_COORD)
        b2_summary = load_json(b2 / B2_SUMMARY)
        b2_closure = load_json(b2 / B2_CLOSURE)

        gate("A1_status_exact", a1_summary.get("status") == EXPECTED_A1_STATUS, a1_summary.get("status"))
        gate("A1_release_exact", a1_summary.get("release_id") == RELEASE_ID, a1_summary.get("release_id"))
        gate("A1_closure_passed", a1_closure.get("all_gates_passed") is True)
        gate("B2_status_exact", b2_summary.get("status") == EXPECTED_B2_STATUS, b2_summary.get("status"))
        gate("B2_release_exact", b2_summary.get("release_id") == RELEASE_ID, b2_summary.get("release_id"))
        gate("B2_closure_passed", b2_closure.get("all_gates_passed") is True)
        gate("B2_phase_B3_authorized", b2_closure.get("phase_B3_authorized") is True)
        gate("coordinate_downward", coord["display_axes"]["positive_z_direction"] == "DOWNWARD_DEPTH", coord["display_axes"]["positive_z_direction"])
        gate("layer_order_exact", coord["layer_order"]["layer_1"] == "SHALLOWEST" and coord["layer_order"]["layer_15"] == "DEEPEST", coord["layer_order"])

        cache_path = a1 / A1_CACHE
        cache_sha = sha256_file(cache_path)
        gate("A1_cache_SHA_exact", cache_sha == EXPECTED_A1_CACHE_SHA256, cache_sha)
        gate("A1_summary_cache_SHA_exact", a1_summary.get("visual_cache_sha256") == cache_sha, a1_summary.get("visual_cache_sha256"))

        failed_stage = "authoritative_terminal_state_extraction"
        with np.load(cache_path, allow_pickle=False) as z:
            perm_md = np.asarray(z["permeability_md"], dtype=np.float64)
            flow_days = np.asarray(z["flow_days"], dtype=np.float64)
            flow_saturation = np.asarray(z["flow_saturation"], dtype=np.float64)
            flow_pressure = np.asarray(z["flow_pressure_psi"], dtype=np.float64)

        gate("perm_shape_exact", perm_md.shape == GRID_SHAPE, perm_md.shape)
        gate("flow_pressure_shape_exact", flow_pressure.ndim == 4 and flow_pressure.shape[1:] == GRID_SHAPE, flow_pressure.shape)
        gate("flow_saturation_shape_exact", flow_saturation.shape == flow_pressure.shape, flow_saturation.shape)
        gate("terminal_day_exact", float(flow_days[-1]) == TERMINAL_DAY, float(flow_days[-1]))
        gate("terminal_pressure_finite", bool(np.all(np.isfinite(flow_pressure[-1]))))
        gate("terminal_saturation_finite", bool(np.all(np.isfinite(flow_saturation[-1]))))
        terminal_pressure = flow_pressure[-1].copy()
        terminal_sat = flow_saturation[-1].copy()

        failed_stage = "read_only_terminal_flow_reconstruction"
        sg2 = load_module(root / SG2_RUNNER, "v16vis_b3_sg2")
        sg3 = load_module(root / SG3_RUNNER, "v16vis_b3_sg3")
        sg4 = load_module(root / SG4_RUNNER, "v16vis_b3_sg4")
        sg5 = load_module(root / SG5_RUNNER, "v16vis_b3_sg5")
        sg6 = load_module(root / SG6_RUNNER, "v16vis_b3_sg6")
        r3 = load_module(root / R3R2R1_RUNNER, "v16vis_b3r1_r3r2r1")
        r3r4r1 = load_module(root / R3R4R1_RUNNER, "v16vis_b3r1_r3r4r1")

        kx, ky, kz = sg2.build_directional_permeability(perm_md)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)
        mobility = r3.phase_mobility_fields(terminal_sat)
        tx, ty, tz, _face_mobility = r3.build_updated_transmissibilities(
            sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
        )
        qx, qy, qz = sg4.compute_face_fluxes(terminal_pressure, tx, ty, tz)
        gate("Qx_shape_exact", qx.shape == (15, 50, 49), qx.shape)
        gate("Qy_shape_exact", qy.shape == (15, 49, 50), qy.shape)
        gate("Qz_shape_exact", qz.shape == (14, 50, 50), qz.shape)
        gate("terminal_face_flux_finite", bool(np.all(np.isfinite(qx)) and np.all(np.isfinite(qy)) and np.all(np.isfinite(qz))))

        _A, _b, producer_wi = r3.assemble_updated_pressure_system(
            sg3, perm_md, tx, ty, tz, mobility["lambda_total"]
        )
        _rates, producer_sink = r3.producer_rates_updated(sg3, terminal_pressure, producer_wi)
        conservation = r3.flow_conservation_metrics(sg3, sg4, qx, qy, qz, producer_sink)
        gate("terminal_flow_local_conservation", conservation["local_relative_l2_error"] < 1.0e-8, conservation["local_relative_l2_error"])
        gate("terminal_flow_global_conservation", conservation["global_relative_mismatch"] < 1.0e-8, conservation["global_relative_mismatch"])

        failed_stage = "exact_pollock_reconstruction"
        vx, vy, vz = sg5.construct_face_pore_velocities(qx, qy, qz)
        faces, seeds = sg5.build_seeds(qx, qy, qz)
        streamlines = sg5.trace_streamlines(seeds, vx, vy, vz)
        gate("outgoing_injector_faces_positive", len(faces) > 0, len(faces))
        gate("streamline_seed_count_positive", len(seeds) > 0, len(seeds))
        gate("streamline_result_count_exact", len(streamlines) == len(seeds), (len(streamlines), len(seeds)))

        seed_weight = float(sum(float(s["weight_m3_s"]) for s in seeds))
        captured = [s for s in streamlines if s["status"] == "PRODUCER"]
        captured_weight = float(sum(float(s["weight_m3_s"]) for s in captured))
        capture_fraction = captured_weight / max(seed_weight, 1.0e-30)
        gate("producer_capture_nonempty", len(captured) > 0, len(captured))
        gate("full_streamline_weight_capture", abs(capture_fraction - 1.0) <= 1.0e-10, capture_fraction)
        gate("all_streamlines_producer_captured", len(captured) == len(streamlines), (len(captured), len(streamlines)))

        failed_stage = "sg5_to_sg6_interface_repair"
        sg6_streamlines = r3r4r1.convert_sg5_to_sg6_streamlines(streamlines)
        gate("SG5_to_SG6_adapter_count_exact", len(sg6_streamlines) == len(streamlines), (len(sg6_streamlines), len(streamlines)))
        required_sg6_keys = {"id", "points_m", "tau_s", "weight_m3_s", "tau_end_s", "status", "producer"}
        gate(
            "SG5_to_SG6_adapter_schema_exact",
            all(required_sg6_keys.issubset(set(s.keys())) for s in sg6_streamlines),
            "required keys: " + ",".join(sorted(required_sg6_keys)),
        )
        gate(
            "SG5_to_SG6_time_mapping_exact",
            all(
                np.array_equal(np.asarray(raw["times_s"]), np.asarray(conv["tau_s"]))
                and float(raw["travel_time_s"]) == float(conv["tau_end_s"])
                for raw, conv in zip(streamlines, sg6_streamlines)
            ),
        )

        failed_stage = "sg6_tof_transport_coordinates"
        db = sg6.build_transport_database(sg6_streamlines)
        sg6.validate_transport(db)
        gate("SG6_common_xi_nodes", len(db["xi"]) == 201, len(db["xi"]))
        gate("SG6_xyz_shape", db["xyz_m"].shape == (len(captured), 201, 3), db["xyz_m"].shape)
        gate("SG6_tau_shape", db["tau_s"].shape == (len(captured), 201), db["tau_s"].shape)
        gate("SG6_positive_weights", bool(np.all(db["weights_m3_s"] > 0.0)))
        gate("SG6_positive_terminal_tof", bool(np.all(db["tau_end_s"] > 0.0)))
        gate("SG6_all_producers", all(np.any(np.asarray(db["producer"]).astype(str) == name) for name in PRODUCER_NAMES))

        tau_end_days = np.asarray(db["tau_end_s"], dtype=np.float64) / DAY_TO_S
        weights = np.asarray(db["weights_m3_s"], dtype=np.float64)
        labels = np.asarray(db["producer"]).astype(str)
        representative_index = select_weighted_median_index(tau_end_days, weights)
        selected_by_producer = {
            name: select_weighted_median_index(tau_end_days, weights, labels == name)
            for name in PRODUCER_NAMES
        }
        gate("representative_index_valid", 0 <= representative_index < len(tau_end_days), representative_index)
        gate("producer_representatives_complete", set(selected_by_producer) == set(PRODUCER_NAMES), selected_by_producer)

        failed_stage = "figure_rendering"
        if out.exists() and any(out.iterdir()):
            raise GateError("B3R1_output_directory_not_empty:refusing_to_overwrite_existing_visual_release")
        out.mkdir(parents=True, exist_ok=True)

        rendered: list[dict[str, Any]] = []
        rendered.extend(render_s01(out, db))
        rendered.extend(render_s02(out, db))
        rendered.extend(render_s03(out, db))
        rendered.extend(render_s04(out, db, representative_index))
        rendered.extend(render_t01(out, db))
        rendered.extend(render_t02(out, db, selected_by_producer))
        rendered.extend(render_t03(out))

        gate("rendered_file_count_exact", len(rendered) == len(FIGURE_VARIANTS) * 2, len(rendered))
        gate("all_rendered_files_nonempty", all(int(r["bytes"]) > 0 for r in rendered))

        failed_stage = "visual_contract_and_closeout"
        rendered_by_stem: dict[str, list[dict[str, Any]]] = {}
        for row in rendered:
            stem = Path(row["file"]).stem
            rendered_by_stem.setdefault(stem, []).append(row)

        authority_by_figure = {
            "S01": "READ_ONLY_DIAGNOSTIC_RECONSTRUCTION: frozen terminal flow + exact SG5 Pollock",
            "S02": "READ_ONLY_DIAGNOSTIC_RECONSTRUCTION: frozen terminal flow + exact SG5 Pollock",
            "S03": "READ_ONLY_DIAGNOSTIC_RECONSTRUCTION: frozen terminal flow + exact SG5 Pollock + SG6 terminal TOF",
            "S04": "DERIVED_FROM_DIAGNOSTIC: representative SG5 Pollock streamline resampled on SG6 xi grid",
            "T01": "READ_ONLY_DIAGNOSTIC_RECONSTRUCTION: SG6 flux-weighted terminal TOF",
            "T02": "DERIVED_FROM_DIAGNOSTIC: SG6 representative producer streamline path length vs TOF",
            "T03": "SCHEMATIC_FROM_FROZEN_CONTRACT: SG6 xi = tau / tau_end with 201 common nodes",
        }

        figure_index: list[dict[str, Any]] = []
        for fid, variant, stem in FIGURE_VARIANTS:
            figure_index.append({
                "figure_id": fid,
                "variant": variant,
                "title_or_stem": stem,
                "authority": authority_by_figure[fid],
                "source_cache_sha256": cache_sha,
                "state_time_days": "contract" if fid == "T03" else TERMINAL_DAY,
                "release_id": RELEASE_ID,
                "z_positive_downward": True,
                "layer_1_shallowest": True,
                "layer_15_deepest": True,
                "files": ";".join(sorted(row["file"] for row in rendered_by_stem[stem])),
            })

        captions = [
            {"figure_id": "S01", "caption": "Full producer-captured 3D Pollock streamline field reconstructed read-only from the frozen V16 terminal 1000-day flow state using the exact SG5 analytical cell-exit tracer. Depth is displayed positive downward; vertical exaggeration is display only."},
            {"figure_id": "S02", "caption": "The same terminal Pollock streamline field grouped by the four five-spot producers, preserving the exact reconstructed trajectories and streamline flow weights."},
            {"figure_id": "S03", "caption": "Terminal Pollock streamlines colored by SG6 terminal physical time-of-flight. SG5 tracks pore velocity, so cumulative Pollock particle time is the physical streamline TOF used by SG6."},
            {"figure_id": "S04", "caption": "Anatomy of the flux-weighted-median representative streamline. Markers show selected normalized transport coordinates xi and their cumulative physical TOF along the frozen SG6 resampled trajectory."},
            {"figure_id": "T01", "caption": "Flux-weighted reservoir distribution of terminal streamline time-of-flight at the frozen 1000-day V16 flow state."},
            {"figure_id": "T02", "caption": "Cumulative geometric distance versus cumulative physical time-of-flight for one flux-weighted-median representative streamline captured by each producer."},
            {"figure_id": "T03", "caption": "SG6 transport-coordinate contract: xi equals tau divided by terminal tau, spanning 0 at the injector-side origin to 1 at the producer-side terminus on a common 201-node grid. This is a schematic of the frozen coordinate definition, not a transport solve."},
        ]

        stats = sg6.calculate_statistics(db)
        diagnostic_contract = {
            "release_id": RELEASE_ID,
            "milestone": MILESTONE,
            "terminal_day": TERMINAL_DAY,
            "source_visual_cache_sha256": cache_sha,
            "pollock_module": SG5_RUNNER,
            "tof_module": SG6_RUNNER,
            "repair_parent_runner": B3_FAILED_RUNNER,
            "repair_parent_git_blob": B3_FAILED_GIT_BLOB,
            "repair_defect": "raw SG5 dictionaries were passed directly to SG6 without the frozen V16 interface adapter",
            "sg5_to_sg6_adapter_module": R3R4R1_RUNNER,
            "sg5_to_sg6_adapter_function": "convert_sg5_to_sg6_streamlines",
            "face_subdivisions": int(sg5.FACE_SUBDIVISIONS),
            "outgoing_injector_faces": len(faces),
            "seed_count": len(seeds),
            "producer_captured_streamlines": len(captured),
            "capture_fraction": capture_fraction,
            "common_xi_nodes": len(db["xi"]),
            "terminal_tof_min_days": float(np.min(tau_end_days)),
            "terminal_tof_max_days": float(np.max(tau_end_days)),
            "terminal_tof_flux_weighted_mean_days": float(stats["global"]["tof_flux_weighted_mean_days"]),
            "terminal_flow_local_relative_l2_error": conservation["local_relative_l2_error"],
            "terminal_flow_global_relative_mismatch": conservation["global_relative_mismatch"],
            "representative_streamline_index": representative_index,
            "representative_streamline_producer": str(labels[representative_index]),
            "producer_representative_indices": selected_by_producer,
            "display_vertical_axis": "Depth below reservoir top, ft (+z downward)",
            "accepted_state_mutation": False,
            "physical_time_advance": False,
            "accepted_step_advance": False,
            "transport_update": False,
            "ledger_update": False,
            "parameter_change": False,
            "calibration": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "release_id": RELEASE_ID,
            "simulation_executed": False,
            "accepted_state_mutation": False,
            "source_visual_cache_sha256": cache_sha,
            "figure_families_completed": ["S01", "S02", "S03", "S04", "T01", "T02", "T03"],
            "rendered_variants": len(FIGURE_VARIANTS),
            "rendered_files_png_pdf": len(rendered),
            "terminal_day": TERMINAL_DAY,
            "outgoing_injector_faces": len(faces),
            "streamline_seed_count": len(seeds),
            "producer_captured_streamlines": len(captured),
            "streamline_capture_fraction": capture_fraction,
            "common_xi_nodes": len(db["xi"]),
            "terminal_tof_min_days": float(np.min(tau_end_days)),
            "terminal_tof_max_days": float(np.max(tau_end_days)),
            "terminal_tof_flux_weighted_mean_days": float(stats["global"]["tof_flux_weighted_mean_days"]),
            "terminal_path_length_mean_ft": float(stats["global"]["path_length_mean_ft"]),
            "z_positive_downward": True,
            "layer_1_shallowest": True,
            "layer_15_deepest": True,
            "next": NEXT,
        }

        closure = {
            "milestone": MILESTONE,
            "status": STATUS,
            "all_gates_passed": all(item["passed"] for item in gates.values()),
            "gate_count": len(gates),
            "S01_complete": True,
            "S02_complete": True,
            "S03_complete": True,
            "S04_complete": True,
            "T01_complete": True,
            "T02_complete": True,
            "T03_complete": True,
            "exact_SG5_Pollock_reconstruction": True,
            "SG6_TOF_transport_coordinates_validated": True,
            "full_streamline_weight_capture": True,
            "SG5_to_SG6_interface_repaired": True,
            "diagnostic_reconstruction_read_only": True,
            "accepted_simulation_state_modified": False,
            "phase_B4_authorized": True,
            "next": NEXT,
        }

        immutable_publish(out, {
            "V16VIS_B3R1_Figure_Index.csv": csv_bytes(figure_index),
            "V16VIS_B3R1_Figure_Captions.csv": csv_bytes(captions),
            "V16VIS_B3R1_Streamline_TOF_Diagnostic_Contract.json": json_bytes(diagnostic_contract),
            "PAD_Stream_V16VIS_B3R1_Summary.json": json_bytes(summary),
            "V16VIS_B3R1_Final_Gate_Matrix.csv": csv_bytes([{"gate": key, **value} for key, value in gates.items()]),
            "V16VIS_B3R1_Final_Closure.json": json_bytes(closure),
        })

        artifact_manifest = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "V16VIS_B3R1_Artifact_Manifest.csv":
                artifact_manifest.append({"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size})
        immutable_publish(out, {"V16VIS_B3R1_Artifact_Manifest.csv": csv_bytes(artifact_manifest)})

        print("\n" + "=" * 164)
        print("PAD-Stream V16VIS-B3R1: PASS")
        print("=" * 164)
        print(f"{'Status':72}: {STATUS}")
        print(f"{'Release ID':72}: {RELEASE_ID}")
        print(f"{'A1 visual cache SHA':72}: {cache_sha}")
        print(f"{'Figure families completed':72}: S01, S02, S03, S04, T01, T02, T03")
        print(f"{'Rendered variants':72}: {len(FIGURE_VARIANTS)}")
        print(f"{'Rendered PNG/PDF files':72}: {len(rendered)}")
        print(f"{'Outgoing injector-region faces':72}: {len(faces)}")
        print(f"{'Streamline seeds / reconstructed':72}: {len(seeds)} / {len(streamlines)}")
        print(f"{'Producer-captured streamlines':72}: {len(captured)}")
        print(f"{'Captured streamline weight fraction':72}: {capture_fraction:.12f}")
        print(f"{'Common SG6 xi nodes':72}: {len(db['xi'])}")
        print(f"{'Terminal TOF range':72}: {np.min(tau_end_days):.6f} to {np.max(tau_end_days):.6f} days")
        print(f"{'Flux-weighted mean terminal TOF':72}: {stats['global']['tof_flux_weighted_mean_days']:.6f} days")
        print(f"{'Mean terminal path length':72}: {stats['global']['path_length_mean_ft']:.6f} ft")
        print(f"{'Terminal flow local conservation rel L2':72}: {conservation['local_relative_l2_error']:.12e}")
        print(f"{'Terminal flow global conservation mismatch':72}: {conservation['global_relative_mismatch']:.12e}")
        print(f"{'Vertical display convention':72}: +z downward / increasing depth")
        print(f"{'Accepted simulation state modified':72}: False")
        print(f"{'Phase B4 authorized':72}: True")
        print(f"{'Next':72}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "FROZEN_V16_POLLOCK_STREAMLINE_AND_TOF_VISUALS_BLOCKED_R1",
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        data = json_bytes(report)
        p = blocked / "V16VIS_B3R1_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / ("V16VIS_B3R1_Blocked_Report_" + hashlib.sha256(data).hexdigest()[:12] + ".json")
        p.write_bytes(data)
        print("\n" + "=" * 164)
        print("PAD-Stream V16VIS-B3R1: BLOCKED")
        print("=" * 164)
        print("Report      :", p)
        print("Failed stage:", failed_stage)
        print("Exception   :", repr(exc))
        return 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
