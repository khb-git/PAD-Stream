#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import Any

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")


MILESTONE = "POSTV16-AV1-D-R7"
STATUS_PASS = (
    "AV1DR7_FULL_END_TO_END_PAD_STREAM_INTEGRATION_PASS_"
    "ACCEPTED_TRANSPORT_RUNTIME_CONSERVATIVELY_BOUND_TO_FOUNDATION_CASE_0001"
)
STATUS_BLOCKED = "AV1DR7_FULL_END_TO_END_INTEGRATION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R6_COMMIT = "18d36dc1e8650de058a1cd09e3046e3036283324"

R6 = "PAD_Stream_POSTV16_AV1_D_R6_Accepted_PIRNN_Deployment_Promotion_and_Canonical_Runtime_Binding.py"
R6_BLOB = "1ca67ca946683eeb31fbba7d31fba2613d5c0f6f"
R8R = "PAD_Stream_V16AR8R_Repaired_Foundation_Case_0001_Final_Assembly_Freeze.py"
R8R_BLOB = "00576330d14efd41ceeb81e2f38b14ba1ef01525"
SG6 = "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py"
SG6_BLOB = "70ceda68e02894167958d753d88b4dbd694731ab"
B2 = "PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py"
B2_BLOB = "95025d1e67a74f9dacaad311e5a402b63e7b4335"
B7 = "PAD_Stream_V16B7_Controlled_Directional_Advective_Travel_Time_Solve.py"
B7_BLOB = "9c860bf05fcf16616b447cd56d0e62065b2174a0"
C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"
C26 = "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"
B1 = "PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB = "8d9561d7c85805b82dedc26073c4633f90eeeab6"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

SOURCE_BLOBS = {
    R6: R6_BLOB,
    R8R: R8R_BLOB,
    SG6: SG6_BLOB,
    B2: B2_BLOB,
    B7: B7_BLOB,
    C2: C2_BLOB,
    C26: C26_BLOB,
    B1: B1_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    SG7D: SG7D_BLOB,
}

FOUNDATION_MANIFEST_REL = (
    Path("output")/"V16_A_R8R_FOUNDATION_CASE_0001_FREEZE"
    /"PAD_Stream_V16A_Foundation_Case_0001"
    /"V16A_Foundation_Case_0001_Manifest.json"
)
FOUNDATION_MANIFEST_BLOB = "4a899e7e21108d1c8b563881505f655d09adb7e0"
FOUNDATION_NAME = "V16A_Foundation_Case_0001.npz"
FOUNDATION_SHA = "4239e412ca6e2780f108c8eb1b0252e80a56be305bce48cc58e50d6140b86acc"

BASE = Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
R6_REL = BASE/"POSTV16_AV1_D_R6_Accepted_PIRNN_Deployment_Promotion_and_Canonical_Runtime_Binding"
R6_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R6_Summary.json"
R6_SCHEMA = "POSTV16_AV1_D_R6_Canonical_Transport_Runtime_Schema.json"
R6_REGISTRY = "POSTV16_AV1_D_R6_Canonical_Deployment_Registry.json"
R6_MANIFEST = "POSTV16_AV1_D_R6_Artifact_Manifest.csv"
R6_WEIGHTS = "POSTV16_AV1_D_R6_ACCEPTED_TRANSPORT_FROZEN.weights.h5"
R6_NORM = "POSTV16_AV1_D_R6_C3_Conditioning_Normalization_Parameters.npz"

R6_STATUS = (
    "AV1DR6_ACCEPTED_PIRNN_DEPLOYMENT_PROMOTED_"
    "CANONICAL_PAD_STREAM_RUNTIME_BOUND_NO_MODEL_CHANGE"
)
SELECTED_ID = "R5B_PRODUCER_BALANCED_RESPONSE"
WEIGHTS_SHA = "46fa4e4dc9fa3dc9f00aaa0d0270010c7dd2a2048f43f247be691c027497c709"
NORM_SHA = "870c7360aff526c6ad0af31562270c139c61c69177a59290518f45b0d907efd3"

OUT_REL = BASE/"POSTV16_AV1_D_R7_Full_End_to_End_PAD_Stream_Integration"
BLOCKED_REL = BASE/"POSTV16_AV1_D_R7_BLOCKED"

DAYS = np.array([30.,60.,100.,150.,250.,365.,500.,750.,1000.], dtype=np.float64)
GRID = (15,50,50)
NSL = 1078
NN = 201
NCV = 200
NT = 9
NSAMP = NSL*NT
DX = 6.096
DY = 6.096
DZ = 1.2192
BACKGROUND = 0.20


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()


def git_text(root: Path,*args:str)->str:
    p=subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE
    )
    return p.stdout.strip()


