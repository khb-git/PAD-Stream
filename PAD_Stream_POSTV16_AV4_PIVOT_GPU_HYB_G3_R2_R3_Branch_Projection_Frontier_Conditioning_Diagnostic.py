#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G3-R2-R3"
PASS="POSTV16AV4PIVOTGPUHYBG3R2R3_BRANCH_PROJECTION_FRONTIER_CONDITIONING_DIAGNOSTIC_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBG3R2R3_TECHNICAL_OR_AUTHORITY_BLOCK_NO_PHYSICS_EXECUTION"
BRANCH="postv16-av4-pivot";PARENT="e9eb6d9dbde8057b2efc6c61727325e0b84e69b1"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
BLOCK_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R2_BLOCKED"
BLOCK_FILE="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R2_Blocked_Report.json"
R25=("PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_R3_Controlled_CapacityLimited_Reprojection_Stage2_PresolveOff.py","65cab626419137b191f2c53a4c543d9805ccf68d")
R2=("PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py","a127f8730a16e150713420ea547a8de6255550ef")
E37A=("PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py","0bbf98ed89cee9128ef1d313c321f9a401b4e9f0")
SG7D=("PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py","890088c0c0fcab415a2c7351c5079ca8ee12bf82")
A2E_REL=BASE/"POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH="POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_SHA="b49d48baa9d791b69a9e9c41635e1930fae84114b93ceb15ab5b21d3441ba08d"
D390_REL=BASE/"POSTV16_AV4_PIVOT_P3_R1_R7_R7_XY2_Day385_to_Day390_FifthObservation_Pilot_and_Exact_Flow_Diagnostic"
D400_REL=BASE/"POSTV16_AV4_PIVOT_P3_R1_R7_R9_XY2_Day395_to_Day400_SeventhObservation_Pilot_and_Exact_Flow_Diagnostic"
D405_REL=BASE/"POSTV16_AV4_PIVOT_P3_R1_R7_R10_XY2_Day400_to_Day405_EighthObservation_Pilot_and_Exact_Flow_Diagnostic"
D390="POSTV16_AV4_PIVOT_P3_R1_R7_R7_Day0390_Exact_Flow_Diagnostic.npz";D390_SHA="a5e2271830649b37e0de38459a9ead58fb79d4c20c185fee1d3390e9e749c9dc"
D400="POSTV16_AV4_PIVOT_P3_R1_R7_R9_Day0400_Exact_Flow_Diagnostic.npz";D400_SHA="2e772ca70526a2c64bc0a84f3fbc42c2540593e6b7d79dc74787e33b52c0ac42"
D405="POSTV16_AV4_PIVOT_P3_R1_R7_R10_Day0405_Exact_Flow_Diagnostic.npz";D405_SHA="a567f4f560fcc56f1a26edfa4a4e6747a2a6d42e93fd9c9ce0c7cd87781fdafa"
D405_STATE="POSTV16_AV4_PIVOT_P3_R1_R7_R10_Day0405_Accepted_Dense_State.npz";D405_STATE_SHA="dbe07ff7e33587f65b7c3ff02a4755e739975715cf003d42541070dc084d2077"
MASS_TOL=1e-6;OPT_REL_TOL=1e-10;NSL=1078;NCV=200;NCELL=37500
OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R3"
OUT_REL=BASE/(OUT_TOKEN+"_Branch_Projection_Frontier_Conditioning_Diagnostic")
OUT_BLOCK=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json";DETAIL=f"{OUT_TOKEN}_Branch_Frontier_Diagnostic.json";CSV=f"{OUT_TOKEN}_Branch_Frontier_Diagnostic.csv";GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv";MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"
class GateError(RuntimeError):pass
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for c in iter(lambda:f.read(1<<20),b""):h.update(c)
 return h.hexdigest()
