#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,io,json,subprocess,sys
from pathlib import Path
import numpy as np

MILESTONE='POSTV16-AV2-A4-R1'
STATUS='AV2A4R1_OOD_METRIC_PRECISION_FAILURE_CAUSE_CLOSED_ORIGINAL_A4_FAIL_PRESERVED_OOD_TARGET_CONFIRMED_UNGENERATED'
BLOCKED='AV2A4R1_FAILURE_CLOSURE_BLOCKED'
RID='PAD_STREAM_V16_RC1_B92D52088D01078A'
PARENT='21d7e2d2114b6c04a16407ce785b860aabd8df21'
A4='PAD_Stream_POSTV16_AV2_A4_PIRNN_Training_Checkpoint_and_OneTouch_OOD.py';A4_BLOB='b6a0fe892598a12e2b4a6ab5366d183713a91d7e'
A3='PAD_Stream_POSTV16_AV2_A3_Variable_Porosity_Teacher_Dataset_and_PIRNN_Protocol.py';A3_BLOB='9b209abc3a2abb905b9250a16344e52160e61c47'
A2='PAD_Stream_POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution.py';A2_BLOB='f141b07f0424d29a7996c089a76dbe7128af5132'
BASE=Path('post_v16')/RID/'POSTV16_AV2_Variable_Porosity'
A2REL=BASE/'POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution'
A3REL=BASE/'POSTV16_AV2_A3_Variable_Porosity_Teacher_Dataset_and_PIRNN_Protocol'
A4REL=BASE/'POSTV16_AV2_A4_PIRNN_Training_Checkpoint_and_OneTouch_OOD'
FAILREL=BASE/'POSTV16_AV2_A4_SCIENTIFIC_FAIL'
OUTREL=BASE/'POSTV16_AV2_A4_R1_OOD_Metric_Precision_Failure_Closure'
BLKREL=BASE/'POSTV16_AV2_A4_R1_BLOCKED'
A2MAN='POSTV16_AV2_A2_Artifact_Manifest.csv';A2OOD='POSTV16_AV2_A2_AV2PHI0004_Variable_Porosity_Pore_Kinematics.npz'
A3MAN='POSTV16_AV2_A3_Artifact_Manifest.csv';A3PH='POSTV16_AV2_A3_Variable_Porosity_Physics_Sidecar.npz'
CHECKPOINT='POSTV16_AV2_A4_Best_Validation_Model.keras';CKFREEZE='POSTV16_AV2_A4_Best_Validation_Checkpoint_Freeze.json';HISTORY='POSTV16_AV2_A4_Training_History.csv';VALPRED='POSTV16_AV2_A4_Validation_Predictions_Before_OOD.npz';MARKER='POSTV16_AV2_A4_LOCKED_OOD_OPENED.marker';FAILREPORT='POSTV16_AV2_A4_Scientific_Fail_Report.json'
FAILSTATUS='AV2A4_VARIABLE_POROSITY_PIRNN_TRAINING_OR_ONE_TOUCH_OOD_SCIENTIFIC_FAIL_NO_RETUNING_OR_REEVALUATION_AUTHORIZED'
FAILDETAIL=4.734486385160608e-07
CKSHA='1c82867c53d9d3a63ee8ba9dab5ab65e9bdfaf6330fb5239954d02d7f566ef28'
BEST_EPOCH=198;EPOCHS=207;BEST_VAL=0.00014610096372457014
class GateError(RuntimeError):pass

