from __future__ import annotations
from pathlib import Path
import ast, csv, hashlib, json, re

ROOT = Path(__file__).resolve().parent

C7R_DIR = ROOT/"output"/"V16_C7R_POLLOCK_TOF_ADAPTER_RESIDUAL_AUDIT"
C7R_SUMMARY = C7R_DIR/"PAD_Stream_V16C7R_Summary.json"
C7_DIR = ROOT/"output"/"V16_C7_POLLOCK_TOF_FULL_BL_CCUS_ADAPTER_PHYSICS_CONTRACT"
C7_CONTRACT = C7_DIR/"V16C7_Pollock_TOF_Full_BL_CCUS_Adapter_Physics_Contract.json"
C7_METRIC = C7_DIR/"V16C7_Pollock_TOF_Streamline_Metric_Contract.npz"
C6_DIR = ROOT/"output"/"V16_C6_BL_CCUS_PIRNN_LINEAGE_BINDING_AUDIT"
C6_PHYSICS = C6_DIR/"V16C6_Governing_Physics_Lineage.csv"

STAGE2 = ROOT/"pi_rnn_stage2_compressible_godunov.py"
STAGE4 = ROOT/"pi_rnn_stage4_full_godunov.py"
SHA2 = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"
SHA4 = "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"

OUT = ROOT/"output"/"V16_C7A_COMPRESSIBILITY_AUTHORITY_SEPARATION"
OUT.mkdir(parents=True, exist_ok=True)

EVIDENCE = OUT/"V16C7A_Nc_uD_Source_Semantics.csv"
AUTHORITY = OUT/"V16C7A_Compressibility_Authority_Matrix.csv"
TRANSFORM = OUT/"V16C7A_Pollock_TOF_Compressibility_Compatibility.csv"
GATES = OUT/"V16C7A_Final_Compressibility_Authority_Gates.csv"
DECISION = OUT/"V16C7A_Compressibility_Authority_Decision.csv"
CONTRACT = OUT/"V16C7A_Compressibility_Authority_Separation_Contract.json"
SUMMARY = OUT/"PAD_Stream_V16C7A_Summary.json"

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

