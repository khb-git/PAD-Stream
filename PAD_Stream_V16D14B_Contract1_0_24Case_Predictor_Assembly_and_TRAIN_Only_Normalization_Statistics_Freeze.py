#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,numpy as np,sys,time
R=Path(__file__).resolve().parent
AR3=R/"output"/"V16_D14AR3_NEW_EXPLICIT_STREAMLINE_TO_GRID_SAMPLING_CONTRACT"
SUM=AR3/"PAD_Stream_V16D14AR3_Summary.json"
CON=AR3/"V16D14AR3_Streamline_to_Grid_Sampling_Contract_1.0.json"
SUMSHA="8c3236a34d9d4be1779c69ba439a2fc258d61d426e5ed94f7257113c877b3b63"
CONSHA="32fec4b708108fb708bd40cc0983d4de093516a4a84b90b7ae9c3020a2383181"
D14=R/"output"/"V16_D14_SOURCEBOUND_24CASE_PREDICTOR_SCHEMA_AUDIT"/"V16D14_Source_Binding_Registry.json"
O=R/"output"/"V16_D14B_CONTRACT1_0_24CASE_PREDICTOR_ASSEMBLY_TRAIN_ONLY_STATS";O.mkdir(parents=True,exist_ok=True)
CASEDIR=O/"cases";CASEDIR.mkdir(exist_ok=True)
TRAIN=["0020","0015","0013","0004","0006","0002","0023","0016","0009","0019","0017","0024","0003","0011","0014","0007"]
VAL=["0010","0025","0008","0012"];TEST=["0005","0018","0021","0022"];ALL=TRAIN+VAL+TEST
DAYS=np.array([30,60,100,150,250,365,500,750,1000.],np.float64)
FEATURES=["xi","pollock_tau_hat","adv_tau_hat","log10_Kh","log10_Kz_over_Kh","porosity","pressure_z","target_time_hat","target_eta_sequence"]
DX,DY,DZ=6.096,6.096,1.2192;NX,NY,NZ=50,50,15;TOL=1e-8
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def fld(z,names,shape):
 h=[n for n in names if n in z.files and np.asarray(z[n]).shape==shape]
 if len(h)!=1:raise RuntimeError(f"expected exactly one {names} shape={shape}, got {h}")
 return np.asarray(z[h[0]],np.float64),h[0]
def sample_idx(xyz):
 lo=xyz.min(axis=(0,1));hi=xyz.max(axis=(0,1));mx=np.array([NX*DX,NY*DY,NZ*DZ])
 if np.any(lo < -TOL) or np.any(hi > mx+TOL):raise RuntimeError(f"materially outside domain: min={lo}, max={hi}, domainmax={mx}")
 i=np.clip(np.floor(xyz[...,0]/DX).astype(np.int64),0,NX-1)
 j=np.clip(np.floor(xyz[...,1]/DY).astype(np.int64),0,NY-1)
 k=np.clip(np.floor(xyz[...,2]/DZ).astype(np.int64),0,NZ-1)
 return k,j,i
def adv_on_path(a,xyz):
 # Prefer already-persisted 1078x201 path values. If D10C stores Eulerian ADV,
 # Contract-1.0 applies the SAME containing-cell map explicitly.
 for names in (["adv_tau_s","tau_adv_s","tau_ADV_s","adv_tau","tau_ADV"],):
  for n in names:
   if n in a.files:
    x=np.asarray(a[n],np.float64)
    if x.shape==(1078,201):return x,n,"persisted_path"
    if x.shape==(NZ,NY,NX):
     k,j,i=sample_idx(xyz);return x[k,j,i],n,"contract1_grid_sample"
 raise RuntimeError("ADV field/path representation not uniquely supported")
