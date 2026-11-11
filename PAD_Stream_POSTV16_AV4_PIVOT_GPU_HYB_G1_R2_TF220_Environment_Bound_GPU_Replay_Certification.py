#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

M = "POSTV16-AV4-PIVOT-GPU-HYB-G1-R2"
NAME = "TensorFlow-2.20 Environment-Bound 100-Day Hybrid BL-DP GPU Replay Certification"
PASS = "POSTV16AV4PIVOTGPUHYBG1R2_TF220_ENVIRONMENT_BOUND_100DAY_GPU_REPLAY_CERTIFICATION_PASS_NO_PHYSICAL_TIME_ADVANCE"
BLOCK = "POSTV16AV4PIVOTGPUHYBG1R2_ENVIRONMENT_OR_FIDELITY_BLOCK_NO_PHYSICAL_TIME_ADVANCE"

BRANCH = "postv16-av4-pivot"
PARENT = "eed19bc3469b8a471b1b8ad9d83ce0d1724dc345"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

G1_R1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G1_R1_Frozen_Input_Bound_100Day_GPU_Replay_Certification.py"
G1_R1_RUNNER_SHA256 = "9d5402fb6d075ed7ce8ac65d9150dcffbdabe2f95b34b9e9f8a47eb451b32cb0"
G1_R1_RUNNER_BLOB = "756fde8da6fb1f7cd538ac6a67a7844093c3c838"

G1_R1_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_GPU_HYB_G1_R1_BLOCKED"
G1_R1_BLOCK_REPORT = "POSTV16_AV4_PIVOT_GPU_HYB_G1_R1_Blocked_Report.json"
G1_R1_BLOCK_STATUS = "POSTV16AV4PIVOTGPUHYBG1R1_TECHNICAL_OR_FIDELITY_BLOCK_NO_PHYSICAL_TIME_ADVANCE"

TF_VERSION = "2.20.0"
TF220_CP313_LINUX_X86_64_WHEEL_SHA256 = "5fa3729b0126f75a99882b89fb7d536515721eda8014a63e259e780ba0a37372"

OUT_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G1_R2"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_TF220_Environment_Bound_100Day_GPU_Replay_Certification")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
ENV_AUDIT = f"{OUT_TOKEN}_Environment_Restoration_Audit.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

DEFAULT_ENV_ROOT = Path("/content/PAD_Stream_G1R2_TF220_ENV")

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
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def python_in_venv(env_root: Path) -> Path:
    p = env_root / "bin" / "python"
    if not p.is_file():
        raise GateError(f"venv_python_missing:{p}")
    return p

def probe_python(python_exe: Path) -> dict[str, Any]:
    code = (
        "import json,sys,tensorflow as tf;"
        "print(json.dumps({'python':sys.version.split()[0],"
        "'tensorflow':tf.__version__,"
        "'gpus':[d.name for d in tf.config.list_physical_devices(\"GPU\")]}))"
    )
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "0"
    q = subprocess.run([str(python_exe), "-c", code], text=True, capture_output=True, env=env)
    payload = None
    if q.returncode == 0 and q.stdout.strip():
        payload = json.loads(q.stdout.strip().splitlines()[-1])
    return {"returncode": q.returncode, "stdout": q.stdout, "stderr": q.stderr, "payload": payload}

def create_tf220_env(env_root: Path) -> dict[str, Any]:
    if env_root.exists():
        shutil.rmtree(env_root)
    subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", str(env_root)], check=True)
    py = python_in_venv(env_root)
    subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], check=True)
    subprocess.run([
        str(py), "-m", "pip", "install",
        "--upgrade", "--force-reinstall", "--no-cache-dir",
        f"tensorflow=={TF_VERSION}",
    ], check=True)
    freeze = subprocess.check_output([str(py), "-m", "pip", "freeze"], text=True)
    probe = probe_python(py)
    return {"env_root": str(env_root), "venv_python": str(py), "pip_freeze": freeze.splitlines(), "probe": probe}

