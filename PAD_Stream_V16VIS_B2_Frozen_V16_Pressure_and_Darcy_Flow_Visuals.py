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


MILESTONE = "V16VIS-B2"
STATUS = "FROZEN_V16_PRESSURE_AND_DARCY_FLOW_VISUALS_VALIDATED"
NEXT = "V16VIS-B3 - Frozen V16 Pollock Streamline and Time-of-Flight Visuals"

RELEASE_ID = "PAD-STREAM-V16-RC1-B92D52088D01078A"
RELEASE_PATH_ID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

A1_RUNNER = "PAD_Stream_V16VIS_A1_Visual_Authority_Manifest_and_Data_Extraction.py"
A1_GIT_BLOB = "7ed31f0e69b63489f25a1833cdc3693f735b1233"
B1_RUNNER = "PAD_Stream_V16VIS_B1_Frozen_SGSim_Geology_and_Reservoir_Geometry_Visuals.py"
B1_GIT_BLOB = "5d8c785e189683c9b46f85b51a94297016c21af5"
SG2_RUNNER = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_GIT_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3_RUNNER = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_GIT_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
SG4_RUNNER = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_GIT_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"
R3R2R1_RUNNER = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_GIT_BLOB = "740c6da03e73906646bf0153633187e749449f31"

EXPECTED_A1_STATUS = "V16_VISUAL_AUTHORITY_MANIFEST_AND_DATA_EXTRACTION_VALIDATED"
EXPECTED_B1_STATUS = "FROZEN_SGSIM_GEOLOGY_AND_RESERVOIR_GEOMETRY_VISUALS_VALIDATED"
EXPECTED_A1_CACHE_SHA256 = "2acbbbc8608eb771d1a6ea6909c7d37caec2ee77666a7828226e3a9e531d316e"
TERMINAL_DAY = 1000.0

A1_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_A_Authority_and_Data_Extraction"
B1_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_B1_Geology_and_Reservoir_Geometry"
OUT_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_B2_Pressure_and_Darcy_Flow"
BLOCKED_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_B2_BLOCKED"

A1_CACHE = "V16VIS_A1_Authoritative_Visual_Data.npz"
A1_SUMMARY = "PAD_Stream_V16VIS_A1_Summary.json"
A1_CLOSURE = "V16VIS_A1_Final_Closure.json"
A1_COORD = "V16VIS_A1_Coordinate_Convention.json"
A1_MANIFEST = "V16VIS_A1_Artifact_Manifest.csv"

B1_SUMMARY = "PAD_Stream_V16VIS_B1_Summary.json"
B1_CLOSURE = "V16VIS_B1_Final_Closure.json"
B1_MANIFEST = "V16VIS_B1_Artifact_Manifest.csv"

GRID_SHAPE = (15, 50, 50)
NX, NY, NZ = 50, 50, 15
DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0
LX_FT = 1000.0
LY_FT = 1000.0
LZ_FT = 60.0
LAYER = 8
K_LAYER = LAYER - 1

INJECTOR_I = 24
INJECTOR_J = 24
PRODUCERS = {
    "PROD_SW": {"i": 4, "j": 4},
    "PROD_SE": {"i": 45, "j": 4},
    "PROD_NW": {"i": 4, "j": 45},
    "PROD_NE": {"i": 45, "j": 45},
}
COMPLETION_TOP_DEPTH_FT = 20.0
COMPLETION_BASE_DEPTH_FT = 40.0

DPI = 300
FIGSIZE = (9.0, 7.0)
QUIVER_STEP = 4
DAY_TO_S = 86400.0
FT_TO_M = 0.3048