def assemble(c,reg):
 part="TRAIN" if c in TRAIN else ("VALIDATION" if c in VAL else "LOCKED_OOD_TEST")
 rr=reg[c];gp=Path(rr["geology_flow"]);pp=Path(rr["pollock_metric"]);ap=Path(rr["adv_travel_time"])
 with np.load(gp,allow_pickle=False) as g,np.load(pp,allow_pickle=False) as p,np.load(ap,allow_pickle=False) as a:
  Kx,kx=fld(g,["Kx"],(NZ,NY,NX));Ky,ky=fld(g,["Ky"],(NZ,NY,NX));Kz,kz=fld(g,["Kz"],(NZ,NY,NX))
  por,kpor=fld(g,["porosity","phi"],(NZ,NY,NX));pr,kpr=fld(g,["pressure"],(NZ,NY,NX))
  theta,kth=fld(p,["theta"],(201,));pt,kpt=fld(p,["pollock_tau_s"],(1078,201));pe,kpe=fld(p,["pollock_tau_end_s"],(1078,))
  xyz,kxyz=fld(p,["streamline_xyz","xyz","transport_xyz"],(1078,201,3))
  adv,kadv,advmode=adv_on_path(a,xyz)
 k,j,i=sample_idx(xyz);Kxp=Kx[k,j,i];Kyp=Ky[k,j,i];Kzp=Kz[k,j,i];phip=por[k,j,i];ppath=pr[k,j,i]
 Kh=np.sqrt(Kxp*Kyp)
 if np.any(Kh<=0) or np.any(Kzp<=0) or np.any(pe<=0):raise RuntimeError(f"Case{c}: nonpositive K/TOF")
 raw=np.empty((9,1078,201,9),np.float64)
 base={"xi":np.broadcast_to(theta,(1078,201)),"pollock_tau_hat":pt/pe[:,None],"adv_tau_hat":adv/pe[:,None],
       "log10_Kh":np.log10(Kh),"log10_Kz_over_Kh":np.log10(Kzp/Kh),"porosity":phip}
 # pressure_z is deliberately RAW here; TRAIN-only z-score is applied after global stats freeze.
 for t,d in enumerate(DAYS):
  vals=[base["xi"],base["pollock_tau_hat"],base["adv_tau_hat"],base["log10_Kh"],base["log10_Kz_over_Kh"],
        base["porosity"],ppath,np.full((1078,201),d/1000.0),np.broadcast_to(86400*d/pe[:,None],(1078,201))]
  raw[t]=np.stack(vals,axis=-1)
 meta={"case_id":c,"partition":part,"feature_order":FEATURES,"shape":list(raw.shape),"sampling_contract":"V16D_STREAMLINE_TO_GRID_SAMPLING_1.0",
       "source":{"geology_flow":str(gp),"pollock":str(pp),"adv":str(ap),"Kx":kx,"Ky":ky,"Kz":kz,"porosity":kpor,"pressure":kpr,"theta":kth,"pollock_tau":kpt,"pollock_tau_end":kpe,"xyz":kxyz,"adv_key":kadv,"adv_mode":advmode}}
 return raw,meta
