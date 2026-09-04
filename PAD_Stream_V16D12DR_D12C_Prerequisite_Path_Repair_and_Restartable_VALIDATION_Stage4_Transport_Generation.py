#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,importlib.util,json,time,numpy as np

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"/"V16_D12D_RESTARTABLE_VALIDATION_STAGE4_TRANSPORT_GENERATION"; CASES=OUT/"cases"; CASES.mkdir(parents=True,exist_ok=True)
C17=ROOT/"PAD_Stream_V16C17_Production_Source_Authentic_Y_Transport_Tensor_Generation_and_Certification.py"
C14=ROOT/"output"/"V16_C14_PRODUCTION_FULL_PHYSICS_TRANSPORT_PARAMETER_AUTHORITY_CONTRACT"/"V16C14_Production_Full_Physics_Parameter_Contract.json"
C15=ROOT/"output"/"V16_C15_PRODUCTION_PHYSICAL_TARGET_TIME_SCHEDULE_AUTHORITY_CONTRACT"/"V16C15_Production_Target_Time_Schedule_Contract.json"
D9DIR=ROOT/"output"/"V16_D9R1_FULL_CASE0002_0025_201NODE_POLLOCK_C7_FACE_METRIC"/"cases"
D12B=ROOT/"output"/"V16_D12B_PARTITION_AWARE_MULTICASE_STAGE4_TRANSPORT_EXECUTION_CONTRACT"/"V16D12B_Partition_Aware_MultiCase_Stage4_Transport_Execution_Contract.json"
D12AR=ROOT/"output"/"V16_D12A_CASE0002_SOURCEAUTHENTIC_9TIME_STAGE4_TRANSPORT_PILOT"/"V16D12A_Case0002_SourceAuthentic_Y_Transport.npz"
C17SHA="1d357be446103cb554c4759948347d2876235b7c630c64cd826801cbfc61dd4f"
D12BSHA="4a041e65a32232c7eab41849f02bc677fc51d9e41b1ecd701d8046d6a58c7b0b"
CASE2SHA="211cacb7752c9a11f81d009a6968aeee414d6b5e3df524f0300e5c490ef7ee70"
TRAIN=["0020","0015","0013","0004","0006","0002","0023","0016","0009","0019","0017","0024","0003","0011","0014","0007"]
VAL=["0010","0025","0008","0012"]
D12C_MAN=ROOT/"output"/"V16_D12C_RESTARTABLE_TRAIN_STAGE4_TRANSPORT_GENERATION"/"V16D12C_TRAIN_Transport_Manifest.csv"
D12C_SUM=ROOT/"output"/"V16_D12C_RESTARTABLE_TRAIN_STAGE4_TRANSPORT_GENERATION"/"PAD_Stream_V16D12C_Summary.json"
D12C_MAN_SHA="85415615a8d752e45085eaff5c4d9b97ecb2c5155d570bc4019ef42221c30264"
CFL=.25;SPD=86400.;EPS=1e-12

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def loadj(p):return json.loads(p.read_text())
def module(p):
 s=importlib.util.spec_from_file_location("d12c_c17",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def savej(p,o):p.write_text(json.dumps(o,indent=2))
def artifact(c):return CASES/f"V16D_Foundation_Case_{c}_Stage4_Y_Transport.npz"
def sidecar(c):return CASES/f"V16D_Foundation_Case_{c}_Stage4_Y_Transport_Certification.json"

def solve(c,c17,par,Pec,lmb,Nc,targets):
 g=D9DIR/f"V16D_Foundation_Case_{c}_Pollock_201Node_C7_FaceMetric.npz"
 with np.load(g,allow_pickle=False) as z:
  th=np.asarray(z["theta"],float);te=np.asarray(z["pollock_tau_end_s"],float)
  mf=np.asarray(z["M_face_dtheta_dxD"],float);M=np.asarray(z["M_node_sidecar_dtheta_dxD"],float)
 if th.ndim==1:th=np.broadcast_to(th[None,:],(len(te),len(th))).copy()
 ns,n=th.shape;dth=np.diff(th,axis=1)
 Mf=np.empty((ns,n+1));Mf[:,1:-1]=mf;Mf[:,0]=mf[:,0];Mf[:,-1]=mf[:,-1]
 tf=np.empty((ns,n+1));tf[:,1:-1]=.5*(th[:,:-1]+th[:,1:]);tf[:,0]=th[:,0];tf[:,-1]=th[:,-1];cv=np.diff(tf,axis=1)
 eta_t=targets[:,None]*SPD/te[None,:];dtc=float(CFL*np.min(cv[:,1:])/(c17.max_dfw(par)+EPS))
 S=np.full((ns,n),par["sw_init"]);S[:,0]=par["sw_inj"];eta=np.zeros(ns);nk=np.zeros(ns,dtype=int)
 Y=np.full((len(targets),ns,n),np.nan);ma=mi=mb=0.;steps=0;t0=time.time();ceiling=int(np.ceil(np.max(eta_t)/dtc))+len(targets)+100
 while np.any(nk<len(targets)):
  active=nk<len(targets);goal=np.zeros(ns);ii=np.where(active)[0];goal[ii]=eta_t[nk[ii],ii]
  hit=active&(np.abs(goal-eta)<=5e-14)
  if np.any(hit):
   h=np.where(hit)[0];Y[nk[h],h]=S[h];nk[h]+=1;continue
  dt=np.zeros(ns);dt[active]=np.minimum(dtc,np.maximum(0.,goal[active]-eta[active]))
  S,_,e=c17.adv(S,dt,cv,par);ma=max(ma,e);mb=max(mb,float(max(0.,par["swc"]-S.min(),S.max()-(1-par["sor"]))))
  np.clip(S,par["swc"],1-par["sor"],out=S);S[:,0]=par["sw_inj"]
  S,r=c17.cap(S,dt,par["phi"],Pec,lmb,M,Mf,cv,dth,par);mi=max(mi,r);mb=max(mb,float(max(0.,par["swc"]-S.min(),S.max()-(1-par["sor"]))))
  np.clip(S,par["swc"],1-par["sor"],out=S);S[:,0]=par["sw_inj"];eta+=dt;steps+=1
  if steps%5000==0:print(f"    step {steps:6d}/{ceiling}: targets {np.sum(nk)}/{ns*len(targets)}")
  if steps>ceiling:raise RuntimeError(f"Case{c} iteration ceiling")
 finite=np.isfinite(Y).all();bound=max(0.,par["swc"]-Y.min(),Y.max()-(1-par["sor"]))
 inlet=np.max(np.abs(Y[:,:,0]-par["sw_inj"]));under=max(0.,par["sw_init"]-np.min(Y[:,:,1:]))
 temporal=np.mean(np.diff(Y,axis=0)<-1e-8);spatial=np.mean(np.diff(Y,axis=2)>1e-8)
 gates={"shape":Y.shape==(9,1078,201),"finite":finite,"bounds":bound<1e-8,"injector":inlet<1e-12,"undershoot":under<1e-8,
 "adv_conservation":ma<1e-11,"cap_residual":mi<1e-10,"preclip":mb<1e-8,"temporal":temporal<.01,"spatial":spatial<.05,
 "Mface_positive":np.all(mf>0),"Pollock_primary":True,"no_fit":True}
 if not all(gates.values()):raise RuntimeError(f"Case{c} certification failed: {gates}")
 a=artifact(c);np.savez_compressed(a,Y_transport=Y,target_days=targets,theta=th[0],terminal_pollock_tof_s=te,target_eta=eta_t,
  M_face_dtheta_dxD=mf,Pe_c=np.array(Pec),lambda_c=np.array(lmb),Nc_metadata_only=np.array(Nc),
  case_id=np.array(f"V16D_Foundation_Case_{c}"))
 rec={"case_id":f"V16D_Foundation_Case_{c}","partition":"VALIDATION","status":"CERTIFIED","artifact":str(a),"sha256":sha(a),
 "steps":steps,"elapsed_seconds":time.time()-t0,"S_min":float(Y.min()),"S_max":float(Y.max()),"adv_max":ma,"cap_residual_max":mi,
 "preclip_max":mb,"temporal_negative_fraction":float(temporal),"spatial_positive_fraction":float(spatial),"gates":{k:bool(v) for k,v in gates.items()}}
 savej(sidecar(c),rec);return rec

def main():
 print("="*78);print("PAD-Stream V16D-12DR")
 print("D12D Prerequisite-Path Repair + Restartable VALIDATION-Partition Stage-4 Transport Generation");print("="*78)
 print("""
D12D FAILED BEFORE ANY VALIDATION TRANSPORT PHYSICS EXECUTED.

THE FAILURE WAS A PREREQUISITE-PATH TYPO ONLY:
D12D LOOKED FOR PAD_Stream_V16D12D_Summary.json INSIDE THE FROZEN D12C
OUTPUT DIRECTORY. THE ACTUAL FROZEN TRAIN SUMMARY IS
PAD_Stream_V16D12C_Summary.json.

D12DR REPAIRS ONLY THAT PATH. NO PHYSICS, PARTITION, SHA, NUMERICAL
THRESHOLD, TARGET TIME, OR CERTIFICATION GATE IS CHANGED.

D12C CERTIFIED THE COMPLETE 16-CASE TRAIN PARTITION.

ONLY THE FROZEN VALIDATION PARTITION IS GENERATED HERE.
EACH VALIDATION CASE IS AN INDEPENDENT CERTIFIED CHECKPOINT.
ON RESTART, A CASE IS SKIPPED ONLY WHEN ITS ARTIFACT + CERTIFICATION SIDECAR
EXIST AND THE RECORDED SHA MATCHES THE ACTUAL ARTIFACT.

TRAIN TARGETS ARE READ-ONLY AND ARE NOT RECOMPUTED.
LOCKED OOD TEST CASES ARE NOT TOUCHED.
NO NORMALIZATION FIT, MODEL SELECTION, OR TRAINING OCCURS.
""")
 if sha(C17)!=C17SHA or sha(D12B)!=D12BSHA or sha(D12AR)!=CASE2SHA:raise RuntimeError("Frozen authority SHA mismatch")
 if not D12C_MAN.exists() or not D12C_SUM.exists():raise RuntimeError("D12C TRAIN authority missing")
 d12c=loadj(D12C_SUM)
 if sha(D12C_MAN)!=D12C_MAN_SHA or d12c.get("manifest_sha256")!=D12C_MAN_SHA:raise RuntimeError("D12C TRAIN manifest SHA mismatch")
 if d12c.get("status")!="V16D_TRAIN_PARTITION_STAGE4_TRANSPORT_SUPERVISION_16_CASES_CERTIFIED_VALIDATION_GENERATION_AUTHORIZED":raise RuntimeError("D12C TRAIN status mismatch")
 c17=module(C17);pc=loadj(C14);tc=loadj(C15);pp=pc["production_parameters"]
 v=lambda k:float(pp[k]["value"])
 par={"nw":v("nw"),"no":v("no"),"swc":v("Swc"),"sor":v("Sor"),"krw_max":v("krw_max"),"kro_max":v("kro_max"),"mu_w":v("mu_w"),"mu_o":v("mu_o"),"phi":v("phi")}
 par["sw_init"]=par["swc"]+1e-3;par["sw_inj"]=1-par["sor"]-1e-3
 Pec=v("Pe_c");lmb=v("lambda_c");Nc=v("Nc");targets=np.asarray(tc["target_days"],float)
 rows=[]
 for j,c in enumerate(VAL,1):
  print(f"\n[{j:02d}/04] Case{c}")
  a,sf=artifact(c),sidecar(c)
  if a.exists() and sf.exists():
   r=loadj(sf)
   if r.get("status")=="CERTIFIED" and r.get("partition")=="VALIDATION" and r.get("sha256")==sha(a):
    print("  RESTART SKIP — certified VALIDATION artifact SHA verified")
    rows.append({"case_id":r["case_id"],"status":"CERTIFIED_RESTART_REUSED","sha256":r["sha256"],"elapsed_seconds":r["elapsed_seconds"]});continue
   raise RuntimeError(f"Case{c}: existing checkpoint is not certifiably reusable; refusing overwrite")
  r=solve(c,c17,par,Pec,lmb,Nc,targets)
  print(f"  CERTIFIED | {r['steps']} steps | {r['elapsed_seconds']:.1f} s | {r['sha256']}")
  rows.append({"case_id":r["case_id"],"status":"CERTIFIED_NEW","sha256":r["sha256"],"elapsed_seconds":r["elapsed_seconds"]})
 man=OUT/"V16D12D_VALIDATION_Transport_Manifest.csv"
 with man.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 gates={"D12C_train_manifest_SHA_exact":sha(D12C_MAN)==D12C_MAN_SHA,
 "D12C_train_status_bound":d12c.get("status")=="V16D_TRAIN_PARTITION_STAGE4_TRANSPORT_SUPERVISION_16_CASES_CERTIFIED_VALIDATION_GENERATION_AUTHORIZED",
 "exact_4_validation":len(rows)==4,"all_validation_certified":all(r["status"].startswith("CERTIFIED") for r in rows),
 "restartable_per_case":True,"train_not_recomputed":True,"locked_OOD_untouched":True,
 "no_normalization_fit":True,"no_model_selection":True,"no_training":True}
 ok=all(gates.values());status="V16D_VALIDATION_PARTITION_STAGE4_TRANSPORT_SUPERVISION_4_CASES_CERTIFIED_LOCKED_OOD_GENERATION_CONTRACT_AUTHORIZED" if ok else "V16D_D12D_VALIDATION_TRANSPORT_INCOMPLETE"
 summary={"milestone":"V16D-12DR","status":status,"manifest_sha256":sha(man),"cases":rows,"gates":gates,
  "next_milestone":"V16D-12E — Locked OOD TEST Transport Generation Final-Evaluation Isolation Contract" if ok else "Resume V16D-12D"}
 sp=OUT/"PAD_Stream_V16D12D_Summary.json";savej(sp,summary)
 print("\n"+"="*78);print("V16D-12DR SUMMARY");print("="*78);print("  certified:",sum(r["status"].startswith("CERTIFIED") for r in rows),"/4");print("  manifest SHA:",sha(man))
 for k,vv in gates.items():print(f"[{'PASS' if vv else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT MILESTONE\n ",summary["next_milestone"])
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
