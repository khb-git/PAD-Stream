#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import types
from pathlib import Path

MILESTONE = "POSTV16-AV4-PIVOT-GPU-HYB-G4-B4-R1"
BRANCH = "postv16-av4-pivot"
PARENT = "2b0c66584a11da496816b813d7c7ca9e47014f00"

B4_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_Single_Batch_GPU_Profile_Pipeline_Optimization.py"
B4_GIT_BLOB = "9aa36908ce766869efcc1038c7b08ff5a5839f59"

R1_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G4_B4_R1"
R1_STATUS = "POSTV16AV4PIVOTGPUHYBG4B4R1_FOOTER_PATCH_ASSEMBLY_REPAIR_PASS"
R1_BLOCK = "POSTV16AV4PIVOTGPUHYBG4B4R1_TECHNICAL_OR_AUTHORITY_BLOCK"
R1_CLASSIFICATION = (
    "G4_B4_SINGLE_BATCH_GPU_PROFILE_PIPELINE_PRESERVED_"
    "FOOTER_PATCH_ASSEMBLY_SYNTAX_REPAIRED"
)

B4_STATUS = "POSTV16AV4PIVOTGPUHYBG4B4_SINGLE_BATCH_GPU_PROFILE_PIPELINE_OPTIMIZATION_PASS"

BAD_FOOTER = '        print("="*202)\n        return 0        print("="*202)\n        return 0'
GOOD_FOOTER = '        print("="*202)\n        return 0'


class R1Error(RuntimeError):
    pass


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def replace_once(source: str, old: str, new: str, label: str) -> str:
    n = source.count(old)
    if n != 1:
        raise R1Error(f"patch_anchor_{label}_count:{n}")
    return source.replace(old, new, 1)


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
    b4 = import_exact(root, B4_RUNNER, B4_GIT_BLOB, "g4b4r1_b4_authority")
    s = b4.patched_b4_source(root)

    s = replace_once(s, BAD_FOOTER, GOOD_FOOTER, "malformed_footer_join")

    replacements = [
        ('M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B4"', f'M="{MILESTONE}"', 'milestone'),
        (f'PASS="{B4_STATUS}"', f'PASS="{R1_STATUS}"', 'pass_status'),
        ('BLOCK="POSTV16AV4PIVOTGPUHYBG4B4_TECHNICAL_OR_AUTHORITY_BLOCK"', f'BLOCK="{R1_BLOCK}"', 'block_status'),
        ('PARENT="c94e5e6c6f3f6c2e433da23cec93ea72d89f092b"', f'PARENT="{PARENT}"', 'parent'),
        ('OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B4"', f'OUT_TOKEN="{R1_TOKEN}"', 'output_token'),
        ('print("POSTV16 GPU-HYB-G4-B4 structural/patch self-test: PASS")',
         'print("POSTV16 GPU-HYB-G4-B4-R1 structural/patch self-test: PASS")',
         'selftest_label'),
        ('gate("parent_is_G4_B3_R1_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',
         'gate("parent_is_G4_B4_failed_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))',
         'parent_gate'),
    ]
    for old, new, label in replacements:
        s = replace_once(s, old, new, label)

    old_banner = (
        'print("G4-B4 — SINGLE-BATCH GPU HYBRID PROFILE PIPELINE OPTIMIZATION")\n'
        '        print("READ-ONLY PERFORMANCE OPTIMIZATION. FROZEN HYBRID10 WEIGHTS, E8R1 SCREEN, ROUTING, MASS BUDGETS, E37A FALLBACK, MAPBACK, AND CAPILLARY PHYSICS ARE UNCHANGED.")\n'
        '        print("CANDIDATE USES THE FROZEN E9-R1 INFERENCE HELPER WITH ONE GPU BATCH; ORIGINAL BATCH-256 PROFILE EXECUTION IS SHADOW VALIDATION ONLY.")'
    )
    new_banner = (
        'print("G4-B4-R1 — FOOTER PATCH-ASSEMBLY REPAIR / SINGLE-BATCH GPU PROFILE PIPELINE")\n'
        '        print("REPAIRS ONLY THE B4 GENERATED-SOURCE FOOTER JOIN. THE B4 SINGLE-BATCH GPU CANDIDATE, SHADOW BATCH-256 VALIDATION, ROUTING, MASS PIPELINE, MAPBACK, AND CAPILLARY PHYSICS ARE UNCHANGED.")\n'
        '        print("FAILED B4 COMMIT 2b0c66584a11da496816b813d7c7ca9e47014f00 REMAINS IMMUTABLE.")'
    )
    s = replace_once(s, old_banner, new_banner, "banner")

    summary_anchor = '            "classification":"FROZEN_HYBRID10_SINGLE_BATCH_GPU_PROFILE_PIPELINE_EXECUTION_BASELINE_BATCH256_SCREEN_AND_PROFILE_EQUIVALENCE_CERTIFIED",'
    summary_replacement = (
        f'            "classification":"{R1_CLASSIFICATION}",\n'
        '            "B4_failed_commit_bound":True,\n'
        '            "B4_R1_footer_patch_assembly_repair_only":True,'
    )
    s = replace_once(s, summary_anchor, summary_replacement, "summary_classification")

    return s


