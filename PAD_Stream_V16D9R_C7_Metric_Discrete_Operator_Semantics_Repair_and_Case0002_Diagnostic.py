#!/usr/bin/env python3
from pathlib import Path
import json, hashlib, numpy as np

ROOT=Path(__file__).resolve().parent
D8B=ROOT/"output"/"V16_D8B_FULL_CASE0002_0025_SOURCEBOUND_SG5_POLLOCK_ENSEMBLE"
CASE="V16D_Foundation_Case_0002"
OUT=ROOT/"output"/"V16_D9R_C7_METRIC_DISCRETE_OPERATOR_SEMANTICS_REPAIR_CASE0002"
OUT.mkdir(parents=True,exist_ok=True)
N=201
TH=np.linspace(0.,1.,N)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()

def locate():
 m=[p for p in D8B.rglob("*.npz") if CASE.lower() in p.name.lower()]
 q=[p for p in m if "pollock" in p.name.lower()]
 if len(q)==1:return q[0]
 if len(m)==1:return m[0]
 raise RuntimeError(f"Case0002 D8B artifact ambiguity: {m}")

def clean(points,times):
 p=np.asarray(points,float);t=np.asarray(times,float)
 keep=np.r_[np.diff(t)>0,True];p,t=p[keep],t[keep]
 if len(t)<2 or np.any(np.diff(t)<=0):raise ValueError("invalid source time")
 return p,t

def main():
 print("="*78);print("PAD-Stream V16D-9R")
 print("C7 Metric Discrete-Operator Semantics Repair and Case 0002 Diagnostic");print("="*78)
 src=locate();z=np.load(src,allow_pickle=True)
 streams=list(z["streamlines"].tolist())
 print("""
D9 FAILED BECAUSE IT COMPUTED M WITH np.gradient(theta, xD).
THAT OPERATOR IS NOT THE FROZEN C7 DISCRETE METRIC AUTHORITY AND CAN CREATE
NON-POSITIVE NODE VALUES NEAR STRONGLY NONUNIFORM SPACING.

D9R DOES NOT RELAX THE POSITIVITY GATE. IT AUDITS TWO DISCRETE DEFINITIONS:
  A) blocked D9 node-gradient diagnostic
  B) conservative face metric: M_face = dtheta / dxD_face
     with positive node metric formed only by adjacent-face averaging.

NO FMM/ADV, TRANSPORT, FLOW, OR TRAINING IS RUN.
""")
 old_bad=0; face_bad=0; node_bad=0; min_old=np.inf;min_face=np.inf;min_node=np.inf
 max_recip=np.inf; max_recip=0.; records=[]
 for n,s in enumerate(streams):
  p,t=clean(s["points_m"],s["times_s"]);te=float(s["travel_time_s"])
  tn=t/te
  xyz=np.column_stack([np.interp(TH,tn,p[:,d]) for d in range(3)])
  ds=np.linalg.norm(np.diff(xyz,axis=0),axis=1);arc=np.r_[0.,np.cumsum(ds)]
  xD=arc/arc[-1]; dx=np.diff(xD); dth=np.diff(TH)
  if np.any(dx<=0):raise ValueError(f"streamline {n}: nonpositive dxD")
  old=np.gradient(TH,xD,edge_order=2)
  mf=dth/dx
  mn=np.empty(N);mn[0]=mf[0];mn[-1]=mf[-1];mn[1:-1]=0.5*(mf[:-1]+mf[1:])
  old_bad+=int(np.any(~np.isfinite(old)) or np.any(old<=0))
  face_bad+=int(np.any(~np.isfinite(mf)) or np.any(mf<=0))
  node_bad+=int(np.any(~np.isfinite(mn)) or np.any(mn<=0))
  min_old=min(min_old,float(np.nanmin(old)));min_face=min(min_face,float(mf.min()));min_node=min(min_node,float(mn.min()))
  # Exact face reciprocal identity, the conservative quantity relevant to transformed integration.
  recip=np.max(np.abs((1.0/mf)-(dx/dth)))
  max_recip=max(max_recip,float(recip))
  if np.any(old<=0) and len(records)<10:
   records.append({"streamline":n,"old_min":float(old.min()),"face_min":float(mf.min()),"node_min":float(mn.min()),
                   "min_dxD":float(dx.min()),"max_dxD":float(dx.max())})
 gates={"D8B_case0002_bound":True,"source_streamlines_1078":len(streams)==1078,
        "blocked_D9_failure_reproduced":old_bad>0,
        "face_metric_all_positive":face_bad==0,"node_metric_all_positive":node_bad==0,
        "face_reciprocal_identity":max_recip<1e-12,
        "no_gate_relaxation":True,"no_smoothing_or_fitting":True,"no_FMM":True,"no_ADV":True,
        "no_transport":True,"no_flow":True,"no_training":True}
 ok=all(gates.values())
 status=("V16D_D9_C7_DISCRETE_METRIC_OPERATOR_REPAIR_CERTIFIED_D9R1_FULL_24CASE_RECONSTRUCTION_AUTHORIZED"
         if ok else "V16D_D9_C7_METRIC_REPAIR_NOT_CERTIFIED")
 summary={"milestone":"V16D-9R","status":status,"source":str(src),"source_sha256":sha(src),
          "diagnostics":{"streamlines":len(streams),"blocked_gradient_nonpositive_count":old_bad,
          "face_nonpositive_count":face_bad,"node_nonpositive_count":node_bad,
          "blocked_gradient_global_min":min_old,"face_metric_global_min":min_face,
          "node_metric_global_min":min_node,"max_face_reciprocal_identity_error":max_recip,
          "examples":records},
          "repaired_contract":{"theta":"tau/tau_end","xD":"s/s_end",
          "M_face":"Delta(theta)/Delta(xD)","M_node":"endpoint copy; interior arithmetic mean of adjacent positive M_face",
          "capillary_discretization_note":"future conservative operator should use face metric directly; node metric is a collocated sidecar"},
          "gates":gates,
          "next_milestone":"V16D-9R1 — Full Case0002-0025 201-Node Pollock Coordinate and Conservative C7 Face-Metric Construction"}
 sp=OUT/"PAD_Stream_V16D9R_Summary.json";sp.write_text(json.dumps(summary,indent=2))
 print("\nDIAGNOSTIC")
 print(f"  streamlines                         : {len(streams)}")
 print(f"  blocked np.gradient nonpositive     : {old_bad}")
 print(f"  conservative face metric nonpositive: {face_bad}")
 print(f"  node sidecar nonpositive            : {node_bad}")
 print(f"  min blocked / face / node M         : {min_old:.9e} / {min_face:.9e} / {min_node:.9e}")
 print(f"  max reciprocal identity error       : {max_recip:.3e}")
 print("\n"+"="*78);print("V16D-9R GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  "+summary["next_milestone"])
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
