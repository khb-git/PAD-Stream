#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,importlib.util,json,re,time,numpy as np
R=Path(__file__).resolve().parent
O=R/"output"/"V16_D31B_R1_RESTARTABLE_VALIDATION_9CASE_STAGE4_TRANSPORT"; C=O/"cases"; C.mkdir(parents=True,exist_ok=True)
D31=R/"output"/"V16_D31B_VALIDATION_PARTITION_STAGE4_TRANSPORT_GENERATION_CONTRACT"/"PAD_Stream_V16D31B_Summary.json"
D31SHA="fc9b8aaaf0d06a9db01c324d205334007b811664bd4f51a2995df136859a3561"
C17=R/"PAD_Stream_V16C17_Production_Source_Authentic_Y_Transport_Tensor_Generation_and_Certification.py"
C17SHA="1d357be446103cb554c4759948347d2876235b7c630c64cd826801cbfc61dd4f"
C14=R/"output"/"V16_C14_PRODUCTION_FULL_PHYSICS_TRANSPORT_PARAMETER_AUTHORITY_CONTRACT"/"V16C14_Production_Full_Physics_Parameter_Contract.json"
C15=R/"output"/"V16_C15_PRODUCTION_PHYSICAL_TARGET_TIME_SCHEDULE_AUTHORITY_CONTRACT"/"V16C15_Production_Target_Time_Schedule_Contract.json"
D28=R/"output"/"V16_D28_R1_36CASE_D9R1_CONSERVATIVE_FACE_METRIC_EXPANSION"/"cases"
SPD=86400.;CFL=.25;EPS=1e-12
VALIDATION=[("0028",r,b) for r in (350,500,650) for b in (1800,2000,2200)]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for x in iter(lambda:f.read(1<<20),b""):h.update(x)
 return h.hexdigest()
