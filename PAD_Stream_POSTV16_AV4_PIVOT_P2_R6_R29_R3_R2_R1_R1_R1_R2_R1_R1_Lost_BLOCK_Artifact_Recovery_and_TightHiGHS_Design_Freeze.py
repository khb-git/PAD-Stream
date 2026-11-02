#!/usr/bin/env python3
from __future__ import annotations

import argparse,csv,hashlib,importlib.util,io,json,subprocess,sys,zipfile
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-P2-R6-R29-R3-R2-R1-R1-R1-R2-R1-R1"
NAME="Lost BLOCK Artifact Recovery + Tight-HiGHS CV Equality + Comprehensive Repair Design Freeze"

PASS="AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1_LOST_BLOCK_ARTIFACT_RECOVERY_TIGHT_HIGHS_CV_EQUALITY_AND_REPAIR_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
BLOCK="AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH="postv16-av4-pivot"
BLOCKED_PARENT_COMMIT="c7fc21401e7a9858c8acc892be51fda8dca50263"
PUBLISHED_PREFORMAL_PARENT_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_Technical_Closure_TightHiGHS_CVEquality_and_Repair_Design_Freeze.py"
PUBLISHED_PREFORMAL_PARENT_RUNNER_BLOB="069e78a10c615261da71a1e530f03d864f269567"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3=Path("post_v16")/RID/"POSTV16_AV3_Corey_Relperm_Heterogeneity"
GRID=(15,50,50);NCELL=int(np.prod(GRID));NSL=1078;NCV=200;NCVT=NSL*NCV
DT=0.03721673128859954;TARGET_DAY=375.0372167312886
BACKGROUND=0.20;MAX_SAT=0.80
MASS_TOL=1e-6;SAT_TOL=1e-10;REL_TOL=1e-10
HALO_OPT_TOL=1e-6

# Authoritative corrected support audit.
A_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R1_Technical_Closure_Corrected_R25R3_Blob_and_ExactSupport_Deadlock_Audit"
A_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R1_Summary.json"
A_DECISION="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R1_Decision_Contract.json"
A_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R1_Artifact_Manifest.csv"
A_ARRAYS="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R1_Support_Topology_Feasibility_Arrays.npz"
A_STATUS="AV4PIVOTP2R6R29R3R2R1R1R1R1_TECHNICAL_CLOSURE_CORRECTED_R25R3_BLOB_AND_EXACT_SUPPORT_FRONTIER_DEADLOCK_AND_MINIMAL_TERMINAL_SUPPORT_EXTENSION_AUDIT_PASS_NO_STATE_MUTATION"
A_CLASS="EXACT_SUPPORT_FRONTIER_DEADLOCK_CONFIRMED_ONE_SHELL_SAME_LAYER_XY_TERMINAL_SUPPORT_EXTENSION_IS_MINIMAL_TESTED_FULL_CLOSURE_TOPOLOGY"

# Remap audit provides direct-delta target.
R_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_RepresentedState_Remap_Feasibility_and_Full_Propagation_Audit"
R_ARRAYS="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R1_PLACEHOLDER"
# actual filename below is intentionally explicit
R_ARRAYS_ACTUAL="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_Remap_Feasibility_Arrays.npz"
R_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_Artifact_Manifest.csv"

# Flux audit provides theory candidate and face flux.
F_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_Compressibility_Accounting_FluxLaw_Alternatives_and_Full_Propagation_Audit"
F_ARRAYS="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_FluxLaw_Alternative_Propagation_Arrays.npz"
F_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_Artifact_Manifest.csv"

# Accepted Day375 parent.
R25_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R25_R3_Controlled_Day375_CapacityLimited_ExactSupport_SplitState_Reprojection_Execution_Stage2_PresolveOff"
R25_STATE="POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
R25_SHA="9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

A6E_REL=BASE_AV3/"POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE="POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_SHA="f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

A_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R1_Technical_Closure_Corrected_R25R3_Blob_and_ExactSupport_Deadlock_Audit.py"
A_RUNNER_BLOB="33db7db971029fe8de037036a5f44bd6061d45d8"
R2SRC="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py";R2SRC_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
A2E="PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py";A2E_BLOB="79a8969233b72b4543edd382a0c3d1028c6dca09"