def repository_preflight(root: Path) -> None:
    branch = git(root, "branch", "--show-current")
    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    clean = git(root, "status", "--porcelain") == ""
    b4 = root / B4_RUNNER
    b4_blob = git(root, "hash-object", str(b4)) if b4.is_file() else "MISSING"

    print("--- G4-B4-R1 REPOSITORY IDENTITY ---")
    print("Branch:", branch)
    print("HEAD  :", head)
    print("HEAD^ :", parent)
    print("Clean :", clean)
    print("B4 runner blob:", b4_blob)
    print("Expected      :", B4_GIT_BLOB)

    if branch != BRANCH:
        raise R1Error(f"branch:{branch}:{BRANCH}")
    if parent != PARENT:
        raise R1Error(f"parent:{parent}:{PARENT}")
    if not clean:
        raise R1Error("repository_not_clean")
    if b4_blob != B4_GIT_BLOB:
        raise R1Error(f"B4_blob:{b4_blob}:{B4_GIT_BLOB}")


def load_patched_module(root: Path) -> types.ModuleType:
    patched = patched_r1_source(root)
    compile(patched, f"<{R1_TOKEN}_patched_B4>", "exec")
    module = types.ModuleType("g4_b4_r1_footer_repair")
    module.__file__ = str(root / B4_RUNNER)
    module.__package__ = None
    sys.modules[module.__name__] = module
    exec(compile(patched, module.__file__, "exec"), module.__dict__)
    return module


def self_test(root: Path) -> None:
    repository_preflight(root)
    b4 = import_exact(root, B4_RUNNER, B4_GIT_BLOB, "g4b4r1_b4_selftest")
    failed_source = b4.patched_b4_source(root)

    bad_count = failed_source.count(BAD_FOOTER)
    if bad_count != 1:
        raise R1Error(f"expected_exact_B4_malformed_footer_once:{bad_count}")

    repaired = patched_r1_source(root)
    if BAD_FOOTER in repaired:
        raise R1Error("malformed_footer_survived_repair")
    if repaired.count(GOOD_FOOTER) < 1:
        raise R1Error("repaired_footer_missing")

    compile(repaired, f"<{R1_TOKEN}_structural_selftest>", "exec")
    module = load_patched_module(root)

    required = ["main", "selftest", "OUT_TOKEN", "PASS", "BLOCK"]
    missing = [x for x in required if not hasattr(module, x)]
    if missing:
        raise R1Error(f"patched_module_missing:{missing}")
    if module.OUT_TOKEN != R1_TOKEN:
        raise R1Error(f"patched_OUT_TOKEN:{module.OUT_TOKEN}")
    if module.PASS != R1_STATUS:
        raise R1Error(f"patched_PASS:{module.PASS}")

    required_markers = [
        'stage="shadow_batch256_profile_equivalence"',
        'gate("B4_single_batch_gpu_call_count_one"',
        '"single_batch_GPU_profile_candidate_used":True',
        '"B4_R1_footer_patch_assembly_repair_only":True',
        '"B5_CPU_GPU_overlap_pipeline_probe_authorized":True',
    ]
    for marker in required_markers:
        if marker not in repaired:
            raise R1Error(f"missing_B4_R1_marker:{marker}")

    print("POSTV16 GPU-HYB-G4-B4-R1 structural/patch self-test: PASS")


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
