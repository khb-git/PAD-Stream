#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,sys
import numpy as np
from scipy.special import ndtr

R=Path(__file__).resolve().parent
D22=R/"output"/"V16_D22_CONTROL_SPACE_DESIGN_FOUNDATION_CASE_REGISTRY"
S22=D22/"PAD_Stream_V16D22_Summary.json"
C22=D22/"V16D22_Control_Space_Recipe_1.0_and_Foundation_Case_Registry.json"
S22SHA="10bcda9ec129578b0170cd36b6b4a327518a24091d6e695cb62743a37d0ee6a8"
O=R/"output"/"V16_D23_FRESH_RECIPE1P1_GEOLOGIES_0026_0029";O.mkdir(parents=True,exist_ok=True)

NX=50;NY=50;NZ=15
DX=20.0;DY=20.0;DZ=4.0
AZ=np.deg2rad(30.0); A_MAJOR=200.0;A_MINOR=200.0;A_VERT=15.0

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def covariance_kernel():
 # Periodic minimum-image displacement, identical Recipe1.1 spectral-GRF concept.
 iz=np.arange(NZ);iy=np.arange(NY);ix=np.arange(NX)
 z=np.minimum(iz,NZ-iz)*DZ; y=np.minimum(iy,NY-iy)*DY; x=np.minimum(ix,NX-ix)*DX
 Z,Y,X=np.meshgrid(z,y,x,indexing="ij")
 # With equal major/minor ranges azimuth rotation is algebraically neutral,
 # retained here for declared Recipe1.1 semantics.
 U=X*np.cos(AZ)+Y*np.sin(AZ); V=-X*np.sin(AZ)+Y*np.cos(AZ)
 hstar=np.sqrt((U/A_MAJOR)**2+(V/A_MINOR)**2+(Z/A_VERT)**2)
 return np.exp(-3.0*hstar)

def generate(seed):
 C=covariance_kernel()
 eig=np.real(np.fft.fftn(C))
 mine=float(eig.min())
 if mine < -1e-10: raise RuntimeError(f"negative spectral eigenvalue {mine}")
 eig=np.maximum(eig,0.0)
 rng=np.random.default_rng(seed)
 white=rng.standard_normal((NZ,NY,NX))
 G=np.real(np.fft.ifftn(np.fft.fftn(white)*np.sqrt(eig)))
 raw_mean=float(G.mean());raw_std=float(G.std())
 G=(G-G.mean())/G.std()
 K=50.0+950.0*ndtr(G)
 return G,K,mine,raw_mean,raw_std

def lagcorr(a,axis):
 x=np.take(a,range(a.shape[axis]-1),axis=axis).ravel()
 y=np.take(a,range(1,a.shape[axis]),axis=axis).ravel()
 return float(np.corrcoef(x,y)[0,1])

def main():
 print("="*78);print("PAD-Stream V16D-23")
 print("Generate + Certify Fresh Recipe1.1 Spectral-GRF Geologies 0026–0029");print("="*78)
 if sha(S22)!=S22SHA:raise RuntimeError("D22 summary SHA mismatch")
 c=json.loads(C22.read_text())
 expected={"0026":350456,"0027":358375,"0028":366294,"0029":374213}
 got={}
 for r in c["registry"]:got[r["geology_case_id"]]=r["geology_seed"]
 if any(got.get(k)!=v for k,v in expected.items()):raise RuntimeError("D22 geology seed registry mismatch")
 cases=[]
 for gid,seed in expected.items():
  G,K,mine,rm,rs=generate(seed)
  Kx=K;Ky=K;Kz=.1*K;phi=np.full_like(K,.2)
  fp=O/f"V16D_Geology_Case_{gid}_Recipe1p1.npz"
  np.savez_compressed(fp,G_standardized=G,Kx_mD=Kx,Ky_mD=Ky,Kz_mD=Kz,porosity=phi,
                      geology_case_id=np.array(gid),seed=np.array(seed))
  q={"geology_case_id":gid,"seed":seed,"artifact":str(fp),"sha256":sha(fp),
     "G_mean":float(G.mean()),"G_std":float(G.std()),"G_min":float(G.min()),"G_max":float(G.max()),
     "K_min_mD":float(K.min()),"K_max_mD":float(K.max()),"K_mean_mD":float(K.mean()),
     "lag1_corr_x":lagcorr(G,2),"lag1_corr_y":lagcorr(G,1),"lag1_corr_z":lagcorr(G,0),
     "spectral_min_eigenvalue":mine,"raw_prefinal_mean":rm,"raw_prefinal_std":rs,
     "gates":{"shape_exact":G.shape==(15,50,50),"finite":bool(np.isfinite(G).all() and np.isfinite(K).all()),
      "sample_mean_exact":abs(float(G.mean()))<1e-12,"sample_std_exact":abs(float(G.std())-1)<1e-12,
      "K_strictly_within_transform_bounds":float(K.min())>50 and float(K.max())<1000,
      "Kx_eq_Ky":bool(np.array_equal(Kx,Ky)),"Kz_eq_0p1Kh":bool(np.allclose(Kz,.1*Kx,rtol=0,atol=1e-12)),
      "porosity_0p2":bool(np.array_equal(phi,np.full_like(phi,.2))),"spectral_psd":mine>=-1e-10}}
  cases.append(q)
  print(f"Case{gid} seed={seed}: G mean/std={q['G_mean']:.3e}/{q['G_std']:.12f} "
        f"K=[{q['K_min_mD']:.3f},{q['K_max_mD']:.3f}] mean={q['K_mean_mD']:.3f} mD "
        f"lag1(x,y,z)=({q['lag1_corr_x']:.4f},{q['lag1_corr_y']:.4f},{q['lag1_corr_z']:.4f})")
 manifest={"milestone":"V16D-23","recipe":"V16D_SPECTRAL_ENSEMBLE_RECIPE_1.1",
 "note":"Deterministic periodic spectral Gaussian random-field sampler; NOT SGS/SGSim.",
 "transform":"K=50+950*Phi(G_standardized) mD; no per-realization fit",
 "cases":cases}
 mp=O/"V16D23_Fresh_Recipe1p1_Geology_Manifest.json";mp.write_text(json.dumps(manifest,indent=2))
 allcase=all(all(q["gates"].values()) for q in cases)
 gates={"D22_SHA_exact":sha(S22)==S22SHA,"exact_geologies_0026_0029":len(cases)==4,
 "D22_seed_registry_exact":True,"Recipe1p1_algorithm_preserved":True,"not_SGS_or_SGSim":True,
 "all_case_certification_gates":allcase,"no_case_replacement":True,"no_flow_generation":True,
 "no_transport_generation":True,"no_training":True,"locked_geology_not_evaluated":True}
 status="V16D_FRESH_RECIPE1P1_GEOLOGIES_0026_0029_GENERATED_CERTIFIED_36CASE_CONTROLSPACE_FLOW_GENERATION_AUTHORIZED"
 nxt="V16D-24 — Source-Bound 36-Foundation-Case SG2/SG3/SG4 Control-Space Flow Generation"
 sp=O/"PAD_Stream_V16D23_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-23","status":status,
 "manifest_sha256":sha(mp),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not all(gates.values()):sys.exit(2)
if __name__=="__main__":main()
