#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import types
from pathlib import Path

MILESTONE="POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R3-R1-R1"
BRANCH="postv16-av4-pivot"
PARENT="0c5438dbaf0da4a8e7c051d66143c86a90a6c6bc"

R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_R1_Duplicate_End_Anchor_Selector_Repair.py"
R1_GIT_BLOB="4772695835d9d84c61bc02f89d8ea79c2d27dcd7"

R1R1_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_R1_R1"
R1R1_STATUS="POSTV16AV4PIVOTGPUHYBG4B4R3R1R1_PATCH_BOUNDARY_CONSUMPTION_REPAIR_PASS"
R1R1_BLOCK="POSTV16AV4PIVOTGPUHYBG4B4R3R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"
R1R1_CLASSIFICATION=(
    "G4_B4_R3_EXACT_OUTPUT_PRESERVING_BATCH256_DESIGN_UNCHANGED_"
    "ALL_REPLACEMENT_END_BOUNDARIES_CONSUMED_CORRECTLY"
)

R1_STATUS="POSTV16AV4PIVOTGPUHYBG4B4R3R1_DUPLICATE_END_ANCHOR_SELECTOR_REPAIR_PASS"

SHADOW_STAGE='        stage="shadow_B2_scalar_projection_correction_after_candidate"'
FOOTER_END='        print("="*202)\n        return 0'


class R1R1Error(RuntimeError):
    pass


def git(root: Path,*args: str) -> str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()


def replace_once(source: str,old: str,new: str,label: str) -> str:
    n=source.count(old)
    if n!=1:
        raise R1R1Error(f"patch_anchor_{label}_count:{n}")
    return source.replace(old,new,1)


def import_exact(root: Path,filename: str,expected_blob: str,module_name: str):
    p=root/filename
    if not p.is_file():
        raise R1R1Error(f"missing_source:{filename}")
    actual=git(root,"hash-object",str(p))
    if actual!=expected_blob:
        raise R1R1Error(f"source_blob:{filename}:{actual}:{expected_blob}")
    spec=importlib.util.spec_from_file_location(module_name,p)
    if spec is None or spec.loader is None:
        raise R1R1Error(f"import_spec:{filename}")
    module=importlib.util.module_from_spec(spec)
    sys.modules[module_name]=module
    spec.loader.exec_module(module)
    return module


def patched_r1r1_source(root: Path) -> str:
    r1=import_exact(root,R1_RUNNER,R1_GIT_BLOB,"g4b4r3r1r1_r1_authority")
    original_import_exact=r1.import_exact

    def intercepted_import_exact(root_arg,filename,expected_blob,module_name):
        module=original_import_exact(root_arg,filename,expected_blob,module_name)

        if filename==r1.R3_RUNNER:
            original_replace_between=module.replace_between

            def boundary_consuming_replace_between(source,start,end,replacement,label):
                # R3-R1 itself handles candidate_profile_pipeline. The remaining
                # R3 replacement blocks below include their own end anchors, so
                # retaining the original end anchor would duplicate executable
                # source. Consume the inherited end anchor exactly once.
                if label in {"exact_output_shadow","footer"}:
                    start_count=source.count(start)
                    if start_count!=1:
                        raise R1R1Error(f"{label}_start_count:{start_count}")
                    i=source.find(start)
                    j=source.find(end,i+len(start))
                    if j<0:
                        raise R1R1Error(f"{label}_end_missing")
                    if source.find(end,j+1)>=0:
                        raise R1R1Error(f"{label}_end_not_unique")
                    return source[:i]+replacement+source[j+len(end):]

                return original_replace_between(source,start,end,replacement,label)

            module.replace_between=boundary_consuming_replace_between

        return module

    r1.import_exact=intercepted_import_exact
    s=r1.patched_r1_source(root)

    replacements=[
        ('M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R3-R1"',f'M="{MILESTONE}"',"milestone"),
        (f'PASS="{R1_STATUS}"',f'PASS="{R1R1_STATUS}"',"pass"),
        ('BLOCK="POSTV16AV4PIVOTGPUHYBG4B4R3R1_TECHNICAL_OR_AUTHORITY_BLOCK"',f'BLOCK="{R1R1_BLOCK}"',"block"),
        ('PARENT="dc32145844dd0cf7ac4500dad532e3d88466e57c"',f'PARENT="{PARENT}"',"parent"),
        ('OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_R1"',f'OUT_TOKEN="{R1R1_TOKEN}"',"token"),
        ('print("POSTV16 GPU-HYB-G4-B4-R3-R1 structural/patch self-test: PASS")',
         'print("POSTV16 GPU-HYB-G4-B4-R3-R1-R1 structural/patch self-test: PASS")',"selftest"),
        ('gate("parent_is_G4_B4_R3_failed_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',
         'gate("parent_is_G4_B4_R3_R1_failed_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',"parentgate"),
    ]
    for old,new,label in replacements:
        s=replace_once(s,old,new,label)

    old_banner=(
        'print("G4-B4-R3-R1 — DUPLICATE END-ANCHOR SELECTOR REPAIR / EXACT-OUTPUT BATCH256 OPTIMIZATION")\n'
        '        print("REPAIRS ONLY R3 PATCH ASSEMBLY. THE BATCH-256 NUMERICAL AUTHORITY, CACHED-XI CANDIDATE, SINGLE SCREEN/PROJECTION PATH, MASS PIPELINE, MAPBACK, AND CAPILLARY DESIGN ARE UNCHANGED.")\n'
        '        print("FAILED R3 COMMIT dc32145844dd0cf7ac4500dad532e3d88466e57c REMAINS IMMUTABLE.")'
    )
    new_banner=(
        'print("G4-B4-R3-R1-R1 — PATCH-BOUNDARY CONSUMPTION REPAIR / EXACT-OUTPUT BATCH256 OPTIMIZATION")\n'
        '        print("REPAIRS ONLY GENERATED-SOURCE BOUNDARY CONSUMPTION FOR THE R3 SHADOW AND FOOTER BLOCKS. SCIENTIFIC AND NUMERICAL DESIGN IS UNCHANGED.")\n'
        '        print("FAILED R3 AND R3-R1 COMMITS REMAIN IMMUTABLE; NO GPU/PHYSICS EXECUTION OCCURRED IN EITHER STRUCTURAL FAILURE.")'
    )
    s=replace_once(s,old_banner,new_banner,"banner")

    old_class='            "classification":"G4_B4_R3_EXACT_OUTPUT_PRESERVING_BATCH256_DESIGN_UNCHANGED_DUPLICATE_END_ANCHOR_SELECTOR_REPAIRED",'
    new_class=(
        f'            "classification":"{R1R1_CLASSIFICATION}",\n'
        '            "R3_failed_commit_bound":True,\n'
        '            "R3_R1_failed_commit_bound":True,\n'
        '            "R3_R1_R1_patch_boundary_consumption_repair_only":True,'
    )
    s=replace_once(s,old_class,new_class,"classification")

    return s


