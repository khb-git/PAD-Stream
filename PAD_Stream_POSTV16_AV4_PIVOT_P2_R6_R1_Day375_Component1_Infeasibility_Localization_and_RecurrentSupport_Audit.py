#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE="POSTV16-AV4-PIVOT-P2-R6-R1"
STATUS_PASS=(
    "AV4PIVOTP2R6R1_DAY375_COMPONENT1_STAGE1_INFEASIBILITY_LOCALIZATION_"
    "AND_RECURRENT_SUPPORT_SUFFICIENCY_AUDIT_PASS_NO_REPAIR_EXECUTION"
)
STATUS_BLOCKED="AV4PIVOTP2R6R1_TECHNICAL_OR_AUTHORITY_BLOCK"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT="7d8d03d73dd73727699e4d0ee64486d0ef2ebf3e"
EXPECTED_BRANCH="postv16-av4-pivot"

GRID=(15,50,50)
NZ,NY,NX=GRID
NCELL=NZ*NY*NX
NSL=1078
NN=201
NCV=200
BACKGROUND=0.20
MAX_SG=0.60
SPD=86400.0

DAY=375.0
STEP_DAYS=5.0
FAILED_COMPONENT_ID=1
EXPECTED_CV_COUNT=78
EXPECTED_CELL_COUNT=60
EXPECTED_EXISTING_VARIABLE_COUNT=101
EXPECTED_H2_EDGE_COUNT=421

CV_TOL_KG=1.0e-7
CELL_TOL_KG=1.0e-7
SIGN_TOL_KG=1.0e-10
SLACK_TOL_KG=1.0e-8

BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

P2R6_FAIL_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_SCIENTIFIC_FAIL"
P2R6_FAIL_REPORT="POSTV16_AV4_PIVOT_P2_R6_Scientific_Fail_Report.json"
P2R6_FAIL_STATUS=(
    "AV4PIVOTP2R6_FROZEN_FLOW_CONTINUATION_SCIENTIFIC_FAIL_"
    "NO_SUPPORT_GROWTH_NO_PRESSURE_REFRESH_NO_AUTOMATIC_RERUN"
)
P2R6_FAIL_STAGE="transport_and_projection_to_day_375"
P2R6_FAIL_GATE="Day375_component_1_stage1_infeasible"

R4_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
R4_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Summary.json"
R4_DECISION="POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Decision_Contract.json"
R4_STATE="POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz"
R4_STATUS=(
    "AV4PIVOTP2R5G2AR4R1R1R1_COMPLETED_COMPONENT_CELL_MEMBERSHIP_IDENTITY_"
    "REPAIR_AND_COMPONENT_FRONTIER_PROJECTION_EXECUTION_PASS"
)

F2R3_REL=BASE_AV4/"POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution"
F2R3_STATE="POSTV16_AV4_F2_R3_Accepted_Parent_Restart_State.npz"

E1R2_REL=BASE_AV4/"POSTV16_AV4_A3_E1_R2_Refreshed_X13_Structural_InputDomain_Audit"
E1R2_X13="POSTV16_AV4_A3_E1_R2_Refreshed_Day365_13Channel_Representation.npz"

A2E_REL=BASE_AV4/"POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH="POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_SUMMARY="PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_STATUS=(
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

OUT_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R1_Day375_Component1_Infeasibility_Localization_Audit"
BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R1_BLOCKED"

F4R3="PAD_Stream_POSTV16_AV4_F4_R3_Terminal_Producer_PassThrough_Repair_Execution.py"
F4R3_BLOB="2e84ab09f9ae7af6f977eabc3d9465d325fad717"
A4R2="PAD_Stream_POSTV16_AV3_A4_R2_Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
A4R2_BLOB="289901331e835afb44ff2f665fe9a6bbea2eac19"
R2SRC="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
E37A="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D="PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB="890088c0c0fcab415a2c7351c5079ca8ee12bf82"
P2R6RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_Dense_Day370_to_Day500_FrozenFlow_Continuation_with_Frozen_ComponentFrontier_H2_Projection.py"
P2R6RUN_BLOB="c7623e1478745733379fee57776cb34b4e8f71e4"
R4RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection_Execution.py"
R4RUN_BLOB="cdcade36343d314bc34063bce6e81e5c9c520294"