SOURCE_BLOCKED_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_Comprehensive_TheoryFlux_XY1_TerminalSupport_Mapback_Repair_Design_Freeze.py"
SOURCE_BLOCKED_RUNNER_BLOB="01465a1f55d31c0b6543264627d075da14f60154"

HIGHS_PRIMAL_FEASIBILITY_TOL=1e-10
HIGHS_DUAL_FEASIBILITY_TOL=1e-10
HIGHS_IPM_OPTIMALITY_TOL=1e-12

SOURCE_BLOBS={SOURCE_BLOCKED_RUNNER:SOURCE_BLOCKED_RUNNER_BLOB,A_RUNNER:A_RUNNER_BLOB,R2SRC:R2SRC_BLOB,A2E:A2E_BLOB}

OUT_TOKEN="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1"
OUT_REL=BASE/(OUT_TOKEN+"_Lost_BLOCK_Artifact_Recovery_and_TightHiGHS_Design_Freeze")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")

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
 # Lexicographic principle: first halo minimum, then closest Cartesian target.
 assert HALO_OPT_TOL>0
 assert OUT_REL.name.startswith(OUT_TOKEN+"_")
 print("POSTV16 AV4 PIVOT P2-R6-R29-R3-R2-R1-R1-R1-R2-R1-R1 structural self-test: PASS")

