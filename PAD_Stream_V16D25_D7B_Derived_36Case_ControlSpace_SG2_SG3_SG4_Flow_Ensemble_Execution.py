#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,importlib.util,json,re,sys,time
import numpy as np

ROOT=Path(__file__).resolve().parent
R7=ROOT/"output"/"V16_D24C_R7_CORRECTED_GLOBAL_CONSERVATION_CONTRACT_RECERTIFICATION"/"PAD_Stream_V16D24C_R7_Summary.json"
R7SHA="e77998de6fe4dfa1d00144bb56be68cef8820f364223312d92d5c8fdc1f64e80"
D7B=ROOT/"PAD_Stream_V16D7B_Full_Frozen_Case0002_0025_SourceBound_SG2_SG3_SG4_Flow_Ensemble_Execution.py"
D7BSHA="d2a736039bd34ec5bc3272ebf0ab9908f47c28cdc1bd91ca74d8d76ec366922b"
S2=ROOT/"PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"; SHA2="8dfc3485682830ef854178720d32050b6b2e9d25befa7ee9669993df1e544416"
S3=ROOT/"PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"; SHA3="d3ba7b7be45636f6d3ee254fd6cb95268cef9e6f35e85d53b5793596cb22b14d"
S4=ROOT/"PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"; SHA4="86a1c88ffc35033314ae6598ade23f0bebfa709f62cbe2cbef1830cd607e0af9"
GDIR=ROOT/"output"/"V16_D23_FRESH_RECIPE1P1_GEOLOGIES_0026_0029"
OUT=ROOT/"output"/"V16_D25_36CASE_CONTROLSPACE_SG2_SG3_SG4_FLOW_ENSEMBLE"; CASEOUT=OUT/"cases"; DER=OUT/"derived_sources"
OUT.mkdir(parents=True,exist_ok=True);CASEOUT.mkdir(exist_ok=True);DER.mkdir(exist_ok=True)

GEO={"0026":("TRAIN",350456),"0027":("TRAIN",358375),"0028":("VALIDATION",366294),"0029":("LOCKED_OOD_TEST",374213)}
RATES=(350.0,500.0,650.0); BHPS=(1800.0,2000.0,2200.0)

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
 out.open("w",encoding="utf-8",newline="").write("".join(lines))
 return changed
def well_source(sg4,k,p):
 ew=sg4.construct_expected_well_rates(k,p);ws=None
 if isinstance(ew,np.ndarray):ws=np.asarray(ew,float)
 elif isinstance(ew,tuple):
  for x in ew:
   if isinstance(x,np.ndarray) and x.shape==(15,50,50):ws=np.asarray(x,float);break
 elif isinstance(ew,dict):
  for key in ("well_source","source","q_well"):
   if key in ew:ws=np.asarray(ew[key],float);break
 if ws is None:raise RuntimeError("Could not bind SG4 well_source")
 return ws
