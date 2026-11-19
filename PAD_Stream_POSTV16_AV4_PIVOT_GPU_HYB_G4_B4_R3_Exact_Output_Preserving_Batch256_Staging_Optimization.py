#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, subprocess, sys, types
from pathlib import Path

MILESTONE='POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R3'
BRANCH='postv16-av4-pivot'
PARENT='eec16bfd57987ba9c9c8d04c853d86c83a53ce8f'

R2_RUNNER='PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R2_Batch_Shape_Numerical_Divergence_Audit.py'
R2_GIT_BLOB='7ee4702835f0f6944c93dd576be7808b8b046cf9'

R3_TOKEN='POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3'
R3_STATUS='POSTV16AV4PIVOTGPUHYBG4B4R3_EXACT_OUTPUT_PRESERVING_BATCH256_STAGING_OPTIMIZATION_PASS'
R3_BLOCK='POSTV16AV4PIVOTGPUHYBG4B4R3_TECHNICAL_OR_AUTHORITY_BLOCK'
R3_CLASSIFICATION='FROZEN_BATCH256_HYBRID10_OUTPUT_EXACT_CACHED_XI_STAGING_SINGLE_SCREEN_PROJECTION_PIPELINE_CERTIFIED'
R2_STATUS='POSTV16AV4PIVOTGPUHYBG4B4R2_BATCH_SHAPE_NUMERICAL_DIVERGENCE_AUDIT_PASS'

class R3Error(RuntimeError): pass

def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()

def replace_once(source,old,new,label):
    n=source.count(old)
    if n!=1: raise R3Error(f'patch_anchor_{label}_count:{n}')
    return source.replace(old,new,1)

def replace_between(source,start,end,replacement,label):
    i=source.find(start)
    if i<0: raise R3Error(f'patch_start_{label}_missing')
    if source.find(start,i+1)>=0: raise R3Error(f'patch_start_{label}_not_unique')
    j=source.find(end,i+len(start))
    if j<0: raise R3Error(f'patch_end_{label}_missing')
    if source.find(end,j+1)>=0: raise R3Error(f'patch_end_{label}_not_unique')
    return source[:i]+replacement+source[j:]

def import_exact(root,filename,expected_blob,module_name):
    p=root/filename
    if not p.is_file(): raise R3Error(f'missing_source:{filename}')
    actual=git(root,'hash-object',str(p))
    if actual!=expected_blob: raise R3Error(f'source_blob:{filename}:{actual}:{expected_blob}')
    spec=importlib.util.spec_from_file_location(module_name,p)
    if spec is None or spec.loader is None: raise R3Error(f'import_spec:{filename}')
    m=importlib.util.module_from_spec(spec); sys.modules[module_name]=m; spec.loader.exec_module(m); return m

