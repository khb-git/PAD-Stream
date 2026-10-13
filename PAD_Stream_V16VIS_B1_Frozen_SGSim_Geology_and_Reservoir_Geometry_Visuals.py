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
from matplotlib.colors import LogNorm


MILESTONE = "V16VIS-B1"
STATUS = "FROZEN_SGSIM_GEOLOGY_AND_RESERVOIR_GEOMETRY_VISUALS_VALIDATED"
NEXT = "V16VIS-B2 - Frozen V16 Pressure and Darcy-Flow Visuals"

RELEASE_ID = "PAD-STREAM-V16-RC1-B92D52088D01078A"
RELEASE_PATH_ID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

A1_RUNNER = "PAD_Stream_V16VIS_A1_Visual_Authority_Manifest_and_Data_Extraction.py"
A1_GIT_BLOB = "7ed31f0e69b63489f25a1833cdc3693f735b1233"
EXPECTED_A1_STATUS = "V16_VISUAL_AUTHORITY_MANIFEST_AND_DATA_EXTRACTION_VALIDATED"
EXPECTED_A1_CACHE_SHA256 = "2acbbbc8608eb771d1a6ea6909c7d37caec2ee77666a7828226e3a9e531d316e"

E49_RUNNER = "PAD_Stream_V16E49_Final_V16_Freeze_and_Release_Candidate_Assembly.py"
E49_GIT_BLOB = "15c7f9c749ba41f62f42003a3a12defcda7451d7"

A1_REL = (
    Path("visuals")
    / RELEASE_PATH_ID
    / "Phase_A_Authority_and_Data_Extraction"
)
A1_CACHE = "V16VIS_A1_Authoritative_Visual_Data.npz"
A1_SUMMARY = "PAD_Stream_V16VIS_A1_Summary.json"
A1_CLOSURE = "V16VIS_A1_Final_Closure.json"
A1_COORD = "V16VIS_A1_Coordinate_Convention.json"
A1_MANIFEST = "V16VIS_A1_Artifact_Manifest.csv"

OUT_REL = (
    Path("visuals")
    / RELEASE_PATH_ID
    / "Phase_B1_Geology_and_Reservoir_Geometry"
)
BLOCKED_REL = (
    Path("visuals")
    / RELEASE_PATH_ID
    / "Phase_B1_BLOCKED"
)

GRID_SHAPE = (15, 50, 50)
NX, NY, NZ = 50, 50, 15
DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0
LX_FT = 1000.0
LY_FT = 1000.0
LZ_FT = 60.0

# Visual-only vertical exaggeration in 3D figures.
# Data coordinates remain true feet.
VERTICAL_EXAGGERATION = 4.166666666666667

INJECTOR_I = 24
INJECTOR_J = 24
PRODUCERS = {
    "PROD_SW": {"i": 4, "j": 4},
    "PROD_SE": {"i": 45, "j": 4},
    "PROD_NW": {"i": 4, "j": 45},
    "PROD_NE": {"i": 45, "j": 45},
}
COMPLETION_LAYERS_ONE_BASED = [6, 7, 8, 9, 10]
COMPLETION_TOP_DEPTH_FT = 20.0
COMPLETION_BASE_DEPTH_FT = 40.0

REPRESENTATIVE_LAYERS = [1, 6, 8, 10, 15]
G05_CONTEXT_LAYER = 8

DPI = 300
FIGSIZE = (9.0, 7.0)

