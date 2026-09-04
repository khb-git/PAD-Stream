#!/usr/bin/env python3
from pathlib import Path
import hashlib, importlib.util, json, sys, types
import numpy as np

ROOT=Path(__file__).resolve().parent
S=ROOT/"output"/"V16_D24C_D7A_DERIVED_REFERENCE_EQUIVALENCE_TRAIN_PILOT"/"PAD_Stream_V16D24C_Summary.json"
SSHA="d83432ace816cbdb4d47ff4faa2a40e33babc277d52cc3b3645c17dd53e145e8"
S2=ROOT/"PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
S3=ROOT/"PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
S4=ROOT/"PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SHA2="8dfc3485682830ef854178720d32050b6b2e9d25befa7ee9669993df1e544416"
SHA3="d3ba7b7be45636f6d3ee254fd6cb95268cef9e6f35e85d53b5793596cb22b14d"
SHA4="86a1c88ffc35033314ae6598ade23f0bebfa709f62cbe2cbef1830cd607e0af9"
CASE=ROOT/"output"/"V16_D23_FRESH_RECIPE1P1_GEOLOGIES_0026_0029"/"V16D_Geology_Case_0026_Recipe1p1.npz"
OUT=ROOT/"output"/"V16_D24C_R1_REFERENCE_EQUIVALENCE_TRAIN_PILOT";OUT.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def loadmod(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def clone_with_controls(base,rate,bhp):
 # Preserve imported SG3 functions and globals; override only the two exact bound globals
 # and recompute their immediate derived globals that frozen functions consume.
 m=types.ModuleType(f"sg3_control_{rate}_{bhp}")
 m.__dict__.update(base.__dict__)
 m.PRODUCER_BHP_PSI=float(bhp)
 m.PRODUCER_BHP_PA=m.PRODUCER_BHP_PSI*m.PSI_TO_PA
 m.CO2_MASS_RATE_TONNES_DAY=float(rate)
 # Recompute frozen source's declared derived rate chain from its own constants.
 m.CO2_MASS_RATE_KG_S=m.CO2_MASS_RATE_TONNES_DAY*m.TONNE_TO_KG/m.DAY_TO_S
 m.CO2_RESERVOIR_RATE_M3_S=m.CO2_MASS_RATE_KG_S/m.CO2_DENSITY_KG_M3
 m.CO2_RESERVOIR_RATE_M3_DAY=m.CO2_RESERVOIR_RATE_M3_S*m.DAY_TO_S
 # Functions retain original __globals__, so make a controlled function clone whose
 # code/defaults are unchanged but globals are this namespace.
 for n,v in list(base.__dict__.items()):
  if isinstance(v,types.FunctionType):
   m.__dict__[n]=types.FunctionType(v.__code__,m.__dict__,n,v.__defaults__,v.__closure__)
   m.__dict__[n].__kwdefaults__=v.__kwdefaults__
 return m

def run_case(k,sg2,sg3,sg4):
 kx,ky,kz=sg2.build_directional_permeability(k)
 kfx,kfy,kfz=sg2.build_face_permeabilities(kx,ky,kz)
 _=sg2.build_transmissibilities(kfx,kfy,kfz)
 tx,ty,tz=sg3.construct_si_transmissibilities(kfx,kfy,kfz)
 assembled=sg3.assemble_pressure_system(k,tx,ty,tz)
 if not isinstance(assembled,tuple) or len(assembled)<2:raise RuntimeError("Unexpected SG3 assemble return")
 A,b=assembled[:2]
 psol=sg3.solve_pressure(A,b)
 p=np.asarray(psol[0] if isinstance(psol,tuple) else psol,float)
 if p.size==15*50*50:p=p.reshape(15,50,50)
 # Frozen D7A semantics: SG3 solve is SI pressure, convert to psi if needed using source constant.
 # D7A evidence indicates p_psi exists; robustly infer from magnitude, not by fitting.
 ppsi=p/sg3.PSI_TO_PA if np.nanmedian(p)>1e5 else p
 flux=sg4.compute_face_fluxes(ppsi,tx,ty,tz)
 if not isinstance(flux,tuple) or len(flux)<3:raise RuntimeError("Unexpected SG4 flux return")
 qx,qy,qz=[np.asarray(x,float) for x in flux[:3]]
 div=np.asarray(sg4.compute_flux_divergence(qx,qy,qz),float)
 ew=sg4.construct_expected_well_rates(k,ppsi)
 ws=None
 if isinstance(ew,np.ndarray):ws=np.asarray(ew,float)
 elif isinstance(ew,tuple):
  for x in ew:
   if isinstance(x,np.ndarray) and x.shape==(15,50,50):ws=np.asarray(x,float);break
 elif isinstance(ew,dict):
  for key in ("well_source","source","q_well"):
   if key in ew:ws=np.asarray(ew[key],float);break
 if ws is None:raise RuntimeError("Could not bind SG4 well_source return contract")
 return dict(Kx_mD=kx,Ky_mD=ky,Kz_mD=kz,kfx_mD=kfx,kfy_mD=kfy,kfz_mD=kfz,
             Tx_SI=tx,Ty_SI=ty,Tz_SI=tz,pressure_psi=ppsi,Qx=qx,Qy=qy,Qz=qz,
             divergence=div,well_source=ws)

def maxdiff(a,b):return float(np.max(np.abs(np.asarray(a)-np.asarray(b))))

def main():
 print("="*78);print("PAD-Stream V16D-24C-R1")
 print("Exact D7A-Derived Reference Equivalence + Geology0026 TRAIN Pilot");print("="*78)
 gates={"D24C_SHA_exact":sha(S)==SSHA,"SG2_SHA_exact":sha(S2)==SHA2,
        "SG3_SHA_exact":sha(S3)==SHA3,"SG4_SHA_exact":sha(S4)==SHA4,"case0026_exists":CASE.exists()}
 if not all(gates.values()):raise RuntimeError("authority pre-gate failure")
 g=np.load(CASE);k=np.asarray(g["Kx_mD"],float)
 sg2=loadmod("d24cr1_sg2",S2);sg3=loadmod("d24cr1_sg3",S3);sg4=loadmod("d24cr1_sg4",S4)

 print("\nREFERENCE EQUIVALENCE: geology0026 @ 500 t/day, 2000 psi")
 ref=run_case(k,sg2,sg3,sg4)
 adapted=run_case(k,sg2,clone_with_controls(sg3,500.,2000.),sg4)
 diffs={x:maxdiff(ref[x],adapted[x]) for x in ("pressure_psi","Qx","Qy","Qz","divergence","well_source")}
 for x,v in diffs.items():print(f"  max|Δ{x}| = {v:.16e}")
 gates["reference_pressure_exact"]=diffs["pressure_psi"]<=1e-12
 gates["reference_Qx_exact"]=diffs["Qx"]<=1e-12
 gates["reference_Qy_exact"]=diffs["Qy"]<=1e-12
 gates["reference_Qz_exact"]=diffs["Qz"]<=1e-12
 gates["reference_divergence_exact"]=diffs["divergence"]<=1e-12
 gates["reference_well_source_exact"]=diffs["well_source"]<=1e-12

 print("\nTRAIN PILOT: geology0026 @ 350 t/day, 1800 psi")
 pilot_sg3=clone_with_controls(sg3,350.,1800.)
 pilot=run_case(k,sg2,pilot_sg3,sg4)
 finite=all(np.isfinite(pilot[x]).all() for x in ("pressure_psi","Qx","Qy","Qz","divergence","well_source"))
 gates["pilot_finite"]=finite
 gates["pilot_pressure_shape"]=pilot["pressure_psi"].shape==(15,50,50)
 gates["pilot_flux_shapes"]=(pilot["Qx"].shape==(15,50,49) and pilot["Qy"].shape==(15,49,50) and pilot["Qz"].shape==(14,50,50))
 # Conservative SG4 identity: divergence should match expected well source under D7A convention.
 cons=float(np.linalg.norm((pilot["divergence"]-pilot["well_source"]).ravel()))
 scale=max(float(np.linalg.norm(pilot["well_source"].ravel())),1e-30)
 rel=cons/scale
 gates["pilot_local_conservation_rel_L2_le_1e_9"]=rel<=1e-9
 global_mismatch=abs(float(pilot["divergence"].sum()-pilot["well_source"].sum()))
 global_scale=max(abs(float(pilot["well_source"].sum())),1e-30)
 grel=global_mismatch/global_scale
 gates["pilot_global_conservation_rel_le_1e_9"]=grel<=1e-9
 print(f"  pressure psi min/mean/max = {pilot['pressure_psi'].min():.6f} / {pilot['pressure_psi'].mean():.6f} / {pilot['pressure_psi'].max():.6f}")
 print(f"  local conservation relative L2 = {rel:.6e}")
 print(f"  global conservation relative mismatch = {grel:.6e}")

 refp=OUT/"V16D24CR1_Geology0026_Reference_500tpd_2000psi.npz"
 pilp=OUT/"V16D24CR1_Geology0026_TRAIN_Pilot_350tpd_1800psi.npz"
 np.savez_compressed(refp,**ref,geology_case_id=np.array("0026"),injection_tonnes_day=np.array(500.),producer_BHP_psi=np.array(2000.))
 np.savez_compressed(pilp,**pilot,geology_case_id=np.array("0026"),injection_tonnes_day=np.array(350.),producer_BHP_psi=np.array(1800.))
 gates["locked_geology0029_not_used"]=True
 gates["no_training"]=True
 ok=all(gates.values())
 status=("V16D_SG3_CONTROL_ADAPTER_REFERENCE_EQUIVALENT_GEOLOGY0026_TRAIN_NEWCONTROL_PILOT_CERTIFIED_36CASE_FLOW_EXECUTION_AUTHORIZED"
         if ok else "V16D_CONTROL_ADAPTER_OR_TRAIN_PILOT_CERTIFICATION_BLOCKED")
 nxt=("V16D-25 — D7B-Derived 36-Foundation-Case Control-Space SG2/SG3/SG4 Flow Ensemble Execution"
      if ok else "Diagnose failed reference/pilot gate; do not execute 36-case batch.")
 summary={"milestone":"V16D-24C-R1","status":status,"reference_diffs":diffs,
          "pilot":{"local_conservation_relative_L2":rel,"global_conservation_relative_mismatch":grel,
                   "reference_artifact_sha256":sha(refp),"pilot_artifact_sha256":sha(pilp)},
          "gates":gates,"next_milestone":nxt}
 sp=OUT/"PAD_Stream_V16D24C_R1_Summary.json";sp.write_text(json.dumps(summary,indent=2))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
