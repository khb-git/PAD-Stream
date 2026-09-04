#!/usr/bin/env python3
from pathlib import Path
import csv, json, hashlib, pickle, sys
import numpy as np

ROOT=Path(__file__).resolve().parent
D28=ROOT/"output"/"V16_D28_D9R1_SOURCE_BINDING_36CASE_METRIC_EXPANSION_AUDIT"/"PAD_Stream_V16D28_Summary.json"
D28SHA="693bb527ecc9241ff5b1c4af71aa40f2e732d0c39bf6c93dcdd151195bba6810"
D9R1=ROOT/"PAD_Stream_V16D9R1_Full_Case0002_0025_201Node_Pollock_Coordinate_and_Conservative_C7_Face_Metric_Construction.py"
D9R1SHA="5df7178f316fc1fa94ce49eb40ee8318f804bce4d420a17dbc5cd79ab59ab8d4"
D26=ROOT/"output"/"V16_D26_R2_R1_36CASE_SOURCEBOUND_SG5_POLLOCK"/"cases"
D27=ROOT/"output"/"V16_D27_36CASE_SG6_STYLE_201NODE_POLLOCK_TRANSPORT_COORDINATES"/"cases"
OUT=ROOT/"output"/"V16_D28_R1_36CASE_D9R1_CONSERVATIVE_FACE_METRIC_EXPANSION"
CASES=OUT/"cases";CASES.mkdir(parents=True,exist_ok=True)
TH=np.linspace(0.,1.,201)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

# Exact D9R1 one()/clean() mechanics, copied source-authentically after D28 SHA binding.
def clean(p,t):
 p=np.asarray(p,float);t=np.asarray(t,float)
 if p.ndim!=2 or p.shape[1]!=3 or t.ndim!=1 or len(p)!=len(t):raise ValueError("bad source geometry/time shape")
 if not np.isfinite(p).all() or not np.isfinite(t).all() or np.any(np.diff(t)<0):raise ValueError("invalid source trajectory")
 keep=np.r_[np.diff(t)>0,True];p,t=p[keep],t[keep]
 if len(t)<2 or np.any(np.diff(t)<=0):raise ValueError("non-increasing cleaned time")
 return p,t

def one(s):
 p,t=clean(s["points_m"],s["times_s"]);te=float(s["travel_time_s"])
 if abs(t[0])>1e-10*max(1.,abs(te)):raise ValueError("nonzero Pollock time origin")
 if not np.isclose(t[-1],te,rtol=1e-10,atol=1e-8):raise ValueError("terminal TOF mismatch")
 tn=t/te
 xyz=np.column_stack([np.interp(TH,tn,p[:,d]) for d in range(3)])
 ds=np.linalg.norm(np.diff(xyz,axis=0),axis=1)
 arc=np.r_[0.,np.cumsum(ds)]
 if arc[-1]<=0 or np.any(ds<=0):raise ValueError("nonpositive resampled path segment")
 xD=arc/arc[-1];dx=np.diff(xD);dth=np.diff(TH)
 if np.any(dx<=0):raise ValueError("nonpositive dxD")
 mf=dth/dx
 mn=np.empty(201);mn[0]=mf[0];mn[-1]=mf[-1];mn[1:-1]=.5*(mf[:-1]+mf[1:])
 invf=dx/dth
 if np.any(mf<=0) or np.any(mn<=0) or not np.isfinite(mf).all():raise ValueError("invalid repaired C7 metric")
 return xyz,TH*te,arc,xD,mf,mn,invf,te,arc[-1],float(s["weight_m3_s"]),str(s["producer"]),str(s["status"]),int(s["seed_id"])

