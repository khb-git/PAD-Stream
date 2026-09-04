#!/usr/bin/env python
from pathlib import Path
import json, hashlib, csv, numpy as np
ROOT=Path(__file__).resolve().parent
E1=ROOT/"output"/"V16_C22R3_EXACT_C20_TIME_CHANNEL_SCHEMA_REPAIR"/"V16C22R3_Locked_Test_Predictions.npz"
E2=ROOT/"output"/"V16_C26_EXP2_PHYSICS_INFORMED_TRAINING_EXECUTION_BEST_VALIDATION_CHECKPOINT_LOCKED_TEST_EVALUATION"/"V16C26_EXP2_Locked_Test_Predictions.npz"
S2=ROOT/"output"/"V16_C26_EXP2_PHYSICS_INFORMED_TRAINING_EXECUTION_BEST_VALIDATION_CHECKPOINT_LOCKED_TEST_EVALUATION"/"PAD_Stream_V16C26_Summary.json"
C7SHA="5a47ef2a4154291b424e43d1b0e21e30baa0c805c846e9943f62f8b389289e6d"
C18SHA="1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"
OUT=ROOT/"output"/"V16_C27_FROZEN_EXP1_VS_EXP2_COMPARATIVE_AUDIT"; OUT.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()
def byhash(x):
 a=[]
 for p in ROOT.rglob("*"):
  if p.is_file():
   try:
    if sha(p)==x:a.append(p)
   except OSError: pass
 if len(a)!=1: raise RuntimeError(f"SHA match count {len(a)} for {x}: {a}")
 return a[0]
def met(P,T):
 e=P-T
 return dict(mse=float(np.mean(e*e)),rmse=float(np.sqrt(np.mean(e*e))),mae=float(np.mean(abs(e))),max_abs=float(np.max(abs(e))))
def fw(S):
 se=np.clip((S-.2)/.6,0,1); krw=.8*se**2; kro=.8*(1-se)**2
 return (krw/.5)/(krw/.5+kro/5+1e-30)
def D(S):
 se=np.clip((S-.2)/.6,1e-10,1-1e-10); return (se*(1-se))**2/.0625
def res(P,idx,sl,days,eta,M):
 th=np.linspace(0,1,201); out=[]
 for g in np.unique(sl):
  q=np.where(sl==g)[0]; q=q[np.argsort(days[q])]
  S=P[q]; et=np.mean(eta[idx[q]],axis=1); dS=np.gradient(S,et,axis=0,edge_order=1); m=M[int(g)]
  for k,s in enumerate(S):
   adv=np.gradient(fw(s),th,edge_order=1); ds=np.gradient(s,th,edge_order=1)
   cap=m*np.gradient(D(s)*m*ds,th,edge_order=1)
   out.append(dS[k]+adv-(.2/22)*cap)
 R=np.asarray(out)
 return dict(l1=float(np.mean(abs(R))),l2=float(np.sqrt(np.mean(R*R))),linf=float(np.max(abs(R))))
