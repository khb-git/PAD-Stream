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


MILESTONE = "POSTV16-AV4-A3-R1"

PROTOCOL_ID = (
    "POSTV16_AV4_A3_R1_TECHNICAL_AUTHORITY_SCHEMA_BLOCK_"
    "ROOT_CAUSE_CLOSURE_AND_CORRECTED_CONTINUATION_FREEZE_V1"
)

STATUS_PASS = (
    "AV4A3R1_ORIGINAL_A3_TECHNICAL_BLOCK_PRESERVED_"
    "A2E_SUMMARY_VS_DECISION_AUTHORITY_SCHEMA_ROOT_CAUSE_CLOSED_"
    "CORRECTED_A3R2_CONTINUATION_PROSPECTIVELY_FROZEN_NO_A3_SCIENTIFIC_EXECUTION"
)

STATUS_BLOCKED = "AV4A3R1_TECHNICAL_CLOSURE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_A3_COMMIT = "227ccdc8cf2b967b894d78a76a4a22b3a9ab9f74"

A3 = (
    "PAD_Stream_POSTV16_AV4_A3_"
    "Refreshed_13Channel_Checkpoint_Compatibility_Protocol_Freeze.py"
)
A3_BLOB = "4ca86c76d29a628ce010661e85663e7e4fa3b34a"

A2E = (
    "PAD_Stream_POSTV16_AV4_A2_E_"
    "Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
)
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

SOURCE_BLOBS = {
    A3: A3_BLOB,
    A2E: A2E_BLOB,
}

BASE_AV4 = (
    Path("post_v16")
    / RID
    / "POSTV16_AV4_Dynamic_Flow_Coupling"
)

A2E_REL = (
    BASE_AV4
    / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
)

A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_DECISION = "POSTV16_AV4_A2_E_Decision_Contract.json"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

ORIGINAL_A3_BLOCK_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_BLOCKED"
)

ORIGINAL_A3_BLOCK = "POSTV16_AV4_A3_Blocked_Report.json"

ORIGINAL_A3_BLOCK_STATUS = "AV4A3_PROTOCOL_FREEZE_BLOCKED"
ORIGINAL_A3_FAILED_STAGE = "A2E_authority_binding"
ORIGINAL_A3_EXPECTED_EXCEPTION = (
    "KeyError('AV4_dynamic_transport_execution_authorized')"
)

ORIGINAL_A3_PASS_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_Refreshed_13Channel_Checkpoint_Compatibility_Protocol_Freeze"
)
ORIGINAL_A3_PASS_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_Summary.json"

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_R1_Technical_Authority_Schema_Block_Closure"
)

BLOCK_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_R1_BLOCKED"
)


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_manifest(directory: Path, name: str) -> dict[str, str]:
    rows = read_csv(directory / name)
    manifest = {r["file"]: r["sha256"] for r in rows}

    if not manifest:
        raise GateError("manifest_empty:" + name)

    for fn, expected in manifest.items():
        p = directory / fn

        if not p.is_file():
            raise GateError("manifest_missing:" + fn)

        if sha256_file(p) != expected:
            raise GateError("manifest_SHA_mismatch:" + fn)

    return manifest


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(
            obj,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""

    fields: list[str] = []

    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    s = io.StringIO(newline="")
    w = csv.DictWriter(
        s,
        fieldnames=fields,
        lineterminator="\n",
    )

    w.writeheader()
    w.writerows(rows)

    return s.getvalue().encode("utf-8")


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)

    for name, data in files.items():
        p = out / name

        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)

        if not p.exists():
            p.write_bytes(data)


