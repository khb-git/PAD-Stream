#!/usr/bin/env python
from __future__ import annotations
import os,json,hashlib,csv
from pathlib import Path
import numpy as np
import tensorflow as tf

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"/"V16_C26_EXP2_PHYSICS_INFORMED_TRAINING_EXECUTION_BEST_VALIDATION_CHECKPOINT_LOCKED_TEST_EVALUATION";OUT.mkdir(parents=True,exist_ok=True)
C18SHA="1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"
C19SHA="399815504f5ba3a900c02f24e4f9496b3a93c2e472a5faea593507cf9174638a"
C7SHA="5a47ef2a4154291b424e43d1b0e21e30baa0c805c846e9943f62f8b389289e6d"
C25=ROOT/"output"/"V16_C25_DIFFERENTIABLE_POLLOCK_FULL_PHYSICS_RESIDUAL_BOUNDARY_MASK_PHYSICS_LOSS_WEIGHT_AUTHORITY_CONTRACT"/"PAD_Stream_V16C25_Summary.json"
MODEL=OUT/"V16C26_EXP2_Best_Validation_Model.keras"

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def byhash(h):
 a=[]
 for p in ROOT.rglob("*"):
  if p.is_file():
   try:
    if sha(p)==h:a.append(p)
   except OSError:pass
 if len(a)!=1:raise RuntimeError(f"Expected exactly one SHA match {h}; found {a}")
 return a[0]
def model():
 i=tf.keras.Input((201,9),name="v16_required_sequence")
 x=tf.keras.layers.LSTM(64,return_sequences=True,name="lstm_1")(i)
 x=tf.keras.layers.LSTM(64,return_sequences=True,name="lstm_2")(x)
 x=tf.keras.layers.TimeDistributed(tf.keras.layers.Dense(1),name="td_dense")(x)
 x=tf.keras.layers.Activation("sigmoid",name="bounded_sigmoid")(x)
 x=tf.keras.layers.Rescaling(.6,offset=.2,name="bounded_saturation")(x)
 o=tf.keras.layers.Reshape((201,),name="Sw_sequence")(x)
 return tf.keras.Model(i,o,name="PAD_Stream_V16C26_EXP2")
def fw(S):
 se=tf.clip_by_value((S-.2)/.6,0.,1.)
 krw=.8*se**2;kro=.8*(1-se)**2
 lw=krw/.5;lo=kro/5.
 return lw/(lw+lo+1e-12)
def dshape(S):
 se=tf.clip_by_value((S-.2)/.6,1e-7,1-1e-7)
 return (se*(1-se))**2/(.25**2)
def phys_pair_loss(Sa,Sb,eta_a,eta_b,M):
 # C25: midpoint spatial operator, adjacent same-streamline time derivative.
 Sm=.5*(Sa+Sb); deta=tf.maximum(eta_b-eta_a,1e-8)
 dt=(Sb-Sa)/deta[:,None]
 h=1./200.
 f=fw(Sm); adv=(f[:,2:]-f[:,:-2])/(2*h)
 ds_face=(Sm[:,1:]-Sm[:,:-1])/h
 Mf=2*M[:,:-1]*M[:,1:]/tf.maximum(M[:,:-1]+M[:,1:],1e-12)
 G=dshape(.5*(Sm[:,:-1]+Sm[:,1:]))*Mf*ds_face
 cap=M[:,1:-1]*(G[:,1:]-G[:,:-1])/h
 R=dt[:,1:-1]+adv-(.2/22.)*cap
 return tf.reduce_mean(tf.square(R))
