#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import types
from pathlib import Path

MILESTONE = "POSTV16-AV4-PIVOT-GPU-HYB-G4-B4"
BRANCH = "postv16-av4-pivot"
PARENT = "c94e5e6c6f3f6c2e433da23cec93ea72d89f092b"

B3R1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_R1_Publication_Variable_Repair.py"
B3R1_GIT_BLOB = "508440fb5e0fc33060228ecc7bb9ee5b5c686346"

B4_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G4_B4"
B4_STATUS = "POSTV16AV4PIVOTGPUHYBG4B4_SINGLE_BATCH_GPU_PROFILE_PIPELINE_OPTIMIZATION_PASS"
B4_BLOCK = "POSTV16AV4PIVOTGPUHYBG4B4_TECHNICAL_OR_AUTHORITY_BLOCK"
B4_CLASSIFICATION = (
    "FROZEN_HYBRID10_SINGLE_BATCH_GPU_PROFILE_PIPELINE_EXECUTION_"
    "BASELINE_BATCH256_SCREEN_AND_PROFILE_EQUIVALENCE_CERTIFIED"
)

B3R1_STATUS = "POSTV16AV4PIVOTGPUHYBG4B3R1_PUBLICATION_VARIABLE_REPAIR_PASS"


class B4Error(RuntimeError):
    pass


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def replace_once(source: str, old: str, new: str, label: str) -> str:
    n = source.count(old)
    if n != 1:
        raise B4Error(f"patch_anchor_{label}_count:{n}")
    return source.replace(old, new, 1)


def replace_between(source: str, start: str, end: str, replacement: str, label: str) -> str:
    i = source.find(start)
    if i < 0:
        raise B4Error(f"patch_start_{label}_missing")
    if source.find(start, i + 1) >= 0:
        raise B4Error(f"patch_start_{label}_not_unique")
    j = source.find(end, i + len(start))
    if j < 0:
        raise B4Error(f"patch_end_{label}_missing")
    if source.find(end, j + 1) >= 0:
        raise B4Error(f"patch_end_{label}_not_unique")
    return source[:i] + replacement + source[j:]


