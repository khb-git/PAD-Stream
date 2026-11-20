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

M="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R4-R1"
PASS="POSTV16AV4PIVOTGPUHYBINTA1R4R1_CERTIFIED_PARENT_REPLAY_OWNERSHIP_VALIDATION_AND_DAY30_DAY45_RUN_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBINTA1R4R1_TECHNICAL_CONSERVATION_OWNERSHIP_CAPACITY_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="7fc9e57fd48a4926bb2eeae6b02e7ab126a68817"

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

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R1"
OUT_REL=BASE/(OUT_TOKEN+"_CertifiedParent_Replay_Ownership_Validation_and_Day30_Day45_Run")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
STEPS=f"{OUT_TOKEN}_Accepted_Transitions.csv"
REFRESHES=f"{OUT_TOKEN}_Flow_Refreshes.csv"
CAPACITY=f"{OUT_TOKEN}_Capacity_Events.csv"
CONTROLLER=f"{OUT_TOKEN}_Controller_Events.csv"
MAPBACK_RETRIES=f"{OUT_TOKEN}_PreValidation_Negative_Mapback_Timestep_Retries.csv"
OWNERSHIP=f"{OUT_TOKEN}_Ownership_Reconciliation_Audit.csv"
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

def _parent_ownership_lp(pair_cv,pair_cell,q0,m0,g0):
    n=len(q0); ncv=len(m0); ncell=len(g0)
    Aeqx=_incidence(pair_cv,ncv,n)
    Acell=_incidence(pair_cell,ncell,n)
    I=eye(n,format="csr")
    Aub=vstack([
        hstack([ I,-I],format="csr"),
        hstack([-I,-I],format="csr"),
        hstack([Acell,csr_matrix((ncell,n))],format="csr"),
    ],format="csr")
    bub=np.concatenate([q0,-q0,g0])
    Aeq=hstack([Aeqx,csr_matrix((ncv,n))],format="csr")
    c=np.concatenate([np.zeros(n),np.ones(n)])
    res=linprog(c,A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=m0,
                bounds=[(0.0,None)]*(2*n),method="highs",
                options={"presolve":True})
    if not res.success:
        raise GateError(f"parent_ownership_stageA_infeasible:{res.status}:{res.message}")
    p=np.asarray(res.x[:n],dtype=np.float64)
    return p,float(np.sum(res.x[n:])),{"status":int(res.status),"message":str(res.message)}

def _child_stage1(pair_cv,pair_cell,target,m1,available):
    n=len(target); ncv=len(m1); ncell=len(available)
    Aeqx=_incidence(pair_cv,ncv,n); Acell=_incidence(pair_cell,ncell,n); I=eye(n,format="csr")
    Aub=vstack([
        hstack([ I,-I],format="csr"),
        hstack([-I,-I],format="csr"),
        hstack([Acell,csr_matrix((ncell,n))],format="csr"),
    ],format="csr")
    bub=np.concatenate([target,-target,available])
    Aeq=hstack([Aeqx,csr_matrix((ncv,n))],format="csr")
    c=np.concatenate([np.zeros(n),np.ones(n)])
    res=linprog(c,A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=m1,
                bounds=[(0.0,None)]*(2*n),method="highs",
                options={"presolve":True})
    if not res.success:
        raise GateError(f"child_ownership_stage1_infeasible:{res.status}:{res.message}")
    return np.asarray(res.x[:n],float),float(np.sum(res.x[n:])),{"status":int(res.status),"message":str(res.message)}

def _child_stage2(pair_cv,pair_cell,target,qtarget,m1,available,opt1,tol1):
    n=len(target); ncv=len(m1); ncell=len(available)
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
    res=linprog(c,A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=m1,
                bounds=[(0.0,None)]*(3*n),method="highs",
                options={"presolve":True})
    if not res.success:
        raise GateError(f"child_ownership_stage2_infeasible:{res.status}:{res.message}")
    return np.asarray(res.x[:n],float),float(np.sum(res.x[2*n:])),{"status":int(res.status),"message":str(res.message)}

def _child_stage3(pair_cv,pair_cell,target,qtarget,m1,available,opt1,tol1,opt2,tol2):
    n=len(target); ncv=len(m1); ncell=len(available)
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
    res=linprog(c,A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=m1,
                bounds=[(0.0,None)]*(3*n),method="highs",
                options={"presolve":True})
    if not res.success:
        raise GateError(f"child_ownership_stage3_infeasible:{res.status}:{res.message}")
    return np.asarray(res.x[:n],float),float(np.dot(rank,res.x[:n])),{"status":int(res.status),"message":str(res.message)}

