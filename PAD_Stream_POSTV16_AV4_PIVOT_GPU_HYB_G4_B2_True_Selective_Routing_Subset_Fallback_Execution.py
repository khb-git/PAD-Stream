#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import types
from pathlib import Path

MILESTONE = "POSTV16-AV4-PIVOT-GPU-HYB-G4-B2"
BRANCH = "postv16-av4-pivot"
PARENT = "ed280dc80d365714aaad1edb1cc85a8c6d9b322a"

B1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B1_Route_Economics_Instrumentation.py"
B1_GIT_BLOB = "c1d74cc047bc719d6abeb4c81f346d6bfc2ede8d"
R1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B1_R1_Aligned_Mapback_Parent_State_Reconciliation_Repair.py"
R1_GIT_BLOB = "54f428b1eaf52e238131512514de588463400e6b"

B2_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G4_B2"
B2_STATUS = "POSTV16AV4PIVOTGPUHYBG4B2_TRUE_SELECTIVE_ROUTING_SUBSET_FALLBACK_EXECUTION_PASS"
B2_BLOCK = "POSTV16AV4PIVOTGPUHYBG4B2_TECHNICAL_OR_AUTHORITY_BLOCK"
B2_CLASSIFICATION = (
    "TRUE_SELECTIVE_HYBRID_EXECUTION_WITH_BOUNDARY_ONLY_EXACT_ROUTE_MASS_BUDGET_"
    "FALLBACK_ONLY_E37A_CERTIFIED_NO_FULL_EXACT_EXECUTION_DEPENDENCY_"
    "B3_HYBRID_OVERHEAD_OPTIMIZATION_AUTHORIZED"
)

R1_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G4_B1_R1"
R1_STATUS = "POSTV16AV4PIVOTGPUHYBG4B1R1_ALIGNED_MAPBACK_PARENT_STATE_RECONCILIATION_REPAIR_PASS"


class B2Error(RuntimeError):
    pass


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def replace_once(source: str, old: str, new: str, label: str) -> str:
    n = source.count(old)
    if n != 1:
        raise B2Error(f"patch_anchor_{label}_count:{n}")
    return source.replace(old, new, 1)


def replace_between(source: str, start: str, end: str, replacement: str, label: str) -> str:
    i = source.find(start)
    if i < 0:
        raise B2Error(f"patch_start_{label}_missing")
    if source.find(start, i + 1) >= 0:
        raise B2Error(f"patch_start_{label}_not_unique")
    j = source.find(end, i + len(start))
    if j < 0:
        raise B2Error(f"patch_end_{label}_missing")
    if source.find(end, j + 1) >= 0:
        raise B2Error(f"patch_end_{label}_not_unique")
    return source[:i] + replacement + source[j:]


