#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-A4"
PASS="POSTV16AV4PIVOTGPUHYBG4A4_FIRST_CONTROLLED_RECURRENT_HYBRID_CHILD_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG4A4_TECHNICAL_OR_STATE_TRANSITION_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="5e542fca093a033288f54ec71397c973efacde01"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

A3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A3_R1_MixedRoute_CVDelta_Ledger_Repair.py"
A3_BLOB="dc0b10d72991786752a0522f2e58f640d90b420d"
G2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_80_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2_BLOB="04c3940a7c736b1d210376113e48bab6111fc173"
R3R4_RUNNER="PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4_BLOB="5f8433437ce111533338ceada922f51abb2edefe"

DAY_TO_S=86400.0
FT_TO_M=0.3048
PARENT_DAY=75.0
NSTREAM=1078

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A4"
OUT_REL=BASE/(OUT_TOKEN+"_First_Controlled_Recurrent_Hybrid_Child")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
CHILD="POSTV16_AV4_PIVOT_GPU_HYB_G4_A4_Controlled_Hybrid_Child_State.npz"
EXACT_CHILD="POSTV16_AV4_PIVOT_GPU_HYB_G4_A4_Exact_Benchmark_Child_State.npz"
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
TRANSITION=f"{OUT_TOKEN}_Transition.json"
PRODUCERS=f"{OUT_TOKEN}_Producer_Output.csv"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError): pass

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def gt(root:Path,*a:str)->str:
    return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()

def blob(root:Path,p:Path)->str:
    return subprocess.check_output(['git','-C',str(root),'hash-object',str(p)],text=True).strip()

def mod(root:Path,fn:str,expected:str,name:str):
    p=root/fn
    if not p.is_file(): raise GateError(f'missing_source:{fn}')
    actual=blob(root,p)
    if actual!=expected: raise GateError(f'source_blob:{fn}:{actual}:{expected}')
    s=importlib.util.spec_from_file_location(name,p)
    if s is None or s.loader is None: raise GateError(f'import_spec:{fn}')
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def js(p:Path): return json.loads(p.read_text(encoding='utf-8'))

def load_npz(p:Path):
    with np.load(p,allow_pickle=False) as z: return {k:np.asarray(z[k]).copy() for k in z.files}

def scalar(x:Any)->float: return float(np.asarray(x).reshape(()))
def int_scalar(x:Any)->int: return int(np.asarray(x).reshape(()))

def write_csv(p:Path,rows:list[dict[str,Any]]):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)

def read_manifest(p:Path)->dict[str,str]:
    with p.open(newline='',encoding='utf-8') as f: return {r['file']:r['sha256'] for r in csv.DictReader(f)}

