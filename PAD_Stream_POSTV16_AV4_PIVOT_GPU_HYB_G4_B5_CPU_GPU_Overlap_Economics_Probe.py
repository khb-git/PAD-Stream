#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import types
from pathlib import Path

MILESTONE="POSTV16-AV4-PIVOT-GPU-HYB-G4-B5"
BRANCH="postv16-av4-pivot"
PARENT="030f7019b20c8ac4198255c4095213d801ee3079"

PARENT_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R4_Fixed_Shape_Graph_Exact_Output_Probe.py"
PARENT_GIT_BLOB="4c8d3ae85b69489807a559e55fec89005bd677fe"

TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B5"
PASS_STATUS="POSTV16AV4PIVOTGPUHYBG4B5_CPU_GPU_OVERLAP_ECONOMICS_PROBE_PASS"
BLOCK_STATUS="POSTV16AV4PIVOTGPUHYBG4B5_TECHNICAL_NUMERICAL_OR_AUTHORITY_BLOCK"
CLASSIFICATION=(
    "R4_FIXED_SHAPE_GRAPH_PLUS_FALLBACK_E37A_"
    "CPU_GPU_OVERLAP_READONLY_ECONOMICS_PROBE_COMPLETE"
)
PARENT_PASS="POSTV16AV4PIVOTGPUHYBG4B4R4_FIXED_SHAPE_GRAPH_EXACT_OUTPUT_PROBE_PASS"

class B5Error(RuntimeError):
    pass


def git(root: Path,*args: str) -> str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()


def replace_once(source: str,old: str,new: str,label: str) -> str:
    n=source.count(old)
    if n!=1:
        raise B5Error(f"patch_anchor_{label}_count:{n}")
    return source.replace(old,new,1)


def import_exact(root: Path,filename: str,expected_blob: str,module_name: str):
    p=root/filename
    if not p.is_file():
        raise B5Error(f"missing_source:{filename}")
    actual=git(root,"hash-object",str(p))
    if actual!=expected_blob:
        raise B5Error(f"source_blob:{filename}:{actual}:{expected_blob}")
    spec=importlib.util.spec_from_file_location(module_name,p)
    if spec is None or spec.loader is None:
        raise B5Error(f"import_spec:{filename}")
    m=importlib.util.module_from_spec(spec)
    sys.modules[module_name]=m
    spec.loader.exec_module(m)
    return m


