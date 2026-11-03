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

M = "POSTV16-AV4-PIVOT-P2-R6-R33"
NAME = "Deferred Refresh-Cadence Reactivation + Corrected P3 Protocol Design Freeze"
PASS = (
    "AV4PIVOTP2R6R33_DEFERRED_REFRESH_CADENCE_REACTIVATION_CORRECTED_P3_PROTOCOL_"
    "DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"
)
BLOCK = "AV4PIVOTP2R6R33_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "520bde65c4ba6afbd90561ac125c71482bdf5f30"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV5 = Path("post_v16") / RID / "POSTV16_AV5_Learned_Acceleration"

AV4_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"

SOURCE_BLOBS = {
    "PAD_Stream_POSTV16_AV4_PIVOT_P0_Pressure_Refresh_Cadence_Diagnostic_Design_Freeze.py":
        "74342f6e770803acf66deeff80c62400fd8aa96f",
    "PAD_Stream_POSTV16_AV4_PIVOT_P1_Existing_Snapshot_Staleness_Pilot.py":
        "156b545aef63d5bdb97d46b6d164fcfab0a00e6a",
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_Dense_5Day_FrozenFlow_Snapshot_Generation.py":
        "b01da68bd7a568198fa1b409bdc8e3d27789c42e",
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R32_Independent_Recurrent_Operation_Closure_Audit.py":
        "435f5d6dcba38de7166e41ba9e081b6ef573edcf",
    "PAD_Stream_POSTV16_AV5_B3_Validation_WallClock_Economics_Outcome_Interpretation_and_AV5_LearnedAcceleration_Closure_Decision_Freeze.py":
        "693f95c53db9c8e5705a62b0feb0baa3571d92d2",
    "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py":
        "79a8969233b72b4543edd382a0c3d1028c6dca09",
}

# P0 original cadence-study authority.
P0_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P0_Pressure_Refresh_Cadence_Diagnostic_Design_Freeze"
P0_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P0_Summary.json"
P0_ARCH = "POSTV16_AV4_PIVOT_P0_Diagnostic_Architecture.json"
P0_METRICS = "POSTV16_AV4_PIVOT_P0_Observable_Metric_Contract.json"
P0_DECISION = "POSTV16_AV4_PIVOT_P0_Decision_Contract.json"
P0_MANIFEST = "POSTV16_AV4_PIVOT_P0_Artifact_Manifest.csv"
P0_STATUS = (
    "AV4PIVOTP0_PARALLEL_PRESSURE_REFRESH_CADENCE_DIAGNOSTIC_DESIGN_FREEZE_PASS_"
    "EXACT_CERTIFICATION_BRANCH_UNCHANGED_NO_PHYSICAL_TIME_ADVANCE_NO_TRAINING"
)

# P1 staleness pilot authority.
P1_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P1_Existing_Snapshot_Staleness_Pilot"
P1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P1_Summary.json"
P1_DECISION = "POSTV16_AV4_PIVOT_P1_Decision_Contract.json"
P1_MANIFEST = "POSTV16_AV4_PIVOT_P1_Artifact_Manifest.csv"
P1_STATUS = (
    "AV4PIVOTP1_EXISTING_SNAPSHOT_PRESSURE_DARCY_POLLOCK_TOF_STALENESS_PILOT_PASS_"
    "DAY365_REFERENCE_DAY500_DAY750_DAY1000_DIAGNOSTICS_AND_3D_VISUALS_PUBLISHED"
)

# Original P2 formal outcome locations. R33 does NOT promote any recovery checkpoint.
P2_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_Dense_5Day_FrozenFlow_Snapshot_Generation"
P2_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_Summary.json"
P2_FAIL_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_SCIENTIFIC_FAIL"
P2_FAIL = "POSTV16_AV4_PIVOT_P2_Scientific_Fail_Report.json"
P2_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_BLOCKED"
P2_BLOCK = "POSTV16_AV4_PIVOT_P2_Blocked_Report.json"
P2_RECOVERY_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_Recovery_Checkpoints"

