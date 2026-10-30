#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

MILESTONE = "POSTV16-AV4-PIVOT-P2-R6-R8-R1"
MILESTONE_NAME = (
    "Targetless-Component Pool-Balance KeyError Technical Closure "
    "and Corrected Localization Execution"
)

EXPECTED_BRANCH = "postv16-av4-pivot"
EXPECTED_PARENT = "dfb57399511875033467bd01a27c30b42a640b44"

ORIGINAL_R8_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_"
    "Day375_Residual_FrozenDomain_Infeasibility_Localization_"
    "and_Minimal_SupportExtension_Design_Freeze.py"
)
ORIGINAL_R8_SHA256 = "e7cd2e3376e6b2e869c541e055c08c3a4604e1786c820d57f1b21e27b356d6b1"
ORIGINAL_R8_BLOB = "3282d333a0232112eefe4ac58fe1059bb984f495"

ORIGINAL_R8_STATUS_BLOCKED = "AV4PIVOTP2R6R8_TECHNICAL_OR_AUTHORITY_BLOCK"
ORIGINAL_R8_EXPECTED_STAGE = "failed_group_localization"
ORIGINAL_R8_EXPECTED_EXCEPTION = "KeyError(0)"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = (
    Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
)
ORIGINAL_R8_BLOCK = (
    BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R6_R8_BLOCKED" /
    "POSTV16_AV4_PIVOT_P2_R6_R8_Blocked_Report.json"
)
ORIGINAL_R8_PASS = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R8_Day375_Residual_FrozenDomain_"
    "Infeasibility_Localization_and_Minimal_SupportExtension_Design_Freeze" /
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_Summary.json"
)
R7_REL = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R7_Day375_Residual_External_Component_"
    "Exact_Projection_Semantics_Freeze"
)
R7_TARGETS = "POSTV16_AV4_PIVOT_P2_R6_R7_Frozen_Target_CVs.csv"
R7_GROUPS = "POSTV16_AV4_PIVOT_P2_R6_R7_Prospective_Execution_Groups.csv"
R7_GROUP_FEAS = "POSTV16_AV4_PIVOT_P2_R6_R7_Group_Exact_Feasibility_Audit.csv"

R1_OUT = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R8_R1_"
    "Targetless_Component_Pool_Balance_KeyError_Technical_Closure_"
    "and_Corrected_Localization_Execution"
)
R1_BLOCK = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R6_R8_R1_BLOCKED"

EXPECTED_EDGE_COUNT = 74237983
EXPECTED_SINK_COUNT = 8226
EXPECTED_FAILED_GROUPS = [
    0, 3, 5, 10, 23, 28, 29, 31, 48, 55, 56,
    64, 65, 69, 73, 74, 76, 77, 79, 81, 83,
]

OLD_PREFIX = "POSTV16_AV4_PIVOT_P2_R6_R8"
NEW_PREFIX = "POSTV16_AV4_PIVOT_P2_R6_R8_R1"
OLD_HYPHEN = "POSTV16-AV4-PIVOT-P2-R6-R8"
NEW_HYPHEN = "POSTV16-AV4-PIVOT-P2-R6-R8-R1"

OLD_BUILD_LINE = (
    'bindiv=sorted(set(bindiv)); '
    'ykeys=[(cid,cv) for cid in group_cids for cv in targets[cid]]; '
    'qkeys=[(cid,c) for cid in group_cids for c in pools[cid]]; '
    'nx=len(pidx); nb=len(bindiv); ny=len(ykeys); nq=len(qkeys); ncv=len(cvs)'
)
NEW_BUILD_LINE = (
    'bindiv=sorted(set(bindiv)); '
    'pcids=[cid for cid in group_cids if targets[cid]]; '
    'ykeys=[(cid,cv) for cid in pcids for cv in targets[cid]]; '
    'qkeys=[(cid,c) for cid in pcids for c in pools[cid]]; '
    'nx=len(pidx); nb=len(bindiv); ny=len(ykeys); nq=len(qkeys); ncv=len(cvs)'
)

OLD_PROW_LINE = (
    'cvrow={int(cv):r for r,cv in enumerate(cvs.tolist())}; '
    'pcids=[cid for cid in group_cids if targets[cid]]; '
    'prow={cid:ncv+i for i,cid in enumerate(pcids)}; er=[]; ec=[]; ev=[]'
)
NEW_PROW_LINE = (
    'cvrow={int(cv):r for r,cv in enumerate(cvs.tolist())}; '
    'prow={cid:ncv+i for i,cid in enumerate(pcids)}; er=[]; ec=[]; ev=[]'
)

