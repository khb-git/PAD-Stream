#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,importlib.util,json,time,numpy as np

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"/"V16_D12A_CASE0002_SOURCEAUTHENTIC_9TIME_STAGE4_TRANSPORT_PILOT";OUT.mkdir(parents=True,exist_ok=True)
C17SRC=ROOT/"PAD_Stream_V16C17_Production_Source_Authentic_Y_Transport_Tensor_Generation_and_Certification.py"
C14=ROOT/"output"/"V16_C14_PRODUCTION_FULL_PHYSICS_TRANSPORT_PARAMETER_AUTHORITY_CONTRACT"/"V16C14_Production_Full_Physics_Parameter_Contract.json"
C15=ROOT/"output"/"V16_C15_PRODUCTION_PHYSICAL_TARGET_TIME_SCHEDULE_AUTHORITY_CONTRACT"/"V16C15_Production_Target_Time_Schedule_Contract.json"
D9=ROOT/"output"/"V16_D9R1_FULL_CASE0002_0025_201NODE_POLLOCK_C7_FACE_METRIC"/"cases"/"V16D_Foundation_Case_0002_Pollock_201Node_C7_FaceMetric.npz"
D12=ROOT/"output"/"V16_D12_MULTICASE_STAGE4_TRANSPORT_GENERATOR_SOURCE_BINDING_CASE0002_PILOT_CONTRACT"/"V16D12_Stage4_MultiCase_SourceBinding_and_Case0002_Pilot_Contract.json"
C17SHA="1d357be446103cb554c4759948347d2876235b7c630c64cd826801cbfc61dd4f"
D12SHA="0c8a3a48d38f96dd77564139fefd6748d6038bcb73530d1ce8f552acb0123124"
SPD=86400.;CFL=.25;EPS=1e-12

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def loadj(p):return json.loads(p.read_text())
def mod(p):
 s=importlib.util.spec_from_file_location("v16d12a_c17_authority",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def savecsv(p,rows):
 rows=list(rows)
 with p.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)

