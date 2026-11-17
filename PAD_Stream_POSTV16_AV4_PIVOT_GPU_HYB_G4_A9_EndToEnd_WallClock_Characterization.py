#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,shutil,subprocess,sys,time
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-A9"
PASS="POSTV16AV4PIVOTGPUHYBG4A9_ENDTOEND_WALLCLOCK_CHARACTERIZATION_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG4A9_TECHNICAL_OR_TIMING_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="8240c6899c1c02fd0f25294b4ec1285900e700f3"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
A8_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A8_Day100_Production_Trajectory_Validation.py"
A8_BLOB="65006bfdc44630746d4c45c6d8696560b70efef6"
R3R7_RUNNER="PAD_Stream_V16E41R3R7_Repaired_Production_Rollout_to_Exact_100Day_Observation.py"
R3R7_BLOB="1e7e54f17477788fe518e440c21a65a544b30a48"
OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A9"
OUT_REL=BASE/(OUT_TOKEN+"_EndToEnd_WallClock_Characterization")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
TIMING=f"{OUT_TOKEN}_Timing.csv"
DECISION=f"{OUT_TOKEN}_Decision.json"
ENV=f"{OUT_TOKEN}_Environment.json"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"
A8_SUM_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G4_A8_Day100_Production_Trajectory_Validation"/"PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A8_Summary.json"
A8_STATUS="POSTV16AV4PIVOTGPUHYBG4A8_DAY100_PRODUCTION_TRAJECTORY_VALIDATION_COMPLETE"

class GateError(RuntimeError): pass

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def gt(root:Path,*a:str)->str:
    return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()

def blob(root:Path,p:Path)->str:return gt(root,'hash-object',str(p))
def js(p:Path):return json.loads(p.read_text(encoding='utf-8'))

def mod(root:Path,fn:str,expected:str,name:str):
    p=root/fn
    if not p.is_file(): raise GateError(f'missing_source:{fn}')
    actual=blob(root,p)
    if actual!=expected: raise GateError(f'source_blob:{fn}:{actual}:{expected}')
    s=importlib.util.spec_from_file_location(name,p)
    if s is None or s.loader is None: raise GateError(f'import_spec:{fn}')
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def write_csv(p:Path,rows:list[dict[str,Any]]):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)

def capture(cmd:list[str])->str:
    try:return subprocess.check_output(cmd,text=True,stderr=subprocess.STDOUT).strip()
    except Exception as exc:return f'UNAVAILABLE:{repr(exc)}'

def selftest():
    assert len(PARENT)==40
    print('POSTV16 GPU-HYB-G4-A9 structural self-test: PASS')

