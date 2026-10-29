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


MILESTONE = "POSTV16-AV4-PIVOT-P2-R5-G2A-R4-R1-R1"
STATUS_PASS = (
    "AV4PIVOTP2R5G2AR4R1R1_BLOCK_PATH_IDENTITY_CLOSURE_"
    "AND_COMPONENT_FRONTIER_PROJECTION_EXECUTION_PASS"
)
STATUS_FAIL = (
    "AV4PIVOTP2R5G2AR4R1R1_COMPONENT_FRONTIER_H2_PROJECTION_SCIENTIFIC_FAIL_"
    "NO_RELAXATION_OR_AUTOMATIC_RERUN_AUTHORIZED"
)
STATUS_BLOCKED = "AV4PIVOTP2R5G2AR4R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "57ea30db3fa5ac053bea848f2974e5fbe50c7747"
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

CV_EQUALITY_TOL_KG=1.0e-7
CELL_BOUND_TOL_KG=1.0e-7
GLOBAL_LEDGER_TOL_KG=1.0e-6
SIGN_TOL_KG=1.0e-10

PRIMARY_ABS_TOL_KG=1.0e-7
PRIMARY_REL_TOL=1.0e-11
COMPLETION_ABS_TOL_KG=1.0e-7
COMPLETION_REL_TOL=1.0e-11

EXPECTED_TARGET_CVS=327
EXPECTED_COMPLETION_EDGES=46915
HISTORICAL_FAILED_COMPONENT_BASELINE_H2_EDGES=402976
EXPECTED_FAILED_COMPONENT_CVS=49627
EXPECTED_FAILED_COMPONENT_CELLS=23845
EXPECTED_FAILED_EXISTING_VARIABLES=59220

BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G1R1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G1_R1_Alternative_Geometric_Domain_Freeze"
G1R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G1_R1_Summary.json"
G1R1_STATUS=(
    "AV4PIVOTP2R5G1R1_ALTERNATIVE_GEOMETRIC_DOMAIN_CANDIDATE_"
    "COMPARISON_AND_FREEZE_PASS_NO_SUPPORT_EXPANSION_EXECUTED"
)

R4_BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_BLOCKED"
R4_BLOCK_REPORT="POSTV16_AV4_PIVOT_P2_R5_G2A_R4_Blocked_Report.json"
R4_BLOCK_STATUS="AV4PIVOTP2R5G2AR4_TECHNICAL_OR_AUTHORITY_BLOCK"
R4_BLOCK_STAGE="reconstruct_day370_mapback"
R4_BLOCK_EXCEPTION="GateError('baseline_H2_edge_count_exact')"

# R4-R1 wrote its own block report into the historical R4 block directory because
# its BLOCK_REL was incorrectly left pointed at R4_BLOCKED. Bind that immutable
# misplaced artifact exactly; do not move or rewrite it.
R4R1_BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_BLOCKED"
R4R1_BLOCK_REPORT="POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_Blocked_Report.json"
R4R1_BLOCK_STATUS="AV4PIVOTP2R5G2AR4R1_TECHNICAL_OR_AUTHORITY_BLOCK"
R4R1_BLOCK_STAGE="R4_block_binding"
R4R1_BLOCK_EXCEPTION="FileNotFoundError(2, 'No such file or directory')"

R3_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R3_ComponentFrontier_H2_Eligibility_Repair_Semantics_Freeze"
R3_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R3_Summary.json"
R3_DECISION="POSTV16_AV4_PIVOT_P2_R5_G2A_R3_Decision_Contract.json"
R3_DESIGN="POSTV16_AV4_PIVOT_P2_R5_G2A_R3_Design_Contract.json"
R3_TARGETS="POSTV16_AV4_PIVOT_P2_R5_G2A_R3_Target_CVs.csv"
R3_COMPLETION="POSTV16_AV4_PIVOT_P2_R5_G2A_R3_ComponentFrontier_Completion_Edges.csv"
R3_STATUS=(
    "AV4PIVOTP2R5G2AR3_COMPONENT_FRONTIER_H2_ELIGIBILITY_"
    "PROSPECTIVE_REPAIR_SEMANTICS_FREEZE_PASS_NO_REPAIR_EXECUTION"
)
R4_NAME="Controlled Component-Frontier H2 Eligibility Exact CV-Conservative Projection Execution"

R1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Infeasibility_Localization_Audit"
R1_CSV="POSTV16_AV4_PIVOT_P2_R5_G2A_R1_CV_Slack_Diagnostics.csv"
R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Summary.json"
R1_STATUS=(
    "AV4PIVOTP2R5G2AR1_H2XY_PRIMARY_INFEASIBILITY_LOCALIZATION_"
    "AND_CONSERVATION_CUT_AUDIT_PASS_NO_REPAIR_EXECUTION"
)

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

OUT_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_BlockPath_Identity_Closure_and_Controlled_Projection"
FAIL_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_SCIENTIFIC_FAIL"
BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_BLOCKED"

R2SRC="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
E37A="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D="PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB="890088c0c0fcab415a2c7351c5079ca8ee12bf82"
A2E="PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB="79a8969233b72b4543edd382a0c3d1028c6dca09"
R3RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R3_ComponentFrontier_H2_Eligibility_Prospective_Repair_Semantics_Freeze.py"
R3RUN_BLOB="5cd10980c96313d71283bd600b342a25a1d7a1bc"
G1R1RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G1_R1_Alternative_Geometric_Domain_Candidate_Comparison_and_Freeze.py"
G1R1RUN_BLOB="fb459dd8a424eb21a9599669e5e7eb034ec5174f"
R4RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_Controlled_ComponentFrontier_H2_Exact_CVConservative_Projection_Execution.py"
R4RUN_BLOB="981514fe45caf4c6994d5ed78505b2b8d8dc1902"
R4R1RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_GlobalBaseline_H2_EdgeCount_Authority_Repair_and_Controlled_Projection_Execution.py"
R4R1RUN_BLOB="53aa32c8340344c9e421e58d33ecb7040d3d4d1e"

SOURCE_BLOBS={
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
    A2E:A2E_BLOB,
    R3RUN:R3RUN_BLOB,
    G1R1RUN:G1R1RUN_BLOB,
    R4RUN:R4RUN_BLOB,
    R4R1RUN:R4R1RUN_BLOB,
}


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self,gate:str,detail:Any=None):
        super().__init__(gate)
        self.gate=gate
        self.detail=detail


def git_text(root:Path,*args:str)->str:
    return subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE
    ).stdout.strip()


