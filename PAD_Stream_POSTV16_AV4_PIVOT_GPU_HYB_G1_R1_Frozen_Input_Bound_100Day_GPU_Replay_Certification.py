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
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV4-PIVOT-GPU-HYB-G1-R1"
NAME = "Frozen-Input-Bound 100-Day Hybrid BL-DP GPU Replay Certification"
PASS = "POSTV16AV4PIVOTGPUHYBG1R1_FROZEN_INPUT_BOUND_100DAY_GPU_REPLAY_CERTIFICATION_PASS_NO_PHYSICAL_TIME_ADVANCE"
BLOCK = "POSTV16AV4PIVOTGPUHYBG1R1_TECHNICAL_OR_FIDELITY_BLOCK_NO_PHYSICAL_TIME_ADVANCE"

BRANCH = "postv16-av4-pivot"
PARENT = "b320cc010cdcf6c71d8b429fd41cbbcd58134da7"  # blocked G1 commit

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

# Prior G1 source and blocked evidence.
G1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G1_Controlled_100Day_GPU_Replay_Certification.py"
G1_RUNNER_SHA256 = "0f9dab709282f472c051683292a26104b2d933f3fb18e8447fa70b341fccd21c"
G1_RUNNER_BLOB = "fad886f94cad813da25998e475a5f120cc10111e"
G1_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_GPU_HYB_G1_BLOCKED"
G1_BLOCK_REPORT = "POSTV16_AV4_PIVOT_GPU_HYB_G1_Blocked_Report.json"

# G0 remains the positive execution authority.
G0_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_GPU_HYB_G0_Cadence_Aware_Hybrid_BLDP_Integration_Contract_Freeze"
G0_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G0_Summary.json"
G0_DECISION = "POSTV16_AV4_PIVOT_GPU_HYB_G0_Decision_Contract.json"
G0_STATUS = "POSTV16AV4PIVOTGPUHYBG0_CADENCE_AWARE_HYBRID_BLDP_INTEGRATION_CONTRACT_FREEZE_PASS_NO_PHYSICS_EXECUTION"

# Immutable E11-R2 reference and exact runner.
E11_RUNNER = "PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
E11_RUNNER_SHA256 = "0363a09612c5e80f6bb8124c817ca0d3726b1654283ab169c9b2d4d9861707b7"
E11_RUNNER_BLOB = "bf89c14a3cb177fb483e233a17b72e824d31119b"
E11_REL = Path("pilots/hybrid_dp/V16E11_R2_SGSIM_100D_CONTROLLED_STREAMLINE_PILOT")
E11_PILOT = ("V16E11_R2_SGSim_100Day_Streamline_Pilot.npz", "710720e933d740787868a9894fa04f90e88429c120d9f86a52b750f4c41db844")
E11_AUDIT = ("V16E11_R2_Path_Eligibility_and_Screening_Audit.json", "170dde9c74b26f949ef90de3d67001a124e740822fe587c032ae2f066379df4f")
E11_SUMMARY = ("PAD_Stream_V16E11_R2_Summary.json", "76336276daf4a506ea7e0880a6ad2e2852724deaf4623ca3945eafbf029e4243")

EXPECTED_NSTREAM = 1078
EXPECTED_NXI = 201
EXPECTED_ROUTE_COUNTS = {
    "HYBRID10_ACCEPT": 462,
    "HYBRID12_ACCEPT": 0,
    "EXACT_R2_FALLBACK": 41,
    "FULL_PHYSICS_SG7A_FALLBACK": 575,
}
EXPECTED_EARLY_PROBES = [[75,80],[120,125],[40,45]]

FLOAT32_EPS = float(np.finfo(np.float32).eps)
REPLAY_ATOL = 32.0 * FLOAT32_EPS
REPLAY_RTOL = 32.0 * FLOAT32_EPS

OUT_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G1_R1"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_Frozen_Input_Bound_100Day_GPU_Replay_Certification")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
AUDIT = f"{OUT_TOKEN}_Replay_Fidelity_Audit.json"
REPAIR = f"{OUT_TOKEN}_Harness_Repair_Audit.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"
REPLAY_DIRNAME = "E11_R2_GPU_REPLAY_FROZEN_INPUT_BOUND"

