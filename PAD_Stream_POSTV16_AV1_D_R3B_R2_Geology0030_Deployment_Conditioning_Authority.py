#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, zipfile
from pathlib import Path
from typing import Any

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

MILESTONE = "POSTV16-AV1-D-R3B-R2"
STATUS_PASS = (
    "AV1DR3BR2_GEOLOGY0030_C26_DEPLOYMENT_CONDITIONING_"
    "AUTHORITY_GENERATED_CERTIFIED_AND_SHA_SEALED"
)
STATUS_BLOCKED = "AV1DR3BR2_DEPLOYMENT_CONDITIONING_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R3B_COMMIT = "4854ff92f7122bc49a8ac3b8274b594802a438bb"

R3B_RUNNER = "PAD_Stream_POSTV16_AV1_D_R3B_Frozen_TrainValidation_Outlet_Response_Repair_Execution.py"
R3B_RUNNER_BLOB = "787fe69e6631a1d294c17e791ab82aa4ab963c10"
R3A_RUNNER = "PAD_Stream_POSTV16_AV1_D_R3A_Generate_and_Seal_Geology0030_Acceptance_Authority.py"
R3A_RUNNER_BLOB = "8a12228f488394e24fdf11479e335f245c800478"
D29_RUNNER = "PAD_Stream_V16D29_R1_Exact_D10C_Derived_FMM_ADV_36Case_ControlSpace_Execution.py"
D29_BLOB = "3377a8987e9078816d5826aef9d52a58465de527"
B2_RUNNER = "PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py"
B2_BLOB = "95025d1e67a74f9dacaad311e5a402b63e7b4335"
B7_RUNNER = "PAD_Stream_V16B7_Controlled_Directional_Advective_Travel_Time_Solve.py"
B7_BLOB = "9c860bf05fcf16616b447cd56d0e62065b2174a0"
SG5_RUNNER = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG5_BLOB = "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"
C2_RUNNER = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"

C2_CONTRACT = Path("output")/"V16_C2_MULTI_COORDINATE_STREAMLINE_TRANSPORT_DATABASE"/"V16C2_Multi_Coordinate_Transport_Database_Contract.json"
C2_CONTRACT_BLOB = "88bc5ad068f0f24e78230318c5eab69b80f3dfc2"
C3_CONTRACT = Path("output")/"V16_C3_PIRNN_TRANSPORT_CONDITIONING_CONTRACT"/"V16C3_PIRNN_Transport_Conditioning_Contract.json"
C3_CONTRACT_BLOB = "220ea7dcf59ef32cc850af065abca0b0c699029e"

SOURCE_BLOBS = {
    R3B_RUNNER: R3B_RUNNER_BLOB,
    R3A_RUNNER: R3A_RUNNER_BLOB,
    D29_RUNNER: D29_BLOB,
    B2_RUNNER: B2_BLOB,
    B7_RUNNER: B7_BLOB,
    SG5_RUNNER: SG5_BLOB,
    C2_RUNNER: C2_BLOB,
}

C3_NAME = "V16C3_Conditioning_Normalization_Parameters.npz"
C3_SHA = "870c7360aff526c6ad0af31562270c139c61c69177a59290518f45b0d907efd3"

R3B_OUT_REL = Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"/"POSTV16_AV1_D_R3B_Frozen_TrainValidation_Repair_Execution"
R3B_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R3B_Summary.json"
R3B_SELECTED = "POSTV16_AV1_D_R3B_Selected_Checkpoint_Contract.json"
R3B_MANIFEST = "POSTV16_AV1_D_R3B_Artifact_Manifest.csv"
R3B_WEIGHTS = "POSTV16_AV1_D_R3B_SELECTED_FROZEN.weights.h5"
R3B_STATUS = (
    "AV1DR3B_THREE_CANDIDATE_TRAIN_VALIDATION_REPAIR_EXECUTED_"
    "SELECTED_CHECKPOINT_FROZEN_GEOLOGY0030_REMAINS_SEALED"
)
SELECTED_ID = "R3B_RESPONSE"
SELECTED_SHA = "8207f17f35c354a3396525ed3ba8de88c923f7b55351f7cc58a9000268a26364"