def self_test() -> None:
    assert ORIGINAL_A3_EXPECTED_EXCEPTION == (
        "KeyError('AV4_dynamic_transport_execution_authorized')"
    )
    assert ORIGINAL_A3_FAILED_STAGE == "A2E_authority_binding"
    assert A3_BLOB == "4ca86c76d29a628ce010661e85663e7e4fa3b34a"
    assert A2E_BLOB == "79a8969233b72b4543edd382a0c3d1028c6dca09"

    print(
        "POSTV16-AV4-A3-R1 technical authority-schema block closure self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()

    out = drive / OUT_REL
    blocked = drive / BLOCK_REL

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)

        gates[name] = {
            "passed": ok,
            "value": value,
        }

        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )

        if not ok:
            raise GateError(name)

    print("=" * 214)
    print(
        "POSTV16-AV4-A3-R1 — TECHNICAL AUTHORITY-SCHEMA BLOCK "
        "ROOT-CAUSE CLOSURE / CORRECTED CONTINUATION FREEZE"
    )
    print("=" * 214)
    print("CLOSURE / FREEZE ONLY.")
    print("THE ORIGINAL AV4-A3 TECHNICAL BLOCK REMAINS IMMUTABLE.")
    print("NO AV4-A3 SCIENTIFIC PASS IS CLAIMED.")
    print("NO PI-RNN MODEL LOAD OR INFERENCE.")
    print("NO TEACHER TRANSPORT. NO PHYSICAL-TIME ADVANCE.")
    print("NO TRAINING / NORMALIZATION REFIT / MAPBACK / LP / CMG.")
    print("NO AUTOMATIC RERUN.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_original_A3_commit",
            parent == PARENT_A3_COMMIT,
            parent,
        )

        gate(
            "repository_clean",
            status == "",
            repr(status),
        )

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn

            actual = (
                git_blob(p, root)
                if p.is_file()
                else "missing"
            )

            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Preserve and bind the original A3 technical block.
        # ------------------------------------------------------------------------------------------
        stage = "original_A3_block_binding"

        block_dir = drive / ORIGINAL_A3_BLOCK_REL
        block_path = block_dir / ORIGINAL_A3_BLOCK

        gate(
            "original_A3_block_report_present",
            block_path.is_file(),
            str(block_path),
        )

        block_sha = sha256_file(block_path)

        original_block = load_json(
            block_path
        )

        gate(
            "original_A3_block_status_exact",
            original_block["status"] == ORIGINAL_A3_BLOCK_STATUS,
            original_block["status"],
        )

        gate(
            "original_A3_failed_stage_exact",
            original_block["failed_stage"] == ORIGINAL_A3_FAILED_STAGE,
            original_block["failed_stage"],
        )

        gate(
            "original_A3_exception_exact",
            original_block["exception"] == ORIGINAL_A3_EXPECTED_EXCEPTION,
            original_block["exception"],
        )

        gate(
            "original_A3_no_checkpoint_model_load",
            original_block["checkpoint_model_loaded"] is False,
        )

        gate(
            "original_A3_no_checkpoint_inference",
            original_block["checkpoint_inference_performed"] is False,
        )

        gate(
            "original_A3_no_teacher_transport",
            original_block["teacher_transport_performed"] is False,
        )

        gate(
            "original_A3_no_physical_time_advance",
            original_block["physical_time_advanced"] is False,
        )

        gate(
            "original_A3_no_training",
            original_block["training_performed"] is False,
        )

        gate(
            "original_A3_no_normalization_refit",
            original_block["normalization_refit"] is False,
        )

        gate(
            "original_A3_dynamic_transport_remained_unauthorized",
            original_block["AV4_dynamic_transport_execution_authorized"] is False,
        )

        gate(
            "original_A3_A3E1_remained_unauthorized",
            original_block["AV4_A3_E1_authorized"] is False,
        )

        original_pass_summary = (
            drive
            / ORIGINAL_A3_PASS_REL
            / ORIGINAL_A3_PASS_SUMMARY
        )

        gate(
            "no_original_A3_PASS_summary_published",
            not original_pass_summary.exists(),
            str(original_pass_summary),
        )

        # ------------------------------------------------------------------------------------------
        # Bind A2-E PASS and prove the exact schema mismatch.
        # ------------------------------------------------------------------------------------------
        stage = "A2E_schema_root_cause_audit"

        a2e = drive / A2E_REL

        gate(
            "A2E_output_present",
            a2e.is_dir(),
            str(a2e),
        )

        m2e = verify_manifest(
            a2e,
            A2E_MANIFEST,
        )

        gate(
            "A2E_manifest_exact_12",
            len(m2e) == 12,
            len(m2e),
        )

        s2e = load_json(
            a2e / A2E_SUMMARY
        )

        d2e = load_json(
            a2e / A2E_DECISION
        )

        gate(
            "A2E_status_exact",
            s2e["status"] == A2E_STATUS,
            s2e["status"],
        )

        gate(
            "A2E_summary_contains_dynamic_transport_authority",
            "AV4_dynamic_transport_execution_authorized" in s2e,
            sorted(s2e.keys()),
        )

        gate(
            "A2E_summary_dynamic_transport_false",
            s2e["AV4_dynamic_transport_execution_authorized"] is False,
            s2e["AV4_dynamic_transport_execution_authorized"],
        )

        gate(
            "A2E_decision_omits_dynamic_transport_authority_key",
            "AV4_dynamic_transport_execution_authorized" not in d2e,
            sorted(d2e.keys()),
        )

        gate(
            "A2E_decision_A3_handoff_exact",
            d2e["next"]["milestone"] == "POSTV16-AV4-A3"
            and d2e["next"]["authorized"] is True
            and d2e["next"]["execution"] is False,
            d2e["next"],
        )

        gate(
            "A2E_summary_and_decision_status_agree",
            s2e["status"] == d2e["status"] == A2E_STATUS,
        )

        # ------------------------------------------------------------------------------------------
        # Source-level proof that original A3 read the wrong artifact.
        # ------------------------------------------------------------------------------------------
        stage = "source_level_root_cause_proof"

        a3_source = (root / A3).read_text(
            encoding="utf-8",
            errors="replace",
        )

        wrong_read = (
            'd2e["AV4_dynamic_transport_execution_authorized"] is False'
        )

        corrected_read = (
            's2e["AV4_dynamic_transport_execution_authorized"] is False'
        )

        gate(
            "original_A3_wrong_decision_read_present",
            wrong_read in a3_source,
            wrong_read,
        )

        gate(
            "corrected_summary_read_not_already_present_at_gate",
            corrected_read not in a3_source,
            corrected_read,
        )

        # ------------------------------------------------------------------------------------------
        # Freeze the root-cause closure.
        # ------------------------------------------------------------------------------------------
        stage = "root_cause_closure_freeze"

        root_cause = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "original_A3_block_report": {
                "path": str(block_path),
                "sha256": block_sha,
                "status": ORIGINAL_A3_BLOCK_STATUS,
                "failed_stage": ORIGINAL_A3_FAILED_STAGE,
                "exception": ORIGINAL_A3_EXPECTED_EXCEPTION,
                "preserved_immutable": True,
            },
            "root_cause": {
                "type": "TECHNICAL_AUTHORITY_SCHEMA_READ_MISMATCH",
                "description": (
                    "The original AV4-A3 runner attempted to read "
                    "AV4_dynamic_transport_execution_authorized from the A2-E "
                    "Decision Contract. A2-E froze that field in its Summary, "
                    "while the Decision Contract omitted that key."
                ),
                "A2E_summary_contains_key": True,
                "A2E_summary_value": False,
                "A2E_decision_contains_key": False,
                "A2E_scientific_result_changed": False,
                "A3_scientific_execution_started": False,
            },
            "scientific_interpretation": (
                "No scientific gate failed. The A3 protocol did not proceed "
                "beyond A2-E authority binding, and no checkpoint/teacher/"
                "transport execution occurred."
            ),
        }

        corrected_authority = {
            "field": "AV4_dynamic_transport_execution_authorized",
            "authoritative_source_for_A3R2": A2E_SUMMARY,
            "required_value": False,
            "forbidden_source_for_this_field": A2E_DECISION,
            "A2E_decision_role_preserved": (
                "authoritative for A2-E scientific PASS facts and A3 handoff"
            ),
            "A2E_summary_role_preserved": (
                "authoritative for explicit top-level AV4 dynamic-transport "
                "authorization state"
            ),
            "normalization_or_physics_change": False,
            "checkpoint_change": False,
            "transport_change": False,
        }

        # ------------------------------------------------------------------------------------------
        # Freeze exactly what A3-R2 may do.
        # ------------------------------------------------------------------------------------------
        stage = "A3R2_continuation_freeze"

        handoff = {
            "milestone": "POSTV16-AV4-A3-R2",
            "name": (
                "Corrected Refreshed 13-Channel / Checkpoint Compatibility "
                "Protocol-Freeze Continuation"
            ),
            "authorized": True,
            "execution": True,
            "required_parent": MILESTONE,
            "allowed_correction": (
                "Replace only the original A3 dynamic-transport authority read "
                "from d2e[...] with the frozen A2-E Summary read s2e[...]."
            ),
            "required_preservation": [
                "preserve original A3 blocked report immutable",
                "preserve original A3 source/commit immutable",
                "bind A2-E PASS and manifest exactly",
                "retain all original A3 firewalls and protocol content",
                "no model load or checkpoint inference",
                "no teacher transport",
                "no physical-time advance",
                "no normalization refit",
                "no training or checkpoint reselection",
                "no mapback, LP, or CMG",
                "AV3 checkpoint committed reuse remains false",
                "AV4 dynamic transport remains unauthorized",
            ],
            "forbidden": [
                "edit or delete the original A3 blocked report",
                "rewrite A2-E artifacts",
                "change A3 scientific criteria",
                "change 13-channel definitions",
                "change checkpoint identity",
                "relax any authority or firewall gate",
                "automatic rerun of original A3",
            ],
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "original_A3_technical_BLOCK_preserved": True,
            "original_A3_block_SHA256": block_sha,
            "original_A3_scientific_PASS_claimed": False,
            "original_A3_scientific_execution_started": False,
            "root_cause_closed": True,
            "root_cause_type": "TECHNICAL_AUTHORITY_SCHEMA_READ_MISMATCH",
            "A2E_scientific_PASS_preserved": True,
            "A2E_summary_dynamic_transport_authority_false": True,
            "A2E_decision_dynamic_transport_key_absent": True,
            "A2E_artifacts_modified": False,
            "A3_artifacts_modified": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "teacher_transport_performed": False,
            "physical_time_advanced": False,
            "normalization_refit": False,
            "training_performed": False,
            "AV4_A3_E1_authorized": False,
            "AV4_A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "AV4_A3_R2_authorized": True,
            "next": handoff,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "original_A3_block_SHA256": block_sha,
            "failed_stage": ORIGINAL_A3_FAILED_STAGE,
            "original_exception": ORIGINAL_A3_EXPECTED_EXCEPTION,
            "root_cause": "A2E_SUMMARY_VS_DECISION_AUTHORITY_SCHEMA_READ_MISMATCH",
            "corrected_authority_source": A2E_SUMMARY,
            "corrected_authority_value": False,
            "scientific_execution_started": False,
            "checkpoint_inference": False,
            "teacher_transport": False,
            "physical_time_advance": False,
            "AV4_A3_R2_authorized": True,
            "AV4_A3_E1_authorized": False,
            "AV4_A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_A3_R1_Summary.json":
                json_bytes(summary),

            "POSTV16_AV4_A3_R1_Original_Block_Preservation_and_Root_Cause.json":
                json_bytes(root_cause),

            "POSTV16_AV4_A3_R1_Corrected_A2E_Authority_Read_Contract.json":
                json_bytes(corrected_authority),

            "POSTV16_AV4_A3_R1_A3R2_Handoff_Contract.json":
                json_bytes(handoff),

            "POSTV16_AV4_A3_R1_Decision_Contract.json":
                json_bytes(decision),

            "POSTV16_AV4_A3_R1_Final_Gate_Matrix.csv":
                csv_bytes(
                    [
                        {
                            "gate": name,
                            **value,
                        }
                        for name, value in gates.items()
                    ]
                ),
        }

        immutable_publish(
            out,
            files,
        )

        manifest_rows = []

        for p in sorted(out.iterdir()):
            if (
                p.is_file()
                and p.name != "POSTV16_AV4_A3_R1_Artifact_Manifest.csv"
            ):
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )

        immutable_publish(
            out,
            {
                "POSTV16_AV4_A3_R1_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print("POSTV16-AV4-A3-R1: TECHNICAL AUTHORITY-SCHEMA BLOCK CLOSURE PASS")
        print("=" * 214)
        print("Original AV4-A3 block                     : PRESERVED")
        print("Original A3 scientific PASS               : NOT CLAIMED")
        print("Failed stage                              :", ORIGINAL_A3_FAILED_STAGE)
        print("Root cause                                : A2-E Summary/Decision schema read mismatch")
        print("Correct authority source                  :", A2E_SUMMARY)
        print("Dynamic transport authority               : False")
        print("Checkpoint inference                      : False")
        print("Teacher transport                         : False")
        print("Physical-time advance                     : False")
        print("POSTV16-AV4-A3-R2                         : AUTHORIZED")
        print("A3-R2 execution                           : AUTHORIZED")
        print("AV4-A3-E1                                 : NOT YET AUTHORIZED")
        print("AV4 dynamic transport                     : NOT YET AUTHORIZED")
        print("=" * 214)

        return 0

    except Exception as exc:
        blocked.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "original_A3_block_preserved": True,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "teacher_transport_performed": False,
            "physical_time_advanced": False,
            "normalization_refit": False,
            "training_performed": False,
            "AV4_A3_R2_authorized": False,
            "AV4_A3_E1_authorized": False,
            "AV4_A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        p = (
            blocked
            / "POSTV16_AV4_A3_R1_Blocked_Report.json"
        )

        if not p.exists():
            p.write_bytes(
                json_bytes(report)
            )

        print()
        print("=" * 214)
        print("POSTV16-AV4-A3-R1: TECHNICAL CLOSURE BLOCK")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO AUTOMATIC RERUN AUTHORIZED.")
        print("=" * 214)

        return 2


def parse_args():
    p = argparse.ArgumentParser()

    p.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )

    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path(
            "/content/drive/MyDrive/PAD_Stream_Compute"
        ),
    )

    p.add_argument(
        "--self-test",
        action="store_true",
    )

    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.self_test:
        self_test()
        raise SystemExit(0)

    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
