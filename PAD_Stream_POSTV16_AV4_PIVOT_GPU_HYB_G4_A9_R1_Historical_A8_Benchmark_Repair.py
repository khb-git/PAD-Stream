#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-A9-R1"
PASS="POSTV16AV4PIVOTGPUHYBG4A9R1_HISTORICAL_A8_BENCHMARK_REPAIR_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG4A9R1_TECHNICAL_OR_TIMING_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="98b6f07e4edaac263f3324f81272eee25c9d6c07"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

ORIGINAL_A9_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A9_EndToEnd_WallClock_Characterization.py"
ORIGINAL_A9_BLOB="76a92f3368b0cbb0fd7bef281664de0c634fa9f1"
ORIGINAL_A9_BLOCK_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G4_A9_BLOCKED"
ORIGINAL_A9_BLOCK_FILE="POSTV16_AV4_PIVOT_GPU_HYB_G4_A9_Blocked_Report.json"

A8_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A8_Day100_Production_Trajectory_Validation.py"
A8_BLOB="65006bfdc44630746d4c45c6d8696560b70efef6"
A8_COMMIT="8240c6899c1c02fd0f25294b4ec1285900e700f3"
A8_PARENT="80299e03e4eaa1a0da1608d5cb8d7ef03ac70e79"
A8_SUM_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G4_A8_Day100_Production_Trajectory_Validation"/"PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A8_Summary.json"
A8_STATUS="POSTV16AV4PIVOTGPUHYBG4A8_DAY100_PRODUCTION_TRAJECTORY_VALIDATION_COMPLETE"

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A9_R1"
OUT_REL=BASE/(OUT_TOKEN+"_Historical_A8_Benchmark_Repair")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
TIMING=f"{OUT_TOKEN}_Timing.csv"
DECISION=f"{OUT_TOKEN}_Decision.json"
PROVENANCE=f"{OUT_TOKEN}_Repair_Provenance.json"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError):
    pass

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):
            h.update(c)
    return h.hexdigest()

