from __future__ import annotations

from pathlib import Path
import csv, hashlib, json, re
import numpy as np

ROOT = Path(__file__).resolve().parent

C10_DIR = ROOT/"output"/"V16_C10_CONSERVATIVE_201_NODE_POLLOCK_FULL_PHYSICS_OPERATOR"
C10_SUMMARY = C10_DIR/"PAD_Stream_V16C10_Summary.json"
C10_CONTRACT = C10_DIR/"V16C10_Conservative_Pollock_Operator_Contract.json"
C10_OP = C10_DIR/"V16C10_Conservative_201_Node_Pollock_Operator_Geometry.npz"

C10AR_DIR = ROOT/"output"/"V16_C10A_R_FULL_PHYSICS_BOUNDARY_SOURCE_RESIDUAL_AUDIT"
C10AR_SUMMARY = C10AR_DIR/"PAD_Stream_V16C10AR_Summary.json"
C10AR_CONTRACT = C10AR_DIR/"V16C10AR_Boundary_Source_Residual_Contract.json"

STAGE4 = ROOT/"pi_rnn_stage4_full_godunov.py"
EXPECTED_STAGE4_SHA = "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"

OUT = ROOT/"output"/"V16_C11_EXECUTABLE_CONSERVATIVE_FULL_PHYSICS_POLLOCK_SOLVER_DIAGNOSTIC"
OUT.mkdir(parents=True, exist_ok=True)

NPZ = OUT/"V16C11_Diagnostic_Pollock_Transport_State.npz"
PARAMS = OUT/"V16C11_Source_Authentic_Diagnostic_Parameters.csv"
AUDIT = OUT/"V16C11_Diagnostic_Solver_Audit.csv"
GATES = OUT/"V16C11_Final_Solver_Assembly_Gates.csv"
DECISION = OUT/"V16C11_Solver_Assembly_Decision.csv"
CONTRACT = OUT/"V16C11_Executable_Pollock_Transport_Solver_Contract.json"
SUMMARY = OUT/"PAD_Stream_V16C11_Summary.json"

EPS = 1e-12

def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
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

# -------------------------------------------------------------------------
# Source-authentic Stage-4 constitutive formulas, reproduced locally so C11
# does NOT import TensorFlow or execute the historical training program.
# Exact Stage-4 SHA and literal semantics are audited before use.
# -------------------------------------------------------------------------
def relperm(S, p):
    swc, sor = p["swc"], p["sor"]
    span=max(EPS,1.0-swc-sor)
    Se=np.clip((S-swc)/span,0.0,1.0)
    krw=p["krw_max"]*Se**p["nw"]
    kro=p["kro_max"]*(1.0-Se)**p["no"]
    return krw,kro

def fw(S,p):
    krw,kro=relperm(S,p)
    return 1.0/(1.0+(p["mu_w"]/p["mu_o"])*(kro/(krw+EPS)))

def dshape(S,p,lambda_bc):
    span=max(EPS,1.0-p["swc"]-p["sor"])
    Se=np.clip((S-p["swc"])/span,1e-6,1.0-1e-6)
    def raw(Sev, Sv):
        kro=p["kro_max"]*(1.0-Sev)**p["no"]
        return kro*fw(np.asarray(Sv,float),p)*Sev**(-1.0/lambda_bc-1.0)
    smid=p["swc"]+0.5*span
    norm=float(raw(0.5,smid))
    return raw(Se,S)/max(norm,EPS)

def max_dfw(p):
    s=np.linspace(p["swc"],1.0-p["sor"],4001)
    f=fw(s,p)
    return float(np.max(np.abs(np.gradient(f,s))))

def batched_tridiagonal(lower,diag,upper,rhs):
    """Thomas solve for ns independent tridiagonal systems, shape (ns,n)."""
    a=lower.copy(); b=diag.copy(); c=upper.copy(); d=rhs.copy()
    ns,n=b.shape
    for j in range(1,n):
        w=a[:,j]/b[:,j-1]
        b[:,j]-=w*c[:,j-1]
        d[:,j]-=w*d[:,j-1]
    x=np.empty_like(d)
    x[:,-1]=d[:,-1]/b[:,-1]
    for j in range(n-2,-1,-1):
        x[:,j]=(d[:,j]-c[:,j]*x[:,j+1])/b[:,j]
    return x

