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

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3-R3"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R4R3R3_CONTROLLED_ALPHA_DEPENDENT_BOX_CONSTRAINED_"
    "TANGENT_CANDIDATE_FEASIBILITY_TEST_PASS_PROSPECTIVE_COMPUTATIONAL_"
    "CANDIDATE_ONLY_NO_FIVE_STAGE_ASSIGNMENT_NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_FAIL = (
    "AV4F4R3R3R3R3R3O3R6R4R3R3_CONTROLLED_ALPHA_DEPENDENT_BOX_CONSTRAINED_"
    "TANGENT_CANDIDATE_FEASIBILITY_TEST_SCIENTIFIC_FAIL_NO_AUTOMATIC_RERUN_"
    "NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R4R3R3_TECHNICAL_OR_AUTHORITY_BLOCK"

PARENT_R3R2_COMMIT = "f1d17ed091ced46d8bd64c6730eb5b9ce919df80"

R3R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_"
    "Alpha_Dependent_Box_Constrained_Tangent_Projection_Semantics_Design_Freeze.py"
)
R3R2_BLOB = "4e5b643ed212ef3432d43026993931325256d28a"
R3R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_"
    "Saturation_Box_Tangent_Correction_Compatibility_ReadOnly_Audit.py"
)
R3R1_BLOB = "aaf38a0a271e05b04c0d17f93ca07d2a69bdfea3"
R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_"
    "Controlled_SingleCut_Projected_Direction_OneStep_Feasibility_Test.py"
)
R3_BLOB = "059b3379115b3cabc215a16d1a1fca82ad0ca88a"
R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_"
    "Projected_Tangent_Constrained_Update_Semantics_Design_Freeze.py"
)
R2_BLOB = "687a35265bf0fe72a2110e2f91dab78cac5805b8"
R4 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_"
    "Controlled_Adaptive_Feasibility_Preserving_Stabilized_Coupled_Execution.py"
)
R4_BLOB = "c41cd5c78e7cc2d91e1920e538f1793037961a31"
R3DESIGN = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_"
    "Adaptive_Feasibility_Preserving_Stabilization_Semantics_Design_Freeze.py"
)
R3DESIGN_BLOB = "c118972a991e4ae0ce7200a9f880a73407450b8b"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R3R2_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_"
    "Alpha_Dependent_Box_Constrained_Tangent_Projection_Semantics_Design_Freeze"
)
R3R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Summary.json"
R3R2_OPERATOR = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Alpha_Dependent_Box_Projection_Operator_Contract.json"
R3R2_CANDIDATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Candidate_Family_Contract.json"
R3R2_CERT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Exact_Candidate_Certification_Contract.json"
R3R2_CONV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Convergence_Preservation_Contract.json"
R3R2_CHECKPOINT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Checkpoint_Restart_Policy.json"
R3R2_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Decision_Contract.json"
R3R2_GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Final_Gate_Matrix.csv"
R3R2_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Artifact_Manifest.csv"
EXPECTED_R3R2_FILES = {
    R3R2_SUMMARY, R3R2_OPERATOR, R3R2_CANDIDATES, R3R2_CERT,
    R3R2_CONV, R3R2_CHECKPOINT, R3R2_DECISION, R3R2_GATES,
}

R3_RECOVERY = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Recovery_Checkpoints"
R4_RECOVERY = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Recovery_Checkpoints"

OUT = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_"
    "Controlled_AlphaDependent_BoxConstrained_Tangent_Candidate_Feasibility_Test"
)
RECOVERY = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_Recovery_Checkpoints"
FAIL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_SCIENTIFIC_FAIL"
BLOCK = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_BLOCKED"

SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_Summary.json"
STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_Selected_Candidate_State.npz"
CANDIDATE_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_Candidate_Results.csv"
DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_Decision_Contract.json"
GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_Final_Gate_Matrix.csv"
MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_Artifact_Manifest.csv"

