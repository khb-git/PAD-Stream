#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,io,json,subprocess,sys,zipfile
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-P2-R6-R29-R3-R2-R1"
NAME="Compressibility-Accounting Flux-Law Alternatives + Full Propagation Audit"
PASS="AV4PIVOTP2R6R29R3R2R1_COMPRESSIBILITY_ACCOUNTING_FLUX_LAW_ALTERNATIVES_AND_FULL_PROPAGATION_AUDIT_PASS_NO_STATE_MUTATION"
BLOCK="AV4PIVOTP2R6R29R3R2R1_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="486e8506778e0f8cb7252e4f1b3dec38f563f14d"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3=Path("post_v16")/RID/"POSTV16_AV3_Corey_Relperm_Heterogeneity"
GRID=(15,50,50);NSL=1078;NN=201;NCV=200
DAY_TO_S=86400.0;DT=0.03721673128859954;TARGET=375.0372167312886
BACKGROUND=0.20;MAX_SAT=0.80;MAX_SG=0.60
RHO_REF=700.0;MASS_TOL=1e-6;SAT_TOL=1e-10;REL_TOL=1e-10

R2_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_Capacity_Constrained_FaceFlux_Repair_Feasibility_and_Comprehensive_Design_Freeze"
R2_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_Summary.json"
R2_DECISION="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_Decision_Contract.json"
R2_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_Artifact_Manifest.csv"
R2_STATUS="AV4PIVOTP2R6R29R3R2_CAPACITY_CONSTRAINED_FACE_FLUX_REPAIR_FEASIBILITY_AND_COMPREHENSIVE_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
R2_CLASSIFICATION="CAPACITY_CONSTRAINED_FACE_FLUX_PROJECTION_INFEASIBLE_AT_NOMINAL_DT_UNDER_FIXED_INLET_AND_PHYSICAL_FACE_FLUX_ENVELOPE"

R1_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R29_R3_R1_CV_Capacity_Localization_and_Full_Downstream_Propagation_Audit"
R1_ARRAYS="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R1_Full_CV_Capacity_and_Propagation_Audit.npz"
R1_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R1_Artifact_Manifest.csv"

R25_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R25_R3_Controlled_Day375_CapacityLimited_ExactSupport_SplitState_Reprojection_Execution_Stage2_PresolveOff"
R25_STATE="POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
R25_SHA="9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

A6E_REL=BASE_AV3/"POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE="POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_SHA="f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

R2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_Capacity_Constrained_FaceFlux_Repair_Feasibility_and_Comprehensive_Design_Freeze.py"
R2_RUNNER_BLOB="d0483553706fcf9197cba0e706b7015fd7bdd354"
E37A="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
R2SRC="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
A2E="PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB="79a8969233b72b4543edd382a0c3d1028c6dca09"
SG7D="PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py";SG7D_BLOB="890088c0c0fcab415a2c7351c5079ca8ee12bf82"
SG7A="PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py";SG7A_BLOB="a4dd47338e7a85f130a6a70d0a41211e38c655f8"
E36="PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py";E36_BLOB="9ab4035c95a25bd61c649f86c82d88f059cef9e2"

SOURCE_BLOBS={R2_RUNNER:R2_RUNNER_BLOB,E37A:E37A_BLOB,R2SRC:R2SRC_BLOB,A2E:A2E_BLOB,SG7D:SG7D_BLOB,SG7A:SG7A_BLOB,E36:E36_BLOB}

OUT_TOKEN="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1"
OUT_REL=BASE/(OUT_TOKEN+"_Compressibility_Accounting_FluxLaw_Alternatives_and_Full_Propagation_Audit")
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
 q=2.;u=1.1;f=.5;rho=650.
 assert np.isclose(q*u*f*rho,715.0)
 assert np.isclose(q*u*f*RHO_REF,770.0)
 assert np.isclose(q*f*RHO_REF,700.0)
 print("POSTV16 AV4 PIVOT P2-R6-R29-R3-R2-R1 structural self-test: PASS")

