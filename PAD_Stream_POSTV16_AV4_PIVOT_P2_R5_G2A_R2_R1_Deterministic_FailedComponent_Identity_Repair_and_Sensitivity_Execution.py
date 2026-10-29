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


MILESTONE = "POSTV16-AV4-PIVOT-P2-R5-G2A-R2-R1"
STATUS_PASS = (
    "AV4PIVOTP2R5G2AR2R1_DETERMINISTIC_FAILED_COMPONENT_IDENTITY_REPAIR_"
    "AND_EDGE_ELIGIBILITY_SENSITIVITY_EXECUTION_PASS"
)
STATUS_BLOCKED = "AV4PIVOTP2R5G2AR2R1_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "1bd0f8ef8d5b4bcbd211ad389e017283d5950260"
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
SLACK_TOL_KG=1.0e-8

FAILED_COMPONENT_ID=5
EXPECTED_FAILED_CV_COUNT=49627
EXPECTED_FAILED_CELL_COUNT=23845
EXPECTED_FAILED_EXISTING_VARIABLES=59220
EXPECTED_FAILED_HALO_EDGES=402976
EXPECTED_BASELINE_SLACK=26847.63444871952
EXPECTED_BASELINE_SLACK_CVS=327
EXPECTED_ZERO_H2_SLACK_CVS=14
EXPECTED_NOT_UPPER_SLACK_CVS=0

BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

R1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Infeasibility_Localization_Audit"
R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Summary.json"
R1_DECISION="POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Decision_Contract.json"
R1_CSV="POSTV16_AV4_PIVOT_P2_R5_G2A_R1_CV_Slack_Diagnostics.csv"
R1_STATUS=(
    "AV4PIVOTP2R5G2AR1_H2XY_PRIMARY_INFEASIBILITY_LOCALIZATION_"
    "AND_CONSERVATION_CUT_AUDIT_PASS_NO_REPAIR_EXECUTION"
)
R1_CLASS="NETWORK_CUT_OBSTRUCTION_UNDER_CURRENT_H2_EDGE_ELIGIBILITY"

G2A_FAIL_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_SCIENTIFIC_FAIL"
G2A_FAIL_REPORT="POSTV16_AV4_PIVOT_P2_R5_G2A_Scientific_Fail_Report.json"

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

R2_BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R2_BLOCKED"
R2_BLOCK_REPORT="POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_Blocked_Report.json"
R2_BLOCK_STATUS="AV4PIVOTP2R5G2AR2_TECHNICAL_OR_AUTHORITY_BLOCK"
R2_BLOCK_STAGE="reconstruct_failed_component"
R2_BLOCK_EXCEPTION="GateError('slack_CVs_subset_failed_component')"

OUT_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_Deterministic_Component_Repair_and_Sensitivity"
BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_BLOCKED"

R2SRC="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
E37A="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D="PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB="890088c0c0fcab415a2c7351c5079ca8ee12bf82"
R1RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R1_H2XY_Primary_Infeasibility_Localization_and_Conservation_Cut_Audit.py"
R1RUN_BLOB="e5adc8f92d8f9fe99a985be64d2a8322b94d230b"
R2RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R2_H2XY_EdgeEligibility_and_NetworkCut_Sensitivity_Design_Freeze.py"
R2RUN_BLOB="69d36def910aac5c0c2b631e521f74a474e9fb49"

SOURCE_BLOBS={
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
    R1RUN:R1RUN_BLOB,
    R2RUN:R2RUN_BLOB,
}


class GateError(RuntimeError):
    pass


def git_text(root:Path,*args:str)->str:
    return subprocess.run(
        ["git","-C",str(root),*args],check=True,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE
    ).stdout.strip()


def load_json(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path:Path)->list[dict[str,str]]:
    with path.open("r",newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:raise GateError(f"cannot_load_module:{path}")
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m)
    return m


def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
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


class DSU:
    def __init__(self,n:int):
        self.p=np.arange(n,dtype=np.int64);self.r=np.zeros(n,dtype=np.int8)
    def find(self,x:int)->int:
        while self.p[x]!=x:
            self.p[x]=self.p[self.p[x]];x=int(self.p[x])
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


