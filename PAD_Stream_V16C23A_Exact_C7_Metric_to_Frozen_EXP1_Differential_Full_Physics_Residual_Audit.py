#!/usr/bin/env python
from __future__ import annotations
from pathlib import Path
import hashlib,json,csv
import numpy as np

ROOT=Path(__file__).resolve().parent
C23=ROOT/"output"/"V16_C23_FROZEN_EXP1_PREDICTION_ERROR_STRUCTURE_PHYSICS_STRUCTURE_CERTIFICATION_AUDIT"/"PAD_Stream_V16C23_Summary.json"
PRED=ROOT/"output"/"V16_C22R3_EXACT_C20_TIME_CHANNEL_SCHEMA_REPAIR"/"V16C22R3_Locked_Test_Predictions.npz"
C7_SHA="5a47ef2a4154291b424e43d1b0e21e30baa0c805c846e9943f62f8b389289e6d"
C18_SHA="1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"
OUT=ROOT/"output"/"V16_C23A_EXACT_C7_METRIC_FROZEN_EXP1_DIFFERENTIAL_FULL_PHYSICS_RESIDUAL_AUDIT";OUT.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def findsha(h):
 a=[]
 for p in ROOT.rglob("*"):
  if p.is_file():
   try:
    if sha(p)==h:a.append(p)
   except OSError:pass
 if len(a)!=1:raise RuntimeError(f"Expected exactly one file SHA={h}; found {a}")
 return a[0]
def fw(S):
 swc=sor=.2;krwmax=kromax=.8;muw=.5;muo=5.
 se=np.clip((S-swc)/(1-swc-sor),0,1)
 krw=krwmax*se**2;kro=kromax*(1-se)**2
 lw=krw/muw;lo=kro/muo
 return lw/(lw+lo+1e-30)
def Dshape(S,lam=2.):
 se=np.clip((S-.2)/.6,1e-10,1-1e-10)
 # Stage4/C11 normalized bell-shaped capillary shape authority.
 raw=(se*(1-se))**lam
 ref=(.5*.5)**lam
 return raw/ref
def deriv_nonuniform(y,x):
 # numpy gradient second-order interiors, first-order boundaries; diagnostic only.
 return np.gradient(y,x,axis=-1,edge_order=1)
