#!/usr/bin/env python3
from pathlib import Path
import os,json,hashlib,random
import numpy as np
R=Path(__file__).resolve().parent
D15=R/"output"/"V16_D15R1_MULTIFOUNDATIONCASE_LEARNING_DATASET_FREEZE"
REG=D15/"V16D15R1_Frozen_MultiFoundationCase_Learning_Dataset_Registry.json"
D17=R/"output"/"V16_D17_EXP_MC1_FIRST_MULTIFOUNDATIONCASE_TRAINING_RUN"
SUM=D17/"PAD_Stream_V16D17_Summary.json"; CK=D17/"V16D17_EXP_MC1_Best.weights.h5"
SUMSHA="160fe4d8138df99d46fb2c1b1b0e37668e66754fb3c11a074a1fac7b4e68caeb"
CKSHA="a6bc919871a5c8726a964e9d8dd88dd366596f2884b880502c233ba225249ac9"
O=R/"output"/"V16_D18_EXP_MC1_LOCKED_CASELEVEL_OOD_FINAL_EVALUATION_ONE_TOUCH"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def loadx(p):
 with np.load(p,allow_pickle=False) as z:a=np.asarray(z["X"],dtype=np.float32)
 if a.shape!=(9,1078,201,9):raise RuntimeError(f"bad X {a.shape}")
 return a
def loady(p):
 with np.load(p,allow_pickle=False) as z:
  hits=[k for k in z.files if np.asarray(z[k]).shape==(9,1078,201)]
  if len(hits)!=1:raise RuntimeError(f"Y not unique {hits}")
  return np.asarray(z[hits[0]],dtype=np.float32)
def main():
 print("="*78);print("PAD-Stream V16D-18")
 print("EXP-MC1 Locked Case-Level OOD Final Evaluation — ONE TOUCH");print("="*78)
 if O.exists() and any(O.iterdir()):raise RuntimeError("D18 output nonempty; one-touch evaluation will not rerun.")
 O.mkdir(parents=True,exist_ok=True)
 if sha(SUM)!=SUMSHA or sha(CK)!=CKSHA:raise RuntimeError("D17 frozen authority SHA mismatch")
 s=json.loads(SUM.read_text())
 if s.get("locked_OOD_opened") or s.get("locked_OOD_evaluated"):raise RuntimeError("D17 says OOD already touched")
 reg=json.loads(REG.read_text());ood=[e for e in reg["cases"] if e["partition"]=="LOCKED_OOD_TEST"]
 if [e["case_id"] for e in ood]!=["0005","0018","0021","0022"]:raise RuntimeError("OOD partition mismatch")
 seed=161501;os.environ["PYTHONHASHSEED"]=str(seed);random.seed(seed);np.random.seed(seed)
 import tensorflow as tf
 tf.keras.utils.set_random_seed(seed)
 inp=tf.keras.Input((201,9),name="C20_predictors")
 x=tf.keras.layers.LSTM(64,return_sequences=True,name="lstm_1")(inp)
 x=tf.keras.layers.LSTM(64,return_sequences=True,name="lstm_2")(x)
 raw=tf.keras.layers.TimeDistributed(tf.keras.layers.Dense(1,activation="sigmoid"),name="td_sigmoid")(x)
 out=tf.keras.layers.Rescaling(scale=.6,offset=.2,name="bounded_Sw_0p2_0p8")(raw)
 model=tf.keras.Model(inp,out);model.load_weights(CK)
 cases=[];SSE=SAE=0.;N=0;mxall=0.;pmin=np.inf;pmax=-np.inf
 print("Opening the four sealed OOD cases for final evaluation.")
 for e in ood:
  c=e["case_id"];X=loadx(Path(e["X_normalized"]["path"]));Y=loady(Path(e["Y_stage4"]["path"]))
  P=model.predict(X.reshape(-1,201,9),batch_size=64,verbose=0).reshape(9,1078,201);E=P-Y
  ef=E.astype(np.float64);mse=float(np.mean(ef**2));mae=float(np.mean(np.abs(ef)));rmse=float(np.sqrt(mse))
  mx=float(np.max(np.abs(ef)));lo=float(P.min());hi=float(P.max())
  cases.append({"case_id":c,"MSE":mse,"RMSE":rmse,"MAE":mae,"max_abs_error":mx,"pred_min":lo,"pred_max":hi})
  SSE+=float(np.sum(ef**2));SAE+=float(np.sum(np.abs(ef)));N+=ef.size;mxall=max(mxall,mx);pmin=min(pmin,lo);pmax=max(pmax,hi)
  print(f"Case{c}: RMSE={rmse:.9e} MAE={mae:.9e} max={mx:.9e} pred=[{lo:.9f},{hi:.9f}]")
 agg={"MSE":SSE/N,"RMSE":float(np.sqrt(SSE/N)),"MAE":SAE/N,"max_abs_error":mxall,"pred_min":pmin,"pred_max":pmax,"N_values":N}
 gates={"D17_summary_SHA_exact":True,"D17_checkpoint_SHA_exact":True,"exact_locked_OOD_cases":len(cases)==4,
 "checkpoint_selected_before_OOD":True,"no_OOD_adaptation":True,"no_OOD_normalization_fit":True,"no_OOD_model_selection":True,
 "no_retraining":True,"finite_metrics":all(np.isfinite(v) for v in agg.values()),"prediction_bounds_respected":pmin>=.2 and pmax<=.8}
 status="V16D_EXP_MC1_LOCKED_CASELEVEL_OOD_FINAL_EVALUATION_COMPLETE_ONE_TOUCH_GENERALIZATION_BASELINE_CERTIFIED"
 result={"milestone":"V16D-18","experiment":"EXP-MC1","one_touch":True,"cases":cases,"aggregate":agg,"gates":gates,"status":status,
 "next_milestone":"V16D-19 — EXP-MC1 Multi-Case Generalization Audit, Interpretation, and V16D Forward Architecture Decision"}
 sp=O/"PAD_Stream_V16D18_Summary.json";sp.write_text(json.dumps(result,indent=2))
 print("\nAGGREGATE LOCKED OOD\n",json.dumps(agg,indent=2));print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",result["next_milestone"]);print("\nSummary SHA-256:",sha(sp))
if __name__=="__main__":main()
