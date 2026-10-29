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


MILESTONE="POSTV16-AV4-PIVOT-P2-R6-R2"
STATUS_PASS=(
    "AV4PIVOTP2R6R2_DAY375_RECURRENT_FROZEN_GRAPH_ELIGIBILITY_AND_"
    "NETWORK_CUT_SENSITIVITY_DESIGN_FREEZE_PASS_NO_REPAIR_EXECUTION"
)
STATUS_BLOCKED="AV4PIVOTP2R6R2_TECHNICAL_OR_AUTHORITY_BLOCK"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT="4f9f384b1c917dd86709e61cf1497ebdb8fb6675"
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
EXPECTED_COMPLETION_EDGE_COUNT=0
EXPECTED_CVS_IN_R4_TARGET=0
EXPECTED_CVS_OUTSIDE_R4_TARGET=78
EXPECTED_ZERO_H2_COMPONENT_CVS=37
EXPECTED_INDIVIDUAL_IMPOSSIBLE_CVS=0
EXPECTED_BASELINE_SLACK=413.7364395997251
EXPECTED_MAX_SINGLE_SLACK=183.5146621445931
EXPECTED_SLACK_CVS=12
EXPECTED_SLACK_OUTSIDE_R4=12
EXPECTED_ZERO_H2_SLACK_CVS=12
R1_CLASS="NETWORK_CUT_OBSTRUCTION_UNDER_FROZEN_R4_RECURRENT_ELIGIBILITY"

CV_TOL_KG=1.0e-7
CELL_TOL_KG=1.0e-7
SIGN_TOL_KG=1.0e-10
SLACK_TOL_KG=1.0e-8

BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

R1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R1_Day375_Component1_Infeasibility_Localization_Audit"
R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R1_Summary.json"
R1_DECISION="POSTV16_AV4_PIVOT_P2_R6_R1_Decision_Contract.json"
R1_CSV="POSTV16_AV4_PIVOT_P2_R6_R1_Component1_CV_Diagnostics.csv"
R1_STATUS=(
    "AV4PIVOTP2R6R1_DAY375_COMPONENT1_STAGE1_INFEASIBILITY_LOCALIZATION_"
    "AND_RECURRENT_SUPPORT_SUFFICIENCY_AUDIT_PASS_NO_REPAIR_EXECUTION"
)
R2_NAME="Day375 Recurrent Frozen-Graph Eligibility and Network-Cut Sensitivity Design Freeze"

P2R6_FAIL_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_SCIENTIFIC_FAIL"
P2R6_FAIL_REPORT="POSTV16_AV4_PIVOT_P2_R6_Scientific_Fail_Report.json"
P2R6_FAIL_STATUS=(
    "AV4PIVOTP2R6_FROZEN_FLOW_CONTINUATION_SCIENTIFIC_FAIL_"
    "NO_SUPPORT_GROWTH_NO_PRESSURE_REFRESH_NO_AUTOMATIC_RERUN"
)

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

