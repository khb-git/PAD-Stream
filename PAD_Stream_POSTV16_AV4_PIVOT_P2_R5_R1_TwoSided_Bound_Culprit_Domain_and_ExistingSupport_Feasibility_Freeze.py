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
from pathlib import Path
from typing import Any

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


MILESTONE = "POSTV16-AV4-PIVOT-P2-R5-R1"
STATUS_PASS = (
    "AV4PIVOTP2R5R1_TWOSIDED_BOUND_CULPRIT_DOMAIN_AND_EXISTING_SUPPORT_"
    "FEASIBILITY_DESIGN_FREEZE_PASS_NO_REPAIR_EXECUTION"
)
STATUS_BLOCKED = "AV4PIVOTP2R5R1_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "27c4630e87482df3cfb5e853f025425a7c8bf6e0"
EXPECTED_BRANCH = "postv16-av4-pivot"

GRID = (15,50,50)
NZ,NY,NX = GRID
NCELL = NZ*NY*NX
NSL = 1078
NN = 201
NCV = 200
BACKGROUND = 0.20
MAX_SG = 0.60
SPD = 86400.0

CELL_TOL_KG = 1.0e-7
COMPONENT_TOL_KG = 1.0e-6
PAIR_TOL_KG = 1.0e-10

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R5_FAIL_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_SCIENTIFIC_FAIL"
R5_FAIL_REPORT = "POSTV16_AV4_PIVOT_P2_R5_Scientific_Fail_Report.json"
R5_FAIL_STATUS = (
    "AV4PIVOTP2R5_DAY370_EXACT_ORIGINAL_SUPPORT_PROJECTION_"
    "SCIENTIFIC_FAIL_NO_RELAXATION_OR_AUTOMATIC_RERUN_AUTHORIZED"
)
R5_FAIL_GATE = "immutable_outside_projection_support_cell_bound_violation"

R4_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R4_Day370_Mapback_Cause_Audit_and_Repair_Selection_Freeze"
R4_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R4_Summary.json"
R4_DECISION = "POSTV16_AV4_PIVOT_P2_R4_Decision_Contract.json"
R4_STATUS = (
    "AV4PIVOTP2R4_DAY370_MAPBACK_LOCAL_INVENTORY_DEFICIT_CAUSE_AUDIT_"
    "AND_REPAIR_SELECTION_FREEZE_PASS_NO_REPAIR_EXECUTED"
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

OUT_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_R1_TwoSided_Bound_Culprit_Domain_Freeze"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_R1_BLOCKED"

R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

SOURCE_BLOBS = {
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
}


class GateError(RuntimeError):
    pass


def git_text(root:Path,*args:str)->str:
    return subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
    ).stdout.strip()


