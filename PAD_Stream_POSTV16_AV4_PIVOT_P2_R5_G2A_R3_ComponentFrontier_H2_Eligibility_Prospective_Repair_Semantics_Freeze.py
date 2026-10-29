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


MILESTONE = "POSTV16-AV4-PIVOT-P2-R5-G2A-R3"
STATUS_PASS = (
    "AV4PIVOTP2R5G2AR3_COMPONENT_FRONTIER_H2_ELIGIBILITY_"
    "PROSPECTIVE_REPAIR_SEMANTICS_FREEZE_PASS_NO_REPAIR_EXECUTION"
)
STATUS_BLOCKED = "AV4PIVOTP2R5G2AR3_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "37efc92f2f2603ca144a5d2d62751dda8ec30075"
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

EXPECTED_TARGET_CVS=327
EXPECTED_COMPLETION_EDGES=46915
EXPECTED_BASELINE_H2_EDGES=402976
EXPECTED_FAILED_COMPONENT_CVS=49627
EXPECTED_FAILED_COMPONENT_CELLS=23845
EXPECTED_FAILED_EXISTING_VARIABLES=59220

BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

PARENT_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_R1_AuthorityBinding_Typo_Closure_and_Deterministic_Sensitivity"
PARENT_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_R1_Summary.json"
PARENT_DECISION="POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_R1_Decision_Contract.json"
PARENT_VARIANTS="POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_R1_Sensitivity_Variants.csv"
PARENT_STATUS=(
    "AV4PIVOTP2R5G2AR2R1R1_AUTHORITY_BINDING_TYPO_CLOSURE_"
    "AND_DETERMINISTIC_SENSITIVITY_EXECUTION_PASS"
)
# The immutable parent runner accidentally serialized an extra "-R1" in its MILESTONE
# string. Bind that raw anomaly exactly; do not rewrite history.
PARENT_RAW_MILESTONE="POSTV16-AV4-PIVOT-P2-R5-G2A-R2-R1-R1-R1"
PARENT_CANONICAL_STEP="POSTV16-AV4-PIVOT-P2-R5-G2A-R2-R1-R1"
PARENT_CLASS="LOCAL_H2_EDGE_ELIGIBILITY_CONTROLS_THE_NETWORK_CUT"
PARENT_CANDIDATE_RULE="component_frontier_completion_for_all_baseline_slack_CVs"

R1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Infeasibility_Localization_Audit"
R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R1_Summary.json"
R1_CSV="POSTV16_AV4_PIVOT_P2_R5_G2A_R1_CV_Slack_Diagnostics.csv"
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

OUT_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R3_ComponentFrontier_H2_Eligibility_Repair_Semantics_Freeze"
BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R3_BLOCKED"

R2SRC="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
E37A="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D="PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB="890088c0c0fcab415a2c7351c5079ca8ee12bf82"
PARENTRUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R2_R1_R1_AuthorityBinding_Typo_Closure_and_Deterministic_Sensitivity_Execution.py"
PARENTRUN_BLOB="bc40aa49cca53ee37daa22b4791d97440389476a"

