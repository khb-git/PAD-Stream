#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G3-R2-R5"
PASS="POSTV16AV4PIVOTGPUHYBG3R2R5_LATENATIVE_DAY405_BRANCHSPECIFIC_PROJECTION_REPAIR_EXECUTION_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG3R2R5_TECHNICAL_NUMERICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="f62fd35af292e82f842843ca4d57413c640c23d3"

B5_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B5_CPU_GPU_Overlap_Economics_Probe.py"
B5_BLOB="e3149d043c71fa7745b37f01bb27630fcbdfa563"
R2R2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R2_LateNative_FlowNetwork_Staleness_Shadow.py"
R2R2_BLOB="1112d9b374fa98c3ff0e8fb8a2800771273d6c12"
R2R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R3_Branch_Projection_Frontier_Conditioning_Diagnostic.py"
R2R3_BLOB="026ac529bdd3a6e00d7e03efcb9588b318521b74"
R2R4_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R4_Branch_Projection_SolverConditioning_Repair_Design_Freeze.py"
R2R4_BLOB="dfa7e7f5a587dc1bbce49e4ce1efffa8b854db69"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

B5_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G4_B5_Route_Economics_Instrumentation"
B5_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B5_Summary.json"
B5_STATUS="POSTV16AV4PIVOTGPUHYBG4B5_CPU_GPU_OVERLAP_ECONOMICS_PROBE_PASS"

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R5"
OUT_REL=BASE/(OUT_TOKEN+"_LateNative_Day405_BranchSpecific_Projection_Repair_Execution")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
PROJECTION=f"{OUT_TOKEN}_Branch_Projection.csv"
RESULTS=f"{OUT_TOKEN}_Branch_Results.csv"
COMPARE=f"{OUT_TOKEN}_Staleness_Comparison.csv"
PRODUCERS=f"{OUT_TOKEN}_Producer_Comparison.csv"
REF_CHILD=f"{OUT_TOKEN}_REFRESHED_0D_Child.npz"
S5_CHILD=f"{OUT_TOKEN}_STALE_5D_Child.npz"
S15_CHILD=f"{OUT_TOKEN}_STALE_15D_Child.npz"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError):
    pass


def gt(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()


def sha256(p:Path)->str:
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):
            h.update(c)
    return h.hexdigest()


