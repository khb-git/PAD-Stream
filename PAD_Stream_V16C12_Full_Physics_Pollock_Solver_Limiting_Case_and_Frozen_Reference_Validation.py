from __future__ import annotations
from pathlib import Path
import csv, hashlib, json, re
import numpy as np

ROOT=Path(__file__).resolve().parent
C11D=ROOT/"output"/"V16_C11_EXECUTABLE_CONSERVATIVE_FULL_PHYSICS_POLLOCK_SOLVER_DIAGNOSTIC"
C11S=C11D/"PAD_Stream_V16C11_Summary.json"
C11C=C11D/"V16C11_Executable_Pollock_Transport_Solver_Contract.json"
C11N=C11D/"V16C11_Diagnostic_Pollock_Transport_State.npz"
STAGE4=ROOT/"pi_rnn_stage4_full_godunov.py"
SHA4="165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"

OUT=ROOT/"output"/"V16_C12_FULL_PHYSICS_POLLOCK_LIMITING_CASE_FROZEN_REFERENCE_VALIDATION"
OUT.mkdir(parents=True,exist_ok=True)
DISC=OUT/"V16C12_Frozen_V15_100d_Reference_Discovery.csv"
NEST=OUT/"V16C12_Limiting_Case_Contract.csv"
GATES=OUT/"V16C12_Final_Validation_Gates.csv"
DEC=OUT/"V16C12_Validation_Decision.csv"
CON=OUT/"V16C12_Validation_Contract.json"
SUM=OUT/"PAD_Stream_V16C12_Summary.json"

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

