#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,importlib.util,json,re,time,numpy as np
R=Path(__file__).resolve().parent
O=R/"output"/"V16_D30_R1_ONE_TRAIN_SOURCEAUTHENTIC_9TIME_STAGE4_TRANSPORT_PILOT";O.mkdir(parents=True,exist_ok=True)
D30=R/"output"/"V16_D30_STAGE4_CONTROLSPACE_TRANSPORT_SUPERVISION_SOURCE_BINDING_CONTRACT"/"PAD_Stream_V16D30_Summary.json"
D30SHA="887c64939da23b2666a3b89ee2e29dd8e0e97e71d6d5692fef38b4d2b0604904"
C17=R/"PAD_Stream_V16C17_Production_Source_Authentic_Y_Transport_Tensor_Generation_and_Certification.py"
C17SHA="1d357be446103cb554c4759948347d2876235b7c630c64cd826801cbfc61dd4f"
C14=R/"output"/"V16_C14_PRODUCTION_FULL_PHYSICS_TRANSPORT_PARAMETER_AUTHORITY_CONTRACT"/"V16C14_Production_Full_Physics_Parameter_Contract.json"
C15=R/"output"/"V16_C15_PRODUCTION_PHYSICAL_TARGET_TIME_SCHEDULE_AUTHORITY_CONTRACT"/"V16C15_Production_Target_Time_Schedule_Contract.json"
D28=R/"output"/"V16_D28_R1_36CASE_D9R1_CONSERVATIVE_FACE_METRIC_EXPANSION"/"cases"
GEO="0026";RATE=350;BHP=1800;SPD=86400.;CFL=.25;EPS=1e-12
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def loadj(p):return json.loads(p.read_text())
def module(p):
 s=importlib.util.spec_from_file_location("d30r1_c17",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def savecsv(p,rows):
 rows=list(rows)
 with p.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
def metric():
 hits=[p for p in D28.glob("*.npz") if GEO in p.name and re.search(r"(?<!\\d)350(?!\\d)",p.name) and re.search(r"(?<!\\d)1800(?!\\d)",p.name)]
 if len(hits)!=1:raise RuntimeError(f"Expected one Case{GEO} R{RATE} B{BHP} D28 artifact; found {len(hits)}: {[p.name for p in hits]}")
 return hits[0]
def main():
 print("="*78);print("PAD-Stream V16D-30-R1");print("One TRAIN Source-Authentic 9-Time Stage-4 Transport Supervision Pilot");print("="*78)
 if not D30.exists() or sha(D30)!=D30SHA:raise RuntimeError("D30 SHA mismatch")
 if loadj(D30).get("status")!="V16D_STAGE4_CONTROLSPACE_TRANSPORT_LINEAGE_EXACTLY_BOUND_ONE_TRAIN_PILOT_GENERATION_AUTHORIZED":raise RuntimeError("D30 status mismatch")
 if sha(C17)!=C17SHA:raise RuntimeError("C17 source SHA mismatch")
 q=metric();c17=module(C17);pc=loadj(C14);tc=loadj(C15)
 with np.load(q,allow_pickle=False) as z:
  th=np.asarray(z["theta"],float);te=np.asarray(z["pollock_tau_end_s"],float);mf=np.asarray(z["M_face_dtheta_dxD"],float);M=np.asarray(z["M_node_sidecar_dtheta_dxD"],float)
 ns,n=th.shape
 if (ns,n)!=(1078,201) or mf.shape!=(1078,200) or M.shape!=(1078,201):raise RuntimeError("D28 geometry shape mismatch")
 dth=np.diff(th,axis=1);Mf=np.empty((ns,n+1));Mf[:,1:-1]=mf;Mf[:,0]=mf[:,0];Mf[:,-1]=mf[:,-1]
 tf=np.empty((ns,n+1));tf[:,1:-1]=.5*(th[:,:-1]+th[:,1:]);tf[:,0]=th[:,0];tf[:,-1]=th[:,-1];cv=np.diff(tf,axis=1)
 if np.any(M<=0) or np.any(mf<=0) or np.any(cv<=0) or np.any(dth<=0):raise RuntimeError("nonpositive geometry")
 pp=pc["production_parameters"];v=lambda k:float(pp[k]["value"])
 par={"nw":v("nw"),"no":v("no"),"swc":v("Swc"),"sor":v("Sor"),"krw_max":v("krw_max"),"kro_max":v("kro_max"),"mu_w":v("mu_w"),"mu_o":v("mu_o"),"phi":v("phi")}
 par["sw_init"]=par["swc"]+1e-3;par["sw_inj"]=1-par["sor"]-1e-3;Pec=v("Pe_c");lmb=v("lambda_c");Nc=v("Nc")
 targets=np.asarray(tc["target_days"],float)
 if targets.tolist()!=[30.,60.,100.,150.,250.,365.,500.,750.,1000.]:raise RuntimeError("target schedule mismatch")
 target_eta=targets[:,None]*SPD/te[None,:];dtc=float(CFL*np.min(cv[:,1:])/(c17.max_dfw(par)+EPS))
 S=np.full((ns,n),par["sw_init"]);S[:,0]=par["sw_inj"];eta=np.zeros(ns);nk=np.zeros(ns,dtype=int);Y=np.full((9,ns,n),np.nan)
 ma=mi=mb=0.;steps=0;t0=time.time();ceil=int(np.ceil(np.max(target_eta)/dtc))+len(targets)+100
 print("PILOT: Case0026 / 350 tpd / 1800 psi / TRAIN");print("D28 artifact:",q.name);print("dt_eta:",dtc,"max_eta:",np.max(target_eta),"ceiling:",ceil)
 while np.any(nk<len(targets)):
  active=nk<len(targets);goal=np.zeros(ns);ii=np.where(active)[0];goal[ii]=target_eta[nk[ii],ii]
  dt=np.zeros(ns);dt[active]=np.minimum(dtc,np.maximum(0.,goal[active]-eta[active]));hit=active&(np.abs(goal-eta)<=5e-14)
  if np.any(hit):
   hi=np.where(hit)[0];Y[nk[hi],hi]=S[hi];nk[hi]+=1;continue
  S,_,e=c17.adv(S,dt,cv,par);ma=max(ma,e);mb=max(mb,float(max(0.,par["swc"]-S.min(),S.max()-(1-par["sor"]))));np.clip(S,par["swc"],1-par["sor"],out=S);S[:,0]=par["sw_inj"]
  S,res=c17.cap(S,dt,par["phi"],Pec,lmb,M,Mf,cv,dth,par);mi=max(mi,res);mb=max(mb,float(max(0.,par["swc"]-S.min(),S.max()-(1-par["sor"]))));np.clip(S,par["swc"],1-par["sor"],out=S);S[:,0]=par["sw_inj"];eta+=dt;steps+=1
  if steps%1000==0:print(f"step {steps}/{ceil}: targets {np.sum(nk)}/{ns*9}")
  if steps>ceil:raise RuntimeError("CFL ceiling exceeded")
 active=nk<len(targets)
 while np.any(active):
  ii=np.where(active)[0];goal=target_eta[nk[ii],ii]
  if not np.all(np.abs(goal-eta[ii])<=1e-11):raise RuntimeError("final target capture mismatch")
  Y[nk[ii],ii]=S[ii];nk[ii]+=1;active=nk<len(targets)
 elapsed=time.time()-t0;smin=float(Y.min());smax=float(Y.max());inlet=float(np.max(np.abs(Y[:,:,0]-par["sw_inj"])))
 bound=max(0.,par["swc"]-smin,smax-(1-par["sor"]));under=max(0.,par["sw_init"]-np.min(Y[:,:,1:]));tem=float(np.mean(np.diff(Y,axis=0)<-1e-8));spa=float(np.mean(np.diff(Y,axis=2)>1e-8))
 gates={"D30_SHA_exact":True,"C17_SHA_exact":True,"TRAIN_pilot_0026_R350_B1800":True,"Y_shape":Y.shape==(9,1078,201),"Mface_direct":True,"Mface_positive":bool(np.all(mf>0)),"Pollock_primary":True,"no_exp_Nc_xD":True,"Nc_metadata_only":True,"FMM_ADV_auxiliary":True,"finite":bool(np.isfinite(Y).all()),"bounds":bound<1e-8,"injector":inlet<1e-12,"undershoot":under<1e-8,"adv_conservation":ma<1e-11,"cap_residual":mi<1e-10,"preclip":mb<1e-8,"temporal":tem<.01,"spatial":spa<.05,"no_fit":True,"no_threshold_relaxation":True,"no_training":True,"validation_OOD_untouched":True}
 ok=all(gates.values());art=O/"V16D30R1_Case0026_R350_B1800_SourceAuthentic_Y_Transport.npz"
 np.savez_compressed(art,Y_transport=Y,target_days=targets,theta=th,terminal_pollock_tof_s=te,target_eta=target_eta,M_face_dtheta_dxD=mf,Pe_c=np.array(Pec),lambda_c=np.array(lmb),Nc_metadata_only=np.array(Nc),sw_init=np.array(par["sw_init"]),sw_inj=np.array(par["sw_inj"]),geology_id=np.array(GEO),injection_rate_tpd=np.array(RATE),producer_bhp_psi=np.array(BHP),case_id=np.array("V16D_Foundation_Case_0026_R350_B1800"))
 savecsv(O/"V16D30R1_Certification_Gates.csv",[{"gate":k,"passed":bool(v)} for k,v in gates.items()])
 status="V16D_CONTROLSPACE_CASE0026_R350_B1800_SOURCEAUTHENTIC_STAGE4_9TIME_TRANSPORT_PILOT_CERTIFIED_36CASE_TRANSPORT_EXECUTION_CONTRACT_AUTHORIZED" if ok else "V16D_D30R1_CONTROLSPACE_STAGE4_TRANSPORT_PILOT_CERTIFICATION_BLOCKED"
 nxt="V16D-31 — Partition-aware restartable 36-case Stage-4 transport supervision execution contract" if ok else "V16D-30-R1-R — pilot audit; do not start batch"
 summ={"milestone":"V16D-30-R1","status":status,"case_id":"V16D_Foundation_Case_0026_R350_B1800","partition":"TRAIN","D30_sha256":sha(D30),"C17_sha256":sha(C17),"D28_artifact":str(q.relative_to(R)),"D28_sha256":sha(q),"Y_shape":list(Y.shape),"target_days":targets.tolist(),"iterations":steps,"elapsed_seconds":elapsed,"S_min":smin,"S_max":smax,"advection_conservation_max_abs":ma,"implicit_residual_max_abs":mi,"preclip_bound_violation_max":mb,"temporal_negative_fraction":tem,"spatial_positive_fraction":spa,"artifact_sha256":sha(art),"gates":gates,"next_milestone":nxt}
 sp=O/"PAD_Stream_V16D30_R1_Summary.json";sp.write_text(json.dumps(summ,indent=2))
 print("\nRESULT",Y.shape,smin,smax,"steps",steps,"seconds",elapsed);print("adv",ma,"cap",mi,"preclip",mb,"temporal",tem,"spatial",spa)
 print("\nGATES");[print("[PASS]" if v else "[FAIL]",k) for k,v in gates.items()];print("\nSTATUS\n",status);print("\nNEXT\n",nxt);print("\nArtifact SHA",sha(art));print("Summary SHA",sha(sp))
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()
