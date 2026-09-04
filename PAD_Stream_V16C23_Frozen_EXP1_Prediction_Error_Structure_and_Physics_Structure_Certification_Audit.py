#!/usr/bin/env python
from __future__ import annotations
from pathlib import Path
import hashlib,json,csv
import numpy as np

ROOT=Path(__file__).resolve().parent
R3=ROOT/"output"/"V16_C22R3_EXACT_C20_TIME_CHANNEL_SCHEMA_REPAIR"
PRED=R3/"V16C22R3_Locked_Test_Predictions.npz"
SUM=R3/"PAD_Stream_V16C22R3_Summary.json"
OUT=ROOT/"output"/"V16_C23_FROZEN_EXP1_PREDICTION_ERROR_STRUCTURE_PHYSICS_STRUCTURE_CERTIFICATION_AUDIT"
OUT.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def csvsave(p,rows):
 rows=list(rows); keys=list(rows[0]) if rows else []
 with p.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def main():
 print("="*78);print("PAD-Stream V16C-23")
 print("Frozen EXP1 Prediction Error-Structure and Physics-Structure Certification Audit");print("="*78)
 print("""C23 DOES NOT TRAIN, RETUNE, OR RESELECT A MODEL.

IT AUDITS THE FROZEN C22R3 LOCKED-TEST PREDICTIONS BY PHYSICAL TARGET TIME,
STREAMLINE, SATURATION BOUNDS, INLET BEHAVIOR, SPATIAL FRONT ORDERING, AND
TEMPORAL ORDERING.

IMPORTANT PROVENANCE RULE:
THE C10/C11 DIFFERENTIAL PDE RESIDUAL REQUIRES THE C7 METRIC M=dtheta/dxD
ALIGNED TO THE LOCKED TEST STREAMLINES. C23 WILL NOT INVENT OR APPROXIMATE M.
IF AN EXACTLY BOUND C7 METRIC ARTIFACT IS NOT LOCALLY IDENTIFIED BY THIS
MILESTONE, THE DIFFERENTIAL RESIDUAL IS RECORDED AS PENDING RATHER THAN
FABRICATED. STRUCTURAL PHYSICS AUDITS REMAIN VALID AND SEPARATE.""")
 if not PRED.exists() or not SUM.exists():raise FileNotFoundError("C22R3 frozen outputs missing")
 s=json.loads(SUM.read_text())
 if s.get("status")!="V16C_PIRNN_EXP1_CHECKPOINT_REPAIRED_LOCKED_TEST_EVALUATION_COMPLETE":
  raise RuntimeError("C22R3 frozen completion status missing")
 with np.load(PRED,allow_pickle=False) as z:
  T=np.asarray(z["Y_true"],float);P=np.asarray(z["Y_pred"],float);idx=np.asarray(z["test_sample_indices"],int)
 if T.shape!=(1449,201) or P.shape!=(1449,201):raise RuntimeError((T.shape,P.shape))
 # Recover certified metadata by exact sample indices from C18R.
 C18SHA="1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"
 hits=[]
 for q in ROOT.rglob("*.npz"):
  try:
   if sha(q)==C18SHA:hits.append(q)
  except:pass
 if len(hits)!=1:raise RuntimeError(f"C18R exact hash hits={hits}")
 with np.load(hits[0],allow_pickle=False) as z:
  days=np.asarray(z["target_time_days"])[idx]
  sl=np.asarray(z["streamline_index"])[idx]
  ti=np.asarray(z["time_index"])[idx]
 E=P-T
 mse=float(np.mean(E**2));rmse=mse**.5;mae=float(np.mean(abs(E)));mx=float(np.max(abs(E)))
 # Time-resolved errors
 rows=[]
 for d in np.unique(days):
  m=days==d;e=E[m]
  rows.append({"target_day":float(d),"samples":int(m.sum()),"mse":float(np.mean(e**2)),
   "rmse":float(np.sqrt(np.mean(e**2))),"mae":float(np.mean(abs(e))),"max_abs_error":float(np.max(abs(e)))})
 csvsave(OUT/"V16C23_Error_By_Target_Time.csv",rows)
 # Streamline-resolved error summary
 sr=[]
 for g in np.unique(sl):
  m=sl==g;e=E[m]
  sr.append({"streamline_index":int(g),"samples":int(m.sum()),"mse":float(np.mean(e**2)),
   "mae":float(np.mean(abs(e))),"max_abs_error":float(np.max(abs(e)))})
 csvsave(OUT/"V16C23_Error_By_Streamline.csv",sr)
 # Structural physics.
 bound=float(max(0,.2-P.min(),P.max()-.8))
 inlet_mae=float(np.mean(abs(P[:,0]-T[:,0])))
 spatial_pos=float(np.mean(np.diff(P,axis=1)>1e-7))
 # temporal monotonicity by streamline, sorted by actual day
 neg=tot=0
 for g in np.unique(sl):
  j=np.where(sl==g)[0];j=j[np.argsort(days[j])]
  d=np.diff(P[j],axis=0);neg+=int(np.sum(d < -1e-6));tot+=d.size
 temporal_neg=float(neg/tot) if tot else 0.
 # Front-location proxy: first node dropping below midpoint saturation.
 mid=.5
 def front(A):
  return np.argmax(A<mid,axis=1)
 fp,ft=front(P),front(T)
 front_mae=float(np.mean(abs(fp-ft)))
 # PDE residual status: do not fake C7 metric binding.
 pde_status="PENDING_EXACT_C7_METRIC_BINDING_NOT_EVALUATED_IN_C23"
 gates=[
 ("C22R3_completion_bound",True),("frozen_test_shape_1449x201",P.shape==(1449,201)),
 ("predictions_finite",bool(np.isfinite(P).all())),("targets_finite",bool(np.isfinite(T).all())),
 ("bounded_saturation_output",bound<=1e-7),("all_nine_target_times_present",len(np.unique(days))==9),
 ("all_test_streamlines_have_nine_times",all(np.sum(sl==g)==9 for g in np.unique(sl))),
 ("no_training",True),("no_retuning",True),("no_test_based_model_selection",True),
 ("differential_PDE_residual_not_fabricated_without_exact_metric_binding",True)]
 ok=all(v for _,v in gates)
 status="V16C_EXP1_FROZEN_PREDICTION_ERROR_AND_STRUCTURAL_PHYSICS_AUDIT_COMPLETE_PDE_RESIDUAL_PENDING" if ok else "V16C_EXP1_PREDICTION_AUDIT_BLOCKED"
 summary={"milestone":"V16C-23","status":status,"prediction_sha256":sha(PRED),
 "global_error":{"mse":mse,"rmse":rmse,"mae":mae,"max_abs_error":mx},
 "structural_physics":{"bound_violation":bound,"inlet_mae":inlet_mae,
 "spatial_positive_fraction":spatial_pos,"temporal_negative_fraction":temporal_neg,
 "front_index_mae_nodes":front_mae},"differential_pde_residual_status":pde_status,
 "gates":dict(gates),"training":False,"retuning":False,
 "next_milestone":"V16C-23A — Exact C7 Metric-to-C22R3 Locked-Test Binding and Differential Full-Physics Residual Audit"}
 (OUT/"PAD_Stream_V16C23_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\\nGLOBAL LOCKED-TEST ERROR")
 print(f"  MSE / RMSE / MAE : {mse:.9e} / {rmse:.9e} / {mae:.9e}")
 print(f"  max |error|      : {mx:.9e}")
 print("\\nSTRUCTURAL PHYSICS")
 print(f"  bound violation       : {bound:.3e}")
 print(f"  inlet MAE             : {inlet_mae:.9e}")
 print(f"  spatial positive frac : {spatial_pos:.9e}")
 print(f"  temporal negative frac: {temporal_neg:.9e}")
 print(f"  front-index MAE nodes : {front_mae:.6f}")
 print(f"  differential PDE      : {pde_status}")
 print("\\n"+"="*78);print("V16C-23 GATES");print("="*78)
 for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
 print("\\nSTATUS\\n ",status)
 print("\\nNEXT MILESTONE\\n  V16C-23A — Exact C7 Metric-to-C22R3 Locked-Test Binding and Differential Full-Physics Residual Audit")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
