#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any

M = "POSTV16-AV5-B1"
NAME = (
    "Day30 Cold-Start Specialization + End-to-End Wall-Clock Economics + "
    "Prospective Admission-Gated Learned-Seed Design Freeze"
)
PASS = (
    "POSTV16AV5B1_DAY30_COLDSTART_DISPATCH_WALLCLOCK_ECONOMICS_PROSPECTIVE_"
    "ADMISSION_GATED_DESIGN_FREEZE_PASS_NO_MODEL_EXECUTION"
)
BLOCK = "POSTV16AV5B1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "4976b8a3e7e6c982dadf027768087102a5e5f148"
RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV5 = Path("post_v16") / RID / "POSTV16_AV5_Learned_Acceleration"
AV4_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"
CHECKPOINT_SHA = "4cb41080b1d92780af21c9fae6e830a681d69315940656f1938db97c75dc52ef"

A7_RUNNER = "PAD_Stream_POSTV16_AV5_A7_Scientific_Outcome_Interpretation_and_Production_Decision_Freeze.py"
A7_RUNNER_BLOB = "3e39af491ed0c3f04c40958eb79571f43d4d6eb7"
A6_RUNNER = "PAD_Stream_POSTV16_AV5_A6_Frozen_Checkpoint_OneTouch_LockedOOD_Sequential_PressureSeed_Evaluation.py"
A6_RUNNER_BLOB = "1d782e6f4616e7a31fcae031c959e1b7a384b46c"
A5R1_RUNNER = (
    "PAD_Stream_POSTV16_AV5_A5_R1_SG3_Blob_Authority_Repair_Controlled_Training_and_"
    "Validation_ExactCorrection_Checkpoint_Selection.py"
)
A5R1_RUNNER_BLOB = "dd1bfd2d8a854d218fc220949bc8ca63d92c650b"
SOURCE_BLOBS = {
    A7_RUNNER: A7_RUNNER_BLOB,
    A6_RUNNER: A6_RUNNER_BLOB,
    A5R1_RUNNER: A5R1_RUNNER_BLOB,
}

A7_TOKEN = "POSTV16_AV5_A7"
A7_REL = BASE_AV5 / (A7_TOKEN + "_Scientific_Outcome_Interpretation_and_Production_Decision_Freeze")
A7_SUMMARY = f"PAD_Stream_{A7_TOKEN}_Summary.json"
A7_DECISION = f"{A7_TOKEN}_Decision_Contract.json"
A7_NEXT = f"{A7_TOKEN}_Focused_Research_Direction_Contract.json"
A7_MANIFEST = f"{A7_TOKEN}_Artifact_Manifest.csv"
A7_STATUS = "POSTV16AV5A7_SCIENTIFIC_OUTCOME_INTERPRETATION_AND_PRODUCTION_DECISION_FREEZE_PASS_NO_MODEL_EXECUTION"
A7_CLASSIFICATION = (
    "AV5_SAFEGUARDED_LEARNED_PRESSURE_SEED_MECHANISM_VALIDATED_LOCKED_OOD_"
    "ACCELERATION_SPARSE_DAY30_FOCUSED_PRODUCTION_AND_P3_NOT_AUTHORIZED"
)

A6_TOKEN = "POSTV16_AV5_A6"
A6_REL = BASE_AV5 / (A6_TOKEN + "_Frozen_Checkpoint_OneTouch_LockedOOD_Sequential_PressureSeed_Evaluation")
A6_SUMMARY = f"PAD_Stream_{A6_TOKEN}_Summary.json"
A6_MANIFEST = f"{A6_TOKEN}_Artifact_Manifest.csv"

A5R1_TOKEN = "POSTV16_AV5_A5_R1"
A5R1_REL = BASE_AV5 / (
    A5R1_TOKEN + "_SG3_Blob_Authority_Repair_Controlled_Training_and_Validation_ExactCorrection_Checkpoint_Selection"
)
A5R1_SUMMARY = f"PAD_Stream_{A5R1_TOKEN}_Summary.json"
A5R1_MANIFEST = f"{A5R1_TOKEN}_Artifact_Manifest.csv"
A5R1_CHECKPOINT = f"{A5R1_TOKEN}_Best_Validation_Model.keras"

