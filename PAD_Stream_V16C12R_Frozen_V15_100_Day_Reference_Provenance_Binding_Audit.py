from __future__ import annotations
from pathlib import Path
import csv, hashlib, json, re

ROOT=Path(__file__).resolve().parent
C12D=ROOT/"output"/"V16_C12_FULL_PHYSICS_POLLOCK_LIMITING_CASE_FROZEN_REFERENCE_VALIDATION"
C12S=C12D/"PAD_Stream_V16C12_Summary.json"
C12C=C12D/"V16C12_Validation_Contract.json"
C12DISC=C12D/"V16C12_Frozen_V15_100d_Reference_Discovery.csv"

OUT=ROOT/"output"/"V16_C12R_FROZEN_V15_100D_REFERENCE_PROVENANCE_BINDING_AUDIT"
OUT.mkdir(parents=True,exist_ok=True)
INV=OUT/"V16C12R_Candidate_Provenance_Inventory.csv"
CHAINS=OUT/"V16C12R_Provenance_Chains.csv"
GATES=OUT/"V16C12R_Final_Provenance_Gates.csv"
DEC=OUT/"V16C12R_Reference_Binding_Decision.csv"
CON=OUT/"V16C12R_Frozen_V15_100d_Reference_Provenance_Contract.json"
SUM=OUT/"PAD_Stream_V16C12R_Summary.json"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def loadj(p): return json.loads(p.read_text(encoding="utf-8"))
def savej(p,x): p.write_text(json.dumps(x,indent=2),encoding="utf-8")
def save_csv(p,rows):
    rows=list(rows); keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)

def flatten(obj,prefix=""):
    out=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            key=f"{prefix}.{k}" if prefix else str(k)
            out.extend(flatten(v,key))
    elif isinstance(obj,list):
        for i,v in enumerate(obj):
            out.extend(flatten(v,f"{prefix}[{i}]"))
    else:
        out.append((prefix,obj))
    return out

def extract_refs(j):
    refs=[]
    for key,val in flatten(j):
        if not isinstance(val,str): continue
        s=val.strip()
        low=s.lower()
        if any(t in key.lower() for t in ("path","file","artifact","source","input","npz","reference","deployment")):
            if any(ext in low for ext in (".npz",".json",".csv",".npy",".zip",".py")) or "\\" in s or "/" in s:
                refs.append((key,s))
    return refs

def resolve_ref(source_json,ref):
    raw=ref.replace("\\","/")
    candidates=[]
    p=Path(raw)
    if p.is_absolute(): candidates.append(p)
    candidates += [ROOT/raw, source_json.parent/raw, ROOT/"output"/raw]
    for c in candidates:
        try:
            if c.exists() and c.is_file(): return c.resolve()
        except OSError: pass
    # exact basename fallback only; never numerical matching
    base=Path(raw).name
    if base:
        hits=[p for p in (ROOT/"output").rglob(base) if p.is_file()]
        if len(hits)==1: return hits[0].resolve()
    return None