def J(p):return json.loads(p.read_text())
def M(p):
 s=importlib.util.spec_from_file_location("d31a_c17",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def js(o):
 if isinstance(o,np.generic):return o.item()
 if isinstance(o,np.ndarray):return o.tolist()
 raise TypeError(type(o).__name__)
def metric(g,r,b):
 h=[p for p in D28.glob("*.npz") if g in p.name and re.search(fr"(?<!\d){r}(?!\d)",p.name) and re.search(fr"(?<!\d){b}(?!\d)",p.name)]
 if len(h)!=1:raise RuntimeError(f"metric identity {g}/{r}/{b}: {len(h)}")
 return h[0]
def paths(g,r,b):
 stem=f"V16D_Foundation_Case_{g}_R{r}_B{b}_Stage4_Transport"
 return C/(stem+".npz"),C/(stem+"_Summary.json")
def certified(a,s,g,r,b):
 if not a.exists() or not s.exists():return False
 try:
  q=J(s);return q.get("status")=="CERTIFIED" and q.get("artifact_sha256")==sha(a) and q.get("case_id")==f"V16D_Foundation_Case_{g}_R{r}_B{b}"
 except:return False
def main():
 print("="*78);print("PAD-Stream V16D-31B-R1");print("Restartable VALIDATION 9-Case Stage-4 Transport Supervision Generator");print("="*78)
 if not D31.exists() or sha(D31)!=D31SHA:raise RuntimeError("D31 SHA mismatch")
 if sha(C17)!=C17SHA:raise RuntimeError("C17 SHA mismatch")
 c17=M(C17);pc=J(C14);tc=J(C15);pp=pc["production_parameters"];v=lambda k:float(pp[k]["value"])
 par={k:v(x) for k,x in [("nw","nw"),("no","no"),("swc","Swc"),("sor","Sor"),("krw_max","krw_max"),("kro_max","kro_max"),("mu_w","mu_w"),("mu_o","mu_o"),("phi","phi")]}
 par["sw_init"]=par["swc"]+1e-3;par["sw_inj"]=1-par["sor"]-1e-3;Pec=v("Pe_c");lam=v("lambda_c");Nc=v("Nc")
 days=np.asarray(tc["target_days"],float)
 if days.tolist()!=[30.,60.,100.,150.,250.,365.,500.,750.,1000.]:raise RuntimeError("target days mismatch")
 rows=[]
 for ic,(g,r,b) in enumerate(VALIDATION,1):
  a,sp=paths(g,r,b)
  if certified(a,sp,g,r,b):
   print(f"[SKIP {ic:02d}/9] Case{g} R{r} B{b} certified");q=J(sp);rows.append(q);continue
  q=metric(g,r,b)
  with np.load(q,allow_pickle=False) as z:
   th=np.asarray(z["theta"],float);te=np.asarray(z["pollock_tau_end_s"],float);mf=np.asarray(z["M_face_dtheta_dxD"],float);Mn=np.asarray(z["M_node_sidecar_dtheta_dxD"],float)
  if th.ndim==1:
   if th.shape!=(201,):raise RuntimeError("theta schema")
   ns=mf.shape[0];n=th.size;th=np.broadcast_to(th[None,:],(ns,n)).copy()
  else:ns,n=th.shape
  if (ns,n)!=(1078,201) or mf.shape!=(1078,200) or Mn.shape!=(1078,201):raise RuntimeError("geometry shape")
  dth=np.diff(th,axis=1);Mf=np.empty((ns,n+1));Mf[:,1:-1]=mf;Mf[:,0]=mf[:,0];Mf[:,-1]=mf[:,-1]
  tf=np.empty((ns,n+1));tf[:,1:-1]=.5*(th[:,:-1]+th[:,1:]);tf[:,0]=th[:,0];tf[:,-1]=th[:,-1];cv=np.diff(tf,axis=1)
  etaT=days[:,None]*SPD/te[None,:];dtc=float(CFL*np.min(cv[:,1:])/(c17.max_dfw(par)+EPS))
  S=np.full((ns,n),par["sw_init"]);S[:,0]=par["sw_inj"];eta=np.zeros(ns);nk=np.zeros(ns,dtype=int);Y=np.full((9,ns,n),np.nan)
  ma=mi=mb=0.;steps=0;t0=time.time();ceil=int(np.ceil(np.max(etaT)/dtc))+109
  print(f"\n[RUN {ic:02d}/9] Case{g} R{r} B{b} dt={dtc:.6e} ceiling={ceil}")
  while np.any(nk<9):
   active=nk<9;goal=np.zeros(ns);ii=np.where(active)[0];goal[ii]=etaT[nk[ii],ii]
   dt=np.zeros(ns);dt[active]=np.minimum(dtc,np.maximum(0.,goal[active]-eta[active]));hit=active&(np.abs(goal-eta)<=5e-14)
   if np.any(hit):
    hi=np.where(hit)[0];Y[nk[hi],hi]=S[hi];nk[hi]+=1;continue
   S,_,e=c17.adv(S,dt,cv,par);ma=max(ma,e);mb=max(mb,float(max(0.,par["swc"]-S.min(),S.max()-(1-par["sor"]))));np.clip(S,par["swc"],1-par["sor"],out=S);S[:,0]=par["sw_inj"]
   S,res=c17.cap(S,dt,par["phi"],Pec,lam,Mn,Mf,cv,dth,par);mi=max(mi,res);mb=max(mb,float(max(0.,par["swc"]-S.min(),S.max()-(1-par["sor"]))));np.clip(S,par["swc"],1-par["sor"],out=S);S[:,0]=par["sw_inj"];eta+=dt;steps+=1
   if steps%2000==0:print(f"  step {steps}/{ceil} targets {np.sum(nk)}/{ns*9}")
   if steps>ceil:raise RuntimeError("CFL ceiling")
  ii=np.where(nk<9)[0]
  if len(ii):raise RuntimeError("target capture incomplete")
  elapsed=time.time()-t0;smin=float(Y.min());smax=float(Y.max());tem=float(np.mean(np.diff(Y,axis=0)<-1e-8));spa=float(np.mean(np.diff(Y,axis=2)>1e-8))
  gates={"finite":bool(np.isfinite(Y).all()),"shape":Y.shape==(9,1078,201),"bounds":max(0.,par["swc"]-smin,smax-(1-par["sor"]))<1e-8,
   "injector":float(np.max(np.abs(Y[:,:,0]-par["sw_inj"])))<1e-12,"undershoot":max(0.,par["sw_init"]-float(np.min(Y[:,:,1:])))<1e-8,
   "adv_conservation":ma<1e-11,"cap_residual":mi<1e-10,"preclip":mb<1e-8,"temporal":tem<.01,"spatial":spa<.05}
  ok=bool(all(gates.values()))
  # Write artifact first only after all scientific gates have been evaluated.
  np.savez_compressed(a,Y_transport=Y,target_days=days,theta=th[0],terminal_pollock_tof_s=te,target_eta=etaT,M_face_dtheta_dxD=mf,
   Pe_c=np.array(Pec),lambda_c=np.array(lam),Nc_metadata_only=np.array(Nc),case_id=np.array(f"V16D_Foundation_Case_{g}_R{r}_B{b}"))
  rec={"case_id":f"V16D_Foundation_Case_{g}_R{r}_B{b}","partition":"VALIDATION","status":"CERTIFIED" if ok else "BLOCKED",
   "metric_sha256":sha(q),"artifact_sha256":sha(a),"steps":steps,"elapsed_seconds":elapsed,"S_min":smin,"S_max":smax,
   "adv_max":ma,"cap_max":mi,"preclip_max":mb,"temporal_negative_fraction":tem,"spatial_positive_fraction":spa,"gates":gates}
  sp.write_text(json.dumps(rec,indent=2,default=js));rows.append(rec)
  print("  ->",rec["status"],"artifact",rec["artifact_sha256"])
  if not ok:raise SystemExit(2)
 # Final manifest is created only when all 18 exact TRAIN cases are certified.
 final=[]
 for g,r,b in VALIDATION:
  a,sp=paths(g,r,b)
  if not certified(a,sp,g,r,b):raise RuntimeError(f"uncertified final case {g}/{r}/{b}")
  final.append(J(sp))
 man=O/"V16D31B_R1_VALIDATION_9Case_Manifest.json";man.write_text(json.dumps({"milestone":"V16D-31A","status":"CERTIFIED","count":18,
  "partition":"VALIDATION","cases":final,"no_validation":True,"no_locked_OOD":True,"no_training":True,"no_normalization":True,"no_deduplication":True},indent=2,default=js))
 sm=O/"PAD_Stream_V16D31B_R1_Summary.json";sm.write_text(json.dumps({"milestone":"V16D-31B-R1",
  "status":"V16D_VALIDATION_9CASE_STAGE4_TRANSPORT_SUPERVISION_GENERATED_CERTIFIED_LOCKED_OOD_GENERATION_CONTRACT_AUTHORIZED",
  "certified_cases":9,"partition":"VALIDATION","TRAIN_not_regenerated":True,"locked_OOD_untouched":True,
  "manifest_sha256":sha(man),"next_milestone":"V16D-31C — locked-OOD Stage-4 transport generation contract"},indent=2))
 print("\n"+"="*78);print("V16D-31B-R1 COMPLETE — 9/9 VALIDATION CASES CERTIFIED");print("="*78)
 print("Manifest SHA-256:",sha(man));print("Summary SHA-256 :",sha(sm))
if __name__=="__main__":main()
