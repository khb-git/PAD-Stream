#!/usr/bin/env python
from pathlib import Path
import json,csv,hashlib
import numpy as np

ROOT=Path(__file__).resolve().parent
D5A=ROOT/"output"/"V16_D5A_SPECTRAL_COVARIANCE_EMBEDDING_FIDELITY_AUDIT"/"PAD_Stream_V16D5A_Summary.json"
D4=ROOT/"output"/"V16_D4_PREDECLARED_SGSIM_SEED_REGISTRY_CASE0002PLUS_GENERATION_CONTRACT"/"PAD_Stream_V16D4_Summary.json"
R3=ROOT/"output"/"V16_D3R3_EXPLICIT_NEW_VERSIONED_SGSIM_ENSEMBLE_RECIPE_AUTHORITY_CONTRACT"/"PAD_Stream_V16D3R3_Summary.json"
REG=ROOT/"output"/"V16_D4_PREDECLARED_SGSIM_SEED_REGISTRY_CASE0002PLUS_GENERATION_CONTRACT"/"V16D4_Predeclared_Case_Seed_Registry.csv"
TRANSFORM=ROOT/"transform_sgsim_perm.py"
OUT=ROOT/"output"/"V16_D6_FROZEN_REGISTRY_CASE0002_0025_ENSEMBLE_GEOLOGY_GENERATION_CERTIFICATION"
CASES=OUT/"cases";CASES.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def cov_exp(dx,dy,dz,rx=200.,ry=200.,rz=15.):
 return np.exp(-3.0*np.sqrt((dx/rx)**2+(dy/ry)**2+(dz/rz)**2))

def gaussian(seed):
 nx=ny=50;nz=15;dx=dy=20.;dz=4.
 rng=np.random.default_rng(int(seed))
 ix=np.minimum(np.arange(nx),nx-np.arange(nx))*dx
 iy=np.minimum(np.arange(ny),ny-np.arange(ny))*dy
 iz=np.minimum(np.arange(nz),nz-np.arange(nz))*dz
 Z,Y,X=np.meshgrid(iz,iy,ix,indexing="ij")
 C=cov_exp(X,Y,Z)
 lam=np.fft.fftn(C).real
 if lam.min() < -1e-12: raise RuntimeError("Certified D5A spectrum unexpectedly changed.")
 w=rng.normal(size=(nz,ny,nx))
 g=np.fft.ifftn(np.fft.fftn(w)*np.sqrt(np.maximum(lam,0))).real
 return (g-g.mean())/g.std(ddof=0)

def transform_source_semantics():
 # Bind the source; do not import/run it because the historical script may be CLI-oriented.
 text=TRANSFORM.read_text(errors="ignore")
 return text

def fixed_v16d_transform(g):
 """
 V16D deterministic no-refit transform preserving frozen support [50,1000] mD.
 Uses the standard-normal CDF mapped to bounded permeability support.
 Injection interval layers 6-10 receive the same transform law; no realization-specific fit.
 This implementation is explicitly V16D and does not claim byte-for-byte historical transform execution.
 """
 # erf without scipy dependency
 from math import erf
 cdf=np.vectorize(lambda x:0.5*(1.0+erf(x/np.sqrt(2.0))),otypes=[float])(g)
 k=50.0+950.0*cdf
 return k.astype(np.float64)

def corr(a,b):
 return float(np.corrcoef(a.ravel(),b.ravel())[0,1])

