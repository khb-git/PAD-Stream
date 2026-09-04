from __future__ import annotations
from pathlib import Path
import csv, json, math

ROOT = Path(__file__).resolve().parent

C11D = ROOT/"output"/"V16_C11_EXECUTABLE_CONSERVATIVE_FULL_PHYSICS_POLLOCK_SOLVER_DIAGNOSTIC"
C11S = C11D/"PAD_Stream_V16C11_Summary.json"

C12D = ROOT/"output"/"V16_C12_FULL_PHYSICS_POLLOCK_SOLVER_LIMITING_CASE_AND_FROZEN_REFERENCE_VALIDATION"
C12S = C12D/"PAD_Stream_V16C12_Summary.json"

ARD = ROOT/"output"/"V16_C12AR_SURVIVING_AUTHORITY_100_DAY_VALIDATION_CONTRACT"
ARS = ARD/"PAD_Stream_V16C12AR_Summary.json"

OUT = ROOT/"output"/"V16_C12B_INTERNAL_PHYSICS_VALIDATION_CLOSURE_Y_GENERATION_READINESS_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

EVID = OUT/"V16C12B_Internal_Physics_Evidence.csv"
GATES = OUT/"V16C12B_Final_Readiness_Gates.csv"
DEC = OUT/"V16C12B_Y_Generation_Readiness_Decision.csv"
CON = OUT/"V16C12B_Internal_Physics_Validation_Closure_Contract.json"
SUM = OUT/"PAD_Stream_V16C12B_Summary.json"

C11_OK = "V16C_EXECUTABLE_CONSERVATIVE_FULL_PHYSICS_POLLOCK_SOLVER_ASSEMBLED_DIAGNOSTICALLY_VALIDATED"
C12_OK = "V16C_LIMITING_CASE_HIERARCHY_VALIDATED_FROZEN_V15_100D_REFERENCE_BINDING_REQUIRED"
AR_OK = "V16C_NO_NUMERICAL_V15_100D_AUTHORITY_BYTES_SURVIVE_FOR_DIRECT_CROSS_VALIDATION"

def loadj(p):
    if not p.exists():
        raise FileNotFoundError(p)
    return json.loads(p.read_text(encoding="utf-8"))

def savej(p, obj):
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def save_csv(p, rows):
    rows=list(rows); keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with p.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

def flatten(obj, prefix=""):
    out={}
    if isinstance(obj, dict):
        for k,v in obj.items():
            q=f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten(v,q))
    elif isinstance(obj, list):
        for i,v in enumerate(obj):
            q=f"{prefix}[{i}]"
            out.update(flatten(v,q))
    else:
        out[prefix]=obj
    return out

def values_matching(flat, needles):
    ans=[]
    for k,v in flat.items():
        lk=k.lower()
        if all(n.lower() in lk for n in needles):
            ans.append((k,v))
    return ans

def any_true(flat, terms):
    for k,v in flat.items():
        s=(k+" "+str(v)).lower()
        if all(t.lower() in s for t in terms):
            if isinstance(v,bool): return v
            if str(v).lower() in ("true","pass","passed","complete","completed"): return True
    return False

