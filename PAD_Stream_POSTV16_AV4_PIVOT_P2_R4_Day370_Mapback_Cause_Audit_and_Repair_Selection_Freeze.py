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


MILESTONE = "POSTV16-AV4-PIVOT-P2-R4"
STATUS_PASS = (
    "AV4PIVOTP2R4_DAY370_MAPBACK_LOCAL_INVENTORY_DEFICIT_CAUSE_AUDIT_"
    "AND_REPAIR_SELECTION_FREEZE_PASS_NO_REPAIR_EXECUTED"
)
STATUS_BLOCKED = "AV4PIVOTP2R4_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "6cd574a99f1fd26ec4b8b4f214edcff3465c1388"
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
CELL_TOL_KG = 1.0e-8

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R3_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R3_Day370_Mapback_Failure_Audit"
R3_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R3_Summary.json"
R3_DECISION = "POSTV16_AV4_PIVOT_P2_R3_Decision_Contract.json"
R3_NEGATIVE_CSV = "POSTV16_AV4_PIVOT_P2_R3_Negative_Cell_Diagnostics.csv"
R3_STATUS = (
    "AV4PIVOTP2R3_ORIGINAL_P2_DAY370_MAPBACK_SCIENTIFIC_FAILURE_RECLASSIFIED_"
    "AND_NEGATIVE_GRID_CELL_MASS_FAILURE_QUANTIFIED_NO_REPAIR_EXECUTION"
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

OUT_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R4_Day370_Mapback_Cause_Audit_and_Repair_Selection_Freeze"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R4_BLOCKED"

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


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
    ).stdout.strip()


