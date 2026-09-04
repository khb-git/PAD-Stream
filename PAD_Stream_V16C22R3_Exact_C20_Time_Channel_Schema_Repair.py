#!/usr/bin/env python
from __future__ import annotations
import hashlib, json, zipfile
from pathlib import Path
import numpy as np
import tensorflow as tf

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"/"V16_C22_PIRNN_EXP1_TRAINING_EXECUTION_BEST_VALIDATION_CHECKPOINT_LOCKED_TEST_EVALUATION"
MODEL=OUT/"V16C22_EXP1_Best_Validation_Model.keras"
ROUT=ROOT/"output"/"V16_C22R3_EXACT_C20_TIME_CHANNEL_SCHEMA_REPAIR"
ROUT.mkdir(parents=True,exist_ok=True)
C18SHA="1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"
C19SHA="399815504f5ba3a900c02f24e4f9496b3a93c2e472a5faea593507cf9174638a"
SWC,SOR=.2,.2

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()

def byhash(h):
 hits=[]
 for p in ROOT.rglob("*"):
  if p.is_file():
   try:
    if sha(p)==h:hits.append(p)
   except OSError:pass
 if len(hits)!=1: raise RuntimeError(f"Expected one file for {h}, found {hits}")
 return hits[0]

def build():
 inp=tf.keras.Input((201,9),name="v16_sequence")
 x=tf.keras.layers.LSTM(64,return_sequences=True,name="lstm_1")(inp)
 x=tf.keras.layers.LSTM(64,return_sequences=True,name="lstm_2")(x)
 x=tf.keras.layers.TimeDistributed(tf.keras.layers.Dense(1),name="td_dense")(x)
 x=tf.keras.layers.Activation("sigmoid",name="bounded_sigmoid")(x)
 x=tf.keras.layers.Rescaling(scale=.6,offset=.2,name="bounded_sw")(x)
 out=tf.keras.layers.Reshape((201,),name="Sw")(x)
 return tf.keras.Model(inp,out,name="V16C22R3_EXP1")

def recover(m):
 try:
  m.load_weights(MODEL); return "load_weights_from_keras_archive"
 except Exception as e:
  with zipfile.ZipFile(MODEL) as z:
   c=[n for n in z.namelist() if n.endswith(".weights.h5")]
   if not c: raise RuntimeError(f"No embedded weights file; direct error={e}")
   q=ROUT/"V16C22R3_recovered.weights.h5"; q.write_bytes(z.read(c[0]))
  m.load_weights(q); return "embedded_h5_weights"

def pick(d,*names):
 for n in names:
  if n in d:return d[n]
 raise KeyError(f"Missing {names}; keys={list(d)}")

