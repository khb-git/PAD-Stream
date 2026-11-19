#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, subprocess, sys, types
from pathlib import Path

MILESTONE='POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R2'
BRANCH='postv16-av4-pivot'
PARENT='0a618e05ed0495ed63c312a8b7318b1653081d3a'
R1_RUNNER='PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R1_Footer_Patch_Assembly_Repair.py'
R1_GIT_BLOB='bd86efafbfddee343a6662643cf99af1b2cf0d55'
R2_TOKEN='POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R2'
R2_STATUS='POSTV16AV4PIVOTGPUHYBG4B4R2_BATCH_SHAPE_NUMERICAL_DIVERGENCE_AUDIT_PASS'
R2_BLOCK='POSTV16AV4PIVOTGPUHYBG4B4R2_TECHNICAL_OR_AUTHORITY_BLOCK'
R2_CLASSIFICATION='SINGLE_BATCH_VS_BATCH256_GPU_NUMERICAL_DIVERGENCE_PROPAGATION_AUDITED_NO_NEW_SCIENTIFIC_TOLERANCE_NO_PRODUCTION_AUTHORIZATION'
R1_STATUS='POSTV16AV4PIVOTGPUHYBG4B4R1_FOOTER_PATCH_ASSEMBLY_REPAIR_PASS'

class R2Error(RuntimeError): pass

def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()

def replace_once(source,old,new,label):
    n=source.count(old)
    if n!=1: raise R2Error(f'patch_anchor_{label}_count:{n}')
    return source.replace(old,new,1)

def import_exact(root,filename,expected_blob,module_name):
    p=root/filename
    if not p.is_file(): raise R2Error(f'missing_source:{filename}')
    actual=git(root,'hash-object',str(p))
    if actual!=expected_blob: raise R2Error(f'source_blob:{filename}:{actual}:{expected_blob}')
    spec=importlib.util.spec_from_file_location(module_name,p)
    if spec is None or spec.loader is None: raise R2Error(f'import_spec:{filename}')
    m=importlib.util.module_from_spec(spec); sys.modules[module_name]=m; spec.loader.exec_module(m); return m