FIGURE_VARIANTS = [
    ("G01", "main", "G01_3D_SGSim_Permeability"),
    ("G02", "Layer01", "G02_Layer01_Horizontal_Permeability"),
    ("G02", "Layer06", "G02_Layer06_Horizontal_Permeability"),
    ("G02", "Layer08", "G02_Layer08_Horizontal_Permeability"),
    ("G02", "Layer10", "G02_Layer10_Horizontal_Permeability"),
    ("G02", "Layer15", "G02_Layer15_Horizontal_Permeability"),
    ("G03", "XZ_Injector", "G03_XZ_Permeability_Through_Injector"),
    ("G03", "YZ_Injector", "G03_YZ_Permeability_Through_Injector"),
    ("G04", "main", "G04_Permeability_Distribution"),
    ("G05", "main", "G05_FiveSpot_Wells_over_SGSim_Geology"),
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
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


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


def cell_center_x_ft(i: int) -> float:
    return (i + 0.5) * DX_FT


def cell_center_y_ft(j: int) -> float:
    return (j + 0.5) * DY_FT


def layer_center_depth_ft(layer_one_based: int) -> float:
    return (layer_one_based - 0.5) * DZ_FT


def save_figure(
    fig: plt.Figure,
    out: Path,
    stem: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ext in ("png", "pdf"):
        p = out / f"{stem}.{ext}"
        if p.exists():
            raise GateError(f"existing_figure:{p.name}")
        fig.savefig(p, dpi=DPI, bbox_inches="tight")
        rows.append(
            {
                "file": p.name,
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size,
            }
        )
    plt.close(fig)
    return rows


def render_g01(
    out: Path,
    perm_md: np.ndarray,
    x_center_ft: np.ndarray,
    y_center_ft: np.ndarray,
    depth_center_ft: np.ndarray,
    norm: LogNorm,
) -> list[dict[str, Any]]:
    z, y, x = np.meshgrid(
        depth_center_ft,
        y_center_ft,
        x_center_ft,
        indexing="ij",
    )

    fig = plt.figure(figsize=FIGSIZE)
    ax = fig.add_subplot(111, projection="3d")
    sc = ax.scatter(
        x.ravel(),
        y.ravel(),
        z.ravel(),
        c=perm_md.ravel(),
        norm=norm,
        s=6,
        alpha=0.72,
        linewidths=0.0,
        rasterized=True,
    )
    ax.set_title("G01 — Frozen SGSim Permeability Model")
    ax.set_xlabel("X, ft")
    ax.set_ylabel("Y, ft")
    ax.set_zlabel("Depth below reservoir top, ft (+z downward)")
    ax.set_xlim(0.0, LX_FT)
    ax.set_ylim(0.0, LY_FT)
    ax.set_zlim(LZ_FT, 0.0)
    ax.set_box_aspect(
        (LX_FT, LY_FT, LZ_FT * VERTICAL_EXAGGERATION)
    )
    cbar = fig.colorbar(sc, ax=ax, shrink=0.72, pad=0.08)
    cbar.set_label("Permeability, mD (log scale)")
    ax.text2D(
        0.02,
        0.02,
        f"Vertical exaggeration: {VERTICAL_EXAGGERATION:.2f}× (display only)",
        transform=ax.transAxes,
    )
    return save_figure(fig, out, "G01_3D_SGSim_Permeability")


def render_g02(
    out: Path,
    perm_md: np.ndarray,
    norm: LogNorm,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    extent = [0.0, LX_FT, 0.0, LY_FT]

    for layer in REPRESENTATIVE_LAYERS:
        k = layer - 1
        depth = layer_center_depth_ft(layer)
        fig, ax = plt.subplots(figsize=FIGSIZE)
        im = ax.imshow(
            perm_md[k],
            origin="lower",
            extent=extent,
            norm=norm,
            interpolation="nearest",
            aspect="equal",
        )
        ax.set_title(
            f"G02 — SGSim Horizontal Permeability, Layer {layer} "
            f"(center depth {depth:.0f} ft)"
        )
        ax.set_xlabel("X, ft")
        ax.set_ylabel("Y, ft")
        ax.set_xlim(0.0, LX_FT)
        ax.set_ylim(0.0, LY_FT)
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Permeability, mD (log scale)")
        rows.extend(
            save_figure(
                fig,
                out,
                f"G02_Layer{layer:02d}_Horizontal_Permeability",
            )
        )
    return rows


def render_g03(
    out: Path,
    perm_md: np.ndarray,
    norm: LogNorm,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    x_edges = np.arange(NX + 1, dtype=float) * DX_FT
    y_edges = np.arange(NY + 1, dtype=float) * DY_FT
    depth_edges = np.arange(NZ + 1, dtype=float) * DZ_FT

    fig, ax = plt.subplots(figsize=FIGSIZE)
    mesh = ax.pcolormesh(
        x_edges,
        depth_edges,
        perm_md[:, INJECTOR_J, :],
        norm=norm,
        shading="flat",
    )
    ax.set_title(
        "G03 — X–Depth Permeability Through Injector "
        f"(Y = {cell_center_y_ft(INJECTOR_J):.0f} ft)"
    )
    ax.set_xlabel("X, ft")
    ax.set_ylabel("Depth below reservoir top, ft (+z downward)")
    ax.set_xlim(0.0, LX_FT)
    ax.set_ylim(LZ_FT, 0.0)
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_label("Permeability, mD (log scale)")
    rows.extend(
        save_figure(
            fig,
            out,
            "G03_XZ_Permeability_Through_Injector",
        )
    )

    fig, ax = plt.subplots(figsize=FIGSIZE)
    mesh = ax.pcolormesh(
        y_edges,
        depth_edges,
        perm_md[:, :, INJECTOR_I],
        norm=norm,
        shading="flat",
    )
    ax.set_title(
        "G03 — Y–Depth Permeability Through Injector "
        f"(X = {cell_center_x_ft(INJECTOR_I):.0f} ft)"
    )
    ax.set_xlabel("Y, ft")
    ax.set_ylabel("Depth below reservoir top, ft (+z downward)")
    ax.set_xlim(0.0, LY_FT)
    ax.set_ylim(LZ_FT, 0.0)
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_label("Permeability, mD (log scale)")
    rows.extend(
        save_figure(
            fig,
            out,
            "G03_YZ_Permeability_Through_Injector",
        )
    )

    return rows


def render_g04(
    out: Path,
    perm_md: np.ndarray,
) -> list[dict[str, Any]]:
    vals = perm_md.ravel()

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.hist(vals, bins=60)
    ax.set_title("G04 — Frozen SGSim Permeability Distribution")
    ax.set_xlabel("Permeability, mD")
    ax.set_ylabel("Cell count")
    stats = (
        f"N = {vals.size:,}\n"
        f"Min = {np.min(vals):.2f} mD\n"
        f"Mean = {np.mean(vals):.2f} mD\n"
        f"Median = {np.median(vals):.2f} mD\n"
        f"Max = {np.max(vals):.2f} mD"
    )
    ax.text(
        0.98,
        0.97,
        stats,
        transform=ax.transAxes,
        ha="right",
        va="top",
    )
    return save_figure(
        fig,
        out,
        "G04_Permeability_Distribution",
    )


def render_g05(
    out: Path,
    perm_md: np.ndarray,
    x_center_ft: np.ndarray,
    y_center_ft: np.ndarray,
    norm: LogNorm,
) -> list[dict[str, Any]]:
    layer = G05_CONTEXT_LAYER
    k = layer - 1
    z_layer = layer_center_depth_ft(layer)

    xx, yy = np.meshgrid(
        x_center_ft,
        y_center_ft,
        indexing="xy",
    )

    fig = plt.figure(figsize=FIGSIZE)
    ax = fig.add_subplot(111, projection="3d")

    sc = ax.scatter(
        xx.ravel(),
        yy.ravel(),
        np.full(xx.size, z_layer),
        c=perm_md[k].ravel(),
        norm=norm,
        s=12,
        alpha=0.58,
        linewidths=0.0,
        rasterized=True,
    )

    inj_x = cell_center_x_ft(INJECTOR_I)
    inj_y = cell_center_y_ft(INJECTOR_J)
    ax.plot(
        [inj_x, inj_x],
        [inj_y, inj_y],
        [COMPLETION_TOP_DEPTH_FT, COMPLETION_BASE_DEPTH_FT],
        marker="^",
        linewidth=2.0,
        label="INJECTOR",
    )
    ax.text(
        inj_x,
        inj_y,
        COMPLETION_TOP_DEPTH_FT,
        " INJECTOR",
    )

    for name, ij in PRODUCERS.items():
        x = cell_center_x_ft(ij["i"])
        y = cell_center_y_ft(ij["j"])
        ax.plot(
            [x, x],
            [y, y],
            [COMPLETION_TOP_DEPTH_FT, COMPLETION_BASE_DEPTH_FT],
            marker="v",
            linewidth=1.6,
            label=name,
        )
        ax.text(
            x,
            y,
            COMPLETION_TOP_DEPTH_FT,
            f" {name}",
        )

    ax.set_title(
        "G05 — Five-Spot Wells Over Frozen SGSim Geology\n"
        f"Layer {layer} permeability context; completions Layers 6–10"
    )
    ax.set_xlabel("X, ft")
    ax.set_ylabel("Y, ft")
    ax.set_zlabel("Depth below reservoir top, ft (+z downward)")
    ax.set_xlim(0.0, LX_FT)
    ax.set_ylim(0.0, LY_FT)
    ax.set_zlim(LZ_FT, 0.0)
    ax.set_box_aspect(
        (LX_FT, LY_FT, LZ_FT * VERTICAL_EXAGGERATION)
    )
    cbar = fig.colorbar(sc, ax=ax, shrink=0.70, pad=0.08)
    cbar.set_label("Layer 8 permeability, mD (log scale)")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.98))
    ax.text2D(
        0.02,
        0.02,
        (
            f"Completions: {COMPLETION_TOP_DEPTH_FT:.0f}–"
            f"{COMPLETION_BASE_DEPTH_FT:.0f} ft | "
            f"vertical exaggeration {VERTICAL_EXAGGERATION:.2f}×"
        ),
        transform=ax.transAxes,
    )
    return save_figure(
        fig,
        out,
        "G05_FiveSpot_Wells_over_SGSim_Geology",
    )


def self_test() -> None:
    if RELEASE_ID != "PAD-STREAM-V16-RC1-B92D52088D01078A":
        raise RuntimeError("release_identity")
    if A1_REL != (
        Path("visuals")
        / RELEASE_PATH_ID
        / "Phase_A_Authority_and_Data_Extraction"
    ):
        raise RuntimeError("A1_path_binding")
    if OUT_REL != (
        Path("visuals")
        / RELEASE_PATH_ID
        / "Phase_B1_Geology_and_Reservoir_Geometry"
    ):
        raise RuntimeError("output_path_binding")
    if GRID_SHAPE != (15, 50, 50):
        raise RuntimeError("grid_identity")
    if REPRESENTATIVE_LAYERS != [1, 6, 8, 10, 15]:
        raise RuntimeError("representative_layers")
    if COMPLETION_LAYERS_ONE_BASED != [6, 7, 8, 9, 10]:
        raise RuntimeError("completion_layers")
    if COMPLETION_TOP_DEPTH_FT != 20.0 or COMPLETION_BASE_DEPTH_FT != 40.0:
        raise RuntimeError("completion_depth")
    if layer_center_depth_ft(1) != 2.0 or layer_center_depth_ft(15) != 58.0:
        raise RuntimeError("depth_display")
    if len(FIGURE_VARIANTS) != 10:
        raise RuntimeError("figure_variant_count")

    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(
        [0.0],
        [0.0],
        [2.0],
        c=[100.0],
        norm=LogNorm(vmin=50.0, vmax=1000.0),
    )
    ax.set_zlim(60.0, 0.0)
    plt.close(fig)

    print(
        "PAD-Stream V16VIS-B1 geology / reservoir-geometry "
        "visual self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    a1 = drive / A1_REL
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    failed_stage: str | None = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {
            "passed": bool(passed),
            "detail": str(detail),
        }
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 164)
        print(
            "PAD-Stream V16VIS-B1 — Frozen SGSim Geology "
            "and Reservoir Geometry Visuals"
        )
        print("=" * 164)
        print("Release                    :", RELEASE_ID)
        print("Simulation                  : none")
        print("Accepted-state mutation     : none")
        print("Input authority             : V16VIS-A1 frozen visual cache")
        print("Display convention          : +z downward / increasing depth")
        print("Layer order                 : Layer 1 shallowest -> Layer 15 deepest")

        failed_stage = "source_and_A1_binding"

        for role, filename, expected_blob in [
            ("A1", A1_RUNNER, A1_GIT_BLOB),
            ("E49", E49_RUNNER, E49_GIT_BLOB),
        ]:
            p = root / filename
            gate(f"{role}_runner_exists", p.is_file(), p)
            actual = git_blob_sha(p, root)
            gate(
                f"{role}_git_blob_exact",
                actual == expected_blob,
                actual,
            )

        for name in [
            A1_CACHE,
            A1_SUMMARY,
            A1_CLOSURE,
            A1_COORD,
            A1_MANIFEST,
        ]:
            gate(
                f"A1_exists_{name}",
                (a1 / name).is_file(),
                a1 / name,
            )

        a1_summary = load_json(a1 / A1_SUMMARY)
        a1_closure = load_json(a1 / A1_CLOSURE)
        coord = load_json(a1 / A1_COORD)

        gate(
            "A1_status_exact",
            a1_summary.get("status") == EXPECTED_A1_STATUS,
            a1_summary.get("status"),
        )
        gate(
            "A1_release_exact",
            a1_summary.get("release_id") == RELEASE_ID,
            a1_summary.get("release_id"),
        )
        gate(
            "A1_closure_passed",
            a1_closure.get("all_gates_passed") is True,
        )
        gate(
            "A1_phase_B_authorized",
            a1_closure.get("phase_B_authorized") is True,
        )
        gate(
            "A1_z_positive_downward",
            a1_closure.get("z_positive_downward") is True,
        )
        gate(
            "A1_layer1_shallowest",
            a1_closure.get("layer_1_shallowest") is True,
        )
        gate(
            "A1_layer15_deepest",
            a1_closure.get("layer_15_deepest") is True,
        )

        cache_path = a1 / A1_CACHE
        cache_sha = sha256_file(cache_path)
        gate(
            "A1_cache_SHA_exact",
            cache_sha == EXPECTED_A1_CACHE_SHA256,
            cache_sha,
        )
        gate(
            "A1_summary_cache_SHA_exact",
            a1_summary.get("visual_cache_sha256") == cache_sha,
            a1_summary.get("visual_cache_sha256"),
        )

        a1_manifest = load_csv(a1 / A1_MANIFEST)
        a1_manifest_map = {
            row["file"]: row
            for row in a1_manifest
        }
        gate(
            "A1_manifest_contains_cache",
            A1_CACHE in a1_manifest_map,
        )
        gate(
            "A1_manifest_cache_SHA_exact",
            a1_manifest_map[A1_CACHE]["sha256"] == cache_sha,
            a1_manifest_map[A1_CACHE]["sha256"],
        )

        gate(
            "A1_coordinate_downward",
            coord["display_axes"]["positive_z_direction"]
            == "DOWNWARD_DEPTH",
            coord["display_axes"]["positive_z_direction"],
        )
        gate(
            "A1_layer_order_exact",
            coord["layer_order"]["layer_1"] == "SHALLOWEST"
            and coord["layer_order"]["layer_15"] == "DEEPEST",
            coord["layer_order"],
        )

        failed_stage = "cache_data_validation"

        with np.load(cache_path, allow_pickle=False) as z:
            perm_md = np.asarray(
                z["permeability_md"],
                dtype=np.float64,
            )
            x_center_ft = np.asarray(
                z["x_center_ft"],
                dtype=np.float64,
            )
            y_center_ft = np.asarray(
                z["y_center_ft"],
                dtype=np.float64,
            )
            depth_center_ft = np.asarray(
                z["depth_center_ft"],
                dtype=np.float64,
            )
            depth_edges_ft = np.asarray(
                z["depth_edges_ft"],
                dtype=np.float64,
            )

        gate(
            "perm_shape_exact",
            perm_md.shape == GRID_SHAPE,
            perm_md.shape,
        )
        gate(
            "perm_finite",
            bool(np.all(np.isfinite(perm_md))),
        )
        gate(
            "perm_positive",
            float(np.min(perm_md)) > 0.0,
            float(np.min(perm_md)),
        )
        gate(
            "x_coordinates_exact",
            x_center_ft.shape == (NX,)
            and x_center_ft[0] == 10.0
            and x_center_ft[-1] == 990.0,
            (x_center_ft[0], x_center_ft[-1]),
        )
        gate(
            "y_coordinates_exact",
            y_center_ft.shape == (NY,)
            and y_center_ft[0] == 10.0
            and y_center_ft[-1] == 990.0,
            (y_center_ft[0], y_center_ft[-1]),
        )
        gate(
            "depth_coordinates_exact",
            depth_center_ft.shape == (NZ,)
            and depth_center_ft[0] == 2.0
            and depth_center_ft[-1] == 58.0
            and np.all(np.diff(depth_center_ft) > 0.0),
            (depth_center_ft[0], depth_center_ft[-1]),
        )
        gate(
            "depth_edges_exact",
            depth_edges_ft.shape == (NZ + 1,)
            and depth_edges_ft[0] == 0.0
            and depth_edges_ft[-1] == 60.0,
            (depth_edges_ft[0], depth_edges_ft[-1]),
        )

        failed_stage = "figure_rendering"

        if out.exists() and any(out.iterdir()):
            raise GateError(
                "B1_output_directory_not_empty:"
                "refusing_to_overwrite_existing_visual_release"
            )
        out.mkdir(parents=True, exist_ok=True)

        norm = LogNorm(
            vmin=float(np.min(perm_md)),
            vmax=float(np.max(perm_md)),
        )

        rendered: list[dict[str, Any]] = []
        rendered.extend(
            render_g01(
                out,
                perm_md,
                x_center_ft,
                y_center_ft,
                depth_center_ft,
                norm,
            )
        )
        rendered.extend(
            render_g02(
                out,
                perm_md,
                norm,
            )
        )
        rendered.extend(
            render_g03(
                out,
                perm_md,
                norm,
            )
        )
        rendered.extend(
            render_g04(
                out,
                perm_md,
            )
        )
        rendered.extend(
            render_g05(
                out,
                perm_md,
                x_center_ft,
                y_center_ft,
                norm,
            )
        )

        expected_rendered_files = len(FIGURE_VARIANTS) * 2
        gate(
            "rendered_file_count_exact",
            len(rendered) == expected_rendered_files,
            len(rendered),
        )
        gate(
            "all_rendered_files_nonempty",
            all(int(r["bytes"]) > 0 for r in rendered),
        )

        failed_stage = "visual_contract_and_closeout"

        rendered_by_stem: dict[str, list[dict[str, Any]]] = {}
        for row in rendered:
            stem = Path(row["file"]).stem
            rendered_by_stem.setdefault(stem, []).append(row)

        figure_index: list[dict[str, Any]] = []
        for fid, variant, stem in FIGURE_VARIANTS:
            files = sorted(
                row["file"]
                for row in rendered_by_stem[stem]
            )
            figure_index.append(
                {
                    "figure_id": fid,
                    "variant": variant,
                    "title_or_stem": stem,
                    "authority": "V16VIS-A1 frozen visual cache",
                    "source_cache_sha256": cache_sha,
                    "release_id": RELEASE_ID,
                    "z_positive_downward": True,
                    "layer_1_shallowest": True,
                    "layer_15_deepest": True,
                    "vertical_exaggeration": (
                        VERTICAL_EXAGGERATION
                        if fid in {"G01", "G05"}
                        else 1.0
                    ),
                    "files": ";".join(files),
                }
            )

        captions = [
            {
                "figure_id": "G01",
                "caption": (
                    "Frozen 50×50×15 SGSim permeability realization used by "
                    "PAD-Stream V16. Depth increases downward. The 3D rendering "
                    f"uses {VERTICAL_EXAGGERATION:.2f}× vertical exaggeration "
                    "for readability; all coordinates remain in true feet."
                ),
            },
            {
                "figure_id": "G02",
                "caption": (
                    "Representative horizontal permeability slices at Layers "
                    "1, 6, 8, 10, and 15. Layer 1 is shallowest and Layer 15 "
                    "is deepest. All variants share the same permeability "
                    "normalization."
                ),
            },
            {
                "figure_id": "G03",
                "caption": (
                    "Orthogonal permeability cross-sections through the "
                    "central injector cell (i=j=24; center 490 ft, 490 ft). "
                    "Depth increases downward from the reservoir top."
                ),
            },
            {
                "figure_id": "G04",
                "caption": (
                    "Cell-wise permeability distribution of the frozen SGSim "
                    "realization (37,500 cells)."
                ),
            },
            {
                "figure_id": "G05",
                "caption": (
                    "Five-spot well geometry over Layer 8 permeability "
                    "context. The injector and four producers are completed "
                    "over physical Layers 6–10 (20–40 ft below reservoir top). "
                    "Depth increases downward; vertical exaggeration is display "
                    "only."
                ),
            },
        ]

        style_contract = {
            "release_id": RELEASE_ID,
            "phase": MILESTONE,
            "raster_dpi": DPI,
            "formats": ["PNG", "PDF"],
            "permeability_normalization": {
                "type": "LogNorm",
                "vmin_md": float(np.min(perm_md)),
                "vmax_md": float(np.max(perm_md)),
                "shared_across_G01_G02_G03_G05": True,
            },
            "coordinate_convention": {
                "x": "X, ft",
                "y": "Y, ft",
                "z": "Depth below reservoir top, ft (+z downward)",
                "layer_1": "shallowest",
                "layer_15": "deepest",
            },
            "three_dimensional_display": {
                "vertical_exaggeration": VERTICAL_EXAGGERATION,
                "data_coordinates_changed": False,
                "applies_to": ["G01", "G05"],
            },
            "well_geometry": {
                "injector_ij_zero_based": [
                    INJECTOR_I,
                    INJECTOR_J,
                ],
                "injector_xy_ft": [
                    cell_center_x_ft(INJECTOR_I),
                    cell_center_y_ft(INJECTOR_J),
                ],
                "producer_ij_zero_based": PRODUCERS,
                "completion_layers_one_based":
                    COMPLETION_LAYERS_ONE_BASED,
                "completion_depth_ft": [
                    COMPLETION_TOP_DEPTH_FT,
                    COMPLETION_BASE_DEPTH_FT,
                ],
            },
            "physics_or_state_mutation": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "release_id": RELEASE_ID,
            "simulation_executed": False,
            "accepted_state_mutation": False,
            "source_visual_cache_sha256": cache_sha,
            "figure_families_completed": [
                "G01",
                "G02",
                "G03",
                "G04",
                "G05",
            ],
            "rendered_variants": len(FIGURE_VARIANTS),
            "rendered_files_png_pdf": len(rendered),
            "representative_horizontal_layers":
                REPRESENTATIVE_LAYERS,
            "injector_cross_section_ij_zero_based": [
                INJECTOR_I,
                INJECTOR_J,
            ],
            "well_completion_layers_one_based":
                COMPLETION_LAYERS_ONE_BASED,
            "well_completion_depth_ft": [
                COMPLETION_TOP_DEPTH_FT,
                COMPLETION_BASE_DEPTH_FT,
            ],
            "z_positive_downward": True,
            "layer_1_shallowest": True,
            "layer_15_deepest": True,
            "three_dimensional_vertical_exaggeration":
                VERTICAL_EXAGGERATION,
            "next": NEXT,
        }

        closure = {
            "milestone": MILESTONE,
            "status": STATUS,
            "all_gates_passed": all(
                item["passed"]
                for item in gates.values()
            ),
            "gate_count": len(gates),
            "G01_complete": True,
            "G02_complete": True,
            "G03_complete": True,
            "G04_complete": True,
            "G05_complete": True,
            "all_figures_from_frozen_A1_cache": True,
            "same_permeability_normalization_used": True,
            "z_positive_downward": True,
            "accepted_simulation_state_modified": False,
            "phase_B2_authorized": True,
            "next": NEXT,
        }

        immutable_publish(
            out,
            {
                "V16VIS_B1_Figure_Index.csv":
                    csv_bytes(figure_index),
                "V16VIS_B1_Figure_Captions.csv":
                    csv_bytes(captions),
                "V16VIS_B1_Style_and_Coordinate_Contract.json":
                    json_bytes(style_contract),
                "PAD_Stream_V16VIS_B1_Summary.json":
                    json_bytes(summary),
                "V16VIS_B1_Final_Gate_Matrix.csv":
                    csv_bytes(
                        [
                            {"gate": key, **value}
                            for key, value in gates.items()
                        ]
                    ),
                "V16VIS_B1_Final_Closure.json":
                    json_bytes(closure),
            },
        )

        artifact_manifest = []
        for p in sorted(out.iterdir()):
            if (
                p.is_file()
                and p.name
                != "V16VIS_B1_Artifact_Manifest.csv"
            ):
                artifact_manifest.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )

        immutable_publish(
            out,
            {
                "V16VIS_B1_Artifact_Manifest.csv":
                    csv_bytes(artifact_manifest)
            },
        )

        print("\n" + "=" * 164)
        print("PAD-Stream V16VIS-B1: PASS")
        print("=" * 164)
        print(f"{'Status':72}: {STATUS}")
        print(f"{'Release ID':72}: {RELEASE_ID}")
        print(f"{'A1 visual cache SHA':72}: {cache_sha}")
        print(f"{'Figure families completed':72}: G01, G02, G03, G04, G05")
        print(f"{'Rendered variants':72}: {len(FIGURE_VARIANTS)}")
        print(f"{'Rendered PNG/PDF files':72}: {len(rendered)}")
        print(f"{'Horizontal slice layers':72}: {REPRESENTATIVE_LAYERS}")
        print(
            f"{'Injector center X/Y':72}: "
            f"{cell_center_x_ft(INJECTOR_I):.1f} / "
            f"{cell_center_y_ft(INJECTOR_J):.1f} ft"
        )
        print(f"{'Well completion layers':72}: 6-10")
        print(f"{'Well completion depth':72}: 20-40 ft")
        print(
            f"{'Vertical display convention':72}: "
            "+z downward / increasing depth"
        )
        print(
            f"{'3D vertical exaggeration':72}: "
            f"{VERTICAL_EXAGGERATION:.2f}x display only"
        )
        print(
            f"{'Accepted simulation state modified':72}: False"
        )
        print(f"{'Phase B2 authorized':72}: True")
        print(f"{'Next':72}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status":
                "FROZEN_SGSIM_GEOLOGY_AND_RESERVOIR_GEOMETRY_VISUALS_BLOCKED",
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        data = json_bytes(report)
        p = blocked / "V16VIS_B1_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "V16VIS_B1_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        p.write_bytes(data)
        print("\n" + "=" * 164)
        print("PAD-Stream V16VIS-B1: BLOCKED")
        print("=" * 164)
        print("Report      :", p)
        print("Failed stage:", failed_stage)
        print("Exception   :", repr(exc))
        return 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--drive-root",
        type=Path,
        default=Path(
            "/content/drive/MyDrive/PAD_Stream_Compute"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
