#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
from typing import Any

M="POSTV16-AV4-PIVOT-GPU-HYB-G1-R4"
NAME="Native Colab TensorFlow-2.20 100-Day Hybrid BL-DP GPU Replay Certification"
PASS="POSTV16AV4PIVOTGPUHYBG1R4_NATIVE_COLAB_TF220_100DAY_GPU_REPLAY_CERTIFICATION_PASS_NO_PHYSICAL_TIME_ADVANCE"
BLOCK="POSTV16AV4PIVOTGPUHYBG1R4_RUNTIME_OR_FIDELITY_BLOCK_NO_PHYSICAL_TIME_ADVANCE"
BRANCH="postv16-av4-pivot"
PARENT="2873fc48081aa08ffb8bfde0546b868c07996644"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G1_R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G1_R1_Frozen_Input_Bound_100Day_GPU_Replay_Certification.py"
G1_R1_RUNNER_SHA256="9d5402fb6d075ed7ce8ac65d9150dcffbdabe2f95b34b9e9f8a47eb451b32cb0"
G1_R1_RUNNER_BLOB="756fde8da6fb1f7cd538ac6a67a7844093c3c838"

G1_R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G1_R3_TF220_Target_Runtime_GPU_Replay_Certification.py"
G1_R3_RUNNER_SHA256="cca587027ed1d99adf10f445117d87941eec4445114f5b90745299566aad01c3"
G1_R3_RUNNER_BLOB="22083753df56e9457383264e7a3387d93beb705f"

G1_R3_BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_GPU_HYB_G1_R3_BLOCKED"
G1_R3_BLOCK_REPORT="POSTV16_AV4_PIVOT_GPU_HYB_G1_R3_Blocked_Report.json"
G1_R3_BLOCK_STATUS="POSTV16AV4PIVOTGPUHYBG1R3_ENVIRONMENT_OR_FIDELITY_BLOCK_NO_PHYSICAL_TIME_ADVANCE"

TF_VERSION="2.20.0"
OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G1_R4"
OUT_REL=BASE_AV4/(OUT_TOKEN+"_Native_Colab_TF220_100Day_GPU_Replay_Certification")
BLOCK_REL=BASE_AV4/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
RUNTIME_AUDIT=f"{OUT_TOKEN}_Native_Runtime_Audit.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError): pass

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def gt(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def js(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def csv_rows(path:Path)->list[dict[str,str]]:
    with path.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))

def write_csv(path:Path,rows:list[dict[str,Any]])->None:
    if not rows:
        path.write_text("",encoding="utf-8"); return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)

def native_runtime_probe()->dict[str,Any]:
    code=("import json,sys,tensorflow as tf;"
          "print(json.dumps({'python':sys.version.split()[0],'tensorflow':tf.__version__,"
          "'tensorflow_file':tf.__file__,'gpus':[d.name for d in tf.config.list_physical_devices('GPU')]}))")
    env=os.environ.copy(); env["CUDA_VISIBLE_DEVICES"]="0"
    q=subprocess.run([sys.executable,"-c",code],text=True,capture_output=True,env=env)
    payload=json.loads(q.stdout.strip().splitlines()[-1]) if q.returncode==0 and q.stdout.strip() else None
    return {"returncode":q.returncode,"stdout":q.stdout,"stderr":q.stderr,"payload":payload}