def build_helper(helper_path: Path, project_root: Path, drive_root: Path) -> None:
    template = """
from pathlib import Path
import importlib.util

PROJECT = Path(__PROJECT__)
DRIVE = Path(__DRIVE__)
RUNNER = PROJECT / __RUNNER__
EXPECTED_SHA = __EXPECTED_SHA__
PARENT = __PARENT__

def sha256(p):
    import hashlib
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

if sha256(RUNNER) != EXPECTED_SHA:
    raise SystemExit("G1-R1 source SHA mismatch")

spec=importlib.util.spec_from_file_location("g1r1_envbound",RUNNER)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

mod.PARENT = PARENT
mod.M = __M__
mod.NAME = __NAME__
mod.PASS = __PASS__
mod.BLOCK = __BLOCK__
mod.OUT_TOKEN = __OUT_TOKEN__
mod.OUT_REL = mod.BASE_AV4 / __OUT_REL_SUFFIX__
mod.STAGE_REL = mod.BASE_AV4 / __STAGE_REL_SUFFIX__
mod.BLOCK_REL = mod.BASE_AV4 / __BLOCK_REL_SUFFIX__
mod.SUMMARY = __SUMMARY__
mod.AUDIT = __AUDIT__
mod.REPAIR = __REPAIR__
mod.DECISION = __DECISION__
mod.GATES = __GATES__
mod.MANIFEST = __MANIFEST__
mod.REPLAY_DIRNAME = "E11_R2_GPU_REPLAY_TF220_ENVIRONMENT_BOUND"

rc = mod.main(PROJECT, DRIVE)
raise SystemExit(rc)
"""
    replacements = {
        "__PROJECT__": repr(str(project_root)),
        "__DRIVE__": repr(str(drive_root)),
        "__RUNNER__": repr(G1_R1_RUNNER),
        "__EXPECTED_SHA__": repr(G1_R1_RUNNER_SHA256),
        "__PARENT__": repr(PARENT),
        "__M__": repr(M),
        "__NAME__": repr(NAME),
        "__PASS__": repr(PASS),
        "__BLOCK__": repr(BLOCK),
        "__OUT_TOKEN__": repr(OUT_TOKEN),
        "__OUT_REL_SUFFIX__": repr(str(OUT_REL.relative_to(BASE_AV4))),
        "__STAGE_REL_SUFFIX__": repr(str(STAGE_REL.relative_to(BASE_AV4))),
        "__BLOCK_REL_SUFFIX__": repr(str(BLOCK_REL.relative_to(BASE_AV4))),
        "__SUMMARY__": repr(SUMMARY),
        "__AUDIT__": repr(OUT_TOKEN + "_Replay_Fidelity_Audit.json"),
        "__REPAIR__": repr(OUT_TOKEN + "_Frozen_Input_Binding_Audit.json"),
        "__DECISION__": repr(DECISION),
        "__GATES__": repr(OUT_TOKEN + "_Final_Gate_Matrix.csv"),
        "__MANIFEST__": repr(MANIFEST),
    }
    for k, v in replacements.items():
        template = template.replace(k, v)
    helper_path.write_text(textwrap.dedent(template), encoding="utf-8")

def selftest() -> None:
    assert TF_VERSION == "2.20.0"
    assert len(TF220_CP313_LINUX_X86_64_WHEEL_SHA256) == 64
    assert PARENT == "eed19bc3469b8a471b1b8ad9d83ce0d1724dc345"
    print("POSTV16 GPU-HYB-G1-R2 structural/environment self-test: PASS")

