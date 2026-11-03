#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any


M = "POSTV16-AV5-B3"
NAME = "Validation Wall-Clock Economics Outcome Interpretation + AV5 Learned-Acceleration Closure Decision Freeze"

PASS = (
    "POSTV16AV5B3_VALIDATION_WALLCLOCK_ECONOMICS_OUTCOME_INTERPRETATION_"
    "AND_AV5_LEARNED_ACCELERATION_CLOSURE_DECISION_FREEZE_PASS_NO_MODEL_EXECUTION"
)
BLOCK = "POSTV16AV5B3_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "fa1f75bec92cc370d529d047ab1ff40a6102fa0d"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV5 = Path("post_v16") / RID / "POSTV16_AV5_Learned_Acceleration"

AV4_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"
CHECKPOINT_SHA = "4cb41080b1d92780af21c9fae6e830a681d69315940656f1938db97c75dc52ef"

# Repository authorities.
B2R1_RUNNER = "PAD_Stream_POSTV16_AV5_B2_R1_Correctness_Audit_Key_Repair_and_Paired_WallClock_Economics_Execution.py"
B2R1_RUNNER_BLOB = "bd6a2b2d3af90f09982a4d3c101be9e0dc46c407"
B2_RUNNER = (
    "PAD_Stream_POSTV16_AV5_B2_Prospective_Day30_Only_FrozenCheckpoint_"
    "Paired_EndToEnd_WallClock_Economics_Execution.py"
)
B2_RUNNER_BLOB = "19d15c9136c9ffc3a5348192647046ec8e2cf77d"
B1_RUNNER = "PAD_Stream_POSTV16_AV5_B1_Day30_ColdStart_Dispatch_WallClock_Economics_Prospective_Design_Freeze.py"
B1_RUNNER_BLOB = "15bc37231d32283fbcd1053619f4a833f349f40e"
A7_RUNNER = "PAD_Stream_POSTV16_AV5_A7_Scientific_Outcome_Interpretation_and_Production_Decision_Freeze.py"
A7_RUNNER_BLOB = "3e39af491ed0c3f04c40958eb79571f43d4d6eb7"

SOURCE_BLOBS = {
    B2R1_RUNNER: B2R1_RUNNER_BLOB,
    B2_RUNNER: B2_RUNNER_BLOB,
    B1_RUNNER: B1_RUNNER_BLOB,
    A7_RUNNER: A7_RUNNER_BLOB,
}

# Frozen Drive authorities.
A7_TOKEN = "POSTV16_AV5_A7"
A7_REL = BASE_AV5 / (A7_TOKEN + "_Scientific_Outcome_Interpretation_and_Production_Decision_Freeze")
A7_SUMMARY = f"PAD_Stream_{A7_TOKEN}_Summary.json"
A7_DECISION = f"{A7_TOKEN}_Decision_Contract.json"
A7_MANIFEST = f"{A7_TOKEN}_Artifact_Manifest.csv"

B1_TOKEN = "POSTV16_AV5_B1"
B1_REL = BASE_AV5 / (B1_TOKEN + "_Day30_ColdStart_Dispatch_WallClock_Economics_Prospective_Design_Freeze")
B1_SUMMARY = f"PAD_Stream_{B1_TOKEN}_Summary.json"
B1_TIMING = f"{B1_TOKEN}_EndToEnd_WallClock_Protocol.json"
B1_DECISION = f"{B1_TOKEN}_Decision_Contract.json"
B1_MANIFEST = f"{B1_TOKEN}_Artifact_Manifest.csv"

ORIGINAL_B2_BLOCK_REL = BASE_AV5 / "POSTV16_AV5_B2_BLOCKED"
ORIGINAL_B2_BLOCK = "POSTV16_AV5_B2_Blocked_Report.json"

