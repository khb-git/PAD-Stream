#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G2-R3-A0"
PASS="POSTV16AV4PIVOTGPUHYBG2R3A0_DAY30_CURRENT_AUTHORITY_SAME_TIME_FLOW_REFRESH_BRIDGE_PASS_NO_PHYSICAL_TIME_ADVANCE"
BLOCK="POSTV16AV4PIVOTGPUHYBG2R3A0_DAY30_REFRESH_BRIDGE_BLOCK_NO_PHYSICAL_TIME_ADVANCE"
BRANCH="postv16-av4-pivot"
PARENT="275af748deffab3c2d6ff7c7ccd705d985389ae5"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G2R2_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Rank2_Day120_Day125_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
G2R2_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Summary.json"
G2R2_STATUS="POSTV16AV4PIVOTGPUHYBG2R2_RANK2_DAY120_DAY125_EXACT_FLOW_AND_READONLY_HYBRID_ENDPOINT_DIAGNOSTIC_PASS"
G2A0_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_A0_Early_Targeted_Window_DualTransport_Protocol_Freeze"
G2A0_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_A0_Summary.json"

E39_REL=Path("provenance/hybrid_dp/V16E39_POST_BREAKTHROUGH_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT")
E39_SUM="PAD_Stream_V16E39_Summary.json"
E39_STATE="V16E39_Canonical_PostBreakthrough_SGSim_Runtime_State_Observation_0030d.npz"
E39_STATUS="POST_BREAKTHROUGH_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT_VALIDATED"

R3R5=("PAD_Stream_V16E41R3R5_Multi_Refresh_Cadence_Sensitivity_Runtime_Refresh_Policy_Calibration.py","15aae3224ba4337cad72f9b4aa9166d602791349")
R3R4R1=("PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py","5f8433437ce111533338ceada922f51abb2edefe")
E42=("PAD_Stream_V16E42_Repaired_Production_Continuation_to_Exact_150Day_Observation.py","7efe0cb943b40e976b7364241dc7f41dc819a2df")
POLICY="HALF_OBSERVED_STALE_INTERVAL"
MAX_EPOCH=4.9417335239115445
FT_TO_M=0.3048

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_A0"
OUT_REL=BASE/(OUT_TOKEN+"_Day30_CurrentAuthority_SameTime_Flow_Refresh_Bridge")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
AUDIT=f"{OUT_TOKEN}_SameTime_Refresh_Audit.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
RESTART=f"{OUT_TOKEN}_Day30_CurrentAuthority_Refreshed_Restart.npz"
FLOW=f"{OUT_TOKEN}_Day30_Exact_Flow_Diagnostic.npz"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

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
 with np.load(p,allow_pickle=False) as z: return {k:z[k].copy() for k in z.files}
