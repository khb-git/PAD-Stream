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


MILESTONE = "POSTV16-AV4-A3-E1-R1"

PROTOCOL_ID = (
    "POSTV16_AV4_A3_E1_R1_TECHNICAL_AUTHORITY_SCHEMA_BLOCK_"
    "ROOT_CAUSE_CLOSURE_AND_CORRECTED_E1R2_CONTINUATION_FREEZE_V1"
)

STATUS_PASS = (
    "AV4A3E1R1_ORIGINAL_E1_TECHNICAL_BLOCK_PRESERVED_"
    "R5_RECONSTRUCTION_CONTRACT_SHAPE_SCHEMA_ROOT_CAUSE_CLOSED_"
    "CORRECTED_E1R2_CONTINUATION_PROSPECTIVELY_FROZEN_"
    "NO_E1_SCIENTIFIC_EXECUTION"
)

STATUS_BLOCKED = "AV4A3E1R1_TECHNICAL_CLOSURE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_E1_COMMIT = "a0c69a355c229840d2de2a782079bcdb3e81f4f4"

E1 = "PAD_Stream_POSTV16_AV4_A3_E1_Refreshed_X13_Structural_InputDomain_Audit.py"
E1_BLOB = "2555ccdb5c3311ea49b0269746ba6ce17aa46258"

R5 = (
    "PAD_Stream_POSTV16_AV4_A3_R2_R1_R5_Preexecution_Historical_Gate_Validated_"
    "Checkpoint_Compatibility_Protocol_Continuation.py"
)
R5_BLOB = "7192495d80d656fb950b7c5418f928f32246e93f"

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

E1_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_BLOCKED"
E1_BLOCK_REPORT = "POSTV16_AV4_A3_E1_Blocked_Report.json"
E1_BLOCK_STATUS = "AV4A3E1_TECHNICAL_EXECUTION_BLOCKED"

E1_PASS_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_Refreshed_X13_Structural_InputDomain_Audit"
E1_PASS_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_E1_Summary.json"

R5_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_R2_R1_R5_Preexecution_Historical_Gate_Validated_Protocol_Continuation"
)
R5_RECON = "POSTV16_AV4_A3_R2_R1_R5_Refreshed_13Channel_Reconstruction_Contract.json"
R5_HANDOFF = "POSTV16_AV4_A3_R2_R1_R5_A3E1_Handoff_Contract.json"
R5_DECISION = "POSTV16_AV4_A3_R2_R1_R5_Decision_Contract.json"
R5_MANIFEST = "POSTV16_AV4_A3_R2_R1_R5_Artifact_Manifest.csv"

