#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3-R6"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R4R3R6_CONTROLLED_FULL_GENERALIZED_ACTIVE_SET_"
    "BOX_CONSTRAINED_PROJECTED_SAME_TIME_COUPLED_FIXED_POINT_EXECUTION_PASS_"
    "ORIGINAL_UNDAMPED_FIXED_POINT_AND_FINAL_CLOSURE_CERTIFIED_NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_FAIL = (
    "AV4F4R3R3R3R3R3O3R6R4R3R6_CONTROLLED_FULL_GENERALIZED_ACTIVE_SET_"
    "BOX_CONSTRAINED_PROJECTED_SAME_TIME_COUPLED_FIXED_POINT_EXECUTION_SCIENTIFIC_FAIL_"
    "NO_AUTOMATIC_RERUN_NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R4R3R6_TECHNICAL_OR_AUTHORITY_BLOCK"

PARENT_R3R5_COMMIT = "efbf0dc28744c77c3fc4446e66e5b21eba74c36c"

R3R5 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_"
    "Controlled_Generalized_ActiveSet_OneStep_SeparationLoop_Validation.py"
)
R3R5_BLOB = "998a20144e071c8ecca026882ac1d908438e7712"
R3R4 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_"
    "Generalized_ActiveSet_BoxConstrained_Projected_CoupledSolver_Semantics_Design_Freeze.py"
)
R3R4_BLOB = "621f77be6dd691fe457751bb91635a9aac39a7e5"
R4 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_"
    "Controlled_Adaptive_Feasibility_Preserving_Stabilized_Coupled_Execution.py"
)
R4_BLOB = "c41cd5c78e7cc2d91e1920e538f1793037961a31"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
EVENT_DAY = 413.78677770818403

GRID = (15, 50, 50)
NCELL = 37500
NCVTOTAL = 215600
EXPECTED_E0 = 269721
EXPECTED_E2 = 3091073
EXPECTED_ACTIVE = 3012452
BACKGROUND = 0.20
INJECTED = 0.80

MAX_NONLINEAR_ITERATIONS = 100
LINE_DEN = 1024
ALPHA_INDICES = [1024,512,256,128,64,32,16,8,4,2,1]
MIN_ALPHA_INDEX = 1
MAX_ACTIVE_CUT_ROUNDS_PER_ALPHA = 32
SENSITIVITY_STEP = 1.0e-5
RAW_SECANT_EPSILON = 1.0/1024.0

PRESSURE_REL_L2_TOL = 1.0e-10
SATURATION_LINF_TOL = 1.0e-10
PROJECTION_LINF_TOL = 1.0e-12
PRESSURE_LINEAR_REL_RESIDUAL_MAX = 1.0e-8
GLOBAL_MASS_REL_TOL = 1.0e-10

FEAS_UNSERVED_TOL_KG = 1.0e-6
FEAS_CV_LINF_TOL_KG = 1.0e-6
FEAS_CAP_EXCESS_TOL_KG = 1.0e-6
CUT_MATCH_TOL_KG = 2.0e-5
TANGENT_ROW_TOL = 1.0e-8

R3R5_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R5_"
    "Controlled_Generalized_ActiveSet_OneStep_SeparationLoop_Validation"
)
R3R4_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_"
    "Generalized_ActiveSet_BoxConstrained_Projected_CoupledSolver_Semantics_Design_Freeze"
)
R4_RECOVERY_REL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Recovery_Checkpoints"
R4_FAIL_REL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_SCIENTIFIC_FAIL"

OUT_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_"
    "Controlled_Full_Generalized_ActiveSet_BoxConstrained_Projected_SameTime_Coupled_FixedPoint_Execution"
)
RECOVERY_REL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Recovery_Checkpoints"
FAIL_REL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_SCIENTIFIC_FAIL"
BLOCK_REL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_BLOCKED"

FINAL_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Summary.json"
FINAL_STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Certified_Nonlinear_Fixed_Point_State.npz"
FINAL_NONLIN = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Nonlinear_Telemetry.csv"
FINAL_ASSIGN = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Assignment_Stage_Telemetry.csv"
FINAL_GLOBAL = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Globalization_Telemetry.csv"
FINAL_CUTS = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Active_Cut_Telemetry.csv"
FINAL_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Decision_Contract.json"
FINAL_GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Final_Gate_Matrix.csv"
FINAL_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Artifact_Manifest.csv"


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
        ["git", "-C", str(root), *args],
        check=True, text=True, capture_output=True
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def array_sha256(a: np.ndarray) -> str:
    aa = np.ascontiguousarray(np.asarray(a))
    h = hashlib.sha256()
    h.update(str(aa.dtype).encode("ascii"))
    h.update(b"|")
    h.update(repr(tuple(aa.shape)).encode("ascii"))
    h.update(b"|")
    h.update(memoryview(aa).cast("B"))
    return h.hexdigest()


def stage_names(iteration: int, stage: int) -> tuple[str,str,str,str]:
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_"
        f"Iteration_{iteration:03d}_Stage_{stage}"
    )
    return stem+"_Resume_State.npz", stem+"_Resume_Metadata.json", stem+"_HiGHS_Basis.bas", stem+"_Manifest.csv"


def map_names(iteration: int) -> tuple[str,str,str]:
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_"
        f"Iteration_{iteration:03d}_Physical_Map_Candidate"
    )
    return stem+".npz", stem+".json", stem+"_Manifest.csv"


def accepted_names(iteration: int) -> tuple[str,str,str]:
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_"
        f"Iteration_{iteration:03d}_Computational_Iterate_Accepted"
    )
    return stem+".npz", stem+".json", stem+"_Manifest.csv"


def recovery_dir(root: Path, kind: str, iteration: int) -> Path:
    return root / kind / f"iteration_{iteration:03d}"


def manifest_valid(r3, d: Path, manifest_name: str, expected: set[str]) -> bool:
    if not d.is_dir() or not (d/manifest_name).is_file():
        return False
    try:
        return set(r3.verify_manifest(d,manifest_name)) == expected
    except Exception:
        return False


def cut_key(cv_ids: np.ndarray, cell_ids: np.ndarray) -> str:
    h=hashlib.sha256()
    h.update(np.asarray(cv_ids,dtype=np.int64).tobytes(order="C"))
    h.update(b"|")
    h.update(np.asarray(cell_ids,dtype=np.int64).tobytes(order="C"))
    return h.hexdigest()


def candidate_dir(recovery: Path, iteration: int, alpha_idx: int, round_idx: int) -> Path:
    return (
        recovery / "globalization" / f"iteration_{iteration:03d}"
        / f"alpha_{alpha_idx:04d}_of_{LINE_DEN}" / f"round_{round_idx:02d}"
    )


def candidate_names(iteration: int, alpha_idx: int, round_idx: int) -> tuple[str,str,str]:
    stem=(
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_"
        f"Iteration_{iteration:03d}_Alpha_{alpha_idx:04d}_of_{LINE_DEN}_Round_{round_idx:02d}"
    )
    return stem+"_State.npz",stem+"_Result.json",stem+"_Manifest.csv"


def probe_dir(recovery: Path, iteration: int, cell: int) -> Path:
    return recovery/"sensitivity_probes"/f"iteration_{iteration:03d}"/f"cell_{cell:05d}"


def probe_names(iteration: int, cell: int) -> tuple[str,str,str]:
    stem=(
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_"
        f"Iteration_{iteration:03d}_Sensitivity_Cell_{cell:05d}"
    )
    return stem+"_State.npz",stem+"_Metadata.json",stem+"_Manifest.csv"


def self_test() -> None:
    assert ALPHA_INDICES == [1024,512,256,128,64,32,16,8,4,2,1]
    assert RAW_SECANT_EPSILON == 1.0/1024.0
    assert MAX_NONLINEAR_ITERATIONS == 100
    assert len(PARENT_R3R5_COMMIT) == 40
    print("POSTV16 O3-R6-R4-R3-R6 generalized full execution structural self-test: PASS")


