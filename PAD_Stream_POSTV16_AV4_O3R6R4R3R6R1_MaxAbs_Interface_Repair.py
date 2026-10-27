#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import types
from pathlib import Path

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3-R6-R1"
PARENT_R3R6_COMMIT = "0e8c7bb5fefd60c5d83937491fecc0da23122724"
ORIGINAL_R3R6_BLOB = "5f70c6dcb6627eccd7ab3c0f5c75169fe1ebe168"

ORIGINAL_RUNNER = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_"
    "Controlled_Full_Generalized_ActiveSet_BoxConstrained_Projected_SameTime_Coupled_FixedPoint_Execution.py"
)

ORIGINAL_BAD_EXPR = (
    'o3r6.max_abs(r4_map1["event_grid_mass_kg"],'
    'r4_acc0["previous_physical_map_mass_kg"])'
)
REPAIRED_EXPR = (
    'o3r6.max_abs(r4_map1["event_grid_mass_kg"]'
    '-r4_acc0["previous_physical_map_mass_kg"])'
)

STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R4R3R6R1_MAX_ABS_INTERFACE_REPAIR_FULL_GENERALIZED_"
    "EXECUTION_PASS_ORIGINAL_UNDAMPED_FIXED_POINT_AND_FINAL_CLOSURE_CERTIFIED_"
    "NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_FAIL = (
    "AV4F4R3R3R3R3R3O3R6R4R3R6R1_MAX_ABS_INTERFACE_REPAIR_FULL_GENERALIZED_"
    "EXECUTION_SCIENTIFIC_FAIL_NO_AUTOMATIC_RERUN_NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R4R3R6R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BASE = Path("post_v16") / "PAD_STREAM_V16_RC1_B92D52088D01078A" / "POSTV16_AV4_Dynamic_Flow_Coupling"

ORIGINAL_BLOCK_DIR = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_BLOCKED"
ORIGINAL_BLOCK_REPORT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6_Blocked_Report.json"
ORIGINAL_BLOCK_STATUS = "AV4F4R3R3R3R3R3O3R6R4R3R6_TECHNICAL_OR_AUTHORITY_BLOCK"

OUT_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_"
    "MaxAbs_Interface_Repair_Full_Generalized_Execution"
)
RECOVERY_REL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_Recovery_Checkpoints"
FAIL_REL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_SCIENTIFIC_FAIL"
BLOCK_REL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_BLOCKED"

FINAL_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_Summary.json"
FINAL_STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_Certified_Nonlinear_Fixed_Point_State.npz"
FINAL_NONLIN = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_Nonlinear_Telemetry.csv"
FINAL_ASSIGN = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_Assignment_Stage_Telemetry.csv"
FINAL_GLOBAL = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_Globalization_Telemetry.csv"
FINAL_CUTS = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_Active_Cut_Telemetry.csv"
FINAL_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_Decision_Contract.json"
FINAL_GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_Final_Gate_Matrix.csv"
FINAL_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_Artifact_Manifest.csv"


class RepairAuthorityError(RuntimeError):
    pass


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, text=True, capture_output=True
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def successor_stage_names(iteration: int, stage: int):
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_"
        f"Iteration_{iteration:03d}_Stage_{stage}"
    )
    return stem+"_Resume_State.npz", stem+"_Resume_Metadata.json", stem+"_HiGHS_Basis.bas", stem+"_Manifest.csv"


def successor_map_names(iteration: int):
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_"
        f"Iteration_{iteration:03d}_Physical_Map_Candidate"
    )
    return stem+".npz", stem+".json", stem+"_Manifest.csv"


def successor_accepted_names(iteration: int):
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_"
        f"Iteration_{iteration:03d}_Computational_Iterate_Accepted"
    )
    return stem+".npz", stem+".json", stem+"_Manifest.csv"


def successor_candidate_names(iteration: int, alpha_idx: int, round_idx: int):
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_"
        f"Iteration_{iteration:03d}_Alpha_{alpha_idx:04d}_of_1024_Round_{round_idx:02d}"
    )
    return stem+"_State.npz", stem+"_Result.json", stem+"_Manifest.csv"


