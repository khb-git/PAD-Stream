#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,io,json,subprocess
from pathlib import Path
from typing import Any

M='POSTV16-AV4-PIVOT-P2-R6-R25-R2'
NAME='R25 Lexicographic Solver-Conditioning Repair Design Freeze — Exact Frontier Preserved'
PASS='AV4PIVOTP2R6R25R2_EXACT_FRONTIER_HIGHS_PRESOLVE_OFF_SOLVER_CONDITIONING_REPAIR_DESIGN_FREEZE_PASS_NO_STATE_MUTATION'
BLOCK='AV4PIVOTP2R6R25R2_TECHNICAL_OR_AUTHORITY_BLOCK'
BRANCH='postv16-av4-pivot'
PARENT='434abfe50e753830a27f9c9b07b93175050c3527'
RID='PAD_STREAM_V16_RC1_B92D52088D01078A'
BASE=Path('post_v16')/RID/'POSTV16_AV4_Dynamic_Flow_Coupling'

R25_FAIL_REL=BASE/'POSTV16_AV4_PIVOT_P2_R6_R25_SCIENTIFIC_FAIL'
R25_FAIL='POSTV16_AV4_PIVOT_P2_R6_R25_Scientific_Fail_Report.json'
R25_FAIL_SHA256='0a6b434db97e8a7f8052fb4eea53071a6fce6b8d325740a0562df6ff44a99678'
R25_FAIL_STATUS='AV4PIVOTP2R6R25_DAY375_CAPACITY_LIMITED_EXACT_SUPPORT_SPLIT_STATE_REPROJECTION_EXECUTION_SCIENTIFIC_FAIL_NO_AUTOMATIC_RERUN'
R25_FAIL_STAGE='stage2_minimum_L1_deviation'
R25_FAIL_GATE='stage2_min_L1_HiGHS'

R25R1_REL=BASE/'POSTV16_AV4_PIVOT_P2_R6_R25_R1_Stage2_Frontier_Feasibility_Numerical_Conditioning_Diagnostic_Freeze'
R25R1_SUMMARY='PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_R1_Summary.json'
R25R1_DIAGNOSTIC='POSTV16_AV4_PIVOT_P2_R6_R25_R1_Frontier_Feasibility_Diagnostic.json'
R25R1_DECISION='POSTV16_AV4_PIVOT_P2_R6_R25_R1_Decision_Contract.json'
R25R1_MANIFEST='POSTV16_AV4_PIVOT_P2_R6_R25_R1_Artifact_Manifest.csv'
R25R1_STATUS='AV4PIVOTP2R6R25R1_STAGE2_FRONTIER_FEASIBILITY_NUMERICAL_CONDITIONING_DIAGNOSTIC_PASS_NO_STATE_MUTATION'
R25R1_CLASSIFICATION='R6R25R1_STAGE1_WITNESS_VALID_EXACT_STAGE2_FEASIBLE_WITHOUT_PRESOLVE_HIGHS_PRESOLVE_CONDITIONING_FAILURE_DESIGN_REPAIR_NEXT'
STAGE1_MASS_KG=52457458.82473308
STAGE1_ACCEPTANCE_TOL_KG=0.005245745882473308
WITNESS_MAX_SUPPLY_CAPACITY_VIOLATION_KG=1.8189894035458565e-12
WITNESS_MAX_L1_EPIGRAPH_VIOLATION_KG=9.094947017729282e-13
WITNESS_EXACT_FRONTIER_EQUALITY_RESIDUAL_KG=0.0

R24_REL=BASE/'POSTV16_AV4_PIVOT_P2_R6_R24_Day375_R22_Geometry_Reprojection_Capacity_Representation_Design_Freeze'
R24_SUMMARY='PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R24_Summary.json'
R24_PROTOCOL='POSTV16_AV4_PIVOT_P2_R6_R24_Capacity_Aware_Reprojection_Protocol.json'
R24_DECISION='POSTV16_AV4_PIVOT_P2_R6_R24_Decision_Contract.json'
R24_MANIFEST='POSTV16_AV4_PIVOT_P2_R6_R24_Artifact_Manifest.csv'
R24_MAX_REPRESENTABLE_S0_MASS_KG=52457458.82473308
R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_KG=6646660.64504873