def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def git(root,*a):return subprocess.run(['git','-C',str(root),*a],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.strip()
def blob(p,root):return git(root,'hash-object',str(p))
def lj(p):return json.loads(p.read_text())
def rcsv(p):
 with p.open('r',newline='') as f:return list(csv.DictReader(f))
def vman(d,n):
 m={r['file']:r['sha256'] for r in rcsv(d/n)}
 if not m:raise GateError('manifest_empty')
 for fn,e in m.items():
  q=d/fn
  if not q.is_file() or sha(q)!=e:raise GateError('manifest:'+fn)
 return m
def mod(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
def jb(o):return (json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def cb(rows):
 rows=list(rows);ks=[]
 for r in rows:
  for k in r:
   if k not in ks:ks.append(k)
 s=io.StringIO();w=csv.DictWriter(s,fieldnames=ks,lineterminator='\n');w.writeheader();w.writerows(rows);return s.getvalue().encode()
def pub(d,files):
 d.mkdir(parents=True,exist_ok=True)
 for n,b in files.items():
  p=d/n
  if p.exists() and p.read_bytes()!=b:raise GateError('existing_output_differs:'+n)
  if not p.exists():p.write_bytes(b)

def self_test():
 x=np.array([1.234567890123,3.987654321987],float);y=x.astype(np.float32).astype(float)
 assert np.allclose(x,x,rtol=1e-12,atol=1e-12) and not np.allclose(x,y,rtol=1e-12,atol=1e-12)
 print('POSTV16-AV2-A4-R1 precision-failure closure self-test: PASS')

def main(root,drive):
 gates={};stage='preflight';out=drive/OUTREL;blk=drive/BLKREL
 def gate(n,v,val=None):
  ok=bool(v);gates[n]={'passed':ok,'value':val};print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f' — {val}' if val is not None else ''))
  if not ok:raise GateError(n)
 try:
  root=root.resolve();drive=drive.resolve();gate('repository_parent_is_failed_A4',git(root,'rev-parse','HEAD^')==PARENT,git(root,'rev-parse','HEAD^'));gate('repository_clean',git(root,'status','--porcelain')=='',repr(git(root,'status','--porcelain')))
  for fn,e in {A4:A4_BLOB,A3:A3_BLOB,A2:A2_BLOB}.items():
   p=root/fn;a=blob(p,root) if p.is_file() else 'missing';gate(Path(fn).stem+'_git_blob_exact',a==e,a)
  a2=drive/A2REL;a3=drive/A3REL;a4=drive/A4REL;fd=drive/FAILREL
  for n,d in [('A2',a2),('A3',a3),('A4_partial',a4),('A4_fail',fd)]:gate(n+'_present',d.is_dir(),str(d))
  m2=vman(a2,A2MAN);m3=vman(a3,A3MAN);gate('A2_manifest_SHA_closure',True,len(m2));gate('A3_manifest_SHA_closure',True,len(m3))
  stage='failed_A4_binding';fr=lj(fd/FAILREPORT)
  gate('A4_fail_status_exact',fr['status']==FAILSTATUS,fr['status']);gate('A4_failed_gate_exact',fr['failed_gate']=='OOD_metric_matches_A3_sidecar',fr['failed_gate']);gate('A4_failed_stage_exact',fr['failed_stage']=='OOD_teacher',fr['failed_stage']);gate('A4_failure_detail_exact',abs(float(fr['detail'])-FAILDETAIL)<=1e-15,float(fr['detail']))
  gate('A4_checkpoint_frozen',fr['checkpoint_frozen'] is True);gate('A4_marker_recorded',fr['LOCKED_OOD_opened'] is True);gate('A4_OOD_teacher_not_generated',fr['LOCKED_OOD_teacher_generated'] is False);gate('A4_OOD_not_evaluated',fr['LOCKED_OOD_evaluated'] is False);gate('A4_next_not_authorized',fr['next_milestone_authorized'] is False)
  stage='checkpoint_binding';ck=a4/CHECKPOINT;cf=a4/CKFREEZE;mk=a4/MARKER
  for q in [ck,cf,a4/HISTORY,a4/VALPRED,mk]:gate('present_'+q.name,q.is_file(),str(q))
  fz=lj(cf);csha=sha(ck);gate('checkpoint_SHA_exact',csha==CKSHA,csha);gate('freeze_SHA_agrees',fz['checkpoint_sha256']==csha,fz['checkpoint_sha256']);gate('best_epoch_exact',int(fz['best_epoch'])==BEST_EPOCH,int(fz['best_epoch']));gate('epochs_exact',int(fz['epochs_completed'])==EPOCHS,int(fz['epochs_completed']));gate('best_validation_total_exact',abs(float(fz['best_validation_total_objective_during_training'])-BEST_VAL)<=1e-15,float(fz['best_validation_total_objective_during_training']));gate('freeze_OOD_target_false',fz['LOCKED_OOD_target_generated_at_freeze_time'] is False);gate('freeze_OOD_open_false',fz['LOCKED_OOD_target_opened_at_freeze_time'] is False)
  stage='exposure_audit'
  for n in ['POSTV16_AV2_A4_LockedOOD_Truth_and_Predictions.npz','POSTV16_AV2_A4_LockedOOD_Predictive_Metrics_By_Time.csv','POSTV16_AV2_A4_LockedOOD_Generalization_Evidence.json','PAD_Stream_POSTV16_AV2_A4_Summary.json','POSTV16_AV2_A4_Decision_Contract.json','POSTV16_AV2_A4_Artifact_Manifest.csv']:gate('absent_'+Path(n).stem,not (a4/n).exists(),n)
  stage='precision_root_cause';ph=a3/A3PH;oo=a2/A2OOD;gate('A3_physics_sidecar_manifested',A3PH in m3 and sha(ph)==m3[A3PH]);gate('A2_OOD_manifested',A2OOD in m2 and sha(oo)==m2[A2OOD])
  with np.load(ph,allow_pickle=False) as z:Mn=np.asarray(z['metric_M']);Pn=np.asarray(z['porosity_sequence'])
  gate('A3_metric_native_float64',Mn.dtype==np.float64,str(Mn.dtype));gate('A3_phi_native_float64',Pn.dtype==np.float64,str(Pn.dtype))
  with np.load(oo,allow_pickle=False) as z:xyz=np.asarray(z['streamline_xyz_m'],float);tof=np.asarray(z['pollock_tof_s'],float)
  Mr=np.asarray(mod(root/A3,'av2a4r1_a3').build_operator_geometry(xyz,tof)['metric_M'],float);M64=np.asarray(Mn[3],float);M32=np.asarray(Mn[3],np.float32).astype(float)
  d64=float(np.max(np.abs(Mr-M64)));d32=float(np.max(np.abs(Mr-M32)));c64=bool(np.allclose(Mr,M64,rtol=1e-12,atol=1e-12));c32=bool(np.allclose(Mr,M32,rtol=1e-12,atol=1e-12))
  gate('native_float64_metric_matches',c64,d64);gate('float32_demotion_fails_original_gate',not c32,d32);gate('float32_demotion_reproduces_A4_detail',abs(d32-FAILDETAIL)<=1e-15,{'reproduced':d32,'A4':FAILDETAIL})
  rootcause={'original_A4_fail_preserved':True,'diagnosis':'A3 metric_M is float64; A4 loaded it as float32 and reused the demoted copy in a 1e-12 integrity check against a freshly recomputed float64 metric. Native float64 matches; float32 demotion reproduces the failure.','native_float64_max_abs_difference':d64,'float32_roundtrip_max_abs_difference':d32,'physical_metric_mismatch_supported':False,'precision_demotion_root_cause_supported':True}
  exposure={'marker_exists':True,'marker_semantics':'Marker was written before the failed metric gate; it records entry into the OOD continuation boundary, not actual Y_transport generation.','checkpoint_frozen_before_marker':True,'OOD_Y_transport_generated':False,'OOD_model_evaluated':False,'OOD_predictive_result_observed':False,'original_A4_rerun_authorized':False}
  cont={'original_A4_rerun_authorized':False,'retraining_authorized':False,'checkpoint_reselection_authorized':False,'normalization_refit_authorized':False,'A4_R2_continuation_authorized':True,'required_checkpoint_sha256':csha,'R2_rules':['Load exact frozen checkpoint; no training.','Use native float64 A3 metric_M/porosity_sequence for integrity and teacher operations.','Verify native metric before teacher generation.','Generate AV2PHI0004 Y exactly once.','Evaluate frozen checkpoint exactly once.','No retuning, reselection, normalization refit, mapback, or CMG.'],'A5_authorized_now':False,'next':{'milestone':'POSTV16-AV2-A4-R2','authorized':True}}
  summ={'milestone':MILESTONE,'status':STATUS,'original_A4_fail_preserved':True,'checkpoint_sha256':csha,'best_epoch':BEST_EPOCH,'epochs_completed':EPOCHS,'best_validation_total_objective':BEST_VAL,'native_float64_metric_match':True,'float32_demotion_reproduces_A4_failure':True,'LOCKED_OOD_Y_generated':False,'LOCKED_OOD_evaluated':False,'A4_rerun_authorized':False,'A4_R2_continuation_authorized':True,'A5_authorized':False,'next':cont['next']}
  pub(out,{'PAD_Stream_POSTV16_AV2_A4_R1_Summary.json':jb(summ),'POSTV16_AV2_A4_R1_Precision_Root_Cause_Audit.json':jb(rootcause),'POSTV16_AV2_A4_R1_OOD_Exposure_State.json':jb(exposure),'POSTV16_AV2_A4_R1_Frozen_Continuation_Contract.json':jb(cont),'POSTV16_AV2_A4_R1_Metric_Precision_Comparison.csv':cb([{'comparison':'native_float64','max_abs_difference':d64,'allclose_1e12':c64},{'comparison':'A4_float32_roundtrip','max_abs_difference':d32,'allclose_1e12':c32}]),'POSTV16_AV2_A4_R1_Final_Gate_Matrix.csv':cb([dict(gate=k,**v) for k,v in gates.items()])})
  mr=[]
  for q in sorted(out.iterdir()):
   if q.is_file() and q.name!='POSTV16_AV2_A4_R1_Artifact_Manifest.csv':mr.append({'file':q.name,'sha256':sha(q),'bytes':q.stat().st_size})
  pub(out,{'POSTV16_AV2_A4_R1_Artifact_Manifest.csv':cb(mr)})
  print('\nPOSTV16-AV2-A4-R1: PASS');print('Original A4 FAIL preserved: True');print('Checkpoint SHA256:',csha);print('Native float64 max diff:',d64);print('A4 float32-roundtrip max diff:',d32);print('OOD Y generated/evaluated: False/False');print('A4 rerun: False');print('A4-R2 continuation: True');print('A5 now: False');return 0
 except Exception as e:
  blk.mkdir(parents=True,exist_ok=True);q=blk/'POSTV16_AV2_A4_R1_Blocked_Report.json';q.write_bytes(jb({'milestone':MILESTONE,'status':BLOCKED,'failed_stage':stage,'exception':repr(e),'gates':gates,'A4_rerun_authorized':False,'A4_R2_authorized':False,'A5_authorized':False})) if not q.exists() else None;print('POSTV16-AV2-A4-R1: BLOCKED',stage,repr(e));return 2

def parse():
 p=argparse.ArgumentParser();p.add_argument('--project-root',type=Path,default=Path('.'));p.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'));p.add_argument('--self-test',action='store_true');return p.parse_args()
if __name__=='__main__':
 a=parse()
 if a.self_test:self_test();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
