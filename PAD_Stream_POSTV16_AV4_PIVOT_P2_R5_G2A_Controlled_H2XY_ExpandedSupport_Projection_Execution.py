#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
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


MILESTONE = "POSTV16-AV4-PIVOT-P2-R5-G2A"
STATUS_PASS = (
    "AV4PIVOTP2R5G2A_CONTROLLED_H2XY_EXPANDED_SUPPORT_CV_CONSERVATIVE_"
    "CELL_BOUNDED_PROJECTION_EXECUTION_PASS"
)
STATUS_FAIL = (
    "AV4PIVOTP2R5G2A_H2XY_EXPANDED_SUPPORT_PROJECTION_SCIENTIFIC_FAIL_"
    "NO_RELAXATION_OR_AUTOMATIC_RERUN_AUTHORIZED"
)
STATUS_BLOCKED = "AV4PIVOTP2R5G2A_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "9a06f6564104106686ad10e8a21a8ca742e33815"
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

CV_EQUALITY_TOL_KG = 1.0e-7
CELL_BOUND_TOL_KG = 1.0e-7
GLOBAL_LEDGER_TOL_KG = 1.0e-6
SIGN_TOL_KG = 1.0e-10
PRIMARY_ABS_TOL_KG = 1.0e-7
PRIMARY_REL_TOL = 1.0e-11
SECONDARY_ABS_TOL_KG = 1.0e-7
SECONDARY_REL_TOL = 1.0e-11

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

G1R1_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_G1_R1_Alternative_Geometric_Domain_Freeze"
G1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G1_R1_Summary.json"
G1R1_DECISION = "POSTV16_AV4_PIVOT_P2_R5_G1_R1_Decision_Contract.json"
G1R1_DESIGN = "POSTV16_AV4_PIVOT_P2_R5_G1_R1_Design_Contract.json"
G1R1_STATUS = (
    "AV4PIVOTP2R5G1R1_ALTERNATIVE_GEOMETRIC_DOMAIN_CANDIDATE_"
    "COMPARISON_AND_FREEZE_PASS_NO_SUPPORT_EXPANSION_EXECUTED"
)
SELECTED = "H2_XY_TWO_RING_SAME_LAYER_TERMINAL_OCCUPANCY_ENVELOPE"

R1_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_R1_TwoSided_Bound_Culprit_Domain_Freeze"
R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_R1_Summary.json"

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

OUT_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_G2A_Controlled_H2XY_ExpandedSupport_Projection"
FAIL_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_G2A_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_G2A_BLOCKED"

R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
G1R1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G1_R1_Alternative_Geometric_Domain_Candidate_Comparison_and_Freeze.py"
G1R1_RUNNER_BLOB = "fb459dd8a424eb21a9599669e5e7eb034ec5174f"

SOURCE_BLOBS = {
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
    A2E:A2E_BLOB,
    G1R1_RUNNER:G1R1_RUNNER_BLOB,
}


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate:str, detail:Any=None):
        super().__init__(gate)
        self.gate=gate
        self.detail=detail


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
    k=flat//(NY*NX)
    rem=flat%(NY*NX)
    j=rem//NX
    i=rem%NX
    return k,j,i


def flat_of(k:int,j:int,i:int)->int:
    return k*(NY*NX)+j*NX+i


def h2xy_cells_from_s0(s0:np.ndarray)->tuple[np.ndarray,set[tuple[int,int]],dict[tuple[int,int],int]]:
    s0_set=set(int(x) for x in s0.tolist())
    halo=set()
    parent_pairs=set()
    pair_distance={}
    for c in s0.tolist():
        k,j,i=ijk(int(c))
        for dj in range(-2,3):
            for di in range(-2,3):
                d=abs(di)+abs(dj)
                if not (1<=d<=2):
                    continue
                jj=j+dj;ii=i+di
                if not (0<=jj<NY and 0<=ii<NX):
                    continue
                nb=flat_of(k,jj,ii)
                if nb in s0_set:
                    continue
                halo.add(nb)
                parent_pairs.add((int(c),int(nb)))
                pair_distance[(int(c),int(nb))]=int(d)
    return np.asarray(sorted(halo),dtype=np.int64),parent_pairs,pair_distance


