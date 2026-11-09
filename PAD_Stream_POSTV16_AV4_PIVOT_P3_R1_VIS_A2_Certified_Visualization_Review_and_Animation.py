#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

M = "POSTV16-AV4-PIVOT-P3-R1-VIS-A2"
NAME = "Certified VIS-A1 3D Visualization Review / Contact Sheets / Time Animation"
PASS = "AV4PIVOTP3R1VISA2_CERTIFIED_VIS_A1_REVIEW_AND_TIME_ANIMATION_PASS_NO_PHYSICS_MUTATION"
BLOCK = "AV4PIVOTP3R1VISA2_TECHNICAL_OR_AUTHORITY_BLOCK_NO_PHYSICS_MUTATION"

BRANCH = "postv16-av4-pivot"
PARENT = "351e87075c3ea4becbb7d3b1732cb2e708424025"  # VIS-A1
RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

VIS_A1_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_VIS_A1"
VIS_A1_REL = BASE_AV4 / (VIS_A1_TOKEN + "_Certified_Day365_to_Day405_ReadOnly_3D_Visualization")
VIS_A1_SUMMARY = f"PAD_Stream_{VIS_A1_TOKEN}_Summary.json"
VIS_A1_METRICS = f"{VIS_A1_TOKEN}_Observation_Metrics.csv"
VIS_A1_AUTHORITY = f"{VIS_A1_TOKEN}_Source_Authority.csv"
VIS_A1_MANIFEST = f"{VIS_A1_TOKEN}_Artifact_Manifest.csv"
VIS_A1_STATUS = "AV4PIVOTP3R1VISA1_CERTIFIED_DAY365_TO_DAY405_READ_ONLY_3D_VISUALIZATION_PASS_NO_PHYSICS_MUTATION"

DAYS = [365, 370, 375, 380, 385, 390, 395, 400, 405]
PLOT_KINDS = {
    "Saturation_Plume": "Saturation_Plume_3D",
    "Pressure_Field": "Pressure_Field_3D",
    "Pollock_Streamlines_TOF": "Pollock_Streamlines_TOF_3D",
    "Saturation_Streamline_Overlay": "Saturation_Streamline_Overlay_3D",
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_VIS_A2"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_Certified_VIS_A1_Review_and_Time_Animation")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
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
    pad = 8
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x0, y0 = pad, pad
    draw.rectangle((x0 - 4, y0 - 3, x0 + tw + 4, y0 + th + 3), fill=(255, 255, 255))
    draw.text((x0, y0), label, fill=(0, 0, 0), font=font)
    return out


def make_contact_sheet(paths: list[Path], labels: list[str], output: Path) -> None:
    if len(paths) != 9 or len(labels) != 9:
        raise GateError("contact_sheet_requires_nine_frames")
    tw, th = CONTACT_TILE
    m = CONTACT_MARGIN
    sheet = Image.new("RGB", (3 * tw + 4 * m, 3 * th + 4 * m), (242, 242, 242))
    for n, (path, label) in enumerate(zip(paths, labels)):
        with Image.open(path) as im:
            tile = centered_canvas(im, CONTACT_TILE)
        tile = label_tile(tile, label)
        row, col = divmod(n, 3)
        x = m + col * (tw + m)
        y = m + row * (th + m)
        sheet.paste(tile, (x, y))
    sheet.save(output, format="PNG", optimize=False)


def make_gif(paths: list[Path], labels: list[str], output: Path) -> None:
    frames: list[Image.Image] = []
    for path, label in zip(paths, labels):
        with Image.open(path) as im:
            frame = centered_canvas(im, GIF_FRAME)
        frames.append(label_tile(frame, label))
    if not frames:
        raise GateError("empty_gif_sequence")
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=GIF_DURATION_MS,
        loop=0,
        optimize=False,
        disposal=2,
    )