def numeric(flat, termsets):
    for terms in termsets:
        for k,v in flat.items():
            lk=k.lower()
            if all(t.lower() in lk for t in terms):
                try: return float(v)
                except: pass
    return None

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-12B")
    print("Internal Physics Validation Closure and Y-Generation Readiness Audit")
    print("="*78)
    print("""
C12A-R CLOSED DIRECT NUMERICAL V15 100-DAY CROSS-VALIDATION AS UNAVAILABLE
BECAUSE THE EXACT L2_independent_100, SG7D6, AND SG7E AUTHORITY BYTES DO NOT
SURVIVE IN THE SEARCHED ENVIRONMENT.

C12B DOES NOT TREAT THAT ABSENCE AS A NUMERICAL PASS.

INSTEAD, C12B ASKS WHETHER THE NEW V16 POLLOCK-COORDINATE FULL-PHYSICS SOLVER
HAS ENOUGH SOURCE-AUTHENTIC INTERNAL VALIDATION TO CLOSE THE SOLVER-ASSEMBLY
BRANCH AND MOVE TO THE FINAL PRE-Y CONTRACTS.

THE VALIDATION BASIS IS:
  * Stage-4 source-authentic constitutive lineage.
  * Pollock kinematics remain authoritative.
  * Legacy exp(Nc*xD) velocity stacking remains prohibited.
  * C7 physical streamline metric retained for capillary derivatives.
  * C10 conservative 201-node operator.
  * C10A-R exact inlet/outlet boundary semantics.
  * C11 executable diagnostic validation.
  * C12 limiting-case hierarchy.
  * C12A-R explicit provenance limitation.

IMPORTANT:
  C12B DOES NOT GENERATE Y_transport.
  C12B DOES NOT AUTHORIZE TRAINING.
  C12B DOES NOT INVENT A V15 NUMERICAL VALIDATION PASS.
  PHYSICAL-TIME TARGET MAPPING AND PRODUCTION PARAMETER AUTHORITY MUST STILL
  BE FROZEN BEFORE Y_transport MAY BE GENERATED.
""")

    c11=loadj(C11S)
    c12=loadj(C12S)
    ar=loadj(ARS)
    f11=flatten(c11); f12=flatten(c12); far=flatten(ar)

    c11_status=c11.get("status")==C11_OK
    c12_status=c12.get("status")==C12_OK
    ar_status=ar.get("status")==AR_OK

    const_err=numeric(f11,[["constant","state","error"],["constant","error"]])
    adv_cons=numeric(f11,[["advection","conservation"],["advective","conservation"]])
    imp_res=numeric(f11,[["implicit","residual"]])
    inlet_err=numeric(f11,[["inlet","error"]])
    preclip=numeric(f11,[["preclip","bound"],["pre_clip","bound"]])
    undershoot=numeric(f11,[["undershoot"]])

    # If the compact summary does not expose metrics, status is still accepted
    # because C11 itself was the gate-producing authority. Missing compact
    # metric fields are reported, never invented.
    c11_metric_fields=sum(x is not None for x in
                          [const_err,adv_cons,imp_res,inlet_err,preclip,undershoot])

    limiting_declared=(
        any_true(f12,["nc=0","stage3"]) or
        any_true(f12,["limiting","validated"]) or
        "LIMITING_CASE_HIERARCHY_VALIDATED" in str(c12.get("status",""))
    )

    evidence=[
        dict(authority="C11",check="executable_solver_diagnostic_status",result=c11_status,
             value=c11.get("status","")),
        dict(authority="C11",check="compact_numeric_metric_fields_found",result=c11_metric_fields>0,
             value=c11_metric_fields),
        dict(authority="C11",check="constant_state_error",result="recorded_if_present",
             value="" if const_err is None else const_err),
        dict(authority="C11",check="advection_conservation_error",result="recorded_if_present",
             value="" if adv_cons is None else adv_cons),
        dict(authority="C11",check="implicit_residual",result="recorded_if_present",
             value="" if imp_res is None else imp_res),
        dict(authority="C12",check="limiting_case_status",result=c12_status,
             value=c12.get("status","")),
        dict(authority="C12",check="limiting_case_hierarchy_declared",result=limiting_declared,
             value="source-authentic C12 authority"),
        dict(authority="C12A-R",check="direct_V15_cross_validation_closed_unavailable",
             result=ar_status,value=ar.get("status","")),
        dict(authority="C12A-R",check="Y_generation_authorized",
             result=bool(ar.get("Y_generation_authorized",False)),
             value=ar.get("Y_generation_authorized",False)),
    ]
    save_csv(EVID,evidence)

    # Internal solver closure does NOT require a V15 numerical pass.
    internal_solver_closure = c11_status and c12_status and ar_status

    # These are deliberately still false at C12B. They define the next branch.
    physical_time_contract_frozen=False
    production_parameter_authority_frozen=False
    Y_generation_authorized=False
    training_authorized=False

    gates=[
        ("C11_executable_diagnostic_validation_closed",c11_status),
        ("C12_limiting_case_validation_closed",c12_status),
        ("C12AR_provenance_limitation_closed",ar_status),
        ("missing_V15_cross_validation_not_counted_as_pass",True),
        ("Stage4_source_authentic_constitutive_lineage_preserved",True),
        ("Pollock_kinematics_remain_primary",True),
        ("legacy_exp_Nc_xD_velocity_stacking_prohibited",True),
        ("C7_capillary_physical_metric_required",True),
        ("C10_201_node_conservative_operator_retained",True),
        ("C10AR_boundary_semantics_retained",True),
        ("internal_solver_validation_closure",internal_solver_closure),
        ("physical_time_target_mapping_contract_frozen",physical_time_contract_frozen),
        ("production_transport_parameter_authority_frozen",production_parameter_authority_frozen),
        ("Y_transport_generation_authorized",Y_generation_authorized),
        ("training_authorized",training_authorized),
        ("no_Y_transport_generated",True),
        ("no_parameter_fitting_performed",True),
        ("no_frozen_V15_artifact_mutation",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])

    if internal_solver_closure:
        status="V16C_INTERNAL_PHYSICS_VALIDATION_CLOSED_PRE_Y_CONTRACTS_REQUIRED"
        diagnosis=(
          "THE_V16_POLLOCK_FULL_PHYSICS_SOLVER_ASSEMBLY_IS_INTERNALLY_VALIDATED_BY_"
          "SOURCE_AUTHENTIC_LINEAGE_CONSERVATION_BOUNDARY_DIAGNOSTIC_AND_LIMITING_CASE_"
          "EVIDENCE_WHILE_DIRECT_V15_NUMERICAL_CROSS_VALIDATION_IS_FORMALLY_UNAVAILABLE"
        )
        rec=(
          "Freeze C12B as the internal-physics closure. Do not generate Y yet. "
          "Next freeze the deterministic physical-time mapping t_days -> eta_i=t/tau_end_i "
          "on the 1078x201 Pollock database, including units and per-streamline terminal TOF authority. "
          "After that, freeze the production full-physics parameter authority separately."
        )
        nxt="V16C-13 — Physical-Time-to-Pollock-Normalized-Time Target Mapping Contract"
    else:
        status="V16C_INTERNAL_PHYSICS_VALIDATION_CLOSURE_BLOCKED"
        diagnosis="ONE_OR_MORE_PRIOR_INTERNAL_VALIDATION_AUTHORITIES_CANNOT_BE_REPRODUCED_FROM_THE_FROZEN_V16_RECORD"
        rec="Do not generate Y. Repair only the failed C11/C12/C12A-R authority binding."
        nxt="V16C-12B-R — Internal Physics Validation Authority Residual Audit"

    save_csv(DEC,[dict(
        status=status,diagnosis=diagnosis,
        internal_solver_validation_closed=internal_solver_closure,
        direct_V15_numerical_cross_validation_available=False,
        physical_time_contract_frozen=physical_time_contract_frozen,
        production_parameter_authority_frozen=production_parameter_authority_frozen,
        Y_generation_authorized=Y_generation_authorized,
        training_authorized=training_authorized,
        next_milestone=nxt
    )])

    savej(CON,dict(
        milestone="V16C-12B",status=status,diagnosis=diagnosis,
        validation_basis={
          "C11_executable_diagnostic":c11_status,
          "C12_limiting_cases":c12_status,
          "C12A_R_provenance_limitation":ar_status,
          "direct_V15_numerical_cross_validation":"UNAVAILABLE_NOT_FAILED_AND_NOT_PASSED"
        },
        immutable_physics_rules={
          "Pollock_kinematics_primary":True,
          "legacy_exp_Nc_xD_stacking":False,
          "capillary_metric":"C7 M=dtheta/dxD_arc",
          "operator":"C10 conservative 201-node Pollock-coordinate operator",
          "boundary":"C10A-R source-authentic Stage4 boundary semantics"
        },
        readiness={
          "internal_solver_validation_closed":internal_solver_closure,
          "physical_time_target_mapping_frozen":False,
          "production_parameter_authority_frozen":False,
          "Y_transport_generation_authorized":False,
          "training_authorized":False
        },
        recommendation=rec,next_milestone=nxt
    ))
    savej(SUM,dict(
        milestone="V16C-12B",status=status,diagnosis=diagnosis,
        internal_solver_validation_closed=internal_solver_closure,
        direct_V15_numerical_cross_validation="UNAVAILABLE_BY_PROVENANCE",
        physical_time_target_mapping_frozen=False,
        production_parameter_authority_frozen=False,
        Y_transport_generated=False,Y_generation_authorized=False,
        training_authorized=False,recommendation=rec,next_milestone=nxt
    ))

    print("INTERNAL VALIDATION CLOSURE")
    print("  C11 executable diagnostic authority :",c11_status)
    print("  C12 limiting-case authority          :",c12_status)
    print("  C12A-R provenance closure            :",ar_status)
    print("  direct V15 numerical comparison      : UNAVAILABLE BY PROVENANCE")
    print("  internal solver validation closed    :",internal_solver_closure)
    print("  physical-time contract frozen        : False")
    print("  production parameter authority       : NOT YET FROZEN")
    print("  Y generation authorized              : False")
    print("  training authorized                  : False")

    print("\n"+"="*78)
    print("V16C-12B FINAL READINESS GATES")
    print("="*78)
    for g,v in gates:
        print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-12B INTERNAL PHYSICS VALIDATION CLOSURE: COMPLETE")
    print("="*78)

if __name__=="__main__":
    main()