def patched_r2_source(root):
    r1=import_exact(root,R1_RUNNER,R1_GIT_BLOB,'g4b4r2_r1_authority')
    s=r1.patched_r1_source(root)
    reps=[
      ('M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R1"',f'M="{MILESTONE}"','milestone'),
      (f'PASS="{R1_STATUS}"',f'PASS="{R2_STATUS}"','pass'),
      ('BLOCK="POSTV16AV4PIVOTGPUHYBG4B4R1_TECHNICAL_OR_AUTHORITY_BLOCK"',f'BLOCK="{R2_BLOCK}"','block'),
      ('PARENT="2b0c66584a11da496816b813d7c7ca9e47014f00"',f'PARENT="{PARENT}"','parent'),
      ('OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R1"',f'OUT_TOKEN="{R2_TOKEN}"','token'),
      ('print("POSTV16 GPU-HYB-G4-B4-R1 structural/patch self-test: PASS")','print("POSTV16 GPU-HYB-G4-B4-R2 structural/patch self-test: PASS")','selftest'),
      ('gate("parent_is_G4_B4_failed_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))','gate("parent_is_G4_B4_R1_block_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))','parentgate'),
    ]
    for a,b,l in reps: s=replace_once(s,a,b,l)
    old=(
      'print("G4-B4-R1 — FOOTER PATCH-ASSEMBLY REPAIR / SINGLE-BATCH GPU PROFILE PIPELINE")\n'
      '        print("REPAIRS ONLY THE B4 GENERATED-SOURCE FOOTER JOIN. THE B4 SINGLE-BATCH GPU CANDIDATE, SHADOW BATCH-256 VALIDATION, ROUTING, MASS PIPELINE, MAPBACK, AND CAPILLARY PHYSICS ARE UNCHANGED.")\n'
      '        print("FAILED B4 COMMIT 2b0c66584a11da496816b813d7c7ca9e47014f00 REMAINS IMMUTABLE.")')
    new=(
      'print("G4-B4-R2 — BATCH-SHAPE NUMERICAL DIVERGENCE PROPAGATION AUDIT")\n'
      '        print("DIAGNOSTIC ONLY. SINGLE-BATCH AND FROZEN BATCH-256 HYBRID10 EXECUTIONS ARE CARRIED THROUGH THE SAME CONSERVATIVE MASS PIPELINE FOR SIDE-BY-SIDE COMPARISON.")\n'
      '        print("NO RAW-PREDICTION TOLERANCE IS RELAXED. NO NEW SCIENTIFIC THRESHOLD. NO PRODUCTION AUTHORIZATION.")')
    s=replace_once(s,old,new,'banner')

    anchor='''        b3r1d=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_R1_Route_Economics_Instrumentation")'''
    insert='''        b4r1_block_path=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R1_BLOCKED")/"POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R1_Blocked_Report.json"
        gate("B4_R1_block_present",b4r1_block_path.is_file(),str(b4r1_block_path))
        b4r1block=js(b4r1_block_path)
        gate("B4_R1_block_status_exact",b4r1block.get("status")=="POSTV16AV4PIVOTGPUHYBG4B4R1_TECHNICAL_OR_AUTHORITY_BLOCK",b4r1block.get("status"))
        gate("B4_R1_block_stage_exact",b4r1block.get("failed_stage")=="shadow_batch256_profile_equivalence",b4r1block.get("failed_stage"))
        gate("B4_R1_block_exception_exact","parent_prediction_float32_execution_equivalence" in str(b4r1block.get("exception","")),b4r1block.get("exception"))
        b4r1_failed=[g for g in b4r1block.get("gates",[]) if g.get("pass") is False]
        gate("B4_R1_exactly_one_failed_gate",len(b4r1_failed)==1,b4r1_failed)
        gate("B4_R1_failed_gate_exact",len(b4r1_failed)==1 and b4r1_failed[0].get("gate")=="parent_prediction_float32_execution_equivalence",b4r1_failed[0] if b4r1_failed else None)

        b3r1d=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_R1_Route_Economics_Instrumentation")'''
    s=replace_once(s,anchor,insert,'r1block')

    old='''        gate("parent_prediction_float32_execution_equivalence",
             parent_prediction_max_abs<=float32_execution_tol,
             (parent_prediction_max_abs,float32_execution_tol))
        gate("child_prediction_float32_execution_equivalence",
             child_prediction_max_abs<=float32_execution_tol,
             (child_prediction_max_abs,float32_execution_tol))'''
    new='''        raw_prediction_execution_equivalent=bool(parent_prediction_max_abs<=float32_execution_tol and child_prediction_max_abs<=float32_execution_tol)
        gate("B4_R1_parent_prediction_divergence_reproduced",parent_prediction_max_abs>float32_execution_tol,(parent_prediction_max_abs,float32_execution_tol))
        gate("single_batch_parent_prediction_difference_finite",np.isfinite(parent_prediction_max_abs),parent_prediction_max_abs)
        gate("single_batch_child_prediction_difference_finite",np.isfinite(child_prediction_max_abs),child_prediction_max_abs)'''
    s=replace_once(s,old,new,'predaudit')

    old='''        gate("parent_profile_float32_execution_equivalence",
             parent_profile_max_abs<=float32_execution_tol,
             (parent_profile_max_abs,float32_execution_tol))
        gate("child_profile_float32_execution_equivalence",
             child_profile_max_abs<=float32_execution_tol,
             (child_profile_max_abs,float32_execution_tol))'''
    new='''        projected_profile_execution_equivalent=bool(parent_profile_max_abs<=float32_execution_tol and child_profile_max_abs<=float32_execution_tol)
        gate("single_batch_parent_profile_difference_finite",np.isfinite(parent_profile_max_abs),parent_profile_max_abs)
        gate("single_batch_child_profile_difference_finite",np.isfinite(child_profile_max_abs),child_profile_max_abs)'''
    s=replace_once(s,old,new,'profileaudit')

    anchor='''        stage="shadow_B2_scalar_projection_correction_after_candidate"'''
    insert='''        stage="batch_shape_downstream_divergence_audit"
        baseline_parent_prof=np.stack([base_parent_profiles[int(i)] for i in eligible],axis=0)
        baseline_child_prof=np.stack([base_child_profiles[int(i)] for i in eligible],axis=0)
        baseline_pmm=mass_only_projection(baseline_parent_prof)
        baseline_cmm=mass_only_projection(baseline_child_prof)
        baseline_raw=old_mass[eligible]+(baseline_cmm-baseline_pmm)
        baseline_cap=np.asarray(e37a.cv_mass_from_saturation(physics,np.full_like(baseline_raw,float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)),coeff_h),dtype=np.float64)
        baseline_mm,baseline_lam,baseline_box_closure=batch_box_project(baseline_raw,hybrid_target_i,baseline_cap)
        baseline_ss=np.asarray(e37a.invert_cv_mass_to_saturation(physics,baseline_mm,coeff_h),dtype=np.float64)
        baseline_mixed_mass=np.empty_like(old_mass,dtype=np.float64); baseline_mixed_sat=np.empty_like(old_sat,dtype=np.float64)
        baseline_mixed_mass[fallback]=np.asarray(exact_subset["new_mass"],float); baseline_mixed_sat[fallback]=np.asarray(exact_subset["new_saturation"],float)
        baseline_mixed_mass[eligible]=baseline_mm; baseline_mixed_sat[eligible]=baseline_ss
        baseline_mapback=e37a.map_control_volume_increment_to_grid(physics,parent_sat,old_sat,baseline_mixed_sat,old_mass,baseline_mixed_mass,epoch["geometry"],pressure,p_ref,cell_pv,target_final)
        baseline_capillary=physics.conservative_capillary_mass_redistribution(transport_saturation=np.asarray(baseline_mapback["corrected_saturation"],float),permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,cell_pore_volume_m3=cell_pv,dt_seconds=dt*DAY_TO_S)
        baseline_box_closure_max_abs=float(np.max(np.abs(baseline_box_closure)))
        baseline_box_closure_tol=max(1e-8,1e-12*max(float(np.max(np.abs(hybrid_target_i))),1.0))
        gate("baseline_batch256_box_closure_existing_B3_criterion",baseline_box_closure_max_abs<=baseline_box_closure_tol,(baseline_box_closure_max_abs,baseline_box_closure_tol))
        batch_shape_parent_mass_projection_max_abs_kg=float(np.max(np.abs(pmm-baseline_pmm)))
        batch_shape_child_mass_projection_max_abs_kg=float(np.max(np.abs(cmm-baseline_cmm)))
        batch_shape_corrected_cv_mass_max_abs_kg=float(np.max(np.abs(batch_mm-baseline_mm)))
        batch_shape_corrected_cv_saturation_max_abs=float(np.max(np.abs(batch_ss-baseline_ss)))
        batch_shape_grid_mapback_mass_max_abs_kg=float(np.max(np.abs(np.asarray(candidate_mapback["corrected_mass"],float)-np.asarray(baseline_mapback["corrected_mass"],float))))
        batch_shape_grid_mapback_saturation_max_abs=float(np.max(np.abs(np.asarray(candidate_mapback["corrected_saturation"],float)-np.asarray(baseline_mapback["corrected_saturation"],float))))
        batch_shape_capillary_saturation_max_abs=float(np.max(np.abs(np.asarray(candidate_capillary["corrected"],float)-np.asarray(baseline_capillary["corrected"],float))))
        batch_shape_mapback_total_mass_difference_kg=float(candidate_mapback["mapped_final_mass_kg"]-baseline_mapback["mapped_final_mass_kg"])
        batch_shape_capillary_final_mass_difference_kg=float(candidate_capillary["final_mass_state_kg"]-baseline_capillary["final_mass_state_kg"])
        candidate_vs_baseline_cv_sat_relL2=float(np.linalg.norm((batch_ss-baseline_ss).ravel())/max(float(np.linalg.norm(baseline_ss.ravel())),1e-30))
        candidate_vs_baseline_grid_sat_relL2=float(np.linalg.norm((np.asarray(candidate_mapback["corrected_saturation"],float)-np.asarray(baseline_mapback["corrected_saturation"],float)).ravel())/max(float(np.linalg.norm(np.asarray(baseline_mapback["corrected_saturation"],float).ravel())),1e-30))
        candidate_vs_baseline_capillary_sat_relL2=float(np.linalg.norm((np.asarray(candidate_capillary["corrected"],float)-np.asarray(baseline_capillary["corrected"],float)).ravel())/max(float(np.linalg.norm(np.asarray(baseline_capillary["corrected"],float).ravel())),1e-30))
        gate("batch_shape_downstream_metrics_finite",all(np.isfinite(x) for x in [batch_shape_parent_mass_projection_max_abs_kg,batch_shape_child_mass_projection_max_abs_kg,batch_shape_corrected_cv_mass_max_abs_kg,batch_shape_corrected_cv_saturation_max_abs,batch_shape_grid_mapback_mass_max_abs_kg,batch_shape_grid_mapback_saturation_max_abs,batch_shape_capillary_saturation_max_abs,batch_shape_mapback_total_mass_difference_kg,batch_shape_capillary_final_mass_difference_kg,candidate_vs_baseline_cv_sat_relL2,candidate_vs_baseline_grid_sat_relL2,candidate_vs_baseline_capillary_sat_relL2]))
        batch_shape_exact_end_state_identity=bool(batch_shape_corrected_cv_mass_max_abs_kg==0.0 and batch_shape_corrected_cv_saturation_max_abs==0.0 and batch_shape_grid_mapback_mass_max_abs_kg==0.0 and batch_shape_grid_mapback_saturation_max_abs==0.0 and batch_shape_capillary_saturation_max_abs==0.0)

        stage="shadow_B2_scalar_projection_correction_after_candidate"'''
    s=replace_once(s,anchor,insert,'downstream')

    old='''            "classification":"G4_B4_SINGLE_BATCH_GPU_PROFILE_PIPELINE_PRESERVED_FOOTER_PATCH_ASSEMBLY_SYNTAX_REPAIRED",
            "B4_failed_commit_bound":True,
            "B4_R1_footer_patch_assembly_repair_only":True,'''
    new=f'''            "classification":"{R2_CLASSIFICATION}",
            "B4_failed_commit_bound":True,
            "B4_R1_blocked_predecessor_bound":True,
            "B4_R2_batch_shape_divergence_audit_only":True,
            "raw_prediction_execution_equivalent_to_batch256":raw_prediction_execution_equivalent,
            "projected_profile_execution_equivalent_to_batch256":projected_profile_execution_equivalent,
            "batch_shape_exact_end_state_identity":batch_shape_exact_end_state_identity,
            "batch_shape_parent_mass_projection_max_abs_kg":batch_shape_parent_mass_projection_max_abs_kg,
            "batch_shape_child_mass_projection_max_abs_kg":batch_shape_child_mass_projection_max_abs_kg,
            "batch_shape_corrected_cv_mass_max_abs_kg":batch_shape_corrected_cv_mass_max_abs_kg,
            "batch_shape_corrected_cv_saturation_max_abs":batch_shape_corrected_cv_saturation_max_abs,
            "batch_shape_grid_mapback_mass_max_abs_kg":batch_shape_grid_mapback_mass_max_abs_kg,
            "batch_shape_grid_mapback_saturation_max_abs":batch_shape_grid_mapback_saturation_max_abs,
            "batch_shape_capillary_saturation_max_abs":batch_shape_capillary_saturation_max_abs,
            "batch_shape_mapback_total_mass_difference_kg":batch_shape_mapback_total_mass_difference_kg,
            "batch_shape_capillary_final_mass_difference_kg":batch_shape_capillary_final_mass_difference_kg,
            "candidate_vs_baseline_cv_sat_relL2":candidate_vs_baseline_cv_sat_relL2,
            "candidate_vs_baseline_grid_sat_relL2":candidate_vs_baseline_grid_sat_relL2,
            "candidate_vs_baseline_capillary_sat_relL2":candidate_vs_baseline_capillary_sat_relL2,
            "new_batch_shape_acceptance_tolerance_defined":False,
            "single_batch_production_equivalence_authorized":False,
            "B4_R3_exact_output_preserving_batch256_optimization_probe_authorized":True,'''
    s=replace_once(s,old,new,'summary')
    s=replace_once(s,'            "B5_CPU_GPU_overlap_pipeline_probe_authorized":True,','            "B5_CPU_GPU_overlap_pipeline_probe_authorized":False,','b5')
    s=replace_once(s,'        print("B5 CPU/GPU overlap pipeline probe                     : AUTHORIZED")','        print("B4-R2 batch-shape divergence audit                    : COMPLETE")\n        print("Raw prediction execution-equivalent to batch256       :",raw_prediction_execution_equivalent)\n        print("Projected profile execution-equivalent to batch256    :",projected_profile_execution_equivalent)\n        print("Corrected CV saturation max abs difference             :",batch_shape_corrected_cv_saturation_max_abs)\n        print("Grid mapback saturation max abs difference             :",batch_shape_grid_mapback_saturation_max_abs)\n        print("Capillary saturation max abs difference                :",batch_shape_capillary_saturation_max_abs)\n        print("Exact end-state identity                               :",batch_shape_exact_end_state_identity)\n        print("B5 CPU/GPU overlap pipeline probe                      : NOT AUTHORIZED")\n        print("B4-R3 exact-output-preserving batch256 optimization    : AUTHORIZED")','footer')
    return s

