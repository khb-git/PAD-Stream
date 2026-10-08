#!/usr/bin/env python3
"""
PAD-Stream V16E-11-R2
Packed SG5 Serialization Repair, Frozen Artifact Recovery and Rebind

Purpose
-------
Recover the already-generated, source-authentic Version-15 7x7 SGSim artifacts
required by V16E-11, bind their hashes and schemas without recomputation, copy
those exact bytes into persistent Google Drive storage, and run the repaired
V16E-11-R2 pilot whose only code change is faithful deserialization of the
historical packed SG5 schema.

This milestone does NOT recompute pressure, Darcy flux, Pollock trajectories,
TOF coordinates, SG7A truth, or any grid map-back. It does not alter any Hybrid
checkpoint or reopen internal-test/OOD evaluation. The original V16E-11 blocked
evidence is preserved and explicitly bound before repaired execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "V16E-11-R2"
STATUS_PACKED = "V16E11_R2_LOCAL_PACKED_SG5_FROZEN_SGSIM_ARTIFACT_BUNDLE_CREATED"
STATUS_BOUND = "V16E11_R2_FROZEN_SGSIM_ARTIFACTS_BOUND_AND_REPAIRED_E11R2_RERUN_COMPLETED"

EXPECTED_ORIGINAL_E11_RUNNER_SHA256 = "3c714222c5698f7a18db9fdbebce9ea1e51b35fba3a08bc3e92904c0d2b60525"
EXPECTED_E11R2_RUNNER_SHA256 = "0363a09612c5e80f6bb8124c817ca0d3726b1654283ab169c9b2d4d9861707b7"
EXPECTED_R1_RUNNER_SHA256 = "6b2930c15fd8099d798fedb2c90183f35121e152a45e22fb3fd74eeea869ac20"
EXPECTED_BLOCKED_REPORT_SHA256 = "4a1bcc5ec54c28dae80262fdb777678e9e201e746d655b9a7319087c1a8501f1"
BLOCKED_DIR_REL = Path("provenance/hybrid_dp/V16E11_BLOCKED_SGSIM_STREAMLINE_PILOT") / EXPECTED_BLOCKED_REPORT_SHA256[:16]
BLOCKED_REPORT_NAME = "V16E11_Blocked_SGSim_Streamline_Pilot_Audit.json"

EXPECTED_NSTREAM = 1078
EXPECTED_NXI = 201
EXPECTED_RATE_M3_DAY = 714.285714
RATE_ABS_TOL_M3_DAY = 5.0e-4

WORKSPACE_BASENAME = "PAD_Stream_V15G0_Windows_Portable_v2_SG5C_seed_07x07"
DRIVE_RECOVERED_REL = Path("recovered_sgsim/V16E11_R2_FROZEN_07x07_WORKSPACE")
PROVENANCE_REL = Path("provenance/hybrid_dp/V16E11_R2_PACKED_SG5_ARTIFACT_RECOVERY")

REQUIRED = [
    Path("output/V15_SG5/STREAMLINES_POLLOCK.npz"),
    Path("output/V15_SG6/STREAMLINE_TRANSPORT_COORDINATES.npz"),
    Path("output/V15_SG7C/SG7C_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"),
]
OPTIONAL_SUMMARIES = [
    Path("output/V15_SG5/PAD_Stream_V15SG5_Summary.json"),
    Path("output/V15_SG6/PAD_Stream_V15SG6_Summary.json"),
    Path("output/V15_SG7C/PAD_Stream_V15SG7C_Summary.json"),
]
MANIFEST_NAME = "V16E11R2_Frozen_SGSim_Artifact_Manifest.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, separators=(",", ": ")) + "\n").encode("utf-8")


def first_key(z, aliases: list[str]) -> str | None:
    for k in aliases:
        if k in z.files:
            return k
    return None


def unpack_object_array(a: np.ndarray) -> list[Any]:
    return list(a.tolist()) if a.dtype == object else list(a)


def extract_sg5_streamlines(path: Path) -> list[dict[str, Any]]:
    """Exact deserialization of frozen SG5 trajectories, including V15 packed schema."""
    with np.load(path, allow_pickle=True) as z:
        for key in ["streamlines", "pollock_streamlines", "streamline_records"]:
            if key in z.files:
                records = unpack_object_array(z[key])
                if records and isinstance(records[0], dict):
                    return records

        packed_required = {
            "points_m", "cumulative_times_s", "offsets",
            "weights_m3_s", "travel_times_s", "statuses", "producers",
        }
        if packed_required.issubset(set(z.files)):
            points = np.asarray(z["points_m"], dtype=np.float64)
            times = np.asarray(z["cumulative_times_s"], dtype=np.float64)
            offsets = np.asarray(z["offsets"], dtype=np.int64)
            weights = np.asarray(z["weights_m3_s"], dtype=np.float64)
            travel = np.asarray(z["travel_times_s"], dtype=np.float64)
            statuses = np.asarray(z["statuses"])
            producers = np.asarray(z["producers"])
            n = weights.size

            if points.ndim != 2 or points.shape[1] != 3:
                raise RuntimeError(f"Packed SG5 points_m shape invalid: {points.shape}")
            if times.ndim != 1 or times.size != points.shape[0]:
                raise RuntimeError("Packed SG5 cumulative_times_s does not align with points_m")
            if offsets.shape != (n + 1,):
                raise RuntimeError(f"Packed SG5 offsets shape {offsets.shape} != {(n + 1,)}")
            if travel.shape != (n,) or statuses.shape != (n,) or producers.shape != (n,):
                raise RuntimeError("Packed SG5 per-streamline arrays do not align")
            if offsets[0] != 0 or offsets[-1] != points.shape[0] or np.any(np.diff(offsets) < 2):
                raise RuntimeError("Packed SG5 offsets are not a valid exact trajectory partition")
            if not np.all(np.isfinite(points)) or not np.all(np.isfinite(times)):
                raise RuntimeError("Packed SG5 source-native arrays contain nonfinite values")
            if not np.all(np.isfinite(weights)) or not np.all(weights > 0.0):
                raise RuntimeError("Packed SG5 weights invalid")
            if not np.all(np.isfinite(travel)) or not np.all(travel > 0.0):
                raise RuntimeError("Packed SG5 travel times invalid")

            out = []
            for i in range(n):
                lo = int(offsets[i]); hi = int(offsets[i + 1])
                pp = np.array(points[lo:hi], copy=True)
                tt = np.array(times[lo:hi], copy=True)
                if tt.size < 2 or np.any(np.diff(tt) < 0.0):
                    raise RuntimeError(f"Packed SG5 streamline {i} has invalid cumulative time order")
                if abs(float(tt[-1]) - float(travel[i])) > 1.0e-7 + 1.0e-10 * max(abs(float(travel[i])), 1.0):
                    raise RuntimeError(f"Packed SG5 streamline {i} terminal time mismatch")
                out.append({
                    "seed_id": i,
                    "points_m": pp,
                    "times_s": tt,
                    "travel_time_s": float(travel[i]),
                    "weight_m3_s": float(weights[i]),
                    "producer": str(producers[i]),
                    "status": str(statuses[i]),
                })
            return out

        pk = first_key(z, ["points_m", "streamline_points_m", "xyz_m"])
        tk = first_key(z, ["times_s", "streamline_times_s", "pollock_times_s"])
        ek = first_key(z, ["travel_time_s", "travel_times_s", "tau_end_s", "terminal_tof_s"])
        wk = first_key(z, ["weight_m3_s", "streamline_weight_m3_s", "weights_m3_s"])
        rk = first_key(z, ["producer", "producers", "producer_id", "producer_name"])
        sk = first_key(z, ["status", "statuses", "streamline_status"])
        ik = first_key(z, ["seed_id", "streamline_id", "id"])
        if pk is None or tk is None or wk is None:
            raise RuntimeError(f"SG5 artifact lacks a recognized source-native trajectory schema: {path}")
        points = unpack_object_array(z[pk]); times = unpack_object_array(z[tk]); n = len(points)

        def vals(key: str | None, default: Any) -> list[Any]:
            if key is None:
                return [default for _ in range(n)]
            q = unpack_object_array(z[key])
            if len(q) != n:
                raise RuntimeError(f"SG5 parallel array {key} length {len(q)} != {n}")
            return q

        ends = vals(ek, None); weights = vals(wk, np.nan); producers = vals(rk, None); statuses = vals(sk, "PRODUCER"); ids = vals(ik, None)
        out = []
        for i in range(n):
            tt = np.asarray(times[i], dtype=np.float64)
            out.append({
                "seed_id": i if ids[i] is None else ids[i],
                "points_m": np.asarray(points[i], dtype=np.float64),
                "times_s": tt,
                "travel_time_s": float(tt[-1]) if ends[i] is None else float(ends[i]),
                "weight_m3_s": float(weights[i]),
                "producer": producers[i],
                "status": statuses[i],
            })
        return out


def validate_sg5(path: Path) -> dict[str, Any]:
    streams = extract_sg5_streamlines(path)
    if len(streams) != EXPECTED_NSTREAM:
        raise RuntimeError(f"SG5 expected {EXPECTED_NSTREAM} streamlines, got {len(streams)}")
    weights = []
    producers = []
    ends = []
    for i, s in enumerate(streams):
        p = np.asarray(s["points_m"], dtype=np.float64)
        t = np.asarray(s["times_s"], dtype=np.float64)
        if p.ndim != 2 or p.shape[1] != 3 or t.ndim != 1 or len(p) != len(t) or len(t) < 2:
            raise RuntimeError(f"SG5 streamline {i} has invalid points/times schema")
        if not np.all(np.isfinite(p)) or not np.all(np.isfinite(t)) or np.any(np.diff(t) < 0.0):
            raise RuntimeError(f"SG5 streamline {i} has nonfinite/nonmonotone source-native trajectory")
        te = float(s["travel_time_s"])
        w = float(s["weight_m3_s"])
        if not np.isfinite(te) or te <= 0.0 or not np.isfinite(w) or w <= 0.0:
            raise RuntimeError(f"SG5 streamline {i} has invalid terminal TOF/weight")
        if not np.isclose(t[-1], te, rtol=1e-10, atol=1e-7):
            raise RuntimeError(f"SG5 streamline {i} terminal TOF mismatch")
        status = str(s.get("status", "")).upper()
        if "PRODUCER" not in status:
            raise RuntimeError(f"SG5 streamline {i} is not producer-captured: {status}")
        weights.append(w)
        producers.append(str(s.get("producer", "")))
        ends.append(te)
    qday = float(np.sum(weights) * 86400.0)
    if abs(qday - EXPECTED_RATE_M3_DAY) > RATE_ABS_TOL_M3_DAY:
        raise RuntimeError(f"SG5 weight sum {qday:.9f} m3/day does not close frozen rate")
    if len(set(producers)) != 4:
        raise RuntimeError(f"SG5 expected four producers, got {sorted(set(producers))}")
    return {
        "streamlines": len(streams),
        "all_producer_captured": True,
        "four_producers": True,
        "weight_sum_m3_day": qday,
        "terminal_tof_min_days": float(np.min(ends) / 86400.0),
        "terminal_tof_max_days": float(np.max(ends) / 86400.0),
    }


def load_sg6(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=True) as z:
        keys = {
            "xi": first_key(z, ["xi", "transport_xi"]),
            "xyz": first_key(z, ["xyz_m", "transport_xyz", "xyz", "streamline_xyz", "XYZ"]),
            "tau": first_key(z, ["tau_s", "tof_s", "tau", "transport_tau_s", "pollock_tau_s"]),
            "tau_end": first_key(z, ["tau_end_s", "terminal_tau_s", "terminal_tof_s", "pollock_tau_end_s"]),
            "weights": first_key(z, ["weights_m3_s", "weights", "flow_weights_m3_s", "streamline_weight_m3_s"]),
            "producer": first_key(z, ["producer", "producer_id", "producer_index"]),
            "streamline_id": first_key(z, ["streamline_id", "id", "seed_id"]),
        }
        if any(keys[k] is None for k in ["xi", "xyz", "tau", "tau_end", "weights", "producer"]):
            raise RuntimeError(f"SG6 required keys missing: {keys}")
        return {
            "keys": keys,
            "xi": np.asarray(z[keys["xi"]], dtype=np.float64),
            "xyz": np.asarray(z[keys["xyz"]], dtype=np.float64),
            "tau": np.asarray(z[keys["tau"]], dtype=np.float64),
            "tau_end": np.asarray(z[keys["tau_end"]], dtype=np.float64),
            "weights": np.asarray(z[keys["weights"]], dtype=np.float64),
            "producer": np.asarray(z[keys["producer"]]),
            "streamline_id": np.asarray(z[keys["streamline_id"]]) if keys["streamline_id"] is not None else None,
        }


def validate_sg6(path: Path) -> dict[str, Any]:
    d = load_sg6(path)
    xi, xyz, tau, end, w, prod = d["xi"], d["xyz"], d["tau"], d["tau_end"], d["weights"], d["producer"]
    checks = {
        "xi_shape": xi.shape == (EXPECTED_NXI,),
        "xi_exact": xi.shape == (EXPECTED_NXI,) and np.array_equal(xi, np.linspace(0.0, 1.0, EXPECTED_NXI)),
        "xyz_shape": xyz.shape == (EXPECTED_NSTREAM, EXPECTED_NXI, 3),
        "tau_shape": tau.shape == (EXPECTED_NSTREAM, EXPECTED_NXI),
        "tau_end_shape": end.shape == (EXPECTED_NSTREAM,),
        "weights_shape": w.shape == (EXPECTED_NSTREAM,),
        "producer_shape": prod.shape == (EXPECTED_NSTREAM,),
        "finite": bool(np.all(np.isfinite(xyz)) and np.all(np.isfinite(tau)) and np.all(np.isfinite(end)) and np.all(np.isfinite(w))),
        "positive_terminal_tof": bool(end.shape == (EXPECTED_NSTREAM,) and np.all(end > 0.0)),
        "positive_weights": bool(w.shape == (EXPECTED_NSTREAM,) and np.all(w > 0.0)),
        "tau_monotonic": bool(tau.shape == (EXPECTED_NSTREAM, EXPECTED_NXI) and np.all(np.diff(tau, axis=1) >= -1.0e-12)),
        "tau_starts_zero": bool(tau.shape == (EXPECTED_NSTREAM, EXPECTED_NXI) and np.max(np.abs(tau[:, 0])) <= 1.0e-8),
        "tau_end_match": bool(tau.shape == (EXPECTED_NSTREAM, EXPECTED_NXI) and end.shape == (EXPECTED_NSTREAM,) and np.allclose(tau[:, -1], end, rtol=1e-12, atol=1e-7)),
        "weight_sum": bool(w.shape == (EXPECTED_NSTREAM,) and abs(float(np.sum(w) * 86400.0) - EXPECTED_RATE_M3_DAY) <= RATE_ABS_TOL_M3_DAY),
        "four_producers": len(set(map(str, prod.tolist()))) == 4,
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        raise RuntimeError("SG6 frozen-reference validation failed: " + ", ".join(failed))
    return {
        "keys": d["keys"],
        "checks": checks,
        "tof_min_days": float(np.min(end) / 86400.0),
        "tof_median_days": float(np.median(end) / 86400.0),
        "tof_max_days": float(np.max(end) / 86400.0),
        "weight_sum_m3_day": float(np.sum(w) * 86400.0),
    }


def validate_sg7c(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=True) as z:
        time_key = first_key(z, ["times_days", "physical_times_days", "deployment_times_days"])
        truth_key = first_key(z, ["SG7A_saturation", "truth_saturation", "reference_saturation", "S_truth"])
        if time_key is None or truth_key is None:
            raise RuntimeError("SG7C database does not expose frozen deployment times + SG7A truth")
        times = np.asarray(z[time_key], dtype=np.float64)
        truth = np.asarray(z[truth_key], dtype=np.float32)
        idx = int(np.argmin(np.abs(times - 100.0)))
        if not np.isclose(times[idx], 100.0, rtol=0.0, atol=1e-12):
            raise RuntimeError(f"SG7C does not contain exact 100-day truth; times={times.tolist()}")
        truth100 = np.asarray(truth[idx], dtype=np.float32)
        if truth100.shape != (EXPECTED_NSTREAM, EXPECTED_NXI) or not np.all(np.isfinite(truth100)):
            raise RuntimeError(f"SG7C truth100 invalid: shape={truth100.shape}")
        return {
            "time_key": time_key,
            "truth_key": truth_key,
            "times_days": [float(x) for x in times.tolist()],
            "truth_shape": list(truth.shape),
            "truth100_shape": list(truth100.shape),
            "truth100_finite": True,
        }


def validate_workspace(workspace: Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    if not workspace.is_dir():
        raise FileNotFoundError(f"Frozen workspace missing: {workspace}")
    if workspace.name != WORKSPACE_BASENAME:
        raise RuntimeError(f"Expected exact frozen workspace basename {WORKSPACE_BASENAME!r}, got {workspace.name!r}")
    missing = [str(rel) for rel in REQUIRED if not (workspace / rel).is_file()]
    if missing:
        raise FileNotFoundError("Required frozen artifacts missing:\n  " + "\n  ".join(missing))
    sg5 = validate_sg5(workspace / REQUIRED[0])
    sg6 = validate_sg6(workspace / REQUIRED[1])
    sg7c = validate_sg7c(workspace / REQUIRED[2])
    return {"sg5": sg5, "sg6": sg6, "sg7c": sg7c}


def artifact_inventory(workspace: Path) -> list[dict[str, Any]]:
    rows = []
    for rel in REQUIRED + OPTIONAL_SUMMARIES:
        p = workspace / rel
        if not p.is_file():
            if rel in REQUIRED:
                raise FileNotFoundError(p)
            continue
        rows.append({
            "relative_path": rel.as_posix(),
            "sha256": sha256_file(p),
            "size_bytes": p.stat().st_size,
            "required": rel in REQUIRED,
        })
    return rows


def build_bundle(workspace: Path, output_zip: Path) -> int:
    workspace = workspace.resolve()
    output_zip = output_zip.resolve()
    print("=" * 110)
    print("PAD-Stream V16E-11-R2 - LOCAL PACKED-SG5 FROZEN ARTIFACT RECOVERY PACK")
    print("=" * 110)
    print("NO RECOMPUTATION. NO FILE MODIFICATION. NO TRAINING. NO GRID MAP-BACK.\n")
    validation = validate_workspace(workspace)
    inventory = artifact_inventory(workspace)
    manifest = {
        "milestone": MILESTONE,
        "status": STATUS_PACKED,
        "source_workspace_absolute": str(workspace),
        "source_workspace_basename": workspace.name,
        "original_e11_runner_sha256": EXPECTED_ORIGINAL_E11_RUNNER_SHA256,
        "e11r2_runner_sha256_required_for_rebind": EXPECTED_E11R2_RUNNER_SHA256,
        "r1_runner_sha256": EXPECTED_R1_RUNNER_SHA256,
        "original_e11_blocked_report_sha256": EXPECTED_BLOCKED_REPORT_SHA256,
        "schema_repair": "historical V15 packed SG5 arrays deserialized exactly via offsets; no trajectory reconstruction",
        "required_artifacts": [x.as_posix() for x in REQUIRED],
        "artifacts": inventory,
        "validation": validation,
        "scientific_state_changed": False,
        "pressure_Darcy_Pollock_TOF_recomputed": False,
        "SG7A_truth_recomputed": False,
        "training_or_checkpoint_change": False,
        "grid_mapback_performed": False,
    }
    manifest_bytes = canonical_json_bytes(manifest)
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr(MANIFEST_NAME, manifest_bytes)
        for row in inventory:
            rel = Path(row["relative_path"])
            zf.write(workspace / rel, arcname=rel.as_posix())
    print("[PASS] Frozen SG5 packed source-native 1078-streamline artifact")
    print("[PASS] Frozen SG6 1078x201 transport-coordinate artifact")
    print("[PASS] Frozen SG7C exact 100-day SG7A truth carrier")
    print("Bundle:", output_zip)
    print("Bundle SHA-256:", sha256_file(output_zip))
    print("Manifest SHA-256:", hashlib.sha256(manifest_bytes).hexdigest())
    print("NEXT: upload this ZIP in the V16E11-R2 Colab wrapper; do not add it to Git.")
    return 0


def safe_extract_bundle(bundle: Path, target: Path) -> dict[str, Any]:
    with zipfile.ZipFile(bundle, "r") as zf:
        names = zf.namelist()
        if MANIFEST_NAME not in names:
            raise RuntimeError(f"Bundle missing {MANIFEST_NAME}")
        for name in names:
            q = Path(name)
            if q.is_absolute() or ".." in q.parts:
                raise RuntimeError(f"Unsafe ZIP member: {name}")
        manifest = json.loads(zf.read(MANIFEST_NAME).decode("utf-8"))
        zf.extractall(target)
    return manifest


def verify_manifest_tree(root: Path, manifest: dict[str, Any]) -> None:
    if manifest.get("milestone") != MILESTONE or manifest.get("status") != STATUS_PACKED:
        raise RuntimeError("Bundle manifest milestone/status mismatch")
    if manifest.get("source_workspace_basename") != WORKSPACE_BASENAME:
        raise RuntimeError("Bundle source workspace identity mismatch")
    if manifest.get("original_e11_runner_sha256") != EXPECTED_ORIGINAL_E11_RUNNER_SHA256:
        raise RuntimeError("Bundle original-E11 authority mismatch")
    if manifest.get("e11r2_runner_sha256_required_for_rebind") != EXPECTED_E11R2_RUNNER_SHA256:
        raise RuntimeError("Bundle was not created for the repaired E11-R2 runner")
    if manifest.get("r1_runner_sha256") != EXPECTED_R1_RUNNER_SHA256:
        raise RuntimeError("Bundle R1 lineage mismatch")
    if manifest.get("original_e11_blocked_report_sha256") != EXPECTED_BLOCKED_REPORT_SHA256:
        raise RuntimeError("Bundle was not created for the recorded E11 blocked evidence")
    for row in manifest.get("artifacts", []):
        p = root / row["relative_path"]
        if not p.is_file():
            raise FileNotFoundError(f"Bundle artifact missing after extraction: {p}")
        actual = sha256_file(p)
        if actual != row["sha256"]:
            raise RuntimeError(f"Bundle artifact SHA mismatch: {row['relative_path']}\nexpected={row['sha256']}\nactual={actual}")
        if p.stat().st_size != int(row["size_bytes"]):
            raise RuntimeError(f"Bundle artifact size mismatch: {row['relative_path']}")


def copy_exact_tree(src_root: Path, dst_root: Path, manifest: dict[str, Any]) -> None:
    dst_root.mkdir(parents=True, exist_ok=True)
    for row in manifest["artifacts"]:
        rel = Path(row["relative_path"])
        src = src_root / rel
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            if sha256_file(dst) != row["sha256"] or dst.stat().st_size != int(row["size_bytes"]):
                raise RuntimeError(f"Refusing to overwrite non-identical recovered artifact: {dst}")
        else:
            shutil.copy2(src, dst)
        if sha256_file(dst) != row["sha256"]:
            raise RuntimeError(f"Post-copy SHA mismatch: {dst}")


def bind_blocked_evidence(drive: Path) -> Path:
    p = drive / BLOCKED_DIR_REL / BLOCKED_REPORT_NAME
    if not p.is_file():
        raise FileNotFoundError(f"Original E11 blocked report missing: {p}")
    actual = sha256_file(p)
    if actual != EXPECTED_BLOCKED_REPORT_SHA256:
        raise RuntimeError(f"Original E11 blocked report SHA drift\nexpected={EXPECTED_BLOCKED_REPORT_SHA256}\nactual={actual}")
    return p


def publish_recovery(drive: Path, bundle: Path, manifest: dict[str, Any], recovered_workspace: Path, e11_exit_code: int) -> Path:
    out = drive / PROVENANCE_REL
    out.mkdir(parents=True, exist_ok=True)
    audit = {
        "milestone": MILESTONE,
        "status": STATUS_BOUND,
        "bundle_sha256": sha256_file(bundle),
        "source_workspace_absolute_recorded": manifest["source_workspace_absolute"],
        "source_workspace_basename": manifest["source_workspace_basename"],
        "original_e11_blocked_report_sha256": EXPECTED_BLOCKED_REPORT_SHA256,
        "schema_repair": "historical V15 packed SG5 arrays deserialized exactly via offsets; no trajectory reconstruction",
        "original_e11_runner_sha256": EXPECTED_ORIGINAL_E11_RUNNER_SHA256,
        "repaired_e11r2_runner_sha256": EXPECTED_E11R2_RUNNER_SHA256,
        "r1_runner_sha256": EXPECTED_R1_RUNNER_SHA256,
        "recovered_workspace": str(recovered_workspace),
        "artifacts": manifest["artifacts"],
        "validation": manifest["validation"],
        "scientific_state_changed": False,
        "pressure_Darcy_Pollock_TOF_recomputed": False,
        "SG7A_truth_recomputed": False,
        "training_or_checkpoint_change": False,
        "grid_mapback_performed": False,
        "e11r2_rerun_exit_code": int(e11_exit_code),
        "next": "V16E-12 only if V16E-11-R2 reports PASS; otherwise repair only the remaining failed gate.",
    }
    audit_path = out / "V16E11_R2_Frozen_SGSim_Artifact_Recovery_Audit.json"
    audit_path.write_bytes(canonical_json_bytes(audit))
    summary = {
        "milestone": MILESTONE,
        "status": STATUS_BOUND if e11_exit_code == 0 else "V16E11_R2_RECOVERY_BOUND_REPAIRED_PILOT_STILL_BLOCKED",
        "artifact_recovery_pass": True,
        "repaired_e11r2_rerun_exit_code": int(e11_exit_code),
        "recovery_audit_sha256": sha256_file(audit_path),
        "no_recomputation": True,
        "no_training": True,
        "no_grid_mapback": True,
    }
    summary_path = out / "PAD_Stream_V16E11_R2_Recovery_Summary.json"
    summary_path.write_bytes(canonical_json_bytes(summary))
    handoff = out / "V16E11_R2_Recovery_Handoff.md"
    handoff.write_text(
        "# PAD-Stream V16E-11-R2 — Packed-SG5 Frozen Artifact Recovery\n\n"
        "The exact Version-15 7x7 SG5/SG6/SG7C artifacts were copied byte-for-byte from the recorded frozen local workspace into persistent Drive storage. No pressure, Darcy, Pollock, TOF, SG7A truth, training, checkpoint, or grid-mapback calculation was repeated. The original blocked V16E-11 record remains immutable.\n\n"
        f"Recovery audit SHA: {sha256_file(audit_path)}\n"
        f"V16E-11-R2 pilot exit code: {e11_exit_code}\n",
        encoding="utf-8",
    )
    print("Recovery audit SHA:", sha256_file(audit_path))
    print("Recovery summary SHA:", sha256_file(summary_path))
    print("Recovery handoff SHA:", sha256_file(handoff))
    return out


def install_and_rerun(bundle: Path, project: Path, drive: Path) -> int:
    bundle, project, drive = bundle.resolve(), project.resolve(), drive.resolve()
    print("=" * 110)
    print("PAD-Stream V16E-11-R2 - COLAB PACKED-SG5 ARTIFACT REBIND + REPAIRED PILOT")
    print("=" * 110)
    print("NO RECOMPUTATION. ORIGINAL E11 BLOCKED EVIDENCE IS PRESERVED.\n")
    original_e11 = project / "PAD_Stream_V16E11_SGSim_100Day_Path_State_Eligibility_and_Controlled_Hybrid_Streamline_Pilot.py"
    r1 = project / "PAD_Stream_V16E11_R1_Frozen_SGSim_Artifact_Recovery_and_Rebind.py"
    e11r2 = project / "PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
    for path, expected, label in [
        (original_e11, EXPECTED_ORIGINAL_E11_RUNNER_SHA256, "original E11"),
        (r1, EXPECTED_R1_RUNNER_SHA256, "R1 recovery"),
        (e11r2, EXPECTED_E11R2_RUNNER_SHA256, "repaired E11-R2"),
    ]:
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"{label} runner SHA mismatch\nexpected={expected}\nactual={actual}")
    blocked = bind_blocked_evidence(drive)
    print("[PASS] Original E11 blocked report SHA exact:", blocked)

    with tempfile.TemporaryDirectory(prefix="v16e11r1_bundle_") as tmp:
        extracted = Path(tmp) / "bundle"
        extracted.mkdir()
        manifest = safe_extract_bundle(bundle, extracted)
        verify_manifest_tree(extracted, manifest)
        # Re-run the same numerical/artifact validation on the transferred bytes.
        # The basename check is applied to the final recovered workspace below.
        sg5_validation = validate_sg5(extracted / REQUIRED[0])
        sg6_validation = validate_sg6(extracted / REQUIRED[1])
        sg7c_validation = validate_sg7c(extracted / REQUIRED[2])
        print("[PASS] Uploaded bundle hashes exact")
        print("[PASS] Uploaded SG5 packed source-native 1078-streamline schema")
        print("[PASS] Uploaded SG6 1078x201 frozen-reference schema")
        print("[PASS] Uploaded SG7C exact 100-day SG7A truth carrier")

        recovered_workspace = drive / DRIVE_RECOVERED_REL
        copy_exact_tree(extracted, recovered_workspace, manifest)
        # Exact final workspace identity expected by the frozen E11 preference rule.
        if "07x07" not in recovered_workspace.name.lower() and "7x7" not in recovered_workspace.name.lower():
            raise RuntimeError("Recovered workspace path must retain explicit 07x07 provenance label")
        # Validate final copied tree in place (without requiring legacy basename).
        validate_sg5(recovered_workspace / REQUIRED[0])
        validate_sg6(recovered_workspace / REQUIRED[1])
        validate_sg7c(recovered_workspace / REQUIRED[2])
        print("[PASS] Frozen artifact bytes copied to Drive without mutation")
        print("Recovered workspace:", recovered_workspace)

        cmd = [
            sys.executable, "-u", str(e11r2),
            "--project-root", str(project),
            "--drive-root", str(drive),
            "--sgsim-workspace", str(recovered_workspace),
        ]
        print("\nRUNNING V16E-11-R2 WITH EXACT PACKED-SG5 DESERIALIZATION REPAIR\n", flush=True)
        with subprocess.Popen(
            cmd,
            cwd=project,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as proc:
            assert proc.stdout is not None
            for line in proc.stdout:
                print(line, end="", flush=True)
            exit_code = proc.wait()

        # Persist the validated values from the uploaded copy in the manifest record.
        manifest = dict(manifest)
        manifest["validation_after_upload"] = {
            "sg5": sg5_validation,
            "sg6": sg6_validation,
            "sg7c": sg7c_validation,
        }
        out = publish_recovery(drive, bundle, manifest, recovered_workspace, exit_code)
        print("Recovery provenance output:", out)
        print("V16E-11-R2 exit code:", exit_code)
        return int(exit_code)


def default_local_workspace() -> Path:
    return Path.home() / "PycharmProjects" / WORKSPACE_BASENAME


def default_local_bundle() -> Path:
    return Path.home() / "Downloads" / "V16E11R2_Frozen_SGSim_Artifact_Bundle.zip"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    p_pack = sub.add_parser("pack", help="Validate the exact frozen Windows workspace and create a transfer ZIP")
    p_pack.add_argument("--workspace", type=Path, default=default_local_workspace())
    p_pack.add_argument("--output-zip", type=Path, default=default_local_bundle())

    p_install = sub.add_parser("install-and-rerun", help="Bind an uploaded frozen artifact ZIP in Drive and run repaired E11-R2")
    p_install.add_argument("--bundle", type=Path, required=True)
    p_install.add_argument("--project-root", type=Path, default=Path("/content/PAD-Stream"))
    p_install.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))

    args = parser.parse_args(argv)
    try:
        if args.mode == "pack":
            return build_bundle(args.workspace, args.output_zip)
        if args.mode == "install-and-rerun":
            return install_and_rerun(args.bundle, args.project_root, args.drive_root)
        raise RuntimeError(f"Unknown mode {args.mode}")
    except (RuntimeError, FileNotFoundError, OSError, ValueError, KeyError, AssertionError) as exc:
        print(f"\n[FAIL] {MILESTONE}: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