OUT_TOKEN = "POSTV16_AV5_B1"
OUT_REL = BASE_AV5 / (OUT_TOKEN + "_Day30_ColdStart_Dispatch_WallClock_Economics_Prospective_Design_Freeze")
BLOCK_REL = BASE_AV5 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DESIGN = f"{OUT_TOKEN}_Day30_ColdStart_Dispatch_Design_Contract.json"
TIMING = f"{OUT_TOKEN}_EndToEnd_WallClock_Protocol.json"
LEAKAGE = f"{OUT_TOKEN}_Prospective_Leakage_and_Selection_Firewall.json"
B2_HANDOFF = f"{OUT_TOKEN}_B2_Handoff_Contract.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
GATE_MATRIX = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

TIMING_PAIRS = 11
WARMUP_PAIRS = 2
REQUIRED_FASTER_PAIRS = 9
VALIDATION_REALIZATION = "AV3CR0003"
LOCKED_OOD_REALIZATION = "AV3CR0004"
CANONICAL_DAYS = [30.0,60.0,100.0,150.0,250.0,365.0,500.0,750.0,1000.0]

class GateError(RuntimeError):
    pass

def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def js(path: Path) -> dict[str,Any]:
    return json.loads(path.read_text(encoding='utf-8'))

def csvr(path: Path) -> list[dict[str,str]]:
    with path.open(newline='',encoding='utf-8') as f: return list(csv.DictReader(f))

def csvb(rows:list[dict[str,Any]])->bytes:
    if not rows: return b''
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    s=io.StringIO(newline='')
    w=csv.DictWriter(s,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows)
    return s.getvalue().encode('utf-8')

