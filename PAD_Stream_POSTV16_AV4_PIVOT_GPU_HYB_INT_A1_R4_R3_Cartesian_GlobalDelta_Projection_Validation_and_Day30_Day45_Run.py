#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, csr_matrix, hstack, vstack, eye

M="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R4-R3"
PASS="POSTV16AV4PIVOTGPUHYBINTA1R4R3_CARTESIAN_GLOBAL_DELTA_PROJECTION_VALIDATION_AND_DAY30_DAY45_RUN_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBINTA1R4R3_TECHNICAL_CONSERVATION_CARTESIAN_PROJECTION_CAPACITY_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="10801978cfe513c617f7387cd112b3e8ef8bd757"

R3R2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R2_Cartesian_GlobalDelta_Mapback_Projection_Design_Freeze.py"
R3R2_BLOB="bfccb23789f4c87595bc7891b51d858c65cefc44"
R3R2_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R3R2_CARTESIAN_GLOBAL_DELTA_MAPBACK_PROJECTION_DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"
R4R2R1R1_FORMAL_BLOCK_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R4R2R1R1_TECHNICAL_CONSERVATION_DELTA_OWNERSHIP_CAPACITY_OR_AUTHORITY_BLOCK"
R4R2R1R1_FORMAL_BLOCK_EXCEPTION="GateError('delta_ownership_negative_child_target:-0.8723954285500215:1e-08')"

R4R2R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R2_R1_Tightened_HiGHS_Feasibility_DeltaOwnership_Run.py"
R4R2R1_BLOB="30b1420ed6821a3e070717e4c9d4016f9cdcd156"
R4R2R1_LOCAL_TECHNICAL_FAILURE="self_referential_source_text_structural_assertion"

R4R2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R2_BoundedOccupancy_DeltaOwnership_Validation_and_Day30_Day45_Run.py"
R4R2_BLOB="368a200eaca4cf0833963c8be5156d873d8056b6"
R4R2_LOCAL_TECHNICAL_FAILURE="synthetic_per_CV_delta_identity_assertion_at_default_HiGHS_feasibility"
HIGHS_PRIMAL_FEASIBILITY_TOL=1.0e-9
HIGHS_DUAL_FEASIBILITY_TOL=1.0e-9
SCIENTIFIC_DELTA_IDENTITY_GATE_KG=1.0e-8

R3R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R1_Corrected_BoundedOccupancy_DeltaOwnership_Design_Freeze.py"
R3R1_BLOB="a96c6a4ca50a109cc1ed8eb54f696b4c7ae541b6"
R3R1_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R3R1_CORRECTED_BOUNDED_OCCUPANCY_DELTA_OWNERSHIP_DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"

R4R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R1_CertifiedParent_Replay_Ownership_Validation_and_Day30_Day45_Run.py"
R4R1_BLOB="570c21db62d0b6636c5de895fdb0425ecb701db6"
R4R1_BLOCK_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R4R1_TECHNICAL_CONSERVATION_OWNERSHIP_CAPACITY_OR_AUTHORITY_BLOCK"
R4R1_EXCEPTION_PREFIX="GateError('parent_ownership_stageA_infeasible:2:"

F2R3_RUNNER="PAD_Stream_POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution.py"
F2R3_BLOB="359f3c0edf87e10bb4006cacdd271cd426fed22b"
E37A_DELTA_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

R4_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_Ownership_Reconciliation_Local_Validation_and_Day30_Day45_Run.py"
R4_BLOB="ac7a9e20321ad74c0ce75928cd72642bacaff3e6"
R4_BLOCK_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R4_TECHNICAL_CONSERVATION_OWNERSHIP_CAPACITY_OR_AUTHORITY_BLOCK"
R4_EXPECTED_FAILED_STAGE="controlled_integrated_rollout"
R4_EXPECTED_EXCEPTION="GateError('first_negative_mapback_not_certified_parent:30.0:30.003412917596155')"

R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_ParentOwnership_Mapback_Reconciliation_Design_Freeze.py"
R3_BLOB="cb9aab3b5c9a6310f4337e22c3d4c207e814b66c"
F4EXEC_RUNNER="PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_Ownership_Reconciled_Event_MapBack_and_Flow_Refresh_Execution.py"
F4EXEC_BLOB="b2c129bd067ef75163c3f06de5c15adc53ae5633"
KNOWN_FAILED_PARENT_DAY=30.003412917596155
KNOWN_FAILED_PARENT_DAY_TOL=1.0e-12

INTA1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_Controlled_Integrated_Day30_Day45_WholeSystem_Run.py"
INTA1_BLOB="4b78313ab08827f3dcc0f63ee5f603df6390b2c1"
INTA1_BLOCK_STATUS="POSTV16AV4PIVOTGPUHYBINTA1_TECHNICAL_CONSERVATION_CAPACITY_OR_AUTHORITY_BLOCK"
INTA1_EXPECTED_FAILED_STAGE="controlled_integrated_rollout"
INTA1_EXPECTED_EXCEPTION="TrialReject('aligned_mapback_negative_cell_mass:-13.558883110855225')"

G3R7_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R7_Controlled_Integrated_Controller_Shadow_Execution_Protocol_Freeze.py"
G3R7_BLOB="2204b827987a2027cc9e6bda8b27582d4b713d60"
G3R5_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R5_Reconciled_Runtime_Controller_Shadow_Implementation_and_Test.py"
G3R5_BLOB="0675eaac7e1c47601dada82e295beaab0076c998"
G2R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Rank3_Day40_45_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2R3_BLOB="b06a18d93e68dca2c3d7326cc8b76e4116999117"
A8_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A8_Day100_Production_Trajectory_Validation.py"
A8_BLOB="65006bfdc44630746d4c45c6d8696560b70efef6"
A1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A1_R1_ReadOnly_Hybrid_ComponentMass_Bridge_TOF_Identity_Repair.py"
A1_BLOB="6b0bff953b11b393affc429825622fe4afdc5942"
B1_RUNNER="PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB="8d9561d7c85805b82dedc26073c4633f90eeeab6"
E11_RUNNER="PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
E11_BLOB="bf89c14a3cb177fb483e233a17b72e824d31119b"
R3R5_RUNNER="PAD_Stream_V16E41R3R5_Multi_Refresh_Cadence_Sensitivity_Runtime_Refresh_Policy_Calibration.py"
R3R5_BLOB="15aae3224ba4337cad72f9b4aa9166d602791349"
R3R4_RUNNER="PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4_BLOB="5f8433437ce111533338ceada922f51abb2edefe"
R2_REPAIR_RUNNER="PAD_Stream_V16E41R2_Capacity_Aware_Conservative_MapBack_Timestep_Repair.py"
R2_REPAIR_BLOB="f6961c48dc47c5fb55f2af658ef4ce429eb66533"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G3R7_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R7_Controlled_Integrated_Controller_Shadow_Execution_Protocol_Freeze"
G3R7_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R7_Summary.json"
G3R7_PROTOCOL="POSTV16_AV4_PIVOT_GPU_HYB_G3_R7_INT_A1_Protocol.json"
G3R7_DECISION="POSTV16_AV4_PIVOT_GPU_HYB_G3_R7_Decision_Contract.json"
G3R7_STATUS="POSTV16AV4PIVOTGPUHYBG3R7_CONTROLLED_INTEGRATED_CONTROLLER_SHADOW_EXECUTION_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"

R3_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_ParentOwnership_Mapback_Reconciliation_Design_Freeze"
R3_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_Summary.json"
R3_PROTOCOL="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_Frozen_Reconciliation_Protocol.json"
R3_HANDOFF="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R4_Execution_Handoff_Contract.json"
R3_DECISION="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_Decision_Contract.json"
R3_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R3_PARENT_OWNERSHIP_MAPBACK_RECONCILIATION_DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"

R4_BLOCK_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_BLOCKED"
R4_BLOCK_REPORT="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_Blocked_Report.json"

R3R1_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R1_Corrected_BoundedOccupancy_DeltaOwnership_Design_Freeze"
R3R1_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R1_Summary.json"
R3R1_PROTOCOL="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R1_Corrected_Reconciliation_Protocol.json"
R3R1_HANDOFF="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R1_R4_R2_Execution_Handoff_Contract.json"
R3R1_DECISION="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R1_Decision_Contract.json"

R3R2_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R2_Cartesian_GlobalDelta_Mapback_Projection_Design_Freeze"
R3R2_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R2_Summary.json"
R3R2_PROTOCOL="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R2_Frozen_Projection_Protocol.json"
R3R2_HANDOFF="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R2_R4_R3_Execution_Handoff_Contract.json"
R3R2_DECISION="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R2_Decision_Contract.json"
R4R2R1R1_FORMAL_BLOCK_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R2_R1_R1_BLOCKED"
R4R2R1R1_FORMAL_BLOCK_REPORT="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R2_R1_R1_Blocked_Report.json"

R4R1_BLOCK_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R1_BLOCKED"
R4R1_BLOCK_REPORT="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R1_Blocked_Report.json"

INTA1_BLOCK_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_BLOCKED"
INTA1_BLOCK_REPORT="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_Blocked_Report.json"

TARGET_DAY=45.0
START_DAY=30.0
MAX_FLOW_EPOCH_DAYS=5.0
SCHEDULED_REFRESH_DAYS=(30.0,35.0,40.0,45.0)
VIS_DAYS=(30.0,35.0,40.0,45.0)
DAY_TO_S=86400.0
FT_TO_M=0.3048
INJECTOR_MASS_RATE_KG_DAY=500_000.0
EXPECTED_GRID=(15,50,50)
POLICY_NAME="G3_RECONCILED_FIVE_DAY_DEVELOPMENT_SHADOW"
NEGATIVE_MAPBACK_RETRY_FACTOR=0.5
MAX_NEGATIVE_MAPBACK_RETRIES=12

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R3"
OUT_REL=BASE/(OUT_TOKEN+"_Cartesian_GlobalDelta_Projection_Validation_and_Day30_Day45_Run")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
STEPS=f"{OUT_TOKEN}_Accepted_Transitions.csv"
REFRESHES=f"{OUT_TOKEN}_Flow_Refreshes.csv"
CAPACITY=f"{OUT_TOKEN}_Capacity_Events.csv"
CONTROLLER=f"{OUT_TOKEN}_Controller_Events.csv"
MAPBACK_RETRIES=f"{OUT_TOKEN}_PreValidation_Negative_Mapback_Timestep_Retries.csv"
OWNERSHIP=f"{OUT_TOKEN}_Cartesian_GlobalDelta_Projection_Audit.csv"
ROUTES=f"{OUT_TOKEN}_Route_Audit.csv"
REFERENCE=f"{OUT_TOKEN}_Reference_Comparison.csv"
CHECKPOINTS=f"{OUT_TOKEN}_Visualization_Checkpoint_Index.csv"
FINAL_STATE=f"{OUT_TOKEN}_Final_Day45_PostRefresh_State.npz"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError):
    pass

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):
            h.update(c)
    return h.hexdigest()

def gt(root:Path,*a:str)->str:
    return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()

def blob(root:Path,p:Path)->str:
    return gt(root,"hash-object",str(p))

def mod(root:Path,fn:str,expected:str,name:str):
    p=root/fn
    if not p.is_file():
        raise GateError(f"missing_source:{fn}")
    actual=blob(root,p)
    if actual!=expected:
        raise GateError(f"source_blob:{fn}:{actual}:{expected}")
    s=importlib.util.spec_from_file_location(name,p)
    if s is None or s.loader is None:
        raise GateError(f"import_spec:{fn}")
    m=importlib.util.module_from_spec(s)
    sys.modules[name]=m
    s.loader.exec_module(m)
    return m

def js(p:Path):
    return json.loads(p.read_text(encoding="utf-8"))

def load_npz(p:Path):
    with np.load(p,allow_pickle=False) as z:
        return {k:np.asarray(z[k]).copy() for k in z.files}

def scalar(x:Any)->float:
    return float(np.asarray(x).reshape(()))

def int_scalar(x:Any)->int:
    return int(np.asarray(x).reshape(()))