FIGURE_VARIANTS = [
    ("F01", "Layer08", "F01_Initial_Reference_Pressure_Layer08"),
    ("F02", "Layer08_1000d", "F02_Terminal_V16_Pressure_Layer08_1000d"),
    ("F03", "SW_INJ_NE", "F03_Terminal_Pressure_SW_Injector_NE_CrossSection"),
    ("F03", "SE_INJ_NW", "F03_Terminal_Pressure_SE_Injector_NW_CrossSection"),
    ("F04", "Layer08_1000d", "F04_Terminal_Darcy_Flux_Magnitude_Layer08_1000d"),
    ("F05", "Layer08_1000d", "F05_Terminal_Pressure_Darcy_Flow_Overlay_Layer08_1000d"),
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


def relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(np.linalg.norm((aa - bb).ravel()) / max(np.linalg.norm(bb.ravel()), 1.0e-30))


def cell_center_x_ft(i: int) -> float:
    return (i + 0.5) * DX_FT


def cell_center_y_ft(j: int) -> float:
    return (j + 0.5) * DY_FT


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


def overlay_wells_plan(ax: plt.Axes) -> None:
    ix = cell_center_x_ft(INJECTOR_I)
    iy = cell_center_y_ft(INJECTOR_J)
    ax.scatter([ix], [iy], marker="^", s=80, label="INJECTOR")
    ax.text(ix + 12.0, iy + 12.0, "INJ", fontsize=8)
    first = True
    for name, ij in PRODUCERS.items():
        x = cell_center_x_ft(ij["i"])
        y = cell_center_y_ft(ij["j"])
        ax.scatter([x], [y], marker="v", s=62, label="PRODUCERS" if first else None)
        ax.text(x + 12.0, y + 12.0, name.replace("PROD_", ""), fontsize=8)
        first = False


def render_pressure_map(
    out: Path,
    pressure_psi: np.ndarray,
    norm: Normalize,
    title: str,
    stem: str,
) -> list[dict[str, Any]]:
    fig, ax = plt.subplots(figsize=FIGSIZE)
    im = ax.imshow(
        pressure_psi[K_LAYER],
        origin="lower",
        extent=[0.0, LX_FT, 0.0, LY_FT],
        interpolation="nearest",
        aspect="equal",
        norm=norm,
    )
    overlay_wells_plan(ax)
    ax.set_title(title)
    ax.set_xlabel("X, ft")
    ax.set_ylabel("Y, ft")
    ax.set_xlim(0.0, LX_FT)
    ax.set_ylim(0.0, LY_FT)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Pressure, psi")
    ax.legend(loc="upper right")
    return save_figure(fig, out, stem)


def path_between(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    path: list[tuple[int, int]] = []
    for seg in range(len(points) - 1):
        i0, j0 = points[seg]
        i1, j1 = points[seg + 1]
        n = max(abs(i1 - i0), abs(j1 - j0)) + 1
        ii = np.rint(np.linspace(i0, i1, n)).astype(int)
        jj = np.rint(np.linspace(j0, j1, n)).astype(int)
        for i, j in zip(ii.tolist(), jj.tolist()):
            ij = (i, j)
            if not path or path[-1] != ij:
                path.append(ij)
    return path


def path_distances_ft(path: list[tuple[int, int]]) -> np.ndarray:
    d = np.zeros(len(path), dtype=np.float64)
    for n in range(1, len(path)):
        i0, j0 = path[n - 1]
        i1, j1 = path[n]
        dx = (i1 - i0) * DX_FT
        dy = (j1 - j0) * DY_FT
        d[n] = d[n - 1] + np.hypot(dx, dy)
    return d


def centers_to_edges(c: np.ndarray) -> np.ndarray:
    c = np.asarray(c, dtype=np.float64)
    if c.size < 2:
        raise GateError("cross_section_requires_multiple_centers")
    edges = np.empty(c.size + 1, dtype=np.float64)
    edges[1:-1] = 0.5 * (c[:-1] + c[1:])
    edges[0] = c[0] - 0.5 * (c[1] - c[0])
    edges[-1] = c[-1] + 0.5 * (c[-1] - c[-2])
    return edges


def render_cross_section(
    out: Path,
    pressure_psi: np.ndarray,
    depth_edges_ft: np.ndarray,
    norm: Normalize,
    points: list[tuple[int, int]],
    well_labels: list[tuple[str, tuple[int, int]]],
    title: str,
    stem: str,
) -> list[dict[str, Any]]:
    path = path_between(points)
    dist = path_distances_ft(path)
    dist_edges = centers_to_edges(dist)
    ii = np.asarray([p[0] for p in path], dtype=int)
    jj = np.asarray([p[1] for p in path], dtype=int)
    section = pressure_psi[:, jj, ii]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    mesh = ax.pcolormesh(
        dist_edges,
        depth_edges_ft,
        section,
        shading="flat",
        norm=norm,
    )
    for label, ij in well_labels:
        matches = [n for n, p in enumerate(path) if p == ij]
        if not matches:
            raise GateError(f"well_not_on_cross_section:{label}")
        x = float(dist[matches[0]])
        ax.plot([x, x], [COMPLETION_TOP_DEPTH_FT, COMPLETION_BASE_DEPTH_FT], linewidth=2.0)
        ax.text(x, COMPLETION_TOP_DEPTH_FT - 1.0, label, ha="center", va="bottom", fontsize=8)

    ax.set_title(title)
    ax.set_xlabel("Distance along well-to-well section, ft")
    ax.set_ylabel("Depth below reservoir top, ft (+z downward)")
    ax.set_ylim(LZ_FT, 0.0)
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_label("Pressure, psi")
    return save_figure(fig, out, stem)


def horizontal_darcy_flux_ft_day(
    qx: np.ndarray,
    qy: np.ndarray,
    sg3: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    vx_face = np.asarray(qx, dtype=np.float64) / float(sg3.AX_M2)
    vy_face = np.asarray(qy, dtype=np.float64) / float(sg3.AY_M2)

    vx = np.zeros((NY, NX), dtype=np.float64)
    vy = np.zeros((NY, NX), dtype=np.float64)

    vx[:, 0] = vx_face[K_LAYER, :, 0]
    vx[:, -1] = vx_face[K_LAYER, :, -1]
    vx[:, 1:-1] = 0.5 * (vx_face[K_LAYER, :, :-1] + vx_face[K_LAYER, :, 1:])

    vy[0, :] = vy_face[K_LAYER, 0, :]
    vy[-1, :] = vy_face[K_LAYER, -1, :]
    vy[1:-1, :] = 0.5 * (vy_face[K_LAYER, :-1, :] + vy_face[K_LAYER, 1:, :])

    convert = DAY_TO_S / FT_TO_M
    vx *= convert
    vy *= convert
    mag = np.sqrt(vx**2 + vy**2)
    return vx, vy, mag


def render_flux_magnitude(out: Path, mag_ft_day: np.ndarray) -> list[dict[str, Any]]:
    fig, ax = plt.subplots(figsize=FIGSIZE)
    im = ax.imshow(
        mag_ft_day,
        origin="lower",
        extent=[0.0, LX_FT, 0.0, LY_FT],
        interpolation="nearest",
        aspect="equal",
        vmin=0.0,
        vmax=float(np.max(mag_ft_day)),
    )
    overlay_wells_plan(ax)
    ax.set_title("F04 — Terminal Horizontal Darcy-Flux Magnitude, Layer 8 (1000 d)")
    ax.set_xlabel("X, ft")
    ax.set_ylabel("Y, ft")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Horizontal Darcy flux magnitude, ft/day")
    ax.legend(loc="upper right")
    return save_figure(fig, out, "F04_Terminal_Darcy_Flux_Magnitude_Layer08_1000d")


def render_pressure_flow_overlay(
    out: Path,
    pressure_psi: np.ndarray,
    norm: Normalize,
    x_center_ft: np.ndarray,
    y_center_ft: np.ndarray,
    vx_ft_day: np.ndarray,
    vy_ft_day: np.ndarray,
) -> list[dict[str, Any]]:
    fig, ax = plt.subplots(figsize=FIGSIZE)
    im = ax.imshow(
        pressure_psi[K_LAYER],
        origin="lower",
        extent=[0.0, LX_FT, 0.0, LY_FT],
        interpolation="nearest",
        aspect="equal",
        norm=norm,
    )

    sl = slice(0, None, QUIVER_STEP)
    xx, yy = np.meshgrid(x_center_ft[sl], y_center_ft[sl], indexing="xy")
    u = vx_ft_day[sl, sl]
    v = vy_ft_day[sl, sl]
    qmag = np.sqrt(u**2 + v**2)
    qmax = float(np.max(qmag))
    scale = qmax / (2.5 * DX_FT) if qmax > 0.0 else 1.0
    quiv = ax.quiver(
        xx,
        yy,
        u,
        v,
        angles="xy",
        scale_units="xy",
        scale=scale,
        pivot="mid",
        width=0.003,
    )
    if qmax > 0.0:
        qref = float(np.percentile(qmag[qmag > 0.0], 90.0))
        ax.quiverkey(quiv, 0.84, 1.03, qref, f"{qref:.2g} ft/day", labelpos="E", coordinates="axes")

    overlay_wells_plan(ax)
    ax.set_title("F05 — Terminal Pressure + Horizontal Darcy-Flow Overlay, Layer 8 (1000 d)")
    ax.set_xlabel("X, ft")
    ax.set_ylabel("Y, ft")
    ax.set_xlim(0.0, LX_FT)
    ax.set_ylim(0.0, LY_FT)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Pressure, psi")
    ax.legend(loc="upper right")
    return save_figure(fig, out, "F05_Terminal_Pressure_Darcy_Flow_Overlay_Layer08_1000d")


def self_test() -> None:
    if RELEASE_ID != "PAD-STREAM-V16-RC1-B92D52088D01078A":
        raise RuntimeError("release_identity")
    if GRID_SHAPE != (15, 50, 50):
        raise RuntimeError("grid_identity")
    if LAYER != 8 or K_LAYER != 7:
        raise RuntimeError("layer_identity")
    if len(FIGURE_VARIANTS) != 6:
        raise RuntimeError("figure_variant_count")
    p1 = path_between([(4, 4), (24, 24), (45, 45)])
    p2 = path_between([(45, 4), (24, 24), (4, 45)])
    for pt in [(4, 4), (24, 24), (45, 45)]:
        if pt not in p1:
            raise RuntimeError("primary_cross_section_path")
    for pt in [(45, 4), (24, 24), (4, 45)]:
        if pt not in p2:
            raise RuntimeError("secondary_cross_section_path")
    if COMPLETION_TOP_DEPTH_FT != 20.0 or COMPLETION_BASE_DEPTH_FT != 40.0:
        raise RuntimeError("completion_depth")
    test_qx = np.ones((NZ, NY, NX - 1), dtype=np.float64)
    test_qy = np.ones((NZ, NY - 1, NX), dtype=np.float64)
    class _SG3:
        AX_M2 = 1.0
        AY_M2 = 1.0
    vx, vy, mag = horizontal_darcy_flux_ft_day(test_qx, test_qy, _SG3)
    if vx.shape != (NY, NX) or vy.shape != (NY, NX) or mag.shape != (NY, NX):
        raise RuntimeError("flux_center_shape")
    print("PAD-Stream V16VIS-B2 pressure / Darcy-flow visual self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    a1 = drive / A1_REL
    b1 = drive / B1_REL
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
        print("PAD-Stream V16VIS-B2 — Frozen V16 Pressure and Darcy-Flow Visuals")
        print("=" * 164)
        print("Release                    :", RELEASE_ID)
        print("Simulation                  : none")
        print("Accepted-state mutation     : none")
        print("Pressure authority          : A1 direct frozen flow state at 1000 d")
        print("Diagnostic reconstruction   : frozen SG2/SG3/R3R2R1/SG4 modules only")
        print("Display convention          : +z downward / increasing depth")

        failed_stage = "source_binding"
        bindings = [
            ("A1", A1_RUNNER, A1_GIT_BLOB),
            ("B1", B1_RUNNER, B1_GIT_BLOB),
            ("SG2", SG2_RUNNER, SG2_GIT_BLOB),
            ("SG3", SG3_RUNNER, SG3_GIT_BLOB),
            ("SG4", SG4_RUNNER, SG4_GIT_BLOB),
            ("R3R2R1", R3R2R1_RUNNER, R3R2R1_GIT_BLOB),
        ]
        for role, filename, expected in bindings:
            p = root / filename
            gate(f"{role}_exists", p.is_file(), p)
            actual = git_blob_sha(p, root)
            gate(f"{role}_git_blob_exact", actual == expected, actual)

        failed_stage = "phase_prerequisite_binding"
        for name in [A1_CACHE, A1_SUMMARY, A1_CLOSURE, A1_COORD, A1_MANIFEST]:
            gate(f"A1_exists_{name}", (a1 / name).is_file(), a1 / name)
        for name in [B1_SUMMARY, B1_CLOSURE, B1_MANIFEST]:
            gate(f"B1_exists_{name}", (b1 / name).is_file(), b1 / name)

        a1_summary = load_json(a1 / A1_SUMMARY)
        a1_closure = load_json(a1 / A1_CLOSURE)
        coord = load_json(a1 / A1_COORD)
        b1_summary = load_json(b1 / B1_SUMMARY)
        b1_closure = load_json(b1 / B1_CLOSURE)

        gate("A1_status_exact", a1_summary.get("status") == EXPECTED_A1_STATUS, a1_summary.get("status"))
        gate("A1_release_exact", a1_summary.get("release_id") == RELEASE_ID, a1_summary.get("release_id"))
        gate("A1_closure_passed", a1_closure.get("all_gates_passed") is True)
        gate("B1_status_exact", b1_summary.get("status") == EXPECTED_B1_STATUS, b1_summary.get("status"))
        gate("B1_release_exact", b1_summary.get("release_id") == RELEASE_ID, b1_summary.get("release_id"))
        gate("B1_closure_passed", b1_closure.get("all_gates_passed") is True)
        gate("B1_phase_B2_authorized", b1_closure.get("phase_B2_authorized") is True)
        gate("coordinate_downward", coord["display_axes"]["positive_z_direction"] == "DOWNWARD_DEPTH", coord["display_axes"]["positive_z_direction"])
        gate("layer_order_exact", coord["layer_order"]["layer_1"] == "SHALLOWEST" and coord["layer_order"]["layer_15"] == "DEEPEST", coord["layer_order"])

        cache_path = a1 / A1_CACHE
        cache_sha = sha256_file(cache_path)
        gate("A1_cache_SHA_exact", cache_sha == EXPECTED_A1_CACHE_SHA256, cache_sha)
        gate("A1_summary_cache_SHA_exact", a1_summary.get("visual_cache_sha256") == cache_sha, a1_summary.get("visual_cache_sha256"))

        failed_stage = "authoritative_cache_extraction"
        with np.load(cache_path, allow_pickle=False) as z:
            perm_md = np.asarray(z["permeability_md"], dtype=np.float64)
            x_center_ft = np.asarray(z["x_center_ft"], dtype=np.float64)
            y_center_ft = np.asarray(z["y_center_ft"], dtype=np.float64)
            depth_center_ft = np.asarray(z["depth_center_ft"], dtype=np.float64)
            depth_edges_ft = np.asarray(z["depth_edges_ft"], dtype=np.float64)
            flow_days = np.asarray(z["flow_days"], dtype=np.float64)
            flow_saturation = np.asarray(z["flow_saturation"], dtype=np.float64)
            flow_pressure = np.asarray(z["flow_pressure_psi"], dtype=np.float64)

        gate("perm_shape_exact", perm_md.shape == GRID_SHAPE, perm_md.shape)
        gate("flow_pressure_shape_exact", flow_pressure.ndim == 4 and flow_pressure.shape[1:] == GRID_SHAPE, flow_pressure.shape)
        gate("flow_saturation_shape_exact", flow_saturation.shape == flow_pressure.shape, flow_saturation.shape)
        gate("terminal_day_exact", float(flow_days[-1]) == TERMINAL_DAY, float(flow_days[-1]))
        gate("terminal_pressure_finite", bool(np.all(np.isfinite(flow_pressure[-1]))))
        gate("terminal_saturation_finite", bool(np.all(np.isfinite(flow_saturation[-1]))))
        gate("display_depth_centers", depth_center_ft[0] == 2.0 and depth_center_ft[-1] == 58.0 and np.all(np.diff(depth_center_ft) > 0.0), (depth_center_ft[0], depth_center_ft[-1]))
        gate("display_depth_edges", depth_edges_ft[0] == 0.0 and depth_edges_ft[-1] == 60.0, (depth_edges_ft[0], depth_edges_ft[-1]))

        terminal_pressure = flow_pressure[-1].copy()
        terminal_sat = flow_saturation[-1].copy()

        failed_stage = "read_only_diagnostic_flow_reconstruction"
        sg2 = load_module(root / SG2_RUNNER, "v16vis_b2_sg2")
        sg3 = load_module(root / SG3_RUNNER, "v16vis_b2_sg3")
        sg4 = load_module(root / SG4_RUNNER, "v16vis_b2_sg4")
        r3 = load_module(root / R3R2R1_RUNNER, "v16vis_b2_r3r2r1")

        kx, ky, kz = sg2.build_directional_permeability(perm_md)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)

        A0, b0, _producer_wi0 = sg3.assemble_pressure_system(perm_md, tx_ref, ty_ref, tz_ref)
        _p0_pa, initial_pressure = sg3.solve_pressure(A0, b0)
        gate("initial_pressure_shape_exact", initial_pressure.shape == GRID_SHAPE, initial_pressure.shape)
        gate("initial_pressure_finite", bool(np.all(np.isfinite(initial_pressure))))

        mobility = r3.phase_mobility_fields(terminal_sat)
        tx, ty, tz, _face_mobility = r3.build_updated_transmissibilities(
            sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
        )
        qx, qy, qz = sg4.compute_face_fluxes(terminal_pressure, tx, ty, tz)
        gate("Qx_shape_exact", qx.shape == (15, 50, 49), qx.shape)
        gate("Qy_shape_exact", qy.shape == (15, 49, 50), qy.shape)
        gate("Qz_shape_exact", qz.shape == (14, 50, 50), qz.shape)
        gate("terminal_face_flux_finite", bool(np.all(np.isfinite(qx)) and np.all(np.isfinite(qy)) and np.all(np.isfinite(qz))))

        A1flow, b1flow, producer_wi = r3.assemble_updated_pressure_system(
            sg3, perm_md, tx, ty, tz, mobility["lambda_total"]
        )
        _pdiag_pa, pdiag, pdiag_residual = r3.solve_updated_pressure(sg3, A1flow, b1flow)
        pdiag_rel = relative_l2(pdiag, terminal_pressure)
        gate("diagnostic_pressure_linear_residual", pdiag_residual < 1.0e-8, pdiag_residual)
        gate("terminal_pressure_reconstruction_consistent", pdiag_rel < 1.0e-9, pdiag_rel)

        _rates, producer_sink = r3.producer_rates_updated(sg3, terminal_pressure, producer_wi)
        conservation = r3.flow_conservation_metrics(sg3, sg4, qx, qy, qz, producer_sink)
        gate("terminal_flow_local_conservation", conservation["local_relative_l2_error"] < 1.0e-8, conservation["local_relative_l2_error"])
        gate("terminal_flow_global_conservation", conservation["global_relative_mismatch"] < 1.0e-8, conservation["global_relative_mismatch"])

        vx_ft_day, vy_ft_day, flux_mag_ft_day = horizontal_darcy_flux_ft_day(qx, qy, sg3)
        gate("horizontal_flux_finite", bool(np.all(np.isfinite(flux_mag_ft_day))))
        gate("horizontal_flux_positive_max", float(np.max(flux_mag_ft_day)) > 0.0, float(np.max(flux_mag_ft_day)))

        failed_stage = "figure_rendering"
        if out.exists() and any(out.iterdir()):
            raise GateError("B2_output_directory_not_empty:refusing_to_overwrite_existing_visual_release")
        out.mkdir(parents=True, exist_ok=True)

        pressure_min = float(min(np.min(initial_pressure), np.min(terminal_pressure)))
        pressure_max = float(max(np.max(initial_pressure), np.max(terminal_pressure)))
        pressure_norm = Normalize(vmin=pressure_min, vmax=pressure_max)

        rendered: list[dict[str, Any]] = []
        rendered.extend(render_pressure_map(
            out,
            initial_pressure,
            pressure_norm,
            "F01 — Initial/Reference Pressure Field, Layer 8",
            "F01_Initial_Reference_Pressure_Layer08",
        ))
        rendered.extend(render_pressure_map(
            out,
            terminal_pressure,
            pressure_norm,
            "F02 — Terminal Frozen V16 Pressure Field, Layer 8 (1000 d)",
            "F02_Terminal_V16_Pressure_Layer08_1000d",
        ))
        rendered.extend(render_cross_section(
            out,
            terminal_pressure,
            depth_edges_ft,
            pressure_norm,
            [(4, 4), (24, 24), (45, 45)],
            [("PROD_SW", (4, 4)), ("INJECTOR", (24, 24)), ("PROD_NE", (45, 45))],
            "F03 — Terminal Pressure Cross-Section: PROD_SW → Injector → PROD_NE (1000 d)",
            "F03_Terminal_Pressure_SW_Injector_NE_CrossSection",
        ))
        rendered.extend(render_cross_section(
            out,
            terminal_pressure,
            depth_edges_ft,
            pressure_norm,
            [(45, 4), (24, 24), (4, 45)],
            [("PROD_SE", (45, 4)), ("INJECTOR", (24, 24)), ("PROD_NW", (4, 45))],
            "F03 — Terminal Pressure Cross-Section: PROD_SE → Injector → PROD_NW (1000 d)",
            "F03_Terminal_Pressure_SE_Injector_NW_CrossSection",
        ))
        rendered.extend(render_flux_magnitude(out, flux_mag_ft_day))
        rendered.extend(render_pressure_flow_overlay(
            out,
            terminal_pressure,
            pressure_norm,
            x_center_ft,
            y_center_ft,
            vx_ft_day,
            vy_ft_day,
        ))

        gate("rendered_file_count_exact", len(rendered) == len(FIGURE_VARIANTS) * 2, len(rendered))
        gate("all_rendered_files_nonempty", all(int(r["bytes"]) > 0 for r in rendered))

        failed_stage = "visual_contract_and_closeout"
        rendered_by_stem: dict[str, list[dict[str, Any]]] = {}
        for row in rendered:
            stem = Path(row["file"]).stem
            rendered_by_stem.setdefault(stem, []).append(row)

        authority_by_figure = {
            "F01": "READ_ONLY_DIAGNOSTIC_RECONSTRUCTION: frozen SG2+SG3+PERM",
            "F02": "DIRECT_FROZEN_RUNTIME_FIELD: A1 terminal accepted_pressure_psi at 1000 d",
            "F03": "DERIVED_FROM_DIRECT: A1 terminal accepted_pressure_psi at 1000 d",
            "F04": "READ_ONLY_DIAGNOSTIC_RECONSTRUCTION: terminal A1 state + frozen R3R2R1 mobility + SG4 flux",
            "F05": "READ_ONLY_DIAGNOSTIC_RECONSTRUCTION: terminal A1 pressure + reconstructed terminal Darcy flux",
        }

        figure_index: list[dict[str, Any]] = []
        for fid, variant, stem in FIGURE_VARIANTS:
            figure_index.append({
                "figure_id": fid,
                "variant": variant,
                "title_or_stem": stem,
                "authority": authority_by_figure[fid],
                "source_cache_sha256": cache_sha,
                "state_time_days": "initial" if fid == "F01" else TERMINAL_DAY,
                "release_id": RELEASE_ID,
                "z_positive_downward": True,
                "layer_1_shallowest": True,
                "layer_15_deepest": True,
                "files": ";".join(sorted(row["file"] for row in rendered_by_stem[stem])),
            })

        captions = [
            {"figure_id": "F01", "caption": "Initial/reference five-spot pressure reconstructed read-only from the exact frozen SG2/SG3 geology, transmissibility, well-control, and gravity formulation. Layer 8 is shown with the injector and four producers."},
            {"figure_id": "F02", "caption": "Authoritative frozen V16 post-refresh pressure field at 1000 days from the A1 visual cache, shown on Layer 8 using the same pressure normalization as F01."},
            {"figure_id": "F03", "caption": "Two terminal 1000-day pressure cross-sections follow exact grid-cell paths through the five-spot wells: PROD_SW–Injector–PROD_NE and PROD_SE–Injector–PROD_NW. Completion intervals are shown from 20 to 40 ft below reservoir top; depth increases downward."},
            {"figure_id": "F04", "caption": "Terminal Layer-8 horizontal Darcy-flux magnitude reconstructed from the frozen 1000-day pressure/saturation state using the exact V16 total-mobility update and SG4 conservative face-flux equations. Face volumetric rates are divided by face area and converted to ft/day for display."},
            {"figure_id": "F05", "caption": "Terminal 1000-day Layer-8 pressure field overlaid with reconstructed horizontal Darcy-flow vectors. Pressure is direct frozen runtime authority; arrows are read-only diagnostics from the same frozen flow epoch."},
        ]

        diagnostic_contract = {
            "release_id": RELEASE_ID,
            "milestone": MILESTONE,
            "terminal_day": TERMINAL_DAY,
            "source_visual_cache_sha256": cache_sha,
            "figure_authority": authority_by_figure,
            "pressure_color_normalization": {
                "type": "shared_linear",
                "vmin_psi": pressure_min,
                "vmax_psi": pressure_max,
                "shared_across": ["F01", "F02", "F03"],
            },
            "terminal_flow_reconstruction": {
                "saturation_source": "A1 flow_saturation[-1] at 1000 d",
                "pressure_source": "A1 flow_pressure_psi[-1] at 1000 d",
                "mobility_module": R3R2R1_RUNNER,
                "flux_module": SG4_RUNNER,
                "local_relative_l2_error": conservation["local_relative_l2_error"],
                "global_relative_mismatch": conservation["global_relative_mismatch"],
                "diagnostic_pressure_relative_l2_vs_direct": pdiag_rel,
                "diagnostic_pressure_linear_residual": pdiag_residual,
            },
            "display_vertical_axis": "Depth below reservoir top, ft (+z downward)",
            "layer_1": "shallowest",
            "layer_15": "deepest",
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
            "figure_families_completed": ["F01", "F02", "F03", "F04", "F05"],
            "rendered_variants": len(FIGURE_VARIANTS),
            "rendered_files_png_pdf": len(rendered),
            "initial_pressure_min_psi": float(np.min(initial_pressure)),
            "initial_pressure_max_psi": float(np.max(initial_pressure)),
            "terminal_pressure_day": TERMINAL_DAY,
            "terminal_pressure_min_psi": float(np.min(terminal_pressure)),
            "terminal_pressure_max_psi": float(np.max(terminal_pressure)),
            "terminal_horizontal_flux_max_ft_day_layer8": float(np.max(flux_mag_ft_day)),
            "terminal_flow_local_relative_l2_error": conservation["local_relative_l2_error"],
            "terminal_flow_global_relative_mismatch": conservation["global_relative_mismatch"],
            "terminal_pressure_diagnostic_relative_l2": pdiag_rel,
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
            "F01_complete": True,
            "F02_complete": True,
            "F03_complete": True,
            "F04_complete": True,
            "F05_complete": True,
            "direct_terminal_pressure_preserved": True,
            "diagnostic_reconstruction_read_only": True,
            "terminal_flow_conservative": True,
            "accepted_simulation_state_modified": False,
            "phase_B3_authorized": True,
            "next": NEXT,
        }

        immutable_publish(out, {
            "V16VIS_B2_Figure_Index.csv": csv_bytes(figure_index),
            "V16VIS_B2_Figure_Captions.csv": csv_bytes(captions),
            "V16VIS_B2_Diagnostic_Reconstruction_Contract.json": json_bytes(diagnostic_contract),
            "PAD_Stream_V16VIS_B2_Summary.json": json_bytes(summary),
            "V16VIS_B2_Final_Gate_Matrix.csv": csv_bytes([{"gate": key, **value} for key, value in gates.items()]),
            "V16VIS_B2_Final_Closure.json": json_bytes(closure),
        })

        artifact_manifest = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "V16VIS_B2_Artifact_Manifest.csv":
                artifact_manifest.append({"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size})
        immutable_publish(out, {"V16VIS_B2_Artifact_Manifest.csv": csv_bytes(artifact_manifest)})

        print("\n" + "=" * 164)
        print("PAD-Stream V16VIS-B2: PASS")
        print("=" * 164)
        print(f"{'Status':72}: {STATUS}")
        print(f"{'Release ID':72}: {RELEASE_ID}")
        print(f"{'A1 visual cache SHA':72}: {cache_sha}")
        print(f"{'Figure families completed':72}: F01, F02, F03, F04, F05")
        print(f"{'Rendered variants':72}: {len(FIGURE_VARIANTS)}")
        print(f"{'Rendered PNG/PDF files':72}: {len(rendered)}")
        print(f"{'Initial/reference pressure range':72}: {np.min(initial_pressure):.6f} to {np.max(initial_pressure):.6f} psi")
        print(f"{'Terminal pressure day':72}: {TERMINAL_DAY:.1f} d")
        print(f"{'Terminal pressure range':72}: {np.min(terminal_pressure):.6f} to {np.max(terminal_pressure):.6f} psi")
        print(f"{'Terminal Layer-8 horizontal Darcy flux max':72}: {np.max(flux_mag_ft_day):.12g} ft/day")
        print(f"{'Terminal flow local conservation rel L2':72}: {conservation['local_relative_l2_error']:.12e}")
        print(f"{'Terminal flow global conservation mismatch':72}: {conservation['global_relative_mismatch']:.12e}")
        print(f"{'Diagnostic pressure rel L2 vs direct':72}: {pdiag_rel:.12e}")
        print(f"{'Vertical display convention':72}: +z downward / increasing depth")
        print(f"{'Accepted simulation state modified':72}: False")
        print(f"{'Phase B3 authorized':72}: True")
        print(f"{'Next':72}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "FROZEN_V16_PRESSURE_AND_DARCY_FLOW_VISUALS_BLOCKED",
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        data = json_bytes(report)
        p = blocked / "V16VIS_B2_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / ("V16VIS_B2_Blocked_Report_" + hashlib.sha256(data).hexdigest()[:12] + ".json")
        p.write_bytes(data)
        print("\n" + "=" * 164)
        print("PAD-Stream V16VIS-B2: BLOCKED")
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
