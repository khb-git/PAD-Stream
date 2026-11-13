#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G2-R2"
PASS="POSTV16AV4PIVOTGPUHYBG2R2_RANK2_DAY120_DAY125_EXACT_FLOW_AND_READONLY_HYBRID_ENDPOINT_DIAGNOSTIC_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG2R2_TECHNICAL_OR_SAFETY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="b158548eb7db5d8dae0e615a7bc44538497e2b17"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G2R1R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_80_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2R1R1_BLOB="04c3940a7c736b1d210376113e48bab6111fc173"
G2R1R1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_Day80_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
G2R1R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Summary.json"
G2R1R1_STATUS="POSTV16AV4PIVOTGPUHYBG2R1R1_RANK1_DAY75_DAY80_EXACT_FLOW_AND_READONLY_HYBRID_ENDPOINT_DIAGNOSTIC_PASS"

E42_RUNNER="PAD_Stream_V16E42_Repaired_Production_Continuation_to_Exact_150Day_Observation.py"
E42_BLOB="7efe0cb943b40e976b7364241dc7f41dc819a2df"
E42_REL=Path("provenance/hybrid_dp/V16E42_REPAIRED_PRODUCTION_EXACT_150D_OBSERVATION")
E42_SUMMARY="PAD_Stream_V16E42_Summary.json"
E42_CLOSURE="V16E42_Final_Closure.json"
E42_STATUS="REPAIRED_PRODUCTION_EXACT_150D_OBSERVATION_VALIDATED"

R3R7_REL=Path("provenance/hybrid_dp/V16E41R3R7_REPAIRED_PRODUCTION_EXACT_100D_OBSERVATION")
R3R7_RESTART="V16E41R3R7_Authoritative_100d_PostObservation_Refreshed_Restart.npz"
DAY100_SHA="0772e6c067d36c20037ff448e2b1ebc7e11c53ef8e05642264583c56bb18a770"
DAY100_STEP=4640

A0_STATUS="POSTV16PCADA0_EXACT_PRESSURE_EVOLUTION_AND_FLOWEPOCH_HOLD_SCREENING_PASS_NO_PHYSICS_MUTATION"
PRIMARY_METRICS=[
 "pressure_relative_L2","flux_relative_L2","tau_end_relative_L2",
 "streamline_weight_relative_L2","producer_connectivity_mismatch_fraction",
 "path_RMS_displacement_ft",
]
TARGETS=[120.0,125.0]
FT_TO_M=0.3048
DAY_TO_S=86400.0
NUM_EPS=1.0e-12

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G2_R2"
OUT_REL=BASE_AV4/(OUT_TOKEN+"_Rank2_Day120_Day125_ExactFlow_and_Hybrid_Endpoint_Diagnostic")
BLOCK_REL=BASE_AV4/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
CADENCE=f"{OUT_TOKEN}_Day120_to_Day125_PCAD_Metrics.csv"
HYBRID=f"{OUT_TOKEN}_Hybrid_Endpoint_Metrics.csv"
ROUTES=f"{OUT_TOKEN}_Hybrid_Route_Counts.csv"
PRODUCERS=f"{OUT_TOKEN}_Hybrid_Producer_Outlet_Diagnostics.csv"
STEPS=f"{OUT_TOKEN}_Accepted_Transitions_100_to125.csv"
REFRESH=f"{OUT_TOKEN}_Flow_Refreshes_100_to125.csv"
CAPACITY=f"{OUT_TOKEN}_Capacity_Preflight_Events.csv"
CONTROLLER=f"{OUT_TOKEN}_Capacity_Controller_Adjustments.csv"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"
DAY120_STATE=f"{OUT_TOKEN}_Exact_Day120_State.npz"
DAY125_STATE=f"{OUT_TOKEN}_Exact_Day125_State.npz"
DAY120_DIAG=f"{OUT_TOKEN}_Day120_ExactFlow_and_Hybrid_Diagnostic.npz"
DAY125_DIAG=f"{OUT_TOKEN}_Day125_ExactFlow_and_Hybrid_Diagnostic.npz"

class GateError(RuntimeError): pass

def sha256(p:Path)->str:
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1<<20),b""): h.update(c)
 return h.hexdigest()

def gt(root:Path,*a)->str:
 return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()

def git_blob(p:Path,root:Path)->str:
 return gt(root,"hash-object",str(p))

def load_module_blob(path:Path,blob:str,name:str,root:Path):
 if not path.is_file(): raise GateError(f"missing_source:{path}")
 actual=git_blob(path,root)
 if actual!=blob: raise GateError(f"source_blob:{path.name}:{actual}:{blob}")
 spec=importlib.util.spec_from_file_location(name,path)
 if spec is None or spec.loader is None: raise GateError(f"cannot_import:{path}")
 mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod

def load_npz(path:Path):
 with np.load(path,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}

def js(p:Path): return json.loads(p.read_text(encoding="utf-8"))
def scalar(v): return float(np.asarray(v).reshape(()))
def int_scalar(v): return int(np.asarray(v).reshape(()))

def write_csv(path:Path,rows:list[dict[str,Any]]):
 if not rows:path.write_text("",encoding="utf-8");return
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields:fields.append(k)
 with path.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def rollout_100_to125(
 parent:dict[str,np.ndarray], *,
 e42,r3r5,r3r4r1,repair,physics,r3r2r1,e36,e37a,sg2,sg3,sg4,sg5,sg6,sg7a,sg7d,
 permeability_md:np.ndarray,cell_pore_volume_m3:float
):
 current={k:np.asarray(v).copy() for k,v in parent.items()}
 refresh_rows=[];step_rows=[];capacity_rows=[];controller_rows=[]
 accepted_dts=[];capacity_margins=[]
 epoch=None;epoch_start_time=None
 refresh_count=0;cadence_refresh_count=0;capacity_refresh_count=0
 capacity_adjustments_total=0;capacity_limited_accepted=0;force_refresh_next=False
 checkpoints={}
 target_final=125.0
 checkpoint_days=[120.0,125.0]

 def do_refresh(trigger:str):
  nonlocal current,epoch,epoch_start_time,refresh_count,cadence_refresh_count,capacity_refresh_count
  before_time=scalar(current["physical_time_days"]);before_step=int_scalar(current["accepted_step_index"])
  before_inj=scalar(current["cumulative_injected_co2_mass_kg"]);before_prod=scalar(current["cumulative_produced_co2_mass_kg"])
  before_stored=scalar(current["stored_co2_mass_current_kg"])
  refreshed,new_epoch,_=r3r5.build_flow_epoch(
   current=current,r3r4r1=r3r4r1,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
   sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
   permeability_md=permeability_md,cell_pore_volume_m3=cell_pore_volume_m3)
  if scalar(refreshed["physical_time_days"])!=before_time:raise GateError("refresh_advanced_time")
  if int_scalar(refreshed["accepted_step_index"])!=before_step:raise GateError("refresh_advanced_step")
  if scalar(refreshed["cumulative_injected_co2_mass_kg"])!=before_inj:raise GateError("refresh_changed_injection")
  if scalar(refreshed["cumulative_produced_co2_mass_kg"])!=before_prod:raise GateError("refresh_changed_production")
  mt=max(1e-6,1e-10*max(abs(before_stored),1.0))
  if abs(scalar(refreshed["stored_co2_mass_current_kg"])-before_stored)>mt:raise GateError("refresh_changed_stored_mass")
  current=refreshed;epoch=new_epoch;epoch_start_time=before_time;refresh_count+=1
  if trigger=="CADENCE":cadence_refresh_count+=1
  if trigger=="CAPACITY_PREFLIGHT_REJECTION":capacity_refresh_count+=1
  refresh_rows.append({
   "refresh_index":refresh_count,"trigger":trigger,"physical_time_days":before_time,"accepted_step_index":before_step,
   "fixed_point_iterations":new_epoch["fixed_point_iterations"],"CFL_dt_days":new_epoch["cfl_dt_days"],
   "streamline_count":new_epoch["nstream"],"capture_fraction":new_epoch["capture_fraction"],
   "flow_local_relative_residual":new_epoch["flow_local_residual"],"flow_global_relative_residual":new_epoch["flow_global_residual"],
   "pressure_rel_L2_vs_pre_refresh":new_epoch["refresh_pressure_rel_L2_vs_parent"],
   "saturation_Linf_vs_pre_refresh":new_epoch["refresh_saturation_Linf_vs_parent"],
   "refresh_global_mass_error_kg":new_epoch["refresh_global_mass_error_kg"],
  })

 do_refresh("RESTART_OR_INITIALIZATION")

 while scalar(current["physical_time_days"])<target_final-1e-13:
  now=scalar(current["physical_time_days"])
  if epoch is None or epoch_start_time is None:raise GateError("missing_active_flow_epoch")
  if force_refresh_next:
   do_refresh("POST_CAPACITY_LIMITED_ACCEPT");force_refresh_next=False;now=scalar(current["physical_time_days"])
  due=epoch_start_time+float(e42.MAX_FLOW_EPOCH_DAYS)
  if now>=due-1e-13:
   do_refresh("CADENCE");now=scalar(current["physical_time_days"]);due=epoch_start_time+float(e42.MAX_FLOW_EPOCH_DAYS)

  future=[d for d in checkpoint_days if d>now+1e-13]
  next_checkpoint=min(future) if future else target_final
  intended_target=min(target_final,next_checkpoint,due,now+float(epoch["cfl_dt_days"]))
  base_dt=intended_target-now
  if not np.isfinite(base_dt) or base_dt<=0:raise GateError(f"nonpositive_base_dt:{base_dt}")

  same_parent_capacity_refresh_done=False;capacity_adjustments_step=0;candidate_dt=float(base_dt)
  while True:
   parent_time=scalar(current["physical_time_days"]);parent_step=int_scalar(current["accepted_step_index"])
   parent_sat=np.asarray(current["transport_saturation"],dtype=np.float64)
   pressure=np.asarray(epoch["pressure_psi"],dtype=np.float64)
   p_ref=scalar(current["co2_density_reference_pressure_pa"]);parent_stored=scalar(current["stored_co2_mass_current_kg"])
   candidate_dt=min(candidate_dt,float(epoch["cfl_dt_days"]),intended_target-parent_time,target_final-parent_time)
   if candidate_dt<=0:raise GateError(f"nonpositive_candidate_dt:{candidate_dt}")

   recomputed=float(physics.stored_co2_mass_kg(parent_sat,pressure,p_ref,cell_pore_volume_m3))
   mt=max(1e-6,1e-10*max(abs(parent_stored),1.0))
   if abs(recomputed-parent_stored)>mt:raise GateError(f"parent_mass_pressure_mismatch:{recomputed-parent_stored}")

   old_cv_sat,old_cv_mass,sample_closure=e37a.sample_grid_inventory_to_control_volumes(
    physics,parent_sat,pressure,p_ref,epoch["geometry"],epoch["nstream"],epoch["ncv"])
   st=max(1e-6,1e-10*max(abs(float(np.sum(old_cv_mass))),1.0))
   if abs(sample_closure)>st:raise GateError(f"grid_to_CV_sampling_closure:{sample_closure}")

   transport=e37a.advance_component_mass_control_volumes(
    physics,sg7a,old_cv_sat,old_cv_mass,epoch["geometry"]["cv_pressure_mass_coeff"],
    epoch["face_pressure_psi"],p_ref,epoch["weights_m3_day"],epoch["xi_faces"],candidate_dt)
   injected=float(transport["injected_mass_kg"]);produced=float(transport["produced_mass_kg"])
   physical=e42.INJECTOR_MASS_RATE_KG_DAY*candidate_dt
   it=max(1e-6,1e-12*max(abs(physical),1.0))
   if abs(injected-physical)>it:raise GateError(f"fixed_rate_injection_mismatch:{injected-physical}")

   parent_mass=r3r4r1.parent_cellwise_component_mass(physics,parent_sat,pressure,p_ref,cell_pore_volume_m3)
   target_mass=parent_stored+injected-produced
   preflight=r3r4r1.preflight_mapback_capacity(
    physics=physics,parent_saturation=parent_sat,parent_mass=parent_mass,
    old_cv_saturation=old_cv_sat,new_cv_saturation=transport["new_saturation"],geometry=epoch["geometry"],
    pressure_psi=pressure,p_ref_gas_pa=p_ref,cell_pore_volume_m3=cell_pore_volume_m3)
   capacity_margins.append(float(preflight["minimum_capacity_margin_kg"]))

   if preflight["overcapacity_cell_count"]>0:
    capacity_rows.append({
     "physical_time_days":parent_time,"accepted_step_index":parent_step,"trial_dt_days":candidate_dt,
     "same_parent_refresh_done":same_parent_capacity_refresh_done,
     "overcapacity_cell_count":preflight["overcapacity_cell_count"],"max_capacity_excess_kg":preflight["max_capacity_excess_kg"],
     "minimum_capacity_margin_kg":preflight["minimum_capacity_margin_kg"]})
    if not same_parent_capacity_refresh_done:
     do_refresh("CAPACITY_PREFLIGHT_REJECTION");same_parent_capacity_refresh_done=True;continue
    ctl=repair.preflight_mapback_capacity(
     r2=physics,e37a=e37a,parent_grid_saturation=parent_sat,old_cv_saturation=old_cv_sat,
     new_cv_saturation=transport["new_saturation"],old_cv_mass=old_cv_mass,new_cv_mass=transport["new_mass"],
     geometry=epoch["geometry"],pressure_psi=pressure,p_ref_gas_pa=p_ref,
     cell_pore_volume_m3=cell_pore_volume_m3,target_final_mass_kg=target_mass,active_dt_days=candidate_dt)
    if ctl.get("native_failure_required"):raise GateError(f"capacity_controller_native_failure_required:{ctl.get('reason')}")
    if not ctl.get("controller_applicable"):raise GateError("capacity_controller_not_applicable")
    rec=float(ctl["recommended_dt_days"])
    if not np.isfinite(rec) or rec<=0 or rec>=candidate_dt:raise GateError(f"invalid_capacity_recommended_dt:{rec}:{candidate_dt}")
    capacity_adjustments_step+=1;capacity_adjustments_total+=1
    controller_rows.append({
     "physical_time_days":parent_time,"accepted_step_index":parent_step,"adjustment_index_this_step":capacity_adjustments_step,
     "candidate_dt_days":candidate_dt,"recommended_dt_days":rec,"raw_admissible_fraction":ctl["raw_admissible_fraction"],
     "max_capacity_excess_kg":ctl["max_capacity_excess_kg"],"limiting_cell_zero_based":str(ctl["upper_limiting_cell_zero_based"])})
    if capacity_adjustments_step>int(repair.MAX_CAPACITY_ADJUSTMENTS):raise GateError(f"capacity_adjustment_budget_exhausted:{parent_step+1}")
    candidate_dt=rec;continue

   mapping=e37a.map_control_volume_increment_to_grid(
    physics,parent_sat,old_cv_sat,transport["new_saturation"],old_cv_mass,transport["new_mass"],
    epoch["geometry"],pressure,p_ref,cell_pore_volume_m3,target_mass)
   capillary=physics.conservative_capillary_mass_redistribution(
    transport_saturation=np.asarray(mapping["corrected_saturation"],dtype=np.float64),
    permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,
    cell_pore_volume_m3=cell_pore_volume_m3,dt_seconds=candidate_dt*DAY_TO_S)
   child_sat=np.asarray(capillary["corrected"],dtype=np.float64);final_stored=float(capillary["final_mass_state_kg"])
   residual=final_stored-parent_stored-injected+produced
   ct=max(1e-6,1e-10*max(abs(target_mass),1.0))
   if abs(capillary["external_mass_change_kg"])>ct:raise GateError(f"capillary_external_mass_change:{capillary['external_mass_change_kg']}")
   if abs(residual)>ct:raise GateError(f"step_component_mass_closure:{residual}")

   _,cut=e37a.producer_rows_from_flux(
    epoch["labels"],epoch["weights_m3_day"],transport["outlet_fractional_flow"],
    transport["face_mass_flux_kg_day"][:,-1],candidate_dt)
   if not np.isfinite(cut) or not 0<=cut<=1:raise GateError(f"producer_gas_cut_invalid:{cut}")

   child=e36.make_child_state(current,child_sat,pressure,p_ref,candidate_dt,produced,cut,final_stored,residual,False)
   child["transport_face_count"]=np.asarray(epoch["nfaces"],dtype=np.int64)
   child["transport_control_volume_count"]=np.asarray(epoch["ncv"],dtype=np.int64)
   child["mass_conservative_flow_refresh_active"]=np.asarray(True,dtype=bool)
   child["runtime_refresh_policy_name_ascii"]=np.frombuffer(e42.PRODUCTION_POLICY.encode("ascii"),dtype=np.uint8)
   child["runtime_max_flow_epoch_days"]=np.asarray(e42.MAX_FLOW_EPOCH_DAYS,dtype=np.float64)
   child["V16E41R3R7_authoritative_post_observation_restart"]=np.asarray(False,dtype=bool)
   child["V16E42_rollout_active"]=np.asarray(True,dtype=bool)
   child["V16E42_canonical_150d_observation_state"]=np.asarray(False,dtype=bool)
   child["last_grid_mapback_ledger_residual_kg"]=np.asarray(mapping["ledger_residual_kg"],dtype=np.float64)
   child["last_capillary_external_mass_change_kg"]=np.asarray(capillary["external_mass_change_kg"],dtype=np.float64)

   accepted_time=scalar(child["physical_time_days"])
   for d in checkpoint_days:
    if abs(d-accepted_time)<=1e-13:
     child["physical_time_days"]=np.asarray(d,dtype=np.float64);accepted_time=d

   accepted_dts.append(candidate_dt)
   step_rows.append({
    "accepted_step_index":int_scalar(child["accepted_step_index"]),"parent_time_days":parent_time,
    "accepted_time_days":accepted_time,"accepted_dt_days":candidate_dt,
    "active_epoch_CFL_dt_days":epoch["cfl_dt_days"],"epoch_age_before_step_days":parent_time-epoch_start_time,
    "targeted_checkpoint_landing":accepted_time in checkpoint_days,
    "capacity_same_parent_refresh_used":same_parent_capacity_refresh_done,
    "capacity_controller_adjustments":capacity_adjustments_step,
    "raw_minimum_capacity_margin_kg":preflight["minimum_capacity_margin_kg"],
    "injected_CO2_mass_kg":injected,"produced_CO2_mass_kg":produced,
    "stored_CO2_mass_kg":final_stored,"step_component_mass_residual_kg":residual,"producer_CO2_gas_cut":cut})
   current={k:np.asarray(v).copy() for k,v in child.items()}
   if accepted_time in checkpoint_days and accepted_time not in checkpoints:
    checkpoints[accepted_time]={k:np.asarray(v).copy() for k,v in current.items()}
   if capacity_adjustments_step>0:
    capacity_limited_accepted+=1;force_refresh_next=True
   break

 for d in checkpoint_days:
  if d not in checkpoints:raise GateError(f"missing_exact_checkpoint:{d}")
 return {
  "checkpoints":checkpoints,"step_rows":step_rows,"refresh_rows":refresh_rows,"capacity_rows":capacity_rows,
  "controller_rows":controller_rows,"accepted_transition_count":len(step_rows),
  "refresh_count":refresh_count,"cadence_refresh_count":cadence_refresh_count,"capacity_refresh_count":capacity_refresh_count,
  "capacity_adjustments_total":capacity_adjustments_total,"capacity_limited_accepted":capacity_limited_accepted,
  "min_dt":float(np.min(accepted_dts)),"median_dt":float(np.median(accepted_dts)),"max_dt":float(np.max(accepted_dts)),
  "min_capacity_margin":float(np.min(capacity_margins)),
 }

