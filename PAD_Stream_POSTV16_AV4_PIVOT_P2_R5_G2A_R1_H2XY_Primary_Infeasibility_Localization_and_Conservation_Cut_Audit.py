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


MILESTONE = "POSTV16-AV4-PIVOT-P2-R5-G2A-R1"
STATUS_PASS = (
    "AV4PIVOTP2R5G2AR1_H2XY_PRIMARY_INFEASIBILITY_LOCALIZATION_"
    "AND_CONSERVATION_CUT_AUDIT_PASS_NO_REPAIR_EXECUTION"
)
STATUS_BLOCKED = "AV4PIVOTP2R5G2AR1_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "ec24d9f2821c6f449b3e26dcf907b8953b7dd3b7"
EXPECTED_BRANCH = "postv16-av4-pivot"

GRID=(15,50,50)
NZ,NY,NX=GRID
NCELL=NZ*NY*NX
NSL=1078
NN=201
NCV=200
BACKGROUND=0.20
MAX_SG=0.60
SPD=86400.0

SIGN_TOL_KG=1.0e-10
CELL_TOL_KG=1.0e-7
CV_TOL_KG=1.0e-7
SLACK_REPORT_TOL_KG=1.0e-8

FAILED_COMPONENT_ID=5
EXPECTED_FAILED_CV_COUNT=49627
EXPECTED_FAILED_CELL_COUNT=23845
EXPECTED_FAILED_EXISTING_VARIABLES=59220
EXPECTED_FAILED_HALO_EDGES=402976

BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G2A_FAIL_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_SCIENTIFIC_FAIL"
G2A_FAIL_REPORT="POSTV16_AV4_PIVOT_P2_R5_G2A_Scientific_Fail_Report.json"
G2A_FAIL_STATUS=(
    "AV4PIVOTP2R5G2A_H2XY_EXPANDED_SUPPORT_PROJECTION_SCIENTIFIC_FAIL_"
    "NO_RELAXATION_OR_AUTOMATIC_RERUN_AUTHORIZED"
)
G2A_FAIL_GATE="HiGHS_H2XY_primary_projection_infeasible_or_failed"

G1R1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G1_R1_Alternative_Geometric_Domain_Freeze"
G1R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G1_R1_Summary.json"
G1R1_DECISION="POSTV16_AV4_PIVOT_P2_R5_G1_R1_Decision_Contract.json"
G1R1_STATUS=(
    "AV4PIVOTP2R5G1R1_ALTERNATIVE_GEOMETRIC_DOMAIN_CANDIDATE_"
    "COMPARISON_AND_FREEZE_PASS_NO_SUPPORT_EXPANSION_EXECUTED"
)
SELECTED="H2_XY_TWO_RING_SAME_LAYER_TERMINAL_OCCUPANCY_ENVELOPE"

R1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_R1_TwoSided_Bound_Culprit_Domain_Freeze"
R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_R1_Summary.json"

R3_RECOVERY_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R3_Recovery"
R3_TEACHER_STATE="Day365_to_Day370_Teacher_State.npz"
R3_TEACHER_META="Day365_to_Day370_Teacher_Metadata.json"
R3_RUNNER_BLOB="b02061d33f6105a06320f8843986de584293c677"

F2R3_REL=BASE_AV4/"POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution"
F2R3_STATE="POSTV16_AV4_F2_R3_Accepted_Parent_Restart_State.npz"

A2E_REL=BASE_AV4/"POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH="POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_SUMMARY="PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_STATUS=(
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

OUT_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Infeasibility_Localization_Audit"
BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R1_BLOCKED"

R2SRC="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
E37A="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D="PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB="890088c0c0fcab415a2c7351c5079ca8ee12bf82"
G2A="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_Controlled_H2XY_ExpandedSupport_Projection_Execution.py"
G2A_BLOB="690663239464107e99c267ac2c862d5f7d803c89"

