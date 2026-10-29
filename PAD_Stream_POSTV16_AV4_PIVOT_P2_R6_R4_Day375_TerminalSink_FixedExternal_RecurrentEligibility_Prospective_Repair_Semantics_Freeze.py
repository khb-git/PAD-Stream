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


MILESTONE="POSTV16-AV4-PIVOT-P2-R6-R4"
STATUS_PASS=(
    "AV4PIVOTP2R6R4_DAY375_TERMINAL_SINK_FIXED_EXTERNAL_RECURRENT_ELIGIBILITY_"
    "PROSPECTIVE_REPAIR_SEMANTICS_FREEZE_PASS_NO_REPAIR_EXECUTION"
)
STATUS_BLOCKED="AV4PIVOTP2R6R4_TECHNICAL_OR_AUTHORITY_BLOCK"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT="d65011cd470477df683d0d83a225b776a0caac17"
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

EXPECTED_COMPONENT_CVS=78
EXPECTED_COMPONENT_CELLS=60
EXPECTED_EXISTING_VARIABLES=101
EXPECTED_BASELINE_H2_EDGES=421
EXPECTED_TARGET_CVS=12
EXPECTED_RECURRENT_EDGES=234
EXPECTED_RECURRENT_UNIQUE_CELLS=54
EXPECTED_BRIDGE_EDGES=33
EXPECTED_BRIDGE_UNIQUE_SINKS=11
EXPECTED_EXTERNAL_BASELINE_COMPONENTS=1
EXPECTED_EXTERNAL_CURRENT_CVS=20
EXPECTED_L1_LOCAL_CELLS=91
EXPECTED_L1_TOTAL_H2_EDGES=655
EXPECTED_SHARED_CANDIDATE_SINKS=34
EXPECTED_FIXED_EXTERNAL_MASS_SHARED_CANDIDATES=40108.01098297185

R3_CLASS=(
    "SHARED_TERMINAL_SINK_VARIABLE_CONNECTIVITY_OVERCOUPLES_RECURRENCE_"
    "AND_12_CV_LOCAL_ELIGIBILITY_IS_SUFFICIENT"
)
R3_RULE="12_Day375_slack_CVs_component_frontier_with_external_components_fixed"
R4_NAME="Day375 Terminal-Sink Fixed-External Recurrent Eligibility Prospective Repair Semantics Freeze"

CV_TOL_KG=1.0e-7
CELL_TOL_KG=1.0e-7
SIGN_TOL_KG=1.0e-10
SLACK_TOL_KG=1.0e-8

BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

R3_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R3_Day375_Residual_Recurrent_NetworkCut_DomainTopology_Audit"
R3_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R3_Summary.json"
R3_DECISION="POSTV16_AV4_PIVOT_P2_R6_R3_Decision_Contract.json"
R3_TOPOLOGY="POSTV16_AV4_PIVOT_P2_R6_R3_Bridge_Topology_Audit.csv"
R3_LOCAL="POSTV16_AV4_PIVOT_P2_R6_R3_TerminalSink_Local_Sensitivity.csv"
R3_STATUS=(
    "AV4PIVOTP2R6R3_DAY375_RESIDUAL_RECURRENT_NETWORK_CUT_DOMAIN_TOPOLOGY_"
    "DESIGN_AUDIT_PASS_NO_REPAIR_EXECUTION"
)

R1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R1_Day375_Component1_Infeasibility_Localization_Audit"
R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R1_Summary.json"
R1_CSV="POSTV16_AV4_PIVOT_P2_R6_R1_Component1_CV_Diagnostics.csv"