def patched_r3_source(root):
    r2=import_exact(root,R2_RUNNER,R2_GIT_BLOB,'g4b4r3_r2_authority')
    s=r2.patched_r2_source(root)

    reps=[
      ('M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R2"',f'M="{MILESTONE}"','milestone'),
      (f'PASS="{R2_STATUS}"',f'PASS="{R3_STATUS}"','pass'),
      ('BLOCK="POSTV16AV4PIVOTGPUHYBG4B4R2_TECHNICAL_OR_AUTHORITY_BLOCK"',f'BLOCK="{R3_BLOCK}"','block'),
      ('PARENT="0a618e05ed0495ed63c312a8b7318b1653081d3a"',f'PARENT="{PARENT}"','parent'),
      ('OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R2"',f'OUT_TOKEN="{R3_TOKEN}"','token'),
      ('print("POSTV16 GPU-HYB-G4-B4-R2 structural/patch self-test: PASS")','print("POSTV16 GPU-HYB-G4-B4-R3 structural/patch self-test: PASS")','selftest'),
      ('gate("parent_is_G4_B4_R1_block_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))','gate("parent_is_G4_B4_R2_audit_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))','parentgate'),
    ]
    for a,b,l in reps: s=replace_once(s,a,b,l)

    old=(
      'print("G4-B4-R2 — BATCH-SHAPE NUMERICAL DIVERGENCE PROPAGATION AUDIT")\n'
      '        print("DIAGNOSTIC ONLY. SINGLE-BATCH AND FROZEN BATCH-256 HYBRID10 EXECUTIONS ARE CARRIED THROUGH THE SAME CONSERVATIVE MASS PIPELINE FOR SIDE-BY-SIDE COMPARISON.")\n'
      '        print("NO RAW-PREDICTION TOLERANCE IS RELAXED. NO NEW SCIENTIFIC THRESHOLD. NO PRODUCTION AUTHORIZATION.")')
    new=(
      'print("G4-B4-R3 — EXACT-OUTPUT-PRESERVING BATCH-256 STAGING OPTIMIZATION")\n'
      '        print("FROZEN NUMERICAL AUTHORITY: SAME 256+REMAINDER GPU BATCH SHAPES, SAME HYBRID10 WEIGHTS, SAME ROUTING, SAME CONSERVATIVE MASS PIPELINE.")\n'
      '        print("OPTIMIZES ONLY XI INPUT STAGING AND DUPLICATE SCREEN/PROJECTION WORK. RAW PREDICTIONS AND FINAL STATE MUST BE EXACTLY IDENTICAL TO THE ORIGINAL BATCH-256 PATH.")')
    s=replace_once(s,old,new,'banner')

    authority_anchor='''        b4r1_block_path=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R1_BLOCKED")/"POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R1_Blocked_Report.json"'''
    authority_insert='''        b4r2d=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R2_Route_Economics_Instrumentation")
        b4r2_summary_name="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R2_Summary.json"
        b4r2_manifest_name="POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R2_Artifact_Manifest.csv"
        gate("B4_R2_summary_present",(b4r2d/b4r2_summary_name).is_file(),str(b4r2d/b4r2_summary_name))
        b4r2=js(b4r2d/b4r2_summary_name)
        gate("B4_R2_status_exact",b4r2.get("status")=="POSTV16AV4PIVOTGPUHYBG4B4R2_BATCH_SHAPE_NUMERICAL_DIVERGENCE_AUDIT_PASS",b4r2.get("status"))
        gate("B4_R2_manifest_present",(b4r2d/b4r2_manifest_name).is_file(),str(b4r2d/b4r2_manifest_name))
        verify_manifest(b4r2d,b4r2_manifest_name)
        gate("B4_R2_single_batch_not_equivalent",b4r2.get("batch_shape_exact_end_state_identity") is False,b4r2.get("batch_shape_exact_end_state_identity"))
        gate("B4_R2_single_batch_not_authorized",b4r2.get("single_batch_production_equivalence_authorized") is False)
        gate("B4_R2_R3_authorized",b4r2.get("B4_R3_exact_output_preserving_batch256_optimization_probe_authorized") is True)

        b4r1_block_path=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R1_BLOCKED")/"POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R1_Blocked_Report.json"'''
    s=replace_once(s,authority_anchor,authority_insert,'r2authority')

    profile_block='''        xi32=np.asarray(xi,dtype=np.float32)
        xi_base=tf.constant(xi32[:,None],tf.float32)
        xi_batch_cache={}

        def cached_xi_batch(n:int):
            n=int(n)
            if n not in xi_batch_cache:
                xi_batch_cache[n]=tf.repeat(xi_base[None,:,:],n,axis=0)
            return xi_batch_cache[n]

        def infer_staged_batch256(cond_arr):
            cond_arr=np.asarray(cond_arr,dtype=np.float32)
            cond_tensor=tf.constant(cond_arr,tf.float32)
            n=int(cond_arr.shape[0])
            out=np.empty((n,len(xi32)),dtype=np.float32)
            calls=0
            for start in range(0,n,256):
                end=min(start+256,n)
                c=cond_tensor[start:end]
                xb=cached_xi_batch(end-start)
                y=model([xb,c],training=False)[:,:,0]
                out[start:end]=np.asarray(y.numpy(),dtype=np.float32)
                calls+=1
            return out,calls

        def screen_and_project_once(y,p,state,tau_nodes):
            yy=np.asarray(y,dtype=np.float64)
            finite=bool(np.all(np.isfinite(yy)))
            lower=float(p["swc"]); upper=1.0-float(p["sor"])
            bounds=finite and bool(np.all(yy>=lower) and np.all(yy<=upper))
            injection_abs=abs(float(yy[0])-upper) if finite else float("inf")
            front_abs=abs(float(yy[-1])-float(state["Sw_star"])) if finite else float("inf")
            char=float(np.sqrt(np.mean(np.square(
                physics.dfw_dsw(yy,adapter.teacher_params(p))[1:-1]
                -xi[1:-1]*float(state["characteristic_speed"])
            )))) if finite else float("inf")
            inventory=abs(float(state["xD_star"])*float(np.trapezoid(yy-lower,xi))-float(state["tD"])) if finite else float("inf")
            inc=np.diff(yy) if finite else np.asarray([float("inf")])
            mono_fraction=float(np.count_nonzero(inc>0.0)/inc.size) if finite else 1.0
            tau_local=np.asarray(tau_nodes,dtype=np.float64)
            projected=adapter.project_fan_to_pollock_nodes(
                tau_nodes=tau_local,state=state,fan_xi=xi,fan_sw=yy,swc=lower
            ) if finite else np.full(tau_local.shape,np.nan,dtype=np.float64)
            downstream=tau_local>float(state["tau_star"])
            downstream_exact=bool(np.all(projected[downstream]==lower)) if finite and np.any(downstream) else finite
            failures=[]
            if not finite: failures.append("nonfinite")
            if not bounds: failures.append("saturation_bounds")
            if injection_abs>float(screen["injection_endpoint_abs_max"]): failures.append("injection_endpoint")
            if front_abs>float(screen["front_endpoint_abs_max"]): failures.append("front_endpoint")
            if char>float(screen["characteristic_RMSE_max"]): failures.append("characteristic")
            if inventory>float(screen["inventory_abs_max"]): failures.append("inventory")
            if mono_fraction>float(screen["monotonic_violation_fraction_max"]): failures.append("monotonicity")
            if not downstream_exact: failures.append("downstream_initial_state")
            failures=list(dict.fromkeys(failures))
            return len(failures)==0,{
                "failures":failures,"finite":finite,"bounds":bounds,
                "injection_endpoint_abs":injection_abs,"front_endpoint_abs":front_abs,
                "characteristic_RMSE":char,"inventory_abs":inventory,
                "monotonic_violation_fraction":mono_fraction,
                "downstream_initial_state_exact":downstream_exact,
            },np.asarray(projected,dtype=np.float64)

        def build_candidate_profile(day:float):
            tprep=time.perf_counter()
            xstar=(float(day)/terminal_days)*speed
            clocks=np.asarray([e11.classify_clock(float(x)) for x in xstar],dtype="U32")
            idx=np.flatnonzero(clocks=="LEARNED_WINDOW")
            cond=[];states=[]
            for i in idx:
                st=adapter.physical_time_state(elapsed_time=day,tau_end=float(terminal_days[i]),
                    characteristic_speed=speed,Sw_star=swstar)
                states.append(st)
                cond.append(adapter.conditioning_vector("HYBRID10",params,st))
            cond_arr=np.asarray(cond,dtype=np.float32)
            prep=float(time.perf_counter()-tprep)

            tinfer=time.perf_counter()
            pred,calls=infer_staged_batch256(cond_arr) if idx.size else (np.empty((0,len(xi)),np.float32),0)
            infer_seconds=float(time.perf_counter()-tinfer)

            tscreen=time.perf_counter()
            profiles={};reject={}
            for local,i in enumerate(idx):
                ok,sm,projected=screen_and_project_once(pred[local],params,states[local],tau[i]/DAY_TO_S)
                if ok:
                    profiles[int(i)]=projected
                else:
                    for reason in sm["failures"]:
                        reject[reason]=reject.get(reason,0)+1
            screen_seconds=float(time.perf_counter()-tscreen)
            return profiles,clocks,reject,{
                "conditioning_seconds":prep,
                "GPU_inference_seconds":infer_seconds,
                "screen_and_node_projection_seconds":screen_seconds,
                "total_profile_seconds":prep+infer_seconds+screen_seconds,
                "learned_window_count":int(idx.size),
                "accepted_profile_count":int(len(profiles)),
                "GPU_call_count":int(calls),
            },pred,idx

        parent_fast=build_candidate_profile(100.0)
        parent_profiles,parent_clocks,parent_reject,parent_profile_time,parent_pred,parent_idx=parent_fast

        child_times=[]; child_output=None
        for _ in range(TIMING_REPEATS):
            child_output=build_candidate_profile(100.0+dt)
            child_times.append(child_output[3])
        child_profiles,child_clocks,child_reject,child_fast_time,child_pred,child_idx=child_output
        child_total_median=float(statistics.median([x["total_profile_seconds"] for x in child_times]))
        child_condition_median=float(statistics.median([x["conditioning_seconds"] for x in child_times]))
        child_infer_median=float(statistics.median([x["GPU_inference_seconds"] for x in child_times]))
        child_screen_median=float(statistics.median([x["screen_and_node_projection_seconds"] for x in child_times]))
        child_gpu_call_count=int(child_fast_time["GPU_call_count"])
        child_learned_window_count=int(child_fast_time["learned_window_count"])
        gate("R3_candidate_retains_two_batch256_shape_calls",child_gpu_call_count==2,(child_gpu_call_count,child_learned_window_count))

        eligible=np.asarray(sorted(set(parent_profiles).intersection(child_profiles)),dtype=np.int64)
'''
    s=replace_between(s,'        xi32=np.asarray(xi,dtype=np.float32)','        eligible=np.asarray(sorted(set(parent_profiles).intersection(child_profiles)),dtype=np.int64)',profile_block,'candidate_profile_pipeline')

    shadow_block='''        stage="exact_output_batch256_shadow_after_candidate"

        def build_baseline_profile(day:float):
            tprep=time.perf_counter()
            xstar=(float(day)/terminal_days)*speed
            clocks=np.asarray([e11.classify_clock(float(x)) for x in xstar],dtype="U32")
            idx=np.flatnonzero(clocks=="LEARNED_WINDOW")
            cond=[];states=[]
            for i in idx:
                st=adapter.physical_time_state(elapsed_time=day,tau_end=float(terminal_days[i]),
                    characteristic_speed=speed,Sw_star=swstar)
                states.append(st)
                cond.append(adapter.conditioning_vector("HYBRID10",params,st))
            cond_arr=np.asarray(cond,dtype=np.float32)
            prep=float(time.perf_counter()-tprep)

            tinfer=time.perf_counter()
            pred=e9r1.infer(tf,model,xi32,cond_arr,batch=256) if idx.size else np.empty((0,len(xi)),np.float32)
            infer_seconds=float(time.perf_counter()-tinfer)

            tscreen=time.perf_counter()
            profiles={};reject={}
            for local,i in enumerate(idx):
                ok,sm=e11.screen_fan_prediction(pred[local],params,states[local],xi,tau[i]/DAY_TO_S,physics,adapter,screen)
                if ok:
                    profiles[int(i)]=adapter.project_fan_to_pollock_nodes(
                        tau_nodes=tau[i]/DAY_TO_S,state=states[local],fan_xi=xi,
                        fan_sw=pred[local],swc=float(params["swc"])).astype(np.float64)
                else:
                    for reason in sm["failures"]:
                        reject[reason]=reject.get(reason,0)+1
            screen_seconds=float(time.perf_counter()-tscreen)
            return profiles,clocks,reject,{
                "conditioning_seconds":prep,"GPU_inference_seconds":infer_seconds,
                "screen_and_node_projection_seconds":screen_seconds,
                "total_profile_seconds":prep+infer_seconds+screen_seconds,
                "GPU_call_count":int((idx.size+255)//256),
            },pred,idx

        base_parent=build_baseline_profile(100.0)
        baseline_child_times=[]; base_child=None
        for _ in range(TIMING_REPEATS):
            base_child=build_baseline_profile(100.0+dt)
            baseline_child_times.append(base_child[3])

        base_parent_profiles,base_parent_clocks,base_parent_reject,base_parent_time,base_parent_pred,base_parent_idx=base_parent
        base_child_profiles,base_child_clocks,base_child_reject,base_child_time,base_child_pred,base_child_idx=base_child
        baseline256_child_total_median=float(statistics.median([x["total_profile_seconds"] for x in baseline_child_times]))
        baseline256_child_infer_median=float(statistics.median([x["GPU_inference_seconds"] for x in baseline_child_times]))
        baseline256_child_screen_median=float(statistics.median([x["screen_and_node_projection_seconds"] for x in baseline_child_times]))

        gate("R3_parent_clock_exact",np.array_equal(parent_clocks,base_parent_clocks))
        gate("R3_child_clock_exact",np.array_equal(child_clocks,base_child_clocks))
        gate("R3_parent_index_exact",np.array_equal(parent_idx,base_parent_idx))
        gate("R3_child_index_exact",np.array_equal(child_idx,base_child_idx))
        gate("R3_parent_reject_exact",parent_reject==base_parent_reject,(parent_reject,base_parent_reject))
        gate("R3_child_reject_exact",child_reject==base_child_reject,(child_reject,base_child_reject))
        gate("R3_parent_route_exact",sorted(parent_profiles)==sorted(base_parent_profiles))
        gate("R3_child_route_exact",sorted(child_profiles)==sorted(base_child_profiles))
        gate("R3_parent_raw_prediction_array_exact",np.array_equal(parent_pred,base_parent_pred))
        gate("R3_child_raw_prediction_array_exact",np.array_equal(child_pred,base_child_pred))

        def profiles_array_exact(a,b):
            keys=sorted(a)
            return keys==sorted(b) and all(np.array_equal(np.asarray(a[k]),np.asarray(b[k])) for k in keys)

        gate("R3_parent_projected_profile_array_exact",profiles_array_exact(parent_profiles,base_parent_profiles))
        gate("R3_child_projected_profile_array_exact",profiles_array_exact(child_profiles,base_child_profiles))

        baseline_parent_prof=np.stack([base_parent_profiles[int(i)] for i in eligible],axis=0)
        baseline_child_prof=np.stack([base_child_profiles[int(i)] for i in eligible],axis=0)
        baseline_pmm=mass_only_projection(baseline_parent_prof)
        baseline_cmm=mass_only_projection(baseline_child_prof)
        baseline_raw=old_mass[eligible]+(baseline_cmm-baseline_pmm)
        baseline_cap=np.asarray(e37a.cv_mass_from_saturation(
            physics,np.full_like(baseline_raw,float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)),coeff_h),dtype=np.float64)
        baseline_mm,baseline_lam,baseline_box_closure=batch_box_project(baseline_raw,hybrid_target_i,baseline_cap)
        baseline_ss=np.asarray(e37a.invert_cv_mass_to_saturation(physics,baseline_mm,coeff_h),dtype=np.float64)

        baseline_mixed_mass=np.empty_like(old_mass,dtype=np.float64)
        baseline_mixed_sat=np.empty_like(old_sat,dtype=np.float64)
        baseline_mixed_mass[fallback]=np.asarray(exact_subset["new_mass"],float)
        baseline_mixed_sat[fallback]=np.asarray(exact_subset["new_saturation"],float)
        baseline_mixed_mass[eligible]=baseline_mm
        baseline_mixed_sat[eligible]=baseline_ss

        baseline_mapback=e37a.map_control_volume_increment_to_grid(
            physics,parent_sat,old_sat,baseline_mixed_sat,old_mass,baseline_mixed_mass,
            epoch["geometry"],pressure,p_ref,cell_pv,target_final)
        baseline_capillary=physics.conservative_capillary_mass_redistribution(
            transport_saturation=np.asarray(baseline_mapback["corrected_saturation"],float),
            permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,
            cell_pore_volume_m3=cell_pv,dt_seconds=dt*DAY_TO_S)

        gate("R3_parent_mass_projection_array_exact",np.array_equal(pmm,baseline_pmm))
        gate("R3_child_mass_projection_array_exact",np.array_equal(cmm,baseline_cmm))
        gate("R3_corrected_cv_mass_array_exact",np.array_equal(batch_mm,baseline_mm))
        gate("R3_corrected_cv_saturation_array_exact",np.array_equal(batch_ss,baseline_ss))
        gate("R3_grid_mapback_mass_array_exact",np.array_equal(np.asarray(candidate_mapback["corrected_mass"]),np.asarray(baseline_mapback["corrected_mass"])))
        gate("R3_grid_mapback_saturation_array_exact",np.array_equal(np.asarray(candidate_mapback["corrected_saturation"]),np.asarray(baseline_mapback["corrected_saturation"])))
        gate("R3_capillary_saturation_array_exact",np.array_equal(np.asarray(candidate_capillary["corrected"]),np.asarray(baseline_capillary["corrected"])))
        gate("R3_final_capillary_mass_exact",float(candidate_capillary["final_mass_state_kg"])==float(baseline_capillary["final_mass_state_kg"]),(candidate_capillary["final_mass_state_kg"],baseline_capillary["final_mass_state_kg"]))

        r3_exact_output_identity=True

        stage="shadow_B2_scalar_projection_correction_after_candidate"'''
    s=replace_between(s,'        stage="batch_shape_downstream_divergence_audit"','        stage="shadow_B2_scalar_projection_correction_after_candidate"',shadow_block,'exact_output_shadow')

    economics='''        stage="economics_interpretation"
        r3_selective_kernel=(exact_subset_median+child_total_median+boundary_budget_median+
            mass_only_projection_median+batch_correction_median+mapback_only_median+capillary_only_median)
        exact_only_kernel=exact_full_median+exact_mapback_median
        r2_single_batch_kernel=float(b4r2["B4_true_selective_candidate_kernel_seconds"])
        r2_single_batch_gpu=float(b4r2["Hybrid_GPU_inference_single_batch_median_seconds"])
        r2_single_batch_profile=float(b4r2["Hybrid_child_profile_single_batch_median_seconds"])
        r3_vs_exact_ratio=r3_selective_kernel/max(exact_only_kernel,1e-30)
        r3_profile_reduction_vs_frozen_batch256=1.0-child_total_median/max(baseline256_child_total_median,1e-30)
        r3_gpu_reduction_vs_frozen_batch256=1.0-child_infer_median/max(baseline256_child_infer_median,1e-30)
        r3_screen_reduction_vs_frozen_batch256=1.0-child_screen_median/max(baseline256_child_screen_median,1e-30)
        exact_subset_fraction=exact_subset_median/max(exact_full_median,1e-30)
        mapback_capillary_sum=mapback_only_median+capillary_only_median
        remaining_nonphysics_hybrid_overhead=(child_total_median+boundary_budget_median+mass_only_projection_median+batch_correction_median)

        gate("R3_candidate_completed_before_frozen_batch256_shadow",True)
        gate("R3_preserves_batch256_call_count",child_gpu_call_count==2,child_gpu_call_count)
        gate("R3_exact_output_identity_certified",r3_exact_output_identity)
        gate("R3_preserves_frozen_routing_policy",True)
        gate("R3_preserves_B3_conservative_mass_pipeline",True)

        timing_rows=[
            {"component":"same_time_flow_rebuild_once","median_seconds":flow_rebuild_seconds,"repeats":1,"scope":"Day100"},
            {"component":"candidate_fallback_only_exact_E37A","median_seconds":exact_subset_median,"repeats":TIMING_REPEATS,"scope":f"{fallback.size}_routes"},
            {"component":"candidate_Hybrid_boundary_only_mass_budget","median_seconds":boundary_budget_median,"repeats":TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"candidate_R3_child_profile_total_batch256_staged","median_seconds":child_total_median,"repeats":TIMING_REPEATS,"scope":f"{len(child_profiles)}_accepted_profiles"},
            {"component":"candidate_R3_child_GPU_batch256_staged","median_seconds":child_infer_median,"repeats":TIMING_REPEATS,"scope":"2_GPU_calls_same_shapes"},
            {"component":"candidate_R3_child_screen_projection_once","median_seconds":child_screen_median,"repeats":TIMING_REPEATS,"scope":f"{child_learned_window_count}_routes"},
            {"component":"shadow_frozen_batch256_child_profile","median_seconds":baseline256_child_total_median,"repeats":TIMING_REPEATS,"scope":"validation_only"},
            {"component":"shadow_frozen_batch256_GPU","median_seconds":baseline256_child_infer_median,"repeats":TIMING_REPEATS,"scope":"validation_only"},
            {"component":"shadow_frozen_batch256_screen_double_projection","median_seconds":baseline256_child_screen_median,"repeats":TIMING_REPEATS,"scope":"validation_only"},
            {"component":"candidate_Hybrid_mass_only_projection","median_seconds":mass_only_projection_median,"repeats":TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"candidate_Hybrid_batched_box_vectorized_inversion","median_seconds":batch_correction_median,"repeats":CORRECTION_TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"candidate_mapback_only","median_seconds":mapback_only_median,"repeats":3,"scope":"all_routes"},
            {"component":"candidate_capillary_only","median_seconds":capillary_only_median,"repeats":3,"scope":"grid"},
            {"component":"candidate_R3_true_selective_kernel","median_seconds":r3_selective_kernel,"repeats":0,"scope":"sum_of_measured_medians"},
            {"component":"shadow_exact_only_kernel","median_seconds":exact_only_kernel,"repeats":0,"scope":"validation_only"},
            {"component":"R2_single_batch_kernel_reference","median_seconds":r2_single_batch_kernel,"repeats":0,"scope":"prior_non_equivalent_path"},
        ]
'''
    s=replace_between(s,'        stage="economics_interpretation"','        stage="publication"',economics,'economics')

    summary=f'''        summary={{
            "milestone":M,
            "status":PASS,
            "classification":"{R3_CLASSIFICATION}",
            "B4_R2_authority_bound":True,
            "B4_R2_status":b4r2.get("status"),
            "B4_R2_single_batch_exact_end_state_identity":b4r2.get("batch_shape_exact_end_state_identity"),
            "B4_R2_single_batch_production_equivalence_authorized":False,
            "Day100_representative_dt_days":dt,
            "Day100_streamline_count":nstream,
            "Day100_Hybrid_eligible_route_count":int(eligible.size),
            "Day100_exact_fallback_route_count":int(fallback.size),
            "Day100_Hybrid_route_fraction":float(eligible.size/nstream),
            "frozen_batch256_numerical_authority_preserved":True,
            "candidate_GPU_call_count":child_gpu_call_count,
            "candidate_GPU_batch_shapes_preserved":True,
            "cached_xi_input_staging_used":True,
            "single_screen_projection_used":True,
            "raw_predictions_array_exact_vs_frozen_batch256":True,
            "projected_profiles_array_exact_vs_frozen_batch256":True,
            "corrected_CV_state_array_exact_vs_frozen_batch256":True,
            "grid_mapback_state_array_exact_vs_frozen_batch256":True,
            "capillary_state_array_exact_vs_frozen_batch256":True,
            "exact_output_identity_certified":r3_exact_output_identity,
            "fallback_subset_E37A_equivalence_certified":True,
            "Hybrid_boundary_only_mass_budget_used":True,
            "mass_only_projection_used":True,
            "batched_box_projection_used":True,
            "vectorized_E37A_mass_inversion_used":True,
            "fallback_only_exact_E37A_median_seconds":exact_subset_median,
            "Hybrid_boundary_budget_median_seconds":boundary_budget_median,
            "Hybrid_child_profile_R3_batch256_staged_median_seconds":child_total_median,
            "Hybrid_GPU_R3_batch256_staged_median_seconds":child_infer_median,
            "Hybrid_screen_projection_R3_once_median_seconds":child_screen_median,
            "frozen_batch256_child_profile_shadow_median_seconds":baseline256_child_total_median,
            "frozen_batch256_GPU_shadow_median_seconds":baseline256_child_infer_median,
            "frozen_batch256_screen_double_projection_shadow_median_seconds":baseline256_child_screen_median,
            "R3_child_profile_reduction_vs_frozen_batch256_fraction":r3_profile_reduction_vs_frozen_batch256,
            "R3_GPU_reduction_vs_frozen_batch256_fraction":r3_gpu_reduction_vs_frozen_batch256,
            "R3_screen_reduction_vs_frozen_batch256_fraction":r3_screen_reduction_vs_frozen_batch256,
            "Hybrid_mass_only_projection_median_seconds":mass_only_projection_median,
            "Hybrid_batched_box_and_vectorized_inversion_median_seconds":batch_correction_median,
            "mapback_only_median_seconds":mapback_only_median,
            "capillary_only_median_seconds":capillary_only_median,
            "mapback_plus_capillary_sum_seconds":mapback_capillary_sum,
            "remaining_nonphysics_Hybrid_overhead_seconds":remaining_nonphysics_hybrid_overhead,
            "R3_true_selective_candidate_kernel_seconds":r3_selective_kernel,
            "shadow_exact_only_kernel_seconds":exact_only_kernel,
            "R3_candidate_over_exact_only_ratio":r3_vs_exact_ratio,
            "R2_single_batch_non_equivalent_kernel_seconds":r2_single_batch_kernel,
            "R2_single_batch_GPU_seconds":r2_single_batch_gpu,
            "R2_single_batch_profile_seconds":r2_single_batch_profile,
            "routing_policy_changed":False,
            "new_scientific_threshold_defined":False,
            "new_numerical_equivalence_tolerance_defined":False,
            "canonical_state_mutated":False,
            "integrated_GPU_runtime_production_authorized":False,
            "B5_CPU_GPU_overlap_pipeline_probe_authorized":False,
            "B4_R4_fixed_shape_graph_exact_output_probe_authorized":True,
            "P4_authorized":False,
        }}
'''
    s=replace_between(s,'        summary={','        (out/SUMMARY).write_text',summary,'summary')

    footer_start='        print("B3-R1 reference kernel s                              :",b3_reference_kernel)'
    footer_end='        print("="*202)\n        return 0'
    footer='''        print("R3 exact-output identity vs frozen batch256             :",r3_exact_output_identity)
        print("R3 child profile batch256 staged median s               :",child_total_median)
        print("Frozen batch256 child profile shadow median s           :",baseline256_child_total_median)
        print("R3 GPU staged median s                                  :",child_infer_median)
        print("Frozen batch256 GPU shadow median s                      :",baseline256_child_infer_median)
        print("R3 single screen/projection median s                     :",child_screen_median)
        print("Frozen double-projection screen median s                 :",baseline256_child_screen_median)
        print("R3 true selective candidate kernel s                     :",r3_selective_kernel)
        print("Shadow exact-only kernel s                               :",exact_only_kernel)
        print("R3 candidate / exact-only ratio                          :",r3_vs_exact_ratio)
        print("R3 profile reduction vs frozen batch256                  :",r3_profile_reduction_vs_frozen_batch256)
        print("B5 CPU/GPU overlap pipeline probe                        : NOT AUTHORIZED")
        print("B4-R4 fixed-shape graph exact-output probe               : AUTHORIZED")
        print("="*202)
        return 0'''
    s=replace_between(s,footer_start,footer_end,footer,'footer')

    return s