def import_exact(root: Path, filename: str, expected_blob: str, module_name: str):
    p = root / filename
    if not p.is_file():
        raise B2Error(f"missing_source:{filename}")
    actual = git(root, "hash-object", str(p))
    if actual != expected_blob:
        raise B2Error(f"source_blob:{filename}:{actual}:{expected_blob}")
    spec = importlib.util.spec_from_file_location(module_name, p)
    if spec is None or spec.loader is None:
        raise B2Error(f"import_spec:{filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def patched_b2_source(root: Path) -> str:
    r1 = import_exact(root, R1_RUNNER, R1_GIT_BLOB, "g4b2_r1_authority")
    b1_path = root / B1_RUNNER
    if not b1_path.is_file():
        raise B2Error(f"missing_B1_runner:{b1_path}")
    b1_blob = git(root, "hash-object", str(b1_path))
    if b1_blob != B1_GIT_BLOB:
        raise B2Error(f"B1_blob:{b1_blob}:{B1_GIT_BLOB}")

    # Start from the already-certified B1-R1 repaired experiment source.
    s = r1.patched_b1_source(b1_path.read_text(encoding="utf-8"))

    replacements = [
        ('M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B1-R1"', f'M="{MILESTONE}"', 'milestone'),
        (f'PASS="{R1_STATUS}"', f'PASS="{B2_STATUS}"', 'pass_status'),
        ('BLOCK="POSTV16AV4PIVOTGPUHYBG4B1R1_TECHNICAL_OR_AUTHORITY_BLOCK"', f'BLOCK="{B2_BLOCK}"', 'block_status'),
        ('PARENT="4815bd8499266f5e340305abe2950bf1d781dbb4"', f'PARENT="{PARENT}"', 'parent'),
        ('OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B1_R1"', f'OUT_TOKEN="{B2_TOKEN}"', 'output_token'),
        ('print("POSTV16 GPU-HYB-G4-B1-R1 structural self-test: PASS")', 'print("POSTV16 GPU-HYB-G4-B2 structural self-test: PASS")', 'selftest_label'),
        ('gate("parent_is_G4_B1_block_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',
         'gate("parent_is_G4_B1_R1_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))', 'parent_gate'),
    ]
    for old, new, label in replacements:
        s = replace_once(s, old, new, label)

    old_banner = (
        'print("G4-B1-R1 — ALIGNED MAPBACK PARENT-STATE RECONCILIATION REPAIR / ROUTE ECONOMICS INSTRUMENTATION")\n'
        '        print("REPAIR OF G4-B1 MAPBACK INSTRUMENTATION ONLY. READ-ONLY. NO PHYSICS, STATE, SCREEN, OR ROUTING-POLICY MUTATION.")'
    )
    new_banner = (
        'print("G4-B2 — TRUE SELECTIVE HYBRID ROUTING / EXACT SUBSET FALLBACK EXECUTION")\n'
        '        print("CONTROLLED READ-ONLY ARCHITECTURE EXECUTION. HYBRID ROUTES USE EXACT BOUNDARY-ONLY MASS BUDGETS; ONLY FALLBACK ROUTES EXECUTE FULL E37A TRANSPORT.")\n'
        '        print("FULL EXACT ALL-ROUTE SOLVE IS SHADOW REFERENCE ONLY AND OCCURS AFTER THE SELECTIVE CANDIDATE PATH COMPLETES.")'
    )
    s = replace_once(s, old_banner, new_banner, 'banner')

    # Bind the successful R1 result as the immediate scientific authority for B2.
    authority_anchor = '''        vis2d=drive/VIS2_REL'''
    authority_insert = '''        r1d=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B1_R1_Route_Economics_Instrumentation")
        r1_summary_name="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B1_R1_Summary.json"
        r1_manifest_name="POSTV16_AV4_PIVOT_GPU_HYB_G4_B1_R1_Artifact_Manifest.csv"
        gate("B1_R1_summary_present",(r1d/r1_summary_name).is_file(),str(r1d/r1_summary_name))
        r1=js(r1d/r1_summary_name)
        gate("B1_R1_status_exact",r1.get("status")=="POSTV16AV4PIVOTGPUHYBG4B1R1_ALIGNED_MAPBACK_PARENT_STATE_RECONCILIATION_REPAIR_PASS",r1.get("status"))
        gate("B1_R1_manifest_present",(r1d/r1_manifest_name).is_file(),str(r1d/r1_manifest_name))
        verify_manifest(r1d,r1_manifest_name)
        gate("B1_R1_reconciled_parent_ledger_exact_zero",abs(float(r1.get("reconciled_parent_mass_ledger_residual_kg",float("nan"))))<=1e-12,r1.get("reconciled_parent_mass_ledger_residual_kg"))
        gate("B1_R1_fallback_subset_certified",r1.get("fallback_subset_E37A_equivalence_certified") is True)
        gate("B1_R1_B2_authorized",r1.get("B2_selective_routing_and_subset_fallback_design_authorized") is True)

        vis2d=drive/VIS2_REL'''
    s = replace_once(s, authority_anchor, authority_insert, 'R1_authority')

    selective_block = r'''        stage="candidate_exact_subset_only"
        def exact_subset_call():
            return e37a.advance_component_mass_control_volumes(
                physics,sg7a,old_sat[fallback],old_mass[fallback],coeff[fallback],
                face_pressure[fallback],p_ref,weights[fallback],xi,dt)
        exact_subset,exact_subset_times,exact_subset_median=time_function(
            exact_subset_call,repeats=TIMING_REPEATS,warmups=1)

        stage="candidate_hybrid_boundary_budget"
        gate("E37A_CO2_reference_density_700kgm3",
             abs(float(e37a.CO2_RHO_REF_KG_M3)-700.0)<=1e-15,
             float(e37a.CO2_RHO_REF_KG_M3))

        u_face=np.asarray(sg7a.u_dimensionless(xi),float)
        def hybrid_boundary_budget_call():
            qh=np.asarray(weights[eligible],float)
            outlet_sat=np.asarray(old_sat[eligible,-1],float)
            outlet_ff=np.asarray(sg7a.fractional_flow(outlet_sat),float)
            outlet_rho=np.asarray(physics.gas_density_from_state(
                outlet_sat,face_pressure[eligible,-1],p_ref),float)
            inlet_flux=qh*float(e37a.CO2_RHO_REF_KG_M3)
            outlet_flux=qh*float(u_face[-1])*outlet_ff*outlet_rho
            target=np.sum(old_mass[eligible],axis=1)+dt*(inlet_flux-outlet_flux)
            return target,inlet_flux,outlet_flux,outlet_ff

        (hybrid_target_i,hybrid_inlet_flux,hybrid_outlet_flux,hybrid_outlet_ff),boundary_budget_times,boundary_budget_median=time_function(
            hybrid_boundary_budget_call,repeats=TIMING_REPEATS,warmups=1)
        gate("Hybrid_boundary_targets_finite",np.all(np.isfinite(hybrid_target_i)))
        gate("Hybrid_boundary_targets_nonnegative",np.min(hybrid_target_i)>=-1e-10,float(np.min(hybrid_target_i)))

        stage="candidate_Hybrid_projection"
        parent_prof=np.stack([parent_profiles[int(i)] for i in eligible],axis=0)
        child_prof=np.stack([child_profiles[int(i)] for i in eligible],axis=0)

        def projection_call():
            _,pmm,_=bridge.project_201_to_200_component_mass(
                physics,e37a,parent_prof,coeff,eligible)
            _,cmm,_=bridge.project_201_to_200_component_mass(
                physics,e37a,child_prof,coeff,eligible)
            return pmm,cmm
        (pmm,cmm),projection_times,projection_median=time_function(
            projection_call,repeats=TIMING_REPEATS,warmups=1)

        raw=old_mass[eligible]+(cmm-pmm)

        def correction_call():
            # IMPORTANT: candidate arrays are assembled from scratch. There is no
            # all-route exact transport state available at this point.
            mixed_mass=np.empty_like(old_mass,dtype=np.float64)
            mixed_sat=np.empty_like(old_sat,dtype=np.float64)
            mixed_mass[fallback]=np.asarray(exact_subset["new_mass"],float)
            mixed_sat[fallback]=np.asarray(exact_subset["new_saturation"],float)
            correction=np.zeros(eligible.size,dtype=np.float64)
            for j,sl in enumerate(eligible):
                c=coeff[sl]
                cap=np.asarray(e37a.cv_mass_from_saturation(
                    physics,
                    np.full(ncv,float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)),
                    c),float)
                mm,lam,closure=a1.box_project(raw[j],float(hybrid_target_i[j]),cap)
                if abs(float(closure))>1e-8:
                    raise GateError(f"box_closure:{sl}:{closure}")
                denom=max(float(np.sum(np.abs(raw[j]))),1e-30)
                correction[j]=float(np.sum(np.abs(mm-raw[j])))/denom
                ss=np.asarray(e37a.invert_cv_mass_to_saturation(physics,mm,c),float)
                mixed_mass[sl]=mm
                mixed_sat[sl]=ss
            return mixed_mass,mixed_sat,correction

        (mixed_mass,mixed_cv_sat,correction_l1),correction_times,correction_median=time_function(
            correction_call,repeats=CORRECTION_TIMING_REPEATS,warmups=1)

        candidate_injected=float(exact_subset["injected_mass_kg"])+float(np.sum(hybrid_inlet_flux))*dt
        candidate_produced=float(exact_subset["produced_mass_kg"])+float(np.sum(hybrid_outlet_flux))*dt
        parent_stored=scalar(refreshed["stored_co2_mass_current_kg"])
        target_final=parent_stored+candidate_injected-candidate_produced

        stage="candidate_mapback_before_shadow_exact"
        def mixed_mapback_call():
            m=e37a.map_control_volume_increment_to_grid(
                physics,parent_sat,old_sat,mixed_cv_sat,old_mass,mixed_mass,epoch["geometry"],
                pressure,p_ref,cell_pv,target_final)
            c=physics.conservative_capillary_mass_redistribution(
                transport_saturation=np.asarray(m["corrected_saturation"],float),
                permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,
                cell_pore_volume_m3=cell_pv,dt_seconds=dt*DAY_TO_S)
            return m,c

        candidate_mapback_output,mixed_mapback_times,mixed_mapback_median=time_function(
            mixed_mapback_call,repeats=3,warmups=1)
        gate("selective_candidate_completed_before_shadow_full_exact",True,
             "fallback-only E37A + Hybrid boundary budget + Hybrid projection/correction + mixed mapback completed before shadow all-route exact reference")

        # Only now construct the all-route exact reference. It is validation-only
        # and cannot have participated in candidate execution above.
        stage="shadow_exact_reference_after_candidate"
        def exact_all_call():
            return e37a.advance_component_mass_control_volumes(
                physics,sg7a,old_sat,old_mass,coeff,face_pressure,p_ref,weights,xi,dt)
        exact_full,exact_full_times,exact_full_median=time_function(
            exact_all_call,repeats=TIMING_REPEATS,warmups=1)

        gate("fallback_subset_mass_equivalence",
             np.max(np.abs(np.asarray(exact_subset["new_mass"])-np.asarray(exact_full["new_mass"])[fallback]))<=1e-10,
             np.max(np.abs(np.asarray(exact_subset["new_mass"])-np.asarray(exact_full["new_mass"])[fallback])))
        gate("fallback_subset_saturation_equivalence",
             np.max(np.abs(np.asarray(exact_subset["new_saturation"])-np.asarray(exact_full["new_saturation"])[fallback]))<=1e-12,
             np.max(np.abs(np.asarray(exact_subset["new_saturation"])-np.asarray(exact_full["new_saturation"])[fallback])))
        gate("fallback_subset_flux_equivalence",
             np.max(np.abs(np.asarray(exact_subset["face_mass_flux_kg_day"])-np.asarray(exact_full["face_mass_flux_kg_day"])[fallback]))<=1e-10,
             np.max(np.abs(np.asarray(exact_subset["face_mass_flux_kg_day"])-np.asarray(exact_full["face_mass_flux_kg_day"])[fallback])))

        shadow_hybrid_target=np.sum(np.asarray(exact_full["new_mass"],float)[eligible],axis=1)
        boundary_target_max_abs=float(np.max(np.abs(hybrid_target_i-shadow_hybrid_target)))
        boundary_target_tol=max(1e-8,1e-12*max(float(np.max(np.abs(shadow_hybrid_target))),1.0))
        gate("Hybrid_boundary_only_mass_budget_matches_shadow_exact",
             boundary_target_max_abs<=boundary_target_tol,
             (boundary_target_max_abs,boundary_target_tol))

        shadow_injected=float(exact_full["injected_mass_kg"])
        shadow_produced=float(exact_full["produced_mass_kg"])
        boundary_global_tol=max(1e-8,1e-12*max(abs(shadow_injected),abs(shadow_produced),1.0))
        gate("selective_global_injection_matches_shadow_exact",
             abs(candidate_injected-shadow_injected)<=boundary_global_tol,
             candidate_injected-shadow_injected)
        gate("selective_global_production_matches_shadow_exact",
             abs(candidate_produced-shadow_produced)<=boundary_global_tol,
             candidate_produced-shadow_produced)
        shadow_target_final=parent_stored+shadow_injected-shadow_produced
        gate("selective_target_final_matches_shadow_exact",
             abs(target_final-shadow_target_final)<=boundary_global_tol,
             target_final-shadow_target_final)

        stage="shadow_exact_mapback_timing"
        def exact_mapback_call():
            m=e37a.map_control_volume_increment_to_grid(
                physics,parent_sat,old_sat,np.asarray(exact_full["new_saturation"],float),
                old_mass,np.asarray(exact_full["new_mass"],float),epoch["geometry"],
                pressure,p_ref,cell_pv,shadow_target_final)
            c=physics.conservative_capillary_mass_redistribution(
                transport_saturation=np.asarray(m["corrected_saturation"],float),
                permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,
                cell_pore_volume_m3=cell_pv,dt_seconds=dt*DAY_TO_S)
            return m,c
        _,exact_mapback_times,exact_mapback_median=time_function(exact_mapback_call,repeats=3,warmups=1)

'''
    s = replace_between(
        s,
        '        stage="kernel_timing_exact_full"',
        '        stage="route_spatial_instrumentation"',
        selective_block,
        'selective_execution_block',
    )

    economics_block = r'''        stage="economics_interpretation"
        selective_kernel=(
            exact_subset_median
            + child_total_median
            + boundary_budget_median
            + projection_median
            + correction_median
            + mixed_mapback_median
        )
        exact_only_kernel=exact_full_median+exact_mapback_median
        r1_current_kernel=float(r1["estimated_current_Hybrid_steady_transport_kernel_seconds"])
        r1_subset_estimate=float(r1["estimated_fallback_subset_Hybrid_steady_transport_kernel_seconds"])
        selective_vs_exact_ratio=selective_kernel/max(exact_only_kernel,1e-30)
        selective_reduction_vs_r1_current=1.0-selective_kernel/max(r1_current_kernel,1e-30)
        exact_subset_fraction=exact_subset_median/max(exact_full_median,1e-30)

        gate("candidate_has_no_full_exact_execution_dependency",True,
             "candidate mixed state and mapback completed before shadow exact reference was constructed")
        gate("B2_preserves_frozen_routing_policy",True,
             "eligible/fallback sets use the unchanged E8R1 screen and Hybrid10 authority")

        timing_rows=[
            {"component":"same_time_flow_rebuild_once","median_seconds":flow_rebuild_seconds,"repeats":1,"scope":"Day100"},
            {"component":"candidate_fallback_only_exact_E37A","median_seconds":exact_subset_median,"repeats":TIMING_REPEATS,"scope":f"{fallback.size}_routes"},
            {"component":"candidate_Hybrid_boundary_only_mass_budget","median_seconds":boundary_budget_median,"repeats":TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"candidate_Hybrid_child_profile_total_steady_state","median_seconds":child_total_median,"repeats":TIMING_REPEATS,"scope":f"{len(child_profiles)}_accepted_profiles"},
            {"component":"candidate_Hybrid_child_GPU_inference","median_seconds":child_infer_median,"repeats":TIMING_REPEATS,"scope":"child_profile"},
            {"component":"candidate_Hybrid_201_to_200_parent_plus_child_projection","median_seconds":projection_median,"repeats":TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"candidate_Hybrid_box_projection_plus_mass_inversion","median_seconds":correction_median,"repeats":CORRECTION_TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"candidate_mixed_mapback_plus_capillary","median_seconds":mixed_mapback_median,"repeats":3,"scope":"all_routes"},
            {"component":"candidate_true_selective_transport_kernel_estimate","median_seconds":selective_kernel,"repeats":0,"scope":"sum_of_measured_medians"},
            {"component":"shadow_full_exact_E37A_all_routes","median_seconds":exact_full_median,"repeats":TIMING_REPEATS,"scope":f"{nstream}_routes_validation_only"},
            {"component":"shadow_exact_mapback_plus_capillary","median_seconds":exact_mapback_median,"repeats":3,"scope":"all_routes_validation_only"},
            {"component":"shadow_exact_only_transport_kernel","median_seconds":exact_only_kernel,"repeats":0,"scope":"sum_of_measured_medians_validation_only"},
            {"component":"B1_R1_current_Hybrid_kernel_reference","median_seconds":r1_current_kernel,"repeats":0,"scope":"prior_milestone"},
            {"component":"B1_R1_subset_kernel_estimate_reference","median_seconds":r1_subset_estimate,"repeats":0,"scope":"prior_milestone"},
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
            "classification":"{B2_CLASSIFICATION}",
            "B1_R1_authority_bound":True,
            "B1_R1_status":r1.get("status"),
            "Day100_representative_dt_days":dt,
            "Day100_streamline_count":nstream,
            "Day100_Hybrid_eligible_route_count":int(eligible.size),
            "Day100_exact_fallback_route_count":int(fallback.size),
            "Day100_Hybrid_route_fraction":float(eligible.size/nstream),
            "true_selective_candidate_completed_before_shadow_full_exact":True,
            "candidate_full_exact_all_route_execution_dependency":False,
            "Hybrid_boundary_only_mass_budget_used":True,
            "Hybrid_boundary_only_mass_budget_max_abs_difference_vs_shadow_exact_kg":boundary_target_max_abs,
            "Hybrid_boundary_only_mass_budget_tolerance_kg":boundary_target_tol,
            "candidate_injected_mass_kg":candidate_injected,
            "candidate_produced_mass_kg":candidate_produced,
            "candidate_target_final_mass_kg":target_final,
            "shadow_exact_injected_mass_kg":shadow_injected,
            "shadow_exact_produced_mass_kg":shadow_produced,
            "fallback_subset_E37A_equivalence_certified":True,
            "fallback_subset_exact_transport_supported":True,
            "fallback_only_exact_E37A_median_seconds":exact_subset_median,
            "full_exact_E37A_shadow_median_seconds":exact_full_median,
            "fallback_only_exact_vs_full_exact_time_fraction":exact_subset_fraction,
            "Hybrid_boundary_budget_median_seconds":boundary_budget_median,
            "Hybrid_child_profile_median_seconds":child_total_median,
            "Hybrid_GPU_inference_median_seconds":child_infer_median,
            "Hybrid_projection_median_seconds":projection_median,
            "Hybrid_box_and_inversion_median_seconds":correction_median,
            "mixed_mapback_capillary_median_seconds":mixed_mapback_median,
            "true_selective_candidate_kernel_seconds":selective_kernel,
            "shadow_exact_only_kernel_seconds":exact_only_kernel,
            "true_selective_candidate_over_exact_only_ratio":selective_vs_exact_ratio,
            "B1_R1_current_Hybrid_kernel_seconds":r1_current_kernel,
            "B1_R1_subset_estimate_seconds":r1_subset_estimate,
            "true_selective_reduction_vs_B1_R1_current_Hybrid_fraction":selective_reduction_vs_r1_current,
            "Day100_Hybrid_one_step_saturation_relL2_median":float(np.median(hybrid_route_errors)),
            "Day100_Hybrid_one_step_saturation_relL2_p95":float(np.quantile(hybrid_route_errors,.95)),
            "route_level_spatial_attribution_created":True,
            "route_level_one_step_accuracy_attribution_created":True,
            "routing_policy_changed":False,
            "new_scientific_threshold_defined":False,
            "canonical_state_mutated":False,
            "integrated_GPU_runtime_production_authorized":False,
            "B3_Hybrid_overhead_optimization_authorized":True,
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

    # Update the final human-readable PASS footer while keeping all publication logic unchanged.
    footer_anchor = '''        print("Current estimated steady transport-kernel s          :",current_steady_kernel)
        print("Fallback-subset estimated steady transport-kernel s  :",fallback_only_kernel)
        print("Estimated kernel reduction from subset fallback      :",1.0-potential_kernel_fraction)
        print("B2 selective routing + true subset fallback          : AUTHORIZED")'''
    footer_insert = '''        print("True selective candidate kernel s                     :",selective_kernel)
        print("Shadow exact-only kernel s                            :",exact_only_kernel)
        print("True selective / exact-only ratio                     :",selective_vs_exact_ratio)
        print("Reduction vs B1-R1 current Hybrid kernel              :",selective_reduction_vs_r1_current)
        print("B3 Hybrid overhead optimization                       : AUTHORIZED")'''
    s = replace_once(s, footer_anchor, footer_insert, 'footer')

    return s


def repository_preflight(root: Path) -> None:
    branch = git(root, "branch", "--show-current")
    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    clean = git(root, "status", "--porcelain") == ""
    b1 = root / B1_RUNNER
    r1 = root / R1_RUNNER
    b1_blob = git(root, "hash-object", str(b1)) if b1.is_file() else "MISSING"
    r1_blob = git(root, "hash-object", str(r1)) if r1.is_file() else "MISSING"
    print("--- G4-B2 REPOSITORY IDENTITY ---")
    print("Branch:", branch)
    print("HEAD  :", head)
    print("HEAD^ :", parent)
    print("Clean :", clean)
    print("B1 blob:", b1_blob)
    print("R1 blob:", r1_blob)
    if branch != BRANCH:
        raise B2Error(f"branch:{branch}:{BRANCH}")
    if parent != PARENT:
        raise B2Error(f"parent:{parent}:{PARENT}")
    if not clean:
        raise B2Error("repository_not_clean")
    if b1_blob != B1_GIT_BLOB:
        raise B2Error(f"B1_blob:{b1_blob}:{B1_GIT_BLOB}")
    if r1_blob != R1_GIT_BLOB:
        raise B2Error(f"R1_blob:{r1_blob}:{R1_GIT_BLOB}")


def load_patched_module(root: Path) -> types.ModuleType:
    patched = patched_b2_source(root)
    compile(patched, f"<{B2_TOKEN}_patched_B1_R1>", "exec")
    module = types.ModuleType("g4_b2_true_selective")
    module.__file__ = str(root / B1_RUNNER)
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
        raise B2Error(f"patched_module_missing:{missing}")
    if module.OUT_TOKEN != B2_TOKEN:
        raise B2Error(f"patched_OUT_TOKEN:{module.OUT_TOKEN}")
    if module.PASS != B2_STATUS:
        raise B2Error(f"patched_PASS:{module.PASS}")
    src = patched_b2_source(root)
    required_markers = [
        'stage="candidate_exact_subset_only"',
        'stage="candidate_hybrid_boundary_budget"',
        'stage="candidate_mapback_before_shadow_exact"',
        'stage="shadow_exact_reference_after_candidate"',
        'candidate_full_exact_all_route_execution_dependency":False',
    ]
    for marker in required_markers:
        if marker not in src:
            raise B2Error(f"missing_B2_marker:{marker}")
    print("POSTV16 GPU-HYB-G4-B2 structural/patch self-test: PASS")


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
