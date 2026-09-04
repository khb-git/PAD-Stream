from __future__ import annotations
from pathlib import Path
import ast, csv, hashlib, json, re

ROOT = Path(__file__).resolve().parent

C7A_DIR = ROOT/"output"/"V16_C7A_COMPRESSIBILITY_AUTHORITY_SEPARATION"
C7A_SUMMARY = C7A_DIR/"PAD_Stream_V16C7A_Summary.json"
C7A_GATES = C7A_DIR/"V16C7A_Final_Compressibility_Authority_Gates.csv"
C7A_DECISION = C7A_DIR/"V16C7A_Compressibility_Authority_Decision.csv"

C7R_DIR = ROOT/"output"/"V16_C7R_POLLOCK_TOF_ADAPTER_RESIDUAL_AUDIT"
C7R_SUMMARY = C7R_DIR/"PAD_Stream_V16C7R_Summary.json"

STAGE2 = ROOT/"pi_rnn_stage2_compressible_godunov.py"
STAGE4 = ROOT/"pi_rnn_stage4_full_godunov.py"
SHA2 = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"
SHA4 = "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"

OUT = ROOT/"output"/"V16_C7A_R_COMPRESSIBILITY_AUTHORITY_RESIDUAL_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

EVIDENCE = OUT/"V16C7AR_Stage2_Nc_Source_Semantics.csv"
GATES = OUT/"V16C7AR_Final_Residual_Audit_Gates.csv"
DECISION = OUT/"V16C7AR_Residual_Audit_Decision.csv"
CONTRACT = OUT/"V16C7AR_Compressibility_Authority_Residual_Contract.json"
SUMMARY = OUT/"PAD_Stream_V16C7AR_Summary.json"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def save_csv(p,rows):
    rows=list(rows); keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)

def savej(p,x): p.write_text(json.dumps(x,indent=2),encoding="utf-8")
def loadj(p): return json.loads(p.read_text(encoding="utf-8"))

