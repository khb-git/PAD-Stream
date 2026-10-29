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


MILESTONE = "POSTV16-AV4-PIVOT-P2-R6"
STATUS_PASS = (
    "AV4PIVOTP2R6_DENSE_DAY365_TO_DAY500_5DAY_FROZEN_FLOW_TRAJECTORY_PASS_"
    "R4_COMPONENT_FRONTIER_H2_PROJECTION_SEMANTICS_CERTIFIED"
)
STATUS_FAIL = (
    "AV4PIVOTP2R6_FROZEN_FLOW_CONTINUATION_SCIENTIFIC_FAIL_"
    "NO_SUPPORT_GROWTH_NO_PRESSURE_REFRESH_NO_AUTOMATIC_RERUN"
)
STATUS_BLOCKED = "AV4PIVOTP2R6_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "5fc174c7262e3178f5b57e470ac7d18434d07802"
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

START_DAY=365.0
REPAIRED_DAY=370.0
END_DAY=500.0
STEP_DAYS=5.0
SNAPSHOT_DAYS=np.arange(START_DAY,END_DAY+0.5*STEP_DAYS,STEP_DAYS,dtype=np.float64)
CONTINUATION_DAYS=np.arange(REPAIRED_DAY+STEP_DAYS,END_DAY+0.5*STEP_DAYS,STEP_DAYS,dtype=np.float64)

CV_TOL_KG=1.0e-7
CELL_TOL_KG=1.0e-7
LEDGER_ABS_TOL_KG=1.0e-6
SIGN_TOL_KG=1.0e-10
PRIMARY_ABS_TOL_KG=1.0e-7
PRIMARY_REL_TOL=1.0e-11
COMPLETION_ABS_TOL_KG=1.0e-7
COMPLETION_REL_TOL=1.0e-11

BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

R4_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
R4_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Summary.json"
R4_DECISION="POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Decision_Contract.json"
R4_STATE="POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz"
R4_STATUS=(
    "AV4PIVOTP2R5G2AR4R1R1R1_COMPLETED_COMPONENT_CELL_MEMBERSHIP_IDENTITY_"
    "REPAIR_AND_COMPONENT_FRONTIER_PROJECTION_EXECUTION_PASS"
)
R4_NEXT_NAME="Dense Day370-to-Day500 Frozen-Flow Snapshot Continuation with Frozen Component-Frontier H2 Eligibility Projection Semantics"

P2R3_RECOVERY_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R3_Recovery"
P2R3_TEACHER_STATE="Day365_to_Day370_Teacher_State.npz"
P2R3_TEACHER_META="Day365_to_Day370_Teacher_Metadata.json"
P2R3_RUNNER_BLOB="b02061d33f6105a06320f8843986de584293c677"

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

OUT_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_Dense_Day370_to_Day500_FrozenFlow_Continuation"
RECOVERY_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_Recovery_Checkpoints"
FAIL_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_SCIENTIFIC_FAIL"
BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_BLOCKED"

F4R3="PAD_Stream_POSTV16_AV4_F4_R3_Terminal_Producer_PassThrough_Repair_Execution.py"
F4R3_BLOB="2e84ab09f9ae7af6f977eabc3d9465d325fad717"
A4R2="PAD_Stream_POSTV16_AV3_A4_R2_Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
A4R2_BLOB="289901331e835afb44ff2f665fe9a6bbea2eac19"
A2E="PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB="79a8969233b72b4543edd382a0c3d1028c6dca09"
R2SRC="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
E37A="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D="PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB="890088c0c0fcab415a2c7351c5079ca8ee12bf82"
P2R2RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R2_Authority_Path_and_Substeps_Interface_Repair.py"
P2R2RUN_BLOB="ad710711012ffed85ecff0ad653993d654294a0c"
R4RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection_Execution.py"
R4RUN_BLOB="cdcade36343d314bc34063bce6e81e5c9c520294"

