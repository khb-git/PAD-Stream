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


MILESTONE="POSTV16-AV4-PIVOT-P2-R6-R5"
STATUS_PASS=(
    "AV4PIVOTP2R6R5_CONTROLLED_DAY375_TERMINAL_SINK_FIXED_EXTERNAL_RECURRENT_"
    "ELIGIBILITY_EXACT_CV_CONSERVATIVE_LOCAL_PROJECTION_EXECUTION_PASS"
)
STATUS_FAIL=(
    "AV4PIVOTP2R6R5_CONTROLLED_DAY375_LOCAL_PROJECTION_SCIENTIFIC_FAIL_"
    "NO_RELAXATION_OR_AUTOMATIC_RERUN_AUTHORIZED"
)
STATUS_BLOCKED="AV4PIVOTP2R6R5_TECHNICAL_OR_AUTHORITY_BLOCK"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT="3d410877e8218efac737df1304b3f287fefd3421"
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
EXPECTED_LOCAL_CELLS=91
EXPECTED_TOTAL_LOCAL_H2_EDGES=655

CV_TOL_KG=1.0e-7
CELL_TOL_KG=1.0e-7
LEDGER_TOL_KG=1.0e-6
SIGN_TOL_KG=1.0e-10

PRIMARY_ABS_TOL_KG=1.0e-7
PRIMARY_REL_TOL=1.0e-11
RECURRENT_ABS_TOL_KG=1.0e-7
RECURRENT_REL_TOL=1.0e-11

BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

R4_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R4_Day375_TerminalSink_FixedExternal_RecurrentEligibility_Semantics_Freeze"
R4_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R4_Summary.json"
R4_DESIGN="POSTV16_AV4_PIVOT_P2_R6_R4_Design_Contract.json"
R4_DECISION="POSTV16_AV4_PIVOT_P2_R6_R4_Decision_Contract.json"
R4_TARGETS="POSTV16_AV4_PIVOT_P2_R6_R4_Frozen_Target_CVs.csv"
R4_EDGES="POSTV16_AV4_PIVOT_P2_R6_R4_Frozen_Recurrent_Edges.csv"
R4_OCCUPANCY="POSTV16_AV4_PIVOT_P2_R6_R4_Frozen_TerminalSink_FixedExternal_Occupancy.csv"
R4_STATUS=(
    "AV4PIVOTP2R6R4_DAY375_TERMINAL_SINK_FIXED_EXTERNAL_RECURRENT_ELIGIBILITY_"
    "PROSPECTIVE_REPAIR_SEMANTICS_FREEZE_PASS_NO_REPAIR_EXECUTION"
)
R5_NAME="Controlled Day375 Terminal-Sink Fixed-External Recurrent Eligibility Exact CV-Conservative Projection Execution"

DAY370_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
DAY370_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Summary.json"
DAY370_STATE="POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz"
DAY370_STATUS=(
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

OUT_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R5_Controlled_Day375_TerminalSink_FixedExternal_Local_Projection"
FAIL_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R5_SCIENTIFIC_FAIL"
BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R5_BLOCKED"

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
A2E="PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB="79a8969233b72b4543edd382a0c3d1028c6dca09"
R4RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R4_Day375_TerminalSink_FixedExternal_RecurrentEligibility_Prospective_Repair_Semantics_Freeze.py"
R4RUN_BLOB="02c5cc227075c4e64b856909545cd1ecbc1daf23"

SOURCE_BLOBS={
    F4R3:F4R3_BLOB,
    A4R2:A4R2_BLOB,
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
    A2E:A2E_BLOB,
    R4RUN:R4RUN_BLOB,
}


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self,gate:str,detail:Any=None):
        super().__init__(gate)
        self.gate=gate
        self.detail=detail


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


def self_test()->None:
    assert EXPECTED_COMPONENT_CVS==78
    assert EXPECTED_TARGET_CVS==12
    assert EXPECTED_RECURRENT_EDGES==234
    assert EXPECTED_TOTAL_LOCAL_H2_EDGES==655
    assert EXPECTED_EXISTING_VARIABLES==101
    print("POSTV16 AV4 PIVOT P2-R6-R5 structural self-test: PASS")


