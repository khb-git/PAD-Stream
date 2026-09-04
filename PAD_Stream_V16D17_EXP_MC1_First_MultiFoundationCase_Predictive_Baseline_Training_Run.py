#!/usr/bin/env python3
from pathlib import Path
import os, json, hashlib, random, time, sys
import numpy as np

R=Path(__file__).resolve().parent
D15=R/"output"/"V16_D15R1_MULTIFOUNDATIONCASE_LEARNING_DATASET_FREEZE"
REG=D15/"V16D15R1_Frozen_MultiFoundationCase_Learning_Dataset_Registry.json"
D16=R/"output"/"V16_D16_EXP_MC1_EXECUTABLE_TRAINING_PROTOCOL_FREEZE"
SUM=D16/"PAD_Stream_V16D16_Summary.json"
PRO=D16/"V16D16_EXP_MC1_Executable_Training_Protocol_1.0.json"
SUMSHA="3b1a9403999c20a0ad3a3c0992c3b3fac38e057c05e56b4ec01a43c9956c1348"
REGSHA="7e3e885a1219bf72f89dd759df7043fe2bd6e9a718d418edbe8db3e2afce6266"
O=R/"output"/"V16_D17_EXP_MC1_FIRST_MULTIFOUNDATIONCASE_TRAINING_RUN";O.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def y_from_npz(path):
 with np.load(path,allow_pickle=False) as z:
  hits=[]
  for k in z.files:
   a=np.asarray(z[k])
   if a.shape==(9,1078,201): hits.append(k)
  if len(hits)!=1: raise RuntimeError(f"target array not unique in {path}: {hits}")
  return np.asarray(z[hits[0]],dtype=np.float32)

def x_from_npz(path):
 with np.load(path,allow_pickle=False) as z:
  if "X" not in z.files: raise RuntimeError(f"X absent in {path}")
  a=np.asarray(z["X"])
  if a.shape!=(9,1078,201,9): raise RuntimeError(f"bad X shape {a.shape}")
  return np.asarray(a,dtype=np.float32)

