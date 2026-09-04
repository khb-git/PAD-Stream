#!/usr/bin/env python
from pathlib import Path
import csv,json,hashlib,numpy as np

ROOT=Path(__file__).resolve().parent
BASE=ROOT/"output"/"V16_D7B_FULL_FROZEN_CASE0002_0025_SOURCEBOUND_SG2_SG3_SG4_FLOW_ENSEMBLE"
FLOW=BASE/"cases"
MAN=BASE/"V16D7B_Flow_Ensemble_Manifest.csv"
OUT=ROOT/"output"/"V16_D7BR_JSON_SERIALIZATION_REPAIR_EXISTING_FLOW_ENSEMBLE_CERTIFICATION"
OUT.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def py(v):
 if isinstance(v,np.generic): return v.item()
 if isinstance(v,np.ndarray): return v.tolist()
 if isinstance(v,dict): return {str(k):py(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)): return [py(x) for x in v]
 return v

def f(x): return float(x)

def main():
 print("="*78);print("PAD-Stream V16D-7BR")
 print("JSON Serialization Repair and Existing Flow Ensemble Certification");print("="*78)
 print("""
D7BR DOES NOT RERUN SG2/SG3/SG4.

D7B ALREADY EXECUTED ALL 24 CASES AND WROTE THEIR FLOW ARTIFACTS + MANIFEST.
THE FAILURE OCCURRED ONLY WHILE JSON-ENCODING A NUMPY BOOL_ IN THE SUMMARY.

D7BR AUDITS THE EXISTING D7B ARTIFACTS/MANIFEST, RECONSTRUCTS THE SUMMARY
WITH NATIVE PYTHON SCALARS, AND CERTIFIES ONLY IF ALL ORIGINAL PHYSICS GATES
ARE SATISFIED. NO CASE IS REPLACED OR RECOMPUTED.
""")
 if not MAN.exists(): raise RuntimeError("D7B manifest missing")
 rows=list(csv.DictReader(MAN.open()))
 expected=[f"V16D_Foundation_Case_{i:04d}" for i in range(2,26)]
 ids=[r["case_id"] for r in rows]
 certified=[r for r in rows if r["status"]=="CERTIFIED"]
 artifact_ok=True; shape_ok=True; finite_ok=True; hash_inventory=[]
 for cid in expected:
  fp=FLOW/f"{cid}_Flow.npz"
  if not fp.exists(): artifact_ok=False;continue
  z=np.load(fp)
  shape_ok &= (z["pressure_psi"].shape==(15,50,50) and z["Qx"].shape==(15,50,49)
               and z["Qy"].shape==(15,49,50) and z["Qz"].shape==(14,50,50))
  finite_ok &= all(np.isfinite(z[k]).all() for k in ["pressure_psi","Qx","Qy","Qz","divergence","well_source"])
  hash_inventory.append({"case_id":cid,"sha256":sha(fp)})
 rr=np.array([f(r["pressure_rel_residual"]) for r in certified])
 lc=np.array([f(r["local_conservation_relative"]) for r in certified])
 gc=np.array([f(r["global_conservation_relative"]) for r in certified])
 pm=np.array([f(r["p_mean"]) for r in certified])
 gates={
  "existing_D7B_manifest_present":True,
  "exact_24_manifest_rows":len(rows)==24,
  "case_ids_exact_and_ordered":ids==expected,
  "all_24_original_status_certified":len(certified)==24,
  "all_24_existing_flow_artifacts_present":artifact_ok and len(hash_inventory)==24,
  "existing_artifact_shapes_valid":bool(shape_ok),
  "existing_artifacts_finite":bool(finite_ok),
  "all_pressure_residuals_pass":bool(len(rr)==24 and rr.max()<=1e-10),
  "all_local_conservation_pass":bool(len(lc)==24 and lc.max()<=1e-8),
  "all_global_conservation_pass":bool(len(gc)==24 and gc.max()<=1e-10),
  "no_flow_rerun":True,"no_case_replacement":True,"no_transport":True,"no_training":True,
  "json_native_scalar_repair":True}
 ok=all(gates.values())
 status=("V16D_CASE0002_0025_SOURCEBOUND_FLOW_ENSEMBLE_CERTIFIED_READY_FOR_VELOCITY_POLLOCK_TRAVELTIME_PIPELINE"
         if ok else "V16D_D7B_EXISTING_FLOW_ENSEMBLE_REPAIR_AUDIT_FAILED")
 summary={"milestone":"V16D-7BR","repair_of":"V16D-7B",
  "failure_class":"POST_EXECUTION_SUMMARY_SERIALIZATION_ONLY",
  "status":status,"certified_count":int(len(certified)),
  "original_manifest":{"path":str(MAN.relative_to(ROOT)),"sha256":sha(MAN)},
  "artifact_hashes":hash_inventory,
  "ensemble_metrics":{
   "pressure_mean_psi":{"min":float(pm.min()),"median":float(np.median(pm)),"max":float(pm.max())},
   "pressure_relative_residual":{"max":float(rr.max())},
   "local_conservation_relative":{"max":float(lc.max())},
   "global_conservation_relative":{"max":float(gc.max())}},
  "gates":gates,
  "next_milestone":"V16D-8 — Source-Bound SG5 Velocity/Pollock Multi-Case Execution Binding and Pilot"}
 summary=py(summary)
 # Prove serialization before writing authority.
 payload=json.dumps(summary,indent=2)
 sp=OUT/"PAD_Stream_V16D7BR_Summary.json";sp.write_text(payload)
 print("\nEXISTING D7B ENSEMBLE")
 print(f"  manifest rows/certified : {len(rows)} / {len(certified)}")
 print(f"  flow artifacts present  : {len(hash_inventory)}/24")
 print(f"  pressure mean psi min/median/max: {pm.min():.3f} / {np.median(pm):.3f} / {pm.max():.3f}")
 print(f"  max pressure residual   : {rr.max():.3e}")
 print(f"  max local conservation  : {lc.max():.3e}")
 print(f"  max global conservation : {gc.max():.3e}")
 print(f"  original manifest SHA-256: {sha(MAN)}")
 print(f"  repaired summary SHA-256 : {sha(sp)}")
 print("\n"+"="*78);print("V16D-7BR GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  V16D-8 — Source-Bound SG5 Velocity/Pollock Multi-Case Execution Binding and Pilot")
 if not ok: raise SystemExit(2)
if __name__=="__main__":main()
