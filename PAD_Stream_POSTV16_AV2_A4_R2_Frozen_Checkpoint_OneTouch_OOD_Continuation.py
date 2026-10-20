#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,io,json,subprocess,sys,time,zipfile
from pathlib import Path
import numpy as np

M="POSTV16-AV2-A4-R2"; PARENT="5355b9e9bbc4015762a8601251afcc6054b532f1"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
CKSHA="1c82867c53d9d3a63ee8ba9dab5ab65e9bdfaf6330fb5239954d02d7f566ef28"
PASS="AV2A4R2_FROZEN_CHECKPOINT_LOCKED_OOD_TEACHER_GENERATED_ONCE_EVALUATED_ONCE_DESCRIPTIVE_GENERALIZATION_EVIDENCE_FROZEN"
FAIL="AV2A4R2_ONE_TOUCH_OOD_CONTINUATION_SCIENTIFIC_FAIL_NO_SECOND_OOD_GENERATION_OR_EVALUATION_AUTHORIZED"
BLOCK="AV2A4R2_TECHNICAL_EXECUTION_BLOCKED"
R1STAT="AV2A4R1_OOD_METRIC_PRECISION_FAILURE_CAUSE_CLOSED_ORIGINAL_A4_FAIL_PRESERVED_OOD_TARGET_CONFIRMED_UNGENERATED"
A4="PAD_Stream_POSTV16_AV2_A4_PIRNN_Training_Checkpoint_and_OneTouch_OOD.py";A4B="b6a0fe892598a12e2b4a6ab5366d183713a91d7e"
R1="PAD_Stream_POSTV16_AV2_A4_R1_OOD_Metric_Precision_Failure_Closure.py";R1B="dddb0e7e64acae111822b7c48281f78b2864bceb"
A3="PAD_Stream_POSTV16_AV2_A3_Variable_Porosity_Teacher_Dataset_and_PIRNN_Protocol.py";A3B="9b209abc3a2abb905b9250a16344e52160e61c47"
A2="PAD_Stream_POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution.py";A2B="f141b07f0424d29a7996c089a76dbe7128af5132"
SRC={A4:A4B,R1:R1B,A3:A3B,A2:A2B}
BASE=Path("post_v16")/RID/"POSTV16_AV2_Variable_Porosity"
A2D=BASE/"POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution";A3D=BASE/"POSTV16_AV2_A3_Variable_Porosity_Teacher_Dataset_and_PIRNN_Protocol";A4D=BASE/"POSTV16_AV2_A4_PIRNN_Training_Checkpoint_and_OneTouch_OOD";R1D=BASE/"POSTV16_AV2_A4_R1_OOD_Metric_Precision_Failure_Closure"
OUT=BASE/"POSTV16_AV2_A4_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation";FD=BASE/"POSTV16_AV2_A4_R2_SCIENTIFIC_FAIL";BD=BASE/"POSTV16_AV2_A4_R2_BLOCKED"
DAYS=np.array([30,60,100,150,250,365,500,750,1000.],float);BATCH=64