# R32 repaired recurrent-physics closure authority.
R32_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R32"
R32_REL = BASE_AV4 / (R32_TOKEN + "_Independent_Recurrent_Operation_Closure_Audit")
R32_SUMMARY = f"PAD_Stream_{R32_TOKEN}_Summary.json"
R32_DECISION = f"{R32_TOKEN}_Decision_Contract.json"
R32_MANIFEST = f"{R32_TOKEN}_Artifact_Manifest.csv"
R32_STATUS = (
    "AV4PIVOTP2R6R32_INDEPENDENT_RECURRENT_OPERATION_CLOSURE_AUDIT_"
    "PASS_AV4_RECURRENT_PHYSICS_CLOSED_NO_R31_TIME_COMMIT"
)

# Accepted Day365 refresh operator remains original start authority.
A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

# AV5 closed experiment authority; cadence work resumes only after its closure.
B3_REL = BASE_AV5 / (
    "POSTV16_AV5_B3_Validation_WallClock_Economics_Outcome_Interpretation_and_"
    "AV5_LearnedAcceleration_Closure_Decision_Freeze"
)
B3_SUMMARY = "PAD_Stream_POSTV16_AV5_B3_Summary.json"
B3_DECISION = "POSTV16_AV5_B3_Decision_Contract.json"
B3_MANIFEST = "POSTV16_AV5_B3_Artifact_Manifest.csv"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R33"
OUT_REL = BASE_AV4 / (
    OUT_TOKEN + "_Deferred_Cadence_Reactivation_and_Corrected_P3_Protocol_Design_Freeze"
)
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")

SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
RECON = f"{OUT_TOKEN}_Cadence_Lineage_Reconciliation.json"
P3_PROTOCOL = f"{OUT_TOKEN}_Corrected_P3_Protocol_Freeze.json"
P3_HANDOFF = f"{OUT_TOKEN}_P3_R0_Handoff_Contract.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

WINDOW = [365.0, 500.0]
SPACING = 5.0
CANDIDATE_CADENCES = [50.0, 5.0]
POLICIES = ["frozen flow", "50-day refresh", "5-day refresh"]
DENSE_DAYS = [float(x) for x in range(365, 501, 5)]


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
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> dict[str, str]:
    result = {}
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
    out.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        (out / name).write_bytes(data)