R25R1_RUNNER='PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_R1_Stage2_Frontier_Feasibility_Numerical_Conditioning_Diagnostic.py'
R25R1_BLOB='54e6dbc573c356e603ebbcddb3a85afac917063d'
R25_RUNNER='PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_Controlled_Day375_CapacityLimited_ExactSupport_SplitState_Reprojection_Execution.py'
R25_BLOB='55f0ebcc5dacdaf3b039cda434748d1e86d4d8ad'
R24_RUNNER='PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R24_Day375_R22_Geometry_Reprojection_Capacity_Representation_Design_Freeze.py'
R24_BLOB='9168baf3155e712b9c342239bed9ab4b1d787691'
SOURCE_BLOBS={R25R1_RUNNER:R25R1_BLOB,R25_RUNNER:R25_BLOB,R24_RUNNER:R24_BLOB}

OUT_TOKEN='POSTV16_AV4_PIVOT_P2_R6_R25_R2'
OUT_REL=BASE/(OUT_TOKEN+'_ExactFrontier_HiGHS_PresolveOff_SolverConditioning_Repair_Design_Freeze')
BLOCK_REL=BASE/(OUT_TOKEN+'_BLOCKED')

class GateError(RuntimeError): pass

def gt(root:Path,*args:str)->str: return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
def sha(path:Path)->str:
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''): h.update(chunk)
    return h.hexdigest()
def js(path:Path)->dict[str,Any]: return json.loads(path.read_text(encoding='utf-8'))
def csvr(path:Path)->list[dict[str,str]]:
    with open(path,newline='',encoding='utf-8') as f: return list(csv.DictReader(f))
def csvb(rows:list[dict[str,Any]])->bytes:
    if not rows:return b''
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    s=io.StringIO(newline=''); w=csv.DictWriter(s,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows);return s.getvalue().encode()
def jb(obj:Any)->bytes:return (json.dumps(obj,indent=2,sort_keys=True)+'\n').encode()
def manifest(directory:Path,filename:str)->dict[str,str]:
    out={}
    for row in csvr(directory/filename):
        p=directory/row['file']
        if not p.is_file(): raise GateError('manifest_missing:'+p.name)
        if sha(p)!=row['sha256']: raise GateError('manifest_sha:'+p.name)
        if p.stat().st_size!=int(row['bytes']): raise GateError('manifest_bytes:'+p.name)
        out[p.name]=row['sha256']
    return out

def selftest():
    assert OUT_REL.name.startswith(OUT_TOKEN+'_')
    assert BLOCK_REL.name==OUT_TOKEN+'_BLOCKED'
    protocol={'stage1_solver':{'method':'highs','presolve':True},'stage2_solver':{'method':'highs','presolve':False},'stage2_frontier_constraint':'sum(x) == M1 exactly','mass_floor_relaxation_authorized':False}
    assert protocol['stage2_solver']['presolve'] is False
    assert protocol['stage2_frontier_constraint']=='sum(x) == M1 exactly'
    assert protocol['mass_floor_relaxation_authorized'] is False
    print('POSTV16 AV4 PIVOT P2-R6-R25-R2 structural self-test: PASS')

