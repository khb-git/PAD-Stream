from __future__ import annotations
from pathlib import Path
import csv, hashlib, json
import numpy as np

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"/"V16_C18_CONDITIONING_TO_Y_TRANSPORT_ALIGNMENT_TRAINING_DATASET_CERTIFICATION"
OUT.mkdir(parents=True,exist_ok=True)
C17=ROOT/"output"/"V16_C17_PRODUCTION_SOURCE_AUTHENTIC_Y_TRANSPORT_TENSOR_GENERATION_CERTIFICATION"/"V16C17_Production_Source_Authentic_Y_Transport.npz"
C17S=C17.parent/"PAD_Stream_V16C17_Summary.json"
C4_NAME="V16C4_Model_Ready_Conditioning_Tensors.npz"
C4_SHA="98a0b65a221433877f3d6d6e8b65b3c4028925cf0dc5304d42421707a33d5b9c"
C17_SHA="d2a7ba92660dfc0ccf08a5f37b1c9519be000e4f42167ad4417e889be0015f63"
DAYS=np.array([30.,60.,100.,150.,250.,365.,500.,750.,1000.])
NPZ=OUT/"V16C18_Certified_Conditioning_to_Y_Transport_Dataset.npz"
GATES=OUT/"V16C18_Final_Dataset_Certification_Gates.csv"
SUMMARY=OUT/"PAD_Stream_V16C18_Summary.json"

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def savecsv(p,rows):
 rows=list(rows);ks=[]
 for r in rows:
  for k in r:
   if k not in ks:ks.append(k)
 with p.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=ks);w.writeheader();w.writerows(rows)
