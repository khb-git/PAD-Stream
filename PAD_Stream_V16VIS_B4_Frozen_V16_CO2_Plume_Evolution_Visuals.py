from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
import subprocess
from typing import Any

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize


MILESTONE = "V16VIS-B4"
STATUS = "FROZEN_V16_CO2_PLUME_EVOLUTION_VISUALS_VALIDATED"
NEXT = "V16VIS-B5 - Frozen V16 Runtime and Mass-Balance Visuals"

RELEASE_ID = "PAD-STREAM-V16-RC1-B92D52088D01078A"
RELEASE_PATH_ID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

A1_RUNNER = "PAD_Stream_V16VIS_A1_Visual_Authority_Manifest_and_Data_Extraction.py"
A1_GIT_BLOB = "7ed31f0e69b63489f25a1833cdc3693f735b1233"
B3R1_RUNNER = "PAD_Stream_V16VIS_B3R1_SG5_to_SG6_Interface_Repair.py"
B3R1_GIT_BLOB = "4bd5675efd0fba4e67634a5f5aab881a4118a52b"

EXPECTED_A1_STATUS = "V16_VISUAL_AUTHORITY_MANIFEST_AND_DATA_EXTRACTION_VALIDATED"
EXPECTED_B3R1_STATUS = "FROZEN_V16_POLLOCK_STREAMLINE_AND_TOF_VISUALS_VALIDATED_R1"
EXPECTED_A1_CACHE_SHA256 = "2acbbbc8608eb771d1a6ea6909c7d37caec2ee77666a7828226e3a9e531d316e"

A1_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_A_Authority_and_Data_Extraction"
B3R1_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_B3R1_Pollock_Streamline_and_TOF_Interface_Repair"
OUT_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_B4_CO2_Plume_Evolution"
BLOCKED_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_B4_BLOCKED"

A1_CACHE = "V16VIS_A1_Authoritative_Visual_Data.npz"
A1_SUMMARY = "PAD_Stream_V16VIS_A1_Summary.json"
A1_CLOSURE = "V16VIS_A1_Final_Closure.json"
A1_COORD = "V16VIS_A1_Coordinate_Convention.json"
A1_MANIFEST = "V16VIS_A1_Artifact_Manifest.csv"

B3R1_SUMMARY = "PAD_Stream_V16VIS_B3R1_Summary.json"
B3R1_CLOSURE = "V16VIS_B3R1_Final_Closure.json"
B3R1_MANIFEST = "V16VIS_B3R1_Artifact_Manifest.csv"

GRID_SHAPE = (15, 50, 50)
NX, NY, NZ = 50, 50, 15
DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0
LX_FT = 1000.0
LY_FT = 1000.0
LZ_FT = 60.0

OBSERVATION_DAYS = np.asarray(
    [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0],
    dtype=np.float64,
)
OBSERVATION_STEPS = np.asarray(
    [611, 1222, 4640, 5747, 7931, 10400, 13259, 18490, 23668],
    dtype=np.int64,
)
SELECTED_DAYS = [30.0, 100.0, 250.0, 500.0, 750.0, 1000.0]

INJECTOR_I = 24
INJECTOR_J = 24
PRODUCERS = {
    "PROD_SW": {"i": 4, "j": 4},
    "PROD_SE": {"i": 45, "j": 4},
    "PROD_NW": {"i": 4, "j": 45},
    "PROD_NE": {"i": 45, "j": 45},
}

DPI = 300
FIGSIZE = (9.0, 7.0)
VERTICAL_EXAGGERATION = 4.166666666666667
LAYER8_K = 7