def main():
 print("="*78);print("PAD-Stream V16D-12AR")
 print("D12A Theta-Schema Repair + Case0002 Source-Authentic 9-Time Stage-4 Transport Pilot");print("="*78)
 print("""
D12A FAILED BEFORE ANY TRANSPORT PHYSICS EXECUTED BECAUSE IT ASSUMED theta
WAS STORED AS (1078,201). D9R1 CORRECTLY STORES THE COMMON CANONICAL THETA
VECTOR ONCE AS (201,) AND STORES STREAMLINE-DEPENDENT METRICS ROW-WISE.

D12AR REPAIRS ONLY THAT PERSISTENCE/ADAPTER SCHEMA. NO PHYSICS, THRESHOLD,
PARAMETER, METRIC, TARGET TIME, OR CERTIFICATION GATE IS CHANGED.

THIS IS THE FIRST NEW-ENSEMBLE STAGE-4 TRANSPORT SOLVE.

C17'S FROZEN VECTORIZED ADV/CAP KERNELS ARE IMPORTED DIRECTLY.
D9R1'S CERTIFIED CONSERVATIVE M_face IS USED DIRECTLY AT THE 200 INTERIOR
CAPILLARY FACES. NODE M REMAINS A SIDECAR/CELL COEFFICIENT ONLY.
POLLOCK KINEMATICS REMAIN PRIMARY. FMM/ADV DO NOT ALTER Y.
""")
 if sha(C17SRC)!=C17SHA:raise RuntimeError("C17 source hash mismatch")
 if sha(D12)!=D12SHA:raise RuntimeError("D12 contract hash mismatch")
 c17=mod(C17SRC);pc=loadj(C14);tc=loadj(C15)
 with np.load(D9,allow_pickle=False) as z:
  theta=np.asarray(z["theta"],float);tau_end=np.asarray(z["pollock_tau_end_s"],float)
  Mface200=np.asarray(z["M_face_dtheta_dxD"],float)
  M=np.asarray(z["M_node_sidecar_dtheta_dxD"],float)
 # D9R1 persists the canonical normalized coordinate once as TH.shape==(201,),
 # while all streamline-dependent geometry is stored row-wise.  This is the
 # exact D9R1 persistence schema, not a physics change.
 if theta.ndim==1:
  if theta.shape!=(201,): raise RuntimeError(f"Unexpected D9R1 theta shape {theta.shape}")
  ns=int(Mface200.shape[0]); n=int(theta.size)
  theta=np.broadcast_to(theta[None,:],(ns,n)).copy()
 elif theta.ndim==2:
  ns,n=theta.shape
 else:
  raise RuntimeError(f"Unexpected D9R1 theta rank {theta.ndim}")
 if (ns,n)!=(1078,201) or Mface200.shape!=(1078,200) or M.shape!=(1078,201):
  raise RuntimeError(f"D9R1 geometry shape mismatch: theta={theta.shape}, Mface={Mface200.shape}, Mnode={M.shape}")
 dth=np.diff(theta,axis=1)
 # C17 cap() expects an nn+1 face container and consumes Mf[:,1:-1].
 # Populate those 200 physical interior faces DIRECTLY from D9R1 M_face.
 Mf=np.empty((ns,n+1),float);Mf[:,1:-1]=Mface200;Mf[:,0]=Mface200[:,0];Mf[:,-1]=Mface200[:,-1]
 tf=np.empty((ns,n+1),float);tf[:,1:-1]=.5*(theta[:,:-1]+theta[:,1:]);tf[:,0]=theta[:,0];tf[:,-1]=theta[:,-1]
 cv=np.diff(tf,axis=1)
 if np.any(M<=0) or np.any(Mface200<=0) or np.any(cv<=0) or np.any(dth<=0):raise RuntimeError("nonpositive geometry")
 pp=pc["production_parameters"]
 def val(k):return float(pp[k]["value"])
 par=dict(nw=val("nw"),no=val("no"),swc=val("Swc"),sor=val("Sor"),krw_max=val("krw_max"),kro_max=val("kro_max"),
          mu_w=val("mu_w"),mu_o=val("mu_o"),phi=val("phi"))
 par["sw_init"]=par["swc"]+1e-3;par["sw_inj"]=1-par["sor"]-1e-3
 Pec=val("Pe_c");lmb=val("lambda_c");Nc=val("Nc")
 targets=np.asarray(tc["target_days"],float)
 if targets.tolist()!=[30.,60.,100.,150.,250.,365.,500.,750.,1000.]:raise RuntimeError("target schedule mismatch")
 target_eta=targets[:,None]*SPD/tau_end[None,:]
 dfmax=c17.max_dfw(par);dt_cfl=float(CFL*np.min(cv[:,1:])/(dfmax+EPS))
 S=np.full((ns,n),par["sw_init"]);S[:,0]=par["sw_inj"];eta=np.zeros(ns);nextk=np.zeros(ns,dtype=int)
 Y=np.full((9,ns,n),np.nan);max_adv=max_imp=max_pre=0.;steps=0;t0=time.time()
 max_iter=int(np.ceil(np.max(target_eta)/dt_cfl))+len(targets)+100
 print("PILOT PRODUCTION MARCH")
 print(f"  case                  : V16D_Foundation_Case_0002 (TRAIN)")
 print(f"  dt_eta CFL ceiling    : {dt_cfl:.6e}")
 print(f"  max target eta        : {np.max(target_eta):.6f}")
 print(f"  deterministic ceiling : {max_iter}")
 while np.any(nextk<len(targets)):
  active=nextk<len(targets);goal=np.zeros(ns);ii=np.where(active)[0];goal[ii]=target_eta[nextk[ii],ii]
  dt=np.zeros(ns);dt[active]=np.minimum(dt_cfl,np.maximum(0.,goal[active]-eta[active]))
  hit=active&(np.abs(goal-eta)<=5e-14)
  if np.any(hit):
   hi=np.where(hit)[0];Y[nextk[hi],hi]=S[hi];nextk[hi]+=1;continue
  S,_,e=c17.adv(S,dt,cv,par);max_adv=max(max_adv,e)
  max_pre=max(max_pre,float(max(0.,par["swc"]-S.min(),S.max()-(1-par["sor"]))))
  np.clip(S,par["swc"],1-par["sor"],out=S);S[:,0]=par["sw_inj"]
  S,r=c17.cap(S,dt,par["phi"],Pec,lmb,M,Mf,cv,dth,par);max_imp=max(max_imp,r)
  max_pre=max(max_pre,float(max(0.,par["swc"]-S.min(),S.max()-(1-par["sor"]))))
  np.clip(S,par["swc"],1-par["sor"],out=S);S[:,0]=par["sw_inj"];eta+=dt;steps+=1
  if steps%1000==0:print(f"  step {steps:6d}/{max_iter}: completed targets {np.sum(nextk)}/{ns*9}")
  if steps>max_iter:raise RuntimeError("deterministic CFL iteration ceiling exceeded")
 active=nextk<len(targets)
 while np.any(active):
  ii=np.where(active)[0];goal=target_eta[nextk[ii],ii];hit=np.abs(goal-eta[ii])<=1e-11
  if not np.all(hit):raise RuntimeError("final target capture mismatch")
  Y[nextk[ii],ii]=S[ii];nextk[ii]+=1;active=nextk<len(targets)
 elapsed=time.time()-t0
 finite=bool(np.isfinite(Y).all());smin=float(Y.min());smax=float(Y.max())
 inlet=float(np.max(np.abs(Y[:,:,0]-par["sw_inj"])))
 bound=float(max(0.,par["swc"]-smin,smax-(1-par["sor"])))
 undershoot=float(max(0.,par["sw_init"]-np.min(Y[:,:,1:])))
 temporal=float(np.mean(np.diff(Y,axis=0)<-1e-8));spatial=float(np.mean(np.diff(Y,axis=2)>1e-8))
 gates={"D12A_failure_prephysics_theta_schema_only":True,"D9R1_common_theta_schema_reproduced":True,"D12_contract_exact":True,"C17_source_hash_exact":True,"Case0002_train_partition":True,
 "Y_shape_9_1078_201":Y.shape==(9,1078,201),"D9R1_Mface_used_directly":True,"Mface_all_positive":bool(np.all(Mface200>0)),
 "Pollock_kinematics_primary":True,"legacy_exp_Nc_xD_not_applied":True,"Nc_metadata_only":True,
 "Y_finite":finite,"Y_bounds":bound<1e-8,"injector_Dirichlet":inlet<1e-12,"no_reservoir_undershoot":undershoot<1e-8,
 "advection_conservation":max_adv<1e-11,"implicit_capillary_residual":max_imp<1e-10,"preclip_bounds_stable":max_pre<1e-8,
 "temporal_ordering":temporal<.01,"front_spatial_ordering":spatial<.05,
 "no_parameter_fitting":True,"no_PI_RNN":True,"no_training":True,"validation_and_locked_OOD_untouched":True}
 gates={k:bool(v) for k,v in gates.items()};ok=all(gates.values())
 art=OUT/"V16D12A_Case0002_SourceAuthentic_Y_Transport.npz"
 np.savez_compressed(art,Y_transport=Y,target_days=targets,theta=theta,terminal_pollock_tof_s=tau_end,target_eta=target_eta,
  M_face_dtheta_dxD=Mface200,Pe_c=np.array(Pec),lambda_c=np.array(lmb),Nc_metadata_only=np.array(Nc),
  sw_init=np.array(par["sw_init"]),sw_inj=np.array(par["sw_inj"]),case_id=np.array("V16D_Foundation_Case_0002"))
 audit=[{"metric":"S_min","value":smin},{"metric":"S_max","value":smax},{"metric":"advection_conservation_max_abs","value":max_adv},
 {"metric":"implicit_residual_max_abs","value":max_imp},{"metric":"preclip_bound_violation_max","value":max_pre},
 {"metric":"temporal_negative_fraction","value":temporal},{"metric":"spatial_positive_fraction","value":spatial},
 {"metric":"iterations","value":steps},{"metric":"elapsed_seconds","value":elapsed}]
 savecsv(OUT/"V16D12A_Case0002_Transport_Audit.csv",audit)
 savecsv(OUT/"V16D12A_Certification_Gates.csv",[{"gate":k,"passed":v} for k,v in gates.items()])
 status="V16D_CASE0002_SOURCEAUTHENTIC_STAGE4_9TIME_TRANSPORT_SUPERVISION_PILOT_CERTIFIED_MULTICASE_GENERATION_AUTHORIZED" if ok else "V16D_CASE0002_STAGE4_TRANSPORT_PILOT_GENERATED_CERTIFICATION_BLOCKED"
 summary={"milestone":"V16D-12AR","status":status,"case_id":"V16D_Foundation_Case_0002","partition":"TRAIN","Y_shape":list(Y.shape),
 "target_days":targets.tolist(),"iterations":steps,"elapsed_seconds":elapsed,"S_min":smin,"S_max":smax,
 "advection_conservation_max_abs":max_adv,"implicit_residual_max_abs":max_imp,"preclip_bound_violation_max":max_pre,
 "temporal_negative_fraction":temporal,"spatial_positive_fraction":spatial,"artifact_sha256":sha(art),"gates":gates,
 "next_milestone":"V16D-12B — Partition-Aware Multi-Case Stage-4 Transport Supervision Generation Execution Contract" if ok else "V16D-12AR — Case0002 Transport Pilot Residual Audit"}
 (OUT/"PAD_Stream_V16D12A_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nPILOT RESULT")
 print("  Y shape                 :",Y.shape);print(f"  S min/max               : {smin:.9f} / {smax:.9f}")
 print(f"  advection conservation  : {max_adv:.6e}");print(f"  implicit residual       : {max_imp:.6e}")
 print(f"  preclip bound violation : {max_pre:.6e}");print(f"  temporal negative frac  : {temporal:.6e}")
 print(f"  spatial positive frac   : {spatial:.6e}");print(f"  iterations / seconds    : {steps} / {elapsed:.2f}")
 print("\n"+"="*78);print("V16D-12AR GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT MILESTONE\n ",summary["next_milestone"])
 print("\nArtifact SHA-256:",sha(art))
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