def load_json(path: Path) -> dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str,str]]:
    with path.open("r",newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


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
        p=self.p
        while p[x] != x:
            p[x]=p[p[x]]
            x=int(p[x])
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
    assert R3_REL.name == "POSTV16_AV4_PIVOT_P2_R3_Day370_Mapback_Failure_Audit"
    assert R3_RECOVERY_REL.name == "POSTV16_AV4_PIVOT_P2_R3_Recovery"
    assert NCELL == 37500
    print("POSTV16 AV4 PIVOT P2-R4 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root=Path(project_root).resolve()
    drive=Path(drive_root).resolve()
    out=drive/OUT_REL
    block_dir=drive/BLOCK_REL
    stage="preflight"

    def gate(name:str, passed:Any, value:Any=None):
        ok=bool(passed)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("="*190)
    print("POSTV16-AV4-PIVOT-P2-R4 -- DAY370 MAPBACK CAUSE AUDIT / REPAIR-SELECTION FREEZE")
    print("="*190)
    print("DESIGN/AUDIT ONLY. NO MAPBACK REPAIR EXECUTION. NO STATE ACCEPTANCE.")
    print("NO CLIPPING. NO RENORMALIZATION. NO SUPPORT EXPANSION. NO PRESSURE REFRESH. NO CADENCE SELECTION.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R4_Summary.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R4_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P2-R4 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_P2R4_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_P2R3_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="R3_binding"
        r3dir=drive/R3_REL
        gate("R3_output_present",r3dir.is_dir(),str(r3dir))
        r3s=load_json(r3dir/R3_SUMMARY)
        r3d=load_json(r3dir/R3_DECISION)
        gate("R3_status_exact",r3s.get("status")==R3_STATUS,r3s.get("status"))
        gate("R3_R4_authorized",r3d.get("P2_R4_authorized") is True,r3d.get("P2_R4_authorized"))
        gate("R3_P3_still_unauthorized",r3d.get("P3_authorized") is False,r3d.get("P3_authorized"))
        gate("R3_negative_cell_count_positive",int(r3s.get("negative_grid_cell_count",0))>0,r3s.get("negative_grid_cell_count"))

        r3_rows=read_csv(r3dir/R3_NEGATIVE_CSV)
        gate("R3_negative_CSV_nonempty",len(r3_rows)>0,len(r3_rows))
        gate("R3_negative_CSV_count_matches_summary",len(r3_rows)==int(r3s["negative_grid_cell_count"]),len(r3_rows))

        stage="R3_teacher_recovery_binding"
        rec=drive/R3_RECOVERY_REL
        state_path=rec/R3_TEACHER_STATE
        meta_path=rec/R3_TEACHER_META
        gate("R3_teacher_state_present",state_path.is_file(),str(state_path))
        gate("R3_teacher_meta_present",meta_path.is_file(),str(meta_path))
        meta=load_json(meta_path)
        gate("R3_teacher_runner_blob_exact",meta.get("runner_blob")==R3_RUNNER_BLOB,meta.get("runner_blob"))
        gate("R3_teacher_state_SHA_exact",meta.get("state_sha256")==sha256_file(state_path),meta.get("state_sha256"))
        with np.load(state_path,allow_pickle=False) as z:
            future_mass=np.asarray(z["future_mass"],dtype=np.float64)
            future_sat=np.asarray(z["future_saturation"],dtype=np.float64)

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
             and future_mass.shape==(NSL,NCV)
             and future_sat.shape==(NSL,NCV)
             and parent_grid_mass.shape==GRID
             and parent_pressure.shape==GRID
             and grid_pv.shape==GRID
             and parent_xyz.shape==(NSL,NN,3)
             and parent_tof.shape==(NSL,NN)
             and parent_weights.shape==(NSL,))

        stage="reconstruct_exact_mapback_contributions"
        r2=load_module(root/R2SRC,"av4_pivot_p2r4_r2")
        e37=load_module(root/E37A,"av4_pivot_p2r4_e37")
        sg7d=load_module(root/SG7D,"av4_pivot_p2r4_sg7d")

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

        cv_id=np.asarray(geometry["cv_id"],dtype=np.int64)
        flat=np.asarray(geometry["flat_cell"],dtype=np.int64)
        pv=np.asarray(geometry["pv_m3"],dtype=np.float64)
        pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64)

        old_flat=parent_cv_sat.reshape(-1)
        new_flat=future_sat.reshape(-1)
        old_sub=old_flat[cv_id]
        new_sub=new_flat[cv_id]
        old_sg=np.clip(old_sub-BACKGROUND,0.0,MAX_SG)
        new_sg=np.clip(new_sub-BACKGROUND,0.0,MAX_SG)
        rho_old=np.asarray(r2.gas_density_from_state(old_sub,pseg,p_ref),dtype=np.float64)
        rho_new=np.asarray(r2.gas_density_from_state(new_sub,pseg,p_ref),dtype=np.float64)
        sub_delta=pv*(rho_new*new_sg-rho_old*old_sg)

        cv_delta=(future_mass-parent_cv_mass).reshape(-1)
        transfer=np.bincount(cv_id,weights=sub_delta,minlength=NSL*NCV)
        transfer_err=transfer-cv_delta
        transfer_tol=max(1.0e-6,1.0e-10*max(float(np.max(np.abs(cv_delta))),1.0))
        gate(
            "per_CV_subsegment_transfer_closure",
            float(np.max(np.abs(transfer_err)))<=transfer_tol,
            {"max_abs_kg":float(np.max(np.abs(transfer_err))),"tol_kg":transfer_tol},
        )

        # Aggregate exact subsegment contributions into existing (CV, Cartesian-cell) support pairs.
        key=cv_id.astype(np.int64)*NCELL+flat.astype(np.int64)
        order=np.argsort(key,kind="mergesort")
        key_s=key[order]
        val_s=sub_delta[order]
        starts=np.r_[0,1+np.flatnonzero(key_s[1:]!=key_s[:-1])]
        pair_key=key_s[starts]
        pair_val=np.add.reduceat(val_s,starts)
        pair_cv=(pair_key//NCELL).astype(np.int64)
        pair_cell=(pair_key%NCELL).astype(np.int64)

        cell_delta=np.bincount(pair_cell,weights=pair_val,minlength=NCELL)
        future_grid=(parent_grid_mass.reshape(-1)+cell_delta)
        roundoff=max(1.0e-6,1.0e-10*max(abs(float(np.sum(future_grid))),1.0))
        neg_mask=future_grid < -roundoff
        neg_cells=np.flatnonzero(neg_mask)
        gate("R4_reproduces_R3_negative_cell_count",len(neg_cells)==int(r3s["negative_grid_cell_count"]),len(neg_cells))
        gate(
            "R4_reproduces_R3_minimum_mass",
            abs(float(np.min(future_grid))-float(r3s["minimum_future_grid_mass_kg"])) <= max(1.0e-8,1.0e-10*abs(float(r3s["minimum_future_grid_mass_kg"]))),
            {"R4":float(np.min(future_grid)),"R3":float(r3s["minimum_future_grid_mass_kg"])},
        )

        stage="negative_cell_ownership_audit"
        pair_is_neg_cell=neg_mask[pair_cell]
        neg_pair_cv=pair_cv[pair_is_neg_cell]
        neg_pair_cell=pair_cell[pair_is_neg_cell]
        neg_pair_val=pair_val[pair_is_neg_cell]

        ownership_rows=[]
        culprit_cvs=set()
        multi_negative_owner_cells=0
        single_negative_owner_cells=0
        overlap_present=False

        # Group pair contributions by failed cell.
        sort_cell=np.argsort(neg_pair_cell,kind="mergesort")
        ccell=neg_pair_cell[sort_cell]
        ccv=neg_pair_cv[sort_cell]
        cval=neg_pair_val[sort_cell]
        cstarts=np.r_[0,1+np.flatnonzero(ccell[1:]!=ccell[:-1])] if len(ccell) else np.array([],dtype=np.int64)

        for pos,s in enumerate(cstarts):
            e=int(cstarts[pos+1]) if pos+1<len(cstarts) else len(ccell)
            cell=int(ccell[s])
            cvs=ccv[s:e]
            vals=cval[s:e]
            neg_cvs=np.unique(cvs[vals<0.0])
            all_cvs=np.unique(cvs)
            streams=np.unique(cvs//NCV)
            neg_streams=np.unique(cvs[vals<0.0]//NCV) if np.any(vals<0.0) else np.asarray([],dtype=np.int64)
            for cv in neg_cvs.tolist():
                culprit_cvs.add(int(cv))
            if len(neg_cvs)>1:
                multi_negative_owner_cells+=1
            elif len(neg_cvs)==1:
                single_negative_owner_cells+=1
            if len(all_cvs)>1:
                overlap_present=True

            k=cell//(NY*NX)
            rem=cell%(NY*NX)
            j=rem//NX
            i=rem%NX
            ownership_rows.append({
                "flat_cell":cell,"k":k,"j":j,"i":i,
                "parent_mass_kg":float(parent_grid_mass.reshape(-1)[cell]),
                "net_mapped_delta_kg":float(cell_delta[cell]),
                "future_mass_kg":float(future_grid[cell]),
                "overdraw_kg":float(-future_grid[cell]),
                "all_contributing_CV_count":int(len(all_cvs)),
                "negative_contributing_CV_count":int(len(neg_cvs)),
                "all_contributing_streamline_count":int(len(streams)),
                "negative_contributing_streamline_count":int(len(neg_streams)),
                "positive_contribution_kg":float(np.sum(vals[vals>0.0])) if np.any(vals>0.0) else 0.0,
                "negative_contribution_kg":float(np.sum(vals[vals<0.0])) if np.any(vals<0.0) else 0.0,
                "largest_single_withdrawal_kg":float(-np.min(vals)) if np.any(vals<0.0) else 0.0,
            })

        ownership_rows.sort(key=lambda r:r["future_mass_kg"])
        culprit_cvs=np.asarray(sorted(culprit_cvs),dtype=np.int64)
        gate("culprit_CV_set_nonempty",culprit_cvs.size>0,int(culprit_cvs.size))

        stage="culprit_CV_support_audit"
        culprit_mask=np.zeros(NSL*NCV,dtype=bool)
        culprit_mask[culprit_cvs]=True
        variable_pair_mask=culprit_mask[pair_cv]
        variable_cells=np.unique(pair_cell[variable_pair_mask])
        variable_pairs_cv=pair_cv[variable_pair_mask]
        variable_pairs_cell=pair_cell[variable_pair_mask]
        variable_pairs_val=pair_val[variable_pair_mask]

        # Per-culprit-CV support diagnostics.
        cv_order=np.argsort(variable_pairs_cv,kind="mergesort")
        vcv=variable_pairs_cv[cv_order]
        vcell=variable_pairs_cell[cv_order]
        vval=variable_pairs_val[cv_order]
        vstarts=np.r_[0,1+np.flatnonzero(vcv[1:]!=vcv[:-1])]
        cv_rows=[]
        for pos,s in enumerate(vstarts):
            e=int(vstarts[pos+1]) if pos+1<len(vstarts) else len(vcv)
            cv=int(vcv[s])
            cells=np.unique(vcell[s:e])
            vals=vval[s:e]
            failed_mask_local=neg_mask[cells]
            support_future=future_grid[cells]
            cv_rows.append({
                "cv_id":cv,
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
                "cv_delta_mass_kg":float(cv_delta[cv]),
                "support_cell_count":int(len(cells)),
                "support_failed_cell_count":int(np.sum(failed_mask_local)),
                "original_negative_pair_count":int(np.sum(vals<0.0)),
                "original_positive_pair_count":int(np.sum(vals>0.0)),
                "support_positive_future_mass_slack_kg":float(np.sum(np.maximum(support_future,0.0))),
                "support_negative_deficit_kg":float(np.sum(np.maximum(-support_future,0.0))),
                "failed_cell_negative_contribution_kg":float(
                    np.sum(vals[np.isin(vcell[s:e],neg_cells) & (vals<0.0)])
                ) if len(vals) else 0.0,
            })

        stage="support_component_capacity_audit"
        # Build connected components over culprit CVs and every cell in their original support.
        cv_local={int(cv):n for n,cv in enumerate(culprit_cvs.tolist())}
        cell_list=np.asarray(variable_cells,dtype=np.int64)
        cell_local={int(c):n for n,c in enumerate(cell_list.tolist())}
        dsu=DSU(len(culprit_cvs)+len(cell_list))
        offset=len(culprit_cvs)
        for cv,cell in zip(variable_pairs_cv.tolist(),variable_pairs_cell.tolist()):
            dsu.union(cv_local[int(cv)],offset+cell_local[int(cell)])

        comp_to_cvs={}
        comp_to_cells={}
        for cv in culprit_cvs.tolist():
            root_id=dsu.find(cv_local[int(cv)])
            comp_to_cvs.setdefault(root_id,[]).append(int(cv))
        for cell in cell_list.tolist():
            root_id=dsu.find(offset+cell_local[int(cell)])
            comp_to_cells.setdefault(root_id,[]).append(int(cell))

        component_rows=[]
        aggregate_capacity_sufficient=True
        for cid,root_id in enumerate(sorted(set(comp_to_cvs)|set(comp_to_cells))):
            cvs=np.asarray(comp_to_cvs.get(root_id,[]),dtype=np.int64)
            cells=np.asarray(comp_to_cells.get(root_id,[]),dtype=np.int64)
            fm=future_grid[cells] if cells.size else np.asarray([],dtype=np.float64)
            deficit=float(np.sum(np.maximum(-fm,0.0))) if cells.size else 0.0
            slack=float(np.sum(np.maximum(fm,0.0))) if cells.size else 0.0
            net=float(np.sum(fm)) if cells.size else 0.0
            sufficient=slack+CELL_TOL_KG>=deficit
            aggregate_capacity_sufficient &= sufficient
            component_rows.append({
                "component_id":cid,
                "culprit_CV_count":int(len(cvs)),
                "support_cell_count":int(len(cells)),
                "failed_cell_count":int(np.sum(neg_mask[cells])) if cells.size else 0,
                "negative_deficit_kg":deficit,
                "positive_future_mass_slack_kg":slack,
                "net_future_mass_kg":net,
                "aggregate_same_support_capacity_sufficient":bool(sufficient),
            })

        stage="upper_capacity_audit"
        # Physical cell mass capacity under the same frozen Day365 pressure.
        sat_max=np.full(GRID,BACKGROUND+MAX_SG,dtype=np.float64)
        rho_max=np.asarray(r2.gas_density_from_state(sat_max,parent_pressure,p_ref),dtype=np.float64)
        cell_capacity=(grid_pv*rho_max*MAX_SG).reshape(-1)
        capacity_excess=future_grid-cell_capacity
        upper_violation_count=int(np.sum(capacity_excess>roundoff))
        upper_max=float(np.max(capacity_excess)) if upper_violation_count else 0.0

        stage="repair_selection_freeze"
        # R4 does not execute a repair. It selects the next exact feasibility problem only.
        if aggregate_capacity_sufficient:
            selected=(
                "SIGN_PRESERVING_ORIGINAL_SUPPORT_PER_CV_CONSERVATIVE_CELL_BOUNDED_PROJECTION"
            )
            r5_authorized=True
            r4a_authorized=False
            rationale=(
                "Every connected culprit-CV/original-support component contains aggregate positive "
                "future-cell inventory at least as large as its negative deficit. This is a necessary "
                "support-capacity condition, not an exact LP feasibility proof. R5 is authorized only "
                "to solve the exact sign-preserving support-constrained projection and execute it if feasible."
            )
        else:
            selected="NO_ORIGINAL_SUPPORT_REPAIR_SELECTED"
            r5_authorized=False
            r4a_authorized=True
            rationale=(
                "At least one connected culprit-CV/original-support component lacks aggregate cell inventory "
                "to absorb its negative deficit. Original-support projection is therefore not authorized; "
                "a separate support-extension or representation repair design is required."
            )

        repair_contract={
            "name":selected,
            "execution_in_R4":False,
            "aggregation_level":"existing (CV_id, Cartesian_cell) support pair",
            "objective_for_R5":"minimize deterministic L1 deviation from original aggregated CV-cell mapback contributions",
            "constraints":[
                "per-CV sum of repaired CV-cell contributions equals original exact CV mass delta",
                "Cartesian future mass must remain >= 0 within numerical tolerance",
                "Cartesian future mass must remain <= frozen-pressure physical mass capacity",
                "no new CV-cell support edges",
                "sign of each nonzero original CV-cell contribution is preserved",
                "zero original contribution remains zero",
                "all contributions from non-culprit CVs remain frozen",
                "global mass ledger remains exact as consequence of per-CV equalities",
            ],
            "forbidden":[
                "cell clipping",
                "post-hoc global renormalization",
                "support expansion",
                "pressure refresh",
                "same-time fixed point",
                "cadence selection",
                "P3 execution",
                "ML training",
            ],
            "R5_may_accept_repaired_state_only_if_exact_feasibility_passes":True,
        }

        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R4_Final_Artifacts"
        if local.exists():
            shutil.rmtree(local)
        local.mkdir(parents=True)
        plots=local/"plots"; plots.mkdir()

        # Ownership multiplicity histogram.
        owners=np.asarray([r["negative_contributing_CV_count"] for r in ownership_rows],dtype=np.int64)
        fig=plt.figure(figsize=(7,4.8))
        ax=fig.add_subplot(111)
        vals,counts=np.unique(owners,return_counts=True)
        ax.bar(vals,counts)
        ax.set_xlabel("Negative-contributing CV count per failed Cartesian cell")
        ax.set_ylabel("Failed cell count")
        ax.set_title("Day370 negative-cell ownership multiplicity")
        ax.grid(True,axis="y",alpha=0.25)
        fig.savefig(plots/"Day370_negative_cell_owner_multiplicity.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        # Overdraw vs multiplicity.
        fig=plt.figure(figsize=(7,4.8))
        ax=fig.add_subplot(111)
        ax.scatter(
            [r["negative_contributing_CV_count"] for r in ownership_rows],
            [r["overdraw_kg"] for r in ownership_rows],
            s=18,alpha=0.65
        )
        ax.set_xlabel("Negative-contributing CV count")
        ax.set_ylabel("Cell overdraw (kg)")
        ax.set_title("Day370 overdraw vs ownership multiplicity")
        ax.grid(True,alpha=0.25)
        fig.savefig(plots/"Day370_overdraw_vs_owner_multiplicity.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        # Component capacity.
        fig=plt.figure(figsize=(7,4.8))
        ax=fig.add_subplot(111)
        x=np.arange(len(component_rows))
        ax.scatter(x,[r["negative_deficit_kg"] for r in component_rows],label="negative deficit",s=28)
        ax.scatter(x,[r["positive_future_mass_slack_kg"] for r in component_rows],label="positive slack",s=28)
        ax.set_xlabel("Connected support component")
        ax.set_ylabel("Mass (kg)")
        ax.set_title("Original-support component deficit vs available cell inventory")
        ax.legend()
        ax.grid(True,alpha=0.25)
        fig.savefig(plots/"Day370_component_deficit_vs_slack.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "negative_grid_cell_count":int(len(neg_cells)),
            "culprit_CV_count":int(len(culprit_cvs)),
            "single_negative_owner_cell_count":int(single_negative_owner_cells),
            "multi_negative_owner_cell_count":int(multi_negative_owner_cells),
            "any_CV_cell_overlap_present":bool(overlap_present),
            "connected_support_component_count":int(len(component_rows)),
            "all_components_aggregate_same_support_capacity_sufficient":bool(aggregate_capacity_sufficient),
            "upper_capacity_violation_count_before_repair":upper_violation_count,
            "maximum_upper_capacity_excess_kg_before_repair":upper_max,
            "selected_repair_semantics":selected,
            "repair_executed":False,
            "P3_authorized":False,
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "selected_repair_semantics":selected,
            "selection_rationale":rationale,
            "P2_R5_authorized":bool(r5_authorized),
            "P2_R5_name":"Day370 Exact Sign-Preserving Original-Support CV-Conservative Cell-Bounded Projection Execution" if r5_authorized else None,
            "P2_R4A_support_extension_design_authorized":bool(r4a_authorized),
            "P3_authorized":False,
            "periodic_cadence_selected_now":False,
            "R3R6R1_execution_invalidated":False,
            "repair_contract":repair_contract,
        }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R4_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R4_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R4_Repair_Selection_Contract.json").write_bytes(json_bytes(repair_contract))
        (local/"POSTV16_AV4_PIVOT_P2_R4_Negative_Cell_Ownership.csv").write_bytes(csv_bytes(ownership_rows))
        (local/"POSTV16_AV4_PIVOT_P2_R4_Culprit_CV_Support.csv").write_bytes(csv_bytes(cv_rows))
        (local/"POSTV16_AV4_PIVOT_P2_R4_Support_Components.csv").write_bytes(csv_bytes(component_rows))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R4_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists():
            raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*190)
        print("POSTV16-AV4-PIVOT-P2-R4: PASS")
        print("Negative grid cells                         :",len(neg_cells))
        print("Culprit CVs                                :",len(culprit_cvs))
        print("Single-negative-owner cells                :",single_negative_owner_cells)
        print("Multi-negative-owner cells                 :",multi_negative_owner_cells)
        print("Connected support components               :",len(component_rows))
        print("All components aggregate capacity sufficient:",aggregate_capacity_sufficient)
        print("Selected repair semantics                  :",selected)
        print("P2-R5 authorized                           :",r5_authorized)
        print("P2-R4A support-extension design authorized :",r4a_authorized)
        print("P3 authorized                              : False")
        print("="*190)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R4_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "automatic_rerun_authorized":False,
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