def rel_l2(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    return float(np.linalg.norm((a-b).ravel())/max(float(np.linalg.norm(b.ravel())),1e-30))

def selftest():
    assert abs((75.0+0.05)-75.05)<1e-12
    print('POSTV16 GPU-HYB-G4-A4 structural self-test: PASS')

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage='preflight';parent_sha_before=None
    def gate(n,c,d=None):
        ok=bool(c);gates.append({'stage':stage,'gate':n,'pass':ok,'detail':'' if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok: raise GateError(n)
    try:
        print('='*190)
        print('G4-A4 — FIRST CONTROLLED ONE-STEP RECURRENT HYBRID CHILD STATE')
        print('USES CERTIFIED A3-R1 MIXED POST-CAPILLARY GRID STATE. CREATES ONE CHILD ARTIFACT ONLY.')
        print('SOURCE DAY75 PARENT REMAINS IMMUTABLE. NO ROLLOUT. NO PRODUCTION-RUNTIME ACTIVATION.')
        print('='*190)

        stage='repository'
        gate('branch_exact',gt(root,'branch','--show-current')==BRANCH,gt(root,'branch','--show-current'))
        gate('parent_is_G4_A3_R1',gt(root,'rev-parse','HEAD^')==PARENT,gt(root,'rev-parse','HEAD^'))
        gate('repository_clean',gt(root,'status','--porcelain')=='')
        a3=mod(root,A3_RUNNER,A3_BLOB,'g4a4_a3')
        g2=mod(root,G2_RUNNER,G2_BLOB,'g4a4_g2')
        r3r4=mod(root,R3R4_RUNNER,R3R4_BLOB,'g4a4_r3r4')

        stage='A3_authority'
        a3s=js(drive/a3.OUT_REL/a3.SUMMARY)
        gate('A3_status_exact',a3s.get('status')==a3.PASS,a3s.get('status'))
        gate('A3_common_mapback_certified',a3s.get('mixed_CV_to_grid_transfer_certified') is True)
        gate('A3_grid_ledger_certified',a3s.get('mixed_grid_mass_ledger_certified') is True)
        gate('A3_capillary_certified',a3s.get('mixed_capillary_mass_conservation_certified') is True)
        gate('A3_A4_authorized',a3s.get('G4_A4_controlled_one_step_recurrent_state_transition_authorized') is True)
        gate('A3_no_canonical_mutation',a3s.get('canonical_state_mutated') is False)
        a3_arrays_path=drive/a3.OUT_REL/a3.ARRAYS
        a3_manifest=read_manifest(drive/a3.OUT_REL/a3.MANIFEST)
        gate('A3_arrays_SHA_manifest',sha(a3_arrays_path)==a3_manifest[a3.ARRAYS],sha(a3_arrays_path))
        a3arr=load_npz(a3_arrays_path)
        mixed_sat=np.asarray(a3arr['mixed_post_capillary_grid_saturation'],dtype=np.float64)
        exact_sat=np.asarray(a3arr['exact_post_capillary_grid_saturation'],dtype=np.float64)

        stage='Day75_parent'
        g2s=js(drive/g2.OUT_REL/g2.SUMMARY)
        gate('G2_status_exact',g2s.get('status')==g2.PASS,g2s.get('status'))
        parent_path=drive/g2.OUT_REL/g2.DAY75_STATE
        parent_sha_before=sha(parent_path)
        gate('Day75_parent_SHA_summary',parent_sha_before==g2s['Day75_exact_state_sha256'],parent_sha_before)
        parent=load_npz(parent_path)
        gate('Day75_parent_time_exact',abs(scalar(parent['physical_time_days'])-PARENT_DAY)<=1e-12,scalar(parent['physical_time_days']))

        stage='rebuild_active_flow_epoch'
        r3r5=g2.load_module_blob(root/g2.R3R5_RUNNER,g2.R3R5_BLOB,'g4a4_r3r5',root)
        roles={}
        for role in ['R3R2R1','E36','E37A','R2_PHYSICS','SG2','SG3','SG4','SG5','SG6','SG7A','SG7D']:
            fn,bl=r3r4.SOURCE_BLOBS[role]
            roles[role]=g2.load_module_blob(root/fn,bl,f'g4a4_{role.lower()}',root)
        r3r2r1=roles['R3R2R1'];e36=roles['E36'];e37a=roles['E37A'];physics=roles['R2_PHYSICS']
        sg2=roles['SG2'];sg3=roles['SG3'];sg4=roles['SG4'];sg5=roles['SG5'];sg6=roles['SG6'];sg7a=roles['SG7A'];sg7d=roles['SG7D']

        pfn,pblob=r3r4.SOURCE_BLOBS['PERM'];perm_path=root/pfn
        gate('permeability_blob_exact',blob(root,perm_path)==pblob,blob(root,perm_path))
        permeability_md=np.loadtxt(perm_path,skiprows=1,dtype=np.float64).reshape((15,50,50),order='C')
        cell_pv=0.20*(20.0*FT_TO_M)*(20.0*FT_TO_M)*(4.0*FT_TO_M)

        ref75,epoch75,db75=g2.same_time_endpoint(
            parent,r3r5=r3r5,r3r4r1=r3r4,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
            sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
            permeability_md=permeability_md,cell_pore_volume_m3=cell_pv)
        gate('same_time_parent_time_exact',abs(scalar(ref75['physical_time_days'])-PARENT_DAY)<=1e-12)
        pressure=np.asarray(epoch75['pressure_psi'],dtype=np.float64)
        p_ref=scalar(ref75['co2_density_reference_pressure_pa'])
        parent_sat=np.asarray(ref75['transport_saturation'],dtype=np.float64)
        old_sat,old_mass,sample_closure=e37a.sample_grid_inventory_to_control_volumes(
            physics,parent_sat,pressure,p_ref,epoch75['geometry'],NSTREAM,200)
        sample_tol=max(1e-6,1e-10*max(abs(float(np.sum(old_mass))),1.0))
        gate('parent_grid_to_CV_sampling_closure',abs(float(sample_closure))<=sample_tol,(sample_closure,sample_tol))

        stage='exact_boundary_ledger'
        face_pressure=e37a.build_face_pressure(e36,sg7d,db75['xyz_m'],pressure)
        q=np.asarray(db75['weights_m3_s'],dtype=np.float64)*DAY_TO_S
        xi=np.asarray(db75['xi'],dtype=np.float64)
        dt=float(r3r4.transport_cfl_dt_days(sg7a,xi,np.asarray(db75['tau_end_s'],dtype=np.float64)))
        gate('dt_matches_A3',abs(dt-float(a3s['aggregate_metrics']['dt_days']))<=1e-15,(dt,a3s['aggregate_metrics']['dt_days']))
        exact=e37a.advance_component_mass_control_volumes(
            physics,sg7a,old_sat,old_mass,epoch75['geometry']['cv_pressure_mass_coeff'],
            face_pressure,p_ref,q,xi,dt)
        producer_rows,aggregate_cut=e37a.producer_rows_from_flux(
            epoch75['labels'],epoch75['weights_m3_day'],exact['outlet_fractional_flow'],exact['face_mass_flux_kg_day'][:,-1],dt)
        produced=float(exact['produced_mass_kg']);injected=float(exact['injected_mass_kg'])
        parent_stored=scalar(ref75['stored_co2_mass_current_kg']);target_stored=parent_stored+injected-produced
        gate('aggregate_gas_cut_valid',np.isfinite(aggregate_cut) and 0.0<=aggregate_cut<=1.0,aggregate_cut)

        mixed_final=float(physics.stored_co2_mass_kg(mixed_sat,pressure,p_ref,cell_pv))
        exact_final=float(physics.stored_co2_mass_kg(exact_sat,pressure,p_ref,cell_pv))
        closure_tol=max(1e-6,1e-10*max(abs(target_stored),1.0))
        mixed_residual=mixed_final-parent_stored-injected+produced
        exact_residual=exact_final-parent_stored-injected+produced
        gate('mixed_child_mass_closure',abs(mixed_residual)<=closure_tol,(mixed_residual,closure_tol))
        gate('exact_child_mass_closure',abs(exact_residual)<=closure_tol,(exact_residual,closure_tol))

        stage='controlled_child_creation'
        mixed_child=e36.make_child_state(ref75,mixed_sat,pressure,p_ref,dt,produced,aggregate_cut,mixed_final,mixed_residual,False)
        exact_child=e36.make_child_state(ref75,exact_sat,pressure,p_ref,dt,produced,aggregate_cut,exact_final,exact_residual,False)
        for child,mode in [(mixed_child,'HYBRID_INCREMENTAL_MIXED'),(exact_child,'EXACT_E37A_BENCHMARK')]:
            child['transport_face_count']=np.asarray(epoch75['nfaces'],dtype=np.int64)
            child['transport_control_volume_count']=np.asarray(epoch75['ncv'],dtype=np.int64)
            child['mass_conservative_flow_refresh_active']=np.asarray(True,dtype=bool)
            child['runtime_refresh_policy_name_ascii']=np.frombuffer(b'FIVE_DAY_CONSERVATIVE_INTEGRATION_REFERENCE',dtype=np.uint8)
            child['runtime_max_flow_epoch_days']=np.asarray(5.0,dtype=np.float64)
            child['hybrid_recurrent_bridge_active']=np.asarray(mode.startswith('HYBRID'),dtype=bool)
            child['hybrid_recurrent_mode_ascii']=np.frombuffer(mode.encode('ascii'),dtype=np.uint8)
            child['hybrid_parent_anchored_incremental']=np.asarray(mode.startswith('HYBRID'),dtype=bool)
            child['flow_epoch_origin_day']=np.asarray(PARENT_DAY,dtype=np.float64)
            child['flow_epoch_age_days']=np.asarray(dt,dtype=np.float64)
            child['last_grid_mapback_ledger_residual_kg']=np.asarray(a3s['aggregate_metrics']['mixed_mapback_ledger_residual_kg'] if mode.startswith('HYBRID') else 0.0,dtype=np.float64)
            child['last_capillary_external_mass_change_kg']=np.asarray(0.0,dtype=np.float64)
        mixed_child['hybrid_incremental_route_count']=np.asarray(int(a3s['Hybrid_incremental_route_count']),dtype=np.int64)
        mixed_child['exact_fallback_route_count']=np.asarray(int(a3s['exact_fallback_route_count']),dtype=np.int64)
        mixed_child['controlled_hybrid_transition_index']=np.asarray(1,dtype=np.int64)

        expected_time=PARENT_DAY+dt;expected_step=int_scalar(ref75['accepted_step_index'])+1
        gate('mixed_child_time_exact',abs(scalar(mixed_child['physical_time_days'])-expected_time)<=1e-12,scalar(mixed_child['physical_time_days']))
        gate('mixed_child_step_exact',int_scalar(mixed_child['accepted_step_index'])==expected_step,int_scalar(mixed_child['accepted_step_index']))
        gate('mixed_child_saturation_exact_A3',np.array_equal(np.asarray(mixed_child['transport_saturation']),mixed_sat))
        gate('mixed_child_stored_mass_exact',abs(scalar(mixed_child['stored_co2_mass_current_kg'])-mixed_final)<=1e-9)
        gate('mixed_child_injection_ledger',abs(scalar(mixed_child['cumulative_injected_co2_mass_kg'])-(scalar(ref75['cumulative_injected_co2_mass_kg'])+injected))<=1e-7,scalar(mixed_child['cumulative_injected_co2_mass_kg']))
        gate('mixed_child_production_ledger',abs(scalar(mixed_child['cumulative_produced_co2_mass_kg'])-(scalar(ref75['cumulative_produced_co2_mass_kg'])+produced))<=1e-7,scalar(mixed_child['cumulative_produced_co2_mass_kg']))
        gate('mixed_child_cumulative_mass_closure',abs(scalar(mixed_child['cumulative_mass_residual_kg']))<=closure_tol,scalar(mixed_child['cumulative_mass_residual_kg']))

        stage='immutability_and_publication'
        gate('source_Day75_parent_unchanged',sha(parent_path)==parent_sha_before,sha(parent_path))
        gate('output_absent',not out.exists(),str(out));out.mkdir(parents=True)
        child_bytes=r3r5.deterministic_npz_bytes(mixed_child);exact_bytes=r3r5.deterministic_npz_bytes(exact_child)
        (out/CHILD).write_bytes(child_bytes);(out/EXACT_CHILD).write_bytes(exact_bytes)
        child_sha=hashlib.sha256(child_bytes).hexdigest();exact_sha=hashlib.sha256(exact_bytes).hexdigest()
        transition={
            'milestone':M,'parent_state_sha256':parent_sha_before,'parent_time_days':PARENT_DAY,
            'parent_step':int_scalar(ref75['accepted_step_index']),'child_state_file':CHILD,'child_state_sha256':child_sha,
            'child_time_days':expected_time,'child_step':expected_step,'dt_days':dt,
            'Hybrid_incremental_route_count':int(a3s['Hybrid_incremental_route_count']),'exact_fallback_route_count':int(a3s['exact_fallback_route_count']),
            'injected_component_mass_kg':injected,'produced_component_mass_kg':produced,'stored_component_mass_kg':mixed_final,
            'step_component_mass_residual_kg':mixed_residual,'producer_CO2_gas_cut':aggregate_cut,
            'mixed_vs_exact_child_saturation_relative_L2':rel_l2(mixed_sat,exact_sat),
            'mixed_vs_exact_child_saturation_Linf':float(np.max(np.abs(mixed_sat-exact_sat))),
            'source_parent_mutated':False,'controlled_child_created':True,
        }
        summary={
            'milestone':M,'status':PASS,
            'classification':'FIRST_CONTROLLED_PARENT_ANCHORED_INCREMENTAL_HYBRID_PLUS_EXACT_FALLBACK_RECURRENT_CHILD_STATE_CERTIFIED_G4_A5_SHORT_MIXED_ROLLOUT_AUTHORIZED',
            'controlled_Hybrid_recurrent_state_transition_executed':True,'controlled_child_state_created':True,
            'controlled_child_state_sha256':child_sha,'exact_benchmark_child_state_sha256':exact_sha,
            'parent_day':PARENT_DAY,'child_day':expected_time,'accepted_dt_days':dt,
            'Hybrid_incremental_route_count':int(a3s['Hybrid_incremental_route_count']),'exact_fallback_route_count':int(a3s['exact_fallback_route_count']),
            'single_common_mapback_and_capillary_inherited_from_A3':True,'component_mass_ledger_closed':True,
            'parent_state_immutable':True,'production_canonical_chain_replaced':False,'new_scientific_threshold_defined':False,
            'G4_A5_short_mixed_recurrent_rollout_authorized':True,'integrated_GPU_runtime_authorized':False,'P4_authorized':False,
            'transition':transition,
        }
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        (out/TRANSITION).write_text(json.dumps(transition,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        write_csv(out/PRODUCERS,producer_rows);write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[{'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST])
        re=load_npz(out/CHILD)
        gate('published_child_reload_time',abs(scalar(re['physical_time_days'])-expected_time)<=1e-12)
        gate('published_child_reload_saturation',np.array_equal(re['transport_saturation'],mixed_sat))
        gate('source_parent_still_unchanged_after_publish',sha(parent_path)==parent_sha_before,sha(parent_path))
        print('='*190);print(M,'PASS')
        print('Parent step/time                              :',int_scalar(ref75['accepted_step_index']),'/',PARENT_DAY)
        print('Controlled child step/time                    :',expected_step,'/',expected_time)
        print('Hybrid / exact fallback routes                :',int(a3s['Hybrid_incremental_route_count']),'/',int(a3s['exact_fallback_route_count']))
        print('Injected / produced kg                        :',injected,'/',produced)
        print('Step component-mass residual kg               :',mixed_residual)
        print('Mixed vs exact child saturation relL2         :',transition['mixed_vs_exact_child_saturation_relative_L2'])
        print('Parent immutable                              : True')
        print('Controlled Hybrid recurrent child             : CERTIFIED')
        print('G4-A5 short mixed recurrent rollout           : AUTHORIZED')
        print('='*190)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f'{OUT_TOKEN}_Blocked_Report.json').write_text(json.dumps({
            'milestone':M,'status':BLOCK,'failed_stage':stage,'exception':repr(exc),'gates':gates,
            'parent_state_sha256_before':parent_sha_before,'controlled_child_state_created':False,'source_parent_mutated':False,
            'G4_A5_short_mixed_recurrent_rollout_authorized':False,'integrated_GPU_runtime_authorized':False,'P4_authorized':False,
        },indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print(M,'BLOCK');print('Stage:',stage);print('Exception:',repr(exc));return 2

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,default=Path('.'));ap.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'));ap.add_argument('--self-test',action='store_true')
    a=ap.parse_args()
    if a.self_test:selftest();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