P01_VARIANTS = [
    ("P01", f"Day{int(day):04d}", f"P01_Frozen_CO2_Plume_3D_{int(day):04d}d")
    for day in OBSERVATION_DAYS
]
FIGURE_VARIANTS = P01_VARIANTS + [
    ("P02", "six_panel_layer8", "P02_Six_Panel_CO2_Plume_Evolution_Layer08"),
    ("P03", "nine_panel_plan_view", "P03_Plan_View_CO2_Plume_Evolution"),
    ("P04", "six_panel_vertical", "P04_Vertical_CO2_Plume_Evolution_Through_Injector"),
    ("P05", "terminal_3d", "P05_Final_1000d_3D_CO2_Plume"),
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


def add_wells_plan(ax: Any) -> None:
    ax.scatter([cell_center_x_ft(INJECTOR_I)], [cell_center_y_ft(INJECTOR_J)], marker="^", s=48)
    for well in PRODUCERS.values():
        ax.scatter([cell_center_x_ft(well["i"])], [cell_center_y_ft(well["j"])], marker="v", s=40)


def add_wells_3d(ax: Any) -> None:
    inj_x = cell_center_x_ft(INJECTOR_I)
    inj_y = cell_center_y_ft(INJECTOR_J)
    ax.plot([inj_x, inj_x], [inj_y, inj_y], [20.0, 40.0], marker="^", markevery=[0], linewidth=1.8)
    for well in PRODUCERS.values():
        x = cell_center_x_ft(well["i"])
        y = cell_center_y_ft(well["j"])
        ax.plot([x, x], [y, y], [20.0, 40.0], marker="v", markevery=[0], linewidth=1.4)


def configure_3d(ax: Any, title: str) -> None:
    ax.set_title(title)
    ax.set_xlabel("X, ft")
    ax.set_ylabel("Y, ft")
    ax.set_zlabel("Depth below reservoir top, ft (+z downward)")
    ax.set_xlim(0.0, LX_FT)
    ax.set_ylim(0.0, LY_FT)
    ax.set_zlim(LZ_FT, 0.0)
    ax.set_box_aspect((LX_FT, LY_FT, LZ_FT * VERTICAL_EXAGGERATION))


def plume_display_threshold(sats: np.ndarray) -> tuple[float, float]:
    smin = float(np.min(sats))
    smax = float(np.max(sats))
    span = max(smax - smin, 1.0e-12)
    threshold = smin + max(0.01, 0.03 * span)
    threshold = min(threshold, smax)
    return smin, threshold


def active_plume_points(
    sat: np.ndarray,
    x_center_ft: np.ndarray,
    y_center_ft: np.ndarray,
    depth_center_ft: np.ndarray,
    threshold: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    k, j, i = np.where(sat > threshold)
    return (
        x_center_ft[i],
        y_center_ft[j],
        depth_center_ft[k],
        sat[k, j, i],
    )


def render_p01_snapshot(
    out: Path,
    sat: np.ndarray,
    day: float,
    x_center_ft: np.ndarray,
    y_center_ft: np.ndarray,
    depth_center_ft: np.ndarray,
    norm: Normalize,
    threshold: float,
) -> list[dict[str, Any]]:
    x, y, z, c = active_plume_points(
        sat, x_center_ft, y_center_ft, depth_center_ft, threshold
    )
    fig = plt.figure(figsize=FIGSIZE)
    ax = fig.add_subplot(111, projection="3d")
    sc = ax.scatter(x, y, z, c=c, norm=norm, s=8, alpha=0.55, linewidths=0.0, rasterized=True)
    add_wells_3d(ax)
    configure_3d(ax, f"P01 — Frozen V16 CO₂ Plume, {day:.0f} d")
    cbar = fig.colorbar(sc, ax=ax, shrink=0.72, pad=0.08)
    cbar.set_label("Frozen transport saturation")
    ax.text2D(
        0.02, 0.02,
        f"Display-only plume threshold: S > {threshold:.4f} | active cells: {len(c):,}",
        transform=ax.transAxes,
    )
    return save_figure(fig, out, f"P01_Frozen_CO2_Plume_3D_{int(day):04d}d")


def render_p02(
    out: Path,
    sats: np.ndarray,
    days: np.ndarray,
    norm: Normalize,
) -> list[dict[str, Any]]:
    fig, axes = plt.subplots(2, 3, figsize=(14.0, 8.5), constrained_layout=True)
    extent = [0.0, LX_FT, 0.0, LY_FT]
    im = None
    for ax, day in zip(axes.ravel(), SELECTED_DAYS):
        idx = int(np.where(np.isclose(days, day))[0][0])
        im = ax.imshow(
            sats[idx, LAYER8_K],
            origin="lower",
            extent=extent,
            norm=norm,
            interpolation="nearest",
            aspect="equal",
        )
        add_wells_plan(ax)
        ax.set_title(f"{day:.0f} d")
        ax.set_xlabel("X, ft")
        ax.set_ylabel("Y, ft")
    assert im is not None
    cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.86)
    cbar.set_label("Frozen transport saturation")
    fig.suptitle("P02 — Frozen V16 CO₂ Plume Evolution, Layer 8")
    return save_figure(fig, out, "P02_Six_Panel_CO2_Plume_Evolution_Layer08")


def render_p03(
    out: Path,
    sats: np.ndarray,
    days: np.ndarray,
    norm: Normalize,
) -> list[dict[str, Any]]:
    fig, axes = plt.subplots(3, 3, figsize=(13.5, 12.5), constrained_layout=True)
    extent = [0.0, LX_FT, 0.0, LY_FT]
    im = None
    for ax, sat, day in zip(axes.ravel(), sats, days):
        plan = np.max(sat, axis=0)
        im = ax.imshow(
            plan,
            origin="lower",
            extent=extent,
            norm=norm,
            interpolation="nearest",
            aspect="equal",
        )
        add_wells_plan(ax)
        ax.set_title(f"{day:.0f} d")
        ax.set_xlabel("X, ft")
        ax.set_ylabel("Y, ft")
    assert im is not None
    cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.82)
    cbar.set_label("Maximum frozen transport saturation over depth")
    fig.suptitle("P03 — Frozen V16 Plan-View CO₂ Plume Evolution")
    return save_figure(fig, out, "P03_Plan_View_CO2_Plume_Evolution")


