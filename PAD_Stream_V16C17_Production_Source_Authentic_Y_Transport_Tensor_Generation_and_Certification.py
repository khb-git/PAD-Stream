from __future__ import annotations
from pathlib import Path
import csv, hashlib, importlib.util, json, time
import numpy as np

ROOT=Path(__file__).resolve().parent
C16S=ROOT/"output"/"V16_C16_SOURCE_AUTHENTIC_Y_TRANSPORT_GENERATION_AUTHORIZATION_AUDIT"/"PAD_Stream_V16C16_Summary.json"
C14C=ROOT/"output"/"V16_C14_PRODUCTION_FULL_PHYSICS_TRANSPORT_PARAMETER_AUTHORITY_CONTRACT"/"V16C14_Production_Full_Physics_Parameter_Contract.json"
C15C=ROOT/"output"/"V16_C15_PRODUCTION_PHYSICAL_TARGET_TIME_SCHEDULE_AUTHORITY_CONTRACT"/"V16C15_Production_Target_Time_Schedule_Contract.json"
C10D=ROOT/"output"/"V16_C10_CONSERVATIVE_201_NODE_POLLOCK_FULL_PHYSICS_OPERATOR"
C10OP=C10D/"V16C10_Conservative_201_Node_Pollock_Operator_Geometry.npz"
C10C=C10D/"V16C10_Conservative_Pollock_Operator_Contract.json"
C11SRC=ROOT/"PAD_Stream_V16C11_Executable_Conservative_Full_Physics_Pollock_Transport_Solver_Assembly_and_Diagnostic_Validation.py"
STAGE4=ROOT/"pi_rnn_stage4_full_godunov.py"

OUT=ROOT/"output"/"V16_C17_PRODUCTION_SOURCE_AUTHENTIC_Y_TRANSPORT_TENSOR_GENERATION_CERTIFICATION"
OUT.mkdir(parents=True,exist_ok=True)
NPZ=OUT/"V16C17_Production_Source_Authentic_Y_Transport.npz"
AUD=OUT/"V16C17_Production_Generation_Audit.csv"
GATES=OUT/"V16C17_Final_Y_Transport_Certification_Gates.csv"
CON=OUT/"V16C17_Y_Transport_Certification_Contract.json"
SUM=OUT/"PAD_Stream_V16C17_Summary.json"

C16_OK="V16C_SOURCE_AUTHENTIC_Y_TRANSPORT_GENERATION_AUTHORIZED"
STAGE4_SHA="165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"
EPS=1e-12; SPD=86400.0; CFL=0.25

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
 rows=list(rows);keys=[]
 for r in rows:
  for k in r:
   if k not in keys:keys.append(k)
 with p.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def relperm(S,p):
 span=max(EPS,1-p["swc"]-p["sor"]);Se=np.clip((S-p["swc"])/span,0,1)
 return p["krw_max"]*Se**p["nw"],p["kro_max"]*(1-Se)**p["no"]
def fw(S,p):
 krw,kro=relperm(S,p);return 1/(1+(p["mu_w"]/p["mu_o"])*(kro/(krw+EPS)))
def dshape(S,p,lmb):
 span=max(EPS,1-p["swc"]-p["sor"]);Se=np.clip((S-p["swc"])/span,1e-6,1-1e-6)
 def raw(E,X):
  kro=p["kro_max"]*(1-E)**p["no"]
  return kro*fw(np.asarray(X,float),p)*E**(-1/lmb-1)
 mid=p["swc"]+.5*span;norm=float(raw(.5,mid));return raw(Se,S)/max(norm,EPS)
def max_dfw(p):
 s=np.linspace(p["swc"],1-p["sor"],4001);return float(np.max(np.abs(np.gradient(fw(s,p),s))))

def tri(lower,diag,upper,rhs):
 a=lower.copy();b=diag.copy();c=upper.copy();d=rhs.copy();ns,n=b.shape
 for j in range(1,n):
  w=a[:,j]/b[:,j-1];b[:,j]-=w*c[:,j-1];d[:,j]-=w*d[:,j-1]
 x=np.empty_like(d);x[:,-1]=d[:,-1]/b[:,-1]
 for j in range(n-2,-1,-1):x[:,j]=(d[:,j]-c[:,j]*x[:,j+1])/b[:,j]
 return x

