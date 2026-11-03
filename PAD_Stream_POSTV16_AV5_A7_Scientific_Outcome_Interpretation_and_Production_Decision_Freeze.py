#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

M = "POSTV16-AV5-A7"
NAME = "Scientific Outcome Interpretation + Learned-Acceleration Scope / Production Decision Freeze"
PASS = (
    "POSTV16AV5A7_SCIENTIFIC_OUTCOME_INTERPRETATION_AND_PRODUCTION_DECISION_"
    "FREEZE_PASS_NO_MODEL_EXECUTION"
)
BLOCK = "POSTV16AV5A7_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "7559a059462907a4f0bff0a0aba5b78fa5f71b79"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV5 = Path("post_v16") / RID / "POSTV16_AV5_Learned_Acceleration"
AV4_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"
CHECKPOINT_SHA = "4cb41080b1d92780af21c9fae6e830a681d69315940656f1938db97c75dc52ef"
CANONICAL_DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]

A6_RUNNER = "PAD_Stream_POSTV16_AV5_A6_Frozen_Checkpoint_OneTouch_LockedOOD_Sequential_PressureSeed_Evaluation.py"
A6_RUNNER_BLOB = "1d782e6f4616e7a31fcae031c959e1b7a384b46c"
A5R1_RUNNER = (
    "PAD_Stream_POSTV16_AV5_A5_R1_SG3_Blob_Authority_Repair_Controlled_Training_and_"
    "Validation_ExactCorrection_Checkpoint_Selection.py"
)
A5R1_RUNNER_BLOB = "dd1bfd2d8a854d218fc220949bc8ca63d92c650b"
SOURCE_BLOBS = {
    A6_RUNNER: A6_RUNNER_BLOB,
    A5R1_RUNNER: A5R1_RUNNER_BLOB,
}

A6_TOKEN = "POSTV16_AV5_A6"
A6_REL = BASE_AV5 / (
    A6_TOKEN + "_Frozen_Checkpoint_OneTouch_LockedOOD_Sequential_PressureSeed_Evaluation"
)
A6_SUMMARY = f"PAD_Stream_{A6_TOKEN}_Summary.json"
A6_OUTCOME = f"{A6_TOKEN}_LockedOOD_Outcome_Contract.json"
A6_DECISION = f"{A6_TOKEN}_Decision_Contract.json"
A6_AUDIT = f"{A6_TOKEN}_LockedOOD_Sequential_State_Audit.csv"
A6_MANIFEST = f"{A6_TOKEN}_Artifact_Manifest.csv"
A6_STATUS = (
    "POSTV16AV5A6_FROZEN_CHECKPOINT_ONE_TOUCH_LOCKED_OOD_SEQUENTIAL_PRESSURE_SEED_"
    "EVALUATION_PASS_NO_RETRAIN_NO_RESELECT_NO_RETUNE"
)
A6_CLASSIFICATION = (
    "AV5_FROZEN_PRESSURE_SEED_ONE_TOUCH_LOCKED_OOD_EXACT_CORRECTION_PASS_"
    "OOD_ACCELERATION_OBSERVED_NO_ADAPTATION"
)

A5R1_TOKEN = "POSTV16_AV5_A5_R1"
A5R1_REL = BASE_AV5 / (
    A5R1_TOKEN
    + "_SG3_Blob_Authority_Repair_Controlled_Training_and_Validation_ExactCorrection_Checkpoint_Selection"
)
A5R1_SUMMARY = f"PAD_Stream_{A5R1_TOKEN}_Summary.json"
A5R1_MANIFEST = f"{A5R1_TOKEN}_Artifact_Manifest.csv"