SOURCE_BLOBS={
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
    G2A:G2A_BLOB,
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
    x=np.asarray(a,dtype=np.float64);y=np.asarray(b,dtype=np.float64)
    return float(np.linalg.norm((x-y).ravel())/max(float(np.linalg.norm(y.ravel())),1.0e-30))


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


def ijk(flat:int)->tuple[int,int,int]:
    k=flat//(NY*NX);rem=flat%(NY*NX);j=rem//NX;i=rem%NX
    return k,j,i


def flat_of(k:int,j:int,i:int)->int:
    return k*(NY*NX)+j*NX+i


def h2xy_cells_from_s0(s0:np.ndarray)->np.ndarray:
    s0_set=set(int(x) for x in s0.tolist())
    halo=set()
    for c in s0.tolist():
        k,j,i=ijk(int(c))
        for dj in range(-2,3):
            for di in range(-2,3):
                d=abs(di)+abs(dj)
                if not (1<=d<=2):continue
                jj=j+dj;ii=i+di
                if not (0<=jj<NY and 0<=ii<NX):continue
                h=flat_of(k,jj,ii)
                if h not in s0_set:halo.add(h)
    return np.asarray(sorted(halo),dtype=np.int64)


def self_test()->None:
    c=flat_of(5,20,20)
    h=h2xy_cells_from_s0(np.asarray([c],dtype=np.int64))
    assert len(h)==12
    assert all(ijk(int(x))[0]==5 for x in h)
    print("POSTV16 AV4 PIVOT P2-R5-G2A-R1 structural self-test: PASS")


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
    print("POSTV16-AV4-PIVOT-P2-R5-G2A-R1 -- H2-XY PRIMARY INFEASIBILITY LOCALIZATION / CONSERVATION-CUT AUDIT")
    print("="*194)
    print("AUDIT ONLY. NO REPAIR. NO ACCEPTED STATE. NO NEW SUPPORT AUTHORITY.")
    print("CELL BOUNDS AND G2A SIGN/ELIGIBILITY RULES REMAIN EXACT; ONLY EXPLICIT DIAGNOSTIC CV-EQUALITY SLACK MAY BE USED.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Summary.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal G2A-R1 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_G2AR1_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_failed_G2A_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="G2A_failure_binding"
        fail=load_json(drive/G2A_FAIL_REL/G2A_FAIL_REPORT)
        gate("G2A_fail_status_exact",fail.get("status")==G2A_FAIL_STATUS,fail.get("status"))
        gate("G2A_failed_gate_exact",fail.get("failed_gate")==G2A_FAIL_GATE,fail.get("failed_gate"))
        d=fail.get("detail") or {}
        gate("G2A_failed_component_exact",int(d.get("component_id",-1))==FAILED_COMPONENT_ID,d.get("component_id"))
        gate("G2A_failed_component_counts_exact",
             int(d.get("CV_count",-1))==EXPECTED_FAILED_CV_COUNT
             and int(d.get("cell_count",-1))==EXPECTED_FAILED_CELL_COUNT
             and int(d.get("existing_variable_count",-1))==EXPECTED_FAILED_EXISTING_VARIABLES
             and int(d.get("halo_edge_count",-1))==EXPECTED_FAILED_HALO_EDGES,
             d)
        gate("G2A_no_auto_rerun",fail.get("automatic_rerun_authorized") is False,fail.get("automatic_rerun_authorized"))
        gate("G2A_no_further_support_expansion",fail.get("further_support_expansion_authorized") is False,fail.get("further_support_expansion_authorized"))
        gate("G2A_P3_unauthorized",fail.get("P3_authorized") is False,fail.get("P3_authorized"))

        stage="G1R1_binding"
        gs=load_json(drive/G1R1_REL/G1R1_SUMMARY)
        gd=load_json(drive/G1R1_REL/G1R1_DECISION)
        gate("G1R1_status_exact",gs.get("status")==G1R1_STATUS,gs.get("status"))
        gate("G1R1_selected_H2XY",gs.get("selected_candidate")==SELECTED,gs.get("selected_candidate"))
        gate("G1R1_G2A_authorized",gd.get("P2_R5_G2A_controlled_selected_domain_LP_authorized") is True,gd.get("P2_R5_G2A_controlled_selected_domain_LP_authorized"))

        stage="R3_teacher_binding"
        rec=drive/R3_RECOVERY_REL
        state_path=rec/R3_TEACHER_STATE
        meta=load_json(rec/R3_TEACHER_META)
        gate("R3_teacher_runner_blob_exact",meta.get("runner_blob")==R3_RUNNER_BLOB,meta.get("runner_blob"))
        gate("R3_teacher_state_SHA_exact",meta.get("state_sha256")==sha256_file(state_path),meta.get("state_sha256"))
        with np.load(state_path,allow_pickle=False) as z:
            future_cv_mass=np.asarray(z["future_mass"],dtype=np.float64)
            future_cv_sat=np.asarray(z["future_saturation"],dtype=np.float64)

        stage="authority_state_binding"
        with np.load(drive/F2R3_REL/F2R3_STATE,allow_pickle=False) as z:
            parent_cv_mass=np.asarray(z["parent_CV_component_mass_kg"],dtype=np.float64)
            parent_cv_sat=np.asarray(z["parent_CV_saturation"],dtype=np.float64)
            parent_cv_pv=np.asarray(z["parent_CV_pore_volume_m3"],dtype=np.float64)
            parent_cv_coeff=np.asarray(z["parent_CV_pressure_mass_coeff"],dtype=np.float64)
        gate("A2E_status_exact",load_json(drive/A2E_REL/A2E_SUMMARY).get("status")==A2E_STATUS)
        with np.load(drive/A2E_REL/A2E_EPOCH,allow_pickle=False) as z:
            epoch={k:np.asarray(z[k]).copy() for k in z.files}
        parent_grid_mass=np.asarray(epoch["parent_component_mass_kg"],dtype=np.float64)
        parent_pressure=np.asarray(epoch["refreshed_pressure_psi"],dtype=np.float64)
        grid_pv=np.asarray(epoch["pore_volume_m3"],dtype=np.float64)
        parent_xyz=np.asarray(epoch["streamline_xyz_m"],dtype=np.float64)
        parent_tof=np.asarray(epoch["streamline_tof_s"],dtype=np.float64)
        parent_weights=np.asarray(epoch["streamline_weight_m3_s"],dtype=np.float64)
        p_ref=float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))

        stage="reconstruct_G2A_failed_component"
        r2=load_module(root/R2SRC,"av4_pivot_g2ar1_r2")
        e37=load_module(root/E37A,"av4_pivot_g2ar1_e37")
        sg7d=load_module(root/SG7D,"av4_pivot_g2ar1_sg7d")

        operator=sg7d.build_subsegment_operator(parent_xyz,parent_tof/SPD,parent_weights*SPD)
        geometry=e37.build_control_volume_geometry(r2,operator,parent_pressure,p_ref,NSL,NCV)
        gate("parent_CV_pv_matches_F2R3",
             float(np.max(np.abs(np.asarray(geometry["cv_pv_m3"])-parent_cv_pv)))<=1.0e-8)
        gate("parent_CV_coeff_matches_F2R3",
             relative_l2(np.asarray(geometry["cv_pressure_mass_coeff"]),parent_cv_coeff)<=1.0e-12)

        cv_id=np.asarray(geometry["cv_id"],dtype=np.int64)
        flat=np.asarray(geometry["flat_cell"],dtype=np.int64)
        pv=np.asarray(geometry["pv_m3"],dtype=np.float64)
        pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64)
        old_flat=parent_cv_sat.reshape(-1);new_flat=future_cv_sat.reshape(-1)
        old_sub=old_flat[cv_id];new_sub=new_flat[cv_id]
        old_sg=np.clip(old_sub-BACKGROUND,0.0,MAX_SG);new_sg=np.clip(new_sub-BACKGROUND,0.0,MAX_SG)
        rho_old=np.asarray(r2.gas_density_from_state(old_sub,pseg,p_ref),dtype=np.float64)
        rho_new=np.asarray(r2.gas_density_from_state(new_sub,pseg,p_ref),dtype=np.float64)
        sub_delta=pv*(rho_new*new_sg-rho_old*old_sg)

        cv_delta=(future_cv_mass-parent_cv_mass).reshape(-1)
        transfer=np.bincount(cv_id,weights=sub_delta,minlength=NSL*NCV)
        gate("per_CV_transfer_closure",float(np.max(np.abs(transfer-cv_delta)))<=CV_TOL_KG,
             float(np.max(np.abs(transfer-cv_delta))))

        key=cv_id.astype(np.int64)*NCELL+flat.astype(np.int64)
        order=np.argsort(key,kind="mergesort")
        key_s=key[order];val_s=sub_delta[order]
        starts=np.r_[0,1+np.flatnonzero(key_s[1:]!=key_s[:-1])]
        pair_key=key_s[starts]
        pair_val=np.add.reduceat(val_s,starts)
        pair_cv=(pair_key//NCELL).astype(np.int64)
        pair_cell=(pair_key%NCELL).astype(np.int64)

        original_delta=np.bincount(pair_cell,weights=pair_val,minlength=NCELL)
        original_future=parent_grid_mass.reshape(-1)+original_delta
        sat_max=np.full(GRID,BACKGROUND+MAX_SG,dtype=np.float64)
        rho_max=np.asarray(r2.gas_density_from_state(sat_max,parent_pressure,p_ref),dtype=np.float64)
        capacity=(grid_pv*rho_max*MAX_SG).reshape(-1)
        lower=original_future<-CELL_TOL_KG
        upper=original_future>capacity+CELL_TOL_KG

        lower_culprit=np.unique(pair_cv[lower[pair_cell]&(pair_val<-SIGN_TOL_KG)]).astype(np.int64)
        upper_culprit=np.unique(pair_cv[upper[pair_cell]&(pair_val>SIGN_TOL_KG)]).astype(np.int64)
        union_culprit=np.union1d(lower_culprit,upper_culprit).astype(np.int64)
        union_mask=np.zeros(NSL*NCV,dtype=bool);union_mask[union_culprit]=True
        upper_mask=np.zeros(NSL*NCV,dtype=bool);upper_mask[upper_culprit]=True

        existing_mask=union_mask[pair_cv]
        existing_cv=pair_cv[existing_mask]
        existing_cell=pair_cell[existing_mask]
        existing_val=pair_val[existing_mask]
        s0=np.unique(existing_cell)
        halo=h2xy_cells_from_s0(s0)
        halo_set=set(int(x) for x in halo.tolist())

        ex_nonzero=np.abs(existing_val)>SIGN_TOL_KG
        var_ex_cv=existing_cv[ex_nonzero]
        var_ex_cell=existing_cell[ex_nonzero]
        var_ex_x0=existing_val[ex_nonzero]

        upper_existing=upper_mask[pair_cv]
        ue_cv=pair_cv[upper_existing]
        ue_cell=pair_cell[upper_existing]
        halo_edge_set=set()
        for cv,cell in zip(ue_cv.tolist(),ue_cell.tolist()):
            k,j,i=ijk(int(cell))
            for dj in range(-2,3):
                for di in range(-2,3):
                    dist=abs(di)+abs(dj)
                    if not (1<=dist<=2):continue
                    jj=j+dj;ii=i+di
                    if not (0<=jj<NY and 0<=ii<NX):continue
                    h=flat_of(k,jj,ii)
                    if h in halo_set:halo_edge_set.add((int(cv),int(h)))
        halo_edges=sorted(halo_edge_set)
        halo_cv=np.asarray([e[0] for e in halo_edges],dtype=np.int64)
        halo_cell=np.asarray([e[1] for e in halo_edges],dtype=np.int64)

        variable_existing_global=union_mask[pair_cv]&(np.abs(pair_val)>SIGN_TOL_KG)
        fixed_delta=np.bincount(pair_cell[~variable_existing_global],
                                weights=pair_val[~variable_existing_global],minlength=NCELL)
        fixed_mass=parent_grid_mass.reshape(-1)+fixed_delta

        all_cells=np.union1d(s0,halo).astype(np.int64)
        cv_local={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local={int(c):n for n,c in enumerate(all_cells.tolist())}
        dsu=DSU(len(union_culprit)+len(all_cells));off=len(union_culprit)
        for cv,cell in zip(existing_cv.tolist(),existing_cell.tolist()):
            dsu.union(cv_local[int(cv)],off+cell_local[int(cell)])
        for cv,cell in halo_edges:
            dsu.union(cv_local[int(cv)],off+cell_local[int(cell)])
        roots=sorted({dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()})
        comp_root=roots[FAILED_COMPONENT_ID]
        comp_cvs=np.asarray([cv for cv in union_culprit.tolist() if dsu.find(cv_local[int(cv)])==comp_root],dtype=np.int64)

        root_of_cv={int(cv):dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()}
        ex_idx=np.flatnonzero(np.asarray([root_of_cv[int(cv)]==comp_root for cv in var_ex_cv],dtype=bool))
        h_idx=np.flatnonzero(np.asarray([root_of_cv[int(cv)]==comp_root for cv in halo_cv],dtype=bool))
        comp_cells=np.unique(np.r_[var_ex_cell[ex_idx],halo_cell[h_idx]]).astype(np.int64)

        gate("failed_component_CV_count_reproduced",len(comp_cvs)==EXPECTED_FAILED_CV_COUNT,len(comp_cvs))
        gate("failed_component_cell_count_reproduced",len(comp_cells)==EXPECTED_FAILED_CELL_COUNT,len(comp_cells))
        gate("failed_existing_variable_count_reproduced",len(ex_idx)==EXPECTED_FAILED_EXISTING_VARIABLES,len(ex_idx))
        gate("failed_halo_edge_count_reproduced",len(h_idx)==EXPECTED_FAILED_HALO_EDGES,len(h_idx))

        cex_cv=var_ex_cv[ex_idx];cex_cell=var_ex_cell[ex_idx];cex_x0=var_ex_x0[ex_idx]
        ch_cv=halo_cv[h_idx];ch_cell=halo_cell[h_idx]
        n_ex=len(ex_idx);n_h=len(h_idx)

        stage="individual_CV_sign_reachability_audit"
        cv_row={int(cv):r for r,cv in enumerate(comp_cvs.tolist())}
        pos_existing=np.zeros(len(comp_cvs),dtype=np.int64)
        neg_existing=np.zeros(len(comp_cvs),dtype=np.int64)
        halo_count=np.zeros(len(comp_cvs),dtype=np.int64)
        for cv,x0 in zip(cex_cv.tolist(),cex_x0.tolist()):
            r=cv_row[int(cv)]
            if x0>SIGN_TOL_KG:pos_existing[r]+=1
            elif x0<-SIGN_TOL_KG:neg_existing[r]+=1
        for cv in ch_cv.tolist():
            halo_count[cv_row[int(cv)]]+=1

        comp_delta=cv_delta[comp_cvs]
        impossible_positive=(comp_delta>CV_TOL_KG)&((pos_existing+halo_count)==0)
        impossible_negative=(comp_delta<-CV_TOL_KG)&(neg_existing==0)
        individually_impossible=impossible_positive|impossible_negative

        stage="reproduce_baseline_infeasibility"
        try:
            from scipy.optimize import linprog
            from scipy import sparse
            import scipy
        except Exception as exc:
            raise GateError("scipy_HiGHS_unavailable:"+repr(exc)) from exc
        print("SciPy version:",scipy.__version__)

        # Base variable vector q=[existing x, halo h].
        nbase=n_ex+n_h
        er=[];ec=[];ev=[]
        for q,cv in enumerate(cex_cv.tolist()):
            er.append(cv_row[int(cv)]);ec.append(q);ev.append(1.0)
        for q,cv in enumerate(ch_cv.tolist()):
            er.append(cv_row[int(cv)]);ec.append(n_ex+q);ev.append(1.0)
        Aeq_base=sparse.coo_matrix(
            (np.asarray(ev),(np.asarray(er),np.asarray(ec))),
            shape=(len(comp_cvs),nbase)
        ).tocsr()
        beq=comp_delta

        cell_row={int(c):r for r,c in enumerate(comp_cells.tolist())}
        cr=[];cc=[];cvv=[]
        for q,c in enumerate(cex_cell.tolist()):
            cr.append(cell_row[int(c)]);cc.append(q);cvv.append(1.0)
        for q,c in enumerate(ch_cell.tolist()):
            cr.append(cell_row[int(c)]);cc.append(n_ex+q);cvv.append(1.0)
        Acell=sparse.coo_matrix(
            (np.asarray(cvv),(np.asarray(cr),np.asarray(cc))),
            shape=(len(comp_cells),nbase)
        ).tocsr()
        Aub_base=sparse.vstack([Acell,-Acell],format="csr")
        bub_base=np.r_[capacity[comp_cells]-fixed_mass[comp_cells],
                       fixed_mass[comp_cells]]

        base_bounds=[]
        for x0 in cex_x0.tolist():
            if x0>SIGN_TOL_KG:base_bounds.append((0.0,None))
            elif x0<-SIGN_TOL_KG:base_bounds.append((None,0.0))
            else:base_bounds.append((0.0,0.0))
        base_bounds.extend([(0.0,None)]*n_h)

        t0=time.time()
        baseline=linprog(np.zeros(nbase),A_ub=Aub_base,b_ub=bub_base,
                         A_eq=Aeq_base,b_eq=beq,bounds=base_bounds,
                         method="highs",options={"presolve":True})
        baseline_s=float(time.time()-t0)
        gate("baseline_primary_infeasibility_reproduced",
             (not baseline.success) and int(baseline.status)==2,
             {"success":baseline.success,"status":int(baseline.status),"message":str(baseline.message)})

        stage="minimum_CV_conservation_slack_audit"
        # q=[base variables, under p, over n], with A*x + p - n = delta.
        ncv=len(comp_cvs)
        nvar=nbase+2*ncv
        Aeq=sparse.hstack([
            Aeq_base,
            sparse.eye(ncv,format="csr"),
            -sparse.eye(ncv,format="csr"),
        ],format="csr")
        Aub=sparse.hstack([
            Aub_base,
            sparse.csr_matrix((Aub_base.shape[0],2*ncv)),
        ],format="csr")
        bounds=base_bounds+[(0.0,None)]*(2*ncv)
        c=np.zeros(nvar,dtype=np.float64)
        c[nbase:]=1.0

        t0=time.time()
        relax=linprog(c,A_ub=Aub,b_ub=bub_base,A_eq=Aeq,b_eq=beq,
                      bounds=bounds,method="highs",options={"presolve":True})
        relax_s=float(time.time()-t0)
        gate("CV_slack_diagnostic_LP_success",relax.success,
             {"status":int(relax.status),"message":str(relax.message)})
        z=np.asarray(relax.x,dtype=np.float64)
        under=z[nbase:nbase+ncv]
        over=z[nbase+ncv:]
        signed_residual=over-under  # assigned - required
        abs_slack=under+over

        total_slack=float(np.sum(abs_slack))
        max_slack=float(np.max(abs_slack))
        slack_mask=abs_slack>SLACK_REPORT_TOL_KG
        slack_count=int(np.sum(slack_mask))
        slack_no_halo=int(np.sum(slack_mask&(halo_count==0)))
        slack_not_upper=int(np.sum(slack_mask&(~np.isin(comp_cvs,upper_culprit))))
        slack_positive_delta_no_halo=int(np.sum(
            slack_mask&(comp_delta>CV_TOL_KG)&(halo_count==0)
        ))

        # Exact cell certification for the diagnostic relaxed solution.
        base_z=z[:nbase]
        cell_mass=fixed_mass[comp_cells]+np.asarray(Acell@base_z).ravel()
        max_lower=max(0.0,-float(np.min(cell_mass)))
        max_upper=max(0.0,float(np.max(cell_mass-capacity[comp_cells])))
        gate("diagnostic_cell_lower_exact",max_lower<=CELL_TOL_KG,max_lower)
        gate("diagnostic_cell_upper_exact",max_upper<=CELL_TOL_KG,max_upper)

        # Per-CV diagnostics.
        upper_set=set(int(x) for x in upper_culprit.tolist())
        lower_set=set(int(x) for x in lower_culprit.tolist())
        rows=[]
        for r,cv in enumerate(comp_cvs.tolist()):
            if abs_slack[r]<=SLACK_REPORT_TOL_KG and not individually_impossible[r]:
                continue
            rows.append({
                "cv_id":int(cv),
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
                "required_CV_delta_kg":float(comp_delta[r]),
                "under_assignment_slack_kg":float(under[r]),
                "over_assignment_slack_kg":float(over[r]),
                "signed_assigned_minus_required_kg":float(signed_residual[r]),
                "absolute_conservation_slack_kg":float(abs_slack[r]),
                "is_upper_culprit":bool(int(cv) in upper_set),
                "is_lower_culprit":bool(int(cv) in lower_set),
                "existing_positive_variable_count":int(pos_existing[r]),
                "existing_negative_variable_count":int(neg_existing[r]),
                "H2_halo_edge_count":int(halo_count[r]),
                "individually_sign_impossible_positive":bool(impossible_positive[r]),
                "individually_sign_impossible_negative":bool(impossible_negative[r]),
            })
        rows.sort(key=lambda x:(-x["absolute_conservation_slack_kg"],x["cv_id"]))

        stage="classification_freeze"
        sign_impossible_count=int(np.sum(individually_impossible))
        if sign_impossible_count>0:
            classification="PER_CV_SIGN_OR_EDGE_ELIGIBILITY_OBSTRUCTION_PRESENT"
            next_name="Per-CV Sign/Eligibility Obstruction Design Audit"
            eligibility_audit=True
            cut_audit=False
            numerical_audit=False
            rationale=(
                "At least one failed-component CV cannot satisfy its own exact Day365->370 delta even before "
                "cell competition, under the frozen existing-edge sign bounds and current H2 halo eligibility."
            )
        elif total_slack>SLACK_REPORT_TOL_KG:
            classification="NETWORK_CUT_OBSTRUCTION_UNDER_CURRENT_H2_EDGE_ELIGIBILITY"
            next_name="H2-XY Edge-Eligibility and Network-Cut Sensitivity Design Freeze"
            eligibility_audit=True
            cut_audit=True
            numerical_audit=False
            rationale=(
                "Every CV is individually sign-reachable, but exact Cartesian cell bounds force nonzero minimum "
                "CV-conservation slack under the current G2A graph. This is a coupled network-cut obstruction, "
                "not a total H2 capacity shortage."
            )
        else:
            classification="BASELINE_INFEASIBLE_BUT_ZERO_SLACK_RELAXATION_NUMERICAL_CONDITIONING_AUDIT_REQUIRED"
            next_name="HiGHS Numerical Conditioning / Formulation Equivalence Audit"
            eligibility_audit=False
            cut_audit=False
            numerical_audit=True
            rationale=(
                "The baseline solve reports infeasible while the equality-relaxed diagnostic reaches essentially "
                "zero conservation slack with exact cell bounds, so formulation/numerical conditioning must be audited "
                "before changing physics or support semantics."
            )

        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R5_G2A_R1_Final_Artifacts"
        if local.exists():shutil.rmtree(local)
        local.mkdir(parents=True)
        plots=local/"plots";plots.mkdir()

        # Slack histogram.
        fig=plt.figure(figsize=(7,5))
        ax=fig.add_subplot(111)
        vals=abs_slack[slack_mask]
        if len(vals):
            ax.hist(vals,bins=min(60,max(10,int(np.sqrt(len(vals))))))
        ax.set_xlabel("Absolute per-CV conservation slack (kg)")
        ax.set_ylabel("CV count")
        ax.set_title("G2A failed component — minimum conservation slack")
        ax.grid(True,alpha=0.25)
        fig.savefig(plots/"G2AR1_CV_conservation_slack_histogram.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        # Top slack CVs.
        top=rows[:50]
        fig=plt.figure(figsize=(9,5))
        ax=fig.add_subplot(111)
        if top:
            ax.bar(np.arange(len(top)),[r["absolute_conservation_slack_kg"] for r in top])
        ax.set_xlabel("Top slack CV rank")
        ax.set_ylabel("Absolute conservation slack (kg)")
        ax.set_title("Top G2A blocked CVs")
        ax.grid(True,axis="y",alpha=0.25)
        fig.savefig(plots/"G2AR1_top_CV_conservation_slack.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "failed_component_id":FAILED_COMPONENT_ID,
            "failed_component_CV_count":int(len(comp_cvs)),
            "failed_component_cell_count":int(len(comp_cells)),
            "failed_component_existing_variable_count":int(n_ex),
            "failed_component_H2_halo_edge_count":int(n_h),
            "individual_sign_impossible_CV_count":sign_impossible_count,
            "individual_positive_delta_no_positive_or_halo_variable_count":int(np.sum(impossible_positive)),
            "individual_negative_delta_no_negative_variable_count":int(np.sum(impossible_negative)),
            "minimum_total_CV_conservation_slack_kg":total_slack,
            "maximum_single_CV_conservation_slack_kg":max_slack,
            "CVs_with_nonzero_conservation_slack":slack_count,
            "slack_CVs_without_H2_halo_edges":slack_no_halo,
            "slack_CVs_not_original_upper_culprits":slack_not_upper,
            "positive_delta_slack_CVs_without_H2_halo_edges":slack_positive_delta_no_halo,
            "diagnostic_maximum_cell_lower_violation_kg":max_lower,
            "diagnostic_maximum_cell_upper_violation_kg":max_upper,
            "baseline_infeasible_solver_runtime_s":baseline_s,
            "CV_slack_diagnostic_solver_runtime_s":relax_s,
            "classification":classification,
            "repair_executed":False,
            "support_changed":False,
            "accepted_state_created":False,
            "P3_authorized":False,
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "classification":classification,
            "classification_rationale":rationale,
            "P2_R5_G2A_R2_authorized":True,
            "P2_R5_G2A_R2_name":next_name,
            "edge_eligibility_sensitivity_audit_authorized":bool(eligibility_audit),
            "network_cut_sensitivity_audit_authorized":bool(cut_audit),
            "numerical_conditioning_audit_authorized":bool(numerical_audit),
            "repair_execution_authorized":False,
            "further_support_expansion_execution_authorized":False,
            "physics_relaxation_authorized":False,
            "P3_authorized":False,
            "periodic_cadence_selected_now":False,
            "R3R6R1_execution_invalidated":False,
        }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R1_CV_Slack_Diagnostics.csv").write_bytes(csv_bytes(rows))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({"file":str(p.relative_to(local)).replace("\\","/"),
                                 "sha256":sha256_file(p),"bytes":p.stat().st_size})
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists():raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*194)
        print("POSTV16-AV4-PIVOT-P2-R5-G2A-R1: PASS")
        print("Individual sign-impossible CVs                 :",sign_impossible_count)
        print("Minimum total CV conservation slack kg         :",total_slack)
        print("Maximum single-CV conservation slack kg        :",max_slack)
        print("CVs with nonzero conservation slack            :",slack_count)
        print("Slack CVs without H2 halo edges                :",slack_no_halo)
        print("Slack CVs not original upper culprits          :",slack_not_upper)
        print("Positive-delta slack CVs without H2 edges      :",slack_positive_delta_no_halo)
        print("Diagnostic max lower/upper cell violation kg   :",max_lower,"/",max_upper)
        print("Classification                                 :",classification)
        print("NEXT                                            :",next_name)
        print("Repair execution authorized                     : False")
        print("Further support expansion execution authorized  : False")
        print("P3 authorized                                  : False")
        print("="*194)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "automatic_rerun_authorized":False,
                "repair_execution_authorized":False,
                "further_support_expansion_execution_authorized":False,
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
