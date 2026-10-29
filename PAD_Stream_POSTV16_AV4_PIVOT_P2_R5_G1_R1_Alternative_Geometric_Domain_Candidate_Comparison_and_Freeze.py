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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


MILESTONE = "POSTV16-AV4-PIVOT-P2-R5-G1-R1"
STATUS_PASS = (
    "AV4PIVOTP2R5G1R1_ALTERNATIVE_GEOMETRIC_DOMAIN_CANDIDATE_"
    "COMPARISON_AND_FREEZE_PASS_NO_SUPPORT_EXPANSION_EXECUTED"
)
STATUS_BLOCKED = "AV4PIVOTP2R5G1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "336e9c8efdc1a87dc85085719ac342a2b0733215"
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

CELL_TOL_KG=1.0e-7
CAPACITY_TOL_KG=1.0e-6
PAIR_TOL_KG=1.0e-10

BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G1_Horizontal_Face_Halo_Candidate_Freeze"
G1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G1_Summary.json"
G1_DECISION="POSTV16_AV4_PIVOT_P2_R5_G1_Decision_Contract.json"
G1_STATUS=(
    "AV4PIVOTP2R5G1_SINGLE_RING_HORIZONTAL_FACE_HALO_CANDIDATE_"
    "CAPACITY_AND_DESIGN_FREEZE_PASS_NO_SUPPORT_EXPANSION_EXECUTED"
)
G1_SELECTED="SINGLE_RING_HORIZONTAL_HALO_NECESSARY_CAPACITY_INSUFFICIENT"

R1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_R1_TwoSided_Bound_Culprit_Domain_Freeze"
R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_R1_Summary.json"
R1_COMPONENTS="POSTV16_AV4_PIVOT_P2_R5_R1_TwoSided_Support_Components.csv"

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

OUT_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G1_R1_Alternative_Geometric_Domain_Freeze"
BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G1_R1_BLOCKED"

R2SRC="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
E37A="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D="PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB="890088c0c0fcab415a2c7351c5079ca8ee12bf82"
AV1_FREEZE="PAD_Stream_POSTV16_AV1_D_R7_R7D_Horizontal_Face_Halo_Occupancy_Domain_Freeze.py"
AV1_FREEZE_BLOB="bd2873f7fb6b98d4e857c98864b78e2da6f202a4"

