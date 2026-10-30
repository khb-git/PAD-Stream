#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,io,json,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-P2-R6-R15"
NAME="Day375 Residual Bottleneck-Specific Projection/Support Reconciliation Design Freeze"
PASS="AV4PIVOTP2R6R15_DAY375_RESIDUAL_BOTTLENECK_SPECIFIC_PROJECTION_SUPPORT_RECONCILIATION_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
BLOCK="AV4PIVOTP2R6R15_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"; PARENT="700438ea7847fbe58a6df83c36ab03787942ac25"
R14RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R14_Day375_Residual_FullAdmissibleDomain_Capacity_Ownership_Bottleneck_Diagnostic_Freeze.py"
R14BLOB="15f2174da644b78cf654ae84b81a2bd7416fa19c"
R2="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2BLOB="a127f8730a16e150713420ea547a8de6255550ef"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"; BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
R14=BASE/"POSTV16_AV4_PIVOT_P2_R6_R14_Day375_Residual_FullAdmissibleDomain_Capacity_Ownership_Bottleneck_Diagnostic_Freeze"
R12=BASE/"POSTV16_AV4_PIVOT_P2_R6_R12_Day375_Residual_AdjacentLayer_FaceConnected_Lateral_Topology_Design_Freeze"
R11=BASE/"POSTV16_AV4_PIVOT_P2_R6_R11_Day375_Residual_BeyondSameLayer_Topology_Design_Freeze"
R10=BASE/"POSTV16_AV4_PIVOT_P2_R6_R10_Day375_Residual_ThirdStage_SupportExtension_Topology_Design_Freeze"
R9=BASE/"POSTV16_AV4_PIVOT_P2_R6_R9_Day375_Residual_SecondStage_SupportExtension_Topology_Design_Freeze"
R8=BASE/"POSTV16_AV4_PIVOT_P2_R6_R8_R1_Day375_Residual_FrozenDomain_Infeasibility_Localization_and_Minimal_SupportExtension_Design_Freeze"
R7=BASE/"POSTV16_AV4_PIVOT_P2_R6_R7_Day375_Residual_External_Component_Exact_Projection_Semantics_Freeze"
R6=BASE/"POSTV16_AV4_PIVOT_P2_R6_R6_Day375_Residual_External_Component_Projection_Authority_and_Global_State_Closure_Audit"
R5=BASE/"POSTV16_AV4_PIVOT_P2_R6_R5_Controlled_Day375_TerminalSink_FixedExternal_Local_Projection"
D370=BASE/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
A2=BASE/"POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
OUT=BASE/"POSTV16_AV4_PIVOT_P2_R6_R15_Day375_Residual_BottleneckSpecific_Projection_Support_Reconciliation_Design_Freeze"
BLK=BASE/"POSTV16_AV4_PIVOT_P2_R6_R15_BLOCKED"

UNRES=[0,3,31,65,79]
CL={0:"EXISTING_PAIR_SIGN_PRESERVATION_BOTTLENECK",3:"EXISTING_PAIR_SIGN_PRESERVATION_BOTTLENECK",31:"COMPONENT_POOL_OWNERSHIP_SEMANTICS_BOTTLENECK",65:"LOCAL_SUPPORT_REACH_TOPOLOGY_BOTTLENECK",79:"LOCAL_SUPPORT_REACH_TOPOLOGY_BOTTLENECK"}
GRID=(15,50,50); NCELL=37500; NCV=200; NCVT=1078*200
BG=.20;MAXSG=.60;CTOL=1e-7;CVTOL=1e-7;LTOL=1e-6;STOL=1e-10;RTOL=1e-8
R5SHA="1553445022f7267d7802f8833d5440d7521433a4cd8b7c06652cffeb6d693e57"