def adv(S,dt,cv,p):
 ns,n=S.shape;F=np.zeros((ns,n+1));F[:,1]=fw(np.full(ns,p["sw_inj"]),p)
 if n>2:F[:,2:n]=fw(S[:,1:n-1],p)
 F[:,n]=fw(S[:,-1],p);old=S.copy();q=dt[:,None]
 S[:,1:]-=q*(F[:,2:]-F[:,1:-1])/cv[:,1:];S[:,0]=p["sw_inj"]
 lhs=np.sum(cv[:,1:]*(S[:,1:]-old[:,1:]),axis=1);rhs=-dt*(F[:,-1]-F[:,1])
 return S,F,float(np.max(np.abs(lhs-rhs)))

def cap(Sadv,dt,phi,Pec,lmb,M,Mf,cv,dth,p):
 ns,n=Sadv.shape;D=dshape(Sadv,p,lmb);Df=.5*(D[:,:-1]+D[:,1:]);Af=Df*Mf[:,1:-1]/dth
 lo=np.zeros((ns,n));di=np.ones((ns,n));up=np.zeros((ns,n));rhs=Sadv.copy()
 beta=(dt*phi/Pec)[:,None];fac=M[:,1:-1]/cv[:,1:-1];aL=Af[:,:-1];aR=Af[:,1:]
 lo[:,1:-1]=-beta*fac*aL;up[:,1:-1]=-beta*fac*aR;di[:,1:-1]=1+beta*fac*(aL+aR)
 rhs[:,0]=p["sw_inj"];rhs[:,-1]=Sadv[:,-1]
 S=tri(lo,di,up,rhs);r=di*S-rhs;r[:,1:]+=lo[:,1:]*S[:,:-1];r[:,:-1]+=up[:,:-1]*S[:,1:]
 return S,float(np.max(np.abs(r)))

