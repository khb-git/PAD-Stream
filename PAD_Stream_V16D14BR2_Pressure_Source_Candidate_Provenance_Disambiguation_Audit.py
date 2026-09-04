#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,numpy as np,re,sys
R=Path(__file__).resolve().parent
BR1=R/"output"/"V16_D14BR1_FIELD_LEVEL_SOURCE_DERIVATION_BINDING"
SUM=BR1/"PAD_Stream_V16D14BR1_Summary.json"
SUMSHA="4cf9f59e009cca494c0317fa24341e7f57f89c55434f0d4c7291ec37257ec366"
D14=R/"output"/"V16_D14_SOURCEBOUND_24CASE_PREDICTOR_SCHEMA_AUDIT"/"V16D14_Source_Binding_Registry.json"
O=R/"output"/"V16_D14BR2_PRESSURE_SOURCE_PROVENANCE_DISAMBIGUATION";O.mkdir(parents=True,exist_ok=True)
CASES=["0020","0015","0013","0004","0006","0002","0023","0016","0009","0019","0017","0024","0003","0011","0014","0007","0010","0025","0008","0012","0005","0018","0021","0022"]
PKEYS=("pressure","pressure_pa","pressure_psi","p","p_pa","p_psi")
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def case_match(p,c):
 s=str(p).lower()
 return any(x in s for x in (f"case_{c}",f"case{c}",f"case-{c}",f"foundation_case_{c}"))
def inspect_npz(p):
 try:
  with np.load(p,allow_pickle=False) as z:
   return [{"key":k,"shape":list(np.asarray(z[k]).shape),"dtype":str(np.asarray(z[k]).dtype)}
           for k in z.files if np.asarray(z[k]).shape==(15,50,50)]
 except:return []
def main():
 print("="*78);print("PAD-Stream V16D-14BR2")
 print("Pressure Source Candidate Provenance Disambiguation Audit");print("="*78)
 print("""BR1 FOUND NO PRESSURE FIELD IN THE D6 GEOLOGY ARTIFACTS.
BR2 BROADENS DISCOVERY TO PRESERVED CASE-LEVEL PHYSICS ARTIFACTS AND
SOURCE/MANIFEST TEXT, WITHOUT RECONSTRUCTING PRESSURE OR COMPARING VALUES.

A PRESSURE FIELD IS AUTHORIZED ONLY WHEN A PERSISTED 15x50x50 ARRAY IS
EXPLICITLY NAMED AS PRESSURE AND ITS CASE ID IS PROVENANCE-BOUND.
""")
 if not SUM.exists() or sha(SUM)!=SUMSHA:raise RuntimeError("BR1 authority SHA mismatch")
 d14=json.loads(D14.read_text());report={};missing=[];amb=[]
 allnpz=list((R/"output").rglob("*.npz"))
 for c in CASES:
  cand=[]
  for q in allnpz:
   if not case_match(q,c):continue
   fields=inspect_npz(q)
   for f in fields:
    if f["key"].lower() in PKEYS:
     cand.append({"path":str(q),"sha256":sha(q),"field":f,"path_tokens":q.parts[-5:]})
  # Search case-bound JSON manifests for explicit pressure artifact paths/keys.
  refs=[]
  for j in (R/"output").rglob("*.json"):
   try:
    txt=j.read_text(encoding="utf-8",errors="ignore")
   except:continue
   if c not in txt or "pressure" not in txt.lower():continue
   # evidence only; never creates a numerical field
   refs.append({"path":str(j),"sha256":sha(j),"mentions_pressure":True})
  # exact duplicate artifact/key refs collapse by SHA+key
  uniq={}
  for x in cand:uniq[(x["sha256"],x["field"]["key"])]=x
  cand=list(uniq.values())
  if len(cand)==0:missing.append(c)
  elif len(cand)>1:amb.append(c)
  report[c]={"D14_geology_flow_binding":d14[c]["geology_flow"],"persisted_pressure_candidates":cand,
             "pressure_manifest_or_source_mentions":refs[:50],"candidate_count":len(cand)}
 rp=O/"V16D14BR2_Pressure_Provenance_Candidate_Registry.json";rp.write_text(json.dumps(report,indent=2))
 gates={"BR1_summary_SHA_exact":sha(SUM)==SUMSHA,"all_24_cases_audited":len(report)==24,
        "persisted_pressure_candidate_present_all":len(missing)==0,
        "persisted_pressure_candidate_unique_all":len(missing)==0 and len(amb)==0,
        "pressure_field_explicitly_named":len(missing)==0 and len(amb)==0,
        "no_pressure_reconstruction":True,"no_physics_rerun":True,"no_numerical_closeness":True,
        "no_target_Y_read":True,"no_normalization_fit":True,"no_training":True}
 ok=all(gates.values())
 if ok:
  status="V16D_PERSISTED_CASE_PRESSURE_FIELDS_UNIQUELY_PROVENANCE_BOUND_D14B_R1_AUTHORIZED"
  nxt="V16D-14B-R1 — Contract-1.0 Predictor Assembly with Explicit K_mD + Pressure Bindings"
 else:
  status="V16D_PERSISTED_PRESSURE_NOT_UNIQUELY_RECOVERABLE_NEW_V16D_PRESSURE_INTERFACE_DECISION_REQUIRED"
  nxt="V16D-14BR3 — Pressure Feature Authority Decision: Persist New Source-Authentic SG3 Pressure or Remove Pressure Predictor"
 q={"milestone":"V16D-14BR2","status":status,"missing_cases":missing,"ambiguous_cases":amb,
    "candidate_registry_sha256":sha(rp),"gates":gates,"next_milestone":nxt}
 sp=O/"PAD_Stream_V16D14BR2_Summary.json";sp.write_text(json.dumps(q,indent=2))
 print("missing pressure cases:",missing if missing else "none");print("ambiguous pressure cases:",amb if amb else "none")
 for c in CASES[:3]:print(f"Case{c} candidates:",report[c]["persisted_pressure_candidates"])
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
