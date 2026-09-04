#!/usr/bin/env python
from pathlib import Path
import json, csv, hashlib, math
import numpy as np

ROOT=Path(__file__).resolve().parent
D4=ROOT/"output"/"V16_D4_PREDECLARED_SGSIM_SEED_REGISTRY_CASE0002PLUS_GENERATION_CONTRACT"/"PAD_Stream_V16D4_Summary.json"
R3=ROOT/"output"/"V16_D3R3_EXPLICIT_NEW_VERSIONED_SGSIM_ENSEMBLE_RECIPE_AUTHORITY_CONTRACT"/"PAD_Stream_V16D3R3_Summary.json"
REG=ROOT/"output"/"V16_D4_PREDECLARED_SGSIM_SEED_REGISTRY_CASE0002PLUS_GENERATION_CONTRACT"/"V16D4_Predeclared_Case_Seed_Registry.csv"
OUT=ROOT/"output"/"V16_D5_DETERMINISTIC_SGSIM_RECIPE1P0_GENERATOR_IMPLEMENTATION_PREGENERATION_VALIDATION";OUT.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def cov_exp(dx,dy,dz,rx,ry,rz):
 # C(h)=exp(-3 h*) convention: declared explicitly for V16D Recipe 1.0 executable implementation.
 h=np.sqrt((dx/rx)**2+(dy/ry)**2+(dz/rz)**2)
 return np.exp(-3.0*h)

def generate_gaussian(seed,nx=50,ny=50,nz=15,dx=20.,dy=20.,dz=4.,rx=200.,ry=200.,rz=15.):
 """
 Deterministic unconditional Gaussian random field with Recipe-1.0 exponential covariance.
 Spectral covariance sampling is used as the executable implementation of the frozen
 stochastic model class. This is NOT claimed to reproduce historical SGeMS internals.
 """
 rng=np.random.default_rng(int(seed))
 # periodic embedding on native grid; construct covariance kernel by minimum wrapped distance
 ix=np.minimum(np.arange(nx),nx-np.arange(nx))*dx
 iy=np.minimum(np.arange(ny),ny-np.arange(ny))*dy
 iz=np.minimum(np.arange(nz),nz-np.arange(nz))*dz
 Z,Y,X=np.meshgrid(iz,iy,ix,indexing="ij")
 C=cov_exp(X,Y,Z,rx,ry,rz)
 lam=np.fft.fftn(C).real
 min_eig=float(lam.min())
 # Numerical/non-positive spectral modes are projected to zero; audit magnitude is reported.
 lam_pos=np.maximum(lam,0.0)
 white=rng.normal(size=(nz,ny,nx))
 F=np.fft.fftn(white)
 g=np.fft.ifftn(F*np.sqrt(lam_pos)).real
 g=(g-g.mean())/g.std(ddof=0)
 return g,min_eig,float(np.mean(lam< -1e-12)),float(lam_pos.max())

def empirical_corr(g,axis,lag):
 a=np.take(g,indices=range(g.shape[axis]-lag),axis=axis).ravel()
 b=np.take(g,indices=range(lag,g.shape[axis]),axis=axis).ravel()
 return float(np.corrcoef(a,b)[0,1])