def make_day405_review_panel(source: Path, output: Path) -> None:
    names = [
        ("Day0405_Saturation_Plume_3D.png", "Day405 — saturation plume"),
        ("Day0405_Pressure_Field_3D.png", "Day405 — refreshed pressure"),
        ("Day0405_Pollock_Streamlines_TOF_3D.png", "Day405 — Pollock / TOF"),
        ("Day0405_Saturation_Streamline_Overlay_3D.png", "Day405 — plume + streamlines"),
    ]
    tile_size = (900, 720)
    margin = 20
    canvas = Image.new("RGB", (2 * tile_size[0] + 3 * margin, 2 * tile_size[1] + 3 * margin), (242, 242, 242))
    for n, (name, label) in enumerate(names):
        p = source / name
        if not p.is_file():
            raise GateError(f"Day405_panel_source_missing:{name}")
        with Image.open(p) as im:
            tile = centered_canvas(im, tile_size)
        tile = label_tile(tile, label)
        row, col = divmod(n, 2)
        canvas.paste(tile, (margin + col * (tile_size[0] + margin), margin + row * (tile_size[1] + margin)))
    canvas.save(output, format="PNG", optimize=False)


def fcol(rows: list[dict[str, str]], name: str) -> np.ndarray:
    try:
        return np.asarray([float(r[name]) for r in rows], dtype=np.float64)
    except Exception as exc:
        raise GateError(f"metrics_column:{name}:{exc!r}") from exc


def make_metrics_plots(metrics: list[dict[str, str]], out: Path) -> list[Path]:
    if [int(float(r["day"])) for r in metrics] != DAYS:
        raise GateError("metrics_day_sequence_mismatch")
    day = fcol(metrics, "day")
    outputs: list[Path] = []

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(day, fcol(metrics, "pressure_min_psi"), marker="o", label="Minimum")
    ax.plot(day, fcol(metrics, "pressure_mean_psi"), marker="o", label="Mean")
    ax.plot(day, fcol(metrics, "pressure_max_psi"), marker="o", label="Maximum")
    ax.set_xlabel("Observation day")
    ax.set_ylabel("Pressure (psi)")
    ax.set_title("Certified exact pressure evolution: Day365–Day405")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    p = out / f"{OUT_TOKEN}_Pressure_Evolution.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    outputs.append(p)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(day, fcol(metrics, "saturation_mean"), marker="o", label="Mean saturation")
    ax.plot(day, fcol(metrics, "saturation_max"), marker="o", label="Maximum saturation")
    ax.set_xlabel("Observation day")
    ax.set_ylabel("Gas saturation")
    ax.set_title("Certified saturation evolution: Day365–Day405")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    p = out / f"{OUT_TOKEN}_Saturation_Evolution.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    outputs.append(p)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(day, fcol(metrics, "plume_cells_above_background"), marker="o")
    ax.set_xlabel("Observation day")
    ax.set_ylabel("Cells above background saturation")
    ax.set_title("CO₂ plume-support growth: Day365–Day405")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    p = out / f"{OUT_TOKEN}_Plume_Cell_Growth.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    outputs.append(p)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(day, fcol(metrics, "tau_end_min_days"), marker="o", label="Minimum")
    ax.plot(day, fcol(metrics, "tau_end_median_days"), marker="o", label="Median")
    ax.plot(day, fcol(metrics, "tau_end_max_days"), marker="o", label="Maximum")
    ax.set_xlabel("Observation day")
    ax.set_ylabel("Terminal TOF (days)")
    ax.set_yscale("log")
    ax.set_title("Exact Pollock terminal time-of-flight evolution")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    p = out / f"{OUT_TOKEN}_Terminal_TOF_Evolution.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    outputs.append(p)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(day, fcol(metrics, "saturation_excess_centroid_x_ft"), marker="o", label="X")
    ax.plot(day, fcol(metrics, "saturation_excess_centroid_y_ft"), marker="o", label="Y")
    ax.plot(day, fcol(metrics, "saturation_excess_centroid_z_ft"), marker="o", label="Z")
    ax.set_xlabel("Observation day")
    ax.set_ylabel("Saturation-excess centroid (ft)")
    ax.set_title("CO₂ saturation-excess centroid evolution")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    p = out / f"{OUT_TOKEN}_Plume_Centroid_Evolution.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    outputs.append(p)

    return outputs