def h2xy_from_cells(cells:np.ndarray,s0_set:set[int])->set[int]:
    out=set()
    for c in cells.tolist():
        k,j,i=ijk(int(c))
        for dj in range(-2,3):
            for di in range(-2,3):
                d=abs(di)+abs(dj)
                if not (1<=d<=2):continue
                jj=j+dj;ii=i+di
                if not (0<=jj<NY and 0<=ii<NX):continue
                h=flat_of(k,jj,ii)
                if h not in s0_set:out.add(h)
    return out


def self_test()->None:
    c=flat_of(5,20,20)
    s={c}
    assert len(h2xy_from_cells(np.asarray([c],dtype=np.int64),s))==12
    print("POSTV16 AV4 PIVOT P2-R5-G2A-R2-R1 structural self-test: PASS")


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
    print("POSTV16-AV4-PIVOT-P2-R5-G2A-R2-R1 -- DETERMINISTIC FAILED-COMPONENT IDENTITY REPAIR / SENSITIVITY EXECUTION")
    print("="*194)
    print("TECHNICAL REPAIR OF COMPONENT IDENTITY ONLY; SCIENTIFIC SENSITIVITY CONTRACT UNCHANGED. NO ACCEPTED STATE. NO NEW CELLS.")
    print("ALL VARIANTS USE THE SAME FROZEN H2-XY CELL DOMAIN AND EXACT CARTESIAN CELL BOUNDS.")
    print()

    try:
        stage="formal_outcome_firewall"
        psum=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_Summary.json"
        block=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_Blocked_Report.json"
        if psum.is_file():
            print("[PASS] formal G2A-R2-R1 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_G2AR2R1_BLOCK",not block.exists(),str(block))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_blocked_G2AR2_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,
             git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",
             repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="G2AR2_block_binding"
        blocked=load_json(drive/R2_BLOCK_REL/R2_BLOCK_REPORT)
        gate("G2AR2_block_status_exact",blocked.get("status")==R2_BLOCK_STATUS,blocked.get("status"))
        gate("G2AR2_block_stage_exact",blocked.get("failed_stage")==R2_BLOCK_STAGE,blocked.get("failed_stage"))
        gate("G2AR2_block_exception_exact",blocked.get("exception")==R2_BLOCK_EXCEPTION,blocked.get("exception"))
        gate("G2AR2_automatic_rerun_false",blocked.get("automatic_rerun_authorized") is False,blocked.get("automatic_rerun_authorized"))
        gate("G2AR2_repair_execution_false",blocked.get("repair_execution_authorized") is False,blocked.get("repair_execution_authorized"))
        gate("G2AR2_support_expansion_false",blocked.get("further_support_expansion_execution_authorized") is False,blocked.get("further_support_expansion_execution_authorized"))
        gate("G2AR2_P3_false",blocked.get("P3_authorized") is False,blocked.get("P3_authorized"))

        stage="G2AR1_binding"
        r1dir=drive/R1_REL
        s1=load_json(r1dir/R1_SUMMARY)
        d1=load_json(r1dir/R1_DECISION)
        rows1=read_csv(r1dir/R1_CSV)
        gate("G2AR1_status_exact",s1.get("status")==R1_STATUS,s1.get("status"))
        gate("G2AR1_class_exact",s1.get("classification")==R1_CLASS,s1.get("classification"))
        gate("G2AR1_R2_authorized",d1.get("P2_R5_G2A_R2_authorized") is True,d1.get("P2_R5_G2A_R2_authorized"))
        gate("G2AR1_edge_eligibility_audit_authorized",d1.get("edge_eligibility_sensitivity_audit_authorized") is True)
        gate("G2AR1_network_cut_audit_authorized",d1.get("network_cut_sensitivity_audit_authorized") is True)
        gate("G2AR1_repair_not_authorized",d1.get("repair_execution_authorized") is False)
        gate("G2AR1_support_expansion_not_authorized",d1.get("further_support_expansion_execution_authorized") is False)
        gate("G2AR1_P3_unauthorized",d1.get("P3_authorized") is False)
        gate("baseline_slack_exact",
             abs(float(s1["minimum_total_CV_conservation_slack_kg"])-EXPECTED_BASELINE_SLACK)<=1e-6,
             s1["minimum_total_CV_conservation_slack_kg"])
        gate("baseline_slack_CV_count_exact",int(s1["CVs_with_nonzero_conservation_slack"])==EXPECTED_BASELINE_SLACK_CVS)
        gate("baseline_zero_H2_slack_CV_count_exact",int(s1["slack_CVs_without_H2_halo_edges"])==EXPECTED_ZERO_H2_SLACK_CVS)
        gate("baseline_not_upper_slack_CV_count_exact",int(s1["slack_CVs_not_original_upper_culprits"])==EXPECTED_NOT_UPPER_SLACK_CVS)

        slack_rows=[r for r in rows1 if float(r["absolute_conservation_slack_kg"])>SLACK_TOL_KG]
        slack_cvs=np.asarray(sorted({int(r["cv_id"]) for r in slack_rows}),dtype=np.int64)
        zero_h2_slack_cvs=np.asarray(sorted({
            int(r["cv_id"]) for r in slack_rows
            if int(r["H2_halo_edge_count"])==0 and float(r["required_CV_delta_kg"])>CV_TOL_KG
        }),dtype=np.int64)
        gate("slack_CV_CSV_count_exact",len(slack_cvs)==EXPECTED_BASELINE_SLACK_CVS,len(slack_cvs))
        gate("zero_H2_slack_CV_CSV_count_exact",len(zero_h2_slack_cvs)==EXPECTED_ZERO_H2_SLACK_CVS,len(zero_h2_slack_cvs))

        stage="teacher_and_state_binding"
        rec=drive/R3_RECOVERY_REL
        state_path=rec/R3_TEACHER_STATE
        meta=load_json(rec/R3_TEACHER_META)
        gate("R3_teacher_runner_blob_exact",meta.get("runner_blob")==R3_RUNNER_BLOB,meta.get("runner_blob"))
        gate("R3_teacher_state_SHA_exact",meta.get("state_sha256")==sha256_file(state_path),meta.get("state_sha256"))
        with np.load(state_path,allow_pickle=False) as z:
            future_cv_mass=np.asarray(z["future_mass"],dtype=np.float64)
            future_cv_sat=np.asarray(z["future_saturation"],dtype=np.float64)

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

        stage="reconstruct_failed_component"
        r2=load_module(root/R2SRC,"av4_pivot_g2ar2_r2")
        e37=load_module(root/E37A,"av4_pivot_g2ar2_e37")
        sg7d=load_module(root/SG7D,"av4_pivot_g2ar2_sg7d")
        operator=sg7d.build_subsegment_operator(parent_xyz,parent_tof/SPD,parent_weights*SPD)
        geometry=e37.build_control_volume_geometry(r2,operator,parent_pressure,p_ref,NSL,NCV)
        gate("parent_CV_pv_matches_F2R3",
             float(np.max(np.abs(np.asarray(geometry["cv_pv_m3"])-parent_cv_pv)))<=1e-8)
        gate("parent_CV_coeff_matches_F2R3",
             relative_l2(np.asarray(geometry["cv_pressure_mass_coeff"]),parent_cv_coeff)<=1e-12)

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
        gate("per_CV_transfer_closure",float(np.max(np.abs(transfer-cv_delta)))<=CV_TOL_KG)

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
        existing_cv=pair_cv[existing_mask];existing_cell=pair_cell[existing_mask];existing_val=pair_val[existing_mask]
        s0=np.unique(existing_cell);s0_set=set(int(x) for x in s0.tolist())
        halo=np.asarray(sorted(h2xy_from_cells(s0,s0_set)),dtype=np.int64)
        halo_set=set(int(x) for x in halo.tolist())

        ex_nonzero=np.abs(existing_val)>SIGN_TOL_KG
        var_ex_cv=existing_cv[ex_nonzero];var_ex_cell=existing_cell[ex_nonzero];var_ex_x0=existing_val[ex_nonzero]

        # Original two-sided S0 components BEFORE halo-induced merging.
        cv_local0={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local0={int(c):n for n,c in enumerate(s0.tolist())}
        d0=DSU(len(union_culprit)+len(s0));off0=len(union_culprit)
        for cv,cell in zip(existing_cv.tolist(),existing_cell.tolist()):
            d0.union(cv_local0[int(cv)],off0+cell_local0[int(cell)])
        orig_root_of_cv={int(cv):d0.find(cv_local0[int(cv)]) for cv in union_culprit.tolist()}
        orig_root_of_cell={int(c):d0.find(off0+cell_local0[int(c)]) for c in s0.tolist()}

        # H2 frontier by original S0 component.
        frontier_by_root={}
        for c in s0.tolist():
            root_id=orig_root_of_cell[int(c)]
            frontier_by_root.setdefault(root_id,set()).update(h2xy_from_cells(np.asarray([c],dtype=np.int64),s0_set))

        # Current G2A halo edges.
        ue=upper_mask[pair_cv]
        current_edges=set()
        for cv,cell in zip(pair_cv[ue].tolist(),pair_cell[ue].tolist()):
            local=h2xy_from_cells(np.asarray([int(cell)],dtype=np.int64),s0_set)
            for h in local:
                if h in halo_set:current_edges.add((int(cv),int(h)))

        # Deterministic technical repair: reproduce the G2A/R1 union order and select the
        # physical failed component by the authoritative R1 slack-CV signature, not by an
        # unstable DSU representative number. R2's blocked implementation iterated an
        # unordered set here, so its numeric component index was not a physical identifier.
        all_cells=np.union1d(s0,halo).astype(np.int64)
        cv_local={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local={int(c):n for n,c in enumerate(all_cells.tolist())}
        dsu=DSU(len(union_culprit)+len(all_cells));off=len(union_culprit)
        for cv,cell in zip(existing_cv.tolist(),existing_cell.tolist()):
            dsu.union(cv_local[int(cv)],off+cell_local[int(cell)])
        current_edges_sorted=sorted(current_edges)
        for cv,h in current_edges_sorted:
            dsu.union(cv_local[int(cv)],off+cell_local[int(h)])
        roots=sorted({dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()})

        slack_roots=sorted({dsu.find(cv_local[int(cv)]) for cv in slack_cvs.tolist()})
        gate("all_authoritative_R1_slack_CVs_share_one_physical_component",len(slack_roots)==1,slack_roots)
        failed_root=slack_roots[0]
        deterministic_component_index=int(roots.index(failed_root))
        gate("deterministic_component_index_reproduces_G2A",deterministic_component_index==FAILED_COMPONENT_ID,deterministic_component_index)

        comp_cvs=np.asarray([cv for cv in union_culprit.tolist() if dsu.find(cv_local[int(cv)])==failed_root],dtype=np.int64)
        comp_set=set(int(x) for x in comp_cvs.tolist())
        ex_idx=np.flatnonzero(np.asarray([int(cv) in comp_set for cv in var_ex_cv],dtype=bool))
        base_edges=[(cv,h) for cv,h in current_edges_sorted if cv in comp_set]
        base_hcv=np.asarray([e[0] for e in base_edges],dtype=np.int64)
        base_hcell=np.asarray([e[1] for e in base_edges],dtype=np.int64)
        comp_cells_authority=np.unique(np.r_[var_ex_cell[ex_idx],base_hcell]).astype(np.int64)

        gate("failed_component_CV_count_reproduced",len(comp_cvs)==EXPECTED_FAILED_CV_COUNT,len(comp_cvs))
        gate("failed_component_cell_count_reproduced",len(comp_cells_authority)==EXPECTED_FAILED_CELL_COUNT,len(comp_cells_authority))
        gate("failed_existing_variable_count_reproduced",len(ex_idx)==EXPECTED_FAILED_EXISTING_VARIABLES,len(ex_idx))
        gate("failed_halo_edge_count_reproduced",len(base_edges)==EXPECTED_FAILED_HALO_EDGES,len(base_edges))

        cex_cv=var_ex_cv[ex_idx];cex_cell=var_ex_cell[ex_idx];cex_x0=var_ex_x0[ex_idx]
        n_ex=len(ex_idx)
        variable_existing_global=union_mask[pair_cv]&(np.abs(pair_val)>SIGN_TOL_KG)
        fixed_delta=np.bincount(pair_cell[~variable_existing_global],
                                weights=pair_val[~variable_existing_global],minlength=NCELL)
        fixed_mass=parent_grid_mass.reshape(-1)+fixed_delta

        gate("slack_CVs_subset_repaired_failed_component",all(int(cv) in comp_set for cv in slack_cvs.tolist()))
        gate("zero_H2_slack_CVs_subset_repaired_failed_component",all(int(cv) in comp_set for cv in zero_h2_slack_cvs.tolist()))

        stage="candidate_edge_construction"
        def completion_edges(target_cvs:np.ndarray)->set[tuple[int,int]]:
            out=set()
            for cv in target_cvs.tolist():
                root_id=orig_root_of_cv[int(cv)]
                for h in frontier_by_root.get(root_id,set()):
                    if h in halo_set:
                        out.add((int(cv),int(h)))
            return out-current_edges

        v1_extra=completion_edges(zero_h2_slack_cvs)
        v2_extra=completion_edges(slack_cvs)

        print("Baseline failed component CVs :",len(comp_cvs))
        print("Baseline current H2 edges      :",len(base_edges))
        print("V1 extra component-frontier edges:",len(v1_extra))
        print("V2 extra component-frontier edges:",len(v2_extra))

        stage="diagnostic_LP_sensitivities"
        try:
            from scipy.optimize import linprog
            from scipy import sparse
            import scipy
        except Exception as exc:
            raise GateError("scipy_HiGHS_unavailable:"+repr(exc)) from exc
        print("SciPy version:",scipy.__version__)

        cv_row={int(cv):r for r,cv in enumerate(comp_cvs.tolist())}
        slack_set=set(int(x) for x in slack_cvs.tolist())

        def solve_variant(name:str,extra_edges:set[tuple[int,int]],relax_sign_for_slack:bool)->dict[str,Any]:
            edges=sorted(set(base_edges)|set((cv,h) for cv,h in extra_edges if cv in comp_set))
            hcv=np.asarray([e[0] for e in edges],dtype=np.int64)
            hcell=np.asarray([e[1] for e in edges],dtype=np.int64)
            comp_cells=np.unique(np.r_[cex_cell,hcell]).astype(np.int64)
            n_h=len(edges);nbase=n_ex+n_h;ncv=len(comp_cvs)

            er=[];ec=[];ev=[]
            for q,cv in enumerate(cex_cv.tolist()):
                er.append(cv_row[int(cv)]);ec.append(q);ev.append(1.0)
            for q,cv in enumerate(hcv.tolist()):
                er.append(cv_row[int(cv)]);ec.append(n_ex+q);ev.append(1.0)
            Aeq_base=sparse.coo_matrix(
                (np.asarray(ev),(np.asarray(er),np.asarray(ec))),
                shape=(ncv,nbase)
            ).tocsr()

            cell_row={int(c):r for r,c in enumerate(comp_cells.tolist())}
            cr=[];cc=[];vv=[]
            for q,c in enumerate(cex_cell.tolist()):
                cr.append(cell_row[int(c)]);cc.append(q);vv.append(1.0)
            for q,c in enumerate(hcell.tolist()):
                cr.append(cell_row[int(c)]);cc.append(n_ex+q);vv.append(1.0)
            Acell=sparse.coo_matrix(
                (np.asarray(vv),(np.asarray(cr),np.asarray(cc))),
                shape=(len(comp_cells),nbase)
            ).tocsr()
            Aub0=sparse.vstack([Acell,-Acell],format="csr")
            bub=np.r_[capacity[comp_cells]-fixed_mass[comp_cells],fixed_mass[comp_cells]]

            base_bounds=[]
            for cv,x0 in zip(cex_cv.tolist(),cex_x0.tolist()):
                if relax_sign_for_slack and int(cv) in slack_set:
                    base_bounds.append((None,None))
                elif x0>SIGN_TOL_KG:base_bounds.append((0.0,None))
                elif x0<-SIGN_TOL_KG:base_bounds.append((None,0.0))
                else:base_bounds.append((0.0,0.0))
            base_bounds.extend([(0.0,None)]*n_h)

            # Equality-slack diagnostic.
            nvar=nbase+2*ncv
            Aeq=sparse.hstack([Aeq_base,sparse.eye(ncv),-sparse.eye(ncv)],format="csr")
            Aub=sparse.hstack([Aub0,sparse.csr_matrix((Aub0.shape[0],2*ncv))],format="csr")
            bounds=base_bounds+[(0.0,None)]*(2*ncv)
            c=np.zeros(nvar);c[nbase:]=1.0
            t0=time.time()
            res=linprog(c,A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=cv_delta[comp_cvs],
                        bounds=bounds,method="highs",options={"presolve":True})
            elapsed=float(time.time()-t0)
            if not res.success:
                return {
                    "variant":name,"solver_success":False,"solver_status":int(res.status),
                    "solver_message":str(res.message),"edge_count":n_h,
                    "extra_edge_count":len(edges)-len(base_edges),
                    "relax_sign_for_baseline_slack_CVs":bool(relax_sign_for_slack),
                    "runtime_s":elapsed,
                }
            z=np.asarray(res.x)
            under=z[nbase:nbase+ncv];over=z[nbase+ncv:]
            abs_slack=under+over
            cell_mass=fixed_mass[comp_cells]+np.asarray(Acell@z[:nbase]).ravel()
            nz=abs_slack>SLACK_TOL_KG
            return {
                "variant":name,
                "solver_success":True,
                "solver_status":int(res.status),
                "solver_message":str(res.message),
                "edge_count":n_h,
                "extra_edge_count":len(edges)-len(base_edges),
                "relax_sign_for_baseline_slack_CVs":bool(relax_sign_for_slack),
                "minimum_total_CV_conservation_slack_kg":float(np.sum(abs_slack)),
                "maximum_single_CV_conservation_slack_kg":float(np.max(abs_slack)),
                "CVs_with_nonzero_conservation_slack":int(np.sum(nz)),
                "maximum_cell_lower_violation_kg":max(0.0,-float(np.min(cell_mass))),
                "maximum_cell_upper_violation_kg":max(0.0,float(np.max(cell_mass-capacity[comp_cells]))),
                "runtime_s":elapsed,
            }

        variants=[]
        # Re-run baseline as authority check.
        variants.append(solve_variant("V0_CURRENT_G2A",set(),False))
        gate("V0_success",variants[-1].get("solver_success") is True,variants[-1])
        gate("V0_baseline_slack_reproduced",
             abs(float(variants[-1]["minimum_total_CV_conservation_slack_kg"])-EXPECTED_BASELINE_SLACK)<=1e-6,
             variants[-1]["minimum_total_CV_conservation_slack_kg"])

        variants.append(solve_variant("V1_ZERO_H2_SLACK_CV_COMPONENT_FRONTIER_COMPLETION",v1_extra,False))
        gate("V1_success",variants[-1].get("solver_success") is True,variants[-1])

        variants.append(solve_variant("V2_ALL_SLACK_CV_COMPONENT_FRONTIER_COMPLETION",v2_extra,False))
        gate("V2_success",variants[-1].get("solver_success") is True,variants[-1])

        if float(variants[-1]["minimum_total_CV_conservation_slack_kg"])>SLACK_TOL_KG:
            variants.append(solve_variant(
                "V3_V2_PLUS_EXISTING_SIGN_RELAXATION_FOR_BASELINE_SLACK_CVS",
                v2_extra,True
            ))
            gate("V3_success",variants[-1].get("solver_success") is True,variants[-1])

        stage="classification_freeze"
        by={v["variant"]:v for v in variants}
        v0=float(by["V0_CURRENT_G2A"]["minimum_total_CV_conservation_slack_kg"])
        v1=float(by["V1_ZERO_H2_SLACK_CV_COMPONENT_FRONTIER_COMPLETION"]["minimum_total_CV_conservation_slack_kg"])
        v2=float(by["V2_ALL_SLACK_CV_COMPONENT_FRONTIER_COMPLETION"]["minimum_total_CV_conservation_slack_kg"])
        v3=(float(by["V3_V2_PLUS_EXISTING_SIGN_RELAXATION_FOR_BASELINE_SLACK_CVS"]["minimum_total_CV_conservation_slack_kg"])
            if "V3_V2_PLUS_EXISTING_SIGN_RELAXATION_FOR_BASELINE_SLACK_CVS" in by else None)

        if v1<=SLACK_TOL_KG:
            classification="FOURTEEN_ZERO_H2_EDGE_CVS_CONTROL_THE_NETWORK_CUT"
            next_name="Component-Frontier H2 Eligibility Prospective Repair Semantics Freeze"
            candidate_rule="component_frontier_completion_for_zero_H2_positive_delta_slack_CVs"
        elif v2<=SLACK_TOL_KG:
            classification="LOCAL_H2_EDGE_ELIGIBILITY_CONTROLS_THE_NETWORK_CUT"
            next_name="Component-Frontier H2 Eligibility Prospective Repair Semantics Freeze"
            candidate_rule="component_frontier_completion_for_all_baseline_slack_CVs"
        elif v3 is not None and v3<=SLACK_TOL_KG:
            classification="H2_EDGE_ELIGIBILITY_PLUS_EXISTING_SIGN_PRESERVATION_CONTROL_THE_NETWORK_CUT"
            next_name="Sign-Preservation and H2 Eligibility Physical Admissibility Design Audit"
            candidate_rule=None
        else:
            classification="NETWORK_CUT_PERSISTS_AFTER_COMPONENT_FRONTIER_ELIGIBILITY_SENSITIVITY"
            next_name="H2-XY Residual Network-Cut / Domain-Topology Design Audit"
            candidate_rule=None

        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R5_G2A_R2_R1_Final_Artifacts"
        if local.exists():shutil.rmtree(local)
        local.mkdir(parents=True)

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "blocked_R2_preserved":True,
            "technical_repair":"sorted_current_edges_plus_authoritative_slack_CV_component_signature",
            "deterministic_failed_component_index":int(deterministic_component_index),
            "reproduced_failed_component_CV_count":int(len(comp_cvs)),
            "reproduced_failed_component_cell_count":int(len(comp_cells_authority)),
            "reproduced_failed_component_existing_variable_count":int(len(ex_idx)),
            "reproduced_failed_component_H2_edge_count":int(len(base_edges)),
            "baseline_slack_kg":v0,
            "V1_slack_kg":v1,
            "V2_slack_kg":v2,
            "V3_slack_kg":v3,
            "baseline_slack_CV_count":EXPECTED_BASELINE_SLACK_CVS,
            "baseline_zero_H2_positive_delta_slack_CV_count":EXPECTED_ZERO_H2_SLACK_CVS,
            "V1_extra_edge_count":int(len(v1_extra)),
            "V2_extra_edge_count":int(len(v2_extra)),
            "classification":classification,
            "candidate_rule_if_any":candidate_rule,
            "repair_executed":False,
            "accepted_state_created":False,
            "H2_cell_domain_changed":False,
            "vertical_support_used":False,
            "P3_authorized":False,
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "classification":classification,
            "blocked_R2_preserved":True,
            "technical_component_identity_repair_closed":True,
            "P2_R5_G2A_R3_authorized":True,
            "P2_R5_G2A_R3_name":next_name,
            "prospective_component_frontier_H2_eligibility_design_authorized":classification in {
                "FOURTEEN_ZERO_H2_EDGE_CVS_CONTROL_THE_NETWORK_CUT",
                "LOCAL_H2_EDGE_ELIGIBILITY_CONTROLS_THE_NETWORK_CUT",
            },
            "sign_preservation_physical_admissibility_audit_authorized":
                classification=="H2_EDGE_ELIGIBILITY_PLUS_EXISTING_SIGN_PRESERVATION_CONTROL_THE_NETWORK_CUT",
            "residual_network_cut_domain_topology_audit_authorized":
                classification=="NETWORK_CUT_PERSISTS_AFTER_COMPONENT_FRONTIER_ELIGIBILITY_SENSITIVITY",
            "repair_execution_authorized":False,
            "further_support_expansion_execution_authorized":False,
            "physics_relaxation_authorized":False,
            "P3_authorized":False,
            "R3R6R1_execution_invalidated":False,
        }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_Sensitivity_Variants.csv").write_bytes(csv_bytes(variants))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({"file":str(p.relative_to(local)).replace("\\","/"),
                                 "sha256":sha256_file(p),"bytes":p.stat().st_size})
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists():raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*194)
        print("POSTV16-AV4-PIVOT-P2-R5-G2A-R2-R1: PASS")
        for v in variants:
            print(v["variant"])
            print("  extra edges                    :",v.get("extra_edge_count"))
            print("  total CV conservation slack kg :",v.get("minimum_total_CV_conservation_slack_kg"))
            print("  nonzero slack CVs              :",v.get("CVs_with_nonzero_conservation_slack"))
            print("  max lower/upper cell violation :",v.get("maximum_cell_lower_violation_kg"),"/",v.get("maximum_cell_upper_violation_kg"))
        print("Classification                  :",classification)
        print("NEXT                            :",next_name)
        print("Repair execution authorized     : False")
        print("Further support expansion       : False")
        print("P3 authorized                   : False")
        print("="*194)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_Blocked_Report.json"
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