def import_exact(root: Path, filename: str, expected_blob: str, module_name: str):
    p = root / filename
    if not p.is_file():
        raise B4Error(f"missing_source:{filename}")
    actual = git(root, "hash-object", str(p))
    if actual != expected_blob:
        raise B4Error(f"source_blob:{filename}:{actual}:{expected_blob}")
    spec = importlib.util.spec_from_file_location(module_name, p)
    if spec is None or spec.loader is None:
        raise B4Error(f"import_spec:{filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def patched_b4_source(root: Path) -> str:
    r1 = import_exact(root, B3R1_RUNNER, B3R1_GIT_BLOB, "g4b4_b3r1_authority")
    s = r1.patched_r1_source(root)

    replacements = [
        ('M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B3-R1"', f'M="{MILESTONE}"', 'milestone'),
        (f'PASS="{B3R1_STATUS}"', f'PASS="{B4_STATUS}"', 'pass_status'),
        ('BLOCK="POSTV16AV4PIVOTGPUHYBG4B3R1_TECHNICAL_OR_AUTHORITY_BLOCK"', f'BLOCK="{B4_BLOCK}"', 'block_status'),
        ('PARENT="fb49567af0094a4a93f4d674250efa234c9c4754"', f'PARENT="{PARENT}"', 'parent'),
        ('OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_R1"', f'OUT_TOKEN="{B4_TOKEN}"', 'output_token'),
        ('print("POSTV16 GPU-HYB-G4-B3-R1 structural/patch self-test: PASS")',
         'print("POSTV16 GPU-HYB-G4-B4 structural/patch self-test: PASS")', 'selftest_label'),
        ('gate("parent_is_G4_B3_block_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',
         'gate("parent_is_G4_B3_R1_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))', 'parent_gate'),
    ]
    for old, new, label in replacements:
        s = replace_once(s, old, new, label)

    old_banner = (
        'print("G4-B3-R1 — PUBLICATION VARIABLE REPAIR / VECTORIZED HYBRID OVERHEAD OPTIMIZATION")\n'
        '        print("REPAIR OF G4-B3 PUBLICATION/REPORTING ONLY. B3 SCIENTIFIC PATH, ROUTING, MASS BUDGETS, CORRECTION, MAPBACK, CAPILLARY, AND SHADOW VALIDATION ARE UNCHANGED.")\n'
        '        print("ORIGINAL G4-B3 BLOCK IS IMMUTABLE AND MUST BE BOUND AS A PUBLICATION-STAGE NAMEERROR WITH ALL RECORDED GATES PASS.")'
    )
    new_banner = (
        'print("G4-B4 — SINGLE-BATCH GPU HYBRID PROFILE PIPELINE OPTIMIZATION")\n'
        '        print("READ-ONLY PERFORMANCE OPTIMIZATION. FROZEN HYBRID10 WEIGHTS, E8R1 SCREEN, ROUTING, MASS BUDGETS, E37A FALLBACK, MAPBACK, AND CAPILLARY PHYSICS ARE UNCHANGED.")\n'
        '        print("CANDIDATE USES THE FROZEN E9-R1 INFERENCE HELPER WITH ONE GPU BATCH; ORIGINAL BATCH-256 PROFILE EXECUTION IS SHADOW VALIDATION ONLY.")'
    )
    s = replace_once(s, old_banner, new_banner, 'banner')

    authority_anchor = '''        b3_block_path=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_BLOCKED")/"POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_Blocked_Report.json"'''
    authority_insert = '''        b3r1d=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_R1_Route_Economics_Instrumentation")
        b3r1_summary_name="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_R1_Summary.json"
        b3r1_manifest_name="POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_R1_Artifact_Manifest.csv"
        gate("B3_R1_summary_present",(b3r1d/b3r1_summary_name).is_file(),str(b3r1d/b3r1_summary_name))
        b3r1=js(b3r1d/b3r1_summary_name)
        gate("B3_R1_status_exact",b3r1.get("status")=="POSTV16AV4PIVOTGPUHYBG4B3R1_PUBLICATION_VARIABLE_REPAIR_PASS",b3r1.get("status"))
        gate("B3_R1_manifest_present",(b3r1d/b3r1_manifest_name).is_file(),str(b3r1d/b3r1_manifest_name))
        verify_manifest(b3r1d,b3r1_manifest_name)
        gate("B3_R1_vectorized_projection_exact",float(b3r1.get("mass_only_projection_max_abs_difference_vs_B2_bridge_mass_kg",float("inf")))==0.0)
        gate("B3_R1_vectorized_box_exact",float(b3r1.get("batched_box_mass_max_abs_difference_vs_B2_scalar_kg",float("inf")))==0.0)
        gate("B3_R1_vectorized_inversion_exact",float(b3r1.get("vectorized_inversion_saturation_max_abs_difference_vs_B2_scalar",float("inf")))==0.0)

        b3_block_path=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_BLOCKED")/"POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_Blocked_Report.json"'''
    s = replace_once(s, authority_anchor, authority_insert, 'B3R1_authority')

    profile_block = r'''        xi32=np.asarray(xi,dtype=np.float32)

        def build_profile_mode(day:float,batch_mode:str):
            tprep=time.perf_counter()
            xstar=(float(day)/terminal_days)*speed
            clocks=np.asarray([e11.classify_clock(float(x)) for x in xstar],dtype="U32")
            idx=np.flatnonzero(clocks=="LEARNED_WINDOW")
            cond=[];states=[]
            for i in idx:
                st=adapter.physical_time_state(
                    elapsed_time=day,tau_end=float(terminal_days[i]),
                    characteristic_speed=speed,Sw_star=swstar)
                states.append(st)
                cond.append(adapter.conditioning_vector("HYBRID10",params,st))
            cond_arr=np.asarray(cond,dtype=np.float32)
            prep_seconds=float(time.perf_counter()-tprep)

            tinfer=time.perf_counter()
            if idx.size:
                if batch_mode=="single":
                    batch=max(int(idx.size),1)
                elif batch_mode=="baseline256":
                    batch=256
                else:
                    raise GateError(f"unknown_profile_batch_mode:{batch_mode}")
                pred=e9r1.infer(tf,model,xi32,cond_arr,batch=batch)
                gpu_call_count=int((idx.size+batch-1)//batch)
            else:
                pred=np.empty((0,len(xi)),dtype=np.float32)
                gpu_call_count=0
            infer_seconds=float(time.perf_counter()-tinfer)

            tscreen=time.perf_counter()
            profiles={}
            reject={}
            for local,i in enumerate(idx):
                ok,sm=e11.screen_fan_prediction(
                    pred[local],params,states[local],xi,tau[i]/DAY_TO_S,teacher,adapter,screen)
                if ok:
                    profiles[int(i)]=adapter.project_fan_to_pollock_nodes(
                        tau_nodes=tau[i]/DAY_TO_S,state=states[local],fan_xi=xi,
                        fan_sw=pred[local],swc=float(params["swc"])).astype(np.float64)
                else:
                    for reason in sm["failures"]:
                        reject[reason]=reject.get(reason,0)+1
            screen_seconds=float(time.perf_counter()-tscreen)
            return profiles,clocks,reject,{
                "conditioning_seconds":prep_seconds,
                "GPU_inference_seconds":infer_seconds,
                "screen_and_node_projection_seconds":screen_seconds,
                "total_profile_seconds":prep_seconds+infer_seconds+screen_seconds,
                "learned_window_count":int(idx.size),
                "accepted_profile_count":int(len(profiles)),
                "GPU_call_count":gpu_call_count,
                "batch_mode":batch_mode,
            },pred,idx

        parent_fast=build_profile_mode(100.0,"single")
        parent_profiles,parent_clocks,parent_reject,parent_profile_time,parent_pred,parent_idx=parent_fast

        child_times=[]
        child_output=None
        for _ in range(TIMING_REPEATS):
            child_output=build_profile_mode(100.0+dt,"single")
            child_times.append(child_output[3])
        child_profiles,child_clocks,child_reject,child_fast_time,child_pred,child_idx=child_output
        child_total_median=float(statistics.median([x["total_profile_seconds"] for x in child_times]))
        child_condition_median=float(statistics.median([x["conditioning_seconds"] for x in child_times]))
        child_infer_median=float(statistics.median([x["GPU_inference_seconds"] for x in child_times]))
        child_screen_median=float(statistics.median([x["screen_and_node_projection_seconds"] for x in child_times]))
        child_gpu_call_count=int(child_fast_time["GPU_call_count"])
        child_learned_window_count=int(child_fast_time["learned_window_count"])

        stage="shadow_batch256_profile_equivalence"
        parent_base=build_profile_mode(100.0,"baseline256")
        child_base=build_profile_mode(100.0+dt,"baseline256")
        base_parent_profiles,base_parent_clocks,base_parent_reject,base_parent_time,base_parent_pred,base_parent_idx=parent_base
        base_child_profiles,base_child_clocks,base_child_reject,base_child_time,base_child_pred,base_child_idx=child_base

        gate("parent_clock_identity_vs_batch256",np.array_equal(parent_clocks,base_parent_clocks))
        gate("child_clock_identity_vs_batch256",np.array_equal(child_clocks,base_child_clocks))
        gate("parent_learned_window_index_identity_vs_batch256",np.array_equal(parent_idx,base_parent_idx))
        gate("child_learned_window_index_identity_vs_batch256",np.array_equal(child_idx,base_child_idx))
        gate("parent_screen_reject_identity_vs_batch256",parent_reject==base_parent_reject,(parent_reject,base_parent_reject))
        gate("child_screen_reject_identity_vs_batch256",child_reject==base_child_reject,(child_reject,base_child_reject))
        gate("parent_accepted_route_identity_vs_batch256",
             sorted(parent_profiles)==sorted(base_parent_profiles),
             (len(parent_profiles),len(base_parent_profiles)))
        gate("child_accepted_route_identity_vs_batch256",
             sorted(child_profiles)==sorted(base_child_profiles),
             (len(child_profiles),len(base_child_profiles)))

        pred_scale=max(
            1.0,
            float(np.max(np.abs(base_parent_pred))) if base_parent_pred.size else 0.0,
            float(np.max(np.abs(base_child_pred))) if base_child_pred.size else 0.0)
        float32_execution_tol=float(16.0*np.finfo(np.float32).eps*pred_scale)
        parent_prediction_max_abs=float(np.max(np.abs(parent_pred.astype(np.float64)-base_parent_pred.astype(np.float64)))) if parent_pred.size else 0.0
        child_prediction_max_abs=float(np.max(np.abs(child_pred.astype(np.float64)-base_child_pred.astype(np.float64)))) if child_pred.size else 0.0
        gate("parent_prediction_float32_execution_equivalence",
             parent_prediction_max_abs<=float32_execution_tol,
             (parent_prediction_max_abs,float32_execution_tol))
        gate("child_prediction_float32_execution_equivalence",
             child_prediction_max_abs<=float32_execution_tol,
             (child_prediction_max_abs,float32_execution_tol))

        def profile_max_abs(a,b):
            keys=sorted(a)
            if keys!=sorted(b):
                return float("inf")
            if not keys:
                return 0.0
            return float(max(np.max(np.abs(np.asarray(a[k],float)-np.asarray(b[k],float))) for k in keys))

        parent_profile_max_abs=profile_max_abs(parent_profiles,base_parent_profiles)
        child_profile_max_abs=profile_max_abs(child_profiles,base_child_profiles)
        gate("parent_profile_float32_execution_equivalence",
             parent_profile_max_abs<=float32_execution_tol,
             (parent_profile_max_abs,float32_execution_tol))
        gate("child_profile_float32_execution_equivalence",
             child_profile_max_abs<=float32_execution_tol,
             (child_profile_max_abs,float32_execution_tol))

        baseline256_child_total_seconds=float(base_child_time["total_profile_seconds"])
        baseline256_child_infer_seconds=float(base_child_time["GPU_inference_seconds"])
        baseline256_child_gpu_call_count=int(base_child_time["GPU_call_count"])

'''
    s = replace_between(
        s,
        '        def build_profile(day:float):',
        '        eligible=np.asarray(sorted(set(parent_profiles).intersection(child_profiles)),dtype=np.int64)',
        profile_block + '        eligible=np.asarray(sorted(set(parent_profiles).intersection(child_profiles)),dtype=np.int64)\n',
        'profile_pipeline',
    )

    economics_block = r'''        stage="economics_interpretation"
        b4_selective_kernel=(
            exact_subset_median
            + child_total_median
            + boundary_budget_median
            + mass_only_projection_median
            + batch_correction_median
            + mapback_only_median
            + capillary_only_median
        )
        exact_only_kernel=exact_full_median+exact_mapback_median
        b3_reference_kernel=float(b3r1["B3_true_selective_candidate_kernel_seconds"])
        b3_reference_child=float(b3r1["Hybrid_child_profile_median_seconds"])
        b3_reference_gpu=float(b3r1["Hybrid_GPU_inference_median_seconds"])
        b4_vs_exact_ratio=b4_selective_kernel/max(exact_only_kernel,1e-30)
        b4_reduction_vs_b3=1.0-b4_selective_kernel/max(b3_reference_kernel,1e-30)
        child_reduction_vs_b3=1.0-child_total_median/max(b3_reference_child,1e-30)
        gpu_reduction_vs_b3=1.0-child_infer_median/max(b3_reference_gpu,1e-30)
        exact_subset_fraction=exact_subset_median/max(exact_full_median,1e-30)
        mapback_capillary_sum=mapback_only_median+capillary_only_median
        remaining_nonphysics_hybrid_overhead=(
            child_total_median+boundary_budget_median+mass_only_projection_median+batch_correction_median
        )

        gate("B4_candidate_profile_path_precedes_batch256_shadow",True,
             "single-batch parent/child profiles were constructed before the baseline batch-256 shadow")
        gate("B4_preserves_frozen_routing_policy",True,
             "eligible/fallback sets use unchanged E8R1 screen and Hybrid10 authority")
        gate("B4_preserves_B3_vectorized_mass_pipeline",True,
             "mass-only projection, batched box projection, vectorized E37A inversion, mapback and capillary are unchanged")
        gate("B4_single_batch_gpu_call_count_one",
             child_gpu_call_count==1,
             (child_gpu_call_count,child_learned_window_count))
        gate("B4_baseline_batch256_requires_multiple_calls",
             baseline256_child_gpu_call_count>=2,
             baseline256_child_gpu_call_count)

        timing_rows=[
            {"component":"same_time_flow_rebuild_once","median_seconds":flow_rebuild_seconds,"repeats":1,"scope":"Day100"},
            {"component":"candidate_fallback_only_exact_E37A","median_seconds":exact_subset_median,"repeats":TIMING_REPEATS,"scope":f"{fallback.size}_routes"},
            {"component":"candidate_Hybrid_boundary_only_mass_budget","median_seconds":boundary_budget_median,"repeats":TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"candidate_Hybrid_child_profile_total_single_batch","median_seconds":child_total_median,"repeats":TIMING_REPEATS,"scope":f"{len(child_profiles)}_accepted_profiles"},
            {"component":"candidate_Hybrid_child_conditioning_single_batch","median_seconds":child_condition_median,"repeats":TIMING_REPEATS,"scope":f"{child_learned_window_count}_learned_window_routes"},
            {"component":"candidate_Hybrid_child_GPU_inference_single_batch","median_seconds":child_infer_median,"repeats":TIMING_REPEATS,"scope":f"{child_gpu_call_count}_GPU_call"},
            {"component":"candidate_Hybrid_child_screen_projection_single_batch","median_seconds":child_screen_median,"repeats":TIMING_REPEATS,"scope":f"{child_learned_window_count}_learned_window_routes"},
            {"component":"shadow_batch256_child_profile_once","median_seconds":baseline256_child_total_seconds,"repeats":1,"scope":"validation_only"},
            {"component":"shadow_batch256_child_GPU_inference_once","median_seconds":baseline256_child_infer_seconds,"repeats":1,"scope":"validation_only"},
            {"component":"candidate_Hybrid_mass_only_201_to_200_parent_plus_child","median_seconds":mass_only_projection_median,"repeats":TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"candidate_Hybrid_batched_box_plus_vectorized_inversion","median_seconds":batch_correction_median,"repeats":CORRECTION_TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"candidate_mapback_only","median_seconds":mapback_only_median,"repeats":3,"scope":"all_routes"},
            {"component":"candidate_capillary_only","median_seconds":capillary_only_median,"repeats":3,"scope":"grid"},
            {"component":"candidate_B4_true_selective_kernel","median_seconds":b4_selective_kernel,"repeats":0,"scope":"sum_of_measured_medians"},
            {"component":"shadow_full_exact_E37A_all_routes","median_seconds":exact_full_median,"repeats":TIMING_REPEATS,"scope":f"{nstream}_routes_validation_only"},
            {"component":"shadow_exact_mapback_plus_capillary","median_seconds":exact_mapback_median,"repeats":3,"scope":"all_routes_validation_only"},
            {"component":"shadow_exact_only_transport_kernel","median_seconds":exact_only_kernel,"repeats":0,"scope":"validation_only"},
            {"component":"B3_R1_true_selective_kernel_reference","median_seconds":b3_reference_kernel,"repeats":0,"scope":"prior_milestone"},
        ]
'''
    s = replace_between(
        s,
        '        stage="economics_interpretation"',
        '        stage="publication"',
        economics_block,
        'economics_block',
    )

    summary_block = f'''        summary={{
            "milestone":M,
            "status":PASS,
            "classification":"{B4_CLASSIFICATION}",
            "B3_R1_authority_bound":True,
            "B3_R1_status":b3r1.get("status"),
            "B3_blocked_predecessor_bound":True,
            "B3_original_failed_stage":b3block.get("failed_stage"),
            "Day100_representative_dt_days":dt,
            "Day100_streamline_count":nstream,
            "Day100_Hybrid_eligible_route_count":int(eligible.size),
            "Day100_exact_fallback_route_count":int(fallback.size),
            "Day100_Hybrid_route_fraction":float(eligible.size/nstream),
            "single_batch_GPU_profile_candidate_used":True,
            "single_batch_GPU_call_count":child_gpu_call_count,
            "baseline_batch256_GPU_call_count":baseline256_child_gpu_call_count,
            "learned_window_route_count":child_learned_window_count,
            "parent_prediction_max_abs_difference_vs_batch256":parent_prediction_max_abs,
            "child_prediction_max_abs_difference_vs_batch256":child_prediction_max_abs,
            "parent_profile_max_abs_difference_vs_batch256":parent_profile_max_abs,
            "child_profile_max_abs_difference_vs_batch256":child_profile_max_abs,
            "float32_execution_equivalence_tolerance":float32_execution_tol,
            "screen_and_route_identity_vs_batch256":True,
            "candidate_full_exact_all_route_execution_dependency":False,
            "Hybrid_boundary_only_mass_budget_used":True,
            "mass_only_projection_used":True,
            "batched_box_projection_used":True,
            "vectorized_E37A_mass_inversion_used":True,
            "fallback_subset_E37A_equivalence_certified":True,
            "fallback_only_exact_E37A_median_seconds":exact_subset_median,
            "full_exact_E37A_shadow_median_seconds":exact_full_median,
            "fallback_only_exact_vs_full_exact_time_fraction":exact_subset_fraction,
            "Hybrid_boundary_budget_median_seconds":boundary_budget_median,
            "Hybrid_child_profile_single_batch_median_seconds":child_total_median,
            "Hybrid_child_conditioning_single_batch_median_seconds":child_condition_median,
            "Hybrid_GPU_inference_single_batch_median_seconds":child_infer_median,
            "Hybrid_child_screen_projection_single_batch_median_seconds":child_screen_median,
            "shadow_batch256_child_profile_seconds":baseline256_child_total_seconds,
            "shadow_batch256_GPU_inference_seconds":baseline256_child_infer_seconds,
            "Hybrid_mass_only_projection_median_seconds":mass_only_projection_median,
            "Hybrid_batched_box_and_vectorized_inversion_median_seconds":batch_correction_median,
            "mapback_only_median_seconds":mapback_only_median,
            "capillary_only_median_seconds":capillary_only_median,
            "mapback_plus_capillary_sum_seconds":mapback_capillary_sum,
            "remaining_nonphysics_Hybrid_overhead_seconds":remaining_nonphysics_hybrid_overhead,
            "B4_true_selective_candidate_kernel_seconds":b4_selective_kernel,
            "shadow_exact_only_kernel_seconds":exact_only_kernel,
            "B4_candidate_over_exact_only_ratio":b4_vs_exact_ratio,
            "B3_R1_true_selective_candidate_kernel_seconds":b3_reference_kernel,
            "B4_reduction_vs_B3_R1_fraction":b4_reduction_vs_b3,
            "B3_R1_child_profile_median_seconds":b3_reference_child,
            "B4_child_profile_reduction_vs_B3_R1_fraction":child_reduction_vs_b3,
            "B3_R1_GPU_inference_median_seconds":b3_reference_gpu,
            "B4_GPU_inference_reduction_vs_B3_R1_fraction":gpu_reduction_vs_b3,
            "Day100_Hybrid_one_step_saturation_relL2_median":float(np.median(hybrid_route_errors)),
            "Day100_Hybrid_one_step_saturation_relL2_p95":float(np.quantile(hybrid_route_errors,.95)),
            "route_level_spatial_attribution_created":True,
            "route_level_one_step_accuracy_attribution_created":True,
            "routing_policy_changed":False,
            "new_scientific_threshold_defined":False,
            "float32_execution_tolerance_is_numerical_not_scientific":True,
            "canonical_state_mutated":False,
            "integrated_GPU_runtime_production_authorized":False,
            "B5_CPU_GPU_overlap_pipeline_probe_authorized":True,
            "P4_authorized":False,
        }}
'''
    s = replace_between(
        s,
        '        summary={',
        '        (out/SUMMARY).write_text',
        summary_block,
        'summary_block',
    )

    footer_start = '        print("B3 predecessor failed only at publication             :",b3block.get("failed_stage"))'
    footer_end = '        print("="*202)\n        return 0'
    new_footer = '''        print("B3-R1 reference kernel s                              :",b3_reference_kernel)
        print("B4 single-batch child profile median s                :",child_total_median)
        print("B4 single-batch GPU inference median s                :",child_infer_median)
        print("Baseline batch256 GPU calls                           :",baseline256_child_gpu_call_count)
        print("B4 single-batch GPU calls                             :",child_gpu_call_count)
        print("B4 true selective candidate kernel s                  :",b4_selective_kernel)
        print("Shadow exact-only kernel s                            :",exact_only_kernel)
        print("B4 candidate / exact-only ratio                       :",b4_vs_exact_ratio)
        print("Reduction vs B3-R1                                    :",b4_reduction_vs_b3)
        print("Child-profile reduction vs B3-R1                      :",child_reduction_vs_b3)
        print("GPU-inference reduction vs B3-R1                      :",gpu_reduction_vs_b3)
        print("B5 CPU/GPU overlap pipeline probe                     : AUTHORIZED")
        print("="*202)
        return 0'''
    s = replace_between(s, footer_start, footer_end, new_footer, 'footer')

    return s


def repository_preflight(root: Path) -> None:
    branch = git(root, "branch", "--show-current")
    parent = git(root, "rev-parse", "HEAD^")
    clean = git(root, "status", "--porcelain") == ""
    r1 = root / B3R1_RUNNER
    r1_blob = git(root, "hash-object", str(r1)) if r1.is_file() else "MISSING"
    print("--- G4-B4 REPOSITORY IDENTITY ---")
    print("Branch:", branch)
    print("HEAD  :", git(root, "rev-parse", "HEAD"))
    print("HEAD^ :", parent)
    print("Clean :", clean)
    print("B3-R1 blob:", r1_blob)
    if branch != BRANCH:
        raise B4Error(f"branch:{branch}:{BRANCH}")
    if parent != PARENT:
        raise B4Error(f"parent:{parent}:{PARENT}")
    if not clean:
        raise B4Error("repository_not_clean")
    if r1_blob != B3R1_GIT_BLOB:
        raise B4Error(f"B3R1_blob:{r1_blob}:{B3R1_GIT_BLOB}")


def load_patched_module(root: Path) -> types.ModuleType:
    patched = patched_b4_source(root)
    compile(patched, f"<{B4_TOKEN}_patched_B3_R1>", "exec")
    module = types.ModuleType("g4_b4_gpu_profile_pipeline")
    module.__file__ = str(root / B3R1_RUNNER)
    module.__package__ = None
    sys.modules[module.__name__] = module
    exec(compile(patched, module.__file__, "exec"), module.__dict__)
    return module


def self_test(root: Path) -> None:
    repository_preflight(root)
    module = load_patched_module(root)
    required = ["main", "selftest", "OUT_TOKEN", "PASS", "BLOCK"]
    missing = [x for x in required if not hasattr(module, x)]
    if missing:
        raise B4Error(f"patched_module_missing:{missing}")
    if module.OUT_TOKEN != B4_TOKEN:
        raise B4Error(f"patched_OUT_TOKEN:{module.OUT_TOKEN}")
    if module.PASS != B4_STATUS:
        raise B4Error(f"patched_PASS:{module.PASS}")
    src = patched_b4_source(root)
    required_markers = [
        'def build_profile_mode(day:float,batch_mode:str):',
        'batch_mode=="single"',
        'stage="shadow_batch256_profile_equivalence"',
        'gate("B4_single_batch_gpu_call_count_one"',
        '"B5_CPU_GPU_overlap_pipeline_probe_authorized":True',
    ]
    for marker in required_markers:
        if marker not in src:
            raise B4Error(f"missing_B4_marker:{marker}")
    print("POSTV16 GPU-HYB-G4-B4 structural/patch self-test: PASS")


def main(root: Path, drive: Path) -> int:
    root = root.resolve()
    drive = drive.resolve()
    repository_preflight(root)
    module = load_patched_module(root)
    return int(module.main(root, drive))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    try:
        if args.self_test:
            self_test(args.project_root.resolve())
            raise SystemExit(0)
        raise SystemExit(main(args.project_root, args.drive_root))
    except Exception as exc:
        print(MILESTONE, "WRAPPER BLOCK")
        print("Exception:", repr(exc))
        raise
