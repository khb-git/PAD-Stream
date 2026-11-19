#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, subprocess, sys, types
from pathlib import Path

MILESTONE="POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R4"
BRANCH="postv16-av4-pivot"
PARENT="44bc4945d1541e44c7b2d21043ceeafb1edcfc7e"
PARENT_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_R1_R1_R1_R1_Shadow_Teacher_Binding_Repair.py"
PARENT_GIT_BLOB="918b235f240800218dd860b8dad8c9c5c8b2dc9a"

TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R4"
PASS_STATUS="POSTV16AV4PIVOTGPUHYBG4B4R4_FIXED_SHAPE_GRAPH_EXACT_OUTPUT_PROBE_PASS"
BLOCK_STATUS="POSTV16AV4PIVOTGPUHYBG4B4R4_TECHNICAL_NUMERICAL_OR_AUTHORITY_BLOCK"
CLASSIFICATION="FIXED_256_PLUS_226_TF_FUNCTION_NON_XLA_GRAPH_EXACT_OUTPUT_IDENTITY_PROBE_COMPLETE"
PARENT_PASS="POSTV16AV4PIVOTGPUHYBG4B4R3R1R1R1R1_SHADOW_TEACHER_BINDING_REPAIR_PASS"

class R4Error(RuntimeError): pass

def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def replace_once(source,old,new,label):
    n=source.count(old)
    if n!=1:
        raise R4Error(f"patch_anchor_{label}_count:{n}")
    return source.replace(old,new,1)

def replace_region(source,start,end,replacement,label):
    if source.count(start)!=1:
        raise R4Error(f"patch_start_{label}_count:{source.count(start)}")
    i=source.find(start)
    j=source.find(end,i+len(start))
    if j<0:
        raise R4Error(f"patch_end_{label}_missing")
    return source[:i]+replacement+source[j:]

def import_exact(root,filename,expected_blob,module_name):
    p=root/filename
    if not p.is_file():
        raise R4Error(f"missing_source:{filename}")
    actual=git(root,"hash-object",str(p))
    if actual!=expected_blob:
        raise R4Error(f"source_blob:{filename}:{actual}:{expected_blob}")
    spec=importlib.util.spec_from_file_location(module_name,p)
    if spec is None or spec.loader is None:
        raise R4Error(f"import_spec:{filename}")
    m=importlib.util.module_from_spec(spec)
    sys.modules[module_name]=m
    spec.loader.exec_module(m)
    return m

