#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,sys
R=Path(__file__).resolve().parent
D14=R/"output"/"V16_D14B_R1_CONTRACT1_0_24CASE_PREDICTOR_ASSEMBLY_EXACT_FIELD_BINDINGS"
D14SUM=D14/"PAD_Stream_V16D14B_R1_Summary.json"
D14SHA="800c75b573860321de15a45b16c1116889fc39cddca3c1589696ea4484643d27"
TRAIN=["0020","0015","0013","0004","0006","0002","0023","0016","0009","0019","0017","0024","0003","0011","0014","0007"]
VAL=["0010","0025","0008","0012"]; OOD=["0005","0018","0021","0022"]
PART={"TRAIN":TRAIN,"VALIDATION":VAL,"LOCKED_OOD_TEST":OOD}
O=R/"output"/"V16_D15R_TARGET_ARTIFACT_SCHEMA_PATH_BINDING_AUDIT";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def cid_from_name(name):
 m=re.search(r'(?<!\d)(00(?:0[2-9]|1\d|2[0-5]))(?!\d)',name)
 return m.group(1) if m else None
def main():
 print("="*78);print("PAD-Stream V16D-15R")
 print("D12 Target Artifact Schema / Path Binding Audit");print("="*78)
 print("""D15 FAILED BEFORE DATASET FREEZE BECAUSE IT ASSUMED D12C/D12DR/D12F
OUTPUT DIRECTORY NAMES. D15R DOES NOT OPEN Y ARRAYS. IT DISCOVERS THE
PRESERVED D12 TRANSPORT TARGET ARTIFACTS BY EXACT CASE ID IN THE ARTIFACT
BASENAME, THEN CLASSIFIES THEM USING THE FROZEN D11 PARTITION.

NO TARGET VALUES, NORMALIZATION, MODEL SELECTION, OR TRAINING ARE TOUCHED.
""")
 if sha(D14SUM)!=D14SHA:raise RuntimeError("D14B-R1 authority SHA mismatch")
 # Broad discovery only among V16 D12 outputs; exact basename case token prevents parent-path bug.
 roots=[d for d in (R/"output").iterdir() if d.is_dir() and "V16_D12" in d.name.upper()]
 report={}; missing=[];amb=[]
 for part,cases in PART.items():
  for c in cases:
   hits=[]
   for root in roots:
    for q in root.rglob("*.npz"):
     if cid_from_name(q.name)!=c:continue
     # Target-like lineage/path tokens only; metadata inspection, no np.load.
     s=(root.name+" "+q.name).lower()
     if any(t in s for t in ("transport","supervision","stage4","target","case")):
      hits.append(q)
   uniq={str(q.resolve()):q for q in hits}
   # Rank is NOT used to select; record all provenance candidates.
   arr=[{"path":str(q),"sha256":sha(q),"root":q.relative_to(R/"output").parts[0],
         "basename_case_id":cid_from_name(q.name)} for q in uniq.values()]
   report[c]={"partition":part,"candidates":arr,"candidate_count":len(arr)}
   if len(arr)==0:missing.append(c)
   elif len(arr)>1:amb.append(c)
 rp=O/"V16D15R_Target_Artifact_Candidate_Registry.json";rp.write_text(json.dumps(report,indent=2))
 gates={"D14B_R1_SHA_exact":sha(D14SUM)==D14SHA,"24_cases_audited":len(report)==24,
        "exact_basename_case_identity_used":True,"target_candidate_present_all_cases":len(missing)==0,
        "target_candidate_unique_all_cases":len(missing)==0 and len(amb)==0,
        "no_Y_array_opened":True,"no_normalization_fit":True,"no_model_selection":True,
        "no_training":True,"locked_OOD_values_untouched":True}
 ok=all(gates.values())
 status="V16D_D12_TARGET_ARTIFACT_PATHS_UNIQUELY_BOUND_D15R1_DATASET_FREEZE_AUTHORIZED" if ok else "V16D_D12_TARGET_ARTIFACT_BINDING_INCOMPLETE_OR_AMBIGUOUS_NO_DATASET_FREEZE"
 nxt="V16D-15R1 — Multi-Foundation-Case Learning Dataset Freeze with Repaired D12 Target Bindings" if ok else "V16D-15R2 — D12 Target Candidate Provenance Disambiguation Audit"
 sp=O/"PAD_Stream_V16D15R_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-15R","missing_cases":missing,"ambiguous_cases":amb,"candidate_registry_sha256":sha(rp),"gates":gates,"status":status,"next_milestone":nxt},indent=2))
 print("D12 output roots found:",len(roots));print("missing:",missing if missing else "none");print("ambiguous:",amb if amb else "none")
 for c in ["0020","0010","0005"]:print(f"Case{c}:",report[c])
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
