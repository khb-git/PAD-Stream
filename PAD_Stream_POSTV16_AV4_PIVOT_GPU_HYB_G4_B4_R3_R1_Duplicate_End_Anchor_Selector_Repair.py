#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, subprocess, sys, types
from pathlib import Path

MILESTONE="POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R3-R1"
BRANCH="postv16-av4-pivot"
PARENT="dc32145844dd0cf7ac4500dad532e3d88466e57c"
R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_Exact_Output_Preserving_Batch256_Staging_Optimization.py"
R3_GIT_BLOB="4ba2b5bfaf6503d14d004d11c2743415d091b963"

R1_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_R1"
R1_STATUS="POSTV16AV4PIVOTGPUHYBG4B4R3R1_DUPLICATE_END_ANCHOR_SELECTOR_REPAIR_PASS"
R1_BLOCK="POSTV16AV4PIVOTGPUHYBG4B4R3R1_TECHNICAL_OR_AUTHORITY_BLOCK"
R1_CLASSIFICATION="G4_B4_R3_EXACT_OUTPUT_PRESERVING_BATCH256_DESIGN_UNCHANGED_DUPLICATE_END_ANCHOR_SELECTOR_REPAIRED"
R3_STATUS="POSTV16AV4PIVOTGPUHYBG4B4R3_EXACT_OUTPUT_PRESERVING_BATCH256_STAGING_OPTIMIZATION_PASS"

CANDIDATE_END='        eligible=np.asarray(sorted(set(parent_profiles).intersection(child_profiles)),dtype=np.int64)'
CANDIDATE_END_PAIR=CANDIDATE_END+"\n"+CANDIDATE_END

class R1Error(RuntimeError): pass

def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def replace_once(source,old,new,label):
    n=source.count(old)
    if n!=1: raise R1Error(f"patch_anchor_{label}_count:{n}")
    return source.replace(old,new,1)

def import_exact(root,filename,expected_blob,module_name):
    p=root/filename
    if not p.is_file(): raise R1Error(f"missing_source:{filename}")
    actual=git(root,"hash-object",str(p))
    if actual!=expected_blob: raise R1Error(f"source_blob:{filename}:{actual}:{expected_blob}")
    spec=importlib.util.spec_from_file_location(module_name,p)
    if spec is None or spec.loader is None: raise R1Error(f"import_spec:{filename}")
    m=importlib.util.module_from_spec(spec); sys.modules[module_name]=m; spec.loader.exec_module(m); return m

def patched_r1_source(root):
    r3=import_exact(root,R3_RUNNER,R3_GIT_BLOB,"g4b4r3r1_r3_authority")
    original_replace_between=r3.replace_between

    def repaired_replace_between(source,start,end,replacement,label):
        if label!="candidate_profile_pipeline":
            return original_replace_between(source,start,end,replacement,label)
        if source.count(start)!=1:
            raise R1Error(f"candidate_profile_start_count:{source.count(start)}")
        if source.count(CANDIDATE_END_PAIR)!=1:
            raise R1Error(f"candidate_profile_duplicate_end_pair_count:{source.count(CANDIDATE_END_PAIR)}")
        i=source.find(start)
        j=source.find(CANDIDATE_END_PAIR,i+len(start))
        if j<0:
            raise R1Error("candidate_profile_duplicate_end_pair_missing_after_start")
        return source[:i]+replacement+source[j+len(CANDIDATE_END_PAIR):]

    r3.replace_between=repaired_replace_between
    s=r3.patched_r3_source(root)

    reps=[
      ('M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R3"',f'M="{MILESTONE}"','milestone'),
      (f'PASS="{R3_STATUS}"',f'PASS="{R1_STATUS}"','pass'),
      ('BLOCK="POSTV16AV4PIVOTGPUHYBG4B4R3_TECHNICAL_OR_AUTHORITY_BLOCK"',f'BLOCK="{R1_BLOCK}"','block'),
      ('PARENT="eec16bfd57987ba9c9c8d04c853d86c83a53ce8f"',f'PARENT="{PARENT}"','parent'),
      ('OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3"',f'OUT_TOKEN="{R1_TOKEN}"','token'),
      ('print("POSTV16 GPU-HYB-G4-B4-R3 structural/patch self-test: PASS")','print("POSTV16 GPU-HYB-G4-B4-R3-R1 structural/patch self-test: PASS")','selftest'),
      ('gate("parent_is_G4_B4_R2_audit_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))','gate("parent_is_G4_B4_R3_failed_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))','parentgate'),
    ]
    for a,b,l in reps: s=replace_once(s,a,b,l)

    old=(
      'print("G4-B4-R3 — EXACT-OUTPUT-PRESERVING BATCH-256 STAGING OPTIMIZATION")\n'
      '        print("FROZEN NUMERICAL AUTHORITY: SAME 256+REMAINDER GPU BATCH SHAPES, SAME HYBRID10 WEIGHTS, SAME ROUTING, SAME CONSERVATIVE MASS PIPELINE.")\n'
      '        print("OPTIMIZES ONLY XI INPUT STAGING AND DUPLICATE SCREEN/PROJECTION WORK. RAW PREDICTIONS AND FINAL STATE MUST BE EXACTLY IDENTICAL TO THE ORIGINAL BATCH-256 PATH.")')
    new=(
      'print("G4-B4-R3-R1 — DUPLICATE END-ANCHOR SELECTOR REPAIR / EXACT-OUTPUT BATCH256 OPTIMIZATION")\n'
      '        print("REPAIRS ONLY R3 PATCH ASSEMBLY. THE BATCH-256 NUMERICAL AUTHORITY, CACHED-XI CANDIDATE, SINGLE SCREEN/PROJECTION PATH, MASS PIPELINE, MAPBACK, AND CAPILLARY DESIGN ARE UNCHANGED.")\n'
      '        print("FAILED R3 COMMIT dc32145844dd0cf7ac4500dad532e3d88466e57c REMAINS IMMUTABLE.")')
    s=replace_once(s,old,new,'banner')

    old='            "classification":"FROZEN_BATCH256_HYBRID10_OUTPUT_EXACT_CACHED_XI_STAGING_SINGLE_SCREEN_PROJECTION_PIPELINE_CERTIFIED",'
    new=(f'            "classification":"{R1_CLASSIFICATION}",\n'
         '            "R3_failed_commit_bound":True,\n'
         '            "R3_R1_duplicate_end_anchor_selector_repair_only":True,')
    s=replace_once(s,old,new,'classification')
    return s