def patched_source(root):
    parent=import_exact(root,PARENT_RUNNER,PARENT_GIT_BLOB,"g4b4r4_parent_authority")
    s=parent.patched_source(root)

    reps=[
        ('M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R3-R1-R1-R1-R1"',f'M="{MILESTONE}"',"milestone"),
        (f'PASS="{PARENT_PASS}"',f'PASS="{PASS_STATUS}"',"pass"),
        ('BLOCK="POSTV16AV4PIVOTGPUHYBG4B4R3R1R1R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"',f'BLOCK="{BLOCK_STATUS}"',"block"),
        ('PARENT="d6beaa53dfa0396a4defd2d2674844408a9cc5bb"',f'PARENT="{PARENT}"',"parent"),
        ('OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_R1_R1_R1_R1"',f'OUT_TOKEN="{TOKEN}"',"token"),
        ('print("POSTV16 GPU-HYB-G4-B4-R3-R1-R1-R1-R1 structural/patch self-test: PASS")',
         'print("POSTV16 GPU-HYB-G4-B4-R4 structural/patch self-test: PASS")',"selftest"),
        ('gate("parent_is_G4_B4_R3_R1_R1_R1_shadow_block_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',
         'gate("parent_is_G4_B4_R3_exact_output_PASS_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',"parentgate"),
    ]
    for a,b,l in reps:
        s=replace_once(s,a,b,l)

    old=(
        'print("G4-B4-R3-R1-R1-R1-R1 — SHADOW TEACHER BINDING REPAIR / EXACT-OUTPUT BATCH256 OPTIMIZATION")\n'
        '        print("REPAIRS ONLY THE FROZEN BATCH-256 SHADOW SCREEN ARGUMENT: RESERVOIR PHYSICS -> FROZEN R2/TEACHER AUTHORITY.")\n'
        '        print("THE R3 CANDIDATE, SCREEN FORMULA/THRESHOLDS, 256+REMAINDER GPU SHAPES, ROUTING, CONSERVATIVE MASS PIPELINE, MAPBACK, CAPILLARY, AND EXACT-OUTPUT GATES ARE UNCHANGED.")')
    new=(
        'print("G4-B4-R4 — FIXED-SHAPE NON-XLA GRAPH EXACT-OUTPUT PROBE")\n'
        '        print("PROBE ONLY: SAME HYBRID10 WEIGHTS, SAME 482 ROUTES, SAME 256+226 GPU BATCH GEOMETRY, SAME R3 SINGLE SCREEN/PROJECTION PATH.")\n'
        '        print("ONLY GPU MODEL EXECUTION IS WRAPPED IN TWO FIXED-SHAPE tf.function GRAPHS WITH jit_compile=False. ANY NON-EXACT OUTPUT BLOCKS THE PROBE.")')
    s=replace_once(s,old,new,"banner")

    authority='''        stage="artifact_authority"
        r3pass_dir=drive/BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_R1_R1_R1_R1_Route_Economics_Instrumentation"
        r3pass_path=r3pass_dir/"PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_R1_R1_R1_R1_Summary.json"
        gate("R3_exact_output_PASS_summary_present",r3pass_path.is_file(),str(r3pass_path))
        r3pass=js(r3pass_path)
        gate("R3_exact_output_PASS_status",r3pass.get("status")=="POSTV16AV4PIVOTGPUHYBG4B4R3R1R1R1R1_SHADOW_TEACHER_BINDING_REPAIR_PASS",r3pass.get("status"))
        gate("R3_exact_output_identity_certified",r3pass.get("exact_output_identity_certified") is True,r3pass.get("exact_output_identity_certified"))
        gate("R3_frozen_batch256_authority_preserved",r3pass.get("frozen_batch256_numerical_authority_preserved") is True,r3pass.get("frozen_batch256_numerical_authority_preserved"))
        gate("R3_authorizes_R4_fixed_shape_graph_probe",r3pass.get("B4_R4_fixed_shape_graph_exact_output_probe_authorized") is True,r3pass.get("B4_R4_fixed_shape_graph_exact_output_probe_authorized"))

'''
    s=replace_once(s,'        stage="artifact_authority"\n',authority,"r3pass_authority")

    graph_block='''        graph_fn_cache={}
        graph_compile_seconds=0.0
        graph_batch_sizes=set()

        def fixed_graph_for(batch_n:int,cond_dim:int):
            nonlocal graph_compile_seconds
            batch_n=int(batch_n); cond_dim=int(cond_dim)
            key=(batch_n,cond_dim)
            if key not in graph_fn_cache:
                xb=cached_xi_batch(batch_n)
                spec=tf.TensorSpec(shape=(batch_n,cond_dim),dtype=tf.float32)
                tcompile=time.perf_counter()
                @tf.function(input_signature=[spec],autograph=False,jit_compile=False)
                def graph_call(c):
                    return model([xb,c],training=False)[:,:,0]
                graph_call.get_concrete_function()
                graph_compile_seconds+=float(time.perf_counter()-tcompile)
                graph_fn_cache[key]=graph_call
            graph_batch_sizes.add(batch_n)
            return graph_fn_cache[key]

        def infer_r3_staged_eager_batch256(cond_arr):
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

        def infer_staged_batch256(cond_arr):
            cond_arr=np.asarray(cond_arr,dtype=np.float32)
            cond_tensor=tf.constant(cond_arr,tf.float32)
            n=int(cond_arr.shape[0])
            cond_dim=int(cond_arr.shape[1])
            out=np.empty((n,len(xi32)),dtype=np.float32)
            calls=0
            for start in range(0,n,256):
                end=min(start+256,n)
                c=cond_tensor[start:end]
                graph_call=fixed_graph_for(end-start,cond_dim)
                y=graph_call(c)
                out[start:end]=np.asarray(y.numpy(),dtype=np.float32)
                calls+=1
            return out,calls

'''
    s=replace_region(
        s,
        '        def infer_staged_batch256(cond_arr):\n',
        '        def screen_and_project_once(y,p,state,tau_nodes):\n',
        graph_block,
        "graph_inference"
    )

    r3_shadow='''        stage="r4_same_session_R3_staged_eager_GPU_shadow_after_candidate"

        def conditioning_for_day(day:float):
            xstar=(float(day)/terminal_days)*speed
            clocks=np.asarray([e11.classify_clock(float(x)) for x in xstar],dtype="U32")
            idx=np.flatnonzero(clocks=="LEARNED_WINDOW")
            cond=[]
            for i in idx:
                st=adapter.physical_time_state(elapsed_time=day,tau_end=float(terminal_days[i]),
                    characteristic_speed=speed,Sw_star=swstar)
                cond.append(adapter.conditioning_vector("HYBRID10",params,st))
            return np.asarray(cond,dtype=np.float32),idx

        r4_parent_cond,r4_parent_idx=conditioning_for_day(100.0)
        r4_child_cond,r4_child_idx=conditioning_for_day(100.0+dt)
        gate("R4_parent_conditioning_index_exact",np.array_equal(r4_parent_idx,parent_idx))
        gate("R4_child_conditioning_index_exact",np.array_equal(r4_child_idx,child_idx))
        gate("R4_learned_window_count_exact_482",int(r4_child_idx.size)==482,int(r4_child_idx.size))

        r3_eager_child_gpu_times=[]
        r3_eager_child_pred=None
        r3_eager_child_calls=None
        for _ in range(TIMING_REPEATS):
            t0=time.perf_counter()
            r3_eager_child_pred,r3_eager_child_calls=infer_r3_staged_eager_batch256(r4_child_cond)
            r3_eager_child_gpu_times.append(float(time.perf_counter()-t0))
        r3_eager_parent_pred,r3_eager_parent_calls=infer_r3_staged_eager_batch256(r4_parent_cond)
        r3_eager_child_gpu_median=float(statistics.median(r3_eager_child_gpu_times))

        gate("R4_graph_batch_sizes_exact_256_226",sorted(graph_batch_sizes)==[226,256],sorted(graph_batch_sizes))
        gate("R4_graph_function_count_exact_2",len(graph_fn_cache)==2,len(graph_fn_cache))
        gate("R4_graph_candidate_GPU_call_count_exact_2",child_gpu_call_count==2,child_gpu_call_count)
        gate("R4_R3_eager_shadow_GPU_call_count_exact_2",r3_eager_child_calls==2,r3_eager_child_calls)
        gate("R4_parent_raw_prediction_exact_vs_R3_staged_eager",np.array_equal(parent_pred,r3_eager_parent_pred))
        gate("R4_child_raw_prediction_exact_vs_R3_staged_eager",np.array_equal(child_pred,r3_eager_child_pred))

        stage="exact_output_batch256_shadow_after_candidate"
'''
    s=replace_once(s,'        stage="exact_output_batch256_shadow_after_candidate"\n',r3_shadow,"same_session_r3_shadow")

    econ='''        r4_selective_kernel=r3_selective_kernel
        r4_vs_exact_ratio=r3_vs_exact_ratio
        r3_pass_gpu=float(r3pass["Hybrid_GPU_R3_batch256_staged_median_seconds"])
        r3_pass_profile=float(r3pass["Hybrid_child_profile_R3_batch256_staged_median_seconds"])
        r3_pass_kernel=float(r3pass["R3_true_selective_candidate_kernel_seconds"])
        r4_gpu_reduction_vs_r3_pass=1.0-child_infer_median/max(r3_pass_gpu,1e-30)
        r4_profile_reduction_vs_r3_pass=1.0-child_total_median/max(r3_pass_profile,1e-30)
        r4_kernel_reduction_vs_r3_pass=1.0-r4_selective_kernel/max(r3_pass_kernel,1e-30)
        r4_gpu_reduction_vs_same_session_r3_eager=1.0-child_infer_median/max(r3_eager_child_gpu_median,1e-30)
        selected_exact_path_for_B5=("R4_FIXED_SHAPE_GRAPH" if r4_selective_kernel < r3_pass_kernel else "R3_STAGED_EAGER")

        stage="publication"
'''
    s=replace_once(s,'        stage="publication"\n',econ,"r4_economics")

    keymap=[
        ('"Hybrid_child_profile_R3_batch256_staged_median_seconds":child_total_median,','"Hybrid_child_profile_R4_fixed_shape_graph_median_seconds":child_total_median,'),
        ('"Hybrid_GPU_R3_batch256_staged_median_seconds":child_infer_median,','"Hybrid_GPU_R4_fixed_shape_graph_median_seconds":child_infer_median,'),
        ('"Hybrid_screen_projection_R3_once_median_seconds":child_screen_median,','"Hybrid_screen_projection_R4_once_median_seconds":child_screen_median,'),
        ('"R3_true_selective_candidate_kernel_seconds":r3_selective_kernel,','"R4_true_selective_candidate_kernel_seconds":r4_selective_kernel,'),
        ('"R3_candidate_over_exact_only_ratio":r3_vs_exact_ratio,','"R4_candidate_over_exact_only_ratio":r4_vs_exact_ratio,'),
    ]
    for a,b in keymap:
        s=replace_once(s,a,b,"summary_key")

    old_class='            "classification":"G4_B4_R3_EXACT_OUTPUT_PRESERVING_BATCH256_DESIGN_UNCHANGED_CANDIDATE_AND_SHADOW_TEACHER_BINDINGS_REPAIRED",'
    new_class=(
        f'            "classification":"{CLASSIFICATION}",\n'
        '            "R3_exact_output_PASS_authority_bound":True,\n'
        '            "R3_exact_output_PASS_status":r3pass.get("status"),\n'
        '            "fixed_shape_tf_function_used":True,\n'
        '            "tf_function_jit_compile":False,\n'
        '            "fixed_graph_batch_sizes":sorted(graph_batch_sizes),\n'
        '            "fixed_graph_function_count":len(graph_fn_cache),\n'
        '            "fixed_graph_trace_seconds":graph_compile_seconds,\n'
        '            "R3_same_session_staged_eager_GPU_median_seconds":r3_eager_child_gpu_median,\n'
        '            "R4_GPU_reduction_vs_R3_same_session_staged_eager_fraction":r4_gpu_reduction_vs_same_session_r3_eager,\n'
        '            "R4_GPU_reduction_vs_R3_PASS_fraction":r4_gpu_reduction_vs_r3_pass,\n'
        '            "R4_child_profile_reduction_vs_R3_PASS_fraction":r4_profile_reduction_vs_r3_pass,\n'
        '            "R4_kernel_reduction_vs_R3_PASS_fraction":r4_kernel_reduction_vs_r3_pass,\n'
        '            "selected_exact_transport_path_for_B5":selected_exact_path_for_B5,'
    )
    s=replace_once(s,old_class,new_class,"classification")
    s=replace_once(s,'            "B5_CPU_GPU_overlap_pipeline_probe_authorized":False,','            "B5_CPU_GPU_overlap_pipeline_probe_authorized":True,',"b5_auth")
    s=replace_once(s,'            "B4_R4_fixed_shape_graph_exact_output_probe_authorized":True,','            "B4_R4_fixed_shape_graph_exact_output_probe_completed":True,',"r4_complete")

    return s

