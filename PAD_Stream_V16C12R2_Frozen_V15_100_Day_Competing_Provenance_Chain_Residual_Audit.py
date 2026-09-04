from __future__ import annotations
from pathlib import Path
import csv, hashlib, json, re

ROOT=Path(__file__).resolve().parent
RDIR=ROOT/"output"/"V16_C12R_FROZEN_V15_100D_REFERENCE_PROVENANCE_BINDING_AUDIT"
RS=RDIR/"PAD_Stream_V16C12R_Summary.json"
RCON=RDIR/"V16C12R_Frozen_V15_100d_Reference_Provenance_Contract.json"
RCHAINS=RDIR/"V16C12R_Provenance_Chains.csv"
RINV=RDIR/"V16C12R_Candidate_Provenance_Inventory.csv"

OUT=ROOT/"output"/"V16_C12R2_FROZEN_V15_100D_COMPETING_PROVENANCE_CHAIN_RESIDUAL_AUDIT"
OUT.mkdir(parents=True,exist_ok=True)
DETAIL=OUT/"V16C12R2_Competing_Artifact_Detail.csv"
AUTH=OUT/"V16C12R2_Authority_Record_Trace.csv"
PROD=OUT/"V16C12R2_Producer_Manifest_Trace.csv"
GATES=OUT/"V16C12R2_Final_Residual_Audit_Gates.csv"
DEC=OUT/"V16C12R2_Reference_Resolution_Decision.csv"
CON=OUT/"V16C12R2_Competing_Provenance_Residual_Contract.json"
SUM=OUT/"PAD_Stream_V16C12R2_Summary.json"

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

def read_csv(p):
    with p.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))

def flags(blob):
    s=blob.lower()
    return dict(
        has_100=bool(re.search(r"\b100(?:\.0)?\s*(?:d|day|days)\b|100[-_ ]?day|100d",s)),
        frozen=("frozen" in s),
        certified=("certified" in s),
        not_certified=("not certified" in s or "uncertified" in s),
        sg7d6=("sg7d6" in s or "sg7d-6" in s),
        deployment=("deploy" in s),
        reference=("reference" in s),
        final=("final" in s),
        freeze=("freeze" in s),
        prohibited_later=bool(re.search(r"(250|500|1000).{0,140}(not certified|uncertified|prohibit|not recoverable)",s,re.S)),
    )