def self_test()->None:
    c=flat_of(5,20,20)
    h,p,d=h2xy_cells_from_s0(np.asarray([c],dtype=np.int64))
    assert len(h)==12
    assert all(ijk(int(x))[0]==5 for x in h)
    assert set(d.values())=={1,2}
    print("POSTV16 AV4 PIVOT P2-R5-G2A structural self-test: PASS")


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
    print("POSTV16-AV4-PIVOT-P2-R5-G2A -- CONTROLLED H2-XY EXPANDED-SUPPORT CV-CONSERVATIVE PROJECTION EXECUTION")
    print("="*194)
    print("EXECUTION MILESTONE. H2-XY SAME-LAYER TERMINAL OCCUPANCY ONLY.")
    print("NO VERTICAL SUPPORT. NO DIAGONALS. NO HALO TRANSIT. NO REVERSE HALO EDGES.")
    print("NEW HALO EDGES ARE NONNEGATIVE DEPOSITION ONLY. NO NEGATIVE-WITHDRAWAL HALO EDGES.")
    print("LEXICOGRAPHIC LP: MINIMIZE HALO MASS, THEN MINIMIZE ORIGINAL-SUPPORT L1 DEVIATION.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_Summary.json"
        fail_report=fail_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_Scientific_Fail_Report.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal G2A PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_G2A_FAIL",not fail_report.exists(),str(fail_report))
        gate("no_preexisting_G2A_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_G1R1_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="G1R1_binding"
        gdir=drive/G1R1_REL
        gs=load_json(gdir/G1R1_SUMMARY)
        gd=load_json(gdir/G1R1_DECISION)
        gdesign=load_json(gdir/G1R1_DESIGN)
        gate("G1R1_status_exact",gs.get("status")==G1R1_STATUS,gs.get("status"))
        gate("G1R1_selected_candidate_exact",gs.get("selected_candidate")==SELECTED,gs.get("selected_candidate"))
        gate("G1R1_execution_authorized",gd.get("P2_R5_G2A_controlled_selected_domain_LP_authorized") is True,gd.get("P2_R5_G2A_controlled_selected_domain_LP_authorized"))
        gate("G1R1_support_expansion_execution_authorized",gd.get("support_expansion_execution_authorized") is True,gd.get("support_expansion_execution_authorized"))
        gate("G1R1_further_design_not_authorized",gd.get("further_geometric_domain_design_authorized") is False,gd.get("further_geometric_domain_design_authorized"))
        gate("G1R1_P3_unauthorized",gd.get("P3_authorized") is False,gd.get("P3_authorized"))
        gate("G1R1_H2XY_necessary_capacity_pass",gs["candidates"]["H2_XY"]["necessary_capacity_candidate_pass"] is True,gs["candidates"]["H2_XY"]["necessary_capacity_candidate_pass"])
        gate("G1R1_H2XY_vertical_false",gdesign["H2_XY"]["vertical_neighbors"] is False,gdesign["H2_XY"]["vertical_neighbors"])
        gate("G1R1_negative_halo_withdrawal_false",gdesign["negative_withdrawal_halo_edges_allowed"] is False,gdesign["negative_withdrawal_halo_edges_allowed"])

        stage="R5R1_binding"
        r1s=load_json(drive/R1_REL/R1_SUMMARY)
        gate("R5R1_parent_clean",
             int(r1s["day365_parent_lower_violation_count"])==0
             and int(r1s["day365_parent_upper_violation_count"])==0,
             [r1s["day365_parent_lower_violation_count"],r1s["day365_parent_upper_violation_count"]])

        stage="R3_teacher_binding"
        rec=drive/R3_RECOVERY_REL
        state_path=rec/R3_TEACHER_STATE
        meta=load_json(rec/R3_TEACHER_META)
        gate("R3_teacher_runner_blob_exact",meta.get("runner_blob")==R3_RUNNER_BLOB,meta.get("runner_blob"))
        gate("R3_teacher_state_SHA_exact",meta.get("state_sha256")==sha256_file(state_path),meta.get("state_sha256"))
        with np.load(state_path,allow_pickle=False) as z:
            future_cv_mass=np.asarray(z["future_mass"],dtype=np.float64)
            future_cv_sat=np.asarray(z["future_saturation"],dtype=np.float64)
            injected_mass=float(np.asarray(z["injected_mass_kg"]).reshape(()))
            produced_mass=float(np.asarray(z["produced_mass_kg"]).reshape(()))

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

        stage="reconstruct_day370_mapback"
        r2=load_module(root/R2SRC,"av4_pivot_g2a_r2")
        e37=load_module(root/E37A,"av4_pivot_g2a_e37")
        sg7d=load_module(root/SG7D,"av4_pivot_g2a_sg7d")
        a2e=load_module(root/A2E,"av4_pivot_g2a_a2e")

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
        sci_gate("per_CV_subsegment_transfer_closure",
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

        lower=original_future < -CELL_BOUND_TOL_KG
        upper=original_future > capacity + CELL_BOUND_TOL_KG
        lower_culprit=np.unique(pair_cv[lower[pair_cell] & (pair_val<-SIGN_TOL_KG)]).astype(np.int64)
        upper_culprit=np.unique(pair_cv[upper[pair_cell] & (pair_val>SIGN_TOL_KG)]).astype(np.int64)
        union_culprit=np.union1d(lower_culprit,upper_culprit).astype(np.int64)
        gate("two_sided_union_count_reproduces_R5R1",
             len(union_culprit)==int(r1s["two_sided_union_culprit_CV_count"]),
             {"G2A":len(union_culprit),"R5R1":r1s["two_sided_union_culprit_CV_count"]})

        union_mask=np.zeros(NSL*NCV,dtype=bool);union_mask[union_culprit]=True
        upper_mask=np.zeros(NSL*NCV,dtype=bool);upper_mask[upper_culprit]=True

        existing_support_mask=union_mask[pair_cv]
        existing_cv=pair_cv[existing_support_mask]
        existing_cell=pair_cell[existing_support_mask]
        existing_val=pair_val[existing_support_mask]
        s0=np.unique(existing_cell)

        halo,parent_pairs,parent_dist=h2xy_cells_from_s0(s0)
        halo_set=set(int(x) for x in halo.tolist())
        gate("H2XY_halo_count_reproduces_G1R1",
             len(halo)==int(gs["candidates"]["H2_XY"]["halo_cell_count"]),
             {"G2A":len(halo),"G1R1":gs["candidates"]["H2_XY"]["halo_cell_count"]})
        gate("H2XY_no_vertical",
             all(ijk(s)[0]==ijk(h)[0] for s,h in parent_pairs))

        # Existing nonzero culprit pairs are variables; existing zeros remain frozen zero.
        ex_nonzero=np.abs(existing_val)>SIGN_TOL_KG
        var_ex_cv=existing_cv[ex_nonzero]
        var_ex_cell=existing_cell[ex_nonzero]
        var_ex_x0=existing_val[ex_nonzero]

        # New CV->halo edges: upper culprit CV only, and only via the H2 envelope of one of its existing S0 cells.
        upper_existing_mask=upper_mask[pair_cv]
        upper_existing_cv=pair_cv[upper_existing_mask]
        upper_existing_cell=pair_cell[upper_existing_mask]
        halo_edge_set=set()
        halo_edge_dist={}
        s0_set=set(int(x) for x in s0.tolist())
        for cv,cell in zip(upper_existing_cv.tolist(),upper_existing_cell.tolist()):
            k,j,i=ijk(int(cell))
            for dj in range(-2,3):
                for di in range(-2,3):
                    d=abs(di)+abs(dj)
                    if not (1<=d<=2):
                        continue
                    jj=j+dj;ii=i+di
                    if not (0<=jj<NY and 0<=ii<NX):
                        continue
                    h=flat_of(k,jj,ii)
                    if h not in halo_set:
                        continue
                    edge=(int(cv),int(h))
                    halo_edge_set.add(edge)
                    old=halo_edge_dist.get(edge)
                    halo_edge_dist[edge]=d if old is None else min(old,d)

        halo_edges=sorted(halo_edge_set)
        halo_cv=np.asarray([x[0] for x in halo_edges],dtype=np.int64)
        halo_cell=np.asarray([x[1] for x in halo_edges],dtype=np.int64)
        halo_dist=np.asarray([halo_edge_dist[x] for x in halo_edges],dtype=np.int64)
        gate("candidate_upper_CV_H2_edge_count_reproduces_G1R1",
             len(halo_edges)==int(gs["candidates"]["H2_XY"]["candidate_upper_CV_halo_edge_count"]),
             {"G2A":len(halo_edges),"G1R1":gs["candidates"]["H2_XY"]["candidate_upper_CV_halo_edge_count"]})

        # Fixed contribution = every pair outside nonzero culprit variables.
        variable_existing_global_mask=union_mask[pair_cv] & (np.abs(pair_val)>SIGN_TOL_KG)
        fixed_delta=np.bincount(
            pair_cell[~variable_existing_global_mask],
            weights=pair_val[~variable_existing_global_mask],
            minlength=NCELL,
        )
        fixed_mass=parent_grid_mass.reshape(-1)+fixed_delta

        # Expanded graph components over culprit CVs, original support cells, and H2 halo cells.
        stage="expanded_component_construction"
        all_cells=np.union1d(s0,halo).astype(np.int64)
        cv_local={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local={int(c):n for n,c in enumerate(all_cells.tolist())}
        dsu=DSU(len(union_culprit)+len(all_cells))
        off=len(union_culprit)

        # Include every existing support incidence, including zero-valued support, to preserve graph topology.
        for cv,cell in zip(existing_cv.tolist(),existing_cell.tolist()):
            dsu.union(cv_local[int(cv)],off+cell_local[int(cell)])
        for cv,cell in halo_edges:
            dsu.union(cv_local[int(cv)],off+cell_local[int(cell)])

        roots=sorted({dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()})
        expanded_component_of_cv={int(cv):dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()}

        print("Expanded components :",len(roots))
        print("Existing variables  :",len(var_ex_x0))
        print("New H2 halo edges   :",len(halo_edges))

        # Cells outside expanded variable domain must already be valid.
        variable_cells=np.union1d(var_ex_cell,halo_cell)
        outside=np.ones(NCELL,dtype=bool);outside[variable_cells]=False
        immutable_lower=np.flatnonzero(outside & (fixed_mass < -CELL_BOUND_TOL_KG))
        immutable_upper=np.flatnonzero(outside & (fixed_mass > capacity + CELL_BOUND_TOL_KG))
        scientific_started=True
        sci_gate("outside_expanded_domain_lower_bounds_clean",len(immutable_lower)==0,int(len(immutable_lower)))
        sci_gate("outside_expanded_domain_upper_bounds_clean",len(immutable_upper)==0,int(len(immutable_upper)))

        stage="HiGHS_expanded_component_projection"
        try:
            from scipy.optimize import linprog
            from scipy import sparse
            import scipy
        except Exception as exc:
            raise GateError("scipy_HiGHS_unavailable:"+repr(exc)) from exc
        print("SciPy version      :",scipy.__version__)

        repaired_ex=var_ex_x0.copy()
        repaired_halo=np.zeros(len(halo_edges),dtype=np.float64)
        component_rows=[]
        total_primary_halo=0.0
        total_secondary_l1=0.0
        total_solver_s=0.0

        # Pre-index variables by expanded component root.
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
                raise ScientificFail("expanded_component_has_no_existing_variables",
                                     {"component_id":cid,"CV_count":len(comp_cvs),"halo_edge_count":n_h})

            cex_cv=var_ex_cv[ex_idx]
            cex_cell=var_ex_cell[ex_idx]
            cex_x0=var_ex_x0[ex_idx]
            ch_cv=halo_cv[h_idx]
            ch_cell=halo_cell[h_idx]

            # z=[existing x (n_ex), halo h (n_h), existing L1 aux y (n_ex)]
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
                (np.asarray(eq_v), (np.asarray(eq_r),np.asarray(eq_c))),
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

            # upper/lower cell bounds
            Aupper=Acell
            bupper=capacity[comp_cells]-fixed_mass[comp_cells]
            Alower=-Acell
            blower=fixed_mass[comp_cells]

            # L1 aux for existing variables only.
            rows=[];cols=[];vals=[];rhs=[]
            for q,x0 in enumerate(cex_x0.tolist()):
                # x - y <= x0
                r=len(rhs); rows.extend([r,r]);cols.extend([q,n_ex+n_h+q]);vals.extend([1.0,-1.0]);rhs.append(float(x0))
                # -x - y <= -x0
                r=len(rhs); rows.extend([r,r]);cols.extend([q,n_ex+n_h+q]);vals.extend([-1.0,-1.0]);rhs.append(float(-x0))
            Al1=sparse.coo_matrix(
                (np.asarray(vals),(np.asarray(rows),np.asarray(cols))),
                shape=(len(rhs),nvar),
            ).tocsr()
            bl1=np.asarray(rhs,dtype=np.float64)

            Abase=sparse.vstack([Aupper,Alower,Al1],format="csr")
            bbase=np.r_[bupper,blower,bl1]

            bounds=[]
            for x0 in cex_x0.tolist():
                if x0>SIGN_TOL_KG: bounds.append((0.0,None))
                elif x0<-SIGN_TOL_KG: bounds.append((None,0.0))
                else: bounds.append((0.0,0.0))
            bounds.extend([(0.0,None)]*n_h)  # H2 halo deposition only
            bounds.extend([(0.0,None)]*n_ex) # L1 aux

            # Stage 1: minimum new H2 halo mass.
            c1=np.zeros(nvar,dtype=np.float64)
            if n_h:
                c1[n_ex:n_ex+n_h]=1.0
            t0=time.time()
            r1=linprog(c1,A_ub=Abase,b_ub=bbase,A_eq=Aeq,b_eq=beq,bounds=bounds,method="highs",options={"presolve":True})
            t1=float(time.time()-t0);total_solver_s+=t1
            if not r1.success:
                raise ScientificFail(
                    "HiGHS_H2XY_primary_projection_infeasible_or_failed",
                    {"component_id":cid,"status":int(r1.status),"message":str(r1.message),
                     "CV_count":len(comp_cvs),"cell_count":len(comp_cells),
                     "existing_variable_count":n_ex,"halo_edge_count":n_h},
                )
            primary=float(r1.fun)
            p_tol=max(PRIMARY_ABS_TOL_KG,abs(primary)*PRIMARY_REL_TOL)

            # Stage 2: preserve the primary minimum and minimize existing-support L1 deviation.
            if n_h:
                prow=np.zeros(nvar,dtype=np.float64)
                prow[n_ex:n_ex+n_h]=1.0
                A2=sparse.vstack([Abase,sparse.csr_matrix(prow.reshape(1,-1))],format="csr")
                b2=np.r_[bbase,primary+p_tol]
            else:
                A2=Abase;b2=bbase
            c2=np.zeros(nvar,dtype=np.float64)
            c2[n_ex+n_h:]=1.0
            t0=time.time()
            r2lp=linprog(c2,A_ub=A2,b_ub=b2,A_eq=Aeq,b_eq=beq,bounds=bounds,method="highs",options={"presolve":True})
            t2=float(time.time()-t0);total_solver_s+=t2
            if not r2lp.success:
                raise ScientificFail(
                    "HiGHS_H2XY_secondary_L1_projection_infeasible_or_failed",
                    {"component_id":cid,"status":int(r2lp.status),"message":str(r2lp.message),
                     "primary_halo_mass_kg":primary,"primary_tolerance_kg":p_tol},
                )

            z=np.asarray(r2lp.x,dtype=np.float64)
            x=z[ix_x]
            h=z[ix_h]
            y=z[ix_y]
            repaired_ex[ex_idx]=x
            if n_h: repaired_halo[h_idx]=h

            halo_mass=float(np.sum(h))
            l1=float(np.sum(np.abs(x-cex_x0)))
            cv_res=np.asarray(Aeq@z-beq).ravel()
            cell_mass=fixed_mass[comp_cells]+np.asarray(Acell@z).ravel()
            lower_v=max(0.0,-float(np.min(cell_mass)))
            upper_v=max(0.0,float(np.max(cell_mass-capacity[comp_cells])))
            sign_v=0.0
            for old,new in zip(cex_x0,x):
                if old>0: sign_v=max(sign_v,max(0.0,-float(new)))
                elif old<0: sign_v=max(sign_v,max(0.0,float(new)))
            halo_neg=max(0.0,-float(np.min(h))) if n_h else 0.0

            sci_gate(f"component_{cid:04d}_CV_equality",
                     float(np.max(np.abs(cv_res)))<=CV_EQUALITY_TOL_KG,
                     float(np.max(np.abs(cv_res))))
            sci_gate(f"component_{cid:04d}_cell_lower",
                     lower_v<=CELL_BOUND_TOL_KG,lower_v)
            sci_gate(f"component_{cid:04d}_cell_upper",
                     upper_v<=CELL_BOUND_TOL_KG,upper_v)
            sci_gate(f"component_{cid:04d}_existing_sign",
                     sign_v<=SIGN_TOL_KG,sign_v)
            sci_gate(f"component_{cid:04d}_halo_nonnegative",
                     halo_neg<=SIGN_TOL_KG,halo_neg)
            sci_gate(f"component_{cid:04d}_primary_envelope",
                     halo_mass<=primary+p_tol+1.0e-8,
                     {"halo_mass":halo_mass,"primary":primary,"tol":p_tol})

            total_primary_halo+=halo_mass
            total_secondary_l1+=l1
            component_rows.append({
                "component_id":cid,
                "CV_count":int(len(comp_cvs)),
                "cell_count":int(len(comp_cells)),
                "existing_variable_count":int(n_ex),
                "halo_edge_count":int(n_h),
                "primary_minimum_halo_mass_kg":primary,
                "accepted_halo_mass_kg":halo_mass,
                "existing_support_L1_adjustment_kg":l1,
                "maximum_CV_equality_residual_kg":float(np.max(np.abs(cv_res))),
                "maximum_lower_bound_violation_kg":lower_v,
                "maximum_upper_bound_violation_kg":upper_v,
                "maximum_existing_sign_violation_kg":sign_v,
                "maximum_halo_negative_violation_kg":halo_neg,
                "primary_solver_runtime_s":t1,
                "secondary_solver_runtime_s":t2,
            })

        stage="global_certification"
        # Start from immutable fixed contributions, add repaired existing variables and new H2 halo contributions.
        repaired_existing_pair_val=pair_val.copy()
        var_ex_key=var_ex_cv.astype(np.int64)*NCELL+var_ex_cell.astype(np.int64)
        for k,new in zip(var_ex_key.tolist(),repaired_ex.tolist()):
            loc=int(np.searchsorted(pair_key,int(k)))
            if loc>=len(pair_key) or int(pair_key[loc])!=int(k):
                raise GateError(f"existing_variable_pair_key_not_found:{k}")
            repaired_existing_pair_val[loc]=float(new)

        repaired_cell_delta=np.bincount(pair_cell,weights=repaired_existing_pair_val,minlength=NCELL)
        if len(halo_edges):
            repaired_cell_delta+=np.bincount(halo_cell,weights=repaired_halo,minlength=NCELL)
        repaired_grid_mass=parent_grid_mass.reshape(-1)+repaired_cell_delta

        repaired_cv_transfer=np.bincount(pair_cv,weights=repaired_existing_pair_val,minlength=NSL*NCV)
        if len(halo_edges):
            repaired_cv_transfer+=np.bincount(halo_cv,weights=repaired_halo,minlength=NSL*NCV)
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
        changed_nonculprit=np.any(changed_existing & (~union_mask[pair_cv]))
        sign_bad=np.any(
            ((pair_val>SIGN_TOL_KG)&(repaired_existing_pair_val<-SIGN_TOL_KG))
            |((pair_val<-SIGN_TOL_KG)&(repaired_existing_pair_val>SIGN_TOL_KG))
        )
        zero_bad=np.any((np.abs(pair_val)<=SIGN_TOL_KG)&(np.abs(repaired_existing_pair_val)>SIGN_TOL_KG))
        sci_gate("nonculprit_existing_pairs_unchanged",not changed_nonculprit,bool(changed_nonculprit))
        sci_gate("existing_pair_sign_preserved_globally",not sign_bad,bool(sign_bad))
        sci_gate("existing_zero_pairs_remain_zero",not zero_bad,bool(zero_bad))
        sci_gate("halo_edges_nonnegative_globally",
                 float(np.min(repaired_halo))>=-SIGN_TOL_KG if len(repaired_halo) else True,
                 float(np.min(repaired_halo)) if len(repaired_halo) else 0.0)

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
        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R5_G2A_Final_Artifacts"
        if local.exists():shutil.rmtree(local)
        local.mkdir(parents=True)
        plots=local/"plots";plots.mkdir()

        halo_used=repaired_halo>1.0e-9
        used_halo_cells=np.unique(halo_cell[halo_used]) if np.any(halo_used) else np.asarray([],dtype=np.int64)

        # Mass comparison plots.
        fig=plt.figure(figsize=(7,5))
        ax=fig.add_subplot(111)
        ax.scatter(original_future[variable_cells],repaired_grid_mass[variable_cells],s=8,alpha=0.35)
        lo=min(float(np.min(original_future[variable_cells])),float(np.min(repaired_grid_mass[variable_cells])))
        hi=max(float(np.max(original_future[variable_cells])),float(np.max(repaired_grid_mass[variable_cells])))
        ax.plot([lo,hi],[lo,hi],linestyle="--")
        ax.axhline(0.0,linewidth=0.8)
        ax.set_xlabel("Original Day370 cell mass (kg)")
        ax.set_ylabel("G2A repaired Day370 cell mass (kg)")
        ax.set_title("H2-XY expanded-support projection")
        ax.grid(True,alpha=0.25)
        fig.savefig(plots/"G2A_original_vs_repaired_cell_mass.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        fig=plt.figure(figsize=(8,6))
        ax=fig.add_subplot(111,projection="3d")
        if len(used_halo_cells):
            k=used_halo_cells//(NY*NX);rr=used_halo_cells%(NY*NX);j=rr//NX;i=rr%NX
            ax.scatter(i,j,k,s=10,alpha=0.5)
        ax.set_xlim(0,NX-1);ax.set_ylim(0,NY-1);ax.set_zlim(0,NZ-1)
        ax.set_xlabel("i");ax.set_ylabel("j");ax.set_zlabel("k")
        ax.view_init(elev=24,azim=-58)
        ax.set_title("G2A H2-XY halo cells receiving positive mass")
        fig.savefig(plots/"3D_G2A_used_H2XY_halo_cells.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        halo_rows=[]
        for q,(cv,cell) in enumerate(halo_edges):
            if repaired_halo[q]<=1.0e-12:continue
            k,j,i=ijk(cell)
            halo_rows.append({
                "cv_id":int(cv),
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
                "flat_cell":int(cell),"k":int(k),"j":int(j),"i":int(i),
                "manhattan_distance_from_some_existing_support":int(halo_dist[q]),
                "repaired_halo_contribution_kg":float(repaired_halo[q]),
            })

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "selected_domain":SELECTED,
            "expanded_component_count":int(len(roots)),
            "existing_projection_variable_count":int(len(var_ex_x0)),
            "candidate_H2_halo_edge_count":int(len(halo_edges)),
            "used_H2_halo_edge_count":int(np.sum(halo_used)),
            "used_H2_halo_cell_count":int(len(used_halo_cells)),
            "minimum_total_H2_halo_mass_kg":float(total_primary_halo),
            "existing_support_L1_adjustment_kg":float(total_secondary_l1),
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
            "vertical_support_used":False,
            "diagonal_support_used":False,
            "halo_transit_used":False,
            "negative_withdrawal_halo_edges_used":False,
            "pressure_refresh_executed":False,
            "P3_authorized":False,
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "P2_R6_authorized":True,
            "P2_R6_name":"Dense Day370-to-Day500 Frozen-Flow Snapshot Continuation with Frozen H2-XY Expanded-Support Projection Semantics",
            "P3_authorized":False,
            "periodic_cadence_selected_now":False,
            "R3R6R1_execution_invalidated":False,
            "frozen_projection_semantics":{
                "domain":SELECTED,
                "new_halo_edges":"upper-bound culprit CV to H2-XY terminal cell only; nonnegative",
                "negative_withdrawal_halo_edges":False,
                "vertical_support":False,
                "diagonal_support":False,
                "halo_transit":False,
                "primary_objective":"minimum total new H2-XY halo mass",
                "secondary_objective":"minimum L1 deviation of existing nonzero culprit CV-cell contributions under the primary envelope",
                "per_CV_mass_conservation":True,
                "cell_lower_and_upper_mass_bounds":True,
            },
        }

        with (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_Repaired_Day370_State.npz").open("wb") as fp:
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
                repaired_halo_contribution_kg=repaired_halo,
                lower_culprit_cv=lower_culprit,
                upper_culprit_cv=upper_culprit,
                union_culprit_cv=union_culprit,
                injected_mass_kg=np.asarray(injected_mass),
                produced_mass_kg=np.asarray(produced_mass),
            )

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_Component_Solver_Audit.csv").write_bytes(csv_bytes(component_rows))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_Used_Halo_Contributions.csv").write_bytes(csv_bytes(halo_rows))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({"file":str(p.relative_to(local)).replace("\\","/"),
                                 "sha256":sha256_file(p),"bytes":p.stat().st_size})
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists():raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*194)
        print("POSTV16-AV4-PIVOT-P2-R5-G2A: PASS")
        print("Expanded components                     :",len(roots))
        print("Candidate H2 halo edges                 :",len(halo_edges))
        print("Used H2 halo edges                      :",int(np.sum(halo_used)))
        print("Used H2 halo cells                      :",len(used_halo_cells))
        print("Minimum total H2 halo mass kg           :",total_primary_halo)
        print("Existing-support L1 adjustment kg       :",total_secondary_l1)
        print("Minimum repaired grid mass kg           :",min_mass)
        print("Maximum repaired capacity excess kg     :",max_excess)
        print("Global mass residual kg                 :",global_res)
        print("Vertical / diagonal support used        : False / False")
        print("P2-R6 authorized                        : True")
        print("P3 authorized                           : False")
        print("="*194)
        return 0

    except ScientificFail as exc:
        fail_dir.mkdir(parents=True,exist_ok=True)
        p=fail_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_Scientific_Fail_Report.json"
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
                "P3_authorized":False,
                "R3R6R1_execution_invalidated":False,
            },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(MILESTONE+": SCIENTIFIC FAIL")
        print("Gate:",exc.gate)
        print("Detail:",exc.detail)
        return 3

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "scientific_execution_started":scientific_started,
                "automatic_rerun_authorized":False,
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