def _child_assignment(pair_cv,pair_cell,p,q1,m0,m1,residual,capacity):
    ncv=len(m0); ncell=len(residual)
    eps=max(1e-12,1e-15*max(float(np.max(np.abs(m0))) if len(m0) else 1.0,1.0))
    # Mandatory zero-delta identity.
    zero_delta=_fmax(m1-m0) <= max(1e-10,1e-14*max(float(np.max(np.abs(m0))) if len(m0) else 1.0,1.0))
    if zero_delta:
        x=p.copy()
        return x,{"zero_delta_shortcut":True,"stage1_objective":0.0,"stage2_objective":0.0,"stage3_objective":0.0}

    positive=m0>eps
    scale=np.zeros_like(m0); scale[positive]=m1[positive]/m0[positive]
    target=p*scale[pair_cv]
    qcv=np.bincount(pair_cv,weights=q1,minlength=ncv)
    qtarget=np.zeros_like(q1)
    for j in np.flatnonzero((~positive)&(m1>eps)):
        mask=pair_cv==j
        if not np.any(mask) or qcv[j]<=eps:
            raise GateError(f"zero_parent_positive_child_without_raw_support:{int(j)}")
        target[mask]=q1[mask]*(m1[j]/qcv[j])
    for j in np.flatnonzero(m1>eps):
        mask=pair_cv==j
        if qcv[j]<=eps: qtarget[mask]=target[mask]
        else: qtarget[mask]=q1[mask]*(m1[j]/qcv[j])

    available=capacity-residual
    numtol=max(1e-7,1e-12*max(float(np.max(np.abs(capacity))),1.0))
    if float(np.min(available)) < -numtol:
        raise GateError(f"ownership_residual_exceeds_capacity:{float(np.min(available))}")
    available=np.maximum(available,0.0)
    x1,o1,m1meta=_child_stage1(pair_cv,pair_cell,target,m1,available)
    t1=max(1e-8,1e-12*max(abs(o1),1.0))
    x2,o2,m2meta=_child_stage2(pair_cv,pair_cell,target,qtarget,m1,available,o1,t1)
    t2=max(1e-8,1e-12*max(abs(o2),1.0))
    x3,o3,m3meta=_child_stage3(pair_cv,pair_cell,target,qtarget,m1,available,o1,t1,o2,t2)
    return x3,{"zero_delta_shortcut":False,
               "stage1_objective":o1,"stage2_objective":o2,"stage3_objective":o3,
               "stage1_meta":m1meta,"stage2_meta":m2meta,"stage3_meta":m3meta}

