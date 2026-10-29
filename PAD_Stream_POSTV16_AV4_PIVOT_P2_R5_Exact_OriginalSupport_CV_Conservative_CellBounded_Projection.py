#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


MILESTONE = "POSTV16-AV4-PIVOT-P2-R5"
STATUS_PASS = (
    "AV4PIVOTP2R5_DAY370_EXACT_SIGN_PRESERVING_ORIGINAL_SUPPORT_"
    "CV_CONSERVATIVE_CELL_BOUNDED_PROJECTION_EXECUTION_PASS"
)
STATUS_FAIL = (
    "AV4PIVOTP2R5_DAY370_EXACT_ORIGINAL_SUPPORT_PROJECTION_"
    "SCIENTIFIC_FAIL_NO_RELAXATION_OR_AUTOMATIC_RERUN_AUTHORIZED"
)
STATUS_BLOCKED = "AV4PIVOTP2R5_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "2a2cd68688246f07e0406a60ff64079e4cfbc31f"
EXPECTED_BRANCH = "postv16-av4-pivot"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = NZ * NY * NX
NSL = 1078
NN = 201
NCV = 200
BACKGROUND = 0.20
MAX_SG = 0.60
SPD = 86400.0

CV_EQUALITY_TOL_KG = 1.0e-7
CELL_BOUND_TOL_KG = 1.0e-7
GLOBAL_LEDGER_TOL_KG = 1.0e-6
L1_OBJECTIVE_REL_TOL = 1.0e-10
SIGN_TOL_KG = 1.0e-10

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R4_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R4_Day370_Mapback_Cause_Audit_and_Repair_Selection_Freeze"
R4_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R4_Summary.json"
R4_DECISION = "POSTV16_AV4_PIVOT_P2_R4_Decision_Contract.json"
R4_REPAIR = "POSTV16_AV4_PIVOT_P2_R4_Repair_Selection_Contract.json"
R4_STATUS = (
    "AV4PIVOTP2R4_DAY370_MAPBACK_LOCAL_INVENTORY_DEFICIT_CAUSE_AUDIT_"
    "AND_REPAIR_SELECTION_FREEZE_PASS_NO_REPAIR_EXECUTED"
)
R4_SELECTED = (
    "SIGN_PRESERVING_ORIGINAL_SUPPORT_PER_CV_CONSERVATIVE_CELL_BOUNDED_PROJECTION"
)

R3_RECOVERY_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R3_Recovery"
R3_TEACHER_STATE = "Day365_to_Day370_Teacher_State.npz"
R3_TEACHER_META = "Day365_to_Day370_Teacher_Metadata.json"
R3_RUNNER_BLOB = "b02061d33f6105a06320f8843986de584293c677"

F2R3_REL = BASE_AV4 / "POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution"
F2R3_STATE = "POSTV16_AV4_F2_R3_Accepted_Parent_Restart_State.npz"

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

OUT_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_Exact_OriginalSupport_Projection_Execution"
FAIL_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_BLOCKED"

R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

SOURCE_BLOBS = {
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
    A2E:A2E_BLOB,
}


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
    ).stdout.strip()


def load_json(path: Path) -> dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()


def relative_l2(a: np.ndarray,b: np.ndarray) -> float:
    x=np.asarray(a,dtype=np.float64)
    y=np.asarray(b,dtype=np.float64)
    return float(np.linalg.norm((x-y).ravel()) / max(float(np.linalg.norm(y.ravel())),1.0e-30))


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj,indent=2,sort_keys=True)+"\n").encode("utf-8")


def csv_bytes(rows: list[dict[str,Any]]) -> bytes:
    if not rows:
        return b""
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    buf=io.StringIO(newline="")
    w=csv.DictWriter(buf,fieldnames=fields,lineterminator="\n")
    w.writeheader(); w.writerows(rows)
    return buf.getvalue().encode("utf-8")


class DSU:
    def __init__(self,n:int):
        self.p=np.arange(n,dtype=np.int64)
        self.r=np.zeros(n,dtype=np.int8)
    def find(self,x:int)->int:
        while self.p[x] != x:
            self.p[x]=self.p[self.p[x]]
            x=int(self.p[x])
        return x
    def union(self,a:int,b:int)->None:
        ra=self.find(a); rb=self.find(b)
        if ra==rb: return
        if self.r[ra] < self.r[rb]:
            ra,rb=rb,ra
        self.p[rb]=ra
        if self.r[ra]==self.r[rb]:
            self.r[ra]+=1


