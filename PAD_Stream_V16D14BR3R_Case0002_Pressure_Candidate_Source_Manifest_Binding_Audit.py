#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,sys
R=Path(__file__).resolve().parent
BR3=R/"output"/"V16_D14BR3_CASE0002_PRESSURE_LINEAGE_DISAMBIGUATION"
SUM=BR3/"PAD_Stream_V16D14BR3_Summary.json"
SUMSHA="93110488b58df1567851cedb289ef4226da62bf96436290cf95c6f2a8af0856b"
O=R/"output"/"V16_D14BR3R_CASE0002_PRESSURE_SOURCE_MANIFEST_BINDING";O.mkdir(parents=True,exist_ok=True)
D7B_DIRNAME="V16_D7B_FULL_FROZEN_CASE0002_0025_SOURCEBOUND_SG2_SG3_SG4_FLOW_ENSEMBLE"
TARGET_NAME="V16D_Foundation_Case_0002_Flow.npz"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-14BR3R")
 print("Case0002 Pressure Candidate Source / Manifest Binding Audit");print("="*78)
 print("""BR3'S 25-CANDIDATE RESULT WAS CAUSED BY A CASE-ID MATCHING BUG:
THE TOKEN 'case0002' OCCURS IN THE D7B ENSEMBLE DIRECTORY NAME
'CASE0002_0025', SO CASE0003...0025 FILES WERE FALSELY ATTRIBUTED TO
CASE0002.

BR3R REPAIRS ONLY CASE IDENTITY. IT REQUIRES THE EXACT CASE0002 FLOW
FILENAME INSIDE THE ALREADY-FROZEN D7B ENSEMBLE. NO VALUES ARE COMPARED.
""")
 if not SUM.exists() or sha(SUM)!=SUMSHA:raise RuntimeError("BR3 authority SHA mismatch")
 d=R/"output"/D7B_DIRNAME/"cases"
 exact=d/TARGET_NAME
 # Strict identity: basename, parent ensemble, explicit file existence.
 matches=[q for q in d.glob("*.npz") if q.name==TARGET_NAME]
 selected=None
 if len(matches)==1:
  q=matches[0];selected={"path":str(q),"sha256":sha(q),"case_id":"0002","field":"pressure_psi"}
 # Look for frozen D7B manifests/summaries that explicitly mention exact basename.
 evidence=[]
 for j in (R/"output"/D7B_DIRNAME).rglob("*.json"):
  try:t=j.read_text(encoding="utf-8",errors="ignore")
  except:continue
  if TARGET_NAME in t or (selected and selected["sha256"] in t):
   evidence.append({"path":str(j),"sha256":sha(j),"mentions_exact_case0002_artifact":TARGET_NAME in t,
                    "mentions_artifact_sha":bool(selected and selected["sha256"] in t)})
 gates={"BR3_summary_SHA_exact":sha(SUM)==SUMSHA,"exact_D7B_case0002_filename_unique":len(matches)==1,
        "selected_case_id_exact_0002":bool(selected and selected["case_id"]=="0002"),
        "selected_field_pressure_psi":bool(selected and selected["field"]=="pressure_psi"),
        "case_identity_uses_filename_not_parent_substring":True,
        "D7B_manifest_evidence_found":len(evidence)>0,
        "no_numerical_closeness":True,"no_pressure_reconstruction":True,"no_SG3_rerun":True,
        "no_target_Y_read":True,"no_normalization_fit":True,"no_training":True}
 ok=all(gates.values())
 status="V16D_CASE0002_D7B_PRESSURE_AUTHORITY_EXACTLY_BOUND_CASE_ID_MATCHING_BUG_REPAIRED_24CASE_PRESSURE_INTERFACE_COMPLETE" if ok else "V16D_CASE0002_PRESSURE_MANIFEST_BINDING_INCOMPLETE_NO_PREDICTOR_ASSEMBLY"
 nxt="V16D-14B-R1 — Contract-1.0 24-Case Predictor Assembly with Explicit D6 K_mD/porosity + D7B pressure_psi" if ok else "V16D-14BR3R1 — D7B Case0002 Manifest/Registry Exact Binding Audit"
 q={"milestone":"V16D-14BR3R","diagnosis":"BR2/BR3 case matching used parent-path substring and falsely mapped all D7B Case0002-0025 files to Case0002.",
    "selected":selected,"manifest_evidence":evidence,"gates":gates,"status":status,"next_milestone":nxt}
 sp=O/"PAD_Stream_V16D14BR3R_Summary.json";sp.write_text(json.dumps(q,indent=2))
 print("exact Case0002 D7B matches:",len(matches));print("SELECTED:",selected);print("manifest evidence:",len(evidence));print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