def patched_source(root: Path) -> str:
    parent=import_exact(root,PARENT_RUNNER,PARENT_GIT_BLOB,"g4b5_parent_authority")
    s=parent.patched_source(root)

    replacements=[
        ('M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R4"',f'M="{MILESTONE}"',"milestone"),
        (f'PASS="{PARENT_PASS}"',f'PASS="{PASS_STATUS}"',"pass"),
        ('BLOCK="POSTV16AV4PIVOTGPUHYBG4B4R4_TECHNICAL_NUMERICAL_OR_AUTHORITY_BLOCK"',f'BLOCK="{BLOCK_STATUS}"',"block"),
        ('PARENT="44bc4945d1541e44c7b2d21043ceeafb1edcfc7e"',f'PARENT="{PARENT}"',"parent"),
        ('OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R4"',f'OUT_TOKEN="{TOKEN}"',"token"),
        ('print("POSTV16 GPU-HYB-G4-B4-R4 structural/patch self-test: PASS")',
         'print("POSTV16 GPU-HYB-G4-B5 structural/patch self-test: PASS")',"selftest"),
        ('gate("parent_is_G4_B4_R3_exact_output_PASS_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',
         'gate("parent_is_G4_B4_R4_exact_output_graph_PASS_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',"parentgate"),
    ]
    for old,new,label in replacements:
        s=replace_once(s,old,new,label)

    old_banner=(
        'print("G4-B4-R4 — FIXED-SHAPE NON-XLA GRAPH EXACT-OUTPUT PROBE")\n'
        '        print("PROBE ONLY: SAME HYBRID10 WEIGHTS, SAME 482 ROUTES, SAME 256+226 GPU BATCH GEOMETRY, SAME R3 SINGLE SCREEN/PROJECTION PATH.")\n'
        '        print("ONLY GPU MODEL EXECUTION IS WRAPPED IN TWO FIXED-SHAPE tf.function GRAPHS WITH jit_compile=False. ANY NON-EXACT OUTPUT BLOCKS THE PROBE.")'
    )
    new_banner=(
        'print("G4-B5 — R4 GPU / FALLBACK E37A CPU OVERLAP ECONOMICS PROBE")\n'
        '        print("READ-ONLY CONCURRENCY PROBE. THE CERTIFIED R4 CANDIDATE EXECUTES UNCHANGED BEFORE ANY OVERLAP REPLAY.")\n'
        '        print("REPLAYS ONLY R4 CHILD GRAPH INFERENCE AND THE 596-ROUTE FALLBACK E37A SOLVE CONCURRENTLY; BOTH REPLAY OUTPUTS MUST BE EXACTLY IDENTICAL TO AUTHORITY.")'
    )
    s=replace_once(s,old_banner,new_banner,"banner")

    authority='''        stage="artifact_authority"
        r4pass_dir=drive/BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R4_Route_Economics_Instrumentation"
        r4pass_path=r4pass_dir/"PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R4_Summary.json"
        gate("R4_PASS_summary_present",r4pass_path.is_file(),str(r4pass_path))
        r4pass=js(r4pass_path)
        gate("R4_PASS_status_exact",
             r4pass.get("status")=="POSTV16AV4PIVOTGPUHYBG4B4R4_FIXED_SHAPE_GRAPH_EXACT_OUTPUT_PROBE_PASS",
             r4pass.get("status"))
        gate("R4_exact_output_identity_certified",
             r4pass.get("exact_output_identity_certified") is True,
             r4pass.get("exact_output_identity_certified"))
        gate("R4_selected_for_B5",
             r4pass.get("selected_exact_transport_path_for_B5")=="R4_FIXED_SHAPE_GRAPH",
             r4pass.get("selected_exact_transport_path_for_B5"))
        gate("R4_B5_authorized",
             r4pass.get("B5_CPU_GPU_overlap_pipeline_probe_authorized") is True,
             r4pass.get("B5_CPU_GPU_overlap_pipeline_probe_authorized"))
        gate("R4_production_still_closed",
             r4pass.get("integrated_GPU_runtime_production_authorized") is False,
             r4pass.get("integrated_GPU_runtime_production_authorized"))

'''
    s=replace_once(s,'        stage="artifact_authority"\n',authority,"r4pass_authority")

    overlap_block='''        stage="B5_readonly_CPU_GPU_overlap_probe"

        from concurrent.futures import ThreadPoolExecutor

        OVERLAP_REPEATS=7
        OVERLAP_WARMUPS=2

        def exact_obj_equal(a,b):
            if isinstance(a,dict) and isinstance(b,dict):
                return set(a)==set(b) and all(exact_obj_equal(a[k],b[k]) for k in a)
            if isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)):
                return len(a)==len(b) and all(exact_obj_equal(x,y) for x,y in zip(a,b))
            if isinstance(a,np.ndarray) or isinstance(b,np.ndarray):
                aa=np.asarray(a); bb=np.asarray(b)
                return aa.shape==bb.shape and aa.dtype==bb.dtype and np.array_equal(aa,bb)
            if isinstance(a,(np.generic,)):
                a=a.item()
            if isinstance(b,(np.generic,)):
                b=b.item()
            return a==b

        def overlap_gpu_call():
            pred,calls=infer_staged_batch256(r4_child_cond)
            return pred,calls

        def overlap_cpu_fallback_call():
            return exact_subset_call()

        trace_counts_before={
            str(k):int(fn.experimental_get_tracing_count())
            for k,fn in graph_fn_cache.items()
        }
        graph_compile_seconds_before=float(graph_compile_seconds)
        graph_cache_size_before=len(graph_fn_cache)

        for _ in range(OVERLAP_WARMUPS):
            gp,gc=overlap_gpu_call()
            cp=overlap_cpu_fallback_call()
            gate("B5_warmup_GPU_prediction_exact",np.array_equal(gp,child_pred))
            gate("B5_warmup_GPU_call_count_exact_2",gc==2,gc)
            gate("B5_warmup_fallback_E37A_exact",exact_obj_equal(cp,exact_subset))

        gpu_only_times=[]
        cpu_only_times=[]
        serial_pair_times=[]
        overlap_pair_times=[]
        overlap_predictions=[]
        overlap_fallbacks=[]

        for _ in range(OVERLAP_REPEATS):
            t0=time.perf_counter()
            gp,gc=overlap_gpu_call()
            gpu_only_times.append(float(time.perf_counter()-t0))
            gate("B5_GPU_only_prediction_exact",np.array_equal(gp,child_pred))
            gate("B5_GPU_only_call_count_exact_2",gc==2,gc)

            t0=time.perf_counter()
            cp=overlap_cpu_fallback_call()
            cpu_only_times.append(float(time.perf_counter()-t0))
            gate("B5_CPU_only_fallback_exact",exact_obj_equal(cp,exact_subset))

            t0=time.perf_counter()
            sgp,sgc=overlap_gpu_call()
            scp=overlap_cpu_fallback_call()
            serial_pair_times.append(float(time.perf_counter()-t0))
            gate("B5_serial_GPU_prediction_exact",np.array_equal(sgp,child_pred))
            gate("B5_serial_GPU_call_count_exact_2",sgc==2,sgc)
            gate("B5_serial_fallback_exact",exact_obj_equal(scp,exact_subset))

        with ThreadPoolExecutor(max_workers=2,thread_name_prefix="PADStreamG4B5") as pool:
            for _ in range(OVERLAP_REPEATS):
                t0=time.perf_counter()
                fg=pool.submit(overlap_gpu_call)
                fc=pool.submit(overlap_cpu_fallback_call)
                gp,gc=fg.result()
                cp=fc.result()
                overlap_pair_times.append(float(time.perf_counter()-t0))
                overlap_predictions.append(gp)
                overlap_fallbacks.append(cp)
                gate("B5_overlap_GPU_prediction_exact",np.array_equal(gp,child_pred))
                gate("B5_overlap_GPU_call_count_exact_2",gc==2,gc)
                gate("B5_overlap_fallback_E37A_exact",exact_obj_equal(cp,exact_subset))

        trace_counts_after={
            str(k):int(fn.experimental_get_tracing_count())
            for k,fn in graph_fn_cache.items()
        }
        graph_compile_seconds_after=float(graph_compile_seconds)
        graph_cache_size_after=len(graph_fn_cache)

        gate("B5_graph_cache_size_preserved_2",
             graph_cache_size_before==2 and graph_cache_size_after==2,
             (graph_cache_size_before,graph_cache_size_after))
        gate("B5_graph_trace_counts_unchanged",
             trace_counts_after==trace_counts_before,
             (trace_counts_before,trace_counts_after))
        gate("B5_graph_compile_seconds_unchanged",
             graph_compile_seconds_after==graph_compile_seconds_before,
             (graph_compile_seconds_before,graph_compile_seconds_after))
        gate("B5_graph_batch_sizes_still_256_226",
             sorted(graph_batch_sizes)==[226,256],
             sorted(graph_batch_sizes))

        gpu_only_median=float(statistics.median(gpu_only_times))
        cpu_only_median=float(statistics.median(cpu_only_times))
        serial_pair_median=float(statistics.median(serial_pair_times))
        overlap_pair_median=float(statistics.median(overlap_pair_times))
        overlap_saved_seconds=serial_pair_median-overlap_pair_median
        overlap_reduction_fraction=1.0-overlap_pair_median/max(serial_pair_median,1e-30)
        overlap_theoretical_floor=max(gpu_only_median,cpu_only_median)
        overlap_theoretical_max_saving=min(gpu_only_median,cpu_only_median)
        overlap_efficiency_fraction=(
            overlap_saved_seconds/max(overlap_theoretical_max_saving,1e-30)
        )
        overlap_economically_positive=bool(overlap_pair_median<serial_pair_median)

        r4_reference_kernel=float(r4pass["R4_true_selective_candidate_kernel_seconds"])
        r4_reference_exact=float(r4pass["shadow_exact_only_kernel_seconds"])
        b5_modeled_kernel=max(0.0,r4_reference_kernel-overlap_saved_seconds)
        b5_modeled_over_exact_ratio=b5_modeled_kernel/max(r4_reference_exact,1e-30)

        stage="publication"
'''
    s=replace_once(s,'        stage="publication"\n',overlap_block,"overlap_probe")

    old_class='            "classification":"FIXED_256_PLUS_226_TF_FUNCTION_NON_XLA_GRAPH_EXACT_OUTPUT_IDENTITY_PROBE_COMPLETE",'
    new_class=(
        f'            "classification":"{CLASSIFICATION}",\n'
        '            "R4_PASS_authority_bound":True,\n'
        '            "R4_selected_exact_transport_path":"R4_FIXED_SHAPE_GRAPH",\n'
        '            "B5_overlap_probe_readonly":True,\n'
        '            "B5_overlap_repeats":OVERLAP_REPEATS,\n'
        '            "B5_overlap_warmups":OVERLAP_WARMUPS,\n'
        '            "B5_GPU_only_median_seconds":gpu_only_median,\n'
        '            "B5_CPU_fallback_only_median_seconds":cpu_only_median,\n'
        '            "B5_serial_GPU_plus_fallback_median_seconds":serial_pair_median,\n'
        '            "B5_overlapped_GPU_plus_fallback_median_seconds":overlap_pair_median,\n'
        '            "B5_overlap_saved_seconds":overlap_saved_seconds,\n'
        '            "B5_overlap_reduction_fraction":overlap_reduction_fraction,\n'
        '            "B5_overlap_theoretical_floor_seconds":overlap_theoretical_floor,\n'
        '            "B5_overlap_theoretical_max_saving_seconds":overlap_theoretical_max_saving,\n'
        '            "B5_overlap_efficiency_fraction":overlap_efficiency_fraction,\n'
        '            "B5_overlap_economically_positive":overlap_economically_positive,\n'
        '            "B5_graph_trace_counts_before":trace_counts_before,\n'
        '            "B5_graph_trace_counts_after":trace_counts_after,\n'
        '            "B5_graph_cache_size_before":graph_cache_size_before,\n'
        '            "B5_graph_cache_size_after":graph_cache_size_after,\n'
        '            "B5_graph_compile_seconds_before":graph_compile_seconds_before,\n'
        '            "B5_graph_compile_seconds_after":graph_compile_seconds_after,\n'
        '            "B5_modeled_integrated_kernel_seconds":b5_modeled_kernel,\n'
        '            "B5_modeled_integrated_over_exact_only_ratio":b5_modeled_over_exact_ratio,\n'
        '            "B5_integrated_overlap_candidate_selected":overlap_economically_positive,\n'
        '            "G4_B4_fixed_shape_graph_transport_authority_preserved":True,\n'
        '            "additional_GPU_physics_offload_authorized":False,\n'
        '            "G4_runtime_optimization_phase_auto_extended":False,'
    )
    s=replace_once(s,old_class,new_class,"classification")

    s=replace_once(
        s,
        '            "B5_CPU_GPU_overlap_pipeline_probe_authorized":True,',
        '            "B5_CPU_GPU_overlap_pipeline_probe_completed":True,',
        "b5_completed"
    )

    return s


