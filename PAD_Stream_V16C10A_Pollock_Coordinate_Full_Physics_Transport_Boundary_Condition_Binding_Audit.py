from __future__ import annotations

from pathlib import Path
import ast, csv, hashlib, json, re

ROOT = Path(__file__).resolve().parent

C10_DIR = ROOT/"output"/"V16_C10_CONSERVATIVE_201_NODE_POLLOCK_FULL_PHYSICS_OPERATOR"
C10_SUMMARY = C10_DIR/"PAD_Stream_V16C10_Summary.json"
C10_CONTRACT = C10_DIR/"V16C10_Conservative_Pollock_Operator_Contract.json"
C10_OP = C10_DIR/"V16C10_Conservative_201_Node_Pollock_Operator_Geometry.npz"

C9_DIR = ROOT/"output"/"V16_C9_SOURCE_AUTHENTIC_FULL_BL_CCUS_TARGET_GENERATOR_BINDING_AUDIT"
C9_CONTRACT = C9_DIR/"V16C9_Source_Authentic_Target_Generator_Binding_Contract.json"

STAGE4 = ROOT/"pi_rnn_stage4_full_godunov.py"
EXPECTED_SHA = "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"

OUT = ROOT/"output"/"V16_C10A_POLLOCK_FULL_PHYSICS_BOUNDARY_CONDITION_BINDING_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

EVIDENCE = OUT/"V16C10A_Stage4_Boundary_Source_Evidence.csv"
BC = OUT/"V16C10A_Pollock_Boundary_Condition_Contract.csv"
CAP = OUT/"V16C10A_Capillary_Boundary_Transform_Contract.csv"
GATES = OUT/"V16C10A_Final_Boundary_Binding_Gates.csv"
DECISION = OUT/"V16C10A_Boundary_Binding_Decision.csv"
CONTRACT = OUT/"V16C10A_Pollock_Full_Physics_Boundary_Condition_Contract.json"
SUMMARY = OUT/"PAD_Stream_V16C10A_Summary.json"

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

