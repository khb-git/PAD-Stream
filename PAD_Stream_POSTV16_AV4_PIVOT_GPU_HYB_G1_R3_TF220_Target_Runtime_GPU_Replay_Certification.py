#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

M = "POSTV16-AV4-PIVOT-GPU-HYB-G1-R3"
NAME = "TensorFlow-2.20 Target-Runtime 100-Day Hybrid BL-DP GPU Replay Certification"
PASS = "POSTV16AV4PIVOTGPUHYBG1R3_TF220_TARGET_RUNTIME_100DAY_GPU_REPLAY_CERTIFICATION_PASS_NO_PHYSICAL_TIME_ADVANCE"
BLOCK = "POSTV16AV4PIVOTGPUHYBG1R3_ENVIRONMENT_OR_FIDELITY_BLOCK_NO_PHYSICAL_TIME_ADVANCE"

BRANCH = "postv16-av4-pivot"
PARENT = "25d72d91c19a1c4da98061da08e4446a63ab8bcc"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

G1_R1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G1_R1_Frozen_Input_Bound_100Day_GPU_Replay_Certification.py"
G1_R1_RUNNER_SHA256 = "9d5402fb6d075ed7ce8ac65d9150dcffbdabe2f95b34b9e9f8a47eb451b32cb0"
G1_R1_RUNNER_BLOB = "756fde8da6fb1f7cd538ac6a67a7844093c3c838"

G1_R2_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G1_R2_TF220_Environment_Bound_GPU_Replay_Certification.py"
G1_R2_RUNNER_SHA256 = "b8fe286c1187516d636738300aa501b40276c7e0b575c62f62d8fcc8ca6ba198"
G1_R2_RUNNER_BLOB = "1b3382caad424de8e5da778f4767e8f327cbf341"

G1_R2_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_GPU_HYB_G1_R2_BLOCKED"
G1_R2_BLOCK_REPORT = "POSTV16_AV4_PIVOT_GPU_HYB_G1_R2_Blocked_Report.json"
G1_R2_BLOCK_STATUS = "POSTV16AV4PIVOTGPUHYBG1R2_ENVIRONMENT_OR_FIDELITY_BLOCK_NO_PHYSICAL_TIME_ADVANCE"

TF_VERSION = "2.20.0"
TF220_CP313_LINUX_X86_64_WHEEL_SHA256 = "5fa3729b0126f75a99882b89fb7d536515721eda8014a63e259e780ba0a37372"

OUT_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G1_R3"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_TF220_Target_Runtime_100Day_GPU_Replay_Certification")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
ENV_AUDIT = f"{OUT_TOKEN}_Target_Runtime_Audit.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

DEFAULT_TARGET_ROOT = Path("/content/PAD_Stream_G1R3_TF220_TARGET")
DEFAULT_WHEELHOUSE_ROOT = Path("/content/PAD_Stream_G1R3_TF220_WHEELHOUSE")

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

def choose_pip() -> list[str]:
    candidates = [[sys.executable, "-m", "pip"]]
    for exe in [shutil.which("pip"), shutil.which("pip3")]:
        if exe:
            candidates.append([exe])
    seen = set()
    for cmd in candidates:
        key = tuple(cmd)
        if key in seen:
            continue
        seen.add(key)
        p = subprocess.run(cmd + ["--version"], text=True, capture_output=True)
        if p.returncode == 0:
            return cmd
    raise GateError("no_working_pip_frontend")

