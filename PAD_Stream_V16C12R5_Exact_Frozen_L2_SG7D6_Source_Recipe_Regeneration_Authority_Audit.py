from __future__ import annotations
from pathlib import Path
import ast, csv, hashlib, json, re

ROOT=Path(__file__).resolve().parent
R4D=ROOT/"output"/"V16_C12R4_FORMAL_V15_FREEZE_CONTRACT_SOURCE_RECIPE_AUTHORITY_AUDIT"
R4S=R4D/"PAD_Stream_V16C12R4_Summary.json"
R4C=R4D/"V16C12R4_Formal_V15_Freeze_Authority_Contract.json"

OUT=ROOT/"output"/"V16_C12R5_EXACT_FROZEN_L2_SG7D6_SOURCE_RECIPE_REGENERATION_AUTHORITY_AUDIT"
OUT.mkdir(parents=True,exist_ok=True)
SRC=OUT/"V16C12R5_Source_Recipe_Inventory.csv"
EDGE=OUT/"V16C12R5_Lineage_Edges.csv"
AUTH=OUT/"V16C12R5_Regeneration_Authority_Evidence.csv"
GATES=OUT/"V16C12R5_Final_Regeneration_Authority_Gates.csv"
DEC=OUT/"V16C12R5_Regeneration_Authority_Decision.csv"
CON=OUT/"V16C12R5_Exact_Source_Recipe_Regeneration_Authority_Contract.json"
SUM=OUT/"PAD_Stream_V16C12R5_Summary.json"

EXPECTED_L2_SHA="01bb967c07b262836f6c140dd519538db13d9ce5b3bc0f83d52a6164ddcfa950"
EXPECTED_SG7D6_SHA="6bf6661e2344d51c54df4689758a1998952454e0bc13797b8e4da57824cf9522"

NAMES=[
 "PAD_Stream_V15SG7D6_Full_Grid_Candidate_Freeze_Provenance_Manifest.py",
 "PAD_Stream_V15SG7D5_Independent_Full_Grid_Completion_Validation.py",
 "PAD_Stream_V15SG7D4_Controlled_Background_Only_Unsupported_Cell_Completion.py",
 "PAD_Stream_V15_Final_Freeze_Documentation_Packaging.py",
]

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
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

def find_sources():
    d={}
    for n in NAMES:
        p=ROOT/n
        if p.exists():d[n]=p
    # Discover R1F3 / SG7D1 producer sources by exact milestone terms.
    for p in ROOT.glob("*.py"):
        try:t=p.read_text(encoding="utf-8",errors="replace")
        except:continue
        if ("R1F3" in p.name or "SG7D1" in p.name or
            "V15-SG7C-R3F5-R1F3" in t or "V15-SG7D1" in t):
            d[p.name]=p
    return d

