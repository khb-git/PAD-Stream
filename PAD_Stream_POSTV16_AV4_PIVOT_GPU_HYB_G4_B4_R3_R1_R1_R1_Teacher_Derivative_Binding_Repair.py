#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import types
from pathlib import Path

MILESTONE="POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R3-R1-R1-R1"
BRANCH="postv16-av4-pivot"
PARENT="fd1e76c39ef238c5e34c409a48898125a65112ef"

PARENT_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_R1_R1_Patch_Boundary_Consumption_Repair.py"
PARENT_GIT_BLOB="ce1a6291bd1b183b1593e92e24480070f7c23898"

TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_R1_R1_R1"
PASS_STATUS="POSTV16AV4PIVOTGPUHYBG4B4R3R1R1R1_TEACHER_DERIVATIVE_BINDING_REPAIR_PASS"
BLOCK_STATUS="POSTV16AV4PIVOTGPUHYBG4B4R3R1R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"
CLASSIFICATION=(
    "G4_B4_R3_EXACT_OUTPUT_PRESERVING_BATCH256_DESIGN_UNCHANGED_"
    "TEACHER_DERIVATIVE_BINDING_REPAIRED"
)

PARENT_PASS="POSTV16AV4PIVOTGPUHYBG4B4R3R1R1_PATCH_BOUNDARY_CONSUMPTION_REPAIR_PASS"

BAD_DERIVATIVE='physics.dfw_dsw(yy,adapter.teacher_params(p))[1:-1]'
GOOD_DERIVATIVE='teacher.dfw_dsw(yy,adapter.teacher_params(p))[1:-1]'


class RepairError(RuntimeError):
    pass


def git(root: Path,*args: str) -> str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()


def replace_once(source: str,old: str,new: str,label: str) -> str:
    n=source.count(old)
    if n!=1:
        raise RepairError(f"patch_anchor_{label}_count:{n}")
    return source.replace(old,new,1)


def import_exact(root: Path,filename: str,expected_blob: str,module_name: str):
    p=root/filename
    if not p.is_file():
        raise RepairError(f"missing_source:{filename}")
    actual=git(root,"hash-object",str(p))
    if actual!=expected_blob:
        raise RepairError(f"source_blob:{filename}:{actual}:{expected_blob}")
    spec=importlib.util.spec_from_file_location(module_name,p)
    if spec is None or spec.loader is None:
        raise RepairError(f"import_spec:{filename}")
    module=importlib.util.module_from_spec(spec)
    sys.modules[module_name]=module
    spec.loader.exec_module(module)
    return module


def patched_source(root: Path) -> str:
    parent=import_exact(root,PARENT_RUNNER,PARENT_GIT_BLOB,"g4b4r3r1r1r1_parent_authority")
    s=parent.patched_r1r1_source(root)

    s=replace_once(s,BAD_DERIVATIVE,GOOD_DERIVATIVE,"teacher_derivative_owner")

    replacements=[
        ('M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R3-R1-R1"',f'M="{MILESTONE}"',"milestone"),
        (f'PASS="{PARENT_PASS}"',f'PASS="{PASS_STATUS}"',"pass"),
        ('BLOCK="POSTV16AV4PIVOTGPUHYBG4B4R3R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"',f'BLOCK="{BLOCK_STATUS}"',"block"),
        ('PARENT="0c5438dbaf0da4a8e7c051d66143c86a90a6c6bc"',f'PARENT="{PARENT}"',"parent"),
        ('OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_R1_R1"',f'OUT_TOKEN="{TOKEN}"',"token"),
        ('print("POSTV16 GPU-HYB-G4-B4-R3-R1-R1 structural/patch self-test: PASS")',
         'print("POSTV16 GPU-HYB-G4-B4-R3-R1-R1-R1 structural/patch self-test: PASS")',"selftest"),
        ('gate("parent_is_G4_B4_R3_R1_failed_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',
         'gate("parent_is_G4_B4_R3_R1_R1_runtime_block_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',"parentgate"),
    ]
    for old,new,label in replacements:
        s=replace_once(s,old,new,label)

    old_banner=(
        'print("G4-B4-R3-R1-R1 — PATCH-BOUNDARY CONSUMPTION REPAIR / EXACT-OUTPUT BATCH256 OPTIMIZATION")\n'
        '        print("REPAIRS ONLY GENERATED-SOURCE BOUNDARY CONSUMPTION FOR THE R3 SHADOW AND FOOTER BLOCKS. SCIENTIFIC AND NUMERICAL DESIGN IS UNCHANGED.")\n'
        '        print("FAILED R3 AND R3-R1 COMMITS REMAIN IMMUTABLE; NO GPU/PHYSICS EXECUTION OCCURRED IN EITHER STRUCTURAL FAILURE.")'
    )
    new_banner=(
        'print("G4-B4-R3-R1-R1-R1 — TEACHER DERIVATIVE BINDING REPAIR / EXACT-OUTPUT BATCH256 OPTIMIZATION")\n'
        '        print("REPAIRS ONLY THE R3 OPTIMIZED SCREEN HELPER MODULE OWNER FOR dfw_dsw: RESERVOIR PHYSICS -> FROZEN R2/TEACHER AUTHORITY.")\n'
        '        print("SCREEN FORMULA, THRESHOLDS, 256+REMAINDER GPU BATCH SHAPES, ROUTING, CONSERVATIVE MASS PIPELINE, MAPBACK, CAPILLARY, AND EXACT-OUTPUT GATES ARE UNCHANGED.")'
    )
    s=replace_once(s,old_banner,new_banner,"banner")

    authority_anchor='        stage="artifact_authority"\n'
    authority_insert='''        stage="artifact_authority"
        r3r1r1_block_path=drive/BASE/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_R1_R1_BLOCKED")/"POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R3_R1_R1_Blocked_Report.json"
        gate("R3_R1_R1_block_present",r3r1r1_block_path.is_file(),str(r3r1r1_block_path))
        r3r1r1block=js(r3r1r1_block_path)
        gate("R3_R1_R1_block_status_exact",
             r3r1r1block.get("status")=="POSTV16AV4PIVOTGPUHYBG4B4R3R1R1_TECHNICAL_OR_AUTHORITY_BLOCK",
             r3r1r1block.get("status"))
        gate("R3_R1_R1_block_stage_Hybrid_authority",
             r3r1r1block.get("failed_stage")=="Hybrid_authority",
             r3r1r1block.get("failed_stage"))
        gate("R3_R1_R1_block_exception_teacher_derivative_binding",
             "g4b1_r2_physics" in str(r3r1r1block.get("exception",""))
             and "dfw_dsw" in str(r3r1r1block.get("exception","")),
             r3r1r1block.get("exception"))

'''
    s=replace_once(s,authority_anchor,authority_insert,"predecessor_block_authority")

    old_class='            "classification":"G4_B4_R3_EXACT_OUTPUT_PRESERVING_BATCH256_DESIGN_UNCHANGED_ALL_REPLACEMENT_END_BOUNDARIES_CONSUMED_CORRECTLY",'
    new_class=(
        f'            "classification":"{CLASSIFICATION}",\n'
        '            "R3_R1_R1_runtime_block_bound":True,\n'
        '            "R3_R1_R1_R1_teacher_derivative_binding_repair_only":True,\n'
        '            "screen_derivative_authority":"frozen_R2_teacher_module",'
    )
    s=replace_once(s,old_class,new_class,"classification")

    return s