def main(project_root:Path,drive_root:Path)->int:
    root=project_root.resolve();drive=drive_root.resolve();out=drive/OUT_REL;block_dir=drive/BLOCK_REL
    stage='preflight';gates=[]
    def gate(name,cond,detail=None):
        nonlocal stage
        ok=bool(cond);gates.append({'stage':stage,'gate':name,'pass':ok,'detail':'' if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"))
        if not ok: raise GateError(name)
    try:
        stage='preexisting_state_firewall'
        gate('no_preexisting_R25R2_PASS',not (out/f'PAD_Stream_{OUT_TOKEN}_Summary.json').exists())
        gate('no_preexisting_R25R2_BLOCK',not (block_dir/f'{OUT_TOKEN}_Blocked_Report.json').exists())

        stage='repository_authority'
        gate('branch_exact',gt(root,'branch','--show-current')==BRANCH)
        gate('parent_is_R25R1_commit',gt(root,'rev-parse','HEAD^')==PARENT)
        gate('repository_clean',gt(root,'status','--porcelain')=='')
        for filename,expected in SOURCE_BLOBS.items():
            p=root/filename;gate(Path(filename).stem+'_present',p.is_file(),str(p));actual=gt(root,'hash-object',str(p)) if p.is_file() else 'missing';gate(Path(filename).stem+'_blob_exact',actual==expected,actual)

        stage='R25_scientific_fail_authority'
        fp=drive/R25_FAIL_REL/R25_FAIL;gate('R25_FAIL_present',fp.is_file(),str(fp));gate('R25_FAIL_SHA_exact',sha(fp)==R25_FAIL_SHA256,sha(fp));f25=js(fp)
        gate('R25_FAIL_status_exact',f25.get('status')==R25_FAIL_STATUS,f25.get('status'));gate('R25_FAIL_stage_exact',f25.get('failed_stage')==R25_FAIL_STAGE);gate('R25_FAIL_gate_exact',f25.get('failed_gate')==R25_FAIL_GATE);gate('R25_FAIL_no_automatic_rerun',f25.get('automatic_rerun_authorized') is False)

        stage='R25R1_diagnostic_authority'
        r1=drive/R25R1_REL;manifest(r1,R25R1_MANIFEST);s1=js(r1/R25R1_SUMMARY);d1=js(r1/R25R1_DECISION);diag1=js(r1/R25R1_DIAGNOSTIC)
        gate('R25R1_status_exact',s1.get('status')==R25R1_STATUS,s1.get('status'));gate('R25R1_classification_exact',s1.get('classification')==R25R1_CLASSIFICATION,s1.get('classification'));gate('R25R1_source_FAIL_SHA_exact',s1.get('source_R25_SCIENTIFIC_FAIL_sha256')==R25_FAIL_SHA256)
        gate('R25R1_stage1_mass_exact',abs(float(s1['stage1_reproduced_mass_kg'])-STAGE1_MASS_KG)<=1e-9)
        gate('R25R1_stage1_acceptance_tolerance_exact',abs(float(s1['stage1_frozen_acceptance_tolerance_kg'])-STAGE1_ACCEPTANCE_TOL_KG)<=1e-15)
        gate('R25R1_witness_supply_capacity_residual_exact',abs(float(s1['stage1_witness_maximum_supply_or_capacity_violation_kg'])-WITNESS_MAX_SUPPLY_CAPACITY_VIOLATION_KG)<=1e-15)
        gate('R25R1_witness_L1_epigraph_residual_exact',abs(float(s1['stage1_witness_maximum_L1_epigraph_violation_kg'])-WITNESS_MAX_L1_EPIGRAPH_VIOLATION_KG)<=1e-15)
        gate('R25R1_witness_frontier_equality_exact',float(s1['stage1_witness_exact_frontier_equality_residual_kg'])==0.0)
        gate('R25R1_witness_valid',s1.get('stage1_witness_feasible_within_frozen_optimum_tolerance') is True)
        gate('R25R1_exact_stage2_no_presolve_success',s1.get('exact_stage2_without_presolve_success') is True)
        gate('R25R1_exact_stage2_no_presolve_optimal',int(s1['exact_stage2_without_presolve_status'])==0 and 'Optimal' in str(s1['exact_stage2_without_presolve_message']))
        gate('R25R2_authorized',d1.get('P2_R6_R25_R2_authorized') is True);gate('R25R2_design_only',d1.get('P2_R6_R25_R2_design_only') is True);gate('R25R2_execution_not_authorized',d1.get('P2_R6_R25_R2_execution_authorized') is False)

        stage='R24_representation_authority'
        r24=drive/R24_REL;manifest(r24,R24_MANIFEST);s24=js(r24/R24_SUMMARY);p24=js(r24/R24_PROTOCOL);d24=js(r24/R24_DECISION)
        gate('R24_maximum_representable_mass_exact',abs(float(s24['maximum_representable_S0_mass_kg'])-R24_MAX_REPRESENTABLE_S0_MASS_KG)<=1e-9);gate('R24_minimum_unavoidable_residual_exact',abs(float(s24['minimum_unavoidable_S0_residual_kg'])-R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_KG)<=1e-9);gate('R24_representation_amendment_required',s24.get('representation_amendment_required') is True);gate('R24_full_S0_infeasible',s24.get('full_S0_exact_support_capacity_feasible') is False)
        gate('R24_stage1_semantics_preserved',p24.get('R25_lexicographic_execution_objective',{}).get('stage1')=='maximize total accepted Day375 Cartesian component mass represented on R22 exact (cell,CV) support subject to per-cell supply and frozen CV capacity')
        gate('R24_stage2_semantics_preserved',p24.get('R25_lexicographic_execution_objective',{}).get('stage2')=='subject to the stage1 optimum, minimize L1 deviation from the original F1-R2 PV-normalized-transpose edge-mass target')
        gate('support_growth_still_forbidden',d24.get('automatic_support_growth_authorized') is False);gate('reverse_H1_pullback_still_forbidden',d24.get('reverse_H1_to_S0_pullback_authorized') is False)

        stage='R25R3_execution_protocol_freeze'
        protocol={
          'milestone':M,'name':NAME,'status':PASS,'classification':'R25_STAGE2_SOLVER_CONDITIONING_REPAIR_EXACT_FRONTIER_PRESERVED_PRESOLVE_OFF_FOR_STAGE2_ONLY',
          'source_authorities':{'R25_scientific_fail_sha256':R25_FAIL_SHA256,'R25_R1_summary':R25R1_SUMMARY,'R24_protocol':R24_PROTOCOL},
          'unchanged_scientific_semantics':{
            'stage1_objective':'maximize total accepted Day375 Cartesian component mass represented on R22 exact support under per-cell supply and frozen CV capacity',
            'stage1_maximum_representable_mass_kg':STAGE1_MASS_KG,
            'stage2_objective':'minimize L1 deviation from the original F1-R2 PV-normalized-transpose edge-mass target subject to the exact Stage-1 optimum',
            'stage2_exact_frontier_constraint':'sum(x) == 52457458.82473308 kg',
            'minimum_unavoidable_S0_residual_kg':R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_KG,
            'capacity_limited_split_state_representation_unchanged':True},
          'solver_conditioning_repair':{
            'stage1':{'method':'highs','presolve':True,'unchanged_from_R25':True},
            'stage2':{'method':'highs','presolve':False,'only_change_from_R25':True,'reason':'R25-R1 proved the Stage-1 witness satisfies Stage-2 constraints and the exact Stage-2 problem solves optimally with HiGHS presolve disabled'},
            'mass_floor_relaxation_authorized':False,'stage1_mass_relaxation_authorized':False,'fallback_solver_configuration_authorized':False,'automatic_retry_authorized':False},
          'execution_prechecks':{'recompute_stage1_and_require_R24_mass_within_frozen_tolerance':True,'evaluate_stage1_solution_as_explicit_stage2_witness':True,'require_witness_supply_capacity_residual_within_frozen_tolerance':True,'require_witness_L1_epigraph_residual_within_frozen_tolerance':True,'require_witness_exact_frontier_residual_within_frozen_tolerance':True},
          'execution_firewalls':{'old_CV_ownership_reuse':False,'support_growth':False,'reverse_H1_to_S0_pullback':False,'mass_discard_or_clipping':False,'global_mass_rescaling':False,'mapback':False,'transport_time_advance':False,'physical_time_advance':False,'P3_authorized':False},
          'failure_semantics':{'if_stage2_no_presolve_fails':'immutable SCIENTIFIC FAIL; no fallback to relaxed frontier, alternate support, automatic retry, or state mutation'} }
        summary={'milestone':M,'name':NAME,'status':PASS,'classification':protocol['classification'],'source_R25_SCIENTIFIC_FAIL_sha256':R25_FAIL_SHA256,'source_R25R1_classification':R25R1_CLASSIFICATION,'stage1_maximum_representable_mass_kg':STAGE1_MASS_KG,'stage1_frozen_acceptance_tolerance_kg':STAGE1_ACCEPTANCE_TOL_KG,'stage1_witness_maximum_supply_or_capacity_violation_kg':WITNESS_MAX_SUPPLY_CAPACITY_VIOLATION_KG,'stage1_witness_maximum_L1_epigraph_violation_kg':WITNESS_MAX_L1_EPIGRAPH_VIOLATION_KG,'stage1_witness_exact_frontier_equality_residual_kg':WITNESS_EXACT_FRONTIER_EQUALITY_RESIDUAL_KG,'exact_stage2_without_presolve_proven_feasible':True,'stage1_solver_presolve':True,'stage2_solver_presolve':False,'exact_stage1_frontier_preserved':True,'mass_floor_relaxation_frozen_out':True,'representation_semantics_changed':False,'state_mutation_executed':False,'support_growth_executed':False,'mapback_executed':False,'physical_time_advance_executed':False,'P3_authorized':False}
        decision={'milestone':M,'status':PASS,'classification':protocol['classification'],'P2_R6_R25_R3_authorized':True,'P2_R6_R25_R3_name':'Controlled Day375 Capacity-Limited Exact-Support Split-State Reprojection Execution — Stage2 HiGHS Presolve Disabled','P2_R6_R25_R3_execution_authorized':True,'P2_R6_R25_R3_must_bind_R25_FAIL_SHA':True,'P2_R6_R25_R3_R25_FAIL_sha256':R25_FAIL_SHA256,'P2_R6_R25_R3_must_bind_R25R2_protocol':True,'exact_stage1_frontier_must_be_preserved':True,'stage2_HiGHS_presolve_must_be_false':True,'mass_floor_relaxation_authorized':False,'automatic_retry_authorized':False,'support_growth_authorized':False,'reverse_H1_to_S0_pullback_authorized':False,'mapback_execution_authorized':False,'transport_time_advance_authorized':False,'physical_time_advance_authorized':False,'P3_authorized':False,'P4_authorized':False,'P5_training_authorized':False}

        stage='design_freeze_publication';out.mkdir(parents=True,exist_ok=False)
        (out/f'PAD_Stream_{OUT_TOKEN}_Summary.json').write_bytes(jb(summary));(out/f'{OUT_TOKEN}_ExactFrontier_SolverConditioning_Repair_Protocol.json').write_bytes(jb(protocol));(out/f'{OUT_TOKEN}_Decision_Contract.json').write_bytes(jb(decision));(out/f'{OUT_TOKEN}_Final_Gate_Matrix.csv').write_bytes(csvb(gates))
        rows=[]
        for p in sorted(out.iterdir()):
            if p.is_file(): rows.append({'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size})
        (out/f'{OUT_TOKEN}_Artifact_Manifest.csv').write_bytes(csvb(rows))
        print('='*180);print(M,'PASS');print('Classification                           :',summary['classification']);print('R25 SCIENTIFIC FAIL SHA256               :',R25_FAIL_SHA256);print('Stage1 maximum mass kg                   :',STAGE1_MASS_KG);print('Stage1 acceptance tolerance kg           :',STAGE1_ACCEPTANCE_TOL_KG);print('Witness max supply/capacity residual kg  :',WITNESS_MAX_SUPPLY_CAPACITY_VIOLATION_KG);print('Witness max L1 epigraph residual kg      :',WITNESS_MAX_L1_EPIGRAPH_VIOLATION_KG);print('Witness exact frontier residual kg       :',WITNESS_EXACT_FRONTIER_EQUALITY_RESIDUAL_KG);print('Stage1 presolve                          : True');print('Stage2 presolve                          : False');print('Exact Stage1 frontier preserved          : True');print('Mass-floor relaxation authorized         : False');print('R25-R3 execution authorized              : True');print('State/support/mapback/time mutation      : False / False / False / False');print('P3 authorized                            : False');print('='*180);return 0
    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True);p=block_dir/f'{OUT_TOKEN}_Blocked_Report.json'
        if not p.exists(): p.write_bytes(jb({'milestone':M,'status':BLOCK,'failed_stage':stage,'exception':repr(exc),'R25_SCIENTIFIC_FAIL_preserved':True,'R25_R1_PASS_preserved':True,'R24_design_preserved':True,'state_mutation_executed':False,'support_growth_executed':False,'mapback_executed':False,'physical_time_advance_executed':False,'P3_authorized':False,'automatic_rerun_authorized':False,'gates_completed':gates}))
        print('='*180);print(M,'TECHNICAL / AUTHORITY BLOCK');print('Stage    :',stage);print('Exception:',repr(exc));print('='*180);return 2

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,default=Path('.'));ap.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'));ap.add_argument('--self-test',action='store_true');args=ap.parse_args()
    if args.self_test:selftest();raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))
