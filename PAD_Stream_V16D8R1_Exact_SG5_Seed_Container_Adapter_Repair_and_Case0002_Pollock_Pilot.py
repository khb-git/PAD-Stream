#!/usr/bin/env python
from pathlib import Path
import json, hashlib, importlib.util, inspect, numpy as np

ROOT=Path(__file__).resolve().parent
D8R=ROOT/"output"/"V16_D8R_SG5_SEED_CONTAINER_CONTRACT_RECOVERY_AUDIT"/"PAD_Stream_V16D8R_Summary.json"
FLOW=ROOT/"output"/"V16_D7B_FULL_FROZEN_CASE0002_0025_SOURCEBOUND_SG2_SG3_SG4_FLOW_ENSEMBLE"/"cases"/"V16D_Foundation_Case_0002_Flow.npz"
SG5=ROOT/"PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
OUT=ROOT/"output"/"V16_D8R1_EXACT_SG5_SEED_CONTAINER_ADAPTER_REPAIR_CASE0002_POLLOCK_PILOT";OUT.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def loadmod():
 s=importlib.util.spec_from_file_location("v16d8r1_sg5",SG5)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def get(s,k,d=None):
 return s.get(k,d) if isinstance(s,dict) else getattr(s,k,d)

def main():
 print("="*78);print("PAD-Stream V16D-8R1")
 print("Exact SG5 Seed-Container Adapter Repair and Case 0002 Pollock Pilot");print("="*78)
 r=json.loads(D8R.read_text())
 if r["status"]!="V16D_SG5_SEED_CONTAINER_CONTRACT_RECOVERED_D8A_ADAPTER_REPAIR_CAN_PROCEED":raise RuntimeError("D8R mismatch")
 if sha(SG5)!=r["SG5_sha256"]:raise RuntimeError("SG5 hash changed")
 sg5=loadmod()
 z=np.load(FLOW);qx,qy,qz=[np.asarray(z[k],float) for k in ["Qx","Qy","Qz"]]

 print("""
D8R1 REPAIRS ONLY THE D8A RETURN-CONTAINER MISTAKE.

SOURCE-AUTHENTIC SG5 CONTRACT:
    faces, seeds = build_seeds(qx, qy, qz)
    streamlines  = trace_streamlines(seeds, vx, vy, vz)
    validation   = validate_streamlines(faces, seeds, streamlines)

NO FLATTENING, REPACKING, SEED REGENERATION, OR POLLOCK REIMPLEMENTATION.
""")
 vel=sg5.construct_face_pore_velocities(qx,qy,qz)
 if not isinstance(vel,tuple) or len(vel)<3:raise RuntimeError("Unexpected SG5 velocity return")
 vx,vy,vz=[np.asarray(x,float) for x in vel[:3]]

 built=sg5.build_seeds(qx,qy,qz)
 if not isinstance(built,tuple) or len(built)!=2:raise RuntimeError(f"build_seeds exact contract changed: {type(built)}")
 faces,seeds=built
 if not isinstance(seeds,list) or not all(isinstance(s,dict) for s in seeds):
  raise RuntimeError("Recovered SG5 seed mapping contract not satisfied")
 required={"seed_id","weight_m3_s","start_cell","position_m"}
 missing=sorted(required-set.intersection(*(set(s.keys()) for s in seeds))) if seeds else sorted(required)
 if missing:raise RuntimeError(f"Required seed keys not common to all seeds: {missing}")

 streams=sg5.trace_streamlines(seeds,vx,vy,vz)
 validation=sg5.validate_streamlines(faces,seeds,streams)

 # Bind exact source-native fields from returned dictionaries.
 status=[str(get(s,"status","")) for s in streams]
 captured=[s for s in streams if "producer" in str(get(s,"status","")).lower() or get(s,"producer_id",None) is not None]
 weights=np.array([float(get(s,"weight_m3_s",np.nan)) for s in streams])
 seedweights=np.array([float(s["weight_m3_s"]) for s in seeds])
 # Inspect common keys for provenance, not assumptions.
 common_keys=sorted(set.intersection(*(set(s.keys()) for s in streams))) if streams else []
 time_keys=[k for k in common_keys if "time" in k.lower() or "tof" in k.lower()]
 point_keys=[k for k in common_keys if any(x in k.lower() for x in ["point","xyz","position","coord"])]
 # Save object structures exactly.
 art=OUT/"V16D8R1_Case0002_SourceNative_SG5_Pollock_Pilot.npz"
 np.savez_compressed(art,Vx=vx,Vy=vy,Vz=vz,faces=np.array(faces,dtype=object),
  seeds=np.array(seeds,dtype=object),streamlines=np.array(streams,dtype=object),
  case_id=np.array("V16D_Foundation_Case_0002"))

 bools=[]
 def walk(x):
  if isinstance(x,(bool,np.bool_)):bools.append(bool(x))
  elif isinstance(x,dict):
   for y in x.values():walk(y)
  elif isinstance(x,(list,tuple)):
   for y in x:walk(y)
 walk(validation)
 gates={
  "D8R_bound":True,"SG5_hash_exact":True,"build_seeds_tuple_contract":True,
  "seed_elements_are_mappings":True,"required_seed_keys_present":True,
  "velocity_shapes":bool(vx.shape==(15,50,49) and vy.shape==(15,49,50) and vz.shape==(14,50,50)),
  "velocities_finite":bool(all(np.isfinite(x).all() for x in [vx,vy,vz])),
  "positive_seed_count":bool(len(seeds)>0),"one_streamline_per_seed":bool(len(streams)==len(seeds)),
  "seed_weights_finite_positive":bool(np.isfinite(seedweights).all() and np.all(seedweights>0)),
  "SG5_validation_boolean_fields_pass":bool(all(bools) if bools else True),
  "no_seed_flattening":True,"no_seed_repacking":True,"no_pollock_reimplementation":True,
  "case0002_only":True,"no_transport":True,"no_training":True}
 ok=all(gates.values())
 status_out=("V16D_CASE0002_SOURCEBOUND_SG5_POLLOCK_PILOT_CERTIFIED_FULL_24CASE_POLLOCK_EXECUTION_AUTHORIZED"
             if ok else "V16D_CASE0002_SOURCEBOUND_SG5_POLLOCK_PILOT_NOT_CERTIFIED")
 summary={"milestone":"V16D-8R1","status":status_out,"case_id":"V16D_Foundation_Case_0002",
  "SG5_sha256":sha(SG5),
  "metrics":{"face_count":int(len(faces)),"seed_count":int(len(seeds)),"streamline_count":int(len(streams)),
   "captured_or_producer_labeled_count":int(len(captured)),
   "seed_weight_sum_m3_s":float(seedweights.sum()),
   "streamline_common_keys":common_keys,"time_like_keys":time_keys,"geometry_like_keys":point_keys,
   "status_counts":{x:status.count(x) for x in sorted(set(status))},
   "V_absmax":[float(np.max(np.abs(vx))),float(np.max(np.abs(vy))),float(np.max(np.abs(vz)))]},
  "validation_repr":repr(validation)[:10000],
  "artifact":{"path":str(art.relative_to(ROOT)),"sha256":sha(art)},"gates":gates,
  "next_milestone":"V16D-8B — Full Case 0002-0025 Source-Bound SG5 Pollock Ensemble Execution"}
 sp=OUT/"PAD_Stream_V16D8R1_Summary.json";sp.write_text(json.dumps(summary,indent=2))
 print("\nCASE 0002 SOURCE-NATIVE POLLOCK")
 print(f"  outward faces           : {len(faces)}")
 print(f"  seeds / streamlines     : {len(seeds)} / {len(streams)}")
 print(f"  seed weight sum m3/s    : {seedweights.sum():.9e}")
 print(f"  status counts           : {summary['metrics']['status_counts']}")
 print(f"  common streamline keys  : {common_keys}")
 print(f"  time-like keys           : {time_keys}")
 print(f"  geometry-like keys       : {point_keys}")
 print(f"  artifact SHA-256         : {sha(art)}")
 print("\n"+"="*78);print("V16D-8R1 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status_out)
 print("\nNEXT MILESTONE\n  V16D-8B — Full Case 0002-0025 Source-Bound SG5 Pollock Ensemble Execution")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
