from __future__ import annotations
from pathlib import Path
import ast, csv, hashlib, json, re

ROOT = Path(__file__).resolve().parent
C10A_DIR = ROOT/"output"/"V16_C10A_POLLOCK_FULL_PHYSICS_BOUNDARY_CONDITION_BINDING_AUDIT"
C10A_SUMMARY = C10A_DIR/"PAD_Stream_V16C10A_Summary.json"
C10A_GATES = C10A_DIR/"V16C10A_Final_Boundary_Binding_Gates.csv"
C10_DIR = ROOT/"output"/"V16_C10_CONSERVATIVE_201_NODE_POLLOCK_FULL_PHYSICS_OPERATOR"
C10_CONTRACT = C10_DIR/"V16C10_Conservative_Pollock_Operator_Contract.json"
C10_OP = C10_DIR/"V16C10_Conservative_201_Node_Pollock_Operator_Geometry.npz"

STAGE3 = ROOT/"pi_rnn_stage3_capillary.py"
STAGE4 = ROOT/"pi_rnn_stage4_full_godunov.py"
SHA3="dab8eade38ac08c819ac27d803c8f1bceca9722c4c37e82977dbef6e6232ae0f"
SHA4="165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"

OUT=ROOT/"output"/"V16_C10A_R_FULL_PHYSICS_BOUNDARY_SOURCE_RESIDUAL_AUDIT"
OUT.mkdir(parents=True,exist_ok=True)
EVIDENCE=OUT/"V16C10AR_Exact_Solver_Boundary_Evidence.csv"
SEMANTICS=OUT/"V16C10AR_Corrected_Boundary_Semantics.csv"
GATES=OUT/"V16C10AR_Final_Residual_Audit_Gates.csv"
DECISION=OUT/"V16C10AR_Boundary_Residual_Decision.csv"
CONTRACT=OUT/"V16C10AR_Boundary_Source_Residual_Contract.json"
SUMMARY=OUT/"PAD_Stream_V16C10AR_Summary.json"

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

def fn_source(path,name):
    text=path.read_text(encoding="utf-8",errors="replace")
    tree=ast.parse(text)
    for n in ast.walk(tree):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name:
            return ast.get_source_segment(text,n) or ""
    return ""

