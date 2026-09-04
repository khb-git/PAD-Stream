from __future__ import annotations
from pathlib import Path
import csv, hashlib, json, re

ROOT=Path(__file__).resolve().parent
R2D=ROOT/"output"/"V16_C12R2_FROZEN_V15_100D_COMPETING_PROVENANCE_CHAIN_RESIDUAL_AUDIT"
R2S=R2D/"PAD_Stream_V16C12R2_Summary.json"
R2C=R2D/"V16C12R2_Competing_Provenance_Residual_Contract.json"
R2DETAIL=R2D/"V16C12R2_Competing_Artifact_Detail.csv"
R2AUTH=R2D/"V16C12R2_Authority_Record_Trace.csv"
R2PROD=R2D/"V16C12R2_Producer_Manifest_Trace.csv"

OUT=ROOT/"output"/"V16_C12R3_EXACT_V15_PRODUCER_MANIFEST_SUPERSESSION_AUDIT"
OUT.mkdir(parents=True,exist_ok=True)
ART=OUT/"V16C12R3_Competing_Artifact_Producer_Trace.csv"
TEXT=OUT/"V16C12R3_Explicit_Supersession_Evidence.csv"
REL=OUT/"V16C12R3_Artifact_Supersession_Relations.csv"
GATES=OUT/"V16C12R3_Final_Supersession_Gates.csv"
DEC=OUT/"V16C12R3_Reference_Supersession_Decision.csv"
CON=OUT/"V16C12R3_Producer_Manifest_Supersession_Contract.json"
SUM=OUT/"PAD_Stream_V16C12R3_Summary.json"

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
    with p.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def resolve_rel(s):
    p=ROOT/str(s)
    return p if p.exists() else None

def readable_text(p):
    if p.suffix.lower() not in (".json",".csv",".txt",".py",".md"): return ""
    try:return p.read_text(encoding="utf-8",errors="replace")
    except Exception:return ""

def explicit_terms(text):
    low=text.lower()
    # Strong terms require explicit replacement/authority language.
    patterns=[
        r"\bsupersed(?:e|es|ed|ing)\b",
        r"\breplac(?:e|es|ed|ing)\b",
        r"\bdeprecated\b",
        r"\bobsolete\b",
        r"\bretired\b",
        r"\bfinal\s+(?:frozen|freeze|deployment|reference|authority)\b",
        r"\bauthoritative\s+(?:artifact|reference|deployment|state)\b",
        r"\bcanonical\s+(?:artifact|reference|deployment|state)\b",
        r"\bdo\s+not\s+use\b",
        r"\bhistorical\s+(?:only|reference|artifact|state)\b",
        r"\bnon[- ]?authoritative\b",
    ]
    hits=[]
    for pat in patterns:
        for m in re.finditer(pat,low,re.I):
            a=max(0,m.start()-180); b=min(len(text),m.end()+260)
            hits.append((pat,text[a:b].replace("\n"," ").strip()))
    return hits

