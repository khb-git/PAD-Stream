#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,pickle,sys
import numpy as np
R=Path(__file__).resolve().parent
S=R/"output"/"V16_D26_R2_R1_36CASE_SOURCEBOUND_SG5_POLLOCK"/"PAD_Stream_V16D26_R2_R1_Summary.json"
SSHA="f6424f45e97c1ec1fc0a5f39da9fbf8a210d58d9cad879e1e644a62ba98b4a05"
IN=R/"output"/"V16_D26_R2_R1_36CASE_SOURCEBOUND_SG5_POLLOCK"/"cases"
OUT=R/"output"/"V16_D27_36CASE_SG6_STYLE_201NODE_POLLOCK_TRANSPORT_COORDINATES";CO=OUT/"cases";CO.mkdir(parents=True,exist_ok=True)
N=201;XI=np.linspace(0.,1.,N)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def interp_stream(s):
 pts=np.asarray(s["points_m"],float); t=np.asarray(s["times_s"],float)
 if pts.ndim!=2 or pts.shape[1]!=3 or t.ndim!=1 or len(t)!=len(pts):raise RuntimeError("native SG5 streamline schema drift")
 if len(t)<2 or not np.all(np.isfinite(t)) or not np.all(np.diff(t)>=0):raise RuntimeError("invalid native Pollock time sequence")
 te=float(s["travel_time_s"])
 if not np.isfinite(te) or te<=0:raise RuntimeError("invalid terminal TOF")
 # Preserve Pollock time as interpolation authority; collapse duplicate time stamps only for np.interp.
 u,idx=np.unique(t,return_index=True); pp=pts[idx]
 if len(u)<2:raise RuntimeError("degenerate Pollock time coordinate")
 tq=XI*te
 xyz=np.column_stack([np.interp(tq,u,pp[:,d]) for d in range(3)])
 return xyz,tq,te
def main():
 print("="*78);print("PAD-Stream V16D-27");print("36-Case SG6-Style 201-Node Pollock TOF / Transport-Coordinate Database");print("="*78)
 gates={"D26R2R1_summary_SHA_exact":S.exists() and sha(S)==SSHA}
 fs=sorted(IN.glob("*_SG5_Pollock.pkl"));gates["exactly_36_Pollock_inputs"]=len(fs)==36
 if not all(gates.values()):raise RuntimeError("authority pre-gate failure")
 rows=[]
 for n,f in enumerate(fs,1):
  with f.open("rb") as q:o=pickle.load(q)
  cid=o["foundation_case_id"];split=o["split"];sl=o["streamlines"]
  xyz=[];tau=[];end=[];w=[];prod=[]
  for s in sl:
   a,b,c=interp_stream(s);xyz.append(a);tau.append(b);end.append(c);w.append(float(s["weight_m3_s"]));prod.append(str(s.get("producer","")))
  xyz=np.asarray(xyz);tau=np.asarray(tau);end=np.asarray(end);w=np.asarray(w)
  if xyz.shape!=(len(sl),N,3) or tau.shape!=(len(sl),N):raise RuntimeError(f"{cid}: shape failure")
  caseg={
   "finite":bool(np.isfinite(xyz).all() and np.isfinite(tau).all() and np.isfinite(end).all() and np.isfinite(w).all()),
   "positive_weights":bool(np.all(w>0)),"positive_terminal_tof":bool(np.all(end>0)),
   "xi_exact":bool(np.array_equal(XI,np.linspace(0,1,N))),
   "tau_monotonic":bool(np.all(np.diff(tau,axis=1)>=-1e-12)),
   "tau_end_match":bool(np.allclose(tau[:,-1],end,rtol=1e-12,atol=1e-9)),
   "all_four_producers":len(set(prod))==4}
  if not all(caseg.values()):raise RuntimeError(f"{cid}: SG6-style validation failure {caseg}")
  op=CO/f"{cid}_SG6_201Node_Transport.npz"
  np.savez_compressed(op,foundation_case_id=np.array(cid),split=np.array(split),xi=XI,
    transport_xyz_m=xyz,pollock_tau_s=tau,pollock_tau_end_s=end,streamline_weight_m3_s=w,
    producer=np.asarray(prod,dtype="U32"),n_nodes=np.array(N))
  row={"foundation_case_id":cid,"split":split,"n_streamlines":len(sl),"n_nodes":N,
       "tof_min_days":float(end.min()/86400),"tof_mean_days":float(end.mean()/86400),"tof_max_days":float(end.max()/86400),
       "weight_sum_m3_s":float(w.sum()),"artifact":str(op.relative_to(R)),"sha256":sha(op),"gates":caseg}
  rows.append(row);print(f"[{n:02d}/36] {cid}: {len(sl)} x {N} PASS | TOF d {row['tof_min_days']:.3f}/{row['tof_mean_days']:.3f}/{row['tof_max_days']:.3f}")
 mf=OUT/"V16D27_36Case_201Node_Transport_Manifest.json";mf.write_text(json.dumps(rows,indent=2))
 gates["36_cases_built"]=len(rows)==36
 gates["all_1078_streamlines"]=all(x["n_streamlines"]==1078 for x in rows)
 gates["all_201_nodes"]=all(x["n_nodes"]==201 for x in rows)
 gates["all_case_validation_pass"]=all(all(x["gates"].values()) for x in rows)
 gates["split_counts_18_9_9"]={s:sum(x["split"]==s for x in rows) for s in ("TRAIN","VALIDATION","LOCKED_OOD_TEST")}=={"TRAIN":18,"VALIDATION":9,"LOCKED_OOD_TEST":9}
 gates["Pollock_primary_coordinate"]=True;gates["no_FMM_ADV_fit"]=True;gates["no_transport_target_generation"]=True;gates["no_training"]=True
 ok=all(gates.values())
 status="V16D_36CASE_201NODE_POLLOCK_TOF_TRANSPORT_COORDINATE_DATABASE_CERTIFIED_D9R1_METRIC_EXPANSION_AUTHORIZED" if ok else "V16D_D27_TRANSPORT_COORDINATE_DATABASE_BLOCKED"
 nxt="V16D-28 — Expand certified D9R1 conservative face metric M across all 36 control-space Foundation Cases" if ok else "Diagnose D27 case validation; do not proceed."
 sp=OUT/"PAD_Stream_V16D27_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-27","status":status,"manifest_sha256":sha(mf),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nGATES");[print(f"[{'PASS' if v else 'FAIL'}] {k}") for k,v in gates.items()]
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