def pct(new,old): return 100*(old-new)/old
def main():
 print("="*78); print("PAD-Stream V16C-27"); print("Frozen EXP1-vs-EXP2 Predictive and Full-Physics Comparative Certification Audit"); print("="*78)
 if json.loads(S2.read_text())["status"]!="V16C_EXP2_PHYSICS_INFORMED_TRAINING_COMPLETE_LOCKED_TEST_EVALUATED": raise RuntimeError("C26 status mismatch")
 with np.load(E1) as z:A={k:z[k] for k in z.files}
 with np.load(E2) as z:B={k:z[k] for k in z.files}
 ia=np.asarray(A["test_sample_indices"],int); ib=np.asarray(B["test_sample_indices"],int)
 if not np.array_equal(ia,ib): raise RuntimeError("Test identities differ")
 T=np.asarray(A["Y_true"],float); T2=np.asarray(B["Y_true"],float)
 if not np.array_equal(T,T2): raise RuntimeError("Targets differ")
 P1=np.asarray(A["Y_pred"],float); P2=np.asarray(B["Y_pred"],float)
 c18=byhash(C18SHA); c7=byhash(C7SHA)
 with np.load(c18) as z:
  sl=np.asarray(z["streamline_index"])[ia]; days=np.asarray(z["target_time_days"])[ia]; eta=np.asarray(z["target_eta_sequence"])
 with np.load(c7) as z:
  key=next(k for k in ("metric_M_dtheta_dxD","metric_M","M_dtheta_dxD") if k in z.files); M=np.asarray(z[key],float)
 m1,m2=met(P1,T),met(P2,T); r1,r2=res(P1,ia,sl,days,eta,M),res(P2,ia,sl,days,eta,M)
 rows=[]
 for d in np.unique(days):
  q=days==d; a,b=met(P1[q],T[q]),met(P2[q],T[q])
  rows.append(dict(day=float(d),EXP1_RMSE=a["rmse"],EXP2_RMSE=b["rmse"],EXP2_RMSE_reduction_pct=pct(b["rmse"],a["rmse"]),EXP1_MAE=a["mae"],EXP2_MAE=b["mae"]))
 with (OUT/"V16C27_Predictive_Comparison_By_Time.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 def structural(P):
  sp=float(np.mean(np.diff(P,axis=1)>1e-7)); neg=tot=0
  for g in np.unique(sl):
   q=np.where(sl==g)[0];q=q[np.argsort(days[q])];dd=np.diff(P[q],axis=0);neg+=int(np.sum(dd<-1e-6));tot+=dd.size
  return dict(spatial_positive_fraction=sp,temporal_negative_fraction=float(neg/tot))
 st1,st2=structural(P1),structural(P2)
 gates=dict(C26_frozen=True,identical_test_indices=True,identical_targets=True,exact_C18R_bound=sha(c18)==C18SHA,exact_C7_bound=sha(c7)==C7SHA,
  EXP1_finite=bool(np.isfinite(P1).all()),EXP2_finite=bool(np.isfinite(P2).all()),same_residual_diagnostic=True,no_retraining=True,no_retuning=True,no_model_reselection=True,no_OOD_claim=True)
 ok=all(gates.values()); status="V16C_EXP1_VS_EXP2_FROZEN_COMPARATIVE_AUDIT_COMPLETE" if ok else "V16C_EXP1_VS_EXP2_COMPARISON_BLOCKED"
 summary=dict(milestone="V16C-27",status=status,predictive=dict(EXP1=m1,EXP2=m2,EXP2_RMSE_reduction_pct=pct(m2["rmse"],m1["rmse"]),EXP2_MAE_reduction_pct=pct(m2["mae"],m1["mae"])),
  physics_residual=dict(EXP1=r1,EXP2=r2,EXP2_L1_reduction_pct=pct(r2["l1"],r1["l1"]),EXP2_L2_reduction_pct=pct(r2["l2"],r1["l2"]),EXP2_Linf_reduction_pct=pct(r2["linf"],r1["linf"])),
  structural=dict(EXP1=st1,EXP2=st2),gates=gates,scientific_rule="Descriptive frozen comparison; superiority is not a gate.",
  next_milestone="V16C-28 — V16C Transport Learning Branch Freeze, Interpretation and Forward Architecture Decision")
 (OUT/"PAD_Stream_V16C27_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nPREDICTIVE COMPARISON")
 print(f" EXP1 RMSE/MAE: {m1['rmse']:.9e} / {m1['mae']:.9e}")
 print(f" EXP2 RMSE/MAE: {m2['rmse']:.9e} / {m2['mae']:.9e}")
 print(f" EXP2 RMSE reduction: {pct(m2['rmse'],m1['rmse']):+.3f}%")
 print("\nFULL-PHYSICS RESIDUAL")
 print(f" EXP1 L1/L2/Linf: {r1['l1']:.6e} / {r1['l2']:.6e} / {r1['linf']:.6e}")
 print(f" EXP2 L1/L2/Linf: {r2['l1']:.6e} / {r2['l2']:.6e} / {r2['linf']:.6e}")
 print(f" EXP2 L2 reduction: {pct(r2['l2'],r1['l2']):+.3f}%")
 print("\nSTRUCTURAL"); print(" EXP1:",st1); print(" EXP2:",st2)
 print("\nGATES")
 for k,v in gates.items(): print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status); print("\nNEXT\n  V16C-28 — V16C Transport Learning Branch Freeze, Interpretation and Forward Architecture Decision")
 if not ok: raise SystemExit(2)
if __name__=="__main__":main()