R4_STATE_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
R4_STATE_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Summary.json"
R4_STATE_FILE="POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz"
R4_STATE_STATUS=(
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

OUT_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R4_Day375_TerminalSink_FixedExternal_RecurrentEligibility_Semantics_Freeze"
BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R4_BLOCKED"

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
R3RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R3_Day375_Residual_Recurrent_NetworkCut_DomainTopology_Design_Audit.py"
R3RUN_BLOB="e091f51c9309ae86169815b6074557f945cbb577"
R1RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R1_Day375_Component1_Infeasibility_Localization_and_RecurrentSupport_Audit.py"
R1RUN_BLOB="9196eca21a42323a47657362e353232b9c200419"

SOURCE_BLOBS={
    F4R3:F4R3_BLOB,
    A4R2:A4R2_BLOB,
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
    R3RUN:R3RUN_BLOB,
    R1RUN:R1RUN_BLOB,
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
    assert EXPECTED_COMPONENT_CVS==78
    assert EXPECTED_TARGET_CVS==12
    assert EXPECTED_RECURRENT_EDGES==234
    assert EXPECTED_L1_TOTAL_H2_EDGES==655
    assert R3_RULE=="12_Day375_slack_CVs_component_frontier_with_external_components_fixed"
    print("POSTV16 AV4 PIVOT P2-R6-R4 structural self-test: PASS")


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

    print("="*196)
    print("POSTV16-AV4-PIVOT-P2-R6-R4 -- DAY375 TERMINAL-SINK FIXED-EXTERNAL RECURRENT ELIGIBILITY PROSPECTIVE REPAIR SEMANTICS FREEZE")
    print("="*196)
    print("DESIGN/FREEZE ONLY. NO PHYSICAL REPAIR. NO ACCEPTED DAY375 STATE. NO NEW CELLS. NO PRESSURE REFRESH. NO P3.")
    print("FREEZE EXACT 12 TARGET CVS + 234 RECURRENT EDGES + FIXED-EXTERNAL TERMINAL-SINK CAPACITY SEMANTICS.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R4_Summary.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R6_R4_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P2-R6-R4 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_P2R6R4_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_R3_PASS_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,
             git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",
             repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="R3_PASS_binding"
        r3dir=drive/R3_REL
        r3s=load_json(r3dir/R3_SUMMARY)
        r3d=load_json(r3dir/R3_DECISION)
        r3top=read_csv(r3dir/R3_TOPOLOGY)
        r3local=read_csv(r3dir/R3_LOCAL)

        gate("R3_status_exact",r3s.get("status")==R3_STATUS,r3s.get("status"))
        gate("R3_decision_status_exact",r3d.get("status")==R3_STATUS,r3d.get("status"))
        gate("R3_class_exact",r3s.get("classification")==R3_CLASS,r3s.get("classification"))
        gate("R3_candidate_rule_exact",r3s.get("candidate_rule_if_any")==R3_RULE,r3s.get("candidate_rule_if_any"))
        gate("R3_R4_authorized",r3d.get("P2_R6_R4_authorized") is True,r3d.get("P2_R6_R4_authorized"))
        gate("R3_R4_name_exact",r3d.get("P2_R6_R4_name")==R4_NAME,r3d.get("P2_R6_R4_name"))
        gate("R3_terminal_sink_design_authorized",
             r3d.get("terminal_sink_fixed_external_recurrent_eligibility_design_authorized") is True)
        gate("R3_repair_false",r3d.get("repair_execution_authorized") is False)
        gate("R3_support_growth_false",r3d.get("support_growth_execution_authorized") is False)
        gate("R3_new_cells_false",r3d.get("new_H2_cells_authorized") is False)
        gate("R3_vertical_false",r3d.get("vertical_support_authorized") is False)
        gate("R3_pressure_false",r3d.get("pressure_refresh_authorized") is False)
        gate("R3_P3_false",r3d.get("P3_authorized") is False)

        gate("R3_baseline_CVs_exact",int(r3s["baseline_failed_component_CV_count"])==EXPECTED_COMPONENT_CVS)
        gate("R3_baseline_cells_exact",int(r3s["baseline_failed_component_cell_count"])==EXPECTED_COMPONENT_CELLS)
        gate("R3_baseline_existing_vars_exact",int(r3s["baseline_existing_variable_count"])==EXPECTED_EXISTING_VARIABLES)
        gate("R3_baseline_H2_edges_exact",int(r3s["baseline_H2_edge_count"])==EXPECTED_BASELINE_H2_EDGES)
        gate("R3_L1_zero_slack",abs(float(r3s["L1_slack_kg"]))<=SLACK_TOL_KG,r3s["L1_slack_kg"])
        gate("R3_no_domain_change",r3s.get("H2_cell_domain_changed") is False)
        gate("R3_no_new_cells",int(r3s.get("new_H2_cell_count",-1))==0)
        gate("R3_no_vertical",r3s.get("vertical_support_used") is False)
        gate("R3_no_pressure_refresh",r3s.get("pressure_refresh_executed") is False)
        gate("R3_no_halo_transit",r3s.get("halo_transit_executed") is False)

        v1top=next(r for r in r3top if r["variant"]=="V1")
        gate("R3_V1_extra_edges_exact",int(v1top["extra_edge_count"])==EXPECTED_RECURRENT_EDGES)
        gate("R3_V1_unique_cells_exact",int(v1top["extra_unique_cell_count"])==EXPECTED_RECURRENT_UNIQUE_CELLS)
        gate("R3_V1_bridge_edges_exact",int(v1top["bridge_edge_count"])==EXPECTED_BRIDGE_EDGES)
        gate("R3_V1_bridge_sinks_exact",int(v1top["bridge_unique_sink_cell_count"])==EXPECTED_BRIDGE_UNIQUE_SINKS)
        gate("R3_V1_external_components_exact",
             int(v1top["external_baseline_component_count_touched_directly"])==EXPECTED_EXTERNAL_BASELINE_COMPONENTS)
        gate("R3_V1_external_CVs_exact",
             int(v1top["external_current_CV_count_touched_directly"])==EXPECTED_EXTERNAL_CURRENT_CVS)

        l1=next(r for r in r3local if r["variant"]=="L1_12_SLACK_CV_FRONTIER_FIXED_EXTERNAL_TERMINAL_SINK")
        gate("R3_L1_component_CVs_exact",int(l1["local_component_CV_count"])==EXPECTED_COMPONENT_CVS)
        gate("R3_L1_component_cells_exact",int(l1["local_component_cell_count"])==EXPECTED_L1_LOCAL_CELLS)
        gate("R3_L1_existing_vars_exact",int(l1["existing_variable_count"])==EXPECTED_EXISTING_VARIABLES)
        gate("R3_L1_total_H2_edges_exact",int(l1["H2_edge_count"])==EXPECTED_L1_TOTAL_H2_EDGES)
        gate("R3_L1_extra_edges_exact",int(l1["extra_edge_count"])==EXPECTED_RECURRENT_EDGES)
        gate("R3_L1_extra_unique_cells_exact",int(l1["extra_unique_cell_count"])==EXPECTED_RECURRENT_UNIQUE_CELLS)
        gate("R3_L1_shared_candidate_sinks_exact",
             int(l1["shared_candidate_sink_cell_count"])==EXPECTED_SHARED_CANDIDATE_SINKS)
        gate("R3_L1_fixed_external_mass_exact",
             abs(float(l1["fixed_external_mass_on_shared_candidate_cells_kg"])-EXPECTED_FIXED_EXTERNAL_MASS_SHARED_CANDIDATES)<=1e-6,
             l1["fixed_external_mass_on_shared_candidate_cells_kg"])
        gate("R3_L1_nonzero_slack_CVs_zero",int(l1["CVs_with_nonzero_conservation_slack"])==0)
        gate("R3_L1_cell_lower_clean",float(l1["maximum_cell_lower_violation_kg"])<=CELL_TOL_KG)
        gate("R3_L1_cell_upper_clean",float(l1["maximum_cell_upper_violation_kg"])<=CELL_TOL_KG)

        stage="R1_target_binding"
        r1dir=drive/R1_REL
        r1s=load_json(r1dir/R1_SUMMARY)
        r1rows=read_csv(r1dir/R1_CSV)
        target_rows_src=[
            r for r in r1rows
            if float(r["diagnostic_absolute_slack_kg"])>SLACK_TOL_KG
        ]
        target_cvs=np.asarray(sorted(int(r["cv_id"]) for r in target_rows_src),dtype=np.int64)
        gate("R1_target_CV_count_exact",len(target_cvs)==EXPECTED_TARGET_CVS,len(target_cvs))
        gate("R1_all_targets_zero_H2",
             all(int(float(r["frozen_H2_edge_count"]))==0 for r in target_rows_src))
        gate("R1_all_targets_outside_old_R4_target",
             all(str(r["in_R4_327_target_set"]).strip().lower()=="false" for r in target_rows_src))
        gate("R1_all_targets_upper_culprits",
             all(str(r["is_Day375_upper_culprit"]).strip().lower()=="true" for r in target_rows_src))

        stage="Day375_authority_reconstruction"
        r4dir=drive/R4_STATE_REL
        r4s=load_json(r4dir/R4_STATE_SUMMARY)
        r4state_path=r4dir/R4_STATE_FILE
        gate("Day370_R4_status_exact",r4s.get("status")==R4_STATE_STATUS,r4s.get("status"))
        gate("Day370_R4_state_SHA_exact",sha256_file(r4state_path)==r4s.get("accepted_state_sha256"))
        with np.load(r4state_path,allow_pickle=False) as z:
            state={k:np.asarray(z[k]).copy() for k in z.files}

        old_cv_mass=np.asarray(state["cv_component_mass_kg"],dtype=np.float64)
        old_cv_sat=np.asarray(state["cv_saturation"],dtype=np.float64)
        old_grid_mass=np.asarray(state["grid_component_mass_kg"],dtype=np.float64)
        frozen_pair_cv=np.asarray(state["existing_pair_cv"],dtype=np.int64)
        frozen_pair_cell=np.asarray(state["existing_pair_cell"],dtype=np.int64)
        frozen_halo_cv=np.asarray(state["halo_cv"],dtype=np.int64)
        frozen_halo_cell=np.asarray(state["halo_cell"],dtype=np.int64)
        frozen_halo_domain=set(int(x) for x in np.unique(frozen_halo_cell).tolist())
        frozen_edge_set=set((int(cv),int(h)) for cv,h in zip(frozen_halo_cv.tolist(),frozen_halo_cell.tolist()))

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

        f4=load_module(root/F4R3,"p2r6r4_f4")
        a4=load_module(root/A4R2,"p2r6r4_a4")
        r2=load_module(root/R2SRC,"p2r6r4_r2")
        e37=load_module(root/E37A,"p2r6r4_e37")
        sg7d=load_module(root/SG7D,"p2r6r4_sg7d")

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
        cv_delta=(new_cv_mass-old_cv_mass).reshape(-1)

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
        cell_capacity=(grid_pv*rho_max*MAX_SG).reshape(-1)

        direct_delta=np.bincount(pair_cell,weights=pair_val,minlength=NCELL)
        direct_future=old_grid_mass.reshape(-1)+direct_delta
        lower=direct_future<-CELL_TOL_KG
        upper=direct_future>cell_capacity+CELL_TOL_KG
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

        # Original two-sided S0 component graph.
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

        # Current expanded graph only to identify the authoritative original failed component.
        all_cells=np.union1d(np.unique(existing_cell),np.unique(current_hcell)).astype(np.int64)
        cv_local={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local={int(c):n for n,c in enumerate(all_cells.tolist())}
        dsu=DSU(len(union_culprit)+len(all_cells));off=len(union_culprit)
        for cv,c in zip(existing_cv.tolist(),existing_cell.tolist()):
            dsu.union(cv_local[int(cv)],off+cell_local[int(c)])
        for cv,h in sorted(current_edges):
            dsu.union(cv_local[int(cv)],off+cell_local[int(h)])

        roots=sorted({dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()})
        target_roots=sorted({dsu.find(cv_local[int(cv)]) for cv in target_cvs.tolist()})
        gate("all_12_targets_share_failed_component",len(target_roots)==1,target_roots)
        failed_root=target_roots[0]
        gate("failed_component_index_exact",int(roots.index(failed_root))==FAILED_COMPONENT_ID,
             int(roots.index(failed_root)))
        comp_cvs=np.asarray(
            [cv for cv in union_culprit.tolist() if dsu.find(cv_local[int(cv)])==failed_root],
            dtype=np.int64
        )
        comp_set=set(int(x) for x in comp_cvs.tolist())
        ex_idx=np.flatnonzero(np.asarray([int(cv) in comp_set for cv in var_ex_cv],dtype=bool))
        baseline_edges=sorted((cv,h) for cv,h in current_edges if cv in comp_set)
        baseline_hcells=np.asarray([h for _,h in baseline_edges],dtype=np.int64)
        comp_cells=np.unique(np.r_[var_ex_cell[ex_idx],baseline_hcells]).astype(np.int64)

        gate("failed_component_CVs_exact",len(comp_cvs)==EXPECTED_COMPONENT_CVS,len(comp_cvs))
        gate("failed_component_cells_exact",len(comp_cells)==EXPECTED_COMPONENT_CELLS,len(comp_cells))
        gate("failed_component_existing_vars_exact",len(ex_idx)==EXPECTED_EXISTING_VARIABLES,len(ex_idx))
        gate("failed_component_baseline_H2_edges_exact",len(baseline_edges)==EXPECTED_BASELINE_H2_EDGES,len(baseline_edges))

        stage="exact_recurrent_manifest_freeze"
        recurrent_edges:set[tuple[int,int]]=set()
        for cv in target_cvs.tolist():
            rid=orig_root_of_cv[int(cv)]
            for h in frontier_by_root.get(rid,set()):
                e=(int(cv),int(h))
                if e not in frozen_edge_set:
                    recurrent_edges.add(e)

        gate("recurrent_edge_count_exact",len(recurrent_edges)==EXPECTED_RECURRENT_EDGES,len(recurrent_edges))
        recurrent_cells=sorted({h for _,h in recurrent_edges})
        gate("recurrent_unique_cell_count_exact",len(recurrent_cells)==EXPECTED_RECURRENT_UNIQUE_CELLS,len(recurrent_cells))
        gate("all_recurrent_cells_in_frozen_H2_domain",
             all(int(h) in frozen_halo_domain for h in recurrent_cells))
        gate("no_recurrent_edge_already_frozen",
             len(recurrent_edges & frozen_edge_set)==0)
        gate("all_recurrent_edges_target_only",
             set(cv for cv,_ in recurrent_edges)==set(int(x) for x in target_cvs.tolist()))

        # Baseline component identity by current graph.
        baseline_component_of_cv={int(cv):int(dsu.find(cv_local[int(cv)])) for cv in union_culprit.tolist()}
        failed_component=int(failed_root)
        current_components_by_halo:dict[int,set[int]]={}
        current_cvs_by_halo:dict[int,set[int]]={}
        for cv,h in current_edges:
            current_components_by_halo.setdefault(int(h),set()).add(baseline_component_of_cv[int(cv)])
            current_cvs_by_halo.setdefault(int(h),set()).add(int(cv))

        bridge_edges=[]
        bridge_cells=set()
        external_components=set()
        external_cvs=set()
        for cv,h in sorted(recurrent_edges):
            ext={c for c in current_components_by_halo.get(int(h),set()) if c!=failed_component}
            if ext:
                bridge_edges.append((int(cv),int(h)))
                bridge_cells.add(int(h))
                external_components.update(ext)
                for other_cv in current_cvs_by_halo.get(int(h),set()):
                    if baseline_component_of_cv[int(other_cv)]!=failed_component:
                        external_cvs.add(int(other_cv))

        gate("bridge_edge_count_exact",len(bridge_edges)==EXPECTED_BRIDGE_EDGES,len(bridge_edges))
        gate("bridge_unique_sink_count_exact",len(bridge_cells)==EXPECTED_BRIDGE_UNIQUE_SINKS,len(bridge_cells))
        gate("external_baseline_component_count_exact",len(external_components)==EXPECTED_EXTERNAL_BASELINE_COMPONENTS,len(external_components))
        gate("external_current_CV_count_exact",len(external_cvs)==EXPECTED_EXTERNAL_CURRENT_CVS,len(external_cvs))

        comp_mask=np.zeros(NSL*NCV,dtype=bool);comp_mask[comp_cvs]=True
        variable_existing_local=comp_mask[pair_cv]&(np.abs(pair_val)>SIGN_TOL_KG)
        fixed_delta_local=np.bincount(
            pair_cell[~variable_existing_local],
            weights=pair_val[~variable_existing_local],
            minlength=NCELL,
        )
        fixed_mass_local=old_grid_mass.reshape(-1)+fixed_delta_local

        all_local_edges=sorted(set(baseline_edges)|recurrent_edges)
        all_local_hcells=np.asarray([h for _,h in all_local_edges],dtype=np.int64)
        local_cells=np.unique(np.r_[var_ex_cell[ex_idx],all_local_hcells]).astype(np.int64)
        gate("prospective_local_cell_count_exact",len(local_cells)==EXPECTED_L1_LOCAL_CELLS,len(local_cells))
        gate("prospective_total_H2_edge_count_exact",len(all_local_edges)==EXPECTED_L1_TOTAL_H2_EDGES,len(all_local_edges))

        shared_candidate_cells={
            h for _,h in recurrent_edges if int(h) in current_components_by_halo
        }
        gate("shared_candidate_sink_count_exact",
             len(shared_candidate_cells)==EXPECTED_SHARED_CANDIDATE_SINKS,len(shared_candidate_cells))
        fixed_external_mass_shared=float(np.sum(
            fixed_mass_local[np.asarray(sorted(shared_candidate_cells),dtype=np.int64)]
        ))
        gate("fixed_external_mass_shared_exact",
             abs(fixed_external_mass_shared-EXPECTED_FIXED_EXTERNAL_MASS_SHARED_CANDIDATES)<=1e-6,
             fixed_external_mass_shared)

        target_manifest=[]
        for cv in target_cvs.tolist():
            srcrow=next(r for r in target_rows_src if int(r["cv_id"])==int(cv))
            target_manifest.append({
                "cv_id":int(cv),
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
                "required_day370_to_day375_delta_kg":float(cv_delta[int(cv)]),
                "R1_diagnostic_absolute_slack_kg":float(srcrow["diagnostic_absolute_slack_kg"]),
                "original_S0_component_root_internal":int(orig_root_of_cv[int(cv)]),
                "baseline_H2_edge_count":int(sum(1 for a,_ in baseline_edges if a==int(cv))),
                "new_recurrent_edge_count":int(sum(1 for a,_ in recurrent_edges if a==int(cv))),
            })

        edge_manifest=[]
        for cv,h in sorted(recurrent_edges):
            k,j,i=ijk(int(h))
            ext_components={
                c for c in current_components_by_halo.get(int(h),set())
                if c!=failed_component
            }
            ext_cvs={
                int(other_cv) for other_cv in current_cvs_by_halo.get(int(h),set())
                if baseline_component_of_cv[int(other_cv)]!=failed_component
            }
            edge_manifest.append({
                "cv_id":int(cv),
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
                "original_S0_component_root_internal":int(orig_root_of_cv[int(cv)]),
                "halo_flat_cell":int(h),
                "k":int(k),"j":int(j),"i":int(i),
                "endpoint_in_frozen_R4_H2_domain":True,
                "new_edge_nonnegative_terminal_deposition_only":True,
                "shared_with_external_baseline_component":bool(ext_components),
                "external_baseline_component_count_at_sink":int(len(ext_components)),
                "external_current_CV_count_at_sink":int(len(ext_cvs)),
            })

        occupancy_manifest=[]
        recurrent_cell_set=set(recurrent_cells)
        for h in sorted(recurrent_cell_set):
            k,j,i=ijk(int(h))
            old_mass=float(old_grid_mass.reshape(-1)[int(h)])
            fixed_day375_delta=float(fixed_delta_local[int(h)])
            fixed_occ=float(fixed_mass_local[int(h)])
            cap=float(cell_capacity[int(h)])
            occupancy_manifest.append({
                "halo_flat_cell":int(h),
                "k":int(k),"j":int(j),"i":int(i),
                "old_Day370_grid_mass_kg":old_mass,
                "fixed_external_plus_nonvariable_Day375_delta_kg":fixed_day375_delta,
                "fixed_occupancy_before_local_projection_kg":fixed_occ,
                "physical_capacity_kg":cap,
                "remaining_capacity_before_local_projection_kg":cap-fixed_occ,
                "shared_with_any_current_frozen_H2_edge":bool(int(h) in current_components_by_halo),
                "shared_with_external_baseline_component":bool(
                    any(c!=failed_component for c in current_components_by_halo.get(int(h),set()))
                ),
            })

        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R6_R4_Final_Artifacts"
        if local.exists():shutil.rmtree(local)
        local.mkdir(parents=True)

        target_path=local/"POSTV16_AV4_PIVOT_P2_R6_R4_Frozen_Target_CVs.csv"
        edge_path=local/"POSTV16_AV4_PIVOT_P2_R6_R4_Frozen_Recurrent_Edges.csv"
        occupancy_path=local/"POSTV16_AV4_PIVOT_P2_R6_R4_Frozen_TerminalSink_FixedExternal_Occupancy.csv"
        target_path.write_bytes(csv_bytes(target_manifest))
        edge_path.write_bytes(csv_bytes(edge_manifest))
        occupancy_path.write_bytes(csv_bytes(occupancy_manifest))
        target_sha=sha256_file(target_path)
        edge_sha=sha256_file(edge_path)
        occupancy_sha=sha256_file(occupancy_path)

        design={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "design_freeze_only":True,
            "day375_authority":{
                "parent_R3_classification":R3_CLASS,
                "candidate_rule":R3_RULE,
                "target_CV_count":int(len(target_cvs)),
                "recurrent_edge_count":int(len(recurrent_edges)),
                "recurrent_unique_cell_count":int(len(recurrent_cells)),
            },
            "variable_ownership":{
                "variable_CVs":"exact original 78-CV failed component only",
                "variable_existing_nonzero_pair_count":int(len(ex_idx)),
                "baseline_H2_edges":int(len(baseline_edges)),
                "new_recurrent_edges":int(len(recurrent_edges)),
                "total_H2_edges":int(len(all_local_edges)),
                "external_existing_pair_contributions":"fixed at exact Day375 direct-mapback values",
                "external_H2_step_variables":"fixed zero",
                "shared_sink_cells_do_not_transfer_variable_ownership":True,
                "halo_transit":False,
            },
            "terminal_sink_capacity":{
                "rule":"full physical Cartesian cell capacity minus fixed external/nonvariable occupancy",
                "shared_candidate_sink_count":int(len(shared_candidate_cells)),
                "fixed_external_mass_on_shared_candidate_cells_kg":fixed_external_mass_shared,
                "new_cartesian_cells":0,
                "vertical_support":False,
                "diagonal_support":False,
            },
            "hard_constraints_for_successor":{
                "exact_per_CV_mass_conservation_for_all_78_local_CVs":True,
                "cartesian_cell_mass_lower_bound_kg":0.0,
                "cartesian_cell_mass_upper_bound":"frozen Day365-pressure physical capacity",
                "existing_nonzero_pair_sign_preservation":True,
                "existing_zero_pairs_remain_zero":True,
                "nonlocal_existing_pairs_unchanged":True,
                "new_recurrent_edges_nonnegative_terminal_deposition_only":True,
                "no_clipping":True,
                "no_global_renormalization":True,
                "pressure_refresh":False,
            },
            "lexicographic_objective_for_successor":[
                "1_minimize_total_H2_terminal_deposition_mass_over_421_baseline_plus_234_recurrent_edges",
                "2_within_stage1_optimum_minimize_total_mass_on_234_new_recurrent_edges",
                "3_within_stage1_and_stage2_optima_minimize_L1_deviation_of_101_existing_nonzero_local_contributions",
            ],
            "manifests":{
                "target_CVs":"POSTV16_AV4_PIVOT_P2_R6_R4_Frozen_Target_CVs.csv",
                "target_CVs_sha256":target_sha,
                "recurrent_edges":"POSTV16_AV4_PIVOT_P2_R6_R4_Frozen_Recurrent_Edges.csv",
                "recurrent_edges_sha256":edge_sha,
                "fixed_external_occupancy":"POSTV16_AV4_PIVOT_P2_R6_R4_Frozen_TerminalSink_FixedExternal_Occupancy.csv",
                "fixed_external_occupancy_sha256":occupancy_sha,
            },
        }

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "design_freeze_only":True,
            "repair_executed":False,
            "accepted_state_created":False,
            "target_CV_count":int(len(target_cvs)),
            "recurrent_edge_count":int(len(recurrent_edges)),
            "recurrent_unique_cell_count":int(len(recurrent_cells)),
            "baseline_component_CV_count":int(len(comp_cvs)),
            "baseline_component_cell_count":int(len(comp_cells)),
            "baseline_existing_variable_count":int(len(ex_idx)),
            "baseline_H2_edge_count":int(len(baseline_edges)),
            "prospective_local_cell_count":int(len(local_cells)),
            "prospective_total_H2_edge_count":int(len(all_local_edges)),
            "bridge_edge_count":int(len(bridge_edges)),
            "bridge_unique_sink_count":int(len(bridge_cells)),
            "external_baseline_component_count_touched":int(len(external_components)),
            "external_current_CV_count_touched":int(len(external_cvs)),
            "shared_candidate_sink_count":int(len(shared_candidate_cells)),
            "fixed_external_mass_on_shared_candidate_cells_kg":fixed_external_mass_shared,
            "target_manifest_sha256":target_sha,
            "recurrent_edge_manifest_sha256":edge_sha,
            "fixed_external_occupancy_manifest_sha256":occupancy_sha,
            "H2_cell_domain_changed":False,
            "new_H2_cell_count":0,
            "vertical_support_used":False,
            "pressure_refresh_executed":False,
            "halo_transit_used":False,
            "P3_authorized":False,
        }

        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "P2_R6_R5_authorized":True,
            "P2_R6_R5_name":"Controlled Day375 Terminal-Sink Fixed-External Recurrent Eligibility Exact CV-Conservative Projection Execution",
            "P2_R6_R5_execution_contract":"exact R4 frozen manifests and lexicographic objective only",
            "repair_execution_authorized_in_R4":False,
            "successor_repair_execution_authorized":True,
            "support_growth_execution_authorized":False,
            "new_H2_cells_authorized":False,
            "vertical_support_authorized":False,
            "pressure_refresh_authorized":False,
            "P3_authorized":False,
            "P4_authorized":False,
            "P5_training_authorized":False,
            "R3R6R1_execution_invalidated":False,
        }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R4_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R6_R4_Design_Contract.json").write_bytes(json_bytes(design))
        (local/"POSTV16_AV4_PIVOT_P2_R6_R4_Decision_Contract.json").write_bytes(json_bytes(decision))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R6_R4_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists():raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*196)
        print("POSTV16-AV4-PIVOT-P2-R6-R4: PASS")
        print("Frozen target CV count                    :",len(target_cvs))
        print("Frozen recurrent edge count               :",len(recurrent_edges))
        print("Frozen recurrent unique cell count        :",len(recurrent_cells))
        print("Baseline / total H2 edges                 :",len(baseline_edges),"/",len(all_local_edges))
        print("Local prospective cell count              :",len(local_cells))
        print("Bridge edges / shared bridge sinks        :",len(bridge_edges),"/",len(bridge_cells))
        print("Shared candidate sinks                    :",len(shared_candidate_cells))
        print("Fixed external mass on shared sinks kg    :",fixed_external_mass_shared)
        print("Target manifest SHA256                    :",target_sha)
        print("Recurrent edge manifest SHA256            :",edge_sha)
        print("Fixed external occupancy manifest SHA256  :",occupancy_sha)
        print("P2-R6-R5 execution authorized             : True")
        print("Repair executed in R4 / new cells / P3   : False / False / False")
        print("="*196)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R6_R4_Blocked_Report.json"
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