def literal_paths_from_source(p):
    text=p.read_text(encoding="utf-8",errors="replace")
    vals=[]
    try:
        tree=ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                s=node.value
                if any(x in s for x in (".npz",".json",".csv","frozen_candidate","V15_SG7")):
                    vals.append(s)
    except SyntaxError:pass
    return sorted(set(vals))

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-12R5")
    print("Exact Frozen L2/SG7D6 Source-Recipe Regeneration Authority Audit")
    print("="*78)
    print("""
R4 RESOLVED THE FORMAL AUTHORITY IDENTITIES BUT FOUND ZERO LOCAL BYTE-EXACT
MATCHES FOR THE CERTIFIED L2_independent_100 AND SG7D6 ARTIFACT HASHES.

R5 DOES NOT REGENERATE THEM.

R5 ASKS A NARROWER QUESTION:
  DOES THE FROZEN V15 RECORD PRESERVE AN EXACT, DETERMINISTIC, SOURCE-AUTHENTIC
  RECIPE THAT IS AUTHORIZED TO RECONSTRUCT THOSE AUTHORITIES WITHOUT TRAINING,
  MODEL REFITTING, THRESHOLD CHANGES, OR NUMERICAL-CLOSENESS SELECTION?

REQUIRED LINEAGE:
  R1F3 frozen L2
      -> SG7D1 conservative segment-weighted map-back
      -> SG7D4 controlled background completion
      -> SG7D5 independent validation
      -> SG7D6 byte-for-byte freeze

R5 AUTHORIZES REGENERATION ONLY IF THE SOURCE RECORD ESTABLISHES THIS LINEAGE
AND THE RECIPE IS DETERMINISTIC FROM ALREADY-FROZEN INPUTS. ACTUAL EXECUTION,
IF AUTHORIZED, BELONGS TO A SEPARATE CONTROLLED REGENERATION MILESTONE.
""")
    for p in [R4S,R4C]:
        if not p.exists():raise FileNotFoundError(p)
    r4=loadj(R4S)
    if r4.get("status")!="V16C_FORMAL_V15_AUTHORITIES_RESOLVED_EXACT_BYTES_REQUIRE_BINDING_OR_AUTHORIZED_REGENERATION":
        raise RuntimeError("R5 requires R4 resolved-authority/missing-bytes status.")

    srcs=find_sources()
    rows=[]
    texts={}
    for n,p in sorted(srcs.items()):
        t=p.read_text(encoding="utf-8",errors="replace");texts[n]=t
        rows.append(dict(source=n,sha256=sha(p),size_bytes=p.stat().st_size,
                         literal_recipe_refs=" | ".join(literal_paths_from_source(p))))
    save_csv(SRC,rows)

    alltext="\n".join(texts.values())
    # Structural lineage predicates.
    has_r1f3="R1F3" in alltext and "frozen" in alltext.lower()
    has_d1="SG7D1" in alltext and ("conservative" in alltext.lower() or "map-back" in alltext.lower())
    has_d4="SG7D4" in alltext and "background" in alltext.lower()
    has_d5="SG7D5" in alltext and ("independent" in alltext.lower() or "validation" in alltext.lower())
    has_d6="SG7D6" in alltext and "freeze" in alltext.lower()

    d6=texts.get("PAD_Stream_V15SG7D6_Full_Grid_Candidate_Freeze_Provenance_Manifest.py","")
    d4=texts.get("PAD_Stream_V15SG7D4_Controlled_Background_Only_Unsupported_Cell_Completion.py","")
    d5=texts.get("PAD_Stream_V15SG7D5_Independent_Full_Grid_Completion_Validation.py","")
    pkg=texts.get("PAD_Stream_V15_Final_Freeze_Documentation_Packaging.py","")

    exact_d6_chain=all(x in d6 for x in [
        "R1F3 frozen L2","SG7D1 conservative segment-weighted map-back",
        "SG7D5","SG7D4","Frozen full-grid SHA-256 matches validated source"
    ])
    d4_deterministic=all(x in d4 for x in [
        "supported cells","unsupported cells","frozen transport background saturation",
        "NO TRAINING","NO INTERPOLATION"
    ])
    d5_independent=("independent" in d5.lower() and "R1F3 frozen L2" in d5
                    and "SG7D1" in d5 and "SG7D4" in d5)
    freeze_immutable=all(x in d6 for x in [
        '"numerical_field_changed": False',
        '"support_mask_changed": False',
        '"conservative_evidence_changed": False',
        '"SG7E_threshold_changed": False'
    ])
    package_no_inference=("No model inference was performed during final packaging" in pkg)
    package_no_training=("No training was performed during final packaging" in pkg)
    later_prohibited=("250/500/1000-day frozen deployment states are not present" in pkg)

    # Critical L2 question: can the missing certified L2 be regenerated exactly?
    # A frozen L2 *consumer* chain does not itself authorize re-running ML inference.
    # Exact L2 regeneration requires a preserved producer source AND an explicit
    # deterministic/replay authority that does not depend on uncertified runtime reproduction.
    r1_sources=[(n,t) for n,t in texts.items() if "R1F3" in n or "V15-SG7C-R3F5-R1F3" in t]
    r1_source_present=bool(r1_sources)
    r1_blob="\n".join(t for _,t in r1_sources)
    r1_freeze_semantics=("frozen" in r1_blob.lower() and "L2" in r1_blob)
    r1_explicit_regen=bool(re.search(r"(reconstruct|regenerat|replay).{0,180}(exact|determin|authoriz)",r1_blob,re.I|re.S))
    r1_no_model_dependency=not bool(re.search(r"\b(model\.predict|predict\(|load_model|tensorflow|keras)\b",r1_blob,re.I))
    # Formal packaging explicitly says exact historical inference runtime reproduction is not certified.
    runtime_not_cert=("Exact historical inference runtime reproduction is not certified" in pkg)
    l2_regen_authorized=(r1_source_present and r1_freeze_semantics and r1_explicit_regen
                         and r1_no_model_dependency and not runtime_not_cert)

    # SG7D6 regeneration is deterministic only if authoritative L2 bytes are available.
    sg7d6_recipe_authorized=(exact_d6_chain and d4_deterministic and d5_independent
                             and freeze_immutable)
    full_chain_regen_authorized=l2_regen_authorized and sg7d6_recipe_authorized

    edges=[
        dict(order=1,source="R1F3 frozen L2",target="SG7D1 conservative map-back",
             source_evidence=has_r1f3,target_evidence=has_d1),
        dict(order=2,source="SG7D1 conservative map-back",target="SG7D4 controlled completion",
             source_evidence=has_d1,target_evidence=has_d4),
        dict(order=3,source="SG7D4 controlled completion",target="SG7D5 independent validation",
             source_evidence=has_d4,target_evidence=has_d5),
        dict(order=4,source="SG7D5 independent validation",target="SG7D6 frozen full-grid",
             source_evidence=has_d5,target_evidence=has_d6),
    ]
    save_csv(EDGE,edges)

    ev=[
        dict(question="R1F3 producer source present",result=r1_source_present),
        dict(question="R1F3 frozen L2 semantics present",result=r1_freeze_semantics),
        dict(question="R1F3 explicit deterministic regeneration authority",result=r1_explicit_regen),
        dict(question="R1F3 regeneration independent of model inference",result=r1_no_model_dependency),
        dict(question="Formal V15 exact historical runtime reproduction NOT certified",result=runtime_not_cert),
        dict(question="SG7D6 exact source chain preserved",result=exact_d6_chain),
        dict(question="SG7D4 deterministic completion preserved",result=d4_deterministic),
        dict(question="SG7D5 independent validation preserved",result=d5_independent),
        dict(question="SG7D6 immutability assertions preserved",result=freeze_immutable),
        dict(question="L2 regeneration authorized",result=l2_regen_authorized),
        dict(question="SG7D6 recipe authorized given authoritative L2 bytes",result=sg7d6_recipe_authorized),
        dict(question="Full missing L2->SG7D6 regeneration authorized",result=full_chain_regen_authorized),
    ]
    save_csv(AUTH,ev)

    gates=[
        ("R4_formal_authority_resolution_reproduced",True),
        ("R1F3_lineage_source_evidence_present",has_r1f3),
        ("SG7D1_lineage_source_evidence_present",has_d1),
        ("SG7D4_lineage_source_evidence_present",has_d4),
        ("SG7D5_lineage_source_evidence_present",has_d5),
        ("SG7D6_lineage_source_evidence_present",has_d6),
        ("SG7D6_exact_provenance_chain_preserved",exact_d6_chain),
        ("SG7D4_deterministic_completion_preserved",d4_deterministic),
        ("SG7D5_independent_validation_preserved",d5_independent),
        ("SG7D6_immutability_contract_preserved",freeze_immutable),
        ("final_packaging_no_training",package_no_training),
        ("final_packaging_no_inference",package_no_inference),
        ("later_time_deployment_remains_prohibited",later_prohibited),
        ("exact_runtime_reproduction_limitation_reproduced",runtime_not_cert),
        ("missing_L2_exact_regeneration_authorized",l2_regen_authorized),
        ("SG7D6_regeneration_recipe_authorized_if_L2_available",sg7d6_recipe_authorized),
        ("full_missing_L2_to_SG7D6_regeneration_authorized",full_chain_regen_authorized),
        ("no_regeneration_executed",True),
        ("no_numerical_closeness_selection",True),
        ("no_Y_transport_generated",True),
        ("no_frozen_artifact_mutation",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])

    if full_chain_regen_authorized:
        status="V16C_EXACT_FROZEN_L2_SG7D6_REGENERATION_AUTHORITY_CONFIRMED"
        diagnosis="THE_FORMAL_V15_RECORD_PRESERVES_AN_EXPLICIT_DETERMINISTIC_AUTHORIZED_RECIPE_FOR_RECONSTRUCTING_THE_MISSING_CERTIFIED_L2_AND_SG7D6_AUTHORITIES"
        rec="Freeze R5 and proceed to controlled source-authentic regeneration with byte-hash verification against the formal frozen identities."
        nxt="V16C-12R6 — Controlled Source-Authentic V15 L2/SG7D6 Regeneration and Hash Verification"
    elif sg7d6_recipe_authorized and not l2_regen_authorized:
        status="V16C_SG7D6_RECIPE_PRESERVED_BUT_MISSING_CERTIFIED_L2_REGENERATION_NOT_AUTHORIZED"
        diagnosis="THE_GRID_DEPLOYMENT_RECIPE_IS_DETERMINISTIC_FROM_R1F3_L2_BUT_THE_FORMAL_V15_RECORD_DOES_NOT_AUTHORIZE_EXACT_REGENERATION_OF_THE_MISSING_CERTIFIED_L2_BECAUSE_HISTORICAL_INFERENCE_RUNTIME_REPRODUCTION_IS_NOT_CERTIFIED"
        rec=("Do not rerun the PI-RNN and do not substitute an ambiguous frozen100 candidate. "
             "Search/bind the exact certified L2_independent_100 bytes from the frozen V15 package/archive or another preserved copy. "
             "Once exact L2 bytes are recovered, SG7D6 may be deterministically reconstructed and hash-checked.")
        nxt="V16C-12R5A — Frozen V15 Package/Archive Exact L2 Byte-Recovery Audit"
    else:
        status="V16C_FROZEN_SOURCE_RECIPE_REGENERATION_AUTHORITY_INCOMPLETE"
        diagnosis="THE_FORMAL_SOURCE_CHAIN_IS_NOT_SUFFICIENTLY_PRESERVED_TO_AUTHORIZE_CONTROLLED_REGENERATION"
        rec="Do not regenerate. Audit the missing source-recipe component indicated by the failed gates."
        nxt="V16C-12R5R — Source-Recipe Authority Residual Audit"

    save_csv(DEC,[dict(status=status,diagnosis=diagnosis,
        source_count=len(srcs),L2_regeneration_authorized=l2_regen_authorized,
        SG7D6_recipe_authorized_if_L2_available=sg7d6_recipe_authorized,
        full_regeneration_authorized=full_chain_regen_authorized,
        regeneration_executed=False,Y_generation_authorized=False,next_milestone=nxt)])
    savej(CON,dict(milestone="V16C-12R5",status=status,diagnosis=diagnosis,
        formal_L2_sha256=EXPECTED_L2_SHA,formal_SG7D6_sha256=EXPECTED_SG7D6_SHA,
        lineage=edges,L2_regeneration_authorized=l2_regen_authorized,
        SG7D6_recipe_authorized_if_L2_available=sg7d6_recipe_authorized,
        full_regeneration_authorized=full_chain_regen_authorized,
        historical_runtime_reproduction_certified=not runtime_not_cert,
        regeneration_executed=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))
    savej(SUM,dict(milestone="V16C-12R5",status=status,diagnosis=diagnosis,
        L2_regeneration_authorized=l2_regen_authorized,
        SG7D6_recipe_authorized_if_L2_available=sg7d6_recipe_authorized,
        full_regeneration_authorized=full_chain_regen_authorized,
        regeneration_executed=False,Y_transport_generated=False,
        Y_generation_authorized=False,recommendation=rec,next_milestone=nxt))

    print("SOURCE-RECIPE AUTHORITY")
    print("  source files inventoried                     :",len(srcs))
    print("  R1F3 frozen L2 lineage                       :",has_r1f3)
    print("  SG7D1 conservative map-back lineage          :",has_d1)
    print("  SG7D4 deterministic completion               :",d4_deterministic)
    print("  SG7D5 independent validation                 :",d5_independent)
    print("  SG7D6 exact freeze chain                      :",exact_d6_chain)
    print("  exact historical runtime reproduction cert.  :",not runtime_not_cert)
    print("  missing L2 regeneration authorized           :",l2_regen_authorized)
    print("  SG7D6 recipe authorized if L2 recovered      :",sg7d6_recipe_authorized)
    print("  full missing-chain regeneration authorized   :",full_chain_regen_authorized)

    print("\n"+"="*78)
    print("V16C-12R5 FINAL REGENERATION AUTHORITY GATES")
    print("="*78)
    for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-12R5 SOURCE-RECIPE REGENERATION AUTHORITY AUDIT: COMPLETE")
    print("="*78)

if __name__=="__main__":main()