def repository_preflight(root):
    branch=git(root,'branch','--show-current'); head=git(root,'rev-parse','HEAD'); par=git(root,'rev-parse','HEAD^'); clean=git(root,'status','--porcelain')==''
    p=root/R2_RUNNER; blob=git(root,'hash-object',str(p)) if p.is_file() else 'MISSING'
    print('--- G4-B4-R3 REPOSITORY IDENTITY ---')
    print('Branch:',branch); print('HEAD  :',head); print('HEAD^ :',par); print('Clean :',clean)
    print('B4-R2 runner blob:',blob); print('Expected         :',R2_GIT_BLOB)
    if branch!=BRANCH: raise R3Error(f'branch:{branch}:{BRANCH}')
    if par!=PARENT: raise R3Error(f'parent:{par}:{PARENT}')
    if not clean: raise R3Error('repository_not_clean')
    if blob!=R2_GIT_BLOB: raise R3Error(f'B4R2_blob:{blob}:{R2_GIT_BLOB}')

def load_patched_module(root):
    src=patched_r3_source(root); compile(src,f'<{R3_TOKEN}_patched_R2>','exec')
    m=types.ModuleType('g4_b4_r3_exact_batch256'); m.__file__=str(root/R2_RUNNER); m.__package__=None
    sys.modules[m.__name__]=m; exec(compile(src,m.__file__,'exec'),m.__dict__); return m

