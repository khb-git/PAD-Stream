#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G2-R3"
PASS="POSTV16AV4PIVOTGPUHYBG2R3_RANK3_DAY40_DAY45_EXACT_FLOW_AND_READONLY_HYBRID_ENDPOINT_DIAGNOSTIC_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG2R3_TECHNICAL_OR_SAFETY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="408e86d97977901a214a4c0f5da6e53e7944ae7c"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

R3A0_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_A0_Day30_CurrentAuthority_SameTime_Flow_Refresh_Bridge.py"
R3A0_BLOB="a9b4f80f43734b54e37a7ab008c3da707c1ce933"
R3A0_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_A0_Day30_CurrentAuthority_SameTime_Flow_Refresh_Bridge"
R3A0_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_A0_Summary.json"
R3A0_RESTART="POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_A0_Day30_CurrentAuthority_Refreshed_Restart.npz"
R3A0_STATUS="POSTV16AV4PIVOTGPUHYBG2R3A0_DAY30_CURRENT_AUTHORITY_SAME_TIME_FLOW_REFRESH_BRIDGE_PASS_NO_PHYSICAL_TIME_ADVANCE"
DAY30_RESTART_SHA="093fa9570b07d91d6865c8464104cd6f72c271b2d638b93dc167c74497827035"

G2R2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Rank2_Day120_125_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2R2_BLOB="1d08f9b2d7c2e38c69862028a731f695811e3cf8"
G2R2_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Rank2_Day120_Day125_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
G2R2_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Summary.json"

G2R1R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_80_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2R1R1_BLOB="04c3940a7c736b1d210376113e48bab6111fc173"

E42_RUNNER="PAD_Stream_V16E42_Repaired_Production_Continuation_to_Exact_150Day_Observation.py"
E42_BLOB="7efe0cb943b40e976b7364241dc7f41dc819a2df"
A0_STATUS="POSTV16PCADA0_EXACT_PRESSURE_EVOLUTION_AND_FLOWEPOCH_HOLD_SCREENING_PASS_NO_PHYSICS_MUTATION"

PRIMARY=[
 "pressure_relative_L2","flux_relative_L2","tau_end_relative_L2",
 "streamline_weight_relative_L2","producer_connectivity_mismatch_fraction",
 "path_RMS_displacement_ft",
]
DAY_TO_S=86400.0
FT_TO_M=0.3048
NUM_EPS=1e-12
TARGET_FINAL=45.0
CHECKPOINTS=[40.0,45.0]

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G2_R3"
OUT_REL=BASE/(OUT_TOKEN+"_Rank3_Day40_Day45_ExactFlow_and_Hybrid_Endpoint_Diagnostic")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
CADENCE=f"{OUT_TOKEN}_Day40_to_Day45_PCAD_Metrics.csv"
HYBRID=f"{OUT_TOKEN}_Hybrid_Endpoint_Metrics.csv"
ROUTES=f"{OUT_TOKEN}_Hybrid_Route_Counts.csv"
PRODUCERS=f"{OUT_TOKEN}_Hybrid_Producer_Outlet_Diagnostics.csv"
STEPS=f"{OUT_TOKEN}_Accepted_Transitions_30_to45.csv"
REFRESH=f"{OUT_TOKEN}_Flow_Refreshes_30_to45.csv"
CAPACITY=f"{OUT_TOKEN}_Capacity_Preflight_Events.csv"
CONTROLLER=f"{OUT_TOKEN}_Capacity_Controller_Adjustments.csv"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"
DAY40_STATE=f"{OUT_TOKEN}_Exact_Day40_State.npz"
DAY45_STATE=f"{OUT_TOKEN}_Exact_Day45_State.npz"
DAY40_DIAG=f"{OUT_TOKEN}_Day40_ExactFlow_and_Hybrid_Diagnostic.npz"
DAY45_DIAG=f"{OUT_TOKEN}_Day45_ExactFlow_and_Hybrid_Diagnostic.npz"

class GateError(RuntimeError): pass

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for c in iter(lambda:f.read(1<<20),b""): h.update(c)
 return h.hexdigest()
