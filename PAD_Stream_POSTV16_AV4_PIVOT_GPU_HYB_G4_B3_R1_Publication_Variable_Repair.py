#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import types
from pathlib import Path

MILESTONE = "POSTV16-AV4-PIVOT-GPU-HYB-G4-B3-R1"
BRANCH = "postv16-av4-pivot"
PARENT = "fb49567af0094a4a93f4d674250efa234c9c4754"

B3_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_Vectorized_Hybrid_Overhead_Optimization.py"
B3_GIT_BLOB = "1db12b6102206eafb09db76a4b11228a093591c7"

R1_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_R1"
R1_STATUS = "POSTV16AV4PIVOTGPUHYBG4B3R1_PUBLICATION_VARIABLE_REPAIR_PASS"
R1_BLOCK = "POSTV16AV4PIVOTGPUHYBG4B3R1_TECHNICAL_OR_AUTHORITY_BLOCK"
R1_CLASSIFICATION = (
    "G4_B3_VECTORIZED_HYBRID_OVERHEAD_OPTIMIZATION_SCIENTIFIC_PATH_CERTIFIED_"
    "PUBLICATION_VARIABLE_REPAIR_COMPLETE"
)

B3_STATUS = "POSTV16AV4PIVOTGPUHYBG4B3_VECTORIZED_HYBRID_OVERHEAD_OPTIMIZATION_PASS"


class R1Error(RuntimeError):
    pass


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def replace_once(source: str, old: str, new: str, label: str) -> str:
    n = source.count(old)
    if n != 1:
        raise R1Error(f"patch_anchor_{label}_count:{n}")
    return source.replace(old, new, 1)


def replace_between(source: str, start: str, end: str, replacement: str, label: str) -> str:
    i = source.find(start)
    if i < 0:
        raise R1Error(f"patch_start_{label}_missing")
    if source.find(start, i + 1) >= 0:
        raise R1Error(f"patch_start_{label}_not_unique")
    j = source.find(end, i + len(start))
    if j < 0:
        raise R1Error(f"patch_end_{label}_missing")
    if source.find(end, j + 1) >= 0:
        raise R1Error(f"patch_end_{label}_not_unique")
    return source[:i] + replacement + source[j:]