def successor_probe_names(iteration: int, cell: int):
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_"
        f"Iteration_{iteration:03d}_Sensitivity_Cell_{cell:05d}"
    )
    return stem+"_State.npz", stem+"_Metadata.json", stem+"_Manifest.csv"


def verify_original_block(drive_root: Path) -> dict:
    p = drive_root / ORIGINAL_BLOCK_DIR / ORIGINAL_BLOCK_REPORT
    if not p.is_file():
        raise RepairAuthorityError(f"immutable_R3R6_block_report_missing:{p}")
    report = json.loads(p.read_text(encoding="utf-8"))
    required = {
        "status": ORIGINAL_BLOCK_STATUS,
        "failed_stage": "bootstrap_from_R4_and_R3R5",
        "exception": "TypeError('max_abs() takes 1 positional argument but 2 were given')",
        "current_iteration": 0,
        "assignment_executed": False,
        "generalized_iteration_executed": False,
        "support_domain_changed": False,
        "physical_time_advanced": False,
        "O3R7_authorized": False,
        "automatic_rerun_authorized": False,
    }
    for k, v in required.items():
        if report.get(k) != v:
            raise RepairAuthorityError(
                f"immutable_R3R6_block_report_field_mismatch:{k}:{report.get(k)!r}!={v!r}"
            )
    return report


def build_repaired_module(project_root: Path):
    original_path = project_root / ORIGINAL_RUNNER
    if not original_path.is_file():
        raise RepairAuthorityError(f"original_R3R6_runner_missing:{original_path}")

    actual_blob = git_blob(original_path, project_root)
    if actual_blob != ORIGINAL_R3R6_BLOB:
        raise RepairAuthorityError(
            f"original_R3R6_blob_mismatch:{actual_blob}!={ORIGINAL_R3R6_BLOB}"
        )

    source = original_path.read_text(encoding="utf-8")
    bad_count = source.count(ORIGINAL_BAD_EXPR)
    repaired_count = source.count(REPAIRED_EXPR)
    if bad_count != 1 or repaired_count != 0:
        raise RepairAuthorityError(
            f"repair_site_cardinality_invalid:bad_count={bad_count},repaired_count={repaired_count}"
        )

    repaired_source = source.replace(ORIGINAL_BAD_EXPR, REPAIRED_EXPR, 1)
    if repaired_source.count(ORIGINAL_BAD_EXPR) != 0:
        raise RepairAuthorityError("original_bad_expression_survived_repair")
    if repaired_source.count(REPAIRED_EXPR) != 1:
        raise RepairAuthorityError("repaired_expression_cardinality_invalid")

    mod = types.ModuleType("postv16_o3r6r4r3r6r1_repaired_runtime")
    mod.__file__ = str(original_path) + "::<R3R6R1_exact_one_expression_repair>"
    exec(compile(repaired_source, mod.__file__, "exec"), mod.__dict__)

    mod.MILESTONE = MILESTONE
    mod.STATUS_PASS = STATUS_PASS
    mod.STATUS_FAIL = STATUS_FAIL
    mod.STATUS_BLOCK = STATUS_BLOCK

    # Successor commit parent is the immutable blocked R3-R6 commit.
    mod.PARENT_R3R5_COMMIT = PARENT_R3R6_COMMIT

    mod.OUT_REL = OUT_REL
    mod.RECOVERY_REL = RECOVERY_REL
    mod.FAIL_REL = FAIL_REL
    mod.BLOCK_REL = BLOCK_REL

    mod.FINAL_SUMMARY = FINAL_SUMMARY
    mod.FINAL_STATE = FINAL_STATE
    mod.FINAL_NONLIN = FINAL_NONLIN
    mod.FINAL_ASSIGN = FINAL_ASSIGN
    mod.FINAL_GLOBAL = FINAL_GLOBAL
    mod.FINAL_CUTS = FINAL_CUTS
    mod.FINAL_DECISION = FINAL_DECISION
    mod.FINAL_GATES = FINAL_GATES
    mod.FINAL_MANIFEST = FINAL_MANIFEST

    mod.stage_names = successor_stage_names
    mod.map_names = successor_map_names
    mod.accepted_names = successor_accepted_names
    mod.candidate_names = successor_candidate_names
    mod.probe_names = successor_probe_names

    return mod, {
        "original_runner_blob": actual_blob,
        "repair_bad_expression_count_before": bad_count,
        "repair_bad_expression_count_after": repaired_source.count(ORIGINAL_BAD_EXPR),
        "repair_repaired_expression_count_after": repaired_source.count(REPAIRED_EXPR),
    }


