#!/usr/bin/env python3
"""
PAD-Stream V16E-8-R1
Adapter / Physics-Screen Reconciliation Protocol Freeze

Purpose
-------
Controlled response to the blocked V16E-9 identical-state adapter execution.
This milestone DOES NOT train, infer, load checkpoints, reopen internal tests/OOD,
or deploy on SGSim. It preserves E8 as immutable audit history and freezes a
reconciled adapter-certification contract for V16E-9-R1.

Scientific diagnosis frozen here
--------------------------------
1. The E9 coordinate/state adapter itself closed to machine precision for tD,
   xD_star, shock-ratio and conditioning roundtrip identities.
2. E8 incorrectly made a *second GPU forward-pass output comparison* an adapter
   equivalence authority. The adapter-equivalence authority must be the exact
   canonical model-input tensor, not bitwise-equivalent outputs from two
   separately scheduled LSTM executions.
3. E8 also reused E3/R2 *teacher-construction* tolerances as if they were the
   acceptance contract for learned proposals. Teacher tolerances remain frozen
   and unchanged for teacher integrity. Learned proposals are governed by the
   prospectively frozen V16E-5 neural acceptance semantics plus hard physical
   safety screens and exact fallback.
4. A learned proposal that fails a screen is not an unsafe accepted state; it is
   rejected and routed to exact physics. Therefore a nonzero fallback count is
   permitted. Zero unsafe accepted proposals remains mandatory.

No sealed-test evidence is used to revise this contract. The only empirical
repair evidence is the V16E-9 public + TRAIN/VALIDATION blocked audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

MILESTONE='V16E-8-R1'
STATUS='V16E8_R1_ADAPTER_PHYSICS_SCREEN_RECONCILIATION_PROTOCOL_FROZEN'
NEXT='V16E-9-R1 — Reconciled Hybrid Transport Adapter Identical-State Certification'

E8_REL=Path('provenance/hybrid_dp/V16E8_TRANSPORT_ADAPTER_IDENTICAL_STATE_PROTOCOL_FREEZE')
E8={
 'contract':('V16E8_Transport_Adapter_Contract.json','c88ebf508451d138197230790ce4b743b8baee40a1daf72a01d72ea0fb189820'),
 'results':('V16E8_Transport_Adapter_and_Identical_State_Results.json','b12be8f10fce1f6d9cc22b204a867c3a3716e41ab9a27121d60ad1a1a524ccb3'),
 'summary':('PAD_Stream_V16E8_Summary.json','6c05ceaeada2d127839e881f0d1d1636a8dca5fe5421f6e452340f948b435760'),
 'handoff':('V16E8_Handoff.md','89db55027cb7dfec8e361b486e591b0878e300ab46a298862a2673ae6efe350e'),
}
E8_RUNNER=('PAD_Stream_V16E8_Transport_Adapter_and_Identical_State_Protocol_Freeze.py','0267669d080fe62f8ea4edbc6d27ac9a66739462b6c9e60ce652e4b106c3d556')

E9_RUNNER=('PAD_Stream_V16E9_Transport_Adapter_Implementation_and_Identical_State_Validation.py','2e66626e666c8239987cd59fd37171b4d3a543506f3a3508111654e81050da74')
E9_ADAPTER=('PAD_Stream_V16E9_Hybrid_Transport_Adapter.py','e5a89a4a591c5e3adf9be52ef274739e45a43f729cd45f044d39cc217bbd7d8f')
E9_REPORT_SHA='77b870beec1516e145cfe16d738bdef0eadfb653163ace7982845a56a1121661'
E9_BLOCKED_REL=Path('provenance/hybrid_dp/V16E9_BLOCKED_ADAPTER_EQUIVALENCE')/E9_REPORT_SHA[:16]
E9_REPORT='V16E9_Blocked_Adapter_Equivalence_Audit.json'
E9_SUMMARY='PAD_Stream_V16E9_Blocked_Summary.json'
E9_HANDOFF='V16E9_Blocked_Handoff.md'

E5_REL=Path('provenance/hybrid_dp/V16E5_PRETRAINING_MANIFEST_FREEZE')
E5_MANIFEST=('V16E5_PreTraining_Manifest.json','c197dae32d01a1f083f7ad414e601eac1f44d7405b6087c7c7db8a6c28c5c808')
E3_REL=Path('provenance/hybrid_dp/V16E3_R1_HYBRID_PROTOCOL_FREEZE')
E3_PROTOCOL=('V16E3_R1_Hybrid_BL_DP_Protocol.json','57bcb2e74c68eb77ed8de69d75ddafc00b38d2f3c4e9b884bfc87676160db4a1')

OUT_REL=Path('provenance/hybrid_dp/V16E8_R1_ADAPTER_PHYSICS_SCREEN_RECONCILIATION_PROTOCOL')

PROHIBITIONS=[
 'NO TRAINING, GRADIENT UPDATE, OR CHECKPOINT CREATION.',
 'NO MODEL INFERENCE OR CHECKPOINT LOAD.',
 'NO CHECKPOINT SELECTION, REPLACEMENT, OR RETRAINING.',
 'NO INTERNAL-TEST RE-EVALUATION OR TEST-INFORMED REVISION.',
 'NO OOD REOPENING.',
 'NO SGSim MODIFICATION OR DEPLOYMENT.',
 'NO PRESSURE / DARCY / POLLOCK / TOF RECOMPUTATION.',
 'NO GRID MAP-BACK.',
 'NO E3/R2 TEACHER-TOLERANCE CHANGE.',
 'NO E5 TRAINING/VALIDATION ACCEPTANCE CHANGE.',
 'NO ROUTING CHANGE FROM V16E-7.',
]

class FreezeError(RuntimeError): pass
class Gates:
 def __init__(self): self.items={}
 def add(self,name,passed,detail=None):
  self.items[name]={'passed':bool(passed),'detail':detail}
  print(f"[{'PASS' if passed else 'FAIL'}] {name}" + (f": {detail}" if detail else ''),flush=True)
  if not passed: raise FreezeError(name + (f': {detail}' if detail else ''))

def sha(path:Path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
 return h.hexdigest()

def digest(data:bytes): return hashlib.sha256(data).hexdigest()
def encoded(obj): return (json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+'\n').encode('utf-8')
def read_json(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def bind(g,label,path,expected):
 path=Path(path); g.add(label+'_exists',path.is_file(),str(path)); actual=sha(path); g.add(label+'_SHA_exact',actual==expected,actual if actual!=expected else None); return actual

def publish(out:Path,payloads:dict[str,bytes]):
 if out.exists():
  names={p.name for p in out.iterdir() if p.is_file()}
  if names!=set(payloads): raise FreezeError('Existing E8-R1 output directory differs; nothing overwritten.')
  for n,b in payloads.items():
   if (out/n).read_bytes()!=b: raise FreezeError('Existing E8-R1 output bytes differ; nothing overwritten.')
  print('Existing identical V16E-8-R1 freeze reused.',flush=True); return
 out.parent.mkdir(parents=True,exist_ok=True)
 stage=Path(tempfile.mkdtemp(prefix='.v16e8-r1-',dir=out.parent))
 try:
  for n,b in payloads.items():
   p=stage/n
   with p.open('xb') as f: f.write(b); f.flush(); os.fsync(f.fileno())
  stage.rename(out)
 finally:
  if stage.exists(): shutil.rmtree(stage)

def main(argv=None):
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--project-root',type=Path,default=Path(__file__).resolve().parent)
 ap.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'))
 ap.add_argument('--output-dir',type=Path)
 a=ap.parse_args(argv); project=a.project_root.resolve(); drive=a.drive_root.resolve(); out=(a.output_dir or drive/OUT_REL).resolve()

 print('='*118); print('PAD-Stream V16E-8-R1 Adapter / Physics-Screen Reconciliation Protocol Freeze'); print('='*118)
 print('\n'.join(PROHIBITIONS),flush=True)
 g=Gates()

 print('\nV16E-8 IMMUTABLE PARENT AUTHORITY')
 e8=drive/E8_REL
 e8_objs={}
 for k,(n,s) in E8.items(): bind(g,'E8_'+k,e8/n,s); e8_objs[k]=read_json(e8/n) if n.endswith('.json') else None
 bind(g,'E8_runner',project/E8_RUNNER[0],E8_RUNNER[1])

 print('\nBLOCKED V16E-9 REPAIR EVIDENCE')
 bind(g,'E9_runner',project/E9_RUNNER[0],E9_RUNNER[1]); bind(g,'E9_adapter',project/E9_ADAPTER[0],E9_ADAPTER[1])
 e9dir=drive/E9_BLOCKED_REL
 report_path=e9dir/E9_REPORT; bind(g,'E9_blocked_report',report_path,E9_REPORT_SHA)
 g.add('E9_blocked_summary_exists',(e9dir/E9_SUMMARY).is_file(),str(e9dir/E9_SUMMARY)); g.add('E9_blocked_handoff_exists',(e9dir/E9_HANDOFF).is_file(),str(e9dir/E9_HANDOFF))
 report=read_json(report_path); summary=read_json(e9dir/E9_SUMMARY)
 g.add('E9_status_blocked','BLOCKED' in str(report.get('status','')).upper())
 g.add('E9_no_training',report.get('training_performed') is False)
 g.add('E9_no_checkpoint_change',report.get('checkpoints_changed') is False)
 g.add('E9_internal_test_closed',report.get('internal_test_reopened') is False)
 g.add('E9_OOD_closed',report.get('OOD_opened') is False)
 g.add('E9_SGSim_not_deployed',report.get('SGSim_deployed') is False)
 g.add('E9_summary_report_link',summary.get('report_sha256')==E9_REPORT_SHA)
 reps=report.get('reports',[]); g.add('E9_two_branch_reports',len(reps)==2,str([r.get('label') for r in reps]))
 repmap={r.get('label'):r for r in reps}
 g.add('E9_Hybrid10_report_present','Hybrid10' in repmap); g.add('E9_Hybrid12_report_present','Hybrid12' in repmap)
 for label in ('Hybrid10','Hybrid12'):
  r=repmap[label]; m=r.get('maxima',{}); gates=r.get('gates',{})
  g.add(label+'_coordinate_identities_machine_close',
        float(m.get('conditioning_roundtrip_abs',1))<=1e-12 and float(m.get('tD_identity_abs',1))<=1e-12 and float(m.get('xD_star_identity_abs',1))<=1e-12 and float(m.get('shock_ratio_identity_abs',1))<=1e-12)
  g.add(label+'_separate_forward_equivalence_gate_failed',gates.get('adapter_vs_direct_model_same_input_abs_max') is False)
  g.add(label+'_zero_fallback_requirement_failed',gates.get('all_frozen_physics_screens_pass') is False)

 print('\nFROZEN E5 NEURAL ACCEPTANCE / E3 TEACHER AUTHORITY')
 e5p=drive/E5_REL/E5_MANIFEST[0]; bind(g,'E5_manifest',e5p,E5_MANIFEST[1]); e5=read_json(e5p)
 e3p=drive/E3_REL/E3_PROTOCOL[0]; bind(g,'E3_protocol',e3p,E3_PROTOCOL[1]); e3=read_json(e3p)
 va=e5['training_protocol']['validation_acceptance'] if 'training_protocol' in e5 else e5.get('validation_acceptance')
 if va is None:
  # E5 production manifest stores Hybrid recipes beneath model_execution.
  def find_va(o):
   if isinstance(o,dict):
    if 'validation_acceptance' in o and isinstance(o['validation_acceptance'],dict): return o['validation_acceptance']
    for v in o.values():
     z=find_va(v)
     if z is not None:return z
   if isinstance(o,list):
    for v in o:
     z=find_va(v)
     if z is not None:return z
   return None
  va=find_va(e5)
 g.add('E5_validation_acceptance_found',isinstance(va,dict))
 required_va={'Sw_RMSE_max':0.020,'Sw_MAE_max':0.0125,'profile_RMSE_p95_max':0.030,'BC_RMSE_max':0.015,'front_RMSE_max':0.015,'physics_characteristic_RMSE_max':0.030,'monotonic_violation_fraction_max':0.005,'nonfinite_predictions_allowed':0}
 g.add('E5_validation_acceptance_exact',all(abs(float(va[k])-v)<=1e-15 for k,v in required_va.items()),str({k:va.get(k) for k in required_va}))

 e8c=e8_objs['contract']; old=e8c['physics_screens_for_future_adapter_execution']
 g.add('E8_teacher_like_characteristic_screen_exact',abs(float(old['characteristic_RMS_tol'])-0.005)<=1e-15)
 g.add('E8_teacher_like_endpoint_screen_exact',abs(float(old['injection_endpoint_abs_tol'])-0.002)<=1e-15 and abs(float(old['shock_endpoint_abs_tol'])-0.002)<=1e-15)
 g.add('E8_zero_fallback_gate_was_required',e8c['identical_state_validation_protocol_for_next_milestone']['required_gates']['all_frozen_physics_screens_pass'] is True)

 prior_selected=report.get('selected_families',{})
 previous_train=list(prior_selected.get('train',{}).get('family_ids',[])); previous_val=list(prior_selected.get('validation',{}).get('family_ids',[]))
 g.add('blocked_E9_selected_16_train_16_validation',len(previous_train)==16 and len(previous_val)==16)

 print('\nV16E-8-R1 RECONCILIATION CONTRACT')
 contract={
  'milestone':MILESTONE,
  'status':STATUS,
  'revision_scope':'supersedes only V16E-8 adapter-equivalence and learned-proposal screening semantics; V16E-8 remains immutable audit history',
  'evidence_basis':{
   'blocked_E9_report_sha256':E9_REPORT_SHA,
   'allowed_for_revision':'public anchors plus TRAIN/VALIDATION identical-state evidence only',
   'internal_test_used_for_revision':False,'OOD_used_for_revision':False,
   'blocked_E9_observed':{
    lab:{'profiles':repmap[lab]['profiles'],'screen_rejections':repmap[lab]['screen_rejections'],'maxima':repmap[lab]['maxima'],'gates':repmap[lab]['gates']} for lab in ('Hybrid10','Hybrid12')
   },
  },
  'unchanged_authorities':{
   'checkpoints':'Hybrid10 and Hybrid12 accepted checkpoint identities unchanged',
   'routing':'V16E-7 fixed-endpoint Hybrid10 / variable-endpoint Hybrid12 / exact fallback unchanged',
   'coordinate_mapping':'V16E-8 Pollock tau -> pre-BT fan eta mathematics unchanged',
   'teacher_tolerances':'E3/R2 teacher generation/audit tolerances remain unchanged and are not reclassified',
   'training_validation_contract':'V16E-5 training, checkpoint selection and validation acceptance remain unchanged',
   'internal_tests':'already consumed once; never reopen for R1 or E9-R1',
   'OOD':'remains closed',
   'SGSim':'remains unauthorized',
  },
  'diagnosis':{
   'adapter_state_math':'accepted as correctly reconstructed in blocked E9 because conditioning/tD/xD_star/shock-ratio identities closed at <=1e-12',
   'separate_forward_pass_gate':'retired as adapter authority; two separately scheduled GPU LSTM calls may differ numerically even for identical canonical inputs',
   'screen_semantic_mismatch':'E8 applied teacher-integrity tolerances (0.002 endpoint, 0.005 characteristic, 1e-7 positive-increment amplitude) as universal neural proposal gates and additionally required zero fallbacks',
   'safety_interpretation':'screen rejection is safe only when the proposal is not accepted and exact physics fallback is used; nonzero fallback count is therefore permitted',
  },
  'reconciled_adapter_equivalence':{
   'authoritative_object':'canonical float32 model input tensor [eta plus repeated conditioning]',
   'conditioning_roundtrip_abs_max':1e-12,
   'state_identity_abs_max':1e-12,
   'model_input_tensor_rule':'direct-state and adapter-state canonical tensors must be np.array_equal after the same float32 construction path',
   'model_inference_rule':'one canonical forward pass per model/batch; do not use difference between two separate forward passes as adapter-equivalence evidence',
   'repeated_inference_difference':'may be recorded as non-gating runtime diagnostic only',
  },
  'teacher_integrity_screens_unchanged':{
   'fan_endpoint_abs_tol':float(old['injection_endpoint_abs_tol']),
   'characteristic_RMS_tol':float(old['characteristic_RMS_tol']),
   'inventory_abs_tol':float(old['inventory_abs_tol']),
   'scope':'R2/E4 teacher construction and audit only; these values remain unchanged',
  },
  'learned_proposal_execution_screen':{
   'finite_prediction':True,
   'saturation_bounds':'swc <= Sw <= 1-sor',
   'injection_endpoint_abs_max':float(required_va['BC_RMSE_max']),
   'front_endpoint_abs_max':float(required_va['front_RMSE_max']),
   'characteristic_RMSE_max':float(required_va['physics_characteristic_RMSE_max']),
   'inventory_abs_max':float(old['inventory_abs_tol']),
   'monotonic_violation_fraction_max':float(required_va['monotonic_violation_fraction_max']),
   'nonfinite_predictions_allowed':0,
   'downstream_initial_state_exact':True,
   'fan_teacher_RMSE':'diagnostic only in E9-R1; no new post-hoc threshold invented',
   'projection_teacher_RMSE':'diagnostic only in E9-R1; no new post-hoc threshold invented',
   'failure_action':'reject learned proposal and invoke exact R2/physics transport for that state; never repair the neural profile in place',
   'fallback_rate':'report descriptively; no safety threshold invented in R1',
   'zero_unsafe_accepted_proposals':True,
  },
  'fresh_E9_R1_certification_population':{
   'public_anchors':'same public anchors allowed as development references',
   'synthetic_family_rule':'exclude every synthetic family used in blocked E9; within TRAIN and VALIDATION separately sort remaining IDs by SHA256("V16E8_R1_CERT_1801|"+family_id), then select first 16 per partition',
   'blocked_E9_train_exclusions':previous_train,
   'blocked_E9_validation_exclusions':previous_val,
   'layers_zero_based':[0,3,7],
   'clock_indices_zero_based':[0,4,9,14,19],
   'allocation_modes_zero_based':[0,1],
   'internal_test_access':False,'OOD_access':False,
   'expected_profiles_per_branch':1000,
  },
  'E9_R1_required_gates':{
   'canonical_input_tensor_identity':True,
   'tD_xDstar_shock_identities_abs_max':1e-12,
   'downstream_initial_state_exact':True,
   'every_profile_partitioned_to_learned_accept_or_exact_fallback':True,
   'zero_unsafe_accepted_proposals':True,
   'at_least_one_learned_proposal_accepted_per_branch':True,
   'fallback_count_may_be_nonzero':True,
   'no_internal_test_or_OOD_access':True,
   'no_checkpoint_or_routing_change':True,
   'SGSim_deployment_authorized_on_E9_R1_pass':False,
  },
  'next_milestone':NEXT,
 }

 g.add('teacher_tolerances_unchanged',contract['teacher_integrity_screens_unchanged']['characteristic_RMS_tol']==0.005 and contract['teacher_integrity_screens_unchanged']['fan_endpoint_abs_tol']==0.002)
 g.add('E5_neural_characteristic_restored_for_proposals',contract['learned_proposal_execution_screen']['characteristic_RMSE_max']==0.03)
 g.add('E5_endpoint_semantics_restored_for_proposals',contract['learned_proposal_execution_screen']['injection_endpoint_abs_max']==0.015 and contract['learned_proposal_execution_screen']['front_endpoint_abs_max']==0.015)
 g.add('monotonic_fraction_not_amplitude',contract['learned_proposal_execution_screen']['monotonic_violation_fraction_max']==0.005)
 g.add('inventory_hard_screen_preserved',contract['learned_proposal_execution_screen']['inventory_abs_max']==0.005)
 g.add('nonzero_fallback_permitted',contract['E9_R1_required_gates']['fallback_count_may_be_nonzero'])
 g.add('zero_unsafe_accept_required',contract['E9_R1_required_gates']['zero_unsafe_accepted_proposals'])
 g.add('fresh_synthetic_certification_disjoint_rule',len(previous_train)==16 and len(previous_val)==16 and 'exclude every synthetic family used in blocked E9' in contract['fresh_E9_R1_certification_population']['synthetic_family_rule'])
 g.add('tests_and_OOD_remain_closed',not contract['fresh_E9_R1_certification_population']['internal_test_access'] and not contract['fresh_E9_R1_certification_population']['OOD_access'])
 g.add('SGSim_still_locked',contract['E9_R1_required_gates']['SGSim_deployment_authorized_on_E9_R1_pass'] is False)

 contract_bytes=encoded(contract)
 results={
  'milestone':MILESTONE,'status':STATUS,'runner_sha256':sha(Path(__file__)),
  'E8_contract_sha256':E8['contract'][1],'blocked_E9_report_sha256':E9_REPORT_SHA,
  'E9_blocked_summary_sha256':sha(e9dir/E9_SUMMARY),'E9_blocked_handoff_sha256':sha(e9dir/E9_HANDOFF),
  'E5_manifest_sha256':E5_MANIFEST[1],'E3_protocol_sha256':E3_PROTOCOL[1],
  'contract_sha256':digest(contract_bytes),'gates':g.items,
  'training_performed':False,'inference_performed':False,'checkpoints_changed':False,
  'internal_test_reopened':False,'OOD_opened':False,'SGSim_deployed':False,
  'next_milestone':NEXT,
 }
 results_bytes=encoded(results)
 summary={
  'milestone':MILESTONE,'status':'PASS','blocked_E9_bound':True,
  'adapter_coordinate_math_changed':False,'routing_changed':False,'checkpoints_changed':False,
  'teacher_tolerances_changed':False,'learned_proposal_screen_semantics_reconciled':True,
  'separate_GPU_forward_pass_difference_retired_as_adapter_gate':True,
  'exact_fallback_on_screen_rejection_required':True,
  'fresh_E9_R1_synthetic_population_disjoint_from_blocked_E9':True,
  'internal_test_reopened':False,'OOD_opened':False,'SGSim_deployment_authorized':False,
  'contract_sha256':digest(contract_bytes),'results_sha256':digest(results_bytes),'next_milestone':NEXT,
 }
 summary_bytes=encoded(summary)
 handoff=f"""# PAD-Stream V16E-8-R1 — Adapter / Physics-Screen Reconciliation Protocol\n\nV16E-9 blocked without training, checkpoint change, test/OOD access, or SGSim deployment.\nThe coordinate/state adapter identities closed to machine precision. The blocked evidence\ntherefore supports a narrow protocol correction rather than retraining.\n\nE8 remains immutable audit history. R1 supersedes only two E8 adapter-execution semantics:\n\n1. Adapter equivalence is now the exact canonical float32 model-input tensor. A difference\n   between two separately scheduled GPU LSTM forward passes is diagnostic, not adapter\n   authority. E9-R1 must use one canonical forward path.\n2. E3/R2 teacher-construction tolerances remain unchanged. Learned proposals are screened\n   under the pre-existing V16E-5 neural acceptance semantics, while the 0.005 inventory\n   identity remains a hard physical screen. Screen failures route to exact physics. A nonzero\n   fallback count is allowed; zero unsafe accepted learned proposals is mandatory.\n\nE9-R1 must exclude every synthetic family used in blocked E9 and certify on a fresh\nTRAIN/VALIDATION subset. Internal tests and OOD remain closed. SGSim remains locked.\n\nContract SHA: {digest(contract_bytes)}\nResults SHA: {digest(results_bytes)}\nBlocked E9 report SHA: {E9_REPORT_SHA}\nNEXT: {NEXT}\n""".encode('utf-8')
 payloads={
  'V16E8_R1_Adapter_Physics_Screen_Reconciliation_Protocol.json':contract_bytes,
  'V16E8_R1_Adapter_Physics_Screen_Reconciliation_Results.json':results_bytes,
  'PAD_Stream_V16E8_R1_Summary.json':summary_bytes,
  'V16E8_R1_Handoff.md':handoff,
 }
 publish(out,payloads)
 print('\n'+'='*118); print('V16E-8-R1 RESULT: PASS'); print('='*118)
 print(f"{'E8 coordinate / routing mathematics changed':50}: NO")
 print(f"{'E3/R2 teacher tolerances changed':50}: NO")
 print(f"{'E5 neural acceptance contract changed':50}: NO")
 print(f"{'Learned-proposal screen semantics reconciled':50}: YES")
 print(f"{'Exact fallback on rejected proposal required':50}: YES")
 print(f"{'Internal test / OOD reopened':50}: NO / NO")
 print(f"{'SGSim deployment authorized':50}: NO")
 for n in payloads: print(n+' SHA:',sha(out/n))
 print('Output:',out); print('NEXT:',NEXT)
 return 0

if __name__=='__main__':
 try: sys.exit(main())
 except (FreezeError,OSError,ValueError,KeyError,TypeError,AssertionError) as exc:
  print('\n[FAIL] V16E-8-R1 did not close:',exc,file=sys.stderr,flush=True)
  print('No checkpoint, test/OOD, routing, or SGSim authority was changed.',file=sys.stderr,flush=True)
  sys.exit(2)