def import_exact(root: Path, filename: str, expected_blob: str, module_name: str):
    p = root / filename
    if not p.is_file():
        raise R1Error(f"missing_source:{filename}")
    actual = git(root, "hash-object", str(p))
    if actual != expected_blob:
        raise R1Error(f"source_blob:{filename}:{actual}:{expected_blob}")
    spec = importlib.util.spec_from_file_location(module_name, p)
    if spec is None or spec.loader is None:
        raise R1Error(f"import_spec:{filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def patched_r1_source(root: Path) -> str:
    b3 = import_exact(root, B3_RUNNER, B3_GIT_BLOB, "g4b3r1_b3_authority")
    s = b3.patched_b3_source(root)

    replacements = [
        ('M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B3"', f'M="{MILESTONE}"', 'milestone'),
        (f'PASS="{B3_STATUS}"', f'PASS="{R1_STATUS}"', 'pass_status'),
        ('BLOCK="POSTV16AV4PIVOTGPUHYBG4B3_TECHNICAL_OR_AUTHORITY_BLOCK"', f'BLOCK="{R1_BLOCK}"', 'block_status'),
        ('PARENT="69a39a7eded5ca0d3dc0d354b9b4ee3e62be2c75"', f'PARENT="{PARENT}"', 'parent'),
        ('OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B3"', f'OUT_TOKEN="{R1_TOKEN}"', 'output_token'),
        ('print("POSTV16 GPU-HYB-G4-B3 structural self-test: PASS")',
         'print("POSTV16 GPU-HYB-G4-B3-R1 structural/patch self-test: PASS")', 'selftest_label'),
        ('gate("parent_is_G4_B2_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',
         'gate("parent_is_G4_B3_block_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))', 'parent_gate'),
    ]
    for old, new, label in replacements:
        s = replace_once(s, old, new, label)

    old_banner = (
        'print("G4-B3 — VECTORIZED HYBRID OVERHEAD OPTIMIZATION / TRUE SELECTIVE EXECUTION")\n'
        '        print("READ-ONLY PERFORMANCE REPAIR. PRESERVES B2 ROUTING, MASS BUDGETS, BOX CONSTRAINTS, E37A CONSTITUTIVE INVERSION, MAPBACK, AND CAPILLARY PHYSICS.")\n'
        '        print("OPTIMIZES ONLY REDUNDANT SATURATION INVERSION AND PYTHON PER-ROUTE CORRECTION OVERHEAD; SCALAR B2 PATH IS SHADOW VALIDATION ONLY.")'
    )
    new_banner = (
        'print("G4-B3-R1 — PUBLICATION VARIABLE REPAIR / VECTORIZED HYBRID OVERHEAD OPTIMIZATION")\n'
        '        print("REPAIR OF G4-B3 PUBLICATION/REPORTING ONLY. B3 SCIENTIFIC PATH, ROUTING, MASS BUDGETS, CORRECTION, MAPBACK, CAPILLARY, AND SHADOW VALIDATION ARE UNCHANGED.")\n'
        '        print("ORIGINAL G4-B3 BLOCK IS IMMUTABLE AND MUST BE BOUND AS A PUBLICATION-STAGE NAMEERROR WITH ALL RECORDED GATES PASS.")'
    )
    s = replace_once(s, old_banner, new_banner, 'banner')

    authority_anchor = '''        b2d=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B2_Route_Economics_Instrumentation")'''
    authority_insert = '''        b3_block_path=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_BLOCKED")/"POSTV16_AV4_PIVOT_GPU_HYB_G4_B3_Blocked_Report.json"
        gate("B3_blocked_predecessor_present",b3_block_path.is_file(),str(b3_block_path))
        b3block=js(b3_block_path)
        gate("B3_blocked_predecessor_status_exact",
             b3block.get("status")=="POSTV16AV4PIVOTGPUHYBG4B3_TECHNICAL_OR_AUTHORITY_BLOCK",
             b3block.get("status"))
        gate("B3_blocked_predecessor_failed_stage_publication",
             b3block.get("failed_stage")=="publication",b3block.get("failed_stage"))
        gate("B3_blocked_predecessor_exception_exact",
             "NameError" in str(b3block.get("exception","")) and "projection_median" in str(b3block.get("exception","")),
             b3block.get("exception"))
        b3_recorded_gates=b3block.get("gates",[])
        gate("B3_blocked_predecessor_has_recorded_gates",
             isinstance(b3_recorded_gates,list) and len(b3_recorded_gates)>0,
             len(b3_recorded_gates) if isinstance(b3_recorded_gates,list) else None)
        gate("B3_blocked_predecessor_all_recorded_gates_pass",
             all(g.get("pass") is True for g in b3_recorded_gates),
             sum(1 for g in b3_recorded_gates if g.get("pass") is True))

        b2d=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B2_Route_Economics_Instrumentation")'''
    s = replace_once(s, authority_anchor, authority_insert, 'B3_block_authority')

    publication = f'''        stage="publication"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)

        write_csv(out/TIMINGS,timing_rows)
        write_csv(out/ROUTES,route_rows)
        write_csv(out/GROUPS,group_rows)
        write_csv(out/TRAJECTORY,trajectory_rows)

        hybrid_route_errors=[
            float(r["Hybrid_saturation_relative_L2_vs_exact_one_step"])
            for r in route_rows if r["route_mode"]=="HYBRID"
        ]
        core_hybrid_errors=[
            float(r["Hybrid_saturation_relative_L2_vs_exact_one_step"])
            for r in route_rows
            if r["route_mode"]=="HYBRID" and r["node_fraction_r_lt_150ft"]>0
        ]
        noncore_hybrid_errors=[
            float(r["Hybrid_saturation_relative_L2_vs_exact_one_step"])
            for r in route_rows
            if r["route_mode"]=="HYBRID" and r["node_fraction_r_lt_150ft"]==0
        ]

        summary={{
            "milestone":M,
            "status":PASS,
            "classification":"{R1_CLASSIFICATION}",
            "B3_blocked_predecessor_bound":True,
            "B3_original_status":b3block.get("status"),
            "B3_original_failed_stage":b3block.get("failed_stage"),
            "B3_original_exception":b3block.get("exception"),
            "B3_original_all_recorded_gates_pass":True,
            "B3_R1_publication_repair_only":True,
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
            "Day100_core_exposed_Hybrid_one_step_saturation_relL2_median":float(np.median(core_hybrid_errors)) if core_hybrid_errors else None,
            "Day100_noncore_Hybrid_one_step_saturation_relL2_median":float(np.median(noncore_hybrid_errors)) if noncore_hybrid_errors else None,
            "route_level_spatial_attribution_created":True,
            "route_level_one_step_accuracy_attribution_created":True,
            "route_level_timing_is_batch_component_attribution_not_individual_route_timer":True,
            "routing_policy_changed":False,
            "new_scientific_threshold_defined":False,
            "canonical_state_mutated":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }}
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[
            {{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}}
            for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST
        ])

        print("="*202)
        print(M,"PASS")
        print("B3 predecessor failed only at publication             :",b3block.get("failed_stage"))
        print("Day100 Hybrid / fallback route count                  :",eligible.size,"/",fallback.size)
        print("Fallback-only exact E37A median s                     :",exact_subset_median)
        print("Hybrid child-profile median s                         :",child_total_median)
        print("Hybrid GPU inference median s                         :",child_infer_median)
        print("Hybrid mass-only 201->200 projection median s         :",mass_only_projection_median)
        print("Hybrid batched box+vectorized inversion median s      :",batch_correction_median)
        print("Mapback-only median s                                 :",mapback_only_median)
        print("Capillary-only median s                               :",capillary_only_median)
        print("B3 true selective candidate kernel s                  :",b3_selective_kernel)
        print("Shadow exact-only kernel s                            :",exact_only_kernel)
        print("B3 candidate / exact-only ratio                       :",b3_vs_exact_ratio)
        print("Reduction vs B2 true-selective kernel                 :",b3_reduction_vs_b2)
        print("Mass-only projection reduction vs B2                  :",projection_reduction)
        print("Batched correction reduction vs B2                    :",correction_reduction)
        print("="*202)
        return 0

'''
    s = replace_between(s, '        stage="publication"', '    except Exception as exc:', publication, 'publication_block')

    s = replace_once(
        s,
        '"B2_selective_routing_and_subset_fallback_design_authorized":False,',
        '"B3_R1_publication_repair_complete":False,',
        'blocked_report_semantics',
    )
    return s


def repository_preflight(root: Path) -> None:
    branch = git(root, "branch", "--show-current")
    parent = git(root, "rev-parse", "HEAD^")
    clean = git(root, "status", "--porcelain") == ""
    b3 = root / B3_RUNNER
    b3_blob = git(root, "hash-object", str(b3)) if b3.is_file() else "MISSING"
    print("--- G4-B3-R1 REPOSITORY IDENTITY ---")
    print("Branch:", branch)
    print("HEAD  :", git(root, "rev-parse", "HEAD"))
    print("HEAD^ :", parent)
    print("Clean :", clean)
    print("B3 blob:", b3_blob)
    if branch != BRANCH:
        raise R1Error(f"branch:{branch}:{BRANCH}")
    if parent != PARENT:
        raise R1Error(f"parent:{parent}:{PARENT}")
    if not clean:
        raise R1Error("repository_not_clean")
    if b3_blob != B3_GIT_BLOB:
        raise R1Error(f"B3_blob:{b3_blob}:{B3_GIT_BLOB}")


def load_patched_module(root: Path) -> types.ModuleType:
    patched = patched_r1_source(root)
    compile(patched, f"<{R1_TOKEN}_patched_B3>", "exec")
    module = types.ModuleType("g4_b3_r1_publication_repair")
    module.__file__ = str(root / B3_RUNNER)
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
        raise R1Error(f"patched_module_missing:{missing}")
    if module.OUT_TOKEN != R1_TOKEN:
        raise R1Error(f"patched_OUT_TOKEN:{module.OUT_TOKEN}")
    if module.PASS != R1_STATUS:
        raise R1Error(f"patched_PASS:{module.PASS}")
    src = patched_r1_source(root)
    required_markers = [
        'gate("B3_blocked_predecessor_failed_stage_publication"',
        '"B3_R1_publication_repair_only":True',
        '"Hybrid_mass_only_projection_median_seconds":mass_only_projection_median',
        '"Hybrid_batched_box_and_vectorized_inversion_median_seconds":batch_correction_median',
        'print("G4-B3-R1 — PUBLICATION VARIABLE REPAIR',
    ]
    for marker in required_markers:
        if marker not in src:
            raise R1Error(f"missing_R1_marker:{marker}")
    pub = src[src.index('        stage="publication"'):src.index('    except Exception as exc:')]
    stale_exact = [
        ':projection_median,', ',projection_median)',
        ':correction_median,', ',correction_median)',
        ':mixed_mapback_median,', ',mixed_mapback_median)',
        ':selective_kernel,', ',selective_kernel)',
        ':selective_vs_exact_ratio,', ',selective_vs_exact_ratio)',
    ]
    for token in stale_exact:
        if token in pub:
            raise R1Error(f"stale_publication_variable:{token}")
    print("POSTV16 GPU-HYB-G4-B3-R1 structural/patch self-test: PASS")


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