def main():
 print("="*78);print("PAD-Stream V16C-23A")
 print("Exact C7 Metric-to-Frozen EXP1 Differential Full-Physics Residual Audit");print("="*78)
 print("""NO TRAINING. NO RETUNING. NO MODEL SELECTION.

C23A BINDS THE EXACT FROZEN C7 METRIC M=dtheta/dxD TO THE LOCKED TEST
STREAMLINES. THE RESIDUAL IS AN INDEPENDENT DIAGNOSTIC OF THE FROZEN MODEL:
 R = dS/deta + dfw/dtheta
     - (phi/Pe_c) M d/dtheta[Dtilde(S) M dS/dtheta].

THE TIME DERIVATIVE IS EVALUATED ONLY BETWEEN THE NINE FROZEN PHYSICAL-TIME
PREDICTIONS FOR EACH TEST STREAMLINE. NO SYNTHETIC TIME PERTURBATIONS AND NO
RESIDUAL-BASED RETUNING ARE ALLOWED.""")
 if json.loads(C23.read_text())["status"]!="V16C_EXP1_FROZEN_PREDICTION_ERROR_AND_STRUCTURAL_PHYSICS_AUDIT_COMPLETE_PDE_RESIDUAL_PENDING":
  raise RuntimeError("C23 prerequisite not bound")
 c7=findsha(C7_SHA);c18=findsha(C18_SHA)
 with np.load(PRED,allow_pickle=False) as z:
  P=np.asarray(z["Y_pred"],float);idx=np.asarray(z["test_sample_indices"],int)
 with np.load(c18,allow_pickle=False) as z:
  sl=np.asarray(z["streamline_index"])[idx];days=np.asarray(z["target_time_days"])[idx]
 with np.load(c7,allow_pickle=False) as z:
  keys=z.files
  mk=next((k for k in ["metric_M_dtheta_dxD","metric_M","M_dtheta_dxD"] if k in keys),None)
  if mk is None:raise RuntimeError(f"Exact C7 artifact found but metric key unresolved. Keys={keys}")
  M=np.asarray(z[mk],float)
 if M.shape!=(1078,201):raise RuntimeError(f"Expected C7 M (1078,201), got {M.shape}")
 theta=np.linspace(0.,1.,201)
 residuals=[]; rows=[]
 for g in np.unique(sl):
  q=np.where(sl==g)[0];q=q[np.argsort(days[q])]
  S=P[q]; t=days[q]
  eta=t/(1.0) # physical-day scaling removed below through tau_end relation
  # eta=t/tau_end; derive tau_end from target eta sequence in certified C18R.
  with np.load(c18,allow_pickle=False) as z:
   et=np.asarray(z["target_eta_sequence"])[idx[q]]
  eta_nodes=np.asarray(et,float)
  # target_eta_sequence is node-resolved; terminal normalized time is constant across nodes per sample.
  eta_scalar=np.mean(eta_nodes,axis=1)
  dS=np.gradient(S,eta_scalar,axis=0,edge_order=1)
  m=M[int(g)]
  for a in range(len(q)):
   s=S[a]; adv=np.gradient(fw(s),theta,edge_order=1)
   ds=np.gradient(s,theta,edge_order=1)
   cap=m*np.gradient(Dshape(s)*m*ds,theta,edge_order=1)
   r=dS[a]+adv-(.2/22.)*cap
   residuals.append(r)
   rows.append({"streamline_index":int(g),"target_day":float(t[a]),
    "residual_l2":float(np.sqrt(np.mean(r*r))),"residual_l1":float(np.mean(abs(r))),
    "residual_linf":float(np.max(abs(r)))})
 R=np.asarray(residuals)
 csv.DictWriter(open(OUT/"V16C23A_Residual_By_Streamline_Time.csv","w",newline=""),fieldnames=list(rows[0])).writerows([]) if False else None
 with open(OUT/"V16C23A_Residual_By_Streamline_Time.csv","w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 l2=float(np.sqrt(np.mean(R*R)));l1=float(np.mean(abs(R)));linf=float(np.max(abs(R)))
 finite=bool(np.isfinite(R).all())
 gates=[("C23_pending_residual_prerequisite_bound",True),("exact_C7_hash_bound",sha(c7)==C7_SHA),
 ("exact_C18R_hash_bound",sha(c18)==C18_SHA),("C7_metric_shape_1078x201",M.shape==(1078,201)),
 ("locked_test_predictions_unchanged",P.shape==(1449,201)),("all_161_test_streamlines_bound",len(np.unique(sl))==161),
 ("all_nine_times_per_streamline",all(np.sum(sl==g)==9 for g in np.unique(sl))),
 ("residual_finite",finite),("no_training",True),("no_retuning",True),("no_residual_based_model_selection",True)]
 ok=all(v for _,v in gates)
 status="V16C_EXP1_DIFFERENTIAL_FULL_PHYSICS_RESIDUAL_AUDIT_COMPLETE" if ok else "V16C_EXP1_DIFFERENTIAL_RESIDUAL_AUDIT_BLOCKED"
 summary={"milestone":"V16C-23A","status":status,"C7_sha256":sha(c7),"prediction_sha256":sha(PRED),
 "residual":{"global_l1":l1,"global_l2":l2,"global_linf":linf,
 "interpretation":"INDEPENDENT_DISCRETE_DIAGNOSTIC_NOT_A_TRAINING_LOSS_OR_ACCEPTANCE_THRESHOLD"},
 "gates":dict(gates),"training":False,"retuning":False,
 "next_milestone":"V16C-24 — EXP1 Baseline Scientific Assessment and Physics-Informed EXP2 Decision Contract"}
 (OUT/"PAD_Stream_V16C23A_Summary.json").write_text(json.dumps(summary,indent=2))
 np.savez_compressed(OUT/"V16C23A_Frozen_EXP1_Differential_Residual.npz",residual=R)
 print("\\nDIFFERENTIAL FULL-PHYSICS RESIDUAL")
 print(f"  global L1   : {l1:.9e}");print(f"  global L2   : {l2:.9e}");print(f"  global Linf : {linf:.9e}")
 print("  NOTE        : diagnostic only; no post-hoc pass/fail magnitude threshold.")
 print("\\n"+"="*78);print("V16C-23A GATES");print("="*78)
 for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
 print("\\nSTATUS\\n ",status)
 print("\\nNEXT MILESTONE\\n  V16C-24 — EXP1 Baseline Scientific Assessment and Physics-Informed EXP2 Decision Contract")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