def self_test() -> None:
    assert R4_SELECTED.startswith("SIGN_PRESERVING_ORIGINAL_SUPPORT")
    assert NCELL == 37500
    assert CV_EQUALITY_TOL_KG > 0.0
    print("POSTV16 AV4 PIVOT P2-R5 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root=Path(project_root).resolve()
    drive=Path(drive_root).resolve()
    out=drive/OUT_REL
    fail_dir=drive/FAIL_REL
    block_dir=drive/BLOCK_REL
    stage="preflight"
    scientific_started=False

    def gate(name:str, passed:Any, value:Any=None):
        ok=bool(passed)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    def sci_gate(name:str, passed:Any, value:Any=None):
        ok=bool(passed)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok:
            raise ScientificFail(name,value)

    print("="*190)
    print("POSTV16-AV4-PIVOT-P2-R5 -- EXACT ORIGINAL-SUPPORT CV-CONSERVATIVE CELL-BOUNDED PROJECTION")
    print("="*190)
    print("EXECUTION MILESTONE. NO SUPPORT EXPANSION. NO CLIPPING. NO GLOBAL RENORMALIZATION.")
    print("DAY370 TEACHER CV STATE IS IMMUTABLE; ONLY ITS CARTESIAN MAPBACK CONTRIBUTIONS MAY BE REALLOCATED.")
    print("NO PRESSURE REFRESH. NO CADENCE SELECTION. P3 REMAINS UNAUTHORIZED.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_Summary.json"
        fail_report=fail_dir/"POSTV16_AV4_PIVOT_P2_R5_Scientific_Fail_Report.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R5_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P2-R5 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_P2R5_FAIL",not fail_report.exists(),str(fail_report))
        gate("no_preexisting_P2R5_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_P2R4_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="R4_binding"
        r4dir=drive/R4_REL
        gate("R4_output_present",r4dir.is_dir(),str(r4dir))
        r4s=load_json(r4dir/R4_SUMMARY)
        r4d=load_json(r4dir/R4_DECISION)
        r4r=load_json(r4dir/R4_REPAIR)
        gate("R4_status_exact",r4s.get("status")==R4_STATUS,r4s.get("status"))
        gate("R4_selected_semantics_exact",r4s.get("selected_repair_semantics")==R4_SELECTED,r4s.get("selected_repair_semantics"))
        gate("R4_R5_authorized",r4d.get("P2_R5_authorized") is True,r4d.get("P2_R5_authorized"))
        gate("R4_R4A_not_authorized",r4d.get("P2_R4A_support_extension_design_authorized") is False,r4d.get("P2_R4A_support_extension_design_authorized"))
        gate("R4_P3_unauthorized",r4d.get("P3_authorized") is False,r4d.get("P3_authorized"))
        gate("R4_no_repair_executed",r4s.get("repair_executed") is False,r4s.get("repair_executed"))
        gate("R4_repair_contract_name_exact",r4r.get("name")==R4_SELECTED,r4r.get("name"))
        gate("R4_required_counts_positive",
             int(r4s.get("negative_grid_cell_count",0))>0
             and int(r4s.get("culprit_CV_count",0))>0
             and int(r4s.get("connected_support_component_count",0))>0,
             {
                 "negative_cells":r4s.get("negative_grid_cell_count"),
                 "culprit_CVs":r4s.get("culprit_CV_count"),
                 "components":r4s.get("connected_support_component_count"),
             })

        stage="R3_teacher_binding"
        rec=drive/R3_RECOVERY_REL
        state_path=rec/R3_TEACHER_STATE
        meta_path=rec/R3_TEACHER_META
        gate("R3_teacher_state_present",state_path.is_file(),str(state_path))
        gate("R3_teacher_meta_present",meta_path.is_file(),str(meta_path))
        meta=load_json(meta_path)
        gate("R3_teacher_runner_blob_exact",meta.get("runner_blob")==R3_RUNNER_BLOB,meta.get("runner_blob"))
        gate("R3_teacher_state_SHA_exact",meta.get("state_sha256")==sha256_file(state_path),meta.get("state_sha256"))
        with np.load(state_path,allow_pickle=False) as z:
            future_cv_mass=np.asarray(z["future_mass"],dtype=np.float64)
            future_cv_sat=np.asarray(z["future_saturation"],dtype=np.float64)
            injected_mass=float(np.asarray(z["injected_mass_kg"]).reshape(()))
            produced_mass=float(np.asarray(z["produced_mass_kg"]).reshape(()))

        stage="authority_state_binding"
        f2path=drive/F2R3_REL/F2R3_STATE
        a2path=drive/A2E_REL/A2E_EPOCH
        a2sum=drive/A2E_REL/A2E_SUMMARY
        gate("F2R3_parent_state_present",f2path.is_file(),str(f2path))
        gate("A2E_epoch_present",a2path.is_file(),str(a2path))
        gate("A2E_status_exact",load_json(a2sum).get("status")==A2E_STATUS,load_json(a2sum).get("status"))

        with np.load(f2path,allow_pickle=False) as z:
            parent_cv_mass=np.asarray(z["parent_CV_component_mass_kg"],dtype=np.float64)
            parent_cv_sat=np.asarray(z["parent_CV_saturation"],dtype=np.float64)
            parent_cv_pv=np.asarray(z["parent_CV_pore_volume_m3"],dtype=np.float64)
            parent_cv_coeff=np.asarray(z["parent_CV_pressure_mass_coeff"],dtype=np.float64)

        with np.load(a2path,allow_pickle=False) as z:
            epoch={k:np.asarray(z[k]).copy() for k in z.files}
        parent_grid_mass=np.asarray(epoch["parent_component_mass_kg"],dtype=np.float64)
        parent_pressure=np.asarray(epoch["refreshed_pressure_psi"],dtype=np.float64)
        grid_pv=np.asarray(epoch["pore_volume_m3"],dtype=np.float64)
        parent_xyz=np.asarray(epoch["streamline_xyz_m"],dtype=np.float64)
        parent_tof=np.asarray(epoch["streamline_tof_s"],dtype=np.float64)
        parent_weights=np.asarray(epoch["streamline_weight_m3_s"],dtype=np.float64)
        p_ref=float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))

        gate("authority_shapes_exact",
             parent_cv_mass.shape==(NSL,NCV)
             and parent_cv_sat.shape==(NSL,NCV)
             and future_cv_mass.shape==(NSL,NCV)
             and future_cv_sat.shape==(NSL,NCV)
             and parent_grid_mass.shape==GRID
             and parent_pressure.shape==GRID
             and grid_pv.shape==GRID
             and parent_xyz.shape==(NSL,NN,3)
             and parent_tof.shape==(NSL,NN)
             and parent_weights.shape==(NSL,))

        stage="source_binding"
        r2=load_module(root/R2SRC,"av4_pivot_p2r5_r2")
        e37=load_module(root/E37A,"av4_pivot_p2r5_e37")
        sg7d=load_module(root/SG7D,"av4_pivot_p2r5_sg7d")
        a2e=load_module(root/A2E,"av4_pivot_p2r5_a2e")

        operator=sg7d.build_subsegment_operator(
            parent_xyz,parent_tof/SPD,parent_weights*SPD
        )
        geometry=e37.build_control_volume_geometry(
            r2,operator,parent_pressure,p_ref,NSL,NCV
        )
        gate(
            "parent_CV_pv_matches_F2R3",
            float(np.max(np.abs(np.asarray(geometry["cv_pv_m3"])-parent_cv_pv)))<=1.0e-8,
            float(np.max(np.abs(np.asarray(geometry["cv_pv_m3"])-parent_cv_pv))),
        )
        gate(
            "parent_CV_coeff_matches_F2R3",
            relative_l2(np.asarray(geometry["cv_pressure_mass_coeff"]),parent_cv_coeff)<=1.0e-12,
            relative_l2(np.asarray(geometry["cv_pressure_mass_coeff"]),parent_cv_coeff),
        )

        stage="reconstruct_R4_pair_state"
        cv_id=np.asarray(geometry["cv_id"],dtype=np.int64)
        flat=np.asarray(geometry["flat_cell"],dtype=np.int64)
        pv=np.asarray(geometry["pv_m3"],dtype=np.float64)
        pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64)

        old_flat=parent_cv_sat.reshape(-1)
        new_flat=future_cv_sat.reshape(-1)
        old_sub=old_flat[cv_id]
        new_sub=new_flat[cv_id]
        old_sg=np.clip(old_sub-BACKGROUND,0.0,MAX_SG)
        new_sg=np.clip(new_sub-BACKGROUND,0.0,MAX_SG)
        rho_old=np.asarray(r2.gas_density_from_state(old_sub,pseg,p_ref),dtype=np.float64)
        rho_new=np.asarray(r2.gas_density_from_state(new_sub,pseg,p_ref),dtype=np.float64)
        sub_delta=pv*(rho_new*new_sg-rho_old*old_sg)

        cv_delta=(future_cv_mass-parent_cv_mass).reshape(-1)
        transfer=np.bincount(cv_id,weights=sub_delta,minlength=NSL*NCV)
        transfer_err=transfer-cv_delta
        sci_gate(
            "per_CV_subsegment_transfer_closure",
            float(np.max(np.abs(transfer_err)))<=CV_EQUALITY_TOL_KG,
            float(np.max(np.abs(transfer_err))),
        )

        key=cv_id.astype(np.int64)*NCELL+flat.astype(np.int64)
        order=np.argsort(key,kind="mergesort")
        key_s=key[order]
        val_s=sub_delta[order]
        starts=np.r_[0,1+np.flatnonzero(key_s[1:]!=key_s[:-1])]
        pair_key=key_s[starts]
        pair_val=np.add.reduceat(val_s,starts)
        pair_cv=(pair_key//NCELL).astype(np.int64)
        pair_cell=(pair_key%NCELL).astype(np.int64)

        original_cell_delta=np.bincount(pair_cell,weights=pair_val,minlength=NCELL)
        original_future=parent_grid_mass.reshape(-1)+original_cell_delta
        neg_mask=original_future < -CELL_BOUND_TOL_KG
        neg_cells=np.flatnonzero(neg_mask)

        # Culprit CVs are all CVs with negative contribution into a failed cell.
        failed_pair=(neg_mask[pair_cell]) & (pair_val < -SIGN_TOL_KG)
        culprit_cvs=np.unique(pair_cv[failed_pair]).astype(np.int64)

        sci_gate("R5_reconstructs_R4_negative_cell_count",
                 int(len(neg_cells))==int(r4s["negative_grid_cell_count"]),
                 {"R5":len(neg_cells),"R4":r4s["negative_grid_cell_count"]})
        sci_gate("R5_reconstructs_R4_culprit_CV_count",
                 int(len(culprit_cvs))==int(r4s["culprit_CV_count"]),
                 {"R5":len(culprit_cvs),"R4":r4s["culprit_CV_count"]})

        culprit_mask=np.zeros(NSL*NCV,dtype=bool)
        culprit_mask[culprit_cvs]=True

        # Existing support graph includes every aggregated pair; zero-valued pairs remain fixed at zero.
        support_pair_mask=culprit_mask[pair_cv]
        support_cv=pair_cv[support_pair_mask]
        support_cell=pair_cell[support_pair_mask]
        support_val=pair_val[support_pair_mask]

        variable_local=np.abs(support_val)>SIGN_TOL_KG
        var_cv=support_cv[variable_local]
        var_cell=support_cell[variable_local]
        x0=support_val[variable_local]
        sci_gate("nonzero_projection_variable_set_nonempty",len(x0)>0,len(x0))

        # Build R4-equivalent connected support components (including zero-valued support edges).
        support_cells=np.unique(support_cell)
        cv_local={int(cv):n for n,cv in enumerate(culprit_cvs.tolist())}
        cell_local={int(c):n for n,c in enumerate(support_cells.tolist())}
        dsu=DSU(len(culprit_cvs)+len(support_cells))
        offset=len(culprit_cvs)
        for cv,cell in zip(support_cv.tolist(),support_cell.tolist()):
            dsu.union(cv_local[int(cv)],offset+cell_local[int(cell)])

        roots=sorted({dsu.find(cv_local[int(cv)]) for cv in culprit_cvs.tolist()})
        sci_gate("R5_reconstructs_R4_component_count",
                 len(roots)==int(r4s["connected_support_component_count"]),
                 {"R5":len(roots),"R4":r4s["connected_support_component_count"]})

        # Physical upper mass capacity under frozen Day365 pressure.
        sat_max=np.full(GRID,BACKGROUND+MAX_SG,dtype=np.float64)
        rho_max=np.asarray(r2.gas_density_from_state(sat_max,parent_pressure,p_ref),dtype=np.float64)
        cell_capacity=(grid_pv*rho_max*MAX_SG).reshape(-1)

        # Fixed contribution contains all non-variable pairs, including nonculprit CVs and zero culprit pairs.
        all_variable_pair_mask=culprit_mask[pair_cv] & (np.abs(pair_val)>SIGN_TOL_KG)
        fixed_delta=np.bincount(
            pair_cell[~all_variable_pair_mask],
            weights=pair_val[~all_variable_pair_mask],
            minlength=NCELL,
        )
        fixed_mass=parent_grid_mass.reshape(-1)+fixed_delta

        variable_cells=np.unique(var_cell)
        outside=np.ones(NCELL,dtype=bool)
        outside[variable_cells]=False
        immutable_lower=np.flatnonzero(outside & (fixed_mass < -CELL_BOUND_TOL_KG))
        immutable_upper=np.flatnonzero(outside & (fixed_mass > cell_capacity + CELL_BOUND_TOL_KG))

        scientific_started=True
        if len(immutable_lower) or len(immutable_upper):
            raise ScientificFail(
                "immutable_outside_projection_support_cell_bound_violation",
                {
                    "outside_lower_violation_count":int(len(immutable_lower)),
                    "outside_upper_violation_count":int(len(immutable_upper)),
                    "outside_minimum_mass_kg":float(np.min(fixed_mass[immutable_lower])) if len(immutable_lower) else None,
                    "outside_maximum_capacity_excess_kg":float(np.max(fixed_mass[immutable_upper]-cell_capacity[immutable_upper])) if len(immutable_upper) else 0.0,
                    "interpretation":"R4 contract requires global cell bounds but authorized variables cannot change these outside-support cells.",
                },
            )

        stage="HiGHS_component_projection"
        try:
            from scipy.optimize import linprog
            from scipy import sparse
            import scipy
        except Exception as exc:
            raise GateError("scipy_HiGHS_unavailable:"+repr(exc)) from exc

        print("SciPy version:",scipy.__version__)
        print("Projection components:",len(roots))
        print("Projection variables :",len(x0))

        # Map global pair key -> variable index for deterministic replacement.
        var_pair_key=var_cv.astype(np.int64)*NCELL+var_cell.astype(np.int64)
        var_index_by_key={int(k):i for i,k in enumerate(var_pair_key.tolist())}
        repaired_x=x0.copy()
        component_rows=[]
        total_l1=0.0
        total_solver_s=0.0

        for component_id,root_id in enumerate(roots):
            comp_cvs=np.asarray(
                [cv for cv in culprit_cvs.tolist() if dsu.find(cv_local[int(cv)])==root_id],
                dtype=np.int64,
            )
            comp_cells=np.asarray(
                [cell for cell in support_cells.tolist() if dsu.find(offset+cell_local[int(cell)])==root_id],
                dtype=np.int64,
            )
            cv_set=set(comp_cvs.tolist())
            cell_set=set(comp_cells.tolist())

            comp_global_var_idx=np.asarray(
                [i for i,(cv,cell) in enumerate(zip(var_cv.tolist(),var_cell.tolist()))
                 if int(cv) in cv_set and int(cell) in cell_set],
                dtype=np.int64,
            )
            if comp_global_var_idx.size == 0:
                raise ScientificFail(
                    "component_has_no_nonzero_projection_variables",
                    {"component_id":component_id,"CV_count":len(comp_cvs),"cell_count":len(comp_cells)},
                )

            c_cv=var_cv[comp_global_var_idx]
            c_cell=var_cell[comp_global_var_idx]
            c_x0=x0[comp_global_var_idx]
            n=len(c_x0)

            # Variables z=[x_0..x_{n-1}, y_0..y_{n-1}], y=|x-x0|.
            c=np.r_[np.zeros(n,dtype=np.float64),np.ones(n,dtype=np.float64)]

            cv_row={int(cv):r for r,cv in enumerate(comp_cvs.tolist())}
            eq_rows=np.asarray([cv_row[int(cv)] for cv in c_cv],dtype=np.int64)
            eq_cols=np.arange(n,dtype=np.int64)
            Aeq_x=sparse.coo_matrix(
                (np.ones(n,dtype=np.float64),(eq_rows,eq_cols)),
                shape=(len(comp_cvs),2*n),
            ).tocsr()
            beq=cv_delta[comp_cvs]

            cell_row={int(cell):r for r,cell in enumerate(comp_cells.tolist())}
            cell_rows=np.asarray([cell_row[int(cell)] for cell in c_cell],dtype=np.int64)
            cell_cols=np.arange(n,dtype=np.int64)
            A_cell=sparse.coo_matrix(
                (np.ones(n,dtype=np.float64),(cell_rows,cell_cols)),
                shape=(len(comp_cells),2*n),
            ).tocsr()

            lower_rhs=fixed_mass[comp_cells]
            upper_rhs=cell_capacity[comp_cells]-fixed_mass[comp_cells]

            # Cell upper: A*x <= cap-fixed.
            # Cell lower: -A*x <= fixed.
            A_upper=A_cell
            b_upper=upper_rhs
            A_lower=-A_cell
            b_lower=lower_rhs

            # L1: x-y <= x0 ; -x-y <= -x0.
            eye=sparse.eye(n,format="csr")
            zero=sparse.csr_matrix((n,n))
            A_l1_pos=sparse.hstack([eye,-eye],format="csr")
            A_l1_neg=sparse.hstack([-eye,-eye],format="csr")
            b_l1_pos=c_x0
            b_l1_neg=-c_x0

            Aub=sparse.vstack([A_upper,A_lower,A_l1_pos,A_l1_neg],format="csr")
            bub=np.r_[b_upper,b_lower,b_l1_pos,b_l1_neg]

            bounds=[]
            for v in c_x0:
                if v > SIGN_TOL_KG:
                    bounds.append((0.0,None))
                elif v < -SIGN_TOL_KG:
                    bounds.append((None,0.0))
                else:
                    bounds.append((0.0,0.0))
            bounds.extend([(0.0,None)]*n)

            t0=time.time()
            res=linprog(
                c,
                A_ub=Aub,
                b_ub=bub,
                A_eq=Aeq_x,
                b_eq=beq,
                bounds=bounds,
                method="highs",
                options={"presolve":True},
            )
            elapsed=float(time.time()-t0)
            total_solver_s+=elapsed

            if not res.success:
                raise ScientificFail(
                    "HiGHS_original_support_projection_infeasible_or_failed",
                    {
                        "component_id":component_id,
                        "status":int(res.status),
                        "message":str(res.message),
                        "culprit_CV_count":int(len(comp_cvs)),
                        "support_cell_count":int(len(comp_cells)),
                        "projection_variable_count":int(n),
                    },
                )

            x=np.asarray(res.x[:n],dtype=np.float64)
            y=np.asarray(res.x[n:],dtype=np.float64)
            repaired_x[comp_global_var_idx]=x
            l1=float(np.sum(np.abs(x-c_x0)))
            total_l1+=l1

            cv_res=np.asarray(Aeq_x[:,:n]@x-beq).ravel()
            cell_mass=fixed_mass[comp_cells]+np.asarray(A_cell[:,:n]@x).ravel()
            lower_violation=float(max(0.0,-float(np.min(cell_mass))))
            upper_violation=float(max(0.0,float(np.max(cell_mass-cell_capacity[comp_cells]))))
            sign_violation=0.0
            for old,new in zip(c_x0,x):
                if old>0:
                    sign_violation=max(sign_violation,max(0.0,-float(new)))
                elif old<0:
                    sign_violation=max(sign_violation,max(0.0,float(new)))

            sci_gate(
                f"component_{component_id:03d}_CV_equality",
                float(np.max(np.abs(cv_res)))<=CV_EQUALITY_TOL_KG,
                float(np.max(np.abs(cv_res))),
            )
            sci_gate(
                f"component_{component_id:03d}_cell_lower_bound",
                lower_violation<=CELL_BOUND_TOL_KG,
                lower_violation,
            )
            sci_gate(
                f"component_{component_id:03d}_cell_upper_bound",
                upper_violation<=CELL_BOUND_TOL_KG,
                upper_violation,
            )
            sci_gate(
                f"component_{component_id:03d}_sign_preservation",
                sign_violation<=SIGN_TOL_KG,
                sign_violation,
            )

            component_rows.append({
                "component_id":component_id,
                "culprit_CV_count":int(len(comp_cvs)),
                "support_cell_count":int(len(comp_cells)),
                "projection_variable_count":int(n),
                "HiGHS_status":int(res.status),
                "HiGHS_message":str(res.message),
                "objective_L1_kg":l1,
                "maximum_CV_equality_residual_kg":float(np.max(np.abs(cv_res))),
                "maximum_lower_bound_violation_kg":lower_violation,
                "maximum_upper_bound_violation_kg":upper_violation,
                "maximum_sign_violation_kg":sign_violation,
                "solver_runtime_s":elapsed,
            })

        stage="global_repaired_state_certification"
        repaired_pair_val=pair_val.copy()
        # Write repaired variables back by exact key lookup.
        for k,new in zip(var_pair_key.tolist(),repaired_x.tolist()):
            loc=int(np.searchsorted(pair_key,int(k)))
            if loc>=len(pair_key) or int(pair_key[loc])!=int(k):
                raise GateError(f"variable_pair_key_not_found:{k}")
            repaired_pair_val[loc]=float(new)

        repaired_cell_delta=np.bincount(pair_cell,weights=repaired_pair_val,minlength=NCELL)
        repaired_grid_mass=parent_grid_mass.reshape(-1)+repaired_cell_delta

        repaired_transfer=np.bincount(pair_cv,weights=repaired_pair_val,minlength=NSL*NCV)
        repaired_cv_res=repaired_transfer-cv_delta

        min_mass=float(np.min(repaired_grid_mass))
        max_capacity_excess=float(np.max(repaired_grid_mass-cell_capacity))
        global_target=float(np.sum(parent_grid_mass)+np.sum(cv_delta))
        global_residual=float(np.sum(repaired_grid_mass)-global_target)

        sci_gate(
            "global_per_CV_conservation",
            float(np.max(np.abs(repaired_cv_res)))<=CV_EQUALITY_TOL_KG,
            float(np.max(np.abs(repaired_cv_res))),
        )
        sci_gate(
            "global_nonnegative_cell_mass",
            min_mass>=-CELL_BOUND_TOL_KG,
            min_mass,
        )
        sci_gate(
            "global_frozen_pressure_cell_capacity",
            max_capacity_excess<=CELL_BOUND_TOL_KG,
            max_capacity_excess,
        )
        sci_gate(
            "global_mass_ledger",
            abs(global_residual)<=GLOBAL_LEDGER_TOL_KG,
            global_residual,
        )

        # Sign and support exactness.
        changed=np.abs(repaired_pair_val-pair_val)>1.0e-10
        changed_nonculprit=np.any(changed & (~culprit_mask[pair_cv]))
        new_sign_violation=np.any(
            ((pair_val> SIGN_TOL_KG)&(repaired_pair_val< -SIGN_TOL_KG))
            |((pair_val< -SIGN_TOL_KG)&(repaired_pair_val> SIGN_TOL_KG))
        )
        zero_changed=np.any((np.abs(pair_val)<=SIGN_TOL_KG)&(np.abs(repaired_pair_val)>SIGN_TOL_KG))
        sci_gate("nonculprit_pairs_unchanged",not changed_nonculprit,bool(changed_nonculprit))
        sci_gate("pair_sign_preserved_globally",not new_sign_violation,bool(new_sign_violation))
        sci_gate("zero_original_pairs_remain_zero",not zero_changed,bool(zero_changed))

        # Invert repaired Cartesian mass under the same frozen Day365 pressure.
        try:
            repaired_sg=a2e.invert_local_mass(
                r2,
                repaired_grid_mass.reshape(GRID),
                parent_pressure,
                p_ref,
                grid_pv,
            )
        except Exception as exc:
            raise ScientificFail("repaired_grid_mass_inversion_failure",repr(exc)) from exc

        repaired_sat=BACKGROUND+np.asarray(repaired_sg,dtype=np.float64)
        sci_gate(
            "repaired_grid_saturation_bounds",
            float(np.min(repaired_sat))>=BACKGROUND-1.0e-10
            and float(np.max(repaired_sat))<=BACKGROUND+MAX_SG+1.0e-10,
            [float(np.min(repaired_sat)),float(np.max(repaired_sat))],
        )

        stage="artifact_publication"
        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R5_Final_Artifacts"
        if local.exists():
            shutil.rmtree(local)
        local.mkdir(parents=True)
        plots=local/"plots"; plots.mkdir()

        # Pair change diagnostics.
        pair_rows=[]
        changed_idx=np.flatnonzero(changed)
        for idx in changed_idx:
            cv=int(pair_cv[idx]); cell=int(pair_cell[idx])
            k=cell//(NY*NX); rem=cell%(NY*NX); j=rem//NX; i=rem%NX
            pair_rows.append({
                "cv_id":cv,
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
                "flat_cell":cell,"k":k,"j":j,"i":i,
                "original_contribution_kg":float(pair_val[idx]),
                "repaired_contribution_kg":float(repaired_pair_val[idx]),
                "delta_from_original_kg":float(repaired_pair_val[idx]-pair_val[idx]),
            })

        fig=plt.figure(figsize=(7,5))
        ax=fig.add_subplot(111)
        ax.scatter(original_future[variable_cells],repaired_grid_mass[variable_cells],s=14,alpha=0.6)
        lo=min(float(np.min(original_future[variable_cells])),float(np.min(repaired_grid_mass[variable_cells])))
        hi=max(float(np.max(original_future[variable_cells])),float(np.max(repaired_grid_mass[variable_cells])))
        ax.plot([lo,hi],[lo,hi],linestyle="--")
        ax.axhline(0.0,linewidth=0.8)
        ax.set_xlabel("Original Day370 future cell mass (kg)")
        ax.set_ylabel("Repaired Day370 future cell mass (kg)")
        ax.set_title("P2-R5 original-support projection")
        ax.grid(True,alpha=0.25)
        fig.savefig(plots/"Day370_original_vs_repaired_cell_mass.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        fig=plt.figure(figsize=(7,5))
        ax=fig.add_subplot(111)
        ax.bar(
            [r["component_id"] for r in component_rows],
            [r["objective_L1_kg"] for r in component_rows],
        )
        ax.set_xlabel("Support component")
        ax.set_ylabel("L1 contribution adjustment (kg)")
        ax.set_title("P2-R5 projection adjustment by component")
        ax.grid(True,axis="y",alpha=0.25)
        fig.savefig(plots/"Day370_component_L1_adjustment.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        with (local/"POSTV16_AV4_PIVOT_P2_R5_Repaired_Day370_State.npz").open("wb") as fp:
            np.savez_compressed(
                fp,
                day=np.asarray(370.0),
                cv_component_mass_kg=future_cv_mass,
                cv_saturation=future_cv_sat,
                grid_component_mass_kg=repaired_grid_mass.reshape(GRID),
                grid_saturation=repaired_sat,
                parent_pressure_psi=parent_pressure,
                original_pair_cv=pair_cv,
                original_pair_cell=pair_cell,
                original_pair_contribution_kg=pair_val,
                repaired_pair_contribution_kg=repaired_pair_val,
                culprit_cv=culprit_cvs,
            )

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "solver":"scipy.optimize.linprog(method='highs')",
            "support_component_count":int(len(roots)),
            "culprit_CV_count":int(len(culprit_cvs)),
            "projection_variable_count":int(len(x0)),
            "changed_pair_count":int(len(changed_idx)),
            "total_L1_adjustment_kg":float(total_l1),
            "total_solver_runtime_s":float(total_solver_s),
            "maximum_per_CV_conservation_residual_kg":float(np.max(np.abs(repaired_cv_res))),
            "minimum_repaired_grid_mass_kg":min_mass,
            "maximum_repaired_capacity_excess_kg":max_capacity_excess,
            "global_mass_residual_kg":global_residual,
            "repaired_grid_saturation_min":float(np.min(repaired_sat)),
            "repaired_grid_saturation_max":float(np.max(repaired_sat)),
            "original_negative_cell_count":int(len(neg_cells)),
            "repaired_negative_cell_count":int(np.sum(repaired_grid_mass < -CELL_BOUND_TOL_KG)),
            "original_upper_capacity_violation_count":int(np.sum(original_future > cell_capacity + CELL_BOUND_TOL_KG)),
            "repaired_upper_capacity_violation_count":int(np.sum(repaired_grid_mass > cell_capacity + CELL_BOUND_TOL_KG)),
            "support_expanded":False,
            "clipping_executed":False,
            "global_renormalization_executed":False,
            "pressure_refresh_executed":False,
            "P3_authorized":False,
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "P2_R6_authorized":True,
            "P2_R6_name":"Dense Day370-to-Day500 Frozen-Flow Snapshot Continuation with Frozen R5 Original-Support Projection Semantics",
            "P3_authorized":False,
            "periodic_cadence_selected_now":False,
            "R3R6R1_execution_invalidated":False,
            "R6_contract":[
                "Day370 repaired state from R5 is the accepted Cartesian restart state",
                "CV transport state remains the exact F4-R3 teacher state",
                "each subsequent 5-day transport step uses the same frozen Day365 pressure/Darcy/Pollock/TOF epoch",
                "each subsequent mapback uses the exact same sign-preserving original-support projection semantics frozen by R4/R5",
                "no support expansion, clipping, global renormalization, pressure refresh, cadence selection, or ML training",
                "P3 remains unauthorized until all dense snapshots through Day500 are certified",
            ],
        }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R5_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R5_Component_Solver_Audit.csv").write_bytes(csv_bytes(component_rows))
        (local/"POSTV16_AV4_PIVOT_P2_R5_Changed_Pair_Contributions.csv").write_bytes(csv_bytes(pair_rows))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R5_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists():
            raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*190)
        print("POSTV16-AV4-PIVOT-P2-R5: PASS")
        print("Support components                 :",len(roots))
        print("Culprit CVs                        :",len(culprit_cvs))
        print("Projection variables               :",len(x0))
        print("Changed pair contributions         :",len(changed_idx))
        print("Total L1 adjustment kg             :",total_l1)
        print("Minimum repaired grid mass kg      :",min_mass)
        print("Maximum repaired capacity excess kg:",max_capacity_excess)
        print("Global mass residual kg            :",global_residual)
        print("P2-R6 authorized                   : True")
        print("P3 authorized                      : False")
        print("="*190)
        return 0

    except ScientificFail as exc:
        fail_dir.mkdir(parents=True,exist_ok=True)
        p=fail_dir/"POSTV16_AV4_PIVOT_P2_R5_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_FAIL,
                "failed_stage":stage,
                "failed_gate":exc.gate,
                "detail":exc.detail,
                "scientific_execution_started":scientific_started,
                "automatic_rerun_authorized":False,
                "support_expansion_authorized":False,
                "physics_relaxation_authorized":False,
                "P3_authorized":False,
                "R3R6R1_execution_invalidated":False,
            },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(MILESTONE+": SCIENTIFIC FAIL")
        print("Gate:",exc.gate)
        print("Detail:",exc.detail)
        return 3

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R5_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "scientific_execution_started":scientific_started,
                "automatic_rerun_authorized":False,
                "P3_authorized":False,
                "R3R6R1_execution_invalidated":False,
            },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(MILESTONE+": BLOCKED")
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
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))
