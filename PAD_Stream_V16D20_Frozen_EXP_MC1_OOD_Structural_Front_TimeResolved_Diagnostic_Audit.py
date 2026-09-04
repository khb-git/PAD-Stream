#!/usr/bin/env python3
from pathlib import Path
import os,json,hashlib,random,math
import numpy as np
R=Path(__file__).resolve().parent
D15=R/"output"/"V16_D15R1_MULTIFOUNDATIONCASE_LEARNING_DATASET_FREEZE"
REG=D15/"V16D15R1_Frozen_MultiFoundationCase_Learning_Dataset_Registry.json"
D17=R/"output"/"V16_D17_EXP_MC1_FIRST_MULTIFOUNDATIONCASE_TRAINING_RUN"
CK=D17/"V16D17_EXP_MC1_Best.weights.h5"
D19=R/"output"/"V16_D19_EXP_MC1_GENERALIZATION_AUDIT_FORWARD_DECISION"
S19=D19/"PAD_Stream_V16D19_Summary.json"
S19SHA="a8347e06a5c4e79d545bc43f94f6416e1c881314e700ab489a94a3f0554fc8ce"
CKSHA="a6bc919871a5c8726a964e9d8dd88dd366596f2884b880502c233ba225249ac9"
DAYS=np.array([30,60,100,150,250,365,500,750,1000])
O=R/"output"/"V16_D20_FROZEN_EXP_MC1_OOD_STRUCTURAL_FRONT_TIME_DIAGNOSTIC";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def lx(p):
 with np.load(p,allow_pickle=False) as z:return np.asarray(z["X"],np.float32)
def ly(p):
 with np.load(p,allow_pickle=False) as z:
  hits=[k for k in z.files if np.asarray(z[k]).shape==(9,1078,201)]
  if len(hits)!=1:raise RuntimeError(f"Y ambiguous {p}: {hits}")
  return np.asarray(z[hits[0]],np.float32)
def metrics(e):
 e=np.asarray(e,np.float64);ae=np.abs(e)
 return {"MSE":float(np.mean(e*e)),"RMSE":float(np.sqrt(np.mean(e*e))),
         "MAE":float(np.mean(ae)),"max_abs_error":float(np.max(ae))}