def repository_preflight(root):
    branch=git(root,"branch","--show-current"); head=git(root,"rev-parse","HEAD")
    par=git(root,"rev-parse","HEAD^"); clean=git(root,"status","--porcelain")==""
    p=root/R3_RUNNER; blob=git(root,"hash-object",str(p)) if p.is_file() else "MISSING"
    print("--- G4-B4-R3-R1 REPOSITORY IDENTITY ---")
    print("Branch:",branch); print("HEAD  :",head); print("HEAD^ :",par); print("Clean :",clean)
    print("R3 runner blob:",blob); print("Expected      :",R3_GIT_BLOB)
    if branch!=BRANCH: raise R1Error(f"branch:{branch}:{BRANCH}")
    if par!=PARENT: raise R1Error(f"parent:{par}:{PARENT}")
    if not clean: raise R1Error("repository_not_clean")
    if blob!=R3_GIT_BLOB: raise R1Error(f"R3_blob:{blob}:{R3_GIT_BLOB}")

def load_patched_module(root):
    src=patched_r1_source(root); compile(src,f"<{R1_TOKEN}_patched_R3>","exec")
    m=types.ModuleType("g4_b4_r3_r1_selector_repair")
    m.__file__=str(root/R3_RUNNER); m.__package__=None; sys.modules[m.__name__]=m
    exec(compile(src,m.__file__,"exec"),m.__dict__); return m

def self_test(root):
    repository_preflight(root)
    r3=import_exact(root,R3_RUNNER,R3_GIT_BLOB,"g4b4r3r1_failure_reproduction")
    reproduced=False
    try:
        r3.patched_r3_source(root)
    except Exception as exc:
        reproduced="patch_end_candidate_profile_pipeline_not_unique" in str(exc)
        if not reproduced: raise R1Error(f"unexpected_R3_failure:{repr(exc)}")
    if not reproduced: raise R1Error("frozen_R3_failure_not_reproduced")

    repaired=patched_r1_source(root)
    if CANDIDATE_END_PAIR in repaired: raise R1Error("duplicate_candidate_end_anchor_survived_repair")
    if repaired.count(CANDIDATE_END)!=1: raise R1Error(f"candidate_end_anchor_postrepair_count:{repaired.count(CANDIDATE_END)}")
    for marker in [
        'def infer_staged_batch256(cond_arr):',
        'def screen_and_project_once(y,p,state,tau_nodes):',
        'gate("R3_parent_raw_prediction_array_exact"',
        'gate("R3_child_raw_prediction_array_exact"',
        'gate("R3_capillary_saturation_array_exact"',
        '"new_numerical_equivalence_tolerance_defined":False',
        '"B4_R4_fixed_shape_graph_exact_output_probe_authorized":True',
        '"R3_R1_duplicate_end_anchor_selector_repair_only":True',
    ]:
        if marker not in repaired: raise R1Error(f"missing_R3_R1_marker:{marker}")
    compile(repaired,f"<{R1_TOKEN}_structural_selftest>","exec")
    m=load_patched_module(root)
    if m.OUT_TOKEN!=R1_TOKEN: raise R1Error(f"patched_OUT_TOKEN:{m.OUT_TOKEN}")
    if m.PASS!=R1_STATUS: raise R1Error(f"patched_PASS:{m.PASS}")
    print("POSTV16 GPU-HYB-G4-B4-R3-R1 structural/patch self-test: PASS")

def main(root,drive):
    root=root.resolve(); drive=drive.resolve(); repository_preflight(root)
    return int(load_patched_module(root).main(root,drive))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    try:
        if args.self_test: self_test(args.project_root.resolve()); raise SystemExit(0)
        raise SystemExit(main(args.project_root,args.drive_root))
    except Exception as exc:
        print(MILESTONE,"WRAPPER BLOCK"); print("Exception:",repr(exc)); raise