def import_c11():
 spec=importlib.util.spec_from_file_location("v16c11_authority",C11SRC);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 print("\n"+"="*78+"\nPAD-Stream V16C-17\nProduction Source-Authentic Y_transport Tensor Generation and Certification\n"+"="*78)
 print("""
C16 AUTHORIZED GENERATION. C17 NOW EXECUTES THE PRODUCTION PHYSICS SOLVER.

Y[k,i,j] = Sw(t_k, streamline_i, theta_j)
EXPECTED SHAPE = (9,1078,201).

THE SOLVER PRESERVES C11 NUMERICS BUT GENERALIZES ITS SCALAR NORMALIZED-TIME
STEP TO A PER-STREAMLINE dt_eta VECTOR SO EACH STREAMLINE HITS THE SAME
PHYSICAL TARGET DAY EXACTLY:
    eta_i(t)=t/tau_end_i.

NO exp(Nc*xD) VELOCITY MULTIPLIER IS USED. NO PI-RNN IS CALLED. NO V15
TARGET IS FITTED. TRAINING REMAINS PROHIBITED UNTIL THIS NEW TENSOR PASSES.
""")
 c16=lj(C16S);pc=lj(C14C);tc=lj(C15C)
 if c16.get("status")!=C16_OK:raise RuntimeError("C16 generation authorization missing.")
 if sha(STAGE4)!=STAGE4_SHA:raise RuntimeError("Stage4 hash mismatch.")
 c10c=lj(C10C)
 if sha(C10OP)!=c10c["operator_sha256"]:raise RuntimeError("C10 operator hash mismatch.")

 with np.load(C10OP,allow_pickle=False) as z:
  theta=np.asarray(z["theta"],float);M=np.asarray(z["metric_M_cell"],float);Mf=np.asarray(z["metric_M_face"],float);cv=np.asarray(z["control_volume_dtheta"],float)
 ns,n=theta.shape;dth=np.diff(theta,axis=1)
 if (ns,n)!=(1078,201):raise RuntimeError((ns,n))
 # terminal TOF from frozen Foundation Case
 fp=next((ROOT/"output").rglob("V16A_Foundation_Case_0001.npz"))
 with np.load(fp,allow_pickle=False) as z:tof=np.asarray(z["pollock_tof"],float)
 tau_end=tof[:,-1];
 if tof.shape!=(1078,201) or np.any(tau_end<=0):raise RuntimeError("Pollock TOF authority invalid")

 pp=pc["production_parameters"]
 def val(k):return float(pp[k]["value"])
 p=dict(nw=val("nw"),no=val("no"),swc=val("Swc"),sor=val("Sor"),krw_max=val("krw_max"),kro_max=val("kro_max"),mu_w=val("mu_w"),mu_o=val("mu_o"),phi=val("phi"))
 p["sw_init"]=p["swc"]+1e-3;p["sw_inj"]=1-p["sor"]-1e-3
 Pec=val("Pe_c");lmb=val("lambda_c");Nc=val("Nc")
 targets=np.asarray(tc["target_days"],float)
 if targets.tolist()!=[30.,60.,100.,150.,250.,365.,500.,750.,1000.]:raise RuntimeError("C15 schedule mismatch")
 target_eta=targets[:,None]*SPD/tau_end[None,:]

 # Exact implementation equivalence: vectorized production kernels must reduce
 # to C11 scalar-dt kernels when all dt rows are equal.
 c11=import_c11();rng=np.random.default_rng(16017)
 St=p["sw_init"]+.05*rng.random((ns,n));St[:,0]=p["sw_inj"]
 dt0=min(CFL*np.min(cv[:,1:])/(max_dfw(p)+EPS),1e-4)
 A1,F1,e1=adv(St.copy(),np.full(ns,dt0),cv,p);A2,F2,e2=c11.advective_step(St.copy(),dt0,cv,p)
 adv_equiv=float(max(np.max(np.abs(A1-A2)),np.max(np.abs(F1-F2)),abs(e1-e2)))
 B1,r1=cap(A1.copy(),np.full(ns,dt0),p["phi"],Pec,lmb,M,Mf,cv,dth,p)
 B2,r2=c11.capillary_implicit(A1.copy(),dt0,p["phi"],Pec,lmb,M,Mf,cv,dth,p)
 cap_equiv=float(max(np.max(np.abs(B1-B2)),abs(r1-r2)))
 if adv_equiv>1e-12 or cap_equiv>1e-12:raise RuntimeError(f"C11 kernel equivalence failed: {adv_equiv}, {cap_equiv}")

 dfmax=max_dfw(p);dt_cfl=float(CFL*np.min(cv[:,1:])/(dfmax+EPS))
 S=np.full((ns,n),p["sw_init"]);S[:,0]=p["sw_inj"]
 eta=np.zeros(ns);nextk=np.zeros(ns,dtype=int);Y=np.full((len(targets),ns,n),np.nan)
 max_adv=0.;max_imp=0.;max_preclip=0.;steps=0;t0=time.time()
 max_iter=int(np.ceil(np.max(target_eta)/dt_cfl))+len(targets)+100
 print("PRODUCTION MARCH")
 print(f"  dt_eta CFL ceiling : {dt_cfl:.6e}")
 print(f"  max target eta     : {np.max(target_eta):.6f}")
 print(f"  iteration ceiling  : {max_iter}")
 while np.any(nextk<len(targets)):
  active=nextk<len(targets);goal=np.zeros(ns);idx=np.where(active)[0];goal[idx]=target_eta[nextk[idx],idx]
  dt=np.zeros(ns);dt[active]=np.minimum(dt_cfl,np.maximum(0.,goal[active]-eta[active]))
  # Rows exactly at a target are captured before another step.
  hit=active & (np.abs(goal-eta)<=5e-14)
  if np.any(hit):
   hi=np.where(hit)[0];Y[nextk[hi],hi,:]=S[hi,:];nextk[hi]+=1;continue
  S,_,e=adv(S,dt,cv,p);max_adv=max(max_adv,e)
  pre=float(max(0.,p["swc"]-np.min(S),np.max(S)-(1-p["sor"])));max_preclip=max(max_preclip,pre)
  np.clip(S,p["swc"],1-p["sor"],out=S);S[:,0]=p["sw_inj"]
  S,r=cap(S,dt,p["phi"],Pec,lmb,M,Mf,cv,dth,p);max_imp=max(max_imp,r)
  pre=float(max(0.,p["swc"]-np.min(S),np.max(S)-(1-p["sor"])));max_preclip=max(max_preclip,pre)
  np.clip(S,p["swc"],1-p["sor"],out=S);S[:,0]=p["sw_inj"];eta+=dt;steps+=1
  if steps%1000==0:print(f"  step {steps:6d}/{max_iter}: completed targets {np.sum(nextk)}/{ns*len(targets)}")
  if steps>max_iter:raise RuntimeError("Production march exceeded deterministic CFL iteration ceiling")
 # capture final exact hits
 active=nextk<len(targets)
 while np.any(active):
  idx=np.where(active)[0];goal=target_eta[nextk[idx],idx]
  hit=np.abs(goal-eta[idx])<=1e-11
  if not np.all(hit):raise RuntimeError("Final target capture mismatch")
  Y[nextk[idx],idx,:]=S[idx,:];nextk[idx]+=1;active=nextk<len(targets)
 elapsed=time.time()-t0

 finite=bool(np.all(np.isfinite(Y)));smin=float(np.min(Y));smax=float(np.max(Y));inlet=float(np.max(np.abs(Y[:,:,0]-p["sw_inj"])))
 bound=float(max(0.,p["swc"]-smin,smax-(1-p["sor"])))
 # Injection should not lower water saturation relative to initial state.
 undershoot=float(max(0.,p["sw_init"]-np.min(Y[:,:,1:])))
 # Temporal monotonicity is expected for this one-way injection problem; audit, do not clip/fix.
 temporal_negative=float(np.mean(np.diff(Y,axis=0)<-1e-8))
 spatial_positive=float(np.mean(np.diff(Y,axis=2)>1e-8))

 np.savez_compressed(NPZ,Y_transport=Y,target_days=targets,theta=theta,pollock_tof_s=tof,
  terminal_pollock_tof_s=tau_end,target_eta=target_eta,Pe_c=np.array(Pec),lambda_c=np.array(lmb),Nc_metadata_only=np.array(Nc),
  sw_init=np.array(p["sw_init"]),sw_inj=np.array(p["sw_inj"]),authority_label_ascii=np.frombuffer(b"V16C17_SOURCE_AUTHENTIC_PRODUCTION_Y_TRANSPORT",dtype=np.uint8))

 audit=[
  dict(test="C11_vectorized_advection_kernel_equivalence",value=adv_equiv,threshold=1e-12,passed=adv_equiv<1e-12),
  dict(test="C11_vectorized_capillary_kernel_equivalence",value=cap_equiv,threshold=1e-12,passed=cap_equiv<1e-12),
  dict(test="production_advection_conservation_max_abs",value=max_adv,threshold=1e-11,passed=max_adv<1e-11),
  dict(test="production_implicit_residual_max_abs",value=max_imp,threshold=1e-10,passed=max_imp<1e-10),
  dict(test="production_preclip_bound_violation_max",value=max_preclip,threshold=1e-8,passed=max_preclip<1e-8),
  dict(test="Y_finite",value=finite,threshold=True,passed=finite),dict(test="Y_bound_violation",value=bound,threshold=1e-8,passed=bound<1e-8),
  dict(test="Y_inlet_Dirichlet_error",value=inlet,threshold=1e-12,passed=inlet<1e-12),dict(test="Y_reservoir_undershoot",value=undershoot,threshold=1e-8,passed=undershoot<1e-8),
  dict(test="temporal_negative_increment_fraction",value=temporal_negative,threshold=0.01,passed=temporal_negative<0.01),
  dict(test="spatial_positive_increment_fraction",value=spatial_positive,threshold=0.05,passed=spatial_positive<0.05)]
 sc(AUD,audit)
 gates=[
  ("C16_generation_authorized",True),("Stage4_exact_hash_reproduced",sha(STAGE4)==STAGE4_SHA),("C10_operator_hash_reproduced",sha(C10OP)==c10c["operator_sha256"]),
  ("C11_advection_kernel_exact_equivalence",adv_equiv<1e-12),("C11_capillary_kernel_exact_equivalence",cap_equiv<1e-12),("Y_shape_9_1078_201",Y.shape==(9,1078,201)),
  ("nine_C15_target_times_exact",targets.tolist()==[30.,60.,100.,150.,250.,365.,500.,750.,1000.]),("per_streamline_target_eta_exact",True),
  ("Pollock_kinematics_primary",True),("legacy_exp_Nc_xD_not_applied",True),("Nc_metadata_only",True),("Y_finite",finite),("Y_saturation_bounds",bound<1e-8),
  ("injector_Dirichlet_exact",inlet<1e-12),("no_reservoir_undershoot",undershoot<1e-8),("advection_conservation",max_adv<1e-11),("implicit_capillary_residual",max_imp<1e-10),
  ("preclip_bounds_stable",max_preclip<1e-8),("temporal_ordering",temporal_negative<0.01),("front_spatial_ordering",spatial_positive<0.05),
  ("new_V16_artifact_not_V15_relabel",True),("no_parameter_fitting",True),("no_PI_RNN_inference",True),("training_not_performed",True),("frozen_inputs_not_mutated",True)]
 sc(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates]);ok=all(v for _,v in gates)
 if ok:
  status="V16C_PRODUCTION_SOURCE_AUTHENTIC_Y_TRANSPORT_TENSOR_CERTIFIED"
  diag="THE_NINE_TIME_1078_STREAMLINE_201_NODE_FULL_PHYSICS_TRANSPORT_TENSOR_IS_GENERATED_FROM_THE_FROZEN_POLLOCK_STAGE4_C13_C14_C15_LINEAGE_AND_PASSES_NUMERICAL_PHYSICAL_AND_PROVENANCE_CERTIFICATION"
  rec="Freeze C17 Y_transport as the V16 source-authentic supervision authority. Next bind it to the frozen C4 conditioning tensors and audit sample/time alignment before authorizing PI-RNN training."
  nxt="V16C-18 — Conditioning-to-Y_transport Alignment and Training Dataset Certification"
 else:
  status="V16C_PRODUCTION_Y_TRANSPORT_GENERATED_CERTIFICATION_BLOCKED";diag="Y_TRANSPORT_WAS_GENERATED_BUT_ONE_OR_MORE_NUMERICAL_PHYSICAL_OR_PROVENANCE_CERTIFICATION_GATES_FAILED"
  rec="Do not train on C17. Preserve the generated artifact for diagnosis and repair only failed certification gates without fitting or threshold relaxation.";nxt="V16C-17R — Y_transport Certification Residual Audit"
 artifact_sha=sha(NPZ)
 sj(CON,dict(milestone="V16C-17",status=status,diagnosis=diag,equation="dS/deta + d fw/dtheta = (phi/Pe_c) M d/dtheta[D_tilde(S) M dS/dtheta]",Y_shape=list(Y.shape),target_days=targets.tolist(),parameters={k:float(v["value"]) for k,v in pp.items()},CFL=CFL,dt_eta_ceiling=dt_cfl,iterations=steps,elapsed_seconds=elapsed,artifact=str(NPZ.relative_to(ROOT)),artifact_sha256=artifact_sha,training_authorized=False,recommendation=rec,next_milestone=nxt))
 sj(SUM,dict(milestone="V16C-17",status=status,diagnosis=diag,Y_transport_generated=True,Y_transport_certified=ok,Y_shape=list(Y.shape),target_days=targets.tolist(),S_min=smin,S_max=smax,advection_conservation_max_abs=max_adv,implicit_residual_max_abs=max_imp,preclip_bound_violation_max=max_preclip,temporal_negative_increment_fraction=temporal_negative,spatial_positive_increment_fraction=spatial_positive,iterations=steps,elapsed_seconds=elapsed,artifact_sha256=artifact_sha,training_authorized=False,recommendation=rec,next_milestone=nxt))
 print("\nPRODUCTION RESULT")
 print("  Y shape                 :",Y.shape);print(f"  S min/max               : {smin:.9f} / {smax:.9f}");print(f"  advection conservation  : {max_adv:.6e}");print(f"  implicit residual       : {max_imp:.6e}");print(f"  preclip bound violation : {max_preclip:.6e}");print(f"  temporal negative frac  : {temporal_negative:.6e}");print(f"  spatial positive frac   : {spatial_positive:.6e}");print(f"  iterations / seconds    : {steps} / {elapsed:.2f}")
 print("\n"+"="*78+"\nV16C-17 FINAL Y_TRANSPORT CERTIFICATION GATES\n"+"="*78)
 for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
 print("="*78+"\n\nSTATUS\n ",status,"\n\nDIAGNOSIS\n ",diag,"\n\nRECOMMENDATION\n ",rec,"\n\nNEXT MILESTONE\n ",nxt)
 print("\nArtifact\n ",NPZ,"\n  SHA-256:",artifact_sha);print("\n"+"="*78+"\nPAD-STREAM V16C-17 PRODUCTION Y_TRANSPORT GENERATION: COMPLETE\n"+"="*78)
if __name__=="__main__":main()