def main():
 print("="*78);print("PAD-Stream V16D-20")
 print("Frozen EXP-MC1 OOD Structural / Front / Time-Resolved Diagnostic Audit");print("="*78)
 print("""THIS IS POST-HOC CHARACTERIZATION OF THE ALREADY-TOUCHED D18 OOD SET.
IT DOES NOT RETRAIN, SELECT, TUNE, OR CHANGE ANY THRESHOLD USED FOR MODEL
SELECTION. FRONT BANDS BELOW ARE PREDECLARED DIAGNOSTIC REGIONS ONLY.
""")
 if sha(S19)!=S19SHA or sha(CK)!=CKSHA:raise RuntimeError("frozen authority SHA mismatch")
 reg=json.loads(REG.read_text());ood=[e for e in reg["cases"] if e["partition"]=="LOCKED_OOD_TEST"]
 seed=161501;os.environ["PYTHONHASHSEED"]=str(seed);random.seed(seed);np.random.seed(seed)
 import tensorflow as tf
 tf.keras.utils.set_random_seed(seed)
 inp=tf.keras.Input((201,9));x=tf.keras.layers.LSTM(64,return_sequences=True,name="lstm_1")(inp)
 x=tf.keras.layers.LSTM(64,return_sequences=True,name="lstm_2")(x)
 raw=tf.keras.layers.TimeDistributed(tf.keras.layers.Dense(1,activation="sigmoid"),name="td_sigmoid")(x)
 out=tf.keras.layers.Rescaling(.6,.2,name="bounded_Sw_0p2_0p8")(raw)
 m=tf.keras.Model(inp,out);m.load_weights(CK)
 bycase={}; pooled_time=[[] for _ in DAYS]; pooled_region={"front":[],"low":[],"high":[]}
 worst={"abs_error":-1}
 for e in ood:
  c=e["case_id"];X=lx(Path(e["X_normalized"]["path"]));Y=ly(Path(e["Y_stage4"]["path"]))
  P=m.predict(X.reshape(-1,201,9),batch_size=64,verbose=0).reshape(Y.shape);E=P-Y
  time=[]
  for ti,d in enumerate(DAYS):
   q=metrics(E[ti]);q["day"]=int(d);time.append(q);pooled_time[ti].append(E[ti].astype(np.float64))
  # Diagnostic front definition: interior saturation 0.25<Y<0.75.
  masks={"front":(Y>0.25)&(Y<0.75),"low":Y<=0.25,"high":Y>=0.75}
  regions={}
  for name,mask in masks.items():
   regions[name]={"fraction":float(mask.mean()),**metrics(E[mask])} if mask.any() else {"fraction":0.0}
   if mask.any():pooled_region[name].append(E[mask].astype(np.float64))
  # spatial monotonicity diagnostic along Pollock node coordinate
  spatial_positive=float(np.mean(np.diff(P,axis=2)>0))
  temporal_negative=float(np.mean(np.diff(P,axis=0)<0))
  idx=np.unravel_index(np.argmax(np.abs(E)),E.shape);val=float(abs(E[idx]))
  if val>worst["abs_error"]:
   worst={"abs_error":val,"case_id":c,"day":int(DAYS[idx[0]]),"streamline":int(idx[1]),"node":int(idx[2]),
          "truth":float(Y[idx]),"prediction":float(P[idx]),"signed_error":float(E[idx])}
  bycase[c]={"overall":metrics(E),"by_time":time,"regions":regions,
             "spatial_positive_fraction":spatial_positive,"temporal_negative_fraction":temporal_negative}
 pooled_by_time=[]
 for ti,d in enumerate(DAYS):
  z=np.concatenate([x.ravel() for x in pooled_time[ti]])
  pooled_by_time.append({"day":int(d),**metrics(z)})
 preg={}
 for n,arr in pooled_region.items():
  z=np.concatenate([x.ravel() for x in arr]);preg[n]={"N":int(z.size),**metrics(z)}
 # Determine descriptive concentrations only; not selection/tuning.
 worst_time=max(pooled_by_time,key=lambda q:q["RMSE"])
 worst_case=max(bycase.items(),key=lambda kv:kv[1]["overall"]["RMSE"])
 report={"milestone":"V16D-20","diagnostic_only":True,
 "front_definition":"0.25 < source-authentic Y < 0.75; predeclared diagnostic band, not a tuning threshold",
 "cases":bycase,"pooled_by_time":pooled_by_time,"pooled_regions":preg,"worst_point":worst,
 "descriptive_summary":{"highest_RMSE_case":worst_case[0],"highest_RMSE_case_value":worst_case[1]["overall"]["RMSE"],
 "highest_RMSE_time_days":worst_time["day"],"highest_RMSE_time_value":worst_time["RMSE"]},
 "decision_constraints":{"MC1_remains_frozen":True,"no_retraining":True,"no_OOD_informed_tuning":True,
 "diagnostics_may_inform_future_experiment_hypotheses_but_not_retroactive_MC1_selection":True}}
 rp=O/"V16D20_EXP_MC1_OOD_Structural_Diagnostic_Report.json";rp.write_text(json.dumps(report,indent=2))
 gates={"D19_SHA_exact":sha(S19)==S19SHA,"checkpoint_SHA_exact":sha(CK)==CKSHA,"exact_four_OOD_cases":len(bycase)==4,
 "nine_times_audited":len(pooled_by_time)==9,"front_region_predeclared":True,"finite_diagnostics":all(math.isfinite(x["RMSE"]) for x in pooled_by_time),
 "no_retraining":True,"no_model_selection":True,"no_threshold_tuning":True,"MC1_unchanged":True}
 status="V16D_EXP_MC1_OOD_STRUCTURAL_FRONT_TIME_DIAGNOSTICS_FROZEN_FUTURE_EXPERIMENT_HYPOTHESIS_FORMULATION_AUTHORIZED"
 nxt="V16D-21 — Post-OOD Scientific Interpretation and Next-Experiment (MC2 / Control-Space Expansion) Decision Contract"
 sp=O/"PAD_Stream_V16D20_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-20","status":status,"diagnostic_report_sha256":sha(rp),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nOOD RMSE BY TIME")
 for q in pooled_by_time:print(f"  {q['day']:4d} d  RMSE={q['RMSE']:.9e} MAE={q['MAE']:.9e} max={q['max_abs_error']:.9e}")
 print("\nPOOLED REGIONS")
 for n,q in preg.items():print(f"  {n:5s} N={q['N']} RMSE={q['RMSE']:.9e} MAE={q['MAE']:.9e} max={q['max_abs_error']:.9e}")
 print("\nWORST POINT",worst)
 print("Highest-RMSE case:",worst_case[0],worst_case[1]["overall"]["RMSE"])
 print("Highest-RMSE time:",worst_time["day"],worst_time["RMSE"])
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
if __name__=="__main__":main()
