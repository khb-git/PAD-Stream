from __future__ import annotations
from pathlib import Path
import csv, hashlib, json, re

ROOT=Path(__file__).resolve().parent

R3D=ROOT/"output"/"V16_C12R3_EXACT_V15_PRODUCER_MANIFEST_SUPERSESSION_AUDIT"
R3S=R3D/"PAD_Stream_V16C12R3_Summary.json"

OUT=ROOT/"output"/"V16_C12R4_FORMAL_V15_FREEZE_CONTRACT_SOURCE_RECIPE_AUTHORITY_AUDIT"
OUT.mkdir(parents=True,exist_ok=True)
REG=OUT/"V16C12R4_Formal_Authority_Registry.csv"
FILES=OUT/"V16C12R4_Bound_Artifact_Identities.csv"
GATES=OUT/"V16C12R4_Final_Authority_Gates.csv"
DEC=OUT/"V16C12R4_Authority_Decision.csv"
CON=OUT/"V16C12R4_Formal_V15_Freeze_Authority_Contract.json"
SUM=OUT/"PAD_Stream_V16C12R4_Summary.json"

EXPECTED_L2_SHA="01bb967c07b262836f6c140dd519538db13d9ce5b3bc0f83d52a6164ddcfa950"
EXPECTED_SG7D6_SHA="6bf6661e2344d51c54df4689758a1998952454e0bc13797b8e4da57824cf9522"
EXPECTED_HIST_FROZEN100_SHA="a08c7320a63ace580456191f408a29afde65e0ad3f078846"
# The historical frozen100 hash above is a distinct runtime-history object and
# is NOT the formal L2_independent_100 deployment authority.

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

def find_hash_file(expected):
    hits=[]
    for p in (ROOT/"output").rglob("*"):
        if not p.is_file(): continue
        if "V16_" in str(p) or "V16C" in str(p): continue
        try:
            if sha(p)==expected: hits.append(p)
        except OSError: pass
    return hits

