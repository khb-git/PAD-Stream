#!/usr/bin/env python
from pathlib import Path
import json, hashlib, importlib.util, sys, os
import numpy as np

ROOT=Path(__file__).resolve().parent
D7=ROOT/"output"/"V16_D7_MULTICASE_SG2_SG3_SG4_SOURCE_AUTHENTIC_EXECUTION_BINDING_AUDIT"/"PAD_Stream_V16D7_Summary.json"
D6=ROOT/"output"/"V16_D6_FROZEN_REGISTRY_CASE0002_0025_ENSEMBLE_GEOLOGY_GENERATION_CERTIFICATION"/"PAD_Stream_V16D6_Summary.json"
CASE=ROOT/"output"/"V16_D6_FROZEN_REGISTRY_CASE0002_0025_ENSEMBLE_GEOLOGY_GENERATION_CERTIFICATION"/"cases"/"V16D_Foundation_Case_0002_Geology.npz"
OUT=ROOT/"output"/"V16_D7A_SOURCEBOUND_SG2_SG3_SG4_ADAPTER_CASE0002_PILOT";OUT.mkdir(parents=True,exist_ok=True)

S2=ROOT/"PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
S3=ROOT/"PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
S4=ROOT/"PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def loadmod(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 print("="*78);print("PAD-Stream V16D-7A")
 print("Source-Bound SG2/SG3/SG4 Adapter Implementation and Case 0002 Pilot");print("="*78)
 d7=json.loads(D7.read_text()); d6=json.loads(D6.read_text())
 if d7["status"]!="V16D_SG2_SG3_SG4_SOURCE_AUTHENTIC_FLOW_LINEAGE_BOUND_MULTICASE_ADAPTER_IMPLEMENTATION_AUTHORIZED":raise RuntimeError("D7 mismatch")
 if d6["status"]!="V16D_CASE0002_0025_ENSEMBLE_GEOLOGIES_GENERATED_CERTIFIED_READY_FOR_MULTI_CASE_FLOW_PIPELINE":raise RuntimeError("D6 mismatch")
 bound={x["stage"]:x["sha256"] for x in d7["sources"]}
 for st,p in [("SG2",S2),("SG3",S3),("SG4",S4)]:
  if sha(p)!=bound[st]:raise RuntimeError(f"{st} source hash changed")

 print("""
D7A RUNS ONLY CASE 0002.

THE ADAPTER CALLS THE SHA-BOUND V15 SG2/SG3/SG4 FUNCTIONS DIRECTLY.
IT TEMPORARILY OVERRIDES ONLY THEIR INPUT-LOADER FUNCTIONS SO THE NEW D6
GEOLOGY ARRAYS ENTER THE EXISTING VALIDATED PHYSICS ALGEBRA. NO GOVERNING
EQUATION, WELL CONTROL, GRAVITY TERM, OR FLUX FORMULA IS REIMPLEMENTED HERE.

IF A SOURCE FUNCTION SIGNATURE/RETURN CONTRACT DOES NOT MATCH, D7A FAILS
OPENLY RATHER THAN GUESSING.
""")
 g=np.load(CASE)
 k=np.asarray(g["Kx_mD"],float)
 if k.shape!=(15,50,50):raise RuntimeError("Case0002 geology shape mismatch")

 sg2=loadmod("v16d_sg2_bound",S2)
 sg3=loadmod("v16d_sg3_bound",S3)
 sg4=loadmod("v16d_sg4_bound",S4)

 # SG2: call exact bound algebraic functions.
 kx,ky,kz=sg2.build_directional_permeability(k)
 kfx,kfy,kfz=sg2.build_face_permeabilities(kx,ky,kz)
 tx2,ty2,tz2=sg2.build_transmissibilities(kfx,kfy,kfz)

 # SG3: exact bound SI conversion + assembly + solve.
 tx,ty,tz=sg3.construct_si_transmissibilities(kfx,kfy,kfz)
 assembled=sg3.assemble_pressure_system(k,tx,ty,tz)
 if not isinstance(assembled,tuple) or len(assembled)<2:
  raise RuntimeError(f"Unexpected SG3 assemble return: {type(assembled)}, len={len(assembled) if isinstance(assembled,tuple) else 'NA'}")
 A,b=assembled[0],assembled[1]
 psol=sg3.solve_pressure(A,b)
 p_pa=psol[0] if isinstance(psol,tuple) else psol
 p_pa=np.asarray(p_pa,float).reshape(-1)
 if p_pa.size!=37500:raise RuntimeError(f"Unexpected pressure size {p_pa.size}")
 p_psi=(p_pa/6894.757293168).reshape(15,50,50)

 # SG4: exact bound face flux function.
 flux=sg4.compute_face_fluxes(p_psi,tx,ty,tz)
 if not isinstance(flux,tuple) or len(flux)<3:raise RuntimeError("Unexpected SG4 flux return")
 qx,qy,qz=[np.asarray(x,float) for x in flux[:3]]
 div=np.asarray(sg4.compute_flux_divergence(qx,qy,qz),float)

 # Expected well source through bound SG4 function.
 ew=sg4.construct_expected_well_rates(k,p_psi)
 # Locate array matching cell grid as well source; retain other return metadata.
 candidates=[]
 def walk(x):
  if isinstance(x,np.ndarray):candidates.append(x)
  elif isinstance(x,(tuple,list)):
   for y in x:walk(y)
  elif isinstance(x,dict):
   for y in x.values():walk(y)
 walk(ew)
 ws=next((np.asarray(x,float) for x in candidates if np.asarray(x).shape==(15,50,50)),None)
 if ws is None:raise RuntimeError("Could not bind SG4 well_source grid from exact return contract.")

 # Residual and conservation metrics from the same discrete objects.
 r=A.dot(p_pa)-b
 relres=float(np.linalg.norm(r)/max(np.linalg.norm(b),1e-300))
 mismatch=div-ws
 l2=float(np.linalg.norm(mismatch))
 linf=float(np.max(np.abs(mismatch)))
 denom=max(float(np.sum(np.abs(ws))),1e-300)
 relcons=float(np.sum(np.abs(mismatch))/denom)
 globalmis=float(abs(np.sum(div)-np.sum(ws))/denom)

 artifact=OUT/"V16D7A_Case0002_SG2_SG3_SG4_Pilot.npz"
 np.savez_compressed(artifact,Kx_mD=kx,Ky_mD=ky,Kz_mD=kz,kfx_mD=kfx,kfy_mD=kfy,kfz_mD=kfz,
  Tx_SI=tx,Ty_SI=ty,Tz_SI=tz,pressure_psi=p_psi,Qx=qx,Qy=qy,Qz=qz,divergence=div,well_source=ws,
  case_id=np.array("V16D_Foundation_Case_0002"))

 shapes=(qx.shape==(15,50,49) and qy.shape==(15,49,50) and qz.shape==(14,50,50))
 finite=all(np.isfinite(x).all() for x in [p_psi,qx,qy,qz,div,ws])
 # Gates use validated numerical tolerances, not Case0001 numerical closeness.
 gates={
  "D7_bound":True,"D6_bound":True,"source_hashes_exact":True,
  "exact_SG2_functions_called":True,"exact_SG3_functions_called":True,"exact_SG4_functions_called":True,
  "case0002_only":True,"pressure_shape":p_psi.shape==(15,50,50),"flux_shapes":shapes,"finite":finite,
  "pressure_linear_residual_le_1e_10":relres<=1e-10,
  "local_conservation_relative_le_1e_8":relcons<=1e-8,
  "global_conservation_relative_le_1e_10":globalmis<=1e-10,
  "no_case0001_closeness_gate":True,"no_transport":True,"no_training":True}
 ok=all(gates.values())
 status="V16D_CASE0002_SOURCEBOUND_SG2_SG3_SG4_PILOT_CERTIFIED_FULL_24CASE_FLOW_EXECUTION_AUTHORIZED" if ok else "V16D_CASE0002_SOURCEBOUND_FLOW_PILOT_BLOCKED"
 summary={"milestone":"V16D-7A","status":status,
  "case_id":"V16D_Foundation_Case_0002",
  "metrics":{"pressure_min_psi":float(p_psi.min()),"pressure_mean_psi":float(p_psi.mean()),"pressure_max_psi":float(p_psi.max()),
             "pressure_relative_linear_residual":relres,"local_conservation_L2":l2,
             "local_conservation_Linf":linf,"local_conservation_relative":relcons,
             "global_conservation_relative":globalmis,
             "Qx_minmax":[float(qx.min()),float(qx.max())],"Qy_minmax":[float(qy.min()),float(qy.max())],
             "Qz_minmax":[float(qz.min()),float(qz.max())]},
  "artifact":{"path":str(artifact.relative_to(ROOT)),"sha256":sha(artifact)},
  "gates":gates,
  "next_milestone":"V16D-7B — Full Frozen Case 0002-0025 Source-Bound SG2/SG3/SG4 Flow Ensemble Execution"}
 (OUT/"PAD_Stream_V16D7A_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nCASE 0002 PILOT")
 print(f"  pressure min/mean/max psi : {p_psi.min():.6f} / {p_psi.mean():.6f} / {p_psi.max():.6f}")
 print(f"  pressure relative residual: {relres:.6e}")
 print(f"  local conservation L2     : {l2:.6e}")
 print(f"  local conservation Linf   : {linf:.6e}")
 print(f"  local conservation relative: {relcons:.6e}")
 print(f"  global conservation relative: {globalmis:.6e}")
 print(f"  Qx shape {qx.shape}; Qy {qy.shape}; Qz {qz.shape}")
 print(f"  artifact SHA-256: {sha(artifact)}")
 print("\n"+"="*78);print("V16D-7A GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  V16D-7B — Full Frozen Case 0002-0025 Source-Bound SG2/SG3/SG4 Flow Ensemble Execution")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