def structural_self_test(project_root: Path | None = None):
    assert ORIGINAL_BAD_EXPR != REPAIRED_EXPR
    assert len(PARENT_R3R6_COMMIT) == 40
    assert len(ORIGINAL_R3R6_BLOB) == 40
    if project_root is not None and (project_root / ORIGINAL_RUNNER).is_file():
        mod, info = build_repaired_module(project_root)
        assert info["repair_bad_expression_count_before"] == 1
        assert info["repair_bad_expression_count_after"] == 0
        assert info["repair_repaired_expression_count_after"] == 1
        assert mod.MILESTONE == MILESTONE
        assert mod.OUT_REL == OUT_REL
        assert mod.RECOVERY_REL == RECOVERY_REL
    print("POSTV16 O3-R6-R4-R3-R6-R1 max_abs interface repair structural self-test: PASS")


def main(project_root: Path, drive_root: Path, verbose_solver: bool = False) -> int:
    project_root = Path(project_root).resolve()
    drive_root = Path(drive_root).resolve()

    print("="*214)
    print(MILESTONE+" -- MAX_ABS INTERFACE REPAIR / FULL GENERALIZED EXECUTION SUCCESSOR")
    print("="*214)
    print("SUCCESSOR TO IMMUTABLE R3-R6 TECHNICAL/AUTHORITY BLOCK.")
    print("EXACT REPAIR: ONE TWO-ARGUMENT max_abs CALL -> ONE-ARGUMENT max_abs OF ARRAY DIFFERENCE.")
    print("NO PHYSICS CHANGE. NO SUPPORT CHANGE. NO TOLERANCE CHANGE. NO TIME ADVANCE.")
    print()

    try:
        parent = git_text(project_root, "rev-parse", "HEAD^")
        dirty = git_text(project_root, "status", "--porcelain")
        if parent != PARENT_R3R6_COMMIT:
            raise RepairAuthorityError(
                f"repository_parent_is_not_immutable_R3R6_blocked_commit:{parent}"
            )
        if dirty != "":
            raise RepairAuthorityError(f"repository_not_clean:{dirty!r}")
        print("[PASS] repository parent is immutable blocked R3-R6 --", parent)
        print("[PASS] repository clean")

        verify_original_block(drive_root)
        print("[PASS] immutable R3-R6 BLOCK report exact")

        repaired, info = build_repaired_module(project_root)
        print("[PASS] original R3-R6 runner blob exact --", info["original_runner_blob"])
        print("[PASS] exact one-expression repair cardinality -- 1")
        print("[PASS] successor output/recovery namespaces isolated from blocked R3-R6")

        rc = repaired.main(project_root, drive_root, verbose_solver)
        print("Formal O3-R6-R4-R3-R6-R1 repaired successor returned:", rc)
        return int(rc)

    except Exception as exc:
        blocked = drive_root / BLOCK_REL
        blocked.mkdir(parents=True, exist_ok=True)
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R6R1_Preflight_Blocked_Report.json"
        if not p.exists():
            p.write_text(
                json.dumps(
                    {
                        "milestone": MILESTONE,
                        "status": STATUS_BLOCK,
                        "failed_stage": "R3R6R1_successor_preflight_or_repair",
                        "exception": repr(exc),
                        "original_R3R6_commit": PARENT_R3R6_COMMIT,
                        "original_R3R6_runner_blob": ORIGINAL_R3R6_BLOB,
                        "physics_changed": False,
                        "support_domain_changed": False,
                        "physical_time_advanced": False,
                        "automatic_rerun_authorized": False,
                        "O3R7_authorized": False,
                    },
                    indent=2, sort_keys=True
                ) + "\n",
                encoding="utf-8",
            )
        print(MILESTONE+": TECHNICAL / AUTHORITY BLOCK")
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
    p.add_argument("--verbose-solver", action="store_true")
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        structural_self_test(Path(args.project_root).resolve())
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root, args.verbose_solver))