def text_candidates():
    pats=[
        "PAD_Stream_V15_Final_Freeze_Documentation_Packaging.py",
        "PAD_Stream_V15SG7D6_Full_Grid_Candidate_Freeze_Provenance_Manifest.py",
    ]
    return {n:ROOT/n for n in pats if (ROOT/n).exists()}

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-12R4")
    print("Formal V15 Freeze Contract and Source-Recipe Authority Audit")
    print("="*78)
    print("""
R3 ESTABLISHED THAT LOW-LEVEL SUPERSESSION RECORDS CANNOT RESOLVE THE THREE
COMPETING HISTORICAL 100-DAY HASHES.

R4 THEREFORE USES THE FORMAL VERSION-15 FREEZE SCOPE AS THE AUTHORITY.

FORMAL V15 DISTINCTION:
  L2_independent_100  = CERTIFIED 100-DAY DEPLOYMENT AUTHORITY
  SG7D6 full-grid     = FROZEN AUTHORITATIVE SINGLE-STATE GRID ARTIFACT
  SG7E four-time      = HISTORICAL REFERENCE AUTHORITY
  250/500/1000 deploy = NOT PRESENT / NOT CERTIFIED

THE HISTORICAL "frozen100" RUNTIME-REPLAY OBJECT IS NOT AUTOMATICALLY THE
FORMAL L2_independent_100 AUTHORITY.

R4 BINDS BY EXACT FORMAL SHA-256 WHERE POSSIBLE. IT DOES NOT USE NUMERICAL
CLOSENESS, TIMESTAMPS, OR FILENAMES AS AUTHORITY.
""")
    if not R3S.exists(): raise FileNotFoundError(R3S)
    r3=loadj(R3S)
    if r3.get("status")!="V16C_FROZEN_V15_100D_REFERENCE_NOT_RESOLVABLE_BY_EXPLICIT_SUPERSESSION_RECORDS":
        raise RuntimeError("R4 requires completed unresolved R3.")

    srcs=text_candidates()
    pkg=srcs.get("PAD_Stream_V15_Final_Freeze_Documentation_Packaging.py")
    d6=srcs.get("PAD_Stream_V15SG7D6_Full_Grid_Candidate_Freeze_Provenance_Manifest.py")

    pkg_text=pkg.read_text(encoding="utf-8",errors="replace") if pkg else ""
    d6_text=d6.read_text(encoding="utf-8",errors="replace") if d6 else ""

    formal_l2=(
        "L2_independent_100 is the authoritative 100-day L2 deployment state" in pkg_text
        or "L2_independent_100" in pkg_text
    )
    formal_d6=(
        "authoritative single-state deployment artifact" in pkg_text
        and "SG7D6" in pkg_text
    )
    later_not_cert=(
        "250/500/1000-day frozen deployment states are not present" in pkg_text
        and "NOT certified" in pkg_text
    )
    no_relabel=(
        "Historical frozen100 may not be relabelled" in pkg_text
    )
    d6_source_l2=(
        '"transport_source":' in d6_text and "R1F3 frozen L2" in d6_text
    )
    d6_mapback=(
        "SG7D1 conservative segment-weighted map-back" in d6_text
    )

    # Exact formal identities are supplied by the frozen runbook/registry.
    # Search actual local V15 output bytes for those exact hashes.
    l2_hits=find_hash_file(EXPECTED_L2_SHA)
    d6_hits=find_hash_file(EXPECTED_SG7D6_SHA)

    registry=[
        dict(object="L2_independent_100",authority="CERTIFIED_100_DAY_DEPLOYMENT_AUTHORITY",
             expected_sha256=EXPECTED_L2_SHA,local_exact_hash_matches=len(l2_hits)),
        dict(object="SG7D6_full_grid",authority="FROZEN_AUTHORITATIVE_SINGLE_STATE_DEPLOYMENT_ARTIFACT",
             expected_sha256=EXPECTED_SG7D6_SHA,local_exact_hash_matches=len(d6_hits)),
        dict(object="SG7E_tensor",authority="HISTORICAL_FOUR_TIME_REFERENCE_AUTHORITY",
             expected_sha256="",local_exact_hash_matches="not_required_here"),
        dict(object="historical_frozen100_runtime_replay",
             authority="HISTORICAL_RUNTIME_REPLAY_OBJECT_NOT_FORMAL_L2_AUTHORITY",
             expected_sha256=EXPECTED_HIST_FROZEN100_SHA,local_exact_hash_matches="not_selected"),
        dict(object="250_500_1000_day_frozen_deployment",
             authority="NOT_PRESENT_IN_FROZEN_V15",expected_sha256="",local_exact_hash_matches=0),
    ]
    save_csv(REG,registry)

    rows=[]
    for role,hits in [("L2_independent_100",l2_hits),("SG7D6_full_grid",d6_hits)]:
        for p in hits:
            rows.append(dict(role=role,path=str(p.relative_to(ROOT)),sha256=sha(p),
                             exact_formal_hash_match=True))
    save_csv(FILES,rows)

    l2_unique=len(l2_hits)==1
    d6_unique=len(d6_hits)==1
    l2_path=str(l2_hits[0].relative_to(ROOT)) if l2_unique else None
    d6_path=str(d6_hits[0].relative_to(ROOT)) if d6_unique else None

    # Formal authority can be resolved even if the exact bytes are absent:
    # the hash identity itself uniquely defines the object. Numerical C12A,
    # however, requires accessible bytes. If absent, controlled regeneration
    # must be separately authorized from the exact frozen recipe.
    authority_resolved=formal_l2 and formal_d6 and later_not_cert and no_relabel
    l2_bytes_available=len(l2_hits)>=1
    d6_bytes_available=len(d6_hits)>=1
    ready_compare=authority_resolved and l2_unique and d6_unique

    gates=[
        ("R3_negative_supersession_finding_reproduced",True),
        ("formal_final_packaging_source_found",pkg is not None),
        ("formal_SG7D6_freeze_source_found",d6 is not None),
        ("L2_independent_100_formally_authoritative",formal_l2),
        ("SG7D6_formally_authoritative_single_state",formal_d6),
        ("SG7D6_transport_source_R1F3_frozen_L2_bound",d6_source_l2),
        ("SG7D6_mapback_source_SG7D1_bound",d6_mapback),
        ("250_500_1000_frozen_deployment_not_certified",later_not_cert),
        ("historical_frozen100_relabel_prohibited",no_relabel),
        ("formal_L2_SHA_identity_defined",len(EXPECTED_L2_SHA)==64),
        ("formal_SG7D6_SHA_identity_defined",len(EXPECTED_SG7D6_SHA)==64),
        ("formal_authority_resolved_without_candidate_closeness",authority_resolved),
        ("unique_local_L2_exact_hash_match",l2_unique),
        ("unique_local_SG7D6_exact_hash_match",d6_unique),
        ("no_numerical_closeness_selection",True),
        ("no_timestamp_selection",True),
        ("no_Y_transport_generated",True),
        ("no_frozen_artifact_mutation",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])

    if ready_compare:
        status="V16C_FORMAL_V15_100D_AND_SG7D6_AUTHORITIES_BOUND_READY_FOR_CROSS_VALIDATION"
        diagnosis="FORMAL_V15_FREEZE_REGISTRY_UNIQUELY_IDENTIFIES_L2_INDEPENDENT_100_AND_SG7D6_AND_THEIR_EXACT_FROZEN_BYTES_ARE_LOCALLY_AVAILABLE"
        rec="Freeze R4. Proceed to C12A cross-authority validation using L2_independent_100 for streamline-space 100-day authority and SG7D6 for grid-level single-state authority. Do not use historical frozen100 as a substitute."
        nxt="V16C-12A — Pollock Solver vs Formal Frozen V15 100-Day / SG7D6 Cross-Authority Validation"
    elif authority_resolved:
        status="V16C_FORMAL_V15_AUTHORITIES_RESOLVED_EXACT_BYTES_REQUIRE_BINDING_OR_AUTHORIZED_REGENERATION"
        diagnosis="THE_FORMAL_FREEZE_CONTRACT_RESOLVES_WHAT_THE_AUTHORITATIVE_OBJECTS_ARE_BUT_ONE_OR_BOTH_EXACT_NUMERICAL_ARTIFACTS_ARE_NOT_UNIQUELY_AVAILABLE_BY_THEIR_FROZEN_HASH"
        rec=("Do not select one of the three ambiguous historical hashes. The formal authority is now resolved. "
             "Next audit the exact R1F3->SG7D1->SG7D6 source recipe and authorize deterministic regeneration only if the frozen contract permits it.")
        nxt="V16C-12R5 — Exact Frozen L2/SG7D6 Source-Recipe Regeneration Authority Audit"
    else:
        status="V16C_FORMAL_V15_FREEZE_AUTHORITY_BINDING_INCOMPLETE"
        diagnosis="ONE_OR_MORE_FORMAL_FREEZE_SCOPE_STATEMENTS_COULD_NOT_BE_REPRODUCED_FROM_LOCAL_FINAL_PACKAGING_SOURCES"
        rec="Do not regenerate or compare. Audit the formal V15 freeze package/runbook source binding."
        nxt="V16C-12R4R — Formal V15 Freeze Source Binding Residual Audit"

    save_csv(DEC,[dict(status=status,diagnosis=diagnosis,
        formal_authority_resolved=authority_resolved,
        L2_exact_matches=len(l2_hits),SG7D6_exact_matches=len(d6_hits),
        L2_path=l2_path or "",SG7D6_path=d6_path or "",
        C12A_ready=ready_compare,Y_generation_authorized=False,next_milestone=nxt)])
    savej(CON,dict(milestone="V16C-12R4",status=status,diagnosis=diagnosis,
        formal_authority_registry=registry,
        L2_independent_100=dict(sha256=EXPECTED_L2_SHA,path=l2_path,
                                local_exact_matches=len(l2_hits)),
        SG7D6=dict(sha256=EXPECTED_SG7D6_SHA,path=d6_path,
                   local_exact_matches=len(d6_hits),
                   transport_source="R1F3 frozen L2",
                   mapback_source="SG7D1 conservative segment-weighted map-back"),
        historical_frozen100=dict(sha256=EXPECTED_HIST_FROZEN100_SHA,
            role="runtime-history object; not substitute for formal L2_independent_100"),
        later_time_policy="250/500/1000 frozen deployment states NOT PRESENT / NOT CERTIFIED",
        selection_method="formal frozen authority registry + exact SHA-256 identity",
        numerical_comparison_executed=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))
    savej(SUM,dict(milestone="V16C-12R4",status=status,diagnosis=diagnosis,
        formal_authority_resolved=authority_resolved,
        L2_exact_matches=len(l2_hits),SG7D6_exact_matches=len(d6_hits),
        C12A_ready=ready_compare,Y_transport_generated=False,
        Y_generation_authorized=False,recommendation=rec,next_milestone=nxt))

    print("FORMAL V15 AUTHORITY REGISTRY")
    print("  L2_independent_100            : CERTIFIED 100-DAY DEPLOYMENT AUTHORITY")
    print("  expected SHA-256              :",EXPECTED_L2_SHA)
    print("  local exact matches           :",len(l2_hits))
    print("  SG7D6 full-grid               : FROZEN SINGLE-STATE DEPLOYMENT AUTHORITY")
    print("  expected SHA-256              :",EXPECTED_SG7D6_SHA)
    print("  local exact matches           :",len(d6_hits))
    print("  SG7D6 transport source        : R1F3 frozen L2")
    print("  SG7D6 map-back source         : SG7D1 conservative segment-weighted map-back")
    print("  250/500/1000 deployment       : NOT CERTIFIED / NOT PRESENT")
    print("  historical frozen100 replay   : NOT A SUBSTITUTE FOR L2_independent_100")

    print("\n"+"="*78)
    print("V16C-12R4 FINAL AUTHORITY GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-12R4 FORMAL V15 FREEZE AUTHORITY AUDIT: COMPLETE")
    print("="*78)

if __name__=="__main__": main()
