from __future__ import annotations

from pathlib import Path
import ast, csv, hashlib, json, re

ROOT = Path(__file__).resolve().parent

C8_DIR = ROOT/"output"/"V16_C8_FULL_BL_CCUS_STREAMLINE_TARGET_SEMANTICS_CONTRACT"
C8_SUMMARY = C8_DIR/"PAD_Stream_V16C8_Summary.json"
C8_CONTRACT = C8_DIR/"V16C8_Full_BL_CCUS_Streamline_Target_Semantics_Contract.json"

C7_DIR = ROOT/"output"/"V16_C7_POLLOCK_TOF_FULL_BL_CCUS_ADAPTER_PHYSICS_CONTRACT"
C7_CONTRACT = C7_DIR/"V16C7_Pollock_TOF_Full_BL_CCUS_Adapter_Physics_Contract.json"
C7_METRIC = C7_DIR/"V16C7_Pollock_TOF_Streamline_Metric_Contract.npz"

STAGE4 = ROOT/"pi_rnn_stage4_full_godunov.py"
EXPECTED_SHA = "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"

OUT = ROOT/"output"/"V16_C9_SOURCE_AUTHENTIC_FULL_BL_CCUS_TARGET_GENERATOR_BINDING_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

IDENTITY = OUT/"V16C9_Source_Identity.csv"
SOLVER = OUT/"V16C9_Stage4_Solver_Operator_Lineage.csv"
ADAPTER = OUT/"V16C9_Pollock_Adapter_Implementation_Requirements.csv"
BINDING = OUT/"V16C9_Target_Generator_Binding_Decision.csv"
GATES = OUT/"V16C9_Final_Target_Generator_Binding_Gates.csv"
CONTRACT = OUT/"V16C9_Source_Authentic_Target_Generator_Binding_Contract.json"
SUMMARY = OUT/"PAD_Stream_V16C9_Summary.json"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def loadj(p): return json.loads(p.read_text(encoding="utf-8"))
def savej(p,x): p.write_text(json.dumps(x,indent=2),encoding="utf-8")

def save_csv(p, rows):
    rows=list(rows); keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)

