#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV4-PIVOT-GPU-HYB-G1"
NAME = "Controlled GPU Runtime / Existing 100-Day Hybrid BL-DP Single-State Replay Certification"
PASS = "POSTV16AV4PIVOTGPUHYBG1_CONTROLLED_100DAY_GPU_REPLAY_CERTIFICATION_PASS_NO_PHYSICAL_TIME_ADVANCE"
BLOCK = "POSTV16AV4PIVOTGPUHYBG1_GPU_REPLAY_TECHNICAL_OR_FIDELITY_BLOCK_NO_PHYSICAL_TIME_ADVANCE"

BRANCH = "postv16-av4-pivot"
PARENT = "a27d59776936282094b41dc7c7ee82cfde7874f8"  # GPU-HYB-G0

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

# G0 authority
G0_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G0_Cadence_Aware_Hybrid_BL_DP_Integration_Contract_Freeze.py"
G0_RUNNER_BLOB = "433ff6da2b68fe234576e1513ce4ffaed1ed61e3"
G0_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_GPU_HYB_G0_Cadence_Aware_Hybrid_BLDP_Integration_Contract_Freeze"
G0_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G0_Summary.json"
G0_HANDOFF = "POSTV16_AV4_PIVOT_GPU_HYB_G0_G1_Handoff_Contract.json"
G0_DECISION = "POSTV16_AV4_PIVOT_GPU_HYB_G0_Decision_Contract.json"
G0_MANIFEST = "POSTV16_AV4_PIVOT_GPU_HYB_G0_Artifact_Manifest.csv"
G0_STATUS = "POSTV16AV4PIVOTGPUHYBG0_CADENCE_AWARE_HYBRID_BLDP_INTEGRATION_CONTRACT_FREEZE_PASS_NO_PHYSICS_EXECUTION"

# Frozen E11-R2 reference and exact runner authority
E11_RUNNER = "PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
E11_RUNNER_SHA256 = "0363a09612c5e80f6bb8124c817ca0d3726b1654283ab169c9b2d4d9861707b7"
E11_RUNNER_BLOB = "bf89c14a3cb177fb483e233a17b72e824d31119b"
E11_REL = Path("pilots/hybrid_dp/V16E11_R2_SGSIM_100D_CONTROLLED_STREAMLINE_PILOT")
E11_PILOT = "V16E11_R2_SGSim_100Day_Streamline_Pilot.npz"
E11_PILOT_SHA256 = "710720e933d740787868a9894fa04f90e88429c120d9f86a52b750f4c41db844"
E11_SUMMARY = "PAD_Stream_V16E11_R2_Summary.json"
E11_SUMMARY_SHA256 = "76336276daf4a506ea7e0880a6ad2e2852724deaf4623ca3945eafbf029e4243"

EXPECTED_NSTREAM = 1078
EXPECTED_NXI = 201
EXPECTED_ROUTE_COUNTS = {
    "HYBRID10_ACCEPT": 462,
    "HYBRID12_ACCEPT": 0,
    "EXACT_R2_FALLBACK": 41,
    "FULL_PHYSICS_SG7A_FALLBACK": 575,
}
EXPECTED_EARLY_PROBES = [[75, 80], [120, 125], [40, 45]]

# Replay numerical tolerance is based only on float32 machine precision.
FLOAT32_EPS = float(np.finfo(np.float32).eps)
REPLAY_ATOL = 32.0 * FLOAT32_EPS
REPLAY_RTOL = 32.0 * FLOAT32_EPS

OUT_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G1"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_Controlled_100Day_GPU_Replay_Certification")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
AUDIT = f"{OUT_TOKEN}_Replay_Fidelity_Audit.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"
REPLAY_DIRNAME = "E11_R2_GPU_REPLAY"

class GateError(RuntimeError):
    pass

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
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
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def verify_manifest(directory: Path, filename: str) -> dict[str, str]:
    rows = csv_rows(directory / filename)
    if not rows:
        raise GateError(f"manifest_empty:{directory / filename}")
    out = {}
    for row in rows:
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        actual = sha256(p)
        if actual != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        out[p.name] = actual
    return out