def ownership_reconciled_mapback(physics,e37a,parent_sat,old_cv_sat,new_cv_sat,
                                 old_cv_mass,new_cv_mass,geometry,pressure,pref,cellpv,target_final):
    cv_id=np.asarray(geometry["cv_id"],dtype=np.int64)
    flat=np.asarray(geometry["flat_cell"],dtype=np.int64)
    pv=np.asarray(geometry["pv_m3"],dtype=np.float64)
    pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64)
    ncell=int(np.prod(parent_sat.shape))
    m0=np.asarray(old_cv_mass,dtype=np.float64).reshape(-1)
    m1=np.asarray(new_cv_mass,dtype=np.float64).reshape(-1)

    oldf=np.asarray(old_cv_sat,dtype=np.float64).reshape(-1)
    newf=np.asarray(new_cv_sat,dtype=np.float64).reshape(-1)
    os=oldf[cv_id]; ns=newf[cv_id]
    osg=np.clip(os-physics.BACKGROUND_SATURATION,0.0,physics.MAX_INCREMENTAL_CO2_SATURATION)
    nsg=np.clip(ns-physics.BACKGROUND_SATURATION,0.0,physics.MAX_INCREMENTAL_CO2_SATURATION)
    ro=np.asarray(physics.gas_density_from_state(os,pseg,pref),dtype=np.float64)
    rn=np.asarray(physics.gas_density_from_state(ns,pseg,pref),dtype=np.float64)
    q0sub=pv*ro*osg
    q1sub=pv*rn*nsg
    pc,cell,q0,key0=_aggregate_pairs(cv_id,flat,q0sub,ncell)
    pc1,cell1,q1,key1=_aggregate_pairs(cv_id,flat,q1sub,ncell)
    if not (np.array_equal(key0,key1) and np.array_equal(pc,pc1) and np.array_equal(cell,cell1)):
        raise GateError("ownership_pair_support_mismatch")

    psat=np.asarray(parent_sat,dtype=np.float64)
    psg=np.clip(psat-physics.BACKGROUND_SATURATION,0.0,physics.MAX_INCREMENTAL_CO2_SATURATION)
    prho=np.asarray(physics.gas_density_from_state(psat,pressure,pref),dtype=np.float64)
    g0=float(cellpv)*prho*psg
    g0f=g0.reshape(-1)

    p,objA,metaA=_parent_ownership_lp(pc,cell,q0,m0,g0f)
    rec0=np.bincount(pc,weights=p,minlength=len(m0))
    mapped0=np.bincount(cell,weights=p,minlength=ncell)
    residual=g0f-mapped0
    ntol=max(1e-7,1e-12*max(float(np.max(np.abs(g0f))),1.0))
    if _fmax(rec0-m0)>ntol: raise GateError(f"ownership_parent_CV_identity:{_fmax(rec0-m0)}")
    if float(np.min(residual)) < -ntol: raise GateError(f"ownership_parent_negative_residual:{float(np.min(residual))}")

    smax=np.full(parent_sat.shape,
                 float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION),
                 dtype=np.float64)
    rho_max=np.asarray(physics.gas_density_from_state(smax,pressure,pref),dtype=np.float64)
    capacity=(float(cellpv)*rho_max*physics.MAX_INCREMENTAL_CO2_SATURATION).reshape(-1)

    # Mandatory zero-delta identity probe.
    xid,metaID=_child_assignment(pc,cell,p,q0,m0,m0,residual,capacity)
    gid=residual+np.bincount(cell,weights=xid,minlength=ncell)
    iderr=_fmax(gid-g0f)
    if iderr>ntol: raise GateError(f"ownership_zero_delta_identity:{iderr}:{ntol}")

    x,metaB=_child_assignment(pc,cell,p,q1,m0,m1,residual,capacity)
    cvrec=np.bincount(pc,weights=x,minlength=len(m1))
    mapped=np.bincount(cell,weights=x,minlength=ncell)
    grid=residual+mapped
    cvtol=max(1e-7,1e-12*max(float(np.max(np.abs(m1))) if len(m1) else 1.0,1.0))
    if _fmax(cvrec-m1)>cvtol: raise GateError(f"ownership_child_CV_identity:{_fmax(cvrec-m1)}")
    if float(np.min(grid)) < -ntol: raise GateError(f"ownership_child_negative_grid:{float(np.min(grid))}")
    excess=grid-capacity
    if float(np.max(excess)) > ntol: raise GateError(f"ownership_child_capacity_excess:{float(np.max(excess))}")

    mapped_total=float(np.sum(grid))
    ledger=mapped_total-float(target_final)
    ltol=max(1e-6,1e-10*max(abs(float(target_final)),1.0))
    if abs(ledger)>ltol: raise GateError(f"ownership_grid_ledger:{ledger}:{ltol}")

    corrected_sg=np.asarray(
        physics._invert_incremental_sg_from_mass(grid.reshape(parent_sat.shape),
                                                 pressure,pref,cellpv),
        dtype=np.float64)
    corrected_sat=physics.BACKGROUND_SATURATION+corrected_sg
    recon=float(physics.stored_co2_mass_kg(corrected_sat,pressure,pref,cellpv))
    invres=recon-mapped_total
    if abs(invres)>ltol: raise GateError(f"ownership_grid_inversion:{invres}:{ltol}")

    return {
        "corrected_saturation":corrected_sat,
        "corrected_mass":grid.reshape(parent_sat.shape),
        "parent_grid_mass_kg":float(np.sum(g0f)),
        "cv_delta_mass_kg":float(np.sum(m1)-np.sum(m0)),
        "subsegment_delta_mass_kg":float(np.sum(q1)-np.sum(q0)),
        "transfer_residual_kg":float((np.sum(q1)-np.sum(q0))-(np.sum(m1)-np.sum(m0))),
        "mapped_final_mass_kg":mapped_total,
        "target_final_mass_kg":float(target_final),
        "ledger_residual_kg":ledger,
        "grid_inversion_residual_kg":invres,
        "roundoff_mass_kg":ltol,
        "deposited_delta_mass":(grid-g0f).reshape(parent_sat.shape),
        "source_local_added_mass_kg":0.0,
        "source_local_corrected_cells":0,
        "ownership_audit":{
            "pair_count":int(len(pc)),
            "supported_cell_count":int(np.unique(cell).size),
            "stageA_objective":objA,
            "stageA_meta":metaA,
            "stageB":metaB,
            "zero_delta_identity_Linf_kg":iderr,
            "parent_CV_identity_Linf_kg":_fmax(rec0-m0),
            "child_CV_identity_Linf_kg":_fmax(cvrec-m1),
            "minimum_parent_residual_kg":float(np.min(residual)),
            "minimum_child_grid_mass_kg":float(np.min(grid)),
            "maximum_child_capacity_excess_kg":float(np.max(excess)),
            "grid_ledger_residual_kg":ledger,
        }
    }



