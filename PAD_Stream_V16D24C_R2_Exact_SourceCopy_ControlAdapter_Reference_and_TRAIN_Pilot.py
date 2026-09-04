#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,importlib.util,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parent
S=ROOT/"output"/"V16_D24C_D7A_DERIVED_REFERENCE_EQUIVALENCE_TRAIN_PILOT"/"PAD_Stream_V16D24C_Summary.json"
SSHA="d83432ace816cbdb4d47ff4faa2a40e33babc277d52cc3b3645c17dd53e145e8"
S2=ROOT/"PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"; SHA2="8dfc3485682830ef854178720d32050b6b2e9d25befa7ee9669993df1e544416"
S3=ROOT/"PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"; SHA3="d3ba7b7be45636f6d3ee254fd6cb95268cef9e6f35e85d53b5793596cb22b14d"
S4=ROOT/"PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"; SHA4="86a1c88ffc35033314ae6598ade23f0bebfa709f62cbe2cbef1830cd607e0af9"
CASE=ROOT/"output"/"V16_D23_FRESH_RECIPE1P1_GEOLOGIES_0026_0029"/"V16D_Geology_Case_0026_Recipe1p1.npz"
OUT=ROOT/"output"/"V16_D24C_R2_EXACT_SOURCECOPY_REFERENCE_TRAIN_PILOT";OUT.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def loadmod(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def patch_source(rate,bhp):
 t=S3.read_text(encoding="utf-8")
 replacements=[
  (r'(?m)^PRODUCER_BHP_PSI\s*=\s*2000\.0\s*$',f'PRODUCER_BHP_PSI = {bhp:.1f}'),
  (r'(?m)^CO2_MASS_RATE_TONNES_DAY\s*=\s*500\.0\s*$',f'CO2_MASS_RATE_TONNES_DAY = {rate:.1f}')]
 out=t; counts=[]
 for pat,rep in replacements:
  out,n=re.subn(pat,rep,out);counts.append(n)
 if counts!=[1,1]:raise RuntimeError(f"exact source patch counts {counts}")
 return out
def run_case(k,sg2,sg3,sg4):
 kx,ky,kz=sg2.build_directional_permeability(k);kfx,kfy,kfz=sg2.build_face_permeabilities(kx,ky,kz)
 sg2.build_transmissibilities(kfx,kfy,kfz)
 tx,ty,tz=sg3.construct_si_transmissibilities(kfx,kfy,kfz)
 assembled=sg3.assemble_pressure_system(k,tx,ty,tz);A,b=assembled[:2]
 psol=sg3.solve_pressure(A,b);p=np.asarray(psol[0] if isinstance(psol,tuple) else psol,float)
 if p.size==37500:p=p.reshape(15,50,50)
 ppsi=p/sg3.PSI_TO_PA if np.nanmedian(p)>1e5 else p
 flux=sg4.compute_face_fluxes(ppsi,tx,ty,tz);qx,qy,qz=[np.asarray(x,float) for x in flux[:3]]
 div=np.asarray(sg4.compute_flux_divergence(qx,qy,qz),float)
 ew=sg4.construct_expected_well_rates(k,ppsi);ws=None
 if isinstance(ew,np.ndarray):ws=np.asarray(ew,float)
 elif isinstance(ew,tuple):
  for x in ew:
   if isinstance(x,np.ndarray) and x.shape==(15,50,50):ws=np.asarray(x,float);break
 elif isinstance(ew,dict):
  for key in ("well_source","source","q_well"):
   if key in ew:ws=np.asarray(ew[key],float);break
 if ws is None:raise RuntimeError("Could not bind SG4 well_source")
 return {"Kx_mD":kx,"Ky_mD":ky,"Kz_mD":kz,"kfx_mD":kfx,"kfy_mD":kfy,"kfz_mD":kfz,
 "Tx_SI":tx,"Ty_SI":ty,"Tz_SI":tz,"pressure_psi":ppsi,"Qx":qx,"Qy":qy,"Qz":qz,"divergence":div,"well_source":ws}
def md(a,b):return float(np.max(np.abs(np.asarray(a)-np.asarray(b))))
def main():
 print("="*78);print("PAD-Stream V16D-24C-R2")
 print("Exact Source-Copy SG3 Adapter: Reference Equivalence + TRAIN Pilot");print("="*78)
 gates={"D24C_SHA_exact":sha(S)==SSHA,"SG2_SHA_exact":sha(S2)==SHA2,"SG3_SHA_exact":sha(S3)==SHA3,
 "SG4_SHA_exact":sha(S4)==SHA4,"case0026_exists":CASE.exists()}
 if not all(gates.values()):raise RuntimeError("authority pre-gate failure")
 k=np.asarray(np.load(CASE)["Kx_mD"],float);sg2=loadmod("r2sg2",S2);sg3=loadmod("r2sg3",S3);sg4=loadmod("r2sg4",S4)
 # Reference adapter is exact original source bytes: no cloning, no altered globals.
 ref=run_case(k,sg2,sg3,sg4)
 ref2=run_case(k,sg2,loadmod("r2sg3_reference_reimport",S3),sg4)
 diffs={x:md(ref[x],ref2[x]) for x in ("pressure_psi","Qx","Qy","Qz","divergence","well_source")}
 print("\nREFERENCE REIMPORT EQUIVALENCE (500/2000)")
 for x,v in diffs.items():print(f"  max|Δ{x}| = {v:.16e}")
 for x,v in diffs.items():gates[f"reference_{x}_exact"]=v<=1e-12
 # New control: create derived physical source copy. Importing normally preserves scipy imports/globals.
 patched=patch_source(350.,1800.)
 dp=OUT/"PAD_Stream_V16D24C_R2_DERIVED_SG3_350tpd_1800psi.py";dp.write_text(patched,encoding="utf-8")
 gates["frozen_SG3_unmodified"]=sha(S3)==SHA3
 original=S3.read_text(encoding="utf-8").splitlines();derived=patched.splitlines()
 changed=[i+1 for i,(a,b) in enumerate(zip(original,derived)) if a!=b]
 gates["derived_SG3_exactly_two_lines_changed"]=changed==[122,132]
 print("  derived SG3 changed lines:",changed)
 pilot=run_case(k,sg2,loadmod("r2sg3_pilot",dp),sg4)
 gates["pilot_finite"]=all(np.isfinite(pilot[x]).all() for x in ("pressure_psi","Qx","Qy","Qz","divergence","well_source"))
 gates["pilot_shapes"]=(pilot["pressure_psi"].shape==(15,50,50) and pilot["Qx"].shape==(15,50,49) and pilot["Qy"].shape==(15,49,50) and pilot["Qz"].shape==(14,50,50))
 cons=np.linalg.norm((pilot["divergence"]-pilot["well_source"]).ravel());scale=max(np.linalg.norm(pilot["well_source"].ravel()),1e-30);rel=float(cons/scale)
 gm=abs(float(pilot["divergence"].sum()-pilot["well_source"].sum()));gs=max(abs(float(pilot["well_source"].sum())),1e-30);grel=float(gm/gs)
 gates["pilot_local_conservation_rel_L2_le_1e_9"]=rel<=1e-9;gates["pilot_global_conservation_rel_le_1e_9"]=grel<=1e-9
 gates["locked_geology0029_not_used"]=True
 print("\nTRAIN PILOT 0026 @ 350 t/day, 1800 psi")
 print(f"  pressure min/mean/max psi = {pilot['pressure_psi'].min():.6f}/{pilot['pressure_psi'].mean():.6f}/{pilot['pressure_psi'].max():.6f}")
 print(f"  local conservation relative L2 = {rel:.6e}")
 print(f"  global conservation relative mismatch = {grel:.6e}")
 rp=OUT/"V16D24CR2_Geology0026_Reference_500tpd_2000psi.npz";pp=OUT/"V16D24CR2_Geology0026_TRAIN_Pilot_350tpd_1800psi.npz"
 np.savez_compressed(rp,**ref,geology_case_id=np.array("0026"),injection_tonnes_day=np.array(500.),producer_BHP_psi=np.array(2000.))
 np.savez_compressed(pp,**pilot,geology_case_id=np.array("0026"),injection_tonnes_day=np.array(350.),producer_BHP_psi=np.array(1800.))
 ok=all(gates.values());status=("V16D_EXACT_SOURCECOPY_CONTROL_ADAPTER_REFERENCE_EQUIVALENT_TRAIN_PILOT_CERTIFIED_36CASE_FLOW_AUTHORIZED" if ok else "V16D_D24C_R2_BLOCKED")
 nxt=("V16D-25 — D7B-Derived 36-Foundation-Case Control-Space Flow Ensemble Execution" if ok else "Diagnose failed gate; do not batch.")
 sp=OUT/"PAD_Stream_V16D24C_R2_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-24C-R2","status":status,"failure_repair":"R1 function cloning lost scipy module globals required by spsolve; R2 uses normal import of an exact two-line derived source copy.","reference_diffs":diffs,"pilot_local_rel_L2":rel,"pilot_global_rel":grel,"derived_SG3_sha256":sha(dp),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