def run_timed(label:str,module:Any,root:Path,drive:Path,tmp_out:Path,tmp_block:Path)->dict[str,Any]:
    if tmp_out.exists(): shutil.rmtree(tmp_out)
    if tmp_block.exists(): shutil.rmtree(tmp_block)
    module.OUT_REL=tmp_out
    if hasattr(module,'BLOCK_REL'): module.BLOCK_REL=tmp_block
    if hasattr(module,'BLOCKED_REL'): module.BLOCKED_REL=tmp_block
    t0=time.perf_counter(); rc=int(module.main(root,drive)); elapsed=float(time.perf_counter()-t0)
    return {'branch':label,'return_code':rc,'wallclock_seconds':elapsed,'local_output_dir':str(tmp_out)}

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage='preflight'
    def gate(n,c,d=None):
        ok=bool(c);gates.append({'stage':stage,'gate':n,'pass':ok,'detail':'' if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok: raise GateError(n)
    try:
        print('='*202)
        print('G4-A9 — SINGLE-PAIR END-TO-END WALL-CLOCK CHARACTERIZATION')
        print('EXACT R3-R7 DAY69.883→100 VS INTEGRATED HYBRID A8 DAY69.883→100 IN THE SAME SESSION.')
        print('NO STATISTICAL ECONOMIC QUALIFICATION. NO PRODUCTION AUTHORIZATION. HYBRID RUN IS TIMED SECOND, INCLUDING MODEL INITIALIZATION.')
        print('='*202)
        stage='repository'
        gate('branch_exact',gt(root,'branch','--show-current')==BRANCH,gt(root,'branch','--show-current'))
        gate('parent_is_G4_A8',gt(root,'rev-parse','HEAD^')==PARENT,gt(root,'rev-parse','HEAD^'))
        gate('repository_clean',gt(root,'status','--porcelain')=='')
        a8=mod(root,A8_RUNNER,A8_BLOB,'g4a9_a8')
        exact=mod(root,R3R7_RUNNER,R3R7_BLOB,'g4a9_exact')

        stage='A8_scientific_authority'
        a8s=js(drive/A8_SUM_REL)
        gate('A8_status_exact',a8s.get('status')==A8_STATUS,a8s.get('status'))
        gate('A8_validation_complete',a8s.get('trajectory_validation_complete') is True)
        gate('A8_scientific_interpretation_required',a8s.get('scientific_interpretation_required') is True)
        gate('A8_review_ready',a8s.get('G4_A9_performance_benchmark_review_ready') is True)
        gate('A8_production_locked',a8s.get('integrated_GPU_runtime_production_authorized') is False)
        gate('A8_P4_locked',a8s.get('P4_authorized') is False)
        sat_rel=float(a8s['mixed_100d_vs_exact_saturation_relative_L2'])
        pressure_rel=float(a8s['mixed_vs_exact_100d_refreshed_pressure_relative_L2'])
        flux_rel=float(a8s['mixed_vs_exact_100d_refreshed_flux_relative_L2'])
        stored_rel=float(a8s['mixed_100d_stored_mass_relative_error'])
        produced_rel=float(a8s['mixed_100d_cumulative_produced_mass_relative_error'])
        cut_abs=abs(float(a8s['mixed_100d_minus_exact_producer_gas_cut']))
        topo=(int(a8s['mixed_100d_minus_exact_active_cell_count'])==0 and int(a8s['mixed_100d_minus_exact_visible_cell_count'])==0)
        scientific_profile={
            'plume_support_topology_preserved':topo,
            'saturation_relative_L2':sat_rel,
            'refreshed_pressure_relative_L2':pressure_rel,
            'refreshed_flux_relative_L2':flux_rel,
            'stored_mass_relative_error':stored_rel,
            'cumulative_produced_mass_relative_error':produced_rel,
            'producer_gas_cut_absolute_error':cut_abs,
            'interpretation':'MODERATE_ACCUMULATED_TRANSPORT_AND_PRODUCER_ERROR_WITH_TIGHTER_PRESSURE_AND_PRESERVED_PLUME_SUPPORT',
            'production_qualified':False,
        }

        stage='environment'
        env={
            'python':sys.version,
            'platform':capture(['uname','-a']),
            'nvidia_smi':capture(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader']),
            'cpu_count':capture(['bash','-lc','nproc']),
            'timing_timer':'time.perf_counter',
            'timing_order':'EXACT_FIRST_THEN_HYBRID',
            'timing_pairs':1,
            'warmup_full_trajectories':0,
            'statistical_economic_qualification':False,
            'Hybrid_model_initialization_in_timed_region':True,
            'benchmark_outputs_written_to_local_content_not_Drive':True,
        }

        stage='paired_end_to_end_timing'
        base=Path('/content/PAD_Stream_G4_A9_Benchmark')
        if base.exists():shutil.rmtree(base)
        base.mkdir(parents=True)
        print('--- A9 EXACT BASELINE TIMING ---',flush=True)
        exact_result=run_timed('EXACT_R3R7',exact,root,drive,base/'exact_output',base/'exact_block')
        gate('exact_benchmark_exit_zero',exact_result['return_code']==0,exact_result)
        print('--- A9 HYBRID INTEGRATED TIMING ---',flush=True)
        hybrid_result=run_timed('HYBRID_A8',a8,root,drive,base/'hybrid_output',base/'hybrid_block')
        gate('Hybrid_benchmark_exit_zero',hybrid_result['return_code']==0,hybrid_result)
        exact_seconds=float(exact_result['wallclock_seconds']); hybrid_seconds=float(hybrid_result['wallclock_seconds'])
        gate('timings_positive_finite',np.isfinite(exact_seconds) and np.isfinite(hybrid_seconds) and exact_seconds>0 and hybrid_seconds>0,(exact_seconds,hybrid_seconds))
        speedup=exact_seconds/hybrid_seconds
        fractional=(exact_seconds-hybrid_seconds)/exact_seconds
        faster=hybrid_seconds<exact_seconds

        stage='characterization'
        timing_rows=[{**exact_result,'order_index':1},{**hybrid_result,'order_index':2}]
        decision={
            'milestone':M,'status':PASS,
            'benchmark_type':'SINGLE_PAIR_END_TO_END_CHARACTERIZATION_NOT_STATISTICAL_QUALIFICATION',
            'exact_seconds':exact_seconds,'Hybrid_seconds':hybrid_seconds,
            'exact_over_Hybrid_speedup':speedup,'fractional_wallclock_reduction':fractional,
            'Hybrid_faster_in_single_pair':faster,'scientific_profile':scientific_profile,
            'performance_claim_allowed':'SINGLE_SESSION_ENGINEERING_CHARACTERIZATION_ONLY',
            'statistical_economic_qualification_authorized':False,
            'integrated_GPU_runtime_production_authorized':False,'P4_authorized':False,
        }
        classification=(
            'HYBRID_INTEGRATED_RUNTIME_FASTER_IN_SINGLE_PAIR_BUT_DAY100_SCIENTIFIC_ERROR_PRECLUDES_PRODUCTION_QUALIFICATION'
            if faster else
            'HYBRID_INTEGRATED_RUNTIME_NOT_FASTER_IN_SINGLE_PAIR_AND_DAY100_SCIENTIFIC_ERROR_PRECLUDES_PRODUCTION_QUALIFICATION'
        )
        summary={
            'milestone':M,'status':PASS,'classification':classification,
            'exact_wallclock_seconds':exact_seconds,'Hybrid_wallclock_seconds':hybrid_seconds,
            'exact_over_Hybrid_speedup':speedup,'fractional_wallclock_reduction':fractional,
            'Hybrid_faster_in_single_pair':faster,'timing_pairs_completed':1,
            'full_trajectory_warmup_pairs_completed':0,'timing_order':'EXACT_FIRST_THEN_HYBRID',
            'statistical_economic_qualification_performed':False,
            'scientific_interpretation':scientific_profile['interpretation'],
            'Day100_plume_support_topology_preserved':topo,
            'Day100_saturation_relative_L2':sat_rel,'Day100_refreshed_pressure_relative_L2':pressure_rel,
            'Day100_refreshed_flux_relative_L2':flux_rel,'Day100_stored_mass_relative_error':stored_rel,
            'Day100_cumulative_produced_mass_relative_error':produced_rel,'Day100_producer_gas_cut_absolute_error':cut_abs,
            'integrated_runtime_architecture_complete':True,'trajectory_validation_complete':True,
            'performance_characterization_complete':True,'production_architecture_freeze_authorized':False,
            '3D_decision_support_visualization_authorized':True,'cadence_optimization_authorized_after_visualization':True,
            'integrated_GPU_runtime_production_authorized':False,'P4_authorized':False,
        }

        stage='publication'
        gate('output_absent',not out.exists(),str(out));out.mkdir(parents=True)
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        (out/ENV).write_text(json.dumps(env,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        write_csv(out/TIMING,timing_rows);write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[{'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST])
        print('='*202);print(M,'PASS')
        print('Exact wallclock seconds                        :',exact_seconds)
        print('Hybrid wallclock seconds                       :',hybrid_seconds)
        print('Exact / Hybrid speedup                         :',speedup)
        print('Fractional wallclock reduction                 :',fractional)
        print('Hybrid faster in single pair                   :',faster)
        print('Day100 saturation relL2                        :',sat_rel)
        print('Day100 refreshed pressure relL2                :',pressure_rel)
        print('Day100 refreshed flux relL2                    :',flux_rel)
        print('Production qualification                       : LOCKED')
        print('3D decision-support visualization              : AUTHORIZED')
        print('='*202)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f'{OUT_TOKEN}_Blocked_Report.json').write_text(json.dumps({
            'milestone':M,'status':BLOCK,'failed_stage':stage,'exception':repr(exc),'gates':gates,
            'statistical_economic_qualification_performed':False,'integrated_GPU_runtime_production_authorized':False,'P4_authorized':False,
        },indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print(M,'BLOCK');print('Stage:',stage);print('Exception:',repr(exc));return 2

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,default=Path('.'));ap.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'));ap.add_argument('--self-test',action='store_true')
    a=ap.parse_args()
    if a.self_test:selftest();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
