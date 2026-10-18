#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,io,json,subprocess,sys,zipfile
from pathlib import Path
from typing import Any
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

MILESTONE='POSTV16-AV1-D-R5C-R1'
STATUS_PASS='AV1DR5CR1_TIME_MAJOR_ORDER_DTYPE_REPAIRED_GEOLOGY0031_C26_DEPLOYMENT_CONDITIONING_AUTHORITY_GENERATED_CERTIFIED_AND_SHA_SEALED'
STATUS_BLOCKED='AV1DR5CR1_DEPLOYMENT_CONDITIONING_BLOCKED'
RID='PAD_STREAM_V16_RC1_B92D52088D01078A'
PARENT='6f6b112614c032f3794126da00d71ea1f6cb0439'

R5C_ORIG='PAD_Stream_POSTV16_AV1_D_R5C_Geology0031_Deployment_Conditioning_Authority.py'; R5C_ORIG_BLOB='3c8b4ecee8599f6dd6d8982c87dbf824d9c00d50'
R5BR1='PAD_Stream_POSTV16_AV1_D_R5B_R1_C7_Metric_Binding_ControlFlow_Repair.py'; R5BR1_BLOB='773defe3d960cade441ce8dd098b31791747ca80'
R5A='PAD_Stream_POSTV16_AV1_D_R5A_Producer_Labels_and_Geology0031_Sealed_Authority.py'; R5A_BLOB='740c4862e934c2b05b2eaa63c4136110c01866e9'
R5='PAD_Stream_POSTV16_AV1_D_R5_Prospective_Producer_Resolved_Repair_and_Geology0031_Freeze.py'; R5_BLOB='c5d2f64f124153b4e352f302302e0558a31c5c58'
R3BR2='PAD_Stream_POSTV16_AV1_D_R3B_R2_Geology0030_Deployment_Conditioning_Authority.py'; R3BR2_BLOB='bbf853cbef197cc585edc67007f8c96815cb25c8'
D29='PAD_Stream_V16D29_R1_Exact_D10C_Derived_FMM_ADV_36Case_ControlSpace_Execution.py'; D29_BLOB='3377a8987e9078816d5826aef9d52a58465de527'
B2='PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py'; B2_BLOB='95025d1e67a74f9dacaad311e5a402b63e7b4335'
B7='PAD_Stream_V16B7_Controlled_Directional_Advective_Travel_Time_Solve.py'; B7_BLOB='9c860bf05fcf16616b447cd56d0e62065b2174a0'
SG5='PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py'; SG5_BLOB='9a0b64ea7e669904d0d9855ade1c6b052f05ecea'
C2='PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py'; C2_BLOB='21ff44de456102772c99f7ddc80898c9139a76db'
BLOBS={R5C_ORIG:R5C_ORIG_BLOB,R5BR1:R5BR1_BLOB,R5A:R5A_BLOB,R5:R5_BLOB,R3BR2:R3BR2_BLOB,D29:D29_BLOB,B2:B2_BLOB,B7:B7_BLOB,SG5:SG5_BLOB,C2:C2_BLOB}