def main():
 print("="*78);print("PAD-Stream V16D-17")
 print("EXP-MC1 First Multi-Foundation-Case Predictive Baseline Training Run");print("="*78)
 if sha(SUM)!=SUMSHA or sha(REG)!=REGSHA: raise RuntimeError("frozen authority SHA mismatch")
 protocol=json.loads(PRO.read_text()); reg=json.loads(REG.read_text())
 seed=protocol["seed"]; random.seed(seed); np.random.seed(seed)
 os.environ["PYTHONHASHSEED"]=str(seed)
 import tensorflow as tf
 tf.keras.utils.set_random_seed(seed)
 try: tf.config.experimental.enable_op_determinism()
 except Exception: pass
 print("TensorFlow:",tf.__version__);print("GPUs:",tf.config.list_physical_devices("GPU"))
 train=[e for e in reg["cases"] if e["partition"]=="TRAIN"]
 val=[e for e in reg["cases"] if e["partition"]=="VALIDATION"]
 ood=[e for e in reg["cases"] if e["partition"]=="LOCKED_OOD_TEST"]
 print("TRAIN/VAL/OOD registry:",len(train),len(val),len(ood))
 # OOD paths are never opened below.
 def gen(entries,shuffle,epoch_seed):
  order=np.arange(len(entries))
  rng=np.random.default_rng(epoch_seed)
  if shuffle:rng.shuffle(order)
  for ii in order:
   e=entries[int(ii)]
   X=x_from_npz(Path(e["X_normalized"]["path"]))
   Y=y_from_npz(Path(e["Y_stage4"]["path"]))
   idx=np.arange(9*1078)
   if shuffle:rng.shuffle(idx)
   X=X.reshape(-1,201,9);Y=Y.reshape(-1,201,1)
   for q in idx: yield X[q],Y[q]
 sig=(tf.TensorSpec((201,9),tf.float32),tf.TensorSpec((201,1),tf.float32))
 # Reiterable dataset generators with deterministic seed.
 trds=tf.data.Dataset.from_generator(lambda:gen(train,True,seed),output_signature=sig).batch(64).prefetch(tf.data.AUTOTUNE)
 vds=tf.data.Dataset.from_generator(lambda:gen(val,False,seed),output_signature=sig).batch(64).prefetch(tf.data.AUTOTUNE)
 inp=tf.keras.Input(shape=(201,9),name="C20_predictors")
 x=tf.keras.layers.LSTM(64,return_sequences=True,name="lstm_1")(inp)
 x=tf.keras.layers.LSTM(64,return_sequences=True,name="lstm_2")(x)
 raw=tf.keras.layers.TimeDistributed(tf.keras.layers.Dense(1,activation="sigmoid"),name="td_sigmoid")(x)
 # Built-in arithmetic layers avoid unsafe Lambda serialization.
 out=tf.keras.layers.Rescaling(scale=0.6,offset=0.2,name="bounded_Sw_0p2_0p8")(raw)
 model=tf.keras.Model(inp,out,name="V16D_EXP_MC1")
 model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),loss="mse",metrics=["mae"])
 model.summary()
 ck=O/"V16D17_EXP_MC1_Best.weights.h5"
 histcsv=O/"V16D17_EXP_MC1_Training_History.csv"
 callbacks=[
  tf.keras.callbacks.ModelCheckpoint(str(ck),monitor="val_loss",mode="min",save_best_only=True,save_weights_only=True,verbose=1),
  tf.keras.callbacks.EarlyStopping(monitor="val_loss",mode="min",patience=25,min_delta=0.0,restore_best_weights=False,verbose=1),
  tf.keras.callbacks.CSVLogger(str(histcsv))
 ]
 t0=time.time()
 hist=model.fit(trds,validation_data=vds,epochs=300,callbacks=callbacks,verbose=2)
 runtime=time.time()-t0
 if not ck.exists():raise RuntimeError("best checkpoint absent")
 model.load_weights(ck)
 # Validation only after best-checkpoint reload. OOD remains sealed.
 vr=model.evaluate(vds,verbose=1,return_dict=True)
 best_epoch=int(np.argmin(hist.history["val_loss"])+1)
 best_val=float(np.min(hist.history["val_loss"]))
 # Save serializable architecture + frozen weights separately.
 arch=O/"V16D17_EXP_MC1_Model_Architecture.json";arch.write_text(model.to_json())
 result={"milestone":"V16D-17","experiment":"EXP-MC1","seed":seed,"epochs_executed":len(hist.history["loss"]),
 "best_epoch":best_epoch,"best_raw_val_MSE":best_val,"best_checkpoint_validation":{k:float(v) for k,v in vr.items()},
 "runtime_seconds":runtime,"checkpoint":{"path":str(ck),"sha256":sha(ck)},"architecture_sha256":sha(arch),
 "locked_OOD_opened":False,"locked_OOD_evaluated":False,
 "status":"V16D_EXP_MC1_MULTIFOUNDATIONCASE_PREDICTIVE_BASELINE_TRAINED_BEST_VALIDATION_CHECKPOINT_FROZEN_LOCKED_OOD_FINAL_EVALUATION_AUTHORIZED",
 "next_milestone":"V16D-18 — EXP-MC1 Locked Case-Level OOD Final Evaluation (One Touch)"}
 rp=O/"PAD_Stream_V16D17_Summary.json";rp.write_text(json.dumps(result,indent=2))
 print("\nBEST EPOCH:",best_epoch);print("BEST RAW VAL MSE:",best_val);print("RELOADED CHECKPOINT VAL:",vr)
 print("CHECKPOINT SHA-256:",sha(ck));print("runtime seconds:",runtime)
 print("\nSTATUS\n ",result["status"]);print("\nNEXT\n ",result["next_milestone"]);print("\nSummary SHA-256:",sha(rp))
if __name__=="__main__":main()
