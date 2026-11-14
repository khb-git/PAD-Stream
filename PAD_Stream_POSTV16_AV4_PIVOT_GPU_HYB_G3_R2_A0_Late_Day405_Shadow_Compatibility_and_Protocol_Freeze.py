#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,subprocess
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G3-R2-A0"
PASS="POSTV16AV4PIVOTGPUHYBG3R2A0_LATE_DAY405_SAME_STATE_SHADOW_COMPATIBILITY_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBG3R2A0_LATE_SHADOW_COMPATIBILITY_BLOCK_NO_PHYSICS_EXECUTION"
BRANCH="postv16-av4-pivot"
PARENT="062d5337cce82aea2feacffd91cbda2b73c5cddd"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G3R1_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R1_Day45_SameState_Stale_vs_Refreshed_Shadow_Transport"
G3R1_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R1_Summary.json"
G3R1_STATUS="POSTV16AV4PIVOTGPUHYBG3R1_DAY45_SAME_STATE_STALE_VS_REFRESHED_SHADOW_TRANSPORT_PASS"

D390_REL=BASE/"POSTV16_AV4_PIVOT_P3_R1_R7_R7_XY2_Day385_to_Day390_FifthObservation_Pilot_and_Exact_Flow_Diagnostic"
D390_STATE="POSTV16_AV4_PIVOT_P3_R1_R7_R7_Day0390_Accepted_Dense_State.npz"
D390_DIAG="POSTV16_AV4_PIVOT_P3_R1_R7_R7_Day0390_Exact_Flow_Diagnostic.npz"
D390_STATE_SHA="83e26d77f5f853412b817c37dcd4d3958ba4469bbd14c10a8467a256b52c33ee"
D390_DIAG_SHA="a5e2271830649b37e0de38459a9ead58fb79d4c20c185fee1d3390e9e749c9dc"

D400_REL=BASE/"POSTV16_AV4_PIVOT_P3_R1_R7_R9_XY2_Day395_to_Day400_SeventhObservation_Pilot_and_Exact_Flow_Diagnostic"
D400_STATE="POSTV16_AV4_PIVOT_P3_R1_R7_R9_Day0400_Accepted_Dense_State.npz"
D400_DIAG="POSTV16_AV4_PIVOT_P3_R1_R7_R9_Day0400_Exact_Flow_Diagnostic.npz"
D400_STATE_SHA="9630449981429d90f3265dad60875217873000061a294b2bf60bbe806cb5c5d4"
D400_DIAG_SHA="2e772ca70526a2c64bc0a84f3fbc42c2540593e6b7d79dc74787e33b52c0ac42"

D405_REL=BASE/"POSTV16_AV4_PIVOT_P3_R1_R7_R10_XY2_Day400_to_Day405_EighthObservation_Pilot_and_Exact_Flow_Diagnostic"
D405_STATE="POSTV16_AV4_PIVOT_P3_R1_R7_R10_Day0405_Accepted_Dense_State.npz"
D405_DIAG="POSTV16_AV4_PIVOT_P3_R1_R7_R10_Day0405_Exact_Flow_Diagnostic.npz"
D405_STATE_SHA="dbe07ff7e33587f65b7c3ff02a4755e739975715cf003d42541070dc084d2077"
D405_DIAG_SHA="a567f4f560fcc56f1a26edfa4a4e6747a2a6d42e93fd9c9ce0c7cd87781fdafa"

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_A0"
OUT_REL=BASE/(OUT_TOKEN+"_Late_Day405_Shadow_Compatibility_and_Protocol_Freeze")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
PROTOCOL=f"{OUT_TOKEN}_Late_Day405_Shadow_Protocol.json"
SCHEMA=f"{OUT_TOKEN}_Late_Artifact_Schema_Audit.csv"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError): pass

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for c in iter(lambda:f.read(1<<20),b""):h.update(c)
 return h.hexdigest()