SOURCE_BLOBS={
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
    AV1_FREEZE:AV1_FREEZE_BLOB,
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
    if not rows: return b""
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    buf=io.StringIO(newline="")
    w=csv.DictWriter(buf,fieldnames=fields,lineterminator="\n")
    w.writeheader(); w.writerows(rows)
    return buf.getvalue().encode("utf-8")


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
        ra=self.find(a); rb=self.find(b)
        if ra==rb:return
        if self.r[ra]<self.r[rb]: ra,rb=rb,ra
        self.p[rb]=ra
        if self.r[ra]==self.r[rb]: self.r[ra]+=1


def ijk(flat:int)->tuple[int,int,int]:
    k=flat//(NY*NX)
    rem=flat%(NY*NX)
    j=rem//NX
    i=rem%NX
    return k,j,i


def flat_of(k:int,j:int,i:int)->int:
    return k*(NY*NX)+j*NX+i


def candidate_cells_from_s0(s0:np.ndarray,kind:str)->tuple[np.ndarray,set[tuple[int,int]]]:
    s0_set=set(int(x) for x in s0.tolist())
    cells=set()
    parent_pairs=set()

    for c in s0.tolist():
        k,j,i=ijk(int(c))
        offsets=[]

        if kind=="H2_XY":
            for dj in range(-2,3):
                for di in range(-2,3):
                    d=abs(di)+abs(dj)
                    if 1<=d<=2:
                        offsets.append((0,dj,di))

        elif kind=="H1_6F":
            offsets=[
                (0,0,-1),(0,0,1),(0,-1,0),(0,1,0),
                (-1,0,0),(1,0,0),
            ]

        elif kind=="H2_XY_PLUS_V1":
            for dj in range(-2,3):
                for di in range(-2,3):
                    d=abs(di)+abs(dj)
                    if 1<=d<=2:
                        offsets.append((0,dj,di))
            offsets.extend([(-1,0,0),(1,0,0)])

        else:
            raise ValueError(kind)

        for dk,dj,di in offsets:
            kk=k+dk; jj=j+dj; ii=i+di
            if not (0<=kk<NZ and 0<=jj<NY and 0<=ii<NX):
                continue
            nb=flat_of(kk,jj,ii)
            if nb in s0_set:
                continue
            cells.add(nb)
            parent_pairs.add((int(c),int(nb)))

    return np.asarray(sorted(cells),dtype=np.int64), parent_pairs


def self_test()->None:
    c=flat_of(5,20,20)
    s0=np.asarray([c],dtype=np.int64)
    h2,_=candidate_cells_from_s0(s0,"H2_XY")
    f6,_=candidate_cells_from_s0(s0,"H1_6F")
    comb,_=candidate_cells_from_s0(s0,"H2_XY_PLUS_V1")
    assert len(h2)==12
    assert len(f6)==6
    assert len(comb)==14
    assert all(ijk(int(x))[0]==5 for x in h2)
    print("POSTV16 AV4 PIVOT P2-R5-G1-R1 structural self-test: PASS")


def main(project_root:Path,drive_root:Path)->int:
    root=Path(project_root).resolve()
    drive=Path(drive_root).resolve()
    out=drive/OUT_REL
    block_dir=drive/BLOCK_REL
    stage="preflight"

    def gate(name:str,passed:Any,value:Any=None):
        ok=bool(passed)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok: raise GateError(name)

    print("="*190)
    print("POSTV16-AV4-PIVOT-P2-R5-G1-R1 -- ALTERNATIVE GEOMETRIC DOMAIN CANDIDATE COMPARISON / FREEZE")
    print("="*190)
    print("AUDIT/DESIGN ONLY. NO LP. NO MAPBACK REPAIR. NO SUPPORT EXPANSION EXECUTION.")
    print("Candidates: H2 same-layer lateral envelope; H1 six-face envelope; H2 lateral plus V1.")
    print("Every halo candidate remains terminal positive-deposition occupancy only.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G1_R1_Summary.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G1_R1_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal G1-R1 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_G1R1_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_G1_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="G1_binding"
        g1dir=drive/G1_REL
        g1s=load_json(g1dir/G1_SUMMARY)
        g1d=load_json(g1dir/G1_DECISION)
        gate("G1_status_exact",g1s.get("status")==G1_STATUS,g1s.get("status"))
        gate("G1_selected_candidate_exact",g1s.get("selected_candidate")==G1_SELECTED,g1s.get("selected_candidate"))
        gate("G1_G2_not_authorized",g1d.get("P2_R5_G2_controlled_expanded_support_LP_authorized") is False,g1d.get("P2_R5_G2_controlled_expanded_support_LP_authorized"))
        gate("G1_alternative_design_authorized",g1d.get("alternative_geometric_domain_design_authorized") is True,g1d.get("alternative_geometric_domain_design_authorized"))
        gate("G1_support_expansion_not_authorized",g1d.get("support_expansion_execution_authorized") is False,g1d.get("support_expansion_execution_authorized"))
        gate("G1_P3_unauthorized",g1d.get("P3_authorized") is False,g1d.get("P3_authorized"))

        stage="R5R1_component_binding"
        r1dir=drive/R1_REL
        r1s=load_json(r1dir/R1_SUMMARY)
        r1_components=read_csv(r1dir/R1_COMPONENTS)
        gate("R5R1_component_count_exact",len(r1_components)==int(r1s["two_sided_support_component_count"]),
             {"csv":len(r1_components),"summary":r1s["two_sided_support_component_count"]})

        stage="R3_teacher_binding"
        rec=drive/R3_RECOVERY_REL
        state_path=rec/R3_TEACHER_STATE
        meta_path=rec/R3_TEACHER_META
        meta=load_json(meta_path)
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

        stage="reconstruct_twosided_S0"
        r2=load_module(root/R2SRC,"av4_pivot_p2r5g1r1_r2")
        e37=load_module(root/E37A,"av4_pivot_p2r5g1r1_e37")
        sg7d=load_module(root/SG7D,"av4_pivot_p2r5g1r1_sg7d")
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
        old_sub=old_flat[cv_id]; new_sub=new_flat[cv_id]
        old_sg=np.clip(old_sub-BACKGROUND,0.0,MAX_SG)
        new_sg=np.clip(new_sub-BACKGROUND,0.0,MAX_SG)
        rho_old=np.asarray(r2.gas_density_from_state(old_sub,pseg,p_ref),dtype=np.float64)
        rho_new=np.asarray(r2.gas_density_from_state(new_sub,pseg,p_ref),dtype=np.float64)
        sub_delta=pv*(rho_new*new_sg-rho_old*old_sg)

        cv_delta=(future_cv_mass-parent_cv_mass).reshape(-1)
        transfer=np.bincount(cv_id,weights=sub_delta,minlength=NSL*NCV)
        gate("per_CV_transfer_closure",float(np.max(np.abs(transfer-cv_delta)))<=1.0e-7)

        key=cv_id.astype(np.int64)*NCELL+flat.astype(np.int64)
        order=np.argsort(key,kind="mergesort")
        key_s=key[order]; val_s=sub_delta[order]
        starts=np.r_[0,1+np.flatnonzero(key_s[1:]!=key_s[:-1])]
        pair_key=key_s[starts]
        pair_val=np.add.reduceat(val_s,starts)
        pair_cv=(pair_key//NCELL).astype(np.int64)
        pair_cell=(pair_key%NCELL).astype(np.int64)

        cell_delta=np.bincount(pair_cell,weights=pair_val,minlength=NCELL)
        future_grid=parent_grid_mass.reshape(-1)+cell_delta
        sat_max=np.full(GRID,BACKGROUND+MAX_SG,dtype=np.float64)
        rho_max=np.asarray(r2.gas_density_from_state(sat_max,parent_pressure,p_ref),dtype=np.float64)
        capacity=(grid_pv*rho_max*MAX_SG).reshape(-1)

        lower=future_grid < -CELL_TOL_KG
        upper=future_grid > capacity + CELL_TOL_KG
        lower_culprit=np.unique(pair_cv[lower[pair_cell] & (pair_val<-PAIR_TOL_KG)]).astype(np.int64)
        upper_culprit=np.unique(pair_cv[upper[pair_cell] & (pair_val>PAIR_TOL_KG)]).astype(np.int64)
        union_culprit=np.union1d(lower_culprit,upper_culprit).astype(np.int64)

        union_mask=np.zeros(NSL*NCV,dtype=bool); union_mask[union_culprit]=True
        support_mask=union_mask[pair_cv]
        support_cv=pair_cv[support_mask]
        support_cell=pair_cell[support_mask]
        s0=np.unique(support_cell)
        gate("S0_count_matches_G1",len(s0)==int(g1s["S0_cell_count"]),{"now":len(s0),"G1":g1s["S0_cell_count"]})

        # Reconstruct component membership from S0 graph.
        cv_local={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local={int(c):n for n,c in enumerate(s0.tolist())}
        dsu=DSU(len(union_culprit)+len(s0))
        offset=len(union_culprit)
        for cv,cell in zip(support_cv.tolist(),support_cell.tolist()):
            dsu.union(cv_local[int(cv)],offset+cell_local[int(cell)])
        roots=sorted({dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()})
        root_to_component={root:i for i,root in enumerate(roots)}
        s0_component={int(cell):root_to_component[dsu.find(offset+cell_local[int(cell)])] for cell in s0.tolist()}
        gate("component_count_matches_R5R1",len(roots)==len(r1_components),{"now":len(roots),"R5R1":len(r1_components)})

        upper_mask=np.zeros(NSL*NCV,dtype=bool); upper_mask[upper_culprit]=True
        upper_support=(upper_mask[pair_cv])
        upper_support_cv=pair_cv[upper_support]
        upper_support_cell=pair_cell[upper_support]

        stage="candidate_comparison"
        prior={int(r["component_id"]):r for r in r1_components}
        candidates=["H2_XY","H1_6F","H2_XY_PLUS_V1"]
        candidate_results={}
        component_rows=[]

        for kind in candidates:
            halo,parent_pairs=candidate_cells_from_s0(s0,kind)
            halo_set=set(int(x) for x in halo.tolist())

            # Candidate cell -> parent components.
            cell_parent_components={int(h):set() for h in halo.tolist()}
            for s,h in parent_pairs:
                cell_parent_components[int(h)].add(int(s0_component[int(s)]))

            spare=np.maximum(capacity[halo]-future_grid[halo],0.0)
            spare_by={int(c):float(v) for c,v in zip(halo.tolist(),spare.tolist())}

            # Prospective positive CV->halo terminal edges.
            cv_halo_pairs=set()
            for cv,cell in zip(upper_support_cv.tolist(),upper_support_cell.tolist()):
                k,j,i=ijk(int(cell))
                # Reuse the same candidate geometry relative to this CV's existing support cell.
                local_halo,_=candidate_cells_from_s0(np.asarray([int(cell)],dtype=np.int64),kind)
                for h in local_halo.tolist():
                    if int(h) in halo_set:
                        cv_halo_pairs.add((int(cv),int(h)))

            deficient=0
            insufficient=0
            total_deficit=0.0
            for cid in range(len(roots)):
                r=prior[cid]
                required=float(r["required_final_component_mass_kg"])
                s0cap=float(r["component_capacity_total_kg"])
                deficit=max(required-s0cap,0.0)
                if deficit>CAPACITY_TOL_KG:
                    deficient+=1
                    total_deficit+=deficit
                comp_halo=[h for h,comps in cell_parent_components.items() if cid in comps]
                comp_spare=sum(spare_by[h] for h in comp_halo)
                sufficient=(comp_spare+CAPACITY_TOL_KG>=deficit)
                if deficit>CAPACITY_TOL_KG and not sufficient:
                    insufficient+=1
                component_rows.append({
                    "candidate":kind,
                    "component_id":cid,
                    "S0_capacity_deficit_kg":deficit,
                    "candidate_halo_cell_count":len(comp_halo),
                    "candidate_halo_spare_kg":comp_spare,
                    "candidate_spare_minus_deficit_kg":comp_spare-deficit,
                    "necessary_capacity_sufficient":bool(sufficient),
                })

            unique_spare=float(np.sum(spare))
            global_ok=unique_spare+CAPACITY_TOL_KG>=total_deficit
            per_component_ok=(insufficient==0)
            candidate_results[kind]={
                "halo_cell_count":int(len(halo)),
                "S0_halo_parent_pair_count":int(len(parent_pairs)),
                "candidate_upper_CV_halo_edge_count":int(len(cv_halo_pairs)),
                "shared_halo_cell_count":int(sum(1 for comps in cell_parent_components.values() if len(comps)>1)),
                "maximum_parent_component_count_per_halo_cell":int(max((len(comps) for comps in cell_parent_components.values()),default=0)),
                "deficient_component_count":int(deficient),
                "insufficient_component_count":int(insufficient),
                "total_S0_capacity_deficit_kg":float(total_deficit),
                "unique_halo_spare_capacity_kg":unique_spare,
                "all_deficient_components_have_candidate_spare":bool(per_component_ok),
                "global_unique_spare_sufficient":bool(global_ok),
                "necessary_capacity_candidate_pass":bool(per_component_ok and global_ok),
            }

        # Deterministic priority: preserve lateral-only semantics before introducing vertical occupancy.
        if candidate_results["H2_XY"]["necessary_capacity_candidate_pass"]:
            selected="H2_XY_TWO_RING_SAME_LAYER_TERMINAL_OCCUPANCY_ENVELOPE"
            exec_authorized=True
            selection_basis="First passing candidate in frozen priority: preserve lateral-only semantics before cross-layer occupancy."
        elif candidate_results["H1_6F"]["necessary_capacity_candidate_pass"]:
            selected="H1_6FACE_SINGLE_RING_TERMINAL_OCCUPANCY_ENVELOPE"
            exec_authorized=True
            selection_basis="H2-XY failed; immediate six-face one-ring candidate passes necessary capacity and is the next frozen candidate."
        elif candidate_results["H2_XY_PLUS_V1"]["necessary_capacity_candidate_pass"]:
            selected="H2_XY_PLUS_V1_TERMINAL_OCCUPANCY_ENVELOPE"
            exec_authorized=True
            selection_basis="Neither smaller candidate passed; combined two-ring lateral plus one vertical ring passes necessary capacity."
        else:
            selected="NO_TESTED_ALTERNATIVE_CANDIDATE_PASSES_NECESSARY_CAPACITY"
            exec_authorized=False
            selection_basis="All three prospective finite-domain candidates fail at least one necessary component or global capacity condition."

        design={
            "selection_priority":["H2_XY","H1_6F","H2_XY_PLUS_V1"],
            "priority_reason":"preserve lateral-only occupancy semantics first; introduce cross-layer occupancy only if lateral-only enlargement is insufficient",
            "H2_XY":{
                "definition":"same-layer Manhattan distance 1 or 2 from S0; S0 excluded",
                "halo_transit":False,
                "reverse_edges":False,
                "vertical_neighbors":False,
                "terminal_positive_deposition_only":True,
            },
            "H1_6F":{
                "definition":"one immediate x/y/z face-neighbor ring around S0; S0 excluded",
                "halo_transit":False,
                "reverse_edges":False,
                "diagonal_neighbors":False,
                "second_ring":False,
                "terminal_positive_deposition_only":True,
            },
            "H2_XY_PLUS_V1":{
                "definition":"union of H2 same-layer Manhattan envelope and immediate vertical face neighbors",
                "halo_transit":False,
                "reverse_edges":False,
                "diagonal_neighbors":False,
                "terminal_positive_deposition_only":True,
            },
            "new_edge_rule":"upper-bound culprit CV may connect nonnegatively to a candidate terminal halo cell only if that halo cell lies in the frozen candidate envelope of one of that CV's existing S0 support cells",
            "negative_withdrawal_halo_edges_allowed":False,
            "existing_support_preserved":True,
            "G1R1_executes_LP":False,
            "G1R1_executes_support_expansion":False,
        }

        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R5_G1_R1_Final_Artifacts"
        if local.exists(): shutil.rmtree(local)
        local.mkdir(parents=True)
        plots=local/"plots"; plots.mkdir()

        # Comparison plot.
        fig=plt.figure(figsize=(8,5))
        ax=fig.add_subplot(111)
        names=candidates
        insuff=[candidate_results[n]["insufficient_component_count"] for n in names]
        ax.bar(names,insuff)
        ax.set_ylabel("Deficient components still lacking candidate spare")
        ax.set_title("Alternative geometric candidate comparison")
        ax.grid(True,axis="y",alpha=0.25)
        fig.savefig(plots/"G1R1_candidate_insufficient_component_count.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        fig=plt.figure(figsize=(8,5))
        ax=fig.add_subplot(111)
        spare=[candidate_results[n]["unique_halo_spare_capacity_kg"] for n in names]
        deficit=[candidate_results[n]["total_S0_capacity_deficit_kg"] for n in names]
        x=np.arange(len(names))
        ax.bar(x-0.18,deficit,width=0.36,label="S0 deficit")
        ax.bar(x+0.18,spare,width=0.36,label="unique candidate spare")
        ax.set_xticks(x,names)
        ax.set_ylabel("Mass capacity (kg)")
        ax.set_title("Candidate global capacity")
        ax.legend()
        ax.grid(True,axis="y",alpha=0.25)
        fig.savefig(plots/"G1R1_candidate_global_deficit_vs_spare.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "G1_selected_candidate":g1s["selected_candidate"],
            "G1_global_spare_sufficient":g1s["global_unique_H1_spare_sufficient"],
            "G1_all_components_sufficient":g1s["all_deficient_components_have_candidate_H1_spare"],
            "candidates":candidate_results,
            "selected_candidate":selected,
            "controlled_expanded_support_execution_authorized":bool(exec_authorized),
            "support_expansion_executed":False,
            "LP_executed":False,
            "P3_authorized":False,
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "selected_candidate":selected,
            "selection_basis":selection_basis,
            "P2_R5_G2A_controlled_selected_domain_LP_authorized":bool(exec_authorized),
            "P2_R5_G2A_name":"Controlled Selected Alternative Terminal-Occupancy Domain Two-Sided CV-Conservative Projection Execution" if exec_authorized else None,
            "further_geometric_domain_design_authorized":bool(not exec_authorized),
            "support_expansion_execution_authorized":bool(exec_authorized),
            "P3_authorized":False,
            "periodic_cadence_selected_now":False,
            "R3R6R1_execution_invalidated":False,
            "design_contract":design,
        }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G1_R1_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G1_R1_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G1_R1_Design_Contract.json").write_bytes(json_bytes(design))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G1_R1_Component_Candidate_Comparison.csv").write_bytes(csv_bytes(component_rows))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R5_G1_R1_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists(): raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*190)
        print("POSTV16-AV4-PIVOT-P2-R5-G1-R1: PASS")
        for name in candidates:
            r=candidate_results[name]
            print(f"{name} halo cells                              :",r["halo_cell_count"])
            print(f"{name} insufficient deficient components       :",r["insufficient_component_count"])
            print(f"{name} unique spare capacity kg                 :",r["unique_halo_spare_capacity_kg"])
            print(f"{name} necessary capacity candidate PASS        :",r["necessary_capacity_candidate_pass"])
        print("Selected candidate                              :",selected)
        print("Controlled selected-domain LP authorized        :",exec_authorized)
        print("Further geometric design authorized             :",not exec_authorized)
        print("P3 authorized                                   : False")
        print("="*190)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G1_R1_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "automatic_rerun_authorized":False,
                "support_expansion_execution_authorized":False,
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