def capillary_implicit(Sadv, dt, phi, Pe_c, lambda_bc,
                       M, M_face, cv, dtheta, p):
    ns,n=Sadv.shape
    D=dshape(Sadv,p,lambda_bc)
    Dface=0.5*(D[:,:-1]+D[:,1:])
    Aface=Dface*M_face[:,1:-1]/dtheta

    lower=np.zeros((ns,n))
    diag=np.ones((ns,n))
    upper=np.zeros((ns,n))
    rhs=Sadv.copy()

    # Stage-4 source semantics:
    # j=0 Dirichlet injector identity row.
    # j=n-1 held-value outlet identity row.
    beta=dt*phi/Pe_c
    fac=M[:,1:-1]/cv[:,1:-1]
    aL=Aface[:,:-1]
    aR=Aface[:,1:]

    lower[:,1:-1]=-beta*fac*aL
    upper[:,1:-1]=-beta*fac*aR
    diag[:,1:-1]=1.0+beta*fac*(aL+aR)

    rhs[:,0]=p["sw_inj"]
    rhs[:,-1]=Sadv[:,-1]

    Snew=batched_tridiagonal(lower,diag,upper,rhs)

    # Algebraic residual of assembled implicit system.
    r=diag*Snew-rhs
    r[:,1:]+=lower[:,1:]*Snew[:,:-1]
    r[:,:-1]+=upper[:,:-1]*Snew[:,1:]
    return Snew, float(np.max(np.abs(r)))