OLD_EXPECTED_PARENT = (
    'EXPECTED_PARENT="604e7a56627868a0cebd410e8da82f135d024f86"'
)
NEW_EXPECTED_PARENT = (
    'EXPECTED_PARENT="dfb57399511875033467bd01a27c30b42a640b44"'
)

OLD_MILESTONE_NAME = (
    'MILESTONE_NAME="Day375 Residual Frozen-Domain Infeasibility Localization '
    'and Minimal Support-Extension Design Freeze"'
)
NEW_MILESTONE_NAME = (
    'MILESTONE_NAME="Targetless-Component Pool-Balance KeyError Technical '
    'Closure and Corrected Localization Execution"'
)

OLD_R8_NAME = 'R8_NAME=MILESTONE_NAME'
NEW_R8_NAME = (
    'R8_NAME="Day375 Residual Frozen-Domain Infeasibility Localization and '
    'Minimal Support-Extension Design Freeze"'
)


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
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


def patch_exact(source: str) -> str:
    # Every replacement is count-checked. This is a surgical closure of the
    # blocked R8 source, not an independent rewrite of its scientific logic.
    replacements = [
        (OLD_BUILD_LINE, NEW_BUILD_LINE, "targetless_q_pool_fix"),
        (OLD_PROW_LINE, NEW_PROW_LINE, "single_pcids_definition"),
        (OLD_EXPECTED_PARENT, NEW_EXPECTED_PARENT, "R8R1_parent"),
        (OLD_MILESTONE_NAME, NEW_MILESTONE_NAME, "R8R1_name"),
        (OLD_R8_NAME, NEW_R8_NAME, "preserve_R7_R8_name_authority"),
    ]
    out = source
    for old, new, label in replacements:
        count = out.count(old)
        if count != 1:
            raise GateError(f"patch_anchor_count_{label}:{count}")
        out = out.replace(old, new, 1)

    # Namespace all newly generated R8 artifacts/directories under R8-R1.
    # This does not alter R7/R6/R5 authority strings.
    out = out.replace(OLD_PREFIX, NEW_PREFIX)
    out = out.replace(OLD_HYPHEN, NEW_HYPHEN)
    out = out.replace("AV4PIVOTP2R6R8_", "AV4PIVOTP2R6R8R1_")

    # The previous replacement changes the R8-R1 milestone identity but must
    # not change the original R8 next-name authority inherited from R7.
    if NEW_R8_NAME not in out:
        raise GateError("R8_name_authority_not_preserved")

    # The corrected pooled formulation must never create q variables for a
    # component lacking target CVs.
    if "qkeys=[(cid,c) for cid in pcids for c in pools[cid]]" not in out:
        raise GateError("corrected_qkeys_rule_missing")
    if "qkeys=[(cid,c) for cid in group_cids for c in pools[cid]]" in out:
        raise GateError("blocked_qkeys_rule_still_present")

    return out


def self_test() -> None:
    sample = (
        OLD_EXPECTED_PARENT + "\n" +
        OLD_MILESTONE_NAME + "\n" +
        OLD_R8_NAME + "\n" +
        OLD_BUILD_LINE + "\n" +
        OLD_PROW_LINE + "\n" +
        'MILESTONE="POSTV16-AV4-PIVOT-P2-R6-R8"\n' +
        'STATUS_BLOCKED="AV4PIVOTP2R6R8_TECHNICAL_OR_AUTHORITY_BLOCK"\n' +
        'X="POSTV16_AV4_PIVOT_P2_R6_R8_BLOCKED"\n'
    )
    patched = patch_exact(sample)
    assert NEW_EXPECTED_PARENT in patched
    assert NEW_MILESTONE_NAME in patched
    assert NEW_R8_NAME in patched
    assert "qkeys=[(cid,c) for cid in pcids for c in pools[cid]]" in patched
    assert OLD_BUILD_LINE not in patched
    print("POSTV16 AV4 PIVOT P2-R6-R8-R1 structural self-test: PASS")