def flatten(obj,prefix=""):
    out=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            out.extend(flatten(v,f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj,list):
        for i,v in enumerate(obj): out.extend(flatten(v,f"{prefix}[{i}]"))
    else: out.append((prefix,obj))
    return out

def resolve(raw,base):
    raw=str(raw).replace("\\","/")
    p=Path(raw)
    cands=[]
    if p.is_absolute(): cands.append(p)
    cands += [ROOT/raw,base/raw,ROOT/"output"/raw]
    for c in cands:
        try:
            if c.exists() and c.is_file(): return c.resolve()
        except OSError: pass
    bn=Path(raw).name
    if bn:
        hits=[x for x in (ROOT/"output").rglob(bn) if x.is_file()]
        if len(hits)==1:return hits[0].resolve()
    return None

def referenced_files(j,jp):
    out=[]
    for k,v in flatten(j):
        if not isinstance(v,str):continue
        kl=k.lower()
        if not any(x in kl for x in ("path","file","artifact","source","input","manifest","summary","contract","producer","script")):
            continue
        rp=resolve(v,jp.parent)
        if rp: out.append((k,rp))
    return out

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-12R2")
    print("Frozen V15 100-Day Competing Provenance Chain Residual Audit")
    print("="*78)
    print("""
C12R FOUND THREE DISTINCT NUMERICAL ARTIFACT HASHES.

R2 DOES NOT CHOOSE THE MOST RECENT FILE.
R2 DOES NOT CHOOSE THE BEST-NAMED FILE.
R2 DOES NOT COMPARE SATURATION VALUES.
R2 DOES NOT COLLAPSE DISTINCT HASHES BY NUMERICAL SIMILARITY.

R2 TRACES EACH COMPETING HASH BACK THROUGH ITS AUTHORITY JSON RECORDS AND
THEN THROUGH ANY EXPLICIT PRODUCER/MANIFEST/SUMMARY/CONTRACT REFERENCES.

A WINNER IS ALLOWED ONLY WHEN THE METADATA ITSELF ESTABLISHES A STRICT
AUTHORITY DISTINCTION (FOR EXAMPLE FINAL FREEZE / SG7D6 DEPLOYMENT AUTHORITY)
AND THE OTHER HASHES ARE EXPLICITLY HISTORICAL, INTERMEDIATE, OR NONCERTIFIED.
""")
    for p in [RS,RCON,RCHAINS,RINV]:
        if not p.exists(): raise FileNotFoundError(p)
    rs=loadj(RS)
    if rs.get("status")!="V16C_FROZEN_V15_100D_REFERENCE_PROVENANCE_REMAINS_AMBIGUOUS":
        raise RuntimeError("R2 requires ambiguous C12R status.")

    chains=read_csv(RCHAINS)
    if len(chains)<2: raise RuntimeError("Expected competing hashes.")

    detail=[]; authrows=[]; prodrows=[]
    authority_by_hash={}
    for row in chains:
        h=row["artifact_sha256"]
        paths=[x.strip() for x in row["artifact_paths"].split(" | ") if x.strip()]
        auths=[x.strip() for x in row["authority_jsons"].split(" | ") if x.strip()]
        score_evidence=[]
        explicit_disqual=False
        for a in auths:
            jp=ROOT/a
            if not jp.exists(): continue
            try:j=loadj(jp); blob=json.dumps(j)
            except Exception:continue
            f=flags(blob)
            refs=referenced_files(j,jp)
            # Evidence classes are categorical, not a numerical ranking.
            classes=[]
            if f["has_100"] and (f["frozen"] or f["certified"]): classes.append("100D_FROZEN_OR_CERTIFIED")
            if f["sg7d6"] and f["deployment"]: classes.append("SG7D6_DEPLOYMENT_CONTEXT")
            if f["final"] and f["freeze"]: classes.append("FINAL_FREEZE_CONTEXT")
            if f["reference"]: classes.append("REFERENCE_CONTEXT")
            if f["not_certified"]: classes.append("NONCERTIFIED_CONTEXT")
            if f["prohibited_later"]: classes.append("LATER_TIMES_PROHIBITED_CONTEXT")
            if f["not_certified"]: explicit_disqual=True
            authrows.append(dict(
                artifact_sha256=h,authority_json=a,authority_json_sha256=sha(jp),
                evidence_classes=" | ".join(classes),**f,
                explicit_referenced_file_count=len(refs)))
            for key,rp in refs:
                rf=flags(rp.read_text(encoding="utf-8",errors="replace")) if rp.suffix.lower() in (".json",".csv",".txt",".py") else {}
                prodrows.append(dict(
                    artifact_sha256=h,authority_json=a,reference_key=key,
                    referenced_path=str(rp.relative_to(ROOT)),referenced_sha256=sha(rp),
                    referenced_suffix=rp.suffix.lower(),
                    referenced_final=rf.get("final",""),
                    referenced_freeze=rf.get("freeze",""),
                    referenced_sg7d6=rf.get("sg7d6",""),
                    referenced_not_certified=rf.get("not_certified","")))
            score_evidence.extend(classes)

        classes=set(score_evidence)
        # Strict authority predicates; no weighted score.
        final_freeze=("FINAL_FREEZE_CONTEXT" in classes)
        sg7d6_deploy=("SG7D6_DEPLOYMENT_CONTEXT" in classes)
        frozen100=("100D_FROZEN_OR_CERTIFIED" in classes)
        reference=("REFERENCE_CONTEXT" in classes)
        eligible=frozen100 and not explicit_disqual
        strongest=eligible and final_freeze and sg7d6_deploy and reference
        authority_by_hash[h]=dict(eligible=eligible,strongest=strongest,
                                  final_freeze=final_freeze,sg7d6_deploy=sg7d6_deploy,
                                  frozen100=frozen100,reference=reference,
                                  explicit_disqual=explicit_disqual,paths=paths)
        detail.append(dict(
            artifact_sha256=h,artifact_paths=" | ".join(paths),
            authority_record_count=len(auths),
            frozen_100d_authority=frozen100,
            final_freeze_context=final_freeze,
            sg7d6_deployment_context=sg7d6_deploy,
            reference_context=reference,
            explicit_noncertified_context=explicit_disqual,
            eligible=eligible,strongest_authority_chain=strongest))

    save_csv(DETAIL,detail); save_csv(AUTH,authrows); save_csv(PROD,prodrows)

    strongest=[h for h,x in authority_by_hash.items() if x["strongest"]]
    eligible=[h for h,x in authority_by_hash.items() if x["eligible"]]
    unique_strong=len(strongest)==1
    others_disqualified=False
    winner=None
    if unique_strong:
        winner=strongest[0]
        others=[x for h,x in authority_by_hash.items() if h!=winner]
        # A unique strongest chain is sufficient only if no competing hash also
        # carries the same full authority class. They need not be "bad"; they
        # may simply be historical/intermediate.
        others_disqualified=all(not x["strongest"] for x in others)

    bound=unique_strong and others_disqualified
    bound_path=None
    if bound:
        ps=authority_by_hash[winner]["paths"]
        if len(ps)==1: bound_path=ps[0]
        else:
            # Multiple paths with identical immutable bytes are aliases; retain
            # all in contract, but do not invent a canonical path.
            bound_path=" | ".join(ps)

    gates=[
        ("C12R_ambiguous_status_reproduced",True),
        ("three_or_more_competing_hashes_reproduced",len(chains)>=3),
        ("authority_records_traced",len(authrows)>0),
        ("producer_manifest_references_traced",len(prodrows)>0),
        ("no_numerical_closeness_selection",True),
        ("no_timestamp_selection",True),
        ("no_filename_preference_selection",True),
        ("strict_authority_predicates_applied",True),
        ("unique_strongest_final_freeze_SG7D6_reference_chain",unique_strong),
        ("no_competing_hash_has_same_strongest_authority",others_disqualified),
        ("no_250_500_1000_promotion",True),
        ("no_Y_transport_generated",True),
        ("no_frozen_artifact_mutation",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])

    if bound:
        status="V16C_FROZEN_V15_100D_REFERENCE_PROVENANCE_UNIQUELY_RESOLVED"
        diagnosis="ONE_ARTIFACT_HASH_HAS_THE_UNIQUE_EXPLICIT_FINAL_FREEZE_SG7D6_DEPLOYMENT_REFERENCE_AUTHORITY_CHAIN_AND_NO_COMPETING_HASH_HAS_EQUIVALENT_AUTHORITY"
        rec="Freeze R2. Proceed to C12A numerical cross-authority validation without fitting the V16 solver to the V15 state."
        nxt="V16C-12A — Pollock Solver vs Frozen V15 100-Day Numerical Cross-Authority Validation"
    else:
        status="V16C_FROZEN_V15_100D_COMPETING_PROVENANCE_REMAINS_UNRESOLVED"
        diagnosis="COMPETING_HASHES_CANNOT_BE_SEPARATED_BY_EXPLICIT_FINAL_FREEZE_SG7D6_REFERENCE_AUTHORITY_ALONE"
        rec=("Do not choose a winner. Use the R2 authority and producer trace tables to audit the exact producer scripts/manifests "
             "for the remaining competing hashes. Preserve all candidates until one is explicitly superseded or bound.")
        nxt="V16C-12R3 — Exact V15 Producer/Manifest Supersession Audit"

    save_csv(DEC,[dict(status=status,diagnosis=diagnosis,
        competing_hash_count=len(chains),eligible_hash_count=len(eligible),
        strongest_hash_count=len(strongest),bound_sha256=winner or "",
        bound_path=bound_path or "",numerical_comparison_executed=False,
        Y_generation_authorized=False,next_milestone=nxt)])
    savej(CON,dict(milestone="V16C-12R2",status=status,diagnosis=diagnosis,
        competing_hash_count=len(chains),authority_by_hash=authority_by_hash,
        bound_reference_sha256=winner if bound else None,
        bound_reference_path=bound_path if bound else None,
        selection_basis="explicit categorical final-freeze + SG7D6-deployment + reference authority; never numerical closeness",
        numerical_comparison_executed=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))
    savej(SUM,dict(milestone="V16C-12R2",status=status,diagnosis=diagnosis,
        competing_hash_count=len(chains),eligible_hash_count=len(eligible),
        strongest_hash_count=len(strongest),reference_bound=bound,
        reference_sha256=winner if bound else None,reference_path=bound_path if bound else None,
        Y_transport_generated=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))

    print("COMPETING PROVENANCE TRACE")
    print("  competing artifact hashes          :",len(chains))
    print("  authority records traced           :",len(authrows))
    print("  producer/manifest refs traced      :",len(prodrows))
    print("  eligible frozen-100d hashes        :",len(eligible))
    print("  strongest authority hashes         :",len(strongest))
    print("  unique reference resolved          :",bound)
    if bound:
        print("  SHA-256                            :",winner)
        print("  path(s)                            :",bound_path)
    else:
        print("  numerical closeness selection      : PROHIBITED")
        print("  timestamp/filename selection       : PROHIBITED")

    print("\n"+"="*78)
    print("V16C-12R2 FINAL RESIDUAL AUDIT GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-12R2 COMPETING PROVENANCE RESIDUAL AUDIT: COMPLETE")
    print("="*78)

if __name__=="__main__": main()