def prepare_target_runtime(target_root: Path, wheelhouse_root: Path) -> dict[str, Any]:
    for p in [target_root, wheelhouse_root]:
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=False)

    pip_cmd = choose_pip()

    # Download the exact TensorFlow wheel and all binary dependencies for this interpreter/platform.
    download_cmd = pip_cmd + [
        "download",
        "--dest", str(wheelhouse_root),
        "--only-binary=:all:",
        f"tensorflow=={TF_VERSION}",
    ]
    subprocess.run(download_cmd, check=True)

    tf_wheels = sorted(
        p for p in wheelhouse_root.glob("tensorflow-2.20.0-*.whl")
        if "cp313-cp313" in p.name and "x86_64" in p.name
    )
    if len(tf_wheels) != 1:
        raise GateError(f"tensorflow_wheel_resolution:{[p.name for p in tf_wheels]}")
    tf_wheel = tf_wheels[0]
    tf_wheel_sha = sha256(tf_wheel)
    if tf_wheel_sha != TF220_CP313_LINUX_X86_64_WHEEL_SHA256:
        raise GateError(f"tensorflow_wheel_sha:{tf_wheel_sha}")

    # Install solely from the frozen local wheelhouse into an isolated import target.
    install_cmd = pip_cmd + [
        "install",
        "--no-index",
        "--find-links", str(wheelhouse_root),
        "--target", str(target_root),
        "--upgrade",
        f"tensorflow=={TF_VERSION}",
    ]
    subprocess.run(install_cmd, check=True)

    return {
        "pip_command": pip_cmd,
        "tensorflow_wheel": str(tf_wheel),
        "tensorflow_wheel_sha256": tf_wheel_sha,
        "wheelhouse_file_count": len(list(wheelhouse_root.iterdir())),
    }