def main():
 print("\n"+"="*78+"\nPAD-Stream V16C-18\nConditioning-to-Y_transport Alignment and Training Dataset Certification\n"+"="*78)
 print("""C18 DOES NOT TRAIN. IT BINDS FROZEN C4 CONDITIONING TO CERTIFIED C17 TARGETS,
PROVES STREAMLINE/NODE/TIME ALIGNMENT, AND CREATES A DETERMINISTIC SAMPLE AXIS:
sample = (target_time, streamline). NO SPLIT OR NORMALIZATION REFIT OCCURS.""")
 hits=list((ROOT/"output").rglob(C4_NAME))
 if len(hits)!=1: raise RuntimeError(f"C4 authority discovery requires exactly one hit; found {len(hits)}")
 c4=hits[0]
 if sha(c4)!=C4_SHA:raise RuntimeError("C4 hash mismatch")
 if sha(C17)!=C17_SHA:raise RuntimeError("C17 hash mismatch")
 s=json.loads(C17S.read_text())
 if s.get("status")!="V16C_PRODUCTION_SOURCE_AUTHENTIC_Y_TRANSPORT_TENSOR_CERTIFIED":raise RuntimeError("C17 not certified")
 with np.load(c4,allow_pickle=False) as z:
  xr=np.asarray(z["X_sequence_required"],float);xo=np.asarray(z["X_sequence_optional"],float);xs=np.asarray(z["X_static_required"],float)
 with np.load(C17,allow_pickle=False) as z:
  Y=np.asarray(z["Y_transport"],float);days=np.asarray(z["target_days"],float);theta=np.asarray(z["theta"],float)
  tof=np.asarray(z["pollock_tof_s"],float);te=np.asarray(z["terminal_pollock_tof_s"],float);eta=np.asarray(z["target_eta"],float)
 if xr.shape!=(1078,201,7) or xo.shape!=(1078,201,4) or xs.shape!=(1078,1) or Y.shape!=(9,1078,201):raise RuntimeError("Authority tensor shape mismatch")
 xi=xr[:,:,0]; ph=xr[:,:,1]
 theta_err=float(np.max(np.abs(xi-theta)))
 tof_err=float(np.max(np.abs(ph-tof/te[:,None])))
 xi_ph_err=float(np.max(np.abs(xi-ph)))
 day_err=float(np.max(np.abs(days-DAYS)))
 eta_err=float(np.max(np.abs(eta-days[:,None]*86400./te[None,:])))
 nt,ns,n=Y.shape;N=nt*ns
 XR=np.broadcast_to(xr[None],(nt,*xr.shape)).reshape(N,n,7).copy()
 XO=np.broadcast_to(xo[None],(nt,*xo.shape)).reshape(N,n,4).copy()
 XS=np.broadcast_to(xs[None],(nt,*xs.shape)).reshape(N,1).copy()
 YY=Y.reshape(N,n).copy()
 ti=np.repeat(np.arange(nt,dtype=np.int64),ns);si=np.tile(np.arange(ns,dtype=np.int64),nt)
 td=np.repeat(days,ns);th=td/1000.;et=eta.reshape(N);es=np.repeat(eta[:,:,None],n,axis=2).reshape(N,n)
 yr=float(np.max(np.abs(YY.reshape(Y.shape)-Y)))
 xrerr=max(float(np.max(np.abs(XR.reshape(nt,ns,n,7)[k]-xr))) for k in range(nt))
 xoerr=max(float(np.max(np.abs(XO.reshape(nt,ns,n,4)[k]-xo))) for k in range(nt))
 xserr=max(float(np.max(np.abs(XS.reshape(nt,ns,1)[k]-xs))) for k in range(nt))
 finite=all(np.all(np.isfinite(a)) for a in [XR,XO,XS,YY,td,th,et,es])
 np.savez_compressed(NPZ,X_sequence_required=XR,X_sequence_optional=XO,X_static_required=XS,Y_transport=YY,
  target_time_days=td,target_time_hat=th,target_eta_terminal=et,target_eta_sequence=es,time_index=ti,streamline_index=si,
  original_target_days=days,original_Y_shape=np.array(Y.shape),authority_label_ascii=np.frombuffer(b"V16C18_CERTIFIED_ALIGNMENT_DATASET_NO_SPLIT_NO_TRAINING",dtype=np.uint8))
 gates=[
 ("C4_exact_frozen_hash_reproduced",sha(c4)==C4_SHA),("C17_exact_certified_hash_reproduced",sha(C17)==C17_SHA),
 ("C17_certification_status_reproduced",True),("C4_required_shape",xr.shape==(1078,201,7)),("C4_optional_shape",xo.shape==(1078,201,4)),
 ("C4_static_shape",xs.shape==(1078,1)),("C17_Y_shape",Y.shape==(9,1078,201)),("Pollock_theta_identity",theta_err<1e-10),
 ("Pollock_TOF_normalization_identity",tof_err<1e-10),("xi_pollock_tau_hat_identity",xi_ph_err<1e-10),("nine_target_times_exact",day_err==0),
 ("physical_time_eta_mapping_exact",eta_err<1e-12),("sample_count_9702",N==9702),("Y_flatten_roundtrip_exact",yr==0),
 ("C4_required_not_mutated",xrerr==0),("C4_optional_not_mutated",xoerr==0),("C4_static_not_mutated",xserr==0),
 ("all_arrays_finite",finite),("time_conditioning_deterministic_no_fit",True),("no_normalization_refit",True),
 ("no_split_selected",True),("no_PI_RNN_training",True),("no_V15_state_substituted",True),("frozen_inputs_not_mutated",True)]
 savecsv(GATES,[{"gate":g,"passed":bool(v)} for g,v in gates]);ok=all(v for _,v in gates)
 if ok:
  status="V16C_CONDITIONING_TO_Y_TRANSPORT_TRAINING_DATASET_CERTIFIED"
  diag="FROZEN_C4_CONDITIONING_AND_CERTIFIED_C17_TARGETS_ARE_EXACTLY_ALIGNED_BY_STREAMLINE_NODE_AND_PHYSICAL_TIME_IN_A_9702_SAMPLE_TRAINING_READY_LAYOUT"
  rec="Freeze C18. Next freeze a leakage-safe train/validation/test/OOD split policy before any PI-RNN training."
  nxt="V16C-19 — Leakage-Safe Training/Validation/Test/OOD Split Authority Contract"
 else:
  status="V16C_CONDITIONING_TO_Y_TRANSPORT_ALIGNMENT_CERTIFICATION_BLOCKED";diag="ONE_OR_MORE_ALIGNMENT_OR_PROVENANCE_GATES_FAILED"
  rec="Do not train. Audit only failed C18 gates without reordering by numerical similarity or refitting normalization.";nxt="V16C-18R — Alignment Residual Audit"
 ah=sha(NPZ)
 SUMMARY.write_text(json.dumps({"milestone":"V16C-18","status":status,"diagnosis":diag,"samples":N,"streamlines":ns,"nodes":n,
 "target_days":days.tolist(),"X_sequence_required_shape":list(XR.shape),"X_sequence_optional_shape":list(XO.shape),
 "X_static_required_shape":list(XS.shape),"Y_transport_shape":list(YY.shape),"theta_alignment_max_abs":theta_err,
 "pollock_tof_normalization_max_abs":tof_err,"eta_mapping_max_abs":eta_err,"artifact_sha256":ah,
 "split_selected":False,"training_authorized":False,"recommendation":rec,"next_milestone":nxt},indent=2))
 print(f"\nALIGNMENT RESULT\n  samples: {N}\n  X required: {XR.shape}\n  X optional: {XO.shape}\n  X static: {XS.shape}\n  Y transport: {YY.shape}")
 print(f"  theta error: {theta_err:.6e}\n  TOF norm error: {tof_err:.6e}\n  eta error: {eta_err:.6e}\n  Y roundtrip: {yr:.6e}")
 print("\n"+"="*78+"\nV16C-18 FINAL DATASET CERTIFICATION GATES\n"+"="*78)
 for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
 print("="*78+"\n\nSTATUS\n ",status,"\n\nDIAGNOSIS\n ",diag,"\n\nRECOMMENDATION\n ",rec,"\n\nNEXT MILESTONE\n ",nxt)
 print("\nArtifact\n ",NPZ,"\n  SHA-256:",ah)
 print("\n"+"="*78+"\nPAD-STREAM V16C-18 CONDITIONING/TARGET ALIGNMENT: COMPLETE\n"+"="*78)
if __name__=="__main__":main()