def repository_preflight(root: Path) -> None:
    branch=git(root,"branch","--show-current")
    head=git(root,"rev-parse","HEAD")
    parent=git(root,"rev-parse","HEAD^")
    clean=git(root,"status","--porcelain")==""
    p=root/R1_RUNNER
    blob=git(root,"hash-object",str(p)) if p.is_file() else "MISSING"

    print("--- G4-B4-R3-R1-R1 REPOSITORY IDENTITY ---")
    print("Branch:",branch)
    print("HEAD  :",head)
    print("HEAD^ :",parent)
    print("Clean :",clean)
    print("R3-R1 runner blob:",blob)
    print("Expected         :",R1_GIT_BLOB)

    if branch!=BRANCH:
        raise R1R1Error(f"branch:{branch}:{BRANCH}")
    if parent!=PARENT:
        raise R1R1Error(f"parent:{parent}:{PARENT}")
    if not clean:
        raise R1R1Error("repository_not_clean")
    if blob!=R1_GIT_BLOB:
        raise R1R1Error(f"R3R1_blob:{blob}:{R1_GIT_BLOB}")


def load_patched_module(root: Path) -> types.ModuleType:
    source=patched_r1r1_source(root)
    compile(source,f"<{R1R1_TOKEN}_patched_R3_R1>","exec")
    module=types.ModuleType("g4_b4_r3_r1_r1_boundary_repair")
    module.__file__=str(root/R1_RUNNER)
    module.__package__=None
    sys.modules[module.__name__]=module
    exec(compile(source,module.__file__,"exec"),module.__dict__)
    return module


def self_test(root: Path) -> None:
    repository_preflight(root)

    # Reproduce the immutable R3-R1 structural failure exactly: its generated
    # source contains the shadow-stage end anchor twice on one executable line.
    r1=import_exact(root,R1_RUNNER,R1_GIT_BLOB,"g4b4r3r1r1_failure_reproduction")
    bad_source=r1.patched_r1_source(root)
    reproduced=False
    try:
        compile(bad_source,"<frozen_R3_R1_failure>","exec")
    except SyntaxError as exc:
        line=(exc.text or "")
        reproduced=(line.count('stage="shadow_B2_scalar_projection_correction_after_candidate"')>=2)
        if not reproduced:
            raise R1R1Error(f"unexpected_R3_R1_syntax_failure:{repr(exc)}")
    if not reproduced:
        raise R1R1Error("frozen_R3_R1_failure_not_reproduced")

    repaired=patched_r1r1_source(root)

    duplicate_shadow=SHADOW_STAGE+SHADOW_STAGE
    duplicate_shadow_spaced=SHADOW_STAGE+(" "*8)+SHADOW_STAGE
    if duplicate_shadow in repaired or duplicate_shadow_spaced in repaired:
        raise R1R1Error("duplicate_shadow_stage_survived_repair")

    # The generated footer must occur exactly once in executable source.
    if repaired.count(FOOTER_END)!=1:
        raise R1R1Error(f"footer_end_postrepair_count:{repaired.count(FOOTER_END)}")

    required=[
        'def infer_staged_batch256(cond_arr):',
        'def screen_and_project_once(y,p,state,tau_nodes):',
        'gate("R3_parent_raw_prediction_array_exact"',
        'gate("R3_child_raw_prediction_array_exact"',
        'gate("R3_capillary_saturation_array_exact"',
        '"new_numerical_equivalence_tolerance_defined":False',
        '"B4_R4_fixed_shape_graph_exact_output_probe_authorized":True',
        '"R3_R1_R1_patch_boundary_consumption_repair_only":True',
    ]
    for marker in required:
        if marker not in repaired:
            raise R1R1Error(f"missing_R3_R1_R1_marker:{marker}")

    compile(repaired,f"<{R1R1_TOKEN}_structural_selftest>","exec")
    module=load_patched_module(root)
    if module.OUT_TOKEN!=R1R1_TOKEN:
        raise R1R1Error(f"patched_OUT_TOKEN:{module.OUT_TOKEN}")
    if module.PASS!=R1R1_STATUS:
        raise R1R1Error(f"patched_PASS:{module.PASS}")

    print("POSTV16 GPU-HYB-G4-B4-R3-R1-R1 structural/patch self-test: PASS")


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
