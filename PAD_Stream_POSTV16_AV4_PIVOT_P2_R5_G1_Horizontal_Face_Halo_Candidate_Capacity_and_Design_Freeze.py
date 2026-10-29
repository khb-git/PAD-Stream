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


MILESTONE = "POSTV16-AV4-PIVOT-P2-R5-G1"
STATUS_PASS = (
    "AV4PIVOTP2R5G1_SINGLE_RING_HORIZONTAL_FACE_HALO_CANDIDATE_"
    "CAPACITY_AND_DESIGN_FREEZE_PASS_NO_SUPPORT_EXPANSION_EXECUTED"
)
STATUS_BLOCKED = "AV4PIVOTP2R5G1_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "33e6a892fc697aff98db9e02fe65ad5330b18417"
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

CELL_TOL_KG = 1.0e-7
CAPACITY_TOL_KG = 1.0e-6
PAIR_TOL_KG = 1.0e-10
HALO_ENTRY_COST = 5.0

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R1_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_R1_TwoSided_Bound_Culprit_Domain_Freeze"
R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_R1_Summary.json"
R1_DECISION = "POSTV16_AV4_PIVOT_P2_R5_R1_Decision_Contract.json"
R1_COMPONENTS = "POSTV16_AV4_PIVOT_P2_R5_R1_TwoSided_Support_Components.csv"
R1_STATUS = (
    "AV4PIVOTP2R5R1_TWOSIDED_BOUND_CULPRIT_DOMAIN_AND_EXISTING_SUPPORT_"
    "FEASIBILITY_DESIGN_FREEZE_PASS_NO_REPAIR_EXECUTION"
)
R1_SELECTED = "EXISTING_SUPPORT_NECESSARY_CONDITIONS_INCOMPLETE_GEOMETRIC_DOMAIN_AUDIT_REQUIRED"

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

OUT_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_G1_Horizontal_Face_Halo_Candidate_Freeze"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R5_G1_BLOCKED"

R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"
AV1_FREEZE = "PAD_Stream_POSTV16_AV1_D_R7_R7D_Horizontal_Face_Halo_Occupancy_Domain_Freeze.py"
AV1_FREEZE_BLOB = "bd2873f7fb6b98d4e857c98864b78e2da6f202a4"
AV1_EXEC = "PAD_Stream_POSTV16_AV1_D_R7_R7E_Frozen_Horizontal_Face_Halo_Occupancy_Domain_Execution.py"
AV1_EXEC_BLOB = "9f99d9dcab649ba7ac911ad09ad79b4e0eb2ecc8"