def rel_l2(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    return float(np.linalg.norm((a-b).ravel())/max(float(np.linalg.norm(b.ravel())),1e-30))

def write_csv(p:Path,rows:list[dict[str,Any]]):
    rows=list(rows)
    if not rows:
        p.write_text("",encoding="utf-8")
        return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader();w.writerows(rows)

def deterministic_npz_bytes(arrays:dict[str,Any])->bytes:
    outer=io.BytesIO()
    with zipfile.ZipFile(outer,mode="w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for key in sorted(arrays):
            b=io.BytesIO()
            np.save(b,np.asarray(arrays[key]),allow_pickle=False)
            info=zipfile.ZipInfo(f"{key}.npy",date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o600<<16
            zf.writestr(info,b.getvalue())
    return outer.getvalue()

def _fmax(a):
    aa=np.asarray(a,dtype=np.float64)
    return float(np.max(np.abs(aa))) if aa.size else 0.0

def _aggregate_pairs(cv_id,flat_cell,values,ncell):
    cv=np.asarray(cv_id,dtype=np.int64).reshape(-1)
    cell=np.asarray(flat_cell,dtype=np.int64).reshape(-1)
    val=np.asarray(values,dtype=np.float64).reshape(-1)
    if not (len(cv)==len(cell)==len(val)):
        raise GateError("ownership_pair_length_mismatch")
    key=cv*np.int64(ncell)+cell
    uniq,inv=np.unique(key,return_inverse=True)
    sums=np.bincount(inv,weights=val,minlength=len(uniq)).astype(np.float64)
    pair_cv=(uniq//ncell).astype(np.int64)
    pair_cell=(uniq%ncell).astype(np.int64)
    order=np.lexsort((pair_cell,pair_cv))
    return pair_cv[order],pair_cell[order],sums[order],uniq[order]

def _incidence(rows_idx,nrows,ncols):
    cols=np.arange(ncols,dtype=np.int64)
    return coo_matrix((np.ones(ncols,dtype=np.float64),
                       (np.asarray(rows_idx,dtype=np.int64),cols)),
                      shape=(nrows,ncols)).tocsr()


def _bounded_parent_occupancy(cv_id,flat,pv,g0f,cellpv,ncv,ncell):
    cv_id=np.asarray(cv_id,dtype=np.int64).reshape(-1)
    flat=np.asarray(flat,dtype=np.int64).reshape(-1)
    pv=np.asarray(pv,dtype=np.float64).reshape(-1)
    g0f=np.asarray(g0f,dtype=np.float64).reshape(-1)
    if not (len(cv_id)==len(flat)==len(pv)):
        raise GateError("bounded_occupancy_subsegment_length_mismatch")
    if len(g0f)!=ncell:
        raise GateError(f"bounded_occupancy_grid_length_mismatch:{len(g0f)}:{ncell}")
    if not np.isfinite(pv).all() or float(np.min(pv))<0.0:
        raise GateError("bounded_occupancy_invalid_subsegment_pv")
    physical_cell_pv=np.full(ncell,float(cellpv),dtype=np.float64)
    W=np.bincount(flat,weights=pv,minlength=ncell).astype(np.float64)
    denom=np.maximum(physical_cell_pv,W)
    if not np.isfinite(denom).all() or float(np.min(denom))<=0.0:
        raise GateError("bounded_occupancy_invalid_denominator")
    p0sub=g0f[flat]*pv/denom[flat]
    if not np.isfinite(p0sub).all():
        raise GateError("bounded_occupancy_nonfinite_parent_subsegment_mass")
    ntol=max(1e-8,1e-12*max(float(np.max(np.abs(g0f))) if g0f.size else 1.0,1.0))
    if float(np.min(p0sub)) < -ntol:
        raise GateError(f"bounded_occupancy_negative_parent_subsegment_mass:{float(np.min(p0sub))}")
    mapped=np.bincount(flat,weights=p0sub,minlength=ncell).astype(np.float64)
    alpha=np.minimum(1.0,W/physical_cell_pv)
    expected=g0f*alpha
    formula_linf=_fmax(mapped-expected)
    if formula_linf>ntol:
        raise GateError(f"bounded_occupancy_formula_closure:{formula_linf}:{ntol}")
    over=float(np.max(mapped-g0f))
    if over>ntol:
        raise GateError(f"bounded_occupancy_mapped_above_parent:{over}:{ntol}")
    residual=g0f-mapped
    if float(np.min(residual)) < -ntol:
        raise GateError(f"bounded_occupancy_negative_residual:{float(np.min(residual))}:{ntol}")
    pair_cv,pair_cell,p0pair,pair_key=_aggregate_pairs(cv_id,flat,p0sub,ncell)
    o0=np.bincount(pair_cv,weights=p0pair,minlength=ncv).astype(np.float64)
    ledger=float(np.sum(residual)+np.sum(o0)-np.sum(g0f))
    ltol=max(1e-7,1e-12*max(abs(float(np.sum(g0f))),1.0))
    if abs(ledger)>ltol:
        raise GateError(f"bounded_occupancy_parent_split_ledger:{ledger}:{ltol}")
    return {
        "pair_cv":pair_cv,
        "pair_cell":pair_cell,
        "pair_key":pair_key,
        "p0_pair":p0pair,
        "o0_cv":o0,
        "residual":residual,
        "W":W,
        "denom":denom,
        "alpha":alpha,
        "mapped":mapped,
        "formula_linf_kg":formula_linf,
        "parent_split_ledger_kg":ledger,
        "minimum_residual_kg":float(np.min(residual)),
        "mapped_above_parent_max_kg":over,
    }

def _child_stage1(pair_cv,pair_cell,target,o1,available):
    n=len(target); ncv=len(o1); ncell=len(available)
    Aeqx=_incidence(pair_cv,ncv,n); Acell=_incidence(pair_cell,ncell,n); I=eye(n,format="csr")
    Aub=vstack([
        hstack([ I,-I],format="csr"),
        hstack([-I,-I],format="csr"),
        hstack([Acell,csr_matrix((ncell,n))],format="csr"),
    ],format="csr")
    bub=np.concatenate([target,-target,available])
    Aeq=hstack([Aeqx,csr_matrix((ncv,n))],format="csr")
    c=np.concatenate([np.zeros(n),np.ones(n)])
    res=linprog(c,A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=o1,
                bounds=[(0.0,None)]*(2*n),method="highs",
                options={"presolve":True,"primal_feasibility_tolerance":HIGHS_PRIMAL_FEASIBILITY_TOL,"dual_feasibility_tolerance":HIGHS_DUAL_FEASIBILITY_TOL})
    if not res.success:
        raise GateError(f"delta_ownership_stage1_infeasible:{res.status}:{res.message}")
    return np.asarray(res.x[:n],float),float(np.sum(res.x[n:])),{"status":int(res.status),"message":str(res.message)}

def _child_stage2(pair_cv,pair_cell,target,qtarget,o1,available,opt1,tol1):
    n=len(target); ncv=len(o1); ncell=len(available)
    Aeqx=_incidence(pair_cv,ncv,n); Acell=_incidence(pair_cell,ncell,n)
    I=eye(n,format="csr"); Z=csr_matrix((n,n))
    Aub=vstack([
        hstack([ I,-I, Z],format="csr"),
        hstack([-I,-I, Z],format="csr"),
        hstack([ I, Z,-I],format="csr"),
        hstack([-I, Z,-I],format="csr"),
        hstack([Acell,csr_matrix((ncell,2*n))],format="csr"),
    ],format="csr")
    bub=np.concatenate([target,-target,qtarget,-qtarget,available])
    prow=csr_matrix((np.ones(n),
        (np.zeros(n,dtype=np.int64),n+np.arange(n,dtype=np.int64))),
        shape=(1,3*n))
    Aub=vstack([Aub,prow],format="csr"); bub=np.concatenate([bub,[opt1+tol1]])
    Aeq=hstack([Aeqx,csr_matrix((ncv,2*n))],format="csr")
    c=np.concatenate([np.zeros(2*n),np.ones(n)])
    res=linprog(c,A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=o1,
                bounds=[(0.0,None)]*(3*n),method="highs",
                options={"presolve":True,"primal_feasibility_tolerance":HIGHS_PRIMAL_FEASIBILITY_TOL,"dual_feasibility_tolerance":HIGHS_DUAL_FEASIBILITY_TOL})
    if not res.success:
        raise GateError(f"delta_ownership_stage2_infeasible:{res.status}:{res.message}")
    return np.asarray(res.x[:n],float),float(np.sum(res.x[2*n:])),{"status":int(res.status),"message":str(res.message)}

def _child_stage3(pair_cv,pair_cell,target,qtarget,o1,available,opt1,tol1,opt2,tol2):
    n=len(target); ncv=len(o1); ncell=len(available)
    Aeqx=_incidence(pair_cv,ncv,n); Acell=_incidence(pair_cell,ncell,n)
    I=eye(n,format="csr"); Z=csr_matrix((n,n))
    Aub=vstack([
        hstack([ I,-I, Z],format="csr"),
        hstack([-I,-I, Z],format="csr"),
        hstack([ I, Z,-I],format="csr"),
        hstack([-I, Z,-I],format="csr"),
        hstack([Acell,csr_matrix((ncell,2*n))],format="csr"),
    ],format="csr")
    bub=np.concatenate([target,-target,qtarget,-qtarget,available])
    prow=csr_matrix((np.ones(n),
        (np.zeros(n,dtype=np.int64),n+np.arange(n,dtype=np.int64))),
        shape=(1,3*n))
    srow=csr_matrix((np.ones(n),
        (np.zeros(n,dtype=np.int64),2*n+np.arange(n,dtype=np.int64))),
        shape=(1,3*n))
    Aub=vstack([Aub,prow,srow],format="csr")
    bub=np.concatenate([bub,[opt1+tol1,opt2+tol2]])
    Aeq=hstack([Aeqx,csr_matrix((ncv,2*n))],format="csr")
    rank=(np.arange(n,dtype=np.float64)+1.0)/max(float(n),1.0)
    c=np.concatenate([rank,np.zeros(2*n)])
    res=linprog(c,A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=o1,
                bounds=[(0.0,None)]*(3*n),method="highs",
                options={"presolve":True,"primal_feasibility_tolerance":HIGHS_PRIMAL_FEASIBILITY_TOL,"dual_feasibility_tolerance":HIGHS_DUAL_FEASIBILITY_TOL})
    if not res.success:
        raise GateError(f"delta_ownership_stage3_infeasible:{res.status}:{res.message}")
    return np.asarray(res.x[:n],float),float(np.dot(rank,res.x[:n])),{"status":int(res.status),"message":str(res.message)}

def _delta_child_assignment(pair_cv,pair_cell,p0,q1,o0,delta,residual,capacity):
    ncv=len(o0)
    o1_raw=np.asarray(o0,dtype=np.float64)+np.asarray(delta,dtype=np.float64)
    otol=max(1e-8,1e-12*max(float(np.max(np.abs(o1_raw))) if len(o1_raw) else 1.0,1.0))
    omin=float(np.min(o1_raw)) if len(o1_raw) else 0.0
    if omin < -otol:
        raise GateError(f"delta_ownership_negative_child_target:{omin}:{otol}")
    # Numerical roundoff normalization only; no scientific mass clipping.
    o1=np.where((o1_raw<0.0)&(o1_raw>=-otol),0.0,o1_raw)
    roundoff_adjustment=float(np.sum(o1-o1_raw))
    zero_delta=_fmax(delta) <= max(1e-10,1e-14*max(float(np.max(np.abs(o0))) if len(o0) else 1.0,1.0))
    if zero_delta:
        return p0.copy(),{
            "zero_delta_shortcut":True,
            "stage1_objective":0.0,"stage2_objective":0.0,"stage3_objective":0.0,
            "o1_raw":o1_raw,"o1":o1,
            "roundoff_target_adjustment_kg":roundoff_adjustment,
        }

    eps=max(1e-12,1e-15*max(float(np.max(np.abs(o0))) if len(o0) else 1.0,1.0))
    target=np.zeros_like(p0)
    positive=o0>eps
    scale=np.zeros_like(o0)
    scale[positive]=o1[positive]/o0[positive]
    target[positive[pair_cv]]=p0[positive[pair_cv]]*scale[pair_cv[positive[pair_cv]]]

    qcv=np.bincount(pair_cv,weights=q1,minlength=ncv).astype(np.float64)
    qtarget=np.zeros_like(q1)
    for j in np.flatnonzero(o1>eps):
        mask=pair_cv==j
        if not np.any(mask):
            raise GateError(f"delta_ownership_positive_child_without_support:{int(j)}")
        if o0[j]<=eps:
            if qcv[j]<=eps:
                raise GateError(f"delta_ownership_zero_parent_positive_child_without_raw_target:{int(j)}")
            target[mask]=q1[mask]*(o1[j]/qcv[j])
        if qcv[j]>eps:
            qtarget[mask]=q1[mask]*(o1[j]/qcv[j])
        else:
            qtarget[mask]=target[mask]

    available=np.asarray(capacity,dtype=np.float64)-np.asarray(residual,dtype=np.float64)
    atol=max(1e-8,1e-12*max(float(np.max(np.abs(capacity))) if len(capacity) else 1.0,1.0))
    if float(np.min(available)) < -atol:
        raise GateError(f"delta_ownership_residual_exceeds_capacity:{float(np.min(available))}:{atol}")
    available=np.where((available<0.0)&(available>=-atol),0.0,available)

    x1,o_stage1,m1meta=_child_stage1(pair_cv,pair_cell,target,o1,available)
    t1=max(1e-8,1e-12*max(abs(o_stage1),1.0))
    x2,o_stage2,m2meta=_child_stage2(pair_cv,pair_cell,target,qtarget,o1,available,o_stage1,t1)
    t2=max(1e-8,1e-12*max(abs(o_stage2),1.0))
    x3,o_stage3,m3meta=_child_stage3(pair_cv,pair_cell,target,qtarget,o1,available,o_stage1,t1,o_stage2,t2)
    return x3,{
        "zero_delta_shortcut":False,
        "stage1_objective":o_stage1,"stage2_objective":o_stage2,"stage3_objective":o_stage3,
        "stage1_meta":m1meta,"stage2_meta":m2meta,"stage3_meta":m3meta,
        "o1_raw":o1_raw,"o1":o1,
        "roundoff_target_adjustment_kg":roundoff_adjustment,
    }


def _bounded_exact_sum_projection(y, upper, target):
    y=np.asarray(y,dtype=np.float64).reshape(-1)
    upper=np.asarray(upper,dtype=np.float64).reshape(-1)
    if y.shape!=upper.shape:
        raise GateError(f"cartesian_projection_shape_mismatch:{y.shape}:{upper.shape}")
    if not np.isfinite(y).all() or not np.isfinite(upper).all() or not np.isfinite(float(target)):
        raise GateError("cartesian_projection_nonfinite_input")
    if float(np.min(upper))<0.0:
        raise GateError(f"cartesian_projection_negative_capacity:{float(np.min(upper))}")
    scale=max(abs(float(target)),float(np.sum(upper)),float(np.max(np.abs(y))) if y.size else 1.0,1.0)
    tol=max(1e-10,1e-13*scale)
    if float(target)<-tol or float(target)>float(np.sum(upper))+tol:
        raise GateError(f"cartesian_projection_infeasible_target:{float(target)}:{float(np.sum(upper))}:{tol}")
    t=min(max(float(target),0.0),float(np.sum(upper)))
    if y.size==0:
        if abs(t)>tol:
            raise GateError(f"cartesian_projection_empty_support_nonzero_target:{t}")
        return y.copy(),0.0,0.0
    span=max(float(np.max(np.abs(y))),float(np.max(upper)),abs(t),1.0)
    lo=float(np.min(y-upper))-2.0*span
    hi=float(np.max(y))+2.0*span
    for _ in range(256):
        lam=0.5*(lo+hi)
        x=np.clip(y-lam,0.0,upper)
        if float(np.sum(x))>t:
            lo=lam
        else:
            hi=lam
    lam=0.5*(lo+hi)
    x=np.clip(y-lam,0.0,upper)
    return x,float(lam),float(np.sum(x)-t)

def _cartesian_projection_synthetic_selftest():
    y=np.asarray([-2.0,5.0,4.0],dtype=np.float64)
    cap=np.asarray([6.0,6.0,6.0],dtype=np.float64)
    x,_,res=_bounded_exact_sum_projection(y,cap,9.0)
    assert abs(float(np.sum(x))-9.0)<=1e-10 and abs(res)<=1e-10
    assert float(np.min(x))>=0.0 and float(np.max(x-cap))<=1e-10
    parent=np.asarray([1.0,2.0,3.0],dtype=np.float64)
    xid,_,r0=_bounded_exact_sum_projection(parent,np.asarray([5.0,5.0,5.0]),float(np.sum(parent)))
    assert float(np.max(np.abs(xid-parent)))<=1e-10 and abs(r0)<=1e-10

def ownership_reconciled_mapback(physics,e37a,parent_sat,old_cv_sat,new_cv_sat,
                                 old_cv_mass,new_cv_mass,geometry,pressure,pref,cellpv,target_final):
    cv_id=np.asarray(geometry["cv_id"],dtype=np.int64).reshape(-1)
    flat=np.asarray(geometry["flat_cell"],dtype=np.int64).reshape(-1)
    pv=np.asarray(geometry["pv_m3"],dtype=np.float64).reshape(-1)
    pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64).reshape(-1)

    oldf=np.asarray(old_cv_sat,dtype=np.float64).reshape(-1)
    newf=np.asarray(new_cv_sat,dtype=np.float64).reshape(-1)
    old_sub_sat=oldf[cv_id]; new_sub_sat=newf[cv_id]
    old_sg=np.clip(old_sub_sat-physics.BACKGROUND_SATURATION,0.0,physics.MAX_INCREMENTAL_CO2_SATURATION)
    new_sg=np.clip(new_sub_sat-physics.BACKGROUND_SATURATION,0.0,physics.MAX_INCREMENTAL_CO2_SATURATION)
    rho_old=np.asarray(physics.gas_density_from_state(old_sub_sat,pseg,pref),dtype=np.float64)
    rho_new=np.asarray(physics.gas_density_from_state(new_sub_sat,pseg,pref),dtype=np.float64)
    raw_sub_delta=pv*(rho_new*new_sg-rho_old*old_sg)

    parent_sat=np.asarray(parent_sat,dtype=np.float64)
    ncell=int(parent_sat.size)
    raw_delta=np.bincount(flat,weights=raw_sub_delta,minlength=ncell).astype(np.float64)

    cv_delta=float(np.sum(np.asarray(new_cv_mass,dtype=np.float64))-np.sum(np.asarray(old_cv_mass,dtype=np.float64)))
    sub_delta=float(np.sum(raw_sub_delta))
    transfer_residual=sub_delta-cv_delta
    transfer_tol=max(1e-6,1e-10*max(abs(cv_delta),1.0))
    if abs(transfer_residual)>transfer_tol:
        raise GateError(f"cartesian_projection_raw_E37A_transfer_closure:{transfer_residual}:{transfer_tol}")

    parent_sg=np.clip(parent_sat-physics.BACKGROUND_SATURATION,0.0,physics.MAX_INCREMENTAL_CO2_SATURATION)
    parent_rho=np.asarray(physics.gas_density_from_state(parent_sat,pressure,pref),dtype=np.float64)
    parent_mass=(float(cellpv)*parent_rho*parent_sg).reshape(-1)
    parent_total=float(np.sum(parent_mass))
    raw_trial=parent_mass+raw_delta

    roundoff=max(1e-6,1e-10*max(abs(float(target_final)),abs(parent_total),1.0))
    raw_target_residual=float(np.sum(raw_trial)-float(target_final))
    if abs(raw_target_residual)>roundoff:
        raise GateError(f"cartesian_projection_raw_global_target_mismatch:{raw_target_residual}:{roundoff}")

    smax=np.full(parent_sat.shape,float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION),dtype=np.float64)
    rho_max=np.asarray(physics.gas_density_from_state(smax,pressure,pref),dtype=np.float64)
    capacity=(float(cellpv)*rho_max*physics.MAX_INCREMENTAL_CO2_SATURATION).reshape(-1)

    support=np.unique(flat)
    support_mask=np.zeros(ncell,dtype=bool); support_mask[support]=True
    outside=~support_mask
    required_supported=float(target_final)-float(np.sum(parent_mass[outside]))
    supported_capacity=float(np.sum(capacity[support]))
    feasibility_tol=max(1e-6,1e-10*max(abs(required_supported),supported_capacity,1.0))
    if required_supported < -feasibility_tol or required_supported > supported_capacity+feasibility_tol:
        raise GateError(f"cartesian_projection_existing_support_capacity_infeasible:{required_supported}:{supported_capacity}:{feasibility_tol}")

    x,lam,projection_sum_residual=_bounded_exact_sum_projection(raw_trial[support],capacity[support],required_supported)
    grid=parent_mass.copy(); grid[support]=x

    outside_identity=float(np.max(np.abs(grid[outside]-parent_mass[outside]))) if np.any(outside) else 0.0
    grid_total=float(np.sum(grid))
    ledger=grid_total-float(target_final)
    global_delta_residual=(grid_total-parent_total)-cv_delta
    min_grid=float(np.min(grid))
    max_capacity_excess=float(np.max(grid-capacity))

    if outside_identity>roundoff:
        raise GateError(f"cartesian_projection_outside_support_identity:{outside_identity}:{roundoff}")
    if abs(ledger)>roundoff:
        raise GateError(f"cartesian_projection_grid_ledger:{ledger}:{roundoff}")
    if abs(global_delta_residual)>roundoff:
        raise GateError(f"cartesian_projection_global_component_delta_identity:{global_delta_residual}:{roundoff}")
    if min_grid<-roundoff:
        raise GateError(f"cartesian_projection_negative_grid:{min_grid}:{roundoff}")
    if max_capacity_excess>roundoff:
        raise GateError(f"cartesian_projection_capacity_excess:{max_capacity_excess}:{roundoff}")

    xid,_,id_sum_res=_bounded_exact_sum_projection(parent_mass[support],capacity[support],float(np.sum(parent_mass[support])))
    zero_delta_identity=float(np.max(np.abs(xid-parent_mass[support]))) if support.size else 0.0
    if zero_delta_identity>roundoff or abs(id_sum_res)>roundoff:
        raise GateError(f"cartesian_projection_zero_delta_identity:{zero_delta_identity}:{id_sum_res}:{roundoff}")

    corrected_sg=np.asarray(physics._invert_incremental_sg_from_mass(grid.reshape(parent_sat.shape),pressure,pref,cellpv),dtype=np.float64)
    corrected_sat=physics.BACKGROUND_SATURATION+corrected_sg
    recon=float(physics.stored_co2_mass_kg(corrected_sat,pressure,pref,cellpv))
    invres=recon-grid_total
    if abs(invres)>roundoff:
        raise GateError(f"cartesian_projection_grid_inversion:{invres}:{roundoff}")

    corr=x-raw_trial[support]; corr_abs=np.abs(corr)
    active_tol=max(1e-10,1e-12*max(float(np.max(np.abs(raw_trial[support]))) if support.size else 1.0,1.0))
    audit={
        "supported_cell_count":int(support.size),
        "raw_negative_cell_count":int(np.sum(raw_trial[support]<-roundoff)),
        "raw_overcapacity_cell_count":int(np.sum(raw_trial[support]>capacity[support]+roundoff)),
        "projection_correction_L1_kg":float(np.sum(corr_abs)),
        "projection_correction_L2_kg":float(np.linalg.norm(corr)),
        "projection_correction_Linf_kg":float(np.max(corr_abs)) if corr_abs.size else 0.0,
        "changed_supported_cell_count":int(np.sum(corr_abs>active_tol)),
        "lower_bound_active_cell_count":int(np.sum(x<=active_tol)),
        "upper_bound_active_cell_count":int(np.sum(x>=capacity[support]-active_tol)),
        "projection_lambda_kg":float(lam),
        "projection_sum_residual_kg":float(projection_sum_residual),
        "raw_global_target_residual_kg":raw_target_residual,
        "raw_E37A_transfer_residual_kg":float(transfer_residual),
        "global_component_delta_identity_residual_kg":float(global_delta_residual),
        "outside_support_identity_Linf_kg":outside_identity,
        "zero_delta_identity_Linf_kg":zero_delta_identity,
        "minimum_child_grid_mass_kg":min_grid,
        "maximum_child_capacity_excess_kg":max_capacity_excess,
        "grid_ledger_residual_kg":float(ledger),
        "supported_target_mass_kg":required_supported,
        "supported_capacity_mass_kg":supported_capacity,
        "transport_global_delta_kg":cv_delta,
    }
    return {
        "corrected_saturation":corrected_sat,
        "corrected_mass":grid.reshape(parent_sat.shape),
        "parent_grid_mass_kg":parent_total,
        "cv_delta_mass_kg":cv_delta,
        "subsegment_delta_mass_kg":sub_delta,
        "transfer_residual_kg":float(transfer_residual),
        "mapped_final_mass_kg":grid_total,
        "target_final_mass_kg":float(target_final),
        "ledger_residual_kg":float(ledger),
        "grid_inversion_residual_kg":float(invres),
        "roundoff_mass_kg":float(roundoff),
        "deposited_delta_mass":(grid-parent_mass).reshape(parent_sat.shape),
        "source_local_added_mass_kg":0.0,
        "source_local_corrected_cells":0,
        "ownership_audit":audit,
        "projection_audit":audit,
    }

def _delta_ownership_synthetic_selftest():
    # One bounded parent split with overlapping subsegments, then an exact per-CV delta update.
    cv_id=np.array([0,0,1,1],dtype=np.int64)
    flat=np.array([0,1,1,2],dtype=np.int64)
    pv=np.array([0.75,0.75,0.75,0.75],dtype=np.float64)
    g0=np.array([4.0,4.0,4.0],dtype=np.float64)
    split=_bounded_parent_occupancy(cv_id,flat,pv,g0,1.0,2,3)
    p0=split["p0_pair"]; pc=split["pair_cv"]; cell=split["pair_cell"]
    o0=split["o0_cv"]; residual=split["residual"]
    delta=np.array([0.25,-0.25],dtype=np.float64)
    q1=np.array([2.0,1.0,1.0,2.0],dtype=np.float64)
    capacity=np.array([6.0,6.0,6.0],dtype=np.float64)
    x,meta=_delta_child_assignment(pc,cell,p0,q1,o0,delta,residual,capacity)
    cv=np.bincount(pc,weights=x,minlength=2)
    grid=residual+np.bincount(cell,weights=x,minlength=3)
    synthetic_delta_residual=float(np.max(np.abs((cv-o0)-delta)))
    assert synthetic_delta_residual <= SCIENTIFIC_DELTA_IDENTITY_GATE_KG, synthetic_delta_residual
    synthetic_global_residual=float(abs((np.sum(grid)-np.sum(g0))-np.sum(delta)))
    assert synthetic_global_residual <= SCIENTIFIC_DELTA_IDENTITY_GATE_KG, synthetic_global_residual
    xid,_=_delta_child_assignment(pc,cell,p0,p0,o0,np.zeros_like(delta),residual,capacity)
    gid=residual+np.bincount(cell,weights=xid,minlength=3)
    synthetic_zero_delta_residual=float(np.max(np.abs(gid-g0)))
    assert synthetic_zero_delta_residual <= SCIENTIFIC_DELTA_IDENTITY_GATE_KG, synthetic_zero_delta_residual

def selftest(root:Path):
    r3r2=mod(root,R3R2_RUNNER,R3R2_BLOB,"inta1r4r3_r3r2_selftest")
    r4r2r1=mod(root,R4R2R1_RUNNER,R4R2R1_BLOB,"inta1r4r3_r4r2r1_selftest")
    r4r2=mod(root,R4R2_RUNNER,R4R2_BLOB,"inta1r4r2r1r1_r4r2_selftest")
    r3r1=mod(root,R3R1_RUNNER,R3R1_BLOB,"inta1r4r2r1r1_r3r1_selftest")
    r4r1=mod(root,R4R1_RUNNER,R4R1_BLOB,"inta1r4r2r1r1_r4r1_selftest")
    f2r3=mod(root,F2R3_RUNNER,F2R3_BLOB,"inta1r4r2r1r1_f2r3_selftest")
    r4=mod(root,R4_RUNNER,R4_BLOB,"inta1r4r2r1r1_r4_selftest")
    r3=mod(root,R3_RUNNER,R3_BLOB,"inta1r4r2r1r1_r3_selftest")
    f4exec=mod(root,F4EXEC_RUNNER,F4EXEC_BLOB,"inta1r4r2r1r1_f4exec_selftest")
    original=mod(root,INTA1_RUNNER,INTA1_BLOB,"inta1r4r2r1r1_original_selftest")
    g3r7=mod(root,G3R7_RUNNER,G3R7_BLOB,"inta1r4r2r1r1_g3r7_selftest")
    g3r5=mod(root,G3R5_RUNNER,G3R5_BLOB,"inta1r4r2r1r1_g3r5_selftest")
    g2=mod(root,G2R3_RUNNER,G2R3_BLOB,"inta1r4r2r1r1_g2_selftest")
    mod(root,A8_RUNNER,A8_BLOB,"inta1r4r2r1r1_a8_selftest")
    mod(root,A1_RUNNER,A1_BLOB,"inta1r4r2r1r1_a1_selftest")
    mod(root,B1_RUNNER,B1_BLOB,"inta1r4r2r1r1_b1_selftest")
    mod(root,E11_RUNNER,E11_BLOB,"inta1r4r2r1r1_e11_selftest")
    mod(root,R3R5_RUNNER,R3R5_BLOB,"inta1r4r2r1r1_r3r5_selftest")
    mod(root,R3R4_RUNNER,R3R4_BLOB,"inta1r4r2r1r1_r3r4_selftest")
    mod(root,R2_REPAIR_RUNNER,R2_REPAIR_BLOB,"inta1r4r2r1r1_repair_selftest")
    assert START_DAY==30.0 and TARGET_DAY==45.0
    assert r4r2r1.M=="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R4-R2-R1"
    assert r4r2.M=="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R4-R2"
    assert HIGHS_PRIMAL_FEASIBILITY_TOL==1.0e-9
    assert HIGHS_DUAL_FEASIBILITY_TOL==1.0e-9
    assert SCIENTIFIC_DELTA_IDENTITY_GATE_KG==1.0e-8
    assert r3r1.PASS==R3R1_STATUS
    assert r4r1.M=="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R4-R1"
    assert f2r3.PASS_STATUS.startswith("AV4F2R3_") if hasattr(f2r3,"PASS_STATUS") else True
    _delta_ownership_synthetic_selftest()
    _cartesian_projection_synthetic_selftest()
    assert r4.M=="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R4"
    assert r3.PASS=="POSTV16AV4PIVOTGPUHYBINTA1R3_PARENT_OWNERSHIP_MAPBACK_RECONCILIATION_DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"
    assert r3r1.PASS==R3R1_STATUS
    assert hasattr(f4exec,"execute_frozen_assignment")
    assert MAX_FLOW_EPOCH_DAYS==5.0
    assert SCHEDULED_REFRESH_DAYS==(30.0,35.0,40.0,45.0)
    assert NEGATIVE_MAPBACK_RETRY_FACTOR==0.5
    assert MAX_NEGATIVE_MAPBACK_RETRIES==12
    assert "_parent_ownership_lp" not in globals()
    _delta_ownership_synthetic_selftest()
    assert original.M=="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1"
    assert g3r5.PRODUCTION_MAX_FLOW_EPOCH_DAYS is None
    assert g3r5.decide_shadow_action(35.0,30.0).action=="FULL_FLOW_REFRESH"
    assert g3r5.decide_shadow_action(40.0,35.0).action=="FULL_FLOW_REFRESH"
    assert g3r5.decide_shadow_action(45.0,40.0).action=="FULL_FLOW_REFRESH"
    assert g2.DAY30_RESTART_SHA=="093fa9570b07d91d6865c8464104cd6f72c271b2d638b93dc167c74497827035"
    assert g3r7.NEXT_MILESTONE=="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1"
    print("POSTV16 GPU-HYB-INT-A1-R4-R3 Cartesian global-delta projection / whole-system self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve()
    drive=drive.resolve()
    out=drive/OUT_REL
    blocked=drive/BLOCK_REL
    gates=[]
    stage="preflight"
    parent_sha_before=None

    def gate(name,cond,detail=None):
        ok=bool(cond)
        gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"),flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("="*202)
        print("INT-A1-R4-R3 — CARTESIAN GLOBAL-DELTA PROJECTION VALIDATION + CONTROLLED DAY30 -> DAY45 RUN")
        print("PRE-VALIDATION: R1 DT REPLAY. CERTIFIED PARENT: SUPPORTED CARTESIAN EXACT-SUM PROJECTION. POST-PASS: SAME FALLBACK.")
        print("NO CLIPPING, MASS DISCARD, TOLERANCE RELAXATION, SUPPORT EXPANSION, OR EXTRA FLOW REFRESH.")
        print("="*202)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_R3_R2_design_freeze_PASS_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="source_authority"
        r3r2=mod(root,R3R2_RUNNER,R3R2_BLOB,"inta1r4r3_r3r2")
        r4r2r1=mod(root,R4R2R1_RUNNER,R4R2R1_BLOB,"inta1r4r3_r4r2r1")
        r4r2=mod(root,R4R2_RUNNER,R4R2_BLOB,"inta1r4r2r1r1_r4r2")
        r3r1=mod(root,R3R1_RUNNER,R3R1_BLOB,"inta1r4r2r1r1_r3r1")
        r4r1=mod(root,R4R1_RUNNER,R4R1_BLOB,"inta1r4r2r1r1_r4r1")
        f2r3=mod(root,F2R3_RUNNER,F2R3_BLOB,"inta1r4r2r1r1_f2r3")
        r4=mod(root,R4_RUNNER,R4_BLOB,"inta1r4r2r1r1_r4")
        r3=mod(root,R3_RUNNER,R3_BLOB,"inta1r4r2r1r1_r3")
        f4exec=mod(root,F4EXEC_RUNNER,F4EXEC_BLOB,"inta1r4r2r1r1_f4exec")
        original=mod(root,INTA1_RUNNER,INTA1_BLOB,"inta1r4r2r1r1_original")
        g3r7=mod(root,G3R7_RUNNER,G3R7_BLOB,"inta1r4r2r1r1_g3r7")
        g3r5=mod(root,G3R5_RUNNER,G3R5_BLOB,"inta1r4r2r1r1_g3r5")
        g2=mod(root,G2R3_RUNNER,G2R3_BLOB,"inta1r4r2r1r1_g2")
        a8=mod(root,A8_RUNNER,A8_BLOB,"inta1r4r2r1r1_a8")
        a1=mod(root,A1_RUNNER,A1_BLOB,"inta1r4r2r1r1_a1")
        b1=mod(root,B1_RUNNER,B1_BLOB,"inta1r4r2r1r1_b1")
        e11=mod(root,E11_RUNNER,E11_BLOB,"inta1r4r2r1r1_e11")
        r3r5=mod(root,R3R5_RUNNER,R3R5_BLOB,"inta1r4r2r1r1_r3r5")
        r3r4=mod(root,R3R4_RUNNER,R3R4_BLOB,"inta1r4r2r1r1_r3r4")
        repair=mod(root,R2_REPAIR_RUNNER,R2_REPAIR_BLOB,"inta1r4r2r1r1_repair")

        stage="G3_R7_authority"
        s7p=drive/G3R7_REL/G3R7_SUM
        p7p=drive/G3R7_REL/G3R7_PROTOCOL
        d7p=drive/G3R7_REL/G3R7_DECISION
        for label,p in [("G3R7_summary",s7p),("G3R7_protocol",p7p),("G3R7_decision",d7p)]:
            gate(label+"_present",p.is_file(),str(p))
        s7=js(s7p);p7=js(p7p);d7=js(d7p)
        gate("G3R7_status_exact",s7.get("status")==G3R7_STATUS,s7.get("status"))
        gate("G3_controller_phase_closed",s7.get("G3_controller_development_phase_closed") is True)
        gate("INT_A1_authorized",s7.get("INT_A1_authorized") is True)
        gate("INT_A1_window_exact",s7.get("INT_A1_window_days")==[30.0,45.0],s7.get("INT_A1_window_days"))
        gate("INT_A1_boundaries_exact",s7.get("INT_A1_refresh_boundary_days")==[35.0,40.0,45.0],s7.get("INT_A1_refresh_boundary_days"))
        gate("INT_A1_visual_days_exact",s7.get("INT_A1_visualization_checkpoint_days")==[30.0,35.0,40.0,45.0])
        gate("INT_A1_whole_system_transport_required",s7.get("INT_A1_requires_Hybrid10_plus_exact_E37A_conservative_transport") is True)
        gate("INT_A1_exact_flow_refresh_required",s7.get("INT_A1_requires_exact_FV_Darcy_Pollock_TOF_refresh") is True)
        gate("INT_A1_stepwise_mass_conservation_required",s7.get("INT_A1_requires_stepwise_component_mass_conservation") is True)
        gate("INT_A1_noncanonical",s7.get("INT_A1_trajectory_class")=="CONTROLLED_NONCANONICAL_WHOLE_SYSTEM_SHADOW_TRAJECTORY")
        gate("INT_A1_no_production_activation",s7.get("INT_A1_production_activation_authorized") is False)
        gate("G3R7_protocol_boundary_policy_exact",
             p7.get("time_window",{}).get("boundary_landing_policy")=="CLIP_ACCEPTED_TIMESTEP_TO_CONTROLLER_BOUNDARY_BEFORE_REFRESH")
        gate("G3R7_decision_INT_A1_authorized",d7.get("INT_A1_controlled_integrated_Day30_to45_run_authorized") is True)

        stage="INT_A1_immutable_BLOCK_authority"
        block_path=drive/INTA1_BLOCK_REL/INTA1_BLOCK_REPORT
        gate("INT_A1_BLOCK_report_present",block_path.is_file(),str(block_path))
        prior_block=js(block_path)
        gate("INT_A1_BLOCK_status_exact",prior_block.get("status")==INTA1_BLOCK_STATUS,prior_block.get("status"))
        gate("INT_A1_BLOCK_failed_stage_exact",prior_block.get("failed_stage")==INTA1_EXPECTED_FAILED_STAGE,prior_block.get("failed_stage"))
        gate("INT_A1_BLOCK_exception_exact",prior_block.get("exception")==INTA1_EXPECTED_EXCEPTION,prior_block.get("exception"))
        gate("INT_A1_BLOCK_Day30_parent_SHA_exact",
             prior_block.get("Day30_parent_sha256_before")=="093fa9570b07d91d6865c8464104cd6f72c271b2d638b93dc167c74497827035",
             prior_block.get("Day30_parent_sha256_before"))
        gate("INT_A1_BLOCK_no_visualization_authority",prior_block.get("INT_VIS_A1_integrated_3D_visualization_authorized") is False)
        gate("INT_A1_BLOCK_no_longer_horizon_authority",prior_block.get("longer_horizon_validation_authorized") is False)
        gate("INT_A1_BLOCK_no_production_authority",prior_block.get("integrated_GPU_runtime_production_authorized") is False)
        gate("INT_A1_BLOCK_P4_closed",prior_block.get("P4_authorized") is False)

        stage="R4_immutable_BLOCK_authority"
        r4bp=drive/R4_BLOCK_REL/R4_BLOCK_REPORT
        gate("R4_BLOCK_report_present",r4bp.is_file(),str(r4bp))
        r4b=js(r4bp)
        gate("R4_BLOCK_status_exact",r4b.get("status")==R4_BLOCK_STATUS,r4b.get("status"))
        gate("R4_BLOCK_failed_stage_exact",r4b.get("failed_stage")==R4_EXPECTED_FAILED_STAGE,r4b.get("failed_stage"))
        gate("R4_BLOCK_exception_exact",r4b.get("exception")==R4_EXPECTED_EXCEPTION,r4b.get("exception"))
        gate("R4_BLOCK_local_validation_not_passed",r4b.get("R3_local_validation_passed") is False)
        gate("R4_BLOCK_ownership_not_executed",int(r4b.get("ownership_reconciliation_count",0))==0)
        gate("R4_BLOCK_no_clipping",r4b.get("cellwise_clipping_performed") is False)
        gate("R4_BLOCK_no_mass_discard",r4b.get("mass_discard_performed") is False)
        gate("R4_BLOCK_no_tolerance_relaxation",r4b.get("scientific_tolerance_relaxed") is False)
        gate("R4_BLOCK_no_support_expansion",r4b.get("support_expansion_performed") is False)

        stage="R4_R1_immutable_BLOCK_authority"
        r4r1bp=drive/R4R1_BLOCK_REL/R4R1_BLOCK_REPORT
        gate("R4_R1_BLOCK_report_present",r4r1bp.is_file(),str(r4r1bp))
        r4r1b=js(r4r1bp)
        gate("R4_R1_BLOCK_status_exact",r4r1b.get("status")==R4R1_BLOCK_STATUS,r4r1b.get("status"))
        gate("R4_R1_BLOCK_failed_stage_exact",r4r1b.get("failed_stage")=="controlled_integrated_rollout",r4r1b.get("failed_stage"))
        gate("R4_R1_STAGEA_infeasibility_bound",
             str(r4r1b.get("exception","")).startswith(R4R1_EXCEPTION_PREFIX),r4r1b.get("exception"))
        gate("R4_R1_no_clipping",r4r1b.get("cell_mass_clipping_performed") is False)
        gate("R4_R1_no_mass_discard",r4r1b.get("mass_discard_performed") is False)
        gate("R4_R1_no_tolerance_relaxation",r4r1b.get("scientific_tolerance_relaxed") is False)

        stage="R4_R2_R1_R1_formal_BLOCK_authority"
        r4r3bp=drive/R4R2R1R1_FORMAL_BLOCK_REL/R4R2R1R1_FORMAL_BLOCK_REPORT
        gate("R4_R2_R1_R1_BLOCK_report_present",r4r3bp.is_file(),str(r4r3bp))
        r4r3b=js(r4r3bp)
        gate("R4_R2_R1_R1_BLOCK_status_exact",
             r4r3b.get("status")==R4R2R1R1_FORMAL_BLOCK_STATUS,r4r3b.get("status"))
        gate("R4_R2_R1_R1_BLOCK_failed_stage_exact",
             r4r3b.get("failed_stage")=="controlled_integrated_rollout",r4r3b.get("failed_stage"))
        gate("R4_R2_R1_R1_negative_child_target_exact",
             r4r3b.get("exception")==R4R2R1R1_FORMAL_BLOCK_EXCEPTION,r4r3b.get("exception"))
        gate("R4_R2_R1_R1_no_clipping",r4r3b.get("cell_mass_clipping_performed") is False)
        gate("R4_R2_R1_R1_no_mass_discard",r4r3b.get("mass_discard_performed") is False)
        gate("R4_R2_R1_R1_no_tolerance_relaxation",r4r3b.get("scientific_tolerance_relaxed") is False)

        stage="R3_R2_design_freeze_authority"
        r32s=drive/R3R2_REL/R3R2_SUM
        r32p=drive/R3R2_REL/R3R2_PROTOCOL
        r32h=drive/R3R2_REL/R3R2_HANDOFF
        r32d=drive/R3R2_REL/R3R2_DECISION
        for label,p in [("R3_R2_summary",r32s),("R3_R2_protocol",r32p),
                        ("R3_R2_handoff",r32h),("R3_R2_decision",r32d)]:
            gate(label+"_present",p.is_file(),str(p))
        s32=js(r32s);p32=js(r32p);h32=js(r32h);d32=js(r32d)
        gate("R3_R2_status_exact",s32.get("status")==R3R2_STATUS,s32.get("status"))
        gate("R3_R2_global_delta_authority",
             s32.get("E37A_global_component_delta_is_mapback_authority") is True)
        gate("R3_R2_per_CV_exclusive_delta_superseded",
             s32.get("per_CV_exclusive_delta_ownership_constraint_superseded") is True)
        gate("R3_R2_projection_space_exact",
             s32.get("projection_space")=="CARTESIAN_CELL_MASS_ON_EXISTING_E37A_SUPPORT")
        gate("R3_R2_projection_objective_exact",
             s32.get("projection_objective")=="MINIMUM_L2_CORRECTION_TO_RAW_E37A_TRIAL")
        gate("R3_R2_existing_support_only",s32.get("existing_E37A_support_only") is True)
        gate("R3_R2_transport_state_immutable",
             s32.get("accepted_CV_transport_state_mutated_by_projection") is False)
        gate("R3_R2_no_support_expansion",s32.get("support_expansion_authorized") is False)
        gate("R3_R2_R4_R3_authorized",s32.get("INT_A1_R4_R3_execution_authorized") is True)
        gate("R3_R2_local_validation_required",
             s32.get("INT_A1_R4_R3_local_validation_required_before_trajectory") is True)
        gate("R3_R2_protocol_operator_exact",
             p32.get("corrected_mapback_operator",{}).get("name")
             =="SUPPORTED_CARTESIAN_BOUNDED_GLOBAL_DELTA_EUCLIDEAN_PROJECTION")
        gate("R3_R2_handoff_R4_R3",h32.get("R4_R3_authorized") is True)
        gate("R3_R2_decision_next_exact",
             d32.get("next_milestone",{}).get("name")
             =="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R4-R3")

        stage="R3_R1_corrected_design_authority"
        r3r1s=drive/R3R1_REL/R3R1_SUM
        r3r1p=drive/R3R1_REL/R3R1_PROTOCOL
        r3r1h=drive/R3R1_REL/R3R1_HANDOFF
        r3r1d=drive/R3R1_REL/R3R1_DECISION
        for label,p in [("R3_R1_summary",r3r1s),("R3_R1_protocol",r3r1p),
                        ("R3_R1_handoff",r3r1h),("R3_R1_decision",r3r1d)]:
            gate(label+"_present",p.is_file(),str(p))
        s31=js(r3r1s);p31=js(r3r1p);h31=js(r3r1h);d31=js(r3r1d)
        gate("R3_R1_status_exact",s31.get("status")==R3R1_STATUS,s31.get("status"))
        gate("R3_R1_absolute_CV_ownership_superseded",s31.get("R3_absolute_CV_ownership_constraint_superseded") is True)
        gate("R3_R1_delta_is_authority",s31.get("transport_authority_preserved_as_exact_per_CV_delta") is True)
        gate("R3_R1_F2R3_split_exact",s31.get("bounded_parent_occupancy_split_source")=="F2_R3")
        gate("R3_R1_existing_support_only",s31.get("existing_E37A_support_only") is True)
        gate("R3_R1_no_support_expansion",s31.get("support_expansion_authorized") is False)
        gate("R3_R1_R4_R2_authorized",s31.get("INT_A1_R4_R2_execution_authorized") is True)
        gate("R3_R1_local_validation_required",s31.get("INT_A1_R4_R2_local_validation_required_before_trajectory") is True)
        gate("R3_R1_protocol_delta_exact",
             p31.get("stage_B_exact_transport_delta_reconciliation",{}).get("transport_increment")
             =="DeltaM_j = M1T_j - M0T_j")
        gate("R3_R1_protocol_parent_split_formula_exact",
             p31.get("stage_A_bounded_parent_occupancy_split",{}).get("P0_q")
             =="G0_c * PV_q / D_c for subsegment q in cell c")
        gate("R3_R1_handoff_R4_R2",h31.get("R4_R2_authorized") is True)
        gate("R3_R1_decision_next_exact",
             d31.get("next_milestone",{}).get("name")=="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R4-R2")

        stage="R3_design_freeze_authority"
        r3s=drive/R3_REL/R3_SUM
        r3p=drive/R3_REL/R3_PROTOCOL
        r3h=drive/R3_REL/R3_HANDOFF
        r3d=drive/R3_REL/R3_DECISION
        for label,p in [("R3_summary",r3s),("R3_protocol",r3p),("R3_handoff",r3h),("R3_decision",r3d)]:
            gate(label+"_present",p.is_file(),str(p))
        r3summary=js(r3s); r3protocol=js(r3p); r3handoff=js(r3h); r3decision=js(r3d)
        gate("R3_status_exact",r3summary.get("status")==R3_STATUS,r3summary.get("status"))
        gate("R3_repair_family_exact",
             r3summary.get("repair_family")=="BOUNDED_PARENT_OWNERSHIP_PRESERVING_MIXED_CV_TO_CARTESIAN_RECONCILIATION")
        gate("R3_existing_support_only",r3summary.get("existing_E37A_support_only") is True)
        gate("R3_CV_mass_preservation",r3summary.get("per_CV_child_mass_preserved_exactly") is True)
        gate("R3_residual_sidecar_preservation",r3summary.get("parent_residual_sidecar_preserved") is True)
        gate("R3_zero_delta_identity_required",r3summary.get("zero_delta_identity_required") is True)
        gate("R3_R4_authorized",r3summary.get("INT_A1_R4_execution_authorized") is True)
        gate("R3_local_validation_required",r3summary.get("INT_A1_R4_local_validation_required_before_trajectory") is True)
        gate("R3_local_validation_parent_frozen",
             r3protocol.get("R4_execution_protocol",{}).get("phase_1_local_validation",{}).get("parent")
             =="the certified failed parent reproduced at Day 30.003412917596155")
        gate("R3_no_support_expansion",r3decision.get("support_expansion_authorized") is False)

        stage="Day30_start_authority"
        bridge_summary=drive/g2.R3A0_REL/g2.R3A0_SUM
        parent_path=drive/g2.R3A0_REL/g2.R3A0_RESTART
        gate("Day30_bridge_summary_present",bridge_summary.is_file(),str(bridge_summary))
        gate("Day30_restart_present",parent_path.is_file(),str(parent_path))
        bs=js(bridge_summary)
        gate("Day30_bridge_status_exact",bs.get("status")==g2.R3A0_STATUS,bs.get("status"))
        parent_sha_before=sha(parent_path)
        gate("Day30_restart_SHA_exact",parent_sha_before==g2.DAY30_RESTART_SHA,parent_sha_before)
        current=load_npz(parent_path)
        gate("Day30_start_time_exact",scalar(current["physical_time_days"])==30.0,scalar(current["physical_time_days"]))

        initial_injected=scalar(current["cumulative_injected_co2_mass_kg"])
        initial_produced=scalar(current["cumulative_produced_co2_mass_kg"])
        initial_stored=scalar(current["stored_co2_mass_current_kg"])

        stage="physics_authority"
        roles={}
        for role in ["R3R2R1","E36","E37A","R2_PHYSICS","SG2","SG3","SG4","SG5","SG6","SG7A","SG7D"]:
            fn,bl=r3r4.SOURCE_BLOBS[role]
            roles[role]=mod(root,fn,bl,f"inta1_{role.lower()}")
        r3r2r1=roles["R3R2R1"];e36=roles["E36"];e37a=roles["E37A"];physics=roles["R2_PHYSICS"]
        sg2=roles["SG2"];sg3=roles["SG3"];sg4=roles["SG4"];sg5=roles["SG5"];sg6=roles["SG6"]
        sg7a=roles["SG7A"];sg7d=roles["SG7D"]

        pfn,pblob=r3r4.SOURCE_BLOBS["PERM"]
        perm_path=root/pfn
        gate("permeability_blob_exact",blob(root,perm_path)==pblob,blob(root,perm_path))
        permeability_md=np.loadtxt(perm_path,skiprows=1,dtype=np.float64).reshape(EXPECTED_GRID,order="C")
        cell_pv=0.20*(20.0*FT_TO_M)*(20.0*FT_TO_M)*(4.0*FT_TO_M)

        stage="Hybrid_authority"
        for rel,entry,label in [
            (e11.E8R1_REL,e11.E8R1["contract"],"E8R1"),
            (e11.E5_REL,e11.E5_MANIFEST,"E5"),
            (e11.E3_REL,e11.E3_PROTOCOL,"E3"),
            (e11.E6A_REL,e11.E6A_CHECKPOINT,"E6A"),
        ]:
            fn,expected=entry
            p=drive/rel/fn
            gate(label+"_present",p.is_file(),str(p))
            gate(label+"_SHA",e11.sha(p)==expected,e11.sha(p))

        screen=e11.read_json(drive/e11.E8R1_REL/e11.E8R1["contract"][0])["learned_proposal_execution_screen"]
        e5=e11.read_json(drive/e11.E5_REL/e11.E5_MANIFEST[0])
        e3=e11.read_json(drive/e11.E3_REL/e11.E3_PROTOCOL[0])
        params=e11.c14_production_params(root/e11.C14_SOURCE[0])
        gate("C14_inside_E3",e11.parameters_inside_e3(params,e3))
        adapter=e11.import_exact(root/e11.E9_ADAPTER[0],e11.E9_ADAPTER[1],"inta1_adapter")
        teacher=e11.import_exact(root/e11.R2_ADAPTER[0],e11.R2_ADAPTER[1],"inta1_teacher")
        e9r1=e11.import_exact(root/e11.E9R1_RUNNER[0],e11.E9R1_RUNNER[1],"inta1_e9r1")
        shock=teacher.welge_shock(adapter.teacher_params(params),scan_nodes=4097)
        speed=float(shock["characteristic_speed"])
        swstar=float(shock["Sw_star"])
        tf=e9r1.prepare_tf(e5)
        gate("TensorFlow_2_20_exact",tf.__version__=="2.20.0",tf.__version__)
        gpu_devices=tf.config.list_physical_devices("GPU")
        cpu_devices=tf.config.list_physical_devices("CPU")
        gate("TensorFlow_compute_device_available",len(gpu_devices)+len(cpu_devices)>=1,
             {"GPU":[str(x) for x in gpu_devices],"CPU":[str(x) for x in cpu_devices]})
        model=e9r1.build_inference_model(tf,10,"INTA1_Hybrid10")
        gate("Hybrid10_parameter_count_exact",model.count_params()==52545,model.count_params())
        model.load_weights(str(drive/e11.E6A_REL/e11.E6A_CHECKPOINT[0]))

        def rebuild_db(epoch:dict[str,Any]):
            vx,vy,vz=sg5.construct_face_pore_velocities(epoch["qx"],epoch["qy"],epoch["qz"])
            _faces,seeds=sg5.build_seeds(epoch["qx"],epoch["qy"],epoch["qz"])
            streamlines=sg5.trace_streamlines(seeds,vx,vy,vz)
            converted=r3r4.convert_sg5_to_sg6_streamlines(streamlines)
            db=sg6.build_transport_database(converted)
            if int(np.asarray(db["xyz_m"]).shape[0])!=int(epoch["nstream"]):
                raise GateError("db_stream_count")
            if int(np.asarray(db["xi"]).shape[0])!=int(epoch["nfaces"]):
                raise GateError("db_face_count")
            w=np.asarray(db["weights_m3_s"],float)*DAY_TO_S
            if np.max(np.abs(w-np.asarray(epoch["weights_m3_day"],float)))>1e-8:
                raise GateError("db_weights")
            if np.max(np.abs(np.asarray(db["xi"],float)-np.asarray(epoch["xi_faces"],float)))>1e-14:
                raise GateError("db_xi")
            return db

        profile_cache={}
        def infer_profiles(day:float,db:dict[str,np.ndarray],epoch_tag:str):
            key=(epoch_tag,round(float(day),12))
            if key in profile_cache:
                return profile_cache[key]
            tau=np.asarray(db["tau_s"],float)
            tau_end=np.asarray(db["tau_end_s"],float)
            xi=np.asarray(db["xi"],float)
            terminal_days=tau_end/DAY_TO_S
            xstar=(float(day)/terminal_days)*speed
            clocks=np.asarray([e11.classify_clock(float(x)) for x in xstar],dtype="U32")
            idx=np.flatnonzero(clocks=="LEARNED_WINDOW")
            profiles={};reject={}
            if idx.size:
                cond=[];states=[]
                for i in idx:
                    st=adapter.physical_time_state(
                        elapsed_time=day,tau_end=float(terminal_days[i]),
                        characteristic_speed=speed,Sw_star=swstar)
                    states.append(st)
                    cond.append(adapter.conditioning_vector("HYBRID10",params,st))
                pred=e9r1.infer(tf,model,xi.astype(np.float32),np.asarray(cond,dtype=np.float32),batch=256)
                for local,i in enumerate(idx):
                    ok,sm=e11.screen_fan_prediction(
                        pred[local],params,states[local],xi,tau[i]/DAY_TO_S,teacher,adapter,screen)
                    if ok:
                        profiles[int(i)]=adapter.project_fan_to_pollock_nodes(
                            tau_nodes=tau[i]/DAY_TO_S,state=states[local],fan_xi=xi,
                            fan_sw=pred[local],swc=float(params["swc"])).astype(np.float64)
                    else:
                        for reason in sm["failures"]:
                            reject[reason]=reject.get(reason,0)+1
            result=(profiles,clocks,reject)
            profile_cache[key]=result
            return result

        refresh_rows=[]
        step_rows=[]
        capacity_rows=[]
        controller_rows=[]
        mapback_retry_rows=[]
        ownership_rows=[]
        route_rows=[]
        reference_rows=[]
        checkpoint_rows=[]
        checkpoint_payloads={}
        pre_boundary_states={}
        capacity_margins=[]

        epoch=None;db=None;epoch_start_time=None;epoch_serial=0
        refresh_count=0;cadence_refresh_count=0;capacity_refresh_count=0
        total_hybrid_routes=0;total_exact_fallback_routes=0
        negative_mapback_retry_total=0
        negative_mapback_retry_step_count=0
        maximum_negative_mapback_retries_on_one_step=0
        minimum_rejected_trial_cell_mass_kg=None
        ownership_reconciliation_count=0
        local_validation_passed=False
        local_validation_parent_day=None
        prevalidation_accepted_retry_step_count=0
        unscheduled_refresh=False

        def make_visual_payload(day:float,trigger:str):
            p_ref=scalar(current["co2_density_reference_pressure_pa"])
            sat=np.asarray(current["transport_saturation"],float)
            pressure=np.asarray(epoch["pressure_psi"],float)
            cell_mass=r3r4.parent_cellwise_component_mass(physics,sat,pressure,p_ref,cell_pv)
            return {
                "physical_time_days":np.asarray(day,dtype=np.float64),
                "accepted_step_index":np.asarray(int_scalar(current["accepted_step_index"]),dtype=np.int64),
                "controller_trigger_ascii":np.frombuffer(trigger.encode("ascii"),dtype=np.uint8),
                "flow_epoch_origin_day":np.asarray(epoch_start_time,dtype=np.float64),
                "flow_epoch_age_days":np.asarray(0.0,dtype=np.float64),
                "transport_saturation":sat,
                "cartesian_component_mass_kg":np.asarray(cell_mass,float),
                "pressure_psi":pressure,
                "qx":np.asarray(epoch["qx"],float),
                "qy":np.asarray(epoch["qy"],float),
                "qz":np.asarray(epoch["qz"],float),
                "streamline_xyz_m":np.asarray(db["xyz_m"],float),
                "streamline_tof_s":np.asarray(db["tau_s"],float),
                "streamline_tau_end_s":np.asarray(db["tau_end_s"],float),
                "streamline_weights_m3_s":np.asarray(db["weights_m3_s"],float),
                "streamline_xi":np.asarray(db["xi"],float),
                "producer_labels":np.asarray(epoch["labels"]),
                "stored_co2_mass_current_kg":np.asarray(scalar(current["stored_co2_mass_current_kg"]),dtype=np.float64),
                "cumulative_injected_co2_mass_kg":np.asarray(scalar(current["cumulative_injected_co2_mass_kg"]),dtype=np.float64),
                "cumulative_produced_co2_mass_kg":np.asarray(scalar(current["cumulative_produced_co2_mass_kg"]),dtype=np.float64),
                "producer_co2_gas_cut":np.asarray(scalar(current["current_producer_co2_gas_cut"]),dtype=np.float64),
                "flow_local_relative_residual":np.asarray(float(epoch["flow_local_residual"]),dtype=np.float64),
                "flow_global_relative_residual":np.asarray(float(epoch["flow_global_residual"]),dtype=np.float64),
                "capture_fraction":np.asarray(float(epoch["capture_fraction"]),dtype=np.float64),
            }

        def do_refresh(trigger:str,scheduled:bool):
            nonlocal current,epoch,db,epoch_start_time,epoch_serial
            nonlocal refresh_count,cadence_refresh_count,capacity_refresh_count,unscheduled_refresh
            before_time=scalar(current["physical_time_days"])
            before_step=int_scalar(current["accepted_step_index"])
            before_inj=scalar(current["cumulative_injected_co2_mass_kg"])
            before_prod=scalar(current["cumulative_produced_co2_mass_kg"])
            before_stored=scalar(current["stored_co2_mass_current_kg"])

            if trigger=="RESTART_OR_INITIALIZATION":
                decision=g3r5.decide_shadow_action(before_time,before_time,hard_triggers=("RESTART_OR_INITIALIZATION",))
            elif trigger=="CAPACITY_PREFLIGHT_REJECTION":
                decision=g3r5.decide_shadow_action(before_time,epoch_start_time,hard_triggers=("CAPACITY_PREFLIGHT_REJECTION",))
            else:
                decision=g3r5.decide_shadow_action(before_time,epoch_start_time)

            if decision.action!="FULL_FLOW_REFRESH":
                raise GateError(f"controller_did_not_authorize_refresh:{trigger}:{before_time}:{decision.action}")

            refreshed,new_epoch,_rows=r3r5.build_flow_epoch(
                current=current,r3r4r1=r3r4,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
                sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
                permeability_md=permeability_md,cell_pore_volume_m3=cell_pv)

            if scalar(refreshed["physical_time_days"])!=before_time:
                raise GateError("refresh_advanced_time")
            if int_scalar(refreshed["accepted_step_index"])!=before_step:
                raise GateError("refresh_advanced_step")
            if scalar(refreshed["cumulative_injected_co2_mass_kg"])!=before_inj:
                raise GateError("refresh_changed_injection")
            if scalar(refreshed["cumulative_produced_co2_mass_kg"])!=before_prod:
                raise GateError("refresh_changed_production")
            mtol=max(1e-6,1e-10*max(abs(before_stored),1.0))
            if abs(scalar(refreshed["stored_co2_mass_current_kg"])-before_stored)>mtol:
                raise GateError("refresh_changed_stored")

            current=refreshed
            epoch=new_epoch
            db=rebuild_db(new_epoch)
            epoch_start_time=before_time
            epoch_serial+=1
            refresh_count+=1
            if trigger=="CADENCE":
                cadence_refresh_count+=1
            if trigger=="CAPACITY_PREFLIGHT_REJECTION":
                capacity_refresh_count+=1
                unscheduled_refresh=True

            refresh_rows.append({
                "refresh_index":refresh_count,
                "trigger":trigger,
                "scheduled":scheduled,
                "physical_time_days":before_time,
                "accepted_step_index":before_step,
                "controller_action":decision.action,
                "controller_reason":decision.reason,
                "fixed_point_iterations":int(new_epoch["fixed_point_iterations"]),
                "CFL_dt_days":float(new_epoch["cfl_dt_days"]),
                "streamline_count":int(new_epoch["nstream"]),
                "capture_fraction":float(new_epoch["capture_fraction"]),
                "flow_local_relative_residual":float(new_epoch["flow_local_residual"]),
                "flow_global_relative_residual":float(new_epoch["flow_global_residual"]),
                "pressure_rel_L2_vs_pre_refresh":float(new_epoch["refresh_pressure_rel_L2_vs_parent"]),
                "saturation_Linf_vs_pre_refresh":float(new_epoch["refresh_saturation_Linf_vs_parent"]),
                "refresh_global_mass_error_kg":float(new_epoch["refresh_global_mass_error_kg"]),
            })
            controller_rows.append({
                "physical_time_days":before_time,
                "flow_epoch_origin_before_event":before_time if trigger=="RESTART_OR_INITIALIZATION" else float(decision.flow_epoch_age_days and (before_time-decision.flow_epoch_age_days)),
                "flow_epoch_age_days":float(decision.flow_epoch_age_days),
                "trigger":trigger,
                "action":decision.action,
                "reason":decision.reason,
                "scheduled":scheduled,
            })

            if before_time in VIS_DAYS:
                checkpoint_payloads[before_time]=make_visual_payload(before_time,trigger)

        stage="controlled_integrated_rollout"
        do_refresh("RESTART_OR_INITIALIZATION",scheduled=True)

        while scalar(current["physical_time_days"])<TARGET_DAY-1e-13:
            now=scalar(current["physical_time_days"])
            if epoch is None or db is None or epoch_start_time is None:
                raise GateError("missing_epoch")

            due=epoch_start_time+MAX_FLOW_EPOCH_DAYS
            if now>=due-1e-13:
                gate(f"scheduled_boundary_exact_{now:.12f}",any(abs(now-d)<=1e-10 for d in (35.0,40.0)))
                do_refresh("CADENCE",scheduled=True)
                now=scalar(current["physical_time_days"])
                due=epoch_start_time+MAX_FLOW_EPOCH_DAYS

            decision=g3r5.decide_shadow_action(now,epoch_start_time)
            if decision.action!="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT":
                raise GateError(f"unexpected_nonreuse_between_boundaries:{now}:{epoch_start_time}:{decision.action}")

            intended_target=min(TARGET_DAY,due,now+float(epoch["cfl_dt_days"]))
            nominal_candidate_dt=float(intended_target-now)
            if not np.isfinite(nominal_candidate_dt) or nominal_candidate_dt<=0:
                raise GateError(f"nonpositive_nominal_candidate_dt:{nominal_candidate_dt}")

            candidate_dt=float(nominal_candidate_dt)
            negative_retry_count=0

            while True:
                parent_time=scalar(current["physical_time_days"])
                parent_step=int_scalar(current["accepted_step_index"])
                parent_sat=np.asarray(current["transport_saturation"],float)
                pressure=np.asarray(epoch["pressure_psi"],float)
                p_ref=scalar(current["co2_density_reference_pressure_pa"])
                parent_stored=scalar(current["stored_co2_mass_current_kg"])

                recomputed=float(physics.stored_co2_mass_kg(parent_sat,pressure,p_ref,cell_pv))
                ptol=max(1e-6,1e-10*max(abs(parent_stored),1.0))
                if abs(recomputed-parent_stored)>ptol:
                    raise GateError(f"parent_mass_pressure_mismatch:{recomputed-parent_stored}")

                old_sat,old_mass,sample=e37a.sample_grid_inventory_to_control_volumes(
                    physics,parent_sat,pressure,p_ref,epoch["geometry"],epoch["nstream"],epoch["ncv"])
                stol=max(1e-6,1e-10*max(abs(float(np.sum(old_mass))),1.0))
                if abs(float(sample))>stol:
                    raise GateError(f"sampling_closure:{sample}")

                exact_fallback=e37a.advance_component_mass_control_volumes(
                    physics,sg7a,old_sat,old_mass,epoch["geometry"]["cv_pressure_mass_coeff"],
                    epoch["face_pressure_psi"],p_ref,epoch["weights_m3_day"],epoch["xi_faces"],candidate_dt)
                child_mass=np.asarray(exact_fallback["new_mass"],float).copy()
                child_cv_sat=np.asarray(exact_fallback["new_saturation"],float).copy()

                u=np.asarray(sg7a.u_dimensionless(epoch["xi_faces"]),float)
                q=np.asarray(epoch["weights_m3_day"],float)
                inlet_rate=q*float(e37a.CO2_RHO_REF_KG_M3)
                outlet_sat=old_sat[:,-1]
                outlet_ff=np.asarray(sg7a.fractional_flow(outlet_sat),float)
                outlet_rho=np.asarray(physics.gas_density_from_state(
                    outlet_sat,epoch["face_pressure_psi"][:,-1],p_ref),float)
                outlet_rate=q*float(u[-1])*outlet_ff*outlet_rho
                target_i=np.sum(old_mass,axis=1)+inlet_rate*candidate_dt-outlet_rate*candidate_dt

                direct_res=float(np.max(np.abs(np.sum(child_mass,axis=1)-target_i)))
                if direct_res>1e-7:
                    raise GateError(f"boundary_budget_vs_exact_fallback:{direct_res}")

                epoch_tag=f"INTA1R1_E{epoch_serial}"
                pp,_,pr=infer_profiles(parent_time,db,epoch_tag)
                cp,_,cr=infer_profiles(parent_time+candidate_dt,db,epoch_tag)
                eligible=np.asarray(sorted(set(pp).intersection(cp)),dtype=np.int64)

                correction_l1=[]
                if eligible.size:
                    parent_prof=np.stack([pp[int(i)] for i in eligible],axis=0)
                    child_prof=np.stack([cp[int(i)] for i in eligible],axis=0)
                    _,pmm,_=b1.project_201_to_200_component_mass(
                        physics,e37a,parent_prof,epoch["geometry"]["cv_pressure_mass_coeff"],eligible)
                    _,cmm,_=b1.project_201_to_200_component_mass(
                        physics,e37a,child_prof,epoch["geometry"]["cv_pressure_mass_coeff"],eligible)
                    raw=old_mass[eligible]+(cmm-pmm)
                    for j,sl in enumerate(eligible):
                        coeff=np.asarray(epoch["geometry"]["cv_pressure_mass_coeff"])[sl]
                        cap=np.asarray(e37a.cv_mass_from_saturation(
                            physics,
                            np.full(int(epoch["ncv"]),float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)),
                            coeff),float)
                        mm,lam,closure=a1.box_project(raw[j],float(target_i[sl]),cap)
                        if abs(float(closure))>1e-8:
                            raise GateError(f"Hybrid_budget_closure:{sl}:{closure}")
                        denom=max(float(np.sum(np.abs(raw[j]))),1e-30)
                        correction_l1.append(float(np.sum(np.abs(mm-raw[j])))/denom)
                        ss=np.asarray(e37a.invert_cv_mass_to_saturation(physics,mm,coeff),float)
                        child_mass[sl]=mm
                        child_cv_sat[sl]=ss

                injected_step=float(np.sum(inlet_rate)*candidate_dt)
                produced_step=float(np.sum(outlet_rate)*candidate_dt)
                physical_injected=INJECTOR_MASS_RATE_KG_DAY*candidate_dt
                itol=max(1e-6,1e-12*max(abs(physical_injected),1.0))
                if abs(injected_step-physical_injected)>itol:
                    raise GateError(f"fixed_rate_injection_mismatch:{injected_step-physical_injected}")

                parent_cell_mass=r3r4.parent_cellwise_component_mass(physics,parent_sat,pressure,p_ref,cell_pv)
                target_final=parent_stored+injected_step-produced_step
                preflight=r3r4.preflight_mapback_capacity(
                    physics=physics,parent_saturation=parent_sat,parent_mass=parent_cell_mass,
                    old_cv_saturation=old_sat,new_cv_saturation=child_cv_sat,geometry=epoch["geometry"],
                    pressure_psi=pressure,p_ref_gas_pa=p_ref,cell_pore_volume_m3=cell_pv)
                capacity_margins.append(float(preflight["minimum_capacity_margin_kg"]))

                if int(preflight["overcapacity_cell_count"])>0:
                    capacity_rows.append({
                        "physical_time_days":parent_time,
                        "accepted_step_index":parent_step,
                        "trial_dt_days":candidate_dt,
                        "overcapacity_cell_count":int(preflight["overcapacity_cell_count"]),
                        "max_capacity_excess_kg":float(preflight["max_capacity_excess_kg"]),
                        "minimum_capacity_margin_kg":float(preflight["minimum_capacity_margin_kg"]),
                        "planned_schedule_status":"BLOCK_REQUIRES_SEPARATE_UPPER_CAPACITY_PROTOCOL_REPAIR",
                    })
                    do_refresh("CAPACITY_PREFLIGHT_REJECTION",scheduled=False)
                    raise GateError("unscheduled_upper_capacity_refresh_requires_separate_protocol_repair")

                try:
                    mapping=e37a.map_control_volume_increment_to_grid(
                        physics,parent_sat,old_sat,child_cv_sat,old_mass,child_mass,epoch["geometry"],
                        pressure,p_ref,cell_pv,target_final)
                    mapback_mode="ORDINARY_E37A"
                    break
                except e37a.TrialReject as exc:
                    reason=str(exc)
                    if not reason.startswith("aligned_mapback_negative_cell_mass:"):
                        raise
                    try:
                        rejected_min_mass=float(reason.rsplit(":",1)[1])
                    except Exception:
                        rejected_min_mass=float("nan")
                    if minimum_rejected_trial_cell_mass_kg is None or (
                        np.isfinite(rejected_min_mass)
                        and rejected_min_mass < minimum_rejected_trial_cell_mass_kg
                    ):
                        minimum_rejected_trial_cell_mass_kg=rejected_min_mass

                    # After the certified local validation, ordinary E37A remains first path
                    # but every negative-cell rejection invokes the frozen ownership operator directly.
                    if local_validation_passed:
                        mapping=ownership_reconciled_mapback(
                            physics,e37a,parent_sat,old_sat,child_cv_sat,old_mass,child_mass,
                            epoch["geometry"],pressure,p_ref,cell_pv,target_final)
                        audit=mapping["ownership_audit"]
                        ownership_reconciliation_count+=1
                        mapback_mode="CARTESIAN_GLOBAL_DELTA_PROJECTED"
                        ownership_rows.append({
                            "event_role":"POST_VALIDATION_FALLBACK",
                            "parent_time_days":parent_time,
                            "accepted_step_index_candidate":parent_step+1,
                            "trial_dt_days":candidate_dt,
                            "ordinary_E37A_reject_reason":reason,
                            "supported_cell_count":audit["supported_cell_count"],
                            "raw_negative_cell_count":audit["raw_negative_cell_count"],
                            "raw_overcapacity_cell_count":audit["raw_overcapacity_cell_count"],
                            "projection_correction_L1_kg":audit["projection_correction_L1_kg"],
                            "projection_correction_L2_kg":audit["projection_correction_L2_kg"],
                            "projection_correction_Linf_kg":audit["projection_correction_Linf_kg"],
                            "changed_supported_cell_count":audit["changed_supported_cell_count"],
                            "lower_bound_active_cell_count":audit["lower_bound_active_cell_count"],
                            "upper_bound_active_cell_count":audit["upper_bound_active_cell_count"],
                            "projection_lambda_kg":audit["projection_lambda_kg"],
                            "projection_sum_residual_kg":audit["projection_sum_residual_kg"],
                            "raw_global_target_residual_kg":audit["raw_global_target_residual_kg"],
                            "raw_E37A_transfer_residual_kg":audit["raw_E37A_transfer_residual_kg"],
                            "global_component_delta_identity_residual_kg":audit["global_component_delta_identity_residual_kg"],
                            "outside_support_identity_Linf_kg":audit["outside_support_identity_Linf_kg"],
                            "zero_delta_identity_Linf_kg":audit["zero_delta_identity_Linf_kg"],
                            "minimum_child_grid_mass_kg":audit["minimum_child_grid_mass_kg"],
                            "maximum_child_capacity_excess_kg":audit["maximum_child_capacity_excess_kg"],
                            "grid_ledger_residual_kg":audit["grid_ledger_residual_kg"],
                            "supported_target_mass_kg":audit["supported_target_mass_kg"],
                            "supported_capacity_mass_kg":audit["supported_capacity_mass_kg"],
                            "transport_global_delta_kg":audit["transport_global_delta_kg"],
                        })
                        break

                    # Before local validation, reproduce R1's exact same-parent dt-refinement path.
                    negative_retry_count+=1
                    negative_mapback_retry_total+=1
                    next_dt=candidate_dt*NEGATIVE_MAPBACK_RETRY_FACTOR
                    mapback_retry_rows.append({
                        "parent_time_days":parent_time,
                        "accepted_step_index":parent_step,
                        "flow_epoch_origin_day":epoch_start_time,
                        "flow_epoch_age_days":parent_time-epoch_start_time,
                        "retry_index_this_parent":negative_retry_count,
                        "nominal_candidate_dt_days":nominal_candidate_dt,
                        "rejected_trial_dt_days":candidate_dt,
                        "rejected_minimum_trial_cell_mass_kg":rejected_min_mass,
                        "reject_reason":reason,
                        "retry_factor":NEGATIVE_MAPBACK_RETRY_FACTOR,
                        "next_trial_dt_days":next_dt,
                        "same_parent_state_preserved":True,
                        "flow_refresh_performed":False,
                        "cell_mass_clipping_performed":False,
                        "mass_discard_performed":False,
                        "scientific_tolerance_relaxed":False,
            "support_expansion_performed":False,
                    })

                    if negative_retry_count>MAX_NEGATIVE_MAPBACK_RETRIES:
                        # The R1 terminal retry exhaustion is the certified R3 local-validation event.
                        if abs(parent_time-KNOWN_FAILED_PARENT_DAY)>KNOWN_FAILED_PARENT_DAY_TOL:
                            raise GateError(
                                f"prevalidation_retry_exhausted_before_certified_parent:"
                                f"{parent_time}:{KNOWN_FAILED_PARENT_DAY}:{reason}"
                            )
                        exact_control=e37a.map_control_volume_increment_to_grid(
                            physics,parent_sat,old_sat,
                            np.asarray(exact_fallback["new_saturation"],float),
                            old_mass,np.asarray(exact_fallback["new_mass"],float),
                            epoch["geometry"],pressure,p_ref,cell_pv,target_final)
                        if float(np.min(np.asarray(exact_control["corrected_mass"],float))) < -1e-8:
                            raise GateError("local_validation_exact_fallback_negative")

                        mapping=ownership_reconciled_mapback(
                            physics,e37a,parent_sat,old_sat,child_cv_sat,old_mass,child_mass,
                            epoch["geometry"],pressure,p_ref,cell_pv,target_final)
                        audit=mapping["ownership_audit"]
                        ownership_reconciliation_count+=1
                        mapback_mode="CARTESIAN_GLOBAL_DELTA_PROJECTED_LOCAL_VALIDATION"
                        ownership_rows.append({
                            "event_role":"CERTIFIED_PARENT_LOCAL_VALIDATION",
                            "parent_time_days":parent_time,
                            "accepted_step_index_candidate":parent_step+1,
                            "trial_dt_days":candidate_dt,
                            "ordinary_E37A_reject_reason":reason,
                            "R1_retry_index":negative_retry_count,
                            "supported_cell_count":audit["supported_cell_count"],
                            "raw_negative_cell_count":audit["raw_negative_cell_count"],
                            "raw_overcapacity_cell_count":audit["raw_overcapacity_cell_count"],
                            "projection_correction_L1_kg":audit["projection_correction_L1_kg"],
                            "projection_correction_L2_kg":audit["projection_correction_L2_kg"],
                            "projection_correction_Linf_kg":audit["projection_correction_Linf_kg"],
                            "changed_supported_cell_count":audit["changed_supported_cell_count"],
                            "lower_bound_active_cell_count":audit["lower_bound_active_cell_count"],
                            "upper_bound_active_cell_count":audit["upper_bound_active_cell_count"],
                            "projection_lambda_kg":audit["projection_lambda_kg"],
                            "projection_sum_residual_kg":audit["projection_sum_residual_kg"],
                            "raw_global_target_residual_kg":audit["raw_global_target_residual_kg"],
                            "raw_E37A_transfer_residual_kg":audit["raw_E37A_transfer_residual_kg"],
                            "global_component_delta_identity_residual_kg":audit["global_component_delta_identity_residual_kg"],
                            "outside_support_identity_Linf_kg":audit["outside_support_identity_Linf_kg"],
                            "zero_delta_identity_Linf_kg":audit["zero_delta_identity_Linf_kg"],
                            "minimum_child_grid_mass_kg":audit["minimum_child_grid_mass_kg"],
                            "maximum_child_capacity_excess_kg":audit["maximum_child_capacity_excess_kg"],
                            "grid_ledger_residual_kg":audit["grid_ledger_residual_kg"],
                            "supported_target_mass_kg":audit["supported_target_mass_kg"],
                            "supported_capacity_mass_kg":audit["supported_capacity_mass_kg"],
                            "transport_global_delta_kg":audit["transport_global_delta_kg"],
                        })
                        local_tol=max(1e-7,float(mapping["roundoff_mass_kg"]))
                        if audit["zero_delta_identity_Linf_kg"] > local_tol:
                            raise GateError(f"local_validation_zero_delta_identity:{audit['zero_delta_identity_Linf_kg']}:{local_tol}")
                        if abs(audit["raw_E37A_transfer_residual_kg"]) > local_tol:
                            raise GateError(f"local_validation_raw_E37A_transfer_closure:{audit['raw_E37A_transfer_residual_kg']}:{local_tol}")
                        if abs(audit["global_component_delta_identity_residual_kg"]) > local_tol:
                            raise GateError(f"local_validation_global_component_delta_identity:{audit['global_component_delta_identity_residual_kg']}:{local_tol}")
                        if audit["outside_support_identity_Linf_kg"] > local_tol:
                            raise GateError(f"local_validation_outside_support_identity:{audit['outside_support_identity_Linf_kg']}:{local_tol}")
                        if audit["minimum_child_grid_mass_kg"] < -local_tol:
                            raise GateError(f"local_validation_negative_grid:{audit['minimum_child_grid_mass_kg']}:{local_tol}")
                        if audit["maximum_child_capacity_excess_kg"] > local_tol:
                            raise GateError(f"local_validation_capacity:{audit['maximum_child_capacity_excess_kg']}:{local_tol}")
                        local_validation_passed=True
                        local_validation_parent_day=parent_time
                        break

                    if not np.isfinite(next_dt) or next_dt<=0:
                        raise GateError(f"invalid_negative_mapback_retry_dt:{next_dt}")
                    candidate_dt=float(next_dt)
                    continue

            if negative_retry_count>0:
                negative_mapback_retry_step_count+=1
                maximum_negative_mapback_retries_on_one_step=max(
                    maximum_negative_mapback_retries_on_one_step,
                    negative_retry_count,
                )
                if not local_validation_passed:
                    prevalidation_accepted_retry_step_count+=1
            capillary=physics.conservative_capillary_mass_redistribution(
                transport_saturation=np.asarray(mapping["corrected_saturation"],float),
                permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,
                cell_pore_volume_m3=cell_pv,dt_seconds=candidate_dt*DAY_TO_S)
            child_sat=np.asarray(capillary["corrected"],float)
            final_stored=float(capillary["final_mass_state_kg"])
            step_residual=final_stored-parent_stored-injected_step+produced_step
            ctol=max(1e-6,1e-10*max(abs(target_final),1.0))
            if abs(float(capillary["external_mass_change_kg"]))>ctol:
                raise GateError(f"capillary_external_mass_change:{capillary['external_mass_change_kg']}")
            if abs(step_residual)>ctol:
                raise GateError(f"step_component_mass_closure:{step_residual}")

            prod_rows,aggregate_cut=e37a.producer_rows_from_flux(
                epoch["labels"],epoch["weights_m3_day"],
                np.asarray(sg7a.fractional_flow(old_sat[:,-1]),float),
                outlet_rate,candidate_dt)
            if not np.isfinite(aggregate_cut) or not 0<=aggregate_cut<=1:
                raise GateError(f"producer_gas_cut_invalid:{aggregate_cut}")

            child=e36.make_child_state(
                current,child_sat,pressure,p_ref,candidate_dt,produced_step,
                aggregate_cut,final_stored,step_residual,False)
            child["transport_face_count"]=np.asarray(epoch["nfaces"],dtype=np.int64)
            child["transport_control_volume_count"]=np.asarray(epoch["ncv"],dtype=np.int64)
            child["mass_conservative_flow_refresh_active"]=np.asarray(True,dtype=bool)
            child["runtime_refresh_policy_name_ascii"]=np.frombuffer(POLICY_NAME.encode("ascii"),dtype=np.uint8)
            child["runtime_max_flow_epoch_days"]=np.asarray(MAX_FLOW_EPOCH_DAYS,dtype=np.float64)
            child["hybrid_recurrent_bridge_active"]=np.asarray(True,dtype=bool)
            child["hybrid_recurrent_mode_ascii"]=np.frombuffer(b"HYBRID_INCREMENTAL_MIXED",dtype=np.uint8)
            child["hybrid_parent_anchored_incremental"]=np.asarray(True,dtype=bool)
            child["hybrid_incremental_route_count"]=np.asarray(int(eligible.size),dtype=np.int64)
            child["exact_fallback_route_count"]=np.asarray(int(epoch["nstream"]-eligible.size),dtype=np.int64)
            child["last_grid_mapback_ledger_residual_kg"]=np.asarray(mapping["ledger_residual_kg"],dtype=np.float64)
            child["last_capillary_external_mass_change_kg"]=np.asarray(capillary["external_mass_change_kg"],dtype=np.float64)
            child["flow_epoch_origin_day"]=np.asarray(epoch_start_time,dtype=np.float64)
            child["flow_epoch_age_days"]=np.asarray(parent_time+candidate_dt-epoch_start_time,dtype=np.float64)

            accepted_time=scalar(child["physical_time_days"])
            for boundary in (35.0,40.0,45.0):
                if abs(accepted_time-boundary)<=1e-13:
                    child["physical_time_days"]=np.asarray(boundary,dtype=np.float64)
                    accepted_time=boundary

            total_hybrid_routes+=int(eligible.size)
            total_exact_fallback_routes+=int(epoch["nstream"]-eligible.size)
            route_rows.append({
                "accepted_step_index":int_scalar(child["accepted_step_index"]),
                "parent_time_days":parent_time,
                "accepted_time_days":accepted_time,
                "Hybrid_incremental_route_count":int(eligible.size),
                "exact_fallback_route_count":int(epoch["nstream"]-eligible.size),
                "Hybrid_route_fraction":float(eligible.size/max(int(epoch["nstream"]),1)),
                "parent_screen_rejection_count":int(sum(pr.values())),
                "child_screen_rejection_count":int(sum(cr.values())),
                "mass_correction_relative_L1_median":float(np.median(correction_l1)) if correction_l1 else 0.0,
                "mass_correction_relative_L1_p95":float(np.quantile(correction_l1,0.95)) if correction_l1 else 0.0,
                "negative_mapback_retry_count":negative_retry_count,
                "mapback_mode":mapback_mode,
            })
            step_rows.append({
                "accepted_step_index":int_scalar(child["accepted_step_index"]),
                "parent_time_days":parent_time,
                "accepted_time_days":accepted_time,
                "nominal_candidate_dt_days":nominal_candidate_dt,
                "accepted_dt_days":candidate_dt,
                "negative_mapback_retry_count":negative_retry_count,
                "mapback_mode":mapback_mode,
                "active_epoch_CFL_dt_days":float(epoch["cfl_dt_days"]),
                "epoch_origin_day":epoch_start_time,
                "epoch_age_before_step_days":parent_time-epoch_start_time,
                "controller_boundary_landing":accepted_time in (35.0,40.0,45.0),
                "raw_minimum_capacity_margin_kg":float(preflight["minimum_capacity_margin_kg"]),
                "injected_CO2_mass_kg":injected_step,
                "produced_CO2_mass_kg":produced_step,
                "stored_CO2_mass_kg":final_stored,
                "step_component_mass_residual_kg":step_residual,
                "producer_CO2_gas_cut":float(aggregate_cut),
                "Hybrid_incremental_route_count":int(eligible.size),
                "exact_fallback_route_count":int(epoch["nstream"]-eligible.size),
            })

            current={k:np.asarray(v).copy() for k,v in child.items()}
            if accepted_time in (35.0,40.0,45.0):
                pre_boundary_states[accepted_time]={k:np.asarray(v).copy() for k,v in current.items()}

        stage="Day45_final_refresh"
        gate("Day45_pre_refresh_landing",scalar(current["physical_time_days"])==45.0,scalar(current["physical_time_days"]))
        gate("Day45_epoch_origin_40",abs(epoch_start_time-40.0)<=1e-12,epoch_start_time)
        gate("Day45_controller_action_refresh",
             g3r5.decide_shadow_action(45.0,epoch_start_time).action=="FULL_FLOW_REFRESH")
        do_refresh("CADENCE",scheduled=True)

        stage="trajectory_closure"
        gate("final_day_45",scalar(current["physical_time_days"])==45.0,scalar(current["physical_time_days"]))
        gate("scheduled_refresh_times_exact",
             [float(r["physical_time_days"]) for r in refresh_rows if r["scheduled"]]==[30.0,35.0,40.0,45.0],
             [r["physical_time_days"] for r in refresh_rows])
        gate("no_unscheduled_refresh",unscheduled_refresh is False)
        gate("capacity_triggered_refresh_count_zero",capacity_refresh_count==0,capacity_refresh_count)
        gate("cadence_refresh_count_three",cadence_refresh_count==3,cadence_refresh_count)
        gate("total_refresh_count_four",refresh_count==4,refresh_count)
        gate("R1_prevalidation_retry_path_replayed",
             negative_mapback_retry_total>=13,negative_mapback_retry_total)
        gate("certified_parent_local_validation_passed",
             local_validation_passed is True,local_validation_parent_day)
        gate("certified_parent_local_validation_day_exact",
             abs(float(local_validation_parent_day)-KNOWN_FAILED_PARENT_DAY)<=KNOWN_FAILED_PARENT_DAY_TOL,
             local_validation_parent_day)
        gate("terminal_R1_retry_count_reproduced",
             maximum_negative_mapback_retries_on_one_step>=13,
             maximum_negative_mapback_retries_on_one_step)
        gate("cartesian_global_delta_projection_used",
             ownership_reconciliation_count>=1,ownership_reconciliation_count)
        gate("repair_did_not_add_flow_refresh",
             [float(r["physical_time_days"]) for r in refresh_rows]==[30.0,35.0,40.0,45.0],
             [r["physical_time_days"] for r in refresh_rows])
        gate("visual_checkpoint_days_complete",sorted(checkpoint_payloads)==[30.0,35.0,40.0,45.0],sorted(checkpoint_payloads))
        gate("Day30_parent_immutable",sha(parent_path)==parent_sha_before,sha(parent_path))

        final_stored=scalar(current["stored_co2_mass_current_kg"])
        final_injected=scalar(current["cumulative_injected_co2_mass_kg"])
        final_produced=scalar(current["cumulative_produced_co2_mass_kg"])
        cumulative_residual=final_stored-scalar(current["stored_co2_mass_initial_kg"])-final_injected+final_produced
        mtol=max(1e-6,1e-10*max(abs(final_stored),1.0))
        gate("final_component_mass_closure",abs(cumulative_residual)<=mtol,(cumulative_residual,mtol))
        expected_added_injection=INJECTOR_MASS_RATE_KG_DAY*(TARGET_DAY-START_DAY)
        actual_added_injection=final_injected-initial_injected
        gate("Day30_to45_injection_rate_exact",
             abs(actual_added_injection-expected_added_injection)<=max(1e-6,1e-12*expected_added_injection),
             (actual_added_injection,expected_added_injection))

        stage="immutable_reference_comparison"
        ref_summary_path=drive/g2.OUT_REL/g2.SUMMARY
        ref40_path=drive/g2.OUT_REL/g2.DAY40_STATE
        ref45_path=drive/g2.OUT_REL/g2.DAY45_STATE
        for label,p in [("G2R3_summary",ref_summary_path),("G2R3_Day40",ref40_path),("G2R3_Day45",ref45_path)]:
            gate(label+"_present",p.is_file(),str(p))
        ref_summary=js(ref_summary_path)
        gate("G2R3_status_exact",ref_summary.get("status")==g2.PASS,ref_summary.get("status"))
        gate("G2R3_reference_continuous",ref_summary.get("continuous_30_to45_rollout") is True)
        refs={40.0:load_npz(ref40_path),45.0:load_npz(ref45_path)}
        for day in (40.0,45.0):
            controlled=pre_boundary_states[day]
            ref=refs[day]
            cs=np.asarray(controlled["transport_saturation"],float)
            rs=np.asarray(ref["transport_saturation"],float)
            metrics={
                "day":day,
                "controlled_vs_reference_saturation_relative_L2":rel_l2(cs,rs),
                "controlled_vs_reference_saturation_Linf":float(np.max(np.abs(cs-rs))),
                "controlled_minus_reference_stored_mass_kg":
                    scalar(controlled["stored_co2_mass_current_kg"])-scalar(ref["stored_co2_mass_current_kg"]),
                "controlled_minus_reference_cumulative_produced_mass_kg":
                    scalar(controlled["cumulative_produced_co2_mass_kg"])-scalar(ref["cumulative_produced_co2_mass_kg"]),
                "controlled_minus_reference_producer_gas_cut":
                    scalar(controlled["current_producer_co2_gas_cut"])-scalar(ref["current_producer_co2_gas_cut"]),
                "new_scientific_acceptance_threshold_applied":False,
                "comparison_role":"DIAGNOSTIC_ONLY_IMMUTABLE_REFERENCE",
            }
            gate(f"Day{int(day)}_reference_metrics_finite",
                 all(np.isfinite(float(metrics[k])) for k in [
                     "controlled_vs_reference_saturation_relative_L2",
                     "controlled_vs_reference_saturation_Linf",
                     "controlled_minus_reference_stored_mass_kg",
                     "controlled_minus_reference_cumulative_produced_mass_kg",
                     "controlled_minus_reference_producer_gas_cut"]))
            reference_rows.append(metrics)

        stage="publication"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)

        for day in VIS_DAYS:
            payload=checkpoint_payloads[day]
            fn=f"{OUT_TOKEN}_Day{int(day):03d}_Visualization_Checkpoint.npz"
            b=deterministic_npz_bytes(payload)
            (out/fn).write_bytes(b)
            checkpoint_rows.append({
                "day":day,
                "file":fn,
                "sha256":hashlib.sha256(b).hexdigest(),
                "pressure_ready":True,
                "saturation_ready":True,
                "component_mass_ready":True,
                "streamlines_ready":True,
                "TOF_ready":True,
                "controller_overlay_ready":True,
            })

        final_bytes=deterministic_npz_bytes(current)
        (out/FINAL_STATE).write_bytes(final_bytes)

        summary={
            "milestone":M,
            "status":PASS,
            "classification":"R3R2_CARTESIAN_GLOBAL_DELTA_PROJECTION_LOCAL_VALIDATION_PASS_AND_CONTROLLED_DAY30_DAY45_WHOLE_SYSTEM_TRAJECTORY_COMPLETE_VISUALIZATION_READY",
            "R3_R2_design_freeze_bound":True,
            "R4_R2_R1_R1_formal_BLOCK_bound":True,
            "per_CV_exclusive_delta_ownership_constraint_used":False,
            "E37A_global_component_delta_is_mapback_authority":True,
            "accepted_CV_transport_state_mutated_by_projection":False,
            "projection_space":"CARTESIAN_CELL_MASS_ON_EXISTING_E37A_SUPPORT",
            "projection_objective":"MINIMUM_L2_CORRECTION_TO_RAW_E37A_TRIAL",
            "immutable_local_R4_R2_R1_technical_selftest_failure_bound":True,
            "structural_selftest_repair_only":True,
            "immutable_local_R4_R2_technical_selftest_failure_bound":True,
            "HiGHS_primal_feasibility_tolerance":HIGHS_PRIMAL_FEASIBILITY_TOL,
            "HiGHS_dual_feasibility_tolerance":HIGHS_DUAL_FEASIBILITY_TOL,
            "scientific_delta_identity_gate_kg":SCIENTIFIC_DELTA_IDENTITY_GATE_KG,
            "scientific_tolerance_relaxed":False,
            "R3_R1_corrected_design_bound":True,
            "local_R4_R2_technical_selftest_failure_bound":True,
            "HiGHS_primal_feasibility_tolerance":HIGHS_PRIMAL_FEASIBILITY_TOL,
            "HiGHS_dual_feasibility_tolerance":HIGHS_DUAL_FEASIBILITY_TOL,
            "scientific_delta_identity_gate_kg":SCIENTIFIC_DELTA_IDENTITY_GATE_KG,
            "R4_R1_immutable_BLOCK_bound":True,
            "absolute_sampled_CV_ownership_constraint_used":False,
            "immutable_R4_BLOCK_bound":True,
            "immutable_R4_BLOCK_exception":R4_EXPECTED_EXCEPTION,
            "R3_design_freeze_bound":True,
            "R3_R1_corrected_design_bound":True,
            "R3_R1_corrected_design_bound":True,
            "R3_R2_local_validation_passed":local_validation_passed,
            "R3_R2_local_validation_parent_day":local_validation_parent_day,
            "prevalidation_accepted_retry_step_count":prevalidation_accepted_retry_step_count,
            "cartesian_global_delta_projection_count":ownership_reconciliation_count,
            "immutable_INT_A1_BLOCK_bound":True,
            "immutable_INT_A1_BLOCK_exception":INTA1_EXPECTED_EXCEPTION,
            "starting_day":START_DAY,
            "target_day":TARGET_DAY,
            "development_flow_refresh_reference_days":MAX_FLOW_EPOCH_DAYS,
            "scheduled_refresh_days":[30.0,35.0,40.0,45.0],
            "accepted_transport_transition_count":len(step_rows),
            "total_flow_refresh_count":refresh_count,
            "cadence_refresh_count":cadence_refresh_count,
            "capacity_triggered_refresh_count":capacity_refresh_count,
            "negative_mapback_rejected_trial_count":negative_mapback_retry_total,
            "negative_mapback_retry_step_count":negative_mapback_retry_step_count,
            "maximum_negative_mapback_retries_on_one_step":maximum_negative_mapback_retries_on_one_step,
            "minimum_rejected_trial_cell_mass_kg":minimum_rejected_trial_cell_mass_kg,
            "minimum_raw_capacity_margin_kg":float(np.min(capacity_margins)) if capacity_margins else None,
            "cumulative_Hybrid_route_uses":total_hybrid_routes,
            "cumulative_exact_fallback_route_uses":total_exact_fallback_routes,
            "final_cumulative_component_mass_residual_kg":cumulative_residual,
            "Day30_to45_added_injected_CO2_mass_kg":actual_added_injection,
            "Hybrid_parent_anchored_incremental_transport_used":True,
            "exact_E37A_fallback_used":True,
            "exact_FV_Darcy_Pollock_TOF_refresh_used":True,
            "ordinary_E37A_mapback_first_path_preserved":True,
            "R1_prevalidation_dt_retry_replay_used":True,
            "cartesian_global_delta_projection_negative_cell_fallback_used":ownership_reconciliation_count>0,
            "existing_E37A_support_only":True,
            "conservative_capillary_redistribution_used":True,
            "visualization_checkpoint_days":[30.0,35.0,40.0,45.0],
            "visualization_checkpoint_count":4,
            "visualization_ready":True,
            "Day40_reference_comparison":reference_rows[0],
            "Day45_reference_comparison":reference_rows[1],
            "negative_mapback_repair_policy":"PRE_VALIDATION_R1_DT_REPLAY_TO_CERTIFIED_PARENT_THEN_EXISTING_SUPPORT_CARTESIAN_BOUNDED_GLOBAL_DELTA_PROJECTION",
            "negative_mapback_retry_factor":NEGATIVE_MAPBACK_RETRY_FACTOR,
            "negative_mapback_retry_budget":MAX_NEGATIVE_MAPBACK_RETRIES,
            "cell_mass_clipping_performed":False,
            "mass_discard_performed":False,
            "mapback_spatial_operator_modified":True,
            "mapback_spatial_operator_change_scope":"NEGATIVE_CELL_REJECTION_ONLY_EXISTING_SUPPORT_CARTESIAN_EXACT_SUM_MINIMUM_L2_PROJECTION",
            "cartesian_global_delta_projection_added_as_negative_cell_fallback":True,
            "support_expansion_performed":False,
            "scientific_tolerance_relaxed":False,
            "new_scientific_accuracy_threshold_defined":False,
            "historical_reference_replaced":False,
            "canonical_state_mutated":False,
            "trajectory_class":"CONTROLLED_NONCANONICAL_WHOLE_SYSTEM_SHADOW_TRAJECTORY",
            "INT_VIS_A1_integrated_3D_visualization_authorized":True,
            "longer_horizon_validation_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
            "final_state_file":FINAL_STATE,
            "final_state_sha256":hashlib.sha256(final_bytes).hexdigest(),
        }

        decision={
            "milestone":M,
            "status":PASS,
            "controlled_whole_system_integration_executed":True,
            "immutable_R4_BLOCK_preserved":True,
            "R3_design_freeze_bound":True,
            "R3_R2_local_validation_passed":local_validation_passed,
            "R3_R2_local_validation_parent_day":local_validation_parent_day,
            "cartesian_global_delta_projection_count":ownership_reconciliation_count,
            "immutable_INT_A1_BLOCK_preserved":True,
            "negative_mapback_trial_repair_executed":True,
            "negative_mapback_repair":"R1 replay to certified parent, then existing-support Cartesian bounded global-delta projection; ordinary E37A remains first path",
            "five_day_controller_boundaries_executed":[35.0,40.0,45.0],
            "whole_system_chain":{
                "pressure_flow":"EXACT_FV_DARCY",
                "streamline_geometry":"EXACT_POLLOCK",
                "time_of_flight":"EXACT_TOF",
                "transport":"HYBRID10_PROPOSAL_PLUS_EXACT_E37A_FALLBACK",
                "conservation":"EXACT_COMPONENT_MASS_BUDGET_PLUS_BOX_PROJECTION",
                "mapback":"ORDINARY_E37A_FIRST_THEN_EXISTING_SUPPORT_CARTESIAN_BOUNDED_EXACT_SUM_MINIMUM_L2_PROJECTION_ON_NEGATIVE_CELL_REJECTION",
                "capillary":"CONSERVATIVE_CARTESIAN_REDISTRIBUTION",
            },
            "next_milestone":{
                "name":"POSTV16-AV4-PIVOT-GPU-HYB-INT-VIS-A1",
                "purpose":"Generate integrated 3D pressure, pressure-change, saturation/CO2-mass, streamline, TOF, controller-event, and Cartesian-projection figures from Day30/35/40/45 checkpoints.",
                "authorized":True,
            },
            "longer_horizon_validation_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "P4_authorized":False,
        }

        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        write_csv(out/STEPS,step_rows)
        write_csv(out/REFRESHES,refresh_rows)
        write_csv(out/CAPACITY,capacity_rows)
        write_csv(out/CONTROLLER,controller_rows)
        write_csv(out/MAPBACK_RETRIES,mapback_retry_rows)
        write_csv(out/OWNERSHIP,ownership_rows)
        write_csv(out/ROUTES,route_rows)
        write_csv(out/REFERENCE,reference_rows)
        write_csv(out/CHECKPOINTS,checkpoint_rows)
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[
            {"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
            for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST
        ])

        print("="*202)
        print(M,"PASS")
        print("Main spine phase                            : CONTROLLED WHOLE-SYSTEM INTEGRATION")
        print("Window                                      : Day30 -> Day45")
        print("Scheduled refreshes                         : Day30 / Day35 / Day40 / Day45")
        print("Pre-validation negative trial count          :",negative_mapback_retry_total)
        print("Cartesian global-delta projection uses       :",ownership_reconciliation_count)
        print("Certified local-validation parent day        :",local_validation_parent_day)
        print("Steps requiring negative-mapback dt retry    :",negative_mapback_retry_step_count)
        print("Worst rejected trial cell mass kg            :",minimum_rejected_trial_cell_mass_kg)
        print("Accepted transport transitions              :",len(step_rows))
        print("Cumulative Hybrid / exact fallback uses     :",total_hybrid_routes,"/",total_exact_fallback_routes)
        print("Final cumulative mass residual kg           :",cumulative_residual)
        print("Visualization checkpoints ready             : Day30 / Day35 / Day40 / Day45")
        print("INT-VIS-A1 integrated 3D visualization      : AUTHORIZED")
        print("Longer-horizon validation                   : NOT YET AUTHORIZED")
        print("Production activation                       : False")
        print("P4 authorized                               : False")
        print("="*202)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,
            "status":BLOCK,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "Day30_parent_sha256_before":parent_sha_before,
            "controlled_whole_system_integration_executed":False,
            "immutable_INT_A1_BLOCK_preserved":True,
            "prevalidation_R1_retry_policy_active":True,
            "postvalidation_cartesian_projection_fallback_active":local_validation_passed,
            "cell_mass_clipping_performed":False,
            "mass_discard_performed":False,
            "scientific_tolerance_relaxed":False,
            "INT_VIS_A1_integrated_3D_visualization_authorized":False,
            "longer_horizon_validation_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"BLOCK")
        print("Stage:",stage)
        print("Exception:",repr(exc))
        return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        selftest(a.project_root.resolve())
        raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