OUT_TOKEN = "POSTV16_AV5_A7"
OUT_REL = BASE_AV5 / (
    OUT_TOKEN + "_Scientific_Outcome_Interpretation_and_Production_Decision_Freeze"
)
BLOCK_REL = BASE_AV5 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
INTERPRETATION = f"{OUT_TOKEN}_Scientific_Interpretation_Contract.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
NEXT_RESEARCH = f"{OUT_TOKEN}_Focused_Research_Direction_Contract.json"
GATE_MATRIX = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
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
    import io
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
    assert len(CANONICAL_DAYS) == 9
    assert A6_CLASSIFICATION.endswith("OOD_ACCELERATION_OBSERVED_NO_ADAPTATION")
    print("POSTV16 AV5-A7 structural self-test: PASS")


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
        print("=" * 204)
        print("POSTV16-AV5-A7 — SCIENTIFIC OUTCOME INTERPRETATION / PRODUCTION DECISION FREEZE")
        print("=" * 204)
        print("READ-ONLY INTERPRETATION OF FROZEN A5-R1 + A6 RESULTS.")
        print("NO MODEL TRAINING. NO MODEL INFERENCE. NO CHECKPOINT RESELECTION. NO RETUNING.")
        print("NO AV4 STATE MUTATION. NO PHYSICAL TIME ADVANCE. NO PRODUCTION/P3 EXECUTION.")
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

        stage = "A5R1_checkpoint_provenance"
        a5d = drive / A5R1_REL
        a5m = manifest(a5d, A5R1_MANIFEST)
        a5s = js(a5d / A5R1_SUMMARY)
        gate("A5R1_manifest_nonempty", len(a5m) > 0)
        gate("A5R1_checkpoint_SHA_exact", a5s.get("checkpoint_sha256") == CHECKPOINT_SHA, a5s.get("checkpoint_sha256"))
        gate("A5R1_locked_OOD_unopened", a5s.get("locked_OOD_pressure_truth_opened") is False)
        gate("A5R1_AV4_state_unmutated", a5s.get("AV4_state_mutated") is False)

        stage = "A6_outcome_authority"
        a6d = drive / A6_REL
        a6m = manifest(a6d, A6_MANIFEST)
        a6s = js(a6d / A6_SUMMARY)
        a6o = js(a6d / A6_OUTCOME)
        a6c = js(a6d / A6_DECISION)
        rows = csvr(a6d / A6_AUDIT)
        gate("A6_manifest_nonempty", len(a6m) > 0)
        gate("A6_status_exact", a6s.get("status") == A6_STATUS, a6s.get("status"))
        gate("A6_classification_exact", a6s.get("classification") == A6_CLASSIFICATION, a6s.get("classification"))
        gate("A6_AV4_state_SHA_exact", a6s.get("AV4_authoritative_state_sha256") == AV4_STATE_SHA)
        gate("A6_checkpoint_SHA_exact", a6s.get("checkpoint_sha256") == CHECKPOINT_SHA)
        gate("A6_checkpoint_loaded", a6s.get("checkpoint_loaded") is True)
        gate("A6_locked_OOD_realization_exact", a6s.get("locked_OOD_realization") == "AV3CR0004")
        gate("A6_nine_states_completed", int(a6s.get("locked_OOD_states_completed")) == 9)
        gate("A6_exactly_nine_inferences", int(a6s.get("model_inference_count")) == 9)
        gate("A6_one_learned_seed_admission", int(a6s.get("learned_seed_admitted_states")) == 1)
        gate("A6_no_selected_fallbacks", int(a6s.get("selected_direct_fallback_states")) == 0)
        gate("A6_no_temporal_fallbacks", int(a6s.get("temporal_direct_fallback_states")) == 0)
        gate("A6_OOD_acceleration_observed", a6s.get("OOD_acceleration_observed") is True)
        gate("A6_truth_opened_after_checkpoint_freeze", a6s.get("locked_OOD_pressure_truth_opened_only_after_checkpoint_freeze") is True)
        gate("A6_no_retraining", a6s.get("model_training_executed") is False)
        gate("A6_no_reselection", a6s.get("checkpoint_reselection_executed") is False)
        gate("A6_no_retuning", a6s.get("retuning_executed") is False)
        gate("A6_no_normalization_refit", a6s.get("normalization_refit_executed") is False)
        gate("A6_AV4_state_unmutated", a6s.get("AV4_state_mutated") is False)
        gate("A6_no_physical_time_advance", a6s.get("physical_time_advance_executed") is False)
        gate("A6_production_not_authorized", a6s.get("AV5_production_execution_authorized") is False)
        gate("A6_P3_not_authorized", a6s.get("P3_authorized") is False)
        gate("A6_next_execution_not_authorized", a6c.get("next_execution_authorized") is False)
        gate(
            "A6_next_step_is_interpret_and_freeze",
            a6c.get("next_step") == "interpret and freeze AV5 scientific outcome before any production/P3 authorization decision",
            a6c.get("next_step"),
        )

        stage = "scientific_pattern_audit"
        gate("A6_outcome_one_touch_no_adaptation", a6o.get("one_touch_no_adaptation") is True)
        gate("A6_outcome_exact_pressure_equivalence", a6o.get("all_corrected_pressures_exact_equivalent_to_direct") is True)
        gate("A6_outcome_one_improved_state", int(a6o.get("states_with_selected_iteration_improvement")) == 1)
        gate(
            "A6_outcome_median_unchanged",
            float(a6o.get("selected_minus_temporal_median_iterations")) == 0.0,
            a6o.get("selected_minus_temporal_median_iterations"),
        )
        gate(
            "A6_outcome_mean_improved",
            float(a6o.get("selected_minus_temporal_mean_iterations")) < 0.0,
            a6o.get("selected_minus_temporal_mean_iterations"),
        )
        gate("A6_state_audit_9_rows", len(rows) == 9, len(rows))
        days = [float(r["target_day"]) for r in rows]
        gate("A6_state_audit_days_exact", days == CANONICAL_DAYS, days)
        admitted = [r for r in rows if as_bool(r["learned_seed_admitted"])]
        gate("A6_exactly_one_admitted_row", len(admitted) == 1, len(admitted))
        gate("A6_admitted_state_is_Day30", len(admitted) == 1 and float(admitted[0]["target_day"]) == 30.0)
        gate(
            "A6_Day30_iteration_improvement_exact",
            len(admitted) == 1
            and int(float(admitted[0]["selected_correction_iterations"])) == 450
            and int(float(admitted[0]["temporal_baseline_correction_iterations"])) == 467,
            admitted[0] if admitted else None,
        )
        later = [r for r in rows if float(r["target_day"]) > 30.0]
        gate("A6_Day60plus_all_temporal_selected", all(r["selected_seed"] == "TEMPORAL" for r in later))
        gate(
            "A6_Day60plus_selected_iterations_equal_temporal",
            all(
                int(float(r["selected_correction_iterations"]))
                == int(float(r["temporal_baseline_correction_iterations"]))
                for r in later
            ),
        )

        stage = "scientific_interpretation_freeze"
        interpretation = {
            "milestone": M,
            "status": PASS,
            "source_A6_classification": A6_CLASSIFICATION,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "scientific_findings": {
                "exactness_and_safety_generalized_to_locked_OOD": True,
                "all_corrected_pressures_exact_equivalent_to_direct": True,
                "direct_fallbacks_required": 0,
                "learned_seed_generalization_observed": True,
                "learned_seed_admission_was_sparse": True,
                "learned_seed_admitted_states": 1,
                "locked_OOD_states": 9,
                "only_observed_iteration_improvement_day": 30.0,
                "Day30_selected_iterations": 450,
                "Day30_temporal_iterations": 467,
                "Day60_plus_temporal_seed_dominated": True,
                "selected_median_iterations": float(a6o["selected_correction_median_iterations"]),
                "temporal_median_iterations": float(a6o["temporal_baseline_median_iterations"]),
                "median_iteration_change": float(a6o["selected_minus_temporal_median_iterations"]),
                "selected_mean_iterations": float(a6o["selected_correction_mean_iterations"]),
                "temporal_mean_iterations": float(a6o["temporal_baseline_mean_iterations"]),
                "mean_iteration_change": float(a6o["selected_minus_temporal_mean_iterations"]),
                "wall_clock_net_speedup_certified": False,
                "wall_clock_reason": (
                    "A6 certified exact-correction iteration behavior, not end-to-end learned-inference "
                    "plus correction wall-clock benefit."
                ),
            },
            "interpretation": (
                "The safeguarded learned pressure-seed mechanism is scientifically validated as exact and safe under "
                "locked-OOD one-touch use. Generalized acceleration exists, but it is sparse and concentrated at the "
                "Day30 cold-start transition. The recurrent temporal seed dominates Day60-Day1000. The present evidence "
                "does not certify production-level net runtime acceleration because end-to-end wall-clock economics "
                "were not frozen as an A6 criterion."
            ),
        }

        classification = (
            "AV5_SAFEGUARDED_LEARNED_PRESSURE_SEED_MECHANISM_VALIDATED_LOCKED_OOD_"
            "ACCELERATION_SPARSE_DAY30_FOCUSED_PRODUCTION_AND_P3_NOT_AUTHORIZED"
        )

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "AV5_scientific_outcome_frozen": True,
            "checkpoint_remains_frozen": True,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "existing_A5R1_checkpoint_retraining_authorized": False,
            "existing_A5R1_checkpoint_reselection_authorized": False,
            "existing_A5R1_checkpoint_retuning_authorized": False,
            "AV5_production_execution_authorized": False,
            "P3_authorized": False,
            "reason_production_not_authorized": (
                "locked-OOD safety/exactness passed and mean correction iterations improved, but median correction "
                "iterations were unchanged, only one of nine OOD states admitted/improved the learned seed, and "
                "end-to-end wall-clock speedup was not certified"
            ),
            "focused_follow_on_research_design_authorized": True,
            "focused_follow_on_execution_authorized": False,
            "next_design_milestone": "POSTV16-AV5-B1",
            "next_design_name": (
                "Day30 Cold-Start Specialization + End-to-End Wall-Clock Economics + "
                "Prospective Admission-Gated Learned-Seed Design Freeze"
            ),
            "AV4_state_mutation_authorized": False,
            "physical_time_advance_authorized": False,
        }

        next_research = {
            "milestone": "POSTV16-AV5-B1",
            "authorized_scope": "DESIGN_FREEZE_ONLY",
            "execution_authorized": False,
            "motivation": {
                "locked_OOD_improvement_concentrated_at_Day30": True,
                "Day60_plus_temporal_seed_dominated": True,
                "production_wall_clock_benefit_not_yet_certified": True,
            },
            "must_preserve": {
                "A5R1_checkpoint_as_frozen_reference": CHECKPOINT_SHA,
                "A4_TRAIN_only_normalization_as_reference": True,
                "exact_residual_seed_admission": True,
                "exact_FV_correction": True,
                "direct_spsolve_fallback_and_reference": True,
                "AV4_conservation_authority": True,
            },
            "design_questions": [
                "whether learned pressure seeding should be specialized to Day30/cold-start conditions rather than recurrent epochs",
                "whether model-inference overhead is smaller than the measured correction-solver savings end-to-end",
                "whether a prospective state-dependent admission policy can avoid unnecessary inference without using pressure truth",
                "whether broader training coverage is scientifically justified before any new checkpoint is trained",
            ],
            "must_not": [
                "retrain the frozen A5R1 checkpoint",
                "reselect the frozen A5R1 checkpoint",
                "retune using the already-opened locked-OOD result as if it were a validation set",
                "authorize production or P3 from A6 iteration-count evidence alone",
            ],
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "AV4_authoritative_state_sha256": AV4_STATE_SHA,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "A6_locked_OOD_outcome_bound": True,
            "exactness_safety_generalized": True,
            "OOD_acceleration_observed": True,
            "learned_seed_admitted_states": 1,
            "locked_OOD_states": 9,
            "only_improved_state_day": 30.0,
            "selected_minus_temporal_median_iterations": float(a6o["selected_minus_temporal_median_iterations"]),
            "selected_minus_temporal_mean_iterations": float(a6o["selected_minus_temporal_mean_iterations"]),
            "wall_clock_net_speedup_certified": False,
            "AV5_scientific_outcome_frozen": True,
            "AV5_production_execution_authorized": False,
            "P3_authorized": False,
            "POSTV16_AV5_B1_design_authorized": True,
            "POSTV16_AV5_B1_execution_authorized": False,
            "model_training_executed": False,
            "model_inference_executed": False,
            "checkpoint_reselection_executed": False,
            "retuning_executed": False,
            "normalization_refit_executed": False,
            "AV4_state_mutated": False,
            "physical_time_advance_executed": False,
        }

        output_files = {
            SUMMARY: jb(summary),
            INTERPRETATION: jb(interpretation),
            DECISION: jb(decision),
            NEXT_RESEARCH: jb(next_research),
            GATE_MATRIX: csvb(gates),
        }
        immutable_publish(out, output_files)
        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                manifest_rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        immutable_publish(out, {MANIFEST: csvb(manifest_rows)})

        print()
        print("=" * 204)
        print(M, "PASS")
        print("Classification                                  :", classification)
        print("Exactness / safety generalized                  : True")
        print("Learned seed admitted OOD states                : 1 / 9")
        print("Only improved OOD state                         : Day30 (450 vs 467 iterations)")
        print("Median correction iteration change              :", a6o["selected_minus_temporal_median_iterations"])
        print("Mean correction iteration change                :", a6o["selected_minus_temporal_mean_iterations"])
        print("End-to-end wall-clock speedup certified         : False")
        print("AV5 production execution authorized             : False")
        print("P3 authorized                                   : False")
        print("AV5-B1 focused design freeze authorized          : True")
        print("AV5-B1 execution authorized                     : False")
        print("=" * 204)
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
                "checkpoint_reselection_executed": False,
                "retuning_executed": False,
                "normalization_refit_executed": False,
                "AV4_state_mutation_executed": False,
                "physical_time_advance_executed": False,
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
