#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R2-R2"
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R2R2_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_COMMIT = "8eda324d7ce76503cbecc9363530247f4b56dff5"
PARENT_RUNNER = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_SG3_Blob_Authority_Repair_and_Coupled_Map_Boundary_Audit.py"
PARENT_RUNNER_BLOB = "477c94c5704ed99c954cfc41224381d5acf6fb22"

BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
R2_BLOCK_DIR = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2_BLOCKED"
R2_BLOCK_REPORT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2_Blocked_Report.json"
R2R1_BLOCK_DIR = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_BLOCKED"
R2R1_BLOCK_REPORT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Blocked_Report.json"

EXPECTED_R2_BLOCK_STATUS = "AV4F4R3R3R3R3R3O3R6R2_TECHNICAL_OR_AUTHORITY_BLOCK"
EXPECTED_R2R1_BLOCK_STATUS = "AV4F4R3R3R3R3R3O3R6R2R1_TECHNICAL_OR_AUTHORITY_BLOCK"
CORRECT_SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"

class RepairError(RuntimeError):
    pass

def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, text=True, capture_output=True
    ).stdout.strip()

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def transform_parent_source(source: str) -> str:
    # Exact deterministic namespace/authority repair only.
    old_parent = 'PARENT="34b9ec244747f2fe0844830a27bfc3c3ef3c6021"'
    new_parent = 'PARENT="8eda324d7ce76503cbecc9363530247f4b56dff5"'
    if source.count(old_parent) != 1:
        raise RepairError(f"parent replacement cardinality={source.count(old_parent)}")
    source = source.replace(old_parent, new_parent)

    # Move the successor execution/output namespace from R2-R1 to R2-R2.
    old_ns = "O3R6R2R1"
    if source.count(old_ns) < 10:
        raise RepairError(f"unexpected R2-R1 namespace cardinality={source.count(old_ns)}")
    source = source.replace(old_ns, "O3R6R2R2")

    old_mid = "O3-R6-R2-R1"
    if old_mid not in source:
        raise RepairError("milestone namespace replacement target missing")
    source = source.replace(old_mid, "O3-R6-R2-R2")

    # Repair the provenance filename: bind the immutable ORIGINAL R2 block report,
    # not a successor report name.
    wrong_after_namespace = (
        'R2_BLOCK_REPORT="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_Blocked_Report.json"'
    )
    correct = (
        'R2_BLOCK_REPORT="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2_Blocked_Report.json"'
    )
    if source.count(wrong_after_namespace) != 1:
        raise RepairError(
            f"R2 block-report filename replacement cardinality={source.count(wrong_after_namespace)}"
        )
    source = source.replace(wrong_after_namespace, correct)

    # Gate label should identify the actual parent commit after repair.
    source = source.replace('"parent_is_R1R1"', '"parent_is_R2R1"')

    # Harden structural self-test against this exact regression.
    old_self = (
        'assert DEN==1024 and COARSE_STEP==64 and FINAL_WIDTH==1 and '
        'MILESTONE.endswith("O3-R6-R2-R2") and len(SG3_BLOB)==40'
    )
    new_self = (
        'assert DEN==1024 and COARSE_STEP==64 and FINAL_WIDTH==1 and '
        'MILESTONE.endswith("O3-R6-R2-R2") and len(SG3_BLOB)==40 and '
        'R2_BLOCK_REPORT=="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2_Blocked_Report.json"'
    )
    if source.count(old_self) != 1:
        raise RepairError(f"self-test replacement cardinality={source.count(old_self)}")
    source = source.replace(old_self, new_self)

    return source

