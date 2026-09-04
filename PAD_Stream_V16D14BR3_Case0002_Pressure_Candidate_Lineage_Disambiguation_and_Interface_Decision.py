#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,numpy as np,sys
R=Path(__file__).resolve().parent
BR2=R/"output"/"V16_D14BR2_PRESSURE_SOURCE_PROVENANCE_DISAMBIGUATION"
SUM=BR2/"PAD_Stream_V16D14BR2_Summary.json"
REG=BR2/"V16D14BR2_Pressure_Provenance_Candidate_Registry.json"
SUMSHA="13dc6c029bdf58540e394c4cbcdc4f1afb17e98df0efbedc3f83985482c62204"
O=R/"output"/"V16_D14BR3_CASE0002_PRESSURE_LINEAGE_DISAMBIGUATION";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-14BR3")
 print("Case0002 Pressure Candidate Lineage Disambiguation + Interface Decision");print("="*78)
 print("""BR2 FOUND A PERSISTED EXPLICIT pressure_psi FIELD FOR EVERY CASE.
ONLY CASE0002 IS AMBIGUOUS.

BR3 DOES NOT DROP PRESSURE AND DOES NOT RERUN SG3. IT EXAMINES THE TWO
CASE0002 CANDIDATES BY PROVENANCE: FROZEN D7B ENSEMBLE AUTHORITY IS
PREFERRED ONLY IF THE CANDIDATE PATH ITSELF IS THE D7B FROZEN FLOW
ENSEMBLE ARTIFACT. NO NUMERICAL VALUES ARE COMPARED.
""")
 if not SUM.exists() or sha(SUM)!=SUMSHA:raise RuntimeError("BR2 authority SHA mismatch")
 reg=json.loads(REG.read_text());c=reg["0002"]["persisted_pressure_candidates"]
 print("Case0002 candidate count:",len(c))
 for i,x in enumerate(c,1):print(f"  [{i}] {x['path']} | {x['sha256']} | {x['field']}")
 d7=[x for x in c if "V16_D7B_FULL_FROZEN_CASE0002_0025_SOURCEBOUND_SG2_SG3_SG4_FLOW_ENSEMBLE" in x["path"] and x["field"]["key"]=="pressure_psi"]
 unique=len(d7)==1
 selected=d7[0] if unique else None
 gates={"BR2_summary_SHA_exact":sha(SUM)==SUMSHA,"Case0002_has_candidates":len(c)>0,
        "unique_D7B_frozen_flow_pressure_candidate":unique,
        "selected_field_explicit_pressure_psi":bool(selected and selected["field"]["key"]=="pressure_psi"),
        "selection_by_frozen_lineage_not_values":True,"all_other_cases_already_unique":all(reg[k]["candidate_count"]==1 for k in reg if k!="0002"),
        "no_pressure_reconstruction":True,"no_SG3_rerun":True,"no_numerical_closeness":True,
        "no_target_Y_read":True,"no_normalization_fit":True,"no_training":True}
 ok=all(gates.values())
 if ok:
  status="V16D_CASE0002_PRESSURE_DISAMBIGUATED_D7B_FROZEN_FLOW_PRESSURE_AUTHORITY_24CASE_PRESSURE_INTERFACE_BOUND"
  nxt="V16D-14B-R1 — Contract-1.0 24-Case Predictor Assembly with Explicit K_mD + D7B pressure_psi"
 else:
  status="V16D_CASE0002_PRESSURE_LINEAGE_REMAINS_AMBIGUOUS_NO_PREDICTOR_ASSEMBLY"
  nxt="V16D-14BR3R — Case0002 Pressure Candidate Source/Manifest Binding Audit"
 q={"milestone":"V16D-14BR3","status":status,"selected_Case0002_pressure":selected,"gates":gates,"next_milestone":nxt}
 sp=O/"PAD_Stream_V16D14BR3_Summary.json";sp.write_text(json.dumps(q,indent=2))
 print("\nSELECTED:",selected if selected else "none");print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