OUT_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R1_Technical_Authority_Schema_Block_Closure"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R1_BLOCKED"


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
    # Exact schema fact that caused the original E1 block:
    recon = {
        "channel_order": [f"c{i}" for i in range(13)],
        "nodes_per_streamline": 201,
        "refreshed_streamlines": 1078,
    }

    assert "shape" not in recon
    assert recon["refreshed_streamlines"] == 1078
    assert recon["nodes_per_streamline"] == 201
    assert len(recon["channel_order"]) == 13

    print(
        "POSTV16-AV4-A3-E1-R1 technical authority-schema block closure "
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
        "POSTV16-AV4-A3-E1-R1 — TECHNICAL AUTHORITY-SCHEMA BLOCK "
        "ROOT-CAUSE CLOSURE / CORRECTED E1-R2 CONTINUATION FREEZE"
    )
    print("=" * 214)
    print("CLOSURE / FREEZE ONLY.")
    print("ORIGINAL E1 TECHNICAL BLOCK REMAINS IMMUTABLE.")
    print("NO E1 SCIENTIFIC PASS CLAIMED.")
    print("NO X13 RECONSTRUCTION. NO CHECKPOINT LOAD/INFERENCE. NO TEACHER.")
    print("NO PHYSICAL-TIME ADVANCE. NO MAPBACK / LP / TRAINING / CMG.")
    print("NO AUTOMATIC RERUN OF ORIGINAL E1.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository/source identity.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_original_E1_commit",
            parent == PARENT_E1_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        for fn, expected in [(E1, E1_BLOB), (R5, R5_BLOB)]:
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Preserve exact original E1 block.
        # ------------------------------------------------------------------------------------------
        stage = "original_E1_block_binding"

        block_path = drive / E1_BLOCK_REL / E1_BLOCK_REPORT
        gate("original_E1_block_report_present", block_path.is_file(), str(block_path))

        block_sha = sha256_file(block_path)
        block = load_json(block_path)

        gate(
            "original_E1_block_status_exact",
            block["status"] == E1_BLOCK_STATUS,
            block["status"],
        )
        gate(
            "original_E1_failed_stage_exact",
            block["failed_stage"] == "R5_authority_binding",
            block["failed_stage"],
        )
        gate(
            "original_E1_exception_exact",
            block["exception"] == "KeyError('shape')",
            block["exception"],
        )
        gate(
            "original_E1_reconstruction_never_started",
            block["reconstruction_started"] is False,
        )
        gate(
            "original_E1_no_checkpoint_model_load",
            block["checkpoint_model_loaded"] is False,
        )
        gate(
            "original_E1_no_checkpoint_inference",
            block["checkpoint_inference_performed"] is False,
        )
        gate(
            "original_E1_no_teacher_transport",
            block["teacher_transport_performed"] is False,
        )
        gate(
            "original_E1_no_physical_time_advance",
            block["physical_time_advanced"] is False,
        )
        gate(
            "original_E1_checkpoint_reuse_false",
            block["AV3_checkpoint_committed_reuse"] is False,
        )
        gate(
            "original_E1_A3E2_unauthorized",
            block["AV4_A3_E2_authorized"] is False,
        )
        gate(
            "original_E1_dynamic_transport_unauthorized",
            block["AV4_dynamic_transport_execution_authorized"] is False,
        )
        gate(
            "original_E1_no_automatic_rerun",
            block["automatic_rerun_authorized"] is False,
        )

        gate(
            "no_original_E1_PASS_summary_published",
            not (drive / E1_PASS_REL / E1_PASS_SUMMARY).exists(),
            str(drive / E1_PASS_REL / E1_PASS_SUMMARY),
        )

        # ------------------------------------------------------------------------------------------
        # Bind frozen R5 reconstruction schema.
        # ------------------------------------------------------------------------------------------
        stage = "R5_reconstruction_schema_binding"

        r5 = drive / R5_REL
        gate("R5_output_present", r5.is_dir(), str(r5))

        m5 = verify_manifest(r5, R5_MANIFEST)
        gate("R5_manifest_exact_11", len(m5) == 11, len(m5))

        recon = load_json(r5 / R5_RECON)
        handoff = load_json(r5 / R5_HANDOFF)
        decision = load_json(r5 / R5_DECISION)

        gate(
            "R5_reconstruction_contract_has_no_shape_key",
            "shape" not in recon,
            sorted(recon.keys()),
        )
        gate(
            "R5_reconstruction_refreshed_streamlines_exact",
            recon["refreshed_streamlines"] == 1078,
            recon["refreshed_streamlines"],
        )
        gate(
            "R5_reconstruction_nodes_per_streamline_exact",
            recon["nodes_per_streamline"] == 201,
            recon["nodes_per_streamline"],
        )
        gate(
            "R5_reconstruction_channel_count_exact_13",
            len(recon["channel_order"]) == 13,
            len(recon["channel_order"]),
        )
        gate(
            "R5_required_identity_gate_freezes_target_shape",
            "shape exactly (1078,201,13) for one target-time slice"
            in recon["required_reconstruction_identity_gates"],
            recon["required_reconstruction_identity_gates"],
        )
        gate(
            "R5_E1_handoff_still_authorized",
            handoff["milestone"] == "POSTV16-AV4-A3-E1"
            and handoff["authorized"] is True
            and handoff["execution"] is True,
            handoff,
        )
        gate(
            "R5_E2_and_dynamic_transport_still_unauthorized",
            handoff["A3_E2_teacher_backed_checkpoint_test_authorized"] is False
            and handoff["AV4_dynamic_transport_execution_authorized"] is False
            and decision["AV4_A3_E2_authorized"] is False
            and decision["AV4_dynamic_transport_execution_authorized"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Source-level root cause proof.
        # ------------------------------------------------------------------------------------------
        stage = "source_level_root_cause"

        e1_source = (root / E1).read_text(encoding="utf-8", errors="replace")
        r5_source = (root / R5).read_text(encoding="utf-8", errors="replace")

        wrong_read = 'recon5["shape"] == [NSL, NN, 13]'
        corrected_read = (
            'recon5["refreshed_streamlines"] == NSL'
        )

        gate(
            "original_E1_wrong_shape_key_read_present",
            wrong_read in e1_source,
            wrong_read,
        )
        gate(
            "original_E1_corrected_schema_read_not_already_present",
            corrected_read not in e1_source,
            corrected_read,
        )
        gate(
            "R5_source_contract_uses_scalar_shape_components",
            '"refreshed_streamlines": NSL' in r5_source
            and '"nodes_per_streamline": NN' in r5_source
            and '"channel_order": CHANNELS13' in r5_source
            and '"shape":' not in r5_source[
                r5_source.find("reconstruction = {"):
                r5_source.find("# Freeze the structural temporal-semantics", r5_source.find("reconstruction = {"))
            ],
        )

        # ------------------------------------------------------------------------------------------
        # Freeze corrected E1-R2 authority-read contract.
        # ------------------------------------------------------------------------------------------
        stage = "corrected_E1R2_contract_freeze"

        corrected_contract = {
            "milestone": MILESTONE,
            "root_cause_type": "TECHNICAL_AUTHORITY_SCHEMA_READ_MISMATCH",
            "original_E1_failed_stage": "R5_authority_binding",
            "original_exception": "KeyError('shape')",
            "R5_reconstruction_contract_shape_key_exists": False,
            "authoritative_shape_components": {
                "refreshed_streamlines": "recon5['refreshed_streamlines']",
                "nodes_per_streamline": "recon5['nodes_per_streamline']",
                "channel_count": "len(recon5['channel_order'])",
                "channel_order": "recon5['channel_order']",
            },
            "required_corrected_gate": (
                "recon5['refreshed_streamlines'] == NSL and "
                "recon5['nodes_per_streamline'] == NN and "
                "len(recon5['channel_order']) == 13 and "
                "recon5['channel_order'] == CHANNELS13"
            ),
            "scientific_change": False,
            "channel_definition_change": False,
            "normalization_change": False,
            "physics_change": False,
            "checkpoint_change": False,
            "transport_change": False,
            "teacher_change": False,
            "time_advance_change": False,
            "original_E1_source_modified": False,
        }

        handoff_r2 = {
            "milestone": "POSTV16-AV4-A3-E1-R2",
            "name": (
                "Corrected Refreshed X13 Structural/Input-Domain Audit "
                "Continuation"
            ),
            "authorized": True,
            "execution": True,
            "required_parent": MILESTONE,
            "allowed_correction": (
                "replace only the invalid R5 reconstruction contract shape-key read "
                "with the frozen scalar shape components + channel-order identity"
            ),
            "preserve": [
                "original E1 technical block and blocked report",
                "all E1 scientific gates",
                "all E1 channel definitions",
                "historical TRAIN-only normalization",
                "exact ADV/pore-velocity/trilinear reconstruction path",
                "no checkpoint load/inference firewall",
                "no teacher/time-advance/mapback/training/CMG firewalls",
                "A3-E2 unauthorized",
                "AV4 dynamic transport unauthorized",
            ],
            "original_E1_automatic_rerun": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        decision_r1 = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "original_E1_technical_BLOCK_preserved": True,
            "original_E1_block_SHA256": block_sha,
            "original_E1_scientific_PASS_claimed": False,
            "root_cause_closed": True,
            "root_cause_type": "TECHNICAL_AUTHORITY_SCHEMA_READ_MISMATCH",
            "R5_shape_key_exists": False,
            "corrected_E1R2_continuation_authorized": True,
            "corrected_E1R2_execution_authorized": True,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "teacher_transport_performed": False,
            "physical_time_advanced": False,
            "scientific_execution_performed": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "original_E1_block_SHA256": block_sha,
            "original_E1_failed_stage": "R5_authority_binding",
            "original_E1_exception": "KeyError('shape')",
            "root_cause": (
                "E1 read recon5['shape']; frozen R5 reconstruction contract "
                "instead stores refreshed_streamlines, nodes_per_streamline, and channel_order"
            ),
            "R5_refreshed_streamlines": recon["refreshed_streamlines"],
            "R5_nodes_per_streamline": recon["nodes_per_streamline"],
            "R5_channel_count": len(recon["channel_order"]),
            "original_E1_reconstruction_started": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "teacher_transport_performed": False,
            "physical_time_advanced": False,
            "A3_E1_R2_authorized": True,
            "A3_E1_R2_execution_authorized": True,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        output_files = {
            "PAD_Stream_POSTV16_AV4_A3_E1_R1_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_A3_E1_R1_Original_Block_Preservation_and_Root_Cause.json":
                json_bytes({
                    "original_block": str(block_path),
                    "original_block_sha256": block_sha,
                    "status": block["status"],
                    "failed_stage": block["failed_stage"],
                    "exception": block["exception"],
                    "reconstruction_started": block["reconstruction_started"],
                    "scientific_execution_claimed": False,
                }),
            "POSTV16_AV4_A3_E1_R1_Corrected_R5_Reconstruction_Schema_Read_Contract.json":
                json_bytes(corrected_contract),
            "POSTV16_AV4_A3_E1_R1_E1R2_Handoff_Contract.json":
                json_bytes(handoff_r2),
            "POSTV16_AV4_A3_E1_R1_Decision_Contract.json":
                json_bytes(decision_r1),
            "POSTV16_AV4_A3_E1_R1_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": name, **value} for name, value in gates.items()]),
        }

        immutable_publish(out, output_files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_A3_E1_R1_Artifact_Manifest.csv":
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
                "POSTV16_AV4_A3_E1_R1_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL AUTHORITY-SCHEMA BLOCK CLOSURE PASS")
        print("=" * 214)
        print("Original E1 block                       : PRESERVED")
        print("Original E1 scientific PASS             : NOT CLAIMED")
        print("Original reconstruction started         : False")
        print("Failed stage                            : R5_authority_binding")
        print("Root cause                              : invalid recon5['shape'] schema read")
        print("R5 authoritative shape components       : 1078 / 201 / 13-channel order")
        print("Checkpoint load / inference             : False / False")
        print("Teacher transport / time advance        : False / False")
        print("POSTV16-AV4-A3-E1-R2                    : AUTHORIZED")
        print("E1-R2 execution                         : AUTHORIZED")
        print("A3-E2                                   : NOT AUTHORIZED")
        print("AV4 dynamic transport                   : NOT AUTHORIZED")
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
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "teacher_transport_performed": False,
            "physical_time_advanced": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }

        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_A3_E1_R1_Blocked_Report.json"

        if p.exists() and p.read_bytes() != data:
            suffix = hashlib.sha256(data).hexdigest()[:12]
            p = blocked / f"POSTV16_AV4_A3_E1_R1_Blocked_Report_{suffix}.json"

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

    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
