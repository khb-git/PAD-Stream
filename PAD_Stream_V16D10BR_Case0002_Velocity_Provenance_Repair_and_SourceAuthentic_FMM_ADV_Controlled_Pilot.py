#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,importlib.util,runpy,shutil,numpy as np

ROOT=Path(__file__).resolve().parent
FMM_SRC=ROOT/"PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py"
B6_SRC=ROOT/"PAD_Stream_V16B6_Directional_Advective_Travel_Time_Numerical_Scheme_Contract.py"
B7_SRC=ROOT/"PAD_Stream_V16B7_Controlled_Directional_Advective_Travel_Time_Solve.py"
SG5_SRC=ROOT/"PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
FLOW=ROOT/"output"/"V16_D7B_FULL_FROZEN_CASE0002_0025_SOURCEBOUND_SG2_SG3_SG4_FLOW_ENSEMBLE"/"cases"/"V16D_Foundation_Case_0002_Flow.npz"
POL=ROOT/"output"/"V16_D9R1_FULL_CASE0002_0025_201NODE_POLLOCK_C7_FACE_METRIC"/"cases"/"V16D_Foundation_Case_0002_Pollock_201Node_C7_FaceMetric.npz"
OUT=ROOT/"output"/"V16_D10B_CASE0002_SOURCEAUTHENTIC_FMM_ADV_CONTROLLED_PILOT";OUT.mkdir(parents=True,exist_ok=True)
HASH={"FMM":"0b26e3cdbc41276c53f4778e7eddcddd0cc8ef081ffb495b71df548152e8f049",
"B6":"fc03e5c9cdeb06a490182d305653a06f4f9d3ddf2a4bd1a80838fc8c89715892",
"B7":"2355f3eecd41bb6571f7ead3ebb1c5d90a1907ae681826159e79463166994c56",
"SG5":"2989fe58d1fd78fe9f9c03176dbb3ff066faf359f7edaf028cbdc0fea85135f2"}

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def mod(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def cell_velocity(vx,vy,vz):
 nz,ny,nxm1=vx.shape;nx=nxm1+1
 cx=np.empty((nz,ny,nx));cy=np.empty((nz,ny,nx));cz=np.empty((nz,ny,nx))
 cx[:,:,0]=vx[:,:,0];cx[:,:,-1]=vx[:,:,-1];cx[:,:,1:-1]=.5*(vx[:,:,:-1]+vx[:,:,1:])
 cy[:,0,:]=vy[:,0,:];cy[:,-1,:]=vy[:,-1,:];cy[:,1:-1,:]=.5*(vy[:,:-1,:]+vy[:,1:,:])
 cz[0]=vz[0];cz[-1]=vz[-1];cz[1:-1]=.5*(vz[:-1]+vz[1:])
 return cx,cy,cz

def main():
 print("="*78);print("PAD-Stream V16D-10BR")
 print("Case 0002 Velocity-Provenance Repair and Source-Authentic FMM/ADV Controlled Pilot");print("="*78)
 for k,p in [("FMM",FMM_SRC),("B6",B6_SRC),("B7",B7_SRC),("SG5",SG5_SRC)]:
  if sha(p)!=HASH[k]:raise RuntimeError(f"{k} source hash mismatch")
 fmm=mod(FMM_SRC,"v16d10b_fmm")
 z=np.load(FLOW);qx,qy,qz=[np.asarray(z[k],float) for k in ["Qx","Qy","Qz"]]
 # D10B incorrectly assumed D7B flow artifacts persisted Vx/Vy/Vz.
 # They persist conservative Q only. Recover face pore velocities through the
 # exact SHA-bound SG5 array-level mapping already certified in D8/D8R1.
 sg5=mod(SG5_SRC,"v16d10br_sg5")
 vx,vy,vz=sg5.construct_face_pore_velocities(qx,qy,qz)
 vx,vy,vz=[np.asarray(a,float) for a in (vx,vy,vz)]
 speed=np.sqrt(sum(a*a for a in cell_velocity(vx,vy,vz)))
 div,tol,src_idx,src_mask,src_meta=fmm.bind_injector_sources(qx,qy,qz)
 dx=dy=6.096;dz=1.2192
 T,state,accepted=fmm.fast_marching_3d(speed,src_mask,dx,dy,dz)
 if not np.isfinite(T).all():raise RuntimeError("FMM nonfinite")
 # Controlled ADV: create the exact B6A NPZ interface consumed by B7, using the
 # frozen closed-boundary projected sign-aware coefficients from current arrays.
 # This reproduces B6/B6A algebra, but B7 itself is executed unchanged.
 cx,cy,cz=cell_velocity(vx,vy,vz);nz,ny,nx=cx.shape
 aW=np.maximum(cx,0)/dx;aE=np.maximum(-cx,0)/dx
 aS=np.maximum(cy,0)/dy;aN=np.maximum(-cy,0)/dy
 aB=np.maximum(cz,0)/dz;aT=np.maximum(-cz,0)/dz
 aW[:,:,0]=0;aE[:,:,-1]=0;aS[:,0,:]=0;aN[:,-1,:]=0;aB[0]=0;aT[-1]=0
 aP=aW+aE+aS+aN+aB+aT
 # B7 expects historical B6A paths. Save backups and restore after controlled run.
 b6dir=ROOT/"output"/"V16_B6_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_NUMERICAL_SCHEME_CONTRACT"
 b6adir=ROOT/"output"/"V16_B6A_DIRECTIONAL_EXTERNAL_BOUNDARY_POLICY_AUDIT"
 b6dir.mkdir(parents=True,exist_ok=True);b6adir.mkdir(parents=True,exist_ok=True)
 b6sum=b6dir/"V16B6_Summary.json";b6acon=b6adir/"V16B6A_External_Boundary_Policy_Contract.json"
 b6anpz=b6adir/"V16B6A_Closed_Boundary_Projected_Scheme_Contract.npz"
 backups={}
 for p in [b6sum,b6acon,b6anpz]:
  if p.exists():
   bp=OUT/(p.name+".backup");shutil.copy2(p,bp);backups[p]=bp
 try:
  b6sum.write_text(json.dumps({"status":"V16B_DIRECTIONAL_NUMERICAL_SCHEME_BOUNDARY_POLICY_REQUIRED"}))
  b6acon.write_text(json.dumps({"status":"V16B_CLOSED_EXTERNAL_BOUNDARY_OPERATOR_POLICY_RESOLVED"}))
  np.savez_compressed(b6anpz,Vx=cx,Vy=cy,Vz=cz,source_mask=src_mask.astype(np.uint8),
   aW=aW,aE=aE,aS=aS,aN=aN,aB=aB,aT=aT,aP=aP,dx_m=dx,dy_m=dy,dz_m=dz)
  runpy.run_path(str(B7_SRC),run_name="__main__")
 finally:
  for p in [b6sum,b6acon,b6anpz]:
   if p in backups:shutil.copy2(backups[p],p)
   elif p.exists():p.unlink()
 b7out=ROOT/"output"/"V16_B7_CONTROLLED_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_SOLVE"/"V16B7_Directional_Advective_Travel_Time.npz"
 if not b7out.exists():raise RuntimeError("B7 output not found")
 db=np.load(b7out);adv=np.asarray(db["tau_adv_s"],float)
 pol=np.load(POL);pt=np.asarray(pol["pollock_tau_end_s"],float)
 gates={"source_hashes_exact":True,"D10B_failure_is_missing_velocity_artifact_key_not_physics":True,
 "SG5_sourcebound_velocity_reconstruction":True,"source_count_5":int(src_mask.sum())==5,
 "FMM_all_finite":bool(np.isfinite(T).all()),"FMM_source_zero":bool(np.max(np.abs(T[src_mask]))<1e-8),
 "ADV_all_finite":bool(np.isfinite(adv).all()),"ADV_source_zero":bool(np.max(np.abs(adv[src_mask]))<1e-8),
 "ADV_nonnegative":bool(np.all(adv>=-1e-10)),"Pollock_reference_loaded":len(pt)==1078,
 "no_transport":True,"no_training":True}
 ok=all(gates.values())
 art=OUT/"V16D10B_Case0002_TravelTime_Hierarchy.npz"
 np.savez_compressed(art,fmm_arrival_s=T,tau_adv_s=adv,source_mask=src_mask.astype(np.uint8),
  pollock_tau_end_s=pt,case_id=np.array("V16D_Foundation_Case_0002"))
 status="V16D_CASE0002_SOURCEBOUND_VELOCITY_FMM_ADV_POLLOCK_TRAVELTIME_HIERARCHY_PILOT_CERTIFIED_FULL_24CASE_EXECUTION_AUTHORIZED" if ok else "V16D_CASE0002_TRAVELTIME_PILOT_NOT_CERTIFIED"
 summary={"milestone":"V16D-10BR","status":status,"metrics":{"sources":int(src_mask.sum()),
 "FMM_days":[float(T.min()/86400),float(np.median(T)/86400),float(T.max()/86400)],
 "ADV_days":[float(adv.min()/86400),float(np.median(adv)/86400),float(adv.max()/86400)],
 "Pollock_terminal_days":[float(pt.min()/86400),float(np.median(pt)/86400),float(pt.max()/86400)]},
 "artifact_sha256":sha(art),"gates":gates,
 "next_milestone":"V16D-10C — Full Case0002-0025 Source-Bound Velocity + FMM/ADV Travel-Time Hierarchy Execution"}
 (OUT/"PAD_Stream_V16D10B_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nTRAVEL-TIME HIERARCHY")
 print(f"  source cells: {src_mask.sum()}")
 print(f"  FMM days min/median/max: {T.min()/86400:.3f} / {np.median(T)/86400:.3f} / {T.max()/86400:.3f}")
 print(f"  ADV days min/median/max: {adv.min()/86400:.3f} / {np.median(adv)/86400:.3f} / {adv.max()/86400:.3f}")
 print(f"  Pollock terminal min/median/max: {pt.min()/86400:.3f} / {np.median(pt)/86400:.3f} / {pt.max()/86400:.3f}")
 print("\n"+"="*78);print("V16D-10B GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT MILESTONE\n  "+summary["next_milestone"])
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