def gt(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def blob(root:Path,p:Path)->str:
    return gt(root,"hash-object",str(p))

def js(p:Path):
    return json.loads(p.read_text(encoding="utf-8"))

def mod(root:Path,fn:str,expected_blob:str,name:str):
    p=root/fn
    if not p.is_file():
        raise GateError(f"missing_source:{fn}")
    actual=blob(root,p)
    if actual!=expected_blob:
        raise GateError(f"source_blob:{fn}:{actual}:{expected_blob}")
    spec=importlib.util.spec_from_file_location(name,p)
    if spec is None or spec.loader is None:
        raise GateError(f"import_spec:{fn}")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m

def write_csv(p:Path,rows:list[dict[str,Any]]):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def exact_timing_from_original_block(block:dict[str,Any])->dict[str,Any]:
    if block.get("failed_stage")!="paired_end_to_end_timing":
        raise GateError(f"original_A9_failed_stage:{block.get('failed_stage')}")
    if "Hybrid_benchmark_exit_zero" not in str(block.get("exception","")):
        raise GateError(f"original_A9_exception:{block.get('exception')}")
    gates=block.get("gates",[])
    exact_gate=next((g for g in gates if g.get("gate")=="exact_benchmark_exit_zero"),None)
    hybrid_gate=next((g for g in gates if g.get("gate")=="Hybrid_benchmark_exit_zero"),None)
    if exact_gate is None or exact_gate.get("pass") is not True:
        raise GateError("original_A9_exact_timing_gate_missing_or_failed")
    if hybrid_gate is None or hybrid_gate.get("pass") is not False:
        raise GateError("original_A9_Hybrid_failure_gate_missing")
    try:
        exact_detail=ast.literal_eval(str(exact_gate.get("detail")))
        hybrid_detail=ast.literal_eval(str(hybrid_gate.get("detail")))
    except Exception as exc:
        raise GateError(f"original_A9_gate_detail_parse:{repr(exc)}")
    if int(exact_detail.get("return_code",-1))!=0:
        raise GateError(f"original_A9_exact_return_code:{exact_detail}")
    exact_seconds=float(exact_detail["wallclock_seconds"])
    hybrid_failed_seconds=float(hybrid_detail["wallclock_seconds"])
    if not np.isfinite(exact_seconds) or exact_seconds<=0:
        raise GateError(f"invalid_preserved_exact_seconds:{exact_seconds}")
    if int(hybrid_detail.get("return_code",-1))==0:
        raise GateError("original_A9_Hybrid_was_not_failed")
    return {
        "exact_seconds":exact_seconds,
        "failed_Hybrid_seconds":hybrid_failed_seconds,
        "exact_detail":exact_detail,
        "hybrid_detail":hybrid_detail,
    }

def historical_clone(source_root:Path,dest:Path)->None:
    if dest.exists():
        shutil.rmtree(dest)
    subprocess.run(
        ["git","clone","--local","--no-hardlinks",str(source_root),str(dest)],
        check=True,
    )
    subprocess.run(["git","-C",str(dest),"checkout",BRANCH],check=True)
    subprocess.run(["git","-C",str(dest),"reset","--hard",A8_COMMIT],check=True)
    subprocess.run(["git","-C",str(dest),"clean","-fdx"],check=True)

def selftest():
    assert len(PARENT)==40 and len(A8_COMMIT)==40
    assert A8_COMMIT!=PARENT
    print("POSTV16 GPU-HYB-G4-A9-R1 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve()
    drive=drive.resolve()
    out=drive/OUT_REL
    blocked=drive/BLOCK_REL
    gates=[]
    stage="preflight"

    def gate(name:str,passed:bool,detail:Any=None):
        ok=bool(passed)
        gates.append({
            "stage":stage,
            "gate":name,
            "pass":ok,
            "detail":"" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"),flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("="*204)
        print("G4-A9-R1 — HISTORICAL A8 BENCHMARK HARNESS REPAIR")
        print("PRESERVES THE VALID EXACT TIMING FROM ORIGINAL A9 BLOCK; RERUNS ONLY HYBRID A8 IN ITS CERTIFIED HISTORICAL REPOSITORY STATE.")
        print("RESULT IS A SALVAGED ENGINEERING CHARACTERIZATION, NOT A STRICT SAME-RUN STATISTICAL PAIRED BENCHMARK.")
        print("="*204)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_original_A9",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        original_runner=root/ORIGINAL_A9_RUNNER
        gate("original_A9_runner_present",original_runner.is_file(),str(original_runner))
        gate("original_A9_runner_blob_exact",blob(root,original_runner)==ORIGINAL_A9_BLOB,blob(root,original_runner))

        stage="original_A9_block_authority"
        block_path=drive/ORIGINAL_A9_BLOCK_REL/ORIGINAL_A9_BLOCK_FILE
        gate("original_A9_BLOCK_present",block_path.is_file(),str(block_path))
        b=js(block_path)
        timing=exact_timing_from_original_block(b)
        exact_seconds=float(timing["exact_seconds"])
        gate("original_A9_exact_timing_valid",exact_seconds>0,exact_seconds)
        gate("original_A9_Hybrid_failed_before_physics_like_duration",
             float(timing["failed_Hybrid_seconds"])<1.0,
             timing["failed_Hybrid_seconds"])

        stage="A8_scientific_authority"
        a8s=js(drive/A8_SUM_REL)
        gate("A8_status_exact",a8s.get("status")==A8_STATUS,a8s.get("status"))
        gate("A8_validation_complete",a8s.get("trajectory_validation_complete") is True)
        gate("A8_scientific_interpretation_required",a8s.get("scientific_interpretation_required") is True)
        gate("A8_production_locked",a8s.get("integrated_GPU_runtime_production_authorized") is False)
        gate("A8_P4_locked",a8s.get("P4_authorized") is False)

        sat_rel=float(a8s["mixed_100d_vs_exact_saturation_relative_L2"])
        pressure_rel=float(a8s["mixed_vs_exact_100d_refreshed_pressure_relative_L2"])
        flux_rel=float(a8s["mixed_vs_exact_100d_refreshed_flux_relative_L2"])
        stored_rel=float(a8s["mixed_100d_stored_mass_relative_error"])
        produced_rel=float(a8s["mixed_100d_cumulative_produced_mass_relative_error"])
        cut_abs=abs(float(a8s["mixed_100d_minus_exact_producer_gas_cut"]))
        topology_preserved=(
            int(a8s["mixed_100d_minus_exact_active_cell_count"])==0
            and int(a8s["mixed_100d_minus_exact_visible_cell_count"])==0
        )

        stage="historical_A8_repository"
        hist=Path("/content/PAD_Stream_G4_A9_R1_A8_Historical")
        historical_clone(root,hist)
        gate("historical_branch_exact",gt(hist,"branch","--show-current")==BRANCH,gt(hist,"branch","--show-current"))
        gate("historical_A8_HEAD_exact",gt(hist,"rev-parse","HEAD")==A8_COMMIT,gt(hist,"rev-parse","HEAD"))
        gate("historical_A8_parent_exact",gt(hist,"rev-parse","HEAD^")==A8_PARENT,gt(hist,"rev-parse","HEAD^"))
        gate("historical_repo_clean",gt(hist,"status","--porcelain")=="")
        a8=mod(hist,A8_RUNNER,A8_BLOB,"g4a9r1_historical_a8")

        local_base=Path("/content/PAD_Stream_G4_A9_R1_Benchmark")
        if local_base.exists():
            shutil.rmtree(local_base)
        local_base.mkdir(parents=True)
        local_out=local_base/"hybrid_output"
        local_block=local_base/"hybrid_block"
        a8.OUT_REL=local_out
        a8.BLOCK_REL=local_block

        stage="repaired_Hybrid_timing"
        t0=time.perf_counter()
        hybrid_rc=int(a8.main(hist,drive))
        hybrid_seconds=float(time.perf_counter()-t0)
        gate("repaired_Hybrid_exit_zero",hybrid_rc==0,{"return_code":hybrid_rc,"seconds":hybrid_seconds})
        gate("repaired_Hybrid_timing_positive",
             np.isfinite(hybrid_seconds) and hybrid_seconds>1.0,
             hybrid_seconds)

        stage="performance_characterization"
        speedup=exact_seconds/hybrid_seconds
        fractional=(exact_seconds-hybrid_seconds)/exact_seconds
        faster=hybrid_seconds<exact_seconds

        # Deliberately no acceptance threshold.
        scientific_interpretation=(
            "MODERATE_ACCUMULATED_TRANSPORT_AND_PRODUCER_ERROR_WITH_TIGHTER_PRESSURE_"
            "AND_PRESERVED_PLUME_SUPPORT_NOT_PRODUCTION_QUALIFIED"
        )
        timing_rows=[
            {
                "branch":"EXACT_R3R7",
                "wallclock_seconds":exact_seconds,
                "source":"PRESERVED_FROM_ORIGINAL_A9_BLOCK",
                "return_code":0,
                "strict_same_R1_invocation":False,
            },
            {
                "branch":"HYBRID_A8",
                "wallclock_seconds":hybrid_seconds,
                "source":"A9_R1_HISTORICAL_A8_RERUN",
                "return_code":0,
                "strict_same_R1_invocation":True,
            },
        ]

        decision={
            "milestone":M,
            "status":PASS,
            "repair_classification":"BENCHMARK_HARNESS_HISTORICAL_REPOSITORY_CONTEXT_REPAIR_ONLY",
            "original_A9_exact_timing_preserved_seconds":exact_seconds,
            "repaired_Hybrid_timing_seconds":hybrid_seconds,
            "exact_over_Hybrid_speedup":speedup,
            "fractional_wallclock_reduction":fractional,
            "Hybrid_faster_in_salvaged_characterization":faster,
            "strict_same_runner_pair_established":False,
            "strict_same_session_pair_established":False,
            "statistical_economic_qualification_performed":False,
            "performance_claim_allowed":"SALVAGED_ENGINEERING_CHARACTERIZATION_ONLY",
            "scientific_interpretation":scientific_interpretation,
            "production_qualified":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }
        provenance={
            "milestone":M,
            "original_A9_commit":PARENT,
            "original_A9_runner_blob":ORIGINAL_A9_BLOB,
            "original_A9_failed_stage":b.get("failed_stage"),
            "original_A9_exception":b.get("exception"),
            "preserved_exact_seconds":exact_seconds,
            "discarded_failed_Hybrid_seconds":float(timing["failed_Hybrid_seconds"]),
            "failure_cause":"A8_RUNNER_WAS_INVOKED_UNDER_A9_REPOSITORY_HEAD_AND_FAILED_ITS_HISTORICAL_PARENT_PROVENANCE_GATE_BEFORE_PHYSICS",
            "repair":"RUN_A8_IN_LOCAL_HISTORICAL_CLONE_RESET_TO_CERTIFIED_A8_COMMIT",
            "A8_historical_commit":A8_COMMIT,
            "A8_historical_parent":A8_PARENT,
            "Hybrid_physics_changed":False,
            "A8_source_changed":False,
            "exact_baseline_rerun":False,
        }

        if faster:
            classification=(
                "HYBRID_FASTER_IN_SALVAGED_ENGINEERING_CHARACTERIZATION_"
                "BUT_DAY100_SCIENTIFIC_ERROR_REMAINS_NOT_PRODUCTION_QUALIFIED"
            )
        else:
            classification=(
                "HYBRID_NOT_FASTER_IN_SALVAGED_ENGINEERING_CHARACTERIZATION_"
                "AND_DAY100_SCIENTIFIC_ERROR_REMAINS_NOT_PRODUCTION_QUALIFIED"
            )

        summary={
            "milestone":M,
            "status":PASS,
            "classification":classification,
            "original_A9_exact_wallclock_seconds":exact_seconds,
            "repaired_Hybrid_wallclock_seconds":hybrid_seconds,
            "exact_over_Hybrid_speedup":speedup,
            "fractional_wallclock_reduction":fractional,
            "Hybrid_faster_in_salvaged_characterization":faster,
            "strict_same_runner_pair_established":False,
            "strict_same_session_pair_established":False,
            "statistical_economic_qualification_performed":False,
            "benchmark_harness_repair_complete":True,
            "historical_A8_repository_context_used":True,
            "Day100_plume_support_topology_preserved":topology_preserved,
            "Day100_saturation_relative_L2":sat_rel,
            "Day100_refreshed_pressure_relative_L2":pressure_rel,
            "Day100_refreshed_flux_relative_L2":flux_rel,
            "Day100_stored_mass_relative_error":stored_rel,
            "Day100_cumulative_produced_mass_relative_error":produced_rel,
            "Day100_producer_gas_cut_absolute_error":cut_abs,
            "scientific_interpretation":scientific_interpretation,
            "integrated_runtime_architecture_complete":True,
            "trajectory_validation_complete":True,
            "performance_characterization_complete":True,
            "production_architecture_freeze_authorized":False,
            "3D_decision_support_visualization_authorized":True,
            "cadence_optimization_authorized_after_visualization":True,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }

        stage="publication"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/PROVENANCE).write_text(json.dumps(provenance,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/TIMING,timing_rows)
        write_csv(out/GATES,gates)
        write_csv(
            out/MANIFEST,
            [
                {"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                for p in sorted(out.iterdir())
                if p.is_file() and p.name!=MANIFEST
            ],
        )

        print("="*204)
        print(M,"PASS")
        print("Preserved exact wallclock seconds             :",exact_seconds)
        print("Repaired Hybrid wallclock seconds             :",hybrid_seconds)
        print("Exact / Hybrid speedup                        :",speedup)
        print("Fractional wallclock reduction                :",fractional)
        print("Hybrid faster                                 :",faster)
        print("Strict same-run paired timing                 : False")
        print("Statistical economic qualification            : False")
        print("Production qualification                      : LOCKED")
        print("3D decision-support visualization             : AUTHORIZED")
        print("="*204)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(
            json.dumps(
                {
                    "milestone":M,
                    "status":BLOCK,
                    "failed_stage":stage,
                    "exception":repr(exc),
                    "gates":gates,
                    "integrated_GPU_runtime_production_authorized":False,
                    "P4_authorized":False,
                },
                indent=2,
                sort_keys=True,
            )+"\n",
            encoding="utf-8",
        )
        print(M,"BLOCK")
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
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))