GRID = (15,50,50)
NCELL = 37500
NCVTOTAL = 215600
EXPECTED_E2 = 3091073
INJECTED = 0.80
LINE_DEN = 1024
CANDIDATE_INDICES = [8,4,2,1]
S_MIN = 0.20
S_MAX = 0.80
TANGENT_TOL = 1.0e-8
FEAS_UNSERVED_TOL = 1.0e-6
FEAS_CV_LINF_TOL = 1.0e-6
FEAS_CAP_EXCESS_TOL = 1.0e-6


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


def candidate_names(index: int) -> tuple[str,str,str]:
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_"
        f"Alpha_{index:04d}_of_{LINE_DEN}"
    )
    return stem+"_State.npz", stem+"_Result.json", stem+"_Manifest.csv"


def checkpoint_valid(r3design, d: Path, manifest: str, expected: set[str]) -> bool:
    if not d.is_dir() or not (d/manifest).is_file():
        return False
    try:
        return set(r3design.verify_manifest(d,manifest)) == expected
    except Exception:
        return False


def self_test() -> None:
    assert CANDIDATE_INDICES == [8,4,2,1]
    assert [i/LINE_DEN for i in CANDIDATE_INDICES] == [1/128,1/256,1/512,1/1024]
    print("POSTV16 O3-R6-R4-R3-R3 alpha-dependent candidate test structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT
    recovery = drive / RECOVERY
    failed = drive / FAIL
    blocked = drive / BLOCK

    gates: dict[str,dict[str,Any]] = {}
    stage = "preflight"
    pressure_solve_executed = False
    feasibility_lp_executed = False

    def gate(name: str, cond: bool, detail: Any=None):
        gates[name] = {"status":"PASS" if cond else "FAIL","detail":detail}
        if not cond:
            raise GateError(f"{name}: {detail!r}")
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    def sci_gate(name: str, cond: bool, detail: Any=None):
        gates[name] = {"status":"PASS" if cond else "FAIL","detail":detail}
        if not cond:
            raise ScientificFail(name,detail)
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    if (out/MANIFEST).is_file():
        print("[PASS] existing immutable O3-R6-R4-R3-R3 PASS detected; no rerun")
        return 0
    fail_report = failed/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_Scientific_Fail_Report.json"
    if fail_report.is_file():
        print("[FAIL] existing immutable O3-R6-R4-R3-R3 scientific FAIL detected; automatic rerun prohibited")
        return 3
    block_report = blocked/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_Blocked_Report.json"
    if block_report.is_file():
        print("[BLOCK] existing immutable O3-R6-R4-R3-R3 technical/authority block detected")
        return 2

    print("="*214)
    print(MILESTONE+" -- CONTROLLED ALPHA-DEPENDENT BOX-CONSTRAINED TANGENT CANDIDATE FEASIBILITY TEST")
    print("="*214)
    print("FOUR INDEPENDENT PROSPECTIVE CANDIDATES: 1/128, 1/256, 1/512, 1/1024.")
    print("EACH CANDIDATE RECOMPUTES q_alpha. NO MONOTONIC LINE-SEARCH ASSUMPTION.")
    print("NO FIVE-STAGE ASSIGNMENT. NO NONLINEAR STATE ACCEPTANCE. NO SUPPORT EXPANSION. NO TIME ADVANCE.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root,"rev-parse","HEAD^")
        dirty = git_text(root,"status","--porcelain")
        gate("repository_parent_is_R3R2_commit",parent==PARENT_R3R2_COMMIT,parent)
        gate("repository_clean",dirty=="",repr(dirty))

        for fn,expected in {
            R3R2:R3R2_BLOB,R3R1:R3R1_BLOB,R3:R3_BLOB,R2:R2_BLOB,
            R4:R4_BLOB,R3DESIGN:R3DESIGN_BLOB,
        }.items():
            p=root/fn
            actual=git_blob(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        r3r2 = load_module(root/R3R2,"postv16_o3r6r4r3r3_r3r2")
        r3r1 = load_module(root/R3R1,"postv16_o3r6r4r3r3_r3r1")
        r3test = load_module(root/R3,"postv16_o3r6r4r3r3_r3test")
        r2 = load_module(root/R2,"postv16_o3r6r4r3r3_r2")
        r4 = load_module(root/R4,"postv16_o3r6r4r3r3_r4")
        r3design = load_module(root/R3DESIGN,"postv16_o3r6r4r3r3_r3design")
        o3r4 = load_module(root/r4.O3R4,"postv16_o3r6r4r3r3_o3r4")
        o3r6 = load_module(root/r4.O3R6,"postv16_o3r6r4r3r3_o3r6")
        a2e = load_module(root/r4.A2E,"postv16_o3r6r4r3r3_a2e")
        r2phys = load_module(root/r4.R2PHYS,"postv16_o3r6r4r3r3_r2phys")
        sg2 = load_module(root/r4.SG2,"postv16_o3r6r4r3r3_sg2")
        sg3 = load_module(root/r4.SG3,"postv16_o3r6r4r3r3_sg3")
        r3r2r1 = load_module(root/r4.R3R2R1,"postv16_o3r6r4r3r3_r3r2r1")

        for fn in [r4.O3R4,r4.O3R6,r4.A2E,r4.R2PHYS,r4.SG2,r4.SG3,r4.R3R2R1,r4.O2,r4.PERM]:
            expected = r4.SOURCE_BLOBS[fn]
            p = root/fn
            actual = git_blob(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        import highspy
        from scipy.sparse import coo_matrix
        gate("highspy_version_exact_1_15_1",highspy.Highs().version()=="1.15.1",highspy.Highs().version())

        stage = "R3R2_contract_binding"
        r3r2d = drive/R3R2_REL
        gate("R3R2_output_present",r3r2d.is_dir(),str(r3r2d))
        manifest = r3design.verify_manifest(r3r2d,R3R2_MANIFEST)
        gate("R3R2_manifest_payload_exact",set(manifest)==EXPECTED_R3R2_FILES,sorted(manifest))

        s32 = r3design.load_json(r3r2d/R3R2_SUMMARY)
        op32 = r3design.load_json(r3r2d/R3R2_OPERATOR)
        cf32 = r3design.load_json(r3r2d/R3R2_CANDIDATES)
        cert32 = r3design.load_json(r3r2d/R3R2_CERT)
        dec32 = r3design.load_json(r3r2d/R3R2_DECISION)

        gate(
            "R3R2_PASS_exact",
            s32.get("status")==r3r2.STATUS_PASS
            and s32.get("design_only") is True
            and s32.get("alpha_dependent_correction") is True
            and s32.get("single_projected_direction") is False
            and s32.get("monotonic_line_search_assumption") is False
            and s32.get("candidate_indices_largest_first")==CANDIDATE_INDICES
            and s32.get("pressure_solve_executed") is False
            and s32.get("feasibility_LP_executed") is False
            and s32.get("five_stage_assignment_executed") is False
            and s32.get("physical_time_advanced") is False,
        )
        gate(
            "R3R2_authorizes_R3R3_only",
            dec32.get("O3R6R4R3R3_controlled_candidate_test_authorized") is True
            and dec32.get("O3R6R4R3R3_full_fixed_point_execution_authorized") is False
            and dec32.get("O3R6R4R3R3_five_stage_assignment_authorized") is False
            and dec32.get("automatic_R3_rerun_authorized") is False
            and dec32.get("sub_1_over_1024_step_authorized") is False
            and dec32.get("support_expansion_authorized") is False
            and dec32.get("O3R7_authorized") is False,
        )
        gate(
            "candidate_family_exact",
            cf32.get("candidate_indices_largest_first")==CANDIDATE_INDICES
            and cf32.get("evaluation_rule","").startswith("Evaluate all four candidates independently")
            and cf32.get("no_binary_refinement") is True
            and cf32.get("no_sub_1_over_1024_candidate") is True,
        )

        # Bind original R2 cut contract for IDs/demand and R3 frozen sensitivity vector.
        r2d = drive/r2.OUT
        r3design.verify_manifest(r2d,r2.MANIFEST)
        op2 = r3design.load_json(r2d/r2.OPERATOR)
        cut_cv_ids = np.asarray(op2["cut_definition"]["CV_ids"],dtype=np.int64)
        cut_cell_ids = np.asarray(op2["cut_definition"]["cell_ids"],dtype=np.int64)
        cut_demand = float(op2["cut_definition"]["demand_kg"])
        a_raw = float(op32["base_objects"]["a_raw_kg_per_full_step"])
        gate(
            "cut_contract_exact",
            cut_cv_ids.size==67 and cut_cell_ids.size==24 and 60424 in cut_cv_ids.tolist()
            and abs(a_raw-53.3337138146162)<=1e-10,
            {"cut_CVs":int(cut_cv_ids.size),"cut_cells":int(cut_cell_ids.size),"a_raw":a_raw},
        )

        # O2 / A2E immutable physics inputs.
        stage = "immutable_state_binding"
        o2d = drive/r4.O2_REL
        r3design.verify_manifest(o2d,r4.O2_MANIFEST)
        with np.load(o2d/r4.O2_STATE,allow_pickle=False) as z:
            demand=np.asarray(z["event_CV_component_mass_kg"],dtype=np.float64).reshape(-1)
            e2_cv=np.asarray(z["E2_pair_cv_id"],dtype=np.int64)
            e2_cell=np.asarray(z["E2_pair_flat_cell"],dtype=np.int64)
            residual_grid=np.asarray(z["frozen_residual_grid_component_mass_kg"],dtype=np.float64)
            grid_pv=np.asarray(z["grid_pore_volume_m3"],dtype=np.float64)
            p_ref=float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
        gate(
            "O2_state_shapes_exact",
            demand.shape==(NCVTOTAL,) and e2_cv.shape==(EXPECTED_E2,) and e2_cell.shape==(EXPECTED_E2,)
            and residual_grid.shape==GRID and grid_pv.shape==GRID,
        )
        residual=residual_grid.reshape(-1)

        a2d = drive/r4.A2E_REL
        r3design.verify_manifest(a2d,r4.A2E_MANIFEST)
        with np.load(a2d/r4.A2E_EPOCH,allow_pickle=False) as z:
            epoch={k:np.asarray(z[k]).copy() for k in z.files}
        grid_nw=np.asarray(epoch["nw"],dtype=np.float64)
        grid_no=np.asarray(epoch["no"],dtype=np.float64)
        grid_krw=np.asarray(epoch["krw_max"],dtype=np.float64)
        grid_kro=np.asarray(epoch["kro_max"],dtype=np.float64)

        # R4 immutable base/map pair.
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
        gate(
            "R4_base_map_pair_exact",
            r4.array_sha256(S_base)==r4.array_sha256(S_iter_map),
            r4.array_sha256(S_base),
        )
        d_raw=S_map-S_base

        # Reuse exact 24-component g from immutable R3 sensitivity probe checkpoints.
        stage = "R3_sensitivity_binding"
        probe_root=drive/R3_RECOVERY/"sensitivity_probes"
        g=np.zeros(24,dtype=np.float64)
        for local_index,cell in enumerate(cut_cell_ids):
            pn,pm=r3test.probe_names(local_index,int(cell))
            pd=probe_root/f"probe_{local_index:02d}_cell_{int(cell):05d}"
            gate(
                f"probe_{local_index:02d}_checkpoint_valid",
                r3test.checkpoint_manifest_valid(r3design,pd,pm,{pn}),
                str(pd),
            )
            rec=r3design.load_json(pd/pn)
            g[local_index]=float(rec["sensitivity_kg_per_saturation"])
        gate(
            "g_exact_norms",
            abs(float(np.linalg.norm(g))-1.2493304995770507)<=1e-12
            and abs(float(np.max(np.abs(g)))-0.7448965334333478)<=1e-12,
            {"g_L2":float(np.linalg.norm(g)),"g_Linf":float(np.max(np.abs(g)))},
        )

        # Pressure/capacity exact physics.
        stage = "pressure_physics_setup"
        permeability_md=np.loadtxt(root/r4.PERM,skiprows=1,dtype=np.float64).reshape(GRID,order="C")
        kx,ky,kz=sg2.build_directional_permeability(permeability_md)
        kfx,kfy,kfz=sg2.build_face_permeabilities(kx,ky,kz)
        tx_ref,ty_ref,tz_ref=sg3.construct_si_transmissibilities(kfx,kfy,kfz)

        def pressure_step(S: np.ndarray) -> tuple[np.ndarray,float]:
            mobility=a2e.spatial_mobility(S,grid_nw,grid_no,grid_krw,grid_kro)
            tx,ty,tz,_=r3r2r1.build_updated_transmissibilities(
                sg3,tx_ref,ty_ref,tz_ref,mobility["lambda_total"]
            )
            A,b,_=r3r2r1.assemble_updated_pressure_system(
                sg3,permeability_md,tx,ty,tz,mobility["lambda_total"]
            )
            _ppa,ppsi,reslin=r3r2r1.solve_updated_pressure(sg3,A,b)
            return np.asarray(ppsi,dtype=np.float64),float(reslin)

        def capacity(S: np.ndarray) -> tuple[np.ndarray,np.ndarray,float,float]:
            nonlocal pressure_solve_executed
            p,pres=pressure_step(S)
            pressure_solve_executed=True
            cap=np.asarray(
                a2e.local_mass(r2phys,np.full(GRID,INJECTED),p,p_ref,grid_pv),
                dtype=np.float64,
            )
            avail_raw=cap.reshape(-1)-residual
            cap_tol=max(1e-8,1e-12*max(float(np.max(np.abs(cap))),1.0))
            if float(np.min(avail_raw)) < -cap_tol:
                raise ScientificFail(
                    "candidate_residual_sidecar_capacity",
                    {"minimum_available_mapped_capacity_kg":float(np.min(avail_raw)),
                     "tolerance_kg":cap_tol},
                )
            avail=np.maximum(avail_raw,0.0)
            cut_deficit=cut_demand-float(np.sum(avail[cut_cell_ids]))
            return p,cap,float(pres),float(cut_deficit),avail

        # Evaluate all four candidates independently.
        stage = "four_candidate_exact_certification"
        cand_root=recovery/"candidates"
        results: dict[int,dict[str,Any]]={}
        sflat=S_base.reshape(-1)
        drflat=d_raw.reshape(-1)
        sb=sflat[cut_cell_ids]
        dr=drflat[cut_cell_ids]
        target=-a_raw

        for idx in CANDIDATE_INDICES:
            alpha=idx/LINE_DEN
            cd=cand_root/f"alpha_{idx:04d}_of_{LINE_DEN}"
            sn,rn,mn=candidate_names(idx)

            if checkpoint_valid(r3design,cd,mn,{sn,rn}):
                rr=r3design.load_json(cd/rn)
                results[idx]=rr
                print(
                    f"[REUSE] alpha={alpha:.9f} feasible={rr['exact_frozen_E2_feasible']} "
                    f"unserved={rr.get('minimum_unserved_mass_kg')}"
                )
                continue

            lo=(S_MIN-sb)/alpha-dr
            hi=(S_MAX-sb)/alpha-dr
            dot_min,dot_max=r3r1.bounded_dot_range(g,lo,hi)
            sci_gate(
                f"alpha_{idx:04d}_analytical_box_tangent_feasible",
                target >= dot_min-r3r1.TARGET_TOL and target <= dot_max+r3r1.TARGET_TOL,
                {"target":target,"dot_min":dot_min,"dot_max":dot_max},
            )
            q=r3r1.min_norm_box_hyperplane(g,lo,hi,target)
            tangent_residual=a_raw+float(np.dot(g,q))
            sci_gate(
                f"alpha_{idx:04d}_tangent_residual",
                abs(tangent_residual)<=TANGENT_TOL,
                tangent_residual,
            )

            d_candidate=drflat.copy()
            d_candidate[cut_cell_ids]+=q
            S_trial=(sflat+alpha*d_candidate).reshape(GRID)
            smin=float(np.min(S_trial)); smax=float(np.max(S_trial))
            sci_gate(
                f"alpha_{idx:04d}_saturation_box",
                smin>=S_MIN-1e-10 and smax<=S_MAX+1e-10,
                {"min":smin,"max":smax},
            )

            p,cap,pres,cut_deficit,available=capacity(S_trial)
            sci_gate(
                f"alpha_{idx:04d}_pressure_residual",
                pres<1.0e-8,
                pres,
            )

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
                f"alpha_{idx:04d}_LP_certification",
                cv_linf<=FEAS_CV_LINF_TOL and cap_excess<=FEAS_CAP_EXCESS_TOL,
                {"CV_Linf_kg":cv_linf,"capacity_excess_kg":cap_excess},
            )
            unserved=float(np.sum(u))
            ids=np.flatnonzero(u>FEAS_UNSERVED_TOL).astype(np.int64)
            vals=u[ids].astype(np.float64)
            feasible=unserved<=FEAS_UNSERVED_TOL

            active_lower=int(np.count_nonzero(np.isclose(q,lo,rtol=0,atol=1e-9)))
            active_upper=int(np.count_nonzero(np.isclose(q,hi,rtol=0,atol=1e-9)))

            rr={
                "milestone":MILESTONE,
                "alpha_index":int(idx),
                "alpha_denominator":LINE_DEN,
                "alpha":alpha,
                "exact_frozen_E2_feasible":bool(feasible),
                "minimum_unserved_mass_kg":unserved,
                "unserved_CV_count_above_1e6_kg":int(ids.size),
                "unserved_CV_ids":[int(v) for v in ids],
                "unserved_CV_values_kg":[float(v) for v in vals],
                "pressure_linear_relative_residual":pres,
                "cut_signed_deficit_kg":cut_deficit,
                "CV_equality_Linf_kg":cv_linf,
                "maximum_cell_capacity_excess_kg":cap_excess,
                "active_exact_zero_pruned_E2_edges":int(nedge),
                "matrix_nnz":int(nnz),
                "q_L2":float(np.linalg.norm(q)),
                "q_Linf":float(np.max(np.abs(q))),
                "q_active_lower_bound_count":active_lower,
                "q_active_upper_bound_count":active_upper,
                "tangent_residual_kg_per_full_step":tangent_residual,
                "trial_saturation_minmax":[smin,smax],
                "solver_telemetry":tel,
                "physical_state_authority":False,
                "physical_time_advanced":False,
            }
            arrays={
                "S_trial":S_trial,
                "pressure_psi":p,
                "cell_capacity_kg":cap,
                "available_mapped_capacity_kg":available.reshape(GRID),
                "q_alpha":q,
                "cut_cell_ids":cut_cell_ids,
                "unserved_CV_ids":ids,
                "unserved_CV_values_kg":vals,
            }
            r3design.immutable_publish(
                cd,
                {sn:o3r6.deterministic_npz_bytes(arrays),rn:r3design.json_bytes(rr)}
            )
            r3design.immutable_publish(
                cd,
                {mn:r3design.csv_bytes([
                    {"file":n,"sha256":r3design.sha256_file(cd/n),"bytes":(cd/n).stat().st_size}
                    for n in (sn,rn)
                ])}
            )
            results[idx]=rr
            print(
                f"[CHECKPOINT] alpha={alpha:.9f} feasible={feasible} "
                f"unserved={unserved:.12e} cut_deficit={cut_deficit:.12e}"
            )
            sys.stdout.flush()

        feasible_indices=[
            idx for idx in CANDIDATE_INDICES if bool(results[idx]["exact_frozen_E2_feasible"])
        ]
        sci_gate(
            "at_least_one_alpha_dependent_candidate_exactly_feasible",
            len(feasible_indices)>=1,
            {"feasible_indices":feasible_indices,
             "feasible_alphas":[i/LINE_DEN for i in feasible_indices]},
        )
        selected_idx=max(feasible_indices)
        selected_alpha=selected_idx/LINE_DEN
        selected=results[selected_idx]

        # Load selected checkpoint state for final immutable output.
        selected_dir=cand_root/f"alpha_{selected_idx:04d}_of_{LINE_DEN}"
        ssn,srn,smn=candidate_names(selected_idx)
        gate(
            "selected_candidate_checkpoint_valid",
            checkpoint_valid(r3design,selected_dir,smn,{ssn,srn}),
            str(selected_dir),
        )
        with np.load(selected_dir/ssn,allow_pickle=False) as z:
            selected_state={k:np.asarray(z[k]).copy() for k in z.files}

        candidate_rows=[]
        for idx in CANDIDATE_INDICES:
            rr=results[idx]
            candidate_rows.append({
                "alpha_index":idx,
                "alpha":idx/LINE_DEN,
                "exact_frozen_E2_feasible":bool(rr["exact_frozen_E2_feasible"]),
                "minimum_unserved_mass_kg":rr["minimum_unserved_mass_kg"],
                "unserved_CV_count":rr["unserved_CV_count_above_1e6_kg"],
                "cut_signed_deficit_kg":rr["cut_signed_deficit_kg"],
                "pressure_linear_relative_residual":rr["pressure_linear_relative_residual"],
                "CV_equality_Linf_kg":rr["CV_equality_Linf_kg"],
                "maximum_cell_capacity_excess_kg":rr["maximum_cell_capacity_excess_kg"],
                "q_L2":rr["q_L2"],
                "q_Linf":rr["q_Linf"],
                "q_active_lower_bound_count":rr["q_active_lower_bound_count"],
                "q_active_upper_bound_count":rr["q_active_upper_bound_count"],
                "tangent_residual_kg_per_full_step":rr["tangent_residual_kg_per_full_step"],
                "trial_saturation_min":rr["trial_saturation_minmax"][0],
                "trial_saturation_max":rr["trial_saturation_minmax"][1],
                "selected":idx==selected_idx,
            })

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "operator_id":op32["operator_id"],
            "candidate_family_id":cf32["candidate_family_id"],
            "candidate_count":4,
            "candidate_indices_evaluated":CANDIDATE_INDICES,
            "candidate_alphas_evaluated":[i/LINE_DEN for i in CANDIDATE_INDICES],
            "feasible_candidate_indices":feasible_indices,
            "feasible_candidate_alphas":[i/LINE_DEN for i in feasible_indices],
            "selected_alpha_index":selected_idx,
            "selected_alpha":selected_alpha,
            "selected_minimum_unserved_mass_kg":selected["minimum_unserved_mass_kg"],
            "selected_cut_signed_deficit_kg":selected["cut_signed_deficit_kg"],
            "selected_q_L2":selected["q_L2"],
            "selected_q_Linf":selected["q_Linf"],
            "selected_trial_saturation_minmax":selected["trial_saturation_minmax"],
            "pressure_solve_executed":bool(pressure_solve_executed),
            "feasibility_LP_executed":bool(feasibility_lp_executed),
            "five_stage_assignment_executed":False,
            "full_fixed_point_execution_performed":False,
            "prospective_candidate_physical_state_authority":False,
            "state_mutated":False,
            "support_domain_changed":False,
            "capacity_relaxed":False,
            "per_CV_mass_relaxed":False,
            "physical_time_advanced":False,
        }

        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "scientific_interpretation":(
                "At least one alpha-dependent box-constrained tangent candidate from "
                "the R3-R2 four-candidate family is exactly frozen-E2 feasible under "
                "the unchanged pressure/capacity physics. This validates the local "
                "box-constrained projected-direction concept for the immutable R4 "
                "iteration-1 base/map pair only; it does not establish a general "
                "active-set nonlinear solver or a physical fixed point."
            ),
            "next_milestone":(
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3-R4 — "
                "generalized active-set box-constrained projected coupled-solver "
                "semantics design freeze"
            ),
            "O3R6R4R3R4_generalized_solver_design_freeze_authorized":True,
            "O3R6R4R3R4_execution_authorized":False,
            "full_fixed_point_execution_authorized":False,
            "five_stage_assignment_execution_authorized":False,
            "selected_prospective_candidate_acceptance_authorized":False,
            "automatic_R3R3_rerun_authorized":False,
            "support_expansion_authorized":False,
            "capacity_relaxation_authorized":False,
            "per_CV_mass_relaxation_authorized":False,
            "sub_1_over_1024_step_authorized":False,
            "O3R7_authorized":False,
            "R3R3R4_authorized":False,
            "F5_dataset_generation_authorized":False,
            "training_authorized":False,
        }

        final_state={
            "S_base":S_base,
            "S_map":S_map,
            "d_raw":d_raw,
            "cut_CV_ids":cut_cv_ids,
            "cut_cell_ids":cut_cell_ids,
            "cut_sensitivity_g":g,
            "selected_alpha_index":np.asarray(selected_idx,dtype=np.int64),
            "selected_alpha":np.asarray(selected_alpha,dtype=np.float64),
            **selected_state,
        }

        r3design.immutable_publish(
            out,
            {
                SUMMARY:r3design.json_bytes(summary),
                STATE:o3r6.deterministic_npz_bytes(final_state),
                CANDIDATE_CSV:r3design.csv_bytes(candidate_rows),
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
        print(MILESTONE+": CONTROLLED CANDIDATE TEST PASS")
        print("="*214)
        print("Evaluated candidates          :", [i/LINE_DEN for i in CANDIDATE_INDICES])
        print("Feasible candidates           :", [i/LINE_DEN for i in feasible_indices])
        print("Selected largest feasible     :", selected_idx,"/",LINE_DEN,"=",selected_alpha)
        print("Selected min unserved kg      :", selected["minimum_unserved_mass_kg"])
        print("Selected cut deficit kg       :", selected["cut_signed_deficit_kg"])
        print("Five-stage assignment         : False")
        print("Prospective candidate authority: False")
        print("R3-R4 generalized design      : AUTHORIZED")
        print("Full fixed-point execution    : NOT AUTHORIZED")
        print("O3-R7                         : NOT AUTHORIZED")
        print("="*214)
        return 0

    except ScientificFail as exc:
        failed.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":MILESTONE,
            "status":STATUS_FAIL,
            "failed_stage":stage,
            "failed_gate":exc.gate,
            "detail":exc.detail,
            "gates":gates,
            "pressure_solve_executed":bool(pressure_solve_executed),
            "feasibility_LP_executed":bool(feasibility_lp_executed),
            "five_stage_assignment_executed":False,
            "full_fixed_point_execution_performed":False,
            "state_mutated":False,
            "support_domain_changed":False,
            "physical_time_advanced":False,
            "automatic_rerun_authorized":False,
            "O3R7_authorized":False,
            "F5_dataset_generation_authorized":False,
        }
        p=failed/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_bytes((json.dumps(report,indent=2,sort_keys=True)+"\n").encode())
        print()
        print(MILESTONE+": SCIENTIFIC FAIL")
        print("Stage :",stage)
        print("Gate  :",exc.gate)
        print("Detail:",exc.detail)
        print("NO AUTOMATIC RERUN AUTHORIZED.")
        return 3

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":MILESTONE,
            "status":STATUS_BLOCK,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "pressure_solve_executed":bool(pressure_solve_executed),
            "feasibility_LP_executed":bool(feasibility_lp_executed),
            "five_stage_assignment_executed":False,
            "full_fixed_point_execution_performed":False,
            "state_mutated":False,
            "support_domain_changed":False,
            "physical_time_advanced":False,
            "automatic_rerun_authorized":False,
            "O3R7_authorized":False,
        }
        p=blocked/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_Blocked_Report.json"
        if not p.exists():
            p.write_bytes((json.dumps(report,indent=2,sort_keys=True)+"\n").encode())
        print()
        print(MILESTONE+": TECHNICAL / AUTHORITY BLOCK")
        print("Stage:",stage)
        print("Exception:",repr(exc))
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
