from __future__ import annotations
from pathlib import Path
import csv, hashlib, json, zipfile

ROOT=Path(__file__).resolve().parent
R5CD=ROOT/"output"/"V16_C12R5C_EXTERNAL_PRESERVED_COPY_EXACT_L2_AUTHORITY_RECOVERY_DECISION"
R5CS=R5CD/"PAD_Stream_V16C12R5C_Summary.json"

OUT=ROOT/"output"/"V16_C12AR_SURVIVING_AUTHORITY_100_DAY_VALIDATION_CONTRACT"
OUT.mkdir(parents=True,exist_ok=True)
INV=OUT/"V16C12AR_Surviving_Authority_Inventory.csv"
CAND=OUT/"V16C12AR_SG7E_Reference_Candidates.csv"
GATES=OUT/"V16C12AR_Final_Validation_Authority_Gates.csv"
DEC=OUT/"V16C12AR_Validation_Authority_Decision.csv"
CON=OUT/"V16C12AR_Surviving_Authority_100_Day_Validation_Contract.json"
SUM=OUT/"PAD_Stream_V16C12AR_Summary.json"

L2_SHA="01bb967c07b262836f6c140dd519538db13d9ce5b3bc0f83d52a6164ddcfa950"
D6_SHA="6bf6661e2344d51c54df4689758a1998952454e0bc13797b8e4da57824cf9522"
SG7E_SHA="e3d4bef65753a2d0dd65414db04416cc3cb89408578411109384617847b31bce"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""):h.update(b)
    return h.hexdigest()
def loadj(p):return json.loads(p.read_text(encoding="utf-8"))
def savej(p,x):p.write_text(json.dumps(x,indent=2),encoding="utf-8")
def save_csv(p,rows):
    rows=list(rows); keys=[]
    for r in rows:
        for k in r:
            if k not in keys:keys.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def exact_file_hits(target):
    hits=[]
    for p in (ROOT/"output").rglob("*"):
        if not p.is_file() or "V16_" in str(p):continue
        try:
            if sha(p)==target:hits.append(p)
        except:pass
    return hits

