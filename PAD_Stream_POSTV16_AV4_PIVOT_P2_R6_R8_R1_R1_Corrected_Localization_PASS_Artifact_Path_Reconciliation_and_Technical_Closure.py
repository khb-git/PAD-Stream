#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

MILESTONE = "POSTV16-AV4-PIVOT-P2-R6-R8-R1-R1"
MILESTONE_NAME = (
    "Corrected Localization PASS Artifact Path Reconciliation "
    "and Technical Closure"
)

EXPECTED_BRANCH = "postv16-av4-pivot"
EXPECTED_PARENT = "fd42c008c15249ca6845b7de3f12c5cd85c5faf0"

R8R1_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_R1_"
    "Targetless_Component_Pool_Balance_KeyError_Technical_Closure_"
    "and_Corrected_Localization_Execution.py"
)
R8R1_RUNNER_SHA256 = "8d50926d98bb5bb2e0d3e3167edf597974d83e7e6f4d3009b751af1020839217"
R8R1_RUNNER_BLOB = "41cef11e8ba4c374d88ddf9eb99277eb331510c6"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R8_BLOCK = (
    BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R6_R8_BLOCKED" /
    "POSTV16_AV4_PIVOT_P2_R6_R8_Blocked_Report.json"
)
EXPECTED_R8_BLOCK_SHA256 = "be564a53aa6ef68ded5a9ed3816404acba36e9499a165f51d6c360825d896c1d"

R8R1_BLOCK = (
    BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R6_R8_R1_BLOCKED" /
    "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Blocked_Report.json"
)

SCI_REL = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Day375_Residual_FrozenDomain_"
    "Infeasibility_Localization_and_Minimal_SupportExtension_Design_Freeze"
)
SCI_SUM = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_R1_Summary.json"
SCI_DEC = "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Decision_Contract.json"
SCI_MAN = "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Artifact_Manifest.csv"
SCI_TIER = "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Tier_Exact_Feasibility_Audit.csv"
SCI_LOC = "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Failed_Group_Infeasibility_Localization.csv"
SCI_COMPACT = "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Frozen_Compact_Support_Extension.csv"
SCI_CONTRACT = "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Compact_Support_Design_Contract.json"

EXPECTED_SUMMARY_SHA256 = "a5e36bbf3602c955ab55dea622ead692bdfd9c8b7143fb02e26c023597234bb9"
EXPECTED_DECISION_SHA256 = "d1424a010666323d6a09f495f5065499e09314500c9a89005d11bf8f5d587e08"

SCI_STATUS = (
    "AV4PIVOTP2R6R8R1_DAY375_RESIDUAL_FROZEN_DOMAIN_INFEASIBILITY_"
    "LOCALIZATION_AND_MINIMAL_SUPPORT_EXTENSION_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
)
SCI_CLASS = (
    "R6R8_SINGLE_SHELL_SUPPORT_EXTENSION_INSUFFICIENT_RESIDUAL_GROUPS_"
    "REQUIRE_SECOND_STAGE_TOPOLOGY_DESIGN"
)
R6R9_NAME = "Day375 Residual Second-Stage Support-Extension Topology Design Freeze"

OUT_REL = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_"
    "Corrected_Localization_PASS_Artifact_Path_Reconciliation_"
    "and_Technical_Closure"
)
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_BLOCKED"