def bind_parent_and_blocks(project_root: Path, drive_root: Path) -> str:
    root = project_root.resolve()
    drive = drive_root.resolve()

    parent = git_text(root, "rev-parse", "HEAD^")
    if parent != PARENT_COMMIT:
        raise RepairError(f"repository_parent_mismatch:{parent}")
    dirty = git_text(root, "status", "--porcelain")
    if dirty != "":
        raise RepairError(f"repository_not_clean:{dirty!r}")

    parent_path = root / PARENT_RUNNER
    if not parent_path.is_file():
        raise RepairError("parent_runner_missing")
    actual_blob = git_text(root, "hash-object", str(parent_path))
    if actual_blob != PARENT_RUNNER_BLOB:
        raise RepairError(f"parent_runner_blob_mismatch:{actual_blob}")

    r2 = drive / R2_BLOCK_DIR / R2_BLOCK_REPORT
    if not r2.is_file():
        raise RepairError(f"original_R2_block_report_missing:{r2}")
    r2j = load_json(r2)
    sg3gate = (
        r2j.get("gates", {})
        .get("PAD_Stream_V15SG3_FiveSpot_Pressure_Solve_blob", {})
    )
    if not (
        r2j.get("status") == EXPECTED_R2_BLOCK_STATUS
        and r2j.get("failed_stage") == "authority"
        and int(r2j.get("new_point_checkpoint_count", -1)) == 0
        and int(r2j.get("reused_point_checkpoint_count", -1)) == 0
        and sg3gate.get("status") == "FAIL"
        and sg3gate.get("detail") == CORRECT_SG3_BLOB
    ):
        raise RepairError("original_R2_block_semantics_mismatch")

    r2r1 = drive / R2R1_BLOCK_DIR / R2R1_BLOCK_REPORT
    if not r2r1.is_file():
        raise RepairError(f"R2R1_block_report_missing:{r2r1}")
    r2r1j = load_json(r2r1)
    if not (
        r2r1j.get("status") == EXPECTED_R2R1_BLOCK_STATUS
        and r2r1j.get("failed_stage") == "original_R2_block_binding"
        and int(r2r1j.get("new_point_checkpoint_count", -1)) == 0
        and int(r2r1j.get("reused_point_checkpoint_count", -1)) == 0
        and "original_R2_block_report_present" in str(r2r1j.get("exception"))
    ):
        raise RepairError("R2R1_block_semantics_mismatch")

    return parent_path.read_text(encoding="utf-8")

def build_transformed_module(project_root: Path, drive_root: Path):
    source = bind_parent_and_blocks(project_root, drive_root)
    transformed = transform_parent_source(source)
    compile(transformed, "<O3R6R2R2_transformed_parent>", "exec")
    mod = types.ModuleType("postv16_o3r6r2r2_transformed_parent")
    mod.__file__ = str(project_root / PARENT_RUNNER)
    sys.modules[mod.__name__] = mod
    exec(compile(transformed, mod.__file__, "exec"), mod.__dict__)
    return mod, transformed

def self_test(project_root: Path | None = None):
    assert len(PARENT_COMMIT) == 40
    assert len(PARENT_RUNNER_BLOB) == 40
    assert R2_BLOCK_REPORT.endswith("O3R6R2_Blocked_Report.json")
    assert R2R1_BLOCK_REPORT.endswith("O3R6R2R1_Blocked_Report.json")
    if project_root is not None:
        parent_path = project_root.resolve() / PARENT_RUNNER
        if parent_path.is_file():
            src = parent_path.read_text(encoding="utf-8")
            transformed = transform_parent_source(src)
            assert "O3R6R2R2" in transformed
            assert 'R2_BLOCK_REPORT="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2_Blocked_Report.json"' in transformed
            compile(transformed, "<self_test_transformed>", "exec")
    print("POSTV16 O3-R6-R2-R2 block-report filename authority-repair structural self-test: PASS")

def main(project_root: Path, drive_root: Path) -> int:
    try:
        mod, transformed = build_transformed_module(project_root, drive_root)
        print("=" * 180)
        print(MILESTONE + " -- DETERMINISTIC R2-R1 AUTHORITY/NAMESPACE REPAIR")
        print("=" * 180)
        print("[PASS] parent R2-R1 runner blob exact --", PARENT_RUNNER_BLOB)
        print("[PASS] immutable R2 SG3-authority block bound")
        print("[PASS] immutable R2-R1 report-filename block bound")
        print("[PASS] corrected original R2 block-report filename --", R2_BLOCK_REPORT)
        print("[PASS] transformed boundary source compiled")
        print("SCIENTIFIC BOUNDARY ALGORITHM / LP / OMEGA GRID / TOLERANCES: UNCHANGED")
        print("=" * 180)
        return int(mod.main(project_root, drive_root))
    except Exception as exc:
        drive = Path(drive_root).resolve()
        blocked = drive / BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_BLOCKED"
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCK,
            "failed_stage": "R2R2_repair_wrapper",
            "exception": repr(exc),
            "scientific_boundary_scan_executed": False,
            "damping_executed": False,
            "coupled_continuation_executed": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "O3R6R3_execution_authorized": False,
            "O3R7_authorized": False,
        }
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(MILESTONE + ": TECHNICAL / AUTHORITY BLOCK")
        print("Exception:", repr(exc))
        return 2

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test(args.project_root)
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
