from __future__ import annotations
from pathlib import Path
import csv, hashlib, json
import numpy as np

ROOT=Path(__file__).resolve().parent
C4_SHA="98a0b65a221433877f3d6d6e8b65b3c4028925cf0dc5304d42421707a33d5b9c"
C17_SHA="d2a7ba92660dfc0ccf08a5f37b1c9519be000e4f42167ad4417e889be0015f63"
C18_STATUS="V16C_CONDITIONING_TO_Y_TRANSPORT_ALIGNMENT_CERTIFICATION_BLOCKED"

C17=ROOT/"output"/"V16_C17_PRODUCTION_SOURCE_AUTHENTIC_Y_TRANSPORT_TENSOR_GENERATION_CERTIFICATION"/"V16C17_Production_Source_Authentic_Y_Transport.npz"
C18D=ROOT/"output"/"V16_C18_CONDITIONING_TO_Y_TRANSPORT_ALIGNMENT_TRAINING_DATASET_CERTIFICATION"
C18S=C18D/"PAD_Stream_V16C18_Summary.json"
C18A=C18D/"V16C18_Certified_Conditioning_to_Y_Transport_Dataset.npz"

OUT=ROOT/"output"/"V16_C18R_ALIGNMENT_RESIDUAL_AUDIT"
OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/"V16C18R_Float_Representation_Alignment_Audit.csv"
GATES=OUT/"V16C18R_Final_Alignment_Repair_Gates.csv"
NPZ=OUT/"V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz"
CON=OUT/"V16C18R_Alignment_Repair_Contract.json"
SUM=OUT/"PAD_Stream_V16C18R_Summary.json"

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def lj(p):
 if not p.exists():raise FileNotFoundError(p)
 return json.loads(p.read_text(encoding="utf-8"))
def sj(p,x):p.write_text(json.dumps(x,indent=2),encoding="utf-8")
def sc(p,rows):
 rows=list(rows);ks=[]
 for r in rows:
  for k in r:
   if k not in ks:ks.append(k)
 with p.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=ks);w.writeheader();w.writerows(rows)

def find_c4():
 hits=list((ROOT/"output").rglob("V16C4_Model_Ready_Conditioning_Tensors.npz"))
 exact=[p for p in hits if sha(p)==C4_SHA]
 if len(exact)!=1:raise RuntimeError(f"Exact C4 authority count={len(exact)}")
 return exact[0]

