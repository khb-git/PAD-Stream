#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,io,json,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
from typing import Any
import numpy as np

MILESTONE='POSTV16-AV2-A4'
STATUS_PASS='AV2A4_VARIABLE_POROSITY_PIRNN_TRAINING_COMPLETE_BEST_VALIDATION_CHECKPOINT_FROZEN_LOCKED_OOD_ONE_TOUCH_EVALUATED'
STATUS_FAIL='AV2A4_VARIABLE_POROSITY_PIRNN_TRAINING_OR_ONE_TOUCH_OOD_SCIENTIFIC_FAIL_NO_RETUNING_OR_REEVALUATION_AUTHORIZED'
STATUS_BLOCKED='AV2A4_TECHNICAL_EXECUTION_BLOCKED'
PROTOCOL_ID='POSTV16_AV2_A4_VARIABLE_PHI_PIRNN_TRAIN_CHECKPOINT_OOD_V1'
RID='PAD_STREAM_V16_RC1_B92D52088D01078A'
PARENT='72bb2c308912185ae7471dcdf73ec1b3b2b75753'
A3='PAD_Stream_POSTV16_AV2_A3_Variable_Porosity_Teacher_Dataset_and_PIRNN_Protocol.py'; A3_BLOB='9b209abc3a2abb905b9250a16344e52160e61c47'
A2='PAD_Stream_POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution.py'; A2_BLOB='f141b07f0424d29a7996c089a76dbe7128af5132'
C25='PAD_Stream_V16C25_Differentiable_Pollock_Full_Physics_Residual_Boundary_Mask_and_Physics_Loss_Weight_Authority_Contract.py'; C25_BLOB='0a4740b95c2b5e5d15db3137414e663e1e9b6282'
C26='PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py'; C26_BLOB='62e19e6b502fb3ab101a2589251c26b5f9ad9031'
SOURCES={A3:A3_BLOB,A2:A2_BLOB,C25:C25_BLOB,C26:C26_BLOB}
BASE=Path('post_v16')/RID/'POSTV16_AV2_Variable_Porosity'
A3REL=BASE/'POSTV16_AV2_A3_Variable_Porosity_Teacher_Dataset_and_PIRNN_Protocol'
A2REL=BASE/'POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution'
OUTREL=BASE/'POSTV16_AV2_A4_PIRNN_Training_Checkpoint_and_OneTouch_OOD'
FAILREL=BASE/'POSTV16_AV2_A4_SCIENTIFIC_FAIL'; BLOCKREL=BASE/'POSTV16_AV2_A4_BLOCKED'
A3_STATUS='AV2A3_VARIABLE_POROSITY_TRAIN_VALIDATION_TEACHER_DATASET_CERTIFIED_LOCKED_OOD_PREDICTOR_ONLY_PIRNN_PROTOCOL_FROZEN'
A3_SUM='PAD_Stream_POSTV16_AV2_A3_Summary.json'; A3_TV='POSTV16_AV2_A3_TrainValidation_Transport_Dataset.npz'; A3_OOD='POSTV16_AV2_A3_LockedOOD_Predictor_Only_Dataset.npz'; A3_PH='POSTV16_AV2_A3_Variable_Porosity_Physics_Sidecar.npz'; A3_NORM='POSTV16_AV2_A3_TRAIN_Only_Normalization.npz'; A3_PROTOCOL='POSTV16_AV2_A3_Frozen_PIRNN_Training_and_Physics_Objective_Contract.json'; A3_DEC='POSTV16_AV2_A3_Decision_Contract.json'; A3_MAN='POSTV16_AV2_A3_Artifact_Manifest.csv'
A2_MAN='POSTV16_AV2_A2_Artifact_Manifest.csv'; A2_OOD='POSTV16_AV2_A2_AV2PHI0004_Variable_Porosity_Pore_Kinematics.npz'
CHECKPOINT='POSTV16_AV2_A4_Best_Validation_Model.keras'; CKFREEZE='POSTV16_AV2_A4_Best_Validation_Checkpoint_Freeze.json'; OODMARK='POSTV16_AV2_A4_LOCKED_OOD_OPENED.marker'
NN=201; NSL=1078; NT=9; CH=9; DAYS=np.array([30.,60.,100.,150.,250.,365.,500.,750.,1000.]); SPD=86400.
SEED=16021; BATCH=64; MAXEP=300; PAT=30; MDELTA=1e-6; LRPAT=10; MINLR=1e-6; LR=1e-3; LPHYS=.01
SWC=.2; SOR=.2; SPAN=.6; PEC=22.; NW=NO=2.; KRW=KRO=.8; MUW=.5; MUO=5.