def main(project_root: Path, drive_root: Path, verbose_solver: bool=False) -> int:
    root=Path(project_root).resolve()
    drive=Path(drive_root).resolve()
    out=drive/OUT_REL
    recovery=drive/RECOVERY_REL
    failed=drive/FAIL_REL
    blocked=drive/BLOCK_REL
    r4recovery=drive/R4_RECOVERY_REL

    gates:dict[str,dict[str,Any]]={}
    solvers=[]
    pressure_solve_executed=False
    assignment_executed=False
    generalized_iteration_executed=False
    current_iteration=0
    stage="preflight"

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

    if (out/FINAL_MANIFEST).is_file():
        print("[PASS] existing immutable R3-R6 PASS detected; no rerun")
        return 0
    fp=failed/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Scientific_Fail_Report.json"
    if fp.is_file():
        print("[FAIL] existing immutable R3-R6 scientific FAIL detected; automatic rerun prohibited")
        return 3
    bp=blocked/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Blocked_Report.json"
    if bp.is_file():
        print("[BLOCK] existing immutable R3-R6 technical/authority BLOCK detected")
        return 2

    print("="*214)
    print(MILESTONE+" -- CONTROLLED FULL GENERALIZED ACTIVE-SET BOX-CONSTRAINED PROJECTED SAME-TIME COUPLED FIXED-POINT EXECUTION")
    print("="*214)
    print("SAME FROZEN EVENT DAY. FROZEN E2/H2. EXACT FIVE-STAGE PHYSICAL MAPS.")
    print("GENERALIZED ACTIVE-SET / MULTI-CUT BOX-QP GLOBALIZATION.")
    print("FINAL PASS REQUIRES ALPHA=1, VANISHING q, ORIGINAL RAW FIXED POINT, AND FINAL UNDAMPED CLOSURE.")
    print("NO SUPPORT EXPANSION. NO MASS/CAPACITY RELAXATION. NO DARCY/POLLOCK/TOF. NO TIME ADVANCE.")
    print()

    try:
        # ----------------------------------------------------------------------------------
        # Repository / source authority.
        # ----------------------------------------------------------------------------------
        stage="repository_authority"
        parent=git_text(root,"rev-parse","HEAD^")
        dirty=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R3R5_commit",parent==PARENT_R3R5_COMMIT,parent)
        gate("repository_clean",dirty=="",repr(dirty))
        for fn,expected in {R3R5:R3R5_BLOB,R3R4:R3R4_BLOB,R4:R4_BLOB}.items():
            p=root/fn
            actual=git_blob(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        r3r5=load_module(root/R3R5,"postv16_r3r6_r3r5")
        r3r4=load_module(root/R3R4,"postv16_r3r6_r3r4")
        r4=load_module(root/R4,"postv16_r3r6_r4")
        # Route helper exceptions into this milestone's immutable PASS/FAIL/BLOCK semantics.
        r3r5.GateError=GateError
        r3r5.ScientificFail=ScientificFail

        # Bind every immutable helper source required by the R4 exact physical map.
        for fn,expected in r4.SOURCE_BLOBS.items():
            p=root/fn
            actual=git_blob(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        r3=load_module(root/r4.R3,"postv16_r3r6_r3")
        o3r6=load_module(root/r4.O3R6,"postv16_r3r6_o3r6")
        o3r4=load_module(root/r4.O3R4,"postv16_r3r6_o3r4")
        o2=load_module(root/r4.O2,"postv16_r3r6_o2")
        a2e=load_module(root/r4.A2E,"postv16_r3r6_a2e")
        r2phys=load_module(root/r4.R2PHYS,"postv16_r3r6_r2phys")
        sg2=load_module(root/r4.SG2,"postv16_r3r6_sg2")
        sg3=load_module(root/r4.SG3,"postv16_r3r6_sg3")
        r3r2r1=load_module(root/r4.R3R2R1,"postv16_r3r6_r3r2r1")

        import highspy
        from scipy.sparse import coo_matrix
        gate("highspy_version_exact_1_15_1",highspy.Highs().version()=="1.15.1",highspy.Highs().version())
        gate("highspy_basis_roundtrip_gate",r4.highspy_basis_roundtrip_self_test(highspy)["getBasis_setBasis_roundtrip"])
        gate("native_HiGHS_QP_self_test",r3r5.highs_qp_self_test(highspy)["max_error"]<=1e-8)

        # Patch R4's trusted restartable five-stage solver into the R3-R6 checkpoint namespace.
        r4.MILESTONE=MILESTONE
        r4.GateError=GateError
        r4.ScientificFail=ScientificFail
        r4.stage_names=stage_names
        r4.recovery_dir=recovery_dir
        r4.manifest_valid=manifest_valid

        # ----------------------------------------------------------------------------------
        # Bind formal R3-R4 design and R3-R5 validation authority.
        # ----------------------------------------------------------------------------------
        stage="R3R4_R3R5_authority"
        d34=drive/R3R4_REL
        gate("R3R4_output_present",d34.is_dir(),str(d34))
        r3.verify_manifest(d34,r3r4.MANIFEST)
        s34=r3.load_json(d34/r3r4.SUMMARY)
        dec34=r3.load_json(d34/r3r4.DECISION)
        gate(
            "R3R4_design_exact",
            s34.get("status")==r3r4.STATUS_PASS
            and s34.get("generalized_active_set") is True
            and s34.get("multi_cut_QP") is True
            and s34.get("projection_must_vanish_for_final_PASS") is True
            and dec34.get("O3R6R4R3R5_one_step_active_set_validation_authorized") is True
            and dec34.get("full_generalized_solver_execution_authorized") is False,
        )

        d35=drive/R3R5_REL
        gate("R3R5_output_present",d35.is_dir(),str(d35))
        r3.verify_manifest(d35,r3r5.MANIFEST)
        s35=r3.load_json(d35/r3r5.SUMMARY)
        dec35=r3.load_json(d35/r3r5.DECISION)
        gate(
            "R3R5_PASS_exact",
            s35.get("status")==r3r5.STATUS_PASS
            and s35.get("initial_active_cut_pool_empty") is True
            and s35.get("round0_cut_matches_R1R1_reference") is True
            and s35.get("round1_exact_frozen_E2_feasible") is True
            and float(s35.get("round1_minimum_unserved_mass_kg"))==0.0
            and s35.get("same_alpha_recertified_after_cut_addition") is True
            and s35.get("support_domain_changed") is False
            and s35.get("physical_time_advanced") is False,
        )
        gate(
            "R3R5_authorizes_full_R3R6_only",
            dec35.get("O3R6R4R3R6_full_generalized_execution_authorized") is True
            and dec35.get("O3R6R4R3R6_must_use_frozen_R3R4_semantics") is True
            and dec35.get("O3R6R4R3R6_five_stage_assignment_authorized") is True
            and dec35.get("O3R6R4R3R6_physical_time_advance_authorized") is False
            and dec35.get("support_expansion_authorized") is False
            and dec35.get("O3R7_authorized") is False,
        )

        # ----------------------------------------------------------------------------------
        # Immutable O2/A2E state and exact graph.
        # ----------------------------------------------------------------------------------
        stage="state_authority_binding"
        o2d=drive/r4.O2_REL
        r3.verify_manifest(o2d,r4.O2_MANIFEST)
        with np.load(o2d/r4.O2_STATE,allow_pickle=False) as z:
            residual_grid=np.asarray(z["frozen_residual_grid_component_mass_kg"],dtype=np.float64)
            event_cv_mass=np.asarray(z["event_CV_component_mass_kg"],dtype=np.float64)
            e0_cv=np.asarray(z["E0_pair_cv_id"],dtype=np.int64)
            e0_cell=np.asarray(z["E0_pair_flat_cell"],dtype=np.int64)
            e2_cv=np.asarray(z["E2_pair_cv_id"],dtype=np.int64)
            e2_cell=np.asarray(z["E2_pair_flat_cell"],dtype=np.int64)
            is_e0=np.asarray(z["E2_pair_is_E0"],dtype=bool)
            is_e1=np.asarray(z["E2_pair_is_E1"],dtype=bool)
            target0=np.asarray(z["E0_parent_continuity_target_kg"],dtype=np.float64)
            qtarget0=np.asarray(z["E0_raw_event_EOS_target_kg"],dtype=np.float64)
            parent_pressure=np.asarray(z["parent_pressure_psi"],dtype=np.float64)
            grid_pv=np.asarray(z["grid_pore_volume_m3"],dtype=np.float64)
            p_ref=float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
        demand=event_cv_mass.reshape(-1).astype(np.float64)
        residual=residual_grid.reshape(-1).astype(np.float64)
        cv_tol=max(1e-6,1e-10*max(float(np.max(np.abs(demand))),1.0))
        gate(
            "O2_shapes_exact",
            e0_cv.size==EXPECTED_E0 and e2_cv.size==EXPECTED_E2
            and e2_cell.size==EXPECTED_E2 and demand.shape==(NCVTOTAL,)
            and residual_grid.shape==GRID and grid_pv.shape==GRID,
        )

        a2d=drive/r4.A2E_REL
        r3.verify_manifest(a2d,r4.A2E_MANIFEST)
        with np.load(a2d/r4.A2E_EPOCH,allow_pickle=False) as z:
            epoch={k:np.asarray(z[k]).copy() for k in z.files}
        grid_nw=np.asarray(epoch["nw"],dtype=np.float64)
        grid_no=np.asarray(epoch["no"],dtype=np.float64)
        grid_krw=np.asarray(epoch["krw_max"],dtype=np.float64)
        grid_kro=np.asarray(epoch["kro_max"],dtype=np.float64)

        e0_idx=np.flatnonzero(is_e0).astype(np.int64)
        gate("E0_count_exact",e0_idx.size==EXPECTED_E0,int(e0_idx.size))
        support={
            "e2_cv":e2_cv,
            "e2_cell":e2_cell,
            "is_e0":is_e0,
            "is_e1":is_e1,
            "is_h2_shell":(~is_e0)&(~is_e1),
            "is_any_extension":(~is_e0),
        }
        target_by_edge=np.zeros(EXPECTED_E2,dtype=np.float64)
        qtarget_by_edge=np.zeros(EXPECTED_E2,dtype=np.float64)
        target_by_edge[e0_idx]=target0
        qtarget_by_edge[e0_idx]=qtarget0
        prep=o2.preprocess_active_graph(
            e2_cv=e2_cv,e2_cell=e2_cell,demand=demand,
            available_raw=np.ones(NCELL,dtype=np.float64),
        )
        gate("active_frozen_E2_edge_count_exact",prep["active_edge_count"]==EXPECTED_ACTIVE,prep["active_edge_count"])
        gate("single_connected_component_exact",prep["component_count"]==1,prep["component_count"])
        graph_identity=array_sha256(np.asarray(prep["sorted_edge_idx"],dtype=np.int64))

        # ----------------------------------------------------------------------------------
        # Pressure physics.
        # ----------------------------------------------------------------------------------
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

        def capacity_from_S(S:np.ndarray):
            p,pres=pressure_step(S)
            cap=np.asarray(
                a2e.local_mass(r2phys,np.full(GRID,INJECTED),p,p_ref,grid_pv),
                dtype=np.float64,
            )
            avail_raw=cap.reshape(-1)-residual
            cap_tol=max(1e-8,1e-12*max(float(np.max(np.abs(cap))),1.0))
            return p,cap,pres,avail_raw,np.maximum(avail_raw,0.0),cap_tol

        def exact_min_unserved(available:np.ndarray):
            lp,active,cv_e,cell_e,nedge,nnz=o3r4.build_feasibility_lp(
                highspy,coo_matrix,e2_cv,e2_cell,demand,available
            )
            x,u,tel=o3r4.run_highs_feasibility(highspy,lp,nedge)
            del lp
            gc.collect()
            assigned=np.bincount(cv_e,weights=x,minlength=NCVTOTAL).astype(np.float64)
            mapped=np.bincount(cell_e,weights=x,minlength=NCELL).astype(np.float64)
            cv_linf=float(np.max(np.abs(assigned+u-demand)))
            cap_excess=float(np.max(mapped-available))
            if cv_linf>FEAS_CV_LINF_TOL_KG or cap_excess>FEAS_CAP_EXCESS_TOL_KG:
                raise ScientificFail(
                    "minimum_unserved_LP_certification_failure",
                    {"CV_Linf_kg":cv_linf,"capacity_excess_kg":cap_excess},
                )
            return {
                "x":x,"u":u,"active_cv":cv_e,"active_cell":cell_e,
                "objective":float(np.sum(u)),
                "CV_Linf_kg":cv_linf,
                "capacity_excess_kg":cap_excess,
                "active_edges":int(nedge),
                "matrix_nnz":int(nnz),
                "telemetry":tel,
            }

        # ----------------------------------------------------------------------------------
        # Build trusted persistent five-stage solver in the R3-R6 recovery namespace.
        # ----------------------------------------------------------------------------------
        stage="persistent_model_build"
        parent_cap=np.asarray(
            a2e.local_mass(r2phys,np.full(GRID,INJECTED),parent_pressure,p_ref,grid_pv),
            dtype=np.float64,
        )
        initial_available=np.maximum(parent_cap.reshape(-1)-residual,0.0)
        for cid in range(prep["component_count"]):
            aa=int(prep["component_starts"][cid]); bb=int(prep["component_starts"][cid+1])
            edge_idx=prep["sorted_edge_idx"][aa:bb]
            comp=o2.make_component(
                component_id=cid,edge_idx=edge_idx,support=support,demand=demand,
                available_safe=initial_available,target_by_edge=target_by_edge,
                qtarget_by_edge=qtarget_by_edge,
            )
            md=o2.build_component_model(comp,highspy)
            solvers.append(
                r4.RestartableLexSolver(
                    component_id=cid,comp=comp,model_data=md,highspy=highspy,
                    o2=o2,o3r6=o3r6,recovery_root=recovery,
                    graph_identity=graph_identity,output_flag=verbose_solver,
                )
            )
        gate("persistent_component_count_exact_1",len(solvers)==1,len(solvers))

        # ----------------------------------------------------------------------------------
        # Bootstrap accepted iteration 0 and physical map iteration 1 from immutable R4 recovery.
        # ----------------------------------------------------------------------------------
        stage="bootstrap_from_R4_and_R3R5"
        r4_acc0_dir=r4.recovery_dir(r4recovery,"accepted_iterates",0)
        r4_acc0_names=r4.accepted_names(0)
        gate(
            "R4_accepted_iteration0_valid",
            r4.manifest_valid(r3,r4_acc0_dir,r4_acc0_names[2],set(r4_acc0_names[:2])),
            str(r4_acc0_dir),
        )
        with np.load(r4_acc0_dir/r4_acc0_names[0],allow_pickle=False) as z:
            r4_acc0={k:np.asarray(z[k]).copy() for k in z.files}

        acc0_dir=recovery_dir(recovery,"accepted_iterates",0)
        a0sn,a0mn,a0man=accepted_names(0)
        if not acc0_dir.exists():
            r3.immutable_publish(
                acc0_dir,
                {
                    a0sn:o3r6.deterministic_npz_bytes({
                        "S_iter_next":r4_acc0["S_iter_next"],
                        "selected_alpha_index":np.asarray(147,dtype=np.int64),
                        "selected_alpha":np.asarray(147/LINE_DEN,dtype=np.float64),
                        "selected_trial_pressure_psi":r4_acc0["selected_trial_pressure_psi"],
                        "previous_physical_map_pressure_psi":r4_acc0["previous_physical_map_pressure_psi"],
                        "previous_physical_map_mass_kg":r4_acc0["previous_physical_map_mass_kg"],
                        "projection_q_L2":np.asarray(0.0),
                        "projection_q_Linf":np.asarray(0.0),
                        "active_cut_count":np.asarray(0,dtype=np.int64),
                    }),
                    a0mn:r3.json_bytes({
                        "milestone":MILESTONE,
                        "checkpoint_classification":"COMPUTATIONAL_ITERATE_ACCEPTED",
                        "source":"immutable R4 iteration-0 bootstrap",
                        "completed_iteration":0,"next_iteration":1,
                        "selected_alpha_index":147,"selected_alpha":147/LINE_DEN,
                        "projection_q_L2":0.0,"projection_q_Linf":0.0,
                        "active_cut_count":0,"provisional_converged":False,
                        "physical_state_authority":False,"physical_time_advanced":False,
                    }),
                }
            )
            r3.immutable_publish(
                acc0_dir,
                {a0man:r3.csv_bytes([
                    {"file":n,"sha256":r3.sha256_file(acc0_dir/n),"bytes":(acc0_dir/n).stat().st_size}
                    for n in (a0sn,a0mn)
                ])}
            )
        gate("R3R6_accepted_iteration0_valid",manifest_valid(r3,acc0_dir,a0man,{a0sn,a0mn}))

        r4_map1_dir=r4.recovery_dir(r4recovery,"physical_maps",1)
        r4_map1_names=r4.map_names(1)
        gate(
            "R4_physical_map_iteration1_valid",
            r4.manifest_valid(r3,r4_map1_dir,r4_map1_names[2],set(r4_map1_names[:2])),
            str(r4_map1_dir),
        )
        with np.load(r4_map1_dir/r4_map1_names[0],allow_pickle=False) as z:
            r4_map1={k:np.asarray(z[k]).copy() for k in z.files}
        r4_map1_meta=r3.load_json(r4_map1_dir/r4_map1_names[1])

        map1_dir=recovery_dir(recovery,"physical_maps",1)
        m1sn,m1mn,m1man=map_names(1)
        if not map1_dir.exists():
            r3.immutable_publish(
                map1_dir,
                {
                    m1sn:o3r6.deterministic_npz_bytes(r4_map1),
                    m1mn:r3.json_bytes({
                        **r4_map1_meta,
                        "milestone":MILESTONE,
                        "source":"immutable R4 iteration-1 physical map reused after R3-R5 validation",
                        "stage5_basis_path":r4_map1_meta["stage5_basis_path"],
                    }),
                }
            )
            r3.immutable_publish(
                map1_dir,
                {m1man:r3.csv_bytes([
                    {"file":n,"sha256":r3.sha256_file(map1_dir/n),"bytes":(map1_dir/n).stat().st_size}
                    for n in (m1sn,m1mn)
                ])}
            )
        gate("R3R6_physical_map_iteration1_valid",manifest_valid(r3,map1_dir,m1man,{m1sn,m1mn}))

        # Bootstrap accepted iteration 1 from formal R3-R5, with fresh exact recertification.
        acc1_dir=recovery_dir(recovery,"accepted_iterates",1)
        a1sn,a1mn,a1man=accepted_names(1)
        if not acc1_dir.exists():
            with np.load(d35/r3r5.STATE,allow_pickle=False) as z:
                r35state={k:np.asarray(z[k]).copy() for k in z.files}
            S0=np.asarray(r4_acc0["S_iter_next"],dtype=np.float64)
            gate("R3R5_S_base_matches_R4_bootstrap",np.max(np.abs(r35state["S_base"]-S0))<=1e-12)
            gate("R3R5_S_map_matches_R4_map1",np.max(np.abs(r35state["S_map"]-r4_map1["S_map"]))<=1e-12)
            S1=np.asarray(r35state["projected_trial_alpha_1_over_256"],dtype=np.float64)
            p1,cap1,pres1,avail_raw1,avail1,cap_tol1=capacity_from_S(S1)
            sci_gate("R3R6_bootstrap_iteration1_pressure_residual",pres1<PRESSURE_LINEAR_REL_RESIDUAL_MAX,pres1)
            sci_gate("R3R6_bootstrap_iteration1_residual_capacity",float(np.min(avail_raw1))>=-cap_tol1,float(np.min(avail_raw1)))
            lp1=exact_min_unserved(avail1)
            sci_gate("R3R6_bootstrap_iteration1_exact_feasibility",lp1["objective"]<=FEAS_UNSERVED_TOL_KG,lp1["objective"])
            q1=np.asarray(r35state["QP_q"],dtype=np.float64)
            raw_res=o3r6.max_abs(r4_map1["S_map"]-S0)
            pdelta=o3r6.relative_l2(r4_map1["P_map_psi"],r4_acc0["previous_physical_map_pressure_psi"])
            mdelta=o3r6.max_abs(r4_map1["event_grid_mass_kg"],r4_acc0["previous_physical_map_mass_kg"])
            mtol=max(1e-8,1e-10*max(float(np.max(np.abs(r4_map1["event_grid_mass_kg"]))),1.0))
            r3.immutable_publish(
                acc1_dir,
                {
                    a1sn:o3r6.deterministic_npz_bytes({
                        "S_iter_next":S1,
                        "selected_alpha_index":np.asarray(4,dtype=np.int64),
                        "selected_alpha":np.asarray(4/LINE_DEN,dtype=np.float64),
                        "selected_trial_pressure_psi":p1,
                        "previous_physical_map_pressure_psi":r4_map1["P_map_psi"],
                        "previous_physical_map_mass_kg":r4_map1["event_grid_mass_kg"],
                        "projection_q_L2":np.asarray(float(np.linalg.norm(q1))),
                        "projection_q_Linf":np.asarray(float(np.max(np.abs(q1)))),
                        "active_cut_count":np.asarray(1,dtype=np.int64),
                    }),
                    a1mn:r3.json_bytes({
                        "milestone":MILESTONE,
                        "checkpoint_classification":"COMPUTATIONAL_ITERATE_ACCEPTED",
                        "source":"formal R3-R5 separation-loop PASS recertified by R3-R6",
                        "completed_iteration":1,"next_iteration":2,
                        "selected_alpha_index":4,"selected_alpha":4/LINE_DEN,
                        "projection_q_L2":float(np.linalg.norm(q1)),
                        "projection_q_Linf":float(np.max(np.abs(q1))),
                        "active_cut_count":1,
                        "raw_fixed_point_saturation_Linf":float(raw_res),
                        "pressure_relative_L2_change":float(pdelta),
                        "grid_mass_Linf_change_kg":float(mdelta),
                        "grid_mass_convergence_tolerance_kg":float(mtol),
                        "provisional_converged":False,
                        "physical_state_authority":False,"physical_time_advanced":False,
                    }),
                }
            )
            r3.immutable_publish(
                acc1_dir,
                {a1man:r3.csv_bytes([
                    {"file":n,"sha256":r3.sha256_file(acc1_dir/n),"bytes":(acc1_dir/n).stat().st_size}
                    for n in (a1sn,a1mn)
                ])}
            )
        gate("R3R6_accepted_iteration1_valid",manifest_valid(r3,acc1_dir,a1man,{a1sn,a1mn}))

        # ----------------------------------------------------------------------------------
        # Durable frontier discovery.
        # ----------------------------------------------------------------------------------
        stage="recovery_frontier_discovery"
        accepted_iters=[]
        ar=recovery/"accepted_iterates"
        for d in sorted(ar.glob("iteration_*")):
            try: i=int(d.name.split("_")[1])
            except Exception: continue
            sn,mn,man=accepted_names(i)
            if manifest_valid(r3,d,man,{sn,mn}):
                accepted_iters.append(i)
            else:
                raise GateError(f"invalid_accepted_iterate_checkpoint:{d}")
        gate("bootstrap_iterations_zero_and_one_present",0 in accepted_iters and 1 in accepted_iters,accepted_iters)
        frontier=max(accepted_iters)
        fsn,fmn,fman=accepted_names(frontier)
        fdir=recovery_dir(recovery,"accepted_iterates",frontier)
        fmeta=r3.load_json(fdir/fmn)
        with np.load(fdir/fsn,allow_pickle=False) as z:
            S_iter=np.asarray(z["S_iter_next"],dtype=np.float64)
            previous_map_pressure=np.asarray(z["previous_physical_map_pressure_psi"],dtype=np.float64)
            previous_map_mass=np.asarray(z["previous_physical_map_mass_kg"],dtype=np.float64)
        current_iteration=int(fmeta["next_iteration"])
        gate("recovery_frontier_next_iteration_valid",1<=current_iteration<=MAX_NONLINEAR_ITERATIONS+1,current_iteration)
        resume_closure_iteration=frontier if fmeta.get("provisional_converged") is True else None

        # ----------------------------------------------------------------------------------
        # Checkpoint helpers.
        # ----------------------------------------------------------------------------------
        def map_checkpoint_valid(iteration:int)->bool:
            d=recovery_dir(recovery,"physical_maps",iteration)
            sn,mn,man=map_names(iteration)
            if not d.exists(): return False
            if not manifest_valid(r3,d,man,{sn,mn}):
                raise GateError(f"invalid_physical_map_checkpoint:iteration={iteration}")
            return True

        def load_map(iteration:int):
            d=recovery_dir(recovery,"physical_maps",iteration)
            sn,mn,man=map_names(iteration)
            r3.verify_manifest(d,man)
            meta=r3.load_json(d/mn)
            with np.load(d/sn,allow_pickle=False) as z:
                state={k:np.asarray(z[k]).copy() for k in z.files}
            return meta,state

        def publish_map(iteration:int,meta:dict[str,Any],arrays:dict[str,Any]):
            d=recovery_dir(recovery,"physical_maps",iteration)
            sn,mn,man=map_names(iteration)
            r3.immutable_publish(d,{sn:o3r6.deterministic_npz_bytes(arrays),mn:r3.json_bytes(meta)})
            r3.immutable_publish(
                d,{man:r3.csv_bytes([
                    {"file":n,"sha256":r3.sha256_file(d/n),"bytes":(d/n).stat().st_size}
                    for n in (sn,mn)
                ])}
            )
            if not manifest_valid(r3,d,man,{sn,mn}):
                raise GateError(f"physical_map_checkpoint_publish_failure:iteration={iteration}")
            print(f"[CHECKPOINT] iteration={iteration:03d} PHYSICAL_MAP_CANDIDATE")

        def load_or_compute_probe(iteration:int,cell:int,S_base:np.ndarray,base_available:np.ndarray):
            d=probe_dir(recovery,iteration,cell)
            sn,mn,man=probe_names(iteration,cell)
            if d.exists():
                if not manifest_valid(r3,d,man,{sn,mn}):
                    raise GateError(f"invalid_sensitivity_probe_checkpoint:iteration={iteration},cell={cell}")
                meta=r3.load_json(d/mn)
                with np.load(d/sn,allow_pickle=False) as z:
                    state={k:np.asarray(z[k]).copy() for k in z.files}
                if meta.get("S_base_sha256")!=array_sha256(S_base):
                    raise GateError("sensitivity_probe_base_state_hash_mismatch")
                return meta,state

            sflat=S_base.reshape(-1)
            s0=float(sflat[cell]); h=SENSITIVITY_STEP
            plus_ok=s0+h<=INJECTED+1e-14
            minus_ok=s0-h>=BACKGROUND-1e-14
            state={"cell":np.asarray(cell,dtype=np.int64)}
            if plus_ok and minus_ok:
                Sp=S_base.copy().reshape(-1); Sm=S_base.copy().reshape(-1)
                Sp[cell]+=h; Sm[cell]-=h
                pp,cp,rp,arp,ap,tp=capacity_from_S(Sp.reshape(GRID))
                pm,cm,rm,arm,am,tm=capacity_from_S(Sm.reshape(GRID))
                sci_gate(f"probe_{iteration}_{cell}_plus_pressure",rp<PRESSURE_LINEAR_REL_RESIDUAL_MAX,rp)
                sci_gate(f"probe_{iteration}_{cell}_minus_pressure",rm<PRESSURE_LINEAR_REL_RESIDUAL_MAX,rm)
                state.update({"available_plus":ap,"available_minus":am})
                mode="central"
            elif plus_ok:
                Sp=S_base.copy().reshape(-1); Sp[cell]+=h
                pp,cp,rp,arp,ap,tp=capacity_from_S(Sp.reshape(GRID))
                sci_gate(f"probe_{iteration}_{cell}_plus_pressure",rp<PRESSURE_LINEAR_REL_RESIDUAL_MAX,rp)
                state.update({"available_plus":ap,"available_base":base_available})
                mode="forward"
            elif minus_ok:
                Sm=S_base.copy().reshape(-1); Sm[cell]-=h
                pm,cm,rm,arm,am,tm=capacity_from_S(Sm.reshape(GRID))
                sci_gate(f"probe_{iteration}_{cell}_minus_pressure",rm<PRESSURE_LINEAR_REL_RESIDUAL_MAX,rm)
                state.update({"available_minus":am,"available_base":base_available})
                mode="backward"
            else:
                raise ScientificFail("no_admissible_sensitivity_probe_direction",{"iteration":iteration,"cell":cell,"S":s0})

            meta={
                "milestone":MILESTONE,"nonlinear_iteration":iteration,"flat_cell":cell,
                "mode":mode,"step":h,"S_base":s0,"S_base_sha256":array_sha256(S_base),
                "physical_state_authority":False,"physical_time_advanced":False,
            }
            r3.immutable_publish(d,{sn:o3r6.deterministic_npz_bytes(state),mn:r3.json_bytes(meta)})
            r3.immutable_publish(
                d,{man:r3.csv_bytes([
                    {"file":n,"sha256":r3.sha256_file(d/n),"bytes":(d/n).stat().st_size}
                    for n in (sn,mn)
                ])}
            )
            return meta,state

        def cut_linearization(
            iteration:int,
            cut:dict[str,Any],
            S_base:np.ndarray,
            base_available:np.ndarray,
            eps_available:np.ndarray,
            union_cells:np.ndarray,
        ):
            cells=np.asarray(cut["cell_ids"],dtype=np.int64)
            cvs=np.asarray(cut["cv_ids"],dtype=np.int64)
            cut_demand=float(np.sum(demand[cvs]))
            D0=cut_demand-float(np.sum(base_available[cells]))
            Deps=cut_demand-float(np.sum(eps_available[cells]))
            a=(Deps-D0)/RAW_SECANT_EPSILON
            g=np.zeros(union_cells.size,dtype=np.float64)
            for jj,cell in enumerate(union_cells):
                meta,state=load_or_compute_probe(iteration,int(cell),S_base,base_available)
                mode=meta["mode"]; h=float(meta["step"])
                if mode=="central":
                    Dp=cut_demand-float(np.sum(state["available_plus"][cells]))
                    Dm=cut_demand-float(np.sum(state["available_minus"][cells]))
                    g[jj]=(Dp-Dm)/(2*h)
                elif mode=="forward":
                    Dp=cut_demand-float(np.sum(state["available_plus"][cells]))
                    g[jj]=(Dp-D0)/h
                elif mode=="backward":
                    Dm=cut_demand-float(np.sum(state["available_minus"][cells]))
                    g[jj]=(D0-Dm)/h
                else:
                    raise GateError("unknown_probe_mode")
            return D0,a,g

        def publish_candidate(
            iteration:int,alpha_idx:int,round_idx:int,
            arrays:dict[str,Any],result:dict[str,Any]
        ):
            d=candidate_dir(recovery,iteration,alpha_idx,round_idx)
            sn,rn,man=candidate_names(iteration,alpha_idx,round_idx)
            r3.immutable_publish(d,{sn:o3r6.deterministic_npz_bytes(arrays),rn:r3.json_bytes(result)})
            r3.immutable_publish(
                d,{man:r3.csv_bytes([
                    {"file":n,"sha256":r3.sha256_file(d/n),"bytes":(d/n).stat().st_size}
                    for n in (sn,rn)
                ])}
            )

        def generalized_globalization(
            iteration:int,
            S_base:np.ndarray,
            S_map:np.ndarray,
            base_capacity:np.ndarray,
        ):
            generalized_iteration_executed_local=True
            d_raw=S_map-S_base
            base_available_raw=base_capacity.reshape(-1)-residual
            base_tol=max(1e-8,1e-12*max(float(np.max(np.abs(base_capacity))),1.0))
            sci_gate(
                f"iteration_{iteration:03d}_base_residual_capacity",
                float(np.min(base_available_raw))>=-base_tol,
                float(np.min(base_available_raw)),
            )
            base_available=np.maximum(base_available_raw,0.0)

            S_eps=S_base+RAW_SECANT_EPSILON*d_raw
            p_eps,c_eps,r_eps,ar_eps,av_eps,t_eps=capacity_from_S(S_eps)
            sci_gate(f"iteration_{iteration:03d}_raw_epsilon_pressure",r_eps<PRESSURE_LINEAR_REL_RESIDUAL_MAX,r_eps)
            sci_gate(
                f"iteration_{iteration:03d}_raw_epsilon_residual_capacity",
                float(np.min(ar_eps))>=-t_eps,float(np.min(ar_eps))
            )

            active_cuts=[]
            active_ids=set()
            telemetry=[]
            cut_rows=[]

            for alpha_idx in ALPHA_INDICES:
                alpha=alpha_idx/LINE_DEN
                # Active cuts are retained as a warm-start pool while alpha decreases.
                for round_idx in range(MAX_ACTIVE_CUT_ROUNDS_PER_ALPHA+1):
                    union_cells=np.asarray(
                        sorted(set(int(c) for cut in active_cuts for c in cut["cell_ids"])),
                        dtype=np.int64,
                    )
                    if active_cuts:
                        G=np.zeros((len(active_cuts),union_cells.size),dtype=np.float64)
                        avec=np.zeros(len(active_cuts),dtype=np.float64)
                        for rr,cut in enumerate(active_cuts):
                            D0,a,g=cut_linearization(
                                iteration,cut,S_base,base_available,av_eps,union_cells
                            )
                            cut["D0"]=float(D0); cut["a"]=float(a)
                            G[rr,:]=g; avec[rr]=a
                        sb=S_base.reshape(-1)[union_cells]
                        dr=d_raw.reshape(-1)[union_cells]
                        lo=(BACKGROUND-sb)/alpha-dr
                        hi=(INJECTED-sb)/alpha-dr
                        try:
                            q,qp_tel=r3r5.solve_box_multicut_qp(
                                highspy,G,avec,lo,hi,output_flag=False
                            )
                        except ScientificFail as exc:
                            if exc.gate in {"active_set_QP_infeasible","QP_variable_bounds_infeasible"}:
                                telemetry.append({
                                    "iteration":iteration,"alpha_index":alpha_idx,"alpha":alpha,
                                    "round":round_idx,"active_cut_count":len(active_cuts),
                                    "classification":"QP_INFEASIBLE","minimum_unserved_mass_kg":None,
                                    "q_L2":None,"q_Linf":None,
                                })
                                break
                            raise
                        row_excess=G@q+avec
                        sci_gate(
                            f"iteration_{iteration:03d}_alpha_{alpha_idx:04d}_round_{round_idx:02d}_QP_rows",
                            float(np.max(row_excess))<=TANGENT_ROW_TOL,
                            float(np.max(row_excess)),
                        )
                    else:
                        q=np.zeros(0,dtype=np.float64)
                        qp_tel={"objective":0.0,"max_row_excess":0.0}
                        union_cells=np.asarray([],dtype=np.int64)

                    dproj=d_raw.reshape(-1).copy()
                    if union_cells.size:
                        dproj[union_cells]+=q
                    S_trial=(S_base.reshape(-1)+alpha*dproj).reshape(GRID)
                    smin=float(np.min(S_trial)); smax=float(np.max(S_trial))
                    if smin<BACKGROUND-1e-10 or smax>INJECTED+1e-10:
                        telemetry.append({
                            "iteration":iteration,"alpha_index":alpha_idx,"alpha":alpha,
                            "round":round_idx,"active_cut_count":len(active_cuts),
                            "classification":"SATURATION_BOUNDS","minimum_unserved_mass_kg":None,
                            "q_L2":float(np.linalg.norm(q)) if q.size else 0.0,
                            "q_Linf":float(np.max(np.abs(q))) if q.size else 0.0,
                        })
                        break

                    p,cap,pres,avail_raw,available,cap_tol=capacity_from_S(S_trial)
                    sci_gate(
                        f"iteration_{iteration:03d}_alpha_{alpha_idx:04d}_round_{round_idx:02d}_pressure",
                        pres<PRESSURE_LINEAR_REL_RESIDUAL_MAX,pres,
                    )
                    if float(np.min(avail_raw)) < -cap_tol:
                        telemetry.append({
                            "iteration":iteration,"alpha_index":alpha_idx,"alpha":alpha,
                            "round":round_idx,"active_cut_count":len(active_cuts),
                            "classification":"RESIDUAL_SIDECAR_CAPACITY","minimum_unserved_mass_kg":None,
                            "q_L2":float(np.linalg.norm(q)) if q.size else 0.0,
                            "q_Linf":float(np.max(np.abs(q))) if q.size else 0.0,
                        })
                        break

                    lp=exact_min_unserved(available)
                    objective=lp["objective"]
                    feasible=objective<=FEAS_UNSERVED_TOL_KG
                    ids=np.flatnonzero(lp["u"]>FEAS_UNSERVED_TOL_KG).astype(np.int64)
                    ql2=float(np.linalg.norm(q)) if q.size else 0.0
                    qlinf=float(np.max(np.abs(q))) if q.size else 0.0

                    result={
                        "milestone":MILESTONE,"nonlinear_iteration":iteration,
                        "alpha_index":alpha_idx,"alpha_denominator":LINE_DEN,"alpha":alpha,
                        "active_cut_count":len(active_cuts),"active_cut_ids":[c["id"] for c in active_cuts],
                        "round":round_idx,"exact_frozen_E2_feasible":bool(feasible),
                        "minimum_unserved_mass_kg":objective,
                        "unserved_CV_ids":[int(v) for v in ids],
                        "pressure_linear_relative_residual":pres,
                        "CV_equality_Linf_kg":lp["CV_Linf_kg"],
                        "maximum_cell_capacity_excess_kg":lp["capacity_excess_kg"],
                        "q_L2":ql2,"q_Linf":qlinf,
                        "trial_saturation_minmax":[smin,smax],
                        "classification":"EXACT_FEASIBLE" if feasible else "EXACT_LP_INFEASIBLE",
                        "physical_state_authority":False,"physical_time_advanced":False,
                    }
                    arrays={
                        "S_trial":S_trial,"pressure_psi":p,"cell_capacity_kg":cap,
                        "available_mapped_capacity_kg":available.reshape(GRID),
                        "union_cut_cell_ids":union_cells,"q":q,
                        "unserved_CV_ids":ids,
                    }
                    publish_candidate(iteration,alpha_idx,round_idx,arrays,result)
                    telemetry.append({
                        "iteration":iteration,"alpha_index":alpha_idx,"alpha":alpha,
                        "round":round_idx,"active_cut_count":len(active_cuts),
                        "classification":result["classification"],
                        "minimum_unserved_mass_kg":objective,"q_L2":ql2,"q_Linf":qlinf,
                    })

                    if feasible:
                        return {
                            "selected_alpha_index":alpha_idx,"selected_alpha":alpha,
                            "S_next":S_trial,"pressure":p,"q":q,
                            "union_cells":union_cells,"active_cuts":active_cuts,
                            "telemetry":telemetry,"cut_rows":cut_rows,
                            "candidate_result":result,
                        }

                    cut_cv_mask,cut_cell_mask,cut_meta=r3r5.residual_min_cut_general(
                        active_cv=lp["active_cv"],active_cell=lp["active_cell"],
                        x=lp["x"],u=lp["u"],demand=demand,available=available,
                    )
                    cut_cv=np.flatnonzero(cut_cv_mask).astype(np.int64)
                    cut_cell=np.flatnonzero(cut_cell_mask).astype(np.int64)
                    cid=cut_key(cut_cv,cut_cell)
                    sci_gate(
                        f"iteration_{iteration:03d}_alpha_{alpha_idx:04d}_round_{round_idx:02d}_cut_matches_LP",
                        abs(float(cut_meta["cut_deficit_kg"])-objective)<=CUT_MATCH_TOL_KG,
                        {"cut_deficit_kg":cut_meta["cut_deficit_kg"],"LP_objective_kg":objective},
                    )
                    cut_rows.append({
                        "iteration":iteration,"alpha_index":alpha_idx,"alpha":alpha,
                        "round":round_idx,"cut_id":cid,
                        "cut_CV_count":int(cut_cv.size),"cut_cell_count":int(cut_cell.size),
                        "cut_deficit_kg":float(cut_meta["cut_deficit_kg"]),
                        "novel":cid not in active_ids,
                    })
                    if cid in active_ids:
                        telemetry.append({
                            "iteration":iteration,"alpha_index":alpha_idx,"alpha":alpha,
                            "round":round_idx,"active_cut_count":len(active_cuts),
                            "classification":"DUPLICATE_MINCUT_LINEARIZATION_STALL",
                            "minimum_unserved_mass_kg":objective,"q_L2":ql2,"q_Linf":qlinf,
                        })
                        break
                    if round_idx>=MAX_ACTIVE_CUT_ROUNDS_PER_ALPHA:
                        break
                    active_ids.add(cid)
                    active_cuts.append({
                        "id":cid,
                        "cv_ids":[int(v) for v in cut_cv],
                        "cell_ids":[int(v) for v in cut_cell],
                    })
                    print(
                        f"[CUT] iter={iteration:03d} alpha={alpha_idx}/{LINE_DEN} "
                        f"round={round_idx} added={cid[:12]} CVs={cut_cv.size} cells={cut_cell.size}"
                    )
                    sys.stdout.flush()

            raise ScientificFail(
                "no_generalized_feasible_alpha_at_or_above_1_over_1024",
                {"iteration":iteration,"minimum_alpha":1/LINE_DEN,"telemetry_tail":telemetry[-10:]},
            )

        def publish_accepted(
            iteration:int,selected:dict[str,Any],
            raw_sat_residual:float,pressure_delta:float,
            grid_mass_delta:float,mass_conv_tol:float,
            previous_map_pressure:np.ndarray,previous_map_mass:np.ndarray,
            provisional:bool,
        ):
            d=recovery_dir(recovery,"accepted_iterates",iteration)
            sn,mn,man=accepted_names(iteration)
            q=np.asarray(selected["q"],dtype=np.float64)
            ql2=float(np.linalg.norm(q)) if q.size else 0.0
            qlinf=float(np.max(np.abs(q))) if q.size else 0.0
            meta={
                "milestone":MILESTONE,"checkpoint_classification":"COMPUTATIONAL_ITERATE_ACCEPTED",
                "completed_iteration":iteration,"next_iteration":iteration+1,
                "selected_alpha_index":int(selected["selected_alpha_index"]),
                "selected_alpha":float(selected["selected_alpha"]),
                "projection_q_L2":ql2,"projection_q_Linf":qlinf,
                "active_cut_count":len(selected["active_cuts"]),
                "active_cut_ids":[c["id"] for c in selected["active_cuts"]],
                "active_cut_CV_counts":[len(c["cv_ids"]) for c in selected["active_cuts"]],
                "active_cut_cell_counts":[len(c["cell_ids"]) for c in selected["active_cuts"]],
                "cut_telemetry":selected.get("cut_rows",[]),
                "raw_fixed_point_saturation_Linf":float(raw_sat_residual),
                "pressure_relative_L2_change":float(pressure_delta),
                "grid_mass_Linf_change_kg":float(grid_mass_delta),
                "grid_mass_convergence_tolerance_kg":float(mass_conv_tol),
                "provisional_converged":bool(provisional),
                "physical_state_authority":False,"physical_time_advanced":False,
            }
            arrays={
                "S_iter_next":selected["S_next"],
                "selected_alpha_index":np.asarray(selected["selected_alpha_index"],dtype=np.int64),
                "selected_alpha":np.asarray(selected["selected_alpha"],dtype=np.float64),
                "selected_trial_pressure_psi":selected["pressure"],
                "previous_physical_map_pressure_psi":previous_map_pressure,
                "previous_physical_map_mass_kg":previous_map_mass,
                "projection_q_L2":np.asarray(ql2),
                "projection_q_Linf":np.asarray(qlinf),
                "active_cut_count":np.asarray(len(selected["active_cuts"]),dtype=np.int64),
            }
            r3.immutable_publish(d,{sn:o3r6.deterministic_npz_bytes(arrays),mn:r3.json_bytes(meta)})
            r3.immutable_publish(
                d,{man:r3.csv_bytes([
                    {"file":n,"sha256":r3.sha256_file(d/n),"bytes":(d/n).stat().st_size}
                    for n in (sn,mn)
                ])}
            )
            print(
                f"[CHECKPOINT] iteration={iteration:03d} COMPUTATIONAL_ITERATE_ACCEPTED "
                f"alpha={selected['selected_alpha_index']}/{LINE_DEN} qLinf={qlinf:.6e}"
            )

        # ----------------------------------------------------------------------------------
        # Full generalized fixed-point loop.
        # ----------------------------------------------------------------------------------
        if resume_closure_iteration is None:
            for iteration in range(current_iteration,MAX_NONLINEAR_ITERATIONS+1):
                current_iteration=iteration
                generalized_iteration_executed=True
                stage=f"iteration_{iteration:03d}_physical_map"

                if map_checkpoint_valid(iteration):
                    map_meta,map_state=load_map(iteration)
                    sci_gate(
                        f"iteration_{iteration:03d}_map_S_iter_identity",
                        o3r6.max_abs(map_state["S_iter"]-S_iter)<=1e-12,
                        o3r6.max_abs(map_state["S_iter"]-S_iter),
                    )
                    pcheck,rcheck=pressure_step(S_iter)
                    sci_gate(f"iteration_{iteration:03d}_reused_map_pressure_residual",rcheck<PRESSURE_LINEAR_REL_RESIDUAL_MAX,rcheck)
                    gate(
                        f"iteration_{iteration:03d}_reused_map_pressure_identity",
                        o3r6.max_abs(pcheck-map_state["P_map_psi"])<=1e-8,
                        o3r6.max_abs(pcheck-map_state["P_map_psi"]),
                    )
                    P_map=np.asarray(map_state["P_map_psi"],dtype=np.float64)
                    cap=np.asarray(map_state["cell_capacity_kg"],dtype=np.float64)
                    full_x=np.asarray(map_state["E2_assignment_mass_kg"],dtype=np.float64)
                    mapped=np.asarray(map_state["mapped_grid_mass_kg"],dtype=np.float64)
                    m_map=np.asarray(map_state["event_grid_mass_kg"],dtype=np.float64)
                    S_map=np.asarray(map_state["S_map"],dtype=np.float64)
                    objectives={k:float(v) for k,v in map_meta["objectives"].items()}
                    map_telemetry=list(map_meta["assignment_telemetry"])
                else:
                    P_map,pres=pressure_step(S_iter)
                    sci_gate(f"iteration_{iteration:03d}_pressure_linear_residual",pres<PRESSURE_LINEAR_REL_RESIDUAL_MAX,pres)
                    cap=np.asarray(
                        a2e.local_mass(r2phys,np.full(GRID,INJECTED),P_map,p_ref,grid_pv),
                        dtype=np.float64,
                    )
                    cap_tol=max(1e-8,1e-12*max(float(np.max(np.abs(cap))),1.0))
                    available_raw=cap.reshape(-1)-residual
                    sci_gate(
                        f"iteration_{iteration:03d}_residual_sidecar_capacity",
                        float(np.min(available_raw))>=-cap_tol,
                        {"min_available_kg":float(np.min(available_raw)),"tol_kg":cap_tol},
                    )
                    available=np.maximum(available_raw,0.0)
                    grid_tol=max(1e-6,1e-10*max(float(np.max(np.abs(cap))),1.0))
                    full_x=np.zeros(EXPECTED_E2,dtype=np.float64)
                    objectives={
                        "stage1_shell_kg":0.0,"stage2_extension_kg":0.0,
                        "stage3_parent_L1_kg":0.0,"stage4_raw_L1_kg":0.0,"stage5_tiebreak":0.0,
                    }
                    map_telemetry=[]
                    prior_basis=None
                    if iteration==2:
                        p=Path(r4_map1_meta["stage5_basis_path"])
                        if p.is_file(): prior_basis=p
                    elif iteration>2:
                        p=recovery_dir(recovery,"lex_stages",iteration-1)/"stage_5"/stage_names(iteration-1,5)[2]
                        if p.is_file(): prior_basis=p

                    for solver in solvers:
                        rr=solver.solve_iteration(
                            r3=r3,iteration=iteration,available_global=available,
                            cv_tol=cv_tol,grid_tol=grid_tol,prior_stage5_basis=prior_basis,
                        )
                        assignment_executed=True
                        full_x[rr["edge_idx"]]=rr["x"]
                        map_telemetry.extend(rr["telemetry"])
                        for k,v in rr["objectives"].items():
                            objectives[k]+=float(v)
                        stage5_basis_path=rr["stage5_basis_path"]

                    mapped_flat=np.bincount(e2_cell,weights=full_x,minlength=NCELL).astype(np.float64)
                    mapped=mapped_flat.reshape(GRID)
                    cv_rec=np.bincount(e2_cv,weights=full_x,minlength=NCVTOTAL).astype(np.float64)
                    m_map=residual_grid+mapped
                    cv_linf=o3r6.max_abs(cv_rec-demand)
                    max_excess=float(np.max(m_map-cap))
                    global_resid=o3r6.fsum_array(m_map)-o3r6.fsum_array(residual)-o3r6.fsum_array(demand)
                    sci_gate(
                        f"iteration_{iteration:03d}_assignment_certification",
                        cv_linf<=cv_tol and max_excess<=grid_tol
                        and abs(global_resid)<=max(1e-5,1e-10*max(o3r6.fsum_array(m_map),1.0)),
                        {"CV_Linf_kg":cv_linf,"max_capacity_excess_kg":max_excess,"global_residual_kg":global_resid},
                    )
                    try:
                        sg_map=a2e.invert_local_mass(r2phys,m_map,P_map,p_ref,grid_pv)
                    except Exception as exc:
                        raise ScientificFail("iterate_EOS_mass_inversion_failure",{"iteration":iteration,"exception":repr(exc)})
                    S_map=BACKGROUND+np.asarray(sg_map,dtype=np.float64)
                    sci_gate(
                        f"iteration_{iteration:03d}_saturation_bounds",
                        np.isfinite(S_map).all() and float(np.min(S_map))>=BACKGROUND-1e-10
                        and float(np.max(S_map))<=INJECTED+1e-10,
                        [float(np.min(S_map)),float(np.max(S_map))],
                    )
                    rec_mass=np.asarray(a2e.local_mass(r2phys,S_map,P_map,p_ref,grid_pv),dtype=np.float64)
                    cell_err=o3r6.max_abs(rec_mass-m_map)
                    global_rel=abs(o3r6.fsum_array(rec_mass)-o3r6.fsum_array(m_map))/max(abs(o3r6.fsum_array(m_map)),1.0)
                    mass_tol=max(1e-8,1e-10*max(float(np.max(np.abs(m_map))),1.0))
                    sci_gate(
                        f"iteration_{iteration:03d}_mass_closure",
                        cell_err<=mass_tol and global_rel<=GLOBAL_MASS_REL_TOL,
                        {"cell_error_kg":cell_err,"tol_kg":mass_tol,"global_rel":global_rel},
                    )
                    raw_res=o3r6.max_abs(S_map-S_iter)
                    pdelta=o3r6.relative_l2(P_map,previous_map_pressure)
                    mdelta=o3r6.max_abs(m_map-previous_map_mass)
                    meta={
                        "milestone":MILESTONE,"checkpoint_classification":"PHYSICAL_MAP_CANDIDATE",
                        "nonlinear_iteration":iteration,"objectives":objectives,
                        "assignment_telemetry":map_telemetry,
                        "stage5_basis_path":str(stage5_basis_path),
                        "metrics":{
                            "raw_fixed_point_saturation_Linf":raw_res,
                            "pressure_relative_L2_change":pdelta,
                            "grid_mass_Linf_change_kg":mdelta,
                            "grid_mass_convergence_tolerance_kg":mass_tol,
                            "pressure_linear_relative_residual":pres,
                            "CV_mass_Linf_error_kg":cv_linf,
                            "maximum_cell_capacity_excess_kg":max_excess,
                            "cellwise_EOS_mass_error_kg":cell_err,
                            "global_EOS_mass_relative_error":global_rel,
                        },
                        "physical_state_authority":True,"physical_time_advanced":False,
                    }
                    publish_map(
                        iteration,meta,{
                            "S_iter":S_iter,"P_map_psi":P_map,"cell_capacity_kg":cap,
                            "E2_assignment_mass_kg":full_x,"mapped_grid_mass_kg":mapped,
                            "event_grid_mass_kg":m_map,"S_map":S_map,
                        }
                    )

                raw_res=o3r6.max_abs(S_map-S_iter)
                pdelta=o3r6.relative_l2(P_map,previous_map_pressure)
                mdelta=o3r6.max_abs(m_map-previous_map_mass)
                mtol=max(1e-8,1e-10*max(float(np.max(np.abs(m_map))),1.0))

                stage=f"iteration_{iteration:03d}_generalized_globalization"
                selected=generalized_globalization(iteration,S_iter,S_map,cap)
                q=np.asarray(selected["q"],dtype=np.float64)
                qlinf=float(np.max(np.abs(q))) if q.size else 0.0
                full_step=selected["selected_alpha_index"]==LINE_DEN
                provisional=(
                    full_step and qlinf<=PROJECTION_LINF_TOL
                    and raw_res<=SATURATION_LINF_TOL
                    and pdelta<=PRESSURE_REL_L2_TOL
                    and mdelta<=mtol
                )
                publish_accepted(
                    iteration,selected,raw_res,pdelta,mdelta,mtol,
                    P_map,m_map,provisional,
                )
                print(
                    f"[ITER {iteration:03d}] alpha={selected['selected_alpha_index']}/{LINE_DEN} "
                    f"qLinf={qlinf:.6e} raw_dS={raw_res:.6e} dP={pdelta:.6e} "
                    f"dM={mdelta:.6e} provisional={provisional}"
                )
                sys.stdout.flush()

                if provisional:
                    resume_closure_iteration=iteration
                    break

                S_iter=np.asarray(selected["S_next"],dtype=np.float64)
                previous_map_pressure=P_map
                previous_map_mass=m_map

            if resume_closure_iteration is None:
                raise ScientificFail(
                    "generalized_coupled_fixed_point_nonconvergence",
                    {"maximum_iterations":MAX_NONLINEAR_ITERATIONS,"last_iteration":current_iteration},
                )

        # ----------------------------------------------------------------------------------
        # Original undamped final closure.
        # ----------------------------------------------------------------------------------
        closure_iteration=int(resume_closure_iteration)
        stage="final_undamped_closure"
        map_meta,map_state=load_map(closure_iteration)
        P_map=np.asarray(map_state["P_map_psi"],dtype=np.float64)
        S_map=np.asarray(map_state["S_map"],dtype=np.float64)
        m_map=np.asarray(map_state["event_grid_mass_kg"],dtype=np.float64)
        full_x=np.asarray(map_state["E2_assignment_mass_kg"],dtype=np.float64)

        adir=recovery_dir(recovery,"accepted_iterates",closure_iteration)
        asn,amn,aman=accepted_names(closure_iteration)
        r3.verify_manifest(adir,aman)
        ameta=r3.load_json(adir/amn)
        sci_gate("closure_requires_full_alpha",int(ameta["selected_alpha_index"])==LINE_DEN,ameta["selected_alpha_index"])
        sci_gate("closure_requires_vanishing_projection",float(ameta["projection_q_Linf"])<=PROJECTION_LINF_TOL,ameta["projection_q_Linf"])
        sci_gate("closure_requires_provisional_convergence",ameta.get("provisional_converged") is True,ameta.get("provisional_converged"))
        sci_gate("closure_raw_fixed_point_saturation",float(ameta["raw_fixed_point_saturation_Linf"])<=SATURATION_LINF_TOL,ameta["raw_fixed_point_saturation_Linf"])
        sci_gate("closure_pressure_iteration_delta",float(ameta["pressure_relative_L2_change"])<=PRESSURE_REL_L2_TOL,ameta["pressure_relative_L2_change"])
        sci_gate(
            "closure_grid_mass_iteration_delta",
            float(ameta["grid_mass_Linf_change_kg"])<=float(ameta["grid_mass_convergence_tolerance_kg"]),
            {"delta":ameta["grid_mass_Linf_change_kg"],"tol":ameta["grid_mass_convergence_tolerance_kg"]},
        )

        closure_pressure,closure_linear_resid=pressure_step(S_map)
        sci_gate("closure_pressure_linear_residual",closure_linear_resid<PRESSURE_LINEAR_REL_RESIDUAL_MAX,closure_linear_resid)
        closure_pressure_delta=o3r6.relative_l2(closure_pressure,P_map)
        sci_gate("closure_pressure_fixed_point",closure_pressure_delta<=PRESSURE_REL_L2_TOL,closure_pressure_delta)

        closure_cap=np.asarray(
            a2e.local_mass(r2phys,np.full(GRID,INJECTED),closure_pressure,p_ref,grid_pv),
            dtype=np.float64,
        )
        closure_cap_tol=max(1e-6,1e-10*max(float(np.max(np.abs(closure_cap))),1.0))
        closure_avail_raw=closure_cap.reshape(-1)-residual
        sci_gate("closure_residual_sidecar_capacity",float(np.min(closure_avail_raw))>=-closure_cap_tol,float(np.min(closure_avail_raw)))
        closure_grid_excess=float(np.max(m_map-closure_cap))
        sci_gate("closure_assignment_within_capacity",closure_grid_excess<=closure_cap_tol,closure_grid_excess)

        try:
            closure_sg=a2e.invert_local_mass(r2phys,m_map,closure_pressure,p_ref,grid_pv)
        except Exception as exc:
            raise ScientificFail("closure_EOS_mass_inversion_failure",repr(exc))
        closure_sat=BACKGROUND+np.asarray(closure_sg,dtype=np.float64)
        sci_gate(
            "closure_saturation_bounds",
            np.isfinite(closure_sat).all() and float(np.min(closure_sat))>=BACKGROUND-1e-10
            and float(np.max(closure_sat))<=INJECTED+1e-10,
            [float(np.min(closure_sat)),float(np.max(closure_sat))],
        )
        closure_sat_delta=o3r6.max_abs(closure_sat-S_map)
        sci_gate("closure_saturation_fixed_point",closure_sat_delta<=SATURATION_LINF_TOL,closure_sat_delta)

        reconstructed_mass=np.asarray(
            a2e.local_mass(r2phys,closure_sat,closure_pressure,p_ref,grid_pv),
            dtype=np.float64,
        )
        final_mass_tol=max(1e-8,1e-10*max(float(np.max(np.abs(m_map))),1.0))
        closure_cell_mass_error=o3r6.max_abs(reconstructed_mass-m_map)
        closure_global_rel=abs(o3r6.fsum_array(reconstructed_mass)-o3r6.fsum_array(m_map))/max(abs(o3r6.fsum_array(m_map)),1.0)
        sci_gate("closure_cellwise_mass_error",closure_cell_mass_error<=final_mass_tol,closure_cell_mass_error)
        sci_gate("closure_global_mass_relative_error",closure_global_rel<=GLOBAL_MASS_REL_TOL,closure_global_rel)

        final_mapped=np.bincount(e2_cell,weights=full_x,minlength=NCELL).astype(np.float64)
        final_cv=np.bincount(e2_cv,weights=full_x,minlength=NCVTOTAL).astype(np.float64)
        final_cv_linf=o3r6.max_abs(final_cv-demand)
        sci_gate("final_per_CV_mass_exact",final_cv_linf<=cv_tol,{"Linf_kg":final_cv_linf,"tol_kg":cv_tol})
        sci_gate(
            "final_grid_reconstruction_exact",
            o3r6.max_abs((residual+final_mapped).reshape(GRID)-m_map)<=1e-8,
            o3r6.max_abs((residual+final_mapped).reshape(GRID)-m_map),
        )

        # ----------------------------------------------------------------------------------
        # Rebuild durable telemetry and publish final fixed point.
        # ----------------------------------------------------------------------------------
        stage="artifact_publication"
        nonlinear_rows=[]
        assignment_rows=[]
        global_rows=[]
        cut_rows=[]
        for i in range(1,closure_iteration+1):
            ad=recovery_dir(recovery,"accepted_iterates",i)
            sn,mn,man=accepted_names(i)
            if manifest_valid(r3,ad,man,{sn,mn}):
                mm=r3.load_json(ad/mn)
                nonlinear_rows.append({
                    "iteration":i,
                    "selected_alpha_index":mm["selected_alpha_index"],
                    "selected_alpha":mm["selected_alpha"],
                    "projection_q_L2":mm["projection_q_L2"],
                    "projection_q_Linf":mm["projection_q_Linf"],
                    "active_cut_count":mm["active_cut_count"],
                    "raw_fixed_point_saturation_Linf":mm.get("raw_fixed_point_saturation_Linf"),
                    "pressure_relative_L2_change":mm.get("pressure_relative_L2_change"),
                    "grid_mass_Linf_change_kg":mm.get("grid_mass_Linf_change_kg"),
                    "provisional_converged":mm["provisional_converged"],
                })
                for cr in mm.get("cut_telemetry", []):
                    cut_rows.append(dict(cr))
            for ss in range(1,6):
                sd=recovery_dir(recovery,"lex_stages",i)/f"stage_{ss}"
                ssn,smn,sbn,sman=stage_names(i,ss)
                if manifest_valid(r3,sd,sman,{ssn,smn,sbn}):
                    assignment_rows.append(r3.load_json(sd/smn)["telemetry"])
            groot=recovery/"globalization"/f"iteration_{i:03d}"
            if groot.is_dir():
                for ap in sorted(groot.glob(f"alpha_*_of_{LINE_DEN}")):
                    for rd in sorted(ap.glob("round_*")):
                        try:
                            ai=int(ap.name.split("_")[1]); rr=int(rd.name.split("_")[1])
                        except Exception:
                            continue
                        csn,crn,cman=candidate_names(i,ai,rr)
                        if manifest_valid(r3,rd,cman,{csn,crn}):
                            rec=r3.load_json(rd/crn)
                            global_rows.append({
                                "iteration":i,"alpha_index":ai,"alpha":rec["alpha"],
                                "round":rr,"active_cut_count":rec["active_cut_count"],
                                "classification":rec["classification"],
                                "minimum_unserved_mass_kg":rec["minimum_unserved_mass_kg"],
                                "q_L2":rec["q_L2"],"q_Linf":rec["q_Linf"],
                            })

        checkpoint=o3r6.deterministic_npz_bytes({
            "event_day":np.asarray(EVENT_DAY),
            "physical_time_advanced_in_R3R6":np.asarray(False),
            "generalized_fixed_point_iteration_count":np.asarray(closure_iteration,dtype=np.int64),
            "converged_pressure_psi":closure_pressure,
            "converged_saturation":closure_sat,
            "converged_event_grid_component_mass_kg":m_map,
            "converged_event_mapped_grid_mass_kg":final_mapped.reshape(GRID),
            "frozen_residual_grid_component_mass_kg":residual_grid,
            "converged_cell_capacity_kg":closure_cap,
            "event_CV_component_mass_kg":event_cv_mass,
            "E2_pair_cv_id":e2_cv,
            "E2_pair_flat_cell":e2_cell,
            "E2_pair_is_E0":is_e0,
            "E2_pair_is_E1":is_e1,
            "E2_pair_converged_mass_kg":full_x,
            "grid_pore_volume_m3":grid_pv,
            "reference_gas_pressure_pa":np.asarray(p_ref),
        })
        summary={
            "milestone":MILESTONE,"status":STATUS_PASS,"event_day":EVENT_DAY,
            "highspy_version":highspy.Highs().version(),
            "generalized_fixed_point_converged":True,
            "generalized_fixed_point_iteration_count":closure_iteration,
            "original_undamped_convergence_certified":True,
            "projection_vanished_at_final_PASS":True,
            "final_selected_alpha":1.0,
            "final_projection_q_Linf":float(ameta["projection_q_Linf"]),
            "final_closure_pressure_relative_L2":closure_pressure_delta,
            "final_closure_saturation_Linf_change":closure_sat_delta,
            "final_CV_mass_Linf_error_kg":final_cv_linf,
            "final_maximum_cell_capacity_excess_kg":closure_grid_excess,
            "final_cellwise_EOS_mass_error_kg":closure_cell_mass_error,
            "final_global_EOS_mass_relative_error":closure_global_rel,
            "minimum_selected_alpha":min(float(r["selected_alpha"]) for r in nonlinear_rows),
            "active_set_globalization_used":any(float(r["projection_q_Linf"] or 0.0)>0 for r in nonlinear_rows),
            "support_domain_changed":False,"capacity_relaxed":False,"per_CV_mass_relaxed":False,
            "mass_clipped_or_discarded":False,"global_rescaling_performed":False,
            "Darcy_Pollock_TOF_executed":False,"reprojection_executed":False,
            "physical_time_advanced":False,
        }
        decision={
            "milestone":MILESTONE,"status":STATUS_PASS,
            "next_milestone":(
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R7 — "
                "single converged-state Darcy / Pollock / TOF flow-geometry refresh"
            ),
            "O3R7_authorized":True,
            "O3R7_must_use_R3R6_certified_fixed_point":True,
            "R3R3R4_authorized":False,
            "F5_dataset_generation_authorized":False,
            "training_authorized":False,
            "automatic_second_event_refresh_authorized":False,
            "physical_time_advance_authorized":False,
        }
        files={
            FINAL_SUMMARY:r3.json_bytes(summary),
            FINAL_STATE:checkpoint,
            FINAL_NONLIN:r3.csv_bytes(nonlinear_rows),
            FINAL_ASSIGN:r3.csv_bytes(assignment_rows),
            FINAL_GLOBAL:r3.csv_bytes(global_rows),
            FINAL_CUTS:r3.csv_bytes(cut_rows),
            FINAL_DECISION:r3.json_bytes(decision),
            FINAL_GATES:r3.csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
        }
        r3.immutable_publish(out,files)
        r3.immutable_publish(
            out,{FINAL_MANIFEST:r3.csv_bytes([
                {"file":p.name,"sha256":r3.sha256_file(p),"bytes":p.stat().st_size}
                for p in sorted(out.iterdir()) if p.is_file() and p.name!=FINAL_MANIFEST
            ])}
        )

        print()
        print("="*214)
        print(MILESTONE+": PASS")
        print("="*214)
        print("Converged iteration          :",closure_iteration)
        print("Selected final alpha         : 1")
        print("Final projection q Linf      :",ameta["projection_q_Linf"])
        print("Original undamped fixed point: CERTIFIED")
        print("Final frozen closure         : CERTIFIED")
        print("O3-R7                        : AUTHORIZED")
        print("Darcy/Pollock/TOF in R3-R6  : NOT EXECUTED")
        print("Physical-time advance        : False")
        print("="*214)
        return 0

    except ScientificFail as exc:
        failed.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":MILESTONE,"status":STATUS_FAIL,
            "failed_stage":stage,"failed_gate":exc.gate,"detail":exc.detail,
            "current_iteration":int(current_iteration),
            "pressure_solve_executed":bool(pressure_solve_executed),
            "assignment_executed":bool(assignment_executed),
            "generalized_iteration_executed":bool(generalized_iteration_executed),
            "support_domain_changed":False,"capacity_relaxed":False,
            "per_CV_mass_relaxed":False,"mass_clipped_or_discarded":False,
            "global_rescaling_performed":False,"Darcy_Pollock_TOF_executed":False,
            "reprojection_executed":False,"physical_time_advanced":False,
            "automatic_rerun_authorized":False,"O3R7_authorized":False,
            "R3R3R4_authorized":False,"F5_dataset_generation_authorized":False,
            "training_authorized":False,"recovery_checkpoints_preserved":True,
        }
        p=failed/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Scientific_Fail_Report.json"
        if not p.exists(): p.write_bytes((json.dumps(report,indent=2,sort_keys=True)+"\n").encode())
        print()
        print(MILESTONE+": SCIENTIFIC FAIL")
        print("Stage:",stage); print("Gate:",exc.gate); print("Detail:",exc.detail)
        print("RECOVERY CHECKPOINTS PRESERVED. NO AUTOMATIC RERUN AUTHORIZED.")
        return 3

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":MILESTONE,"status":STATUS_BLOCK,
            "failed_stage":stage,"exception":repr(exc),"gates":gates,
            "current_iteration":int(current_iteration),
            "pressure_solve_executed":bool(pressure_solve_executed),
            "assignment_executed":bool(assignment_executed),
            "generalized_iteration_executed":bool(generalized_iteration_executed),
            "support_domain_changed":False,"physical_time_advanced":False,
            "automatic_rerun_authorized":False,"O3R7_authorized":False,
            "recovery_checkpoints_preserved":True,
        }
        p=blocked/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Blocked_Report.json"
        if not p.exists(): p.write_bytes((json.dumps(report,indent=2,sort_keys=True)+"\n").encode())
        print()
        print(MILESTONE+": TECHNICAL / AUTHORITY BLOCK")
        print("Stage:",stage); print("Exception:",repr(exc))
        return 2

    finally:
        for solver in solvers:
            try: solver.close()
            except Exception: pass


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--verbose-solver",action="store_true")
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()


if __name__=="__main__":
    args=parse_args()
    if args.self_test:
        self_test(); raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root,args.verbose_solver))
