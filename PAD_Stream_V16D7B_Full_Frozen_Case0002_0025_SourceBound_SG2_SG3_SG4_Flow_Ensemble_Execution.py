#!/usr/bin/env python
from pathlib import Path
import json,csv,hashlib,importlib.util
import numpy as np

ROOT=Path(__file__).resolve().parent
D7A=ROOT/"output"/"V16_D7A_SOURCEBOUND_SG2_SG3_SG4_ADAPTER_CASE0002_PILOT"/"PAD_Stream_V16D7A_Summary.json"
D7=ROOT/"output"/"V16_D7_MULTICASE_SG2_SG3_SG4_SOURCE_AUTHENTIC_EXECUTION_BINDING_AUDIT"/"PAD_Stream_V16D7_Summary.json"
D6=ROOT/"output"/"V16_D6_FROZEN_REGISTRY_CASE0002_0025_ENSEMBLE_GEOLOGY_GENERATION_CERTIFICATION"/"PAD_Stream_V16D6_Summary.json"
CASES=ROOT/"output"/"V16_D6_FROZEN_REGISTRY_CASE0002_0025_ENSEMBLE_GEOLOGY_GENERATION_CERTIFICATION"/"cases"
OUT=ROOT/"output"/"V16_D7B_FULL_FROZEN_CASE0002_0025_SOURCEBOUND_SG2_SG3_SG4_FLOW_ENSEMBLE"
FLOW=OUT/"cases";FLOW.mkdir(parents=True,exist_ok=True)
S2=ROOT/"PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
S3=ROOT/"PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
S4=ROOT/"PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def mod(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def extract_grid_array(x,shape=(15,50,50)):
 found=[]
 def walk(v):
  if isinstance(v,np.ndarray): found.append(v)
  elif isinstance(v,(tuple,list)):
   for q in v:walk(q)
  elif isinstance(v,dict):
   for q in v.values():walk(q)
 walk(x)
 return next((np.asarray(a,float) for a in found if np.asarray(a).shape==shape),None)