def module(root,spec,name):
 fn,blob=spec;p=root/fn
 if not p.is_file(): raise GateError(f"missing_source:{fn}")
 actual=gt(root,"hash-object",str(p))
 if actual!=blob: raise GateError(f"blob:{fn}:{actual}:{blob}")
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def write_csv(p,rows):
 if not rows: Path(p).write_text("",encoding="utf-8"); return
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields: fields.append(k)
 with open(p,"w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def selftest():
 assert MAX_EPOCH<5.0 and POLICY=="HALF_OBSERVED_STALE_INTERVAL"
 print("POSTV16 GPU-HYB-G2-R3-A0 structural self-test: PASS")

def main(root,drive):
 root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
 gates=[];stage="preflight"
 def gate(n,c,d=None):
  ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
  print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
  if not ok: raise GateError(n)
 try:
  print("="*170)
  print("G2-R3-A0 — HISTORICAL DAY30 -> CURRENT-AUTHORITY SAME-TIME FULL FLOW REFRESH")
  print("NO TRANSPORT ADVANCE. NO HYBRID INFERENCE.")
  print("="*170)

  stage="repository"
  gate("branch",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
  gate("parent",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
  gate("clean",gt(root,"status","--porcelain")=="")

  stage="handoff"
  s2=js(drive/G2R2_REL/G2R2_SUM)
  gate("G2R2_status",s2.get("status")==G2R2_STATUS,s2.get("status"))
  gate("bridge_authorized",s2.get("G2_R3_A0_Day30_current_authority_refresh_bridge_authorized") is True)
  gate("cadence_unselected",s2.get("production_pressure_refresh_cadence_selected") is False)
  a0=js(drive/G2A0_REL/G2A0_SUM)
  expected_sha=a0["Day30_anchor_sha256"]

  r3r5=module(root,R3R5,"g2r3a0_r3r5")
  r3r4r1=module(root,R3R4R1,"g2r3a0_r3r4r1")
  e42=module(root,E42,"g2r3a0_e42")
  role={}
  for key in ["R3R2R1","E36","E37A","R2_PHYSICS","SG2","SG3","SG4","SG5","SG6","SG7A","SG7D"]:
   role[key]=module(root,r3r4r1.SOURCE_BLOBS[key],"g2r3a0_"+key.lower())
  r3r2r1,e36,e37a,physics=role["R3R2R1"],role["E36"],role["E37A"],role["R2_PHYSICS"]
  sg2,sg3,sg4,sg5,sg6,sg7a,sg7d=role["SG2"],role["SG3"],role["SG4"],role["SG5"],role["SG6"],role["SG7A"],role["SG7D"]
  pfn,pblob=r3r4r1.SOURCE_BLOBS["PERM"];pp=root/pfn
  gate("perm_blob",gt(root,"hash-object",str(pp))==pblob)

  stage="historical_Day30"
  e39s=js(drive/E39_REL/E39_SUM);gate("E39_status",e39s.get("status")==E39_STATUS,e39s.get("status"))
  p=drive/E39_REL/E39_STATE;gate("Day30_present",p.is_file(),str(p));gate("Day30_sha",sha(p)==expected_sha,sha(p))
  state=load_npz(p);gate("Day30_time",scalar(state["physical_time_days"])==30.0,scalar(state["physical_time_days"]))
  for k in ["transport_saturation","accepted_pressure_psi","co2_density_reference_pressure_pa","stored_co2_mass_current_kg",
            "cumulative_injected_co2_mass_kg","cumulative_produced_co2_mass_kg","accepted_step_index"]:
   gate("key_"+k,k in state)

  dx,dy,dz=20*FT_TO_M,20*FT_TO_M,4*FT_TO_M
  pv=0.20*dx*dy*dz
  perm=np.loadtxt(pp,skiprows=1,dtype=np.float64).reshape((15,50,50),order="C")

  stage="pre_refresh_mass"
  t0=scalar(state["physical_time_days"]);step0=integer(state["accepted_step_index"])
  inj0=scalar(state["cumulative_injected_co2_mass_kg"]);prod0=scalar(state["cumulative_produced_co2_mass_kg"]);stored0=scalar(state["stored_co2_mass_current_kg"])
  sat0=np.asarray(state["transport_saturation"],dtype=np.float64);p0=np.asarray(state["accepted_pressure_psi"],dtype=np.float64)
  pref=scalar(state["co2_density_reference_pressure_pa"])
  pm=r3r4r1.parent_cellwise_component_mass(physics,sat0,p0,pref,pv)
  mt=max(1e-6,1e-10*max(abs(stored0),1.0));mismatch=float(np.sum(pm))-stored0
  gate("cellwise_mass_ledger",abs(mismatch)<=mt,(mismatch,mt))

  stage="current_authority_refresh"
  refreshed,epoch,_=r3r5.build_flow_epoch(
   current=state,r3r4r1=r3r4r1,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
   sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
   permeability_md=perm,cell_pore_volume_m3=pv)
  gate("same_time",scalar(refreshed["physical_time_days"])==t0)
  gate("same_step",integer(refreshed["accepted_step_index"])==step0)
  gate("inj_unchanged",scalar(refreshed["cumulative_injected_co2_mass_kg"])==inj0)
  gate("prod_unchanged",scalar(refreshed["cumulative_produced_co2_mass_kg"])==prod0)
  gate("stored_unchanged",abs(scalar(refreshed["stored_co2_mass_current_kg"])-stored0)<=mt)
  sat1=np.asarray(refreshed["transport_saturation"],dtype=np.float64);p1=np.asarray(refreshed["accepted_pressure_psi"],dtype=np.float64)
  sat_linf=float(np.max(np.abs(sat1-sat0)))
  p_rel=float(np.linalg.norm((p1-p0).ravel())/max(float(np.linalg.norm(p0.ravel())),1e-30))
  gate("sat_finite",np.all(np.isfinite(sat1)));gate("pressure_finite",np.all(np.isfinite(p1)))
  gate("sat_bounds",float(np.min(sat1))>=-1e-10 and float(np.max(sat1))<=0.80000001,(float(np.min(sat1)),float(np.max(sat1))))
  gate("flow_local",float(epoch["flow_local_residual"])<1e-8,epoch["flow_local_residual"])
  gate("flow_global",float(epoch["flow_global_residual"])<1e-8,epoch["flow_global_residual"])
  gate("capture",abs(float(epoch["capture_fraction"])-1.0)<=1e-10,epoch["capture_fraction"])

  vx,vy,vz=sg5.construct_face_pore_velocities(np.asarray(epoch["qx"]),np.asarray(epoch["qy"]),np.asarray(epoch["qz"]))
  _faces,seeds=sg5.build_seeds(np.asarray(epoch["qx"]),np.asarray(epoch["qy"]),np.asarray(epoch["qz"]))
  streams=sg5.trace_streamlines(seeds,vx,vy,vz)
  db0=sg6.build_transport_database(r3r4r1.convert_sg5_to_sg6_streamlines(streams))
  db={k:np.asarray(db0[k]) for k in ["xyz_m","tau_s","tau_end_s","weights_m3_s","producer","xi"]}
  gate("streamlines",db["xyz_m"].shape[0]>0,db["xyz_m"].shape);gate("nodes_201",db["xyz_m"].shape[1]==201,db["xyz_m"].shape)

  refreshed["runtime_refresh_policy_name_ascii"]=np.frombuffer(POLICY.encode("ascii"),dtype=np.uint8)
  refreshed["runtime_max_flow_epoch_days"]=np.asarray(MAX_EPOCH,dtype=np.float64)
  refreshed["G2_R3_Day30_current_authority_refresh_bridge"]=np.asarray(True,dtype=bool)
  refreshed["G2_R3_Day30_bridge_source_state_sha256_ascii"]=np.frombuffer(expected_sha.encode("ascii"),dtype=np.uint8)
  refreshed["G2_R3_Day30_bridge_epoch_start_time_days"]=np.asarray(30.0,dtype=np.float64)
  refreshed["V16E41R3R7_authoritative_post_observation_restart"]=np.asarray(False,dtype=bool)
  refreshed["V16E42_rollout_active"]=np.asarray(False,dtype=bool)

  stage="publish"
  gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
  rb=e42.deterministic_npz_bytes(refreshed)
  fb=e42.deterministic_npz_bytes({
   "physical_time_days":np.asarray(30.0),"pressure_psi":np.asarray(epoch["pressure_psi"]),
   "Qx":np.asarray(epoch["qx"]),"Qy":np.asarray(epoch["qy"]),"Qz":np.asarray(epoch["qz"]),
   "xyz_m":db["xyz_m"],"tau_s":db["tau_s"],"tau_end_s":db["tau_end_s"],
   "weights_m3_s":db["weights_m3_s"],"producer":db["producer"].astype("U64"),"xi":db["xi"]})
  (out/RESTART).write_bytes(rb);(out/FLOW).write_bytes(fb)

  restart_sha=hashlib.sha256(rb).hexdigest()
  audit={"milestone":M,"status":PASS,"historical_Day30_sha256":expected_sha,"refreshed_Day30_sha256":restart_sha,
         "same_time_saturation_Linf_change":sat_linf,"same_time_pressure_relative_L2_change":p_rel,
         "fixed_point_iterations":int(epoch["fixed_point_iterations"]),"flow_local_relative_residual":float(epoch["flow_local_residual"]),
         "flow_global_relative_residual":float(epoch["flow_global_residual"]),"streamline_count":int(db["xyz_m"].shape[0]),
         "CFL_dt_days":float(epoch["cfl_dt_days"]),"time_advanced":False,"injection_ledger_changed":False,
         "production_ledger_changed":False,"stored_mass_ledger_changed":False}
  decision={"milestone":M,"status":PASS,
            "classification":"HISTORICAL_DAY30_RECONCILED_TO_CURRENT_MASS_CONSERVATIVE_FULL_FLOW_AUTHORITY_G2_R3_DAY40_DAY45_EXECUTION_AUTHORIZED",
            "G2_R3_Day40_Day45_execution_authorized":True,
            "rank3_parent":"current-authority refreshed Day30 restart",
            "rank3_semantics":"continuous Day30->45 current capacity-aware runtime; exact Day40 snapshot is not a restart",
            "production_pressure_refresh_cadence_selected":False,"Hybrid_may_advance_runtime_state":False,"P4_authorized":False}
  summary={**audit,"classification":decision["classification"],"current_authority_Day30_restart_sha256":restart_sha,
           "G2_R3_Day40_Day45_execution_authorized":True,"production_pressure_refresh_cadence_selected":False,"P4_authorized":False}
  for fn,obj in [(AUDIT,audit),(DECISION,decision),(SUMMARY,summary)]:
   (out/fn).write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
  write_csv(out/GATES,gates)
  manifest=[{"file":q.name,"sha256":sha(q),"bytes":q.stat().st_size} for q in sorted(out.iterdir()) if q.is_file() and q.name!=MANIFEST]
  write_csv(out/MANIFEST,manifest)

  print("="*170);print(M,"PASS")
  print("Historical Day30 SHA                    :",expected_sha)
  print("Current-authority Day30 restart SHA     :",restart_sha)
  print("Same-time saturation Linf change        :",sat_linf)
  print("Same-time pressure relative L2 change    :",p_rel)
  print("Fixed-point iterations                  :",audit["fixed_point_iterations"])
  print("Streamline count                        :",audit["streamline_count"])
  print("CFL dt days                             :",audit["CFL_dt_days"])
  print("Time advanced                           : False")
  print("Mass ledgers changed                    : False")
  print("G2-R3 Day40->45 execution authorized    : True")
  print("Production cadence selected             : False")
  print("P4 authorized                           : False")
  print("="*170)
  return 0
 except Exception as exc:
  blocked.mkdir(parents=True,exist_ok=True)
  (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps(
   {"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
    "physical_time_advanced":False,"G2_R3_Day40_Day45_execution_authorized":False,
    "production_pressure_refresh_cadence_selected":False,"P4_authorized":False},indent=2,sort_keys=True)+"\n",encoding="utf-8")
  print(M,"BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--project-root",type=Path,default=Path("."))
 ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
 ap.add_argument("--self-test",action="store_true");a=ap.parse_args()
 if a.self_test:selftest();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