def repository_preflight(root):
    branch=git(root,'branch','--show-current'); head=git(root,'rev-parse','HEAD'); par=git(root,'rev-parse','HEAD^'); clean=git(root,'status','--porcelain')==''
    p=root/R1_RUNNER; bl=git(root,'hash-object',str(p)) if p.is_file() else 'MISSING'
    print('--- G4-B4-R2 REPOSITORY IDENTITY ---'); print('Branch:',branch); print('HEAD  :',head); print('HEAD^ :',par); print('Clean :',clean); print('B4-R1 runner blob:',bl); print('Expected         :',R1_GIT_BLOB)
    if branch!=BRANCH: raise R2Error(f'branch:{branch}:{BRANCH}')
    if par!=PARENT: raise R2Error(f'parent:{par}:{PARENT}')
    if not clean: raise R2Error('repository_not_clean')
    if bl!=R1_GIT_BLOB: raise R2Error(f'B4R1_blob:{bl}:{R1_GIT_BLOB}')

def load_patched_module(root):
    src=patched_r2_source(root); compile(src,f'<{R2_TOKEN}_patched_B4_R1>','exec')
    m=types.ModuleType('g4_b4_r2_batch_shape_audit'); m.__file__=str(root/R1_RUNNER); m.__package__=None; sys.modules[m.__name__]=m; exec(compile(src,m.__file__,'exec'),m.__dict__); return m