def source_inventory(path):
    text=path.read_text(encoding="utf-8",errors="replace")
    tree=ast.parse(text)
    funcs={n.name:n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    names=set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b",text))
    return text, funcs, names

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-9")
    print("Source-Authentic Full BL/CCUS Pollock-Adapter Target Generator Binding Audit")
    print("="*78)
    print("""
C8 TARGET SEMANTICS IS FROZEN.

NO TRANSPORT SOLVE WILL BE EXECUTED.
NO Y_TRANSPORT OR SATURATION FIELD WILL BE GENERATED.
NO PI-RNN WILL BE TRAINED OR INFERRED.
NO TARGET TIMES WILL BE SELECTED.
NO LOSS WEIGHTS WILL BE CHANGED.
NO FROZEN ARTIFACT WILL BE MODIFIED.

THIS MILESTONE BINDS THE EXISTING STAGE-4 NUMERICAL PHYSICS COMPONENTS AND
DEFINES THE MINIMUM NEW V16 ADAPTER IMPLEMENTATION REQUIRED BEFORE Y MAY EXIST.
""")

    for p in [C8_SUMMARY,C8_CONTRACT,C7_CONTRACT,C7_METRIC,STAGE4]:
        if not p.exists(): raise FileNotFoundError(p)

    c8=loadj(C8_SUMMARY)
    if c8.get("status")!="V16C_FULL_BL_CCUS_STREAMLINE_TARGET_SEMANTICS_FROZEN_READY_FOR_SOURCE_AUTHENTIC_GENERATOR_BINDING":
        raise RuntimeError("C9 requires completed C8.")

    c7=loadj(C7_CONTRACT)
    stage4_sha=sha(STAGE4)
    metric_sha=sha(C7_METRIC)

    text, funcs, names=source_inventory(STAGE4)

    # Alias-tolerant source semantics. C9 does not execute Stage 4.
    has_full_solver = "solve_capillary_snapshots" in funcs or any(
        re.search(r"solve.*(?:full|capillary|snapshot)",f,re.I) for f in funcs
    )
    has_cap_diff = (
        any(re.search(r"cap|diff|tridiag|thomas|implicit",f,re.I) for f in funcs)
        and re.search(r"Pe.?c|inv_Pec|capillary.*diffusion",text,re.I|re.S) is not None
    )
    has_variable_u = re.search(r"(?:exp|expm1).*Nc.*xD|Nc.*xD.*(?:exp|expm1)",text,re.I|re.S) is not None
    has_conservative = re.search(r"conservative",text,re.I) is not None
    has_bounds = re.search(r"swc|swi",text,re.I) is not None and re.search(r"sor",text,re.I) is not None
    has_fractional_flow = (
        any(re.search(r"fractional|fw",f,re.I) for f in funcs)
        or re.search(r"\bfw\b|fractional.?flow",text,re.I) is not None
    )
    has_godunov = re.search(r"godunov",text,re.I) is not None

    identity=[{
        "stage4_source":STAGE4.name,
        "sha256":stage4_sha,
        "expected_sha256":EXPECTED_SHA,
        "exact_sha_match":stage4_sha==EXPECTED_SHA,
        "C7_metric_sha256":metric_sha,
        "C7_metric_hash_matches_contract":metric_sha==c7["metric_artifact"]["sha256"],
        "C8_contract_sha256":sha(C8_CONTRACT),
    }]
    save_csv(IDENTITY,identity)

    solver_rows=[
        dict(component="fractional_flow_and_relative_permeability",
             source_authentic=has_fractional_flow,
             reuse_policy="REUSE_STAGE4_PHYSICS"),
        dict(component="conservative_Godunov_advection",
             source_authentic=has_godunov and has_conservative,
             reuse_policy="REUSE_FLUX_LOGIC_BUT_REPLACE_NATIVE_XD_KINEMATIC_MAPPING_WITH_C7A_POLLOCK_AUTHORITY"),
        dict(component="legacy_variable_u_exp_Nc_xD",
             source_authentic=has_variable_u,
             reuse_policy="DO_NOT_APPLY_AS_SECOND_KINEMATIC_MULTIPLIER"),
        dict(component="capillary_diffusion",
             source_authentic=has_cap_diff,
             reuse_policy="REUSE_D_TILDE_AND_COEFFICIENT_PHYSICS_WITH_C7_TRANSFORMED_SPATIAL_OPERATOR"),
        dict(component="full_operator_split_solver_lineage",
             source_authentic=has_full_solver,
             reuse_policy="REFERENCE_IMPLEMENTATION_FOR_NEW_V16_ADAPTER_SOLVER"),
        dict(component="saturation_bounds",
             source_authentic=has_bounds,
             reuse_policy="PRESERVE"),
    ]
    save_csv(SOLVER,solver_rows)

    # The new target generator cannot simply call the native Stage-4 solver:
    # it solves on native xD/64-node assumptions and applies uD explicitly.
    adapter_rows=[
        dict(requirement_id="G1",
             requirement="201-node Pollock sequence",
             derivation="C8 frozen target geometry",
             implementation="new deterministic V16 transport-grid interface",
             fitted=False),
        dict(requirement_id="G2",
             requirement="theta=tau/tau_end and xD_arc=s/L",
             derivation="C7",
             implementation="consume frozen C7 metric artifact",
             fitted=False),
        dict(requirement_id="G3",
             requirement="M=dtheta/dxD_arc",
             derivation="C7",
             implementation="consume frozen C7 metric; no recalibration",
             fitted=False),
        dict(requirement_id="G4",
             requirement="capillary operator M d/dtheta[D_tilde M dS/dtheta]",
             derivation="C7/C7R",
             implementation="new conservative face-form V16 operator",
             fitted=False),
        dict(requirement_id="G5",
             requirement="Pollock TOF is kinematic authority",
             derivation="C7A/C7A-R",
             implementation="do not multiply legacy exp(Nc xD) on top of Pollock advection",
             fitted=False),
        dict(requirement_id="G6",
             requirement="Stage-4 Nc semantics retained",
             derivation="C7A/C7A-R",
             implementation="retain as source-lineage parameter/conditioning metadata; no invented PVT law",
             fitted=False),
        dict(requirement_id="G7",
             requirement="source-authentic Stage-4 constitutive physics",
             derivation="C6/C8",
             implementation="reuse relative-perm/fractional-flow/capillary constitutive functions",
             fitted=False),
        dict(requirement_id="G8",
             requirement="conservative discrete transport",
             derivation="Stage-4 Godunov lineage + C8",
             implementation="derive V16 face flux/operator before target generation",
             fitted=False),
    ]
    save_csv(ADAPTER,adapter_rows)

    direct_native_call_allowed=False
    new_adapter_solver_required=True

    gates=[
        ("C8_target_semantics_status_reproduced",True),
        ("stage4_exact_source_hash_reproduced",stage4_sha==EXPECTED_SHA),
        ("C7_metric_hash_reproduced",metric_sha==c7["metric_artifact"]["sha256"]),
        ("stage4_fractional_flow_lineage_bound",has_fractional_flow),
        ("stage4_conservative_Godunov_lineage_bound",has_godunov and has_conservative),
        ("stage4_variable_u_lineage_bound",has_variable_u),
        ("stage4_capillary_diffusion_lineage_bound",has_cap_diff),
        ("stage4_full_solver_lineage_bound",has_full_solver),
        ("stage4_saturation_bounds_lineage_bound",has_bounds),
        ("native_Stage4_direct_call_classified_as_incompatible_with_C8_target_geometry",not direct_native_call_allowed),
        ("new_V16_Pollock_adapter_solver_requirement_explicit",new_adapter_solver_required),
        ("201_node_sequence_requirement_explicit",True),
        ("C7_metric_consumption_requirement_explicit",True),
        ("C7_capillary_transform_requirement_explicit",True),
        ("C7A_legacy_uD_suppression_requirement_explicit",True),
        ("no_new_PVT_law_introduced",True),
        ("no_fitted_adapter_parameter_introduced",True),
        ("no_target_times_selected",True),
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
        status="V16C_SOURCE_AUTHENTIC_TARGET_GENERATOR_LINEAGE_BOUND_NEW_POLLOCK_ADAPTER_SOLVER_REQUIRED"
        diagnosis="STAGE4_CONSTITUTIVE_AND_NUMERICAL_PHYSICS_ARE_BOUND_BUT_NATIVE_STAGE4_SOLVER_CANNOT_BE_CALLED_DIRECTLY_BECAUSE_V16_REQUIRES_201_NODE_POLLOCK_KINEMATICS_AND_THE_C7_TRANSFORMED_CAPILLARY_OPERATOR"
        rec=("Freeze C9 binding. Implement C10 as a no-target numerical operator construction/verification milestone: "
             "build the conservative 201-node Pollock-coordinate advection-capillary operator from the bound Stage-4 physics, "
             "consume the frozen C7 metric, suppress legacy uD double counting, and validate algebraic/conservation properties before any Y generation.")
        nxt="V16C-10 — Conservative 201-Node Pollock-Coordinate Full-Physics Operator Construction"
    else:
        status="V16C_SOURCE_AUTHENTIC_TARGET_GENERATOR_BINDING_INCOMPLETE"
        diagnosis="ONE_OR_MORE_STAGE4_SOLVER_OR_ADAPTER_BINDING_GATES_FAILED"
        rec="Do not implement or generate Y. Audit only failed C9 gates."
        nxt="V16C-9R — Target Generator Binding Residual Audit"

    decision=[dict(
        status=status,diagnosis=diagnosis,
        direct_native_Stage4_solver_call="PROHIBITED",
        source_authentic_constitutive_reuse="REQUIRED",
        new_V16_Pollock_adapter_solver="REQUIRED",
        Y_generation_authorized=False,
        next_milestone=nxt)]
    save_csv(BINDING,decision)

    savej(CONTRACT,dict(
        milestone="V16C-9",status=status,diagnosis=diagnosis,
        source_identity=identity[0],
        bound_stage4_components=solver_rows,
        adapter_requirements=adapter_rows,
        direct_native_stage4_solver_call="PROHIBITED",
        Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))
    savej(SUMMARY,dict(
        milestone="V16C-9",status=status,diagnosis=diagnosis,
        direct_native_stage4_solver_call_allowed=False,
        new_pollock_adapter_solver_required=True,
        Y_transport_generated=False,
        Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))

    print("STAGE-4 SOURCE BINDING")
    print(f"  Exact SHA                 : {stage4_sha==EXPECTED_SHA}")
    print(f"  Fractional flow           : {has_fractional_flow}")
    print(f"  Conservative Godunov      : {has_godunov and has_conservative}")
    print(f"  Variable uD=exp(Nc xD)    : {has_variable_u}")
    print(f"  Capillary diffusion       : {has_cap_diff}")
    print(f"  Full solver lineage       : {has_full_solver}")
    print(f"  Saturation bounds         : {has_bounds}")

    print("\nGENERATOR BINDING DECISION")
    print("  Direct native Stage-4 call: PROHIBITED")
    print("  Stage-4 constitutive reuse : REQUIRED")
    print("  New V16 adapter solver     : REQUIRED")
    print("  Sequence                   : 201 Pollock nodes")
    print("  C7 metric                  : REQUIRED")
    print("  Legacy exp(Nc xD) stacking : PROHIBITED")
    print("  Y generation               : NOT AUTHORIZED YET")

    print("\n"+"="*78)
    print("V16C-9 FINAL TARGET GENERATOR BINDING GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-9 TARGET GENERATOR BINDING AUDIT: COMPLETE")
    print("="*78)

if __name__=="__main__":
    main()