def block_gate_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("gate")): row
        for row in report.get("gates_completed", [])
        if isinstance(row, dict) and row.get("gate") is not None
    }


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    block_dir = drive / R1_BLOCK
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

    print("=" * 206)
    print(
        "POSTV16-AV4-PIVOT-P2-R6-R8-R1 -- TARGETLESS-COMPONENT "
        "POOL-BALANCE KEYERROR TECHNICAL CLOSURE"
    )
    print("=" * 206)
    print("TECHNICAL CLOSURE OF AUTHORITATIVE R6-R8 BLOCK.")
    print("NO ORIGINAL R6-R8 BLOCK DELETION. NO DAY375 STATE MUTATION BY THIS WRAPPER.")
    print("CORRECTION: q sink-allocation variables exist only for components with R6-R7 target CVs.")
    print()

    try:
        stage = "formal_outcome_firewall"
        r1_summary = drive / R1_OUT / (
            "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_R1_Summary.json"
        )
        r1_block = block_dir / (
            "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Blocked_Report.json"
        )
        if r1_summary.is_file():
            print("[PASS] formal R6-R8-R1 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R8R1_BLOCK", not r1_block.exists(), str(r1_block))

        stage = "repository_authority"
        gate("branch_exact", git_text(root, "branch", "--show-current") == EXPECTED_BRANCH)
        head_parent = git_text(root, "rev-parse", "HEAD^")
        gate("parent_is_authoritative_blocked_R6R8_commit",
             head_parent == EXPECTED_PARENT, head_parent)
        gate("repository_clean",
             git_text(root, "status", "--porcelain") == "",
             repr(git_text(root, "status", "--porcelain")))

        original = root / ORIGINAL_R8_RUNNER
        gate("original_R8_runner_present", original.is_file(), str(original))
        original_sha = sha256_file(original)
        gate("original_R8_runner_SHA_exact",
             original_sha == ORIGINAL_R8_SHA256, original_sha)
        original_blob = git_text(root, "hash-object", str(original))
        gate("original_R8_runner_blob_exact",
             original_blob == ORIGINAL_R8_BLOB, original_blob)

        stage = "authoritative_R8_BLOCK_binding"
        old_block_path = drive / ORIGINAL_R8_BLOCK
        gate("authoritative_R8_BLOCK_present",
             old_block_path.is_file(), str(old_block_path))
        gate("no_R8_PASS_summary_exists",
             not (drive / ORIGINAL_R8_PASS).is_file(),
             str(drive / ORIGINAL_R8_PASS))

        old_block = json.loads(old_block_path.read_text(encoding="utf-8"))
        gate("R8_BLOCK_status_exact",
             old_block.get("status") == ORIGINAL_R8_STATUS_BLOCKED,
             old_block.get("status"))
        gate("R8_BLOCK_failed_stage_exact",
             old_block.get("failed_stage") == ORIGINAL_R8_EXPECTED_STAGE,
             old_block.get("failed_stage"))
        gate("R8_BLOCK_exception_exact",
             old_block.get("exception") == ORIGINAL_R8_EXPECTED_EXCEPTION,
             old_block.get("exception"))
        gate("R8_BLOCK_no_state_mutation",
             old_block.get("state_mutation_executed") is False)
        gate("R8_BLOCK_no_automatic_rerun",
             old_block.get("automatic_rerun_authorized") is False)
        gate("R8_BLOCK_no_support_growth",
             old_block.get("support_growth_execution_authorized") is False)
        gate("R8_BLOCK_no_pressure_refresh",
             old_block.get("pressure_refresh_authorized") is False)
        gate("R8_BLOCK_no_time_advance",
             old_block.get("time_advance_authorized") is False)
        gate("R8_BLOCK_P3_false",
             old_block.get("P3_authorized") is False)

        gm = block_gate_map(old_block)
        gate("R8_BLOCK_total_rec_exact_gate_present",
             "total_rec_exact" in gm)
        gate("R8_BLOCK_total_rec_exact_gate_pass",
             gm["total_rec_exact"].get("pass") is True,
             gm["total_rec_exact"].get("detail"))
        gate("R8_BLOCK_total_rec_exact_value",
             str(EXPECTED_EDGE_COUNT) in str(gm["total_rec_exact"].get("detail")),
             gm["total_rec_exact"].get("detail"))
        gate("R8_BLOCK_unique_sinks_exact_gate_present",
             "unique_sinks_exact" in gm)
        gate("R8_BLOCK_unique_sinks_exact_gate_pass",
             gm["unique_sinks_exact"].get("pass") is True,
             gm["unique_sinks_exact"].get("detail"))
        gate("R8_BLOCK_unique_sinks_exact_value",
             str(EXPECTED_SINK_COUNT) in str(gm["unique_sinks_exact"].get("detail")),
             gm["unique_sinks_exact"].get("detail"))

        stage = "targetless_component_defect_confirmation"
        r7dir = drive / R7_REL
        target_rows = read_csv(r7dir / R7_TARGETS)
        group_rows = read_csv(r7dir / R7_GROUPS)
        feas_rows = read_csv(r7dir / R7_GROUP_FEAS)

        group_ids = sorted(int(r["execution_group_id"]) for r in group_rows)
        failed_ids = sorted(
            int(r["execution_group_id"])
            for r in feas_rows
            if str(r["exact_frozen_domain_feasible"]).strip().lower()
            not in {"true", "1", "yes"}
        )
        gate("R7_group_ids_exact_0_to_86",
             group_ids == list(range(87)), group_ids)
        gate("R7_failed_group_ids_exact",
             failed_ids == EXPECTED_FAILED_GROUPS, failed_ids)
        gate("first_failed_group_is_zero", failed_ids[0] == 0)

        gmeta = {int(r["execution_group_id"]): r for r in group_rows}
        gate("group_zero_manifest_present", 0 in gmeta)
        group0_cids = [
            int(x)
            for x in gmeta[0]["R6R6_component_ids"].split(";")
            if x
        ]
        gate("group_zero_contains_component_zero", 0 in group0_cids, group0_cids)

        target_count_c0 = sum(
            1 for r in target_rows if int(r["component_id"]) == 0
        )
        gate("component_zero_has_no_R6R7_target_CVs",
             target_count_c0 == 0, target_count_c0)

        stage = "deterministic_source_patch"
        source = original.read_text(encoding="utf-8")
        corrected = patch_exact(source)
        patched_path = Path("/content") / (
            "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_R1_"
            "Corrected_Runtime_Source.py"
        )
        patched_path.write_text(corrected, encoding="utf-8", newline="\n")
        patched_sha = sha256_file(patched_path)

        gate("corrected_source_differs_from_blocked_source",
             patched_sha != original_sha, patched_sha)
        gate("corrected_source_compiles", subprocess.run(
            [sys.executable, "-m", "py_compile", str(patched_path)]
        ).returncode == 0)

        # Preserve the authoritative blocked file byte-for-byte before running
        # corrected R8-R1.
        old_block_sha_before = sha256_file(old_block_path)

        stage = "corrected_localization_execution"
        rc = subprocess.run([
            sys.executable,
            str(patched_path),
            "--project-root", str(root),
            "--drive-root", str(drive),
        ]).returncode
        gate("corrected_R8R1_runner_exit_zero", rc == 0, rc)

        old_block_sha_after = sha256_file(old_block_path)
        gate("authoritative_R8_BLOCK_preserved_byte_exact",
             old_block_sha_after == old_block_sha_before,
             old_block_sha_after)

        r1dir = drive / R1_OUT
        r1_summary_path = r1dir / (
            "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_R1_Summary.json"
        )
        r1_decision_path = r1dir / (
            "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Decision_Contract.json"
        )
        gate("R8R1_summary_present", r1_summary_path.is_file(),
             str(r1_summary_path))
        gate("R8R1_decision_present", r1_decision_path.is_file(),
             str(r1_decision_path))

        summary = json.loads(r1_summary_path.read_text(encoding="utf-8"))
        decision = json.loads(r1_decision_path.read_text(encoding="utf-8"))
        gate("R8R1_no_state_mutation",
             summary.get("state_mutation_executed") is False)
        gate("R8R1_R5_local_repair_held_fixed",
             summary.get("R5_local_repair_held_fixed") is True)
        gate("R8R1_21_failed_groups_localized",
             int(summary.get("R6R7_failed_group_count_localized", -1)) == 21,
             summary.get("R6R7_failed_group_count_localized"))
        gate("R8R1_T0_all_21_reproduced",
             int(summary.get("T0_failed_groups_reproduced", -1)) == 21,
             summary.get("T0_failed_groups_reproduced"))
        gate("R8R1_R6R9_authorized",
             decision.get("P2_R6_R9_authorized") is True)
        gate("R8R1_restart_still_false",
             decision.get("P2_continuation_restart_authorized_now") is False)
        gate("R8R1_P3_false",
             decision.get("P3_authorized") is False)

        closure = {
            "milestone": MILESTONE,
            "name": MILESTONE_NAME,
            "status": "R6R8R1_TECHNICAL_KEYERROR_CLOSURE_PASS",
            "immutable_blocked_R8_commit": EXPECTED_PARENT,
            "immutable_blocked_R8_runner_sha256": ORIGINAL_R8_SHA256,
            "immutable_blocked_R8_runner_blob": ORIGINAL_R8_BLOB,
            "authoritative_R8_block_report": str(ORIGINAL_R8_BLOCK),
            "authoritative_R8_block_sha256": old_block_sha_after,
            "blocked_stage": ORIGINAL_R8_EXPECTED_STAGE,
            "blocked_exception": ORIGINAL_R8_EXPECTED_EXCEPTION,
            "proven_pre_failure_R7_compact_edge_count": EXPECTED_EDGE_COUNT,
            "proven_pre_failure_R7_unique_sink_count": EXPECTED_SINK_COUNT,
            "root_cause": (
                "Blocked R8 created pooled q sink-allocation variables for all "
                "group components, while pool-balance rows prow existed only for "
                "components with R6-R7 target CVs. Failed group 0 contains "
                "component 0 with zero R6-R7 target CVs, so qkeys included cid=0 "
                "and prow[0] raised KeyError(0)."
            ),
            "correction": {
                "active_pool_components": (
                    "pcids = components with nonempty R6-R7 target-CV sets"
                ),
                "ykeys_domain": "pcids only",
                "qkeys_domain": "pcids only",
                "baseline_individual_H2_edges_for_targetless_components": (
                    "preserved explicit and unchanged"
                ),
                "scientific_extension_tiers_changed": False,
                "capacity_semantics_changed": False,
                "R5_state_changed": False,
            },
            "corrected_runtime_source_sha256": patched_sha,
            "R8R1_summary_sha256": sha256_file(r1_summary_path),
            "R8R1_decision_sha256": sha256_file(r1_decision_path),
            "R6R9_name": decision.get("P2_R6_R9_name"),
            "R6R9_projection_execution_authorized": (
                decision.get("P2_R6_R9_projection_execution_authorized")
            ),
            "R6R9_second_stage_topology_design_authorized": (
                decision.get(
                    "P2_R6_R9_second_stage_topology_design_authorized"
                )
            ),
            "state_mutation_executed": False,
            "pressure_refresh_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
        }
        closure_path = r1dir / (
            "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Technical_Closure_Contract.json"
        )
        closure_path.write_text(
            json.dumps(closure, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        # Refresh the R8-R1 artifact manifest so the technical closure contract
        # is itself part of the persisted authority.
        manifest_path = r1dir / (
            "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Artifact_Manifest.csv"
        )
        rows = []
        for fp in sorted(r1dir.iterdir()):
            if fp.is_file() and fp.name != manifest_path.name:
                rows.append({
                    "file": fp.name,
                    "sha256": sha256_file(fp),
                    "bytes": fp.stat().st_size,
                })
        with manifest_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f, fieldnames=["file", "sha256", "bytes"],
                lineterminator="\n"
            )
            w.writeheader()
            w.writerows(rows)

        print()
        print("=" * 206)
        print("POSTV16-AV4-PIVOT-P2-R6-R8-R1: PASS")
        print("Authoritative R8 BLOCK preserved           : True")
        print("Original R8 compact edge count reproduced  :", EXPECTED_EDGE_COUNT)
        print("Original R8 unique sink count reproduced   :", EXPECTED_SINK_COUNT)
        print("Root cause                                 : targetless q-pool / prow mismatch")
        print("Component 0 R6-R7 target CV count          :", target_count_c0)
        print("Corrected runtime source SHA256             :", patched_sha)
        print("T1A feasible groups                         :", summary.get("T1A_connectivity_only_feasible_group_count"))
        print("T1B feasible groups                         :", summary.get("T1B_single_shell_new_endpoint_feasible_group_count"))
        print("Still infeasible after T1B                  :", summary.get("single_shell_still_infeasible_group_count"))
        print("R6-R9 projection execution authorized       :", decision.get("P2_R6_R9_projection_execution_authorized"))
        print("R6-R9 second-stage topology design          :", decision.get("P2_R6_R9_second_stage_topology_design_authorized"))
        print("Day375 state mutation                       : False")
        print("P3 authorized                               : False")
        print("=" * 206)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        rp = block_dir / (
            "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Blocked_Report.json"
        )
        if not rp.exists():
            rp.write_text(
                json.dumps({
                    "milestone": MILESTONE,
                    "status": "R6R8R1_TECHNICAL_CLOSURE_BLOCK",
                    "failed_stage": stage,
                    "exception": repr(exc),
                    "state_mutation_executed": False,
                    "original_R8_BLOCK_must_remain_immutable": True,
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
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