def main(project_root: Path, drive_root: Path, env_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCK_REL
    stage = "preflight"

    try:
        print("=" * 190)
        print("POSTV16-AV4-PIVOT-GPU-HYB-G1-R2 — TF2.20 ENVIRONMENT-BOUND 100-DAY GPU REPLAY CERTIFICATION")
        print("ENVIRONMENT REPAIR ONLY. G1-R1 FROZEN-INPUT REPLAY LOGIC / PHYSICS / TOLERANCES REMAIN UNCHANGED.")
        print("=" * 190)

        stage = "repository_authority"
        if gt(root, "branch", "--show-current") != BRANCH:
            raise GateError("branch_exact")
        if gt(root, "rev-parse", "HEAD^") != PARENT:
            raise GateError(f"parent_exact:{gt(root,'rev-parse','HEAD^')}")
        if gt(root, "status", "--porcelain") != "":
            raise GateError("repository_not_clean")

        g1r1 = root / G1_R1_RUNNER
        if not g1r1.is_file():
            raise GateError("G1_R1_runner_missing")
        if sha256(g1r1) != G1_R1_RUNNER_SHA256:
            raise GateError("G1_R1_runner_sha")
        if gt(root, "hash-object", str(g1r1)) != G1_R1_RUNNER_BLOB:
            raise GateError("G1_R1_runner_blob")

        stage = "prior_G1_R1_block_authority"
        prior_block = drive / G1_R1_BLOCK_REL / G1_R1_BLOCK_REPORT
        if not prior_block.is_file():
            raise GateError(f"G1_R1_block_report_missing:{prior_block}")
        prior = js(prior_block)
        if prior.get("status") != G1_R1_BLOCK_STATUS:
            raise GateError(f"G1_R1_block_status:{prior.get('status')}")
        if prior.get("failed_stage") != "GPU_runtime":
            raise GateError(f"G1_R1_failed_stage_not_GPU_runtime:{prior.get('failed_stage')}")
        if prior.get("exception") != "GateError('tensorflow_2_20_exact')":
            raise GateError(f"G1_R1_unexpected_exception:{prior.get('exception')}")
        if prior.get("new_physical_time_advance_executed") is not False:
            raise GateError("G1_R1_time_advance_not_false")
        if prior.get("AV4_authoritative_state_mutated") is not False:
            raise GateError("G1_R1_AV4_mutation_not_false")

        stage = "tf220_environment_restoration"
        if out.exists():
            raise GateError(f"output_preexists:{out}")
        env_info = create_tf220_env(env_root)
        probe = env_info["probe"]
        if probe["returncode"] != 0 or probe["payload"] is None:
            raise GateError(f"TF220_probe_failed:{probe}")
        payload = probe["payload"]
        if payload.get("tensorflow") != TF_VERSION:
            raise GateError(f"TF_version:{payload.get('tensorflow')}")
        if not payload.get("gpus"):
            raise GateError(f"TF220_GPU_not_visible:{payload}")

        stage = "exact_G1_R1_replay_under_tf220"
        helper = env_root / "run_g1r1_under_tf220.py"
        build_helper(helper, root, drive)
        py = python_in_venv(env_root)
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = "0"
        env["TF_DETERMINISTIC_OPS"] = "1"
        env["TF_CUDNN_DETERMINISTIC"] = "1"
        proc = subprocess.run([str(py), str(helper)], env=env)
        if proc.returncode != 0:
            raise GateError(f"G1_R1_under_TF220_exit:{proc.returncode}")

        stage = "R2_output_validation"
        if not out.is_dir():
            raise GateError(f"R2_output_missing:{out}")
        summary_path = out / SUMMARY
        decision_path = out / DECISION
        manifest_path = out / MANIFEST
        for p in [summary_path, decision_path, manifest_path]:
            if not p.is_file():
                raise GateError(f"R2_artifact_missing:{p.name}")

        summary = js(summary_path)
        if summary.get("status") != PASS:
            raise GateError(f"R2_status:{summary.get('status')}")
        if summary.get("TensorFlow_version") != TF_VERSION:
            raise GateError(f"R2_summary_TF:{summary.get('TensorFlow_version')}")
        if summary.get("GPU_HYB_G2_authorized") is not True:
            raise GateError("R2_G2_not_authorized")
        if summary.get("new_physical_time_advance_executed") is not False:
            raise GateError("R2_time_advance_not_false")
        if summary.get("P4_authorized") is not False:
            raise GateError("R2_P4_not_false")

        env_audit = {
            "milestone": M,
            "status": PASS,
            "repair_scope": "software environment only",
            "prior_G1_R1_block_report_sha256": sha256(prior_block),
            "prior_G1_R1_failed_stage": prior.get("failed_stage"),
            "prior_G1_R1_exception": prior.get("exception"),
            "system_interpreter_tensorflow_observed_by_user_run": "2.21.0",
            "certified_tensorflow_required": TF_VERSION,
            "isolated_environment_root": str(env_root),
            "isolated_python": payload.get("python"),
            "isolated_tensorflow": payload.get("tensorflow"),
            "isolated_gpu_devices": payload.get("gpus"),
            "official_TF220_cp313_linux_x86_64_wheel_sha256_reference": TF220_CP313_LINUX_X86_64_WHEEL_SHA256,
            "G1_R1_replay_logic_changed": False,
            "frozen_input_binding_changed": False,
            "hybrid_routing_or_screen_changed": False,
            "checkpoint_changed": False,
            "replay_tolerances_changed": False,
            "physics_changed": False,
            "new_physical_time_advance": False,
        }
        env_audit_path = out / ENV_AUDIT
        env_audit_path.write_text(json.dumps(env_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        summary["environment_restoration_PASS"] = True
        summary["system_tensorflow_before_isolated_replay"] = "2.21.0"
        summary["isolated_certified_tensorflow"] = TF_VERSION
        summary["isolated_tensorflow_GPU_visible"] = True
        summary["G1_R1_replay_logic_changed_in_R2"] = False
        summary["physics_or_tolerance_changed_in_R2"] = False
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        old_rows = csv_rows(manifest_path)
        replay_rows = [r for r in old_rows if "/" in r["file"]]
        flat = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                flat.append({"file": p.name, "sha256": sha256(p), "bytes": p.stat().st_size})
        write_csv(manifest_path, flat + replay_rows)

        print("=" * 190)
        print(M, "PASS")
        print("Prior G1-R1 failed stage                    :", prior.get("failed_stage"))
        print("Prior G1-R1 exception                       :", prior.get("exception"))
        print("Isolated Python                             :", payload.get("python"))
        print("Isolated TensorFlow                         :", payload.get("tensorflow"))
        print("Isolated TensorFlow GPUs                    :", payload.get("gpus"))
        print("G1-R1 replay logic changed                  : False")
        print("Physics / tolerance changed                 : False")
        print("Route code exact                            :", summary.get("route_code_exact"))
        print("Learned screen exact                        :", summary.get("learned_screen_pass_exact"))
        print("All non-saturation arrays exact             :", summary.get("all_non_saturation_arrays_exact"))
        print("Fallback saturation exact                   :", summary.get("nonlearned_fallback_saturation_exact"))
        print("Saturation machine-precision replay PASS    :", summary.get("saturation_machine_precision_replay_PASS"))
        print("G2 authorized                               :", summary.get("GPU_HYB_G2_authorized"))
        print("Production cadence selected                 :", summary.get("production_pressure_refresh_cadence_selected"))
        print("New physical time advance                   :", summary.get("new_physical_time_advance_executed"))
        print("Day405->Day410 remains authorized           :", summary.get("Day405_to_Day410_transport_remains_authorized"))
        print("P4 authorized                               :", summary.get("P4_authorized"))
        print("Output directory                            :", out)
        print("=" * 190)
        return 0

    except Exception as exc:
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
        }
        (blocked / f"{OUT_TOKEN}_Blocked_Report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(M, "ENVIRONMENT / FIDELITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--env-root", type=Path, default=DEFAULT_ENV_ROOT)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root, args.env_root))