def load_json(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path:Path)->list[dict[str,str]]:
    with path.open("r",newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


def h2xy_cells_from_s0(s0:np.ndarray):
    s0_set=set(int(x) for x in s0.tolist())
    halo=set()
    parent_pairs=[]
    pair_distance={}
    for c in s0.tolist():
        k,j,i=ijk(int(c))
        for dj in range(-2,3):
            for di in range(-2,3):
                d=abs(di)+abs(dj)
                if not (1<=d<=2):continue
                jj=j+dj;ii=i+di
                if not (0<=jj<NY and 0<=ii<NX):continue
                h=flat_of(k,jj,ii)
                if h in s0_set:continue
                halo.add(h)
                parent_pairs.append((int(c),int(h)))
                pair_distance[(int(c),int(h))]=int(d)
    return np.asarray(sorted(halo),dtype=np.int64),parent_pairs,pair_distance


def self_test()->None:
    c=flat_of(5,20,20)
    h,p,d=h2xy_cells_from_s0(np.asarray([c],dtype=np.int64))
    assert len(h)==12
    assert all(ijk(int(x))[0]==5 for x in h)
    assert set(d.values())=={1,2}
    print("POSTV16 AV4 PIVOT P2-R5-G2A-R4-R1-R1 structural self-test: PASS")


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

    print("="*194)
    print("POSTV16-AV4-PIVOT-P2-R5-G2A-R4-R1-R1 -- BLOCK-PATH IDENTITY CLOSURE / CONTROLLED COMPONENT-FRONTIER PROJECTION")
    print("="*194)
    print("TECHNICAL BLOCK-PATH IDENTITY CLOSURE + EXECUTION. IMMUTABLE R4 AND R4-R1 BLOCKS PRESERVED; EXACT R3 MANIFESTS.")
    print("NO NEW CARTESIAN CELLS. NO VERTICAL SUPPORT. NO SIGN RELAXATION. NO PRESSURE REFRESH.")
    print("LEXICOGRAPHIC LP: (1) TOTAL H2 MASS, (2) NEW COMPLETION-EDGE MASS, (3) EXISTING-SUPPORT L1.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_Summary.json"
        fail_report=fail_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_Scientific_Fail_Report.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal R4 PASS already exists; immutable outcome preserved.")
            return 0
        if fail_report.is_file():
            print("[PASS] formal R4 SCIENTIFIC FAIL already exists; immutable outcome preserved.")
            return 3
        if block_report.is_file():
            print("[PASS] formal R4 BLOCK already exists; immutable outcome preserved.")
            return 2

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_blocked_R4R1_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,
             git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",
             repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="R4R1_block_binding"
        r4r1block=load_json(drive/R4R1_BLOCK_REL/R4R1_BLOCK_REPORT)
        gate("R4R1_block_status_exact",r4r1block.get("status")==R4R1_BLOCK_STATUS,r4r1block.get("status"))
        gate("R4R1_block_stage_exact",r4r1block.get("failed_stage")==R4R1_BLOCK_STAGE,r4r1block.get("failed_stage"))
        gate("R4R1_block_exception_exact",r4r1block.get("exception")==R4R1_BLOCK_EXCEPTION,r4r1block.get("exception"))
        gate("R4R1_block_scientific_execution_false",
             r4r1block.get("scientific_execution_started") is False,
             r4r1block.get("scientific_execution_started"))
        gate("R4R1_block_automatic_rerun_false",
             r4r1block.get("automatic_rerun_authorized") is False,
             r4r1block.get("automatic_rerun_authorized"))
        gate("R4R1_block_P2_R6_false",
             r4r1block.get("P2_R6_authorized") is False,
             r4r1block.get("P2_R6_authorized"))
        gate("R4R1_block_P3_false",
             r4r1block.get("P3_authorized") is False,
             r4r1block.get("P3_authorized"))

        stage="R4_block_binding"
        r4block=load_json(drive/R4_BLOCK_REL/R4_BLOCK_REPORT)
        gate("R4_block_status_exact",r4block.get("status")==R4_BLOCK_STATUS,r4block.get("status"))
        gate("R4_block_stage_exact",r4block.get("failed_stage")==R4_BLOCK_STAGE,r4block.get("failed_stage"))
        gate("R4_block_exception_exact",r4block.get("exception")==R4_BLOCK_EXCEPTION,r4block.get("exception"))
        gate("R4_block_scientific_execution_false",
             r4block.get("scientific_execution_started") is False,
             r4block.get("scientific_execution_started"))
        gate("R4_block_automatic_rerun_false",
             r4block.get("automatic_rerun_authorized") is False,
             r4block.get("automatic_rerun_authorized"))
        gate("R4_block_P2_R6_false",r4block.get("P2_R6_authorized") is False,r4block.get("P2_R6_authorized"))
        gate("R4_block_P3_false",r4block.get("P3_authorized") is False,r4block.get("P3_authorized"))

        stage="G1R1_global_H2_authority_binding"
        g1s=load_json(drive/G1R1_REL/G1R1_SUMMARY)
        gate("G1R1_status_exact",g1s.get("status")==G1R1_STATUS,g1s.get("status"))
        expected_global_baseline_H2_edges=int(g1s["candidates"]["H2_XY"]["candidate_upper_CV_halo_edge_count"])
        gate("G1R1_global_H2_edge_count_positive",expected_global_baseline_H2_edges>0,expected_global_baseline_H2_edges)
        gate("G1R1_global_count_exceeds_failed_component_history",
             expected_global_baseline_H2_edges>HISTORICAL_FAILED_COMPONENT_BASELINE_H2_EDGES,
             {"global":expected_global_baseline_H2_edges,
              "historical_failed_component":HISTORICAL_FAILED_COMPONENT_BASELINE_H2_EDGES})

        stage="R3_freeze_binding"
        r3dir=drive/R3_REL
        r3s=load_json(r3dir/R3_SUMMARY)
        r3d=load_json(r3dir/R3_DECISION)
        r3design=load_json(r3dir/R3_DESIGN)

        gate("R3_status_exact",r3s.get("status")==R3_STATUS,r3s.get("status"))
        gate("R3_milestone_exact",r3s.get("milestone")=="POSTV16-AV4-PIVOT-P2-R5-G2A-R3",r3s.get("milestone"))
        gate("R3_R4_authorized",
             r3d.get("P2_R5_G2A_R4_controlled_repair_execution_authorized") is True,
             r3d.get("P2_R5_G2A_R4_controlled_repair_execution_authorized"))
        gate("R3_R4_name_exact",r3d.get("P2_R5_G2A_R4_name")==R4_NAME,r3d.get("P2_R5_G2A_R4_name"))
        gate("R3_repair_not_executed",r3s.get("repair_executed") is False,r3s.get("repair_executed"))
        gate("R3_state_not_accepted",r3s.get("accepted_state_created") is False,r3s.get("accepted_state_created"))
        gate("R3_no_new_cells",int(r3s.get("new_cartesian_cell_count",-1))==0,r3s.get("new_cartesian_cell_count"))
        gate("R3_vertical_false",r3s.get("vertical_support_used") is False,r3s.get("vertical_support_used"))
        gate("R3_sign_rule_unchanged",r3s.get("existing_sign_rule_changed") is False,r3s.get("existing_sign_rule_changed"))
        gate("R3_P3_false",r3d.get("P3_authorized") is False,r3d.get("P3_authorized"))
        gate("R3_support_expansion_false",
             r3d.get("further_support_expansion_execution_authorized") is False,
             r3d.get("further_support_expansion_execution_authorized"))
        gate("R3_physics_relaxation_false",
             r3d.get("physics_relaxation_authorized") is False,
             r3d.get("physics_relaxation_authorized"))
        gate("R3_pressure_refresh_false",
             r3d.get("pressure_refresh_authorized") is False,
             r3d.get("pressure_refresh_authorized"))

        expected_objectives=[
            "1_minimize_total_H2_terminal_deposition_mass_over_baseline_plus_completion_edges",
            "2_within_stage1_optimum_minimize_total_mass_on_new_component_frontier_completion_edges",
            "3_within_stage1_and_stage2_optima_minimize_L1_deviation_of_existing_nonzero_culprit_CV_cell_contributions",
        ]
        gate("R3_objectives_exact",
             r3design.get("lexicographic_objective_for_successor")==expected_objectives,
             r3design.get("lexicographic_objective_for_successor"))

        target_path=r3dir/R3_TARGETS
        completion_path=r3dir/R3_COMPLETION
        target_sha=sha256_file(target_path)
        completion_sha=sha256_file(completion_path)
        gate("R3_target_manifest_SHA_summary_exact",
             target_sha==r3s.get("target_CV_manifest_sha256"),
             {"actual":target_sha,"summary":r3s.get("target_CV_manifest_sha256")})
        gate("R3_target_manifest_SHA_decision_exact",
             target_sha==r3d.get("target_CV_manifest_sha256"),
             {"actual":target_sha,"decision":r3d.get("target_CV_manifest_sha256")})
        gate("R3_completion_manifest_SHA_summary_exact",
             completion_sha==r3s.get("completion_edge_manifest_sha256"),
             {"actual":completion_sha,"summary":r3s.get("completion_edge_manifest_sha256")})
        gate("R3_completion_manifest_SHA_decision_exact",
             completion_sha==r3d.get("completion_edge_manifest_sha256"),
             {"actual":completion_sha,"decision":r3d.get("completion_edge_manifest_sha256")})

        target_rows=read_csv(target_path)
        completion_rows=read_csv(completion_path)
        target_cvs=np.asarray(sorted({int(r["cv_id"]) for r in target_rows}),dtype=np.int64)
        frozen_completion_edges=set((int(r["cv_id"]),int(r["halo_flat_cell"])) for r in completion_rows)
        gate("R3_target_CV_count_exact",len(target_cvs)==EXPECTED_TARGET_CVS,len(target_cvs))
        gate("R3_completion_edge_count_exact",len(frozen_completion_edges)==EXPECTED_COMPLETION_EDGES,len(frozen_completion_edges))

        stage="R1_target_authority_binding"
        r1dir=drive/R1_REL
        r1s=load_json(r1dir/R1_SUMMARY)
        r1rows=read_csv(r1dir/R1_CSV)
        gate("R1_status_exact",r1s.get("status")==R1_STATUS,r1s.get("status"))
        r1_slack_cvs=np.asarray(sorted({
            int(r["cv_id"]) for r in r1rows
            if float(r["absolute_conservation_slack_kg"])>1.0e-8
        }),dtype=np.int64)
        gate("R3_targets_equal_R1_slack_CVs",np.array_equal(target_cvs,r1_slack_cvs),
             {"R3":len(target_cvs),"R1":len(r1_slack_cvs)})

        stage="teacher_and_state_binding"
        rec=drive/R3_RECOVERY_REL
        state_path=rec/R3_TEACHER_STATE
        meta=load_json(rec/R3_TEACHER_META)
        gate("teacher_runner_blob_exact",meta.get("runner_blob")==R3_RUNNER_BLOB,meta.get("runner_blob"))
        gate("teacher_state_SHA_exact",meta.get("state_sha256")==sha256_file(state_path),meta.get("state_sha256"))
        with np.load(state_path,allow_pickle=False) as z:
            future_cv_mass=np.asarray(z["future_mass"],dtype=np.float64)
            future_cv_sat=np.asarray(z["future_saturation"],dtype=np.float64)
            injected_mass=float(np.asarray(z["injected_mass_kg"]).reshape(()))
            produced_mass=float(np.asarray(z["produced_mass_kg"]).reshape(()))

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

        stage="reconstruct_day370_mapback"
        r2=load_module(root/R2SRC,"av4_pivot_g2ar4_r2")
        e37=load_module(root/E37A,"av4_pivot_g2ar4_e37")
        sg7d=load_module(root/SG7D,"av4_pivot_g2ar4_sg7d")
        a2e=load_module(root/A2E,"av4_pivot_g2ar4_a2e")

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

        old_flat=parent_cv_sat.reshape(-1)
        new_flat=future_cv_sat.reshape(-1)
        old_sub=old_flat[cv_id];new_sub=new_flat[cv_id]
        old_sg=np.clip(old_sub-BACKGROUND,0.0,MAX_SG)
        new_sg=np.clip(new_sub-BACKGROUND,0.0,MAX_SG)
        rho_old=np.asarray(r2.gas_density_from_state(old_sub,pseg,p_ref),dtype=np.float64)
        rho_new=np.asarray(r2.gas_density_from_state(new_sub,pseg,p_ref),dtype=np.float64)
        sub_delta=pv*(rho_new*new_sg-rho_old*old_sg)

        cv_delta=(future_cv_mass-parent_cv_mass).reshape(-1)
        transfer=np.bincount(cv_id,weights=sub_delta,minlength=NSL*NCV)
        gate("per_CV_subsegment_transfer_closure",
             float(np.max(np.abs(transfer-cv_delta)))<=CV_EQUALITY_TOL_KG,
             float(np.max(np.abs(transfer-cv_delta))))

        key=cv_id.astype(np.int64)*NCELL+flat.astype(np.int64)
        order=np.argsort(key,kind="mergesort")
        key_s=key[order];val_s=sub_delta[order]
        starts=np.r_[0,1+np.flatnonzero(key_s[1:]!=key_s[:-1])]
        pair_key=key_s[starts]
        pair_val=np.add.reduceat(val_s,starts)
        pair_cv=(pair_key//NCELL).astype(np.int64)
        pair_cell=(pair_key%NCELL).astype(np.int64)

        original_cell_delta=np.bincount(pair_cell,weights=pair_val,minlength=NCELL)
        original_future=parent_grid_mass.reshape(-1)+original_cell_delta

        sat_max=np.full(GRID,BACKGROUND+MAX_SG,dtype=np.float64)
        rho_max=np.asarray(r2.gas_density_from_state(sat_max,parent_pressure,p_ref),dtype=np.float64)
        capacity=(grid_pv*rho_max*MAX_SG).reshape(-1)

        lower=original_future<-CELL_BOUND_TOL_KG
        upper=original_future>capacity+CELL_BOUND_TOL_KG
        lower_culprit=np.unique(pair_cv[lower[pair_cell]&(pair_val<-SIGN_TOL_KG)]).astype(np.int64)
        upper_culprit=np.unique(pair_cv[upper[pair_cell]&(pair_val>SIGN_TOL_KG)]).astype(np.int64)
        union_culprit=np.union1d(lower_culprit,upper_culprit).astype(np.int64)

        union_mask=np.zeros(NSL*NCV,dtype=bool);union_mask[union_culprit]=True
        upper_mask=np.zeros(NSL*NCV,dtype=bool);upper_mask[upper_culprit]=True
        gate("target_CVs_subset_original_upper_culprits",
             set(target_cvs.tolist()).issubset(set(upper_culprit.tolist())))

        existing_mask=union_mask[pair_cv]
        existing_cv=pair_cv[existing_mask]
        existing_cell=pair_cell[existing_mask]
        existing_val=pair_val[existing_mask]
        s0=np.unique(existing_cell)
        s0_set=set(int(x) for x in s0.tolist())

        halo,parent_pairs,parent_dist=h2xy_cells_from_s0(s0)
        halo_set=set(int(x) for x in halo.tolist())
        gate("H2_no_vertical",
             all(ijk(s)[0]==ijk(h)[0] for s,h in parent_pairs))
        gate("completion_cells_subset_frozen_H2",
             all(int(h) in halo_set for _,h in frozen_completion_edges))

        ex_nonzero=np.abs(existing_val)>SIGN_TOL_KG
        var_ex_cv=existing_cv[ex_nonzero]
        var_ex_cell=existing_cell[ex_nonzero]
        var_ex_x0=existing_val[ex_nonzero]

        # Original two-sided S0 components, used only to independently reproduce R3 completion edges.
        cv_local0={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local0={int(c):n for n,c in enumerate(s0.tolist())}
        d0=DSU(len(union_culprit)+len(s0));off0=len(union_culprit)
        for cv,cell in zip(existing_cv.tolist(),existing_cell.tolist()):
            d0.union(cv_local0[int(cv)],off0+cell_local0[int(cell)])
        orig_root_of_cv={int(cv):d0.find(cv_local0[int(cv)]) for cv in union_culprit.tolist()}
        orig_root_of_cell={int(c):d0.find(off0+cell_local0[int(c)]) for c in s0.tolist()}

        frontier_by_root={}
        frontier_dist={}
        for s,h in parent_pairs:
            rid=orig_root_of_cell[int(s)]
            frontier_by_root.setdefault(rid,set()).add(int(h))
            k=(rid,int(h))
            d=int(parent_dist[(int(s),int(h))])
            frontier_dist[k]=d if k not in frontier_dist else min(frontier_dist[k],d)

        # Baseline G2A H2 edges.
        upper_existing_mask=upper_mask[pair_cv]
        upper_existing_cv=pair_cv[upper_existing_mask]
        upper_existing_cell=pair_cell[upper_existing_mask]
        baseline_edges=set()
        baseline_dist={}
        for cv,cell in zip(upper_existing_cv.tolist(),upper_existing_cell.tolist()):
            k,j,i=ijk(int(cell))
            for dj in range(-2,3):
                for di in range(-2,3):
                    d=abs(di)+abs(dj)
                    if not (1<=d<=2):continue
                    jj=j+dj;ii=i+di
                    if not (0<=jj<NY and 0<=ii<NX):continue
                    h=flat_of(k,jj,ii)
                    if h not in halo_set:continue
                    e=(int(cv),int(h))
                    baseline_edges.add(e)
                    baseline_dist[e]=d if e not in baseline_dist else min(baseline_dist[e],d)

        # Independently reproduce R3 completion edges.
        reproduced_completion=set()
        for cv in target_cvs.tolist():
            rid=orig_root_of_cv[int(cv)]
            for h in frontier_by_root.get(rid,set()):
                if h in halo_set:
                    reproduced_completion.add((int(cv),int(h)))
        reproduced_completion-=baseline_edges

        gate("reproduced_completion_count_exact",
             len(reproduced_completion)==EXPECTED_COMPLETION_EDGES,len(reproduced_completion))
        gate("reproduced_completion_set_equals_R3_manifest",
             reproduced_completion==frozen_completion_edges,
             {"reproduced":len(reproduced_completion),"R3":len(frozen_completion_edges)})
        gate("baseline_completion_disjoint",
             len(baseline_edges & frozen_completion_edges)==0,
             len(baseline_edges & frozen_completion_edges))

        full_edges=sorted(baseline_edges|frozen_completion_edges)
        halo_cv=np.asarray([e[0] for e in full_edges],dtype=np.int64)
        halo_cell=np.asarray([e[1] for e in full_edges],dtype=np.int64)
        halo_is_completion=np.asarray([e in frozen_completion_edges for e in full_edges],dtype=bool)

        halo_dist=[]
        for e,is_comp in zip(full_edges,halo_is_completion.tolist()):
            if not is_comp:
                halo_dist.append(int(baseline_dist[e]))
            else:
                cv,h=e
                rid=orig_root_of_cv[int(cv)]
                halo_dist.append(int(frontier_dist[(rid,int(h))]))
        halo_dist=np.asarray(halo_dist,dtype=np.int64)

        gate("global_baseline_H2_edge_count_matches_G1R1",
             len(baseline_edges)==expected_global_baseline_H2_edges,
             {"R4R1":len(baseline_edges),"G1R1":expected_global_baseline_H2_edges})
        gate("full_H2_edge_count_exact",
             len(full_edges)==expected_global_baseline_H2_edges+EXPECTED_COMPLETION_EDGES,
             {"R4R1":len(full_edges),
              "expected":expected_global_baseline_H2_edges+EXPECTED_COMPLETION_EDGES})

        variable_existing_global=union_mask[pair_cv]&(np.abs(pair_val)>SIGN_TOL_KG)
        fixed_delta=np.bincount(
            pair_cell[~variable_existing_global],
            weights=pair_val[~variable_existing_global],
            minlength=NCELL,
        )
        fixed_mass=parent_grid_mass.reshape(-1)+fixed_delta

        stage="expanded_component_construction"
        all_cells=np.union1d(s0,halo).astype(np.int64)
        cv_local={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local={int(c):n for n,c in enumerate(all_cells.tolist())}
        dsu=DSU(len(union_culprit)+len(all_cells));off=len(union_culprit)

        for cv,cell in zip(existing_cv.tolist(),existing_cell.tolist()):
            dsu.union(cv_local[int(cv)],off+cell_local[int(cell)])
        for cv,h in full_edges:
            dsu.union(cv_local[int(cv)],off+cell_local[int(h)])

        roots=sorted({dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()})
        expanded_component_of_cv={int(cv):dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()}

        # Verify the authoritative failed G2A component is still identified by all target CVs.
        target_roots=sorted({expanded_component_of_cv[int(cv)] for cv in target_cvs.tolist()})
        gate("all_target_CVs_share_one_R4_component",len(target_roots)==1,target_roots)
        failed_root=target_roots[0]
        failed_cvs=np.asarray(
            [cv for cv in union_culprit.tolist() if expanded_component_of_cv[int(cv)]==failed_root],
            dtype=np.int64,
        )
        failed_ex_idx=np.flatnonzero(np.asarray(
            [expanded_component_of_cv[int(cv)]==failed_root for cv in var_ex_cv],dtype=bool
        ))
        failed_h_idx=np.flatnonzero(np.asarray(
            [expanded_component_of_cv[int(cv)]==failed_root for cv in halo_cv],dtype=bool
        ))
        failed_cells=np.unique(np.r_[var_ex_cell[failed_ex_idx],halo_cell[failed_h_idx]]).astype(np.int64)
        # CV/existing counts are preserved. Cell count may only stay the same because R3 added no cells.
        gate("failed_component_CV_count_exact",len(failed_cvs)==EXPECTED_FAILED_COMPONENT_CVS,len(failed_cvs))
        gate("failed_component_cell_count_exact",len(failed_cells)==EXPECTED_FAILED_COMPONENT_CELLS,len(failed_cells))
        gate("failed_component_existing_variable_count_exact",
             len(failed_ex_idx)==EXPECTED_FAILED_EXISTING_VARIABLES,len(failed_ex_idx))

        variable_cells=np.union1d(var_ex_cell,halo_cell)
        outside=np.ones(NCELL,dtype=bool);outside[variable_cells]=False
        immutable_lower=np.flatnonzero(outside&(fixed_mass<-CELL_BOUND_TOL_KG))
        immutable_upper=np.flatnonzero(outside&(fixed_mass>capacity+CELL_BOUND_TOL_KG))

        scientific_started=True
        sci_gate("outside_expanded_domain_lower_bounds_clean",len(immutable_lower)==0,int(len(immutable_lower)))
        sci_gate("outside_expanded_domain_upper_bounds_clean",len(immutable_upper)==0,int(len(immutable_upper)))

        stage="HiGHS_component_frontier_projection"
        try:
            from scipy.optimize import linprog
            from scipy import sparse
            import scipy
        except Exception as exc:
            raise GateError("scipy_HiGHS_unavailable:"+repr(exc)) from exc
        print("SciPy version:",scipy.__version__)

        repaired_ex=var_ex_x0.copy()
        repaired_halo=np.zeros(len(full_edges),dtype=np.float64)
        component_rows=[]

        total_stage1_min_halo=0.0
        total_accepted_halo=0.0
        total_stage2_min_completion=0.0
        total_accepted_completion=0.0
        total_existing_l1=0.0
        total_solver_s=0.0

        ex_root=np.asarray([expanded_component_of_cv[int(cv)] for cv in var_ex_cv],dtype=np.int64)
        h_root=np.asarray([expanded_component_of_cv[int(cv)] for cv in halo_cv],dtype=np.int64)

        for cid,root_id in enumerate(roots):
            comp_cvs=np.asarray(
                [cv for cv in union_culprit.tolist() if expanded_component_of_cv[int(cv)]==root_id],
                dtype=np.int64,
            )
            ex_idx=np.flatnonzero(ex_root==root_id)
            h_idx=np.flatnonzero(h_root==root_id)
            comp_cells=np.unique(np.r_[var_ex_cell[ex_idx],halo_cell[h_idx]]).astype(np.int64)

            n_ex=len(ex_idx);n_h=len(h_idx)
            if n_ex==0:
                raise ScientificFail(
                    "expanded_component_has_no_existing_variables",
                    {"component_id":cid,"CV_count":len(comp_cvs),"halo_edge_count":n_h},
                )

            cex_cv=var_ex_cv[ex_idx]
            cex_cell=var_ex_cell[ex_idx]
            cex_x0=var_ex_x0[ex_idx]
            ch_cv=halo_cv[h_idx]
            ch_cell=halo_cell[h_idx]
            ch_completion=halo_is_completion[h_idx]

            # z = [existing x, all H2 h, existing L1 aux y]
            nvar=n_ex+n_h+n_ex
            ix_x=slice(0,n_ex)
            ix_h=slice(n_ex,n_ex+n_h)
            ix_y=slice(n_ex+n_h,nvar)

            cv_row={int(cv):r for r,cv in enumerate(comp_cvs.tolist())}
            eq_r=[];eq_c=[];eq_v=[]
            for q,cv in enumerate(cex_cv.tolist()):
                eq_r.append(cv_row[int(cv)]);eq_c.append(q);eq_v.append(1.0)
            for q,cv in enumerate(ch_cv.tolist()):
                eq_r.append(cv_row[int(cv)]);eq_c.append(n_ex+q);eq_v.append(1.0)
            Aeq=sparse.coo_matrix(
                (np.asarray(eq_v),(np.asarray(eq_r),np.asarray(eq_c))),
                shape=(len(comp_cvs),nvar),
            ).tocsr()
            beq=cv_delta[comp_cvs]

            cell_row={int(c):r for r,c in enumerate(comp_cells.tolist())}
            cr=[];cc=[];cvv=[]
            for q,c in enumerate(cex_cell.tolist()):
                cr.append(cell_row[int(c)]);cc.append(q);cvv.append(1.0)
            for q,c in enumerate(ch_cell.tolist()):
                cr.append(cell_row[int(c)]);cc.append(n_ex+q);cvv.append(1.0)
            Acell=sparse.coo_matrix(
                (np.asarray(cvv),(np.asarray(cr),np.asarray(cc))),
                shape=(len(comp_cells),nvar),
            ).tocsr()

            bupper=capacity[comp_cells]-fixed_mass[comp_cells]
            blower=fixed_mass[comp_cells]

            rows=[];cols=[];vals=[];rhs=[]
            for q,x0 in enumerate(cex_x0.tolist()):
                r=len(rhs);rows.extend([r,r]);cols.extend([q,n_ex+n_h+q]);vals.extend([1.0,-1.0]);rhs.append(float(x0))
                r=len(rhs);rows.extend([r,r]);cols.extend([q,n_ex+n_h+q]);vals.extend([-1.0,-1.0]);rhs.append(float(-x0))
            Al1=sparse.coo_matrix(
                (np.asarray(vals),(np.asarray(rows),np.asarray(cols))),
                shape=(len(rhs),nvar),
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

            # Stage 1: minimize total H2 deposition over baseline + completion edges.
            c1=np.zeros(nvar,dtype=np.float64)
            if n_h:c1[n_ex:n_ex+n_h]=1.0
            t0=time.time()
            lp1=linprog(c1,A_ub=Abase,b_ub=bbase,A_eq=Aeq,b_eq=beq,
                        bounds=bounds,method="highs",options={"presolve":True})
            t1=float(time.time()-t0);total_solver_s+=t1
            if not lp1.success:
                raise ScientificFail(
                    "HiGHS_R4_stage1_total_H2_projection_infeasible_or_failed",
                    {"component_id":cid,"status":int(lp1.status),"message":str(lp1.message),
                     "CV_count":len(comp_cvs),"cell_count":len(comp_cells),
                     "existing_variable_count":n_ex,"H2_edge_count":n_h,
                     "completion_edge_count":int(np.sum(ch_completion))},
                )
            primary_raw=float(lp1.fun)
            sci_gate(f"component_{cid:04d}_stage1_objective_nonnegative",
                     primary_raw>=-1.0e-8,primary_raw)
            primary=max(0.0,primary_raw)
            p_tol=max(PRIMARY_ABS_TOL_KG,abs(primary)*PRIMARY_REL_TOL)

            primary_row=np.zeros(nvar,dtype=np.float64)
            if n_h:primary_row[n_ex:n_ex+n_h]=1.0
            A2=sparse.vstack([Abase,sparse.csr_matrix(primary_row.reshape(1,-1))],format="csr")
            b2=np.r_[bbase,primary+p_tol]

            # Stage 2: within stage-1 optimum, minimize mass on NEW completion edges.
            c2=np.zeros(nvar,dtype=np.float64)
            if n_h:
                comp_local=np.flatnonzero(ch_completion)
                if len(comp_local):
                    c2[n_ex+comp_local]=1.0
            t0=time.time()
            lp2=linprog(c2,A_ub=A2,b_ub=b2,A_eq=Aeq,b_eq=beq,
                        bounds=bounds,method="highs",options={"presolve":True})
            t2=float(time.time()-t0);total_solver_s+=t2
            if not lp2.success:
                raise ScientificFail(
                    "HiGHS_R4_stage2_completion_mass_minimization_infeasible_or_failed",
                    {"component_id":cid,"status":int(lp2.status),"message":str(lp2.message),
                     "stage1_minimum_H2_mass_kg":primary,"stage1_tolerance_kg":p_tol},
                )
            completion_raw=float(lp2.fun)
            sci_gate(f"component_{cid:04d}_stage2_objective_nonnegative",
                     completion_raw>=-1.0e-8,completion_raw)
            completion_min=max(0.0,completion_raw)
            c_tol=max(COMPLETION_ABS_TOL_KG,abs(completion_min)*COMPLETION_REL_TOL)

            completion_row=np.zeros(nvar,dtype=np.float64)
            if n_h:
                comp_local=np.flatnonzero(ch_completion)
                if len(comp_local):
                    completion_row[n_ex+comp_local]=1.0
            A3=sparse.vstack(
                [A2,sparse.csr_matrix(completion_row.reshape(1,-1))],
                format="csr",
            )
            b3=np.r_[b2,completion_min+c_tol]

            # Stage 3: within both envelopes, minimize original-support L1 deviation.
            c3=np.zeros(nvar,dtype=np.float64)
            c3[n_ex+n_h:]=1.0
            t0=time.time()
            lp3=linprog(c3,A_ub=A3,b_ub=b3,A_eq=Aeq,b_eq=beq,
                        bounds=bounds,method="highs",options={"presolve":True})
            t3=float(time.time()-t0);total_solver_s+=t3
            if not lp3.success:
                raise ScientificFail(
                    "HiGHS_R4_stage3_existing_support_L1_infeasible_or_failed",
                    {"component_id":cid,"status":int(lp3.status),"message":str(lp3.message),
                     "stage1_minimum_H2_mass_kg":primary,"stage1_tolerance_kg":p_tol,
                     "stage2_minimum_completion_mass_kg":completion_min,
                     "stage2_tolerance_kg":c_tol},
                )

            z=np.asarray(lp3.x,dtype=np.float64)
            x=z[ix_x];h=z[ix_h]
            repaired_ex[ex_idx]=x
            if n_h:repaired_halo[h_idx]=h

            halo_mass=float(np.sum(h))
            completion_mass=float(np.sum(h[ch_completion])) if n_h else 0.0
            l1=float(np.sum(np.abs(x-cex_x0)))
            cv_res=np.asarray(Aeq@z-beq).ravel()
            cell_mass=fixed_mass[comp_cells]+np.asarray(Acell@z).ravel()
            lower_v=max(0.0,-float(np.min(cell_mass)))
            upper_v=max(0.0,float(np.max(cell_mass-capacity[comp_cells])))
            sign_v=0.0
            for oldv,newv in zip(cex_x0,x):
                if oldv>0:sign_v=max(sign_v,max(0.0,-float(newv)))
                elif oldv<0:sign_v=max(sign_v,max(0.0,float(newv)))
            halo_neg=max(0.0,-float(np.min(h))) if n_h else 0.0

            sci_gate(f"component_{cid:04d}_CV_equality",
                     float(np.max(np.abs(cv_res)))<=CV_EQUALITY_TOL_KG,
                     float(np.max(np.abs(cv_res))))
            sci_gate(f"component_{cid:04d}_cell_lower",lower_v<=CELL_BOUND_TOL_KG,lower_v)
            sci_gate(f"component_{cid:04d}_cell_upper",upper_v<=CELL_BOUND_TOL_KG,upper_v)
            sci_gate(f"component_{cid:04d}_existing_sign",sign_v<=SIGN_TOL_KG,sign_v)
            sci_gate(f"component_{cid:04d}_H2_nonnegative",halo_neg<=SIGN_TOL_KG,halo_neg)
            sci_gate(f"component_{cid:04d}_stage1_envelope",
                     halo_mass<=primary+p_tol+1.0e-8,
                     {"accepted":halo_mass,"minimum":primary,"tol":p_tol})
            sci_gate(f"component_{cid:04d}_stage2_completion_envelope",
                     completion_mass<=completion_min+c_tol+1.0e-8,
                     {"accepted":completion_mass,"minimum":completion_min,"tol":c_tol})

            total_stage1_min_halo+=primary
            total_accepted_halo+=halo_mass
            total_stage2_min_completion+=completion_min
            total_accepted_completion+=completion_mass
            total_existing_l1+=l1

            component_rows.append({
                "component_id":int(cid),
                "CV_count":int(len(comp_cvs)),
                "cell_count":int(len(comp_cells)),
                "existing_variable_count":int(n_ex),
                "H2_edge_count":int(n_h),
                "completion_edge_count":int(np.sum(ch_completion)),
                "stage1_minimum_total_H2_mass_kg":primary,
                "accepted_total_H2_mass_kg":halo_mass,
                "stage2_minimum_completion_edge_mass_kg":completion_min,
                "accepted_completion_edge_mass_kg":completion_mass,
                "stage3_existing_support_L1_adjustment_kg":l1,
                "maximum_CV_equality_residual_kg":float(np.max(np.abs(cv_res))),
                "maximum_lower_bound_violation_kg":lower_v,
                "maximum_upper_bound_violation_kg":upper_v,
                "maximum_existing_sign_violation_kg":sign_v,
                "maximum_H2_negative_violation_kg":halo_neg,
                "stage1_runtime_s":t1,
                "stage2_runtime_s":t2,
                "stage3_runtime_s":t3,
            })

        stage="global_certification"
        repaired_existing_pair_val=pair_val.copy()
        var_ex_key=var_ex_cv.astype(np.int64)*NCELL+var_ex_cell.astype(np.int64)
        for k,newv in zip(var_ex_key.tolist(),repaired_ex.tolist()):
            loc=int(np.searchsorted(pair_key,int(k)))
            if loc>=len(pair_key) or int(pair_key[loc])!=int(k):
                raise GateError(f"existing_variable_pair_key_not_found:{k}")
            repaired_existing_pair_val[loc]=float(newv)

        repaired_cell_delta=np.bincount(
            pair_cell,weights=repaired_existing_pair_val,minlength=NCELL
        )
        if len(full_edges):
            repaired_cell_delta+=np.bincount(
                halo_cell,weights=repaired_halo,minlength=NCELL
            )
        repaired_grid_mass=parent_grid_mass.reshape(-1)+repaired_cell_delta

        repaired_cv_transfer=np.bincount(
            pair_cv,weights=repaired_existing_pair_val,minlength=NSL*NCV
        )
        if len(full_edges):
            repaired_cv_transfer+=np.bincount(
                halo_cv,weights=repaired_halo,minlength=NSL*NCV
            )
        repaired_cv_res=repaired_cv_transfer-cv_delta

        min_mass=float(np.min(repaired_grid_mass))
        max_excess=float(np.max(repaired_grid_mass-capacity))
        global_target=float(np.sum(parent_grid_mass)+np.sum(cv_delta))
        global_res=float(np.sum(repaired_grid_mass)-global_target)

        sci_gate("global_per_CV_conservation",
                 float(np.max(np.abs(repaired_cv_res)))<=CV_EQUALITY_TOL_KG,
                 float(np.max(np.abs(repaired_cv_res))))
        sci_gate("global_nonnegative_cell_mass",
                 min_mass>=-CELL_BOUND_TOL_KG,min_mass)
        sci_gate("global_cell_capacity",
                 max_excess<=CELL_BOUND_TOL_KG,max_excess)
        sci_gate("global_mass_ledger",
                 abs(global_res)<=GLOBAL_LEDGER_TOL_KG,global_res)

        changed_existing=np.abs(repaired_existing_pair_val-pair_val)>1.0e-10
        changed_nonculprit=np.any(changed_existing&(~union_mask[pair_cv]))
        sign_bad=np.any(
            ((pair_val>SIGN_TOL_KG)&(repaired_existing_pair_val<-SIGN_TOL_KG))
            |((pair_val<-SIGN_TOL_KG)&(repaired_existing_pair_val>SIGN_TOL_KG))
        )
        zero_bad=np.any(
            (np.abs(pair_val)<=SIGN_TOL_KG)&
            (np.abs(repaired_existing_pair_val)>SIGN_TOL_KG)
        )
        sci_gate("nonculprit_existing_pairs_unchanged",not changed_nonculprit,bool(changed_nonculprit))
        sci_gate("existing_pair_sign_preserved_globally",not sign_bad,bool(sign_bad))
        sci_gate("existing_zero_pairs_remain_zero",not zero_bad,bool(zero_bad))
        sci_gate("all_H2_edges_nonnegative_globally",
                 float(np.min(repaired_halo))>=-SIGN_TOL_KG if len(repaired_halo) else True,
                 float(np.min(repaired_halo)) if len(repaired_halo) else 0.0)
        sci_gate("completion_edges_are_exact_R3_manifest",
                 set(e for e,flag in zip(full_edges,halo_is_completion.tolist()) if flag)==frozen_completion_edges,
                 int(np.sum(halo_is_completion)))

        try:
            repaired_sg=a2e.invert_local_mass(
                r2,repaired_grid_mass.reshape(GRID),parent_pressure,p_ref,grid_pv
            )
        except Exception as exc:
            raise ScientificFail("repaired_grid_mass_inversion_failure",repr(exc)) from exc

        repaired_sat=BACKGROUND+np.asarray(repaired_sg,dtype=np.float64)
        sci_gate("repaired_grid_saturation_bounds",
                 float(np.min(repaired_sat))>=BACKGROUND-1.0e-10
                 and float(np.max(repaired_sat))<=BACKGROUND+MAX_SG+1.0e-10,
                 [float(np.min(repaired_sat)),float(np.max(repaired_sat))])

        stage="artifact_publication"
        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_Final_Artifacts"
        if local.exists():shutil.rmtree(local)
        local.mkdir(parents=True)
        plots=local/"plots";plots.mkdir()

        used=repaired_halo>1.0e-9
        used_baseline=used&(~halo_is_completion)
        used_completion=used&halo_is_completion
        used_cells=np.unique(halo_cell[used]) if np.any(used) else np.asarray([],dtype=np.int64)

        fig=plt.figure(figsize=(7,5))
        ax=fig.add_subplot(111)
        ax.scatter(original_future[variable_cells],repaired_grid_mass[variable_cells],s=8,alpha=0.35)
        lo=min(float(np.min(original_future[variable_cells])),float(np.min(repaired_grid_mass[variable_cells])))
        hi=max(float(np.max(original_future[variable_cells])),float(np.max(repaired_grid_mass[variable_cells])))
        ax.plot([lo,hi],[lo,hi],linestyle="--")
        ax.axhline(0.0,linewidth=0.8)
        ax.set_xlabel("Original Day370 cell mass (kg)")
        ax.set_ylabel("R4 repaired Day370 cell mass (kg)")
        ax.set_title("Component-frontier H2 exact projection")
        ax.grid(True,alpha=0.25)
        fig.savefig(plots/"R4_original_vs_repaired_cell_mass.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        fig=plt.figure(figsize=(8,6))
        ax=fig.add_subplot(111,projection="3d")
        if len(used_cells):
            k=used_cells//(NY*NX);rr=used_cells%(NY*NX);j=rr//NX;i=rr%NX
            ax.scatter(i,j,k,s=10,alpha=0.5)
        ax.set_xlim(0,NX-1);ax.set_ylim(0,NY-1);ax.set_zlim(0,NZ-1)
        ax.set_xlabel("i");ax.set_ylabel("j");ax.set_zlabel("k")
        ax.view_init(elev=24,azim=-58)
        ax.set_title("R4 H2 cells receiving positive projected mass")
        fig.savefig(plots/"3D_R4_used_H2_cells.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        used_rows=[]
        for q,(cv,cell) in enumerate(full_edges):
            if repaired_halo[q]<=1.0e-12:continue
            k,j,i=ijk(int(cell))
            used_rows.append({
                "cv_id":int(cv),
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
                "flat_cell":int(cell),
                "k":int(k),"j":int(j),"i":int(i),
                "H2_distance":int(halo_dist[q]),
                "edge_kind":"completion" if bool(halo_is_completion[q]) else "baseline",
                "repaired_H2_contribution_kg":float(repaired_halo[q]),
            })

        state_path=local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_Repaired_Day370_State.npz"
        with state_path.open("wb") as fp:
            np.savez_compressed(
                fp,
                day=np.asarray(370.0),
                cv_component_mass_kg=future_cv_mass,
                cv_saturation=future_cv_sat,
                grid_component_mass_kg=repaired_grid_mass.reshape(GRID),
                grid_saturation=repaired_sat,
                parent_pressure_psi=parent_pressure,
                existing_pair_cv=pair_cv,
                existing_pair_cell=pair_cell,
                original_existing_pair_contribution_kg=pair_val,
                repaired_existing_pair_contribution_kg=repaired_existing_pair_val,
                halo_cv=halo_cv,
                halo_cell=halo_cell,
                halo_distance=halo_dist,
                halo_is_completion=halo_is_completion,
                repaired_halo_contribution_kg=repaired_halo,
                completion_target_cv=target_cvs,
                lower_culprit_cv=lower_culprit,
                upper_culprit_cv=upper_culprit,
                union_culprit_cv=union_culprit,
                injected_mass_kg=np.asarray(injected_mass),
                produced_mass_kg=np.asarray(produced_mass),
                R3_target_manifest_sha256=np.asarray(target_sha),
                R3_completion_manifest_sha256=np.asarray(completion_sha),
            )
        state_sha=sha256_file(state_path)

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "blocked_R4_preserved":True,
            "blocked_R4_R1_preserved":True,
            "block_path_identity_closure":True,
            "technical_repair":"block_path_identity_closure_plus_global_baseline_H2_edge_count_authority_repair",
            "G1R1_global_baseline_H2_edge_count":int(expected_global_baseline_H2_edges),
            "historical_failed_component_baseline_H2_edge_count":int(HISTORICAL_FAILED_COMPONENT_BASELINE_H2_EDGES),
            "target_CV_count":int(len(target_cvs)),
            "baseline_H2_edge_count":int(len(baseline_edges)),
            "completion_edge_count":int(len(frozen_completion_edges)),
            "total_H2_edge_count":int(len(full_edges)),
            "expanded_component_count":int(len(roots)),
            "existing_projection_variable_count":int(len(var_ex_x0)),
            "stage1_sum_minimum_total_H2_mass_kg":float(total_stage1_min_halo),
            "accepted_total_H2_mass_kg":float(total_accepted_halo),
            "stage2_sum_minimum_completion_edge_mass_kg":float(total_stage2_min_completion),
            "accepted_completion_edge_mass_kg":float(total_accepted_completion),
            "stage3_existing_support_L1_adjustment_kg":float(total_existing_l1),
            "used_baseline_H2_edge_count":int(np.sum(used_baseline)),
            "used_completion_H2_edge_count":int(np.sum(used_completion)),
            "used_H2_cell_count":int(len(used_cells)),
            "maximum_per_CV_conservation_residual_kg":float(np.max(np.abs(repaired_cv_res))),
            "minimum_repaired_grid_mass_kg":min_mass,
            "maximum_repaired_capacity_excess_kg":max_excess,
            "global_mass_residual_kg":global_res,
            "repaired_grid_saturation_min":float(np.min(repaired_sat)),
            "repaired_grid_saturation_max":float(np.max(repaired_sat)),
            "original_lower_violation_count":int(np.sum(lower)),
            "original_upper_violation_count":int(np.sum(upper)),
            "repaired_lower_violation_count":int(np.sum(repaired_grid_mass<-CELL_BOUND_TOL_KG)),
            "repaired_upper_violation_count":int(np.sum(repaired_grid_mass>capacity+CELL_BOUND_TOL_KG)),
            "R3_target_manifest_sha256":target_sha,
            "R3_completion_manifest_sha256":completion_sha,
            "accepted_state_sha256":state_sha,
            "new_cartesian_cell_count":0,
            "vertical_support_used":False,
            "diagonal_support_used":False,
            "halo_transit_used":False,
            "negative_withdrawal_H2_edges_used":False,
            "existing_sign_rule_changed":False,
            "pressure_refresh_executed":False,
            "P3_authorized":False,
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "accepted_repaired_day370_state_sha256":state_sha,
            "P2_R6_authorized":True,
            "P2_R6_name":"Dense Day370-to-Day500 Frozen-Flow Snapshot Continuation with Frozen Component-Frontier H2 Eligibility Projection Semantics",
            "P3_authorized":False,
            "periodic_cadence_selected_now":False,
            "R3R6R1_execution_invalidated":False,
            "frozen_projection_semantics":{
                "H2_cell_domain":"same-layer Manhattan distance 1 or 2 from S0; no new cells",
                "target_CVs":"exact 327-CV R3 target manifest",
                "baseline_H2_edges":"preserved",
                "completion_edges":"exact 46,915-edge R3 component-frontier manifest",
                "completion_edges_nonnegative_deposition_only":True,
                "negative_withdrawal_H2_edges":False,
                "vertical_support":False,
                "diagonal_support":False,
                "halo_transit":False,
                "existing_nonzero_pair_sign_preservation":True,
                "existing_zero_pairs_remain_zero":True,
                "nonculprit_existing_pairs_unchanged":True,
                "stage1_objective":"minimum total H2 terminal-deposition mass",
                "stage2_objective":"minimum mass on R3 completion edges within stage1 envelope",
                "stage3_objective":"minimum L1 deviation of existing nonzero culprit CV-cell contributions within stage1 and stage2 envelopes",
                "exact_per_CV_mass_conservation":True,
                "physical_cell_lower_upper_mass_bounds":True,
                "pressure_refresh":False,
            },
        }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_Component_Solver_Audit.csv").write_bytes(csv_bytes(component_rows))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_Used_H2_Contributions.csv").write_bytes(csv_bytes(used_rows))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists():raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*194)
        print("POSTV16-AV4-PIVOT-P2-R5-G2A-R4-R1-R1: PASS")
        print("Target CVs                               :",len(target_cvs))
        print("Global baseline / completion / total H2  :",len(baseline_edges),"/",len(frozen_completion_edges),"/",len(full_edges))
        print("Stage1 minimum H2 mass kg                :",total_stage1_min_halo)
        print("Accepted H2 mass kg                      :",total_accepted_halo)
        print("Stage2 minimum completion mass kg        :",total_stage2_min_completion)
        print("Accepted completion mass kg              :",total_accepted_completion)
        print("Stage3 existing-support L1 kg            :",total_existing_l1)
        print("Used baseline / completion H2 edges      :",int(np.sum(used_baseline)),"/",int(np.sum(used_completion)))
        print("Minimum repaired grid mass kg            :",min_mass)
        print("Maximum repaired capacity excess kg      :",max_excess)
        print("Maximum per-CV residual kg               :",float(np.max(np.abs(repaired_cv_res))))
        print("Global mass residual kg                  :",global_res)
        print("Accepted Day370 state SHA256             :",state_sha)
        print("P2-R6 authorized                         : True")
        print("P3 authorized                            : False")
        print("="*194)
        return 0

    except ScientificFail as exc:
        fail_dir.mkdir(parents=True,exist_ok=True)
        p=fail_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_FAIL,
                "failed_stage":stage,
                "failed_gate":exc.gate,
                "detail":exc.detail,
                "scientific_execution_started":scientific_started,
                "automatic_rerun_authorized":False,
                "further_support_expansion_authorized":False,
                "physics_relaxation_authorized":False,
                "pressure_refresh_authorized":False,
                "P2_R6_authorized":False,
                "P3_authorized":False,
                "R3R6R1_execution_invalidated":False,
            },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(MILESTONE+": SCIENTIFIC FAIL")
        print("Stage:",stage)
        print("Gate:",exc.gate)
        print("Detail:",exc.detail)
        return 3

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "scientific_execution_started":scientific_started,
                "automatic_rerun_authorized":False,
                "P2_R6_authorized":False,
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