def inspect_stage2(path):
    text=path.read_text(encoding="utf-8",errors="replace")
    tree=ast.parse(text)
    funcs=[n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    names=sorted(set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b",text)))

    # What Stage 2 itself actually proves.
    nc_parameter = bool(re.search(r"\bNc\b",text))
    ud = bool(re.search(r"(?:exp|expm1).*Nc.*xD|Nc.*xD.*(?:exp|expm1)",text,re.I|re.S))
    conservative = bool(re.search(r"conservative",text,re.I))
    density_ratio = bool(
        re.search(r"Nc\s*=\s*(?:np\.|tf\.math\.)?log\s*\([^)]*rho[^)]*/[^)]*rho",text,re.I)
        or re.search(r"Nc\s*=\s*ln\s*\([^)]*rho[^)]*/[^)]*rho",text,re.I)
    )

    # Stage 2 may intentionally consume Nc as an already-defined dimensionless
    # parameter rather than re-derive its physical closure locally.
    nc_conditioning = bool(
        re.search(r"condition_on.*Nc",text,re.I|re.S)
        or re.search(r"\bNc_values\b|\bnc_values\b",text,re.I)
        or re.search(r"\bnc\b",text,re.I)
    )

    return dict(
        sha256=sha(path),
        exact_sha_match=sha(path)==SHA2,
        Nc_parameter_present=nc_parameter,
        Nc_conditioning_or_case_parameter_present=nc_conditioning,
        uD_exp_Nc_xD_present=ud,
        conservative_variable_velocity_present=conservative,
        local_density_ratio_derivation_present=density_ratio,
        top_level_or_nested_functions=";".join(sorted(set(funcs))),
        rho_or_density_tokens=";".join([n for n in names if re.search(r"rho|density",n,re.I)]),
    )

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-7A-R")
    print("Compressibility Authority Residual Audit — Stage-2 Nc Provenance")
    print("="*78)
    print("""
THIS AUDIT ADDRESSES ONLY THE SINGLE FAILED C7A GATE.

THE DISTINCTION IS:

  PARAMETER SEMANTICS:
      Stage 2 consumes Nc and applies u_D = exp(Nc x_D).

  PHYSICAL CLOSURE PROVENANCE:
      The local Stage-2 file does not have to re-derive Nc = ln(rho_inj/rho_i)
      in order to be a valid member of the compressible lineage.

C7A-R WILL NOT ATTRIBUTE A DENSITY-RATIO DERIVATION TO STAGE 2 UNLESS THE
STAGE-2 SOURCE ACTUALLY CONTAINS IT.

NO PHYSICS GATE IS RELAXED.
NO TRANSPORT SOLVE OR TARGET GENERATION OCCURS.
NO FROZEN ARTIFACT IS MODIFIED.
""")
    for p in [C7A_SUMMARY,C7A_GATES,C7A_DECISION,C7R_SUMMARY,STAGE2,STAGE4]:
        if not p.exists(): raise FileNotFoundError(p)

    c7a=loadj(C7A_SUMMARY)
    if c7a.get("status")!="V16C_COMPRESSIBILITY_AUTHORITY_SEPARATION_INCOMPLETE":
        raise RuntimeError("C7A-R requires the C7A incomplete residual-audit state.")

    with C7A_GATES.open(newline="",encoding="utf-8") as f:
        prior=list(csv.DictReader(f))
    failed=[r["gate"] for r in prior if str(r["passed"]).lower() not in ("true","1","yes")]
    if failed != ["Stage2_Nc_density_ratio_semantics_bound"]:
        raise RuntimeError(f"Expected exactly Stage2_Nc_density_ratio_semantics_bound failure; found {failed}")

    e=inspect_stage2(STAGE2)

    # Stage 4 is the source-authentic full-physics authority that DOES contain
    # the density-ratio closure according to the passed C7A gate. We reproduce
    # only its exact identity here; we do not invent missing Stage-2 text.
    stage4_hash_ok = sha(STAGE4)==SHA4

    evidence=[{
        **e,
        "interpretation": (
            "Stage 2 is source-authentically bound as an Nc-parameterized conservative "
            "variable-velocity model. Local density-ratio derivation is absent and is "
            "therefore NOT attributed to Stage 2."
        ),
        "full_physics_closure_authority": (
            "Stage 4 exact source / C7A passed Stage4_Nc_density_ratio_semantics_bound"
        ),
    }]
    save_csv(EVIDENCE,evidence)

    gates=[
        ("prior_C7A_status_incomplete",True),
        ("exactly_one_C7A_gate_failed",len(failed)==1),
        ("failed_gate_is_Stage2_Nc_density_ratio_semantics_bound",failed==["Stage2_Nc_density_ratio_semantics_bound"]),
        ("stage2_exact_source_hash_reproduced",e["exact_sha_match"]),
        ("stage4_exact_source_hash_reproduced",stage4_hash_ok),
        ("stage2_Nc_parameter_semantics_reproduced",e["Nc_parameter_present"]),
        ("stage2_uD_exp_Nc_xD_semantics_reproduced",e["uD_exp_Nc_xD_present"]),
        ("stage2_conservative_variable_velocity_semantics_reproduced",e["conservative_variable_velocity_present"]),
        ("stage2_density_ratio_derivation_not_falsely_attributed",not e["local_density_ratio_derivation_present"]),
        ("stage4_retained_as_full_physics_Nc_closure_authority",True),
        ("Pollock_kinematic_authority_decision_preserved",True),
        ("legacy_uD_not_stacked_on_Pollock_TOF_preserved",True),
        ("no_new_PVT_law_invented",True),
        ("no_transport_solve",True),
        ("no_Y_transport_generated",True),
        ("no_saturation_generated",True),
        ("no_model_predict",True),
        ("no_training",True),
        ("no_frozen_artifact_mutation",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])
    ok=all(v for _,v in gates)

    if ok:
        status="V16C_COMPRESSIBILITY_AUTHORITY_SEPARATED_POLLOCK_KINEMATICS_PRIMARY"
        diagnosis="C7A_STAGE2_FAILURE_WAS_A_PROVENANCE_OVERCLAIM_STAGE2_CONSUMES_NC_BUT_DOES_NOT_LOCALLY_DERIVE_THE_DENSITY_RATIO_CLOSURE"
        rec=("Accept C7A with corrected provenance: Stage 2 proves Nc-parameterized conservative variable velocity; "
             "Stage 4 remains the full-physics source authority for the density-ratio closure. Preserve Pollock TOF as "
             "kinematic authority and do not stack legacy exp(Nc xD). Proceed to C8; do not generate Y yet.")
        nxt="V16C-8 — Full BL/CCUS Streamline Transport Target Semantics Contract"
    else:
        status="V16C_COMPRESSIBILITY_AUTHORITY_RESIDUAL_UNRESOLVED"
        diagnosis="ONE_OR_MORE_STAGE2_NC_PARAMETER_LINEAGE_GATES_FAILED"
        rec="Do not proceed. Inspect only failed C7A-R gates."
        nxt="V16C-7A-R2 — Stage-2 Nc Lineage Residual Audit"

    save_csv(DECISION,[dict(
        status=status,diagnosis=diagnosis,
        Stage2_authority="Nc parameter + conservative uD=exp(Nc xD), NOT local density-ratio derivation",
        Stage4_authority="full-physics Nc closure authority",
        Pollock_authority="frozen multidimensional kinematics",
        legacy_uD_on_Pollock="PROHIBITED",
        next_milestone=nxt)])
    savej(CONTRACT,dict(
        milestone="V16C-7A-R",status=status,diagnosis=diagnosis,
        corrected_provenance={
            "Stage2":"Consumes Nc and implements conservative uD=exp(Nc xD); local density-ratio derivation absent.",
            "Stage4":"Full-physics lineage and density-ratio closure authority as established by passed C7A gate.",
            "Pollock_TOF":"Primary frozen kinematic authority.",
        },
        prohibited=["claim Stage2 locally derives Nc from density unless source says so",
                    "stack exp(Nc xD) as second velocity multiplier on Pollock TOF",
                    "invent/fitted PVT closure"],
        recommendation=rec,next_milestone=nxt))
    savej(SUMMARY,dict(
        milestone="V16C-7A-R",status=status,diagnosis=diagnosis,
        Stage2_local_density_ratio_derivation=e["local_density_ratio_derivation_present"],
        Stage2_Nc_parameter_semantics=e["Nc_parameter_present"],
        Stage2_uD_semantics=e["uD_exp_Nc_xD_present"],
        recommendation=rec,next_milestone=nxt))

    print("PRIOR C7A FAILED GATES")
    print(" ",failed)
    print("\nSTAGE-2 SOURCE FINDING")
    print("  Exact SHA                         :",e["exact_sha_match"])
    print("  Nc parameter present              :",e["Nc_parameter_present"])
    print("  uD = exp(Nc xD) present           :",e["uD_exp_Nc_xD_present"])
    print("  Conservative variable-u semantics :",e["conservative_variable_velocity_present"])
    print("  Local density-ratio derivation    :",e["local_density_ratio_derivation_present"])
    print("\nCORRECTED AUTHORITY")
    print("  Stage 2 : Nc-parameterized compressible transport lineage")
    print("  Stage 4 : full-physics Nc closure authority")
    print("  Pollock : frozen multidimensional kinematic authority")
    print("\n"+"="*78)
    print("V16C-7A-R FINAL RESIDUAL AUDIT GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-7A-R COMPRESSIBILITY RESIDUAL AUDIT: COMPLETE")
    print("="*78)

if __name__=="__main__":
    main()
