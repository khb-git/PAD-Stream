#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,numpy as np,sys
R=Path(__file__).resolve().parent
D14=R/"output"/"V16_D14_SOURCEBOUND_24CASE_PREDICTOR_SCHEMA_AUDIT"
SUM=D14/"PAD_Stream_V16D14_Summary.json";REG=D14/"V16D14_Source_Binding_Registry.json"
SUMSHA="75f48ebede8e6f17d44d3c51918b9bdcc1d328789926477a5d45555cc6019d25"
O=R/"output"/"V16_D14BR_GEOLOGY_FLOW_FIELD_SCHEMA_REPAIR_AUDIT";O.mkdir(parents=True,exist_ok=True)
CASES=["0020","0015","0013","0004","0006","0002","0023","0016","0009","0019","0017","0024","0003","0011","0014","0007","0010","0025","0008","0012","0005","0018","0021","0022"]
ALIASES={"Kx":["Kx","kx","KX"],"Ky":["Ky","ky","KY"],"Kz":["Kz","kz","KZ"],"porosity":["porosity","phi","PORO"],"pressure":["pressure","p","P"]}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-14BR")
 print("Geology/Flow Field Schema Repair Audit");print("="*78)
 print("""D14B FAILED ON CASE0020 BEFORE WRITING ANY PREDICTOR ARTIFACT.
THE FAILURE WAS A FIELD-SCHEMA ASSUMPTION: THE SOURCE-BOUND GEOLOGY/FLOW
ARTIFACT DOES NOT EXPOSE A (15,50,50) ARRAY LITERALLY NAMED 'Kx'.

THIS AUDIT DOES NOT REGENERATE PHYSICS, FIT VALUES, OR SELECT BY NUMERICAL
CLOSENESS. IT RECORDS THE EXACT NPZ KEYS/SHAPES FOR ALL 24 BOUND SOURCES
AND BINDS ONLY UNIQUE FIELD-LEVEL REPRESENTATIONS.
""")
 if not SUM.exists() or sha(SUM)!=SUMSHA:raise RuntimeError("D14 authority SHA mismatch")
 reg=json.loads(REG.read_text());report={};bad=[]
 for c in CASES:
  gp=Path(reg[c]["geology_flow"])
  with np.load(gp,allow_pickle=False) as z:
   schema={k:list(np.asarray(z[k]).shape) for k in z.files}
   bind={}
   for role,names in ALIASES.items():
    hits=[n for n in names if n in z.files and np.asarray(z[n]).shape==(15,50,50)]
    bind[role]=hits[0] if len(hits)==1 else None
   # Also record all grid-shaped candidates; no automatic semantic relabeling.
   grid=[k for k in z.files if np.asarray(z[k]).shape==(15,50,50)]
  report[c]={"artifact":str(gp),"sha256":sha(gp),"schema":schema,"grid_shaped_fields":grid,"unique_alias_bindings":bind}
  if any(v is None for v in bind.values()):bad.append(c)
 rp=O/"V16D14BR_24Case_Geology_Flow_Field_Schema.json";rp.write_text(json.dumps(report,indent=2))
 gates={"D14_SHA_exact":sha(SUM)==SUMSHA,"exact_24_sources":len(report)==24,
        "all_Kx_unique_alias_bound":all(report[c]["unique_alias_bindings"]["Kx"] is not None for c in CASES),
        "all_Ky_unique_alias_bound":all(report[c]["unique_alias_bindings"]["Ky"] is not None for c in CASES),
        "all_Kz_unique_alias_bound":all(report[c]["unique_alias_bindings"]["Kz"] is not None for c in CASES),
        "all_porosity_unique_alias_bound":all(report[c]["unique_alias_bindings"]["porosity"] is not None for c in CASES),
        "all_pressure_unique_alias_bound":all(report[c]["unique_alias_bindings"]["pressure"] is not None for c in CASES),
        "no_physics_regeneration":True,"no_numerical_closeness":True,"no_fitting":True,"no_target_Y_read":True,"no_training":True}
 ok=all(gates.values())
 status="V16D_GEOLOGY_FLOW_FIELD_SCHEMA_UNIQUELY_REPAIRED_D14B_RETRY_AUTHORIZED" if ok else "V16D_GEOLOGY_FLOW_FIELD_SCHEMA_NOT_FULLY_BOUND_NO_PREDICTOR_ASSEMBLY"
 nxt="V16D-14B-R1 — Contract-1.0 Predictor Assembly with Repaired Field Schema" if ok else "V16D-14BR1 — Field-Level Source/Derivation Binding Audit"
 q={"milestone":"V16D-14BR","status":status,"cases_not_fully_alias_bound":bad,"schema_registry_sha256":sha(rp),"gates":gates,"next_milestone":nxt}
 sp=O/"PAD_Stream_V16D14BR_Summary.json";sp.write_text(json.dumps(q,indent=2))
 print("cases not fully alias-bound:",bad if bad else "none")
 print("\nCase0020 grid-shaped fields:",report["0020"]["grid_shaped_fields"])
 print("Case0020 bindings:",report["0020"]["unique_alias_bindings"])
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