def main(project_root,drive_root):
 root=project_root.resolve();drive=drive_root.resolve();out=drive/OUT_REL;block=drive/BLOCK_REL;stage="preflight";gates=[]
 def gate(n,c,d=None):
  ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
  print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"))
  if not ok:raise GateError(n)
 try:
  stage="preexisting_state_firewall"
  gate("no_preexisting_PASS",not (out/f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
  gate("no_preexisting_BLOCK",not (block/f"{OUT_TOKEN}_Blocked_Report.json").exists())

  stage="repository_authority"
  gate("branch_exact",gt(root,"branch","--show-current")==BRANCH)
  gate("parent_exact",gt(root,"rev-parse","HEAD^")==PARENT)
  gate("repository_clean",gt(root,"status","--porcelain")=="")
  for fn,ex in SOURCE_BLOBS.items():
   p=root/fn;gate(f"{Path(fn).stem}_present",p.is_file(),str(p))
   actual=gt(root,"hash-object",str(p)) if p.is_file() else "missing";gate(f"{Path(fn).stem}_blob_exact",actual==ex,actual)

  stage="R29R3R2_authority"
  r2dir=drive/R2_REL;mm2=manifest(r2dir,R2_MANIFEST);s2=js(r2dir/R2_SUMMARY);d2=js(r2dir/R2_DECISION)
  gate("R2_status_exact",s2.get("status")==R2_STATUS,s2.get("status"))
  gate("R2_classification_exact",s2.get("classification")==R2_CLASSIFICATION,s2.get("classification"))
  gate("R2_flux_projection_infeasible",s2.get("face_flux_projection_feasible") is False)
  gate("R2_infeasible_count_matches_R1",int(s2.get("face_flux_infeasible_CV_count"))==1305)
  gate("R2_execution_not_authorized",d2.get("P2_R6_R29_R3_R3_execution_authorized") is False)
  gate("R2_no_dt_change",d2.get("nominal_dt_change_authorized") is False)
  gate("R2_no_time",d2.get("physical_time_advance_authorized") is False)

  stage="R1_arrays_authority"
  r1dir=drive/R1_REL;mm1=manifest(r1dir,R1_MANIFEST)
  gate("R1_arrays_manifested",R1_ARRAYS in mm1)
  with np.load(r1dir/R1_ARRAYS,allow_pickle=False) as z:
   old_mass=np.asarray(z["old_CV_mass_kg"],dtype=np.float64)
   old_sat=np.asarray(z["old_CV_saturation"],dtype=np.float64)
   cv_capacity=np.asarray(z["CV_capacity_kg"],dtype=np.float64)
   baseline_flux=np.asarray(z["face_mass_flux_kg_day"],dtype=np.float64)

  stage="accepted_parent_geometry"
  r25=drive/R25_REL;m25=manifest(r25,R25_MANIFEST);sp=r25/R25_STATE
  gate("R25_state_SHA",m25.get(R25_STATE)==R25_SHA and sha(sp)==R25_SHA)
  with np.load(sp,allow_pickle=False) as z:
   grid_parent=np.asarray(z["cartesian_component_mass_kg"],dtype=np.float64)
   represented_parent=np.asarray(z["represented_cartesian_cell_mass_kg"],dtype=np.float64)
   residual_parent=np.asarray(z["grid_residual_component_mass_kg"],dtype=np.float64)
   xyz=np.asarray(z["streamline_xyz_m"],dtype=np.float64)
   tof_s=np.asarray(z["streamline_tof_s"],dtype=np.float64)
   weights_m3_s=np.asarray(z["streamline_weight_m3_s"],dtype=np.float64)
   producer_labels=np.asarray(z["producer_labels"]).astype("U32")
   streamline_id=np.asarray(z["streamline_id"],dtype=np.int64)
   pressure_psi=np.asarray(z["refreshed_pressure_psi"],dtype=np.float64)
   p_ref=float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

  e37a=load_module(root/E37A,"fluxaudit_e37a");r2=load_module(root/R2SRC,"fluxaudit_r2");a2e=load_module(root/A2E,"fluxaudit_a2e")
  sg7d=load_module(root/SG7D,"fluxaudit_sg7d");sg7a=load_module(root/SG7A,"fluxaudit_sg7a");e36=load_module(root/E36,"fluxaudit_e36")
  a6=drive/A6E_REL/A6E_STATE;gate("A6E_SHA",a6.is_file() and sha(a6)==A6E_SHA)
  with np.load(a6,allow_pickle=False) as z:phi=np.asarray(z["paired_porosity"],dtype=np.float64)
  hetero_pv=phi*float(a2e.BULK_VOLUME_M3)
  op=sg7d.build_subsegment_operator(xyz,tof_s/DAY_TO_S,weights_m3_s*DAY_TO_S)
  geometry=e37a.build_control_volume_geometry(r2,op,pressure_psi,p_ref,NSL,NCV)
  face_pressure=e37a.build_face_pressure(e36,sg7d,xyz,pressure_psi)
  xi=np.linspace(0.,1.,NCV+1);u=np.asarray(sg7a.u_dimensionless(xi),dtype=np.float64);q=weights_m3_s*DAY_TO_S

  # Compressibility-accounting diagnosis at fully saturated faces.
  stage="compressibility_accounting_diagnosis"
  satmax=np.full((NSL,NCV),float(sg7a.S_INJECTED))
  rho_max=np.asarray(r2.gas_density_from_state(satmax,face_pressure[:,1:],p_ref),dtype=np.float64)
  u_pressure_consistent=RHO_REF/rho_max
  saturated_existing_ratio=u[None,1:]*rho_max/RHO_REF
  ratio_diff=np.diff(saturated_existing_ratio,axis=1)
  decreasing_existing_count=int(np.count_nonzero(ratio_diff<0.0))
  max_abs_log_u_mismatch=float(np.max(np.abs(np.log(np.maximum(u[None,1:],1e-30)/np.maximum(u_pressure_consistent,1e-30)))))
  existing_ratio_min=float(np.min(saturated_existing_ratio));existing_ratio_max=float(np.max(saturated_existing_ratio))

  # Candidate flux laws.
  donor=old_sat[:,:-1]
  ff=np.asarray(sg7a.fractional_flow(donor),dtype=np.float64)
  rho=np.asarray(r2.gas_density_from_state(donor,face_pressure[:,1:-1],p_ref),dtype=np.float64)
  out_sat=old_sat[:,-1]
  out_ff=np.asarray(sg7a.fractional_flow(out_sat),dtype=np.float64)
  out_rho=np.asarray(r2.gas_density_from_state(out_sat,face_pressure[:,-1],p_ref),dtype=np.float64)

  fluxes={}
  fluxes["existing_E37A_double_compressibility"]=baseline_flux.copy()

  f=np.zeros_like(baseline_flux);f[:,0]=q*RHO_REF
  f[:,1:-1]=q[:,None]*ff*rho
  f[:,-1]=q*out_ff*out_rho
  fluxes["pressure_density_only"]=f

  f=np.zeros_like(baseline_flux);f[:,0]=q*RHO_REF
  f[:,1:-1]=q[:,None]*u[None,1:-1]*ff*RHO_REF
  f[:,-1]=q*float(u[-1])*out_ff*RHO_REF
  fluxes["SG7A_uD_reference_density"]=f

  f=np.zeros_like(baseline_flux);f[:,0]=q*RHO_REF
  f[:,1:-1]=q[:,None]*ff*RHO_REF
  f[:,-1]=q*out_ff*RHO_REF
  fluxes["source_mass_normalized"]=f

  def downstream_for(flux):
   new_mass=old_mass+DT*(flux[:,:-1]-flux[:,1:])
   min_mass=float(np.min(new_mass));excess=float(np.max(new_mass-cv_capacity))
   tol=max(1e-6,1e-10*max(float(np.sum(old_mass)),1.0))
   ctol=max(1e-9,1e-12*max(float(np.max(np.abs(new_mass))),1.0))
   injected=float(np.sum(flux[:,0])*DT);produced=float(np.sum(flux[:,-1])*DT)
   delta=float(np.sum(new_mass)-np.sum(old_mass));residual=delta-injected+produced
   result={"CV_nonnegative_pass":min_mass>=-tol,"CV_capacity_pass":excess<=ctol,
           "CV_source_sink_closure_pass":abs(residual)<=tol,"CV_inversion_pass":False,
           "CV_to_subsegment_closure_pass":False,"subsegment_to_grid_closure_pass":False,
           "represented_nonnegative_pass":False,"split_identity_pass":False,
           "heterogeneous_cartesian_capacity_pass":False,"heterogeneous_cartesian_inversion_pass":False,
           "cartesian_source_sink_closure_pass":False,"all_downstream_checks_pass":False,
           "CV_min_mass_kg":min_mass,"CV_max_capacity_excess_kg":excess,
           "CV_capacity_violation_count":int(np.count_nonzero(new_mass-cv_capacity>ctol)),
           "injected_mass_kg":injected,"produced_mass_kg":produced,"CV_delta_kg":delta,
           "CV_source_sink_residual_kg":residual,"exception":None}
   arrays={"new_CV_mass_kg":new_mass}
   if not (result["CV_nonnegative_pass"] and result["CV_capacity_pass"] and result["CV_source_sink_closure_pass"]):
    return result,arrays
   try:
    sat=np.asarray(e37a.invert_cv_mass_to_saturation(r2,new_mass,np.asarray(geometry["cv_pressure_mass_coeff"],dtype=np.float64)),dtype=np.float64)
    result["CV_inversion_pass"]=True
    cv_id=np.asarray(geometry["cv_id"],dtype=np.int64);flat=np.asarray(geometry["flat_cell"],dtype=np.int64)
    pv=np.asarray(geometry["pv_m3"],dtype=np.float64);pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64)
    os=old_sat.reshape(-1)[cv_id];ns=sat.reshape(-1)[cv_id]
    osg=np.clip(os-BACKGROUND,0.,MAX_SG);nsg=np.clip(ns-BACKGROUND,0.,MAX_SG)
    ro=np.asarray(r2.gas_density_from_state(os,pseg,p_ref),dtype=np.float64);rn=np.asarray(r2.gas_density_from_state(ns,pseg,p_ref),dtype=np.float64)
    sub=pv*(rn*nsg-ro*osg);subsum=float(np.sum(sub));tr=subsum-delta
    gtol=max(MASS_TOL,REL_TOL*max(abs(delta),float(np.sum(grid_parent)),1.0))
    result["CV_to_subsegment_closure_pass"]=abs(tr)<=gtol
    dg=np.bincount(flat,weights=sub,minlength=int(np.prod(GRID))).reshape(GRID);dr=float(np.sum(dg)-subsum)
    result["subsegment_to_grid_closure_pass"]=abs(dr)<=gtol
    rep=represented_parent+dg;resid=residual_parent.copy();cand=grid_parent+dg
    minrep=float(np.min(rep));split=float(np.max(np.abs(cand-rep-resid)))
    result["represented_nonnegative_pass"]=minrep>=-MASS_TOL;result["split_identity_pass"]=split<=MASS_TOL
    full=np.full(GRID,float(a2e.INJECTED));cc=np.asarray(a2e.local_mass(r2,full,pressure_psi,p_ref,hetero_pv),dtype=np.float64)
    cctol=max(1e-8,1e-12*max(float(np.max(cc)),1.0));ce=float(np.max(cand-cc))
    result["heterogeneous_cartesian_capacity_pass"]=ce<=cctol
    cs=None;cerr=None
    if result["heterogeneous_cartesian_capacity_pass"]:
     csg=np.asarray(a2e.invert_local_mass(r2,cand,pressure_psi,p_ref,hetero_pv),dtype=np.float64);cs=float(a2e.BACKGROUND)+csg
     recon=np.asarray(a2e.local_mass(r2,cs,pressure_psi,p_ref,hetero_pv),dtype=np.float64);cerr=float(np.max(np.abs(recon-cand)))
     result["heterogeneous_cartesian_inversion_pass"]=cerr<=1e-8 and float(np.min(cs))>=BACKGROUND-SAT_TOL and float(np.max(cs))<=MAX_SAT+SAT_TOL
    target=float(np.sum(grid_parent))+injected-produced;ct=float(np.sum(cand));csr=ct-target
    result["cartesian_source_sink_closure_pass"]=abs(csr)<=gtol
    result.update({"CV_to_subsegment_residual_kg":tr,"subsegment_to_grid_residual_kg":dr,
                   "minimum_represented_candidate_mass_kg":minrep,"split_identity_max_abs_error_kg":split,
                   "cartesian_max_capacity_excess_kg":ce,"cartesian_capacity_tolerance_kg":cctol,
                   "cartesian_cellwise_mass_reconstruction_error_kg":cerr,"cartesian_source_sink_residual_kg":csr,
                   "candidate_saturation_min":float(np.min(cs)) if cs is not None else None,
                   "candidate_saturation_max":float(np.max(cs)) if cs is not None else None})
    req=("CV_nonnegative_pass","CV_capacity_pass","CV_source_sink_closure_pass","CV_inversion_pass",
         "CV_to_subsegment_closure_pass","subsegment_to_grid_closure_pass","represented_nonnegative_pass",
         "split_identity_pass","heterogeneous_cartesian_capacity_pass","heterogeneous_cartesian_inversion_pass",
         "cartesian_source_sink_closure_pass")
    result["all_downstream_checks_pass"]=all(bool(result[k]) for k in req)
    arrays.update({"new_CV_saturation":sat,"delta_grid_mass_kg":dg,"candidate_grid_mass_kg":cand})
   except Exception as exc:
    result["exception"]=repr(exc)
   return result,arrays

  stage="flux_law_full_propagation_audit"
  results={};all_arrays={}
  for name,flux in fluxes.items():
   r,a=downstream_for(flux);results[name]=r;all_arrays[name+"_face_mass_flux_kg_day"]=flux
   for k,v in a.items():all_arrays[name+"_"+k]=v

  passing=[n for n,r in results.items() if r["all_downstream_checks_pass"]]
  theory_preferred="SG7A_uD_reference_density"
  preferred_pass=theory_preferred in passing
  if preferred_pass:
   classification="SG7A_UD_REFERENCE_DENSITY_FLUX_REMOVES_LOCAL_DENSITY_DOUBLE_COUNT_AND_PASSES_FULL_PROPAGATION"
  elif passing:
   classification="ALTERNATIVE_FLUX_LAW_PASSES_FULL_PROPAGATION_BUT_THEORY_PREFERRED_SG7A_REFERENCE_DENSITY_DOES_NOT"
  else:
   classification="NO_TESTED_COMPRESSIBILITY_ACCOUNTING_FLUX_LAW_PASSES_FULL_PROPAGATION"

  stage="publication"
  out.mkdir(parents=True,exist_ok=False)
  diag={"u_sg7a":u[1:],"u_pressure_consistent_full_sat":u_pressure_consistent,
        "existing_saturated_mass_flux_ratio_to_source":saturated_existing_ratio,
        "existing_saturated_ratio_downstream_difference":ratio_diff}
  diag.update(all_arrays)
  (out/f"{OUT_TOKEN}_FluxLaw_Alternative_Propagation_Arrays.npz").write_bytes(npzb(diag))

  rows=[]
  for n,r in results.items():
   row={"flux_law":n}
   row.update({k:v for k,v in r.items() if not isinstance(v,(dict,list))})
   rows.append(row)
  (out/f"{OUT_TOKEN}_FluxLaw_Comparison.csv").write_bytes(csvb(rows))

  summary={"milestone":M,"name":NAME,"status":PASS,"classification":classification,
           "source_R29R3R2_summary_sha256":mm2[R2_SUMMARY],
           "nominal_dt_days":DT,"candidate_target_day":TARGET,
           "existing_saturated_mass_flux_ratio_min":existing_ratio_min,
           "existing_saturated_mass_flux_ratio_max":existing_ratio_max,
           "existing_saturated_capacity_decreasing_face_pair_count":decreasing_existing_count,
           "max_abs_log_ratio_SG7A_u_to_pressure_consistent_u":max_abs_log_u_mismatch,
           "tested_flux_laws":list(results.keys()),"full_propagation_passing_flux_laws":passing,
           "theory_preferred_flux_law":theory_preferred,"theory_preferred_flux_law_passes":preferred_pass,
           "results":results,"state_mutation_executed":False,"physical_time_advance_executed":False,
           "R30_authorized":False,"P3_authorized":False}

  audit={"milestone":M,"status":PASS,
         "question":"Is R29-R3 failure caused by inconsistent/double compressibility accounting in component face flux?",
         "existing_flux":"q * u_D(xi) * f(S) * rho_local(S,p_face)",
         "alternative_pressure_density_only":"q * f(S) * rho_local(S,p_face)",
         "alternative_SG7A_uD_reference_density":"q * u_D(xi) * f(S) * rho_ref",
         "alternative_source_mass_normalized":"q * f(S) * rho_ref",
         "theory_note":"SG7A governing equation already places compressibility in u_D(xi); multiplying by local pressure-dependent density in the face flux adds a second compressibility factor. Local density remains authoritative for stored component mass/capacity.",
         "diagnostics":{"existing_saturated_mass_flux_ratio_to_source_min":existing_ratio_min,
                        "existing_saturated_mass_flux_ratio_to_source_max":existing_ratio_max,
                        "existing_saturated_capacity_decreasing_face_pair_count":decreasing_existing_count,
                        "max_abs_log_ratio_SG7A_u_to_pressure_consistent_u":max_abs_log_u_mismatch},
         "full_propagation_results":results}

  decision={"milestone":M,"status":PASS,"classification":classification,
            "P2_R6_R29_R3_R2_R2_authorized":bool(preferred_pass),
            "P2_R6_R29_R3_R2_R2_name":"Comprehensive Transport Flux-Law Repair Design Freeze",
            "P2_R6_R29_R3_R2_R2_design_only":True,
            "P2_R6_R29_R3_R2_R2_execution_authorized":False,
            "preferred_repair_flux_law":theory_preferred if preferred_pass else None,
            "preferred_repair_requires_removing_local_density_from_face_flux":bool(preferred_pass),
            "storage_density_model_change_authorized":False,
            "CV_capacity_model_change_authorized":False,
            "subsegment_delta_formula_change_authorized":False,
            "Cartesian_mapback_formula_change_authorized":False,
            "nominal_dt_change_authorized":False,"inlet_component_flux_change_authorized":False,
            "state_mutation_authorized":False,"physical_time_advance_authorized":False,
            "R30_authorized":False,"P3_authorized":False}

  (out/f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
  (out/f"{OUT_TOKEN}_Compressibility_Accounting_Audit.json").write_bytes(jb(audit))
  (out/f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
  (out/f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))
  mrows=[]
  for p in sorted(out.iterdir()):
   if p.is_file():mrows.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
  (out/f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(mrows))

  print("="*190)
  print(M,"PASS")
  print("Classification                              :",classification)
  print("Existing saturated flux/source ratio min/max:",existing_ratio_min,"/",existing_ratio_max)
  print("Existing decreasing carrying-capacity pairs :",decreasing_existing_count)
  for n,r in results.items():
   print(f"{n:42s} CV violations={r['CV_capacity_violation_count']} full_downstream_PASS={r['all_downstream_checks_pass']}")
  print("Full-propagation passing laws               :",passing)
  print("Theory-preferred SG7A uD + rho_ref PASS     :",preferred_pass)
  print("R29-R3-R2-R2 design freeze authorized       :",preferred_pass)
  print("State / time / R30                          : False / False / False")
  print("="*190)
  return 0

 except Exception as exc:
  block.mkdir(parents=True,exist_ok=True);p=block/f"{OUT_TOKEN}_Blocked_Report.json"
  if not p.exists():p.write_bytes(jb({"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),
   "R29R3R2_design_preserved":True,"state_mutation_executed":False,"physical_time_advance_executed":False,
   "R30_authorized":False,"P3_authorized":False,"gates_completed":gates}))
  print(M,"TECHNICAL / AUTHORITY BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--project-root",type=Path,default=Path("."));ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"));ap.add_argument("--self-test",action="store_true");a=ap.parse_args()
 if a.self_test:selftest();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