def route_counts(code: np.ndarray) -> dict[str, int]:
    return {
        "HYBRID10_ACCEPT": int(np.sum(code == 10)),
        "HYBRID12_ACCEPT": int(np.sum(code == 12)),
        "EXACT_R2_FALLBACK": int(np.sum(code == 20)),
        "FULL_PHYSICS_SG7A_FALLBACK": int(np.sum(code == 30)),
    }

def gpu_probe() -> dict[str, Any]:
    info: dict[str, Any] = {
        "nvidia_smi_ok": False,
        "gpu_name": None,
        "tensorflow_probe_ok": False,
        "tensorflow_version": None,
        "tensorflow_gpu_devices": [],
    }
    try:
        p = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            text=True, capture_output=True, check=True
        )
        names = [x.strip() for x in p.stdout.splitlines() if x.strip()]
        info["nvidia_smi_ok"] = bool(names)
        info["gpu_name"] = names[0] if names else None
    except Exception as exc:
        info["nvidia_smi_error"] = repr(exc)

    code = (
        "import json, tensorflow as tf;"
        "print(json.dumps({'version':tf.__version__,"
        "'gpus':[d.name for d in tf.config.list_physical_devices(\"GPU\")]}))"
    )
    try:
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = "0"
        p = subprocess.run([sys.executable, "-c", code], text=True, capture_output=True, check=True, env=env)
        payload = json.loads(p.stdout.strip().splitlines()[-1])
        info["tensorflow_probe_ok"] = True
        info["tensorflow_version"] = payload["version"]
        info["tensorflow_gpu_devices"] = payload["gpus"]
    except Exception as exc:
        info["tensorflow_probe_error"] = repr(exc)
    return info

def compare_npz(reference_path: Path, replay_path: Path) -> dict[str, Any]:
    with np.load(reference_path, allow_pickle=False) as a, np.load(replay_path, allow_pickle=False) as b:
        ka, kb = sorted(a.files), sorted(b.files)
        if ka != kb:
            raise GateError(f"replay_key_set_mismatch:{ka}:{kb}")

        exact_keys = []
        nonexact_keys = []
        details: dict[str, Any] = {}
        for key in ka:
            aa = np.asarray(a[key])
            bb = np.asarray(b[key])
            same_shape = aa.shape == bb.shape
            exact = same_shape and np.array_equal(aa, bb)
            if exact:
                exact_keys.append(key)
            else:
                nonexact_keys.append(key)
            details[key] = {
                "shape_reference": list(aa.shape),
                "shape_replay": list(bb.shape),
                "dtype_reference": str(aa.dtype),
                "dtype_replay": str(bb.dtype),
                "exact_array_equal": bool(exact),
            }

        # All non-saturation arrays are frozen interface / route evidence and must be exact.
        required_exact = [k for k in ka if k != "saturation_100d"]
        exact_interface = all(details[k]["exact_array_equal"] for k in required_exact)

        sa = np.asarray(a["saturation_100d"], dtype=np.float32)
        sb = np.asarray(b["saturation_100d"], dtype=np.float32)
        diff = sb.astype(np.float64) - sa.astype(np.float64)
        sat_exact = np.array_equal(sa, sb)
        sat_allclose = np.allclose(sa, sb, rtol=REPLAY_RTOL, atol=REPLAY_ATOL, equal_nan=False)
        sat_max_abs = float(np.max(np.abs(diff)))
        sat_rmse = float(np.sqrt(np.mean(diff * diff)))
        denom = float(np.linalg.norm(sa.astype(np.float64).ravel()))
        sat_rel_l2 = float(np.linalg.norm(diff.ravel()) / denom) if denom > 0 else 0.0

        route_ref = np.asarray(a["route_code"])
        route_rep = np.asarray(b["route_code"])
        screen_ref = np.asarray(a["learned_screen_pass"])
        screen_rep = np.asarray(b["learned_screen_pass"])

        learned_mask = route_ref == 10
        fallback_mask = ~learned_mask
        learned_max_abs = float(np.max(np.abs(diff[learned_mask]))) if np.any(learned_mask) else 0.0
        fallback_exact = bool(np.array_equal(sa[fallback_mask], sb[fallback_mask]))

        return {
            "key_set_exact": True,
            "all_non_saturation_arrays_exact": bool(exact_interface),
            "exact_keys": exact_keys,
            "nonexact_keys": nonexact_keys,
            "route_code_exact": bool(np.array_equal(route_ref, route_rep)),
            "route_counts_reference": route_counts(route_ref),
            "route_counts_replay": route_counts(route_rep),
            "learned_screen_pass_exact": bool(np.array_equal(screen_ref, screen_rep)),
            "saturation_exact_array_equal": bool(sat_exact),
            "saturation_allclose_float32_machine_precision_contract": bool(sat_allclose),
            "saturation_replay_atol": REPLAY_ATOL,
            "saturation_replay_rtol": REPLAY_RTOL,
            "saturation_max_abs": sat_max_abs,
            "saturation_rmse": sat_rmse,
            "saturation_relative_L2": sat_rel_l2,
            "learned_route_saturation_max_abs": learned_max_abs,
            "nonlearned_fallback_saturation_exact": fallback_exact,
        }