def text_flags(text):
    low=text.lower()
    has100=bool(re.search(r"\b100(?:\.0)?\s*(?:d|day|days)\b|100[-_ ]?day|100d",low))
    frozen=("frozen" in low)
    certified=("certified" in low)
    notcert=("not certified" in low or "uncertified" in low)
    sg7d6=("sg7d6" in low or "sg7d-6" in low)
    deploy=("deploy" in low)
    reference=("reference" in low)
    prohibited_later=bool(re.search(r"(250|500|1000).{0,100}(not certified|uncertified|prohibit)",low,re.S))
    return has100,frozen,certified,notcert,sg7d6,deploy,reference,prohibited_later

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-12R")
    print("Frozen V15 100-Day Reference Provenance Binding Audit")
    print("="*78)
    print("""
C12 PHYSICS HIERARCHY IS FROZEN AS VALIDATED.

C12R DOES NOT SELECT A REFERENCE BY NUMERICAL CLOSENESS.
C12R DOES NOT RELABEL A FILE BECAUSE ITS NAME CONTAINS "100".
C12R DOES NOT PROMOTE V15 250/500/1000-DAY STATES.
C12R DOES NOT GENERATE TRANSPORT OR MODIFY FROZEN ARTIFACTS.

THE AUDIT SEARCHES THE LOCAL V15 OUTPUT TREE FOR EXPLICIT METADATA AND
FILE-REFERENCE CHAINS THAT CONNECT:
  FROZEN/CERTIFIED AUTHORITY -> 100-DAY STATE -> CONCRETE NUMERICAL ARTIFACT.

A REFERENCE IS BOUND ONLY IF ONE CONCRETE NUMERICAL ARTIFACT HAS A UNIQUE,
EXPLICIT PROVENANCE CHAIN.
""")
    for p in [C12S,C12C,C12DISC]:
        if not p.exists(): raise FileNotFoundError(p)
    c12=loadj(C12S)
    if c12.get("status")!="V16C_LIMITING_CASE_HIERARCHY_VALIDATED_FROZEN_V15_100D_REFERENCE_BINDING_REQUIRED":
        raise RuntimeError("C12R requires C12 reference-binding-required status.")

    outroot=ROOT/"output"
    jsons=[p for p in outroot.rglob("*.json")
           if "V16_" not in str(p) and "V16C" not in str(p)]
    inventory=[]
    chains=[]

    for jp in jsons:
        try:
            j=loadj(jp)
            blob=json.dumps(j)
        except Exception:
            continue
        has100,frozen,certified,notcert,sg7d6,deploy,reference,prohibited_later=text_flags(blob)
        refs=extract_refs(j)
        resolved=[]
        for key,r in refs:
            rp=resolve_ref(jp,r)
            if rp is None: continue
            if rp.suffix.lower() not in (".npz",".npy",".csv"): continue
            resolved.append((key,rp))
        inventory.append(dict(
            json_path=str(jp.relative_to(ROOT)),sha256=sha(jp),
            has_100day=has100,frozen=frozen,certified=certified,
            explicit_not_certified=notcert,mentions_SG7D6=sg7d6,
            mentions_deployment=deploy,mentions_reference=reference,
            later_times_explicitly_prohibited=prohibited_later,
            resolved_numerical_refs=len(resolved)
        ))
        # Strict authority requires 100d + affirmative freeze/certification and
        # no global "not certified" contamination. SG7D6/reference/deployment
        # context strengthens the chain but does not substitute for it.
        authority=has100 and (frozen or certified) and not notcert
        if authority:
            for key,rp in resolved:
                rlow=str(rp).lower()
                # Concrete artifact must itself be tied to 100d or SG7D6 context.
                artifact_context=("100" in rp.name.lower() or sg7d6 or "sg7d6" in rlow)
                if artifact_context:
                    chains.append(dict(
                        authority_json=str(jp.relative_to(ROOT)),
                        authority_json_sha256=sha(jp),
                        reference_key=key,
                        artifact_path=str(rp.relative_to(ROOT)),
                        artifact_sha256=sha(rp),
                        authority_has_100day=has100,
                        authority_frozen=frozen,
                        authority_certified=certified,
                        authority_SG7D6=sg7d6,
                        authority_reference=reference,
                        authority_deployment=deploy,
                    ))

    save_csv(INV,inventory)

    # Collapse multiple metadata records pointing to the same immutable bytes.
    by_hash={}
    for c in chains:
        by_hash.setdefault(c["artifact_sha256"],[]).append(c)
    chain_rows=[]
    for h,cs in by_hash.items():
        paths=sorted(set(c["artifact_path"] for c in cs))
        auths=sorted(set(c["authority_json"] for c in cs))
        chain_rows.append(dict(
            artifact_sha256=h,
            artifact_paths=" | ".join(paths),
            authority_jsons=" | ".join(auths),
            chain_count=len(cs),
            unique_path_count=len(paths)
        ))
    save_csv(CHAINS,chain_rows)

    unique_hash=len(by_hash)==1
    unique_path=False
    bound_path=None; bound_sha=None
    if unique_hash:
        bound_sha=next(iter(by_hash))
        paths=sorted(set(c["artifact_path"] for c in by_hash[bound_sha]))
        unique_path=len(paths)==1
        if unique_path: bound_path=paths[0]

    # If metadata chains remain ambiguous, that is the correct result. Do not
    # resolve by array values, timestamps, or filename preference.
    bound=unique_hash and unique_path

    gates=[
        ("C12_reference_binding_required_status_reproduced",True),
        ("C12_limiting_case_physics_remains_validated",bool(c12.get("limiting_case_physics_validated"))),
        ("V15_JSON_metadata_inventory_completed",len(inventory)>0),
        ("no_numerical_closeness_selection",True),
        ("no_filename_only_certification",True),
        ("no_250_500_1000_state_promotion",True),
        ("explicit_authority_to_numerical_artifact_chains_found",len(chains)>0),
        ("unique_concrete_artifact_hash_bound",unique_hash),
        ("unique_concrete_artifact_path_bound",unique_path),
        ("no_Y_transport_generated",True),
        ("no_model_predict",True),
        ("no_training",True),
        ("no_frozen_artifact_mutation",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])

    if bound:
        status="V16C_FROZEN_V15_100D_REFERENCE_PROVENANCE_BOUND"
        diagnosis="A_UNIQUE_CONCRETE_V15_100DAY_NUMERICAL_ARTIFACT_IS_EXPLICITLY_BOUND_THROUGH_FROZEN_CERTIFIED_METADATA_PROVENANCE"
        rec="Freeze C12R provenance. Proceed to C12A numerical cross-authority validation; do not fit or recalibrate the V16 solver to the V15 reference."
        nxt="V16C-12A — Pollock Solver vs Frozen V15 100-Day Numerical Cross-Authority Validation"
    else:
        status="V16C_FROZEN_V15_100D_REFERENCE_PROVENANCE_REMAINS_AMBIGUOUS"
        diagnosis="LOCAL_METADATA_DOES_NOT_YET_FORM_ONE_UNIQUE_EXPLICIT_AUTHORITY_TO_NUMERICAL_ARTIFACT_CHAIN"
        rec=("Do not select among candidates by filename, timestamp, or numerical similarity. Inspect the C12R provenance-chain table. "
             "A subsequent residual audit must trace the competing authority JSON records to their producer scripts/manifests or exact hashes.")
        nxt="V16C-12R2 — Frozen V15 100-Day Competing Provenance Chain Residual Audit"

    save_csv(DEC,[dict(status=status,diagnosis=diagnosis,
        metadata_json_count=len(inventory),explicit_chain_count=len(chains),
        unique_artifact_hash_count=len(by_hash),
        bound_reference_path=bound_path or "",bound_reference_sha256=bound_sha or "",
        numerical_comparison_executed=False,Y_generation_authorized=False,next_milestone=nxt)])
    savej(CON,dict(milestone="V16C-12R",status=status,diagnosis=diagnosis,
        metadata_json_count=len(inventory),explicit_chain_count=len(chains),
        unique_artifact_hash_count=len(by_hash),
        frozen_V15_100d_reference_path=bound_path,
        frozen_V15_100d_reference_sha256=bound_sha,
        selection_method="explicit metadata/file-reference provenance only; no numerical closeness",
        numerical_comparison_executed=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))
    savej(SUM,dict(milestone="V16C-12R",status=status,diagnosis=diagnosis,
        metadata_json_count=len(inventory),explicit_chain_count=len(chains),
        unique_artifact_hash_count=len(by_hash),
        reference_bound=bound,reference_path=bound_path,
        Y_transport_generated=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))

    print("PROVENANCE INVENTORY")
    print("  V15 JSON metadata files            :",len(inventory))
    print("  explicit authority->artifact chains:",len(chains))
    print("  unique numerical artifact hashes   :",len(by_hash))
    print("  unique concrete reference bound    :",bound)
    if bound:
        print("  reference                           :",bound_path)
        print("  SHA-256                             :",bound_sha)
    else:
        print("  selection by numerical closeness    : PROHIBITED")
        print("  selection by filename/timestamp      : PROHIBITED")

    print("\n"+"="*78)
    print("V16C-12R FINAL PROVENANCE GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-12R FROZEN V15 100-DAY PROVENANCE AUDIT: COMPLETE")
    print("="*78)

if __name__=="__main__": main()