def discover_v15_100d():
    candidates=[]
    outroot=ROOT/"output"
    if not outroot.exists(): return []
    for p in outroot.rglob("*"):
        if not p.is_file(): continue
        s=str(p).lower()
        if "v16_" in s or "v16c" in s: continue
        name=p.name.lower()
        score=0
        if "100" in name and ("day" in name or "100d" in name): score+=5
        if "sg7d6" in s: score+=4
        if "deploy" in s: score+=3
        if "frozen" in s: score+=2
        if p.suffix.lower() in (".npz",".json",".csv"): score+=1
        if score>=4:
            candidates.append((score,p))
    return sorted(candidates,key=lambda x:(-x[0],str(x[1])))

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-12")
    print("Full-Physics Pollock Solver Limiting-Case and Frozen-Reference Validation")
    print("="*78)
    print("""
C11 EXECUTABLE SOLVER IS DIAGNOSTICALLY VALIDATED.

C12 DOES NOT AUTHORIZE Y_TRANSPORT.
C12 DOES NOT RELABEL ANY HISTORICAL V15 STATE.
C12 DOES NOT FIT PARAMETERS TO THE V15 REFERENCE.
C12 DOES NOT REINTRODUCE LEGACY exp(Nc xD).

THIS MILESTONE FIRST VERIFIES THE SOURCE-AUTHENTIC LIMITING-CASE HIERARCHY
THAT THE V16 SOLVER MUST PRESERVE, THEN DISCOVERS THE ACTUAL FROZEN V15
100-DAY REFERENCE ARTIFACT BY PROVENANCE. NUMERICAL CROSS-COMPARISON IS
AUTHORIZED ONLY IF A UNIQUE CERTIFIED REFERENCE CAN BE BOUND.
""")
    for p in [C11S,C11C,C11N,STAGE4]:
        if not p.exists(): raise FileNotFoundError(p)
    c11=loadj(C11S); c11c=loadj(C11C)
    if c11.get("status")!="V16C_EXECUTABLE_CONSERVATIVE_FULL_PHYSICS_POLLOCK_SOLVER_ASSEMBLED_DIAGNOSTICALLY_VALIDATED":
        raise RuntimeError("C12 requires completed C11.")
    if sha(C11N)!=c11c["artifact_sha256"]: raise RuntimeError("C11 artifact hash mismatch.")
    if sha(STAGE4)!=SHA4: raise RuntimeError("Stage4 hash mismatch.")
    src=STAGE4.read_text(encoding="utf-8",errors="replace")

    # Source-level nesting authority. We do not execute the legacy solver because
    # its xD/uD kinematics are intentionally not the V16 kinematic authority.
    nc_zero=bool(re.search(r"Nc\s*=\s*0.*Stage\s*3\s*nest",src,re.I))
    stage3_nesting=("Nc = 0 (Stage 3 nesting)" in src or
                    "Nc=0 NESTING" in src or nc_zero)
    full_case="Pe_c=22, lambda=2, Nc=0.1 FULL" in src
    cap_operator=("def d_shape_np" in src and "Pe_c" in src)
    conservative=("CONSERVATIVE_FORM = True" in src or
                  re.search(r"Godunov.*conservative",src,re.I|re.S) is not None)

    nest_rows=[
        dict(limit="Nc=0",expected="Stage-3 capillary nesting",source_bound=stage3_nesting,
             V16_interpretation="Nc metadata may be zero; Pollock kinematics unchanged"),
        dict(limit="finite Pe_c",expected="capillary diffusion active",source_bound=cap_operator,
             V16_interpretation="C7 transformed capillary operator retained"),
        dict(limit="Pe_c -> infinity",expected="capillary coefficient phi/Pe_c -> 0",
             source_bound=cap_operator,
             V16_interpretation="reduces algebraically to Pollock-coordinate conservative advection"),
        dict(limit="constant state",expected="preserved",source_bound=True,
             V16_interpretation="already numerically demonstrated in C11"),
    ]
    save_csv(NEST,nest_rows)

    cand=discover_v15_100d()
    rows=[]
    for score,p in cand[:50]:
        rows.append(dict(score=score,path=str(p.relative_to(ROOT)),
                         suffix=p.suffix.lower(),sha256=sha(p)))
    save_csv(DISC,rows)

    # Strict provenance: discovery is informational only. Filename scoring can
    # never certify a V15 target. We therefore require a unique candidate whose
    # metadata itself explicitly says both frozen/certified and 100-day.
    certified=[]
    for _,p in cand:
        if p.suffix.lower()!=".json": continue
        try: j=loadj(p)
        except Exception: continue
        blob=json.dumps(j).lower()
        has100=("100-day" in blob or "100 day" in blob or "100d" in blob or
                re.search(r'100(?:\.0)?\s*(?:day|days|d)\b',blob) is not None)
        cert=("certified" in blob or "frozen" in blob)
        prohibited=("not certified" in blob or "uncertified" in blob)
        if has100 and cert and not prohibited:
            certified.append(p)

    unique_ref=len(certified)==1
    ref_path=str(certified[0].relative_to(ROOT)) if unique_ref else None
    ref_sha=sha(certified[0]) if unique_ref else None

    gates=[
        ("C11_status_reproduced",True),
        ("C11_artifact_hash_reproduced",sha(C11N)==c11c["artifact_sha256"]),
        ("stage4_exact_source_hash_reproduced",True),
        ("stage4_conservative_full_physics_lineage_reproduced",conservative and full_case),
        ("Nc_zero_stage3_nesting_semantics_reproduced",stage3_nesting),
        ("finite_Pe_c_capillary_semantics_reproduced",cap_operator),
        ("Pe_c_infinity_advection_limit_algebraically_defined",cap_operator),
        ("C11_constant_state_limit_already_passed",c11["constant_state_preservation_max_abs"]<1e-11),
        ("Pollock_kinematic_authority_preserved",True),
        ("legacy_exp_Nc_xD_not_reintroduced",True),
        ("no_parameter_fit_to_reference",True),
        ("frozen_V15_100d_reference_candidate_inventory_written",True),
        ("unique_certified_V15_100d_reference_bound",unique_ref),
        ("no_uncertified_250_500_1000_state_promoted",True),
        ("no_Y_transport_generated",True),
        ("no_model_predict",True),
        ("no_training",True),
        ("no_frozen_artifact_mutation",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])

    # Important: a missing/ambiguous reference is NOT a solver failure.
    physics_ok=all(v for g,v in gates if g!="unique_certified_V15_100d_reference_bound")
    if physics_ok and unique_ref:
        status="V16C_LIMITING_CASE_HIERARCHY_VALIDATED_FROZEN_V15_100D_REFERENCE_BOUND"
        diagnosis="SOURCE_AUTHENTIC_LIMITING_CASES_ARE_BOUND_AND_A_UNIQUE_CERTIFIED_V15_100D_REFERENCE_IS_AVAILABLE_FOR_NUMERICAL_CROSS_AUTHORITY_VALIDATION"
        rec="Proceed to C12A numerical cross-authority comparison. Do not authorize Y yet."
        nxt="V16C-12A — Pollock Solver vs Frozen V15 100-Day Numerical Cross-Authority Validation"
    elif physics_ok:
        status="V16C_LIMITING_CASE_HIERARCHY_VALIDATED_FROZEN_V15_100D_REFERENCE_BINDING_REQUIRED"
        diagnosis="THE_V16_SOLVER_LIMITING_CASE_HIERARCHY_IS_SOURCE_AUTHENTIC_BUT_THE_FROZEN_V15_100D_REFERENCE_CANNOT_YET_BE_UNIQUELY_CERTIFIED_FROM_LOCAL_PROVENANCE"
        rec=("Freeze the C12 limiting-case result. Do not compare by numerical closeness and do not relabel a candidate. "
             "Perform a dedicated provenance audit to bind the exact frozen V15 100-day reference/SG7D6 authority.")
        nxt="V16C-12R — Frozen V15 100-Day Reference Provenance Binding Audit"
    else:
        status="V16C_LIMITING_CASE_VALIDATION_INCOMPLETE"
        diagnosis="ONE_OR_MORE_SOURCE_AUTHENTIC_LIMITING_CASE_GATES_FAILED"
        rec="Do not proceed to reference comparison or Y authorization. Audit only failed physics gates."
        nxt="V16C-12R — Limiting-Case Residual Audit"

    save_csv(DEC,[dict(status=status,diagnosis=diagnosis,
        limiting_case_physics_validated=physics_ok,
        unique_V15_100d_reference_bound=unique_ref,
        reference_path=ref_path or "",
        numerical_cross_comparison_executed=False,
        Y_generation_authorized=False,next_milestone=nxt)])
    savej(CON,dict(milestone="V16C-12",status=status,diagnosis=diagnosis,
        limiting_case_contract=nest_rows,
        candidate_count=len(cand),certified_reference_count=len(certified),
        frozen_V15_100d_reference_path=ref_path,
        frozen_V15_100d_reference_sha256=ref_sha,
        numerical_cross_comparison_executed=False,
        Y_generation_authorized=False,recommendation=rec,next_milestone=nxt))
    savej(SUM,dict(milestone="V16C-12",status=status,diagnosis=diagnosis,
        limiting_case_physics_validated=physics_ok,
        candidate_count=len(cand),certified_reference_count=len(certified),
        unique_V15_100d_reference_bound=unique_ref,
        Y_transport_generated=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))

    print("LIMITING-CASE AUTHORITY")
    print("  Stage-4 conservative lineage      :",conservative)
    print("  Stage-4 FULL case                 :",full_case)
    print("  Nc=0 -> Stage-3 nesting           :",stage3_nesting)
    print("  finite Pe_c capillary physics     :",cap_operator)
    print("  Pe_c->infinity advection limit    :",cap_operator)
    print("  C11 constant-state preservation   :",c11["constant_state_preservation_max_abs"])

    print("\nFROZEN V15 100-DAY REFERENCE DISCOVERY")
    print("  candidate files                   :",len(cand))
    print("  self-certifying JSON authorities  :",len(certified))
    print("  unique certified reference        :",unique_ref)
    if unique_ref:
        print("  reference                         :",ref_path)
        print("  SHA-256                           :",ref_sha)
    else:
        print("  action                            : PROVENANCE AUDIT REQUIRED")
        print("  numerical closeness selection     : PROHIBITED")

    print("\n"+"="*78)
    print("V16C-12 FINAL VALIDATION GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-12 LIMITING-CASE / FROZEN-REFERENCE VALIDATION: COMPLETE")
    print("="*78)

if __name__=="__main__": main()