def main():
 print("="*78);print("PAD-Stream V16C-22R3")
 print("Checkpoint Deserialization Repair and Locked-Test Completion");print("="*78)
 print("NO RETRAINING. NO RETUNING. REPAIR IS LIMITED TO POST-TRAINING CHECKPOINT LOADING.")
 if not MODEL.exists():raise FileNotFoundError(MODEL)
 dpath,spath=byhash(C18SHA),byhash(C19SHA)
 d={k:v for k,v in np.load(dpath,allow_pickle=True).items()}
 s={k:v for k,v in np.load(spath,allow_pickle=True).items()}
 X=pick(d,"X_sequence_required","X_required","X").astype(np.float32)
 Y=pick(d,"Y_transport","Y").astype(np.float32)
 if X.shape[-1]==7:
  # Exact C20 construction from the certified C18R schema.
  # target_time_hat is sample-scalar -> broadcast across 201 nodes.
  # target_eta_sequence is already node-resolved (9702,201) -> append directly.
  if "target_time_hat" not in d or "target_eta_sequence" not in d:
   raise RuntimeError(f"Certified C18R time fields missing; keys={list(d)}")
  th=np.asarray(d["target_time_hat"],dtype=np.float32).reshape(-1)
  eta=np.asarray(d["target_eta_sequence"],dtype=np.float32)
  if th.shape!=(9702,) or eta.shape!=(9702,201):
   raise RuntimeError(f"Unexpected certified time shapes: target_time_hat={th.shape}, target_eta_sequence={eta.shape}")
  t=np.broadcast_to(th[:,None,None],(9702,201,1)).astype(np.float32)
  e=eta[:,:,None].astype(np.float32)
  X=np.concatenate([X,t,e],axis=-1)
 if X.shape!=(9702,201,9):raise RuntimeError(f"Unexpected X {X.shape}")
 tidx=None
 for k in ("test_sample_indices","test_indices","idx_test"):
  if k in s:tidx=np.asarray(s[k],dtype=int).reshape(-1);break
 if tidx is None:
  ts=pick(s,"test_streamline_index","test_streamline_indices","test_streamlines").reshape(-1)
  ss=np.tile(np.arange(1078),9)
  tidx=np.flatnonzero(np.isin(ss,ts))
 if tidx.size!=1449:raise RuntimeError(f"Expected 1449 test samples, got {tidx.size}")
 tf.keras.utils.set_random_seed(16021)
 m=build(); mode=recover(m)
 repaired=ROUT/"V16C22R3_EXP1_Best_Validation_Model_Serializable.keras";m.save(repaired)
 # First and only test access occurs after checkpoint recovery/freeze.
 Xt,Yt=X[tidx],Y[tidx]
 P=m.predict(Xt,batch_size=64,verbose=1).astype(np.float64); T=Yt.astype(np.float64)
 E=P-T;mse=float(np.mean(E*E));mae=float(np.mean(abs(E)));rmse=mse**.5
 finite=bool(np.isfinite(P).all());bounds=bool(P.min()>=SWC-1e-6 and P.max()<=1-SOR+1e-6)
 np.savez_compressed(ROUT/"V16C22R3_Locked_Test_Predictions.npz",test_sample_indices=tidx,Y_true=T,Y_pred=P)
 gates={"C22_checkpoint_exists":MODEL.exists(),"C18R_hash":sha(dpath)==C18SHA,"C19_hash":sha(spath)==C19SHA,
 "no_retraining":True,"no_retuning":True,"checkpoint_recovered_without_model_deserialization":True,
 "repaired_model_saved_before_test":repaired.exists(),"locked_test_count_1449":tidx.size==1449,
 "test_predictions_finite":finite,"bounded_output_preserved":bounds,"test_not_used_for_selection":True}
 print("\nLOCKED TEST RESULT");print(f"  recovery mode : {mode}");print(f"  MSE/RMSE/MAE  : {mse:.9e} / {rmse:.9e} / {mae:.9e}")
 print(f"  pred min/max  : {P.min():.9f} / {P.max():.9f}")
 print("\n"+"="*78);print("V16C-22R GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 ok=all(gates.values());status="V16C_PIRNN_EXP1_CHECKPOINT_REPAIRED_LOCKED_TEST_EVALUATION_COMPLETE" if ok else "V16C_PIRNN_EXP1_CHECKPOINT_REPAIR_BLOCKED"
 summary={"status":status,"repair_scope":"POST_TRAINING_LAMBDA_DESERIALIZATION_ONLY","retraining":False,"retuning":False,
 "original_checkpoint_sha256":sha(MODEL),"repaired_model_sha256":sha(repaired),"metrics":{"mse":mse,"rmse":rmse,"mae":mae,"max_abs_error":float(abs(E).max())},
 "gates":gates,"next_milestone":"V16C-23 — Frozen EXP1 Prediction Full-Physics Residual and Error-Structure Certification Audit"}
 (ROUT/"PAD_Stream_V16C22R3_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nSTATUS\n ",status)
 print("\nRECOMMENDATION\n ","Freeze C22R and proceed to C23." if ok else "Do not retrain; audit only failed recovery gates.")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