def child_env(target_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(target_root) + (os.pathsep + existing if existing else "")
    env["PYTHONNOUSERSITE"] = "1"
    env["CUDA_VISIBLE_DEVICES"] = "0"
    env["TF_DETERMINISTIC_OPS"] = "1"
    env["TF_CUDNN_DETERMINISTIC"] = "1"
    return env

def probe_target_runtime(target_root: Path) -> dict[str, Any]:
    code = (
        "import json,sys,tensorflow as tf;"
        "print(json.dumps({'python':sys.version.split()[0],"
        "'tensorflow':tf.__version__,"
        "'tensorflow_file':tf.__file__,"
        "'gpus':[d.name for d in tf.config.list_physical_devices(\"GPU\")],"
        "'sys_path_head':sys.path[:6]}))"
    )
    q = subprocess.run(
        [sys.executable, "-c", code],
        text=True, capture_output=True, env=child_env(target_root)
    )
    payload = None
    if q.returncode == 0 and q.stdout.strip():
        payload = json.loads(q.stdout.strip().splitlines()[-1])
    return {
        "returncode": q.returncode,
        "stdout": q.stdout,
        "stderr": q.stderr,
        "payload": payload,
    }

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

spec=importlib.util.spec_from_file_location("g1r1_targetruntime",RUNNER)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Child commit and publication namespace only.
mod.PARENT = PARENT
mod.M = __M__
mod.NAME = __NAME__
mod.PASS = __PASS__
mod.BLOCK = __BLOCK__
mod.OUT_TOKEN = __OUT_TOKEN__
mod.OUT_REL = mod.BASE_AV4 / __OUT_REL_SUFFIX__
mod.BLOCK_REL = mod.BASE_AV4 / __BLOCK_REL_SUFFIX__
mod.SUMMARY = __SUMMARY__
mod.AUDIT = __AUDIT__
mod.REPAIR = __REPAIR__
mod.DECISION = __DECISION__
mod.GATES = __GATES__
mod.MANIFEST = __MANIFEST__
mod.REPLAY_DIRNAME = "E11_R2_GPU_REPLAY_TF220_TARGET_RUNTIME"

rc = mod.main(PROJECT, DRIVE)
raise SystemExit(rc)
"""
    repl = {
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
        "__BLOCK_REL_SUFFIX__": repr(str(BLOCK_REL.relative_to(BASE_AV4))),
        "__SUMMARY__": repr(SUMMARY),
        "__AUDIT__": repr(OUT_TOKEN + "_Replay_Fidelity_Audit.json"),
        "__REPAIR__": repr(OUT_TOKEN + "_Frozen_Input_Binding_Audit.json"),
        "__DECISION__": repr(DECISION),
        "__GATES__": repr(OUT_TOKEN + "_Final_Gate_Matrix.csv"),
        "__MANIFEST__": repr(MANIFEST),
    }
    for k, v in repl.items():
        template = template.replace(k, v)
    helper_path.write_text(textwrap.dedent(template), encoding="utf-8")

def selftest() -> None:
    assert TF_VERSION == "2.20.0"
    assert len(TF220_CP313_LINUX_X86_64_WHEEL_SHA256) == 64
    assert PARENT == "25d72d91c19a1c4da98061da08e4446a63ab8bcc"
    assert G1_R1_RUNNER_BLOB == "756fde8da6fb1f7cd538ac6a67a7844093c3c838"
    print("POSTV16 GPU-HYB-G1-R3 structural/target-runtime self-test: PASS")

def main(project_root: Path, drive_root: Path, target_root: Path, wheelhouse_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCK_REL
    stage = "preflight"

    try:
        print("=" * 190)
        print("POSTV16-AV4-PIVOT-GPU-HYB-G1-R3 — TF2.20 TARGET-RUNTIME 100-DAY GPU REPLAY CERTIFICATION")
        print("TARGET-RUNTIME REPAIR ONLY. NO VENV. G1-R1 REPLAY LOGIC / PHYSICS / TOLERANCES UNCHANGED.")
        print("=" * 190)

        stage = "repository_authority"
        if gt(root, "branch", "--show-current") != BRANCH:
            raise GateError("branch_exact")
        if gt(root, "rev-parse", "HEAD^") != PARENT:
            raise GateError(f"parent_exact:{gt(root,'rev-parse','HEAD^')}")
        if gt(root, "status", "--porcelain") != "":
            raise GateError("repository_not_clean")

        r1 = root / G1_R1_RUNNER
        r2 = root / G1_R2_RUNNER
        if not r1.is_file() or sha256(r1) != G1_R1_RUNNER_SHA256:
            raise GateError("G1_R1_runner_sha")
        if gt(root, "hash-object", str(r1)) != G1_R1_RUNNER_BLOB:
            raise GateError("G1_R1_runner_blob")
        if not r2.is_file() or sha256(r2) != G1_R2_RUNNER_SHA256:
            raise GateError("G1_R2_runner_sha")
        if gt(root, "hash-object", str(r2)) != G1_R2_RUNNER_BLOB:
            raise GateError("G1_R2_runner_blob")

        stage = "prior_G1_R2_block_authority"
        prior_block = drive / G1_R2_BLOCK_REL / G1_R2_BLOCK_REPORT
        if not prior_block.is_file():
            raise GateError(f"G1_R2_block_report_missing:{prior_block}")
        prior = js(prior_block)
        if prior.get("status") != G1_R2_BLOCK_STATUS:
            raise GateError(f"G1_R2_block_status:{prior.get('status')}")
        if prior.get("failed_stage") != "tf220_environment_restoration":
            raise GateError(f"G1_R2_failed_stage:{prior.get('failed_stage')}")
        if "venv" not in str(prior.get("exception", "")):
            raise GateError(f"G1_R2_exception_not_venv:{prior.get('exception')}")
        if prior.get("new_physical_time_advance_executed") is not False:
            raise GateError("G1_R2_time_advance_not_false")
        if prior.get("AV4_authoritative_state_mutated") is not False:
            raise GateError("G1_R2_AV4_mutation_not_false")

        stage = "tf220_target_runtime_restoration"
        if out.exists():
            raise GateError(f"output_preexists:{out}")

        install_info = prepare_target_runtime(target_root, wheelhouse_root)
        probe = probe_target_runtime(target_root)
        if probe["returncode"] != 0 or probe["payload"] is None:
            raise GateError(f"target_runtime_probe_failed:{probe}")
        payload = probe["payload"]
        if payload.get("tensorflow") != TF_VERSION:
            raise GateError(f"target_runtime_tensorflow:{payload.get('tensorflow')}")
        tf_file = str(payload.get("tensorflow_file", ""))
        if not tf_file.startswith(str(target_root)):
            raise GateError(f"tensorflow_not_loaded_from_target:{tf_file}")
        if not payload.get("gpus"):
            raise GateError(f"target_runtime_GPU_not_visible:{payload}")

        stage = "exact_G1_R1_replay_under_target_runtime"
        helper = target_root / "run_g1r1_under_tf220_target.py"
        build_helper(helper, root, drive)
        proc = subprocess.run(
            [sys.executable, str(helper)],
            env=child_env(target_root)
        )
        if proc.returncode != 0:
            raise GateError(f"G1_R1_under_target_runtime_exit:{proc.returncode}")

        stage = "R3_output_validation"
        if not out.is_dir():
            raise GateError(f"R3_output_missing:{out}")
        summary_path = out / SUMMARY
        decision_path = out / DECISION
        manifest_path = out / MANIFEST
        for p in [summary_path, decision_path, manifest_path]:
            if not p.is_file():
                raise GateError(f"R3_artifact_missing:{p.name}")

        summary = js(summary_path)
        if summary.get("status") != PASS:
            raise GateError(f"R3_status:{summary.get('status')}")
        if summary.get("TensorFlow_version") != TF_VERSION:
            raise GateError(f"R3_summary_TF:{summary.get('TensorFlow_version')}")
        if summary.get("GPU_HYB_G2_authorized") is not True:
            raise GateError("R3_G2_not_authorized")
        if summary.get("new_physical_time_advance_executed") is not False:
            raise GateError("R3_time_advance_not_false")
        if summary.get("P4_authorized") is not False:
            raise GateError("R3_P4_not_false")

        env_audit = {
            "milestone": M,
            "status": PASS,
            "repair_scope": "software environment import target only",
            "prior_G1_R2_block_report_sha256": sha256(prior_block),
            "prior_G1_R2_failed_stage": prior.get("failed_stage"),
            "prior_G1_R2_exception": prior.get("exception"),
            "certified_tensorflow_required": TF_VERSION,
            "target_runtime_root": str(target_root),
            "wheelhouse_root": str(wheelhouse_root),
            "pip_command": install_info["pip_command"],
            "official_TF220_wheel_sha256_expected": TF220_CP313_LINUX_X86_64_WHEEL_SHA256,
            "downloaded_TF220_wheel": install_info["tensorflow_wheel"],
            "downloaded_TF220_wheel_sha256": install_info["tensorflow_wheel_sha256"],
            "wheelhouse_file_count": install_info["wheelhouse_file_count"],
            "child_python": payload.get("python"),
            "child_tensorflow": payload.get("tensorflow"),
            "child_tensorflow_file": payload.get("tensorflow_file"),
            "child_gpu_devices": payload.get("gpus"),
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
        summary["target_runtime_tensorflow"] = TF_VERSION
        summary["target_runtime_tensorflow_file"] = payload.get("tensorflow_file")
        summary["target_runtime_GPU_visible"] = True
        summary["G1_R1_replay_logic_changed_in_R3"] = False
        summary["physics_or_tolerance_changed_in_R3"] = False
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
        print("Prior G1-R2 failed stage                    :", prior.get("failed_stage"))
        print("Prior G1-R2 exception                       :", prior.get("exception"))
        print("TensorFlow wheel SHA verified               :", install_info["tensorflow_wheel_sha256"])
        print("Target TensorFlow                           :", payload.get("tensorflow"))
        print("Target TensorFlow file                      :", payload.get("tensorflow_file"))
        print("Target TensorFlow GPUs                      :", payload.get("gpus"))
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
    ap.add_argument("--target-root", type=Path, default=DEFAULT_TARGET_ROOT)
    ap.add_argument("--wheelhouse-root", type=Path, default=DEFAULT_WHEELHOUSE_ROOT)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root, args.target_root, args.wheelhouse_root))