def selftest() -> None:
    assert DAYS == list(range(365, 406, 5))
    assert len(PLOT_KINDS) == 4
    assert PARENT == "351e87075c3ea4becbb7d3b1732cb2e708424025"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        paths = []
        labels = []
        for n, day in enumerate(DAYS):
            im = Image.new("RGB", (320, 240), (240 - n * 10, 245 - n * 8, 250 - n * 6))
            d = ImageDraw.Draw(im)
            d.text((15, 15), f"Day {day}", fill=(0, 0, 0), font=ImageFont.load_default())
            p = root / f"f{n}.png"
            im.save(p)
            paths.append(p)
            labels.append(f"Day {day}")
        make_contact_sheet(paths, labels, root / "sheet.png")
        make_gif(paths, labels, root / "anim.gif")
        assert (root / "sheet.png").is_file() and (root / "sheet.png").stat().st_size > 0
        assert (root / "anim.gif").is_file() and (root / "anim.gif").stat().st_size > 0
        with Image.open(root / "anim.gif") as g:
            assert getattr(g, "n_frames", 1) == 9
    print("POSTV16 AV4 PIVOT P3-R1 VIS-A2 structural/render self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    source = drive / VIS_A1_REL
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
        print("POSTV16-AV4-PIVOT-P3-R1-VIS-A2 — CERTIFIED VIS-A1 REVIEW / CONTACT SHEETS / TIME ANIMATION", flush=True)
        print("READ-ONLY DERIVATIVE VISUALIZATION ONLY. NO PHYSICS RECOMPUTATION. NO TRANSPORT ADVANCE. NO STATE MUTATION.", flush=True)
        print("=" * 150, flush=True)

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_VIS_A1_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        stage = "VIS_A1_authority"
        gate("VIS_A1_output_exists", source.is_dir(), str(source))
        for fn in [VIS_A1_SUMMARY, VIS_A1_METRICS, VIS_A1_AUTHORITY, VIS_A1_MANIFEST]:
            gate(f"VIS_A1_artifact_present:{fn}", (source / fn).is_file())
        source_manifest = verify_manifest(source, VIS_A1_MANIFEST)
        source_summary = js(source / VIS_A1_SUMMARY)
        gate("VIS_A1_status_exact", source_summary.get("status") == VIS_A1_STATUS, source_summary.get("status"))
        gate("VIS_A1_observation_days_exact", source_summary.get("observation_days") == DAYS, source_summary.get("observation_days"))
        gate("VIS_A1_plot_count_exact", int(source_summary.get("total_png_count")) == 37, source_summary.get("total_png_count"))
        gate("VIS_A1_no_physics_mutation", source_summary.get("authoritative_physics_state_mutated") is False)
        gate("VIS_A1_no_transport_advance", source_summary.get("Day405_to_Day410_transport_executed") is False)
        gate("VIS_A1_Day410_authority_preserved", source_summary.get("Day405_to_Day410_transport_remains_authorized") is True)
        gate("VIS_A1_P4_locked", source_summary.get("P4_authorized") is False)
        day405_state_sha = str(source_summary.get("Day405_state_sha256"))
        day405_diag_sha = str(source_summary.get("Day405_diagnostic_sha256"))
        gate("VIS_A1_Day405_state_hash_present", len(day405_state_sha) == 64, day405_state_sha)
        gate("VIS_A1_Day405_diagnostic_hash_present", len(day405_diag_sha) == 64, day405_diag_sha)

        stage = "source_plot_sequence"
        labels = [f"Day {d}" for d in DAYS]
        plot_sequences: dict[str, list[Path]] = {}
        for kind, suffix in PLOT_KINDS.items():
            seq = [source / f"Day{d:04d}_{suffix}.png" for d in DAYS]
            for p in seq:
                gate(f"source_plot_manifested:{p.name}", p.name in source_manifest and p.is_file())
            plot_sequences[kind] = seq

        stage = "metrics_authority"
        metrics = csv_rows(source / VIS_A1_METRICS)
        gate("metrics_nine_rows", len(metrics) == 9, len(metrics))
        gate("metrics_days_exact", [int(float(r["day"])) for r in metrics] == DAYS, [r.get("day") for r in metrics])

        stage = "output_firewall"
        gate("VIS_A2_output_does_not_preexist", not out.exists(), str(out))
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=False)

        stage = "contact_sheets_and_GIFs"
        index_rows: list[dict[str, Any]] = []
        contact_outputs: list[Path] = []
        gif_outputs: list[Path] = []
        for kind, seq in plot_sequences.items():
            contact = staging / f"{OUT_TOKEN}_{kind}_Day365_to_Day405_ContactSheet.png"
            gif = staging / f"{OUT_TOKEN}_{kind}_Day365_to_Day405.gif"
            print(f"[VIS-A2] contact sheet: {kind}", flush=True)
            make_contact_sheet(seq, labels, contact)
            print(f"[VIS-A2] GIF animation: {kind}", flush=True)
            make_gif(seq, labels, gif)
            contact_outputs.append(contact)
            gif_outputs.append(gif)
            index_rows.append({"artifact": contact.name, "type": "contact_sheet", "source_kind": kind, "days": "365;370;375;380;385;390;395;400;405"})
            index_rows.append({"artifact": gif.name, "type": "gif_animation", "source_kind": kind, "days": "365;370;375;380;385;390;395;400;405"})

        stage = "Day405_review_panel"
        day405_panel = staging / f"{OUT_TOKEN}_Day0405_FourView_Scientific_Review.png"
        make_day405_review_panel(source, day405_panel)
        index_rows.append({"artifact": day405_panel.name, "type": "four_view_review", "source_kind": "Day405", "days": "405"})

        stage = "metrics_review_plots"
        metric_outputs = make_metrics_plots(metrics, staging)
        for p in metric_outputs:
            index_rows.append({"artifact": p.name, "type": "metrics_review", "source_kind": "VIS-A1 metrics", "days": "365;370;375;380;385;390;395;400;405"})

        stage = "publication"
        write_csv(staging / INDEX, index_rows)
        expected_png = 4 + 1 + 5  # contact sheets + Day405 panel + metrics review
        expected_gif = 4
        pngs = sorted(staging.glob("*.png"))
        gifs = sorted(staging.glob("*.gif"))
        gate("expected_VIS_A2_PNG_count", len(pngs) == expected_png, len(pngs))
        gate("expected_VIS_A2_GIF_count", len(gifs) == expected_gif, len(gifs))
        for gif in gifs:
            with Image.open(gif) as im:
                gate(f"GIF_nine_frames:{gif.name}", getattr(im, "n_frames", 1) == 9, getattr(im, "n_frames", 1))

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "repository_parent_VIS_A1_commit": PARENT,
            "source_VIS_A1_status": VIS_A1_STATUS,
            "source_VIS_A1_summary_sha256": sha256(source / VIS_A1_SUMMARY),
            "source_VIS_A1_manifest_sha256": sha256(source / VIS_A1_MANIFEST),
            "source_VIS_A1_total_png_count": int(source_summary.get("total_png_count")),
            "source_Day405_state_sha256": day405_state_sha,
            "source_Day405_diagnostic_sha256": day405_diag_sha,
            "observation_days": DAYS,
            "contact_sheet_count": len(contact_outputs),
            "gif_animation_count": len(gif_outputs),
            "gif_frames_each": 9,
            "gif_frame_duration_ms": GIF_DURATION_MS,
            "Day405_four_view_review_count": 1,
            "metrics_review_plot_count": len(metric_outputs),
            "total_VIS_A2_png_count": len(pngs),
            "total_VIS_A2_gif_count": len(gifs),
            "visualization_index": INDEX,
            "read_only_derivative_visualization": True,
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
            "recommended_next_action": "Review the VIS-A2 contact sheets, GIFs, Day405 four-view panel, and metrics trends. If the scientific presentation is acceptable, preserve VIS-A1/VIS-A2 as immutable read-only visualization artifacts and resume transport with the already-authorized Day405-to-Day410 ninth-observation pilot.",
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
        print("Source VIS-A1 status                    :", VIS_A1_STATUS, flush=True)
        print("Observation days                        :", DAYS, flush=True)
        print("Contact sheets                          :", len(contact_outputs), flush=True)
        print("GIF animations                          :", len(gif_outputs), flush=True)
        print("Day405 four-view scientific review      :", day405_panel.name, flush=True)
        print("Metrics review plots                    :", len(metric_outputs), flush=True)
        print("Authoritative physics state mutated     : False", flush=True)
        print("Day405->Day410 transport executed       : False", flush=True)
        print("Day405->Day410 transport remains allowed: True", flush=True)
        print("P4 authorized                           : False", flush=True)
        print("Output directory                        :", out, flush=True)
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
