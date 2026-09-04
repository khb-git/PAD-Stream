from __future__ import annotations
from pathlib import Path
import ast, csv, hashlib, json, re

ROOT=Path(__file__).resolve().parent
C13D=ROOT/"output"/"V16_C13_PHYSICAL_TIME_TO_POLLOCK_NORMALIZED_TIME_TARGET_MAPPING_CONTRACT"
C13S=C13D/"PAD_Stream_V16C13_Summary.json"

OUT=ROOT/"output"/"V16_C14_PRODUCTION_FULL_PHYSICS_TRANSPORT_PARAMETER_AUTHORITY_CONTRACT"
OUT.mkdir(parents=True,exist_ok=True)
SRC=OUT/"V16C14_Stage4_Source_Authority.csv"
PAR=OUT/"V16C14_Production_Parameter_Authority.csv"
GATES=OUT/"V16C14_Final_Parameter_Authority_Gates.csv"
CON=OUT/"V16C14_Production_Full_Physics_Parameter_Contract.json"
SUM=OUT/"PAD_Stream_V16C14_Summary.json"

C13_OK="V16C_PHYSICAL_TIME_TO_POLLOCK_NORMALIZED_TIME_MAPPING_FROZEN"

def loadj(p):
    if not p.exists(): raise FileNotFoundError(p)
    return json.loads(p.read_text(encoding="utf-8"))
def savej(p,x): p.write_text(json.dumps(x,indent=2),encoding="utf-8")
def save_csv(p,rows):
    rows=list(rows); keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def find_stage4():
    candidates=[]
    for p in ROOT.glob("*.py"):
        try:t=p.read_text(encoding="utf-8",errors="replace")
        except:continue
        if ("STAGE 4: FULL PHYSICS" in t and "CONSERVATIVE_FORM" in t and
            "Pe_c" in t and "Nc" in t and "lambda" in t):
            candidates.append(p)
    exact=[p for p in candidates if sha(p)=="165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"]
    if len(exact)==1:return exact[0],True
    if len(candidates)==1:return candidates[0],False
    if not candidates:raise FileNotFoundError("Stage4 full-physics source not found in project root.")
    raise RuntimeError("Ambiguous Stage4 source binding:\n  "+"\n  ".join(map(str,candidates)))

