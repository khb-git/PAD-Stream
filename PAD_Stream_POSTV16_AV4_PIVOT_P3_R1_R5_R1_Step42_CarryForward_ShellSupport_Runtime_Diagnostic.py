#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, shutil, subprocess, sys, time
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P3-R1-R5-R1"
NAME = "Step-42 Carry-Forward Shell-Support Runtime Diagnostic"
PASS = "AV4PIVOTP3R1R5R1_STEP42_CARRY_FORWARD_SHELL_SUPPORT_RUNTIME_DIAGNOSTIC_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP3R1R5R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "354f532b3b1cc519d00f0a048abf11505a89fb02"

P3R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_Corrected_Dense_FrozenFlow_Trajectory_and_Exact_5Day_Flow_Diagnostic_Sweep.py"
P3R1_BLOB = "84076001f40ebcf0825bb8d9bcabe060ed0840d2"
R31 = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R31_PostR30_Recurrent_FrozenFlow_Transport_Mapback_Certification.py"
R31_BLOB = "c6307aa53109c4ae6c4a2f962e1fef86fbc8ea4a"
R32 = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R32_Independent_Recurrent_Operation_Closure_Audit.py"
R32_BLOB = "435f5d6dcba38de7166e41ba9e081b6ef573edcf"
R5 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R5_RestartSafe_Day365_to_Day370_Repaired_Pilot_and_Exact_Flow_Diagnostic.py"
R5_BLOB = "effbefeebe1444010b07e0384061f0d4e4f26fe4"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
R5_STAGE_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R5_STAGING"
R5_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R5_BLOCKED"
R5_BLOCK_FILE = "POSTV16_AV4_PIVOT_P3_R1_R5_Blocked_Report.json"
R5_BLOCK_STATUS = "AV4PIVOTP3R1R5_TECHNICAL_OR_AUTHORITY_BLOCK"
R5_CP = "POSTV16_AV4_PIVOT_P3_R1_R5_Latest_Recurrent_Checkpoint.npz"
R5_CP_META = "POSTV16_AV4_PIVOT_P3_R1_R5_Latest_Recurrent_Checkpoint.json"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R5_R1"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_Step42_CarryForward_ShellSupport_Runtime_Diagnostic")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
LOCAL = f"{OUT_TOKEN}_Step42_Localization.json"
CG = f"{OUT_TOKEN}_Column_Generation_Audit.csv"
RESULT = f"{OUT_TOKEN}_CarryForward_Result.json"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

DAY_TO_S = 86400.0
MASS_TOL = 1e-6
SAT_TOL = 1e-10
REL_TOL = 1e-10
HIGHS_FEAS_TOL = 1e-10
HALO_OPT_TOL = 1e-6
PRICING_TOL = 1e-8
POSITIVE_EDGE_TOL = 1e-10
EXPECTED_CP_DAY = 366.4084157817048
EXPECTED_CP_STEPS = 41
EXPECTED_CP_SHA = "70fd7b6c233d9fe62828ffb5e979cc5a09bb73955b92a64c90d1cecfa7dd9a86"

class GateError(RuntimeError): pass

def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git","-C",str(root),*args], text=True).strip()

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def load_module(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise GateError(f"cannot_load:{path}")
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def js(path: Path): return json.loads(path.read_text(encoding="utf-8"))

def csvb(rows):
    if not rows: return b""
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    s=io.StringIO(newline=""); w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)
    return s.getvalue().encode()