def selftest() -> None:
    assert WINDOW == [365.0, 500.0]
    assert SPACING == 5.0
    assert CANDIDATE_CADENCES == [50.0, 5.0]
    assert POLICIES == ["frozen flow", "50-day refresh", "5-day refresh"]
    assert len(DENSE_DAYS) == 28 and DENSE_DAYS[0] == 365.0 and DENSE_DAYS[-1] == 500.0
    assert len(PARENT) == 40
    print("POSTV16 AV4 PIVOT P2-R6-R33 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gate_rows: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gate_rows.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    try:
        print("=" * 210)
        print("POSTV16-AV4-PIVOT-P2-R6-R33 — DEFERRED CADENCE REACTIVATION / CORRECTED P3 PROTOCOL DESIGN FREEZE")
        print("=" * 210)
        print("READ-ONLY REACTIVATION MILESTONE.")
        print("NO PRESSURE SOLVE. NO TRANSPORT. NO MAPBACK. NO MODEL EXECUTION. NO PHYSICAL TIME ADVANCE.")
        print("ORIGINAL P0 CADENCE QUESTION IS PRESERVED: FROZEN vs 50-DAY vs 5-DAY, DAY365->500.")
        print("OLD P2 RECOVERY CHECKPOINTS ARE HISTORICAL EVIDENCE ONLY — NOT ACCEPTED P3 STATE AUTHORITY.")
        print()

        stage = "preexisting_state_firewall"
        gate("no_preexisting_R33_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_R33_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        branch = gt(root, "branch", "--show-current")
        parent = gt(root, "rev-parse", "HEAD^")
        dirty = gt(root, "status", "--porcelain")
        gate("branch_exact", branch == BRANCH, branch)
        gate("parent_exact", parent == PARENT, parent)
        gate("repository_clean", dirty == "", repr(dirty))
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        # Original P3/P4/P5 were designed in P0 but never implemented.
        gate("repository_has_no_P3_runner",
             len(list(root.glob("PAD_Stream_POSTV16_AV4_PIVOT_P3*.py"))) == 0)
        gate("repository_has_no_P4_runner",
             len(list(root.glob("PAD_Stream_POSTV16_AV4_PIVOT_P4*.py"))) == 0)
        gate("repository_has_no_P5_runner",
             len(list(root.glob("PAD_Stream_POSTV16_AV4_PIVOT_P5*.py"))) == 0)

        stage = "P0_original_contract_authority"
        p0d = drive / P0_REL
        p0m = manifest(p0d, P0_MANIFEST)
        p0s = js(p0d / P0_SUMMARY)
        p0a = js(p0d / P0_ARCH)
        p0metrics = js(p0d / P0_METRICS)
        p0c = js(p0d / P0_DECISION)
        gate("P0_manifest_nonempty", len(p0m) > 0)
        gate("P0_status_exact", p0s.get("status") == P0_STATUS, p0s.get("status"))
        gate("P0_candidate_cadences_exact", p0c.get("candidate_cadences_days") == CANDIDATE_CADENCES,
             p0c.get("candidate_cadences_days"))
        gate("P0_no_cadence_preselected", p0c.get("periodic_cadence_selected_now") is False)
        gate("P0_P2_window_exact", p0a["phase_P2"]["window_days"] == WINDOW, p0a["phase_P2"]["window_days"])
        gate("P0_P2_spacing_exact",
             float(p0a["phase_P2"]["diagnostic_snapshot_spacing_days"]) == SPACING)
        gate("P0_P2_candidates_exact", p0a["phase_P2"]["cadence_policies_days"] == CANDIDATE_CADENCES)
        gate("P0_P3_pipeline_exact",
             p0a["phase_P3"]["pipeline"] ==
             ["S(t)", "spatial mobility", "pressure", "Darcy flux", "Pollock", "TOF"])
        gate("P0_P3_same_time", p0a["phase_P3"]["same_time"] is True)
        gate("P0_P3_no_transport_restart",
             p0a["phase_P3"]["transport_restart_from_refreshed_geometry"] is False)
        gate("P0_P4_policies_exact", p0a["phase_P4"]["policies"] == POLICIES, p0a["phase_P4"]["policies"])
        gate("P0_P4_no_preselection",
             p0a["phase_P4"]["selection_rule"] ==
             "accuracy-versus-cost evidence; no cadence preselected in P0")
        gate("P0_metrics_no_numeric_thresholds",
             p0metrics.get("P0_numeric_acceptance_thresholds") ==
             "NONE; P0 freezes observables, not an arbitrary production cadence.")

        stage = "P1_staleness_authority"
        p1d = drive / P1_REL
        p1m = manifest(p1d, P1_MANIFEST)
        p1s = js(p1d / P1_SUMMARY)
        p1c = js(p1d / P1_DECISION)
        gate("P1_manifest_nonempty", len(p1m) > 0)
        gate("P1_status_exact", p1s.get("status") == P1_STATUS, p1s.get("status"))
        gate("P1_P2_was_authorized", p1c.get("AV4_PIVOT_P2_authorized") is True)
        gate("P1_no_cadence_selected", p1c.get("periodic_cadence_selected_now") is False)

        stage = "original_P2_outcome_audit"
        p2_pass = (drive / P2_REL / P2_SUMMARY).is_file()
        p2_fail = (drive / P2_FAIL_REL / P2_FAIL).is_file()
        p2_block = (drive / P2_BLOCK_REL / P2_BLOCK).is_file()
        p2_recovery = drive / P2_RECOVERY_REL
        recovery_dirs = sorted([p.name for p in p2_recovery.glob("day_*") if p.is_dir()]) if p2_recovery.is_dir() else []
        gate("original_P2_formal_PASS_absent", p2_pass is False, p2_pass)
        gate("original_P2_recovery_not_promoted_to_PASS",
             not p2_pass and (p2_fail or p2_block or len(recovery_dirs) > 0),
             {"fail": p2_fail, "block": p2_block, "recovery_count": len(recovery_dirs)})

        stage = "R32_repaired_recurrent_physics_authority"
        r32d = drive / R32_REL
        r32m = manifest(r32d, R32_MANIFEST)
        r32s = js(r32d / R32_SUMMARY)
        r32c = js(r32d / R32_DECISION)
        gate("R32_manifest_nonempty", len(r32m) > 0)
        gate("R32_status_exact", r32s.get("status") == R32_STATUS, r32s.get("status"))
        gate("R32_AV4_recurrent_physics_closed", r32s.get("AV4_recurrent_physics_closed") is True)
        gate("R32_authoritative_state_SHA_exact", r32s.get("R30_committed_state_sha256") == AV4_STATE_SHA)
        gate("R32_full_cartesian_refresh_handoff_valid", r32s.get("full_cartesian_refresh_handoff_valid") is True)
        gate("R32_no_P3_authority_at_closure", r32c.get("P3_authorized") is False)
        gate("R32_no_automatic_physics_change", r32c.get("automatic_physics_change_authorized") is False)

        stage = "Day365_refresh_start_authority"
        a2ed = drive / A2E_REL
        a2es = js(a2ed / A2E_SUMMARY)
        gate("A2E_status_exact", a2es.get("status") == A2E_STATUS, a2es.get("status"))

        stage = "AV5_B3_closure_authority"
        b3d = drive / B3_REL
        b3m = manifest(b3d, B3_MANIFEST)
        b3s = js(b3d / B3_SUMMARY)
        b3c = js(b3d / B3_DECISION)
        gate("B3_manifest_nonempty", len(b3m) > 0)
        gate("B3_AV5_workstream_closed", b3s.get("AV5_learned_acceleration_workstream_closed") is True)
        gate("B3_pressure_checkpoint_research_only",
             b3s.get("checkpoint_disposition") == "RESEARCH_REFERENCE_ONLY_NOT_PRODUCTION_AUTHORIZED")
        gate("B3_next_execution_not_automatically_authorized", b3c.get("next_execution_authorized") is False)

        stage = "corrected_P3_protocol_freeze"
        reconciliation = {
            "milestone": M,
            "status": PASS,
            "ledger_obligation": "AV4 deferred Frozen Flow vs 50-day vs 5-day cadence closure",
            "historical_facts": {
                "P0_design_freeze_pass": True,
                "P1_staleness_pilot_pass": True,
                "original_P2_formal_pass": False,
                "original_P2_fail_report_present": p2_fail,
                "original_P2_block_report_present": p2_block,
                "original_P2_recovery_checkpoint_directory_count": len(recovery_dirs),
                "R32_recurrent_physics_closed": True,
                "AV5_pressure_acceleration_branch_closed": True,
                "P3_runner_previously_implemented": False,
                "P4_runner_previously_implemented": False,
            },
            "authority_rule": (
                "Old P2 recovery artifacts remain immutable historical evidence and may be inspected for diagnosis, "
                "but they are not accepted dense cadence-state authority. Corrected P3 must regenerate its common "
                "dense state basis prospectively under the R32-certified recurrent conservation/map-back semantics."
            ),
            "unchanged_scientific_question": {
                "window_days": WINDOW,
                "dense_snapshot_spacing_days": SPACING,
                "candidate_cadences_days": CANDIDATE_CADENCES,
                "policies": POLICIES,
                "cadence_preselected": False,
            },
        }

        corrected_p3 = {
            "milestone": "POSTV16-AV4-PIVOT-P3-R0",
            "name": "Corrected Dense Cadence Diagnostic Protocol Freeze",
            "status_at_R33": "AUTHORIZED_FOR_DESIGN_FREEZE_ONLY",
            "purpose": (
                "Prospectively define the corrected dense Day365->500 common-state generator and exact "
                "same-time flow diagnostic sweep required to resume the original P0 cadence study after "
                "the R32 recurrent-physics repair lineage."
            ),
            "unchanged_P0_contract": {
                "window_days": WINDOW,
                "observation_days": DENSE_DAYS,
                "observation_spacing_days": SPACING,
                "candidate_cadences_days": CANDIDATE_CADENCES,
                "policies": POLICIES,
                "diagnostic_pipeline": ["S(t)", "spatial mobility", "pressure", "Darcy flux", "Pollock", "TOF"],
                "same_time_diagnostics": True,
                "transport_restart_from_refreshed_geometry_during_diagnostic_sweep": False,
                "numeric_cadence_preselected": False,
            },
            "corrected_state_authority_requirements": {
                "Day365_flow_start_authority": "accepted A2E Day365 refreshed flow epoch",
                "transport_recurrence_semantics": "R32-certified full-Cartesian primary recurrent state / all-CV conservation / exact support and residual accounting",
                "common_dense_transport_history": (
                    "Prospectively regenerated from Day365 with the flow epoch frozen at Day365 for the common "
                    "diagnostic trajectory, using corrected recurrent transport/map-back semantics."
                ),
                "old_P2_recovery_checkpoints_as_accepted_state": False,
                "old_P2_recovery_checkpoints_may_be_read_for_diagnostic_provenance": True,
                "new_dense_state_outputs_must_be_manifested_and_restartable": True,
                "all_28_observation_states_required": True,
            },
            "P3_R0_must_freeze_before_execution": [
                "exact recurrent operator modules and Git blobs",
                "Day365 start-state arrays and SHA identities",
                "corrected support / projection / residual-sidecar semantics",
                "time-step and substep policy used to reach each 5-day observation state",
                "mass / capacity / saturation / restart acceptance gates",
                "exact flow-diagnostic observables inherited from P0",
                "artifact schema for all 28 dense states and all refreshed flow fields",
                "compute-time measurement boundaries",
            ],
            "forbidden_in_P3_R0": [
                "physics execution",
                "cadence selection",
                "ML training or inference",
                "reuse of AV5 pressure checkpoint as production authority",
                "promotion of old P2 recovery artifacts to PASS evidence",
                "change to Day365->500 study window",
                "change to 5-day dense observation spacing",
                "change to 50-day and 5-day candidate cadence set",
            ],
        }

        handoff = {
            "milestone": "POSTV16-AV4-PIVOT-P3-R0",
            "name": "Corrected Dense Cadence Diagnostic Protocol Freeze",
            "authorized": True,
            "execution": True,
            "design_freeze_only": True,
            "must_bind_R33_status": PASS,
            "must_bind_R32_authoritative_state_sha256": AV4_STATE_SHA,
            "must_preserve_original_P0_window_days": WINDOW,
            "must_preserve_original_P0_dense_spacing_days": SPACING,
            "must_preserve_original_P0_candidate_cadences_days": CANDIDATE_CADENCES,
            "must_preserve_original_P0_policy_set": POLICIES,
            "must_use_A2E_Day365_start_flow_authority": True,
            "must_use_R32_certified_recurrent_semantics": True,
            "old_P2_recovery_may_not_be_promoted_to_accepted_dense_state": True,
            "physics_execution_authorized_in_P3_R0": False,
            "P3_execution_authorized_now": False,
            "P4_cadence_comparison_authorized_now": False,
            "P5_ML_refresh_comparison_authorized_now": False,
        }

        classification = (
            "AV4_DEFERRED_CADENCE_STUDY_REACTIVATED_ORIGINAL_P0_SCIENCE_PRESERVED_"
            "OLD_P2_RECOVERY_NOT_PROMOTED_R32_RECURRENT_PHYSICS_BOUND_P3_R0_DESIGN_FREEZE_AUTHORIZED"
        )

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "AV4_deferred_cadence_obligation_reactivated": True,
            "original_P0_scientific_question_preserved": True,
            "original_P2_formal_pass": False,
            "old_P2_recovery_is_accepted_dense_state_authority": False,
            "R32_recurrent_physics_remains_authoritative": True,
            "R32_authoritative_state_sha256": AV4_STATE_SHA,
            "P3_R0_design_freeze_authorized": True,
            "P3_R0_execution_authorized": True,
            "P3_physics_execution_authorized": False,
            "P4_cadence_comparison_authorized": False,
            "P5_ML_refresh_comparison_authorized": False,
            "periodic_cadence_selected_now": False,
            "candidate_cadences_days": CANDIDATE_CADENCES,
            "policies": POLICIES,
            "AV5_pressure_checkpoint_promotion_authorized": False,
            "physical_time_advance_authorized": False,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "AV4_deferred_cadence_obligation_reactivated": True,
            "P0_design_bound": True,
            "P1_staleness_pilot_bound": True,
            "original_P2_formal_pass": False,
            "old_P2_recovery_checkpoint_directory_count": len(recovery_dirs),
            "old_P2_recovery_promoted_to_authority": False,
            "R32_recurrent_physics_closed": True,
            "R32_authoritative_state_sha256": AV4_STATE_SHA,
            "AV5_pressure_branch_closed": True,
            "study_start_day": WINDOW[0],
            "study_end_day": WINDOW[1],
            "dense_spacing_days": SPACING,
            "dense_observation_count": len(DENSE_DAYS),
            "candidate_cadences_days": CANDIDATE_CADENCES,
            "periodic_cadence_selected_now": False,
            "P3_R0_design_freeze_authorized": True,
            "P3_physics_execution_authorized": False,
            "P4_authorized": False,
            "P5_authorized": False,
            "physics_execution_executed": False,
            "model_execution_executed": False,
            "state_mutation_executed": False,
            "physical_time_advance_executed": False,
        }

        files = {
            SUMMARY: jb(summary),
            RECON: jb(reconciliation),
            P3_PROTOCOL: jb(corrected_p3),
            P3_HANDOFF: jb(handoff),
            DECISION: jb(decision),
            GATES: csvb(gate_rows),
        }
        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                manifest_rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / MANIFEST).write_bytes(csvb(manifest_rows))

        print()
        print("=" * 210)
        print(M, "PASS")
        print("Classification                                  :", classification)
        print("Original P0 window preserved                    : Day365 -> Day500")
        print("Dense observation spacing preserved             : 5 days")
        print("Candidate policies preserved                    : Frozen / 50-day / 5-day")
        print("Old P2 recovery promoted to accepted authority  : False")
        print("R32 recurrent physics bound                     : True")
        print("P3-R0 corrected protocol design freeze authorized: True")
        print("P3 physics execution authorized                 : False")
        print("P4 cadence comparison authorized                : False")
        print("Periodic cadence selected                       : False")
        print("=" * 210)
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
                "R32_authoritative_state_preserved": True,
                "old_P2_recovery_promoted_to_authority": False,
                "P3_physics_execution_authorized": False,
                "P4_cadence_comparison_authorized": False,
                "periodic_cadence_selected_now": False,
                "state_mutation_executed": False,
                "physical_time_advance_executed": False,
                "gates_completed": gate_rows,
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