EXPECTED_FAILED_GROUP_COUNT = 21
EXPECTED_T1A = 1
EXPECTED_T1B = 13
EXPECTED_STILL_INFEASIBLE = 7
EXPECTED_DEFICIENT_CVS = 130
EXPECTED_CANDIDATE_MEMBERSHIPS = 2613
EXPECTED_COMPACT_MEMBERSHIPS = 2608


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_text(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return (p.stdout or "").strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def bool_csv(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    import io
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def self_test() -> None:
    assert EXPECTED_FAILED_GROUP_COUNT == EXPECTED_T1A + EXPECTED_T1B + EXPECTED_STILL_INFEASIBLE
    assert EXPECTED_STILL_INFEASIBLE == 7
    assert SCI_STATUS.endswith("PASS_NO_STATE_MUTATION")
    assert R6R9_NAME.startswith("Day375 Residual Second-Stage")
    print("POSTV16 AV4 PIVOT P2-R6-R8-R1-R1 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    block = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, passed: Any, detail: Any = None) -> None:
        ok = bool(passed)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" +
              ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    print("=" * 212)
    print(
        "POSTV16-AV4-PIVOT-P2-R6-R8-R1-R1 -- CORRECTED LOCALIZATION "
        "PASS ARTIFACT PATH RECONCILIATION + TECHNICAL CLOSURE"
    )
    print("=" * 212)
    print("READ-ONLY CLOSURE. NO LP EXECUTION. NO DAY375 STATE MUTATION.")
    print("BINDS THE ALREADY-PERSISTED R8-R1 SCIENTIFIC PASS AND BOTH BLOCK HISTORIES.")
    print()

    try:
        stage = "formal_outcome_firewall"
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_Blocked_Report.json"
        if summary_path.is_file():
            print("[PASS] formal R6-R8-R1-R1 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R8R1R1_BLOCK", not block_path.exists(), str(block_path))

        stage = "repository_authority"
        gate("branch_exact", git_text(root, "branch", "--show-current") == EXPECTED_BRANCH)
        parent = git_text(root, "rev-parse", "HEAD^")
        gate("parent_is_blocked_R6R8R1_commit", parent == EXPECTED_PARENT, parent)
        status = git_text(root, "status", "--porcelain")
        gate("repository_clean", status == "", repr(status))
        r8r1_runner = root / R8R1_RUNNER
        gate("R8R1_runner_present", r8r1_runner.is_file(), str(r8r1_runner))
        gate("R8R1_runner_SHA_exact",
             sha256_file(r8r1_runner) == R8R1_RUNNER_SHA256,
             sha256_file(r8r1_runner))
        blob = git_text(root, "hash-object", str(r8r1_runner))
        gate("R8R1_runner_blob_exact", blob == R8R1_RUNNER_BLOB, blob)

        stage = "block_history_binding"
        r8_block_path = drive / R8_BLOCK
        r8r1_block_path = drive / R8R1_BLOCK
        gate("R8_authoritative_BLOCK_present", r8_block_path.is_file(), str(r8_block_path))
        gate("R8_authoritative_BLOCK_SHA_exact",
             sha256_file(r8_block_path) == EXPECTED_R8_BLOCK_SHA256,
             sha256_file(r8_block_path))
        gate("R8R1_authoritative_BLOCK_present", r8r1_block_path.is_file(), str(r8r1_block_path))

        r8r1_block = json.loads(r8r1_block_path.read_text(encoding="utf-8"))
        gate("R8R1_BLOCK_status_exact",
             r8r1_block.get("status") == "R6R8R1_TECHNICAL_CLOSURE_BLOCK",
             r8r1_block.get("status"))
        gate("R8R1_BLOCK_stage_exact",
             r8r1_block.get("failed_stage") == "corrected_localization_execution",
             r8r1_block.get("failed_stage"))
        gate("R8R1_BLOCK_exception_exact",
             r8r1_block.get("exception") == "GateError('R8R1_summary_present')",
             r8r1_block.get("exception"))
        gate("R8R1_BLOCK_no_state_mutation",
             r8r1_block.get("state_mutation_executed") is False)
        gate("R8R1_BLOCK_no_automatic_rerun",
             r8r1_block.get("automatic_rerun_authorized") is False)

        bm = {
            str(r.get("gate")): r
            for r in r8r1_block.get("gates_completed", [])
            if isinstance(r, dict) and r.get("gate") is not None
        }
        gate("corrected_runner_exit_gate_present",
             "corrected_R8R1_runner_exit_zero" in bm)
        gate("corrected_runner_exit_gate_PASS",
             bm["corrected_R8R1_runner_exit_zero"].get("pass") is True,
             bm["corrected_R8R1_runner_exit_zero"].get("detail"))
        gate("original_R8_BLOCK_preserved_gate_PASS",
             bm.get("authoritative_R8_BLOCK_preserved_byte_exact", {}).get("pass") is True,
             bm.get("authoritative_R8_BLOCK_preserved_byte_exact", {}).get("detail"))

        stage = "scientific_PASS_binding"
        sci = drive / SCI_REL
        required = [
            SCI_SUM, SCI_DEC, SCI_MAN, SCI_TIER, SCI_LOC, SCI_COMPACT, SCI_CONTRACT,
            "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Localized_Deficient_CVs.csv",
            "POSTV16_AV4_PIVOT_P2_R6_R8_R1_SingleShell_Candidate_Terminal_Sinks.csv",
            "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Final_Gate_Matrix.csv",
        ]
        for name in required:
            gate(f"scientific_{name}_present", (sci / name).is_file(), str(sci / name))

        sum_path = sci / SCI_SUM
        dec_path = sci / SCI_DEC
        gate("scientific_summary_SHA_exact",
             sha256_file(sum_path) == EXPECTED_SUMMARY_SHA256,
             sha256_file(sum_path))
        gate("scientific_decision_SHA_exact",
             sha256_file(dec_path) == EXPECTED_DECISION_SHA256,
             sha256_file(dec_path))

        summary = json.loads(sum_path.read_text(encoding="utf-8"))
        decision = json.loads(dec_path.read_text(encoding="utf-8"))

        gate("scientific_status_exact", summary.get("status") == SCI_STATUS, summary.get("status"))
        gate("scientific_classification_exact", summary.get("classification") == SCI_CLASS,
             summary.get("classification"))
        gate("scientific_21_failed_groups",
             int(summary.get("R6R7_failed_group_count_localized", -1)) == EXPECTED_FAILED_GROUP_COUNT,
             summary.get("R6R7_failed_group_count_localized"))
        gate("scientific_T0_reproduced_21",
             int(summary.get("T0_failed_groups_reproduced", -1)) == EXPECTED_FAILED_GROUP_COUNT,
             summary.get("T0_failed_groups_reproduced"))
        gate("scientific_T1A_exact",
             int(summary.get("T1A_connectivity_only_feasible_group_count", -1)) == EXPECTED_T1A,
             summary.get("T1A_connectivity_only_feasible_group_count"))
        gate("scientific_T1B_exact",
             int(summary.get("T1B_single_shell_new_endpoint_feasible_group_count", -1)) == EXPECTED_T1B,
             summary.get("T1B_single_shell_new_endpoint_feasible_group_count"))
        gate("scientific_still_infeasible_exact",
             int(summary.get("single_shell_still_infeasible_group_count", -1)) == EXPECTED_STILL_INFEASIBLE,
             summary.get("single_shell_still_infeasible_group_count"))
        gate("scientific_all_resolved_false",
             summary.get("all_21_failed_groups_resolved_by_single_shell") is False)
        gate("scientific_deficient_CV_count_exact",
             int(summary.get("localized_deficient_CV_count", -1)) == EXPECTED_DEFICIENT_CVS,
             summary.get("localized_deficient_CV_count"))
        gate("scientific_candidate_memberships_exact",
             int(summary.get("candidate_terminal_sink_membership_count", -1)) == EXPECTED_CANDIDATE_MEMBERSHIPS,
             summary.get("candidate_terminal_sink_membership_count"))
        gate("scientific_compact_memberships_exact",
             int(summary.get("frozen_compact_support_membership_count", -1)) == EXPECTED_COMPACT_MEMBERSHIPS,
             summary.get("frozen_compact_support_membership_count"))
        gate("scientific_R5_fixed", summary.get("R5_local_repair_held_fixed") is True)
        gate("scientific_no_state_mutation", summary.get("state_mutation_executed") is False)
        gate("scientific_no_pressure_refresh", summary.get("pressure_refresh_executed") is False)
        gate("scientific_no_time_advance", summary.get("time_advance_executed") is False)
        gate("scientific_P3_false", summary.get("P3_authorized") is False)

        gate("decision_status_exact", decision.get("status") == SCI_STATUS, decision.get("status"))
        gate("decision_class_exact", decision.get("classification") == SCI_CLASS,
             decision.get("classification"))
        gate("decision_R6R9_authorized", decision.get("P2_R6_R9_authorized") is True)
        gate("decision_R6R9_name_exact", decision.get("P2_R6_R9_name") == R6R9_NAME,
             decision.get("P2_R6_R9_name"))
        gate("decision_projection_execution_false",
             decision.get("P2_R6_R9_projection_execution_authorized") is False)
        gate("decision_second_stage_design_true",
             decision.get("P2_R6_R9_second_stage_topology_design_authorized") is True)
        gate("decision_restart_false",
             decision.get("P2_continuation_restart_authorized_now") is False)
        gate("decision_accepted_state_false",
             decision.get("accepted_Day375_state_authorized_now") is False)
        gate("decision_support_growth_execution_false",
             decision.get("support_growth_execution_authorized_now") is False)
        gate("decision_new_H2_execution_false",
             decision.get("new_H2_endpoint_execution_authorized_now") is False)
        gate("decision_pressure_false", decision.get("pressure_refresh_authorized") is False)
        gate("decision_time_false", decision.get("time_advance_authorized") is False)
        gate("decision_P3_false", decision.get("P3_authorized") is False)
        gate("decision_P4_false", decision.get("P4_authorized") is False)
        gate("decision_P5_false", decision.get("P5_training_authorized") is False)

        stage = "scientific_manifest_integrity"
        man_rows = read_csv(sci / SCI_MAN)
        manifest = {r["file"]: r for r in man_rows}
        # The source R8-R1 manifest intentionally enumerates every artifact that
        # existed when it was generated; verify every listed file byte-for-byte.
        for name, row in sorted(manifest.items()):
            fp = sci / name
            gate(f"manifest_file_present::{name}", fp.is_file(), str(fp))
            gate(f"manifest_SHA_exact::{name}",
                 sha256_file(fp) == row["sha256"], sha256_file(fp))
            gate(f"manifest_bytes_exact::{name}",
                 fp.stat().st_size == int(row["bytes"]), fp.stat().st_size)

        stage = "unresolved_group_localization"
        tier_rows = read_csv(sci / SCI_TIER)
        loc_rows = read_csv(sci / SCI_LOC)
        loc_by_gid = {int(r["execution_group_id"]): r for r in loc_rows}
        unresolved: list[dict[str, Any]] = []
        t1b_rows = [
            r for r in tier_rows
            if r.get("tier") == "T1B_SINGLE_NONRECURSIVE_FACE_SHELL"
        ]
        for row in t1b_rows:
            gid = int(row["execution_group_id"])
            if not bool_csv(row["exact_feasible"]):
                lr = loc_by_gid[gid]
                unresolved.append({
                    "execution_group_id": gid,
                    "R6R6_component_ids": lr["R6R6_component_ids"],
                    "component_count": int(lr["component_count"]),
                    "CV_count": int(lr["CV_count"]),
                    "R6R7_target_CV_count": int(lr["R6R7_target_CV_count"]),
                    "localized_deficient_CV_count": int(lr["localized_deficient_CV_count"]),
                    "localized_deficient_component_count": int(lr["localized_deficient_component_count"]),
                    "localized_deficient_component_ids": lr["localized_deficient_component_ids"],
                    "minimum_L1_total_absolute_conservation_slack_kg": float(
                        lr["minimum_L1_total_absolute_conservation_slack_kg"]
                    ),
                    "minimum_L1_max_absolute_conservation_slack_kg": float(
                        lr["minimum_L1_max_absolute_conservation_slack_kg"]
                    ),
                    "T1A_candidate_cell_count": int(lr["T1A_candidate_cell_count"]),
                    "T1B_candidate_cell_count": int(lr["T1B_candidate_cell_count"]),
                    "T1B_new_endpoint_cell_count": int(lr["T1B_new_endpoint_cell_count"]),
                    "chosen_support_class": lr["chosen_support_class"],
                    "R6R9_second_stage_topology_design_required": True,
                })
        unresolved.sort(key=lambda r: r["execution_group_id"])
        gate("exactly_seven_unresolved_groups",
             len(unresolved) == EXPECTED_STILL_INFEASIBLE,
             [r["execution_group_id"] for r in unresolved])
        gate("all_unresolved_classes_T1B_insufficient",
             all(r["chosen_support_class"] == "T1B_SINGLE_SHELL_INSUFFICIENT"
                 for r in unresolved))

        stage = "closure_publication"
        out.mkdir(parents=True, exist_ok=False)

        unresolved_path = out / (
            "POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_"
            "Seven_Unresolved_Groups_for_R6_R9.csv"
        )
        unresolved_path.write_bytes(csv_bytes(unresolved))

        r8r1_block_sha = sha256_file(r8r1_block_path)
        closure = {
            "milestone": MILESTONE,
            "name": MILESTONE_NAME,
            "status": "AV4PIVOTP2R6R8R1R1_CORRECTED_LOCALIZATION_PASS_ARTIFACT_PATH_RECONCILIATION_TECHNICAL_CLOSURE_PASS",
            "classification": SCI_CLASS,
            "read_only_closure": True,
            "scientific_LP_reexecuted": False,
            "state_mutation_executed": False,
            "scientific_authority": {
                "R8R1_parent_commit": EXPECTED_PARENT,
                "R8R1_runner_sha256": R8R1_RUNNER_SHA256,
                "R8R1_runner_blob": R8R1_RUNNER_BLOB,
                "scientific_output_directory": str(SCI_REL),
                "scientific_summary_sha256": EXPECTED_SUMMARY_SHA256,
                "scientific_decision_sha256": EXPECTED_DECISION_SHA256,
                "scientific_status": SCI_STATUS,
                "scientific_classification": SCI_CLASS,
            },
            "block_history": {
                "R8_block_sha256": EXPECTED_R8_BLOCK_SHA256,
                "R8R1_block_sha256": r8r1_block_sha,
                "R8R1_block_failed_stage": "corrected_localization_execution",
                "R8R1_block_exception": "GateError('R8R1_summary_present')",
                "corrected_R8R1_scientific_runner_exit_zero": True,
                "block_cause": (
                    "Post-execution wrapper searched for the PASS summary under "
                    "the technical-closure directory, while the corrected R8 source "
                    "persisted the PASS under the R8-R1 scientific output directory."
                ),
            },
            "scientific_result": {
                "R6R7_failed_groups_localized": EXPECTED_FAILED_GROUP_COUNT,
                "T1A_connectivity_only_feasible_groups": EXPECTED_T1A,
                "T1B_single_shell_new_endpoint_feasible_groups": EXPECTED_T1B,
                "still_infeasible_after_single_shell": EXPECTED_STILL_INFEASIBLE,
                "localized_deficient_CVs": EXPECTED_DEFICIENT_CVS,
                "candidate_terminal_sink_memberships": EXPECTED_CANDIDATE_MEMBERSHIPS,
                "frozen_compact_support_memberships": EXPECTED_COMPACT_MEMBERSHIPS,
                "unresolved_execution_group_ids": [
                    r["execution_group_id"] for r in unresolved
                ],
            },
            "R6R9_authority": {
                "authorized": True,
                "name": R6R9_NAME,
                "projection_execution_authorized": False,
                "second_stage_topology_design_authorized": True,
                "must_bind_R8R1_compact_support_contract": True,
                "must_bind_seven_unresolved_groups_manifest": True,
                "support_growth_execution_authorized_now": False,
                "new_H2_endpoint_execution_authorized_now": False,
                "pressure_refresh_authorized": False,
                "time_advance_authorized": False,
                "P3_authorized": False,
                "P4_authorized": False,
                "P5_training_authorized": False,
            },
        }
        closure_path = out / (
            "POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_Technical_Closure_Contract.json"
        )
        closure_path.write_bytes(json_bytes(closure))

        summary_out = {
            "milestone": MILESTONE,
            "name": MILESTONE_NAME,
            "status": closure["status"],
            "classification": SCI_CLASS,
            "read_only_closure": True,
            "scientific_LP_reexecuted": False,
            "state_mutation_executed": False,
            "R8R1_scientific_PASS_bound": True,
            "R8R1_scientific_summary_sha256": EXPECTED_SUMMARY_SHA256,
            "R8R1_scientific_decision_sha256": EXPECTED_DECISION_SHA256,
            "R8R1_BLOCK_preserved": True,
            "R6R7_failed_group_count_localized": EXPECTED_FAILED_GROUP_COUNT,
            "T1A_connectivity_only_feasible_group_count": EXPECTED_T1A,
            "T1B_single_shell_new_endpoint_feasible_group_count": EXPECTED_T1B,
            "single_shell_still_infeasible_group_count": EXPECTED_STILL_INFEASIBLE,
            "unresolved_execution_group_ids": [
                r["execution_group_id"] for r in unresolved
            ],
            "R6R9_authorized": True,
            "R6R9_name": R6R9_NAME,
            "R6R9_projection_execution_authorized": False,
            "R6R9_second_stage_topology_design_authorized": True,
            "pressure_refresh_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }
        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_Summary.json").write_bytes(
            json_bytes(summary_out)
        )

        decision_out = {
            "milestone": MILESTONE,
            "status": closure["status"],
            "classification": SCI_CLASS,
            "P2_R6_R9_authorized": True,
            "P2_R6_R9_name": R6R9_NAME,
            "P2_R6_R9_projection_execution_authorized": False,
            "P2_R6_R9_second_stage_topology_design_authorized": True,
            "P2_R6_R9_must_bind_R6R8R1_scientific_PASS": True,
            "P2_R6_R9_must_bind_R6R8R1_compact_support_contract": True,
            "P2_R6_R9_must_bind_seven_unresolved_groups_manifest": True,
            "P2_continuation_restart_authorized_now": False,
            "accepted_Day375_state_authorized_now": False,
            "support_growth_execution_authorized_now": False,
            "new_H2_endpoint_execution_authorized_now": False,
            "pressure_refresh_authorized": False,
            "Darcy_Pollock_TOF_regeneration_authorized": False,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }
        (out / "POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_Decision_Contract.json").write_bytes(
            json_bytes(decision_out)
        )

        (out / "POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_Final_Gate_Matrix.csv").write_bytes(
            csv_bytes(gates)
        )

        manifest_rows: list[dict[str, Any]] = []
        for fp in sorted(out.iterdir()):
            if fp.is_file():
                manifest_rows.append({
                    "file": fp.name,
                    "sha256": sha256_file(fp),
                    "bytes": fp.stat().st_size,
                })
        (out / "POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_Artifact_Manifest.csv").write_bytes(
            csv_bytes(manifest_rows)
        )

        print()
        print("=" * 212)
        print("POSTV16-AV4-PIVOT-P2-R6-R8-R1-R1: PASS")
        print("R8-R1 scientific PASS bound                 : True")
        print("Scientific LP re-executed                   : False")
        print("T1A feasible groups                         :", EXPECTED_T1A)
        print("T1B feasible groups                         :", EXPECTED_T1B)
        print("Still infeasible after single shell         :", EXPECTED_STILL_INFEASIBLE)
        print("Unresolved group IDs                        :", [r["execution_group_id"] for r in unresolved])
        print("R6-R9 projection execution authorized       : False")
        print("R6-R9 second-stage topology design          : True")
        print("Day375 state mutation                       : False")
        print("P3 authorized                               : False")
        print("=" * 212)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        rp = block / "POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_Blocked_Report.json"
        if not rp.exists():
            rp.write_text(
                json.dumps({
                    "milestone": MILESTONE,
                    "status": "R6R8R1R1_TECHNICAL_CLOSURE_BLOCK",
                    "failed_stage": stage,
                    "exception": repr(exc),
                    "state_mutation_executed": False,
                    "scientific_LP_reexecuted": False,
                    "automatic_rerun_authorized": False,
                    "pressure_refresh_authorized": False,
                    "time_advance_authorized": False,
                    "P3_authorized": False,
                    "gates_completed": gates,
                }, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(MILESTONE + ": BLOCKED")
        print("Stage:", stage)
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
    a = parse_args()
    if a.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root, a.drive_root))