def js(p:Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_csv(p:Path,rows):
    rows=list(rows)
    if not rows:
        p.write_text("",encoding="utf-8")
        return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(p,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def import_exact(root:Path,filename:str,blob:str,name:str):
    p=root/filename
    if not p.is_file():
        raise GateError(f"missing_source:{filename}")
    actual=gt(root,"hash-object",str(p))
    if actual!=blob:
        raise GateError(f"source_blob:{filename}:{actual}:{blob}")
    spec=importlib.util.spec_from_file_location(name,p)
    if spec is None or spec.loader is None:
        raise GateError(f"source_spec:{filename}")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m


def close(a,b):
    return abs(float(a)-float(b)) <= max(1e-12,1e-12*max(abs(float(b)),1.0))


def solve2_with_x(gm,cap,ecv,ecell,target,m1,*,delta,presolve):
    # Exact R2-R3 formulation, extended only to retain the solved x vector for R5 execution.
    from scipy import sparse
    from scipy.optimize import linprog

    gm=np.asarray(gm,dtype=np.float64).ravel()
    cap=np.asarray(cap,dtype=np.float64).ravel()
    ecv=np.asarray(ecv,dtype=np.int64)
    ecell=np.asarray(ecell,dtype=np.int64)
    target=np.asarray(target,dtype=np.float64)
    n=len(ecv)
    ac=np.unique(ecell)
    av=np.unique(ecv)
    cr=np.searchsorted(ac,ecell)
    vr=np.searchsorted(av,ecv)
    nv=2*n

    As=sparse.coo_matrix(
        (np.ones(2*n),
         (np.r_[cr,len(ac)+vr],np.r_[np.arange(n),np.arange(n)])),
        shape=(len(ac)+len(av),nv)
    ).tocsr()
    bs=np.r_[gm[ac],cap[av]]

    r=np.arange(n)
    Aa=sparse.coo_matrix(
        (np.r_[np.ones(n),-np.ones(n),-np.ones(n),-np.ones(n)],
         (np.r_[r,r,n+r,n+r],np.r_[r,n+r,r,n+r])),
        shape=(2*n,nv)
    ).tocsr()
    ba=np.r_[target,-target]
    Aub=sparse.vstack([As,Aa])
    bub=np.r_[bs,ba]
    Aeq=None
    beq=None

    total=sparse.csr_matrix(
        (np.ones(n),(np.zeros(n,dtype=int),np.arange(n))),
        shape=(1,nv)
    )
    if delta is None:
        Aeq=total
        beq=np.asarray([m1],dtype=np.float64)
    else:
        Aub=sparse.vstack([Aub,total,-total])
        bub=np.r_[bub,m1,-(m1-float(delta))]

    lp=linprog(
        np.r_[np.zeros(n),np.ones(n)],
        A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=beq,
        bounds=(0,None),method="highs",
        options={"presolve":bool(presolve)}
    )
    if not lp.success:
        raise GateError(f"stage2_policy_solve:{lp.status}:{lp.message}")

    x=np.asarray(lp.x[:n],dtype=np.float64)
    realized=float(np.sum(x))
    return {
        "success":True,
        "status":int(lp.status),
        "message":str(lp.message),
        "x":x,
        "realized_mass_kg":realized,
        "mass_loss_vs_stage1_kg":float(m1-realized),
        "L1_objective_kg":float(lp.fun),
        "mass_floor_delta_kg":delta,
        "presolve":bool(presolve),
    }


def build_branch_r5(base,r4,name,stale_days,diag,*,parent_mass,frozen_pressure,pref,p3,r25,e37a,r2,sg7a,sg7d):
    xyz=diag["xyz_m"]
    tau=diag["tau_s"]
    weights_day=diag["weights_m3_s"]*base.DAY_TO_S
    xi=diag["xi"]
    nstream=int(xyz.shape[0])
    ncv=len(xi)-1
    if nstream!=base.NSL or ncv!=base.NCV:
        raise GateError(f"{name}:shape:{nstream}:{ncv}")

    op=sg7d.build_subsegment_operator(xyz,tau/base.DAY_TO_S,weights_day)
    geom=e37a.build_control_volume_geometry(r2,op,frozen_pressure,pref,base.NSL,base.NCV)
    exact_cv,exact_cell,target=r25.build_edge_target_and_support(parent_mass,op)
    cv_capacity=np.asarray(
        e37a.cv_mass_from_saturation(
            r2,
            np.full((base.NSL,base.NCV),base.MAX_SAT),
            geom["cv_pressure_mass_coeff"]),
        dtype=np.float64
    )

    s1=r25.stage1_max_representable(parent_mass,cv_capacity,exact_cv,exact_cell)
    m1=float(s1["represented_mass_kg"])
    policy=r4.EXPECTED[name]

    if not close(m1,policy["stage1_mass_kg"]):
        raise GateError(f"{name}:stage1_mass_authority:{m1}:{policy['stage1_mass_kg']}")

    if name=="REFRESHED_0D":
        delta=float(policy["delta"])
        presolve=True
    else:
        delta=None
        presolve=False

    s2=solve2_with_x(
        parent_mass,cv_capacity,exact_cv,exact_cell,target,m1,
        delta=delta,presolve=presolve
    )
    exact_mass=np.asarray(s2["x"],dtype=np.float64)
    realized=float(s2["realized_mass_kg"])
    loss=float(s2["mass_loss_vs_stage1_kg"])

    if name=="REFRESHED_0D":
        if loss < -base.MASS_TOL or loss > float(policy["delta"])+base.MASS_TOL:
            raise GateError(f"{name}:bounded_frontier_loss:{loss}:{policy['delta']}")
    else:
        if abs(realized-m1) > max(base.MASS_TOL,1e-12*max(abs(m1),1.0)):
            raise GateError(f"{name}:exact_frontier_mass:{realized}:{m1}")

    cv_mass=np.bincount(exact_cv,weights=exact_mass,minlength=base.NCVT).reshape(base.NSL,base.NCV)
    rep=np.bincount(exact_cell,weights=exact_mass,minlength=base.NCELL).reshape(base.GRID)
    residual=np.asarray(parent_mass,dtype=np.float64)-rep
    if float(np.min(residual)) < -base.MASS_TOL:
        raise GateError(f"{name}:negative_residual:{float(np.min(residual))}")
    residual=np.maximum(residual,0.0)

    parent_total=float(np.sum(parent_mass))
    split_total=float(np.sum(rep)+np.sum(residual))
    if abs(split_total-parent_total)>max(base.MASS_TOL,base.REL_TOL*max(abs(parent_total),1.0)):
        raise GateError(f"{name}:parent_split_mass:{split_total-parent_total}")

    cv_sat=np.asarray(
        e37a.invert_cv_mass_to_saturation(r2,cv_mass,geom["cv_pressure_mass_coeff"]),
        dtype=np.float64
    )
    edge_cv,edge_cell,shell,exact_pos=p3.build_xy1_support(exact_cv,exact_cell)
    edge_mass=np.zeros(len(edge_cv),dtype=np.float64)
    edge_mass[exact_pos]=exact_mass

    sub_cv=np.asarray(op["streamline"],dtype=np.int64)*base.NCV+np.asarray(op["node"],dtype=np.int64)
    sub_cell=np.asarray(op["flat_cell"],dtype=np.int64)
    exact_keys=exact_cv*base.NCELL+exact_cell
    key_to_exact={int(k):i for i,k in enumerate(exact_keys.tolist())}
    sub_exact_idx=np.asarray(
        [key_to_exact[int(k)] for k in (sub_cv*base.NCELL+sub_cell).tolist()],
        dtype=np.int64
    )

    scan=np.linspace(float(sg7a.S_INITIAL),float(sg7a.S_INJECTED),4001)
    max_df=float(np.max(np.abs(np.asarray(sg7a.df_dS(scan),dtype=np.float64))))
    u=np.asarray(sg7a.u_dimensionless(xi),dtype=np.float64)
    dtD=float(sg7a.CFL*(1.0/base.NCV)/(float(np.max(u))*max_df+float(sg7a.EPS)))
    cfl=float(dtD*np.min(diag["tau_end_s"]/base.DAY_TO_S))

    return {
        "name":name,
        "stale_days":float(stale_days),
        "diag":diag,
        "op":op,
        "geom":geom,
        "weights_day":weights_day,
        "xi":xi,
        "u":u,
        "cfl_days":cfl,
        "cv_mass":cv_mass,
        "cv_sat":cv_sat,
        "rep":rep,
        "residual":residual,
        "edge_cv":edge_cv,
        "edge_cell":edge_cell,
        "shell":shell,
        "exact_pos":exact_pos,
        "edge_mass":edge_mass,
        "exact_cv":exact_cv,
        "sub_exact_idx":sub_exact_idx,
        "represented_mass_kg":float(np.sum(rep)),
        "residual_mass_kg":float(np.sum(residual)),
        "represented_fraction":float(np.sum(rep)/np.sum(parent_mass)),
        "stage1_mass_kg":m1,
        "stage2_realized_mass_kg":realized,
        "stage2_mass_loss_vs_stage1_kg":loss,
        "stage2_L1_kg":float(s2["L1_objective_kg"]),
        "projection_policy":policy["mode"],
        "stage2_presolve":bool(presolve),
        "stage2_mass_floor_delta_kg":delta,
        "parent_split_mass_residual_kg":float(split_total-parent_total),
    }


def repository_preflight(root:Path):
    branch=gt(root,"branch","--show-current")
    head=gt(root,"rev-parse","HEAD")
    par=gt(root,"rev-parse","HEAD^")
    clean=gt(root,"status","--porcelain")==""
    b5=root/B5_RUNNER
    blob=gt(root,"hash-object",str(b5)) if b5.is_file() else "MISSING"
    print("--- G3-R2-R5 REPOSITORY IDENTITY ---")
    print("Branch:",branch)
    print("HEAD  :",head)
    print("HEAD^ :",par)
    print("Clean :",clean)
    print("B5 runner blob:",blob)
    print("Expected      :",B5_BLOB)
    if branch!=BRANCH:
        raise GateError(f"branch:{branch}:{BRANCH}")
    if par!=PARENT:
        raise GateError(f"parent:{par}:{PARENT}")
    if not clean:
        raise GateError("repository_not_clean")
    if blob!=B5_BLOB:
        raise GateError(f"B5_blob:{blob}:{B5_BLOB}")


def selftest(root:Path):
    repository_preflight(root)
    base=import_exact(root,R2R2_RUNNER,R2R2_BLOB,"g3r2r5_base_selftest")
    diag=import_exact(root,R2R3_RUNNER,R2R3_BLOB,"g3r2r5_diag_selftest")
    r4=import_exact(root,R2R4_RUNNER,R2R4_BLOB,"g3r2r5_r4_selftest")
    assert callable(base.shadow)
    assert callable(diag.solve2)
    assert r4.EXPECTED["REFRESHED_0D"]["mode"]=="BOUNDED_FRONTIER_WITHIN_FROZEN_STAGE1_TOL"
    assert r4.EXPECTED["STALE_5D"]["mode"]=="EXACT_FRONTIER_PRESOLVE_OFF"
    assert r4.EXPECTED["STALE_15D"]["mode"]=="EXACT_FRONTIER_PRESOLVE_OFF"
    assert r4.EXPECTED["REFRESHED_0D"]["delta"]==r4.EXPECTED["REFRESHED_0D"]["tol_kg"]
    print("POSTV16 GPU-HYB-G3-R2-R5 structural/authority self-test: PASS")


def main(root:Path,drive:Path)->int:
    root=root.resolve()
    drive=drive.resolve()
    out=drive/OUT_REL
    blocked=drive/BLOCK_REL
    gates=[]
    stage="preflight"

    def gate(name,cond,detail=None):
        ok=bool(cond)
        gates.append({
            "stage":stage,
            "gate":name,
            "pass":ok,
            "detail":"" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"),flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("="*190)
        print("G3-R2-R5 — LATE-NATIVE DAY405 FLOW-NETWORK STALENESS SHADOW / BRANCH-SPECIFIC PROJECTION REPAIR EXECUTION")
        print("PRESERVES DAY405 CARTESIAN MASS, NATIVE HETEROGENEOUS PV, AND FROZEN DAY365 THERMODYNAMIC PRESSURE.")
        print("NO SUPPORT GROWTH. NO MASS DISCARD. NO GLOBAL RESCALING. NO PRODUCTION CADENCE SELECTION.")
        print("="*190)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_B5_PASS_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="source_authority"
        base=import_exact(root,R2R2_RUNNER,R2R2_BLOB,"g3r2r5_base")
        diagmod=import_exact(root,R2R3_RUNNER,R2R3_BLOB,"g3r2r5_diag")
        r4=import_exact(root,R2R4_RUNNER,R2R4_BLOB,"g3r2r5_r4")
        import_exact(root,B5_RUNNER,B5_BLOB,"g3r2r5_b5")
        gate("R2R2_shadow_authority_callable",callable(base.shadow))
        gate("R2R3_frontier_solver_authority_callable",callable(diagmod.solve2))
        gate("R2R4_R5_authorized",r4.EXPECTED["REFRESHED_0D"]["mode"]=="BOUNDED_FRONTIER_WITHIN_FROZEN_STAGE1_TOL")

        stage="R4_design_freeze_authority"
        r4_summary_path=drive/r4.OUT_REL/r4.SUMMARY
        r4_decision_path=drive/r4.OUT_REL/r4.DECISION
        gate("R4_summary_present",r4_summary_path.is_file(),str(r4_summary_path))
        gate("R4_decision_present",r4_decision_path.is_file(),str(r4_decision_path))
        r4s=js(r4_summary_path)
        r4d=js(r4_decision_path)
        gate("R4_status_exact",r4s.get("status")==r4.PASS,r4s.get("status"))
        gate("R4_R5_authorized",r4d.get("G3_R2_R5_authorized") is True)
        gate("R4_no_support_growth",r4d.get("support_growth_authorized") is False)
        gate("R4_no_cadence_selection_in_R5",r4d.get("cadence_selection_authorized_in_R5") is False)
        gate("R4_P4_closed",r4d.get("P4_authorized") is False)

        stage="B5_runtime_context"
        b5p=drive/B5_REL/B5_SUM
        gate("B5_summary_present",b5p.is_file(),str(b5p))
        b5s=js(b5p)
        gate("B5_status_exact",b5s.get("status")==B5_STATUS,b5s.get("status"))
        gate("B5_exact_transport_identity",b5s.get("exact_output_identity_certified") is True)
        gate("B5_R4_transport_authority_preserved",b5s.get("G4_B4_fixed_shape_graph_transport_authority_preserved") is True)
        gate("B5_production_closed",b5s.get("integrated_GPU_runtime_production_authorized") is False)
        gate("B5_P4_closed",b5s.get("P4_authorized") is False)

        p3=base.module(root,base.P3,"g3r2r5_p3")
        r25=base.module(root,base.R25,"g3r2r5_r25")
        a2e=base.module(root,base.A2E,"g3r2r5_a2e")
        r2=base.module(root,base.R2SRC,"g3r2r5_r2")
        e37a=base.module(root,base.E37A,"g3r2r5_e37a")
        sg7a=base.module(root,base.SG7A,"g3r2r5_sg7a")
        sg7d=base.module(root,base.SG7D,"g3r2r5_sg7d")

        stage="native_authorities"
        a2ep=drive/base.A2E_REL/base.A2E_EPOCH
        a6ep=drive/base.A6E_REL/base.A6E_STATE
        gate("A2E_SHA_exact",sha256(a2ep)==base.A2E_EPOCH_SHA,sha256(a2ep))
        gate("A6E_SHA_exact",sha256(a6ep)==base.A6E_SHA,sha256(a6ep))
        with np.load(a2ep,allow_pickle=False) as z:
            frozen_pressure=np.asarray(z["refreshed_pressure_psi"],dtype=np.float64)
            pref=base.scalar(z["reference_gas_pressure_pa"])
        with np.load(a6ep,allow_pickle=False) as z:
            phi=np.asarray(z["paired_porosity"],dtype=np.float64)
        hetero_pv=phi*float(a2e.BULK_VOLUME_M3)

        specs=[
            (390,drive/base.D390_REL/base.D390_STATE,drive/base.D390_REL/base.D390_DIAG,base.D390_STATE_SHA,base.D390_DIAG_SHA),
            (400,drive/base.D400_REL/base.D400_STATE,drive/base.D400_REL/base.D400_DIAG,base.D400_STATE_SHA,base.D400_DIAG_SHA),
            (405,drive/base.D405_REL/base.D405_STATE,drive/base.D405_REL/base.D405_DIAG,base.D405_STATE_SHA,base.D405_DIAG_SHA),
        ]
        states={}
        diags={}
        stage="late_artifacts"
        for day,sp,dp,ssha,dsha in specs:
            gate(f"Day{day}_state_SHA",sha256(sp)==ssha,sha256(sp))
            gate(f"Day{day}_diag_SHA",sha256(dp)==dsha,sha256(dp))
            st=base.load_npz(sp)
            dg=base.late_diag(dp)
            rec=np.asarray(
                a2e.local_mass(r2,st["cartesian_saturation"],frozen_pressure,pref,hetero_pv),
                dtype=np.float64
            )
            gate(f"Day{day}_native_mass_semantics",
                 float(np.max(np.abs(rec-st["cartesian_component_mass_kg"])))<=1e-8)
            gate(f"Day{day}_diagnostic_saturation_same",
                 float(np.max(np.abs(dg["saturation"]-st["cartesian_saturation"])))<=1e-12)
            states[day]=st
            diags[day]=dg

        stage="branch_specific_projection_repair"
        parent_mass=np.asarray(states[405]["cartesian_component_mass_kg"],dtype=np.float64)
        parent_total=float(np.sum(parent_mass))
        parent_mass_sha=hashlib.sha256(np.ascontiguousarray(parent_mass).tobytes()).hexdigest()

        branches=[
            build_branch_r5(base,r4,"REFRESHED_0D",0,diags[405],
                            parent_mass=parent_mass,frozen_pressure=frozen_pressure,pref=pref,
                            p3=p3,r25=r25,e37a=e37a,r2=r2,sg7a=sg7a,sg7d=sg7d),
            build_branch_r5(base,r4,"STALE_5D",5,diags[400],
                            parent_mass=parent_mass,frozen_pressure=frozen_pressure,pref=pref,
                            p3=p3,r25=r25,e37a=e37a,r2=r2,sg7a=sg7a,sg7d=sg7d),
            build_branch_r5(base,r4,"STALE_15D",15,diags[390],
                            parent_mass=parent_mass,frozen_pressure=frozen_pressure,pref=pref,
                            p3=p3,r25=r25,e37a=e37a,r2=r2,sg7a=sg7a,sg7d=sg7d),
        ]

        for b in branches:
            p=r4.EXPECTED[b["name"]]
            gate(b["name"]+"_projection_policy_exact",b["projection_policy"]==p["mode"],b["projection_policy"])
            gate(b["name"]+"_stage1_mass_exact",close(b["stage1_mass_kg"],p["stage1_mass_kg"]),b["stage1_mass_kg"])
            gate(b["name"]+"_parent_split_mass_closed",
                 abs(b["parent_split_mass_residual_kg"])<=max(base.MASS_TOL,base.REL_TOL*max(abs(parent_total),1.0)),
                 b["parent_split_mass_residual_kg"])

        gate("REFRESHED_bounded_delta_exact",
             close(branches[0]["stage2_mass_floor_delta_kg"],r4.EXPECTED["REFRESHED_0D"]["delta"]),
             branches[0]["stage2_mass_floor_delta_kg"])
        gate("STALE5_exact_frontier_no_delta",branches[1]["stage2_mass_floor_delta_kg"] is None)
        gate("STALE15_exact_frontier_no_delta",branches[2]["stage2_mass_floor_delta_kg"] is None)
        gate("REFRESHED_presolve_on",branches[0]["stage2_presolve"] is True)
        gate("STALE5_presolve_off",branches[1]["stage2_presolve"] is False)
        gate("STALE15_presolve_off",branches[2]["stage2_presolve"] is False)

        common_dt=min(b["cfl_days"] for b in branches)
        gate("common_dt_positive",common_dt>0,common_dt)

        stage="shadow_transport"
        results={
            b["name"]:base.shadow(
                b,common_dt,
                parent_mass=parent_mass,parent_total=parent_total,
                frozen_pressure=frozen_pressure,pref=pref,hetero_pv=hetero_pv,
                a2e=a2e,r2=r2,e37a=e37a,sg7a=sg7a
            )
            for b in branches
        }

        injected=[results[b["name"]]["injected"] for b in branches]
        injtol=max(1e-8,1e-10*max(abs(injected[0]),1.0))
        gate("same_injected_mass_all_branches",
             max(injected)-min(injected)<=injtol,
             {"values":injected,"tol":injtol})

        for b in branches:
            x=results[b["name"]]
            gate(b["name"]+"_CV_conservative",
                 abs(float(x["CV_residual"]))<=max(base.MASS_TOL,base.REL_TOL*max(abs(x["injected"]),1.0)),
                 x["CV_residual"])
            gate(b["name"]+"_grid_conservative",
                 abs(float(x["grid_ledger_residual"]))<=max(base.MASS_TOL,base.REL_TOL*max(abs(x["final_total"]),1.0)),
                 x["grid_ledger_residual"])
            gate(b["name"]+"_capacity_safe",float(x["capacity_margin"])>=-base.MASS_TOL,x["capacity_margin"])
            gate(b["name"]+"_EOS_reconstruction",float(x["EOS_reconstruction_Linf_kg"])<=1e-8,x["EOS_reconstruction_Linf_kg"])

        ref=results["REFRESHED_0D"]
        comparisons=[]
        for name in ["STALE_5D","STALE_15D"]:
            x=results[name]
            comparisons.append({
                "branch":name,
                "staleness_days":5 if name=="STALE_5D" else 15,
                "child_cellwise_CO2_mass_relative_L2_vs_refreshed":base.rel_l2(x["child_mass"],ref["child_mass"]),
                "child_cellwise_CO2_mass_Linf_kg_vs_refreshed":float(np.max(np.abs(x["child_mass"]-ref["child_mass"]))),
                "child_saturation_relative_L2_vs_refreshed":base.rel_l2(x["child_sat"],ref["child_sat"]),
                "child_saturation_Linf_vs_refreshed":float(np.max(np.abs(x["child_sat"]-ref["child_sat"]))),
                "produced_CO2_mass_difference_kg_vs_refreshed":float(x["produced"]-ref["produced"]),
                "produced_CO2_mass_abs_difference_kg_vs_refreshed":float(abs(x["produced"]-ref["produced"])),
                "producer_CO2_gas_cut_difference_vs_refreshed":float(x["cut"]-ref["cut"]),
                "producer_CO2_gas_cut_abs_difference_vs_refreshed":float(abs(x["cut"]-ref["cut"])),
                "final_total_stored_mass_difference_kg_vs_refreshed":float(x["final_total"]-ref["final_total"]),
            })

        stage="publication"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)

        projection_rows=[]
        result_rows=[]
        producer_rows=[]
        for b in branches:
            x=results[b["name"]]
            projection_rows.append({
                "branch":b["name"],
                "staleness_days":b["stale_days"],
                "projection_policy":b["projection_policy"],
                "stage2_presolve":b["stage2_presolve"],
                "stage2_mass_floor_delta_kg":b["stage2_mass_floor_delta_kg"],
                "stage1_mass_kg":b["stage1_mass_kg"],
                "stage2_realized_mass_kg":b["stage2_realized_mass_kg"],
                "stage2_mass_loss_vs_stage1_kg":b["stage2_mass_loss_vs_stage1_kg"],
                "represented_mass_kg":b["represented_mass_kg"],
                "residual_mass_kg":b["residual_mass_kg"],
                "represented_fraction":b["represented_fraction"],
                "stage2_L1_kg":b["stage2_L1_kg"],
                "parent_split_mass_residual_kg":b["parent_split_mass_residual_kg"],
                "branch_CFL_dt_days":b["cfl_days"],
            })
            result_rows.append({
                "branch":b["name"],
                "staleness_days":b["stale_days"],
                "common_shadow_dt_days":common_dt,
                "injected_CO2_mass_kg":x["injected"],
                "produced_CO2_mass_kg":x["produced"],
                "producer_CO2_gas_cut":x["cut"],
                "final_stored_CO2_mass_kg":x["final_total"],
                "CV_transport_residual_kg":x["CV_residual"],
                "CV_to_subsegment_transfer_residual_kg":x["transfer_residual"],
                "grid_ledger_residual_kg":x["grid_ledger_residual"],
                "minimum_capacity_margin_kg":x["capacity_margin"],
                "EOS_reconstruction_Linf_kg":x["EOS_reconstruction_Linf_kg"],
                "representation_mode":x["representation_mode"],
                "representation_halo_mass_kg":x["representation_halo_mass_kg"],
                "representation_cell_L1_kg":x["representation_cell_L1_kg"],
            })
            for pr in x["producer_rows"]:
                producer_rows.append({
                    "branch":b["name"],
                    "staleness_days":b["stale_days"],
                    **pr
                })

        write_csv(out/PROJECTION,projection_rows)
        write_csv(out/RESULTS,result_rows)
        write_csv(out/COMPARE,comparisons)
        write_csv(out/PRODUCERS,producer_rows)

        cmap={
            "REFRESHED_0D":REF_CHILD,
            "STALE_5D":S5_CHILD,
            "STALE_15D":S15_CHILD,
        }
        for b in branches:
            x=results[b["name"]]
            np.savez_compressed(
                out/cmap[b["name"]],
                branch=np.asarray(b["name"]),
                staleness_days=np.asarray(b["stale_days"]),
                common_shadow_dt_days=np.asarray(common_dt),
                child_saturation=x["child_sat"],
                child_cellwise_CO2_mass_kg=x["child_mass"],
            )

        c5=next(x for x in comparisons if x["branch"]=="STALE_5D")
        c15=next(x for x in comparisons if x["branch"]=="STALE_15D")

        summary={
            "milestone":M,
            "status":PASS,
            "classification":"LATE_DAY405_BRANCH_SPECIFIC_PROJECTION_REPAIR_EXECUTED_FLOW_NETWORK_STALENESS_CAUSAL_SHADOW_COMPLETE",
            "R2_R4_design_freeze_authority_bound":True,
            "B5_runtime_context_bound":True,
            "causal_scope":"FLOW_NETWORK_STALENESS_ONLY",
            "parent_day":405.0,
            "parent_state_sha256":base.D405_STATE_SHA,
            "parent_component_mass_array_sha256":parent_mass_sha,
            "parent_stored_CO2_mass_kg":parent_total,
            "native_frozen_Day365_thermodynamic_pressure_retained":True,
            "native_heterogeneous_cartesian_PV_retained":True,
            "diagnostic_pressure_used_as_thermodynamic_state_pressure":False,
            "branch_specific_projection_policy_used":True,
            "branch_projection_policy":{b["name"]:b["projection_policy"] for b in branches},
            "branch_stage2_presolve":{b["name"]:b["stage2_presolve"] for b in branches},
            "branch_stage2_mass_floor_delta_kg":{b["name"]:b["stage2_mass_floor_delta_kg"] for b in branches},
            "branch_stage1_mass_kg":{b["name"]:b["stage1_mass_kg"] for b in branches},
            "branch_stage2_realized_mass_kg":{b["name"]:b["stage2_realized_mass_kg"] for b in branches},
            "branch_stage2_mass_loss_vs_stage1_kg":{b["name"]:b["stage2_mass_loss_vs_stage1_kg"] for b in branches},
            "branch_represented_fraction":{b["name"]:b["represented_fraction"] for b in branches},
            "common_shadow_dt_days":common_dt,
            "branch_CFL_dt_days":{b["name"]:b["cfl_days"] for b in branches},
            "same_injected_component_mass_all_branches":True,
            "STALE_5D_effect_vs_refreshed":c5,
            "STALE_15D_effect_vs_refreshed":c15,
            "all_branches_component_mass_conservative":True,
            "all_branches_capacity_safe_at_common_dt":True,
            "support_growth_executed":False,
            "mass_discard_executed":False,
            "global_mass_rescaling_executed":False,
            "cartesian_parent_mass_mutated":False,
            "canonical_trajectory_mutated":False,
            "new_scientific_tolerance_defined":False,
            "production_pressure_refresh_cadence_selected":False,
            "G3_R3_early_late_causal_cadence_decision_freeze_authorized":True,
            "G3_R3_must_preserve_scope_distinction_between_early_full_refresh_and_late_flow_network_only_shadow":True,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }
        decision={
            "milestone":M,
            "status":PASS,
            "R5_execution_complete":True,
            "production_pressure_refresh_cadence_selected":False,
            "G3_R3_early_late_causal_cadence_decision_freeze_authorized":True,
            "G3_R3_must_bind_G2_CAD_D1_early_evidence":True,
            "G3_R3_must_bind_R5_late_causal_effects":True,
            "G3_R3_must_preserve_5day_conservative_cross_regime_reference":True,
            "G3_R3_may_evaluate_longer_stagewise_or_adaptive_hold":True,
            "P4_authorized":False,
        }

        (out/SUMMARY).write_text(
            json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",
            encoding="utf-8"
        )
        (out/DECISION).write_text(
            json.dumps(decision,indent=2,sort_keys=True,allow_nan=False)+"\n",
            encoding="utf-8"
        )
        write_csv(out/GATES,gates)
        manifest=[
            {"file":q.name,"sha256":sha256(q),"bytes":q.stat().st_size}
            for q in sorted(out.iterdir())
            if q.is_file() and q.name!=MANIFEST
        ]
        write_csv(out/MANIFEST,manifest)

        print("="*190)
        print(M,"PASS")
        print("Parent day                                      : 405")
        print("Common shadow dt days                           :",common_dt)
        print("Projection policies                             :",{b["name"]:b["projection_policy"] for b in branches})
        print("Stage2 mass loss kg                             :",{b["name"]:b["stage2_mass_loss_vs_stage1_kg"] for b in branches})
        print("5d stale child mass relL2 vs refreshed          :",c5["child_cellwise_CO2_mass_relative_L2_vs_refreshed"])
        print("15d stale child mass relL2 vs refreshed         :",c15["child_cellwise_CO2_mass_relative_L2_vs_refreshed"])
        print("5d stale child saturation Linf vs refreshed     :",c5["child_saturation_Linf_vs_refreshed"])
        print("15d stale child saturation Linf vs refreshed    :",c15["child_saturation_Linf_vs_refreshed"])
        print("Production cadence selected                     : False")
        print("G3-R3 cadence decision freeze authorized        : True")
        print("P4 authorized                                   : False")
        print("="*190)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":M,
            "status":BLOCK,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "production_pressure_refresh_cadence_selected":False,
            "G3_R3_early_late_causal_cadence_decision_freeze_authorized":False,
            "P4_authorized":False,
        }
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",
            encoding="utf-8"
        )
        print(M,"BLOCK")
        print("Stage:",stage)
        print("Exception:",repr(exc))
        return 2


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        try:
            selftest(a.project_root.resolve())
            raise SystemExit(0)
        except Exception as exc:
            print(M,"SELF-TEST BLOCK",repr(exc))
            raise
    raise SystemExit(main(a.project_root,a.drive_root))
