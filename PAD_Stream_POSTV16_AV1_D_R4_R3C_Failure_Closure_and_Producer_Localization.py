#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, io, json, subprocess
from pathlib import Path
from typing import Any
import numpy as np

MILESTONE='POSTV16-AV1-D-R4'
STATUS_PASS='AV1DR4_R3C_FINAL_FAIL_CLOSED_PROD_SW_DAY30_PRODUCER_EVENT_MISMATCH_LOCALIZED_GEOLOGY0030_CONSUMED_NO_RETEST_AUTHORIZED'
STATUS_BLOCKED='AV1DR4_R3C_FAILURE_CLOSURE_TECHNICALLY_BLOCKED'
RID='PAD_STREAM_V16_RC1_B92D52088D01078A'
PARENT_R3C_COMMIT='3d3b6af3e985e5ff147fbe35f30f0a1383da42b0'

SOURCE_BLOBS={
 'PAD_Stream_POSTV16_AV1_D_R3C_One_Touch_Final_Geology0030_Acceptance.py':'578accd65e5abd6f40e8c898c9bd79b43008d7d9',
 'PAD_Stream_POSTV16_AV1_D_R3B_Frozen_TrainValidation_Outlet_Response_Repair_Execution.py':'787fe69e6631a1d294c17e791ab82aa4ab963c10',
 'PAD_Stream_POSTV16_AV1_D_R3_R1_Threshold_Schema_Binding_Repair_and_Prospective_Freeze.py':'9d8c5b47b33e69e641df28ab130fddf401a11492',
}
R3C_REL=Path('post_v16')/RID/'POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi'/'POSTV16_AV1_D_R3C_One_Touch_Final_Geology0030_Acceptance'
R3C_MANIFEST='POSTV16_AV1_D_R3C_Artifact_Manifest.csv'
R3C_SUMMARY='PAD_Stream_POSTV16_AV1_D_R3C_Summary.json'
R3C_DECISION='POSTV16_AV1_D_R3C_Final_Decision.json'
R3C_AGG='POSTV16_AV1_D_R3C_Aggregate_Event_Audit.csv'
R3C_PROD='POSTV16_AV1_D_R3C_Producer_Event_Audit.csv'
R3C_GATES='POSTV16_AV1_D_R3C_Final_Gate_Matrix.csv'
R3C_FAIL_STATUS='AV1DR3C_ONE_TOUCH_GEOLOGY0030_FINAL_EVENT_ACCEPTANCE_FAIL_NO_ADAPTATION_OR_RETEST_AUTHORIZED'
SELECTED_ID='R3B_RESPONSE'
SELECTED_SHA='8207f17f35c354a3396525ed3ba8de88c923f7b55351f7cc58a9000268a26364'
CONDITIONING_SHA='f0ce016d5f1f25df2a4932a16d35de93366de76fbf09868e0fc029f6ec683fc5'
TRUTH_SHA='bef8c3875ab30a561f1cb9f6d16c1816691394b13e2ddb6ea384d44d40f6109c'
THRESHOLD=1.0e-4
EXPECTED_DAYS=[30.,60.,100.,150.,250.,365.,500.,750.,1000.]
EXPECTED_PRODUCERS=['PROD_NE','PROD_NW','PROD_SE','PROD_SW']
OUT_REL=Path('post_v16')/RID/'POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi'/'POSTV16_AV1_D_R4_R3C_Failure_Closure_and_Producer_Localization'
BLOCKED_REL=Path('post_v16')/RID/'POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi'/'POSTV16_AV1_D_R4_BLOCKED'

class GateError(RuntimeError): pass