def gt(root,*a): return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()
def scalar(v): return float(np.asarray(v).reshape(()))
def integer(v): return int(np.asarray(v).reshape(()))
def js(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def load_npz(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def module(root,fn,blob,name):
 p=root/fn
 if not p.is_file(): raise GateError(f"missing_source:{fn}")
 actual=gt(root,"hash-object",str(p))
 if actual!=blob: raise GateError(f"source_blob:{fn}:{actual}:{blob}")
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def write_csv(path,rows):
 if not rows: Path(path).write_text("",encoding="utf-8");return
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields:fields.append(k)
 with open(path,"w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def rollout_day30_to45(parent,*,e42,r3r5,r3r4r1,repair,physics,r3r2r1,e36,e37a,sg2,sg3,sg4,sg5,sg6,sg7a,sg7d,perm,pv):
 current={k:np.asarray(v).copy() for k,v in parent.items()}
 steps=[];refreshes=[];capacity=[];controller=[]
 epoch=None;epoch_start=None;force_refresh=False
 refresh_count=cadence_count=capacity_refresh_count=0
 capacity_adjustments=capacity_limited=0
 dts=[];margins=[];snapshots={}

 def do_refresh(trigger):
  nonlocal current,epoch,epoch_start,refresh_count,cadence_count,capacity_refresh_count
  t=scalar(current["physical_time_days"]);st=integer(current["accepted_step_index"])
  inj=scalar(current["cumulative_injected_co2_mass_kg"]);prod=scalar(current["cumulative_produced_co2_mass_kg"]);stored=scalar(current["stored_co2_mass_current_kg"])
  nxt,ep,_=r3r5.build_flow_epoch(
   current=current,r3r4r1=r3r4r1,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
   sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
   permeability_md=perm,cell_pore_volume_m3=pv)
  if scalar(nxt["physical_time_days"])!=t or integer(nxt["accepted_step_index"])!=st: raise GateError("refresh_advanced_state_index")
  if scalar(nxt["cumulative_injected_co2_mass_kg"])!=inj or scalar(nxt["cumulative_produced_co2_mass_kg"])!=prod: raise GateError("refresh_changed_mass_ledger")
  tol=max(1e-6,1e-10*max(abs(stored),1.0))
  if abs(scalar(nxt["stored_co2_mass_current_kg"])-stored)>tol: raise GateError("refresh_changed_stored_mass")
  current=nxt;epoch=ep;epoch_start=t;refresh_count+=1
  if trigger=="CADENCE":cadence_count+=1
  if trigger=="CAPACITY_PREFLIGHT_REJECTION":capacity_refresh_count+=1
  refreshes.append({"refresh_index":refresh_count,"trigger":trigger,"physical_time_days":t,"accepted_step_index":st,
   "CFL_dt_days":ep["cfl_dt_days"],"streamline_count":ep["nstream"],"capture_fraction":ep["capture_fraction"],
   "flow_local_relative_residual":ep["flow_local_residual"],"flow_global_relative_residual":ep["flow_global_residual"],
   "fixed_point_iterations":ep["fixed_point_iterations"],"pressure_rel_L2_vs_pre_refresh":ep["refresh_pressure_rel_L2_vs_parent"],
   "saturation_Linf_vs_pre_refresh":ep["refresh_saturation_Linf_vs_parent"],"refresh_global_mass_error_kg":ep["refresh_global_mass_error_kg"]})

 do_refresh("RESTART_OR_INITIALIZATION")

 while scalar(current["physical_time_days"])<TARGET_FINAL-1e-13:
  now=scalar(current["physical_time_days"])
  if force_refresh:
   do_refresh("POST_CAPACITY_LIMITED_ACCEPT");force_refresh=False;now=scalar(current["physical_time_days"])
  due=epoch_start+float(e42.MAX_FLOW_EPOCH_DAYS)
  if now>=due-1e-13:
   do_refresh("CADENCE");now=scalar(current["physical_time_days"]);due=epoch_start+float(e42.MAX_FLOW_EPOCH_DAYS)
  future=[x for x in CHECKPOINTS if x>now+1e-13]
  target=min(TARGET_FINAL,min(future) if future else TARGET_FINAL,due,now+float(epoch["cfl_dt_days"]))
  base=target-now
  if not np.isfinite(base) or base<=0: raise GateError(f"nonpositive_base_dt:{base}")
  candidate=float(base);same_parent_refresh=False;adj_this=0

  while True:
   pt=scalar(current["physical_time_days"]);ps=integer(current["accepted_step_index"])
   sat=np.asarray(current["transport_saturation"],dtype=np.float64);press=np.asarray(epoch["pressure_psi"],dtype=np.float64)
   pref=scalar(current["co2_density_reference_pressure_pa"]);stored=scalar(current["stored_co2_mass_current_kg"])
   candidate=min(candidate,float(epoch["cfl_dt_days"]),target-pt,TARGET_FINAL-pt)
   if candidate<=0: raise GateError("nonpositive_candidate_dt")
   recomputed=float(physics.stored_co2_mass_kg(sat,press,pref,pv))
   mt=max(1e-6,1e-10*max(abs(stored),1.0))
   if abs(recomputed-stored)>mt: raise GateError("parent_mass_pressure_mismatch")
   old_sat,old_mass,closure=e37a.sample_grid_inventory_to_control_volumes(physics,sat,press,pref,epoch["geometry"],epoch["nstream"],epoch["ncv"])
   st=max(1e-6,1e-10*max(abs(float(np.sum(old_mass))),1.0))
   if abs(closure)>st: raise GateError("grid_to_CV_sampling_closure")
   tr=e37a.advance_component_mass_control_volumes(
    physics,sg7a,old_sat,old_mass,epoch["geometry"]["cv_pressure_mass_coeff"],epoch["face_pressure_psi"],
    pref,epoch["weights_m3_day"],epoch["xi_faces"],candidate)
   injected=float(tr["injected_mass_kg"]);produced=float(tr["produced_mass_kg"])
   physical=e42.INJECTOR_MASS_RATE_KG_DAY*candidate
   if abs(injected-physical)>max(1e-6,1e-12*max(abs(physical),1.0)): raise GateError("fixed_rate_injection_mismatch")
   parent_mass=r3r4r1.parent_cellwise_component_mass(physics,sat,press,pref,pv)
   target_mass=stored+injected-produced
   pf=r3r4r1.preflight_mapback_capacity(
    physics=physics,parent_saturation=sat,parent_mass=parent_mass,old_cv_saturation=old_sat,new_cv_saturation=tr["new_saturation"],
    geometry=epoch["geometry"],pressure_psi=press,p_ref_gas_pa=pref,cell_pore_volume_m3=pv)
   margins.append(float(pf["minimum_capacity_margin_kg"]))
   if pf["overcapacity_cell_count"]>0:
    capacity.append({"physical_time_days":pt,"accepted_step_index":ps,"trial_dt_days":candidate,
     "same_parent_refresh_done":same_parent_refresh,"overcapacity_cell_count":pf["overcapacity_cell_count"],
     "max_capacity_excess_kg":pf["max_capacity_excess_kg"],"minimum_capacity_margin_kg":pf["minimum_capacity_margin_kg"]})
    if not same_parent_refresh:
     do_refresh("CAPACITY_PREFLIGHT_REJECTION");same_parent_refresh=True;continue
    ctl=repair.preflight_mapback_capacity(
     r2=physics,e37a=e37a,parent_grid_saturation=sat,old_cv_saturation=old_sat,new_cv_saturation=tr["new_saturation"],
     old_cv_mass=old_mass,new_cv_mass=tr["new_mass"],geometry=epoch["geometry"],pressure_psi=press,p_ref_gas_pa=pref,
     cell_pore_volume_m3=pv,target_final_mass_kg=target_mass,active_dt_days=candidate)
    if ctl.get("native_failure_required") or not ctl.get("controller_applicable"): raise GateError("capacity_controller_failure")
    rec=float(ctl["recommended_dt_days"])
    if not np.isfinite(rec) or rec<=0 or rec>=candidate: raise GateError("invalid_capacity_recommended_dt")
    adj_this+=1;capacity_adjustments+=1
    controller.append({"physical_time_days":pt,"accepted_step_index":ps,"adjustment_index_this_step":adj_this,
     "candidate_dt_days":candidate,"recommended_dt_days":rec,"raw_admissible_fraction":ctl["raw_admissible_fraction"],
     "max_capacity_excess_kg":ctl["max_capacity_excess_kg"],"limiting_cell_zero_based":str(ctl["upper_limiting_cell_zero_based"])})
    if adj_this>int(repair.MAX_CAPACITY_ADJUSTMENTS): raise GateError("capacity_adjustment_budget_exhausted")
    candidate=rec;continue

   mapping=e37a.map_control_volume_increment_to_grid(
    physics,sat,old_sat,tr["new_saturation"],old_mass,tr["new_mass"],epoch["geometry"],press,pref,pv,target_mass)
   cap=physics.conservative_capillary_mass_redistribution(
    transport_saturation=np.asarray(mapping["corrected_saturation"],dtype=np.float64),permeability_md=perm,
    pressure_psi=press,p_ref_pa=pref,cell_pore_volume_m3=pv,dt_seconds=candidate*DAY_TO_S)
   child_sat=np.asarray(cap["corrected"],dtype=np.float64);final_stored=float(cap["final_mass_state_kg"])
   resid=final_stored-stored-injected+produced
   ct=max(1e-6,1e-10*max(abs(target_mass),1.0))
   if abs(cap["external_mass_change_kg"])>ct or abs(resid)>ct: raise GateError("step_mass_closure")
   _,cut=e37a.producer_rows_from_flux(epoch["labels"],epoch["weights_m3_day"],tr["outlet_fractional_flow"],tr["face_mass_flux_kg_day"][:,-1],candidate)
   if not np.isfinite(cut) or not 0<=cut<=1: raise GateError("producer_gas_cut_invalid")

   child=e36.make_child_state(current,child_sat,press,pref,candidate,produced,cut,final_stored,resid,False)
   child["transport_face_count"]=np.asarray(epoch["nfaces"],dtype=np.int64)
   child["transport_control_volume_count"]=np.asarray(epoch["ncv"],dtype=np.int64)
   child["mass_conservative_flow_refresh_active"]=np.asarray(True,dtype=bool)
   child["runtime_refresh_policy_name_ascii"]=np.frombuffer(e42.PRODUCTION_POLICY.encode("ascii"),dtype=np.uint8)
   child["runtime_max_flow_epoch_days"]=np.asarray(e42.MAX_FLOW_EPOCH_DAYS,dtype=np.float64)
   child["V16E41R3R7_authoritative_post_observation_restart"]=np.asarray(False,dtype=bool)
   child["V16E42_rollout_active"]=np.asarray(False,dtype=bool)
   child["G2_R3_early_targeted_rollout_active"]=np.asarray(True,dtype=bool)
   child["last_grid_mapback_ledger_residual_kg"]=np.asarray(mapping["ledger_residual_kg"],dtype=np.float64)
   child["last_capillary_external_mass_change_kg"]=np.asarray(cap["external_mass_change_kg"],dtype=np.float64)
   at=scalar(child["physical_time_days"])
   for d in CHECKPOINTS:
    if abs(at-d)<=1e-13:
     child["physical_time_days"]=np.asarray(d,dtype=np.float64);at=d
   dts.append(candidate)
   steps.append({"accepted_step_index":integer(child["accepted_step_index"]),"parent_time_days":pt,"accepted_time_days":at,
    "accepted_dt_days":candidate,"active_epoch_CFL_dt_days":epoch["cfl_dt_days"],"epoch_age_before_step_days":pt-epoch_start,
    "targeted_checkpoint_landing":at in CHECKPOINTS,"capacity_same_parent_refresh_used":same_parent_refresh,
    "capacity_controller_adjustments":adj_this,"raw_minimum_capacity_margin_kg":pf["minimum_capacity_margin_kg"],
    "injected_CO2_mass_kg":injected,"produced_CO2_mass_kg":produced,"stored_CO2_mass_kg":final_stored,
    "step_component_mass_residual_kg":resid,"producer_CO2_gas_cut":cut})
   current={k:np.asarray(v).copy() for k,v in child.items()}
   if at in CHECKPOINTS and at not in snapshots: snapshots[at]={k:np.asarray(v).copy() for k,v in current.items()}
   if adj_this>0: capacity_limited+=1;force_refresh=True
   break

 for d in CHECKPOINTS:
  if d not in snapshots: raise GateError(f"missing_checkpoint:{d}")
 return {"checkpoints":snapshots,"steps":steps,"refreshes":refreshes,"capacity":capacity,"controller":controller,
  "accepted_transition_count":len(steps),"refresh_count":refresh_count,"cadence_refresh_count":cadence_count,
  "capacity_refresh_count":capacity_refresh_count,"capacity_adjustments":capacity_adjustments,
  "capacity_limited_accepted":capacity_limited,"min_dt":float(np.min(dts)),"median_dt":float(np.median(dts)),
  "max_dt":float(np.max(dts)),"min_capacity_margin":float(np.min(margins))}

def selftest():
 assert CHECKPOINTS==[40.0,45.0] and TARGET_FINAL==45.0
 print("POSTV16 GPU-HYB-G2-R3 structural self-test: PASS")

def main(root,drive):
 root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
 gates=[];stage="preflight"
 def gate(n,c,d=None):
  ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
  print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
  if not ok:raise GateError(n)
 try:
  print("="*190)
  print("G2-R3 — FINAL EARLY CADENCE PROBE DAY40->DAY45")
  print("CONTINUOUS CURRENT-AUTHORITY DAY30->45 ROLLOUT; DAY40 SNAPSHOT IS NOT A RESTART.")
  print("="*190)

  stage="repo"
  gate("branch",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
  gate("parent",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
  gate("clean",gt(root,"status","--porcelain")=="")

  bridge=module(root,R3A0_RUNNER,R3A0_BLOB,"g2r3_bridge")
  prev2=module(root,G2R2_RUNNER,G2R2_BLOB,"g2r3_prev2")
  prev1=module(root,G2R1R1_RUNNER,G2R1R1_BLOB,"g2r3_prev1")
  e42=module(root,E42_RUNNER,E42_BLOB,"g2r3_e42")

  stage="bridge_handoff"
  bs=js(drive/R3A0_REL/R3A0_SUM)
  gate("bridge_status",bs.get("status")==R3A0_STATUS,bs.get("status"))
  gate("rank3_authorized",bs.get("G2_R3_Day40_Day45_execution_authorized") is True)
  gate("bridge_restart_sha",bs.get("current_authority_Day30_restart_sha256")==DAY30_RESTART_SHA,bs.get("current_authority_Day30_restart_sha256"))
  p=drive/R3A0_REL/R3A0_RESTART
  gate("restart_present",p.is_file(),str(p));gate("restart_sha_exact",sha(p)==DAY30_RESTART_SHA,sha(p))
  parent=load_npz(p);gate("restart_time_30",scalar(parent["physical_time_days"])==30.0,scalar(parent["physical_time_days"]))

  r3r5=module(root,e42.R3R5_RUNNER,e42.R3R5_GIT_BLOB,"g2r3_r3r5")
  r3r4r1=module(root,e42.R3R4R1_RUNNER,e42.R3R4R1_GIT_BLOB,"g2r3_r3r4r1")
  repair=module(root,e42.R2_REPAIR_RUNNER,e42.R2_REPAIR_GIT_BLOB,"g2r3_repair")
  role={}
  for key in ["R3R2R1","E36","E37A","R2_PHYSICS","SG2","SG3","SG4","SG5","SG6","SG7A","SG7D"]:
   fn,b=r3r4r1.SOURCE_BLOBS[key];role[key]=module(root,fn,b,"g2r3_"+key.lower())
  r3r2r1,e36,e37a,physics=role["R3R2R1"],role["E36"],role["E37A"],role["R2_PHYSICS"]
  sg2,sg3,sg4,sg5,sg6,sg7a,sg7d=role["SG2"],role["SG3"],role["SG4"],role["SG5"],role["SG6"],role["SG7A"],role["SG7D"]
  pfn,pblob=r3r4r1.SOURCE_BLOBS["PERM"];pp=root/pfn;gate("perm_blob",gt(root,"hash-object",str(pp))==pblob)
  dx,dy,dz=20*FT_TO_M,20*FT_TO_M,4*FT_TO_M;pv=0.20*dx*dy*dz
  perm=np.loadtxt(pp,skiprows=1,dtype=np.float64).reshape((15,50,50),order="C")

  stage="continuous_rollout"
  rr=rollout_day30_to45(parent,e42=e42,r3r5=r3r5,r3r4r1=r3r4r1,repair=repair,physics=physics,r3r2r1=r3r2r1,
   e36=e36,e37a=e37a,sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,perm=perm,pv=pv)
  s40=rr["checkpoints"][40.0];s45=rr["checkpoints"][45.0]
  gate("Day40_exact",scalar(s40["physical_time_days"])==40.0,scalar(s40["physical_time_days"]))
  gate("Day45_exact",scalar(s45["physical_time_days"])==45.0,scalar(s45["physical_time_days"]))
  gate("capacity_margin_positive",rr["min_capacity_margin"]>0,rr["min_capacity_margin"])

  stage="endpoint_flow"
  ref40,ep40,db40=prev1.same_time_endpoint(
   s40,r3r5=r3r5,r3r4r1=r3r4r1,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,sg2=sg2,sg3=sg3,sg4=sg4,
   sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,permeability_md=perm,cell_pore_volume_m3=pv)
  ref45,ep45,db45=prev1.same_time_endpoint(
   s45,r3r5=r3r5,r3r4r1=r3r4r1,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,sg2=sg2,sg3=sg3,sg4=sg4,
   sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,permeability_md=perm,cell_pore_volume_m3=pv)
  gate("streamline_shape",db40["xyz_m"].shape==db45["xyz_m"].shape,(db40["xyz_m"].shape,db45["xyz_m"].shape))

  stage="P_CAD"
  a0=module(root,prev1.A0_RUNNER,prev1.A0_BLOB,"g2r3_a0")
  rec40={"day":40,"pressure":ep40["pressure_psi"],"Qx":ep40["qx"],"Qy":ep40["qy"],"Qz":ep40["qz"],
         "tau_end_s":db40["tau_end_s"],"streamline_weight_m3_s":db40["weights_m3_s"],"xyz_m":db40["xyz_m"],"producer_labels":db40["producer"]}
  rec45={"day":45,"pressure":ep45["pressure_psi"],"Qx":ep45["qx"],"Qy":ep45["qy"],"Qz":ep45["qz"],
         "tau_end_s":db45["tau_end_s"],"streamline_weight_m3_s":db45["weights_m3_s"],"xyz_m":db45["xyz_m"],"producer_labels":db45["producer"]}
  early=a0.pair_metrics(rec40,rec45)
  with (drive/a0.OUT_REL/a0.HOLD_SUMMARY).open(newline="",encoding="utf-8") as f:hold=list(csv.DictReader(f))
  base=[r for r in hold if int(float(r["hold_days"]))==5];gate("late5_row",len(base)==1,len(base));base=base[0]
  comp={};within=True
  for m in PRIMARY:
   v=float(early[m]);lim=float(base[m+"_max"]);ok=v<=lim*(1+NUM_EPS)+1e-15
   comp[m]={"early":v,"late5":lim,"inflation":v/lim if lim>0 else (0 if v==0 else float("inf")),"within":ok}
   if not ok:within=False
  exceed=[m for m in PRIMARY if not comp[m]["within"]]

  stage="Hybrid"
  e11=module(root,prev1.E11_RUNNER,prev1.E11_BLOB,"g2r3_e11")
  for rel,entry,label in [(e11.E8R1_REL,e11.E8R1["contract"],"E8R1"),(e11.E5_REL,e11.E5_MANIFEST,"E5"),
                          (e11.E3_REL,e11.E3_PROTOCOL,"E3"),(e11.E6A_REL,e11.E6A_CHECKPOINT,"E6A")]:
   fn,expected=entry;q=drive/rel/fn;gate(label+"_present",q.is_file(),str(q));gate(label+"_sha",e11.sha(q)==expected,e11.sha(q) if q.is_file() else "missing")
  adapter=e11.import_exact(root/e11.E9_ADAPTER[0],e11.E9_ADAPTER[1],"g2r3_adapter")
  r2=e11.import_exact(root/e11.R2_ADAPTER[0],e11.R2_ADAPTER[1],"g2r3_r2")
  e9r1=e11.import_exact(root/e11.E9R1_RUNNER[0],e11.E9R1_RUNNER[1],"g2r3_e9r1")
  screen=e11.read_json(drive/e11.E8R1_REL/e11.E8R1["contract"][0])["learned_proposal_execution_screen"]
  e5=e11.read_json(drive/e11.E5_REL/e11.E5_MANIFEST[0]);e3=e11.read_json(drive/e11.E3_REL/e11.E3_PROTOCOL[0])
  pars=e11.c14_production_params(root/e11.C14_SOURCE[0]);gate("C14_inside_E3",e11.parameters_inside_e3(pars,e3))
  shock=r2.welge_shock(adapter.teacher_params(pars),scan_nodes=4097);speed=float(shock["characteristic_speed"]);swstar=float(shock["Sw_star"])
  tf=e9r1.prepare_tf(e5);gate("TF220",tf.__version__=="2.20.0",tf.__version__);gate("GPU_visible",len(tf.config.list_physical_devices("GPU"))>=1)
  model=e9r1.build_inference_model(tf,10,"G2R3_Hybrid10");gate("Hybrid10_params",model.count_params()==52545,model.count_params())
  model.load_weights(str(drive/e11.E6A_REL/e11.E6A_CHECKPOINT[0]))
  h40,a40,p40=prev1.hybrid_endpoint(40.0,ref40,ep40,db40,e37a=e37a,physics=physics,e11=e11,adapter=adapter,r2=r2,e9r1=e9r1,
   tf=tf,model10=model,p=pars,speed=speed,swstar=swstar,screen=screen)
  h45,a45,p45=prev1.hybrid_endpoint(45.0,ref45,ep45,db45,e37a=e37a,physics=physics,e11=e11,adapter=adapter,r2=r2,e9r1=e9r1,
   tf=tf,model10=model,p=pars,speed=speed,swstar=swstar,screen=screen)
  gate("zero_unsafe40",h40["unsafe_learned_accepts"]==0,h40["unsafe_learned_accepts"])
  gate("zero_unsafe45",h45["unsafe_learned_accepts"]==0,h45["unsafe_learned_accepts"])

  stage="publish"
  gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
  b40=e42.deterministic_npz_bytes(s40);b45=e42.deterministic_npz_bytes(s45)
  (out/DAY40_STATE).write_bytes(b40);(out/DAY45_STATE).write_bytes(b45)
  (out/DAY40_DIAG).write_bytes(e42.deterministic_npz_bytes(a40));(out/DAY45_DIAG).write_bytes(e42.deterministic_npz_bytes(a45))
  row=dict(early)
  for m in PRIMARY:
   row[m+"_late_5day_max"]=comp[m]["late5"];row[m+"_inflation_vs_late_5day_max"]=comp[m]["inflation"];row[m+"_within_late_5day_max"]=comp[m]["within"]
  row["all_primary_within_late_5day_max"]=within
  write_csv(out/CADENCE,[row]);write_csv(out/HYBRID,[h40,h45])
  routes=[]
  for d,h in [(40,h40),(45,h45)]:
   routes += [{"day":d,"route":"HYBRID10_ACCEPT","count":h["Hybrid10_screen_accept_count"]},
              {"day":d,"route":"HYBRID10_SCREEN_REJECT_EXACT_RUNTIME_FALLBACK","count":h["Hybrid10_screen_reject_count"]},
              {"day":d,"route":"PREBT_EXACT_RUNTIME_FALLBACK","count":h["preBT_exact_runtime_fallback"]},
              {"day":d,"route":"POSTBT_EXACT_RUNTIME_FALLBACK","count":h["postBT_exact_runtime_fallback"]}]
  write_csv(out/ROUTES,routes);write_csv(out/PRODUCERS,p40+p45);write_csv(out/STEPS,rr["steps"]);write_csv(out/REFRESH,rr["refreshes"])
  write_csv(out/CAPACITY,rr["capacity"]);write_csv(out/CONTROLLER,rr["controller"])

  classification=("RANK3_DAY40_DAY45_WITHIN_LATE_5DAY_MAX_ENVELOPE_ALL_THREE_EARLY_PROBES_COMPLETE_CADENCE_DECISION_FREEZE_AUTHORIZED"
                  if within else
                  "RANK3_DAY40_DAY45_EXCEEDS_LATE_5DAY_MAX_ENVELOPE_LOCAL_EXPANSION_REQUIRED_BEFORE_CADENCE_DECISION")
  summary={"milestone":M,"status":PASS,"classification":classification,
   "Day40_state_sha256":hashlib.sha256(b40).hexdigest(),"Day45_state_sha256":hashlib.sha256(b45).hexdigest(),
   "continuous_30_to45_rollout":True,"Day40_was_restart":False,
   "accepted_transition_count_30_to45":rr["accepted_transition_count"],"flow_refresh_count_30_to45":rr["refresh_count"],
   "cadence_refresh_count_30_to45":rr["cadence_refresh_count"],"capacity_refresh_count_30_to45":rr["capacity_refresh_count"],
   "capacity_controller_adjustments_30_to45":rr["capacity_adjustments"],"minimum_raw_capacity_margin_kg":rr["min_capacity_margin"],
   "rank3_probe_pair":[40,45],"P_CAD_primary_metrics":{m:comp[m]["early"] for m in PRIMARY},
   "late_5day_max_envelope":{m:comp[m]["late5"] for m in PRIMARY},"P_CAD_inflation_vs_late_5day_max":{m:comp[m]["inflation"] for m in PRIMARY},
   "all_primary_within_late_5day_max_envelope":bool(within),"primary_metrics_exceeding_late_5day_max":exceed,
   "rank3_local_expansion_authorized":bool(not within),"rank3_local_expansion_pairs_if_needed":[[35,40],[45,50]] if not within else [],
   "Hybrid_Day40":h40,"Hybrid_Day45":h45,"Hybrid_recurrent_state_mutation_performed":False,
   "Hybrid_read_only_endpoint_diagnostic_completed":True,"new_Hybrid_error_acceptance_threshold_defined":False,
   "all_three_ranked_early_probe_pairs_complete":True,
   "cadence_decision_freeze_authorized":bool(within),
   "early_3D_visualization_sequence_authorized":True,
   "early_3D_visualization_days":[40,45,75,80,120,125],
   "production_pressure_refresh_cadence_selected":False,"P4_authorized":False}
  decision={"milestone":M,"status":PASS,"classification":classification,
   "rank3_complete":True,"rank3_exceeds_late_5day_envelope":bool(not within),"rank3_exceeding_metrics":exceed,
   "local_expansion_required_before_cadence_decision":bool(not within),
   "cadence_decision_freeze_authorized":bool(within),"early_3D_visualization_authorized":True,
   "production_pressure_refresh_cadence_selected":False,"Hybrid_may_advance_runtime_state":False,
   "future_recurrent_Hybrid_component_mass_bridge_still_required":True,"P4_authorized":False}
  (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
  (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
  write_csv(out/GATES,gates)
  manifest=[{"file":q.name,"sha256":sha(q),"bytes":q.stat().st_size} for q in sorted(out.iterdir()) if q.is_file() and q.name!=MANIFEST]
  write_csv(out/MANIFEST,manifest)

  print("="*190);print(M,"PASS");print("Classification:",classification)
  print("Day40 state SHA:",summary["Day40_state_sha256"]);print("Day45 state SHA:",summary["Day45_state_sha256"])
  print("Continuous Day30->45 rollout: True; Day40 restart: False")
  print("All rank3 primary metrics within late 5-day max:",within);print("Exceeding metrics:",exceed)
  print("Day40 Hybrid candidates/accept/reject:",h40["learned_window_candidates"],h40["Hybrid10_screen_accept_count"],h40["Hybrid10_screen_reject_count"])
  print("Day45 Hybrid candidates/accept/reject:",h45["learned_window_candidates"],h45["Hybrid10_screen_accept_count"],h45["Hybrid10_screen_reject_count"])
  print("Cadence decision freeze authorized:",bool(within));print("Early 3D visualization authorized: True")
  print("Production cadence selected: False");print("P4 authorized: False");print("="*190)
  return 0
 except Exception as exc:
  blocked.mkdir(parents=True,exist_ok=True)
  (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps(
   {"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
    "Hybrid_recurrent_state_mutation_performed":False,"cadence_decision_freeze_authorized":False,
    "production_pressure_refresh_cadence_selected":False,"P4_authorized":False},indent=2,sort_keys=True)+"\n",encoding="utf-8")
  print(M,"BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--project-root",type=Path,default=Path("."))
 ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"));ap.add_argument("--self-test",action="store_true")
 a=ap.parse_args()
 if a.self_test:selftest();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