def render_p04(
    out: Path,
    sats: np.ndarray,
    days: np.ndarray,
    depth_edges_ft: np.ndarray,
    norm: Normalize,
) -> list[dict[str, Any]]:
    fig, axes = plt.subplots(2, 3, figsize=(14.0, 8.5), constrained_layout=True)
    x_edges = np.arange(NX + 1, dtype=np.float64) * DX_FT
    mesh = None
    for ax, day in zip(axes.ravel(), SELECTED_DAYS):
        idx = int(np.where(np.isclose(days, day))[0][0])
        section = sats[idx, :, INJECTOR_J, :]
        mesh = ax.pcolormesh(
            x_edges,
            depth_edges_ft,
            section,
            shading="flat",
            norm=norm,
        )
        ax.set_title(f"{day:.0f} d")
        ax.set_xlabel("X, ft")
        ax.set_ylabel("Depth below reservoir top, ft (+z downward)")
        ax.set_xlim(0.0, LX_FT)
        ax.set_ylim(LZ_FT, 0.0)
        ax.axvline(cell_center_x_ft(INJECTOR_I), linewidth=1.0)
        for well in PRODUCERS.values():
            if well["j"] == INJECTOR_J:
                ax.axvline(cell_center_x_ft(well["i"]), linewidth=0.8)
    assert mesh is not None
    cbar = fig.colorbar(mesh, ax=axes.ravel().tolist(), shrink=0.86)
    cbar.set_label("Frozen transport saturation")
    fig.suptitle(
        f"P04 — Frozen V16 Vertical CO₂ Plume Evolution Through Injector Y = {cell_center_y_ft(INJECTOR_J):.0f} ft"
    )
    return save_figure(fig, out, "P04_Vertical_CO2_Plume_Evolution_Through_Injector")


def render_p05(
    out: Path,
    sat: np.ndarray,
    x_center_ft: np.ndarray,
    y_center_ft: np.ndarray,
    depth_center_ft: np.ndarray,
    norm: Normalize,
    threshold: float,
) -> list[dict[str, Any]]:
    x, y, z, c = active_plume_points(
        sat, x_center_ft, y_center_ft, depth_center_ft, threshold
    )
    fig = plt.figure(figsize=(10.0, 8.0))
    ax = fig.add_subplot(111, projection="3d")
    sc = ax.scatter(
        x, y, z, c=c, norm=norm, s=13, alpha=0.62, linewidths=0.0, rasterized=True
    )
    add_wells_3d(ax)
    configure_3d(ax, "P05 — Final Frozen V16 CO₂ Plume at 1000 Days")
    cbar = fig.colorbar(sc, ax=ax, shrink=0.74, pad=0.08)
    cbar.set_label("Frozen transport saturation")
    ax.text2D(
        0.02, 0.02,
        f"Direct 1000-day pre-refresh observation | display threshold S > {threshold:.4f}",
        transform=ax.transAxes,
    )
    return save_figure(fig, out, "P05_Final_1000d_3D_CO2_Plume")


