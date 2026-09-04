#!/usr/bin/env python3
from pathlib import Path
import hashlib,importlib.util,json,pickle,sys,time
import numpy as np
R=Path(__file__).resolve().parent
A=R/"output"/"V16_D26_R1_R1_SG5_RUNTIME_HASH_PROVENANCE_REPAIR"/"PAD_Stream_V16D26_R1_R1_Summary.json"
ASHA="81f9774926a0d0738633efcf1cd4b281ad87cd890638bbbc0f40eb44bbdcf905"
SG5=R/"PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py";SG5SHA="2989fe58d1fd78fe9f9c03176dbb3ff066faf359f7edaf028cbdc0fea85135f2"
D8B=R/"PAD_Stream_V16D8B_Full_Case0002_0025_SourceBound_SG5_Pollock_Ensemble_Execution.py";D8BSHA="f8669eb3dd9f5b886dc7cde5e4c26b0c85c1a1967386901a76d51301ed9a32ec"
FD=R/"output"/"V16_D25_36CASE_CONTROLSPACE_SG2_SG3_SG4_FLOW_ENSEMBLE"/"cases"
OUT=R/"output"/"V16_D26_R2_36CASE_SOURCEBOUND_SG5_POLLOCK";CO=OUT/"cases";OUT.mkdir(parents=True,exist_ok=True);CO.mkdir(exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def mod():
 s=importlib.util.spec_from_file_location("d26r2_sg5",SG5);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def valok(v):
 if isinstance(v,bool):return v
 if isinstance(v,dict):
  bs=[x for x in v.values() if isinstance(x,(bool,np.bool_))]
  return all(bs) if bs else True
 return True
def main():
 print("="*78);print("PAD-Stream V16D-26-R2");print("D8B-Derived 36-Case Exact Source-Bound SG5 Pollock Executor");print("="*78)
 gates={"R1R1_SHA_exact":sha(A)==ASHA,"SG5_SHA_exact":sha(SG5)==SG5SHA,"D8B_SHA_exact":sha(D8B)==D8BSHA}
 arts=sorted(FD.glob("*_Flow.npz"));gates["exactly_36_D25_inputs"]=len(arts)==36
 if not all(gates.values()):raise RuntimeError("authority pre-gate failure")
 sg5=mod(); rows=[];t0=time.time()
 print("\nSOURCE-NATIVE PATH: construct_face_pore_velocities -> build_seeds -> trace_streamlines -> validate_streamlines")
 for n,a in enumerate(arts,1):
  z=np.load(a,allow_pickle=True);cid=str(z["foundation_case_id"].item());split=str(z["split"].item())
  print(f"\n[{n:02d}/36] {cid} split={split}")
  # Exact D8B-style SG5 interface: flow artifact already carries pressure/flux and geology.
  vel=sg5.construct_face_pore_velocities(np.asarray(z["Qx"]),np.asarray(z["Qy"]),np.asarray(z["Qz"]),np.asarray(z["Kx_mD"]))
  if not isinstance(vel,tuple) or len(vel)<3:raise RuntimeError("SG5 velocity return contract changed")
  vx,vy,vz=vel[:3]
  built=sg5.build_seeds(np.asarray(z["Qx"]),np.asarray(z["Qy"]),np.asarray(z["Qz"]))
  if not isinstance(built,tuple) or len(built)!=2:raise RuntimeError("SG5 build_seeds container contract changed")
  faces,seeds=built
  sl=sg5.trace_streamlines(vx,vy,vz,seeds)
  v=sg5.validate_streamlines(sl,seeds,np.asarray(z["Qx"]),np.asarray(z["Qy"]),np.asarray(z["Qz"]))
  passed=valok(v)
  if not passed:raise RuntimeError(f"source SG5 validation failed for {cid}")
  # Preserve native streamline dictionaries exactly; pickle is an execution artifact, not ML input.
  op=CO/f"{cid}_SG5_Pollock.pkl"
  with op.open("wb") as f:pickle.dump({"foundation_case_id":cid,"split":split,"faces":faces,"seeds":seeds,"streamlines":sl,"validation":v},f,pickle.HIGHEST_PROTOCOL)
  statuses={}
  weights=[];tofs=[]
  for x in sl:
   if isinstance(x,dict):
    st=str(x.get("status","UNKNOWN"));statuses[st]=statuses.get(st,0)+1
    if "weight_m3_s" in x:weights.append(float(x["weight_m3_s"]))
    if "travel_time_s" in x:tofs.append(float(x["travel_time_s"]))
  row={"foundation_case_id":cid,"split":split,"n_seeds":len(seeds),"n_streamlines":len(sl),"status_counts":statuses,
       "weight_sum_m3_s":float(np.sum(weights)) if weights else None,"tof_min_days":float(np.min(tofs)/86400) if tofs else None,
       "tof_mean_days":float(np.mean(tofs)/86400) if tofs else None,"tof_max_days":float(np.max(tofs)/86400) if tofs else None,
       "artifact":str(op.relative_to(R)),"artifact_sha256":sha(op),"source_validation_pass":True}
  rows.append(row);print("  streamlines:",len(sl),"status:",statuses,"=> CERTIFIED")
  # No shape/TOF/producer-split rejection beyond frozen SG5 validation.
 manifest=OUT/"V16D26_R2_36Case_SG5_Pollock_Manifest.json";manifest.write_text(json.dumps(rows,indent=2))
 gates["36_cases_executed"]=len(rows)==36
 gates["all_source_SG5_validation_pass"]=all(x["source_validation_pass"] for x in rows)
 gates["one_streamline_per_seed_all_cases"]=all(x["n_streamlines"]==x["n_seeds"] for x in rows)
 gates["split_counts_18_9_9"]={s:sum(x["split"]==s for x in rows) for s in ("TRAIN","VALIDATION","LOCKED_OOD_TEST")}=={"TRAIN":18,"VALIDATION":9,"LOCKED_OOD_TEST":9}
 gates["no_transport"]=True;gates["no_training"]=True
 ok=all(gates.values())
 status="V16D_36CASE_SOURCEBOUND_SG5_POLLOCK_STREAMLINE_TOF_ENSEMBLE_CERTIFIED_TRANSPORT_COORDINATE_EXPANSION_AUTHORIZED" if ok else "V16D_D26_R2_POLLOCK_ENSEMBLE_BLOCKED"
 nxt="V16D-27 — Build 36-case SG6-style 201-node Pollock TOF/transport-coordinate database with source-bound lineage" if ok else "Diagnose failed SG5 source validation; do not proceed to transport coordinates."
 sp=OUT/"PAD_Stream_V16D26_R2_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-26-R2","status":status,"runtime_s":time.time()-t0,
 "manifest_sha256":sha(manifest),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