def build_helper(helper_path:Path, project_root:Path, drive_root:Path)->None:
    src=f"""
from pathlib import Path
import importlib.util
PROJECT=Path({str(project_root)!r})
DRIVE=Path({str(drive_root)!r})
RUNNER=PROJECT/{G1_R1_RUNNER!r}
EXPECTED_SHA={G1_R1_RUNNER_SHA256!r}
PARENT={PARENT!r}
def sha256(p):
    import hashlib
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()
if sha256(RUNNER)!=EXPECTED_SHA: raise SystemExit('G1-R1 source SHA mismatch')
spec=importlib.util.spec_from_file_location('g1r1_native_tf220',RUNNER)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.PARENT=PARENT
mod.M={M!r}; mod.NAME={NAME!r}; mod.PASS={PASS!r}; mod.BLOCK={BLOCK!r}
mod.OUT_TOKEN={OUT_TOKEN!r}
mod.OUT_REL=mod.BASE_AV4/{str(OUT_REL.relative_to(BASE_AV4))!r}
mod.BLOCK_REL=mod.BASE_AV4/{str(BLOCK_REL.relative_to(BASE_AV4))!r}
mod.SUMMARY={SUMMARY!r}
mod.AUDIT={OUT_TOKEN+"_Replay_Fidelity_Audit.json"!r}
mod.REPAIR={OUT_TOKEN+"_Frozen_Input_Binding_Audit.json"!r}
mod.DECISION={DECISION!r}
mod.GATES={OUT_TOKEN+"_Final_Gate_Matrix.csv"!r}
mod.MANIFEST={MANIFEST!r}
mod.REPLAY_DIRNAME='E11_R2_GPU_REPLAY_NATIVE_COLAB_TF220'
raise SystemExit(mod.main(PROJECT,DRIVE))
"""
    helper_path.write_text(src,encoding="utf-8")

def selftest()->None:
    assert TF_VERSION=="2.20.0"
    assert PARENT=="2873fc48081aa08ffb8bfde0546b868c07996644"
    print("POSTV16 GPU-HYB-G1-R4 structural/native-runtime self-test: PASS")