def self_test() -> None:
    if RELEASE_ID != "PAD-STREAM-V16-RC1-B92D52088D01078A":
        raise RuntimeError("release_identity")
    if GRID_SHAPE != (15, 50, 50):
        raise RuntimeError("grid_identity")
    if OBSERVATION_DAYS.tolist() != [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]:
        raise RuntimeError("observation_days")
    if len(FIGURE_VARIANTS) != 13:
        raise RuntimeError("figure_variant_count")
    if OUT_REL != Path("visuals") / RELEASE_PATH_ID / "Phase_B4_CO2_Plume_Evolution":
        raise RuntimeError("output_path")
    if VERTICAL_EXAGGERATION <= 1.0:
        raise RuntimeError("vertical_exaggeration")
    synthetic = np.linspace(0.2, 0.8, 9 * 15 * 2 * 2, dtype=np.float64).reshape(9, 15, 2, 2)
    smin, threshold = plume_display_threshold(synthetic)
    if not (smin <= threshold <= float(np.max(synthetic))):
        raise RuntimeError("threshold_contract")
    print("PAD-Stream V16VIS-B4 frozen CO2 plume visual self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    a1 = drive / A1_REL
    b3r1 = drive / B3R1_REL
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
        print("PAD-Stream V16VIS-B4 — Frozen V16 CO2 Plume Evolution Visuals")
        print("=" * 164)
        print("Release                    :", RELEASE_ID)
        print("Simulation                  : none")
        print("Accepted-state mutation     : none")
        print("Plume authority             : exact pre-refresh frozen observation states")
        print("Observation days            :", OBSERVATION_DAYS.tolist())
        print("Display convention          : +z downward / increasing depth")

        failed_stage = "repository_source_binding"
        for role, filename, expected in [
            ("A1", A1_RUNNER, A1_GIT_BLOB),
            ("B3R1", B3R1_RUNNER, B3R1_GIT_BLOB),
        ]:
            p = root / filename
            gate(f"{role}_exists", p.is_file(), p)
            actual = git_blob_sha(p, root)
            gate(f"{role}_git_blob_exact", actual == expected, actual)

        failed_stage = "phase_prerequisite_binding"
        for name in [A1_CACHE, A1_SUMMARY, A1_CLOSURE, A1_COORD, A1_MANIFEST]:
            gate(f"A1_exists_{name}", (a1 / name).is_file(), a1 / name)
        for name in [B3R1_SUMMARY, B3R1_CLOSURE, B3R1_MANIFEST]:
            gate(f"B3R1_exists_{name}", (b3r1 / name).is_file(), b3r1 / name)

        a1_summary = load_json(a1 / A1_SUMMARY)
        a1_closure = load_json(a1 / A1_CLOSURE)
        coord = load_json(a1 / A1_COORD)
        b3r1_summary = load_json(b3r1 / B3R1_SUMMARY)
        b3r1_closure = load_json(b3r1 / B3R1_CLOSURE)

        gate("A1_status_exact", a1_summary.get("status") == EXPECTED_A1_STATUS, a1_summary.get("status"))
        gate("A1_release_exact", a1_summary.get("release_id") == RELEASE_ID, a1_summary.get("release_id"))
        gate("A1_closure_passed", a1_closure.get("all_gates_passed") is True)
        gate("B3R1_status_exact", b3r1_summary.get("status") == EXPECTED_B3R1_STATUS, b3r1_summary.get("status"))
        gate("B3R1_release_exact", b3r1_summary.get("release_id") == RELEASE_ID, b3r1_summary.get("release_id"))
        gate("B3R1_closure_passed", b3r1_closure.get("all_gates_passed") is True)
        gate("B3R1_phase_B4_authorized", b3r1_closure.get("phase_B4_authorized") is True)
        gate(
            "coordinate_downward",
            coord["display_axes"]["positive_z_direction"] == "DOWNWARD_DEPTH",
            coord["display_axes"]["positive_z_direction"],
        )
        gate(
            "layer_order_exact",
            coord["layer_order"]["layer_1"] == "SHALLOWEST"
            and coord["layer_order"]["layer_15"] == "DEEPEST",
            coord["layer_order"],
        )

        cache_path = a1 / A1_CACHE
        cache_sha = sha256_file(cache_path)
        gate("A1_cache_SHA_exact", cache_sha == EXPECTED_A1_CACHE_SHA256, cache_sha)
        gate("A1_summary_cache_SHA_exact", a1_summary.get("visual_cache_sha256") == cache_sha)

        failed_stage = "direct_frozen_plume_extraction"
        with np.load(cache_path, allow_pickle=False) as z:
            plume_days = np.asarray(z["plume_days"], dtype=np.float64)
            plume_steps = np.asarray(z["plume_steps"], dtype=np.int64)
            plume_saturation = np.asarray(z["plume_saturation"], dtype=np.float64)
            plume_sha = np.asarray(z["plume_state_sha256"]).astype(str)
            x_center_ft = np.asarray(z["x_center_ft"], dtype=np.float64)
            y_center_ft = np.asarray(z["y_center_ft"], dtype=np.float64)
            depth_center_ft = np.asarray(z["depth_center_ft"], dtype=np.float64)
            depth_edges_ft = np.asarray(z["depth_edges_ft"], dtype=np.float64)

        gate("plume_days_exact", np.array_equal(plume_days, OBSERVATION_DAYS), plume_days.tolist())
        gate("plume_steps_exact", np.array_equal(plume_steps, OBSERVATION_STEPS), plume_steps.tolist())
        gate("plume_shape_exact", plume_saturation.shape == (9, 15, 50, 50), plume_saturation.shape)
        gate("plume_finite", bool(np.all(np.isfinite(plume_saturation))))
        gate("plume_SHA_count_exact", len(plume_sha) == 9, len(plume_sha))
        gate("plume_SHA_format", all(len(s) == 64 for s in plume_sha))
        gate("x_coordinates_exact", x_center_ft.shape == (50,) and x_center_ft[0] == 10.0 and x_center_ft[-1] == 990.0)
        gate("y_coordinates_exact", y_center_ft.shape == (50,) and y_center_ft[0] == 10.0 and y_center_ft[-1] == 990.0)
        gate("depth_coordinates_exact", depth_center_ft.shape == (15,) and depth_center_ft[0] == 2.0 and depth_center_ft[-1] == 58.0)
        gate("depth_edges_exact", depth_edges_ft.shape == (16,) and depth_edges_ft[0] == 0.0 and depth_edges_ft[-1] == 60.0)

        sat_min = float(np.min(plume_saturation))
        sat_max = float(np.max(plume_saturation))
        gate("saturation_range_nonzero", sat_max > sat_min, (sat_min, sat_max))
        gate("saturation_bounds_physical", sat_min >= -1.0e-12 and sat_max <= 1.0 + 1.0e-12, (sat_min, sat_max))
        sat_norm = Normalize(vmin=sat_min, vmax=sat_max)
        background_sat, threshold = plume_display_threshold(plume_saturation)

        failed_stage = "figure_rendering"
        if out.exists() and any(out.iterdir()):
            raise GateError("B4_output_directory_not_empty:refusing_to_overwrite_existing_visual_release")
        out.mkdir(parents=True, exist_ok=True)

        rendered: list[dict[str, Any]] = []
        for sat, day in zip(plume_saturation, plume_days):
            rendered.extend(
                render_p01_snapshot(
                    out, sat, float(day),
                    x_center_ft, y_center_ft, depth_center_ft,
                    sat_norm, threshold,
                )
            )
        rendered.extend(render_p02(out, plume_saturation, plume_days, sat_norm))
        rendered.extend(render_p03(out, plume_saturation, plume_days, sat_norm))
        rendered.extend(render_p04(out, plume_saturation, plume_days, depth_edges_ft, sat_norm))
        rendered.extend(
            render_p05(
                out, plume_saturation[-1],
                x_center_ft, y_center_ft, depth_center_ft,
                sat_norm, threshold,
            )
        )

        gate("rendered_file_count_exact", len(rendered) == len(FIGURE_VARIANTS) * 2, len(rendered))
        gate("all_rendered_files_nonempty", all(int(r["bytes"]) > 0 for r in rendered))

        failed_stage = "visual_contract_and_closeout"
        rendered_by_stem: dict[str, list[dict[str, Any]]] = {}
        for row in rendered:
            rendered_by_stem.setdefault(Path(row["file"]).stem, []).append(row)

        authority_by_figure = {
            "P01": "DIRECT_FROZEN_OBSERVATION: exact pre-refresh plume saturation states",
            "P02": "DIRECT_FROZEN_OBSERVATION: selected Layer-8 views from exact pre-refresh plume states",
            "P03": "DERIVED_FROM_DIRECT: maximum saturation over depth from exact pre-refresh plume states",
            "P04": "DERIVED_FROM_DIRECT: X-depth section through injector from exact pre-refresh plume states",
            "P05": "DIRECT_FROZEN_OBSERVATION: terminal exact 1000-day pre-refresh plume state",
        }

        figure_index: list[dict[str, Any]] = []
        for fid, variant, stem in FIGURE_VARIANTS:
            if fid == "P01":
                day = float(variant.replace("Day", ""))
            elif fid == "P05":
                day = 1000.0
            elif fid in {"P02", "P04"}:
                day = "30;100;250;500;750;1000"
            else:
                day = "30;60;100;150;250;365;500;750;1000"
            figure_index.append({
                "figure_id": fid,
                "variant": variant,
                "title_or_stem": stem,
                "authority": authority_by_figure[fid],
                "source_cache_sha256": cache_sha,
                "state_time_days": day,
                "release_id": RELEASE_ID,
                "shared_saturation_vmin": sat_min,
                "shared_saturation_vmax": sat_max,
                "z_positive_downward": True,
                "accepted_state_mutation": False,
                "files": ";".join(sorted(r["file"] for r in rendered_by_stem[stem])),
            })

        captions = [
            {
                "figure_id": "P01",
                "caption": (
                    "Full nine-checkpoint set of frozen V16 CO2-plume saturation states at "
                    "30, 60, 100, 150, 250, 365, 500, 750, and 1000 days. Each 3D view is "
                    "drawn directly from the corresponding exact pre-refresh observation array. "
                    "A common display-only plume threshold suppresses background cells; saturation "
                    "values and coordinates are not altered."
                ),
            },
            {
                "figure_id": "P02",
                "caption": (
                    "Six-panel Layer-8 plume evolution at 30, 100, 250, 500, 750, and 1000 days, "
                    "using one shared saturation normalization."
                ),
            },
            {
                "figure_id": "P03",
                "caption": (
                    "Nine-checkpoint plan-view plume evolution. Each panel displays the maximum "
                    "frozen transport saturation over depth for each horizontal cell; this is a "
                    "visual reduction of direct frozen observation states."
                ),
            },
            {
                "figure_id": "P04",
                "caption": (
                    "Six-panel X-depth plume evolution through the injector row. Depth increases "
                    "downward from the reservoir top, consistent with the locked V16VIS display convention."
                ),
            },
            {
                "figure_id": "P05",
                "caption": (
                    "Final frozen V16 1000-day 3D plume from the exact pre-refresh observation state. "
                    "The display-only threshold is identical to P01; no accepted simulation state is modified."
                ),
            },
        ]

        contract = {
            "release_id": RELEASE_ID,
            "milestone": MILESTONE,
            "source_visual_cache_sha256": cache_sha,
            "plume_authority": "exact pre-refresh frozen observation states",
            "observation_days": plume_days.tolist(),
            "observation_steps": plume_steps.tolist(),
            "observation_state_sha256": plume_sha.tolist(),
            "shared_saturation_normalization": {
                "type": "linear",
                "vmin": sat_min,
                "vmax": sat_max,
                "applies_to": ["P01", "P02", "P03", "P04", "P05"],
            },
            "three_dimensional_display": {
                "background_reference_saturation": background_sat,
                "display_only_threshold": threshold,
                "data_arrays_modified": False,
                "vertical_exaggeration": VERTICAL_EXAGGERATION,
                "applies_to": ["P01", "P05"],
            },
            "coordinate_convention": {
                "z": "Depth below reservoir top, ft (+z downward)",
                "layer_1": "shallowest",
                "layer_15": "deepest",
            },
            "simulation_executed": False,
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
            "figure_families_completed": ["P01", "P02", "P03", "P04", "P05"],
            "rendered_variants": len(FIGURE_VARIANTS),
            "rendered_files_png_pdf": len(rendered),
            "plume_observation_count": len(plume_days),
            "plume_observation_days": plume_days.tolist(),
            "plume_observation_steps": plume_steps.tolist(),
            "saturation_min": sat_min,
            "saturation_max": sat_max,
            "three_dimensional_display_threshold": threshold,
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
            "P01_complete": True,
            "P02_complete": True,
            "P03_complete": True,
            "P04_complete": True,
            "P05_complete": True,
            "nine_exact_pre_refresh_plume_states_used": True,
            "shared_saturation_normalization": True,
            "diagnostic_or_simulation_reconstruction_used": False,
            "accepted_simulation_state_modified": False,
            "phase_B5_authorized": True,
            "next": NEXT,
        }

        immutable_publish(out, {
            "V16VIS_B4_Figure_Index.csv": csv_bytes(figure_index),
            "V16VIS_B4_Figure_Captions.csv": csv_bytes(captions),
            "V16VIS_B4_Plume_Visualization_Contract.json": json_bytes(contract),
            "PAD_Stream_V16VIS_B4_Summary.json": json_bytes(summary),
            "V16VIS_B4_Final_Gate_Matrix.csv": csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
            "V16VIS_B4_Final_Closure.json": json_bytes(closure),
        })

        artifact_manifest = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "V16VIS_B4_Artifact_Manifest.csv":
                artifact_manifest.append({
                    "file": p.name,
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })
        immutable_publish(out, {"V16VIS_B4_Artifact_Manifest.csv": csv_bytes(artifact_manifest)})

        print("\n" + "=" * 164)
        print("PAD-Stream V16VIS-B4: PASS")
        print("=" * 164)
        print(f"{'Status':72}: {STATUS}")
        print(f"{'Release ID':72}: {RELEASE_ID}")
        print(f"{'A1 visual cache SHA':72}: {cache_sha}")
        print(f"{'Figure families completed':72}: P01, P02, P03, P04, P05")
        print(f"{'Rendered variants':72}: {len(FIGURE_VARIANTS)}")
        print(f"{'Rendered PNG/PDF files':72}: {len(rendered)}")
        print(f"{'Exact frozen plume observations':72}: {len(plume_days)}")
        print(f"{'Observation days':72}: {plume_days.tolist()}")
        print(f"{'Saturation range':72}: {sat_min:.12g} to {sat_max:.12g}")
        print(f"{'3D display-only plume threshold':72}: {threshold:.12g}")
        print(f"{'Vertical display convention':72}: +z downward / increasing depth")
        print(f"{'Accepted simulation state modified':72}: False")
        print(f"{'Phase B5 authorized':72}: True")
        print(f"{'Next':72}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "FROZEN_V16_CO2_PLUME_EVOLUTION_VISUALS_BLOCKED",
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        data = json_bytes(report)
        p = blocked / "V16VIS_B4_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / ("V16VIS_B4_Blocked_Report_" + hashlib.sha256(data).hexdigest()[:12] + ".json")
        p.write_bytes(data)
        print("\n" + "=" * 164)
        print("PAD-Stream V16VIS-B4: BLOCKED")
        print("=" * 164)
        print("Report      :", p)
        print("Failed stage:", failed_stage)
        print("Exception   :", repr(exc))
        return 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