R3A_OUT_REL = Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"/"POSTV16_AV1_D_R3A_Geology0030_Sealed_Acceptance_Authority"
R3A_AUTHORITY = "POSTV16_AV1_D_R3A_Sealed_Acceptance_Authority.json"
R3A_MANIFEST = "POSTV16_AV1_D_R3A_Artifact_Manifest.csv"
FLOW_NAME = "POSTV16_AV1_D_R3A_Geology0030_R500_B2000_Flow.npz"
METRIC_NAME = "POSTV16_AV1_D_R3A_Geology0030_R500_B2000_201Node_C7_FaceMetric.npz"
SEALED_TARGET_NAME = "POSTV16_AV1_D_R3A_Geology0030_R500_B2000_SEALED_Stage4_Target.npz"
SEALED_TARGET_SHA = "bef8c3875ab30a561f1cb9f6d16c1816691394b13e2ddb6ea384d44d40f6109c"

OUT_REL = Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"/"POSTV16_AV1_D_R3B_R2_Geology0030_Deployment_Conditioning_Authority"
BLOCKED_REL = Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"/"POSTV16_AV1_D_R3B_R2_BLOCKED"

EXPECTED_GRID=(15,50,50)
EXPECTED_STREAMLINES=1078
EXPECTED_NODES=201
TARGET_DAYS=np.array([30.,60.,100.,150.,250.,365.,500.,750.,1000.])
CASE_ID="POSTV16_AV1_Geology0030_R500_B2000"


class GateError(RuntimeError):
    pass