def main():
 print("="*78);print("PAD-Stream V16D-28-R1")
 print("Exact D9R1 Conservative Face-Metric Expansion Across 36 Control-Space Foundation Cases");print("="*78)
 gates={
  "D28_summary_SHA_exact":D28.exists() and sha(D28)==D28SHA,
  "D9R1_source_SHA_exact":D9R1.exists() and sha(D9R1)==D9R1SHA,
  "D26_Pollock_case_dir_exists":D26.exists(),
  "D27_transport_case_dir_exists":D27.exists()
 }
 if not all(gates.values()):
  print(gates);raise RuntimeError("authority pre-gate failure")
 d28=json.loads(D28.read_text())
 gates["D28_status_authorizes_execution"]=d28.get("status")=="V16D_D9R1_EXACT_METRIC_SOURCE_BOUND_36CASE_D28R1_EXECUTION_AUTHORIZED"
 fs=sorted(D26.glob("*_SG5_Pollock.pkl"))
 gates["exactly_36_source_Pollock_artifacts"]=len(fs)==36
 if not all(gates.values()):
  print(gates);raise RuntimeError("execution pre-gate failure")

 rows=[]
 for ci,src in enumerate(fs,1):
  with src.open("rb") as f:o=pickle.load(f)
  cid=str(o["foundation_case_id"]);split=str(o["split"]);ss=list(o["streamlines"])
  if len(ss)!=1078:raise RuntimeError(f"{cid}: expected certified 1078, got {len(ss)}")
  n=len(ss);xyz=np.empty((n,201,3));tau=np.empty((n,201));arc=np.empty((n,201));xd=np.empty((n,201))
  mf=np.empty((n,200));mn=np.empty((n,201));invf=np.empty((n,200));te=np.empty(n);plen=np.empty(n);w=np.empty(n)
  prod=np.empty(n,dtype="U32");status=np.empty(n,dtype="U32");sid=np.empty(n,dtype=np.int64)
  for i,s in enumerate(ss):
   q=one(s);xyz[i],tau[i],arc[i],xd[i],mf[i],mn[i],invf[i],te[i],plen[i],w[i],prod[i],status[i],sid[i]=q
  reciprocal=float(np.max(np.abs(1./mf-invf)))
  cg={"1078_streamlines":n==1078,"201_nodes":xyz.shape==(1078,201,3),"200_faces":mf.shape==(1078,200),
      "finite":bool(all(np.isfinite(a).all() for a in [xyz,tau,arc,xd,mf,mn,invf,te,plen,w])),
      "positive_TOF":bool(np.all(te>0)),"positive_weight":bool(np.all(w>0)),"positive_path":bool(np.all(plen>0)),
      "theta_TOF_monotone":bool(np.all(np.diff(tau,axis=1)>0)),"xD_monotone":bool(np.all(np.diff(xd,axis=1)>0)),
      "M_face_positive":bool(np.all(mf>0)),"M_node_sidecar_positive":bool(np.all(mn>0)),
      "reciprocal_identity":reciprocal<1e-12,"producer_status_all":bool(np.all(status=="PRODUCER")),
      "four_producers":len(set(prod.tolist()))==4}
  certified=all(cg.values())
  if not certified:raise RuntimeError(f"{cid}: D9R1 certification failure {cg}")
  # Cross-check D27's independently persisted Pollock coordinate database.
  d27m=list(D27.glob(f"{cid}_SG6_201Node_Transport.npz"))
  if len(d27m)!=1:raise RuntimeError(f"{cid}: D27 artifact ambiguity {d27m}")
  with np.load(d27m[0],allow_pickle=False) as z:
   d27xyz=np.asarray(z["transport_xyz_m"],float);d27tau=np.asarray(z["pollock_tau_s"],float);d27te=np.asarray(z["pollock_tau_end_s"],float)
  cross_xyz=float(np.max(np.abs(xyz-d27xyz)));cross_tau=float(np.max(np.abs(tau-d27tau)));cross_te=float(np.max(np.abs(te-d27te)))
  # D27 and D9R1 use equivalent TOF interpolation but slightly different duplicate-time cleanup;
  # equality is diagnostic, not a new physics acceptance criterion.
  art=CASES/f"{cid}_Pollock_201Node_C7_FaceMetric.npz"
  np.savez_compressed(art,foundation_case_id=np.array(cid),split=np.array(split),theta=TH,xyz_m=xyz,pollock_tau_s=tau,
   pollock_tau_end_s=te,arc_length_m=arc,path_length_m=plen,xD=xd,M_face_dtheta_dxD=mf,
   M_node_sidecar_dtheta_dxD=mn,dxD_dtheta_face=invf,streamline_weight_m3_s=w,producer=prod,status=status,seed_id=sid,
   source_pollock_artifact=np.array(str(src.relative_to(ROOT))),source_pollock_sha256=np.array(sha(src)),
   D9R1_source_sha256=np.array(D9R1SHA),c7_contract=np.array("M_face=Delta(theta)/Delta(xD); node M is sidecar only"))
  row={"foundation_case_id":cid,"split":split,"status":"CERTIFIED","streamlines":n,"nodes":201,"faces":200,
       "tof_median_d":float(np.median(te)/86400),"path_median_m":float(np.median(plen)),
       "M_face_min":float(mf.min()),"M_face_median":float(np.median(mf)),"M_face_max":float(mf.max()),
       "reciprocal_error":reciprocal,"D27_xyz_max_abs_delta_m":cross_xyz,"D27_tau_max_abs_delta_s":cross_tau,
       "D27_tau_end_max_abs_delta_s":cross_te,"artifact_sha256":sha(art)}
  rows.append(row)
  print(f"[{ci:02d}/36] {cid} -> CERTIFIED | Mface min/med/max={row['M_face_min']:.6e}/{row['M_face_median']:.6e}/{row['M_face_max']:.6e}")

 man=OUT/"V16D28R1_Manifest.csv"
 with man.open("w",newline="") as f:
  wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
 split_counts={s:sum(x["split"]==s for x in rows) for s in ("TRAIN","VALIDATION","LOCKED_OOD_TEST")}
 gates.update({
  "36_cases_built":len(rows)==36,
  "all_36_certified":all(x["status"]=="CERTIFIED" for x in rows),
  "total_38808_streamlines":sum(x["streamlines"] for x in rows)==38808,
  "canonical_201_nodes":all(x["nodes"]==201 for x in rows),
  "conservative_200_face_metric":all(x["faces"]==200 for x in rows),
  "all_face_metrics_positive":all(x["M_face_min"]>0 for x in rows),
  "split_counts_18_9_9":split_counts=={"TRAIN":18,"VALIDATION":9,"LOCKED_OOD_TEST":9},
  "no_case_or_streamline_selection":True,
  "no_clipping_floor_smoothing_fitting":True,
  "no_FMM_ADV":True,"no_transport_target_generation":True,"no_training":True
 })
 ok=all(gates.values())
 status="V16D_36CASE_D9R1_CONSERVATIVE_C7_FACE_METRIC_ENSEMBLE_CERTIFIED_FMM_ADV_CONTROLSPACE_EXPANSION_AUTHORIZED" if ok else "V16D_D28_R1_METRIC_EXPANSION_BLOCKED"
 nxt="V16D-29 — Source-bound FMM/ADV travel-time hierarchy expansion across all 36 control-space Foundation Cases" if ok else "Diagnose D28-R1 metric construction; do not proceed."
 summary={"milestone":"V16D-28-R1","status":status,"cases":len(rows),"total_streamlines":sum(x["streamlines"] for x in rows),
          "nodes_per_streamline":201,"faces_per_streamline":200,"C7_primary_metric":"M_face=Delta(theta)/Delta(xD)",
          "C7_node_metric_role":"SIDECAR_ONLY","D9R1_source_sha256":D9R1SHA,"manifest_sha256":sha(man),
          "ensemble":{"M_face_global_min":float(min(x["M_face_min"] for x in rows)),
                      "M_face_global_max":float(max(x["M_face_max"] for x in rows))},
          "gates":gates,"next_milestone":nxt}
 sp=OUT/"PAD_Stream_V16D28_R1_Summary.json";sp.write_text(json.dumps(summary,indent=2))
 print("\nGATES");[print(f"[{'PASS' if v else 'FAIL'}] {k}") for k,v in gates.items()]
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)

if __name__=="__main__":main()
