#!/usr/bin/env python3
from pathlib import Path
import csv,json,hashlib,numpy as np

ROOT=Path(__file__).resolve().parent
D8B=ROOT/"output"/"V16_D8B_FULL_CASE0002_0025_SOURCEBOUND_SG5_POLLOCK_ENSEMBLE"
D9R=ROOT/"output"/"V16_D9R_C7_METRIC_DISCRETE_OPERATOR_SEMANTICS_REPAIR_CASE0002"/"PAD_Stream_V16D9R_Summary.json"
OUT=ROOT/"output"/"V16_D9R1_FULL_CASE0002_0025_201NODE_POLLOCK_C7_FACE_METRIC";CASES=OUT/"cases";CASES.mkdir(parents=True,exist_ok=True)
TH=np.linspace(0.,1.,201); CASE_IDS=[f"V16D_Foundation_Case_{i:04d}" for i in range(2,26)]

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def locate(cid):
 m=[p for p in D8B.rglob("*.npz") if cid.lower() in p.name.lower()]
 q=[p for p in m if "pollock" in p.name.lower()]
 if len(q)==1:return q[0]
 if len(m)==1:return m[0]
 raise RuntimeError(f"{cid}: artifact ambiguity {m}")

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
 print("="*78);print("PAD-Stream V16D-9R1")
 print("Full Case0002-0025 201-Node Pollock Coordinate and Conservative C7 Face-Metric Construction");print("="*78)
 r=json.loads(D9R.read_text())
 if r["status"]!="V16D_D9_C7_DISCRETE_METRIC_OPERATOR_REPAIR_CERTIFIED_D9R1_FULL_24CASE_RECONSTRUCTION_AUTHORIZED":raise RuntimeError("D9R authority mismatch")
 print("""
D9R1 APPLIES THE CERTIFIED D9R REPAIR TO ALL 24 CASES.

PRIMARY C7 DISCRETE METRIC:
    M_face[j+1/2] = Delta(theta) / Delta(x_D)

NODE-COLLOCATED M IS SAVED ONLY AS A SIDECAR FOR MODEL/DIAGNOSTIC USE.
THE FUTURE CONSERVATIVE CAPILLARY OPERATOR MUST USE M_face DIRECTLY.

NO CLIPPING, EPSILON FLOOR, SMOOTHING, FITTING, CASE SELECTION, FMM/ADV,
TRANSPORT, OR TRAINING IS PERFORMED.
""")
 rows=[]
 for ci,cid in enumerate(CASE_IDS,1):
  src=locate(cid);z=np.load(src,allow_pickle=True);ss=list(z["streamlines"].tolist())
  if len(ss)!=1078:raise RuntimeError(f"{cid}: expected certified 1078, got {len(ss)}")
  n=len(ss);xyz=np.empty((n,201,3));tau=np.empty((n,201));arc=np.empty((n,201));xd=np.empty((n,201))
  mf=np.empty((n,200));mn=np.empty((n,201));invf=np.empty((n,200));te=np.empty(n);plen=np.empty(n);w=np.empty(n)
  prod=np.empty(n,dtype="U32");status=np.empty(n,dtype="U32");sid=np.empty(n,dtype=np.int64)
  for i,s in enumerate(ss):
   q=one(s);xyz[i],tau[i],arc[i],xd[i],mf[i],mn[i],invf[i],te[i],plen[i],w[i],prod[i],status[i],sid[i]=q
  reciprocal=float(np.max(np.abs(1./mf-invf)))
  gates={"1078_streamlines":n==1078,"201_nodes":xyz.shape==(1078,201,3),"200_faces":mf.shape==(1078,200),
   "finite":bool(all(np.isfinite(a).all() for a in [xyz,tau,arc,xd,mf,mn,invf,te,plen,w])),
   "positive_TOF":bool(np.all(te>0)),"positive_weight":bool(np.all(w>0)),"positive_path":bool(np.all(plen>0)),
   "theta_TOF_monotone":bool(np.all(np.diff(tau,axis=1)>0)),"xD_monotone":bool(np.all(np.diff(xd,axis=1)>0)),
   "M_face_positive":bool(np.all(mf>0)),"M_node_sidecar_positive":bool(np.all(mn>0)),
   "reciprocal_identity":reciprocal<1e-12,"producer_status_all":bool(np.all(status=="PRODUCER")),
   "four_producers":len(set(prod.tolist()))==4}
  certified=all(gates.values())
  art=CASES/f"{cid}_Pollock_201Node_C7_FaceMetric.npz"
  np.savez_compressed(art,theta=TH,xyz_m=xyz,pollock_tau_s=tau,pollock_tau_end_s=te,
   arc_length_m=arc,path_length_m=plen,xD=xd,M_face_dtheta_dxD=mf,
   M_node_sidecar_dtheta_dxD=mn,dxD_dtheta_face=invf,streamline_weight_m3_s=w,
   producer=prod,status=status,seed_id=sid,source_d8b_artifact=str(src),source_d8b_sha256=sha(src),
   c7_contract=np.array("M_face=Delta(theta)/Delta(xD); node M is sidecar only"))
  row={"case_id":cid,"status":"CERTIFIED" if certified else "FAILED","streamlines":n,
   "tof_min_d":float(te.min()/86400),"tof_median_d":float(np.median(te)/86400),"tof_max_d":float(te.max()/86400),
   "path_median_m":float(np.median(plen)),"M_face_min":float(mf.min()),"M_face_median":float(np.median(mf)),
   "M_face_max":float(mf.max()),"reciprocal_error":reciprocal,"artifact_sha256":sha(art)}
  rows.append(row)
  print(f"[{ci:02d}/24] {cid} -> {row['status']} | TOF50={row['tof_median_d']:.3f} d | Mface_min={row['M_face_min']:.6e}")
 man=OUT/"V16D9R1_Manifest.csv"
 with man.open("w",newline="") as f:
  wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
 good=[x for x in rows if x["status"]=="CERTIFIED"]
 gates={"D9R_authority_bound":True,"exact_24_cases":len(rows)==24,"all_24_certified":len(good)==24,
  "total_25872_streamlines":sum(x["streamlines"] for x in rows)==25872,"canonical_201_nodes":True,
  "conservative_200_face_metric":True,"all_face_metrics_positive":len(good)==24 and all(x["M_face_min"]>0 for x in good),
  "no_case_or_streamline_selection":True,"no_clipping_floor_smoothing_fitting":True,
  "no_FMM":True,"no_ADV":True,"no_transport":True,"no_training":True}
 gates={k:bool(v) for k,v in gates.items()};ok=all(gates.values())
 status=("V16D_CASE0002_0025_POLLOCK_201NODE_CONSERVATIVE_C7_FACE_METRIC_ENSEMBLE_CERTIFIED_READY_FOR_MULTICASE_FMM_ADV_TRAVELTIME_HIERARCHY"
         if ok else "V16D_D9R1_BLOCKED")
 summary={"milestone":"V16D-9R1","status":status,"cases":24,"total_streamlines":25872,
  "nodes_per_streamline":201,"faces_per_streamline":200,
  "C7_primary_metric":"M_face=Delta(theta)/Delta(xD)",
  "C7_node_metric_role":"SIDECAR_ONLY","manifest_sha256":sha(man),"gates":gates,
  "ensemble":{"tof_median_case_min_d":float(min(x["tof_median_d"] for x in rows)),
   "tof_median_case_median_d":float(np.median([x["tof_median_d"] for x in rows])),
   "tof_median_case_max_d":float(max(x["tof_median_d"] for x in rows)),
   "M_face_global_min":float(min(x["M_face_min"] for x in rows)),
   "M_face_global_max":float(max(x["M_face_max"] for x in rows))},
  "next_milestone":"V16D-10 — Multi-Case FMM/ADV Travel-Time Hierarchy Construction and Certification"}
 sp=OUT/"PAD_Stream_V16D9R1_Summary.json";sp.write_text(json.dumps(summary,indent=2))
 print("\n"+"="*78);print("V16D-9R1 ENSEMBLE SUMMARY");print("="*78)
 print(f"  certified cases       : {len(good)}/24")
 print(f"  total trajectories     : {sum(x['streamlines'] for x in rows)}")
 print(f"  nodes / faces          : 201 / 200")
 print(f"  M_face global min/max  : {summary['ensemble']['M_face_global_min']:.6e} / {summary['ensemble']['M_face_global_max']:.6e}")
 print(f"  manifest SHA-256       : {sha(man)}")
 print("\n"+"="*78);print("V16D-9R1 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  "+summary["next_milestone"])
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
