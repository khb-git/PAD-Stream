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


MILESTONE = "POSTV16-AV4-F1-R1"

PROTOCOL_ID = (
    "POSTV16_AV4_F1_R1_TECHNICAL_SOURCE_BLOB_AUTHORITY_TYPO_"
    "ROOT_CAUSE_CLOSURE_AND_CORRECTED_F1R2_CONTINUATION_FREEZE_V1"
)

STATUS_PASS = (
    "AV4F1R1_ORIGINAL_F1_TECHNICAL_BLOCK_PRESERVED_E1R2_BLOB_LITERAL_"
    "TYPO_ROOT_CAUSE_CLOSED_ALL_OTHER_SOURCE_BLOBS_REVALIDATED_"
    "CORRECTED_F1R2_CONTINUATION_AUTHORIZED_NO_F1_SCIENTIFIC_EXECUTION"
)

STATUS_BLOCKED = "AV4F1R1_TECHNICAL_CLOSURE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_F1_COMMIT = "b5ff08269ea6a1c4326701065a775235bd50efc8"

F1 = "PAD_Stream_POSTV16_AV4_F1_Restart_State_and_Conservative_Parent_Projection_Freeze.py"
F1_BLOB = "556641cc8bfa7eac396cc082f08c35cc871c3836"

E1R2 = (
    "PAD_Stream_POSTV16_AV4_A3_E1_R2_Fully_Schema_Corrected_"
    "Refreshed_X13_Structural_InputDomain_Audit.py"
)
E1R2_ACTUAL_BLOB = "058f00fd12bd491dc7d7d7e471af3d4ff865af70"
E1R2_BAD_LITERAL = "058f00fd12bd491dc7d7e471af3d4ff865af70"

A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

R7R7D = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7D_"
    "Horizontal_Face_Halo_Occupancy_Domain_Freeze.py"
)
R7R7D_BLOB = "bd2873f7fb6b98d4e857c98864b78e2da6f202a4"

R7R7E = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7E_"
    "Frozen_Horizontal_Face_Halo_Occupancy_Domain_Execution.py"
)
R7R7E_BLOB = "9f99d9dcab649ba7ac911ad09ad79b4e0eb2ecc8"

CORRECT_SOURCE_BLOBS = {
    E1R2: E1R2_ACTUAL_BLOB,
    A2E: A2E_BLOB,
    E37A: E37A_BLOB,
    SG7D: SG7D_BLOB,
    R7R7D: R7R7D_BLOB,
    R7R7E: R7R7E_BLOB,
}

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

F1_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F1_BLOCKED"
F1_BLOCK_REPORT = "POSTV16_AV4_F1_Blocked_Report.json"
F1_BLOCK_STATUS = "AV4F1_PROTOCOL_FREEZE_BLOCKED"

F1_PASS_REL = BASE_AV4 / "POSTV16_AV4_F1_Restart_State_and_Conservative_Parent_Projection_Freeze"
F1_PASS_SUMMARY = "PAD_Stream_POSTV16_AV4_F1_Summary.json"