class GateError(RuntimeError): pass
class ScientificFail(RuntimeError):
    def __init__(self,g,d=None): super().__init__(g); self.g=g; self.d=d

def sha(p):
    h=hashlib.sha256();
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def git(root,*a): return subprocess.run(['git','-C',str(root),*a],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.strip()
def blob(p,root): return git(root,'hash-object',str(p))
def lj(p): return json.loads(p.read_text())
def rcsv(p):
    with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def vman(d,n):
    m={r['file']:r['sha256'] for r in rcsv(d/n)}
    if not m: raise GateError('empty_manifest')
    for fn,e in m.items():
        p=d/fn
        if not p.is_file() or sha(p)!=e: raise GateError(f'manifest:{fn}')
    return m
def jb(x): return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def cb(rows):
    if not rows:return b''
    ks=[]
    for r in rows:
        for k in r:
            if k not in ks:ks.append(k)
    s=io.StringIO(newline=''); w=csv.DictWriter(s,fieldnames=ks,lineterminator='\n'); w.writeheader(); w.writerows(rows); return s.getvalue().encode()
def npzb(a):
    o=io.BytesIO()
    with zipfile.ZipFile(o,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for k in sorted(a):
            b=io.BytesIO(); np.save(b,np.asarray(a[k]),allow_pickle=False)
            i=zipfile.ZipInfo(k+'.npy',date_time=(1980,1,1,0,0,0)); i.compress_type=zipfile.ZIP_DEFLATED; i.external_attr=0o600<<16; z.writestr(i,b.getvalue())
    return o.getvalue()
def pub(out,files):
    out.mkdir(parents=True,exist_ok=True)
    for n,d in files.items():
        p=out/n
        if p.exists() and p.read_bytes()!=d: raise GateError('existing_output_differs:'+n)
        if not p.exists(): p.write_bytes(d)
def mod(path,name):
    s=importlib.util.spec_from_file_location(name,path)
    if s is None or s.loader is None: raise GateError('module:'+str(path))
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def pairs(ids,ri,sl,ti):
    A=[];B=[];ids=np.asarray(ids,int)
    for r in np.unique(ri[ids]):
        rr=ids[ri[ids]==r]
        for g in np.unique(sl[rr]):
            q=rr[sl[rr]==g];q=q[np.argsort(ti[q])]
            for a,b in zip(q[:-1],q[1:]):A.append(int(a));B.append(int(b))
    return np.asarray(A,int),np.asarray(B,int)
def met(P,T):
    e=np.asarray(P,float)-np.asarray(T,float); mse=float(np.mean(e*e));
    return dict(mse=mse,rmse=float(np.sqrt(mse)),mae=float(np.mean(np.abs(e))),max_abs_error=float(np.max(np.abs(e))),prediction_min=float(np.min(P)),prediction_max=float(np.max(P)))
def struct(P,ti,sl):
    P=np.asarray(P,float);sp=float(np.mean(np.diff(P,axis=1)>1e-7));neg=tot=0
    for g in np.unique(sl):
        q=np.where(sl==g)[0];q=q[np.argsort(ti[q])];dd=np.diff(P[q],axis=0);neg+=int(np.sum(dd<-1e-6));tot+=dd.size
    return dict(spatial_positive_fraction=sp,temporal_negative_fraction=float(neg/tot if tot else 0.))
def teacher_ok(d):
    return bool(d['Y_finite'] and d['advection_conservation_max_abs']<1e-11 and d['implicit_residual_max_abs']<1e-10 and d['preclip_bound_violation_max']<1e-8 and d['Y_bound_violation']<1e-8 and d['Y_inlet_Dirichlet_error']<1e-12 and d['Y_reservoir_undershoot']<1e-8 and d['temporal_negative_increment_fraction']<.01 and d['spatial_positive_increment_fraction']<.05)
def self_test():
    ri=[];sl=[];ti=[]
    for r in range(2):
        for t in range(3):
            for g in range(2):ri.append(r);ti.append(t);sl.append(g)
    ri=np.array(ri);sl=np.array(sl);ti=np.array(ti);a,b=pairs(np.arange(len(ri)),ri,sl,ti)
    if len(a)!=8 or not np.all(ri[a]==ri[b]) or not np.all(sl[a]==sl[b]) or not np.all(ti[b]-ti[a]==1): raise RuntimeError('pair_selftest')
    print('POSTV16-AV2-A4 training/OOD execution self-test: PASS')

def main(root,drive):
    import tensorflow as tf
    gates={};stage='preflight';training=False;ckf=False;oodopen=False;oodteacher=False;oodeval=False
    out=drive/OUTREL; fail=drive/FAILREL; blocked=drive/BLOCKREL; ck=out/CHECKPOINT; ckfr=out/CKFREEZE; marker=out/OODMARK
    def gate(n,p,v=None):
        ok=bool(p);gates[n]={'passed':ok,'value':v};print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f' — {v}' if v is not None else ''))
        if not ok:raise GateError(n)
    def sg(n,p,v=None):
        ok=bool(p);gates[n]={'passed':ok,'value':v,'scientific_execution_gate':True};print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f' — {v}' if v is not None else ''))
        if not ok:raise ScientificFail(n,v)
    print('='*180);print('POSTV16-AV2-A4 — VARIABLE-POROSITY PI-RNN TRAINING + BEST-VALIDATION CHECKPOINT + ONE-TOUCH LOCKED-OOD');print('='*180)
    print('NO OOD Y UNTIL CHECKPOINT IS FROZEN. NO POST-OOD TRAINING/RETUNING/RESELECTION. OOD METRICS ARE DESCRIPTIVE. NO MAPBACK. NO CMG.\n')
    try:
        root=root.resolve();drive=drive.resolve();gate('repository_parent_is_AV2A3',git(root,'rev-parse','HEAD^')==PARENT,git(root,'rev-parse','HEAD^'));gate('repository_clean',git(root,'status','--porcelain')=='',repr(git(root,'status','--porcelain')))
        for fn,e in SOURCES.items():
            p=root/fn; a=blob(p,root) if p.is_file() else 'missing';gate(Path(fn).stem+'_git_blob_exact',a==e,a)
        gate('no_prior_locked_OOD_marker',not marker.exists(),str(marker))
        stage='A3_binding';a3=drive/A3REL;gate('A3_output_present',a3.is_dir(),str(a3));m3=vman(a3,A3_MAN);gate('A3_manifest_SHA_closure',True,len(m3));s3=lj(a3/A3_SUM);pr=lj(a3/A3_PROTOCOL);dec=lj(a3/A3_DEC)
        gate('A3_status_exact',s3['status']==A3_STATUS,s3['status']);gate('A4_authorized',dec['next']['authorized'] is True and dec['next']['milestone']=='POSTV16-AV2-A4');gate('A3_OOD_Y_not_generated',s3['LOCKED_OOD_target_generated'] is False);gate('A3_architecture_exact',pr['architecture']['input_nodes']==201 and pr['architecture']['input_channels']==9 and pr['architecture']['hidden_units']==64 and pr['architecture']['lstm_layers']==2);gate('A3_lambda_phys_exact',float(pr['physics_loss']['lambda_phys'])==.01)
        with np.load(a3/A3_TV,allow_pickle=False) as z:
            X=np.asarray(z['X_required_9'],np.float32);Y=np.asarray(z['Y_transport'],np.float32);ri=np.asarray(z['realization_index'],int);ti=np.asarray(z['time_index'],int);sl=np.asarray(z['streamline_index'],int);part=np.asarray(z['partition_code'],np.int8);eta=np.asarray(z['target_eta_sequence'],np.float32);daytv=np.asarray(z['target_time_days'],np.float32)
        gate('trainval_shapes',X.shape==(29106,201,9) and Y.shape==(29106,201),(X.shape,Y.shape))
        with np.load(a3/A3_OOD,allow_pickle=False) as z:
            gate('OOD_Y_key_absent','Y_transport' not in z.files,sorted(z.files));Xo=np.asarray(z['X_required_9'],np.float32);rio=np.asarray(z['realization_index'],int);tio=np.asarray(z['time_index'],int);slo=np.asarray(z['streamline_index'],int);etao=np.asarray(z['target_eta_sequence'],np.float32);dayo=np.asarray(z['target_time_days'],np.float32)
        gate('OOD_X_shape',Xo.shape==(9702,201,9),Xo.shape)
        with np.load(a3/A3_PH,allow_pickle=False) as z:Mall=np.asarray(z['metric_M'],np.float32);phiall=np.asarray(z['porosity_sequence'],np.float32)
        gate('physics_sidecar_shapes',Mall.shape==(4,1078,201) and phiall.shape==(4,1078,201),(Mall.shape,phiall.shape))
        with np.load(a3/A3_NORM,allow_pickle=False) as z:
            fr=np.asarray(z['fit_realizations']).astype(str).tolist();vu=bool(np.asarray(z['validation_used_for_fit']).reshape(-1)[0]);ou=bool(np.asarray(z['locked_OOD_used_for_fit']).reshape(-1)[0])
        gate('normalization_TRAIN_only',fr==['AV2PHI0001','AV2PHI0002'] and not vu and not ou,dict(fit=fr,val=vu,ood=ou))
        stage='pairs';train=np.flatnonzero(part==0);val=np.flatnonzero(part==1);ta,tb=pairs(train,ri,sl,ti);va,vb=pairs(val,ri,sl,ti)
        sg('TRAIN_pairs_17248',len(ta)==17248,len(ta));sg('VAL_pairs_8624',len(va)==8624,len(va));sg('TRAIN_pair_identity',np.all(ri[ta]==ri[tb]) and np.all(sl[ta]==sl[tb]) and np.all(ti[tb]-ti[ta]==1));sg('VAL_pair_identity',np.all(ri[va]==ri[vb]) and np.all(sl[va]==sl[vb]) and np.all(ti[vb]-ti[va]==1))
        def model():
            i=tf.keras.Input((201,9),name='v16_required_sequence');x=tf.keras.layers.LSTM(64,return_sequences=True,name='lstm_1')(i);x=tf.keras.layers.LSTM(64,return_sequences=True,name='lstm_2')(x);x=tf.keras.layers.TimeDistributed(tf.keras.layers.Dense(1),name='td_dense')(x);x=tf.keras.layers.Activation('sigmoid',name='bounded_sigmoid')(x);x=tf.keras.layers.Rescaling(.6,offset=.2,name='bounded_saturation')(x);o=tf.keras.layers.Reshape((201,),name='Sw_sequence')(x);return tf.keras.Model(i,o,name='PAD_Stream_AV2_A4')
        def fw(S):
            se=tf.clip_by_value((S-.2)/.6,0.,1.);krw=.8*se**2;kro=.8*(1-se)**2;lw=krw/.5;lo=kro/5.;return lw/(lw+lo+1e-12)
        def ds(S):
            se=tf.clip_by_value((S-.2)/.6,1e-7,1-1e-7);return (se*(1-se))**2/(.25**2)
        def ploss(Sa,Sb,ea,eb,M,phi):
            Sm=.5*(Sa+Sb);deta=tf.maximum(eb-ea,1e-8);dt=(Sb-Sa)/deta[:,None];h=1./200.;f=fw(Sm);adv=(f[:,2:]-f[:,:-2])/(2*h);dSf=(Sm[:,1:]-Sm[:,:-1])/h;Mf=2*M[:,:-1]*M[:,1:]/tf.maximum(M[:,:-1]+M[:,1:],1e-12);G=ds(.5*(Sm[:,:-1]+Sm[:,1:]))*Mf*dSf;cap=M[:,1:-1]*(G[:,1:]-G[:,:-1])/h;R=dt[:,1:-1]+adv-(phi[:,1:-1]/22.)*cap;return tf.reduce_mean(tf.square(R))
        Mt=tf.convert_to_tensor(Mall,tf.float32);Pt=tf.convert_to_tensor(phiall,tf.float32)
        def side(a):
            idx=tf.stack([tf.convert_to_tensor(ri[a],tf.int32),tf.convert_to_tensor(sl[a],tf.int32)],1);return tf.gather_nd(Mt,idx),tf.gather_nd(Pt,idx)
        try:tf.config.experimental.enable_op_determinism()
        except Exception:pass
        tf.keras.utils.set_random_seed(SEED);m=model();sg('model_parameter_count_52033',m.count_params()==52033,m.count_params());opt=tf.keras.optimizers.Adam(LR);training=True;tmp=Path(tempfile.mkdtemp(prefix='AV2A4_'))/CHECKPOINT
        best=np.inf;bestep=None;esbest=np.inf;wait=lrwait=0;hist=[];rng=np.random.default_rng(SEED);stage='training'
        for ep in range(1,MAXEP+1):
            order=rng.permutation(len(ta));TD=[];TP=[];TT=[]
            for st in range(0,len(order),BATCH):
                z=order[st:st+BATCH];a=ta[z];b=tb[z]
                with tf.GradientTape() as tape:
                    Sa=m(X[a],training=True);Sb=m(X[b],training=True);ld=.5*(tf.reduce_mean((Sa-Y[a])**2)+tf.reduce_mean((Sb-Y[b])**2));ea=tf.reduce_mean(eta[a],1);eb=tf.reduce_mean(eta[b],1);M,ph=side(a);lp=ploss(Sa,Sb,ea,eb,M,ph);loss=ld+.01*lp
                gr=tape.gradient(loss,m.trainable_variables);opt.apply_gradients(zip(gr,m.trainable_variables));TD.append(float(ld));TP.append(float(lp));TT.append(float(loss))
            VD=[];VP=[];VT=[]
            for st in range(0,len(va),BATCH):
                a=va[st:st+BATCH];b=vb[st:st+BATCH];Sa=m(X[a],training=False);Sb=m(X[b],training=False);ld=.5*(tf.reduce_mean((Sa-Y[a])**2)+tf.reduce_mean((Sb-Y[b])**2));ea=tf.reduce_mean(eta[a],1);eb=tf.reduce_mean(eta[b],1);M,ph=side(a);lp=ploss(Sa,Sb,ea,eb,M,ph);tot=ld+.01*lp;VD.append(float(ld));VP.append(float(lp));VT.append(float(tot))
            trd,trp,trt=map(float,map(np.mean,(TD,TP,TT)));vld,vlp,vlt=map(float,map(np.mean,(VD,VP,VT)));lr=float(opt.learning_rate.numpy());sg(f'epoch_{ep:03d}_finite',np.all(np.isfinite([trd,trp,trt,vld,vlp,vlt])),dict(train=trt,val=vlt));hist.append([ep,trd,trp,trt,vld,vlp,vlt,lr])
            if vlt<best:best=vlt;bestep=ep;m.save(tmp,overwrite=True);lrwait=0
            else:lrwait+=1
            if vlt<esbest-MDELTA:esbest=vlt;wait=0
            else:wait+=1
            if lrwait>=LRPAT:opt.learning_rate.assign(max(float(opt.learning_rate.numpy())*.5,MINLR));lrwait=0
            print(f'Epoch {ep:03d}: loss={trt:.6e} data={trd:.6e} phys={trp:.6e} val={vlt:.6e} val_data={vld:.6e} val_phys={vlp:.6e} lr={float(opt.learning_rate.numpy()):.3e}')
            if wait>=PAT:print(f'Early stopping at epoch {ep}; best={best:.9e} epoch={bestep}');break
        sg('best_checkpoint_created',tmp.is_file(),str(tmp));sg('best_validation_finite',np.isfinite(best),best)
        stage='checkpoint_freeze';out.mkdir(parents=True,exist_ok=True)
        if ck.exists():raise GateError('checkpoint_preexists')
        shutil.copy2(tmp,ck);cksha=sha(ck);bestm=tf.keras.models.load_model(ck);Vp=bestm.predict(X[val],batch_size=BATCH,verbose=0).astype(float);Vt=Y[val].astype(float);vm=met(Vp,Vt);vs=struct(Vp,ti[val],sl[val]);VD=[];VP=[];VT=[]
        for st in range(0,len(va),BATCH):
            a=va[st:st+BATCH];b=vb[st:st+BATCH];Sa=bestm(X[a],training=False);Sb=bestm(X[b],training=False);ld=.5*(tf.reduce_mean((Sa-Y[a])**2)+tf.reduce_mean((Sb-Y[b])**2));ea=tf.reduce_mean(eta[a],1);eb=tf.reduce_mean(eta[b],1);M,ph=side(a);lp=ploss(Sa,Sb,ea,eb,M,ph);VD.append(float(ld));VP.append(float(lp));VT.append(float(ld+.01*lp))
        vobj=dict(data=float(np.mean(VD)),physics=float(np.mean(VP)),total=float(np.mean(VT)));freeze=dict(milestone=MILESTONE,protocol_id=PROTOCOL_ID,checkpoint_file=CHECKPOINT,checkpoint_sha256=cksha,best_epoch=int(bestep),epochs_completed=len(hist),best_validation_total_objective_during_training=float(best),frozen_checkpoint_validation_objective=vobj,frozen_checkpoint_validation_predictive_metrics=vm,frozen_checkpoint_validation_structural_metrics=vs,LOCKED_OOD_target_generated_at_freeze_time=False,LOCKED_OOD_target_opened_at_freeze_time=False,optimizer_updates_after_this_freeze_authorized=False,checkpoint_reselection_after_this_freeze_authorized=False,normalization_refit_after_this_freeze_authorized=False,architecture_or_loss_change_after_this_freeze_authorized=False);ckfr.write_bytes(jb(freeze));ckf=True;sg('checkpoint_frozen_before_OOD',ckfr.is_file() and sha(ck)==cksha,cksha)
        rows=[dict(epoch=int(r[0]),train_data=r[1],train_phys=r[2],train_total=r[3],val_data=r[4],val_phys=r[5],val_total=r[6],learning_rate=r[7]) for r in hist];pub(out,{'POSTV16_AV2_A4_Training_History.csv':cb(rows),'POSTV16_AV2_A4_Validation_Predictions_Before_OOD.npz':npzb(dict(sample_indices=val,Y_true=Vt,Y_pred=Vp,time_index=ti[val],streamline_index=sl[val],target_time_days=daytv[val]))})
        stage='OOD_open';marker.write_text(f'POSTV16-AV2-A4 LOCKED OOD OPENED\ncheckpoint_sha256={cksha}\nretraining_after_marker=false\n');oodopen=True;sg('OOD_open_only_after_checkpoint_freeze',ckf and marker.is_file())
        stage='OOD_teacher';a2d=drive/A2REL;gate('A2_output_present',a2d.is_dir(),str(a2d));m2=vman(a2d,A2_MAN);gate('A2_manifest_SHA_closure',True,len(m2));oo=a2d/A2_OOD;gate('OOD_A2_artifact_manifested',A2_OOD in m2 and oo.is_file() and sha(oo)==m2[A2_OOD])
        with np.load(oo,allow_pickle=False) as z:xyz=np.asarray(z['streamline_xyz_m'],float);tof=np.asarray(z['pollock_tof_s'],float)
        a3m=mod(root/A3,'av2a4_a3');op=a3m.build_operator_geometry(xyz,tof);Mo=np.asarray(Mall[3],float);pho=np.asarray(phiall[3],float);sg('OOD_metric_matches_A3_sidecar',np.allclose(op['metric_M'],Mo,rtol=1e-12,atol=1e-12),float(np.max(np.abs(op['metric_M']-Mo))));Y3,tdiag=a3m.generate_teacher(pho,op,DAYS);oodteacher=True;sg('OOD_teacher_certified',teacher_ok(tdiag),tdiag);sg('OOD_Y_shape',Y3.shape==(9,1078,201),Y3.shape);Yo=Y3.reshape(9702,201).astype(float)
        stage='OOD_eval';Po=bestm.predict(Xo,batch_size=BATCH,verbose=0).astype(float);oodeval=True;sg('OOD_predictions_finite',np.isfinite(Po).all());sg('OOD_predictions_bounded',Po.min()>=.2-1e-6 and Po.max()<=.8+1e-6,[float(Po.min()),float(Po.max())]);om=met(Po,Yo);os=struct(Po,tio,slo);oa,ob=pairs(np.arange(len(Xo)),rio,slo,tio);sg('OOD_pairs_8624',len(oa)==8624,len(oa));Moot=tf.convert_to_tensor(Mo,tf.float32);Poot=tf.convert_to_tensor(pho,tf.float32);OP=[]
        for st in range(0,len(oa),BATCH):
            a=oa[st:st+BATCH];b=ob[st:st+BATCH];Sa=tf.convert_to_tensor(Po[a],tf.float32);Sb=tf.convert_to_tensor(Po[b],tf.float32);ea=tf.reduce_mean(etao[a],1);eb=tf.reduce_mean(etao[b],1);M=tf.gather(Moot,slo[a]);ph=tf.gather(Poot,slo[a]);OP.append(float(ploss(Sa,Sb,ea,eb,M,ph)))
        ophys=float(np.mean(OP));by=[]
        for d in DAYS:
            q=np.isclose(dayo,d);by.append(dict(target_day=float(d),**met(Po[q],Yo[q])))
        gen=dict(validation=vm,locked_OOD=om,OOD_to_validation_RMSE_ratio=om['rmse']/max(vm['rmse'],1e-300),OOD_to_validation_MAE_ratio=om['mae']/max(vm['mae'],1e-300),validation_structural=vs,locked_OOD_structural=os,locked_OOD_physics_residual_MSE=ophys,scientific_rule='Descriptive one-touch OOD evidence. No post-hoc accuracy threshold, model reselection, or retuning is authorized.')
        for n in ['no_post_OOD_training','no_post_OOD_checkpoint_reselection','no_post_OOD_normalization_refit','no_post_OOD_hyperparameter_retuning','no_second_OOD_evaluation','no_mapback','no_CMG']:gate(n,True)
        dec4=dict(milestone=MILESTONE,status=STATUS_PASS,protocol_id=PROTOCOL_ID,training_protocol_executed_exactly=True,best_validation_checkpoint_frozen_before_OOD=True,checkpoint_sha256=cksha,best_epoch=int(bestep),epochs_completed=len(hist),locked_OOD_opened_after_checkpoint_freeze=True,locked_OOD_teacher_generated_once=True,locked_OOD_evaluated_once=True,post_OOD_training=False,post_OOD_reselection=False,post_OOD_retuning=False,post_OOD_normalization_refit=False,OOD_accuracy_threshold_gate=False,reason_no_OOD_accuracy_gate='Frozen A3/C26 lineage specifies one-touch locked evaluation and validation-only selection but no predeclared OOD accuracy threshold; A4 therefore freezes OOD metrics descriptively rather than inventing a post-hoc gate.',variable_phi_predictive_generalization_claim=False,mapback_performed=False,CMG_validation_performed=False,A5_integration_authorized=True,next=dict(milestone='POSTV16-AV2-A5',name='Frozen AV2 Checkpoint Deployment, Local-Pore-Volume Capacity Integration, and R7D Terminal-Halo Reconstruction',authorized=True,scope='Integration/deployment only; A4 OOD metrics remain frozen and may not be used to retune the checkpoint.'))
        summary=dict(milestone=MILESTONE,status=STATUS_PASS,protocol_id=PROTOCOL_ID,checkpoint_sha256=cksha,best_epoch=int(bestep),epochs_completed=len(hist),best_validation_total_objective=float(best),validation_metrics=vm,validation_objective=vobj,locked_OOD_teacher_certified=True,locked_OOD_teacher_diagnostics=tdiag,locked_OOD_metrics=om,locked_OOD_physics_residual_MSE=ophys,locked_OOD_structural_metrics=os,OOD_accuracy_gate_applied=False,training_after_OOD=False,reselection_after_OOD=False,retuning_after_OOD=False,mapback=False,CMG_validation=False,next=dec4['next'])
        pub(out,{'PAD_Stream_POSTV16_AV2_A4_Summary.json':jb(summary),'POSTV16_AV2_A4_LockedOOD_Truth_and_Predictions.npz':npzb(dict(Y_true=Yo,Y_pred=Po,target_time_days=dayo,time_index=tio,streamline_index=slo,realization_index=rio,checkpoint_sha256=np.asarray(cksha))),'POSTV16_AV2_A4_LockedOOD_Predictive_Metrics_By_Time.csv':cb(by),'POSTV16_AV2_A4_LockedOOD_Generalization_Evidence.json':jb(gen),'POSTV16_AV2_A4_Decision_Contract.json':jb(dec4),'POSTV16_AV2_A4_Final_Gate_Matrix.csv':cb([dict(gate=k,**v) for k,v in gates.items()])})
        mr=[]
        for q in sorted(out.iterdir()):
            if q.is_file() and q.name!='POSTV16_AV2_A4_Artifact_Manifest.csv':mr.append(dict(file=q.name,sha256=sha(q),bytes=q.stat().st_size))
        pub(out,{'POSTV16_AV2_A4_Artifact_Manifest.csv':cb(mr)})
        print('\n'+'='*180);print('POSTV16-AV2-A4: PASS');print('='*180);print('Status:',STATUS_PASS);print('Epochs / best epoch:',len(hist),'/',bestep);print('Best validation total:',f'{best:.9e}');print('Checkpoint SHA256:',cksha);print('Validation RMSE / MAE:',f"{vm['rmse']:.9e} / {vm['mae']:.9e}");print('Locked OOD RMSE / MAE:',f"{om['rmse']:.9e} / {om['mae']:.9e}");print('OOD/validation RMSE ratio:',f"{gen['OOD_to_validation_RMSE_ratio']:.6f}");print('Locked OOD physics residual MSE:',f'{ophys:.9e}');print('OOD accuracy threshold applied: False — descriptive frozen evidence');print('Post-OOD training/reselection/retuning: False / False / False');print('NEXT: POSTV16-AV2-A5');print('='*180);return 0
    except ScientificFail as e:
        fail.mkdir(parents=True,exist_ok=True);r=dict(milestone=MILESTONE,status=STATUS_FAIL,failed_stage=stage,failed_gate=e.g,detail=e.d,gates=gates,training_started=training,checkpoint_frozen=ckf,LOCKED_OOD_opened=oodopen,LOCKED_OOD_teacher_generated=oodteacher,LOCKED_OOD_evaluated=oodeval,post_OOD_retuning_authorized=False,second_OOD_evaluation_authorized=False,mapback=False,CMG_validation=False,next_milestone_authorized=False,next_action='Freeze and interpret A4 failure. If OOD was opened, do not retrain, reselect, retune, or repeat OOD evaluation.');d=jb(r);q=fail/'POSTV16_AV2_A4_Scientific_Fail_Report.json';q.write_bytes(d) if not q.exists() else None;print('\nPOSTV16-AV2-A4: SCIENTIFIC FAIL',e.g,e.d);return 3
    except Exception as e:
        blocked.mkdir(parents=True,exist_ok=True);r=dict(milestone=MILESTONE,status=STATUS_BLOCKED,failed_stage=stage,exception=repr(e),gates=gates,training_started=training,checkpoint_frozen=ckf,LOCKED_OOD_opened=oodopen,LOCKED_OOD_teacher_generated=oodteacher,LOCKED_OOD_evaluated=oodeval,post_OOD_retuning_authorized=False,second_OOD_evaluation_authorized=False,next_milestone_authorized=False,next_action='Audit only technical failure. If OOD-open marker exists, do not rerun A4 without explicit failure-closure protocol.');d=jb(r);q=blocked/'POSTV16_AV2_A4_Blocked_Report.json';q.write_bytes(d) if not q.exists() else None;print('\nPOSTV16-AV2-A4: BLOCKED',stage,repr(e));return 2

def parse():
    p=argparse.ArgumentParser();p.add_argument('--project-root',type=Path,default=Path('.'));p.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'));p.add_argument('--self-test',action='store_true');return p.parse_args()
if __name__=='__main__':
    a=parse()
    if a.self_test:self_test();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
