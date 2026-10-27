#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3-R5"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R4R3R5_CONTROLLED_GENERALIZED_ACTIVE_SET_ONE_STEP_"
    "SEPARATION_LOOP_VALIDATION_PASS_EMPTY_POOL_CUT_DISCOVERED_QP_PROJECTED_"
    "CANDIDATE_EXACTLY_FEASIBLE_NO_FIVE_STAGE_ASSIGNMENT_NO_TIME_ADVANCE"
)
STATUS_FAIL = (
    "AV4F4R3R3R3R3R3O3R6R4R3R5_CONTROLLED_GENERALIZED_ACTIVE_SET_ONE_STEP_"
    "SEPARATION_LOOP_VALIDATION_SCIENTIFIC_FAIL_NO_AUTOMATIC_RERUN_"
    "NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R4R3R5_TECHNICAL_OR_AUTHORITY_BLOCK"

PARENT_R3R4_COMMIT = "b17fbb936f43fa1501adf6164b35da7b4c698a8f"

R3R4 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_"
    "Generalized_ActiveSet_BoxConstrained_Projected_CoupledSolver_Semantics_Design_Freeze.py"
)
R3R4_BLOB = "621f77be6dd691fe457751bb91635a9aac39a7e5"
R3R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_"
    "Controlled_AlphaDependent_BoxConstrained_Tangent_Candidate_Feasibility_Test.py"
)
R3R3_BLOB = "9d10e50f49af402634db0f22e8f29899076eb6da"
R3R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_"
    "Saturation_Box_Tangent_Correction_Compatibility_ReadOnly_Audit.py"
)
R3R1_BLOB = "aaf38a0a271e05b04c0d17f93ca07d2a69bdfea3"
R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1_"
    "CV60424_FrozenE2_Active_Cut_Local_Feasibility_Geometry_Audit.py"
)
R1_BLOB = "c7f7b33885c36808e9ea5cda929c3fc60dfea31e"
R4 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_"
    "Controlled_Adaptive_Feasibility_Preserving_Stabilized_Coupled_Execution.py"
)
R4_BLOB = "c41cd5c78e7cc2d91e1920e538f1793037961a31"
R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_"
    "Projected_Tangent_Constrained_Update_Semantics_Design_Freeze.py"
)
R2_BLOB = "687a35265bf0fe72a2110e2f91dab78cac5805b8"
R3DESIGN = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_"
    "Adaptive_Feasibility_Preserving_Stabilization_Semantics_Design_Freeze.py"
)
R3DESIGN_BLOB = "c118972a991e4ae0ce7200a9f880a73407450b8b"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R3R3_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_"
    "Controlled_AlphaDependent_BoxConstrained_Tangent_Candidate_Feasibility_Test"
)
R3_RECOVERY = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Recovery_Checkpoints"
R4_RECOVERY = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Recovery_Checkpoints"

OUT = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_"
    "Controlled_Generalized_ActiveSet_OneStep_SeparationLoop_Validation"
)
RECOVERY = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_Recovery_Checkpoints"
FAIL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_SCIENTIFIC_FAIL"
BLOCK = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_BLOCKED"

SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_Summary.json"
STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_Validation_State.npz"
CUT_JSON = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_Discovered_Cut.json"
ROUNDS_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_Separation_Rounds.csv"
DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_Decision_Contract.json"
GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_Final_Gate_Matrix.csv"
MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_Artifact_Manifest.csv"

GRID = (15,50,50)
NCELL = 37500
NCVTOTAL = 215600
EXPECTED_E2 = 3091073
INJECTED = 0.80
TARGET_ALPHA_INDEX = 4
LINE_DEN = 1024
TARGET_ALPHA = TARGET_ALPHA_INDEX / LINE_DEN
S_MIN = 0.20
S_MAX = 0.80
TANGENT_TOL = 1.0e-8
PRESSURE_TOL = 1.0e-8
FEAS_UNSERVED_TOL = 1.0e-6
FEAS_CV_LINF_TOL = 1.0e-6
FEAS_CAP_EXCESS_TOL = 1.0e-6
CUT_MATCH_TOL = 2.0e-5
EXPECTED_RAW_UNSERVED = 0.20799761993202992
EXPECTED_PROJECTED_CUT_DEFICIT = -0.024434776074485853
FLOW_POSITIVE_TOL = 1.0e-9


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,capture_output=True
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root,"hash-object",str(path))


def cut_identity(cv_ids: np.ndarray, cell_ids: np.ndarray) -> str:
    import hashlib
    h=hashlib.sha256()
    h.update(np.asarray(cv_ids,dtype=np.int64).tobytes(order="C"))
    h.update(b"|")
    h.update(np.asarray(cell_ids,dtype=np.int64).tobytes(order="C"))
    return h.hexdigest()