def main():
 print("="*78);print("PAD-Stream V16D-25")
 print("D7B-Derived 36-Foundation-Case Control-Space SG2/SG3/SG4 Flow Ensemble");print("="*78)
 pre={"R7_SHA_exact":R7.exists() and sha(R7)==R7SHA,"D7B_SHA_exact":D7B.exists() and sha(D7B)==D7BSHA,
 "SG2_SHA_exact":sha(S2)==SHA2,"SG3_SHA_exact":sha(S3)==SHA3,"SG4_SHA_exact":sha(S4)==SHA4,
 "four_fresh_geologies_exist":all((GDIR/f"V16D_Geology_Case_{g}_Recipe1p1.npz").exists() for g in GEO)}
 print("\nPRE-GATES")
 for k,v in pre.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 if not all(pre.values()):raise RuntimeError("D25 authority pre-gate failure")
 sg2=loadmod("d25sg2",S2)
 # Build one exact source-preserving SG3/SG4 pair per control tuple; reuse across geologies.
 mods={}
 for r in RATES:
  for b in BHPS:
   tag=f"R{int(r)}_B{int(b)}"
   d3=DER/f"D25_DERIVED_SG3_{tag}.py";d4=DER/f"D25_DERIVED_SG4_{tag}.py"
   c3=patch(S3,r,b,d3);c4=patch(S4,r,b,d4)
   if c3!=[122,132] or c4!=[113,123]:raise RuntimeError(f"patch-line contract failure {tag}: {c3},{c4}")
   m3=loadmod("d25sg3_"+tag,d3);m4=loadmod("d25sg4_"+tag,d4)
   if float(m3.CO2_MASS_RATE_TONNES_DAY)!=r or float(m4.CO2_MASS_RATE_TONNES_DAY)!=r or float(m3.PRODUCER_BHP_PSI)!=b or float(m4.PRODUCER_BHP_PSI)!=b:
    raise RuntimeError("cross-module control mismatch "+tag)
   mods[(r,b)]=(m3,m4,d3,d4)
 rows=[];allpass=True;t0=time.time();n=0
 for gid,(split,seed) in GEO.items():
  gp=GDIR/f"V16D_Geology_Case_{gid}_Recipe1p1.npz";gz=np.load(gp);k=np.asarray(gz["Kx_mD"],float)
  kx,ky,kz=sg2.build_directional_permeability(k);kfx,kfy,kfz=sg2.build_face_permeabilities(kx,ky,kz);sg2.build_transmissibilities(kfx,kfy,kfz)
  for rate in RATES:
   for bhp in BHPS:
    n+=1;case_id=f"V16D_Foundation_Case_{gid}_R{int(rate)}_B{int(bhp)}"
    print(f"\n[{n:02d}/36] {case_id}  split={split}")
    sg3,sg4,d3,d4=mods[(rate,bhp)]
    tx,ty,tz=sg3.construct_si_transmissibilities(kfx,kfy,kfz)
    A,b=sg3.assemble_pressure_system(k,tx,ty,tz)[:2]
    sol=sg3.solve_pressure(A,b);p=np.asarray(sol[0] if isinstance(sol,tuple) else sol,float)
    if p.size==37500:p=p.reshape(15,50,50)
    ppsi=p/sg3.PSI_TO_PA if np.nanmedian(p)>1e5 else p
    flux=sg4.compute_face_fluxes(ppsi,tx,ty,tz);qx,qy,qz=[np.asarray(x,float) for x in flux[:3]]
    div=np.asarray(sg4.compute_flux_divergence(qx,qy,qz),float);ws=well_source(sg4,k,ppsi);res=div-ws
    finite=all(np.isfinite(x).all() for x in (ppsi,qx,qy,qz,div,ws))
    local=float(np.linalg.norm(res.ravel())/max(np.linalg.norm(ws.ravel()),1e-30))
    gross=float(np.abs(ws).sum());inj=float(ws[ws>0].sum());prod=float(-ws[ws<0].sum());through=max(abs(inj),abs(prod),1e-30)
    gg=float(abs(res.sum())/max(gross,1e-30));gt=float(abs(res.sum())/through);wb=float(abs(inj-prod)/through)
    passed=finite and local<=1e-9 and gg<=1e-9 and gt<=1e-9 and wb<=1e-9
    allpass &= passed
    ap=CASEOUT/f"{case_id}_Flow.npz"
    np.savez_compressed(ap,Kx_mD=kx,Ky_mD=ky,Kz_mD=kz,kfx_mD=kfx,kfy_mD=kfy,kfz_mD=kfz,
      Tx_SI=tx,Ty_SI=ty,Tz_SI=tz,pressure_psi=ppsi,Qx=qx,Qy=qy,Qz=qz,divergence=div,well_source=ws,
      geology_case_id=np.array(gid),foundation_case_id=np.array(case_id),split=np.array(split),geology_seed=np.array(seed),
      injection_tonnes_day=np.array(rate),producer_BHP_psi=np.array(bhp))
    row={"foundation_case_id":case_id,"geology_id":gid,"split":split,"seed":seed,"injection_tonnes_day":rate,"producer_BHP_psi":bhp,
      "pressure_min_psi":float(ppsi.min()),"pressure_mean_psi":float(ppsi.mean()),"pressure_max_psi":float(ppsi.max()),
      "local_relative_L2":local,"global_gross_scaled":gg,"global_throughput_scaled":gt,"well_balance_relative":wb,
      "finite":finite,"certified":passed,"artifact":str(ap.relative_to(ROOT)),"artifact_sha256":sha(ap)}
    rows.append(row)
    print(f"  P min/mean/max = {row['pressure_min_psi']:.3f}/{row['pressure_mean_psi']:.3f}/{row['pressure_max_psi']:.3f} psi")
    print(f"  conservation local={local:.3e} global_gross={gg:.3e} throughput={gt:.3e} well_balance={wb:.3e} => {'PASS' if passed else 'FAIL'}")
    if not passed:
     print("SAFE BLOCK: case failed certification; remaining cases will not be executed.")
     break
   if not allpass:break
  if not allpass:break
 manifest=OUT/"V16D25_36Case_ControlSpace_Flow_Ensemble_Manifest.csv"
 if rows:
  with manifest.open("w",newline="") as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 gates=dict(pre);gates.update({"exactly_36_cases_executed":len(rows)==36,"all_executed_cases_certified":all(x["certified"] for x in rows),
 "split_counts_18_9_9":({s:sum(x["split"]==s for x in rows) for s in ("TRAIN","VALIDATION","LOCKED_OOD_TEST")}=={"TRAIN":18,"VALIDATION":9,"LOCKED_OOD_TEST":9}),
 "all_9_control_combinations_per_geology":all(sum(x["geology_id"]==g for x in rows)==9 for g in GEO),
 "frozen_SG3_SG4_unmodified":sha(S3)==SHA3 and sha(S4)==SHA4,
 "no_transport":True,"no_training":True,"locked_OOD_generated_not_evaluated":True})
 ok=all(gates.values()) and allpass
 status="V16D_36CASE_CONTROLSPACE_SG2_SG3_SG4_FLOW_ENSEMBLE_GENERATED_CERTIFIED_POLLOCK_EXPANSION_AUTHORIZED" if ok else "V16D_D25_36CASE_FLOW_ENSEMBLE_BLOCKED"
 nxt="V16D-26 — Source-Bound SG5 Pollock Streamline/TOF Expansion Across 36 Control-Space Foundation Cases" if ok else "Diagnose failed D25 case/gate; do not proceed to Pollock."
 summary={"milestone":"V16D-25","status":status,"authority":{"R7_sha256":R7SHA,"D7B_sha256":D7BSHA},
 "design":{"geologies":GEO,"rates_tonnes_day":RATES,"producer_BHP_psi":BHPS,"total_cases":36},
 "execution":{"completed":len(rows),"runtime_s":time.time()-t0,"manifest_sha256":sha(manifest) if manifest.exists() else None},
 "gates":gates,"next_milestone":nxt}
 sp=OUT/"PAD_Stream_V16D25_Summary.json";sp.write_text(json.dumps(summary,indent=2))
 print("\n"+"="*78+"\nD25 GATES\n"+"="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
