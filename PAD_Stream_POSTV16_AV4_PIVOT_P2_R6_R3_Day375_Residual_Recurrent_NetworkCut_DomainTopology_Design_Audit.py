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


MILESTONE="POSTV16-AV4-PIVOT-P2-R6-R3"
STATUS_PASS=(
    "AV4PIVOTP2R6R3_DAY375_RESIDUAL_RECURRENT_NETWORK_CUT_DOMAIN_TOPOLOGY_"
    "DESIGN_AUDIT_PASS_NO_REPAIR_EXECUTION"
)
STATUS_BLOCKED="AV4PIVOTP2R6R3_TECHNICAL_OR_AUTHORITY_BLOCK"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT="8ba8f31304440c571aca8f71318c23fd73403b94"
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
EXPECTED_BASELINE_SLACK=413.7364395997251
EXPECTED_SLACK_CVS=12
R2R1_CLASS="RECURRENT_NETWORK_CUT_PERSISTS_AFTER_FROZEN_DOMAIN_FRONTIER_SENSITIVITY"
R3_NAME="Day375 Residual Recurrent Network-Cut / Domain-Topology Design Audit"

CV_TOL_KG=1.0e-7
CELL_TOL_KG=1.0e-7
SIGN_TOL_KG=1.0e-10
SLACK_TOL_KG=1.0e-8

BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

R2R1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R2_R1_SameLayer_ComponentFrontier_Provenance_Gate_Closure_and_Sensitivity_Execution"
R2R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R2_R1_Summary.json"
R2R1_DECISION="POSTV16_AV4_PIVOT_P2_R6_R2_R1_Decision_Contract.json"
R2R1_VARIANTS="POSTV16_AV4_PIVOT_P2_R6_R2_R1_Sensitivity_Variants.csv"
R2R1_STATUS=(
    "AV4PIVOTP2R6R2R1_SAME_LAYER_COMPONENT_FRONTIER_PROVENANCE_GATE_"
    "CLOSURE_AND_DETERMINISTIC_SENSITIVITY_EXECUTION_PASS_NO_REPAIR_EXECUTION"
)

R1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R1_Day375_Component1_Infeasibility_Localization_Audit"
R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R1_Summary.json"
R1_CSV="POSTV16_AV4_PIVOT_P2_R6_R1_Component1_CV_Diagnostics.csv"

R4_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
R4_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Summary.json"
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

OUT_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R3_Day375_Residual_Recurrent_NetworkCut_DomainTopology_Audit"
BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R3_BLOCKED"

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
R2R1RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R2_R1_SameLayer_ComponentFrontier_Provenance_Gate_Closure_and_Deterministic_Sensitivity_Execution.py"
R2R1RUN_BLOB="a71733913278474b2742328bd1cb61351e11a47b"
R1RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R1_Day375_Component1_Infeasibility_Localization_and_RecurrentSupport_Audit.py"
R1RUN_BLOB="9196eca21a42323a47657362e353232b9c200419"
R4RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection_Execution.py"
R4RUN_BLOB="cdcade36343d314bc34063bce6e81e5c9c520294"

SOURCE_BLOBS={
    F4R3:F4R3_BLOB,
    A4R2:A4R2_BLOB,
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
    R2R1RUN:R2R1RUN_BLOB,
    R1RUN:R1RUN_BLOB,
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


def read_csv(path:Path)->list[dict[str,str]]:
    with path.open("r",encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f))


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


def ijk(flat:int)->tuple[int,int,int]:
    k=flat//(NY*NX);rem=flat%(NY*NX);j=rem//NX;i=rem%NX
    return k,j,i


def flat_of(k:int,j:int,i:int)->int:
    return k*(NY*NX)+j*NX+i


def h2xy_from_cells(cells:np.ndarray,s0_set:set[int])->set[int]:
    out:set[int]=set()
    for c in cells.tolist():
        k,j,i=ijk(int(c))
        for dj in range(-2,3):
            for di in range(-2,3):
                d=abs(di)+abs(dj)
                if not (1<=d<=2):continue
                jj=j+dj;ii=i+di
                if not (0<=jj<NY and 0<=ii<NX):continue
                h=flat_of(k,jj,ii)
                if h in s0_set:continue
                out.add(int(h))
    return out