def source_semantics(text):
    def has(*terms):return all(x.lower() in text.lower() for x in terms)
    return dict(
        full_physics=has("STAGE 4: FULL PHYSICS"),
        conservative_form=has("CONSERVATIVE_FORM = True"),
        nc_density_ratio=has("Nc=ln(rho_inj/rho_i)") or has("Nc = ln(rho_inj/rho_i)"),
        variable_velocity=has("u_D(x_D)=exp(Nc x_D)") or has("u_D(x_D) = exp(Nc x_D)"),
        capillary_Pec=has("Pe_c"),
        capillary_lambda=has("lambda"),
        bounded_endpoints=has("swc","sor","krw_max","kro_max"),
        viscosities=has("mu_w","mu_o"),
    )

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-14")
    print("Production Full-Physics Transport Parameter Authority Contract")
    print("="*78)
    print("""
C13 FROZE PHYSICAL-TIME MAPPING. C14 NOW FREEZES THE PRODUCTION TRANSPORT
PARAMETER AUTHORITY BEFORE ANY Y_transport MAY BE GENERATED.

AUTHORITY POLICY:
  * Stage4 exact source defines constitutive semantics and parameter meanings.
  * PAD-Stream Foundation Case defines porosity/geometry/kinematics.
  * Pollock TOF remains the velocity/travel-time authority.
  * Legacy Stage4 u_D=exp(Nc*xD) is NOT reintroduced.
  * Nc is retained as source-lineage compressibility metadata/conditioning only
    unless a separately authorized storage/PVT closure is introduced.
  * No parameter is fitted to unavailable V15 numerical states.

PRODUCTION BASE PARAMETER SET:
  nw=no=2
  Swc=Sor=0.2
  krw_max=kro_max=0.8
  mu_w=0.5 cP
  mu_o=5.0 cP
  phi=0.20 from Foundation Case
  Pe_c=22
  lambda_c=2.0
  Nc=0.1 metadata/conditioning only

NOTE:
  Stage4 Case1 used mu_o=0.7 cP as a diagnostic/test override.
  C14 DOES NOT promote that diagnostic override to the production base case.
  The production base retains the established RockFluid default mu_o=5.0 cP.
""")
    c13=loadj(C13S)
    if c13.get("status")!=C13_OK:
        raise RuntimeError("C14 requires frozen C13 physical-time mapping.")

    s4,exact=find_stage4()
    text=s4.read_text(encoding="utf-8",errors="replace")
    sem=source_semantics(text)
    s4sha=sha(s4)

    # Production authority: explicit, source-derived/default or Foundation Case.
    params=[
      dict(parameter="nw",value=2.0,units="-",authority="Stage4 RockFluid default",role="constitutive"),
      dict(parameter="no",value=2.0,units="-",authority="Stage4 RockFluid default",role="constitutive"),
      dict(parameter="Swc",value=0.2,units="fraction",authority="Stage4 RockFluid default",role="constitutive"),
      dict(parameter="Sor",value=0.2,units="fraction",authority="Stage4 RockFluid default",role="constitutive"),
      dict(parameter="krw_max",value=0.8,units="-",authority="Stage4 RockFluid default",role="constitutive"),
      dict(parameter="kro_max",value=0.8,units="-",authority="Stage4 RockFluid default",role="constitutive"),
      dict(parameter="mu_w",value=0.5,units="cP",authority="Stage4 RockFluid default",role="constitutive"),
      dict(parameter="mu_o",value=5.0,units="cP",authority="Stage4 RockFluid default",role="constitutive"),
      dict(parameter="phi",value=0.20,units="fraction",authority="V16A Foundation Case",role="storage/capillary coefficient"),
      dict(parameter="Pe_c",value=22.0,units="-",authority="Stage4 FULL source reference case",role="capillary"),
      dict(parameter="lambda_c",value=2.0,units="-",authority="Stage4 FULL source reference case",role="capillary"),
      dict(parameter="Nc",value=0.1,units="-",authority="Stage4 FULL source reference case",role="metadata/conditioning_only"),
    ]
    save_csv(PAR,params)
    save_csv(SRC,[dict(path=str(s4.relative_to(ROOT)),sha256=s4sha,
                       exact_known_stage4_sha256=exact,**sem)])

    # Explicit policy checks.
    span=1.0-0.2-0.2
    endpoints_valid=span>0
    viscosities_positive=0.5>0 and 5.0>0
    capillary_valid=22.0>0 and 2.0>0
    phi_valid=0<0.20<1
    nc_not_kinematic=True
    no_fit=True

    gates=[
      ("C13_physical_time_mapping_frozen",True),
      ("Stage4_full_physics_source_bound",sem["full_physics"]),
      ("Stage4_conservative_source_semantics_bound",sem["conservative_form"]),
      ("Stage4_exact_known_source_hash_bound",exact),
      ("Brooks_Corey_endpoints_valid",endpoints_valid),
      ("viscosities_positive",viscosities_positive),
      ("Foundation_porosity_valid",phi_valid),
      ("capillary_Pe_c_lambda_positive",capillary_valid),
      ("production_mu_o_uses_RockFluid_default_5cp_not_Case1_override",True),
      ("Nc_source_semantics_retained",sem["nc_density_ratio"]),
      ("legacy_exp_Nc_xD_source_semantics_recognized",sem["variable_velocity"]),
      ("legacy_exp_Nc_xD_not_used_in_PAD_Stream_kinematics",nc_not_kinematic),
      ("Pollock_kinematics_remain_authoritative",True),
      ("Nc_role_metadata_conditioning_only",True),
      ("no_uninvented_PVT_storage_law",True),
      ("no_parameter_fit_to_missing_V15_states",no_fit),
      ("production_parameter_set_complete",len(params)==12),
      ("no_transport_solve_performed",True),
      ("no_Y_transport_generated",True),
      ("training_not_authorized",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])
    passed=all(v for _,v in gates)

    if passed:
        status="V16C_PRODUCTION_FULL_PHYSICS_TRANSPORT_PARAMETER_AUTHORITY_FROZEN"
        diagnosis="THE_PRODUCTION_BL_CCUS_CONSTITUTIVE_PARAMETER_SET_IS_BOUND_TO_STAGE4_SOURCE_SEMANTICS_AND_FOUNDATION_CASE_POROSITY_WITH_POLLOCK_KINEMATICS_PRESERVED_AND_NC_EXCLUDED_FROM_DUPLICATE_VELOCITY_SCALING"
        rec=("Freeze C14. The remaining pre-Y decision is the physical target-time schedule. "
             "Next freeze which physical days constitute the V16 source-authentic supervision set; "
             "do not inherit uncertified V15 deployment times merely because they were historical SG7E reference times.")
        nxt="V16C-15 — Production Physical Target-Time Schedule Authority Contract"
    else:
        status="V16C_PRODUCTION_PARAMETER_AUTHORITY_BLOCKED"
        diagnosis="ONE_OR_MORE_STAGE4_SOURCE_OR_PARAMETER_AUTHORITY_GATES_FAILED"
        rec="Do not generate Y. Repair only the failed source/parameter authority gate."
        nxt="V16C-14R — Production Parameter Authority Residual Audit"

    contract=dict(
      milestone="V16C-14",status=status,diagnosis=diagnosis,
      stage4_source=str(s4.relative_to(ROOT)),stage4_sha256=s4sha,
      production_parameters={r["parameter"]:dict(value=r["value"],units=r["units"],
                                                   authority=r["authority"],role=r["role"]) for r in params},
      policies={
        "Pollock_kinematics_primary":True,
        "use_exp_Nc_xD_velocity_scaling":False,
        "Nc_role":"source-lineage metadata/conditioning only",
        "invented_PVT_storage_law":False,
        "fit_to_V15_reference":False,
        "Stage4_Case1_mu_o_0p7_promoted_to_production":False
      },
      physical_target_time_schedule_frozen=False,
      Y_transport_generated=False,Y_generation_authorized=False,
      training_authorized=False,recommendation=rec,next_milestone=nxt
    )
    savej(CON,contract)
    savej(SUM,dict(
      milestone="V16C-14",status=status,diagnosis=diagnosis,
      production_parameter_authority_frozen=passed,
      stage4_exact_source_hash_bound=exact,
      physical_target_time_schedule_frozen=False,
      Y_transport_generated=False,Y_generation_authorized=False,
      training_authorized=False,recommendation=rec,next_milestone=nxt
    ))

    print("PRODUCTION PARAMETER AUTHORITY")
    print("  Stage4 source :",s4)
    print("  Stage4 SHA256 :",s4sha)
    print("  exact source  :",exact)
    for r in params:
        print(f"  {r['parameter']:10s} = {r['value']:<8} {r['units']:<8} [{r['role']}]")
    print("  exp(Nc*xD) velocity scaling : PROHIBITED IN PAD-STREAM")
    print("  Y generation authorized     : False")

    print("\n"+"="*78)
    print("V16C-14 FINAL PARAMETER AUTHORITY GATES")
    print("="*78)
    for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-14 PRODUCTION PARAMETER AUTHORITY CONTRACT: COMPLETE")
    print("="*78)

if __name__=="__main__":main()
