#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path
from typing import Any
M='POSTV16-AV4-PIVOT-GPU-HYB-G1-R4-R1'
NAME='Clean-Repository Native TensorFlow-2.20 100-Day Hybrid BL-DP GPU Replay Certification'
PASS='POSTV16AV4PIVOTGPUHYBG1R4R1_CLEAN_REPO_NATIVE_TF220_100DAY_GPU_REPLAY_CERTIFICATION_PASS_NO_PHYSICAL_TIME_ADVANCE'
BLOCK='POSTV16AV4PIVOTGPUHYBG1R4R1_RUNTIME_OR_FIDELITY_BLOCK_NO_PHYSICAL_TIME_ADVANCE'
BRANCH='postv16-av4-pivot'; PARENT='66f1c8ffabf46940bae3048818b32e1071082cbb'
RID='PAD_STREAM_V16_RC1_B92D52088D01078A'; BASE_AV4=Path('post_v16')/RID/'POSTV16_AV4_Dynamic_Flow_Coupling'
G1_R1_RUNNER='PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G1_R1_Frozen_Input_Bound_100Day_GPU_Replay_Certification.py'
G1_R1_RUNNER_SHA256='9d5402fb6d075ed7ce8ac65d9150dcffbdabe2f95b34b9e9f8a47eb451b32cb0'; G1_R1_RUNNER_BLOB='756fde8da6fb1f7cd538ac6a67a7844093c3c838'
R4_RUNNER='PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_Native_Colab_TF220_GPU_Replay_Certification.py'
R4_RUNNER_SHA256='7d369b24517126e27dd77c7b3211716de01ba9037c9ffcc6f5578f167e9dea39'; R4_RUNNER_BLOB='caed3e629c6b9407d8fd9c6d875d393a9f30f092'
R4_BLOCK_REL=BASE_AV4/'POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_BLOCKED'; R4_BLOCK_REPORT='POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_Blocked_Report.json'
R4_BLOCK_STATUS='POSTV16AV4PIVOTGPUHYBG1R4_RUNTIME_OR_FIDELITY_BLOCK_NO_PHYSICAL_TIME_ADVANCE'
TF_VERSION='2.20.0'; OUT_TOKEN='POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_R1'
OUT_REL=BASE_AV4/(OUT_TOKEN+'_CleanRepo_Native_TF220_100Day_GPU_Replay_Certification')
INNER_BLOCK_REL=BASE_AV4/(OUT_TOKEN+'_INNER_BLOCKED'); OUTER_BLOCK_REL=BASE_AV4/(OUT_TOKEN+'_BLOCKED')
SUMMARY=f'PAD_Stream_{OUT_TOKEN}_Summary.json'; DECISION=f'{OUT_TOKEN}_Decision_Contract.json'; MANIFEST=f'{OUT_TOKEN}_Artifact_Manifest.csv'; RUNTIME_AUDIT=f'{OUT_TOKEN}_Runtime_and_Harness_Audit.json'
class GateError(RuntimeError): pass
def sha256(path):
    h=hashlib.sha256(); f=path.open('rb')
    with f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()
def gt(root,*args): return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
def js(path): return json.loads(path.read_text(encoding='utf-8'))
def csv_rows(path):
    with path.open(newline='',encoding='utf-8') as f: return list(csv.DictReader(f))
def write_csv(path,rows):
    if not rows: path.write_text('',encoding='utf-8'); return
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows)
def import_exact(path,expected,module_name):
    if not path.is_file(): raise GateError(f'missing:{path}')
    actual=sha256(path)
    if actual!=expected: raise GateError(f'sha:{path.name}:{actual}:{expected}')
    spec=importlib.util.spec_from_file_location(module_name,path)
    if spec is None or spec.loader is None: raise GateError(f'cannot_import:{path}')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def native_runtime_probe():
    import tensorflow as tf
    return {'python':sys.version.split()[0],'tensorflow':tf.__version__,'tensorflow_file':tf.__file__,'gpus':[d.name for d in tf.config.list_physical_devices('GPU')]}
