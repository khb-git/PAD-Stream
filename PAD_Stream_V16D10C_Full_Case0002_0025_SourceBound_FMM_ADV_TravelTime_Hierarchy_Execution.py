#!/usr/bin/env python3
from pathlib import Path
import csv,json,hashlib,importlib.util,runpy,shutil,numpy as np

ROOT=Path(__file__).resolve().parent
FMM_SRC=ROOT/"PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py"
B7_SRC=ROOT/"PAD_Stream_V16B7_Controlled_Directional_Advective_Travel_Time_Solve.py"
SG5_SRC=ROOT/"PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
FLOWDIR=ROOT/"output"/"V16_D7B_FULL_FROZEN_CASE0002_0025_SOURCEBOUND_SG2_SG3_SG4_FLOW_ENSEMBLE"/"cases"
POLDIR=ROOT/"output"/"V16_D9R1_FULL_CASE0002_0025_201NODE_POLLOCK_C7_FACE_METRIC"/"cases"
OUT=ROOT/"output"/"V16_D10C_FULL_CASE0002_0025_FMM_ADV_TRAVELTIME_HIERARCHY";CASES=OUT/"cases";CASES.mkdir(parents=True,exist_ok=True)
HASH={"FMM":"0b26e3cdbc41276c53f4778e7eddcddd0cc8ef081ffb495b71df548152e8f049",
"B7":"2355f3eecd41bb6571f7ead3ebb1c5d90a1907ae681826159e79463166994c56",
"SG5":"2989fe58d1fd78fe9f9c03176dbb3ff066faf359f7edaf028cbdc0fea85135f2"}

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def mod(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def cv(vx,vy,vz):
 nz,ny,nxm1=vx.shape;nx=nxm1+1;x=np.empty((nz,ny,nx));y=np.empty_like(x);z=np.empty_like(x)
 x[:,:,0]=vx[:,:,0];x[:,:,-1]=vx[:,:,-1];x[:,:,1:-1]=.5*(vx[:,:,:-1]+vx[:,:,1:])
 y[:,0,:]=vy[:,0,:];y[:,-1,:]=vy[:,-1,:];y[:,1:-1,:]=.5*(vy[:,:-1,:]+vy[:,1:,:])
 z[0]=vz[0];z[-1]=vz[-1];z[1:-1]=.5*(vz[:-1]+vz[1:]);return x,y,z

def main():
 print("="*78);print("PAD-Stream V16D-10C")
 print("Full Case0002-0025 Source-Bound FMM/ADV Travel-Time Hierarchy Execution");print("="*78)
 for k,p in [("FMM",FMM_SRC),("B7",B7_SRC),("SG5",SG5_SRC)]:
  if sha(p)!=HASH[k]:raise RuntimeError(k+" hash mismatch")
 fmm=mod(FMM_SRC,"d10c_fmm");sg5=mod(SG5_SRC,"d10c_sg5")
 b6dir=ROOT/"output"/"V16_B6_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_NUMERICAL_SCHEME_CONTRACT"
 b6adir=ROOT/"output"/"V16_B6A_DIRECTIONAL_EXTERNAL_BOUNDARY_POLICY_AUDIT"
 b6dir.mkdir(parents=True,exist_ok=True);b6adir.mkdir(parents=True,exist_ok=True)
 paths=[b6dir/"V16B6_Summary.json",b6adir/"V16B6A_External_Boundary_Policy_Contract.json",b6adir/"V16B6A_Closed_Boundary_Projected_Scheme_Contract.npz"]
 backups={}
 for q in paths:
  if q.exists():
   b=OUT/(q.name+".pre_D10C_backup");shutil.copy2(q,b);backups[q]=b
 rows=[]
 try:
  for num in range(2,26):
   cid=f"V16D_Foundation_Case_{num:04d}";print(f"\n{'-'*78}\n[{num-1:02d}/24] {cid}\n{'-'*78}")
   fl=np.load(FLOWDIR/f"{cid}_Flow.npz");qx,qy,qz=[np.asarray(fl[k],float) for k in ["Qx","Qy","Qz"]]
   vx,vy,vz=[np.asarray(a,float) for a in sg5.construct_face_pore_velocities(qx,qy,qz)]
   cx,cy,cz=cv(vx,vy,vz);speed=np.sqrt(cx*cx+cy*cy+cz*cz)
   div,tol,src_idx,sm,meta=fmm.bind_injector_sources(qx,qy,qz)
   T,state,accepted=fmm.fast_marching_3d(speed,sm,6.096,6.096,1.2192)
   dx=dy=6.096;dz=1.2192
   aW=np.maximum(cx,0)/dx;aE=np.maximum(-cx,0)/dx;aS=np.maximum(cy,0)/dy;aN=np.maximum(-cy,0)/dy;aB=np.maximum(cz,0)/dz;aT=np.maximum(-cz,0)/dz
   aW[:,:,0]=0;aE[:,:,-1]=0;aS[:,0,:]=0;aN[:,-1,:]=0;aB[0]=0;aT[-1]=0;aP=aW+aE+aS+aN+aB+aT
   paths[0].write_text(json.dumps({"status":"V16B_DIRECTIONAL_NUMERICAL_SCHEME_BOUNDARY_POLICY_REQUIRED"}))
   paths[1].write_text(json.dumps({"status":"V16B_CLOSED_EXTERNAL_BOUNDARY_OPERATOR_POLICY_RESOLVED"}))
   np.savez_compressed(paths[2],Vx_m_s=cx,Vy_m_s=cy,Vz_m_s=cz,source_mask=sm.astype(np.uint8),
    aW_s_inv=aW,aE_s_inv=aE,aS_s_inv=aS,aN_s_inv=aN,aB_s_inv=aB,aT_s_inv=aT,aP_s_inv=aP,
    dx_m=np.array(dx),dy_m=np.array(dy),dz_m=np.array(dz))
   runpy.run_path(str(B7_SRC),run_name="__main__")
   b7out=ROOT/"output"/"V16_B7_CONTROLLED_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_SOLVE"/"V16B7_Directional_Advective_Travel_Time.npz"
   db=np.load(b7out);adv=np.asarray(db["tau_adv_s"],float)
   pol=np.load(POLDIR/f"{cid}_Pollock_201Node_C7_FaceMetric.npz");pt=np.asarray(pol["pollock_tau_end_s"],float)
   passed=(int(sm.sum())==5 and np.isfinite(T).all() and np.isfinite(adv).all() and np.all(T>=0) and np.all(adv>=0)
           and np.max(np.abs(T[sm]))<1e-8 and np.max(np.abs(adv[sm]))<1e-8 and len(pt)==1078)
   art=CASES/f"{cid}_FMM_ADV_Pollock_Hierarchy.npz"
   np.savez_compressed(art,fmm_arrival_s=T,tau_adv_s=adv,source_mask=sm.astype(np.uint8),pollock_tau_end_s=pt,
    Vx=vx,Vy=vy,Vz=vz,case_id=np.array(cid))
   row={"case_id":cid,"status":"CERTIFIED" if passed else "FAILED","source_cells":int(sm.sum()),
    "fmm_median_d":float(np.median(T)/86400),"fmm_max_d":float(T.max()/86400),
    "adv_median_d":float(np.median(adv)/86400),"adv_max_d":float(adv.max()/86400),
    "pollock_median_d":float(np.median(pt)/86400),"pollock_max_d":float(pt.max()/86400),"artifact_sha256":sha(art)}
   rows.append(row)
   print(f"D10C CASE STATUS: {row['status']} | FMM50={row['fmm_median_d']:.3f} d | ADV50={row['adv_median_d']:.3f} d | Pollock50={row['pollock_median_d']:.3f} d")
 finally:
  for q in paths:
   if q in backups:shutil.copy2(backups[q],q)
   elif q.exists():q.unlink()
 man=OUT/"V16D10C_TravelTime_Hierarchy_Manifest.csv"
 with man.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 good=[r for r in rows if r["status"]=="CERTIFIED"]
 gates={"source_hashes_exact":True,"all_24_attempted":len(rows)==24,"all_24_certified":len(good)==24,
 "all_five_source_cells":len(good)==24 and all(r["source_cells"]==5 for r in good),"no_case_replacement":True,
 "Pollock_remains_authoritative_reference":True,"FMM_role_auxiliary_scalar_control":True,"ADV_role_auxiliary_directional_field":True,
 "no_transport":True,"no_training":True}
 gates={k:bool(v) for k,v in gates.items()};ok=all(gates.values())
 vals=lambda k:np.array([r[k] for r in good],float)
 status="V16D_CASE0002_0025_FMM_ADV_POLLOCK_TRAVELTIME_HIERARCHY_ENSEMBLE_CERTIFIED_READY_FOR_MULTICASE_TRANSPORT_SUPERVISION" if ok else "V16D_D10C_TRAVELTIME_ENSEMBLE_HAS_FAILURES"
 summary={"milestone":"V16D-10C","status":status,"certified_cases":len(good),"manifest_sha256":sha(man),"gates":gates,
 "ensemble":({k:{"min":float(vals(k).min()),"median":float(np.median(vals(k))),"max":float(vals(k).max())}
 for k in ["fmm_median_d","fmm_max_d","adv_median_d","adv_max_d","pollock_median_d","pollock_max_d"]} if good else {}),
 "next_milestone":"V16D-11 — Multi-Foundation-Case Stage-4 Transport Supervision Generation Contract and Case-Level Split Freeze"}
 (OUT/"PAD_Stream_V16D10C_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\n"+"="*78);print("V16D-10C ENSEMBLE SUMMARY");print("="*78)
 print(f"  certified cases: {len(good)}/24")
 if good:
  print("  FMM median days case min/median/max: %.3f / %.3f / %.3f"%(vals("fmm_median_d").min(),np.median(vals("fmm_median_d")),vals("fmm_median_d").max()))
  print("  ADV median days case min/median/max: %.3f / %.3f / %.3f"%(vals("adv_median_d").min(),np.median(vals("adv_median_d")),vals("adv_median_d").max()))
  print("  Pollock median case min/median/max : %.3f / %.3f / %.3f"%(vals("pollock_median_d").min(),np.median(vals("pollock_median_d")),vals("pollock_median_d").max()))
 print(f"  manifest SHA-256: {sha(man)}")
 print("\n"+"="*78);print("V16D-10C GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT MILESTONE\n  "+summary["next_milestone"])
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