def self_test(root):
    repository_preflight(root); src=patched_r2_source(root)
    for marker in ['gate("parent_prediction_float32_execution_equivalence"','gate("child_prediction_float32_execution_equivalence"','gate("parent_profile_float32_execution_equivalence"','gate("child_profile_float32_execution_equivalence"']:
        if marker in src: raise R2Error(f'obsolete_equivalence_gate_survived:{marker}')
    for marker in ['gate("B4_R1_parent_prediction_divergence_reproduced"','stage="batch_shape_downstream_divergence_audit"','"new_batch_shape_acceptance_tolerance_defined":False','"single_batch_production_equivalence_authorized":False','"B4_R3_exact_output_preserving_batch256_optimization_probe_authorized":True','"B5_CPU_GPU_overlap_pipeline_probe_authorized":False']:
        if marker not in src: raise R2Error(f'missing_R2_marker:{marker}')
    compile(src,f'<{R2_TOKEN}_structural_selftest>','exec'); m=load_patched_module(root)
    if m.OUT_TOKEN!=R2_TOKEN: raise R2Error(f'patched_OUT_TOKEN:{m.OUT_TOKEN}')
    if m.PASS!=R2_STATUS: raise R2Error(f'patched_PASS:{m.PASS}')
    print('POSTV16 GPU-HYB-G4-B4-R2 structural/patch self-test: PASS')

def main(root,drive):
    root=root.resolve(); drive=drive.resolve(); repository_preflight(root); return int(load_patched_module(root).main(root,drive))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',type=Path,default=Path('.')); ap.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute')); ap.add_argument('--self-test',action='store_true'); args=ap.parse_args()
    try:
        if args.self_test: self_test(args.project_root.resolve()); raise SystemExit(0)
        raise SystemExit(main(args.project_root,args.drive_root))
    except Exception as exc:
        print(MILESTONE,'WRAPPER BLOCK'); print('Exception:',repr(exc)); raise