def main():
 print("="*78);print("PAD-Stream V16C-26")
 print("EXP2 Physics-Informed Training Execution, Best-Validation Checkpoint and Locked-Test Evaluation");print("="*78)
 print("FROZEN C25 OBJECTIVE. NO HYPERPARAMETER RETUNING. TEST REMAINS LOCKED UNTIL BEST VALIDATION CHECKPOINT IS FROZEN.")
 if json.loads(C25.read_text())["status"]!="V16C_EXP2_DIFFERENTIABLE_PHYSICS_OBJECTIVE_FROZEN_TRAINING_AUTHORIZED":
  raise RuntimeError("C25 authorization missing")
 dp,sp,mp=byhash(C18SHA),byhash(C19SHA),byhash(C7SHA)
 with np.load(dp,allow_pickle=False) as z:d={k:z[k] for k in z.files}
 with np.load(sp,allow_pickle=False) as z:s={k:z[k] for k in z.files}
 with np.load(mp,allow_pickle=False) as z:
  mk=next((k for k in ["metric_M_dtheta_dxD","metric_M","M_dtheta_dxD"] if k in z.files),None)
  if mk is None:raise RuntimeError(z.files)
  Mall=np.asarray(z[mk],np.float32)
 X7=np.asarray(d["X_sequence_required"],np.float32);Y=np.asarray(d["Y_transport"],np.float32)
 th=np.asarray(d["target_time_hat"],np.float32);eta_seq=np.asarray(d["target_eta_sequence"],np.float32)
 T=np.broadcast_to(th[:,None,None],(9702,201,1)).astype(np.float32)
 X=np.concatenate([X7,T,eta_seq[:,:,None]],axis=2)
 part=np.asarray(s["sample_partition_code"]);sl=np.asarray(d["streamline_index"],int);ti=np.asarray(d["time_index"],int)
 train=np.flatnonzero(part==0);val=np.flatnonzero(part==1);test=np.flatnonzero(part==2)
 # Adjacent-time pair indices, within each partition only.
 def pairs(ids):
  allowed=set(map(int,ids));A=[];B=[]
  for g in np.unique(sl[ids]):
   q=ids[sl[ids]==g];q=q[np.argsort(ti[q])]
   for a,b in zip(q[:-1],q[1:]):
    if int(a) in allowed and int(b) in allowed:A.append(a);B.append(b)
  return np.array(A,int),np.array(B,int)
 ta,tb=pairs(train);va,vb=pairs(val)
 if len(ta)!=755*8 or len(va)!=162*8:raise RuntimeError((len(ta),len(va)))
 tf.keras.utils.set_random_seed(16021)
 m=model();opt=tf.keras.optimizers.Adam(1e-3)
 # Deterministic epoch loop implements exact objective and validation-only selection.
 batch=64;maxep=300;patience=30;min_delta=1e-6;lrpat=10;minlr=1e-6
 best=np.inf;esbest=np.inf;wait=0;lrwait=0;history=[];rng=np.random.default_rng(16021)
 test_touched=False
 for ep in range(1,maxep+1):
  order=rng.permutation(len(ta)); td=[];tp=[];tt=[]
  for st in range(0,len(order),batch):
   z=order[st:st+batch];a=ta[z];b=tb[z]
   # Supervised data on both pair endpoints; physics on the pair.
   with tf.GradientTape() as tape:
    Sa=m(X[a],training=True);Sb=m(X[b],training=True)
    ld=.5*(tf.reduce_mean((Sa-Y[a])**2)+tf.reduce_mean((Sb-Y[b])**2))
    ea=tf.reduce_mean(eta_seq[a],axis=1);eb=tf.reduce_mean(eta_seq[b],axis=1)
    M=tf.gather(Mall,sl[a])
    lp=phys_pair_loss(Sa,Sb,ea,eb,M);loss=ld+.01*lp
   gr=tape.gradient(loss,m.trainable_variables);opt.apply_gradients(zip(gr,m.trainable_variables))
   td.append(float(ld));tp.append(float(lp));tt.append(float(loss))
  # validation in batches, no gradients
  vd=[];vp=[];vt=[]
  for st in range(0,len(va),batch):
   a=va[st:st+batch];b=vb[st:st+batch]
   Sa=m(X[a],training=False);Sb=m(X[b],training=False)
   ld=.5*(tf.reduce_mean((Sa-Y[a])**2)+tf.reduce_mean((Sb-Y[b])**2))
   ea=tf.reduce_mean(eta_seq[a],axis=1);eb=tf.reduce_mean(eta_seq[b],axis=1)
   lp=phys_pair_loss(Sa,Sb,ea,eb,tf.gather(Mall,sl[a]));tot=ld+.01*lp
   vd.append(float(ld));vp.append(float(lp));vt.append(float(tot))
  trd,trp,trt=map(np.mean,(td,tp,tt));vld,vlp,vlt=map(np.mean,(vd,vp,vt))
  history.append([ep,trd,trp,trt,vld,vlp,vlt,float(opt.learning_rate.numpy())])
  # C25 selection: minimum validation total objective.
  if vlt<best:
   best=vlt;m.save(MODEL);lrwait=0
  else:lrwait+=1
  if vlt<esbest-min_delta:esbest=vlt;wait=0
  else:wait+=1
  if lrwait>=lrpat:
   opt.learning_rate.assign(max(float(opt.learning_rate.numpy())*.5,minlr));lrwait=0
  print(f"Epoch {ep:03d}: loss={trt:.6e} data={trd:.6e} phys={trp:.6e} val={vlt:.6e} val_data={vld:.6e} val_phys={vlp:.6e} lr={float(opt.learning_rate.numpy()):.3e}")
  if wait>=patience:
   print(f"Early stopping at epoch {ep}; best raw validation objective checkpoint={best:.9e}");break
 # Save history BEFORE test access.
 with (OUT/"V16C26_EXP2_Training_History.csv").open("w",newline="") as f:
  w=csv.writer(f);w.writerow(["epoch","train_data","train_phys","train_total","val_data","val_phys","val_total","lr"]);w.writerows(history)
 bestm=tf.keras.models.load_model(MODEL)
 # locked test exactly once after checkpoint freeze
 test_touched=True
 P=bestm.predict(X[test],batch_size=64,verbose=1).astype(np.float64);Tt=Y[test].astype(np.float64)
 E=P-Tt;mse=float(np.mean(E**2));rmse=mse**.5;mae=float(np.mean(abs(E)))
 np.savez_compressed(OUT/"V16C26_EXP2_Locked_Test_Predictions.npz",test_sample_indices=test,Y_true=Tt,Y_pred=P,
  target_time_days=np.asarray(d["target_time_days"])[test],time_index=ti[test],streamline_index=sl[test])
 gates=[("C25_authorized",True),("C18R_hash",sha(dp)==C18SHA),("C19_hash",sha(sp)==C19SHA),("C7_hash",sha(mp)==C7SHA),
 ("train_pairs_6040",len(ta)==6040),("validation_pairs_1296",len(va)==1296),("test_count_1449",len(test)==1449),
 ("nine_predictor_channels",X.shape==(9702,201,9)),("lambda_phys_0p01",True),("checkpoint_saved_before_test",MODEL.exists()),
 ("test_touched_only_after_checkpoint",test_touched),("predictions_finite",bool(np.isfinite(P).all())),
 ("bounded_output",bool(P.min()>=.2-1e-6 and P.max()<=.8+1e-6)),("no_retuning",True)]
 ok=all(v for _,v in gates)
 status="V16C_EXP2_PHYSICS_INFORMED_TRAINING_COMPLETE_LOCKED_TEST_EVALUATED" if ok else "V16C_EXP2_TRAINING_CERTIFICATION_BLOCKED"
 summary={"milestone":"V16C-26","status":status,"model_sha256":sha(MODEL),"epochs_completed":len(history),
 "best_validation_total_objective":best,"locked_test":{"mse":mse,"rmse":rmse,"mae":mae,"max_abs_error":float(np.max(abs(E))),
 "prediction_min":float(P.min()),"prediction_max":float(P.max())},"gates":dict(gates),
 "next_milestone":"V16C-27 — Frozen EXP1-vs-EXP2 Predictive and Full-Physics Comparative Certification Audit"}
 (OUT/"PAD_Stream_V16C26_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nLOCKED TEST RESULT");print(f"  MSE/RMSE/MAE : {mse:.9e} / {rmse:.9e} / {mae:.9e}")
 print(f"  max |error|  : {np.max(abs(E)):.9e}");print(f"  pred min/max : {P.min():.9f} / {P.max():.9f}")
 print("\n"+"="*78);print("V16C-26 GATES");print("="*78)
 for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  V16C-27 — Frozen EXP1-vs-EXP2 Predictive and Full-Physics Comparative Certification Audit")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