C2_CONTRACT=Path('output')/'V16_C2_MULTI_COORDINATE_STREAMLINE_TRANSPORT_DATABASE'/'V16C2_Multi_Coordinate_Transport_Database_Contract.json'; C2_CONTRACT_BLOB='88bc5ad068f0f24e78230318c5eab69b80f3dfc2'
C3_CONTRACT=Path('output')/'V16_C3_PIRNN_TRANSPORT_CONDITIONING_CONTRACT'/'V16C3_PIRNN_Transport_Conditioning_Contract.json'; C3_CONTRACT_BLOB='220ea7dcf59ef32cc850af065abca0b0c699029e'
C3_NAME='V16C3_Conditioning_Normalization_Parameters.npz'; C3_SHA='870c7360aff526c6ad0af31562270c139c61c69177a59290518f45b0d907efd3'
BASE=Path('post_v16')/RID/'POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi'
R5D=BASE/'POSTV16_AV1_D_R5_Prospective_Producer_Resolved_Repair_and_Geology0031_Freeze'; R5_ACCEPT='POSTV16_AV1_D_R5_Geology0031_Independent_Acceptance_Authority.json'; R5_MANIFEST='POSTV16_AV1_D_R5_Artifact_Manifest.csv'
R5AD=BASE/'POSTV16_AV1_D_R5A_Producer_Labels_and_Geology0031_Sealed_Authority'; R5A_AUTH='POSTV16_AV1_D_R5A_Sealed_Acceptance_Authority.json'; R5A_MANIFEST='POSTV16_AV1_D_R5A_Artifact_Manifest.csv'
FLOW='POSTV16_AV1_D_R5A_Geology0031_R500_B2000_Flow.npz'; METRIC='POSTV16_AV1_D_R5A_Geology0031_R500_B2000_201Node_C7_FaceMetric.npz'; TARGET='POSTV16_AV1_D_R5A_Geology0031_R500_B2000_SEALED_Stage4_Target.npz'; TARGET_SHA='cef2647c394909fb268b621a5e6074b49c3aa41a285c75082d7d976f48e62afc'
R5BD=BASE/'POSTV16_AV1_D_R5B_R1_Producer_Balanced_TrainValidation_Repair_Execution'; R5B_SUMMARY='PAD_Stream_POSTV16_AV1_D_R5B_R1_Summary.json'; R5B_SEL='POSTV16_AV1_D_R5B_R1_Selected_Checkpoint_Contract.json'; R5B_MANIFEST='POSTV16_AV1_D_R5B_R1_Artifact_Manifest.csv'; R5B_WEIGHTS='POSTV16_AV1_D_R5B_R1_SELECTED_FROZEN.weights.h5'
R5B_STATUS='AV1DR5BR1_C7_METRIC_BINDING_CONTROLFLOW_REPAIRED_SINGLE_PRODUCER_BALANCED_TRAIN_VALIDATION_REPAIR_EXECUTED_SELECTED_CHECKPOINT_FROZEN_GEOLOGY0031_REMAINS_SEALED'
SELECTED_ID='R5B_PRODUCER_BALANCED_RESPONSE'; SELECTED_SHA='46fa4e4dc9fa3dc9f00aaa0d0270010c7dd2a2048f43f247be691c027497c709'
OUTD=BASE/'POSTV16_AV1_D_R5C_R1_Geology0031_Deployment_Conditioning_Authority'; BLOCKD=BASE/'POSTV16_AV1_D_R5C_R1_BLOCKED'
GRID=(15,50,50); NSL=1078; NN=201; DAYS=np.array([30.,60.,100.,150.,250.,365.,500.,750.,1000.]); CASE='POSTV16_AV1_Geology0031_R500_B2000'