def repository_preflight(root):
    branch=git(root,"branch","--show-current")
    par=git(root,"rev-parse","HEAD^")
    clean=git(root,"status","--porcelain")==""
    p=root/PARENT_RUNNER
    blob=git(root,"hash-object",str(p)) if p.is_file() else "MISSING"
    print("--- G4-B4-R4 REPOSITORY IDENTITY ---")
    print("Branch:",branch); print("HEAD  :",git(root,"rev-parse","HEAD")); print("HEAD^ :",par); print("Clean :",clean)
    print("R3 PASS runner blob:",blob); print("Expected           :",PARENT_GIT_BLOB)
    if branch!=BRANCH: raise R4Error(f"branch:{branch}:{BRANCH}")
    if par!=PARENT: raise R4Error(f"parent:{par}:{PARENT}")
    if not clean: raise R4Error("repository_not_clean")
    if blob!=PARENT_GIT_BLOB: raise R4Error(f"parent_blob:{blob}:{PARENT_GIT_BLOB}")

def load_patched_module(root):
    src=patched_source(root)
    compile(src,f"<{TOKEN}_patched_parent>","exec")
    m=types.ModuleType("g4_b4_r4_fixed_shape_graph")
    m.__file__=str(root/PARENT_RUNNER); m.__package__=None
    sys.modules[m.__name__]=m
    exec(compile(src,m.__file__,"exec"),m.__dict__)
    return m