def main(project_root:Path,drive_root:Path)->int:
    root=project_root.resolve(); drive=drive_root.resolve()
    out=drive/OUT_REL; blocked=drive/BLOCK_REL; stage="preflight"
    try:
        print("="*180)
        print("POSTV16-AV4-PIVOT-GPU-HYB-G1-R4 — NATIVE COLAB TF2.20 100-DAY GPU REPLAY CERTIFICATION")
        print("REQUIRES NATIVE TF2.20+GPU. NO PACKAGE INSTALLATION. G1-R1 REPLAY LOGIC UNCHANGED.")
        print("="*180)

        stage="repository_authority"
        if gt(root,"branch","--show-current")!=BRANCH: raise GateError("branch_exact")
        if gt(root,"rev-parse","HEAD^")!=PARENT: raise GateError(f"parent_exact:{gt(root,'rev-parse','HEAD^')}")
        if gt(root,"status","--porcelain")!="": raise GateError("repository_not_clean")
        r1=root/G1_R1_RUNNER; r3=root/G1_R3_RUNNER
        if not r1.is_file() or sha256(r1)!=G1_R1_RUNNER_SHA256: raise GateError("G1_R1_runner_sha")
        if gt(root,"hash-object",str(r1))!=G1_R1_RUNNER_BLOB: raise GateError("G1_R1_runner_blob")
        if not r3.is_file() or sha256(r3)!=G1_R3_RUNNER_SHA256: raise GateError("G1_R3_runner_sha")
        if gt(root,"hash-object",str(r3))!=G1_R3_RUNNER_BLOB: raise GateError("G1_R3_runner_blob")

        stage="prior_G1_R3_block_authority"
        prior_block=drive/G1_R3_BLOCK_REL/G1_R3_BLOCK_REPORT
        if not prior_block.is_file(): raise GateError(f"G1_R3_block_report_missing:{prior_block}")
        prior=js(prior_block)
        if prior.get("status")!=G1_R3_BLOCK_STATUS: raise GateError(f"G1_R3_block_status:{prior.get('status')}")
        if prior.get("failed_stage")!="tf220_target_runtime_restoration": raise GateError(f"G1_R3_failed_stage:{prior.get('failed_stage')}")
        if "target_runtime_GPU_not_visible" not in str(prior.get("exception","")): raise GateError(f"G1_R3_unexpected_exception:{prior.get('exception')}")
        if prior.get("new_physical_time_advance_executed") is not False: raise GateError("G1_R3_time_advance_not_false")
        if prior.get("AV4_authoritative_state_mutated") is not False: raise GateError("G1_R3_AV4_mutation_not_false")

        stage="native_tf220_GPU_runtime"
        if out.exists(): raise GateError(f"output_preexists:{out}")
        probe=native_runtime_probe()
        if probe["returncode"]!=0 or probe["payload"] is None: raise GateError(f"native_runtime_probe_failed:{probe}")
        payload=probe["payload"]
        if payload.get("tensorflow")!=TF_VERSION:
            raise GateError(f"native_tensorflow_version:{payload.get('tensorflow')}; select Colab Runtime Version 2026.07")
        if not payload.get("gpus"):
            raise GateError("native_tensorflow_GPU_not_visible; select a GPU hardware accelerator")

        stage="exact_G1_R1_replay_under_native_tf220"
        helper=root/".g1r4_native_tf220_helper.py"
        try:
            build_helper(helper,root,drive)
            env=os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"]="0"; env["TF_DETERMINISTIC_OPS"]="1"; env["TF_CUDNN_DETERMINISTIC"]="1"
            proc=subprocess.run([sys.executable,str(helper)],env=env)
        finally:
            if helper.exists(): helper.unlink()
        if proc.returncode!=0: raise GateError(f"G1_R1_under_native_TF220_exit:{proc.returncode}")

        stage="R4_output_validation"
        if not out.is_dir(): raise GateError(f"R4_output_missing:{out}")
        summary_path=out/SUMMARY; decision_path=out/DECISION; manifest_path=out/MANIFEST
        for p in [summary_path,decision_path,manifest_path]:
            if not p.is_file(): raise GateError(f"R4_artifact_missing:{p.name}")
        summary=js(summary_path)
        if summary.get("status")!=PASS: raise GateError(f"R4_status:{summary.get('status')}")
        if summary.get("TensorFlow_version")!=TF_VERSION: raise GateError(f"R4_summary_TF:{summary.get('TensorFlow_version')}")
        if summary.get("GPU_HYB_G2_authorized") is not True: raise GateError("R4_G2_not_authorized")
        if summary.get("new_physical_time_advance_executed") is not False: raise GateError("R4_time_advance_not_false")
        if summary.get("P4_authorized") is not False: raise GateError("R4_P4_not_false")

        audit={
            "milestone":M,"status":PASS,
            "repair_scope":"native Colab runtime selection only",
            "prior_G1_R3_block_report_sha256":sha256(prior_block),
            "native_python":payload.get("python"),
            "native_tensorflow":payload.get("tensorflow"),
            "native_tensorflow_file":payload.get("tensorflow_file"),
            "native_gpu_devices":payload.get("gpus"),
            "package_installation_performed":False,
            "G1_R1_replay_logic_changed":False,
            "physics_changed":False,
            "replay_tolerances_changed":False,
            "new_physical_time_advance":False,
        }
        (out/RUNTIME_AUDIT).write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        summary.update({
            "native_runtime_certification_PASS":True,
            "native_python":payload.get("python"),
            "native_tensorflow":payload.get("tensorflow"),
            "native_tensorflow_GPU_visible":True,
            "package_installation_performed":False,
            "G1_R1_replay_logic_changed_in_R4":False,
            "physics_or_tolerance_changed_in_R4":False,
        })
        summary_path.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        old_rows=csv_rows(manifest_path)
        replay_rows=[r for r in old_rows if "/" in r["file"]]
        flat=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!=MANIFEST:
                flat.append({"file":p.name,"sha256":sha256(p),"bytes":p.stat().st_size})
        write_csv(manifest_path,flat+replay_rows)

        print("="*180)
        print(M,"PASS")
        for k in ["native_python","native_tensorflow","route_code_exact","learned_screen_pass_exact",
                  "all_non_saturation_arrays_exact","nonlearned_fallback_saturation_exact",
                  "saturation_machine_precision_replay_PASS","GPU_HYB_G2_authorized",
                  "production_pressure_refresh_cadence_selected","new_physical_time_advance_executed",
                  "Day405_to_Day410_transport_remains_authorized","P4_authorized"]:
            print(f"{k:55s}: {summary.get(k)!r}")
        print("Output directory:",out)
        print("="*180)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),
                "GPU_HYB_G2_authorized":False,"new_physical_time_advance_executed":False,
                "AV4_authoritative_state_mutated":False,"P4_authorized":False}
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"RUNTIME / FIDELITY BLOCK")
        print("Stage:",stage); print("Exception:",repr(exc))
        return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        selftest(); raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))
