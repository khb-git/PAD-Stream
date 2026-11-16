#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,subprocess
from pathlib import Path
M="POSTV16-AV4-PIVOT-GPU-HYB-G3-R2-R4"
PASS="POSTV16AV4PIVOTGPUHYBG3R2R4_BRANCH_PROJECTION_SOLVER_CONDITIONING_REPAIR_DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBG3R2R4_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot";PARENT="0445ebb71876ce99d33b20528084ad0455a6fac4"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A";BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
R3_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R3_Branch_Projection_Frontier_Conditioning_Diagnostic"
R3_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R3_Summary.json";R3_DIAG="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R3_Branch_Frontier_Diagnostic.json"
R3_STATUS="POSTV16AV4PIVOTGPUHYBG3R2R3_BRANCH_PROJECTION_FRONTIER_CONDITIONING_DIAGNOSTIC_PASS_NO_PHYSICS_EXECUTION";R3_CLASS="ALL_BRANCHES_FEASIBLE_AT_OR_WITHIN_FROZEN_STAGE1_ACCEPTANCE_TOLERANCE"
EXPECTED={
"REFRESHED_0D":{"classification":"EXACT_EQUALITY_NUMERICALLY_ILL_CONDITIONED_BOUNDED_FRONTIER_FEASIBLE","stage1_mass_kg":53257914.56834785,"tol_kg":0.005325791456834785,"exact_success":False,"mode":"BOUNDED_FRONTIER_WITHIN_FROZEN_STAGE1_TOL","presolve":True,"delta":0.005325791456834785,"loss":0.005322165787220001},
"STALE_5D":{"classification":"EXACT_STAGE2_NO_PRESOLVE_FEASIBLE","stage1_mass_kg":53123910.57844832,"tol_kg":0.005312391057844832,"exact_success":True,"mode":"EXACT_FRONTIER_PRESOLVE_OFF","presolve":False,"delta":None},
"STALE_15D":{"classification":"EXACT_STAGE2_NO_PRESOLVE_FEASIBLE","stage1_mass_kg":53106123.56674311,"tol_kg":0.005310612356674312,"exact_success":True,"mode":"EXACT_FRONTIER_PRESOLVE_OFF","presolve":False,"delta":None}}
OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R4";OUT_REL=BASE/(OUT_TOKEN+"_Branch_Projection_SolverConditioning_Repair_Design_Freeze");BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json";PROTOCOL=f"{OUT_TOKEN}_Projection_Repair_Protocol.json";DECISION=f"{OUT_TOKEN}_Decision_Contract.json";BRANCH_CSV=f"{OUT_TOKEN}_Branch_Solver_Policy.csv";GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv";MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"
class GateError(RuntimeError):pass
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def gt(root,*a):return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
def js(p):return json.loads(Path(p).read_text())
def csvw(p,rows):
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields:fields.append(k)
 with open(p,'w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
def close(a,b):return abs(float(a)-float(b))<=max(1e-12,1e-12*max(abs(float(b)),1.0))
def selftest():
 assert EXPECTED['REFRESHED_0D']['delta']==EXPECTED['REFRESHED_0D']['tol_kg'];assert EXPECTED['STALE_5D']['delta'] is None;print('POSTV16 GPU-HYB-G3-R2-R4 structural self-test: PASS')
def main(root,drive):
 root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;block=drive/BLOCK_REL;gates=[];stage='preflight'
 def gate(n,c,d=None):
  ok=bool(c);gates.append({'stage':stage,'gate':n,'pass':ok,'detail':'' if d is None else repr(d)});print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"))
  if not ok:raise GateError(n)
 try:
  stage='repository';gate('branch',gt(root,'branch','--show-current')==BRANCH);gate('parent',gt(root,'rev-parse','HEAD^')==PARENT,gt(root,'rev-parse','HEAD^'));gate('clean',gt(root,'status','--porcelain')=='')
  stage='R3_authority';s=js(drive/R3_REL/R3_SUM);d=js(drive/R3_REL/R3_DIAG);gate('R3_status',s.get('status')==R3_STATUS,s.get('status'));gate('R3_class',s.get('classification')==R3_CLASS,s.get('classification'));gate('R3_all_bounded',s.get('all_branches_bounded_frontier_feasible') is True);gate('R3_within_tol',s.get('all_branches_within_frozen_stage1_acceptance_tolerance') is True);gate('R3_no_transport',s.get('transport_executed') is False);gate('R3_no_support',s.get('support_growth_executed') is False);gate('R3_no_mutation',s.get('state_mutation_executed') is False)
  rows=[]
  for name,e in EXPECTED.items():
   v=d[name];gate(name+'_class',v['classification']==e['classification'],v['classification']);gate(name+'_mass',close(v['stage1_mass_kg'],e['stage1_mass_kg']),v['stage1_mass_kg']);gate(name+'_tol',close(v['stage1_acceptance_tolerance_kg'],e['tol_kg']),v['stage1_acceptance_tolerance_kg']);gate(name+'_witness',v['stage1_witness_feasible_within_frozen_tolerance'] is True);gate(name+'_exact',bool(v['exact_stage2_without_presolve']['success']) is e['exact_success'])
   if name=='REFRESHED_0D':
    f=v['first_feasible_bounded_probe'];gate('REFRESHED_probe',f is not None);gate('REFRESHED_delta',close(f['mass_floor_delta_kg'],e['delta']),f['mass_floor_delta_kg']);gate('REFRESHED_loss',float(f['mass_loss_vs_stage1_kg'])<=e['delta']+1e-9,f['mass_loss_vs_stage1_kg'])
   rows.append({'branch':name,'repair_mode':e['mode'],'stage1_mass_kg':e['stage1_mass_kg'],'frozen_stage1_acceptance_tolerance_kg':e['tol_kg'],'stage2_method':'highs','stage2_presolve':e['presolve'],'exact_frontier_equality_required':name!='REFRESHED_0D','bounded_mass_floor_delta_kg':e['delta'],'support_growth_authorized':False,'cartesian_parent_mass_change_authorized':False})
  protocol={'milestone':M,'classification':'BRANCH_SPECIFIC_STAGE2_SOLVER_CONDITIONING_REPAIR_FROZEN_NO_SUPPORT_GROWTH','branch_policy':{k:{'repair_mode':v['mode'],'stage1_mass_kg':v['stage1_mass_kg'],'stage1_tolerance_kg':v['tol_kg'],'stage2_method':'highs','stage2_presolve':v['presolve'],'mass_floor_delta_kg':v['delta']} for k,v in EXPECTED.items()},'support_growth_authorized':False,'frontier_band_above_frozen_stage1_tolerance_authorized':False,'mass_discard_authorized':False,'global_mass_rescaling_authorized':False,'cartesian_parent_mass_mutation_authorized':False,'residual_sidecar_absorbs_representation_difference':True,'transport_execution_authorized_in_this_milestone':False,'G3_R2_R5_late_flow_network_shadow_execution_authorized':True,'production_pressure_refresh_cadence_selected':False,'scientific_cadence_tolerance_defined':False,'P4_authorized':False}
  decision={'milestone':M,'status':PASS,'G3_R2_R5_authorized':True,'G3_R2_R5_name':'Late-Native Day405 Flow-Network Staleness Shadow — Branch-Specific Projection Repair Execution','must_bind_R3_frontier_diagnostic':True,'must_use_branch_specific_solver_policy':True,'must_preserve_total_Day405_cartesian_component_mass':True,'must_preserve_native_heterogeneous_PV_and_frozen_Day365_thermodynamic_pressure':True,'support_growth_authorized':False,'cadence_selection_authorized_in_R5':False,'P4_authorized':False}
  summary={'milestone':M,'status':PASS,'classification':protocol['classification'],'REFRESHED_0D_policy':protocol['branch_policy']['REFRESHED_0D'],'STALE_5D_policy':protocol['branch_policy']['STALE_5D'],'STALE_15D_policy':protocol['branch_policy']['STALE_15D'],'maximum_authorized_representation_band_kg':EXPECTED['REFRESHED_0D']['tol_kg'],'maximum_authorized_representation_band_fraction_of_refreshed_stage1':EXPECTED['REFRESHED_0D']['tol_kg']/EXPECTED['REFRESHED_0D']['stage1_mass_kg'],'support_growth_required':False,'support_growth_authorized':False,'scientific_cadence_tolerance_defined':False,'production_pressure_refresh_cadence_selected':False,'G3_R2_R5_late_flow_network_shadow_execution_authorized':True,'P4_authorized':False}
  stage='publication';gate('output_absent',not out.exists(),str(out));out.mkdir(parents=True);(out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');(out/PROTOCOL).write_text(json.dumps(protocol,indent=2,sort_keys=True)+'\n');(out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True)+'\n');csvw(out/BRANCH_CSV,rows);csvw(out/GATES,gates);csvw(out/MANIFEST,[{'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST]);print(json.dumps(summary,indent=2));return 0
 except Exception as exc:
  block.mkdir(parents=True,exist_ok=True);(block/f'{OUT_TOKEN}_Blocked_Report.json').write_text(json.dumps({'milestone':M,'status':BLOCK,'failed_stage':stage,'exception':repr(exc),'gates':gates,'G3_R2_R5_late_flow_network_shadow_execution_authorized':False,'production_pressure_refresh_cadence_selected':False,'P4_authorized':False},indent=2)+'\n');print('BLOCK',stage,repr(exc));return 2
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,default=Path('.'));ap.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'));ap.add_argument('--self-test',action='store_true');a=ap.parse_args()
 if a.self_test:selftest();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