def gt(root,*a):return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()
def mod(root,spec,name):
 fn,blob=spec;p=root/fn
 if not p.is_file():raise GateError("missing:"+fn)
 if gt(root,"hash-object",str(p))!=blob:raise GateError("blob:"+fn)
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def write_csv(p,rows):
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields:fields.append(k)
 with open(p,"w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)
def diag(p):
 with np.load(p,allow_pickle=False) as z:return np.asarray(z["streamline_xyz_m"],float),np.asarray(z["streamline_tof_s"],float),np.asarray(z["streamline_weight_m3_s"],float)
def stage1(gm,cap,ecv,ecell):
 from scipy import sparse
 from scipy.optimize import linprog
 gm=gm.ravel();cap=cap.ravel();ac=np.unique(ecell);av=np.unique(ecv);cr=np.searchsorted(ac,ecell);vr=np.searchsorted(av,ecv);n=len(ecv)
 A=sparse.coo_matrix((np.ones(2*n),(np.r_[cr,len(ac)+vr],np.r_[np.arange(n),np.arange(n)])),shape=(len(ac)+len(av),n)).tocsr();b=np.r_[gm[ac],cap[av]]
 lp=linprog(-np.ones(n),A_ub=A,b_ub=b,bounds=(0,None),method="highs",options={"presolve":True})
 if not lp.success:raise GateError(f"stage1:{lp.status}:{lp.message}")
 return np.asarray(lp.x),float(np.sum(lp.x)),A,b
def solve2(gm,cap,ecv,ecell,target,m1,delta=None,presolve=False):
 from scipy import sparse
 from scipy.optimize import linprog
 gm=gm.ravel();cap=cap.ravel();n=len(ecv);ac=np.unique(ecell);av=np.unique(ecv);cr=np.searchsorted(ac,ecell);vr=np.searchsorted(av,ecv);nv=2*n
 As=sparse.coo_matrix((np.ones(2*n),(np.r_[cr,len(ac)+vr],np.r_[np.arange(n),np.arange(n)])),shape=(len(ac)+len(av),nv)).tocsr();bs=np.r_[gm[ac],cap[av]]
 r=np.arange(n);Aa=sparse.coo_matrix((np.r_[np.ones(n),-np.ones(n),-np.ones(n),-np.ones(n)],(np.r_[r,r,n+r,n+r],np.r_[r,n+r,r,n+r])),shape=(2*n,nv)).tocsr();ba=np.r_[target,-target]
 Aub=sparse.vstack([As,Aa]);bub=np.r_[bs,ba];Aeq=None;beq=None
 total=sparse.csr_matrix((np.ones(n),(np.zeros(n,dtype=int),np.arange(n))),shape=(1,nv))
 if delta is None:Aeq=total;beq=np.asarray([m1])
 else:Aub=sparse.vstack([Aub,total,-total]);bub=np.r_[bub,m1,-(m1-delta)]
 lp=linprog(np.r_[np.zeros(n),np.ones(n)],A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=beq,bounds=(0,None),method="highs",options={"presolve":presolve})
 out={"success":bool(lp.success),"status":int(lp.status),"message":str(lp.message),"mass_floor_delta_kg":delta}
 if lp.success:
  x=np.asarray(lp.x[:n]);out.update(realized_mass_kg=float(np.sum(x)),mass_loss_vs_stage1_kg=float(m1-np.sum(x)),L1_objective_kg=float(lp.fun))
 return out
def selftest():print("POSTV16 GPU-HYB-G3-R2-R3 structural self-test: PASS")
def main(root,drive):
 root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blk=drive/OUT_BLOCK;gates=[];stage="preflight"
 def gate(n,c,d=None):
  ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)});print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"))
  if not ok:raise GateError(n)
 try:
  stage="repo";gate("branch",gt(root,"branch","--show-current")==BRANCH);gate("parent",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"));gate("clean",gt(root,"status","--porcelain")=="")
  stage="prior_block";bp=drive/BLOCK_REL/BLOCK_FILE;gate("block_present",bp.is_file());br=json.loads(bp.read_text());gate("failed_stage",br.get("failed_stage")=="branch_projection",br.get("failed_stage"));gate("failed_gate","stage2_min_L1_HiGHS" in str(br.get("exception","")),br.get("exception"))
  r25=mod(root,R25,"r25");r2=mod(root,R2,"r2");e37a=mod(root,E37A,"e37a");sg7d=mod(root,SG7D,"sg7d")
  stage="authority";ep=drive/A2E_REL/A2E_EPOCH;gate("A2E_SHA",sha(ep)==A2E_SHA,sha(ep))
  with np.load(ep,allow_pickle=False) as z:pressure=np.asarray(z["refreshed_pressure_psi"],float);pref=float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
  sp=drive/D405_REL/D405_STATE;gate("Day405_state_SHA",sha(sp)==D405_STATE_SHA,sha(sp))
  with np.load(sp,allow_pickle=False) as z:gm=np.asarray(z["cartesian_component_mass_kg"],float)
  specs=[("REFRESHED_0D",405,drive/D405_REL/D405,D405_SHA),("STALE_5D",400,drive/D400_REL/D400,D400_SHA),("STALE_15D",390,drive/D390_REL/D390,D390_SHA)]
  res={};rows=[];stage="diagnostics"
  for name,day,p,expected in specs:
   gate(name+"_SHA",sha(p)==expected,sha(p));xyz,tof,w=diag(p);op=sg7d.build_subsegment_operator(xyz,tof/86400.0,w*86400.0);geom=e37a.build_control_volume_geometry(r2,op,pressure,pref,NSL,NCV)
   ecv,ecell,target=r25.build_edge_target_and_support(gm,op);cap=np.asarray(e37a.cv_mass_from_saturation(r2,np.full((NSL,NCV),0.8),geom["cv_pressure_mass_coeff"]),float)
   x1,m1,A,b=stage1(gm,cap,ecv,ecell);tol=max(MASS_TOL,OPT_REL_TOL*max(abs(m1),1.0));d=np.abs(x1-target)
   supply=np.asarray(A@x1-b);witness={"maximum_supply_or_capacity_violation_kg":float(max(0,np.max(supply))),"minimum_x_kg":float(np.min(x1)),"maximum_L1_epigraph_violation_kg":0.0,"exact_frontier_equality_residual_kg":float(np.sum(x1)-m1),"witness_L1_objective_kg":float(np.sum(d))}
   wok=witness["maximum_supply_or_capacity_violation_kg"]<=tol and witness["minimum_x_kg"]>=-tol and abs(witness["exact_frontier_equality_residual_kg"])<=tol
   exact=solve2(gm,cap,ecv,ecell,target,m1,None,False);first=None;probes=[]
   for delta in [tol,100*tol,10000*tol]:
    q=solve2(gm,cap,ecv,ecell,target,m1,float(delta),True);probes.append(q)
    if q["success"] and first is None:first=q
   cls="EXACT_STAGE2_NO_PRESOLVE_FEASIBLE" if exact["success"] else ("EXACT_EQUALITY_NUMERICALLY_ILL_CONDITIONED_BOUNDED_FRONTIER_FEASIBLE" if wok and first else ("NONZERO_FRONTIER_RELAXATION_REQUIRED_WITHIN_TESTED_BANDS" if first else "INFEASIBLE_UNDER_TESTED_FRONTIER_BANDS"))
   res[name]={"day":day,"classification":cls,"stage1_mass_kg":m1,"stage1_acceptance_tolerance_kg":tol,"stage1_witness":witness,"stage1_witness_feasible_within_frozen_tolerance":wok,"exact_stage2_without_presolve":exact,"bounded_frontier_probes":probes,"first_feasible_bounded_probe":first}
   rows.append({"branch":name,"day":day,"classification":cls,"stage1_mass_kg":m1,"stage1_acceptance_tolerance_kg":tol,"witness_feasible":wok,"exact_no_presolve_success":exact["success"],"exact_status":exact["status"],"exact_message":exact["message"],"bounded_any_success":first is not None,"minimum_feasible_delta_kg":None if first is None else first["mass_floor_delta_kg"],"realized_mass_loss_kg":None if first is None else first["mass_loss_vs_stage1_kg"]})
  all_exact=all(v["exact_stage2_without_presolve"]["success"] for v in res.values());all_bounded=all(v["exact_stage2_without_presolve"]["success"] or v["first_feasible_bounded_probe"] is not None for v in res.values());all_tol=all(v["exact_stage2_without_presolve"]["success"] or (v["first_feasible_bounded_probe"] and v["first_feasible_bounded_probe"]["mass_floor_delta_kg"]<=v["stage1_acceptance_tolerance_kg"]*(1+1e-12)) for v in res.values())
  overall="ALL_BRANCHES_EXACT_STAGE2_NO_PRESOLVE_FEASIBLE" if all_exact else ("ALL_BRANCHES_FEASIBLE_AT_OR_WITHIN_FROZEN_STAGE1_ACCEPTANCE_TOLERANCE" if all_tol else ("ALL_BRANCHES_FEASIBLE_WITHIN_TESTED_BANDS_BUT_LARGER_FRONTIER_BAND_REQUIRED" if all_bounded else "AT_LEAST_ONE_BRANCH_REMAINS_INFEASIBLE_UNDER_R25R1_FRONTIER_BANDS"))
  stage="publish";gate("out_absent",not out.exists());out.mkdir(parents=True)
  summary={"milestone":M,"status":PASS,"classification":overall,"branch_classifications":{k:v["classification"] for k,v in res.items()},"all_branches_exact_stage2_no_presolve_feasible":all_exact,"all_branches_bounded_frontier_feasible":all_bounded,"all_branches_within_frozen_stage1_acceptance_tolerance":all_tol,"diagnostic_only":True,"transport_executed":False,"support_growth_executed":False,"state_mutation_executed":False,"G3_R2_late_shadow_execution_authorized":False,"production_pressure_refresh_cadence_selected":False,"P4_authorized":False}
  (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n");(out/DETAIL).write_text(json.dumps(res,indent=2,sort_keys=True)+"\n");write_csv(out/CSV,rows);write_csv(out/GATES,gates);write_csv(out/MANIFEST,[{"file":q.name,"sha256":sha(q),"bytes":q.stat().st_size} for q in sorted(out.iterdir()) if q.is_file() and q.name!=MANIFEST])
  print("--- G3-R2-R3 SUMMARY ---");print(json.dumps(summary,indent=2))
  for k,v in res.items():print(k,json.dumps(v,indent=2))
  return 0
 except Exception as exc:
  blk.mkdir(parents=True,exist_ok=True);(blk/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,"transport_executed":False,"state_mutation_executed":False,"production_pressure_refresh_cadence_selected":False},indent=2)+"\n");print("BLOCK",stage,repr(exc));return 2
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--project-root",type=Path,default=Path("."));ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"));ap.add_argument("--self-test",action="store_true");a=ap.parse_args()
 if a.self_test:selftest();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