B2R1_TOKEN = "POSTV16_AV5_B2_R1"
B2R1_REL = BASE_AV5 / (
    B2R1_TOKEN + "_Prospective_Day30_Only_FrozenCheckpoint_Paired_EndToEnd_WallClock_Economics_Execution"
)
B2R1_SUMMARY = f"PAD_Stream_{B2R1_TOKEN}_Summary.json"
B2R1_PAIR_AUDIT = f"{B2R1_TOKEN}_Paired_WallClock_Audit.csv"
B2R1_CORRECTNESS = f"{B2R1_TOKEN}_Validation_Correctness_Audit.csv"
B2R1_OUTCOME = f"{B2R1_TOKEN}_WallClock_Economics_Outcome_Contract.json"
B2R1_HANDOFF = f"{B2R1_TOKEN}_B3_Handoff_Contract.json"
B2R1_DECISION = f"{B2R1_TOKEN}_Decision_Contract.json"
B2R1_MANIFEST = f"{B2R1_TOKEN}_Artifact_Manifest.csv"
B2R1_PROVENANCE = f"{B2R1_TOKEN}_Technical_Repair_Provenance.json"

B2R1_STATUS = (
    "POSTV16AV5B2R1_CORRECTNESS_AUDIT_KEY_REPAIR_PROSPECTIVE_DAY30_ONLY_FROZEN_CHECKPOINT_"
    "PAIRED_END_TO_END_WALLCLOCK_ECONOMICS_EXECUTION_PASS_NO_TRAINING_NO_OOD_REUSE"
)
B2R1_CLASSIFICATION = (
    "AV5_DAY30_ONLY_FROZEN_CHECKPOINT_VALIDATION_END_TO_END_WALLCLOCK_"
    "ECONOMICS_NOT_QUALIFIED_B3_INTERPRETATION_FREEZE_AUTHORIZED_NO_OOD_REUSE"
)

OUT_TOKEN = "POSTV16_AV5_B3"
OUT_REL = BASE_AV5 / (
    OUT_TOKEN + "_Validation_WallClock_Economics_Outcome_Interpretation_and_AV5_LearnedAcceleration_Closure_Decision_Freeze"
)
BLOCK_REL = BASE_AV5 / (OUT_TOKEN + "_BLOCKED")

SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
INTERPRETATION = f"{OUT_TOKEN}_Scientific_and_Economic_Interpretation_Contract.json"
DISPOSITION = f"{OUT_TOKEN}_Learned_Pressure_Seed_Disposition_Contract.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
GATE_MATRIX = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"


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


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csvb(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        result[p.name] = row["sha256"]
    if not result:
        raise GateError(f"manifest_empty:{filename}")
    return result


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


def as_bool(v: str) -> bool:
    return str(v).strip().lower() in {"true", "1", "yes"}


def selftest() -> None:
    assert BRANCH == "postv16-av4-pivot"
    assert len(PARENT) == 40
    assert len(CHECKPOINT_SHA) == 64
    assert B2R1_CLASSIFICATION.endswith("NO_OOD_REUSE")
    print("POSTV16 AV5-B3 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
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
        print("POSTV16-AV5-B3 — VALIDATION WALL-CLOCK ECONOMICS OUTCOME INTERPRETATION / AV5 LEARNED-ACCELERATION CLOSURE")
        print("=" * 214)
        print("READ-ONLY CLOSURE. NO MODEL EXECUTION.")
        print("NO TRAINING / NEW CHECKPOINT / RESELECTION / RETUNING / NORMALIZATION REFIT.")
        print("LOCKED OOD IS NOT REUSED FOR SELECTION.")
        print("NO AV4 STATE MUTATION. NO PHYSICAL TIME ADVANCE. PRODUCTION AND P3 REMAIN LOCKED.")
        print()

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        branch = gt(root, "branch", "--show-current")
        parent = gt(root, "rev-parse", "HEAD^")
        clean = gt(root, "status", "--porcelain")
        gate("branch_exact", branch == BRANCH, branch)
        gate("parent_exact", parent == PARENT, parent)
        gate("repository_clean", clean == "", clean)
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "A7_scientific_outcome_authority"
        a7d = drive / A7_REL
        a7m = manifest(a7d, A7_MANIFEST)
        a7s = js(a7d / A7_SUMMARY)
        a7c = js(a7d / A7_DECISION)
        gate("A7_manifest_nonempty", len(a7m) > 0)
        gate("A7_AV4_state_SHA_exact", a7s.get("AV4_authoritative_state_sha256") == AV4_STATE_SHA)
        gate("A7_checkpoint_SHA_exact", a7s.get("checkpoint_sha256") == CHECKPOINT_SHA)
        gate("A7_exactness_safety_generalized", a7s.get("exactness_safety_generalized") is True)
        gate("A7_OOD_acceleration_observed", a7s.get("OOD_acceleration_observed") is True)
        gate("A7_learned_seed_admission_sparse", int(a7s.get("learned_seed_admitted_states")) == 1)
        gate("A7_only_improved_day30", float(a7s.get("only_improved_state_day")) == 30.0)
        gate("A7_wallclock_not_certified", a7s.get("wall_clock_net_speedup_certified") is False)
        gate("A7_production_locked", a7c.get("AV5_production_execution_authorized") is False)
        gate("A7_P3_locked", a7c.get("P3_authorized") is False)

        stage = "B1_prospective_economics_protocol_authority"
        b1d = drive / B1_REL
        b1m = manifest(b1d, B1_MANIFEST)
        b1s = js(b1d / B1_SUMMARY)
        b1t = js(b1d / B1_TIMING)
        b1c = js(b1d / B1_DECISION)
        gate("B1_manifest_nonempty", len(b1m) > 0)
        gate("B1_checkpoint_SHA_exact", b1s.get("checkpoint_sha256") == CHECKPOINT_SHA)
        gate("B1_validation_realization_exact", b1s.get("B2_validation_realization") == "AV3CR0003")
        gate("B1_11_pairs_exact", int(b1s.get("paired_timing_repeats")) == 11)
        gate("B1_2_warmups_exact", int(b1s.get("warmup_pairs")) == 2)
        gate("B1_9_of_11_threshold_exact", int(b1s.get("required_candidate_faster_pairs")) == 9)
        econ = b1t.get("economic_acceptance", {})
        gate("B1_both_economic_criteria_required", econ.get("both_required") is True)
        gate("B1_validation_only", b1c.get("B2_wallclock_acceptance_is_validation_only") is True)
        gate("B1_production_locked", b1c.get("AV5_production_execution_authorized") is False)
        gate("B1_P3_locked", b1c.get("P3_authorized") is False)

        stage = "original_B2_BLOCK_and_R1_repair_provenance"
        original_block = drive / ORIGINAL_B2_BLOCK_REL / ORIGINAL_B2_BLOCK
        gate("original_B2_BLOCK_present", original_block.is_file(), str(original_block))
        ob = js(original_block)
        gate("original_B2_BLOCK_stage_exact", ob.get("failed_stage") == "warmup_and_correctness", ob.get("failed_stage"))
        gate("original_B2_BLOCK_exception_exact", ob.get("exception") == "KeyError('selected_seed')", ob.get("exception"))
        gate("original_B2_measured_pairs_zero", int(ob.get("measured_candidate_trajectories")) == 0 and int(ob.get("measured_baseline_trajectories")) == 0)
        gate("original_B2_OOD_unopened", ob.get("locked_OOD_loaded_or_scored") is False)

        b2d = drive / B2R1_REL
        b2m = manifest(b2d, B2R1_MANIFEST)
        b2s = js(b2d / B2R1_SUMMARY)
        b2o = js(b2d / B2R1_OUTCOME)
        b2h = js(b2d / B2R1_HANDOFF)
        b2c = js(b2d / B2R1_DECISION)
        b2p = js(b2d / B2R1_PROVENANCE)
        pairs = csvr(b2d / B2R1_PAIR_AUDIT)
        correctness = csvr(b2d / B2R1_CORRECTNESS)

        gate("B2R1_manifest_nonempty", len(b2m) > 0)
        gate("B2R1_repair_provenance_manifested", B2R1_PROVENANCE in b2m)
        gate("B2R1_repair_scope_key_only", b2p.get("repair_classification") == "ONE_DICTIONARY_KEY_REFERENCE_REPAIR_ONLY")
        gate("B2R1_timing_protocol_unchanged", b2p.get("timing_protocol_changed") is False)
        gate("B2R1_economic_thresholds_unchanged", b2p.get("economic_acceptance_thresholds_changed") is False)
        gate("B2R1_physics_unchanged", b2p.get("physics_changed") is False)
        gate("B2R1_checkpoint_unchanged", b2p.get("checkpoint_changed") is False)
        gate("B2R1_status_exact", b2s.get("status") == B2R1_STATUS, b2s.get("status"))
        gate("B2R1_classification_exact", b2s.get("classification") == B2R1_CLASSIFICATION, b2s.get("classification"))
        gate("B2R1_AV4_state_SHA_exact", b2s.get("AV4_authoritative_state_sha256") == AV4_STATE_SHA)
        gate("B2R1_checkpoint_SHA_exact", b2s.get("checkpoint_sha256") == CHECKPOINT_SHA)
        gate("B2R1_validation_realization_exact", b2s.get("validation_realization") == "AV3CR0003")
        gate("B2R1_11_pairs_completed", int(b2s.get("paired_timing_repeats_completed")) == 11)
        gate("B2R1_2_warmups_completed", int(b2s.get("warmup_pairs_completed")) == 2)
        gate("B2R1_Day30_learned_admitted", b2s.get("candidate_Day30_learned_seed_admitted") is True)
        gate("B2R1_candidate_median_not_lower", float(b2s.get("candidate_median_seconds")) >= float(b2s.get("baseline_median_seconds")))
        gate("B2R1_candidate_faster_pairs_exact_4", int(b2s.get("candidate_faster_pairs")) == 4, b2s.get("candidate_faster_pairs"))
        gate("B2R1_required_faster_pairs_exact_9", int(b2s.get("required_candidate_faster_pairs")) == 9)
        gate("B2R1_economic_qualification_false", b2s.get("wallclock_economic_qualification_pass") is False)
        gate("B2R1_OOD_never_loaded", b2s.get("locked_OOD_loaded_or_scored") is False)
        gate("B2R1_no_training", b2s.get("model_training_executed") is False)
        gate("B2R1_no_new_checkpoint", b2s.get("new_checkpoint_created") is False)
        gate("B2R1_no_reselection", b2s.get("checkpoint_reselection_executed") is False)
        gate("B2R1_no_retuning", b2s.get("retuning_executed") is False)
        gate("B2R1_no_normalization_refit", b2s.get("normalization_refit_executed") is False)
        gate("B2R1_production_locked", b2s.get("AV5_production_execution_authorized") is False)
        gate("B2R1_P3_locked", b2s.get("P3_authorized") is False)
        gate("B2R1_11_pair_rows", len(pairs) == 11, len(pairs))
        gate("B2R1_9_correctness_rows", len(correctness) == 9, len(correctness))
        gate("B2R1_B3_authorized", b2c.get("B3_authorized") is True and b2h.get("authorized") is True)
        gate("B2R1_B3_execution_authorized", b2c.get("B3_execution_authorized") is True and b2h.get("execution") is True)
        gate("B2R1_B3_no_model_execution", b2c.get("B3_must_not_execute_model") is True and b2h.get("must_not_execute_model") is True)
        gate("B2R1_B3_no_OOD_reuse", b2c.get("B3_must_not_reuse_locked_OOD_for_selection") is True and b2h.get("must_not_reuse_locked_OOD_for_selection") is True)

        stage = "frozen_economic_interpretation"
        candidate_median = float(b2o["candidate_median_seconds"])
        baseline_median = float(b2o["baseline_median_seconds"])
        candidate_mean = float(b2o["candidate_mean_seconds"])
        baseline_mean = float(b2o["baseline_mean_seconds"])
        median_delta = float(b2o["median_candidate_minus_baseline_seconds"])
        median_ratio = float(b2o["median_candidate_to_baseline_ratio"])
        median_fractional_speedup = float(b2o["median_fractional_speedup"])
        faster_pairs = int(b2o["candidate_faster_pairs"])
        sign_p = float(b2o["one_sided_exact_sign_test_tail_probability"])

        gate("economic_criterion_1_false", b2o.get("criterion_1_candidate_median_lower") is False)
        gate("economic_criterion_2_false", b2o.get("criterion_2_candidate_faster_at_least_9_of_11") is False)
        gate("economic_both_required_false", b2o.get("economic_qualification_both_required") is False)
        gate("median_delta_positive", median_delta > 0.0, median_delta)
        gate("median_ratio_above_one", median_ratio > 1.0, median_ratio)
        gate("sign_test_not_supportive", sign_p > 0.05, sign_p)

        candidate_wins = sum(as_bool(r["candidate_faster"]) for r in pairs)
        gate("pair_audit_candidate_wins_reproduced_4", candidate_wins == 4, candidate_wins)

        # Interpretation intentionally does not substitute mean behavior for the frozen robust criteria.
        classification = (
            "AV5_LEARNED_PRESSURE_SEED_MECHANISM_SCIENTIFICALLY_VALIDATED_EXACT_SAFE_"
            "BUT_VALIDATION_END_TO_END_WALLCLOCK_ECONOMICS_NOT_QUALIFIED_"
            "PRODUCTION_AND_P3_NOT_AUTHORIZED_AV5_ACCELERATION_EXPERIMENT_CLOSED"
        )

        interpretation = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "scientific_result": {
                "learned_seed_mechanism_exactness_and_safety_validated": True,
                "locked_OOD_generalization_observed_in_A6": True,
                "locked_OOD_acceleration_was_sparse_and_Day30_focused": True,
                "frozen_checkpoint_sha256": CHECKPOINT_SHA,
            },
            "validation_wallclock_result": {
                "validation_realization": "AV3CR0003",
                "candidate_Day30_learned_seed_admitted": True,
                "candidate_median_seconds": candidate_median,
                "baseline_median_seconds": baseline_median,
                "median_candidate_minus_baseline_seconds": median_delta,
                "median_candidate_to_baseline_ratio": median_ratio,
                "median_fractional_speedup": median_fractional_speedup,
                "candidate_mean_seconds": candidate_mean,
                "baseline_mean_seconds": baseline_mean,
                "candidate_faster_pairs": faster_pairs,
                "measured_pairs": 11,
                "required_candidate_faster_pairs": 9,
                "one_sided_exact_sign_test_tail_probability": sign_p,
                "criterion_1_candidate_median_lower": False,
                "criterion_2_candidate_faster_at_least_9_of_11": False,
                "economic_qualification_pass": False,
            },
            "interpretation": (
                "The safeguarded learned pressure-seed mechanism remains a valid scientific result because exact "
                "residual admission and exact FV correction preserve the authoritative solution. However, the "
                "prospectively frozen validation wall-clock protocol did not demonstrate robust end-to-end economic "
                "benefit. The candidate median trajectory time was slower than temporal-only baseline and the "
                "candidate won only 4 of 11 paired repeats. A lower arithmetic mean does not override the two "
                "prospectively frozen acceptance criteria and is influenced by large timing excursions in both arms."
            ),
        }

        disposition = {
            "milestone": M,
            "status": PASS,
            "frozen_checkpoint_sha256": CHECKPOINT_SHA,
            "checkpoint_disposition": "RESEARCH_REFERENCE_ONLY_NOT_PRODUCTION_AUTHORIZED",
            "scientific_mechanism_disposition": "VALIDATED_EXACT_SAFE_SAFEGUARDED_PROPOSAL_MECHANISM",
            "economic_disposition": "NOT_QUALIFIED_FOR_PRODUCTION_ACCELERATION_UNDER_FROZEN_B1_B2_PROTOCOL",
            "production_pressure_seed_policy": "NO_CHANGE_AUTHORIZED_BY_AV5",
            "temporal_seed_exact_correction_baseline_remains_authoritative_reference": True,
            "exact_residual_admission_contract_preserved_as_research_mechanism": True,
            "exact_FV_correction_remains_authoritative": True,
            "direct_spsolve_reference_and_fallback_remains_required": True,
            "existing_A5R1_checkpoint_may_be_retrained": False,
            "existing_A5R1_checkpoint_may_be_reselected": False,
            "existing_A5R1_checkpoint_may_be_retuned": False,
            "already_opened_locked_OOD_may_be_reused_for_future_selection": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "AV5_scientific_mechanism_validated": True,
            "AV5_validation_wallclock_economic_qualification_pass": False,
            "AV5_learned_acceleration_workstream_closed": True,
            "checkpoint_remains_frozen": True,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "checkpoint_disposition": "RESEARCH_REFERENCE_ONLY_NOT_PRODUCTION_AUTHORIZED",
            "AV5_model_training_authorized": False,
            "AV5_checkpoint_reselection_authorized": False,
            "AV5_retuning_authorized": False,
            "AV5_production_execution_authorized": False,
            "P3_authorized": False,
            "AV4_state_mutation_authorized": False,
            "physical_time_advance_authorized": False,
            "locked_OOD_reuse_for_selection_authorized": False,
            "next_execution_authorized": False,
            "next_step": (
                "AV5 learned-acceleration experiment is closed; return to the PAD-Stream development roadmap "
                "for the next independently authorized workstream without promoting the AV5 checkpoint to production"
            ),
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "AV4_authoritative_state_sha256": AV4_STATE_SHA,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "scientific_mechanism_validated": True,
            "validation_wallclock_economic_qualification_pass": False,
            "candidate_Day30_learned_seed_admitted": True,
            "candidate_median_seconds": candidate_median,
            "baseline_median_seconds": baseline_median,
            "median_candidate_minus_baseline_seconds": median_delta,
            "median_candidate_to_baseline_ratio": median_ratio,
            "candidate_mean_seconds": candidate_mean,
            "baseline_mean_seconds": baseline_mean,
            "candidate_faster_pairs": faster_pairs,
            "required_candidate_faster_pairs": 9,
            "one_sided_exact_sign_test_tail_probability": sign_p,
            "locked_OOD_reused_for_selection": False,
            "AV5_learned_acceleration_workstream_closed": True,
            "checkpoint_disposition": "RESEARCH_REFERENCE_ONLY_NOT_PRODUCTION_AUTHORIZED",
            "model_training_executed": False,
            "model_inference_executed": False,
            "new_checkpoint_created": False,
            "checkpoint_reselection_executed": False,
            "retuning_executed": False,
            "normalization_refit_executed": False,
            "AV5_production_execution_authorized": False,
            "P3_authorized": False,
            "AV4_state_mutated": False,
            "physical_time_advance_executed": False,
            "next_execution_authorized": False,
        }

        output_files = {
            SUMMARY: jb(summary),
            INTERPRETATION: jb(interpretation),
            DISPOSITION: jb(disposition),
            DECISION: jb(decision),
            GATE_MATRIX: csvb(gates),
        }
        immutable_publish(out, output_files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                manifest_rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        immutable_publish(out, {MANIFEST: csvb(manifest_rows)})

        print()
        print("=" * 214)
        print(M, "PASS")
        print("Classification                                      :", classification)
        print("Scientific learned-seed mechanism validated         : True")
        print("Validation wall-clock economics qualified           : False")
        print("Candidate / baseline median seconds                 :", candidate_median, "/", baseline_median)
        print("Median candidate-minus-baseline seconds             :", median_delta)
        print("Candidate faster paired repeats                     :", faster_pairs, "/ 11")
        print("One-sided exact sign-test tail p                    :", sign_p)
        print("Frozen checkpoint disposition                       : RESEARCH REFERENCE ONLY")
        print("AV5 learned-acceleration workstream closed          : True")
        print("Production / P3 authorized                          : False / False")
        print("Next execution authorized                           : False")
        print("=" * 214)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "model_training_executed": False,
                "model_inference_executed": False,
                "new_checkpoint_created": False,
                "checkpoint_reselection_executed": False,
                "retuning_executed": False,
                "normalization_refit_executed": False,
                "locked_OOD_reused_for_selection": False,
                "AV5_production_execution_authorized": False,
                "P3_authorized": False,
                "AV4_state_mutation_executed": False,
                "physical_time_advance_executed": False,
                "next_execution_authorized": False,
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