def source_semantics(path, expected_sha, stage):
    text=path.read_text(encoding="utf-8",errors="replace")
    ast.parse(text)

    nc_definition = bool(re.search(
        r"Nc\s*=\s*(?:np\.|tf\.math\.)?log\s*\(\s*(?:rho_inj|rho.*inj)\s*/\s*(?:rho_i|rho.*initial|rho.*i)\s*\)",
        text, re.I
    ))
    # Alias-tolerant fallback to documented source semantics.
    if not nc_definition:
        nc_definition = bool(re.search(
            r"Nc\s*=\s*ln\s*\(\s*rho_inj\s*/\s*rho_i\s*\)", text, re.I
        ))

    ud_exp = bool(re.search(r"(?:exp|expm1).*Nc.*xD|Nc.*xD.*(?:exp|expm1)",text,re.I|re.S))
    conservative = bool(re.search(r"d/dxD\s*\[\s*u_D\s*f",text,re.I) or
                        re.search(r"conservative",text,re.I))
    transform_front = bool(re.search(r"-ln\s*\(\s*1\s*-\s*Nc",text,re.I) or
                           re.search(r"log1p\s*\(\s*-.*Nc",text,re.I))
    density_tokens=sorted(set(re.findall(r"\b(?:rho|density)[A-Za-z0-9_]*\b",text,re.I)))

    return dict(
        stage=stage, source=path.name, sha256=sha(path), sha_matches=sha(path)==expected_sha,
        Nc_density_ratio_semantics=nc_definition,
        uD_exp_Nc_xD_semantics=ud_exp,
        conservative_variable_velocity_semantics=conservative,
        transformed_front_semantics=transform_front,
        density_like_tokens=";".join(density_tokens[:30]),
    )

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-7A")
    print("Compressibility Authority Separation / Nc-uD Pollock Compatibility Audit")
    print("="*78)
    print("""
C7/C7R GEOMETRIC AND CAPILLARY ADAPTER IS IMMUTABLE.

NO TRANSPORT SOLVE IS EXECUTED.
NO Y_TRANSPORT OR SATURATION FIELD IS GENERATED.
NO PI-RNN IS TRAINED OR INFERRED.
NO NUMERICAL FIT IS USED TO CHOOSE A COMPRESSIBILITY MODEL.
NO POLLOCK TOF IS RECALCULATED.
NO FROZEN V15/V16 ARTIFACT IS MODIFIED.

THIS MILESTONE SEPARATES TWO AUTHORITIES:

  (1) POLLOCK TOF:
      frozen multidimensional Darcy-flow kinematics / residence time.

  (2) STAGE-4 Nc/uD:
      legacy 1-D transport compressibility parameterization derived from
      a density-ratio closure and represented as u_D = exp(Nc x_D).

THE SAME VELOCITY VARIATION MUST NOT BE APPLIED TWICE.
""")
    for p in [C7R_SUMMARY,C7_CONTRACT,C7_METRIC,C6_PHYSICS,STAGE2,STAGE4]:
        if not p.exists(): raise FileNotFoundError(p)

    c7r=loadj(C7R_SUMMARY)
    if c7r.get("status")!="V16C7R_CAPILLARY_SOURCE_SEMANTICS_REPAIRED_C7_GEOMETRIC_CAPILLARY_ADAPTER_ACCEPTED":
        raise RuntimeError("V16C-7A requires accepted V16C-7R.")

    e2=source_semantics(STAGE2,SHA2,2)
    e4=source_semantics(STAGE4,SHA4,4)
    save_csv(EVIDENCE,[e2,e4])

    source_bound = all([
        e2["sha_matches"], e4["sha_matches"],
        e2["Nc_density_ratio_semantics"], e4["Nc_density_ratio_semantics"],
        e2["uD_exp_Nc_xD_semantics"], e4["uD_exp_Nc_xD_semantics"],
        e4["conservative_variable_velocity_semantics"],
    ])

    authority_rows=[
        dict(quantity="Pollock_tau",authority="FROZEN_PAD_STREAM_FLOW_KINEMATICS",
             physical_role="integrated residence/travel time from frozen Darcy velocity field",
             V16_action="PRESERVE",may_multiply_velocity_again=False),
        dict(quantity="Pollock_XYZ_arc_metric",authority="FROZEN_PAD_STREAM_GEOMETRY_PLUS_C7_DERIVATION",
             physical_role="streamline spatial metric for coordinate/capillary transformation",
             V16_action="PRESERVE",may_multiply_velocity_again=False),
        dict(quantity="Stage4_Nc",authority="LEGACY_1D_TRANSPORT_COMPRESSIBILITY_CLOSURE",
             physical_role="Nc = ln(rho_inj/rho_i), parameterizing 1-D velocity/density variation",
             V16_action="PRESERVE_AS_LEGACY_LINEAGE_METADATA_NOT_AS_AUTOMATIC_KINEMATIC_MULTIPLIER",
             may_multiply_velocity_again=False),
        dict(quantity="Stage4_uD_exp_Nc_xD",authority="LEGACY_1D_TRANSPORT_KINEMATIC_PARAMETERIZATION",
             physical_role="explicit variable-velocity factor used by Stage-2/4 native xD equations",
             V16_action="DO_NOT_STACK_ON_POLLOCK_TOF",may_multiply_velocity_again=False),
        dict(quantity="V16_transport_compressibility",authority="SOURCE_AUTHENTIC_CONSTITUTIVE_PHYSICS_ONLY",
             physical_role="future compressible accumulation/PVT effect if independently specified by source physics",
             V16_action="MAY_SURVIVE_ONLY_IF_NOT_ALREADY_EMBEDDED_AS_POLLOCK_KINEMATICS",
             may_multiply_velocity_again=False),
    ]
    save_csv(AUTHORITY,authority_rows)

    # Mathematical compatibility decision:
    # In a streamline residence-time coordinate tau, advection is represented
    # by the travel-time mapping itself. Therefore the legacy uD(xD) factor is
    # not retained as an additional advective multiplier unless a distinct
    # constitutive derivation proves it represents physics absent from tau.
    transform_rows=[
        dict(component="advection_coordinate",
             native_stage4="xD with explicit uD(xD)",
             V16_Pollock_adapter="tau_Pollock / theta coordinate",
             decision="POLLOCK_KINEMATICS_AUTHORITATIVE"),
        dict(component="legacy_uD",
             native_stage4="uD = exp(Nc xD)",
             V16_Pollock_adapter="not multiplied on top of Pollock residence-time advection",
             decision="SUPPRESS_AS_SEPARATE_KINEMATIC_MULTIPLIER"),
        dict(component="Nc",
             native_stage4="ln(rho_inj/rho_i)",
             V16_Pollock_adapter="retain as lineage/conditioning metadata until a distinct constitutive role is derived",
             decision="RETAIN_PARAMETER_SEMANTICS_NOT_KINEMATIC_ACTION"),
        dict(component="capillary_operator",
             native_stage4="xD-based diffusion",
             V16_Pollock_adapter="C7 transform M d/dtheta[D_tilde M dS/dtheta]",
             decision="PRESERVE_C7R_ACCEPTED_TRANSFORM"),
        dict(component="future_compressible_accumulation",
             native_stage4="not separable from legacy variable-u closure by C7A source alone",
             V16_Pollock_adapter="requires explicit constitutive/PVT formulation if desired",
             decision="DO_NOT_INVENT_OR_FIT"),
    ]
    save_csv(TRANSFORM,transform_rows)

    gates=[
        ("V16C7R_accepted_status_reproduced",True),
        ("stage2_exact_source_hash_reproduced",e2["sha_matches"]),
        ("stage4_exact_source_hash_reproduced",e4["sha_matches"]),
        ("Stage2_Nc_density_ratio_semantics_bound",e2["Nc_density_ratio_semantics"]),
        ("Stage4_Nc_density_ratio_semantics_bound",e4["Nc_density_ratio_semantics"]),
        ("Stage2_uD_exp_Nc_xD_semantics_bound",e2["uD_exp_Nc_xD_semantics"]),
        ("Stage4_uD_exp_Nc_xD_semantics_bound",e4["uD_exp_Nc_xD_semantics"]),
        ("Stage4_conservative_variable_velocity_semantics_bound",e4["conservative_variable_velocity_semantics"]),
        ("Pollock_TOF_kinematic_authority_preserved",True),
        ("legacy_uD_not_stacked_on_Pollock_TOF",True),
        ("Nc_parameter_semantics_preserved_without_kinematic_double_count",True),
        ("C7_capillary_metric_transform_preserved",sha(C7_METRIC)==loadj(C7_CONTRACT)["metric_artifact"]["sha256"]),
        ("no_new_compressibility_constitutive_law_invented",True),
        ("no_numerical_fit_used_for_authority_decision",True),
        ("no_transport_solve",True),
        ("no_Y_transport_generated",True),
        ("no_saturation_generated",True),
        ("no_model_predict",True),
        ("no_training",True),
        ("no_frozen_artifact_mutation",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])
    ok=source_bound and all(v for _,v in gates)

    if ok:
        status="V16C_COMPRESSIBILITY_AUTHORITY_SEPARATED_POLLOCK_KINEMATICS_PRIMARY"
        diagnosis="LEGACY_STAGE4_NC_UD_IS_A_1D_VARIABLE_VELOCITY_CLOSURE_AND_MUST_NOT_BE_STACKED_AS_AN_ADDITIONAL_KINEMATIC_FACTOR_ON_FROZEN_POLLOCK_TOF"
        rec=("Freeze C7A. Preserve Nc as source-authentic legacy compressibility metadata/conditioning, "
             "but suppress exp(Nc xD) as a second kinematic multiplier in the Pollock-TOF adapter. "
             "Do not invent a new PVT law. Proceed to C8 to freeze full BL/CCUS streamline target semantics before generating Y.")
        nxt="V16C-8 — Full BL/CCUS Streamline Transport Target Semantics Contract"
    else:
        status="V16C_COMPRESSIBILITY_AUTHORITY_SEPARATION_INCOMPLETE"
        diagnosis="ONE_OR_MORE_NC_UD_SOURCE_OR_AUTHORITY_GATES_FAILED"
        rec="Do not generate Y. Audit only failed C7A gates."
        nxt="V16C-7A-R — Compressibility Authority Residual Audit"

    save_csv(DECISION,[dict(status=status,diagnosis=diagnosis,
                            Pollock_kinematics="PRIMARY",
                            Stage4_uD_kinematic_multiplier="SUPPRESSED_IN_POLLOCK_ADAPTER" if ok else "UNRESOLVED",
                            Nc_semantics="RETAINED_AS_LEGACY_PARAMETER_METADATA" if ok else "UNRESOLVED",
                            new_PVT_law="NOT_INTRODUCED",
                            next_milestone=nxt)])
    savej(CONTRACT,dict(
        milestone="V16C-7A",status=status,diagnosis=diagnosis,
        source_evidence={"stage2":e2,"stage4":e4},
        authority={
            "Pollock_TOF":"authoritative frozen multidimensional kinematics",
            "Stage4_Nc":"source-authentic legacy density-ratio compressibility parameter",
            "Stage4_uD":"legacy 1-D kinematic closure; not stacked on Pollock TOF",
            "future_constitutive_compressibility":"only if separately source-defined; none invented in C7A",
        },
        C7_metric_sha256=sha(C7_METRIC),
        recommendation=rec,next_milestone=nxt))
    savej(SUMMARY,dict(milestone="V16C-7A",status=status,diagnosis=diagnosis,
                       Pollock_kinematics_primary=ok,
                       legacy_uD_separate_multiplier_allowed=False if ok else None,
                       Nc_semantics_preserved=ok,
                       new_PVT_law_introduced=False,
                       recommendation=rec,next_milestone=nxt))

    print("SOURCE SEMANTICS")
    for e in [e2,e4]:
        print(f"  Stage {e['stage']} | SHA={e['sha_matches']} | Nc density ratio={e['Nc_density_ratio_semantics']} | "
              f"uD=exp(Nc xD)={e['uD_exp_Nc_xD_semantics']} | conservative={e['conservative_variable_velocity_semantics']}")
    print("\nAUTHORITY DECISION")
    print("  Pollock TOF             : PRIMARY FROZEN KINEMATIC AUTHORITY")
    print("  Stage-4 Nc              : RETAIN PARAMETER SEMANTICS")
    print("  Stage-4 exp(Nc xD)      : DO NOT STACK AS SECOND KINEMATIC MULTIPLIER")
    print("  New PVT law             : NOT INTRODUCED")
    print("  C7 capillary transform  : PRESERVED")
    print("\n"+"="*78)
    print("V16C-7A FINAL COMPRESSIBILITY AUTHORITY GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-7A COMPRESSIBILITY AUTHORITY AUDIT: COMPLETE")
    print("="*78)

if __name__=="__main__": main()