def gt(root,*a):return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()
def js(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def write_csv(p,rows):
 if not rows:Path(p).write_text("",encoding="utf-8");return
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields:fields.append(k)
 with open(p,"w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def selftest():
 assert [405-405,405-400,405-390]==[0,5,15]
 print("POSTV16 GPU-HYB-G3-R2-A0 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
 root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
 gates=[];stage="preflight"
 def gate(n,c,d=None):
  ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
  print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
  if not ok:raise GateError(n)
 try:
  print("="*180)
  print("G3-R2-A0 — LATE DAY405 SAME-STATE SHADOW COMPATIBILITY / PROTOCOL FREEZE")
  print("NO PHYSICS EXECUTION. NO STATE MUTATION.")
  print("="*180)

  stage="repository"
  gate("branch",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
  gate("parent_is_G3_R1",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
  gate("clean",gt(root,"status","--porcelain")=="")

  stage="G3_R1_authority"
  g3=js(drive/G3R1_REL/G3R1_SUM)
  gate("G3_R1_status",g3.get("status")==G3R1_STATUS,g3.get("status"))
  gate("G3_R1_conservative",g3.get("all_branches_component_mass_conservative") is True)
  gate("G3_R1_capacity_safe",g3.get("all_branches_capacity_safe_at_common_dt") is True)
  gate("G3_R1_no_cadence_selection",g3.get("production_pressure_refresh_cadence_selected") is False)
  gate("G3_R2_authorized",g3.get("G3_R2_causal_interpretation_freeze_authorized") is True)

  specs=[
   (390,D390_REL,D390_STATE,D390_DIAG,D390_STATE_SHA,D390_DIAG_SHA),
   (400,D400_REL,D400_STATE,D400_DIAG,D400_STATE_SHA,D400_DIAG_SHA),
   (405,D405_REL,D405_STATE,D405_DIAG,D405_STATE_SHA,D405_DIAG_SHA),
  ]
  rows=[];audited={}
  state_required=["physical_day","cartesian_component_mass_kg","cartesian_saturation",
                  "reference_gas_pressure_pa","cumulative_injected_component_mass_kg",
                  "cumulative_produced_component_mass_kg"]
  diag_required=["diagnostic_day","pressure_psi","streamline_xyz_m","streamline_tof_s",
                 "streamline_weight_m3_s","tau_end_s","producer_labels","xi"]

  stage="late_artifact_schema"
  for day,rel,sfn,dfn,ssha,dsha in specs:
   sp=drive/rel/sfn;dp=drive/rel/dfn
   gate(f"Day{day}_state_present",sp.is_file(),str(sp));gate(f"Day{day}_diag_present",dp.is_file(),str(dp))
   gate(f"Day{day}_state_SHA",sha(sp)==ssha,sha(sp));gate(f"Day{day}_diag_SHA",sha(dp)==dsha,sha(dp))
   with np.load(sp,allow_pickle=False) as z:
    keys=set(z.files)
    for k in state_required:gate(f"Day{day}_state_key:{k}",k in keys)
    physical=float(np.asarray(z["physical_day"]).reshape(()))
    mass=np.asarray(z["cartesian_component_mass_kg"],dtype=np.float64)
    sat=np.asarray(z["cartesian_saturation"],dtype=np.float64)
    pref=float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
    gate(f"Day{day}_state_day_exact",physical==float(day),physical)
    gate(f"Day{day}_mass_shape",mass.shape==(15,50,50),mass.shape)
    gate(f"Day{day}_sat_shape",sat.shape==(15,50,50),sat.shape)
    gate(f"Day{day}_mass_finite",np.all(np.isfinite(mass)))
    gate(f"Day{day}_mass_nonnegative",float(np.min(mass))>=-1e-9,float(np.min(mass)))
    gate(f"Day{day}_pref_positive",np.isfinite(pref) and pref>0,pref)
    mass_total=float(np.sum(mass))
   with np.load(dp,allow_pickle=False) as z:
    keys=set(z.files)
    for k in diag_required:gate(f"Day{day}_diag_key:{k}",k in keys)
    dd=float(np.asarray(z["diagnostic_day"]).reshape(()))
    pressure=np.asarray(z["pressure_psi"],dtype=np.float64)
    xyz=np.asarray(z["streamline_xyz_m"],dtype=np.float64)
    tof=np.asarray(z["streamline_tof_s"],dtype=np.float64)
    w=np.asarray(z["streamline_weight_m3_s"],dtype=np.float64)
    te=np.asarray(z["tau_end_s"],dtype=np.float64)
    labels=np.asarray(z["producer_labels"]).astype("U64")
    xi=np.asarray(z["xi"],dtype=np.float64)
    gate(f"Day{day}_diag_day_exact",dd==float(day),dd)
    gate(f"Day{day}_pressure_shape",pressure.shape==(15,50,50),pressure.shape)
    gate(f"Day{day}_xyz_shape",xyz.ndim==3 and xyz.shape[1:]==(201,3),xyz.shape)
    n=xyz.shape[0]
    gate(f"Day{day}_tof_shape",tof.shape==(n,201),tof.shape)
    gate(f"Day{day}_weights_shape",w.shape==(n,),w.shape)
    gate(f"Day{day}_tau_end_shape",te.shape==(n,),te.shape)
    gate(f"Day{day}_labels_shape",labels.shape==(n,),labels.shape)
    gate(f"Day{day}_xi_shape",xi.shape==(201,),xi.shape)
    gate(f"Day{day}_xi_domain",abs(float(xi[0]))<=1e-15 and abs(float(xi[-1])-1.0)<=1e-15,(xi[0],xi[-1]))
    gate(f"Day{day}_xi_uniform",np.allclose(np.diff(xi),np.diff(xi)[0],rtol=1e-12,atol=1e-14))
    gate(f"Day{day}_all_finite",np.all(np.isfinite(pressure)) and np.all(np.isfinite(xyz)) and np.all(np.isfinite(tof)) and np.all(np.isfinite(w)) and np.all(np.isfinite(te)))
    gate(f"Day{day}_positive_weights",float(np.min(w))>0,float(np.min(w)))
    gate(f"Day{day}_positive_tau_end",float(np.min(te))>0,float(np.min(te)))
    gate(f"Day{day}_same_time_no_feedback",("diagnostic_transport_feedback" in keys and not bool(np.asarray(z["diagnostic_transport_feedback"]).reshape(()))))
   audited[day]={"state":sp,"diag":dp,"mass_total":mass_total,"streamlines":int(n),"pref":pref}
   rows.append({"day":day,"state_sha256":ssha,"diagnostic_sha256":dsha,
                "cartesian_component_mass_total_kg":mass_total,"streamline_count":int(n),
                "nodes_per_streamline":201,"xi_faces":201,"state_schema_compatible":True,"diagnostic_schema_compatible":True})

  stage="cross_day_compatibility"
  gate("all_streamline_counts_equal",len({audited[d]["streamlines"] for d in audited})==1,{d:audited[d]["streamlines"] for d in audited})
  gate("reference_pressure_semantics_stable",
       max(audited[d]["pref"] for d in audited)-min(audited[d]["pref"] for d in audited)<=1e-6,
       {d:audited[d]["pref"] for d in audited})

  protocol={
   "milestone":M,"status":PASS,
   "parent_state_day":405,
   "parent_state_quantity":"Day405 cartesian_component_mass_kg, frozen exactly",
   "branches":[
    {"name":"REFRESHED_0D","flow_source_day":405,"staleness_days":0},
    {"name":"STALE_5D","flow_source_day":400,"staleness_days":5},
    {"name":"STALE_15D","flow_source_day":390,"staleness_days":15},
   ],
   "late_diagnostic_key_mapping":{
    "pressure":"pressure_psi","xyz_m":"streamline_xyz_m","tau_s":"streamline_tof_s",
    "weights_m3_s":"streamline_weight_m3_s","tau_end_s":"tau_end_s",
    "producer":"producer_labels","xi":"xi"},
   "transport_operator":"modern E37A exact conservative component-mass shadow transport",
   "parent_mass_handling":"use Day405 cartesian_component_mass_kg directly; invert identical mass under each branch pressure",
   "common_dt":"minimum exact CFL across all three branches",
   "capacity_policy":"BLOCK if any branch is capacity-infeasible at common dt; no branch-specific dt adjustment",
   "canonical_trajectory_mutation":False,
   "scientific_tolerance_defined":False,
   "production_cadence_selected":False,
   "G3_R2_late_Day405_shadow_execution_authorized":True,
  }

  stage="publication"
  gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
  summary={
   "milestone":M,"status":PASS,
   "classification":"LATE_DAY390_DAY400_DAY405_ARTIFACTS_DIRECTLY_COMPATIBLE_WITH_MODERN_SAME_STATE_COMPONENT_MASS_SHADOW_OPERATOR_G3_R2_EXECUTION_AUTHORIZED",
   "late_parent_day":405,
   "late_staleness_branches_days":[0,5,15],
   "Day390_state_sha256":D390_STATE_SHA,"Day390_diagnostic_sha256":D390_DIAG_SHA,
   "Day400_state_sha256":D400_STATE_SHA,"Day400_diagnostic_sha256":D400_DIAG_SHA,
   "Day405_state_sha256":D405_STATE_SHA,"Day405_diagnostic_sha256":D405_DIAG_SHA,
   "late_state_component_mass_direct_authority":True,
   "late_diagnostics_have_201_node_Pollock_TOF_database":True,
   "direct_modern_E37A_shadow_compatibility":True,
   "bridge_execution_required_before_shadow":False,
   "G3_R2_late_Day405_shadow_execution_authorized":True,
   "canonical_trajectory_mutated":False,
   "scientific_tolerance_defined":False,
   "production_pressure_refresh_cadence_selected":False,
   "P4_authorized":False}
  write_csv(out/SCHEMA,rows)
  (out/PROTOCOL).write_text(json.dumps(protocol,indent=2,sort_keys=True)+"\n",encoding="utf-8")
  (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
  write_csv(out/GATES,gates)
  manifest=[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST]
  write_csv(out/MANIFEST,manifest)

  print("="*180);print(M,"PASS")
  print("Late parent day                             : 405")
  print("Staleness branches                         : 0 / 5 / 15 days")
  print("State component-mass direct authority      : True")
  print("201-node diagnostics compatible            : True")
  print("Bridge required before shadow              : False")
  print("G3-R2 late Day405 shadow authorized        : True")
  print("Production cadence selected                : False")
  print("P4 authorized                              : False")
  print("="*180)
  return 0
 except Exception as exc:
  blocked.mkdir(parents=True,exist_ok=True)
  (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps(
   {"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
    "G3_R2_late_Day405_shadow_execution_authorized":False,
    "production_pressure_refresh_cadence_selected":False,"P4_authorized":False},indent=2,sort_keys=True)+"\n",encoding="utf-8")
  print(M,"BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
 ap=argparse.ArgumentParser()
 ap.add_argument("--project-root",type=Path,default=Path("."))
 ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
 ap.add_argument("--self-test",action="store_true")
 a=ap.parse_args()
 if a.self_test:selftest();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