def main():
 print("="*78);print("PAD-Stream V16D-5")
 print("Deterministic SGSim Recipe 1.0 Generator Implementation and Pre-Generation Validation");print("="*78)
 d4=json.loads(D4.read_text());r3=json.loads(R3.read_text())
 if d4["status"]!="V16D_PREDECLARED_CASE0002_0025_SGSIM_SEED_REGISTRY_FROZEN_GENERATION_EXECUTION_CAN_PROCEED":raise RuntimeError("D4 mismatch")
 if r3["status"]!="V16D_NEW_VERSIONED_SGSIM_ENSEMBLE_RECIPE_1P0_FROZEN_SEED_REGISTRY_CAN_PROCEED":raise RuntimeError("R3 mismatch")
 expected=d4["contract"]["registry_sha256"]; actual=sha(REG)
 rows=list(csv.DictReader(REG.open()))
 seed=int(rows[0]["sgsim_seed"])

 print("""
D5 IMPLEMENTS THE NEW V16D RECIPE 1.0 STOCHASTIC GENERATOR AND VALIDATES IT
ON THE FIRST PREDECLARED SEED ONLY AS A GENERATOR TEST.

THIS IS NOT YET A CERTIFIED FOUNDATION CASE AND DOES NOT RUN FLOW/TRANSPORT.
NO SEED MAY BE CHANGED AFTER SEEING THE DIAGNOSTIC REALIZATION.

IMPORTANT IMPLEMENTATION LABEL:
Recipe 1.0 specified the geological covariance model, not historical SGeMS
software internals. The executable V16D implementation uses deterministic
spectral Gaussian-field sampling of that frozen covariance model. It is NOT
claimed to reproduce historical SGeMS realization mechanics.
""")
 g1,mineig,negfrac,lmax=generate_gaussian(seed)
 g2,_,_,_=generate_gaussian(seed)
 g3,_,_,_=generate_gaussian(int(rows[1]["sgsim_seed"]))
 same=np.array_equal(g1,g2); different=not np.array_equal(g1,g3)
 finite=bool(np.isfinite(g1).all())
 mean=float(g1.mean());std=float(g1.std());mn=float(g1.min());mx=float(g1.max())
 cx1=empirical_corr(g1,2,1);cy1=empirical_corr(g1,1,1);cz1=empirical_corr(g1,0,1)
 # No goodness-of-fit gate to a single stochastic realization: diagnostics only.
 artifact=OUT/"V16D5_Generator_Diagnostic_Seed160400.npz"
 np.savez_compressed(artifact,gaussian=g1,seed=np.int64(seed),
   recipe_id=np.array("V16D_SGSIM_ENSEMBLE_RECIPE_1.0"),
   implementation=np.array("deterministic_spectral_exponential_covariance"))
 gates={
  "R3_bound":True,"D4_bound":True,"registry_hash_exact":actual==expected,
  "first_seed_exact":seed==160400,"shape_15_50_50":g1.shape==(15,50,50),
  "finite":finite,"deterministic_same_seed":same,"different_next_seed":different,
  "normalized_mean_machine_zero":abs(mean)<1e-12,
  "normalized_std_one":abs(std-1.0)<1e-12,
  "no_seed_change":True,"no_realization_rejection":True,
  "no_flow_run":True,"no_transport_run":True,"no_training":True}
 ok=all(gates.values())
 status="V16D_RECIPE1P0_DETERMINISTIC_GEOLOGY_GENERATOR_IMPLEMENTED_PREGENERATION_VALIDATED" if ok else "V16D_RECIPE1P0_GENERATOR_VALIDATION_BLOCKED"
 summary={"milestone":"V16D-5","status":status,"seed":seed,
  "implementation_authority":"NEW_V16D_DETERMINISTIC_SPECTRAL_GAUSSIAN_FIELD_IMPLEMENTATION_NOT_HISTORICAL_SGEMS_INTERNALS",
  "diagnostics":{"mean":mean,"std":std,"min":mn,"max":mx,"corr_x_lag1":cx1,"corr_y_lag1":cy1,"corr_z_lag1":cz1,
                 "spectral_min_raw_eigenvalue":mineig,"negative_spectral_mode_fraction":negfrac,"max_projected_eigenvalue":lmax},
  "artifact":{"path":str(artifact.relative_to(ROOT)),"sha256":sha(artifact)},
  "gates":gates,
  "next_milestone":"V16D-5A — Spectral Covariance Embedding Fidelity Audit Before Ensemble Generation"}
 (OUT/"PAD_Stream_V16D5_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nGENERATOR DIAGNOSTIC — PREDECLARED CASE 0002 SEED")
 print(f"  seed                  : {seed}")
 print(f"  shape                 : {g1.shape}")
 print(f"  mean/std              : {mean:.6e} / {std:.6e}")
 print(f"  min/max               : {mn:.6f} / {mx:.6f}")
 print(f"  lag-1 corr x/y/z      : {cx1:.6f} / {cy1:.6f} / {cz1:.6f}")
 print(f"  raw spectral min eig  : {mineig:.6e}")
 print(f"  negative mode fraction: {negfrac:.6e}")
 print(f"  artifact SHA-256      : {sha(artifact)}")
 print("\nNOTE: correlation values are diagnostic, not single-realization acceptance gates.")
 print("\n"+"="*78);print("V16D-5 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  V16D-5A — Spectral Covariance Embedding Fidelity Audit Before Ensemble Generation")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
