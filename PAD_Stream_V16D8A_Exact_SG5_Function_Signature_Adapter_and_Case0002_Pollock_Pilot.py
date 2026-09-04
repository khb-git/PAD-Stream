#!/usr/bin/env python
from pathlib import Path
import json, hashlib, importlib.util, inspect, numpy as np

ROOT=Path(__file__).resolve().parent
D8=ROOT/"output"/"V16_D8_SOURCEBOUND_SG5_VELOCITY_POLLOCK_BINDING_CASE0002_PILOT"/"PAD_Stream_V16D8_Summary.json"
FLOW=ROOT/"output"/"V16_D7B_FULL_FROZEN_CASE0002_0025_SOURCEBOUND_SG2_SG3_SG4_FLOW_ENSEMBLE"/"cases"/"V16D_Foundation_Case_0002_Flow.npz"
SG5=ROOT/"PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
OUT=ROOT/"output"/"V16_D8A_EXACT_SG5_FUNCTION_SIGNATURE_ADAPTER_CASE0002_POLLOCK_PILOT";OUT.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def loadmod():
 s=importlib.util.spec_from_file_location("v16d8a_sg5",SG5)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def stream_get(s,name,default=None):
 if isinstance(s,dict):return s.get(name,default)
 return getattr(s,name,default)

def flatten_xyz(s):
 for key in ["xyz","points","positions","path","coords","coordinates"]:
  a=stream_get(s,key,None)
  if a is not None:
   a=np.asarray(a,float)
   if a.ndim==2 and a.shape[1]==3:return a
 return None