def sha256_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def git_text(root:Path,*args:str)->str:
 p=subprocess.run(['git','-C',str(root),*args],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 return p.stdout.strip()

def git_blob_sha(p:Path,root:Path)->str: return git_text(root,'hash-object',str(p))
def load_json(p:Path): return json.loads(p.read_text(encoding='utf-8'))
def read_csv(p:Path):
 with p.open('r',newline='',encoding='utf-8') as f: return list(csv.DictReader(f))
def parse_bool(x:Any)->bool:
 if isinstance(x,bool): return x
 s=str(x).strip().lower()
 if s in {'true','1','yes'}: return True
 if s in {'false','0','no'}: return False
 raise GateError(f'invalid_boolean:{x}')
def verify_manifest(d:Path,name:str):
 rows=read_csv(d/name); m={r['file']:r['sha256'] for r in rows}
 for fn,e in m.items():
  p=d/fn
  if not p.is_file(): raise GateError(f'manifest_file_missing:{fn}')
  a=sha256_file(p)
  if a!=e: raise GateError(f'manifest_SHA_mismatch:{fn}:{a}:{e}')
 return m

def json_bytes(x): return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def csv_bytes(rows):
 if not rows:return b''
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields:fields.append(k)
 s=io.StringIO(newline=''); w=csv.DictWriter(s,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows)
 return s.getvalue().encode()
def immutable_publish(out:Path,files):
 out.mkdir(parents=True,exist_ok=True)
 for n,d in files.items():
  p=out/n
  if p.exists() and p.read_bytes()!=d: raise GateError(f'existing_output_differs:{n}')
  if not p.exists(): p.write_bytes(d)
def basic_error_metrics(rows):
 e=np.asarray([float(r['prediction_CO2_cut'])-float(r['truth_CO2_cut']) for r in rows],dtype=float)
 return {'count':int(len(e)),'bias':float(np.mean(e)),'mae':float(np.mean(np.abs(e))),'rmse':float(np.sqrt(np.mean(e*e))),'max_abs':float(np.max(np.abs(e)))}

def self_test():
 r={'truth_CO2_cut':8e-5,'prediction_CO2_cut':1.2e-4,'classification_match':False,'producer':'PROD_SW','target_day':30.0}
 if parse_bool(r['classification_match']): raise RuntimeError('bool')
 if abs((THRESHOLD-r['truth_CO2_cut'])-2e-5)>1e-15: raise RuntimeError('truth_margin')
 if abs((r['prediction_CO2_cut']-THRESHOLD)-2e-5)>1e-15: raise RuntimeError('pred_margin')
 print('POSTV16-AV1-D-R4 self-test: PASS')

def main(root:Path,drive:Path)->int:
 gates={};stage='preflight';out=drive/OUT_REL;blocked=drive/BLOCKED_REL
 def gate(n,p,v=None):
  ok=bool(p);gates[n]={'passed':ok,'value':v};print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f' — {v}' if v is not None else ''))
  if not ok: raise GateError(n)
 print('='*168);print('POSTV16-AV1-D-R4 — R3C FINAL-FAILURE CLOSURE + PRODUCER-LEVEL LOCALIZATION');print('='*168)
 print('DIAGNOSTIC ONLY. NO MODEL INFERENCE. NO TARGET ARRAY OPENING. NO TRAINING/RETUNING.')
 print('NO THRESHOLD CHANGE. NO ALTERNATE CANDIDATE. NO GEOLOGY0030 RETEST.\n')
 try:
  root=root.resolve();drive=drive.resolve();head=git_text(root,'rev-parse','HEAD');parent=git_text(root,'rev-parse','HEAD^');status=git_text(root,'status','--porcelain')
  gate('repository_parent_is_R3C_commit',parent==PARENT_R3C_COMMIT,parent);gate('repository_clean',status=='',repr(status))
  for fn,blob in SOURCE_BLOBS.items():
   p=root/fn;a=git_blob_sha(p,root) if p.is_file() else 'missing';gate(f'{Path(fn).stem}_git_blob_exact',a==blob,a)
  stage='R3C_final_decision_binding';r3c=drive/R3C_REL;gate('R3C_output_present',r3c.is_dir(),str(r3c));manifest=verify_manifest(r3c,R3C_MANIFEST);gate('R3C_manifest_SHA_closure',True,len(manifest))
  for fn in [R3C_SUMMARY,R3C_DECISION,R3C_AGG,R3C_PROD,R3C_GATES]: gate(f'{Path(fn).stem}_present',(r3c/fn).is_file(),str(r3c/fn))
  summary=load_json(r3c/R3C_SUMMARY);decision=load_json(r3c/R3C_DECISION);agg_raw=read_csv(r3c/R3C_AGG);prod_raw=read_csv(r3c/R3C_PROD)
  gate('R3C_status_exact_final_FAIL',decision['status']==R3C_FAIL_STATUS,decision['status']);gate('R3C_final_acceptance_false',decision['final_acceptance_pass'] is False);gate('R3C_structural_acceptance_true',decision['structural_acceptance_pass'] is True);gate('R3C_primary_event_acceptance_false',decision['primary_event_acceptance_pass'] is False)
  gate('R3C_selected_candidate_exact',decision['selected_candidate']==SELECTED_ID);gate('R3C_selected_SHA_exact',decision['selected_weights_sha256']==SELECTED_SHA);gate('R3C_conditioning_SHA_exact',decision['conditioning_sha256']==CONDITIONING_SHA);gate('R3C_truth_SHA_exact',decision['sealed_target_sha256']==TRUTH_SHA);gate('R3C_threshold_exact',float(decision['breakthrough_threshold'])==THRESHOLD)
  gate('R3C_all_1078_used',decision['all_1078_streamlines_used'] is True);gate('R3C_all_9_days_used',decision['all_9_target_days_used'] is True);gate('R3C_no_adaptation',decision['adaptation_after_opening'] is False);gate('R3C_no_threshold_tuning',decision['threshold_tuning_after_opening'] is False);gate('R3C_no_alternate_candidate',decision['alternate_candidate_evaluated'] is False);gate('R3C_no_replacement_geology',decision['replacement_geology_or_seed_used'] is False);gate('R3C_no_second_test_attempt',decision['second_test_attempt_authorized'] is False)
  gate('R3C_target_was_opened_in_final_test',summary['target_opened'] is True);gate('R3C_inference_was_performed_in_final_test',summary['model_inference_performed'] is True)
  stage='audit_table_normalization'
  agg=[]
  for r in agg_raw: agg.append({'target_day':float(r['target_day']),'truth_aggregate_CO2_cut':float(r['truth_aggregate_CO2_cut']),'prediction_aggregate_CO2_cut':float(r['prediction_aggregate_CO2_cut']),'absolute_CO2_cut_error':float(r['absolute_CO2_cut_error']),'truth_breakthrough':parse_bool(r['truth_breakthrough']),'prediction_breakthrough':parse_bool(r['prediction_breakthrough']),'classification_match':parse_bool(r['classification_match'])})
  prod=[]
  for r in prod_raw: prod.append({'target_day':float(r['target_day']),'producer':str(r['producer']),'truth_CO2_cut':float(r['truth_CO2_cut']),'prediction_CO2_cut':float(r['prediction_CO2_cut']),'absolute_CO2_cut_error':float(r['absolute_CO2_cut_error']),'truth_breakthrough':parse_bool(r['truth_breakthrough']),'prediction_breakthrough':parse_bool(r['prediction_breakthrough']),'classification_match':parse_bool(r['classification_match'])})
  gate('aggregate_row_count_9',len(agg)==9,len(agg));gate('producer_row_count_36',len(prod)==36,len(prod));gate('aggregate_days_exact',sorted(r['target_day'] for r in agg)==EXPECTED_DAYS,sorted(r['target_day'] for r in agg));gate('producer_set_exact',sorted(set(r['producer'] for r in prod))==EXPECTED_PRODUCERS,sorted(set(r['producer'] for r in prod)))
  for p in EXPECTED_PRODUCERS: gate(f'{p}_all_9_days_present',sorted(r['target_day'] for r in prod if r['producer']==p)==EXPECTED_DAYS)
  stage='producer_event_failure_localization';am=[r for r in agg if not r['classification_match']];pm=[r for r in prod if not r['classification_match']]
  gate('aggregate_mismatch_count_zero',len(am)==0,len(am));gate('producer_mismatch_count_exactly_one',len(pm)==1,len(pm));m=pm[0];gate('sole_mismatch_day30',m['target_day']==30.,m['target_day']);gate('sole_mismatch_PROD_SW',m['producer']=='PROD_SW',m['producer']);gate('sole_mismatch_truth_no_breakthrough',m['truth_breakthrough'] is False);gate('sole_mismatch_prediction_false_positive',m['prediction_breakthrough'] is True)
  tc=float(m['truth_CO2_cut']);pc=float(m['prediction_CO2_cut']);truth_margin=THRESHOLD-tc;pred_excess=pc-THRESHOLD;signed=pc-tc;abserr=abs(signed);gate('mismatch_truth_cut_below_threshold',truth_margin>0,truth_margin);gate('mismatch_prediction_cut_above_threshold',pred_excess>=0,pred_excess)
  d30prod=sorted([r for r in prod if r['target_day']==30.],key=lambda r:r['producer']);d30agg=[r for r in agg if r['target_day']==30.][0]
  localization=[]
  for r in prod:
   tm=r['truth_CO2_cut']-THRESHOLD;pmg=r['prediction_CO2_cut']-THRESHOLD
   localization.append({**r,'signed_CO2_cut_error':r['prediction_CO2_cut']-r['truth_CO2_cut'],'truth_margin_from_threshold':tm,'prediction_margin_from_threshold':pmg,'truth_abs_distance_to_threshold':abs(tm),'prediction_abs_distance_to_threshold':abs(pmg),'is_final_hard_gate_mismatch':not r['classification_match']})
  ps=[]
  for p in EXPECTED_PRODUCERS:
   rows=[r for r in prod if r['producer']==p];met=basic_error_metrics(rows);ps.append({'producer':p,**met,'classification_mismatch_count':sum(not r['classification_match'] for r in rows),'minimum_truth_abs_distance_to_threshold':min(abs(r['truth_CO2_cut']-THRESHOLD) for r in rows),'minimum_prediction_abs_distance_to_threshold':min(abs(r['prediction_CO2_cut']-THRESHOLD) for r in rows)})
  aggctx=[]
  for r in agg: aggctx.append({**r,'signed_CO2_cut_error':r['prediction_aggregate_CO2_cut']-r['truth_aggregate_CO2_cut'],'truth_margin_from_threshold':r['truth_aggregate_CO2_cut']-THRESHOLD,'prediction_margin_from_threshold':r['prediction_aggregate_CO2_cut']-THRESHOLD})
  closure={'milestone':MILESTONE,'status':STATUS_PASS,'R3C_final_decision':'FAIL','R3C_failure_type':'producer-resolved early-time breakthrough classification mismatch','structural_acceptance':True,'aggregate_event_acceptance':True,'aggregate_first_breakthrough_truth_day':float(decision['truth_first_breakthrough_target_day']),'aggregate_first_breakthrough_prediction_day':float(decision['prediction_first_breakthrough_target_day']),'producer_event_acceptance':False,'sole_hard_gate_mismatch':{'target_day':30.0,'producer':'PROD_SW','truth_CO2_cut':tc,'prediction_CO2_cut':pc,'threshold':THRESHOLD,'truth_margin_below_threshold':truth_margin,'prediction_excess_above_threshold':pred_excess,'signed_prediction_minus_truth':signed,'absolute_CO2_cut_error':abserr,'truth_breakthrough':False,'prediction_breakthrough':True},'mismatch_scope':{'producer_day_pairs_total':36,'producer_day_pairs_mismatched':1,'mismatch_fraction':1/36,'aggregate_days_total':9,'aggregate_days_mismatched':0},'descriptive_producer_cut_error_all_36_pairs':basic_error_metrics(prod),'day30_aggregate_context':{'truth_CO2_cut':d30agg['truth_aggregate_CO2_cut'],'prediction_CO2_cut':d30agg['prediction_aggregate_CO2_cut'],'threshold':THRESHOLD,'truth_breakthrough':d30agg['truth_breakthrough'],'prediction_breakthrough':d30agg['prediction_breakthrough'],'classification_match':d30agg['classification_match']},'causal_claim':'NOT ESTABLISHED. R4 localizes the final acceptance failure to PROD_SW at day 30 but does not attribute it to any specific streamline, geology feature, loss term, architecture component, or numerical operator.','posthoc_tolerance_created':False,'threshold_changed':False,'model_inference_performed':False,'target_array_opened':False,'training_or_retuning_performed':False,'geology0030_status':'CONSUMED FINAL INDEPENDENT ACCEPTANCE EVIDENCE; MAY BE USED ONLY AS DIAGNOSTIC/DEVELOPMENT EVIDENCE FOR FUTURE WORK.','geology0030_retest_authorized':False,'alternate_R3_candidate_authorized':False,'next_decision':{'path_A':'If the intended claim is aggregate field-level breakthrough behavior, retain R3C as a documented producer-local limitation and do not relabel the failed producer-resolved gate as PASS.','path_B':'If producer-resolved breakthrough fidelity is required, freeze a new prospective repair protocol and a new untouched independent acceptance geology before any retraining. Geology0030 remains consumed and cannot serve as that acceptance case.'}}
  summary4={'milestone':MILESTONE,'status':STATUS_PASS,'repository_head':head,'repository_parent':parent,'localization':'PROD_SW / day 30 only','truth_CO2_cut':tc,'prediction_CO2_cut':pc,'truth_margin_below_threshold':truth_margin,'prediction_excess_above_threshold':pred_excess,'producer_day_mismatch_count':1,'producer_day_total_count':36,'aggregate_mismatch_count':0,'geology0030_consumed':True,'new_inference':False,'target_reopened':False,'retraining':False,'next':'POSTV16-AV1-D-R5 only if producer-resolved fidelity remains a required claim: prospective producer-resolved repair + new independent acceptance freeze before generating a new case.'}
  immutable_publish(out,{'PAD_Stream_POSTV16_AV1_D_R4_Summary.json':json_bytes(summary4),'POSTV16_AV1_D_R4_R3C_Scientific_Failure_Closure.json':json_bytes(closure),'POSTV16_AV1_D_R4_Producer_Time_Localization.csv':csv_bytes(localization),'POSTV16_AV1_D_R4_Producer_Error_Summary.csv':csv_bytes(ps),'POSTV16_AV1_D_R4_Day30_Producer_Context.csv':csv_bytes(d30prod),'POSTV16_AV1_D_R4_Aggregate_Context.csv':csv_bytes(aggctx),'POSTV16_AV1_D_R4_Final_Gate_Matrix.csv':csv_bytes([{'gate':k,**v} for k,v in gates.items()])})
  mr=[]
  for p in sorted(out.iterdir()):
   if p.is_file() and p.name!='POSTV16_AV1_D_R4_Artifact_Manifest.csv':mr.append({'file':p.name,'sha256':sha256_file(p),'bytes':p.stat().st_size})
  immutable_publish(out,{'POSTV16_AV1_D_R4_Artifact_Manifest.csv':csv_bytes(mr)})
  print('\n'+'='*168);print('POSTV16-AV1-D-R4: PASS');print('='*168);print(f"{'Status':88}: {STATUS_PASS}");print(f"{'R3C final acceptance':88}: FAIL (closed; not relabeled)");print(f"{'Structural acceptance':88}: True");print(f"{'Aggregate event classifications':88}: 9 / 9 match");print(f"{'Aggregate first breakthrough truth / prediction':88}: 60.0 / 60.0 days");print(f"{'Producer-day classification mismatches':88}: 1 / 36");print(f"{'Sole mismatch':88}: day 30 / PROD_SW / truth=False / prediction=True");print(f"{'PROD_SW day30 truth CO2 cut':88}: {tc:.12e}");print(f"{'PROD_SW day30 prediction CO2 cut':88}: {pc:.12e}");print(f"{'Truth margin below 1e-4':88}: {truth_margin:.12e}");print(f"{'Prediction excess above 1e-4':88}: {pred_excess:.12e}");print(f"{'Absolute producer cut error':88}: {abserr:.12e}");print(f"{'New model inference / target opening':88}: False / False");print(f"{'Training / threshold change':88}: False / False");print(f"{'Geology0030':88}: CONSUMED independent acceptance evidence");print(f"{'Causal mechanism identified':88}: False");print(f"{'NEXT':88}: R5 only if producer-resolved fidelity remains required");print('='*168);return 0
 except Exception as exc:
  blocked.mkdir(parents=True,exist_ok=True);rep={'milestone':MILESTONE,'status':STATUS_BLOCKED,'failed_stage':stage,'exception':repr(exc),'gates':gates,'model_inference_performed':False,'target_array_opened':False,'training_or_retuning_performed':False,'threshold_changed':False,'geology0030_retest_authorized':False,'next_action':'Audit only the technical R4 failure. Do not rerun R3C, reopen geology0030 target arrays, change the threshold, or substitute another candidate.'};data=json_bytes(rep);p=blocked/'POSTV16_AV1_D_R4_Blocked_Report.json'
  if p.exists() and p.read_bytes()!=data:p=blocked/('POSTV16_AV1_D_R4_Blocked_Report_'+hashlib.sha256(data).hexdigest()[:12]+'.json')
  if not p.exists():p.write_bytes(data)
  print('\n'+'='*168);print('POSTV16-AV1-D-R4: BLOCKED');print('='*168);print('Failed stage:',stage);print('Exception   :',repr(exc));print('No inference or target opening was performed by R4.');print('Report      :',p);return 2

def parse_args():
 p=argparse.ArgumentParser();p.add_argument('--project-root',type=Path,default=Path('.'));p.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'));p.add_argument('--self-test',action='store_true');return p.parse_args()
if __name__=='__main__':
 a=parse_args()
 if a.self_test:self_test();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
