#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


M = "POSTV16-AV5-B2-R1"
NAME = "Correctness-Audit Key Repair + Frozen B2 Paired End-to-End Wall-Clock Economics Execution"

BRANCH = "postv16-av4-pivot"
PARENT = "9f3461aece2f0e4faf854c7b6445540d6c449aca"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV5 = Path("post_v16") / RID / "POSTV16_AV5_Learned_Acceleration"

ORIGINAL_B2_RUNNER = (
    "PAD_Stream_POSTV16_AV5_B2_Prospective_Day30_Only_FrozenCheckpoint_"
    "Paired_EndToEnd_WallClock_Economics_Execution.py"
)
ORIGINAL_B2_RUNNER_SHA256 = "07ac02f67c40ef3acfb6f79175448ab890b3ba589385fdb2729b3be12a9b9d7d"
ORIGINAL_B2_RUNNER_BLOB = "19d15c9136c9ffc3a5348192647046ec8e2cf77d"

ORIGINAL_BLOCK_REL = BASE_AV5 / "POSTV16_AV5_B2_BLOCKED"
ORIGINAL_BLOCK_FILE = "POSTV16_AV5_B2_Blocked_Report.json"
ORIGINAL_BLOCK_STATUS = "POSTV16AV5B2_TECHNICAL_OR_AUTHORITY_BLOCK"
ORIGINAL_BLOCK_STAGE = "warmup_and_correctness"
ORIGINAL_BLOCK_EXCEPTION = "KeyError('selected_seed')"

R1_TOKEN = "POSTV16_AV5_B2_R1"
R1_OUT_REL = BASE_AV5 / (
    R1_TOKEN + "_Prospective_Day30_Only_FrozenCheckpoint_Paired_EndToEnd_WallClock_Economics_Execution"
)
R1_BLOCK_REL = BASE_AV5 / (R1_TOKEN + "_BLOCKED")
R1_SUMMARY = f"PAD_Stream_{R1_TOKEN}_Summary.json"
R1_DECISION = f"{R1_TOKEN}_Decision_Contract.json"
R1_MANIFEST = f"{R1_TOKEN}_Artifact_Manifest.csv"
R1_PROVENANCE = f"{R1_TOKEN}_Technical_Repair_Provenance.json"

BAD_GATE = (
    'gate("correctness_candidate_Day60plus_no_model_dispatch", '
    'all(r["selected_seed"] == "TEMPORAL" for r in correctness_rows[1:]))'
)
GOOD_GATE = (
    'gate("correctness_candidate_Day60plus_no_model_dispatch", '
    'all(r["candidate_selected_seed"] == "TEMPORAL" for r in correctness_rows[1:]))'
)


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def patch_exact_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise GateError(f"patch_count_{label}:{count}")
    return text.replace(old, new, 1)


def patched_source(original: str) -> str:
    s = original
    s = patch_exact_once(
        s,
        'M = "POSTV16-AV5-B2"',
        'M = "POSTV16-AV5-B2-R1"',
        "milestone",
    )
    s = patch_exact_once(
        s,
        'NAME = "Prospective Day30-Only Frozen-Checkpoint Dispatch + Paired End-to-End Wall-Clock Economics Execution"',
        'NAME = "Correctness-Audit Key Repair + Prospective Day30-Only Frozen-Checkpoint Dispatch + Paired End-to-End Wall-Clock Economics Execution"',
        "name",
    )
    s = patch_exact_once(
        s,
        '"POSTV16AV5B2_PROSPECTIVE_DAY30_ONLY_FROZEN_CHECKPOINT_PAIRED_END_TO_END_"',
        '"POSTV16AV5B2R1_CORRECTNESS_AUDIT_KEY_REPAIR_PROSPECTIVE_DAY30_ONLY_FROZEN_CHECKPOINT_PAIRED_END_TO_END_"',
        "pass_status",
    )
    s = patch_exact_once(
        s,
        'BLOCK = "POSTV16AV5B2_TECHNICAL_OR_AUTHORITY_BLOCK"',
        'BLOCK = "POSTV16AV5B2R1_TECHNICAL_OR_AUTHORITY_BLOCK"',
        "block_status",
    )
    s = patch_exact_once(
        s,
        'PARENT = "0d8ca28b2b229b071a80bc018c819396c4601c31"',
        'PARENT = "9f3461aece2f0e4faf854c7b6445540d6c449aca"',
        "parent",
    )
    s = patch_exact_once(
        s,
        'OUT_TOKEN = "POSTV16_AV5_B2"',
        'OUT_TOKEN = "POSTV16_AV5_B2_R1"',
        "out_token",
    )
    s = patch_exact_once(s, BAD_GATE, GOOD_GATE, "correctness_audit_key")
    s = patch_exact_once(
        s,
        'print("POSTV16 AV5-B2 structural self-test: PASS")',
        'print("POSTV16 AV5-B2-R1 patched-child structural self-test: PASS")',
        "selftest_label",
    )
    s = patch_exact_once(
        s,
        'print("POSTV16-AV5-B2 — PROSPECTIVE DAY30-ONLY FROZEN-CHECKPOINT PAIRED END-TO-END WALL-CLOCK ECONOMICS EXECUTION")',
        'print("POSTV16-AV5-B2-R1 — CORRECTNESS-AUDIT KEY REPAIR + PROSPECTIVE DAY30-ONLY FROZEN-CHECKPOINT PAIRED END-TO-END WALL-CLOCK ECONOMICS EXECUTION")',
        "banner",
    )
    return s