class GateError(RuntimeError): pass
def gt(r,*a):return subprocess.check_output(["git","-C",str(r),*a],text=True).strip()
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def js(p):return json.loads(Path(p).read_text())
def csvr(p):
 with open(p,newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def csvb(rows):
 if not rows:return b""
 fs=[]
 for r in rows:
  for k in r:
   if k not in fs:fs.append(k)
 s=io.StringIO(newline="");w=csv.DictWriter(s,fieldnames=fs,lineterminator="\n");w.writeheader();w.writerows(rows);return s.getvalue().encode()
def jb(x):return (json.dumps(x,indent=2,sort_keys=True)+"\n").encode()
def man(d,n):
 for r in csvr(d/n):
  p=d/r["file"]
  if not p.is_file() or sha(p)!=r["sha256"] or p.stat().st_size!=int(r["bytes"]):raise GateError("manifest:"+p.name)
def mod(p,n):
 sp=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(sp);sys.modules[n]=m;sp.loader.exec_module(m);return m
def h2(cells,s0):
 o=set()
 for c in np.asarray(cells,dtype=np.int64).reshape(-1):
  k=int(c)//2500;rem=int(c)%2500;j,i=rem//50,rem%50
  for dj in range(-2,3):
   for di in range(-2,3):
    if 1<=abs(di)+abs(dj)<=2 and 0<=j+dj<50 and 0<=i+di<50:
     x=k*2500+(j+dj)*50+i+di
     if x not in s0:o.add(int(x))
 return o
def emap(rows):
 d={}
 for r in rows:
  if r.get("flat_cell","")!="":d.setdefault((int(r["execution_group_id"]),int(r["component_id"])),set()).add(int(r["flat_cell"]))
 return d
def selftest():
 assert UNRES==[0,3,31,65,79] and NCELL==37500
 print("POSTV16 AV4 PIVOT P2-R6-R15 structural self-test: PASS")

def main(root,drive):
 root=Path(root).resolve();drive=Path(drive).resolve();out=drive/OUT;blk=drive/BLK;stage="preflight";gates=[]
 def gate(n,x,d=None):
  ok=bool(x);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
  print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"))
  if not ok:raise GateError(n)
 try:
  if (out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R15_Summary.json").is_file():return 0
  gate("no_preexisting_BLOCK",not (blk/"POSTV16_AV4_PIVOT_P2_R6_R15_Blocked_Report.json").exists())
  stage="repo";gate("branch",gt(root,"branch","--show-current")==BRANCH);gate("parent",gt(root,"rev-parse","HEAD^")==PARENT);gate("clean",gt(root,"status","--porcelain")=="")
  gate("R14_blob",gt(root,"hash-object",str(root/R14RUN))==R14BLOB);gate("R2_blob",gt(root,"hash-object",str(root/R2))==R2BLOB)

  stage="R14";man(drive/R14,"POSTV16_AV4_PIVOT_P2_R6_R14_Artifact_Manifest.csv")
  s14=js(drive/R14/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R14_Summary.json");d14=js(drive/R14/"POSTV16_AV4_PIVOT_P2_R6_R14_Decision_Contract.json")
  cls=csvr(drive/R14/"POSTV16_AV4_PIVOT_P2_R6_R14_Bottleneck_Classification.csv");diag=csvr(drive/R14/"POSTV16_AV4_PIVOT_P2_R6_R14_Projection_Formulation_Diagnostic_Matrix.csv")
  got={int(r["execution_group_id"]):r["bottleneck_classification"] for r in cls}
  gate("classification_map",got==CL,got);gate("R15_authorized",d14.get("P2_R6_R15_authorized") is True)
  fe={(int(r["execution_group_id"]),r["variant"]):str(r["exact_feasible"]).lower()=="true" for r in diag}
  gate("g31_V0",fe[(31,"V0_CURRENT_SUPPORT_SHARED_POOL")])
  for gid in (65,79):gate(f"g{gid}_V1",not fe[(gid,"V0_CURRENT_SUPPORT_SHARED_POOL")] and fe[(gid,"V1_STRICT_FULL_UNOWNED_DOMAIN")])
  for gid in (0,3):gate(f"g{gid}_V4",all(not fe[(gid,v)] for v in ["V0_CURRENT_SUPPORT_SHARED_POOL","V1_STRICT_FULL_UNOWNED_DOMAIN","V2_OWNERSHIP_RELAXED_FULL_DOMAIN","V3_ALL_GROUP_CVS_H2_ELIGIBLE"]) and fe[(gid,"V4_SIGN_RELAXED_EXISTING_PAIRS")])

  stage="support"; 
  for rel,mn in [(R12,"POSTV16_AV4_PIVOT_P2_R6_R12_Artifact_Manifest.csv"),(R11,"POSTV16_AV4_PIVOT_P2_R6_R11_Artifact_Manifest.csv"),(R10,"POSTV16_AV4_PIVOT_P2_R6_R10_Artifact_Manifest.csv"),(R9,"POSTV16_AV4_PIVOT_P2_R6_R9_Artifact_Manifest.csv"),(R8,"POSTV16_AV4_PIVOT_P2_R6_R8_R1_Artifact_Manifest.csv")]:man(drive/rel,mn)
  xs=[emap(csvr(drive/R8/"POSTV16_AV4_PIVOT_P2_R6_R8_R1_Frozen_Compact_Support_Extension.csv")),emap(csvr(drive/R9/"POSTV16_AV4_PIVOT_P2_R6_R9_Frozen_SecondStage_Support_Extension.csv")),emap(csvr(drive/R10/"POSTV16_AV4_PIVOT_P2_R6_R10_Frozen_ThirdStage_Support_Extension.csv")),emap(csvr(drive/R11/"POSTV16_AV4_PIVOT_P2_R6_R11_Frozen_Vertical_Support_Extension.csv")),emap(csvr(drive/R12/"POSTV16_AV4_PIVOT_P2_R6_R12_Frozen_AdjacentLayerLateral_Support_Extension.csv"))]

  stage="reconstruct"
  gr=csvr(drive/R7/"POSTV16_AV4_PIVOT_P2_R6_R7_Prospective_Execution_Groups.csv");tr=csvr(drive/R7/"POSTV16_AV4_PIVOT_P2_R6_R7_Frozen_Target_CVs.csv");cvr=csvr(drive/R6/"POSTV16_AV4_PIVOT_P2_R6_R6_Residual_CV_Component_Ownership.csv")
  gm={int(r["execution_group_id"]):r for r in gr};c2g={}
  for gid,r in gm.items():
   for c in [int(x) for x in r["R6R6_component_ids"].split(";") if x]:c2g[c]=gid
  cv2c={int(r["cv_id"]):int(r["component_id"]) for r in cvr};cc={c:np.asarray(sorted(v for v,o in cv2c.items() if o==c),dtype=np.int64) for c in range(158)};tgt={c:set(int(r["cv_id"]) for r in tr if int(r["component_id"])==c) for c in range(158)}
  stp=drive/R5/"POSTV16_AV4_PIVOT_P2_R6_R5_Provisional_LocalRepaired_Day375_State.npz";gate("R5sha",sha(stp)==R5SHA)
  with np.load(stp,allow_pickle=False) as z:
   pcv=np.asarray(z["existing_pair_cv"],dtype=np.int64).reshape(-1);pcel=np.asarray(z["existing_pair_cell"],dtype=np.int64).reshape(-1);pval=np.asarray(z["locally_repaired_existing_pair_contribution_kg"],float).reshape(-1);prov=np.asarray(z["provisional_grid_component_mass_kg"],float).reshape(-1);r5cv=np.asarray(z["local_component_cv"],dtype=np.int64).reshape(-1);hcv=np.asarray(z["local_halo_cv"],dtype=np.int64).reshape(-1);hcel=np.asarray(z["local_halo_cell"],dtype=np.int64).reshape(-1);hm=np.asarray(z["local_halo_contribution_kg"],float).reshape(-1);pstate=np.asarray(z["parent_pressure_psi"],float)
  with np.load(drive/D370/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz",allow_pickle=False) as z:
   old=np.asarray(z["grid_component_mass_kg"],float).reshape(-1);fhcv=np.asarray(z["halo_cv"],dtype=np.int64).reshape(-1);fhcel=np.asarray(z["halo_cell"],dtype=np.int64).reshape(-1)
  ky=np.unique(fhcv*NCELL+fhcel);fhcv=ky//NCELL;fhcel=ky%NCELL;fdom=set(np.unique(fhcel).tolist())
  with np.load(drive/A2/"POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz",allow_pickle=False) as z:
   pr=np.asarray(z["refreshed_pressure_psi"],float);pv=np.asarray(z["pore_volume_m3"],float);pref=float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
  gate("pressure",np.max(np.abs(pr-pstate))<=1e-12)
  r2=mod(root/R2,"r15r2");rho=np.asarray(r2.gas_density_from_state(np.full(GRID,BG+MAXSG),pr,pref),float);cap=(pv*rho*MAXSG).reshape(-1)
  cur=np.bincount(pcv,weights=pval,minlength=NCVT)+np.bincount(hcv,weights=hm,minlength=NCVT)
  recon=old+np.bincount(pcel,weights=pval,minlength=NCELL)+np.bincount(hcel,weights=hm,minlength=NCELL);gate("recon",np.max(np.abs(recon-prov))<=CTOL);gate("ledger",abs(prov.sum()-(old.sum()+cur.sum()))<=LTOL)
  s0=set(np.unique(pcel).tolist());r5fixed=set(np.unique(np.r_[pcel[np.isin(pcv,r5cv)],hcel]).tolist())
  frontier={};base={}
  for c in range(158):
   cvs=cc[c];s0c=np.unique(pcel[np.isin(pcv,cvs)]);frontier[c]=set(x for x in h2(s0c,s0) if x in fdom);m=np.isin(fhcv,cvs);base[c]=sorted(set((int(a),int(b)) for a,b in zip(fhcv[m],fhcel[m])))
  comp_pool={};owners={}
  for c in range(158):
   gid=c2g[c];p=set(frontier[c]);p.update(h for _,h in base[c])
   for src in xs:p.update(src.get((gid,c),set()))
   comp_pool[c]=p
   for x in p:owners.setdefault(int(x),set()).add(gid)

  plans=[
   {"execution_group_id":31,"R6R14_bottleneck":CL[31],"group_shared_pool":True,"support_domain":"CURRENT_FROZEN_GROUP_SUPPORT_ONLY","intergroup_ownership_relaxed":False,"H2_eligibility":"R6R7_TARGET_CVS_ONLY","existing_pair_sign_relaxed":False},
   {"execution_group_id":65,"R6R14_bottleneck":CL[65],"group_shared_pool":True,"support_domain":"STRICT_FULL_UNOWNED_POSITIVE_ROOM_DOMAIN_AT_ENTRY","intergroup_ownership_relaxed":False,"H2_eligibility":"R6R7_TARGET_CVS_ONLY","existing_pair_sign_relaxed":False},
   {"execution_group_id":79,"R6R14_bottleneck":CL[79],"group_shared_pool":True,"support_domain":"STRICT_FULL_UNOWNED_POSITIVE_ROOM_DOMAIN_AT_ENTRY","intergroup_ownership_relaxed":False,"H2_eligibility":"R6R7_TARGET_CVS_ONLY","existing_pair_sign_relaxed":False},
   {"execution_group_id":0,"R6R14_bottleneck":CL[0],"group_shared_pool":True,"support_domain":"OWNERSHIP_RELAXED_FULL_POSITIVE_ROOM_DOMAIN","intergroup_ownership_relaxed":True,"H2_eligibility":"ALL_RESIDUAL_CVS_IN_GROUP","existing_pair_sign_relaxed":True},
   {"execution_group_id":3,"R6R14_bottleneck":CL[3],"group_shared_pool":True,"support_domain":"OWNERSHIP_RELAXED_FULL_POSITIVE_ROOM_DOMAIN","intergroup_ownership_relaxed":True,"H2_eligibility":"ALL_RESIDUAL_CVS_IN_GROUP","existing_pair_sign_relaxed":True},
  ];plan={int(r["execution_group_id"]):r for r in plans};pools={};allcells=np.arange(NCELL,dtype=np.int64);ucvs=set()
  for gid in UNRES:
   cids=[int(x) for x in gm[gid]["R6R6_component_ids"].split(";") if x];gc=np.asarray(sorted(v for c in cids for v in cc[c]),dtype=np.int64);ucvs.update(gc.tolist());gp=set(x for c in cids for x in comp_pool[c]);pm=np.isin(pcv,gc);fixed=old+np.bincount(pcel[~pm],weights=pval[~pm],minlength=NCELL)+np.bincount(hcel,weights=hm,minlength=NCELL);room=cap-fixed;mode=plan[gid]["support_domain"]
   if mode=="CURRENT_FROZEN_GROUP_SUPPORT_ONLY":pools[gid]=gp
   elif mode=="STRICT_FULL_UNOWNED_POSITIVE_ROOM_DOMAIN_AT_ENTRY":pools[gid]=gp|set(int(c) for c in allcells[room>RTOL] if int(c) not in s0 and int(c) not in r5fixed and int(c) not in owners)
   else:pools[gid]=gp|set(int(c) for c in allcells[room>RTOL] if int(c) not in s0 and int(c) not in r5fixed)

  stage="joint"
  from scipy.optimize import linprog
  from scipy import sparse
  ucv=np.asarray(sorted(ucvs),dtype=np.int64);pm=np.isin(pcv,ucv);pi=np.flatnonzero(pm&(np.abs(pval)>STOL));xcv=pcv[pi];xcell=pcel[pi];x0=pval[pi];cvg={int(v):c2g[cv2c[int(v)]] for v in ucv}
  bi=[];yk=[];qk=[]
  for gid in UNRES:
   cids=[int(x) for x in gm[gid]["R6R6_component_ids"].split(";") if x];elig=set(int(v) for c in cids for v in (cc[c].tolist() if plan[gid]["H2_eligibility"]=="ALL_RESIDUAL_CVS_IN_GROUP" else tgt[c]));ps=pools[gid]
   for c in cids:
    for cv,h in base[c]:
     if cv in elig and h in ps:continue
     bi.append((int(cv),int(h)))
   yk += [(gid,int(v)) for v in sorted(elig)];qk += [(gid,int(c)) for c in sorted(ps)]
  bi=sorted(set(bi));yk=sorted(set(yk));qk=sorted(set(qk));nx,nb,ny,nq=len(pi),len(bi),len(yk),len(qk);ncv=len(ucv);ob=nx;oy=ob+nb;oq=oy+ny;nv=oq+nq;cr={int(v):i for i,v in enumerate(ucv)};grr={g:ncv+i for i,g in enumerate(UNRES)}
  er=[];ec=[];ev=[]
  for q,v in enumerate(xcv):er.append(cr[int(v)]);ec.append(q);ev.append(1.)
  for q,(v,h) in enumerate(bi):er.append(cr[v]);ec.append(ob+q);ev.append(1.)
  for q,(g,v) in enumerate(yk):er += [cr[v],grr[g]];ec += [oy+q,oy+q];ev += [1.,1.]
  for q,(g,c) in enumerate(qk):er.append(grr[g]);ec.append(oq+q);ev.append(-1.)
  Aeq=sparse.coo_matrix((ev,(er,ec)),shape=(ncv+len(UNRES),nv)).tocsr();beq=np.r_[cur[ucv],np.zeros(len(UNRES))]
  loc=sorted(set(xcell.tolist())|set(h for _,h in bi)|set(c for _,c in qk));lr={c:i for i,c in enumerate(loc)};rr=[];ci=[];vv=[]
  for q,c in enumerate(xcell):rr.append(lr[int(c)]);ci.append(q);vv.append(1.)
  for q,(v,c) in enumerate(bi):rr.append(lr[c]);ci.append(ob+q);vv.append(1.)
  for q,(g,c) in enumerate(qk):rr.append(lr[c]);ci.append(oq+q);vv.append(1.)
  Ac=sparse.coo_matrix((vv,(rr,ci)),shape=(len(loc),nv)).tocsr();fixed=old+np.bincount(pcel[~pm],weights=pval[~pm],minlength=NCELL)+np.bincount(hcel,weights=hm,minlength=NCELL);li=np.asarray(loc,dtype=np.int64);Aub=sparse.vstack([Ac,-Ac]);bub=np.r_[cap[li]-fixed[li],fixed[li]]
  bd=[];relaxed=0
  for v,cv in zip(x0,xcv):
   gid=cvg[int(cv)]
   if plan[gid]["existing_pair_sign_relaxed"]:bd.append((None,None));relaxed+=1
   elif v>STOL:bd.append((0,None))
   elif v<-STOL:bd.append((None,0))
   else:bd.append((0,0))
  bd += [(0,None)]*(nb+ny+nq)
  lp=linprog(np.zeros(nv),A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=beq,bounds=bd,method="highs",options={"presolve":True})
  mcv=lo=hi=None;joint=False
  if lp.success:
   z=np.asarray(lp.x);res=np.asarray(Aeq[:ncv]@z-beq[:ncv]).ravel();cm=fixed[li]+np.asarray(Ac@z).ravel();mcv=float(np.max(np.abs(res)));lo=max(0.,-float(np.min(cm)));hi=max(0.,float(np.max(cm-cap[li])));joint=mcv<=CVTOL and lo<=CTOL and hi<=CTOL
  gate("joint_LP_success",lp.success,lp.message);gate("joint_exact_feasible",joint,(mcv,lo,hi))

  stage="publish";out.mkdir(parents=True)
  (out/"POSTV16_AV4_PIVOT_P2_R6_R15_Group_Reconciliation_Semantics.csv").write_bytes(csvb(plans))
  dom=[{"execution_group_id":g,"candidate_pool_cell_count":len(pools[g]),"support_domain":plan[g]["support_domain"],"H2_eligibility":plan[g]["H2_eligibility"],"existing_pair_sign_relaxed":plan[g]["existing_pair_sign_relaxed"]} for g in UNRES]
  (out/"POSTV16_AV4_PIVOT_P2_R6_R15_Candidate_Domain_Audit.csv").write_bytes(csvb(dom))
  audit={"prospective_joint_exact_feasible":joint,"HiGHS_status":int(lp.status),"HiGHS_message":str(lp.message),"joint_existing_pair_variable_count":nx,"joint_baseline_H2_variable_count":nb,"joint_H2_CV_aggregate_variable_count":ny,"joint_H2_cell_aggregate_variable_count":nq,"joint_total_variable_count":nv,"joint_CV_count":ncv,"joint_local_cell_count":len(loc),"sign_relaxed_existing_pair_variable_count":relaxed,"maximum_CV_residual_kg":mcv,"maximum_cell_lower_violation_kg":lo,"maximum_cell_upper_violation_kg":hi}
  (out/"POSTV16_AV4_PIVOT_P2_R6_R15_Prospective_Joint_Feasibility_Audit.json").write_bytes(jb(audit))
  C="R6R15_BOTTLENECK_SPECIFIC_FIVE_GROUP_RECONCILIATION_SEMANTICS_JOINTLY_EXACT_FEASIBLE_CONTROLLED_EXECUTION_NEXT"
  summary={"milestone":M,"name":NAME,"status":PASS,"classification":C,"R6R14_group_classifications":{str(k):v for k,v in CL.items()},"prospective_joint_exact_feasible":joint,"candidate_domain_cell_counts":{str(r["execution_group_id"]):r["candidate_pool_cell_count"] for r in dom},"joint_total_variable_count":nv,"joint_CV_count":ncv,"joint_local_cell_count":len(loc),"sign_relaxed_existing_pair_variable_count":relaxed,"state_mutation_executed":False,"support_growth_executed":False,"pressure_refresh_executed":False,"time_advance_executed":False,"P3_authorized":False}
  contract={"milestone":M,"name":NAME,"status":PASS,"classification":C,"design_freeze_only":True,"state_mutation_executed":False,"joint_execution_contract":{"single_coupled_five_group_LP_required":True,"global_cell_capacity_constraints_required":True,"single_global_mass_ledger_required":True,"independent_group_execution_forbidden":True,"entry_candidate_domains_immutable_during_execution":True,"cell_to_cell_mass_transit_forbidden":True,"sign_relaxation_scope_limited_to_groups_0_3":True,"R16_secondary_objective_must_minimize_sign_relaxation_magnitude_for_groups_0_3":True},"prospective_joint_feasibility":audit}
  decision={"milestone":M,"status":PASS,"classification":C,"P2_R6_R16_authorized":True,"P2_R6_R16_name":"Controlled Day375 Five-Group Bottleneck-Specific Joint CV-Conservative Reconciliation Execution","P2_R6_R16_joint_reconciliation_execution_authorized":True,"P2_R6_R16_must_bind_R6R14_bottleneck_classification_contract":True,"P2_R6_R16_must_bind_R6R15_branch_semantics_contract":True,"P2_R6_R16_independent_group_execution_forbidden":True,"support_growth_execution_authorized_now":False,"new_H2_endpoint_execution_authorized_now":False,"accepted_Day375_state_authorized_now":False,"pressure_refresh_authorized":False,"time_advance_authorized":False,"P3_authorized":False,"P4_authorized":False,"P5_training_authorized":False}
  (out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R15_Summary.json").write_bytes(jb(summary));(out/"POSTV16_AV4_PIVOT_P2_R6_R15_Reconciliation_Design_Contract.json").write_bytes(jb(contract));(out/"POSTV16_AV4_PIVOT_P2_R6_R15_Decision_Contract.json").write_bytes(jb(decision))
  gate("R5_unchanged",sha(stp)==R5SHA);(out/"POSTV16_AV4_PIVOT_P2_R6_R15_Final_Gate_Matrix.csv").write_bytes(csvb(gates))
  mr=[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()];(out/"POSTV16_AV4_PIVOT_P2_R6_R15_Artifact_Manifest.csv").write_bytes(csvb(mr))
  print("POSTV16-AV4-PIVOT-P2-R6-R15: PASS");print("Joint exact feasible:",joint);print("R6-R16 joint execution authorized: True");return 0
 except Exception as e:
  blk.mkdir(parents=True,exist_ok=True);rp=blk/"POSTV16_AV4_PIVOT_P2_R6_R15_Blocked_Report.json"
  if not rp.exists():rp.write_bytes(jb({"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(e),"state_mutation_executed":False,"automatic_rerun_authorized":False,"gates_completed":gates}))
  print(M+": BLOCKED");print("Stage:",stage);print("Exception:",repr(e));return 2

if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--project-root",type=Path,default=Path("."));ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"));ap.add_argument("--self-test",action="store_true");a=ap.parse_args()
 if a.self_test:selftest();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