SOURCE_BLOBS = {
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
    AV1_FREEZE:AV1_FREEZE_BLOB,
    AV1_EXEC:AV1_EXEC_BLOB,
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


def horizontal_neighbors(flat:int)->list[int]:
    k=flat//(NY*NX)
    rem=flat%(NY*NX)
    j=rem//NX
    i=rem%NX
    out=[]
    if i>0: out.append(flat-1)
    if i<NX-1: out.append(flat+1)
    if j>0: out.append(flat-NX)
    if j<NY-1: out.append(flat+NX)
    return out


def self_test()->None:
    # Nonrecursive same-layer x/y face-neighbor geometry.
    center=1*(NY*NX)+10*NX+10
    n=set(horizontal_neighbors(center))
    assert n=={center-1,center+1,center-NX,center+NX}
    assert all((x//(NY*NX))==(center//(NY*NX)) for x in n)
    assert HALO_ENTRY_COST==5.0
    print("POSTV16 AV4 PIVOT P2-R5-G1 structural self-test: PASS")


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
    print("POSTV16-AV4-PIVOT-P2-R5-G1 -- SINGLE-RING HORIZONTAL FACE-HALO CANDIDATE CAPACITY / DESIGN FREEZE")
    print("="*190)
    print("DESIGN/AUDIT ONLY. NO LP. NO MAPBACK REPAIR. NO SUPPORT EXPANSION EXECUTION.")
    print("Candidate: one non-recursive same-layer x/y face-neighbor H1 ring; H1 is positive-deposition terminal occupancy only.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G1_Summary.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G1_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal G1 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_G1_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_R5R1_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",repr(git_text(root,"status","--porcelain")))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="R5R1_binding"
        r1dir=drive/R1_REL
        r1s=load_json(r1dir/R1_SUMMARY)
        r1d=load_json(r1dir/R1_DECISION)
        gate("R5R1_status_exact",r1s.get("status")==R1_STATUS,r1s.get("status"))
        gate("R5R1_selected_semantics_exact",r1s.get("selected_next_semantics")==R1_SELECTED,r1s.get("selected_next_semantics"))
        gate("R5R1_geometric_design_authorized",r1d.get("geometric_support_domain_design_authorized") is True,r1d.get("geometric_support_domain_design_authorized"))
        gate("R5R1_support_expansion_execution_not_authorized",r1d.get("support_expansion_execution_authorized") is False,r1d.get("support_expansion_execution_authorized"))
        gate("R5R1_P3_unauthorized",r1d.get("P3_authorized") is False,r1d.get("P3_authorized"))
        gate("R5R1_parent_clean",int(r1s.get("day365_parent_upper_violation_count",-1))==0,r1s.get("day365_parent_upper_violation_count"))
        gate("R5R1_no_uncovered_bound_cells",
             int(r1s.get("uncovered_lower_violation_cell_count",-1))==0
             and int(r1s.get("uncovered_upper_violation_cell_count",-1))==0,
             [r1s.get("uncovered_lower_violation_cell_count"),r1s.get("uncovered_upper_violation_cell_count")])
        gate("R5R1_component_necessary_bounds_failed",r1s.get("all_components_necessary_mass_bounds_ok") is False,r1s.get("all_components_necessary_mass_bounds_ok"))

        r1_components=read_csv(r1dir/R1_COMPONENTS)
        gate("R5R1_component_CSV_nonempty",len(r1_components)>0,len(r1_components))

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
        f2path=drive/F2R3_REL/F2R3_STATE
        a2path=drive/A2E_REL/A2E_EPOCH
        a2sum=drive/A2E_REL/A2E_SUMMARY
        gate("A2E_status_exact",load_json(a2sum).get("status")==A2E_STATUS,load_json(a2sum).get("status"))

        with np.load(f2path,allow_pickle=False) as z:
            parent_cv_mass=np.asarray(z["parent_CV_component_mass_kg"],dtype=np.float64)
            parent_cv_sat=np.asarray(z["parent_CV_saturation"],dtype=np.float64)
            parent_cv_pv=np.asarray(z["parent_CV_pore_volume_m3"],dtype=np.float64)
            parent_cv_coeff=np.asarray(z["parent_CV_pressure_mass_coeff"],dtype=np.float64)

        with np.load(a2path,allow_pickle=False) as z:
            epoch={k:np.asarray(z[k]).copy() for k in z.files}
        parent_grid_mass=np.asarray(epoch["parent_component_mass_kg"],dtype=np.float64)
        parent_pressure=np.asarray(epoch["refreshed_pressure_psi"],dtype=np.float64)
        grid_pv=np.asarray(epoch["pore_volume_m3"],dtype=np.float64)
        parent_xyz=np.asarray(epoch["streamline_xyz_m"],dtype=np.float64)
        parent_tof=np.asarray(epoch["streamline_tof_s"],dtype=np.float64)
        parent_weights=np.asarray(epoch["streamline_weight_m3_s"],dtype=np.float64)
        p_ref=float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))

        stage="reconstruct_day370_and_twosided_domain"
        r2=load_module(root/R2SRC,"av4_pivot_p2r5g1_r2")
        e37=load_module(root/E37A,"av4_pivot_p2r5g1_e37")
        sg7d=load_module(root/SG7D,"av4_pivot_p2r5g1_sg7d")

        operator=sg7d.build_subsegment_operator(parent_xyz,parent_tof/SPD,parent_weights*SPD)
        geometry=e37.build_control_volume_geometry(r2,operator,parent_pressure,p_ref,NSL,NCV)
        gate("parent_CV_pv_matches_F2R3",
             float(np.max(np.abs(np.asarray(geometry["cv_pv_m3"])-parent_cv_pv)))<=1.0e-8,
             float(np.max(np.abs(np.asarray(geometry["cv_pv_m3"])-parent_cv_pv))))
        gate("parent_CV_coeff_matches_F2R3",
             relative_l2(np.asarray(geometry["cv_pressure_mass_coeff"]),parent_cv_coeff)<=1.0e-12,
             relative_l2(np.asarray(geometry["cv_pressure_mass_coeff"]),parent_cv_coeff))

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
        gate("per_CV_transfer_closure",
             float(np.max(np.abs(transfer-cv_delta)))<=1.0e-7,
             float(np.max(np.abs(transfer-cv_delta))))

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
        lower_pair=lower[pair_cell] & (pair_val < -PAIR_TOL_KG)
        upper_pair=upper[pair_cell] & (pair_val > PAIR_TOL_KG)
        lower_culprit=np.unique(pair_cv[lower_pair]).astype(np.int64)
        upper_culprit=np.unique(pair_cv[upper_pair]).astype(np.int64)
        union_culprit=np.union1d(lower_culprit,upper_culprit).astype(np.int64)

        union_mask=np.zeros(NSL*NCV,dtype=bool)
        union_mask[union_culprit]=True
        support_mask=union_mask[pair_cv]
        support_cv=pair_cv[support_mask]
        support_cell=pair_cell[support_mask]
        support_val=pair_val[support_mask]
        s0=np.unique(support_cell)

        gate("S0_cell_count_reproduces_R5R1",
             len(s0)==int(r1s["two_sided_support_cell_count"]),
             {"G1":len(s0),"R5R1":r1s["two_sided_support_cell_count"]})

        stage="build_nonrecursive_horizontal_H1"
        s0_set=set(int(x) for x in s0.tolist())
        h1_set=set()
        parent_pairs=set()
        for cell in s0.tolist():
            for nb in horizontal_neighbors(int(cell)):
                if nb in s0_set:
                    continue
                h1_set.add(int(nb))
                parent_pairs.add((int(cell),int(nb)))

        h1=np.asarray(sorted(h1_set),dtype=np.int64)
        gate("H1_nonempty",len(h1)>0,len(h1))
        gate("H1_disjoint_S0",len(set(h1.tolist()) & s0_set)==0)
        gate("no_vertical_halo",
             all((a//(NY*NX))==(b//(NY*NX)) for a,b in parent_pairs))
        gate("every_H1_has_S0_xy_face_parent",
             all(any((a,b)==pp for pp in parent_pairs) for b in h1.tolist() for a in [next(a for a,bb in parent_pairs if bb==b)]))

        # Map each S0 cell to component using the same union-CV/support graph.
        cv_local={int(cv):n for n,cv in enumerate(union_culprit.tolist())}
        cell_local={int(c):n for n,c in enumerate(s0.tolist())}
        dsu=DSU(len(union_culprit)+len(s0))
        offset=len(union_culprit)
        for cv,cell in zip(support_cv.tolist(),support_cell.tolist()):
            dsu.union(cv_local[int(cv)],offset+cell_local[int(cell)])
        roots=sorted({dsu.find(cv_local[int(cv)]) for cv in union_culprit.tolist()})
        root_to_component={root:i for i,root in enumerate(roots)}
        s0_component={}
        for cell in s0.tolist():
            root_id=dsu.find(offset+cell_local[int(cell)])
            s0_component[int(cell)]=root_to_component[root_id]

        gate("component_count_reproduces_R5R1",
             len(roots)==int(r1s["two_sided_support_component_count"]),
             {"G1":len(roots),"R5R1":r1s["two_sided_support_component_count"]})

        # Candidate H1 parent-component relationships.
        h1_parent_components={int(h):set() for h in h1.tolist()}
        for s,h in parent_pairs:
            h1_parent_components[int(h)].add(int(s0_component[int(s)]))

        shared_h1=[h for h,comps in h1_parent_components.items() if len(comps)>1]
        max_parent_components=max(len(v) for v in h1_parent_components.values()) if h1_parent_components else 0

        h1_spare=np.maximum(capacity[h1]-future_grid[h1],0.0)
        h1_spare_by_cell={int(c):float(s) for c,s in zip(h1.tolist(),h1_spare.tolist())}

        # Upper-culprit CV -> H1 candidate edges. Positive-deposition only.
        upper_mask=np.zeros(NSL*NCV,dtype=bool)
        upper_mask[upper_culprit]=True
        upper_support_mask=upper_mask[pair_cv]
        upper_support_cv=pair_cv[upper_support_mask]
        upper_support_cell=pair_cell[upper_support_mask]

        cv_h1_pairs=set()
        for cv,cell in zip(upper_support_cv.tolist(),upper_support_cell.tolist()):
            for nb in horizontal_neighbors(int(cell)):
                if nb in h1_set:
                    cv_h1_pairs.add((int(cv),int(nb)))
        gate("candidate_upper_CV_to_H1_edges_nonempty",len(cv_h1_pairs)>0,len(cv_h1_pairs))

        stage="component_candidate_capacity_audit"
        prior={int(r["component_id"]):r for r in r1_components}
        component_rows=[]
        all_deficient_components_have_candidate_spare=True
        sum_component_deficits=0.0

        for cid in range(len(roots)):
            r=prior.get(cid)
            if r is None:
                raise GateError(f"missing_R5R1_component_row:{cid}")
            required=float(r["required_final_component_mass_kg"])
            s0cap=float(r["component_capacity_total_kg"])
            deficit=max(required-s0cap,0.0)
            sum_component_deficits+=deficit

            comp_h1=[h for h,comps in h1_parent_components.items() if cid in comps]
            spare=sum(h1_spare_by_cell[h] for h in comp_h1)
            sufficient=spare+CAPACITY_TOL_KG>=deficit
            if deficit>CAPACITY_TOL_KG:
                all_deficient_components_have_candidate_spare &= sufficient

            component_rows.append({
                "component_id":cid,
                "S0_support_cell_count":int(r["support_cell_count"]),
                "S0_required_final_mass_kg":required,
                "S0_capacity_kg":s0cap,
                "S0_capacity_deficit_kg":deficit,
                "candidate_H1_cell_count":int(len(comp_h1)),
                "candidate_H1_spare_capacity_kg":float(spare),
                "candidate_H1_spare_minus_deficit_kg":float(spare-deficit),
                "candidate_H1_necessary_capacity_sufficient":bool(sufficient),
            })

        unique_h1_spare=float(np.sum(h1_spare))
        global_candidate_spare_sufficient=unique_h1_spare+CAPACITY_TOL_KG>=sum_component_deficits

        stage="candidate_design_freeze"
        if all_deficient_components_have_candidate_spare and global_candidate_spare_sufficient:
            selected=(
                "SINGLE_NONRECURSIVE_SAME_LAYER_XY_FACE_HALO_"
                "POSITIVE_DEPOSITION_TERMINAL_EXTENSION_V1"
            )
            g2_authorized=True
            alternative_design_authorized=False
            rationale=(
                "The AV1-certified one-ring horizontal face-halo geometry provides at least the necessary "
                "candidate spare capacity for every deficient two-sided support component and globally. "
                "This is not a feasibility proof because H1 cells may be shared across components and "
                "per-CV sign/equality constraints have not been solved. A controlled G2 LP execution is authorized."
            )
        else:
            selected="SINGLE_RING_HORIZONTAL_HALO_NECESSARY_CAPACITY_INSUFFICIENT"
            g2_authorized=False
            alternative_design_authorized=True
            rationale=(
                "At least one deficient existing-support component, or the global unique H1 inventory, lacks "
                "the necessary one-ring horizontal spare capacity. The single-ring candidate is not authorized "
                "for execution; a different prospective geometric domain must be designed."
            )

        design={
            "protocol_id":"POSTV16_AV4_PIVOT_P2_R5_G1_SINGLE_RING_HORIZONTAL_FACE_HALO_V1",
            "selected_candidate":selected,
            "exact_S0":"two-sided lower+upper culprit CV existing SG7D/E37A support cells",
            "H1_definition":"all in-bounds cells not in S0 sharing an x-face or y-face with an S0 cell",
            "H1_nonrecursive":True,
            "vertical_neighbors_allowed":False,
            "diagonal_neighbors_allowed":False,
            "second_ring_neighbors_allowed":False,
            "H1_role":"terminal positive-deposition occupancy only",
            "H1_reverse_edges_allowed":False,
            "H1_to_H1_transit_allowed":False,
            "negative_withdrawal_H1_edges_allowed":False,
            "new_CV_H1_edge_rule":"upper-bound culprit CV may connect positively to H1 only when one of its existing support cells is x/y-face adjacent to that H1 cell",
            "existing_CV_cell_support_preserved":True,
            "new_edge_original_contribution_kg":0.0,
            "new_edge_sign":"nonnegative only",
            "halo_entry_cost_units":HALO_ENTRY_COST,
            "halo_entry_cost_source":"AV1 R7-R7D/R7-R7E certified 20-ft horizontal step convention",
            "G1_executes_LP":False,
            "G1_executes_support_expansion":False,
        }

        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R5_G1_Final_Artifacts"
        if local.exists(): shutil.rmtree(local)
        local.mkdir(parents=True)
        plots=local/"plots"; plots.mkdir()

        fig=plt.figure(figsize=(8,6))
        ax=fig.add_subplot(111,projection="3d")
        kk=s0//(NY*NX); rr=s0%(NY*NX); jj=rr//NX; ii=rr%NX
        ax.scatter(ii,jj,kk,s=8,alpha=0.35,label="S0")
        kh=h1//(NY*NX); rh=h1%(NY*NX); jh=rh//NX; ih=rh%NX
        ax.scatter(ih,jh,kh,s=8,alpha=0.25,label="H1")
        ax.set_xlim(0,NX-1); ax.set_ylim(0,NY-1); ax.set_zlim(0,NZ-1)
        ax.set_xlabel("i"); ax.set_ylabel("j"); ax.set_zlabel("k")
        ax.view_init(elev=24,azim=-58)
        ax.legend()
        ax.set_title("G1 candidate: two-sided S0 + single-ring horizontal H1")
        fig.savefig(plots/"3D_G1_S0_plus_horizontal_H1_candidate.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        fig=plt.figure(figsize=(8,5))
        ax=fig.add_subplot(111)
        ids=[r["component_id"] for r in component_rows if r["S0_capacity_deficit_kg"]>CAPACITY_TOL_KG]
        deficits=[r["S0_capacity_deficit_kg"] for r in component_rows if r["S0_capacity_deficit_kg"]>CAPACITY_TOL_KG]
        spares=[r["candidate_H1_spare_capacity_kg"] for r in component_rows if r["S0_capacity_deficit_kg"]>CAPACITY_TOL_KG]
        ax.scatter(ids,deficits,s=16,label="S0 deficit")
        ax.scatter(ids,spares,s=16,label="candidate H1 spare")
        ax.set_xlabel("Deficient support component")
        ax.set_ylabel("Mass capacity (kg)")
        ax.set_title("G1 necessary capacity audit")
        ax.legend()
        ax.grid(True,alpha=0.25)
        fig.savefig(plots/"G1_component_deficit_vs_candidate_H1_spare.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "S0_cell_count":int(len(s0)),
            "H1_cell_count":int(len(h1)),
            "S0_H1_face_adjacency_count":int(len(parent_pairs)),
            "upper_culprit_CV_count":int(len(upper_culprit)),
            "candidate_upper_CV_H1_edge_count":int(len(cv_h1_pairs)),
            "shared_H1_cell_count":int(len(shared_h1)),
            "maximum_parent_component_count_per_H1_cell":int(max_parent_components),
            "deficient_S0_component_count":int(sum(1 for r in component_rows if r["S0_capacity_deficit_kg"]>CAPACITY_TOL_KG)),
            "total_S0_component_capacity_deficit_kg":float(sum_component_deficits),
            "unique_H1_spare_capacity_kg":float(unique_h1_spare),
            "all_deficient_components_have_candidate_H1_spare":bool(all_deficient_components_have_candidate_spare),
            "global_unique_H1_spare_sufficient":bool(global_candidate_spare_sufficient),
            "selected_candidate":selected,
            "support_expansion_executed":False,
            "LP_executed":False,
            "P3_authorized":False,
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "selected_candidate":selected,
            "selection_rationale":rationale,
            "P2_R5_G2_controlled_expanded_support_LP_authorized":bool(g2_authorized),
            "P2_R5_G2_name":"Controlled Single-Ring Horizontal Face-Halo Two-Sided CV-Conservative Projection Execution" if g2_authorized else None,
            "alternative_geometric_domain_design_authorized":bool(alternative_design_authorized),
            "support_expansion_execution_authorized":bool(g2_authorized),
            "P3_authorized":False,
            "periodic_cadence_selected_now":False,
            "R3R6R1_execution_invalidated":False,
            "design_contract":design,
        }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G1_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G1_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G1_Halo_Design_Contract.json").write_bytes(json_bytes(design))
        (local/"POSTV16_AV4_PIVOT_P2_R5_G1_Component_Candidate_Capacity.csv").write_bytes(csv_bytes(component_rows))

        h1_rows=[]
        for h in h1.tolist():
            k=h//(NY*NX); rem=h%(NY*NX); j=rem//NX; i=rem%NX
            h1_rows.append({
                "flat_cell":int(h),"k":int(k),"j":int(j),"i":int(i),
                "future_mass_kg":float(future_grid[h]),
                "capacity_kg":float(capacity[h]),
                "spare_capacity_kg":float(h1_spare_by_cell[h]),
                "parent_component_count":int(len(h1_parent_components[h])),
            })
        (local/"POSTV16_AV4_PIVOT_P2_R5_G1_H1_Candidate_Cells.csv").write_bytes(csv_bytes(h1_rows))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R5_G1_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists(): raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*190)
        print("POSTV16-AV4-PIVOT-P2-R5-G1: PASS")
        print("S0 cells                                   :",len(s0))
        print("H1 cells                                   :",len(h1))
        print("S0-H1 face adjacencies                     :",len(parent_pairs))
        print("Upper culprit CVs                          :",len(upper_culprit))
        print("Candidate upper-CV -> H1 edges             :",len(cv_h1_pairs))
        print("Shared H1 cells                            :",len(shared_h1))
        print("Deficient S0 components                    :",sum(1 for r in component_rows if r["S0_capacity_deficit_kg"]>CAPACITY_TOL_KG))
        print("Total S0 component capacity deficit kg     :",sum_component_deficits)
        print("Unique H1 spare capacity kg                :",unique_h1_spare)
        print("All deficient components have H1 spare     :",all_deficient_components_have_candidate_spare)
        print("Global unique H1 spare sufficient          :",global_candidate_spare_sufficient)
        print("Selected candidate                         :",selected)
        print("G2 expanded-support LP authorized          :",g2_authorized)
        print("Alternative geometric design authorized    :",alternative_design_authorized)
        print("P3 authorized                              : False")
        print("="*190)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R5_G1_Blocked_Report.json"
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