def selftest():
    assert TF_VERSION=='2.20.0' and PARENT=='66f1c8ffabf46940bae3048818b32e1071082cbb'
    print('POSTV16 GPU-HYB-G1-R4-R1 structural/clean-repo self-test: PASS')
def main(project_root,drive_root):
    root=project_root.resolve(); drive=drive_root.resolve(); out=drive/OUT_REL; outer=drive/OUTER_BLOCK_REL; inner=drive/INNER_BLOCK_REL; stage='preflight'
    try:
        print('='*180); print('POSTV16-AV4-PIVOT-GPU-HYB-G1-R4-R1 — CLEAN-REPO NATIVE TF2.20 GPU REPLAY CERTIFICATION'); print('R4 HARNESS REPAIR ONLY: NO TEMP FILE INSIDE GIT REPO.'); print('='*180)
        stage='repository_authority'
        if gt(root,'branch','--show-current')!=BRANCH: raise GateError('branch_exact')
        if gt(root,'rev-parse','HEAD^')!=PARENT: raise GateError(f"parent_exact:{gt(root,'rev-parse','HEAD^')}")
        if gt(root,'status','--porcelain')!='': raise GateError(f"repository_not_clean_before_replay:{gt(root,'status','--porcelain')}")
        r1=root/G1_R1_RUNNER; r4=root/R4_RUNNER
        if not r1.is_file() or sha256(r1)!=G1_R1_RUNNER_SHA256 or gt(root,'hash-object',str(r1))!=G1_R1_RUNNER_BLOB: raise GateError('G1_R1_runner_identity')
        if not r4.is_file() or sha256(r4)!=R4_RUNNER_SHA256 or gt(root,'hash-object',str(r4))!=R4_RUNNER_BLOB: raise GateError('R4_runner_identity')
        stage='prior_R4_block_authority'
        p=drive/R4_BLOCK_REL/R4_BLOCK_REPORT
        if not p.is_file(): raise GateError(f'R4_block_missing:{p}')
        rb=js(p)
        if rb.get('status')!=R4_BLOCK_STATUS: raise GateError(f"R4_block_status:{rb.get('status')}")
        if rb.get('failed_stage')!='exact_G1_R1_replay_under_native_tf220': raise GateError(f"R4_failed_stage:{rb.get('failed_stage')}")
        if 'G1_R1_under_native_TF220_exit:2' not in str(rb.get('exception','')): raise GateError(f"R4_unexpected_exception:{rb.get('exception')}")
        stage='native_tf220_GPU_runtime'; runtime=native_runtime_probe()
        if runtime['tensorflow']!=TF_VERSION: raise GateError(f"native_tensorflow_version:{runtime['tensorflow']}")
        if not runtime['gpus']: raise GateError('native_tensorflow_GPU_not_visible')
        stage='clean_repo_pre_inner_replay'; pre=gt(root,'status','--porcelain')
        if pre!='': raise GateError(f'repository_dirtied_before_inner_replay:{pre}')
        stage='exact_G1_R1_replay'
        mod=import_exact(r1,G1_R1_RUNNER_SHA256,'g1r1_clean_native_tf220')
        mod.PARENT=PARENT; mod.M=M; mod.NAME=NAME; mod.PASS=PASS; mod.BLOCK=BLOCK; mod.OUT_TOKEN=OUT_TOKEN; mod.OUT_REL=OUT_REL; mod.STAGE_REL=BASE_AV4/(OUT_TOKEN+'_STAGING'); mod.BLOCK_REL=INNER_BLOCK_REL
        mod.SUMMARY=SUMMARY; mod.AUDIT=f'{OUT_TOKEN}_Replay_Fidelity_Audit.json'; mod.REPAIR=f'{OUT_TOKEN}_Frozen_Input_Binding_Audit.json'; mod.DECISION=DECISION; mod.GATES=f'{OUT_TOKEN}_Final_Gate_Matrix.csv'; mod.MANIFEST=MANIFEST; mod.REPLAY_DIRNAME='E11_R2_GPU_REPLAY_NATIVE_TF220_CLEAN_REPO'
        os.environ['CUDA_VISIBLE_DEVICES']='0'; os.environ['TF_DETERMINISTIC_OPS']='1'; os.environ['TF_CUDNN_DETERMINISTIC']='1'
        rc=mod.main(root,drive)
        if rc!=0:
            ir=inner/f'{OUT_TOKEN}_Blocked_Report.json'; detail=js(ir) if ir.is_file() else {}
            raise GateError(f"inner_G1_R1_exit_2:stage={detail.get('failed_stage')!r};exception={detail.get('exception')!r};report={str(ir)!r}")
        stage='accepted_output_validation'; sp=out/SUMMARY; dp=out/DECISION; mp=out/MANIFEST
        for q in [sp,dp,mp]:
            if not q.is_file(): raise GateError(f'accepted_artifact_missing:{q.name}')
        s=js(sp)
        if s.get('status')!=PASS: raise GateError(f"accepted_status:{s.get('status')}")
        if s.get('TensorFlow_version')!=TF_VERSION: raise GateError(f"accepted_tensorflow:{s.get('TensorFlow_version')}")
        if s.get('GPU_HYB_G2_authorized') is not True: raise GateError('G2_not_authorized')
        if s.get('new_physical_time_advance_executed') is not False: raise GateError('physical_time_advanced')
        if s.get('P4_authorized') is not False: raise GateError('P4_not_false')
        audit={'milestone':M,'status':PASS,'repair_scope':'R4 temporary-helper repository cleanliness bug only','prior_R4_block_report_sha256':sha256(p),'R4_concrete_harness_bug':'R4 created .g1r4_native_tf220_helper.py inside repository root before invoking G1-R1, while G1-R1 requires git status --porcelain to be empty.','temporary_file_created_inside_repository_in_R4_R1':False,'repository_status_immediately_before_G1_R1':pre,'native_python':runtime['python'],'native_tensorflow':runtime['tensorflow'],'native_gpu_devices':runtime['gpus'],'G1_R1_replay_logic_changed':False,'physics_changed':False,'replay_tolerances_changed':False,'new_physical_time_advance':False}
        (out/RUNTIME_AUDIT).write_text(json.dumps(audit,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        s.update({'R4_R1_clean_repository_harness_repair_PASS':True,'native_python':runtime['python'],'native_tensorflow':runtime['tensorflow'],'native_tensorflow_GPU_visible':True,'G1_R1_replay_logic_changed_in_R4_R1':False,'physics_or_tolerance_changed_in_R4_R1':False})
        sp.write_text(json.dumps(s,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        old=csv_rows(mp); replay=[r for r in old if '/' in r['file']]; flat=[]
        for q in sorted(out.iterdir()):
            if q.is_file() and q.name!=MANIFEST: flat.append({'file':q.name,'sha256':sha256(q),'bytes':q.stat().st_size})
        write_csv(mp,flat+replay)
        print('='*180); print(M,'PASS')
        for k in ['native_python','native_tensorflow','route_code_exact','learned_screen_pass_exact','all_non_saturation_arrays_exact','nonlearned_fallback_saturation_exact','saturation_exact_array_equal','saturation_machine_precision_replay_PASS','saturation_max_abs','saturation_RMSE','saturation_relative_L2','GPU_HYB_G2_authorized','production_pressure_refresh_cadence_selected','new_physical_time_advance_executed','Day405_to_Day410_transport_remains_authorized','P4_authorized']:
            print(f'{k:60s}: {s.get(k)!r}')
        print('Output directory:',out); print('='*180); return 0
    except Exception as exc:
        outer.mkdir(parents=True,exist_ok=True)
        report={'milestone':M,'status':BLOCK,'failed_stage':stage,'exception':repr(exc),'inner_block_report_preserved':True,'GPU_HYB_G2_authorized':False,'new_physical_time_advance_executed':False,'AV4_authoritative_state_mutated':False,'P4_authorized':False}
        (outer/f'{OUT_TOKEN}_Blocked_Report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print(M,'RUNTIME / FIDELITY BLOCK'); print('Stage:',stage); print('Exception:',repr(exc)); return 2
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',type=Path,default=Path('.')); ap.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute')); ap.add_argument('--self-test',action='store_true'); a=ap.parse_args()
    if a.self_test: selftest(); raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
