#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parent
D27=ROOT/"output"/"V16_D27_36CASE_SG6_STYLE_201NODE_POLLOCK_TRANSPORT_COORDINATES"/"PAD_Stream_V16D27_Summary.json"
D27SHA="6c10ede5895bed51a9324ff8503ec3dffbf8b3d908cc077bdfb476dc65a822f1"
D9R1=ROOT/"PAD_Stream_V16D9R1_Full_Case0002_0025_201Node_Pollock_Coordinate_and_Conservative_C7_Face_Metric_Construction.py"
OUT=ROOT/"output"/"V16_D28_D9R1_SOURCE_BINDING_36CASE_METRIC_EXPANSION_AUDIT";OUT.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-28")
 print("D9R1 Source Binding + 36-Case Conservative Face-Metric Expansion Audit");print("="*78)
 gates={
  "D27_summary_exists":D27.exists(),
  "D27_summary_SHA_exact":D27.exists() and sha(D27)==D27SHA,
  "D9R1_source_exists":D9R1.exists(),
 }
 if not all(gates.values()):
  print(gates);raise RuntimeError("authority pre-gate failure")
 d27=json.loads(D27.read_text())
 gates["D27_status_authorizes_metric_expansion"]=d27.get("status")=="V16D_36CASE_201NODE_POLLOCK_TOF_TRANSPORT_COORDINATE_DATABASE_CERTIFIED_D9R1_METRIC_EXPANSION_AUTHORIZED"
 text=D9R1.read_text(encoding="utf-8",errors="replace")
 h=sha(D9R1)
 print("\nD9R1 SOURCE")
 print(" ",D9R1.name)
 print("  SHA-256:",h)
 required=[
  "TH=np.linspace(0.,1.,201)",
  'mf=dth/dx',
  'mn[0]=mf[0]',
  'mn[-1]=mf[-1]',
  'mn[1:-1]=.5*(mf[:-1]+mf[1:])',
  'invf=dx/dth',
  'M_face_dtheta_dxD=mf',
  'M_node_sidecar_dtheta_dxD=mn',
  'dxD_dtheta_face=invf',
  'NO CLIPPING, EPSILON FLOOR, SMOOTHING, FITTING, CASE SELECTION, FMM/ADV'
 ]
 for tok in required:gates["source_has_"+re.sub(r'[^A-Za-z0-9]+','_',tok)[:48]]=tok in text
 # Exact semantic contract extraction evidence.
 gates["primary_metric_is_face_ratio"]=bool(re.search(r'mf\s*=\s*dth\s*/\s*dx',text))
 gates["reciprocal_is_dx_over_dtheta"]=bool(re.search(r'invf\s*=\s*dx\s*/\s*dth',text))
 gates["node_metric_sidecar_only"]="NODE-COLLOCATED M IS SAVED ONLY AS A SIDECAR" in text
 gates["future_capillary_uses_face_metric_directly"]="THE FUTURE CONSERVATIVE CAPILLARY OPERATOR MUST USE M_face DIRECTLY" in text
 gates["no_metric_fitting_or_smoothing"]="NO CLIPPING, EPSILON FLOOR, SMOOTHING, FITTING" in text
 report={
  "milestone":"V16D-28",
  "D27_sha256":sha(D27),
  "D9R1_source":D9R1.name,
  "D9R1_sha256":h,
  "frozen_metric_contract":{
   "theta":"linspace(0,1,201)",
   "xD":"arc_length / terminal_arc_length",
   "M_face_dtheta_dxD":"Delta(theta)/Delta(xD), shape (1078,200)",
   "M_node_sidecar_dtheta_dxD":"endpoint copy; interior arithmetic mean of adjacent M_face, shape (1078,201)",
   "dxD_dtheta_face":"Delta(xD)/Delta(theta), reciprocal sidecar, shape (1078,200)",
   "capillary_authority":"M_face only",
   "node_role":"SIDECAR_ONLY",
   "prohibited":"clipping/floor/smoothing/fitting/case selection/FMM/ADV/transport/training"
  },
  "gates":gates
 }
 rp=OUT/"V16D28_D9R1_Source_Binding_Report.json";rp.write_text(json.dumps(report,indent=2))
 ok=all(gates.values())
 status="V16D_D9R1_EXACT_METRIC_SOURCE_BOUND_36CASE_D28R1_EXECUTION_AUTHORIZED" if ok else "V16D_D28_D9R1_SOURCE_BINDING_BLOCKED"
 nxt="V16D-28-R1 — Execute exact D9R1 conservative face-metric construction across all 36 control-space Foundation Cases" if ok else "Resolve D9R1 source/contract ambiguity; do not construct metrics."
 sp=OUT/"PAD_Stream_V16D28_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-28","status":status,"D9R1_sha256":h,"report_sha256":sha(rp),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