def git_blob_sha(path: Path,root: Path)->str:
    return git_text(root,"hash-object",str(path))


def load_json(path: Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path)->list[dict[str,str]]:
    with path.open("r",newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_manifest(directory: Path,name: str)->dict[str,str]:
    rows=read_csv(directory/name)
    m={r["file"]:r["sha256"] for r in rows}
    for fn,e in m.items():
        p=directory/fn
        if not p.is_file():
            raise GateError(f"manifest_missing:{fn}")
        a=sha256_file(p)
        if a!=e:
            raise GateError(f"manifest_SHA:{fn}:{a}:{e}")
    return m


def json_bytes(x:Any)->bytes:
    return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()


def csv_bytes(rows:list[dict[str,Any]])->bytes:
    if not rows:
        return b""
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n")
    w.writeheader();w.writerows(rows)
    return s.getvalue().encode()


def deterministic_npz_bytes(arrays:dict[str,Any])->bytes:
    outer=io.BytesIO()
    with zipfile.ZipFile(outer,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for key in sorted(arrays):
            b=io.BytesIO()
            np.save(b,np.asarray(arrays[key]),allow_pickle=False)
            info=zipfile.ZipInfo(f"{key}.npy",date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o600<<16
            zf.writestr(info,b.getvalue())
    return outer.getvalue()


def immutable_publish(out:Path,files:dict[str,bytes])->None:
    out.mkdir(parents=True,exist_ok=True)
    for n,d in files.items():
        p=out/n
        if p.exists() and p.read_bytes()!=d:
            raise GateError(f"existing_output_differs:{n}")
        if not p.exists():
            p.write_bytes(d)


def find_named_exact(roots:list[Path],name:str,expected_sha:str)->Path:
    hits=[]
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob(name):
            try:
                if p.is_file() and sha256_file(p)==expected_sha:
                    hits.append(p.resolve())
            except OSError:
                pass
    if not hits:
        raise GateError(f"exact_authority_not_found:{name}:{expected_sha}")
    return sorted(set(hits),key=lambda p:(len(str(p)),str(p)))[0]


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m


def face_to_cell(vx,vy,vz):
    nz,ny,nxm1=vx.shape
    nx=nxm1+1
    x=np.empty((nz,ny,nx));y=np.empty_like(x);z=np.empty_like(x)
    x[:,:,0]=vx[:,:,0];x[:,:,-1]=vx[:,:,-1];x[:,:,1:-1]=.5*(vx[:,:,:-1]+vx[:,:,1:])
    y[:,0,:]=vy[:,0,:];y[:,-1,:]=vy[:,-1,:];y[:,1:-1,:]=.5*(vy[:,:-1,:]+vy[:,1:,:])
    z[0]=vz[0];z[-1]=vz[-1];z[1:-1]=.5*(vz[:-1]+vz[1:])
    return x,y,z


def solve_adv(cx,cy,cz,source_mask,dx,dy,dz):
    aW=np.maximum(cx,0)/dx;aE=np.maximum(-cx,0)/dx
    aS=np.maximum(cy,0)/dy;aN=np.maximum(-cy,0)/dy
    aB=np.maximum(cz,0)/dz;aT=np.maximum(-cz,0)/dz
    aW[:,:,0]=0;aE[:,:,-1]=0;aS[:,0,:]=0;aN[:,-1,:]=0;aB[0]=0;aT[-1]=0
    aP=aW+aE+aS+aN+aB+aT
    nz,ny,nx=aP.shape;n=nz*ny*nx
    def flat(k,j,i):return (k*ny+j)*nx+i
    rows=[];cols=[];vals=[];rhs=np.ones(n,float)
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                r=flat(k,j,i)
                if source_mask[k,j,i]:
                    rows.append(r);cols.append(r);vals.append(1.);rhs[r]=0.;continue
                diag=aP[k,j,i]
                if not np.isfinite(diag) or diag<=0:
                    raise GateError(f"invalid_ADV_diagonal:{(k,j,i)}:{diag}")
                rows.append(r);cols.append(r);vals.append(diag)
                if i>0 and aW[k,j,i]>0:rows.append(r);cols.append(flat(k,j,i-1));vals.append(-aW[k,j,i])
                if i<nx-1 and aE[k,j,i]>0:rows.append(r);cols.append(flat(k,j,i+1));vals.append(-aE[k,j,i])
                if j>0 and aS[k,j,i]>0:rows.append(r);cols.append(flat(k,j-1,i));vals.append(-aS[k,j,i])
                if j<ny-1 and aN[k,j,i]>0:rows.append(r);cols.append(flat(k,j+1,i));vals.append(-aN[k,j,i])
                if k>0 and aB[k,j,i]>0:rows.append(r);cols.append(flat(k-1,j,i));vals.append(-aB[k,j,i])
                if k<nz-1 and aT[k,j,i]>0:rows.append(r);cols.append(flat(k+1,j,i));vals.append(-aT[k,j,i])
    A=sparse.csr_matrix((vals,(rows,cols)),shape=(n,n))
    tf=spsolve(A,rhs)
    tau=tf.reshape(GRID)
    res=A@tf-rhs
    return tau,{
        "relative_L2_residual":float(np.linalg.norm(res)/max(np.linalg.norm(rhs),1e-300)),
        "max_abs_residual":float(np.max(np.abs(res))),
        "source_max_abs_s":float(np.max(np.abs(tau[source_mask]))),
        "finite":bool(np.isfinite(tau).all()),
        "nonnegative":bool(np.all(tau>=-1e-10)),
        "non_source_positive":bool(np.all(tau[~source_mask]>0)),
    }


def self_test():
    xi=np.linspace(0.,1.,201)
    if xi.shape!=(201,) or xi[0]!=0. or xi[-1]!=1.:
        raise RuntimeError("xi")
    if DAYS.tolist()!=[30.,60.,100.,150.,250.,365.,500.,750.,1000.]:
        raise RuntimeError("days")
    print("POSTV16-AV1-D-R7 self-test: PASS")


def main(root:Path,drive:Path)->int:
    import tensorflow as tf

    gates={}
    stage="preflight"
    out=drive/OUT_REL
    blocked=drive/BLOCKED_REL

    def gate(n,p,v=None):
        ok=bool(p);gates[n]={"passed":ok,"value":v}
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f" — {v}" if v is not None else ""))
        if not ok:
            raise GateError(n)

    print("="*182)
    print("POSTV16-AV1-D-R7 — FULL END-TO-END PAD-STREAM INTEGRATION")
    print("="*182)
    print("FIXTURE: FROZEN FOUNDATION CASE 0001. THIS IS AN INTEGRATION TEST, NOT A NEW ACCURACY TEST.")
    print("FLOW/POLLOCK STATE -> ADV/CONDITIONING -> ACCEPTED R6 C26 TRANSPORT -> B1 201->200 MASS BRIDGE -> E37A 3-D GRID MAPBACK.")
    print("NO TRAINING. NO ACCEPTANCE-TRUTH OPENING. NO GEOLOGY0031 INPUT. NO MODEL MODIFICATION.\n")

    try:
        root=root.resolve();drive=drive.resolve()

        head=git_text(root,"rev-parse","HEAD")
        parent=git_text(root,"rev-parse","HEAD^")
        stat=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R6_commit",parent==PARENT_R6_COMMIT,parent)
        gate("repository_clean",stat=="",repr(stat))

        for fn,b in SOURCE_BLOBS.items():
            p=root/fn
            a=git_blob_sha(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",a==b,a)

        fm=root/FOUNDATION_MANIFEST_REL
        fmb=git_blob_sha(fm,root) if fm.is_file() else "missing"
        gate("foundation_manifest_git_blob_exact",fmb==FOUNDATION_MANIFEST_BLOB,fmb)

        stage="R6_runtime_binding"
        r6=drive/R6_REL
        gate("R6_output_present",r6.is_dir(),str(r6))
        m6=verify_manifest(r6,R6_MANIFEST)
        gate("R6_manifest_SHA_closure",True,len(m6))
        s6=load_json(r6/R6_SUMMARY)
        schema=load_json(r6/R6_SCHEMA)
        reg=load_json(r6/R6_REGISTRY)
        gate("R6_status_exact",s6["status"]==R6_STATUS,s6["status"])
        gate("R6_candidate_exact",s6["accepted_candidate"]==SELECTED_ID)
        gate("R6_weights_SHA_exact",s6["accepted_weights_sha256"]==WEIGHTS_SHA)
        gate("R6_norm_SHA_exact",s6["C3_normalization_sha256"]==NORM_SHA)
        gate("R6_R7_authorized",s6["R7_end_to_end_integration_authorized"] is True)
        gate("R6_no_prior_inference",s6["model_inference_performed"] is False)
        gate("R6_schema_no_acceptance_input",schema["runtime_scope"]["geology0031_conditioning_is_runtime_input"] is False and schema["runtime_scope"]["geology0031_truth_is_runtime_input"] is False)
        gate("R6_registry_R7_authorized",reg["next"]["authorized"] is True)

        weights_path=r6/R6_WEIGHTS
        norm_path=r6/R6_NORM
        gate("R6_runtime_weights_SHA_exact",weights_path.is_file() and sha256_file(weights_path)==WEIGHTS_SHA)
        gate("R6_runtime_norm_SHA_exact",norm_path.is_file() and sha256_file(norm_path)==NORM_SHA)

        stage="foundation_case_binding"
        fmanifest=load_json(fm)
        gate("foundation_manifest_status_complete",fmanifest["status"]=="V16A_FOUNDATION_CASE_0001_FROZEN_COMPLETE",fmanifest["status"])
        gate("foundation_manifest_case0001",fmanifest["foundation_case"]=="0001")
        gate("foundation_manifest_NPZ_SHA_exact",fmanifest["foundation_npz_sha256"]==FOUNDATION_SHA,fmanifest["foundation_npz_sha256"])
        foundation=find_named_exact([root,drive],FOUNDATION_NAME,FOUNDATION_SHA)
        gate("foundation_NPZ_exact_SHA",sha256_file(foundation)==FOUNDATION_SHA,str(foundation))

        with np.load(foundation,allow_pickle=False) as z:
            required=["Kx","Ky","Kz","porosity","pressure","Qx","Qy","Qz","Vx","Vy","Vz","streamline_xyz","pollock_tof","streamline_weight"]
            gate("foundation_required_keys_present",set(required).issubset(set(z.files)),sorted(z.files))
            d={k:np.asarray(z[k]).copy() for k in required}

        shapes={
            "Kx":GRID,"Ky":GRID,"Kz":GRID,"porosity":GRID,"pressure":GRID,
            "Qx":(15,50,49),"Qy":(15,49,50),"Qz":(14,50,50),
            "Vx":(15,50,49),"Vy":(15,49,50),"Vz":(14,50,50),
            "streamline_xyz":(NSL,NN,3),"pollock_tof":(NSL,NN),"streamline_weight":(NSL,)
        }
        for k,sh in shapes.items():
            gate(f"foundation_{k}_shape_exact",d[k].shape==sh,d[k].shape)
            gate(f"foundation_{k}_finite",np.isfinite(d[k]).all())

        gate("foundation_weights_positive",np.all(d["streamline_weight"]>0))
        gate("foundation_porosity_constant_0p20",np.max(np.abs(d["porosity"]-.2))<=1e-12,float(np.max(np.abs(d["porosity"]-.2))))
        pressure=np.asarray(d["pressure"],float)
        gate("foundation_pressure_bound_as_psi",1000.<float(np.median(pressure))<4000.,float(np.median(pressure)))

        stage="ADV_and_runtime_conditioning"
        b2=load_module(root/B2,"r7_b2")
        c2=load_module(root/C2,"r7_c2")

        cx,cy,cz=face_to_cell(d["Vx"],d["Vy"],d["Vz"])
        _,_,_,source_mask,_=b2.bind_injector_sources(d["Qx"],d["Qy"],d["Qz"])
        source_mask=np.asarray(source_mask,bool)
        gate("ADV_five_source_cells",int(source_mask.sum())==5,int(source_mask.sum()))
        adv_grid,adv_audit=solve_adv(cx,cy,cz,source_mask,DX,DY,DZ)
        gate("ADV_finite",adv_audit["finite"])
        gate("ADV_nonnegative",adv_audit["nonnegative"])
        gate("ADV_positive_non_source",adv_audit["non_source_positive"])
        gate("ADV_source_zero",adv_audit["source_max_abs_s"]<1e-8,adv_audit["source_max_abs_s"])
        gate("ADV_PDE_residual_lt_1e8",adv_audit["relative_L2_residual"]<1e-8,adv_audit["relative_L2_residual"])

        xyz=np.asarray(d["streamline_xyz"],float)
        ptau=np.asarray(d["pollock_tof"],float)
        te=ptau[:,-1].copy()
        gate("pollock_terminal_TOF_positive",np.all(te>0),[float(np.min(te)),float(np.max(te))])
        xi=np.linspace(0.,1.,NN)
        pth=ptau/te[:,None]
        gate("pollock_hat_boundaries",np.max(np.abs(pth[:,0]))<=1e-12 and np.max(np.abs(pth[:,-1]-1.))<=1e-12)

        origin=np.array([0.,0.,0.],float)
        adv_s,_=c2.trilinear(adv_grid,xyz,DX,DY,DZ,origin)
        kx_s,_=c2.trilinear(d["Kx"],xyz,DX,DY,DZ,origin)
        ky_s,_=c2.trilinear(d["Ky"],xyz,DX,DY,DZ,origin)
        kz_s,_=c2.trilinear(d["Kz"],xyz,DX,DY,DZ,origin)
        phi_s,_=c2.trilinear(d["porosity"],xyz,DX,DY,DZ,origin)
        p_s,_=c2.trilinear(pressure,xyz,DX,DY,DZ,origin)

        with np.load(norm_path,allow_pickle=False) as z:
            pmean=float(np.asarray(z["pressure_mean_psi"]).reshape(-1)[0])
            pstd=float(np.asarray(z["pressure_std_psi"]).reshape(-1)[0])
            lwmean=float(np.asarray(z["ln_weight_mean"]).reshape(-1)[0])
            lwstd=float(np.asarray(z["ln_weight_std"]).reshape(-1)[0])

        Kh=np.sqrt(np.maximum(kx_s,1e-30)*np.maximum(ky_s,1e-30))
        X7=np.stack([
            np.broadcast_to(xi[None,:],(NSL,NN)),
            pth,
            adv_s/te[:,None],
            np.log10(np.maximum(Kh,1e-30)),
            np.log10(np.maximum(kz_s,1e-30)/np.maximum(Kh,1e-30)),
            phi_s,
            (p_s-pmean)/pstd,
        ],axis=-1).astype(np.float32)
        Xstatic=((np.log(np.maximum(d["streamline_weight"],1e-300))-lwmean)/lwstd)[:,None].astype(np.float32)

        gate("runtime_X7_shape_exact",X7.shape==(NSL,NN,7),X7.shape)
        gate("runtime_X7_finite",np.isfinite(X7).all())
        gate("runtime_static_sidecar_shape_exact",Xstatic.shape==(NSL,1),Xstatic.shape)
        gate("runtime_static_sidecar_finite",np.isfinite(Xstatic).all())

        X7f=np.broadcast_to(X7[None],(NT,NSL,NN,7)).reshape(NSAMP,NN,7).copy()
        td=np.repeat(DAYS,NSL)
        th=(td/1000.).astype(np.float32)
        eta=DAYS[:,None]*86400./te[None,:]
        es=np.repeat(eta[:,:,None],NN,axis=2).reshape(NSAMP,NN).astype(np.float32)
        T=np.broadcast_to(th[:,None,None],(NSAMP,NN,1)).astype(np.float32)
        X9=np.concatenate([X7f,T,es[:,:,None]],axis=2).astype(np.float32)
        gate("runtime_X9_shape_exact",X9.shape==(NSAMP,NN,9),X9.shape)
        gate("runtime_X9_finite",np.isfinite(X9).all())

        stage="accepted_transport_inference"
        c26=load_module(root/C26,"r7_c26")
        try:
            tf.config.experimental.enable_op_determinism()
        except Exception:
            pass
        tf.keras.utils.set_random_seed(16021)
        model=c26.model()
        gate("C26_parameter_count_52033",model.count_params()==52033,model.count_params())
        model.load_weights(weights_path)
        pred_flat=model.predict(X9,batch_size=64,verbose=0).astype(np.float64)
        gate("accepted_transport_prediction_shape_exact",pred_flat.shape==(NSAMP,NN),pred_flat.shape)
        gate("accepted_transport_prediction_finite",np.isfinite(pred_flat).all())
        gate("accepted_transport_saturation_bounds",float(np.min(pred_flat))>=.2-1e-12 and float(np.max(pred_flat))<=.8+1e-12,[float(np.min(pred_flat)),float(np.max(pred_flat))])
        pred201=pred_flat.reshape(NT,NSL,NN)

        stage="conservative_201_to_200_bridge"
        b1=load_module(root/B1,"r7_b1")
        r2=load_module(root/R2,"r7_r2")
        e37a=load_module(root/E37A,"r7_e37a")

        with tempfile.TemporaryDirectory(prefix="POSTV16_R7_SG7D_") as tdtmp:
            tdtmp=Path(tdtmp)
            sg7d_copy=tdtmp/SG7D
            sg7d_copy.write_bytes((root/SG7D).read_bytes())
            sg7d=load_module(sg7d_copy,"r7_sg7d")

            operator=sg7d.build_subsegment_operator(
                xyz,
                ptau/float(e37a.DAY_TO_S),
                np.asarray(d["streamline_weight"],float)*float(e37a.DAY_TO_S),
            )

            injection_pc=float(r2.capillary_pressure_from_incremental_sg(float(r2.MAX_INCREMENTAL_CO2_SATURATION)))
            injector_pw_pa=np.array([
                pressure[k,int(r2.INJECTOR_J),int(r2.INJECTOR_I)]*float(r2.PSI_TO_PA)
                for k in r2.COMPLETION_K
            ],dtype=np.float64)
            p_ref=float(np.mean(injector_pw_pa)+injection_pc)
            gate("reference_gas_pressure_finite",np.isfinite(p_ref),p_ref)

            geometry=e37a.build_control_volume_geometry(
                r2,operator,pressure,p_ref,NSL,NCV
            )
            coeff=np.asarray(geometry["cv_pressure_mass_coeff"],float)
            gate("E37A_coeff_shape_exact",coeff.shape==(NSL,NCV),coeff.shape)
            gate("E37A_coeff_positive_finite",np.isfinite(coeff).all() and np.all(coeff>0))

            ids=np.tile(np.arange(NSL,dtype=np.int64),NT)
            pred200_flat,pred_mass_flat,pred_source_mass_flat=b1.project_201_to_200_component_mass(
                r2,e37a,pred201.reshape(-1,NN),coeff,ids
            )
            pred200=pred200_flat.reshape(NT,NSL,NCV)
            pred_mass=pred_mass_flat.reshape(NT,NSL,NCV)
            pred_source_mass=pred_source_mass_flat.reshape(NT,NSL,NN)

            den=np.maximum(np.abs(np.sum(pred_mass,axis=(1,2))),1.0)
            srcsum=np.sum(pred_source_mass,axis=(1,2))
            cvsum=np.sum(pred_mass,axis=(1,2))
            closure=np.max(np.abs(cvsum-srcsum)/den)
            gate("B1_mass_projection_closure",float(closure)<=1e-12,float(closure))

            naive=.5*(pred201[:,:,:-1]+pred201[:,:,1:])
            nonlinear_gap=float(np.max(np.abs(pred200-naive)))
            gate("direct_saturation_averaging_not_used",nonlinear_gap>1e-12,nonlinear_gap)

            stage="E37A_grid_mapback"
            baseline_cv_sat=np.full((NSL,NCV),BACKGROUND,float)
            baseline_cv_mass=e37a.cv_mass_from_saturation(r2,baseline_cv_sat,coeff)
            gate("baseline_cv_mass_zero",float(np.max(np.abs(baseline_cv_mass)))<=1e-10,float(np.max(np.abs(baseline_cv_mass))))
            parent_grid=np.full(GRID,BACKGROUND,float)
            cell_pv=DX*DY*DZ*.2

            grid_sat=np.empty((NT,)+GRID,dtype=np.float64)
            grid_mass=np.empty((NT,)+GRID,dtype=np.float64)
            map_rows=[]
            for it,day in enumerate(DAYS):
                target_mass=float(np.sum(pred_mass[it]))
                mapped=e37a.map_control_volume_increment_to_grid(
                    r2,
                    parent_grid,
                    baseline_cv_sat,
                    pred200[it],
                    baseline_cv_mass,
                    pred_mass[it],
                    geometry,
                    pressure,
                    p_ref,
                    cell_pv,
                    target_mass,
                )
                grid_sat[it]=np.asarray(mapped["corrected_saturation"],float)
                grid_mass[it]=np.asarray(mapped["corrected_mass"],float)
                map_rows.append({
                    "target_day":float(day),
                    "streamline_component_mass_kg":target_mass,
                    "grid_component_mass_kg":float(np.sum(grid_mass[it])),
                    "transfer_residual_kg":float(mapped["transfer_residual_kg"]),
                    "ledger_residual_kg":float(mapped["ledger_residual_kg"]),
                    "grid_inversion_residual_kg":float(mapped["grid_inversion_residual_kg"]),
                    "grid_saturation_min":float(np.min(grid_sat[it])),
                    "grid_saturation_max":float(np.max(grid_sat[it])),
                })

        gate("grid_saturation_shape_exact",grid_sat.shape==(NT,15,50,50),grid_sat.shape)
        gate("grid_saturation_finite",np.isfinite(grid_sat).all())
        gate("grid_saturation_bounds",float(np.min(grid_sat))>=.2-1e-12 and float(np.max(grid_sat))<=.8+1e-12,[float(np.min(grid_sat)),float(np.max(grid_sat))])
        max_mass_rel=max(
            abs(r["grid_component_mass_kg"]-r["streamline_component_mass_kg"])
            / max(abs(r["streamline_component_mass_kg"]),1.0)
            for r in map_rows
        )
        gate("streamline_to_grid_mass_closure_all_times",max_mass_rel<=1e-10,max_mass_rel)

        stage="seal_integrated_runtime_state"
        state_name="POSTV16_AV1_D_R7_Foundation0001_Integrated_Runtime_State.npz"
        state_bytes=deterministic_npz_bytes({
            "target_days":DAYS,
            "streamline_saturation_201":pred201.astype(np.float32),
            "streamline_saturation_200":pred200.astype(np.float32),
            "streamline_component_mass_200_kg":pred_mass.astype(np.float64),
            "grid_saturation":grid_sat.astype(np.float32),
            "grid_component_mass_kg":grid_mass.astype(np.float64),
            "adv_travel_time_grid_s":adv_grid.astype(np.float64),
            "streamline_weight_m3_s":np.asarray(d["streamline_weight"],float),
            "pollock_tof_s":ptau.astype(np.float64),
            "foundation_case_sha256":np.array(FOUNDATION_SHA),
            "runtime_weights_sha256":np.array(WEIGHTS_SHA),
            "runtime_normalization_sha256":np.array(NORM_SHA),
        })
        immutable_publish(out,{state_name:state_bytes})
        state_sha=sha256_file(out/state_name)

        interface_rows=[
            {"stage":"foundation geology/storage","artifact":"V16A Foundation Case 0001","status":"PASS","detail":"Kx/Ky/Kz/porosity frozen and finite"},
            {"stage":"pressure/flow","artifact":"V16A Foundation Case 0001","status":"PASS","detail":"pressure/Qx/Qy/Qz frozen source-authentic state"},
            {"stage":"Pollock/TOF","artifact":"V16A Foundation Case 0001","status":"PASS","detail":"1078 x 201 XYZ/TOF and weights"},
            {"stage":"ADV conditioning","artifact":"R7 generated from frozen velocities","status":"PASS","detail":f"PDE relative residual {adv_audit['relative_L2_residual']:.3e}"},
            {"stage":"canonical C26 conditioning","artifact":"R6 schema + C3 normalization","status":"PASS","detail":"9702 x 201 x 9"},
            {"stage":"accepted PI-RNN transport","artifact":SELECTED_ID,"status":"PASS","detail":"9702 x 201 saturation predictions"},
            {"stage":"B1 representation bridge","artifact":"component-mass half-overlap","status":"PASS","detail":f"closure {closure:.3e}"},
            {"stage":"E37A grid mapback","artifact":"3-D conservative mapback","status":"PASS","detail":f"max relative mass closure {max_mass_rel:.3e}"},
        ]

        integration_contract={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "fixture":{
                "case":"FOUNDATION_CASE_0001",
                "foundation_sha256":FOUNDATION_SHA,
                "role":"FROZEN_INTEGRATION_FIXTURE_NOT_NEW_INDEPENDENT_ACCURACY_CASE",
            },
            "runtime":{
                "candidate_id":SELECTED_ID,
                "weights_sha256":WEIGHTS_SHA,
                "normalization_sha256":NORM_SHA,
                "target_days":DAYS.tolist(),
                "input_shape":[NSAMP,NN,9],
                "streamline_output_shape":[NT,NSL,NN],
                "control_volume_output_shape":[NT,NSL,NCV],
                "grid_output_shape":[NT,15,50,50],
            },
            "physics_to_ml_interfaces":{
                "geology_storage":"foundation Kx/Ky/Kz/porosity",
                "pressure_flow":"foundation pressure/Qx/Qy/Qz/Vx/Vy/Vz",
                "Pollock_TOF":"foundation streamline_xyz/pollock_tof/streamline_weight",
                "ADV":"exact D29/B7 directional semantics reconstructed from frozen velocity field",
                "sampling":"frozen C2 trilinear cell-centered",
                "conditioning":"frozen C3 + exact R6 channel schema",
                "transport":"accepted immutable C26 checkpoint",
                "representation_bridge":"B1 exact component-mass 201->200 half-overlap",
                "grid_mapback":"E37A subsegment-overlap conservative component-mass mapback",
            },
            "scientific_scope":{
                "training_performed":False,
                "accepted_weights_modified":False,
                "normalization_refit":False,
                "geology0031_used":False,
                "acceptance_truth_used":False,
                "new_accuracy_claim":False,
                "new_generalization_claim":False,
                "integration_claim_only":(
                    "The accepted post-V16 transport runtime is executable end-to-end "
                    "on frozen Foundation Case 0001 with closed interface dimensions, "
                    "physical saturation bounds, conservative 201->200 component-mass "
                    "transfer, and conservative 3-D grid mapback."
                ),
            },
            "next":{
                "milestone":"POSTV16-AV1-D-R8",
                "name":"Prospective Full-Field / Plume Fidelity Validation Protocol",
                "authorized":True,
                "rule":"Freeze spatial/plume accuracy gates before opening any new validation geology.",
            },
        }

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "repository_head":head,
            "repository_parent":parent,
            "foundation_case_sha256":FOUNDATION_SHA,
            "accepted_weights_sha256":WEIGHTS_SHA,
            "normalization_sha256":NORM_SHA,
            "integrated_state_sha256":state_sha,
            "target_days":DAYS.tolist(),
            "C26_input_shape":[NSAMP,NN,9],
            "streamline_saturation_201_shape":[NT,NSL,NN],
            "streamline_saturation_200_shape":[NT,NSL,NCV],
            "grid_saturation_shape":[NT,15,50,50],
            "prediction_min":float(np.min(pred201)),
            "prediction_max":float(np.max(pred201)),
            "grid_saturation_min":float(np.min(grid_sat)),
            "grid_saturation_max":float(np.max(grid_sat)),
            "B1_projection_max_relative_closure":float(closure),
            "grid_mapback_max_relative_mass_closure":float(max_mass_rel),
            "training_performed":False,
            "geology0031_used":False,
            "acceptance_truth_used":False,
            "new_accuracy_claim":False,
            "R8_spatial_validation_protocol_authorized":True,
        }

        immutable_publish(out,{
            "PAD_Stream_POSTV16_AV1_D_R7_Summary.json":json_bytes(summary),
            "POSTV16_AV1_D_R7_End_to_End_Integration_Contract.json":json_bytes(integration_contract),
            "POSTV16_AV1_D_R7_Interface_Audit.csv":csv_bytes(interface_rows),
            "POSTV16_AV1_D_R7_Grid_Mapback_Audit.csv":csv_bytes(map_rows),
            "POSTV16_AV1_D_R7_Final_Gate_Matrix.csv":csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
        })

        manifest=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="POSTV16_AV1_D_R7_Artifact_Manifest.csv":
                manifest.append({"file":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
        immutable_publish(out,{"POSTV16_AV1_D_R7_Artifact_Manifest.csv":csv_bytes(manifest)})

        print("\n"+"="*182)
        print("POSTV16-AV1-D-R7: PASS")
        print("="*182)
        print(f"{'Status':100}: {STATUS_PASS}")
        print(f"{'Integration fixture':100}: FOUNDATION_CASE_0001")
        print(f"{'Foundation SHA256':100}: {FOUNDATION_SHA}")
        print(f"{'Accepted runtime weights SHA256':100}: {WEIGHTS_SHA}")
        print(f"{'C26 input shape':100}: (9702, 201, 9)")
        print(f"{'201-node transport output':100}: (9, 1078, 201)")
        print(f"{'200-CV conservative output':100}: (9, 1078, 200)")
        print(f"{'3-D grid saturation output':100}: (9, 15, 50, 50)")
        print(f"{'Prediction saturation min / max':100}: {float(np.min(pred201)):.12e} / {float(np.max(pred201)):.12e}")
        print(f"{'Grid saturation min / max':100}: {float(np.min(grid_sat)):.12e} / {float(np.max(grid_sat)):.12e}")
        print(f"{'B1 201->200 mass closure max relative':100}: {float(closure):.12e}")
        print(f"{'E37A grid mapback mass closure max relative':100}: {float(max_mass_rel):.12e}")
        print(f"{'Geology0031 / acceptance truth used':100}: False / False")
        print(f"{'Training / model modification':100}: False / False")
        print(f"{'New accuracy/generalization claim':100}: False / False")
        print(f"{'Integrated state SHA256':100}: {state_sha}")
        print(f"{'R8 spatial validation protocol authorized':100}: True")
        print(f"{'NEXT':100}: POSTV16-AV1-D-R8 — prospective full-field/plume fidelity validation protocol")
        print("="*182)
        return 0

    except Exception as e:
        blocked.mkdir(parents=True,exist_ok=True)
        rep={
            "milestone":MILESTONE,
            "status":STATUS_BLOCKED,
            "failed_stage":stage,
            "exception":repr(e),
            "gates":gates,
            "training_performed":False,
            "accepted_weights_modified":False,
            "normalization_refit":False,
            "geology0031_used":False,
            "acceptance_truth_used":False,
            "new_accuracy_claim":False,
            "next_action":(
                "Audit only the failed R7 integration/interface/conservation gate. "
                "Do not retrain or modify the accepted checkpoint, do not use geology0031, "
                "and do not create spatial accuracy claims until R8 is prospectively frozen."
            ),
        }
        data=json_bytes(rep)
        p=blocked/"POSTV16_AV1_D_R7_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:
            p=blocked/f"POSTV16_AV1_D_R7_Blocked_Report_{hashlib.sha256(data).hexdigest()[:12]}.json"
        if not p.exists():
            p.write_bytes(data)
        print("\n"+"="*182)
        print("POSTV16-AV1-D-R7: BLOCKED")
        print("="*182)
        print("Failed stage:",stage)
        print("Exception   :",repr(e))
        print("Report      :",p)
        return 2


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()


if __name__=="__main__":
    a=parse_args()
    if a.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
