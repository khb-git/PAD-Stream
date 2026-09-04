#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,numpy as np,sys
R=Path(__file__).resolve().parent
BR=R/"output"/"V16_D14BR_GEOLOGY_FLOW_FIELD_SCHEMA_REPAIR_AUDIT"
SUM=BR/"PAD_Stream_V16D14BR_Summary.json";REG=BR/"V16D14BR_24Case_Geology_Flow_Field_Schema.json"
SUMSHA="3abe21395678e00ed15ae6491ba538395fc6aab53f045a47f186a68f2a367320"
D14REG=R/"output"/"V16_D14_SOURCEBOUND_24CASE_PREDICTOR_SCHEMA_AUDIT"/"V16D14_Source_Binding_Registry.json"
O=R/"output"/"V16_D14BR1_FIELD_LEVEL_SOURCE_DERIVATION_BINDING";O.mkdir(parents=True,exist_ok=True)
CASES=["0020","0015","0013","0004","0006","0002","0023","0016","0009","0019","0017","0024","0003","0011","0014","0007","0010","0025","0008","0012","0005","0018","0021","0022"]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def grid_fields(p):
 with np.load(p,allow_pickle=False) as z:return {k:list(np.asarray(z[k]).shape) for k in z.files if np.asarray(z[k]).shape==(15,50,50)}
def search_pressure(c,exclude):
 hits=[]
 for p in (R/"output").rglob("*.npz"):
  if p.resolve()==exclude.resolve():continue
  n=p.name.lower()
  if not (f"case_{c}" in n or f"case{c}" in n):continue
  try:
   with np.load(p,allow_pickle=False) as z:
    keys=[k for k in z.files if np.asarray(z[k]).shape==(15,50,50) and k.lower() in ("pressure","pressure_pa","p","p_pa")]
   if keys:hits.append({"path":str(p),"sha256":sha(p),"keys":keys})
  except:pass
 return hits
def main():
 print("="*78);print("PAD-Stream V16D-14BR1");print("Field-Level Source / Derivation Binding Audit");print("="*78)
 print("""BR ESTABLISHED THAT THE BOUND GEOLOGY ARTIFACT USES Kx_mD/Ky_mD/Kz_mD
AND POROSITY, WHILE PRESSURE IS NOT STORED THERE.

BR1 BINDS THOSE EXPLICIT PERMEABILITY FIELDS DIRECTLY AND SEARCHES THE
PRESERVED CASE PHYSICS ARTIFACTS FOR AN EXPLICIT (15,50,50) PRESSURE FIELD.
NO PRESSURE IS RECONSTRUCTED, NO PHYSICS IS RERUN, AND NO ARRAY IS CHOSEN
BY NUMERICAL CLOSENESS.
""")
 if not SUM.exists() or sha(SUM)!=SUMSHA:raise RuntimeError("BR authority SHA mismatch")
 br=json.loads(REG.read_text());d14=json.loads(D14REG.read_text());out={};amb=[];miss=[]
 for c in CASES:
  gp=Path(br[c]["artifact"])
  with np.load(gp,allow_pickle=False) as z:
   bind={}
   for role,key in [("Kx","Kx_mD"),("Ky","Ky_mD"),("Kz","Kz_mD"),("porosity","porosity")]:
    bind[role]=key if key in z.files and np.asarray(z[key]).shape==(15,50,50) else None
  ph=search_pressure(c,gp)
  if len(ph)==0:miss.append(c);pressure=None
  elif len(ph)>1:amb.append({"case":c,"candidates":ph});pressure=None
  else:pressure=ph[0]
  out[c]={"geology_artifact":str(gp),"geology_sha256":sha(gp),"field_bindings":bind,"pressure_binding":pressure}
 rp=O/"V16D14BR1_Field_Level_Binding_Registry.json";rp.write_text(json.dumps(out,indent=2))
 gates={"BR_summary_SHA_exact":sha(SUM)==SUMSHA,
 "all_Kx_mD_bound":all(out[c]["field_bindings"]["Kx"]=="Kx_mD" for c in CASES),
 "all_Ky_mD_bound":all(out[c]["field_bindings"]["Ky"]=="Ky_mD" for c in CASES),
 "all_Kz_mD_bound":all(out[c]["field_bindings"]["Kz"]=="Kz_mD" for c in CASES),
 "all_porosity_bound":all(out[c]["field_bindings"]["porosity"]=="porosity" for c in CASES),
 "pressure_candidate_present_all_cases":len(miss)==0,"pressure_candidate_unique_all_cases":len(amb)==0 and len(miss)==0,
 "no_pressure_reconstruction":True,"no_physics_rerun":True,"no_numerical_closeness":True,"no_target_Y_read":True,"no_training":True}
 ok=all(gates.values())
 status="V16D_K_FIELDS_AND_PRESSURE_SOURCE_UNIQUELY_BOUND_D14B_R1_AUTHORIZED" if ok else "V16D_PRESSURE_SOURCE_BINDING_INCOMPLETE_OR_AMBIGUOUS_NO_PREDICTOR_ASSEMBLY"
 nxt="V16D-14B-R1 — Contract-1.0 Predictor Assembly with Bound K_mD + Pressure Fields" if ok else "V16D-14BR2 — Pressure Source Candidate Provenance Disambiguation Audit"
 q={"milestone":"V16D-14BR1","status":status,"missing_pressure_cases":miss,"ambiguous_pressure_cases":amb,
 "binding_registry_sha256":sha(rp),"gates":gates,"next_milestone":nxt}
 sp=O/"PAD_Stream_V16D14BR1_Summary.json";sp.write_text(json.dumps(q,indent=2))
 print("pressure missing cases:",miss if miss else "none");print("pressure ambiguous cases:",len(amb))
 print("Case0020:",out["0020"]);print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