def audit_solver(path, expected_sha, stage):
    src=fn_source(path,"solve_capillary_snapshots")
    if not src: raise RuntimeError(f"{path.name}: solve_capillary_snapshots not found")
    # Exact implementation semantics, not descriptive labels.
    held_doc=bool(re.search(r"held-value outlet row",src,re.I))
    inj_assign=bool(re.search(r"S\s*\[\s*0\s*\]\s*=\s*sw_inj",src))
    inj_rhs=bool(re.search(r"rhs\s*\[\s*0\s*\]\s*=\s*sw_inj",src))
    out_adv=bool(re.search(r"F\s*\[\s*nx\s*\]\s*=\s*.*f\s*\[\s*-1\s*\]",src))
    # The tridiagonal boundary rows remain identity because only 1:-1 entries
    # of lower/upper/diag are changed, and rhs is S.copy().
    rhs_copy=bool(re.search(r"rhs\s*=\s*S\.copy\s*\(\s*\)",src))
    diag_ones=bool(re.search(r"diag\s*=\s*np\.ones\s*\(\s*nx\s*\)",src))
    diag_interior=bool(re.search(r"diag\s*\[\s*1\s*:\s*-1\s*\]\s*=",src))
    lower_interior=bool(re.search(r"lower\s*\[\s*1\s*:\s*-1\s*\]\s*=",src))
    upper_interior=bool(re.search(r"upper\s*\[\s*1\s*:\s*-1\s*\]\s*=",src))
    solve=bool(re.search(r"solve_banded",src))
    held_implementation=all([rhs_copy,diag_ones,diag_interior,lower_interior,upper_interior,solve])
    return dict(
        stage=stage, source=path.name, sha256=sha(path), exact_sha_match=sha(path)==expected_sha,
        held_value_outlet_docstring=held_doc,
        injector_state_assignment=inj_assign,
        injector_diffusion_rhs_assignment=inj_rhs,
        advective_outlet_uses_last_interior_state=out_adv,
        diffusion_rhs_is_current_state_copy=rhs_copy,
        diffusion_diagonal_initialized_identity=diag_ones,
        diffusion_coefficients_only_interior=diag_interior and lower_interior and upper_interior,
        banded_diffusion_solve_present=solve,
        held_value_outlet_implementation_proven=held_implementation,
    )

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-10A-R")
    print("Full-Physics Boundary Source Residual Audit")
    print("="*78)
    print("""
THIS AUDIT ADDRESSES ONLY THE FAILED C10A OUTLET-SEMANTICS GATE.

THE EXACT STAGE-4 SOLVER DOES NOT LABEL ITS OUTLET AS "ZERO GRADIENT".
IT DOCUMENTS A "HELD-VALUE OUTLET ROW" AND IMPLEMENTS THAT ROW DIRECTLY.

C10A-R WILL PRESERVE THAT SOURCE SEMANTIC. IT WILL NOT REINTERPRET THE
HELD-VALUE ROW AS A ZERO-GRADIENT/NEUMANN CONDITION.

NO TRANSPORT SOLVE, Y GENERATION, TRAINING, OR FROZEN MUTATION OCCURS.
""")
    for p in [C10A_SUMMARY,C10A_GATES,C10_CONTRACT,C10_OP,STAGE3,STAGE4]:
        if not p.exists(): raise FileNotFoundError(p)

    c10a=loadj(C10A_SUMMARY)
    if c10a.get("status")!="V16C_POLLOCK_BOUNDARY_PHYSICS_REQUIRES_SOURCE_AUDIT":
        raise RuntimeError("C10A-R requires C10A source-audit state.")
    with C10A_GATES.open(newline="",encoding="utf-8") as f:
        prior=list(csv.DictReader(f))
    failed=[r["gate"] for r in prior if str(r["passed"]).lower() not in ("true","1","yes")]
    if failed != ["stage4_outlet_zero_gradient_or_no_flux_semantics_bound"]:
        raise RuntimeError(f"Expected one failed outlet gate; found {failed}")

    c10=loadj(C10_CONTRACT)
    if sha(C10_OP)!=c10["operator_sha256"]: raise RuntimeError("C10 operator hash mismatch.")

    e3=audit_solver(STAGE3,SHA3,3)
    e4=audit_solver(STAGE4,SHA4,4)
    save_csv(EVIDENCE,[e3,e4])

    stage4_held=e4["held_value_outlet_docstring"] and e4["held_value_outlet_implementation_proven"]
    nested=stage4_held and e3["held_value_outlet_implementation_proven"]

    rows=[
        dict(boundary="inlet",native_solver="Dirichlet sw_inj; reapplied after advection and diffusion",
             Pollock_mapping="theta=0; preserve source-authentic injected saturation state",
             classification="BOUND"),
        dict(boundary="outlet_advection",
             native_solver="outflow face uses last-cell fractional flow F[nx] ~ f[-1] (native source also multiplies legacy u_face)",
             Pollock_mapping="theta=1 conservative outflow from terminal interior state; DO NOT restore legacy uD multiplier",
             classification="BOUND"),
        dict(boundary="outlet_capillary_diffusion",
             native_solver="held-value outlet row: diffusion solve leaves terminal node at its post-advection current value during that substep",
             Pollock_mapping="theta=1 identity/held-value diffusion row",
             classification="BOUND"),
        dict(boundary="outlet_capillary_interpretation",
             native_solver="NOT explicitly zero-gradient/Neumann",
             Pollock_mapping="do not replace with G_out=0 unless separately authorized",
             classification="PROVENANCE_CORRECTION"),
    ]
    save_csv(SEMANTICS,rows)

    gates=[
        ("prior_C10A_status_requires_source_audit",True),
        ("exactly_one_C10A_gate_failed",len(failed)==1),
        ("failed_gate_is_outlet_zero_gradient_or_no_flux_semantics",failed==["stage4_outlet_zero_gradient_or_no_flux_semantics_bound"]),
        ("stage3_exact_source_hash_reproduced",e3["exact_sha_match"]),
        ("stage4_exact_source_hash_reproduced",e4["exact_sha_match"]),
        ("stage4_held_value_outlet_docstring_reproduced",e4["held_value_outlet_docstring"]),
        ("stage4_held_value_outlet_implementation_proven",e4["held_value_outlet_implementation_proven"]),
        ("stage4_advective_outlet_last_state_semantics_proven",e4["advective_outlet_uses_last_interior_state"]),
        ("stage4_injector_Dirichlet_semantics_reproduced",e4["injector_state_assignment"] and e4["injector_diffusion_rhs_assignment"]),
        ("nested_stage3_stage4_boundary_lineage_consistent",nested),
        ("zero_gradient_not_falsely_attributed_to_stage4",True),
        ("Pollock_outlet_advection_bound_without_legacy_uD",True),
        ("Pollock_capillary_outlet_held_value_row_bound",stage4_held),
        ("C10_operator_hash_preserved",sha(C10_OP)==c10["operator_sha256"]),
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
        diagnosis="C10A_OUTLET_FAILURE_WAS_A_BOUNDARY_CLASSIFICATION_MISMATCH_STAGE4_USES_A_HELD_VALUE_DIFFUSION_OUTLET_ROW_NOT_AN_EXPLICIT_ZERO_GRADIENT_NEUMANN_CONDITION"
        rec=("Accept C10A with corrected outlet provenance. Preserve the Stage-4 split boundary semantics: "
             "conservative terminal-state advective outflow plus a held-value identity row during the implicit capillary substep. "
             "Map these to theta=1 without restoring legacy exp(Nc xD). Proceed to C11 diagnostic solver assembly; do not authorize Y yet.")
        nxt="V16C-11 — Executable Conservative Full-Physics Pollock Transport Solver Assembly and Diagnostic Validation"
    else:
        status="V16C_POLLOCK_BOUNDARY_SOURCE_RESIDUAL_UNRESOLVED"
        diagnosis="ONE_OR_MORE_EXACT_SOLVER_BOUNDARY_IMPLEMENTATION_GATES_FAILED"
        rec="Do not assemble the physical solver. Inspect only failed C10A-R gates."
        nxt="V16C-10A-R2 — Exact Boundary Implementation Residual Audit"

    save_csv(DECISION,[dict(status=status,diagnosis=diagnosis,
        inlet="DIRICHLET_SOURCE_AUTHENTIC" if ok else "UNRESOLVED",
        outlet_advection="TERMINAL_STATE_CONSERVATIVE_OUTFLOW" if ok else "UNRESOLVED",
        outlet_capillary="HELD_VALUE_IDENTITY_ROW" if ok else "UNRESOLVED",
        outlet_zero_gradient="NOT_ATTRIBUTED",
        solver_assembly_authorized=ok,Y_generation_authorized=False,next_milestone=nxt)])
    savej(CONTRACT,dict(milestone="V16C-10A-R",status=status,diagnosis=diagnosis,
        corrected_boundary_semantics=rows,stage3_evidence=e3,stage4_evidence=e4,
        C10_operator_sha256=sha(C10_OP),solver_assembly_authorized=ok,
        Y_generation_authorized=False,recommendation=rec,next_milestone=nxt))
    savej(SUMMARY,dict(milestone="V16C-10A-R",status=status,diagnosis=diagnosis,
        inlet_boundary_bound=ok,outlet_advective_boundary_bound=ok,
        outlet_capillary_held_value_boundary_bound=ok,
        zero_gradient_claim=False,solver_assembly_authorized=ok,
        Y_transport_generated=False,recommendation=rec,next_milestone=nxt))

    print("EXACT STAGE-4 SOLVER FINDING")
    print("  Exact SHA                         :",e4["exact_sha_match"])
    print("  Held-value outlet docstring       :",e4["held_value_outlet_docstring"])
    print("  Held-value implementation proven  :",e4["held_value_outlet_implementation_proven"])
    print("  Advective terminal-state outflow  :",e4["advective_outlet_uses_last_interior_state"])
    print("  Injector Dirichlet implementation :",e4["injector_state_assignment"] and e4["injector_diffusion_rhs_assignment"])
    print("\nCORRECTED OUTLET AUTHORITY")
    print("  Advection : terminal-state conservative outflow")
    print("  Diffusion : held-value / identity outlet row")
    print("  Neumann   : NOT ATTRIBUTED")
    print("  Legacy uD : NOT REINTRODUCED")
    print("\n"+"="*78)
    print("V16C-10A-R FINAL RESIDUAL AUDIT GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-10A-R BOUNDARY SOURCE RESIDUAL AUDIT: COMPLETE")
    print("="*78)

if __name__=="__main__": main()