def selftest():
 assert TARGETS==[120.0,125.0] and TARGETS[1]-TARGETS[0]==5.0
 print("POSTV16 GPU-HYB-G2-R2 structural self-test: PASS")

def main(project_root:Path,drive_root:Path)->int:
 root=project_root.resolve();drive=drive_root.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
 gates=[];stage="preflight"
 def gate(name,cond,detail=None):
  ok=bool(cond);gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if detail is None else repr(detail)})
  print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"),flush=True)
  if not ok:raise GateError(name)
 try:
  print("="*190)
  print("POSTV16-AV4-PIVOT-GPU-HYB-G2-R2 — RANK-2 DAY120->DAY125 EXACT FLOW + READ-ONLY HYBRID ENDPOINT DIAGNOSTIC")
  print("ONE CONTINUOUS CAPACITY-AWARE DAY100->125 PRODUCTION ROLLOUT; DAY120 IS AN EXACT SNAPSHOT, NOT A RESTART.")
  print("="*190)

  stage="repository_authority"
  gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
  gate("parent_is_G2_R1_R1",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
  gate("repository_clean",gt(root,"status","--porcelain")=="")

  prev=load_module_blob(root/G2R1R1_RUNNER,G2R1R1_BLOB,"g2r2_prev",root)
  e42=load_module_blob(root/E42_RUNNER,E42_BLOB,"g2r2_e42",root)
  stage="rank1_handoff"
  ps=js(drive/G2R1R1_REL/G2R1R1_SUMMARY)
  gate("rank1_status_exact",ps.get("status")==G2R1R1_STATUS,ps.get("status"))
  gate("rank1_G2_R2_authorized",ps.get("G2_R2_Day120_Day125_authorized") is True)
  gate("rank1_no_production_cadence",ps.get("production_pressure_refresh_cadence_selected") is False)

  stage="E42_production_authority"
  e42s=js(drive/E42_REL/E42_SUMMARY);e42c=js(drive/E42_REL/E42_CLOSURE)
  gate("E42_status_exact",e42s.get("status")==E42_STATUS,e42s.get("status"))
  gate("E42_closure_pass",e42c.get("all_gates_passed") is True,e42c.get("all_gates_passed"))

  r3r5=load_module_blob(root/e42.R3R5_RUNNER,e42.R3R5_GIT_BLOB,"g2r2_r3r5",root)
  r3r4r1=load_module_blob(root/e42.R3R4R1_RUNNER,e42.R3R4R1_GIT_BLOB,"g2r2_r3r4r1",root)
  repair=load_module_blob(root/e42.R2_REPAIR_RUNNER,e42.R2_REPAIR_GIT_BLOB,"g2r2_repair",root)

  role={}
  for key in ["R3R2R1","E36","E37A","R2_PHYSICS","SG2","SG3","SG4","SG5","SG6","SG7A","SG7D"]:
   fn,blob=r3r4r1.SOURCE_BLOBS[key];role[key]=load_module_blob(root/fn,blob,f"g2r2_{key.lower()}",root)
  r3r2r1=role["R3R2R1"];e36=role["E36"];e37a=role["E37A"];physics=role["R2_PHYSICS"]
  sg2=role["SG2"];sg3=role["SG3"];sg4=role["SG4"];sg5=role["SG5"];sg6=role["SG6"];sg7a=role["SG7A"];sg7d=role["SG7D"]
  pfn,pblob=r3r4r1.SOURCE_BLOBS["PERM"];pp=root/pfn
  gate("PERM_blob_exact",git_blob(pp,root)==pblob,git_blob(pp,root))

  parent_path=drive/R3R7_REL/R3R7_RESTART
  gate("Day100_parent_present",parent_path.is_file(),str(parent_path))
  gate("Day100_parent_SHA_exact",sha256(parent_path)==DAY100_SHA,sha256(parent_path))
  parent=load_npz(parent_path)
  gate("Day100_time_exact",scalar(parent["physical_time_days"])==100.0,scalar(parent["physical_time_days"]))
  gate("Day100_step_exact",int_scalar(parent["accepted_step_index"])==DAY100_STEP,int_scalar(parent["accepted_step_index"]))

  dx=20*FT_TO_M;dy=20*FT_TO_M;dz=4*FT_TO_M
  cell_pore_volume_m3=0.20*dx*dy*dz
  perm=np.loadtxt(pp,skiprows=1,dtype=np.float64).reshape((15,50,50),order="C")

  stage="continuous_exact_100_to125"
  rr=rollout_100_to125(
   parent,e42=e42,r3r5=r3r5,r3r4r1=r3r4r1,repair=repair,physics=physics,r3r2r1=r3r2r1,
   e36=e36,e37a=e37a,sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
   permeability_md=perm,cell_pore_volume_m3=cell_pore_volume_m3)
  state120=rr["checkpoints"][120.0];state125=rr["checkpoints"][125.0]
  gate("Day120_exact",scalar(state120["physical_time_days"])==120.0,scalar(state120["physical_time_days"]))
  gate("Day125_exact",scalar(state125["physical_time_days"])==125.0,scalar(state125["physical_time_days"]))
  gate("capacity_margin_positive",rr["min_capacity_margin"]>0,rr["min_capacity_margin"])

  stage="same_time_endpoint_flow"
  ref120,epoch120,db120=prev.same_time_endpoint(
   state120,r3r5=r3r5,r3r4r1=r3r4r1,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
   sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
   permeability_md=perm,cell_pore_volume_m3=cell_pore_volume_m3)
  ref125,epoch125,db125=prev.same_time_endpoint(
   state125,r3r5=r3r5,r3r4r1=r3r4r1,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
   sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
   permeability_md=perm,cell_pore_volume_m3=cell_pore_volume_m3)
  gate("streamline_shape_exact",db120["xyz_m"].shape==db125["xyz_m"].shape,(db120["xyz_m"].shape,db125["xyz_m"].shape))

  stage="P_CAD_rank2"
  a0=load_module_blob(root/prev.A0_RUNNER,prev.A0_BLOB,"g2r2_a0",root)
  rec120={"day":120,"pressure":epoch120["pressure_psi"],"Qx":epoch120["qx"],"Qy":epoch120["qy"],"Qz":epoch120["qz"],
          "tau_end_s":db120["tau_end_s"],"streamline_weight_m3_s":db120["weights_m3_s"],"xyz_m":db120["xyz_m"],"producer_labels":db120["producer"]}
  rec125={"day":125,"pressure":epoch125["pressure_psi"],"Qx":epoch125["qx"],"Qy":epoch125["qy"],"Qz":epoch125["qz"],
          "tau_end_s":db125["tau_end_s"],"streamline_weight_m3_s":db125["weights_m3_s"],"xyz_m":db125["xyz_m"],"producer_labels":db125["producer"]}
  early=a0.pair_metrics(rec120,rec125)
  with (drive/a0.OUT_REL/a0.HOLD_SUMMARY).open(newline="",encoding="utf-8") as f:hold=list(csv.DictReader(f))
  base=[r for r in hold if int(float(r["hold_days"]))==5]
  gate("single_late5_envelope",len(base)==1,len(base));base=base[0]
  comp={};within=True
  for m in PRIMARY_METRICS:
   v=float(early[m]);lim=float(base[m+"_max"]);ok=v<=lim*(1+NUM_EPS)+1e-15
   comp[m]={"early":v,"late5":lim,"inflation":v/lim if lim>0 else (0 if v==0 else float("inf")),"within":ok}
   if not ok:within=False
  exceed=[m for m in PRIMARY_METRICS if not comp[m]["within"]]

  stage="Hybrid_readonly_rank2"
  e11=load_module_blob(root/prev.E11_RUNNER,prev.E11_BLOB,"g2r2_e11",root)
  for rel,entry,label in [
   (e11.E8R1_REL,e11.E8R1["contract"],"E8R1"),(e11.E5_REL,e11.E5_MANIFEST,"E5"),
   (e11.E3_REL,e11.E3_PROTOCOL,"E3"),(e11.E6A_REL,e11.E6A_CHECKPOINT,"E6A")]:
   fn,expected=entry;p=drive/rel/fn
   gate(label+"_present",p.is_file(),str(p));gate(label+"_SHA",e11.sha(p)==expected,e11.sha(p) if p.is_file() else "missing")
  adapter=e11.import_exact(root/e11.E9_ADAPTER[0],e11.E9_ADAPTER[1],"g2r2_adapter")
  r2=e11.import_exact(root/e11.R2_ADAPTER[0],e11.R2_ADAPTER[1],"g2r2_r2")
  e9r1=e11.import_exact(root/e11.E9R1_RUNNER[0],e11.E9R1_RUNNER[1],"g2r2_e9r1")
  e8=e11.read_json(drive/e11.E8R1_REL/e11.E8R1["contract"][0]);screen=e8["learned_proposal_execution_screen"]
  e5=e11.read_json(drive/e11.E5_REL/e11.E5_MANIFEST[0]);e3=e11.read_json(drive/e11.E3_REL/e11.E3_PROTOCOL[0])
  p=e11.c14_production_params(root/e11.C14_SOURCE[0]);gate("C14_inside_E3",e11.parameters_inside_e3(p,e3))
  shock=r2.welge_shock(adapter.teacher_params(p),scan_nodes=4097);speed=float(shock["characteristic_speed"]);swstar=float(shock["Sw_star"])
  tf=e9r1.prepare_tf(e5);gate("TF220",tf.__version__=="2.20.0",tf.__version__);gate("GPU_visible",len(tf.config.list_physical_devices("GPU"))>=1)
  model=e9r1.build_inference_model(tf,10,"G2R2_Hybrid10");gate("Hybrid10_params",model.count_params()==52545,model.count_params())
  model.load_weights(str(drive/e11.E6A_REL/e11.E6A_CHECKPOINT[0]))

  h120,a120,p120=prev.hybrid_endpoint(
   120.0,ref120,epoch120,db120,e37a=e37a,physics=physics,e11=e11,adapter=adapter,r2=r2,e9r1=e9r1,
   tf=tf,model10=model,p=p,speed=speed,swstar=swstar,screen=screen)
  h125,a125,p125=prev.hybrid_endpoint(
   125.0,ref125,epoch125,db125,e37a=e37a,physics=physics,e11=e11,adapter=adapter,r2=r2,e9r1=e9r1,
   tf=tf,model10=model,p=p,speed=speed,swstar=swstar,screen=screen)
  gate("zero_unsafe_D120",h120["unsafe_learned_accepts"]==0,h120["unsafe_learned_accepts"])
  gate("zero_unsafe_D125",h125["unsafe_learned_accepts"]==0,h125["unsafe_learned_accepts"])

  stage="publication"
  gate("output_does_not_preexist",not out.exists(),str(out));out.mkdir(parents=True)
  b120=e42.deterministic_npz_bytes(state120);b125=e42.deterministic_npz_bytes(state125)
  (out/DAY120_STATE).write_bytes(b120);(out/DAY125_STATE).write_bytes(b125)
  (out/DAY120_DIAG).write_bytes(e42.deterministic_npz_bytes(a120));(out/DAY125_DIAG).write_bytes(e42.deterministic_npz_bytes(a125))
  row=dict(early)
  for m in PRIMARY_METRICS:
   row[m+"_late_5day_max"]=comp[m]["late5"];row[m+"_inflation_vs_late_5day_max"]=comp[m]["inflation"];row[m+"_within_late_5day_max"]=comp[m]["within"]
  row["all_primary_within_late_5day_max"]=within
  write_csv(out/CADENCE,[row]);write_csv(out/HYBRID,[h120,h125])
  routes=[]
  for d,hx in [(120,h120),(125,h125)]:
   routes += [
    {"day":d,"route":"HYBRID10_ACCEPT","count":hx["Hybrid10_screen_accept_count"]},
    {"day":d,"route":"HYBRID10_SCREEN_REJECT_EXACT_RUNTIME_FALLBACK","count":hx["Hybrid10_screen_reject_count"]},
    {"day":d,"route":"PREBT_EXACT_RUNTIME_FALLBACK","count":hx["preBT_exact_runtime_fallback"]},
    {"day":d,"route":"POSTBT_EXACT_RUNTIME_FALLBACK","count":hx["postBT_exact_runtime_fallback"]}]
  write_csv(out/ROUTES,routes);write_csv(out/PRODUCERS,p120+p125)
  write_csv(out/STEPS,rr["step_rows"]);write_csv(out/REFRESH,rr["refresh_rows"]);write_csv(out/CAPACITY,rr["capacity_rows"]);write_csv(out/CONTROLLER,rr["controller_rows"])

  classification=("RANK2_DAY120_DAY125_WITHIN_LATE_5DAY_MAX_ENVELOPE_G2_R3_DAY30_REFRESH_BRIDGE_AUTHORIZED"
                  if within else
                  "RANK2_DAY120_DAY125_EXCEEDS_LATE_5DAY_MAX_ENVELOPE_LOCAL_EXPANSION_FLAGGED_G2_R3_DAY30_REFRESH_BRIDGE_AUTHORIZED")
  summary={
   "milestone":M,"status":PASS,"classification":classification,
   "Day120_state_sha256":hashlib.sha256(b120).hexdigest(),"Day125_state_sha256":hashlib.sha256(b125).hexdigest(),
   "continuous_100_to125_rollout":True,"Day120_was_restart":False,
   "accepted_transition_count_100_to125":rr["accepted_transition_count"],"flow_refresh_count_100_to125":rr["refresh_count"],
   "cadence_refresh_count_100_to125":rr["cadence_refresh_count"],"capacity_refresh_count_100_to125":rr["capacity_refresh_count"],
   "capacity_controller_adjustments_100_to125":rr["capacity_adjustments_total"],"minimum_raw_capacity_margin_kg":rr["min_capacity_margin"],
   "rank2_probe_pair":[120,125],"P_CAD_primary_metrics":{m:comp[m]["early"] for m in PRIMARY_METRICS},
   "late_5day_max_envelope":{m:comp[m]["late5"] for m in PRIMARY_METRICS},
   "P_CAD_inflation_vs_late_5day_max":{m:comp[m]["inflation"] for m in PRIMARY_METRICS},
   "all_primary_within_late_5day_max_envelope":bool(within),"primary_metrics_exceeding_late_5day_max":exceed,
   "rank2_local_expansion_authorized":bool(not within),
   "rank2_local_expansion_pairs_if_needed":[[115,120],[125,130]] if not within else [],
   "Hybrid_Day120":h120,"Hybrid_Day125":h125,
   "Hybrid_recurrent_state_mutation_performed":False,"Hybrid_read_only_endpoint_diagnostic_completed":True,
   "new_Hybrid_error_acceptance_threshold_defined":False,
   "G2_R3_A0_Day30_current_authority_refresh_bridge_authorized":True,
   "G2_R3_Day40_Day45_execution_authorized":False,
   "production_pressure_refresh_cadence_selected":False,"P4_authorized":False}
  decision={
   "milestone":M,"status":PASS,"classification":classification,
   "rank2_early_5day_probe_complete":True,"rank2_exceeds_late_5day_envelope":bool(not within),
   "rank2_exceeding_metrics":exceed,"local_expansion_authorized_only_if_exceeded":bool(not within),
   "G2_R3_A0_Day30_refresh_bridge_authorized":True,"G2_R3_direct_execution_authorized":False,
   "reason_direct_rank3_locked":"Historical Day30 Cartesian state must first receive a certified same-time current-authority full flow refresh.",
   "production_pressure_refresh_cadence_selected":False,"Hybrid_may_advance_runtime_state":False,
   "future_recurrent_Hybrid_component_mass_bridge_still_required":True,"P4_authorized":False}
  (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
  (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
  write_csv(out/GATES,gates)
  manifest=[]
  for q in sorted(out.iterdir()):
   if q.is_file() and q.name!=MANIFEST:manifest.append({"file":q.name,"sha256":sha256(q),"bytes":q.stat().st_size})
  write_csv(out/MANIFEST,manifest)

  print("="*190);print(M,"PASS");print("Classification:",classification)
  print("Day120 state SHA:",summary["Day120_state_sha256"]);print("Day125 state SHA:",summary["Day125_state_sha256"])
  print("Continuous Day100->125 rollout: True; Day120 restart: False")
  print("All rank2 primary metrics within late 5-day max:",within);print("Exceeding metrics:",exceed)
  print("Day120 Hybrid candidates/accept/reject:",h120["learned_window_candidates"],h120["Hybrid10_screen_accept_count"],h120["Hybrid10_screen_reject_count"])
  print("Day125 Hybrid candidates/accept/reject:",h125["learned_window_candidates"],h125["Hybrid10_screen_accept_count"],h125["Hybrid10_screen_reject_count"])
  print("G2-R3-A0 Day30 refresh bridge authorized: True");print("Production cadence selected: False");print("P4 authorized: False")
  print("Output:",out);print("="*190)
  return 0
 except Exception as exc:
  blocked.mkdir(parents=True,exist_ok=True)
  (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
   "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
   "Hybrid_recurrent_state_mutation_performed":False,"production_pressure_refresh_cadence_selected":False,
   "G2_R3_A0_authorized":False,"P4_authorized":False},indent=2,sort_keys=True)+"\n",encoding="utf-8")
  print(M,"BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--project-root",type=Path,default=Path("."))
 ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"));ap.add_argument("--self-test",action="store_true")
 a=ap.parse_args()
 if a.self_test:selftest();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