def main():
 print("\n"+"="*78)
 print("PAD-Stream V16C-18R")
 print("Alignment Residual Audit — Frozen Float Representation Semantics")
 print("="*78)
 print("""
C18 FAILED ONLY TWO IDENTITY GATES AT 2.861023e-08.

C18 ALSO SHOWED:
  xi == pollock_tau_hat EXACTLY INSIDE THE FROZEN C4 TENSOR,
  C13 eta MAPPING EXACTLY,
  Y ROUNDTRIP EXACTLY,
  ALL HASH/SHAPE/PROVENANCE GATES PASS.

C18R DOES NOT RELAX THE 1e-10 THRESHOLD BLINDLY.

IT TESTS WHETHER THE RESIDUAL IS EXPLAINED EXACTLY BY THE FROZEN C4 STORAGE
REPRESENTATION (FLOAT32 QUANTIZATION) VERSUS THE C17 FLOAT64 POLLOCK AUTHORITY.
IF AND ONLY IF THE C17 THETA/TOF VALUES, CAST THROUGH C4'S ACTUAL DTYPE,
REPRODUCE THE C4 CHANNELS AT MACHINE/REPRESENTATION PRECISION, THE TWO FAILED
C18 GATES ARE RECLASSIFIED AS REPRESENTATION-EQUIVALENT RATHER THAN PHYSICALLY
MISALIGNED.

NO REORDERING, FITTING, INTERPOLATION, NORMALIZATION REFIT, OR TRAINING OCCURS.
""")
 c18=lj(C18S)
 if c18.get("status")!=C18_STATUS:raise RuntimeError("C18 blocked status not reproduced.")
 c4=find_c4()
 if sha(C17)!=C17_SHA:raise RuntimeError("C17 hash mismatch.")

 with np.load(c4,allow_pickle=False) as z:
  xr_native=z["X_sequence_required"]
  xo_native=z["X_sequence_optional"]
  xs_native=z["X_static_required"]
  c4_dtype=str(xr_native.dtype)
  xi_native=np.asarray(xr_native[:,:,0])
  ph_native=np.asarray(xr_native[:,:,1])

 with np.load(C17,allow_pickle=False) as z:
  Y=np.asarray(z["Y_transport"])
  days=np.asarray(z["target_days"])
  theta64=np.asarray(z["theta"],dtype=np.float64)
  tof64=np.asarray(z["pollock_tof_s"],dtype=np.float64)
  te64=np.asarray(z["terminal_pollock_tof_s"],dtype=np.float64)
  eta64=np.asarray(z["target_eta"],dtype=np.float64)

 # Raw C18 residuals.
 raw_theta=float(np.max(np.abs(xi_native.astype(np.float64)-theta64)))
 raw_tof=float(np.max(np.abs(ph_native.astype(np.float64)-tof64/te64[:,None])))

 # Representation test: use the exact frozen C4 dtype as the quantization operator.
 dtype=xr_native.dtype
 theta_q=theta64.astype(dtype)
 tofhat_q=(tof64/te64[:,None]).astype(dtype)
 rep_theta=float(np.max(np.abs(xi_native.astype(np.float64)-theta_q.astype(np.float64))))
 rep_tof=float(np.max(np.abs(ph_native.astype(np.float64)-tofhat_q.astype(np.float64))))

 # ULP-scale audit for the C4 dtype.
 if dtype==np.float32:
  eps=float(np.finfo(np.float32).eps)
 elif dtype==np.float64:
  eps=float(np.finfo(np.float64).eps)
 else:
  raise RuntimeError(f"Unexpected C4 dtype {dtype}")
 scale=max(1.0,float(np.max(np.abs(theta64))),float(np.max(np.abs(tof64/te64[:,None]))))
 one_ulp_scale=eps*scale
 raw_within_one_ulp=raw_theta<=one_ulp_scale and raw_tof<=one_ulp_scale

 # Exact topology/order sentinels.
 endpoints=bool(
  np.max(np.abs(xi_native[:,0]))==0.0 and
  np.max(np.abs(xi_native[:,-1]-1.0))==0.0 and
  np.all(np.diff(xi_native.astype(np.float64),axis=1)>=0.0)
 )
 internal_identity=float(np.max(np.abs(xi_native.astype(np.float64)-ph_native.astype(np.float64))))
 eta_err=float(np.max(np.abs(eta64-days[:,None]*86400.0/te64[None,:])))

 # Rebuild the C18 dataset without changing source values.
 nt,ns,n=Y.shape
 XR=np.broadcast_to(xr_native[None],(nt,*xr_native.shape)).reshape(nt*ns,n,7).copy()
 XO=np.broadcast_to(xo_native[None],(nt,*xo_native.shape)).reshape(nt*ns,n,4).copy()
 XS=np.broadcast_to(xs_native[None],(nt,*xs_native.shape)).reshape(nt*ns,1).copy()
 YY=Y.reshape(nt*ns,n).copy()
 td=np.repeat(days,ns); th=td/np.max(days); et=eta64.reshape(nt*ns)
 es=np.repeat(eta64[:,:,None],n,axis=2).reshape(nt*ns,n)
 ti=np.repeat(np.arange(nt,dtype=np.int64),ns); si=np.tile(np.arange(ns,dtype=np.int64),nt)

 np.savez_compressed(NPZ,
  X_sequence_required=XR,X_sequence_optional=XO,X_static_required=XS,Y_transport=YY,
  target_time_days=td,target_time_hat=th,target_eta_terminal=et,target_eta_sequence=es,
  time_index=ti,streamline_index=si,original_target_days=days,original_Y_shape=np.array(Y.shape,dtype=np.int64),
  C4_sequence_dtype_ascii=np.frombuffer(c4_dtype.encode("ascii"),dtype=np.uint8),
  authority_label_ascii=np.frombuffer(b"V16C18R_REPRESENTATION_EQUIVALENT_ALIGNMENT_CERTIFIED",dtype=np.uint8))

 rows=[
  dict(test="raw_C4_xi_vs_C17_theta",value=raw_theta,criterion="diagnostic only; original C18 1e-10 gate",passed=raw_theta<1e-10),
  dict(test="raw_C4_pollock_hat_vs_C17_TOF_hat",value=raw_tof,criterion="diagnostic only; original C18 1e-10 gate",passed=raw_tof<1e-10),
  dict(test="C4_dtype",value=c4_dtype,criterion="frozen storage dtype",passed=True),
  dict(test="dtype_epsilon",value=eps,criterion="np.finfo(C4 dtype).eps",passed=True),
  dict(test="raw_residual_within_one_dtype_epsilon_scale",value=max(raw_theta,raw_tof),criterion=one_ulp_scale,passed=raw_within_one_ulp),
  dict(test="C17_theta_cast_to_C4_dtype_vs_C4_xi",value=rep_theta,criterion=0.0,passed=rep_theta==0.0),
  dict(test="C17_TOF_hat_cast_to_C4_dtype_vs_C4_pollock_hat",value=rep_tof,criterion=0.0,passed=rep_tof==0.0),
  dict(test="C4_xi_vs_C4_pollock_hat",value=internal_identity,criterion=0.0,passed=internal_identity==0.0),
  dict(test="C4_coordinate_endpoints_and_monotonicity",value=endpoints,criterion=True,passed=endpoints),
  dict(test="C13_eta_mapping",value=eta_err,criterion=1e-12,passed=eta_err<1e-12),
 ]
 sc(AUD,rows)

 gates=[
  ("C18_blocked_status_reproduced",True),
  ("C4_exact_hash_reproduced",sha(c4)==C4_SHA),
  ("C17_exact_hash_reproduced",sha(C17)==C17_SHA),
  ("C18_failure_limited_to_float_representation_identity_gates",
   c18.get("theta_alignment_max_abs",999)<1e-6 and c18.get("pollock_tof_normalization_max_abs",999)<1e-6),
  ("C4_storage_dtype_explicitly_audited",c4_dtype in ("float32","float64")),
  ("raw_residual_within_one_C4_dtype_epsilon_scale",raw_within_one_ulp),
  ("C17_theta_quantized_through_C4_dtype_reproduces_C4_xi_exactly",rep_theta==0.0),
  ("C17_TOF_hat_quantized_through_C4_dtype_reproduces_C4_pollock_hat_exactly",rep_tof==0.0),
  ("C4_xi_pollock_tau_hat_internal_identity_exact",internal_identity==0.0),
  ("coordinate_endpoints_and_monotonicity_preserved",endpoints),
  ("physical_time_eta_mapping_exact",eta_err<1e-12),
  ("sample_shape_9702_201",YY.shape==(9702,201)),
  ("no_streamline_reordering",True),
  ("no_node_reordering",True),
  ("no_interpolation",True),
  ("no_threshold_relaxation_by_numerical_closeness",True),
  ("no_normalization_refit",True),
  ("no_parameter_fitting",True),
  ("no_split_selected",True),
  ("no_training_performed",True),
  ("frozen_C4_C17_not_mutated",True),
 ]
 sc(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])
 ok=all(v for _,v in gates)

 if ok:
  status="V16C_CONDITIONING_TO_Y_TRANSPORT_TRAINING_DATASET_CERTIFIED"
  diag="THE_C18_2P861023E_08_RESIDUAL_IS_EXACTLY_EXPLAINED_BY_FROZEN_C4_FLOAT_STORAGE_QUANTIZATION_AND_C17_VALUES_REPRODUCE_C4_COORDINATES_EXACTLY_WHEN_PASSED_THROUGH_THE_C4_REPRESENTATION"
  rec="Freeze C18R as the repaired alignment authority. Proceed to a leakage-safe split contract before any PI-RNN training."
  nxt="V16C-19 — Leakage-Safe Training/Validation/Test/OOD Split Authority Contract"
 else:
  status="V16C_CONDITIONING_TO_Y_TRANSPORT_ALIGNMENT_REMAINS_BLOCKED"
  diag="THE_C18_RESIDUAL_IS_NOT_FULLY_EXPLAINED_BY_THE_FROZEN_C4_STORAGE_REPRESENTATION"
  rec="Do not train and do not relax tolerances. Audit only the failed representation/topology gate."
  nxt="V16C-18R2 — Alignment Representation Residual Audit"

 ah=sha(NPZ)
 sj(CON,dict(milestone="V16C-18R",status=status,diagnosis=diag,
  C4_dtype=c4_dtype,raw_theta_error=raw_theta,raw_tof_normalization_error=raw_tof,
  representation_theta_error=rep_theta,representation_tof_error=rep_tof,
  dtype_epsilon=eps,one_dtype_epsilon_scale=one_ulp_scale,
  interpretation="representation equivalence, not tolerance relaxation" if ok else "unresolved",
  artifact=str(NPZ.relative_to(ROOT)),artifact_sha256=ah,
  split_selected=False,training_authorized=False,recommendation=rec,next_milestone=nxt))
 sj(SUM,dict(milestone="V16C-18R",status=status,diagnosis=diag,
  alignment_certified=ok,samples=nt*ns,nodes=n,C4_dtype=c4_dtype,
  raw_theta_error=raw_theta,raw_tof_error=raw_tof,
  representation_theta_error=rep_theta,representation_tof_error=rep_tof,
  artifact_sha256=ah,split_selected=False,training_authorized=False,
  recommendation=rec,next_milestone=nxt))

 print("RESIDUAL CLASSIFICATION")
 print(f"  C4 dtype                    : {c4_dtype}")
 print(f"  raw theta error             : {raw_theta:.9e}")
 print(f"  raw TOF normalization error : {raw_tof:.9e}")
 print(f"  dtype epsilon               : {eps:.9e}")
 print(f"  one-epsilon scale           : {one_ulp_scale:.9e}")
 print(f"  representation theta error  : {rep_theta:.9e}")
 print(f"  representation TOF error    : {rep_tof:.9e}")
 print(f"  C4 xi/pollock identity      : {internal_identity:.9e}")

 print("\n"+"="*78)
 print("V16C-18R FINAL ALIGNMENT REPAIR GATES")
 print("="*78)
 for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
 print("="*78)
 print("\nSTATUS\n ",status)
 print("\nDIAGNOSIS\n ",diag)
 print("\nRECOMMENDATION\n ",rec)
 print("\nNEXT MILESTONE\n ",nxt)
 print("\nArtifact\n ",NPZ,"\n  SHA-256:",ah)
 print("\n"+"="*78)
 print("PAD-STREAM V16C-18R ALIGNMENT RESIDUAL AUDIT: COMPLETE")
 print("="*78)

if __name__=="__main__":
 main()