class G(RuntimeError):pass
class S(RuntimeError):
 def __init__(self,g,d=None):super().__init__(g);self.g=g;self.d=d
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def git(r,*a):return subprocess.run(["git","-C",str(r),*a],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.strip()
def blob(p,r):return git(r,"hash-object",str(p))
def j(p):return json.loads(Path(p).read_text())
def rows(p):
 with open(p,newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def man(d,n):
 m={x["file"]:x["sha256"] for x in rows(d/n)}
 for f,e in m.items():
  q=d/f
  if not q.is_file() or sha(q)!=e:raise G("manifest:"+f)
 return m
def loadmod(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
def jb(x):return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()
def cb(rr):
 rr=list(rr);ks=[]
 for r in rr:
  for k in r:
   if k not in ks:ks.append(k)
 s=io.StringIO();w=csv.DictWriter(s,fieldnames=ks,lineterminator="\n");w.writeheader();w.writerows(rr);return s.getvalue().encode()
def npzb(a):
 o=io.BytesIO()
 with zipfile.ZipFile(o,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for k in sorted(a):
   b=io.BytesIO();np.save(b,np.asarray(a[k]),allow_pickle=False);i=zipfile.ZipInfo(k+".npy",(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,b.getvalue())
 return o.getvalue()
def pub(d,fs):
 d.mkdir(parents=True,exist_ok=True)
 for n,b in fs.items():
  p=d/n
  if p.exists() and p.read_bytes()!=b:raise G("existing:"+n)
  if not p.exists():p.write_bytes(b)
def met(P,T):
 E=np.asarray(P,float)-np.asarray(T,float);m=float(np.mean(E*E));P=np.asarray(P,float)
 return dict(mse=m,rmse=float(np.sqrt(m)),mae=float(np.mean(abs(E))),max_abs_error=float(np.max(abs(E))),prediction_min=float(P.min()),prediction_max=float(P.max()))
def pair(ids,ri,sl,ti):
 A=[];B=[];ids=np.asarray(ids,int)
 for r in np.unique(ri[ids]):
  rr=ids[ri[ids]==r]
  for g in np.unique(sl[rr]):
   q=rr[sl[rr]==g];q=q[np.argsort(ti[q])]
   for a,b in zip(q[:-1],q[1:]):A.append(a);B.append(b)
 return np.array(A,int),np.array(B,int)
def selftest():
 ri=np.repeat(3,9702);sl=np.tile(np.arange(1078),9);ti=np.repeat(np.arange(9),1078);a,b=pair(np.arange(9702),ri,sl,ti);assert len(a)==8624 and np.all(ti[b]-ti[a]==1);print("POSTV16-AV2-A4-R2 frozen-checkpoint OOD continuation self-test: PASS")

def main(root,drive):
 import tensorflow as tf
 gates={};stage="preflight";started=done=evaluated=False;out=drive/OUT;marker=out/"POSTV16_AV2_A4_R2_OOD_GENERATION_STARTED.marker"
 def g(n,v,val=None):
  ok=bool(v);gates[n]={"passed":ok,"value":val};print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f" — {val}" if val is not None else ""))
  if not ok:raise G(n)
 def sg(n,v,val=None):
  ok=bool(v);gates[n]={"passed":ok,"value":val,"scientific_execution_gate":True};print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f" — {val}" if val is not None else ""))
  if not ok:raise S(n,val)
 print("="*180);print("POSTV16-AV2-A4-R2 — FROZEN-CHECKPOINT ONE-TOUCH LOCKED-OOD CONTINUATION");print("="*180);print("NO TRAINING. NO RESELECTION. NO NORMALIZATION REFIT. NO MAPBACK. NO CMG.")
 try:
  root=root.resolve();drive=drive.resolve();g("repository_parent_is_A4R1",git(root,"rev-parse","HEAD^")==PARENT,git(root,"rev-parse","HEAD^"));g("repository_clean",git(root,"status","--porcelain")=="")
  for f,e in SRC.items():g(Path(f).stem+"_blob_exact",blob(root/f,root)==e,blob(root/f,root))
  g("no_prior_R2_marker",not marker.exists(),str(marker))
  a2=drive/A2D;a3=drive/A3D;a4=drive/A4D;r1=drive/R1D
  m2=man(a2,"POSTV16_AV2_A2_Artifact_Manifest.csv");m3=man(a3,"POSTV16_AV2_A3_Artifact_Manifest.csv");mr=man(r1,"POSTV16_AV2_A4_R1_Artifact_Manifest.csv");g("manifest_closure",True,(len(m2),len(m3),len(mr)))
  rs=j(r1/"PAD_Stream_POSTV16_AV2_A4_R1_Summary.json");rr=j(r1/"POSTV16_AV2_A4_R1_Precision_Root_Cause_Audit.json");re=j(r1/"POSTV16_AV2_A4_R1_OOD_Exposure_State.json");rc=j(r1/"POSTV16_AV2_A4_R1_Frozen_Continuation_Contract.json")
  g("R1_status",rs["status"]==R1STAT,rs["status"]);g("R1_precision_root_cause",rr["precision_demotion_root_cause_supported"] is True);g("R1_no_physical_metric_mismatch",rr["physical_metric_mismatch_supported"] is False);g("R1_OOD_unobserved",re["OOD_Y_transport_generated"] is False and re["OOD_model_evaluated"] is False);g("R1_R2_authorized",rc["A4_R2_continuation_authorized"] is True);g("R1_retraining_prohibited",rc["retraining_authorized"] is False);g("R1_checkpoint_exact",rc["required_checkpoint_sha256"]==CKSHA)
  ck=a4/"POSTV16_AV2_A4_Best_Validation_Model.keras";fz=j(a4/"POSTV16_AV2_A4_Best_Validation_Checkpoint_Freeze.json");g("checkpoint_SHA",sha(ck)==CKSHA,sha(ck));g("best_epoch_198",fz["best_epoch"]==198);vm=fz["frozen_checkpoint_validation_predictive_metrics"];vo=fz["frozen_checkpoint_validation_objective"]
  ox=a3/"POSTV16_AV2_A3_LockedOOD_Predictor_Only_Dataset.npz";ph=a3/"POSTV16_AV2_A3_Variable_Porosity_Physics_Sidecar.npz";oa=a2/"POSTV16_AV2_A2_AV2PHI0004_Variable_Porosity_Pore_Kinematics.npz"
  with np.load(ox,allow_pickle=False) as z:
   g("OOD_Y_absent","Y_transport" not in z.files);X=np.asarray(z["X_required_9"],np.float32);ri=np.asarray(z["realization_index"],int);ti=np.asarray(z["time_index"],int);sl=np.asarray(z["streamline_index"],int);eta=np.asarray(z["target_eta_sequence"],np.float32);days=np.asarray(z["target_time_days"],float)
  with np.load(ph,allow_pickle=False) as z:Mall=np.asarray(z["metric_M"]);Phi=np.asarray(z["porosity_sequence"])
  with np.load(oa,allow_pickle=False) as z:xyz=np.asarray(z["streamline_xyz_m"],float);tof=np.asarray(z["pollock_tof_s"],float)
  g("native_sidecar_float64",Mall.dtype==np.float64 and Phi.dtype==np.float64,(str(Mall.dtype),str(Phi.dtype)))
  a3m=loadmod(root/A3,"av2a4r2_a3");op=a3m.build_operator_geometry(xyz,tof);M64=np.asarray(Mall[3],float);phi=np.asarray(Phi[3],float);d=float(np.max(abs(np.asarray(op["metric_M"],float)-M64)));sg("native_metric_exact",np.allclose(op["metric_M"],M64,rtol=1e-12,atol=1e-12),d)
  out.mkdir(parents=True,exist_ok=True);marker.write_text(f"POSTV16-AV2-A4-R2 OOD GENERATION STARTED\ncheckpoint_sha256={CKSHA}\ntraining=false\n");started=True;sg("R2_marker_written",marker.is_file())
  t0=time.time();Y3,td=a3m.generate_teacher(phi,op,DAYS);done=True;sg("OOD_teacher_certified",a3m.teacher_diag_pass(td),td);sg("OOD_Y_shape",Y3.shape==(9,1078,201),Y3.shape);Y=Y3.reshape(9702,201).astype(float)
  model=tf.keras.models.load_model(ck);P=model.predict(X,batch_size=BATCH,verbose=0).astype(float);evaluated=True;sg("OOD_predictions_finite",np.isfinite(P).all());sg("OOD_predictions_bounded",P.min()>=.2-1e-6 and P.max()<=.8+1e-6,[float(P.min()),float(P.max())]);om=met(P,Y)
  a,b=pair(np.arange(len(X)),ri,sl,ti);sg("OOD_pairs_8624",len(a)==8624,len(a))
  def fw(S):se=tf.clip_by_value((S-.2)/.6,0.,1.);krw=.8*se**2;kro=.8*(1-se)**2;return (krw/.5)/(krw/.5+kro/5+1e-12)
  def ds(S):se=tf.clip_by_value((S-.2)/.6,1e-7,1-1e-7);return (se*(1-se))**2/.0625
  def pl(Sa,Sb,ea,eb,Mm,pp):
   Sm=.5*(Sa+Sb);de=tf.maximum(eb-ea,1e-8);dt=(Sb-Sa)/de[:,None];h=1/200;adv=(fw(Sm)[:,2:]-fw(Sm)[:,:-2])/(2*h);dS=(Sm[:,1:]-Sm[:,:-1])/h;Mf=2*Mm[:,:-1]*Mm[:,1:]/tf.maximum(Mm[:,:-1]+Mm[:,1:],1e-12);G=ds(.5*(Sm[:,:-1]+Sm[:,1:]))*Mf*dS;cap=Mm[:,1:-1]*(G[:,1:]-G[:,:-1])/h;R=dt[:,1:-1]+adv-(pp[:,1:-1]/22)*cap;return tf.reduce_mean(tf.square(R))
  Mt=tf.constant(M64,tf.float32);Pt=tf.constant(phi,tf.float32);vals=[]
  for st in range(0,len(a),BATCH):
   aa=a[st:st+BATCH];bb=b[st:st+BATCH];vals.append(float(pl(tf.constant(P[aa],tf.float32),tf.constant(P[bb],tf.float32),tf.reduce_mean(eta[aa],1),tf.reduce_mean(eta[bb],1),tf.gather(Mt,sl[aa]),tf.gather(Pt,sl[aa]))))
  ophys=float(np.mean(vals));by=[{"target_day":float(dd),**met(P[np.isclose(days,dd)],Y[np.isclose(days,dd)])} for dd in DAYS]
  gen={"validation":vm,"validation_objective":vo,"locked_OOD":om,"OOD_to_validation_RMSE_ratio":om["rmse"]/max(float(vm["rmse"]),1e-300),"OOD_to_validation_MAE_ratio":om["mae"]/max(float(vm["mae"]),1e-300),"locked_OOD_physics_residual_MSE":ophys,"teacher_elapsed_seconds":float(time.time()-t0),"scientific_rule":"Descriptive one-touch OOD evidence only; no post-hoc accuracy threshold or retuning."}
  dec={"milestone":M,"status":PASS,"checkpoint_sha256":CKSHA,"training_performed_in_R2":False,"checkpoint_reselected":False,"normalization_refit":False,"locked_OOD_teacher_generated_once":True,"locked_OOD_evaluated_once":True,"OOD_accuracy_threshold_gate":False,"post_OOD_retuning":False,"variable_phi_predictive_generalization_claim":False,"mapback_performed":False,"CMG_validation_performed":False,"A5_integration_authorized":True,"next":{"milestone":"POSTV16-AV2-A5","authorized":True,"name":"Frozen AV2 Checkpoint Deployment, Local-Pore-Volume Capacity Integration, and R7D Terminal-Halo Reconstruction"}}
  summ={"milestone":M,"status":PASS,"checkpoint_sha256":CKSHA,"best_epoch":198,"epochs_completed":207,"validation_metrics":vm,"locked_OOD_teacher_certified":True,"locked_OOD_teacher_diagnostics":td,"locked_OOD_metrics":om,"locked_OOD_physics_residual_MSE":ophys,"OOD_accuracy_gate_applied":False,"training_in_R2":False,"retuning_after_OOD":False,"mapback":False,"CMG_validation":False,"next":dec["next"]}
  pub(out,{"PAD_Stream_POSTV16_AV2_A4_R2_Summary.json":jb(summ),"POSTV16_AV2_A4_R2_LockedOOD_Truth_and_Predictions.npz":npzb({"Y_true":Y,"Y_pred":P,"target_time_days":days,"time_index":ti,"streamline_index":sl,"realization_index":ri,"checkpoint_sha256":np.asarray(CKSHA)}),"POSTV16_AV2_A4_R2_LockedOOD_Predictive_Metrics_By_Time.csv":cb(by),"POSTV16_AV2_A4_R2_LockedOOD_Generalization_Evidence.json":jb(gen),"POSTV16_AV2_A4_R2_Decision_Contract.json":jb(dec),"POSTV16_AV2_A4_R2_Final_Gate_Matrix.csv":cb([{"gate":k,**v} for k,v in gates.items()])})
  manifest=[{"file":q.name,"sha256":sha(q),"bytes":q.stat().st_size} for q in sorted(out.iterdir()) if q.is_file() and q.name!="POSTV16_AV2_A4_R2_Artifact_Manifest.csv"];pub(out,{"POSTV16_AV2_A4_R2_Artifact_Manifest.csv":cb(manifest)})
  print("\nPOSTV16-AV2-A4-R2: PASS");print("OOD RMSE / MAE:",om["rmse"],om["mae"]);print("OOD/validation RMSE ratio:",gen["OOD_to_validation_RMSE_ratio"]);print("A5 authorized: True");return 0
 except S as e:
  q=drive/FD;q.mkdir(parents=True,exist_ok=True);r={"milestone":M,"status":FAIL,"failed_stage":stage,"failed_gate":e.g,"detail":e.d,"gates":gates,"teacher_generation_started":started,"teacher_generation_completed":done,"locked_OOD_evaluated":evaluated,"second_OOD_generation_authorized":False,"second_OOD_evaluation_authorized":False,"retraining_authorized":False,"A5_authorized":False};(q/"POSTV16_AV2_A4_R2_Scientific_Fail_Report.json").write_bytes(jb(r));print("POSTV16-AV2-A4-R2: SCIENTIFIC FAIL",e.g);return 3
 except Exception as e:
  q=drive/BD;q.mkdir(parents=True,exist_ok=True);r={"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(e),"gates":gates,"teacher_generation_started":started,"teacher_generation_completed":done,"locked_OOD_evaluated":evaluated,"second_OOD_generation_authorized":False,"second_OOD_evaluation_authorized":False,"retraining_authorized":False,"A5_authorized":False};(q/"POSTV16_AV2_A4_R2_Blocked_Report.json").write_bytes(jb(r));print("POSTV16-AV2-A4-R2: BLOCKED",stage,repr(e));return 2

def parse():
 p=argparse.ArgumentParser();p.add_argument("--project-root",type=Path,default=Path("."));p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"));p.add_argument("--self-test",action="store_true");return p.parse_args()
if __name__=="__main__":
 a=parse()
 if a.self_test:selftest();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