SOURCE_BLOBS={
    F4R3:F4R3_BLOB,
    A4R2:A4R2_BLOB,
    A2E:A2E_BLOB,
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
    P2R2RUN:P2R2RUN_BLOB,
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


def fsum_array(a:np.ndarray)->float:
    return float(math.fsum(float(x) for x in np.asarray(a,dtype=np.float64).ravel()))


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


def checkpoint_paths(recovery:Path,day:float)->tuple[Path,Path]:
    d=recovery/f"day_{int(round(day)):04d}"
    return d/"State.npz",d/"Metadata.json"


def save_checkpoint(
    recovery:Path,day:float,runner_blob:str,
    arrays:dict[str,np.ndarray],meta:dict[str,Any]
)->None:
    state_path,meta_path=checkpoint_paths(recovery,day)
    state_path.parent.mkdir(parents=True,exist_ok=True)
    tmp=state_path.with_suffix(".npz.tmp")
    with tmp.open("wb") as fp:
        np.savez_compressed(fp,**arrays)
    tmp.replace(state_path)
    m={
        "milestone":MILESTONE,
        "runner_blob":runner_blob,
        "day":float(day),
        "state_sha256":sha256_file(state_path),
        **meta,
    }
    meta_path.write_text(json.dumps(m,indent=2,sort_keys=True)+"\n",encoding="utf-8")


def load_checkpoint(
    recovery:Path,day:float,runner_blob:str
)->tuple[dict[str,np.ndarray],dict[str,Any]]|None:
    state_path,meta_path=checkpoint_paths(recovery,day)
    if not state_path.is_file() or not meta_path.is_file():
        return None
    meta=load_json(meta_path)
    if (
        meta.get("milestone")!=MILESTONE
        or meta.get("runner_blob")!=runner_blob
        or abs(float(meta.get("day",-999.0))-float(day))>1.0e-12
        or meta.get("state_sha256")!=sha256_file(state_path)
    ):
        raise GateError(f"invalid_P2R6_checkpoint_day_{day:g}")
    with np.load(state_path,allow_pickle=False) as z:
        arrays={k:np.asarray(z[k]).copy() for k in z.files}
    return arrays,meta


def plot_metrics(rows:list[dict[str,Any]],outdir:Path)->list[str]:
    outdir.mkdir(parents=True,exist_ok=True)
    days=np.asarray([float(r["day"]) for r in rows])
    specs=[
        ("dense_total_grid_CO2_mass_vs_day.png","grid_total_mass_kg","Grid CO2 mass (kg)","Frozen-flow CO2 inventory"),
        ("dense_max_grid_saturation_vs_day.png","grid_saturation_max","Maximum grid saturation","Frozen-flow saturation evolution"),
        ("dense_cumulative_produced_CO2_vs_day.png","cumulative_produced_mass_kg","Cumulative produced CO2 (kg)","Frozen-flow produced CO2"),
        ("dense_projection_H2_mass_vs_day.png","projection_H2_mass_kg","Projected H2 mass (kg)","Frozen component-frontier projection usage"),
    ]
    names=[]
    for fn,key,ylabel,title in specs:
        vals=np.asarray([float(r.get(key,0.0)) for r in rows])
        fig=plt.figure(figsize=(7,4.5))
        ax=fig.add_subplot(111)
        ax.plot(days,vals,marker="o",markersize=3)
        ax.set_xlabel("Day");ax.set_ylabel(ylabel);ax.set_title(title);ax.grid(True,alpha=0.25)
        fig.savefig(outdir/fn,dpi=180,bbox_inches="tight")
        plt.close(fig);names.append(fn)
    return names


def plot_plumes(days:np.ndarray,grid_sat:np.ndarray,outdir:Path)->list[str]:
    outdir.mkdir(parents=True,exist_ok=True)
    selected=[365.0,370.0,400.0,450.0,500.0]
    names=[]
    for day in selected:
        idx=int(np.where(np.isclose(days,day,atol=1.0e-12,rtol=0.0))[0][0])
        sg=np.maximum(np.asarray(grid_sat[idx],dtype=np.float64)-BACKGROUND,0.0)
        pts=np.argwhere(sg>1.0e-4)
        vals=sg[sg>1.0e-4]
        fig=plt.figure(figsize=(8,6))
        ax=fig.add_subplot(111,projection="3d")
        if len(pts):
            ax.scatter(pts[:,2],pts[:,1],pts[:,0],s=8,c=vals,alpha=0.55)
        ax.set_xlim(0,NX-1);ax.set_ylim(0,NY-1);ax.set_zlim(0,NZ-1)
        ax.set_xlabel("i");ax.set_ylabel("j");ax.set_zlabel("k")
        ax.set_title(f"Dense frozen-flow CO2 plume — Day {int(day)}")
        ax.view_init(elev=24,azim=-58)
        fn=f"3D_dense_frozen_flow_CO2_plume_day{int(day):04d}.png"
        fig.savefig(outdir/fn,dpi=180,bbox_inches="tight")
        plt.close(fig);names.append(fn)
    return names


def self_test()->None:
    assert len(SNAPSHOT_DAYS)==28
    assert SNAPSHOT_DAYS[0]==365.0 and SNAPSHOT_DAYS[-1]==500.0
    assert len(CONTINUATION_DAYS)==26
    assert CONTINUATION_DAYS[0]==375.0 and CONTINUATION_DAYS[-1]==500.0
    assert np.allclose(np.diff(SNAPSHOT_DAYS),5.0)
    print("POSTV16 AV4 PIVOT P2-R6 structural self-test: PASS")


def main(project_root:Path,drive_root:Path)->int:
    root=Path(project_root).resolve()
    drive=Path(drive_root).resolve()
    out=drive/OUT_REL
    recovery=drive/RECOVERY_REL
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
    print("POSTV16-AV4-PIVOT-P2-R6 -- DENSE DAY370->DAY500 FROZEN-FLOW CONTINUATION WITH FROZEN COMPONENT-FRONTIER H2 PROJECTION")
    print("="*194)
    print("FLOW FIELD FROZEN AT DAY365. DAY370 IS THE ACCEPTED R4 REPAIRED STATE.")
    print("NO SUPPORT GROWTH. NO VERTICAL/DIAGONAL SUPPORT. NO PRESSURE REFRESH. NO TRAINING.")
    print("DAYS375-500: 5-DAY TEACHER STEP -> DIRECT MAPBACK -> FROZEN R4 PROJECTION IF REQUIRED.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_Summary.json"
        fail_report=fail_dir/"POSTV16_AV4_PIVOT_P2_R6_Scientific_Fail_Report.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R6_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P2-R6 PASS already exists; immutable outcome preserved.")
            return 0
        if fail_report.is_file():
            print("[PASS] formal P2-R6 SCIENTIFIC FAIL already exists; immutable outcome preserved.")
            return 3
        if block_report.is_file():
            print("[PASS] formal P2-R6 BLOCK already exists; immutable outcome preserved.")
            return 2

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_R4_PASS_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,
             git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",
             repr(git_text(root,"status","--porcelain")))
        runner_blob=git_text(root,"hash-object",str(Path(__file__).resolve()))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="R4_PASS_binding"
        r4dir=drive/R4_REL
        r4s=load_json(r4dir/R4_SUMMARY)
        r4d=load_json(r4dir/R4_DECISION)
        r4state_path=r4dir/R4_STATE
        gate("R4_summary_status_exact",r4s.get("status")==R4_STATUS,r4s.get("status"))
        gate("R4_decision_status_exact",r4d.get("status")==R4_STATUS,r4d.get("status"))
        gate("R4_P2R6_authorized",r4d.get("P2_R6_authorized") is True,r4d.get("P2_R6_authorized"))
        gate("R4_P2R6_name_exact",r4d.get("P2_R6_name")==R4_NEXT_NAME,r4d.get("P2_R6_name"))
        gate("R4_P3_still_false",r4d.get("P3_authorized") is False,r4d.get("P3_authorized"))
        gate("R4_state_present",r4state_path.is_file(),str(r4state_path))
        gate("R4_state_SHA_summary_exact",sha256_file(r4state_path)==r4s.get("accepted_state_sha256"),
             {"actual":sha256_file(r4state_path),"summary":r4s.get("accepted_state_sha256")})
        gate("R4_state_SHA_decision_exact",sha256_file(r4state_path)==r4d.get("accepted_repaired_day370_state_sha256"),
             {"actual":sha256_file(r4state_path),"decision":r4d.get("accepted_repaired_day370_state_sha256")})

        sem=r4d.get("frozen_projection_semantics",{})
        gate("R4_projection_no_vertical",sem.get("vertical_support") is False)
        gate("R4_projection_no_diagonal",sem.get("diagonal_support") is False)
        gate("R4_projection_no_negative_halo",sem.get("negative_withdrawal_H2_edges") is False)
        gate("R4_projection_sign_preserving",sem.get("existing_nonzero_pair_sign_preservation") is True)
        gate("R4_projection_zero_pairs_frozen",sem.get("existing_zero_pairs_remain_zero") is True)
        gate("R4_projection_nonculprits_fixed",sem.get("nonculprit_existing_pairs_unchanged") is True)
        gate("R4_projection_pressure_frozen",sem.get("pressure_refresh") is False)

        with np.load(r4state_path,allow_pickle=False) as z:
            r4state={k:np.asarray(z[k]).copy() for k in z.files}
        gate("R4_state_day_exact",abs(float(np.asarray(r4state["day"]).reshape(()))-370.0)<=1.0e-12)
        day370_cv_mass=np.asarray(r4state["cv_component_mass_kg"],dtype=np.float64)
        day370_cv_sat=np.asarray(r4state["cv_saturation"],dtype=np.float64)
        day370_grid_mass=np.asarray(r4state["grid_component_mass_kg"],dtype=np.float64)
        day370_grid_sat=np.asarray(r4state["grid_saturation"],dtype=np.float64)
        frozen_pair_cv=np.asarray(r4state["existing_pair_cv"],dtype=np.int64)
        frozen_pair_cell=np.asarray(r4state["existing_pair_cell"],dtype=np.int64)
        frozen_halo_cv=np.asarray(r4state["halo_cv"],dtype=np.int64)
        frozen_halo_cell=np.asarray(r4state["halo_cell"],dtype=np.int64)
        frozen_halo_is_completion=np.asarray(r4state["halo_is_completion"],dtype=bool)
        frozen_halo_distance=np.asarray(r4state["halo_distance"],dtype=np.int64)
        day370_injected=float(np.asarray(r4state["injected_mass_kg"]).reshape(()))
        day370_produced=float(np.asarray(r4state["produced_mass_kg"]).reshape(()))

        gate("R4_state_CV_shapes",day370_cv_mass.shape==(NSL,NCV) and day370_cv_sat.shape==(NSL,NCV))
        gate("R4_state_grid_shapes",day370_grid_mass.shape==GRID and day370_grid_sat.shape==GRID)
        gate("R4_frozen_edge_array_shapes",
             frozen_halo_cv.shape==frozen_halo_cell.shape==frozen_halo_is_completion.shape==frozen_halo_distance.shape)
        gate("R4_completion_edge_count_exact",int(np.sum(frozen_halo_is_completion))==46915,int(np.sum(frozen_halo_is_completion)))

        stage="Day365_and_teacher_authority"
        f2path=drive/F2R3_REL/F2R3_STATE
        x13path=drive/E1R2_REL/E1R2_X13
        a2path=drive/A2E_REL/A2E_EPOCH
        a2sum=drive/A2E_REL/A2E_SUMMARY
        teacher_path=drive/P2R3_RECOVERY_REL/P2R3_TEACHER_STATE
        teacher_meta_path=drive/P2R3_RECOVERY_REL/P2R3_TEACHER_META

        for label,p in [
            ("F2R3_state",f2path),("E1R2_X13",x13path),("A2E_epoch",a2path),
            ("A2E_summary",a2sum),("P2R3_teacher_state",teacher_path),("P2R3_teacher_meta",teacher_meta_path)
        ]:
            gate(label+"_present",p.is_file(),str(p))
        gate("A2E_status_exact",load_json(a2sum).get("status")==A2E_STATUS,load_json(a2sum).get("status"))
        tmeta=load_json(teacher_meta_path)
        gate("P2R3_teacher_runner_blob_exact",tmeta.get("runner_blob")==P2R3_RUNNER_BLOB,tmeta.get("runner_blob"))
        gate("P2R3_teacher_SHA_exact",tmeta.get("state_sha256")==sha256_file(teacher_path),tmeta.get("state_sha256"))

        with np.load(f2path,allow_pickle=False) as z:
            parent_cv_mass=np.asarray(z["parent_CV_component_mass_kg"],dtype=np.float64)
            parent_cv_sat=np.asarray(z["parent_CV_saturation"],dtype=np.float64)
            parent_cv_capacity=np.asarray(z["parent_CV_capacity_kg"],dtype=np.float64)
            parent_cv_pv=np.asarray(z["parent_CV_pore_volume_m3"],dtype=np.float64)
            parent_cv_coeff=np.asarray(z["parent_CV_pressure_mass_coeff"],dtype=np.float64)
        with np.load(x13path,allow_pickle=False) as z:
            X13=np.asarray(z["X_refreshed_13"],dtype=np.float64)
        with np.load(a2path,allow_pickle=False) as z:
            epoch={k:np.asarray(z[k]).copy() for k in z.files}
        with np.load(teacher_path,allow_pickle=False) as z:
            teacher370={k:np.asarray(z[k]).copy() for k in z.files}

        required={
            "parent_component_mass_kg","reconciled_saturation","refreshed_pressure_psi",
            "pore_volume_m3","reference_gas_pressure_pa","streamline_xyz_m",
            "streamline_tof_s","streamline_weight_m3_s","streamline_face_pressure_psi","xi"
        }
        gate("A2E_required_epoch_arrays",required.issubset(epoch),sorted(required))

        day365_grid_mass=np.asarray(epoch["parent_component_mass_kg"],dtype=np.float64)
        day365_grid_sat=np.asarray(epoch["reconciled_saturation"],dtype=np.float64)
        parent_pressure=np.asarray(epoch["refreshed_pressure_psi"],dtype=np.float64)
        grid_pv=np.asarray(epoch["pore_volume_m3"],dtype=np.float64)
        p_ref=float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))
        parent_xyz=np.asarray(epoch["streamline_xyz_m"],dtype=np.float64)
        parent_tof=np.asarray(epoch["streamline_tof_s"],dtype=np.float64)
        parent_weights=np.asarray(epoch["streamline_weight_m3_s"],dtype=np.float64)
        parent_face_pressure=np.asarray(epoch["streamline_face_pressure_psi"],dtype=np.float64)
        xi=np.asarray(epoch["xi"],dtype=np.float64).reshape(-1)

        gate("Day370_CV_mass_matches_teacher",
             np.allclose(day370_cv_mass,np.asarray(teacher370["future_mass"],dtype=np.float64),rtol=0.0,atol=1.0e-10))
        gate("Day370_CV_sat_matches_teacher",
             np.allclose(day370_cv_sat,np.asarray(teacher370["future_saturation"],dtype=np.float64),rtol=0.0,atol=1.0e-12))
        gate("Day370_injected_matches_teacher",
             abs(day370_injected-float(np.asarray(teacher370["injected_mass_kg"]).reshape(())))<=1.0e-8)
        gate("Day370_produced_matches_teacher",
             abs(day370_produced-float(np.asarray(teacher370["produced_mass_kg"]).reshape(())))<=1.0e-8)
        day370_substeps=int(np.asarray(teacher370["substeps"]).reshape(()))

        stage="source_module_binding"
        f4=load_module(root/F4R3,"av4_p2r6_f4")
        a4=load_module(root/A4R2,"av4_p2r6_a4")
        a2e=load_module(root/A2E,"av4_p2r6_a2e")
        r2=load_module(root/R2SRC,"av4_p2r6_r2")
        e37=load_module(root/E37A,"av4_p2r6_e37")
        sg7d=load_module(root/SG7D,"av4_p2r6_sg7d")

        gate("required_helpers_present",
             hasattr(f4,"execute_teacher_with_coeff")
             and hasattr(f4,"build_cv_geometry_from_faces")
             and hasattr(a2e,"invert_local_mass"))

        cvavg=0.5*(X13[:,:-1,:]+X13[:,1:,:])
        phi_cv=cvavg[:,:,5]
        nw_cv=3.0+cvavg[:,:,9]
        no_cv=3.0+cvavg[:,:,10]
        krw_cv=0.80+0.20*cvavg[:,:,11]
        kro_cv=0.80+0.20*cvavg[:,:,12]
        cvgeom=f4.build_cv_geometry_from_faces(parent_tof,xi)

        parent_operator=sg7d.build_subsegment_operator(parent_xyz,parent_tof/SPD,parent_weights*SPD)
        geometry=e37.build_control_volume_geometry(r2,parent_operator,parent_pressure,p_ref,NSL,NCV)
        gate("parent_CV_pore_volume_matches_F2R3",
             float(np.max(np.abs(np.asarray(geometry["cv_pv_m3"])-parent_cv_pv)))<=1.0e-8)
        gate("parent_CV_pressure_coeff_matches_F2R3",
             relative_l2(np.asarray(geometry["cv_pressure_mass_coeff"]),parent_cv_coeff)<=1.0e-12)

        cv_id=np.asarray(geometry["cv_id"],dtype=np.int64)
        flat=np.asarray(geometry["flat_cell"],dtype=np.int64)
        pv=np.asarray(geometry["pv_m3"],dtype=np.float64)
        pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64)

        sat_max=np.full(GRID,BACKGROUND+MAX_SG,dtype=np.float64)
        rho_max=np.asarray(r2.gas_density_from_state(sat_max,parent_pressure,p_ref),dtype=np.float64)
        cell_capacity=(grid_pv*rho_max*MAX_SG).reshape(-1)

        # Pair-key support is geometry-only and must remain identical to the accepted R4 state.
        geom_key=cv_id.astype(np.int64)*NCELL+flat.astype(np.int64)
        order=np.argsort(geom_key,kind="mergesort")
        key_s=geom_key[order]
        starts=np.r_[0,1+np.flatnonzero(key_s[1:]!=key_s[:-1])]
        pair_key_geom=key_s[starts]
        pair_cv_geom=(pair_key_geom//NCELL).astype(np.int64)
        pair_cell_geom=(pair_key_geom%NCELL).astype(np.int64)
        gate("R4_pair_CV_support_exact",np.array_equal(pair_cv_geom,frozen_pair_cv))
        gate("R4_pair_cell_support_exact",np.array_equal(pair_cell_geom,frozen_pair_cell))

        # Day370 ledger closes against the accepted repaired Cartesian state.
        d365_total=fsum_array(day365_grid_mass)
        d370_total=fsum_array(day370_grid_mass)
        d370_expected=d365_total+day370_injected-day370_produced
        d370_tol=max(LEDGER_ABS_TOL_KG,1.0e-10*max(abs(d370_expected),1.0))
        sci_gate("Day370_accepted_state_mass_ledger",
                 abs(d370_total-d370_expected)<=d370_tol,
                 {"actual":d370_total,"expected":d370_expected,"residual":d370_total-d370_expected,"tol":d370_tol})

        def projected_mapback(
            old_grid_mass:np.ndarray,
            old_cv_mass:np.ndarray,
            old_cv_sat:np.ndarray,
            new_cv_mass:np.ndarray,
            new_cv_sat:np.ndarray,
            day:float,
        )->tuple[np.ndarray,np.ndarray,dict[str,Any]]:
            # Recompute exact parent-geometry pair contributions for this 5-day CV transition.
            old_flat=np.asarray(old_cv_sat,dtype=np.float64).reshape(-1)
            new_flat=np.asarray(new_cv_sat,dtype=np.float64).reshape(-1)
            old_sub=old_flat[cv_id];new_sub=new_flat[cv_id]
            old_sg=np.clip(old_sub-BACKGROUND,0.0,MAX_SG)
            new_sg=np.clip(new_sub-BACKGROUND,0.0,MAX_SG)
            rho_old=np.asarray(r2.gas_density_from_state(old_sub,pseg,p_ref),dtype=np.float64)
            rho_new=np.asarray(r2.gas_density_from_state(new_sub,pseg,p_ref),dtype=np.float64)
            sub_delta=pv*(rho_new*new_sg-rho_old*old_sg)

            cv_delta=(np.asarray(new_cv_mass)-np.asarray(old_cv_mass)).reshape(-1)
            transfer=np.bincount(cv_id,weights=sub_delta,minlength=NSL*NCV)
            max_transfer_res=float(np.max(np.abs(transfer-cv_delta)))
            if max_transfer_res>CV_TOL_KG:
                raise ScientificFail(
                    f"Day{int(day)}_subsegment_per_CV_transfer_closure",
                    {"max_residual_kg":max_transfer_res},
                )

            val_s=sub_delta[order]
            pair_val=np.add.reduceat(val_s,starts)
            pair_cv=frozen_pair_cv
            pair_cell=frozen_pair_cell

            direct_delta=np.bincount(pair_cell,weights=pair_val,minlength=NCELL)
            direct_future=np.asarray(old_grid_mass,dtype=np.float64).reshape(-1)+direct_delta
            lower=direct_future<-CELL_TOL_KG
            upper=direct_future>cell_capacity+CELL_TOL_KG

            # Direct conservative mapback is accepted if already physical.
            if not np.any(lower) and not np.any(upper):
                try:
                    sg=a2e.invert_local_mass(
                        r2,direct_future.reshape(GRID),parent_pressure,p_ref,grid_pv
                    )
                except Exception as exc:
                    raise ScientificFail(
                        f"Day{int(day)}_direct_mapback_mass_inversion",
                        repr(exc)
                    ) from exc
                grid_sat=BACKGROUND+np.asarray(sg,dtype=np.float64)
                return direct_future.reshape(GRID),grid_sat,{
                    "projection_applied":False,
                    "lower_violation_count_before":0,
                    "upper_violation_count_before":0,
                    "culprit_CV_count":0,
                    "eligible_H2_edge_count":0,
                    "completion_edge_count_available":0,
                    "projection_H2_mass_kg":0.0,
                    "projection_completion_mass_kg":0.0,
                    "existing_support_L1_adjustment_kg":0.0,
                    "maximum_per_CV_residual_kg":max_transfer_res,
                    "maximum_capacity_excess_kg":float(np.max(direct_future-cell_capacity)),
                    "minimum_grid_mass_kg":float(np.min(direct_future)),
                }

            lower_culprit=np.unique(pair_cv[lower[pair_cell]&(pair_val<-SIGN_TOL_KG)]).astype(np.int64)
            upper_culprit=np.unique(pair_cv[upper[pair_cell]&(pair_val>SIGN_TOL_KG)]).astype(np.int64)
            union_culprit=np.union1d(lower_culprit,upper_culprit).astype(np.int64)
            if len(union_culprit)==0:
                raise ScientificFail(
                    f"Day{int(day)}_violating_cells_without_two_sided_culprit_CVs",
                    {"lower":int(np.sum(lower)),"upper":int(np.sum(upper))}
                )

            union_mask=np.zeros(NSL*NCV,dtype=bool);union_mask[union_culprit]=True
            existing_mask=union_mask[pair_cv]
            existing_cv=pair_cv[existing_mask]
            existing_cell=pair_cell[existing_mask]
            existing_val=pair_val[existing_mask]
            ex_nonzero=np.abs(existing_val)>SIGN_TOL_KG
            var_ex_cv=existing_cv[ex_nonzero]
            var_ex_cell=existing_cell[ex_nonzero]
            var_ex_x0=existing_val[ex_nonzero]

            # The R4 graph is frozen. Only edges whose CV is currently in the culprit domain
            # are retained; all excluded edges are algebraically forced to zero by nonculprit freezing.
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
            fixed_mass=np.asarray(old_grid_mass,dtype=np.float64).reshape(-1)+fixed_delta

            variable_cells=np.union1d(var_ex_cell,halo_cell).astype(np.int64)
            outside=np.ones(NCELL,dtype=bool);outside[variable_cells]=False
            immutable_lower=np.flatnonzero(outside&(fixed_mass<-CELL_TOL_KG))
            immutable_upper=np.flatnonzero(outside&(fixed_mass>cell_capacity+CELL_TOL_KG))
            if len(immutable_lower) or len(immutable_upper):
                raise ScientificFail(
                    f"Day{int(day)}_frozen_R4_graph_does_not_cover_all_cell_bound_violations",
                    {"outside_lower_count":int(len(immutable_lower)),
                     "outside_upper_count":int(len(immutable_upper)),
                     "current_culprit_CV_count":int(len(union_culprit))}
                )

            # Connected components of the CURRENT culprit solve graph.
            all_cells=np.union1d(np.unique(existing_cell),np.unique(halo_cell)).astype(np.int64)
            cv_local={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
            cell_local={int(c):n for n,c in enumerate(all_cells.tolist())}
            dsu=DSU(len(union_culprit)+len(all_cells));off=len(union_culprit)

            for cv,c in zip(existing_cv.tolist(),existing_cell.tolist()):
                dsu.union(cv_local[int(cv)],off+cell_local[int(c)])
            for cv,c in zip(halo_cv.tolist(),halo_cell.tolist()):
                dsu.union(cv_local[int(cv)],off+cell_local[int(c)])

            roots=sorted({dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()})
            comp_of_cv={int(cv):dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()}
            ex_root=np.asarray([comp_of_cv[int(cv)] for cv in var_ex_cv],dtype=np.int64)
            h_root=np.asarray([comp_of_cv[int(cv)] for cv in halo_cv],dtype=np.int64)

            try:
                from scipy.optimize import linprog
                from scipy import sparse
            except Exception as exc:
                raise GateError("scipy_HiGHS_unavailable:"+repr(exc)) from exc

            repaired_ex=var_ex_x0.copy()
            repaired_halo=np.zeros(len(halo_cv),dtype=np.float64)
            stage1_total=0.0
            stage2_completion_total=0.0
            stage3_l1_total=0.0

            for cid,root_id in enumerate(roots):
                comp_cvs=np.asarray(
                    [cv for cv in union_culprit.tolist() if comp_of_cv[int(cv)]==root_id],
                    dtype=np.int64
                )
                ex_idx=np.flatnonzero(ex_root==root_id)
                h_idx=np.flatnonzero(h_root==root_id)
                n_ex=len(ex_idx);n_h=len(h_idx)
                if n_ex==0:
                    raise ScientificFail(
                        f"Day{int(day)}_component_{cid}_has_no_existing_projection_variables",
                        {"CV_count":int(len(comp_cvs)),"H2_edge_count":int(n_h)}
                    )

                cex_cv=var_ex_cv[ex_idx]
                cex_cell=var_ex_cell[ex_idx]
                cex_x0=var_ex_x0[ex_idx]
                ch_cv=halo_cv[h_idx]
                ch_cell=halo_cell[h_idx]
                ch_comp=halo_is_completion[h_idx]
                comp_cells=np.unique(np.r_[cex_cell,ch_cell]).astype(np.int64)

                nvar=n_ex+n_h+n_ex
                cv_row={int(cv):r for r,cv in enumerate(comp_cvs.tolist())}
                eq_r=[];eq_c=[];eq_v=[]
                for q,cv in enumerate(cex_cv.tolist()):
                    eq_r.append(cv_row[int(cv)]);eq_c.append(q);eq_v.append(1.0)
                for q,cv in enumerate(ch_cv.tolist()):
                    eq_r.append(cv_row[int(cv)]);eq_c.append(n_ex+q);eq_v.append(1.0)
                Aeq=sparse.coo_matrix(
                    (np.asarray(eq_v),(np.asarray(eq_r),np.asarray(eq_c))),
                    shape=(len(comp_cvs),nvar)
                ).tocsr()
                beq=cv_delta[comp_cvs]

                cell_row={int(c):r for r,c in enumerate(comp_cells.tolist())}
                cr=[];cc=[];vv=[]
                for q,c in enumerate(cex_cell.tolist()):
                    cr.append(cell_row[int(c)]);cc.append(q);vv.append(1.0)
                for q,c in enumerate(ch_cell.tolist()):
                    cr.append(cell_row[int(c)]);cc.append(n_ex+q);vv.append(1.0)
                Acell=sparse.coo_matrix(
                    (np.asarray(vv),(np.asarray(cr),np.asarray(cc))),
                    shape=(len(comp_cells),nvar)
                ).tocsr()

                bupper=cell_capacity[comp_cells]-fixed_mass[comp_cells]
                blower=fixed_mass[comp_cells]

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

                # Stage 1.
                c1=np.zeros(nvar,dtype=np.float64)
                if n_h:c1[n_ex:n_ex+n_h]=1.0
                lp1=linprog(c1,A_ub=Abase,b_ub=bbase,A_eq=Aeq,b_eq=beq,
                            bounds=bounds,method="highs",options={"presolve":True})
                if not lp1.success:
                    raise ScientificFail(
                        f"Day{int(day)}_component_{cid}_stage1_infeasible",
                        {"status":int(lp1.status),"message":str(lp1.message),
                         "CV_count":int(len(comp_cvs)),"cell_count":int(len(comp_cells)),
                         "existing_variable_count":int(n_ex),"H2_edge_count":int(n_h)}
                    )
                primary=max(0.0,float(lp1.fun))
                p_tol=max(PRIMARY_ABS_TOL_KG,abs(primary)*PRIMARY_REL_TOL)
                prow=np.zeros(nvar,dtype=np.float64)
                if n_h:prow[n_ex:n_ex+n_h]=1.0
                A2=sparse.vstack([Abase,sparse.csr_matrix(prow.reshape(1,-1))],format="csr")
                b2=np.r_[bbase,primary+p_tol]

                # Stage 2.
                c2=np.zeros(nvar,dtype=np.float64)
                if n_h:
                    idx=np.flatnonzero(ch_comp)
                    if len(idx):c2[n_ex+idx]=1.0
                lp2=linprog(c2,A_ub=A2,b_ub=b2,A_eq=Aeq,b_eq=beq,
                            bounds=bounds,method="highs",options={"presolve":True})
                if not lp2.success:
                    raise ScientificFail(
                        f"Day{int(day)}_component_{cid}_stage2_infeasible",
                        {"status":int(lp2.status),"message":str(lp2.message)}
                    )
                completion_min=max(0.0,float(lp2.fun))
                c_tol=max(COMPLETION_ABS_TOL_KG,abs(completion_min)*COMPLETION_REL_TOL)
                crow=np.zeros(nvar,dtype=np.float64)
                if n_h:
                    idx=np.flatnonzero(ch_comp)
                    if len(idx):crow[n_ex+idx]=1.0
                A3=sparse.vstack([A2,sparse.csr_matrix(crow.reshape(1,-1))],format="csr")
                b3=np.r_[b2,completion_min+c_tol]

                # Stage 3.
                c3=np.zeros(nvar,dtype=np.float64)
                c3[n_ex+n_h:]=1.0
                lp3=linprog(c3,A_ub=A3,b_ub=b3,A_eq=Aeq,b_eq=beq,
                            bounds=bounds,method="highs",options={"presolve":True})
                if not lp3.success:
                    raise ScientificFail(
                        f"Day{int(day)}_component_{cid}_stage3_infeasible",
                        {"status":int(lp3.status),"message":str(lp3.message)}
                    )

                z=np.asarray(lp3.x,dtype=np.float64)
                x=z[:n_ex];h=z[n_ex:n_ex+n_h]
                repaired_ex[ex_idx]=x
                if n_h:repaired_halo[h_idx]=h

                cv_res=np.asarray(Aeq@z-beq).ravel()
                cell_mass=fixed_mass[comp_cells]+np.asarray(Acell@z).ravel()
                lower_v=max(0.0,-float(np.min(cell_mass)))
                upper_v=max(0.0,float(np.max(cell_mass-cell_capacity[comp_cells])))
                sign_v=0.0
                for oldv,newv in zip(cex_x0,x):
                    if oldv>0:sign_v=max(sign_v,max(0.0,-float(newv)))
                    elif oldv<0:sign_v=max(sign_v,max(0.0,float(newv)))
                halo_neg=max(0.0,-float(np.min(h))) if n_h else 0.0
                max_cv=float(np.max(np.abs(cv_res)))

                if max_cv>CV_TOL_KG or lower_v>CELL_TOL_KG or upper_v>CELL_TOL_KG or sign_v>SIGN_TOL_KG or halo_neg>SIGN_TOL_KG:
                    raise ScientificFail(
                        f"Day{int(day)}_component_{cid}_postsolve_certification",
                        {"max_CV_residual":max_cv,"lower_violation":lower_v,
                         "upper_violation":upper_v,"sign_violation":sign_v,
                         "halo_negative_violation":halo_neg}
                    )

                stage1_total+=float(np.sum(h))
                stage2_completion_total+=float(np.sum(h[ch_comp])) if n_h else 0.0
                stage3_l1_total+=float(np.sum(np.abs(x-cex_x0)))

            repaired_pair_val=pair_val.copy()
            var_key=var_ex_cv.astype(np.int64)*NCELL+var_ex_cell.astype(np.int64)
            frozen_pair_key=frozen_pair_cv.astype(np.int64)*NCELL+frozen_pair_cell.astype(np.int64)
            for k,newv in zip(var_key.tolist(),repaired_ex.tolist()):
                loc=int(np.searchsorted(frozen_pair_key,int(k)))
                if loc>=len(frozen_pair_key) or int(frozen_pair_key[loc])!=int(k):
                    raise GateError(f"Day{int(day)}_existing_pair_key_not_found:{k}")
                repaired_pair_val[loc]=float(newv)

            repaired_delta=np.bincount(pair_cell,weights=repaired_pair_val,minlength=NCELL)
            if len(halo_cv):
                repaired_delta+=np.bincount(halo_cell,weights=repaired_halo,minlength=NCELL)
            repaired_grid=np.asarray(old_grid_mass,dtype=np.float64).reshape(-1)+repaired_delta

            repaired_cv=np.bincount(pair_cv,weights=repaired_pair_val,minlength=NSL*NCV)
            if len(halo_cv):
                repaired_cv+=np.bincount(halo_cv,weights=repaired_halo,minlength=NSL*NCV)
            max_cv_res=float(np.max(np.abs(repaired_cv-cv_delta)))
            min_mass=float(np.min(repaired_grid))
            max_excess=float(np.max(repaired_grid-cell_capacity))
            ledger_res=float(np.sum(repaired_grid)-(
                np.sum(np.asarray(old_grid_mass,dtype=np.float64))+np.sum(cv_delta)
            ))

            if max_cv_res>CV_TOL_KG or min_mass<-CELL_TOL_KG or max_excess>CELL_TOL_KG or abs(ledger_res)>LEDGER_ABS_TOL_KG:
                raise ScientificFail(
                    f"Day{int(day)}_global_projection_certification",
                    {"max_CV_residual":max_cv_res,"minimum_grid_mass":min_mass,
                     "maximum_capacity_excess":max_excess,"ledger_residual":ledger_res}
                )

            try:
                sg=a2e.invert_local_mass(r2,repaired_grid.reshape(GRID),parent_pressure,p_ref,grid_pv)
            except Exception as exc:
                raise ScientificFail(f"Day{int(day)}_projected_mass_inversion",repr(exc)) from exc
            grid_sat=BACKGROUND+np.asarray(sg,dtype=np.float64)
            if float(np.min(grid_sat))<BACKGROUND-1.0e-10 or float(np.max(grid_sat))>BACKGROUND+MAX_SG+1.0e-10:
                raise ScientificFail(
                    f"Day{int(day)}_projected_saturation_bounds",
                    [float(np.min(grid_sat)),float(np.max(grid_sat))]
                )

            return repaired_grid.reshape(GRID),grid_sat,{
                "projection_applied":True,
                "lower_violation_count_before":int(np.sum(lower)),
                "upper_violation_count_before":int(np.sum(upper)),
                "culprit_CV_count":int(len(union_culprit)),
                "eligible_H2_edge_count":int(len(halo_cv)),
                "completion_edge_count_available":int(np.sum(halo_is_completion)),
                "projection_H2_mass_kg":float(stage1_total),
                "projection_completion_mass_kg":float(stage2_completion_total),
                "existing_support_L1_adjustment_kg":float(stage3_l1_total),
                "maximum_per_CV_residual_kg":max_cv_res,
                "maximum_capacity_excess_kg":max_excess,
                "minimum_grid_mass_kg":min_mass,
            }

        scientific_started=True
        recovery.mkdir(parents=True,exist_ok=True)

        # Immutable Day365 and accepted Day370 anchors.
        states:dict[float,dict[str,np.ndarray]]={}
        metas:dict[float,dict[str,Any]]={}

        states[365.0]={
            "cv_mass_kg":parent_cv_mass,
            "cv_saturation":parent_cv_sat,
            "grid_mass_kg":day365_grid_mass,
            "grid_saturation":day365_grid_sat,
        }
        metas[365.0]={
            "previous_day":None,
            "teacher_substeps":0,
            "injected_mass_kg":0.0,
            "produced_mass_kg":0.0,
            "cumulative_injected_mass_kg":0.0,
            "cumulative_produced_mass_kg":0.0,
            "grid_total_mass_kg":d365_total,
            "grid_saturation_min":float(np.min(day365_grid_sat)),
            "grid_saturation_max":float(np.max(day365_grid_sat)),
            "global_mass_residual_kg":0.0,
            "projection_applied":False,
            "projection_H2_mass_kg":0.0,
            "projection_completion_mass_kg":0.0,
            "existing_support_L1_adjustment_kg":0.0,
            "step_runtime_s":0.0,
        }
        states[370.0]={
            "cv_mass_kg":day370_cv_mass,
            "cv_saturation":day370_cv_sat,
            "grid_mass_kg":day370_grid_mass,
            "grid_saturation":day370_grid_sat,
        }
        metas[370.0]={
            "previous_day":365.0,
            "teacher_substeps":day370_substeps,
            "injected_mass_kg":day370_injected,
            "produced_mass_kg":day370_produced,
            "cumulative_injected_mass_kg":day370_injected,
            "cumulative_produced_mass_kg":day370_produced,
            "grid_total_mass_kg":d370_total,
            "grid_saturation_min":float(np.min(day370_grid_sat)),
            "grid_saturation_max":float(np.max(day370_grid_sat)),
            "global_mass_residual_kg":float(d370_total-d370_expected),
            "projection_applied":True,
            "projection_H2_mass_kg":float(r4s.get("accepted_total_H2_mass_kg",0.0)),
            "projection_completion_mass_kg":float(r4s.get("accepted_completion_edge_mass_kg",0.0)),
            "existing_support_L1_adjustment_kg":float(r4s.get("stage3_existing_support_L1_adjustment_kg",0.0)),
            "step_runtime_s":0.0,
        }

        current_arrays=states[370.0]
        cumulative_injected=day370_injected
        cumulative_produced=day370_produced

        for day in CONTINUATION_DAYS:
            cached=load_checkpoint(recovery,float(day),runner_blob)
            if cached is not None:
                arrays,meta=cached
                states[float(day)]=arrays
                metas[float(day)]=meta
                current_arrays=arrays
                cumulative_injected=float(meta["cumulative_injected_mass_kg"])
                cumulative_produced=float(meta["cumulative_produced_mass_kg"])
                print(f"[PASS] reused P2-R6 checkpoint -- Day {day:g}")
                continue

            stage=f"transport_and_projection_to_day_{int(day)}"
            prev_day=float(day-STEP_DAYS)
            old=current_arrays
            t0=time.time()

            teacher=f4.execute_teacher_with_coeff(
                a4=a4,
                r2=r2,
                e37=e37,
                old_mass=np.asarray(old["cv_mass_kg"],dtype=np.float64),
                old_sat=np.asarray(old["cv_saturation"],dtype=np.float64),
                capacity=parent_cv_capacity,
                cv_pressure_mass_coeff=parent_cv_coeff,
                cv_pv_m3=parent_cv_pv,
                face_pressure_psi=parent_face_pressure,
                p_ref_pa=p_ref,
                q_m3_day=parent_weights*SPD,
                nw=nw_cv,no=no_cv,krw_max=krw_cv,kro_max=kro_cv,
                phi_cv=phi_cv,
                cvgeom=cvgeom,
                delta_days=STEP_DAYS,
            )

            new_cv_mass=np.asarray(teacher["future_mass"],dtype=np.float64)
            new_cv_sat=np.asarray(teacher["future_saturation"],dtype=np.float64)

            new_grid_mass,new_grid_sat,pdiag=projected_mapback(
                np.asarray(old["grid_mass_kg"],dtype=np.float64),
                np.asarray(old["cv_mass_kg"],dtype=np.float64),
                np.asarray(old["cv_saturation"],dtype=np.float64),
                new_cv_mass,new_cv_sat,float(day),
            )

            step_injected=float(teacher["injected_mass_kg"])
            step_produced=float(teacher["produced_mass_kg"])
            cumulative_injected+=step_injected
            cumulative_produced+=step_produced

            expected=fsum_array(np.asarray(old["grid_mass_kg"]))+step_injected-step_produced
            actual=fsum_array(new_grid_mass)
            tol=max(LEDGER_ABS_TOL_KG,1.0e-10*max(abs(expected),1.0))
            sci_gate(
                f"Day{int(day)}_grid_mass_ledger",
                abs(actual-expected)<=tol,
                {"actual_kg":actual,"expected_kg":expected,"residual_kg":actual-expected,"tol_kg":tol}
            )

            arrays={
                "cv_mass_kg":new_cv_mass,
                "cv_saturation":new_cv_sat,
                "grid_mass_kg":new_grid_mass,
                "grid_saturation":new_grid_sat,
            }
            meta={
                "previous_day":prev_day,
                "teacher_substeps":int(teacher["substeps"]),
                "injected_mass_kg":step_injected,
                "produced_mass_kg":step_produced,
                "cumulative_injected_mass_kg":cumulative_injected,
                "cumulative_produced_mass_kg":cumulative_produced,
                "global_mass_residual_kg":float(actual-expected),
                "grid_total_mass_kg":actual,
                "grid_saturation_min":float(np.min(new_grid_sat)),
                "grid_saturation_max":float(np.max(new_grid_sat)),
                "pass_through_activation_events":int(teacher["pass_through_activation_events"]),
                "step_runtime_s":float(time.time()-t0),
                **pdiag,
            }
            save_checkpoint(recovery,float(day),runner_blob,arrays,meta)
            print(f"[PASS] durable P2-R6 checkpoint published -- Day {day:g}")

            states[float(day)]=arrays
            metas[float(day)]=meta
            current_arrays=arrays

        stage="consolidation"
        days=SNAPSHOT_DAYS.copy()
        gate("all_28_snapshot_days_present",all(float(d) in states for d in days),
             [float(d) for d in days if float(d) not in states])

        cv_mass=np.stack([states[float(d)]["cv_mass_kg"] for d in days],axis=0)
        cv_sat=np.stack([states[float(d)]["cv_saturation"] for d in days],axis=0)
        grid_mass=np.stack([states[float(d)]["grid_mass_kg"] for d in days],axis=0)
        grid_sat=np.stack([states[float(d)]["grid_saturation"] for d in days],axis=0)

        rows=[]
        for d in days:
            m=metas[float(d)]
            rows.append({
                "day":float(d),
                "grid_total_mass_kg":float(m["grid_total_mass_kg"]),
                "grid_saturation_min":float(m["grid_saturation_min"]),
                "grid_saturation_max":float(m["grid_saturation_max"]),
                "teacher_substeps":int(m.get("teacher_substeps",0)),
                "step_injected_mass_kg":float(m.get("injected_mass_kg",0.0)),
                "step_produced_mass_kg":float(m.get("produced_mass_kg",0.0)),
                "cumulative_injected_mass_kg":float(m.get("cumulative_injected_mass_kg",0.0)),
                "cumulative_produced_mass_kg":float(m.get("cumulative_produced_mass_kg",0.0)),
                "global_mass_residual_kg":float(m.get("global_mass_residual_kg",0.0)),
                "projection_applied":bool(m.get("projection_applied",False)),
                "lower_violation_count_before":int(m.get("lower_violation_count_before",0)),
                "upper_violation_count_before":int(m.get("upper_violation_count_before",0)),
                "culprit_CV_count":int(m.get("culprit_CV_count",0)),
                "eligible_H2_edge_count":int(m.get("eligible_H2_edge_count",0)),
                "completion_edge_count_available":int(m.get("completion_edge_count_available",0)),
                "projection_H2_mass_kg":float(m.get("projection_H2_mass_kg",0.0)),
                "projection_completion_mass_kg":float(m.get("projection_completion_mass_kg",0.0)),
                "existing_support_L1_adjustment_kg":float(m.get("existing_support_L1_adjustment_kg",0.0)),
                "step_runtime_s":float(m.get("step_runtime_s",0.0)),
            })

        initial_total=fsum_array(grid_mass[0])
        final_total=fsum_array(grid_mass[-1])
        total_injected=sum(float(metas[float(d)].get("injected_mass_kg",0.0)) for d in days[1:])
        total_produced=sum(float(metas[float(d)].get("produced_mass_kg",0.0)) for d in days[1:])
        end_residual=final_total-(initial_total+total_injected-total_produced)
        end_tol=max(LEDGER_ABS_TOL_KG,1.0e-10*max(abs(final_total),1.0))
        sci_gate("P2R6_end_to_end_global_mass_ledger",
                 abs(end_residual)<=end_tol,
                 {"residual_kg":end_residual,"tolerance_kg":end_tol})

        stage="artifact_publication"
        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R6_Final_Artifacts"
        if local.exists():shutil.rmtree(local)
        local.mkdir(parents=True)
        plot_dir=local/"plots"
        qplots=plot_metrics(rows,plot_dir)
        pplots=plot_plumes(days,grid_sat,plot_dir)

        snapshot_path=local/"POSTV16_AV4_PIVOT_P2_R6_Dense_5Day_Snapshots.npz"
        with snapshot_path.open("wb") as fp:
            np.savez_compressed(
                fp,
                target_days=days,
                cv_component_mass_kg=cv_mass,
                cv_saturation=cv_sat,
                grid_component_mass_kg=grid_mass,
                grid_saturation=grid_sat,
                frozen_pressure_psi=parent_pressure,
                frozen_streamline_xyz_m=parent_xyz,
                frozen_streamline_tof_s=parent_tof,
                frozen_streamline_weight_m3_s=parent_weights,
                frozen_streamline_face_pressure_psi=parent_face_pressure,
                xi=xi,
                R4_accepted_day370_state_sha256=np.asarray(r4s["accepted_state_sha256"]),
            )
        snapshot_sha=sha256_file(snapshot_path)

        projection_days=[float(r["day"]) for r in rows if bool(r["projection_applied"])]
        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "start_day":START_DAY,
            "repaired_anchor_day":REPAIRED_DAY,
            "end_day":END_DAY,
            "spacing_days":STEP_DAYS,
            "snapshot_count":int(len(days)),
            "continuation_interval_count":int(len(CONTINUATION_DAYS)),
            "flow_epoch_frozen_at_day":365.0,
            "pressure_refresh_executed":False,
            "support_growth_executed":False,
            "vertical_support_used":False,
            "diagonal_support_used":False,
            "training_executed":False,
            "R4_accepted_day370_state_sha256":r4s["accepted_state_sha256"],
            "dense_snapshot_file":"POSTV16_AV4_PIVOT_P2_R6_Dense_5Day_Snapshots.npz",
            "dense_snapshot_sha256":snapshot_sha,
            "projection_applied_day_count":int(len(projection_days)),
            "projection_applied_days":projection_days,
            "maximum_step_absolute_mass_residual_kg":float(max(abs(float(r["global_mass_residual_kg"])) for r in rows)),
            "end_to_end_mass_residual_kg":float(end_residual),
            "end_to_end_mass_tolerance_kg":float(end_tol),
            "quantitative_plot_count":len(qplots),
            "threeD_plume_plot_count":len(pplots),
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "scientific_interpretation":(
                "P2 is now closed as one shared 5-day-resolution frozen-flow transport trajectory "
                "from Day365 through Day500. Day370 uses the accepted R4 conservative projection; "
                "Days375-500 preserve the same frozen Day365 pressure/Darcy/Pollock/TOF field and "
                "the exact frozen R4 component-frontier H2 eligibility graph. This trajectory is "
                "the common state basis for exact flow-refresh diagnostics before cadence policies are compared."
            ),
            "AV4_PIVOT_P3_authorized":True,
            "P3_name":"Dense 5-Day Exact Flow-Refresh Diagnostic Sweep",
            "P3_required_days":[float(x) for x in days],
            "candidate_cadences_days":[50.0,5.0],
            "periodic_cadence_selected_now":False,
            "P4_authorized":False,
            "P5_training_authorized":False,
            "R3R6R1_execution_invalidated":False,
        }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R6_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R6_Dense_Snapshot_Metrics.csv").write_bytes(csv_bytes(rows))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R6_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists():raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*194)
        print("POSTV16-AV4-PIVOT-P2-R6: PASS")
        print("Dense snapshots published             :",len(days))
        print("Snapshot days                         :",days.tolist())
        print("Projection-applied days               :",projection_days)
        print("End-to-end mass residual kg           :",end_residual)
        print("Dense snapshot SHA256                 :",snapshot_sha)
        print("P3 authorized                         : True")
        print("P4 authorized                         : False")
        print("="*194)
        return 0

    except ScientificFail as exc:
        fail_dir.mkdir(parents=True,exist_ok=True)
        p=fail_dir/"POSTV16_AV4_PIVOT_P2_R6_Scientific_Fail_Report.json"
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
                "pressure_refresh_authorized":False,
                "AV4_PIVOT_P3_authorized":False,
                "P4_authorized":False,
                "P5_training_authorized":False,
                "R3R6R1_execution_invalidated":False,
            },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(MILESTONE+": SCIENTIFIC FAIL")
        print("Stage:",stage)
        print("Gate:",exc.gate)
        print("Detail:",exc.detail)
        return 3

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R6_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "scientific_execution_started":scientific_started,
                "automatic_rerun_authorized":False,
                "AV4_PIVOT_P3_authorized":False,
                "P4_authorized":False,
                "P5_training_authorized":False,
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