def main():
 print("="*78);print("PAD-Stream V16D-7B")
 print("Full Frozen Case 0002-0025 Source-Bound SG2/SG3/SG4 Flow Ensemble Execution");print("="*78)
 a=json.loads(D7A.read_text());d7=json.loads(D7.read_text());d6=json.loads(D6.read_text())
 if a["status"]!="V16D_CASE0002_SOURCEBOUND_SG2_SG3_SG4_PILOT_CERTIFIED_FULL_24CASE_FLOW_EXECUTION_AUTHORIZED":raise RuntimeError("D7A mismatch")
 bound={x["stage"]:x["sha256"] for x in d7["sources"]}
 for st,p in [("SG2",S2),("SG3",S3),("SG4",S4)]:
  if sha(p)!=bound[st]:raise RuntimeError(f"{st} source changed")
 print("""
D7B EXECUTES THE EXACT D7A SOURCE-BOUND FLOW PATH FOR EVERY FROZEN D6 CASE.

NO CASE IS SELECTED OR REJECTED BY PRESSURE MAGNITUDE, WELL RESPONSE, OR
FLUX PATTERN. CERTIFICATION IS GOVERNING-EQUATION/CONSERVATION BASED.
A TECHNICAL FAILURE REMAINS ATTACHED TO ITS ORIGINAL CASE ID.
""")
 sg2=mod("d7b_sg2",S2);sg3=mod("d7b_sg3",S3);sg4=mod("d7b_sg4",S4)
 recs=[]
 for idx in range(2,26):
  cid=f"V16D_Foundation_Case_{idx:04d}"
  gp=CASES/f"{cid}_Geology.npz"
  rec={"case_id":cid}
  try:
   g=np.load(gp);k=np.asarray(g["Kx_mD"],float);seed=int(g["seed"])
   kx,ky,kz=sg2.build_directional_permeability(k)
   kfx,kfy,kfz=sg2.build_face_permeabilities(kx,ky,kz)
   # Execute SG2 transmissibility path as an explicit lineage check.
   _=sg2.build_transmissibilities(kfx,kfy,kfz)
   tx,ty,tz=sg3.construct_si_transmissibilities(kfx,kfy,kfz)
   ass=sg3.assemble_pressure_system(k,tx,ty,tz);A,b=ass[0],ass[1]
   sol=sg3.solve_pressure(A,b);ppa=np.asarray(sol[0] if isinstance(sol,tuple) else sol,float).reshape(-1)
   ppsi=(ppa/6894.757293168).reshape(15,50,50)
   fl=sg4.compute_face_fluxes(ppsi,tx,ty,tz);qx,qy,qz=[np.asarray(x,float) for x in fl[:3]]
   div=np.asarray(sg4.compute_flux_divergence(qx,qy,qz),float)
   ws=extract_grid_array(sg4.construct_expected_well_rates(k,ppsi))
   if ws is None:raise RuntimeError("well_source binding failed")
   rr=float(np.linalg.norm(A.dot(ppa)-b)/max(np.linalg.norm(b),1e-300))
   mm=div-ws;den=max(float(np.sum(np.abs(ws))),1e-300)
   lc=float(np.sum(np.abs(mm))/den);gc=float(abs(np.sum(div)-np.sum(ws))/den)
   fp=FLOW/f"{cid}_Flow.npz"
   np.savez_compressed(fp,Kx_mD=kx,Ky_mD=ky,Kz_mD=kz,kfx_mD=kfx,kfy_mD=kfy,kfz_mD=kfz,
      Tx_SI=tx,Ty_SI=ty,Tz_SI=tz,pressure_psi=ppsi,Qx=qx,Qy=qy,Qz=qz,
      divergence=div,well_source=ws,case_id=np.array(cid),seed=np.int64(seed))
   passed=(rr<=1e-10 and lc<=1e-8 and gc<=1e-10 and
           qx.shape==(15,50,49) and qy.shape==(15,49,50) and qz.shape==(14,50,50) and
           all(np.isfinite(x).all() for x in [ppsi,qx,qy,qz]))
   rec.update(status="CERTIFIED" if passed else "PHYSICS_GATE_FAILURE",seed=seed,sha256=sha(fp),
    p_min=float(ppsi.min()),p_mean=float(ppsi.mean()),p_max=float(ppsi.max()),
    pressure_rel_residual=rr,local_conservation_relative=lc,global_conservation_relative=gc,
    qx_absmax=float(np.max(np.abs(qx))),qy_absmax=float(np.max(np.abs(qy))),qz_absmax=float(np.max(np.abs(qz))))
  except Exception as e:
   rec.update(status="TECHNICAL_FAILURE",error=repr(e))
  recs.append(rec);print(f"[{idx-1:02d}/24] {cid} -> {rec['status']}")
 fields=sorted(set().union(*(r.keys() for r in recs)))
 man=OUT/"V16D7B_Flow_Ensemble_Manifest.csv"
 with man.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(recs)
 good=[r for r in recs if r["status"]=="CERTIFIED"]
 vals=lambda k:np.array([float(r[k]) for r in good])
 gates={
  "D7A_authorization_bound":True,"source_hashes_exact":True,
  "all_24_attempted":len(recs)==24,"all_24_certified":len(good)==24,
  "no_case_replacement":True,"no_case0001_closeness_gate":True,
  "all_pressure_residuals_pass":len(good)==24 and max(vals("pressure_rel_residual"))<=1e-10,
  "all_local_conservation_pass":len(good)==24 and max(vals("local_conservation_relative"))<=1e-8,
  "all_global_conservation_pass":len(good)==24 and max(vals("global_conservation_relative"))<=1e-10,
  "no_transport":True,"no_training":True}
 ok=all(gates.values())
 status="V16D_CASE0002_0025_SOURCEBOUND_FLOW_ENSEMBLE_CERTIFIED_READY_FOR_VELOCITY_POLLOCK_TRAVELTIME_PIPELINE" if ok else "V16D_MULTICASE_FLOW_ENSEMBLE_HAS_DOCUMENTED_FAILURES"
 summary={"milestone":"V16D-7B","status":status,"certified_count":len(good),
  "manifest":{"path":str(man.relative_to(ROOT)),"sha256":sha(man)},
  "ensemble_metrics":({k:{"min":float(vals(k).min()),"median":float(np.median(vals(k))),"max":float(vals(k).max())}
    for k in ["p_min","p_mean","p_max","pressure_rel_residual","local_conservation_relative","global_conservation_relative"]} if good else {}),
  "gates":gates,
  "next_milestone":"V16D-8 — Source-Bound SG5 Velocity/Pollock Multi-Case Execution Binding and Pilot"}
 (OUT/"PAD_Stream_V16D7B_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nENSEMBLE FLOW SUMMARY")
 print(f"  certified: {len(good)}/24")
 if good:
  print(f"  pressure mean psi min/median/max: {vals('p_mean').min():.3f} / {np.median(vals('p_mean')):.3f} / {vals('p_mean').max():.3f}")
  print(f"  max pressure residual           : {vals('pressure_rel_residual').max():.3e}")
  print(f"  max local conservation relative : {vals('local_conservation_relative').max():.3e}")
  print(f"  max global conservation relative: {vals('global_conservation_relative').max():.3e}")
 print(f"  manifest SHA-256: {sha(man)}")
 print("\n"+"="*78);print("V16D-7B GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  V16D-8 — Source-Bound SG5 Velocity/Pollock Multi-Case Execution Binding and Pilot")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