def main(project_root:Path,drive_root:Path)->int:
    root=Path(project_root).resolve()
    drive=Path(drive_root).resolve()
    out=drive/OUT_REL
    fail_dir=drive/FAIL_REL
    block_dir=drive/BLOCK_REL
    stage="preflight"
    scientific_started=False

    def gate(name:str,passed:Any,value:Any=None):
        ok=bool(passed)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok:raise GateError(name)

    def sci_gate(name:str,passed:Any,value:Any=None):
        ok=bool(passed)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok:raise ScientificFail(name,value)

    print("="*198)
    print("POSTV16-AV4-PIVOT-P2-R6-R5 -- CONTROLLED DAY375 TERMINAL-SINK FIXED-EXTERNAL RECURRENT ELIGIBILITY EXACT CV-CONSERVATIVE PROJECTION")
    print("="*198)
    print("EXECUTE EXACT R4-FROZEN 78-CV LOCAL REPAIR. EXTERNAL DAY375 CONTRIBUTIONS REMAIN FIXED DURING THIS LOCAL SOLVE.")
    print("NO NEW CELLS. NO PRESSURE REFRESH. NO VERTICAL/DIAGONAL SUPPORT. NO HALO TRANSIT. NO P3.")
    print("GLOBAL RESIDUAL CELL VIOLATIONS, IF ANY, ARE AUDITED BUT DO NOT EXPAND R5 AUTHORITY.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R5_Summary.json"
        fail_report=fail_dir/"POSTV16_AV4_PIVOT_P2_R6_R5_Scientific_Fail_Report.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R6_R5_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P2-R6-R5 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_P2R6R5_FAIL",not fail_report.exists(),str(fail_report))
        gate("no_preexisting_P2R6R5_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_R4_PASS_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,
             git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",
             repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="R4_PASS_binding"
        r4dir=drive/R4_REL
        r4s=load_json(r4dir/R4_SUMMARY)
        r4design=load_json(r4dir/R4_DESIGN)
        r4d=load_json(r4dir/R4_DECISION)
        target_path=r4dir/R4_TARGETS
        edge_path=r4dir/R4_EDGES
        occupancy_path=r4dir/R4_OCCUPANCY

        gate("R4_status_exact",r4s.get("status")==R4_STATUS,r4s.get("status"))
        gate("R4_design_status_exact",r4design.get("status")==R4_STATUS,r4design.get("status"))
        gate("R4_decision_status_exact",r4d.get("status")==R4_STATUS,r4d.get("status"))
        gate("R4_R5_authorized",r4d.get("P2_R6_R5_authorized") is True,r4d.get("P2_R6_R5_authorized"))
        gate("R4_R5_name_exact",r4d.get("P2_R6_R5_name")==R5_NAME,r4d.get("P2_R6_R5_name"))
        gate("R4_successor_repair_authorized",r4d.get("successor_repair_execution_authorized") is True)
        gate("R4_itself_no_repair",r4d.get("repair_execution_authorized_in_R4") is False)
        gate("R4_no_support_growth",r4d.get("support_growth_execution_authorized") is False)
        gate("R4_no_new_cells",r4d.get("new_H2_cells_authorized") is False)
        gate("R4_no_vertical",r4d.get("vertical_support_authorized") is False)
        gate("R4_no_pressure_refresh",r4d.get("pressure_refresh_authorized") is False)
        gate("R4_P3_false",r4d.get("P3_authorized") is False)

        manifests=r4design["manifests"]
        gate("R4_target_manifest_present",target_path.is_file(),str(target_path))
        gate("R4_edge_manifest_present",edge_path.is_file(),str(edge_path))
        gate("R4_occupancy_manifest_present",occupancy_path.is_file(),str(occupancy_path))
        target_sha=sha256_file(target_path)
        edge_sha=sha256_file(edge_path)
        occupancy_sha=sha256_file(occupancy_path)
        gate("R4_target_manifest_SHA_summary_exact",target_sha==r4s["target_manifest_sha256"],target_sha)
        gate("R4_target_manifest_SHA_design_exact",target_sha==manifests["target_CVs_sha256"],target_sha)
        gate("R4_edge_manifest_SHA_summary_exact",edge_sha==r4s["recurrent_edge_manifest_sha256"],edge_sha)
        gate("R4_edge_manifest_SHA_design_exact",edge_sha==manifests["recurrent_edges_sha256"],edge_sha)
        gate("R4_occupancy_manifest_SHA_summary_exact",occupancy_sha==r4s["fixed_external_occupancy_manifest_sha256"],occupancy_sha)
        gate("R4_occupancy_manifest_SHA_design_exact",occupancy_sha==manifests["fixed_external_occupancy_sha256"],occupancy_sha)

        target_rows=read_csv(target_path)
        edge_rows=read_csv(edge_path)
        occupancy_rows=read_csv(occupancy_path)
        target_cvs=np.asarray(sorted(int(r["cv_id"]) for r in target_rows),dtype=np.int64)
        recurrent_edges=set((int(r["cv_id"]),int(r["halo_flat_cell"])) for r in edge_rows)
        recurrent_cells=set(int(r["halo_flat_cell"]) for r in edge_rows)

        gate("R4_target_count_exact",len(target_cvs)==EXPECTED_TARGET_CVS,len(target_cvs))
        gate("R4_recurrent_edge_count_exact",len(recurrent_edges)==EXPECTED_RECURRENT_EDGES,len(recurrent_edges))
        gate("R4_recurrent_unique_cell_count_exact",len(recurrent_cells)==EXPECTED_RECURRENT_UNIQUE_CELLS,len(recurrent_cells))
        gate("R4_occupancy_row_count_exact",len(occupancy_rows)==EXPECTED_RECURRENT_UNIQUE_CELLS,len(occupancy_rows))

        own=r4design["variable_ownership"]
        gate("R4_variable_CVs_exact",own["variable_CVs"]=="exact original 78-CV failed component only")
        gate("R4_external_existing_fixed",own["external_existing_pair_contributions"]=="fixed at exact Day375 direct-mapback values")
        gate("R4_external_H2_zero",own["external_H2_step_variables"]=="fixed zero")
        gate("R4_shared_sink_no_variable_transfer",own["shared_sink_cells_do_not_transfer_variable_ownership"] is True)
        gate("R4_halo_transit_false",own["halo_transit"] is False)

        stage="Day370_state_binding"
        d370dir=drive/DAY370_REL
        d370s=load_json(d370dir/DAY370_SUMMARY)
        d370path=d370dir/DAY370_STATE
        gate("Day370_status_exact",d370s.get("status")==DAY370_STATUS,d370s.get("status"))
        gate("Day370_state_present",d370path.is_file(),str(d370path))
        gate("Day370_state_SHA_exact",sha256_file(d370path)==d370s.get("accepted_state_sha256"))
        with np.load(d370path,allow_pickle=False) as z:
            state={k:np.asarray(z[k]).copy() for k in z.files}

        old_cv_mass=np.asarray(state["cv_component_mass_kg"],dtype=np.float64)
        old_cv_sat=np.asarray(state["cv_saturation"],dtype=np.float64)
        old_grid_mass=np.asarray(state["grid_component_mass_kg"],dtype=np.float64)
        old_grid_sat=np.asarray(state["grid_saturation"],dtype=np.float64)
        frozen_pair_cv=np.asarray(state["existing_pair_cv"],dtype=np.int64)
        frozen_pair_cell=np.asarray(state["existing_pair_cell"],dtype=np.int64)
        frozen_halo_cv=np.asarray(state["halo_cv"],dtype=np.int64)
        frozen_halo_cell=np.asarray(state["halo_cell"],dtype=np.int64)
        frozen_halo_domain=set(int(x) for x in np.unique(frozen_halo_cell).tolist())
        day370_injected=float(np.asarray(state["injected_mass_kg"]).reshape(()))
        day370_produced=float(np.asarray(state["produced_mass_kg"]).reshape(()))
        gate("Day370_day_exact",abs(float(np.asarray(state["day"]).reshape(()))-370.0)<=1.0e-12)

        stage="Day375_teacher_and_direct_mapback"
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

        f4=load_module(root/F4R3,"p2r6r5_f4")
        a4=load_module(root/A4R2,"p2r6r5_a4")
        r2=load_module(root/R2SRC,"p2r6r5_r2")
        e37=load_module(root/E37A,"p2r6r5_e37")
        sg7d=load_module(root/SG7D,"p2r6r5_sg7d")
        a2e=load_module(root/A2E,"p2r6r5_a2e")

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
        step_injected=float(teacher.get("injected_mass_kg",0.0))
        step_produced=float(teacher.get("produced_mass_kg",0.0))
        teacher_substeps=int(teacher.get("substeps",0))
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
        sci_gate("Day375_subsegment_per_CV_closure",
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
        gate("pair_CV_support_matches_Day370",np.array_equal(pair_cv,frozen_pair_cv))
        gate("pair_cell_support_matches_Day370",np.array_equal(pair_cell,frozen_pair_cell))

        sat_max=np.full(GRID,BACKGROUND+MAX_SG,dtype=np.float64)
        rho_max=np.asarray(r2.gas_density_from_state(sat_max,parent_pressure,p_ref),dtype=np.float64)
        capacity=(grid_pv*rho_max*MAX_SG).reshape(-1)

        direct_delta=np.bincount(pair_cell,weights=pair_val,minlength=NCELL)
        direct_future=old_grid_mass.reshape(-1)+direct_delta
        direct_lower=direct_future<-CELL_TOL_KG
        direct_upper=direct_future>capacity+CELL_TOL_KG
        lower_culprit=np.unique(pair_cv[direct_lower[pair_cell]&(pair_val<-SIGN_TOL_KG)]).astype(np.int64)
        upper_culprit=np.unique(pair_cv[direct_upper[pair_cell]&(pair_val>SIGN_TOL_KG)]).astype(np.int64)
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
        sci_gate("all_R4_targets_in_one_current_component",len(target_roots)==1,target_roots)
        failed_root=target_roots[0]
        sci_gate("failed_component_index_exact",int(roots.index(failed_root))==FAILED_COMPONENT_ID,
                 int(roots.index(failed_root)))
        comp_cvs=np.asarray(
            [cv for cv in union_culprit.tolist() if dsu.find(cv_local[int(cv)])==failed_root],
            dtype=np.int64
        )
        comp_set=set(int(x) for x in comp_cvs.tolist())
        ex_idx=np.flatnonzero(np.asarray([int(cv) in comp_set for cv in var_ex_cv],dtype=bool))
        baseline_edges=set((cv,h) for cv,h in current_edges if cv in comp_set)
        baseline_hcells=np.asarray([h for _,h in sorted(baseline_edges)],dtype=np.int64)
        base_cells=np.unique(np.r_[var_ex_cell[ex_idx],baseline_hcells]).astype(np.int64)

        sci_gate("local_component_CV_count_exact",len(comp_cvs)==EXPECTED_COMPONENT_CVS,len(comp_cvs))
        sci_gate("local_component_cell_count_exact",len(base_cells)==EXPECTED_COMPONENT_CELLS,len(base_cells))
        sci_gate("local_existing_variable_count_exact",len(ex_idx)==EXPECTED_EXISTING_VARIABLES,len(ex_idx))
        sci_gate("local_baseline_H2_edge_count_exact",len(baseline_edges)==EXPECTED_BASELINE_H2_EDGES,len(baseline_edges))
        sci_gate("all_recurrent_edges_target_local_CVs",
                 all(cv in comp_set and cv in set(target_cvs.tolist()) for cv,_ in recurrent_edges))
        sci_gate("all_recurrent_endpoints_in_frozen_H2_domain",
                 all(h in frozen_halo_domain for _,h in recurrent_edges))

        full_edges=sorted(baseline_edges|recurrent_edges)
        hcv=np.asarray([cv for cv,_ in full_edges],dtype=np.int64)
        hcell=np.asarray([h for _,h in full_edges],dtype=np.int64)
        h_is_recurrent=np.asarray([e in recurrent_edges for e in full_edges],dtype=bool)
        local_cells=np.unique(np.r_[var_ex_cell[ex_idx],hcell]).astype(np.int64)

        sci_gate("local_total_H2_edge_count_exact",len(full_edges)==EXPECTED_TOTAL_LOCAL_H2_EDGES,len(full_edges))
        sci_gate("local_cell_count_with_recurrent_exact",len(local_cells)==EXPECTED_LOCAL_CELLS,len(local_cells))
        sci_gate("recurrent_edge_flag_count_exact",int(np.sum(h_is_recurrent))==EXPECTED_RECURRENT_EDGES,int(np.sum(h_is_recurrent)))

        comp_mask=np.zeros(NSL*NCV,dtype=bool);comp_mask[comp_cvs]=True
        variable_existing_local=comp_mask[pair_cv]&(np.abs(pair_val)>SIGN_TOL_KG)
        fixed_delta=np.bincount(
            pair_cell[~variable_existing_local],
            weights=pair_val[~variable_existing_local],
            minlength=NCELL,
        )
        fixed_mass=old_grid_mass.reshape(-1)+fixed_delta

        occupancy_by_cell={int(r["halo_flat_cell"]):r for r in occupancy_rows}
        for h in recurrent_cells:
            sci_gate(
                f"R4_fixed_occupancy_cell_{h}_exact",
                abs(float(occupancy_by_cell[h]["fixed_occupancy_before_local_projection_kg"])-float(fixed_mass[h]))<=1e-6,
                {
                    "R4":float(occupancy_by_cell[h]["fixed_occupancy_before_local_projection_kg"]),
                    "R5":float(fixed_mass[h]),
                }
            )
            sci_gate(
                f"R4_capacity_cell_{h}_exact",
                abs(float(occupancy_by_cell[h]["physical_capacity_kg"])-float(capacity[h]))<=1e-6,
                {
                    "R4":float(occupancy_by_cell[h]["physical_capacity_kg"]),
                    "R5":float(capacity[h]),
                }
            )

        scientific_started=True
        stage="R4_frozen_local_lexicographic_projection"
        try:
            from scipy.optimize import linprog
            from scipy import sparse
            import scipy
        except Exception as exc:
            raise GateError("scipy_HiGHS_unavailable:"+repr(exc)) from exc
        print("SciPy version:",scipy.__version__)

        cex_cv=var_ex_cv[ex_idx]
        cex_cell=var_ex_cell[ex_idx]
        cex_x0=var_ex_x0[ex_idx]
        n_ex=len(ex_idx);n_h=len(full_edges);ncv=len(comp_cvs)
        nvar=n_ex+n_h+n_ex
        ix_x=slice(0,n_ex)
        ix_h=slice(n_ex,n_ex+n_h)

        cv_row={int(cv):r for r,cv in enumerate(comp_cvs.tolist())}
        er=[];ec=[];ev=[]
        for q,cv in enumerate(cex_cv.tolist()):
            er.append(cv_row[int(cv)]);ec.append(q);ev.append(1.0)
        for q,cv in enumerate(hcv.tolist()):
            er.append(cv_row[int(cv)]);ec.append(n_ex+q);ev.append(1.0)
        Aeq=sparse.coo_matrix(
            (np.asarray(ev),(np.asarray(er),np.asarray(ec))),
            shape=(ncv,nvar)
        ).tocsr()
        beq=cv_delta[comp_cvs]

        cell_row={int(c):r for r,c in enumerate(local_cells.tolist())}
        cr=[];cc=[];vv=[]
        for q,c in enumerate(cex_cell.tolist()):
            cr.append(cell_row[int(c)]);cc.append(q);vv.append(1.0)
        for q,c in enumerate(hcell.tolist()):
            cr.append(cell_row[int(c)]);cc.append(n_ex+q);vv.append(1.0)
        Acell=sparse.coo_matrix(
            (np.asarray(vv),(np.asarray(cr),np.asarray(cc))),
            shape=(len(local_cells),nvar)
        ).tocsr()

        bupper=capacity[local_cells]-fixed_mass[local_cells]
        blower=fixed_mass[local_cells]

        rows=[];cols=[];vals=[];rhs=[]
        for q,x0 in enumerate(cex_x0.tolist()):
            rr=len(rhs);rows.extend([rr,rr]);cols.extend([q,n_ex+n_h+q]);vals.extend([1.0,-1.0]);rhs.append(float(x0))
            rr=len(rhs);rows.extend([rr,rr]);cols.extend([q,n_ex+n_h+q]);vals.extend([-1.0,-1.0]);rhs.append(float(-x0))
        Al1=sparse.coo_matrix(
            (np.asarray(vals),(np.asarray(rows),np.asarray(cols))),
            shape=(len(rhs),nvar)
        ).tocsr()
        bl1=np.asarray(rhs,dtype=np.float64)

        Abase=sparse.vstack([Acell,-Acell,Al1],format="csr")
        bbase=np.r_[bupper,blower,bl1]

        bounds=[]
        for x0 in cex_x0.tolist():
            if x0>SIGN_TOL_KG:bounds.append((0.0,None))
            elif x0<-SIGN_TOL_KG:bounds.append((None,0.0))
            else:bounds.append((0.0,0.0))
        bounds.extend([(0.0,None)]*n_h)
        bounds.extend([(0.0,None)]*n_ex)

        # Stage 1: minimum total H2 deposition over baseline + recurrent edges.
        c1=np.zeros(nvar,dtype=np.float64)
        c1[n_ex:n_ex+n_h]=1.0
        t0=time.time()
        lp1=linprog(c1,A_ub=Abase,b_ub=bbase,A_eq=Aeq,b_eq=beq,
                    bounds=bounds,method="highs",options={"presolve":True})
        t1=float(time.time()-t0)
        if not lp1.success:
            raise ScientificFail(
                "Day375_R5_stage1_total_H2_projection_infeasible_or_failed",
                {"status":int(lp1.status),"message":str(lp1.message),
                 "CV_count":ncv,"cell_count":len(local_cells),
                 "existing_variable_count":n_ex,"H2_edge_count":n_h,
                 "recurrent_edge_count":int(np.sum(h_is_recurrent))}
            )
        primary=max(0.0,float(lp1.fun))
        p_tol=max(PRIMARY_ABS_TOL_KG,abs(primary)*PRIMARY_REL_TOL)

        prow=np.zeros(nvar,dtype=np.float64)
        prow[n_ex:n_ex+n_h]=1.0
        A2=sparse.vstack([Abase,sparse.csr_matrix(prow.reshape(1,-1))],format="csr")
        b2=np.r_[bbase,primary+p_tol]

        # Stage 2: within stage-1 envelope, minimum mass on 234 recurrent edges.
        c2=np.zeros(nvar,dtype=np.float64)
        ridx=np.flatnonzero(h_is_recurrent)
        c2[n_ex+ridx]=1.0
        t0=time.time()
        lp2=linprog(c2,A_ub=A2,b_ub=b2,A_eq=Aeq,b_eq=beq,
                    bounds=bounds,method="highs",options={"presolve":True})
        t2=float(time.time()-t0)
        if not lp2.success:
            raise ScientificFail(
                "Day375_R5_stage2_recurrent_edge_mass_minimization_infeasible_or_failed",
                {"status":int(lp2.status),"message":str(lp2.message),
                 "stage1_minimum_total_H2_mass_kg":primary}
            )
        recurrent_min=max(0.0,float(lp2.fun))
        r_tol=max(RECURRENT_ABS_TOL_KG,abs(recurrent_min)*RECURRENT_REL_TOL)

        rrow=np.zeros(nvar,dtype=np.float64)
        rrow[n_ex+ridx]=1.0
        A3=sparse.vstack([A2,sparse.csr_matrix(rrow.reshape(1,-1))],format="csr")
        b3=np.r_[b2,recurrent_min+r_tol]

        # Stage 3: within stages 1-2, minimum L1 disturbance of 101 existing variables.
        c3=np.zeros(nvar,dtype=np.float64)
        c3[n_ex+n_h:]=1.0
        t0=time.time()
        lp3=linprog(c3,A_ub=A3,b_ub=b3,A_eq=Aeq,b_eq=beq,
                    bounds=bounds,method="highs",options={"presolve":True})
        t3=float(time.time()-t0)
        if not lp3.success:
            raise ScientificFail(
                "Day375_R5_stage3_existing_support_L1_infeasible_or_failed",
                {"status":int(lp3.status),"message":str(lp3.message),
                 "stage1_minimum_total_H2_mass_kg":primary,
                 "stage2_minimum_recurrent_edge_mass_kg":recurrent_min}
            )

        z=np.asarray(lp3.x,dtype=np.float64)
        x=z[ix_x]
        h=z[ix_h]
        cv_res=np.asarray(Aeq@z-beq).ravel()
        local_mass=fixed_mass[local_cells]+np.asarray(Acell@z).ravel()

        halo_mass=float(np.sum(h))
        recurrent_mass=float(np.sum(h[h_is_recurrent]))
        existing_l1=float(np.sum(np.abs(x-cex_x0)))
        lower_v=max(0.0,-float(np.min(local_mass)))
        upper_v=max(0.0,float(np.max(local_mass-capacity[local_cells])))
        sign_v=0.0
        for oldv,newv in zip(cex_x0,x):
            if oldv>0:sign_v=max(sign_v,max(0.0,-float(newv)))
            elif oldv<0:sign_v=max(sign_v,max(0.0,float(newv)))
        halo_neg=max(0.0,-float(np.min(h)))

        sci_gate("R5_local_per_CV_equality",
                 float(np.max(np.abs(cv_res)))<=CV_TOL_KG,
                 float(np.max(np.abs(cv_res))))
        sci_gate("R5_local_cell_lower",lower_v<=CELL_TOL_KG,lower_v)
        sci_gate("R5_local_cell_upper",upper_v<=CELL_TOL_KG,upper_v)
        sci_gate("R5_local_existing_sign",sign_v<=SIGN_TOL_KG,sign_v)
        sci_gate("R5_local_H2_nonnegative",halo_neg<=SIGN_TOL_KG,halo_neg)
        sci_gate("R5_stage1_envelope",halo_mass<=primary+p_tol+1.0e-8,
                 {"accepted":halo_mass,"minimum":primary,"tol":p_tol})
        sci_gate("R5_stage2_recurrent_envelope",recurrent_mass<=recurrent_min+r_tol+1.0e-8,
                 {"accepted":recurrent_mass,"minimum":recurrent_min,"tol":r_tol})

        stage="global_local_repair_certification_and_residual_audit"
        repaired_pair_val=pair_val.copy()
        key_to_idx={(int(cv),int(c)):q for q,(cv,c) in enumerate(zip(pair_cv.tolist(),pair_cell.tolist()))}
        for cv,c,newv in zip(cex_cv.tolist(),cex_cell.tolist(),x.tolist()):
            q=key_to_idx.get((int(cv),int(c)))
            if q is None:raise GateError(f"existing_pair_key_not_found:{cv}:{c}")
            repaired_pair_val[q]=float(newv)

        local_h_delta=np.bincount(hcell,weights=h,minlength=NCELL)
        repaired_existing_delta=np.bincount(pair_cell,weights=repaired_pair_val,minlength=NCELL)
        provisional_grid=old_grid_mass.reshape(-1)+repaired_existing_delta+local_h_delta

        repaired_cv_transfer=np.bincount(pair_cv,weights=repaired_pair_val,minlength=NSL*NCV)
        repaired_cv_transfer+=np.bincount(hcv,weights=h,minlength=NSL*NCV)
        global_cv_res=repaired_cv_transfer-cv_delta
        global_ledger=float(np.sum(provisional_grid)-(np.sum(old_grid_mass)+np.sum(cv_delta)))

        sci_gate("R5_global_per_CV_conservation",
                 float(np.max(np.abs(global_cv_res)))<=CV_TOL_KG,
                 float(np.max(np.abs(global_cv_res))))
        sci_gate("R5_global_mass_ledger",abs(global_ledger)<=LEDGER_TOL_KG,global_ledger)

        local_mask=np.zeros(NCELL,dtype=bool);local_mask[local_cells]=True
        post_lower=provisional_grid<-CELL_TOL_KG
        post_upper=provisional_grid>capacity+CELL_TOL_KG

        sci_gate("R5_no_residual_lower_violation_inside_local_domain",
                 not bool(np.any(post_lower&local_mask)),
                 int(np.sum(post_lower&local_mask)))
        sci_gate("R5_no_residual_upper_violation_inside_local_domain",
                 not bool(np.any(post_upper&local_mask)),
                 int(np.sum(post_upper&local_mask)))

        changed=np.abs(repaired_pair_val-pair_val)>1.0e-10
        sci_gate("R5_nonlocal_existing_pairs_unchanged",
                 not bool(np.any(changed&(~comp_mask[pair_cv]))),
                 int(np.sum(changed&(~comp_mask[pair_cv]))))
        sci_gate("R5_existing_zero_pairs_remain_zero",
                 not bool(np.any((np.abs(pair_val)<=SIGN_TOL_KG)&(np.abs(repaired_pair_val)>SIGN_TOL_KG))))
        sci_gate("R5_existing_sign_preserved_globally",
                 not bool(np.any(
                     ((pair_val>SIGN_TOL_KG)&(repaired_pair_val<-SIGN_TOL_KG))
                     |((pair_val<-SIGN_TOL_KG)&(repaired_pair_val>SIGN_TOL_KG))
                 )))

        residual_lower_cells=np.flatnonzero(post_lower)
        residual_upper_cells=np.flatnonzero(post_upper)
        residual_cells=np.union1d(residual_lower_cells,residual_upper_cells).astype(np.int64)
        residual_outside_local=all(not local_mask[int(c)] for c in residual_cells.tolist())
        sci_gate("R5_all_residual_bound_violations_outside_local_authority",
                 residual_outside_local,
                 {"residual_cells":int(len(residual_cells))})

        residual_lower_cvs=np.unique(
            pair_cv[post_lower[pair_cell]&(repaired_pair_val<-SIGN_TOL_KG)]
        ).astype(np.int64)
        residual_upper_cvs=np.unique(
            pair_cv[post_upper[pair_cell]&(repaired_pair_val>SIGN_TOL_KG)]
        ).astype(np.int64)
        residual_cvs=np.union1d(residual_lower_cvs,residual_upper_cvs).astype(np.int64)

        fully_physical=(len(residual_cells)==0)
        accepted_grid_sat=None
        if fully_physical:
            try:
                sg=a2e.invert_local_mass(
                    r2,provisional_grid.reshape(GRID),parent_pressure,p_ref,grid_pv
                )
            except Exception as exc:
                raise ScientificFail("R5_full_Day375_mass_inversion_failure",repr(exc)) from exc
            accepted_grid_sat=BACKGROUND+np.asarray(sg,dtype=np.float64)
            sci_gate("R5_full_Day375_saturation_bounds",
                     float(np.min(accepted_grid_sat))>=BACKGROUND-1.0e-10
                     and float(np.max(accepted_grid_sat))<=BACKGROUND+MAX_SG+1.0e-10,
                     [float(np.min(accepted_grid_sat)),float(np.max(accepted_grid_sat))])

        stage="artifact_publication"
        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R6_R5_Final_Artifacts"
        if local.exists():shutil.rmtree(local)
        local.mkdir(parents=True)

        used=h>1.0e-9
        used_recurrent=used&h_is_recurrent
        used_baseline=used&(~h_is_recurrent)
        used_rows=[]
        for q,(cv,c) in enumerate(full_edges):
            if h[q]<=1.0e-12:continue
            used_rows.append({
                "cv_id":int(cv),
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
                "halo_flat_cell":int(c),
                "edge_kind":"recurrent" if bool(h_is_recurrent[q]) else "baseline",
                "projected_mass_kg":float(h[q]),
            })
        (local/"POSTV16_AV4_PIVOT_P2_R6_R5_Used_Local_H2_Edges.csv").write_bytes(csv_bytes(used_rows))

        residual_rows=[]
        for c in residual_cells.tolist():
            residual_rows.append({
                "flat_cell":int(c),
                "provisional_mass_kg":float(provisional_grid[int(c)]),
                "capacity_kg":float(capacity[int(c)]),
                "lower_violation_kg":max(0.0,-float(provisional_grid[int(c)])),
                "upper_violation_kg":max(0.0,float(provisional_grid[int(c)]-capacity[int(c)])),
                "inside_R5_local_authority":bool(local_mask[int(c)]),
            })
        (local/"POSTV16_AV4_PIVOT_P2_R6_R5_Residual_Cell_Bound_Audit.csv").write_bytes(csv_bytes(residual_rows))

        residual_cv_rows=[]
        for cv in residual_cvs.tolist():
            residual_cv_rows.append({
                "cv_id":int(cv),
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
                "is_R5_local_component":bool(int(cv) in comp_set),
                "is_lower_residual_culprit":bool(int(cv) in set(residual_lower_cvs.tolist())),
                "is_upper_residual_culprit":bool(int(cv) in set(residual_upper_cvs.tolist())),
            })
        (local/"POSTV16_AV4_PIVOT_P2_R6_R5_Residual_CV_Audit.csv").write_bytes(csv_bytes(residual_cv_rows))

        provisional_path=local/"POSTV16_AV4_PIVOT_P2_R6_R5_Provisional_LocalRepaired_Day375_State.npz"
        with provisional_path.open("wb") as fp:
            np.savez_compressed(
                fp,
                day=np.asarray(DAY),
                cv_component_mass_kg=new_cv_mass,
                cv_saturation=new_cv_sat,
                provisional_grid_component_mass_kg=provisional_grid.reshape(GRID),
                parent_pressure_psi=parent_pressure,
                existing_pair_cv=pair_cv,
                existing_pair_cell=pair_cell,
                original_existing_pair_contribution_kg=pair_val,
                locally_repaired_existing_pair_contribution_kg=repaired_pair_val,
                local_halo_cv=hcv,
                local_halo_cell=hcell,
                local_halo_is_recurrent=h_is_recurrent,
                local_halo_contribution_kg=h,
                local_component_cv=comp_cvs,
                recurrent_target_cv=target_cvs,
                residual_lower_cell=residual_lower_cells,
                residual_upper_cell=residual_upper_cells,
                residual_lower_cv=residual_lower_cvs,
                residual_upper_cv=residual_upper_cvs,
                step_injected_mass_kg=np.asarray(step_injected),
                step_produced_mass_kg=np.asarray(step_produced),
                cumulative_injected_mass_kg=np.asarray(day370_injected+step_injected),
                cumulative_produced_mass_kg=np.asarray(day370_produced+step_produced),
                R4_target_manifest_sha256=np.asarray(target_sha),
                R4_recurrent_edge_manifest_sha256=np.asarray(edge_sha),
                R4_fixed_external_occupancy_manifest_sha256=np.asarray(occupancy_sha),
            )
        provisional_sha=sha256_file(provisional_path)

        accepted_state_sha=None
        if fully_physical:
            accepted_path=local/"POSTV16_AV4_PIVOT_P2_R6_R5_Accepted_Day375_State.npz"
            with accepted_path.open("wb") as fp:
                np.savez_compressed(
                    fp,
                    day=np.asarray(DAY),
                    cv_component_mass_kg=new_cv_mass,
                    cv_saturation=new_cv_sat,
                    grid_component_mass_kg=provisional_grid.reshape(GRID),
                    grid_saturation=accepted_grid_sat,
                    parent_pressure_psi=parent_pressure,
                    existing_pair_cv=pair_cv,
                    existing_pair_cell=pair_cell,
                    repaired_existing_pair_contribution_kg=repaired_pair_val,
                    local_halo_cv=hcv,
                    local_halo_cell=hcell,
                    local_halo_is_recurrent=h_is_recurrent,
                    local_halo_contribution_kg=h,
                    cumulative_injected_mass_kg=np.asarray(day370_injected+step_injected),
                    cumulative_produced_mass_kg=np.asarray(day370_produced+step_produced),
                    R4_target_manifest_sha256=np.asarray(target_sha),
                    R4_recurrent_edge_manifest_sha256=np.asarray(edge_sha),
                    R4_fixed_external_occupancy_manifest_sha256=np.asarray(occupancy_sha),
                )
            accepted_state_sha=sha256_file(accepted_path)

        classification=(
            "FULL_DAY375_PHYSICAL_STATE_CLOSED_BY_R5_LOCAL_REPAIR"
            if fully_physical else
            "R5_LOCAL_REPAIR_PASS_RESIDUAL_EXTERNAL_COMPONENT_VIOLATIONS_REQUIRE_STATE_CLOSURE"
        )

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "classification":classification,
            "scientific_execution_started":True,
            "local_repair_executed":True,
            "full_Day375_state_accepted":bool(fully_physical),
            "local_component_CV_count":int(len(comp_cvs)),
            "local_component_existing_variable_count":int(n_ex),
            "baseline_H2_edge_count":int(len(baseline_edges)),
            "recurrent_edge_count":int(np.sum(h_is_recurrent)),
            "total_local_H2_edge_count":int(n_h),
            "local_cell_count":int(len(local_cells)),
            "stage1_minimum_total_H2_mass_kg":float(primary),
            "accepted_total_H2_mass_kg":float(halo_mass),
            "stage2_minimum_recurrent_edge_mass_kg":float(recurrent_min),
            "accepted_recurrent_edge_mass_kg":float(recurrent_mass),
            "stage3_existing_support_L1_adjustment_kg":float(existing_l1),
            "used_baseline_H2_edge_count":int(np.sum(used_baseline)),
            "used_recurrent_H2_edge_count":int(np.sum(used_recurrent)),
            "maximum_local_CV_residual_kg":float(np.max(np.abs(cv_res))),
            "maximum_global_CV_residual_kg":float(np.max(np.abs(global_cv_res))),
            "global_mass_residual_kg":float(global_ledger),
            "direct_lower_violation_count":int(np.sum(direct_lower)),
            "direct_upper_violation_count":int(np.sum(direct_upper)),
            "post_R5_residual_lower_violation_count":int(len(residual_lower_cells)),
            "post_R5_residual_upper_violation_count":int(len(residual_upper_cells)),
            "post_R5_residual_violation_cell_count":int(len(residual_cells)),
            "post_R5_residual_culprit_CV_count":int(len(residual_cvs)),
            "all_residual_violations_outside_R5_local_authority":bool(residual_outside_local),
            "provisional_state_sha256":provisional_sha,
            "accepted_state_sha256":accepted_state_sha,
            "R4_target_manifest_sha256":target_sha,
            "R4_recurrent_edge_manifest_sha256":edge_sha,
            "R4_fixed_external_occupancy_manifest_sha256":occupancy_sha,
            "new_cartesian_cell_count":0,
            "vertical_support_used":False,
            "diagonal_support_used":False,
            "halo_transit_used":False,
            "pressure_refresh_executed":False,
            "P3_authorized":False,
        }

        if fully_physical:
            decision={
                "milestone":MILESTONE,
                "status":STATUS_PASS,
                "classification":classification,
                "accepted_Day375_state_sha256":accepted_state_sha,
                "P2_R6_R6_authorized":True,
                "P2_R6_R6_name":"Day375 Accepted-State Sealing and Frozen-Flow Continuation Restart Protocol Freeze",
                "P2_continuation_restart_authorized_now":False,
                "residual_external_state_closure_required":False,
                "support_growth_authorized":False,
                "new_H2_cells_authorized":False,
                "pressure_refresh_authorized":False,
                "P3_authorized":False,
                "P4_authorized":False,
                "P5_training_authorized":False,
            }
        else:
            decision={
                "milestone":MILESTONE,
                "status":STATUS_PASS,
                "classification":classification,
                "accepted_Day375_state_sha256":None,
                "provisional_local_repair_state_sha256":provisional_sha,
                "P2_R6_R6_authorized":True,
                "P2_R6_R6_name":"Day375 Residual External-Component Projection Authority and Global State-Closure Audit",
                "P2_continuation_restart_authorized_now":False,
                "residual_external_state_closure_required":True,
                "support_growth_authorized":False,
                "new_H2_cells_authorized":False,
                "pressure_refresh_authorized":False,
                "P3_authorized":False,
                "P4_authorized":False,
                "P5_training_authorized":False,
            }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R5_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R6_R5_Decision_Contract.json").write_bytes(json_bytes(decision))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R6_R5_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists():raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*198)
        print("POSTV16-AV4-PIVOT-P2-R6-R5: PASS")
        print("Classification                          :",classification)
        print("Local CVs / existing vars               :",len(comp_cvs),"/",n_ex)
        print("Baseline / recurrent / total H2 edges   :",len(baseline_edges),"/",int(np.sum(h_is_recurrent)),"/",n_h)
        print("Stage1 min / accepted H2 kg             :",primary,"/",halo_mass)
        print("Stage2 min / accepted recurrent kg      :",recurrent_min,"/",recurrent_mass)
        print("Stage3 existing-support L1 kg           :",existing_l1)
        print("Global CV residual kg                   :",float(np.max(np.abs(global_cv_res))))
        print("Global mass ledger residual kg          :",global_ledger)
        print("Residual lower / upper cells            :",len(residual_lower_cells),"/",len(residual_upper_cells))
        print("Full Day375 accepted                    :",fully_physical)
        print("P2-R6-R6 authorized                     : True")
        print("P3 authorized                           : False")
        print("="*198)
        return 0

    except ScientificFail as exc:
        fail_dir.mkdir(parents=True,exist_ok=True)
        p=fail_dir/"POSTV16_AV4_PIVOT_P2_R6_R5_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_FAIL,
                "failed_stage":stage,
                "failed_gate":exc.gate,
                "detail":exc.detail,
                "scientific_execution_started":scientific_started,
                "automatic_rerun_authorized":False,
                "support_growth_authorized":False,
                "new_H2_cells_authorized":False,
                "pressure_refresh_authorized":False,
                "P3_authorized":False,
                "P4_authorized":False,
                "P5_training_authorized":False,
            },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(MILESTONE+": SCIENTIFIC FAIL")
        print("Stage:",stage)
        print("Gate :",exc.gate)
        print("Detail:",exc.detail)
        return 3

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R6_R5_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "scientific_execution_started":scientific_started,
                "automatic_rerun_authorized":False,
                "support_growth_authorized":False,
                "new_H2_cells_authorized":False,
                "pressure_refresh_authorized":False,
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