def self_test()->None:
    assert R2R1_CLASS=="RECURRENT_NETWORK_CUT_PERSISTS_AFTER_FROZEN_DOMAIN_FRONTIER_SENSITIVITY"
    assert (EXPECTED_CV_COUNT,EXPECTED_CELL_COUNT,EXPECTED_EXISTING_VARIABLE_COUNT,EXPECTED_H2_EDGE_COUNT)==(78,60,101,421)
    assert EXPECTED_SLACK_CVS==12
    print("POSTV16 AV4 PIVOT P2-R6-R3 structural self-test: PASS")


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
    print("POSTV16-AV4-PIVOT-P2-R6-R3 -- DAY375 RESIDUAL RECURRENT NETWORK-CUT / DOMAIN-TOPOLOGY DESIGN AUDIT")
    print("="*194)
    print("AUDIT ONLY. NO REPAIR. NO NEW CELLS. NO PRESSURE REFRESH. NO P3.")
    print("DISTINGUISH SHARED TERMINAL-SINK CAPACITY COUPLING FROM VARIABLE-COMPONENT CONNECTIVITY.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R3_Summary.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R6_R3_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P2-R6-R3 audit PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_P2R6R3_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_R2R1_PASS_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,
             git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",
             repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="R2R1_PASS_binding"
        r2dir=drive/R2R1_REL
        r2s=load_json(r2dir/R2R1_SUMMARY)
        r2d=load_json(r2dir/R2R1_DECISION)
        r2v=read_csv(r2dir/R2R1_VARIANTS)
        gate("R2R1_status_exact",r2s.get("status")==R2R1_STATUS,r2s.get("status"))
        gate("R2R1_decision_status_exact",r2d.get("status")==R2R1_STATUS,r2d.get("status"))
        gate("R2R1_class_exact",r2s.get("classification")==R2R1_CLASS,r2s.get("classification"))
        gate("R2R1_R3_authorized",r2d.get("P2_R6_R3_authorized") is True,r2d.get("P2_R6_R3_authorized"))
        gate("R2R1_R3_name_exact",r2d.get("P2_R6_R3_name")==R3_NAME,r2d.get("P2_R6_R3_name"))
        gate("R2R1_repair_false",r2d.get("repair_execution_authorized") is False)
        gate("R2R1_new_cells_false",r2d.get("new_H2_cells_authorized") is False)
        gate("R2R1_pressure_false",r2d.get("pressure_refresh_authorized") is False)
        gate("R2R1_P3_false",r2d.get("P3_authorized") is False)
        gate("R2R1_V0_slack_exact",
             abs(float(r2s["V0_slack_kg"])-EXPECTED_BASELINE_SLACK)<=1e-6,r2s["V0_slack_kg"])
        gate("R2R1_full_merge_V1_expanded",
             int(next(r for r in r2v if r["variant"].startswith("V1_"))["augmented_component_CV_count"])>EXPECTED_CV_COUNT)
        gate("R2R1_full_merge_V2_expanded",
             int(next(r for r in r2v if r["variant"].startswith("V2_"))["augmented_component_CV_count"])>EXPECTED_CV_COUNT)

        stage="R1_and_R4_binding"
        r1dir=drive/R1_REL
        r1s=load_json(r1dir/R1_SUMMARY)
        r1rows=read_csv(r1dir/R1_CSV)
        gate("R1_baseline_slack_exact",
             abs(float(r1s["minimum_total_CV_conservation_slack_kg"])-EXPECTED_BASELINE_SLACK)<=1e-6)
        slack_cvs=np.asarray(sorted(
            int(r["cv_id"]) for r in r1rows
            if float(r["diagnostic_absolute_slack_kg"])>SLACK_TOL_KG
        ),dtype=np.int64)
        gate("R1_slack_CV_count_exact",len(slack_cvs)==EXPECTED_SLACK_CVS,len(slack_cvs))

        r4dir=drive/R4_REL
        r4s=load_json(r4dir/R4_SUMMARY)
        r4state_path=r4dir/R4_STATE
        gate("R4_status_exact",r4s.get("status")==R4_STATUS,r4s.get("status"))
        gate("R4_state_SHA_exact",sha256_file(r4state_path)==r4s.get("accepted_state_sha256"))
        with np.load(r4state_path,allow_pickle=False) as z:
            r4state={k:np.asarray(z[k]).copy() for k in z.files}

        old_cv_mass=np.asarray(r4state["cv_component_mass_kg"],dtype=np.float64)
        old_cv_sat=np.asarray(r4state["cv_saturation"],dtype=np.float64)
        old_grid_mass=np.asarray(r4state["grid_component_mass_kg"],dtype=np.float64)
        frozen_pair_cv=np.asarray(r4state["existing_pair_cv"],dtype=np.int64)
        frozen_pair_cell=np.asarray(r4state["existing_pair_cell"],dtype=np.int64)
        frozen_halo_cv=np.asarray(r4state["halo_cv"],dtype=np.int64)
        frozen_halo_cell=np.asarray(r4state["halo_cell"],dtype=np.int64)
        frozen_halo_domain=set(int(x) for x in np.unique(frozen_halo_cell).tolist())
        frozen_edge_set=set(
            (int(cv),int(h)) for cv,h in zip(frozen_halo_cv.tolist(),frozen_halo_cell.tolist())
        )

        stage="Day375_reconstruction"
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

        f4=load_module(root/F4R3,"p2r6r3_f4")
        a4=load_module(root/A4R2,"p2r6r3_a4")
        r2=load_module(root/R2SRC,"p2r6r3_r2")
        e37=load_module(root/E37A,"p2r6r3_e37")
        sg7d=load_module(root/SG7D,"p2r6r3_sg7d")

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
        gate("CV_pv_matches",float(np.max(np.abs(np.asarray(geometry["cv_pv_m3"])-parent_cv_pv)))<=1e-8)
        gate("CV_coeff_matches",relative_l2(np.asarray(geometry["cv_pressure_mass_coeff"]),parent_cv_coeff)<=1e-12)

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
        current_hcv=frozen_halo_cv[edge_mask]
        current_hcell=frozen_halo_cell[edge_mask]
        current_edges=set((int(cv),int(h)) for cv,h in zip(current_hcv.tolist(),current_hcell.tolist()))

        s0=np.unique(existing_cell).astype(np.int64)
        s0_set=set(int(x) for x in s0.tolist())
        cv_local0={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local0={int(c):n for n,c in enumerate(s0.tolist())}
        d0=DSU(len(union_culprit)+len(s0));off0=len(union_culprit)
        for cv,c in zip(existing_cv.tolist(),existing_cell.tolist()):
            d0.union(cv_local0[int(cv)],off0+cell_local0[int(c)])
        orig_root_of_cv={int(cv):d0.find(cv_local0[int(cv)]) for cv in union_culprit.tolist()}
        orig_root_of_cell={int(c):d0.find(off0+cell_local0[int(c)]) for c in s0.tolist()}

        frontier_by_root:dict[int,set[int]]={}
        for c in s0.tolist():
            rid=orig_root_of_cell[int(c)]
            geom=h2xy_from_cells(np.asarray([int(c)],dtype=np.int64),s0_set)
            frontier_by_root.setdefault(rid,set()).update(
                int(h) for h in geom if int(h) in frozen_halo_domain
            )

        all_cells=np.union1d(np.unique(existing_cell),np.unique(current_hcell)).astype(np.int64)
        cv_local={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local={int(c):n for n,c in enumerate(all_cells.tolist())}
        dsu=DSU(len(union_culprit)+len(all_cells));off=len(union_culprit)
        for cv,c in zip(existing_cv.tolist(),existing_cell.tolist()):
            dsu.union(cv_local[int(cv)],off+cell_local[int(c)])
        for cv,h in sorted(current_edges):
            dsu.union(cv_local[int(cv)],off+cell_local[int(h)])

        roots=sorted({dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()})
        slack_roots=sorted({dsu.find(cv_local[int(cv)]) for cv in slack_cvs.tolist()})
        gate("all_R1_slack_CVs_share_one_failed_component",len(slack_roots)==1,slack_roots)
        failed_root=slack_roots[0]
        gate("failed_component_index_reproduced",int(roots.index(failed_root))==FAILED_COMPONENT_ID,
             int(roots.index(failed_root)))
        baseline_comp_cvs=np.asarray(
            [cv for cv in union_culprit.tolist() if dsu.find(cv_local[int(cv)])==failed_root],
            dtype=np.int64
        )
        baseline_comp_set=set(int(x) for x in baseline_comp_cvs.tolist())
        baseline_ex_idx=np.flatnonzero(np.asarray(
            [int(cv) in baseline_comp_set for cv in var_ex_cv],dtype=bool
        ))
        baseline_edges=sorted((cv,h) for cv,h in current_edges if cv in baseline_comp_set)
        baseline_hcells=np.asarray([h for _,h in baseline_edges],dtype=np.int64)
        baseline_cells=np.unique(np.r_[var_ex_cell[baseline_ex_idx],baseline_hcells]).astype(np.int64)

        gate("baseline_failed_CV_count_exact",len(baseline_comp_cvs)==EXPECTED_CV_COUNT,len(baseline_comp_cvs))
        gate("baseline_failed_cell_count_exact",len(baseline_cells)==EXPECTED_CELL_COUNT,len(baseline_cells))
        gate("baseline_existing_variable_count_exact",
             len(baseline_ex_idx)==EXPECTED_EXISTING_VARIABLE_COUNT,len(baseline_ex_idx))
        gate("baseline_H2_edge_count_exact",len(baseline_edges)==EXPECTED_H2_EDGE_COUNT,len(baseline_edges))

        stage="candidate_reconstruction_and_bridge_topology"
        def completion_edges(target_cvs:np.ndarray)->set[tuple[int,int]]:
            result:set[tuple[int,int]]=set()
            for cv in target_cvs.tolist():
                rid=orig_root_of_cv[int(cv)]
                for h in frontier_by_root.get(rid,set()):
                    e=(int(cv),int(h))
                    if e not in frozen_edge_set:
                        result.add(e)
            return result

        v1_extra=completion_edges(slack_cvs)
        v2_extra=completion_edges(baseline_comp_cvs)

        # Current baseline component id for every culprit CV.
        baseline_component_of_cv={int(cv):int(dsu.find(cv_local[int(cv)])) for cv in union_culprit.tolist()}
        failed_baseline_component=int(failed_root)

        # Which current baseline CV components already touch each halo sink via current frozen edges?
        current_components_by_halo:dict[int,set[int]]={}
        current_cvs_by_halo:dict[int,set[int]]={}
        for cv,h in current_edges:
            current_components_by_halo.setdefault(int(h),set()).add(baseline_component_of_cv[int(cv)])
            current_cvs_by_halo.setdefault(int(h),set()).add(int(cv))

        def bridge_audit(name:str,extra:set[tuple[int,int]])->dict[str,Any]:
            shared_edges=[]
            external_components:set[int]=set()
            external_cvs:set[int]=set()
            shared_cells:set[int]=set()
            for cv,h in sorted(extra):
                comps=current_components_by_halo.get(int(h),set())
                ext={c for c in comps if c!=failed_baseline_component}
                if ext:
                    shared_edges.append((int(cv),int(h),len(ext)))
                    shared_cells.add(int(h))
                    external_components.update(ext)
                    for other_cv in current_cvs_by_halo.get(int(h),set()):
                        if baseline_component_of_cv[int(other_cv)]!=failed_baseline_component:
                            external_cvs.add(int(other_cv))

            # Full augmented DSU for topology only.
            augmented_edges=set(current_edges)|set(extra)
            variant_cells=np.union1d(
                np.unique(existing_cell),
                np.asarray(sorted({h for _,h in augmented_edges}),dtype=np.int64)
                if augmented_edges else np.asarray([],dtype=np.int64)
            ).astype(np.int64)
            vcell_local={int(c):n for n,c in enumerate(variant_cells.tolist())}
            vdsu=DSU(len(union_culprit)+len(variant_cells));voff=len(union_culprit)
            for cv,c in zip(existing_cv.tolist(),existing_cell.tolist()):
                vdsu.union(cv_local[int(cv)],voff+vcell_local[int(c)])
            for cv,h in sorted(augmented_edges):
                vdsu.union(cv_local[int(cv)],voff+vcell_local[int(h)])
            target_roots=sorted({vdsu.find(cv_local[int(cv)]) for cv in baseline_comp_cvs.tolist()})
            gate(name+"_baseline_component_not_split",len(target_roots)==1,target_roots)
            rr=target_roots[0]
            merged_cvs=np.asarray(
                [cv for cv in union_culprit.tolist() if vdsu.find(cv_local[int(cv)])==rr],
                dtype=np.int64
            )
            return {
                "variant":name,
                "extra_edge_count":int(len(extra)),
                "extra_unique_cell_count":int(len({h for _,h in extra})),
                "bridge_edge_count":int(len(shared_edges)),
                "bridge_unique_sink_cell_count":int(len(shared_cells)),
                "external_baseline_component_count_touched_directly":int(len(external_components)),
                "external_current_CV_count_touched_directly":int(len(external_cvs)),
                "full_augmented_component_CV_count":int(len(merged_cvs)),
                "full_augmented_external_CV_count":int(len(merged_cvs)-len(baseline_comp_cvs)),
            }

        bridge_v1=bridge_audit("V1",v1_extra)
        bridge_v2=bridge_audit("V2",v2_extra)

        stage="terminal_sink_fixed_external_occupancy_sensitivity"
        try:
            from scipy.optimize import linprog
            from scipy import sparse
            import scipy
        except Exception as exc:
            raise GateError("scipy_HiGHS_unavailable:"+repr(exc)) from exc
        print("SciPy version:",scipy.__version__)

        cex_cv=var_ex_cv[baseline_ex_idx]
        cex_cell=var_ex_cell[baseline_ex_idx]
        cex_x0=var_ex_x0[baseline_ex_idx]
        n_ex=len(baseline_ex_idx)
        cv_row={int(cv):r for r,cv in enumerate(baseline_comp_cvs.tolist())}
        baseline_comp_mask=np.zeros(NSL*NCV,dtype=bool);baseline_comp_mask[baseline_comp_cvs]=True

        # All Day375 direct-mapback contributions outside the original 78-CV component are fixed.
        # Shared sink capacity still includes those external fixed contributions.
        variable_existing_local=baseline_comp_mask[pair_cv]&(np.abs(pair_val)>SIGN_TOL_KG)
        fixed_delta_local=np.bincount(
            pair_cell[~variable_existing_local],
            weights=pair_val[~variable_existing_local],
            minlength=NCELL,
        )
        fixed_mass_local=old_grid_mass.reshape(-1)+fixed_delta_local

        baseline_comp_set_frozen=set(int(x) for x in baseline_comp_cvs.tolist())

        def solve_local_terminal_sink(
            name:str,
            extra:set[tuple[int,int]],
            relax_sign:bool,
        )->dict[str,Any]:
            edges=sorted(set(baseline_edges)|set(extra))
            hcv=np.asarray([cv for cv,_ in edges],dtype=np.int64)
            hcell=np.asarray([h for _,h in edges],dtype=np.int64)
            comp_cells=np.unique(np.r_[cex_cell,hcell]).astype(np.int64)
            n_h=len(edges);ncv=len(baseline_comp_cvs);nbase=n_ex+n_h

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
            bub=np.r_[capacity[comp_cells]-fixed_mass_local[comp_cells],
                      fixed_mass_local[comp_cells]]

            base_bounds=[]
            relaxed_count=0
            for cv,x0 in zip(cex_cv.tolist(),cex_x0.tolist()):
                if relax_sign and int(cv) in baseline_comp_set_frozen:
                    base_bounds.append((None,None));relaxed_count+=1
                elif x0>SIGN_TOL_KG:base_bounds.append((0.0,None))
                elif x0<-SIGN_TOL_KG:base_bounds.append((None,0.0))
                else:base_bounds.append((0.0,0.0))
            base_bounds.extend([(0.0,None)]*n_h)

            nvar=nbase+2*ncv
            Aeq=sparse.hstack(
                [Aeq_base,sparse.eye(ncv,format="csr"),-sparse.eye(ncv,format="csr")],
                format="csr"
            )
            Aub=sparse.hstack(
                [Aub0,sparse.csr_matrix((Aub0.shape[0],2*ncv))],
                format="csr"
            )
            bounds=base_bounds+[(0.0,None)]*(2*ncv)
            c=np.zeros(nvar,dtype=np.float64);c[nbase:]=1.0
            t0=time.time()
            res=linprog(
                c,A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=cv_delta[baseline_comp_cvs],
                bounds=bounds,method="highs",options={"presolve":True}
            )
            elapsed=float(time.time()-t0)
            gate(name+"_diagnostic_solver_success",res.success,
                 {"status":int(res.status),"message":str(res.message)})
            z=np.asarray(res.x,dtype=np.float64)
            splus=z[nbase:nbase+ncv];sminus=z[nbase+ncv:nbase+2*ncv]
            abs_slack=splus+sminus
            nz=abs_slack>SLACK_TOL_KG
            cell_mass=fixed_mass_local[comp_cells]+np.asarray(Acell@z[:nbase]).ravel()

            shared_candidate_cells={h for _,h in extra if h in current_components_by_halo}
            fixed_external_mass_on_shared_cells=float(np.sum(
                fixed_mass_local[np.asarray(sorted(shared_candidate_cells),dtype=np.int64)]
            )) if shared_candidate_cells else 0.0

            return {
                "variant":name,
                "solver_success":True,
                "local_component_CV_count":int(len(baseline_comp_cvs)),
                "local_component_cell_count":int(len(comp_cells)),
                "existing_variable_count":int(n_ex),
                "H2_edge_count":int(n_h),
                "extra_edge_count":int(len(set(edges)-set(baseline_edges))),
                "extra_unique_cell_count":int(len({h for _,h in extra})),
                "shared_candidate_sink_cell_count":int(len(shared_candidate_cells)),
                "fixed_external_mass_on_shared_candidate_cells_kg":fixed_external_mass_on_shared_cells,
                "relaxed_existing_variable_count":int(relaxed_count),
                "minimum_total_CV_conservation_slack_kg":float(np.sum(abs_slack)),
                "maximum_single_CV_conservation_slack_kg":float(np.max(abs_slack)) if len(abs_slack) else 0.0,
                "CVs_with_nonzero_conservation_slack":int(np.sum(nz)),
                "maximum_cell_lower_violation_kg":max(0.0,-float(np.min(cell_mass))),
                "maximum_cell_upper_violation_kg":max(0.0,float(np.max(cell_mass-capacity[comp_cells]))),
                "runtime_s":elapsed,
            }

        local_v0=solve_local_terminal_sink("L0_BASELINE_78_FIXED_EXTERNAL",set(),False)
        gate("L0_reproduces_R1_baseline_slack",
             abs(float(local_v0["minimum_total_CV_conservation_slack_kg"])-EXPECTED_BASELINE_SLACK)<=1e-6,
             local_v0["minimum_total_CV_conservation_slack_kg"])

        local_v1=solve_local_terminal_sink(
            "L1_12_SLACK_CV_FRONTIER_FIXED_EXTERNAL_TERMINAL_SINK",
            v1_extra,False
        )
        local_v2=None
        local_v3=None
        if float(local_v1["minimum_total_CV_conservation_slack_kg"])>SLACK_TOL_KG:
            local_v2=solve_local_terminal_sink(
                "L2_ALL_78_FRONTIER_FIXED_EXTERNAL_TERMINAL_SINK",
                v2_extra,False
            )
            if float(local_v2["minimum_total_CV_conservation_slack_kg"])>SLACK_TOL_KG:
                local_v3=solve_local_terminal_sink(
                    "L3_L2_PLUS_SIGN_RELAXATION_FIXED_EXTERNAL_TERMINAL_SINK",
                    v2_extra,True
                )

        stage="classification_freeze"
        l1=float(local_v1["minimum_total_CV_conservation_slack_kg"])
        l2=(float(local_v2["minimum_total_CV_conservation_slack_kg"]) if local_v2 is not None else None)
        l3=(float(local_v3["minimum_total_CV_conservation_slack_kg"]) if local_v3 is not None else None)

        if l1<=SLACK_TOL_KG:
            classification="SHARED_TERMINAL_SINK_VARIABLE_CONNECTIVITY_OVERCOUPLES_RECURRENCE_AND_12_CV_LOCAL_ELIGIBILITY_IS_SUFFICIENT"
            next_name="Day375 Terminal-Sink Fixed-External Recurrent Eligibility Prospective Repair Semantics Freeze"
            candidate_rule="12_Day375_slack_CVs_component_frontier_with_external_components_fixed"
        elif l2 is not None and l2<=SLACK_TOL_KG:
            classification="SHARED_TERMINAL_SINK_VARIABLE_CONNECTIVITY_OVERCOUPLES_RECURRENCE_AND_78_CV_LOCAL_ELIGIBILITY_IS_SUFFICIENT"
            next_name="Day375 Terminal-Sink Fixed-External Recurrent Eligibility Prospective Repair Semantics Freeze"
            candidate_rule="all_78_failed_component_CVs_component_frontier_with_external_components_fixed"
        elif l3 is not None and l3<=SLACK_TOL_KG:
            classification="LOCAL_FIXED_EXTERNAL_ELIGIBILITY_PLUS_SIGN_PRESERVATION_CONTROLS_RECURRENCE"
            next_name="Day375 Terminal-Sink Fixed-External Sign-Preservation Physical-Admissibility Audit"
            candidate_rule=None
        else:
            classification="RESIDUAL_NETWORK_CUT_PERSISTS_UNDER_TERMINAL_SINK_FIXED_EXTERNAL_SEMANTICS"
            next_name="Day375 Frozen-H2 Spatial-Domain Sufficiency / Topology Extension Design Audit"
            candidate_rule=None

        topology_rows=[bridge_v1,bridge_v2]
        local_rows=[local_v0,local_v1]
        if local_v2 is not None:local_rows.append(local_v2)
        if local_v3 is not None:local_rows.append(local_v3)

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "audit_only":True,
            "repair_executed":False,
            "accepted_state_created":False,
            "R2R1_full_merge_classification":R2R1_CLASS,
            "baseline_failed_component_CV_count":int(len(baseline_comp_cvs)),
            "baseline_failed_component_cell_count":int(len(baseline_cells)),
            "baseline_existing_variable_count":int(len(baseline_ex_idx)),
            "baseline_H2_edge_count":int(len(baseline_edges)),
            "V1_bridge_edge_count":int(bridge_v1["bridge_edge_count"]),
            "V1_bridge_unique_sink_cell_count":int(bridge_v1["bridge_unique_sink_cell_count"]),
            "V1_external_baseline_components_touched":int(bridge_v1["external_baseline_component_count_touched_directly"]),
            "V1_full_augmented_component_CV_count":int(bridge_v1["full_augmented_component_CV_count"]),
            "V2_bridge_edge_count":int(bridge_v2["bridge_edge_count"]),
            "V2_bridge_unique_sink_cell_count":int(bridge_v2["bridge_unique_sink_cell_count"]),
            "V2_external_baseline_components_touched":int(bridge_v2["external_baseline_component_count_touched_directly"]),
            "V2_full_augmented_component_CV_count":int(bridge_v2["full_augmented_component_CV_count"]),
            "L0_slack_kg":float(local_v0["minimum_total_CV_conservation_slack_kg"]),
            "L1_slack_kg":l1,
            "L2_slack_kg":l2,
            "L3_slack_kg":l3,
            "classification":classification,
            "candidate_rule_if_any":candidate_rule,
            "H2_cell_domain_changed":False,
            "new_H2_cell_count":0,
            "vertical_support_used":False,
            "pressure_refresh_executed":False,
            "halo_transit_executed":False,
            "P3_authorized":False,
        }

        design={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "audit_question":"Does shared terminal-sink capacity require variable-component merging, or can external occupancy remain fixed while local failed-component eligibility is tested?",
            "frozen_parent_semantics":{
                "halo_transit":False,
                "nonculprit_existing_pairs_unchanged":True,
                "completion_edges_nonnegative_terminal_deposition_only":True,
            },
            "local_terminal_sink_diagnostic_semantics":{
                "variable_existing_pairs":"original 78-CV failed component only",
                "external_existing_pair_contributions":"fixed at Day375 direct-mapback values",
                "external_H2_variables":"fixed at zero for this local diagnostic",
                "shared_sink_capacity":"full physical cell capacity with external fixed occupancy included",
                "new_cartesian_cells":False,
                "pressure_refresh":False,
            },
        }

        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "classification":classification,
            "P2_R6_R4_authorized":True,
            "P2_R6_R4_name":next_name,
            "prospective_candidate_rule":candidate_rule,
            "terminal_sink_fixed_external_recurrent_eligibility_design_authorized":
                classification in {
                    "SHARED_TERMINAL_SINK_VARIABLE_CONNECTIVITY_OVERCOUPLES_RECURRENCE_AND_12_CV_LOCAL_ELIGIBILITY_IS_SUFFICIENT",
                    "SHARED_TERMINAL_SINK_VARIABLE_CONNECTIVITY_OVERCOUPLES_RECURRENCE_AND_78_CV_LOCAL_ELIGIBILITY_IS_SUFFICIENT",
                },
            "sign_preservation_physical_admissibility_audit_authorized":
                classification=="LOCAL_FIXED_EXTERNAL_ELIGIBILITY_PLUS_SIGN_PRESERVATION_CONTROLS_RECURRENCE",
            "frozen_H2_spatial_domain_sufficiency_audit_authorized":
                classification=="RESIDUAL_NETWORK_CUT_PERSISTS_UNDER_TERMINAL_SINK_FIXED_EXTERNAL_SEMANTICS",
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

        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R6_R3_Final_Artifacts"
        if local.exists():shutil.rmtree(local)
        local.mkdir(parents=True)

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R3_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R6_R3_Design_Contract.json").write_bytes(json_bytes(design))
        (local/"POSTV16_AV4_PIVOT_P2_R6_R3_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R6_R3_Bridge_Topology_Audit.csv").write_bytes(csv_bytes(topology_rows))
        (local/"POSTV16_AV4_PIVOT_P2_R6_R3_TerminalSink_Local_Sensitivity.csv").write_bytes(csv_bytes(local_rows))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R6_R3_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists():raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*194)
        print("POSTV16-AV4-PIVOT-P2-R6-R3: PASS")
        print("V1 bridge edges / shared sinks / full CVs :",bridge_v1["bridge_edge_count"],"/",bridge_v1["bridge_unique_sink_cell_count"],"/",bridge_v1["full_augmented_component_CV_count"])
        print("V2 bridge edges / shared sinks / full CVs :",bridge_v2["bridge_edge_count"],"/",bridge_v2["bridge_unique_sink_cell_count"],"/",bridge_v2["full_augmented_component_CV_count"])
        for r in local_rows:
            print(r["variant"],"slack kg =",r["minimum_total_CV_conservation_slack_kg"],
                  "nonzero CVs =",r["CVs_with_nonzero_conservation_slack"])
        print("Classification                              :",classification)
        print("Candidate rule                               :",candidate_rule)
        print("P2-R6-R4 authorized                          : True")
        print("Repair / new cells / P3                      : False / False / False")
        print("="*194)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R6_R3_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "automatic_rerun_authorized":False,
                "repair_execution_authorized":False,
                "support_growth_execution_authorized":False,
                "new_H2_cells_authorized":False,
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