def repository_preflight(root: Path) -> None:
    branch=git(root,"branch","--show-current")
    head=git(root,"rev-parse","HEAD")
    par=git(root,"rev-parse","HEAD^")
    clean=git(root,"status","--porcelain")==""
    p=root/PARENT_RUNNER
    blob=git(root,"hash-object",str(p)) if p.is_file() else "MISSING"

    print("--- G4-B5 REPOSITORY IDENTITY ---")
    print("Branch:",branch)
    print("HEAD  :",head)
    print("HEAD^ :",par)
    print("Clean :",clean)
    print("R4 PASS runner blob:",blob)
    print("Expected           :",PARENT_GIT_BLOB)

    if branch!=BRANCH:
        raise B5Error(f"branch:{branch}:{BRANCH}")
    if par!=PARENT:
        raise B5Error(f"parent:{par}:{PARENT}")
    if not clean:
        raise B5Error("repository_not_clean")
    if blob!=PARENT_GIT_BLOB:
        raise B5Error(f"parent_blob:{blob}:{PARENT_GIT_BLOB}")


def load_patched_module(root: Path) -> types.ModuleType:
    src=patched_source(root)
    compile(src,f"<{TOKEN}_patched_parent>","exec")
    m=types.ModuleType("g4_b5_cpu_gpu_overlap")
    m.__file__=str(root/PARENT_RUNNER)
    m.__package__=None
    sys.modules[m.__name__]=m
    exec(compile(src,m.__file__,"exec"),m.__dict__)
    return m


