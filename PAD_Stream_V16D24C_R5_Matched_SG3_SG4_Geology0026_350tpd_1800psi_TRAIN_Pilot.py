#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,importlib.util,sys
import numpy as np
ROOT=Path(__file__).resolve().parent
S=ROOT/"output"/"V16_D24C_R4_SG4_CONTROL_DEPENDENCY_BINDING"/"PAD_Stream_V16D24C_R4_Summary.json"
SSHA="eb38ffd2e2d7a5737104fdc92c4238d54c2a6b5fec963489570d225dfa1b0354"
S2=ROOT/"PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"; SHA2="8dfc3485682830ef854178720d32050b6b2e9d25befa7ee9669993df1e544416"
S3=ROOT/"PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"; SHA3="d3ba7b7be45636f6d3ee254fd6cb95268cef9e6f35e85d53b5793596cb22b14d"
S4=ROOT/"PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"; SHA4="86a1c88ffc35033314ae6598ade23f0bebfa709f62cbe2cbef1830cd607e0af9"
CASE=ROOT/"output"/"V16_D23_FRESH_RECIPE1P1_GEOLOGIES_0026_0029"/"V16D_Geology_Case_0026_Recipe1p1.npz"
OUT=ROOT/"output"/"V16_D24C_R5_MATCHED_SG3_SG4_0026_TRAIN_PILOT";OUT.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def loadmod(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def patch(path,rate,bhp,out):
 text=path.open("r",encoding="utf-8",newline="").read();lines=text.splitlines(keepends=True);changed=[]
 for idx,line in enumerate(lines):
  for name,old,new in (("PRODUCER_BHP_PSI","2000.0",f"{bhp:.1f}"),("CO2_MASS_RATE_TONNES_DAY","500.0",f"{rate:.1f}")):
   m=re.match(rf"^({name}\s*=\s*){re.escape(old)}(\s*(?:#.*)?)(\r?\n)?$",line)
   if m:
    lines[idx]=m.group(1)+new+m.group(2)+(m.group(3) or "");changed.append(idx+1)
 out.write_text("".join(lines),encoding="utf-8",newline="")
 return changed
def main():
 print("="*78);print("PAD-Stream V16D-24C-R5")
 print("Matched SG3+SG4 Geology0026 TRAIN Pilot — 350 t/day, 1800 psi");print("="*78)
 gates={"R4_SHA_exact":sha(S)==SSHA,"SG2_SHA_exact":sha(S2)==SHA2,"SG3_SHA_exact":sha(S3)==SHA3,
 "SG4_SHA_exact":sha(S4)==SHA4,"case0026_exists":CASE.exists()}
 if not all(gates.values()):raise RuntimeError("authority pre-gate failure")
 d3=OUT/"PAD_Stream_V16D24C_R5_DERIVED_SG3_350tpd_1800psi.py"
 d4=OUT/"PAD_Stream_V16D24C_R5_DERIVED_SG4_350tpd_1800psi.py"
 c3=patch(S3,350,1800,d3);c4=patch(S4,350,1800,d4)
 gates["SG3_only_lines_122_132"]=c3==[122,132];gates["SG4_only_lines_113_123"]=c4==[113,123]
 gates["frozen_sources_still_exact"]=sha(S3)==SHA3 and sha(S4)==SHA4
 sg2=loadmod("r5sg2",S2);sg3=loadmod("r5sg3",d3);sg4=loadmod("r5sg4",d4)
 gates["matched_rate_controls"]=float(sg3.CO2_MASS_RATE_TONNES_DAY)==float(sg4.CO2_MASS_RATE_TONNES_DAY)==350.0
 gates["matched_bhp_controls"]=float(sg3.PRODUCER_BHP_PSI)==float(sg4.PRODUCER_BHP_PSI)==1800.0
 k=np.asarray(np.load(CASE)["Kx_mD"],float)
 kx,ky,kz=sg2.build_directional_permeability(k);kfx,kfy,kfz=sg2.build_face_permeabilities(kx,ky,kz);sg2.build_transmissibilities(kfx,kfy,kfz)
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
 gates["finite"]=all(np.isfinite(x).all() for x in (ppsi,qx,qy,qz,div,ws))
 gates["shapes"]=(ppsi.shape==(15,50,50) and qx.shape==(15,50,49) and qy.shape==(15,49,50) and qz.shape==(14,50,50))
 diff=div-ws;rel=float(np.linalg.norm(diff.ravel())/max(np.linalg.norm(ws.ravel()),1e-30))
 grel=float(abs(div.sum()-ws.sum())/max(abs(ws.sum()),1e-30))
 gates["local_conservation_rel_L2_le_1e_9"]=rel<=1e-9
 gates["global_conservation_rel_le_1e_9"]=grel<=1e-9
 gates["locked_0029_not_used"]=True
 print(f"\npressure min/mean/max psi: {ppsi.min():.6f} / {ppsi.mean():.6f} / {ppsi.max():.6f}")
 print(f"Qx min/max: {qx.min():.6e} / {qx.max():.6e}")
 print(f"Qy min/max: {qy.min():.6e} / {qy.max():.6e}")
 print(f"Qz min/max: {qz.min():.6e} / {qz.max():.6e}")
 print(f"local conservation relative L2: {rel:.12e}")
 print(f"global conservation relative mismatch: {grel:.12e}")
 art=OUT/"V16D24CR5_Geology0026_TRAIN_350tpd_1800psi_MatchedFlow.npz"
 np.savez_compressed(art,Kx_mD=kx,Ky_mD=ky,Kz_mD=kz,kfx_mD=kfx,kfy_mD=kfy,kfz_mD=kfz,
 Tx_SI=tx,Ty_SI=ty,Tz_SI=tz,pressure_psi=ppsi,Qx=qx,Qy=qy,Qz=qz,divergence=div,well_source=ws,
 geology_case_id=np.array("0026"),split=np.array("TRAIN"),injection_tonnes_day=np.array(350.),producer_BHP_psi=np.array(1800.))
 ok=all(gates.values())
 status="V16D_MATCHED_SG3_SG4_CONTROL_ADAPTER_TRAIN_PILOT_CERTIFIED_36CASE_FLOW_ENSEMBLE_AUTHORIZED" if ok else "V16D_D24C_R5_MATCHED_CONTROL_PILOT_BLOCKED"
 nxt="V16D-25 — D7B-Derived 36-Foundation-Case Control-Space SG2/SG3/SG4 Flow Ensemble Execution" if ok else "Diagnose matched-control conservation failure; do not batch."
 sp=OUT/"PAD_Stream_V16D24C_R5_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-24C-R5","status":status,
 "controls":{"rate_tonnes_day":350.0,"producer_BHP_psi":1800.0},"artifact_sha256":sha(art),
 "derived_SG3_sha256":sha(d3),"derived_SG4_sha256":sha(d4),"local_conservation_relative_L2":rel,
 "global_conservation_relative_mismatch":grel,"gates":gates,"next_milestone":nxt},indent=2))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