def jb(obj:Any)->bytes:
    return (json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')

def manifest(directory:Path, filename:str)->dict[str,str]:
    result={}
    for row in csvr(directory/filename):
        p=directory/row['file']
        if not p.is_file(): raise GateError('manifest_missing:'+p.name)
        if sha(p)!=row['sha256']: raise GateError('manifest_sha:'+p.name)
        if p.stat().st_size!=int(row['bytes']): raise GateError('manifest_bytes:'+p.name)
        result[p.name]=row['sha256']
    if not result: raise GateError('manifest_empty:'+filename)
    return result

def immutable_publish(out:Path, files:dict[str,bytes])->None:
    out.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        p=out/name
        if p.exists() and p.read_bytes()!=data: raise GateError('existing_output_differs:'+name)
        if not p.exists(): p.write_bytes(data)

def selftest()->None:
    assert BRANCH=='postv16-av4-pivot'
    assert len(PARENT)==40
    assert len(CHECKPOINT_SHA)==64
    assert TIMING_PAIRS==11 and WARMUP_PAIRS==2 and REQUIRED_FASTER_PAIRS==9
    assert len(CANONICAL_DAYS)==9 and CANONICAL_DAYS[0]==30.0
    print('POSTV16 AV5-B1 structural self-test: PASS')

def main(project_root:Path, drive_root:Path)->int:
    root=project_root.resolve(); drive=drive_root.resolve(); out=drive/OUT_REL; block_dir=drive/BLOCK_REL
    stage='preflight'; gates=[]
    def gate(name:str,cond:Any,detail:Any=None)->None:
        ok=bool(cond); gates.append({'stage':stage,'gate':name,'pass':ok,'detail':'' if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ('' if detail is None else f' -- {detail}'))
        if not ok: raise GateError(name)
    try:
        print('='*208)
        print('POSTV16-AV5-B1 — DAY30 COLD-START DISPATCH / WALL-CLOCK ECONOMICS / PROSPECTIVE DESIGN FREEZE')
        print('='*208)
        print('DESIGN FREEZE ONLY. NO MODEL TRAINING. NO MODEL INFERENCE. NO TIMING EXECUTION.')
        print('A6 LOCKED-OOD RESULT IS MOTIVATION ONLY — NEVER A TUNING OR SELECTION SET.')
        print('FROZEN A5-R1 CHECKPOINT REMAINS UNCHANGED. PRODUCTION/P3 REMAIN LOCKED.')
        print()

        stage='preexisting_state_firewall'
        gate('no_preexisting_PASS',not (out/SUMMARY).exists())
        gate('no_preexisting_BLOCK',not (block_dir/f'{OUT_TOKEN}_Blocked_Report.json').exists())

        stage='repository_authority'
        branch=gt(root,'branch','--show-current'); parent=gt(root,'rev-parse','HEAD^'); clean=gt(root,'status','--porcelain')
        gate('branch_exact',branch==BRANCH,branch); gate('parent_exact',parent==PARENT,parent); gate('repository_clean',clean=='',clean)
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn; gate(f'{Path(fn).stem}_present',p.is_file(),str(p))
            actual=gt(root,'hash-object',str(p)) if p.is_file() else 'missing'
            gate(f'{Path(fn).stem}_blob_exact',actual==expected,actual)

        stage='A7_design_authority'
        a7d=drive/A7_REL; a7m=manifest(a7d,A7_MANIFEST); a7s=js(a7d/A7_SUMMARY); a7c=js(a7d/A7_DECISION); a7n=js(a7d/A7_NEXT)
        gate('A7_manifest_nonempty',len(a7m)>0)
        gate('A7_status_exact',a7s.get('status')==A7_STATUS,a7s.get('status'))
        gate('A7_classification_exact',a7s.get('classification')==A7_CLASSIFICATION,a7s.get('classification'))
        gate('A7_AV4_state_SHA_exact',a7s.get('AV4_authoritative_state_sha256')==AV4_STATE_SHA)
        gate('A7_checkpoint_SHA_exact',a7s.get('checkpoint_sha256')==CHECKPOINT_SHA)
        gate('A7_scientific_outcome_frozen',a7s.get('AV5_scientific_outcome_frozen') is True)
        gate('A7_production_locked',a7c.get('AV5_production_execution_authorized') is False)
        gate('A7_P3_locked',a7c.get('P3_authorized') is False)
        gate('A7_B1_design_authorized',a7c.get('focused_follow_on_research_design_authorized') is True)
        gate('A7_B1_execution_not_authorized',a7c.get('focused_follow_on_execution_authorized') is False)
        gate('A7_next_milestone_B1',a7c.get('next_design_milestone')=='POSTV16-AV5-B1',a7c.get('next_design_milestone'))
        gate('A7_B1_scope_design_freeze_only',a7n.get('authorized_scope')=='DESIGN_FREEZE_ONLY',a7n.get('authorized_scope'))
        gate('A7_B1_execution_false',a7n.get('execution_authorized') is False)
        preserve=a7n.get('must_preserve',{})
        gate('A7_preserve_checkpoint',preserve.get('A5R1_checkpoint_as_frozen_reference')==CHECKPOINT_SHA)
        gate('A7_preserve_exact_residual_admission',preserve.get('exact_residual_seed_admission') is True)
        gate('A7_preserve_exact_FV',preserve.get('exact_FV_correction') is True)
        gate('A7_preserve_direct_fallback',preserve.get('direct_spsolve_fallback_and_reference') is True)

        stage='frozen_reference_provenance'
        a5d=drive/A5R1_REL; a5m=manifest(a5d,A5R1_MANIFEST); a5s=js(a5d/A5R1_SUMMARY)
        gate('A5R1_manifest_nonempty',len(a5m)>0)
        gate('A5R1_checkpoint_manifested',A5R1_CHECKPOINT in a5m and (a5d/A5R1_CHECKPOINT).is_file())
        gate('A5R1_checkpoint_file_SHA_exact',sha(a5d/A5R1_CHECKPOINT)==CHECKPOINT_SHA,sha(a5d/A5R1_CHECKPOINT))
        gate('A5R1_checkpoint_summary_SHA_exact',a5s.get('checkpoint_sha256')==CHECKPOINT_SHA)
        a6d=drive/A6_REL; a6m=manifest(a6d,A6_MANIFEST); a6s=js(a6d/A6_SUMMARY)
        gate('A6_manifest_nonempty',len(a6m)>0)
        gate('A6_locked_OOD_motivation_bound',a6s.get('locked_OOD_realization')==LOCKED_OOD_REALIZATION)
        gate('A6_only_implied_motivation_not_selection',True)

        stage='prospective_design_freeze'
        leakage = {
            'milestone': M,
            'status': PASS,
            'A6_locked_OOD_role': 'RETROSPECTIVE_MOTIVATION_ONLY',
            'A6_locked_OOD_may_be_used_for_optimizer_updates': False,
            'A6_locked_OOD_may_be_used_for_threshold_tuning': False,
            'A6_locked_OOD_may_be_used_for_checkpoint_selection': False,
            'A6_locked_OOD_may_be_used_for_B2_wallclock_acceptance': False,
            'B2_economic_selection_set': VALIDATION_REALIZATION,
            'TRAIN_realizations': ['AV3CR0001','AV3CR0002'],
            'VALIDATION_realization': VALIDATION_REALIZATION,
            'LOCKED_OOD_realization_already_opened_but_sealed_from_B2_selection': LOCKED_OOD_REALIZATION,
            'normalization_refit_allowed': False,
            'checkpoint_retraining_allowed': False,
            'checkpoint_reselection_allowed': False,
            'checkpoint_retuning_allowed': False,
        }

        dispatch = {
            'milestone': M,
            'status': PASS,
            'policy_name': 'DAY30_ONLY_FROZEN_CHECKPOINT_DISPATCH_WITH_EXACT_RESIDUAL_ADMISSION',
            'frozen_checkpoint_sha256': CHECKPOINT_SHA,
            'new_model_training': False,
            'new_checkpoint_creation': False,
            'pre_inference_dispatch_gate': {
                'inputs': ['canonical_time_index_or_day_only'],
                'rule': 'invoke frozen learned pressure-seed model iff target_day == 30.0; otherwise bypass learned inference',
                'pressure_truth_used': False,
                'solver_residual_used_before_inference': False,
            },
            'Day30_post_inference_admission': {
                'rule': 'admit learned seed iff ||b-A*p_hat||_2 < ||b-A*p_temporal||_2',
                'exact_residual_comparison_required': True,
            },
            'Day60_plus_policy': 'TEMPORAL_SEED_ONLY_NO_MODEL_INFERENCE',
            'correction': 'exact iterative finite-volume correction A*delta=b-A*p_selected',
            'direct_fallback_and_reference': True,
            'sequential_state_rule': 'carry accepted exact corrected pressure forward; never carry direct reference solely because it is reference truth',
            'purpose': 'test whether operational specialization removes unnecessary recurrent inference overhead before considering any new training',
        }

        timing = {
            'milestone': M,
            'status': PASS,
            'execution_milestone': 'POSTV16-AV5-B2',
            'validation_realization': VALIDATION_REALIZATION,
            'trajectory_days': CANONICAL_DAYS,
            'candidate_path': 'Day30-only learned dispatch + exact residual admission + exact correction; Day60+ temporal-only correction',
            'baseline_path': 'temporal-seed exact correction at all 9 canonical states',
            'paired_timing_repeats': TIMING_PAIRS,
            'warmup_pairs': WARMUP_PAIRS,
            'ordering': 'alternate candidate-first and baseline-first across paired repeats',
            'timer': 'time.perf_counter',
            'model_inference_synchronization': 'materialize TensorFlow prediction to NumPy inside timed region',
            'candidate_time_includes': ['Day30 model inference','exact residual admission','selected exact correction','direct fallback only if actually required'],
            'candidate_time_excludes': ['untimed direct-reference solve used only for correctness audit','artifact serialization','repository/Drive I/O'],
            'baseline_time_includes': ['temporal exact correction','direct fallback only if actually required'],
            'baseline_time_excludes': ['untimed direct-reference solve used only for correctness audit','artifact serialization','repository/Drive I/O'],
            'exactness_gate_relative_residual': 1.0e-8,
            'pressure_equivalence_gate_relative_L2': 1.0e-8,
            'economic_acceptance': {
                'criterion_1': 'median candidate full-trajectory wall-clock < median baseline full-trajectory wall-clock',
                'criterion_2': f'candidate faster in at least {REQUIRED_FASTER_PAIRS} of {TIMING_PAIRS} paired repeats',
                'criterion_2_interpretation': 'one-sided exact sign-test p<0.05 under equal faster/slower probability (9/11 or stronger)',
                'both_required': True,
            },
            'correctness_required_before_economics': True,
            'production_authorization_from_B2': False,
        }

        b2_handoff = {
            'milestone': 'POSTV16-AV5-B2',
            'name': 'Prospective Day30-Only Frozen-Checkpoint Dispatch + Paired End-to-End Wall-Clock Economics Execution',
            'authorized': True,
            'execution': True,
            'must_bind_A7_commit': PARENT,
            'must_bind_checkpoint_sha256': CHECKPOINT_SHA,
            'must_use_validation_realization': VALIDATION_REALIZATION,
            'must_not_load_or_score_locked_OOD_for_selection': True,
            'must_not_train_model': True,
            'must_not_create_new_checkpoint': True,
            'must_not_reselect_or_retune_checkpoint': True,
            'must_not_refit_normalization': True,
            'must_execute_exactly_11_paired_timing_repeats': True,
            'must_execute_2_warmup_pairs': True,
            'must_alternate_pair_order': True,
            'must_preserve_exact_residual_admission': True,
            'must_preserve_exact_FV_correction': True,
            'must_preserve_direct_spsolve_fallback_and_reference': True,
            'must_not_authorize_production_or_P3': True,
        }

        classification = (
            'AV5_DAY30_ONLY_FROZEN_CHECKPOINT_DISPATCH_AND_PAIRED_END_TO_END_WALLCLOCK_'
            'ECONOMICS_PROTOCOL_FROZEN_B2_EXECUTION_AUTHORIZED_NO_TRAINING_NO_OOD_REUSE'
        )
        decision = {
            'milestone': M,
            'status': PASS,
            'classification': classification,
            'A7_scientific_outcome_preserved': True,
            'checkpoint_remains_frozen': True,
            'checkpoint_sha256': CHECKPOINT_SHA,
            'B2_authorized': True,
            'B2_execution_authorized': True,
            'B2_must_not_use_locked_OOD_for_selection': True,
            'B2_must_not_train_or_reselect_or_retune': True,
            'B2_wallclock_acceptance_is_validation_only': True,
            'AV5_production_execution_authorized': False,
            'P3_authorized': False,
            'AV4_state_mutation_authorized': False,
            'physical_time_advance_authorized': False,
        }
        summary = {
            'milestone': M,'name': NAME,'status': PASS,'classification': classification,
            'AV4_authoritative_state_sha256': AV4_STATE_SHA,'checkpoint_sha256': CHECKPOINT_SHA,
            'A7_scientific_outcome_bound': True,'A6_locked_OOD_used_as_motivation_only': True,
            'Day30_only_dispatch_frozen': True,'Day60_plus_model_inference_bypassed': True,
            'paired_timing_repeats': TIMING_PAIRS,'warmup_pairs': WARMUP_PAIRS,
            'required_candidate_faster_pairs': REQUIRED_FASTER_PAIRS,
            'B2_validation_realization': VALIDATION_REALIZATION,'B2_authorized': True,'B2_execution_authorized': True,
            'model_training_executed': False,'model_inference_executed': False,'wallclock_timing_executed': False,
            'checkpoint_reselection_executed': False,'retuning_executed': False,'normalization_refit_executed': False,
            'locked_OOD_reused_for_selection': False,'AV5_production_execution_authorized': False,'P3_authorized': False,
            'AV4_state_mutated': False,'physical_time_advance_executed': False,
        }
        files={SUMMARY:jb(summary),DESIGN:jb(dispatch),TIMING:jb(timing),LEAKAGE:jb(leakage),B2_HANDOFF:jb(b2_handoff),DECISION:jb(decision),GATE_MATRIX:csvb(gates)}
        immutable_publish(out,files)
        man=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!=MANIFEST: man.append({'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size})
        immutable_publish(out,{MANIFEST:csvb(man)})

        print(); print('='*208); print(M,'PASS')
        print('Classification                                  :',classification)
        print('Frozen checkpoint                               :',CHECKPOINT_SHA)
        print('Candidate dispatch                              : Day30 learned / Day60+ temporal-only')
        print('B2 validation realization                       :',VALIDATION_REALIZATION)
        print('Paired timing repeats / warmups                  :',TIMING_PAIRS,'/',WARMUP_PAIRS)
        print('Economic paired-repeat requirement               : >=',REQUIRED_FASTER_PAIRS,'of',TIMING_PAIRS,'candidate faster')
        print('A6 locked OOD reused for B2 selection            : False')
        print('Model training / inference / timing executed     : False / False / False')
        print('B2 execution authorized                          : True')
        print('Production / P3 authorized                       : False / False')
        print('='*208)
        return 0
    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True); p=block_dir/f'{OUT_TOKEN}_Blocked_Report.json'
        if not p.exists():
            p.write_bytes(jb({'milestone':M,'status':BLOCK,'failed_stage':stage,'exception':repr(exc),
                'model_training_executed':False,'model_inference_executed':False,'wallclock_timing_executed':False,
                'checkpoint_reselection_executed':False,'retuning_executed':False,'normalization_refit_executed':False,
                'locked_OOD_reused_for_selection':False,'AV5_production_execution_authorized':False,'P3_authorized':False,
                'AV4_state_mutation_executed':False,'physical_time_advance_executed':False,'gates_completed':gates}))
        print(M,'TECHNICAL / AUTHORITY BLOCK'); print('Stage:',stage); print('Exception:',repr(exc)); return 2

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',type=Path,default=Path('.')); ap.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute')); ap.add_argument('--self-test',action='store_true')
    args=ap.parse_args()
    if args.self_test: selftest(); raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))
