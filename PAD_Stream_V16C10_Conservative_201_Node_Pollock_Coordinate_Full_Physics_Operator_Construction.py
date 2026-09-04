from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import numpy as np

ROOT = Path(__file__).resolve().parent

C9_DIR = ROOT/"output"/"V16_C9_SOURCE_AUTHENTIC_FULL_BL_CCUS_TARGET_GENERATOR_BINDING_AUDIT"
C9_SUMMARY = C9_DIR/"PAD_Stream_V16C9_Summary.json"
C9_CONTRACT = C9_DIR/"V16C9_Source_Authentic_Target_Generator_Binding_Contract.json"

C7_DIR = ROOT/"output"/"V16_C7_POLLOCK_TOF_FULL_BL_CCUS_ADAPTER_PHYSICS_CONTRACT"
C7_CONTRACT = C7_DIR/"V16C7_Pollock_TOF_Full_BL_CCUS_Adapter_Physics_Contract.json"
C7_METRIC = C7_DIR/"V16C7_Pollock_TOF_Streamline_Metric_Contract.npz"

OUT = ROOT/"output"/"V16_C10_CONSERVATIVE_201_NODE_POLLOCK_FULL_PHYSICS_OPERATOR"
OUT.mkdir(parents=True, exist_ok=True)

OP_NPZ = OUT/"V16C10_Conservative_201_Node_Pollock_Operator_Geometry.npz"
ADV_CSV = OUT/"V16C10_Advection_Operator_Contract.csv"
CAP_CSV = OUT/"V16C10_Capillary_Operator_Contract.csv"
BC_CSV = OUT/"V16C10_Boundary_Operator_Contract.csv"
AUDIT_CSV = OUT/"V16C10_Algebraic_Conservation_Audit.csv"
GATES_CSV = OUT/"V16C10_Final_Operator_Construction_Gates.csv"
DECISION_CSV = OUT/"V16C10_Operator_Construction_Decision.csv"
CONTRACT_JSON = OUT/"V16C10_Conservative_Pollock_Operator_Contract.json"
SUMMARY_JSON = OUT/"PAD_Stream_V16C10_Summary.json"

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

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-10")
    print("Conservative 201-Node Pollock-Coordinate Full-Physics Operator Construction")
    print("="*78)
    print("""
C9 GENERATOR BINDING IS FROZEN.

THIS MILESTONE CONSTRUCTS ONLY THE DISCRETE OPERATOR GEOMETRY/ALGEBRA.
NO PHYSICAL-TIME TRANSPORT MARCH IS EXECUTED.
NO Y_TRANSPORT OR SATURATION TARGET IS GENERATED.
NO PI-RNN IS TRAINED OR INFERRED.
NO TARGET TIMES ARE SELECTED.
NO FITTED ADAPTER PARAMETER IS INTRODUCED.
NO LEGACY exp(Nc xD) KINEMATIC MULTIPLIER IS APPLIED.
NO FROZEN V15/V16 ARTIFACT IS MODIFIED.

THE PURPOSE IS TO VERIFY THAT THE 201-NODE POLLOCK OPERATOR CAN BE WRITTEN
IN CONSERVATIVE FACE-DIVERGENCE FORM BEFORE ANY SOURCE-AUTHENTIC TARGET RUN.
""")

    for p in [C9_SUMMARY,C9_CONTRACT,C7_CONTRACT,C7_METRIC]:
        if not p.exists(): raise FileNotFoundError(p)

    c9=loadj(C9_SUMMARY)
    if c9.get("status")!="V16C_SOURCE_AUTHENTIC_TARGET_GENERATOR_LINEAGE_BOUND_NEW_POLLOCK_ADAPTER_SOLVER_REQUIRED":
        raise RuntimeError("C10 requires completed C9.")

    c7=loadj(C7_CONTRACT)
    if sha(C7_METRIC)!=c7["metric_artifact"]["sha256"]:
        raise RuntimeError("C7 metric hash mismatch.")

    with np.load(C7_METRIC,allow_pickle=False) as d:
        xD=np.asarray(d["xD_arc"],dtype=np.float64)
        theta=np.asarray(d["pollock_theta"],dtype=np.float64)
        M=np.asarray(d["metric_M_dtheta_dxD"],dtype=np.float64)
        L=np.asarray(d["streamline_terminal_length_m"],dtype=np.float64)

    ns,nn=theta.shape
    if (ns,nn)!=(1078,201): raise RuntimeError(f"Unexpected shape {(ns,nn)}")

    dtheta=np.diff(theta,axis=1)
    dxD=np.diff(xD,axis=1)
    if np.any(dtheta<=0) or np.any(dxD<=0):
        raise RuntimeError("Nonpositive Pollock coordinate spacing.")

    # Finite-volume control-volume widths in theta.
    theta_face=np.empty((ns,nn+1),dtype=np.float64)
    theta_face[:,1:-1]=0.5*(theta[:,:-1]+theta[:,1:])
    theta_face[:,0]=theta[:,0]
    theta_face[:,-1]=theta[:,-1]
    cv_dtheta=np.diff(theta_face,axis=1)

    # Face metric M. Harmonic averaging preserves positivity and is appropriate
    # for a face transport coefficient. No calibration/fitting is involved.
    M_face=np.empty((ns,nn+1),dtype=np.float64)
    M_face[:,0]=M[:,0]
    M_face[:,-1]=M[:,-1]
    M_face[:,1:-1]=2.0*M[:,:-1]*M[:,1:]/(M[:,:-1]+M[:,1:])

    # ---------------------------------------------------------------------
    # Conservative operator contracts.
    #
    # Advection in Pollock residence-time coordinates:
    #   dS/dt + dF_adv/dtheta = 0
    # with Pollock kinematics authoritative. The nonlinear F_adv(S) comes
    # from Stage-4 fractional-flow physics in the later solver.
    #
    # Capillary:
    #   M d/dtheta [ D(S) M dS/dtheta ]
    #
    # We construct the geometric linear skeleton for D=1:
    #   G_face = M_face * (S_R-S_L)/dtheta_center
    #   Lcap   = M_cell/cv_dtheta * (G_R-G_L)
    #
    # This verifies telescoping conservative face fluxes. D(S) is deliberately
    # NOT evaluated because that would require a saturation field.
    # ---------------------------------------------------------------------

    # Build a deterministic non-physical test vector solely for algebraic audit.
    # It is not a saturation solution or target.
    q=np.linspace(0.0,1.0,nn,dtype=np.float64)[None,:]
    q=np.repeat(q,ns,axis=0)

    # Interior unit-diffusivity capillary face gradient skeleton.
    G=np.zeros((ns,nn+1),dtype=np.float64)
    G[:,1:-1]=M_face[:,1:-1]*np.diff(q,axis=1)/dtheta

    # Homogeneous no-capillary-flux boundaries for the algebraic telescoping
    # audit only. Physical injection saturation BC is deferred to solver BC
    # construction because no transport solve occurs in C10.
    G[:,0]=0.0
    G[:,-1]=0.0

    Lcap=M/cv_dtheta*(G[:,1:]-G[:,:-1])

    # Weighted divergence must telescope exactly to boundary flux difference:
    # sum (cv/M)*Lcap = G_out-G_in = 0.
    cap_balance=np.sum((cv_dtheta/M)*Lcap,axis=1)
    cap_telescoping_max=float(np.max(np.abs(cap_balance)))

    # Generic conservative advection divergence audit using arbitrary face flux.
    # This is algebraic only; no fw(S) is evaluated.
    F=np.zeros((ns,nn+1),dtype=np.float64)
    # deterministic interior face field; boundary faces fixed to zero
    F[:,1:-1]=np.linspace(0.0,1.0,nn-1,dtype=np.float64)[None,:]
    divF=(F[:,1:]-F[:,:-1])/cv_dtheta
    adv_balance=np.sum(cv_dtheta*divF,axis=1)-(F[:,-1]-F[:,0])
    adv_telescoping_max=float(np.max(np.abs(adv_balance)))

    finite=all(np.all(np.isfinite(a)) for a in [xD,theta,M,theta_face,cv_dtheta,M_face,Lcap])
    positive=bool(np.all(M>0) and np.all(M_face>0) and np.all(cv_dtheta>0))

    np.savez_compressed(
        OP_NPZ,
        theta=theta,
        xD_arc=xD,
        metric_M_cell=M,
        metric_M_face=M_face,
        theta_face=theta_face,
        control_volume_dtheta=cv_dtheta,
        streamline_terminal_length_m=L,
        authority_label_ascii=np.frombuffer(
            b"PAD_STREAM_V16C10_CONSERVATIVE_POLLOCK_OPERATOR_GEOMETRY",dtype=np.uint8)
    )

    save_csv(ADV_CSV,[
        dict(item="coordinate",definition="theta=tau_Pollock/tau_end",authority="C7/C8"),
        dict(item="kinematics",definition="Pollock TOF",authority="C7A/C7A-R"),
        dict(item="face_flux",definition="F_adv from Stage-4 fractional-flow constitutive physics in future solver",authority="C9"),
        dict(item="cell_divergence",definition="(F_{j+1/2}-F_{j-1/2})/Delta_theta_j",authority="C10"),
        dict(item="legacy_uD",definition="exp(Nc xD)",authority="NOT_APPLIED_AS_SECOND_KINEMATIC_MULTIPLIER"),
    ])

    save_csv(CAP_CSV,[
        dict(item="continuous_operator",definition="M d/dtheta[D_tilde(S) M dS/dtheta]",authority="C7/C7R"),
        dict(item="face_metric",definition="harmonic average of positive cell M",authority="C10_DETERMINISTIC_DISCRETIZATION"),
        dict(item="face_gradient",definition="M_face*(S_R-S_L)/Delta_theta_center",authority="C10"),
        dict(item="nonlinear_diffusivity",definition="D_tilde(S) from Stage-4 source-authentic physics",authority="C9_FUTURE_SOLVER_REUSE"),
        dict(item="cell_divergence",definition="M_cell/Delta_theta_CV*(G_R-G_L)",authority="C10"),
    ])

    save_csv(BC_CSV,[
        dict(boundary="inlet",advection="future source-authentic injection saturation flux/BC",
             capillary="must be explicitly derived before physical solve",C10_action="NO_PHYSICAL_BC_APPLIED"),
        dict(boundary="outlet",advection="future conservative outflow treatment",
             capillary="must be explicitly derived before physical solve",C10_action="NO_PHYSICAL_BC_APPLIED"),
        dict(boundary="algebraic_audit_only",advection="zero boundary test flux",
             capillary="zero boundary test flux",C10_action="TELESCOPING_TEST_ONLY"),
    ])

    audit=[
        dict(test="shape",value=f"{ns}x{nn}",passed=(ns,nn)==(1078,201)),
        dict(test="all_operator_geometry_finite",value=finite,passed=finite),
        dict(test="all_metric_and_cv_widths_positive",value=positive,passed=positive),
        dict(test="advection_face_divergence_telescoping_max_abs",value=adv_telescoping_max,passed=adv_telescoping_max<1e-12),
        dict(test="capillary_transformed_flux_telescoping_max_abs",value=cap_telescoping_max,passed=cap_telescoping_max<1e-12),
        dict(test="legacy_uD_multiplier_present",value=False,passed=True),
        dict(test="physical_saturation_used_in_audit",value=False,passed=True),
    ]
    save_csv(AUDIT_CSV,audit)

    gates=[
        ("C9_generator_binding_status_reproduced",True),
        ("C7_metric_hash_reproduced",sha(C7_METRIC)==c7["metric_artifact"]["sha256"]),
        ("201_node_Pollock_sequence_reproduced",(ns,nn)==(1078,201)),
        ("theta_spacing_positive",bool(np.all(dtheta>0))),
        ("xD_arc_spacing_positive",bool(np.all(dxD>0))),
        ("cell_metric_M_positive",bool(np.all(M>0))),
        ("face_metric_M_positive",bool(np.all(M_face>0))),
        ("control_volume_width_positive",bool(np.all(cv_dtheta>0))),
        ("operator_geometry_finite",finite),
        ("conservative_advection_face_divergence_constructed",True),
        ("transformed_capillary_face_divergence_constructed",True),
        ("advection_telescoping_identity_pass",adv_telescoping_max<1e-12),
        ("capillary_telescoping_identity_pass",cap_telescoping_max<1e-12),
        ("legacy_exp_Nc_xD_not_applied",True),
        ("no_fitted_adapter_parameter",True),
        ("no_physical_boundary_condition_silently_assumed",True),
        ("no_transport_time_march",True),
        ("no_Y_transport_generated",True),
        ("no_saturation_target_generated",True),
        ("no_model_predict",True),
        ("no_training",True),
        ("no_target_times_selected",True),
        ("no_frozen_artifact_mutation",True),
    ]
    save_csv(GATES_CSV,[dict(gate=g,passed=bool(v)) for g,v in gates])
    ok=all(v for _,v in gates)

    if ok:
        status="V16C_CONSERVATIVE_201_NODE_POLLOCK_OPERATOR_GEOMETRY_CONSTRUCTED_BOUNDARY_PHYSICS_PENDING"
        diagnosis="INTERIOR_ADVECTION_AND_C7_TRANSFORMED_CAPILLARY_OPERATORS_HAVE_CONSERVATIVE_FACE_DIVERGENCE_FORMS_AND_PASS_TELESCOPING_AUDITS_WITHOUT_LEGACY_UD_DOUBLE_COUNTING"
        rec=("Freeze the C10 interior operator geometry. Before any physical-time transport solve, bind the source-authentic "
             "inlet/outlet transport boundary conditions and their transformed capillary treatment on the Pollock coordinate.")
        nxt="V16C-10A — Pollock-Coordinate Full-Physics Transport Boundary Condition Binding Audit"
    else:
        status="V16C_CONSERVATIVE_POLLOCK_OPERATOR_CONSTRUCTION_INCOMPLETE"
        diagnosis="ONE_OR_MORE_OPERATOR_GEOMETRY_OR_CONSERVATION_GATES_FAILED"
        rec="Do not construct physical BCs or generate Y. Audit only failed C10 gates."
        nxt="V16C-10R — Conservative Pollock Operator Residual Audit"

    save_csv(DECISION_CSV,[dict(
        status=status,diagnosis=diagnosis,
        interior_operator="CONSTRUCTED" if ok else "INCOMPLETE",
        physical_boundary_conditions="PENDING",
        physical_time_march_authorized=False,
        Y_generation_authorized=False,
        next_milestone=nxt)])

    savej(CONTRACT_JSON,dict(
        milestone="V16C-10",status=status,diagnosis=diagnosis,
        operator_artifact=str(OP_NPZ),operator_sha256=sha(OP_NPZ),
        advection="conservative face divergence in theta; nonlinear fw deferred to source-authentic solver",
        capillary="M/cv_dtheta times divergence of D_tilde*M*dS/dtheta face flux",
        legacy_uD_action="NOT_APPLIED",
        physical_boundary_conditions="PENDING_C10A",
        physical_time_march_authorized=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))

    savej(SUMMARY_JSON,dict(
        milestone="V16C-10",status=status,diagnosis=diagnosis,
        streamlines=ns,nodes=nn,
        advection_telescoping_max_abs=adv_telescoping_max,
        capillary_telescoping_max_abs=cap_telescoping_max,
        operator_sha256=sha(OP_NPZ),
        physical_time_march_authorized=False,Y_transport_generated=False,
        recommendation=rec,next_milestone=nxt))

    print("OPERATOR GEOMETRY")
    print(f"  Streamlines                    : {ns}")
    print(f"  Nodes / streamline             : {nn}")
    print(f"  M cell positive                : {np.all(M>0)}")
    print(f"  M face positive                : {np.all(M_face>0)}")
    print(f"  CV widths positive             : {np.all(cv_dtheta>0)}")

    print("\nCONSERVATION AUDIT")
    print(f"  Advection telescoping max abs  : {adv_telescoping_max:.6e}")
    print(f"  Capillary telescoping max abs  : {cap_telescoping_max:.6e}")
    print("  Legacy exp(Nc xD) applied      : False")
    print("  Physical saturation generated  : False")

    print("\nBOUNDARY STATUS")
    print("  Physical inlet BC              : PENDING")
    print("  Physical outlet BC             : PENDING")
    print("  C10 boundary values            : ALGEBRAIC AUDIT ONLY")

    print("\n"+"="*78)
    print("V16C-10 FINAL OPERATOR CONSTRUCTION GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\nNumerical\n ",OP_NPZ.name,"\n  SHA-256:",sha(OP_NPZ))
    print("\n"+"="*78)
    print("PAD-STREAM V16C-10 CONSERVATIVE POLLOCK OPERATOR CONSTRUCTION: COMPLETE")
    print("="*78)

if __name__=="__main__":
    main()