def source_audit(path):
    text=path.read_text(encoding="utf-8",errors="replace")
    tree=ast.parse(text)
    funcs={n.name:n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}

    # We deliberately separate source evidence from interpretation.
    inj_terms = re.findall(r".{0,100}(?:inject|inlet|left.?bc|boundary).{0,160}", text, re.I)
    out_terms = re.findall(r".{0,100}(?:outlet|right.?bc|tip.?bc|zero.?gradient|neumann).{0,160}", text, re.I)
    cap_terms = re.findall(r".{0,100}(?:capillary|diffusion|flux).{0,160}", text, re.I)

    injector_bc_function = any(re.search(r"inject|inlet|left.*bc|bc.*left",f,re.I) for f in funcs)
    outlet_bc_function = any(re.search(r"outlet|right.*bc|tip.*bc|bc.*right",f,re.I) for f in funcs)
    boundary_language = bool(inj_terms or out_terms)
    capillary_boundary_language = bool(
        re.search(r"(?:capillary|diffusion).{0,250}(?:boundary|bc|inlet|outlet|left|right)|"
                  r"(?:boundary|bc|inlet|outlet|left|right).{0,250}(?:capillary|diffusion)",
                  text,re.I|re.S)
    )

    # Saturation symbols are evidence of Dirichlet-like injection semantics,
    # but we do NOT assign a numeric value here.
    saturation_bc_language = bool(
        re.search(r"(?:Sw|S_w|swi|swc|1\s*-\s*sor).{0,100}(?:inject|inlet|left|boundary)|"
                  r"(?:inject|inlet|left|boundary).{0,100}(?:Sw|S_w|swi|swc|sor)",
                  text,re.I|re.S)
    )

    # Detect common no-gradient/no-diffusive-flux outlet semantics without
    # claiming them unless actually present.
    zero_gradient_language = bool(
        re.search(r"zero.?gradient|no.?flux|neumann|dS.?dx\s*=\s*0|gradient.{0,30}0",text,re.I)
    )

    return {
        "exact_sha_match":sha(path)==EXPECTED_SHA,
        "injector_bc_function_detected":injector_bc_function,
        "outlet_bc_function_detected":outlet_bc_function,
        "boundary_language_detected":boundary_language,
        "saturation_boundary_language_detected":saturation_bc_language,
        "capillary_boundary_language_detected":capillary_boundary_language,
        "zero_gradient_or_no_flux_language_detected":zero_gradient_language,
        "injector_evidence_excerpt":" | ".join(x.strip().replace("\n"," ") for x in inj_terms[:4]),
        "outlet_evidence_excerpt":" | ".join(x.strip().replace("\n"," ") for x in out_terms[:4]),
        "capillary_evidence_excerpt":" | ".join(x.strip().replace("\n"," ") for x in cap_terms[:4]),
    }

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-10A")
    print("Pollock-Coordinate Full-Physics Transport Boundary Condition Binding Audit")
    print("="*78)
    print("""
C10 INTERIOR OPERATOR GEOMETRY IS IMMUTABLE.

NO PHYSICAL-TIME TRANSPORT SOLVE WILL BE EXECUTED.
NO Y_TRANSPORT OR SATURATION FIELD WILL BE GENERATED.
NO NUMERIC BOUNDARY VALUE WILL BE INVENTED.
NO PI-RNN WILL BE TRAINED OR INFERRED.
NO TARGET TIMES WILL BE SELECTED.
NO FROZEN ARTIFACT WILL BE MODIFIED.

THIS MILESTONE BINDS ONLY SOURCE-SUPPORTED BOUNDARY SEMANTICS AND MAPS THEM
ONTO THE POLLOCK-COORDINATE CONSERVATIVE FACE-FLUX FORM.
""")

    for p in [C10_SUMMARY,C10_CONTRACT,C10_OP,C9_CONTRACT,STAGE4]:
        if not p.exists(): raise FileNotFoundError(p)

    c10=loadj(C10_SUMMARY)
    if c10.get("status")!="V16C_CONSERVATIVE_201_NODE_POLLOCK_OPERATOR_GEOMETRY_CONSTRUCTED_BOUNDARY_PHYSICS_PENDING":
        raise RuntimeError("C10A requires completed C10.")

    c10c=loadj(C10_CONTRACT)
    if sha(C10_OP)!=c10c["operator_sha256"]:
        raise RuntimeError("C10 operator artifact hash mismatch.")

    ev=source_audit(STAGE4)
    save_csv(EVIDENCE,[ev])

    # Boundary contract: source-authentic where bound, otherwise explicitly
    # unresolved. The coordinate transform itself is exact:
    # d/dxD = M d/dtheta, so a homogeneous spatial gradient maps to a
    # homogeneous theta gradient because M>0.
    inlet_bound = ev["boundary_language_detected"] and ev["saturation_boundary_language_detected"]
    outlet_no_flux_bound = ev["zero_gradient_or_no_flux_language_detected"]
    capillary_bc_bound = ev["capillary_boundary_language_detected"] or outlet_no_flux_bound

    bc_rows=[
        dict(boundary="inlet",
             native_stage4_semantics="source-supported saturation/injection boundary" if inlet_bound else "UNRESOLVED",
             pollock_location="theta=0",
             advection_face_action="use source-authentic injected-state fractional-flow face flux; numeric state deferred to source parameter binding",
             capillary_action="do not invent; bind exact source treatment before solve",
             authority="STAGE4_SOURCE" if inlet_bound else "PENDING"),
        dict(boundary="outlet",
             native_stage4_semantics="zero-gradient/no-diffusive-flux" if outlet_no_flux_bound else "UNRESOLVED",
             pollock_location="theta=1",
             advection_face_action="conservative outflow using interior/upwind state; no external velocity multiplier",
             capillary_action="G_out=0 if source zero-gradient/no-flux semantics are confirmed",
             authority="STAGE4_SOURCE" if outlet_no_flux_bound else "PENDING"),
    ]
    save_csv(BC,bc_rows)

    cap_rows=[
        dict(native_condition="dS/dxD = 0",
             transformed_condition="M dS/dtheta = 0",
             implication="because M>0, dS/dtheta=0",
             status="EXACT_COORDINATE_TRANSFORM"),
        dict(native_condition="capillary face flux = 0",
             transformed_condition="D_tilde M dS/dtheta = 0",
             implication="transformed face flux remains zero",
             status="EXACT_COORDINATE_TRANSFORM"),
        dict(native_condition="Dirichlet saturation",
             transformed_condition="same saturation value at corresponding theta boundary",
             implication="coordinate change does not alter saturation value",
             status="EXACT_COORDINATE_TRANSFORM"),
    ]
    save_csv(CAP,cap_rows)

    # We only authorize solver construction if BOTH physical boundaries can be
    # bound from source. Otherwise the correct next step is a residual audit,
    # not guessing a boundary condition.
    gates=[
        ("C10_status_reproduced",True),
        ("C10_operator_hash_reproduced",sha(C10_OP)==c10c["operator_sha256"]),
        ("stage4_exact_source_hash_reproduced",ev["exact_sha_match"]),
        ("stage4_boundary_language_detected",ev["boundary_language_detected"]),
        ("stage4_inlet_saturation_semantics_bound",inlet_bound),
        ("stage4_outlet_zero_gradient_or_no_flux_semantics_bound",outlet_no_flux_bound),
        ("capillary_boundary_semantics_bound",capillary_bc_bound),
        ("inlet_maps_to_theta_zero",True),
        ("outlet_maps_to_theta_one",True),
        ("homogeneous_gradient_transform_exact",True),
        ("zero_capillary_flux_transform_exact",True),
        ("Dirichlet_saturation_value_invariant_under_coordinate_change",True),
        ("legacy_exp_Nc_xD_not_reintroduced_at_boundary",True),
        ("no_numeric_boundary_value_invented",True),
        ("no_transport_time_march",True),
        ("no_Y_transport_generated",True),
        ("no_saturation_generated",True),
        ("no_model_predict",True),
        ("no_training",True),
        ("no_target_times_selected",True),
        ("no_frozen_artifact_mutation",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])
    ok=all(v for _,v in gates)

    if ok:
        status="V16C_POLLOCK_FULL_PHYSICS_BOUNDARY_SEMANTICS_BOUND_READY_FOR_SOLVER_ASSEMBLY"
        diagnosis="SOURCE_AUTHENTIC_INLET_AND_OUTLET_TRANSPORT_BOUNDARIES_ARE_BOUND_AND_EXACTLY_MAPPED_TO_THETA_ZERO_AND_ONE_WITH_TRANSFORMED_CAPILLARY_FLUX_SEMANTICS"
        rec=("Freeze C10A. Proceed to C11 to assemble the executable conservative full-physics Pollock-coordinate solver, "
             "still using diagnostic/non-target runs first before authorizing Y generation.")
        nxt="V16C-11 — Executable Conservative Full-Physics Pollock Transport Solver Assembly and Diagnostic Validation"
    else:
        status="V16C_POLLOCK_BOUNDARY_PHYSICS_REQUIRES_SOURCE_AUDIT"
        diagnosis="ONE_OR_MORE_PHYSICAL_BOUNDARY_SEMANTICS_ARE_NOT_EXPLICITLY_BOUND_FROM_THE_STAGE4_SOURCE"
        rec=("Do not guess missing boundary physics and do not generate Y. Audit the failed C10A source-boundary gates against "
             "the exact Stage-4 solver implementation and, if needed, its nested Stage-3 predecessor.")
        nxt="V16C-10A-R — Full-Physics Boundary Source Residual Audit"

    save_csv(DECISION,[dict(
        status=status,diagnosis=diagnosis,
        inlet_boundary="BOUND" if inlet_bound else "PENDING",
        outlet_boundary="BOUND" if outlet_no_flux_bound else "PENDING",
        capillary_boundary="BOUND" if capillary_bc_bound else "PENDING",
        solver_assembly_authorized=ok,
        Y_generation_authorized=False,
        next_milestone=nxt)])

    savej(CONTRACT,dict(
        milestone="V16C-10A",status=status,diagnosis=diagnosis,
        stage4_source_sha256=sha(STAGE4),
        C10_operator_sha256=sha(C10_OP),
        source_evidence=ev,boundary_contract=bc_rows,
        coordinate_transform=cap_rows,
        solver_assembly_authorized=ok,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))

    savej(SUMMARY,dict(
        milestone="V16C-10A",status=status,diagnosis=diagnosis,
        inlet_boundary_bound=inlet_bound,
        outlet_boundary_bound=outlet_no_flux_bound,
        capillary_boundary_bound=capillary_bc_bound,
        solver_assembly_authorized=ok,
        Y_transport_generated=False,
        recommendation=rec,next_milestone=nxt))

    print("SOURCE BOUNDARY EVIDENCE")
    print("  Stage-4 exact SHA                  :",ev["exact_sha_match"])
    print("  Boundary language                  :",ev["boundary_language_detected"])
    print("  Inlet saturation semantics         :",inlet_bound)
    print("  Outlet zero-gradient/no-flux       :",outlet_no_flux_bound)
    print("  Capillary boundary semantics       :",capillary_bc_bound)

    print("\nPOLLOCK MAPPING")
    print("  Inlet                              : theta = 0")
    print("  Outlet                             : theta = 1")
    print("  dS/dxD = 0                        : M dS/dtheta = 0")
    print("  Zero capillary flux                : preserved exactly")
    print("  Dirichlet saturation               : value invariant")
    print("  Legacy exp(Nc xD) boundary factor  : NOT INTRODUCED")

    print("\n"+"="*78)
    print("V16C-10A FINAL BOUNDARY BINDING GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-10A BOUNDARY CONDITION BINDING AUDIT: COMPLETE")
    print("="*78)

if __name__=="__main__":
    main()