SOURCE_BLOBS={
    F4R3:F4R3_BLOB,
    A4R2:A4R2_BLOB,
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
    P2R6RUN:P2R6RUN_BLOB,
    R4RUN:R4RUN_BLOB,
}


class GateError(RuntimeError):
    pass


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
        ra=self.find(a);rb=self.find(b)
        if ra==rb:return
        if self.r[ra]<self.r[rb]:ra,rb=rb,ra
        self.p[rb]=ra
        if self.r[ra]==self.r[rb]:self.r[ra]+=1


def git_text(root:Path,*args:str)->str:
    return subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE
    ).stdout.strip()


def load_json(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod


def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()


def relative_l2(a:np.ndarray,b:np.ndarray)->float:
    x=np.asarray(a,dtype=np.float64);y=np.asarray(b,dtype=np.float64)
    return float(np.linalg.norm((x-y).ravel())/max(float(np.linalg.norm(y.ravel())),1e-30))


def json_bytes(obj:Any)->bytes:
    return (json.dumps(obj,indent=2,sort_keys=True)+"\n").encode("utf-8")


def csv_bytes(rows:list[dict[str,Any]])->bytes:
    if not rows:return b""
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields:fields.append(k)
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n")
    w.writeheader();w.writerows(rows)
    return s.getvalue().encode("utf-8")


def self_test()->None:
    assert DAY==375.0
    assert FAILED_COMPONENT_ID==1
    assert (EXPECTED_CV_COUNT,EXPECTED_CELL_COUNT,EXPECTED_EXISTING_VARIABLE_COUNT,EXPECTED_H2_EDGE_COUNT)==(78,60,101,421)
    print("POSTV16 AV4 PIVOT P2-R6-R1 structural self-test: PASS")


def main(project_root:Path,drive_root:Path)->int:
    root=Path(project_root).resolve()
    drive=Path(drive_root).resolve()
    out=drive/OUT_REL
    block_dir=drive/BLOCK_REL
    stage="preflight"

    def gate(name:str,passed:Any,value:Any=None):
        ok=bool(passed)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok:raise GateError(name)

    print("="*194)
    print("POSTV16-AV4-PIVOT-P2-R6-R1 -- DAY375 COMPONENT-1 STAGE-1 INFEASIBILITY LOCALIZATION / RECURRENT-SUPPORT AUDIT")
    print("="*194)
    print("AUDIT ONLY. NO REPAIR. NO SUPPORT GROWTH. NO PRESSURE REFRESH. NO P3.")
    print("REPRODUCE THE EXACT 78-CV / 60-CELL / 101-EXISTING / 421-H2 FAILED COMPONENT.")
    print("THEN MINIMIZE DIAGNOSTIC PER-CV CONSERVATION SLACK UNDER THE UNCHANGED FROZEN R4 GRAPH.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R1_Summary.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R6_R1_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P2-R6-R1 audit PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_P2R6R1_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_P2R6_FAIL_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,
             git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",
             repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="P2R6_scientific_fail_binding"
        fail_path=drive/P2R6_FAIL_REL/P2R6_FAIL_REPORT
        p2fail=load_json(fail_path)
        gate("P2R6_fail_status_exact",p2fail.get("status")==P2R6_FAIL_STATUS,p2fail.get("status"))
        gate("P2R6_failed_stage_exact",p2fail.get("failed_stage")==P2R6_FAIL_STAGE,p2fail.get("failed_stage"))
        gate("P2R6_failed_gate_exact",p2fail.get("failed_gate")==P2R6_FAIL_GATE,p2fail.get("failed_gate"))
        detail=p2fail.get("detail",{})
        gate("P2R6_failed_component_signature_exact",
             int(detail.get("CV_count",-1))==EXPECTED_CV_COUNT
             and int(detail.get("cell_count",-1))==EXPECTED_CELL_COUNT
             and int(detail.get("existing_variable_count",-1))==EXPECTED_EXISTING_VARIABLE_COUNT
             and int(detail.get("H2_edge_count",-1))==EXPECTED_H2_EDGE_COUNT,
             detail)
        gate("P2R6_scientific_execution_true",p2fail.get("scientific_execution_started") is True)
        gate("P2R6_auto_rerun_false",p2fail.get("automatic_rerun_authorized") is False)
        gate("P2R6_support_growth_false",p2fail.get("support_growth_authorized") is False)
        gate("P2R6_pressure_refresh_false",p2fail.get("pressure_refresh_authorized") is False)
        gate("P2R6_P3_false",p2fail.get("AV4_PIVOT_P3_authorized") is False)

        stage="R4_PASS_binding"
        r4dir=drive/R4_REL
        r4s=load_json(r4dir/R4_SUMMARY)
        r4d=load_json(r4dir/R4_DECISION)
        r4state_path=r4dir/R4_STATE
        gate("R4_status_exact",r4s.get("status")==R4_STATUS,r4s.get("status"))
        gate("R4_decision_status_exact",r4d.get("status")==R4_STATUS,r4d.get("status"))
        gate("R4_state_present",r4state_path.is_file(),str(r4state_path))
        gate("R4_state_SHA_exact",sha256_file(r4state_path)==r4s.get("accepted_state_sha256"),
             sha256_file(r4state_path))

        with np.load(r4state_path,allow_pickle=False) as z:
            r4state={k:np.asarray(z[k]).copy() for k in z.files}
        old_cv_mass=np.asarray(r4state["cv_component_mass_kg"],dtype=np.float64)
        old_cv_sat=np.asarray(r4state["cv_saturation"],dtype=np.float64)
        old_grid_mass=np.asarray(r4state["grid_component_mass_kg"],dtype=np.float64)
        frozen_pair_cv=np.asarray(r4state["existing_pair_cv"],dtype=np.int64)
        frozen_pair_cell=np.asarray(r4state["existing_pair_cell"],dtype=np.int64)
        frozen_halo_cv=np.asarray(r4state["halo_cv"],dtype=np.int64)
        frozen_halo_cell=np.asarray(r4state["halo_cell"],dtype=np.int64)
        frozen_halo_is_completion=np.asarray(r4state["halo_is_completion"],dtype=bool)
        r4_target_cvs=np.asarray(r4state["completion_target_cv"],dtype=np.int64)

        stage="Day375_teacher_reproduction"
        f2path=drive/F2R3_REL/F2R3_STATE
        x13path=drive/E1R2_REL/E1R2_X13
        a2path=drive/A2E_REL/A2E_EPOCH
        a2sum=drive/A2E_REL/A2E_SUMMARY
        for label,p in [("F2R3",f2path),("X13",x13path),("A2E_epoch",a2path),("A2E_summary",a2sum)]:
            gate(label+"_present",p.is_file(),str(p))
        gate("A2E_status_exact",load_json(a2sum).get("status")==A2E_STATUS,load_json(a2sum).get("status"))

        with np.load(f2path,allow_pickle=False) as z:
            parent_cv_capacity=np.asarray(z["parent_CV_capacity_kg"],dtype=np.float64)
            parent_cv_pv=np.asarray(z["parent_CV_pore_volume_m3"],dtype=np.float64)
            parent_cv_coeff=np.asarray(z["parent_CV_pressure_mass_coeff"],dtype=np.float64)
        with np.load(x13path,allow_pickle=False) as z:
            X13=np.asarray(z["X_refreshed_13"],dtype=np.float64)
        with np.load(a2path,allow_pickle=False) as z:
            epoch={k:np.asarray(z[k]).copy() for k in z.files}

        parent_pressure=np.asarray(epoch["refreshed_pressure_psi"],dtype=np.float64)
        grid_pv=np.asarray(epoch["pore_volume_m3"],dtype=np.float64)
        p_ref=float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))
        parent_xyz=np.asarray(epoch["streamline_xyz_m"],dtype=np.float64)
        parent_tof=np.asarray(epoch["streamline_tof_s"],dtype=np.float64)
        parent_weights=np.asarray(epoch["streamline_weight_m3_s"],dtype=np.float64)
        parent_face_pressure=np.asarray(epoch["streamline_face_pressure_psi"],dtype=np.float64)
        xi=np.asarray(epoch["xi"],dtype=np.float64).reshape(-1)

        f4=load_module(root/F4R3,"p2r6r1_f4")
        a4=load_module(root/A4R2,"p2r6r1_a4")
        r2=load_module(root/R2SRC,"p2r6r1_r2")
        e37=load_module(root/E37A,"p2r6r1_e37")
        sg7d=load_module(root/SG7D,"p2r6r1_sg7d")

        cvavg=0.5*(X13[:,:-1,:]+X13[:,1:,:])
        phi_cv=cvavg[:,:,5]
        nw_cv=3.0+cvavg[:,:,9]
        no_cv=3.0+cvavg[:,:,10]
        krw_cv=0.80+0.20*cvavg[:,:,11]
        kro_cv=0.80+0.20*cvavg[:,:,12]
        cvgeom=f4.build_cv_geometry_from_faces(parent_tof,xi)

        teacher=f4.execute_teacher_with_coeff(
            a4=a4,r2=r2,e37=e37,
            old_mass=old_cv_mass,old_sat=old_cv_sat,
            capacity=parent_cv_capacity,
            cv_pressure_mass_coeff=parent_cv_coeff,
            cv_pv_m3=parent_cv_pv,
            face_pressure_psi=parent_face_pressure,
            p_ref_pa=p_ref,
            q_m3_day=parent_weights*SPD,
            nw=nw_cv,no=no_cv,krw_max=krw_cv,kro_max=kro_cv,
            phi_cv=phi_cv,cvgeom=cvgeom,delta_days=STEP_DAYS,
        )
        new_cv_mass=np.asarray(teacher["future_mass"],dtype=np.float64)
        new_cv_sat=np.asarray(teacher["future_saturation"],dtype=np.float64)

        operator=sg7d.build_subsegment_operator(parent_xyz,parent_tof/SPD,parent_weights*SPD)
        geometry=e37.build_control_volume_geometry(r2,operator,parent_pressure,p_ref,NSL,NCV)
        gate("CV_pv_matches",float(np.max(np.abs(np.asarray(geometry["cv_pv_m3"])-parent_cv_pv)))<=1.0e-8)
        gate("CV_coeff_matches",relative_l2(np.asarray(geometry["cv_pressure_mass_coeff"]),parent_cv_coeff)<=1.0e-12)

        cv_id=np.asarray(geometry["cv_id"],dtype=np.int64)
        flat=np.asarray(geometry["flat_cell"],dtype=np.int64)
        pv=np.asarray(geometry["pv_m3"],dtype=np.float64)
        pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64)

        old_flat=old_cv_sat.reshape(-1);new_flat=new_cv_sat.reshape(-1)
        old_sub=old_flat[cv_id];new_sub=new_flat[cv_id]
        old_sg=np.clip(old_sub-BACKGROUND,0.0,MAX_SG)
        new_sg=np.clip(new_sub-BACKGROUND,0.0,MAX_SG)
        rho_old=np.asarray(r2.gas_density_from_state(old_sub,pseg,p_ref),dtype=np.float64)
        rho_new=np.asarray(r2.gas_density_from_state(new_sub,pseg,p_ref),dtype=np.float64)
        sub_delta=pv*(rho_new*new_sg-rho_old*old_sg)

        cv_delta=(new_cv_mass-old_cv_mass).reshape(-1)
        transfer=np.bincount(cv_id,weights=sub_delta,minlength=NSL*NCV)
        gate("Day375_subsegment_per_CV_closure",
             float(np.max(np.abs(transfer-cv_delta)))<=CV_TOL_KG,
             float(np.max(np.abs(transfer-cv_delta))))

        key=cv_id.astype(np.int64)*NCELL+flat.astype(np.int64)
        order=np.argsort(key,kind="mergesort")
        key_s=key[order];val_s=sub_delta[order]
        starts=np.r_[0,1+np.flatnonzero(key_s[1:]!=key_s[:-1])]
        pair_key=key_s[starts]
        pair_val=np.add.reduceat(val_s,starts)
        pair_cv=(pair_key//NCELL).astype(np.int64)
        pair_cell=(pair_key%NCELL).astype(np.int64)
        gate("pair_CV_support_matches_R4",np.array_equal(pair_cv,frozen_pair_cv))
        gate("pair_cell_support_matches_R4",np.array_equal(pair_cell,frozen_pair_cell))

        sat_max=np.full(GRID,BACKGROUND+MAX_SG,dtype=np.float64)
        rho_max=np.asarray(r2.gas_density_from_state(sat_max,parent_pressure,p_ref),dtype=np.float64)
        capacity=(grid_pv*rho_max*MAX_SG).reshape(-1)

        direct_delta=np.bincount(pair_cell,weights=pair_val,minlength=NCELL)
        direct_future=old_grid_mass.reshape(-1)+direct_delta
        lower=direct_future<-CELL_TOL_KG
        upper=direct_future>capacity+CELL_TOL_KG

        lower_culprit=np.unique(pair_cv[lower[pair_cell]&(pair_val<-SIGN_TOL_KG)]).astype(np.int64)
        upper_culprit=np.unique(pair_cv[upper[pair_cell]&(pair_val>SIGN_TOL_KG)]).astype(np.int64)
        union_culprit=np.union1d(lower_culprit,upper_culprit).astype(np.int64)
        union_mask=np.zeros(NSL*NCV,dtype=bool);union_mask[union_culprit]=True

        existing_mask=union_mask[pair_cv]
        existing_cv=pair_cv[existing_mask]
        existing_cell=pair_cell[existing_mask]
        existing_val=pair_val[existing_mask]
        ex_nonzero=np.abs(existing_val)>SIGN_TOL_KG
        var_ex_cv=existing_cv[ex_nonzero]
        var_ex_cell=existing_cell[ex_nonzero]
        var_ex_x0=existing_val[ex_nonzero]

        edge_mask=union_mask[frozen_halo_cv]
        halo_cv=frozen_halo_cv[edge_mask]
        halo_cell=frozen_halo_cell[edge_mask]
        halo_is_completion=frozen_halo_is_completion[edge_mask]

        variable_existing_global=union_mask[pair_cv]&(np.abs(pair_val)>SIGN_TOL_KG)
        fixed_delta=np.bincount(
            pair_cell[~variable_existing_global],
            weights=pair_val[~variable_existing_global],
            minlength=NCELL,
        )
        fixed_mass=old_grid_mass.reshape(-1)+fixed_delta

        all_cells=np.union1d(np.unique(existing_cell),np.unique(halo_cell)).astype(np.int64)
        cv_local={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local={int(c):n for n,c in enumerate(all_cells.tolist())}
        dsu=DSU(len(union_culprit)+len(all_cells));off=len(union_culprit)
        for cv,c in zip(existing_cv.tolist(),existing_cell.tolist()):
            dsu.union(cv_local[int(cv)],off+cell_local[int(c)])
        for cv,c in zip(halo_cv.tolist(),halo_cell.tolist()):
            dsu.union(cv_local[int(cv)],off+cell_local[int(c)])

        roots=sorted({dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()})
        gate("failed_component_id_exists",FAILED_COMPONENT_ID<len(roots),len(roots))
        comp_of_cv={int(cv):dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()}
        root_id=roots[FAILED_COMPONENT_ID]
        comp_cvs=np.asarray(
            [cv for cv in union_culprit.tolist() if comp_of_cv[int(cv)]==root_id],
            dtype=np.int64
        )
        ex_root=np.asarray([comp_of_cv[int(cv)] for cv in var_ex_cv],dtype=np.int64)
        h_root=np.asarray([comp_of_cv[int(cv)] for cv in halo_cv],dtype=np.int64)
        ex_idx=np.flatnonzero(ex_root==root_id)
        h_idx=np.flatnonzero(h_root==root_id)

        cex_cv=var_ex_cv[ex_idx]
        cex_cell=var_ex_cell[ex_idx]
        cex_x0=var_ex_x0[ex_idx]
        ch_cv=halo_cv[h_idx]
        ch_cell=halo_cell[h_idx]
        ch_completion=halo_is_completion[h_idx]
        comp_cells=np.unique(np.r_[cex_cell,ch_cell]).astype(np.int64)

        gate("Day375_component1_CV_count_exact",len(comp_cvs)==EXPECTED_CV_COUNT,len(comp_cvs))
        gate("Day375_component1_cell_count_exact",len(comp_cells)==EXPECTED_CELL_COUNT,len(comp_cells))
        gate("Day375_component1_existing_variable_count_exact",len(ex_idx)==EXPECTED_EXISTING_VARIABLE_COUNT,len(ex_idx))
        gate("Day375_component1_H2_edge_count_exact",len(h_idx)==EXPECTED_H2_EDGE_COUNT,len(h_idx))

        stage="component1_hard_infeasibility_reproduction"
        try:
            from scipy.optimize import linprog
            from scipy import sparse
        except Exception as exc:
            raise GateError("scipy_HiGHS_unavailable:"+repr(exc)) from exc

        n_ex=len(ex_idx);n_h=len(h_idx)
        nbase=n_ex+n_h
        cv_row={int(cv):r for r,cv in enumerate(comp_cvs.tolist())}

        eq_r=[];eq_c=[];eq_v=[]
        for q,cv in enumerate(cex_cv.tolist()):
            eq_r.append(cv_row[int(cv)]);eq_c.append(q);eq_v.append(1.0)
        for q,cv in enumerate(ch_cv.tolist()):
            eq_r.append(cv_row[int(cv)]);eq_c.append(n_ex+q);eq_v.append(1.0)
        Aeq_base=sparse.coo_matrix(
            (np.asarray(eq_v),(np.asarray(eq_r),np.asarray(eq_c))),
            shape=(len(comp_cvs),nbase)
        ).tocsr()
        beq=cv_delta[comp_cvs]

        cell_row={int(c):r for r,c in enumerate(comp_cells.tolist())}
        cr=[];cc=[];vv=[]
        for q,c in enumerate(cex_cell.tolist()):
            cr.append(cell_row[int(c)]);cc.append(q);vv.append(1.0)
        for q,c in enumerate(ch_cell.tolist()):
            cr.append(cell_row[int(c)]);cc.append(n_ex+q);vv.append(1.0)
        Acell_base=sparse.coo_matrix(
            (np.asarray(vv),(np.asarray(cr),np.asarray(cc))),
            shape=(len(comp_cells),nbase)
        ).tocsr()

        bupper=capacity[comp_cells]-fixed_mass[comp_cells]
        blower=fixed_mass[comp_cells]
        Abase=sparse.vstack([Acell_base,-Acell_base],format="csr")
        bbase=np.r_[bupper,blower]

        bounds=[]
        for x0 in cex_x0.tolist():
            if x0>SIGN_TOL_KG:bounds.append((0.0,None))
            elif x0<-SIGN_TOL_KG:bounds.append((None,0.0))
            else:bounds.append((0.0,0.0))
        bounds.extend([(0.0,None)]*n_h)

        c_hard=np.zeros(nbase,dtype=np.float64)
        if n_h:c_hard[n_ex:]=1.0
        hard=linprog(c_hard,A_ub=Abase,b_ub=bbase,A_eq=Aeq_base,b_eq=beq,
                     bounds=bounds,method="highs",options={"presolve":True})
        gate("Day375_component1_hard_stage1_reproduces_infeasible",
             hard.success is False and int(hard.status)==2,
             {"success":bool(hard.success),"status":int(hard.status),"message":str(hard.message)})

        stage="component1_reachability_and_slack_diagnostic"
        pos_existing_count={int(cv):0 for cv in comp_cvs.tolist()}
        neg_existing_count={int(cv):0 for cv in comp_cvs.tolist()}
        h2_count={int(cv):0 for cv in comp_cvs.tolist()}
        completion_count={int(cv):0 for cv in comp_cvs.tolist()}
        for cv,x0 in zip(cex_cv.tolist(),cex_x0.tolist()):
            if x0>SIGN_TOL_KG:pos_existing_count[int(cv)]+=1
            elif x0<-SIGN_TOL_KG:neg_existing_count[int(cv)]+=1
        for cv,iscomp in zip(ch_cv.tolist(),ch_completion.tolist()):
            h2_count[int(cv)]+=1
            if bool(iscomp):completion_count[int(cv)]+=1

        r4_target_set=set(int(x) for x in r4_target_cvs.tolist())
        upper_set=set(int(x) for x in upper_culprit.tolist())
        lower_set=set(int(x) for x in lower_culprit.tolist())

        individual_impossible=[]
        for cv in comp_cvs.tolist():
            d=float(cv_delta[int(cv)])
            has_pos=pos_existing_count[int(cv)]>0 or h2_count[int(cv)]>0
            has_neg=neg_existing_count[int(cv)]>0
            if d>CV_TOL_KG and not has_pos:
                individual_impossible.append((int(cv),"positive_delta_no_positive_or_H2_variable"))
            elif d<-CV_TOL_KG and not has_neg:
                individual_impossible.append((int(cv),"negative_delta_no_negative_variable"))

        # Diagnostic LP: keep exact cell bounds/sign rules/frozen graph, add +/- equality slack.
        # z = [existing, H2, splus, sminus], with A*x + splus - sminus = required CV delta.
        ncv=len(comp_cvs)
        nvar=nbase+2*ncv
        Aeq_diag=sparse.hstack([
            Aeq_base,
            sparse.identity(ncv,format="csr"),
            -sparse.identity(ncv,format="csr"),
        ],format="csr")
        Acell_diag=sparse.hstack([
            Acell_base,
            sparse.csr_matrix((len(comp_cells),2*ncv))
        ],format="csr")
        A_ub_diag=sparse.vstack([Acell_diag,-Acell_diag],format="csr")
        b_ub_diag=bbase
        diag_bounds=list(bounds)+[(0.0,None)]*(2*ncv)
        cdiag=np.zeros(nvar,dtype=np.float64)
        cdiag[nbase:]=1.0

        diag=linprog(cdiag,A_ub=A_ub_diag,b_ub=b_ub_diag,A_eq=Aeq_diag,b_eq=beq,
                     bounds=diag_bounds,method="highs",options={"presolve":True})
        gate("diagnostic_slack_LP_success",diag.success,
             {"status":int(diag.status),"message":str(diag.message)})

        z=np.asarray(diag.x,dtype=np.float64)
        basez=z[:nbase]
        splus=z[nbase:nbase+ncv]
        sminus=z[nbase+ncv:nbase+2*ncv]
        abs_slack=splus+sminus
        signed_slack=splus-sminus
        slack_mask=abs_slack>SLACK_TOL_KG

        min_total_slack=float(np.sum(abs_slack))
        max_single_slack=float(np.max(abs_slack)) if len(abs_slack) else 0.0
        slack_cvs=comp_cvs[slack_mask]
        cell_mass=fixed_mass[comp_cells]+np.asarray(Acell_base@basez).ravel()
        lower_v=max(0.0,-float(np.min(cell_mass)))
        upper_v=max(0.0,float(np.max(cell_mass-capacity[comp_cells])))

        slack_outside_r4=[int(cv) for cv in slack_cvs.tolist() if int(cv) not in r4_target_set]
        zero_h2_slack=[int(cv) for cv in slack_cvs.tolist() if h2_count[int(cv)]==0]
        component_outside_r4=[int(cv) for cv in comp_cvs.tolist() if int(cv) not in r4_target_set]
        component_zero_h2=[int(cv) for cv in comp_cvs.tolist() if h2_count[int(cv)]==0]

        if individual_impossible:
            classification="INDIVIDUAL_CV_SIGN_OR_FROZEN_EDGE_REACHABILITY_OBSTRUCTION"
        elif min_total_slack>SLACK_TOL_KG:
            classification="NETWORK_CUT_OBSTRUCTION_UNDER_FROZEN_R4_RECURRENT_ELIGIBILITY"
        else:
            classification="HARD_FEASIBILITY_REPRODUCTION_DISCREPANCY"

        rows=[]
        impossible_map={cv:reason for cv,reason in individual_impossible}
        for r,cv in enumerate(comp_cvs.tolist()):
            rows.append({
                "cv_id":int(cv),
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
                "required_delta_kg":float(beq[r]),
                "existing_positive_variable_count":int(pos_existing_count[int(cv)]),
                "existing_negative_variable_count":int(neg_existing_count[int(cv)]),
                "frozen_H2_edge_count":int(h2_count[int(cv)]),
                "frozen_completion_edge_count":int(completion_count[int(cv)]),
                "in_R4_327_target_set":bool(int(cv) in r4_target_set),
                "is_Day375_upper_culprit":bool(int(cv) in upper_set),
                "is_Day375_lower_culprit":bool(int(cv) in lower_set),
                "individual_reachability_impossible":bool(int(cv) in impossible_map),
                "individual_impossibility_reason":impossible_map.get(int(cv),""),
                "diagnostic_positive_slack_kg":float(splus[r]),
                "diagnostic_negative_slack_kg":float(sminus[r]),
                "diagnostic_signed_slack_kg":float(signed_slack[r]),
                "diagnostic_absolute_slack_kg":float(abs_slack[r]),
            })

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "audit_only":True,
            "repair_executed":False,
            "accepted_state_created":False,
            "Day375_component_id":FAILED_COMPONENT_ID,
            "Day375_component_CV_count":int(len(comp_cvs)),
            "Day375_component_cell_count":int(len(comp_cells)),
            "Day375_component_existing_variable_count":int(n_ex),
            "Day375_component_H2_edge_count":int(n_h),
            "Day375_component_completion_edge_count":int(np.sum(ch_completion)),
            "Day375_component_CVs_in_R4_target_set":int(sum(int(cv) in r4_target_set for cv in comp_cvs.tolist())),
            "Day375_component_CVs_outside_R4_target_set":int(len(component_outside_r4)),
            "Day375_component_CVs_with_zero_H2_edges":int(len(component_zero_h2)),
            "individual_sign_or_reachability_impossible_CV_count":int(len(individual_impossible)),
            "minimum_total_CV_conservation_slack_kg":min_total_slack,
            "maximum_single_CV_conservation_slack_kg":max_single_slack,
            "CVs_with_nonzero_conservation_slack":int(np.sum(slack_mask)),
            "slack_CVs_outside_R4_target_set":int(len(slack_outside_r4)),
            "slack_CVs_with_zero_H2_edges":int(len(zero_h2_slack)),
            "maximum_cell_lower_violation_kg":lower_v,
            "maximum_cell_upper_violation_kg":upper_v,
            "classification":classification,
            "support_growth_executed":False,
            "pressure_refresh_executed":False,
            "P3_authorized":False,
        }

        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "classification":classification,
            "P2_R6_R2_authorized":True,
            "P2_R6_R2_name":"Day375 Recurrent Frozen-Graph Eligibility and Network-Cut Sensitivity Design Freeze",
            "recommended_sensitivity_sequence":[
                "V0_reproduce_current_frozen_R4_component1_minimum_conservation_slack",
                "V1_current_Day375_slack_CVs_component_frontier_completion_within_existing_frozen_H2_cell_domain_only",
                "V2_all_Day375_component1_CVs_component_frontier_completion_within_existing_frozen_H2_cell_domain_only_if_V1_nonzero",
                "V3_existing_sign_rule_physical_admissibility_audit_only_if_V2_nonzero",
            ],
            "repair_execution_authorized":False,
            "support_growth_execution_authorized":False,
            "new_H2_cells_authorized":False,
            "vertical_support_authorized":False,
            "pressure_refresh_authorized":False,
            "P3_authorized":False,
            "P4_authorized":False,
            "P5_training_authorized":False,
            "R3R6R1_execution_invalidated":False,
        }

        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R6_R1_Final_Artifacts"
        if local.exists():
            import shutil
            shutil.rmtree(local)
        local.mkdir(parents=True)

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R1_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R6_R1_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R6_R1_Component1_CV_Diagnostics.csv").write_bytes(csv_bytes(rows))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R6_R1_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists():raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        import shutil
        shutil.copytree(local,out)

        print()
        print("="*194)
        print("POSTV16-AV4-PIVOT-P2-R6-R1: PASS")
        print("Hard Stage-1 infeasibility reproduced       : True")
        print("Component signature                         :",len(comp_cvs),len(comp_cells),n_ex,n_h)
        print("Component CVs outside R4 target set         :",len(component_outside_r4))
        print("Component CVs with zero H2 edges            :",len(component_zero_h2))
        print("Individual reachability-impossible CVs      :",len(individual_impossible))
        print("Minimum total CV conservation slack kg      :",min_total_slack)
        print("Maximum single CV conservation slack kg     :",max_single_slack)
        print("Nonzero-slack CV count                      :",int(np.sum(slack_mask)))
        print("Slack CVs outside R4 target set             :",len(slack_outside_r4))
        print("Slack CVs with zero H2 edges                :",len(zero_h2_slack))
        print("Cell lower / upper violation kg             :",lower_v,"/",upper_v)
        print("Classification                              :",classification)
        print("P2-R6-R2 design/sensitivity authorized      : True")
        print("Repair / support growth / pressure refresh  : False / False / False")
        print("P3 authorized                               : False")
        print("="*194)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R6_R1_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "automatic_rerun_authorized":False,
                "repair_execution_authorized":False,
                "support_growth_execution_authorized":False,
                "pressure_refresh_authorized":False,
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
        self_test();raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))