OUT_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R2_Day375_Recurrent_FrozenGraph_Eligibility_NetworkCut_Sensitivity_Freeze"
BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R2_BLOCKED"

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
    P2R6RUN:P2R6RUN_BLOB,
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
    c=flat_of(5,20,20)
    h=h2xy_from_cells(np.asarray([c],dtype=np.int64),{c})
    assert len(h)==12
    assert all(ijk(x)[0]==5 for x in h)
    assert (EXPECTED_CV_COUNT,EXPECTED_SLACK_CVS,EXPECTED_ZERO_H2_SLACK_CVS)==(78,12,12)
    print("POSTV16 AV4 PIVOT P2-R6-R2 structural self-test: PASS")


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
    print("POSTV16-AV4-PIVOT-P2-R6-R2 -- DAY375 RECURRENT FROZEN-GRAPH ELIGIBILITY / NETWORK-CUT SENSITIVITY DESIGN FREEZE")
    print("="*194)
    print("READ-ONLY SENSITIVITY. NO REPAIR. NO ACCEPTED STATE. NO NEW H2 CELLS. NO VERTICAL SUPPORT. NO PRESSURE REFRESH. NO P3.")
    print("V0 CURRENT GRAPH -> V1 12 SLACK-CV FRONTIERS -> V2 ALL 78 FAILED-COMPONENT CV FRONTIERS IF NEEDED -> V3 SIGN AUDIT IF NEEDED.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R2_Summary.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R6_R2_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P2-R6-R2 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_P2R6R2_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_R1_PASS_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,
             git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",
             repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="R1_PASS_binding"
        r1dir=drive/R1_REL
        r1s=load_json(r1dir/R1_SUMMARY)
        r1d=load_json(r1dir/R1_DECISION)
        r1rows=read_csv(r1dir/R1_CSV)

        gate("R1_status_exact",r1s.get("status")==R1_STATUS,r1s.get("status"))
        gate("R1_decision_status_exact",r1d.get("status")==R1_STATUS,r1d.get("status"))
        gate("R1_class_exact",r1s.get("classification")==R1_CLASS,r1s.get("classification"))
        gate("R1_R2_authorized",r1d.get("P2_R6_R2_authorized") is True,r1d.get("P2_R6_R2_authorized"))
        gate("R1_R2_name_exact",r1d.get("P2_R6_R2_name")==R2_NAME,r1d.get("P2_R6_R2_name"))
        gate("R1_repair_false",r1d.get("repair_execution_authorized") is False)
        gate("R1_support_growth_false",r1d.get("support_growth_execution_authorized") is False)
        gate("R1_new_H2_cells_false",r1d.get("new_H2_cells_authorized") is False)
        gate("R1_vertical_false",r1d.get("vertical_support_authorized") is False)
        gate("R1_pressure_refresh_false",r1d.get("pressure_refresh_authorized") is False)
        gate("R1_P3_false",r1d.get("P3_authorized") is False)

        expected_sequence=[
            "V0_reproduce_current_frozen_R4_component1_minimum_conservation_slack",
            "V1_current_Day375_slack_CVs_component_frontier_completion_within_existing_frozen_H2_cell_domain_only",
            "V2_all_Day375_component1_CVs_component_frontier_completion_within_existing_frozen_H2_cell_domain_only_if_V1_nonzero",
            "V3_existing_sign_rule_physical_admissibility_audit_only_if_V2_nonzero",
        ]
        gate("R1_sensitivity_sequence_exact",
             r1d.get("recommended_sensitivity_sequence")==expected_sequence,
             r1d.get("recommended_sensitivity_sequence"))

        scalar_checks={
            "Day375_component_CV_count":EXPECTED_CV_COUNT,
            "Day375_component_cell_count":EXPECTED_CELL_COUNT,
            "Day375_component_existing_variable_count":EXPECTED_EXISTING_VARIABLE_COUNT,
            "Day375_component_H2_edge_count":EXPECTED_H2_EDGE_COUNT,
            "Day375_component_completion_edge_count":EXPECTED_COMPLETION_EDGE_COUNT,
            "Day375_component_CVs_in_R4_target_set":EXPECTED_CVS_IN_R4_TARGET,
            "Day375_component_CVs_outside_R4_target_set":EXPECTED_CVS_OUTSIDE_R4_TARGET,
            "Day375_component_CVs_with_zero_H2_edges":EXPECTED_ZERO_H2_COMPONENT_CVS,
            "individual_sign_or_reachability_impossible_CV_count":EXPECTED_INDIVIDUAL_IMPOSSIBLE_CVS,
            "CVs_with_nonzero_conservation_slack":EXPECTED_SLACK_CVS,
            "slack_CVs_outside_R4_target_set":EXPECTED_SLACK_OUTSIDE_R4,
            "slack_CVs_with_zero_H2_edges":EXPECTED_ZERO_H2_SLACK_CVS,
        }
        for k,v in scalar_checks.items():
            gate("R1_"+k+"_exact",int(r1s.get(k,-1))==v,r1s.get(k))
        gate("R1_baseline_slack_exact",
             abs(float(r1s["minimum_total_CV_conservation_slack_kg"])-EXPECTED_BASELINE_SLACK)<=1e-6,
             r1s["minimum_total_CV_conservation_slack_kg"])
        gate("R1_max_single_slack_exact",
             abs(float(r1s["maximum_single_CV_conservation_slack_kg"])-EXPECTED_MAX_SINGLE_SLACK)<=1e-6,
             r1s["maximum_single_CV_conservation_slack_kg"])
        gate("R1_cell_lower_clean",float(r1s["maximum_cell_lower_violation_kg"])<=CELL_TOL_KG)
        gate("R1_cell_upper_clean",float(r1s["maximum_cell_upper_violation_kg"])<=CELL_TOL_KG)

        def truth(v:str)->bool:
            return str(v).strip().lower()=="true"
        def fval(v:str)->float:
            return float(v)

        slack_rows=[
            r for r in r1rows
            if fval(r["diagnostic_absolute_slack_kg"])>SLACK_TOL_KG
        ]
        slack_cvs=np.asarray(sorted(int(r["cv_id"]) for r in slack_rows),dtype=np.int64)
        zero_h2_slack_cvs=np.asarray(sorted(
            int(r["cv_id"]) for r in slack_rows if int(float(r["frozen_H2_edge_count"]))==0
        ),dtype=np.int64)
        gate("R1_slack_CV_count_from_CSV",len(slack_cvs)==EXPECTED_SLACK_CVS,len(slack_cvs))
        gate("R1_zero_H2_slack_CV_count_from_CSV",
             len(zero_h2_slack_cvs)==EXPECTED_ZERO_H2_SLACK_CVS,len(zero_h2_slack_cvs))
        gate("R1_all_slack_CVs_outside_R4_target",
             all(not truth(r["in_R4_327_target_set"]) for r in slack_rows))
        gate("R1_all_slack_CVs_upper_culprits",
             all(truth(r["is_Day375_upper_culprit"]) for r in slack_rows))
        gate("R1_no_individual_impossible_CVs",
             all(not truth(r["individual_reachability_impossible"]) for r in r1rows))

        stage="P2R6_FAIL_and_R4_binding"
        p2fail=load_json(drive/P2R6_FAIL_REL/P2R6_FAIL_REPORT)
        gate("P2R6_fail_status_exact",p2fail.get("status")==P2R6_FAIL_STATUS,p2fail.get("status"))
        gate("P2R6_fail_gate_exact",p2fail.get("failed_gate")=="Day375_component_1_stage1_infeasible",
             p2fail.get("failed_gate"))

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
        frozen_halo_is_completion=np.asarray(r4state["halo_is_completion"],dtype=bool)
        frozen_halo_domain=set(int(x) for x in np.unique(frozen_halo_cell).tolist())
        frozen_edge_set=set(
            (int(cv),int(h)) for cv,h in zip(frozen_halo_cv.tolist(),frozen_halo_cell.tolist())
        )

        stage="Day375_reconstruction"
        f2path=drive/F2R3_REL/F2R3_STATE
        x13path=drive/E1R2_REL/E1R2_X13
        a2path=drive/A2E_REL/A2E_EPOCH
        a2sum=drive/A2E_REL/A2E_SUMMARY
        gate("F2R3_present",f2path.is_file(),str(f2path))
        gate("X13_present",x13path.is_file(),str(x13path))
        gate("A2E_epoch_present",a2path.is_file(),str(a2path))
        gate("A2E_summary_present",a2sum.is_file(),str(a2sum))
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

        f4=load_module(root/F4R3,"p2r6r2_f4")
        a4=load_module(root/A4R2,"p2r6r2_a4")
        r2=load_module(root/R2SRC,"p2r6r2_r2")
        e37=load_module(root/E37A,"p2r6r2_e37")
        sg7d=load_module(root/SG7D,"p2r6r2_sg7d")

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
        current_hcomp=frozen_halo_is_completion[edge_mask]
        current_edges=set((int(cv),int(h)) for cv,h in zip(current_hcv.tolist(),current_hcell.tolist()))

        # Original two-sided S0 components BEFORE H2-induced merging.
        s0=np.unique(existing_cell).astype(np.int64)
        s0_set=set(int(x) for x in s0.tolist())
        cv_local0={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local0={int(c):n for n,c in enumerate(s0.tolist())}
        d0=DSU(len(union_culprit)+len(s0));off0=len(union_culprit)
        for cv,c in zip(existing_cv.tolist(),existing_cell.tolist()):
            d0.union(cv_local0[int(cv)],off0+cell_local0[int(c)])
        orig_root_of_cv={int(cv):d0.find(cv_local0[int(cv)]) for cv in union_culprit.tolist()}
        orig_root_of_cell={int(c):d0.find(off0+cell_local0[int(c)]) for c in s0.tolist()}

        # Component-frontier cells are generated geometrically, but can ONLY use cells
        # already present in the globally frozen R4 H2 cell domain.
        frontier_by_root:dict[int,set[int]]={}
        for c in s0.tolist():
            rid=orig_root_of_cell[int(c)]
            geom=h2xy_from_cells(np.asarray([int(c)],dtype=np.int64),s0_set)
            frontier_by_root.setdefault(rid,set()).update(
                int(h) for h in geom if int(h) in frozen_halo_domain
            )

        # Reconstruct current graph and identify failed component by R1 slack-CV signature.
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
        deterministic_component_index=int(roots.index(failed_root))
        gate("failed_component_index_reproduced",deterministic_component_index==FAILED_COMPONENT_ID,
             deterministic_component_index)

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
        gate("all_slack_CVs_in_baseline_failed_component",
             all(int(cv) in baseline_comp_set for cv in slack_cvs.tolist()))
        gate("all_zero_H2_slack_CVs_in_baseline_failed_component",
             all(int(cv) in baseline_comp_set for cv in zero_h2_slack_cvs.tolist()))

        stage="candidate_edge_construction"
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

        gate("V1_no_new_H2_cells",
             all(int(h) in frozen_halo_domain for _,h in v1_extra),len(v1_extra))
        gate("V2_no_new_H2_cells",
             all(int(h) in frozen_halo_domain for _,h in v2_extra),len(v2_extra))
        gate("V1_no_vertical_edges",
             all(ijk(int(h))[0]==ijk(int(c))[0]
                 for cv,h in v1_extra
                 for c in existing_cell[existing_cv==int(cv)].tolist()),True)
        gate("V2_no_vertical_edges",
             all(ijk(int(h))[0]==ijk(int(c))[0]
                 for cv,h in v2_extra
                 for c in existing_cell[existing_cv==int(cv)].tolist()),True)

        print("Baseline failed component CVs       :",len(baseline_comp_cvs))
        print("Baseline current frozen H2 edges    :",len(baseline_edges))
        print("V1 target CVs / extra edges         :",len(slack_cvs),"/",len(v1_extra))
        print("V2 target CVs / extra edges         :",len(baseline_comp_cvs),"/",len(v2_extra))

        stage="diagnostic_LP_sensitivities"
        try:
            from scipy.optimize import linprog
            from scipy import sparse
            import scipy
        except Exception as exc:
            raise GateError("scipy_HiGHS_unavailable:"+repr(exc)) from exc
        print("SciPy version:",scipy.__version__)

        baseline_comp_set_frozen=set(int(x) for x in baseline_comp_cvs.tolist())

        def solve_variant(
            name:str,
            extra_edges:set[tuple[int,int]],
            sign_relax_target_cvs:set[int],
        )->dict[str,Any]:
            augmented_edges=set(current_edges)|set(extra_edges)

            # Rebuild connectivity over all current culprit CVs. Prospective edges may
            # legitimately merge the baseline failed component with another current component.
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
            if len(target_roots)!=1:
                return {
                    "variant":name,
                    "solver_success":False,
                    "technical_error":"baseline_failed_component_split_after_edge_addition",
                    "target_root_count":len(target_roots),
                }
            vroot=target_roots[0]
            comp_cvs=np.asarray(
                [cv for cv in union_culprit.tolist() if vdsu.find(cv_local[int(cv)])==vroot],
                dtype=np.int64
            )
            comp_set=set(int(x) for x in comp_cvs.tolist())

            ex_idx=np.flatnonzero(np.asarray(
                [int(cv) in comp_set for cv in var_ex_cv],dtype=bool
            ))
            cex_cv=var_ex_cv[ex_idx]
            cex_cell=var_ex_cell[ex_idx]
            cex_x0=var_ex_x0[ex_idx]
            edges=sorted((cv,h) for cv,h in augmented_edges if cv in comp_set)
            hcv=np.asarray([e[0] for e in edges],dtype=np.int64)
            hcell=np.asarray([e[1] for e in edges],dtype=np.int64)
            comp_cells=np.unique(np.r_[cex_cell,hcell]).astype(np.int64)

            # All existing nonzero variables outside the augmented solve component are fixed.
            comp_mask=np.zeros(NSL*NCV,dtype=bool);comp_mask[comp_cvs]=True
            variable_existing=comp_mask[pair_cv]&(np.abs(pair_val)>SIGN_TOL_KG)
            fixed_delta=np.bincount(
                pair_cell[~variable_existing],
                weights=pair_val[~variable_existing],
                minlength=NCELL,
            )
            fixed_mass=old_grid_mass.reshape(-1)+fixed_delta

            n_ex=len(ex_idx);n_h=len(edges);ncv=len(comp_cvs);nbase=n_ex+n_h
            cv_row={int(cv):r for r,cv in enumerate(comp_cvs.tolist())}

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
            relaxed_existing_variable_count=0
            for cv,x0 in zip(cex_cv.tolist(),cex_x0.tolist()):
                if int(cv) in sign_relax_target_cvs:
                    base_bounds.append((None,None))
                    relaxed_existing_variable_count+=1
                elif x0>SIGN_TOL_KG:
                    base_bounds.append((0.0,None))
                elif x0<-SIGN_TOL_KG:
                    base_bounds.append((None,0.0))
                else:
                    base_bounds.append((0.0,0.0))
            base_bounds.extend([(0.0,None)]*n_h)

            # Per-CV equality-slack diagnostic only.
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
                c,A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=cv_delta[comp_cvs],
                bounds=bounds,method="highs",options={"presolve":True}
            )
            elapsed=float(time.time()-t0)
            if not res.success:
                return {
                    "variant":name,
                    "solver_success":False,
                    "solver_status":int(res.status),
                    "solver_message":str(res.message),
                    "augmented_component_CV_count":int(len(comp_cvs)),
                    "augmented_component_cell_count":int(len(comp_cells)),
                    "existing_variable_count":int(n_ex),
                    "H2_edge_count":int(n_h),
                    "extra_edge_count":int(len(set(edges)-set(current_edges))),
                    "relaxed_existing_variable_count":int(relaxed_existing_variable_count),
                    "runtime_s":elapsed,
                }

            z=np.asarray(res.x,dtype=np.float64)
            splus=z[nbase:nbase+ncv]
            sminus=z[nbase+ncv:nbase+2*ncv]
            abs_slack=splus+sminus
            nz=abs_slack>SLACK_TOL_KG
            cell_mass=fixed_mass[comp_cells]+np.asarray(Acell@z[:nbase]).ravel()

            extra_used=set(edges)-set(current_edges)
            return {
                "variant":name,
                "solver_success":True,
                "solver_status":int(res.status),
                "solver_message":str(res.message),
                "augmented_component_CV_count":int(len(comp_cvs)),
                "augmented_component_cell_count":int(len(comp_cells)),
                "existing_variable_count":int(n_ex),
                "H2_edge_count":int(n_h),
                "extra_edge_count":int(len(extra_used)),
                "extra_unique_cell_count":int(len({h for _,h in extra_used})),
                "relaxed_existing_variable_count":int(relaxed_existing_variable_count),
                "minimum_total_CV_conservation_slack_kg":float(np.sum(abs_slack)),
                "maximum_single_CV_conservation_slack_kg":float(np.max(abs_slack)) if len(abs_slack) else 0.0,
                "CVs_with_nonzero_conservation_slack":int(np.sum(nz)),
                "maximum_cell_lower_violation_kg":max(0.0,-float(np.min(cell_mass))),
                "maximum_cell_upper_violation_kg":max(0.0,float(np.max(cell_mass-capacity[comp_cells]))),
                "runtime_s":elapsed,
            }

        variants:list[dict[str,Any]]=[]
        v0=solve_variant("V0_CURRENT_FROZEN_R4_GRAPH",set(),set())
        variants.append(v0)
        gate("V0_success",v0.get("solver_success") is True,v0)
        gate("V0_baseline_slack_reproduced",
             abs(float(v0["minimum_total_CV_conservation_slack_kg"])-EXPECTED_BASELINE_SLACK)<=1e-6,
             v0["minimum_total_CV_conservation_slack_kg"])
        gate("V0_failed_component_CV_count",
             int(v0["augmented_component_CV_count"])==EXPECTED_CV_COUNT,v0["augmented_component_CV_count"])
        gate("V0_failed_component_cell_count",
             int(v0["augmented_component_cell_count"])==EXPECTED_CELL_COUNT,v0["augmented_component_cell_count"])
        gate("V0_existing_variable_count",
             int(v0["existing_variable_count"])==EXPECTED_EXISTING_VARIABLE_COUNT,v0["existing_variable_count"])
        gate("V0_H2_edge_count",
             int(v0["H2_edge_count"])==EXPECTED_H2_EDGE_COUNT,v0["H2_edge_count"])

        v1=solve_variant(
            "V1_DAY375_SLACK_CVS_COMPONENT_FRONTIER_COMPLETION_IN_FROZEN_H2_DOMAIN",
            v1_extra,set()
        )
        variants.append(v1)
        gate("V1_success",v1.get("solver_success") is True,v1)

        v2=None
        v3=None
        if float(v1["minimum_total_CV_conservation_slack_kg"])>SLACK_TOL_KG:
            v2=solve_variant(
                "V2_ALL_78_FAILED_COMPONENT_CVS_COMPONENT_FRONTIER_COMPLETION_IN_FROZEN_H2_DOMAIN",
                v2_extra,set()
            )
            variants.append(v2)
            gate("V2_success",v2.get("solver_success") is True,v2)

            if float(v2["minimum_total_CV_conservation_slack_kg"])>SLACK_TOL_KG:
                v3=solve_variant(
                    "V3_V2_PLUS_EXISTING_SIGN_RELAXATION_FOR_BASELINE_78_COMPONENT_CVS",
                    v2_extra,baseline_comp_set_frozen
                )
                variants.append(v3)
                gate("V3_success",v3.get("solver_success") is True,v3)

        stage="classification_freeze"
        v0_slack=float(v0["minimum_total_CV_conservation_slack_kg"])
        v1_slack=float(v1["minimum_total_CV_conservation_slack_kg"])
        v2_slack=(float(v2["minimum_total_CV_conservation_slack_kg"]) if v2 is not None else None)
        v3_slack=(float(v3["minimum_total_CV_conservation_slack_kg"]) if v3 is not None else None)

        if v1_slack<=SLACK_TOL_KG:
            classification="TWELVE_NEW_ZERO_H2_SLACK_CVS_CONTROL_RECURRENT_NETWORK_CUT"
            next_name="Day375 Recurrent Component-Frontier H2 Eligibility Prospective Repair Semantics Freeze"
            candidate_rule="component_frontier_completion_for_12_Day375_nonzero_slack_CVs"
            chosen_targets=slack_cvs
            chosen_edges=v1_extra
        elif v2_slack is not None and v2_slack<=SLACK_TOL_KG:
            classification="FAILED_COMPONENT_RECURRENT_ELIGIBILITY_CONTROLS_NETWORK_CUT"
            next_name="Day375 Recurrent Component-Frontier H2 Eligibility Prospective Repair Semantics Freeze"
            candidate_rule="component_frontier_completion_for_all_78_Day375_failed_component_CVs"
            chosen_targets=baseline_comp_cvs
            chosen_edges=v2_extra
        elif v3_slack is not None and v3_slack<=SLACK_TOL_KG:
            classification="RECURRENT_ELIGIBILITY_PLUS_SIGN_PRESERVATION_CONTROL_NETWORK_CUT"
            next_name="Day375 Recurrent Sign-Preservation and Eligibility Physical-Admissibility Design Audit"
            candidate_rule=None
            chosen_targets=np.asarray([],dtype=np.int64)
            chosen_edges=set()
        else:
            classification="RECURRENT_NETWORK_CUT_PERSISTS_AFTER_FROZEN_DOMAIN_FRONTIER_SENSITIVITY"
            next_name="Day375 Residual Recurrent Network-Cut / Domain-Topology Design Audit"
            candidate_rule=None
            chosen_targets=np.asarray([],dtype=np.int64)
            chosen_edges=set()

        # Freeze the exact prospective candidate manifests when eligibility alone controls the cut.
        target_rows=[
            {
                "cv_id":int(cv),
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
            }
            for cv in chosen_targets.tolist()
        ]
        edge_rows=[]
        for cv,h in sorted(chosen_edges):
            k,j,i=ijk(int(h))
            edge_rows.append({
                "cv_id":int(cv),
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
                "halo_flat_cell":int(h),
                "k":int(k),"j":int(j),"i":int(i),
            })

        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R6_R2_Final_Artifacts"
        if local.exists():shutil.rmtree(local)
        local.mkdir(parents=True)

        target_path=local/"POSTV16_AV4_PIVOT_P2_R6_R2_Prospective_Target_CVs.csv"
        edge_path=local/"POSTV16_AV4_PIVOT_P2_R6_R2_Prospective_ComponentFrontier_Edges.csv"
        target_path.write_bytes(csv_bytes(target_rows))
        edge_path.write_bytes(csv_bytes(edge_rows))
        target_sha=sha256_file(target_path)
        edge_sha=sha256_file(edge_path)

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "audit_only":True,
            "repair_executed":False,
            "accepted_state_created":False,
            "baseline_component_CV_count":int(len(baseline_comp_cvs)),
            "baseline_component_cell_count":int(len(baseline_cells)),
            "baseline_existing_variable_count":int(len(baseline_ex_idx)),
            "baseline_H2_edge_count":int(len(baseline_edges)),
            "baseline_slack_CV_count":int(len(slack_cvs)),
            "baseline_zero_H2_slack_CV_count":int(len(zero_h2_slack_cvs)),
            "V0_slack_kg":v0_slack,
            "V1_slack_kg":v1_slack,
            "V2_slack_kg":v2_slack,
            "V3_slack_kg":v3_slack,
            "V1_extra_edge_count":int(len(v1_extra)),
            "V1_extra_unique_cell_count":int(len({h for _,h in v1_extra})),
            "V2_extra_edge_count":int(len(v2_extra)),
            "V2_extra_unique_cell_count":int(len({h for _,h in v2_extra})),
            "classification":classification,
            "candidate_rule_if_any":candidate_rule,
            "prospective_target_CV_count":int(len(chosen_targets)),
            "prospective_edge_count":int(len(chosen_edges)),
            "prospective_target_manifest_sha256":target_sha,
            "prospective_edge_manifest_sha256":edge_sha,
            "H2_cell_domain_changed":False,
            "new_H2_cell_count":0,
            "vertical_support_used":False,
            "pressure_refresh_executed":False,
            "sign_relaxation_executed_in_physical_state":False,
            "P3_authorized":False,
        }

        design={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "frozen_domain":"exact globally frozen R4 H2-XY cell domain",
            "new_cartesian_cells_allowed":False,
            "vertical_support_allowed":False,
            "diagonal_support_allowed":False,
            "pressure_refresh_allowed":False,
            "repair_execution_allowed":False,
            "sensitivity_variants":[v["variant"] for v in variants],
            "component_frontier_definition":(
                "For each target CV, use the same-layer Manhattan-distance-1-or-2 frontier "
                "of that CV's Day375 pre-H2 two-sided existing-support component, intersected "
                "with the globally frozen R4 H2 cell domain; subtract already frozen R4 CV-to-H2 edges."
            ),
            "augmented_connectivity_rule":(
                "Each variant rebuilds connectivity over all Day375 culprit CVs after prospective "
                "edges are added and solves the full connected component containing the original "
                "78-CV failed component."
            ),
            "V3_sign_relaxation_scope":"existing nonzero variables belonging to the original baseline 78 failed-component CVs only",
        }

        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "classification":classification,
            "P2_R6_R3_authorized":True,
            "P2_R6_R3_name":next_name,
            "prospective_recurrent_component_frontier_eligibility_design_authorized":
                classification in {
                    "TWELVE_NEW_ZERO_H2_SLACK_CVS_CONTROL_RECURRENT_NETWORK_CUT",
                    "FAILED_COMPONENT_RECURRENT_ELIGIBILITY_CONTROLS_NETWORK_CUT",
                },
            "prospective_candidate_rule":candidate_rule,
            "prospective_target_CV_count":int(len(chosen_targets)),
            "prospective_edge_count":int(len(chosen_edges)),
            "prospective_target_manifest_sha256":target_sha,
            "prospective_edge_manifest_sha256":edge_sha,
            "sign_preservation_physical_admissibility_audit_authorized":
                classification=="RECURRENT_ELIGIBILITY_PLUS_SIGN_PRESERVATION_CONTROL_NETWORK_CUT",
            "residual_recurrent_network_cut_domain_topology_audit_authorized":
                classification=="RECURRENT_NETWORK_CUT_PERSISTS_AFTER_FROZEN_DOMAIN_FRONTIER_SENSITIVITY",
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

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R2_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R6_R2_Design_Contract.json").write_bytes(json_bytes(design))
        (local/"POSTV16_AV4_PIVOT_P2_R6_R2_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R6_R2_Sensitivity_Variants.csv").write_bytes(csv_bytes(variants))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R6_R2_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists():raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*194)
        print("POSTV16-AV4-PIVOT-P2-R6-R2: PASS")
        for v in variants:
            print(v["variant"])
            print("  augmented CV / cell count  :",v.get("augmented_component_CV_count"),"/",v.get("augmented_component_cell_count"))
            print("  extra edges / unique cells :",v.get("extra_edge_count"),"/",v.get("extra_unique_cell_count"))
            print("  total CV slack kg          :",v.get("minimum_total_CV_conservation_slack_kg"))
            print("  nonzero-slack CV count     :",v.get("CVs_with_nonzero_conservation_slack"))
        print("Classification                :",classification)
        print("Candidate rule                 :",candidate_rule)
        print("Prospective targets / edges    :",len(chosen_targets),"/",len(chosen_edges))
        print("Target manifest SHA256         :",target_sha)
        print("Edge manifest SHA256           :",edge_sha)
        print("P2-R6-R3 authorized            : True")
        print("Repair / new cells / P3        : False / False / False")
        print("="*194)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R6_R2_Blocked_Report.json"
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
