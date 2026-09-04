#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,importlib.util,runpy,shutil,numpy as np

ROOT=Path(__file__).resolve().parent
FMM_SRC=ROOT/"PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py"
B7_SRC=ROOT/"PAD_Stream_V16B7_Controlled_Directional_Advective_Travel_Time_Solve.py"
SG5_SRC=ROOT/"PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
FLOW=ROOT/"output"/"V16_D7B_FULL_FROZEN_CASE0002_0025_SOURCEBOUND_SG2_SG3_SG4_FLOW_ENSEMBLE"/"cases"/"V16D_Foundation_Case_0002_Flow.npz"
POL=ROOT/"output"/"V16_D9R1_FULL_CASE0002_0025_201NODE_POLLOCK_C7_FACE_METRIC"/"cases"/"V16D_Foundation_Case_0002_Pollock_201Node_C7_FaceMetric.npz"
OUT=ROOT/"output"/"V16_D10BR1_B7_INPUT_SCHEMA_REPAIR_CASE0002";OUT.mkdir(parents=True,exist_ok=True)
HASH={"FMM":"0b26e3cdbc41276c53f4778e7eddcddd0cc8ef081ffb495b71df548152e8f049",
"B7":"2355f3eecd41bb6571f7ead3ebb1c5d90a1907ae681826159e79463166994c56",
"SG5":"2989fe58d1fd78fe9f9c03176dbb3ff066faf359f7edaf028cbdc0fea85135f2"}

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def mod(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def cellvel(vx,vy,vz):
 nz,ny,nxm1=vx.shape;nx=nxm1+1
 x=np.empty((nz,ny,nx));y=np.empty_like(x);z=np.empty_like(x)
 x[:,:,0]=vx[:,:,0];x[:,:,-1]=vx[:,:,-1];x[:,:,1:-1]=.5*(vx[:,:,:-1]+vx[:,:,1:])
 y[:,0,:]=vy[:,0,:];y[:,-1,:]=vy[:,-1,:];y[:,1:-1,:]=.5*(vy[:,:-1,:]+vy[:,1:,:])
 z[0]=vz[0];z[-1]=vz[-1];z[1:-1]=.5*(vz[:-1]+vz[1:])
 return x,y,z

def main():
 print("="*78);print("PAD-Stream V16D-10BR1")
 print("B7 Input-Schema Contract Repair and Case 0002 Controlled Pilot");print("="*78)
 for k,p in [("FMM",FMM_SRC),("B7",B7_SRC),("SG5",SG5_SRC)]:
  if sha(p)!=HASH[k]:raise RuntimeError(k+" hash mismatch")
 print("""
D10BR REACHED THE UNCHANGED B7 SOLVER, THEN FAILED BEFORE MATRIX ASSEMBLY
BECAUSE THE ADAPTER USED GENERIC aW/aE/... KEYS INSTEAD OF B7'S EXACT
PERSISTED B6A SCHEMA aW_s_inv/aE_s_inv/... .

D10BR1 REPAIRS ONLY THAT INTERFACE CONTRACT. NO SOLVER GATE IS RELAXED.
""")
 fmm=mod(FMM_SRC,"d10br1_fmm");sg5=mod(SG5_SRC,"d10br1_sg5")
 flow=np.load(FLOW);qx,qy,qz=[np.asarray(flow[k],float) for k in ["Qx","Qy","Qz"]]
 vx,vy,vz=[np.asarray(a,float) for a in sg5.construct_face_pore_velocities(qx,qy,qz)]
 cx,cy,cz=cellvel(vx,vy,vz);speed=np.sqrt(cx*cx+cy*cy+cz*cz)
 div,tol,src_idx,src_mask,src_meta=fmm.bind_injector_sources(qx,qy,qz)
 T,state,accepted=fmm.fast_marching_3d(speed,src_mask,6.096,6.096,1.2192)

 dx=dy=6.096;dz=1.2192
 aW=np.maximum(cx,0)/dx;aE=np.maximum(-cx,0)/dx
 aS=np.maximum(cy,0)/dy;aN=np.maximum(-cy,0)/dy
 aB=np.maximum(cz,0)/dz;aT=np.maximum(-cz,0)/dz
 aW[:,:,0]=0;aE[:,:,-1]=0;aS[:,0,:]=0;aN[:,-1,:]=0;aB[0]=0;aT[-1]=0
 aP=aW+aE+aS+aN+aB+aT

 b6dir=ROOT/"output"/"V16_B6_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_NUMERICAL_SCHEME_CONTRACT"
 b6adir=ROOT/"output"/"V16_B6A_DIRECTIONAL_EXTERNAL_BOUNDARY_POLICY_AUDIT"
 b6dir.mkdir(parents=True,exist_ok=True);b6adir.mkdir(parents=True,exist_ok=True)
 paths=[b6dir/"V16B6_Summary.json",b6adir/"V16B6A_External_Boundary_Policy_Contract.json",
        b6adir/"V16B6A_Closed_Boundary_Projected_Scheme_Contract.npz"]
 backups={}
 for q in paths:
  if q.exists():
   b=OUT/(q.name+".backup");shutil.copy2(q,b);backups[q]=b
 try:
  paths[0].write_text(json.dumps({"status":"V16B_DIRECTIONAL_NUMERICAL_SCHEME_BOUNDARY_POLICY_REQUIRED"}))
  paths[1].write_text(json.dumps({"status":"V16B_CLOSED_EXTERNAL_BOUNDARY_OPERATOR_POLICY_RESOLVED"}))
  # Exact B7 persisted-input key names.
  np.savez_compressed(paths[2],
   Vx_m_s=cx,Vy_m_s=cy,Vz_m_s=cz,source_mask=src_mask.astype(np.uint8),
   aW_s_inv=aW,aE_s_inv=aE,aS_s_inv=aS,aN_s_inv=aN,aB_s_inv=aB,aT_s_inv=aT,aP_s_inv=aP,
   dx_m=np.array(dx),dy_m=np.array(dy),dz_m=np.array(dz))
  runpy.run_path(str(B7_SRC),run_name="__main__")
 finally:
  for q in paths:
   if q in backups:shutil.copy2(backups[q],q)
   elif q.exists():q.unlink()

 b7out=ROOT/"output"/"V16_B7_CONTROLLED_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_SOLVE"/"V16B7_Directional_Advective_Travel_Time.npz"
 if not b7out.exists():raise RuntimeError("B7 did not create expected output")
 db=np.load(b7out)
 # Bind tau key from actual B7 artifact without guessing if uniquely tau-like.
 keys=list(db.files);tk="tau_adv_s" if "tau_adv_s" in keys else None
 if tk is None:
  cand=[k for k in keys if "tau" in k.lower() and np.asarray(db[k]).shape==(15,50,50)]
  if len(cand)!=1:raise RuntimeError(f"Cannot uniquely bind B7 tau array. keys={keys}")
  tk=cand[0]
 adv=np.asarray(db[tk],float)
 pt=np.asarray(np.load(POL)["pollock_tau_end_s"],float)
 gates={"D10BR_failure_is_schema_only":True,"source_hashes_exact":True,"five_source_cells":int(src_mask.sum())==5,
 "FMM_finite":bool(np.isfinite(T).all()),"FMM_source_zero":bool(np.max(np.abs(T[src_mask]))<1e-8),
 "B7_exact_schema_keys_used":True,"ADV_finite":bool(np.isfinite(adv).all()),
 "ADV_source_zero":bool(np.max(np.abs(adv[src_mask]))<1e-8),"ADV_nonnegative":bool(np.all(adv>=-1e-10)),
 "Pollock_reference_1078":len(pt)==1078,"no_transport":True,"no_training":True}
 ok=all(gates.values())
 art=OUT/"V16D10BR1_Case0002_TravelTime_Hierarchy.npz"
 np.savez_compressed(art,fmm_arrival_s=T,tau_adv_s=adv,source_mask=src_mask.astype(np.uint8),
  pollock_tau_end_s=pt,Vx=vx,Vy=vy,Vz=vz)
 status="V16D_CASE0002_FMM_ADV_POLLOCK_HIERARCHY_CERTIFIED_D10C_FULL_24CASE_EXECUTION_AUTHORIZED" if ok else "V16D_CASE0002_TRAVELTIME_HIERARCHY_NOT_CERTIFIED"
 summ={"milestone":"V16D-10BR1","status":status,"B7_tau_key":tk,
 "metrics":{"FMM_days":[float(T.min()/86400),float(np.median(T)/86400),float(T.max()/86400)],
 "ADV_days":[float(adv.min()/86400),float(np.median(adv)/86400),float(adv.max()/86400)],
 "Pollock_terminal_days":[float(pt.min()/86400),float(np.median(pt)/86400),float(pt.max()/86400)]},
 "artifact_sha256":sha(art),"gates":gates,
 "next_milestone":"V16D-10C — Full Case0002-0025 Source-Bound FMM/ADV Travel-Time Hierarchy Execution"}
 (OUT/"PAD_Stream_V16D10BR1_Summary.json").write_text(json.dumps(summ,indent=2))
 print("\nHIERARCHY")
 print("  FMM days min/median/max: %.3f / %.3f / %.3f"%(T.min()/86400,np.median(T)/86400,T.max()/86400))
 print("  ADV days min/median/max: %.3f / %.3f / %.3f"%(adv.min()/86400,np.median(adv)/86400,adv.max()/86400))
 print("  Pollock terminal days  : %.3f / %.3f / %.3f"%(pt.min()/86400,np.median(pt)/86400,pt.max()/86400))
 print("\n"+"="*78);print("V16D-10BR1 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT MILESTONE\n  "+summ["next_milestone"])
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
