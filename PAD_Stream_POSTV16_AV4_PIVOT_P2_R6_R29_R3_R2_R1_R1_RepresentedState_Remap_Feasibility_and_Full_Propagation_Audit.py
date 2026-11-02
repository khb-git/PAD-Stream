#!/usr/bin/env python3
from __future__ import annotations

import argparse,csv,hashlib,importlib.util,io,json,subprocess,sys,zipfile
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-P2-R6-R29-R3-R2-R1-R1"
NAME="Represented-State Remap Feasibility + Full Propagation Audit"
PASS="AV4PIVOTP2R6R29R3R2R1R1_REPRESENTED_STATE_REMAP_FEASIBILITY_AND_FULL_PROPAGATION_AUDIT_PASS_NO_STATE_MUTATION"
BLOCK="AV4PIVOTP2R6R29R3R2R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="8bcd9511414fe9d2b7c1f9fee6a63a9e02705902"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3=Path("post_v16")/RID/"POSTV16_AV3_Corey_Relperm_Heterogeneity"
GRID=(15,50,50);NSL=1078;NN=201;NCV=200;NCELL=int(np.prod(GRID))
DT=0.03721673128859954;TARGET=375.0372167312886;DAY_TO_S=86400.0
BACKGROUND=0.20;MAX_SAT=0.80;MAX_SG=0.60
MASS_TOL=1e-6;SAT_TOL=1e-10;REL_TOL=1e-10

# R29-R3-R2-R1 authority.
F_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_Compressibility_Accounting_FluxLaw_Alternatives_and_Full_Propagation_Audit"
F_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_Summary.json"
F_DECISION="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_Decision_Contract.json"
F_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_Artifact_Manifest.csv"
F_ARRAYS="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_FluxLaw_Alternative_Propagation_Arrays.npz"
F_STATUS="AV4PIVOTP2R6R29R3R2R1_COMPRESSIBILITY_ACCOUNTING_FLUX_LAW_ALTERNATIVES_AND_FULL_PROPAGATION_AUDIT_PASS_NO_STATE_MUTATION"
F_CLASS="NO_TESTED_COMPRESSIBILITY_ACCOUNTING_FLUX_LAW_PASSES_FULL_PROPAGATION"

# Accepted parent.
R25_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R25_R3_Controlled_Day375_CapacityLimited_ExactSupport_SplitState_Reprojection_Execution_Stage2_PresolveOff"
R25_STATE="POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
R25_SHA="9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

A6E_REL=BASE_AV3/"POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE="POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_SHA="f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

F_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_Compressibility_Accounting_FluxLaw_Alternatives_and_Full_Propagation_Audit.py"
F_RUNNER_BLOB="160e9866e41dc8c83563559324c8e8867f24d424"
E37A="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py";E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
R2SRC="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py";R2SRC_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
A2E="PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py";A2E_BLOB="79a8969233b72b4543edd382a0c3d1028c6dca09"
SG7D="PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py";SG7D_BLOB="890088c0c0fcab415a2c7351c5079ca8ee12bf82"
E36="PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py";E36_BLOB="9ab4035c95a25bd61c649f86c82d88f059cef9e2"

SOURCE_BLOBS={F_RUNNER:F_RUNNER_BLOB,E37A:E37A_BLOB,R2SRC:R2SRC_BLOB,A2E:A2E_BLOB,SG7D:SG7D_BLOB,E36:E36_BLOB}
OUT_TOKEN="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1"
OUT_REL=BASE/(OUT_TOKEN+"_RepresentedState_Remap_Feasibility_and_Full_Propagation_Audit")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")

ALT_NAMES=("SG7A_uD_reference_density","source_mass_normalized")

class GateError(RuntimeError):pass

def gt(root,*args):return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for c in iter(lambda:f.read(1<<20),b""):h.update(c)
 return h.hexdigest()
def js(p):return json.loads(p.read_text(encoding="utf-8"))
def csvr(p):
 with open(p,newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def csvb(rows):
 if not rows:return b""
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields:fields.append(k)
 s=io.StringIO(newline="");w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows);return s.getvalue().encode()