def main(project_root,drive_root):
 from scipy.optimize import linprog
 from scipy.sparse import coo_matrix,vstack,hstack,csr_matrix

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
  gate("blocked_parent_is_grandparent",gt(root,"rev-parse","HEAD^^")==BLOCKED_PARENT_COMMIT,gt(root,"rev-parse","HEAD^^"))
  parent_runner_blob=gt(root,"rev-parse",f"HEAD^:{PUBLISHED_PREFORMAL_PARENT_RUNNER}")
  gate("published_preformal_parent_runner_blob_exact",parent_runner_blob==PUBLISHED_PREFORMAL_PARENT_RUNNER_BLOB,parent_runner_blob)
  parent_delta=gt(root,"diff","--name-only","HEAD^^","HEAD^").splitlines()
  gate("published_preformal_parent_single_file_exact",parent_delta==[PUBLISHED_PREFORMAL_PARENT_RUNNER],parent_delta)
  gate("repository_clean",gt(root,"status","--porcelain")=="")
  for fn,ex in SOURCE_BLOBS.items():
   p=root/fn;gate(f"{Path(fn).stem}_present",p.is_file(),str(p))
   actual=gt(root,"hash-object",str(p)) if p.is_file() else "missing";gate(f"{Path(fn).stem}_blob_exact",actual==ex,actual)

  stage="lost_parent_BLOCK_artifact_recovery_authority"
  # The c7fc formal run reported TECHNICAL BLOCK at CV_mass_equalities, but
  # that Drive BLOCK artifact is now absent. Never recreate/fabricate it.
  # Bind exact frozen code and reproduce the default-solver failure below.
  blocked_blob=gt(root,"hash-object",str(root/SOURCE_BLOCKED_RUNNER))
  gate("blocked_parent_runner_blob_exact",blocked_blob==SOURCE_BLOCKED_RUNNER_BLOB,blocked_blob)
  parent_cv_equality_detail=None

  stage="authoritative_support_audit"
  ad=drive/A_REL;mma=manifest(ad,A_MANIFEST);sa=js(ad/A_SUMMARY);da=js(ad/A_DECISION)
  gate("support_audit_status_exact",sa.get("status")==A_STATUS,sa.get("status"))
  gate("support_audit_class_exact",sa.get("classification")==A_CLASS,sa.get("classification"))
  gate("deadlock_proved",sa.get("structural_deadlock_proved") is True)
  gate("XY1_first_full_closure",sa.get("first_full_closure_topology")=="XY1")
  xy1=sa["topology_results"]["XY1"]
  gate("XY1_LP_feasible",xy1.get("LP_feasible") is True)
  gate("XY1_full_closure",xy1.get("full_downstream_propagation_pass") is True)
  gate("XY1_terminal_mass_exact",abs(float(xy1["minimum_terminal_extension_mass_kg"])-103.35211851061669)<=1e-9,
       xy1["minimum_terminal_extension_mass_kg"])
  gate("design_freeze_authorized",da.get("P2_R6_R29_R3_R2_R1_R1_R1_R2_authorized") is True)
  gate("design_only",da.get("P2_R6_R29_R3_R2_R1_R1_R1_R2_design_only") is True)
  gate("execution_not_yet_authorized",da.get("P2_R6_R29_R3_R2_R1_R1_R1_R2_execution_authorized") is False)
  gate("preferred_flux_exact",da.get("preferred_flux_law")=="SG7A_uD_reference_density")
  gate("preferred_topology_exact",da.get("minimal_tested_terminal_support_topology")=="XY1")
  gate("support_arrays_manifested",A_ARRAYS in mma)
  with np.load(ad/A_ARRAYS,allow_pickle=False) as z:
   edge_cv=np.asarray(z["XY1_edge_cv"],dtype=np.int64)
   edge_cell=np.asarray(z["XY1_edge_cell"],dtype=np.int64)
   shell=np.asarray(z["XY1_edge_shell_cost"],dtype=np.int8)
   stage1_x=np.asarray(z["XY1_edge_allocation_kg"],dtype=np.float64)

  stage="parent_and_candidate_authority"
  r25=drive/R25_REL;m25=manifest(r25,R25_MANIFEST);sp=r25/R25_STATE
  gate("R25_state_SHA",m25.get(R25_STATE)==R25_SHA and sha(sp)==R25_SHA)
  with np.load(sp,allow_pickle=False) as z:
   grid_parent=np.asarray(z["cartesian_component_mass_kg"],dtype=np.float64)
   represented_parent=np.asarray(z["represented_cartesian_cell_mass_kg"],dtype=np.float64)
   residual_parent=np.asarray(z["grid_residual_component_mass_kg"],dtype=np.float64)
   old_cv_mass=np.asarray(z["transport_CV_component_mass_kg"],dtype=np.float64)
   pressure=np.asarray(z["refreshed_pressure_psi"],dtype=np.float64)
   p_ref=float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

  fd=drive/F_REL;mmf=manifest(fd,F_MANIFEST);gate("flux_arrays_manifested",F_ARRAYS in mmf)
  with np.load(fd/F_ARRAYS,allow_pickle=False) as z:
   new_cv_mass=np.asarray(z["SG7A_uD_reference_density_new_CV_mass_kg"],dtype=np.float64)
   new_cv_sat=np.asarray(z["SG7A_uD_reference_density_new_CV_saturation"],dtype=np.float64)
   theory_flux=np.asarray(z["SG7A_uD_reference_density_face_mass_flux_kg_day"],dtype=np.float64)

  rd=drive/R_REL;mmr=manifest(rd,R_MANIFEST);gate("remap_arrays_manifested",R_ARRAYS_ACTUAL in mmr)
  with np.load(rd/R_ARRAYS_ACTUAL,allow_pickle=False) as z:
   direct_delta_grid=np.asarray(z["SG7A_uD_reference_density_direct_delta_grid_kg"],dtype=np.float64)

  direct_target_rep=represented_parent+direct_delta_grid
  target_total=float(np.sum(direct_target_rep))
  gate("direct_target_total_matches_new_CV_total",abs(target_total-float(np.sum(new_cv_mass)))<=1e-5,
       target_total-float(np.sum(new_cv_mass)))

  stage="heterogeneous_capacity"
  r2src=load_module(root/R2SRC,"freeze_r2");a2e=load_module(root/A2E,"freeze_a2e")
  a6=drive/A6E_REL/A6E_STATE;gate("A6E_SHA",a6.is_file() and sha(a6)==A6E_SHA)
  with np.load(a6,allow_pickle=False) as z:phi=np.asarray(z["paired_porosity"],dtype=np.float64)
  hetero_pv=phi*float(a2e.BULK_VOLUME_M3)
  full=np.full(GRID,float(a2e.INJECTED))
  cart_capacity=np.asarray(a2e.local_mass(r2src,full,pressure,p_ref,hetero_pv),dtype=np.float64)
  rep_capacity=np.maximum(cart_capacity-residual_parent,0.0).reshape(-1)

  # Build sparse matrices for XY1 support.
  stage="lexicographic_stage1_reproduction"
  nedge=len(edge_cv)
  active=np.where(new_cv_mass.reshape(-1)>MASS_TOL)[0]
  cvmap=np.full(NCVT,-1,dtype=np.int64);cvmap[active]=np.arange(len(active),dtype=np.int64)
  rr=cvmap[edge_cv];mask=rr>=0;cols=np.nonzero(mask)[0]
  Aeq=coo_matrix((np.ones(len(cols)),(rr[mask],cols)),shape=(len(active),nedge)).tocsr()
  beq=new_cv_mass.reshape(-1)[active]
  Acell=coo_matrix((np.ones(nedge),(edge_cell,np.arange(nedge))),shape=(NCELL,nedge)).tocsr()
  c1=(shell>0).astype(np.float64)
  lp1=linprog(c1,A_ub=Acell,b_ub=rep_capacity,A_eq=Aeq,b_eq=beq,bounds=(0.0,None),method="highs",options={"presolve":True})
  gate("stage1_XY1_feasible",lp1.success,[lp1.status,lp1.message])
  halo_opt=float(lp1.fun)
  gate("stage1_halo_opt_matches_authority",abs(halo_opt-float(xy1["minimum_terminal_extension_mass_kg"]))<=HALO_OPT_TOL,
       [halo_opt,xy1["minimum_terminal_extension_mass_kg"]])

  # Stage2: hold minimum halo mass and minimize cell-level L1 distance from
  # the old direct-delta Cartesian represented target.
  stage="lexicographic_stage2_cell_L1"
  nd=NCELL
  # Variables z=[x_edge, d_cell].
  zero_d=csr_matrix((Acell.shape[0],nd))
  A_cap=hstack([Acell,zero_d],format="csr")
  b_cap=rep_capacity

  # |Acell*x - target| <= d
  I=csr_matrix(np.eye(nd))
  A_abs_pos=hstack([Acell,-I],format="csr")
  A_abs_neg=hstack([-Acell,-I],format="csr")
  t=direct_target_rep.reshape(-1)
  b_abs_pos=t
  b_abs_neg=-t

  # Halo optimum within tolerance, represented as two inequalities.
  halo_row=csr_matrix(c1.reshape(1,-1))
  zero1=csr_matrix((1,nd))
  A_halo_pos=hstack([halo_row,zero1],format="csr")
  A_halo_neg=hstack([-halo_row,zero1],format="csr")
  b_halo=np.asarray([halo_opt+HALO_OPT_TOL,-halo_opt+HALO_OPT_TOL],dtype=np.float64)

  A_ub=vstack([A_cap,A_abs_pos,A_abs_neg,A_halo_pos,A_halo_neg],format="csr")
  b_ub=np.concatenate([b_cap,b_abs_pos,b_abs_neg,b_halo])

  Aeq2=hstack([Aeq,csr_matrix((Aeq.shape[0],nd))],format="csr")
  c2=np.concatenate([np.zeros(nedge),np.ones(nd)])
  bounds=[(0.0,None)]*(nedge+nd)

  # Reproduce the lost c7fc BLOCK using the exact default HiGHS settings.
  lp2_default=linprog(c2,A_ub=A_ub,b_ub=b_ub,A_eq=Aeq2,b_eq=beq,bounds=bounds,method="highs",options={"presolve":True})
  gate("default_parent_stage2_feasible",lp2_default.success,[lp2_default.status,lp2_default.message])
  zd=np.asarray(lp2_default.x,dtype=np.float64);xd=zd[:nedge]
  cv_check_default=np.bincount(edge_cv,weights=xd,minlength=NCVT).reshape(NSL,NCV)
  default_parent_cv_err=float(np.max(np.abs(cv_check_default-new_cv_mass)))
  parent_cv_equality_detail=repr(default_parent_cv_err)
  gate("lost_parent_CV_equality_failure_reproduced",default_parent_cv_err>MASS_TOL,[default_parent_cv_err,MASS_TOL])

  # Narrow technical repair only: tighten solver feasibility. Science gate unchanged.
  lp2=linprog(c2,A_ub=A_ub,b_ub=b_ub,A_eq=Aeq2,b_eq=beq,bounds=bounds,method="highs",options={"presolve":True,"primal_feasibility_tolerance":HIGHS_PRIMAL_FEASIBILITY_TOL,"dual_feasibility_tolerance":HIGHS_DUAL_FEASIBILITY_TOL,"ipm_optimality_tolerance":HIGHS_IPM_OPTIMALITY_TOL})
  gate("stage2_cell_L1_feasible",lp2.success,[lp2.status,lp2.message])

  z=np.asarray(lp2.x,dtype=np.float64);x=z[:nedge];d=z[nedge:]
  halo2=float(np.sum(x[shell>0]))
  cell_rep=np.bincount(edge_cell,weights=x,minlength=NCELL).reshape(GRID)
  candidate=cell_rep+residual_parent
  cv_check=np.bincount(edge_cv,weights=x,minlength=NCVT).reshape(NSL,NCV)
  cv_err=float(np.max(np.abs(cv_check-new_cv_mass)))
  cap_excess=float(np.max(candidate-cart_capacity))
  min_rep=float(np.min(cell_rep))
  split_err=float(np.max(np.abs(candidate-cell_rep-residual_parent)))
  L1_exact=float(np.sum(np.abs(cell_rep-direct_target_rep)))
  d_err=float(np.max(np.abs(d-np.abs(cell_rep.reshape(-1)-t))))

  injected=float(np.sum(theory_flux[:,0])*DT);produced=float(np.sum(theory_flux[:,-1])*DT)
  expected_total=float(np.sum(grid_parent))+injected-produced
  source_sink_residual=float(np.sum(candidate))-expected_total
  global_tol=max(MASS_TOL,REL_TOL*max(abs(expected_total),1.0))

  candidate_sg=np.asarray(a2e.invert_local_mass(r2src,candidate,pressure,p_ref,hetero_pv),dtype=np.float64)
  candidate_sat=float(a2e.BACKGROUND)+candidate_sg
  reconstructed=np.asarray(a2e.local_mass(r2src,candidate_sat,pressure,p_ref,hetero_pv),dtype=np.float64)
  recon_err=float(np.max(np.abs(reconstructed-candidate)))

  stage="comprehensive_design_gates"
  gate("stage2_halo_optimum_preserved",abs(halo2-halo_opt)<=2*HALO_OPT_TOL,[halo2,halo_opt])
  gate("stage2_reported_L1_exact",abs(float(lp2.fun)-L1_exact)<=max(1e-5,1e-10*max(L1_exact,1.0)),[lp2.fun,L1_exact])
  gate("stage2_abs_auxiliary_exact",d_err<=1e-5,d_err)
  gate("CV_mass_equalities",cv_err<=MASS_TOL,cv_err)
  gate("represented_nonnegative",min_rep>=-MASS_TOL,min_rep)
  gate("heterogeneous_cartesian_capacity",cap_excess<=1e-8,cap_excess)
  gate("split_identity",split_err<=MASS_TOL,split_err)
  gate("source_sink_closure",abs(source_sink_residual)<=global_tol,[source_sink_residual,global_tol])
  gate("cartesian_EOS_reconstruction",recon_err<=1e-8,recon_err)
  gate("candidate_saturation_bounds",float(np.min(candidate_sat))>=BACKGROUND-SAT_TOL and float(np.max(candidate_sat))<=MAX_SAT+SAT_TOL,
       [float(np.min(candidate_sat)),float(np.max(candidate_sat))])

  # This is the exact prospective design state to freeze for controlled execution.
  stage="design_publication"
  out.mkdir(parents=True,exist_ok=False)
  arrays={
   "XY1_edge_cv":edge_cv,"XY1_edge_cell":edge_cell,"XY1_edge_shell_cost":shell,
   "lexicographic_stage1_minimum_terminal_mass_kg":np.asarray(halo_opt),
   "lexicographic_stage2_edge_allocation_kg":x,
   "lexicographic_stage2_represented_candidate_kg":cell_rep,
   "lexicographic_stage2_candidate_grid_mass_kg":candidate,
   "lexicographic_stage2_candidate_saturation":candidate_sat,
   "theory_transport_new_CV_mass_kg":new_cv_mass,
   "theory_transport_new_CV_saturation":new_cv_sat,
   "theory_face_mass_flux_kg_day":theory_flux,
   "direct_delta_represented_target_kg":direct_target_rep,
   "residual_parent_frozen_kg":residual_parent,
  }
  design_npz=f"{OUT_TOKEN}_Frozen_Prospective_TheoryFlux_XY1_Candidate.npz"
  (out/design_npz).write_bytes(npzb(arrays))
  design_sha=sha(out/design_npz)

  summary={"milestone":M,"name":NAME,"status":PASS,
   "classification":"LOST_BLOCK_ARTIFACT_RECOVERY_TIGHT_HIGHS_CV_EQUALITY_THEORY_PREFERRED_SG7A_UD_REFERENCE_DENSITY_PLUS_XY1_TERMINAL_SUPPORT_LEXICOGRAPHIC_MAPBACK_DESIGN_FROZEN_FULL_PROPAGATION_CLOSED",
   "source_parent_BLOCK_artifact_present":False,
   "source_parent_BLOCK_artifact_recovery_method":"exact blocked-runner + authoritative-input default-solver failure reproduction",
   "reproduced_parent_CV_equality_max_abs_error_kg":default_parent_cv_err,
   "reproduced_parent_CV_equality_detail":parent_cv_equality_detail,
   "HiGHS_primal_feasibility_tolerance":HIGHS_PRIMAL_FEASIBILITY_TOL,
   "HiGHS_dual_feasibility_tolerance":HIGHS_DUAL_FEASIBILITY_TOL,
   "HiGHS_ipm_optimality_tolerance":HIGHS_IPM_OPTIMALITY_TOL,
   "source_support_audit_summary_sha256":mma[A_SUMMARY],
   "source_R25_state_sha256":R25_SHA,
   "nominal_dt_days":DT,"candidate_target_day":TARGET_DAY,
   "flux_law":"q * u_D(xi) * f(S) * rho_ref",
   "local_pressure_density_retained_for_storage":True,
   "terminal_support_topology":"XY1",
   "terminal_support_semantics":"same-layer X/Y face-neighbor Cartesian occupancy sinks only; never transport CVs or transit nodes",
   "stage1_minimum_terminal_mass_kg":halo_opt,
   "stage2_terminal_mass_kg":halo2,
   "stage2_cell_L1_deviation_from_direct_delta_target_kg":L1_exact,
   "stage2_used_terminal_edge_count":int(np.count_nonzero((shell>0)&(x>MASS_TOL))),
   "CV_equality_max_abs_error_kg":cv_err,
   "minimum_represented_mass_kg":min_rep,
   "cartesian_max_capacity_excess_kg":cap_excess,
   "cartesian_source_sink_residual_kg":source_sink_residual,
   "cartesian_mass_reconstruction_max_abs_error_kg":recon_err,
   "candidate_saturation_min":float(np.min(candidate_sat)),
   "candidate_saturation_max":float(np.max(candidate_sat)),
   "frozen_prospective_candidate_sha256":design_sha,
   "state_mutation_executed":False,"support_growth_executed":False,
   "physical_time_advance_executed":False,"R30_authorized":False,"P3_authorized":False}

  protocol={"milestone":M,"status":PASS,
   "repair_scope":{
    "transport_flux_law":{
     "old":"q * u_D * f(S) * rho_local",
     "new":"q * u_D * f(S) * rho_ref",
     "reason":"avoid double compressibility accounting in face component flux; local density remains storage authority"},
    "mapback":{
     "support":"exact R22 CV-cell support plus one same-layer X/Y face-neighbor shell",
     "terminal_cells":"occupancy sinks only; not CVs, not transit, no pressure/TOF retrace",
     "residual_sidecar":"bitwise/floating-value unchanged from accepted R25-R3 parent",
     "stage1":"minimize total represented mass assigned to XY1 terminal edges subject to exact transported CV mass and heterogeneous Cartesian represented capacity",
     "stage2":"hold Stage1 terminal-mass optimum within 1e-6 kg and minimize cell-level L1 deviation from represented_parent + direct physical subsegment delta",
     "absolute_reprojection_required":True,
     "direct_delta_mapback_forbidden":True},
    "unchanged":{
     "nominal_dt_days":DT,"inlet_component_mass_flux":True,"pressure_epoch":True,"R22_TOF_geometry":True,
     "CV_storage_density_model":True,"Cartesian_storage_density_model":True,"residual_sidecar":True}},
   "prospective_candidate_sha256":design_sha,
   "full_propagation_closed":True}

  decision={"milestone":M,"status":PASS,"classification":summary["classification"],
   "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R3_authorized":True,
   "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R3_name":"Controlled Theory-Flux + XY1 Terminal-Support Mapback Candidate Execution — No Time Commit",
   "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R3_execution_authorized":True,
   "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R3_candidate_only":True,
   "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R3_must_bind_frozen_candidate_SHA":design_sha,
   "flux_law_change_authorized_for_R3":True,
   "authorized_flux_law":"SG7A_uD_reference_density",
   "XY1_terminal_support_growth_authorized_for_R3":True,
   "absolute_represented_state_reprojection_authorized_for_R3":True,
   "direct_delta_mapback_authorized":False,
   "support_beyond_XY1_authorized":False,
   "residual_sidecar_mutation_authorized":False,
   "nominal_dt_change_authorized":False,"inlet_component_flux_change_authorized":False,
   "pressure_refresh_authorized":False,"TOF_retrace_authorized":False,
   "storage_density_model_change_authorized":False,"CV_capacity_model_change_authorized":False,
   "physical_time_advance_authorized":False,"automatic_rerun_authorized":False,
   "R30_authorized":False,"P3_authorized":False}

  (out/f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
  (out/f"{OUT_TOKEN}_Comprehensive_Repair_Protocol.json").write_bytes(jb(protocol))
  (out/f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
  (out/f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))
  rows=[]
  for p in sorted(out.iterdir()):
   if p.is_file():rows.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
  (out/f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

  print("="*200)
  print(M,"PASS")
  print("Classification                         :",summary["classification"])
  print("Flux law                              : SG7A u_D * f(S) * rho_ref")
  print("Terminal support                      : XY1")
  print("Stage1 minimum terminal mass kg       :",halo_opt)
  print("Stage2 terminal mass kg               :",halo2)
  print("Stage2 Cartesian L1 deviation kg      :",L1_exact)
  print("Used terminal edges                   :",summary["stage2_used_terminal_edge_count"])
  print("CV equality max error kg              :",cv_err)
  print("Cartesian max capacity excess kg      :",cap_excess)
  print("Cartesian source/sink residual kg     :",source_sink_residual)
  print("Candidate saturation min/max          :",summary["candidate_saturation_min"],"/",summary["candidate_saturation_max"])
  print("Frozen prospective candidate SHA256   :",design_sha)
  print("R29-R3-...-R3 execution authorized    : True")
  print("Physical time / R30                   : False / False")
  print("="*200)
  return 0

 except Exception as exc:
  block.mkdir(parents=True,exist_ok=True);p=block/f"{OUT_TOKEN}_Blocked_Report.json"
  if not p.exists():p.write_bytes(jb({"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),
    "lost_parent_BLOCK_not_recreated":True,"prior_scientific_results_preserved":True,"state_mutation_executed":False,"support_growth_executed":False,
    "physical_time_advance_executed":False,"R30_authorized":False,"P3_authorized":False,"gates_completed":gates}))
  print(M,"TECHNICAL / AUTHORITY BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--project-root",type=Path,default=Path("."));ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"));ap.add_argument("--self-test",action="store_true");a=ap.parse_args()
 if a.self_test:selftest();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