def selftest() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        a = p / "a.npz"
        b = p / "b.npz"
        keys = dict(
            route_code=np.array([10,20,30], dtype=np.int16),
            learned_screen_pass=np.array([1,0,0], dtype=np.uint8),
            xi=np.array([0.0,1.0], dtype=np.float64),
            saturation_100d=np.array([[0.2,0.5],[0.2,0.4],[0.2,0.3]], dtype=np.float32),
        )
        np.savez_compressed(a, **keys)
        keys2 = {k: np.array(v, copy=True) for k,v in keys.items()}
        keys2["saturation_100d"][0,1] += np.float32(FLOAT32_EPS)
        np.savez_compressed(b, **keys2)
        d = compare_npz(a,b)
        assert d["all_non_saturation_arrays_exact"]
        assert d["route_code_exact"]
        assert d["saturation_allclose_float32_machine_precision_contract"]
    print("POSTV16 GPU-HYB-G1 structural/replay self-test: PASS")

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
        print("=" * 190)
        print("POSTV16-AV4-PIVOT-GPU-HYB-G1 — CONTROLLED 100-DAY HYBRID BL-DP GPU REPLAY CERTIFICATION")
        print("GPU INFERENCE REPLAY ONLY. NO NEW PHYSICAL TIME ADVANCE. NO PRESSURE/DARCY/POLLOCK/TOF RECOMPUTATION. NO MAP-BACK.")
        print("=" * 190)

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_GPU_HYB_G0_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        g0runner = root / G0_RUNNER
        gate("G0_runner_present", g0runner.is_file())
        gate("G0_runner_blob_exact", gt(root, "hash-object", str(g0runner)) == G0_RUNNER_BLOB,
             gt(root, "hash-object", str(g0runner)) if g0runner.is_file() else "missing")

        e11runner = root / E11_RUNNER
        gate("E11_R2_runner_present", e11runner.is_file())
        gate("E11_R2_runner_sha256_exact", sha256(e11runner) == E11_RUNNER_SHA256,
             sha256(e11runner) if e11runner.is_file() else "missing")
        gate("E11_R2_runner_blob_exact", gt(root, "hash-object", str(e11runner)) == E11_RUNNER_BLOB,
             gt(root, "hash-object", str(e11runner)) if e11runner.is_file() else "missing")

        stage = "G0_authority"
        g0dir = drive / G0_REL
        gate("G0_output_exists", g0dir.is_dir(), str(g0dir))
        for fn in [G0_SUMMARY, G0_HANDOFF, G0_DECISION, G0_MANIFEST]:
            gate(f"G0_artifact_present:{fn}", (g0dir / fn).is_file())
        verify_manifest(g0dir, G0_MANIFEST)
        g0s = js(g0dir / G0_SUMMARY)
        g0h = js(g0dir / G0_HANDOFF)
        g0d = js(g0dir / G0_DECISION)
        gate("G0_status_exact", g0s.get("status") == G0_STATUS, g0s.get("status"))
        gate("G0_G1_authorized", g0s.get("GPU_HYB_G1_authorized") is True)
        gate("G0_G2_locked", g0s.get("GPU_HYB_G2_authorized") is False)
        gate("G0_two_clock_frozen", g0s.get("two_clock_architecture_frozen") is True)
        gate("G0_flow_epoch_full_network", g0s.get("flow_epoch_is_full_pressure_flow_network_state") is True)
        gate("G0_handoff_authorized", g0h.get("authorized") is True)
        gate("G0_decision_G1_authorized", g0d.get("GPU_HYB_G1_single_state_replay_authorized") is True)
        gate("G0_P4_locked", g0d.get("P4_authorized") is False)

        stage = "frozen_E11_reference"
        e11dir = drive / E11_REL
        ref_pilot = e11dir / E11_PILOT
        ref_summary = e11dir / E11_SUMMARY
        gate("E11_reference_dir_exists", e11dir.is_dir(), str(e11dir))
        gate("E11_reference_pilot_present", ref_pilot.is_file())
        gate("E11_reference_pilot_sha_exact", sha256(ref_pilot) == E11_PILOT_SHA256,
             sha256(ref_pilot) if ref_pilot.is_file() else "missing")
        gate("E11_reference_summary_present", ref_summary.is_file())
        gate("E11_reference_summary_sha_exact", sha256(ref_summary) == E11_SUMMARY_SHA256,
             sha256(ref_summary) if ref_summary.is_file() else "missing")
        rs = js(ref_summary)
        gate("E11_reference_status_PASS", str(rs.get("status")).upper() == "PASS", rs.get("status"))
        gate("E11_reference_streamlines", int(rs.get("streamline_count",-1)) == EXPECTED_NSTREAM)
        gate("E11_reference_nodes", int(rs.get("transport_nodes",-1)) == EXPECTED_NXI)
        gate("E11_reference_100d", float(rs.get("physical_time_days",-1)) == 100.0)
        gate("E11_reference_zero_unsafe", int(rs.get("unsafe_learned_proposals_accepted",-1)) == 0)

        stage = "GPU_runtime"
        gpu = gpu_probe()
        gate("nvidia_gpu_visible", gpu.get("nvidia_smi_ok") is True, gpu)
        gate("tensorflow_gpu_visible", gpu.get("tensorflow_probe_ok") is True and len(gpu.get("tensorflow_gpu_devices",[])) >= 1, gpu)
        gate("tensorflow_2_20_exact", gpu.get("tensorflow_version") == "2.20.0", gpu.get("tensorflow_version"))

        stage = "fresh_E11_GPU_replay"
        gate("output_does_not_preexist", not out.exists(), str(out))
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=False)
        replay_dir = staging / REPLAY_DIRNAME

        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = "0"
        env["TF_DETERMINISTIC_OPS"] = "1"
        env["TF_CUDNN_DETERMINISTIC"] = "1"
        cmd = [
            sys.executable, str(e11runner),
            "--project-root", str(root),
            "--drive-root", str(drive),
            "--output-dir", str(replay_dir),
        ]
        print("Executing exact immutable E11-R2 runner into fresh G1 replay directory...", flush=True)
        proc = subprocess.run(cmd, env=env)
        gate("E11_R2_replay_exit_zero", proc.returncode == 0, proc.returncode)
        replay_pilot = replay_dir / E11_PILOT
        replay_summary = replay_dir / E11_SUMMARY
        gate("replay_pilot_present", replay_pilot.is_file())
        gate("replay_summary_present", replay_summary.is_file())

        rps = js(replay_summary)
        gate("replay_status_PASS", str(rps.get("status")).upper() == "PASS", rps.get("status"))
        gate("replay_zero_unsafe", int(rps.get("unsafe_learned_proposals_accepted",-1)) == 0,
             rps.get("unsafe_learned_proposals_accepted"))
        gate("replay_no_pressure_flow_recompute", rps.get("pressure_Darcy_Pollock_TOF_recomputed") is False)
        gate("replay_no_mapback", rps.get("grid_mapback_performed") is False)

        stage = "replay_fidelity"
        audit = compare_npz(ref_pilot, replay_pilot)
        gate("NPZ_key_set_exact", audit["key_set_exact"])
        gate("all_non_saturation_arrays_exact", audit["all_non_saturation_arrays_exact"], audit["nonexact_keys"])
        gate("route_code_exact", audit["route_code_exact"])
        gate("route_counts_reference_exact", audit["route_counts_reference"] == EXPECTED_ROUTE_COUNTS, audit["route_counts_reference"])
        gate("route_counts_replay_exact", audit["route_counts_replay"] == EXPECTED_ROUTE_COUNTS, audit["route_counts_replay"])
        gate("learned_screen_pass_exact", audit["learned_screen_pass_exact"])
        gate("nonlearned_fallback_saturation_exact", audit["nonlearned_fallback_saturation_exact"])
        gate("saturation_float32_replay_contract_PASS",
             audit["saturation_allclose_float32_machine_precision_contract"], audit)
        gate("AV4_physical_time_not_advanced", g0s.get("Day405_to_Day410_transport_executed") is False)
        gate("P4_still_locked", g0s.get("P4_authorized") is False)

        # Persist replay audit and promote staging atomically.
        audit_out = {
            "milestone": M,
            "status": PASS,
            "GPU_runtime": gpu,
            "reference_E11_pilot_sha256": E11_PILOT_SHA256,
            "replay_E11_pilot_sha256": sha256(replay_pilot),
            "E11_runner_sha256": E11_RUNNER_SHA256,
            "E11_runner_git_blob": E11_RUNNER_BLOB,
            "comparison_contract": {
                "all_non_saturation_arrays": "exact np.array_equal",
                "route_code_and_screen_decisions": "exact",
                "nonlearned_fallback_saturation": "exact",
                "learned_saturation": "np.allclose using 32*float32 machine epsilon for both atol and rtol",
                "float32_epsilon": FLOAT32_EPS,
                "atol": REPLAY_ATOL,
                "rtol": REPLAY_RTOL,
                "scientific_tolerance_tuned": False,
            },
            "fidelity": audit,
        }
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": "FROZEN_E11_R2_100DAY_HYBRID_SGSIM_STATE_REPRODUCED_ON_GPU_WITH_EXACT_ROUTE_SCREEN_AND_MACHINE_PRECISION_SATURATION_FIDELITY_G2_AUTHORIZED",
            "GPU_HYB_G2_early_contiguous_trajectory_authorized": True,
            "GPU_HYB_G2_targeted_early_probe_execution_authorized": True,
            "GPU_HYB_G2_required_probe_pairs": EXPECTED_EARLY_PROBES,
            "GPU_HYB_G2_reference_truth_requires_exact_FV_pressure": True,
            "GPU_HYB_G2_reference_truth_requires_exact_Darcy_Pollock_TOF": True,
            "learned_pressure_seed_can_define_reference_truth": False,
            "production_pressure_refresh_cadence_selected": False,
            "brute_force_Day30_to_Day365_five_day_sweep_authorized": False,
            "Day405_to_Day410_transport_remains_authorized": True,
            "Day405_to_Day410_transport_executed": False,
            "P4_authorized": False,
            "recommended_next_action": (
                "Build G2 as a cadence-aware early GPU BL/Hybrid-DP reference-trajectory execution plan. "
                "Generate only the state history required to reach the frozen targeted probe pairs and exact diagnostic "
                "anchors; do not authorize a uniform five-day Day30-to-Day365 sweep."
            ),
        }
        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": decision["classification"],
            "repository_parent_GPU_HYB_G0_commit": PARENT,
            "GPU_name": gpu.get("gpu_name"),
            "TensorFlow_version": gpu.get("tensorflow_version"),
            "TensorFlow_GPU_devices": gpu.get("tensorflow_gpu_devices"),
            "E11_R2_exact_runner_reexecuted": True,
            "E11_R2_replay_exit_zero": True,
            "route_code_exact": audit["route_code_exact"],
            "learned_screen_pass_exact": audit["learned_screen_pass_exact"],
            "all_non_saturation_arrays_exact": audit["all_non_saturation_arrays_exact"],
            "nonlearned_fallback_saturation_exact": audit["nonlearned_fallback_saturation_exact"],
            "saturation_exact_array_equal": audit["saturation_exact_array_equal"],
            "saturation_machine_precision_replay_PASS": audit["saturation_allclose_float32_machine_precision_contract"],
            "saturation_max_abs": audit["saturation_max_abs"],
            "saturation_RMSE": audit["saturation_rmse"],
            "saturation_relative_L2": audit["saturation_relative_L2"],
            "late_time_evidence_bracket_days": [5,15],
            "early_target_pairs": EXPECTED_EARLY_PROBES,
            "GPU_HYB_G2_authorized": True,
            "production_pressure_refresh_cadence_selected": False,
            "new_pressure_solve_executed": False,
            "Darcy_recomputation_executed": False,
            "Pollock_retracing_executed": False,
            "TOF_recomputation_executed": False,
            "streamline_to_grid_mapback_executed": False,
            "new_physical_time_advance_executed": False,
            "AV4_authoritative_state_mutated": False,
            "Day405_to_Day410_transport_executed": False,
            "Day405_to_Day410_transport_remains_authorized": True,
            "P4_authorized": False,
        }

        (staging / AUDIT).write_text(json.dumps(audit_out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (staging / DECISION).write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (staging / SUMMARY).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_csv(staging / GATES, gates)

        manifest_rows = []
        for p in sorted(staging.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                manifest_rows.append({"file": p.name, "sha256": sha256(p), "bytes": p.stat().st_size})
        # Replay subdirectory is intentionally included as a reference output tree but not duplicated in flat manifest.
        manifest_rows.append({
            "file": f"{REPLAY_DIRNAME}/{E11_PILOT}",
            "sha256": sha256(replay_pilot),
            "bytes": replay_pilot.stat().st_size,
        })
        manifest_rows.append({
            "file": f"{REPLAY_DIRNAME}/{E11_SUMMARY}",
            "sha256": sha256(replay_summary),
            "bytes": replay_summary.stat().st_size,
        })
        write_csv(staging / MANIFEST, manifest_rows)

        staging.rename(out)

        print("=" * 190)
        print(M, "PASS")
        print("GPU                                                :", gpu.get("gpu_name"))
        print("TensorFlow                                         :", gpu.get("tensorflow_version"))
        print("Exact route_code replay                            :", audit["route_code_exact"])
        print("Exact learned screen decisions                     :", audit["learned_screen_pass_exact"])
        print("All non-saturation arrays exact                    :", audit["all_non_saturation_arrays_exact"])
        print("Nonlearned fallback saturation exact               :", audit["nonlearned_fallback_saturation_exact"])
        print("Saturation exact array equality                    :", audit["saturation_exact_array_equal"])
        print("Saturation machine-precision replay PASS           :", audit["saturation_allclose_float32_machine_precision_contract"])
        print("Saturation max abs / RMSE / relative L2            :",
              audit["saturation_max_abs"], audit["saturation_rmse"], audit["saturation_relative_L2"])
        print("New pressure/Darcy/Pollock/TOF                     : False / False / False / False")
        print("New physical time advance                          : False")
        print("G2 early contiguous trajectory authorized          : True")
        print("Production cadence selected                        : False")
        print("Day405->Day410 remains authorized                  : True")
        print("P4 authorized                                      : False")
        print("Output directory                                   :", out)
        print("=" * 190)
        return 0

    except Exception as exc:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": M,
            "status": BLOCK,
            "failed_stage": stage,
            "exception": repr(exc),
            "GPU_HYB_G2_authorized": False,
            "new_pressure_solve_executed": False,
            "Darcy_recomputation_executed": False,
            "Pollock_retracing_executed": False,
            "TOF_recomputation_executed": False,
            "streamline_to_grid_mapback_executed": False,
            "new_physical_time_advance_executed": False,
            "AV4_authoritative_state_mutated": False,
            "P4_authorized": False,
            "gates_completed": gates,
        }
        (blocked / f"{OUT_TOKEN}_Blocked_Report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(M, "TECHNICAL / FIDELITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
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