SOURCE_BLOBS={
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
    PARENTRUN:PARENTRUN_BLOB,
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
    assert len(h2xy_from_cells(np.asarray([c],dtype=np.int64),{c}))==12
    print("POSTV16 AV4 PIVOT P2-R5-G2A-R3 structural self-test: PASS")


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
    print("POSTV16-AV4-PIVOT-P2-R5-G2A-R3 -- COMPONENT-FRONTIER H2 ELIGIBILITY PROSPECTIVE REPAIR SEMANTICS FREEZE")
    print("="*194)
    print("DESIGN/FREEZE ONLY. NO LP REPAIR EXECUTION. NO ACCEPTED STATE. NO NEW CARTESIAN CELLS.")
    print("THE FROZEN H2-XY CELL DOMAIN, PRESSURE STATE, CELL BOUNDS, AND EXISTING-EDGE SIGN RULES REMAIN UNCHANGED.")
    print()

    try:
        stage="formal_outcome_firewall"
        psum=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R3_Summary.json"
        block=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_R3_Blocked_Report.json"
        if psum.is_file():
            print("[PASS] formal G2A-R3 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_G2AR3_BLOCK",not block.exists(),str(block))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_R2R1R1_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,
             git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",
             repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="parent_PASS_binding"
        pdir=drive/PARENT_REL
        ps=load_json(pdir/PARENT_SUMMARY)
        pd=load_json(pdir/PARENT_DECISION)
        pv=read_csv(pdir/PARENT_VARIANTS)

        gate("parent_status_exact",ps.get("status")==PARENT_STATUS,ps.get("status"))
        gate("parent_raw_milestone_anomaly_exact",ps.get("milestone")==PARENT_RAW_MILESTONE,ps.get("milestone"))
        gate("parent_classification_exact",ps.get("classification")==PARENT_CLASS,ps.get("classification"))
        gate("parent_candidate_rule_exact",ps.get("candidate_rule_if_any")==PARENT_CANDIDATE_RULE,ps.get("candidate_rule_if_any"))
        gate("parent_R3_authorized",pd.get("P2_R5_G2A_R3_authorized") is True,pd.get("P2_R5_G2A_R3_authorized"))
        gate("parent_R3_name_exact",
             pd.get("P2_R5_G2A_R3_name")=="Component-Frontier H2 Eligibility Prospective Repair Semantics Freeze",
             pd.get("P2_R5_G2A_R3_name"))
        gate("parent_design_authorized",
             pd.get("prospective_component_frontier_H2_eligibility_design_authorized") is True)
        gate("parent_sign_audit_not_authorized",
             pd.get("sign_preservation_physical_admissibility_audit_authorized") is False)
        gate("parent_residual_topology_audit_not_authorized",
             pd.get("residual_network_cut_domain_topology_audit_authorized") is False)
        gate("parent_repair_execution_not_authorized",pd.get("repair_execution_authorized") is False)
        gate("parent_support_expansion_not_authorized",pd.get("further_support_expansion_execution_authorized") is False)
        gate("parent_P3_unauthorized",pd.get("P3_authorized") is False)

        vmap={r["variant"]:r for r in pv}
        gate("V0_present","V0_CURRENT_G2A" in vmap)
        gate("V1_present","V1_ZERO_H2_SLACK_CV_COMPONENT_FRONTIER_COMPLETION" in vmap)
        gate("V2_present","V2_ALL_SLACK_CV_COMPONENT_FRONTIER_COMPLETION" in vmap)
        gate("V3_not_required","V3_V2_PLUS_EXISTING_SIGN_RELAXATION_FOR_BASELINE_SLACK_CVS" not in vmap)
        v0=float(vmap["V0_CURRENT_G2A"]["minimum_total_CV_conservation_slack_kg"])
        v1=float(vmap["V1_ZERO_H2_SLACK_CV_COMPONENT_FRONTIER_COMPLETION"]["minimum_total_CV_conservation_slack_kg"])
        v2=float(vmap["V2_ALL_SLACK_CV_COMPONENT_FRONTIER_COMPLETION"]["minimum_total_CV_conservation_slack_kg"])
        gate("V0_nonzero_slack",v0>SLACK_TOL_KG,v0)
        gate("V1_nonzero_slack",v1>SLACK_TOL_KG,v1)
        gate("V2_zero_within_tolerance",abs(v2)<=SLACK_TOL_KG,v2)
        gate("V2_extra_edge_count_exact",
             int(vmap["V2_ALL_SLACK_CV_COMPONENT_FRONTIER_COMPLETION"]["extra_edge_count"])==EXPECTED_COMPLETION_EDGES,
             vmap["V2_ALL_SLACK_CV_COMPONENT_FRONTIER_COMPLETION"]["extra_edge_count"])

        stage="R1_target_set_binding"
        r1dir=drive/R1_REL
        r1s=load_json(r1dir/R1_SUMMARY)
        r1rows=read_csv(r1dir/R1_CSV)
        gate("R1_status_exact",r1s.get("status")==R1_STATUS,r1s.get("status"))
        slack_rows=[r for r in r1rows if float(r["absolute_conservation_slack_kg"])>SLACK_TOL_KG]
        target_cvs=np.asarray(sorted({int(r["cv_id"]) for r in slack_rows}),dtype=np.int64)
        gate("target_CV_count_exact",len(target_cvs)==EXPECTED_TARGET_CVS,len(target_cvs))
        gate("all_target_CVs_original_upper_culprits",
             all(str(r["is_upper_culprit"]).lower()=="true" for r in slack_rows))

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

        stage="prospective_edge_manifest_reconstruction"
        r2=load_module(root/R2SRC,"av4_pivot_g2ar3_r2")
        e37=load_module(root/E37A,"av4_pivot_g2ar3_e37")
        sg7d=load_module(root/SG7D,"av4_pivot_g2ar3_sg7d")

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

        gate("target_CVs_subset_upper_culprits",
             set(target_cvs.tolist()).issubset(set(upper_culprit.tolist())))

        existing_mask=union_mask[pair_cv]
        existing_cv=pair_cv[existing_mask]
        existing_cell=pair_cell[existing_mask]
        s0=np.unique(existing_cell)
        s0_set=set(int(x) for x in s0.tolist())
        halo=np.asarray(sorted(h2xy_from_cells(s0,s0_set)),dtype=np.int64)
        halo_set=set(int(x) for x in halo.tolist())

        # Original two-sided S0 graph before any H2 halo merging.
        cv_local0={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local0={int(c):n for n,c in enumerate(s0.tolist())}
        d0=DSU(len(union_culprit)+len(s0));off0=len(union_culprit)
        for cv,cell in zip(existing_cv.tolist(),existing_cell.tolist()):
            d0.union(cv_local0[int(cv)],off0+cell_local0[int(cell)])
        orig_root_of_cv={int(cv):d0.find(cv_local0[int(cv)]) for cv in union_culprit.tolist()}
        orig_root_of_cell={int(c):d0.find(off0+cell_local0[int(c)]) for c in s0.tolist()}

        frontier_by_root={}
        for c in s0.tolist():
            root_id=orig_root_of_cell[int(c)]
            frontier_by_root.setdefault(root_id,set()).update(
                h2xy_from_cells(np.asarray([c],dtype=np.int64),s0_set)
            )

        # Current G2A H2 edges: upper culprit CV to H2 cells in the local H2 envelope
        # of each of that CV's existing support cells.
        current_edges=set()
        ue=upper_mask[pair_cv]
        for cv,cell in zip(pair_cv[ue].tolist(),pair_cell[ue].tolist()):
            local=h2xy_from_cells(np.asarray([int(cell)],dtype=np.int64),s0_set)
            for h in local:
                if h in halo_set:
                    current_edges.add((int(cv),int(h)))

        # Prospective completion: each authoritative target CV may access every H2 cell
        # associated with its ORIGINAL two-sided S0 component. No new cells are created.
        completion_edges=set()
        for cv in target_cvs.tolist():
            root_id=orig_root_of_cv[int(cv)]
            for h in frontier_by_root.get(root_id,set()):
                if h in halo_set:
                    completion_edges.add((int(cv),int(h)))
        completion_edges-=current_edges

        gate("completion_edge_count_exact",len(completion_edges)==EXPECTED_COMPLETION_EDGES,len(completion_edges))

        # Bind the target CVs to the deterministic failed G2A expanded component.
        all_cells=np.union1d(s0,halo).astype(np.int64)
        cv_local={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local={int(c):n for n,c in enumerate(all_cells.tolist())}
        dsu=DSU(len(union_culprit)+len(all_cells));off=len(union_culprit)
        for cv,cell in zip(existing_cv.tolist(),existing_cell.tolist()):
            dsu.union(cv_local[int(cv)],off+cell_local[int(cell)])
        current_edges_sorted=sorted(current_edges)
        for cv,h in current_edges_sorted:
            dsu.union(cv_local[int(cv)],off+cell_local[int(h)])
        target_roots=sorted({dsu.find(cv_local[int(cv)]) for cv in target_cvs.tolist()})
        gate("all_target_CVs_share_one_G2A_expanded_component",len(target_roots)==1,target_roots)
        failed_root=target_roots[0]
        roots=sorted({dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()})
        deterministic_index=int(roots.index(failed_root))
        gate("failed_component_index_exact",deterministic_index==5,deterministic_index)

        comp_cvs=np.asarray(
            [cv for cv in union_culprit.tolist() if dsu.find(cv_local[int(cv)])==failed_root],
            dtype=np.int64
        )
        comp_set=set(int(x) for x in comp_cvs.tolist())
        ex_nonzero=(np.abs(pair_val)>SIGN_TOL_KG)&union_mask[pair_cv]
        ex_cv=pair_cv[ex_nonzero];ex_cell=pair_cell[ex_nonzero]
        ex_idx=np.flatnonzero(np.asarray([int(cv) in comp_set for cv in ex_cv],dtype=bool))
        comp_edges=[e for e in current_edges_sorted if e[0] in comp_set]
        comp_hcell=np.asarray([e[1] for e in comp_edges],dtype=np.int64)
        comp_cells=np.unique(np.r_[ex_cell[ex_idx],comp_hcell]).astype(np.int64)

        gate("failed_component_CV_count_exact",len(comp_cvs)==EXPECTED_FAILED_COMPONENT_CVS,len(comp_cvs))
        gate("failed_component_cell_count_exact",len(comp_cells)==EXPECTED_FAILED_COMPONENT_CELLS,len(comp_cells))
        gate("failed_component_existing_variable_count_exact",len(ex_idx)==EXPECTED_FAILED_EXISTING_VARIABLES,len(ex_idx))
        gate("failed_component_baseline_H2_edge_count_exact",len(comp_edges)==EXPECTED_BASELINE_H2_EDGES,len(comp_edges))

        # Exact, deterministic prospective edge manifest.
        manifest_rows=[]
        for cv,h in sorted(completion_edges):
            k,j,i=ijk(int(h))
            root_id=orig_root_of_cv[int(cv)]
            manifest_rows.append({
                "cv_id":int(cv),
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
                "original_S0_component_root_internal":int(root_id),
                "halo_flat_cell":int(h),
                "k":int(k),"j":int(j),"i":int(i),
                "new_edge_nonnegative_deposition_only":True,
                "same_layer_H2_domain_only":True,
            })

        target_rows=[]
        for cv in target_cvs.tolist():
            target_rows.append({
                "cv_id":int(cv),
                "streamline":int(cv//NCV),
                "cv_node":int(cv%NCV),
                "required_day365_to_day370_delta_kg":float(cv_delta[int(cv)]),
                "original_S0_component_root_internal":int(orig_root_of_cv[int(cv)]),
                "completion_edge_count":int(sum(1 for a,_ in completion_edges if a==int(cv))),
            })

        design={
            "canonical_milestone":MILESTONE,
            "parent_provenance":{
                "canonical_parent_step":PARENT_CANONICAL_STEP,
                "immutable_parent_raw_milestone_field":PARENT_RAW_MILESTONE,
                "parent_status":PARENT_STATUS,
                "parent_commit":EXPECTED_PARENT,
                "note":"Parent PASS artifact contains one extra -R1 in its raw MILESTONE field; retained exactly and not rewritten.",
            },
            "day370_target_CV_selection":{
                "source":"authoritative G2A-R1 minimum-CV-conservation-slack diagnostic",
                "rule":"all CVs with absolute conservation slack > 1e-8 kg in the frozen baseline G2A failed component",
                "target_CV_count":int(len(target_cvs)),
                "all_are_original_upper_culprits":True,
            },
            "frozen_H2_cell_domain":{
                "definition":"same-layer Manhattan distance 1 or 2 from the two-sided S0 cell set; S0 excluded",
                "new_cartesian_cells_added_by_R3":0,
                "vertical_support":False,
                "diagonal_support":False,
                "halo_transit":False,
                "reverse_halo_edges":False,
            },
            "prospective_completion_edge_rule":{
                "rule":"for each of the 327 authoritative target CVs, add a nonnegative terminal-deposition edge to every frozen H2 cell belonging to the H2 frontier of that CV's original two-sided S0 connected component, excluding edges already present in baseline G2A",
                "completion_edge_count":int(len(completion_edges)),
                "negative_withdrawal_on_completion_edges":False,
                "existing_baseline_H2_edges_preserved":True,
                "existing_S0_support_preserved":True,
            },
            "hard_execution_constraints_for_successor":{
                "exact_per_CV_mass_conservation":True,
                "cartesian_cell_mass_lower_bound_kg":0.0,
                "cartesian_cell_mass_upper_bound":"frozen Day365-pressure physical cell capacity",
                "existing_nonzero_pair_sign_preservation":True,
                "existing_zero_pairs_remain_zero":True,
                "nonculprit_existing_pairs_unchanged":True,
                "completion_edges_nonnegative_only":True,
                "pressure_refresh":False,
                "clipping":False,
                "global_renormalization":False,
            },
            "lexicographic_objective_for_successor":[
                "1_minimize_total_H2_terminal_deposition_mass_over_baseline_plus_completion_edges",
                "2_within_stage1_optimum_minimize_total_mass_on_new_component_frontier_completion_edges",
                "3_within_stage1_and_stage2_optima_minimize_L1_deviation_of_existing_nonzero_culprit_CV_cell_contributions",
            ],
            "R3_executes_repair":False,
            "R3_creates_accepted_state":False,
        }

        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R5_G2A_R3_Final_Artifacts"
        if local.exists():shutil.rmtree(local)
        local.mkdir(parents=True)

        completion_csv=csv_bytes(manifest_rows)
        target_csv=csv_bytes(target_rows)
        completion_sha=hashlib.sha256(completion_csv).hexdigest()
        target_sha=hashlib.sha256(target_csv).hexdigest()

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "parent_raw_milestone_anomaly_preserved":True,
            "parent_raw_milestone_field":PARENT_RAW_MILESTONE,
            "parent_canonical_step":PARENT_CANONICAL_STEP,
            "parent_classification":PARENT_CLASS,
            "baseline_G2A_slack_kg":v0,
            "V1_slack_kg":v1,
            "V2_slack_kg":v2,
            "target_CV_count":int(len(target_cvs)),
            "completion_edge_count":int(len(completion_edges)),
            "completion_edge_manifest_sha256":completion_sha,
            "target_CV_manifest_sha256":target_sha,
            "H2_cell_domain_changed":False,
            "new_cartesian_cell_count":0,
            "vertical_support_used":False,
            "existing_sign_rule_changed":False,
            "repair_executed":False,
            "accepted_state_created":False,
            "P3_authorized":False,
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "selected_prospective_repair_rule":PARENT_CANDIDATE_RULE,
            "P2_R5_G2A_R4_controlled_repair_execution_authorized":True,
            "P2_R5_G2A_R4_name":"Controlled Component-Frontier H2 Eligibility Exact CV-Conservative Projection Execution",
            "completion_edge_manifest_sha256":completion_sha,
            "target_CV_manifest_sha256":target_sha,
            "repair_execution_authorized_now":False,
            "further_support_expansion_execution_authorized":False,
            "physics_relaxation_authorized":False,
            "pressure_refresh_authorized":False,
            "P3_authorized":False,
            "R3R6R1_execution_invalidated":False,
            "design_contract":design,
        }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R3_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R3_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R3_Design_Contract.json").write_bytes(json_bytes(design))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R3_Target_CVs.csv").write_bytes(target_csv)
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R3_ComponentFrontier_Completion_Edges.csv").write_bytes(completion_csv)

        artifact_manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                artifact_manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R5_G2A_R3_Artifact_Manifest.csv").write_bytes(csv_bytes(artifact_manifest))

        if out.exists():raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*194)
        print("POSTV16-AV4-PIVOT-P2-R5-G2A-R3: PASS")
        print("Parent raw milestone anomaly preserved        :",PARENT_RAW_MILESTONE)
        print("Canonical parent step                         :",PARENT_CANONICAL_STEP)
        print("Target CV count                               :",len(target_cvs))
        print("Completion edge count                         :",len(completion_edges))
        print("V0/V1/V2 slack kg                             :",v0,"/",v1,"/",v2)
        print("H2 cell domain changed                        : False")
        print("Vertical support                              : False")
        print("Existing sign rule changed                    : False")
        print("Repair executed                               : False")
        print("R4 controlled repair execution authorized     : True")
        print("P3 authorized                                 : False")
        print("="*194)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G2A_R3_Blocked_Report.json"
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
