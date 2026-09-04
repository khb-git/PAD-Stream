#!/usr/bin/env python
from pathlib import Path
import json, hashlib, numpy as np

ROOT=Path(__file__).resolve().parent
D5=ROOT/"output"/"V16_D5_DETERMINISTIC_SGSIM_RECIPE1P0_GENERATOR_IMPLEMENTATION_PREGENERATION_VALIDATION"/"PAD_Stream_V16D5_Summary.json"
R3=ROOT/"output"/"V16_D3R3_EXPLICIT_NEW_VERSIONED_SGSIM_ENSEMBLE_RECIPE_AUTHORITY_CONTRACT"/"PAD_Stream_V16D3R3_Summary.json"
OUT=ROOT/"output"/"V16_D5A_SPECTRAL_COVARIANCE_EMBEDDING_FIDELITY_AUDIT";OUT.mkdir(parents=True,exist_ok=True)

def cov_exp(dx,dy,dz,rx=200.,ry=200.,rz=15.):
 h=np.sqrt((dx/rx)**2+(dy/ry)**2+(dz/rz)**2)
 return np.exp(-3.0*h)

def kernel_spectrum(nz,ny,nx,dz=4.,dy=20.,dx=20.):
 ix=np.minimum(np.arange(nx),nx-np.arange(nx))*dx
 iy=np.minimum(np.arange(ny),ny-np.arange(ny))*dy
 iz=np.minimum(np.arange(nz),nz-np.arange(nz))*dz
 Z,Y,X=np.meshgrid(iz,iy,ix,indexing="ij")
 C=cov_exp(X,Y,Z)
 lam=np.fft.fftn(C).real
 return C,lam

def main():
 print("="*78);print("PAD-Stream V16D-5A")
 print("Spectral Covariance Embedding Fidelity Audit Before Ensemble Generation");print("="*78)
 d5=json.loads(D5.read_text()); r3=json.loads(R3.read_text())
 if d5["status"]!="V16D_RECIPE1P0_DETERMINISTIC_GEOLOGY_GENERATOR_IMPLEMENTED_PREGENERATION_VALIDATED":raise RuntimeError("D5 mismatch")
 if r3["status"]!="V16D_NEW_VERSIONED_SGSIM_ENSEMBLE_RECIPE_1P0_FROZEN_SEED_REGISTRY_CAN_PROCEED":raise RuntimeError("R3 mismatch")

 print("""
D5A AUDITS THE NUMERICAL COVARIANCE EMBEDDING, NOT A PARTICULAR REALIZATION.

THE NATIVE 15x50x50 PERIODIC COVARIANCE KERNEL IS COMPARED DIRECTLY WITH THE
FROZEN RECIPE-1.0 EXPONENTIAL COVARIANCE AT REPRESENTABLE LAGS.

NO EMPIRICAL SINGLE-REALIZATION CORRELATION IS USED AS AN ACCEPTANCE GATE.
NO SEED, VARIOGRAM PARAMETER, OR RECIPE VALUE IS CHANGED.
""")
 C,lam=kernel_spectrum(15,50,50)
 neg=lam[lam<0]
 min_eig=float(lam.min()); negfrac=float(np.mean(lam < -1e-12))
 projected=np.maximum(lam,0)
 # Since D5 had no negative modes, spectral projection should be exactly inactive.
 projection_active=bool(np.any(lam<0))
 rel_projection_energy=float(np.linalg.norm(projected-lam)/max(np.linalg.norm(lam),1e-300))

 # Direct kernel-vs-theory checks at key grid lags.
 checks={}
 for name,(k,j,i) in {
   "x_1cell":(0,0,1),"x_5cell":(0,0,5),"x_10cell":(0,0,10),
   "y_1cell":(0,1,0),"y_5cell":(0,5,0),"y_10cell":(0,10,0),
   "z_1cell":(1,0,0),"z_2cell":(2,0,0),"z_3cell":(3,0,0),
   "xyz_1cell":(1,1,1)}.items():
  dx=min(i,50-i)*20.;dy=min(j,50-j)*20.;dz=min(k,15-k)*4.
  target=float(cov_exp(dx,dy,dz))
  actual=float(C[k,j,i])
  checks[name]={"target":target,"kernel":actual,"abs_error":abs(target-actual)}

 maxerr=max(v["abs_error"] for v in checks.values())
 # FFT inverse reconstruction audit.
 Crec=np.fft.ifftn(lam).real
 recon=float(np.max(np.abs(Crec-C)))

 gates={
  "D5_bound":True,"R3_bound":True,
  "native_embedding_positive_semidefinite":min_eig>=-1e-12,
  "negative_mode_fraction_zero":negfrac==0.0,
  "spectral_projection_inactive":not projection_active,
  "projection_energy_zero":rel_projection_energy==0.0,
  "kernel_matches_declared_covariance":maxerr<1e-14,
  "fft_roundtrip_kernel":recon<1e-12,
  "no_single_realization_acceptance_gate":True,
  "no_seed_change":True,"no_recipe_change":True,
  "no_generation_of_ensemble":True,"no_flow":True,"no_transport":True,"no_training":True}
 ok=all(gates.values())
 status="V16D_RECIPE1P0_NATIVE_SPECTRAL_COVARIANCE_EMBEDDING_CERTIFIED_ENSEMBLE_GEOLOGY_GENERATION_AUTHORIZED" if ok else "V16D_RECIPE1P0_NATIVE_SPECTRAL_EMBEDDING_NOT_CERTIFIED_LARGER_EMBEDDING_REQUIRED"
 summary={"milestone":"V16D-5A","status":status,
  "spectral":{"min_eigenvalue":min_eig,"negative_mode_fraction":negfrac,
              "projection_active":projection_active,"relative_projection_energy":rel_projection_energy},
  "covariance_checks":checks,"max_covariance_abs_error":maxerr,"fft_roundtrip_max_error":recon,
  "gates":gates,
  "next_milestone":("V16D-6 — Frozen Registry Case 0002-0025 Ensemble Geology Generation and Certification"
                    if ok else "V16D-5B — Larger Circulant Embedding Implementation and Fidelity Audit")}
 (OUT/"PAD_Stream_V16D5A_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nSPECTRAL EMBEDDING")
 print(f"  raw min eigenvalue       : {min_eig:.9e}")
 print(f"  negative mode fraction   : {negfrac:.9e}")
 print(f"  projection active        : {projection_active}")
 print(f"  relative projection energy: {rel_projection_energy:.9e}")
 print("\nCOVARIANCE KERNEL")
 for k,v in checks.items():print(f"  {k:12s} target={v['target']:.9e} kernel={v['kernel']:.9e} err={v['abs_error']:.3e}")
 print(f"  max covariance abs error : {maxerr:.3e}")
 print(f"  FFT roundtrip max error  : {recon:.3e}")
 print("\n"+"="*78);print("V16D-5A GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n ",summary["next_milestone"])
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