class GateError(RuntimeError): pass
def sha(p):
 h=hashlib.sha256(); p=Path(p)
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def git(root,*args): return subprocess.run(['git','-C',str(root),*args],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.strip()
def loadj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def readcsv(p):
 with Path(p).open('r',newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def manifest(d,n):
 m={r['file']:r['sha256'] for r in readcsv(d/n)}
 for fn,e in m.items():
  p=d/fn
  if not p.is_file() or sha(p)!=e: raise GateError(f'manifest_SHA:{fn}')
 return m
def jbytes(x): return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def cbytes(rows):
 if not rows:return b''
 fs=[]
 for r in rows:
  for k in r:
   if k not in fs:fs.append(k)
 s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=fs,lineterminator='\n');w.writeheader();w.writerows(rows);return s.getvalue().encode()
def npzbytes(arrays):
 o=io.BytesIO()
 with zipfile.ZipFile(o,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for k in sorted(arrays):
   b=io.BytesIO();np.save(b,np.asarray(arrays[k]),allow_pickle=False);info=zipfile.ZipInfo(f'{k}.npy',date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o600<<16;z.writestr(info,b.getvalue())
 return o.getvalue()
def publish(d,files):
 d.mkdir(parents=True,exist_ok=True)
 for n,b in files.items():
  p=d/n
  if p.exists() and p.read_bytes()!=b: raise GateError(f'existing_output_differs:{n}')
  if not p.exists(): p.write_bytes(b)
def findexact(roots,name,e):
 hits=[]
 for r in roots:
  if not r.exists():continue
  for p in r.rglob(name):
   try:
    if p.is_file() and sha(p)==e:hits.append(p.resolve())
   except OSError:pass
 if not hits:raise GateError(f'exact_authority_not_found:{name}:{e}')
 return sorted(set(hits),key=lambda p:(len(str(p)),str(p)))[0]
def mod(path,name):
 s=importlib.util.spec_from_file_location(name,path)
 if s is None or s.loader is None:raise GateError(f'cannot_load_module:{path}')
 m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def face_to_cell(vx,vy,vz):
 nz,ny,nxm1=vx.shape;nx=nxm1+1;x=np.empty((nz,ny,nx));y=np.empty_like(x);z=np.empty_like(x)
 x[:,:,0]=vx[:,:,0];x[:,:,-1]=vx[:,:,-1];x[:,:,1:-1]=.5*(vx[:,:,:-1]+vx[:,:,1:]);y[:,0,:]=vy[:,0,:];y[:,-1,:]=vy[:,-1,:];y[:,1:-1,:]=.5*(vy[:,:-1,:]+vy[:,1:,:]);z[0]=vz[0];z[-1]=vz[-1];z[1:-1]=.5*(vz[:-1]+vz[1:]);return x,y,z
def solve_adv(cx,cy,cz,sm,dx,dy,dz):
 aW=np.maximum(cx,0)/dx;aE=np.maximum(-cx,0)/dx;aS=np.maximum(cy,0)/dy;aN=np.maximum(-cy,0)/dy;aB=np.maximum(cz,0)/dz;aT=np.maximum(-cz,0)/dz
 aW[:,:,0]=0;aE[:,:,-1]=0;aS[:,0,:]=0;aN[:,-1,:]=0;aB[0]=0;aT[-1]=0;aP=aW+aE+aS+aN+aB+aT;nz,ny,nx=aP.shape;n=nz*ny*nx
 def flat(k,j,i):return (k*ny+j)*nx+i
 rows=[];cols=[];vals=[];rhs=np.ones(n,float)
 for k in range(nz):
  for j in range(ny):
   for i in range(nx):
    r=flat(k,j,i)
    if sm[k,j,i]: rows.append(r);cols.append(r);vals.append(1.);rhs[r]=0.;continue
    d=aP[k,j,i]
    if not np.isfinite(d) or d<=0:raise GateError(f'invalid_ADV_diagonal:{(k,j,i)}:{d}')
    rows.append(r);cols.append(r);vals.append(d)
    if i>0 and aW[k,j,i]>0:rows.append(r);cols.append(flat(k,j,i-1));vals.append(-aW[k,j,i])
    if i<nx-1 and aE[k,j,i]>0:rows.append(r);cols.append(flat(k,j,i+1));vals.append(-aE[k,j,i])
    if j>0 and aS[k,j,i]>0:rows.append(r);cols.append(flat(k,j-1,i));vals.append(-aS[k,j,i])
    if j<ny-1 and aN[k,j,i]>0:rows.append(r);cols.append(flat(k,j+1,i));vals.append(-aN[k,j,i])
    if k>0 and aB[k,j,i]>0:rows.append(r);cols.append(flat(k-1,j,i));vals.append(-aB[k,j,i])
    if k<nz-1 and aT[k,j,i]>0:rows.append(r);cols.append(flat(k+1,j,i));vals.append(-aT[k,j,i])
 A=sparse.csr_matrix((vals,(rows,cols)),shape=(n,n));tf=spsolve(A,rhs);tau=tf.reshape(GRID);res=A@tf-rhs
 return tau,{'relative_L2_residual':float(np.linalg.norm(res)/max(np.linalg.norm(rhs),1e-300)),'max_abs_residual':float(np.max(np.abs(res))),'source_max_abs_s':float(np.max(np.abs(tau[sm]))),'finite':bool(np.isfinite(tau).all()),'nonnegative':bool(np.all(tau>=-1e-10)),'non_source_positive':bool(np.all(tau[~sm]>0)),'unknowns':int(n),'nnz':int(A.nnz)}
def self_test():
 assert SELECTED_ID=='R5B_PRODUCER_BALANCED_RESPONSE';assert SELECTED_SHA=='46fa4e4dc9fa3dc9f00aaa0d0270010c7dd2a2048f43f247be691c027497c709';assert DAYS.tolist()==[30.,60.,100.,150.,250.,365.,500.,750.,1000.];print('POSTV16-AV1-D-R5C-R1 self-test: PASS')

def main(root,drive):
 gates={};stage='preflight';root=root.resolve();drive=drive.resolve();out=drive/OUTD;blocked=drive/BLOCKD
 def gate(n,v,x=None):
  ok=bool(v);gates[n]={'passed':ok,'value':x};print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f' — {x}' if x is not None else ''))
  if not ok:raise GateError(n)
 print('='*172);print('POSTV16-AV1-D-R5C-R1 — TIME-MAJOR ORDER DTYPE REPAIR + GEOLOGY0031 C26 DEPLOYMENT CONDITIONING AUTHORITY');print('='*172);print('NO MODEL INFERENCE. NO TARGET OPENING. NO TRAINING/RETUNING.');print('ADV: FROZEN D29/B7 SEMANTICS. SAMPLING: FROZEN C2. NORMALIZATION: FROZEN C3.\n')
 try:
  head=git(root,'rev-parse','HEAD');parent=git(root,'rev-parse','HEAD^');stat=git(root,'status','--porcelain');gate('repository_parent_is_R5C_commit',parent==PARENT,parent);gate('repository_clean',stat=='',repr(stat))
  for fn,e in BLOBS.items():
   a=git(root,'hash-object',str(root/fn)) if (root/fn).is_file() else 'missing';gate(f'{Path(fn).stem}_git_blob_exact',a==e,a)
  for p,e,n in ((root/C2_CONTRACT,C2_CONTRACT_BLOB,'C2_contract'),(root/C3_CONTRACT,C3_CONTRACT_BLOB,'C3_contract')):
   a=git(root,'hash-object',str(p)) if p.is_file() else 'missing';gate(f'{n}_git_blob_exact',a==e,a)
  stage='contract_binding';r5=drive/R5D;r5a=drive/R5AD;r5b=drive/R5BD
  for n,d in [('R5',r5),('R5A',r5a),('R5BR1',r5b)]:gate(f'{n}_output_present',d.is_dir(),str(d))
  m5=manifest(r5,R5_MANIFEST);m5a=manifest(r5a,R5A_MANIFEST);m5b=manifest(r5b,R5B_MANIFEST);gate('R5_manifest_SHA_closure',True,len(m5));gate('R5A_manifest_SHA_closure',True,len(m5a));gate('R5BR1_manifest_SHA_closure',True,len(m5b))
  acc=loadj(r5/R5_ACCEPT);a5=loadj(r5a/R5A_AUTH);s5b=loadj(r5b/R5B_SUMMARY);sel=loadj(r5b/R5B_SEL)
  gate('R5_acceptance_0031',acc['geology_id']=='0031' and int(acc['seed'])==390051);gate('R5_target_days_exact',[float(x) for x in acc['target_days']]==DAYS.tolist());gate('R5_target_forbidden_training',acc['generation_order']['target_may_not_be_opened_for_training_or_selection'] is True)
  gate('R5A_authority_0031',a5['acceptance_authority']['geology']['id']=='0031');gate('R5A_performance_unopened',a5['acceptance_authority']['firewall']['model_performance_computed'] is False);gate('R5A_target_manifest_SHA',m5a.get(TARGET)==TARGET_SHA,m5a.get(TARGET));gate('R5A_target_file_SHA_without_opening',(r5a/TARGET).is_file() and sha(r5a/TARGET)==TARGET_SHA)
  gate('R5BR1_status_exact',s5b['status']==R5B_STATUS,s5b['status']);gate('R5BR1_candidate_exact',s5b['candidate_id']==SELECTED_ID,s5b['candidate_id']);gate('R5BR1_selected_SHA_exact',s5b['selected_frozen_weights_sha256']==SELECTED_SHA);gate('R5BR1_selection_candidate_exact',sel['candidate_id']==SELECTED_ID);gate('R5BR1_0031_unopened',sel['geology0031_target_opened'] is False);gate('R5BR1_0031_inference_false',sel['geology0031_model_inference'] is False);gate('R5BR1_retired_test_unused',sel['retired_test_used'] is False)
  wp=r5b/R5B_WEIGHTS;gate('R5BR1_weights_SHA_exact',wp.is_file() and sha(wp)==SELECTED_SHA,sha(wp) if wp.is_file() else 'missing')
  stage='C3_binding';c3=findexact([root,drive],C3_NAME,C3_SHA);gate('C3_exact_SHA',sha(c3)==C3_SHA,str(c3));c2c=loadj(root/C2_CONTRACT);c3c=loadj(root/C3_CONTRACT);channels=['xi','pollock_tau_hat','adv_tau_hat','log10_Kh','log10_Kz_over_Kh','porosity','pressure_z'];gate('C2_method',c2c['sampling']['method']=='trilinear cell-centered');gate('C2_origin',c2c['sampling']['origin_center_m']==[0.,0.,0.]);gate('C2_spacing',c2c['sampling']['grid_spacing_m']==[6.096,6.096,1.2192]);gate('C3_channels',c3c['required_sequence_channels']==channels,c3c['required_sequence_channels'])
  with np.load(c3,allow_pickle=False) as z:pmean=float(z['pressure_mean_psi'].reshape(-1)[0]);pstd=float(z['pressure_std_psi'].reshape(-1)[0]);lnwm=float(z['ln_weight_mean'].reshape(-1)[0]);lnws=float(z['ln_weight_std'].reshape(-1)[0])
  gate('C3_stds_positive',pstd>0 and lnws>0,(pstd,lnws))
  stage='load_R5A_physics';fp=r5a/FLOW;mp=r5a/METRIC;gate('R5A_flow_SHA',fp.is_file() and sha(fp)==m5a[FLOW],m5a.get(FLOW));gate('R5A_metric_SHA',mp.is_file() and sha(mp)==m5a[METRIC],m5a.get(METRIC))
  with np.load(fp,allow_pickle=False) as z:qx,qy,qz=[np.asarray(z[k],float) for k in ('Qx','Qy','Qz')];Kx,Ky,Kz=[np.asarray(z[k],float) for k in ('Kx_mD','Ky_mD','Kz_mD')];pressure=np.asarray(z['pressure_psi'],float);phi=np.full(GRID,.2,float)
  with np.load(mp,allow_pickle=False) as z:theta=np.asarray(z['theta'],float);xyz=np.asarray(z['xyz_m'],float);ptau=np.asarray(z['pollock_tau_s'],float);te=np.asarray(z['pollock_tau_end_s'],float);weight=np.asarray(z['streamline_weight_m3_s'],float)
  gate('metric_shapes',xyz.shape==(NSL,NN,3) and ptau.shape==(NSL,NN) and te.shape==(NSL,) and weight.shape==(NSL,),(xyz.shape,ptau.shape,te.shape,weight.shape));gate('weights_positive',np.isfinite(weight).all() and np.all(weight>0))
  stage='ADV';sg5=mod(root/SG5,'r5c_sg5');b2=mod(root/B2,'r5c_b2');c2=mod(root/C2,'r5c_c2');vx,vy,vz=[np.asarray(a,float) for a in sg5.construct_face_pore_velocities(qx,qy,qz)];cx,cy,cz=face_to_cell(vx,vy,vz);div,tol,src_idx,sm,meta=b2.bind_injector_sources(qx,qy,qz);sm=np.asarray(sm,bool);gate('ADV_five_sources',int(sm.sum())==5,int(sm.sum()));adv,aa=solve_adv(cx,cy,cz,sm,6.096,6.096,1.2192);gate('ADV_shape',adv.shape==GRID,adv.shape);gate('ADV_finite',aa['finite']);gate('ADV_nonnegative',aa['nonnegative']);gate('ADV_positive_non_source',aa['non_source_positive']);gate('ADV_source_zero',aa['source_max_abs_s']<1e-8,aa['source_max_abs_s']);gate('ADV_PDE_residual',aa['relative_L2_residual']<1e-8,aa['relative_L2_residual'])
  stage='conditioning';origin=np.asarray(c2c['sampling']['origin_center_m'],float);dx,dy,dz=[float(x) for x in c2c['sampling']['grid_spacing_m']];adv_s,aadv=c2.trilinear(adv,xyz,dx,dy,dz,origin);kx_s,akx=c2.trilinear(Kx,xyz,dx,dy,dz,origin);ky_s,aky=c2.trilinear(Ky,xyz,dx,dy,dz,origin);kz_s,akz=c2.trilinear(Kz,xyz,dx,dy,dz,origin);phi_s,aphi=c2.trilinear(phi,xyz,dx,dy,dz,origin);p_s,ap=c2.trilinear(pressure,xyz,dx,dy,dz,origin);sampled=[adv_s,kx_s,ky_s,kz_s,phi_s,p_s];gate('sample_shapes',all(a.shape==(NSL,NN) for a in sampled));gate('sample_finite',all(np.isfinite(a).all() for a in sampled))
  pth=ptau/te[:,None];ath=adv_s/te[:,None];Kh=np.sqrt(np.maximum(kx_s,1e-30)*np.maximum(ky_s,1e-30));logKh=np.log10(np.maximum(Kh,1e-30));logKr=np.log10(np.maximum(kz_s,1e-30)/np.maximum(Kh,1e-30));pz=(p_s-pmean)/pstd;xi=np.broadcast_to(theta[None,:],(NSL,NN));X7=np.stack([xi,pth,ath,logKh,logKr,phi_s,pz],axis=-1).astype(np.float32);Xs=((np.log(np.maximum(weight,1e-300))-lnwm)/lnws)[:,None].astype(np.float32);gate('X7_shape',X7.shape==(NSL,NN,7),X7.shape);gate('X7_finite',np.isfinite(X7).all());gate('Xstatic_shape',Xs.shape==(NSL,1));gate('pollock_hat_boundaries',np.max(np.abs(pth[:,0]))<=1e-12 and np.max(np.abs(pth[:,-1]-1))<=1e-12)
  nt=9;N=nt*NSL;X7f=np.broadcast_to(X7[None],(nt,NSL,NN,7)).reshape(N,NN,7).copy();td=np.repeat(DAYS,NSL);th=(td/1000.).astype(np.float32);eta=DAYS[:,None]*86400./te[None,:];es=np.repeat(eta[:,:,None],NN,axis=2).reshape(N,NN).astype(np.float32);Tseq=np.broadcast_to(th[:,None,None],(N,NN,1)).astype(np.float32);X9=np.concatenate([X7f,Tseq,es[:,:,None]],axis=2).astype(np.float32);ti=np.repeat(np.arange(nt,dtype=np.int64),NSL);si=np.tile(np.arange(NSL,dtype=np.int64),nt);gate('X9_shape',X9.shape==(9702,201,9),X9.shape);gate('X9_finite',np.isfinite(X9).all());gate('time_major_order',np.array_equal(ti[:NSL],np.zeros(NSL,np.int64)) and np.array_equal(si[:NSL],np.arange(NSL,dtype=np.int64)));gate('eta_positive',np.isfinite(es).all() and np.all(es>0))
  stage='seal';cname='POSTV16_AV1_D_R5C_R1_Geology0031_C26_Deployment_Conditioning.npz';publish(out,{cname:npzbytes({'X_sequence_required_geology0031':X7,'X_static_required_geology0031':Xs,'X_full_C26_input':X9,'target_time_days':td,'target_time_hat':th,'target_eta_sequence':es,'time_index':ti,'streamline_index':si,'streamline_weight_m3_s':weight,'pollock_tau_s':ptau,'pollock_tau_end_s':te,'adv_tau_grid_s':adv,'adv_tau_sampled_s':adv_s,'theta':theta,'case_id':np.array(CASE),'selected_checkpoint_sha256':np.array(SELECTED_SHA),'C3_normalization_sha256':np.array(C3_SHA),'sealed_target_sha256':np.array(TARGET_SHA)})});csha=sha(out/cname)
  auth={'milestone':MILESTONE,'status':STATUS_PASS,'case_id':CASE,'selected_model':{'candidate_id':SELECTED_ID,'weights_sha256':SELECTED_SHA,'loaded_for_inference':False},'conditioning':{'required_sequence_channels':channels,'X7_shape':[1078,201,7],'C26_input_shape':[9702,201,9],'target_days':DAYS.tolist(),'sample_order':'time-major then streamline','ADV_authority':'exact D29/B7 directional travel-time semantics','sampling_authority':'frozen V16C2 trilinear cell-centered','normalization_authority_sha256':C3_SHA,'artifact':cname,'artifact_sha256':csha},'ADV_certification':aa,'sampling_audit':{'ADV':aadv,'Kx':akx,'Ky':aky,'Kz':akz,'porosity':aphi,'pressure':ap},'firewall':{'sealed_geology0031_target_opened':False,'model_inference_performed':False,'training_or_retuning_performed':False,'checkpoint_selection_changed':False,'normalization_refit':False,'feature_substitution':False,'xD_used_as_ADV_substitute':False,'geology0030_used':False,'retired_C19_test_used':False},'next':'POSTV16-AV1-D-R5D — one-touch final evaluation of frozen R5B-R1 checkpoint on sealed geology0031.'}
  summary={'milestone':MILESTONE,'status':STATUS_PASS,'repository_head':head,'repository_parent':parent,'selected_candidate':SELECTED_ID,'selected_weights_sha256':SELECTED_SHA,'conditioning_artifact_sha256':csha,'C26_input_shape':[9702,201,9],'sealed_target_sha256':TARGET_SHA,'sealed_target_opened':False,'model_inference_performed':False,'training_or_retuning_performed':False,'geology0030_used':False,'next':auth['next']};publish(out,{'PAD_Stream_POSTV16_AV1_D_R5C_R1_Summary.json':jbytes(summary),'POSTV16_AV1_D_R5C_R1_Deployment_Conditioning_Authority.json':jbytes(auth),'POSTV16_AV1_D_R5C_R1_Final_Gate_Matrix.csv':cbytes([{'gate':k,**v} for k,v in gates.items()])});rows=[]
  for p in sorted(out.iterdir()):
   if p.is_file() and p.name!='POSTV16_AV1_D_R5C_R1_Artifact_Manifest.csv':rows.append({'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size})
  publish(out,{'POSTV16_AV1_D_R5C_R1_Artifact_Manifest.csv':cbytes(rows)});print('\n'+'='*172);print('POSTV16-AV1-D-R5C-R1: PASS');print('='*172);print('Status:',STATUS_PASS);print('Selected candidate / SHA:',SELECTED_ID,'/',SELECTED_SHA);print('C26 deployment input shape: (9702, 201, 9)');print('Conditioning artifact SHA256:',csha);print('Sealed geology0031 target SHA256:',TARGET_SHA);print('Sealed target opened: False');print('Model inference performed: False');print('NEXT: POSTV16-AV1-D-R5D — one-touch final sealed evaluation');print('='*172);return 0
 except Exception as e:
  blocked.mkdir(parents=True,exist_ok=True);rep={'milestone':MILESTONE,'status':STATUS_BLOCKED,'failed_stage':stage,'exception':repr(e),'gates':gates,'sealed_target_opened':False,'model_inference_performed':False,'training_or_retuning_performed':False,'geology0030_used':False,'next_action':'Audit only the failed R5C conditioning gate. Do not open geology0031 or alter the R5B-R1 checkpoint.'};data=jbytes(rep);p=blocked/'POSTV16_AV1_D_R5C_R1_Blocked_Report.json';
  if p.exists() and p.read_bytes()!=data:p=blocked/f"POSTV16_AV1_D_R5C_R1_Blocked_Report_{hashlib.sha256(data).hexdigest()[:12]}.json"
  if not p.exists():p.write_bytes(data)
  print('\nPOSTV16-AV1-D-R5C-R1: BLOCKED\nStage:',stage,'\nException:',repr(e),'\nReport:',p);return 2

def args():
 p=argparse.ArgumentParser();p.add_argument('--project-root',type=Path,default=Path('.'));p.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'));p.add_argument('--self-test',action='store_true');return p.parse_args()
if __name__=='__main__':
 a=args()
 if a.self_test:self_test();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