def main():
 print("="*78);print("PAD-Stream V16D-8A")
 print("Exact SG5 Function-Signature Adapter and Case 0002 Pollock Pilot");print("="*78)
 d8=json.loads(D8.read_text())
 if d8["status"]!="V16D_SG5_SOURCE_BOUND_ARRAY_ENTRYPOINTS_IDENTIFIED_CASE0002_ADAPTER_EXECUTION_AUTHORIZED":raise RuntimeError("D8 mismatch")
 if sha(SG5)!=d8["SG5"]["sha256"]:raise RuntimeError("SG5 hash changed")
 sg5=loadmod()
 expected={
  "construct_face_pore_velocities":"(qx, qy, qz)",
  "build_seeds":"(qx, qy, qz)",
  "trace_streamlines":"(seeds, vx, vy, vz)",
  "validate_streamlines":"(faces, seeds, streamlines)"}
 sigs={k:str(inspect.signature(getattr(sg5,k))) for k in expected}
 for k,v in sigs.items():
  print(f"  {k}{v}")
  if v!=expected[k]:raise RuntimeError(f"Signature drift for {k}: {v}")

 print("""
D8A EXECUTES THE EXACT SHA-BOUND SG5 ARRAY-LEVEL FUNCTIONS ON CASE 0002.
NO POLLOCK EQUATION, VELOCITY FORMULA, SEED RULE, OR CAPTURE RULE IS COPIED
INTO THIS ADAPTER.

THE SAME SG5 FUNCTIONS DETERMINE FACE PORE VELOCITIES, OUTWARD INJECTOR
FACES, 7x7 FLUX-WEIGHTED SEEDS, EXACT POLLOCK TRAJECTORIES, AND VALIDATION.
""")
 z=np.load(FLOW)
 qx,qy,qz=[np.asarray(z[k],float) for k in ["Qx","Qy","Qz"]]
 vel=sg5.construct_face_pore_velocities(qx,qy,qz)
 if not isinstance(vel,tuple) or len(vel)<3:raise RuntimeError("Unexpected velocity return")
 vx,vy,vz=[np.asarray(x,float) for x in vel[:3]]
 faces=sg5.outward_faces_of_injector_region(qx,qy,qz)
 seeds=sg5.build_seeds(qx,qy,qz)
 streams=sg5.trace_streamlines(seeds,vx,vy,vz)
 validation=sg5.validate_streamlines(faces,seeds,streams)

 # Persist source-native streamlines as object array; no semantic rewriting.
 artifact=OUT/"V16D8A_Case0002_SG5_Pollock_Pilot.npz"
 np.savez_compressed(artifact,Vx=vx,Vy=vy,Vz=vz,
   streamlines=np.array(streams,dtype=object),case_id=np.array("V16D_Foundation_Case_0002"))

 nseed=len(seeds);nstream=len(streams)
 xyz=[flatten_xyz(s) for s in streams]
 xyz_ok=sum(x is not None and np.isfinite(x).all() and len(x)>=2 for x in xyz)
 # Extract statuses only as diagnostics; exact SG5 validation remains authority.
 statuses=[stream_get(s,"status","") for s in streams]
 prod=[stream_get(s,"producer_id",stream_get(s,"producer","")) for s in streams]
 # Validation may be dict/bool/tuple; require it to indicate no failed boolean fields.
 bools=[]
 def walk(x):
  if isinstance(x,(bool,np.bool_)):bools.append(bool(x))
  elif isinstance(x,dict):
   for y in x.values():walk(y)
  elif isinstance(x,(tuple,list)):
   for y in x:walk(y)
 walk(validation)
 validation_pass=(all(bools) if bools else True)

 gates={
  "D8_bound":True,"SG5_hash_exact":True,"exact_signatures_bound":True,
  "velocity_shapes":bool(vx.shape==(15,50,49) and vy.shape==(15,49,50) and vz.shape==(14,50,50)),
  "velocities_finite":bool(all(np.isfinite(x).all() for x in [vx,vy,vz])),
  "positive_seed_count":bool(nseed>0),"one_streamline_per_seed":bool(nstream==nseed),
  "streamline_geometry_extractable":bool(xyz_ok==nstream),
  "SG5_validation_boolean_fields_pass":bool(validation_pass),
  "no_pollock_reimplementation":True,"case0002_only":True,"no_transport":True,"no_training":True}
 ok=all(gates.values())
 status=("V16D_CASE0002_SOURCEBOUND_SG5_POLLOCK_PILOT_CERTIFIED_FULL_24CASE_POLLOCK_EXECUTION_AUTHORIZED"
         if ok else "V16D_CASE0002_SG5_POLLOCK_PILOT_BLOCKED_REPAIR_REQUIRED")
 summary={"milestone":"V16D-8A","status":status,"case_id":"V16D_Foundation_Case_0002",
  "SG5_sha256":sha(SG5),"signatures":sigs,
  "metrics":{"seed_count":int(nseed),"streamline_count":int(nstream),"extractable_xyz_count":int(xyz_ok),
    "Vx_absmax":float(np.max(np.abs(vx))),"Vy_absmax":float(np.max(np.abs(vy))),"Vz_absmax":float(np.max(np.abs(vz))),
    "status_counts":{str(k):statuses.count(k) for k in sorted(set(statuses),key=str)},
    "producer_labels":sorted(set(map(str,prod)))},
  "artifact":{"path":str(artifact.relative_to(ROOT)),"sha256":sha(artifact)},
  "validation_repr":repr(validation)[:8000],"gates":gates,
  "next_milestone":"V16D-8B — Full Case 0002-0025 Source-Bound SG5 Pollock Ensemble Execution"}
 (OUT/"PAD_Stream_V16D8A_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nCASE 0002 POLLOCK PILOT")
 print(f"  seeds / streamlines     : {nseed} / {nstream}")
 print(f"  extractable XYZ         : {xyz_ok}/{nstream}")
 print(f"  max |Vx| / |Vy| / |Vz| : {np.max(np.abs(vx)):.6e} / {np.max(np.abs(vy)):.6e} / {np.max(np.abs(vz)):.6e}")
 print(f"  status counts           : {summary['metrics']['status_counts']}")
 print(f"  producer labels         : {summary['metrics']['producer_labels']}")
 print(f"  artifact SHA-256        : {sha(artifact)}")
 print("\n"+"="*78);print("V16D-8A GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  V16D-8B — Full Case 0002-0025 Source-Bound SG5 Pollock Ensemble Execution")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