def sha256_file(p: Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()


def git_text(root:Path,*args:str)->str:
    p=subprocess.run(["git","-C",str(root),*args],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return p.stdout.strip()


def git_blob_sha(path:Path,root:Path)->str:
    return git_text(root,"hash-object",str(path))


def load_json(p:Path)->dict[str,Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def read_csv(p:Path)->list[dict[str,str]]:
    with p.open("r",newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


def json_bytes(x:Any)->bytes:
    return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()


def csv_bytes(rows:list[dict[str,Any]])->bytes:
    if not rows:return b""
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields:fields.append(k)
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)
    return s.getvalue().encode()


def deterministic_npz_bytes(arrays:dict[str,Any])->bytes:
    outer=io.BytesIO()
    with zipfile.ZipFile(outer,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for key in sorted(arrays):
            b=io.BytesIO();np.save(b,np.asarray(arrays[key]),allow_pickle=False)
            info=zipfile.ZipInfo(f"{key}.npy",date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o600<<16
            zf.writestr(info,b.getvalue())
    return outer.getvalue()


def immutable_publish(out:Path,files:dict[str,bytes])->None:
    out.mkdir(parents=True,exist_ok=True)
    for n,d in files.items():
        p=out/n
        if p.exists():
            if p.read_bytes()!=d:raise GateError(f"existing_output_differs:{n}")
        else:p.write_bytes(d)


def verify_manifest(directory:Path,manifest_name:str)->dict[str,str]:
    rows=read_csv(directory/manifest_name)
    m={r["file"]:r["sha256"] for r in rows}
    for n,e in m.items():
        p=directory/n
        if not p.is_file():raise GateError(f"manifest_file_missing:{n}")
        a=sha256_file(p)
        if a!=e:raise GateError(f"manifest_SHA_mismatch:{n}:{a}:{e}")
    return m


def find_named_exact(roots:list[Path],name:str,expected_sha:str)->Path:
    hits=[]
    for root in roots:
        if not root.exists():continue
        for p in root.rglob(name):
            try:
                if p.is_file() and sha256_file(p)==expected_sha:hits.append(p)
            except OSError:pass
    if not hits:raise GateError(f"exact_authority_not_found:{name}:{expected_sha}")
    return sorted(set(hits),key=lambda p:(len(str(p)),str(p)))[0]


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:raise GateError(f"cannot_load_module:{path}")
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m


def face_to_cell(vx,vy,vz):
    nz,ny,nxm1=vx.shape;nx=nxm1+1
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
        if not np.isfinite(diag) or diag<=0:raise GateError(f"invalid_ADV_diagonal:{(k,j,i)}:{diag}")
        rows.append(r);cols.append(r);vals.append(diag)
        if i>0 and aW[k,j,i]>0:rows.append(r);cols.append(flat(k,j,i-1));vals.append(-aW[k,j,i])
        if i<nx-1 and aE[k,j,i]>0:rows.append(r);cols.append(flat(k,j,i+1));vals.append(-aE[k,j,i])
        if j>0 and aS[k,j,i]>0:rows.append(r);cols.append(flat(k,j-1,i));vals.append(-aS[k,j,i])
        if j<ny-1 and aN[k,j,i]>0:rows.append(r);cols.append(flat(k,j+1,i));vals.append(-aN[k,j,i])
        if k>0 and aB[k,j,i]>0:rows.append(r);cols.append(flat(k-1,j,i));vals.append(-aB[k,j,i])
        if k<nz-1 and aT[k,j,i]>0:rows.append(r);cols.append(flat(k+1,j,i));vals.append(-aT[k,j,i])
    A=sparse.csr_matrix((vals,(rows,cols)),shape=(n,n))
    tf=spsolve(A,rhs);tau=tf.reshape(EXPECTED_GRID);res=A@tf-rhs
    return tau,{
        "relative_L2_residual":float(np.linalg.norm(res)/max(np.linalg.norm(rhs),1e-300)),
        "max_abs_residual":float(np.max(np.abs(res))),
        "source_max_abs_s":float(np.max(np.abs(tau[source_mask]))),
        "finite":bool(np.isfinite(tau).all()),
        "nonnegative":bool(np.all(tau>=-1e-10)),
        "non_source_positive":bool(np.all(tau[~source_mask]>0)),
        "unknowns":int(n),"nnz":int(A.nnz),
    }


def self_test():
    if SELECTED_ID!="R3B_RESPONSE":raise RuntimeError("selected_id")
    if TARGET_DAYS.tolist()!=[30.,60.,100.,150.,250.,365.,500.,750.,1000.]:raise RuntimeError("days")
    print("POSTV16-AV1-D-R3B-R2 self-test: PASS")


def main(root:Path,drive:Path)->int:
    gates={}
    stage="preflight"
    out=drive/OUT_REL;blocked=drive/BLOCKED_REL
    def gate(n,p,v=None):
        ok=bool(p);gates[n]={"passed":ok,"value":v}
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f" — {v}" if v is not None else ""))
        if not ok:raise GateError(n)

    print("="*168)
    print("POSTV16-AV1-D-R3B-R2 — GEOLOGY0030 C26 DEPLOYMENT CONDITIONING AUTHORITY")
    print("="*168)
    print("NO MODEL INFERENCE. NO TARGET OPENING. NO TRAINING/RETUNING.")
    print("ADV: FROZEN D29/B7 SEMANTICS. SAMPLING: FROZEN C2. NORMALIZATION: FROZEN C3.\n")

    try:
        root=root.resolve();drive=drive.resolve()
        head=git_text(root,"rev-parse","HEAD");parent=git_text(root,"rev-parse","HEAD^");status=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R3B_commit",parent==PARENT_R3B_COMMIT,parent)
        gate("repository_clean",status=="",repr(status))
        for fn,blob in SOURCE_BLOBS.items():
            p=root/fn;a=git_blob_sha(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",a==blob,a)
        for p,blob,label in ((root/C2_CONTRACT,C2_CONTRACT_BLOB,"C2_contract"),(root/C3_CONTRACT,C3_CONTRACT_BLOB,"C3_contract")):
            a=git_blob_sha(p,root) if p.is_file() else "missing";gate(f"{label}_git_blob_exact",a==blob,a)

        stage="R3B_R3A_binding"
        r3b=drive/R3B_OUT_REL;r3a=drive/R3A_OUT_REL
        gate("R3B_output_present",r3b.is_dir(),str(r3b));gate("R3A_output_present",r3a.is_dir(),str(r3a))
        m3b=verify_manifest(r3b,R3B_MANIFEST);m3a=verify_manifest(r3a,R3A_MANIFEST)
        gate("R3B_manifest_SHA_closure",True,len(m3b));gate("R3A_manifest_SHA_closure",True,len(m3a))
        s3b=load_json(r3b/R3B_SUMMARY);sel=load_json(r3b/R3B_SELECTED);a3=load_json(r3a/R3A_AUTHORITY)
        gate("R3B_status_exact",s3b.get("status")==R3B_STATUS,s3b.get("status"))
        gate("R3B_selected_candidate_exact",s3b.get("winner_candidate_id")==SELECTED_ID,s3b.get("winner_candidate_id"))
        gate("R3B_selected_SHA_exact",s3b.get("selected_frozen_weights_sha256")==SELECTED_SHA,s3b.get("selected_frozen_weights_sha256"))
        gate("R3B_selection_contract_winner_exact",sel["winner"]["candidate_id"]==SELECTED_ID)
        gate("R3B_geology0030_unopened",sel["geology0030_opened_for_selection"] is False)
        wp=r3b/R3B_WEIGHTS
        gate("R3B_selected_weights_present",wp.is_file(),str(wp))
        gate("R3B_selected_weights_file_SHA_exact",wp.is_file() and sha256_file(wp)==SELECTED_SHA,sha256_file(wp) if wp.is_file() else "missing")
        gate("R3A_authority_geology0030",a3["geology"]["id"]=="0030")
        gate("R3A_model_performance_still_unopened",a3["firewall"]["model_performance_computed"] is False)
        gate("R3A_sealed_target_manifest_SHA_exact",m3a.get(SEALED_TARGET_NAME)==SEALED_TARGET_SHA,m3a.get(SEALED_TARGET_NAME))
        st=r3a/SEALED_TARGET_NAME
        gate("R3A_sealed_target_file_SHA_verified_without_opening",st.is_file() and sha256_file(st)==SEALED_TARGET_SHA)

        stage="C3_authority_binding"
        c3=find_named_exact([root,drive],C3_NAME,C3_SHA)
        gate("C3_normalization_exact_SHA",sha256_file(c3)==C3_SHA,str(c3))
        c2c=load_json(root/C2_CONTRACT);c3c=load_json(root/C3_CONTRACT)
        gate("C2_sampling_method_exact",c2c["sampling"]["method"]=="trilinear cell-centered",c2c["sampling"]["method"])
        gate("C2_sampling_origin_exact",c2c["sampling"]["origin_center_m"]==[0.,0.,0.],c2c["sampling"]["origin_center_m"])
        gate("C2_grid_spacing_exact",c2c["sampling"]["grid_spacing_m"]==[6.096,6.096,1.2192],c2c["sampling"]["grid_spacing_m"])
        expected_channels=["xi","pollock_tau_hat","adv_tau_hat","log10_Kh","log10_Kz_over_Kh","porosity","pressure_z"]
        gate("C3_required_sequence_channels_exact",c3c["required_sequence_channels"]==expected_channels,c3c["required_sequence_channels"])
        with np.load(c3,allow_pickle=False) as z:
            pmean=float(np.asarray(z["pressure_mean_psi"]).reshape(-1)[0])
            pstd=float(np.asarray(z["pressure_std_psi"]).reshape(-1)[0])
            lnwm=float(np.asarray(z["ln_weight_mean"]).reshape(-1)[0])
            lnws=float(np.asarray(z["ln_weight_std"]).reshape(-1)[0])
        gate("C3_pressure_std_positive",np.isfinite(pstd) and pstd>0,pstd)
        gate("C3_ln_weight_std_positive",np.isfinite(lnws) and lnws>0,lnws)

        stage="load_R3A_physics"
        fp=r3a/FLOW_NAME;mp=r3a/METRIC_NAME
        gate("R3A_flow_SHA_exact",fp.is_file() and sha256_file(fp)==m3a[FLOW_NAME],m3a.get(FLOW_NAME))
        gate("R3A_metric_SHA_exact",mp.is_file() and sha256_file(mp)==m3a[METRIC_NAME],m3a.get(METRIC_NAME))
        with np.load(fp,allow_pickle=False) as z:
            qx,qy,qz=[np.asarray(z[k],float) for k in ("Qx","Qy","Qz")]
            Kx,Ky,Kz=[np.asarray(z[k],float) for k in ("Kx_mD","Ky_mD","Kz_mD")]
            pressure=np.asarray(z["pressure_psi"],float);phi=np.full(EXPECTED_GRID,.2,float)
        with np.load(mp,allow_pickle=False) as z:
            theta=np.asarray(z["theta"],float);xyz=np.asarray(z["xyz_m"],float)
            ptau=np.asarray(z["pollock_tau_s"],float);te=np.asarray(z["pollock_tau_end_s"],float)
            weight=np.asarray(z["streamline_weight_m3_s"],float)
        gate("R3A_xyz_shape_exact",xyz.shape==(1078,201,3),xyz.shape)
        gate("R3A_pollock_tau_shape_exact",ptau.shape==(1078,201),ptau.shape)
        gate("R3A_tau_end_shape_exact",te.shape==(1078,),te.shape)

        stage="source_authentic_ADV_generation"
        sg5=load_module(root/SG5_RUNNER,"r3br2_sg5")
        b2=load_module(root/B2_RUNNER,"r3br2_b2")
        c2=load_module(root/C2_RUNNER,"r3br2_c2")
        vx,vy,vz=[np.asarray(a,float) for a in sg5.construct_face_pore_velocities(qx,qy,qz)]
        cx,cy,cz=face_to_cell(vx,vy,vz)
        div,tol,src_idx,sm,meta=b2.bind_injector_sources(qx,qy,qz);sm=np.asarray(sm,bool)
        gate("ADV_exact_five_source_cells",int(sm.sum())==5,int(sm.sum()))
        adv_grid,aa=solve_adv(cx,cy,cz,sm,6.096,6.096,1.2192)
        gate("ADV_grid_shape_exact",adv_grid.shape==EXPECTED_GRID,adv_grid.shape)
        gate("ADV_grid_finite",aa["finite"]);gate("ADV_grid_nonnegative",aa["nonnegative"])
        gate("ADV_non_source_positive",aa["non_source_positive"])
        gate("ADV_source_zero",aa["source_max_abs_s"]<1e-8,aa["source_max_abs_s"])
        gate("ADV_relative_PDE_residual_lt_1e8",aa["relative_L2_residual"]<1e-8,aa["relative_L2_residual"])

        stage="C2_sampling_C3_conditioning"
        origin=np.asarray(c2c["sampling"]["origin_center_m"],float);dx,dy,dz=[float(x) for x in c2c["sampling"]["grid_spacing_m"]]
        adv_s,aadv=c2.trilinear(adv_grid,xyz,dx,dy,dz,origin)
        kx_s,akx=c2.trilinear(Kx,xyz,dx,dy,dz,origin)
        ky_s,aky=c2.trilinear(Ky,xyz,dx,dy,dz,origin)
        kz_s,akz=c2.trilinear(Kz,xyz,dx,dy,dz,origin)
        phi_s,aphi=c2.trilinear(phi,xyz,dx,dy,dz,origin)
        p_s,ap=c2.trilinear(pressure,xyz,dx,dy,dz,origin)
        sampled=[adv_s,kx_s,ky_s,kz_s,phi_s,p_s]
        gate("all_sampled_channel_shapes_exact",all(a.shape==(1078,201) for a in sampled))
        gate("all_sampled_channels_finite",all(np.isfinite(a).all() for a in sampled))
        pth=ptau/te[:,None];ath=adv_s/te[:,None]
        Kh=np.sqrt(np.maximum(kx_s,1e-30)*np.maximum(ky_s,1e-30))
        logKh=np.log10(np.maximum(Kh,1e-30))
        logKr=np.log10(np.maximum(kz_s,1e-30)/np.maximum(Kh,1e-30))
        pz=(p_s-pmean)/pstd;xi=np.broadcast_to(theta[None,:],(1078,201))
        X7=np.stack([xi,pth,ath,logKh,logKr,phi_s,pz],axis=-1).astype(np.float32)
        Xstatic=((np.log(np.maximum(weight,1e-300))-lnwm)/lnws)[:,None].astype(np.float32)
        gate("X7_shape_exact",X7.shape==(1078,201,7),X7.shape);gate("X7_finite",np.isfinite(X7).all())
        gate("Xstatic_shape_exact",Xstatic.shape==(1078,1),Xstatic.shape)
        gate("pollock_tau_hat_start_zero",float(np.max(np.abs(pth[:,0])))<=1e-12)
        gate("pollock_tau_hat_end_one",float(np.max(np.abs(pth[:,-1]-1.)))<=1e-12)

        nt=9;N=nt*1078
        X7f=np.broadcast_to(X7[None],(nt,1078,201,7)).reshape(N,201,7).copy()
        td=np.repeat(TARGET_DAYS,1078);th=(td/1000.).astype(np.float32)
        eta=TARGET_DAYS[:,None]*86400./te[None,:]
        es=np.repeat(eta[:,:,None],201,axis=2).reshape(N,201).astype(np.float32)
        Tseq=np.broadcast_to(th[:,None,None],(N,201,1)).astype(np.float32)
        X9=np.concatenate([X7f,Tseq,es[:,:,None]],axis=2).astype(np.float32)
        ti=np.repeat(np.arange(nt,dtype=np.int64),1078);si=np.tile(np.arange(1078,dtype=np.int64),nt)
        gate("deployment_X9_shape_exact",X9.shape==(9702,201,9),X9.shape)
        gate("deployment_X9_finite",np.isfinite(X9).all())
        gate("deployment_time_major_order_exact",np.array_equal(ti[:1078],np.zeros(1078,dtype=np.int64)))
        gate("deployment_streamline_order_exact",np.array_equal(si[:1078],np.arange(1078,dtype=np.int64)))
        gate("eta_mapping_finite_positive",np.isfinite(es).all() and np.all(es>0))

        stage="seal_conditioning_authority"
        cname="POSTV16_AV1_D_R3B_R2_Geology0030_C26_Deployment_Conditioning.npz"
        cbytes=deterministic_npz_bytes({
            "X_sequence_required_geology0030":X7,
            "X_static_required_geology0030":Xstatic,
            "X_full_C26_input":X9,
            "target_time_days":td,"target_time_hat":th,"target_eta_sequence":es,
            "time_index":ti,"streamline_index":si,
            "streamline_weight_m3_s":weight,
            "pollock_tau_s":ptau,"pollock_tau_end_s":te,
            "adv_tau_grid_s":adv_grid,"adv_tau_sampled_s":adv_s,
            "theta":theta,"case_id":np.array(CASE_ID),
            "selected_checkpoint_sha256":np.array(SELECTED_SHA),
            "C3_normalization_sha256":np.array(C3_SHA),
        })
        immutable_publish(out,{cname:cbytes});csha=sha256_file(out/cname)

        authority={
            "milestone":MILESTONE,"status":STATUS_PASS,"case_id":CASE_ID,
            "selected_model":{"candidate_id":SELECTED_ID,"weights_sha256":SELECTED_SHA,"loaded_for_inference":False},
            "conditioning":{
                "required_sequence_channels":expected_channels,
                "X7_shape":[1078,201,7],"C26_input_shape":[9702,201,9],
                "target_days":TARGET_DAYS.tolist(),"sample_order":"time-major then streamline",
                "ADV_authority":"exact D29/B7 directional travel-time semantics",
                "sampling_authority":"frozen V16C2 trilinear cell-centered",
                "normalization_authority_sha256":C3_SHA,
                "artifact":cname,"artifact_sha256":csha,
            },
            "ADV_certification":aa,
            "sampling_audit":{"ADV":aadv,"Kx":akx,"Ky":aky,"Kz":akz,"porosity":aphi,"pressure":ap},
            "firewall":{
                "sealed_geology0030_target_opened":False,"model_inference_performed":False,
                "training_or_retuning_performed":False,"checkpoint_selection_changed":False,
                "normalization_refit":False,"feature_substitution":False,"xD_used_as_ADV_substitute":False,
            },
            "next":"POSTV16-AV1-D-R3C — one-touch final evaluation of frozen R3B_RESPONSE on sealed geology0030.",
        }
        summary={
            "milestone":MILESTONE,"status":STATUS_PASS,"repository_head":head,"repository_parent":parent,
            "selected_candidate":SELECTED_ID,"selected_weights_sha256":SELECTED_SHA,
            "conditioning_artifact_sha256":csha,"C26_input_shape":[9702,201,9],
            "sealed_target_opened":False,"model_inference_performed":False,"training_or_retuning_performed":False,
            "next":authority["next"],
        }
        immutable_publish(out,{
            "PAD_Stream_POSTV16_AV1_D_R3B_R2_Summary.json":json_bytes(summary),
            "POSTV16_AV1_D_R3B_R2_Deployment_Conditioning_Authority.json":json_bytes(authority),
            "POSTV16_AV1_D_R3B_R2_Final_Gate_Matrix.csv":csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
        })
        rows=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="POSTV16_AV1_D_R3B_R2_Artifact_Manifest.csv":
                rows.append({"file":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
        immutable_publish(out,{"POSTV16_AV1_D_R3B_R2_Artifact_Manifest.csv":csv_bytes(rows)})

        print("\n"+"="*168);print("POSTV16-AV1-D-R3B-R2: PASS");print("="*168)
        print(f"{'Status':86}: {STATUS_PASS}")
        print(f"{'Selected candidate / SHA':86}: {SELECTED_ID} / {SELECTED_SHA}")
        print(f"{'C26 deployment input shape':86}: (9702, 201, 9)")
        print(f"{'Conditioning artifact SHA256':86}: {csha}")
        print(f"{'Sealed geology0030 target opened':86}: False")
        print(f"{'Model inference performed':86}: False")
        print(f"{'NEXT':86}: POSTV16-AV1-D-R3C — one-touch final sealed evaluation")
        print("="*168)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        rep={"milestone":MILESTONE,"status":STATUS_BLOCKED,"failed_stage":stage,"exception":repr(exc),"gates":gates,
             "sealed_target_opened":False,"model_inference_performed":False,"training_or_retuning_performed":False,
             "next_action":"Audit only failed deployment-conditioning authority gate. Do not open geology0030 target or alter selected checkpoint."}
        data=json_bytes(rep);p=blocked/"POSTV16_AV1_D_R3B_R2_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:
            p=blocked/("POSTV16_AV1_D_R3B_R2_Blocked_Report_"+hashlib.sha256(data).hexdigest()[:12]+".json")
        if not p.exists():p.write_bytes(data)
        print("\n"+"="*168);print("POSTV16-AV1-D-R3B-R2: BLOCKED");print("="*168)
        print("Failed stage:",stage);print("Exception   :",repr(exc));print("Report      :",p)
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
        self_test();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