def selftest() -> None:
    miniature = "\n".join([
        'M = "POSTV16-AV5-B2"',
        'NAME = "Prospective Day30-Only Frozen-Checkpoint Dispatch + Paired End-to-End Wall-Clock Economics Execution"',
        'PASS = (',
        '    "POSTV16AV5B2_PROSPECTIVE_DAY30_ONLY_FROZEN_CHECKPOINT_PAIRED_END_TO_END_"',
        ')',
        'BLOCK = "POSTV16AV5B2_TECHNICAL_OR_AUTHORITY_BLOCK"',
        'PARENT = "0d8ca28b2b229b071a80bc018c819396c4601c31"',
        'OUT_TOKEN = "POSTV16_AV5_B2"',
        BAD_GATE,
        'print("POSTV16 AV5-B2 structural self-test: PASS")',
        'print("POSTV16-AV5-B2 — PROSPECTIVE DAY30-ONLY FROZEN-CHECKPOINT PAIRED END-TO-END WALL-CLOCK ECONOMICS EXECUTION")',
    ])
    p = patched_source(miniature)
    assert 'r["candidate_selected_seed"]' in p
    assert 'r["selected_seed"] == "TEMPORAL" for r in correctness_rows[1:]' not in p
    assert 'M = "POSTV16-AV5-B2-R1"' in p
    assert 'OUT_TOKEN = "POSTV16_AV5_B2_R1"' in p
    assert PARENT in p
    print("POSTV16 AV5-B2-R1 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    try:
        print("=" * 214)
        print("POSTV16-AV5-B2-R1 — IMMUTABLE B2 BLOCK BINDING / CORRECTNESS-AUDIT KEY REPAIR / ORIGINAL B2 ECONOMICS PROTOCOL")
        print("=" * 214)
        print("REPAIR SCOPE: one incorrect correctness-audit dictionary key only.")
        print("ORIGINAL B2 MEASURED TIMING PAIRS: 0. LOCKED OOD: unopened.")
        print("NO TRAINING / NEW CHECKPOINT / RESELECTION / RETUNING / NORMALIZATION REFIT.")
        print()

        stage = "repository_authority"
        branch = gt(root, "branch", "--show-current")
        parent = gt(root, "rev-parse", "HEAD^")
        clean = gt(root, "status", "--porcelain")
        gate("branch_exact", branch == BRANCH, branch)
        gate("parent_exact", parent == PARENT, parent)
        gate("repository_clean", clean == "", clean)

        original_path = root / ORIGINAL_B2_RUNNER
        gate("original_B2_runner_present", original_path.is_file(), str(original_path))
        gate("original_B2_runner_SHA256_exact", sha(original_path) == ORIGINAL_B2_RUNNER_SHA256, sha(original_path))
        original_blob = gt(root, "hash-object", str(original_path)) if original_path.is_file() else "missing"
        gate("original_B2_runner_blob_exact", original_blob == ORIGINAL_B2_RUNNER_BLOB, original_blob)

        stage = "immutable_original_B2_BLOCK_authority"
        block_path = drive / ORIGINAL_BLOCK_REL / ORIGINAL_BLOCK_FILE
        gate("original_B2_BLOCK_present", block_path.is_file(), str(block_path))
        b = json.loads(block_path.read_text(encoding="utf-8"))
        gate("original_B2_BLOCK_status_exact", b.get("status") == ORIGINAL_BLOCK_STATUS, b.get("status"))
        gate("original_B2_BLOCK_stage_exact", b.get("failed_stage") == ORIGINAL_BLOCK_STAGE, b.get("failed_stage"))
        gate("original_B2_BLOCK_exception_exact", b.get("exception") == ORIGINAL_BLOCK_EXCEPTION, b.get("exception"))
        gate("original_B2_checkpoint_loaded", b.get("checkpoint_loaded") is True)
        gate("original_B2_model_inference_count_exact_2", int(b.get("model_inference_count")) == 2, b.get("model_inference_count"))
        gate("original_B2_warmup_candidate_exact_2", int(b.get("warmup_candidate_trajectories")) == 2, b.get("warmup_candidate_trajectories"))
        gate("original_B2_warmup_baseline_exact_2", int(b.get("warmup_baseline_trajectories")) == 2, b.get("warmup_baseline_trajectories"))
        gate("original_B2_measured_candidate_zero", int(b.get("measured_candidate_trajectories")) == 0, b.get("measured_candidate_trajectories"))
        gate("original_B2_measured_baseline_zero", int(b.get("measured_baseline_trajectories")) == 0, b.get("measured_baseline_trajectories"))
        gate("original_B2_locked_OOD_unopened", b.get("locked_OOD_loaded_or_scored") is False)
        gate("original_B2_no_training", b.get("model_training_executed") is False)
        gate("original_B2_no_new_checkpoint", b.get("new_checkpoint_created") is False)
        gate("original_B2_no_reselection", b.get("checkpoint_reselection_executed") is False)
        gate("original_B2_no_retuning", b.get("retuning_executed") is False)
        gate("original_B2_no_normalization_refit", b.get("normalization_refit_executed") is False)
        gate("original_B2_production_locked", b.get("AV5_production_execution_authorized") is False)
        gate("original_B2_P3_locked", b.get("P3_authorized") is False)
        gate("original_B2_AV4_unmutated", b.get("AV4_state_mutation_executed") is False)
        gate("original_B2_no_time_advance", b.get("physical_time_advance_executed") is False)

        stage = "technical_repair_freeze"
        original_text = original_path.read_text(encoding="utf-8")
        gate("bad_key_occurs_exactly_once", original_text.count(BAD_GATE) == 1, original_text.count(BAD_GATE))
        gate("good_key_absent_from_original", original_text.count(GOOD_GATE) == 0, original_text.count(GOOD_GATE))

        repaired = patched_source(original_text)
        gate("repaired_bad_key_absent", BAD_GATE not in repaired)
        gate("repaired_good_key_exactly_once", repaired.count(GOOD_GATE) == 1, repaired.count(GOOD_GATE))

        # Publish provenance before the child run. The patched child creates the rest of the R1 output
        # and its manifest will therefore include this immutable repair record.
        r1_out = drive / R1_OUT_REL
        r1_block = drive / R1_BLOCK_REL / f"{R1_TOKEN}_Blocked_Report.json"
        gate("no_preexisting_R1_PASS", not (r1_out / R1_SUMMARY).exists())
        gate("no_preexisting_R1_BLOCK", not r1_block.exists())

        r1_out.mkdir(parents=True, exist_ok=True)
        provenance = {
            "milestone": M,
            "repair_classification": "ONE_DICTIONARY_KEY_REFERENCE_REPAIR_ONLY",
            "original_B2_commit": PARENT,
            "original_B2_runner": ORIGINAL_B2_RUNNER,
            "original_B2_runner_sha256": ORIGINAL_B2_RUNNER_SHA256,
            "original_B2_runner_git_blob": ORIGINAL_B2_RUNNER_BLOB,
            "original_B2_BLOCK_preserved": True,
            "original_B2_BLOCK_failed_stage": ORIGINAL_BLOCK_STAGE,
            "original_B2_BLOCK_exception": ORIGINAL_BLOCK_EXCEPTION,
            "original_B2_warmup_pairs_completed": 2,
            "original_B2_measured_timing_pairs_completed": 0,
            "original_B2_locked_OOD_loaded_or_scored": False,
            "repair_from": 'correctness_rows[1:]["selected_seed"]',
            "repair_to": 'correctness_rows[1:]["candidate_selected_seed"]',
            "timing_protocol_changed": False,
            "economic_acceptance_thresholds_changed": False,
            "physics_changed": False,
            "checkpoint_changed": False,
            "validation_realization_changed": False,
            "locked_OOD_policy_changed": False,
        }
        provenance_path = r1_out / R1_PROVENANCE
        if provenance_path.exists() and provenance_path.read_bytes() != jb(provenance):
            raise GateError("existing_R1_repair_provenance_differs")
        if not provenance_path.exists():
            provenance_path.write_bytes(jb(provenance))

        stage = "patched_child_execution"
        with tempfile.TemporaryDirectory(prefix="av5b2r1_") as td:
            patched_path = Path(td) / "PAD_Stream_POSTV16_AV5_B2_R1_patched_child.py"
            patched_path.write_text(repaired, encoding="utf-8")
            subprocess.run([sys.executable, "-m", "py_compile", str(patched_path)], check=True)
            cp = subprocess.run([
                sys.executable,
                str(patched_path),
                "--project-root", str(root),
                "--drive-root", str(drive),
            ])

        if cp.returncode != 0:
            raise GateError(f"patched_child_exit_code:{cp.returncode}")

        stage = "R1_publication_verification"
        summary_path = r1_out / R1_SUMMARY
        decision_path = r1_out / R1_DECISION
        manifest_path = r1_out / R1_MANIFEST
        gate("R1_PASS_summary_present", summary_path.is_file(), str(summary_path))
        gate("R1_decision_present", decision_path.is_file(), str(decision_path))
        gate("R1_manifest_present", manifest_path.is_file(), str(manifest_path))
        gate("R1_repair_provenance_preserved", provenance_path.is_file())
        gate("R1_BLOCK_absent", not r1_block.exists())

        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        gate("R1_summary_milestone_exact", summary.get("milestone") == M, summary.get("milestone"))
        gate("R1_summary_status_is_PASS", "PASS_NO_TRAINING_NO_OOD_REUSE" in str(summary.get("status")), summary.get("status"))
        gate("R1_decision_milestone_exact", decision.get("milestone") == M, decision.get("milestone"))
        gate("R1_locked_OOD_unopened", summary.get("locked_OOD_loaded_or_scored") is False)
        gate("R1_production_locked", summary.get("AV5_production_execution_authorized") is False)
        gate("R1_P3_locked", summary.get("P3_authorized") is False)

        manifest_rows = list(csv.DictReader(manifest_path.open(newline="", encoding="utf-8")))
        manifested = {row["file"] for row in manifest_rows}
        gate("R1_repair_provenance_manifested", R1_PROVENANCE in manifested)

        print()
        print("=" * 214)
        print(M, "PASS")
        print("Original B2 BLOCK preserved                         : True")
        print("Original B2 measured timing pairs                   : 0")
        print("Repair scope                                        : selected_seed -> candidate_selected_seed audit key")
        print("Timing / economics protocol changed                 : False")
        print("LOCKED OOD reused                                   : False")
        print("Wall-clock economic qualification                   :", summary.get("wallclock_economic_qualification_pass"))
        print("Candidate faster pairs                              :", summary.get("candidate_faster_pairs"), "/ 11")
        print("Candidate / baseline median seconds                 :", summary.get("candidate_median_seconds"), "/", summary.get("baseline_median_seconds"))
        print("B3 interpretation freeze authorized                 :", summary.get("B3_interpretation_freeze_authorized"))
        print("Production / P3 authorized                          : False / False")
        print("=" * 214)
        return 0

    except Exception as exc:
        # If the child already wrote its own R1 BLOCK, preserve it. Otherwise write a wrapper block.
        block_dir = drive / R1_BLOCK_REL
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{R1_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": "POSTV16AV5B2R1_TECHNICAL_OR_AUTHORITY_BLOCK",
                "failed_stage": stage,
                "exception": repr(exc),
                "original_B2_BLOCK_preserved": True,
                "repair_scope": "selected_seed_to_candidate_selected_seed_correctness_audit_key_only",
                "AV5_production_execution_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