def load_json(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m


def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()


def relative_l2(a:np.ndarray,b:np.ndarray)->float:
    x=np.asarray(a,dtype=np.float64)
    y=np.asarray(b,dtype=np.float64)
    return float(np.linalg.norm((x-y).ravel())/max(float(np.linalg.norm(y.ravel())),1.0e-30))


def json_bytes(obj:Any)->bytes:
    return (json.dumps(obj,indent=2,sort_keys=True)+"\n").encode("utf-8")


def csv_bytes(rows:list[dict[str,Any]])->bytes:
    if not rows: return b""
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    buf=io.StringIO(newline="")
    w=csv.DictWriter(buf,fieldnames=fields,lineterminator="\n")
    w.writeheader(); w.writerows(rows)
    return buf.getvalue().encode("utf-8")


class DSU:
    def __init__(self,n:int):
        self.p=np.arange(n,dtype=np.int64)
        self.r=np.zeros(n,dtype=np.int8)
    def find(self,x:int)->int:
        while self.p[x]!=x:
            self.p[x]=self.p[self.p[x]]
            x=int(self.p[x])
        return x
    def union(self,a:int,b:int)->None:
        ra=self.find(a); rb=self.find(b)
        if ra==rb:return
        if self.r[ra]<self.r[rb]: ra,rb=rb,ra
        self.p[rb]=ra
        if self.r[ra]==self.r[rb]: self.r[ra]+=1


def self_test()->None:
    assert R5_FAIL_GATE=="immutable_outside_projection_support_cell_bound_violation"
    assert NCELL==37500
    print("POSTV16 AV4 PIVOT P2-R5-R1 structural self-test: PASS")


def main(project_root:Path,drive_root:Path)->int:
    root=Path(project_root).resolve()
    drive=Path(drive_root).resolve()
    out=drive/OUT_REL
    block_dir=drive/BLOCK_REL
    stage="preflight"

    def gate(name:str,passed:Any,value:Any=None):
        ok=bool(passed)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok: raise GateError(name)

    print("="*190)
    print("POSTV16-AV4-PIVOT-P2-R5-R1 -- TWO-SIDED BOUND-CULPRIT DOMAIN / EXISTING-SUPPORT FEASIBILITY FREEZE")
    print("="*190)
    print("AUDIT/DESIGN FREEZE ONLY. NO LP EXECUTION. NO REPAIR. NO SUPPORT EXPANSION.")
    print("Purpose: distinguish a too-narrow variable CV domain from a true geometric-support or parent-state capacity defect.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_R1_Summary.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R5_R1_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P2-R5-R1 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_P2R5R1_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_failed_R5_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="R5_failure_binding"
        r5=load_json(drive/R5_FAIL_REL/R5_FAIL_REPORT)
        gate("R5_fail_status_exact",r5.get("status")==R5_FAIL_STATUS,r5.get("status"))
        gate("R5_failed_gate_exact",r5.get("failed_gate")==R5_FAIL_GATE,r5.get("failed_gate"))
        gate("R5_scientific_execution_started",r5.get("scientific_execution_started") is True,r5.get("scientific_execution_started"))
        detail=r5.get("detail") or {}
        gate("R5_outside_lower_zero",int(detail.get("outside_lower_violation_count",-1))==0,detail.get("outside_lower_violation_count"))
        gate("R5_outside_upper_positive",int(detail.get("outside_upper_violation_count",0))>0,detail.get("outside_upper_violation_count"))
        gate("R5_support_expansion_not_authorized",r5.get("support_expansion_authorized") is False,r5.get("support_expansion_authorized"))
        gate("R5_P3_unauthorized",r5.get("P3_authorized") is False,r5.get("P3_authorized"))

        stage="R4_binding"
        r4dir=drive/R4_REL
        r4s=load_json(r4dir/R4_SUMMARY)
        r4d=load_json(r4dir/R4_DECISION)
        gate("R4_status_exact",r4s.get("status")==R4_STATUS,r4s.get("status"))
        gate("R4_R5_authorized_historically",r4d.get("P2_R5_authorized") is True,r4d.get("P2_R5_authorized"))
        gate("R4_P3_unauthorized",r4d.get("P3_authorized") is False,r4d.get("P3_authorized"))

        stage="R3_teacher_binding"
        rec=drive/R3_RECOVERY_REL
        state_path=rec/R3_TEACHER_STATE
        meta_path=rec/R3_TEACHER_META
        gate("R3_teacher_state_present",state_path.is_file(),str(state_path))
        meta=load_json(meta_path)
        gate("R3_teacher_runner_blob_exact",meta.get("runner_blob")==R3_RUNNER_BLOB,meta.get("runner_blob"))
        gate("R3_teacher_state_SHA_exact",meta.get("state_sha256")==sha256_file(state_path),meta.get("state_sha256"))
        with np.load(state_path,allow_pickle=False) as z:
            future_cv_mass=np.asarray(z["future_mass"],dtype=np.float64)
            future_cv_sat=np.asarray(z["future_saturation"],dtype=np.float64)

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
        parent_grid_sat=np.asarray(epoch["reconciled_saturation"],dtype=np.float64)
        parent_pressure=np.asarray(epoch["refreshed_pressure_psi"],dtype=np.float64)
        grid_pv=np.asarray(epoch["pore_volume_m3"],dtype=np.float64)
        parent_xyz=np.asarray(epoch["streamline_xyz_m"],dtype=np.float64)
        parent_tof=np.asarray(epoch["streamline_tof_s"],dtype=np.float64)
        parent_weights=np.asarray(epoch["streamline_weight_m3_s"],dtype=np.float64)
        p_ref=float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))

        gate("authority_shapes_exact",
             parent_cv_mass.shape==(NSL,NCV)
             and future_cv_mass.shape==(NSL,NCV)
             and parent_grid_mass.shape==GRID
             and parent_grid_sat.shape==GRID
             and parent_pressure.shape==GRID
             and grid_pv.shape==GRID
             and parent_xyz.shape==(NSL,NN,3)
             and parent_tof.shape==(NSL,NN)
             and parent_weights.shape==(NSL,))

        stage="reconstruct_exact_day370_mapback"
        r2=load_module(root/R2SRC,"av4_pivot_p2r5r1_r2")
        e37=load_module(root/E37A,"av4_pivot_p2r5r1_e37")
        sg7d=load_module(root/SG7D,"av4_pivot_p2r5r1_sg7d")

        operator=sg7d.build_subsegment_operator(parent_xyz,parent_tof/SPD,parent_weights*SPD)
        geometry=e37.build_control_volume_geometry(r2,operator,parent_pressure,p_ref,NSL,NCV)
        gate("parent_CV_pv_matches_F2R3",
             float(np.max(np.abs(np.asarray(geometry["cv_pv_m3"])-parent_cv_pv)))<=1.0e-8,
             float(np.max(np.abs(np.asarray(geometry["cv_pv_m3"])-parent_cv_pv))))
        gate("parent_CV_coeff_matches_F2R3",
             relative_l2(np.asarray(geometry["cv_pressure_mass_coeff"]),parent_cv_coeff)<=1.0e-12,
             relative_l2(np.asarray(geometry["cv_pressure_mass_coeff"]),parent_cv_coeff))

        cv_id=np.asarray(geometry["cv_id"],dtype=np.int64)
        flat=np.asarray(geometry["flat_cell"],dtype=np.int64)
        pv=np.asarray(geometry["pv_m3"],dtype=np.float64)
        pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64)

        old_flat=parent_cv_sat.reshape(-1)
        new_flat=future_cv_sat.reshape(-1)
        old_sub=old_flat[cv_id]; new_sub=new_flat[cv_id]
        old_sg=np.clip(old_sub-BACKGROUND,0.0,MAX_SG)
        new_sg=np.clip(new_sub-BACKGROUND,0.0,MAX_SG)
        rho_old=np.asarray(r2.gas_density_from_state(old_sub,pseg,p_ref),dtype=np.float64)
        rho_new=np.asarray(r2.gas_density_from_state(new_sub,pseg,p_ref),dtype=np.float64)
        sub_delta=pv*(rho_new*new_sg-rho_old*old_sg)

        cv_delta=(future_cv_mass-parent_cv_mass).reshape(-1)
        transfer=np.bincount(cv_id,weights=sub_delta,minlength=NSL*NCV)
        gate("per_CV_transfer_closure",
             float(np.max(np.abs(transfer-cv_delta)))<=1.0e-7,
             float(np.max(np.abs(transfer-cv_delta))))

        key=cv_id.astype(np.int64)*NCELL+flat.astype(np.int64)
        order=np.argsort(key,kind="mergesort")
        key_s=key[order]; val_s=sub_delta[order]
        starts=np.r_[0,1+np.flatnonzero(key_s[1:]!=key_s[:-1])]
        pair_key=key_s[starts]
        pair_val=np.add.reduceat(val_s,starts)
        pair_cv=(pair_key//NCELL).astype(np.int64)
        pair_cell=(pair_key%NCELL).astype(np.int64)

        cell_delta=np.bincount(pair_cell,weights=pair_val,minlength=NCELL)
        future_grid=parent_grid_mass.reshape(-1)+cell_delta

        sat_max=np.full(GRID,BACKGROUND+MAX_SG,dtype=np.float64)
        rho_max=np.asarray(r2.gas_density_from_state(sat_max,parent_pressure,p_ref),dtype=np.float64)
        cell_capacity=(grid_pv*rho_max*MAX_SG).reshape(-1)

        parent_flat=parent_grid_mass.reshape(-1)
        parent_lower=parent_flat < -CELL_TOL_KG
        parent_upper=parent_flat > cell_capacity + CELL_TOL_KG
        future_lower=future_grid < -CELL_TOL_KG
        future_upper=future_grid > cell_capacity + CELL_TOL_KG

        gate("R5_failure_upper_count_reproduced",
             int(np.sum(future_upper))==int(r4s["upper_capacity_violation_count_before_repair"]),
             {"R5R1":int(np.sum(future_upper)),"R4":int(r4s["upper_capacity_violation_count_before_repair"])})
        gate("R5_failure_max_upper_excess_reproduced",
             abs(float(np.max(future_grid-cell_capacity))-float(r4s["maximum_upper_capacity_excess_kg_before_repair"]))<=1.0e-7,
             {"R5R1":float(np.max(future_grid-cell_capacity)),"R4":float(r4s["maximum_upper_capacity_excess_kg_before_repair"])})

        stage="two_sided_culprit_domain_audit"
        lower_cells=np.flatnonzero(future_lower)
        upper_cells=np.flatnonzero(future_upper)

        lower_pair=(future_lower[pair_cell]) & (pair_val < -PAIR_TOL_KG)
        upper_pair=(future_upper[pair_cell]) & (pair_val > PAIR_TOL_KG)
        lower_culprit=np.unique(pair_cv[lower_pair]).astype(np.int64)
        upper_culprit=np.unique(pair_cv[upper_pair]).astype(np.int64)
        union_culprit=np.union1d(lower_culprit,upper_culprit).astype(np.int64)

        upper_without_positive_pair=[]
        for cell in upper_cells.tolist():
            m=(pair_cell==cell)&(pair_val>PAIR_TOL_KG)
            if not np.any(m): upper_without_positive_pair.append(int(cell))
        lower_without_negative_pair=[]
        for cell in lower_cells.tolist():
            m=(pair_cell==cell)&(pair_val<-PAIR_TOL_KG)
            if not np.any(m): lower_without_negative_pair.append(int(cell))

        union_mask=np.zeros(NSL*NCV,dtype=bool)
        union_mask[union_culprit]=True
        support_mask=union_mask[pair_cv]
        support_cv=pair_cv[support_mask]
        support_cell=pair_cell[support_mask]
        support_val=pair_val[support_mask]
        support_cells=np.unique(support_cell)

        # Any violating cell not touched by the two-sided authorized original support?
        support_cell_bool=np.zeros(NCELL,dtype=bool)
        support_cell_bool[support_cells]=True
        uncovered_lower=lower_cells[~support_cell_bool[lower_cells]]
        uncovered_upper=upper_cells[~support_cell_bool[upper_cells]]

        # Parent-state inheritance categories.
        inherited_upper=np.flatnonzero(parent_upper & future_upper)
        newly_created_upper=np.flatnonzero((~parent_upper)&future_upper)
        resolved_parent_upper=np.flatnonzero(parent_upper & (~future_upper))

        stage="component_necessary_feasibility_audit"
        cv_local={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local={int(c):n for n,c in enumerate(support_cells.tolist())}
        dsu=DSU(len(union_culprit)+len(support_cells))
        offset=len(union_culprit)
        for cv,cell in zip(support_cv.tolist(),support_cell.tolist()):
            dsu.union(cv_local[int(cv)],offset+cell_local[int(cell)])

        roots=sorted({dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()})
        comp_rows=[]
        all_component_mass_bounds=True
        all_components_cover_violations=True

        for cid,root_id in enumerate(roots):
            cvs=np.asarray([cv for cv in union_culprit.tolist() if dsu.find(cv_local[int(cv)])==root_id],dtype=np.int64)
            cells=np.asarray([c for c in support_cells.tolist() if dsu.find(offset+cell_local[int(c)])==root_id],dtype=np.int64)

            # Fixed contributions from all CVs outside this union culprit set.
            comp_cv_mask=np.zeros(NSL*NCV,dtype=bool)
            comp_cv_mask[cvs]=True
            comp_pair_mask=comp_cv_mask[pair_cv]
            fixed_pair_mask=~comp_pair_mask
            fixed_delta=np.bincount(pair_cell[fixed_pair_mask],weights=pair_val[fixed_pair_mask],minlength=NCELL)
            fixed_mass=parent_flat+fixed_delta

            # Total variable mass for these CVs is fixed by exact per-CV conservation.
            variable_total=float(np.sum(cv_delta[cvs]))
            fixed_total=float(np.sum(fixed_mass[cells]))
            final_component_total=fixed_total+variable_total
            cap_total=float(np.sum(cell_capacity[cells]))
            lower_ok=final_component_total >= -COMPONENT_TOL_KG
            upper_ok=final_component_total <= cap_total + COMPONENT_TOL_KG
            mass_bounds_ok=lower_ok and upper_ok
            all_component_mass_bounds &= mass_bounds_ok

            comp_lower=np.intersect1d(cells,lower_cells,assume_unique=False)
            comp_upper=np.intersect1d(cells,upper_cells,assume_unique=False)
            covered=(len(comp_lower)+len(comp_upper))>0
            all_components_cover_violations &= covered

            comp_rows.append({
                "component_id":cid,
                "culprit_CV_count":int(len(cvs)),
                "support_cell_count":int(len(cells)),
                "lower_violation_cell_count":int(len(comp_lower)),
                "upper_violation_cell_count":int(len(comp_upper)),
                "fixed_mass_total_kg":fixed_total,
                "exact_variable_CV_delta_total_kg":variable_total,
                "required_final_component_mass_kg":final_component_total,
                "component_capacity_total_kg":cap_total,
                "lower_total_bound_ok":bool(lower_ok),
                "upper_total_bound_ok":bool(upper_ok),
                "necessary_component_mass_bounds_ok":bool(mass_bounds_ok),
            })

        stage="decision_freeze"
        parent_clean=(int(np.sum(parent_lower))==0 and int(np.sum(parent_upper))==0)
        all_violation_cells_covered=(len(uncovered_lower)==0 and len(uncovered_upper)==0)
        no_unattributed=(len(lower_without_negative_pair)==0 and len(upper_without_positive_pair)==0)

        if parent_clean and all_violation_cells_covered and no_unattributed and all_component_mass_bounds:
            selected="TWOSIDED_LOWER_AND_UPPER_CULPRIT_CV_ORIGINAL_SUPPORT_DOMAIN"
            r2_authorized=True
            parent_reconciliation_authorized=False
            geometric_extension_authorized=False
            rationale=(
                "The accepted Day365 Cartesian parent state satisfies the same frozen-pressure mass bounds. "
                "Every Day370 lower/upper violating cell is covered by the union of lower-withdrawal and "
                "upper-deposition culprit CVs on their already-existing SG7D/E37A support, and every connected "
                "component satisfies the necessary aggregate mass-versus-capacity bounds. The R5 failure therefore "
                "demonstrates that the negative-only 84-CV variable domain was too narrow; it does not yet establish "
                "a geometric-support deficiency. An exact two-sided original-support LP is authorized next."
            )
        elif not parent_clean:
            selected="PARENT_DAY365_CARTESIAN_CAPACITY_REPRESENTATION_RECONCILIATION_REQUIRED"
            r2_authorized=False
            parent_reconciliation_authorized=True
            geometric_extension_authorized=False
            rationale=(
                "The accepted Day365 parent state itself violates the frozen-pressure Cartesian mass bounds, so "
                "a Day370 mapback projection is not authorized to absorb an inherited parent-state inconsistency."
            )
        else:
            selected="EXISTING_SUPPORT_NECESSARY_CONDITIONS_INCOMPLETE_GEOMETRIC_DOMAIN_AUDIT_REQUIRED"
            r2_authorized=False
            parent_reconciliation_authorized=False
            geometric_extension_authorized=True
            rationale=(
                "At least one Day370 bound violation is not attributable/covered within the two-sided culprit CV "
                "original support, or a connected support component fails the necessary aggregate mass-capacity test. "
                "No support expansion is executed here; a prospective geometric-domain design branch is required."
            )

        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R5_R1_Final_Artifacts"
        if local.exists(): shutil.rmtree(local)
        local.mkdir(parents=True)
        plots=local/"plots"; plots.mkdir()

        # 3D lower vs upper violation locations.
        fig=plt.figure(figsize=(8,6))
        ax=fig.add_subplot(111,projection="3d")
        if len(lower_cells):
            kk=lower_cells//(NY*NX); rr=lower_cells%(NY*NX); jj=rr//NX; ii=rr%NX
            ax.scatter(ii,jj,kk,s=16,alpha=0.7,label="lower")
        if len(upper_cells):
            kk=upper_cells//(NY*NX); rr=upper_cells%(NY*NX); jj=rr//NX; ii=rr%NX
            ax.scatter(ii,jj,kk,s=10,alpha=0.35,label="upper")
        ax.set_xlim(0,NX-1); ax.set_ylim(0,NY-1); ax.set_zlim(0,NZ-1)
        ax.set_xlabel("i"); ax.set_ylabel("j"); ax.set_zlabel("k")
        ax.view_init(elev=24,azim=-58)
        ax.legend()
        ax.set_title("Day370 lower/upper Cartesian mass-bound violations")
        fig.savefig(plots/"3D_Day370_lower_upper_bound_violations.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        fig=plt.figure(figsize=(7,5))
        ax=fig.add_subplot(111)
        labels=["lower CVs","upper CVs","union CVs"]
        vals=[len(lower_culprit),len(upper_culprit),len(union_culprit)]
        ax.bar(labels,vals)
        ax.set_ylabel("CV count")
        ax.set_title("Two-sided culprit-domain size")
        ax.grid(True,axis="y",alpha=0.25)
        fig.savefig(plots/"Day370_two_sided_culprit_CV_counts.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        fig=plt.figure(figsize=(7,5))
        ax=fig.add_subplot(111)
        x=np.arange(len(comp_rows))
        ax.scatter(x,[r["required_final_component_mass_kg"] for r in comp_rows],s=20,label="required final mass")
        ax.scatter(x,[r["component_capacity_total_kg"] for r in comp_rows],s=20,label="capacity")
        ax.set_xlabel("Two-sided support component")
        ax.set_ylabel("Mass (kg)")
        ax.set_title("Necessary component mass-capacity test")
        ax.legend()
        ax.grid(True,alpha=0.25)
        fig.savefig(plots/"Day370_two_sided_component_mass_vs_capacity.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        cell_rows=[]
        for cell in np.union1d(lower_cells,upper_cells).tolist():
            k=cell//(NY*NX); rem=cell%(NY*NX); j=rem//NX; i=rem%NX
            cell_rows.append({
                "flat_cell":int(cell),"k":int(k),"j":int(j),"i":int(i),
                "parent_mass_kg":float(parent_flat[cell]),
                "day370_future_mass_kg":float(future_grid[cell]),
                "capacity_kg":float(cell_capacity[cell]),
                "lower_violation":bool(future_lower[cell]),
                "upper_violation":bool(future_upper[cell]),
                "parent_upper_violation":bool(parent_upper[cell]),
                "covered_by_two_sided_original_support":bool(support_cell_bool[cell]),
            })

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "R5_failed_gate":R5_FAIL_GATE,
            "R5_outside_upper_violation_count":int(detail["outside_upper_violation_count"]),
            "day365_parent_lower_violation_count":int(np.sum(parent_lower)),
            "day365_parent_upper_violation_count":int(np.sum(parent_upper)),
            "day370_lower_violation_count":int(np.sum(future_lower)),
            "day370_upper_violation_count":int(np.sum(future_upper)),
            "day370_inherited_upper_violation_count":int(len(inherited_upper)),
            "day370_newly_created_upper_violation_count":int(len(newly_created_upper)),
            "day370_resolved_parent_upper_violation_count":int(len(resolved_parent_upper)),
            "lower_culprit_CV_count":int(len(lower_culprit)),
            "upper_culprit_CV_count":int(len(upper_culprit)),
            "two_sided_union_culprit_CV_count":int(len(union_culprit)),
            "two_sided_support_cell_count":int(len(support_cells)),
            "two_sided_support_component_count":int(len(roots)),
            "uncovered_lower_violation_cell_count":int(len(uncovered_lower)),
            "uncovered_upper_violation_cell_count":int(len(uncovered_upper)),
            "lower_violation_cells_without_negative_pair_count":int(len(lower_without_negative_pair)),
            "upper_violation_cells_without_positive_pair_count":int(len(upper_without_positive_pair)),
            "all_components_necessary_mass_bounds_ok":bool(all_component_mass_bounds),
            "selected_next_semantics":selected,
            "repair_executed":False,
            "LP_executed":False,
            "support_expanded":False,
            "P3_authorized":False,
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "selected_next_semantics":selected,
            "selection_rationale":rationale,
            "P2_R5_R2_two_sided_original_support_LP_authorized":bool(r2_authorized),
            "P2_R5_R2_name":"Exact Two-Sided Bound-Culprit Original-Support CV-Conservative Cell-Bounded Projection Execution" if r2_authorized else None,
            "parent_state_capacity_reconciliation_design_authorized":bool(parent_reconciliation_authorized),
            "geometric_support_domain_design_authorized":bool(geometric_extension_authorized),
            "support_expansion_execution_authorized":False,
            "P3_authorized":False,
            "periodic_cadence_selected_now":False,
            "R3R6R1_execution_invalidated":False,
        }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_R1_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R5_R1_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R5_R1_Bound_Violation_Cells.csv").write_bytes(csv_bytes(cell_rows))
        (local/"POSTV16_AV4_PIVOT_P2_R5_R1_TwoSided_Support_Components.csv").write_bytes(csv_bytes(comp_rows))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R5_R1_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists(): raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*190)
        print("POSTV16-AV4-PIVOT-P2-R5-R1: PASS")
        print("Day365 parent upper violations            :",int(np.sum(parent_upper)))
        print("Day370 lower violations                   :",int(np.sum(future_lower)))
        print("Day370 upper violations                   :",int(np.sum(future_upper)))
        print("Lower culprit CVs                         :",len(lower_culprit))
        print("Upper culprit CVs                         :",len(upper_culprit))
        print("Two-sided union culprit CVs               :",len(union_culprit))
        print("Two-sided support components              :",len(roots))
        print("Uncovered lower violation cells           :",len(uncovered_lower))
        print("Uncovered upper violation cells           :",len(uncovered_upper))
        print("All components necessary mass bounds OK   :",all_component_mass_bounds)
        print("Selected next semantics                   :",selected)
        print("Two-sided exact LP authorized             :",r2_authorized)
        print("Parent capacity reconciliation authorized :",parent_reconciliation_authorized)
        print("Geometric support design authorized       :",geometric_extension_authorized)
        print("P3 authorized                             : False")
        print("="*190)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R5_R1_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "automatic_rerun_authorized":False,
                "support_expansion_execution_authorized":False,
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