def self_test(root):
    repository_preflight(root); src=patched_r3_source(root)
    for marker in [
        'def infer_staged_batch256(cond_arr):',
        'def screen_and_project_once(y,p,state,tau_nodes):',
        'gate("R3_parent_raw_prediction_array_exact"',
        'gate("R3_child_raw_prediction_array_exact"',
        'gate("R3_capillary_saturation_array_exact"',
        '"new_numerical_equivalence_tolerance_defined":False',
        '"B4_R4_fixed_shape_graph_exact_output_probe_authorized":True',
        '"B5_CPU_GPU_overlap_pipeline_probe_authorized":False',
    ]:
        if marker not in src: raise R3Error(f'missing_R3_marker:{marker}')
    compile(src,f'<{R3_TOKEN}_structural_selftest>','exec'); m=load_patched_module(root)
    if m.OUT_TOKEN!=R3_TOKEN: raise R3Error(f'patched_OUT_TOKEN:{m.OUT_TOKEN}')
    if m.PASS!=R3_STATUS: raise R3Error(f'patched_PASS:{m.PASS}')
    print('POSTV16 GPU-HYB-G4-B4-R3 structural/patch self-test: PASS')

def main(root,drive):
    root=root.resolve(); drive=drive.resolve(); repository_preflight(root)
    return int(load_patched_module(root).main(root,drive))

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--project-root',type=Path,default=Path('.'))
    ap.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'))
    ap.add_argument('--self-test',action='store_true')
    args=ap.parse_args()
    try:
        if args.self_test: self_test(args.project_root.resolve()); raise SystemExit(0)
        raise SystemExit(main(args.project_root,args.drive_root))
    except Exception as exc:
        print(MILESTONE,'WRAPPER BLOCK'); print('Exception:',repr(exc)); raise