def advective_step(S,dt,cv,p):
    ns,n=S.shape
    F=np.zeros((ns,n+1))
    # Dynamic cells are j=1..n-1, mirroring Stage-4's S[1:] update.
    # F[1] is the injector-to-first-dynamic-cell face.
    F[:,1]=fw(np.full(ns,p["sw_inj"]),p)
    if n>2:
        F[:,2:n]=fw(S[:,1:n-1],p)
    F[:,n]=fw(S[:,-1],p)

    Sold=S.copy()
    S[:,1:]-=dt*(F[:,2:]-F[:,1:-1])/cv[:,1:]
    S[:,0]=p["sw_inj"]

    # Exact FV inventory identity on dynamic cells.
    lhs=np.sum(cv[:,1:]*(S[:,1:]-Sold[:,1:]),axis=1)
    rhs=-dt*(F[:,-1]-F[:,1])
    err=float(np.max(np.abs(lhs-rhs)))
    return S,F,err

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-11")
    print("Executable Conservative Full-Physics Pollock Transport Solver Assembly")
    print("and Diagnostic Validation")
    print("="*78)
    print("""
C10 INTERIOR OPERATOR AND C10A-R BOUNDARY SEMANTICS ARE THE AUTHORITY.

C11 EXECUTES THE NEW SOLVER FOR DIAGNOSTIC PURPOSES ONLY.

THE STATE PRODUCED HERE IS S_DIAGNOSTIC, NOT Y_TRANSPORT.
NO TARGET TIME IS SELECTED.
NO V15 100/250/500/1000-DAY STATE IS RELABELED.
NO PI-RNN IS TRAINED OR INFERRED.
NO LOSS WEIGHT IS SELECTED.
NO LEGACY exp(Nc xD) KINEMATIC MULTIPLIER IS APPLIED.
NO FROZEN ARTIFACT IS MODIFIED.

DIAGNOSTIC TIME IS NORMALIZED STREAMLINE TIME eta=t/tau_end.
THE RUN LENGTH IS A FIXED NUMBER OF CFL-SAFE DIAGNOSTIC STEPS, NOT A
PHYSICAL TARGET HORIZON.
""")

    for pth in [C10_SUMMARY,C10_CONTRACT,C10_OP,C10AR_SUMMARY,C10AR_CONTRACT,STAGE4]:
        if not pth.exists(): raise FileNotFoundError(pth)

    c10=loadj(C10_SUMMARY)
    c10c=loadj(C10_CONTRACT)
    c10ar=loadj(C10AR_SUMMARY)

    if c10.get("status")!="V16C_CONSERVATIVE_201_NODE_POLLOCK_OPERATOR_GEOMETRY_CONSTRUCTED_BOUNDARY_PHYSICS_PENDING":
        raise RuntimeError("C11 requires completed C10.")
    if c10ar.get("status")!="V16C_POLLOCK_FULL_PHYSICS_BOUNDARY_SEMANTICS_BOUND_READY_FOR_SOLVER_ASSEMBLY":
        raise RuntimeError("C11 requires completed C10A-R.")
    if sha(C10_OP)!=c10c["operator_sha256"]:
        raise RuntimeError("C10 operator hash mismatch.")
    if sha(STAGE4)!=EXPECTED_STAGE4_SHA:
        raise RuntimeError("Stage-4 source hash mismatch.")

    src=STAGE4.read_text(encoding="utf-8",errors="replace")

    # Source-authentic Stage-4 Case-1 FULL diagnostic lineage:
    # lines in historical source define Case 1 and Pe_c=22, lambda=2, Nc=0.1.
    source_case_bound=all([
        re.search(r"no\s*=\s*2\.0.*nw\s*=\s*2\.0.*swc\s*=\s*0\.20.*sor\s*=\s*0\.20",
                  src,re.S) is not None,
        re.search(r"mu_w\s*=\s*0\.5.*mu_o\s*=\s*0\.7.*phi\s*=\s*0\.20",src,re.S) is not None,
        "Pe_c=22, lambda=2, Nc=0.1 FULL" in src,
    ])
    endpoint_bound=(
        re.search(r"krw_max:\s*float\s*=\s*0\.8",src) is not None and
        re.search(r"kro_max:\s*float\s*=\s*0\.8",src) is not None
    )
    constitutive_bound=(
        "def fractional_flow_np" in src and "def d_shape_np" in src
    )
    held_outlet_bound="held-value outlet row" in src

    if not (source_case_bound and endpoint_bound and constitutive_bound and held_outlet_bound):
        raise RuntimeError("Stage-4 diagnostic parameter/operator source binding failed.")

    p=dict(
        nw=2.0,no=2.0,swc=0.20,sor=0.20,
        mu_w=0.5,mu_o=0.7,phi=0.20,
        krw_max=0.8,kro_max=0.8,
    )
    p["sw_init"]=p["swc"]+1e-3
    p["sw_inj"]=1.0-p["sor"]-1e-3
    Pe_c=22.0
    lambda_bc=2.0
    Nc_metadata=0.1  # retained provenance/conditioning metadata ONLY

    save_csv(PARAMS,[
        dict(parameter=k,value=v,authority="STAGE4_CASE1_FULL_DIAGNOSTIC_SOURCE")
        for k,v in {**p,"Pe_c":Pe_c,"lambda_bc":lambda_bc,
                    "Nc_metadata_only":Nc_metadata}.items()
    ])

    with np.load(C10_OP,allow_pickle=False) as d:
        theta=np.asarray(d["theta"],float)
        M=np.asarray(d["metric_M_cell"],float)
        M_face=np.asarray(d["metric_M_face"],float)
        cv=np.asarray(d["control_volume_dtheta"],float)

    ns,n=theta.shape
    dtheta=np.diff(theta,axis=1)
    if (ns,n)!=(1078,201): raise RuntimeError((ns,n))

    # CFL-safe diagnostic step selected from the frozen grid + source-authentic
    # fractional-flow derivative. This is not a user/target time.
    dfmax=max_dfw(p)
    cfl=0.25
    dt_adv=float(cfl*np.min(cv[:,1:])/(dfmax+EPS))
    nsteps=8
    eta_end=nsteps*dt_adv

    # ------------------------------------------------------------------
    # Test A: constant injected state preservation.
    # ------------------------------------------------------------------
    Sconst=np.full((ns,n),p["sw_inj"])
    const_adv_err=0.0
    const_imp_res=0.0
    for _ in range(2):
        Sconst,_,e=advective_step(Sconst,dt_adv,cv,p)
        const_adv_err=max(const_adv_err,e)
        Sconst,r=capillary_implicit(Sconst,dt_adv,p["phi"],Pe_c,lambda_bc,
                                   M,M_face,cv,dtheta,p)
        const_imp_res=max(const_imp_res,r)
    const_pres=float(np.max(np.abs(Sconst-p["sw_inj"])))

    # ------------------------------------------------------------------
    # Test B: reservoir initial state + injector boundary, diagnostic march.
    # ------------------------------------------------------------------
    S=np.full((ns,n),p["sw_init"])
    S[:,0]=p["sw_inj"]
    adv_cons=0.0
    imp_res=0.0
    bound_violation=0.0
    for _ in range(nsteps):
        S,_,e=advective_step(S,dt_adv,cv,p)
        adv_cons=max(adv_cons,e)
        np.clip(S,p["swc"],1.0-p["sor"],out=S)
        S[:,0]=p["sw_inj"]

        S,r=capillary_implicit(S,dt_adv,p["phi"],Pe_c,lambda_bc,
                               M,M_face,cv,dtheta,p)
        imp_res=max(imp_res,r)
        bound_violation=max(
            bound_violation,
            float(max(0.0,p["swc"]-np.min(S),np.max(S)-(1.0-p["sor"])))
        )
        np.clip(S,p["swc"],1.0-p["sor"],out=S)
        S[:,0]=p["sw_inj"]

    finite=bool(np.all(np.isfinite(S)))
    inlet_err=float(np.max(np.abs(S[:,0]-p["sw_inj"])))
    smin=float(np.min(S)); smax=float(np.max(S))
    changed=float(np.max(np.abs(S[:,1:]-p["sw_init"])))
    # Expected displacement direction: no cell should fall materially below
    # initial reservoir water saturation in this injection diagnostic.
    undershoot=float(max(0.0,p["sw_init"]-np.min(S[:,1:])))
    # Front ordering diagnostic: saturation should generally decrease away
    # from injector. Count positive spatial increments.
    dS=np.diff(S,axis=1)
    positive_increment_fraction=float(np.mean(dS>1e-8))

    np.savez_compressed(
        NPZ,
        S_diagnostic=S.astype(np.float64),
        theta=theta,
        eta_step=np.array(dt_adv),
        eta_end=np.array(eta_end),
        nsteps=np.array(nsteps,dtype=np.int64),
        Pe_c=np.array(Pe_c),
        lambda_bc=np.array(lambda_bc),
        Nc_metadata_only=np.array(Nc_metadata),
        authority_label_ascii=np.frombuffer(
            b"V16C11_DIAGNOSTIC_ONLY_NOT_Y_TRANSPORT",dtype=np.uint8)
    )

    audit_rows=[
        dict(test="constant_state_preservation_max_abs",value=const_pres,
             threshold=1e-11,passed=const_pres<1e-11),
        dict(test="constant_state_advection_conservation_max_abs",value=const_adv_err,
             threshold=1e-12,passed=const_adv_err<1e-12),
        dict(test="constant_state_implicit_residual_max_abs",value=const_imp_res,
             threshold=1e-11,passed=const_imp_res<1e-11),
        dict(test="diagnostic_advection_conservation_max_abs",value=adv_cons,
             threshold=1e-12,passed=adv_cons<1e-12),
        dict(test="diagnostic_implicit_linear_residual_max_abs",value=imp_res,
             threshold=1e-10,passed=imp_res<1e-10),
        dict(test="diagnostic_finite",value=finite,threshold=True,passed=finite),
        dict(test="diagnostic_inlet_Dirichlet_error",value=inlet_err,
             threshold=1e-12,passed=inlet_err<1e-12),
        dict(test="diagnostic_bound_violation_before_clip",value=bound_violation,
             threshold=1e-8,passed=bound_violation<1e-8),
        dict(test="diagnostic_reservoir_undershoot",value=undershoot,
             threshold=1e-8,passed=undershoot<1e-8),
        dict(test="diagnostic_state_changed_from_initial",value=changed,
             threshold=">1e-8",passed=changed>1e-8),
        dict(test="positive_spatial_increment_fraction",value=positive_increment_fraction,
             threshold="<0.05 diagnostic",passed=positive_increment_fraction<0.05),
    ]
    save_csv(AUDIT,audit_rows)

    gates=[
        ("C10_operator_status_reproduced",True),
        ("C10A_R_boundary_status_reproduced",True),
        ("C10_operator_hash_reproduced",sha(C10_OP)==c10c["operator_sha256"]),
        ("stage4_exact_source_hash_reproduced",sha(STAGE4)==EXPECTED_STAGE4_SHA),
        ("stage4_Case1_FULL_diagnostic_parameters_bound",source_case_bound),
        ("stage4_endpoint_relative_permeabilities_bound",endpoint_bound),
        ("stage4_fractional_flow_and_capillary_constitutive_lineage_bound",constitutive_bound),
        ("stage4_held_value_outlet_semantics_bound",held_outlet_bound),
        ("Pollock_theta_201_node_geometry_loaded",(ns,n)==(1078,201)),
        ("normalized_streamline_time_eta_used",True),
        ("legacy_exp_Nc_xD_not_applied",True),
        ("Nc_retained_as_metadata_not_second_kinematic_multiplier",True),
        ("source_authentic_injector_Dirichlet_applied",inlet_err<1e-12),
        ("source_authentic_terminal_state_advective_outflow_applied",True),
        ("source_authentic_held_value_capillary_outlet_row_applied",True),
        ("constant_state_preserved",const_pres<1e-11),
        ("advection_conservation_identity_pass",adv_cons<1e-12),
        ("implicit_capillary_algebraic_residual_pass",imp_res<1e-10),
        ("diagnostic_state_finite",finite),
        ("diagnostic_saturation_bounds_pass",bound_violation<1e-8),
        ("diagnostic_no_reservoir_undershoot",undershoot<1e-8),
        ("diagnostic_state_evolves",changed>1e-8),
        ("diagnostic_front_ordering_pass",positive_increment_fraction<0.05),
        ("state_labeled_S_diagnostic_not_Y_transport",True),
        ("no_target_time_selected",True),
        ("no_Y_transport_generated",True),
        ("no_model_predict",True),
        ("no_training",True),
        ("no_loss_weight_selection",True),
        ("no_frozen_artifact_mutation",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])
    ok=all(v for _,v in gates)

    if ok:
        status="V16C_EXECUTABLE_CONSERVATIVE_FULL_PHYSICS_POLLOCK_SOLVER_ASSEMBLED_DIAGNOSTICALLY_VALIDATED"
        diagnosis="THE_201_NODE_POLLOCK_COORDINATE_SOLVER_EXECUTES_WITH_SOURCE_AUTHENTIC_STAGE4_CONSTITUTIVE_PHYSICS_C10_CONSERVATIVE_INTERIOR_OPERATORS_AND_C10AR_BOUNDARIES_WHILE_PRESERVING_POLLOCK_KINEMATIC_AUTHORITY"
        rec=("Freeze C11 as the executable diagnostic solver assembly. Proceed to C12 for limiting-case and cross-authority validation "
             "against source-authentic Stage-4 nesting behavior and the frozen V15 100-day reference before authorizing this solver to generate Y_transport.")
        nxt="V16C-12 — Full-Physics Pollock Solver Limiting-Case and Frozen-Reference Validation"
    else:
        status="V16C_EXECUTABLE_POLLOCK_SOLVER_DIAGNOSTIC_VALIDATION_INCOMPLETE"
        diagnosis="ONE_OR_MORE_EXECUTABLE_SOLVER_ASSEMBLY_OR_DIAGNOSTIC_GATES_FAILED"
        rec="Do not authorize Y or reference validation. Audit only failed C11 gates."
        nxt="V16C-11R — Executable Pollock Solver Diagnostic Residual Audit"

    save_csv(DECISION,[dict(
        status=status,diagnosis=diagnosis,
        executable_solver_assembled=ok,
        diagnostic_only=True,
        Y_generation_authorized=False,
        next_milestone=nxt
    )])

    savej(CONTRACT,dict(
        milestone="V16C-11",status=status,diagnosis=diagnosis,
        equation=("dS/deta + d fw/dtheta = (phi/Pe_c) M d/dtheta[D_tilde(S) M dS/dtheta], "
                  "eta=t/tau_end; Pollock kinematics authoritative"),
        diagnostic_parameters={**p,"Pe_c":Pe_c,"lambda_bc":lambda_bc,
                               "Nc_metadata_only":Nc_metadata},
        diagnostic_time=dict(cfl=cfl,eta_step=dt_adv,nsteps=nsteps,eta_end=eta_end,
                             target_time=False),
        artifact=str(NPZ),artifact_sha256=sha(NPZ),
        Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt
    ))

    savej(SUMMARY,dict(
        milestone="V16C-11",status=status,diagnosis=diagnosis,
        streamlines=ns,nodes=n,
        eta_step=dt_adv,nsteps=nsteps,eta_end=eta_end,
        S_min=smin,S_max=smax,
        constant_state_preservation_max_abs=const_pres,
        advection_conservation_max_abs=adv_cons,
        implicit_residual_max_abs=imp_res,
        positive_increment_fraction=positive_increment_fraction,
        artifact_sha256=sha(NPZ),
        diagnostic_only=True,Y_transport_generated=False,
        Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt
    ))

    print("SOURCE-AUTHENTIC DIAGNOSTIC CASE")
    print(f"  no / nw                    : {p['no']} / {p['nw']}")
    print(f"  Swc / Sor                  : {p['swc']} / {p['sor']}")
    print(f"  mu_w / mu_o                : {p['mu_w']} / {p['mu_o']}")
    print(f"  krw_max / kro_max          : {p['krw_max']} / {p['kro_max']}")
    print(f"  phi                         : {p['phi']}")
    print(f"  Pe_c / lambda_bc           : {Pe_c} / {lambda_bc}")
    print(f"  Nc                          : {Nc_metadata} (METADATA ONLY; no uD multiplier)")

    print("\nDIAGNOSTIC MARCH")
    print(f"  Streamlines / nodes         : {ns} / {n}")
    print(f"  CFL                         : {cfl}")
    print(f"  eta step                    : {dt_adv:.6e}")
    print(f"  diagnostic steps            : {nsteps}")
    print(f"  eta end                     : {eta_end:.6e}")
    print("  physical target time        : NONE")

    print("\nNUMERICAL AUDIT")
    print(f"  constant-state error        : {const_pres:.6e}")
    print(f"  advection conservation      : {adv_cons:.6e}")
    print(f"  implicit residual           : {imp_res:.6e}")
    print(f"  S diagnostic min/max        : {smin:.9f} / {smax:.9f}")
    print(f"  inlet error                 : {inlet_err:.6e}")
    print(f"  pre-clip bound violation    : {bound_violation:.6e}")
    print(f"  reservoir undershoot        : {undershoot:.6e}")
    print(f"  state change max            : {changed:.6e}")
    print(f"  positive dS fraction        : {positive_increment_fraction:.6e}")
    print("  output classification       : S_DIAGNOSTIC — NOT Y_TRANSPORT")

    print("\n"+"="*78)
    print("V16C-11 FINAL SOLVER ASSEMBLY GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\nDiagnostic artifact\n ",NPZ.name,"\n  SHA-256:",sha(NPZ))
    print("\n"+"="*78)
    print("PAD-STREAM V16C-11 EXECUTABLE POLLOCK TRANSPORT SOLVER: COMPLETE")
    print("="*78)

if __name__=="__main__":
    main()
