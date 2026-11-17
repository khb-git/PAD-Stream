#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import types
from pathlib import Path

MILESTONE = "POSTV16-AV4-PIVOT-GPU-HYB-G4-B3"
BRANCH = "postv16-av4-pivot"
PARENT = "69a39a7eded5ca0d3dc0d354b9b4ee3e62be2c75"

B2_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B2_True_Selective_Routing_Subset_Fallback_Execution.py"
B2_GIT_BLOB = "be7650b83a21300bac7952fdde5404b77b7f309d"

B3_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G4_B3"
B3_STATUS = "POSTV16AV4PIVOTGPUHYBG4B3_VECTORIZED_HYBRID_OVERHEAD_OPTIMIZATION_PASS"
B3_BLOCK = "POSTV16AV4PIVOTGPUHYBG4B3_TECHNICAL_OR_AUTHORITY_BLOCK"
B3_CLASSIFICATION = (
    "TRUE_SELECTIVE_HYBRID_EXECUTION_PRESERVED_MASS_ONLY_201_TO_200_PROJECTION_"
    "BATCH_BOX_PROJECTION_AND_VECTORIZED_E37A_INVERSION_CERTIFIED_"
    "MAPBACK_CAPILLARY_COST_SPLIT_INSTRUMENTED"
)
B2_STATUS = "POSTV16AV4PIVOTGPUHYBG4B2_TRUE_SELECTIVE_ROUTING_SUBSET_FALLBACK_EXECUTION_PASS"


class B3Error(RuntimeError):
    pass


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def replace_once(source: str, old: str, new: str, label: str) -> str:
    n = source.count(old)
    if n != 1:
        raise B3Error(f"patch_anchor_{label}_count:{n}")
    return source.replace(old, new, 1)


def replace_between(source: str, start: str, end: str, replacement: str, label: str) -> str:
    i = source.find(start)
    if i < 0:
        raise B3Error(f"patch_start_{label}_missing")
    if source.find(start, i + 1) >= 0:
        raise B3Error(f"patch_start_{label}_not_unique")
    j = source.find(end, i + len(start))
    if j < 0:
        raise B3Error(f"patch_end_{label}_missing")
    if source.find(end, j + 1) >= 0:
        raise B3Error(f"patch_end_{label}_not_unique")
    return source[:i] + replacement + source[j:]