def residual_min_cut_general(
    *,
    active_cv: np.ndarray,
    active_cell: np.ndarray,
    x: np.ndarray,
    u: np.ndarray,
    demand: np.ndarray,
    available: np.ndarray,
) -> tuple[np.ndarray,np.ndarray,dict[str,Any]]:
    cut_cv=np.asarray(u>FEAS_UNSERVED_TOL,dtype=bool)
    cut_cell=np.zeros(NCELL,dtype=bool)
    if not np.any(cut_cv):
        raise GateError("residual_min_cut_requested_without_unserved_source_CV")

    positive_flow=np.asarray(x>FLOW_POSITIVE_TOL,dtype=bool)
    iterations=0
    while True:
        iterations+=1
        if iterations>NCVTOTAL+NCELL:
            raise GateError("residual_cut_closure_nontermination")

        edge_from_cut_cv=cut_cv[active_cv]
        new_cells=np.zeros(NCELL,dtype=bool)
        if np.any(edge_from_cut_cv):
            new_cells[np.unique(active_cell[edge_from_cut_cv])]=True
        updated_cells=cut_cell|new_cells

        reverse=updated_cells[active_cell]&positive_flow
        new_cvs=np.zeros(NCVTOTAL,dtype=bool)
        if np.any(reverse):
            new_cvs[np.unique(active_cv[reverse])]=True
        updated_cvs=cut_cv|new_cvs

        if np.array_equal(updated_cells,cut_cell) and np.array_equal(updated_cvs,cut_cv):
            break
        cut_cell=updated_cells
        cut_cv=updated_cvs

    cut_demand=float(np.sum(demand[cut_cv]))
    cut_capacity=float(np.sum(available[cut_cell]))
    mapped=np.bincount(active_cell,weights=x,minlength=NCELL).astype(np.float64)
    slack=available[cut_cell]-mapped[cut_cell]
    return cut_cv,cut_cell,{
        "closure_iterations":iterations,
        "cut_CV_count":int(np.count_nonzero(cut_cv)),
        "cut_cell_count":int(np.count_nonzero(cut_cell)),
        "cut_demand_kg":cut_demand,
        "cut_capacity_kg":cut_capacity,
        "cut_deficit_kg":cut_demand-cut_capacity,
        "maximum_source_reachable_cell_residual_capacity_kg":
            float(np.max(slack)) if slack.size else 0.0,
    }


def solve_box_multicut_qp(
    highspy,
    G: np.ndarray,
    a: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    output_flag: bool=False,
) -> tuple[np.ndarray,dict[str,Any]]:
    G=np.asarray(G,dtype=np.float64)
    a=np.asarray(a,dtype=np.float64).reshape(-1)
    lo=np.asarray(lo,dtype=np.float64).reshape(-1)
    hi=np.asarray(hi,dtype=np.float64).reshape(-1)
    m,n=G.shape
    if a.shape!=(m,) or lo.shape!=(n,) or hi.shape!=(n,):
        raise GateError("QP_shape_mismatch")
    if np.any(lo>hi):
        raise ScientificFail("QP_variable_bounds_infeasible",{"max_lo_minus_hi":float(np.max(lo-hi))})

    model=highspy.HighsModel()
    model.lp_.num_col_=n
    model.lp_.num_row_=m
    model.lp_.sense_=highspy.ObjSense.kMinimize
    model.lp_.col_cost_=np.zeros(n,dtype=np.double)
    model.lp_.col_lower_=lo.astype(np.double)
    model.lp_.col_upper_=hi.astype(np.double)
    model.lp_.row_lower_=np.full(m,-highspy.kHighsInf,dtype=np.double)
    model.lp_.row_upper_=(-a).astype(np.double)
    model.lp_.a_matrix_.format_=highspy.MatrixFormat.kColwise

    starts=[0]
    indices=[]
    values=[]
    for j in range(n):
        col=G[:,j]
        nz=np.flatnonzero(col!=0.0)
        indices.extend(int(i) for i in nz)
        values.extend(float(col[i]) for i in nz)
        starts.append(len(indices))
    model.lp_.a_matrix_.start_=np.asarray(starts,dtype=np.int32)
    model.lp_.a_matrix_.index_=np.asarray(indices,dtype=np.int32)
    model.lp_.a_matrix_.value_=np.asarray(values,dtype=np.double)

    model.hessian_.dim_=n
    model.hessian_.format_=highspy.HessianFormat.kTriangular
    model.hessian_.start_=np.arange(n+1,dtype=np.int32)
    model.hessian_.index_=np.arange(n,dtype=np.int32)
    model.hessian_.value_=np.ones(n,dtype=np.double)

    h=highspy.Highs()
    h.setOptionValue("output_flag",bool(output_flag))
    status=h.passModel(model)
    if str(status).endswith("kError"):
        raise GateError("highs_QP_passModel_error")
    h.run()
    model_status=h.getModelStatus()
    status_text=h.modelStatusToString(model_status)
    if status_text!="Optimal":
        if "Infeasible" in status_text:
            raise ScientificFail("active_set_QP_infeasible",{"model_status":status_text})
        raise GateError(f"highs_QP_nonoptimal_status:{status_text}")
    sol=np.asarray(h.getSolution().col_value,dtype=np.float64)
    info=h.getInfo()
    row_activity=G@sol
    return sol,{
        "model_status":status_text,
        "objective":float(0.5*np.dot(sol,sol)),
        "run_time_s":float(h.getRunTime()),
        "qp_iteration_count":int(getattr(info,"qp_iteration_count",0)),
        "max_row_excess":float(np.max(row_activity+a)) if m else 0.0,
        "max_lower_bound_violation":float(np.max(lo-sol)) if n else 0.0,
        "max_upper_bound_violation":float(np.max(sol-hi)) if n else 0.0,
    }