def jb(o):return (json.dumps(o,indent=2,sort_keys=True)+"\n").encode()
def manifest(d,n):
 out={}
 for r in csvr(d/n):
  p=d/r["file"]
  if not p.is_file():raise GateError(f"manifest_missing:{p.name}")
  if sha(p)!=r["sha256"]:raise GateError(f"manifest_sha:{p.name}")
  if p.stat().st_size!=int(r["bytes"]):raise GateError(f"manifest_bytes:{p.name}")
  out[p.name]=r["sha256"]
 return out
def load_module(p,n):
 spec=importlib.util.spec_from_file_location(n,p)
 if spec is None or spec.loader is None:raise GateError(f"cannot_load:{p}")
 m=importlib.util.module_from_spec(spec);sys.modules[n]=m;spec.loader.exec_module(m);return m
def npzb(arrays):
 outer=io.BytesIO()
 with zipfile.ZipFile(outer,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for k in sorted(arrays):
   a=np.asarray(arrays[k])
   if a.dtype==object:raise GateError(f"object_dtype:{k}")
   b=io.BytesIO();np.lib.format.write_array(b,a,allow_pickle=False)
   info=zipfile.ZipInfo(f"{k}.npy");info.date_time=(1980,1,1,0,0,0);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o600<<16
   z.writestr(info,b.getvalue())
 return outer.getvalue()

def selftest():
 # Two CVs share two cells; absolute support reprojection can satisfy capacity.
 edge_cv=np.asarray([0,0,1,1]);edge_cell=np.asarray([0,1,0,1])
 assert len(edge_cv)==4 and len(edge_cell)==4
 print("POSTV16 AV4 PIVOT P2-R6-R29-R3-R2-R1-R1 structural self-test: PASS")

def main(project_root,drive_root):
 from scipy.optimize import linprog
 from scipy.sparse import coo_matrix,vstack

 root=project_root.resolve();drive=drive_root.resolve();out=drive/OUT_REL;block=drive/BLOCK_REL
 stage="preflight";gates=[]
 def gate(n,c,d=None):
  ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
  print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"))
  if not ok:raise GateError(n)

 try:
  stage="preexisting_state_firewall"
  gate("no_preexisting_PASS",not(out/f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
  gate("no_preexisting_BLOCK",not(block/f"{OUT_TOKEN}_Blocked_Report.json").exists())

  stage="repository_authority"
  gate("branch_exact",gt(root,"branch","--show-current")==BRANCH)
  gate("parent_exact",gt(root,"rev-parse","HEAD^")==PARENT)
  gate("repository_clean",gt(root,"status","--porcelain")=="")
  for fn,ex in SOURCE_BLOBS.items():
   p=root/fn;gate(f"{Path(fn).stem}_present",p.is_file(),str(p))
   actual=gt(root,"hash-object",str(p)) if p.is_file() else "missing";gate(f"{Path(fn).stem}_blob_exact",actual==ex,actual)

  stage="flux_audit_authority"
  fd=drive/F_REL;mm=manifest(fd,F_MANIFEST);fs=js(fd/F_SUMMARY);fdec=js(fd/F_DECISION)
  gate("flux_audit_status_exact",fs.get("status")==F_STATUS,fs.get("status"))
  gate("flux_audit_class_exact",fs.get("classification")==F_CLASS,fs.get("classification"))
  gate("theory_flux_CV_capacity_pass",fs["results"]["SG7A_uD_reference_density"]["CV_capacity_pass"] is True)
  gate("theory_flux_direct_mapback_rep_negative",fs["results"]["SG7A_uD_reference_density"]["represented_nonnegative_pass"] is False)
  gate("theory_flux_direct_mapback_cart_capacity_fail",fs["results"]["SG7A_uD_reference_density"]["heterogeneous_cartesian_capacity_pass"] is False)
  gate("source_normalized_CV_capacity_pass",fs["results"]["source_mass_normalized"]["CV_capacity_pass"] is True)
  gate("no_prior_repair_design_authority",fdec.get("P2_R6_R29_R3_R2_R2_authorized") is False)
  gate("flux_arrays_manifested",F_ARRAYS in mm)
  with np.load(fd/F_ARRAYS,allow_pickle=False) as z:
   farr={k:z[k].copy() for k in z.files}

  stage="accepted_parent_authority"
  r25=drive/R25_REL;m25=manifest(r25,R25_MANIFEST);sp=r25/R25_STATE
  gate("R25_state_SHA",m25.get(R25_STATE)==R25_SHA and sha(sp)==R25_SHA)
  with np.load(sp,allow_pickle=False) as z:
   grid_parent=np.asarray(z["cartesian_component_mass_kg"],dtype=np.float64)
   represented_parent=np.asarray(z["represented_cartesian_cell_mass_kg"],dtype=np.float64)
   residual_parent=np.asarray(z["grid_residual_component_mass_kg"],dtype=np.float64)
   old_cv_mass=np.asarray(z["transport_CV_component_mass_kg"],dtype=np.float64)
   old_cv_sat=np.asarray(z["transport_CV_saturation"],dtype=np.float64)
   xyz=np.asarray(z["streamline_xyz_m"],dtype=np.float64)
   tof_s=np.asarray(z["streamline_tof_s"],dtype=np.float64)
   weights_m3_s=np.asarray(z["streamline_weight_m3_s"],dtype=np.float64)
   pressure_psi=np.asarray(z["refreshed_pressure_psi"],dtype=np.float64)
   p_ref=float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

  gate("parent_split_identity",float(np.max(np.abs(grid_parent-represented_parent-residual_parent)))<=MASS_TOL)
  gate("parent_represented_total_matches_CV_total",abs(float(np.sum(represented_parent))-float(np.sum(old_cv_mass)))<=1e-6,
       float(np.sum(represented_parent))-float(np.sum(old_cv_mass)))

  e37a=load_module(root/E37A,"remap_e37a");r2=load_module(root/R2SRC,"remap_r2");a2e=load_module(root/A2E,"remap_a2e")
  sg7d=load_module(root/SG7D,"remap_sg7d");e36=load_module(root/E36,"remap_e36")
  a6=drive/A6E_REL/A6E_STATE;gate("A6E_SHA",a6.is_file() and sha(a6)==A6E_SHA)
  with np.load(a6,allow_pickle=False) as z:phi=np.asarray(z["paired_porosity"],dtype=np.float64)
  hetero_pv=phi*float(a2e.BULK_VOLUME_M3)
  full_sat=np.full(GRID,float(a2e.INJECTED))
  cart_capacity=np.asarray(a2e.local_mass(r2,full_sat,pressure_psi,p_ref,hetero_pv),dtype=np.float64)
  represented_capacity=cart_capacity-residual_parent
  parent_cap_tol=max(1e-8,1e-12*max(float(np.max(cart_capacity)),1.0))
  gate("represented_capacity_nonnegative",float(np.min(represented_capacity))>=-parent_cap_tol,float(np.min(represented_capacity)))
  represented_capacity=np.maximum(represented_capacity,0.0)

  op=sg7d.build_subsegment_operator(xyz,tof_s/DAY_TO_S,weights_m3_s*DAY_TO_S)
  geometry=e37a.build_control_volume_geometry(r2,op,pressure_psi,p_ref,NSL,NCV)
  cv_id=np.asarray(geometry["cv_id"],dtype=np.int64)
  flat=np.asarray(geometry["flat_cell"],dtype=np.int64)
  sub_pv=np.asarray(geometry["pv_m3"],dtype=np.float64)
  pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64)
  ncv_total=NSL*NCV

  # Unique existing CV-cell support.
  stage="support_edge_construction"
  pair_key=cv_id.astype(np.int64)*NCELL+flat.astype(np.int64)
  uniq,inv=np.unique(pair_key,return_inverse=True)
  edge_cv=(uniq//NCELL).astype(np.int64)
  edge_cell=(uniq%NCELL).astype(np.int64)
  nedge=len(uniq)
  edge_count=np.bincount(edge_cv,minlength=ncv_total)
  gate("support_edge_count_positive",nedge>0,nedge)
  gate("every_nonzero_parent_CV_has_support",np.all(edge_count[old_cv_mass.reshape(-1)>MASS_TOL]>0))

  # Parent subsegment-implied absolute represented inventory.
  old_sub_sat=old_cv_sat.reshape(-1)[cv_id]
  old_sub_sg=np.clip(old_sub_sat-BACKGROUND,0.,MAX_SG)
  old_rho=np.asarray(r2.gas_density_from_state(old_sub_sat,pseg,p_ref),dtype=np.float64)
  old_sub_mass=sub_pv*old_rho*old_sub_sg
  old_edge_abs=np.bincount(inv,weights=old_sub_mass,minlength=nedge)
  old_implied_grid=np.bincount(flat,weights=old_sub_mass,minlength=NCELL).reshape(GRID)
  parent_embedding_diff=represented_parent-old_implied_grid
  embedding_l1=float(np.sum(np.abs(parent_embedding_diff)))
  embedding_max=float(np.max(np.abs(parent_embedding_diff)))
  embedding_cells=int(np.count_nonzero(np.abs(parent_embedding_diff)>MASS_TOL))

  # Sparse incidence helpers.
  cell_rows=edge_cell
  cell_cols=np.arange(nedge,dtype=np.int64)
  A_cell=coo_matrix((np.ones(nedge), (cell_rows,cell_cols)),shape=(NCELL,nedge)).tocsr()

  results={};all_arrays={
   "edge_cv":edge_cv,"edge_cell":edge_cell,
   "old_edge_absolute_mass_kg":old_edge_abs,
   "old_subsegment_implied_grid_mass_kg":old_implied_grid,
   "accepted_represented_parent_mass_kg":represented_parent,
   "parent_embedding_difference_kg":parent_embedding_diff,
   "represented_capacity_kg":represented_capacity,
  }

  def active_eq_matrix(supply):
   flat_supply=np.asarray(supply,dtype=np.float64).reshape(-1)
   active=np.where(np.abs(flat_supply)>MASS_TOL)[0]
   rowmap=np.full(ncv_total,-1,dtype=np.int64);rowmap[active]=np.arange(len(active),dtype=np.int64)
   rr=rowmap[edge_cv];mask=rr>=0
   A=coo_matrix((np.ones(int(np.count_nonzero(mask))),(rr[mask],np.nonzero(mask)[0])),
                shape=(len(active),nedge)).tocsr()
   b=flat_supply[active]
   return active,A,b

  def propagate_cell_rep(rep_candidate,new_cv_mass,flux):
   cand=rep_candidate+residual_parent
   minrep=float(np.min(rep_candidate));split=float(np.max(np.abs(cand-rep_candidate-residual_parent)))
   capex=float(np.max(cand-cart_capacity));ctol=max(1e-8,1e-12*max(float(np.max(cart_capacity)),1.0))
   injected=float(np.sum(flux[:,0])*DT);produced=float(np.sum(flux[:,-1])*DT)
   target=float(np.sum(grid_parent))+injected-produced;tot=float(np.sum(cand))
   sr=tot-target;gtol=max(MASS_TOL,REL_TOL*max(abs(target),1.0))
   invpass=False;cerr=None;smin=None;smax=None
   if minrep>=-MASS_TOL and capex<=ctol:
    csg=np.asarray(a2e.invert_local_mass(r2,cand,pressure_psi,p_ref,hetero_pv),dtype=np.float64)
    cs=float(a2e.BACKGROUND)+csg
    recon=np.asarray(a2e.local_mass(r2,cs,pressure_psi,p_ref,hetero_pv),dtype=np.float64)
    cerr=float(np.max(np.abs(recon-cand)));smin=float(np.min(cs));smax=float(np.max(cs))
    invpass=cerr<=1e-8 and smin>=BACKGROUND-SAT_TOL and smax<=MAX_SAT+SAT_TOL
   return {"represented_nonnegative_pass":minrep>=-MASS_TOL,"split_identity_pass":split<=MASS_TOL,
           "heterogeneous_cartesian_capacity_pass":capex<=ctol,"heterogeneous_cartesian_inversion_pass":invpass,
           "cartesian_source_sink_closure_pass":abs(sr)<=gtol,
           "minimum_represented_candidate_mass_kg":minrep,"split_identity_max_abs_error_kg":split,
           "cartesian_max_capacity_excess_kg":capex,"cartesian_capacity_tolerance_kg":ctol,
           "cartesian_cellwise_mass_reconstruction_error_kg":cerr,
           "candidate_saturation_min":smin,"candidate_saturation_max":smax,
           "cartesian_source_sink_residual_kg":sr,
           "represented_total_kg":float(np.sum(rep_candidate)),
           "new_CV_total_kg":float(np.sum(new_cv_mass))}

  for alt in ALT_NAMES:
   stage=f"{alt}_target_construction"
   new_mass=np.asarray(farr[alt+"_new_CV_mass_kg"],dtype=np.float64)
   new_sat=np.asarray(farr[alt+"_new_CV_saturation"],dtype=np.float64)
   flux=np.asarray(farr[alt+"_face_mass_flux_kg_day"],dtype=np.float64)
   cv_delta=new_mass-old_cv_mass

   new_sub_sat=new_sat.reshape(-1)[cv_id]
   new_sub_sg=np.clip(new_sub_sat-BACKGROUND,0.,MAX_SG)
   new_rho=np.asarray(r2.gas_density_from_state(new_sub_sat,pseg,p_ref),dtype=np.float64)
   new_sub_mass=sub_pv*new_rho*new_sub_sg
   sub_delta=new_sub_mass-old_sub_mass
   target_delta_edge=np.bincount(inv,weights=sub_delta,minlength=nedge)
   target_new_abs_edge=np.bincount(inv,weights=new_sub_mass,minlength=nedge)

   # Per-CV edge closure.
   edge_delta_cv=np.bincount(edge_cv,weights=target_delta_edge,minlength=ncv_total).reshape(NSL,NCV)
   edge_abs_cv=np.bincount(edge_cv,weights=target_new_abs_edge,minlength=ncv_total).reshape(NSL,NCV)
   delta_closure=float(np.max(np.abs(edge_delta_cv-cv_delta)))
   abs_closure=float(np.max(np.abs(edge_abs_cv-new_mass)))

   direct_delta_grid=np.bincount(edge_cell,weights=target_delta_edge,minlength=NCELL).reshape(GRID)
   direct_rep=represented_parent+direct_delta_grid
   direct=propagate_cell_rep(direct_rep,new_mass,flux)

   # ---------------------------------------------------------------
   # A) Support-constrained signed DELTA redistribution.
   # ---------------------------------------------------------------
   stage=f"{alt}_delta_remap_LP"
   active,Aeq,beq=active_eq_matrix(cv_delta)
   lb=np.full(nedge,-np.inf);ub=np.full(nedge,np.inf)
   dflat=cv_delta.reshape(-1)
   sign=dflat[edge_cv]
   lb[sign>MASS_TOL]=0.0
   ub[sign<-MASS_TOL]=0.0
   zero=np.abs(sign)<=MASS_TOL;lb[zero]=0.0;ub[zero]=0.0

   upper=(cart_capacity-grid_parent).reshape(-1)
   lower_allow=represented_parent.reshape(-1)
   upper=np.maximum(upper,0.0);lower_allow=np.maximum(lower_allow,0.0)
   Aub=vstack([A_cell,-A_cell],format="csr")
   bub=np.concatenate([upper,lower_allow])
   sol_delta=linprog(np.zeros(nedge),A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=beq,
                     bounds=list(zip(lb,ub)),method="highs",
                     options={"presolve":True})
   delta_feasible=bool(sol_delta.success)
   delta_result={"LP_feasible":delta_feasible,"LP_status":int(sol_delta.status),
                 "LP_message":str(sol_delta.message),"active_CV_count":int(len(active))}
   if delta_feasible:
    x=np.asarray(sol_delta.x,dtype=np.float64)
    cell_delta=np.bincount(edge_cell,weights=x,minlength=NCELL).reshape(GRID)
    rep=represented_parent+cell_delta
    pr=propagate_cell_rep(rep,new_mass,flux)
    deviation=x-target_delta_edge
    delta_result.update(pr)
    delta_result.update({"edge_target_L1_deviation_kg":float(np.sum(np.abs(deviation))),
                         "edge_target_max_abs_deviation_kg":float(np.max(np.abs(deviation))),
                         "changed_edge_count":int(np.count_nonzero(np.abs(deviation)>MASS_TOL)),
                         "all_downstream_checks_pass":all(bool(pr[k]) for k in(
                          "represented_nonnegative_pass","split_identity_pass",
                          "heterogeneous_cartesian_capacity_pass","heterogeneous_cartesian_inversion_pass",
                          "cartesian_source_sink_closure_pass"))})
    all_arrays[alt+"_delta_LP_edge_allocation_kg"]=x
    all_arrays[alt+"_delta_LP_represented_candidate_kg"]=rep
   else:
    delta_result["all_downstream_checks_pass"]=False

   # ---------------------------------------------------------------
   # B) Support-constrained ABSOLUTE represented-state reprojection.
   # ---------------------------------------------------------------
   stage=f"{alt}_absolute_reprojection_LP"
   active2,Aeq2,beq2=active_eq_matrix(new_mass)
   cap=represented_capacity.reshape(-1)
   sol_abs=linprog(np.zeros(nedge),A_ub=A_cell,b_ub=cap,A_eq=Aeq2,b_eq=beq2,
                   bounds=(0.0,None),method="highs",options={"presolve":True})
   abs_feasible=bool(sol_abs.success)
   abs_result={"LP_feasible":abs_feasible,"LP_status":int(sol_abs.status),
               "LP_message":str(sol_abs.message),"active_CV_count":int(len(active2))}
   if abs_feasible:
    y=np.asarray(sol_abs.x,dtype=np.float64)
    rep=np.bincount(edge_cell,weights=y,minlength=NCELL).reshape(GRID)
    pr=propagate_cell_rep(rep,new_mass,flux)
    deviation=y-target_new_abs_edge
    abs_result.update(pr)
    abs_result.update({"edge_target_L1_deviation_kg":float(np.sum(np.abs(deviation))),
                       "edge_target_max_abs_deviation_kg":float(np.max(np.abs(deviation))),
                       "changed_edge_count":int(np.count_nonzero(np.abs(deviation)>MASS_TOL)),
                       "represented_change_L1_from_parent_kg":float(np.sum(np.abs(rep-represented_parent))),
                       "all_downstream_checks_pass":all(bool(pr[k]) for k in(
                        "represented_nonnegative_pass","split_identity_pass",
                        "heterogeneous_cartesian_capacity_pass","heterogeneous_cartesian_inversion_pass",
                        "cartesian_source_sink_closure_pass"))})
    all_arrays[alt+"_absolute_LP_edge_allocation_kg"]=y
    all_arrays[alt+"_absolute_LP_represented_candidate_kg"]=rep
   else:
    abs_result["all_downstream_checks_pass"]=False

   results[alt]={
    "target_edge_delta_CV_closure_max_abs_kg":delta_closure,
    "target_edge_absolute_CV_closure_max_abs_kg":abs_closure,
    "direct_flat_delta_mapback":direct,
    "support_constrained_signed_delta_redistribution":delta_result,
    "support_constrained_absolute_represented_reprojection":abs_result,
   }
   all_arrays[alt+"_target_edge_delta_kg"]=target_delta_edge
   all_arrays[alt+"_target_edge_new_absolute_mass_kg"]=target_new_abs_edge
   all_arrays[alt+"_direct_delta_grid_kg"]=direct_delta_grid

  theory=results["SG7A_uD_reference_density"]
  if theory["support_constrained_signed_delta_redistribution"]["all_downstream_checks_pass"]:
   classification="THEORY_PREFERRED_FLUX_SUPPORT_CONSTRAINED_SIGNED_DELTA_REMAP_FEASIBLE_WITH_FULL_PROPAGATION_CLOSURE"
   preferred="support_constrained_signed_delta_redistribution"
  elif theory["support_constrained_absolute_represented_reprojection"]["all_downstream_checks_pass"]:
   classification="THEORY_PREFERRED_FLUX_REQUIRES_SUPPORT_CONSTRAINED_ABSOLUTE_REPRESENTED_STATE_REPROJECTION_FOR_FULL_PROPAGATION_CLOSURE"
   preferred="support_constrained_absolute_represented_reprojection"
  else:
   classification="THEORY_PREFERRED_FLUX_HAS_NO_FEASIBLE_TESTED_EXISTING_SUPPORT_REMAP_WITH_FULL_PROPAGATION_CLOSURE"
   preferred=None

  stage="publication"
  out.mkdir(parents=True,exist_ok=False)
  (out/f"{OUT_TOKEN}_Remap_Feasibility_Arrays.npz").write_bytes(npzb(all_arrays))

  rows=[]
  for alt,r in results.items():
   for scheme in ("direct_flat_delta_mapback","support_constrained_signed_delta_redistribution","support_constrained_absolute_represented_reprojection"):
    x=r[scheme];rows.append({"flux_law":alt,"mapback_scheme":scheme,
      "feasible":x.get("LP_feasible",scheme=="direct_flat_delta_mapback"),
      "represented_nonnegative_pass":x.get("represented_nonnegative_pass"),
      "cartesian_capacity_pass":x.get("heterogeneous_cartesian_capacity_pass"),
      "cartesian_inversion_pass":x.get("heterogeneous_cartesian_inversion_pass"),
      "source_sink_closure_pass":x.get("cartesian_source_sink_closure_pass"),
      "all_downstream_checks_pass":x.get("all_downstream_checks_pass",False),
      "edge_target_L1_deviation_kg":x.get("edge_target_L1_deviation_kg"),
      "edge_target_max_abs_deviation_kg":x.get("edge_target_max_abs_deviation_kg"),
      "LP_status":x.get("LP_status"),"LP_message":x.get("LP_message")})
  (out/f"{OUT_TOKEN}_Remap_Feasibility_Comparison.csv").write_bytes(csvb(rows))

  summary={"milestone":M,"name":NAME,"status":PASS,"classification":classification,
   "source_flux_audit_summary_sha256":mm[F_SUMMARY],"nominal_dt_days":DT,"candidate_target_day":TARGET,
   "unique_existing_CV_cell_support_edge_count":nedge,
   "parent_subsegment_implied_vs_accepted_represented_L1_difference_kg":embedding_l1,
   "parent_subsegment_implied_vs_accepted_represented_max_abs_cell_difference_kg":embedding_max,
   "parent_subsegment_implied_vs_accepted_represented_different_cell_count":embedding_cells,
   "results":results,"theory_preferred_flux_law":"SG7A_uD_reference_density",
   "preferred_mapback_family":preferred,"state_mutation_executed":False,
   "physical_time_advance_executed":False,"R30_authorized":False,"P3_authorized":False}

  audit={"milestone":M,"status":PASS,
   "scientific_question":"Does the downstream failure arise because exact flat-cell delta deposition is inconsistent with the accepted projected represented state, and can the transported CV inventory be conservatively re-embedded on existing support?",
   "parent_embedding_diagnosis":{"accepted_represented_total_kg":float(np.sum(represented_parent)),
      "subsegment_implied_represented_total_kg":float(np.sum(old_implied_grid)),
      "L1_cell_difference_kg":embedding_l1,"max_abs_cell_difference_kg":embedding_max,
      "different_cell_count":embedding_cells},
   "tested_mapback_families":{
      "direct_flat_delta":"existing frozen formula, no redistribution",
      "support_constrained_signed_delta_redistribution":"preserve accepted represented parent; preserve each CV delta; signed allocations only; existing support only; residual fixed; Cartesian bounds enforced",
      "support_constrained_absolute_represented_reprojection":"preserve each transported absolute CV mass; nonnegative allocation on existing support only; residual fixed; Cartesian capacity enforced"},
   "results":results}

  design_authorized=preferred is not None
  decision={"milestone":M,"status":PASS,"classification":classification,
   "P2_R6_R29_R3_R2_R1_R2_authorized":bool(design_authorized),
   "P2_R6_R29_R3_R2_R1_R2_name":"Comprehensive Flux + Represented-State Mapback Repair Design Freeze",
   "P2_R6_R29_R3_R2_R1_R2_design_only":True,
   "P2_R6_R29_R3_R2_R1_R2_execution_authorized":False,
   "preferred_flux_law":"SG7A_uD_reference_density" if design_authorized else None,
   "preferred_mapback_family":preferred,
   "existing_support_only_required":True,"support_growth_authorized":False,
   "residual_sidecar_mutation_authorized":False,
   "nominal_dt_change_authorized":False,"inlet_component_flux_change_authorized":False,
   "storage_density_model_change_authorized":False,"CV_capacity_model_change_authorized":False,
   "physical_time_advance_authorized":False,"R30_authorized":False,"P3_authorized":False}

  (out/f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
  (out/f"{OUT_TOKEN}_RepresentedState_Remap_Audit.json").write_bytes(jb(audit))
  (out/f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
  (out/f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))
  mrows=[]
  for p in sorted(out.iterdir()):
   if p.is_file():mrows.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
  (out/f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(mrows))

  print("="*200)
  print(M,"PASS")
  print("Classification                                      :",classification)
  print("Existing CV-cell support edges                      :",nedge)
  print("Parent embedding L1 mismatch kg                     :",embedding_l1)
  print("Parent embedding max abs cell mismatch kg           :",embedding_max)
  print("Parent embedding different cell count               :",embedding_cells)
  for alt in ALT_NAMES:
   r=results[alt]
   print("---",alt,"---")
   print("Direct flat delta represented/capacity PASS         :",r["direct_flat_delta_mapback"]["represented_nonnegative_pass"],"/",r["direct_flat_delta_mapback"]["heterogeneous_cartesian_capacity_pass"])
   print("Signed delta LP feasible / full propagation PASS    :",r["support_constrained_signed_delta_redistribution"]["LP_feasible"],"/",r["support_constrained_signed_delta_redistribution"]["all_downstream_checks_pass"])
   print("Absolute reprojection LP feasible / full PASS       :",r["support_constrained_absolute_represented_reprojection"]["LP_feasible"],"/",r["support_constrained_absolute_represented_reprojection"]["all_downstream_checks_pass"])
  print("Preferred mapback family                            :",preferred)
  print("Next comprehensive design freeze authorized         :",design_authorized)
  print("State / time / R30                                  : False / False / False")
  print("="*200)
  return 0

 except Exception as exc:
  block.mkdir(parents=True,exist_ok=True);p=block/f"{OUT_TOKEN}_Blocked_Report.json"
  if not p.exists():p.write_bytes(jb({"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),
    "prior_scientific_results_preserved":True,"state_mutation_executed":False,
    "physical_time_advance_executed":False,"R30_authorized":False,"P3_authorized":False,
    "gates_completed":gates}))
  print(M,"TECHNICAL / AUTHORITY BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--project-root",type=Path,default=Path("."));ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"));ap.add_argument("--self-test",action="store_true");a=ap.parse_args()
 if a.self_test:selftest();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