def self_test(root: Path) -> None:
    repository_preflight(root)
    src=patched_source(root)

    required=[
        'from concurrent.futures import ThreadPoolExecutor',
        'OVERLAP_REPEATS=7',
        'def overlap_gpu_call():',
        'def overlap_cpu_fallback_call():',
        'gate("B5_overlap_GPU_prediction_exact"',
        'gate("B5_overlap_fallback_E37A_exact"',
        'gate("B5_graph_trace_counts_unchanged"',
        'gate("B5_graph_compile_seconds_unchanged"',
        '"B5_CPU_GPU_overlap_pipeline_probe_completed":True',
        '"additional_GPU_physics_offload_authorized":False',
        '"integrated_GPU_runtime_production_authorized":False',
        '"P4_authorized":False',
        '"new_numerical_equivalence_tolerance_defined":False',
    ]
    for marker in required:
        if marker not in src:
            raise B5Error(f"missing_required_marker:{marker}")

    compile(src,f"<{TOKEN}_structural_selftest>","exec")
    m=load_patched_module(root)

    if m.OUT_TOKEN!=TOKEN:
        raise B5Error(f"patched_OUT_TOKEN:{m.OUT_TOKEN}")
    if m.PASS!=PASS_STATUS:
        raise B5Error(f"patched_PASS:{m.PASS}")

    print("POSTV16 GPU-HYB-G4-B5 structural/patch self-test: PASS")


def main(root: Path,drive: Path) -> int:
    root=root.resolve()
    drive=drive.resolve()
    repository_preflight(root)
    return int(load_patched_module(root).main(root,drive))


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    try:
        if args.self_test:
            self_test(args.project_root.resolve())
            raise SystemExit(0)
        raise SystemExit(main(args.project_root,args.drive_root))
    except Exception as exc:
        print(MILESTONE,"WRAPPER BLOCK")
        print("Exception:",repr(exc))
        raise