def highs_qp_self_test(highspy) -> dict[str,Any]:
    # min 0.5 ||q||^2 s.t. q0+q1 <= -1, -2<=q<=2.
    q,tel=solve_box_multicut_qp(
        highspy,
        np.asarray([[1.0,1.0]]),
        np.asarray([1.0]),
        np.asarray([-2.0,-2.0]),
        np.asarray([2.0,2.0]),
        output_flag=False,
    )
    err=float(np.max(np.abs(q-np.asarray([-0.5,-0.5]))))
    if err>1e-8:
        raise GateError(f"highs_QP_self_test_solution_mismatch:{err}")
    return {"solution":q.tolist(),"max_error":err,**tel}


def self_test() -> None:
    assert TARGET_ALPHA_INDEX==4
    assert TARGET_ALPHA==1.0/256.0
    assert EXPECTED_RAW_UNSERVED>0
    print("POSTV16 O3-R6-R4-R3-R5 separation-loop validation structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root=Path(project_root).resolve()
    drive=Path(drive_root).resolve()
    out=drive/OUT
    recovery=drive/RECOVERY
    failed=drive/FAIL
    blocked=drive/BLOCK
    gates:dict[str,dict[str,Any]]={}
    stage="preflight"
    pressure_solve_executed=False
    feasibility_lp_executed=False
    qp_executed=False

    def gate(name:str,cond:bool,detail:Any=None):
        gates[name]={"status":"PASS" if cond else "FAIL","detail":detail}
        if not cond:
            raise GateError(f"{name}: {detail!r}")
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    def sci_gate(name:str,cond:bool,detail:Any=None):
        gates[name]={"status":"PASS" if cond else "FAIL","detail":detail}
        if not cond:
            raise ScientificFail(name,detail)
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    if (out/MANIFEST).is_file():
        print("[PASS] existing immutable R3-R5 PASS detected; no rerun")
        return 0
    fp=failed/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_Scientific_Fail_Report.json"
    if fp.is_file():
        print("[FAIL] existing immutable R3-R5 scientific FAIL detected; automatic rerun prohibited")
        return 3
    bp=blocked/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_Blocked_Report.json"
    if bp.is_file():
        print("[BLOCK] existing immutable R3-R5 technical/authority BLOCK detected")
        return 2

    print("="*214)
    print(MILESTONE+" -- CONTROLLED GENERALIZED ACTIVE-SET ONE-STEP SEPARATION-LOOP VALIDATION")
    print("="*214)
    print("EMPTY ACTIVE-CUT POOL AT ALPHA=1/256.")
    print("ROUND 0: RAW CANDIDATE MUST FAIL EXACT FROZEN-E2 FEASIBILITY.")
    print("SEPARATE RESIDUAL MINIMUM CUT -> ADD CUT -> NATIVE HIGHS BOX-QP -> RECERTIFY SAME ALPHA.")
    print("NO FIVE-STAGE ASSIGNMENT. NO NONLINEAR STATE ACCEPTANCE. NO SUPPORT EXPANSION. NO TIME ADVANCE.")
    print()

    try:
        stage="repository_authority"
        parent=git_text(root,"rev-parse","HEAD^")
        dirty=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R3R4_commit",parent==PARENT_R3R4_COMMIT,parent)
        gate("repository_clean",dirty=="",repr(dirty))
        for fn,expected in {
            R3R4:R3R4_BLOB,R3R3:R3R3_BLOB,R3R1:R3R1_BLOB,R1:R1_BLOB,
            R4:R4_BLOB,R2:R2_BLOB,R3DESIGN:R3DESIGN_BLOB,
        }.items():
            p=root/fn
            actual=git_blob(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        r3r4=load_module(root/R3R4,"postv16_r3r5_r3r4")
        r3r3=load_module(root/R3R3,"postv16_r3r5_r3r3")
        r3r1=load_module(root/R3R1,"postv16_r3r5_r3r1")
        r1=load_module(root/R1,"postv16_r3r5_r1")
        r4=load_module(root/R4,"postv16_r3r5_r4")
        r2=load_module(root/R2,"postv16_r3r5_r2")
        r3design=load_module(root/R3DESIGN,"postv16_r3r5_r3design")
        o3r4=load_module(root/r4.O3R4,"postv16_r3r5_o3r4")
        o3r6=load_module(root/r4.O3R6,"postv16_r3r5_o3r6")
        a2e=load_module(root/r4.A2E,"postv16_r3r5_a2e")
        r2phys=load_module(root/r4.R2PHYS,"postv16_r3r5_r2phys")
        sg2=load_module(root/r4.SG2,"postv16_r3r5_sg2")
        sg3=load_module(root/r4.SG3,"postv16_r3r5_sg3")
        r3r2r1=load_module(root/r4.R3R2R1,"postv16_r3r5_r3r2r1")

        import highspy
        from scipy.sparse import coo_matrix
        gate("highspy_version_exact_1_15_1",highspy.Highs().version()=="1.15.1",highspy.Highs().version())

        stage="highs_QP_self_test"
        qp_test=highs_qp_self_test(highspy)
        gate("native_HiGHS_QP_API_solution_self_test",True,qp_test)

        stage="R3R4_contract_binding"
        d34=drive/r3r4.OUT
        gate("R3R4_output_present",d34.is_dir(),str(d34))
        r3design.verify_manifest(d34,r3r4.MANIFEST)
        s34=r3design.load_json(d34/r3r4.SUMMARY)
        dec34=r3design.load_json(d34/r3r4.DECISION)
        gate(
            "R3R4_PASS_exact",
            s34.get("status")==r3r4.STATUS_PASS
            and s34.get("generalized_active_set") is True
            and s34.get("multi_cut_QP") is True
            and s34.get("R3R5_one_step_validation_authorized") is True
            and s34.get("full_generalized_solver_execution_authorized") is False
            and s34.get("generalized_execution_performed") is False,
        )
        gate(
            "R3R4_authorizes_R3R5_only",
            dec34.get("O3R6R4R3R5_one_step_active_set_validation_authorized") is True
            and dec34.get("O3R6R4R3R5_full_fixed_point_execution_authorized") is False
            and dec34.get("O3R6R4R3R5_five_stage_assignment_authorized") is False
            and dec34.get("full_generalized_solver_execution_authorized") is False
            and dec34.get("support_expansion_authorized") is False
            and dec34.get("O3R7_authorized") is False,
        )

        stage="reference_contract_binding"
        d33=drive/R3R3_REL
        r3design.verify_manifest(d33,r3r3.MANIFEST)
        s33=r3design.load_json(d33/r3r3.SUMMARY)
        gate(
            "R3R3_reference_alpha_1_over_256_exact",
            int(s33.get("selected_alpha_index",-1))==TARGET_ALPHA_INDEX
            and abs(float(s33.get("selected_alpha"))-TARGET_ALPHA)<=1e-15
            and float(s33.get("selected_minimum_unserved_mass_kg"))==0.0
            and abs(float(s33.get("selected_cut_signed_deficit_kg"))-EXPECTED_PROJECTED_CUT_DEFICIT)<=1e-12,
        )

        # Cut IDs/demand from R2 frozen contract.
        d2=drive/r2.OUT
        r3design.verify_manifest(d2,r2.MANIFEST)
        op2=r3design.load_json(d2/r2.OPERATOR)
        ref_cut_cv=np.asarray(op2["cut_definition"]["CV_ids"],dtype=np.int64)
        ref_cut_cell=np.asarray(op2["cut_definition"]["cell_ids"],dtype=np.int64)
        ref_cut_id=cut_identity(ref_cut_cv,ref_cut_cell)
        gate(
            "reference_cut_exact_67_CV_24_cell",
            ref_cut_cv.size==67 and ref_cut_cell.size==24 and 60424 in ref_cut_cv.tolist(),
            {"cut_id":ref_cut_id},
        )

        stage="immutable_state_binding"
        o2d=drive/r4.O2_REL
        r3design.verify_manifest(o2d,r4.O2_MANIFEST)
        with np.load(o2d/r4.O2_STATE,allow_pickle=False) as z:
            demand=np.asarray(z["event_CV_component_mass_kg"],dtype=np.float64).reshape(-1)
            e2_cv=np.asarray(z["E2_pair_cv_id"],dtype=np.int64)
            e2_cell=np.asarray(z["E2_pair_flat_cell"],dtype=np.int64)
            residual_grid=np.asarray(z["frozen_residual_grid_component_mass_kg"],dtype=np.float64)
            grid_pv=np.asarray(z["grid_pore_volume_m3"],dtype=np.float64)
            p_ref=float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
        residual=residual_grid.reshape(-1)
        gate(
            "O2_shapes_exact",
            demand.shape==(NCVTOTAL,) and e2_cv.shape==(EXPECTED_E2,)
            and e2_cell.shape==(EXPECTED_E2,) and grid_pv.shape==GRID,
        )

        a2d=drive/r4.A2E_REL
        r3design.verify_manifest(a2d,r4.A2E_MANIFEST)
        with np.load(a2d/r4.A2E_EPOCH,allow_pickle=False) as z:
            epoch={k:np.asarray(z[k]).copy() for k in z.files}
        grid_nw=np.asarray(epoch["nw"],dtype=np.float64)
        grid_no=np.asarray(epoch["no"],dtype=np.float64)
        grid_krw=np.asarray(epoch["krw_max"],dtype=np.float64)
        grid_kro=np.asarray(epoch["kro_max"],dtype=np.float64)

        r4rec=drive/R4_RECOVERY
        bdir=r4.recovery_dir(r4rec,"accepted_iterates",0)
        bsn,bmn,bman=r4.accepted_names(0)
        gate("R4_base_checkpoint_valid",r4.manifest_valid(r3design,bdir,bman,{bsn,bmn}),str(bdir))
        with np.load(bdir/bsn,allow_pickle=False) as z:
            S_base=np.asarray(z["S_iter_next"],dtype=np.float64)

        mdir=r4.recovery_dir(r4rec,"physical_maps",1)
        msn,mmn,mman=r4.map_names(1)
        gate("R4_map_checkpoint_valid",r4.manifest_valid(r3design,mdir,mman,{msn,mmn}),str(mdir))
        with np.load(mdir/msn,allow_pickle=False) as z:
            S_iter_map=np.asarray(z["S_iter"],dtype=np.float64)
            S_map=np.asarray(z["S_map"],dtype=np.float64)
        gate("R4_base_map_pair_exact",r4.array_sha256(S_base)==r4.array_sha256(S_iter_map))
        d_raw=S_map-S_base

        # Reuse immutable R3 g for known cut after separation proves identity.
        probe_root=drive/R3_RECOVERY/"sensitivity_probes"
        g_ref=np.zeros(ref_cut_cell.size,dtype=np.float64)
        # Load the immutable R3 one-step source explicitly for checkpoint naming/validation.
        r3test=load_module(root/r3r3.R3,"postv16_r3r5_r3test")
        for local_index,cell in enumerate(ref_cut_cell):
            pn,pm=r3test.probe_names(local_index,int(cell))
            pd=probe_root/f"probe_{local_index:02d}_cell_{int(cell):05d}"
            gate(
                f"reference_probe_{local_index:02d}_valid",
                r3test.checkpoint_manifest_valid(r3design,pd,pm,{pn}),
                str(pd),
            )
            rec=r3design.load_json(pd/pn)
            g_ref[local_index]=float(rec["sensitivity_kg_per_saturation"])
        gate(
            "reference_g_norms_exact",
            abs(float(np.linalg.norm(g_ref))-1.2493304995770507)<=1e-12
            and abs(float(np.max(np.abs(g_ref)))-0.7448965334333478)<=1e-12,
        )

        stage="pressure_physics_setup"
        permeability_md=np.loadtxt(root/r4.PERM,skiprows=1,dtype=np.float64).reshape(GRID,order="C")
        kx,ky,kz=sg2.build_directional_permeability(permeability_md)
        kfx,kfy,kfz=sg2.build_face_permeabilities(kx,ky,kz)
        tx_ref,ty_ref,tz_ref=sg3.construct_si_transmissibilities(kfx,kfy,kfz)

        def pressure_step(S:np.ndarray)->tuple[np.ndarray,float]:
            nonlocal pressure_solve_executed
            mobility=a2e.spatial_mobility(S,grid_nw,grid_no,grid_krw,grid_kro)
            tx,ty,tz,_=r3r2r1.build_updated_transmissibilities(
                sg3,tx_ref,ty_ref,tz_ref,mobility["lambda_total"]
            )
            A,b,_=r3r2r1.assemble_updated_pressure_system(
                sg3,permeability_md,tx,ty,tz,mobility["lambda_total"]
            )
            _ppa,ppsi,reslin=r3r2r1.solve_updated_pressure(sg3,A,b)
            pressure_solve_executed=True
            return np.asarray(ppsi,dtype=np.float64),float(reslin)

        def capacity(S:np.ndarray):
            p,pres=pressure_step(S)
            cap=np.asarray(
                a2e.local_mass(r2phys,np.full(GRID,INJECTED),p,p_ref,grid_pv),
                dtype=np.float64,
            )
            avail_raw=cap.reshape(-1)-residual
            cap_tol=max(1e-8,1e-12*max(float(np.max(np.abs(cap))),1.0))
            if float(np.min(avail_raw)) < -cap_tol:
                raise ScientificFail(
                    "residual_sidecar_capacity",
                    {"minimum_available_mapped_capacity_kg":float(np.min(avail_raw))}
                )
            return p,cap,pres,np.maximum(avail_raw,0.0)

        def exact_lp(available:np.ndarray):
            nonlocal feasibility_lp_executed
            lp,active,cv_e,cell_e,nedge,nnz=o3r4.build_feasibility_lp(
                highspy,coo_matrix,e2_cv,e2_cell,demand,available
            )
            x,u,tel=o3r4.run_highs_feasibility(highspy,lp,nedge)
            del lp
            gc.collect()
            feasibility_lp_executed=True
            assigned=np.bincount(cv_e,weights=x,minlength=NCVTOTAL).astype(np.float64)
            mapped=np.bincount(cell_e,weights=x,minlength=NCELL).astype(np.float64)
            cv_linf=float(np.max(np.abs(assigned+u-demand)))
            cap_excess=float(np.max(mapped-available))
            sci_gate(
                "exact_LP_numerical_certification",
                cv_linf<=FEAS_CV_LINF_TOL and cap_excess<=FEAS_CAP_EXCESS_TOL,
                {"CV_Linf_kg":cv_linf,"capacity_excess_kg":cap_excess},
            )
            return x,u,cv_e,cell_e,float(np.sum(u)),cv_linf,cap_excess,tel

        round_rows=[]

        # Round 0: empty pool, q=0, raw alpha candidate.
        stage="round0_empty_pool_raw_candidate"
        S_raw=S_base+TARGET_ALPHA*d_raw
        p_raw,cap_raw,pres_raw,avail_raw=capacity(S_raw)
        sci_gate("round0_pressure_residual",pres_raw<PRESSURE_TOL,pres_raw)
        x0,u0,cv_e0,cell_e0,obj0,cv0,ce0,tel0=exact_lp(avail_raw)
        sci_gate(
            "round0_raw_candidate_is_infeasible",
            obj0>FEAS_UNSERVED_TOL,
            obj0,
        )
        gate(
            "round0_reproduces_R4_raw_alpha_1_over_256",
            abs(obj0-EXPECTED_RAW_UNSERVED)<=1e-6,
            {"reconstructed":obj0,"R4_checkpoint":EXPECTED_RAW_UNSERVED},
        )

        cut_cv_mask,cut_cell_mask,cut_meta=residual_min_cut_general(
            active_cv=cv_e0,active_cell=cell_e0,x=x0,u=u0,demand=demand,available=avail_raw
        )
        cut_cv=np.flatnonzero(cut_cv_mask).astype(np.int64)
        cut_cell=np.flatnonzero(cut_cell_mask).astype(np.int64)
        discovered_id=cut_identity(cut_cv,cut_cell)
        gate(
            "round0_cut_deficit_matches_LP",
            abs(float(cut_meta["cut_deficit_kg"])-obj0)<=CUT_MATCH_TOL,
            {"cut_deficit":cut_meta["cut_deficit_kg"],"LP":obj0},
        )
        gate(
            "round0_discovered_cut_matches_known_R1R1_controlling_cut",
            discovered_id==ref_cut_id
            and np.array_equal(cut_cv,ref_cut_cv)
            and np.array_equal(cut_cell,ref_cut_cell),
            {"discovered_cut_id":discovered_id,"reference_cut_id":ref_cut_id,
             "cut_CVs":int(cut_cv.size),"cut_cells":int(cut_cell.size)},
        )
        round_rows.append({
            "round":0,"active_cut_count_before":0,"alpha":TARGET_ALPHA,
            "q_L2":0.0,"minimum_unserved_mass_kg":obj0,
            "exact_frozen_E2_feasible":False,"discovered_cut_id":discovered_id,
            "discovered_cut_CVs":int(cut_cv.size),"discovered_cut_cells":int(cut_cell.size),
        })

        # Current-state secant slope for discovered cut using base and epsilon raw probe.
        stage="cut_secant_and_QP"
        p_base,cap_base,pres_base,avail_base=capacity(S_base)
        sci_gate("base_pressure_residual",pres_base<PRESSURE_TOL,pres_base)
        eps=1.0/LINE_DEN
        S_eps=S_base+eps*d_raw
        p_eps,cap_eps,pres_eps,avail_eps=capacity(S_eps)
        sci_gate("epsilon_pressure_residual",pres_eps<PRESSURE_TOL,pres_eps)
        cut_demand=float(np.sum(demand[cut_cv]))
        D0=cut_demand-float(np.sum(avail_base[cut_cell]))
        D_eps=cut_demand-float(np.sum(avail_eps[cut_cell]))
        a_cut=(D_eps-D0)/eps
        gate(
            "discovered_cut_raw_secant_matches_R3_reference",
            abs(a_cut-53.3337138146162)<=1e-6,
            a_cut,
        )

        # One active cut; QP uses the generalized multi-cut machinery.
        sb=S_base.reshape(-1)[cut_cell]
        dr=d_raw.reshape(-1)[cut_cell]
        lo=(S_MIN-sb)/TARGET_ALPHA-dr
        hi=(S_MAX-sb)/TARGET_ALPHA-dr
        G=g_ref.reshape(1,-1)
        a_vec=np.asarray([a_cut],dtype=np.float64)
        q,qp_tel=solve_box_multicut_qp(highspy,G,a_vec,lo,hi,output_flag=False)
        qp_executed=True
        sci_gate(
            "QP_cut_row_satisfied",
            a_cut+float(np.dot(g_ref,q))<=TANGENT_TOL,
            a_cut+float(np.dot(g_ref,q)),
        )
        sci_gate(
            "QP_bounds_satisfied",
            float(np.max(lo-q))<=1e-10 and float(np.max(q-hi))<=1e-10,
            {"lower_violation":float(np.max(lo-q)),"upper_violation":float(np.max(q-hi))},
        )

        # Cross-check generalized QP against prior R3-R3 alpha=1/256 validated candidate.
        ref_dir=drive/R3R3_REL/"../"  # unused; checkpoint is in R3R3 recovery
        cand_dir=drive/r3r3.RECOVERY/"candidates"/f"alpha_{TARGET_ALPHA_INDEX:04d}_of_{LINE_DEN}"
        csn,crn,cmn=r3r3.candidate_names(TARGET_ALPHA_INDEX)
        gate(
            "R3R3_alpha_1_over_256_checkpoint_valid",
            r3r3.checkpoint_valid(r3design,cand_dir,cmn,{csn,crn}),
            str(cand_dir),
        )
        with np.load(cand_dir/csn,allow_pickle=False) as z:
            q_ref=np.asarray(z["q_alpha"],dtype=np.float64)
            S_ref=np.asarray(z["S_trial"],dtype=np.float64)
        gate(
            "generalized_QP_reproduces_prior_one_cut_q",
            float(np.max(np.abs(q-q_ref)))<=1e-7,
            float(np.max(np.abs(q-q_ref))),
        )

        # Round 1: same alpha, active cut included, recertify exact nonlinear candidate.
        stage="round1_projected_candidate_recertification"
        dproj=d_raw.reshape(-1).copy()
        dproj[cut_cell]+=q
        S_proj=(S_base.reshape(-1)+TARGET_ALPHA*dproj).reshape(GRID)
        sci_gate(
            "round1_saturation_box",
            float(np.min(S_proj))>=S_MIN-1e-10 and float(np.max(S_proj))<=S_MAX+1e-10,
            {"min":float(np.min(S_proj)),"max":float(np.max(S_proj))},
        )
        gate(
            "round1_trial_matches_R3R3_reference",
            float(np.max(np.abs(S_proj-S_ref)))<=1e-8,
            float(np.max(np.abs(S_proj-S_ref))),
        )
        p1,cap1,pres1,avail1=capacity(S_proj)
        sci_gate("round1_pressure_residual",pres1<PRESSURE_TOL,pres1)
        x1,u1,cv_e1,cell_e1,obj1,cv1,ce1,tel1=exact_lp(avail1)
        sci_gate(
            "round1_projected_candidate_exactly_feasible",
            obj1<=FEAS_UNSERVED_TOL,
            obj1,
        )
        cut_deficit1=cut_demand-float(np.sum(avail1[cut_cell]))
        gate(
            "round1_cut_has_positive_slack",
            cut_deficit1<0.0,
            cut_deficit1,
        )
        gate(
            "round1_matches_R3R3_projected_result",
            abs(obj1-0.0)<=1e-12
            and abs(cut_deficit1-EXPECTED_PROJECTED_CUT_DEFICIT)<=1e-8,
            {"unserved":obj1,"cut_deficit":cut_deficit1},
        )
        round_rows.append({
            "round":1,"active_cut_count_before":1,"alpha":TARGET_ALPHA,
            "q_L2":float(np.linalg.norm(q)),"minimum_unserved_mass_kg":obj1,
            "exact_frozen_E2_feasible":True,"discovered_cut_id":None,
            "discovered_cut_CVs":None,"discovered_cut_cells":None,
        })

        stage="final_certification"
        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "validation_alpha_index":TARGET_ALPHA_INDEX,
            "validation_alpha":TARGET_ALPHA,
            "initial_active_cut_pool_empty":True,
            "round0_minimum_unserved_mass_kg":obj0,
            "round0_cut_identity":discovered_id,
            "round0_cut_CV_count":int(cut_cv.size),
            "round0_cut_cell_count":int(cut_cell.size),
            "round0_cut_matches_R1R1_reference":True,
            "active_cut_added_after_round0":True,
            "native_HiGHS_QP_executed":True,
            "QP_q_L2":float(np.linalg.norm(q)),
            "QP_q_Linf":float(np.max(np.abs(q))),
            "round1_minimum_unserved_mass_kg":obj1,
            "round1_exact_frozen_E2_feasible":True,
            "round1_cut_signed_deficit_kg":cut_deficit1,
            "same_alpha_recertified_after_cut_addition":True,
            "separation_loop_round_count":2,
            "pressure_solve_executed":bool(pressure_solve_executed),
            "feasibility_LP_executed":bool(feasibility_lp_executed),
            "QP_executed":bool(qp_executed),
            "five_stage_assignment_executed":False,
            "nonlinear_state_accepted":False,
            "support_domain_changed":False,
            "capacity_relaxed":False,
            "per_CV_mass_relaxed":False,
            "physical_time_advanced":False,
        }

        cut_json={
            "milestone":MILESTONE,
            "cut_identity":discovered_id,
            "cut_CV_ids":[int(v) for v in cut_cv],
            "cut_cell_ids":[int(v) for v in cut_cell],
            "cut_demand_kg":cut_demand,
            "round0_cut_capacity_kg":float(cut_meta["cut_capacity_kg"]),
            "round0_cut_deficit_kg":float(cut_meta["cut_deficit_kg"]),
            "base_cut_deficit_kg":D0,
            "epsilon_raw_cut_deficit_kg":D_eps,
            "raw_secant_slope_kg_per_full_step":a_cut,
            "round1_projected_cut_deficit_kg":cut_deficit1,
            "matches_R1R1_reference_cut":True,
        }

        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "scientific_interpretation":(
                "Starting from an empty active-cut pool at alpha=1/256, the exact "
                "frozen-E2 LP reproduced the known raw-candidate infeasibility, the "
                "residual network independently rediscovered the controlling cut, "
                "the generalized native-HiGHS box-QP reproduced the validated one-cut "
                "projection, and exact pressure/capacity plus frozen-E2 recertification "
                "made the same alpha candidate feasible with zero unserved mass. "
                "This validates the active-set separation/add/project/recertify loop "
                "for the immutable R4 iteration-1 base/map pair."
            ),
            "next_milestone":(
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3-R6 — "
                "controlled full generalized active-set box-constrained projected "
                "same-time coupled fixed-point execution"
            ),
            "O3R6R4R3R6_full_generalized_execution_authorized":True,
            "O3R6R4R3R6_must_use_frozen_R3R4_semantics":True,
            "O3R6R4R3R6_five_stage_assignment_authorized":True,
            "O3R6R4R3R6_physical_time_advance_authorized":False,
            "automatic_R3R5_rerun_authorized":False,
            "sub_1_over_1024_step_authorized":False,
            "support_expansion_authorized":False,
            "capacity_relaxation_authorized":False,
            "per_CV_mass_relaxation_authorized":False,
            "O3R7_authorized":False,
            "R3R3R4_authorized":False,
            "F5_dataset_generation_authorized":False,
            "training_authorized":False,
        }

        state={
            "S_base":S_base,
            "S_map":S_map,
            "d_raw":d_raw,
            "raw_trial_alpha_1_over_256":S_raw,
            "discovered_cut_CV_ids":cut_cv,
            "discovered_cut_cell_ids":cut_cell,
            "discovered_cut_sensitivity_g":g_ref,
            "QP_q":q,
            "projected_trial_alpha_1_over_256":S_proj,
            "projected_pressure_psi":p1,
            "projected_cell_capacity_kg":cap1,
            "projected_available_mapped_capacity_kg":avail1.reshape(GRID),
        }

        r3design.immutable_publish(
            out,
            {
                SUMMARY:r3design.json_bytes(summary),
                STATE:o3r6.deterministic_npz_bytes(state),
                CUT_JSON:r3design.json_bytes(cut_json),
                ROUNDS_CSV:r3design.csv_bytes(round_rows),
                DECISION:r3design.json_bytes(decision),
                GATES:r3design.csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
            }
        )
        rows=[
            {"file":p.name,"sha256":r3design.sha256_file(p),"bytes":p.stat().st_size}
            for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST
        ]
        r3design.immutable_publish(out,{MANIFEST:r3design.csv_bytes(rows)})

        print()
        print("="*214)
        print(MILESTONE+": SEPARATION-LOOP VALIDATION PASS")
        print("="*214)
        print("Validation alpha                  :",TARGET_ALPHA_INDEX,"/",LINE_DEN,"=",TARGET_ALPHA)
        print("Round 0 active cuts              : 0")
        print("Round 0 raw min unserved kg      :",obj0)
        print("Discovered cut CV / cell count   :",int(cut_cv.size),"/",int(cut_cell.size))
        print("Cut matches R1-R1 reference      : True")
        print("Native HiGHS box-QP executed     : True")
        print("Round 1 projected min unserved   :",obj1)
        print("Same alpha recertified feasible  : True")
        print("Five-stage assignment            : False")
        print("Full generalized R3-R6 execution : AUTHORIZED")
        print("O3-R7                            : NOT AUTHORIZED")
        print("="*214)
        return 0

    except ScientificFail as exc:
        failed.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":MILESTONE,"status":STATUS_FAIL,
            "failed_stage":stage,"failed_gate":exc.gate,"detail":exc.detail,
            "gates":gates,
            "pressure_solve_executed":bool(pressure_solve_executed),
            "feasibility_LP_executed":bool(feasibility_lp_executed),
            "QP_executed":bool(qp_executed),
            "five_stage_assignment_executed":False,
            "nonlinear_state_accepted":False,
            "support_domain_changed":False,
            "physical_time_advanced":False,
            "automatic_rerun_authorized":False,
            "O3R7_authorized":False,
        }
        p=failed/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_bytes((json.dumps(report,indent=2,sort_keys=True)+"\n").encode())
        print()
        print(MILESTONE+": SCIENTIFIC FAIL")
        print("Stage:",stage); print("Gate:",exc.gate); print("Detail:",exc.detail)
        return 3

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":MILESTONE,"status":STATUS_BLOCK,
            "failed_stage":stage,"exception":repr(exc),"gates":gates,
            "pressure_solve_executed":bool(pressure_solve_executed),
            "feasibility_LP_executed":bool(feasibility_lp_executed),
            "QP_executed":bool(qp_executed),
            "five_stage_assignment_executed":False,
            "nonlinear_state_accepted":False,
            "support_domain_changed":False,
            "physical_time_advanced":False,
            "automatic_rerun_authorized":False,
            "O3R7_authorized":False,
        }
        p=blocked/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_Blocked_Report.json"
        if not p.exists():
            p.write_bytes((json.dumps(report,indent=2,sort_keys=True)+"\n").encode())
        print()
        print(MILESTONE+": TECHNICAL / AUTHORITY BLOCK")
        print("Stage:",stage); print("Exception:",repr(exc))
        return 2


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()


if __name__=="__main__":
    args=parse_args()
    if args.self_test:
        self_test(); raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))