OUT_REL = BASE_AV4 / "POSTV16_AV4_F1_R1_Technical_Source_Blob_Authority_Typo_Closure"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F1_R1_BLOCKED"


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


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)
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
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
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
    assert len(E1R2_ACTUAL_BLOB) == 40
    assert len(E1R2_BAD_LITERAL) == 38
    assert E1R2_ACTUAL_BLOB != E1R2_BAD_LITERAL
    assert E1R2_ACTUAL_BLOB == (
        E1R2_BAD_LITERAL[:20] + "d7" + E1R2_BAD_LITERAL[20:]
    )

    for sha in CORRECT_SOURCE_BLOBS.values():
        assert len(sha) == 40
        int(sha, 16)

    print(
        "POSTV16-AV4-F1-R1 source-blob authority typo closure "
        "self-test: PASS"
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
        gates[name] = {"passed": ok, "value": value}
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )
        if not ok:
            raise GateError(name)

    print("=" * 214)
    print(
        "POSTV16-AV4-F1-R1 — TECHNICAL SOURCE-BLOB AUTHORITY TYPO "
        "ROOT-CAUSE CLOSURE / CORRECTED F1-R2 CONTINUATION FREEZE"
    )
    print("=" * 214)
    print("CLOSURE / FREEZE ONLY.")
    print("ORIGINAL F1 TECHNICAL BLOCK REMAINS IMMUTABLE.")
    print("NO F1 SCIENTIFIC OR PROTOCOL PASS CLAIMED.")
    print("NO PROJECTION. NO CV MASS INVERSION. NO TEACHER. NO MODEL INFERENCE.")
    print("NO PHYSICAL-TIME ADVANCE. NO MAPBACK. NO TRAINING. NO CMG.")
    print("F2 IS NOT AUTHORIZED BY THIS CLOSURE; ONLY CORRECTED F1-R2 IS AUTHORIZED.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_original_F1_commit",
            parent == PARENT_F1_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        f1_actual = git_blob(root / F1, root) if (root / F1).is_file() else "missing"
        gate("original_F1_git_blob_exact", f1_actual == F1_BLOB, f1_actual)

        # Revalidate every actual source blob with corrected authority values.
        actual_blobs: dict[str, str] = {}
        for fn, expected in CORRECT_SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            actual_blobs[fn] = actual
            gate(
                f"{Path(fn).stem}_actual_git_blob_exact",
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind the immutable original F1 block.
        # ------------------------------------------------------------------------------------------
        stage = "original_F1_block_binding"

        block_path = drive / F1_BLOCK_REL / F1_BLOCK_REPORT
        gate("original_F1_block_report_present", block_path.is_file(), str(block_path))
        block = load_json(block_path)
        block_sha = sha256_file(block_path)

        gate(
            "original_F1_block_status_exact",
            block["status"] == F1_BLOCK_STATUS,
            block["status"],
        )
        gate(
            "original_F1_failed_stage_exact",
            block["failed_stage"] == "repository_authority",
            block["failed_stage"],
        )
        expected_exception = (
            "GateError('PAD_Stream_POSTV16_AV4_A3_E1_R2_Fully_Schema_Corrected_"
            "Refreshed_X13_Structural_InputDomain_Audit_git_blob_exact')"
        )
        gate(
            "original_F1_exception_exact",
            block["exception"] == expected_exception,
            block["exception"],
        )
        gate(
            "original_F1_no_projection_execution",
            block["projection_executed"] is False,
        )
        gate(
            "original_F1_no_CV_mass_inversion",
            block["CV_mass_inversion_executed"] is False,
        )
        gate(
            "original_F1_no_teacher",
            block["teacher_transport_performed"] is False,
        )
        gate(
            "original_F1_no_model_load",
            block["checkpoint_model_loaded"] is False,
        )
        gate(
            "original_F1_no_model_inference",
            block["checkpoint_inference_performed"] is False,
        )
        gate(
            "original_F1_no_time_advance",
            block["physical_time_advanced"] is False,
        )
        gate(
            "original_F1_no_training",
            block["training_performed"] is False,
        )
        gate(
            "original_F1_no_mapback",
            block["mapback_performed"] is False,
        )
        gate(
            "original_F1_F2_not_authorized_on_block",
            block["F2_authorized"] is False,
        )
        gate(
            "original_F1_F3_not_authorized",
            block["F3_authorized"] is False,
        )
        gate(
            "original_F1_A3E2_not_authorized",
            block["A3_E2_authorized"] is False,
        )
        gate(
            "original_F1_dynamic_transport_not_authorized",
            block["AV4_dynamic_transport_execution_authorized"] is False,
        )
        gate(
            "original_F1_no_automatic_rerun",
            block["automatic_rerun_authorized"] is False,
        )

        gate(
            "no_original_F1_PASS_summary_published",
            not (drive / F1_PASS_REL / F1_PASS_SUMMARY).exists(),
            str(drive / F1_PASS_REL / F1_PASS_SUMMARY),
        )

        # ------------------------------------------------------------------------------------------
        # Source-level root-cause proof.
        # ------------------------------------------------------------------------------------------
        stage = "source_level_root_cause"

        f1_source = (root / F1).read_text(encoding="utf-8", errors="replace")

        bad_line = f'E1R2_BLOB = "{E1R2_BAD_LITERAL}"'
        good_line = f'E1R2_BLOB = "{E1R2_ACTUAL_BLOB}"'

        gate(
            "original_F1_bad_E1R2_blob_literal_present",
            bad_line in f1_source,
            bad_line,
        )
        gate(
            "original_F1_correct_E1R2_blob_literal_absent",
            good_line not in f1_source,
            good_line,
        )
        gate(
            "bad_literal_length_38",
            len(E1R2_BAD_LITERAL) == 38,
            len(E1R2_BAD_LITERAL),
        )
        gate(
            "correct_literal_length_40",
            len(E1R2_ACTUAL_BLOB) == 40,
            len(E1R2_ACTUAL_BLOB),
        )
        gate(
            "root_cause_exact_missing_d7_pair",
            E1R2_ACTUAL_BLOB
            == E1R2_BAD_LITERAL[:20] + "d7" + E1R2_BAD_LITERAL[20:],
            {
                "bad": E1R2_BAD_LITERAL,
                "correct": E1R2_ACTUAL_BLOB,
            },
        )
        gate(
            "all_other_F1_source_blob_authorities_revalidated",
            all(
                actual_blobs[name] == expected
                for name, expected in CORRECT_SOURCE_BLOBS.items()
                if name != E1R2
            ),
            {
                name: actual_blobs[name]
                for name in CORRECT_SOURCE_BLOBS
                if name != E1R2
            },
        )

        # ------------------------------------------------------------------------------------------
        # Freeze corrected F1-R2 continuation.
        # ------------------------------------------------------------------------------------------
        stage = "F1R2_continuation_freeze"

        correction = {
            "milestone": MILESTONE,
            "root_cause_type": "TECHNICAL_SOURCE_BLOB_LITERAL_TYPO",
            "original_F1_failed_stage": "repository_authority",
            "original_F1_scientific_execution_performed": False,
            "bad_literal": E1R2_BAD_LITERAL,
            "bad_literal_length": len(E1R2_BAD_LITERAL),
            "correct_literal": E1R2_ACTUAL_BLOB,
            "correct_literal_length": len(E1R2_ACTUAL_BLOB),
            "exact_correction": (
                "replace only E1R2_BLOB literal in the F1 continuation from the "
                "38-character bad value to the exact 40-character Git blob"
            ),
            "missing_characters": "d7",
            "scientific_change": False,
            "projection_protocol_change": False,
            "restart_state_contract_change": False,
            "residual_sidecar_contract_change": False,
            "temporal_contract_change": False,
            "halo_semantics_change": False,
            "A2E_parent_authority_change": False,
            "E37A_SG7D_authority_change": False,
            "all_other_source_blob_values_revalidated": True,
            "original_F1_source_modified": False,
        }

        handoff = {
            "milestone": "POSTV16-AV4-F1-R2",
            "name": (
                "Corrected Restart-State Representation and Conservative "
                "Parent-State Projection Protocol Freeze"
            ),
            "authorized": True,
            "execution": True,
            "required_parent": MILESTONE,
            "allowed_correction": (
                "correct only the malformed E1R2_BLOB authority literal from "
                f"{E1R2_BAD_LITERAL} to {E1R2_ACTUAL_BLOB}"
            ),
            "required_preservation": [
                "all F1 restart-state design semantics",
                "normalized-transpose S0 mass projection",
                "exact residual Cartesian grid sidecar",
                "reverse H1->S0 pullback forbidden",
                "explicit parent/target/delta restart temporal semantics",
                "neural input dimensionality remains unfrozen",
                "no projection execution in F1-R2",
                "no CV mass inversion execution in F1-R2",
                "no teacher/checkpoint inference/time advance/mapback/training/CMG",
            ],
            "F2_authorized": False,
            "F2_execution_authorized": False,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "original_F1_technical_BLOCK_preserved": True,
            "original_F1_block_SHA256": block_sha,
            "original_F1_PASS_claimed": False,
            "root_cause_closed": True,
            "root_cause_type": "TECHNICAL_SOURCE_BLOB_LITERAL_TYPO",
            "all_other_source_blobs_revalidated": True,
            "corrected_F1R2_authorized": True,
            "corrected_F1R2_execution_authorized": True,
            "F2_authorized": False,
            "F2_execution_authorized": False,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "projection_executed": False,
            "CV_mass_inversion_executed": False,
            "teacher_transport_performed": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "physical_time_advanced": False,
            "training_performed": False,
            "mapback_performed": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "original_F1_block_SHA256": block_sha,
            "original_F1_failed_stage": "repository_authority",
            "root_cause": (
                "F1 froze a malformed 38-character E1R2 Git blob literal; "
                "the exact E1R2 repository blob is a 40-character SHA."
            ),
            "bad_E1R2_blob_literal": E1R2_BAD_LITERAL,
            "correct_E1R2_blob": E1R2_ACTUAL_BLOB,
            "all_other_source_blobs_exact": True,
            "original_F1_scientific_execution": False,
            "F1R2_authorized": True,
            "F1R2_execution_authorized": True,
            "F2_authorized": False,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        output_files = {
            "PAD_Stream_POSTV16_AV4_F1_R1_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F1_R1_Original_Block_Preservation_and_Root_Cause.json":
                json_bytes({
                    "original_block": str(block_path),
                    "original_block_sha256": block_sha,
                    "status": block["status"],
                    "failed_stage": block["failed_stage"],
                    "exception": block["exception"],
                    "scientific_execution_performed": False,
                }),
            "POSTV16_AV4_F1_R1_Corrected_Source_Blob_Authority_Contract.json":
                json_bytes(correction),
            "POSTV16_AV4_F1_R1_F1R2_Handoff_Contract.json":
                json_bytes(handoff),
            "POSTV16_AV4_F1_R1_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F1_R1_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": name, **value} for name, value in gates.items()]),
        }

        immutable_publish(out, output_files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F1_R1_Artifact_Manifest.csv":
                manifest_rows.append({
                    "file": p.name,
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })

        immutable_publish(
            out,
            {
                "POSTV16_AV4_F1_R1_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL SOURCE-BLOB AUTHORITY TYPO CLOSURE PASS")
        print("=" * 214)
        print("Original F1 block                       : PRESERVED")
        print("Original F1 PASS                        : NOT CLAIMED")
        print("Original F1 scientific execution        : False")
        print("Failed stage                            : repository_authority")
        print("Root cause                              : malformed 38-char E1R2 blob literal")
        print("Correct E1R2 blob                       :", E1R2_ACTUAL_BLOB)
        print("All other F1 source blobs               : REVALIDATED EXACT")
        print("Projection / CV inversion               : False / False")
        print("Teacher / checkpoint inference          : False / False")
        print("Physical time advance                   : False")
        print("POSTV16-AV4-F1-R2                       : AUTHORIZED")
        print("F1-R2 execution                         : AUTHORIZED")
        print("F2 / F3 / A3-E2 / dynamic transport    : NOT AUTHORIZED")
        print("=" * 214)

        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)

        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "scientific_execution_performed": False,
            "projection_executed": False,
            "CV_mass_inversion_executed": False,
            "teacher_transport_performed": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "physical_time_advanced": False,
            "training_performed": False,
            "mapback_performed": False,
            "F2_authorized": False,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }

        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F1_R1_Blocked_Report.json"

        if p.exists() and p.read_bytes() != data:
            suffix = hashlib.sha256(data).hexdigest()[:12]
            p = blocked / f"POSTV16_AV4_F1_R1_Blocked_Report_{suffix}.json"

        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL CLOSURE BLOCKED")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO AUTOMATIC RERUN AUTHORIZED.")
        print("=" * 214)

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