def repository_preflight(root: Path) -> None:
    branch=git(root,"branch","--show-current")
    head=git(root,"rev-parse","HEAD")
    parent=git(root,"rev-parse","HEAD^")
    clean=git(root,"status","--porcelain")==""
    p=root/PARENT_RUNNER
    blob=git(root,"hash-object",str(p)) if p.is_file() else "MISSING"

    print("--- G4-B4-R3-R1-R1-R1 REPOSITORY IDENTITY ---")
    print("Branch:",branch)
    print("HEAD  :",head)
    print("HEAD^ :",parent)
    print("Clean :",clean)
    print("R3-R1-R1 runner blob:",blob)
    print("Expected            :",PARENT_GIT_BLOB)

    if branch!=BRANCH:
        raise RepairError(f"branch:{branch}:{BRANCH}")
    if parent!=PARENT:
        raise RepairError(f"parent:{parent}:{PARENT}")
    if not clean:
        raise RepairError("repository_not_clean")
    if blob!=PARENT_GIT_BLOB:
        raise RepairError(f"parent_blob:{blob}:{PARENT_GIT_BLOB}")


def load_patched_module(root: Path) -> types.ModuleType:
    source=patched_source(root)
    compile(source,f"<{TOKEN}_patched_parent>","exec")
    module=types.ModuleType("g4_b4_r3_r1_r1_r1_teacher_binding")
    module.__file__=str(root/PARENT_RUNNER)
    module.__package__=None
    sys.modules[module.__name__]=module
    exec(compile(source,module.__file__,"exec"),module.__dict__)
    return module


def self_test(root: Path) -> None:
    repository_preflight(root)
    parent=import_exact(root,PARENT_RUNNER,PARENT_GIT_BLOB,"g4b4r3r1r1r1_parent_selftest")
    raw=parent.patched_r1r1_source(root)

    if raw.count(BAD_DERIVATIVE)!=1:
        raise RepairError(f"frozen_bad_derivative_count:{raw.count(BAD_DERIVATIVE)}")

    repaired=patched_source(root)

    if BAD_DERIVATIVE in repaired:
        raise RepairError("bad_physics_derivative_binding_survived")
    if repaired.count(GOOD_DERIVATIVE)!=1:
        raise RepairError(f"teacher_derivative_binding_count:{repaired.count(GOOD_DERIVATIVE)}")

    required=[
        'gate("R3_parent_raw_prediction_array_exact"',
        'gate("R3_child_raw_prediction_array_exact"',
        'gate("R3_parent_projected_profile_array_exact"',
        'gate("R3_child_projected_profile_array_exact"',
        'gate("R3_corrected_cv_mass_array_exact"',
        'gate("R3_grid_mapback_saturation_array_exact"',
        'gate("R3_capillary_saturation_array_exact"',
        '"new_numerical_equivalence_tolerance_defined":False',
        '"R3_R1_R1_R1_teacher_derivative_binding_repair_only":True',
        '"screen_derivative_authority":"frozen_R2_teacher_module"',
    ]
    for marker in required:
        if marker not in repaired:
            raise RepairError(f"missing_required_marker:{marker}")

    compile(repaired,f"<{TOKEN}_structural_selftest>","exec")
    module=load_patched_module(root)

    if module.OUT_TOKEN!=TOKEN:
        raise RepairError(f"patched_OUT_TOKEN:{module.OUT_TOKEN}")
    if module.PASS!=PASS_STATUS:
        raise RepairError(f"patched_PASS:{module.PASS}")

    print("POSTV16 GPU-HYB-G4-B4-R3-R1-R1-R1 structural/patch self-test: PASS")


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