def mentions(text, tokens):
    low=text.lower()
    return [t for t in tokens if t.lower() in low]

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-12R3")
    print("Exact V15 Producer/Manifest Supersession Audit")
    print("="*78)
    print("""
R2 LEFT THREE DISTINCT FROZEN-100D ARTIFACT HASHES.

R3 MAY RESOLVE THEM ONLY FROM EXPLICIT PRODUCER/MANIFEST/SUMMARY/CONTRACT
LINEAGE. IT WILL NOT USE:
  - FILE TIMESTAMPS
  - LEXICAL VERSION ORDERING
  - DIRECTORY DEPTH
  - NUMERICAL SIMILARITY
  - "NEWEST" OR "BEST LOOKING" FILENAMES

R3 SEARCHES THE ALREADY-TRACED V15 AUTHORITY/PRODUCER RECORDS FOR EXPLICIT
SUPERSESSION OR FINAL-AUTHORITY LANGUAGE AND REQUIRES THAT SUCH LANGUAGE
IDENTIFY THE COMPETING ARTIFACT(S) BY PATH, BASENAME, OR SHA-256.

NO Y_TRANSPORT IS GENERATED AND NO FROZEN ARTIFACT IS MODIFIED.
""")
    for p in [R2S,R2C,R2DETAIL,R2AUTH,R2PROD]:
        if not p.exists(): raise FileNotFoundError(p)
    r2=loadj(R2S)
    if r2.get("status")!="V16C_FROZEN_V15_100D_COMPETING_PROVENANCE_REMAINS_UNRESOLVED":
        raise RuntimeError("R3 requires unresolved R2 status.")

    detail=read_csv(R2DETAIL)
    prod=read_csv(R2PROD)
    hashes=[r["artifact_sha256"] for r in detail]
    if len(set(hashes))<3: raise RuntimeError("Expected >=3 competing hashes.")

    # Gather exact path/basename/hash tokens for each competing artifact.
    tokens={}
    for r in detail:
        h=r["artifact_sha256"]
        ps=[x.strip() for x in r["artifact_paths"].split(" | ") if x.strip()]
        toks=[h,h[:16],h[:12]]
        for x in ps:
            toks += [x,Path(x).name]
        tokens[h]=sorted(set(toks),key=len,reverse=True)

    trace_rows=[]
    evidence=[]
    files_seen={}
    for row in prod:
        rp=resolve_rel(row["referenced_path"])
        if not rp or not rp.is_file(): continue
        key=str(rp.resolve())
        if key in files_seen: continue
        files_seen[key]=rp
        text=readable_text(rp)
        if not text: continue
        hits=explicit_terms(text)
        alltokens=[t for ts in tokens.values() for t in ts]
        mentioned=mentions(text,alltokens)
        trace_rows.append(dict(
            referenced_path=str(rp.relative_to(ROOT)),
            sha256=sha(rp),suffix=rp.suffix.lower(),
            explicit_authority_term_count=len(hits),
            competing_artifact_token_mentions=len(mentioned)
        ))
        if hits and mentioned:
            for pat,snip in hits:
                mh=[]
                for h,ts in tokens.items():
                    if any(t.lower() in snip.lower() for t in ts):
                        mh.append(h)
                if mh:
                    evidence.append(dict(
                        source_path=str(rp.relative_to(ROOT)),
                        source_sha256=sha(rp),
                        authority_pattern=pat,
                        mentioned_artifact_hashes=" | ".join(sorted(set(mh))),
                        evidence_excerpt=snip[:700]
                    ))

    save_csv(ART,trace_rows)
    save_csv(TEXT,evidence)

    # Build explicit directed relations only when a single evidence excerpt
    # identifies both an authority/replacement semantic and concrete artifact.
    # Classification is conservative:
    # - "final/authoritative/canonical" => positive authority for mentioned hash
    # - "superseded/replaced/deprecated/obsolete/retired/do not use/historical/
    #   non-authoritative" => negative/superseded for mentioned hash.
    pos={h:[] for h in hashes}; neg={h:[] for h in hashes}
    relrows=[]
    for e in evidence:
        pat=e["authority_pattern"].lower()
        hs=[x.strip() for x in e["mentioned_artifact_hashes"].split(" | ") if x.strip()]
        positive=any(x in pat for x in ("final","authoritative","canonical"))
        negative=any(x in pat for x in ("supersed","replac","deprecated","obsolete",
                                        "retired","do\\s+not\\s+use","historical","non[- ]?authoritative"))
        for h in hs:
            if positive:
                pos[h].append(e["source_path"])
                relrows.append(dict(artifact_sha256=h,relation="EXPLICIT_FINAL_AUTHORITY",
                                    source_path=e["source_path"],pattern=e["authority_pattern"]))
            if negative:
                neg[h].append(e["source_path"])
                relrows.append(dict(artifact_sha256=h,relation="EXPLICIT_SUPERSEDED_OR_NONAUTHORITY",
                                    source_path=e["source_path"],pattern=e["authority_pattern"]))
    save_csv(REL,relrows)

    # Unique winner requires positive explicit authority and no negative evidence,
    # while every other candidate has explicit negative/superseded evidence.
    winners=[h for h in hashes if pos[h] and not neg[h]]
    resolved=False; winner=None
    if len(winners)==1:
        w=winners[0]
        others=[h for h in hashes if h!=w]
        resolved=all(bool(neg[h]) for h in others)
        if resolved:winner=w

    gates=[
        ("R2_unresolved_status_reproduced",True),
        ("competing_hashes_reproduced",len(set(hashes))>=3),
        ("producer_manifest_trace_loaded",len(prod)>0),
        ("referenced_text_records_scanned",len(trace_rows)>0),
        ("no_timestamp_selection",True),
        ("no_version_number_ordering_selection",True),
        ("no_numerical_similarity_selection",True),
        ("explicit_supersession_or_authority_evidence_found",len(evidence)>0),
        ("explicit_evidence_mentions_concrete_competing_artifact",len(evidence)>0),
        ("unique_positive_final_authority_candidate",len(winners)==1),
        ("all_other_candidates_explicitly_superseded_or_nonauthoritative",
         bool(winner) and all(bool(neg[h]) for h in hashes if h!=winner)),
        ("no_250_500_1000_promotion",True),
        ("no_Y_transport_generated",True),
        ("no_frozen_artifact_mutation",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])

    bound_path=None
    if resolved:
        rr=next(r for r in detail if r["artifact_sha256"]==winner)
        bound_path=rr["artifact_paths"]

    if resolved:
        status="V16C_FROZEN_V15_100D_REFERENCE_EXPLICITLY_SUPERSESSION_RESOLVED"
        diagnosis="ONE_COMPETING_HASH_IS_EXPLICITLY_IDENTIFIED_AS_FINAL_AUTHORITY_AND_EACH_OTHER_HASH_IS_EXPLICITLY_SUPERSEDED_OR_NONAUTHORITATIVE_BY_V15_PRODUCER_MANIFEST_RECORDS"
        rec="Freeze R3 provenance resolution. Proceed to C12A numerical cross-authority validation. Do not fit V16 to the V15 reference."
        nxt="V16C-12A — Pollock Solver vs Frozen V15 100-Day Numerical Cross-Authority Validation"
    else:
        status="V16C_FROZEN_V15_100D_REFERENCE_NOT_RESOLVABLE_BY_EXPLICIT_SUPERSESSION_RECORDS"
        diagnosis="THE_LOCAL_V15_PRODUCER_MANIFEST_RECORDS_DO_NOT_EXPLICITLY_IDENTIFY_ONE_COMPETING_HASH_AS_FINAL_WHILE_SUPERSEDING_ALL_OTHERS"
        rec=("Do not choose among the three hashes. Freeze the negative provenance finding. "
             "The next milestone must determine the intended frozen 100-day authority from the formal V15 freeze contract/runbook or regenerate the comparison from the exact frozen source recipe if that contract explicitly authorizes regeneration.")
        nxt="V16C-12R4 — Formal V15 Freeze Contract and Source-Recipe Authority Audit"

    save_csv(DEC,[dict(status=status,diagnosis=diagnosis,
        competing_hash_count=len(set(hashes)),scanned_record_count=len(trace_rows),
        explicit_evidence_count=len(evidence),positive_candidate_count=len(winners),
        reference_resolved=resolved,bound_sha256=winner or "",
        bound_path=bound_path or "",numerical_comparison_executed=False,
        Y_generation_authorized=False,next_milestone=nxt)])
    savej(CON,dict(milestone="V16C-12R3",status=status,diagnosis=diagnosis,
        competing_hashes=hashes,positive_authority_sources=pos,
        supersession_or_nonauthority_sources=neg,
        bound_reference_sha256=winner,bound_reference_path=bound_path,
        resolution_rule="explicit final authority for winner + explicit supersession/nonauthority for every competitor",
        numerical_comparison_executed=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))
    savej(SUM,dict(milestone="V16C-12R3",status=status,diagnosis=diagnosis,
        competing_hash_count=len(set(hashes)),scanned_record_count=len(trace_rows),
        explicit_evidence_count=len(evidence),reference_resolved=resolved,
        reference_sha256=winner,reference_path=bound_path,
        Y_transport_generated=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))

    print("EXACT PRODUCER/MANIFEST TRACE")
    print("  competing hashes                  :",len(set(hashes)))
    print("  referenced text records scanned   :",len(trace_rows))
    print("  explicit artifact-linked evidence :",len(evidence))
    print("  positive authority candidates     :",len(winners))
    print("  unique reference resolved         :",resolved)
    if resolved:
        print("  SHA-256                           :",winner)
        print("  path(s)                           :",bound_path)
    else:
        print("  timestamp selection               : PROHIBITED")
        print("  numerical similarity selection    : PROHIBITED")
        print("  implicit version ordering         : PROHIBITED")

    print("\n"+"="*78)
    print("V16C-12R3 FINAL SUPERSESSION GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-12R3 PRODUCER/MANIFEST SUPERSESSION AUDIT: COMPLETE")
    print("="*78)

if __name__=="__main__": main()