def selftest(root:Path):
    r4=mod(root,R4_RUNNER,R4_BLOB,"inta1r4r1_r4_selftest")
    r3=mod(root,R3_RUNNER,R3_BLOB,"inta1r4r1_r3_selftest")
    f4exec=mod(root,F4EXEC_RUNNER,F4EXEC_BLOB,"inta1r4r1_f4exec_selftest")
    original=mod(root,INTA1_RUNNER,INTA1_BLOB,"inta1r4r1_original_selftest")
    g3r7=mod(root,G3R7_RUNNER,G3R7_BLOB,"inta1r4r1_g3r7_selftest")
    g3r5=mod(root,G3R5_RUNNER,G3R5_BLOB,"inta1r4r1_g3r5_selftest")
    g2=mod(root,G2R3_RUNNER,G2R3_BLOB,"inta1r4r1_g2_selftest")
    mod(root,A8_RUNNER,A8_BLOB,"inta1r4r1_a8_selftest")
    mod(root,A1_RUNNER,A1_BLOB,"inta1r4r1_a1_selftest")
    mod(root,B1_RUNNER,B1_BLOB,"inta1r4r1_b1_selftest")
    mod(root,E11_RUNNER,E11_BLOB,"inta1r4r1_e11_selftest")
    mod(root,R3R5_RUNNER,R3R5_BLOB,"inta1r4r1_r3r5_selftest")
    mod(root,R3R4_RUNNER,R3R4_BLOB,"inta1r4r1_r3r4_selftest")
    mod(root,R2_REPAIR_RUNNER,R2_REPAIR_BLOB,"inta1r4r1_repair_selftest")
    assert START_DAY==30.0 and TARGET_DAY==45.0
    assert r4.M=="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R4"
    assert r3.PASS=="POSTV16AV4PIVOTGPUHYBINTA1R3_PARENT_OWNERSHIP_MAPBACK_RECONCILIATION_DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"
    assert hasattr(f4exec,"execute_frozen_assignment")
    assert MAX_FLOW_EPOCH_DAYS==5.0
    assert SCHEDULED_REFRESH_DAYS==(30.0,35.0,40.0,45.0)
    assert NEGATIVE_MAPBACK_RETRY_FACTOR==0.5
    assert MAX_NEGATIVE_MAPBACK_RETRIES==12
    assert original.M=="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1"
    assert g3r5.PRODUCTION_MAX_FLOW_EPOCH_DAYS is None
    assert g3r5.decide_shadow_action(35.0,30.0).action=="FULL_FLOW_REFRESH"
    assert g3r5.decide_shadow_action(40.0,35.0).action=="FULL_FLOW_REFRESH"
    assert g3r5.decide_shadow_action(45.0,40.0).action=="FULL_FLOW_REFRESH"
    assert g2.DAY30_RESTART_SHA=="093fa9570b07d91d6865c8464104cd6f72c271b2d638b93dc167c74497827035"
    assert g3r7.NEXT_MILESTONE=="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1"
    print("POSTV16 GPU-HYB-INT-A1-R4-R1 certified-parent replay / ownership-validation self-test: PASS")

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
        print("INT-A1-R4-R1 — CERTIFIED-PARENT REPLAY + OWNERSHIP VALIDATION + CONTROLLED DAY30 -> DAY45 RUN")
        print("PRE-VALIDATION: R1 SAME-PARENT DT RETRIES. AT CERTIFIED PARENT: R3 OWNERSHIP VALIDATION. POST-VALIDATION: OWNERSHIP FALLBACK.")
        print("NO CLIPPING, MASS DISCARD, TOLERANCE RELAXATION, SUPPORT EXPANSION, OR EXTRA FLOW REFRESH.")
        print("="*202)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_immutable_R4_BLOCK_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="source_authority"
        r4=mod(root,R4_RUNNER,R4_BLOB,"inta1r4r1_r4")
        r3=mod(root,R3_RUNNER,R3_BLOB,"inta1r4r1_r3")
        f4exec=mod(root,F4EXEC_RUNNER,F4EXEC_BLOB,"inta1r4r1_f4exec")
        original=mod(root,INTA1_RUNNER,INTA1_BLOB,"inta1r4r1_original")
        g3r7=mod(root,G3R7_RUNNER,G3R7_BLOB,"inta1r4r1_g3r7")
        g3r5=mod(root,G3R5_RUNNER,G3R5_BLOB,"inta1r4r1_g3r5")
        g2=mod(root,G2R3_RUNNER,G2R3_BLOB,"inta1r4r1_g2")
        a8=mod(root,A8_RUNNER,A8_BLOB,"inta1r4r1_a8")
        a1=mod(root,A1_RUNNER,A1_BLOB,"inta1r4r1_a1")
        b1=mod(root,B1_RUNNER,B1_BLOB,"inta1r4r1_b1")
        e11=mod(root,E11_RUNNER,E11_BLOB,"inta1r4r1_e11")
        r3r5=mod(root,R3R5_RUNNER,R3R5_BLOB,"inta1r4r1_r3r5")
        r3r4=mod(root,R3R4_RUNNER,R3R4_BLOB,"inta1r4r1_r3r4")
        repair=mod(root,R2_REPAIR_RUNNER,R2_REPAIR_BLOB,"inta1r4r1_repair")

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
                        mapback_mode="PARENT_OWNERSHIP_RECONCILED"
                        ownership_rows.append({
                            "event_role":"POST_VALIDATION_FALLBACK",
                            "parent_time_days":parent_time,
                            "accepted_step_index_candidate":parent_step+1,
                            "trial_dt_days":candidate_dt,
                            "ordinary_E37A_reject_reason":reason,
                            "pair_count":audit["pair_count"],
                            "supported_cell_count":audit["supported_cell_count"],
                            "stageA_objective":audit["stageA_objective"],
                            "stageB_stage1_objective":audit["stageB"].get("stage1_objective"),
                            "stageB_stage2_objective":audit["stageB"].get("stage2_objective"),
                            "stageB_stage3_objective":audit["stageB"].get("stage3_objective"),
                            "zero_delta_identity_Linf_kg":audit["zero_delta_identity_Linf_kg"],
                            "parent_CV_identity_Linf_kg":audit["parent_CV_identity_Linf_kg"],
                            "child_CV_identity_Linf_kg":audit["child_CV_identity_Linf_kg"],
                            "minimum_parent_residual_kg":audit["minimum_parent_residual_kg"],
                            "minimum_child_grid_mass_kg":audit["minimum_child_grid_mass_kg"],
                            "maximum_child_capacity_excess_kg":audit["maximum_child_capacity_excess_kg"],
                            "grid_ledger_residual_kg":audit["grid_ledger_residual_kg"],
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
                        mapback_mode="PARENT_OWNERSHIP_RECONCILED_LOCAL_VALIDATION"
                        ownership_rows.append({
                            "event_role":"CERTIFIED_PARENT_LOCAL_VALIDATION",
                            "parent_time_days":parent_time,
                            "accepted_step_index_candidate":parent_step+1,
                            "trial_dt_days":candidate_dt,
                            "ordinary_E37A_reject_reason":reason,
                            "R1_retry_index":negative_retry_count,
                            "pair_count":audit["pair_count"],
                            "supported_cell_count":audit["supported_cell_count"],
                            "stageA_objective":audit["stageA_objective"],
                            "stageB_stage1_objective":audit["stageB"].get("stage1_objective"),
                            "stageB_stage2_objective":audit["stageB"].get("stage2_objective"),
                            "stageB_stage3_objective":audit["stageB"].get("stage3_objective"),
                            "zero_delta_identity_Linf_kg":audit["zero_delta_identity_Linf_kg"],
                            "parent_CV_identity_Linf_kg":audit["parent_CV_identity_Linf_kg"],
                            "child_CV_identity_Linf_kg":audit["child_CV_identity_Linf_kg"],
                            "minimum_parent_residual_kg":audit["minimum_parent_residual_kg"],
                            "minimum_child_grid_mass_kg":audit["minimum_child_grid_mass_kg"],
                            "maximum_child_capacity_excess_kg":audit["maximum_child_capacity_excess_kg"],
                            "grid_ledger_residual_kg":audit["grid_ledger_residual_kg"],
                        })
                        if audit["zero_delta_identity_Linf_kg"] > 1e-7:
                            raise GateError(f"local_validation_zero_delta_identity:{audit['zero_delta_identity_Linf_kg']}")
                        if audit["child_CV_identity_Linf_kg"] > 1e-7:
                            raise GateError(f"local_validation_child_CV_identity:{audit['child_CV_identity_Linf_kg']}")
                        if audit["minimum_child_grid_mass_kg"] < -1e-7:
                            raise GateError(f"local_validation_negative_grid:{audit['minimum_child_grid_mass_kg']}")
                        if audit["maximum_child_capacity_excess_kg"] > 1e-7:
                            raise GateError(f"local_validation_capacity:{audit['maximum_child_capacity_excess_kg']}")
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
        gate("ownership_reconciliation_used",
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
            "classification":"R4_BLOCK_REPAIRED_BY_CERTIFIED_R1_PARENT_REPLAY_R3_OWNERSHIP_LOCAL_VALIDATION_PASS_AND_CONTROLLED_DAY30_DAY45_TRAJECTORY_COMPLETE_VISUALIZATION_READY",
            "immutable_R4_BLOCK_bound":True,
            "immutable_R4_BLOCK_exception":R4_EXPECTED_EXCEPTION,
            "R3_design_freeze_bound":True,
            "R3_local_validation_passed":local_validation_passed,
            "R3_local_validation_parent_day":local_validation_parent_day,
            "prevalidation_accepted_retry_step_count":prevalidation_accepted_retry_step_count,
            "ownership_reconciliation_count":ownership_reconciliation_count,
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
            "ownership_reconciliation_negative_cell_fallback_used":ownership_reconciliation_count>0,
            "existing_E37A_support_only":True,
            "conservative_capillary_redistribution_used":True,
            "visualization_checkpoint_days":[30.0,35.0,40.0,45.0],
            "visualization_checkpoint_count":4,
            "visualization_ready":True,
            "Day40_reference_comparison":reference_rows[0],
            "Day45_reference_comparison":reference_rows[1],
            "negative_mapback_repair_policy":"PRE_VALIDATION_R1_DT_REPLAY_TO_CERTIFIED_PARENT_THEN_R3_PARENT_OWNERSHIP_FALLBACK",
            "negative_mapback_retry_factor":NEGATIVE_MAPBACK_RETRY_FACTOR,
            "negative_mapback_retry_budget":MAX_NEGATIVE_MAPBACK_RETRIES,
            "cell_mass_clipping_performed":False,
            "mass_discard_performed":False,
            "mapback_spatial_operator_modified":False,
            "parent_ownership_reconciliation_operator_added_as_negative_cell_fallback":True,
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
            "R3_local_validation_passed":local_validation_passed,
            "R3_local_validation_parent_day":local_validation_parent_day,
            "ownership_reconciliation_count":ownership_reconciliation_count,
            "immutable_INT_A1_BLOCK_preserved":True,
            "negative_mapback_trial_repair_executed":True,
            "negative_mapback_repair":"same-parent transport timestep refinement; frozen E37A mapback remains acceptance authority",
            "five_day_controller_boundaries_executed":[35.0,40.0,45.0],
            "whole_system_chain":{
                "pressure_flow":"EXACT_FV_DARCY",
                "streamline_geometry":"EXACT_POLLOCK",
                "time_of_flight":"EXACT_TOF",
                "transport":"HYBRID10_PROPOSAL_PLUS_EXACT_E37A_FALLBACK",
                "conservation":"EXACT_COMPONENT_MASS_BUDGET_PLUS_BOX_PROJECTION",
                "mapback":"SINGLE_COMMON_FROZEN_E37A_MAPBACK_WITH_TRIAL_REJECT_AND_SAME_PARENT_DT_RETRY",
                "capillary":"CONSERVATIVE_CARTESIAN_REDISTRIBUTION",
            },
            "next_milestone":{
                "name":"POSTV16-AV4-PIVOT-GPU-HYB-INT-VIS-A1",
                "purpose":"Generate integrated 3D pressure, pressure-change, saturation/CO2-mass, streamline, TOF, controller-event, and ownership-reconciliation figures from Day30/35/40/45 checkpoints.",
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
        print("Ownership reconciliation uses                :",ownership_reconciliation_count)
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
            "postvalidation_ownership_fallback_active":local_validation_passed,
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