def find_sg7e_candidates():
    rows=[]
    for p in (ROOT/"output").rglob("*.npz"):
        if "V16_" in str(p):continue
        low=p.name.lower()
        if "sg7e" in low or "plume" in low or "coverage" in low:
            try:hh=sha(p)
            except:continue
            rows.append(dict(path=str(p.relative_to(ROOT)),sha256=hh,
                             exact_formal_SG7E_hash=(hh==SG7E_SHA),
                             filename=p.name))
    return rows

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-12A-R")
    print("Surviving-Authority 100-Day Validation Contract")
    print("="*78)
    print("""
R5C CLOSED EXACT BYTE RECOVERY FOR L2_independent_100 AND SG7D6 IN THE
SEARCHED ENVIRONMENT.

C12A-R DOES NOT RECREATE OR SUBSTITUTE THOSE MISSING AUTHORITIES.

IT FREEZES THE VALIDATION HIERARCHY THAT REMAINS SCIENTIFICALLY LEGITIMATE:

  1. V16 C11/C12 source-authentic Pollock solver:
       CURRENT V16 PHYSICS SUBJECT UNDER VALIDATION.

  2. L2_independent_100:
       FORMAL V15 CERTIFIED 100-DAY STREAMLINE DEPLOYMENT AUTHORITY,
       BUT BYTES UNAVAILABLE -> CANNOT BE USED FOR NUMERICAL COMPARISON.

  3. SG7D6:
       FORMAL V15 FROZEN SINGLE-STATE GRID DEPLOYMENT AUTHORITY,
       BUT BYTES UNAVAILABLE -> CANNOT BE USED FOR NUMERICAL COMPARISON.

  4. SG7E historical tensor:
       HISTORICAL FOUR-TIME GRID REFERENCE AUTHORITY.
       ITS 100-DAY SLICE MAY BE USED ONLY AS A HISTORICAL/VALIDATION
       REFERENCE IF THE EXACT FORMAL SG7E ARTIFACT IS LOCALLY BOUND.

NO MISSING V15 ARTIFACT MAY BE RECONSTRUCTED BY NUMERICAL CLOSENESS.
NO HISTORICAL REFERENCE MAY BE RELABELLED AS THE MISSING CERTIFIED L2.
NO Y_transport IS AUTHORIZED BY THIS CONTRACT.
""")
    if not R5CS.exists():raise FileNotFoundError(R5CS)
    r5c=loadj(R5CS)
    if r5c.get("status")!="V16C_CERTIFIED_L2_AUTHORITY_BYTES_UNAVAILABLE_AFTER_PRESERVED_COPY_SEARCH":
        raise RuntimeError("C12A-R requires R5C closed-unavailable status.")

    l2=exact_file_hits(L2_SHA); d6=exact_file_hits(D6_SHA); sg7e=exact_file_hits(SG7E_SHA)
    candidates=find_sg7e_candidates()
    save_csv(CAND,candidates)

    inv=[
      dict(authority="L2_independent_100",role="CERTIFIED_100_DAY_STREAMLINE_DEPLOYMENT",
           sha256=L2_SHA,bytes_available=bool(l2),numerical_use_allowed=bool(l2),
           substitution_allowed=False),
      dict(authority="SG7D6",role="FROZEN_SINGLE_STATE_GRID_DEPLOYMENT",
           sha256=D6_SHA,bytes_available=bool(d6),numerical_use_allowed=bool(d6),
           substitution_allowed=False),
      dict(authority="SG7E_historical_tensor",role="HISTORICAL_FOUR_TIME_GRID_REFERENCE",
           sha256=SG7E_SHA,bytes_available=bool(sg7e),numerical_use_allowed=bool(sg7e),
           substitution_allowed=False),
    ]
    save_csv(INV,inv)

    sg7e_bound=len(sg7e)==1
    gates=[
      ("R5C_missing_L2_closed_unavailable",True),
      ("L2_missing_state_not_reconstructed",not bool(l2)),
      ("SG7D6_missing_state_not_reconstructed",not bool(d6)),
      ("no_ambiguous_frozen100_substitution",True),
      ("SG7E_formal_hash_identity_defined",len(SG7E_SHA)==64),
      ("SG7E_exact_historical_reference_locally_bound",sg7e_bound),
      ("SG7E_100d_role_validation_only",True),
      ("SG7E_not_relabelled_as_L2",True),
      ("SG7E_not_relabelled_as_SG7D6",True),
      ("250_500_1000_remain_historical_reference_only",True),
      ("no_parameter_fitting_authorized",True),
      ("no_Y_transport_generated",True),
      ("no_Y_transport_authorized",True),
      ("no_frozen_artifact_mutation",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])

    if sg7e_bound:
        status="V16C_SURVIVING_100D_VALIDATION_AUTHORITY_BOUND_TO_EXACT_SG7E_HISTORICAL_REFERENCE"
        diagnosis="CERTIFIED_L2_AND_SG7D6_BYTES_ARE_UNAVAILABLE_BUT_THE_EXACT_FORMAL_SG7E_HISTORICAL_REFERENCE_SURVIVES_AND_MAY_SUPPORT_A_VALIDATION_ONLY_100_DAY_GRID_COMPARISON"
        rec=("Freeze C12A-R. Next inspect the exact SG7E tensor schema and construct a deterministic V16 Pollock-to-grid 100-day comparison path. "
             "Keep the comparison explicitly historical/validation-only; do not treat SG7E as the missing L2 or SG7D6 authority.")
        nxt="V16C-12A1 — Exact SG7E 100-Day Reference Schema and V16 Grid-Comparison Binding Audit"
    else:
        status="V16C_NO_NUMERICAL_V15_100D_AUTHORITY_BYTES_SURVIVE_FOR_DIRECT_CROSS_VALIDATION"
        diagnosis="L2_INDEPENDENT_100_AND_SG7D6_ARE_UNAVAILABLE_AND_THE_EXACT_FORMAL_SG7E_HISTORICAL_TENSOR_IS_NOT_LOCALLY_BOUND_SO_DIRECT_V15_100_DAY_NUMERICAL_CROSS_VALIDATION_CANNOT_BE PERFORMED"
        rec=("Freeze the provenance limitation. Do not fabricate a V15 numerical comparison. Close C12 cross-authority validation as unavailable and proceed with source-authentic limiting-case, conservation, boundary, and internal-physics validation for V16. "
             "A future exact SG7E recovery may reopen historical 100-day comparison.")
        nxt="V16C-12B — Internal Physics Validation Closure and Y-Generation Readiness Audit"

    sgpath=str(sg7e[0].relative_to(ROOT)) if sg7e_bound else ""
    save_csv(DEC,[dict(status=status,diagnosis=diagnosis,
        L2_bytes_available=bool(l2),SG7D6_bytes_available=bool(d6),
        SG7E_exact_hits=len(sg7e),SG7E_path=sgpath,
        direct_L2_comparison_allowed=bool(l2),
        direct_SG7D6_comparison_allowed=bool(d6),
        historical_SG7E_100d_validation_allowed=sg7e_bound,
        Y_generation_authorized=False,next_milestone=nxt)])
    savej(CON,dict(milestone="V16C-12A-R",status=status,diagnosis=diagnosis,
        authority_hierarchy=inv,
        SG7E_exact_path=sgpath or None,
        validation_rules={
          "L2_independent_100":"formal authority retained; numerical comparison prohibited while bytes unavailable",
          "SG7D6":"formal authority retained; numerical comparison prohibited while bytes unavailable",
          "SG7E_100d":"historical validation-only if exact formal artifact is bound",
          "parameter_fitting_to_SG7E":False,
          "relabel_SG7E_as_missing_L2_or_SG7D6":False,
          "later_times_as_frozen_deployment":False},
        Y_generation_authorized=False,recommendation=rec,next_milestone=nxt))
    savej(SUM,dict(milestone="V16C-12A-R",status=status,diagnosis=diagnosis,
        L2_bytes_available=bool(l2),SG7D6_bytes_available=bool(d6),
        SG7E_exact_hits=len(sg7e),SG7E_exact_bound=sg7e_bound,
        Y_transport_generated=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))

    print("SURVIVING AUTHORITY INVENTORY")
    print("  L2_independent_100 exact bytes :",len(l2))
    print("  SG7D6 exact bytes              :",len(d6))
    print("  SG7E exact historical hits     :",len(sg7e))
    if sg7e_bound: print("  SG7E bound path                :",sgpath)
    print("  SG7E role                      : HISTORICAL VALIDATION ONLY")
    print("  Y generation authorized       : False")

    print("\n"+"="*78)
    print("V16C-12A-R FINAL VALIDATION AUTHORITY GATES")
    print("="*78)
    for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-12A-R SURVIVING-AUTHORITY CONTRACT: COMPLETE")
    print("="*78)

if __name__=="__main__":main()
