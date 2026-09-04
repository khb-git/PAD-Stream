#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,numpy as np
R=Path(__file__).resolve().parent;D=R/"output"/"V16_D14_SOURCEBOUND_24CASE_PREDICTOR_SCHEMA_AUDIT";O=R/"output"/"V16_D14A_EXACT_FIELD_BINDING";O.mkdir(parents=True,exist_ok=True)
S=D/"PAD_Stream_V16D14_Summary.json";REG=D/"V16D14_Source_Binding_Registry.json";AUTH="75f48ebede8e6f17d44d3c51918b9bdcc1d328789926477a5d45555cc6019d25"
CASES=["0020","0015","0013","0004","0006","0002","0023","0016","0009","0019","0017","0024","0003","0011","0014","0007","0010","0025","0008","0012","0005","0018","0021","0022"]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def exact(z,names,shape):
 h=[n for n in names if n in z.files and np.asarray(z[n]).shape==shape]
 return h[0] if len(h)==1 else None
def main():
 print("="*78);print("PAD-Stream V16D-14A");print("Exact Field-Level Predictor Assembly Preflight");print("="*78)
 print("NO NUMERICAL CLOSENESS MATCHING. NO XYZ->CELL INDEXING IS INVENTED. NO TRAINING.")
 if sha(S)!=AUTH:raise RuntimeError("D14 authority SHA mismatch")
 reg=json.loads(REG.read_text());report={};blocked=[]
 for c in CASES:
  r=reg[c];gp=Path(r["geology_flow"]);pp=Path(r["pollock_metric"]);ap=Path(r["adv_travel_time"])
  with np.load(gp,allow_pickle=False) as g,np.load(pp,allow_pickle=False) as p,np.load(ap,allow_pickle=False) as a:
   b={"theta":exact(p,["theta"],(201,)),"pollock_tau_s":exact(p,["pollock_tau_s"],(1078,201)),
      "pollock_tau_end_s":exact(p,["pollock_tau_end_s"],(1078,)),"xyz":exact(p,["streamline_xyz","xyz","transport_xyz"],(1078,201,3)),
      "Kx":exact(g,["Kx"],(15,50,50)),"Ky":exact(g,["Ky"],(15,50,50)),"Kz":exact(g,["Kz"],(15,50,50)),
      "porosity_grid":exact(g,["porosity","phi"],(15,50,50)),"pressure_grid":exact(g,["pressure"],(15,50,50)),
      "adv_path":exact(a,["adv_tau_s","tau_adv_s","tau_ADV_s","adv_tau","tau_ADV"],(1078,201))}
   sampled={}
   aliases={"log10_Kh":["log10_Kh"],"log10_Kz_over_Kh":["log10_Kz_over_Kh"],"porosity_path":["porosity_path","porosity_sampled"],"pressure_z":["pressure_z","pressure_path_z"]}
   for k,names in aliases.items():sampled[k]=exact(p,names,(1078,201))
   b.update(sampled);missing=[k for k,v in b.items() if v is None]
   # Grid fields + xyz are insufficient until the exact historical coordinate-to-cell
   # sampling algebra is source-bound. This preflight deliberately blocks instead of guessing.
   if any(k in missing for k in ["log10_Kh","log10_Kz_over_Kh","porosity_path","pressure_z"]):blocked.append(c)
   report[c]={"bindings":b,"missing":missing}
 rp=O/"V16D14A_Field_Level_Preflight_Registry.json";rp.write_text(json.dumps(report,indent=2))
 ok=len(blocked)==0
 status="V16D_EXACT_FIELD_LEVEL_PREDICTOR_BINDING_COMPLETE_ASSEMBLY_AUTHORIZED" if ok else "V16D_EXACT_STREAMLINE_SAMPLING_ALGEBRA_NOT_YET_BOUND_NO_PREDICTOR_ASSEMBLY_NO_NORMALIZATION_STATS"
 nxt="V16D-14B — Predictor Assembly + TRAIN-Only Statistics Freeze" if ok else "V16D-14AR — Exact Historical Streamline Sampling Algebra Source-Binding Audit"
 print("cases requiring sampling-algebra binding:",blocked if blocked else "none")
 print(f"[{'PASS' if ok else 'FAIL'}] exact_path_sampled_geology_pressure_fields_bound")
 print("STATUS\n ",status);print("NEXT\n ",nxt);print("Registry SHA-256:",sha(rp))
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