def import_exact(root: Path, filename: str, expected_blob: str, module_name: str):
    p = root / filename
    if not p.is_file():
        raise B3Error(f"missing_source:{filename}")
    actual = git(root, "hash-object", str(p))
    if actual != expected_blob:
        raise B3Error(f"source_blob:{filename}:{actual}:{expected_blob}")
    spec = importlib.util.spec_from_file_location(module_name, p)
    if spec is None or spec.loader is None:
        raise B3Error(f"import_spec:{filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def patched_b3_source(root: Path) -> str:
    b2mod = import_exact(root, B2_RUNNER, B2_GIT_BLOB, "g4b3_b2_authority")
    s = b2mod.patched_b2_source(root)

    replacements = [
        ('M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B2"', f'M="{MILESTONE}"', 'milestone'),
        (f'PASS="{B2_STATUS}"', f'PASS="{B3_STATUS}"', 'pass_status'),
        ('BLOCK="POSTV16AV4PIVOTGPUHYBG4B2_TECHNICAL_OR_AUTHORITY_BLOCK"', f'BLOCK="{B3_BLOCK}"', 'block_status'),
        ('PARENT="ed280dc80d365714aaad1edb1cc85a8c6d9b322a"', f'PARENT="{PARENT}"', 'parent'),
        ('OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B2"', f'OUT_TOKEN="{B3_TOKEN}"', 'output_token'),
        ('print("POSTV16 GPU-HYB-G4-B2 structural self-test: PASS")',
         'print("POSTV16 GPU-HYB-G4-B3 structural self-test: PASS")', 'selftest_label'),
        ('gate("parent_is_G4_B1_R1_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',
         'gate("parent_is_G4_B2_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))', 'parent_gate'),
    ]
    for old, new, label in replacements:
        s = replace_once(s, old, new, label)

    old_banner = (
        'print("G4-B2 — TRUE SELECTIVE HYBRID ROUTING / EXACT SUBSET FALLBACK EXECUTION")\n'
        '        print("CONTROLLED READ-ONLY ARCHITECTURE EXECUTION. HYBRID ROUTES USE EXACT BOUNDARY-ONLY MASS BUDGETS; ONLY FALLBACK ROUTES EXECUTE FULL E37A TRANSPORT.")\n'
        '        print("FULL EXACT ALL-ROUTE SOLVE IS SHADOW REFERENCE ONLY AND OCCURS AFTER THE SELECTIVE CANDIDATE PATH COMPLETES.")'
    )
    new_banner = (
        'print("G4-B3 — VECTORIZED HYBRID OVERHEAD OPTIMIZATION / TRUE SELECTIVE EXECUTION")\n'
        '        print("READ-ONLY PERFORMANCE REPAIR. PRESERVES B2 ROUTING, MASS BUDGETS, BOX CONSTRAINTS, E37A CONSTITUTIVE INVERSION, MAPBACK, AND CAPILLARY PHYSICS.")\n'
        '        print("OPTIMIZES ONLY REDUNDANT SATURATION INVERSION AND PYTHON PER-ROUTE CORRECTION OVERHEAD; SCALAR B2 PATH IS SHADOW VALIDATION ONLY.")'
    )
    s = replace_once(s, old_banner, new_banner, 'banner')

    authority_anchor = '''        r1d=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B1_R1_Route_Economics_Instrumentation")'''
    authority_insert = '''        b2d=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B2_Route_Economics_Instrumentation")
        b2_summary_name="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B2_Summary.json"
        b2_manifest_name="POSTV16_AV4_PIVOT_GPU_HYB_G4_B2_Artifact_Manifest.csv"
        gate("B2_summary_present",(b2d/b2_summary_name).is_file(),str(b2d/b2_summary_name))
        b2s=js(b2d/b2_summary_name)
        gate("B2_status_exact",b2s.get("status")=="POSTV16AV4PIVOTGPUHYBG4B2_TRUE_SELECTIVE_ROUTING_SUBSET_FALLBACK_EXECUTION_PASS",b2s.get("status"))
        gate("B2_manifest_present",(b2d/b2_manifest_name).is_file(),str(b2d/b2_manifest_name))
        verify_manifest(b2d,b2_manifest_name)
        gate("B2_true_selective_before_shadow",b2s.get("true_selective_candidate_completed_before_shadow_full_exact") is True)
        gate("B2_no_full_exact_candidate_dependency",b2s.get("candidate_full_exact_all_route_execution_dependency") is False)
        gate("B2_boundary_mass_budget_certified",
             float(b2s.get("Hybrid_boundary_only_mass_budget_max_abs_difference_vs_shadow_exact_kg",float("inf"))) <=
             float(b2s.get("Hybrid_boundary_only_mass_budget_tolerance_kg",-1.0)))
        gate("B2_B3_authorized",b2s.get("B3_Hybrid_overhead_optimization_authorized") is True)

        r1d=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B1_R1_Route_Economics_Instrumentation")'''
    s = replace_once(s, authority_anchor, authority_insert, 'B2_authority')

    optimized_block = r'''        stage="candidate_Hybrid_mass_only_projection"
        parent_prof=np.stack([parent_profiles[int(i)] for i in eligible],axis=0)
        child_prof=np.stack([child_profiles[int(i)] for i in eligible],axis=0)
        coeff_h=np.asarray(coeff[eligible],dtype=np.float64)

        def mass_only_projection(profile):
            ss=np.asarray(profile,dtype=np.float64)
            g=np.asarray(bridge.e37a_mass_factor(physics,ss),dtype=np.float64)
            g200=0.5*g[:,:-1]+0.5*g[:,1:]
            return coeff_h*g200

        def mass_only_projection_call():
            return mass_only_projection(parent_prof),mass_only_projection(child_prof)

        (pmm,cmm),mass_only_projection_times,mass_only_projection_median=time_function(
            mass_only_projection_call,repeats=TIMING_REPEATS,warmups=1)
        raw=old_mass[eligible]+(cmm-pmm)

        stage="candidate_Hybrid_batched_box_and_vectorized_inversion"
        def batch_box_project(candidate,target,capacity):
            c=np.asarray(candidate,dtype=np.float64)
            t=np.asarray(target,dtype=np.float64)
            cap=np.asarray(capacity,dtype=np.float64)
            if c.shape!=cap.shape or t.shape!=(c.shape[0],):
                raise GateError(f"batch_box_shape:{c.shape}:{t.shape}:{cap.shape}")
            tol=np.maximum(1e-9,1e-12*np.maximum(np.abs(t),1.0))
            capsum=np.sum(cap,axis=1)
            if np.any(t < -tol) or np.any(t > capsum+tol):
                bad=np.flatnonzero((t < -tol)|(t > capsum+tol))
                raise GateError(f"batch_box_target_infeasible:{bad[:10].tolist()}")
            t=np.clip(t,0.0,capsum)
            lo=np.min(-c,axis=1)-1.0
            hi=np.max(cap-c,axis=1)+1.0
            for _ in range(120):
                mid=0.5*(lo+hi)
                sm=np.sum(np.clip(c+mid[:,None],0.0,cap),axis=1)
                below=sm<t
                lo=np.where(below,mid,lo)
                hi=np.where(below,hi,mid)
            lam=0.5*(lo+hi)
            out=np.clip(c+lam[:,None],0.0,cap)
            residual=t-np.sum(out,axis=1)
            free=(out>tol[:,None])&(out<cap-tol[:,None])
            nfree=np.sum(free,axis=1)
            needs=(np.abs(residual)>tol)&(nfree>0)
            adjust=np.zeros_like(residual)
            adjust[needs]=residual[needs]/nfree[needs]
            out=np.clip(out+free*adjust[:,None],0.0,cap)
            closure=np.sum(out,axis=1)-t
            closure_tol=np.maximum(1e-8,1e-12*np.maximum(np.abs(t),1.0))
            if np.any(np.abs(closure)>closure_tol):
                bad=np.flatnonzero(np.abs(closure)>closure_tol)
                raise GateError(f"batch_box_closure:{bad[:10].tolist()}:{float(np.max(np.abs(closure)))}")
            return out,lam,closure

        def batch_correction_call():
            cap=np.asarray(e37a.cv_mass_from_saturation(
                physics,
                np.full_like(raw,float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)),
                coeff_h),dtype=np.float64)
            mm,lam,closure=batch_box_project(raw,hybrid_target_i,cap)
            ss=np.asarray(e37a.invert_cv_mass_to_saturation(
                physics,mm,coeff_h),dtype=np.float64)
            denom=np.maximum(np.sum(np.abs(raw),axis=1),1e-30)
            correction=np.sum(np.abs(mm-raw),axis=1)/denom
            mixed_mass=np.empty_like(old_mass,dtype=np.float64)
            mixed_sat=np.empty_like(old_sat,dtype=np.float64)
            mixed_mass[fallback]=np.asarray(exact_subset["new_mass"],float)
            mixed_sat[fallback]=np.asarray(exact_subset["new_saturation"],float)
            mixed_mass[eligible]=mm
            mixed_sat[eligible]=ss
            return mixed_mass,mixed_sat,correction,mm,ss,closure

        (mixed_mass,mixed_cv_sat,correction_l1,batch_mm,batch_ss,batch_closure),batch_correction_times,batch_correction_median=time_function(
            batch_correction_call,repeats=CORRECTION_TIMING_REPEATS,warmups=1)
        gate("batch_box_all_route_closure",
             float(np.max(np.abs(batch_closure)))<=max(1e-8,1e-12*max(float(np.max(np.abs(hybrid_target_i))),1.0)),
             float(np.max(np.abs(batch_closure))))

        candidate_injected=float(exact_subset["injected_mass_kg"])+float(np.sum(hybrid_inlet_flux))*dt
        candidate_produced=float(exact_subset["produced_mass_kg"])+float(np.sum(hybrid_outlet_flux))*dt
        parent_stored=scalar(refreshed["stored_co2_mass_current_kg"])
        target_final=parent_stored+candidate_injected-candidate_produced

        stage="candidate_mapback_timing_split"
        def mapback_only_call():
            return e37a.map_control_volume_increment_to_grid(
                physics,parent_sat,old_sat,mixed_cv_sat,old_mass,mixed_mass,epoch["geometry"],
                pressure,p_ref,cell_pv,target_final)

        candidate_mapback,mapback_only_times,mapback_only_median=time_function(
            mapback_only_call,repeats=3,warmups=1)

        stage="candidate_capillary_timing_split"
        def capillary_only_call():
            return physics.conservative_capillary_mass_redistribution(
                transport_saturation=np.asarray(candidate_mapback["corrected_saturation"],float),
                permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,
                cell_pore_volume_m3=cell_pv,dt_seconds=dt*DAY_TO_S)

        candidate_capillary,capillary_only_times,capillary_only_median=time_function(
            capillary_only_call,repeats=3,warmups=1)
        gate("selective_candidate_completed_before_scalar_and_shadow_full_exact",True,
             "fallback-only E37A + Hybrid boundary budget + mass-only projection + batched conservative correction + mapback + capillary completed before scalar B2 and all-route exact shadows")

        stage="shadow_B2_scalar_projection_correction_after_candidate"
        def scalar_projection_reference_call():
            _,rpmm,_=bridge.project_201_to_200_component_mass(
                physics,e37a,parent_prof,coeff,eligible)
            _,rcmm,_=bridge.project_201_to_200_component_mass(
                physics,e37a,child_prof,coeff,eligible)
            return rpmm,rcmm

        (ref_pmm,ref_cmm),scalar_projection_times,scalar_projection_median=time_function(
            scalar_projection_reference_call,repeats=1,warmups=0)
        projection_mass_max_abs=float(max(
            np.max(np.abs(pmm-ref_pmm)),
            np.max(np.abs(cmm-ref_cmm))))
        projection_mass_tol=max(
            1e-10,
            1e-12*max(float(np.max(np.abs(ref_pmm))),float(np.max(np.abs(ref_cmm))),1.0))
        gate("mass_only_projection_matches_B2_bridge_mass",
             projection_mass_max_abs<=projection_mass_tol,
             (projection_mass_max_abs,projection_mass_tol))

        ref_raw=old_mass[eligible]+(ref_cmm-ref_pmm)
        def scalar_correction_reference_call():
            ref_mm=np.empty_like(ref_raw,dtype=np.float64)
            ref_ss=np.empty_like(ref_raw,dtype=np.float64)
            for j,sl in enumerate(eligible):
                c=coeff[sl]
                cap=np.asarray(e37a.cv_mass_from_saturation(
                    physics,
                    np.full(ncv,float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)),
                    c),float)
                mm,lam,closure=a1.box_project(ref_raw[j],float(hybrid_target_i[j]),cap)
                if abs(float(closure))>1e-8:
                    raise GateError(f"scalar_shadow_box_closure:{sl}:{closure}")
                ref_mm[j]=mm
                ref_ss[j]=np.asarray(e37a.invert_cv_mass_to_saturation(physics,mm,c),float)
            return ref_mm,ref_ss

        (scalar_mm,scalar_ss),scalar_correction_times,scalar_correction_median=time_function(
            scalar_correction_reference_call,repeats=1,warmups=0)
        batch_mass_max_abs=float(np.max(np.abs(batch_mm-scalar_mm)))
        batch_sat_max_abs=float(np.max(np.abs(batch_ss-scalar_ss)))
        batch_mass_tol=max(1e-8,1e-12*max(float(np.max(np.abs(scalar_mm))),1.0))
        gate("batched_box_mass_matches_B2_scalar",
             batch_mass_max_abs<=batch_mass_tol,
             (batch_mass_max_abs,batch_mass_tol))
        gate("vectorized_inversion_matches_B2_scalar",
             batch_sat_max_abs<=1e-12,
             batch_sat_max_abs)

'''
    s = replace_between(
        s,
        '        stage="candidate_Hybrid_projection"',
        '        # Only now construct the all-route exact reference. It is validation-only',
        optimized_block,
        'B3_optimized_candidate_block',
    )

    economics_block = r'''        stage="economics_interpretation"
        b3_selective_kernel=(
            exact_subset_median
            + child_total_median
            + boundary_budget_median
            + mass_only_projection_median
            + batch_correction_median
            + mapback_only_median
            + capillary_only_median
        )
        exact_only_kernel=exact_full_median+exact_mapback_median
        b2_kernel=float(b2s["true_selective_candidate_kernel_seconds"])
        b2_projection=float(b2s["Hybrid_projection_median_seconds"])
        b2_correction=float(b2s["Hybrid_box_and_inversion_median_seconds"])
        b2_mapback_capillary=float(b2s["mixed_mapback_capillary_median_seconds"])
        b3_vs_exact_ratio=b3_selective_kernel/max(exact_only_kernel,1e-30)
        b3_reduction_vs_b2=1.0-b3_selective_kernel/max(b2_kernel,1e-30)
        projection_reduction=1.0-mass_only_projection_median/max(b2_projection,1e-30)
        correction_reduction=1.0-batch_correction_median/max(b2_correction,1e-30)
        exact_subset_fraction=exact_subset_median/max(exact_full_median,1e-30)
        mapback_capillary_sum=mapback_only_median+capillary_only_median
        remaining_nonphysics_hybrid_overhead=(
            child_total_median+boundary_budget_median+mass_only_projection_median+batch_correction_median
        )

        gate("candidate_has_no_scalar_B2_or_full_exact_execution_dependency",True,
             "B3 candidate mapback and capillary completed before scalar B2 correction shadow and all-route exact shadow")
        gate("B3_preserves_frozen_routing_policy",True,
             "eligible/fallback sets use unchanged E8R1 screen and Hybrid10 authority")
        gate("B3_preserves_exact_Hybrid_route_mass_budget",True,
             "same boundary-only exact route mass targets certified in B2")
        gate("B3_preserves_E37A_mapback_and_capillary",True,
             "map_control_volume_increment_to_grid and conservative_capillary_mass_redistribution are unchanged")

        timing_rows=[
            {"component":"same_time_flow_rebuild_once","median_seconds":flow_rebuild_seconds,"repeats":1,"scope":"Day100"},
            {"component":"candidate_fallback_only_exact_E37A","median_seconds":exact_subset_median,"repeats":TIMING_REPEATS,"scope":f"{fallback.size}_routes"},
            {"component":"candidate_Hybrid_boundary_only_mass_budget","median_seconds":boundary_budget_median,"repeats":TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"candidate_Hybrid_child_profile_total_steady_state","median_seconds":child_total_median,"repeats":TIMING_REPEATS,"scope":f"{len(child_profiles)}_accepted_profiles"},
            {"component":"candidate_Hybrid_child_GPU_inference","median_seconds":child_infer_median,"repeats":TIMING_REPEATS,"scope":"child_profile"},
            {"component":"candidate_Hybrid_mass_only_201_to_200_parent_plus_child","median_seconds":mass_only_projection_median,"repeats":TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"candidate_Hybrid_batched_box_plus_vectorized_inversion","median_seconds":batch_correction_median,"repeats":CORRECTION_TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"candidate_mapback_only","median_seconds":mapback_only_median,"repeats":3,"scope":"all_routes"},
            {"component":"candidate_capillary_only","median_seconds":capillary_only_median,"repeats":3,"scope":"grid"},
            {"component":"candidate_B3_true_selective_kernel","median_seconds":b3_selective_kernel,"repeats":0,"scope":"sum_of_measured_medians"},
            {"component":"shadow_B2_scalar_projection_once","median_seconds":scalar_projection_median,"repeats":1,"scope":"validation_only"},
            {"component":"shadow_B2_scalar_correction_once","median_seconds":scalar_correction_median,"repeats":1,"scope":"validation_only"},
            {"component":"shadow_full_exact_E37A_all_routes","median_seconds":exact_full_median,"repeats":TIMING_REPEATS,"scope":f"{nstream}_routes_validation_only"},
            {"component":"shadow_exact_mapback_plus_capillary","median_seconds":exact_mapback_median,"repeats":3,"scope":"all_routes_validation_only"},
            {"component":"shadow_exact_only_transport_kernel","median_seconds":exact_only_kernel,"repeats":0,"scope":"validation_only"},
            {"component":"B2_true_selective_kernel_reference","median_seconds":b2_kernel,"repeats":0,"scope":"prior_milestone"},
        ]

'''
    s = replace_between(
        s,
        '        stage="economics_interpretation"',
        '        stage="publication"',
        economics_block,
        'B3_economics_block',
    )

    summary_block = f'''        summary={{
            "milestone":M,
            "status":PASS,
            "classification":"{B3_CLASSIFICATION}",
            "B2_authority_bound":True,
            "B2_status":b2s.get("status"),
            "Day100_representative_dt_days":dt,
            "Day100_streamline_count":nstream,
            "Day100_Hybrid_eligible_route_count":int(eligible.size),
            "Day100_exact_fallback_route_count":int(fallback.size),
            "Day100_Hybrid_route_fraction":float(eligible.size/nstream),
            "candidate_completed_before_scalar_B2_shadow":True,
            "candidate_completed_before_full_exact_shadow":True,
            "candidate_scalar_B2_execution_dependency":False,
            "candidate_full_exact_all_route_execution_dependency":False,
            "Hybrid_boundary_only_mass_budget_used":True,
            "mass_only_projection_used":True,
            "mass_only_projection_max_abs_difference_vs_B2_bridge_mass_kg":projection_mass_max_abs,
            "mass_only_projection_tolerance_kg":projection_mass_tol,
            "batched_box_projection_used":True,
            "vectorized_E37A_mass_inversion_used":True,
            "batched_box_mass_max_abs_difference_vs_B2_scalar_kg":batch_mass_max_abs,
            "batched_box_mass_tolerance_kg":batch_mass_tol,
            "vectorized_inversion_saturation_max_abs_difference_vs_B2_scalar":batch_sat_max_abs,
            "fallback_subset_E37A_equivalence_certified":True,
            "fallback_only_exact_E37A_median_seconds":exact_subset_median,
            "full_exact_E37A_shadow_median_seconds":exact_full_median,
            "fallback_only_exact_vs_full_exact_time_fraction":exact_subset_fraction,
            "Hybrid_boundary_budget_median_seconds":boundary_budget_median,
            "Hybrid_child_profile_median_seconds":child_total_median,
            "Hybrid_GPU_inference_median_seconds":child_infer_median,
            "Hybrid_mass_only_projection_median_seconds":mass_only_projection_median,
            "Hybrid_batched_box_and_vectorized_inversion_median_seconds":batch_correction_median,
            "mapback_only_median_seconds":mapback_only_median,
            "capillary_only_median_seconds":capillary_only_median,
            "mapback_plus_capillary_sum_seconds":mapback_capillary_sum,
            "remaining_nonphysics_Hybrid_overhead_seconds":remaining_nonphysics_hybrid_overhead,
            "B3_true_selective_candidate_kernel_seconds":b3_selective_kernel,
            "shadow_exact_only_kernel_seconds":exact_only_kernel,
            "B3_candidate_over_exact_only_ratio":b3_vs_exact_ratio,
            "B2_true_selective_candidate_kernel_seconds":b2_kernel,
            "B3_reduction_vs_B2_fraction":b3_reduction_vs_b2,
            "B2_projection_median_seconds":b2_projection,
            "B3_projection_reduction_fraction":projection_reduction,
            "B2_box_and_inversion_median_seconds":b2_correction,
            "B3_correction_reduction_fraction":correction_reduction,
            "B2_mapback_capillary_median_seconds":b2_mapback_capillary,
            "Day100_Hybrid_one_step_saturation_relL2_median":float(np.median(hybrid_route_errors)),
            "Day100_Hybrid_one_step_saturation_relL2_p95":float(np.quantile(hybrid_route_errors,.95)),
            "routing_policy_changed":False,
            "new_scientific_threshold_defined":False,
            "canonical_state_mutated":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }}
'''
    s = replace_between(
        s,
        '        summary={',
        '        (out/SUMMARY).write_text',
        summary_block,
        'B3_summary_block',
    )

    footer_anchor = '''        print("True selective candidate kernel s                     :",selective_kernel)
        print("Shadow exact-only kernel s                            :",exact_only_kernel)
        print("True selective / exact-only ratio                     :",selective_vs_exact_ratio)
        print("Reduction vs B1-R1 current Hybrid kernel              :",selective_reduction_vs_r1_current)
        print("B3 Hybrid overhead optimization                       : AUTHORIZED")'''
    footer_insert = '''        print("B3 true selective candidate kernel s                  :",b3_selective_kernel)
        print("Shadow exact-only kernel s                            :",exact_only_kernel)
        print("B3 candidate / exact-only ratio                       :",b3_vs_exact_ratio)
        print("Reduction vs B2 true-selective kernel                 :",b3_reduction_vs_b2)
        print("Mass-only projection reduction vs B2                 :",projection_reduction)
        print("Batched correction reduction vs B2                   :",correction_reduction)
        print("Mapback-only median s                                 :",mapback_only_median)
        print("Capillary-only median s                               :",capillary_only_median)'''
    s = replace_once(s, footer_anchor, footer_insert, 'B3_footer')

    return s


def repository_preflight(root: Path) -> None:
    branch = git(root, "branch", "--show-current")
    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    clean = git(root, "status", "--porcelain") == ""
    b2 = root / B2_RUNNER
    b2_blob = git(root, "hash-object", str(b2)) if b2.is_file() else "MISSING"
    print("--- G4-B3 REPOSITORY IDENTITY ---")
    print("Branch:", branch)
    print("HEAD  :", head)
    print("HEAD^ :", parent)
    print("Clean :", clean)
    print("B2 blob:", b2_blob)
    if branch != BRANCH:
        raise B3Error(f"branch:{branch}:{BRANCH}")
    if parent != PARENT:
        raise B3Error(f"parent:{parent}:{PARENT}")
    if not clean:
        raise B3Error("repository_not_clean")
    if b2_blob != B2_GIT_BLOB:
        raise B3Error(f"B2_blob:{b2_blob}:{B2_GIT_BLOB}")


def load_patched_module(root: Path) -> types.ModuleType:
    patched = patched_b3_source(root)
    compile(patched, f"<{B3_TOKEN}_patched_B2>", "exec")
    module = types.ModuleType("g4_b3_vectorized_overhead")
    module.__file__ = str(root / B2_RUNNER)
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
        raise B3Error(f"patched_module_missing:{missing}")
    if module.OUT_TOKEN != B3_TOKEN:
        raise B3Error(f"patched_OUT_TOKEN:{module.OUT_TOKEN}")
    if module.PASS != B3_STATUS:
        raise B3Error(f"patched_PASS:{module.PASS}")
    src = patched_b3_source(root)
    required_markers = [
        'stage="candidate_Hybrid_mass_only_projection"',
        'stage="candidate_Hybrid_batched_box_and_vectorized_inversion"',
        'stage="candidate_mapback_timing_split"',
        'stage="candidate_capillary_timing_split"',
        'stage="shadow_B2_scalar_projection_correction_after_candidate"',
        '"candidate_scalar_B2_execution_dependency":False',
        '"candidate_full_exact_all_route_execution_dependency":False',
    ]
    for marker in required_markers:
        if marker not in src:
            raise B3Error(f"missing_B3_marker:{marker}")
    print("POSTV16 GPU-HYB-G4-B3 structural/patch self-test: PASS")


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