def self_test(root):
    repository_preflight(root)
    src=patched_source(root)
    required=[
        '@tf.function(input_signature=[spec],autograph=False,jit_compile=False)',
        'def infer_r3_staged_eager_batch256(cond_arr):',
        'gate("R4_graph_batch_sizes_exact_256_226"',
        'gate("R4_parent_raw_prediction_exact_vs_R3_staged_eager"',
        'gate("R3_parent_raw_prediction_array_exact"',
        'gate("R3_capillary_saturation_array_exact"',
        '"B5_CPU_GPU_overlap_pipeline_probe_authorized":True',
        '"P4_authorized":False',
    ]
    for marker in required:
        if marker not in src:
            raise R4Error(f"missing_required_marker:{marker}")
    compile(src,f"<{TOKEN}_structural_selftest>","exec")
    m=load_patched_module(root)
    if m.OUT_TOKEN!=TOKEN: raise R4Error(f"patched_OUT_TOKEN:{m.OUT_TOKEN}")
    if m.PASS!=PASS_STATUS: raise R4Error(f"patched_PASS:{m.PASS}")
    print("POSTV16 GPU-HYB-G4-B4-R4 structural/patch self-test: PASS")

def main(root,drive):
    root=root.resolve(); drive=drive.resolve()
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
        print(MILESTONE,"WRAPPER BLOCK"); print("Exception:",repr(exc)); raise