def main():
 print("="*78);print("PAD-Stream V16D-6")
 print("Frozen Registry Case 0002-0025 Ensemble Geology Generation and Certification");print("="*78)
 d5a=json.loads(D5A.read_text());d4=json.loads(D4.read_text());r3=json.loads(R3.read_text())
 if d5a["status"]!="V16D_RECIPE1P0_NATIVE_SPECTRAL_COVARIANCE_EMBEDDING_CERTIFIED_ENSEMBLE_GEOLOGY_GENERATION_AUTHORIZED":raise RuntimeError("D5A mismatch")
 if d4["status"]!="V16D_PREDECLARED_CASE0002_0025_SGSIM_SEED_REGISTRY_FROZEN_GENERATION_EXECUTION_CAN_PROCEED":raise RuntimeError("D4 mismatch")
 if sha(REG)!=d4["contract"]["registry_sha256"]:raise RuntimeError("Registry hash mismatch")
 if not TRANSFORM.exists():raise RuntimeError("transform_sgsim_perm.py missing")
 expected_t=r3["transform_source"]["sha256"]
 if sha(TRANSFORM)!=expected_t:raise RuntimeError("Transform source hash mismatch")
 _=transform_source_semantics()
 rows=list(csv.DictReader(REG.open()))
 print("""
D6 GENERATES EVERY PREDECLARED GEOLOGY IN ASCENDING CASE-ID ORDER.
NO CASE IS REJECTED FOR APPEARANCE OR STATISTICS. CERTIFICATION CHECKS ONLY
EXECUTION/CONTRACT INVARIANTS, NOT WHETHER A REALIZATION IS 'GOOD'.

IMPORTANT TRANSFORM AUTHORITY:
The historical transform source is SHA-bound. Because Recipe 1.0 is a new V16D
ensemble, D6 uses an explicit deterministic bounded standard-normal-CDF
permeability transform with fixed [50,1000] mD support and NO per-case fitting.
This V16D transform is recorded separately and is not mislabeled as historical
source execution.
""")
 records=[]; arrays=[]
 for n,row in enumerate(rows,1):
  cid=row["case_id"];seed=int(row["sgsim_seed"])
  try:
   g=gaussian(seed);k=fixed_v16d_transform(g)
   kx=k;ky=k;kz=0.10*k;phi=np.full_like(k,0.20)
   cp=CASES/f"{cid}_Geology.npz"
   np.savez_compressed(cp,gaussian=g,Kx_mD=kx,Ky_mD=ky,Kz_mD=kz,porosity=phi,
      seed=np.int64(seed),case_id=np.array(cid),recipe_id=np.array("V16D_SGSIM_ENSEMBLE_RECIPE_1.0"),
      transform_id=np.array("V16D_FIXED_NORMAL_CDF_50_1000_MD_V1"))
   rec={"case_id":cid,"seed":seed,"status":"GENERATED","sha256":sha(cp),
        "g_mean":float(g.mean()),"g_std":float(g.std()),"g_min":float(g.min()),"g_max":float(g.max()),
        "K_min_mD":float(k.min()),"K_mean_mD":float(k.mean()),"K_max_mD":float(k.max()),
        "KzKh_mean":float(np.mean(kz/kx)),"phi_mean":float(phi.mean())}
   arrays.append(g)
  except Exception as e:
   rec={"case_id":cid,"seed":seed,"status":"TECHNICAL_FAILURE","sha256":"",
        "g_mean":"","g_std":"","g_min":"","g_max":"","K_min_mD":"","K_mean_mD":"","K_max_mD":"",
        "KzKh_mean":"","phi_mean":"","error":repr(e)}
  records.append(rec)
  print(f"[{n:02d}/24] {cid} seed={seed} -> {rec['status']}")
 fields=sorted(set().union(*(r.keys() for r in records)))
 man=OUT/"V16D6_Ensemble_Geology_Manifest.csv"
 with man.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
 success=[r for r in records if r["status"]=="GENERATED"]
 # Diversity diagnostic only, never rejection criterion.
 pair=[]
 if len(arrays)>1:
  for i in range(len(arrays)):
   for j in range(i+1,len(arrays)):pair.append(corr(arrays[i],arrays[j]))
 pair=np.array(pair,float) if pair else np.array([])
 gates={
  "D5A_bound":True,"D4_registry_exact":True,"R3_transform_source_exact":True,
  "all_24_registry_entries_attempted":len(records)==24,
  "all_24_generated":len(success)==24,
  "case_ids_unchanged":[r["case_id"] for r in records]==[r["case_id"] for r in rows],
  "seeds_unchanged":[r["seed"] for r in records]==[int(r["sgsim_seed"]) for r in rows],
  "all_shapes_contract":all(np.load(CASES/f"{r['case_id']}_Geology.npz")["Kx_mD"].shape==(15,50,50) for r in success),
  "all_finite":all(np.isfinite(np.load(CASES/f"{r['case_id']}_Geology.npz")["Kx_mD"]).all() for r in success),
  "K_support":all(float(r["K_min_mD"])>=50 and float(r["K_max_mD"])<=1000 for r in success),
  "KzKh_0p10":all(abs(float(r["KzKh_mean"])-0.1)<1e-14 for r in success),
  "phi_0p20":all(abs(float(r["phi_mean"])-0.2)<1e-14 for r in success),
  "no_cherrypicking":True,"no_seed_replacement":True,"no_per_case_transform_fit":True,
  "no_flow":True,"no_transport":True,"no_training":True}
 ok=all(v if isinstance(v,bool) else bool(v) for v in gates.values())
 status="V16D_CASE0002_0025_ENSEMBLE_GEOLOGIES_GENERATED_CERTIFIED_READY_FOR_MULTI_CASE_FLOW_PIPELINE" if ok else "V16D_ENSEMBLE_GEOLOGY_GENERATION_HAS_DOCUMENTED_TECHNICAL_FAILURES"
 summary={"milestone":"V16D-6","status":status,"generated_count":len(success),
  "manifest":{"path":str(man.relative_to(ROOT)),"sha256":sha(man)},
  "transform":{"historical_source_sha256":expected_t,"V16D_execution":"V16D_FIXED_NORMAL_CDF_50_1000_MD_V1"},
  "diversity_diagnostic":{"pairwise_gaussian_corr_min":float(pair.min()) if pair.size else None,
                          "median":float(np.median(pair)) if pair.size else None,
                          "max":float(pair.max()) if pair.size else None},
  "gates":gates,
  "next_milestone":"V16D-7 — Multi-Case SG2/SG3/SG4 Pressure-Flux Physics Pipeline Execution and Certification"}
 (OUT/"PAD_Stream_V16D6_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nENSEMBLE SUMMARY")
 print(f"  generated             : {len(success)}/24")
 print(f"  manifest SHA-256      : {sha(man)}")
 if pair.size:
  print(f"  pairwise G corr min/median/max: {pair.min():.4f} / {np.median(pair):.4f} / {pair.max():.4f}")
 print("  Diversity statistics are diagnostic only; no realization was selected/rejected by them.")
 print("\n"+"="*78);print("V16D-6 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if bool(v) else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  V16D-7 — Multi-Case SG2/SG3/SG4 Pressure-Flux Physics Pipeline Execution and Certification")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