class GateError(RuntimeError):
    pass

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git","-C",str(root),*args], text=True).strip()

def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def csv_rows(path: Path) -> list[dict[str,str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict[str,Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader(); w.writerows(rows)

def route_counts(code: np.ndarray) -> dict[str,int]:
    return {
        "HYBRID10_ACCEPT": int(np.sum(code == 10)),
        "HYBRID12_ACCEPT": int(np.sum(code == 12)),
        "EXACT_R2_FALLBACK": int(np.sum(code == 20)),
        "FULL_PHYSICS_SG7A_FALLBACK": int(np.sum(code == 30)),
    }

def import_exact(path: Path, expected_sha256: str, module_name: str):
    if not path.is_file():
        raise GateError(f"missing_source:{path}")
    actual=sha256(path)
    if actual != expected_sha256:
        raise GateError(f"source_sha:{path.name}:{actual}:{expected_sha256}")
    spec=importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_import:{path}")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def resolve_frozen_artifact(recorded_path: str, expected_sha: str, drive_root: Path) -> tuple[Path,str]:
    """Resolve by immutable SHA identity, never by shape/eligibility scoring."""
    rp=Path(recorded_path)
    if rp.is_file():
        actual=sha256(rp)
        if actual == expected_sha:
            return rp.resolve(), "recorded_path_exact"

    basename=rp.name
    matches=[]
    # Exact-SHA recovery only. This is not semantic/discovery substitution.
    for p in drive_root.rglob(basename):
        if not p.is_file():
            continue
        try:
            if sha256(p) == expected_sha:
                matches.append(p.resolve())
        except OSError:
            pass
    unique=sorted(set(map(str,matches)))
    if len(unique) == 1:
        return Path(unique[0]), "exact_sha_recovery"
    if not unique:
        raise GateError(f"frozen_artifact_not_found:{basename}:{expected_sha}")
    raise GateError(f"frozen_artifact_exact_sha_ambiguous:{basename}:{unique}")

def load_exact_truth_carrier(e11, path: Path) -> dict[str,Any]:
    with np.load(path, allow_pickle=True) as z:
        tk=e11.first_key(z, ["times_days","physical_times_days","deployment_times_days"])
        sk=e11.first_key(z, ["SG7A_saturation","truth_saturation","reference_saturation","S_truth"])
        if tk is None or sk is None:
            raise GateError("frozen_SG7A_truth_keys_missing")
        times=np.asarray(z[tk],dtype=np.float64)
        truth=np.asarray(z[sk],dtype=np.float32)
        idx=int(np.argmin(np.abs(times - e11.PHYSICAL_TIME_DAYS)))
        if not np.isclose(times[idx], e11.PHYSICAL_TIME_DAYS, rtol=0.0, atol=1.0e-12):
            raise GateError("frozen_SG7A_no_exact_100day_snapshot")
        truth100=np.asarray(truth[idx],dtype=np.float32)
    if truth100.shape != (EXPECTED_NSTREAM,EXPECTED_NXI) or not np.all(np.isfinite(truth100)):
        raise GateError(f"frozen_SG7A_truth_shape_or_finite:{truth100.shape}")
    return {"path":path,"sha256":sha256(path),"truth100":truth100}

def gpu_probe() -> dict[str,Any]:
    info={"nvidia_smi_ok":False,"gpu_name":None,"tensorflow_probe_ok":False,
          "tensorflow_version":None,"tensorflow_gpu_devices":[]}
    try:
        p=subprocess.run(["nvidia-smi","--query-gpu=name","--format=csv,noheader"],
                         text=True,capture_output=True,check=True)
        names=[x.strip() for x in p.stdout.splitlines() if x.strip()]
        info["nvidia_smi_ok"]=bool(names); info["gpu_name"]=names[0] if names else None
    except Exception as exc:
        info["nvidia_smi_error"]=repr(exc)
    code=("import json,tensorflow as tf;"
          "print(json.dumps({'version':tf.__version__,'gpus':[d.name for d in tf.config.list_physical_devices(\"GPU\")]}))")
    try:
        env=os.environ.copy(); env["CUDA_VISIBLE_DEVICES"]="0"
        p=subprocess.run([sys.executable,"-c",code],text=True,capture_output=True,check=True,env=env)
        payload=json.loads(p.stdout.strip().splitlines()[-1])
        info["tensorflow_probe_ok"]=True
        info["tensorflow_version"]=payload["version"]
        info["tensorflow_gpu_devices"]=payload["gpus"]
    except Exception as exc:
        info["tensorflow_probe_error"]=repr(exc)
    return info

def compare_npz(reference_path: Path, replay_path: Path) -> dict[str,Any]:
    with np.load(reference_path,allow_pickle=False) as a, np.load(replay_path,allow_pickle=False) as b:
        ka,kb=sorted(a.files),sorted(b.files)
        if ka != kb:
            raise GateError(f"replay_key_set_mismatch:{ka}:{kb}")
        details={}; exact_keys=[]; nonexact_keys=[]
        for key in ka:
            aa=np.asarray(a[key]); bb=np.asarray(b[key])
            exact=aa.shape==bb.shape and np.array_equal(aa,bb)
            details[key]={"shape_reference":list(aa.shape),"shape_replay":list(bb.shape),
                          "dtype_reference":str(aa.dtype),"dtype_replay":str(bb.dtype),
                          "exact_array_equal":bool(exact)}
            (exact_keys if exact else nonexact_keys).append(key)
        exact_interface=all(details[k]["exact_array_equal"] for k in ka if k!="saturation_100d")
        sa=np.asarray(a["saturation_100d"],dtype=np.float32)
        sb=np.asarray(b["saturation_100d"],dtype=np.float32)
        diff=sb.astype(np.float64)-sa.astype(np.float64)
        sat_exact=np.array_equal(sa,sb)
        sat_close=np.allclose(sa,sb,rtol=REPLAY_RTOL,atol=REPLAY_ATOL,equal_nan=False)
        denom=float(np.linalg.norm(sa.astype(np.float64).ravel()))
        route_ref=np.asarray(a["route_code"]); route_rep=np.asarray(b["route_code"])
        screen_ref=np.asarray(a["learned_screen_pass"]); screen_rep=np.asarray(b["learned_screen_pass"])
        learned=route_ref==10; fallback=~learned
        return {
            "key_set_exact":True,
            "all_non_saturation_arrays_exact":bool(exact_interface),
            "exact_keys":exact_keys,
            "nonexact_keys":nonexact_keys,
            "route_code_exact":bool(np.array_equal(route_ref,route_rep)),
            "route_counts_reference":route_counts(route_ref),
            "route_counts_replay":route_counts(route_rep),
            "learned_screen_pass_exact":bool(np.array_equal(screen_ref,screen_rep)),
            "saturation_exact_array_equal":bool(sat_exact),
            "saturation_allclose_float32_machine_precision_contract":bool(sat_close),
            "saturation_replay_atol":REPLAY_ATOL,
            "saturation_replay_rtol":REPLAY_RTOL,
            "saturation_max_abs":float(np.max(np.abs(diff))),
            "saturation_rmse":float(np.sqrt(np.mean(diff*diff))),
            "saturation_relative_L2":float(np.linalg.norm(diff.ravel())/denom) if denom>0 else 0.0,
            "learned_route_saturation_max_abs":float(np.max(np.abs(diff[learned]))) if np.any(learned) else 0.0,
            "nonlearned_fallback_saturation_exact":bool(np.array_equal(sa[fallback],sb[fallback])),
            "array_details":details,
        }

def selftest() -> None:
    assert EXPECTED_EARLY_PROBES == [[75,80],[120,125],[40,45]]
    assert sum(EXPECTED_ROUTE_COUNTS.values()) == EXPECTED_NSTREAM
    assert REPLAY_ATOL == 32.0*np.finfo(np.float32).eps
    print("POSTV16 GPU-HYB-G1-R1 structural/frozen-input self-test: PASS")

def main(project_root: Path, drive_root: Path) -> int:
    root=project_root.resolve(); drive=drive_root.resolve()
    out=drive/OUT_REL; staging=drive/STAGE_REL; blocked=drive/BLOCK_REL
    stage="preflight"; gates=[]

    def gate(name:str,cond:Any,detail:Any=None):
        ok=bool(cond); gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"),flush=True)
        if not ok: raise GateError(name)

    try:
        print("="*190)
        print("POSTV16-AV4-PIVOT-GPU-HYB-G1-R1 — FROZEN-INPUT-BOUND 100-DAY GPU REPLAY CERTIFICATION")
        print("REPAIR SCOPE: ARTIFACT DISCOVERY ONLY. HYBRID/SCREEN/FALLBACK PHYSICS AND REPLAY TOLERANCES UNCHANGED.")
        print("="*190)

        stage="repository_authority"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_blocked_G1_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        g1src=root/G1_RUNNER
        gate("blocked_G1_runner_present",g1src.is_file())
        gate("blocked_G1_runner_sha_exact",sha256(g1src)==G1_RUNNER_SHA256,sha256(g1src) if g1src.is_file() else "missing")
        gate("blocked_G1_runner_blob_exact",gt(root,"hash-object",str(g1src))==G1_RUNNER_BLOB,
             gt(root,"hash-object",str(g1src)) if g1src.is_file() else "missing")

        stage="blocked_G1_evidence"
        prev_block=drive/G1_BLOCK_REL/G1_BLOCK_REPORT
        gate("prior_G1_block_report_present",prev_block.is_file(),str(prev_block))
        prev=js(prev_block)
        gate("prior_G1_status_BLOCK",prev.get("status")==
             "POSTV16AV4PIVOTGPUHYBG1_GPU_REPLAY_TECHNICAL_OR_FIDELITY_BLOCK_NO_PHYSICAL_TIME_ADVANCE",
             prev.get("status"))
        gate("prior_G1_no_time_advance",prev.get("new_physical_time_advance_executed") is False)
        gate("prior_G1_no_AV4_mutation",prev.get("AV4_authoritative_state_mutated") is False)
        prior_failed_stage=prev.get("failed_stage")
        prior_exception=prev.get("exception")
        print("Prior G1 failed stage:",prior_failed_stage)
        print("Prior G1 exception   :",prior_exception)

        stage="G0_authority"
        g0dir=drive/G0_REL
        gate("G0_summary_present",(g0dir/G0_SUMMARY).is_file())
        gate("G0_decision_present",(g0dir/G0_DECISION).is_file())
        g0s=js(g0dir/G0_SUMMARY); g0d=js(g0dir/G0_DECISION)
        gate("G0_status_exact",g0s.get("status")==G0_STATUS,g0s.get("status"))
        gate("G0_G1_authorized",g0s.get("GPU_HYB_G1_authorized") is True)
        gate("G0_G2_locked_pre_repair",g0s.get("GPU_HYB_G2_authorized") is False)
        gate("G0_Day405_to410_preserved",g0s.get("Day405_to_Day410_transport_remains_authorized") is True)
        gate("G0_P4_locked",g0s.get("P4_authorized") is False)

        stage="frozen_E11_authority"
        e11dir=drive/E11_REL
        ref_pilot=e11dir/E11_PILOT[0]; ref_audit=e11dir/E11_AUDIT[0]; ref_summary=e11dir/E11_SUMMARY[0]
        for label,p,hs in [("pilot",ref_pilot,E11_PILOT[1]),("audit",ref_audit,E11_AUDIT[1]),("summary",ref_summary,E11_SUMMARY[1])]:
            gate(f"E11_{label}_present",p.is_file(),str(p))
            gate(f"E11_{label}_sha_exact",sha256(p)==hs,sha256(p) if p.is_file() else "missing")
        e11audit=js(ref_audit); e11sum=js(ref_summary)
        gate("E11_status_PASS",str(e11sum.get("status")).upper()=="PASS",e11sum.get("status"))
        gate("E11_unsafe_zero",int(e11sum.get("unsafe_learned_proposals_accepted",-1))==0)

        artifacts=e11audit.get("SGSim_artifacts",{})
        required_artifact_fields=["SG6_path","SG6_sha256","SG5_path","SG5_sha256","SG7A_truth_carrier_path","SG7A_truth_carrier_sha256"]
        gate("E11_frozen_artifact_identities_complete",all(artifacts.get(k) for k in required_artifact_fields),artifacts)

        sg6_path,sg6_mode=resolve_frozen_artifact(artifacts["SG6_path"],artifacts["SG6_sha256"],drive)
        sg5_path,sg5_mode=resolve_frozen_artifact(artifacts["SG5_path"],artifacts["SG5_sha256"],drive)
        sg7a_path,sg7a_mode=resolve_frozen_artifact(artifacts["SG7A_truth_carrier_path"],artifacts["SG7A_truth_carrier_sha256"],drive)
        gate("SG6_frozen_SHA_bound",sha256(sg6_path)==artifacts["SG6_sha256"],str(sg6_path))
        gate("SG5_frozen_SHA_bound",sha256(sg5_path)==artifacts["SG5_sha256"],str(sg5_path))
        gate("SG7A_frozen_SHA_bound",sha256(sg7a_path)==artifacts["SG7A_truth_carrier_sha256"],str(sg7a_path))

        e11runner=root/E11_RUNNER
        gate("E11_runner_present",e11runner.is_file())
        gate("E11_runner_sha_exact",sha256(e11runner)==E11_RUNNER_SHA256,sha256(e11runner) if e11runner.is_file() else "missing")
        gate("E11_runner_blob_exact",gt(root,"hash-object",str(e11runner))==E11_RUNNER_BLOB,
             gt(root,"hash-object",str(e11runner)) if e11runner.is_file() else "missing")

        stage="GPU_runtime"
        gpu=gpu_probe()
        gate("nvidia_gpu_visible",gpu.get("nvidia_smi_ok") is True,gpu)
        gate("tensorflow_gpu_visible",gpu.get("tensorflow_probe_ok") is True and len(gpu.get("tensorflow_gpu_devices",[]))>=1,gpu)
        gate("tensorflow_2_20_exact",gpu.get("tensorflow_version")=="2.20.0",gpu.get("tensorflow_version"))

        stage="frozen_input_bound_E11_replay"
        gate("output_does_not_preexist",not out.exists(),str(out))
        if staging.exists(): shutil.rmtree(staging)
        staging.mkdir(parents=True,exist_ok=False)
        replay_dir=staging/REPLAY_DIRNAME

        # Import exact E11 and patch ONLY open-ended artifact discovery.
        e11=import_exact(e11runner,E11_RUNNER_SHA256,"v16e11r2_frozen_replay")
        exact_sg6=e11.load_sg6_candidate(sg6_path)
        ok,checks=e11.sg6_is_reference(exact_sg6)
        gate("bound_SG6_reference_contract_PASS",ok,checks)

        def bound_discover_sg6(project,drive_arg,workspace):
            return exact_sg6,[{
                "path":str(sg6_path),
                "sha256":artifacts["SG6_sha256"],
                "eligible_reference":True,
                "checks":checks,
                "binding":"E11_AUDIT_FROZEN_EXACT_SHA",
            }]

        def bound_locate_sg5_for_sg6(_):
            return sg5_path

        def bound_load_truth(_):
            return load_exact_truth_carrier(e11,sg7a_path)

        e11.discover_sg6=bound_discover_sg6
        e11.locate_sg5_for_sg6=bound_locate_sg5_for_sg6
        e11.load_sg7a_truth100_for_workspace=bound_load_truth

        os.environ["CUDA_VISIBLE_DEVICES"]="0"
        os.environ["TF_DETERMINISTIC_OPS"]="1"
        os.environ["TF_CUDNN_DETERMINISTIC"]="1"

        print("Executing immutable E11-R2 run() with frozen artifact-discovery bindings...",flush=True)
        rc=e11.run(root,drive,replay_dir,None)
        gate("E11_R2_frozen_bound_replay_exit_zero",rc==0,rc)

        replay_pilot=replay_dir/E11_PILOT[0]
        replay_summary=replay_dir/E11_SUMMARY[0]
        gate("replay_pilot_present",replay_pilot.is_file())
        gate("replay_summary_present",replay_summary.is_file())
        rps=js(replay_summary)
        gate("replay_status_PASS",str(rps.get("status")).upper()=="PASS",rps.get("status"))
        gate("replay_zero_unsafe",int(rps.get("unsafe_learned_proposals_accepted",-1))==0)
        gate("replay_no_pressure_Darcy_Pollock_TOF",rps.get("pressure_Darcy_Pollock_TOF_recomputed") is False)
        gate("replay_no_mapback",rps.get("grid_mapback_performed") is False)

        stage="replay_fidelity"
        fidelity=compare_npz(ref_pilot,replay_pilot)
        gate("NPZ_key_set_exact",fidelity["key_set_exact"])
        gate("all_non_saturation_arrays_exact",fidelity["all_non_saturation_arrays_exact"],fidelity["nonexact_keys"])
        gate("route_code_exact",fidelity["route_code_exact"])
        gate("route_counts_reference_exact",fidelity["route_counts_reference"]==EXPECTED_ROUTE_COUNTS,fidelity["route_counts_reference"])
        gate("route_counts_replay_exact",fidelity["route_counts_replay"]==EXPECTED_ROUTE_COUNTS,fidelity["route_counts_replay"])
        gate("learned_screen_pass_exact",fidelity["learned_screen_pass_exact"])
        gate("nonlearned_fallback_saturation_exact",fidelity["nonlearned_fallback_saturation_exact"])
        gate("saturation_machine_precision_replay_PASS",
             fidelity["saturation_allclose_float32_machine_precision_contract"],fidelity)

        repair_audit={
            "milestone":M,
            "repair_scope":"artifact discovery / provenance binding only",
            "prior_G1_failed_stage":prior_failed_stage,
            "prior_G1_exception":prior_exception,
            "prior_G1_block_report_sha256":sha256(prev_block),
            "physics_or_routing_change":False,
            "screen_change":False,
            "checkpoint_change":False,
            "replay_tolerance_change":False,
            "open_ended_SGSim_discovery_used":False,
            "frozen_artifacts":{
                "SG6":{"path":str(sg6_path),"sha256":sha256(sg6_path),"resolution":sg6_mode},
                "SG5":{"path":str(sg5_path),"sha256":sha256(sg5_path),"resolution":sg5_mode},
                "SG7A_truth_carrier":{"path":str(sg7a_path),"sha256":sha256(sg7a_path),"resolution":sg7a_mode},
            },
            "binding_source":"immutable E11-R2 audit SGSim_artifacts identities",
        }

        audit_out={
            "milestone":M,"status":PASS,"GPU_runtime":gpu,
            "comparison_contract":{
                "all_non_saturation_arrays":"exact np.array_equal",
                "route_code_and_screen_decisions":"exact",
                "nonlearned_fallback_saturation":"exact",
                "learned_saturation":"np.allclose with 32*float32 epsilon atol/rtol",
                "float32_epsilon":FLOAT32_EPS,"atol":REPLAY_ATOL,"rtol":REPLAY_RTOL,
                "scientific_tolerance_tuned":False,
            },
            "fidelity":fidelity,
        }
        decision={
            "milestone":M,"status":PASS,
            "classification":"FROZEN_E11_INPUT_IDENTITIES_BOUND_EXACT_HYBRID_GPU_REPLAY_PASS_G2_EARLY_REFERENCE_TRAJECTORY_AUTHORIZED",
            "GPU_HYB_G2_early_contiguous_trajectory_authorized":True,
            "GPU_HYB_G2_targeted_early_probe_execution_authorized":True,
            "GPU_HYB_G2_required_probe_pairs":EXPECTED_EARLY_PROBES,
            "GPU_HYB_G2_reference_truth_requires_exact_FV_pressure":True,
            "GPU_HYB_G2_reference_truth_requires_exact_Darcy_Pollock_TOF":True,
            "learned_pressure_seed_can_define_reference_truth":False,
            "production_pressure_refresh_cadence_selected":False,
            "brute_force_Day30_to_Day365_five_day_sweep_authorized":False,
            "Day405_to_Day410_transport_remains_authorized":True,
            "Day405_to_Day410_transport_executed":False,
            "P4_authorized":False,
            "recommended_next_action":(
                "Design G2 contiguous early GPU BL/Hybrid-DP reference trajectory around exact diagnostic anchors "
                "needed for Day75-80, Day120-125, and Day40-45; do not authorize a uniform five-day Day30-365 sweep."
            ),
        }
        summary={
            "milestone":M,"name":NAME,"status":PASS,"classification":decision["classification"],
            "repository_parent_blocked_G1_commit":PARENT,
            "prior_G1_failed_stage":prior_failed_stage,
            "prior_G1_exception":prior_exception,
            "frozen_input_binding_repair_PASS":True,
            "GPU_name":gpu.get("gpu_name"),
            "TensorFlow_version":gpu.get("tensorflow_version"),
            "route_code_exact":fidelity["route_code_exact"],
            "learned_screen_pass_exact":fidelity["learned_screen_pass_exact"],
            "all_non_saturation_arrays_exact":fidelity["all_non_saturation_arrays_exact"],
            "nonlearned_fallback_saturation_exact":fidelity["nonlearned_fallback_saturation_exact"],
            "saturation_exact_array_equal":fidelity["saturation_exact_array_equal"],
            "saturation_machine_precision_replay_PASS":fidelity["saturation_allclose_float32_machine_precision_contract"],
            "saturation_max_abs":fidelity["saturation_max_abs"],
            "saturation_RMSE":fidelity["saturation_rmse"],
            "saturation_relative_L2":fidelity["saturation_relative_L2"],
            "late_time_evidence_bracket_days":[5,15],
            "early_target_pairs":EXPECTED_EARLY_PROBES,
            "GPU_HYB_G2_authorized":True,
            "production_pressure_refresh_cadence_selected":False,
            "new_pressure_solve_executed":False,
            "Darcy_recomputation_executed":False,
            "Pollock_retracing_executed":False,
            "TOF_recomputation_executed":False,
            "streamline_to_grid_mapback_executed":False,
            "new_physical_time_advance_executed":False,
            "AV4_authoritative_state_mutated":False,
            "Day405_to_Day410_transport_executed":False,
            "Day405_to_Day410_transport_remains_authorized":True,
            "P4_authorized":False,
        }

        (staging/REPAIR).write_text(json.dumps(repair_audit,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (staging/AUDIT).write_text(json.dumps(audit_out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (staging/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (staging/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(staging/GATES,gates)
        manifest=[]
        for p in sorted(staging.iterdir()):
            if p.is_file() and p.name!=MANIFEST:
                manifest.append({"file":p.name,"sha256":sha256(p),"bytes":p.stat().st_size})
        for p in [replay_pilot,replay_summary]:
            manifest.append({"file":f"{REPLAY_DIRNAME}/{p.name}","sha256":sha256(p),"bytes":p.stat().st_size})
        write_csv(staging/MANIFEST,manifest)
        staging.rename(out)

        print("="*190)
        print(M,"PASS")
        print("Prior G1 failed stage                          :",prior_failed_stage)
        print("Prior G1 exception                             :",prior_exception)
        print("Frozen-input binding repair                    : PASS")
        print("GPU                                             :",gpu.get("gpu_name"))
        print("TensorFlow                                      :",gpu.get("tensorflow_version"))
        print("Route code exact                                :",fidelity["route_code_exact"])
        print("Learned screen exact                            :",fidelity["learned_screen_pass_exact"])
        print("All non-saturation arrays exact                 :",fidelity["all_non_saturation_arrays_exact"])
        print("Nonlearned fallback saturation exact            :",fidelity["nonlearned_fallback_saturation_exact"])
        print("Saturation exact array equal                    :",fidelity["saturation_exact_array_equal"])
        print("Saturation machine-precision replay PASS        :",fidelity["saturation_allclose_float32_machine_precision_contract"])
        print("Saturation max abs / RMSE / relative L2         :",fidelity["saturation_max_abs"],fidelity["saturation_rmse"],fidelity["saturation_relative_L2"])
        print("G2 early reference trajectory authorized        : True")
        print("Production cadence selected                     : False")
        print("Day405->Day410 remains authorized               : True")
        print("P4 authorized                                   : False")
        print("Output directory                                :",out)
        print("="*190)
        return 0

    except Exception as exc:
        if staging.exists(): shutil.rmtree(staging,ignore_errors=True)
        blocked.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),
            "GPU_HYB_G2_authorized":False,
            "new_pressure_solve_executed":False,
            "Darcy_recomputation_executed":False,
            "Pollock_retracing_executed":False,
            "TOF_recomputation_executed":False,
            "streamline_to_grid_mapback_executed":False,
            "new_physical_time_advance_executed":False,
            "AV4_authoritative_state_mutated":False,
            "P4_authorized":False,
            "gates_completed":gates,
        }
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"TECHNICAL / FIDELITY BLOCK")
        print("Stage:",stage)
        print("Exception:",repr(exc))
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