def main():
 print("="*78);print("PAD-Stream V16D-14B");print("Contract-1.0 24-Case Predictor Assembly + TRAIN-Only Normalization Statistics Freeze");print("="*78)
 print("NO TARGET Y IS READ. TRAIN FITS NORMALIZATION; VALIDATION/OOD ARE TRANSFORM-ONLY. NO MODEL TRAINING.")
 if sha(SUM)!=SUMSHA or sha(CON)!=CONSHA:raise RuntimeError("AR3 authority SHA mismatch")
 if json.loads(SUM.read_text())["status"]!="V16D_STREAMLINE_TO_GRID_SAMPLING_1_0_FROZEN_NEW_VERSIONED_PREDICTOR_ASSEMBLY_AUTHORIZED":raise RuntimeError("AR3 not authorized")
 reg=json.loads(D14.read_text())
 # Pass 1: assemble/cache raw predictors for all cases, accumulate TRAIN only.
 acc={f:[0,0.0,0.0,float("inf"),float("-inf")] for f in FEATURES};rows=[]
 for n,c in enumerate(ALL,1):
  print(f"[{n:02d}/24] Case{c}")
  raw,meta=assemble(c,reg);rp=CASEDIR/f"V16D14B_Case_{c}_Predictors_RAW.npz"
  np.savez_compressed(rp,X_raw=raw,target_days=DAYS,feature_order=np.array(FEATURES))
  if c in TRAIN:
   for m,f in enumerate(FEATURES):
    x=raw[...,m];a=acc[f];a[0]+=x.size;a[1]+=x.sum(dtype=np.float64);a[2]+=np.square(x).sum(dtype=np.float64);a[3]=min(a[3],float(x.min()));a[4]=max(a[4],float(x.max()))
  meta["raw_sha256"]=sha(rp);(CASEDIR/f"V16D14B_Case_{c}_RAW.json").write_text(json.dumps(meta,indent=2));rows.append(meta)
 stats={}
 for f,(n,s,ss,mn,mx) in acc.items():
  mu=s/n;var=max(0.0,ss/n-mu*mu);sd=var**0.5
  stats[f]={"n":n,"mean":mu,"std":sd,"min":mn,"max":mx,"policy":"CONSTANT_IDENTITY" if sd==0 else "ZSCORE_TRAIN_ONLY"}
 st=O/"V16D14B_TRAIN_Only_Normalization_Statistics.json";st.write_text(json.dumps({"feature_order":FEATURES,"fit_cases":TRAIN,"statistics":stats},indent=2))
 # Pass 2: normalize using frozen TRAIN stats only.
 for c in ALL:
  rp=CASEDIR/f"V16D14B_Case_{c}_Predictors_RAW.npz"
  with np.load(rp,allow_pickle=False) as z:x=np.asarray(z["X_raw"],np.float64)
  xn=x.copy()
  for m,f in enumerate(FEATURES):
   q=stats[f]
   if q["std"]>0:xn[...,m]=(x[...,m]-q["mean"])/q["std"]
  npth=CASEDIR/f"V16D14B_Case_{c}_Predictors_NORMALIZED.npz";np.savez_compressed(npth,X=xn,target_days=DAYS,feature_order=np.array(FEATURES))
  if not np.isfinite(xn).all():raise RuntimeError(f"Case{c}: nonfinite normalized predictors")
 manifest={"milestone":"V16D-14B","sampling_contract_sha256":sha(CON),"normalization_stats_sha256":sha(st),"feature_order":FEATURES,
 "partitions":{"TRAIN":TRAIN,"VALIDATION":VAL,"LOCKED_OOD_TEST":TEST},"cases":[{"case_id":c,"raw_sha256":sha(CASEDIR/f"V16D14B_Case_{c}_Predictors_RAW.npz"),"normalized_sha256":sha(CASEDIR/f"V16D14B_Case_{c}_Predictors_NORMALIZED.npz")} for c in ALL]}
 mp=O/"V16D14B_24Case_Predictor_Manifest.json";mp.write_text(json.dumps(manifest,indent=2))
 gates={"AR3_summary_SHA_exact":sha(SUM)==SUMSHA,"sampling_contract_SHA_exact":sha(CON)==CONSHA,"exact_24_cases":len(ALL)==24,
 "feature_order_exact":FEATURES==["xi","pollock_tau_hat","adv_tau_hat","log10_Kh","log10_Kz_over_Kh","porosity","pressure_z","target_time_hat","target_eta_sequence"],
 "all_raw_and_normalized_exist":all((CASEDIR/f"V16D14B_Case_{c}_Predictors_RAW.npz").exists() and (CASEDIR/f"V16D14B_Case_{c}_Predictors_NORMALIZED.npz").exists() for c in ALL),
 "TRAIN_only_stats":True,"validation_transform_only":True,"OOD_transform_only":True,"no_target_Y_read":True,"M_face_not_predictor":True,"no_training":True,"no_model_selection":True}
 ok=all(gates.values());status="V16D_24CASE_C20_PREDICTOR_TENSORS_ASSEMBLED_CONTRACT1_0_TRAIN_ONLY_NORMALIZATION_STATISTICS_FROZEN" if ok else "V16D_D14B_BLOCKED"
 sm={"milestone":"V16D-14B","status":status,"normalization_stats_sha256":sha(st),"predictor_manifest_sha256":sha(mp),"gates":gates,
 "next_milestone":"V16D-15 — Multi-Foundation-Case Learning Dataset Freeze and Training Protocol Authority Contract" if ok else "V16D-14BR"}
 sp=O/"PAD_Stream_V16D14B_Summary.json";sp.write_text(json.dumps(sm,indent=2))
 print("\nTRAIN-ONLY NORMALIZATION STATISTICS")
 for f in FEATURES:print(f"  {f:24s} mean={stats[f]['mean']:.9e} std={stats[f]['std']:.9e} policy={stats[f]['policy']}")
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",sm["next_milestone"]);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