def jb(obj): return (json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def classify(certified: bool, method: str | None, result: dict[str,Any]):
    if certified:
        return (
            "P3R1_STEP42_CARRY_FORWARD_SHELL_SUPPORT_COLUMN_GENERATION_GLOBAL_OPTIMUM_CERTIFIED_R5_CHECKPOINT_RESUME_REPAIR_AUTHORIZED",
            f"Implement the R5 resume repair from the preserved step-41 checkpoint using carry-forward shell support and {method} restricted-master solves with full omitted-column pricing; do not restart from Day365.",
            True,
        )
    if result.get("any_restricted_master_success"):
        return (
            "P3R1_STEP42_RESTRICTED_MASTER_SOLVED_BUT_GLOBAL_PRICING_NOT_CLOSED_ADDITIONAL_RUNTIME_DIAGNOSIS_REQUIRED",
            "Continue from the step-41 checkpoint with the recorded pricing evidence; do not enlarge the physical timestep or change physics.",
            False,
        )
    return (
        "P3R1_STEP42_RESTRICTED_MASTER_RUNTIME_LIMIT_PERSISTS_WITH_CARRY_FORWARD_SUPPORT_SOLVER_EXECUTION_REDESIGN_REQUIRED",
        "Preserve the step-41 checkpoint and frozen LP; investigate solver execution/basis reuse rather than changing CFL, transport, or support topology.",
        False,
    )

def selftest():
    c,_,ok=classify(True,"highs-ds",{})
    assert "RESUME_REPAIR_AUTHORIZED" in c and ok
    c,_,ok=classify(False,None,{"any_restricted_master_success":False})
    assert "RUNTIME_LIMIT_PERSISTS" in c and not ok
    assert PARENT=="354f532b3b1cc519d00f0a048abf11505a89fb02"
    print("POSTV16 AV4 PIVOT P3-R1-R5-R1 structural self-test: PASS")

def main(project_root: Path, drive_root: Path, time_limit_seconds: float, max_cg_iterations: int, column_batch_size: int) -> int:
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix, csr_matrix, eye, hstack, vstack

    root=project_root.resolve(); drive=drive_root.resolve()
    out=drive/OUT_REL; staging=drive/STAGE_REL; blocked=drive/BLOCK_REL
    stage="preflight"; gates=[]

    def gate(name, cond, detail=None):
        ok=bool(cond); gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"), flush=True)
        if not ok: raise GateError(name)

    try:
        print("="*220)
        print("POSTV16-AV4-PIVOT-P3-R1-R5-R1 — STEP-42 CARRY-FORWARD SHELL-SUPPORT RUNTIME DIAGNOSTIC")
        print("READ-ONLY. CONSUMES THE PRESERVED R5 STEP-41 CHECKPOINT. NO STATE/TIME ADVANCE.")
        print("="*220)

        stage="preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out/SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (blocked/f"{OUT_TOKEN}_Blocked_Report.json").exists())
        gate("no_preexisting_STAGING", not staging.exists())

        stage="repository_authority"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_R5_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        for fn,blob in [(P3R1,P3R1_BLOB),(R31,R31_BLOB),(R32,R32_BLOB),(R5,R5_BLOB)]:
            fp=root/fn; gate(f"{Path(fn).stem}_present",fp.is_file(),str(fp))
            gate(f"{Path(fn).stem}_blob_exact",gt(root,"hash-object",str(fp))==blob,gt(root,"hash-object",str(fp)))

        p3=load_module(root/P3R1,"p3r1_r5r1_p3")

        stage="R5_block_and_checkpoint_authority"
        r5block=drive/R5_BLOCK_REL/R5_BLOCK_FILE
        cp=drive/R5_STAGE_REL/R5_CP
        cpmeta=drive/R5_STAGE_REL/R5_CP_META
        gate("R5_BLOCK_exists",r5block.is_file(),str(r5block))
        gate("R5_checkpoint_exists",cp.is_file(),str(cp))
        gate("R5_checkpoint_meta_exists",cpmeta.is_file(),str(cpmeta))
        b=js(r5block); meta=js(cpmeta)
        gate("R5_BLOCK_status_exact",b.get("status")==R5_BLOCK_STATUS,b.get("status"))
        gate("R5_BLOCK_no_state_mutation",b.get("authoritative_physics_state_mutated") is False and b.get("authoritative_physical_time_advanced") is False)
        exc=str(b.get("exception",""))
        gate("R5_BLOCK_retry_budget_exhausted_at_checkpoint",f"atomic_retry_budget_exhausted:{EXPECTED_CP_DAY}" in exc,exc[:200])
        gate("R5_BLOCK_all_nine_retries_runtime_limited",exc.count("Time limit reached") == 9,exc.count("Time limit reached"))
        gate("checkpoint_SHA_exact",sha(cp)==EXPECTED_CP_SHA,sha(cp))
        gate("checkpoint_meta_SHA_exact",meta.get("checkpoint_sha256")==EXPECTED_CP_SHA,meta.get("checkpoint_sha256"))
        gate("checkpoint_day_exact",abs(float(meta.get("physical_day"))-EXPECTED_CP_DAY)<=1e-12,meta.get("physical_day"))
        gate("checkpoint_steps_exact",int(meta.get("accepted_atomic_steps"))==EXPECTED_CP_STEPS,meta.get("accepted_atomic_steps"))

        stage="authoritative_inputs"
        a2ep=drive/p3.A2E_REL/p3.A2E_EPOCH; a6ep=drive/p3.A6E_REL/p3.A6E_STATE
        gate("A2E_epoch_exists",a2ep.is_file(),str(a2ep)); gate("A2E_epoch_SHA_exact",sha(a2ep)==p3.A2E_EPOCH_SHA,sha(a2ep))
        gate("A6E_state_exists",a6ep.is_file(),str(a6ep)); gate("A6E_state_SHA_exact",sha(a6ep)==p3.A6E_SHA,sha(a6ep))
        for fn,expected in [(p3.A2E,p3.A2E_BLOB),(p3.R2SRC,p3.R2SRC_BLOB),(p3.E37A,p3.E37A_BLOB),(p3.SG7A,p3.SG7A_BLOB),(p3.SG7D,p3.SG7D_BLOB)]:
            fp=root/fn; gate(f"{Path(fn).stem}_present",fp.is_file(),str(fp)); gate(f"{Path(fn).stem}_blob_exact",gt(root,"hash-object",str(fp))==expected,gt(root,"hash-object",str(fp)))

        a2e=load_module(root/p3.A2E,"p3r1r5r1_a2e"); r2=load_module(root/p3.R2SRC,"p3r1r5r1_r2")
        e37a=load_module(root/p3.E37A,"p3r1r5r1_e37a"); sg7a=load_module(root/p3.SG7A,"p3r1r5r1_sg7a"); sg7d=load_module(root/p3.SG7D,"p3r1r5r1_sg7d")

        with np.load(a2ep,allow_pickle=False) as z:
            frozen_pressure=np.asarray(z["refreshed_pressure_psi"],dtype=np.float64)
            xyz=np.asarray(z["streamline_xyz_m"],dtype=np.float64); tof_s=np.asarray(z["streamline_tof_s"],dtype=np.float64)
            weights_m3_s=np.asarray(z["streamline_weight_m3_s"],dtype=np.float64); p_ref=float(np.asarray(z["reference_gas_pressure_pa"]).reshape(())); tau_end_s=np.asarray(z["tau_end_s"],dtype=np.float64)
        with np.load(a6ep,allow_pickle=False) as z: phi=np.asarray(z["paired_porosity"],dtype=np.float64)
        with np.load(cp,allow_pickle=False) as z:
            physical_day=float(np.asarray(z["physical_day"]).reshape(())); accepted_steps=int(np.asarray(z["accepted_atomic_steps"]).reshape(()))
            current_grid_mass=np.asarray(z["cartesian_component_mass_kg"],dtype=np.float64); current_rep=np.asarray(z["represented_cartesian_cell_mass_kg"],dtype=np.float64)
            current_residual=np.asarray(z["grid_residual_component_mass_kg"],dtype=np.float64); current_cv_mass=np.asarray(z["transport_CV_component_mass_kg"],dtype=np.float64)
            current_cv_sat=np.asarray(z["transport_CV_saturation"],dtype=np.float64); edge_cv=np.asarray(z["XY1_edge_cv"],dtype=np.int64); edge_cell=np.asarray(z["XY1_edge_cell"],dtype=np.int64)
            shell=np.asarray(z["XY1_edge_shell_cost"],dtype=np.int8); current_edge_mass=np.asarray(z["XY1_edge_assigned_mass_kg"],dtype=np.float64)

        gate("checkpoint_npz_day_exact",abs(physical_day-EXPECTED_CP_DAY)<=1e-12,physical_day)
        gate("checkpoint_npz_steps_exact",accepted_steps==EXPECTED_CP_STEPS,accepted_steps)

        hetero_pv=phi*float(a2e.BULK_VOLUME_M3)
        op=sg7d.build_subsegment_operator(xyz,tof_s/DAY_TO_S,weights_m3_s*DAY_TO_S)
        geometry=e37a.build_control_volume_geometry(r2,op,frozen_pressure,p_ref,p3.NSL,p3.NCV)
        xi_faces=np.linspace(0.0,1.0,p3.NCV+1,dtype=np.float64); weights_m3_day=weights_m3_s*DAY_TO_S
        sat_scan=np.linspace(float(sg7a.S_INITIAL),float(sg7a.S_INJECTED),4001)
        max_df=float(np.max(np.abs(np.asarray(sg7a.df_dS(sat_scan),dtype=np.float64))))
        u_face=np.asarray(sg7a.u_dimensionless(xi_faces),dtype=np.float64)
        dtD=float(sg7a.CFL*(1.0/p3.NCV)/(float(np.max(u_face))*max_df+float(sg7a.EPS)))
        dt=float(dtD*np.min(tau_end_s/DAY_TO_S))
        gate("nominal_dt_exact",abs(dt-0.03730130768843055)<=1e-14,dt)

        sub_pv=np.asarray(geometry["pv_m3"],dtype=np.float64); pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64)
        flat_cell=np.asarray(geometry["flat_cell"],dtype=np.int64); geom_cv_id=np.asarray(geometry["cv_id"],dtype=np.int64); rho_ref=float(e37a.CO2_RHO_REF_KG_M3)

        full_sat=np.full(p3.GRID,float(a2e.INJECTED),dtype=np.float64)
        cart_capacity=np.asarray(a2e.local_mass(r2,full_sat,frozen_pressure,p_ref,hetero_pv),dtype=np.float64)
        rep_capacity=cart_capacity-current_residual; rep_capacity_flat=np.maximum(rep_capacity,0.0).reshape(-1)
        cart_cap_tol=max(1e-8,1e-12*max(float(np.max(cart_capacity)),1.0))
        gate("represented_capacity_nonnegative",float(np.min(rep_capacity))>=-cart_cap_tol,float(np.min(rep_capacity)))

        stage="step42_candidate"
        theory_flux=np.zeros((p3.NSL,p3.NCV+1),dtype=np.float64)
        theory_flux[:,0]=weights_m3_day*rho_ref
        ff_internal=np.asarray(sg7a.fractional_flow(current_cv_sat[:,:-1]),dtype=np.float64)
        theory_flux[:,1:-1]=weights_m3_day[:,None]*u_face[None,1:-1]*ff_internal*rho_ref
        ff_out=np.asarray(sg7a.fractional_flow(current_cv_sat[:,-1]),dtype=np.float64)
        theory_flux[:,-1]=weights_m3_day*float(u_face[-1])*ff_out*rho_ref
        new_cv_mass=current_cv_mass+dt*(theory_flux[:,:-1]-theory_flux[:,1:])
        new_cv_sat=np.asarray(e37a.invert_cv_mass_to_saturation(r2,new_cv_mass,geometry["cv_pressure_mass_coeff"]),dtype=np.float64)

        old_sub_sat=current_cv_sat.reshape(-1)[geom_cv_id]; new_sub_sat=new_cv_sat.reshape(-1)[geom_cv_id]
        old_sub_sg=np.clip(old_sub_sat-p3.BACKGROUND,0.0,p3.MAX_SG); new_sub_sg=np.clip(new_sub_sat-p3.BACKGROUND,0.0,p3.MAX_SG)
        rho_old=np.asarray(r2.gas_density_from_state(old_sub_sat,pseg,p_ref),dtype=np.float64); rho_new=np.asarray(r2.gas_density_from_state(new_sub_sat,pseg,p_ref),dtype=np.float64)
        sub_delta=sub_pv*(rho_new*new_sub_sg-rho_old*old_sub_sg)
        delta_grid=np.bincount(flat_cell,weights=sub_delta,minlength=p3.NCELL).reshape(p3.GRID)
        direct_target=current_rep+delta_grid

        nedge=len(edge_cv); idx=np.arange(nedge,dtype=np.int64)
        Aeq_full=coo_matrix((np.ones(nedge),(edge_cv,idx)),shape=(p3.NCVT,nedge)).tocsr()
        Acell_full=coo_matrix((np.ones(nedge),(edge_cell,idx)),shape=(p3.NCELL,nedge)).tocsr()
        c1=(shell>0).astype(np.float64)

        stage="step42_stage1"
        t=time.perf_counter()
        lp1=linprog(c1,A_ub=Acell_full,b_ub=rep_capacity_flat,A_eq=Aeq_full,b_eq=new_cv_mass.reshape(-1),bounds=(0.0,None),method="highs-ds",
                    options={"presolve":True,"primal_feasibility_tolerance":HIGHS_FEAS_TOL,"dual_feasibility_tolerance":HIGHS_FEAS_TOL,"time_limit":float(time_limit_seconds)})
        stage1_wall=time.perf_counter()-t
        gate("step42_stage1_success",lp1.success,[lp1.status,lp1.message])
        halo_opt=float(lp1.fun); x1=np.asarray(lp1.x,dtype=np.float64)
        shell_mask=shell>0; exact_positions=np.where(shell==0)[0]; shell_positions=np.where(shell_mask)[0]
        stage1_shell=np.where(shell_mask & (x1>POSITIVE_EDGE_TOL))[0]
        prior_shell=np.where(shell_mask & (current_edge_mass>POSITIVE_EDGE_TOL))[0]
        union_shell=np.unique(np.concatenate([stage1_shell,prior_shell]))
        overlap=np.intersect1d(stage1_shell,prior_shell)
        local={
            "checkpoint_day":physical_day,"candidate_day":physical_day+dt,"accepted_steps_parent":accepted_steps,
            "stage1_wall_seconds":stage1_wall,"stage1_halo_optimum_kg":halo_opt,
            "stage1_positive_shell_edge_count":int(stage1_shell.size),
            "prior_accepted_positive_shell_edge_count":int(prior_shell.size),
            "stage1_prior_shell_overlap_count":int(overlap.size),
            "carry_forward_union_shell_edge_count":int(union_shell.size),
            "full_shell_edge_count":int(shell_positions.size),
            "full_support_edge_count":int(nedge),
        }
        print("--- STEP42 LOCALIZATION ---")
        for k,v in local.items(): print(f"{k:58s}: {v}")

        def run_cg(method: str):
            selected_shell=set(int(x) for x in union_shell.tolist())
            rows=[]; final_lp=None; final_positions=None; certified=False; pricing_err=None; min_rc=None
            for it in range(1,max_cg_iterations+1):
                sel=np.unique(np.concatenate([exact_positions,np.asarray(sorted(selected_shell),dtype=np.int64)]))
                nsel=int(sel.size); scv=edge_cv[sel]; scall=edge_cell[sel]; sshell=shell[sel]; sidx=np.arange(nsel,dtype=np.int64)
                Aeqx=coo_matrix((np.ones(nsel),(scv,sidx)),shape=(p3.NCVT,nsel)).tocsr()
                Acell=coo_matrix((np.ones(nsel),(scall,sidx)),shape=(p3.NCELL,nsel)).tocsr()
                nd=p3.NCELL; Z=csr_matrix((p3.NCELL,nd)); I=eye(nd,format="csr")
                A_ub=vstack([
                    hstack([Acell,Z],format="csr"),
                    hstack([Acell,-I],format="csr"),
                    hstack([-Acell,-I],format="csr"),
                    hstack([csr_matrix((sshell>0).astype(float).reshape(1,-1)),csr_matrix((1,nd))],format="csr"),
                    hstack([-csr_matrix((sshell>0).astype(float).reshape(1,-1)),csr_matrix((1,nd))],format="csr"),
                ],format="csr")
                target=direct_target.reshape(-1)
                b_ub=np.concatenate([rep_capacity_flat,target,-target,np.asarray([halo_opt+HALO_OPT_TOL,-halo_opt+HALO_OPT_TOL])])
                Aeq=hstack([Aeqx,csr_matrix((p3.NCVT,nd))],format="csr")
                c=np.concatenate([np.zeros(nsel),np.ones(nd)])
                ts=time.perf_counter()
                lp=linprog(c,A_ub=A_ub,b_ub=b_ub,A_eq=Aeq,b_eq=new_cv_mass.reshape(-1),bounds=[(0.0,None)]*(nsel+nd),method=method,
                           options={"presolve":True,"primal_feasibility_tolerance":HIGHS_FEAS_TOL,"dual_feasibility_tolerance":HIGHS_FEAS_TOL,"time_limit":float(time_limit_seconds)})
                wall=time.perf_counter()-ts
                row={"method":method,"iteration":it,"selected_edge_count":nsel,"selected_shell_edge_count":int(np.count_nonzero(sshell>0)),
                     "solve_success":bool(lp.success),"solve_status":int(lp.status),"solve_message":str(lp.message),"solve_wall_seconds":wall,
                     "objective_L1_kg":float(lp.fun) if lp.success else None}
                print(f"[{method} CG {it}] shell={row['selected_shell_edge_count']} success={lp.success} status={lp.status} wall={wall:.3f}s",flush=True)
                final_lp=lp; final_positions=sel
                if not lp.success:
                    rows.append(row); break
                mu=np.asarray(lp.ineqlin.marginals,dtype=np.float64); lam=np.asarray(lp.eqlin.marginals,dtype=np.float64); lower=np.asarray(lp.lower.marginals,dtype=np.float64)
                mu_cap=mu[:p3.NCELL]; mu_pos=mu[p3.NCELL:2*p3.NCELL]; mu_neg=mu[2*p3.NCELL:3*p3.NCELL]
                mu_hp=float(mu[3*p3.NCELL]); mu_hn=float(mu[3*p3.NCELL+1])
                pred=-(mu_cap[scall]+mu_pos[scall]-mu_neg[scall]+(sshell>0).astype(float)*(mu_hp-mu_hn))-lam[scv]
                pricing_err=float(np.max(np.abs(pred-lower[:nsel])))
                gate(f"{method}_pricing_formula_iter_{it}",pricing_err<=1e-7,pricing_err)
                sm=np.zeros(nedge,dtype=bool)
                if selected_shell: sm[np.asarray(sorted(selected_shell),dtype=np.int64)]=True
                omitted=np.where(shell_mask & (~sm))[0]
                if omitted.size:
                    oc=edge_cell[omitted]; ov=edge_cv[omitted]
                    rc=-(mu_cap[oc]+mu_pos[oc]-mu_neg[oc]+(mu_hp-mu_hn))-lam[ov]
                    min_rc=float(np.min(rc)); neg=np.where(rc < -PRICING_TOL)[0]
                else:
                    rc=np.asarray([]); min_rc=float("inf"); neg=np.asarray([],dtype=np.int64)
                row.update({"pricing_validation_error":pricing_err,"omitted_shell_count":int(omitted.size),
                            "minimum_omitted_reduced_cost":min_rc,"negative_omitted_count":int(neg.size)})
                if neg.size==0:
                    row["global_optimality_certified"]=True; rows.append(row); certified=True; break
                order=neg[np.argsort(rc[neg])]; take=order[:column_batch_size]; add=omitted[take]
                for pos in add.tolist(): selected_shell.add(int(pos))
                row["columns_added"]=int(add.size); row["most_negative_added"]=float(np.min(rc[take])) if take.size else None
                rows.append(row)
            return certified,rows,final_lp,final_positions,pricing_err,min_rc

        stage="carry_forward_column_generation"
        methods=["highs-ds","highs-ipm"]
        all_rows=[]; certified=False; cert_method=None; final_lp=None; final_pos=None; final_min_rc=None
        any_success=False
        for method in methods:
            ok,rows,lp,pos,perr,mrc=run_cg(method)
            all_rows.extend(rows)
            any_success = any_success or any(bool(r.get("solve_success")) for r in rows)
            if ok:
                certified=True; cert_method=method; final_lp=lp; final_pos=pos; final_min_rc=mrc; break

        result={"global_optimality_certified":certified,"certified_method":cert_method,"any_restricted_master_success":any_success,
                "stage1_halo_optimum_kg":halo_opt,"carry_forward_union_shell_edge_count":int(union_shell.size),
                "final_minimum_omitted_reduced_cost":final_min_rc,"final_selected_shell_edge_count":None,
                "CV_equality_max_abs_error_kg":None,"halo_mass_kg":None,"L1_recomputed_kg":None,
                "cartesian_min_mass_kg":None,"cartesian_capacity_excess_kg":None}

        if certified and final_lp is not None and final_pos is not None:
            nsel=int(final_pos.size); z=np.asarray(final_lp.x); x=z[:nsel]; d=z[nsel:]; scv=edge_cv[final_pos]; scall=edge_cell[final_pos]; sshell=shell[final_pos]
            cv=np.bincount(scv,weights=x,minlength=p3.NCVT).reshape(p3.NSL,p3.NCV)
            rep=np.bincount(scall,weights=x,minlength=p3.NCELL); halo=float(np.sum(x[sshell>0]))
            cv_err=float(np.max(np.abs(cv-new_cv_mass))); l1=float(np.sum(np.abs(rep-direct_target.reshape(-1))))
            aux=float(np.max(np.abs(d-np.abs(rep-direct_target.reshape(-1)))))
            grid=rep.reshape(p3.GRID)+current_residual; cmin=float(np.min(grid)); cap=float(np.max(grid-cart_capacity))
            result.update({"final_selected_shell_edge_count":int(np.count_nonzero(sshell>0)),"CV_equality_max_abs_error_kg":cv_err,
                           "halo_mass_kg":halo,"halo_optimum_gap_kg":halo-halo_opt,"L1_recomputed_kg":l1,
                           "auxiliary_max_abs_error_kg":aux,"cartesian_min_mass_kg":cmin,"cartesian_capacity_excess_kg":cap})
            gate("certified_CV_equalities",cv_err<=MASS_TOL,cv_err)
            gate("certified_halo_optimum",abs(halo-halo_opt)<=2*HALO_OPT_TOL,[halo,halo_opt])
            gate("certified_L1_objective",abs(float(final_lp.fun)-l1)<=max(1e-5,1e-10*max(l1,1.0)),[final_lp.fun,l1])
            gate("certified_auxiliary",aux<=1e-5,aux)
            gate("certified_cartesian_nonnegative",cmin>=-MASS_TOL,cmin)
            gate("certified_cartesian_capacity",cap<=cart_cap_tol,[cap,cart_cap_tol])

        classification,recommendation,auth=classify(certified,cert_method,result)

        stage="publication"
        staging.mkdir(parents=True,exist_ok=False)
        (staging/LOCAL).write_bytes(jb(local)); (staging/CG).write_bytes(csvb(all_rows)); (staging/RESULT).write_bytes(jb(result)); (staging/GATES).write_bytes(csvb(gates))
        summary={"milestone":M,"name":NAME,"status":PASS,"classification":classification,"repository_parent_R5_commit":PARENT,
                 "R5_block_status_bound":R5_BLOCK_STATUS,"R5_checkpoint_sha256":EXPECTED_CP_SHA,"R5_checkpoint_day":physical_day,
                 "R5_checkpoint_accepted_steps":accepted_steps,"authoritative_physics_state_mutated":False,"authoritative_physical_time_advanced":False,
                 "localization":local,"carry_forward_result":result,"recommended_next_action":recommendation,
                 "CFL_change_authorized":False,"transport_law_change_authorized":False,"support_topology_change_authorized":False,
                 "residual_sidecar_change_authorized":False,"lexicographic_objective_change_authorized":False,
                 "R5_checkpoint_resume_repair_authorized":auth,"Day370_to_Day375_repaired_pilot_authorized":False,
                 "P3_R1_full_rerun_authorized":False,"P4_authorized":False}
        decision={"milestone":M,"status":PASS,"classification":classification,"R32_recurrent_semantics_remain_authoritative":True,
                  "R5_prior_block_is_scientific_failure":False,"R5_checkpoint_must_be_preserved":True,"restart_from_Day365_authorized":False,
                  "R5_checkpoint_resume_repair_authorized":auth,"carry_forward_prior_shell_support_may_seed_restricted_master":auth,
                  "omitted_shell_dual_pricing_must_close_before_acceptance":True,
                  "physics_change_authorized":False,"CFL_change_authorized":False,"support_topology_change_authorized":False,
                  "lexicographic_objective_change_authorized":False,"Day370_to_Day375_repaired_pilot_authorized":False,
                  "P3_R1_full_rerun_authorized":False,"P4_authorized":False,"recommended_next_action":recommendation}
        (staging/SUMMARY).write_bytes(jb(summary)); (staging/DECISION).write_bytes(jb(decision))
        rows=[]
        for p in sorted(staging.iterdir()):
            if p.is_file() and p.name!=MANIFEST: rows.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
        (staging/MANIFEST).write_bytes(csvb(rows))
        staging.rename(out)
        print("="*220); print(M,"PASS"); print("Classification:",classification); print("Certified method:",cert_method)
        print("R5 checkpoint resume repair authorized:",auth); print("Full P3-R1 rerun authorized: False"); print("P4 authorized: False"); print("="*220)
        return 0
    except Exception as exc:
        if staging.exists(): shutil.rmtree(staging)
        blocked.mkdir(parents=True,exist_ok=True)
        report=blocked/f"{OUT_TOKEN}_Blocked_Report.json"
        if not report.exists():
            report.write_bytes(jb({"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),
                                   "authoritative_physics_state_mutated":False,"authoritative_physical_time_advanced":False,
                                   "P3_R1_full_rerun_authorized":False,"P4_authorized":False,"gates_completed":gates}))
        print(M,"TECHNICAL / AUTHORITY BLOCK"); print("Stage:",stage); print("Exception:",repr(exc)); return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--time-limit-seconds",type=float,default=60.0)
    ap.add_argument("--max-cg-iterations",type=int,default=5)
    ap.add_argument("--column-batch-size",type=int,default=5000)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        selftest(); raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root,args.time_limit_seconds,args.max_cg_iterations,args.column_batch_size))
